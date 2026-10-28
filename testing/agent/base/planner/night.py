"""The night instinct (Plan 23 Task 12, spec § 7, P23-9): when tired or late, shelter in a known interior and sleep.

`Night` is a `policies.Policy`, one action at a time; `survive.Survive` runs it as its `night` branch, after `threat`,
`need` and `load` (so a heavy load is dropped before the sleep) and before the goal (Task 13; until then `forage`
and `explore`).

- The want (`wants()`): the frame's `stats.fatigue` above TIRED_T 0.6 (the first TIRED moodle), or the frame's
  `me.hour` at LATE_HOUR 22.0 or later with fatigue above LATE_FATIGUE 0.3. A frame with no `hour` (a log older than
  PZA/1.2) reads as daytime. A sleep that ended `done` with its `fatigueAfter` under TIRED_T clears the want (`rested`)
  while the frame's fatigue reads under TIRED_T, so a character woken at 23:00 with fatigue above LATE_FATIGUE does
  not lie down again at once; the first frame at TIRED_T or above ends the clearance.
- Inside (`inside()`): the player's square `(floor(x), floor(y), floor(z))` is in `world.map` with a `room` that is
  not None. Every frame inside adds the square's building to `visited`.
- The shelter (`choose()`), with a zombie within DANGER_R sending nothing (the threat branch owns it): inside, `Sleep()`
  at once (no walk), except while a plan's `close` step is due. Outside, a plan: of `world.interiors()`, the buildings
  (a building id that is not None) with at least one door square in `world.doors_of(b)` on the player's floor and not
  shunned, ranked visited first (a building the character has stood in), then by the distance from the player to its
  nearest interior square on that floor, ties by the id. Its door: a door that read open first, then one that read
  neither locked nor barricaded, then any, each nearest the player. Its interior square: the building's interior square
  on the floor nearest the door square, the door square itself only when it is the only one (so the close is one step
  away and the character does not stand in the doorway). The steps, each one `Action`:
  (a) `approach`: `WalkTo` at a walk to the centre of the door square's adjacent square, skipped when the player
      already stands within one square (Chebyshev) of the door, as the Lua's interact would be;
  (b) `open`: `Interact(dx, dy, "open")`, skipped when the door read open at its last record;
  (c) `enter`: `WalkTo` at a walk to the interior square's centre;
  (d) `close`: `Interact(dx, dy, "close")` on the door;
  (e) `sleep`: `Sleep()` (inside by then).
  The adjacent square (ruling, Task 12): the first of `world.reachable_adjacent(door, z)` (nearest the player first)
  that has no room, the outside square; when none has (a closed door blocks its own edge, so the square across it is
  never listed as reachable, and every diagonal through the door's corner reads blocked), the nearest mapped,
  non-solid neighbour with no room, the Lua interact's own approach rule (`approach` in `PZAgent_SkillsWorld.lua`
  reads no edge). Cost if wrong: an approach to the wrong side of a wall, which the open then fails `not adjacent`,
  shunning the building.
- A step's end (`observe()`): `done` advances the plan; `failed` for a reason in SHUN_REASONS (`locked`, `not
  adjacent`, `no door`, and the walk reasons `policies.STUCK_REASONS`) shuns the plan's building for SHUN_MIN 120 game
  minutes (`shunned {building: gameMin}`) and drops the plan, so the next choose tries the next building; a `close`
  that fails otherwise is passed over (the character is inside: it sleeps with the door as it is); a `superseded` step
  (a higher branch's send) is sent again; any other end keeps the step, and Survive's failed-action cooldown passes the
  branch over for its ticks. A sleep `rejected` or `failed` `not safe` (a zombie visible, chasing or very close; the
  threat branch owns one within DANGER_R, one beyond it is no threat but blocks the sleep) holds the branch for
  NOT_SAFE_S 30 wall seconds from the refusal's `ended_wall` (`hold_until`: Survive answers the branch with no command, so no lower branch walks the
  character out of its shelter); a sleep `done` records `last_sleep` (`gameMin` and the result's `sleptH`,
  `fatigueBefore`, `fatigueAfter`, `bedType`) and sets `rested` when `fatigueAfter` (else the frame's fatigue) reads
  under TIRED_T.
- `want_shelter`: True while the branch wants and knows no building to shelter in (outside, no ranked building); the
  goal layer's `Shelter` (Task 13) reads it off `survive.night`. False otherwise.
- `why` (logged by Survive under the branch): `step` (the step chosen, or None), `building`, `shunned` (the buildings
  shunned now, sorted), plus `threat`, `hold` (wall seconds left), `inside` and `want_shelter` when they apply.
"""
import json
import math
import time

from agent.base.planner.policies import DANGER_R, STUCK_REASONS, PREEMPTED, Policy, me_floor, me_xy, zdist
from agent.base.pza1 import Interact, Sleep, WalkTo

TIRED_T = 0.6         # the first TIRED moodle fires above 0.6 [#2279]
LATE_HOUR = 22.0      # from this hour of day ...
LATE_FATIGUE = 0.3    # ... the branch wants at a fatigue above this
SHUN_MIN = 120        # game minutes a building whose shelter step failed is passed over
NOT_SAFE_S = 30.0     # wall seconds the branch holds after a sleep refused `not safe`
SHUN_REASONS = ("locked", "not adjacent", "no door") + STUCK_REASONS
NOT_SAFE = "not safe"
STEPS = ("approach", "open", "enter", "close", "sleep")

__all__ = ["Night", "TIRED_T", "LATE_HOUR", "LATE_FATIGUE", "SHUN_MIN", "NOT_SAFE_S", "SHUN_REASONS", "STEPS"]


def _num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _centre(sq):
    return sq[0] + 0.5, sq[1] + 0.5


class Night(Policy):
    def __init__(self, world, actions, clock=time.time):
        super().__init__(world, actions, clock)
        self.want_shelter = False
        self.shunned = {}       # building -> the gameMin it was shunned at
        self.visited = set()    # the buildings whose interior the character has stood in
        self.last_sleep = None  # {gameMin, sleptH, fatigueBefore, fatigueAfter, bedType} of the last sleep done
        self.rested = False     # the last sleep ended under TIRED_T: no want while fatigue stays under it
        self.hold_until = None  # wall until which a sleep refused `not safe` holds the branch
        self.plan = None        # {building, door, inside, step} while sheltering
        self._read = None       # the last action whose end observe() has read

    # ---------------------------------------------------------------- reading the frame
    def fatigue(self):
        f = (self.world.stats or {}).get("fatigue")
        return f if _num(f) else 0.0

    def hour(self):
        h = (self.world.me or {}).get("hour")
        return h if _num(h) else None

    def wants(self):
        f = self.fatigue()
        if self.rested and f < TIRED_T:
            return False
        if f > TIRED_T:
            return True
        h = self.hour()
        return h is not None and h >= LATE_HOUR and f > LATE_FATIGUE

    def _square(self):
        me = self.world.me or {}
        x, y = me.get("x"), me.get("y")
        if not (_num(x) and _num(y)):
            return None
        return int(math.floor(x)), int(math.floor(y)), me_floor(self.world)

    def inside(self):
        s = self.world.map.get(self._square())
        return s is not None and s.get("room") is not None

    def shunned_now(self):
        now = self.world.game_min or 0.0
        return {b for b, at in self.shunned.items() if now - at < SHUN_MIN}

    def holding(self):
        """Wall seconds the branch still holds after a sleep refused `not safe`, else 0.0."""
        if self.hold_until is None:
            return 0.0
        return max(0.0, self.hold_until - self.clock())

    def idle(self):
        """The branch does not want: no plan, no shelter wanted."""
        self.plan, self.want_shelter = None, False
        self.why = {"wants": False}

    # ---------------------------------------------------------------- the plan
    def _dist(self, sq):
        mx, my = me_xy(self.world)
        c = _centre(sq)
        return math.hypot(c[0] - mx, c[1] - my)

    def _door_rank(self, sq):
        d = self.world.map[sq].get("door") or {}
        state = 0 if d.get("open") else (2 if d.get("locked") or d.get("barricaded") else 1)
        return state, self._dist(sq), sq

    def _plan_for(self, b, rooms, z):
        doors = [sq for sq in self.world.doors_of(b) if sq[2] == z]
        inner = [sq for sq in rooms if sq[2] == z]
        if not doors or not inner:
            return None
        door = min(doors, key=self._door_rank)
        deeper = [sq for sq in inner if sq != door] or inner
        target = min(deeper, key=lambda sq: (math.hypot(sq[0] - door[0], sq[1] - door[1]), sq))
        return {"building": b, "door": door, "inside": target, "step": "approach",
                "rank": (b not in self.visited, min(self._dist(sq) for sq in inner), json.dumps(b))}

    def _new_plan(self):
        z = me_floor(self.world)
        skip = self.shunned_now()
        plans = [self._plan_for(b, rooms, z) for b, rooms in self.world.interiors().items()
                 if b is not None and b not in skip]
        plans = [p for p in plans if p is not None]
        if not plans:
            return None
        best = min(plans, key=lambda p: p["rank"])
        del best["rank"]
        return best

    def _approach(self, door):
        """The square the approach walks to (the module docstring's ruling), None when the door has no free
        neighbour outside."""
        for sq in self.world.reachable_adjacent((door[0], door[1]), door[2]):
            if self.world.map[sq].get("room") is None:
                return sq
        out = []
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                sq = (door[0] + dx, door[1] + dy, door[2])
                s = self.world.map.get(sq)
                if sq == door or s is None or s.get("solid") or s.get("room") is not None:
                    continue
                out.append((self._dist(sq), sq))
        return min(out)[1] if out else None

    def _shun(self, building):
        self.shunned[building] = self.world.game_min or 0.0
        self.plan = None

    def _near_door(self, door):
        sq = self._square()
        return sq is not None and sq[2] == door[2] and max(abs(sq[0] - door[0]), abs(sq[1] - door[1])) <= 1

    def _door_open(self, door):
        d = (self.world.map.get(door) or {}).get("door") or {}
        return bool(d.get("open"))

    def _advance(self):
        self.plan["step"] = STEPS[STEPS.index(self.plan["step"]) + 1]

    # ---------------------------------------------------------------- the policy
    def observe(self):
        sq = self._square()
        s = self.world.map.get(sq) if sq is not None else None
        if s is not None and s.get("room") is not None and s.get("building") is not None:
            self.visited.add(s["building"])
        if self.rested and self.fatigue() >= TIRED_T:
            self.rested = False
        a = self.last
        if a is None or a is self._read or not self.actions.done(a):
            return
        self._read = a
        if a.type == "sleep":
            self._sleep_ended(a)
            return
        if self.plan is None or (a.state == "failed" and a.reason == PREEMPTED):
            return
        if a.state == "done":
            self._advance()
        elif a.state == "failed" and a.reason in SHUN_REASONS:
            self._shun(self.plan["building"])
        elif self.plan["step"] == "close":
            self._advance()   # inside: a close that failed otherwise is passed over, the sleep goes ahead

    def _sleep_ended(self, a):
        if a.state in ("rejected", "failed") and a.reason == NOT_SAFE:
            ended = a.ended_wall if _num(a.ended_wall) else self.clock()
            self.hold_until = ended + NOT_SAFE_S   # from the refusal's own wall, not the tick that read it
        elif a.state == "done":
            res = a.result if isinstance(a.result, dict) else {}
            self.last_sleep = {"gameMin": self.world.game_min, "sleptH": res.get("sleptH"),
                               "fatigueBefore": res.get("fatigueBefore"), "fatigueAfter": res.get("fatigueAfter"),
                               "bedType": res.get("bedType")}
            after = res.get("fatigueAfter")
            self.rested = (after if _num(after) else self.fatigue()) < TIRED_T
            self.plan = None

    def choose(self):
        cmd, step = self._choose()
        building = self.plan["building"] if self.plan is not None else self.why.get("building")
        self.why = dict(self.why, step=step, building=building, shunned=sorted(self.shunned_now(), key=json.dumps))
        return cmd

    def _choose(self):
        self.why, self.want_shelter = {}, False
        if any(z.get("x") is not None and z.get("y") is not None and zdist(self.world, z) <= DANGER_R
               for z in self.world.zombies.values()):
            self.why["threat"] = True
            return None, None
        hold = self.holding()
        if hold > 0.0:
            self.why["hold"] = hold
            return None, None
        self.hold_until = None
        p = self.plan
        if p is not None and p["step"] == "close":
            return Interact(p["door"][0], p["door"][1], "close"), "close"
        if self.inside():
            self.why.update(inside=True, building=(self.world.map.get(self._square()) or {}).get("building"))
            if p is not None:
                p["step"] = "sleep"
            return Sleep(), "sleep"
        while True:
            if self.plan is None:
                self.plan = self._new_plan()
            p = self.plan
            if p is None:
                self.want_shelter = True
                self.why["want_shelter"] = True
                return None, None
            if p["step"] == "approach":
                if self._near_door(p["door"]):
                    self._advance()
                else:
                    sq = self._approach(p["door"])
                    if sq is None:
                        self._shun(p["building"])   # no free square outside the door: the next building
                        continue
                    return WalkTo(sq[0] + 0.5, sq[1] + 0.5, "walk"), "approach"
            if p["step"] == "open":
                if self._door_open(p["door"]):
                    self._advance()
                else:
                    return Interact(p["door"][0], p["door"][1], "open"), "open"
            if p["step"] in ("enter", "sleep"):   # outside again after a sleep step: walk back in
                p["step"] = "enter"
                c = _centre(p["inside"])
                return WalkTo(c[0], c[1], "walk"), "enter"
            return None, None
