"""The care branch (Plan 24 Task 10, ruling P24-G 2; Angus's direction of 2026-10-29: bandage wounds first, rags from
ripping clothes and washing them; the jar reads #4298-#4301): `Care`, a one-action-at-a-time policy over PZA/1.5's
`bandage`, `rip` and `wash` (Task 9), which `survive.Survive` runs between `threat` and `need` while no threat is held
(the threat branch runs first and answers while any zombie is within its hold radius, so the branch yields to a
threat within DANGER_R, and a threat arriving supersedes its running action).

Its choose, the first that answers (`why` names the `reason`, the `part`, the `item` and its `kind`):
1. `bleeding`: the worst bleeding unbandaged part of the frame's `body.parts` (a deep wound first, then the longest
   `bleedingTime`, then the least index), bandaged (`Bandage(itemId, part)`) with the best held item by `care_kind`:
   a clean bandage, then a clean rag, then a dirty one only when the part's `bleedingTime` exceeds DIRTY_RAG_MIN (a
   dirty rag stops the bleeding but doubles the infection odds against none, #4299; the bleeding drain scales with
   the bleeding time, #4298). With no rag of any kind held, one held cotton garment is ripped (`no_rag`, step 4's
   rule); a dirty rag held under the time rule falls through to the wash.
2. `replace`: a bandaged part whose `bandageLife` reached 0 or that reads `bandageDirty`, with a clean bandage or rag
   held: bandaged again with it (the Lua takes the old one off first).
3. `wash`: a dirty rag held, no zombie within DISENGAGE_R (Survive passes `quiet`), and a known water source (the map's
   square `water` record with water in it, on the player's floor, not refused lately) within WASH_R: `Wash(itemId, x,
   y)`, the Lua walking next to it (a wash does not test the water's taint, #4301).
4. `rip`: no bandage item of any kind held and a held item `rippable` names a cotton garment, never one of the
   inventory's first sight (`World.first_sight`: the clothes the character stands in, which the Lua refuses `worn`)
   nor one marked `unrippable` (a rip refused `worn`, `not cotton` or `needs tool`, `World.mark`): `Rip(itemId)`.
An item whose care action ended failed (never `superseded`), timed out or was rejected is left out for
CARE_RETRY_MIN game minutes (`World.world_minutes`); a wash refused `no source` or `no water` leaves its source out for
SOURCE_RETRY_MIN. Each step needs its skill in the hello's caps (`World.can`); a PZA/1.4 frame's parts carry no
`bleeding` (decoded None), so the branch reads no wound there and no decision golden moves.

The item reads are names (`care_kind`, `rippable`): what `ISApplyBandage` reads, `Dirty` in the type (#4299); the
`RipClothing` recipe's cotton tag is in no dataset the repository carries, so `rippable` is a guess the Lua's refusal
corrects.
"""
import math
import re
import time

from agent.base.planner.policies import Policy, PREEMPTED, item_id_ok
from agent.base.pza1 import Bandage, Rip, Wash
from agent.base.world import me_floor, me_xy

CARE_RETRY_MIN = 2.0      # game minutes an item whose care action was refused is left out (P24-G 2)
DIRTY_RAG_MIN = 10.0      # a dirty rag goes on a part only when its bleedingTime exceeds this (P24-G 2; the engine's
                          # own bleeding-time scale, the ruling's "10 game minutes")
WASH_R = 15.0             # tiles: a dirty rag is washed at a known water source this near (P24-G 2)
SOURCE_RETRY_MIN = 10.0   # game minutes a source a wash or a fill found dry or gone is left out (a judgment)
KINDS = ("bandage", "rag", "dirty")              # care_kind's order of choice
CLEAN_BANDAGES = ("Bandage", "AlcoholBandage", "Bandaid")
CLEAN_RAGS = ("RippedSheets", "AlcoholRippedSheets", "DenimStrips", "LeatherStrips")
COTTON_RX = re.compile(r"\.(Tshirt|Shirt|Dress|Skirt|TankTop|Tanktop|Socks|Boxers|Briefs|Underpants)(_|$)")
TOOL_WORDS = ("Denim", "Leather")                # RipDenimClothing's fabrics: scissors or a knife (#4300)
RIP_REFUSALS = ("worn", "not cotton", "needs tool")   # a rip refused so never succeeds on that item
DRY_REASONS = ("no source", "no water")          # a wash or fill refused so leaves its source out a while
FAILED = ("failed", "timeout", "rejected")

__all__ = ["Care", "care_kind", "rippable", "water_sources", "CARE_RETRY_MIN", "DIRTY_RAG_MIN", "WASH_R",
           "SOURCE_RETRY_MIN", "KINDS"]


def care_kind(full_type):
    """What a bandage item is by its name: `bandage` (a clean bandage), `rag` (a clean ripped sheet or strip),
    `dirty` (a type naming `Dirty`: life 0), else None."""
    name = (full_type or "").rsplit(".", 1)[-1]
    if "Dirty" in name and any(name.startswith(w) for w in CLEAN_BANDAGES + CLEAN_RAGS):
        return "dirty"
    if name in CLEAN_BANDAGES:
        return "bandage"
    if name in CLEAN_RAGS:
        return "rag"
    return None


def rippable(full_type):
    """The cotton-garment name guess: a T-shirt, shirt, dress, skirt, tank top, sock or underwear naming neither denim
    nor leather."""
    ft = full_type or ""
    return bool(COTTON_RX.search(ft)) and not any(w in ft for w in TOOL_WORDS)


def water_sources(world, r, skip=()):
    """[(dist, (x, y, z), water record)] of the map's squares on the player's floor whose `water` record has water
    (`infinite`, or an `amount` above 0) within `r` tiles of the player by the square's centre, nearest first (ties by
    the square), `skip` left out."""
    floor = me_floor(world)
    mx, my = me_xy(world)
    out = []
    for sq, rec in world.map.items():
        w = rec.get("water")
        if sq[2] != floor or not isinstance(w, dict) or sq in skip:
            continue
        if not (w.get("infinite") is True or (isinstance(w.get("amount"), (int, float)) and w["amount"] > 0)):
            continue
        d = math.hypot(sq[0] + 0.5 - mx, sq[1] + 0.5 - my)
        if d <= r:
            out.append((d, sq, w))
    return sorted(out, key=lambda t: (t[0], t[1]))


def _num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


class Care:
    """The care branch's policy (the module docstring): `observe()` every tick, `choose(quiet)` when not busy."""

    def __init__(self, world, actions, clock=time.time):
        self.world = world
        self.actions = actions
        self.clock = clock
        self.last = None
        self.why = {}
        self.sends = {}    # item id -> its last care Action
        self.held_out = {}   # item id -> world minute its care action was refused (CARE_RETRY_MIN)
        self.dry = {}      # source square -> world minute a wash or fill there was refused for its water
        self._read = set()   # the aids whose end observe() has read

    # -- the policy seam (Survive sends through it, as the owner) -------------------------------------------------
    def busy(self):
        return self.last is not None and self.actions.current is self.last

    def send(self, cmd):
        action = self.actions.send(cmd)
        self.last = action
        self.sends[cmd.itemId] = action
        return action

    def observe(self):
        """Each care action's end, once: a refusal holds its item out for CARE_RETRY_MIN; a rip refused for good marks
        it `unrippable`; a wash refused for its water leaves its source out for SOURCE_RETRY_MIN."""
        now = self.world.world_minutes()
        for iid, a in list(self.sends.items()):
            if a.aid in self._read or not self.actions.done(a):
                continue
            self._read.add(a.aid)
            if a.state not in FAILED or (a.state == "failed" and a.reason == PREEMPTED):
                continue
            self.held_out[iid] = now
            if a.type == "rip" and a.reason in RIP_REFUSALS and iid in self.world.inventory:
                self.world.mark(iid, "unrippable")
            if a.type == "wash" and a.reason in DRY_REASONS:
                self.dry[(a.args.get("x"), a.args.get("y"), me_floor(self.world))] = now

    def dry_now(self):
        now = self.world.world_minutes()
        return {sq for sq, at in self.dry.items() if now - at < SOURCE_RETRY_MIN}

    # -- the reads ------------------------------------------------------------------------------------------------
    def _items(self):
        """{kind: [held ids]} by `care_kind`, an id held out by a refusal left out, ids ascending."""
        now = self.world.world_minutes()
        out = {k: [] for k in KINDS}
        for iid, it in self.world.inventory.items():
            k = care_kind(it.get("fullType"))
            if k is None or not item_id_ok(iid) or now - self.held_out.get(iid, -math.inf) < CARE_RETRY_MIN:
                continue
            out[k].append(iid)
        return {k: sorted(v) for k, v in out.items()}

    def _parts(self):
        return [p for p in ((self.world.body or {}).get("parts") or ()) if isinstance(p, dict) and _num(p.get("i"))]

    def _bleeding(self):
        """The bleeding unbandaged parts, worst first: deep, then the longest bleeding time, then the least index."""
        ps = [p for p in self._parts() if p.get("bleeding") is True and p.get("bandaged") is not True]
        return sorted(ps, key=lambda p: (p.get("deep") is not True, -(p.get("bleedingTime") or 0.0), p["i"]))

    def _spent(self):
        """The bandaged parts whose bandage is spent: `bandageLife` at or under 0, or `bandageDirty`."""
        return [p for p in self._parts() if p.get("bandaged") is True
                and ((_num(p.get("bandageLife")) and p["bandageLife"] <= 0) or p.get("bandageDirty") is True)]

    def _rip_item(self):
        """The least held id `rippable` names, never of the first sight, marked `unrippable` or held out."""
        now = self.world.world_minutes()
        marked = self.world.marked("unrippable")
        ids = [iid for iid, it in self.world.inventory.items() if item_id_ok(iid) and rippable(it.get("fullType"))
               and iid not in self.world.first_sight and iid not in marked
               and now - self.held_out.get(iid, -math.inf) >= CARE_RETRY_MIN]
        return min(ids) if ids else None

    # -- the choice -----------------------------------------------------------------------------------------------
    def choose(self, quiet):
        """The next care command, or None (the module docstring's order); `quiet`: no zombie within DISENGAGE_R."""
        w = self.world
        items = self._items()
        any_rag = any(items[k] for k in KINDS)
        bleeding = self._bleeding()
        if bleeding and w.can("bandage"):
            p = bleeding[0]
            bt = p.get("bleedingTime") or 0.0
            kinds = ("bandage", "rag", "dirty") if bt > DIRTY_RAG_MIN else ("bandage", "rag")
            k = next((k for k in kinds if items[k]), None)
            if k is not None:
                self.why = {"reason": "bleeding", "part": p["i"], "item": items[k][0], "kind": k, "bleedingTime": bt,
                            "deep": p.get("deep") is True}
                return Bandage(items[k][0], part=p["i"])
            if not any_rag and w.can("rip"):
                rip = self._rip_item()
                if rip is not None:
                    self.why = {"reason": "no_rag", "part": p["i"], "item": rip}
                    return Rip(rip)
        clean = items["bandage"] + items["rag"]
        spent = self._spent()
        if spent and clean and w.can("bandage"):
            p = spent[0]
            self.why = {"reason": "spent", "part": p["i"], "item": clean[0],
                        "kind": "bandage" if items["bandage"] else "rag", "life": p.get("bandageLife"),
                        "dirty": p.get("bandageDirty")}
            return Bandage(clean[0], part=p["i"])
        if items["dirty"] and quiet and w.can("wash"):
            src = water_sources(w, WASH_R, self.dry_now())
            if src:
                d, sq, rec = src[0]
                self.why = {"reason": "dirty_rag", "item": items["dirty"][0], "source": [sq[0], sq[1]], "dist": d,
                            "tainted": rec.get("tainted")}
                return Wash(items["dirty"][0], sq[0], sq[1])
        if not any_rag and w.can("rip"):
            rip = self._rip_item()
            if rip is not None:
                self.why = {"reason": "no_rag", "item": rip}
                return Rip(rip)
        self.why = {"bleeding": [p["i"] for p in bleeding], "spent": [p["i"] for p in spent],
                    "held": {k: len(v) for k, v in items.items()}} if (bleeding or spent or any_rag) else {}
        return None
