"""base/gates_f.py grade_f6 (Plan 25 Task 1), offline: the kills read off the act lines and the zombie_dead events on the two
committed LLM artifacts (F3 = f_goals_4: 5, where grade_f5 read 0; F2: 2), grade_f5 reproducing F3's committed report
byte for byte, every other key of grade_f6 grade_f5's, and f_grade_6.py. Module-level `F` so a mutation pass can run the
tests against a mutated copy of gates_f."""
import json
import os
import subprocess
import sys

import pytest

from agent.base import gates_e as E
from agent.base import gates_f as F
from agent.drivers import f_grade_6 as FG6

HERE = os.path.dirname(os.path.abspath(__file__))
TESTING = os.path.dirname(os.path.dirname(HERE))
F3 = os.path.join(TESTING, "artifacts", "f_goals_4-20261030-114742")
F2 = os.path.join(TESTING, "artifacts", "f_goals_2-20261029-041705")


def _grade(d, name, fn=None):
    p = os.path.join(d, name + ".json")
    if not os.path.isfile(p):
        pytest.skip("%s is not checked out" % d)
    with open(p, encoding="utf-8") as fh:
        out = json.load(fh)
    fn = fn or F.grade_f6
    return fn(out, None, FG6.load_log(p), state_dir=d, goal_lines=FG6.load_goals(p))


def test_grade_f6_on_f3_reads_five_kills_off_the_act_lines_where_grade_f5_read_none():
    g = _grade(F3, "f_goals_4")
    k = g["kills"]
    assert g["grade"] == "grade_f6" and k["planner"] == 5 and k["planner_ids"] == [17072, 17060, 17071, 17073, 17098]
    assert k["events"] == 5 and k["source"] == "act lines"
    assert g["report_lines"][0].startswith("kills 5 (")
    assert g["report_lines"][1].startswith("kills sources: planner 5 (act lines), zombie_dead events 5")
    assert _grade(F3, "f_goals_4", F.grade_f5)["kills"]["planner"] == 0


def test_grade_f6_on_f2_reads_two_kills():
    g = _grade(F2, "f_goals_2")
    assert g["kills"]["planner"] == 2 and g["kills"]["events"] == 2


def test_grade_f6_changes_only_the_grade_name_the_kills_and_the_report():
    g5, g6 = _grade(F3, "f_goals_4", F.grade_f5), _grade(F3, "f_goals_4")
    skip = ("grade", "kills", "report_lines")
    assert {k: v for k, v in g5.items() if k not in skip} == {k: v for k, v in g6.items() if k not in skip}


def test_grade_f5_still_reproduces_f3s_committed_report_byte_for_byte():
    script = os.path.join(TESTING, "agent", "drivers", "f_grade_5.py")
    p = os.path.join(F3, "f_goals_4.json")
    if not os.path.isfile(p):
        pytest.skip("the F3 artifact is not checked out")
    r = subprocess.run([sys.executable, script, p], capture_output=True)
    with open(os.path.join(F3, "f_grade.txt"), "rb") as fh:
        assert r.returncode == 0 and r.stdout == fh.read()


def test_f_grade_6_prints_the_kills_sources_line_and_the_json_and_refuses_a_bad_call(tmp_path):
    script = os.path.join(TESTING, "agent", "drivers", "f_grade_6.py")
    p = os.path.join(F3, "f_goals_4.json")
    if not os.path.isfile(p):
        pytest.skip("the F3 artifact is not checked out")
    r = subprocess.run([sys.executable, script, p], capture_output=True, text=True, encoding="utf-8")
    assert r.returncode == 0 and "kills sources: planner 5 (act lines)" in r.stdout
    assert json.loads(r.stdout[r.stdout.index("\n{\n"):])["grade"] == "grade_f6"
    for args in ([], ["a", "b"], [str(tmp_path / "nope.json")]):
        assert subprocess.run([sys.executable, script] + args, capture_output=True, text=True).returncode == 2


def test_gate_f6_is_gate_f5():
    assert F.gate_f6([]) == F.gate_f5([])
