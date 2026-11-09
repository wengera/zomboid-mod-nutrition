"""base/grades/x2.py (Plan 32 Task 4), offline: `grade_x2` and its two facing readings (`facing_body`: the body's error
at every press, by kind and by the leaf's press mode, through the stance ticks with its median, 90th percentile and
hold30, and the breaks over 45 degrees with the action sent before each; `facing_ring`: the forward direction's shares
on the aim vector, the walk vector and the bearing), each on a fabricated ring where it counts, its unread case and a
mutant of each reading that its fixture fails; every grade_x1 key kept under `grade_x2` on the committed F17
(`f_goals_17-20261108-172833`, the baseline) and E23 artifacts, through the function and through the regrade scripts
`f_grade_14.py` and `e_grade_23.py`; F17's regrade pinned byte for byte (its grade_x1 lines and keys equal to the
committed `f_grade.txt`'s, the whole output's sha256, and the facing numbers, the baseline table of
`testing/trials/facing.md`)."""
import functools
import hashlib
import json
import math
import os
import subprocess
import sys

import pytest

from agent.base.grades import x1 as GX1
from agent.base.grades import x2 as G
from agent.drivers import e_grade_23 as EG23
from agent.drivers import f_grade_14 as FG14
from . import test_grades_e14 as T14
from . import test_grades_e20 as T20
from .test_gates_e7 import T0
from .test_grades_e14 import actl

HERE = os.path.dirname(os.path.abspath(__file__))
TESTING = os.path.dirname(os.path.dirname(HERE))
F17 = os.path.join(TESTING, "artifacts", "f_goals_17-20261108-172833")
E23 = os.path.join(TESTING, "artifacts", "e_day_23-20261105-095110")
R = math.radians


# ================================================================ the fabricated ring
def rec(actions=(), wall_s=600.0):
    a = T14.artifact(actions)
    a["stop"]["wallS"] = wall_s
    return a


def act_row(aid, type_, sent_s, **args):
    return {"aid": aid, "type": type_, "args": dict(args), "state": "done", "reason": "", "sentS": sent_s,
            "endedS": sent_s + 1.0, "branch": "threat"}


def zr(zid, x, y, floor=None, head=None):
    z = {"id": zid, "x": x, "y": y, "dist": math.hypot(x - 10.0, y - 10.0), "onFloor": floor, "headX": None,
         "headY": None}
    if head is not None:
        z["headX"], z["headY"] = head
    return z


def fr(t, body, look=None, x=10.0, y=10.0, zs=(), act=None, fwd=None, aim=None):
    """A frame `t` seconds into the loop: the body and look angles (radians; the look the body's unless given), the
    ring's forward and aim angles (None: a PZA/1.10 frame), the position, the zombies and the act."""
    me = {"x": x, "y": y, "bodyAngle": body, "lookAngle": body if look is None else look, "fwdAngle": fwd,
          "aimAngle": aim, "twist": None, "hitReaction": "", "hour": 10.0 + t / 3600.0, "moving": False}
    return {"kind": "frame", "seq": int(round(t * 10)), "wallMs": int(round((T0 + t) * 1000)), "me": me,
            "zombies": [dict(z) for z in zs], "act": act, "body": {"health": 100.0, "parts": []}}


def mel(aid, t, step=None, state="progress", **res):
    r = dict(res)
    if step is not None:
        r["step"] = step
    return actl(aid, "melee", state, t, r)


def leaf(**kw):
    return dict({"d_press": 1.0, "d_collide_pred": 1.0, "d_min": 1.0, "look_off": 0.0, "hp0": 1.0, "hp1": 1.0,
                 "knock": False, "cut_by": ""}, **kw)


def sent(t, type_, **args):
    return {"action": {"type": type_, "args": dict(args)}, "branch": "threat", "gameMin": 600, "inputs": {},
            "sent": True, "wall": T0 + t}


def ordered(*groups):
    return sorted([ln for g in groups for ln in g], key=lambda ln: ln["wallMs"])


Z7 = zr(7, 11.0, 10.0)   # due east of the player: bearing 0


# ---------------------------------------------------------------- a press 10 degrees off
def press_case():
    """A melee m1 at zombie 7 (due east): the press (step swing) at 1.05 s, the frame at 1.0 reading the body 10 and
    the look 5 degrees off, a frame at 1.1 (after the press) 40 off; the leaf on the line at 1.5 names unaimed_snap.
    A second melee m2's shove at 3.05 with a leaf naming no mode, the frame at 3.0 the body 20 off."""
    m1 = {"aid": "m1", "state": "progress", "step": "face"}
    m2 = {"aid": "m2", "state": "progress", "step": "face"}
    frames = [fr(1.0, R(10), R(5), zs=[Z7], act=m1), fr(1.1, R(40), zs=[Z7], act=dict(m1, step="swing")),
              fr(3.0, R(-20), zs=[Z7], act=m2)]
    acts = [mel("m1", 0.5, state="accepted"), mel("m1", 0.8, "face"), mel("m1", 1.05, "swing"),
            mel("m1", 1.5, "face", press=leaf(facing="unaimed_snap", body_off=10.0)),
            mel("m2", 2.5, state="accepted"), mel("m2", 3.05, "shove"), mel("m2", 3.5, "face", press=leaf())]
    out = rec([act_row("m1", "melee", 0.4, targetId=7, mode="strike"),
               act_row("m2", "melee", 2.4, targetId=7, mode="strike")])
    return out, None, ordered(frames, acts)


def test_a_press_reads_the_body_and_the_look_off_the_bearing_at_the_frame_before_it():
    p = G.readings_x2(*press_case())["facing_body"]["presses"]
    rows = p["rows"]
    assert [(r["aid"], r["kind"], r["mode"]) for r in rows] == [("m1", "swing", "unaimed_snap"),
                                                                  ("m2", "shove", G.UNNAMED)]
    assert rows[0]["err_body"] == pytest.approx(10.0) and rows[0]["err_look"] == pytest.approx(5.0)
    assert rows[1]["err_body"] == pytest.approx(-20.0)
    assert p["body"]["n"] == 2 and p["body"]["median"] == pytest.approx(10.0) and p["body"]["p90"] == pytest.approx(20.0)
    assert p["by_kind"]["swing"]["body"]["median"] == pytest.approx(10.0)
    assert p["by_mode"]["unaimed_snap"]["n"] == 1 and p["by_mode"][G.UNNAMED]["n"] == 1


def test_a_press_after_its_own_leaf_line_and_a_heartbeat_are_counted_once_each():
    """A press on the line carrying the previous press's leaf (the meet presses again on the result's tick) is a new
    press; a heartbeat line holding the step is none."""
    m1 = {"aid": "m1", "state": "progress", "step": "swing"}
    frames = [fr(1.0, 0.0, zs=[Z7], act=m1), fr(2.0, R(30), zs=[Z7], act=m1)]
    acts = [mel("m1", 0.5, state="accepted"), mel("m1", 1.05, "swing"), mel("m1", 1.6, "swing"),
            mel("m1", 2.05, "swing", press=leaf()), mel("m1", 2.6, "face", press=leaf(facing="block_aim"))]
    out = rec([act_row("m1", "melee", 0.4, targetId=7)])
    rows = G.readings_x2(out, None, ordered(frames, acts))["facing_body"]["presses"]["rows"]
    assert [(r["wallMs"], r["mode"]) for r in rows] == [(int((T0 + 1.05) * 1000), G.UNNAMED),
                                                        (int((T0 + 2.05) * 1000), "block_aim")]
    assert [round(r["err_body"]) for r in rows] == [0, 30]


def test_a_finish_under_head_aim_reads_the_head_estimate():
    """A stomp at a fallen zombie whose head estimate lies due south of the player: the body facing south reads 0."""
    m1 = {"aid": "m1", "state": "progress", "step": "head"}
    z = zr(7, 11.0, 10.0, floor=True, head=(10.0, 11.0))
    frames = [fr(1.0, R(90), zs=[z], act=m1)]
    acts = [mel("m1", 0.5, state="accepted"), mel("m1", 1.05, "stomp")]
    out = rec([act_row("m1", "melee", 0.4, targetId=7, mode="finish", headAim=True)])
    rows = G.readings_x2(out, None, ordered(frames, acts))["facing_body"]["presses"]["rows"]
    assert rows[0]["err_body"] == pytest.approx(0.0)


# ---------------------------------------------------------------- a stance leg with a break run
def stance_case():
    """An aim leg g1 at zombie 7 (due east) over ten frames, 2.0 to 2.9 s, the body on it but at 2.3, 2.4 and 2.5,
    60 degrees off; the aim sent at 2.2 (the action before the run), a stop at 2.25 not sent, and a steer sent at 2.35
    (inside it)."""
    g1 = {"aid": "g1", "state": "progress", "step": None}
    frames = [fr(2.0 + k / 10.0, R(60) if k in (3, 4, 5) else 0.0, zs=[Z7], act=g1) for k in range(10)]
    acts = [actl("g1", "aim", "accepted", 1.9)]
    rows = [sent(1.0, "walkTo", x=1, y=2), sent(2.2, "aim", targetId=7, vx=-1.0, vy=0.0, seconds=2.0, bearing=-1),
            dict(sent(2.25, "stop"), sent=False), sent(2.35, "steer", vx=1.0, vy=0.0)]
    out = rec([act_row("g1", "aim", 1.85, targetId=7, vx=-1.0, vy=0.0, seconds=2.0)])
    return out, rows, ordered(frames, acts)


def test_a_stance_leg_reads_its_error_series_and_its_break_with_the_action_before_it():
    fb = G.readings_x2(*stance_case())["facing_body"]
    st = fb["stance"]
    assert st["frames"] == 10 and st["read"] == 10
    assert st["body"] == {"n": 10, "median": pytest.approx(0.0), "p90": pytest.approx(60.0), "hold30": 0.7}
    assert set(st["by_type"]) == {"aim"}
    br = fb["breaks"]
    assert br["n"] == 1 and br["frames"] == 3
    r = br["rows"][0]
    assert (r["seq0"], r["seq1"], r["n"], r["type"], r["aid"]) == (23, 25, 3, "aim", "g1")
    assert r["max"] == pytest.approx(60.0)
    assert r["sent"]["type"] == "aim" and r["sent"]["s_before"] == pytest.approx(0.1)
    assert r["sent"]["args"] == {"targetId": 7, "vx": -1.0, "vy": 0.0, "seconds": 2.0, "bearing": -1}


def test_two_break_runs_split_at_a_frame_back_on_the_target():
    out, rows, lines = stance_case()
    lines = [dict(ln, me=dict(ln["me"], bodyAngle=0.0)) if ln.get("kind") == "frame" and ln["seq"] == 24 else ln
             for ln in lines]
    br = G.readings_x2(out, rows, lines)["facing_body"]["breaks"]
    assert [(r["seq0"], r["n"]) for r in br["rows"]] == [(23, 1), (25, 1)]


def test_a_bearing_aim_and_a_frame_outside_any_leg():
    """An aim at a bearing (90: south) reads its error against it; a frame whose act is a walk is no stance tick."""
    g1 = {"aid": "g1", "state": "progress", "step": None}
    frames = [fr(1.0, R(80), act=g1), fr(1.1, R(150), act={"aid": "w1", "state": "progress", "step": None})]
    acts = [actl("g1", "aim", "accepted", 0.9), actl("w1", "walkTo", "accepted", 1.05)]
    out = rec([act_row("g1", "aim", 0.85, vx=0, vy=0, seconds=1.0, targetId=-1, bearing=90)])
    st = G.readings_x2(out, None, ordered(frames, acts))["facing_body"]["stance"]
    assert st["frames"] == 1 and st["body"]["median"] == pytest.approx(10.0)


def test_a_re_pin_moves_the_target_and_an_unlisted_target_falls_back_to_the_nearest_standing():
    """The melee's line carrying target 8 re-pins the frames after it to zombie 8 (due south); a target the frame
    does not list reads the nearest standing zombie within FACING_R."""
    m1 = {"aid": "m1", "state": "progress", "step": "face"}
    z8 = zr(8, 10.0, 11.0)
    frames = [fr(1.0, 0.0, zs=[Z7, z8], act=m1), fr(2.0, R(90), zs=[Z7, z8], act=m1),
              fr(3.0, R(90), zs=[z8], act=dict(m1, aid="m2"))]
    acts = [mel("m1", 0.5, state="accepted"), mel("m1", 1.5, "repin", target=8, repins=1),
            mel("m2", 2.5, state="accepted")]
    out = rec([act_row("m1", "melee", 0.4, targetId=7), act_row("m2", "melee", 2.4, targetId=99)])
    st = G.readings_x2(out, None, ordered(frames, acts))["facing_body"]["stance"]
    assert st["body"] == {"n": 3, "median": pytest.approx(0.0), "p90": pytest.approx(0.0), "hold30": 1.0}


def test_a_log_with_no_body_angle_reads_unread():
    out, rows, lines = stance_case()
    lines = [dict(ln, me=dict(ln["me"], bodyAngle=None)) if ln.get("kind") == "frame" else ln for ln in lines]
    assert G.readings_x2(out, rows, lines)["facing_body"] == {"read": False}


def test_the_readings_read_the_sources_clipped_at_the_stop():
    out, rows, lines = stance_case()
    out["stop"]["wallS"] = 2.35 + (out["loop"]["startPyMs"] / 1000.0 - T0)
    st = G.readings_x2(out, rows, lines)["facing_body"]["stance"]
    assert st["frames"] == 4


# ---------------------------------------------------------------- the ring
def ring_case():
    """Four stance frames of a PZA/1.11 log (the forward direction read): on the aim vector at 1.0 and 1.1 (the mouse
    won, 90 off the target), on the bearing at 1.2 (the aim beside it) and 1.3 (the aim 100 degrees off); the player moving east 0.1 a frame at 1.1 and 1.2 (the
    walk vector 0, on the bearing) and standing at 1.3 (no walk vector)."""
    m1 = {"aid": "m1", "state": "progress", "step": "face"}
    frames = [fr(1.0, R(90), zs=[Z7], act=m1, fwd=R(90), aim=R(92)),
              fr(1.1, R(90), x=10.1, zs=[Z7], act=m1, fwd=R(90), aim=R(95)),
              fr(1.2, 0.0, x=10.2, zs=[Z7], act=m1, fwd=R(3), aim=R(5)),
              fr(1.3, 0.0, x=10.2, zs=[Z7], act=m1, fwd=R(-2), aim=R(100))]
    acts = [mel("m1", 0.5, state="accepted")]
    return rec([act_row("m1", "melee", 0.4, targetId=7)]), None, ordered(frames, acts)


def test_the_ring_reads_which_writer_won():
    r = G.readings_x2(*ring_case())["facing_ring"]
    assert r["read"] is True and r["frames"] == 4
    assert (r["aim"], r["aim_n"]) == (pytest.approx(0.75), 4)
    assert (r["walk"], r["walk_n"]) == (pytest.approx(0.5), 2)
    assert (r["bearing"], r["bearing_n"]) == (pytest.approx(0.5), 4)


def test_a_log_without_the_ring_reads_null_shares():
    r = G.readings_x2(*stance_case())["facing_ring"]
    assert r == {"read": False, "frames": 0, "aim": None, "walk": None, "bearing": None}


def test_the_summary_is_nearest_rank_over_absolute_errors():
    s = G.summary([-50.0, 1.0, 2.0, None, 40.0, -3.0])
    assert s == {"n": 5, "median": 3.0, "p90": 50.0, "hold30": 0.6}
    assert G.summary([None]) == {"n": 0}
    assert G.wrap_deg(R(190)) == pytest.approx(-170.0) and G.wrap_deg(R(-180)) == pytest.approx(180.0)


# ================================================================ the module's frozen copies
def test_the_module_imports_no_live_planner_world_or_tools_name_and_holds_its_own_copies():
    names = T20._imports(G.__file__)
    assert not any(m.startswith(("agent.base.planner", "agent.base.world", "tools", "trial_score")) for m in names)
    ns = vars(G)
    assert ns["PRESS_STEPS"] == ("swing", "shove", "stomp", "floor") and ns["FINISH_KINDS"] == ("floor", "stomp")
    assert (ns["MELEE"], ns["AIM"], ns["FACING_KEY"], ns["TARGET"]) == ("melee", "aim", "facing", "target")
    assert ns["LIVE_STATES"] == ("accepted", "progress")
    assert (ns["FACING_R"], ns["HOLD_DEG"], ns["BREAK_DEG"], ns["RING_DEG"], ns["MOVE_EPS"]) == (
        1.5, 30.0, 45.0, 10.0, 0.02)
    assert ns["NEW"] == ("facing_body", "facing_ring")


# ================================================================ the mutants
def _mutated(name, edit):
    """grades/x2.py's source with `edit` applied inside the top-level def `name` only, executed as a module copy."""
    src = open(G.__file__, encoding="utf-8").read()
    head = "\ndef %s(" % name
    start = src.index(head)
    nxt = [i for i in (src.find("\ndef ", start + 5), src.find("\nclass ", start + 5)) if i >= 0]
    end = min(nxt) if nxt else len(src)
    new = edit(src[start:end])
    assert new != src[start:end], (name, "the mutant changed nothing")
    ns = {"__name__": "x2_mutant"}
    exec(compile(src[:start] + new + src[end:], "x2_mutant", "exec"), ns)    # noqa: S102 - a scratch copy
    return ns


def _presses():
    return G.readings_x2(*press_case())["facing_body"]["presses"]


def _stance():
    return G.readings_x2(*stance_case())["facing_body"]


def _ring():
    return G.readings_x2(*ring_case())["facing_ring"]


MUTANTS = [
    ("wrap_deg", lambda b: b.replace("while d > 180.0:", "while d > 1000.0:"),
     lambda: G.wrap_deg(R(190)) == pytest.approx(-170.0)),
    ("_rank", lambda b: b.replace("math.ceil(q * len(s))", "int(q * len(s))"),
     lambda: G.summary([-50.0, 1.0, 2.0, 40.0, -3.0])["median"] == 3.0),
    ("summary", lambda b: b.replace("[abs(x) for x in errs", "[x for x in errs"),
     lambda: G.summary([-50.0, 1.0, 2.0, 40.0, -3.0])["p90"] == 50.0),
    ("summary", lambda b: b.replace("if x < HOLD_DEG", "if x <= 90"),
     lambda: _stance()["stance"]["body"]["hold30"] == 0.7),
    ("press_rows", lambda b: b.replace("bisect.bisect_right(index[0], w) - 1", "bisect.bisect_right(index[0], w)"),
     lambda: _presses()["rows"][0]["err_body"] == pytest.approx(10.0)),
    ("press_rows", lambda b: b.replace(" or isinstance(res.get(\"press\"), dict))", ")"),
     lambda: len(G.readings_x2(rec([act_row("m1", "melee", 0.4, targetId=7)]), None, ordered(
         [fr(1.0, 0.0, zs=[Z7], act={"aid": "m1", "state": "progress", "step": "swing"})],
         [mel("m1", 0.5, state="accepted"), mel("m1", 1.05, "swing"), mel("m1", 2.05, "swing", press=leaf())]))[
         "facing_body"]["presses"]["rows"]) == 2),
    ("press_rows", lambda b: b.replace("for x in lns[k + 1:]", "for x in lns[:k]"),
     lambda: _presses()["rows"][0]["mode"] == "unaimed_snap"),
    ("press_rows", lambda b: b.replace('"err_look": _err(f, "lookAngle", b)', '"err_look": _err(f, "bodyAngle", b)'),
     lambda: _presses()["rows"][0]["err_look"] == pytest.approx(5.0)),
    ("bearing", lambda b: b.replace("math.atan2(p[1] - me[1], p[0] - me[0])", "math.atan2(p[0] - me[0], p[1] - me[1])"),
     lambda: _presses()["rows"][0]["err_body"] == pytest.approx(10.0)),
    ("bearing", lambda b: b.replace("return math.radians(b)", "return b"),
     lambda: G.readings_x2(rec([act_row("g1", "aim", 0.85, targetId=-1, bearing=90)]), None, ordered(
         [fr(1.0, R(80), act={"aid": "g1", "state": "progress", "step": None})],
         [actl("g1", "aim", "accepted", 0.9)]))["facing_body"]["stance"]["body"]["median"] == pytest.approx(10.0)),
    ("bearing", lambda b: b.replace("if head and", "if False and"),
     test_a_finish_under_head_aim_reads_the_head_estimate),
    ("_nearest", lambda b: b.replace("d <= FACING_R and", ""),
     lambda: G.readings_x2(rec([act_row("m2", "melee", 2.4, targetId=99)]), None, ordered(
         [fr(3.0, 0.0, zs=[zr(8, 13.0, 10.0)], act={"aid": "m2", "state": "progress", "step": "face"})],
         [mel("m2", 2.5, state="accepted")]))["facing_body"]["stance"]["body"] == {"n": 0}),
    ("_target_id", lambda b: b.replace("if i >= 0:", "if False:"),
     test_a_re_pin_moves_the_target_and_an_unlisted_target_falls_back_to_the_nearest_standing),
    ("stance_frames", lambda b: b.replace("or act.get(\"state\") not in LIVE_STATES", ""),
     lambda: G.readings_x2(rec([act_row("g1", "aim", 0.85, targetId=7)]), None, ordered(
         [fr(1.0, 0.0, zs=[Z7], act={"aid": "g1", "state": "progress"}),
          fr(1.1, 0.0, zs=[Z7], act={"aid": "g1", "state": "done"})],
         [actl("g1", "aim", "accepted", 0.9)]))["facing_body"]["stance"]["frames"] == 1),
    ("stance_frames", lambda b: b.replace("if typ not in (AIM, MELEE)", "if typ is None"),
     test_a_bearing_aim_and_a_frame_outside_any_leg),
    ("breaks", lambda b: b.replace("abs(e) > BREAK_DEG and (not cur", "abs(e) > 90 and (not cur"),
     lambda: _stance()["breaks"]["n"] == 1),
    ("breaks", lambda b: b.replace("cur[-1][0] == i - 1", "True"),
     lambda: [r["n"] for r in G.readings_x2(*_gap_case())["facing_body"]["breaks"]["rows"]] == [1, 1]),
    ("_sent_before", lambda b: b.replace("w * 1000.0 <= wall_ms", "True"),
     lambda: _stance()["breaks"]["rows"][0]["sent"]["type"] == "aim"),
    ("_sent_before", lambda b: b.replace('r.get("sent") is True and ', ""),
     lambda: _stance()["breaks"]["rows"][0]["sent"]["s_before"] == pytest.approx(0.1)),
    ("e_facing_ring", lambda b: b.replace("aim += _on(fwd, a)", "aim += 1"), lambda: _ring()["aim"] == pytest.approx(0.75)),
    ("e_facing_ring", lambda b: b.replace("> MOVE_EPS", "> -1"), lambda: _ring()["walk_n"] == 2),
    ("e_facing_ring", lambda b: b.replace("bear += _on(fwd, b)", "bear += _on(fwd, a)"),
     lambda: _ring()["bearing"] == pytest.approx(0.5)),
    ("_on", lambda b: b.replace("abs(wrap_deg(a - v))", "abs(a - v)"),
     lambda: G._on(R(179), R(-179)) is True and G._on(0.0, R(90)) is False),
]


def _gap_case():
    """Two stance frames over 45 degrees with a walk's frame between them: two runs, not one."""
    g1 = {"aid": "g1", "state": "progress", "step": None}
    frames = [fr(2.0, R(60), zs=[Z7], act=g1), fr(2.1, R(60), zs=[Z7], act={"aid": "w1", "state": "progress"}),
              fr(2.2, R(60), zs=[Z7], act=g1)]
    acts = [actl("g1", "aim", "accepted", 1.9), actl("w1", "walkTo", "accepted", 2.05)]
    return rec([act_row("g1", "aim", 1.85, targetId=7)]), None, ordered(frames, acts)


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


# ================================================================ the real checks: F17 (the baseline) and E23
def _path(d, name):
    p = os.path.join(d, name)
    if not os.path.isfile(p):
        pytest.skip("%s is not checked out" % d)
    return p


@functools.lru_cache(maxsize=None)
def _f17():
    p = _path(F17, "f_goals_17.json")
    out, log, goals = EG23.load(p), EG23.load_log(p), FG14.load_goals(p)
    return G.grade_x2(out, log, state_dir=F17, goal_lines=goals), GX1.grade_x1(out, log, state_dir=F17,
                                                                               goal_lines=goals)


def to_x1(g):
    """grade_x2's dict as grade_x1's: the new keys and `base_x1` dropped, the names restored, the new lines dropped."""
    g = dict(g)
    for k in G.NEW:
        g.pop(k)
    g["grade"], g["base"] = g.pop("base"), g.pop("base_x1")
    g["report_lines"] = [("gate_x1 " + ln[len("gate_x2 "):]) if ln.startswith("gate_x2 ") else ln
                         for ln in g["report_lines"][:-G.N_LINES]]
    return g


def test_on_f17_grade_x2_keeps_every_grade_x1_key():
    g, base = _f17()
    assert g["grade"] == "grade_x2" and g["base"] == "grade_x1" and g["base_x1"] == "grade_f12"
    assert to_x1(g) == base
    json.dumps(g, allow_nan=False)


# The baseline (F17, grade_x2): testing/trials/facing.md's `## Baseline (F17, grade_x2)` table, pinned here.
F17_PRESSES = {"n": 82, "median": 0.3455538002065168, "p90": 22.074432922861945, "hold30": 0.9024390243902439}
F17_STANCE = {"n": 1582, "median": 15.869722123128636, "p90": 135.62161536197556, "hold30": 0.5474083438685209}


def test_on_f17_the_facing_readings_are_the_baseline():
    fb, ring = _f17()[0]["facing_body"], _f17()[0]["facing_ring"]
    assert fb["presses"]["body"] == pytest.approx(F17_PRESSES)
    assert {k: v["n"] for k, v in fb["presses"]["by_kind"].items()} == {"floor": 1, "shove": 28, "stomp": 39,
                                                                        "swing": 14}
    assert set(fb["presses"]["by_mode"]) == {G.UNNAMED}
    assert fb["stance"]["body"] == pytest.approx(F17_STANCE)
    assert {k: v["n"] for k, v in fb["stance"]["by_type"].items()} == {"aim": 764, "melee": 818}
    assert (fb["breaks"]["n"], fb["breaks"]["frames"]) == (45, 615)
    assert ring == {"read": False, "frames": 0, "aim": None, "walk": None, "bearing": None}   # a PZA/1.10 log


def _script(name, path):
    r = subprocess.run([sys.executable, os.path.join(TESTING, "agent", "drivers", name), path], capture_output=True,
                       cwd=TESTING)
    assert r.returncode == 0, r.stderr
    return r.stdout.replace(b"\r\n", b"\n")


F17_SHA256 = "77a3a7f39c471dddcabec81047547fc7ef52acfdf660352d98ab374d334fdf8a"   # f_grade_14.py's whole stdout on F17 (CRLF folded), at its first run


def test_f_grade_14_on_f17_reproduces_the_committed_f_grade_txt_under_its_new_lines_byte_for_byte():
    """f_grade_14.py on F17: its grade_x1 lines are the committed f_grade.txt's lines byte for byte, its JSON is the
    committed one's with the facing keys and the names added, and the whole output's sha256 is pinned (a drift in any
    reading or any live name read through the grade chain fails here)."""
    p = _path(F17, "f_goals_17.json")
    got = _script("f_grade_14.py", p)
    want = open(os.path.join(F17, "f_grade.txt"), "rb").read().replace(b"\r\n", b"\n").decode("utf-8")
    text = got.decode("utf-8")
    i, j = text.index("\n{\n"), want.index("\n{\n")
    lines, wlines = text[:i + 1].splitlines(), want[:j + 1].splitlines()
    assert lines[:-G.N_LINES] == wlines and len(lines) == len(wlines) + G.N_LINES
    assert lines[-G.N_LINES].startswith("facing body (me.bodyAngle against the bearing")
    js, wjs = json.loads(text[i:]), json.loads(want[j:])
    assert to_x1(dict(js, report_lines=js["report_lines"])) == wjs
    assert hashlib.sha256(got).hexdigest() == F17_SHA256


@functools.lru_cache(maxsize=None)
def _e23():
    p = _path(E23, "e_day_23.json")
    out, log = EG23.load(p), EG23.load_log(p)
    return G.grade_x2(out, log, state_dir=E23, kind="e"), GX1.grade_x1(out, log, state_dir=E23, kind="e")


def test_on_e23_grade_x2_keeps_every_grade_x1_key():
    g, base = _e23()
    assert g["base_x1"] == "grade_e21" and to_x1(g) == base


def test_e_grade_23_prints_grade_x1_s_lines_then_the_facing_ones_and_the_json():
    p = _path(E23, "e_day_23.json")
    text = _script("e_grade_23.py", p).decode("utf-8")
    i = text.index("\n{\n")
    g, base = _e23()
    printed = text[:i + 1].splitlines()
    assert printed[:-G.N_LINES] == base["report_lines"] and printed[-G.N_LINES:] == g["report_lines"][-G.N_LINES:]
    got = json.loads(text[i:])
    assert got["grade"] == "grade_x2" and got["base"] == "grade_x1" and got["base_x1"] == "grade_e21"


def test_the_regrade_scripts_refuse_an_argument_they_do_not_define():
    """Read statically (CLAUDE.md section 5): e_grade_23's main answers usage, exit 2, on no path or more than two
    outside `--chain`; f_grade_14's on anything but one path."""
    e = open(EG23.__file__, encoding="utf-8").read()
    assert "if not paths or (not chain and len(paths) > 2):" in e and "return 2" in e and "usage: e_grade_23.py" in e
    assert "from agent.base.grades.x2 import gate_x2, grade_x2, report_lines_x2" in e and EG23.KIND == "e"
    f = open(FG14.__file__, encoding="utf-8").read()
    assert "if len(argv) != 1:" in f and "usage: f_grade_14.py" in f and FG14.KIND == "f"
    assert EG23.grade_x2 is G.grade_x2 and FG14.grade_x2 is G.grade_x2
