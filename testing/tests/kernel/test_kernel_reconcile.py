"""The reconcile kernel (NR_Kernel_Reconcile.lua, K.reconcile; Plan 8 Task 3, ruling 6).

The missed-intake delta: the vanilla macro stores minus the baseline on the four macros; a calorie rise above
RECONCILE_EPS is an intake landing as the four macros only (every other vector key 0) with the note; a fall,
no change or a rise inside the tolerance lands nothing; baselineAfter is a copy of the four values.
"""
import math

MACROS = ["calories", "carbs", "lipids", "proteins"]


def R(h):
    return h.K.reconcile


def test_the_eps_and_the_note(host):
    assert R(host).RECONCILE_EPS == 0.5
    assert R(host).NOTE == "reconciled: macros only, nutrient vector unknown"


def test_delta_is_store_minus_baseline_on_the_four_macros(host):
    store = host.table({"calories": 1200.0, "carbs": 80.0, "lipids": 30.0, "proteins": 10.0, "fibre": 9})
    base = host.table({"calories": 1000.0, "carbs": 50.0, "lipids": 32.0, "proteins": 10.0})
    assert host.py(R(host).delta(store, base)) == {"calories": 200.0, "carbs": 30.0, "lipids": -2.0, "proteins": 0.0}


def test_delta_reads_a_nil_table_or_value_as_zero(host):
    store = host.table({"calories": 100.0, "carbs": "x"})
    assert host.py(R(host).delta(store, None)) == {"calories": 100.0, "carbs": 0, "lipids": 0, "proteins": 0}
    assert host.py(R(host).delta(None, host.table({"lipids": 4}))) == {"calories": 0, "carbs": 0, "lipids": -4,
                                                                        "proteins": 0}


def test_intake_lands_the_four_macros_only_with_the_note(host):
    d = host.table({"calories": 105.11, "carbs": 26.97, "lipids": 0.39, "proteins": 1.29})
    vec, note = R(host).intake(d, None)
    v = host.py(vec)
    assert note == "reconciled: macros only, nutrient vector unknown"
    assert {k: v[k] for k in MACROS} == {"calories": 105.11, "carbs": 26.97, "lipids": 0.39, "proteins": 1.29}
    assert set(v) == set(host.py(host.call("vector.new")))
    assert all(v[k] == 0 for k in v if k not in MACROS)


def test_a_macro_fall_beside_a_calorie_rise_lands_zero(host):
    d = host.table({"calories": 50.0, "carbs": -10.0, "lipids": 4.0, "proteins": 0.0})
    v = host.py(R(host).intake(d, 5)[0])
    assert (v["calories"], v["carbs"], v["lipids"], v["proteins"]) == (50.0, 0, 4.0, 0)


def test_no_intake_at_or_below_the_tolerance_or_on_a_fall(host):
    for cal in (5.0, 4.99, 0.0, -300.0):
        assert R(host).intake(host.table({"calories": cal, "carbs": 10}), 5) is None, cal
    assert R(host).intake(host.table({"calories": 0.5}), None) is None          # eps nil reads RECONCILE_EPS
    assert R(host).intake(host.table({"calories": 0.4}), None) is None
    assert R(host).intake(host.table({"calories": 0.6}), None) is not None      # a 0.6 kcal rise lands
    assert R(host).intake(host.table({"calories": 0.99}), None) is not None     # RedRadish, the smallest item-pass food
    assert R(host).intake(host.table({"calories": 30.0}), 50) is None          # an explicit eps wins
    assert R(host).intake(None, 5) is None


def test_a_nan_lands_nothing(host):
    nan = float("nan")
    assert R(host).intake(host.table({"calories": nan}), 5) is None
    v = host.py(R(host).intake(host.table({"calories": 20.0, "carbs": nan}), 5)[0])
    assert v["carbs"] == 0 and not math.isnan(v["carbs"])


def test_baseline_after_is_a_copy_of_the_four_values(host):
    store = host.table({"calories": 1500.0, "carbs": 12.5, "lipids": -3.0, "fibre": 4})
    b = R(host).baselineAfter(store)
    assert host.py(b) == {"calories": 1500.0, "carbs": 12.5, "lipids": -3.0, "proteins": 0}
    store["calories"] = 0
    assert b["calories"] == 1500.0
    assert host.py(R(host).baselineAfter(None)) == {"calories": 0, "carbs": 0, "lipids": 0, "proteins": 0}


def test_a_landing_then_its_baseline_leaves_no_second_delta(host):
    base = host.table({"calories": 800.0, "carbs": 40.0, "lipids": 20.0, "proteins": 30.0})
    store = host.table({"calories": 1050.0, "carbs": 70.0, "lipids": 25.0, "proteins": 35.0})
    assert R(host).intake(R(host).delta(store, base), None) is not None
    base = R(host).baselineAfter(store)
    assert R(host).intake(R(host).delta(store, base), None) is None
