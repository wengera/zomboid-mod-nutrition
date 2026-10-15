"""Offline tests of testing/experiments/x433_regrade.py (Plan 13 Task 21's regrade): R1 reads an empty trait list
answered as {} as the empty list, and the regrade still fails a held band or a missing read."""
import copy
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "experiments"))
sys.path.insert(0, HERE)

import x433_regrade as R             # noqa: E402
import x43_strength_lib as L          # noqa: E402


def doc(server_tl, client_tl):
    e = L.expect_body([], 0)
    body = {k: e[k] for k in ("lm", "fm", "F0", "Fc", "Pk", "N0")}
    body["lx"] = 0.0
    mass = e["lm"] + e["fm"]
    pair = {"server_stats": {"weight": mass, "traitList": server_tl},
            "client_stats": {"weight": mass, "traitList": client_tl},
            "server_xp": {"level": 5}, "client_xp": {"level": 5}, "gap_s": 0.5}
    checks = {f"C{lab}": {} for lab, _p in L.CASES}
    checks["Ca"] = {"landed": True, "expect": e, "body": body, "pair": pair, "want_stripped": []}
    verdicts = {f"21_{lab}_{k}": {"verdict": "as_predicted"} for lab, _p in L.CASES for k in ("body", "state", "strips")}
    verdicts["21_a_state"] = {"verdict": "unmeasured"}
    return {"checks": checks, "verdicts": verdicts}


def test_r1_reads_the_empty_list():
    out = R.regrade(doc({}, {}))
    assert out["verdicts"]["21_a_state"]["verdict"] == "as_predicted"
    assert out["verdicts"]["21_a_state"]["run_verdict"] == "unmeasured"
    assert out["verdicts"]["21_b_body"]["verdict"] == "as_predicted" and out["verdicts"]["21_b_body"]["copied"]


def test_r1_still_fails_a_held_band_and_an_unread_list():
    assert R.regrade(doc({}, ["stout"]))["verdicts"]["21_a_state"]["verdict"] == "falsified"
    assert R.regrade(doc({}, None))["verdicts"]["21_a_state"]["verdict"] == "unmeasured"


def test_r1_leaves_the_source_untouched():
    d = doc({}, {})
    before = copy.deepcopy(d)
    R.regrade(d)
    assert d == before
