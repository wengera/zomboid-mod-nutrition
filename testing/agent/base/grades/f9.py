"""grades.f9 -- the LLM session grade, pass 9 (Plan 28 Task 4): `grade_f9` is `grades.f8.grade_f8` under "grade_f9"
with the nine readings of survival iteration 20 read by `grades.e17`'s readers (`e17.readings_e17`: `stuck_leave`,
`floor_finish`, `fallen_seek`, `listing`, `shove_close`, `stock_early`, `low_exit`, `spent_held`, `wounded_swing_off`)
and the nine of pass 18 read by `grades.e18`'s (`e18.readings_e18`: the hits per kill P28-M off the frames, and
`wound_dress`, `shove_back`, `drift_stand`, `floor_pain`, `busy_retry`, `circle`, `facing`, `client_end`), each
{"read": False} without a decision log (the hits without frames); every other key is grade_f8's. The LLM source stands
as `grade_f7` reads it (Plan 28 changes no goal source).

This module reads no live planner name of its own: the readers' frozen copies live in `grades/e17.py` and
`grades/e18.py` (ruling P26-Q); it imports nothing from `agent.base.planner` or `agent.base.world`, and the chain it
imports (`grades.f8.grade_f8`, which reads `llm.objects` and `view.OPEN_KEY` live through `grade_f7`) is pinned by the
regrade tests of the artifacts graded through it. Frozen once an artifact carries its output (`grades/__init__.py`);
`gates_f`, `grades/f7.py`, `grades/f8.py` and every driver stay untouched."""
from agent.base import gates_e as E
from agent.base.grades import e17 as G17
from agent.base.grades import e18 as G18
from agent.base.grades import f8 as G8

NEW = G17.NEW + G18.NEW


def report_lines_f9(g):
    """report_lines_f8's lines then one line per iteration 20 reading (`e17.lines_e17`) and per pass 18 reading
    (`e18.lines_e18`), each marked reading or inference."""
    g = E._d(g)
    return G8.report_lines_f8(g) + G17.lines_e17(g) + G18.lines_e18(g)


def grade_f9(out, prev=None, decision_lines=None, state_dir=None, lines=None, goal_lines=None):
    """grade_f8 under "grade_f9" with the nine readings of survival iteration 20 (`e17.readings_e17`) and the nine of
    pass 18 (`e18.readings_e18`, the hits over grade_f8's `kills.planner`), over the state lines of `state_dir` unless
    `lines` is given; each {"read": False} without a decision log (the hits without frames)."""
    g = G8.grade_f8(out, prev, decision_lines, state_dir, lines, goal_lines)
    g["grade"] = "grade_f9"
    if lines is None:
        lines = E.session_lines(state_dir)[0] if state_dir is not None else []
    g.update(G17.readings_e17(out, decision_lines, lines))
    g.update(G18.readings_e18(out, decision_lines, lines, E._d(g.get("kills")).get("planner")))
    g["report_lines"] = report_lines_f9(g)
    return g


def gate_f9(outs):
    """gate_f8 (grade_f9 changes none of what it reads), named gate_f9."""
    return G8.gate_f8(outs)
