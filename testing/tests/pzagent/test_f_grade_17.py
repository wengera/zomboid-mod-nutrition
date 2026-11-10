"""testing/agent/drivers/f_grade_17.py (Plan 35 Task 5), offline: the LLM session's regrade script under grade_x5,
read statically (CLAUDE.md section 5: a driver refuses any argument it does not define, tested statically and never by
invoking it with a bad argument; it names its own file) and run on the committed F20 artifact (its output's grade_x4
part byte for byte is test_grades_x5's; here the grade it prints is grade_x5's own dict)."""
import json
import os
import subprocess
import sys

import pytest

from agent.base.grades import x5 as G
from agent.drivers import f_grade_17 as FG17

HERE = os.path.dirname(os.path.abspath(__file__))
TESTING = os.path.dirname(os.path.dirname(HERE))
F20 = os.path.join(TESTING, "artifacts", "f_goals_20-20261109-155512")


def test_f_grade_17_names_itself_and_refuses_an_argument_it_does_not_define():
    """Its main answers usage, exit 2, on anything but one path; it names itself, imports grade_x5 and reads kind f."""
    f = open(FG17.__file__, encoding="utf-8").read()
    assert "if len(argv) != 1:" in f and "usage: f_grade_17.py" in f and "return 2" in f and FG17.KIND == "f"
    assert f.startswith('"""f_grade_17 --') and "f_grade_16" not in f and "grade_x4" not in f
    assert "python testing/agent/drivers/f_grade_17.py <artifact.json>" in f
    assert "from agent.base.grades.x5 import grade_x5" in f and FG17.grade_x5 is G.grade_x5


def test_f_grade_17_on_f20_prints_grade_x5_s_report_lines_and_its_json():
    p = os.path.join(F20, "f_goals_20.json")
    if not os.path.isfile(p):
        pytest.skip("%s is not checked out" % F20)
    r = subprocess.run([sys.executable, FG17.__file__, p], capture_output=True, cwd=TESTING)
    assert r.returncode == 0, r.stderr
    text = r.stdout.replace(b"\r\n", b"\n").decode("utf-8")
    i = text.index("\n{\n")
    got = json.loads(text[i:])
    assert (got["grade"], got["base"], got["base_x4"], got["base_x1"]) == ("grade_x5", "grade_x4", "grade_x3",
                                                                          "grade_f12")
    assert text[:i + 1].splitlines() == got["report_lines"]
