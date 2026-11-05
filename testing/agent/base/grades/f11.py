"""grades.f11 -- the LLM session grade, pass 11 (Plan 29 Task 3): `grade_f11` is `grades.f10.grade_f10` under
"grade_f11" with `grades.e20`'s reads (`e20.apply_e20`: the kills and the hits read whole, ruling P29-J, the frozen
reads kept under `kills.legacy_planner` and `hits.legacy`; the facing over every press `facing_all`, the melee's swings
by the arms' pain `pain_swings`, and one reading per rule of survival iteration 23) and one reading of its own off the
goals log:

  stall_views  P29-B, the view's `stall` line (the target of the last goal that stood unmoved for its budget, which
               the goal prompt tells the model never to answer): the views carrying it, the goals taken on them by
               type, and those taken at the stalled square (must read 0).

`stall_views` is {"read": False} without the goals log and on a log no view of which carries the line (a log written
before iteration 23, F13's); every other key is grade_f10's or `e20`'s, read as `e20` reads them. The inherited report
lines read the legacy kills and hits (`e20._legacy`), so they stand as grade_f10 printed them.

The view's key is copied below as a frozen constant with its source and value at d54bfc1a (ruling P26-Q); the readers'
other frozen copies live in `grades/e17.py` to `grades/e20.py`. This module imports nothing from `agent.base.planner`
or `agent.base.world`, and the chain it imports (`grades.f10.grade_f10`, which reads `llm.objects` and `view.OPEN_KEY`
live through `grade_f7`) is pinned by the regrade tests of the artifacts graded through it. Frozen once an artifact
carries its output (`grades/__init__.py`); `gates_f`, `grades/f7.py` to `grades/f10.py` and every driver stay
untouched."""
import json

from agent.base import gates_e as E
from agent.base import gates_f as F
from agent.base.grades import e20 as G20
from agent.base.grades import f10 as G10

STALL_KEY = "stall"                  # planner/view.py:139 (P29-B): the stalled target's key, rendered `stall: [x,y]`
STALL_LINE = STALL_KEY + ": "
NEW = G10.NEW + G20.NEW + ("stall_views",)
N_LINES = G20.N_LINES + 1            # the report lines appended to grade_f10's: e20's, then the stall views'


def _stall(prompt):
    """The square [x, y] the rendered view's `stall:` line names, else None (no line, or one that does not parse)."""
    for ln in str(prompt).splitlines():
        if ln.startswith(STALL_LINE):
            try:
                v = json.loads(ln[len(STALL_LINE):])
            except ValueError:
                return None
            return v if isinstance(v, list) and len(v) == 2 else None
    return None


def f_stall_views(goal_lines):
    """The view's `stall` line (P29-B): {read, n, taken, at_stall, squares} ({"read": False} without the goals log or
    on a log no view of which carries the line). Reading: `n` the rows whose prompt carries the `stall:` line, `taken`
    the goals taken on them by type (`ok` true, `gates_f._goal_of`), `at_stall` those whose (x, y) is the stalled square
    (must read 0: the prompt's line), `squares` the stalled squares named, each once."""
    if goal_lines is None:
        return {"read": False}
    n = at = 0
    taken, squares = {}, []
    for r in (x for x in E._l(goal_lines) if isinstance(x, dict)):
        sq = _stall(r.get("prompt"))
        if sq is None:
            continue
        n += 1
        if sq not in squares:
            squares.append(sq)
        g = F._goal_of(r)
        if g.get("type") is None:
            continue
        taken[str(g["type"])] = taken.get(str(g["type"]), 0) + 1
        at += 1 if [g.get("x"), g.get("y")] == sq else 0
    if not n:
        return {"read": False}
    return {"read": True, "n": n, "taken": taken, "at_stall": at, "squares": squares}


def report_lines_f11(g):
    """report_lines_f10's lines over the legacy kills and hits (`e20._legacy`), then `e20.lines_e20`'s, then the stall
    views' line, each marked reading or inference."""
    g = E._d(g)
    sv = E._d(g.get("stall_views"))
    tail = ("stall views (iteration 23, P29-B) [reading]: %s views carrying `stall:` at %s, taken by type %s, %s at "
            "the stalled square (must read 0)" % (sv.get("n"), sv.get("squares"), sv.get("taken"), sv.get("at_stall"))
            if sv.get("read") else
            "stall views (iteration 23, P29-B): no line read (no goals log, or no view carrying `stall:`)")
    return G10.report_lines_f10(G20._legacy(g)) + G20.lines_e20(g) + [tail]


def grade_f11(out, prev=None, decision_lines=None, state_dir=None, lines=None, goal_lines=None):
    """grade_f10 under "grade_f11" with `e20.apply_e20`'s reads and `stall_views`, over the state lines of `state_dir`
    unless `lines` is given, read once and handed down (`frames_files` restored, as grade_f10 does over grade_f9)."""
    files = []
    if lines is None:
        lines, files = E.session_lines(state_dir) if state_dir is not None else ([], [])
    g = G10.grade_f10(out, prev, decision_lines, state_dir, lines, goal_lines)
    g["grade"] = "grade_f11"
    if files and "frames_files" in g:
        g["frames_files"] = files                      # grade_f10 was handed the lines, so it did not see the files
    G20.apply_e20(g, out, decision_lines, lines)
    g["stall_views"] = f_stall_views(goal_lines)
    g["report_lines"] = report_lines_f11(g)
    return g


def gate_f11(outs):
    """gate_f10 (grade_f11 changes none of what it reads), named gate_f11."""
    return G10.gate_f10(outs)
