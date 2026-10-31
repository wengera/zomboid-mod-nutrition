"""base/gates_e.py pass 12 (Plan 25 Task 11), offline: `grade_e12` and its five readings of survival iteration 15 (the unarmed
fight P25-P, the trapped hold's care ticks P25-Q, the `toward` acceptance P25-R, the low fight P25-S, the run-counted breaks
P25-T), each on a fixture where it reads zero and one where it counts, a mutant per reading, `grade_e11` unchanged on E13 under
`grade_e12`, and `e_grade_12.py`."""
import json
import os
import subprocess
import sys

import pytest

from agent.base import gates_e as E
from .test_gates_e import art
from .test_gates_e7 import T0, _mutated, act, aline, result, zf
from .test_gates_e11 import bline

HERE = os.path.dirname(os.path.abspath(__file__))
TESTING = os.path.dirname(os.path.dirname(HERE))
E13 = os.path.join(TESTING, "artifacts", "e_day_13-20261030-213219")
NEW = ("unarmed", "trapped_care", "toward", "low_fight", "run_breaks")


def grade(actions=(), results=(), log=None, frames=(), calls=None, stop="day_cap"):
    a = art(actions=list(actions), results=list(results), startPyMs=T0 * 1000.0, t_loop0_ms=T0 * 1000.0)
    a["stop"]["reason"] = stop
    if calls is not None:
        a["loop"]["llm"] = {"calls": list(calls)}
    return E.grade_e12(a, decision_lines=log, lines=list(frames))


def _act(type_, **args):
    return {"type": type_, "args": args}


# ================================================================ the committed artifact
def _load(name):
    p = os.path.join(E13, name)
    if not os.path.isfile(p):
        pytest.skip("%s is not checked out" % E13)
    return p


def _e13():
    with open(_load("e_day_13.json"), encoding="utf-8") as fh:
        o = json.load(fh)
    log = [json.loads(l) for l in open(_load("decision.log"), encoding="utf-8") if l.strip()]
    return o, log


def test_grade_e12_on_e13_changes_only_the_grade_name_the_five_readings_and_the_report():
    o, log = _e13()
    e11 = E.grade_e11(o, decision_lines=log, state_dir=E13)
    e12 = E.grade_e12(o, decision_lines=log, state_dir=E13)
    skip = ("grade", "report_lines") + NEW
    assert e12["grade"] == "grade_e12" and all(e12[k]["read"] is True for k in NEW)
    assert {k: v for k, v in e11.items() if k not in skip} == {k: v for k, v in e12.items() if k not in skip}
    keep = lambda r: [l for l in r if not l.startswith("gate_e")]
    assert keep(e12["report_lines"])[:len(keep(e11["report_lines"]))] == keep(e11["report_lines"])
    assert len(e12["report_lines"]) == len(e11["report_lines"]) + 5
    # E13 ran iteration 14 on an armed chain: none of the iteration 15 whys existed
    assert e12["unarmed"]["lines"] == e12["unarmed"]["runs"] == e12["unarmed"]["flee_unarmed"] == 0
    assert e12["low_fight"]["lines"] == e12["low_fight"]["runs"] == e12["low_fight"]["run_health"].__len__() == 0
    assert e12["trapped_care"]["care_lines"] == e12["trapped_care"]["care_tried"] == 0
    assert (e12["toward"]["llm_calls"], e12["toward"]["beyond"], e12["toward"]["explore"]) == (0, 0, 0)
    assert any("a scripted chain reads 0 by construction" in l for l in e12["report_lines"])
    # P25-L's break and the `health` flee existed on E13, so these two read what they read
    assert e12["run_breaks"]["breaks"] == e12["corner_kinds"]["miss_breaks"]


def test_grade_e12_on_e13_reads_the_health_flees_split_and_the_new_counts_at_their_pinned_values():
    o, log = _e13()
    g = E.grade_e12(o, decision_lines=log, state_dir=E13)
    lo = g["low_fight"]
    # E13 ran iteration 14 (no LOW_FIGHT): its 159 `health` flee lines, every one on the threat branch, split by the frame and
    # the line's inputs; the one-zombie share (63) is what the low fight takes once the switch is on (iteration 15 must read 0)
    assert (lo["flee_health"], lo["flee_health_other_branch"], lo["health_low"]) == (159, 0, 30.32921600341797)
    assert (lo["flee_health_floor"], lo["flee_health_pair"], lo["flee_health_misfire"], lo["flee_health_other"]) == (0, 5, 63, 91)
    assert (g["unarmed"]["flee_unarmed_other"], g["unarmed"]["flee_unarmed_abandon"]) == (0, 0)
    assert (g["run_breaks"]["pair_breaks"], g["run_breaks"]["pair_run_breaks"]) == (3, 0)


def test_grade_e11_on_e13_still_reproduces_the_committed_report_byte_for_byte():
    o, log = _e13()
    r = E.grade_e11(o, decision_lines=log, state_dir=E13)["report_lines"]
    want = open(_load("e_grade.txt"), encoding="utf-8").read().split("\n{\n")[0].split("\n")
    assert r == want[:len(r)]


# ================================================================ P25-P, the unarmed fight
def unarmed_fixture(flag=True, tail=True):
    f = lambda n, t, w, a=None, s=True: aline(n, t, dict({"fight": True, "target": 1}, **w), a, sent=s)
    u = {"unarmed_fight": True} if flag else {}
    log = [f(0, 0.0, dict(u, shove="unarmed"), _act("shove", targetId=1)),
           f(1, 1.0, u, _act("stomp", targetId=1)),
           bline(2, 2.0, "goal", {"goal": "Rest"}, None, sent=False),
           f(3, 3.0, u, None, False),
           f(4, 3.2, u, _act("stomp", targetId=1)),
           f(5, 3.5, u, _act("attack", targetId=1)),
           aline(6, 4.0, dict({"flee": "unarmed"}, **u), _act("steer")),   # a flee line carrying the key: not a fight line
           f(7, 5.0, {}, _act("attack", targetId=2)),                    # an armed fight: never counted
           f(8, 5.5, {"unarmed_fight": False}, None, False),
           bline(9, 6.0, "care", {"reason": "x"}, None, sent=False, others={"threat": {"flee": "unarmed", "trapped": 1}})]
    if tail:   # the flee after a knock-down or a fallen target (review-t10 4c): two counted, one after a goal line is not
        log += [aline(10, 7.0, {"knocked": 5}, None, sent=False), aline(11, 7.5, {"flee": "unarmed"}, _act("steer")),
                bline(12, 8.0, "goal", {"goal": "Rest"}, None, sent=False, others={"threat": {"knocked": 5}}),
                aline(13, 8.5, {"flee": "unarmed"}, _act("steer")),
                aline(14, 9.0, {"downed": 5}, None, sent=False), aline(15, 9.5, {"flee": "unarmed"}, _act("steer"))]
    acts = [act("s1", "shove", 0.0, targetId=1), act("s2", "stomp", 1.0, targetId=1)]
    return grade(acts, [result("s2", targetDead=True)], log)["unarmed"]


def test_the_unarmed_fight_counts_the_lines_runs_actions_kills_and_the_unarmed_flee():
    g = unarmed_fixture()
    assert g["read"] is True and (g["lines"], g["runs"], g["shoves"], g["stomps"], g["attacks"]) == (5, 2, 1, 2, 1)
    assert (g["shove_unarmed"], g["kills"]) == (1, 1)
    # the flee counts on every branch: the trapped tick the care took (line 9) beside the threat branch's five
    assert (g["flee_unarmed"], g["flee_unarmed_other"], g["flee_unarmed_abandon"]) == (5, 1, 2)


def test_the_unarmed_flee_after_a_knock_down_reads_zero_without_one():
    g = unarmed_fixture(tail=False)
    assert (g["flee_unarmed"], g["flee_unarmed_other"], g["flee_unarmed_abandon"]) == (2, 1, 0)


def test_the_unarmed_fight_reads_zero_without_the_why_and_unread_without_a_log():
    g = unarmed_fixture(flag=False)
    assert (g["lines"], g["runs"], g["shoves"], g["stomps"], g["attacks"], g["shove_unarmed"], g["kills"]) == (0,) * 7
    assert (g["flee_unarmed"], g["flee_unarmed_abandon"]) == (5, 2)
    assert grade(log=None)["unarmed"] == {"read": False}


# ================================================================ P25-Q, the trapped hold's care ticks
def trapped_fixture(flag=True):
    t = {"flee": "unarmed", "trapped": 1} if flag else {"flee": "unarmed"}
    bandage = lambda n, tt: bline(n, tt, "care", {"reason": "bleeding", "part": 3}, _act("bandage", part=3), others={"threat": t})
    log = [bline(0, 0.0, "threat", t, None, sent=False),
           bline(1, 1.0, "threat", t, None, sent=False, others={"care": {}}),
           bandage(2, 2.0),
           bline(3, 3.0, "care", {"reason": "unwear", "part": 3}, _act("unwear", itemId=9), others={"threat": t}),
           bandage(4, 4.0),
           bline(5, 5.0, "threat", {"flee": "unarmed"}, None, sent=False),
           bline(6, 6.0, "goal", {"goal": "Rest"}, None, sent=False, others={"threat": t})]
    acts = [act("b1", "bandage", 2.0, part=3), dict(act("b2", "bandage", 4.0, part=3), state="failed")]
    return grade(acts, [], log)["trapped_care"]


def test_the_trapped_care_counts_the_hold_the_care_ticks_the_bandages_and_what_else_was_sent():
    g = trapped_fixture()
    assert g["read"] is True and (g["trapped_lines"], g["hold_lines"], g["care_lines"]) == (6, 2, 3)
    assert (g["care_why"], g["care_tried"], g["care_sent"]) == (3, 1, 3)
    assert (g["bandages"], g["bandages_done"], g["other_sent"]) == (2, 1, {"unwear": 1})


def test_the_trapped_care_reads_zero_without_a_trapped_why_and_unread_without_a_log():
    g = trapped_fixture(flag=False)
    assert g["trapped_lines"] == g["hold_lines"] == g["care_lines"] == g["care_why"] == g["care_sent"] == 0
    assert grade(log=None)["trapped_care"] == {"read": False}


# ================================================================ P25-R, the `toward` acceptance
def calls_fixture(with_calls=True):
    ok = lambda dt, x, y, kind="ExploreToward": {"wall": T0 + dt, "ok": True, "error": None,
                                                 "goal": {"type": kind, "x": x, "y": y} if kind == "ExploreToward"
                                                 else {"type": kind, "building": 2}}
    bad = lambda dt, err: {"wall": T0 + dt, "ok": False, "error": err, "goal": None}
    calls = [ok(1.0, 10, 10), ok(1.5, 120, 100), ok(1.7, 100, 101), ok(2.0, 0, 0, "LootBuilding"),
             bad(2.5, "invalid: out of range"), bad(3.0, "invalid: in the woods"), ok(-5.0, 10, 10),
             dict(ok(2.2, 10, 10), ok=False, error="invalid: refused")]
    return grade(log=[], frames=[zf(0.5, x=100.0, y=100.0)], calls=calls if with_calls else None)["toward"]


def test_the_toward_acceptance_counts_the_explores_beyond_range_the_refusals_and_the_frameless():
    g = calls_fixture()
    assert g["read"] is True and (g["llm_calls"], g["explore"], g["beyond"], g["no_frame"]) == (8, 4, 1, 1)
    assert (g["refused_range"], g["refused_woods"]) == (1, 1)
    assert abs(g["max_dist"] - ((89.5 ** 2) * 2) ** 0.5) < 1e-9


def test_the_toward_acceptance_reads_zero_on_a_chain_and_says_so():
    g = calls_fixture(with_calls=False)
    assert (g["llm_calls"], g["explore"], g["beyond"], g["max_dist"], g["no_frame"]) == (0, 0, 0, None, 0)
    assert any("a scripted chain reads 0 by construction" in l for l in grade(log=[])["report_lines"])
    assert not any("a scripted chain reads 0" in l for l in grade(log=[], calls=[{"wall": T0, "ok": False, "goal": None,
                                                                                     "error": "timeout"}])["report_lines"])


# ================================================================ P25-S, the low fight
def hframe(t, h):
    f = zf(t)
    f["body"]["health"] = h
    return f


def low_fixture(flag=True):
    f = lambda n, t, w, a=None, s=True: aline(n, t, dict({"fight": True, "target": 1}, **w), a, sent=s)
    u = {"low_fight": True} if flag else {}
    log = [f(0, 0.0, dict(u, shove="low"), _act("shove", targetId=1)),
           f(1, 1.0, u, _act("stomp", targetId=1)),
           bline(2, 2.0, "goal", {"goal": "Rest"}, None, sent=False),
           f(3, 3.0, u, None, False),
           f(4, 3.5, u, _act("attack", targetId=1)),
           aline(5, 4.0, {"flee": "health"}, _act("steer")),
           f(6, 5.0, {}, _act("attack", targetId=2))]
    frames = [hframe(0.0, 38), hframe(1.0, 36), hframe(3.0, 25), hframe(3.5, 24), hframe(4.0, 18), hframe(5.0, 60)]
    acts = [act("s1", "shove", 0.0, targetId=1), act("s2", "stomp", 1.0, targetId=1)]
    return grade(acts, [result("s2", targetDead=True)], log, frames)["low_fight"]


def test_the_low_fight_counts_the_lines_runs_actions_kills_the_run_health_and_the_health_flees():
    g = low_fixture()
    assert g["read"] is True and (g["lines"], g["runs"], g["shoves"], g["stomps"], g["attacks"]) == (4, 2, 1, 1, 1)
    assert (g["shove_low"], g["kills"], g["flee_health"], g["health_low"]) == (1, 1, 1, 18)
    assert g["run_health"] == [{"lines": 2, "first": 38, "last": 36}, {"lines": 2, "first": 25, "last": 24}]


def split_fixture(kinds=True):
    """`health` flee lines of each kind: under the floor (inputs.health 15), two zombies within DANGER_R, one zombie at the
    floor or above (the misfire), none; a care-branch line carrying the threat's flee (counted, with the other branch); and
    two lines without inputs.health and threats, read off the frame (two zombies, one fallen, within DANGER_R; one beyond)."""
    def fl(n, t, health, threats, branch="threat"):
        ln = aline(n, t, {"flee": "health"}, _act("steer"), branch=branch)
        ln["inputs"].update(health=health, threats=threats)
        return ln
    if not kinds:
        return grade(log=[aline(0, 0.0, {"fight": True, "target": 1}, None, sent=False), fl(1, 1.0, 100, 0)])["low_fight"]
    care = bline(5, 5.0, "care", {"reason": "x"}, None, sent=False, others={"threat": {"flee": "health", "trapped": 1}})
    care["inputs"].update(health=30, threats=2)
    log = [fl(0, 0.0, 15, 1), fl(1, 1.0, 19.5, 3), fl(2, 2.0, 30, 2), fl(3, 3.0, 20, 1), fl(4, 4.0, 39, 0), care,
           aline(6, 6.0, {"flee": "health"}, _act("steer")), aline(7, 7.0, {"flee": "health"}, _act("steer"))]
    frames = [hframe(6.0, 35), hframe(7.0, 35)]
    frames[0]["zombies"] = [{"id": 1, "dist": 3.0}, {"id": 2, "dist": 6.0, "onFloor": True}, {"id": 3, "dist": 6.5}]
    frames[1]["zombies"] = [{"id": 1, "dist": 3.0}, {"id": 2, "dist": 6.5}]
    return grade(log=log, frames=frames)["low_fight"]


def test_the_low_fight_splits_the_health_flees_into_floor_pair_misfire_and_other():
    g = split_fixture()
    assert g["flee_health"] == 8 and g["flee_health_other_branch"] == 1
    assert (g["flee_health_floor"], g["flee_health_pair"], g["flee_health_misfire"], g["flee_health_other"]) == (2, 3, 2, 1)
    assert g["flee_health_floor"] + g["flee_health_pair"] + g["flee_health_misfire"] + g["flee_health_other"] == g["flee_health"]


def test_the_low_fight_split_reads_zero_without_a_health_flee_under_the_misfire_and_the_floor():
    g = split_fixture(kinds=False)
    assert (g["flee_health_floor"], g["flee_health_pair"], g["flee_health_misfire"]) == (0, 0, 0)
    assert (g["flee_health"], g["flee_health_other"], g["flee_health_other_branch"]) == (1, 1, 0)
    # the unmutated low-fight fixture's only flee (health 18 off the frame, no zombie listed) is under the floor
    assert low_fixture()["flee_health_floor"] == 1 and low_fixture()["flee_health_misfire"] == 0


def test_the_low_fight_reads_zero_without_the_why_and_unread_without_a_log():
    g = low_fixture(flag=False)
    assert (g["lines"], g["runs"], g["shoves"], g["stomps"], g["attacks"], g["shove_low"], g["kills"]) == (0,) * 7
    assert g["run_health"] == [] and g["flee_health"] == 1 and g["health_low"] == 18
    assert grade(log=None)["low_fight"] == {"read": False}


# ================================================================ P25-T, the run-counted breaks
def breaks_fixture(flag=True):
    def f(n, t, zid, corner=None, kind="shove"):
        why = {"fight": True, "target": zid}
        if corner:
            why["corner"] = corner
        return aline(n, t, why, _act(kind, targetId=zid) if kind else None, sent=bool(kind))
    cs = lambda zid: {"kind": "shove", "shoved": zid, "n": 1, "sore": False} if flag else None
    log = [f(0, 0.0, 5),
           f(1, 5.0, 5, cs(5)),
           f(2, 10.0, 5, cs(5)),
           f(3, 15.0, 5, {"kind": "break", "shoved": 5, "n": 1, "misses": 3} if flag else None, kind="steer" if flag else "shove"),
           f(4, 16.0, 6),
           f(5, 17.0, 6),
           f(6, 18.0, 6, {"kind": "break", "shoved": 6, "n": 1, "misses": 3} if flag else None, kind="steer" if flag else None),
           f(7, 20.0, 7, {"kind": "break", "shoved": 7, "n": 1, "misses": 2} if flag else None, kind="steer" if flag else None),
           f(8, 21.0, 8, {"kind": "break", "shoved": 8, "n": 2} if flag else None, kind="steer" if flag else None),
           f(9, 22.0, 9),
           f(10, 23.0, 9, {"kind": "break", "shoved": 9, "n": 2} if flag else None, kind="steer" if flag else None),
           f(11, 24.0, 10),
           f(12, 30.0, 10, {"kind": "break", "shoved": 10, "n": 2} if flag else None, kind="steer" if flag else None)]
    acts = [act("s%d" % i, "shove", t, targetId=z) for i, t, z in ((0, 0.0, 5), (1, 5.0, 5), (2, 10.0, 5), (4, 16.0, 6),
                                                                  (5, 17.0, 6), (9, 22.0, 9), (11, 24.0, 10))]
    res = [result("s0", knockdown=False), result("s1", knockdown=False), result("s2", knockdown=False),
           result("s4", knockdown=True), result("s5", knockdown=False)]
    return grade(acts, res, log)["run_breaks"]


def test_the_run_breaks_count_the_breaks_their_spacing_and_the_corner_s_answers_to_a_miss():
    g = breaks_fixture()
    assert g["read"] is True and (g["breaks"], g["run_breaks"], g["misses"]) == (3, 2, [3, 3, 2])
    assert g["spacings"] == [[5.0, 5.0], [], []] and (g["spaced"], g["max_gap"]) == (1, 5.0)
    assert (g["corner_shove"], g["shove_after_miss"], g["answered_shove"]) == (2, 2, 2)
    # the two-zombie breaks (no `misses`): target 8 never shoved, 9 one second after its shove, 10 six seconds after: only the
    # last was the run's consult outside the window
    assert (g["pair_breaks"], g["pair_run_breaks"]) == (3, 1)


def test_the_run_breaks_read_zero_without_a_corner_why_and_unread_without_a_log():
    g = breaks_fixture(flag=False)
    assert (g["breaks"], g["run_breaks"], g["spaced"], g["corner_shove"], g["answered_shove"]) == (0, 0, 0, 0, 0)
    assert (g["pair_breaks"], g["pair_run_breaks"]) == (0, 0)
    assert g["shove_after_miss"] == 3 and g["max_gap"] is None
    assert grade(log=None)["run_breaks"] == {"read": False}


# ================================================================ the report
def test_the_report_names_the_five_rules_and_marks_reading_or_inference():
    g = grade(log=[aline(0, 0.0, {"fight": True, "target": 1}, None, sent=False)])
    r = g["report_lines"]
    assert g["grade"] == "grade_e12" and set(g) >= set(NEW)
    tags = ("unarmed fight (P25-P) [reading]", "trapped care (P25-Q) [reading]", "toward (P25-R) [reading",
            "low fight (P25-S) [reading]", "run breaks (P25-T) [reading]")
    for t in tags:
        assert any(l.startswith(t) for l in r), t
    assert sum("[inference" in l for l in r) >= 7
    lo = next(l for l in r if l.startswith("low fight"))
    assert "the LOW_FIGHT misfire" in lo and "under the floor [reading]" in lo and "two or more zombies" in lo
    assert any("following a `knocked` or `downed` line [inference]" in l for l in r)
    assert any("two-zombie breaks" in l and "[inference]" in l for l in r)
    assert not any(l.startswith("gate_e9 ") or l.startswith("gate_e10 ") or l.startswith("gate_e11 ") for l in r)
    nolog = grade(log=None)["report_lines"]
    assert any(l == "unarmed fight (P25-P): no decision log read" for l in nolog)
    assert E.gate_e12([art()]) == E.gate_e11([art()])


# ================================================================ a mutant per reading
MUTANTS = [
    ("_flag_fight", lambda b: b.replace("L.is_fight(ln) and ", ""), lambda: unarmed_fixture()["lines"] == 5),
    ("_flag_fight", lambda b: b.replace("is True", "is not None"), lambda: unarmed_fixture()["lines"] == 5),
    ("e_unarmed", lambda b: b.replace('"unarmed_fight"', '"low_fight"'), lambda: unarmed_fixture()["lines"] == 5),
    ("e_unarmed", lambda b: b.replace('"stomp"', '"shove"'), lambda: unarmed_fixture()["stomps"] == 2),
    ("e_unarmed", lambda b: b.replace('"attack"', '"stomp"'), lambda: unarmed_fixture()["attacks"] == 1),
    ("e_unarmed", lambda b: b.replace('.get("shove") == "unarmed"', '.get("shove") == "xx"'), lambda: unarmed_fixture()["shove_unarmed"] == 1),
    ("_flee_lines", lambda b: b.replace('L.why(ln).get("flee") == reason', 'ln.get("branch") == "threat" and L.why(ln).get("flee") == reason'),
     lambda: unarmed_fixture()["flee_unarmed"] == 5),
    ("_flee_lines", lambda b: b.replace('L.why(ln).get("flee") == reason', 'ln.get("branch") == "threat" and L.why(ln).get("flee") == reason'),
     lambda: split_fixture()["flee_health"] == 8),
    ("e_unarmed", lambda b: b.replace('ln.get("branch") != "threat"', "False"), lambda: unarmed_fixture()["flee_unarmed_other"] == 1),
    ("e_unarmed", lambda b: b.replace('before.get("branch") == "threat"', "True"), lambda: unarmed_fixture()["flee_unarmed_abandon"] == 2),
    ("e_unarmed", lambda b: b.replace('why.get("knocked") is not None or ', ""), lambda: unarmed_fixture()["flee_unarmed_abandon"] == 2),
    ("e_unarmed", lambda b: b.replace('or why.get("downed") is not None', ""), lambda: unarmed_fixture()["flee_unarmed_abandon"] == 2),
    ("e_low_fight", lambda b: b.replace('h < FLEE_HEALTH_FLOOR', 'h <= FLEE_HEALTH_FLOOR'), lambda: split_fixture()["flee_health_floor"] == 2),
    ("e_low_fight", lambda b: b.replace('h < FLEE_HEALTH_FLOOR', 'h < 0'), lambda: split_fixture()["flee_health_floor"] == 2),
    ("e_low_fight", lambda b: b.replace('n >= 2', 'n >= 3'), lambda: split_fixture()["flee_health_pair"] == 3),
    ("e_low_fight", lambda b: b.replace('n == 1 and h is not None', 'False'), lambda: split_fixture()["flee_health_misfire"] == 2),
    ("e_low_fight", lambda b: b.replace('n == 1 and h is not None', 'n == 0'), lambda: split_fixture()["flee_health_misfire"] == 2),
    ("e_low_fight", lambda b: b.replace('ln.get("branch") != "threat"', "False"), lambda: split_fixture()["flee_health_other_branch"] == 1),
    ("_danger_count", lambda b: b.replace('z["dist"] <= DANGER_R', 'z["dist"] < DANGER_R'), lambda: split_fixture()["flee_health_pair"] == 3),
    ("_danger_count", lambda b: b.replace('z["dist"] <= DANGER_R', 'z["dist"] <= 99'), lambda: split_fixture()["flee_health_pair"] == 3),
    ("_danger_count", lambda b: b.replace('_n(_d(ln.get("inputs")).get("threats"))', "None"), lambda: split_fixture()["flee_health_pair"] == 3),
    ("_line_health", lambda b: b.replace('_n(_d(ln.get("inputs")).get("health"))', "None"), lambda: split_fixture()["flee_health_floor"] == 2),
    ("e_unarmed", lambda b: b.replace("L.kill_ids(lines)", "[]"), lambda: unarmed_fixture()["kills"] == 1),
    ("e_trapped_care", lambda b: b.replace('"trapped" not in L.why(ln)', "False"), lambda: trapped_fixture()["trapped_lines"] == 6),
    ("e_trapped_care", lambda b: b.replace('"care" in _d', '"xx" in _d'), lambda: trapped_fixture()["care_tried"] == 1),
    ("e_trapped_care", lambda b: b.replace('kind == "bandage"', 'kind == "xx"'), lambda: trapped_fixture()["bandages"] == 2),
    ("e_trapped_care", lambda b: b.replace('row.get("state") == "done"', 'row.get("state") == "xx"'),
     lambda: trapped_fixture()["bandages_done"] == 1),
    ("e_trapped_care", lambda b: b.replace('ln.get("branch") == "threat"', 'ln.get("branch") != "care"'),
     lambda: trapped_fixture()["hold_lines"] == 2),
    ("e_trapped_care", lambda b: b.replace('why_n += 1 if _bw(ln, "care") else 0', "why_n += 1"),
     lambda: trapped_fixture()["care_why"] == 3),
    ("e_toward", lambda b: b.replace("d > EXPLORE_MAX_TILES", "d < EXPLORE_MAX_TILES"), lambda: calls_fixture()["beyond"] == 1),
    ("e_toward", lambda b: b.replace('"invalid: in the woods"', '"invalid: xx"'), lambda: calls_fixture()["refused_woods"] == 1),
    ("e_toward", lambda b: b.replace('"invalid: out of range"', '"invalid: xx"'), lambda: calls_fixture()["refused_range"] == 1),
    ("e_toward", lambda b: b.replace("nof += 1", "nof += 0"), lambda: calls_fixture()["no_frame"] == 1),
    ("e_toward", lambda b: b.replace('g.get("type") != "ExploreToward"', "False"), lambda: calls_fixture()["explore"] == 4),
    ("e_toward", lambda b: b.replace('c.get("ok") is not True', "False"), lambda: calls_fixture()["explore"] == 4),
    ("e_low_fight", lambda b: b.replace('"low_fight"', '"unarmed_fight"'), lambda: low_fixture()["lines"] == 4),
    ("e_low_fight", lambda b: b.replace('_flee_lines(L, "health")', '_flee_lines(L, "xx")'), lambda: low_fixture()["flee_health"] == 1),
    ("e_low_fight", lambda b: b.replace('== "low")', '== "xx")'), lambda: low_fixture()["shove_low"] == 1),
    ("e_low_fight", lambda b: b.replace("lines + flee", "lines"), lambda: low_fixture()["health_low"] == 18),
    ("e_low_fight", lambda b: b.replace('"last": _health_at(L, r[-1])', '"last": _health_at(L, r[0])'),
     lambda: low_fixture()["run_health"][0]["last"] == 36),
    ("e_low_fight", lambda b: b.replace('_sent_count(lines, "attack")', "0"), lambda: low_fixture()["attacks"] == 1),
    ("_health_at", lambda b: b.replace('"health"', '"xx"'), lambda: low_fixture()["health_low"] == 18),
    ("e_run_breaks", lambda b: b.replace("k >= SHOVE_BREAK_N", "True"), lambda: breaks_fixture()["run_breaks"] == 2),
    ("e_run_breaks", lambda b: b.replace('c.get("kind") != "break" or c.get("misses") is None', 'c.get("kind") != "break"'),
     lambda: breaks_fixture()["breaks"] == 3),
    ("e_run_breaks", lambda b: b.replace("x > SHOVE_REPEAT_S", "x > 99"), lambda: breaks_fixture()["spaced"] == 1),
    ("e_run_breaks", lambda b: b.replace("w - p > SHOVE_REPEAT_S", "w - p > 99"), lambda: breaks_fixture()["pair_run_breaks"] == 1),
    ("e_run_breaks", lambda b: b.replace("w - p > SHOVE_REPEAT_S", "w - p >= 0"), lambda: breaks_fixture()["pair_run_breaks"] == 1),
    ("e_run_breaks", lambda b: b.replace('lastw[zid] = _n(ln.get("wall"))', "pass"), lambda: breaks_fixture()["pair_run_breaks"] == 1),
    ("e_run_breaks", lambda b: b.replace('c.get("kind") == "break" and c.get("misses") is None', 'c.get("kind") == "break"'),
     lambda: breaks_fixture()["pair_breaks"] == 3),
    ("e_run_breaks", lambda b: b.replace("[-k:]", "[-1:]"), lambda: breaks_fixture()["spacings"][0] == [5.0, 5.0]),
    ("e_run_breaks", lambda b: b.replace("if last.get(zid) is False:", "if True:"), lambda: breaks_fixture()["shove_after_miss"] == 2),
    ("e_run_breaks", lambda b: b.replace("if kd is True:", "if False:"), lambda: breaks_fixture()["spacings"][1] == []),
    ("e_run_breaks", lambda b: b.replace('c.get("kind") == "shove"', 'c.get("kind") == "xx"'), lambda: breaks_fixture()["corner_shove"] == 2),
    ("e_run_breaks", lambda b: b.replace("answered += 1 if c.get", "answered += 0 if c.get"), lambda: breaks_fixture()["answered_shove"] == 2),
]


@pytest.mark.parametrize("n", range(len(MUTANTS)), ids=lambda n: "%s-%d" % (MUTANTS[n][0], n))
def test_a_mutant_of_each_reading_fails_its_fixture(n, monkeypatch):
    fn_name, edit, holds = MUTANTS[n]
    assert holds(), "the fixture must hold on the real function"
    monkeypatch.setattr(E, fn_name, _mutated(fn_name, edit)[fn_name])
    assert not holds(), "the mutant of %s survives its fixture" % fn_name


# ================================================================ e_grade_12.py
def test_e_grade_12_is_e_grade_11s_command_line_over_grade_e12(tmp_path):
    (tmp_path / "a.json").write_text(json.dumps(art(startPyMs=T0 * 1000.0, t_loop0_ms=T0 * 1000.0)), encoding="utf-8")
    script = os.path.join(TESTING, "agent", "drivers", "e_grade_12.py")
    r = subprocess.run([sys.executable, script, str(tmp_path / "a.json")], capture_output=True, text=True, cwd=TESTING)
    assert r.returncode == 0 and r.stdout.startswith("kills ") and "\nkills sources: " in r.stdout
    assert json.loads(r.stdout[r.stdout.index("\n{\n"):])["grade"] == "grade_e12"
    c = subprocess.run([sys.executable, script, "--chain", str(tmp_path / "a.json"), str(tmp_path / "a.json")],
                       capture_output=True, text=True, cwd=TESTING)
    assert c.returncode == 0 and "\ngate_e12 " in c.stdout
    for args in ([], ["a", "b", "c"], [str(tmp_path / "nope.json")]):
        assert subprocess.run([sys.executable, script, *args], capture_output=True, cwd=TESTING).returncode == 2


def test_e_grade_12_is_e_grade_11_with_only_the_grade_names_changed():
    a = open(os.path.join(TESTING, "agent", "drivers", "e_grade_11.py"), encoding="utf-8").read()
    b = open(os.path.join(TESTING, "agent", "drivers", "e_grade_12.py"), encoding="utf-8").read()
    body = b[b.index("\nimport json"):]
    assert body.replace("e_grade_12", "e_grade_11").replace("grade_e12", "grade_e11").replace("gate_e12", "gate_e11").replace(
        "report_lines_e12", "report_lines_e11") == a[a.index("\nimport json"):]
