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
   the bleeding time, #4298; the threshold is in the engine's raw wound-time units, `BodyPart.getBleedingTime()`,
   never game minutes: a plain scratch reads about 2 to 9 by `generateBleeding`, 0.3 to 0.6 of a scratch time of 7 to
   15, the Task 10 review's jar read, and a cut, a deep wound, glass or a bullet adds to it, so a plain scratch never
   takes a dirty rag and a cut or a deep wound usually does: Task 10 fix 1, minor 12). With no rag of any kind held,
   one held cotton garment is ripped for it (`no_rag`: `rippable` names it, never one of the inventory's first sight,
   `World.first_sight`, the clothes the character stands in, which the Lua refuses `worn`; on a PZA/1.5.2 log the item
   record's `worn` and `rip` say instead, Task 10 fix 2: only a `cotton` unworn one; nor one marked
   `unrippable`, a rip refused `worn`, `not cotton` or `needs tool`, `World.mark`: `Rip(itemId)`); a dirty rag held
   under the time rule falls through to the wash.
2. `replace`: a bandaged part whose `bandageLife` reached 0 or that reads `bandageDirty`, with a clean bandage or rag
   held: bandaged again with it (the Lua takes the old one off first).
3. `wash`: a dirty rag held, no zombie within DISENGAGE_R (Survive sets `quiet` each tick), and a known water source
   (`World.water_sources`: the map's square `water` record with water in it, on the player's floor, not refused
   lately) within WASH_R: `Wash(itemId, x, y)`, the Lua walking next to it (a wash does not test the water's taint,
   #4301).
Ruling P24-P (Plan 24 Task 12, E6: the health fell from 100 to 17.6 while a zombie was held, the one bandage sent on
the first tick with none): the bleeding step also runs with a threat held, whenever the nearest listed zombie is
beyond CARE_R and `tends_wound` answers (Survive's threat branch yields to it only then, so no other step sends).
A garment is ripped only for a bleeding part (Task 10 fix 1, the review's major 2: ruling P24-G 2's rip is the
wound's; a rip for stock destroyed looted clothing and, from above the need branch, superseded a running drink).
An item whose care action ended failed (never `superseded`), timed out or was rejected is left out for
CARE_RETRY_MIN game minutes (`World.world_minutes`); a wash refused `no source` or `no water` leaves its source out
(`World.mark_dry`, `world.SOURCE_RETRY_MIN`). A part a bandage ended `done` on is left out until a frame newer than
the one read with that end (`World.frame_n`; Task 10 fix 1, minor 6: the frame that reads the bandage on may follow
the done, and a stale one would put the next item on the same wound). Each step needs its skill in the hello's caps
(`World.can`); a PZA/1.4 frame's parts carry no `bleeding` (decoded None), so the branch reads no wound there and no
decision golden moves. `Care` is a `Policy` (Task 10 fix 1, minor 13): Survive sends through it as the owner, and its
`sent` records each item's action.

The item reads are names (`care_kind`, `rippable`): what `ISApplyBandage` reads, `Dirty` in the type (#4299); the
`RipClothing` recipe's cotton tag is in no dataset the repository carries, so `rippable` is a guess the Lua's refusal
corrects.
"""
import math
import re
import time

from agent.base.planner.policies import Policy, PREEMPTED, item_id_ok
from agent.base.pza1 import Bandage, Rip, Wash
from agent.base.world import me_floor

CARE_RETRY_MIN = 2.0      # game minutes an item whose care action was refused is left out (P24-G 2)
DIRTY_RAG_MIN = 10.0      # a dirty rag goes on a part only when its bleedingTime exceeds this (P24-G 2): the engine's
                          # raw wound-time units, #4298 (a plain scratch about 2-9, generateBleeding), never minutes
WASH_R = 15.0             # tiles: a dirty rag is washed at a known water source this near (P24-G 2)
CARE_R = 4.0              # tiles: a bleeding part is tended with a threat held while the nearest zombie is beyond this
                          # (ruling P24-P, Plan 24 Task 12: E6 bled from 100 to 17.6 health before its one bandage)
KINDS = ("bandage", "rag", "dirty")              # care_kind's order of choice
CLEAN_BANDAGES = ("Bandage", "AlcoholBandage", "Bandaid")
CLEAN_RAGS = ("RippedSheets", "AlcoholRippedSheets", "DenimStrips", "LeatherStrips")
COTTON_RX = re.compile(r"\.(Tshirt|Shirt|Dress|Skirt|TankTop|Tanktop|Socks|Boxers|Briefs|Underpants)(_|$)")
TOOL_WORDS = ("Denim", "Leather")                # RipDenimClothing's fabrics: scissors or a knife (#4300)
RIP_REFUSALS = ("worn", "not cotton", "needs tool")   # a rip refused so never succeeds on that item
DRY_REASONS = ("no source", "no water")          # a wash or fill refused so leaves its source out a while
FAILED = ("failed", "timeout", "rejected")

__all__ = ["Care", "care_kind", "rippable", "CARE_RETRY_MIN", "DIRTY_RAG_MIN", "WASH_R", "CARE_R", "KINDS",
           "DRY_REASONS"]


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


def _num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


class Care(Policy):
    """The care branch's policy (the module docstring): `observe()` every tick, `choose()` when not busy, `quiet` set
    by Survive each tick (no zombie within DISENGAGE_R: the wash's condition)."""

    def __init__(self, world, actions, clock=time.time):
        super().__init__(world, actions, clock)
        self.quiet = False
        self.sends = {}      # item id -> its last care Action
        self.held_out = {}   # item id -> world minute its care action was refused (CARE_RETRY_MIN)
        self.fresh = {}      # part index -> `World.frame_n` when its bandage's done was read (minor 6)
        self._read = set()   # the aids whose end observe() has read

    def sent(self, cmd, action):
        self.sends[cmd.itemId] = action

    def observe(self):
        """Each care action's end, once: a bandage done leaves its part out until a newer frame (`fresh`); a refusal
        holds its item out for CARE_RETRY_MIN; a rip refused for good marks it `unrippable`; a wash refused for its
        water leaves its source out (`World.mark_dry`). A part's `fresh` entry goes once a newer frame came."""
        n = self.world.frame_n
        self.fresh = {i: at for i, at in self.fresh.items() if at >= n}
        for iid, a in list(self.sends.items()):
            if a.aid in self._read or not self.actions.done(a):
                continue
            self._read.add(a.aid)
            if a.type == "bandage" and a.state == "done":
                self.fresh[a.args.get("part")] = n
            if a.state not in FAILED or (a.state == "failed" and a.reason == PREEMPTED):
                continue
            self.held_out[iid] = self.world.world_minutes()
            if a.reason == "in bag" and iid in self.world.inventory:
                self.world.mark(iid, "in_bag")   # Task 10 fix 2: the move could not be queued, a hard refusal
            elif a.type == "rip" and a.reason in RIP_REFUSALS and iid in self.world.inventory:
                self.world.mark(iid, "unrippable")
            if a.type == "wash" and a.reason in DRY_REASONS:
                self.world.mark_dry((a.args.get("x"), a.args.get("y"), me_floor(self.world)))

    # -- the reads ------------------------------------------------------------------------------------------------
    def _items(self):
        """{kind: [held ids]} by `care_kind`, an id held out by a refusal left out, ids ascending."""
        now = self.world.world_minutes()
        out = {k: [] for k in KINDS}
        barred = self.world.marked("in_bag")
        for iid, it in self.world.inventory.items():
            k = care_kind(it.get("fullType"))
            if (k is None or not item_id_ok(iid) or iid in barred
                    or now - self.held_out.get(iid, -math.inf) < CARE_RETRY_MIN):
                continue
            out[k].append(iid)
        return {k: sorted(v) for k, v in out.items()}

    def _parts(self):
        """The frame's part records, a part whose bandage ended done on this very frame left out (`fresh`)."""
        return [p for p in ((self.world.body or {}).get("parts") or ())
                if isinstance(p, dict) and _num(p.get("i")) and p["i"] not in self.fresh]

    def _bleeding(self):
        """The bleeding unbandaged parts, worst first: deep, then the longest bleeding time, then the least index."""
        ps = [p for p in self._parts() if p.get("bleeding") is True and p.get("bandaged") is not True]
        return sorted(ps, key=lambda p: (p.get("deep") is not True, -(p.get("bleedingTime") or 0.0), p["i"]))

    def _spent(self):
        """The bandaged parts whose bandage is spent: `bandageLife` at or under 0, or `bandageDirty`."""
        return [p for p in self._parts() if p.get("bandaged") is True
                and ((_num(p.get("bandageLife")) and p["bandageLife"] <= 0) or p.get("bandageDirty") is True)]

    def _rip_item(self):
        """The least held id that can be ripped, never one marked `unrippable` or `in_bag`, or held out. On a PZA/1.5.2
        hello's log (`World.item_fields`) the item record says: `rip` cotton and not `worn` (denim and leather need a
        tool the planner has no action for; absent is no class). On an older log the name guess `rippable` stands and
        the inventory's first sight (the clothes worn) is left out."""
        now = self.world.world_minutes()
        marked = self.world.marked("unrippable") | self.world.marked("in_bag")
        fields = self.world.item_fields()
        ids = [iid for iid, it in self.world.inventory.items() if item_id_ok(iid) and iid not in marked
               and (it.get("rip") == "cotton" and it.get("worn") is not True if fields
                    else rippable(it.get("fullType")) and iid not in self.world.first_sight)
               and now - self.held_out.get(iid, -math.inf) >= CARE_RETRY_MIN]
        return min(ids) if ids else None

    # -- the choice -----------------------------------------------------------------------------------------------
    def _wound(self, items, bleeding):
        """The bleeding step, `(command, why)` or (None, None): the worst bleeding part's bandage with the best held
        item, else with no rag of any kind held a garment's rip for it."""
        w = self.world
        if not bleeding or not w.can("bandage"):
            return None, None
        p = bleeding[0]
        bt = p.get("bleedingTime") or 0.0
        kinds = ("bandage", "rag", "dirty") if bt > DIRTY_RAG_MIN else ("bandage", "rag")
        k = next((k for k in kinds if items[k]), None)
        if k is not None:
            return Bandage(items[k][0], part=p["i"]), {"reason": "bleeding", "part": p["i"], "item": items[k][0],
                                                        "kind": k, "bleedingTime": bt, "deep": p.get("deep") is True}
        if not any(items[k] for k in KINDS) and w.can("rip"):
            rip = self._rip_item()
            if rip is not None:
                return Rip(rip), {"reason": "no_rag", "part": p["i"], "item": rip}
        return None, None

    def tends_wound(self):
        """The bleeding step would send now (ruling P24-P: Survive's threat branch yields to it beyond CARE_R)."""
        return self._wound(self._items(), self._bleeding())[0] is not None

    def choose(self):
        """The next care command, or None (the module docstring's order). Under a held threat (P24-P) Survive runs
        the branch only when `tends_wound` answers, so the bleeding step is the one that sends there."""
        w = self.world
        items = self._items()
        any_rag = any(items[k] for k in KINDS)
        bleeding = self._bleeding()
        cmd, why = self._wound(items, bleeding)
        if cmd is not None:
            self.why = why
            return cmd
        clean = items["bandage"] + items["rag"]
        spent = self._spent()
        if spent and clean and w.can("bandage"):
            p = spent[0]
            self.why = {"reason": "spent", "part": p["i"], "item": clean[0],
                        "kind": "bandage" if items["bandage"] else "rag", "life": p.get("bandageLife"),
                        "dirty": p.get("bandageDirty")}
            return Bandage(clean[0], part=p["i"])
        if items["dirty"] and self.quiet and w.can("wash"):
            src = w.water_sources(WASH_R)
            if src:
                d, sq, rec = src[0]
                self.why = {"reason": "dirty_rag", "item": items["dirty"][0], "source": [sq[0], sq[1]], "dist": d,
                            "tainted": rec.get("tainted")}
                return Wash(items["dirty"][0], sq[0], sq[1])
        self.why = {"bleeding": [p["i"] for p in bleeding], "spent": [p["i"] for p in spent],
                    "held": {k: len(v) for k, v in items.items()}} if (bleeding or spent or any_rag) else {}
        return None
