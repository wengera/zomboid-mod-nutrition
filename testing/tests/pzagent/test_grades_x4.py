"""base/grades/x4.py (Plan 34 Task 5), offline: `grade_x4` and its column readings (`care_withheld`: the lines whose threat
why carries LEAVE_CARE's key, by its `n` and its keys; `care_at_group`: the care sends a column forbids, criterion 1;
`door_leave`: the leave's door picks, refusals and aborts, the enters read outside and the closes read inside;
`retreat`: the fighting retreat's legs by kind, its melee's give-way, the strung holds and the gap; `shoves`: the shove
and stomp acts' ends, criterion 4; `idle_snap_by_act`: x3's idle frames split by the frame's act; `frame_age`: the
lines carrying the stale frame's age; `group_leave_legs` and `drag_fight`: the frozen x3 readers' vocabulary folded
in), each on a fabricated ring where it counts, its unread case and a mutant of each reading that its fixture fails;
every grade_x3 key kept under `grade_x4` on the committed F19 (`f_goals_19-20261109-060929`, Plan 33's evidence
session, the first graded through grade_x3) and E23 artifacts, through the function and through the regrade scripts
`f_grade_16.py` and `e_grade_25.py`; F19's readings pinned (the counts this writer read off its decision and state logs,
each docstring saying how)."""
import functools
import hashlib
import json
import math
import os
import subprocess
import sys

import pytest

from agent.base.grades import x3 as GX3
from agent.base.grades import x4 as G
from agent.drivers import e_grade_23 as EG23
from agent.drivers import e_grade_25 as EG25
from agent.drivers import f_grade_15 as FG15
from agent.drivers import f_grade_16 as FG16
from . import test_grades_e20 as T20
from .test_gates_e7 import T0
from .test_grades_e14 import actl
from .test_grades_x2 import fr, ordered, rec, zr
from .test_grades_x3 import idle_case

HERE = os.path.dirname(os.path.abspath(__file__))
TESTING = os.path.dirname(os.path.dirname(HERE))
F19 = os.path.join(TESTING, "artifacts", "f_goals_19-20261109-060929")
E23 = os.path.join(TESTING, "artifacts", "e_day_23-20261105-095110")
R = math.radians


def dline(t, threat, type_=None, sent=True, branch="threat", nearest=None, top=None, **args):
    """A decision line `t` seconds into the loop: its branch, its threat why, its action (None without a type), the
    line's `inputs.nearest` and hour (10:00 plus `t` seconds) and any top-level keys `top`."""
    ln = {"action": {"type": type_, "args": dict(args)} if type_ else None, "branch": branch, "gameMin": 600,
          "inputs": {"branches": {"threat": dict(threat)}, "nearest": nearest, "hour": 10.0 + t / 3600.0},
          "sent": sent, "wall": T0 + t}
    ln.update(top or {})
    return ln


def care(t, type_, sent=True, **args):
    return dline(t, {}, type_, sent=sent, branch="care", **args)


def mapl(t, *squares):
    """A state-log map line `t` seconds into the loop listing `squares` ((x, y, room, building))."""
    return {"kind": "map", "seq": int(t * 10), "tick": int(t * 60), "wallMs": int((T0 + t) * 1000), "mode": "delta",
            "scanId": 0, "squares": [{"x": x, "y": y, "z": 0, "room": room, "building": b} for x, y, room, b in squares],
            "missing": []}


# ================================================================ care_withheld
def withheld_case():
    """Four lines: the key on line 0 (n 4, key bleed 7), nested in a flee's why on line 1 (n 3, no key), none on line 2,
    on line 3 (n 4, key bleed 7 again)."""
    rows = [dline(1.0, {"care_withheld": {"why": "group", "n": 4, "key": ["bleed", 7]}}, "steer", vx=1.0, vy=0.0),
            dline(1.5, {"flee": "many", "leave": {"care_withheld": {"why": "group", "n": 3, "key": None}}}),
            dline(2.0, {"flee": "many"}),
            dline(2.5, {"care_withheld": {"why": "group", "n": 4, "key": ["bleed", 7]}}, "steer", vx=1.0, vy=0.0)]
    return rec(), rows, []


def _withheld():
    return G.readings_x4(*withheld_case())["care_withheld"]


def test_care_withheld_counts_its_lines_by_n_and_its_keys():
    assert _withheld() == {"read": True, "lines": 3, "by_n": {"3": 1, "4": 2}, "keys": [["bleed", 7]]}


# ================================================================ care_at_group
def group_frame(t, n_standing, fallen=0, far=False):
    """A frame `t` seconds in: `n_standing` standing zombies within GROUP_ENTRY_R (the last at 5.5 tiles), `fallen`
    fallen ones at 2 tiles, and (with `far`) one standing at 6.5 tiles."""
    zs = [zr(100 + k, 10.0 + (5.5 if k == n_standing - 1 else 1.0 + k * 0.5), 10.0) for k in range(n_standing)]
    zs += [zr(200 + k, 10.0, 12.0, floor=True) for k in range(fallen)]
    if far:
        zs.append(zr(300, 16.5, 10.0))
    return fr(t, 0.0, zs=zs)


def care_group_case():
    """Eight lines, each with a frame 0.05 s before it: a stop at three standing (counted); a rip at two standing and a
    fallen one (not); a riding bandage at three (not); a standing bandage at three (counted); an unwear not sent (not);
    a wear at three (not a dressing send); a threat line's stop at three (not the care's); an unwear at four standing,
    one more at 6.5 tiles (counted). The frame after the first line reads none standing."""
    rows = [care(1.0, "stop"), care(1.5, "rip", itemId=5), care(2.0, "bandage", keepMoving=True, part=7),
            care(2.5, "bandage", part=7), care(3.0, "unwear", sent=False, itemId=6), care(3.5, "wear", itemId=6),
            dline(4.0, {}, "stop"), care(4.5, "unwear", itemId=6)]
    frames = [group_frame(0.95, 3), group_frame(1.05, 0), group_frame(1.45, 2, fallen=1), group_frame(1.95, 3),
              group_frame(2.45, 3), group_frame(2.95, 3), group_frame(3.45, 3), group_frame(3.95, 3),
              group_frame(4.45, 4, far=True)]
    return rec(), rows, ordered(frames)


def _care_group():
    return G.readings_x4(*care_group_case())["care_at_group"]


def test_care_at_group_counts_the_care_sends_a_column_forbids():
    c = _care_group()
    assert (c["read"], c["lines"]) == (True, 3)
    assert c["rows"] == [{"i": 0, "type": "stop", "standing": 3}, {"i": 3, "type": "bandage", "standing": 3},
                         {"i": 7, "type": "unwear", "standing": 4}]


# ================================================================ door_leave
def door_case():
    """Fifteen lines: a door pick sent then held (one pick, two door lines); a retreat; a second door pick sent then
    held; the race and one-exit refusals; an abort; an enter ended outside; a close refused guarded; a close sent on a
    room square of the plan's building 12 (inside); one sent on a square of building 12 with no room (outside); a doorway pick's
    `refused` list (no close refusal); a door leg never sent (no pick); a close sent on a room square of building 13."""
    rows = [dline(1.0, {"group_leave": {"leg": "door", "n": 3, "door": [11, 10, 0]}}, "walkTo", x=11.5, y=10.5),
            dline(1.5, {"group_leave": {"leg": "door", "n": 3}}),
            dline(2.0, {"group_leave": {"leg": "retreat"}}, "aim", targetId=1),
            dline(2.5, {"group_leave": {"leg": "door"}}, "walkTo", x=11.5, y=10.5),
            dline(3.0, {"group_leave": {"leg": "door"}}),
            dline(3.5, {"group_leave": {"n": 4, "door_refused": "race"}}),
            dline(4.0, {"group_leave": {"n": 4, "door_refused": "one_exit"}}),
            dline(4.5, {"group_leave": {"door_dropped": "abort", "near": 0.8}}, "steer", vx=1.0, vy=0.0),
            dline(5.0, {"shelter": 12, "step": "enter", "ended": "outside", "retries": 1}, "walkTo", x=10.5, y=10.5),
            dline(5.5, {"shelter": 12, "step": "close", "refused": "guarded"}),
            dline(6.0, {"shelter": 12, "step": "close", "ended": "advance"}, "interact", kind="close", x=11, y=10),
            dline(6.5, {"shelter": 12, "step": "close", "ended": "advance"}, "interact", kind="close", x=11, y=10),
            dline(7.0, {"flee": "doorway", "shelter": None, "refused": [[1, 2]]}),
            dline(7.5, {"group_leave": {"leg": "door"}}, "walkTo", sent=False, x=11.5, y=10.5),
            dline(8.0, {"shelter": 12, "step": "close"}, "interact", kind="close", x=11, y=10)]
    maps = [mapl(0.5, (10, 10, "kitchen", 12), (12, 10, None, 12), (20, 10, "kitchen", 13))]
    frames = [fr(5.95, 0.0, x=10.6, y=10.4), fr(6.45, 0.0, x=12.3, y=10.4), fr(7.95, 0.0, x=20.5, y=10.5)]
    return rec(), rows, ordered(maps, frames)


def _door():
    return G.readings_x4(*door_case())["door_leave"]


def test_door_leave_reads_the_picks_refusals_aborts_enters_and_closes():
    d = _door()
    assert (d["read"], d["lines"], d["picks"], d["refused"], d["aborts"], d["enters_outside"]) == (
        True, 5, 2, {"race": 1, "one_exit": 1}, 1, 1)
    assert d["closes"] == {"sent": 3, "inside": 1, "refused": 1, "refused_by": {"guarded": 1}, "unread": 0}


def test_a_close_with_no_frame_or_no_square_record_is_unread():
    out, rows, lines = door_case()
    lines = [ln for ln in lines if ln["kind"] != "map"]
    c = G.readings_x4(out, rows, lines)["door_leave"]["closes"]
    assert (c["sent"], c["inside"], c["unread"]) == (3, 0, 3)


# ================================================================ retreat
def retreat_case():
    """Eight lines: three retreat legs (a stand at 3.0 tiles, a back leg, a melee given way to with retreat_break), a
    door leg's group_retreat (not the retreat), two strung holds, a back leg at 0.5 tiles (under GAP_CLOSE), and a
    leave line with no strung count."""
    rows = [dline(1.0, {"group_retreat": {"leg": "retreat"}, "retreat_leg": {"kind": "stand", "in_place_of": None}},
                  "aim", nearest=3.0, targetId=1),
            dline(1.5, {"group_retreat": {"leg": "retreat"}, "retreat_leg": {"kind": "back", "in_place_of": "walkTo"}},
                  "aim", nearest=2.0, targetId=1),
            dline(2.0, {"group_retreat": {"leg": "retreat"}, "fight": {"retreat_break": {"other": 5, "dist": 1.2}}},
                  "melee", nearest=1.0, targetId=1, mode="strike"),
            dline(2.5, {"group_retreat": {"leg": "door"}}, "walkTo", nearest=4.0, x=1, y=2),
            dline(3.0, {"group_leave": {"n": 2, "strung_n": 1}}),
            dline(3.5, {"group_leave": {"n": 2, "strung_n": 2}}),
            dline(4.0, {"group_retreat": {"leg": "retreat"}, "retreat_leg": {"kind": "back"}}, "aim", nearest=0.5,
                  targetId=1),
            dline(4.5, {"group_leave": {"n": 3, "leg": "retreat"}})]
    return rec(), rows, []


def _retreat():
    return G.readings_x4(*retreat_case())["retreat"]


def test_retreat_reads_its_legs_by_kind_the_breaks_the_strung_holds_and_the_gap():
    r = _retreat()
    assert (r["read"], r["lines"], r["by_kind"], r["breaks"], r["strung_holds"]) == (
        True, 4, {"stand": 1, "back": 2, "melee": 1}, 1, 2)
    g = r["gap"]
    assert (g["read"], g["lines"], g["min"], g["median"], g["closed"]) == (True, 4, 0.5, 1.5, 1)
    assert g["minutes"] == pytest.approx((0.5 + 0.5 + 0.5 + 0.5) / 60.0)


def test_the_gap_is_the_scorecards_retreat_gap_copied():
    """The frozen copy reads what tools/trial_score.py's live `retreat_gap` reads on the same lines (the copy's source)."""
    sys.path.insert(0, os.path.join(os.path.dirname(TESTING), "tools"))
    import trial_score as TS
    rows = retreat_case()[1]
    assert G.retreat_gap(rows) == TS.retreat_gap(rows)


# ================================================================ shoves
def shove_case():
    """Seven acts: a shove done with the attack started after 3 ticks' wait; one rejected busy; one failed busy after
    45 ticks; one rejected out of range; a stomp done not started with no wait; a stomp done started (no `waited`, a
    log before PZA/1.12); a melee (not counted)."""
    acts = [actl("s1", "shove", "accepted", 1.0), actl("s1", "shove", "done", 1.2, {"attackStarted": True, "waited": 3}),
            actl("s2", "shove", "rejected", 1.5, reason="busy"),
            actl("s3", "shove", "accepted", 2.0), actl("s3", "shove", "failed", 2.8, {"waited": 45}, reason="busy"),
            actl("s4", "shove", "rejected", 3.0, reason="range"),
            actl("t1", "stomp", "accepted", 3.5), actl("t1", "stomp", "done", 3.7, {"attackStarted": False, "waited": 0}),
            actl("t2", "stomp", "accepted", 4.0), actl("t2", "stomp", "progress", 4.1),
            actl("t2", "stomp", "done", 4.2, {"attackStarted": True}),
            actl("m1", "melee", "accepted", 5.0)]
    return rec(), None, ordered(acts)


def _shoves():
    return G.readings_x4(*shove_case())["shoves"]


def test_shoves_read_the_sent_done_started_busy_and_the_wait():
    s = _shoves()
    assert {k: s[k] for k in ("read", "sent", "done", "started", "busy", "waited")} == {
        "read": True, "sent": 6, "done": 3, "started": 2, "busy": 2, "waited": 3}
    assert s["by_type"] == {"shove": {"sent": 4, "done": 1, "started": 1, "busy": 2, "waited": 24.0},
                            "stomp": {"sent": 2, "done": 2, "started": 1, "busy": 0, "waited": 0}}


def test_shoves_read_none_waited_before_pza_1_12_and_unread_without_an_act_line():
    acts = [actl("s1", "shove", "accepted", 1.0), actl("s1", "shove", "done", 1.2, {"attackStarted": True})]
    s = G.readings_x4(rec(), None, acts)["shoves"]
    assert (s["sent"], s["done"], s["started"], s["waited"]) == (1, 1, 1, None)
    assert G.readings_x4(rec(), None, [fr(1.0, 0.0)])["shoves"] == {"read": False}


# ================================================================ idle_snap_by_act
def _idle():
    return G.readings_x4(*idle_case())["idle_snap_by_act"]


def test_idle_snap_by_act_splits_x3_s_frames_by_the_frame_s_act():
    """x3's idle case: the idle frame (10 degrees off) and the frame after the melee's done (35 off) read `none`, the
    walk's (20 off) `walkTo`; the frame inside the melee and the one with no zombie near are x3's own exclusions."""
    i = _idle()
    assert (i["read"], i["frames"]) == (True, 3)
    assert i["by_act"]["none"] == {"n": 2, "median": pytest.approx(10.0), "p90": pytest.approx(35.0),
                                   "hold30": pytest.approx(0.5)}
    assert i["by_act"]["walkTo"] == {"n": 1, "median": pytest.approx(20.0), "p90": pytest.approx(20.0),
                                     "hold30": pytest.approx(1.0)}
    assert set(i["by_act"]) == {"none", "walkTo"}
    assert i["frames"] == GX3.readings_x3(*idle_case())["idle_snap"]["frames"]


def test_idle_snap_by_act_reads_unread_without_a_body_angle():
    out, rows, lines = idle_case()
    lines = [dict(ln, me=dict(ln["me"], bodyAngle=None)) if ln.get("kind") == "frame" else ln for ln in lines]
    assert G.readings_x4(out, rows, lines)["idle_snap_by_act"] == {"read": False}


# ================================================================ frame_age
def age_case():
    rows = [dline(1.0, {}, top={"frame_age": 0.6}), dline(1.5, {}), dline(2.0, {}, top={"frame_age": 1.2}),
            dline(2.5, {"frame_age": 9.9}), dline(3.0, {}, top={"frame_age": 0.9})]
    return rec(), rows, []


def _age():
    return G.readings_x4(*age_case())["frame_age"]


def test_frame_age_reads_the_lines_carrying_it_their_median_and_max():
    """Only the line's own key (a why's key of the same name is not the line's frame)."""
    assert _age() == {"read": True, "lines": 3, "median": 0.9, "max": 1.2}


# ================================================================ group_leave_legs and drag_fight
def legs_case():
    rows = [dline(1.0, {"group_leave": {"closing": [1, 2, 3], "leg": "shove", "target": 1}}, "shove", targetId=1),
            dline(1.5, {"group_leave": {"n": 3, "leg": "door", "door": [1, 2, 0]}}, "walkTo", x=1.5, y=2.5),
            dline(2.0, {"group_leave": {"n": 3, "leg": "door"}}),
            dline(2.5, {"group_leave": {"n": 4, "leg": "retreat"}}, "aim", targetId=1),
            dline(3.0, {"group_leave": {"n": 6, "leg": "run"}}, "steer", vx=1.0, vy=0.0),
            dline(3.5, {"group_leave": {"n": 7, "leg": "run"}}),
            dline(4.0, {"group_leave": {"end": "strung", "n": 2}}),
            dline(4.5, {"drag_fight": {"why": "hit", "dist": 0.5, "target": 9}}, "shove", targetId=9),
            dline(5.0, {"drag_fight": {"why": "hit", "spent": 1}}, "steer", vx=1.0, vy=0.0),
            dline(5.5, {"drag_fight": {"why": "stuck", "dist": 0.5, "target": 9}}, "shove", targetId=9)]
    return rec(), rows, []


def test_group_leave_legs_count_every_leg_and_the_strung_ends():
    g = G.readings_x4(*legs_case())["group_leave_legs"]
    assert g == {"read": True, "lines": 7, "legs": {"shove": 1, "door": 2, "retreat": 1, "run": 2},
                 "ends": {"strung": 1}}


def test_drag_fight_reads_its_whys_and_the_spent_lines():
    assert G.readings_x4(*legs_case())["drag_fight"] == {"read": True, "lines": 3, "by_why": {"hit": 2, "stuck": 1},
                                                         "spent": 1}


# ================================================================ the module's cases
def test_the_decision_readings_are_unread_without_a_decision_log():
    g = G.readings_x4(rec(), None, [fr(1.0, 0.0)])
    for k in ("care_withheld", "care_at_group", "door_leave", "retreat", "frame_age", "group_leave_legs",
              "drag_fight"):
        assert g[k] == {"read": False}, k


def test_the_readings_read_the_sources_clipped_at_the_stop():
    out, rows, lines = withheld_case()
    out["stop"]["wallS"] = 1.6 + (out["loop"]["startPyMs"] / 1000.0 - T0)
    assert G.readings_x4(out, rows, lines)["care_withheld"]["lines"] == 2


def test_the_scorecard_cell_is_care_at_group_s_lines():
    assert G.care_cell(*care_group_case()) == 3
    assert G.care_cell(rec(), None, []) is None


def test_the_module_imports_no_live_planner_world_or_tools_name_and_holds_its_own_copies():
    names = T20._imports(G.__file__)
    assert not any(m.startswith(("agent.base.planner", "agent.base.world", "tools", "trial_score")) for m in names)
    ns = vars(G)
    assert (ns["GROUP_LEAVE_N"], ns["GROUP_ENTRY_R"], ns["GAP_CLOSE"], ns["IDLE_SNAP_R"]) == (3, 6.0, 0.6, 2.5)
    assert ns["CARE_SENDS"] == ("stop", "rip", "unwear") and ns["BANDAGE"] == "bandage"
    assert (ns["CARE_WITHHELD"], ns["DOOR_REFUSED"], ns["DOOR_DROPPED"], ns["STRUNG_N"], ns["RETREAT_LEG"],
            ns["RETREAT_BREAK"], ns["DRAG_FIGHT"], ns["SHELTER"], ns["FRAME_AGE"], ns["WAITED"]) == (
        "care_withheld", "door_refused", "door_dropped", "strung_n", "retreat_leg", "retreat_break", "drag_fight",
        "shelter", "frame_age", "waited")
    assert ns["NEW"] == ("care_withheld", "care_at_group", "door_leave", "retreat", "shoves", "idle_snap_by_act",
                         "frame_age", "group_leave_legs", "drag_fight")
    assert (G.carries, G.value_of, G.threat_why, G.sent_action, G.standing) == (
        GX3.carries, GX3.value_of, GX3.threat_why, GX3.sent_action, GX3.standing)


# ================================================================ the mutants
def _mutated(name, edit):
    """grades/x4.py's source with `edit` applied inside the top-level def `name` only, executed as a module copy."""
    src = open(G.__file__, encoding="utf-8").read()
    head = "\ndef %s(" % name
    start = src.index(head)
    nxt = [i for i in (src.find("\ndef ", start + 5), src.find("\nclass ", start + 5)) if i >= 0]
    end = min(nxt) if nxt else len(src)
    new = edit(src[start:end])
    assert new != src[start:end], (name, "the mutant changed nothing")
    ns = {"__name__": "x4_mutant"}
    exec(compile(src[:start] + new + src[end:], "x4_mutant", "exec"), ns)    # noqa: S102 - a scratch copy
    return ns


MUTANTS = [
    # care_withheld
    ("e_care_withheld", lambda b: b.replace("carries(threat_why(r), CARE_WITHHELD)", "CARE_WITHHELD in threat_why(r)"),
     lambda: _withheld()["lines"] == 3),
    ("e_care_withheld", lambda b: b.replace('w.get("n")', 'w.get("why")'), lambda: _withheld()["by_n"] == {"3": 1, "4": 2}),
    ("e_care_withheld", lambda b: b.replace("if k is not None and k not in keys", "if k not in keys"),
     lambda: _withheld()["keys"] == [["bleed", 7]]),
    # care_at_group
    ("e_care_at_group", lambda b: b.replace("r.get(\"branch\") != CARE", "False"), lambda: _care_group()["lines"] == 3),
    ("e_care_at_group", lambda b: b.replace("args.get(KEEP_MOVING) is not True", "True"),
     lambda: _care_group()["lines"] == 3),
    ("e_care_at_group", lambda b: b.replace("standing(f, GROUP_ENTRY_R)", "standing(f, 99.0)"),
     lambda: _care_group()["rows"][-1]["standing"] == 4),
    ("e_care_at_group", lambda b: b.replace(">= GROUP_LEAVE_N", ">= 2"), lambda: _care_group()["lines"] == 3),
    ("e_care_at_group", lambda b: b.replace("E._frame_at(index, E._n(r.get(\"wall\")))",
                                            "E._frame_at(index, E._n(r.get(\"wall\")) + 0.07)"),
     lambda: _care_group()["lines"] == 3),
    # door_leave
    ("e_door_leave", lambda b: b.replace("if not any(sent_action(rows[i])[0] for i in run):", "if False:"),
     lambda: _door()["picks"] == 2),
    ("e_door_leave", lambda b: b.replace('gl.get("leg") == DOOR', 'gl.get("leg") is not None'),
     lambda: _door()["picks"] == 2),
    ("e_door_leave", lambda b: b.replace("isinstance(sh.get(REFUSED), str)", "sh.get(REFUSED)"),
     lambda: _door()["closes"]["refused"] == 1),
    ("e_door_leave", lambda b: b.replace("sh.get(ENDED) == OUTSIDE", "sh.get(ENDED) is not None"),
     lambda: _door()["enters_outside"] == 1),
    ("e_door_leave", lambda b: b.replace("carries(gl, DOOR_DROPPED)", "carries(gl, \"n\")"),
     lambda: _door()["aborts"] == 1),
    ("on_room", lambda b: b.replace(" and (building is None or s.get(\"building\") == building)", ""),
     lambda: _door()["closes"]["inside"] == 1),
    ("on_room", lambda b: b.replace('s.get("room") is not None and ', ""), lambda: _door()["closes"]["inside"] == 1),
    ("square_at", lambda b: b.replace("int(math.floor(me[0]))", "int(round(me[0]))"),
     lambda: _door()["closes"]["inside"] == 1),
    ("owner", lambda b: b.replace("if key in why:", "if False:"), lambda: _door()["enters_outside"] == 1),
    # retreat
    ("e_retreat", lambda b: b.replace('gr.get("leg") != RETREAT', 'gr.get("leg") is None'),
     lambda: _retreat()["lines"] == 4),
    ("e_retreat", lambda b: b.replace("if typ == MELEE:", "if typ == AIM:"),
     lambda: _retreat()["by_kind"] == {"stand": 1, "back": 2, "melee": 1}),
    ("e_retreat", lambda b: b.replace("carries(why, RETREAT_BREAK)", "RETREAT_BREAK in why"),
     lambda: _retreat()["breaks"] == 1),
    ("e_retreat", lambda b: b.replace("carries(gl, STRUNG_N)", "carries(gl, \"n\")"),
     lambda: _retreat()["strung_holds"] == 2),
    ("retreat_gap", lambda b: b.replace("if d < GAP_CLOSE:", "if d <= 0.4:"), lambda: _retreat()["gap"]["closed"] == 1),
    # shoves
    ("_shove_block", lambda b: b.replace("is True", "is not None"), lambda: _shoves()["started"] == 2),
    ("_shove_block", lambda b: b.replace(' and ln.get("reason") == BUSY', ""), lambda: _shoves()["busy"] == 2),
    ("_shove_block", lambda b: b.replace("statistics.median(waited)", "max(waited)"), lambda: _shoves()["waited"] == 3),
    ("e_shoves", lambda b: b.replace('ln.get("type") in (SHOVE, STOMP)', 'ln.get("type") == SHOVE'), lambda: _shoves()["sent"] == 6),
    # idle_snap_by_act
    ("e_idle_snap_by_act", lambda b: b.replace("if act.get(\"state\") in LIVE_STATES", "if True"),
     test_idle_snap_by_act_splits_x3_s_frames_by_the_frame_s_act),
    ("e_idle_snap_by_act", lambda b: b.replace('types.get(act.get("aid")) == MELEE and ', ""),
     lambda: _idle()["frames"] == 3),
    # frame_age
    ("e_frame_age", lambda b: b.replace("E._d(r).get(FRAME_AGE)", "value_of(r, FRAME_AGE)"),
     lambda: _age()["lines"] == 3),
    ("e_frame_age", lambda b: b.replace("statistics.median(ages)", "ages[0]"), lambda: _age()["median"] == 0.9),
    # group_leave_legs and drag_fight
    ("e_group_leave_legs", lambda b: b.replace('legs[leg] = legs.get(leg, 0) + 1', 'pass'),
     lambda: G.readings_x4(*legs_case())["group_leave_legs"]["legs"]["door"] == 2),
    ("e_group_leave_legs", lambda b: b.replace('gl.get("end")', 'gl.get("leg")'),
     lambda: G.readings_x4(*legs_case())["group_leave_legs"]["ends"] == {"strung": 1}),
    ("e_drag_fight", lambda b: b.replace('df.get("why")', 'df.get("target")'),
     lambda: G.readings_x4(*legs_case())["drag_fight"]["by_why"] == {"hit": 2, "stuck": 1}),
    ("e_drag_fight", lambda b: b.replace("carries(df, SPENT)", "carries(df, \"why\")"),
     lambda: G.readings_x4(*legs_case())["drag_fight"]["spent"] == 1),
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


# ================================================================ the real checks: F19 and E23
def _path(d, name):
    p = os.path.join(d, name)
    if not os.path.isfile(p):
        pytest.skip("%s is not checked out" % d)
    return p


@functools.lru_cache(maxsize=None)
def _f19():
    p = _path(F19, "f_goals_19.json")
    out, log, goals = EG23.load(p), EG23.load_log(p), FG15.load_goals(p)
    return G.grade_x4(out, log, state_dir=F19, goal_lines=goals, kind="f"), GX3.grade_x3(
        out, log, state_dir=F19, goal_lines=goals, kind="f")


def to_x3(g):
    """grade_x4's dict as grade_x3's: the new keys and `base_x3` dropped, the names restored, the new lines dropped."""
    g = dict(g)
    for k in G.NEW:
        g.pop(k)
    g["grade"], g["base"] = g.pop("base"), g.pop("base_x3")
    g["report_lines"] = [("gate_x3 " + ln[len("gate_x4 "):]) if ln.startswith("gate_x4 ") else ln
                         for ln in g["report_lines"][:-G.N_LINES]]
    return g


def test_on_f19_grade_x4_keeps_every_grade_x3_key():
    g, base = _f19()
    assert (g["grade"], g["base"], g["base_x3"], g["base_x2"], g["base_x1"]) == (
        "grade_x4", "grade_x3", "grade_x2", "grade_x1", "grade_f12")
    assert to_x3(g) == base
    json.dumps(g, allow_nan=False)


def test_on_f19_the_column_readings():
    """F19's readings, read by this writer off its decision.log (1614 lines, none after the stop) and state.log:
    care_at_group 14: the care lines sending a stop, rip, unwear or standing bandage with three or more standing within
    6 tiles on the frame at or before the line are lines 1545, 1551, 1558, 1579, 1583, 1588, 1594 and 1598 (the 8
    stops), 1552 (the unwear) and 1559, 1580, 1584, 1589 and 1599 (the 5 rips), standing 3 to 6 (the GUIDE's section 3
    names the same fourteen; Plan 34's plan text said 13); the session's ninth stop, its one standing bandage (line 610)
    and its two wears are not under a column. The door: one close sent (line 1602) with the player on the door's own
    outdoor square, so none inside; no shelter why yet ends `outside` or refuses (Task 2's keys); the door leg's 11
    lines in two runs (1595-1602, 1607-1611), each sending, so 2 picks. The shove and stomp acts: 10 sent (a244-a247,
    a279 stomps; a282, a283, a289, a321, a324 shoves), 5 rejected `busy` (a245 and the four shoves), 5 done all
    `attackStarted` true, no `waited` (PZA/1.11); the shoves alone 5 sent, 4 busy, 1 done. No line carries
    `care_withheld` or `frame_age` (both after this plan's code). The leave's legs: run 29, retreat 19, door 11, shove
    2, strung 12; the drag fight: hit 7, stuck 1, spent 5. The retreat: 19 lines (the scorecard's `retreat_gap` lines,
    min 0.8358422340940963), none carrying `retreat_leg`'s kind (it logs only `in_place_of` before Task 3), 2 sending a
    melee (lines 1568 and 1573: a300, a302). The idle frames by act: none 43, steer 192, walkTo 37, aim 29, rip 16,
    interact 2, shove 2, unwear 1 (the GUIDE's section 5 split, 322 frames)."""
    g = _f19()[0]
    c = g["care_at_group"]
    assert (c["read"], c["lines"]) == (True, 14)
    assert [r["i"] + 1 for r in c["rows"]] == [1545, 1551, 1552, 1558, 1559, 1579, 1580, 1583, 1584, 1588, 1589, 1594,
                                               1598, 1599]
    assert [r["type"] for r in c["rows"]].count("stop") == 8 and [r["type"] for r in c["rows"]].count("rip") == 5
    d = g["door_leave"]
    assert d["closes"]["sent"] == 1 and d["closes"]["inside"] == 0 and d["closes"]["unread"] == 0
    assert (d["picks"], d["lines"], d["refused"], d["aborts"], d["enters_outside"], d["closes"]["refused"]) == (
        2, 11, {"race": 0, "one_exit": 0}, 0, 0, 0)
    s = g["shoves"]
    assert (s["sent"], s["done"], s["started"], s["busy"], s["waited"]) == (10, 5, 5, 5, None)
    assert (s["by_type"]["shove"]["sent"], s["by_type"]["shove"]["busy"], s["by_type"]["shove"]["done"]) == (5, 4, 1)
    assert g["care_withheld"] == {"read": True, "lines": 0, "by_n": {}, "keys": []}
    assert g["frame_age"] == {"read": True, "lines": 0, "median": None, "max": None}
    assert g["group_leave_legs"] == {"read": True, "lines": 74, "legs": {"shove": 2, "door": 11, "retreat": 19,
                                                                         "run": 29}, "ends": {"strung": 12}}
    assert g["drag_fight"] == {"read": True, "lines": 8, "by_why": {"hit": 7, "stuck": 1}, "spent": 5}
    r = g["retreat"]
    assert (r["lines"], r["by_kind"], r["breaks"], r["strung_holds"]) == (19, {"stand": 0, "back": 0, "melee": 2}, 0, 0)
    assert (r["gap"]["lines"], r["gap"]["min"], r["gap"]["closed"]) == (19, 0.8358422340940963, 0)
    i = g["idle_snap_by_act"]
    assert {k: v["n"] for k, v in i["by_act"].items()} == {"none": 43, "steer": 192, "walkTo": 37, "aim": 29, "rip": 16,
                                                           "interact": 2, "shove": 2, "unwear": 1}
    assert i["frames"] == 322 == g["idle_snap"]["frames"]


def _script(name, path):
    r = subprocess.run([sys.executable, os.path.join(TESTING, "agent", "drivers", name), path], capture_output=True,
                       cwd=TESTING)
    assert r.returncode == 0, r.stderr
    return r.stdout.replace(b"\r\n", b"\n")


F19_SHA256 = "61af6c370f6d2efc0df07ac0137c014e16ac56e722639833f66a7cfef1e4017c"   # f_grade_16.py's whole stdout on F19 (CRLF folded), pinned at its first run


def test_f_grade_16_on_f19_reproduces_the_committed_f_grade_txt_under_its_new_lines():
    """f_grade_16.py on F19: its grade_x3 lines are the committed f_grade.txt's (f_grade_15's) lines byte for byte, the
    new lines after them one per reading, its JSON the committed one's with the column keys and the names added, and
    the whole output's sha256 pinned (a drift in any reading or any live name read through the grade chain fails here)."""
    p = _path(F19, "f_goals_19.json")
    text = _script("f_grade_16.py", p).decode("utf-8")
    want = open(os.path.join(F19, "f_grade.txt"), "rb").read().replace(b"\r\n", b"\n").decode("utf-8")
    i, j = text.index("\n{\n"), want.index("\n{\n")
    lines, wlines = text[:i + 1].splitlines(), want[:j + 1].splitlines()
    assert [("gate_x3 " + ln[len("gate_x4 "):]) if ln.startswith("gate_x4 ") else ln
            for ln in lines[:-G.N_LINES]] == wlines and len(lines) == len(wlines) + G.N_LINES
    assert lines[-G.N_LINES].startswith("care withheld (threat why care_withheld)")
    assert to_x3(json.loads(text[i:])) == json.loads(want[j:])
    assert hashlib.sha256(text.encode("utf-8")).hexdigest() == F19_SHA256


@functools.lru_cache(maxsize=None)
def _e23():
    p = _path(E23, "e_day_23.json")
    out, log = EG23.load(p), EG23.load_log(p)
    return G.grade_x4(out, log, state_dir=E23, kind="e"), GX3.grade_x3(out, log, state_dir=E23, kind="e")


def test_on_e23_grade_x4_keeps_every_grade_x3_key():
    g, base = _e23()
    assert g["base_x1"] == "grade_e21" and g["base_x3"] == "grade_x2" and to_x3(g) == base


def test_e_grade_25_prints_grade_x3_s_lines_then_the_column_ones_and_the_json():
    p = _path(E23, "e_day_23.json")
    text = _script("e_grade_25.py", p).decode("utf-8")
    i = text.index("\n{\n")
    g, base = _e23()
    printed = text[:i + 1].splitlines()
    assert [("gate_x3 " + ln[len("gate_x4 "):]) if ln.startswith("gate_x4 ") else ln
            for ln in printed[:-G.N_LINES]] == base["report_lines"]
    assert printed[-G.N_LINES:] == g["report_lines"][-G.N_LINES:]
    got = json.loads(text[i:])
    assert (got["grade"], got["base"], got["base_x3"], got["base_x1"]) == ("grade_x4", "grade_x3", "grade_x2",
                                                                          "grade_e21")


def test_the_regrade_scripts_name_themselves_and_refuse_an_argument_they_do_not_define():
    """Read statically (CLAUDE.md section 5): e_grade_25's main answers usage, exit 2, on no path or more than two
    outside `--chain`; f_grade_16's on anything but one path; each names itself and imports grade_x4."""
    e = open(EG25.__file__, encoding="utf-8").read()
    assert "if not paths or (not chain and len(paths) > 2):" in e and "return 2" in e and "usage: e_grade_25.py" in e
    assert "from agent.base.grades.x4 import gate_x4, grade_x4, report_lines_x4" in e and EG25.KIND == "e"
    assert e.startswith('"""e_grade_25 --') and "e_grade_24.py <" not in e and "grade_x3" not in e
    f = open(FG16.__file__, encoding="utf-8").read()
    assert "if len(argv) != 1:" in f and "usage: f_grade_16.py" in f and FG16.KIND == "f"
    assert f.startswith('"""f_grade_16 --') and "f_grade_15.py <" not in f and "grade_x3" not in f
    assert "from agent.base.grades.x4 import grade_x4" in f
    assert EG25.grade_x4 is G.grade_x4 and FG16.grade_x4 is G.grade_x4


F20 = os.path.join(TESTING, "artifacts", "f_goals_20-20261109-155512")


def test_f_grade_16_on_f20_reproduces_the_committed_f_grade_txt_byte_for_byte():
    """Ruling P26-Q: `f_grade_16.py` on the committed F20 artifact (the first session graded through `grade_x4`: the care, door,
    retreat, shove, frame-age and leg readings over grade_x3's) reproduces its
    committed `f_grade.txt` byte for byte (CRLF folded), so a drift in any live name read through the grade chain fails here."""
    p = os.path.join(F20, "f_goals_20.json")
    if not os.path.isfile(p):
        pytest.skip("%s is not checked out" % F20)
    script = os.path.join(TESTING, "agent", "drivers", "f_grade_16.py")
    r = subprocess.run([sys.executable, script, p], capture_output=True, cwd=TESTING)
    assert r.returncode == 0
    want = open(os.path.join(F20, "f_grade.txt"), "rb").read().replace(b"\r\n", b"\n")
    assert r.stdout.replace(b"\r\n", b"\n") == want
