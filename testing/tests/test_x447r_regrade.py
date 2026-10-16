"""Offline tests of testing/experiments/x447r_regrade.py (Plan 14 Task 6's M2 regrade): a regrade that drops, adds or
mis-sizes a live-drunk drink fails INPUTS and grades nothing; a drink with no sip row is unrecorded; a grade on zero
compared rows is unmeasured, never a pass; the real artifact's six live drinks all reach the events."""
import copy
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "experiments"))

import pytest                         # noqa: E402

import x447r_regrade as R              # noqa: E402

SIPS = R.L.SIPS_G


def ring(sips):
    """Rows s=1.. at ages 1.0, 1.1, ... with the sips counter given per row."""
    return [{"s": i + 1, "age": 1.0 + 0.1 * i, SIPS: v} for i, v in enumerate(sips)]


def drink(label, a0, a1, drunk, fluid="Beer"):
    return {"label": label, "age0": a0, "age1": a1, "drunk": drunk, "fluid": fluid}


def ev(label, litres, s=2):
    return {"s": s, "kind": "drink", "fluid": "Beer", "litres": litres, "label": label}


# ---------------------------------------------------------------- INPUTS
def test_inputs_pass_when_every_live_drink_is_in_the_events():
    rows = ring([0, 2, 2, 5, 5])
    ds = [drink("a", 1.05, 1.15, 0.3), drink("b", 1.25, 1.35, 0.3), drink("c", 1.0, 1.4, 0.0)]
    v, o = R.check_inputs(rows, ds, [ev("a", 0.3), ev("b", 0.1), ev("b", 0.2)])
    assert v == "as_predicted", o


def test_a_dropped_drink_fails_inputs():
    rows = ring([0, 2, 2, 5, 5])
    ds = [drink("a", 1.05, 1.15, 0.3), drink("b", 1.25, 1.35, 0.3)]
    v, o = R.check_inputs(rows, ds, [ev("a", 0.3)])
    assert v == "falsified" and o["missing"] == ["b"]


def test_an_extra_or_mis_sized_drink_fails_inputs():
    rows = ring([0, 2, 2, 5, 5])
    ds = [drink("a", 1.05, 1.15, 0.3), drink("b", 1.25, 1.35, 0.3), drink("c", 1.0, 1.4, 0.0)]
    v, o = R.check_inputs(rows, ds, [ev("a", 0.3), ev("b", 0.3), ev("c", 0.1)])
    assert v == "falsified" and o["extra"] == ["c"]
    v, o = R.check_inputs(rows, ds, [ev("a", 0.3), ev("b", 0.25)])
    assert v == "falsified" and o["litres_off"] == ["b"]


def test_a_live_drink_with_no_sip_row_is_unrecorded():
    rows = ring([0, 2, 2, 2, 2])
    ds = [drink("a", 1.05, 1.15, 0.3), drink("b", 1.25, 1.35, 0.3)]
    v, o = R.check_inputs(rows, ds, [ev("a", 0.3), ev("b", 0.3)])
    assert v == "unmeasured" and o["unrecorded"] == ["b"]


def test_no_live_drink_is_unmeasured():
    v, _ = R.check_inputs(ring([0, 0]), [drink("a", 1.0, 1.1, 0.0)], [])
    assert v == "unmeasured"


# ---------------------------------------------------------------- the field grades
def test_field_grades_are_unmeasured_unless_inputs_pass():
    diff = {"fields": {f: {"n": 10, "max": 0.0, "over": 0} for f in R.tolerances()}}
    hang = [{"age": 2.0, "acute.hang": 1}]
    out = R.grade_fields(diff, hang, hang, "falsified")
    assert out and all(x["verdict"] == "unmeasured" for x in out.values())
    out = R.grade_fields(diff, hang, hang, "as_predicted")
    assert all(x["verdict"] == "as_predicted" for x in out.values())


def test_a_grade_on_zero_samples_is_unmeasured():
    diff = {"fields": {f: {"n": 0, "max": None, "over": 0} for f in R.tolerances()}}
    out = R.grade_fields(diff, [], [], "as_predicted")
    assert all(x["verdict"] == "unmeasured" for x in out.values()), out
    out = R.grade_fields({}, [], [], "as_predicted")
    assert all(x["verdict"] == "unmeasured" for x in out.values())


def test_a_field_over_its_tolerance_and_a_one_sided_hangover_fail():
    diff = {"fields": {f: {"n": 10, "max": 9.0, "over": 3} for f in R.tolerances()}}
    out = R.grade_fields(diff, [{"age": 2.0, "acute.hang": 1}], [{"age": 2.0, "acute.hang": 0}], "as_predicted")
    assert all(x["verdict"] == "falsified" for x in out.values())


# ---------------------------------------------------------------- the real artifact (no replay run)
@pytest.fixture(scope="module")
def inp():
    if not os.path.isdir(R.SRC_DIR):
        pytest.skip("x447's artifact folder is absent")
    return R.load()


def test_the_artifact_has_six_live_drinks_each_with_its_own_sip_rows(inp):
    ds = inp["d"]["drinks"]
    live = R.landed(ds)
    assert [x["label"] for x in live] == ["X_coffee1", "X_coffee3", "X_beer1", "X_beer2", "X_beer3", "X_beer4"]
    seen = set()
    for x in live:
        s = [r["s"] for r in R.sip_rows(inp["rows"], x)]
        assert s and not (seen & set(s))
        seen |= set(s)


def test_the_regrade_events_carry_all_six_and_the_runs_carried_one(inp):
    drinks, events, _ = R.build(inp, R.landed)
    assert R.check_inputs(inp["rows"], drinks, events)[0] == "as_predicted"
    drinks, events, _ = R.build(inp, R.gate_passed)
    v, o = R.check_inputs(inp["rows"], drinks, events)
    assert v == "falsified" and len(o["missing"]) == 5


def test_a_regrade_that_drops_a_drink_fails_and_grades_nothing(inp):
    def drop_beer2(ds):
        return [x for x in R.landed(ds) if x["label"] != "X_beer2"]
    out = R.regrade(copy.deepcopy(inp), select=drop_beer2, rep=False)
    assert out["summary"]["INPUTS"] == "falsified"
    assert out["verdicts"]["INPUTS"]["observed"]["missing"] == ["X_beer2"]
    assert all(v == "unmeasured" for k, v in out["summary"].items() if k.startswith("M2r_"))


def test_the_run_events_rebuild_from_the_gate_rule(inp):
    _, ev_run, _ = R.build(inp, R.gate_passed)
    assert R.norm(ev_run) == R.norm(inp["events_run"])


# ---------------------------------------------------------------- REP's failing cases (the review's F7)
def test_rep_fails_when_an_event_is_dropped_from_the_runs_events(inp):
    bad = copy.deepcopy(inp)
    bad["events_run"] = bad["events_run"][1:]
    v, o = R.reproduce(bad)
    assert v == "falsified" and o["events_equal"] is False


def test_rep_fails_on_a_perturbed_run_field_stat(inp):
    bad = copy.deepcopy(inp)
    bad["d"]["replay"]["fields"]["HUNGER"]["max"] += 0.01
    v, o = R.reproduce(bad)
    assert v == "falsified" and o["events_equal"] is True and "rebuilt_fields" in o


def test_rep_is_unmeasured_without_run_fields(inp):
    bad = copy.deepcopy(inp)
    bad["d"]["replay"] = {}
    v, o = R.reproduce(bad)
    assert v == "unmeasured" and o["events_equal"] is True
