"""The goal layer (Plan 23 Task 13, spec § 8, P23-10, P23-B): typed goals under the instincts, chosen by a source
behind one seam (`GoalSource.propose(view) -> Goal | None`) that the scripted source and Task 14's LLM source share;
None is *pending* (ruling P23-AC): the source has no answer yet (the LLM's call in flight), and the scripted source
never answers it.

`Survive`'s last branch, `goal`, runs one goal at a time through `GoalRunner`; the instincts above it (threat, need,
load, night) pre-empt it. The goal types are `schema/goals.json`'s five, each a dataclass whose fields are that
entry's properties less `type` (P23-B, asserted by the tests), plus three run fields every goal carries (`RUN_FIELDS`:
`state` "running" | "done" | "failed" | "superseded", `reason`, `started_wall`, keyword-only and defaulted), `TYPE`
a class attribute equal to the entry's `const`:
- `ExploreToward(x, y)`: Explore's logic aimed at a point: a `Scan(SCAN_R)` of the player's place while the place is
  unscanned, then a `WalkTo(x, y)` at a walk; `done "arrived"` when its walk ends done, or when the place is scanned
  and the player stands within ARRIVE_R (1.5 tiles) of (x, y); a walk or scan that ends any other way but
  `superseded` fails the goal under the action's reason (a walk failed for a `STUCK_REASONS` reason is marked stuck by
  `Explore.observe`, so the scripted source's next edge leaves it out). The climb in routes (Plan 24 Task 10, ruling
  P24-G 4; #4296: a short fence climbed at a walk never trips; `_Climbing` and the kit's `hop_after`, shared with
  `Shelter` since Task 10 fix 1, minor 9): a walk the path follower could not finish, ended `failed "stuck"` where the
  straight line from the player toward the walk's target first crosses a hoppable edge (`World.hop_ahead`: blocked,
  its square's `hopN`/`hopW` true, at the player's own square), sends `Climb(x, y)` of that fence's square (the build
  announcing `climb`, `World.can`) and walks again once the climb ends done, the climbed walk target's stuck mark
  dropped (`Kit.climbed`: `Explore.observe` marked it at the stuck end, which would leave the edge out of
  `unexplored_edge` for STUCK_TTL_MIN after a climb that crossed it); a climb that ends any other way (`fell`, a tall
  fence's `failed`) fails the goal under its reason, and a second stuck walk at a fence it already climbed fails it
  `stuck`. A walk whose path crosses a hoppable edge the follower climbs itself needs nothing; nothing here ever runs or
  sprints over a fence (no vault).
- `LootBuilding(building)`: `LootHouse` kept to the containers on the building's squares (`LootHouse.within`), one
  loot at a time for the first of STOCK_WANTS (water, food, bandage, weapon) that `LootHouse.target` answers there;
  `done "looted"` when none answers after at least one loot, `failed "nothing to loot"` when none answered at all,
  `failed "load"` above `LOOT_MAX_LEVEL` (the level guard, spec § 9 (1)).
- `Shelter(building)`: Night's shelter machine for a named building (`night.shelter_plan`, `shelter_step`,
  `shelter_ended`, never re-implemented): approach the exterior door, open it, step in, close it (a step's walk failed
  `stuck` at a hoppable edge climbs it first, as `ExploreToward` does, and walks again; a climb that fails is read as
  that walk's stuck end, the machine's next door or shun); `done "inside"` once the plan reads done, `failed "no
  plan"` with no exterior door or room on the player's floor, `failed "shun"` when the machine shuns the building; both shun the building in the kit's `shunned` for `night.SHUN_MIN` game
  minutes (fix 1, I3) on `World.world_minutes()` (monotonic across midnight: fix wave P, I-1), the store
  `Night.shunned` is when the runner is given it (`GoalRunner(..., shunned=)`, M6), so the night and the goal pass
  over the same buildings; the view reads it.
- `Stock(kind)`: `LootHouse` with `want = kind` (water or food) over the nearest containers holding that use;
  `done "stocked"` once `world.by_use()[kind]` holds more ids than at the goal's start, `failed "none found"` when no
  container answers, `failed "load"` above `LOOT_MAX_LEVEL`.
- `Rest(seconds)`: nothing sent (the frame keeps coming) until its seconds pass on the injected clock, then
  `done "rested"`. Its budget is `max(GOAL_MAX_S, seconds)` (ruling P23-W: a rest is the one goal whose length is its
  content, so a schema-valid Rest up to 120 s ends rested, never on the budget); every other goal's is GOAL_MAX_S.

A goal's `step(world, actions, clock)` is `observe` (the end of its own last action, its own done test) then, while
it runs and its own action is not still running, `choose` (the next command, or None); it returns that command or
None and sets `state`/`reason` itself when it ends. The machines are built on the first step: a goal takes the
runner's `Kit` (one `Explore`, one `LootHouse` and the shelter shuns, shared by every goal of a session, so a place
scanned, a container looted or capped and a pending loot superseded by an instinct outlive the goal that made them,
as the old `forage`/`explore` branches' long-lived machines did), else builds its own (a goal run alone).

`validate(obj) -> Goal` checks a dict against `goals.json` with a stdlib walk (the `type` const, `required`,
`additionalProperties`, each field's `type`, `enum`, `minimum`, `maximum`; a bool is never a number, a non-finite
number is refused) and raises
`ValueError` with a one-line reason; it returns the dataclass. `EXAMPLES` holds one valid argument dict per type.

`ScriptedSource` (`NAME = "scripted"`) is the old forage and explore reshaped, its order: `Stock(kind)` when the view's
`needs_wanted` names water or food (water first) and `stock_uses` says a container answers it; `Shelter` the nearest
known building for which the view's `shelter` reads true (`night.shelter_plan` answers: rooms and an exterior door on
the player's floor) and that is not shunned, when `want_shelter`; `LootBuilding` the nearest building with a container
known and not yet looted (the view's `looted` false and `containers` above 0, P24-B 3); `ExploreToward` the view's
`edge` (which leaves out the bearing of a met group, `World.unexplored_edge`, ruling P24-B 2), else the player's own
square while `scanned_here` is false (a fresh session's first scan, before the map holds an edge); else `Rest(REST_S)`.
The edge leaves a stuck area (ruling P23-AP 1, E4's twelve walks from one square north of a locked gate): after two
walks from the player's square failed `stuck` unmoved, `world.unexplored_edge` answers only a square a bounded flood
from the player reaches and whose straight line from it crosses no known blocking edge, else none, and the kit's
`Explore` has dropped the place from `scanned`; so the source proposes a loot, else the scan of the player's own
square, never a third walk from that square. A loot goal (`Stock`, `LootBuilding`) is proposed only at the view's load
level `LOOT_MAX_LEVEL` or below, so a heavy load never proposes a goal that fails on its first step. A candidate the
view's `cooled` lists is passed over for the next.

`GoalRunner(source, clock, shunned=None)`: `current` (the running goal or None), `history` (the record rows,
`loop.goals` of task-15-amendments.md: `{type, args, state, reason, startS, endS, source}`, `startS`/`endS` seconds
on the injected clock from the runner's creation, `source` the source's `NAME`), `kit`, `cooled`, `why`.
`rows()` is the record's `loop.goals`: copies of `history`, then the running goal's row (state "running", `endS`
None; Task 16d, the drivers' copy of it removed).
`observe(world, actions)`, which Survive calls every tick before its branches whether or not the goal branch runs
(fix 1, I1): the kit's bookkeeping, then the running goal is closed `superseded` (reason: the type of the action
that replaced it) when the last action sent is not its own, its own being its last sent action, else its `mark` (the
last action sent when the runner took it, so a goal that has sent nothing, a Rest or one whose first command was
cooled, is superseded too: fix 1, the spec gap), closed `superseded` (reason `hold`) once another branch has answered
GOAL_HOLD_SUPERSEDE_TICKS (20) planner ticks in a row without sending (an instinct's hold-without-send never moves
the history, so the mark never reads it: fix wave P, M-7; Survive reports each tick through `held(by_other)`), or
closed `failed "goal budget"` past its budget in wall seconds from when it was taken; so the row's `endS` and the
log's `goal` read the pre-emption on the tick after the instinct's send, not when the goal branch next runs.
`tick(world, actions, view=None)` observes first unless `observe` ran since the last tick (a runner ticked alone),
lets the running goal read its own end, and with no goal running asks the source once (`view` is the dict, or a
callable building it only then), so at most one proposal a tick; the new goal steps at once. A source answering None
is pending (P23-AC): no goal this tick, `pending` true (Survive's goal branch then holds, so nothing lower runs), the
log's `goal` reads `{"pending": <source NAME>}`, and the next tick asks again with a fresh view; the budget starts
only when a goal is taken. A superseded goal is gone; the source may propose the same goal again. A goal that ends
`failed` having sent nothing (a first-step failure: an unknown building, no plan) is cooled per `(type, args)` for
GOAL_COOL_S (30) wall seconds (fix 1, I4): the view lists the cooled goals (`cooled`), the scripted source passes
them over, and a cooled goal a source still proposes is refused for that tick (`why.refused`), no row written.
`send(cmd)` sends the
goal's command and hands the `Action` to the goal (Survive sends through it, as the owner). `line()` is the
decision log's `goal` field: `{type, args, state, source}` of the running goal, or of the one that ended this tick,
else `{"pending": <source NAME>}` while the source is pending, else None.
"""
import json
import math
import os
import time
from dataclasses import dataclass, field, fields
from typing import ClassVar, Optional, Protocol, runtime_checkable

from agent.base.items import use_of
from agent.base.planner.night import SHUN_MIN, shelter_ended, shelter_plan, shelter_step
from agent.base.planner.policies import (LOOT_MAX_LEVEL, LOOT_WANTS, PREEMPTED, SCAN_R, Explore, LootHouse, me_xy,
                                         place_of)
from agent.base.pza1 import Climb, Scan, WalkTo

GOAL_MAX_S = 90.0     # wall seconds a goal may run before it is failed "goal budget" and replaced (a Rest: P23-W)
GOAL_COOL_S = 30.0    # wall seconds a goal that failed having sent nothing is not taken again (fix 1, I4)
GOAL_HOLD_SUPERSEDE_TICKS = 20   # planner ticks another branch holds without sending before the goal is superseded
ARRIVE_R = 1.5        # tiles: an ExploreToward whose place is scanned is done within this of its point
REST_S = 30.0         # the scripted source's rest
STOCK_WANTS = ("water", "food", "bandage", "weapon")   # LootBuilding's order of uses
STOCK_KINDS = ("water", "food")                        # Stock's kinds, the scripted source's order
RUN_FIELDS = ("state", "reason", "started_wall")
STATES = ("running", "done", "failed", "superseded")
SCHEMA_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "schema", "goals.json")
EXAMPLES = {"ExploreToward": {"x": 120, "y": 205}, "LootBuilding": {"building": 3}, "Shelter": {"building": 3},
            "Stock": {"kind": "water"}, "Rest": {"seconds": 30.0}}

__all__ = ["Goal", "ExploreToward", "LootBuilding", "Shelter", "Stock", "Rest", "GoalSource", "ScriptedSource",
           "GoalRunner", "Kit", "validate", "open_uses", "int_id", "goal_key", "GOAL_MAX_S", "GOAL_COOL_S",
           "GOAL_HOLD_SUPERSEDE_TICKS",
           "ARRIVE_R", "REST_S", "STOCK_WANTS",
           "STOCK_KINDS", "RUN_FIELDS", "STATES", "SCHEMA_PATH", "EXAMPLES"]


def _num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def int_id(v):
    """An int that is not a bool (a building id the schema's integer admits)."""
    return isinstance(v, int) and not isinstance(v, bool)


def goal_key(typ, args):
    """The cooling key of a goal: its type and its args as sorted JSON."""
    return typ, json.dumps(args, sort_keys=True)


def open_uses(world, loot, key, waiting=None):
    """The uses of LOOT_WANTS a loot could still take at container `key`: the container holds an item of the use, is
    not marked looted for it, and is not waiting on the cap (`LootHouse.waiting`, read off `loot` unless `waiting`
    {use: keys} is given). The view counts a container with none as looted."""
    c = world.containers.get(key)
    if c is None or not c["n"] or not c["items"]:
        return []
    out = []
    for u in LOOT_WANTS:
        if u in c["looted"] or not any(use_of(i) == u for i in c["items"]):
            continue
        skip = waiting[u] if waiting is not None else (loot.waiting(u) if loot is not None else ())
        if key not in skip:
            out.append(u)
    return out


# ---------------------------------------------------------------- the shared machines
class Kit:
    """The machines a session's goals share: one `Explore` (its scanned places), one `LootHouse` (its pending loots,
    capped squares) and `shunned` {building: world minutes}, the Shelter goals' shuns (`Night.shunned` when given,
    M6)."""

    def __init__(self, world=None, actions=None, clock=time.time, shunned=None):
        self.explore = Explore(world, actions, clock)
        self.loot = LootHouse(world, actions, clock)
        self.shunned = {} if shunned is None else shunned

    def bind(self, world, actions):
        for m in (self.explore, self.loot):
            m.world, m.actions = world, actions

    def observe(self, world, actions):
        """The machines' bookkeeping, every tick (idempotent): a loot's end marks its containers, a stuck walk its
        square, a scan ended badly unmarks its place."""
        self.bind(world, actions)
        self.loot.observe()
        self.explore.observe()

    def hop_after(self, world, action, climbed=()):
        """The route climb's read (ruling P24-G 4): the fence square (x, y) to climb after `action`, a `walkTo` that
        ended `failed "stuck"` on a build announcing `climb`, where the straight line from the player toward its target
        first crosses a hoppable edge (`World.hop_ahead`) not in `climbed`; else None."""
        if not (action.type == "walkTo" and action.state == "failed" and action.reason == "stuck"
                and world.can("climb")):
            return None
        hop = world.hop_ahead(me_xy(world), (action.args.get("x"), action.args.get("y")))
        return None if hop is None or hop in climbed else hop

    def climbed(self, world, walk):
        """A climb after `walk` ended done: the walk target's stuck mark (`Explore`'s, at the stuck end) is dropped."""
        world.unmark_stuck(int(math.floor(walk.args.get("x"))), int(math.floor(walk.args.get("y"))))

    def shunned_now(self, world):
        """The buildings shunned within SHUN_MIN game minutes of `world.world_minutes()` (I-1)."""
        now = world.world_minutes()
        return {b for b, at in self.shunned.items() if now - at < SHUN_MIN}


# ---------------------------------------------------------------- the goals
@dataclass
class Goal:
    """A goal: see the module docstring. Subclasses add their schema fields and `choose`."""
    TYPE: ClassVar[str] = ""
    state: str = field(default="running", kw_only=True)
    reason: Optional[str] = field(default=None, kw_only=True)
    started_wall: Optional[float] = field(default=None, kw_only=True)

    def __post_init__(self):
        self.kit = None        # the runner's Kit, else built on the first step
        self.last = None       # the last Action this goal sent
        self.mark = None       # the last action sent (by anyone) when the runner took this goal
        self.why = {}          # the goal's inputs to its last choice, logged under the goal branch
        self.sent_n = 0        # commands this goal sent
        self._read = None      # the last action whose end observe() has read
        self._begun = False

    # -- the record ---------------------------------------------------------------------------------------------
    def args(self):
        return {f.name: getattr(self, f.name) for f in fields(self) if f.name not in RUN_FIELDS}

    def row(self):
        return {"type": self.TYPE, "args": self.args(), "state": self.state, "reason": self.reason}

    @property
    def running(self):
        return self.state == "running"

    def end(self, state, reason):
        if self.running:
            self.state, self.reason = state, reason

    def budget(self):
        """Wall seconds this goal may run from its proposal."""
        return GOAL_MAX_S

    # -- the step -----------------------------------------------------------------------------------------------
    def begin(self, world, actions, clock):
        """Once, on the first observe: the machines (the runner's kit, else its own), the clock's start."""
        if self._begun:
            return
        self._begun = True
        if self.kit is None:
            self.kit = Kit(world, actions, clock)
        if self.started_wall is None:
            self.started_wall = clock()
        self.kit.bind(world, actions)
        self.start(world)

    def start(self, world):
        """A subclass's first-step setup."""

    def busy(self, actions):
        return self.last is not None and not actions.done(self.last)

    def observe(self, world, actions, clock):
        self.begin(world, actions, clock)
        if not self.running:
            return
        a = self.last
        if a is not None and a is not self._read and actions.done(a):
            self._read = a
            if not (a.state == "failed" and a.reason == PREEMPTED):   # a superseded step is chosen again
                self.ended(world, a)
        if self.running and not self.busy(actions):
            self.check(world, clock)

    def ended(self, world, action):
        """Read the end of this goal's own last action (never a superseded one)."""

    def check(self, world, clock):
        """The goal's own done test, read while its action is not running."""

    def step(self, world, actions, clock):
        self.observe(world, actions, clock)
        if not self.running or self.busy(actions):
            return None
        return self.choose(world, actions, clock)

    def choose(self, world, actions, clock):
        raise NotImplementedError

    def sent(self, cmd, action):
        self.last = action
        self.sent_n += 1


class _Climbing:
    """The route climb's goal side (ruling P24-G 4; lifted out of `ExploreToward` at Task 10 fix 1, minor 9, for the
    `Shelter` walks too): `_climbs()` once at the start; `_stuck(world, walk)` after a walk's end, True when a climb is
    due (`Kit.hop_after`); `_climb_ended(world, action)` after the climb's, True when it ended done (the fence kept in
    `climbed`, the walk target's stuck mark dropped: `Kit.climbed`); `_climb_cmd()` the due `Climb`, else None."""

    def _climbs(self):
        self.climb = None        # the fence square (x, y) the next choose climbs, else None
        self.climbed = set()     # the fence squares this goal climbed
        self.stuck_walk = None   # the walk whose stuck end the due or running climb answers

    def _stuck(self, world, walk):
        hop = self.kit.hop_after(world, walk, self.climbed)
        if hop is None:
            return False
        self.climb, self.stuck_walk = hop, walk
        return True

    def _climb_ended(self, world, action):
        if action.state != "done":
            return False
        self.climbed.add((action.args.get("x"), action.args.get("y")))
        self.kit.climbed(world, self.stuck_walk)
        return True

    def _climb_cmd(self):
        if self.climb is None:
            return None
        x, y = self.climb
        self.climb = None
        return Climb(x, y)


@dataclass
class ExploreToward(_Climbing, Goal):
    TYPE: ClassVar[str] = "ExploreToward"
    x: int
    y: int

    def _dist(self, world):
        mx, my = me_xy(world)
        return math.hypot(self.x - mx, self.y - my)

    def start(self, world):
        self._climbs()

    def ended(self, world, action):
        if action.type == "walkTo":
            if action.state == "done":
                self.end("done", "arrived")
            elif not self._stuck(world, action):
                self.end("failed", action.reason or action.state)
        elif action.type == "climb":
            if not self._climb_ended(world, action):
                self.end("failed", action.reason or action.state)
        elif action.type == "scan" and action.state != "done":
            self.end("failed", action.reason or action.state)

    def check(self, world, clock):
        if place_of(world) in self.kit.explore.scanned and self._dist(world) <= ARRIVE_R:
            self.end("done", "arrived")

    def choose(self, world, actions, clock):
        ex = self.kit.explore
        place = place_of(world)
        if place not in ex.scanned:
            self.why = {"scanAt": list(place), "toward": [self.x, self.y]}
            return Scan(SCAN_R)
        climb = self._climb_cmd()
        if climb is not None:
            self.why = {"toward": [self.x, self.y], "climb": [climb.x, climb.y]}
            return climb
        self.why = {"toward": [self.x, self.y], "dist": self._dist(world)}
        return WalkTo(self.x, self.y, "walk")

    def sent(self, cmd, action):
        super().sent(cmd, action)
        self.kit.explore.sent(cmd, action)


class _Looting:
    """The loot goals' shared send: the kit's LootHouse records its pending loot."""

    def sent(self, cmd, action):
        super().sent(cmd, action)
        self.kit.loot.sent(cmd, action)

    def _guard(self):
        level = self.kit.loot.level()
        if level > LOOT_MAX_LEVEL:
            self.why = {"level": level, "hold": True}
            self.end("failed", "load")
            return True
        return False


@dataclass
class LootBuilding(_Looting, Goal):
    TYPE: ClassVar[str] = "LootBuilding"
    building: int

    def keys(self, world):
        """The container keys on the building's squares."""
        return {k for k in world.containers if (world.map.get(k[:3]) or {}).get("building") == self.building}

    def choose(self, world, actions, clock):
        if self._guard():
            return None
        loot = self.kit.loot
        loot.within = self.keys(world)
        try:
            want = next((u for u in STOCK_WANTS if loot.target(u) is not None), None)
            if want is not None:
                loot.want = want
                cmd = loot.choose()
                self.why = dict(loot.why, building=self.building)
                return cmd
        finally:
            loot.within = None
        self.why = {"building": self.building, "want": None}
        if self.sent_n:
            self.end("done", "looted")
        else:
            self.end("failed", "nothing to loot")
        return None


@dataclass
class Shelter(_Climbing, Goal):
    TYPE: ClassVar[str] = "Shelter"
    building: int

    def start(self, world):
        self._climbs()
        self.plan = shelter_plan(world, self.building)
        if self.plan is None:
            self.why = {"building": self.building, "plan": None}
            self.kit.shunned[self.building] = world.world_minutes()   # I3: never re-proposed every tick
            self.end("failed", "no plan")

    def _shun(self, world):
        self.kit.shunned[self.building] = world.world_minutes()
        self.end("failed", "shun")

    def ended(self, world, action):
        """A step's end into the plan (`shelter_ended`); a walk stuck at a hoppable edge climbs first (the plan's step
        kept), and a climb that did not end done is read as that walk's own stuck end."""
        if action.type == "climb":
            if self._climb_ended(world, action):
                self.why = dict(self.why, ended="climbed")
                return
            action = self.stuck_walk
        elif self._stuck(world, action):
            self.why = dict(self.why, ended="climb")
            return
        out = shelter_ended(self.plan, action)
        self.why = dict(self.why, ended=out)
        if out == "shun":
            self._shun(world)

    def check(self, world, clock):
        if self.plan["step"] == "done":
            self.why = dict(self.why, step="done")
            self.end("done", "inside")

    def choose(self, world, actions, clock):
        climb = self._climb_cmd()
        if climb is not None:
            self.why = {"step": "climb", "building": self.building, "climb": [climb.x, climb.y]}
            return climb
        cmd, step = shelter_step(world, self.plan)
        self.why = {"step": step, "building": self.building, "door": list(self.plan["doors"][self.plan["door_i"]])}
        if step == "shun":
            self._shun(world)
            return None
        if step == "done":
            self.end("done", "inside")
            return None
        return cmd


@dataclass
class Stock(_Looting, Goal):
    TYPE: ClassVar[str] = "Stock"
    kind: str

    def _held(self, world):
        return len(world.by_use().get(self.kind, ()))

    def start(self, world):
        self.base = self._held(world)

    def check(self, world, clock):
        if self._held(world) > self.base:
            self.end("done", "stocked")

    def choose(self, world, actions, clock):
        if self._guard():
            return None
        loot = self.kit.loot
        loot.want, loot.within = self.kind, None
        cmd = loot.choose()
        self.why = dict(loot.why, held=self._held(world), base=self.base)
        if cmd is None:
            self.end("failed", "none found")
        return cmd


@dataclass
class Rest(Goal):
    TYPE: ClassVar[str] = "Rest"
    seconds: float

    def budget(self):
        return max(GOAL_MAX_S, self.seconds)   # ruling P23-W

    def check(self, world, clock):
        if clock() - self.started_wall >= self.seconds - 1e-9:
            self.end("done", "rested")

    def choose(self, world, actions, clock):
        self.why = {"rest": self.seconds, "left": self.seconds - (clock() - self.started_wall)}
        return None


TYPES = {c.TYPE: c for c in (ExploreToward, LootBuilding, Shelter, Stock, Rest)}


# ---------------------------------------------------------------- validate
_SCHEMA = {}


def _entries():
    if not _SCHEMA:
        with open(SCHEMA_PATH, encoding="utf-8") as f:
            for e in json.load(f)["oneOf"]:
                _SCHEMA[e["properties"]["type"]["const"]] = e
    return _SCHEMA


_JSON_TYPES = {"integer": int_id, "number": _num, "string": lambda v: isinstance(v, str)}


def _field(t, name, spec, v):
    kind = spec.get("type")
    if kind is not None and not _JSON_TYPES[kind](v):
        raise ValueError("%s.%s: %r is not of type %s" % (t, name, v, kind))
    if _num(v) and not math.isfinite(v):
        raise ValueError("%s.%s: %r is not finite" % (t, name, v))
    if "enum" in spec and v not in spec["enum"]:
        raise ValueError("%s.%s: %r not in %s" % (t, name, v, spec["enum"]))
    if "maximum" in spec and v > spec["maximum"]:
        raise ValueError("%s.%s: %r above the maximum %s" % (t, name, v, spec["maximum"]))
    if "minimum" in spec and v < spec["minimum"]:
        raise ValueError("%s.%s: %r below the minimum %s" % (t, name, v, spec["minimum"]))


def validate(obj):
    """The goal `obj` names, checked against `goals.json` (the module docstring); ValueError with a one-line reason."""
    if not isinstance(obj, dict):
        raise ValueError("goal: %r is not an object" % (obj,))
    t = obj.get("type")
    e = _entries().get(t) if isinstance(t, str) else None
    if e is None:
        raise ValueError("goal: unknown goal type %r" % (t,))
    props = e["properties"]
    for k in e.get("required", ()):
        if k not in obj:
            raise ValueError("%s: missing %s" % (t, k))
    if e.get("additionalProperties") is False:
        extra = sorted(k for k in obj if k not in props)
        if extra:
            raise ValueError("%s: unexpected %s" % (t, ", ".join(extra)))
    for k, v in obj.items():
        if k != "type":
            _field(t, k, props[k], v)
    return TYPES[t](**{k: v for k, v in obj.items() if k != "type"})


# ---------------------------------------------------------------- the sources
@runtime_checkable
class GoalSource(Protocol):
    NAME: str

    def propose(self, view: dict) -> Optional[Goal]:
        """A goal, or None while the source is pending (P23-AC)."""
        ...


def _nearest_first(buildings):
    return sorted((b for b in buildings if int_id(b.get("id"))),
                  key=lambda b: (b["dist"] if _num(b.get("dist")) else math.inf, b["id"]))


class ScriptedSource:
    """The scripted order (the module docstring)."""
    NAME = "scripted"

    def propose(self, view):
        cooled = {goal_key(c.get("type"), c.get("args")) for c in view.get("cooled") or () if isinstance(c, dict)}
        return next((g for g in self.candidates(view) if goal_key(g.TYPE, g.args()) not in cooled), Rest(REST_S))

    def candidates(self, view):
        """The goals in the scripted order (the module docstring), each one the view admits."""
        level = (view.get("load") or {}).get("level")
        loot_ok = not _num(level) or level <= LOOT_MAX_LEVEL
        wanted, ready = view.get("needs_wanted") or (), view.get("stock_uses") or ()
        if loot_ok:
            for kind in STOCK_KINDS:
                if kind in wanted and kind in ready:
                    yield Stock(kind)
        bs = _nearest_first(view.get("buildings") or ())
        if view.get("want_shelter"):
            for b in bs:
                if b.get("shelter") and not b.get("shunned"):
                    yield Shelter(b["id"])
        if loot_ok:
            for b in bs:
                if b.get("looted") is False and (b.get("containers") or 0) > 0:
                    yield LootBuilding(b["id"])
        edge = view.get("edge")
        if edge:
            yield ExploreToward(int(edge[0]), int(edge[1]))
        pos = view.get("pos") or {}
        if not view.get("scanned_here") and _num(pos.get("x")) and _num(pos.get("y")):
            yield ExploreToward(int(math.floor(pos["x"])), int(math.floor(pos["y"])))


# ---------------------------------------------------------------- the runner
class GoalRunner:
    def __init__(self, source, clock=time.time, shunned=None):
        self.source = source
        self.clock = clock
        self.t0 = clock()
        self.kit = Kit(clock=clock, shunned=shunned)
        self.current = None
        self.history = []      # loop.goals: {type, args, state, reason, startS, endS, source} per goal run
        self.cooled = {}       # goal_key -> wall until a goal that failed having sent nothing is refused
        self.why = {}
        self.actions = None
        self.pending = False   # the source answered None (P23-AC) on the last ask and no goal runs
        self.hold_ticks = 0    # planner ticks in a row another branch held without sending, the goal running (M-7)
        self._ended_now = None
        self._observed = False

    def _name(self):
        return getattr(self.source, "NAME", None)

    def _s(self, wall):
        return wall - self.t0 if _num(wall) else None

    def _close(self, g):
        now = self.clock()
        self.history.append(dict(g.row(), startS=self._s(g.started_wall), endS=self._s(now), source=self._name()))
        if g.state == "failed" and g.sent_n == 0:
            self.cooled[goal_key(g.TYPE, g.args())] = now + GOAL_COOL_S
        self._ended_now, self.current, self.hold_ticks = g, None, 0

    def cooling(self):
        """The goals cooled now, as `[{type, args}]` sorted (the view's `cooled`)."""
        now = self.clock()
        return [{"type": k[0], "args": json.loads(k[1])} for k, until in sorted(self.cooled.items()) if until > now]

    def observe(self, world, actions):
        """The kit's bookkeeping and the running goal's pre-emption and budget (the module docstring); Survive calls
        it every tick before its branches."""
        self.actions = actions
        self._ended_now, self._observed = None, True
        self.kit.observe(world, actions)
        g = self.current
        if g is None:
            return
        top = actions.history[-1] if actions.history else None
        if top is not (g.last if g.last is not None else g.mark):
            g.end("superseded", top.type)
        elif self.hold_ticks >= GOAL_HOLD_SUPERSEDE_TICKS:
            g.end("superseded", "hold")
        elif self.clock() - g.started_wall > g.budget():
            g.end("failed", "goal budget")
        if not g.running:
            self._close(g)

    def tick(self, world, actions, view=None):
        """The goal's command this tick, or None (the module docstring)."""
        if not self._observed:
            self.observe(world, actions)
        self._observed = False
        ended = self.history[-1] if self._ended_now is not None else None
        proposed, refused = None, None
        g = self.current
        if g is not None:
            g.observe(world, actions, self.clock)
            if not g.running:
                self._close(g)
                ended = self.history[-1]
        if self.current is None:
            g = self.source.propose(view() if callable(view) else (view if view is not None else {}))
            self.pending = g is None
            if g is not None and self.cooled.get(goal_key(g.TYPE, g.args()), 0.0) > self.clock():
                refused, g = {"type": g.TYPE, "args": g.args()}, None
            if g is None:
                self.why = {"proposed": None, "refused": refused, "ended": ended, "pending": self.pending}
                return None
            proposed = g.TYPE
            g.started_wall, g.kit = self.clock(), self.kit   # the budget starts here, never while pending
            g.mark = actions.history[-1] if actions.history else None
            self.current, self.hold_ticks = g, 0
        cmd = g.step(world, actions, self.clock)
        if not g.running:
            self._close(g)
            cmd = None
        self.why = dict(g.why, goal=g.TYPE, args=g.args(), state=g.state, reason=g.reason, proposed=proposed,
                        ended=ended)
        return cmd

    def held(self, by_other):
        """Survive's report at the end of each tick: `by_other` when a branch other than the goal answered with no
        command (a hold that sends nothing). Counts the ticks in a row while a goal runs (M-7)."""
        self.hold_ticks = self.hold_ticks + 1 if by_other and self.current is not None else 0

    def send(self, cmd):
        action = self.actions.send(cmd)
        if self.current is not None:
            self.current.sent(cmd, action)
        return action

    def rows(self):
        """loop.goals: every goal that ended (copies of `history`), then the running one with endS None."""
        rows = [dict(r) for r in self.history]
        g = self.current
        if g is not None:
            rows.append(dict(g.row(), startS=self._s(g.started_wall), endS=None, source=self._name()))
        return rows

    def line(self):
        g = self.current or self._ended_now
        if g is None:
            return {"pending": self._name()} if self.pending else None
        return {"type": g.TYPE, "args": g.args(), "state": g.state, "source": self._name()}
