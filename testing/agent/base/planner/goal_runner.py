"""The goal runner and the sources (`goals.py`'s module docstring the record): `validate` (a goal checked against
`schema/goals.json`), the `GoalSource` seam, the `ScriptedSource` and the `GoalRunner`. Moved out of `goals.py` at
Plan 25 Task 2 (a pure move: every rule and constant unchanged; the constants and the shared reads stay in
`goals.py`, which re-exports every name here).
"""
import json
import math
import time
from typing import Optional, Protocol, runtime_checkable

from agent.base.planner.goal_policies import ExploreToward, Goal, Kit, LootBuilding, Rest, Shelter, Stock, TYPES
from agent.base.planner.goals import (BUILDING_R, COOL_REASONS, GOAL_COOL_S, GOAL_HOLD_SUPERSEDE_TICKS,
                                      OPTIONAL_FIELDS, REST_S, SCHEMA_PATH, STOCK_KINDS, _num, goal_key, int_id)
from agent.base.planner.policies import LOOT_MAX_LEVEL
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
        self._ended_now = None
        self._observed = False

    def _name(self):
        return getattr(self.source, "NAME", None)

    def _s(self, wall):
        return wall - self.t0 if _num(wall) else None

    def _close(self, g):
        now = self.clock()
        self.history.append(dict(g.row(), startS=self._s(g.started_wall), endS=self._s(now), source=self._name()))
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
        self.actions = actions
        self._ended_now, self._observed = None, True
        self.kit.observe(world, actions)
        self.kit.read_buildings(world)
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
            seen = self._carried(view)
            g = self.source.propose(seen)
            self.pending = g is None
            if g is not None and self.cooled.get(goal_key(g.TYPE, g.args()), 0.0) > self.clock():
                refused, self.refusal, g = {"type": g.TYPE, "args": g.args()}, self._refusal(g), None
            if g is None:
                self.why = {"proposed": None, "refused": refused, "ended": ended, "pending": self.pending}
                return None
            proposed = g.TYPE
            g.started_wall, g.kit = self.clock(), self.kit   # the budget starts here, never while pending
            g.for_hold = bool(seen.get("spent"))   # a Rest under a hold is not "nothing to do here" (`Kit.rested`)
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
