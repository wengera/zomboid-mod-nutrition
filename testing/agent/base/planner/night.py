"""The night instinct (Plan 23 Task 12, spec § 7, P23-9): when tired or late, shelter in a known interior and sleep.

`Night` is a `policies.Policy`, one action at a time; `survive.Survive` runs it as its `night` branch, after `threat`,
`need` and `load` (so a heavy load is dropped before the sleep) and before the goal (Task 13; until then `forage`
and `explore`). The shelter steps are module functions (`shelter_plan`, `shelter_step`, `shelter_ended`) so Task 13's
`Shelter(building)` goal runs the same machine.

- The want (`wants()`): the frame's `stats.fatigue` above TIRED_T 0.6 (the first TIRED moodle), or a late hour
  with fatigue above LATE_FATIGUE 0.3, late being the frame's `me.hour` at LATE_HOUR 22.0 or later or under DAWN_HOUR
  6.0 (fix wave P, M-3: the night runs through midnight to dawn). A frame with no `hour` (a log older than PZA/1.2)
  reads as daytime. A sleep that ended `done` with its `fatigueAfter` under TIRED_T clears the want (`rested`), so a
  character woken at 23:00 with fatigue above LATE_FATIGUE does not lie down again at once, nor after midnight; the
  clearance ends at the first frame at TIRED_T or above, or at the first daytime frame (an hour from DAWN_HOUR to under
  LATE_HOUR: a new day, the late rule fires again the next night). A sleep ended any other way sets no clearance: one
  a threat superseded (P23-AB; the Lua wakes the character) or one `done` still above TIRED_T leaves the want
  standing, so the night sleeps again once nothing pre-empts it. A sleep refused `not allowed` (the server's
  SleepAllowed off, which does not change within a session) ends the want for the session (`allowed` False, ruling
  P23-U), logged once as `why.barred` on the tick that read it.
- Inside (`inside()`): the player's square `(floor(x), floor(y), floor(z))` is in `world.map` with a `room` that is
  not None. Every frame inside adds the square's building to `visited`.
- The choice (`choose()`), with a zombie within DANGER_R sending nothing (the threat branch owns it): inside, `Sleep()`
  at once (no walk), except while a plan's `close` step is due. A plan that reads `done` while the character is not
  `inside()` (pushed out of the doorway after the close) never sleeps there (fix wave P, the deferred T12 minor): the
  plan goes back to its `enter` step, logged `ended: "outside"` and counted as a retry (STEP_RETRIES, then the
  building is shunned). Outside, a plan: of `world.interiors()`, the buildings
  (an id that is not None, not shunned) for which `shelter_plan` answers, ranked visited first (a building the
  character has stood in), then by the distance from the player to its nearest interior square on the player's
  floor, ties by the id. None answers: `want_shelter` True (the goal layer's `Shelter`, Task 13, reads it off
  `survive.night`), no command; False otherwise.
- The shelter machine (`shelter_plan(world, building, door=None)`, a dict, kept to one exterior door when `door` is
  given (the flee's, `policies.Flee`, P23-AG); `shelter_step(world, plan)`; `shelter_ended(plan,
  action)`):
  - Its doors are the building's exterior doors on the player's floor: a door square of `world.doors_of(b)` with at
    least one mapped, non-solid orthogonal neighbour whose `room` is None. An interior door between two rooms is never
    a candidate (the review's I1). They are ranked: read open first, then neither locked nor barricaded, then any,
    each nearest the player. No exterior door: no plan.
  - For the door in use, the interior square is the building's room square on that floor nearest the door, the door
    square itself only when it is the only one (the close is then one step away and the character is not in the
    doorway).
  - The steps, each one `Action`: (a) `approach`, a `WalkTo` at a walk to the centre of the door's approach square,
    skipped when the player already stands within one square (Chebyshev) of the door; (b) `open`, `Interact(dx, dy,
    "open")`, skipped when the door read open at its last record; (c) `enter`, a `WalkTo` at a walk to the interior
    square's centre; (d) `close`, `Interact(dx, dy, "close")`. Then the plan reads `done` and Night sends `Sleep()`.
  - The approach step is kept beside the Lua interact's own walk to the door (`approach` in `PZAgent_SkillsWorld.lua`)
    so a walk that cannot reach the door fails under the walk's own reason (`stuck`, `no path`), which the shun reads,
    rather than inside the open as `not adjacent`.
  - The approach square (ruling, Task 12): the first of `world.reachable_adjacent(door, z)` (nearest the player first)
    with no room, the outside square; when none has (a closed door blocks its own edge, so the square across it is
    never listed as reachable, and every diagonal through the door's corner reads blocked), the nearest mapped,
    non-solid neighbour with no room, the Lua interact's own approach rule (it reads no edge). Cost if wrong: an
    approach to the wrong side of a wall, which the open then fails `not adjacent`, moving to the next door.
  - A step's end (`shelter_ended`): `done` advances; a `superseded` step is sent again (`resend`); a `close` that ends
    any other way is passed over (`passed`: the character is inside and never shuns the building it shelters in, the
    review's M2); `failed` for a reason in SHUN_REASONS (`locked`, `not adjacent`, `no door`, and the walk reasons
    `policies.STUCK_REASONS`) moves to the building's next exterior door at its approach (`next door`), and with no
    next door answers `shun`; any other end (`timeout`, `rejected`, another failure) is retried (`retry`), at most
    STEP_RETRIES 3 times per building, then `shun`. Night shuns the building for SHUN_MIN 120 game minutes (`shunned
    {building: world minutes}`, `World.world_minutes()`, monotonic across midnight: fix wave P, I-1) and drops the
    plan, so the next choose tries the next building. `shunned_now(store, now)` reads the store; the flee shuns into
    the same one.
- A sleep's end (`observe()`): `not safe` (a zombie visible, chasing or very close; one beyond DANGER_R is no threat
  but blocks the sleep) holds the branch NOT_SAFE_S 30 wall seconds and `not valid` (pain, panic, a vehicle) NOT_VALID_S
  60 (ruling P23-U), each from the refusal's `ended_wall`, `rejected` or `failed` alike (`hold_until`: Survive answers
  the branch with no command, so no lower branch walks the character out of its shelter; threat and need stay above
  it); `not allowed` ends the want (above); `done` records `last_sleep` (`gameMin` and the result's `sleptH`,
  `fatigueBefore`, `fatigueAfter`, `bedType`), drops the plan and sets `rested` when `fatigueAfter` (else the frame's
  fatigue) reads under TIRED_T.
- The record for the drivers' `loop.night` (task-15-amendments.md): `wants_n` (the ticks Survive's night branch
  wanted, counted by Survive), `steps` (`[{step, building, aid, state, reason, startS, endS}]`, one per shelter step
  ended) and `sleeps` (`[{aid, state, reason, result, startS, endS, fatigueBefore, fatigueAfter, sleptH, bedType}]`),
  `startS`/`endS` the action's sent and ended wall in seconds from the policy's creation on the injected clock.
- `why` (logged by Survive under the branch): `step` (the step chosen, or None), `building`, `shunned` (the buildings
  shunned now, sorted), `aid` (the action sent, once sent), plus `threat`, `hold` (wall seconds left), `inside`,
  `want_shelter`, `ended` (the outcome of the step end read this tick) and `barred` when they apply.
"""
import json
import math
import time

from agent.base.planner.policies import DANGER_R, PREEMPTED, STUCK_REASONS, Policy, me_floor, me_xy, zdist
from agent.base.pza1 import Interact, Sleep, WalkTo

TIRED_T = 0.6         # the first TIRED moodle fires above 0.6 [#2279]
LATE_HOUR = 22.0      # from this hour of day ...
DAWN_HOUR = 6.0       # ... to this one (through midnight) ...
LATE_FATIGUE = 0.3    # ... the branch wants at a fatigue above this
SHUN_MIN = 120        # game minutes a building whose shelter failed is passed over
NOT_SAFE_S = 30.0     # wall seconds the branch holds after a sleep refused `not safe`
NOT_VALID_S = 60.0    # wall seconds the branch holds after a sleep refused `not valid` (ruling P23-U)
STEP_RETRIES = 3      # non-shun ends of shelter steps a building takes before it is shunned
SHUN_REASONS = ("locked", "not adjacent", "no door") + STUCK_REASONS
HOLD_S = {"not safe": NOT_SAFE_S, "not valid": NOT_VALID_S}
NOT_ALLOWED = "not allowed"
SHELTER_STEPS = ("approach", "open", "enter", "close")

__all__ = ["Night", "TIRED_T", "LATE_HOUR", "DAWN_HOUR", "LATE_FATIGUE", "SHUN_MIN", "NOT_SAFE_S", "NOT_VALID_S",
           "STEP_RETRIES", "SHUN_REASONS", "SHELTER_STEPS", "shelter_plan", "shelter_step", "shelter_ended",
           "exterior_doors", "approach_square", "shunned_now", "player_square"]


def _num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _centre(sq):
    return sq[0] + 0.5, sq[1] + 0.5


def _dist(world, sq):
    mx, my = me_xy(world)
    c = _centre(sq)
    return math.hypot(c[0] - mx, c[1] - my)


def player_square(world):
    """The player's floored square `(x, y, z)`, None when the frame has no position."""
    me = world.me or {}
    x, y = me.get("x"), me.get("y")
    if not (_num(x) and _num(y)):
        return None
    return int(math.floor(x)), int(math.floor(y)), me_floor(world)


def _outdoor(world, sq):
    s = world.map.get(sq)
    return s is not None and not s.get("solid") and s.get("room") is None


# ---------------------------------------------------------------- the shelter machine
def exterior_doors(world, building, z):
    """The building's exterior door squares on floor `z` (a mapped, non-solid, room-less orthogonal neighbour), ranked
    open first, then neither locked nor barricaded, then any, each nearest the player. The candidates are read once
    per map version (`World.memo`, M-4); only the ranking, which reads the player, runs each call."""
    def rank(sq):
        d = world.map[sq].get("door") or {}
        state = 0 if d.get("open") else (2 if d.get("locked") or d.get("barricaded") else 1)
        return state, _dist(world, sq), sq

    def candidates():
        return [sq for sq in world.doors_of(building) if sq[2] == z
                and any(_outdoor(world, (sq[0] + dx, sq[1] + dy, z)) for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)))]
    return sorted(world.memo(("exterior_doors", building, z), candidates), key=rank)


def approach_square(world, door):
    """The square the approach walks to (the module docstring's ruling), None when the door has no free neighbour
    outside."""
    for sq in world.reachable_adjacent((door[0], door[1]), door[2]):
        if world.map[sq].get("room") is None:
            return sq
    out = [(_dist(world, sq), sq) for sq in ((door[0] + dx, door[1] + dy, door[2]) for dx in (-1, 0, 1)
                                             for dy in (-1, 0, 1)) if sq != door and _outdoor(world, sq)]
    return min(out)[1] if out else None


def _inside_for(rooms, door):
    deeper = [sq for sq in rooms if sq != door] or rooms
    return min(deeper, key=lambda sq: (math.hypot(sq[0] - door[0], sq[1] - door[1]), sq))


def shunned_now(store, now):
    """The buildings of a shun store (building -> world minutes shunned at) still shunned at world minute `now`
    (SHUN_MIN): the night's and the flee's one rule over the one store."""
    return {b for b, at in store.items() if now - at < SHUN_MIN}


def shelter_plan(world, building, door=None, step="approach"):
    """A shelter plan for `building` on the player's floor: `{building, doors, door_i, rooms, inside, step, retries,
    near}`, `near` the distance from the player to its nearest room square; None with no exterior door or no room.
    With `door`, the plan is kept to that one exterior door (the flee's, P23-AG), None when it is not one; `step`
    the step it starts at (the flee adopts the building it stands in at `done`)."""
    z = me_floor(world)
    rooms = [sq for sq in world.interiors().get(building, ()) if sq[2] == z]
    doors = exterior_doors(world, building, z)
    if door is not None:
        doors = [door] if door in doors else []
    if not rooms or not doors:
        return None
    return {"building": building, "doors": doors, "door_i": 0, "rooms": rooms, "inside": _inside_for(rooms, doors[0]),
            "step": step, "retries": 0, "near": min(_dist(world, sq) for sq in rooms)}


def _door(plan):
    return plan["doors"][plan["door_i"]]


def _near(world, door):
    sq = player_square(world)
    return sq is not None and sq[2] == door[2] and max(abs(sq[0] - door[0]), abs(sq[1] - door[1])) <= 1


def _next_door(plan):
    """Move to the next exterior door at its approach; False when none is left."""
    if plan["door_i"] + 1 >= len(plan["doors"]):
        return False
    plan["door_i"] += 1
    plan["inside"] = _inside_for(plan["rooms"], _door(plan))
    plan["step"] = "approach"
    return True


def shelter_step(world, plan):
    """(command, step) of the plan's next step, skipping an approach the player stands at and an open of a door that
    read open; (None, "done") once the close ended; (None, "shun") when no door is left to try."""
    while plan["step"] != "done":
        door, step = _door(plan), plan["step"]
        if step == "approach":
            if _near(world, door):
                plan["step"] = "open"
                continue
            sq = approach_square(world, door)
            if sq is not None:
                c = _centre(sq)
                return WalkTo(c[0], c[1], "walk"), step
            if not _next_door(plan):
                return None, "shun"
            continue
        if step == "open":
            if ((world.map.get(door) or {}).get("door") or {}).get("open"):
                plan["step"] = "enter"
                continue
            return Interact(door[0], door[1], "open"), step
        if step == "enter":
            c = _centre(plan["inside"])
            return WalkTo(c[0], c[1], "walk"), step
        return Interact(door[0], door[1], "close"), step
    return None, "done"


def shelter_ended(plan, action):
    """Read a shelter step's end into the plan (the module docstring's rule): `advance`, `resend`, `passed`, `next
    door`, `retry` or `shun`."""
    step = plan["step"]
    if action.state == "failed" and action.reason == PREEMPTED:
        return "resend"
    if action.state == "done":
        plan["step"] = SHELTER_STEPS[SHELTER_STEPS.index(step) + 1] if step != "close" else "done"
        return "advance"
    if step == "close":
        plan["step"] = "done"
        return "passed"
    if action.state == "failed" and action.reason in SHUN_REASONS:
        return "next door" if _next_door(plan) else "shun"
    plan["retries"] += 1
    return "retry" if plan["retries"] < STEP_RETRIES else "shun"


# ---------------------------------------------------------------- the policy
class Night(Policy):
    def __init__(self, world, actions, clock=time.time):
        super().__init__(world, actions, clock)
        self.t0 = clock()
        self.want_shelter = False
        self.allowed = True     # False once a sleep was refused `not allowed`: no want for the session
        self.shunned = {}       # building -> the world minutes it was shunned at (World.world_minutes)
        self.visited = set()    # the buildings whose interior the character has stood in
        self.last_sleep = None  # {gameMin, sleptH, fatigueBefore, fatigueAfter, bedType} of the last sleep done
        self.rested = False     # the last sleep ended under TIRED_T (the module docstring's clearance)
        self.hold_until = None  # wall until which a refused sleep holds the branch
        self.plan = None        # the shelter plan while sheltering
        self.wants_n = 0        # ticks the night branch wanted (Survive counts them)
        self.steps = []         # each shelter step ended, for loop.night
        self.sleeps = []        # each sleep ended, for loop.night
        self._read = None       # the last action whose end observe() has read
        self._sent = None       # (step, building) of the last command chosen
        self._note = {}         # what observe read this tick, merged into why

    # ---------------------------------------------------------------- reading the frame
    def fatigue(self):
        f = (self.world.stats or {}).get("fatigue")
        return f if _num(f) else 0.0

    def hour(self):
        h = (self.world.me or {}).get("hour")
        return h if _num(h) else None

    def late(self):
        """The frame's hour is the night's: LATE_HOUR or later, or under DAWN_HOUR (M-3); no hour reads daytime."""
        h = self.hour()
        return h is not None and (h >= LATE_HOUR or h < DAWN_HOUR)

    def wants(self):
        if not self.allowed:
            return False
        f = self.fatigue()
        if self.rested and f < TIRED_T:
            return False
        if f > TIRED_T:
            return True
        return self.late() and f > LATE_FATIGUE

    def inside(self):
        sq = player_square(self.world)
        s = self.world.map.get(sq) if sq is not None else None
        return s is not None and s.get("room") is not None

    def shunned_now(self):
        return shunned_now(self.shunned, self.world.world_minutes())

    def holding(self):
        """Wall seconds the branch still holds after a refused sleep, else 0.0."""
        if self.hold_until is None:
            return 0.0
        return max(0.0, self.hold_until - self.clock())

    def idle(self):
        """The branch does not want: no plan, no shelter wanted; a `not allowed` read this tick is logged once."""
        self.plan, self.want_shelter = None, False
        self.why = dict({"wants": False}, **self._note)
        self._note = {}

    # ---------------------------------------------------------------- the record
    def _s(self, wall):
        return wall - self.t0 if _num(wall) else None

    def _row(self, a):
        return {"aid": a.aid, "state": a.state, "reason": a.reason, "startS": self._s(a.sent_wall),
                "endS": self._s(a.ended_wall)}

    # ---------------------------------------------------------------- the policy
    def observe(self):
        sq = player_square(self.world)
        s = self.world.map.get(sq) if sq is not None else None
        if s is not None and s.get("room") is not None and s.get("building") is not None:
            self.visited.add(s["building"])
        if self.rested and (self.fatigue() >= TIRED_T or (self.hour() is not None and not self.late())):
            self.rested = False   # tired again, or a daytime frame: the new day
        a = self.last
        if a is None or a is self._read or not self.actions.done(a):
            return
        self._read = a
        if a.type == "sleep":
            self._sleep_ended(a)
            return
        step, building = self._sent
        self.steps.append(dict(self._row(a), step=step, building=building))
        if self.plan is None or self.plan["building"] != building:
            return
        out = shelter_ended(self.plan, a)
        self._note = {"ended": out}
        if out == "shun":
            self._shun(building)

    def _sleep_ended(self, a):
        res = a.result if isinstance(a.result, dict) else {}
        keys = ("fatigueBefore", "fatigueAfter", "sleptH", "bedType")
        self.sleeps.append(dict(self._row(a), result=a.result, **{k: res.get(k) for k in keys}))
        if a.state in ("rejected", "failed") and a.reason in HOLD_S:
            ended = a.ended_wall if _num(a.ended_wall) else self.clock()
            self.hold_until = ended + HOLD_S[a.reason]   # from the refusal's own wall, not the tick that read it
        elif a.state in ("rejected", "failed") and a.reason == NOT_ALLOWED:
            self.allowed = False
            self._note = {"barred": NOT_ALLOWED}
        elif a.state == "done":
            self.last_sleep = dict({"gameMin": self.world.game_min}, **{k: res.get(k) for k in keys})
            after = res.get("fatigueAfter")
            self.rested = (after if _num(after) else self.fatigue()) < TIRED_T
            self.plan = None

    def choose(self):
        cmd, step = self._choose()
        building = self.plan["building"] if self.plan is not None else self.why.get("building")
        self._sent = (step, building)
        self.why = dict(self.why, step=step, building=building, shunned=sorted(self.shunned_now(), key=json.dumps),
                        **self._note)
        self._note = {}
        return cmd

    def sent(self, cmd, action):
        self.why["aid"] = action.aid

    def _shun(self, building):
        self.shunned[building] = self.world.world_minutes()
        self.plan = None

    def _outside_done(self, p):
        """A plan done with the character not inside: back to its enter step as a retry (the module docstring)."""
        self._note = dict(self._note, ended="outside")
        p["retries"] += 1
        if p["retries"] >= STEP_RETRIES:
            self._shun(p["building"])
        else:
            p["step"] = "enter"

    def _new_plan(self):
        skip = self.shunned_now()
        plans = [shelter_plan(self.world, b) for b in self.world.interiors() if b is not None and b not in skip]
        plans = [p for p in plans if p is not None]
        if not plans:
            return None
        return min(plans, key=lambda p: (p["building"] not in self.visited, p["near"], json.dumps(p["building"])))

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
            return shelter_step(self.world, p)
        if self.inside():
            sq = player_square(self.world)
            self.why.update(inside=True, building=(self.world.map.get(sq) or {}).get("building"))
            return Sleep(), "sleep"
        while True:
            if self.plan is None:
                self.plan = self._new_plan()
            if self.plan is None:
                self.want_shelter = True
                self.why["want_shelter"] = True
                return None, None
            cmd, step = shelter_step(self.world, self.plan)
            if step == "shun":
                self._shun(self.plan["building"])
                continue
            if step == "done":            # not inside (checked above): never a sleep outdoors
                self._outside_done(self.plan)
                continue
            return cmd, step
