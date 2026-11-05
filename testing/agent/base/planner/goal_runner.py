"""The goal runner and the sources (`goals.py`'s module docstring the record): `validate` (a goal checked against
`schema/goals.json`), the `GoalSource` seam, the `ScriptedSource` and the `GoalRunner`. Moved out of `goals.py` at
Plan 25 Task 2 (a pure move: every rule and constant unchanged; the constants and the shared reads stay in
`goals.py`, which re-exports every name here).

Ruling P27-F (`STUCK_LEAVE`, survival iteration 20; E19, `e_day_19-20261103-072904`: from game minute 639 to 781 the
character stood on one square north of the fence row's locked gate, its four goal walks from it toward the row's
unlocked door each `stuck` 5.992 to 5.994 s after its accept with the character unmoved, and the scripted source rested
17 times there): the runner keeps each goal walk it sends with the square and position it was sent from
(`GoalRunner.send`), and a walk that ends `failed "stuck"` with the frame's square equal to the send's marks the square
and the route's first edge out of it (`edges.first_edge` of the line to the walk's target) for STUCK_MARK_MIN game
minutes (`stuck_marks`, read by `stuck_at`; logged `stuck_mark` {edge, square, goal} on that tick's decision line,
`stuck_now`); the view carries the player's mark as `stuck` {square, edge}. The scripted source then never answers
`Rest` there: it takes the first way out not cooled (`ScriptedSource._ways_out`): the walk back to the nearest known
building on the square's side of the marked edge (its door, else its nearest room square), else a `LootBuilding` of the
nearest unlooted building, else an `ExploreToward` STUCK_LEAVE_R tiles from the square away from the edge, logged
`leave` {why "stuck", target {type, args}} on the runner's why of that pick. Cost if wrong: a walk away from an edge
the next session might cross.

Ruling P29-B (`GOAL_STALL`, survival iteration 23; F13, `f_goals_14-20261105-021722`: four ExploreTowards in a row
begun at the fence gate (10747, 10642) each ended `goal budget` with the character 0.0 tiles from where it began, the
model's calls reading one position, `last_goal` failed and `cooled` empty, and answering the view's own `edge` square
again, #4633, #4634): the runner keeps the player's position when it takes a goal (`Goal.start_xy`), and a `goal
budget` end of a goal with a target of its own (`Goal.stall_target`: an ExploreToward's square) with the character's
displacement since then under STALL_R is a stall (`_stall`): the goal cooled (GOAL_COOL_S, though it sent) and its
target marked (`mark_far`: `World.mark_stuck`, so the view's `edge` leaves it), logged `stall` {moved, target} on that
tick's decision line (`stall_now`), and the view carries the target as `stall` while the goal is cooled (`stalled`).
Cost if wrong: a far target dropped after one long stall.

Ruling P30-B (`GOAL_CONTINUE`, survival iteration 24; F14, `f_goals_15-20261105-092752`: the goal was pending on 275
decision lines, 181 of them with a zombie within 10 tiles, the character standing through each call, over 28 calls of
median 4.60 s; the model's ExploreToward hops ran 1 to 6 tiles, each followed by a 7 to 14 s wait standing, decision
lines 196 to 274): while the source is pending and no goal runs, the runner keeps a walk going (`_continue_walk`):
toward the last goal's walk target when that goal was superseded short of it (`last`: a threat's or another branch's
send cut the walk; a goal that ended done arrived, one that failed is not walked into again), else toward the view's
`edge` square (`edge`), at a walk, re-sent only when none is running, logged `goal_continue` {target, source "last" or
"edge"} on each such line (`continue_now`); within WALK_DONE_R of both, the runner stands as before. The answer's
goal replaces the leg (its first send supersedes the walk). The threat branch, above the goal's, pre-empts it as
before. And the hop (`goal_policies.hop_target`): an `ExploreToward` the model answered (`NAME` "llm") nearer than
EXPLORE_HOP_MIN is extended along its line toward `edge`, or to the last open square before the first unknown one,
logged `hop_extended` {from, to} on the line that takes it. Cost if wrong: a walk continued into a situation the model
would have changed (bounded by the threat branch's pre-emption); a longer hop past a building the model wanted looted.
"""
import json
import math
import time
from typing import Optional, Protocol, runtime_checkable

from agent.base.planner.edges import first_edge, same_side
from agent.base.planner.goal_policies import ExploreToward, Goal, Kit, LootBuilding, Rest, Shelter, Stock, TYPES
from agent.base.planner.goals import (ARRIVE_R, BUILDING_R, COOL_REASONS, GOAL_COOL_S, GOAL_HOLD_SUPERSEDE_TICKS,
                                      OPTIONAL_FIELDS, REST_S, SCHEMA_PATH, STOCK_KINDS, _num, goal_key, int_id)
from agent.base.planner.night import player_square
from agent.base.planner.policies import LOOT_MAX_LEVEL, STALL_R, STUCK_LEAVE_R, STUCK_MARK_MIN, WALK_DONE_R, me_xy
from agent.base.pza1 import WalkTo
from agent.base.planner.view import why_of


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
    obj = {k: v for k, v in obj.items() if k != "type" and not (v is None and k in OPTIONAL_FIELDS.get(t, ()))}
    for k, v in obj.items():
        _field(t, k, props[k], v)
    return TYPES[t](**obj)


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

    def __init__(self):
        self.last_leave = None   # P27-F: {why "stuck", target {type, args}} when the last pick left a marked square

    def propose(self, view):
        cooled = {goal_key(c.get("type"), c.get("args")) for c in view.get("cooled") or () if isinstance(c, dict)}
        self.last_leave = None
        g = next((g for g in self.candidates(view) if goal_key(g.TYPE, g.args()) not in cooled), None)
        if g is not None:
            return g
        g = next((g for g in self._ways_out(view) if goal_key(g.TYPE, g.args()) not in cooled), None)
        if g is None:
            return Rest(REST_S)
        self.last_leave = {"why": "stuck", "target": {"type": g.TYPE, "args": g.args()}}
        return g

    def _ways_out(self, view):
        """Ruling P27-F (the module docstring): the goals that leave the square the view's `stuck` marks, in order,
        where the scripted order would rest: an ExploreToward to each known building's door (else its nearest room
        square) on the player's side of the marked edge, nearest first, never one within ARRIVE_R nor blocked nor
        shunned; a LootBuilding of each building reading not looted and not blocked, nearest first (at a load the loot
        takes); then an ExploreToward STUCK_LEAVE_R tiles from the square away from the edge. Nothing without a mark."""
        stuck, pos = view.get("stuck"), view.get("pos") or {}
        if not isinstance(stuck, dict) or not (_num(pos.get("x")) and _num(pos.get("y"))):
            return
        me = (pos["x"], pos["y"])
        e = stuck.get("edge")
        edge = ((e[0], e[1], 0), e[2]) if e else None
        bs = _nearest_first(view.get("buildings") or ())
        for b in bs:
            to = b.get("door") or [b.get("x"), b.get("y")]
            if (b.get("blocked") or b.get("shunned") or not _num(b.get("dist")) or b["dist"] <= ARRIVE_R
                    or not all(int_id(v) for v in to)
                    or (edge is not None and not same_side(edge, me, (to[0] + 0.5, to[1] + 0.5)))):
                continue
            yield ExploreToward(to[0], to[1])
        level = (view.get("load") or {}).get("level")
        if not _num(level) or level <= LOOT_MAX_LEVEL:
            for b in bs:
                if b.get("looted") is False and not b.get("blocked"):
                    yield LootBuilding(b["id"])
        if edge is not None:
            (hx, hy, _), side = edge
            x, y, r = int(math.floor(me[0])), int(math.floor(me[1])), int(STUCK_LEAVE_R)
            if side == "N":
                yield ExploreToward(x, y - r if me[1] < hy else y + r)
            else:
                yield ExploreToward(x - r if me[0] < hx else x + r, y)

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
        if loot_ok and "bandage" in wanted:   # P24-AB: a wound with nothing to dress it loots a known bandage first
            for b in bs:
                if ((b.get("holds") or {}).get("bandage") and _num(b.get("dist")) and b["dist"] <= BUILDING_R
                        and not b.get("blocked")):
                    yield LootBuilding(b["id"])
        if view.get("want_shelter"):
            for b in bs:
                if b.get("shelter") and not b.get("shunned"):
                    yield Shelter(b["id"])
        if loot_ok:
            for b in bs:
                if (b.get("looted") is False and (b.get("containers") or 0) > 0 and _num(b.get("dist"))
                        and b["dist"] <= BUILDING_R and not b.get("blocked")):   # P24-Z: every door stuck
                    yield LootBuilding(b["id"])
        toward = view.get("toward") or {}
        to = toward.get("door") or toward.get("square")
        if toward.get("for") == "unlooted" and to:
            yield ExploreToward(int(to[0]), int(to[1]))
        edge = view.get("edge")
        if edge:
            yield ExploreToward(int(edge[0]), int(edge[1]))
        if toward.get("for") == "cluster" and to:
            yield ExploreToward(int(to[0]), int(to[1]))
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
        self.cooled = {}       # goal_key -> wall until a goal that failed having sent nothing (or for a shun,
                               # COOL_REASONS: P25-G) is refused
        self.why = {}
        self.actions = None
        self.pending = False   # the source answered None (P23-AC) on the last ask and no goal runs
        self.hold_ticks = 0    # planner ticks in a row another branch held without sending, the goal running (M-7)
        self.refusal = None    # the last proposal refused as cooled, for the next proposal's view (`_carried`)
        self.stuck_leave = True   # ruling P27-F: Survive sets it each tick from its `STUCK_LEAVE`; off, no stuck mark
        self.stuck_marks = {}  # square (x, y, z) -> (world minutes, {edge, square, goal}) of a walk stuck unmoved there
        self.stuck_now = None  # this tick's stuck mark (P27-F), logged on the decision line, else None
        self.goal_stall = True   # ruling P29-B: Survive sets it each tick from its `GOAL_STALL`; off, no stall read
        self.stall_now = None  # this observe's stall (P29-B) {moved, target}, logged on the decision line, else None
        self.stall = None      # (goal_key, target) of the last stall, the view's `stall` while that goal is cooled
        self.goal_continue = True   # ruling P30-B: Survive sets it each tick from its `GOAL_CONTINUE`; off, a pending
                                    # source stands the character and no answer's hop is extended
        self.continue_now = None   # this tick's continued walk (P30-B) {target, source}, logged, else None
        self._continue = None  # (the continued walk's command, its Action once sent, its why) while it may run (P30-B)
        self._cut_target = None   # [x, y] of the last goal's walk when that goal was superseded short of it (P30-B)
        self._walk_target = None  # [x, y] of the running goal's last walk sent (P30-B)
        self.door_left = None     # this tick's edge a `leave` read past (ruling P30-C, set by the threat branch's
                                  # read): no continued walk targets a square across it
        self.world = None      # the World of the last observe (a sent walk's square is read off it)
        self._walks = []       # (walk Action, the send's square, the player's position, the goal's {type, args})
        self._ended_now = None
        self._observed = False

    def _name(self):
        return getattr(self.source, "NAME", None)

    def _s(self, wall):
        return wall - self.t0 if _num(wall) else None

    def _close(self, g):
        now = self.clock()
        self.history.append(dict(g.row(), startS=self._s(g.started_wall), endS=self._s(now), source=self._name()))
        self._cut_target = self._walk_target if g.state == "superseded" else None   # P30-B: `last`
        self._walk_target = None
        if g.state == "failed" and (g.sent_n == 0 or getattr(g, "cool", False) or g.reason in COOL_REASONS):
            self.cooled[goal_key(g.TYPE, g.args())] = now + GOAL_COOL_S
        self.kit.rested(g)
        self._ended_now, self.current, self.hold_ticks = g, None, 0

    def _refusal(self, g):
        """The cooled refusal of goal `g` as the next view's `last_goal` (Plan 25 Task 4, spec 2.2(b); F3 refused 14
        valid answers as cooled and told the model nothing): `{type, args, end: "cooled", why}`, `why` the meaning
        (`view.why_of`) of the goal's own last end in `history`, the one that cooled it, else "failed"."""
        key = goal_key(g.TYPE, g.args())
        row = next((r for r in reversed(self.history) if goal_key(r.get("type"), r.get("args")) == key), None)
        return {"type": g.TYPE, "args": g.args(), "end": "cooled", "why": why_of(row) if row is not None else "failed"}

    def _carried(self, view):
        """The view a proposal reads: `view` (called when callable, `{}` when None) with the last cooled refusal laid
        over its `last_goal`, once, as the LLM source lays its own refusals (P24-B 3); the refusal is then cleared."""
        v = view() if callable(view) else (view if view is not None else {})
        if self.refusal is not None:
            v, self.refusal = dict(v, last_goal=self.refusal), None
        return v

    def cooling(self):
        """The goals cooled now, as `[{type, args}]` sorted (the view's `cooled`)."""
        now = self.clock()
        return [{"type": k[0], "args": json.loads(k[1])} for k, until in sorted(self.cooled.items()) if until > now]

    def observe(self, world, actions):
        """The kit's bookkeeping and the running goal's pre-emption and budget (the module docstring); Survive calls
        it every tick before its branches."""
        self.actions, self.world = actions, world
        self._ended_now, self._observed, self.stall_now = None, True, None
        self.kit.observe(world, actions)
        self.kit.read_buildings(world)
        self._read_walks(world, actions)
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
            self._stall(world, g)
        if not g.running:
            self._close(g)

    def _stall(self, world, g):
        """Ruling P29-B (the module docstring): goal `g` ended `goal budget`; with `goal_stall` on, a target of its own
        and the player moved under STALL_R since the runner took it, the goal is cooled, its target marked
        (`mark_far`), the stall logged (`stall_now`) and kept for the view (`stall`)."""
        target = g.stall_target() if self.goal_stall else None
        if target is None or g.start_xy is None:
            return
        mx, my = me_xy(world)
        moved = math.hypot(mx - g.start_xy[0], my - g.start_xy[1])
        if moved >= STALL_R:
            return
        g.cool = True
        g.mark_far(world)
        self.stall_now = {"moved": moved, "target": list(target)}
        self.stall = (goal_key(g.TYPE, g.args()), list(target))

    def stalled(self):
        """Ruling P29-B: the last stall's target [x, y] while its goal is cooled, else None (the view's `stall`)."""
        if self.stall is None or self.cooled.get(self.stall[0], 0.0) <= self.clock():
            return None
        return list(self.stall[1])

    def _read_walks(self, world, actions):
        """Ruling P27-F (the module docstring): each goal walk sent (`_walks`) read once at its end; one that ended
        `failed "stuck"` with the player still on the send's square marks it, with the route's first edge, when
        `stuck_leave` is on (`stuck_now` names the mark this tick)."""
        self.stuck_now = None
        keep = []
        for w in self._walks:
            a, sq, pos, goal = w
            if not actions.done(a):
                keep.append(w)
            elif self.stuck_leave and a.state == "failed" and a.reason == "stuck" and player_square(world) == sq:
                edge = first_edge(world, pos, (a.args.get("x"), a.args.get("y")))
                self.stuck_now = {"edge": None if edge is None else [edge[0][0], edge[0][1], edge[1]],
                                  "square": [sq[0], sq[1]], "goal": goal}
                self.stuck_marks[sq] = (world.world_minutes(), self.stuck_now)
        self._walks = keep

    def stuck_at(self, world):
        """The player's square's stuck mark within STUCK_MARK_MIN game minutes, `{square, edge}`, else None (P27-F: the
        view's `stuck`)."""
        sq = player_square(world)
        m = self.stuck_marks.get(sq) if sq is not None else None
        if m is None or world.world_minutes() - m[0] >= STUCK_MARK_MIN:
            return None
        return {"square": m[1]["square"], "edge": m[1]["edge"]}

    def tick(self, world, actions, view=None):
        """The goal's command this tick, or None (the module docstring)."""
        if not self._observed:
            self.observe(world, actions)
        self._observed = False
        ended = self.history[-1] if self._ended_now is not None else None
        proposed, refused, route_end = None, None, None
        g = self.current
        if g is not None:
            g.observe(world, actions, self.clock)
            route_end = g.take_route_end()   # P29-A: a route leg's end read this tick, on this line's why
            if not g.running:
                self._close(g)
                ended = self.history[-1]
        if self.current is None:
            seen = self._carried(view)
            g = self.source.propose(seen)
            self.pending = g is None
            if g is not None and self.cooled.get(goal_key(g.TYPE, g.args()), 0.0) > self.clock():
                refused, self.refusal, g = {"type": g.TYPE, "args": g.args()}, self._refusal(g), None
            if g is None:
                cmd = self._continue_walk(world, actions, seen) if self.pending else None
                self.why = self._noted({"proposed": None, "refused": refused, "ended": ended, "pending": self.pending},
                                       route_end)
                if self.continue_now is not None:
                    self.why["goal_continue"] = self.continue_now   # P30-B: the walk kept going while pending
                return cmd
            self._continue, self.continue_now = None, None
            hop = self._hop(world, g, seen)
            proposed = g.TYPE
            g.started_wall, g.kit = self.clock(), self.kit   # the budget starts here, never while pending
            g.start_xy = me_xy(world)   # P29-B: where the goal began, its budget end's stall read
            g.for_hold = bool(seen.get("spent"))   # a Rest under a hold is not "nothing to do here" (`Kit.rested`)
            g.mark = actions.history[-1] if actions.history else None
            self.current, self.hold_ticks = g, 0
        cmd = g.step(world, actions, self.clock)
        route_end = g.take_route_end() or route_end
        if not g.running:
            self._close(g)
            cmd = None
        self.why = self._noted(dict(g.why, goal=g.TYPE, args=g.args(), state=g.state, reason=g.reason,
                                    proposed=proposed, ended=ended), route_end)
        leave = getattr(self.source, "last_leave", None) if proposed is not None else None
        if leave is not None:
            self.why["leave"] = leave   # P27-F: the source's pick that leaves a marked square
        if proposed is not None and hop is not None:
            self.why["hop_extended"] = hop   # P30-B: the model's short hop extended
        return cmd

    def _hop(self, world, g, seen):
        """Ruling P30-B (the module docstring): the model's ExploreToward answer `g` (the source's `NAME` "llm")
        extended (`ExploreToward.extend_hop` toward the view's `edge`); its `hop_extended` {from, to}, else None."""
        if not (self.goal_continue and self._name() == "llm" and g.TYPE == "ExploreToward"):
            return None
        edge = seen.get("edge")
        return g.extend_hop(world, edge if isinstance(edge, (list, tuple)) and len(edge) >= 2 else None)

    def _continue_walk(self, world, actions, seen):
        """Ruling P30-B (the module docstring): the walk kept going while the source is pending, else None. A walk it
        sent still running holds (None, `continue_now` its target); else a `WalkTo` at a walk toward the last goal's
        cut walk target (`last`), else toward the centre of the view's `edge` square (`edge`), whichever lies beyond
        WALK_DONE_R of the player and not across the edge a P30-C `leave` read this tick (`door_left`); neither, the
        runner stands (`continue_now` None)."""
        self.continue_now = None
        if not self.goal_continue:
            return None
        run = self._continue
        if run is not None and run[1] is not None and actions.current is run[1]:
            self.continue_now = dict(run[2])
            return None
        mx, my = me_xy(world)
        edge = seen.get("edge")
        on_edge = (edge[0] + 0.5, edge[1] + 0.5) if isinstance(edge, (list, tuple)) and len(edge) >= 2 else None
        for target, source in ((self._cut_target, "last"), (on_edge, "edge")):
            if target is not None and self.door_left is not None and not same_side(self.door_left, (mx, my), target):
                continue   # P30-C: never a walk past the door the threat branch left
            if target is not None and math.hypot(target[0] - mx, target[1] - my) > WALK_DONE_R:
                self.continue_now = {"target": [target[0], target[1]], "source": source}
                cmd = WalkTo(float(target[0]), float(target[1]), "walk")
                self._continue = (cmd, None, self.continue_now)
                return cmd
        self._continue = None
        return None

    def _noted(self, why, route_end):
        """`why` with this tick's route leg end (P29-A, `route_end`) and budget-end stall (P29-B, `stall`), when
        read."""
        if route_end is not None:
            why["route_end"] = route_end
        if self.stall_now is not None:
            why["stall"] = self.stall_now
        return why

    def held(self, by_other):
        """Survive's report at the end of each tick: `by_other` when a branch other than the goal answered with no
        command (a hold that sends nothing). Counts the ticks in a row while a goal runs (M-7)."""
        self.hold_ticks = self.hold_ticks + 1 if by_other and self.current is not None else 0

    def send(self, cmd):
        action = self.actions.send(cmd)
        g = self.current
        run = self._continue
        if g is None and run is not None and cmd is run[0]:
            self._continue = (cmd, action, run[2])   # P30-B: the continued walk, held while it runs
        if g is not None:
            g.sent(cmd, action)
            if cmd.TYPE == "walkTo":
                self._walk_target = [cmd.x, cmd.y]   # P30-B: the walk a supersede would cut
            sq = player_square(self.world) if cmd.TYPE == "walkTo" and self.world is not None else None
            if sq is not None:   # P27-F: the square and position the walk left from, its end read by `_read_walks`
                self._walks.append((action, sq, me_xy(self.world), {"type": g.TYPE, "args": g.args()}))
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
