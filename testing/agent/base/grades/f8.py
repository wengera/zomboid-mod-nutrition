"""grades.f8 -- the LLM session grade, pass 8 (Plan 27 Task 2): `grade_f8` is `grades.f7.grade_f7` under "grade_f8"
with the nine readings of survival iteration 19 read by `grades.e16`'s readers (`e16.readings_e16`: `flee_finish`,
`many_tail`, `hold_fight`, `hold_rest`, `spent_kept`, `low_swing`, `wounded_swings`, `window_still`, `unwear_live`),
each {"read": False} without a decision log; every other key is grade_f7's. The LLM source's fourth round stands as
`grade_f7` reads it (Plan 27 changes no goal source).

This module reads no live planner name of its own: the readers' frozen copies live in `grades/e16.py` (ruling P26-Q);
it imports nothing from `agent.base.planner` or `agent.base.world`, and the chain it imports (`grades.f7.grade_f7`,
which reads `llm.objects` and `view.OPEN_KEY` live) is pinned by the regrade tests of the artifacts graded through it.
Frozen once an artifact carries its output (`grades/__init__.py`); `gates_f`, `grades/f7.py` and every driver stay
untouched."""
from agent.base import gates_e as E
from agent.base.grades import e16 as G16
from agent.base.grades import f7 as G7

NEW = G16.NEW


def report_lines_f8(g):
    """report_lines_f7's lines then one line per iteration 19 reading (`e16.lines_e16`), each marked reading or
    inference."""
    g = E._d(g)
    return G7.report_lines_f7(g) + G16.lines_e16(g)


def grade_f8(out, prev=None, decision_lines=None, state_dir=None, lines=None, goal_lines=None):
    """grade_f7 under "grade_f8" with the nine readings of survival iteration 19 (`e16.readings_e16` over the state
    lines of `state_dir` unless `lines` is given; each {"read": False} without a decision log)."""
    g = G7.grade_f7(out, prev, decision_lines, state_dir, lines, goal_lines)
    g["grade"] = "grade_f8"
    if lines is None:
        lines = E.session_lines(state_dir)[0] if state_dir is not None else []
    g.update(G16.readings_e16(out, decision_lines, lines))
    g["report_lines"] = report_lines_f8(g)
    return g


def gate_f8(outs):
    """gate_f7 (grade_f8 changes none of what it reads), named gate_f8."""
    return G7.gate_f7(outs)
