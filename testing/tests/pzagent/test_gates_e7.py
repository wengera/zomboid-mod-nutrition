"""base/gates_e.py pass 7 (Plan 24 Task 33), offline: `grade_e7` and its seven readings of survival iteration 11 (the pull,
the doorway stand, the wounded fight, the fallen target, the care tick, the transparent solid, the shot taker's index),
each on a fixture decision log and frame set where it reads zero and one where it counts, a mutant per reading, and
`grade_e6` reproduced on the committed E8 and E9 artifacts."""
import copy
import json
import os
import subprocess
import sys

import pytest

from agent.base import gates_e as E
from agent.base.planner.policies import DANGER_R, FIGHT_REACH, KEEP_R, STRAIN_HARD
from .fakemod import DEFAULT_FRAME
from .test_gates_e import art

HERE = os.path.dirname(os.path.abspath(__file__))
TESTING = os.path.dirname(os.path.dirname(HERE))
T0 = 1000.0                                           # the loop start in epoch seconds (loop.startPyMs 1e6 ms)


def aline(n, wall_off, why=None, action=None, sent=True, branch="threat", care=None, nearest=None, mode=None):
    """A decision-log line `wall_off` seconds into the loop with a threat why (and a care why)."""
    br = {"threat": dict(why or {})}
    if care is not None:
        br["care"] = care
    return {"action": action, "branch": branch, "gameMin": 600 + n, "inputs": {"nearest": nearest, "mode": mode,
                                                                              "branches": br},
            "sent": sent, "wall": T0 + wall_off}


def act(aid, type_, sent_s, **args):
    return {"aid": aid, "type": type_, "args": args, "state": "done", "reason": "", "sentS": sent_s, "endedS": sent_s + 1}


def zf(wall_off, zombies=(), pain=0, attackers=0, x=10.0, y=10.0, parts=(), game_min=600):
    """A decoded frame line at `wall_off` seconds into the loop."""
    f = copy.deepcopy(DEFAULT_FRAME)
    f.update(kind="frame", seq=int(wall_off * 10), wallMs=int((T0 + wall_off) * 1000), gameMin=game_min,
             zombies=[dict({"id": 1, "dist": 3.0, "hasTarget": True, "onFloor": None}, **z) for z in zombies])
    f["me"].update(x=x, y=y, z=0, attackers=attackers)
    f["body"] = {"health": 100, "bleeding": 0, "scratched": 0, "bitten": 0, "parts": list(parts), "armPain": pain,
                 "strain": {"l": 0, "r": 0}}
    return f


def grade(actions=(), results=(), log=None, frames=(), maps=(), stop="day_cap", state_dir=None):
    a = art(actions=list(actions), results=list(results), startPyMs=T0 * 1000.0, t_loop0_ms=T0 * 1000.0)
    a["stop"]["reason"] = stop
    return E.grade_e7(a, decision_lines=log, lines=list(frames) + list(maps), state_dir=state_dir)


def result(aid, **r):
    return {"aid": aid, "type": "x", "state": "done", "result": r}


# ================================================================ the pull (P24-AN)
def pull_fixture(kill=True, swing=True, far=True):
    far_z = [{"id": 2, "dist": 8.5, "hasTarget": False}] if far else []
    frames = [zf(i * 0.5, [{"id": 1, "dist": 4.0}] + far_z) for i in range(8)]
    log = [aline(0, 0.0, {"fight": True, "leg": "pull", "pull": [1.0, 2.0], "stance": True},
                 {"type": "aim", "args": {"targetId": 1}}),
           aline(1, 1.0, {"fight": True, "leg": "pull", "pull": [1.0, 2.0]}, None, sent=False),
           aline(2, 2.0, {"fight": True, "target": 1, "dist": 1.5}, {"type": "attack", "args": {"targetId": 1}} if swing
                 else None, sent=swing)]
    acts = [act("a1", "aim", 0.0, targetId=1)] + ([act("a2", "attack", 2.0, targetId=1)] if swing else [])
    res = [result("a2", targetDead=True)] if swing and kill else []
    return acts, res, log, frames


def test_the_pull_counts_the_group_listed_the_pull_legs_the_swings_and_the_kills():
    g = grade(*pull_fixture())["pull"]
    assert g["read"] is True and g["fights"] == 1 and g["beyond_fights"] == 1 and g["beyond_lines"] == 3
    assert (g["pull_lines"], g["pull_sent"], g["pull_fights"], g["pull_fights_swung"], g["pull_kills"]) == (2, 1, 1, 1, 1)


def test_the_pull_reads_zero_without_a_pull_and_without_a_far_zombie():
    g = grade(*pull_fixture(far=False))["pull"]
    assert g["beyond_fights"] == 0 and g["beyond_lines"] == 0 and g["pull_fights"] == 1
    acts, res, log, frames = pull_fixture()
    for ln in log:
        ln["inputs"]["branches"]["threat"].pop("leg", None)
    g = grade(acts, res, log, frames)["pull"]
    assert (g["pull_lines"], g["pull_sent"], g["pull_fights"], g["pull_fights_swung"], g["pull_kills"]) == (0, 0, 0, 0, 0)
    assert grade(*pull_fixture(swing=False))["pull"]["pull_fights_swung"] == 0
    assert grade(*pull_fixture(kill=False))["pull"]["pull_kills"] == 0
    assert grade()["pull"] == {"read": False}                                  # no decision log


def test_the_pull_beyond_reading_is_the_frame_at_or_before_the_line():
    acts, res, log, frames = pull_fixture()
    late = [zf(i * 0.5 + 5.0, [{"id": 1, "dist": 4.0}, {"id": 2, "dist": 8.5, "hasTarget": False}]) for i in range(2)]
    g = grade(acts, res, log, late)["pull"]                                    # every frame after the lines: no frame at them
    assert g["beyond_fights"] == 0
    near = [zf(i * 0.5, [{"id": 1, "dist": 4.0}, {"id": 2, "dist": DANGER_R}]) for i in range(8)]
    assert grade(acts, res, log, near)["pull"]["beyond_fights"] == 0           # at DANGER_R is not beyond it


# ================================================================ the doorway stand (P24-AO)
def door_fixture(attackers=0, kill=True, swing=True, died=False):
    z = [{"id": 1, "dist": 1.0}]
    frames = [zf(i * 0.5, z, attackers=attackers) for i in range(6)]
    why = {"fight": True, "doorway": 3, "door": [5, 6]}
    log = [aline(0, 0.0, dict(why, target=1), {"type": "attack", "args": {"targetId": 1}} if swing else None, sent=swing),
           aline(1, 1.0, dict(why, target=1, shove="doorway"), {"type": "shove", "args": {"targetId": 1}}),
           aline(2, 2.0, dict(why, step="return"), None, sent=False)]
    acts = ([act("a1", "attack", 0.0, targetId=1)] if swing else []) + [act("a2", "shove", 1.0, targetId=1)]
    res = [result("a1", targetDead=True)] if swing and kill else []
    return acts, res, log, frames, "death" if died else "day_cap"


def test_the_doorway_stand_counts_its_fights_swings_shoves_and_kills_under_many():
    acts, res, log, frames, stop = door_fixture()
    g = grade(acts, res, log, frames, stop=stop)["doorway"]
    assert (g["read"], g["fights"], g["lines"], g["swings"], g["shoves"], g["kills"]) == (True, 1, 3, 1, 1, 1)
    assert g["attackers3_frames"] == 0 and g["drag_deaths"] == 0


def test_the_doorway_reads_zero_without_a_stand_and_a_drag_down_needs_three_attackers_and_the_death():
    acts, res, log, frames, stop = door_fixture(swing=False)
    g = grade(acts, res, log, frames, stop=stop)["doorway"]
    assert g["swings"] == 0 and g["kills"] == 0
    for ln in log:
        ln["inputs"]["branches"]["threat"].pop("doorway")
    g = grade(acts, res, log, frames)["doorway"]
    assert (g["fights"], g["lines"], g["swings"], g["shoves"], g["kills"]) == (0, 0, 0, 0, 0)
    acts, res, log, frames, stop = door_fixture(attackers=3, died=True)
    g = grade(acts, res, log, frames, stop=stop)["doorway"]
    assert g["attackers3_frames"] == 6 and g["drag_deaths"] == 1                # died inside the stand at three attackers
    after = frames + [zf(30.0, [{"id": 1, "dist": 1.0}], attackers=3)]
    g = grade(acts, res, log, after, stop=stop)["doorway"]
    assert g["attackers3_frames"] == 6 and g["drag_deaths"] == 0                # the last frame is outside every stand
    short = frames[:3]
    g = grade(acts, res, log, short)["doorway"]
    assert g["attackers3_frames"] == 3 and g["drag_deaths"] == 0                # alive: a count, no death
    two = [zf(i * 0.5, [{"id": 1, "dist": 1.0}], attackers=2) for i in range(3)]
    assert grade(acts, res, log, two, stop=stop)["doorway"]["attackers3_frames"] == 0
    assert grade()["doorway"] == {"read": False}


# ================================================================ the wounded fight (P24-AP)
def wound_fixture(pain, sends=("shove", "stomp"), swing=False, flee_near=None):
    frames = [zf(i, [{"id": 1, "dist": 1.0}], pain=pain) for i in range(8)]
    log, acts, res = [], [], []
    for i, kind in enumerate(sends):
        log.append(aline(i, float(i), {"fight": True, "wounded": pain, "target": 1},
                         {"type": kind, "args": {"targetId": 1}}))
        acts.append(act("s%d" % i, kind, float(i), targetId=1))
    res.append(result("s%d" % (len(sends) - 1), targetDead=True))
    if swing:
        log.append(aline(5, 5.0, {"fight": True, "target": 1}, {"type": "attack", "args": {"targetId": 1}}))
        acts.append(act("w", "attack", 5.0, targetId=1))
    log.append(aline(6, 6.0, {"fight": True, "hold": True, "wounded": pain}, None, sent=False))
    if flee_near is not None:
        log.append(aline(7, 7.0, {"flee": "strain", "nearest": flee_near, "strain": {"armPain": pain}}))
    return acts, res, log, frames


def test_the_wounded_fight_counts_shoves_stomps_and_kills_under_the_hold_and_swings_read_zero():
    g = grade(*wound_fixture(37.6))["wounded"]
    assert g["read"] is True and g["swings_at_pain"] == 0 and g["shoves_hold"] == 1 and g["stomps_hold"] == 1
    assert g["kills_hold"] == 1 and g["hold_lines"] == 1 and g["strain_flees_near"] == 0


def test_a_swing_under_the_hold_is_counted_and_below_the_hold_it_is_not():
    g = grade(*wound_fixture(STRAIN_HARD, swing=True))["wounded"]
    assert g["swings_at_pain"] == 1
    below = grade(*wound_fixture(STRAIN_HARD - 0.1, swing=True))["wounded"]
    assert below["swings_at_pain"] == 0 and below["shoves_hold"] == 0 and below["kills_hold"] == 0


def test_a_strain_flee_with_a_zombie_within_keep_r_is_counted_a_far_one_is_not():
    assert grade(*wound_fixture(37.6, flee_near=KEEP_R))["wounded"]["strain_flees_near"] == 1
    assert grade(*wound_fixture(37.6, flee_near=KEEP_R + 0.5))["wounded"]["strain_flees_near"] == 0
    acts, res, log, frames = wound_fixture(37.6, flee_near=None)
    log.append(aline(8, 8.0, {"flee": "strain"}, nearest=2.0))                 # the why carries none: the line's nearest
    assert grade(acts, res, log, frames)["wounded"]["strain_flees_near"] == 1
    assert grade()["wounded"] == {"read": False}


# ================================================================ the fallen target (P24-AQ)
def fall_fixture(finish=True, standing_near=False, far=3.0):
    z = [{"id": 1, "dist": 1.2, "onFloor": True}]
    if standing_near:
        z.append({"id": 2, "dist": 4.0, "onFloor": None})
    frames = [zf(i * 0.5, z) for i in range(8)]
    log = [aline(0, 0.0, {"fight": True, "target": 1}, {"type": "attack", "args": {"targetId": 1}}),
           aline(1, 2.0, {"flee": "many", "nearest": far}, {"type": "steer", "args": {"vx": 1.0, "vy": 0.0}})]
    if finish:
        log.insert(1, aline(2, 1.0, {"finish": 1, "kind": "stomp", "dist": 1.2}, {"type": "stomp", "args": {"targetId": 1}},
                            mode="flee"))
    acts = [act("a1", "attack", 0.0, targetId=1)] + ([act("a2", "stomp", 1.0, targetId=1)] if finish else [])
    res = [result("a2", targetDead=True)] if finish else []
    return acts, res, log, frames


def fall_fixture_late():
    """The flee line comes first, the stomp a half second after it: the finish is not before the flee resumed."""
    acts, res, log, frames = fall_fixture()
    flee = aline(2, 1.9, {"flee": "many", "nearest": 3.0}, {"type": "steer", "args": {"vx": 1.0, "vy": 0.0}})
    stomp = aline(1, 2.2, {"finish": 1, "kind": "stomp", "dist": 1.2}, {"type": "stomp", "args": {"targetId": 1}})
    return acts, res, [log[0], flee, stomp], frames


def test_a_fallen_target_finished_before_the_flee_resumed_is_counted_finished_with_its_kill():
    g = grade(*fall_fixture())["fallen"]
    assert (g["read"], g["fallen"], g["finished"], g["left"], g["finish_lines"], g["finish_kills"]) == (True, 1, 1, 0, 1, 1)
    assert g["rows"][0]["id"] == 1 and g["rows"][0]["finished"] is True


def test_a_fallen_target_left_to_a_flee_is_counted_left_and_a_near_standing_zombie_voids_the_reading():
    g = grade(*fall_fixture(finish=False))["fallen"]
    assert (g["fallen"], g["finished"], g["left"], g["finish_lines"]) == (1, 0, 1, 0)
    g = grade(*fall_fixture(finish=False, standing_near=True))["fallen"]
    assert g["fallen"] == 0                                                    # a standing zombie within DANGER_R: not read
    acts, res, log, frames = fall_fixture_late()
    g = grade(acts, res, log, frames)["fallen"]
    assert g["finished"] == 0 and g["left"] == 1 and g["finish_lines"] == 1      # the finish sent after the flee resumed
    acts, res, log, frames = fall_fixture()
    far_frames = [zf(i * 0.5, [{"id": 1, "dist": FIGHT_REACH + 0.5, "onFloor": True}]) for i in range(8)]
    assert grade(acts, res, log, far_frames)["fallen"]["fallen"] == 0          # beyond FIGHT_REACH
    nobody = [zf(i * 0.5, [{"id": 9, "dist": 1.2, "onFloor": True}]) for i in range(8)]
    assert grade(acts, res, log, nobody)["fallen"]["fallen"] == 0              # never a target of the planner
    assert grade()["fallen"] == {"read": False}


# ================================================================ the care tick (P24-AR)
def care_fixture(ride=True, flee="many"):
    why = {"flee": flee}
    if ride:
        why["ride"] = "a97"
    log = [aline(0, 0.0, dict(why), care={"held": {"bandage": 1, "dirty": 0, "rag": 2}}),
           aline(1, 1.0, dict(why), care={"held": {"bandage": 0, "dirty": 1, "rag": 1}})]
    parts = [{"i": 5, "bleeding": True}, {"i": 8, "bleeding": True}, {"i": 2, "bleeding": False}]
    frames = [zf(0.0, parts=[], game_min=600), zf(0.5, parts=parts[:1], game_min=600), zf(1.0, parts=parts, game_min=601),
              zf(1.5, parts=parts, game_min=601)]
    return [], [], log, frames


def test_the_care_tick_counts_the_bandages_ridden_on_a_many_flee_the_dressings_and_the_bleeding():
    g = grade(*care_fixture())["care_tick"]
    assert g["read"] is True and g["rides_many"] == 1 and g["ride_lines"] == 2
    assert g["dressings_last"] == {"gameMin": 601, "dressings": 1}
    assert g["bleeding"] == {"max": 2, "minutes": 2, "series": [[600, 0], [600, 1], [601, 2]]}


def test_the_care_tick_reads_zero_without_a_ride_or_on_another_flee():
    assert grade(*care_fixture(ride=False))["care_tick"]["rides_many"] == 0
    g = grade(*care_fixture(flee="held"))["care_tick"]
    assert g["rides_many"] == 0 and g["ride_lines"] == 0
    assert grade()["care_tick"] == {"read": False}
    quiet = grade([], [], [aline(0, 0.0, {"fight": True})], [zf(0.0)])["care_tick"]
    assert quiet["dressings_last"] is None and quiet["bleeding"] == {"max": 0, "minutes": 0, "series": [[600, 0]]}


# ================================================================ the transparent solid (P24-AS)
def solid_fixture(secs=16.5, move=0.0, heading=(0.0, 1.0), trans=True, steer=True, slide=0.0):
    frames = [zf(i * 0.5, x=10.5 + slide * i, y=10.5 + move * i) for i in range(int(secs * 2) + 1)]
    sq = {"x": 10, "y": 11, "z": 0, "solid": False, "solidTrans": trans}
    maps = [{"kind": "map", "mode": "delta", "squares": [sq]}]
    log = [aline(0, 0.0, {"flee": "many"}, {"type": "steer", "args": {"vx": heading[0], "vy": heading[1], "seconds": 3.0}})
           if steer else aline(0, 0.0, {"flee": "many"}, None, sent=False)]
    return [], [], log, frames, maps


def test_a_steer_held_against_a_solid_trans_square_for_five_seconds_is_counted():
    a, r, log, frames, maps = solid_fixture()
    g = grade(a, r, log, frames, maps)["transparent"]
    assert g["read"] is True and g["steers"] == 1 and g["held_runs"] == 1
    assert abs(g["rows"][0]["secs"] - 16.5) < 1e-6 and g["rows"][0]["square"] == [10, 11, 0] and g["rows"][0]["axis"] == "y"


def test_a_steer_held_on_one_axis_while_the_character_slides_along_the_row_is_counted():
    """E9: y fixed for 18.4 s, x moving, the steers' heading (0.19, 0.98) into a solidTrans row."""
    a, r, log, frames, maps = solid_fixture(slide=0.001, heading=(0.2, 0.98))
    g = grade(a, r, log, frames, maps)["transparent"]
    assert g["held_runs"] == 1 and g["rows"][0]["axis"] == "y"
    a, r, log, frames, maps = solid_fixture(slide=0.001, heading=(0.98, 0.2))      # mostly along x: x is the sliding axis
    assert grade(a, r, log, frames, maps)["transparent"]["held_runs"] == 0


def test_the_transparent_solid_reads_zero_when_moving_short_off_the_square_or_without_a_steer():
    a, r, log, frames, maps = solid_fixture(move=0.5)
    assert grade(a, r, log, frames, maps)["transparent"]["held_runs"] == 0       # the position moves 0.5 a frame
    a, r, log, frames, maps = solid_fixture(secs=4.5)
    assert grade(a, r, log, frames, maps)["transparent"]["held_runs"] == 0       # held under five seconds
    a, r, log, frames, maps = solid_fixture(heading=(1.0, 0.0))
    assert grade(a, r, log, frames, maps)["transparent"]["held_runs"] == 0       # the heading is not into the square
    a, r, log, frames, maps = solid_fixture(trans=False)
    assert grade(a, r, log, frames, maps)["transparent"]["held_runs"] == 0       # the square is not solidTrans
    a, r, log, frames, maps = solid_fixture(steer=False)
    g = grade(a, r, log, frames, maps)["transparent"]
    assert g["steers"] == 0 and g["held_runs"] == 0                              # no steer in force
    a, r, log, frames, maps = solid_fixture(move=0.01)
    assert grade(a, r, log, frames, maps)["transparent"]["held_runs"] == 0       # 0.01 a frame drifts past 0.02 in 3 frames
    assert grade()["transparent"] == {"read": False}


# ================================================================ the shots (P24-AM)
def test_the_shots_index_is_read_by_method_skip_reason_and_image(tmp_path):
    rows = [{"n": 1, "skipped": "not foreground"}, {"n": 2, "skipped": "occluded", "method": "screen"},
            {"n": 3, "file": "a.jpg", "method": "window", "skipped_screen": "not foreground"},
            {"n": 4, "skipped": "blank", "method": "window"}, {"n": 5, "file": "b.jpg"}, {"n": 6, "skipped": "no window"}]
    (tmp_path / "shots").mkdir()
    (tmp_path / "shots" / "shots.jsonl").write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
    g = grade(state_dir=str(tmp_path))["shots"]
    assert g == {"read": True, "lines": 6, "images": 2, "by_method": {"screen": 4, "window": 2},
                 "skipped": {"not foreground": 1, "occluded": 1, "blank": 1, "no window": 1},
                 "window_after_screen_refused": 1}
    assert grade()["shots"] == {"read": False} and grade(state_dir=str(tmp_path / "nope"))["shots"] == {"read": False}


# ================================================================ the whole grade
def test_grade_e7_is_grade_e6_plus_the_pass_7_fields_and_its_report_names_gate_e7():
    a, r, log, frames = pull_fixture()
    o = art(actions=a, results=r, startPyMs=T0 * 1000.0, t_loop0_ms=T0 * 1000.0)
    e6 = E.grade_e6(o, decision_lines=log, lines=frames)
    e7 = E.grade_e7(o, decision_lines=log, lines=frames)
    new = ("grade", "report_lines", "pull", "doorway", "wounded", "fallen", "care_tick", "transparent", "shots")
    assert {k: v for k, v in e6.items() if k not in ("grade", "report_lines")} == {k: v for k, v in e7.items() if k not in new}
    assert e7["grade"] == "grade_e7" and E.gate_e7([o, o]) == E.gate_e6([o, o])
    text = "\n".join(e7["report_lines"])
    for key in ("pull (P24-AN)", "doorway (P24-AO)", "wounded (P24-AP)", "fallen (P24-AQ)", "care tick (P24-AR)",
                "transparent solid (P24-AS)", "shots (P24-AM)", "[inference"):
        assert key in text, key
    assert e7["report_lines"][0] == e6["report_lines"][0]
    assert "gate_e6" not in text
    bare = E.grade_e7({})
    assert bare["grade"] == "grade_e7" and all(bare[k]["read"] is False for k in new[2:])
    assert E.grade_e7(None)["pull"] == {"read": False}


# ================================================================ mutants: each reading fails a changed copy of its function
def _pull_at_danger_r():
    acts, res, log, _ = pull_fixture()
    frames = [zf(i * 0.5, [{"id": 2, "dist": DANGER_R}]) for i in range(8)]
    return grade(acts, res, log, frames)["pull"]["beyond_fights"]


MUTANTS = (
    ("e_pull", lambda s: s.replace('L.why(ln).get("leg") == "pull" for ln in r', 'L.why(ln).get("leg") == "walk" for ln in r'),
     lambda: grade(*pull_fixture())["pull"]["pull_fights"] == 1),
    ("e_pull", lambda s: s.replace("z[\"dist\"] > DANGER_R", "z[\"dist\"] >= DANGER_R"),
     lambda: _pull_at_danger_r() == 0),
    ("e_doorway", lambda s: s.replace(">= 3:", ">= 2:"),
     lambda: grade(*door_fixture(attackers=2)[:4])["doorway"]["attackers3_frames"] == 0),
    ("e_doorway", lambda s: s.replace('_sent(ln, "attack")', '_sent(ln, "shove")'),
     lambda: grade(*door_fixture(swing=False)[:4])["doorway"]["swings"] == 0),
    ("e_wounded", lambda s: s.replace("pain < STRAIN_HARD", "pain < STRAIN_HARD + 100"),
     lambda: grade(*wound_fixture(37.6, swing=True))["wounded"]["swings_at_pain"] == 1),
    ("e_wounded", lambda s: s.replace("d <= KEEP_R", "d <= 0.0"),
     lambda: grade(*wound_fixture(37.6, flee_near=1.0))["wounded"]["strain_flees_near"] == 1),
    ("e_fallen", lambda s: s.replace('isinstance(L.why(ln).get("flee"), str)', 'False'),
     lambda: grade(*fall_fixture_late())["fallen"]["left"] == 1),
    ("e_fallen", lambda s: s.replace("z[\"dist\"] <= FIGHT_REACH and", "True and"),
     lambda: grade(*fall_fixture()[:3], [zf(0.0, [{"id": 1, "dist": 5.0, "onFloor": True}])])["fallen"]["fallen"] == 0),
    ("e_care_tick", lambda s: s.replace('why.get("flee") == "many" and why.get("ride")', 'why.get("ride")'),
     lambda: grade(*care_fixture(flee="held"))["care_tick"]["rides_many"] == 0),
    ("e_transparent", lambda s: s.replace("secs >= HELD_MIN_S", "secs >= 0.0"),
     lambda: grade(*solid_fixture(secs=4.5))["transparent"]["held_runs"] == 0),
    ("e_transparent", lambda s: s.replace("if sq in trans:", "if True:"),
     lambda: grade(*solid_fixture(trans=False))["transparent"]["held_runs"] == 0),
)


def _mutated(fn_name, edit):
    """gates_e's source with `edit` applied inside function `fn_name` only, executed as a module copy."""
    path = os.path.join(TESTING, "agent", "base", "gates_e.py")
    src = open(path, encoding="utf-8").read()
    start = src.index("\ndef %s(" % fn_name)
    end = src.index("\ndef ", start + 5)
    body = src[start:end]
    new = edit(body)
    assert new != body, (fn_name, "the mutant changed nothing")
    ns = {"__name__": "gates_e_mutant"}
    exec(compile(src[:start] + new + src[end:], "gates_e_mutant", "exec"), ns)    # noqa: S102 - a scratch copy
    return ns


@pytest.mark.parametrize("fn_name,edit,holds", MUTANTS,
                         ids=lambda v: v if isinstance(v, str) else None)
def test_a_mutant_of_each_reading_fails_its_fixture(fn_name, edit, holds, monkeypatch):
    assert holds(), "the fixture must hold on the real function"
    mutant = _mutated(fn_name, edit)
    monkeypatch.setattr(E, fn_name, mutant[fn_name])
    assert not holds(), "the mutant of %s survives its fixture" % fn_name


def test_the_shots_mutant_that_drops_the_method_default_fails(tmp_path, monkeypatch):
    (tmp_path / "shots").mkdir()
    (tmp_path / "shots" / "shots.jsonl").write_text(json.dumps({"n": 1, "skipped": "blank"}) + "\n", encoding="utf-8")

    def holds():
        return grade(state_dir=str(tmp_path))["shots"]["by_method"] == {"screen": 1, "window": 0}
    assert holds()
    mutant = _mutated("e_shots", lambda s: s.replace('if r.get("method") in ("screen", "window") else "screen"',
                                                      'if r.get("method") in ("screen", "window") else "window"'))
    monkeypatch.setattr(E, "e_shots", mutant["e_shots"])
    assert not holds()


# ================================================================ grade_e6 is unchanged on the committed artifacts
def test_grade_e6_reproduces_the_committed_report_of_e9_byte_for_byte():
    """E9's e_grade.txt is e_grade_6.py's stdout (E8's is e_grade_5.py's, so it is not a grade_e6 record)."""
    d = os.path.join(TESTING, "artifacts", "e_day_9-20261030-052429")
    if not os.path.isfile(os.path.join(d, "e_grade.txt")):
        pytest.skip("e_day_9-20261030-052429 is not checked out")
    script = os.path.join(TESTING, "agent", "drivers", "e_grade_6.py")
    r = subprocess.run([sys.executable, script, os.path.join(d, "e_day_9.json")], capture_output=True)
    assert r.returncode == 0
    with open(os.path.join(d, "e_grade.txt"), "rb") as fh:
        assert r.stdout == fh.read()


@pytest.mark.parametrize("run_id,key", (("e_day_8-20261029-174023", "e_day_8"), ("e_day_9-20261030-052429", "e_day_9")))
def test_grade_e7_on_the_e8_and_e9_artifacts_is_grade_e6_plus_the_new_fields(run_id, key):
    d = os.path.join(TESTING, "artifacts", run_id)
    if not os.path.isfile(os.path.join(d, key + ".json")):
        pytest.skip("%s is not checked out" % run_id)
    with open(os.path.join(d, key + ".json"), encoding="utf-8") as fh:
        o = json.load(fh)
    log = [json.loads(l) for l in open(os.path.join(d, "decision.log"), encoding="utf-8") if l.strip()]
    e6 = E.grade_e6(o, decision_lines=log, state_dir=d)
    e7 = E.grade_e7(o, decision_lines=log, state_dir=d)
    new = ("grade", "report_lines", "pull", "doorway", "wounded", "fallen", "care_tick", "transparent", "shots")
    assert {k: v for k, v in e6.items() if k not in ("grade", "report_lines")} == {k: v for k, v in e7.items() if k not in new}
    assert e7["report_lines"][:len(e6["report_lines"])] == [l.replace("gate_e6 ", "gate_e7 ") for l in e6["report_lines"]]
    assert all(e7[k]["read"] is True for k in new[2:])


# ================================================================ e_grade_7.py
def test_e_grade_7_is_e_grade_6s_command_line_over_grade_e7(tmp_path):
    (tmp_path / "a.json").write_text(json.dumps(art(startPyMs=T0 * 1000.0, t_loop0_ms=T0 * 1000.0)), encoding="utf-8")
    (tmp_path / "decision.log").write_text(json.dumps(aline(0, 0.0, {"fight": True, "leg": "pull"})) + "\n",
                                           encoding="utf-8")
    script = os.path.join(TESTING, "agent", "drivers", "e_grade_7.py")
    r = subprocess.run([sys.executable, script, str(tmp_path / "a.json")], capture_output=True, text=True, cwd=TESTING)
    assert r.returncode == 0 and r.stdout.startswith("kills ") and "pull (P24-AN)" in r.stdout
    assert json.loads(r.stdout[r.stdout.index("\n{\n"):])["grade"] == "grade_e7"
    c = subprocess.run([sys.executable, script, "--chain", str(tmp_path / "a.json"), str(tmp_path / "a.json")],
                       capture_output=True, text=True, cwd=TESTING)
    assert c.returncode == 0 and "\ngate_e7 " in c.stdout and "\ngate_e6 " not in c.stdout
    for args in ([], ["a", "b", "c"], [str(tmp_path / "nope.json")]):
        assert subprocess.run([sys.executable, script] + args, capture_output=True, text=True,
                              cwd=TESTING).returncode == 2
