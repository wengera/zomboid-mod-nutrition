"""grades.f12 -- the LLM session grade, pass 12 (Plan 30 Task 4): `grade_f12` is `grades.f11.grade_f11` under
"grade_f12" with `grades.e21`'s reads (`e21.apply_e21`: the hits as the union of the frames' reaction runs and the
reflex's `hit` steps, the kills matched to the press before each `zombie_dead` event, one reading per rule of survival
iteration 24 and the standing minutes), each read as `e21` reads it; every other key is grade_f11's, and the inherited
report lines stand as grade_f11 printed them, `e21.lines_e21`'s after them.

This module copies no live name of its own (the readers' frozen copies live in `grades/e21.py`), imports nothing from
`agent.base.planner` or `agent.base.world`, and the chain it imports (`grades.f11.grade_f11`, which reads `llm.objects`
and `view.OPEN_KEY` live through `grade_f7`) is pinned by the regrade tests of the artifacts graded through it. Frozen
once an artifact carries its output (`grades/__init__.py`); `gates_f`, `grades/f7.py` to `grades/f11.py` and every
driver stay untouched."""
from agent.base import gates_e as E
from agent.base.grades import e21 as G21
from agent.base.grades import f11 as G11

NEW = G11.NEW + G21.NEW
N_LINES = G21.N_LINES                # the report lines appended to grade_f11's: e21's


def report_lines_f12(g):
    """report_lines_f11's lines, then `e21.lines_e21`'s, each marked reading or inference."""
    g = E._d(g)
    return G11.report_lines_f11(g) + G21.lines_e21(g)


def grade_f12(out, prev=None, decision_lines=None, state_dir=None, lines=None, goal_lines=None):
    """grade_f11 under "grade_f12" with `e21.apply_e21`'s reads, over the state lines of `state_dir` unless `lines` is
    given, read once and handed down (`frames_files` restored, as grade_f11 does over grade_f10)."""
    files = []
    if lines is None:
        lines, files = E.session_lines(state_dir) if state_dir is not None else ([], [])
    g = G11.grade_f11(out, prev, decision_lines, state_dir, lines, goal_lines)
    g["grade"] = "grade_f12"
    if files and "frames_files" in g:
        g["frames_files"] = files                      # grade_f11 was handed the lines, so it did not see the files
    G21.apply_e21(g, out, decision_lines, lines)
    g["report_lines"] = report_lines_f12(g)
    return g


def gate_f12(outs):
    """gate_f11 (grade_f12 changes none of what it reads), named gate_f12."""
    return G11.gate_f11(outs)
