"""testing/agent/drivers/e_grade_27.py (Plan 36 Task 5c), offline: the chain sessions' regrade script under grade_x6,
read statically (CLAUDE.md section 5: a driver refuses any argument it does not define, tested statically; it names its
own file) and run on the committed E23 artifact (`e_day_23-20261105-095110`, the chain session test_e_grade_26 regrades
through e_grade_26): its grade_x5 lines are e_grade_26's, the engagement lines after them, each engagement reading of a
Plan 36 key unread (E23 ran before PZA/1.14)."""
import functools
import json
import os
import subprocess
import sys

import pytest

from agent.base.grades import x5 as GX5
from agent.base.grades import x6 as G
from agent.drivers import e_grade_23 as EG23
from agent.drivers import e_grade_27 as EG27

HERE = os.path.dirname(os.path.abspath(__file__))
TESTING = os.path.dirname(os.path.dirname(HERE))
E23 = os.path.join(TESTING, "artifacts", "e_day_23-20261105-095110")


def test_e_grade_27_names_itself_and_refuses_an_argument_it_does_not_define():
    """Its main answers usage, exit 2, on no path or more than two outside `--chain`; it names itself, imports grade_x6,
    gate_x6 and report_lines_x6 and reads kind e."""
    e = open(EG27.__file__, encoding="utf-8").read()
    assert "if not paths or (not chain and len(paths) > 2):" in e and "return 2" in e and "usage: e_grade_27.py" in e
    assert "from agent.base.grades.x6 import gate_x6, grade_x6, report_lines_x6" in e and EG27.KIND == "e"
    assert e.startswith('"""e_grade_27 --') and "e_grade_26" not in e and "x5" not in e
    assert "python testing/agent/drivers/e_grade_27.py --chain <a1.json> <a2.json> [...]" in e
    assert (EG27.grade_x6, EG27.gate_x6, EG27.report_lines_x6) == (G.grade_x6, G.gate_x6, G.report_lines_x6)


@functools.lru_cache(maxsize=None)
def _e23():
    p = os.path.join(E23, "e_day_23.json")
    if not os.path.isfile(p):
        pytest.skip("%s is not checked out" % E23)
    out, log = EG23.load(p), EG23.load_log(p)
    return p, G.grade_x6(out, log, state_dir=E23, kind="e"), GX5.grade_x5(out, log, state_dir=E23, kind="e")


def test_e_grade_27_prints_grade_x5_s_lines_then_the_engagement_ones_and_the_json():
    p, g, base = _e23()
    r = subprocess.run([sys.executable, EG27.__file__, p], capture_output=True, cwd=TESTING)
    assert r.returncode == 0, r.stderr
    text = r.stdout.replace(b"\r\n", b"\n").decode("utf-8")
    i = text.index("\n{\n")
    printed = text[:i + 1].splitlines()
    assert [("gate_x5 " + ln[len("gate_x6 "):]) if ln.startswith("gate_x6 ") else ln
            for ln in printed[:-G.N_LINES]] == base["report_lines"]
    assert printed[-G.N_LINES:] == g["report_lines"][-G.N_LINES:]
    got = json.loads(text[i:])
    assert (got["grade"], got["base"], got["base_x5"], got["base_x1"]) == ("grade_x6", "grade_x5", "grade_x4",
                                                                          "grade_e21")


def test_on_e23_every_plan_36_reading_is_unread():
    """E23 carries none of PZA/1.14's ring, PZA/1.15's leaves, the pull or the clock; it carries no bodyAngle (PZA/1.10)
    and no work leaf either; its two rips were sent standing and done."""
    _, g, _ = _e23()
    for k in ("cadence", "steps", "engage_pull", "cone_bites", "clock", "room"):
        assert g[k] == {"read": False}, k
    assert (g["crawler"]["frames"], g["crawler"]["buffer"]) == (0, 0)
    assert g["rip_ride"]["riding"]["sent"] == 0 and g["rip_ride"]["standing"]["sent"] == 2
