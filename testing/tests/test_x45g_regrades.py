"""Offline tests of the Task 11 regrades (x455_regrade.py, x45g_onset_regrade.py): each grade with a failing and an
unmeasured case, and each script's run on its committed inputs."""
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "experiments"))

import x455_regrade as R5        # noqa: E402
import x45g_onset_regrade as RO  # noqa: E402


def test_grade_sb():
    red = 0.0165
    pred = R5.WOUND_X451 + red * R5.M_H + R5.STARVE_GH
    assert R5.grade_sb(pred, red, [4, 4], [0.0, 0.0])[0] == "as_predicted"
    assert R5.grade_sb(pred * 1.3, red, [4, 4], [0.0, 0.0])[0] == "falsified"
    assert R5.grade_sb(pred - red * R5.M_H, red, [4, 4], [0.0, 0.0])[0] == "falsified"   # no BLEEDING-4 term
    assert R5.grade_sb(pred, red, [4, 4], [0.0165, 0.0])[0] == "falsified"
    assert R5.grade_sb(pred, red, [3, 4], [0.0, 0.0])[0] == "unmeasured"
    assert R5.grade_sb(None, red, [4, 4], [0.0, 0.0])[0] == "unmeasured"


def test_x455_regrade_on_its_artifact():
    with tempfile.TemporaryDirectory() as d:
        res = R5.main(["--out", d])
    v = res["verdicts"]["SB_ABS"]
    assert v["verdict"] == "as_predicted" and abs(v["observed"]["predicted_per_gh"] - 36.705) < 0.001
    assert res["readings"]["N"]["well_fed"] is True


def _rows(onset_at=30.0, pre_h=0.69, on_h=1.0):
    rows = []
    for i in range(30):
        age = 10.0 + i / 60.0
        s = 29.75 + (i - 1) / 60.0              # the record's clock: one row behind the row's age
        rows.append({"s": i, "age": age, "drain.fedAgeH": age - (29.75 + i / 60.0) + 0.0, "drain.starvedH": s,
                     "drain.starveAcute": s >= onset_at, "HUNGER": on_h if s >= onset_at else pre_h})
    return rows


def test_grade_onset_record():
    assert RO.grade_onset_record(_rows(), 9.99)[0] == "as_predicted"
    assert RO.grade_onset_record(_rows(onset_at=30.1), 9.99)[0] == "falsified"
    assert RO.grade_onset_record(_rows(on_h=0.69), 9.99)[0] == "falsified"
    assert RO.grade_onset_record(_rows(pre_h=0.75), 9.99)[0] == "falsified"
    assert RO.grade_onset_record(_rows(onset_at=99), 9.99)[0] == "unmeasured"


def test_lag_identity():
    rows = [{"s": i, "age": 10.0 + i / 60.0, "drain.fedAgeH": -20.0, "drain.starvedH": 10.0 + (i - 1) / 60.0 + 20.0,
             "drain.starveAcute": False} for i in range(10)]
    rows.append({"s": 10, "age": 10.2, "drain.fedAgeH": 10.2, "drain.starvedH": 0.0, "drain.starveAcute": True})
    assert RO.lag_identity(rows, 9.99)["max_abs_diff_h"] < 1e-9
    rows[5]["drain.starvedH"] += 0.01
    assert abs(RO.lag_identity(rows, 9.99)["max_abs_diff_h"] - 0.01) < 1e-9


def test_onset_regrade_on_its_artifacts():
    with tempfile.TemporaryDirectory() as d:
        res = RO.main(["--out", d])
    for k in ("x454", "x455"):
        r = res["runs"][k]
        assert r["verdict"] == "as_predicted" and r["lag_identity"]["max_abs_diff_h"] < 1e-6
