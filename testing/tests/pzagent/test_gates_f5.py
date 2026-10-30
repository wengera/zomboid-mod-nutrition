"""base/gates_f.py grade_f5 (Plan 24 Task 35), offline: the LLM session's readings over fixture goals logs (rows of the
LLMSource's goals.log, each carrying the rendered view as its `prompt`, built here by the real `view.render`) and a
fixture artifact. Every test builds its own input and uses no pytest fixture, so the mutation pass can run the test
functions against a mutated copy of gates_f (module-level `F`)."""
import json
import os
import subprocess
import sys

import pytest

from agent.base import gates_e as E
from agent.base import gates_f as F
from agent.base.planner import view as V
from agent.drivers import f_grade_5 as FG
from .test_gates_e import good

HERE = os.path.dirname(os.path.abspath(__file__))


def bld(i, dist, flags="", z=None, holds=None):
    return {"id": i, "x": 10 * i, "y": 5, "door": [10 * i, 4], "dist": dist, "containers": 3,
            "looted": "L" in flags, "visited": "v" in flags, "shunned": "s" in flags, "blocked": "x" in flags,
            "holds": holds or {}, **({"zombies_near": z} if z is not None else {})}


def prompt(buildings, night=False, tired=False, last_goal=None):
    v = {"pos": {"x": 1, "y": 2, "z": 0}, "hour": 12.0, "health": 100, "kills": 0, "buildings": buildings,
         "last_goal": last_goal, "night": night, "tired": tired}
    return V.render(v)


def row(goal=None, error=None, p=None, answer=None, latency=2.0, ok=None):
    goal = dict(goal) if goal else None
    ok = (goal is not None and error is None) if ok is None else ok
    ans = answer if answer is not None else (json.dumps(goal) if goal else None)
    return {"wall": 1.0, "latency_s": latency, "ok": ok, "goal": goal if ok else None, "error": error,
            "prompt": p if p is not None else prompt([bld(1, 3.0)]), "answer": ans,
            "answer_bytes": len(ans or ""), "prompt_bytes": 100, "model": "sonnet"}


def art(rows, goals=()):
    a = good()
    a["loop"]["llm"] = {"calls": [{k: v for k, v in r.items() if k not in ("prompt", "answer")} for r in rows],
                        "model": "sonnet", "cli_version": "1"}
    a["loop"]["goals"] = list(goals)
    return a


def g5(rows, goals=()):
    return F.grade_f5(art(rows, goals), goal_lines=rows)


def gl(type_, source="llm", state="done"):
    return {"type": type_, "args": {}, "state": state, "reason": None, "startS": 0.0, "endS": 1.0, "source": source}


# ================================================================ the zero cases
def test_a_session_without_a_goals_log_reads_what_the_artifact_carries_and_never_raises():
    rows = [row({"type": "Rest", "seconds": 5}), row(error="timeout", latency=20.0), row(error="malformed")]
    g = F.grade_f5(art(rows))
    assert g["grade"] == "grade_f5" and g["answers"]["read"] is False and g["strategy"]["read"] is False
    assert g["refusals"]["read"] is False
    assert g["answers"]["by_type"] == {"Rest": 1} and g["answers"]["weapon"] is None
    assert g["latency"]["timeouts"] == 1 and g["latency"]["malformed"] == 1 and g["latency"]["answered"] == 2
    assert any("no goals.log read" in l for l in g["report_lines"])
    for bad in ({}, None, "x", {"loop": {"llm": None, "goals": 5}}):
        h = F.grade_f5(bad, goal_lines=[None, 3])
        assert h["grade"] == "grade_f5" and h["latency"]["calls"] == 0 and h["fallback"]["goals"] == 0
        assert h["strategy"]["shelter"]["answers"] == 0 and h["refusals"]["carried"] == 0


def test_grade_f5_carries_grade_e7_and_the_llm_arm():
    rows = [row({"type": "Rest", "seconds": 5}), row(error="timeout", latency=20.0)]
    a = art(rows, [gl("Rest"), gl("ExploreToward", "scripted")])
    g, e = F.grade_f5(a, goal_lines=rows), E.grade_e7(a)
    assert g["grade"] == "grade_f5" and g["llm"] == F.f_llm(a) == F.grade_f4(a)["llm"]
    for k in ("pull", "wounded", "shots", "doorway", "kills", "needs"):
        assert g[k] == e[k], k
    assert g["report_lines"][0] == E.report_lines_e7(e)[0]
    assert F.grade_f4(a)["grade"] == "grade_f4" and F.gate_f5([a]) == E.gate_e7([a])


# ================================================================ (a) the answers
def test_the_answers_by_type_and_want_and_the_refused_bag():
    rows = [row({"type": "LootBuilding", "building": 1, "want": "weapon"}),
            row({"type": "LootBuilding", "building": 1}),
            row({"type": "LootBuilding", "building": 1, "want": "weapon"}),
            row({"type": "ExploreToward", "x": 1, "y": 2}),
            row(error="invalid: want 'bag' is not one of ['weapon']", answer='{"type": "LootBuilding", "building": 1, "want": "bag"}'),
            row(error="invalid: bad", answer='{"type": "LootBuilding", "building": 1, "want": null}')]
    a = g5(rows)["answers"]
    assert a["read"] is True and a["by_type"] == {"LootBuilding": 3, "ExploreToward": 1}
    assert a["weapon"] == 2 and a["bag_refused"] == 1 and a["by_want"] == {"weapon": 2}
    zero = g5([row({"type": "Rest", "seconds": 5})])["answers"]
    assert zero["weapon"] == 0 and zero["bag_refused"] == 0 and zero["by_want"] == {}


# ================================================================ (b) the strategy lines
def test_shelter_answers_by_tired_and_night_in_the_view():
    sh = {"type": "Shelter", "building": 1}
    rows = [row(sh, p=prompt([bld(1, 3.0)], night=True)), row(sh, p=prompt([bld(1, 3.0)], tired=True)),
            row(sh, p=prompt([bld(1, 3.0)], night=True, tired=True)), row(sh, p=prompt([bld(1, 3.0)])),
            row(sh, p="pos: {}\nbuildings: 1 @1,1 door - 1.0 c1 -"), row(sh, p="night: false\ntired: null")]
    s = g5(rows)["strategy"]["shelter"]
    assert s == {"answers": 6, "tired_or_night": 3, "neither": 1, "unread": 2}
    z = g5([row({"type": "Rest", "seconds": 5})])["strategy"]["shelter"]
    assert z == {"answers": 0, "tired_or_night": 0, "neither": 0, "unread": 0}


def test_loot_answers_against_the_zombies_listed_beside_each_building():
    def loot(b):
        return {"type": "LootBuilding", "building": b}
    z0 = [bld(1, 5.0, z=0), bld(2, 9.0, z=4)]
    rows = [row(loot(1), p=prompt(z0)),                                   # a z:0 building chosen
            row(loot(2), p=prompt(z0)),                                   # z above 0 while a z:0 building was shown
            row(loot(2), p=prompt([bld(2, 9.0, z=4), bld(3, 11.0, z=2)])),    # z above 0, no z:0 shown
            row(loot(1), p=prompt([bld(1, 5.0)]))]                        # no z on the line (old view)
    s = g5(rows)["strategy"]["loot"]
    assert s == {"answers": 4, "z0": 1, "zpos_with_z0_shown": 1, "zpos_no_z0_shown": 1, "unread": 1}
    assert g5([row({"type": "Rest", "seconds": 5})])["strategy"]["loot"]["answers"] == 0


def test_the_nearest_unlooted_rule_ranks_the_choice_among_the_unlooted_shown():
    def loot(b):
        return {"type": "LootBuilding", "building": b}
    bs = [bld(1, 2.0, "L"), bld(2, 4.0), bld(3, 6.0), bld(4, 7.0, "x"), bld(5, 8.0)]
    rows = [row(loot(2), p=prompt(bs)),           # rank 0 (the looted 1 and the blocked 4 left out)
            row(loot(3), p=prompt(bs)),           # rank 1
            row(loot(5), p=prompt(bs)),           # rank 2
            row(loot(2), p=prompt(bs)),
            row(loot(1), p=prompt(bs)),           # a looted building chosen: rank unread (the refusal rule's)
            row(loot(2), p="pos: {}")]            # no building line
    n = g5(rows)["strategy"]["nearest"]
    assert n == {"answers": 6, "rank0": 2, "ranks": {"0": 2, "1": 1, "2": 1}, "unranked": 2}
    tie = [bld(1, 4.0), bld(2, 4.0), bld(3, 5.0)]
    assert g5([row(loot(2), p=prompt(tie))])["strategy"]["nearest"]["rank0"] == 1     # a tie is nearest


def test_the_loop_line_counts_the_relooted_buildings():
    rows = [row(error="invalid: looted already"), row(error="invalid: looted already"), row(error="invalid: refused"),
            row({"type": "Rest", "seconds": 5})]
    assert g5(rows)["strategy"]["loop"] == {"looted_already": 2}
    assert F.grade_f5(art(rows))["strategy"]["loop"] == {"looted_already": 2}          # read off the artifact's calls
    assert g5([row({"type": "Rest", "seconds": 5})])["strategy"]["loop"] == {"looted_already": 0}


# ================================================================ (c) the refusals
def refused(why, type_="LootBuilding", building=9):
    return {"type": type_, "args": {"building": building}, "end": "refused", "why": why}


def test_the_refusals_by_why_and_the_refusal_carried_into_the_next_view():
    loot9 = {"type": "LootBuilding", "building": 9}
    rows = [row(error="invalid: refused", answer=json.dumps(loot9)),
            row({"type": "Rest", "seconds": 5}, p=prompt([bld(1, 1.0)], last_goal=refused("refused"))),   # carried
            row(error="invalid: out of range", answer="{}"),
            row({"type": "Rest", "seconds": 5}, p=prompt([bld(1, 1.0)])),                                  # not carried
            row(error="invalid: looted already", answer="{}"),
            row({"type": "Rest", "seconds": 5}, p=prompt([bld(1, 1.0)], last_goal=refused("refused"))),    # wrong why
            row(error="invalid: in the woods", answer="{}"),
            row(error="invalid: seconds must be 1 to 60", answer="{}"),                                     # not a rule's
            row(error="invalid: refused", answer="{}")]                                                    # the last row
    r = g5(rows)["refusals"]
    assert r["read"] is True
    assert r["by_why"] == {"done": 0, "stuck": 0, "superseded by the threat": 0, "superseded by an instinct": 0,
                           "looted already": 1, "refused": 2, "out of range": 1, "in the woods": 1, "failed": 0}
    assert r["invalid_other"] == 1
    assert (r["carried"], r["not_carried"], r["unchecked"]) == (1, 3, 1)
    z = g5([row({"type": "Rest", "seconds": 5})])["refusals"]
    assert z["by_why"]["refused"] == 0 and (z["carried"], z["not_carried"], z["unchecked"]) == (0, 0, 0)


# ================================================================ (d) the latencies and the failures
def test_the_latencies_of_the_answered_calls_and_the_failure_counts():
    rows = [row({"type": "Rest", "seconds": 5}, latency=2.0), row(error="invalid: refused", latency=6.0),
            row(error="timeout", latency=20.0), row(error="cli error", latency=3.0), row(error="malformed", latency=1.0),
            row(error="exit 1", latency=0.5), row(error="spawn: OSError: x", latency=0.1)]
    t = g5(rows)["latency"]
    assert t["calls"] == 7 and t["timeouts"] == 1 and t["cli_error"] == 1 and t["malformed"] == 1
    assert t["answered"] == 4 and t["max"] == 6.0 and t["mean"] == pytest.approx(3.0)
    z = g5([row(error="timeout", latency=20.0)])["latency"]
    assert z["answered"] == 0 and z["mean"] is None and z["max"] is None and z["timeouts"] == 1


# ================================================================ (f) the fallback's share
def test_the_fallbacks_share_of_the_goals():
    rows = [row({"type": "Rest", "seconds": 5}), row(error="timeout", latency=20.0)]
    f = g5(rows, [gl("Rest"), gl("ExploreToward", "scripted"), gl("Rest", "scripted"), gl("Rest", "scripted")])["fallback"]
    assert (f["goals"], f["scripted"], f["llm"]) == (4, 3, 1) and f["share"] == pytest.approx(0.75)
    assert f["calls"] == 2 and f["calls_fallbacks"] == 1
    z = g5([], [])["fallback"]
    assert z["share"] is None and z["goals"] == 0


# ================================================================ the report lines
def test_the_report_lines_name_each_reading_and_mark_it_reading_or_inference():
    loot = {"type": "LootBuilding", "building": 1, "want": "weapon"}
    rows = [row(loot, p=prompt([bld(1, 2.0, z=0)])), row({"type": "Shelter", "building": 1}, p=prompt([bld(1, 2.0)], night=True)),
            row(error="invalid: looted already", answer="{}"), row(error="timeout", latency=20.0)]
    lines = g5(rows, [gl("LootBuilding"), gl("Rest", "scripted")])["report_lines"]
    keys = ("answers (", "shelter (", "loot z (", "nearest (", "loop (", "refusals (", "latency (", "fallback (")
    for k in keys:
        hit = [l for l in lines if l.startswith(k)]
        assert len(hit) == 1 and ("[reading" in hit[0] or "[inference" in hit[0]), k
    assert any(l.startswith("llm:") for l in lines) and any(l.startswith("pull (P24-AN)") for l in lines)
    h = [l for l in lines if l.startswith("shelter (")][0]
    assert "inference" in h and "1 with tired or night true" in h
    assert "weapon 1" in [l for l in lines if l.startswith("answers (")][0]
    assert "timeouts 1" in [l for l in lines if l.startswith("latency (")][0]
    assert "looted already 1" in [l for l in lines if l.startswith("loop (")][0]


# ================================================================ the command line
def test_the_command_line_prints_the_report_then_the_grade_as_strict_json(tmp_path):
    rows = [row({"type": "Rest", "seconds": 5}), row(error="timeout", latency=20.0)]
    a = art(rows, [gl("Rest")])
    p = tmp_path / "f_goals_4.json"
    p.write_text(json.dumps(a), encoding="utf-8")
    (tmp_path / "goals.log").write_text("\n".join(json.dumps(r) for r in rows) + "\nnot json\n", encoding="utf-8")
    script = os.path.join(os.path.dirname(F.__file__), "..", "drivers", "f_grade_5.py")
    cwd = os.path.dirname(os.path.dirname(HERE))
    r = subprocess.run([sys.executable, script, str(p)], capture_output=True, text=True, cwd=cwd)
    assert r.returncode == 0, r.stderr
    g = json.loads(r.stdout[r.stdout.index("\n{\n"):])
    assert g["grade"] == "grade_f5" and g["answers"]["read"] is True and g["latency"]["timeouts"] == 1
    assert any(l.startswith("latency (") for l in r.stdout.splitlines())
    for args in ([], ["a", "b"], [str(tmp_path / "nope.json")]):
        assert subprocess.run([sys.executable, script] + args, capture_output=True, text=True,
                              cwd=cwd).returncode == 2
    assert FG.load_goals(str(tmp_path / "gone" / "x.json")) is None
    assert len(FG.load_goals(str(p))) == 2
    assert FG.finite(float("inf")) is None


F2 = os.path.join(os.path.dirname(os.path.dirname(HERE)), "artifacts", "f_goals_2-20261029-041705", "f_goals_2.json")


@pytest.mark.skipif(not os.path.isfile(F2), reason="the F2 artifact is not in this tree")
def test_grade_f5_reads_the_committed_f2_artifact_and_leaves_grade_f4_as_it_was():
    out = json.load(open(F2, encoding="utf-8"))
    rows = FG.load_goals(F2)
    g4, g5_ = F.grade_f4(out), F.grade_f5(out, goal_lines=rows)
    assert g4["grade"] == "grade_f4" and g5_["grade"] == "grade_f5" and g5_["llm"] == g4["llm"]
    assert g5_["latency"]["calls"] == g4["llm"]["calls"] == len(rows) == 22
    assert g5_["refusals"]["by_why"]["refused"] >= 1                   # F2's first answer named a building not shown
    assert g5_["fallback"]["calls_fallbacks"] == g4["llm"]["fallbacks"] == 4
    json.dumps(g5_, allow_nan=False, default=lambda o: None)
