"""base/grades/f11.py (Plan 29 Task 3), offline: `grade_f11` is `grade_f10` under "grade_f11" with `grades.e20`'s reads
(the kills and the hits whole, the facing over every press, the melee's swings by the arms' pain, iteration 23's rule
readings: each new key equal to `grade_e20`'s on the same fabricated log) and the views' `stall` line, every
`grade_f10` key unchanged through the legacy views on the fabricated log and on F3 (`f_goals_4-20261030-114742`), the
unread cases, the report lines, the module's imports and frozen copy (ruling P26-Q), and the real checks on F13
(`f_goals_14-20261105-021722`): `kills.planner` 4, two the ladder's `targetDead` and two the melee's done `kill`, the
events agreeing; the eleven melee swings facing their targets and sent under STRAIN_HARD (the T89 write-up's
section 3); iteration 23's readings and the stall views unread (the session predates the rules); every inherited key
equal to the committed `f_grade.txt`'s, through the function and through `f_grade_11.py`."""
import ast
import json
import os
import subprocess
import sys

import pytest

from agent.base.grades import e20 as G20
from agent.base.grades import f10 as G10
from agent.base.grades import f11 as G
from agent.drivers import f_grade_11 as FG11
from . import test_grades_e14 as T14
from . import test_grades_e20 as T20
from .test_gates_e import art

HERE = os.path.dirname(os.path.abspath(__file__))
TESTING = os.path.dirname(os.path.dirname(HERE))
F3 = os.path.join(TESTING, "artifacts", "f_goals_4-20261030-114742")
F13 = os.path.join(TESTING, "artifacts", "f_goals_14-20261105-021722")
NEW20 = G20.NEW
OWN = NEW20 + ("stall_views",)


def to_f10(g):
    """grade_f11's dict as grade_f10's: the new keys dropped, `kills` and `hits` their legacy views, the name, the new
    report lines dropped."""
    g = dict(g)
    for k in OWN:
        g.pop(k)
    g["kills"] = g["kills"]["legacy_planner"]
    if g["hits"].get("read"):
        h = dict(g["hits"])
        h.update(h.pop("legacy"))
        g["hits"] = h
    g["grade"] = "grade_f10"
    g["report_lines"] = g["report_lines"][:-G.N_LINES]
    return g


@pytest.mark.parametrize("which", ("cut2", "rules", "cut2-nolog"))
def test_the_pass_20_keys_are_grade_e20_s_readings_on_the_same_log(which):
    if which == "rules":
        a, dl, lines = T14.artifact(), T20.rules_log(), [T20.hf(0.0)]
    else:
        a, dl, lines = T14.artifact(T20.cut2_actions(), []), (T20.cut2_log() if which == "cut2" else None), \
            T20.cut2_lines()
    e20 = G20.grade_e20(a, decision_lines=dl, lines=lines)
    f11 = G.grade_f11(a, decision_lines=dl, lines=lines)
    assert f11["grade"] == "grade_f11" and {k: f11[k] for k in NEW20 + ("kills", "hits")} == {
        k: e20[k] for k in NEW20 + ("kills", "hits")}
    assert to_f10(f11) == G10.grade_f10(a, decision_lines=dl, lines=lines)


def test_grade_f11_without_a_decision_log_reads_the_new_keys_unread_and_its_report_lines_are_f10_s_then_e20_s():
    g = G.grade_f11(art())
    assert g["grade"] == "grade_f11" and all(g[k] == {"read": False} for k in OWN)
    assert G.NEW == G10.NEW + NEW20 + ("stall_views",) and G.N_LINES == G20.N_LINES + 1
    assert g["report_lines"] == G10.report_lines_f10(G20._legacy(g)) + G20.lines_e20(g) + [g["report_lines"][-1]]
    assert "no line read" in g["report_lines"][-1] and "(iteration 23, P29-B)" in g["report_lines"][-1]
    assert G.gate_f11([]) == G10.gate_f10([])


# ================================================================ the stall views
def view(stall=None, goal=None, ok=True):
    lines = ["pos: {\"x\":10747.8,\"y\":10641.7,\"z\":0}", "last_goal: {\"end\":\"failed\"}"]
    if stall is not None:
        lines.append("stall: " + json.dumps(stall, separators=(",", ":")))
    lines.append("cooled: []")
    return {"prompt": "\n".join(lines), "goal": goal, "ok": ok, "error": None if ok else "invalid: x"}


def stall_rows():
    """Five calls: two views naming the stall (10748, 10650), one answered at that square, one with a LootBuilding;
    a third naming (10700, 10600) refused; a view without the line; a line that does not parse."""
    return [view([10748, 10650], {"type": "ExploreToward", "x": 10748, "y": 10650}),
            view([10748, 10650], {"type": "LootBuilding", "building": 2}),
            view([10700, 10600], None, ok=False),
            view(None, {"type": "ExploreToward", "x": 10748, "y": 10650}),
            {"prompt": "stall: [10748,", "goal": None, "ok": False}]


def test_the_stall_views_read_the_views_carrying_the_line_and_the_goals_taken_at_the_stalled_square():
    assert G.f_stall_views(stall_rows()) == {"read": True, "n": 3, "taken": {"ExploreToward": 1, "LootBuilding": 1},
                                             "at_stall": 1, "squares": [[10748, 10650], [10700, 10600]]}
    g = G.grade_f11(art(), goal_lines=stall_rows())
    assert g["stall_views"]["n"] == 3 and "3 views carrying `stall:`" in g["report_lines"][-1]
    assert "[reading]" in g["report_lines"][-1]


def test_the_stall_views_read_unread_without_a_goals_log_or_a_view_carrying_the_line():
    assert G.f_stall_views(None) == {"read": False}
    assert G.f_stall_views([view(None, {"type": "Rest"})]) == {"read": False}
    assert G._stall("a\nstall: [1,2]\nb") == [1, 2] and G._stall("stall: x") is None and G._stall(None) is None


def test_a_mutant_of_the_stall_views_fails_its_fixture():
    src = open(G.__file__, encoding="utf-8").read()
    for old, new in (('[g.get("x"), g.get("y")] == sq', "False"), ("if sq not in squares:", "if True:"),
                     ("if ln.startswith(STALL_LINE):", "if ln.startswith(STALL_KEY):")):
        assert old in src
        ns = {"__name__": "f11_mutant"}
        exec(compile(src.replace(old, new), "f11_mutant", "exec"), ns)    # noqa: S102 - a scratch copy
        rows = stall_rows() + [{"prompt": "stallx [1,2]", "goal": None, "ok": False}]   # not the line
        assert ns["f_stall_views"](rows) != G.f_stall_views(rows) == G.f_stall_views(stall_rows()), old


def test_the_module_imports_no_live_planner_or_world_name_and_holds_its_copy():
    tree = ast.parse(open(G.__file__, encoding="utf-8").read())
    mods = [n.module or "" for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)]
    mods += [a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names]
    assert mods and not any(m.startswith(("agent.base.planner", "agent.base.world")) for m in mods), mods
    assert not any(getattr(v, "__module__", "").startswith(("agent.base.planner", "agent.base.world"))
                   for v in vars(G).values())
    assert G.STALL_KEY == "stall" and G.STALL_LINE == "stall: "


# ================================================================ the committed artifacts
def _grade(d, name, fn):
    p = os.path.join(d, name + ".json")
    if not os.path.isfile(p):
        pytest.skip("%s is not checked out" % d)
    with open(p, encoding="utf-8") as fh:
        out = json.load(fh)
    return fn(out, None, FG11.load_log(p), state_dir=d, goal_lines=FG11.load_goals(p))


def _committed(path, name):
    text = open(os.path.join(path, name), encoding="utf-8").read()
    i = text.index("\n{\n")
    return text[:i + 1].splitlines(), json.loads(text[i:])


def test_grade_f11_on_f3_reads_every_grade_f10_key_unchanged():
    g10, g11 = _grade(F3, "f_goals_4", G10.grade_f10), _grade(F3, "f_goals_4", G.grade_f11)
    assert g11["grade"] == "grade_f11" and to_f10(g11) == g10


def test_grade_f11_on_f13_reads_the_four_kills_whole_two_a_side_with_the_events_agreeing():
    """F13's four kills (the T89 write-up's section 1): 28222 and 28215 by the ladder's floor swings (`targetDead`, the
    frozen read's 2), 28219 and 28212 by the strike-mode melees a195 and a230 (`kill`), placed in fights 3 and 4 by
    their done lines (the frozen `per_fight` [0, 0, 2, 0, 0, 0] kept under `legacy_planner`); no hit: 0 a kill over
    4."""
    g = _grade(F13, "f_goals_14", G.grade_f11)
    k = g["kills"]
    assert (k["planner"], k["events"], k["agree"]) == (4, 4, True)
    assert k["melee"] == [28219, 28212] and k["ladder"] == [28222, 28215]
    assert k["planner_ids"] == k["event_ids"] == [28222, 28215, 28219, 28212] and k["legacy_planner"]["planner"] == 2
    assert (g["hits"]["runs"], g["hits"]["kills"], g["hits"]["per_kill"]) == (0, 4, 0.0)
    assert k["per_fight"] == [0, 0, 2, 1, 1, 0] and k["legacy_planner"]["per_fight"] == [0, 0, 2, 0, 0, 0]


def test_grade_f11_on_f13_reads_the_eleven_melee_swings_facing_and_under_the_pain():
    """The eleven melee `swing` events each read the target's bearing on the frame after (section 3: E on eight, SE on
    three, 0 points off); the ladder's nine attacks (8 at 0 points, a141 at 1) and one stomp (0); every swing sent
    under STRAIN_HARD (the `melee` log's pain 0 to 1.8), every one lowering its target, none knocking it down, two
    killing."""
    g = _grade(F13, "f_goals_14", G.grade_f11)
    f = g["facing_all"]
    m, lad = f["by_source"]["melee"], f["by_source"]["ladder"]
    assert (f["presses"], f["other"], f["paired"]) == (21, 0, {"frame": 21, "line": 0})
    assert m["swings"] == T20._t(11, p0=11) and all(m[k]["n"] == 0 for k in ("shoves", "stomps", "floors"))
    assert lad["swings"] == T20._t(9, p0=8, p1=1) and lad["stomps"] == T20._t(1, p0=1)
    ps = g["pain_swings"]
    assert ps["under"] == T20._band(11, 11, 0, 2) and ps["at_or_above"] == T20._band() == ps["unread"]
    assert max(r["pain"] for r in ps["rows"]) == 1.8


def test_grade_f11_on_f13_keeps_every_grade_f10_key_as_the_committed_f_grade_txt_and_reads_the_rules_unread():
    g = _grade(F13, "f_goals_14", G.grade_f11)
    assert g["grade"] == "grade_f11" and T20.unread(g, ends=5) and g["stall_views"] == {"read": False}
    lines, committed = _committed(F13, "f_grade.txt")
    mine = to_f10(json.loads(json.dumps(FG11.finite(g), sort_keys=True, allow_nan=False)))
    assert mine == committed and g["report_lines"][:-G.N_LINES] == lines


def test_f_grade_11_on_f13_prints_the_committed_f_grade_txt_s_lines_then_the_new_ones():
    """`f_grade_11.py` on the committed F13 artifact: the committed `f_grade.txt`'s report lines, then the new lines,
    then the JSON whose grade_f10 keys equal the committed (CRLF folded)."""
    p = os.path.join(F13, "f_goals_14.json")
    if not os.path.isfile(p):
        pytest.skip("%s is not checked out" % F13)
    script = os.path.join(TESTING, "agent", "drivers", "f_grade_11.py")
    r = subprocess.run([sys.executable, script, p], capture_output=True, cwd=TESTING)
    assert r.returncode == 0
    text = r.stdout.decode("utf-8").replace("\r\n", "\n")
    i = text.index("\n{\n")
    printed, got = text[:i + 1].splitlines(), json.loads(text[i:])
    want_lines, want = _committed(F13, "f_grade.txt")
    assert printed[:-G.N_LINES] == want_lines and len(printed) == len(want_lines) + G.N_LINES
    assert got["grade"] == "grade_f11" and printed[-G.N_LINES:] == got["report_lines"][-G.N_LINES:]
    assert to_f10(got) == want and got["kills"]["planner"] == 4


def test_f_grade_11_refuses_an_argument_it_does_not_define():
    """Read statically (CLAUDE.md section 5): its main answers usage, exit 2, on any call but one path."""
    src = open(FG11.__file__, encoding="utf-8").read()
    assert "if len(argv) != 1:" in src and "return 2" in src
    assert "from agent.base.grades.f11 import grade_f11" in src and "usage: f_grade_11.py" in src
    body = src[src.index('"""', 3):]
    assert "grade_f10" not in body and "f_grade_10" not in body


F14 = os.path.join(TESTING, "artifacts", "f_goals_15-20261105-092752")


def test_f_grade_11_on_f14_reproduces_the_committed_f_grade_txt_byte_for_byte():
    """Ruling P26-Q: `f_grade_11.py` on the committed F14 artifact (the first session graded through `grade_f11`, the
    first with the whole kill read and iteration 23's readings) reproduces its committed `f_grade.txt` byte for byte
    (CRLF folded), so a drift in any live name read through the grade chain fails here."""
    p = os.path.join(F14, "f_goals_15.json")
    if not os.path.isfile(p):
        pytest.skip("%s is not checked out" % F14)
    script = os.path.join(TESTING, "agent", "drivers", "f_grade_11.py")
    r = subprocess.run([sys.executable, script, p], capture_output=True, cwd=TESTING)
    assert r.returncode == 0
    want = open(os.path.join(F14, "f_grade.txt"), "rb").read().replace(b"\r\n", b"\n")
    assert r.stdout.replace(b"\r\n", b"\n") == want
