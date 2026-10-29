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
- `sent(action)` remembers the need's fill: its action, and the vessel's `item_changed` count at the send.
- `wants(marks, now)`: the goal layer's wants beside `water` (FILL_WANTS) on a tick the need found no water held: the
  one `why` names marked at `now`, the other dropped; `clear(marks)` drops both (a held drink found).
"""
import time

from agent.base.planner.care import DRY_REASONS
from agent.base.planner.policies import PREEMPTED, STUCK_REASONS, item_id_ok
from agent.base.pza1 import Fill
from agent.base.world import me_floor

FILL_SETTLE_S = 2.0      # wall seconds a done fill waits for its vessel's item_changed before it is read as filled (9 fix 2)
FILL_RETRY_MIN = 2.0     # game minutes from its end a vessel whose fill failed is left out (as care.CARE_RETRY_MIN)
FILL_WANTS = ("container", "water_source")   # the water chain's wants beside `water` (P24-G 3, P24-L)
SOURCE_FAILS = DRY_REASONS + ("not adjacent",) + STUCK_REASONS   # a fill failed so leaves its source out (Task 10
                         # fix 1, minor 5: a walk to it that failed, as one refused for its water), as a timeout does

__all__ = ["Water", "FILL_SETTLE_S", "FILL_RETRY_MIN", "FILL_WANTS", "SOURCE_FAILS"]


class Water:
    """The water chain (the module docstring). `world`, `actions` and `clock` are Survive's, re-bound each tick."""

    def __init__(self, world, actions, clock=time.time):
        self.world = world
        self.actions = actions
        self.clock = clock
        self.fills = {}   # vessel id -> {action, read, at, base, done_wall}: the need's fills (P24-G 3)
        self.why = None   # this tick: the plan's fill or want, logged in the need's why

    def check(self):
        """Each fill's end, once (the module docstring)."""
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
        d, sq, _ = clean[0]
        self.why = {"vessel": min(vessels), "source": [sq[0], sq[1]], "dist": d}
        return Fill(min(vessels), sq[0], sq[1])

    def sent(self, action):
        """Remember the need's fill: its action, and the vessel's `item_changed` count at the send (the settle's)."""
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
