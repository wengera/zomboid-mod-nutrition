"""base/grades/e20.py (Plan 29 Task 3), offline: `grade_e20` and cut 2 of the maneuver layer's reads (ruling P29-J: the
kills whole, the facing over every press, the melee's swings by the arms' pain) with one reading per rule of survival
iteration 23 (`T13_SWITCHES`: P29-A to P29-H'), each on a fabricated log where it counts, the clean case and the unread
case, a mutant per reading, every `grade_e19` key unchanged under `grade_e20` on test_gates_e13's fixtures (`kills` and
`hits` through their legacy views), the module's frozen copies (ruling P26-Q), and the real checks on E22
(`e_day_22-20261105-004919`, the first session with melee spans): `kills.planner` 4 off the melee's done lines with
the `zombie_dead` events agreeing, the 44 melee presses facing their targets (the T88 write-up's read, `GUIDE.md`
section 4), the eight swings by the pain (unread: no send line logs it), iteration 23's readings unread (the
session predates the rules), and every inherited key equal to the committed `e_grade.txt`'s, through the function
and through `e_grade_20.py`."""
import ast
import json
import os
import subprocess
import sys

import pytest

from agent.base import gates_e as E
from agent.base.grades import e19 as G19
from agent.base.grades import e20 as G
from agent.drivers import e_grade_20 as EG20
from . import test_grades_e14 as T14
from .test_gates_e7 import T0
from .test_gates_e13 import _act
from .test_grades_e14 import actl, row
from .test_grades_e17 import CLEAN
from .test_grades_e18 import hf
from .test_grades_e19 import dead, mv

HERE = os.path.dirname(os.path.abspath(__file__))
TESTING = os.path.dirname(os.path.dirname(HERE))
E22 = os.path.join(TESTING, "artifacts", "e_day_22-20261105-004919")
NEW = G.NEW
RULES = G.RULES


def grade(actions=(), results=(), log=None, frames=()):
    return G.grade_e20(T14.artifact(actions, results), decision_lines=log, lines=list(frames))


# ================================================================ the fixture of cut 2's reads
def z(zid, x, y, **kw):
    return dict({"id": zid, "x": x, "y": y}, **kw)


EAST8, EAST9, SOUTH5, EAST7, EAST4 = z(8, 12.0, 10.0), z(9, 12.0, 10.0), z(5, 10.0, 12.0), z(7, 12.0, 10.0), \
    z(4, 12.0, 10.0)


def pf(t, aid, step, me_dir, zombies=(), react=""):
    """A frame at (10, 10) facing `me_dir` with the act group {aid, accepted, step} (None without an aid)."""
    f = hf(t, react, zombies=zombies, me_dir=me_dir)
    f["act"] = {"aid": aid, "state": "accepted", "step": step} if aid is not None else None
    return f


def mp(aid, t, step, hp, **counts):
    """A melee progress act line at `t` with the target's health `hp` and the six counts (0 unless given)."""
    return actl(aid, "melee", "progress", t, dict({k: 0 for k in G19.COUNTS}, step=step, d=1.2, hp=hp, **counts))


def md(aid, t, end, hp1, **counts):
    r = dict({k: 0 for k in G19.COUNTS}, end=end, kill=end == "dead", hp0=2.0, hp1=hp1, dMin=0.5, steps={}, **counts)
    return actl(aid, "melee", "done", t, r)


def swing(t):
    """A state-log `swing` event (attackStarted true) `t` seconds into the loop."""
    return {"kind": "event", "event": "swing", "attackStarted": True, "meleeDelay": 0, "seq": int(t * 10),
            "tick": int(t * 60), "wallMs": int((T0 + t) * 1000)}


def cut2_lines():
    """The state log in wall order. m1 (a strike at 8, superseded): face (a frame facing N, 2 points off, the frame
    before the press), the swing twice (the heartbeat: one swing), the event, the frame after facing E (0 off), back
    lowering 2.0 to 1.6. m2 (a strike at 8): face (E), the swing, the frame after facing N (2 off), knock_wait (no fall
    in the health, the knock-down count 0 to 1), two floor presses in one `floor` step (each its event, each 0 off),
    done dead (8 killed). m3 (a strike at 9): the swing at 0.3, the frame after 0 off; the ladder's stomp k1 at 9 (its
    frame's own act, 0 off) reading targetDead, then m3's done dead at 9 (one kill of 9). The ladder's attack a1 at 5
    (S, 0 off, targetDead) and shove s1 at 6 (its frame carries no act and lists no zombie 6: read off the last
    accepted line, unread). m4 (a shove at 7, facing NE: 1 off; a steer accepted between its step and its event, so
    the frame's own act is m4 and the last accepted line the steer's). m6 (a strike at 4, facing W: 4 off; no
    decision line sent it, its pain unread; its swing lowered nothing). A reaction run at 9.5, a steer's event (no
    strike). The zombie_dead events: 8, 9, 5."""
    return [
        actl("m1", "melee", "accepted", 1.0), mp("m1", 1.1, "face", 2.0), pf(1.15, "m1", "face", "N", [EAST8]),
        mp("m1", 1.2, "swing", 2.0, swings=1), mp("m1", 1.22, "swing", 2.0, swings=1), swing(1.25),
        pf(1.3, "m1", "swing", "E", [EAST8]), mp("m1", 1.5, "back", 1.6, swings=1),
        actl("m1", "melee", "failed", 2.0, reason="superseded"),
        actl("m2", "melee", "accepted", 2.0), mp("m2", 2.1, "face", 1.6), pf(2.15, "m2", "face", "E", [EAST8]),
        mp("m2", 2.2, "swing", 1.6, swings=1), swing(2.25), pf(2.3, "m2", "swing", "N", [EAST8]),
        mp("m2", 2.5, "knock_wait", 1.6, swings=1, knockdowns=1), mp("m2", 2.7, "floor", 1.6, swings=1, knockdowns=1),
        swing(2.75), pf(2.8, "m2", "floor", "E", [dict(EAST8, onFloor=True)]), swing(2.85),
        pf(2.9, "m2", "floor", "E", [dict(EAST8, onFloor=True)]),
        md("m2", 3.0, "dead", 0.0, swings=1, knockdowns=1, floors=2), dead(3.0, 8),
        actl("m3", "melee", "accepted", 3.5), mp("m3", 3.6, "face", 0.3), mp("m3", 3.7, "swing", 0.3, swings=1),
        swing(3.75), pf(3.8, "m3", "swing", "E", [EAST9]),
        actl("k1", "stomp", "accepted", 3.85), swing(3.88), pf(3.9, "k1", None, "E", [EAST9]),
        actl("k1", "stomp", "done", 3.95, {"hit": True, "targetDead": True}),
        md("m3", 4.0, "dead", 0.0, swings=1), dead(4.0, 9),
        actl("a1", "attack", "accepted", 5.0), swing(5.25), pf(5.3, "a1", None, "S", [SOUTH5]),
        actl("a1", "attack", "done", 5.5, {"targetDead": True}), dead(5.5, 5),
        actl("s1", "shove", "accepted", 6.0), swing(6.25), pf(6.3, None, None, "S", [SOUTH5]),
        actl("s1", "shove", "done", 6.5, {"knockdown": False}),
        actl("m4", "melee", "accepted", 7.0), mp("m4", 7.1, "shove", 1.0, shoves=1),
        actl("q1", "steer", "accepted", 7.12), swing(7.15),
        pf(7.2, "m4", "shove", "NE", [EAST7]), md("m4", 7.5, "time", 1.0, shoves=1),
        actl("m6", "melee", "accepted", 8.0), mp("m6", 8.1, "face", 1.0), mp("m6", 8.2, "swing", 1.0, swings=1),
        swing(8.25), pf(8.3, "m6", "swing", "W", [EAST4]), mp("m6", 8.5, "back", 1.0, swings=1),
        md("m6", 9.0, "time", 1.0, swings=1),
        pf(9.5, None, None, "S", react="Bite"), pf(9.6, None, None, "S"),
        actl("st1", "steer", "accepted", 9.7), swing(9.75), pf(9.8, "st1", None, "S")]


def cut2_actions():
    return [row("m1", "melee", 1.0, state="failed", reason="superseded", targetId=8, mode="strike"),
            row("m2", "melee", 2.0, targetId=8, mode="strike"), row("m3", "melee", 3.5, targetId=9, mode="strike"),
            row("k1", "stomp", 3.85, targetId=9), row("a1", "attack", 5.0, targetId=5),
            row("s1", "shove", 6.0, targetId=6), row("m4", "melee", 7.0, targetId=7, mode="shove"),
            row("m6", "melee", 8.0, targetId=4, mode="strike"), row("st1", "steer", 9.7)]


def cut2_log():
    """The melee sends with their `melee` {mode, pain} (`dispatch._melee_dispatch`): m1 at 5.0, m2 at 20.0 (at
    STRAIN_HARD: the band's boundary), m3 at 30.0, m4 with the pain unread; no line sends m6."""
    return [aline_(0, 1.0, mv(8, melee={"mode": "strike", "pain": 5.0}), _act("melee", targetId=8, mode="strike")),
            aline_(1, 2.0, mv(8, melee={"mode": "strike", "pain": 20.0}), _act("melee", targetId=8, mode="strike")),
            aline_(2, 3.5, mv(9, melee={"mode": "strike", "pain": 30.0}), _act("melee", targetId=9, mode="strike")),
            aline_(3, 7.0, mv(7, melee={"mode": "shove", "pain": None}), _act("melee", targetId=7, mode="shove"))]


def cut2(log=True, lines=None):
    return grade(cut2_actions(), [], cut2_log() if log else None, cut2_lines() if lines is None else lines)


def aline_(n, t, threat=None, action=None, sent=True, branch="threat", goal=None, need=None, care=None):
    """A decision-log line `t` seconds into the loop with the threat why and, given, the goal, need and care whys."""
    br = {"threat": dict(threat or {})}
    for k, v in (("goal", goal), ("need", need), ("care", care)):
        if v is not None:
            br[k] = v
    return {"action": action, "branch": branch, "gameMin": 600 + n, "inputs": {"nearest": None, "mode": None,
                                                                              "branches": br},
            "sent": sent, "wall": T0 + t}


# ================================================================ the kills, whole
KILLS = {"planner": 3, "planner_ids": [8, 9, 5], "melee": [8, 9], "ladder": [9, 5], "events": 3,
         "event_ids": [8, 9, 5], "agree": True, "source": "act lines"}


def test_the_kills_are_the_union_of_the_ladder_s_targetdead_and_the_melee_s_kill_one_id_once():
    g = cut2()
    assert G.e_kills_whole(T14.artifact(cut2_actions(), []), cut2_lines()) == KILLS
    k = g["kills"]
    assert {key: k[key] for key in KILLS} == KILLS
    assert k["legacy_planner"]["planner"] == 2 and k["legacy_planner"]["planner_ids"] == [9, 5]
    assert k["legacy_planner"] == E.e_kills_9(T14.artifact(cut2_actions(), []), cut2_lines())


def test_the_hits_per_kill_read_over_the_whole_count_the_legacy_kept():
    h = cut2()["hits"]
    assert h["runs"] == 1 and h["kills"] == 3 and h["per_kill"] == 1 / 3 and h["wounds_per_kill"] == 0.0
    assert h["legacy"] == {"kills": 2, "per_kill": 0.5, "wounds_per_kill": 0.0}


def test_the_kills_agree_false_on_a_kill_no_event_reads_and_none_without_lines():
    lines = [ln for ln in cut2_lines() if not (ln.get("kind") == "event" and ln.get("event") == "zombie_dead"
                                                and ln.get("id") == 5)]
    k = G.e_kills_whole(T14.artifact(cut2_actions(), []), lines)
    assert k["planner"] == 3 and k["events"] == 2 and k["agree"] is False
    res = [{"aid": "m2", "type": "melee", "result": {"kill": True}}, {"aid": "a1", "type": "attack",
                                                                      "result": {"targetDead": True}}]
    k0 = G.e_kills_whole(T14.artifact(cut2_actions(), res), [])
    assert k0 == {"planner": 2, "planner_ids": [8, 5], "melee": [8], "ladder": [5], "events": None,
                  "event_ids": None, "agree": None, "source": "loop.results"}


def test_the_kills_read_zero_on_a_clean_log():
    k = G.e_kills_whole(T14.artifact(), [hf(0.0), hf(1.0)])
    assert k == {"planner": 0, "planner_ids": [], "melee": [], "ladder": [], "events": 0, "event_ids": [],
                 "agree": True, "source": "act lines"}


# ================================================================ the facing over every press
def _t(n=0, unread=0, **pts):
    off = {str(i): 0 for i in range(5)}
    off.update({k[1:]: v for k, v in pts.items()})
    return {"n": n, "off_by_points": off, "unread": unread}


MELEE_F = {"swings": _t(4, p0=2, p2=1, p4=1), "shoves": _t(1, p1=1), "stomps": _t(), "floors": _t(2, p0=2)}
LADDER_F = {"swings": _t(1, p0=1), "shoves": _t(1, unread=1), "stomps": _t(1, p0=1), "floors": _t()}
FACING = {"read": True, "presses": 10, "swings": _t(5, p0=3, p2=1, p4=1), "shoves": _t(2, p1=1, unread=1),
          "stomps": _t(1, p0=1), "floors": _t(2, p0=2), "by_source": {"ladder": LADDER_F, "melee": MELEE_F},
          "paired": {"frame": 9, "line": 1}, "other": 0}


def test_the_facing_reads_every_press_on_the_frame_after_its_event_by_source_and_step():
    assert cut2()["facing_all"] == FACING


def test_the_facing_reads_a_melee_press_s_step_off_its_last_progress_line_where_the_frame_carries_no_act():
    lines = cut2_lines()
    i = next(i for i, ln in enumerate(lines) if ln.get("kind") == "frame" and ln["seq"] == 13)    # m1's frame after
    lines[i] = pf(1.3, None, None, "E", [EAST8])
    f = cut2(lines=lines)["facing_all"]
    assert f["by_source"]["melee"]["swings"] == MELEE_F["swings"] and f["paired"] == {"frame": 8, "line": 2}


def test_the_facing_reads_zero_on_quiet_frames_and_unread_without_frames():
    assert grade(log=None, frames=[hf(0.0), hf(1.0)])["facing_all"] == {
        "read": True, "presses": 0, "swings": _t(), "shoves": _t(), "stomps": _t(), "floors": _t(),
        "by_source": {s: {k: _t() for k in ("swings", "shoves", "stomps", "floors")} for s in ("ladder", "melee")},
        "paired": {"frame": 0, "line": 0}, "other": 0}
    assert grade(log=CLEAN)["facing_all"] == {"read": False}


# ================================================================ the swings by the arms' pain
def _band(swings=0, lowered=0, knockdowns=0, killed=0):
    return {"swings": swings, "lowered": lowered, "knockdowns": knockdowns, "killed": killed}


PAIN = {"read": True, "under": _band(1, 1), "at_or_above": _band(2, 1, 1, 1), "unread": _band(1),
        "rows": [{"aid": "m1", "target": 8, "pain": 5.0, "hp0": 2.0, "hp1": 1.6, "lowered": True, "knockdown": False,
                  "killed": False},
                 {"aid": "m2", "target": 8, "pain": 20.0, "hp0": 1.6, "hp1": 1.6, "lowered": False, "knockdown": True,
                  "killed": False},
                 {"aid": "m3", "target": 9, "pain": 30.0, "hp0": 0.3, "hp1": 0.0, "lowered": True, "knockdown": False,
                  "killed": True},
                 {"aid": "m6", "target": 4, "pain": None, "hp0": 1.0, "hp1": 1.0, "lowered": False, "knockdown": False,
                  "killed": False}]}


def test_the_pain_swings_band_each_melee_swing_by_its_send_s_pain_with_its_landing():
    assert cut2()["pain_swings"] == PAIN


def test_the_pain_swings_read_zero_without_a_melee_and_unread_without_a_log():
    assert grade(log=CLEAN, frames=[hf(0.0)])["pain_swings"] == {
        "read": True, "under": _band(), "at_or_above": _band(), "unread": _band(), "rows": []}
    assert cut2(log=False)["pain_swings"] == {"read": False}


def test_the_pain_band_s_boundary_is_strain_hard_at_or_above():
    assert G._band(19.999) == "under" and G._band(20.0) == "at_or_above" and G._band(None) == "unread"
    assert G.STRAIN_HARD == 20.0


# ================================================================ iteration 23's readings, one per rule
R_GOAL = {"door": [5, 5], "target": [5.5, 6.5], "beyond": True, "start_side": "N"}
R_FIGHT = {"door": [7, 3], "target": [7.5, 3.5], "beyond": False, "start_side": "S"}
R_FILL = {"door": [2, 2], "target": [2.5, 3.5], "beyond": True, "start_side": "N"}


def walk(x, y, gait="walk"):
    return _act("walkTo", x=x, y=y, gait=gait)


def rules_log():
    """One block per rule (the why keys as Tasks 1 and 2 committed them): P29-A's three route legs (the goal's, the
    Fight's, the fill's; a holding line and a LootBuilding's string `route` not a leg) and four `route_end`s (two
    uncrossed on the goal, one routing to the run's next way; one crossed on the Fight; one dropped on the fill);
    P29-B's two budget ends, one a `stall`, and a `stuck` end; P29-C's idle walk, a chaser's walk (the rule off) and
    two `close_held`; P29-D's two `dress_finish`; P29-E's `health_near` on a stance, a care pass, a flee and a goal
    pass; P29-F's `finish_lone`; P29-G's three `many_near`; P29-H''s `flee_held_stance`."""
    gw = {"goal": "ExploreToward", "state": "running"}
    end = lambda door, crossed, nxt, dropped: {"door": door, "crossed": crossed, "noted": not crossed,  # noqa: E731
                                               "next": nxt, "dropped": dropped}
    return [
        aline_(0, 1.0, None, walk(5.5, 6.5), branch="goal", goal=dict(gw, route=R_GOAL, leg=[5.5, 6.5])),
        aline_(1, 1.5, None, None, sent=False, branch="goal", goal=dict(gw, route=R_GOAL, leg=[5.5, 6.5])),
        aline_(2, 2.0, {"fight": True, "target": 3, "route": R_FIGHT}, walk(7.5, 3.5)),
        aline_(3, 2.5, None, walk(2.5, 3.5), branch="need", need={"item": None, "fill": {"route": R_FILL,
                                                                                         "walk": [2.5, 3.5]}}),
        aline_(4, 3.0, None, walk(1.5, 1.5), branch="goal", goal={"goal": "LootBuilding", "route": "step",
                                                                  "door": [1, 1]}),
        aline_(5, 3.5, None, None, sent=False, branch="goal", goal=dict(gw, route_end=end([5, 5], False, [5, 5],
                                                                                         False))),
        aline_(6, 4.0, None, None, sent=False, branch="goal", goal=dict(gw, route_end=end([5, 5], False, [8, 5],
                                                                                         False))),
        aline_(7, 4.5, {"fight": True, "route_end": end([7, 3], True, None, False)}, None, sent=False),
        aline_(8, 5.0, None, None, sent=False, branch="need",
               need={"item": None, "fill": {"want": "water_source", "route_end": end([2, 2], False, None, True)}}),
        aline_(9, 5.5, None, None, sent=False, branch="goal",
               goal={"ended": {"reason": "goal budget", "type": "ExploreToward"},
                     "stall": {"moved": 0.3, "target": [10748, 10650]}}),
        aline_(10, 6.0, None, None, sent=False, branch="goal",
               goal={"ended": {"reason": "goal budget", "type": "ExploreToward"}}),
        aline_(11, 6.5, None, None, sent=False, branch="goal", goal={"ended": {"reason": "stuck"}}),
        aline_(12, 7.0, {"target": 3, "pinned": True, "dist": 2.0,
                         "shove_close": {"target": 3, "dist": 2.0, "ticks": 4, "idle": True}}, walk(11.5, 10.5)),
        aline_(13, 7.5, {"target": 3, "pinned": True, "dist": 4.2,
                         "shove_close": {"target": 3, "dist": 4.2, "ticks": 4}}, walk(12.5, 10.5)),
        aline_(14, 8.0, {"fight": True, "close_held": {"target": 11504, "d": 4.284030540414437}}, _act("aim")),
        aline_(15, 8.5, {"fight": True, "close_held": {"target": 11504, "d": 3.9}}, None, sent=False),
        aline_(16, 9.0, {"dress_finish": {"action": "a9", "near": 0}}, None, sent=False),
        aline_(17, 9.5, {"dress_finish": {"action": "a9", "near": 0}}, None, sent=False),
        aline_(18, 10.0, {"fight": True, "health_near": {"near": 0}}, _act("aim")),
        aline_(19, 10.5, {"health_near": {"near": 0}, "held": 1}, _act("bandage", itemId=50, part=4),
               branch="care"),
        aline_(20, 11.0, {"flee": "pair", "health_near": {"near": 0}}, _act("steer")),
        aline_(21, 11.5, {"health_near": {"near": 0}, "held": 0}, None, sent=False, branch="goal"),
        aline_(22, 12.0, {"fight": True, "finish_lone": {"target": 11526}}, None, sent=False),
        aline_(23, 12.5, {"flee": "health", "many_near": {"n": 1}}, _act("steer")),
        aline_(24, 13.0, {"flee": "health", "many_near": {"n": 1}}, None, sent=False),
        aline_(25, 13.5, {"fight": True, "many_near": {"n": 2}}, None, sent=False),
        aline_(26, 14.0, {"fight": True, "flee_held_stance": {"target": 28222, "heading": 14.9, "bearing": 8.3,
                                                              "d": 5.289648927890628}}, _act("aim"))]


READ = {"route_cross": {"read": True, "legs": 3, "by_site": {"goal": 1, "threat": 1, "need": 1}, "ends": 4,
                        "crossed": 1, "uncrossed": 3, "noted": 3, "next_way": 1, "dropped": 1},
        "goal_stall": {"read": True, "ends": 2, "marked": 1, "targets": [[10748, 10650]]},
        "close_idle": {"read": True, "walks": 1, "chasing": 1, "held": 2},
        "dress_finish": {"read": True, "waits": 2},
        "health_near": {"read": True, "lines": 4, "stances": 1, "cares": 1, "flees": 1, "other": 1},
        "finish_lone": {"read": True, "kept": 1, "targets": [11526]},
        "many_near": {"read": True, "lines": 3, "n": {"1": 2, "2": 1}},
        "flee_held": {"read": True, "given_up": 1, "targets": [28222]}}


def test_each_rule_of_iteration_23_reads_its_why_field_s_lines():
    g = grade(log=rules_log(), frames=[hf(0.0)])
    assert {k: g[k] for k in RULES} == READ


def test_each_rule_reads_unread_on_a_log_carrying_none_of_its_lines_and_without_a_log():
    assert all(grade(log=CLEAN)[k] == {"read": False} for k in RULES)
    assert all(grade(log=None)[k] == {"read": False} for k in RULES)
    assert all(cut2()[k] == {"read": False} for k in RULES)


def test_a_rule_reads_when_its_one_line_is_there_alone():
    log = rules_log()
    assert G.e_route_cross(E._Lines(T14.artifact(), [log[7]], []))["ends"] == 1
    assert G.e_goal_stall(E._Lines(T14.artifact(), [log[10]], [])) == {"read": False}   # an end, no stall
    assert G.e_close_idle(E._Lines(T14.artifact(), [log[12]], []))["walks"] == 1
    assert G.e_close_idle(E._Lines(T14.artifact(), [log[13]], [])) == {"read": False}  # the legacy walk alone


# ================================================================ grade_e20 over grade_e19
def to_e19(g, keep_lines=True):
    """grade_e20's dict as grade_e19's: the new keys dropped, `kills` its legacy, `hits` its legacy fields, the name
    and the gate line renamed, the new report lines dropped."""
    g = dict(g)
    for k in NEW:
        g.pop(k)
    g["kills"] = g["kills"]["legacy_planner"]
    if g["hits"].get("read"):
        h = dict(g["hits"])
        h.update(h.pop("legacy"))
        g["hits"] = h
    g["grade"] = "grade_e19"
    if keep_lines:
        g["report_lines"] = [("gate_e19 " + ln[len("gate_e20 "):]) if ln.startswith("gate_e20 ") else ln
                             for ln in g["report_lines"][:-G.N_LINES]]
    return g


@pytest.mark.parametrize("fixture", T14.E13_FIXTURES, ids=lambda f: f.__name__)
def test_grade_e20_reads_every_grade_e19_key_unchanged_on_test_gates_e13_s_fixtures(fixture, monkeypatch):
    seen = T14._captured(monkeypatch, fixture)
    a = T14.artifact(seen["actions"], seen["results"], seen["goals"])
    a["stop"]["reason"] = seen["stop"]
    e19 = G19.grade_e19(a, decision_lines=seen["log"], lines=seen["frames"])
    e20 = G.grade_e20(a, decision_lines=seen["log"], lines=seen["frames"])
    assert e20["grade"] == "grade_e20" and e20["kills"]["legacy_planner"] == e19["kills"]
    assert to_e19(e20) == e19


def test_grade_e20_on_the_cut2_fixture_keeps_every_grade_e19_key():
    a = T14.artifact(cut2_actions(), [])
    e19 = G19.grade_e19(a, decision_lines=cut2_log(), lines=cut2_lines())
    assert to_e19(cut2()) == e19
    assert G.readings_e20({}, None, []) == dict({k: {"read": False} for k in NEW})


def test_report_lines_e20_names_gate_e20_then_the_kills_line_and_one_line_per_reading():
    g = cut2()
    tail = g["report_lines"][-G.N_LINES:]
    assert tail == G.lines_e20(g) and G.N_LINES == 1 + len(NEW)
    for line in tail:
        assert "(iteration 23" in line or "(P29-J" in line, line
    assert all("[reading]" in line for line in tail[:3]) and all("no line read" in line for line in tail[3:])
    assert "[inference]" in tail[1] and "[inference]" in tail[2]   # the facing's act off a line; the landing
    assert tail[0].startswith("kills whole (P29-J) [reading]: 3 kills")
    rules = grade(log=rules_log())["report_lines"][-len(RULES):]
    assert all("[reading]" in line for line in rules)
    off = grade(log=None)["report_lines"][-G.N_LINES:]
    assert "no decision log read" in off[2] and all("no line read" in line for line in off[3:])
    assert "no frames read" in off[1]
    renamed = G.report_lines_e20(dict(g, gate={"pass": True}))
    assert any(line.startswith("gate_e20 ") for line in renamed)
    assert not any(line.startswith("gate_e19 ") for line in renamed)
    assert G.gate_e20([]) == E.gate_e13([])
    assert all(len(line) < 2000 for line in tail)


def test_the_inherited_report_lines_read_the_legacy_kills():
    g = cut2()
    e19 = G19.grade_e19(T14.artifact(cut2_actions(), []), decision_lines=cut2_log(), lines=cut2_lines())
    assert g["report_lines"][:-G.N_LINES] == e19["report_lines"]


# ================================================================ ruling P26-Q: the frozen copies
def _imports(path):
    tree = ast.parse(open(path, encoding="utf-8").read())
    names = []
    for n in ast.walk(tree):
        if isinstance(n, ast.ImportFrom):
            names.append(n.module or "")
            names += ["%s.%s" % (n.module, a.name) for a in n.names]
        elif isinstance(n, ast.Import):
            names += [a.name for a in n.names]
    return names


def test_the_module_imports_no_live_planner_or_world_name_and_holds_its_own_copies():
    names = _imports(G.__file__)
    assert not any(m.startswith(("agent.base.planner", "agent.base.world")) for m in names), names
    ns = vars(G)
    assert ns["SWING_TYPES"] == ("attack", "aim", "shove", "stomp") and ns["STRAIN_HARD"] == 20.0
    assert ns["PRESS_STEPS"] == ("swing", "shove", "stomp", "floor") and ns["MELEE"] == "melee"
    assert ns["LADDER_STRIKES"] == {"attack": "swings", "shove": "shoves", "stomp": "stomps"}
    assert ns["MELEE_STRIKES"] == {"swing": "swings", "shove": "shoves", "stomp": "stomps", "floor": "floors"}
    assert RULES == ("route_cross", "goal_stall", "close_idle", "dress_finish", "health_near", "finish_lone",
                     "many_near", "flee_held")
    assert not any(getattr(v, "__module__", "").startswith(("agent.base.planner", "agent.base.world"))
                   for v in ns.values())


# ================================================================ the mutants
def _mutated(name, edit):
    """grades/e20.py's source with `edit` applied inside the top-level def `name` only, executed as a module copy."""
    src = open(G.__file__, encoding="utf-8").read()
    head = "\ndef %s(" % name
    start = src.index(head)
    nxt = [i for i in (src.find("\ndef ", start + 5), src.find("\nclass ", start + 5)) if i >= 0]
    end = min(nxt) if nxt else len(src)
    new = edit(src[start:end])
    assert new != src[start:end], (name, "the mutant changed nothing")
    ns = {"__name__": "e20_mutant"}
    exec(compile(src[:start] + new + src[end:], "e20_mutant", "exec"), ns)    # noqa: S102 - a scratch copy
    return ns


K = lambda: G.e_kills_whole(T14.artifact(cut2_actions(), []), cut2_lines())    # noqa: E731
F = lambda: cut2()["facing_all"]                                              # noqa: E731
P = lambda: cut2()["pain_swings"]                                             # noqa: E731
RL = lambda k: grade(log=rules_log())[k]                                      # noqa: E731

MUTANTS = [
    ("e_kills_whole", lambda b: b.replace("if zid in seen:", "if False:"), lambda: K() == KILLS),
    ("e_kills_whole", lambda b: b.replace('res.get("kill") is True', 'res.get("end") is not None'),
     lambda: K() == KILLS),
    ("e_kills_whole", lambda b: b.replace("set(ids) == set(events)", "True"),
     lambda: G.e_kills_whole(T14.artifact(cut2_actions(), []), _no_dead_5())["agree"] is False),
    ("_whole", lambda b: b.replace("_per(runs, n)", "_per(runs, n + 1)"), lambda: cut2()["hits"]["per_kill"] == 1 / 3),
    ("e_facing_all", lambda b: b.replace("elif k == \"frame\" and pend:", "elif k == \"frame\" and False:"),
     lambda: F() == FACING),
    ("e_facing_all", lambda b: b.replace("own if own is not None else inferred", "inferred"), lambda: F() == FACING),
    ("e_facing_all", lambda b: b.replace("_last_press(before, aid, step)", "step"),
     lambda: F()["by_source"]["melee"]["swings"] == MELEE_F["swings"]
     and cut2(lines=_no_act_after_m1())["facing_all"]["by_source"]["melee"]["swings"] == MELEE_F["swings"]),
    ("_band", lambda b: b.replace("pain >= STRAIN_HARD", "pain > STRAIN_HARD"), lambda: P() == PAIN),
    ("e_pain_swings", lambda b: b.replace("st == SWING_STEP and st != prev", "st == SWING_STEP"),
     lambda: P()["under"]["swings"] == 1),
    ("_landing", lambda b: b.replace('E._n(r1.get("knockdowns")) > E._n(r0.get("knockdowns"))', "False"),
     lambda: P()["at_or_above"]["knockdowns"] == 1),
    ("_landing", lambda b: b.replace("h1 < h0", "h1 <= h0"), lambda: P()["at_or_above"]["lowered"] == 1),
    ("e_route_cross", lambda b: b.replace("_target_of(ln) == _xy(r.get(\"target\"))", "True"),
     lambda: RL("route_cross")["legs"] == 3),
    ("e_route_cross", lambda b: b.replace("nxt is not None and nxt != e.get(\"door\")", "nxt is not None"),
     lambda: RL("route_cross")["next_way"] == 1),
    ("e_goal_stall", lambda b: b.replace("== BUDGET", "is not None"), lambda: RL("goal_stall")["ends"] == 2),
    ("e_close_idle", lambda b: b.replace('sc.get("idle") is True', "True"), lambda: RL("close_idle")["walks"] == 1),
    ("e_health_near", lambda b: b.replace('ln.get("branch") == "care"', 'ln.get("branch") != "threat"'),
     lambda: RL("health_near")["cares"] == 1),
    ("e_many_near", lambda b: b.replace('str(E._n(m.get("n")))', '"n"'), lambda: RL("many_near")["n"] == READ[
        "many_near"]["n"]),
]


def _no_dead_5():
    return [x for x in cut2_lines() if x.get("id") != 5 or x.get("event") != "zombie_dead"]


def _no_act_after_m1():
    lines = cut2_lines()
    i = next(i for i, ln in enumerate(lines) if ln.get("kind") == "frame" and ln["seq"] == 13)
    lines[i] = pf(1.3, None, None, "E", [EAST8])
    return lines


@pytest.mark.parametrize("n", range(len(MUTANTS)), ids=lambda n: "%s-%d" % (MUTANTS[n][0], n))
def test_a_mutant_of_each_reading_fails_its_fixture(n, monkeypatch):
    name, edit, holds = MUTANTS[n]
    assert holds(), "the fixture must hold on the real module"
    monkeypatch.setattr(G, name, _mutated(name, edit)[name])
    try:
        survives = holds()
    except Exception:       # a mutant that raises on the fixture is caught by it
        survives = False
    assert not survives, "the mutant of %s survives its fixture" % name


# ================================================================ the real checks: E22
def _committed(path, name):
    text = open(os.path.join(path, name), encoding="utf-8").read()
    i = text.index("\n{\n")
    return text[:i + 1].splitlines(), json.loads(text[i:])


def _e22():
    p = os.path.join(E22, "e_day_22.json")
    if not os.path.isfile(p):
        pytest.skip("%s is not checked out" % E22)
    return p


def test_grade_e20_on_e22_reads_the_four_melee_kills_whole_with_the_events_agreeing():
    """E22's four kills are each a melee's done `kill` (the T88 write-up's section 1): `kills.planner` 4 where the
    frozen read took 0, the events agreeing; the hits 14 over 4."""
    p = _e22()
    g = G.grade_e20(EG20.load(p), None, EG20.load_log(p), state_dir=EG20._dir(p))
    k = g["kills"]
    assert (k["planner"], k["events"], k["agree"], k["ladder"]) == (4, 4, True, [])
    assert sorted(k["melee"]) == sorted(k["event_ids"]) == sorted(k["planner_ids"]) == [11479, 11516, 11531, 11602]
    assert k["legacy_planner"]["planner"] == 0 and g["hits"]["runs"] == 14 and g["hits"]["per_kill"] == 3.5
    assert g["hits"]["legacy"]["per_kill"] is None


def test_grade_e20_on_e22_reads_every_melee_press_facing_and_the_swings_under_the_pain():
    """The 46 swing events: 44 melee presses (8 swings, 27 shoves, 5 stomps, 4 floor swings: the T88 write-up's
    section 4, each 0 points off), the ladder's one stomp a319 (0 off) and a steer's shove event (no strike); the
    eight swings in the `unread` band (E22 ran at bd07b731, before P28-H's `melee` {mode, pain} on the send line,
    a7595529: no send line carries it), seven lowering their target, a40's knocking 11479 down and a48's second
    killing 11531 (section 1)."""
    p = _e22()
    g = G.grade_e20(EG20.load(p), None, EG20.load_log(p), state_dir=EG20._dir(p))
    f, m = g["facing_all"], g["facing_all"]["by_source"]["melee"]
    assert f["presses"] == 45 and f["other"] == 0
    assert {k: (m[k]["n"], m[k]["off_by_points"]["0"], m[k]["unread"]) for k in m} == {
        "swings": (8, 8, 0), "shoves": (27, 27, 0), "stomps": (5, 5, 0), "floors": (4, 4, 0)}
    assert f["by_source"]["ladder"]["stomps"]["off_by_points"]["0"] == 1 and f["swings"]["n"] == 8
    ps = g["pain_swings"]
    assert ps["unread"] == _band(8, 7, 1, 1) and ps["at_or_above"] == _band() and ps["under"] == _band()
    assert [(r["aid"], r["knockdown"], r["killed"]) for r in ps["rows"] if r["knockdown"] or r["killed"]] == [
        ("a40", True, False), ("a48", False, True)]


def test_grade_e20_on_e22_reads_iteration_23_s_rules_unread_and_keeps_every_grade_e19_key():
    p = _e22()
    g = G.grade_e20(EG20.load(p), None, EG20.load_log(p), state_dir=EG20._dir(p))
    assert g["grade"] == "grade_e20" and all(g[k] == {"read": False} for k in RULES)
    mine = json.loads(json.dumps(EG20.finite(g), sort_keys=True, allow_nan=False))
    lines, committed = _committed(E22, "e_grade.txt")
    assert to_e19(mine) == committed and g["report_lines"][:-G.N_LINES] == lines


def test_e_grade_20_prints_the_committed_e_grade_txt_s_lines_then_the_new_ones():
    """`e_grade_20.py` on the committed E22 artifact: the committed `e_grade.txt`'s report lines (CRLF folded), then
    the new lines, then the JSON whose inherited keys equal the committed."""
    p = _e22()
    script = os.path.join(TESTING, "agent", "drivers", "e_grade_20.py")
    r = subprocess.run([sys.executable, script, p], capture_output=True, cwd=TESTING)
    assert r.returncode == 0
    text = r.stdout.decode("utf-8").replace("\r\n", "\n")
    i = text.index("\n{\n")
    printed, got = text[:i + 1].splitlines(), json.loads(text[i:])
    want_lines, want = _committed(E22, "e_grade.txt")
    assert printed[:-G.N_LINES] == want_lines and len(printed) == len(want_lines) + G.N_LINES
    assert got["grade"] == "grade_e20" and printed[-G.N_LINES:] == got["report_lines"][-G.N_LINES:]
    assert to_e19(got) == want and got["kills"]["planner"] == 4


def test_e_grade_20_refuses_an_argument_it_does_not_define():
    """Read statically (CLAUDE.md section 5): its main answers usage, exit 2, on no path or more than two outside
    `--chain`."""
    src = open(EG20.__file__, encoding="utf-8").read()
    assert "if not paths or (not chain and len(paths) > 2):" in src and "return 2" in src
    assert "from agent.base.grades.e20 import gate_e20, grade_e20, report_lines_e20" in src
    body = src[src.index('"""', 3):]
    assert "usage: e_grade_20.py" in src and "e19" not in body and "_e19" not in body
