"""testing/agent/drivers/e_grade_28.py (Plan 37 Task 4), offline: the chain sessions' regrade script under grade_x7,
read statically (CLAUDE.md section 5: a driver refuses any argument it does not define, tested statically; it names its
own file) and run on the committed E23 artifact (`e_day_23-20261105-095110`, the chain session test_e_grade_27 regrades
through e_grade_27): its grade_x6 lines are grade_x6's, the disposition lines after them, each crowd reading unread
(E23 ran before PZA/1.16's keys and before the work leaf of PZA/1.13)."""
import functools
import json
import os
import subprocess
import sys

import pytest

from agent.base.grades import x6 as GX6
from agent.base.grades import x7 as G
from agent.drivers import e_grade_23 as EG23
from agent.drivers import e_grade_28 as EG28

HERE = os.path.dirname(os.path.abspath(__file__))
TESTING = os.path.dirname(os.path.dirname(HERE))
E23 = os.path.join(TESTING, "artifacts", "e_day_23-20261105-095110")


def test_e_grade_28_names_itself_and_refuses_an_argument_it_does_not_define():
    """Its main answers usage, exit 2, on no path or more than two outside `--chain`; it names itself, imports grade_x7,
    gate_x7 and report_lines_x7 and reads kind e."""
    e = open(EG28.__file__, encoding="utf-8").read()
    assert "if not paths or (not chain and len(paths) > 2):" in e and "return 2" in e and "usage: e_grade_28.py" in e
    assert "from agent.base.grades.x7 import gate_x7, grade_x7, report_lines_x7" in e and EG28.KIND == "e"
    assert e.startswith('"""e_grade_28 --') and "e_grade_27" not in e and "x6" not in e
    assert "python testing/agent/drivers/e_grade_28.py --chain <a1.json> <a2.json> [...]" in e
    assert (EG28.grade_x7, EG28.gate_x7, EG28.report_lines_x7) == (G.grade_x7, G.gate_x7, G.report_lines_x7)


@functools.lru_cache(maxsize=None)
def _e23():
    p = os.path.join(E23, "e_day_23.json")
    if not os.path.isfile(p):
        pytest.skip("%s is not checked out" % E23)
    out, log = EG23.load(p), EG23.load_log(p)
    return p, G.grade_x7(out, log, state_dir=E23, kind="e"), GX6.grade_x6(out, log, state_dir=E23, kind="e")


def test_e_grade_28_prints_grade_x6_s_lines_then_the_disposition_ones_and_the_json():
    p, g, base = _e23()
    r = subprocess.run([sys.executable, EG28.__file__, p], capture_output=True, cwd=TESTING)
    assert r.returncode == 0, r.stderr
    text = r.stdout.replace(b"\r\n", b"\n").decode("utf-8")
    i = text.index("\n{\n")
    printed = text[:i + 1].splitlines()
    assert [("gate_x6 " + ln[len("gate_x7 "):]) if ln.startswith("gate_x7 ") else ln
            for ln in printed[:-G.N_LINES]] == base["report_lines"]
    assert printed[-G.N_LINES:] == g["report_lines"][-G.N_LINES:]
    got = json.loads(text[i:])
    assert (got["grade"], got["base"], got["base_x6"], got["base_x1"]) == ("grade_x7", "grade_x6", "grade_x5",
                                                                          "grade_e21")


def test_on_e23_every_crowd_reading_is_unread():
    """E23 carries no work leaf, no disposition and no release key."""
    _, g, _ = _e23()
    for k in ("restarts", "disposition", "string", "safe_release"):
        assert g[k] == {"read": False}, k
