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
beyond CARE_R and `tends_wound` answers (Survive's threat branch yields to it only then, so no other step sends);
Task 12 fix 1 gives the yield its hysteresis (`survive.Survive._care_yields`): a bandage starts beyond CARE_R only
with the nearest not closing over CARE_STILL_TICKS ticks and no flee leg running from a chaser, and a running one is
superseded only inside CARE_HOLD_R. The ride (ruling P24-U, Task 12 fix 1; PZA/1.5.3's `keepMoving`, ruling P24-R):
under a running flee leg (a steer, or a walk on an open line) with the nearest zombie beyond RIDE_R or no zombie
chasing, Survive sets `ride_now` and the bleeding step bandages the worst bleeding part above the legs (index under
LEG_FIRST; a leg part takes the standing bandage only, under the hysteresis) with `Bandage(itemId, part,
keepMoving=True)`, no rip; the ride is tracked by its own act lines (`ride`, `riding`): the Care is busy while it runs
whatever was sent since (the flee's re-aims are new legs that keep it), and a ride the engine stopped (`failed
stopped`) holds no item out.
A garment is ripped from the choose only for a bleeding part (Task 10 fix 1, the review's major 2: ruling P24-G 2's
rip is the wound's; a rip for stock destroyed looted clothing and, from above the need branch, superseded a running
drink). The rag stock (ruling P24-AB, Plan 24 Task 21; E8, `e_day_8-20261029-174023`: the second bite bled 73 game
minutes to the death with no dressing held, its last 31 standing still with the only zombie idle 8.3 tiles off; Angus:
"he will need a couple clean rags, which he can get from ripping clothes and washing the resulting rags as
necessary"): `stock()` answers `Rip(itemId)` of the held unworn cotton garment (`_rip_item`) while fewer than
RAG_STOCK clean dressings (`bandage` and `rag` items) are held, the build announces `rip` and no zombie is within
DISENGAGE_R (`quiet`); Survive tries it only on an idle tick, behind the need, the load and the night and before the
goal, with no action running (so it never supersedes a drink, a fill or a goal's walk or loot: Task 10's objection),
its line the care branch's (`why` `stock`). `wants_dressing()`: a part bleeds, no item the bleeding step may put on
it is held (nor a dirty rag to wash) and no garment can be ripped: Survive then marks the want `bandage`, which the
view lists and the goal layer's loot takes first (`goals.wanted_uses`). The worn garment's unwear and rip waits for
the Lua's unwear (PZA/1.6 has `wear` only).
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
CARE_HOLD_R = CARE_R - 1.0   # tiles: a running bandage is superseded only with the nearest zombie inside this (Task
                          # 12 fix 1, the review's ruling: CARE_R the start line, this the supersede line; at CARE_R
                          # alone a chaser at about 4 tiles alternated the bandage and the steer every tick)
CARE_STILL_TICKS = 2      # threat ticks over which the nearest zombie's distance must not have fallen before a bandage
                          # starts under a held threat (Task 12 fix 1: the yield's start reads it not closing)
KINDS = ("bandage", "rag", "dirty")              # care_kind's order of choice
CLEAN_BANDAGES = ("Bandage", "AlcoholBandage", "Bandaid")
CLEAN_RAGS = ("RippedSheets", "AlcoholRippedSheets", "DenimStrips", "LeatherStrips")
COTTON_RX = re.compile(r"\.(Tshirt|Shirt|Dress|Skirt|TankTop|Tanktop|Socks|Boxers|Briefs|Underpants)(_|$)")
TOOL_WORDS = ("Denim", "Leather")                # RipDenimClothing's fabrics: scissors or a knife (#4300)
RIP_REFUSALS = ("worn", "not cotton", "needs tool")   # a rip refused so never succeeds on that item
DRY_REASONS = ("no source", "no water")          # a wash or fill refused so leaves its source out a while
FAILED = ("failed", "timeout", "rejected")
LEG_FIRST = 11            # the first leg part (UpperLeg_L; 11-16 the thighs, shins and feet): a bandage on one stops on
                          # a walk, so the Lua rejects it `leg part` with keepMoving (PZA/1.5.3, ruling P24-R)
RIDE_R = 6.0              # tiles: a bandage rides a running flee leg only with the nearest zombie beyond this, or with
                          # no zombie chasing (ruling P24-U, Task 12 fix 1: the ride holds the leg to a walk)
RIDE_FREE = ("stopped",)  # a ride failed so was stopped by the engine (a run, an aim, a hit): its item is not held out
RIDE_RETRY_S = 3.0        # seconds after a stopped ride before the care rides again (Task 12 fix 2, the re-review's major
                          # 2: the same ride re-chosen at once was cooled and the tick fell through to a drink)
RAG_STOCK = 2             # clean dressings (bandages and clean rags) the care keeps, ripping one unworn cotton garment
                          # on an idle tick while fewer are held (ruling P24-AB; Angus: "a couple clean rags")

__all__ = ["Care", "care_kind", "rippable", "CARE_RETRY_MIN", "DIRTY_RAG_MIN", "WASH_R", "CARE_R", "CARE_HOLD_R",
           "CARE_STILL_TICKS", "KINDS", "DRY_REASONS", "LEG_FIRST", "RIDE_R", "RIDE_RETRY_S", "RAG_STOCK"]


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
        self.ride = None     # the last bandage sent with keepMoving (P24-U), tracked by its own act lines
        self.ride_stopped_at = -math.inf   # the wall of the last ride the engine stopped (RIDE_RETRY_S)
        self.ride_now = False   # Survive sets it on a tick the threat yields to a ride: the bleeding step rides

    def sent(self, cmd, action):
        self.sends[cmd.itemId] = action
        if cmd.TYPE == "bandage" and cmd.keepMoving:
            self.ride = action

    def riding(self):
        """The riding bandage while it runs (not yet terminal), else None: the flee's leg sent since keeps it."""
        return self.ride if self.ride is not None and not self.actions.done(self.ride) else None

    def busy(self):
        """The Policy's rule, or a ride running (its leg, or a re-aimed one, is the current action meanwhile)."""
        return super().busy() or self.riding() is not None

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
            if a.state == "failed" and a.reason in RIDE_FREE and a.args.get("keepMoving") is True:
                self.ride_stopped_at = self.clock()
                continue   # P24-U: the engine stopped the ride; the item is good
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
    def _wound(self, items, bleeding, ride=False):
        """The bleeding step, `(command, why)` or (None, None): the worst bleeding part's bandage with the best held
        item, else with no rag of any kind held a garment's rip for it. With `ride` (P24-U) the worst bleeding part
        above the legs (index under LEG_FIRST) is bandaged with keepMoving, never a rip (a rip stops the leg)."""
        w = self.world
        if ride:
            bleeding = [p for p in bleeding if p["i"] < LEG_FIRST]
        if not bleeding or not w.can("bandage"):
            return None, None
        p = bleeding[0]
        bt = p.get("bleedingTime") or 0.0
        kinds = ("bandage", "rag", "dirty") if bt > DIRTY_RAG_MIN else ("bandage", "rag")
        k = next((k for k in kinds if items[k]), None)
        if k is not None:
            why = {"reason": "bleeding", "part": p["i"], "item": items[k][0], "kind": k, "bleedingTime": bt,
                   "deep": p.get("deep") is True}
            if ride:
                why["ride"] = True
            return Bandage(items[k][0], part=p["i"], keepMoving=ride), why
        if not ride and not any(items[k] for k in KINDS) and w.can("rip"):
            rip = self._rip_item()
            if rip is not None:
                return Rip(rip), {"reason": "no_rag", "part": p["i"], "item": rip}
        return None, None

    def stock(self):
        """The rag stock's rip (ruling P24-AB, the module docstring), `(command, why)` or (None, None): fewer than
        RAG_STOCK clean dressings held, an unworn cotton garment held, `rip` announced, `quiet`. Survive calls it only
        on an idle tick."""
        if not (self.quiet and self.world.can("rip")):
            return None, None
        items = self._items()
        held = len(items["bandage"]) + len(items["rag"])
        if held >= RAG_STOCK:
            return None, None
        rip = self._rip_item()
        if rip is None:
            return None, None
        return Rip(rip), {"reason": "stock", "item": rip, "dressings": held, "stock": RAG_STOCK}

    def wants_dressing(self):
        """A part bleeds (unbandaged), `bandage` announced, and the bleeding step has nothing to put on it: no clean
        bandage or rag, no dirty rag the time rule allows, no dirty rag to wash, no garment to rip (P24-AB: the want
        `bandage`)."""
        if not self.world.can("bandage"):
            return False
        bleeding = self._bleeding()
        if not bleeding:
            return False
        items = self._items()
        return self._wound(items, bleeding)[0] is None and not items["dirty"]

    def tends_wound(self):
        """The bleeding step would send now (ruling P24-P: Survive's threat branch yields to it beyond CARE_R)."""
        return self._wound(self._items(), self._bleeding())[0] is not None

    def rides_wound(self):
        """The bleeding step would ride now (P24-U): a part above the legs bleeds and a bandage item is held, and no
        ride was stopped by the engine within RIDE_RETRY_S (Task 12 fix 2)."""
        if self.clock() - self.ride_stopped_at < RIDE_RETRY_S:
            return False
        return self._wound(self._items(), self._bleeding(), ride=True)[0] is not None

    def choose(self):
        """The next care command, or None (the module docstring's order). Under a held threat (P24-P) Survive runs
        the branch only when `tends_wound` answers, so the bleeding step is the one that sends there."""
        w = self.world
        items = self._items()
        any_rag = any(items[k] for k in KINDS)
        bleeding = self._bleeding()
        cmd, why = self._wound(items, bleeding, ride=self.ride_now)
        if cmd is not None or self.ride_now:
            self.why = why or {}
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
