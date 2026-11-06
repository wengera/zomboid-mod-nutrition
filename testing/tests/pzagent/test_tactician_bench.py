"""The tactician's offline bench (`tools/tactician_bench.py`; Plan 31 Task 11, T, the amendments' item 2): the view
choice, the call plan and its budget, the stop at the first limit, the scores and the verdict, on fixed views and a
fake runner (no test makes a real `claude` call), and the committed recording's own invariants."""
import json
import os
import sys

import pytest

from agent.base.planner.tactician import table as T

from .test_tactician import BUILDING, DOOR, Proc, bleeding_part, envelope, mkview, zrow

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, os.path.join(REPO, "tools"))
import tactician_bench as B  # noqa: E402

README = os.path.join(REPO, "testing", "agent", "base", "planner", "tactician", "README.md")


def fixed_views():
    """Ten views over two rings: four lone chasers, two bleeds, two groups, two quiet."""
    vs = ([mkview([zrow("Z1", 4.0)]) for _ in range(4)]
          + [mkview(parts=[bleeding_part()], kit={"bandages": 1}) for _ in range(2)]
          + [mkview([zrow("Z%d" % k, 3.0 + k) for k in (1, 2, 3)], doors=[DOOR]) for _ in range(2)]
          + [mkview(buildings=[BUILDING]) for _ in range(2)])
    out = []
    for i, v in enumerate(vs):
        ring = B.RINGS[i % 2]
        out.append(({"id": "v%d" % i, "ring": ring, "frame": i, "wall": float(i), "trigger": ["notice"], "cls": "c",
                     "sha": B.sha(v)}, v, "kite" if i < 4 else None))
    return out


def calls_from(views, answer_of, configs=B.CONFIGS, latency=3.0):
    return [{"config": cfg, "view": rec["id"], "k": 0, "answer": answer_of(cfg, rec, v), "text": None,
             "latency_s": latency, "error": None, "limited": False, "returncode": 0} for rec, v, _ in views
            for cfg in configs]


def doctrine_like(cfg, rec, v):
    return B.F.doctrine(v)[1]


def test_the_choice_is_round_robin_over_the_classes_and_deterministic():
    pts = [{"ring": B.RINGS[0], "frame": i, "cls": "a" if i < 90 else "b", "wall": 0.0, "triggers": []}
           for i in range(100)]
    got = B.choose(pts, 20)
    assert len(got) == 20 and sum(p["cls"] == "b" for p in got) == 10   # the rare class gets its full share
    assert got == B.choose(list(reversed(pts)), 20) or [p["frame"] for p in got] == sorted(p["frame"] for p in got)
    assert len(B.choose(pts, 200)) == 100                              # never more than there are


def test_the_call_plan_interleaves_the_configurations_and_fits_the_budget():
    views = [({"id": "v%d" % i}, None, None) for i in range(B.VIEWS_N)]
    plan = B.plan_calls(views, [])
    assert len(plan) == B.CALL_BUDGET == 2 * B.VIEWS_N + B.SELF_N * (B.SELF_K - 1)
    assert plan[:4] == [("haiku", "v0", 0), ("sonnet", "v0", 0), ("haiku", "v1", 0), ("sonnet", "v1", 0)]
    assert all(c[0] == B.REFERENCE and c[2] > 0 for c in plan[2 * B.VIEWS_N:])
    done = [{"config": "haiku", "view": "v0", "k": 0}]
    assert B.plan_calls(views, done)[0] == ("sonnet", "v0", 0)        # a resumed run never asks again


def test_record_stops_at_the_first_exit_and_resumes_without_asking_again(tmp_path):
    views = fixed_views()
    n = {"calls": 0}

    def runner(argv, prompt, timeout, env):
        n["calls"] += 1
        if n["calls"] == 3:
            return Proc("", rc=1, err="rate limited")
        return Proc(envelope({"play": "fight", "target": "Z1", "bound": "dead", "why": "lone_chaser"}))
    path = str(tmp_path / "rec.json")
    rec = B.record(runner=runner, path=path, log=lambda *a: None, views=views)
    assert n["calls"] == 3 and len(rec["calls"]) == 3 and rec["calls"][-1]["limited"] is True
    rec2 = B.record(max_calls=2, runner=lambda *a: Proc(envelope({"play": "fight"})), path=path,
                    log=lambda *a: None, views=views)
    assert len(rec2["calls"]) == 5 and [c["view"] for c in rec2["calls"][3:]] == ["v1", "v2"]


def test_record_refuses_a_recording_whose_views_differ(tmp_path):
    views = fixed_views()
    path = str(tmp_path / "rec.json")
    B.save({"views": [dict(views[0][0], sha="0" * 64)], "calls": []}, path)
    with pytest.raises(SystemExit):
        B.record(dry=True, path=path, log=lambda *a: None, views=views)


def test_a_model_answering_as_the_doctrine_is_tied_by_the_table_and_scored_with_no_violation():
    views = fixed_views()
    rec = {"views": [v for v, _, _ in views], "calls": calls_from(views, doctrine_like)}
    sc = B.score(rec, views)
    ch = sc["choosers"]
    assert ch["sonnet"]["valid_share"] == 1.0 and ch["sonnet"]["violations_total"] == 0
    assert ch["doctrine"]["agree_type_sonnet"] == 1.0 and ch["table"]["agree_type_sonnet"] == 1.0
    assert sc["verdict"]["tie"] is True and "ties the model" in sc["verdict"]["text"]
    assert ch["sonnet"]["latency_p50"] == 3.0 and ch["ladder"]["violations"]["lone_not_fight"] == 4


def test_a_model_that_flees_the_lone_chaser_breaks_the_rubric_and_the_table_never_learns_it():
    views = fixed_views()

    def kites(cfg, rec, v):
        if v["zombies"] and len(v["zombies"]) == 1:
            return {"play": "kite", "target": "Z1", "toward": "stance", "bound": "time", "why": "lone_chaser"}
        return B.F.doctrine(v)[1]
    rec = {"views": [v for v, _, _ in views], "calls": calls_from(views, kites)}
    sc = B.score(rec, views)
    ch = sc["choosers"]
    assert ch["sonnet"]["violations"]["lone_not_fight"] == 4
    assert ch["table"]["violations_total"] == ch["table_in"]["violations_total"] == 0   # the rule binds: the doctrine
    assert ch["table_in"]["agree_type_sonnet"] == 0.6                  # the four lone views are the doctrine's
    assert sc["verdict"]["tie"] is False


def test_an_invalid_answer_counts_against_validity_and_reads_as_no_play():
    views = fixed_views()
    rec = {"views": [v for v, _, _ in views],
           "calls": calls_from(views, lambda cfg, r, v: {"play": "fight", "target": "Z9", "bound": "dead",
                                                          "why": "lone_chaser"})}
    sc = B.score(rec, views)
    assert sc["choosers"]["sonnet"]["valid"] == 0 and sc["choosers"]["sonnet"]["refused"] == {"unknown_label": 10}
    assert sc["verdict"]["tie"] is None                                # no valid pair: no verdict


def test_the_self_agreement_reads_the_three_samples_of_each_view():
    views = fixed_views()
    calls = calls_from(views, doctrine_like)
    for k in (1, 2):
        calls.append({"config": "sonnet", "view": "v0", "k": k, "answer": doctrine_like("sonnet", None, views[0][1]),
                      "latency_s": 2.0, "error": None})
        calls.append({"config": "sonnet", "view": "v4", "k": k,
                      "answer": {"play": "fight", "target": "Z1", "bound": "dead", "why": "lone_chaser"},
                      "latency_s": 2.0, "error": None})
    sc = B.score({"views": [v for v, _, _ in views], "calls": calls}, views)
    assert sc["self_agreement"] == {"views": 2, "k": 3, "all_same_type": 0.5, "all_same_target": 0.5,
                                    "pairwise_type": 0.5, "first_two_type": 0.5}


def test_the_percentiles_are_nearest_rank():
    assert B._pct([1.0, 2.0, 3.0, 4.0], 0.5) == 2.0 and B._pct([1.0, 2.0, 3.0, 4.0], 0.99) == 4.0
    assert B._pct([], 0.5) is None


@pytest.fixture(scope="module")
def recording():
    rec = B.load()
    if rec is None:
        pytest.skip("no committed recording")
    return rec


def test_the_committed_recording_kept_its_budget_and_stopped_at_its_first_limit(recording):
    calls = recording["calls"]
    assert len(calls) <= B.CALL_BUDGET and len(recording["views"]) == B.VIEWS_N
    stops = [i for i, c in enumerate(calls) if c["limited"] or str(c["error"]).startswith(("exit", "spawn"))]
    assert not stops or stops[0] == len(calls) - 1
    keys = [(c["config"], c["view"], c["k"]) for c in calls]
    assert len(keys) == len(set(keys))


def test_the_committed_scores_name_the_verdict_the_readme_s_first_line_states(recording):
    sc = recording.get("scores")
    assert sc is not None and sc["calls"] == len(recording["calls"])
    with open(README, encoding="utf-8") as f:
        first = f.readline()
    assert ("ties the model" in first) == bool(sc["verdict"]["tie"])


def test_the_committed_table_is_the_bench_s_in_sample_fit(recording):
    t = T.Table.load()
    with open(T.TABLE_PATH, encoding="utf-8") as f:
        meta = json.load(f)
    assert meta["reference"] == B.REFERENCE and meta["verdict"] == recording["scores"]["verdict"]["text"]
    assert t.cells and set(t.cells.values()) <= set(B.P.PLAYS)


def test_check_is_read_only_and_fails_on_scores_or_a_table_that_moved(tmp_path):
    """Fix 1 (review-t11 L2): `check` re-reads the scores and the table and writes nothing."""
    views = fixed_views()
    rec = {"views": [v for v, _, _ in views], "calls": calls_from(views, doctrine_like)}
    rec["scores"] = B.score(rec, views)
    fitted = T.Table.fit([(v, B._valid(doctrine_like("sonnet", r, v), v)) for r, v, _ in views])
    before = json.dumps(rec, sort_keys=True)
    assert B.check(rec, views, log=lambda *a: None, table=fitted) == 0
    assert json.dumps(rec, sort_keys=True) == before
    assert B.check(rec, views, log=lambda *a: None, table=T.Table({"x": "fight"})) == 1
    rec["scores"]["choosers"]["sonnet"]["violations_total"] = 99
    assert B.check(rec, views, log=lambda *a: None, table=fitted) == 1
