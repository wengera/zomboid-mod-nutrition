"""base/gates_e.py pass 8 (Plan 24 Task 37), offline: `grade_e8`, the three defects of E10's grade fixed (the carried
`nearest`, the finish counted at its landing, the pull's fights named by their unit) and the five readings of survival
iteration 12 (the hold's kinds, the edge hold, the stomp on the first fallen frame, the fills, `doorway_pick`), each on a
fixture where it reads zero and one where it counts, a mutant per reading, `grade_e7` reproduced on E10's committed report
byte for byte, and `e_grade_8.py`."""
import copy
import json
import os
import subprocess
import sys

import pytest

from agent.base import gates_e as E
from agent.base.planner.policies import EDGE_HOLD_TICKS, KEEP_R
from agent.base.planner.survive import FINISH_R
from .test_gates_e import art
from .test_gates_e7 import T0, _mutated, act, aline, fall_fixture, pull_fixture, result, wound_fixture, zf

HERE = os.path.dirname(os.path.abspath(__file__))
TESTING = os.path.dirname(os.path.dirname(HERE))
E10 = os.path.join(TESTING, "artifacts", "e_day_10-20261030-084253")


def grade(actions=(), results=(), log=None, frames=(), stop="day_cap", **loop):
    a = art(actions=list(actions), results=list(results), startPyMs=T0 * 1000.0, t_loop0_ms=T0 * 1000.0, **loop)
    a["stop"]["reason"] = stop
    return E.grade_e8(a, decision_lines=log, lines=list(frames))


def acted(aid, type_, sent_s, state="done", reason="", **args):
    a = act(aid, type_, sent_s, **args)
    a.update(state=state, reason=reason)
    return a


# ================================================================ (a) the carried nearest
def test_a_strain_flee_is_near_by_the_lines_inputs_nearest_never_by_a_why_nearest_carried_from_a_steer():
    acts, res, log, frames = wound_fixture(37.6)
    log.append(aline(8, 8.0, {"flee": "strain", "nearest": 1.0}, nearest=8.0))      # the why carries 1.0, the planner read 8.0
    g = grade(acts, res, log, frames)["wounded"]
    assert g["strain_flees_near"] == 0 and g["strain_flees"] == 1 and g["strain_flees_carried"] == 1
    log.append(aline(9, 9.0, {"flee": "strain", "nearest": 9.0}, nearest=KEEP_R))   # the planner read it within KEEP_R
    g = grade(acts, res, log, frames)["wounded"]
    assert g["strain_flees_near"] == 1 and g["strain_flees"] == 2 and g["strain_flees_carried"] == 1
    # a why nearest alone (inputs.nearest absent) is no reading
    acts, res, log, frames = wound_fixture(37.6, flee_near=1.0)
    assert grade(acts, res, log, frames)["wounded"]["strain_flees_near"] == 0
    assert grade()["wounded"] == {"read": False}


def test_the_wounded_reading_keeps_the_rest_of_grade_e7s():
    acts, res, log, frames = wound_fixture(37.6, swing=True)
    g7 = E.grade_e7(art(actions=acts, results=res, startPyMs=T0 * 1000.0, t_loop0_ms=T0 * 1000.0),
                    decision_lines=log, lines=frames)["wounded"]
    g8 = grade(acts, res, log, frames)["wounded"]
    assert {k: v for k, v in g8.items() if k not in ("strain_flees", "strain_flees_carried", "strain_flees_near")} == {
        k: v for k, v in g7.items() if k != "strain_flees_near"}


# ================================================================ (b) the landed finish
def stomp_variant(state="done", reason="", **res):
    acts, _, log, frames = fall_fixture()
    acts[1] = acted("a2", "stomp", 1.0, state=state, reason=reason, targetId=1)
    return acts, ([result("a2", **res)] if res else []), log, frames


def test_a_landed_stomp_finishes_by_hit_or_target_dead_and_a_stood_or_rejected_one_does_not():
    g = grade(*stomp_variant(hit=True))["fallen"]
    assert (g["fallen"], g["finished"], g["sent"], g["left"], g["stood"], g["rejected"]) == (1, 1, 1, 0, 0, 0)
    g = grade(*stomp_variant(targetDead=True))["fallen"]
    assert g["finished"] == 1 and g["rows"][0]["finished"] is True
    g = grade(*stomp_variant(state="failed", reason="stood"))["fallen"]                 # E10's a62
    assert (g["finished"], g["sent"], g["left"], g["stood"], g["rejected"], g["finish_lines"]) == (0, 1, 1, 1, 0, 1)
    g = grade(*stomp_variant(state="rejected", reason="not valid"))["fallen"]           # E10's a59
    assert (g["finished"], g["sent"], g["stood"], g["rejected"]) == (0, 1, 0, 1)
    assert grade(*stomp_variant(hit=False))["fallen"]["finished"] == 0                  # done but no hit: not landed
    assert grade(*stomp_variant())["fallen"]["finished"] == 0                           # done with no result row
    assert grade()["fallen"] == {"read": False}


def test_a_stood_stomp_followed_by_a_landed_one_before_the_flee_resumed_finishes_the_target():
    acts, res, log, frames = stomp_variant(state="failed", reason="stood")
    log.insert(2, copy.deepcopy(log[1]))
    log[2]["wall"] = T0 + 1.5
    acts.append(acted("a3", "stomp", 1.5, targetId=1))
    res = [result("a3", hit=True)]
    g = grade(acts, res, log, frames)["fallen"]
    assert (g["finished"], g["sent"], g["stood"]) == (1, 1, 1)


# ================================================================ (c) the pull's units
def test_the_pull_names_its_units_fight_runs_against_the_loops_threat_episodes():
    g = grade(*pull_fixture(), fights=[{"flee": {}}] * 5)["pull"]
    assert g["fight_runs"] == g["fights"] == 1 and g["loop_fights"] == 5
    assert grade(*pull_fixture())["pull"]["loop_fights"] == 0
    assert grade()["pull"] == {"read": False}


# ================================================================ (d) the hold's kinds
def kinds_fixture(arms=True, pain=True):
    sp = {"spent": ["arms"]} if arms else {}
    pn = {"pain": {"kind": "wounded", "armPain": 37.6, "strain": {"l": 0, "r": 0}}} if pain else {}
    log = [aline(0, 0.0, dict(sp, fight=True, target=1), {"type": "shove", "args": {"targetId": 1}}),
           aline(1, 1.0, dict(sp, **dict(pn, fight=True, target=1)), {"type": "shove", "args": {"targetId": 1}}),
           aline(2, 2.0, {"fight": False}, None, sent=False),
           aline(3, 3.0, dict(pn, flee="many") if pain else {"flee": "many"}, None, sent=False),
           aline(4, 4.0, {"flee": "strain", "strain": {"kind": "arms", "armPain": 5.0}} if arms else {"flee": "x"}, None,
                 sent=False),
           aline(5, 5.0, dict(sp, fight=True, target=2), {"type": "attack", "args": {"targetId": 2}})]
    acts = [acted("s0", "shove", 0.0, targetId=1), acted("s1", "shove", 1.0, targetId=1),
            acted("w5", "attack", 5.0, targetId=2)]
    return acts, [result("s1", targetDead=True)], log, []


def test_the_hold_kinds_count_lines_fights_kills_swings_and_shoves_under_arms_and_wounded():
    g = grade(*kinds_fixture())["hold_kinds"]
    assert g["read"] is True
    assert g["arms"] == {"lines": 4, "fight_lines": 3, "fights": 2, "kills": 1, "swings": 1, "shoves": 2}
    assert g["wounded"] == {"lines": 2, "fight_lines": 1, "fights": 1, "kills": 1, "swings": 0, "shoves": 1}
    assert grade()["hold_kinds"] == {"read": False}


def test_the_hold_kinds_read_zero_without_either_why():
    g = grade(*kinds_fixture(arms=False, pain=False))["hold_kinds"]
    zero = {"lines": 0, "fight_lines": 0, "fights": 0, "kills": 0, "swings": 0, "shoves": 0}
    assert g["arms"] == zero and g["wounded"] == zero
    g = grade(*kinds_fixture(arms=True, pain=False))["hold_kinds"]
    assert g["wounded"]["lines"] == 0 and g["arms"]["lines"] == 4
    g = grade(*kinds_fixture(arms=False, pain=True))["hold_kinds"]
    assert g["arms"]["lines"] == 0 and g["wounded"]["lines"] == 2


def test_a_swing_under_the_wounded_pain_is_counted_so_that_the_must_read_zero_can_fail():
    acts, res, log, frames = kinds_fixture()
    log[5]["inputs"]["branches"]["threat"]["pain"] = {"kind": "wounded"}
    assert grade(acts, res, log, frames)["hold_kinds"]["wounded"]["swings"] == 1


# ================================================================ (e) the edge hold
def edge_fixture(legs=("seek", "pull", "seek"), gap=1.0, targets=(1, 1, 1), edge=None, end="done"):
    log, acts = [], []
    for i, (leg, t) in enumerate(zip(legs, targets)):
        why = {"fight": True, "leg": leg, "target": t}
        if edge and leg == "pull":
            why["edge"] = list(edge)
        log.append(aline(i, i * gap, why, {"type": "aim", "args": {"targetId": t}}))
        acts.append(acted("a%d" % i, "aim", i * gap, state="failed" if i < len(legs) - 1 else end,
                          reason="superseded" if i < len(legs) - 1 else "", targetId=t))
    return acts, [], log, []


def test_the_edge_hold_counts_aims_superseded_by_the_opposite_leg_within_the_window():
    assert EDGE_HOLD_TICKS / 2.0 == E.EDGE_WINDOW_S == 3.0
    g = grade(*edge_fixture())["edge"]
    assert (g["read"], g["aims"], g["superseded"], g["flipped"], g["retargeted"]) == (True, 3, 2, 2, 0)
    assert grade()["edge"] == {"read": False}


def test_the_edge_hold_reads_zero_for_the_same_leg_a_late_next_aim_and_an_aim_that_ran_to_its_end():
    assert grade(*edge_fixture(legs=("seek", "seek", "seek")))["edge"]["flipped"] == 0
    g = grade(*edge_fixture(gap=E.EDGE_WINDOW_S + 0.5))["edge"]
    assert g["superseded"] == 2 and g["flipped"] == 0
    acts, res, log, frames = edge_fixture()
    for a in acts:
        a.update(state="done", reason="")
    g = grade(acts, res, log, frames)["edge"]
    assert g["superseded"] == 0 and g["flipped"] == 0 and g["aims"] == 3


def test_the_edge_hold_counts_a_target_change_and_the_targets_kept_through_an_unlisting():
    g = grade(*edge_fixture(legs=("seek", "seek", "seek"), targets=(1, 2, 2)))["edge"]
    assert g["retargeted"] == 1 and g["flipped"] == 0
    g = grade(*edge_fixture(edge=[7, 8]))["edge"]
    assert g["pull_edge_lines"] == 1 and g["pull_edge_ids"] == 2
    assert grade(*edge_fixture())["edge"]["pull_edge_lines"] == 0
    assert grade(*_seek_edge())["edge"]["pull_edge_lines"] == 0


# ================================================================ (f) the stomp on the first fallen frame
def stomp_first_fixture(on_floor=True, state="done", reason="", block=False, **res):
    z = [{"id": 1, "dist": 1.2, "onFloor": True if on_floor else None}]
    frames = [zf(i * 0.5, z) for i in range(8)]
    log = [aline(0, 1.0, {"finish": 1, "kind": "stomp", "dist": 1.2}, {"type": "stomp", "args": {"targetId": 1}})]
    if block:
        log.append(aline(1, 2.0, {"flee": "many", "finish_block": {"target": 1, "chaser": 2, "dist": 3.0}}, None,
                         sent=False))
    return [acted("a1", "stomp", 1.0, state=state, reason=reason, targetId=1)], ([result("a1", **res)] if res else []), \
        log, frames


def test_a_stomp_is_counted_on_the_floor_frame_landed_and_refused_for_a_chaser():
    g = grade(*stomp_first_fixture(hit=True, block=True))["stomp_first"]
    assert (g["read"], g["sent"], g["on_floor"], g["early"], g["rejected_not_valid"], g["stood"], g["landed"],
            g["finish_block"]) == (True, 1, 1, 0, 0, 0, 1, 1)
    assert grade()["stomp_first"] == {"read": False}


def _stale_block():
    acts, res, log, frames = stomp_first_fixture(hit=True, block=True)
    stale = aline(2, 3.0, {"finish_block": {"target": 1, "chaser": 2, "dist": 3.0}}, None, sent=False)
    stale2 = aline(3, 4.0, {"flee": None, "finish_block": {"target": 1, "chaser": 2, "dist": 3.0}}, None, sent=False)
    return grade(acts, res, log + [stale, stale2], frames)["stomp_first"]["finish_block"]


def test_finish_block_counts_only_the_refusals_own_line_never_a_stale_value_on_a_later_one():
    assert _stale_block() == 1


def test_a_stomp_before_the_fallen_frame_a_not_valid_rejection_and_a_stood_one_are_counted_apart():
    g = grade(*stomp_first_fixture(on_floor=False, state="rejected", reason="not valid"))["stomp_first"]
    assert (g["sent"], g["on_floor"], g["early"], g["rejected_not_valid"], g["landed"]) == (1, 0, 1, 1, 0)
    g = grade(*stomp_first_fixture(state="failed", reason="stood"))["stomp_first"]
    assert (g["stood"], g["landed"], g["rejected_not_valid"], g["finish_block"]) == (1, 0, 0, 0)


def test_a_stomp_with_no_frame_at_the_line_is_early():
    acts, res, log, _ = stomp_first_fixture(hit=True)
    late = [zf(5.0 + i * 0.5, [{"id": 1, "dist": 1.2, "onFloor": True}]) for i in range(2)]
    assert grade(acts, res, log, late)["stomp_first"]["on_floor"] == 0


# ================================================================ (g) the fills
def need_line(n, off, fill, action=None, sent=True, branch="need"):
    ln = aline(n, off, {}, action, sent=sent, branch=branch)
    ln["inputs"]["branches"] = {"need": {"fill": fill}}
    return ln


def fills_fixture(walk=True):
    acts = [acted("f0", "fill", 0.0, itemId=5, x=1, y=2),
            acted("f1", "fill", 1.0, state="rejected", reason="no source", itemId=5, x=1, y=2),
            acted("f2", "fill", 2.0, state="failed", reason="superseded", itemId=5, x=1, y=2)]
    log = [need_line(0, 0.0, {"vessel": 5, "source": [1, 2], "dist": 3.0}, {"type": "fill", "args": {"itemId": 5}}),
           # no loaded source: the need branch sends nothing and a lower branch (`goal`) answers, yet the need why is logged
           need_line(3, 3.0, {"vessel": 5, "source": None, "want": "water_source", "unloaded": 2}, None, sent=False,
                     branch="goal")]
    if walk:
        log.append(need_line(4, 4.0, {"vessel": 5, "source": [9, 9], "dist": 30.0, "unloaded": 1, "walk": [9, 8]},
                             {"type": "walkTo", "args": {"x": 9.5, "y": 8.5}}))
        acts.append(acted("w4", "walkTo", 4.0, x=9.5, y=8.5))
    return acts, [], log, []


def test_the_fills_count_sent_done_no_source_superseded_and_the_walks():
    g = grade(*fills_fixture())["fills"]
    assert (g["read"], g["sent"], g["done"], g["no_source"], g["superseded"], g["walks_sent"], g["walks_done"],
            g["unloaded_lines"]) == (True, 3, 1, 1, 1, 1, 1, 2)
    assert grade(*fills_fixture(walk=False))["fills"]["unloaded_lines"] == 1          # the goal-branch line alone
    assert grade()["fills"] == {"read": False}


def _goal_walk():
    walk = need_line(4, 4.0, {"vessel": 5, "source": [9, 9], "dist": 30.0, "unloaded": 1, "walk": [9, 8]},
                     {"type": "walkTo", "args": {"x": 9.5, "y": 8.5}}, branch="goal")
    return grade([acted("w4", "walkTo", 4.0, x=9.5, y=8.5)], [], [walk], [])["fills"]


def test_the_fills_read_zero_without_fills_walks_or_a_need_why():
    acts, res, log, frames = fills_fixture(walk=False)
    g = grade([], res, [], frames)["fills"]
    assert (g["sent"], g["done"], g["no_source"], g["walks_sent"], g["unloaded_lines"]) == (0, 0, 0, 0, 0)
    log2 = [ln for ln in log if "walk" not in ln["inputs"]["branches"]["need"]["fill"]]
    assert grade(acts, res, log2, frames)["fills"]["walks_sent"] == 0
    assert grade(acts, res, log2, frames)["fills"]["unloaded_lines"] == 1
    other = copy.deepcopy(log[0])
    other["branch"] = "goal"
    assert grade([], res, [other], frames)["fills"]["walks_sent"] == 0
    g = _goal_walk()
    assert (g["walks_sent"], g["unloaded_lines"]) == (0, 1)       # a walk of another branch is no fill walk


def test_a_fill_walk_that_did_not_end_done_is_sent_but_not_done():
    acts, res, log, frames = fills_fixture()
    acts[-1].update(state="failed", reason="stuck")
    g = grade(acts, res, log, frames)["fills"]
    assert g["walks_sent"] == 1 and g["walks_done"] == 0


# ================================================================ (h) doorway_pick
def pick_fixture():
    log = [aline(i, float(i), {"flee": "many", "doorway_pick": v} if v else {"flee": "many"}, None, sent=False)
           for i, v in enumerate(("ok", "ok", "taken", None))]
    log.append(aline(9, 9.0, {"flee": "pair", "doorway_pick": "ok"}, None, sent=False))
    log.append(aline(10, 10.0, {"flee": "many", "doorway_pick": "locked"}, None, sent=False, branch="goal"))
    return [], [], log, []


def test_the_doorway_pick_distribution_is_read_on_the_many_lines_only():
    g = grade(*pick_fixture())["doorway_pick"]
    assert g == {"read": True, "many_lines": 4, "values": {"ok": 2, "taken": 1}, "absent": 1}
    g = grade([], [], [aline(0, 0.0, {"fight": True}, None, sent=False)], [])["doorway_pick"]
    assert g == {"read": True, "many_lines": 0, "values": {}, "absent": 0}
    assert grade()["doorway_pick"] == {"read": False}


# ================================================================ the whole grade
NEW = ("hold_kinds", "edge", "stomp_first", "fills", "doorway_pick")
OVERRIDDEN = ("pull", "wounded", "fallen")


def test_grade_e8_is_grade_e7_with_three_readings_re_read_five_added_and_a_report_naming_gate_e8():
    a, r, log, frames = pull_fixture()
    o = art(actions=a, results=r, startPyMs=T0 * 1000.0, t_loop0_ms=T0 * 1000.0)
    e7 = E.grade_e7(o, decision_lines=log, lines=frames)
    e8 = E.grade_e8(o, decision_lines=log, lines=frames)
    skip = ("grade", "report_lines") + OVERRIDDEN + NEW
    assert {k: v for k, v in e7.items() if k not in skip} == {k: v for k, v in e8.items() if k not in skip}
    assert e8["grade"] == "grade_e8" and E.gate_e8([o, o]) == E.gate_e7([o, o])
    text = "\n".join(e8["report_lines"])
    for key in ("pull (P24-AN)", "wounded (P24-AP)", "fallen (P24-AQ)", "hold kinds (P24-AT)", "edge hold (P24-AU)",
                "stomp (P24-AV)", "fills (P24-AW)", "doorway_pick (P24-AX)", "fight runs", "threat episodes", "[reading",
                "[inference", "(must read 0)"):
        assert key in text, key
    assert "E10" not in text and "[inference: a fight run lies inside one episode]" in text
    assert "gate_e7" not in text and e8["report_lines"][0] == e7["report_lines"][0]
    bare = E.grade_e8({})
    assert bare["grade"] == "grade_e8" and all(bare[k]["read"] is False for k in NEW + OVERRIDDEN)
    assert "no decision log read" in "\n".join(bare["report_lines"])
    assert E.grade_e8(None)["fills"] == {"read": False}


# ================================================================ mutants
def _seek_edge():
    acts, res, log, frames = edge_fixture(legs=("seek", "seek", "seek"))
    log[0]["inputs"]["branches"]["threat"]["edge"] = [1]          # an edge on a seek leg is no pull's
    return acts, res, log, frames


def _near_fixture():
    acts, res, log, frames = wound_fixture(37.6)
    log.append(aline(8, 8.0, {"flee": "strain"}, nearest=KEEP_R))
    return acts, res, log, frames


MUTANTS = (
    ("e_wounded_8", lambda s: s.replace('d = _n(_d(ln.get("inputs")).get("nearest"))',
                                        'd = _n(why.get("nearest"))'),
     lambda: grade(*wound_fixture(37.6, flee_near=1.0))["wounded"]["strain_flees_near"] == 0),
    ("e_wounded_8", lambda s: s.replace("d <= KEEP_R", "d <= 0.0"),
     lambda: grade(*_near_fixture())["wounded"]["strain_flees_near"] == 1),
    ("_landed", lambda s: s.replace('row.get("state") != "done"', 'False'),
     lambda: grade(*stomp_variant(state="failed", reason="stood", hit=True))["fallen"]["finished"] == 0),
    ("_landed", lambda s: s.replace('res.get("hit") is True or ', ''),
     lambda: grade(*stomp_variant(hit=True))["fallen"]["finished"] == 1),
    ("e_fallen_8", lambda s: s.replace("if _landed(L, ln):", "if True:"),
     lambda: grade(*stomp_variant(state="failed", reason="stood"))["fallen"]["finished"] == 0),
    ("e_fallen_8", lambda s: s.replace('a.get("reason") == "stood"', 'a.get("reason") == "x"'),
     lambda: grade(*stomp_variant(state="failed", reason="stood"))["fallen"]["stood"] == 1),
    ("e_pull_8", lambda s: s.replace('len(_l(_d(loop).get("fights")))', '0'),
     lambda: grade(*pull_fixture(), fights=[{}] * 4)["pull"]["loop_fights"] == 4),
    ("_kinds8", lambda s: s.replace('st.get("kind") == "arms"', 'st.get("kind") == "x"'),
     lambda: grade(*kinds_fixture())["hold_kinds"]["arms"]["lines"] == 4),
    ("_kinds8", lambda s: s.replace('pn.get("kind") == "wounded"', 'pn.get("kind") == "x"'),
     lambda: grade(*kinds_fixture())["hold_kinds"]["wounded"]["lines"] == 2),
    ("e_hold_kinds", lambda s: s.replace('_sent(ln, "attack")', '_sent(ln, "shove")'),
     lambda: grade(*kinds_fixture())["hold_kinds"]["arms"]["swings"] == 1),
    ("e_hold_kinds", lambda s: s.replace("L.kill_ids([ln for r in held for ln in r])", "[]"),
     lambda: grade(*kinds_fixture())["hold_kinds"]["arms"]["kills"] == 1),
    ("e_edge", lambda s: s.replace("b - a > EDGE_WINDOW_S", "False"),
     lambda: grade(*edge_fixture(gap=E.EDGE_WINDOW_S + 0.5))["edge"]["flipped"] == 0),
    ("e_edge", lambda s: s.replace('{la, lb} == {"seek", "pull"}', 'la != lb'),
     lambda: grade(*edge_fixture(legs=("seek", "stand", "seek")))["edge"]["flipped"] == 0),
    ("e_edge", lambda s: s.replace('row.get("reason") != "superseded"', 'False'),
     lambda: grade(*edge_fixture(end="failed"))["edge"]["superseded"] == 2),
    ("e_edge", lambda s: s.replace("retarget += 1 if ta != tb else 0", "retarget += 0"),
     lambda: grade(*edge_fixture(legs=("seek", "seek", "seek"), targets=(1, 2, 2)))["edge"]["retargeted"] == 1),
    ("e_edge", lambda s: s.replace('L.why(ln).get("leg") == "pull"\n             and', 'True\n             and'),
     lambda: grade(*_seek_edge())["edge"]["pull_edge_lines"] == 0),
    ("e_stomp_first", lambda s: s.replace('z.get("onFloor") is True', 'True'),
     lambda: grade(*stomp_first_fixture(on_floor=False))["stomp_first"]["early"] == 1),
    ("e_stomp_first", lambda s: s.replace('a.get("reason") == "not valid"', 'a.get("reason") == "x"'),
     lambda: grade(*stomp_first_fixture(state="rejected", reason="not valid"))["stomp_first"]["rejected_not_valid"] == 1),
    ("e_stomp_first", lambda s: s.replace('L.why(ln).get("finish_block")', 'None'),
     lambda: grade(*stomp_first_fixture(hit=True, block=True))["stomp_first"]["finish_block"] == 1),
    ("e_fills", lambda s: s.replace('a.get("reason") == "no source"', 'a.get("reason") == "x"'),
     lambda: grade(*fills_fixture())["fills"]["no_source"] == 1),
    ("e_fills", lambda s: s.replace('fw.get("walk") is not None', 'False'),
     lambda: grade(*fills_fixture())["fills"]["walks_sent"] == 1),
    ("e_fills", lambda s: s.replace('unl += 1 if fw.get("unloaded") is not None else 0', 'unl += 0'),
     lambda: grade(*fills_fixture())["fills"]["unloaded_lines"] == 2),
    ("e_fills", lambda s: s.replace('ln.get("branch") == "need" and ', ''),
     lambda: _goal_walk()["walks_sent"] == 0),
    ("e_fills", lambda s: s.replace('unl += 1 if fw.get("unloaded") is not None else 0',
                                    'unl += 1 if fw.get("unloaded") is not None and ln.get("branch") == "need" else 0'),
     lambda: grade(*fills_fixture())["fills"]["unloaded_lines"] == 2),
    ("e_stomp_first", lambda s: s.replace('isinstance(L.why(ln).get("flee"), str)', 'True'),
     lambda: _stale_block() == 1),
    ("e_fills", lambda s: s.replace('row.get("state") == "done" else 0', 'False else 0'),
     lambda: grade(*fills_fixture())["fills"]["walks_done"] == 1),
    ("e_doorway_pick", lambda s: s.replace('why.get("flee") != "many"', 'False'),
     lambda: grade(*pick_fixture())["doorway_pick"]["many_lines"] == 4),
    ("e_doorway_pick", lambda s: s.replace("absent += 1", "absent += 0"),
     lambda: grade(*pick_fixture())["doorway_pick"]["absent"] == 1),
)


@pytest.mark.parametrize("fn_name,edit,holds", MUTANTS, ids=lambda v: v if isinstance(v, str) else None)
def test_a_mutant_of_each_reading_fails_its_fixture(fn_name, edit, holds, monkeypatch):
    assert holds(), "the fixture must hold on the real function"
    mutant = _mutated(fn_name, edit)
    monkeypatch.setattr(E, fn_name, mutant[fn_name])
    assert not holds(), "the mutant of %s survives its fixture" % fn_name


# ================================================================ grade_e7 is unchanged on E10, and grade_e8 reads it
def _need_e10():
    if not os.path.isfile(os.path.join(E10, "e_day_10.json")):
        pytest.skip("e_day_10-20261030-084253 is not checked out")


def test_grade_e7_reproduces_the_committed_report_of_e10_byte_for_byte():
    _need_e10()
    script = os.path.join(TESTING, "agent", "drivers", "e_grade_7.py")
    r = subprocess.run([sys.executable, script, os.path.join(E10, "e_day_10.json")], capture_output=True)
    assert r.returncode == 0
    with open(os.path.join(E10, "e_grade.txt"), "rb") as fh:
        assert r.stdout == fh.read()


def test_grade_e8_on_e10_fixes_the_three_defects_and_reads_the_new_fields():
    _need_e10()
    with open(os.path.join(E10, "e_day_10.json"), encoding="utf-8") as fh:
        o = json.load(fh)
    log = [json.loads(l) for l in open(os.path.join(E10, "decision.log"), encoding="utf-8") if l.strip()]
    e7 = E.grade_e7(o, decision_lines=log, state_dir=E10)
    e8 = E.grade_e8(o, decision_lines=log, state_dir=E10)
    skip = ("grade", "report_lines") + OVERRIDDEN + NEW
    assert {k: v for k, v in e7.items() if k not in skip} == {k: v for k, v in e8.items() if k not in skip}
    assert e7["wounded"]["strain_flees_near"] == 13 and e8["wounded"]["strain_flees_near"] == 0
    assert e8["wounded"]["strain_flees_carried"] == 13 and e8["wounded"]["strain_flees"] == 308
    assert e7["fallen"]["finished"] == 1 and e8["fallen"]["finished"] == 0 and e8["fallen"]["sent"] == 1
    assert (e8["fallen"]["stood"], e8["fallen"]["rejected"]) == (1, 1)
    assert (e8["pull"]["fight_runs"], e8["pull"]["loop_fights"]) == (9, 39)
    assert (e8["fills"]["sent"], e8["fills"]["done"], e8["fills"]["no_source"], e8["fills"]["superseded"]) == (63, 0, 55, 8)
    assert (e8["edge"]["aims"], e8["edge"]["superseded"], e8["edge"]["flipped"]) == (25, 19, 7)
    assert (e8["stomp_first"]["sent"], e8["stomp_first"]["rejected_not_valid"], e8["stomp_first"]["stood"]) == (2, 1, 1)
    assert e8["doorway_pick"] == {"read": True, "many_lines": 162, "values": {}, "absent": 162}   # a PZA/1.7 build: none
    assert e8["hold_kinds"]["wounded"]["lines"] == 0 and e8["hold_kinds"]["arms"]["lines"] == 311
    assert e8["kills"] == e7["kills"] and e8["report_lines"][0] == e7["report_lines"][0]


# ================================================================ e_grade_8.py
def test_e_grade_8_is_e_grade_7s_command_line_over_grade_e8(tmp_path):
    (tmp_path / "a.json").write_text(json.dumps(art(startPyMs=T0 * 1000.0, t_loop0_ms=T0 * 1000.0)), encoding="utf-8")
    (tmp_path / "decision.log").write_text(json.dumps(aline(0, 0.0, {"fight": True, "leg": "pull"})) + "\n",
                                           encoding="utf-8")
    script = os.path.join(TESTING, "agent", "drivers", "e_grade_8.py")
    r = subprocess.run([sys.executable, script, str(tmp_path / "a.json")], capture_output=True, text=True, cwd=TESTING)
    assert r.returncode == 0 and r.stdout.startswith("kills ") and "hold kinds (P24-AT)" in r.stdout
    assert json.loads(r.stdout[r.stdout.index("\n{\n"):])["grade"] == "grade_e8"
    c = subprocess.run([sys.executable, script, "--chain", str(tmp_path / "a.json"), str(tmp_path / "a.json")],
                       capture_output=True, text=True, cwd=TESTING)
    assert c.returncode == 0 and "\ngate_e8 " in c.stdout and "\ngate_e7 " not in c.stdout
    for args in ([], ["a", "b", "c"], [str(tmp_path / "nope.json")]):
        assert subprocess.run([sys.executable, script] + args, capture_output=True, text=True,
                              cwd=TESTING).returncode == 2
