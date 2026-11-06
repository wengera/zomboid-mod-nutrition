"""The tactician over two committed rings (Plan 31 Task 11, T; the common amendments' item 6): F15
(`f_goals_16-20261105-164332`) and E23 (`e_day_23-20261105-095110`), their frames decoded as live
(`replay_decisions.read_record`: `FileTransport`, `pza1.decode` and `merge_delta`).

The replay is open loop (`replay_decisions.py`'s docstring): it checks decisions at recorded situations, never
outcomes. Two readings:
1. The doctrine (`fallback.doctrine`, what the table answers in its empty cells and what the trials run) at every
   other frame's tactical view: one standing zombie within DANGER_R while armed (no dressing due) → `fight` it; a
   bleeding part with no standing zombie within KEEP_R and something to dress or tear → `dress`; three or more standing
   within DANGER_R → a `kite` or `avoid` toward a listed refuge (`stance` only with none listed); the nearest standing
   zombie behind a door (`line` door) → a play, never a wait (no play would be a wait).
2. The whole decider (`Survive(control="tactician")`) at 2 Hz over the same frames, its commands sent through a stub
   transport and ended `done` after DONE_S (the record's own act lines are not replayed: they name the record's aids):
   no tick raises, every send passes the schema, and at the situations of (1) the line's play is the doctrine's
   (`fight`, `dress`, a retreat label) or the guard's `fight`; a door situation's tick sends or holds a running action.
"""
import json
import os

import pytest

from agent.base.actions import Actions
from agent.base.planner.policies import DANGER_R, KEEP_R
from agent.base.planner.survive import Survive
from agent.base.planner.tactician import fallback as F
from agent.base.planner.tactician import rubric as R
from agent.base.planner.tactician import tview as V
from agent.base.planner.tactician.trigger import Triggers
from agent.base.replay_decisions import ARTIFACTS, read_record
from agent.base.world import World

RINGS = ("f_goals_16-20261105-164332", "e_day_23-20261105-095110")
EVERY = 2          # every other frame (5 Hz of the Lua's 10)
TICK = 5           # the decider's every fifth frame (2 Hz, PLANNER_HZ)
DONE_S = 1.0       # wall seconds after which the stub ends an open action `done`


def situation(view):
    """The doctrine situation a view carries (the module docstring's (1)), else None."""
    s6 = F._standing(view, DANGER_R)
    if R.dress_due(view):
        return "bleed"
    if len(s6) == 1 and F.armed(view):
        return "lone"
    if len(s6) >= 3:
        return "group"
    near = F._standing(view, 12.0)
    if near and near[0].get("line") == "door":
        return "door"
    return None


def expect(sit, ans, view):
    """The doctrine's answer `ans` holds at situation `sit`."""
    if sit == "lone":
        return ans["play"] == "fight"
    if sit == "bleed":
        return ans["play"] == "dress"
    if sit == "group":
        if ans["play"] not in ("kite", "avoid", "fight"):
            return False
        if ans["play"] == "fight":   # a zombie in reach is struck first; with no refuge, the stand (fix 1)
            return bool(F._standing(view, KEEP_R)) or F.refuge(view) is None
        t = ans.get("toward")
        return t != "stance" or F.refuge(view) is None
    if sit == "door":
        return ans is not None
    return True


@pytest.fixture(scope="module", params=RINGS)
def ring(request):
    return request.param, read_record(os.path.join(ARTIFACTS, request.param))


def test_the_doctrine_holds_at_every_situation_the_ring_carries(ring):
    name, (lines, _) = ring
    w, trig = World(), Triggers()
    seen, bad, fi = {}, [], 0
    for ln in lines:
        w.apply(ln)
        if ln["kind"] != "frame":
            continue
        fi += 1
        trig.step(w, ln["wallMs"] / 1000.0)
        if fi % EVERY:
            continue
        view = V.build(w, trig)
        sit = situation(view)
        if sit is None:
            continue
        rule, ans = F.doctrine(view)
        seen[sit] = seen.get(sit, 0) + 1
        if not expect(sit, ans, view) or R.violations(view, ans):
            bad.append((fi, sit, rule, ans))
    assert not bad, bad[:5]
    assert seen.get("lone", 0) > 0 and seen.get("bleed", 0) > 0, seen   # both rings carry a lone chaser and a bleed


class StubTransport:
    """The commands sent, in order; no file."""

    def __init__(self):
        self.cmd_seq, self.sent = 0, []

    def send(self, cmd):
        self.cmd_seq = cmd["seq"]
        self.sent.append(cmd)


def test_the_decider_runs_open_loop_over_the_ring_and_keeps_the_doctrine(ring, tmp_path):
    name, (lines, _) = ring
    clock = {"t": 0.0}
    w, tr = World(), StubTransport()
    acts = Actions(tr, clock=lambda: clock["t"])
    sv = Survive(w, acts, str(tmp_path / "decision.log"), lambda: clock["t"], control="tactician")
    fi, ticks, held, by = 0, 0, [], {}
    for ln in lines:
        if ln["kind"] == "act":
            continue   # the record's own aids: never this replay's
        w.apply(ln)
        if ln["kind"] != "frame":
            continue
        fi += 1
        clock["t"] = ln["wallMs"] / 1000.0
        if fi % TICK:
            continue
        for a in acts.history + acts.postures:
            if a.state not in ("done", "failed", "rejected", "timeout") and clock["t"] - a.sent_wall >= DONE_S:
                a.state, a.ended_wall, a.result = "done", clock["t"], {}
        sv.tick(w, acts)
        ticks += 1
    rows = [json.loads(x) for x in (tmp_path / "decision.log").read_text(encoding="utf-8").splitlines()]
    assert len(rows) == ticks > 100
    plays = {}
    for r in rows:
        k = r["inputs"]["play"]["kind"]
        plays[k] = plays.get(k, 0) + 1
    assert plays.get("fight", 0) > 0, plays
    # the decider's lines at the doctrine's situations: re-read off the line's own tactical record
    bad = []
    for r in rows:
        tac = r["inputs"]["tactician"]
        if tac["source"] == "doctrine" and tac["rule"] == "fight" and r["inputs"]["play"]["type"] != "fight":
            bad.append(r)
        if tac["play"] in ("kite", "avoid") and r["branch"] != "threat":
            bad.append(r)
    assert not bad, bad[:3]
    assert all(c["type"] != "steer" or c["args"].get("gait") != "sprint" for c in tr.sent)   # never a sprint
    starts = [json.loads(x) for x in (tmp_path / "plays.log").read_text(encoding="utf-8").splitlines()]
    starts = [x for x in starts if x["kind"] == "play"]
    flips = flips_within(starts, FLIP_S)
    print("%s: %d plays, %d A-B-A flips within %s s" % (name, len(starts), flips, FLIP_S))
    assert flips < FLIPS_BEFORE[name] and flips < REVIEW_FLIPS.get(name, FLIPS_BEFORE[name]), flips   # fix 1, M2


FLIP_S = 10.0      # wall seconds an A -> B -> A flip spans at most to count (review-t11 M2)
FLIPS_BEFORE = {"f_goals_16-20261105-164332": 29, "e_day_23-20261105-095110": 19}   # `flips_within` over this
                   # replay at bfeea009, before the hysteresis (a `git archive` of it, read by fix 1)
REVIEW_FLIPS = {"e_day_23-20261105-095110": 14}   # the review's own E23 count (review-t11 section 6), to fall from


def flips_within(starts, span):
    """The A -> B -> A play-type flips among the play starts whose first and third lie within `span` wall seconds."""
    return sum(1 for a, b, c in zip(starts, starts[1:], starts[2:]) if a["play"]["play"] == c["play"]["play"]
               != b["play"]["play"] and c["wall"] - a["wall"] <= span)
