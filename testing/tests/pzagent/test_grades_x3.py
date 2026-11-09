"""base/grades/x3.py (Plan 33 Task 4), offline: `grade_x3` and its five group readings (`head_ticks`: the finish's head
step off the press leaves and the head_stall handbacks; `crawler_first`: the lines carrying the CRAWLER_FIRST why, the
finishes they sent and the kills; `group_leave`: the GROUP_LEAVE legs, toward a door or a run, with the standing count
at each leg's first line; `drag_guard`: the guard's shoves and refused runs, SIDE_CLEAR's clear steers and their
rotations, and every sent steer heading into a standing zombie; `idle_snap`: the body against the nearest standing
zombie on the frames no melee runs), each on a fabricated ring where it counts, its unread case and a mutant of each
reading that its fixture fails; every grade_x2 key kept under `grade_x3` on the committed F18
(`f_goals_18-20261108-235005`, Plan 32's evidence session, its leaves before Task 1's `head_ticks`) and E23 artifacts,
through the function and through the regrade scripts `f_grade_15.py` and `e_grade_24.py`; F18's regrade pinned byte
for byte (its grade_x2 lines and keys equal to the committed `f_grade.txt`'s, the whole output's sha256, and the group
numbers)."""
import functools
import hashlib
import json
import math
import os
import subprocess
import sys

import pytest

from agent.base.grades import x2 as GX2
from agent.base.grades import x3 as G
from agent.drivers import e_grade_23 as EG23
from agent.drivers import e_grade_24 as EG24
from agent.drivers import f_grade_15 as FG15
from . import test_grades_e20 as T20
from .test_gates_e7 import T0
from .test_grades_e14 import actl
from .test_grades_x2 import act_row, fr, leaf, mel, ordered, rec, zr

HERE = os.path.dirname(os.path.abspath(__file__))
TESTING = os.path.dirname(os.path.dirname(HERE))
F18 = os.path.join(TESTING, "artifacts", "f_goals_18-20261108-235005")
E23 = os.path.join(TESTING, "artifacts", "e_day_23-20261105-095110")
R = math.radians


def dline(t, threat, type_=None, sent=True, **args):
    """A decision line `t` seconds into the loop: its threat why and its action (None without a type)."""
    return {"action": {"type": type_, "args": dict(args)} if type_ else None, "branch": "threat", "gameMin": 600,
            "inputs": {"branches": {"threat": dict(threat)}}, "sent": sent, "wall": T0 + t}


def dead(zid, t):
    return {"kind": "event", "event": "zombie_dead", "id": zid, "seq": int(t * 10), "tick": int(t * 60),
            "wallMs": int((T0 + t) * 1000)}


# ================================================================ head_ticks
def head_case():
    """m1: a press waiting 3 head ticks, then the head_stall handback at 20; m2: a press with no wait, a kill; m3: a
    crowd handback with no head_ticks (a leaf before Task 1)."""
    acts = [mel("m1", 0.5, state="accepted"), mel("m1", 1.0, "stomp"),
            mel("m1", 1.2, "head", press=leaf(head_ticks=3)),
            mel("m1", 2.4, state="done", end="handback", why="head_stall", head_ticks=20, n=0),
            mel("m2", 3.0, state="accepted"), mel("m2", 3.5, "stomp"),
            mel("m2", 3.7, state="done", end="kill", kill=True, press=leaf(head_ticks=0)),
            mel("m3", 4.0, state="accepted"), mel("m3", 4.5, state="done", end="handback", why="crowd", n=2)]
    out = rec([act_row(a, "melee", s, targetId=7, mode="finish") for a, s in (("m1", 0.4), ("m2", 2.9), ("m3", 3.9))])
    return out, None, ordered(acts)


def _head():
    return G.readings_x3(*head_case())["head_ticks"]


def test_head_ticks_reads_the_press_leaves_and_the_head_stall_handback():
    h = _head()
    assert h == {"read": True, "leaves": 3, "max": 20, "over_cap": 1, "by_melee": [["m1", 20], ["m2", 0]]}


def test_head_ticks_reads_unread_without_a_melee_line_and_none_on_leaves_before_task_1():
    assert G.readings_x3(rec(), None, [fr(1.0, 0.0)])["head_ticks"] == {"read": False}
    old = [mel("m1", 0.5, state="accepted"), mel("m1", 1.0, "stomp", press=leaf())]
    assert G.readings_x3(rec([act_row("m1", "melee", 0.4, targetId=7)]), None, old)["head_ticks"] == {
        "read": True, "leaves": 0, "max": None, "over_cap": 0, "by_melee": []}


# ================================================================ crawler_first
def crawler_case():
    """Five lines: one without the key; the key with a finish sent at 9; the key nested in a fight's why with a strike
    at 8; the key with a finish not sent; the key with a stomp at 10. Zombie 9 dies, 10 does not."""
    rows = [dline(1.0, {"flee": "many"}, "steer", vx=1.0, vy=0.0),
            dline(1.5, {"crawler_first": {"id": 9, "d": 0.5}}, "melee", targetId=9, mode="finish"),
            dline(2.0, {"fight": {"crawler_first": {"id": 8, "d": 0.9}}}, "melee", targetId=8, mode="strike"),
            dline(2.5, {"crawler_first": {"id": 11, "d": 0.4}}, "melee", sent=False, targetId=11, mode="finish"),
            dline(3.0, {"crawler_first": {"id": 10, "d": 0.7}}, "stomp", targetId=10)]
    return rec(), rows, [dead(9, 2.2), dead(77, 2.6)]


def _crawler():
    return G.readings_x3(*crawler_case())["crawler_first"]


def test_crawler_first_counts_its_lines_their_finishes_and_the_kills():
    c = _crawler()
    assert (c["read"], c["lines"], c["finishes"], c["targets"], c["kills"]) == (True, 4, 2, [9, 10], 1)
    assert [(r["i"], r["sent"], r["type"], r["mode"], r["target"]) for r in c["rows"]] == [
        (1, True, "melee", "finish", 9), (2, True, "melee", "strike", 8), (3, False, None, None, None),
        (4, True, "stomp", None, 10)]
    assert c["rows"][1]["crawler"] == {"id": 8, "d": 0.9}


def test_the_decision_readings_are_unread_without_a_decision_log():
    g = G.readings_x3(rec(), None, [fr(1.0, 0.0)])
    assert g["crawler_first"] == g["group_leave"] == g["drag_guard"] == {"read": False}


# ================================================================ group_leave
def group_case():
    """Eight lines: the key on lines 1-2 (a steer sent on 1), 4-5 (a walkTo on 4) and 7 (nothing sent); the frame
    before line 1 lists two standing zombies within GROUP_NEAR_R, a fallen one within it and a standing one at 5 tiles;
    the frame before line 4 one standing at 1 tile."""
    k = {"group_leave": {"centroid": [12.0, 10.0], "n": 2}}
    rows = [dline(1.0, {}), dline(1.5, k, "steer", vx=-1.0, vy=0.0), dline(2.0, k), dline(2.5, {}),
            dline(3.0, k, "walkTo", x=1, y=2), dline(3.5, k, "walkTo", sent=False, x=1, y=2), dline(4.0, {}),
            dline(4.5, k, "steer", sent=False, vx=1.0, vy=0.0)]
    frames = [fr(1.4, 0.0, zs=[zr(1, 12.0, 10.0), zr(2, 10.0, 12.5), zr(3, 11.0, 10.0, floor=True),
                               zr(4, 15.0, 10.0)]),
              fr(2.9, 0.0, zs=[zr(1, 11.0, 10.0)])]
    return rec(), rows, ordered(frames)


def _group():
    return G.readings_x3(*group_case())["group_leave"]


def test_group_leave_reads_its_legs_toward_a_door_or_a_run_and_the_standing_count():
    g = _group()
    assert (g["read"], g["lines"], g["legs"], g["to_door"], g["runs"], g["standing_at"]) == (True, 5, 2, 1, 1, [2, 1])
    assert [(r["i0"], r["i1"], r["types"]) for r in g["rows"]] == [(1, 2, ["steer"]), (4, 5, ["walkTo"])]


# ================================================================ drag_guard
def drag_case():
    """The guard's lines: a melee shove, a steer east past a standing zombie 0.3 tiles off its line, nothing sent;
    SIDE_CLEAR's: a steer south rotated 30 degrees (clear: the zombie 1.5 tiles off that line), a shove with no clear
    bearing."""
    rows = [dline(1.0, {"flee": "many", "drag_guard": {"hit": True}}, "melee", targetId=5, mode="shove"),
            dline(1.5, {"flee": "many", "drag_guard": {"moved": True}}, "steer", vx=1.0, vy=0.0),
            dline(2.0, {"flee": "many", "drag_guard": {"stuck": 10}}),
            dline(2.5, {"side_clear": {"rotation": 30}}, "steer", vx=0.0, vy=1.0),
            dline(3.0, {"side_clear": 45}, "shove", targetId=5)]
    return rec(), rows, ordered([fr(0.5, 0.0, zs=[zr(5, 11.5, 10.3)])])


def _drag():
    return G.readings_x3(*drag_case())["drag_guard"]


def test_drag_guard_reads_the_shoves_the_refused_runs_the_clear_steers_and_the_steers_into_a_zombie():
    assert _drag() == {"read": True, "guard_lines": 3, "shoves": 1, "runs_refused": 2, "runs": 1, "clear_lines": 2,
                       "clear_steers": 1, "rotations": [30], "side_shoves": 1, "into_side": {"steers": 2, "blocked": 1}}


def test_a_steer_s_clearance_is_read_over_its_first_side_look_tiles_only():
    """A standing zombie on the heading 3.5 tiles out (beyond SIDE_LOOK, more than SIDE_R past the leg's end) does not
    block it; one 3.5 tiles out and 0.5 off the line is within SIDE_R of the leg's end and does."""
    assert G.blocks(fr(0.0, 0.0, zs=[zr(1, 14.5, 10.0)]), 1.0, 0.0) is False
    assert G.blocks(fr(0.0, 0.0, zs=[zr(1, 13.4, 10.5)]), 1.0, 0.0) is True
    assert G.blocks(fr(0.0, 0.0, zs=[zr(1, 9.0, 10.0)]), 1.0, 0.0) is False     # behind
    assert G.blocks(fr(0.0, 0.0, zs=[zr(1, 11.0, 10.0)]), 0.0, 0.0) is False    # no heading


# ================================================================ idle_snap
def idle_case():
    """Five frames: idle with a standing zombie east at 1.5 (body 10 off); idle with one at 3 only; a melee running
    with one at 1.5; a walk running with a fallen one at 1 and a standing one south at 2 (body 20 off); the melee done
    with one east at 1 (body 35 off)."""
    m1 = {"aid": "m1", "state": "progress", "step": "face"}
    frames = [fr(1.0, R(10), zs=[zr(1, 11.5, 10.0)]), fr(1.1, R(50), zs=[zr(1, 13.0, 10.0)]),
              fr(1.2, R(90), zs=[zr(1, 11.5, 10.0)], act=m1),
              fr(1.3, R(110), zs=[zr(2, 11.0, 10.0, floor=True), zr(1, 10.0, 12.0)],
                 act={"aid": "w1", "state": "progress", "step": None}),
              fr(1.4, R(-35), zs=[zr(1, 11.0, 10.0)], act=dict(m1, state="done"))]
    acts = [mel("m1", 1.15, state="accepted"), actl("w1", "walkTo", "accepted", 1.25)]
    return rec([act_row("m1", "melee", 1.1, targetId=1)]), None, ordered(frames, acts)


def _idle():
    return G.readings_x3(*idle_case())["idle_snap"]


def test_idle_snap_reads_the_body_on_the_frames_no_melee_runs_near_a_standing_zombie():
    i = _idle()
    assert i["read"] is True and i["frames"] == 3
    assert i["body"] == {"n": 3, "median": pytest.approx(20.0), "p90": pytest.approx(35.0), "hold30": pytest.approx(2 / 3)}
    assert i["body_err_median"] == pytest.approx(20.0)


def test_idle_snap_reads_unread_without_a_body_angle():
    out, rows, lines = idle_case()
    lines = [dict(ln, me=dict(ln["me"], bodyAngle=None)) if ln.get("kind") == "frame" else ln for ln in lines]
    assert G.readings_x3(out, rows, lines)["idle_snap"] == {"read": False}


def test_the_readings_read_the_sources_clipped_at_the_stop():
    out, rows, lines = crawler_case()
    out["stop"]["wallS"] = 1.6 + (out["loop"]["startPyMs"] / 1000.0 - T0)
    assert G.readings_x3(out, rows, lines)["crawler_first"]["lines"] == 1


def test_the_scorecard_cell_is_head_ticks_max():
    assert G.head_ticks_cell(*head_case()) == 20
    assert G.head_ticks_cell(rec(), None, []) is None


# ================================================================ the module's frozen copies
def test_the_module_imports_no_live_planner_world_or_tools_name_and_holds_its_own_copies():
    names = T20._imports(G.__file__)
    assert not any(m.startswith(("agent.base.planner", "agent.base.world", "tools", "trial_score")) for m in names)
    ns = vars(G)
    assert (ns["MELEE"], ns["STEER"], ns["WALK"], ns["SHOVE"], ns["STOMP"], ns["FINISH"]) == (
        "melee", "steer", "walkTo", "shove", "stomp", "finish")
    assert (ns["HEAD_TICKS"], ns["HANDBACK"], ns["HEAD_STALL"], ns["THREAT"]) == (
        "head_ticks", "handback", "head_stall", "threat")
    assert (ns["CRAWLER_FIRST"], ns["GROUP_LEAVE"], ns["DRAG_GUARD"], ns["SIDE_CLEAR"]) == (
        "crawler_first", "group_leave", "drag_guard", "side_clear")
    assert (ns["GROUP_NEAR_R"], ns["SIDE_R"], ns["SIDE_LOOK"], ns["IDLE_SNAP_R"]) == (3.0, 1.0, 3.0, 2.5)
    assert ns["LIVE_STATES"] == ("accepted", "progress")
    assert ns["NEW"] == ("head_ticks", "crawler_first", "group_leave", "drag_guard", "idle_snap")


# ================================================================ the mutants
def _mutated(name, edit):
    """grades/x3.py's source with `edit` applied inside the top-level def `name` only, executed as a module copy."""
    src = open(G.__file__, encoding="utf-8").read()
    head = "\ndef %s(" % name
    start = src.index(head)
    nxt = [i for i in (src.find("\ndef ", start + 5), src.find("\nclass ", start + 5)) if i >= 0]
    end = min(nxt) if nxt else len(src)
    new = edit(src[start:end])
    assert new != src[start:end], (name, "the mutant changed nothing")
    ns = {"__name__": "x3_mutant"}
    exec(compile(src[:start] + new + src[end:], "x3_mutant", "exec"), ns)    # noqa: S102 - a scratch copy
    return ns


MUTANTS = [
    # head_ticks
    ("e_head_ticks", lambda b: b.replace("res.get(HEAD_TICKS)):", "None):"), lambda: _head()["max"] == 20),
    ("e_head_ticks", lambda b: b.replace(' and res.get("why") == HEAD_STALL', ""), lambda: _head()["over_cap"] == 1),
    ("e_head_ticks", lambda b: b.replace("rows.append([aid, max(vals)])", "rows.append([aid, vals[0]])"),
     lambda: _head()["by_melee"] == [["m1", 20], ["m2", 0]]),
    # crawler_first
    ("carries", lambda b: b.replace(" or any(carries(v, key) for v in why.values())", ""),
     lambda: _crawler()["lines"] == 4),
    ("is_finish", lambda b: b.replace(' and args.get("mode") == FINISH', ""), lambda: _crawler()["finishes"] == 2),
    ("e_crawler_first", lambda b: b.replace(" if t in dead", ""), lambda: _crawler()["kills"] == 1),
    ("sent_action", lambda b: b.replace('row.get("sent") is not True or ', ""), lambda: _crawler()["finishes"] == 2),
    ("value_of", lambda b: b.replace("return value_of(v, key)", "return v", 1),
     lambda: _crawler()["rows"][1]["crawler"] == {"id": 8, "d": 0.9}),
    # group_leave
    ("e_group_leave", lambda b: b.replace("cur[-1] != i - 1", "False"), lambda: _group()["legs"] == 2),
    ("e_group_leave", lambda b: b.replace("standing(f, GROUP_NEAR_R)", "standing(f, 99.0)"),
     lambda: _group()["standing_at"] == [2, 1]),
    ("e_group_leave", lambda b: b.replace("if WALK in g", "if g"), lambda: _group()["to_door"] == 1),
    ("e_group_leave", lambda b: b.replace("if not types:", "if False:"), lambda: _group()["legs"] == 2),
    ("standing", lambda b: b.replace(' or z.get("onFloor") is True', ""), lambda: _group()["standing_at"] == [2, 1]),
    # drag_guard
    ("is_shove", lambda b: b.replace(' or (typ == MELEE and args.get("mode") == SHOVE)', ""),
     lambda: _drag()["shoves"] == 1),
    ("e_drag_guard", lambda b: b.replace('g["runs" if typ == STEER else "runs_refused"] += 1',
                                         'g["runs_refused"] += 1 if typ is None else 0'),
     lambda: _drag()["runs_refused"] == 2),
    ("e_drag_guard", lambda b: b.replace('            if typ == STEER:\n                g["clear_steers"]',
                                         '            if True:\n                g["clear_steers"]'),
     lambda: _drag()["clear_steers"] == 1),
    ("rotation", lambda b: b.replace("return next((v[k] for k in ROTATION_KEYS", "return next((None for k in ROTATION_KEYS"),
     lambda: _drag()["rotations"] == [30]),
    ("blocks", lambda b: b.replace("< SIDE_R", "< 99.0"), lambda: _drag()["into_side"] == {"steers": 2, "blocked": 1}),
    ("blocks", lambda b: b.replace("min(max((p[0] - me[0]) * ux + (p[1] - me[1]) * uy, 0.0), SIDE_LOOK)",
                                   "(p[0] - me[0]) * ux + (p[1] - me[1]) * uy"),
     test_a_steer_s_clearance_is_read_over_its_first_side_look_tiles_only),
    # idle_snap
    ("e_idle_snap", lambda b: b.replace('types.get(act.get("aid")) == MELEE and ', ""), lambda: _idle()["frames"] == 3),
    ("e_idle_snap", lambda b: b.replace("and act.get(\"state\") in LIVE_STATES", ""), lambda: _idle()["frames"] == 3),
    ("e_idle_snap", lambda b: b.replace("standing(f, IDLE_SNAP_R)", "standing(f, 99.0)"),
     lambda: _idle()["frames"] == 3),
    ("e_idle_snap", lambda b: b.replace("math.atan2(p[1] - me[1], p[0] - me[0])", "math.atan2(p[0] - me[0], p[1] - me[1])"),
     lambda: _idle()["body_err_median"] == pytest.approx(20.0)),
]


@pytest.mark.parametrize("n", range(len(MUTANTS)), ids=lambda n: "%s-%d" % (MUTANTS[n][0], n))
def test_a_mutant_of_each_reading_fails_its_fixture(n, monkeypatch):
    name, edit, holds = MUTANTS[n]
    assert holds() is not False, "the fixture must hold on the real module"
    monkeypatch.setattr(G, name, _mutated(name, edit)[name])
    try:
        survives = holds() is not False
    except AssertionError:   # a fixture written as a test fails by assertion
        survives = False
    except Exception:        # a mutant that raises on the fixture is caught by it
        survives = False
    assert not survives, "the mutant of %s survives its fixture" % name


# ================================================================ the real checks: F18 and E23
def _path(d, name):
    p = os.path.join(d, name)
    if not os.path.isfile(p):
        pytest.skip("%s is not checked out" % d)
    return p


@functools.lru_cache(maxsize=None)
def _f18():
    p = _path(F18, "f_goals_18.json")
    out, log, goals = EG23.load(p), EG23.load_log(p), FG15.load_goals(p)
    return G.grade_x3(out, log, state_dir=F18, goal_lines=goals), GX2.grade_x2(out, log, state_dir=F18,
                                                                               goal_lines=goals)


def to_x2(g):
    """grade_x3's dict as grade_x2's: the new keys and `base_x2` dropped, the names restored, the new lines dropped."""
    g = dict(g)
    for k in G.NEW:
        g.pop(k)
    g["grade"], g["base"] = g.pop("base"), g.pop("base_x2")
    g["report_lines"] = [("gate_x2 " + ln[len("gate_x3 "):]) if ln.startswith("gate_x3 ") else ln
                         for ln in g["report_lines"][:-G.N_LINES]]
    return g


def test_on_f18_grade_x3_keeps_every_grade_x2_key():
    g, base = _f18()
    assert (g["grade"], g["base"], g["base_x2"], g["base_x1"]) == ("grade_x3", "grade_x2", "grade_x1", "grade_f12")
    assert to_x2(g) == base
    json.dumps(g, allow_nan=False)


def test_on_f18_the_group_readings():
    """F18's leaves predate Task 1 (no head_ticks: read, max None) and its planner Tasks 2 and 3 (no line carries the
    new why keys); five of its seven steers headed within SIDE_R of a standing zombie (the drag-down runs); 141 idle
    frames near a standing zombie, the body's median error 22.1 degrees."""
    g = _f18()[0]
    assert g["head_ticks"] == {"read": True, "leaves": 0, "max": None, "over_cap": 0, "by_melee": []}
    assert (g["crawler_first"]["lines"], g["group_leave"]["lines"], g["drag_guard"]["guard_lines"],
            g["drag_guard"]["clear_lines"]) == (0, 0, 0, 0)
    assert g["drag_guard"]["into_side"] == {"steers": 7, "blocked": 5}
    assert g["idle_snap"]["frames"] == 141
    assert g["idle_snap"]["body_err_median"] == pytest.approx(22.10030221611603)


def _script(name, path):
    r = subprocess.run([sys.executable, os.path.join(TESTING, "agent", "drivers", name), path], capture_output=True,
                       cwd=TESTING)
    assert r.returncode == 0, r.stderr
    return r.stdout.replace(b"\r\n", b"\n")


F18_SHA256 = "c93fa11f0aea1a8a982d2b21a324a93ed0b4ac07443bb12fa8cdd254a9e6dcf5"   # f_grade_15.py's whole stdout on F18 (CRLF folded), pinned at its first run


def test_f_grade_15_on_f18_reproduces_the_committed_f_grade_txt_under_its_new_lines_byte_for_byte():
    """f_grade_15.py on F18: its grade_x2 lines are the committed f_grade.txt's lines byte for byte, its JSON is the
    committed one's with the group keys and the names added, and the whole output's sha256 is pinned (a drift in any
    reading or any live name read through the grade chain fails here)."""
    p = _path(F18, "f_goals_18.json")
    got = _script("f_grade_15.py", p)
    want = open(os.path.join(F18, "f_grade.txt"), "rb").read().replace(b"\r\n", b"\n").decode("utf-8")
    text = got.decode("utf-8")
    i, j = text.index("\n{\n"), want.index("\n{\n")
    lines, wlines = text[:i + 1].splitlines(), want[:j + 1].splitlines()
    assert lines[:-G.N_LINES] == wlines and len(lines) == len(wlines) + G.N_LINES
    assert lines[-G.N_LINES].startswith("head ticks (the finish's head step")
    js, wjs = json.loads(text[i:]), json.loads(want[j:])
    assert to_x2(js) == wjs
    assert hashlib.sha256(got).hexdigest() == F18_SHA256


@functools.lru_cache(maxsize=None)
def _e23():
    p = _path(E23, "e_day_23.json")
    out, log = EG23.load(p), EG23.load_log(p)
    return G.grade_x3(out, log, state_dir=E23, kind="e"), GX2.grade_x2(out, log, state_dir=E23, kind="e")


def test_on_e23_grade_x3_keeps_every_grade_x2_key():
    g, base = _e23()
    assert g["base_x1"] == "grade_e21" and g["base_x2"] == "grade_x1" and to_x2(g) == base


def test_e_grade_24_prints_grade_x2_s_lines_then_the_group_ones_and_the_json():
    p = _path(E23, "e_day_23.json")
    text = _script("e_grade_24.py", p).decode("utf-8")
    i = text.index("\n{\n")
    g, base = _e23()
    printed = text[:i + 1].splitlines()
    assert printed[:-G.N_LINES] == base["report_lines"] and printed[-G.N_LINES:] == g["report_lines"][-G.N_LINES:]
    got = json.loads(text[i:])
    assert (got["grade"], got["base"], got["base_x2"], got["base_x1"]) == ("grade_x3", "grade_x2", "grade_x1",
                                                                          "grade_e21")


def test_the_regrade_scripts_refuse_an_argument_they_do_not_define():
    """Read statically (CLAUDE.md section 5): e_grade_24's main answers usage, exit 2, on no path or more than two
    outside `--chain`; f_grade_15's on anything but one path."""
    e = open(EG24.__file__, encoding="utf-8").read()
    assert "if not paths or (not chain and len(paths) > 2):" in e and "return 2" in e and "usage: e_grade_24.py" in e
    assert "from agent.base.grades.x3 import gate_x3, grade_x3, report_lines_x3" in e and EG24.KIND == "e"
    f = open(FG15.__file__, encoding="utf-8").read()
    assert "if len(argv) != 1:" in f and "usage: f_grade_15.py" in f and FG15.KIND == "f"
    assert EG24.grade_x3 is G.grade_x3 and FG15.grade_x3 is G.grade_x3
