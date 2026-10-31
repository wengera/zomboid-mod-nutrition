"""base/gates_e.py pass 11 (Plan 25 Task 9), offline: `grade_e11` and its eight readings of survival iteration 14 (the shun
loop P25-G, the unwear as a wound step P25-H, the corner's kinds and the break P25-I/P25-L, the far finishes P25-J, the
stand's wound end P25-K, the hold's release P25-M, the legs of the Shelter goals and the night P25-N, the item record read
live P25-O), each on a fixture decision log where it reads zero and one where it counts, a mutant per reading, `grade_e10`
unchanged on E12 under `grade_e11`, and `e_grade_11.py`."""
import json
import os
import subprocess
import sys

import pytest

from agent.base import gates_e as E
from .test_gates_e import art
from .test_gates_e7 import T0, _mutated, act, aline, result, zf

HERE = os.path.dirname(os.path.abspath(__file__))
TESTING = os.path.dirname(os.path.dirname(HERE))
E12 = os.path.join(TESTING, "artifacts", "e_day_12-20261030-175041")
NEW = ("shun", "unwear", "corner_kinds", "far_finish", "stand_wound", "release", "door_legs", "item_record")


def grade(actions=(), results=(), log=None, frames=(), goals=(), stop="day_cap"):
    a = art(actions=list(actions), results=list(results), startPyMs=T0 * 1000.0, t_loop0_ms=T0 * 1000.0)
    a["stop"]["reason"] = stop
    if goals:
        a["loop"]["goals"] = list(goals)
    return E.grade_e11(a, decision_lines=log, lines=list(frames))


def _act(type_, **args):
    return {"type": type_, "args": args}


def bline(n, t, branch, why, action=None, sent=True, cooled=None, others=None):
    """A decision-log line of `branch` whose own why is `why` (and any other branch's in `others`)."""
    br = dict(others or {})
    br[branch] = why
    return {"action": action, "branch": branch, "gameMin": 600 + n, "inputs": {"nearest": None, "mode": None,
                                                                              "branches": br, "cooled": cooled},
            "sent": sent, "wall": T0 + t}


# ================================================================ the committed artifact
def _load(name):
    p = os.path.join(E12, name)
    if not os.path.isfile(p):
        pytest.skip("%s is not checked out" % E12)
    return p


def test_grade_e11_on_e12_changes_only_the_grade_name_the_eight_readings_and_the_report():
    with open(_load("e_day_12.json"), encoding="utf-8") as fh:
        o = json.load(fh)
    log = [json.loads(l) for l in open(_load("decision.log"), encoding="utf-8") if l.strip()]
    e10 = E.grade_e10(o, decision_lines=log, state_dir=E12)
    e11 = E.grade_e11(o, decision_lines=log, state_dir=E12)
    skip = ("grade", "report_lines") + NEW
    assert e11["grade"] == "grade_e11" and all(e11[k]["read"] is True for k in NEW)
    assert {k: v for k, v in e10.items() if k not in skip} == {k: v for k, v in e11.items() if k not in skip}
    keep = lambda r: [l for l in r if not l.startswith("gate_e")]
    assert keep(e11["report_lines"])[:len(keep(e10["report_lines"]))] == keep(e10["report_lines"])
    assert len(e11["report_lines"]) == len(e10["report_lines"]) + 8
    # E12 ran iteration 13: none of the iteration 14 fields existed
    assert e11["shun"]["cooled_goals"] == e11["shun"]["invalid_shunned"] == 0
    assert e11["unwear"]["wound_lines"] == 0 and e11["corner_kinds"]["shove"] == 0
    assert e11["corner_kinds"]["miss_breaks"] == 0
    assert e11["far_finish"]["far_lines"] == e11["far_finish"]["pair_yield"] == e11["far_finish"]["stand_far_lines"] == 0
    assert e11["stand_wound"]["lines"] == e11["release"]["lines"] == 0
    assert e11["door_legs"]["shelter_legs"] == e11["door_legs"]["night_legs"] == 0
    # the fix 1 blocks: E12 is the a86 and a69 shape itself (a pair flee line in a knock-down's window, no yield: 2 and 2)
    assert (e11["far_finish"]["pair_knock"], e11["far_finish"]["pair_knock_no_yield"]) == (2, 2)
    assert e11["door_legs"]["shelter_ended_leg"] == e11["door_legs"]["night_ended_leg"] == 0
    assert "cooled_lines" not in e11["shun"]


def test_grade_e10_on_e12_still_reproduces_the_committed_report_byte_for_byte():
    with open(_load("e_day_12.json"), encoding="utf-8") as fh:
        o = json.load(fh)
    log = [json.loads(l) for l in open(_load("decision.log"), encoding="utf-8") if l.strip()]
    r = E.grade_e10(o, decision_lines=log, state_dir=E12)["report_lines"]
    want = open(_load("e_grade.txt"), encoding="utf-8").read().split("\n{\n")[0].split("\n")
    assert r == want[:len(r)]


# ================================================================ P25-G, the shun loop
def shun_fixture(cool=True):
    goals = [{"type": "Shelter", "state": "failed", "reason": "shunned"}, {"type": "Shelter", "state": "failed",
                                                                         "reason": "shun"},
             {"type": "Shelter", "state": "failed", "reason": "no plan"}, {"type": "LootBuilding", "state": "failed",
                                                                           "reason": "no door"},
             {"type": "Shelter", "state": "done", "reason": "inside"},
             {"type": "Rest", "state": "failed", "reason": "goal budget"}]
    log = [bline(0, 0.0, "goal", {"goal": "Shelter", "proposed": None, "refused": {"type": "Shelter"}}, None, sent=False),
           bline(1, 1.0, "care", {"reason": "x"}, None, sent=False, cooled={"type": "walkTo", "args": {}} if cool else None),
           bline(2, 2.0, "goal", {"goal": "Rest"}, None, sent=False)]
    return grade(log=log, goals=goals)["shun"]


def test_the_shun_counts_the_goal_ends_by_reason_the_cooled_goals_and_the_refusals():
    g = shun_fixture()
    assert g["read"] is True and g["ends"] == {"shun": 1, "shunned": 1, "no plan": 1, "no door": 1}
    assert (g["cooled_goals"], g["shelter_shunned"], g["refused_lines"], g["invalid_shunned"]) == (4, 1, 1, 0)
    # inputs.cooled is the old per-action cooldown (an action type), not P25-G's goal cooling: never read
    assert "cooled_lines" not in g and "cooled_lines" not in shun_fixture(cool=False)
    assert not any("passed a cooled goal over" in l for l in grade(log=[])["report_lines"])
    inv = grade(log=[], goals=[{"type": "Shelter", "state": "failed", "reason": "invalid: shunned"}])["shun"]
    assert inv["invalid_shunned"] == 1


def test_the_shun_reads_zero_without_a_shun_end_and_unread_without_a_log():
    g = grade(log=[bline(0, 0.0, "goal", {"goal": "Rest"}, None, sent=False)],
              goals=[{"type": "Rest", "state": "done", "reason": "rested"}])["shun"]
    assert g["cooled_goals"] == g["shelter_shunned"] == g["refused_lines"] == 0
    assert grade(log=None)["shun"] == {"read": False}


# ================================================================ P25-H, the unwear as a wound step
def cline(n, t, care, action, sent=True, stock=False):
    return bline(n, t, "care", {"stock": care} if stock else care, action, sent)


def unwear_fixture(rip=True, bandage=True, part=3, stock=False):
    log = [cline(0, 0.0, {"reason": "unwear", "part": 3, "item": 11, "cover": 1.0}, _act("unwear", itemId=11)),
           cline(1, 1.0, {"reason": "unwear", "item": 12, "cover": 1.0}, _act("unwear", itemId=12), stock=True)]
    if rip:
        log.append(cline(2, 2.0, {"reason": "no_rag", "part": part, "item": 11}, _act("rip", itemId=11)))
    if bandage:
        log.append(cline(3, 3.0, {"reason": "bleeding", "part": part, "item": 99, "kind": "rag"},
                         _act("bandage", itemId=99, part=part)))
    return grade(log=log)["unwear"]


def test_the_unwear_counts_the_wound_steps_the_stock_and_the_rip_and_bandage_that_followed_per_part():
    g = unwear_fixture()
    assert g["read"] is True and (g["wound_lines"], g["wound_sent"], g["stock_lines"]) == (1, 1, 1)
    assert (g["ripped"], g["bandaged"]) == (1, 1)
    assert unwear_fixture(rip=False)["ripped"] == 0 and unwear_fixture(rip=False)["bandaged"] == 0
    assert unwear_fixture(bandage=False)["bandaged"] == 0
    other = unwear_fixture(part=4)
    assert (other["ripped"], other["bandaged"]) == (0, 0)             # the rip and the bandage of another part do not count


def stock_leak_fixture():
    """The idle stock's line: the unanswered care branch's own why (here wound-shaped) beside the stock's, the stock's send."""
    leak = {"reason": "unwear", "part": 3, "item": 13, "stock": {"reason": "unwear", "item": 13, "cover": 1.0}}
    return grade(log=[cline(0, 0.0, leak, _act("unwear", itemId=13)),
                      cline(1, 1.0, {"reason": "no_rag", "part": 3, "item": 13}, _act("rip", itemId=13))])["unwear"]


def test_the_unwear_stock_line_counts_as_stock_and_never_as_a_wound_step():
    g = stock_leak_fixture()
    assert (g["wound_lines"], g["wound_sent"], g["stock_lines"], g["ripped"]) == (0, 0, 1, 0)


def test_the_unwear_follow_window_is_a_count_of_log_lines():
    log = [cline(0, 0.0, {"reason": "unwear", "part": 3, "item": 11}, _act("unwear", itemId=11))]
    log += [bline(i, float(i), "need", {}, None, sent=False) for i in range(1, E.UNWEAR_SEQ_LINES + 1)]
    log.append(cline(99, 99.0, {"reason": "no_rag", "part": 3, "item": 11}, _act("rip", itemId=11)))
    assert grade(log=log)["unwear"]["ripped"] == 0


def test_the_unwear_reads_zero_without_the_reason():
    g = grade(log=[cline(0, 0.0, {"reason": "bleeding", "part": 3, "item": 9}, _act("bandage", itemId=9))])["unwear"]
    assert (g["wound_lines"], g["wound_sent"], g["stock_lines"], g["ripped"], g["bandaged"]) == (0, 0, 0, 0, 0)


# ================================================================ P25-I and P25-L, the corner's kinds
def kinds_fixture(near=False):
    f = lambda n, t, c, **kw: aline(n, t, dict({"fight": True, "target": 5, "corner": c}, **kw),
                                    _act("steer") if c["kind"] == "break" else None, sent=c["kind"] == "break")
    log = [f(0, 0.0, {"kind": "shove", "shoved": 5, "n": 1, "sore": True}),
           f(1, 1.0, {"kind": "shove", "shoved": 5, "n": 1, "sore": False}),
           f(2, 2.0, {"kind": "swing", "shoved": 5, "n": 1}),
           f(3, 3.0, {"kind": "break", "shoved": 5, "n": 2}),                        # P25-A's two-zombie break
           f(4, 4.0, {"kind": "break", "shoved": 5, "n": 1, "misses": 3}),           # P25-L's break
           aline(5, 5.0, {"fight": True, "target": 5, "dist": 1.5 if near else 3.5}, None, sent=False),
           f(6, 6.0, {"kind": "break", "shoved": 5, "n": 1, "misses": 4}),
           aline(7, 7.0, {"fight": True, "target": 6, "dist": 1.0}, None, sent=False),   # another target: no outcome
           f(8, 8.0, {"kind": "break", "shoved": 5, "n": 1, "misses": 3})]            # the log ends
    return grade(log=log)["corner_kinds"]


def test_the_corner_kinds_count_the_kinds_the_sore_shoves_the_misses_and_the_break_s_outcome():
    g = kinds_fixture()
    assert g["read"] is True and (g["shove"], g["swing"], g["break"], g["miss_breaks"]) == (2, 1, 4, 3)
    assert (g["sore"], g["max_n"], g["misses"]) == (1, 2, [3, 4, 3])
    assert g["outcomes"] == {"far": 1, "near": 0, "none": 2}
    assert kinds_fixture(near=True)["outcomes"] == {"far": 0, "near": 1, "none": 2}


def test_the_corner_kinds_read_zero_without_a_corner_why():
    g = grade(log=[aline(0, 0.0, {"fight": True, "target": 1}, None, sent=False)])["corner_kinds"]
    assert (g["shove"], g["swing"], g["break"], g["miss_breaks"], g["sore"], g["misses"]) == (0, 0, 0, 0, 0, [])


# ================================================================ P25-J, the far finishes
def far_fixture(land=True):
    def f(n, t, d, kind="stomp", **kw):
        return aline(n, t, dict({"fight": True, "target": 7, "dist": d, "downed": 7}, **kw),
                     _act(kind, targetId=7), sent=True)
    log = [f(0, 5.0, 3.5, stomp=True),                                   # a far finish, landed or not
           f(1, 6.0, 1.5, stomp=True),                                   # within reach: not far
           f(2, 7.0, 5.0, "attack", floor=True),                         # at FINISH_R: far, the floor strike
           f(3, 8.0, 5.5, stomp=True),                                   # beyond FINISH_R: not read
           f(4, 9.0, 3.0, stomp=True, doorway=[1, 2]),                   # the stand's far stomp
           f(5, 10.0, 1.0, stomp=True, doorway=[1, 2]),
           aline(6, 11.0, {"fight": True, "pair_yield": 7}, _act("stomp", targetId=7), sent=True),
           aline(7, 12.0, {"fight": True, "pair_yield": 7}, _act("steer"), sent=True),
           aline(8, 13.0, {"fight": True, "pair_yield": 8}, None, sent=False)]
    acts = [act("a1", "stomp", 5.0, targetId=7)]
    res = [result("a1", targetDead=land, hit=land)]
    return grade(acts, res, log)["far_finish"]


def test_the_far_finishes_count_the_stomps_the_stand_s_and_what_followed_a_pair_yield():
    g = far_fixture()
    assert g["read"] is True and (g["far_lines"], g["far_stomps"], g["far_floor"], g["max_dist"]) == (3, 2, 1, 5.0)
    assert g["far_attacks"] == 1
    assert g["far_landed"] == 1 and far_fixture(land=False)["far_landed"] == 0
    assert (g["stand_far_lines"], g["stand_far_stomps"]) == (1, 1)
    assert g["pair_yield"] == 3 and g["yield_next"] == {"stomp": 1, "other": 1, "open": 1}


def knock_fixture(yield_at=None, outside=False, no_zombie=False, knock=True):
    """A sent shove at zombie 7 (result knockdown), then pair flee lines inside the window whose frames list it standing, then
    the line whose frame reads it fallen (`outside`: it stays standing and one more pair line falls past KNOCK_READ_S)."""
    stand = [{"id": 7, "dist": 2.0, "onFloor": None}]
    fallen = stand if outside else [{"id": 7, "dist": 2.0, "onFloor": True}]
    frames = [zf(0.0, stand), zf(0.5, [] if no_zombie else stand), zf(1.0, stand), zf(1.5, fallen), zf(2.5, stand)]
    yl = lambda k: {"pair_yield": 7} if yield_at == k else {}
    log = [aline(0, 0.0, {"fight": True, "target": 7}, _act("shove", targetId=7)),
           aline(1, 0.5, dict({"flee": "pair"}, **yl(1)), _act("steer")),
           aline(2, 1.0, dict({"flee": "pair"}, **yl(2)), _act("steer")),
           aline(3, 1.5, dict({"fight": True, "target": 7, "downed": 7, "dist": 2.0}, **yl(3)), _act("stomp", targetId=7))]
    if outside:
        log.append(aline(4, 2.5, {"flee": "pair"}, _act("steer")))
    acts = [act("s1", "shove", 0.0, targetId=7)]
    return grade(acts, [result("s1", knockdown=knock)], log, frames)["far_finish"]


def test_the_pair_flee_lines_in_a_knock_window_without_a_yield_are_counted():
    g = knock_fixture()
    assert (g["pair_knock"], g["pair_knock_no_yield"]) == (2, 2)
    assert knock_fixture(outside=True)["pair_knock"] == 2                    # a line past KNOCK_READ_S is not in the window
    assert knock_fixture(no_zombie=True)["pair_knock"] == 1                  # a frame not listing the zombie is not counted
    assert knock_fixture(knock=False)["pair_knock"] == 0                     # a shove that knocked nothing down opens no window
    d = knock_fixture(yield_at=3)
    assert (d["pair_knock"], d["pair_knock_no_yield"]) == (2, 0)             # a yield on the line reading it fallen closes both
    y = knock_fixture(yield_at=1)
    assert (y["pair_knock"], y["pair_knock_no_yield"]) == (2, 1)             # a yield only closes the lines up to it


def test_the_far_finishes_read_zero_without_a_downed_why():
    g = grade(log=[aline(0, 0.0, {"fight": True, "target": 1, "dist": 3.0}, _act("attack", targetId=1))])["far_finish"]
    assert (g["far_lines"], g["far_stomps"], g["pair_yield"], g["stand_far_lines"], g["max_dist"]) == (0, 0, 0, 0, None)
    assert (g["pair_knock"], g["pair_knock_no_yield"]) == (0, 0)


# ================================================================ P25-K, the stand's wound end
def wound_fixture(next_flee=True):
    log = [aline(0, 0.0, {"flee": "many", "doorway_left": "wound", "doorway_wound": [2, 5]}, _act("steer")),
           aline(1, 1.0, {"flee": "doorway"} if next_flee else {"fight": True, "target": 1}, _act("steer")),
           aline(2, 2.0, {"flee": "many", "doorway_left": "health"}, _act("steer")),
           aline(3, 3.0, {"flee": "many", "doorway_left": "wound", "doorway_wound": [1]}, _act("steer"))]
    return grade(log=log)["stand_wound"]


def test_the_stand_s_wound_end_counts_the_lines_the_parts_and_the_line_after():
    g = wound_fixture()
    assert g["read"] is True and (g["lines"], g["parts"], g["left_health"]) == (2, 3, 1)
    assert g["next"] == {"flee": 1, "other": 0, "open": 1}
    assert wound_fixture(next_flee=False)["next"] == {"flee": 0, "other": 1, "open": 1}


def test_the_stand_s_wound_end_reads_zero_without_the_why():
    g = grade(log=[aline(0, 0.0, {"flee": "many", "doorway_left": "quiet"}, _act("steer"))])["stand_wound"]
    assert (g["lines"], g["parts"], g["left_health"]) == (0, 0, 0)


# ================================================================ P25-M, the release
def release_fixture():
    log = [aline(0, 0.0, {"flee": "strain", "release": {"kind": "endurance", "why": "line", "endurance": 0.9,
                                                       "held_min": 12.5}}, _act("steer")),
           aline(1, 1.0, {"fight": True, "release": {"kind": "endurance", "why": "timed", "endurance": 0.6,
                                                    "held_min": 31.0}}, None, sent=False),
           aline(2, 2.0, {"fight": True, "release": {"kind": "arms", "why": "pain", "armPain": 20, "held_min": None}},
                 None, sent=False),
           # Survive.assess puts release on the threat why whichever branch answered: a timed release on a goal-branch line
           bline(3, 3.0, "goal", {"goal": "Rest"}, None, sent=False,
                 others={"threat": {"release": {"kind": "endurance", "why": "timed", "endurance": 0.5, "held_min": 40.0}}})]
    return grade(log=log)["release"]


def test_the_release_counts_the_kinds_whys_and_the_held_span():
    g = release_fixture()
    assert g["read"] is True and g["lines"] == 4
    assert g["by"] == {"endurance:line": 1, "endurance:timed": 2, "arms:pain": 1}
    assert (g["timed"], g["min_held"], g["max_held"]) == (2, 12.5, 40.0)


def test_the_release_reads_zero_without_the_field_and_keeps_the_inferred_block_beside_it():
    g = grade(log=[aline(0, 0.0, {"flee": "strain", "strain": {"kind": "endurance", "endurance": 0.7}}, _act("steer"))])
    assert (g["release"]["lines"], g["release"]["timed"], g["release"]["max_held"]) == (0, 0, None)
    assert g["hold_walk"]["read"] is True and "released_under" in g["hold_walk"]


# ================================================================ P25-N, the legs
def legs_fixture(halve=True):
    sh = lambda n, t, ln_, **kw: bline(n, t, "goal", dict({"goal": "Shelter", "leg": [1, 2], "legLen": ln_}, **kw),
                                       _act("walkTo", x=1, y=2), sent=True)
    night = lambda n, t, **kw: bline(n, t, "night", dict({"leg": [3, 4], "legLen": 40.0}, **kw), _act("walkTo", x=3, y=4))
    log = [sh(0, 0.0, 40.0), sh(1, 5.0, 20.0 if halve else 40.0), sh(2, 9.0, 20.0 if halve else 40.0, ended="leg"),
           bline(3, 10.0, "goal", {"goal": "Shelter", "args": {}}, _act("walkTo", x=9, y=9)),     # no leg
           bline(4, 11.0, "goal", {"goal": "LootBuilding", "leg": [5, 6], "legLen": 40.0}, _act("walkTo", x=5, y=6)),
           night(5, 12.0), night(6, 13.0, ended="leg")]
    acts = [dict(act("a1", "walkTo", 0.0, x=1, y=2)),
            dict(act("a2", "walkTo", 5.0, x=1, y=2), state="failed", reason="no square"),
            dict(act("a3", "walkTo", 9.0, x=1, y=2), state="failed", reason="stuck"),
            dict(act("a4", "walkTo", 12.0, x=3, y=4)),
            dict(act("a5", "walkTo", 13.0, x=3, y=4), state="failed", reason="no square")]
    goals = [{"type": "Shelter", "state": "failed", "reason": "no square"}, {"type": "Shelter", "state": "done",
                                                                           "reason": "inside"},
             {"type": "Shelter", "state": "failed", "reason": "no square"}, {"type": "Rest", "state": "done",
                                                                           "reason": "rested"}]
    return grade(acts, log=log, goals=goals)["door_legs"]


def test_the_legs_count_the_shelter_and_night_legs_their_results_the_halvings_and_the_goals_ends():
    g = legs_fixture()
    assert g["read"] is True and (g["shelter_legs"], g["shelter_sent"], g["shelter_done"]) == (3, 3, 1)
    assert (g["shelter_no_square"], g["shelter_other_fail"], g["halved"]) == (1, 1, 1)
    assert (g["night_legs"], g["night_done"], g["night_no_square"], g["night_ended_leg"]) == (2, 1, 1, 1)
    assert g["shelter_ended_leg"] == 1                                  # the Shelter goal's own ended leg, beside the night's
    assert g["shelter_ends"] == {"done:inside": 1, "failed:no square": 2}
    assert legs_fixture(halve=False)["halved"] == 0


def test_the_legs_read_zero_without_a_leg_why():
    g = grade(log=[bline(0, 0.0, "goal", {"goal": "Shelter"}, _act("walkTo", x=1, y=1))])["door_legs"]
    assert (g["shelter_legs"], g["night_legs"], g["halved"], g["shelter_ends"]) == (0, 0, 0, {})
    assert (g["shelter_ended_leg"], g["night_ended_leg"]) == (0, 0)


# ================================================================ P25-O, the item record read live
def hello(mod):
    return {"kind": "hello", "mod": mod, "seq": 1}


def item_fixture(mod="1.7", unwear_first=True):
    acts = [act("u1", "unwear", 1.0, itemId=11), act("r1", "rip", 3.0, itemId=11) if unwear_first
            else act("r1", "rip", 0.5, itemId=11), act("r2", "rip", 4.0, itemId=12)]
    return grade(acts, log=[], frames=[hello(mod)])["item_record"]


def test_the_item_record_reads_the_hello_s_mod_and_the_rips_that_named_an_unwear_first():
    g = item_fixture()
    assert g["read"] is True and g["mod"] == "1.7" and g["item_fields"] is True
    assert (g["unwear_sent"], g["rips"], g["rip_after_unwear"]) == (1, 2, 1)
    assert item_fixture(unwear_first=False)["rip_after_unwear"] == 0
    old = item_fixture(mod="1.5.1")
    assert old["mod"] == "1.5.1" and old["item_fields"] is False
    assert item_fixture(mod="1.7.1")["item_fields"] is True


def test_the_item_record_reads_none_without_a_hello():
    g = grade(log=[])["item_record"]
    assert g["mod"] is None and g["item_fields"] is False and (g["rips"], g["unwear_sent"], g["rip_after_unwear"]) == (0, 0, 0)


# ================================================================ the report
def test_the_report_names_the_eight_rules_and_marks_reading_or_inference():
    g = grade(log=[aline(0, 0.0, {"fight": True, "target": 1}, None, sent=False)])
    r = g["report_lines"]
    assert g["grade"] == "grade_e11" and set(g) >= set(NEW)
    tags = ("shun (P25-G) [reading]", "unwear (P25-H) [reading]", "corner kinds (P25-I, P25-L) [reading]",
            "far finish (P25-J) [reading]", "stand wound (P25-K) [reading]", "release (P25-M) [reading]",
            "door legs (P25-N) [reading]", "item record (P25-O) [reading]")
    for t in tags:
        assert any(l.startswith(t) for l in r), t
    assert sum("[inference" in l for l in r) >= 5
    assert not any(l.startswith("gate_e9 ") or l.startswith("gate_e10 ") for l in r)
    nolog = grade(log=None)["report_lines"]
    assert any(l == "shun (P25-G): no decision log read" for l in nolog)
    assert E.gate_e11([art()]) == E.gate_e10([art()])


# ================================================================ a mutant per reading
MUTANTS = [
    ("e_shun", lambda b: b.replace('g.get("reason") in ends', 'g.get("reason") in ()'),
     lambda: shun_fixture()["ends"]["shun"] == 1),
    ("e_shun", lambda b: b.replace('"invalid: shunned"', '"invalid: xx"'),
     lambda: grade(log=[], goals=[{"type": "Shelter", "state": "failed", "reason": "invalid: shunned"}])["shun"]["invalid_shunned"] == 1),
    ("e_unwear", lambda b: b.replace('"no_rag"', '"xx"'), lambda: unwear_fixture()["ripped"] == 1),
    ("e_unwear", lambda b: b.replace("s[2] == part", "True"), lambda: unwear_fixture(part=4)["ripped"] == 0),
    ("e_corner_kinds", lambda b: b.replace('c.get("misses") is None', "False"),
     lambda: kinds_fixture()["miss_breaks"] == 3),
    ("e_corner_kinds", lambda b: b.replace("d > FIGHT_REACH", "d < FIGHT_REACH"), lambda: kinds_fixture()["outcomes"]["far"] == 1),
    ("e_far_finish", lambda b: b.replace("d <= FINISH_R", "d <= 99"), lambda: far_fixture()["far_lines"] == 3),
    ("e_far_finish", lambda b: b.replace("FIGHT_REACH < d", "0.0 < d"), lambda: far_fixture()["far_lines"] == 3),
    ("e_far_finish", lambda b: b.replace('"doorway" in why', "False"), lambda: far_fixture()["stand_far_lines"] == 1),
    ("e_stand_wound", lambda b: b.replace('== "wound"', '== "health"'), lambda: wound_fixture()["lines"] == 2),
    ("e_stand_wound", lambda b: b.replace("len(parts)", "1"), lambda: wound_fixture()["parts"] == 3),
    ("e_release", lambda b: b.replace('r.get("why") == "timed"', 'r.get("why") == "xx"'), lambda: release_fixture()["timed"] == 2),
    ("e_door_legs", lambda b: b.replace("< prev", "> prev"), lambda: legs_fixture()["halved"] == 1),
    ("e_door_legs", lambda b: b.replace('"no square"', '"xx"'), lambda: legs_fixture()["shelter_no_square"] == 1),
    ("e_shun", lambda b: b.replace('"refused") is not None', '"refusedx") is not None'),
     lambda: shun_fixture()["refused_lines"] == 1),
    ("e_unwear", lambda b: b.replace('if "stock" in c:', "if False:"), lambda: stock_leak_fixture()["wound_lines"] == 0),
    ("e_far_finish", lambda b: b.replace("wj > w + KNOCK_READ_S", "wj > w + 99"), lambda: knock_fixture(outside=True)["pair_knock"] == 2),
    ("e_far_finish", lambda b: b.replace('L.res.get(row.get("aid"), {}).get("knockdown") is not True', "False"),
     lambda: knock_fixture(knock=False)["pair_knock"] == 0),
    ("e_far_finish", lambda b: b.replace("y >= p", "y > 99"), lambda: knock_fixture(yield_at=3)["pair_knock_no_yield"] == 0),
    ("e_far_finish", lambda b: b.replace("and z is not None:", ":"), lambda: knock_fixture(no_zombie=True)["pair_knock"] == 1),
    ("e_release", lambda b: b.replace("for ln in L.rows)", 'for ln in L.rows if ln.get("branch") == "threat")'),
     lambda: release_fixture()["timed"] == 2),
    ("e_door_legs", lambda b: b.replace("ended[b] += 1", 'ended["night"] += 1'), lambda: legs_fixture()["shelter_ended_leg"] == 1),
    ("e_item_record", lambda b: b.replace("< sent", "> sent"), lambda: item_fixture()["rip_after_unwear"] == 1),
    ("e_item_record", lambda b: b.replace('l.get("kind") == "hello"', "False"), lambda: item_fixture()["mod"] == "1.7"),
]


@pytest.mark.parametrize("n", range(len(MUTANTS)), ids=lambda n: "%s-%d" % (MUTANTS[n][0], n))
def test_a_mutant_of_each_reading_fails_its_fixture(n, monkeypatch):
    fn_name, edit, holds = MUTANTS[n]
    assert holds(), "the fixture must hold on the real function"
    monkeypatch.setattr(E, fn_name, _mutated(fn_name, edit)[fn_name])
    assert not holds(), "the mutant of %s survives its fixture" % fn_name


# ================================================================ e_grade_11.py
def test_e_grade_11_is_e_grade_10s_command_line_over_grade_e11(tmp_path):
    (tmp_path / "a.json").write_text(json.dumps(art(startPyMs=T0 * 1000.0, t_loop0_ms=T0 * 1000.0)), encoding="utf-8")
    script = os.path.join(TESTING, "agent", "drivers", "e_grade_11.py")
    r = subprocess.run([sys.executable, script, str(tmp_path / "a.json")], capture_output=True, text=True, cwd=TESTING)
    assert r.returncode == 0 and r.stdout.startswith("kills ") and "\nkills sources: " in r.stdout
    assert json.loads(r.stdout[r.stdout.index("\n{\n"):])["grade"] == "grade_e11"
    c = subprocess.run([sys.executable, script, "--chain", str(tmp_path / "a.json"), str(tmp_path / "a.json")],
                       capture_output=True, text=True, cwd=TESTING)
    assert c.returncode == 0 and "\ngate_e11 " in c.stdout
    for args in ([], ["a", "b", "c"], [str(tmp_path / "nope.json")]):
        assert subprocess.run([sys.executable, script, *args], capture_output=True, cwd=TESTING).returncode == 2


def test_e_grade_11_is_e_grade_10_with_only_the_grade_names_changed():
    a = open(os.path.join(TESTING, "agent", "drivers", "e_grade_10.py"), encoding="utf-8").read()
    b = open(os.path.join(TESTING, "agent", "drivers", "e_grade_11.py"), encoding="utf-8").read()
    body = b[b.index("\nimport json"):]
    assert body.replace("e_grade_11", "e_grade_10").replace("grade_e11", "grade_e10").replace("gate_e11", "gate_e10").replace(
        "report_lines_e11", "report_lines_e10") == a[a.index("\nimport json"):]
