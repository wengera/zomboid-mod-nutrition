"""base/gates_f.py (Plan 23 Task 15), offline: grade_f1 over an LLM session artifact."""
import json
import os
import subprocess
import sys

from agent.base import gates_e as E
from agent.base import gates_f as F
from agent.drivers import f_grade as FG
from .test_gates_e import _event_death_art, art, good

HERE = os.path.dirname(os.path.abspath(__file__))


def goal(type_, state, source="llm"):
    return {"type": type_, "args": {}, "state": state, "reason": None, "startS": 0.0, "endS": 1.0, "source": source}


def call(latency, ok=True):
    return {"wall": 1.0, "latency_s": latency, "ok": ok, "goal": "x", "error": None if ok else "boom",
            "prompt_bytes": 100}


def f_art(calls, goals, **kw):
    a = good(**kw)
    a["loop"]["goals"] = goals
    a["loop"]["llm"] = {"calls": calls, "model": "m", "cli_version": "1"}
    return a


def test_grade_f1_is_grade_e1_plus_the_llm_block():
    a = f_art([call(1.0), call(2.0), call(9.0, ok=False), call(3.0)],
              [goal("eat", "done"), goal("eat", "failed"), goal("sleep", "superseded"), goal("drink", "done", "scripted")])
    g = F.grade_f1(a)
    e = E.grade_e1(a)
    assert g["grade"] == "grade_f1" and g["needs"] == e["needs"] and g["fights"] == e["fights"]
    assert g["llm"] == {"calls": 4, "ok": 3, "fallbacks": 1, "latency_p50": 2.0, "latency_p99": 9.0,
                        "goals_by_type": {"eat": 2, "sleep": 1, "drink": 1},
                        "goal_ends": {"done": 2, "failed": 1, "superseded": 1}}
    assert g["report_lines"][-1].startswith("llm: 4 calls (3 ok, 1 fallbacks)")


def test_a_session_without_llm_keys_reads_as_empty_and_never_raises():
    for bad in ({}, None, "x", {"loop": {"llm": None, "goals": 5}}, art()):
        g = F.grade_f1(bad)
        assert g["llm"]["calls"] == 0 and g["llm"]["latency_p50"] is None
        assert g["llm"]["goal_ends"] == {"done": 0, "failed": 0, "superseded": 0}
    g = F.grade_f1({"loop": {"llm": {"calls": [None, {"ok": "yes"}, {"latency_s": 1.5, "ok": True}]}}})
    assert g["llm"]["calls"] == 3 and g["llm"]["ok"] == 1 and g["llm"]["fallbacks"] == 2
    assert g["llm"]["latency_p50"] == 1.5


def test_the_f_grade_carries_the_death_and_the_survival_of_the_e_grade():
    a = f_art([], [], stop="death") if False else f_art([], [])
    a["stop"]["reason"] = "death"
    a["loop"]["death"] = {"last_frames": a["loop"]["last_frames"], "server_damage": []}
    g = F.grade_f1(a)
    assert g["survived"] is False and g["death"]["explained"] is False


def test_grade_f2_is_grade_e2_plus_the_llm_arm_of_grade_f1():
    a = f_art([call(1.0), call(2.0), call(9.0, ok=False), call(3.0)],
              [goal("eat", "done"), goal("eat", "failed"), goal("sleep", "superseded"), goal("drink", "done", "scripted")])
    g, g1, e = F.grade_f2(a), F.grade_f1(a), E.grade_e2(a)
    assert g["grade"] == "grade_f2" and g["llm"] == g1["llm"] and g["needs"] == e["needs"]
    assert g["report_lines"][:-1] == E.grade_e2(a)["report_lines"] and g["report_lines"][-1] == g1["report_lines"][-1]
    assert F.grade_f1(a)["grade"] == "grade_f1"
    for bad in ({}, None, "x", {"loop": {"llm": None, "goals": 5}}):
        assert F.grade_f2(bad)["llm"] == F.grade_f1(bad)["llm"]


def test_grade_f2_carries_the_death_signal_of_an_event_death():
    a = _event_death_art()
    a["loop"]["goals"] = []
    a["loop"]["llm"] = {"calls": [call(1.0)], "model": "m", "cli_version": "1"}
    g = F.grade_f2(a)
    assert g["survived"] is False and g["death"]["check"]["signal"] == "event"
    assert g["death"] == E.grade_e2(a)["death"]
    assert any(l.startswith("death (signal event)") for l in g["report_lines"])
    assert "signal" not in (F.grade_f1(a)["death"] or {}).get("check", {})


def test_the_script(tmp_path):
    p = tmp_path / "f.json"
    p.write_text(json.dumps(f_art([call(1.0)], [goal("eat", "done")])), encoding="utf-8")
    script = os.path.join(os.path.dirname(F.__file__), "..", "drivers", "f_grade.py")
    cwd = os.path.dirname(os.path.dirname(HERE))
    r = subprocess.run([sys.executable, script, str(p)], capture_output=True, text=True, cwd=cwd)
    assert r.returncode == 0 and json.loads(r.stdout[r.stdout.index("\n{\n"):])["llm"]["calls"] == 1
    assert json.loads(r.stdout[r.stdout.index("\n{\n"):])["grade"] == "grade_f2"      # the default pass
    r1 = subprocess.run([sys.executable, script, "--grade", "f1", str(p)], capture_output=True, text=True, cwd=cwd)
    assert r1.returncode == 0 and json.loads(r1.stdout[r1.stdout.index("\n{\n"):])["grade"] == "grade_f1"
    assert any(l.startswith("llm:") for l in r.stdout.splitlines())
    for args in ([], ["a", "b"], [str(tmp_path / "nope.json")]):
        assert subprocess.run([sys.executable, script] + args, capture_output=True, text=True,
                              cwd=cwd).returncode == 2
    assert FG.finite(float("-inf")) is None


# ================================================================ pass 3 (Plan 24 Task 11)
def test_grade_f3_is_grade_e3_plus_the_llm_arm_and_leaves_grade_f2_as_it_was():
    from .test_gates_e import care_art
    a = care_art()
    a["loop"]["goals"] = [goal("eat", "done"), goal("sleep", "failed")]
    a["loop"]["llm"] = {"calls": [call(1.0), call(9.0, ok=False)], "model": "m", "cli_version": "1"}
    g, g2, e = F.grade_f3(a), F.grade_f2(a), E.grade_e3(a)
    assert g["grade"] == "grade_f3" and g["llm"] == g2["llm"] and g["care"] == e["care"] and g["wounds"] == e["wounds"]
    assert g["care"]["fill"]["done"] == 2 and g["care"]["need_chain"]["fills_done"] == 2
    assert g["report_lines"][:-1] == E.grade_e3(a)["report_lines"] and g["report_lines"][-1] == g2["report_lines"][-1]
    assert g2["grade"] == "grade_f2" and "care" not in g2 and "wounds" not in g2
    for bad in ({}, None, "x", {"loop": {"llm": None, "goals": 5}}):
        assert F.grade_f3(bad)["llm"] == F.grade_f2(bad)["llm"]


def test_grade_f3_does_not_count_a_bandage_on_a_full_health_part_as_a_wound():
    from .test_gates_e import BANDAGED, _bandage_art
    a = _bandage_art(BANDAGED, stop="death")
    a["loop"]["death"] = {"last_frames": a["loop"]["last_frames"], "server_damage": []}
    assert F.grade_f3(a)["death"]["first_wound_seq"] is None and F.grade_f2(a)["death"]["first_wound_seq"] == 101
    assert F.grade_f3(a)["wounds"]["real"] == 0 and F.grade_f3(a)["wounds"]["listed"] == 1


def test_the_f3_script(tmp_path):
    from .test_gates_e import care_art
    p = tmp_path / "f.json"
    p.write_text(json.dumps(care_art()), encoding="utf-8")
    script = os.path.join(os.path.dirname(F.__file__), "..", "drivers", "f_grade_3.py")
    cwd = os.path.dirname(os.path.dirname(HERE))
    r = subprocess.run([sys.executable, script, str(p)], capture_output=True, text=True, cwd=cwd)
    assert r.returncode == 0 and json.loads(r.stdout[r.stdout.index("\n{\n"):])["grade"] == "grade_f3"
    assert any(l.startswith("llm:") for l in r.stdout.splitlines()) and "\ncare: bandage sent 3" in r.stdout
    for args in ([], ["a", "b"], [str(tmp_path / "nope.json")]):
        assert subprocess.run([sys.executable, script] + args, capture_output=True, text=True,
                              cwd=cwd).returncode == 2


# ================================================================ pass 4 (Plan 24 Task 17)
def test_grade_f4_is_grade_e4_plus_the_llm_arm_and_leaves_grade_f3_as_it_was():
    from .test_gates_e import _kill_art
    a = _kill_art(engine=2)
    a["loop"]["goals"] = [goal("eat", "done"), goal("sleep", "failed")]
    a["loop"]["llm"] = {"calls": [call(1.0), call(9.0, ok=False)], "model": "m", "cli_version": "1"}
    g, g3, e = F.grade_f4(a), F.grade_f3(a), E.grade_e4(a)
    assert g["grade"] == "grade_f4" and g["llm"] == g3["llm"] and g3["grade"] == "grade_f3" and "kills" not in g3
    for k in ("kills", "stance_held", "ride", "yields", "glides", "care", "wounds"):
        assert g[k] == e[k]
    assert g["report_lines"][0].startswith("kills 2 (engine 2, planner 1); died at 605")
    assert g["report_lines"][-1].startswith("llm:") and g["report_lines"][:-1] == e["report_lines"]
    for bad in ({}, None, "x", {"loop": {"llm": None, "goals": 5}}):
        assert F.grade_f4(bad)["llm"] == F.grade_f3(bad)["llm"]


def test_the_f4_script(tmp_path):
    from .test_gates_e import _kill_art
    p = tmp_path / "f.json"
    p.write_text(json.dumps(_kill_art(engine=2)), encoding="utf-8")
    script = os.path.join(os.path.dirname(F.__file__), "..", "drivers", "f_grade_4.py")
    cwd = os.path.dirname(os.path.dirname(HERE))
    r = subprocess.run([sys.executable, script, str(p)], capture_output=True, text=True, cwd=cwd)
    assert r.returncode == 0 and r.stdout.startswith("kills 2 (engine 2, planner 1)")
    assert json.loads(r.stdout[r.stdout.index("\n{\n"):])["grade"] == "grade_f4"
    assert any(l.startswith("llm:") for l in r.stdout.splitlines())
    for args in ([], ["a", "b"], [str(tmp_path / "nope.json")]):
        assert subprocess.run([sys.executable, script] + args, capture_output=True, text=True,
                              cwd=cwd).returncode == 2
