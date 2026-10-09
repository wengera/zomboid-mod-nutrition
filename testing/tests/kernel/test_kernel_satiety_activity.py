"""The activity terms of the satiety model (Plan 11c Task 4b; spec § 5c; ruling 11c-29), as pure kernel functions:

- K.satiety.exerciseSuppression(S, dtH, vigorous, kind): the acute suppression state S in [0, 1]. It relaxes toward
  the kind's weight while vigorous (aerobic 1, resistance ACUTE_KIND.resistance, walking 0; an unknown kind 0) and
  toward 0 otherwise, first-order with the half-life ACUTE_HALF_LIFE_H. K.satiety.acuteFactor(S) = 1 - ACUTE_MAX x S
  is what the writer multiplies hunger by (Task 6 wires it).
- K.energy.exerciseLag(L, exKcal, dtH): L, the exercise expenditure rate (kcal per day) appetite has caught up with,
  a first-order lag of the exercise kcal with the time constant EX_LAG_TAU_D days. K.energy.lagged(L) reads it,
  non-negative and finite.
- K.energy.activityState(eb24h, ex24h, L, fatDep, g, ee24h): the energy state the writer hands to hungerTarget. The
  food balance (eb24h with the exercise kcal of the same window added back) enters at once; the exercise share enters
  only through the lag, which a 24 h total deficit bypasses on a linear ramp between EX_BYPASS_LO and EX_BYPASS_HI of
  the 24 h expenditure ee24h (ruling 11c-32 as amended). Its value is never below the state of the same intake without
  the activity.

The replays that fit the constants are test_satiety_activity.py.
"""
import math
import re
import os

import pytest

from .conftest import SHARED

LN2 = math.log(2)


def src(name):
    with open(os.path.join(SHARED, name), encoding="utf-8") as fh:
        return fh.read()


# --- the constants and their labels ------------------------------------------------------------------------------------

def test_the_constants(host):
    assert host.K.satiety.ACUTE_MAX == 0.7
    assert host.K.satiety.ACUTE_HALF_LIFE_H == 0.5
    assert host.K.satiety.ACUTE_KIND.aerobic == 1
    assert host.K.satiety.ACUTE_KIND.resistance == 0.5
    assert host.K.satiety.ACUTE_KIND.walk == 0
    assert host.K.energy.EX_LAG_TAU_D == 24
    assert host.K.energy.EX_BYPASS_LO == 0.30
    assert host.K.energy.EX_BYPASS_HI == 0.45


def test_each_activity_constant_names_its_rows_and_its_label():
    sat = src("NR_Kernel_Satiety.lua")
    for name in ("ACUTE_MAX", "ACUTE_HALF_LIFE_H"):
        line = re.search(r"^K\.satiety\.%s = .*$" % name, sat, re.M).group(0)
        assert "game choice, fitted in Task 4b (Plan 11c)" in line, name
        assert "S1334 open" in line, name
        assert re.search(r"S13(0[3-6])", line), name
    for kind in ("aerobic", "resistance", "walk"):
        line = re.search(r"^K\.satiety\.ACUTE_KIND\.%s = .*$" % kind, sat, re.M).group(0)
        assert re.search(r"S1\d{3}", line), kind
    line = re.search(r"^K\.satiety\.ACUTE_KIND\.resistance = .*$", sat, re.M).group(0)
    assert "game choice" in line and "S1301" in line
    line = re.search(r"^K\.satiety\.ACUTE_KIND\.walk = .*$", sat, re.M).group(0)
    assert "S1302" in line
    eng = src("NR_Kernel_Energy.lua")
    line = re.search(r"^K\.energy\.EX_LAG_TAU_D = .*$", eng, re.M).group(0)
    assert "game choice, fitted in Task 4b (Plan 11c)" in line
    assert "S1335 open" in line and "S1318" in line and "S1312" in line
    for name in ("EX_BYPASS_LO", "EX_BYPASS_HI"):
        line = re.search(r"^K\.energy\.%s = .*$" % name, eng, re.M).group(0)
        assert "game choice" in line and "ruling 11c-32" in line, name
    line = re.search(r"^K\.energy\.EX_BYPASS_LO = .*$", eng, re.M).group(0)
    assert "S1325" in line and "S1312" in line and "S1318" in line


# --- the acute suppression term --------------------------------------------------------------------------------------

def test_suppression_rises_toward_one_while_vigorous_aerobic(host):
    S = host.call("satiety.exerciseSuppression", 0, 0.5, True, "aerobic")
    assert S == pytest.approx(0.5)
    S = host.call("satiety.exerciseSuppression", S, 0.5, True, "aerobic")
    assert S == pytest.approx(0.75)


def test_suppression_decays_by_half_each_half_life_when_not_vigorous(host):
    S = host.call("satiety.exerciseSuppression", 0.8, 0.5, False, "aerobic")
    assert S == pytest.approx(0.4)
    S = host.call("satiety.exerciseSuppression", 0.8, 1.0, False, None)
    assert S == pytest.approx(0.2)


def test_suppression_steps_compose_minute_by_minute(host):
    S = 0
    for _ in range(60):
        S = host.call("satiety.exerciseSuppression", S, 1 / 60, True, "aerobic")
    assert S == pytest.approx(0.75)
    for _ in range(30):
        S = host.call("satiety.exerciseSuppression", S, 1 / 60, False, "aerobic")
    assert S == pytest.approx(0.375)


def test_resistance_rises_toward_its_smaller_weight(host):
    S = host.call("satiety.exerciseSuppression", 0, 10.0, True, "resistance")
    assert S == pytest.approx(0.5)
    a = host.call("satiety.exerciseSuppression", 0, 0.5, True, "aerobic")
    r = host.call("satiety.exerciseSuppression", 0, 0.5, True, "resistance")
    assert 0 < r < a


def test_walking_and_an_unknown_kind_add_nothing(host):
    assert host.call("satiety.exerciseSuppression", 0, 1.0, True, "walk") == 0
    assert host.call("satiety.exerciseSuppression", 0, 1.0, True, "juggling") == 0
    assert host.call("satiety.exerciseSuppression", 0, 1.0, True, None) == 0
    # a walk after a run relaxes toward 0 like rest
    assert host.call("satiety.exerciseSuppression", 0.8, 0.5, True, "walk") == pytest.approx(0.4)


def test_suppression_holds_for_no_time_and_reads_a_bad_state_as_zero(host):
    assert host.call("satiety.exerciseSuppression", 0.6, 0, True, "aerobic") == 0.6
    assert host.call("satiety.exerciseSuppression", 0.6, -1, False, "aerobic") == 0.6
    nan = float("nan")
    assert host.call("satiety.exerciseSuppression", nan, 0.5, False, "aerobic") == 0
    assert host.call("satiety.exerciseSuppression", math.inf, 0.5, True, "aerobic") == pytest.approx(0.5)
    assert host.call("satiety.exerciseSuppression", nan, 0, True, "aerobic") == 0


def test_suppression_no_time_path_is_clamped_to_the_unit_interval(host):
    nan = float("nan")
    for dt in (0, -1, nan):
        assert host.call("satiety.exerciseSuppression", 1.7, dt, True, "aerobic") == 1
        assert host.call("satiety.exerciseSuppression", -0.4, dt, False, "aerobic") == 0
        assert host.call("satiety.exerciseSuppression", 0.6, dt, True, "aerobic") == 0.6
        assert host.call("satiety.exerciseSuppression", nan, dt, True, "aerobic") == 0
        assert host.call("satiety.exerciseSuppression", math.inf, dt, True, "aerobic") == 0


def test_suppression_stays_in_the_unit_interval(host):
    for S in (-0.5, 0, 0.3, 1, 1.7):
        for vig in (True, False):
            for kind in ("aerobic", "resistance", "walk"):
                for dt in (1 / 60, 0.5, 3.0):
                    out = host.call("satiety.exerciseSuppression", S, dt, vig, kind)
                    assert 0 <= out <= 1, (S, vig, kind, dt, out)


def test_acute_factor_is_one_less_the_scaled_state(host):
    assert host.call("satiety.acuteFactor", 0) == 1
    assert host.call("satiety.acuteFactor", 1) == pytest.approx(1 - host.K.satiety.ACUTE_MAX)
    assert host.call("satiety.acuteFactor", 0.5) == pytest.approx(1 - 0.5 * host.K.satiety.ACUTE_MAX)


def test_acute_factor_reads_a_bad_state_as_zero_and_clamps_to_the_unit_interval(host):
    top = 1 - host.K.satiety.ACUTE_MAX
    assert host.call("satiety.acuteFactor", 1.7) == pytest.approx(top)
    assert host.call("satiety.acuteFactor", -0.4) == 1
    assert host.call("satiety.acuteFactor", float("nan")) == 1
    assert host.call("satiety.acuteFactor", math.inf) == 1
    assert host.call("satiety.acuteFactor", -math.inf) == 1


# --- the exercise lag ------------------------------------------------------------------------------------------------

def test_the_lag_relaxes_toward_the_exercise_rate(host):
    tau_h = host.K.energy.EX_LAG_TAU_D * 24
    # 1 kcal a minute held for one hour: a rate of 1440 kcal a day, entered by 1 - exp(-1 / tau_h)
    L = host.call("energy.exerciseLag", 0, 60.0, 1.0)
    assert L == pytest.approx(1440.0 * (1 - math.exp(-1 / tau_h)))
    # one time constant at a steady rate reaches 1 - 1/e of it
    L = 0
    for _ in range(int(round(tau_h))):
        L = host.call("energy.exerciseLag", L, 60.0, 1.0)
    assert L == pytest.approx(1440.0 * (1 - math.exp(-1)), rel=1e-9)


def test_the_lag_decays_with_no_exercise(host):
    tau_h = host.K.energy.EX_LAG_TAU_D * 24
    assert host.call("energy.exerciseLag", 500.0, 0, 24.0) == pytest.approx(500.0 * math.exp(-24 / tau_h))


def test_the_lag_is_about_zero_the_same_day(host):
    # S1312: a 90 min run of 1127 kcal enters the lag at about exKcal / EX_LAG_TAU_D
    L = 0
    for _ in range(90):
        L = host.call("energy.exerciseLag", L, 1127.0 / 90, 1 / 60)
    assert L == pytest.approx(1127.0 / host.K.energy.EX_LAG_TAU_D, rel=0.01)
    assert L / 1127.0 < 0.05


def test_the_lag_holds_for_no_time_and_heals_bad_reads(host):
    assert host.call("energy.exerciseLag", 300.0, 50.0, 0) == 300.0
    assert host.call("energy.exerciseLag", float("nan"), 0, 1.0) == 0
    assert host.call("energy.exerciseLag", 300.0, float("nan"), 1.0) == pytest.approx(
        300.0 * math.exp(-1 / (host.K.energy.EX_LAG_TAU_D * 24)))


def test_the_lag_reads_a_negative_or_infinite_exercise_as_none(host):
    decay = 300.0 * math.exp(-1 / (host.K.energy.EX_LAG_TAU_D * 24))
    for bad in (-50.0, -math.inf, math.inf):
        assert host.call("energy.exerciseLag", 300.0, bad, 1.0) == pytest.approx(decay)
    assert host.call("energy.exerciseLag", 0, -50.0, 1.0) == 0


def test_lagged_reads_the_state_non_negative_and_finite(host):
    assert host.call("energy.lagged", 250.0) == 250.0
    assert host.call("energy.lagged", -5.0) == 0
    assert host.call("energy.lagged", float("nan")) == 0
    assert host.call("energy.lagged", math.inf) == 0


# --- the energy state the writer hands to hungerTarget --------------------------------------------------------------

def test_a_food_deficit_enters_at_once(host):
    es = host.call("energy.activityState", -750.0, 0, 0, 0, 1)
    assert es == pytest.approx(host.call("energy.state", -750.0, 0, 1))
    assert es == pytest.approx(1.25)


def test_the_exercise_share_enters_only_through_the_lag(host):
    # an 1127 kcal run with no food change: eb24h -1127, ex24h 1127; with the lag at 0 the state reads neutral
    assert host.call("energy.activityState", -1127.0, 1127.0, 0, 0, 1) == pytest.approx(1.0)
    # the lag's share enters as a deficit
    assert host.call("energy.activityState", -1127.0, 1127.0, 300.0, 0, 1) == pytest.approx(1 + 0.5 * 300 / 1500)
    # today's form (activity billed at once) would read 1.376
    assert host.call("energy.state", -1127.0, 0, 1) == pytest.approx(1 + 0.5 * 1127 / 1500)


def test_the_fat_and_glycogen_arms_pass_through(host):
    a = host.call("energy.activityState", -200.0, 100.0, 50.0, 0.2, 0.4)
    assert a == pytest.approx(host.call("energy.state", -200.0 + 100.0 - 50.0, 0.2, 0.4))
    assert host.call("energy.activityState", 0, 0, 0, 0, None) == pytest.approx(1.0)


def test_activity_never_pushes_the_state_below_the_same_intake_without_it(host):
    # S1330-S1332: the state with the activity is never below the state of the same intake had the activity not
    # happened (eb24h + ex24h, no lag), over a grid that includes a surplus from eating to match the work and every
    # read of the 24 h expenditure the bypass can meet
    nan = float("nan")
    for intake_bal in (-2500.0, -800.0, 0.0, 900.0, 3200.0):
        for ex in (0.0, 300.0, 2300.0):
            for L in (0.0, 100.0, 2300.0, -50.0, nan):
                for ee in (None, nan, 0, -2500.0, 1e12, 2500.0, 600.0):
                    with_act = host.call("energy.activityState", intake_bal - ex, ex, L, 0, 1, ee)
                    without = host.call("energy.state", intake_bal, 0, 1)
                    assert with_act >= without - 1e-12, (intake_bal, ex, L, ee)


def test_the_bypass_ramp_has_weight_zero_half_and_one(host):
    # eb24h + ex24h - lag becomes eb24h + ex24h - (lag + w x (ex24h - lag)); d = -eb24h / ee24h is the deficit share
    ee, ex, L = 2500.0, 800.0, 100.0
    lo, hi = host.K.energy.EX_BYPASS_LO, host.K.energy.EX_BYPASS_HI

    def at(d):
        eb = -d * ee
        return host.call("energy.activityState", eb, ex, L, 0, 1, ee), eb

    def expect(eb, w):
        return host.call("energy.state", eb + ex - (L + w * (ex - L)), 0, 1)

    for d in (0.0, 0.2, lo):
        es, eb = at(d)
        assert es == pytest.approx(expect(eb, 0)), d
        assert es == pytest.approx(host.call("energy.state", eb + ex - L, 0, 1)), d
    es, eb = at((lo + hi) / 2)
    assert es == pytest.approx(expect(eb, 0.5))
    assert es > host.call("energy.state", eb + ex - L, 0, 1)
    for d in (hi, 0.6, 1.0):
        es, eb = at(d)
        assert es == pytest.approx(expect(eb, 1)), d
        assert es == pytest.approx(host.call("energy.state", eb, 0, 1)), d


def test_the_bypass_leaves_whybrows_26_to_28_percent_arms_at_weight_zero(host):
    # S1318: arms at 26-28 % deficits still compensate about 30 % over weeks, so the ramp has not begun there
    ee, ex, L = 2500.0, 800.0, 100.0
    for d in (0.26, 0.28):
        assert host.call("energy.activityState", -d * ee, ex, L, 0, 1, ee) == pytest.approx(
            host.call("energy.state", -d * ee + ex - L, 0, 1)), d


def test_the_bypass_does_nothing_when_the_lag_already_covers_the_exercise(host):
    # lag >= ex24h: nothing to bypass
    assert host.call("energy.activityState", -1500.0, 200.0, 900.0, 0, 1, 2500.0) == pytest.approx(
        host.call("energy.state", -1500.0 + 200.0 - 900.0, 0, 1))


def test_an_unreadable_expenditure_leaves_the_lag_unbypassed(host):
    base = host.call("energy.activityState", -1500.0, 800.0, 100.0, 0, 1)
    assert base == pytest.approx(host.call("energy.state", -1500.0 + 800.0 - 100.0, 0, 1))
    for ee in (None, float("nan"), math.inf, 0, -2500.0):
        assert host.call("energy.activityState", -1500.0, 800.0, 100.0, 0, 1, ee) == pytest.approx(base), ee
    assert host.call("energy.activityState", -1500.0, 800.0, 100.0, 0, 1, 1e12) == pytest.approx(base)


def test_a_negative_exercise_read_is_taken_as_none(host):
    assert host.call("energy.activityState", -300.0, -200.0, 0, 0, 1) == pytest.approx(
        host.call("energy.state", -300.0, 0, 1))


def test_a_non_finite_exercise_read_is_taken_as_none(host):
    for bad in (float("nan"), math.inf):
        assert host.call("energy.activityState", -300.0, bad, 0, 0, 1) == pytest.approx(
            host.call("energy.state", -300.0, 0, 1))
