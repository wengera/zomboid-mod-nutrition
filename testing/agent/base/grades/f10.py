"""grades.f10 -- the LLM session grade, pass 10 (Plan 28 Task 7c): `grade_f10` is `grades.f9.grade_f9` under
"grade_f10" with the four readings of survival iteration 22 read by `grades.e19`'s readers (`e19.readings_e19`: the
melee spans `melee`, the hits inside and outside them `hits_in_melee`, the strike before each hit inside a span by step
`melee_strike` and the skill tick's cost over the spans `melee_cost`), `melee` {"read": False} without a decision log
and the other three without a frame; every other key is grade_f9's. The LLM source stands as `grade_f7` reads it
(Plan 28 changes no goal source).

This module reads no live planner name of its own: the readers' frozen copies live in `grades/e17.py`,
`grades/e18.py` and `grades/e19.py` (ruling P26-Q); it imports nothing from `agent.base.planner` or `agent.base.world`,
and the chain it imports (`grades.f9.grade_f9`, which reads `llm.objects` and `view.OPEN_KEY` live through
`grade_f7`) is pinned by the regrade tests of the artifacts graded through it. Frozen once an artifact carries its
output (`grades/__init__.py`); `gates_f`, `grades/f7.py` to `grades/f9.py` and every driver stay untouched."""
from agent.base import gates_e as E
from agent.base.grades import e19 as G19
from agent.base.grades import f9 as G9

NEW = G9.NEW + G19.NEW


def report_lines_f10(g):
    """report_lines_f9's lines then one line per pass 19 reading (`e19.lines_e19`), each marked reading or
    inference."""
    g = E._d(g)
    return G9.report_lines_f9(g) + G19.lines_e19(g)


def grade_f10(out, prev=None, decision_lines=None, state_dir=None, lines=None, goal_lines=None):
    """grade_f9 under "grade_f10" with the four readings of pass 19 (`e19.readings_e19`), over the state lines of
    `state_dir` unless `lines` is given, read once and handed down (`frames_files` restored, as `grade_e7` does over
    `grade_e6`); `melee` {"read": False} without a decision log, the other three without a frame."""
    files = []
    if lines is None:
        lines, files = E.session_lines(state_dir) if state_dir is not None else ([], [])
    g = G9.grade_f9(out, prev, decision_lines, state_dir, lines, goal_lines)
    g["grade"] = "grade_f10"
    if files and "frames_files" in g:
        g["frames_files"] = files                      # grade_f9 was handed the lines, so it did not see the files
    g.update(G19.readings_e19(out, decision_lines, lines))
    g["report_lines"] = report_lines_f10(g)
    return g


def gate_f10(outs):
    """gate_f9 (grade_f10 changes none of what it reads), named gate_f10."""
    return G9.gate_f9(outs)
