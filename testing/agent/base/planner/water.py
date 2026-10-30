"""The water chain (Plan 24 Task 10, ruling P24-G 3 as P24-L narrowed it; lifted out of `survive.Survive` at Plan 24
Task 21's refactor A, the Task 10 review's ruling 7, shaped like `care.py`): `Water`, the need branch's second and
third steps when no `water` item is held, which `survive.Survive._need` runs after its drink pick.

- `plan(by_use)`, the second step: a held `container` (`by_use`, the least id; one whose fill is running, settling or
  failed within FILL_RETRY_MIN left out) and the nearest known clean water source on the player's floor
  (`World.water_sources`, the dry and the tainted ones left out): `Fill(vessel, x, y)`, the Lua walking next to it.
  None without the `fill` skill (`World.can`), a free vessel or a clean source; `why` says which: `want` "container"
  with no vessel held at all (the third step: the goal layer's loot), `held_out` with every held vessel left out,
  `want` "water_source" with a vessel and no clean source known (P24-L: the vessel is kept, and the goal layer may
  seek a building's sink). Never a tainted source (P24-L, Task 10 fix 1: the Lua's consume refuses tainted water,
  `W.drinkable`, so a tainted fill lost the vessel for the session).
- `check()`, each fill's end, once: done marks its vessel `filled` (or `tainted`, the act's result or its fluid
  saying so: the source is then kept in `World.tainted_sources`), so `by_use` reads it water and the next tick drinks
  it; 9 fix 2: a done fill waits for the engine's own re-read of the vessel (`item_changed`, `World.changes` past the
  count at the send) or FILL_SETTLE_S of wall time before it is read (`settling()` names the vessels waiting, and the
  need holds on them). A failure for its source (SOURCE_FAILS: refused for its water, a walk there that failed `not
  adjacent` or for a STUCK_REASONS reason, Task 10 fix 1, minor 5; or a timeout) leaves the source out
  (`World.mark_dry`, `world.SOURCE_RETRY_MIN`, the store the care's wash shares) and frees the vessel for the next
  source; any other end but a supersede leaves the vessel out of the plan for FILL_RETRY_MIN game minutes from the
  minute its end was read (never from the send: a 30 s walk then coming back at once).
- Ruling P24-AW (survival iteration 12, Plan 24 Task 36; E10: 55 of 63 fills rejected `no source`, each sent with
  the source 60.04 to 159.03 tiles off, a square the client held no grid square for, #4375): the plan takes the
  nearest clean source within the client's loaded grid (`loaded`: the goal legs' `goals.leg_max` off the World's
  `me.loadedWidth`, ruling P24-AI, read square by its Chebyshev distance, the grid being one of chunks); within
  FILL_WALK_R of it the `Fill` goes as before (the Lua walks next to it); farther, a `WalkTo` at a walk to the open
  square beside it nearest the player (`World.reachable_adjacent`, else the source's own centre) goes first, the need
  holding while it runs, and the fill on the tick it is within FILL_WALK_R; a walk that failed (never one superseded)
  leaves its source out as a fill's walk failure does (`World.mark_dry`). A source beyond the grid is never sent: with
  every clean source out of it the vessel is kept and the want names `water_source` (`why` `unloaded`, their count).
- `sent(action)` remembers the need's fill: its action, and the vessel's `item_changed` count at the send; or its walk
  to a source (`walk`).
- `wants(marks, now)`: the goal layer's wants beside `water` (FILL_WANTS) on a tick the need found no water held: the
  one `why` names marked at `now`, the other dropped; `clear(marks)` drops both (a held drink found).
"""
import time

from agent.base.planner.care import DRY_REASONS
from agent.base.planner.goals import leg_max
from agent.base.planner.policies import PREEMPTED, STUCK_REASONS, centre, item_id_ok
from agent.base.pza1 import Fill, WalkTo
from agent.base.world import me_floor, me_xy

FILL_SETTLE_S = 2.0      # wall seconds a done fill waits for its vessel's item_changed before it is read as filled (9 fix 2)
FILL_RETRY_MIN = 2.0     # game minutes from its end a vessel whose fill failed is left out (as care.CARE_RETRY_MIN)
FILL_WANTS = ("container", "water_source")   # the water chain's wants beside `water` (P24-G 3, P24-L)
SOURCE_FAILS = DRY_REASONS + ("not adjacent",) + STUCK_REASONS   # a fill failed so leaves its source out (Task 10
                         # fix 1, minor 5: a walk to it that failed, as one refused for its water), as a timeout does
FILL_WALK_R = 20.0       # tiles: the farthest source a `Fill` is sent to (ruling P24-AW, a judgment: the Lua's own walk
                         # next to it, no radius of its own); a loaded source farther off is walked to first
FILL_NEAR_R = 2.0        # tiles: that walk ends beside the source (ruling P24-AW: "a walkTo leg to within 2 tiles"), on
                         # the open square next to it nearest the player

__all__ = ["Water", "FILL_SETTLE_S", "FILL_RETRY_MIN", "FILL_WANTS", "SOURCE_FAILS", "FILL_WALK_R", "FILL_NEAR_R",
           "loaded"]


def loaded(world, sq):
    """Ruling P24-AW: square `sq` (x, y, z) lies within the client's loaded grid as the goal legs read it (`goals.leg_max`
    off `me.loadedWidth`, ruling P24-AI: half the grid less a chunk; LEG_MAX with no width read), by its Chebyshev
    distance from the player's square (the grid is one of chunks, square on both axes, #4375)."""
    mx, my = me_xy(world)
    return max(abs(sq[0] + 0.5 - mx), abs(sq[1] + 0.5 - my)) <= leg_max(world)


class Water:
    """The water chain (the module docstring). `world`, `actions` and `clock` are Survive's, re-bound each tick."""

    def __init__(self, world, actions, clock=time.time):
        self.world = world
        self.actions = actions
        self.clock = clock
        self.fills = {}   # vessel id -> {action, read, at, base, done_wall}: the need's fills (P24-G 3)
        self.walk = None  # (walk Action, source square) of the need's walk to a far source until its end is read (P24-AW)
        self.why = None   # this tick: the plan's fill or want, logged in the need's why

    def check(self):
        """Each fill's end, once, and the walk's to a far source (the module docstring)."""
        if self.walk is not None and self.actions.done(self.walk[0]):
            a, sq = self.walk
            self.walk = None
            if a.state != "done" and not (a.state == "failed" and a.reason == PREEMPTED):
                self.world.mark_dry(sq)   # P24-AW: a walk to it that failed leaves the source out (SOURCE_RETRY_MIN)
        now = self.world.world_minutes()
        for iid, f in list(self.fills.items()):
            a = f["action"]
            if f["read"]:
                if now - f["at"] >= FILL_RETRY_MIN:
                    del self.fills[iid]
                continue
            if not self.actions.done(a):
                continue
            if a.state == "done" and iid in self.world.inventory:
                # 9 fix 2: the engine's own read (item_changed) follows the fill by a moment; wait for it, or for
                # FILL_SETTLE_S of wall time, before the vessel is read as filled
                f.setdefault("done_wall", a.ended_wall if a.ended_wall is not None else self.clock())
                res = a.result if isinstance(a.result, dict) else {}
                it = self.world.inventory[iid]
                event = self.world.changes.get(iid, 0) > f["base"]
                if not event and self.clock() - f["done_wall"] < FILL_SETTLE_S:
                    continue
                tainted = res.get("tainted") is True or it.get("fluid") == "TaintedWater"
                if tainted:
                    self.world.tainted_sources.add((a.args.get("x"), a.args.get("y"), me_floor(self.world)))
                if not event:
                    self.world.mark(iid, "tainted" if tainted else "filled")
                del self.fills[iid]
                continue
            if a.state == "done" or (a.state == "failed" and a.reason == PREEMPTED):
                del self.fills[iid]
                continue
            if a.state == "timeout" or a.reason in SOURCE_FAILS:
                self.world.mark_dry((a.args.get("x"), a.args.get("y"), me_floor(self.world)))
                del self.fills[iid]
                continue
            f["read"], f["at"] = True, now

    def settling(self):
        """The vessels whose done fill waits for its `item_changed` (9 fix 2), ids sorted as strings."""
        return sorted((i for i, f in self.fills.items() if "done_wall" in f), key=str)

    def plan(self, by_use):
        """The second step's `Fill`, else None (the module docstring), `why` set."""
        if not self.world.can("fill"):
            return None
        held = [i for i in by_use["container"] if item_id_ok(i)]
        if not held:
            self.why = {"want": "container"}
            return None
        vessels = [i for i in held if i not in self.fills]
        if not vessels:
            self.why = {"held_out": held}
            return None
        clean = [s for s in self.world.water_sources() if s[2].get("tainted") is not True]
        if not clean:
            self.why = {"vessel": min(vessels), "source": None, "want": "water_source"}
            return None
        near = [s for s in clean if loaded(self.world, s[1])]   # P24-AW: never a source the client holds no square of
        if not near:
            self.why = {"vessel": min(vessels), "source": None, "want": "water_source", "unloaded": len(clean)}
            return None
        d, sq, _ = near[0]
        self.why = {"vessel": min(vessels), "source": [sq[0], sq[1]], "dist": d}
        if d <= FILL_WALK_R:
            return Fill(min(vessels), sq[0], sq[1])
        beside = self.world.reachable_adjacent(centre(sq), sq[2])   # P24-AW: the walk first, beside the source
        to = beside[0] if beside else sq
        self.why["walk"] = [to[0], to[1]]
        return WalkTo(*centre(to), "walk")

    def sent(self, action):
        """Remember the need's fill: its action, and the vessel's `item_changed` count at the send (the settle's); or
        its walk to a far source (P24-AW), the source the plan's `why` named."""
        if action.type == "walkTo":
            src = (self.why or {}).get("source")
            self.walk = (action, (src[0], src[1], me_floor(self.world)))
            return
        iid = action.args.get("itemId")
        self.fills[iid] = {"action": action, "read": False, "at": None, "base": self.world.changes.get(iid, 0)}

    def wants(self, marks, now):
        """The goal layer's wants beside `water`: the one `why` names marked in `marks` at `now`, the other dropped."""
        want = (self.why or {}).get("want")
        for u in FILL_WANTS:
            if u == want:
                marks[u] = now
            else:
                marks.pop(u, None)

    @staticmethod
    def clear(marks):
        """A held drink found: both wants dropped."""
        for u in FILL_WANTS:
            marks.pop(u, None)
