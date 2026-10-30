"""base/gates_e.py pass 9 (Plan 24 Task 40), offline: `grade_e9` reads the kills off the act lines (every SWING_TYPES send
whose result read targetDead true, by the sent action's target id, deduplicated) and off the zombie_dead events, on the three
committed artifacts (E11: 3, 3, 3 with two stomps; E10: 0; E8: 4 as grade_e5 read), a mutant per rule, `grade_e8` unchanged
on E11's committed report, and `e_grade_9.py`."""
import json
import os
import subprocess
import sys

import pytest

from agent.base import gates_e as E
from .test_gates_e import art
from .test_gates_e7 import T0, _mutated

HERE = os.path.dirname(os.path.abspath(__file__))
TESTING = os.path.dirname(os.path.dirname(HERE))
E8 = os.path.join(TESTING, "artifacts", "e_day_8-20261029-174023")
E10 = os.path.join(TESTING, "artifacts", "e_day_10-20261030-084253")
E11 = os.path.join(TESTING, "artifacts", "e_day_11-20261030-113732")


def _load(d, name):
    if not os.path.isfile(os.path.join(d, name + ".json")):
        pytest.skip("%s is not checked out" % d)
    with open(os.path.join(d, name + ".json"), encoding="utf-8") as fh:
        return json.load(fh)


def _log(d):
    return [json.loads(l) for l in open(os.path.join(d, "decision.log"), encoding="utf-8") if l.strip()]


# ---------------------------------------------------------------- the committed artifacts
def test_grade_e9_on_e11_reads_three_kills_off_two_stomps_and_an_attack_that_the_events_and_the_engine_agree_with():
    g = E.grade_e9(_load(E11, "e_day_11"), decision_lines=_log(E11), state_dir=E11)
    k = g["kills"]
    assert g["grade"] == "grade_e9" and k["planner"] == 3 and k["planner_ids"] == [27615, 27609, 27581]
    assert (k["events"], k["event_ids"], k["engine"], k["agree"], k["source"]) == (
        3, [27615, 27609, 27581], 3, True, "act lines")
    assert sum(k["per_fight"]) == 3
    assert g["report_lines"][0].startswith("kills 3 (engine 3, planner 3); died at 622")
    assert g["report_lines"][1] == "kills sources: planner 3 (act lines), zombie_dead events 3, engine 3; agree"


def test_grade_e9_on_e10_reads_no_kill_from_any_source():
    g = E.grade_e9(_load(E10, "e_day_10"), decision_lines=_log(E10), state_dir=E10)
    k = g["kills"]
    assert (k["planner"], k["events"], k["planner_ids"]) == (0, 0, []) and set(k["per_fight"]) == {0}


def test_grade_e9_on_e8_reads_the_four_kills_grade_e5_read():
    o = _load(E8, "e_day_8")
    g = E.grade_e9(o, decision_lines=_log(E8), state_dir=E8)
    assert g["kills"]["planner_ids"] == [16288, 16324, 16320, 16322] == E.e_kills(o)["planner_ids"]
    assert g["kills"]["events"] == 4 and g["kills"]["agree"] is True


def test_grade_e8_still_reproduces_e11s_committed_report_and_grade_e9_changes_only_the_kills_and_the_report():
    o = _load(E11, "e_day_11")
    e8 = E.grade_e8(o, decision_lines=_log(E11), state_dir=E11)
    assert e8["kills"]["planner"] == 1
    e9 = E.grade_e9(o, decision_lines=_log(E11), state_dir=E11)
    skip = ("grade", "kills", "report_lines")
    assert {k: v for k, v in e8.items() if k not in skip} == {k: v for k, v in e9.items() if k not in skip}
    script = os.path.join(TESTING, "agent", "drivers", "e_grade_8.py")
    r = subprocess.run([sys.executable, script, os.path.join(E11, "e_day_11.json")], capture_output=True)
    with open(os.path.join(E11, "e_grade.txt"), "rb") as fh:
        assert r.returncode == 0 and r.stdout == fh.read()


# ---------------------------------------------------------------- fixtures
def action(aid, type_, sent_s, zid):
    return {"aid": aid, "type": type_, "state": "done", "sentS": sent_s, "args": {"targetId": zid}}


def actline(aid, type_, dead, seq):
    return {"kind": "act", "aid": aid, "type": type_, "state": "done", "seq": seq,
            "result": {"targetDead": dead}, "snapshot": {"nearest": {"id": 999}}}


def fixture(types=("stomp", "shove", "attack"), dup=False):
    acts = [action("a1", types[0], 10.0, 7), action("a2", types[1], 20.0, 8), action("a3", types[2], 30.0, 8 if dup else 9)]
    lines = [actline("a1", types[0], True, 1), actline("a2", types[1], True, 2), actline("a3", types[2], True, 3),
             {"kind": "event", "event": "zombie_dead", "id": 7, "seq": 4}]
    o = art(actions=acts, startPyMs=T0 * 1000.0, t_loop0_ms=T0 * 1000.0,
            fights=[{"startS": 5.0, "end": {"endS": 15.0}}, {"startS": 18.0, "end": {"endS": 40.0}}])
    return o, lines


def test_every_swing_type_counts_by_the_sent_targets_id_and_the_fights_split_them():
    o, lines = fixture()
    g = E.grade_e9(o, lines=lines)
    k = g["kills"]
    assert k["planner_ids"] == [7, 8, 9] and k["per_fight"] == [1, 2] and (k["events"], k["agree"]) == (1, None)


def test_an_act_line_that_read_targetdead_false_and_a_non_swing_type_do_not_count():
    o, lines = fixture(types=("bandage", "shove", "attack"))
    lines[1]["result"]["targetDead"] = False
    assert E.grade_e9(o, lines=lines)["kills"]["planner_ids"] == [9]


def test_a_record_without_state_lines_reads_the_swing_results_off_loop_results():
    o, lines = fixture()
    o["loop"]["results"] = [{"aid": l["aid"], "type": l["type"], "state": "done", "result": l["result"]}
                            for l in lines if l["kind"] == "act"]
    k = E.grade_e9(o, lines=[])["kills"]
    assert k["planner_ids"] == [7, 8, 9] and k["source"] == "loop.results" and k["events"] is None


def test_the_dedup_counts_a_target_killed_by_two_sends_once():
    o, lines = fixture(dup=True)
    assert E.grade_e9(o, lines=lines)["kills"]["planner_ids"] == [7, 8]


# ---------------------------------------------------------------- a mutant per rule
MUTANTS = [
    ("_act_kills", lambda b: b.replace("not in SWING_TYPES", "not in (\"attack\", \"aim\")"),
     lambda: E.grade_e9(*[fixture()[0]], lines=fixture()[1])["kills"]["planner"] == 3),
    ("_act_kills", lambda b: b.replace("zid is None or zid in seen", "zid is None"),
     lambda: E.grade_e9(fixture(dup=True)[0], lines=fixture(dup=True)[1])["kills"]["planner"] == 2),
    ("_dead_events", lambda b: b.replace(" and l.get(\"id\") not in ids", ""),
     lambda: E._dead_events([{"kind": "event", "event": "zombie_dead", "id": 1}] * 2) == [1]),
]


@pytest.mark.parametrize("fn_name,edit,holds", MUTANTS, ids=["stomp-dropped", "dedup", "event-dedup"])
def test_a_mutant_of_each_rule_fails_its_fixture(monkeypatch, fn_name, edit, holds):
    assert holds(), "the fixture must hold on the real function"
    monkeypatch.setattr(E, fn_name, _mutated(fn_name, edit)[fn_name])
    assert not holds(), "the mutant of %s survives its fixture" % fn_name


# ---------------------------------------------------------------- e_grade_9.py
def test_e_grade_9_is_e_grade_8s_command_line_over_grade_e9(tmp_path):
    (tmp_path / "a.json").write_text(json.dumps(art(startPyMs=T0 * 1000.0, t_loop0_ms=T0 * 1000.0)), encoding="utf-8")
    script = os.path.join(TESTING, "agent", "drivers", "e_grade_9.py")
    r = subprocess.run([sys.executable, script, str(tmp_path / "a.json")], capture_output=True, text=True, cwd=TESTING)
    assert r.returncode == 0 and r.stdout.startswith("kills ") and "\nkills sources: " in r.stdout
    assert json.loads(r.stdout[r.stdout.index("\n{\n"):])["grade"] == "grade_e9"
    c = subprocess.run([sys.executable, script, "--chain", str(tmp_path / "a.json"), str(tmp_path / "a.json")],
                       capture_output=True, text=True, cwd=TESTING)
    assert c.returncode == 0 and "\ngate_e9 " in c.stdout
    for args in ([], ["a", "b", "c"], [str(tmp_path / "nope.json")]):
        assert subprocess.run([sys.executable, script, *args], capture_output=True, cwd=TESTING).returncode == 2
