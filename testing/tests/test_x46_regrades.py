"""Offline tests of Plan 16 Task 9's regrades (x461_regrade.py, x463a_regrade.py): each grade with a failing and an
unmeasured case, and each script's run on its committed inputs."""
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "experiments"))

import x461_regrade as R1        # noqa: E402
import x463a_regrade as R3       # noqa: E402


def _rows(n, cold=1.003):
    return [{"s": i + 1, "on": True, "cold": cold + 1e-5 * i} for i in range(n)]


def test_grade_cold_fed():
    import replay_live as RL
    rows = _rows(6)
    derived = RL.ring_cold_events(rows)
    assert R1.grade_cold_fed(rows, derived, derived)[0] == "as_predicted"
    assert R1.grade_cold_fed(rows, derived[2:], derived)[0] == "as_predicted"       # a later start: a subset
    assert R1.grade_cold_fed(rows, [], derived)[0] == "falsified"                    # nothing fed
    bad = [dict(derived[0], cold=1.5)]
    assert R1.grade_cold_fed(rows, bad, derived)[0] == "falsified"                   # a feed the ring does not give
    holes = rows[:3] + [{"s": 4, "on": True}] + rows[4:]
    assert R1.grade_cold_fed(holes, derived, derived)[0] == "falsified"              # a row without cold
    assert R1.grade_cold_fed(rows, None, derived)[0] == "unmeasured"
    assert R1.grade_cold_fed([], derived, derived)[0] == "unmeasured"
    off = rows + [{"s": 7, "on": False}]
    assert R1.grade_cold_fed(off, derived, derived)[0] == "as_predicted"             # offline rows are not read


def test_admitted_and_grade_written():
    assert R3.admitted(0.158252, 0.157975, 0.157975)
    assert R3.admitted(0.158252, 0.157975, 0.157716)                                 # one minute later
    assert not R3.admitted(0.158252, 0.157975, 0.157400)                             # two minutes later
    assert not R3.admitted(0.158252, 0.157975, 0.158500)                             # the wrong way
    assert R3.admitted(0.0, 0.0, 0.0) and not R3.admitted(0.0, 0.0, 0.01)
    assert not R3.admitted(None, 0.0, 0.0)
    pre = [{"on": True, "HUNGER": 0, "THIRST": 0, "FATIGUE": 0.158252},
           {"on": True, "HUNGER": 0, "THIRST": 0, "FATIGUE": 0.157975}]
    assert R3.grade_written(pre, {"s": 5, "HUNGER": 0, "THIRST": 0, "FATIGUE": 0.157716})[0] == "as_predicted"
    assert R3.grade_written(pre, {"s": 5, "HUNGER": 0.01, "THIRST": 0, "FATIGUE": 0.157716})[0] == "falsified"
    assert R3.grade_written(pre, {"s": 5, "HUNGER": 0, "THIRST": 0, "FATIGUE": 0.1570})[0] == "falsified"
    assert R3.grade_written(pre[:1], {"s": 5, "HUNGER": 0, "THIRST": 0, "FATIGUE": 0.157716})[0] == "unmeasured"
    assert R3.grade_written(pre, None)[0] == "unmeasured"


def test_x461_regrade_on_its_artifacts():
    with tempfile.TemporaryDirectory() as d:
        res = R1.main(["--out", d])
    for k in ("x461a.COLD_FED_RG", "x461b.COLD_FED_RG"):
        v = res["verdicts"][k]
        assert v["verdict"] == "as_predicted" and v["observed"]["frozen_verdict"] == "falsified"
        assert v["observed"]["rows_with_cold"] == v["observed"]["rows"] and v["observed"]["recorded_events"] > 0


def test_x463a_regrade_on_its_artifact():
    with tempfile.TemporaryDirectory() as d:
        res = R3.main(["--out", d])
    v = res["verdicts"]["WRITTEN_RG"]
    assert v["verdict"] == "as_predicted" and v["observed"]["frozen_verdict"] == "falsified"
    assert v["observed"]["per_stat"]["FATIGUE"]["admitted"] is True


def test_x467_cold_ablation_grade():
    import x467_cold_ablation as A
    rows = [{"s": 1}, {"s": 2, "fluids.autoDrop": 0.12}, {"s": 3, "fluids.autoDrop": 0}, {"s": 4},
            {"s": 5, "fluids.autoDrop": 0.2}]
    auto = A.autodrink_rows(rows)
    assert auto == [1, 4]
    off = list(range(100, 100 + A.MIN_OFF_GAP + 2))
    assert A.grade([1, 4], off, auto, 1000)[0] == "as_predicted"
    assert A.grade([1, 4, 77], off, auto, 1000)[0] == "falsified"                 # a cold-fed miss off an auto-drink
    assert A.grade([1, 4], off[:10], auto, 1000)[0] == "falsified"                # the cold changed nothing
    assert A.grade([], [], auto, 0)[0] == "unmeasured"
    assert A.over_rows({"findings": [{"field": "THIRST", "s": 9}, {"field": "HUNGER", "s": 3},
                                     {"field": "THIRST", "n": 0, "why": "x"}]}) == [9]


def test_x467_cold_ablation_on_its_artifact():
    import x467_cold_ablation as A
    with tempfile.TemporaryDirectory() as d:
        res = A.main(["--out", d])
    o = res["verdicts"]["COLD_DISCRIMINATES"]["observed"]
    assert res["verdicts"]["COLD_DISCRIMINATES"]["verdict"] == "as_predicted"
    assert o["on_over"] == 2 and o["off_over"] > 300
