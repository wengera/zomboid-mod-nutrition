"""base/gates_e.py pass 10 (Plan 25 Task 5), offline: `grade_e10` and its six readings of survival iteration 13 (the corner
under a hold P25-A, the stomp before a running attack P25-B, the endurance hold walk and its timed release P25-C, the ride
waits P25-D, the stalled walk of a doorway stand P25-E, the fence wait P25-F), each on a fixture decision log where it reads
zero and one where it counts, a mutant per reading, `grade_e9` unchanged on E11 under `grade_e10`, and `e_grade_10.py`."""
import json
import os
import subprocess
import sys

import pytest

from agent.base import gates_e as E
from .test_gates_e import art
from .test_gates_e7 import T0, _mutated, act, aline, result

HERE = os.path.dirname(os.path.abspath(__file__))
TESTING = os.path.dirname(os.path.dirname(HERE))
E11 = os.path.join(TESTING, "artifacts", "e_day_11-20261030-113732")


def grade(actions=(), results=(), log=None, frames=(), stop="day_cap"):
    a = art(actions=list(actions), results=list(results), startPyMs=T0 * 1000.0, t_loop0_ms=T0 * 1000.0)
    a["stop"]["reason"] = stop
    return E.grade_e10(a, decision_lines=log, lines=list(frames))


def _act(type_, **args):
    return {"type": type_, "args": args}


# ================================================================ the committed artifact
def _load(name):
    p = os.path.join(E11, name)
    if not os.path.isfile(p):
        pytest.skip("%s is not checked out" % E11)
    return p


def test_grade_e10_on_e11_changes_only_the_grade_name_the_six_readings_and_the_report():
    with open(_load("e_day_11.json"), encoding="utf-8") as fh:
        o = json.load(fh)
    log = [json.loads(l) for l in open(_load("decision.log"), encoding="utf-8") if l.strip()]
    e9 = E.grade_e9(o, decision_lines=log, state_dir=E11)
    e10 = E.grade_e10(o, decision_lines=log, state_dir=E11)
    new = ("corner", "finish_first", "hold_walk", "ride_wait", "door_walk", "fence_wait")
    skip = ("grade", "report_lines") + new
    assert e10["grade"] == "grade_e10" and all(e10[k]["read"] is True for k in new)
    assert {k: v for k, v in e9.items() if k not in skip} == {k: v for k, v in e10.items() if k not in skip}
    assert e10["report_lines"][:len(e9["report_lines"])][0] == e9["report_lines"][0]
    assert e10["report_lines"][1] == e9["report_lines"][1] and len(e10["report_lines"]) == len(e9["report_lines"]) + 6
    # E11 ran iteration 12: none of the six rules fired
    assert e10["corner"]["lines"] == e10["finish_first"]["lines"] == e10["ride_wait"]["lines"] == 0
    assert e10["door_walk"]["lines"] == e10["fence_wait"]["lines"] == e10["hold_walk"]["hold_walk"] == 0
    assert E.grade_e9(o, decision_lines=log, state_dir=E11)["kills"] == e9["kills"]
    assert e10["kills"] == e9["kills"]


# ================================================================ P25-A, the corner
def corner_fixture(repeat=False):
    log = [aline(0, 0.0, {"fight": True, "cornered": 1, "corner": {"kind": "break", "shoved": 1, "n": 2}},
                 _act("steer", heading=[1, 0], gait="run")),
           aline(1, 1.0, {"fight": True, "cornered": 1, "corner": {"kind": "swing", "shoved": 1, "n": 1}},
                 _act("attack", targetId=1)),
           aline(2, 10.0, {"fight": True, "target": 1}, _act("shove", targetId=1)),
           aline(3, 11.0 if repeat else 14.0, {"fight": True, "target": 1}, _act("shove", targetId=1))]
    return grade(log=log)["corner"]


def test_the_corner_counts_breaks_swings_and_the_shoves_repeated_within_the_window():
    g = corner_fixture()
    assert g["read"] is True and (g["lines"], g["break"], g["swing"]) == (2, 1, 1)
    assert (g["break_steers"], g["swing_attacks"], g["shoves"], g["repeat_shoves"]) == (1, 1, 2, 0)
    assert corner_fixture(repeat=True)["repeat_shoves"] == 1


def test_the_corner_reads_zero_without_a_corner_why_and_unread_without_a_log():
    g = grade(log=[aline(0, 0.0, {"fight": True, "target": 1}, _act("attack", targetId=1))])["corner"]
    assert (g["lines"], g["break"], g["swing"], g["shoves"]) == (0, 0, 0, 0)
    assert grade(log=None)["corner"] == {"read": False}


# ================================================================ P25-B, the stomp first
def finish_fixture(stomp=True, kill=True):
    log = [aline(0, 5.0, {"fight": True, "finish_first": {"target": 7, "dist": 4.5}}, _act("stomp", targetId=7) if stomp
                 else None, sent=stomp),
           aline(1, 6.0, {"fight": True, "finish_first": {"target": 8, "dist": 1.0}}, None, sent=False)]
    acts = [act("a1", "stomp", 5.0, targetId=7)] if stomp else []
    res = [result("a1", targetDead=kill, hit=kill)] if stomp else []
    return grade(acts, res, log)["finish_first"]


def test_the_finish_first_counts_the_stomps_sent_landed_and_those_beyond_reach():
    g = finish_fixture()
    assert (g["lines"], g["stomps"], g["landed"], g["beyond_reach"], g["max_dist"]) == (2, 1, 1, 1, 4.5)
    assert finish_fixture(kill=False)["landed"] == 0


def test_the_finish_first_reads_zero_without_the_why():
    g = grade(log=[aline(0, 0.0, {"fight": True, "target": 1}, _act("stomp", targetId=1))])["finish_first"]
    assert (g["lines"], g["stomps"], g["landed"], g["max_dist"]) == (0, 0, 0, None)


# ================================================================ P25-C, the hold walk
def hold_fixture(walk_near=False, quiet_end=True):
    def strain(n, t, e, walk=True, nearest=9.0):
        why = {"flee": "strain", "strain": {"kind": "endurance", "endurance": e}}
        if walk:
            why["hold_walk"] = True
        return aline(n, t, why, _act("steer", gait="walk"), nearest=nearest)
    log = [strain(0, 0.0, 0.73, nearest=3.0 if walk_near else 9.0), strain(1, 1.0, 0.74), strain(2, 2.0, 0.75, walk=False),
           aline(3, 3.0, {"fight": True, "target": 1}, _act("attack", targetId=1)),
           strain(4, 4.0, 0.60)]
    if not quiet_end:
        log = log[:3]
    return grade(log=log)["hold_walk"]


def test_the_hold_walk_counts_walking_lines_runs_and_the_release_under_the_line():
    g = hold_fixture()
    assert (g["strain_lines"], g["hold_walk"], g["walk_near"], g["runs"]) == (4, 3, 0, 2)
    assert (g["released_under"], g["open_runs"]) == (1, 1)
    assert hold_fixture(walk_near=True)["walk_near"] == 1
    open_end = hold_fixture(quiet_end=False)
    assert (open_end["released_under"], open_end["open_runs"]) == (0, 1)      # the log ends on the hold: no release read


def test_the_hold_walk_reads_zero_without_an_endurance_strain_flee():
    log = [aline(0, 0.0, {"flee": "strain", "strain": {"kind": "arms"}}, _act("steer")),
           aline(1, 1.0, {"flee": "many"}, _act("steer"))]
    g = grade(log=log)["hold_walk"]
    assert (g["strain_lines"], g["hold_walk"], g["runs"], g["released_under"], g["open_runs"]) == (0, 0, 0, 0, 0)


# ================================================================ P25-D, the ride waits
def test_the_ride_waits_count_lines_that_sent_nothing_and_the_rides_done():
    log = [aline(0, 0.0, {"fight": True, "ride_wait": 11}, None, sent=False),
           aline(1, 1.0, {"fight": True, "ride_wait": 11}, None, sent=False),
           aline(2, 2.0, {"fight": True, "ride_wait": 12}, None, sent=False)]
    acts = [dict(act("11", "bandage", 0.0), aid=11, state="done"), dict(act("12", "bandage", 1.0), aid=12, state="failed")]
    g = grade(acts, log=log)["ride_wait"]
    assert (g["lines"], g["sent"], g["rides"], g["rides_done"]) == (3, 0, 2, 1)
    sent = grade(acts, log=[aline(0, 0.0, {"fight": True, "ride_wait": 11}, _act("shove", targetId=1))])["ride_wait"]
    assert sent["sent"] == 1


def test_the_ride_waits_read_zero_without_the_why():
    g = grade(log=[aline(0, 0.0, {"fight": True, "target": 1}, None, sent=False)])["ride_wait"]
    assert (g["lines"], g["sent"], g["rides"], g["rides_done"]) == (0, 0, 0, 0)


# ================================================================ P25-E, the stalled walk
def test_the_door_walk_counts_reroutes_drops_and_the_doorway_left_stall():
    log = [aline(0, 0.0, {"flee": "many", "door_walk": {"stall": 20.5, "end": "reroute"}}, _act("walkTo", x=1, y=2)),
           aline(1, 30.0, {"flee": "many", "door_walk": {"stall": 21.0, "end": "drop"}, "doorway_left": "stall"},
                 _act("steer"))]
    g = grade(log=log)["door_walk"]
    assert (g["lines"], g["reroute"], g["drop"], g["left_stall"], g["max_stall"]) == (2, 1, 1, 1, 21.0)


def test_the_door_walk_reads_zero_without_the_why():
    g = grade(log=[aline(0, 0.0, {"flee": "many", "doorway_left": "quiet"}, _act("steer"))])["door_walk"]
    assert (g["lines"], g["reroute"], g["drop"], g["left_stall"], g["max_stall"]) == (0, 0, 0, 0, None)


# ================================================================ P25-F, the fence wait
def fence(n, t, leg, sent=True):
    return aline(n, t, {"fight": True, "leg": leg,
                        "fence_wait": {"target": 3, "fence": [10, 20], "dist": 2.0, "leg": leg}},
                 _act("aim", targetId=3) if sent else None, sent=sent)


def fence_fixture(after):
    log = [fence(0, 0.0, "back"), fence(1, 1.0, "stand", sent=False), after, fence(3, 5.0, "toward")]
    return grade(log=log)["fence_wait"]


def test_the_fence_wait_counts_the_legs_aims_waits_and_their_outcomes():
    g = fence_fixture(aline(2, 2.0, {"fight": True, "target": 3}, _act("attack", targetId=3)))
    assert (g["lines"], g["aims"], g["waits"]) == (3, 2, 2) and g["legs"] == {"back": 1, "stand": 1, "toward": 1}
    assert g["outcomes"] == {"swing": 1, "stomp": 0, "other": 0, "open": 1}
    s = fence_fixture(aline(2, 2.0, {"fight": True, "target": 3}, _act("stomp", targetId=3)))
    assert s["outcomes"]["stomp"] == 1
    o = fence_fixture(aline(2, 2.0, {"fight": True, "target": 3}, None, sent=False))
    assert o["outcomes"]["other"] == 1


def test_the_fence_wait_reads_zero_without_the_why():
    g = grade(log=[aline(0, 0.0, {"fight": True, "target": 1}, None, sent=False)])["fence_wait"]
    assert (g["lines"], g["aims"], g["waits"], g["legs"]) == (0, 0, 0, {})


# ================================================================ the report
def test_the_report_names_the_six_rules_and_marks_reading_or_inference():
    g = grade(log=[aline(0, 0.0, {"fight": True, "target": 1}, None, sent=False)])
    r = g["report_lines"]
    assert len(r) >= 6 and g["grade"] == "grade_e10"
    tags = ("corner (P25-A) [reading]", "finish first (P25-B) [reading]", "hold walk (P25-C)", "ride wait (P25-D) [reading]",
            "door walk (P25-E) [reading]", "fence wait (P25-F) [reading]")
    for t in tags:
        assert any(l.startswith(t) for l in r), t
    assert any("[inference" in l for l in r)
    assert not any(l.startswith("gate_e9 ") for l in r)
    nolog = grade(log=None)["report_lines"]
    assert any(l == "corner (P25-A): no decision log read" for l in nolog)


# ================================================================ a mutant per reading
def _sets(fn):
    return lambda: fn()


MUTANTS = [
    ("e_corner", lambda b: b.replace("w - last[zid] <= SHOVE_REPEAT_S", "w - last[zid] < 0"),
     lambda: corner_fixture(repeat=True)["repeat_shoves"] == 1),
    ("e_corner", lambda b: b.replace('c.get("kind") in kinds', 'c.get("kind") == "break"'),
     lambda: corner_fixture()["swing"] == 1),
    ("e_finish_first", lambda b: b.replace("d > FIGHT_REACH", "d > 99"), lambda: finish_fixture()["beyond_reach"] == 1),
    ("e_finish_first", lambda b: b.replace("and _landed(L, ln)", ""), lambda: finish_fixture(kill=False)["landed"] == 0),
    ("e_hold_walk", lambda b: b.replace("d <= DANGER_R", "d > DANGER_R"), lambda: hold_fixture(walk_near=True)["walk_near"] == 1),
    ("e_hold_walk", lambda b: b.replace("cur < ENDURANCE_RELEASE", "cur > ENDURANCE_RELEASE"),
     lambda: hold_fixture()["released_under"] == 1),
    ("e_ride_wait", lambda b: b.replace("states.get(a) == \"done\"", "True"),
     lambda: grade([dict(act("11", "bandage", 0.0), aid=11, state="failed")],
                   log=[aline(0, 0.0, {"fight": True, "ride_wait": 11}, None, sent=False)])["ride_wait"]["rides_done"] == 0),
    ("e_door_walk", lambda b: b.replace('== "stall"', '== "xx"'),
     lambda: grade(log=[aline(0, 0.0, {"flee": "many", "door_walk": {"stall": 20.5, "end": "drop"},
                                       "doorway_left": "stall"}, _act("steer"))])["door_walk"]["left_stall"] == 1),
    ("e_door_walk", lambda b: b.replace('dw.get("end") in ends', 'dw.get("end") == "drop"'),
     lambda: grade(log=[aline(0, 0.0, {"flee": "many", "door_walk": {"stall": 20.5, "end": "reroute"}},
                              _act("walkTo", x=1, y=2))])["door_walk"]["reroute"] == 1),
    ("e_fence_wait", lambda b: b.replace('"swing" if _sent(ln, "attack")', '"other" if _sent(ln, "attack")'),
     lambda: fence_fixture(aline(2, 2.0, {"fight": True, "target": 3}, _act("attack", targetId=3)))["outcomes"]["swing"] == 1),
    ("e_fence_wait", lambda b: b.replace("waits += 0 if inrun else 1", "waits += 1"),
     lambda: fence_fixture(aline(2, 2.0, {"fight": True, "target": 3}, None, sent=False))["waits"] == 2),
]


@pytest.mark.parametrize("n", range(len(MUTANTS)), ids=lambda n: "%s-%d" % (MUTANTS[n][0], n))
def test_a_mutant_of_each_reading_fails_its_fixture(n, monkeypatch):
    fn_name, edit, holds = MUTANTS[n]
    assert holds(), "the fixture must hold on the real function"
    monkeypatch.setattr(E, fn_name, _mutated(fn_name, edit)[fn_name])
    assert not holds(), "the mutant of %s survives its fixture" % fn_name


# ================================================================ e_grade_10.py
def test_e_grade_10_is_e_grade_9s_command_line_over_grade_e10(tmp_path):
    (tmp_path / "a.json").write_text(json.dumps(art(startPyMs=T0 * 1000.0, t_loop0_ms=T0 * 1000.0)), encoding="utf-8")
    script = os.path.join(TESTING, "agent", "drivers", "e_grade_10.py")
    r = subprocess.run([sys.executable, script, str(tmp_path / "a.json")], capture_output=True, text=True, cwd=TESTING)
    assert r.returncode == 0 and r.stdout.startswith("kills ") and "\nkills sources: " in r.stdout
    assert json.loads(r.stdout[r.stdout.index("\n{\n"):])["grade"] == "grade_e10"
    c = subprocess.run([sys.executable, script, "--chain", str(tmp_path / "a.json"), str(tmp_path / "a.json")],
                       capture_output=True, text=True, cwd=TESTING)
    assert c.returncode == 0 and "\ngate_e10 " in c.stdout
    for args in ([], ["a", "b", "c"], [str(tmp_path / "nope.json")]):
        assert subprocess.run([sys.executable, script, *args], capture_output=True, cwd=TESTING).returncode == 2
