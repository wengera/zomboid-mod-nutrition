"""base/grades/f10.py (Plan 28 Task 7c), offline: `grade_f10` is `grade_f9` under "grade_f10" with the four readings of
survival iteration 22 read by `grades.e19`'s readers: each new key equal to `grade_e19`'s on the same fabricated log,
every `grade_f9` key unchanged on F3 (`f_goals_4-20261030-114742`), the unread case, the report lines, the module's
imports (ruling P26-Q), and the real checks on F12 (`f_goals_13-20261104-203950`, no melee sent: the new keys read
zero there, its nine hits all outside a span over its four kills): every `grade_f9` key equal to the committed
`f_grade.txt`'s, through the function and through `f_grade_10.py`."""
import ast
import json
import os
import subprocess
import sys

import pytest

from agent.base import gates_e as E
from agent.base.grades import e19 as G19
from agent.base.grades import f9 as G9
from agent.base.grades import f10 as G
from agent.drivers import f_grade_10 as FG10
from . import test_grades_e14 as T14
from . import test_grades_e19 as T19
from .test_gates_e import art

HERE = os.path.dirname(os.path.abspath(__file__))
TESTING = os.path.dirname(os.path.dirname(HERE))
F3 = os.path.join(TESTING, "artifacts", "f_goals_4-20261030-114742")
F12 = os.path.join(TESTING, "artifacts", "f_goals_13-20261104-203950")
NEW = G.NEW
NEW9, NEW19 = G9.NEW, G19.NEW


def _fixture_artifact(log=True):
    a = T14.artifact(T19.melee_actions(), [])
    a["loop"]["fights"] = list(T19.FIGHTS)
    return a, (T19.melee_log() if log else None), T19.melee_lines()


@pytest.mark.parametrize("log", (True, False))
def test_the_pass_19_keys_are_grade_e19_s_readings_on_the_same_log(log):
    a, dl, lines = _fixture_artifact(log)
    e19 = G19.grade_e19(a, decision_lines=dl, lines=lines)
    f10 = G.grade_f10(a, decision_lines=dl, lines=lines)
    assert f10["grade"] == "grade_f10" and {k: f10[k] for k in NEW19} == {k: e19[k] for k in NEW19}
    assert f10["melee"] == (T19.MELEE if log else {"read": False}) and f10["melee_cost"] == T19.COST
    f9 = G9.grade_f9(a, decision_lines=dl, lines=lines)
    skip = ("grade", "report_lines") + NEW19
    assert {k: v for k, v in f9.items() if k not in skip} == {k: v for k, v in f10.items() if k not in skip}


def test_grade_f10_without_a_decision_log_reads_the_new_keys_unread_and_its_report_lines_are_f9_s_then_e19_s():
    g = G.grade_f10(art())
    assert g["grade"] == "grade_f10" and all(g[k] == {"read": False} for k in NEW) and len(NEW) == 22
    assert NEW == NEW9 + NEW19
    assert g["report_lines"] == G9.report_lines_f9(g) + G19.lines_e19(g)
    assert all("no decision log read" in line or "no frames read" in line for line in g["report_lines"][-len(NEW):])
    assert G.gate_f10([]) == G9.gate_f9([])


def test_the_module_imports_no_live_planner_or_world_name():
    tree = ast.parse(open(G.__file__, encoding="utf-8").read())
    mods = [n.module or "" for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)]
    mods += [a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names]
    assert mods and not any(m.startswith(("agent.base.planner", "agent.base.world")) for m in mods), mods
    assert not any(getattr(v, "__module__", "").startswith(("agent.base.planner", "agent.base.world"))
                   for v in vars(G).values())


# ================================================================ the committed artifacts
def _grade(d, name, fn):
    p = os.path.join(d, name + ".json")
    if not os.path.isfile(p):
        pytest.skip("%s is not checked out" % d)
    with open(p, encoding="utf-8") as fh:
        out = json.load(fh)
    return fn(out, None, FG10.load_log(p), state_dir=d, goal_lines=FG10.load_goals(p))


def _committed(path, name):
    text = open(os.path.join(path, name), encoding="utf-8").read()
    i = text.index("\n{\n")
    return text[:i + 1].splitlines(), json.loads(text[i:])


def _to_f9(g):
    g = dict(g)
    for k in NEW19:
        g.pop(k)
    g["grade"] = "grade_f9"
    g["report_lines"] = g["report_lines"][:-len(NEW19)]
    return g


def test_grade_f10_on_f3_reads_every_grade_f9_key_unchanged():
    g9, g10 = _grade(F3, "f_goals_4", G9.grade_f9), _grade(F3, "f_goals_4", G.grade_f10)
    skip = ("grade", "report_lines") + NEW19
    assert g10["grade"] == "grade_f10" and all(g10[k]["read"] is True for k in NEW19)
    assert {k: v for k, v in g9.items() if k not in skip} == {k: v for k, v in g10.items() if k not in skip}
    assert g10["report_lines"][:-len(NEW19)] == g9["report_lines"]


def test_grade_f10_on_f12_keeps_every_grade_f9_key_as_the_committed_f_grade_txt_and_reads_no_melee():
    """F12 ran survival iteration 21 on PZA/1.7.2 (no melee sent, no frame `act.step`): the melee reads zero over its
    nineteen fights; its nine reaction runs all outside a span and all nine inside a ladder fight, over its four kills
    (the inherited `kills.planner`) at 2.25 a kill; every frame outside a span."""
    g = _grade(F12, "f_goals_13", G.grade_f10)
    assert g["grade"] == "grade_f10" and all(g[k]["read"] is True for k in NEW)
    assert g["melee"] == T19._zero_melee(19)
    assert g["hits_in_melee"] == {"read": True, "runs": 9, "inside": 0, "outside": 9, "outside_fight": 9,
                                  "kills_inside": 0, "kills_outside": 4, "kills": 4, "per_kill": 2.25,
                                  "kills_events": 4, "per_kill_events": 2.25, "per_kill_inside": None,
                                  "per_kill_outside": 2.25}
    assert g["kills"]["events"] == 4
    assert g["kills"]["planner"] == 4 and g["hits"]["runs"] == 9 and g["hits"]["per_kill"] == 2.25
    assert g["melee_strike"]["runs"] == 0 and g["melee_cost"]["inside"]["frames"] == 0
    assert g["melee_cost"]["outside"]["frames"] == len(E._frame_index(E.session_lines(F12)[0])[1])
    _, committed = _committed(F12, "f_grade.txt")
    mine = json.loads(json.dumps(FG10.finite(g), sort_keys=True, allow_nan=False))
    assert _to_f9(mine) == committed


def test_f_grade_10_on_f12_prints_the_committed_f_grade_txt_s_lines_then_the_four_new_ones():
    """`f_grade_10.py` on the committed F12 artifact: the committed `f_grade.txt`'s report lines, then the four new
    lines, then the JSON whose grade_f9 keys equal the committed (CRLF folded)."""
    p = os.path.join(F12, "f_goals_13.json")
    if not os.path.isfile(p):
        pytest.skip("%s is not checked out" % F12)
    script = os.path.join(TESTING, "agent", "drivers", "f_grade_10.py")
    r = subprocess.run([sys.executable, script, p], capture_output=True, cwd=TESTING)
    assert r.returncode == 0
    text = r.stdout.decode("utf-8").replace("\r\n", "\n")
    i = text.index("\n{\n")
    printed, got = text[:i + 1].splitlines(), json.loads(text[i:])
    want_lines, want = _committed(F12, "f_grade.txt")
    assert printed[:-len(NEW19)] == want_lines and len(printed) == len(want_lines) + len(NEW19)
    assert got["grade"] == "grade_f10" and printed[-len(NEW19):] == got["report_lines"][-len(NEW19):]
    assert _to_f9(got) == want


def test_f_grade_10_refuses_an_argument_it_does_not_define():
    """Read statically (CLAUDE.md section 5): its main answers usage, exit 2, on any call but one path."""
    src = open(FG10.__file__, encoding="utf-8").read()
    assert "if len(argv) != 1:" in src and "return 2" in src
    assert "from agent.base.grades.f10 import grade_f10" in src and "usage: f_grade_10.py" in src
    body = src[src.index('"""', 3):]
    assert "grade_f9" not in body and "f_grade_9" not in body
