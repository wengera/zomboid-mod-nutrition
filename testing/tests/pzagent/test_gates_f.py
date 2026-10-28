"""base/gates_f.py (Plan 23 Task 15), offline: grade_f1 over an LLM session artifact."""
import json
import os
import subprocess
import sys

from agent.base import gates_e as E
from agent.base import gates_f as F
from agent.drivers import f_grade as FG
from .test_gates_e import art, good

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


def test_the_script(tmp_path):
    p = tmp_path / "f.json"
    p.write_text(json.dumps(f_art([call(1.0)], [goal("eat", "done")])), encoding="utf-8")
    script = os.path.join(os.path.dirname(F.__file__), "..", "drivers", "f_grade.py")
    cwd = os.path.dirname(os.path.dirname(HERE))
    r = subprocess.run([sys.executable, script, str(p)], capture_output=True, text=True, cwd=cwd)
    assert r.returncode == 0 and json.loads(r.stdout[r.stdout.index("\n{\n"):])["llm"]["calls"] == 1
    assert any(l.startswith("llm:") for l in r.stdout.splitlines())
    for args in ([], ["a", "b"], [str(tmp_path / "nope.json")]):
        assert subprocess.run([sys.executable, script] + args, capture_output=True, text=True,
                              cwd=cwd).returncode == 2
    assert FG.finite(float("-inf")) is None
