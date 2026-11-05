"""The goals (`goals.py`'s module docstring the record: the goal types, their steps and the kit they share), the
policies a goal source proposes: `Kit`, `Goal` and its five types (`ExploreToward`, `LootBuilding`, `Shelter`,
`Stock`, `Rest`), their step mixins and `TYPES`. Moved out of `goals.py` at Plan 25 Task 2 (a pure move: every rule
and constant unchanged; the constants and the shared reads stay in `goals.py`, which re-exports every name here).
"""
import math
import time
from dataclasses import dataclass, field, fields
from typing import ClassVar, Optional

from agent.base.planner.edges import GoalEdge
from agent.base.planner.goals import (ARRIVE_R, GOAL_MAX_S, LEG_CHUNK, LEG_MAX, LEG_MIN, LEG_SQ_MARGIN, OPTIONAL_FIELDS,
                                      REST_N, RUN_FIELDS, WANT_USES, WOODS_MAX_R, WOODS_R, WOODS_STEP,
                                      held_of, looted, open_uses, wanted_uses, window_pick)
from agent.base.planner.night import (SHUN_MIN, door_blocked, hop_after, player_square, shelter_ended, shelter_plan,
                                      shelter_step)
from agent.base.planner.policies import (Explore, LOOT_MAX_LEVEL, LootHouse, PREEMPTED, SCAN_R, centre, me_floor, me_xy,
                                         place_of)
from agent.base.planner.windows import note_window_end
from agent.base.pza1 import Climb, Scan, WalkTo, Window


# ---------------------------------------------------------------- the shared machines
class Kit:
    """The machines a session's goals share: one `Explore` (its scanned places), one `LootHouse` (its pending loots,
    capped squares), `shunned` {building: world minutes}, the Shelter goals' shuns (`Night.shunned` when given, M6),
    and the woods radius (`woods_r`, `rests` the Rests in a row ended rested, `known` the buildings known when it was
    last reset: Task 18 fix 1, ruling 3), and `wants` (the uses a loot takes first: the care's `bandage`, P24-AB)."""

    def __init__(self, world=None, actions=None, clock=time.time, shunned=None):
        self.explore = Explore(world, actions, clock)
        self.loot = LootHouse(world, actions, clock)
        self.shunned = {} if shunned is None else shunned
        self.woods_r, self.rests, self.known = WOODS_R, 0, 0
        self.wants = ()   # the uses a loot takes first (Survive's need marks, `survive.KIT_WANTS`: P24-AB)
        self.shelter_legs = True   # ruling P25-N: a Shelter approaches a far door in legs (Survive's SHELTER_LEGS)
        self.blocked_edge = True   # ruling P25-X: a target beyond a known blocked edge routed or dropped (`_edge_cmd`)
        self.route_cross = True    # ruling P29-A: the route walks beyond the door and reads its end by the crossing
                                   # (Survive's ROUTE_CROSS, set each tick)

    def rested(self, goal):
        """A goal ended: a Rest ended rested counts one, REST_N in a row widening the woods radius by WOODS_STEP up
        to WOODS_MAX_R; any other goal's end restarts the count (a superseded Rest neither counts nor restarts it, nor
        does a Rest proposed under a hold: it was spent, not nothing to do here: Plan 25 Task 4 fix 1)."""
        if goal.TYPE != "Rest":
            self.rests = 0
        elif goal.state == "done" and not goal.for_hold:
            self.rests += 1
            if self.rests >= REST_N:
                self.woods_r, self.rests = min(self.woods_r + WOODS_STEP, WOODS_MAX_R), 0

    def read_buildings(self, world):
        """A building newly read (`World.building_boxes` grew) resets the woods radius to WOODS_R."""
        n = len(world.building_boxes())
        if n > self.known:
            self.woods_r, self.rests = WOODS_R, 0
        self.known = n

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
        """The route climb's read (ruling P24-G 4): `night.hop_after`, shared with `Night`'s own shelter walk."""
        return hop_after(world, action, climbed)

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
        self.for_hold = False  # proposed while the view read a hold (`spent`): the runner sets it, `Kit.rested`
                               # reads it
        self.mark = None       # the last action sent (by anyone) when the runner took this goal
        self.why = {}          # the goal's inputs to its last choice, logged under the goal branch
        self.sent_n = 0        # commands this goal sent
        self.start_xy = None   # the player's (x, y) when the runner took this goal (P29-B: its stall read)
        self._read = None      # the last action whose end observe() has read
        self._begun = False

    # -- the record ---------------------------------------------------------------------------------------------
    def args(self):
        """The schema fields, an optional one left unset (None: OPTIONAL_FIELDS) left out."""
        opt = OPTIONAL_FIELDS.get(self.TYPE, ())
        return {f.name: getattr(self, f.name) for f in fields(self)
                if f.name not in RUN_FIELDS and not (f.name in opt and getattr(self, f.name) is None)}

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

    def stall_target(self):
        """Ruling P29-B: the goal's walk target [x, y] its budget end is read against (`GoalRunner._stall`), else
        None: a goal with no walk target (a Rest stands by design; a Stock's loot walks itself) is never a stall.
        ExploreToward its square; LootBuilding its last walk's (fix 1, M1); Shelter its plan's door square."""
        return None

    def take_route_end(self):
        """Ruling P29-A: the route leg's end read since the last take (`_Legs`'s `route_end`, `edges.route_end`'s why),
        else None; cleared, so the runner logs it on the one line that read it."""
        end = getattr(self, "route_end", None)
        self.route_end = None
        return end


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


def leg_max(world):
    """Ruling P24-AI (#4375): the longest goal leg, `LEG_CHUNK * floor(width / 16) - LEG_CHUNK` tiles off the World's
    last `me.loadedWidth` (40 at 104 tiles, 64 at 152: half the window's chunks less the player's own, one chunk to
    spare for a chunk not yet streamed in at the edge), never under LEG_MIN; LEG_MAX with no width read."""
    w = getattr(world, "loaded_width", None)
    if not isinstance(w, int) or isinstance(w, bool) or w <= 0:
        return LEG_MAX
    return max(float(LEG_CHUNK * (w // (2 * LEG_CHUNK)) - LEG_CHUNK), LEG_MIN)


class _Legs(GoalEdge):
    """Ruling P24-AC (Plan 24 Task 21; E8, `e_day_8-20261029-174023`: from game minute 618 every one of the goal's 278
    walks failed `no square` within 0.53 s, its targets 62 to 234 tiles off, each failure marking the target stuck so
    the edge stepped to the next far square): a goal destination farther than `leg_len` (`leg_max`, P24-AI) is approached in
    legs along the straight line, each a `WalkTo` at a walk to the centre of the square `leg_len` - LEG_SQ_MARGIN
    tiles toward it (so within `leg_len`); a leg that ends done restores the full length and the next leg follows; one that
    fails `no square` (the client holds no square there) halves `leg_len`, down to LEG_MIN, and the next leg is
    re-sent shorter; at LEG_MIN a `no square` fails the goal. A leg's `no square` never marks a square stuck
    (`Explore.sent`'s `leg`), so the far target stays the goal's. `_legs()` once at the start; `_leg_cmd(world, x, y)`
    the leg toward (x, y), else None when it lies within `leg_len` (the direct walk is the goal's own); `_leg_ended(
    action, world)` "next" (go on), "fail" (the leg's own failure: the goal reads it) or None (not a leg). Ruling P25-X
    (`edges.GoalEdge._edge_cmd`, `_edge_leg`): a target beyond a known blocked edge is first routed through its unlocked
    door, the route a leg, or the goal ends `failed "blocked edge"`, cooled. Ruling P29-A (the kit's `route_cross`): a
    route leg ended done is read by whether it crossed (`edges.GoalEdge._route_ended`, given the `world`), never as
    "next" by its `done` alone."""

    def _legs(self):
        self.leg_len = None      # tiles: the next leg's length, None for the full `leg_max` (P24-AI: read at each leg)
        self.leg = None          # (x, y) of the leg the last choose sent, else None
        self.cool = False        # a leg failed for good: the runner cools the goal though it sent (`GoalRunner._close`)
        self.edge_route = None   # P29-A: the running route leg's record (`edges.GoalEdge._edge_cmd`), else None
        self.route_end = None    # P29-A: its end's `route_end` why, until the runner takes it (`Goal.take_route_end`)

    def _leg_cmd(self, world, x, y):
        if self.leg_len is None:
            self.leg_len = leg_max(world)
        mx, my = me_xy(world)
        d = math.hypot(x - mx, y - my)
        if d <= self.leg_len:
            self.leg = None
            return None
        k = (self.leg_len - LEG_SQ_MARGIN) / d
        self.leg = centre((mx + (x - mx) * k, my + (y - my) * k))
        return WalkTo(self.leg[0], self.leg[1], "walk")

    def _edge_leg(self, world, x, y):
        """P25-X's route toward (x, y) within the leg length (`leg_max`), else None (`_edge_cmd`)."""
        return self._edge_cmd(world, x, y, leg_max(world))

    def _leg_ended(self, action, world=None):
        if self.leg is None or action.type != "walkTo" or (action.args.get("x"), action.args.get("y")) != self.leg:
            return None
        self.leg = None
        route = self._route_ended(world, action) if world is not None else None   # P29-A: crossed or a door failure
        if route is not None:
            self.leg_len = None
            return route
        if action.state == "done":
            self.leg_len = None   # the full length again, read off the window at the next leg
            return "next"
        if action.reason == "no square" and self.leg_len is not None and self.leg_len > LEG_MIN:
            self.leg_len = max(self.leg_len / 2.0, LEG_MIN)
            return "next"
        return "fail"

    def _leg_failed(self, world):
        """A leg's final failure (`no path`; `stuck` with no fence to climb; `no square` at LEG_MIN; review-t21's
        blocker, the E8 loop without the edge's stepping): the goal is cooled for GOAL_COOL_S whatever it sent, so the
        source proposes another; a goal with a far target of its own (`mark_far`) marks it as a direct walk's failure
        would."""
        self.cool = True
        self.mark_far(world)

    def mark_far(self, world):
        """The goal's far target marked stuck (ExploreToward's; a loot's container is left to the cooling)."""


@dataclass
class ExploreToward(_Legs, _Climbing, Goal):
    TYPE: ClassVar[str] = "ExploreToward"
    x: int
    y: int

    def _dist(self, world):
        mx, my = me_xy(world)
        return math.hypot(self.x - mx, self.y - my)

    def start(self, world):
        self._climbs()
        self._legs()

    def mark_far(self, world):
        world.mark_stuck(self.x, self.y)

    def stall_target(self):
        return [self.x, self.y]

    def ended(self, world, action):
        leg = self._leg_ended(action, world)
        if leg == "next":
            return
        if action.type == "walkTo":
            if action.state == "done":
                self.end("done", "arrived")
            elif not self._stuck(world, action):
                if leg == "fail":
                    self._leg_failed(world)
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
        route = self._edge_leg(world, self.x, self.y)   # P25-X: across a known blocked edge, its door or no walk
        if route is not None or not self.running:
            return route
        leg = self._leg_cmd(world, self.x, self.y)   # P24-AC: a far target in legs
        if leg is not None:
            self.why.update(leg=[leg.x, leg.y], legLen=self.leg_len)
            return leg
        return WalkTo(self.x, self.y, "walk")

    def sent(self, cmd, action):
        super().sent(cmd, action)
        self.kit.explore.sent(cmd, action, leg=self.leg is not None and cmd.TYPE == "walkTo")


class _Looting:
    """The loot goals' shared send: the kit's LootHouse records its pending loot (a loot's own interact only, never a
    route step's open)."""

    def sent(self, cmd, action):
        super().sent(cmd, action)
        if cmd.TYPE == "interact" and cmd.args().get("kind") == "loot":
            self.kit.loot.sent(cmd, action)

    def _guard(self):
        level = self.kit.loot.level()
        if level > LOOT_MAX_LEVEL:
            self.why = {"level": level, "hold": True}
            self.end("failed", "load")
            return True
        return False


@dataclass
class LootBuilding(_Legs, _Looting, Goal):
    TYPE: ClassVar[str] = "LootBuilding"
    building: int
    want: Optional[str] = None

    def start(self, world):
        self._legs()
        self.base = held_of(world, self.want) if self.want is not None else None   # Task 29: the want's held count
        self.route = None        # the entry plan (night.shelter_plan) while the route is due (P24-Z), else None
        self.route_due = False   # a loot failed `not adjacent`: in by a door the World has not marked first
        self.window = None       # the window route's (x, y, z) while its Window runs, else None (Task 24)
        self.no_doors = False    # the route's doors are spent (the plan answered none or the machine shunned): windows

    def keys(self, world):
        """The container keys on the building's squares."""
        return {k for k in world.containers if (world.map.get(k[:3]) or {}).get("building") == self.building}

    def _inside(self, world):
        sq = player_square(world)
        s = world.map.get(sq) if sq is not None else None
        return s is not None and s.get("room") is not None and s.get("building") == self.building

    def ended(self, world, action):
        """A loot failed `not adjacent` makes the route due (P24-Z); a route step's end is read into its plan
        (`night.shelter_ended`), `shun` (no door left) failing the goal `no door`; a leg toward a far container
        (P24-AC) goes on, or fails the goal under its reason."""
        leg = self._leg_ended(action, world)
        if leg is not None:
            if leg == "fail":
                self._leg_failed(world)
                self.end("failed", action.reason or action.state)
            return
        if action.type == "interact" and action.args.get("kind") == "loot":
            if action.state == "failed" and action.reason == "not adjacent":
                self.route_due = True
            return
        if action.type == "window":
            self._window_ended(world, action)
            return
        if self.route is not None:
            out = shelter_ended(self.route, action)
            self.why = dict(self.why, ended=out)
            if out == "shun":
                self.route, self.no_doors = None, True   # no exterior door left: the window route, else it fails
                if window_pick(world, self.building, self.kit.shunned_now(world)) is None:
                    self.end("failed", "no door")

    def check(self, world, clock):
        if self.want is not None and held_of(world, self.want) > self.base:
            self.why = dict(self.why, want=self.want, met=True)
            self.end("done", "want met")

    def _wants(self):
        """The kit's wants, then the goal's want's use (Task 29): the wants `wanted_uses` puts first."""
        use = WANT_USES.get(self.want)
        return tuple(self.kit.wants) + ((use,) if use is not None and use not in self.kit.wants else ())

    def _uses(self, world):
        """The uses in the order the loot takes them (`_wants` first)."""
        return wanted_uses(world, self._wants())

    def stall_target(self):
        """Ruling P29-B (fix 1, M1): the square of the walk this loot last sent (a route or a leg target, or a walk to
        a container), else None when its last send was not a `walkTo`: a loot working through one room's containers
        (each an `interact` the Lua walks to) for its budget is no stall. `mark_far` stays a no-op (the cooling and the
        view's `stall` square are the stall's reads)."""
        a = self.last
        if a is None or a.type != "walkTo":
            return None
        x, y = a.args.get("x"), a.args.get("y")
        if x is None or y is None:
            return None
        return [int(x // 1), int(y // 1)]   # the integer square, as edge, stuck and the explore stall read (fix 1 r1)

    def _window_ended(self, world, action):
        """A window action's end (Task 24): done leaves the route (the character stands inside; the care branch reads the
        wounds from the frame's body parts whatever `cut` says, the result's `cut` being unreliable in multiplayer: it is
        logged); a failure leaves the window out (`World.note_window_fail`): `locked` lets the next try smash it."""
        sq = self.window
        self.window = None
        if action.state == "done":
            self.route_due = False
            res = action.result if isinstance(action.result, dict) else {}
            self.why = dict(self.why, ended="window", cut=res.get("cut"), wounds=res.get("wounds"))
            return
        if sq is not None:
            note_window_end(world, sq, action)   # review-t24 major 2, P26-7c: the one failure leg
        self.why = dict(self.why, ended="window " + (action.reason or action.state))

    def _route(self, world):
        """The route's next step while it is due and the player is not inside the building, else None (the route
        done or not due); with no unmarked exterior door left (`night.shelter_plan` answers none, or the machine shuns
        every door) the window route (`_window_pick`, one `Window` at a time), else the goal ends `failed "no door"`."""
        if not self.route_due or self._inside(world):
            self.route_due, self.route, self.window, self.no_doors = False, None, None, False
            return None
        if self.route is None and not self.no_doors:
            self.route = shelter_plan(world, self.building)
        cmd, step = (None, "shun") if self.route is None else shelter_step(world, self.route)
        if step == "shun":
            self.route = None
            pick = window_pick(world, self.building, self.kit.shunned_now(world))
            if pick is None:
                self.why = {"building": self.building, "route": None}
                self.end("failed", "no door")
                return None
            self.window = pick[:3]
            self.why = {"building": self.building, "route": "window", "window": [pick[0], pick[1]], "smash": pick[3]}
            return Window(pick[0], pick[1], smash=pick[3])
        if step in ("close", "done"):   # in: the loot resumes from inside
            self.route_due, self.route = False, None
            return None
        door = self.route["doors"][self.route["door_i"]]
        self.why = {"building": self.building, "route": step, "door": [door[0], door[1]]}
        return cmd

    def choose(self, world, actions, clock):
        if self._guard():
            return None
        if (not self.route_due and world.can("window") and not self._inside(world)
                and door_blocked(world, self.building, me_floor(world))):
            self.route_due = True   # Task 24: every exterior door marked from outside, so the loot is not tried first
        cmd = self._route(world)
        if cmd is not None or not self.running:
            return cmd
        loot = self.kit.loot
        loot.within = self.keys(world)
        try:   # Plan 25 Task 4: `looted`, the view's `L`, is the rule `nothing to loot` reads
            want = None if looted(world, self.building, loot, self._wants(), keys=loot.within) else next(
                (u for u in self._uses(world) if loot.target(u) is not None), None)
            if want is not None:
                key = loot.target(want)
                self.why = {"building": self.building, "want": want, "container": list(key)}
                route = self._edge_leg(world, *centre(key))   # P25-X: across a known blocked edge, its door or none
                if route is not None or not self.running:
                    return route
                leg = self._leg_cmd(world, *centre(key))   # P24-AC: a container beyond the leg length is walked to in legs
                if leg is not None:
                    self.why = {"building": self.building, "want": want, "container": list(key),
                                "leg": [leg.x, leg.y], "legLen": self.leg_len}
                    return leg
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
class Shelter(_Legs, _Climbing, Goal):
    TYPE: ClassVar[str] = "Shelter"
    building: int

    def start(self, world):
        """The plan, before any walk: a building the kit shuns now ends the goal `failed "shunned"` (ruling P25-G, F4:
        57 Shelters of a shunned building each walked and failed `shun` within 1.5 s; its stamp untouched, so the span
        does not restart); a building with no plan is shunned (I3: never re-proposed every tick)."""
        self._climbs()
        self._legs()
        self.plan = None
        if self.building in self.kit.shunned_now(world):
            self.why = {"building": self.building, "shunned": True}
            self.end("failed", "shunned")
            return
        self.plan = shelter_plan(world, self.building)
        if self.plan is None:
            self.why = {"building": self.building, "plan": None}
            self._shun(world, "no plan")

    def stall_target(self):
        """Ruling P29-B (fix 1, M1): the plan's current door square [x, y], else None (no plan)."""
        if self.plan is None:
            return None
        door = self.plan["doors"][self.plan["door_i"]]
        return [door[0], door[1]]

    def _shun(self, world, reason="shun"):
        self.kit.shunned[self.building] = world.world_minutes()
        self.end("failed", reason)

    def ended(self, world, action):
        """A step's end into the plan (`shelter_ended`); a walk stuck at a hoppable edge climbs first (the plan's step
        kept), and a climb that did not end done is read as that walk's own stuck end. Ruling P25-N: a leg toward the
        door (`_Legs`) goes on, done or halved on `no square`; its final failure ends the goal under its reason, cooled
        (`_leg_failed`), the building not shunned (the stamp is the machine's) and the plan's step untouched."""
        if action.type == "climb":
            if self._climb_ended(world, action):
                self.why = dict(self.why, ended="climbed")
                return
            action = self.stuck_walk
        elif self._stuck(world, action):
            self.why = dict(self.why, ended="climb")
            return
        leg = self._leg_ended(action, world)
        if leg is not None:
            self.why = dict(self.why, ended="leg")
            if leg == "fail":
                self._leg_failed(world)
                self.end("failed", action.reason or action.state)
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
        door = self.plan["doors"][self.plan["door_i"]]
        self.why = {"step": step, "building": self.building, "door": list(door)}
        if step == "shun":
            self._shun(world)
            return None
        if step == "done":
            self.end("done", "inside")
            return None
        if step == "approach":
            route = self._edge_leg(world, *centre(door))   # P25-X: across a known blocked edge, its door or none
            if route is not None or not self.running:
                return route
        if step == "approach" and self.kit.shelter_legs:
            leg = self._leg_cmd(world, *centre(door))   # P25-N: a door beyond the leg length is walked to in legs
            if leg is not None:
                self.why.update(leg=[leg.x, leg.y], legLen=self.leg_len)
                return leg
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
