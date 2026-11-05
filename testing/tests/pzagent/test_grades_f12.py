"""base/grades/f12.py (Plan 30 Task 4), offline: `grade_f12` is `grade_f11` under "grade_f12" with `grades.e21`'s reads
(the hits as the union, the kills matched to the press, iteration 24's rule readings and the standing minutes: each new
key equal to `grade_e21`'s on the same fabricated log), every `grade_f11` key unchanged on the fabricated logs and on
F3 (`f_goals_4-20261030-114742`), the unread cases, the report lines, the module's imports (ruling P26-Q), and the
real checks on F14 (`f_goals_15-20261105-092752`): the union 8 over the kills 7 with the events agreeing (32434
matched to the ladder's floor attack a59), iteration 24's readings unread (the session predates the rules), and every
inherited key equal to the committed `f_grade.txt`'s, through the function and through `f_grade_12.py`."""
import functools
import json
import os
import subprocess
import sys

import pytest

from agent.base import gates_e as E
from agent.base.grades import e21 as G21
from agent.base.grades import f11 as G11
from agent.base.grades import f12 as G
from agent.drivers import f_grade_12 as FG12
from . import test_grades_e14 as T14
from . import test_grades_e20 as T20
from . import test_grades_e21 as T21
from .test_gates_e import art

HERE = os.path.dirname(os.path.abspath(__file__))
TESTING = os.path.dirname(os.path.dirname(HERE))
F3 = os.path.join(TESTING, "artifacts", "f_goals_4-20261030-114742")
F14 = os.path.join(TESTING, "artifacts", "f_goals_15-20261105-092752")
NEW21 = G21.NEW


def to_f11(g):
    """grade_f12's dict as grade_f11's: the new keys dropped, the name, the new report lines dropped."""
    g = dict(g)
    for k in NEW21:
        g.pop(k)
    g["grade"] = "grade_f11"
    g["report_lines"] = g["report_lines"][:-G.N_LINES]
    return g


def _fixture(which):
    if which == "cut2":
        return T14.artifact(T20.cut2_actions(), []), T20.cut2_log(), T20.cut2_lines()
    if which == "goal":
        return T14.artifact(), T21.goal_log(), T21.goal_frames()
    if which == "kills":
        return T14.artifact(T21.kills_actions(), []), T20.rules_log(), T21.kills_lines()
    if which == "close":
        return T14.artifact(), T21.close_log(), T21.close_lines()
    return T14.artifact(T20.cut2_actions(), []), None, T20.cut2_lines()


@pytest.mark.parametrize("which", ("cut2", "goal", "kills", "close", "cut2-nolog"))
def test_the_pass_21_keys_are_grade_e21_s_readings_on_the_same_log(which):
    a, dl, lines = _fixture(which)
    e21 = G21.grade_e21(a, decision_lines=dl, lines=lines)
    f12 = G.grade_f12(a, decision_lines=dl, lines=lines)
    assert f12["grade"] == "grade_f12" and {k: f12[k] for k in NEW21} == {k: e21[k] for k in NEW21}
    assert to_f11(f12) == G11.grade_f11(a, decision_lines=dl, lines=lines)


def test_grade_f12_without_a_decision_log_reads_the_new_keys_unread_and_its_report_lines_are_f11_s_then_e21_s():
    g = G.grade_f12(art())
    assert g["grade"] == "grade_f12" and all(g[k] == {"read": False} for k in NEW21 if k != "kills_matched")
    assert G.NEW == G11.NEW + NEW21 and G.N_LINES == G21.N_LINES
    assert g["report_lines"] == G11.report_lines_f11(g) + G21.lines_e21(g)
    assert "(iteration 24, P30-B)" in g["report_lines"][-6] and "no line read" in g["report_lines"][-6]
    assert G.gate_f12([]) == G11.gate_f11([])


def test_the_module_imports_no_live_planner_or_world_name():
    names = T20._imports(G.__file__)
    assert names and not any(m.startswith(("agent.base.planner", "agent.base.world")) for m in names), names
    assert not any(getattr(v, "__module__", "").startswith(("agent.base.planner", "agent.base.world"))
                   for v in vars(G).values())


# ================================================================ the committed artifacts
def _grade(d, name, fn):
    p = os.path.join(d, name + ".json")
    if not os.path.isfile(p):
        pytest.skip("%s is not checked out" % d)
    with open(p, encoding="utf-8") as fh:
        out = json.load(fh)
    return fn(out, None, FG12.load_log(p), state_dir=d, goal_lines=FG12.load_goals(p))


@functools.lru_cache(maxsize=None)
def _f14():
    return _grade(F14, "f_goals_15", G.grade_f12)


def _committed(path, name):
    text = open(os.path.join(path, name), encoding="utf-8").read()
    i = text.index("\n{\n")
    return text[:i + 1].splitlines(), json.loads(text[i:])


def test_grade_f12_on_f3_reads_every_grade_f11_key_unchanged():
    g11, g12 = _grade(F3, "f_goals_4", G11.grade_f11), _grade(F3, "f_goals_4", G.grade_f12)
    assert g12["grade"] == "grade_f12" and to_f11(g12) == g11


def test_grade_f12_on_f14_reads_the_union_8_over_the_7_kills_matched_and_the_rules_unread():
    """F14's guide section 1: the eight attacks that landed (five reaction runs, three `hit` steps with none) and the
    seven `zombie_dead` events, 32434's matched to a59 four frames after its swing event (seq 3920)."""
    g = _f14()
    u, k = g["hits_union"], g["kills_matched"]
    assert (u["union"], u["kills"], u["per_kill_union"]) == (8, 7, 8 / 7)
    assert (k["planner"], k["agree"], [(m["id"], m["aid"]) for m in k["matched"]]) == (7, True, [(32434, "a59")])
    assert T21.unread_rules(g) and g["standing"]["stretches"] == 8
    assert g["kills"]["planner"] == 6 and g["hits"]["runs"] == 5    # grade_f11's, unchanged


def test_grade_f12_on_f14_keeps_every_grade_f11_key_as_the_committed_f_grade_txt():
    g = _f14()
    lines, committed = _committed(F14, "f_grade.txt")
    mine = to_f11(json.loads(json.dumps(FG12.finite(g), sort_keys=True, allow_nan=False)))
    assert mine == committed and g["report_lines"][:-G.N_LINES] == lines


def test_f_grade_12_on_f14_prints_the_committed_f_grade_txt_s_lines_then_the_new_ones():
    """`f_grade_12.py` on the committed F14 artifact: the committed `f_grade.txt`'s report lines, then the new lines,
    then the JSON whose grade_f11 keys equal the committed (CRLF folded)."""
    p = os.path.join(F14, "f_goals_15.json")
    if not os.path.isfile(p):
        pytest.skip("%s is not checked out" % F14)
    script = os.path.join(TESTING, "agent", "drivers", "f_grade_12.py")
    r = subprocess.run([sys.executable, script, p], capture_output=True, cwd=TESTING)
    assert r.returncode == 0
    text = r.stdout.decode("utf-8").replace("\r\n", "\n")
    i = text.index("\n{\n")
    printed, got = text[:i + 1].splitlines(), json.loads(text[i:])
    want_lines, want = _committed(F14, "f_grade.txt")
    assert printed[:-G.N_LINES] == want_lines and len(printed) == len(want_lines) + G.N_LINES
    assert got["grade"] == "grade_f12" and printed[-G.N_LINES:] == got["report_lines"][-G.N_LINES:]
    assert to_f11(got) == want and got["kills_matched"]["planner"] == 7


def test_f_grade_12_refuses_an_argument_it_does_not_define():
    """Read statically (CLAUDE.md section 5): its main answers usage, exit 2, on any call but one path."""
    src = open(FG12.__file__, encoding="utf-8").read()
    assert "if len(argv) != 1:" in src and "return 2" in src
    assert "from agent.base.grades.f12 import grade_f12" in src and "usage: f_grade_12.py" in src
    body = src[src.index('"""', 3):]
    assert "grade_f11" not in body and "f_grade_11 import load_goals" in body


def test_the_readings_on_f14_are_e21_s_over_the_same_sources():
    """grade_f12's new keys on F14 equal `e21.readings_e21` over the same artifact, decision log and state lines (the
    readings test_grades_e21 pins)."""
    g = _f14()
    r = T21._f14_readings()
    assert {k: json.dumps(g[k], sort_keys=True) for k in NEW21} == {k: json.dumps(r[k], sort_keys=True) for k in NEW21}
    assert E._d(g["goal_wait"]["near_runs"])["lines"] == 181


F15 = os.path.join(TESTING, "artifacts", "f_goals_16-20261105-164332")


def test_f_grade_12_on_f15_reproduces_the_committed_f_grade_txt_byte_for_byte():
    """Ruling P26-Q: `f_grade_12.py` on the committed F15 artifact (the first session graded through `grade_f12`, the first
    with the union hits, the event-matched kills and iteration 24's readings) reproduces its committed `f_grade.txt` byte
    for byte (CRLF folded), so a drift in any live name read through the grade chain fails here."""
    p = os.path.join(F15, "f_goals_16.json")
    if not os.path.isfile(p):
        pytest.skip("%s is not checked out" % F15)
    script = os.path.join(TESTING, "agent", "drivers", "f_grade_12.py")
    r = subprocess.run([sys.executable, script, p], capture_output=True, cwd=TESTING)
    assert r.returncode == 0
    want = open(os.path.join(F15, "f_grade.txt"), "rb").read().replace(b"\r\n", b"\n")
    assert r.stdout.replace(b"\r\n", b"\n") == want
