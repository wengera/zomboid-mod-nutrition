"""Offline tests of testing/experiments/x436_regrade.py (Plan 13 Task 22b's names regrade): N1 grades only the mod's
three display names, passes on vanilla's own Obese label, and still fails a vanilla or missing label of a renamed trait."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "experiments"))

import x436_regrade as R             # noqa: E402

WANT = {"underweight": "Overly Lean", "veryunderweight": "Gaunt", "overweight": "Overfat"}


def doc(labels):
    return {"checks": {"S": {"labels": labels, "want_names": dict(WANT)}},
            "verdicts": {"36_names": {"verdict": "falsified"}}}


def test_n1_grades_the_mods_three_names_only():
    out = R.regrade(doc(dict(WANT, obese="Very High Weight")))
    v = out["verdicts"]["36_names_mod"]
    assert v["verdict"] == "as_predicted" and v["run_verdict_36_names"] == "falsified"
    assert v["observed"]["obese_reported"] == "Very High Weight"


def test_n1_fails_a_vanilla_label_and_reads_a_missing_one_unmeasured():
    assert R.regrade(doc(dict(WANT, underweight="Underweight")))["verdicts"]["36_names_mod"]["verdict"] == "falsified"
    assert R.regrade(doc(dict(WANT, overweight="Overweight")))["verdicts"]["36_names_mod"]["verdict"] == "falsified"
    assert R.regrade(doc(dict(WANT, veryunderweight=None)))["verdicts"]["36_names_mod"]["verdict"] == "unmeasured"


def test_the_run_artifact_reads_the_staged_names():
    import json
    with open(R.SRC, encoding="utf-8") as fh:
        d = json.load(fh)
    assert d["checks"]["S"]["want_names"] == WANT
