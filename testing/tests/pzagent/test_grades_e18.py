"""base/grades/e18.py (Plan 28 Task 4), offline: `grade_e18` and its nine readings of survival iteration 21 and the
plan's second metric (the hits per kill P28-M, the wound dressed P28-A, the back leg after a missed shove P28-B2, the
drifted pin's stance P28-B3, the floor swing under the arms' pain P28-C, a `busy` rejection retried P28-D, the circle
P28-E, the facing on the swing P28-F and the client's end as a stop, the spec's 1 (c)), each on a fabricated log where
it counts and a clean one where it reads zero, the unread case (`hits` reads the frames alone), a mutant per reading,
every `grade_e17` key unchanged under `grade_e18` on test_gates_e13's fixtures, the module's frozen copies of the live
names (ruling P26-Q), and the real checks on E20 (`e_day_20-20261103-121340`) and E19 (`e_day_19-20261103-072904`):
every inherited key equal to the committed `e_grade.txt`'s, through the function and through `e_grade_18.py` (its
printed lines the committed ones then the new ones), and the new readings as the grade reads them."""
import ast
import json
import os
import subprocess
import sys

import pytest

from agent.base import gates_e as E
from agent.base.grades import e17 as G17
from agent.base.grades import e18 as G
from agent.drivers import e_grade_18 as EG18
from . import test_grades_e14 as T14
from .test_gates_e7 import T0, aline, zf
from .test_gates_e13 import _act
from .test_grades_e14 import actl, row
from .test_grades_e17 import CLEAN, res, swing

HERE = os.path.dirname(os.path.abspath(__file__))
TESTING = os.path.dirname(os.path.dirname(HERE))
E19 = os.path.join(TESTING, "artifacts", "e_day_19-20261103-072904")
E20 = os.path.join(TESTING, "artifacts", "e_day_20-20261103-121340")
E21 = os.path.join(TESTING, "artifacts", "e_day_21-20261104-201749")
NEW = G.NEW
NEW17 = G17.NEW
TAGS = ("P28-M", "P28-A", "P28-B2", "P28-B3", "P28-C", "P28-D", "P28-E", "P28-F", "the spec's 1 (c)")
SWEEP = ("wound_dress", "shove_back", "drift_stand", "floor_pain", "busy_retry", "circle", "facing", "client_end")


def grade(actions=(), results=(), log=None, frames=(), fights=None, stop=None, end=None):
    a = T14.artifact(actions, results)
    if fights is not None:
        a["loop"]["fights"] = list(fights)
    if stop is not None:
        a["stop"]["reason"] = stop
    if end is not None:
        a["loop"]["end"] = dict(end)
    return G.grade_e18(a, decision_lines=log, lines=list(frames))


def hf(t, react="", health=100.0, parts=(), zombies=(), scratched=0, bitten=0, bleeding=None, x=10.0, y=10.0,
       me_dir="S"):
    """`zf` with the reaction (`me.hitReaction`), the facing, the body's health, its counts and its parts set; the
    body's `bleeding` count is the parts' bleeding unless given."""
    f = zf(t, zombies, parts=[dict(p) for p in parts], x=x, y=y)
    f["me"].update(hitReaction=react, dir=me_dir)
    bled = sum(1 for p in parts if p.get("bleeding") is True) if bleeding is None else bleeding
    f["body"].update(health=health, scratched=scratched, bitten=bitten, bleeding=bled)
    return f


# ================================================================ P28-M, the hits per kill
def hits_fixture():
    """Four reaction runs: `Bite` on the first frame (after None) and on the next (one run, `scratched` 0 to 1), a
    `BiteLEFT` after an empty frame (`bitten` 0 to 1), a `BiteLEFT` after a None frame (`bleeding` 0 to 2) and a
    `BiteRIGHT` after a quiet frame whose `bleeding` fell to 1 (to 2 again): five rises on four frames. Fight 0 spans
    1.0 to 3.0 (runs 2 and 3), fight 1 from 5.0 with no end (run 4), run 1 before both. The strikes before the runs:
    none within STRIKE_BEFORE_S of run 1 (an aim at -0.5, a shove at -2.5); before run 2 a stomp at 0.1 and then the
    shove s1 at 0.2 (the last, `knockdown` false, at 9, not the nearest standing); the attack a1 at 2.0 before run 3
    (`attackStarted` true, at 9, the nearest standing beside a fallen 10); the stomp k1 at 5.5 before run 4 (killing 7,
    which lies fallen). Two kills (k0 at -5.0 and k1)."""
    z = lambda zid, d, fl=None: {"id": zid, "dist": d, "onFloor": fl}
    frames = [hf(0.0, "Bite"), hf(0.5, "Bite", scratched=1), hf(1.0, "", scratched=1),
              hf(1.5, "BiteLEFT", scratched=1, bitten=1, zombies=[z(9, 0.8), z(10, 0.5)]),
              hf(2.0, None, scratched=1, bitten=1),
              hf(2.5, "BiteLEFT", scratched=1, bitten=1, bleeding=2, zombies=[z(9, 0.6), z(10, 0.3, True)]),
              hf(3.5, "", scratched=1, bitten=1, bleeding=1),
              hf(6.0, "BiteRIGHT", scratched=1, bitten=1, bleeding=2, zombies=[z(7, 0.4, True)])]
    acts = [actl("k0", "stomp", "accepted", -5.0), actl("k0", "stomp", "done", -4.9, {"hit": True, "targetDead": True}),
            actl("s0", "shove", "accepted", -2.5), actl("g0", "aim", "accepted", -0.5),
            actl("k2", "stomp", "accepted", 0.1), actl("s1", "shove", "accepted", 0.2),
            actl("s1", "shove", "done", 0.9, {"knockdown": False}),
            actl("a1", "attack", "accepted", 2.0), actl("a1", "attack", "done", 2.4, {"attackStarted": True}),
            actl("k1", "stomp", "accepted", 5.5), actl("k1", "stomp", "done", 5.8, {"hit": True, "targetDead": True})]
    actions = [row("k0", "stomp", -5.0, targetId=8), row("s0", "shove", -2.5, targetId=9),
               row("g0", "aim", -0.5, targetId=9), row("k2", "stomp", 0.1, targetId=10),
               row("s1", "shove", 0.2, targetId=9), row("a1", "attack", 2.0, targetId=9),
               row("k1", "stomp", 5.5, targetId=7)]
    fights = [{"startS": 1.0, "end": {"endS": 3.0}}, {"startS": 5.0, "end": None}]
    return grade(actions, [], None, frames + acts, fights=fights)


HITS = {"read": True, "runs": 4, "kills": 2, "per_kill": 2.0, "wounds": 5, "wound_frames": 4, "wounds_per_kill": 2.5,
        "by_fight": [2, 1], "outside": 1, "kinds": {"Bite": 1, "BiteLEFT": 2, "BiteRIGHT": 1},
        "strike_before": [
            {"seq": 0, "kind": "Bite", "type": None, "aid": None, "before_s": None, "target": None, "nearest": None,
             "knockdown": None, "attackStarted": None},
            {"seq": 15, "kind": "BiteLEFT", "type": "shove", "aid": "s1", "before_s": 1.3, "target": 9,
             "nearest": False, "knockdown": False, "attackStarted": None},
            {"seq": 25, "kind": "BiteLEFT", "type": "attack", "aid": "a1", "before_s": 0.5, "target": 9,
             "nearest": True, "knockdown": None, "attackStarted": True},
            {"seq": 60, "kind": "BiteRIGHT", "type": "stomp", "aid": "k1", "before_s": 0.5, "target": 7,
             "nearest": False, "knockdown": None, "attackStarted": None}]}


def test_the_hits_count_the_runs_their_kinds_the_wounds_per_kill_the_fights_and_the_strike_before_each():
    g = hits_fixture()
    assert g["kills"]["planner"] == 2
    assert g["hits"] == HITS


def test_the_hits_read_zero_on_quiet_frames_and_unread_without_frames_even_with_a_log():
    zero = {"read": True, "runs": 0, "kills": 0, "per_kill": None, "wounds": 0, "wound_frames": 0,
            "wounds_per_kill": None, "by_fight": [], "outside": 0, "kinds": {}, "strike_before": []}
    assert grade(log=None, frames=[hf(0.0), hf(1.0, None), hf(2.0)])["hits"] == zero
    assert grade(log=CLEAN)["hits"] == {"read": False}
    assert grade(log=None)["hits"] == {"read": False}


# ================================================================ P28-A, the wound dressed
def wpart(i, h, wound=True, bandaged=False, bleeding=False):
    return {"i": i, "h": h, "bleeding": bleeding, "bleedingTime": 0, "bandaged": bandaged, "wound": wound}


def wound_fixture(flag=True):
    """Two wound dressings sent (part 4's done, part 6's rejected `busy`), one logged and not sent, one on a threat
    line, two `wound_held` lines (one holding two clean, over WOUND_RESERVE). The frames: parts 4 and 6 wounded and
    undressed with part 9 reading `wound` None (an older log's); the health falls 1.0 quiet, then on a bleed, then on
    a bite reaction, then 0.5 and 0.5 with part 6 undressed, then 1.0 with every wound dressed; part 11 opens on the
    last frame."""
    why = (lambda p, h: {"reason": "wound", "part": p, "item": 50, "kind": "rag", "h": h}) if flag \
        else (lambda p, h: {"bleeding": [], "spent": []})
    held = (lambda p, c: {"wound_held": {"part": p, "clean": c}}) if flag else (lambda p, c: {})
    log = [aline(0, 1.0, {}, _act("bandage", itemId=50, part=4), branch="care", care=why(4, 82.0)),
           aline(1, 2.0, {}, None, sent=False, branch="care", care=dict({"bleeding": []}, **held(6, 1))),
           aline(2, 3.0, {}, _act("bandage", itemId=51, part=6), branch="care", care=why(6, 95.0)),
           aline(3, 4.0, {}, _act("bandage", itemId=52, part=4), sent=False, branch="care", care=why(4, 82.0)),
           aline(4, 5.0, {"flee": "strain"}, _act("bandage", itemId=53, part=4), care=why(4, 82.0)),
           aline(5, 6.0, {}, None, sent=False, branch="care", care=dict({"bleeding": []}, **held(8, 2)))]
    acts = [row("b1", "bandage", 1.0, branch="care", itemId=50, part=4),
            row("b2", "bandage", 3.0, state="rejected", reason="busy", branch="care", itemId=51, part=6),
            row("b3", "bandage", 5.0, itemId=53, part=4)]
    old = wpart(9, 99.0, wound=None)
    p4, p6 = (lambda h, **kw: wpart(4, h, **kw)), (lambda h, **kw: wpart(6, h, **kw))
    frames = [hf(0.9, health=90.0, parts=[p4(82.0), p6(95.0), old]),
              hf(1.95, health=89.0, parts=[p4(82.0), p6(95.0), old]),
              hf(2.95, health=87.0, parts=[p4(81.0, bleeding=True), p6(95.0), old]),
              hf(3.95, "Bite", health=86.0, parts=[p4(81.0), p6(95.0), old]),
              hf(4.95, health=84.0, parts=[p4(81.0, bandaged=True), p6(94.5), old]),
              hf(5.95, health=83.5, parts=[p4(81.0, bandaged=True), p6(94.2), old]),
              hf(6.95, health=83.0, parts=[p4(80.5, bandaged=True), p6(94.0, bandaged=True), old]),
              hf(7.95, health=82.0, parts=[p4(80.0, bandaged=True), p6(94.0, bandaged=True), old,
                                           wpart(11, 99.5)])]
    return grade(acts, [], log, frames)["wound_dress"]


def test_the_wound_dress_counts_the_dressings_by_part_the_holds_and_the_health_fallen_quiet_on_an_open_wound():
    assert wound_fixture() == {"read": True, "sent": 2, "done": 1, "by_part": {"4": 1, "6": 1},
                               "part_h": {"4": [82.0, 80.0], "6": [95.0, 94.0]}, "held": 2, "held_over_reserve": 1,
                               "no_bleed_fall": 2.0, "parts_undressed_at_end": [11]}


def test_the_wound_dress_reads_zero_without_the_why_and_unread_without_a_log():
    off = wound_fixture(flag=False)
    assert off == {"read": True, "sent": 0, "done": 0, "by_part": {}, "part_h": {}, "held": 0, "held_over_reserve": 0,
                   "no_bleed_fall": 2.0, "parts_undressed_at_end": [11]}
    assert grade(log=CLEAN, frames=[hf(1.0, parts=[wpart(4, 80.0, wound=None)]), hf(2.0, health=99.0)])[
        "wound_dress"] == {"read": True, "sent": 0, "done": 0, "by_part": {}, "part_h": {}, "held": 0,
                           "held_over_reserve": 0, "no_bleed_fall": 0.0, "parts_undressed_at_end": []}
    assert grade(log=None)["wound_dress"] == {"read": False}


# ================================================================ P28-B2, the back leg after a missed shove
def back_fixture(flag=True):
    """Two `shove_back` legs sent (at 4, ended 3.0, a bite reaction starting within it at 2.0 and the shove at 4 after
    it; at 5, ended 6.0, a shove at 6 after it and a reaction at 7.0 after its end), one logged and not sent, one on a
    care line."""
    sb = (lambda zid: {"shove_back": {"target": zid, "missed": 1}}) if flag else (lambda zid: {})
    leg = lambda zid: dict({"fight": True, "target": zid, "stance": True, "leg": "back", "back": [-1.0, 0.0]},
                           **sb(zid))
    log = [aline(0, 1.0, leg(4), _act("aim", targetId=4)),
           aline(1, 2.0, {"fight": True, "target": 4}, None, sent=False),
           aline(2, 3.5, {"fight": True, "target": 4}, _act("shove", targetId=4)),
           aline(3, 5.0, leg(5), _act("aim", targetId=5)),
           aline(4, 5.5, {"fight": True, "target": 6}, _act("shove", targetId=6)),
           aline(5, 8.0, leg(7), _act("aim", targetId=7), sent=False),
           aline(6, 9.0, leg(8), _act("aim", targetId=8), branch="care")]
    acts = [row("g1", "aim", 1.0, ended=3.0, targetId=4), row("s1", "shove", 3.5, targetId=4),
            row("g2", "aim", 5.0, ended=6.0, targetId=5), row("s2", "shove", 5.5, targetId=6),
            row("g3", "aim", 9.0, branch="care", targetId=8)]
    frames = [hf(0.5), hf(2.0, "Bite"), hf(2.5), hf(7.0, "Bite"), hf(7.5), hf(9.5, "Bite")]
    return grade(acts, [], log, frames)["shove_back"]


def test_the_shove_back_counts_the_legs_the_bites_during_them_and_the_shoves_after():
    assert back_fixture() == {"read": True, "lines": 3, "legs": 2, "bites_during": 1, "shoves_after": 1}


def test_the_shove_back_reads_zero_without_the_why_and_unread_without_a_log():
    assert back_fixture(flag=False) == {"read": True, "lines": 0, "legs": 0, "bites_during": 0, "shoves_after": 0}
    assert grade(log=None)["shove_back"] == {"read": False}


# ================================================================ P28-B3, the drifted pin's stance
def drift_fixture(flag=True):
    """Two drifted pins' stance legs sent (at 4, shoved on the next line, a bite reaction 3 s on; at 5, a shove at
    another zombie after it and the next reaction 15 s on), an older log's `out_of_reach` without the stance, one
    logged and not sent."""
    ds = {"stance": True, "leg": "stand"} if flag else {}
    pin = lambda zid: dict({"target": zid, "pinned": True, "dist": 3.0, "out_of_reach": True}, **ds)
    log = [aline(0, 1.0, pin(4), _act("aim", targetId=4)),
           aline(1, 2.0, {"fight": True, "target": 4}, _act("shove", targetId=4)),
           aline(2, 20.0, pin(5), _act("aim", targetId=5)),
           aline(2, 20.5, {"fight": True, "target": 9}, _act("shove", targetId=9)),
           aline(3, 21.0, {"target": 6, "pinned": True, "dist": 3.0, "out_of_reach": True}, None, sent=False),
           aline(4, 22.0, pin(6), _act("aim", targetId=6), sent=False)]
    acts = [row("g1", "aim", 1.0, targetId=4), row("s1", "shove", 2.0, targetId=4), row("g2", "aim", 20.0, targetId=5),
            row("s2", "shove", 20.5, targetId=9)]
    frames = [hf(0.5), hf(4.0, "Bite"), hf(4.5), hf(35.0, "BiteLEFT"), hf(35.5)]
    return grade(acts, [], log, frames)["drift_stand"]


def test_the_drift_stand_counts_the_legs_the_shoves_after_and_the_bites_after():
    assert drift_fixture() == {"read": True, "lines": 3, "legs": 2, "shoves_after": 1, "bites_after": 1}


def test_the_drift_stand_reads_zero_without_the_why_and_unread_without_a_log():
    assert drift_fixture(flag=False) == {"read": True, "lines": 0, "legs": 0, "shoves_after": 0, "bites_after": 0}
    assert grade(log=None)["drift_stand"] == {"read": False}


# ================================================================ P28-C, the floor swing under the arms' pain
def pain_fixture(flag=True):
    """Floor swings sent under the pain (at 4, pain 30, a swing event and a stomp at 4 after it; at 5, pain 25,
    killing it, a stomp at another zombie after it), one under STRAIN_HARD (pain 10, the frame's armPain 22), two
    older logs' without the `pain` field (the frame's armPain 25 and 5), one logged and not sent."""
    ff = (lambda zid, p: {"floor_finish": dict({"target": zid, "health": 1.5},
                                               **({"pain": p} if p is not None else {}))})
    fight = lambda zid, p: dict({"fight": True, "target": zid}, **ff(zid, p if flag else None))
    log = [aline(0, 1.0, fight(4, 30.0), _act("attack", targetId=4)),
           aline(1, 1.5, {"fight": True, "target": 4, "finish": 4}, _act("stomp", targetId=4)),
           aline(2, 3.0, fight(5, 25.0), _act("attack", targetId=5)),
           aline(2, 3.6, {"fight": True, "target": 99, "finish": 99}, _act("stomp", targetId=99)),
           aline(3, 5.0, fight(6, 10.0), _act("attack", targetId=6)),
           aline(4, 6.0, dict({"fight": True, "target": 7}, **ff(7, None)), _act("attack", targetId=7)),
           aline(5, 7.0, dict({"fight": True, "target": 8}, **ff(8, None)), _act("attack", targetId=8)),
           aline(6, 8.0, fight(9, 40.0), _act("attack", targetId=9), sent=False)]
    acts = [row("f1", "attack", 1.0, ended=1.8, targetId=4), row("f2", "stomp", 1.5, targetId=4),
            row("f3", "attack", 3.0, ended=3.5, targetId=5), row("f7", "stomp", 3.6, targetId=99),
            row("f4", "attack", 5.0, targetId=6),
            row("f5", "attack", 6.0, targetId=7), row("f6", "attack", 7.0, targetId=8)]
    events = [zf(0.5), zf(4.9, pain=22.0), zf(5.9, pain=25.0), zf(6.9, pain=5.0), swing(1.3), swing(3.2), swing(5.2)]
    results = [res("f1", hit=True), res("f3", hit=True, targetDead=True)]
    return grade(acts, results, log, events)["floor_pain"]


def test_the_floor_pain_counts_the_swings_under_the_pain_their_landings_kills_the_stomps_after_and_the_check():
    assert pain_fixture() == {"read": True, "swings": 2, "landed": 2, "kills": 1, "stomps_after": 1,
                              "swings_under_pain_before": 1}


def test_the_floor_pain_reads_zero_without_the_why_and_unread_without_a_log():
    assert pain_fixture(flag=False) == {"read": True, "swings": 0, "landed": 0, "kills": 0, "stomps_after": 0,
                                        "swings_under_pain_before": 2}
    assert grade(log=CLEAN)["floor_pain"] == {"read": True, "swings": 0, "landed": 0, "kills": 0, "stomps_after": 0,
                                              "swings_under_pain_before": 0}
    assert grade(log=None)["floor_pain"] == {"read": False}


# ================================================================ P28-D, a `busy` rejection retried
def busy_fixture(flag=True):
    """Retries sent: the stomp at 4 (landing, the kill on the next line), the shove at 5, the stomp at 8 (missing, a
    landed stomp at 9 after it); a retry logged and not sent, and one whose kind is not the send's."""
    br = (lambda zid, kind: {"busy_retry": {"target": zid, "kind": kind}}) if flag else (lambda *a: {})
    fight = lambda zid, kind: dict({"fight": True, "target": zid}, **br(zid, kind))
    log = [aline(0, 1.0, fight(4, "stomp"), _act("stomp", targetId=4)),
           aline(1, 1.5, {"fight": True, "target": 4}, _act("stomp", targetId=4)),
           aline(2, 3.0, fight(5, "shove"), _act("shove", targetId=5)),
           aline(3, 4.0, fight(6, "stomp"), _act("stomp", targetId=6), sent=False),
           aline(4, 5.0, fight(7, "stomp"), _act("shove", targetId=7)),
           aline(5, 6.0, fight(8, "stomp"), _act("stomp", targetId=8)),
           aline(6, 6.5, {"fight": True, "target": 9}, _act("stomp", targetId=9))]
    acts = [row("k1", "stomp", 1.0, targetId=4), row("k2", "stomp", 1.5, targetId=4),
            row("s1", "shove", 3.0, targetId=5), row("s2", "shove", 5.0, targetId=7),
            row("k3", "stomp", 6.0, targetId=8), row("k4", "stomp", 6.5, targetId=9)]
    results = [res("k1", hit=True), res("k2", hit=True, targetDead=True), res("k3", hit=False), res("k4", hit=True)]
    return grade(acts, results, log)["busy_retry"]


def test_the_busy_retry_counts_the_sends_by_kind_the_stomps_landed_after_and_the_kills_after():
    assert busy_fixture() == {"read": True, "sends": 3, "by_kind": {"stomp": 2, "shove": 1}, "stomps_landed_after": 1,
                              "kills_after": 1}


def test_the_busy_retry_reads_zero_without_the_why_and_unread_without_a_log():
    assert busy_fixture(flag=False) == {"read": True, "sends": 0, "by_kind": {}, "stomps_landed_after": 0,
                                        "kills_after": 0}
    assert grade(log=None)["busy_retry"] == {"read": False}


# ================================================================ P28-E, the circle
def circle_fixture(flag=True):
    """`back` legs sent with the circle's turn +45, +45, -45 (the side switched), +30 (switched, off CIRCLE_TURN);
    two straight `back` legs (two standing within KEEP_R; one standing beside a fallen one, `straight_one`); a circle
    logged and
    not sent and one on a care line."""
    c = (lambda t: {"circle": {"turn": t}}) if flag else (lambda t: {})
    back = lambda t: dict({"fight": True, "target": 1, "stance": True, "leg": "back", "back": [-0.7, 0.7]}, **c(t))
    plain = {"fight": True, "target": 1, "stance": True, "leg": "back", "back": [-1.0, 0.0]}
    log = [aline(0, 1.0, back(45.0), _act("aim", targetId=1)), aline(1, 2.0, back(45.0), _act("aim", targetId=1)),
           aline(2, 3.0, back(-45.0), _act("aim", targetId=1)), aline(3, 4.0, back(30.0), _act("aim", targetId=1)),
           aline(4, 5.0, plain, _act("aim", targetId=1)), aline(5, 6.0, plain, _act("aim", targetId=1)),
           aline(6, 7.0, back(45.0), _act("aim", targetId=1), sent=False),
           aline(7, 8.0, back(45.0), _act("aim", targetId=1), branch="care")]
    two = [{"id": 1, "dist": 1.0}, {"id": 2, "dist": 2.0}]
    frames = [zf(0.5, two), zf(4.9, two), zf(5.9, [{"id": 1, "dist": 1.0}, {"id": 2, "dist": 2.0, "onFloor": True}])]
    return grade([], [], log, frames)["circle"]


def test_the_circle_counts_the_legs_by_side_the_switched_sides_the_off_turns_and_the_straight_legs_at_two():
    assert circle_fixture() == {"read": True, "legs": 4, "sides": {"+": 3, "-": 1}, "blocked_turns": 2, "off_turn": 1,
                                "straight_two": 1, "straight_one": 1}


def test_the_circle_reads_zero_without_the_why_and_unread_without_a_log():
    assert circle_fixture(flag=False) == {"read": True, "legs": 0, "sides": {}, "blocked_turns": 0, "off_turn": 0,
                                          "straight_two": 5, "straight_one": 1}
    assert grade(log=CLEAN)["circle"] == {"read": True, "legs": 0, "sides": {}, "blocked_turns": 0, "off_turn": 0,
                                          "straight_two": 0, "straight_one": 0}
    assert grade(log=None)["circle"] == {"read": False}


# ================================================================ P28-F, the facing on the swing
def facing_fixture():
    """The player at (10, 10). Attack swings: a1 facing SE at 4 bearing N (350 degrees; a frame facing N before the
    event), a2 facing N (0 off), a3 facing S (4 off), a4's swing not started, a5's target off the frame (unread), a6
    facing N whose frame names it (`act.aid`) after an aim's later accept; the shoves s1 facing E at 5 due east (0)
    and s2 facing NE (1); the stomp k1 facing S at 6 just south (0), s2's late `done` line between its accept and its
    swing event; an aim's swing event not read. The frames after a1, a2, a3, s1 and a6 carry `act.aid` (paired by the
    frame), those after s2, k1 and a5 none (paired by the last accepted line)."""
    z4 = [{"id": 4, "x": 9.83, "y": 9.0, "dist": 1.0}]
    z5 = [{"id": 5, "x": 11.0, "y": 10.0, "dist": 1.0}]

    def f(t, d, zs, aid=None):
        fr = hf(t, me_dir=d, zombies=zs)
        fr["act"] = {"aid": aid, "state": "accepted"} if aid is not None else None
        return fr
    lines = [actl("a1", "attack", "accepted", 1.0), f(1.05, "N", z4, "a1"), swing(1.1), f(1.2, "SE", z4, "a1"),
             f(1.3, "N", z4, "a1"),
             actl("a2", "attack", "accepted", 2.0), swing(2.1), f(2.2, "N", z4, "a2"),
             actl("a3", "attack", "accepted", 3.0), swing(3.1), f(3.2, "S", z4, "a3"),
             actl("s1", "shove", "accepted", 4.0), swing(4.1), f(4.2, "E", z5, "s1"),
             actl("s2", "shove", "accepted", 5.0), swing(5.1), f(5.2, "NE", z5),
             actl("k1", "stomp", "accepted", 6.0), actl("s2", "shove", "done", 6.05), swing(6.1),
             f(6.2, "S", [{"id": 6, "x": 10.0, "y": 10.3}]),
             actl("g1", "aim", "accepted", 7.0), swing(7.1), f(7.2, "W", z4),
             actl("a4", "attack", "accepted", 8.0), swing(8.1, started=False), f(8.2, "W", z4),
             actl("a5", "attack", "accepted", 9.0), swing(9.1), f(9.2, "N", z5),
             actl("a6", "attack", "accepted", 10.0), actl("g2", "aim", "accepted", 10.05), swing(10.1),
             f(10.2, "N", z4, "a6")]
    acts = [row("a1", "attack", 1.0, targetId=4), row("a2", "attack", 2.0, targetId=4),
            row("a3", "attack", 3.0, targetId=4), row("s1", "shove", 4.0, targetId=5),
            row("s2", "shove", 5.0, targetId=5), row("k1", "stomp", 6.0, targetId=6), row("g1", "aim", 7.0, targetId=4),
            row("a4", "attack", 8.0, targetId=4), row("a5", "attack", 9.0, targetId=4),
            row("a6", "attack", 10.0, targetId=4), row("g2", "aim", 10.05, targetId=4)]
    return grade(acts, [], CLEAN, lines)["facing"]


def _off(**kw):
    return dict({"0": 0, "1": 0, "2": 0, "3": 0, "4": 0}, **kw)


def test_the_facing_reads_the_compass_points_off_the_target_on_the_frame_after_each_swing_event():
    assert facing_fixture() == {"read": True, "swings": 5, "off_by_points": _off(**{"0": 2, "3": 1, "4": 1}),
                                "unread": 1, "shoves_off": {"swings": 2, "off_by_points": _off(**{"0": 1, "1": 1}),
                                                            "unread": 0},
                                "stomps_off": {"swings": 1, "off_by_points": _off(**{"0": 1}), "unread": 0},
                                "paired": {"frame": 5, "line": 3}}


def test_the_facing_reads_zero_without_a_swing_and_unread_without_a_log():
    zero = {"swings": 0, "off_by_points": _off(), "unread": 0}
    assert grade(log=CLEAN, frames=[hf(1.0)])["facing"] == dict(zero, read=True, shoves_off=dict(zero),
                                                                stomps_off=dict(zero), paired={"frame": 0, "line": 0})
    assert grade(log=None)["facing"] == {"read": False}


def test_the_compass_reads_the_eight_points_world_x_east_y_south():
    assert [G.compass(dx, dy) for dx, dy in ((0, -1), (1, -1), (1, 0), (1, 1), (0, 1), (-1, 1), (-1, 0), (-1, -1))] \
        == list(G.COMPASS)
    assert G.compass(0, 0) is None and G.compass(-0.17, -1.0) == "N" and G.compass(-0.5, -1.0) == "NW"
    assert G._points("SE", "N") == 3 and G._points("NE", "E") == 1 and G._points("S", "N") == 4
    assert G._points("x", "N") is None and G._points("N", None) is None


# ================================================================ the spec's 1 (c), the client's end
def test_the_client_end_reads_the_stop_and_the_loop_end_s_seq_and_health():
    end = {"seq": 9, "health": 8.903915405273438, "players": []}
    assert grade(log=CLEAN, stop="client_end", end=end)["client_end"] == {
        "read": True, "stopped": "client_end", "seq": 9, "health": 8.903915405273438}
    assert grade(log=CLEAN, stop="death")["client_end"] == {"read": True, "stopped": "death", "seq": None,
                                                            "health": None}
    assert grade(log=None, stop="client_end", end=end)["client_end"] == {"read": False}


# ================================================================ grade_e18 over grade_e17
@pytest.mark.parametrize("fixture", T14.E13_FIXTURES, ids=lambda f: f.__name__)
def test_grade_e18_reads_every_grade_e17_key_unchanged_on_test_gates_e13_s_fixtures(fixture, monkeypatch):
    seen = T14._captured(monkeypatch, fixture)
    a = T14.artifact(seen["actions"], seen["results"], seen["goals"])
    a["stop"]["reason"] = seen["stop"]
    e17 = G17.grade_e17(a, decision_lines=seen["log"], lines=seen["frames"])
    e18 = G.grade_e18(a, decision_lines=seen["log"], lines=seen["frames"])
    assert e18["grade"] == "grade_e18" and all(e18[k]["read"] is True for k in SWEEP)
    assert e18["hits"]["read"] is bool(E._frame_index(seen["frames"])[1])
    skip = ("grade", "report_lines") + NEW
    assert {k: v for k, v in e17.items() if k not in skip} == {k: v for k, v in e18.items() if k not in skip}
    assert e18["report_lines"][:-len(NEW)] == [("gate_e18 " + ln[len("gate_e17 "):]) if ln.startswith("gate_e17 ")
                                               else ln for ln in e17["report_lines"]]


def test_grade_e18_without_a_decision_log_reads_the_new_keys_unread_but_the_hits_off_the_frames():
    g = grade(log=None, frames=[hf(0.0, "Bite"), hf(1.0)])
    assert g["grade"] == "grade_e18" and all(g[k] == {"read": False} for k in SWEEP)
    assert g["hits"]["read"] is True and g["hits"]["runs"] == 1
    assert all(g[k] == {"read": False} for k in NEW17)
    assert G.readings_e18({}, None, []) == {k: {"read": False} for k in NEW}
    assert NEW == ("hits",) + SWEEP


def test_report_lines_e18_names_gate_e18_then_one_line_per_reading_marked_reading_or_inference():
    g = grade(log=CLEAN, frames=[hf(0.0)])
    tail = g["report_lines"][-len(NEW):]
    assert tail == G.lines_e18(g)
    for line, tag in zip(tail, TAGS):
        assert ("(%s)" % tag) in line and "[reading]" in line, line
    assert sum("[inference]" in line for line in tail) == 8
    off = grade(log=None)["report_lines"][-len(NEW):]
    assert "no frames read" in off[0] and all("no decision log read" in line for line in off[1:])
    renamed = G.report_lines_e18(dict(g, gate={"pass": True}))
    assert any(line.startswith("gate_e18 ") for line in renamed)
    assert not any(line.startswith(("gate_e13 ", "gate_e14 ", "gate_e15 ", "gate_e16 ", "gate_e17 "))
                   for line in renamed)
    assert G.gate_e18([]) == E.gate_e13([])
    assert all(len(line) < 2000 for line in G.lines_e18(hits_fixture()))


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
    assert not any(n.startswith("agent.base") and n.split(".")[-1] in ("planner", "world") for n in names), names
    ns = vars(G)
    assert (ns["STRAIN_HARD"], ns["KEEP_R"], ns["AIM_LEG_S"], ns["WOUND_RESERVE"], ns["CIRCLE_TURN"]) == \
        (20.0, 2.5, 2.0, 1, 45.0)
    assert ns["COMPASS"] == ("N", "NE", "E", "SE", "S", "SW", "W", "NW")
    assert ns["compass"].__module__ == G.__name__ and ns["bearing_deg"].__module__ == G.__name__
    assert not any(getattr(v, "__module__", "").startswith(("agent.base.planner", "agent.base.world"))
                   for v in ns.values())


# ================================================================ the mutants
def _mutated(fn_name, edit):
    """grades/e18.py's source with `edit` applied inside function `fn_name` only, executed as a module copy."""
    src = open(G.__file__, encoding="utf-8").read()
    start = src.index("\ndef %s(" % fn_name)
    end = src.index("\ndef ", start + 5)
    new = edit(src[start:end])
    assert new != src[start:end], (fn_name, "the mutant changed nothing")
    ns = {"__name__": "e18_mutant"}
    exec(compile(src[:start] + new + src[end:], "e18_mutant", "exec"), ns)    # noqa: S102 - a scratch copy
    return ns


MUTANTS = [
    # P28-M
    ("_hit_runs", lambda b: b.replace("prev is None", "True"), lambda: hits_fixture()["hits"]["runs"] == 4),
    ("_wound_rises", lambda b: b.replace("max(0, ", "(0 + "), lambda: hits_fixture()["hits"]["wounds"] == 5),
    ("_in_span", lambda b: b.replace("t >= s and ", ""), lambda: hits_fixture()["hits"]["outside"] == 1),
    ("_strike_before", lambda b: b.replace("w - STRIKE_BEFORE_S * 1000.0", "w - 1e9"),
     lambda: hits_fixture()["hits"]["strike_before"][0]["type"] is None),
    ("_nearest_standing", lambda b: b.replace(' if E._d(z).get("onFloor") is not True', ""),
     lambda: hits_fixture()["hits"]["strike_before"][2]["nearest"] is True),
    ("_accepts", lambda b: b.replace(' and ln.get("type") in STRIKES', ""),
     lambda: hits_fixture()["hits"]["strike_before"][0]["type"] is None),
    ("e_hits", lambda b: b.replace("n / k if k else None", "n"), lambda: hits_fixture()["hits"]["per_kill"] == 2.0),
    # P28-A
    ("e_wound_dress", lambda b: b.replace("cl > WOUND_RESERVE", "cl > 5"),
     lambda: wound_fixture()["held_over_reserve"] == 1),
    ("_done", lambda b: b.replace('== "done"', 'in ("done", "rejected")'), lambda: wound_fixture()["done"] == 1),
    ("_quiet", lambda b: b.replace(" and _reaction(f) is None", ""), lambda: wound_fixture()["no_bleed_fall"] == 2.0),
    ("_undressed", lambda b: b.replace(' and p.get("bandaged") is not True', ""),
     lambda: wound_fixture()["no_bleed_fall"] == 2.0),
    ("_undressed", lambda b: b.replace('p.get("wound") is True', 'p.get("wound") is not False'),
     lambda: wound_fixture()["parts_undressed_at_end"] == [11]),
    ("e_wound_dress", lambda b: b.replace('ln.get("branch") != "care" or ', ""), lambda: wound_fixture()["sent"] == 2),
    # P28-B2
    ("e_shove_back", lambda b: b.replace("hi = end if end is not None else w + AIM_LEG_S * 1000.0", "hi = w + 1e9"),
     lambda: back_fixture()["bites_during"] == 1),
    ("e_shove_back", lambda b: b.replace('E._sent(r, "shove") and G17._target(r) == zid', 'E._sent(r, "shove")'),
     lambda: back_fixture()["shoves_after"] == 1),
    ("e_shove_back", lambda b: b.replace(' if ln.get("branch") == "threat" else None', ""),
     lambda: back_fixture()["lines"] == 3),
    # P28-B3
    ("_drift_leg", lambda b: b.replace(' and w.get("stance") is True and w.get("leg") == "stand"', ""),
     lambda: drift_fixture()["lines"] == 3),
    ("e_drift_stand", lambda b: b.replace("wm + BITE_AFTER_S * 1000.0", "wm + 1e9"),
     lambda: drift_fixture()["bites_after"] == 1),
    ("e_drift_stand", lambda b: b.replace('E._sent(r, "shove") and G17._target(r) == zid', 'E._sent(r, "shove")'),
     lambda: drift_fixture()["shoves_after"] == 1),
    # P28-C
    ("e_floor_pain", lambda b: b.replace("p < STRAIN_HARD", "p < 0"), lambda: pain_fixture()["swings"] == 2),
    ("e_floor_pain", lambda b: b.replace("ap >= STRAIN_HARD", "ap > 1000"),
     lambda: pain_fixture()["swings_under_pain_before"] == 1),
    ("e_floor_pain", lambda b: b.replace('E._sent(r, "stomp") and G17._target(r) == zid', 'E._sent(r, "stomp")'),
     lambda: pain_fixture()["stomps_after"] == 1),
    ("e_floor_pain", lambda b: b.replace("G17._swung(L, ln, L.action(ln), acts, swings)", "True"),
     lambda: pain_fixture()["landed"] == 2 and _landed_on_unstarted() == 0),
    # P28-D
    ("e_busy_retry", lambda b: b.replace("E._sent(ln, kind)", 'E._sent(ln, "stomp") or E._sent(ln, "shove")'),
     lambda: busy_fixture()["sends"] == 3),
    ("e_busy_retry", lambda b: b.replace(' and G17._target(r) == zid and _hit(L, r)', ""),
     lambda: busy_fixture()["stomps_landed_after"] == 1),
    ("_hit", lambda b: b.replace('.get("hit") is True', '.get("hit") is not None'),
     lambda: busy_fixture()["stomps_landed_after"] == 1),
    ("e_busy_retry", lambda b: b.replace("L.killed(r) == zid", "L.killed(r) is not None"),
     lambda: busy_fixture()["kills_after"] == 1 and _kills_elsewhere() == 0),
    # P28-E
    ("e_circle", lambda b: b.replace("last is not None and side != last", "False"),
     lambda: circle_fixture()["blocked_turns"] == 2),
    ("e_circle", lambda b: b.replace("abs(abs(t) - CIRCLE_TURN) > 1e-9", "False"),
     lambda: circle_fixture()["off_turn"] == 1),
    ("_standing_within", lambda b: b.replace('E._d(z).get("onFloor") is not True and ', ""),
     lambda: circle_fixture()["straight_two"] == 1),
    ("e_circle", lambda b: b.replace('if ln.get("branch") != "threat":', "if False:"),
     lambda: circle_fixture()["legs"] == 4),
    ("e_circle", lambda b: b.replace("n == 1", "n >= 1"), lambda: circle_fixture()["straight_one"] == 1),
    # P28-F
    ("bearing_deg", lambda b: b.replace("math.atan2(dx, -dy)", "math.atan2(dx, dy)"),
     lambda: G.compass(0, -1) == "N" and G.compass(1, 1) == "SE"),
    ("compass", lambda b: b.replace("(b + 22.5) // 45.0", "b // 45.0"),
     lambda: facing_fixture()["off_by_points"] == _off(**{"0": 2, "3": 1, "4": 1})),
    ("_points", lambda b: b.replace("min(i, 8 - i)", "i"),
     lambda: facing_fixture()["shoves_off"]["off_by_points"] == _off(**{"0": 1, "1": 1})),
    ("e_facing", lambda b: b.replace("pend = []", "pend = pend"), lambda: facing_fixture()["swings"] == 5),
    ("e_facing", lambda b: b.replace("aid = own if own is not None else inferred", "aid = inferred"),
     lambda: facing_fixture()["swings"] == 5),
    ("e_facing", lambda b: b.replace(' and ln.get("attackStarted") is True', ""),
     lambda: facing_fixture()["swings"] == 5),
    ("e_facing", lambda b: b.replace('ln.get("state") == "accepted"', 'ln.get("state") is not None'),
     lambda: facing_fixture()["stomps_off"]["swings"] == 1),
    # the spec's 1 (c)
    ("e_client_end", lambda b: b.replace('.get("end")', '.get("death")'),
     lambda: grade(log=CLEAN, stop="client_end", end={"seq": 9, "health": 8.9})["client_end"]["seq"] == 9),
]


def _landed_on_unstarted():
    """A floor swing under the pain whose act saw only an unstarted swing event: 0 landed."""
    log = [aline(0, 1.0, {"fight": True, "target": 4, "floor_finish": {"target": 4, "health": 1.5, "pain": 30.0}},
                 _act("attack", targetId=4))]
    acts = [row("f1", "attack", 1.0, ended=1.8, targetId=4)]
    return grade(acts, [], log, [swing(1.3, started=False)])["floor_pain"]["landed"]


def _kills_elsewhere():
    """A stomp retry at 4 followed by a kill of another zombie: no kill after."""
    log = [aline(0, 1.0, {"fight": True, "target": 4, "busy_retry": {"target": 4, "kind": "stomp"}},
                 _act("stomp", targetId=4)),
           aline(1, 1.5, {"fight": True, "target": 5}, _act("stomp", targetId=5))]
    acts = [row("k1", "stomp", 1.0, targetId=4), row("k2", "stomp", 1.5, targetId=5)]
    return grade(acts, [res("k2", hit=True, targetDead=True)], log)["busy_retry"]["kills_after"]


@pytest.mark.parametrize("n", range(len(MUTANTS)), ids=lambda n: "%s-%d" % (MUTANTS[n][0], n))
def test_a_mutant_of_each_reading_fails_its_fixture(n, monkeypatch):
    fn_name, edit, holds = MUTANTS[n]
    assert holds(), "the fixture must hold on the real function"
    monkeypatch.setattr(G, fn_name, _mutated(fn_name, edit)[fn_name])
    try:
        survives = holds()
    except Exception:       # a mutant that raises on the fixture is caught by it
        survives = False
    assert not survives, "the mutant of %s survives its fixture" % fn_name


# ================================================================ the real checks: E20 and E19
def _committed(path, name):
    text = open(os.path.join(path, name), encoding="utf-8").read()
    i = text.index("\n{\n")
    return text[:i + 1].splitlines(), json.loads(text[i:])


def _real(path, name):
    p = os.path.join(path, name)
    if not os.path.isfile(p):
        pytest.skip("%s is not checked out" % path)
    g = G.grade_e18(EG18.load(p), None, EG18.load_log(p), state_dir=EG18._dir(p))
    return g, json.loads(json.dumps(EG18.finite(g), sort_keys=True, allow_nan=False))


ZERO = {
    "wound_dress": {"read": True, "sent": 0, "done": 0, "by_part": {}, "part_h": {}, "held": 0, "held_over_reserve": 0,
                    "no_bleed_fall": 0.0, "parts_undressed_at_end": []},
    "shove_back": {"read": True, "lines": 0, "legs": 0, "bites_during": 0, "shoves_after": 0},
    "drift_stand": {"read": True, "lines": 0, "legs": 0, "shoves_after": 0, "bites_after": 0},
    "floor_pain": {"read": True, "swings": 0, "landed": 0, "kills": 0, "stomps_after": 0,
                   "swings_under_pain_before": 0},
    "busy_retry": {"read": True, "sends": 0, "by_kind": {}, "stomps_landed_after": 0, "kills_after": 0},
    "circle": {"read": True, "legs": 0, "sides": {}, "blocked_turns": 0, "off_turn": 0, "straight_two": 0,
               "straight_one": 0},
}


def zero(k, straight_one):
    """ZERO[k], the circle's `straight_one` an older log's own count (its straight `back` legs at one standing zombie
    within KEEP_R: the circle off, no rule check)."""
    return dict(ZERO[k], straight_one=straight_one) if k == "circle" else ZERO[k]


def test_grade_e18_on_e20_keeps_every_grade_e17_key_as_the_committed_e_grade_txt_and_reads_the_new_keys():
    """E20 ran survival iteration 20 on PZA/1.7.1 (no part `wound` field, no iteration 21 why) and stopped before
    Plan 28 Task 1's `client_end` (its stop reads `death`, no `loop.end`): every rule key reads 0; the hits read its
    six bite reactions over its seven kills, the facing its 36 attack swings each on the target's bearing (and its two
    stomps'), each paired by its frame's own `act.aid`; the circle's `straight_one` its five straight `back` legs at one
    standing zombie (the circle not yet a rule)."""
    g, mine = _real(E20, "e_day_20.json")
    assert g["grade"] == "grade_e18"
    for k in ZERO:
        assert g[k] == zero(k, 5), k
    h = g["hits"]
    assert (h["runs"], h["kills"], h["per_kill"], h["kinds"]) == (6, 7, 6 / 7, {"Bite": 6})
    assert g["kills"]["planner"] == 7
    assert g["facing"] == {"read": True, "swings": 36, "off_by_points": _off(**{"0": 36}), "unread": 0,
                           "shoves_off": {"swings": 0, "off_by_points": _off(), "unread": 0},
                           "stomps_off": {"swings": 2, "off_by_points": _off(**{"0": 2}), "unread": 0},
                           "paired": {"frame": 38, "line": 0}}
    assert g["client_end"] == {"read": True, "stopped": "death", "seq": None, "health": None}
    _, committed = _committed(E20, "e_grade.txt")
    for k in NEW:
        mine.pop(k)
    mine["grade"] = "grade_e17"
    mine["report_lines"] = [("gate_e17 " + ln[len("gate_e18 "):]) if ln.startswith("gate_e18 ") else ln
                            for ln in mine["report_lines"][:-len(NEW)]]
    assert mine == committed


def test_grade_e18_on_e19_reads_no_hit_over_its_six_kills():
    """E19 reached its day cap with no wound (#4552): no reaction run, the hits per kill 0 over six."""
    g, _ = _real(E19, "e_day_19.json")
    h = g["hits"]
    assert (h["runs"], h["kills"], h["per_kill"], h["wounds"], h["kinds"]) == (0, 6, 0.0, 0, {})
    assert g["client_end"] == {"read": True, "stopped": "day_cap", "seq": None, "health": None}


def test_e_grade_18_prints_the_committed_e_grade_txt_s_lines_then_the_new_ones():
    """`e_grade_18.py` on the committed E20 artifact: the committed `e_grade.txt`'s report lines byte for byte (CRLF
    folded), then the nine new lines, then the JSON whose inherited keys equal the committed."""
    p = os.path.join(E20, "e_day_20.json")
    if not os.path.isfile(p):
        pytest.skip("%s is not checked out" % E20)
    script = os.path.join(TESTING, "agent", "drivers", "e_grade_18.py")
    r = subprocess.run([sys.executable, script, p], capture_output=True, cwd=TESTING)
    assert r.returncode == 0
    raw = r.stdout.replace(b"\r\n", b"\n")
    want_raw = open(os.path.join(E20, "e_grade.txt"), "rb").read().replace(b"\r\n", b"\n")
    head = want_raw[:want_raw.index(b"\n{\n") + 1]
    assert raw.startswith(head)
    text = raw.decode("utf-8")
    i = text.index("\n{\n")
    printed, got = text[:i + 1].splitlines(), json.loads(text[i:])
    want_lines, want = _committed(E20, "e_grade.txt")
    assert printed[:-len(NEW)] == want_lines and len(printed) == len(want_lines) + len(NEW)
    assert got["grade"] == "grade_e18" and printed[-len(NEW):] == got["report_lines"][-len(NEW):]
    for k in NEW:
        got.pop(k)
    got["grade"] = "grade_e17"
    got["report_lines"] = got["report_lines"][:-len(NEW)]
    assert got == want


def test_e_grade_18_refuses_an_argument_it_does_not_define():
    """Read statically (CLAUDE.md section 5: a driver's refusal is tested without invoking it on a bad argument): its
    main answers usage, exit 2, on no path or more than two outside `--chain`."""
    src = open(EG18.__file__, encoding="utf-8").read()
    assert "if not paths or (not chain and len(paths) > 2):" in src and "return 2" in src
    assert "from agent.base.grades.e18 import gate_e18, grade_e18, report_lines_e18" in src
    assert "usage: e_grade_18.py" in src and "e17" not in src[src.index('"""', 3):]


def test_the_strike_window_is_two_seconds_before_the_run():
    assert G.STRIKE_BEFORE_S == 2.0 and G.BITE_AFTER_S == G17.BITE_AFTER_S and G.FOLLOW_LINES == G17.FOLLOW_LINES
    assert T0 == 1000.0


def test_e_grade_18_on_e21_reproduces_the_committed_e_grade_txt_byte_for_byte():
    """Ruling P26-Q: `e_grade_18.py` on the committed E21 artifact (the first session graded through `grade_e18`)
    reproduces its committed `e_grade.txt` byte for byte (CRLF folded), so a drift in any live name read through the
    grade chain (`grade_e17` to `grade_e14`, `gates_e`) fails here."""
    p = os.path.join(E21, "e_day_21.json")
    if not os.path.isfile(p):
        pytest.skip("%s is not checked out" % E21)
    script = os.path.join(TESTING, "agent", "drivers", "e_grade_18.py")
    r = subprocess.run([sys.executable, script, p], capture_output=True, cwd=TESTING)
    assert r.returncode == 0
    want = open(os.path.join(E21, "e_grade.txt"), "rb").read().replace(b"\r\n", b"\n")
    assert r.stdout.replace(b"\r\n", b"\n") == want
