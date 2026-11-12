"""testing/agent/drivers/f_grade_18.py (Plan 36 Task 5c), offline: the LLM session's regrade script under grade_x6,
read statically (CLAUDE.md section 5: a driver refuses any argument it does not define, tested statically and never by
invoking it with a bad argument; it names its own file) and run on the committed F21 artifact (its output's grade_x5
part byte for byte is test_grades_x6's; here the grade it prints is grade_x6's own dict)."""
import json
import os
import subprocess
import sys

import pytest

from agent.base.grades import x6 as G
from agent.drivers import f_grade_18 as FG18

HERE = os.path.dirname(os.path.abspath(__file__))
TESTING = os.path.dirname(os.path.dirname(HERE))
F21 = os.path.join(TESTING, "artifacts", "f_goals_21-20261111-150552")


def test_f_grade_18_names_itself_and_refuses_an_argument_it_does_not_define():
    """Its main answers usage, exit 2, on anything but one path; it names itself, imports grade_x6 and reads kind f."""
    f = open(FG18.__file__, encoding="utf-8").read()
    assert "if len(argv) != 1:" in f and "usage: f_grade_18.py" in f and "return 2" in f and FG18.KIND == "f"
    assert f.startswith('"""f_grade_18 --') and "f_grade_17" not in f and "grade_x5" not in f
    assert "python testing/agent/drivers/f_grade_18.py <artifact.json>" in f
    assert "from agent.base.grades.x6 import grade_x6" in f and FG18.grade_x6 is G.grade_x6


def test_f_grade_18_on_f21_prints_grade_x6_s_report_lines_and_its_json():
    p = os.path.join(F21, "f_goals_21.json")
    if not os.path.isfile(p):
        pytest.skip("%s is not checked out" % F21)
    r = subprocess.run([sys.executable, FG18.__file__, p], capture_output=True, cwd=TESTING)
    assert r.returncode == 0, r.stderr
    text = r.stdout.replace(b"\r\n", b"\n").decode("utf-8")
    i = text.index("\n{\n")
    got = json.loads(text[i:])
    assert (got["grade"], got["base"], got["base_x5"], got["base_x1"]) == ("grade_x6", "grade_x5", "grade_x4",
                                                                          "grade_f12")
    assert text[:i + 1].splitlines() == got["report_lines"]
