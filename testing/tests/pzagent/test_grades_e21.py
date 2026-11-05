"""base/grades/e21.py (Plan 30 Task 4), offline: `grade_e21` and its nine readings (the hits as the union of the
frames' reaction runs and the reflex's `hit` steps, the kills matched to the press before each `zombie_dead` event, and
one reading per rule of survival iteration 24, `T14_SWITCHES`: the sneak P30-D, the goal wait P30-B, the door P30-C,
the swing close P30-A, the still P30-E, the dress ride P30-F, with the standing minutes), each on a fabricated log
where it counts, the unread case, a mutant per reading, every `grade_e20` key unchanged under `grade_e21` on
test_gates_e13's fixtures and on test_grades_e20's cut 2 fixture, the module's frozen copies (ruling P26-Q), and the
real checks on F14 (`f_goals_15-20261105-092752`) and E23 (`e_day_23-20261105-095110`): the union 8 and 6 (the T92
write-up's eight attacks that landed, F14's guide section 1), F14's seventh kill 32434 matched to the ladder's floor
attack a59 (the kills 7 with the events agreeing) and E23's one, the twelve standing stretches of Plan 29's desk read
`pause-and-door-read.md` section A.1 (eight on F14, four on E23) and its 181 pending lines (90.1 s) with a zombie
within 10 tiles, iteration 24's readings unread (both sessions predate the rules), and every inherited key equal to
the committed `e_grade.txt`'s, through the function and through `e_grade_21.py`."""
import ast
import functools
import json
import math
import os
import subprocess
import sys

import pytest

from agent.base import gates_e as E
from agent.base.grades import e20 as G20
from agent.base.grades import e21 as G
from agent.drivers import e_grade_21 as EG21
from . import test_grades_e14 as T14
from . import test_grades_e20 as T20
from .test_gates_e7 import T0
from .test_gates_e13 import _act
from .test_grades_e14 import actl, row
from .test_grades_e17 import CLEAN
from .test_grades_e18 import hf
from .test_grades_e19 import dead

HERE = os.path.dirname(os.path.abspath(__file__))
TESTING = os.path.dirname(os.path.dirname(HERE))
F14 = os.path.join(TESTING, "artifacts", "f_goals_15-20261105-092752")
E23 = os.path.join(TESTING, "artifacts", "e_day_23-20261105-095110")
NEW = G.NEW
RULES = G.RULES


def grade(actions=(), results=(), log=None, frames=()):
    return G.grade_e21(T14.artifact(actions, results), decision_lines=log, lines=list(frames))


def fr(t, react="", zombies=(), x=10.0, y=10.0, sneaking=False, gm=600, act=None, health=100.0, seq=None):
    """A frame `t` seconds into the loop at (x, y): the reaction, the zombies (each {id, x, y, ...}), `me.sneaking`
    (None drops the field: a frame before PZA/1.9), the game minute, the act group and the health."""
    f = hf(t, react, health=health, zombies=zombies, x=x, y=y)
    if sneaking is None:
        f["me"].pop("sneaking", None)
    else:
        f["me"]["sneaking"] = sneaking
    f["gameMin"], f["act"] = gm, act
    if seq is not None:
        f["seq"] = seq
    return f


def z(zid, x, y, **kw):
    return dict({"id": zid, "x": x, "y": y, "hasTarget": False}, **kw)


def mp(aid, t, step, hp, **counts):
    return T20.mp(aid, t, step, hp, **counts)


def swing_ev(t):
    return T20.swing(t)


def line(n, t, threat=None, action=None, sent=True, branch="threat", goal=None, x=10.0, y=10.0, sneak=None):
    """test_grades_e20's decision line with the inputs' position and, given, `inputs.sneak`."""
    ln = T20.aline_(n, t, threat, action, sent=sent, branch=branch, goal=goal)
    ln["inputs"].update(x=x, y=y)
    if sneak is not None:
        ln["inputs"]["sneak"] = sneak
    return ln


# ================================================================ the hits, the union
def union_lines():
    """Frames every 0.1 s from 0.0 to 9.0; three reaction runs: A `Bite` 1.0-1.2, B `BiteLEFT` 5.0-5.1, C `Bite`
    7.0-7.1. m1's `hit` step at 1.05 inside A (joined) and its heartbeat repeat at 1.6 (one run of consecutive `hit`
    steps); m2's `hit` at 3.0 and again at 3.55 after a `back` (two runs, no reaction: each alone); m3's `hit` at 6.9,
    on the wall of the frame before C's first (joined: the bound is inclusive), and at 8.5, past the frame after C's
    last (7.2: alone)."""
    react = {k: "Bite" for k in (10, 11, 12, 70, 71)}
    react.update({50: "BiteLEFT", 51: "BiteLEFT"})
    frames = [(k / 10.0, fr(k / 10.0, react.get(k, ""), seq=1000 + k)) for k in range(91)]
    acts = [(0.5, actl("m1", "melee", "accepted", 0.5)), (0.8, mp("m1", 0.8, "swing", 2.0, swings=1)),
            (1.05, mp("m1", 1.05, "hit", 2.0, swings=1, hits=1)), (1.6, mp("m1", 1.6, "hit", 2.0, swings=1, hits=1)),
            (2.0, mp("m1", 2.0, "stand", 2.0, swings=1, hits=1)),
            (2.5, actl("m1", "melee", "done", 2.5, {"end": "time"})),
            (2.6, actl("m2", "melee", "accepted", 2.6)), (2.8, mp("m2", 2.8, "swing", 2.0, swings=1)),
            (3.0, mp("m2", 3.0, "hit", 2.0, swings=1, hits=1)), (3.3, mp("m2", 3.3, "back", 2.0, swings=1, hits=1)),
            (3.55, mp("m2", 3.55, "hit", 2.0, swings=1, hits=2)),
            (4.0, actl("m2", "melee", "done", 4.0, {"end": "time"})),
            (6.5, actl("m3", "melee", "accepted", 6.5)), (6.9, mp("m3", 6.9, "hit", 2.0, hits=1)),
            (7.5, mp("m3", 7.5, "stand", 2.0, hits=1)), (8.5, mp("m3", 8.5, "hit", 2.0, hits=2)),
            (9.0, actl("m3", "melee", "done", 9.0, {"end": "time"}))]
    return [ln for _, ln in sorted(frames + acts, key=lambda p: p[0])]


def union_read(kills=3):
    lines = union_lines()
    return G.e_hits_union(E._frame_index(lines)[1], lines, kills)


def test_the_union_joins_a_hit_step_within_a_frame_interval_of_a_run_and_counts_the_rest_once():
    u = union_read()
    assert (u["read"], u["runs"], u["steps"], u["joined"], u["union"], u["kills"]) == (True, 3, 5, 2, 6, 3)
    assert u["per_kill_union"] == 2.0
    assert [(r["source"], r["aid"], r["kind"]) for r in u["rows"]] == [
        ("both", "m1", "Bite"), ("step", "m2", None), ("step", "m2", None), ("reaction", None, "BiteLEFT"),
        ("both", "m3", "Bite"), ("step", "m3", None)]
    assert [r["seq"] for r in u["rows"]] == [1010, 30, 35, 1050, 69, 85]   # a joined row's seq the earlier line's


def test_the_union_reads_unread_without_frames_and_none_a_kill_at_zero():
    assert G.e_hits_union([], union_lines(), 3) == {"read": False}
    u = union_read(kills=0)
    assert u["union"] == 6 and u["per_kill_union"] is None
    q = G.e_hits_union([fr(0.0), fr(0.1)], [], 0)
    assert (q["runs"], q["steps"], q["union"], q["rows"]) == (0, 0, 0, [])


# ================================================================ the kills, matched to the press
def W(t):
    return fr(t, "", zombies=(), seq=None)


def kills_lines(all_match=False):
    """In log order, the character at (10, 10). m1's done `kill` of 8 (the whole read). The ladder's attack a1 at 5:
    its swing event, then three frames, the third listing 6 fallen at 0.4 tiles (the weapon's reach 1.2), then 6's
    death: matched to a1. The shove s1 at 7, 7 at 2.0 tiles on the frame after its swing event (beyond K.SHOVE_R 1.5),
    then 7's death: unmatched. The stomp k1 at 9 (9 at 0.3), eleven frames, then 9's death: past MATCH_FRAMES,
    unmatched. The finish melee m2 at 10 (its reach 1.3): its floor step's swing event, the frame after listing 11 at
    0.3, 11's death: matched to the melee's floor step. The shove-mode m3 at 12: its shove step's swing event, 12 at
    0.2, 12's death: a melee shove is no killing press, unmatched. With `all_match` only 8, 6 and 11 die."""
    out = [actl("m1", "melee", "accepted", 10.0), mp("m1", 10.1, "swing", 1.0, swings=1), swing_ev(10.15),
           fr(10.2, zombies=[z(8, 11.0, 10.0)], act={"aid": "m1", "state": "accepted", "step": "swing"}),
           actl("m1", "melee", "done", 10.3, dict({k: 0 for k in ("swings",)}, end="dead", kill=True)),
           dead(10.35, 8),
           actl("a1", "attack", "accepted", 11.0), swing_ev(11.05),
           fr(11.1, zombies=[z(5, 11.0, 10.0), z(6, 10.4, 10.0, onFloor=True)],
              act={"aid": "a1", "state": "accepted", "step": None}),
           fr(11.2, zombies=[z(6, 10.4, 10.0, onFloor=True)]), fr(11.3, zombies=[z(6, 10.4, 10.0, onFloor=True)]),
           dead(11.35, 6), actl("a1", "attack", "done", 11.4, {"targetDead": False}),
           actl("s1", "shove", "accepted", 12.0), swing_ev(12.05),
           fr(12.1, zombies=[z(7, 12.0, 10.0)], act={"aid": "s1", "state": "accepted", "step": None}),
           fr(12.2, zombies=[z(7, 12.0, 10.0)])]
    if not all_match:
        out.append(dead(12.25, 7))
    out += [actl("s1", "shove", "done", 12.3, {"knockdown": False}),
            actl("k1", "stomp", "accepted", 13.0), swing_ev(13.05),
            fr(13.1, zombies=[z(9, 10.3, 10.0, onFloor=True)], act={"aid": "k1", "state": "accepted", "step": None})]
    out += [fr(13.1 + k / 10.0, zombies=[z(9, 10.3, 10.0, onFloor=True)]) for k in range(1, 11)]
    if not all_match:
        out.append(dead(14.15, 9))
    out += [actl("k1", "stomp", "done", 14.2, {"hit": True, "targetDead": False}),
            actl("m2", "melee", "accepted", 15.0), mp("m2", 15.1, "floor", 1.0, floors=1), swing_ev(15.15),
            fr(15.2, zombies=[z(10, 11.0, 10.0, onFloor=True), z(11, 10.3, 10.0, onFloor=True)],
               act={"aid": "m2", "state": "accepted", "step": "floor"}),
            dead(15.25, 11), actl("m2", "melee", "done", 15.5, {"end": "time", "kill": False}),
            actl("m3", "melee", "accepted", 16.0), mp("m3", 16.1, "shove", 1.0, shoves=1), swing_ev(16.15),
            fr(16.2, zombies=[z(12, 10.2, 10.0)], act={"aid": "m3", "state": "accepted", "step": "shove"})]
    if not all_match:
        out.append(dead(16.25, 12))
    out.append(actl("m3", "melee", "done", 16.5, {"end": "time", "kill": False}))
    return out


def kills_actions():
    return [row("m1", "melee", 10.0, targetId=8, mode="strike", reach=0.0), row("a1", "attack", 11.0, targetId=5),
            row("s1", "shove", 12.0, targetId=7), row("k1", "stomp", 13.0, targetId=9),
            row("m2", "melee", 15.0, targetId=10, mode="finish", reach=1.3),
            row("m3", "melee", 16.0, targetId=12, mode="shove", reach=0.0)]


def kills_read(all_match=False):
    return G.e_kills_matched(T14.artifact(kills_actions(), []), kills_lines(all_match))


def test_the_kills_match_an_unnamed_death_to_the_last_killing_press_within_match_frames_at_its_reach():
    k = kills_read()
    assert (k["whole"], k["whole_ids"], k["planner"], k["planner_ids"]) == (1, [8], 3, [8, 6, 11])
    assert (k["events"], k["event_ids"], k["unmatched"], k["agree"]) == (6, [8, 6, 7, 9, 11, 12], [7, 9, 12], False)
    m = [(r["id"], r["aid"], r["type"], r["step"], r["source"], r["frames_before"], r["reach"]) for r in k["matched"]]
    assert m == [(6, "a1", "attack", None, "ladder", 3, 1.2), (11, "m2", "melee", "floor", "melee", 1, 1.3)]
    assert [round(r["d"], 6) for r in k["matched"]] == [0.4, 0.3]
    assert k["by_source"] == {"ladder": 1, "melee": 1}
    assert {key: k[key] for key in ("melee", "ladder", "source")} == {"melee": [8], "ladder": [], "source": "act lines"}


def test_the_kills_agree_once_every_death_is_matched_and_read_the_loop_results_without_lines():
    k = kills_read(all_match=True)
    assert (k["planner"], k["planner_ids"], k["unmatched"], k["agree"]) == (3, [8, 6, 11], [], True)
    res = [{"aid": "m1", "type": "melee", "result": {"kill": True}}]
    k0 = G.e_kills_matched(T14.artifact(kills_actions(), res), [])
    assert (k0["planner"], k0["matched"], k0["unmatched"], k0["agree"], k0["source"]) == (
        1, [], None, None, "loop.results")


def test_the_press_reach_is_the_presses_own():
    f = fr(0.0)
    assert G._reach("attack", None, None, f) == 1.2 and G._reach("shove", None, None, f) == G.SHOVE_R == 1.5
    assert G._reach("stomp", None, None, f) == G.STOMP_R == 0.5 and G._reach("melee", "stomp", 1.3, f) == 0.5
    assert G._reach("melee", "swing", 1.3, f) == 1.3 and G._reach("melee", "floor", 0.0, f) == 1.2
    assert G._reach("melee", "shove", 1.3, f) == 1.5 and G._reach("aim", None, None, f) is None


# ================================================================ P30-D, the sneak
def sneak_lines():
    """Twelve frames 0.5 s apart from 20.0: k0-k5 sneaking (game minutes 600 and 601), k6-k8 upright (602), k9-k11
    sneaking (603). The walks: w1 at a walk while sneaking, 1 tile in 1 s; w2 at a walk while sneaking, 2 tiles in 1 s;
    w3 at a run, upright; w4 at a run while sneaking, 3 tiles in 1 s. The zombies: 21 idle within SNEAK_R on every
    sneaking frame (passed); 22 idle on k0-k2, chasing from k3 (`state` walktoward: the first target change, 4 tiles
    off); 23 at 9.5 tiles or more (never near); 24 chasing on the upright frames only; 25 chasing from its first
    sneaking frame (k9-k11)."""
    xs = [10.0, 10.5, 11.0, 11.0, 12.0, 13.0, 13.0, 13.0, 13.0, 13.0, 14.5, 16.0]
    snk = [True] * 6 + [False] * 3 + [True] * 3
    gms = [600, 600, 600, 600, 601, 601, 602, 602, 602, 603, 603, 603]
    frames = []
    for k in range(12):
        t = 20.0 + k * 0.5
        zs = [z(23, 10.0, 19.5)]
        if snk[k]:
            zs += [z(21, 14.0, 10.0), z(22, 15.0, 10.0, hasTarget=k >= 3, state="walktoward" if k >= 3 else "idle")]
        else:
            zs.append(z(24, 13.5, 10.0, hasTarget=True))
        if k >= 9:
            zs.append(z(25, 13.0, 10.0, hasTarget=True))
        frames.append((t, fr(t, zombies=zs, x=xs[k], sneaking=snk[k], gm=gms[k], seq=2000 + k)))
    acts = [(20.0, actl("w1", "walkTo", "accepted", 20.0)), (21.0, actl("w1", "walkTo", "done", 21.0)),
            (21.5, actl("w2", "walkTo", "accepted", 21.5)), (22.5, actl("w2", "walkTo", "done", 22.5)),
            (23.0, actl("w3", "walkTo", "accepted", 23.0)), (24.0, actl("w3", "walkTo", "done", 24.0)),
            (24.5, actl("w4", "walkTo", "accepted", 24.5)), (25.5, actl("w4", "walkTo", "done", 25.5))]
    return [ln for _, ln in sorted(frames + acts, key=lambda p: (p[0], p[1].get("kind") != "act"))]


def sneak_actions():
    return [row("w1", "walkTo", 20.0, x=11.0, y=10.0, gait="walk"),
            row("w2", "walkTo", 21.5, x=13.0, y=10.0, gait="walk"),
            row("w3", "walkTo", 23.0, x=13.0, y=10.0, gait="run"),
            row("w4", "walkTo", 24.5, x=16.0, y=10.0, gait="run")]


def sneak_log():
    return [line(0, 20.0, None, _act("sneak", on=True), sneak={"on": True, "near": 2, "sent": True, "deferred": None}),
            line(1, 22.0, None, None, sent=False, sneak={"on": True, "near": 2}),
            line(2, 23.0, None, _act("sneak"), sneak={"on": False, "near": 1, "sent": True, "deferred": "melee"})]


def sneak_read(log=True):
    lines = sneak_lines()
    a = T14.artifact(sneak_actions(), [])
    L = E._Lines(a, sneak_log() if log else [], lines)
    return G.e_sneak(a, L if log else None, lines, E._frame_index(lines)[1])


def test_the_sneak_reads_the_minutes_the_walk_s_speed_and_the_zombies_passed_and_noticed():
    s = sneak_read()
    assert (s["read"], s["frames"], s["minutes"], s["seconds"]) == (True, 9, 3, 4.0)
    assert s["walk_speed"] == 1.5
    assert [(r["aid"], r["gait"], r["tiles"], r["s"], r["speed"]) for r in s["legs"]] == [
        ("w1", "walk", 1.0, 1.0, 1.0), ("w2", "walk", 2.0, 1.0, 2.0), ("w4", "run", 3.0, 1.0, 3.0)]
    assert (s["near"], s["passed"], s["noticed"], s["chasing"]) == (3, [21], [22], [25])
    assert s["first_change"] == {"seq": 2003, "id": 22, "d": 4.0, "state": "walktoward"}
    assert s["postures"] == {"on": 1, "off": 1}


def test_the_sneak_reads_unread_on_frames_before_pza_1_9_and_counts_no_minute_upright():
    lines = [fr(0.0, sneaking=None), fr(0.5, sneaking=None)]
    assert G.e_sneak(T14.artifact(), None, lines, E._frame_index(lines)[1]) == {"read": False}
    assert G.e_sneak(T14.artifact(), None, [], []) == {"read": False}
    up = [fr(0.0, zombies=[z(1, 12.0, 10.0)]), fr(0.5, zombies=[z(1, 12.0, 10.0)])]
    s = G.e_sneak(T14.artifact(), None, up, E._frame_index(up)[1])
    assert (s["read"], s["frames"], s["minutes"], s["seconds"], s["near"], s["walk_speed"]) == (
        True, 0, 0, 0.0, 0, None)
    assert s["postures"] is None and sneak_read(log=False)["postures"] is None


# ================================================================ P30-B, the goal wait
def goal_log(rule=True):
    """Lines 0.5 s apart from 30.0. L0 takes an ExploreToward to (12, 10) at (10, 10) (a 2-tile hop); L1-L4 pending,
    unmoved, a zombie at 5 tiles; L5 takes one to (22, 10) (12 tiles), extended from (14, 10) (8 tiles); L6-L8
    pending with the continued walk toward `edge` (sent on L6), moving, the zombie at 4.5 to 3 tiles; L9-L10 pending,
    unmoved (0 and 0.1 tiles), the zombie at 18 tiles. Without `rule` the two why fields are absent."""
    et = {"goal": "ExploreToward", "proposed": "ExploreToward", "state": "running"}
    cont = {"target": [22.5, 10.5], "source": "edge"} if rule else None
    pend = lambda: {"pending": True, "proposed": None, "ended": None, "refused": None}    # noqa: E731
    out = [line(0, 30.0, None, _act("walkTo", x=12.0, y=10.0, gait="walk"), branch="goal",
                goal=dict(et, args={"x": 12, "y": 10}))]
    out += [line(n, 30.0 + 0.5 * n, None, None, sent=False, branch="goal", goal=pend()) for n in range(1, 5)]
    g5 = dict(et, args={"x": 22, "y": 10})
    if rule:
        g5["hop_extended"] = {"from": [14, 10], "to": [22, 10]}
    out.append(line(5, 32.5, None, _act("walkTo", x=22.0, y=10.0, gait="walk"), branch="goal", goal=g5))
    for n, x in ((6, 10.5), (7, 11.0), (8, 12.0), (9, 12.0), (10, 12.1)):
        g = pend()
        if rule and n <= 8:
            g["goal_continue"] = dict(cont)
        sent = rule and n == 6
        out.append(line(n, 30.0 + 0.5 * n, None, _act("walkTo", x=22.5, y=10.5, gait="walk") if sent else None,
                        sent=sent, branch="goal", goal=g, x=x))
    return out


def goal_frames():
    xs = [10.0] * 6 + [10.5, 11.0, 12.0, 12.0, 12.1]
    zx = [15.0] * 9 + [30.0, 30.0]
    return [fr(30.0 + 0.5 * n, zombies=[z(40, zx[n], 10.0)], x=xs[n]) for n in range(11)]


def goal_read(rule=True):
    return G.e_goal_wait(E._Lines(T14.artifact(), goal_log(rule), goal_frames()))


WAIT = {"lines": 9, "runs": 2, "seconds": 4.5, "unmoved": 6, "unmoved_near": 4, "unmoved_near_s": 2.0,
        "near_runs": {"runs": 2, "lines": 9, "s": 4.5}, "hops": [2.0, 12.0]}


def test_the_goal_wait_reads_the_pending_lines_the_stands_near_a_zombie_the_hops_and_the_rule_s_lines():
    g = goal_read()
    assert g["read"] is True and {k: g[k] for k in WAIT} == WAIT
    assert g["continued"] == {"lines": 3, "sent": 1, "by_source": {"edge": 3}}
    assert g["extended"] == {"lines": 1, "lengths": [8.0]}


def test_the_goal_wait_keeps_its_measures_unread_without_the_rule_s_lines_and_reads_unread_without_a_log():
    g = goal_read(rule=False)
    assert g["read"] is False and {k: g[k] for k in WAIT} == WAIT
    assert g["continued"] == {"lines": 0, "sent": 0, "by_source": {}} and g["extended"] == {"lines": 0, "lengths": []}
    assert G.e_goal_wait(None) == {"read": False}


# ================================================================ P30-C, the door held
def door_log():
    """A `stance_open` at the door (5, 5) with its post, open and meet steps, then three `leave`s (a locked gate, a
    door with two behind, a window)."""
    dh = lambda door, kind, n, dec: {"door": door, "kind": kind, "n_behind": n, "decision": dec}   # noqa: E731
    return [line(0, 40.0, {"fight": True, "door_held": dh([5, 5], "door", 1, "stance_open"), "door_step": "post"},
                 _act("aim")),
            line(1, 40.5, {"fight": True, "door_step": "open"}, _act("interact")),
            line(2, 41.0, {"fight": True, "door_step": "meet"}, _act("aim")),
            line(3, 42.0, {"door_held": dh([7, 3], "locked gate", 1, "leave")}, None, sent=False),
            line(4, 43.0, {"door_held": dh([9, 9], "door", 2, "leave")}, None, sent=False),
            line(5, 44.0, {"door_held": dh([2, 2], "window", 1, "leave")}, None, sent=False)]


def door_lines():
    return [dead(39.0, 33), dead(70.0, 31), dead(110.0, 32)]


def test_the_door_held_reads_the_decisions_by_kind_the_steps_and_the_kills_after_a_stance_open():
    lines = door_lines()
    d = G.e_door_held(E._Lines(T14.artifact(), door_log(), lines), lines)
    assert d == {"read": True, "lines": 4, "by_kind": {"door": 2, "locked gate": 1, "window": 1},
                 "by_decision": {"stance_open": 1, "leave": 3},
                 "by": {"door stance_open": 1, "locked gate leave": 1, "door leave": 1, "window leave": 1},
                 "doors": [[5, 5], [7, 3], [9, 9], [2, 2]], "steps": {"post": 1, "open": 1, "meet": 1},
                 "kills_after_open": 1, "kill_ids": [31]}


def test_the_door_held_reads_unread_without_its_lines():
    assert G.e_door_held(E._Lines(T14.artifact(), CLEAN, []), []) == {"read": False}
    assert G.e_door_held(None, door_lines()) == {"read": False}


# ================================================================ P30-A, the swing close
def close_lines(rule=True):
    """m1 (strike): a swing that lowered (2.0 to 1.5) then its back step, with a bite (a reaction run at 50.6) in it;
    a stand, a swing that did nothing pressed again, then a back step (within K.STAND_R) and the reflex's `hit` at its
    end (a hit step, no reaction frame); done with `held` 2, `again` 1. m2 (shove mode): a shove that knocked nothing
    down, its back step. m3: a back step with no press before it. Without `rule` no line carries `held` or `again`."""
    hk = (lambda **kw: kw) if rule else (lambda **kw: {})
    frames = [(50.0 + k / 10.0, fr(50.0 + k / 10.0, "Bite" if k in (6, 7) else "", seq=3000 + k)) for k in range(46)]
    acts = [(50.0, actl("m1", "melee", "accepted", 50.0)),
            (50.1, mp("m1", 50.1, "swing", 2.0, swings=1, **hk(held=1, again=0))),
            (50.4, mp("m1", 50.4, "back", 1.5, swings=1, **hk(held=1, again=0))),
            (50.9, mp("m1", 50.9, "stand", 1.5, swings=1, hits=1, **hk(held=2, again=0))),
            (51.0, mp("m1", 51.0, "swing", 1.5, swings=2, hits=1, **hk(held=2, again=1))),
            (51.8, mp("m1", 51.8, "back", 1.5, swings=2, hits=1, **hk(held=2, again=1))),
            (52.0, mp("m1", 52.0, "hit", 1.5, swings=2, hits=2, **hk(held=2, again=1))),
            (52.5, actl("m1", "melee", "done", 52.5, dict({"end": "time"}, **hk(held=2, again=1)))),
            (53.0, actl("m2", "melee", "accepted", 53.0)), (53.1, mp("m2", 53.1, "shove", 3.0, shoves=1)),
            (53.4, mp("m2", 53.4, "back", 3.0, shoves=1)), (53.8, actl("m2", "melee", "done", 53.8, {"end": "time"})),
            (54.0, actl("m3", "melee", "accepted", 54.0)), (54.1, mp("m3", 54.1, "back", 3.0)),
            (54.5, actl("m3", "melee", "done", 54.5, {"end": "time"}))]
    return [ln for _, ln in sorted(frames + acts, key=lambda p: p[0])]


def close_log():
    sc = lambda h, a: {"fight": True, "maneuver": {"maneuver": "melee", "swing_close": {"held": h,   # noqa: E731
                                                                                         "pressed_again": a}}}
    return [line(0, 50.2, sc(1, 0), None, sent=False), line(1, 51.2, sc(2, 1), None, sent=False),
            line(2, 53.2, {"fight": True, "maneuver": {"maneuver": "melee"}}, None, sent=False)]


def close_read(rule=True, log=True):
    lines = close_lines(rule)
    L = E._Lines(T14.artifact(), close_log(), lines) if log else None
    rows = G.e_hits_union(E._frame_index(lines)[1], lines, 0)["rows"]
    return G.e_swing_close(L, lines, rows)


BACK = {"after_landed": 1, "after_nothing": 2, "no_press": 1}


def test_the_swing_close_reads_the_lua_s_held_and_again_the_back_steps_by_the_press_and_the_bites_in_them():
    s = close_read()
    assert (s["read"], s["held"], s["again"], s["lines"]) == (True, 2, 1, 2)
    assert s["back"] == BACK and s["bites_in_back"] == 2


def test_the_swing_close_keeps_the_back_steps_unread_without_held_or_again():
    s = close_read(rule=False)
    assert (s["read"], s["held"], s["again"]) == (False, 0, 0)
    assert s["back"] == BACK and s["bites_in_back"] == 2
    assert close_read(log=False)["lines"] is None


# ================================================================ P30-E, the still; P30-F, the dress ride
def still_log():
    return [line(0, 60.0, {"fight": True, "still": {"target": 4, "d": 2.0, "resolved": "approach"}}, _act("aim")),
            line(1, 60.5, {"still": {"target": 5, "d": 3.1, "resolved": "goal"}, "held": 1}, None, sent=False),
            line(2, 61.0, {"fight": True, "target": 4}, _act("aim")),
            line(3, 64.0, {"fight": True, "still": {"target": 4, "d": 2.2, "resolved": "approach"}}, _act("aim"))]


def test_the_still_reads_its_resolutions_by_kind_and_unread_without_its_lines():
    s = G.e_still(E._Lines(T14.artifact(), still_log(), []))
    assert s == {"read": True, "resolutions": 3, "by": {"approach": 2, "goal": 1}, "targets": [4, 5],
                 "d": [2.0, 3.1, 2.2]}
    assert G.e_still(E._Lines(T14.artifact(), CLEAN, [])) == {"read": False} and G.e_still(None) == {"read": False}


def ride_log():
    ride = lambda part, rate: {"flee": "health", "dress_ride": {"part": part, "rate": rate}}   # noqa: E731
    return [line(0, 70.0, ride(6, 13.0), None, sent=False), line(1, 70.5, ride(6, 12.0), None, sent=False),
            line(2, 71.0, ride(6, 14.0), None, sent=False), line(3, 71.5, {"flee": "health"}, _act("steer")),
            line(4, 72.0, ride(9, 3.0), None, sent=False)]


def ride_frames():
    return [fr(70.0 + 0.5 * k, health=h) for k, h in enumerate((90.0, 85.0, 80.0, 78.0, 77.0))]


def test_the_dress_ride_reads_each_ride_s_lines_rate_and_the_health_across_it():
    r = G.e_dress_ride(E._Lines(T14.artifact(), ride_log(), ride_frames()))
    assert r == {"read": True, "rides": 2, "lines": 4, "health_lost": 10.0, "rows": [
        {"part": 6, "lines": 3, "rate_max": 14.0, "h0": 90.0, "h1": 80.0, "h_min": 80.0},
        {"part": 9, "lines": 1, "rate_max": 3.0, "h0": 77.0, "h1": 77.0, "h_min": 77.0}]}
    assert G.e_dress_ride(E._Lines(T14.artifact(), CLEAN, [])) == {"read": False}
    assert G.e_dress_ride(None) == {"read": False}


# ================================================================ the standing minutes
def stand_log():
    """45 lines 0.5 s apart from 80.0 and a zombie listed within NEAR_R on each but L44-L45: L0-L24 within a tile of
    (10, 10) (drifting 0.4), 20 threat lines then 5 goal lines; L25 moves 1.5 tiles; L25-L43 19 lines unmoved (too
    short); L44 no zombie within 10; L45-L66 22 goal lines unmoved at (20, 20) with the zombie at 9.9 tiles."""
    out = []
    for n in range(67):
        x, y = (10.0 + (0.4 if n % 2 else 0.0), 10.0) if n < 25 else ((11.5, 10.0) if n < 45 else (20.0, 20.0))
        branch = "threat" if n < 20 else "goal"
        out.append(line(n, 80.0 + 0.5 * n, {"fight": True} if branch == "threat" else None, None, sent=False,
                        branch=branch, x=x, y=y))
    return out


def stand_frames():
    out = []
    for n, ln in enumerate(stand_log()):
        x, y = ln["inputs"]["x"], ln["inputs"]["y"]
        zs = [] if n == 44 else ([z(50, 15.0, 10.0)] if n < 45 else [z(50, 29.9, 20.0)])
        out.append(fr(80.0 + 0.5 * n, zombies=zs, x=x, y=y))
    return out


def test_the_standing_reads_the_stretches_of_twenty_lines_unmoved_near_a_zombie_by_branch():
    s = G.e_standing(E._Lines(T14.artifact(), stand_log(), stand_frames()))
    assert (s["read"], s["stretches"], s["lines"], s["seconds"], s["game_minutes"]) == (True, 2, 47, 23.5, 45)
    assert s["by_branch"] == {"threat": {"stretches": 1, "lines": 25, "seconds": 12.5},
                              "goal": {"stretches": 1, "lines": 22, "seconds": 11.0}}
    assert [(r["first"], r["last"], r["lines"], r["s"], r["gm"], r["branch"]) for r in s["rows"]] == [
        (1, 25, 25, 12.5, 24, "threat"), (46, 67, 22, 11.0, 21, "goal")]
    assert s["rows"][0]["branches"] == {"threat": 20, "goal": 5}
    assert G.e_standing(None) == {"read": False}
    assert G.e_standing(E._Lines(T14.artifact(), CLEAN, []))["stretches"] == 0


# ================================================================ grade_e21 over grade_e20
def to_e20(g):
    """grade_e21's dict as grade_e20's: the new keys dropped, the name and the gate line renamed, the new report lines
    dropped."""
    g = dict(g)
    for k in NEW:
        g.pop(k)
    g["grade"] = "grade_e20"
    g["report_lines"] = [("gate_e20 " + ln[len("gate_e21 "):]) if ln.startswith("gate_e21 ") else ln
                         for ln in g["report_lines"][:-G.N_LINES]]
    return g


@pytest.mark.parametrize("fixture", T14.E13_FIXTURES, ids=lambda f: f.__name__)
def test_grade_e21_reads_every_grade_e20_key_unchanged_on_test_gates_e13_s_fixtures(fixture, monkeypatch):
    seen = T14._captured(monkeypatch, fixture)
    a = T14.artifact(seen["actions"], seen["results"], seen["goals"])
    a["stop"]["reason"] = seen["stop"]
    e20 = G20.grade_e20(a, decision_lines=seen["log"], lines=seen["frames"])
    e21 = G.grade_e21(a, decision_lines=seen["log"], lines=seen["frames"])
    assert e21["grade"] == "grade_e21" and to_e20(e21) == e20


def test_grade_e21_on_the_cut2_fixture_keeps_every_grade_e20_key_and_reads_unread_without_anything():
    a = T14.artifact(T20.cut2_actions(), [])
    e20 = G20.grade_e20(a, decision_lines=T20.cut2_log(), lines=T20.cut2_lines())
    g = G.grade_e21(a, decision_lines=T20.cut2_log(), lines=T20.cut2_lines())
    assert to_e20(g) == e20
    assert g["kills_matched"]["planner"] == 3 and g["hits_union"]["union"] == 1
    r = G.readings_e21({}, None, [])
    assert all(r[k] == {"read": False} for k in NEW if k != "kills_matched")
    assert r["kills_matched"]["planner"] == 0 and r["kills_matched"]["matched"] == []


def test_report_lines_e21_names_gate_e21_then_one_line_per_reading():
    g = grade(log=goal_log(), frames=goal_frames())
    tail = g["report_lines"][-G.N_LINES:]
    assert tail == G.lines_e21(g) and G.N_LINES == len(NEW) == 9
    for ln, tag in zip(tail, ("(P30, the union", "(P30, the kills", "(iteration 24, P30-D", "(iteration 24, P30-B",
                              "(iteration 24, P30-C", "(iteration 24, P30-A", "(iteration 24, P30-E",
                              "(iteration 24, P30-F", "(P30, the standing")):
        assert tag in ln, (tag, ln)
    assert "[reading]" in tail[3] and "pending" in tail[3]
    off = grade(log=None)["report_lines"][-G.N_LINES:]
    assert all("no line read" in ln for ln in off[2:])
    renamed = G.report_lines_e21(dict(g, gate={"pass": True}))
    assert any(ln.startswith("gate_e21 ") for ln in renamed) and not any(ln.startswith("gate_e20 ") for ln in renamed)
    assert G.gate_e21([]) == E.gate_e13([]) and all(len(ln) < 2000 for ln in tail)


def test_the_inherited_report_lines_are_grade_e20_s():
    a = T14.artifact(T20.cut2_actions(), [])
    e20 = G20.grade_e20(a, decision_lines=T20.cut2_log(), lines=T20.cut2_lines())
    g = G.grade_e21(a, decision_lines=T20.cut2_log(), lines=T20.cut2_lines())
    assert g["report_lines"][:-G.N_LINES] == e20["report_lines"]


# ================================================================ ruling P26-Q: the frozen copies
def test_the_module_imports_no_live_planner_or_world_name_and_holds_its_own_copies():
    names = T20._imports(G.__file__)
    assert not any(m.startswith(("agent.base.planner", "agent.base.world")) for m in names), names
    ns = vars(G)
    assert (ns["SNEAK_R"], ns["STILL_DRIFT_R"], ns["STILL_MOVE_R"], ns["SHOVE_R"], ns["STOMP_R"]) == (
        8.0, 0.3, 1.0, 1.5, 0.5)
    assert (ns["MATCH_FRAMES"], ns["NEAR_R"], ns["STAND_LINES"], ns["DOOR_KILL_S"], ns["LINE_S"]) == (
        8, 10.0, 20, 60.0, 0.5)
    assert ns["MATCH_LADDER"] == ("attack", "stomp", "shove") and ns["MATCH_STEPS"] == ("swing", "floor", "stomp")
    assert ns["PRESS_STEPS"] == ("swing", "shove", "stomp", "floor") and (ns["HIT_STEP"], ns["BACK_STEP"]) == (
        "hit", "back")
    assert RULES == ("sneak", "goal_wait", "door_held", "swing_close", "still", "dress_ride")
    assert NEW == ("hits_union", "kills_matched") + RULES + ("standing",)
    assert not any(getattr(v, "__module__", "").startswith(("agent.base.planner", "agent.base.world"))
                   for v in ns.values())


# ================================================================ the mutants
def _mutated(name, edit):
    """grades/e21.py's source with `edit` applied inside the top-level def `name` only, executed as a module copy."""
    src = open(G.__file__, encoding="utf-8").read()
    head = "\ndef %s(" % name
    start = src.index(head)
    nxt = [i for i in (src.find("\ndef ", start + 5), src.find("\nclass ", start + 5)) if i >= 0]
    end = min(nxt) if nxt else len(src)
    new = edit(src[start:end])
    assert new != src[start:end], (name, "the mutant changed nothing")
    ns = {"__name__": "e21_mutant"}
    exec(compile(src[:start] + new + src[end:], "e21_mutant", "exec"), ns)    # noqa: S102 - a scratch copy
    return ns


MUTANTS = [
    ("e_hits_union", lambda b: b.replace("len(runs) + len(steps) - joined", "len(runs) + len(steps)"),
     lambda: union_read()["union"] == 6),
    ("_joins", lambda b: b.replace("lo <= w <= hi", "lo < w < hi"), lambda: union_read()["joined"] == 2),
    ("_step_runs", lambda b: b.replace("st == HIT_STEP and prev != HIT_STEP", "st == HIT_STEP"),
     lambda: union_read()["steps"] == 5),
    ("e_kills_matched", lambda b: b.replace("d <= reach", "True"), lambda: kills_read()["planner"] == 3),
    ("e_kills_matched", lambda b: b.replace("fb > MATCH_FRAMES", "False"), lambda: kills_read()["planner"] == 3),
    ("_press_kind", lambda b: b.replace("step in MATCH_STEPS", "step in PRESS_STEPS"),
     lambda: kills_read()["planner"] == 3),
    ("_sneaking", lambda b: b.replace("is True", "is not None"), lambda: sneak_read()["minutes"] == 3),
    ("e_sneak", lambda b: b.replace('r["gait"] == SNEAK_GAIT', "True"), lambda: sneak_read()["walk_speed"] == 1.5),
    ("e_sneak", lambda b: b.replace("d <= SNEAK_R", "True"), lambda: sneak_read()["near"] == 3),
    ("e_goal_wait", lambda b: b.replace("< STILL_DRIFT_R", "< 10.0"), lambda: goal_read()["unmoved"] == 6),
    ("e_goal_wait", lambda b: b.replace("near(first) or near(last)", "near(first)"),
     lambda: goal_read()["near_runs"]["runs"] == 2 and _near_runs_end_only() == 1),
    ("e_door_held", lambda b: b.replace("w - t <= DOOR_KILL_S", "True"), lambda: _door()["kills_after_open"] == 1),
    ("e_swing_close", lambda b: b.replace("lowered or kd", "lowered"), lambda: _close_kd()["after_landed"] == 1),
    ("e_swing_close", lambda b: b.replace("lo <= w <= hi", "lo < w < hi"), lambda: close_read()["bites_in_back"] == 2),
    ("e_dress_ride", lambda b: b.replace("prev_part == part and prev_i == i - 1", "prev_part == part"),
     lambda: _ride_split() == 2),
    ("_stretches", lambda b: b.replace(">= STILL_MOVE_R", ">= 10.0"),
     lambda: [(r["first"], r["last"]) for r in G.e_standing(E._Lines(T14.artifact(), stand_log(),
                                                                   stand_frames()))["rows"]] == [(1, 25), (46, 67)]),
]


def _near_runs_end_only():
    """The goal wait's near runs with the zombie only at a run's end: L1-L4's zombie at 30 tiles but on L4."""
    frames = goal_frames()
    for n in (1, 2, 3):
        frames[n]["zombies"] = [z(40, 30.0, 10.0)]
    frames[0]["zombies"] = [z(40, 30.0, 10.0)]
    log = [ln for ln in goal_log() if ln["gameMin"] <= 604]
    return G.e_goal_wait(E._Lines(T14.artifact(), log, frames))["near_runs"]["runs"]


def _door():
    lines = door_lines()
    return G.e_door_held(E._Lines(T14.artifact(), door_log(), lines), lines)


def _close_kd():
    """The swing close's back steps with m1's first press a shove that knocked its zombie down without lowering it."""
    lines = close_lines()
    for ln in lines:
        if ln.get("aid") == "m1" and ln.get("state") == "progress" and ln["result"]["step"] == "back" and \
                ln["result"]["hp"] == 1.5 and ln["wallMs"] < int((T0 + 50.5) * 1000):
            ln["result"].update(hp=2.0, knockdowns=1)
    rows = G.e_hits_union(E._frame_index(lines)[1], lines, 0)["rows"]
    return G.e_swing_close(None, lines, rows)["back"]


def _ride_split():
    """Two rides of one part split by a line without the why: two rides, not one."""
    log = ride_log()
    log[4]["inputs"]["branches"]["threat"]["dress_ride"]["part"] = 6
    return G.e_dress_ride(E._Lines(T14.artifact(), log, ride_frames()))["rides"]


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


# ================================================================ the real checks: F14 and E23
def _committed(path, name):
    text = open(os.path.join(path, name), encoding="utf-8").read()
    i = text.index("\n{\n")
    return text[:i + 1].splitlines(), json.loads(text[i:])


def _path(d, name):
    p = os.path.join(d, name)
    if not os.path.isfile(p):
        pytest.skip("%s is not checked out" % d)
    return p


@functools.lru_cache(maxsize=None)
def _e23():
    p = _path(E23, "e_day_23.json")
    return G.grade_e21(EG21.load(p), None, EG21.load_log(p), state_dir=EG21._dir(p))


@functools.lru_cache(maxsize=None)
def _f14_readings():
    """`readings_e21` over F14's artifact, decision log and state lines (`grade_f12` reads them the same way:
    test_grades_f12)."""
    p = _path(F14, "f_goals_15.json")
    lines, _ = E.session_lines(F14)
    return G.readings_e21(EG21.load(p), EG21.load_log(p), lines)


def unread_rules(g):
    """Iteration 24's rule readings unread, their measures kept: the sneak, the door, the still and the ride
    {"read": False}; the goal wait and the swing close read False with their measures."""
    plain = all(g[k] == {"read": False} for k in ("sneak", "door_held", "still", "dress_ride"))
    return plain and g["goal_wait"]["read"] is False and g["swing_close"]["read"] is False and \
        set(g["goal_wait"]) == set(WAIT) | {"read", "continued", "extended"} and \
        set(g["swing_close"]) == {"read", "held", "again", "lines", "back", "bites_in_back"}


def test_on_f14_the_union_reads_the_eight_attacks_that_landed_and_the_seventh_kill_is_matched_to_a59():
    """F14's guide section 1: five reaction runs and the reflex's `hit` steps of a104, a128 and a212 with no reaction
    frame (a130's joins the run from seq 7649), 8 over the 7 kills; 32434's death (seq 3927) four frames after the
    swing event of the ladder's floor attack a59 at 32433 (seq 3920), 32434 at 0.096 tiles within the bat's reach."""
    r = _f14_readings()
    u, k = r["hits_union"], r["kills_matched"]
    assert (u["runs"], u["steps"], u["joined"], u["union"], u["kills"]) == (5, 4, 1, 8, 7)
    assert u["per_kill_union"] == 8 / 7
    assert sorted(x["aid"] for x in u["rows"] if x["aid"] is not None) == ["a104", "a128", "a130", "a212"]
    assert (k["planner"], k["whole"], k["agree"], k["unmatched"]) == (7, 6, True, [])
    m = k["matched"]
    assert [(x["id"], x["aid"], x["type"], x["source"], x["seq"], x["frames_before"]) for x in m] == [
        (32434, "a59", "attack", "ladder", 3920, 4)]
    assert round(m[0]["d"], 3) == 0.096 and m[0]["reach"] == 1.125


def test_on_f14_the_standing_reads_the_desk_read_s_eight_stretches_and_the_wait_its_181_pending_lines_near():
    """Plan 29's `pause-and-door-read.md` section A.1 (F14's #5-#12, the lines 1-47, 48-76, 146-192, 225-254,
    281-316, 749-768, 1085-1110 and 1427-1488) and A.2 (275 lines pending, 19 runs with a zombie within 10 tiles at
    the run's start or end: 181 lines, 90.1 s)."""
    r = _f14_readings()
    s = r["standing"]
    assert [(x["first"], x["last"]) for x in s["rows"]] == [(1, 47), (48, 76), (146, 192), (225, 254), (281, 316),
                                                             (749, 768), (1085, 1110), (1427, 1488)]
    assert [x["branch"] for x in s["rows"]] == ["goal", "goal", "goal", "goal", "threat", "threat", "threat",
                                                "threat"]
    assert s["rows"][2]["s"] == pytest.approx(23.5, abs=0.05) and s["rows"][7]["s"] == pytest.approx(31.0, abs=0.05)
    w = r["goal_wait"]
    assert (w["lines"], w["near_runs"]["runs"], w["near_runs"]["lines"]) == (275, 19, 181)
    assert w["near_runs"]["s"] == pytest.approx(90.1, abs=0.05) and w["seconds"] == pytest.approx(137.0, abs=1.0)
    assert len(w["hops"]) == 8 and w["hops"][2] == 5.404340020749572    # line 168's own `dist` (`_dist`)
    assert unread_rules(r)


def test_on_e23_the_union_reads_six_the_kill_one_the_four_stretches_and_the_rules_unread():
    """E23: four reaction runs and the reflex's `hit` steps of a41 and a42 with none (a125's, a130's and a131's join
    their runs), 6 over its one kill (26241, the whole read's); the desk read's E23 #1-#4 (lines 1-36, 37-58, 92-119,
    157-191)."""
    g = _e23()
    u, k = g["hits_union"], g["kills_matched"]
    assert (u["runs"], u["steps"], u["joined"], u["union"], u["per_kill_union"]) == (4, 5, 3, 6, 6.0)
    assert (k["planner"], k["planner_ids"], k["matched"], k["agree"]) == (1, [26241], [], True)
    assert [(x["first"], x["last"], x["branch"]) for x in g["standing"]["rows"]] == [
        (1, 36, "goal"), (37, 58, "goal"), (92, 119, "goal"), (157, 191, "threat")]
    assert unread_rules(g)


def test_grade_e21_on_e23_keeps_every_grade_e20_key_as_the_committed_e_grade_txt():
    g = _e23()
    mine = json.loads(json.dumps(EG21.finite(g), sort_keys=True, allow_nan=False))
    lines, committed = _committed(E23, "e_grade.txt")
    assert g["grade"] == "grade_e21" and to_e20(mine) == committed
    assert [("gate_e20 " + ln[len("gate_e21 "):]) if ln.startswith("gate_e21 ") else ln
            for ln in g["report_lines"][:-G.N_LINES]] == lines


def test_e_grade_21_prints_the_committed_e_grade_txt_s_lines_then_the_new_ones():
    """`e_grade_21.py` on the committed E23 artifact: the committed `e_grade.txt`'s report lines (CRLF folded), then
    the new lines, then the JSON whose inherited keys equal the committed."""
    p = _path(E23, "e_day_23.json")
    script = os.path.join(TESTING, "agent", "drivers", "e_grade_21.py")
    r = subprocess.run([sys.executable, script, p], capture_output=True, cwd=TESTING)
    assert r.returncode == 0
    text = r.stdout.decode("utf-8").replace("\r\n", "\n")
    i = text.index("\n{\n")
    printed, got = text[:i + 1].splitlines(), json.loads(text[i:])
    want_lines, want = _committed(E23, "e_grade.txt")
    assert printed[:-G.N_LINES] == want_lines and len(printed) == len(want_lines) + G.N_LINES
    assert got["grade"] == "grade_e21" and printed[-G.N_LINES:] == got["report_lines"][-G.N_LINES:]
    assert to_e20(got) == want and got["hits_union"]["union"] == 6


def test_e_grade_21_refuses_an_argument_it_does_not_define():
    """Read statically (CLAUDE.md section 5): its main answers usage, exit 2, on no path or more than two outside
    `--chain`."""
    src = open(EG21.__file__, encoding="utf-8").read()
    assert "if not paths or (not chain and len(paths) > 2):" in src and "return 2" in src
    assert "from agent.base.grades.e21 import gate_e21, grade_e21, report_lines_e21" in src
    body = src[src.index('"""', 3):]
    assert "usage: e_grade_21.py" in src and "e20" not in body and "_e20" not in body


def test_the_frozen_chain_is_untouched():
    """Ruling P26-Q: grade_e21 reads grade_e20 through its function (no edit of the frozen modules: the task's
    diffstat), and its own readers through no name of the frozen chain but those it imports."""
    src = open(G.__file__, encoding="utf-8").read()
    assert "G20.grade_e20(" in src and "def grade_e20" not in src and math.isclose(G.LINE_S, 0.5)
