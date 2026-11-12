"""base/grades/x6.py (Plan 36 Task 5c), offline: `grade_x6` and its engagement readings (`cadence`: the press leaves on
the moving back step and in the air, the done lines' counts and the presses per retreat; `steps`: the work leaf's step,
shove and re-pin reasons as runs, the NaN headings and x5's pile; `engage_pull`: the pull by why with its held lines,
its room clamp and its episodes' first spreads; `cone_bites`: the onsets from outside the front half; `clock`: the
clock's allowed, held and cut lines by action, the starts under the need, the cares cut by a steer and the timed
actions' durations; `crawler`: a crawler within a tile while pressing at a standing target; `room`: the ring's frames,
stops and cost and the ring closed at each bite; `rip_ride`: the rips sent riding against standing by their ends),
each on a fabricated ring where it counts, its unread case and a mutant of each reading its fixture fails (each mutant
named in the MUTANTS list's comment); every grade_x5 key kept under `grade_x6` on the committed F21
(`f_goals_21-20261111-150552`, Plan 35's evidence session, graded through grade_x5) and F20, through the function and
through the regrade script `f_grade_18.py`, whose grade_x5 part reproduces F21's committed `f_grade.txt` byte for byte.

F21 and F20 ran before the Plan 36 keys (PZA/1.14's room, PZA/1.15's moving_back and air, the pull, the clock): their
cadence, engage_pull, clock and room read unread. Their cone bites, steps, crawler and rip ride read keys older than
Plan 36 (`me.bodyAngle`, Plan 35's `step_for`, the zombie's `crawler`, the rip), so those readings are pinned at what
the sessions carry (F21: no bite outside the cone over 7 onsets, step_for gap 9 retreat 6 pile 1, no crawler frame, 7
standing rips all superseded)."""
import functools
import hashlib
import json
import os
import subprocess
import sys

import pytest

from agent.base.grades import x5 as GX5
from agent.base.grades import x6 as G
from agent.drivers import e_grade_23 as EG23
from agent.drivers import f_grade_15 as FG15
from . import test_grades_e20 as T20
from .test_gates_e7 import T0
from .test_grades_e14 import actl
from .test_grades_x2 import fr, leaf, ordered, rec, zr
from .test_grades_x4 import dline

HERE = os.path.dirname(os.path.abspath(__file__))
TESTING = os.path.dirname(os.path.dirname(HERE))
F20 = os.path.join(TESTING, "artifacts", "f_goals_20-20261109-155512")
F21 = os.path.join(TESTING, "artifacts", "f_goals_21-20261111-150552")


def _ts():
    sys.path.insert(0, os.path.join(os.path.dirname(TESTING), "tools"))
    import trial_score as TS
    return TS


def mel(aid, t, state="progress", step=None, work=None, press=None, reason="", **res):
    """A melee act line `t` seconds in: its step, its `work` leaf and press leaf when given."""
    r = dict(res)
    if step is not None:
        r["step"] = step
    if work is not None:
        r["work"] = dict(work)
    if press is not None:
        r["press"] = press
    return actl(aid, "melee", state, t, r, reason)


def pl(d, **kw):
    """A press leaf launched at `d` tiles (the leaf's key: d_press, hp0, d_collide_pred)."""
    return leaf(d_press=d, d_collide_pred=d, **kw)


# ================================================================ cadence
def cadence_case():
    """m1: leaf A (not back, not air) before any retreat; a retreat run (two lines) carrying leaf B (back, air) re-read on
    the heartbeat line after it with a moved hp1; the line after the run (no retreat) carrying leaf C (back, air at
    launch: the scorecard's window, it belongs to the run); a plain line; a second retreat run carrying leaf D (not
    back); done with back_presses 2, air_presses 1, swings 4. m2: leaf E (back, no retreat) and a failed superseded line
    with back_presses 9 (a failed line's counts are not read). m3: a pre-1.15 leaf F carrying neither key (a press, in
    no share's denominator)."""
    r = {"retreat": True}
    acts = [mel("m1", 1.0, "accepted"), mel("m1", 1.1, step="face", press=pl(1.0, moving_back=False, air=False,
                                                                           air_launch=False)),
            mel("m1", 1.2, step="work", work=r),
            mel("m1", 1.3, step="swing", work=r, press=pl(1.1, moving_back=True, air=True, air_launch=False)),
            mel("m1", 1.4, step="work", work=r, press=pl(1.1, moving_back=True, air=True, air_launch=False, hp1=0.5)),
            mel("m1", 1.5, step="face", press=pl(1.2, moving_back=True, air=False, air_launch=True)),
            mel("m1", 1.6, step="face"), mel("m1", 1.7, step="work", work=r),
            mel("m1", 1.8, step="swing", work=r, press=pl(1.3, moving_back=False, air=False, air_launch=False)),
            mel("m1", 1.9, "done", end="kill", back_presses=2, air_presses=1, swings=4),
            mel("m2", 2.0, "accepted"), mel("m2", 2.1, step="swing", press=pl(1.4, moving_back=True, air=False,
                                                                             air_launch=False)),
            mel("m2", 2.2, "failed", reason="superseded", back_presses=9, air_presses=9, swings=9),
            mel("m3", 3.0, "accepted"), mel("m3", 3.1, step="swing", press=pl(1.5)),
            mel("m3", 3.2, "done", end="kill", swings=1)]
    return rec(), None, ordered(acts)


CADENCE_WANT = {"read": True, "presses": 6, "moving_back": {"n": 3, "of": 5, "share": 0.6},
                "air": {"n": 1, "of": 5, "share": 0.2}, "air_launch": {"n": 1, "of": 5, "share": 0.2},
                "done": {"back_presses": 2, "air_presses": 1, "swings": 5},
                "retreats": [{"aid": "m1", "presses": 2, "back": 2}, {"aid": "m1", "presses": 1, "back": 0}]}


def _cadence():
    return G.readings_x6(*cadence_case())["cadence"]


def test_cadence_reads_the_presses_on_the_moving_back_step_and_in_the_air():
    assert _cadence() == CADENCE_WANT


def test_cadence_is_unread_on_a_run_before_pza1_15_and_agrees_with_the_scorecard():
    """A leaf with neither key (PZA/1.14 and before) reads unread; the scorecard's live `press_readings` (the copy's
    source) reads the same shares and the same retreat window on the fixture."""
    acts = [mel("m1", 1.0, "accepted"), mel("m1", 1.1, step="swing", press=pl(1.0)), mel("m1", 1.2, "done")]
    assert G.readings_x6(rec(), None, acts)["cadence"] == {"read": False}
    TS = _ts()
    live = TS.press_readings(cadence_case()[2])
    c = _cadence()
    assert (live["back"], live["back_leaves"], live["air"], live["leaves"]) == (
        c["moving_back"]["n"], c["moving_back"]["of"], c["air"]["n"], c["air"]["of"])
    assert (live["retreat_back"], live["retreat_leaves"]) == (sum(r["back"] for r in c["retreats"]),
                                                             sum(r["presses"] for r in c["retreats"]))


# ================================================================ steps
def steps_case():
    """m1's work leaves: step_for gap twice (one run), retreat, gap (a new run), none, gap (a new run after the gap in
    it), Plan 35's crawler (kept after the listed values), shove_for knockdown on two lines (one run), repin_for
    attacker, nan_heading on two lines, m1 ending on gap with no end line. m2 (no accepted line): step_for gap first (a
    new melee: a new run though m1 ended on gap), then two pile progress lines carrying step_for pile (one run; x5's
    pile one episode, one shove)."""
    acts = [mel("m1", 1.0, "accepted"), mel("m1", 1.1, step="work", work={"step_for": "gap"}),
            mel("m1", 1.2, step="work", work={"step_for": "gap"}), mel("m1", 1.3, step="work", work={"step_for": "retreat"}),
            mel("m1", 1.4, step="work", work={"step_for": "gap", "nan_heading": True}),
            mel("m1", 1.5, step="face", work={}), mel("m1", 1.6, step="work", work={"step_for": "gap"}),
            mel("m1", 1.7, step="work", work={"step_for": "crawler", "shove_for": "knockdown"}),
            mel("m1", 1.8, step="work", work={"step_for": "gap", "shove_for": "knockdown", "nan_heading": True}),
            mel("m1", 1.9, step="work", work={"repin_for": "attacker", "step_for": "gap"}),
            mel("m2", 3.1, step="work", work={"step_for": "gap"}),
            mel("m2", 3.2, step="pile", work={"step_for": "pile"}), mel("m2", 3.3, step="pile", work={"step_for": "pile"}),
            mel("m2", 3.4, "done", end="kill")]
    return rec(), None, ordered(acts)


STEPS_WANT = {"read": True,
              "step_for": {"gap": 5, "retreat": 1, "pile": 1, "pile_out": 0, "stagger_in": 0, "crawler_buffer": 0,
                           "crawler": 1},
              "shove_for": {"knockdown": 1}, "repin_for": {"stall": 0, "attacker": 1}, "nan_heading": 2,
              "pile": {"episodes": 1, "shoves": 1, "knockdowns": 0}}


def _steps():
    return G.readings_x6(*steps_case())["steps"]


def test_steps_read_the_work_leaf_s_reasons_as_runs():
    assert _steps() == STEPS_WANT


def test_steps_are_unread_without_a_reason_and_agree_with_the_scorecard():
    acts = [mel("m1", 1.0, "accepted"), mel("m1", 1.1, step="work", work={"heading": 0.0}), mel("m1", 1.2, "done")]
    assert G.readings_x6(rec(), None, acts)["steps"] == {"read": False}
    live = _ts().step_reasons(steps_case()[2])
    s = _steps()
    assert {k: {v: n for v, n in s[k].items() if n} for k in G.STEP_KEYS} == live["by"]
    assert live["nan_heading"] == s["nan_heading"]


# ================================================================ engage_pull
def pull(why, spread, **kw):
    return {"engage_pull": dict({"why": why, "spread": spread, "n": 2, "heading": 180.0}, **kw)}


def pull_case():
    """Spread at 80 then 70 (one episode), a line with none, spread at 50 (a second episode); retreat at 90, then held
    with room closed, then clamped {from 200}; cone at 120 (one episode)."""
    rows = [dline(1.0, pull("spread", 80.0)), dline(1.5, pull("spread", 70.0)), dline(2.0, {}),
            dline(2.5, pull("spread", 50.0)), dline(3.0, pull("retreat", 90.0)),
            dline(3.5, pull("retreat", 95.0, held=True, room="closed")),
            dline(4.0, pull("retreat", 99.0, room={"from": 200.0})), dline(4.5, pull("cone", 120.0, flank=2))]
    return rec(), rows, []


PULL_WANT = {"read": True, "lines": 7, "spread_first_median": 85.0, "by": {
    "spread": {"lines": 3, "held": 0, "closed": 0, "clamped": 0, "episodes": 2, "spread_first_median": 65.0},
    "retreat": {"lines": 3, "held": 1, "closed": 1, "clamped": 1, "episodes": 1, "spread_first_median": 90.0},
    "cone": {"lines": 1, "held": 0, "closed": 0, "clamped": 0, "episodes": 1, "spread_first_median": 120.0}}}


def _pull():
    return G.readings_x6(*pull_case())["engage_pull"]


def test_engage_pull_reads_the_pull_by_why_its_room_and_its_episodes():
    assert _pull() == PULL_WANT


def test_engage_pull_is_unread_without_a_log_or_a_pull_and_agrees_with_the_scorecard():
    assert G.readings_x6(rec(), None, [])["engage_pull"] == {"read": False}
    assert G.readings_x6(rec(), [dline(1.0, {})], [])["engage_pull"] == {"read": False}
    live = _ts().pull_counts(pull_case()[1])
    assert live["by"] == {k: v["lines"] for k, v in _pull()["by"].items()}
    assert live["held"] == {k: v["held"] for k, v in _pull()["by"].items() if v["held"]}


# ================================================================ cone_bites
def bite(t, reaction, zs, body=0.0):
    f = fr(t, body, zs=zs)
    f["me"]["hitReaction"] = reaction
    return f


def crawler_z(zid, x, y):
    z = zr(zid, x, y)
    z["crawler"] = True
    return z


def cone_case():
    """The body faces +x (0). Onsets: 1.1 a zombie due north (exactly 90 degrees off: inside), 1.3 one due west (180:
    outside), 1.5 a standing one east beside a nearer crawler west (the standing one read: inside), 1.7 a type change
    inside the run (CrawlerBite after Bite: an onset) with one standing west (outside), 1.9 a bite with nobody listed
    (not read)."""
    fs = [bite(1.0, "", [zr(7, 11.0, 10.0)]), bite(1.1, "Bite", [zr(7, 10.0, 11.0)]), bite(1.2, "", []),
          bite(1.3, "Bite", [zr(7, 9.0, 10.0)]), bite(1.4, "", []),
          bite(1.5, "Bite", [zr(7, 11.0, 10.0), crawler_z(8, 9.5, 10.0)]),
          bite(1.6, "Bite", [zr(7, 11.0, 10.0)]), bite(1.7, "CrawlerBite", [zr(7, 9.0, 10.0)]),
          bite(1.8, "", []), bite(1.9, "Bite", []), bite(2.0, "", [])]
    return rec(), None, ordered(fs)


def _cone():
    return G.readings_x6(*cone_case())["cone_bites"]


def test_cone_bites_read_the_onsets_from_outside_the_front_half():
    c = _cone()
    assert (c["read"], c["bites"], c["outside"]) == (True, 4, 2)
    assert [(r["seq"], round(r["angle"], 6), r["outside"]) for r in c["rows"]] == [
        (11, -90.0, False), (13, 180.0, True), (15, 0.0, False), (17, 180.0, True)]


def test_cone_bites_are_unread_without_a_body_angle_and_agree_with_the_scorecard():
    f = bite(1.0, "Bite", [zr(7, 9.0, 10.0)])
    f["me"]["bodyAngle"] = None
    assert G.readings_x6(rec(), None, [f])["cone_bites"] == {"read": False}
    live = _ts().cone_bites(cone_case()[2])
    assert (live["bites"], live["outside"]) == (_cone()["bites"], _cone()["outside"])


# ================================================================ clock
def ck(action, ttc, need, **kw):
    return {"clock": dict({"action": action, "ttc": ttc, "need": need}, **kw)}


def gl(t, why, type_=None, sent=True, branch="threat", **args):
    """A decision line whose why sits on `branch`."""
    r = dline(t, {}, type_, sent=sent, **args)
    r["inputs"]["branches"] = {branch: dict(why)}
    return r


def act(aid, type_, t, state, reason="", **res):
    return actl(aid, type_, state, t, res, reason)


def clock_case():
    """Clocks: a loot allowed (ttc 5 need 3), a rip allowed at ttc equal to need (not under), a running loot held, a loot
    cut (the aim the cut's), a bandage held waiting 1.5 s. The acts: the loot a1 superseded by the cut's aim; the rip a2
    superseded by a steer (a care cut by a steer); a door a3 done in 0.1 s; an unwear a4 accepted 0.05 s after its send,
    done 1.0 s later; a scan a5 with no accepted line done 0.03 s after its send; a door a6 superseded by a steer (no
    care: not counted)."""
    rows = [gl(1.0, ck("loot", 5.0, 3.0), "interact", branch="goal", kind="loot", x=1, y=1),
            gl(2.0, ck("rip", 3.0, 3.0), "rip", branch="care", itemId=5),
            gl(3.0, ck("loot", 2.0, 3.0, running="a1"), sent=False),
            gl(4.0, ck("loot", 1.0, 3.0, running="a1", cut=True, target=7), "aim", targetId=7),
            gl(5.0, ck("bandage", 2.0, 6.0, waited=1.5), sent=False, branch="care"),
            gl(6.0, {}, "steer", vx=1.0, vy=0.0), gl(7.0, {}, "interact", kind="open", x=2, y=2),
            gl(8.0, {}, "unwear", itemId=6), gl(10.0, {}, "scan"), gl(11.0, {}, "interact", kind="open", x=3, y=3),
            gl(12.0, {}, "steer", vx=0.0, vy=1.0)]
    acts = [act("a1", "interact", 1.05, "accepted"), act("a1", "interact", 4.05, "failed", "superseded"),
            act("a2", "rip", 2.05, "accepted"), act("a2", "rip", 6.05, "failed", "superseded"),
            act("a3", "interact", 7.05, "accepted"), act("a3", "interact", 7.15, "done"),
            act("a4", "unwear", 8.05, "accepted"), act("a4", "unwear", 9.05, "done"),
            act("a5", "scan", 10.03, "done"),
            act("a6", "interact", 11.05, "accepted"), act("a6", "interact", 12.05, "failed", "superseded")]
    return rec(), rows, ordered(acts)


def _clock():
    return G.readings_x6(*clock_case())["clock"]


def test_clock_reads_its_lines_by_action_the_steer_cuts_and_the_durations():
    c = _clock()
    durs = c.pop("durations")
    assert c == {"read": True, "lines": 5, "allowed": 2, "held": 2, "cut": 1, "waited": 1.5, "starts": 2,
                 "rides": 0, "under": 0,
                 "under_lines": [], "steer_cuts": 1, "superseded_by": {"aim": 1, "steer": 1},
                 "by_action": {"loot": {"allowed": 1, "held": 1, "cut": 1}, "rip": {"allowed": 1, "held": 0, "cut": 0},
                               "bandage": {"allowed": 0, "held": 1, "cut": 0}}}
    assert list(durs) == ["unwear", "door", "scan"] and [durs[k]["n"] for k in durs] == [1, 1, 1]
    assert durs["unwear"]["median"] == pytest.approx(1.0) and durs["scan"]["median"] == pytest.approx(0.03)
    assert durs["door"] == {"n": 1, "median": pytest.approx(0.1)}


def test_clock_reads_an_allowed_start_under_the_need():
    rows = [gl(1.0, ck("loot", 2.9, 3.0), "interact", branch="goal", kind="loot")]
    c = G.readings_x6(rec(), rows, [])["clock"]
    assert (c["under"], c["under_lines"]) == (1, [0])


def under_case():
    """The pre-run edit's fixture (the scorecard's `clock <0` counted 14 against 1 on x_trial-ladder-20261111-205858):
    a refused bandage whose line sent the gain-distance leg under the margin (a steer: no start), a riding rip sent under
    the margin (`ride` true: no start), and a loot sent under the margin (its own action: the one start under)."""
    rows = [gl(1.0, ck("bandage", 2.0, 6.0, refused=True, leg="sent"), "steer", branch="care", vx=1.0, vy=0.0),
            gl(2.0, ck("rip", 1.0, 5.0, ride=True), "rip", branch="care", itemId=5, keepMoving=True),
            gl(3.0, ck("loot", 2.0, 3.0), "interact", branch="goal", kind="loot", x=1, y=1)]
    return rec(), rows, []


UNDER_WANT = (3, 1, 1, 1, [2])   # allowed, starts, rides, under, under_lines


def _under():
    c = G.readings_x6(*under_case())["clock"]
    return (c["allowed"], c["starts"], c["rides"], c["under"], c["under_lines"])


def test_clock_under_the_margin_counts_only_the_clock_s_own_action_and_no_ride():
    """A leg line under the margin counts 0, a riding rip 0, a loot sent under the margin 1."""
    assert _under() == UNDER_WANT


def test_clock_is_unread_without_a_clock_and_agrees_with_the_scorecard():
    assert G.readings_x6(rec(), [gl(1.0, {}, "steer")], [])["clock"] == {"read": False}
    assert G.readings_x6(rec(), None, [])["clock"] == {"read": False}
    live = _ts().clock_gate(clock_case()[1])
    c = _clock()
    assert (live["lines"], live["ok"], live["held"], live["cut"], live["waited"]) == (
        c["lines"], c["allowed"], c["held"], c["cut"], c["waited"])   # `under` is no longer the scorecard's (the edit)


# ================================================================ crawler
def cfr(t, step, zs, aid="m1"):
    return fr(t, 0.0, zs=zs, act={"aid": aid, "state": "progress", "step": step} if step else None)


def crawler_case():
    """Frames 0.1 s apart. 1.0 a swing with a crawler at 0.5 and the standing target at 1.2 (counts); 1.1 a floor swing
    beside a crawler at 0.5 (the crawler's own press: no); 1.2 a swing with the crawler at 1.0 exactly (no); 1.3 a shove
    with the melee's target re-pinned to the crawler (1.25: not standing, no); 1.4 a stomp with the crawler at 0.3 and
    the target re-pinned back to the standing one (1.35: counts); 1.5 no act. m1's work leaf carries step_for
    crawler_buffer once."""
    std = zr(7, 11.2, 10.0)
    fs = [cfr(1.0, "swing", [crawler_z(8, 10.5, 10.0), std]), cfr(1.1, "floor", [crawler_z(8, 10.5, 10.0), std]),
          cfr(1.2, "swing", [crawler_z(8, 11.0, 10.0), std]), cfr(1.3, "shove", [crawler_z(8, 10.4, 10.0), std]),
          cfr(1.4, "stomp", [crawler_z(8, 10.3, 10.0), zr(7, 12.0, 10.0)]), cfr(1.5, None, [])]
    acts = [mel("m1", 0.9, "accepted"), mel("m1", 0.95, step="work", work={"step_for": "crawler_buffer"}),
            mel("m1", 1.25, step="shove", target=8), mel("m1", 1.35, step="stomp", target=7), mel("m1", 1.6, "done")]
    return rec(), None, ordered(fs, acts)


def _crawler():
    return G.readings_x6(*crawler_case())["crawler"]


def test_crawler_reads_a_crawler_within_a_tile_while_pressing_at_a_standing_target():
    c = _crawler()
    assert (c["read"], c["frames"], c["buffer"]) == (True, 2, 1)
    assert c["seconds"] == pytest.approx(0.2)


def test_crawler_is_unread_without_a_frame_and_agrees_with_the_scorecard():
    assert G.readings_x6(rec(), None, [mel("m1", 1.0, "accepted")])["crawler"] == {"read": False}
    lines = crawler_case()[2]
    from agent.base import gates_e as E
    live = _ts().crawler_close(E._frame_index(lines)[1], lines)
    assert live["frames"] == _crawler()["frames"] and live["seconds"] == pytest.approx(_crawler()["seconds"])


# ================================================================ room
def rfr(t, ring=None, ms=0, reaction=""):
    f = fr(t, 0.0)
    f["me"]["hitReaction"] = reaction
    f["me"]["room"] = ring
    f["cost"] = {"roomMs": ms}
    return f


def ring(h, stop=None):
    return {"h": list(h), "stop": list(stop or ["open"] * 8), "tick": 1}


def room_case():
    """The body faces +x: the headings behind it 135, 180 and 225 (90 and 270 are exactly 90 off: not behind). Rings on
    frames 0, 1, 3 and 6. The onset at frame 1 carries its ring (135 and 180 at 0.5: two closed, both behind; 225 at 1.0
    exactly: not closed); the onset at frame 5 reads frame 3's ring two frames back (none closed); the onset at frame 9
    has frame 6's ring three back, past the Sense's cadence (unread)."""
    fs = [rfr(1.0, ring([3] * 8), 4), rfr(1.1, ring([3, 3, 3, 0.5, 0.5, 1.0, 3, 3],
                                                    ["open", "open", "open", "wall", "wall", "door", "open", "open"]), 2,
                                          "Bite"),
          rfr(1.2), rfr(1.3, ring([3] * 8), 0), rfr(1.4), rfr(1.5, reaction="Bite"),
          rfr(1.6, ring([3] * 8, ["hop"] + ["open"] * 7), 1), rfr(1.7), rfr(1.8), rfr(1.9, reaction="Bite"), rfr(2.0)]
    return rec(), None, ordered(fs)


ROOM_WANT = {"read": True, "frames": 4, "stops": {"open": 28, "wall": 2, "door": 1, "hop": 1}, "ms_p50": 1.5,
             "ms_max": 4, "bites_read": 2,
             "bites": [{"seq": 11, "closed": 2, "behind": 3, "behind_closed": 2},
                       {"seq": 15, "closed": 0, "behind": 3, "behind_closed": 0},
                       {"seq": 19, "closed": None, "behind": None, "behind_closed": None}]}


def _room():
    return G.readings_x6(*room_case())["room"]


def test_room_reads_the_ring_s_frames_stops_cost_and_the_ring_at_each_bite():
    assert _room() == ROOM_WANT


def test_room_is_unread_without_a_ring_and_agrees_with_the_scorecard():
    assert G.readings_x6(rec(), None, [rfr(1.0)])["room"] == {"read": False}
    from agent.base import gates_e as E
    live = _ts().room_readings(E._frame_index(room_case()[2])[1])
    r = _room()
    assert (live["frames"], live["stops"], live["ms_p50"], live["ms_max"]) == (
        r["frames"], r["stops"], r["ms_p50"], r["ms_max"])


# ================================================================ rip_ride
def rip_case():
    """Rips: riding a1 done; riding a2 superseded; standing (keepMoving false) a3 failed stopped; riding at 5.0 with no
    act line (open); standing a4 at 5.5 rejected worn (its first line 5.55: the send at 5.5 its own, the earlier riding
    one left open); standing (keepMoving false) a5 done."""
    rows = [gl(1.0, {}, "rip", branch="care", itemId=1, keepMoving=True),
            gl(2.0, {}, "rip", branch="care", itemId=2, keepMoving=True),
            gl(3.0, {}, "rip", branch="care", itemId=3, keepMoving=False),
            gl(5.0, {}, "rip", branch="care", itemId=4, keepMoving=True),
            gl(5.5, {}, "rip", branch="care", itemId=5),
            gl(7.0, {}, "rip", branch="care", itemId=6, keepMoving=False)]
    acts = [act("a1", "rip", 1.05, "accepted"), act("a1", "rip", 4.0, "done", rags=1),
            act("a2", "rip", 2.05, "accepted"), act("a2", "rip", 2.5, "failed", "superseded"),
            act("a3", "rip", 3.05, "accepted"), act("a3", "rip", 3.5, "failed", "stopped"),
            act("a4", "rip", 5.55, "rejected", "worn"),
            act("a5", "rip", 7.05, "accepted"), act("a5", "rip", 9.0, "done")]
    return rec(), rows, ordered(acts)


RIP_WANT = {"read": True, "riding": {"sent": 3, "done": 1, "failed": 0, "superseded": 1, "open": 1},
            "standing": {"sent": 3, "done": 1, "failed": 2, "superseded": 0, "open": 0}}


def _rip():
    return G.readings_x6(*rip_case())["rip_ride"]


def test_rip_ride_reads_the_rips_riding_against_standing_by_their_ends():
    assert _rip() == RIP_WANT


def test_rip_ride_is_unread_without_a_decision_log():
    assert G.readings_x6(rec(), None, [])["rip_ride"] == {"read": False}


# ================================================================ the module's cases
def test_the_readings_read_the_sources_clipped_at_the_stop():
    out, rows, lines = pull_case()
    out["stop"]["wallS"] = 1.6 + (out["loop"]["startPyMs"] / 1000.0 - T0)
    assert G.readings_x6(out, rows, lines)["engage_pull"]["lines"] == 2


def test_the_module_imports_no_live_planner_world_or_tools_name_and_holds_its_own_copies():
    names = T20._imports(G.__file__)
    assert not any(m.startswith(("agent.base.planner", "agent.base.world", "tools", "trial_score")) for m in names)
    assert G.NEW == ("cadence", "steps", "engage_pull", "cone_bites", "clock", "crawler", "room", "rip_ride")
    assert (G.CONE_DEG, G.CRAWLER_R, G.CRAWLER_STEPS) == (90.0, 1.0, ("swing", "shove", "stomp"))
    assert (G.ROOM_NEED, G.ROOM_STEP_DEG, G.ROOM_EVERY) == (1.0, 45.0, 3)
    assert G.TIMED == ("rip", "unwear", "bandage", "loot", "door", "scan")
    assert G.STEP_VALUES == {"step_for": ("gap", "retreat", "pile", "pile_out", "stagger_in", "crawler_buffer"),
                             "shove_for": ("knockdown",), "repin_for": ("stall", "attacker")}


def test_the_frozen_copies_match_their_live_sources_at_this_commit():
    """The copies' sources read at the commit the module was written on (3f1e86b5): the scorecard's constants, the
    clock's TIMED and action_kind, the Lua's K.WORK_ROOM_NEED, K.WORK_ROOM_HEADINGS and S.ROOM_EVERY as text, and the
    schema's work-leaf reasons named in its descriptions (a later change of any is the next grade's to fold in)."""
    TS = _ts()
    assert (G.CONE_DEG, G.CRAWLER_R, G.CRAWLER_STEPS, G.STEP_KEYS) == (TS.CONE_DEG, TS.CRAWLER_R, TS.CRAWLER_STEPS,
                                                                       TS.STEP_KEYS)
    assert tuple(TS.PULL_LETTERS) == G.PULL_WHYS
    from agent.base.planner import clock as PC
    assert PC.TIMED == G.TIMED
    for typ, args in [("rip", {}), ("unwear", {}), ("scan", {}), ("bandage", {}), ("bandage", {"keepMoving": True}),
                      ("interact", {"kind": "loot"}), ("interact", {"kind": "open"}), ("interact", {"kind": "close"}),
                      ("interact", {"kind": "use"}), ("melee", {})]:
        assert G.action_kind(typ, args) == PC.action_kind(typ, args), (typ, args)
    lua = os.path.join(TESTING, "PZAgent", "PZAgent", "42", "media", "lua", "client")
    work = open(os.path.join(lua, "PZAgent_StanceWork.lua"), encoding="utf-8").read()
    assert "K.WORK_ROOM_NEED = 1.0 " in work and "K.WORK_ROOM_HEADINGS = { 0, 45, 90, 135, 180, 225, 270, 315 }" in work
    assert "S.ROOM_EVERY = 3\n" in open(os.path.join(lua, "PZAgent_Sense.lua"), encoding="utf-8").read().replace(
        "\r\n", "\n")
    schema = open(os.path.join(TESTING, "agent", "base", "schema", "pza1.json"), encoding="utf-8").read()
    for word in G.STEP_FOR + G.SHOVE_FOR + G.REPIN_FOR + (G.MOVING_BACK, G.AIR_LAUNCH, G.KEEP_MOVING):
        assert word in schema, word


def test_no_new_key_shadows_an_earlier_grade_s_key():
    """grade_x6 updates grade_x5's dict with NEW: a key an earlier grade holds (x1's `pull`, P24-AN) would be
    overwritten and the base's report lines with it; the committed F21 grade holds none of NEW."""
    p = os.path.join(F21, "f_grade.txt")
    if not os.path.isfile(p):
        pytest.skip("%s is not checked out" % F21)
    t = open(p, "rb").read().replace(b"\r\n", b"\n").decode("utf-8")
    keys = set(json.loads(t[t.index("\n{\n"):]))
    assert not keys & set(G.NEW) and "pull" in keys


# ================================================================ the mutants
def _mutated(name, edit):
    """grades/x6.py's source with `edit` applied inside the top-level def `name` only, executed as a module copy."""
    src = open(G.__file__, encoding="utf-8").read()
    head = "\ndef %s(" % name
    start = src.index(head)
    nxt = [i for i in (src.find("\ndef ", start + 5), src.find("\nclass ", start + 5)) if i >= 0]
    end = min(nxt) if nxt else len(src)
    new = edit(src[start:end])
    assert new != src[start:end], (name, "the mutant changed nothing")
    ns = {"__name__": "x6_mutant"}
    exec(compile(src[:start] + new + src[end:], "x6_mutant", "exec"), ns)    # noqa: S102 - a scratch copy
    return ns


def holds(fn, want):
    return lambda: fn() == want


MUTANTS = [
    # cadence: the retreat's window off by one (the line after the run not read: the leaf C dropped)
    ("e_cadence", lambda b: b.replace("if (own or prev) and cur is not None:", "if own and cur is not None:"),
     holds(_cadence, CADENCE_WANT)),
    # cadence: a heartbeat's re-read leaf counted again (no key)
    ("press_leaves", lambda b: b.replace("if key not in seen:", "if True:"), holds(_cadence, CADENCE_WANT)),
    # cadence: the shares over every leaf, a pre-1.15 leaf in the denominator
    ("e_cadence", lambda b: b.replace("has = [p for p in ls if p[\"leaf\"].get(key) is not None]", "has = ls"),
     holds(_cadence, CADENCE_WANT)),
    # cadence: a failed line's counts read beside the done lines'
    ("e_cadence", lambda b: b.replace("if ln.get(\"state\") == DONE:", "if ln.get(\"state\") in (DONE, FAILED):"),
     holds(_cadence, CADENCE_WANT)),
    # cadence: the retreat's back presses off a wrong key (air for moving_back)
    ("e_cadence", lambda b: b.replace("cur[\"back\"] += 1 if p[\"leaf\"].get(MOVING_BACK) is True",
                                      "cur[\"back\"] += 1 if p[\"leaf\"].get(AIR) is True"),
     holds(_cadence, CADENCE_WANT)),
    # steps: every line counted (no runs)
    ("e_steps", lambda b: b.replace("if v is not None and v != prev.get(k):", "if v is not None:"),
     holds(_steps, STEPS_WANT)),
    # steps: a value after a gap in it read as the same run
    ("e_steps", lambda b: b.replace("prev[k] = v\n", "prev[k] = v if v is not None else prev.get(k)\n"),
     holds(_steps, STEPS_WANT)),
    # steps: the runs carried across melees
    ("e_steps", lambda b: b.replace("        prev = {}\n", "").replace("by, nan = {}, 0", "by, nan, prev = {}, 0, {}"),
     holds(_steps, STEPS_WANT)),
    # steps: nan_heading off a wrong key
    ("e_steps", lambda b: b.replace("if w.get(NAN_HEADING):", "if w.get(\"nan\"):"), holds(_steps, STEPS_WANT)),
    # engage_pull: an episode per line
    ("e_pull", lambda b: b.replace("if k not in prev:", "if True:"), holds(_pull, PULL_WANT)),
    # engage_pull: a line with no pull not ending the episode
    ("e_pull", lambda b: b.replace("prev = now", "prev = prev | now"), holds(_pull, PULL_WANT)),
    # engage_pull: any room read as closed
    ("e_pull", lambda b: b.replace("1 if room == ROOM_CLOSED else 0", "1 if room is not None else 0"),
     holds(_pull, PULL_WANT)),
    # engage_pull: held off a wrong key
    ("e_pull", lambda b: b.replace("p.get(\"held\") is True", "p.get(\"hold\") is True"), holds(_pull, PULL_WANT)),
    # cone_bites: a bite inside the cone (exactly 90 off) counted outside
    ("e_cone_bites", lambda b: b.replace("abs(ang) > CONE_DEG", "abs(ang) >= CONE_DEG"),
     test_cone_bites_read_the_onsets_from_outside_the_front_half),
    # cone_bites: the nearest zombie read whatever it is (a crawler)
    ("_nearest_standing_xy", lambda b: b.replace("if _standing(z) and ", "if "),
     test_cone_bites_read_the_onsets_from_outside_the_front_half),
    # cone_bites: the reaction runs for the segments (a type change no onset)
    ("e_cone_bites", lambda b: b.replace("GX1.reaction_segments(frames)", "G21._reaction_runs(frames)"),
     test_cone_bites_read_the_onsets_from_outside_the_front_half),
    # clock: a clock line with ttc == need read as started under the need
    ("e_clock", lambda b: b.replace("ttc < need", "ttc <= need"),
     test_clock_reads_its_lines_by_action_the_steer_cuts_and_the_durations),
    # clock (the pre-run edit): a leg line under the margin read as a start (any sent line)
    ("e_clock", lambda b: b.replace("!= c.get(\"action\"):", "is None and False:"), holds(_under, UNDER_WANT)),
    # clock (the pre-run edit): a riding rip read as a start
    ("e_clock", lambda b: b.replace("if c.get(RIDE) is True:", "if False:"), holds(_under, UNDER_WANT)),
    # clock: a cut read as allowed
    ("e_clock", lambda b: b.replace("if c.get(\"cut\"):", "if False:"),
     test_clock_reads_its_lines_by_action_the_steer_cuts_and_the_durations),
    # clock: the superseding send read as the first send after the action's (not the last before its end)
    ("e_clock", lambda b: b.replace("typ = later[-1][1]", "typ = later[0][1]"),
     test_clock_reads_its_lines_by_action_the_steer_cuts_and_the_durations),
    # clock: a door counted as a care
    ("e_clock", lambda b: b.replace("if kind in CARE_KINDS and", "if kind in TIMED and"),
     test_clock_reads_its_lines_by_action_the_steer_cuts_and_the_durations),
    # clock: the duration from the send, not the accepted line
    ("e_clock", lambda b: b.replace("start = acc if acc is not None else s[0]", "start = s[0]"),
     test_clock_reads_its_lines_by_action_the_steer_cuts_and_the_durations),
    # crawler: a crawler on a floor step counted
    ("e_crawler", lambda b: b.replace("not in CRAWLER_STEPS:", "not in CRAWLER_STEPS + (\"floor\",):"),
     test_crawler_reads_a_crawler_within_a_tile_while_pressing_at_a_standing_target),
    # crawler: the radius inclusive
    ("e_crawler", lambda b: b.replace("< CRAWLER_R]", "<= CRAWLER_R]"),
     test_crawler_reads_a_crawler_within_a_tile_while_pressing_at_a_standing_target),
    # crawler: a target not standing (the crawler re-pinned to) counted
    ("e_crawler", lambda b: b.replace("if target is not None and _standing(target):", "if target is not None:"),
     test_crawler_reads_a_crawler_within_a_tile_while_pressing_at_a_standing_target),
    # crawler: the buffer steps off a wrong value
    ("e_crawler", lambda b: b.replace(".get(CRAWLER_BUFFER, 0)", ".get(\"crawler\", 0)"),
     test_crawler_reads_a_crawler_within_a_tile_while_pressing_at_a_standing_target),
    # room: a heading at ROOM_NEED exactly read closed
    ("e_room", lambda b: b.replace("v < ROOM_NEED)", "v <= ROOM_NEED)"), holds(_room, ROOM_WANT)),
    # room: a heading exactly 90 off the body read behind
    ("e_room", lambda b: b.replace("- body)) > CONE_DEG]", "- body)) >= CONE_DEG]"), holds(_room, ROOM_WANT)),
    # room: the ring's window one frame too long (a ring three frames back read)
    ("e_room", lambda b: b.replace("max(a - ROOM_EVERY, -1)", "max(a - ROOM_EVERY - 1, -1)"), holds(_room, ROOM_WANT)),
    # room: a ring's stops counted once per frame, not per heading
    ("e_room", lambda b: b.replace("for k in E._l(room.get(\"stop\")):", "for k in E._l(room.get(\"stop\"))[:1]:"),
     holds(_room, ROOM_WANT)),
    # rip_ride: keepMoving read as present, not true
    ("e_rip_ride", lambda b: b.replace("args.get(KEEP_MOVING) is True", "KEEP_MOVING in args"), holds(_rip, RIP_WANT)),
    # rip_ride: superseded read as any failure
    ("e_rip_ride", lambda b: b.replace(" and end.get(\"reason\") == SUPERSEDED", ""), holds(_rip, RIP_WANT)),
    # rip_ride (aid_sends): an aid matched to the earliest send of its type, not the latest before its first line
    ("aid_sends", lambda b: b.replace("        while k + 1 < len(cand) and cand[k + 1][0] <= w:\n            k += 1\n",
                                      "        if k + 1 < len(cand) and cand[k + 1][0] <= w:\n            k += 1\n"),
     holds(_rip, RIP_WANT)),
]


@pytest.mark.parametrize("n", range(len(MUTANTS)), ids=lambda n: "%s-%d" % (MUTANTS[n][0], n))
def test_a_mutant_of_each_reading_fails_its_fixture(n, monkeypatch):
    name, edit, check = MUTANTS[n]
    assert check() is not False, "the fixture must hold on the real module"
    monkeypatch.setattr(G, name, _mutated(name, edit)[name])
    try:
        survives = check() is not False
    except AssertionError:   # a fixture written as a test fails by assertion
        survives = False
    assert not survives, "the mutant of %s survives its fixture" % name


# ================================================================ the real check: F21 and F20
def _path(d, name):
    p = os.path.join(d, name)
    if not os.path.isfile(p):
        pytest.skip("%s is not checked out" % d)
    return p


def to_x5(g):
    """grade_x6's dict as grade_x5's: the new keys and `base_x5` dropped, the names restored, the new lines dropped."""
    g = dict(g)
    for k in G.NEW:
        g.pop(k)
    g["grade"], g["base"] = g.pop("base"), g.pop("base_x5")
    g["report_lines"] = [("gate_x5 " + ln[len("gate_x6 "):]) if ln.startswith("gate_x6 ") else ln
                         for ln in g["report_lines"][:-G.N_LINES]]
    return g


UNREAD = {"read": False}
RIP_NONE = {"sent": 0, "done": 0, "failed": 0, "superseded": 0, "open": 0}
F21_X6 = {
    "cadence": UNREAD, "engage_pull": UNREAD, "clock": UNREAD, "room": UNREAD,
    "steps": {"read": True, "step_for": {"gap": 9, "retreat": 6, "pile": 1, "pile_out": 0, "stagger_in": 0,
                                         "crawler_buffer": 0},
              "shove_for": {"knockdown": 0}, "repin_for": {"stall": 0, "attacker": 0}, "nan_heading": 0,
              "pile": {"episodes": 1, "shoves": 1, "knockdowns": 1}},
    "crawler": {"read": True, "frames": 0, "seconds": 0.0, "buffer": 0},
    "rip_ride": {"read": True, "riding": RIP_NONE, "standing": dict(RIP_NONE, sent=7, superseded=7)},
}
F21_CONE = [(3340, False), (3517, False), (3676, False), (4888, False), (4902, False), (4914, False), (4918, False)]
F20_X6 = {
    "cadence": UNREAD, "engage_pull": UNREAD, "clock": UNREAD, "room": UNREAD, "steps": UNREAD,
    "crawler": {"read": True, "frames": 0, "seconds": 0.0, "buffer": 0},
    "rip_ride": {"read": True, "riding": RIP_NONE, "standing": dict(RIP_NONE, sent=1, done=1)},
}


def _script(name, path):
    r = subprocess.run([sys.executable, os.path.join(TESTING, "agent", "drivers", name), path], capture_output=True,
                       cwd=TESTING)
    assert r.returncode == 0, r.stderr
    return r.stdout.replace(b"\r\n", b"\n")


def _check_f21(got):
    assert {k: got[k] for k in G.NEW if k != "cone_bites"} == F21_X6
    cb = got["cone_bites"]
    assert (cb["read"], cb["bites"], cb["outside"]) == (True, 7, 0)
    assert [(r["seq"], r["outside"]) for r in cb["rows"]] == F21_CONE


F21_SHA256 = "be21f9bacd77c0486d0e55184c1a5d07f175d8b05bccc74b50702eb1e65b80f7"   # f_grade_18.py's whole stdout on F21 (CRLF folded), pinned at its first run


def test_f_grade_18_on_f21_reproduces_the_committed_f_grade_txt_under_its_new_lines():
    """f_grade_18.py on F21: its grade_x5 lines are the committed f_grade.txt's (f_grade_17's) lines byte for byte, the
    eight engagement lines after them, its JSON the committed one's with the engagement keys and the names added, the
    readings as F21's logs carry them (F21_X6: the Plan 36 keys unread, the older keys' readings pinned), and the whole
    output's sha256 pinned (a drift in any reading or any live name read through the grade chain fails here)."""
    p = _path(F21, "f_goals_21.json")
    text = _script("f_grade_18.py", p).decode("utf-8")
    want = open(os.path.join(F21, "f_grade.txt"), "rb").read().replace(b"\r\n", b"\n").decode("utf-8")
    i, j = text.index("\n{\n"), want.index("\n{\n")
    lines, wlines = text[:i + 1].splitlines(), want[:j + 1].splitlines()
    assert [("gate_x5 " + ln[len("gate_x6 "):]) if ln.startswith("gate_x6 ") else ln
            for ln in lines[:-G.N_LINES]] == wlines and len(lines) == len(wlines) + G.N_LINES
    assert lines[-G.N_LINES].startswith("cadence")
    got = json.loads(text[i:])
    _check_f21(got)
    assert to_x5(got) == json.loads(want[j:])
    assert (got["grade"], got["base"], got["base_x5"], got["base_x4"], got["base_x1"]) == (
        "grade_x6", "grade_x5", "grade_x4", "grade_x3", "grade_f12")
    assert hashlib.sha256(text.encode("utf-8")).hexdigest() == F21_SHA256


@functools.lru_cache(maxsize=None)
def _f20():
    p = _path(F20, "f_goals_20.json")
    out, log, goals = EG23.load(p), EG23.load_log(p), FG15.load_goals(p)
    return G.grade_x6(out, log, state_dir=F20, goal_lines=goals, kind="f"), GX5.grade_x5(
        out, log, state_dir=F20, goal_lines=goals, kind="f")


def test_on_f20_grade_x6_keeps_every_grade_x5_key():
    g, base = _f20()
    assert to_x5(g) == base
    assert {k: g[k] for k in G.NEW if k != "cone_bites"} == F20_X6
    assert (g["cone_bites"]["bites"], g["cone_bites"]["outside"]) == (1, 0)
    json.dumps(g, allow_nan=False)


# ================================================================ the first artifact graded through grade_x6: F22
F22 = os.path.join(TESTING, "artifacts", "f_goals_22-20261111-215108")


def test_f_grade_18_on_f22_reproduces_the_committed_f_grade_txt_byte_for_byte():
    """Ruling P26-Q: `f_grade_18.py` on the committed F22 artifact (Plan 36's evidence session, the first graded through
    `grade_x6`: the cadence, steps, engage_pull, cone_bites, clock, crawler, room and rip_ride readings over grade_x5's)
    reproduces its committed `f_grade.txt` byte for byte (CRLF folded), so a drift in any live name read through the grade
    chain fails here."""
    p = _path(F22, "f_goals_22.json")
    want = open(os.path.join(F22, "f_grade.txt"), "rb").read().replace(b"\r\n", b"\n")
    assert _script("f_grade_18.py", p) == want
