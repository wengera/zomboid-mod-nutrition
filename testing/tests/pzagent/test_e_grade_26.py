"""testing/agent/drivers/e_grade_26.py (Plan 35 Task 5), offline: the chain sessions' regrade script under grade_x5,
read statically (CLAUDE.md section 5: a driver refuses any argument it does not define, tested statically; it names its
own file) and run on the committed E23 artifact (`e_day_23-20261105-095110`, the chain session test_grades_x4 regrades
through e_grade_25): its grade_x4 lines are e_grade_25's, the footwork lines after them, each footwork reading empty
(E23 ran before PZA/1.13)."""
import functools
import json
import os
import subprocess
import sys

import pytest

from agent.base.grades import x4 as GX4
from agent.base.grades import x5 as G
from agent.drivers import e_grade_23 as EG23
from agent.drivers import e_grade_26 as EG26

HERE = os.path.dirname(os.path.abspath(__file__))
TESTING = os.path.dirname(os.path.dirname(HERE))
E23 = os.path.join(TESTING, "artifacts", "e_day_23-20261105-095110")


def test_e_grade_26_names_itself_and_refuses_an_argument_it_does_not_define():
    """Its main answers usage, exit 2, on no path or more than two outside `--chain`; it names itself, imports grade_x5,
    gate_x5 and report_lines_x5 and reads kind e."""
    e = open(EG26.__file__, encoding="utf-8").read()
    assert "if not paths or (not chain and len(paths) > 2):" in e and "return 2" in e and "usage: e_grade_26.py" in e
    assert "from agent.base.grades.x5 import gate_x5, grade_x5, report_lines_x5" in e and EG26.KIND == "e"
    assert e.startswith('"""e_grade_26 --') and "e_grade_25" not in e and "x4" not in e
    assert "python testing/agent/drivers/e_grade_26.py --chain <a1.json> <a2.json> [...]" in e
    assert (EG26.grade_x5, EG26.gate_x5, EG26.report_lines_x5) == (G.grade_x5, G.gate_x5, G.report_lines_x5)


@functools.lru_cache(maxsize=None)
def _e23():
    p = os.path.join(E23, "e_day_23.json")
    if not os.path.isfile(p):
        pytest.skip("%s is not checked out" % E23)
    out, log = EG23.load(p), EG23.load_log(p)
    return p, G.grade_x5(out, log, state_dir=E23, kind="e"), GX4.grade_x4(out, log, state_dir=E23, kind="e")


def test_e_grade_26_prints_grade_x4_s_lines_then_the_footwork_ones_and_the_json():
    p, g, base = _e23()
    r = subprocess.run([sys.executable, EG26.__file__, p], capture_output=True, cwd=TESTING)
    assert r.returncode == 0, r.stderr
    text = r.stdout.replace(b"\r\n", b"\n").decode("utf-8")
    i = text.index("\n{\n")
    printed = text[:i + 1].splitlines()
    assert [("gate_x4 " + ln[len("gate_x5 "):]) if ln.startswith("gate_x5 ") else ln
            for ln in printed[:-G.N_LINES]] == base["report_lines"]
    assert printed[-G.N_LINES:] == g["report_lines"][-G.N_LINES:]
    got = json.loads(text[i:])
    assert (got["grade"], got["base"], got["base_x4"], got["base_x1"]) == ("grade_x5", "grade_x4", "grade_x3",
                                                                          "grade_e21")


def test_on_e23_every_footwork_reading_is_empty():
    _, g, _ = _e23()
    assert g["work"]["steps"] == {"work": 0, "cornered": 0, "pile": 0} and g["work"]["turns"] == {}
    assert (g["contact"]["engagements"], g["contact"]["seconds"], g["handbacks"]["by_why"]) == (0, 0, {})
    assert (g["engage_hold"]["lines"], g["withdraw"]["lines"]) == (0, 0)
