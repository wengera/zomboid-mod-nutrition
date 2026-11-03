"""base/grades/f8.py (Plan 27 Task 2), offline: `grade_f8` is `grade_f7` under "grade_f8" with the nine readings of
survival iteration 19 read by `grades.e16`'s readers: each new key equal to `grade_e16`'s on the same fabricated log,
every `grade_f7` key unchanged on F3 (`f_goals_4-20261030-114742`), the unread case, the report lines, the module's
imports (ruling P26-Q), and the real checks on F9 (`f_goals_10-20261102-231705`): every `grade_f7` key equal to the
committed `f_grade.txt`'s, through the function and through `f_grade_8.py`, and the new readings as the grade reads
them (the three unwears rejected `held`, the one window climb)."""
import ast
import json
import os
import subprocess
import sys

import pytest

from agent.base.grades import e16 as G16
from agent.base.grades import f7 as G7
from agent.base.grades import f8 as G
from agent.drivers import f_grade_8 as FG8
from . import test_grades_e14 as T14
from . import test_grades_e16 as T16
from .test_gates_e import art

HERE = os.path.dirname(os.path.abspath(__file__))
TESTING = os.path.dirname(os.path.dirname(HERE))
F3 = os.path.join(TESTING, "artifacts", "f_goals_4-20261030-114742")
F9 = os.path.join(TESTING, "artifacts", "f_goals_10-20261102-231705")
F10 = os.path.join(TESTING, "artifacts", "f_goals_11-20261103-075140")
NEW = G16.NEW


def test_the_new_keys_are_grade_e16_s_readings_on_the_same_log(monkeypatch):
    """Each fixture of test_grades_e16, graded by grade_f8 over the same artifact and lines: every new key equal to
    grade_e16's."""
    seen = {}

    def grab(actions=(), results=(), log=None, frames=()):
        seen.update(actions=list(actions), results=list(results), log=log, frames=list(frames))
        return {k: {} for k in NEW}
    fixtures = (T16.finish_fixture, T16.tail_fixture, T16.hold_fixture, T16.rest_fixture, T16.kept_fixture,
                T16.low_fixture, T16.wounded_fixture, T16.window_fixture, T16.unwear_fixture)
    for fx in fixtures:
        monkeypatch.setattr(T16, "grade", grab)
        fx()
        monkeypatch.undo()
        a = T14.artifact(seen["actions"], seen["results"])
        e16 = G16.grade_e16(a, decision_lines=seen["log"], lines=seen["frames"])
        f8 = G.grade_f8(a, decision_lines=seen["log"], lines=seen["frames"])
        assert f8["grade"] == "grade_f8" and {k: f8[k] for k in NEW} == {k: e16[k] for k in NEW}, fx.__name__


def test_grade_f8_without_a_decision_log_reads_the_new_keys_unread_and_its_report_lines_are_f7_s_then_e16_s():
    g = G.grade_f8(art())
    assert g["grade"] == "grade_f8" and all(g[k] == {"read": False} for k in NEW)
    assert g["report_lines"] == G7.report_lines_f7(g) + G16.lines_e16(g)
    assert all("no decision log read" in line for line in g["report_lines"][-len(NEW):])
    assert G.gate_f8([]) == G7.gate_f7([])


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
    return fn(out, None, FG8.load_log(p), state_dir=d, goal_lines=FG8.load_goals(p))


def _committed(path, name):
    text = open(os.path.join(path, name), encoding="utf-8").read()
    i = text.index("\n{\n")
    return text[:i + 1].splitlines(), json.loads(text[i:])


def test_grade_f8_on_f3_reads_every_grade_f7_key_unchanged():
    g7, g8 = _grade(F3, "f_goals_4", G7.grade_f7), _grade(F3, "f_goals_4", G.grade_f8)
    skip = ("grade", "report_lines") + NEW
    assert g8["grade"] == "grade_f8" and all(g8[k]["read"] is True for k in NEW)
    assert {k: v for k, v in g7.items() if k not in skip} == {k: v for k, v in g8.items() if k not in skip}
    assert g8["report_lines"][:-len(NEW)] == g7["report_lines"]


def test_grade_f8_on_f9_keeps_every_grade_f7_key_as_the_committed_f_grade_txt_and_reads_the_new_keys():
    g = _grade(F9, "f_goals_10", G.grade_f8)
    assert g["grade"] == "grade_f8" and all(g[k]["read"] is True for k in NEW)
    for k, v in T16.E18_READ.items():
        if k != "unwear_live":
            assert g[k] == v, k
    # P26-O's three unwears of the cotton T-shirt (a91, a107, a121), each rejected `held` (the Lua's unwear fixed
    # after the session); no rip followed
    assert g["unwear_live"] == {"read": True, "sent": 3, "done": 0, "rejected": {"held": 3}, "failed": {},
                                "rip_after": 0}
    # F9 swung no P26-L1 swing and walked no endurance hold; its one window climb (a3) under WINDOW_STALL_S
    assert g["wounded_swings"] == {"read": True, "lines": 0, "sent": 0, "landed": 0, "health_before_after": [],
                                   "wound_frames_after": 0, "wounded": 0}
    assert g["hold_rest"] == {"read": True, "ticks": 0, "near": 0, "walk_ticks": 0, "standing": {"read": False},
                              "walking": {"read": False}}
    assert g["spent_kept"] == {"read": True, "lines": 0, "parts": {}, "health_across": {}, "short": 0,
                               "redressed": 0}
    assert g["window_still"] == {"read": True, "over": 0, "climbs": [
        {"aid": "a3", "state": "done", "accept_done_s": 2.609, "still_s": 2.514}]}
    _, committed = _committed(F9, "f_grade.txt")
    mine = json.loads(json.dumps(FG8.finite({k: v for k, v in g.items() if k not in NEW}), sort_keys=True,
                                 allow_nan=False))
    mine["grade"] = "grade_f7"
    mine["report_lines"] = mine["report_lines"][:-len(NEW)]
    assert mine == committed


def test_f_grade_8_on_f9_prints_the_committed_f_grade_txt_s_lines_then_the_new_ones():
    """`f_grade_8.py` on the committed F9 artifact: the committed `f_grade.txt`'s report lines, then the nine new
    lines, then the JSON whose grade_f7 keys equal the committed (CRLF folded)."""
    p = os.path.join(F9, "f_goals_10.json")
    if not os.path.isfile(p):
        pytest.skip("%s is not checked out" % F9)
    script = os.path.join(TESTING, "agent", "drivers", "f_grade_8.py")
    r = subprocess.run([sys.executable, script, p], capture_output=True, cwd=TESTING)
    assert r.returncode == 0
    text = r.stdout.decode("utf-8").replace("\r\n", "\n")
    i = text.index("\n{\n")
    printed, got = text[:i + 1].splitlines(), json.loads(text[i:])
    want_lines, want = _committed(F9, "f_grade.txt")
    assert printed[:-len(NEW)] == want_lines and len(printed) == len(want_lines) + len(NEW)
    assert got["grade"] == "grade_f8"
    for k in NEW:
        got.pop(k)
    got["grade"] = "grade_f7"
    got["report_lines"] = got["report_lines"][:-len(NEW)]
    assert got == want


def test_f_grade_8_on_f10_reproduces_the_committed_f_grade_txt_byte_for_byte():
    """Ruling P26-Q: `f_grade_8.py` on the committed F10 artifact (the first LLM session graded through `grade_f8`)
    reproduces its committed `f_grade.txt` byte for byte (CRLF folded), so a drift in any live name read through the
    grade chain (`grade_f7`: `llm.objects`, `view.OPEN_KEY`, the rest) fails here."""
    p = os.path.join(F10, "f_goals_11.json")
    if not os.path.isfile(p):
        pytest.skip("%s is not checked out" % F10)
    script = os.path.join(TESTING, "agent", "drivers", "f_grade_8.py")
    r = subprocess.run([sys.executable, script, p], capture_output=True, cwd=TESTING)
    assert r.returncode == 0
    want = open(os.path.join(F10, "f_grade.txt"), "rb").read().replace(b"\r\n", b"\n")
    assert r.stdout.replace(b"\r\n", b"\n") == want


def test_f_grade_8_refuses_an_argument_it_does_not_define():
    """Read statically (CLAUDE.md section 5): its main answers usage, exit 2, on any call but one path."""
    src = open(FG8.__file__, encoding="utf-8").read()
    assert "if len(argv) != 1:" in src and "return 2" in src
    assert "from agent.base.grades.f8 import grade_f8" in src
