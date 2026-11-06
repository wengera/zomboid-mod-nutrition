"""The utility decider's tick (Plan 31 Task 11 U): `Utility.assess(inputs) -> Decision`, the fork's `assess` for
`Survive(control="utility")`. Its state lives on `survive.control_state["utility"]` (this object).

One tick: the frame's features (`features.read`, after `Tracks.update`), the running executor's ends (`observe`),
the context (`context`: the goal, the needs, the door read, the marks, the dress's cooling, the filter stood on), the
candidates (`acts.generate`), their scores (`select.score_all`), the interrupts, the commitment (`Selector.decide`),
then the held act's executor (`execute.EXECUTORS`) for the tick's command. An executor that ends on its first step
(the goal runner holding nothing, the needs gone) is passed over once, the next best taken uncommitted (the selector
dropped, so the next tick chooses afresh).

The line (the fork's contract, `planner/control.py`): `branch` "threat" on a fight or a retreat tick, the retreat's
reason at `inputs.branches.threat.flee` ("retreat:door"), `inputs.x`/`inputs.y` from `_read`; a kill read this tick
at `inputs.branches.threat.kill` (P24-Q's field) and the door read's decision at `inputs.branches.threat.door_held`
(P30-C's), whatever answered. The scorecard's label (`tools/trial_score.py`): `inputs.intent` {kind, target}, kind
the act's (`retreat:door` for a retreat, so it reads both a retreat and a refuge; `meet:stand` for the stand), target
the zombie id of a fight or a stand,
the filter's door square [x, y] of a retreat, the goal's square of a travel, a loot or a sneak (none for a dress, the
needs or the rest: a part index is no square). The utility's own: `inputs.utility` {act, kind, target, scores {key:
[total, {term: weighted}]}, vetoes {key: why}, runner_up, margin, held_by, select, interrupts, end; ride, note and
passed (the act chosen first whose executor ended on its first step, on a fallback's line) when set}, every float
rounded to LOG_DIGITS.
"""
import json

from agent.base.planner.care import DRESS_RETRY_S
from agent.base.planner.policies import DANGER_R, KEEP_R, UNREACHABLE_S, blocked
from agent.base.planner.survive import Decision
from agent.base.planner.utility import acts as A
from agent.base.planner.utility import execute as X
from agent.base.planner.utility import features as F
from agent.base.planner.utility import models as M
from agent.base.planner.utility import select as S

LOG_DIGITS = 6            # the line's floats: enough to rescore, short enough to read
LOOT_GOALS = ("LootBuilding", "Stock")   # the goal types the goal candidate is labelled `loot` under
NEED_STEPS = ("need", "load", "night", "care", "stock")   # the ladder's quiet steps, in its order (`survive.STEPS`)
STATE_KEY = "utility"
LABELS = {"stand": "meet:stand"}   # the scorecard's label of a kind not its own word: the stand is a meet in place
                                   # (`tools/trial_score.py` KNOWN_LABELS: `meet`), never a retreat


def _r(v):
    return round(v, LOG_DIGITS) if isinstance(v, float) else v


class Utility:
    """The decider (the module docstring)."""

    def __init__(self, survive, models=M.FITTED, weights=None):
        self.sv = survive
        self.models = models
        self.weights = weights
        self.tracks = F.Tracks()
        self.selector = S.Selector()
        self.ex = None
        self.retired = []         # maneuvers of replaced executors whose late ends (a kill) are still read
        self.unreach = {}         # zombie id -> wall until it is skipped (a melee's `out of reach`)
        self.at_filter = None     # the Filter a retreat arrived at, while the player stands on it
        self.dress_fail = None    # (wall, held item ids) of the last Dress that failed
        self.needs_answer = None
        self.dead_now = frozenset()
        self.kill_now = None
        self._near = frozenset()
        self._reach = frozenset()
        self._goal_key = None
        self.goal_answer = None   # ((owner, cmd) or None, why) of the runner's tick the context's proposal made

    # -- the hooks the executors call -----------------------------------------------------------------------------
    def killed(self, zid):
        sv = self.sv
        if sv.world.note_kill(zid):
            self.kill_now = zid
        sv.dead[zid] = sv.clock() + UNREACHABLE_S

    def mark_unreachable(self, zid, seconds):
        self.unreach[zid] = self.sv.clock() + seconds

    def dress_failed(self):
        self.dress_fail = (self.sv.clock(), frozenset(self.sv.world.inventory))

    def take_goal_answer(self):
        """The goal runner's answer the context's proposal read this tick, once (`execute.GoalExec`), else None."""
        out, self.goal_answer = self.goal_answer, None
        return out

    # -- the reads ------------------------------------------------------------------------------------------------
    def _observe_retired(self):
        for m in self.retired:
            m.observe()
            for zid in m.take_kills():
                self.killed(zid)
        self.retired = [m for m in self.retired if not m.drained()]

    def _needs(self, sit):
        """The ladder's quiet steps in order (NEED_STEPS), the first that answers: (branch, owner, cmd, why), else
        None; only with no standing zombie within DANGER_R, the care's only with nothing bleeding (the dress is this
        decider's), a cooled command passed over as the ladder does (`Survive._cooling`)."""
        sv = self.sv
        sv.need_mark = None
        if sit.standing(DANGER_R):
            return None
        for name in NEED_STEPS:
            if name == "care" and sit.bleeding:
                continue
            sv.why = {}
            ans = sv._care_stock() if name == "stock" else getattr(sv, "_" + name)()
            if ans is None:
                continue
            owner, cmd = ans
            if cmd is not None and sv._cooling(cmd) and not sv.care.owns(cmd):
                continue
            return (name if name != "stock" else "care"), owner, cmd, dict(sv.why)
        return None

    def _goal_read(self, group):
        """(the goal candidate's label or None, its target (x, y) or None). A goal is a candidate only while the runner
        holds one running or a source pending (fix 1, review-t11-utility m6); with neither and no group arriving the
        runner is asked to propose (its tick, kept for the executor: `take_goal_answer`), as the ladder's last branch
        asks it. The target: the goal's `stall_target`, else its args' square."""
        sv = self.sv
        self.goal_answer = None
        goals = sv.goals
        if getattr(goals, "current", None) is None and not goals.pending:
            if group:
                return None, None
            sv.why = {}
            self.goal_answer = (sv._goal(), dict(sv.why))
            if getattr(goals, "current", None) is None and not goals.pending:
                return None, None
        line = goals.line() or {}
        g = getattr(goals, "current", None)
        target = g.stall_target() if hasattr(g, "stall_target") else None
        args = line.get("args") or {}
        if target is None and all(isinstance(args.get(k), (int, float)) for k in ("x", "y")):
            target = (args["x"], args["y"])
        return ("loot" if line.get("type") in LOOT_GOALS else "travel"), target

    def context(self, sit):
        sv = self.sv
        now = sv.clock()
        group = A.group_arriving(sit)
        goal, target = self._goal_read(group)
        cooled = False
        if self.dress_fail is not None:
            at, held = self.dress_fail
            cooled = now - at < DRESS_RETRY_S and frozenset(sv.world.inventory) <= held
        if self.at_filter is not None and not A.filter_at(sit, self.at_filter):
            self.at_filter = None
        self.needs_answer = None if group else self._needs(sit)
        return A.Context(
            goal=goal, goal_target=target,
            needs=None if self.needs_answer is None else self.needs_answer[0],
            door_open=(sv.door_open or {}).get("zid"),
            unreachable=frozenset(blocked(sv.unreachable, now) | set(sv._edge_out()) | blocked(self.unreach, now)),
            dress_cooled=cooled, held_kind=self.selector.kind, at_filter=self.at_filter,
            held_target=self.ex.target if self.ex is not None and self.ex.kind == "fight" else None)

    def _want(self, cands, now):
        """Ruling P24-AB's want, as the care branch marks it: a bleeding part with nothing to dress it and nothing to
        tear (the dress vetoed `nothing`) marks `bandage` for the goal's loot (`goals.Kit.wants`); a tick with none
        drops it."""
        if any(c.kind == "dress" and c.veto == "nothing" for c in cands):
            self.sv.need_marks["bandage"] = now
        else:
            self.sv.need_marks.pop("bandage", None)

    def interrupts(self, sit):
        out = []
        if sit.hit_onset:
            out.append("hit")
        if sit.new_bleeding:
            out.append("bleeding")
        held = self.ex.target if self.ex is not None and self.ex.kind == "fight" else None
        near = frozenset(z.id for z in sit.standing(S.NEAR_R))
        if near - self._near - {held}:
            out.append("near")
        self._near = near
        reach = frozenset(z.id for z in sit.aware_standing(KEEP_R))
        if reach - self._reach - {held}:
            out.append("reach")   # fix 1: an aware zombie come within the stance's reach, chosen for afresh
        self._reach = reach
        line = self.sv.goals.line() or {}
        key = (line.get("type"), json.dumps(line.get("args"), sort_keys=True)) if line.get("type") else None
        if key is not None and key != self._goal_key:
            out.append("goal")
        self._goal_key = key
        return out

    # -- the tick -------------------------------------------------------------------------------------------------
    def assess(self, inputs):
        sv = self.sv
        now = sv.clock()
        self.kill_now = None
        self.dead_now = frozenset(blocked(sv.dead, now))
        self.tracks.update(sv.world, now, self.dead_now)
        sit = F.read(sv.world, now, self.tracks, self.dead_now)
        self._observe_retired()
        ended = None
        if self.ex is not None:
            self.ex.rebind()
            self.ex.observe(sit)
            ended = self.ex.ended
        ctx = self.context(sit)
        cands = A.generate(sit, ctx, sv.world)
        self._want(cands, now)
        scores = S.score_all(cands, sit, ctx, self.models, self.weights)
        chosen, info = self.selector.decide(cands, scores, now, self.interrupts(sit), ended=ended is not None)
        info["end"] = ended
        step, pool = None, cands
        for _ in range(2):
            if chosen is None:
                break
            step = self._run(chosen, sit)
            if step is not None:
                break
            pool = [c for c in pool if c.key != chosen.key]
            first = chosen.key
            chosen, again = self.selector.decide(pool, scores, now, (), ended=True, floor=S.FALLBACK_FLOOR)
            info.update(again, select="fallback", end=ended, interrupts=info["interrupts"], passed=first)
            self.selector.drop()   # a fallback is never committed: the next tick chooses afresh
        return self._decision(inputs, chosen, step, cands, scores, info)

    def _run(self, c, sit):
        """The tick's Step of the held act `c`, its executor made anew when the act changed or ended."""
        ex = self.ex
        if ex is None or ex.key != c.key or ex.ended is not None:
            if ex is not None:
                ex.retire()
            ex = self.ex = X.EXECUTORS[c.kind](self, c)
        return ex.step(sit, c)

    def _decision(self, inputs, c, step, cands, scores, info):
        sv = self.sv
        branch = step.branch if step is not None else None
        branches = {} if step is None or branch is None else {branch: step.why}
        threat = dict(branches.get("threat") or {})
        if self.kill_now is not None:
            threat["kill"] = self.kill_now
        if sv.door_held_now is not None:
            threat["door_held"] = sv.door_held_now
        if threat:
            branches["threat"] = threat
        inputs["need"] = sv.need_mark
        inputs["consume_refused"] = sv.consume_refused
        inputs["cooled"] = None
        inputs["branches"] = branches
        label = None if c is None else LABELS.get(c.kind, c.kind)
        if c is not None and c.kind == "retreat":
            label = "retreat:%s" % c.filter.kind
        tgt = None
        if c is not None and c.kind in ("fight", "stand", "retreat", "travel", "loot", "sneak"):
            tgt = c.target
        inputs["intent"] = None if c is None else {"kind": label, "target": tgt}
        inputs["utility"] = {
            "act": None if c is None else c.key, "kind": None if c is None else c.kind,
            "target": None if c is None else c.target,
            "scores": {k: [_r(v[0]), {t: _r(x) for t, x in v[1].items() if x != 0.0}] for k, v in scores.items()},
            "vetoes": {x.key: x.veto for x in cands if x.veto is not None},
            "runner_up": info["runner_up"], "margin": _r(info["margin"]), "held_by": info["held_by"],
            "select": info["select"], "interrupts": info["interrupts"], "end": info["end"]}
        if info.get("passed") is not None:
            inputs["utility"]["passed"] = info["passed"]   # the act chosen whose executor ended on its first step
        if c is not None and c.ride:
            inputs["utility"]["ride"] = True
        if c is not None and c.note is not None:
            inputs["utility"]["note"] = c.note
        if step is None:
            return Decision(None, None, None, inputs)
        return Decision(branch, step.owner, step.cmd, inputs)
