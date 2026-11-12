"""testing/agent/drivers/f_grade_19.py (Plan 37 Task 4), offline: the LLM session's regrade script under grade_x7,
read statically (CLAUDE.md section 5: a driver refuses any argument it does not define, tested statically and never by
invoking it with a bad argument; it names its own file) and run on the committed F22 artifact (its output's grade_x6
part line for line is test_grades_x7's; here the grade it prints is grade_x7's own dict)."""
import json
import os
import subprocess
import sys

import pytest

from agent.base.grades import x7 as G
from agent.drivers import f_grade_19 as FG19

HERE = os.path.dirname(os.path.abspath(__file__))
TESTING = os.path.dirname(os.path.dirname(HERE))
F22 = os.path.join(TESTING, "artifacts", "f_goals_22-20261111-215108")


def test_f_grade_19_names_itself_and_refuses_an_argument_it_does_not_define():
    """Its main answers usage, exit 2, on anything but one path; it names itself, imports grade_x7 and reads kind f."""
    f = open(FG19.__file__, encoding="utf-8").read()
    assert "if len(argv) != 1:" in f and "usage: f_grade_19.py" in f and "return 2" in f and FG19.KIND == "f"
    assert f.startswith('"""f_grade_19 --') and "f_grade_18" not in f and "grade_x6" not in f
    assert "python testing/agent/drivers/f_grade_19.py <artifact.json>" in f
    assert "from agent.base.grades.x7 import grade_x7" in f and FG19.grade_x7 is G.grade_x7


def test_f_grade_19_on_f22_prints_grade_x7_s_report_lines_and_its_json():
    p = os.path.join(F22, "f_goals_22.json")
    if not os.path.isfile(p):
        pytest.skip("%s is not checked out" % F22)
    r = subprocess.run([sys.executable, FG19.__file__, p], capture_output=True, cwd=TESTING)
    assert r.returncode == 0, r.stderr
    text = r.stdout.replace(b"\r\n", b"\n").decode("utf-8")
    i = text.index("\n{\n")
    got = json.loads(text[i:])
    assert (got["grade"], got["base"], got["base_x6"], got["base_x1"]) == ("grade_x7", "grade_x6", "grade_x5",
                                                                          "grade_f12")
    assert text[:i + 1].splitlines() == got["report_lines"]
