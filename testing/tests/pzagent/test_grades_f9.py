"""base/grades/f9.py (Plan 28 Task 4), offline: `grade_f9` is `grade_f8` under "grade_f9" with the nine readings of
survival iteration 20 read by `grades.e17`'s readers and the nine of pass 18 read by `grades.e18`'s: each new key equal
to `grade_e17`'s or `grade_e18`'s on the same fabricated log, every `grade_f8` key unchanged on F3
(`f_goals_4-20261030-114742`), the unread case, the report lines, the module's imports (ruling P26-Q), and the real
checks on F11 (`f_goals_12-20261103-144240`): every `grade_f8` key equal to the committed `f_grade.txt`'s, through the
function and through `f_grade_9.py`, iteration 20's readings as its guide's section 8 counts them, the hits as its
section 2 table reads them (seven reactions over three kills) and the facing as the same section reads it; and F10's
hits (`f_goals_11-20261103-075140`), the close report's baseline."""
import ast
import json
import os
import subprocess
import sys

import pytest

from agent.base.grades import e17 as G17
from agent.base.grades import e18 as G18
from agent.base.grades import f8 as G8
from agent.base.grades import f9 as G
from agent.drivers import f_grade_9 as FG9
from . import test_grades_e14 as T14
from . import test_grades_e17 as T17
from . import test_grades_e18 as T18
from .test_gates_e import art

HERE = os.path.dirname(os.path.abspath(__file__))
TESTING = os.path.dirname(os.path.dirname(HERE))
F3 = os.path.join(TESTING, "artifacts", "f_goals_4-20261030-114742")
F10 = os.path.join(TESTING, "artifacts", "f_goals_11-20261103-075140")
F11 = os.path.join(TESTING, "artifacts", "f_goals_12-20261103-144240")
NEW = G.NEW
NEW17, NEW18 = G17.NEW, G18.NEW


def _capture(monkeypatch, module, fx):
    seen = {}

    def grab(actions=(), results=(), log=None, frames=(), fights=None, stop=None, end=None):
        seen.update(actions=list(actions), results=list(results), log=log, frames=list(frames), fights=fights,
                    stop=stop, end=end)
        return {k: {} for k in NEW}
    monkeypatch.setattr(module, "grade", grab)
    fx()
    monkeypatch.undo()
    a = T14.artifact(seen["actions"], seen["results"])
    if seen["fights"] is not None:
        a["loop"]["fights"] = list(seen["fights"])
    if seen["stop"] is not None:
        a["stop"]["reason"] = seen["stop"]
    if seen["end"] is not None:
        a["loop"]["end"] = dict(seen["end"])
    return a, seen


E17_FIXTURES = (T17.stuck_fixture, T17.floor_fixture, T17.fallen_fixture, T17.listing_fixture, T17.close_fixture,
                T17.stock_fixture, T17.low_fixture, T17.spent_fixture, T17.wounded_fixture)
E18_FIXTURES = (T18.hits_fixture, T18.wound_fixture, T18.back_fixture, T18.drift_fixture, T18.pain_fixture,
                T18.busy_fixture, T18.circle_fixture, T18.facing_fixture)


@pytest.mark.parametrize("fx", E17_FIXTURES, ids=lambda f: f.__name__)
def test_the_iteration_20_keys_are_grade_e17_s_readings_on_the_same_log(fx, monkeypatch):
    a, seen = _capture(monkeypatch, T17, fx)
    e17 = G17.grade_e17(a, decision_lines=seen["log"], lines=seen["frames"])
    f9 = G.grade_f9(a, decision_lines=seen["log"], lines=seen["frames"])
    assert f9["grade"] == "grade_f9" and {k: f9[k] for k in NEW17} == {k: e17[k] for k in NEW17}


@pytest.mark.parametrize("fx", E18_FIXTURES, ids=lambda f: f.__name__)
def test_the_pass_18_keys_are_grade_e18_s_readings_on_the_same_log(fx, monkeypatch):
    a, seen = _capture(monkeypatch, T18, fx)
    e18 = G18.grade_e18(a, decision_lines=seen["log"], lines=seen["frames"])
    f9 = G.grade_f9(a, decision_lines=seen["log"], lines=seen["frames"])
    assert f9["grade"] == "grade_f9" and {k: f9[k] for k in NEW18} == {k: e18[k] for k in NEW18}
    assert f9["kills"]["planner"] == e18["kills"]["planner"]
    assert any(e18[k].get("read") for k in NEW18)


def test_grade_f9_without_a_decision_log_reads_the_new_keys_unread_and_its_report_lines_are_f8_s_then_e17_e18_s():
    g = G.grade_f9(art())
    assert g["grade"] == "grade_f9" and all(g[k] == {"read": False} for k in NEW) and len(NEW) == 18
    assert g["report_lines"] == G8.report_lines_f8(g) + G17.lines_e17(g) + G18.lines_e18(g)
    assert all("no decision log read" in line or "no frames read" in line for line in g["report_lines"][-len(NEW):])
    assert G.gate_f9([]) == G8.gate_f8([])


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
    return fn(out, None, FG9.load_log(p), state_dir=d, goal_lines=FG9.load_goals(p))


def _committed(path, name):
    text = open(os.path.join(path, name), encoding="utf-8").read()
    i = text.index("\n{\n")
    return text[:i + 1].splitlines(), json.loads(text[i:])


def test_grade_f9_on_f3_reads_every_grade_f8_key_unchanged():
    g8, g9 = _grade(F3, "f_goals_4", G8.grade_f8), _grade(F3, "f_goals_4", G.grade_f9)
    skip = ("grade", "report_lines") + NEW
    assert g9["grade"] == "grade_f9" and all(g9[k]["read"] is True for k in NEW)
    assert {k: v for k, v in g8.items() if k not in skip} == {k: v for k, v in g9.items() if k not in skip}
    assert g9["report_lines"][:-len(NEW)] == g8["report_lines"]


def _off(**kw):
    return dict({"0": 0, "1": 0, "2": 0, "3": 0, "4": 0}, **kw)


F11_STRIKES = [(2230, "Bite", "attack", "a46", None, True), (2270, "Bite", "shove", "a49", False, True),
               (3085, "BiteLEFT", "shove", "a71", False, True), (3113, "BiteRIGHT", None, None, None, None),
               (7254, "BiteRIGHT", "shove", "a158", False, True), (7612, "BiteLEFT", "shove", "a165", False, True),
               (7957, "Bite", "shove", "a181", False, True)]


def test_grade_f9_on_f11_keeps_every_grade_f8_key_as_the_committed_f_grade_txt_and_reads_the_new_keys():
    """F11 ran survival iteration 20 on PZA/1.7.1: iteration 20's readings as its guide's section 8 counts them
    (`floor_finish` 5 lines, `listing` 59, `stock_early` 2); every rule key of pass 18 reads 0; the hits read the
    section 2 table's seven bite reactions over the three kills, the strike before each the table's (a46's swing,
    the five shoves left standing, none before 3113 within STRIKE_BEFORE_S); the facing the section's read (the six
    attack swings 0, 1, 1, 1, 0 and 3 points off, the 34 shoves' all on the bearing)."""
    g = _grade(F11, "f_goals_12", G.grade_f9)
    assert g["grade"] == "grade_f9" and all(g[k]["read"] is True for k in NEW)
    assert (g["floor_finish"]["lines"], g["listing"]["lines"], g["stock_early"]["lines"]) == (5, 59, 2)
    for k in T18.ZERO:
        assert g[k] == T18.zero(k, 27), k
    h = g["hits"]
    assert (h["runs"], h["kills"], h["per_kill"]) == (7, 3, 7 / 3) and g["kills"]["planner"] == 3
    assert h["kinds"] == {"Bite": 3, "BiteLEFT": 2, "BiteRIGHT": 2}
    assert [(s["seq"], s["kind"], s["type"], s["aid"], s["knockdown"], s["nearest"]) for s in h["strike_before"]] \
        == F11_STRIKES
    assert g["facing"] == {"read": True, "swings": 6, "off_by_points": _off(**{"0": 2, "1": 3, "3": 1}), "unread": 0,
                           "shoves_off": {"swings": 34, "off_by_points": _off(**{"0": 34}), "unread": 0},
                           "stomps_off": {"swings": 14, "off_by_points": _off(**{"0": 14}), "unread": 0},
                           "paired": {"frame": 54, "line": 0}}
    assert g["client_end"] == {"read": True, "stopped": "death", "seq": None, "health": None}
    _, committed = _committed(F11, "f_grade.txt")
    mine = json.loads(json.dumps(FG9.finite({k: v for k, v in g.items() if k not in NEW}), sort_keys=True,
                                 allow_nan=False))
    mine["grade"] = "grade_f8"
    mine["report_lines"] = mine["report_lines"][:-len(NEW)]
    assert mine == committed


def test_grade_f9_on_f10_reads_its_fifteen_hits_over_two_kills():
    """F10's hits, the close report's baseline: fifteen reaction runs over its two kills."""
    g = _grade(F10, "f_goals_11", G.grade_f9)
    h = g["hits"]
    assert (h["runs"], h["kills"], h["per_kill"]) == (15, 2, 7.5)
    assert h["kinds"] == {"Bite": 5, "BiteLEFT": 8, "BiteRIGHT": 1, "BiteDefended": 1}


def test_f_grade_9_on_f11_prints_the_committed_f_grade_txt_s_lines_then_the_new_ones():
    """`f_grade_9.py` on the committed F11 artifact: the committed `f_grade.txt`'s report lines, then the eighteen new
    lines, then the JSON whose grade_f8 keys equal the committed (CRLF folded)."""
    p = os.path.join(F11, "f_goals_12.json")
    if not os.path.isfile(p):
        pytest.skip("%s is not checked out" % F11)
    script = os.path.join(TESTING, "agent", "drivers", "f_grade_9.py")
    r = subprocess.run([sys.executable, script, p], capture_output=True, cwd=TESTING)
    assert r.returncode == 0
    text = r.stdout.decode("utf-8").replace("\r\n", "\n")
    i = text.index("\n{\n")
    printed, got = text[:i + 1].splitlines(), json.loads(text[i:])
    want_lines, want = _committed(F11, "f_grade.txt")
    assert printed[:-len(NEW)] == want_lines and len(printed) == len(want_lines) + len(NEW)
    assert got["grade"] == "grade_f9" and printed[-len(NEW):] == got["report_lines"][-len(NEW):]
    for k in NEW:
        got.pop(k)
    got["grade"] = "grade_f8"
    got["report_lines"] = got["report_lines"][:-len(NEW)]
    assert got == want


def test_f_grade_9_refuses_an_argument_it_does_not_define():
    """Read statically (CLAUDE.md section 5): its main answers usage, exit 2, on any call but one path."""
    src = open(FG9.__file__, encoding="utf-8").read()
    assert "if len(argv) != 1:" in src and "return 2" in src
    assert "from agent.base.grades.f9 import grade_f9" in src and "usage: f_grade_9.py" in src


F12 = os.path.join(TESTING, "artifacts", "f_goals_13-20261104-203950")


def test_f_grade_9_on_f12_reproduces_the_committed_f_grade_txt_byte_for_byte():
    """Ruling P26-Q: `f_grade_9.py` on the committed F12 artifact (the first LLM session graded through `grade_f9`)
    reproduces its committed `f_grade.txt` byte for byte (CRLF folded), so a drift in any live name read through the
    grade chain (`grade_f8`, `grade_f7`, `e18`, `e17`, `gates_e`) fails here."""
    p = os.path.join(F12, "f_goals_13.json")
    if not os.path.isfile(p):
        pytest.skip("%s is not checked out" % F12)
    script = os.path.join(TESTING, "agent", "drivers", "f_grade_9.py")
    r = subprocess.run([sys.executable, script, p], capture_output=True, cwd=TESTING)
    assert r.returncode == 0
    want = open(os.path.join(F12, "f_grade.txt"), "rb").read().replace(b"\r\n", b"\n")
    assert r.stdout.replace(b"\r\n", b"\n") == want
