"""The remaining-fraction drain (NR_Kernel_Drain.lua, K.drain; Plan 17 Task 2, spec docs/superpowers/specs/2026-10-19-
health-combine-design.md sections 1 and 2; the onsets and clocks of Plan 15 Tasks 4 and 6).

Every lethal state keeps a remaining fraction, 1 at its onset and 0 at its death point (S2231-S2262): starvation by BMI
to 12 (S2234) and dehydration by deficit to 17 % on the curve 1 - ln(1 + a t) / ln(1 + a T), which opens at vanilla's
level-4 rate (#0516, #0518, #2922); wet beriberi 5 weeks after clinical onset (S2255, an inference), scurvy and
pellagra at the game choices of 90 and 180 days and the sodium and iron rungs at their Plan 5 drain times, each on a
line. The minute's target folds the active fractions by the combine rule (worst, multiply, add) and health falls toward
it by at most the sum of the active rates. Each expectation was worked in Python doubles from the spec's formulas
before it was written.
"""
import json
import math
import os
import random

import pytest

TOL = 1e-12
H2 = 1.70 * 1.70
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
CALIBRATION = os.path.join(REPO, "testing", "artifacts", "calibrate-drain-20261019", "calibration.json")
FAST_DEATHS = {                       # water-only fasts (dtM 1), Plan 16 Task 5: (body weight kg, days, death day, state)
    "default": (None, 79, 77.00, 3),  # wet beriberi since Plan 16 Task 5 (no deficit ceiling): was starvation at BMI 12, day 61.91
    "90 kg": (90.0, 79, 77.00, 3),    # wet beriberi (K.drain.BERIBERI): clinical at day 42 + 840 h, before BMI 12
}
LINES = [(2, 2160), (3, 840), (4, 4320), (5, 6), (7, 24)]     # the line states and their death hours


@pytest.fixture(scope="module")
def D(host):
    return host.K.drain


def opt(h, pace=3, combine=2, dayMin=90):
    return h.table({"pace": pace, "combine": combine, "dayMin": dayMin})


def frac(h, code, t=0.0, pace=3, dayMin=90, p=0.0, dehyd=0.0):
    """The fraction and rate of state code at t hours (pStarve p, dehydPct dehyd)."""
    return h.K.drain.fraction(code, t, h.table({"pStarve": p, "dehydPct": dehyd}), opt(h, pace, 2, dayMin))


def record(h, unfed=None, inDay=0.0, day=4, lm=52.02, fm=10.0, lx=0.0, dehyd=0.0, na=140.0, vitC=(1, 0),
           thiamine=(1, 0), niacin=(1, 0), iron=0, lastAgeH=100.0, at=100.0):
    """A record at world age `at`: fed (the meal pool at 10) unless `unfed` hours ago its pool was last fed (M 0 and
    drain.fedAgeH at - unfed, Plan 15 Task 6 fix 1)."""
    t = {
        "body": {"lm": lm, "fm": fm, "lx": lx, "inDay": inDay, "dayStartH": day * 24.0},
        "nutrients": {"vitC": {"g": vitC[0], "ah": vitC[1]}, "thiamine": {"g": thiamine[0], "ah": thiamine[1]},
                      "niacin": {"g": niacin[0], "ah": niacin[1]}, "iron": {"x": iron}, "lastAgeH": lastAgeH},
        "fluids": {"dehydPct": dehyd, "naPlasma": na},
        "acute": {"starvedDays": 0},
        "satiety": {"M": 10.0},
    }
    if unfed is not None:
        t["satiety"]["M"] = 0.0
        t["drain"] = {"fedAgeH": at - unfed}
    rec = h.table(t)
    if unfed is not None:
        h.K.drain.ensure(rec)                       # the rest of the fresh table laid around the stamp
        for k, v in h.py(h.K.drain.new()).items():
            if rec.drain[k] is None:
                rec.drain[k] = h.table(v) if isinstance(v, dict) else v
    return rec


def curve(t, T, a):
    t = min(max(t, 0.0), T)
    return 1 - math.log(1 + a * t) / math.log(1 + a * T) if a > 1e-9 else 1 - t / T


# --- the states and the options ---------------------------------------------------------------------------------

def test_the_seven_states_and_their_death_points(host, D):
    S = host.py(D.states)
    assert [S[i]["name"] for i in range(1, 8)] == ["starvation", "scurvy", "beriberi", "pellagra", "hyponatraemia",
                                                   "dehydration", "iron"]
    assert [S[i]["death"] for i in range(1, 8)] == [12, 2160, 840, 4320, 6, 17, 24]
    assert [S[i]["onset"] for i in range(1, 8)] == [30, 4, 4, 4, 3, 4, 3]       # Task 4 fix 1: dehydration at 4 %; Task 6 fix 1: 30 unfed hours
    assert [S[i].get("short") for i in range(1, 8)] == [336, None, None, None, None, 48, None]   # the two curve states
    assert (D.STARVATION, D.SCURVY, D.BERIBERI, D.PELLAGRA, D.HYPONAT, D.DEHYD, D.IRON, D.N) == (1, 2, 3, 4, 5, 6, 7, 7)
    assert D.BMI_DEATH == 12 and D.BERIBERI_DEATH_H == 35 * 24                 # S2234; S2255 five weeks
    assert D.SCURVY_DEATH_H == 90 * 24 and D.PELLAGRA_DEATH_H == 180 * 24      # the named game choices
    assert (D.DEHYD_ONSET, D.DEHYD_KNEE, D.DEHYD_DEATH, D.DEHYD_FINAL) == (4, 15, 17, 0.1)
    assert D.SLEEP_FLOOR == 10 and D.NONE == 100


def test_the_options_and_their_defaults(host, D):
    assert host.py(D.OPT) == {"pace": 3, "combine": 2, "dayMin": 90}           # Realistic and Multiply (spec 2.2, 2.3)
    assert (D.PACE_VANILLA, D.PACE_SHORT, D.PACE_REAL) == (1, 2, 3)
    assert (D.COMBINE_WORST, D.COMBINE_MULTIPLY, D.COMBINE_ADD) == (1, 2, 3)
    assert (D.SHORT_STARVE_H, D.SHORT_DEHYD_H) == (336, 48)
    for name in ("FIRST_FLOOR", "STARVE_RATE", "DEF_RATE", "DEF_HOLD_H", "DEF_FINAL_H", "ACUTE_FINAL_H", "BMI_KNEE",
                 "timeKnots", "starveFloor", "DEHYD_RATE", "DEHYD_KNOTS", "floor"):
        assert D[name] is None, name                                           # spec 2.4: removed, no shim


# --- the curve --------------------------------------------------------------------------------------------------

def test_the_curve_ends_and_opening_slope(host, D):
    K = host.K
    assert K.drain.curve(0.0, 336.0, 0.05) == 1.0
    assert abs(K.drain.curve(336.0, 336.0, 0.05)) < 1e-12
    s = (1.0 - K.drain.curve(1e-6, 336.0, 0.05)) / 1e-6
    assert abs(s - 0.05 / math.log(1 + 0.05 * 336.0)) < 1e-6


def test_the_curve_is_the_line_at_a_zero(host, D):
    assert abs(host.K.drain.curve(84.0, 336.0, 0.0) - 0.75) < 1e-12
    assert D.curve(84.0, 336.0, D.A_EPS) == pytest.approx(0.75, abs=TOL)       # at the epsilon: the line
    assert D.curve(-5.0, 336.0, 0.05) == 1.0 and D.curve(400.0, 336.0, 0.05) == 0.0   # tau clamps to [0, T]
    assert D.curve(1.0, 0.0, 0.05) == 0 and D.curve(1.0, -1.0, 0.0) == 0      # no span: dead


def test_the_curve_falls_monotonically_and_flattens(host, D):
    prev, prev_drop = 1.0, None
    for i in range(1, 337):
        f = D.curve(float(i), 336.0, 0.05)
        assert f == pytest.approx(curve(i, 336.0, 0.05), abs=1e-12)
        drop = prev - f
        assert drop > 0
        if prev_drop is not None:
            assert drop <= prev_drop + 1e-15                                   # the slope only eases
        prev, prev_drop = f, drop


def test_vanillas_rates_at_the_day_length(host, D):
    r = D.rVanilla
    assert abs(r(D.STARVATION, 90) - 3.564) < 1e-9 and abs(r(D.DEHYD, 90) - 17.82) < 1e-9
    assert abs(r(D.STARVATION, 60) - 2.376) < 1e-9 and abs(r(D.DEHYD, 60) - 11.88) < 1e-9
    assert r(D.SCURVY, 90) is None and r(D.IRON, 90) is None
    assert r(D.STARVATION, 0) == r(D.STARVATION, None) == r(D.STARVATION, float("nan")) == r(D.STARVATION, 90)
    assert D.R_HUNGER == pytest.approx(3.3e-4 * 120, abs=TOL) and D.R_THIRST == pytest.approx(1.65e-3 * 120, abs=TOL)


def test_solve_a_opens_at_vanillas_rate(host, D):
    K = host.K
    r = float(K.drain.rVanilla(K.drain.STARVATION, 90))
    assert abs(r - 3.564) < 1e-9
    a = K.drain.solveA(r, 336.0)
    assert abs(100 * a / math.log(1 + a * 336.0) - r) < 1e-6
    assert D.solveA(r, 336.0) == a                                              # the cached answer
    d = D.solveA(17.82, 48.0)
    assert abs(100 * d / math.log(1 + d * 48.0) - 17.82) < 1e-6
    assert D.solveA(100 / 336.0, 336.0) == 0 and D.solveA(0.1, 336.0) == 0     # at or under the line's own rate


def test_the_solve_is_cached_once_per_rate_and_death_time(host, D):
    n0 = len(host.py(D.ACACHE))
    for _ in range(50):
        D.aFor(D.STARVATION, 3.3, 336.0)
    assert len(host.py(D.ACACHE)) == n0 + 1                                      # one entry, not one per minute
    D.aFor(D.STARVATION, 2.2, 336.0)                                             # a new day length: one more
    assert len(host.py(D.ACACHE)) == n0 + 2
    m = host.py(D.AMEMO[1])
    assert m["r"] == 2.2 and m["T"] == 336.0 and m["a"] == D.solveA(2.2, 336.0)


# --- the paces --------------------------------------------------------------------------------------------------

def test_vanilla_pace_is_vanillas_line(host, D):
    K = host.K
    T = 100 / 3.564
    f, rate = K.drain.fraction(K.drain.STARVATION, T / 2, None, host.table({"pace": 1, "combine": 3, "dayMin": 90}))
    assert abs(f - 0.5) < 1e-9 and abs(rate - 3.564 * 24) < 1e-9
    f, rate = frac(host, D.DEHYD, 100 / 17.82, pace=1)
    assert f == pytest.approx(0, abs=1e-9) and rate == pytest.approx(17.82 * 24, abs=1e-9)
    f, _ = frac(host, D.DEHYD, 100 / 11.88 / 4, pace=1, dayMin=60)             # a 60-minute day: a slower line
    assert f == pytest.approx(0.75, abs=1e-9)


@pytest.mark.parametrize("code,T,r", [(1, 336.0, 3.564), (6, 48.0, 17.82)])
def test_shortened_is_the_curve_on_hours_opening_at_vanillas_rate(host, D, code, T, r):
    f0, rate = frac(host, code, 0.0, pace=2)
    assert f0 == 1.0 and rate == pytest.approx(r * 24, abs=1e-9)
    s = (1 - frac(host, code, 1e-6, pace=2)[0]) / 1e-6 * 100
    assert s == pytest.approx(r, rel=1e-5)                                       # opening slope, health a game hour
    assert frac(host, code, T - 0.1, pace=2)[0] > 0 and frac(host, code, T, pace=2)[0] == pytest.approx(0, abs=1e-12)
    prev = 1.0
    for i in range(1, 101):
        f = frac(host, code, T * i / 100, pace=2)[0]
        assert f < prev                                                          # no knee, no hold: unbroken to 0
        prev = f
    assert frac(host, code, T / 2, pace=2, dehyd=16.5)[0] == frac(host, code, T / 2, pace=2)[0]   # hours, not deficit


def test_shortened_takes_the_line_when_vanillas_rate_is_under_it(host, D):
    f, rate = frac(host, D.STARVATION, 168.0, pace=2, dayMin=5)                  # 0.198 a game hour < 100 / 336
    assert f == pytest.approx(0.5, abs=1e-12) and rate == pytest.approx(100 / 336 * 24, abs=1e-9)


@pytest.mark.parametrize("code,T", LINES)
@pytest.mark.parametrize("pace", [1, 2, 3])
def test_a_deficiency_or_rung_is_a_line_to_its_death_at_every_pace(host, D, code, T, pace):
    for k in range(0, 11):
        f, rate = frac(host, code, T * k / 10, pace=pace, dayMin=60)
        assert f == pytest.approx(1 - k / 10, abs=1e-12)
        assert rate == pytest.approx(100 * 24 / T, abs=1e-9)
    assert frac(host, code, T + 100, pace=pace)[0] == 0


def test_realistic_dehydration_curve_to_its_knee_then_the_final_stage(host, D):
    f = lambda d: frac(host, D.DEHYD, 5.0, dehyd=d)[0]
    assert f(3.0) == 1.0 and f(4.0) == 1.0
    assert f(15.0) == pytest.approx(0.1, abs=1e-12)                              # the 0.1 knee at 15 %
    assert f(16.0) == pytest.approx(0.05, abs=1e-12) and f(17.0) == 0 and f(25.0) == 0
    assert f(9.5) == pytest.approx(0.1 + 0.9 * curve(0.5, 1.0, D.A_DEHYD), abs=1e-12)
    prev = 1.0
    for i in range(1, 1301):
        d = 4 + i * 0.01
        g = f(d)
        assert g < prev or g == 0, d
        assert (g > 0.1 + 1e-12) == (d < 15 - 1e-9) or abs(d - 15) < 1e-6, d
        prev = g
    assert frac(host, D.DEHYD, 5.0, dehyd=9.5)[1] == pytest.approx(17.82 * 24, abs=1e-9)


def test_realistic_starvation_by_bmi_progress(host, D):
    f = lambda p: frac(host, D.STARVATION, 5.0, p=p)[0]
    assert f(0.0) == 1.0 and f(1.0) == pytest.approx(0, abs=1e-12) and f(2.0) == 0
    assert f(0.25) == pytest.approx(curve(0.25, 1.0, D.A_STARVE), abs=1e-12)
    assert D.progress(22.0, 17.0) == pytest.approx(0.5, abs=TOL) and D.progress(22.0, 23.0) == 0
    assert D.progress(22.0, 11.0) == 1 and D.progress(12.0, 12.0) == 1 and D.progress(11.5, 11.0) == 1


def test_the_opening_slopes_match_the_calibration_artifact(host, D):
    # ruling T1-1: the constants cannot drift from calibrate-drain-20261019; each opens at vanilla's rate at 90 min
    with open(CALIBRATION, encoding="utf-8") as fh:
        cal = json.load(fh)
    a, d = float(D.A_STARVE), float(D.A_DEHYD)
    assert a == cal["a_starve"] and float(D.STARVE_DPDT) == cal["starve_dpdt_per_h"]
    starve = 100 * a / math.log(1 + a) * cal["starve_dpdt_per_h"]
    dehyd = 100 * 0.9 * d / math.log(1 + d) * cal["dehyd_dpdt_per_h"]          # the 0.9 form (ruling T1-1)
    assert starve == pytest.approx(3.564, rel=1e-6) and dehyd == pytest.approx(17.82, rel=1e-6)
    dp = 1e-9                                                                    # and through the kernel's own fractions
    ks = (1 - frac(host, D.STARVATION, 0, p=dp)[0]) / dp * 100 * cal["starve_dpdt_per_h"]
    kd = (1 - frac(host, D.DEHYD, 0, dehyd=4 + 11 * dp)[0]) / dp * 100 * cal["dehyd_dpdt_per_h"]
    assert ks == pytest.approx(3.564, rel=1e-5) and kd == pytest.approx(17.82, rel=1e-5)


def test_a_non_finite_input_leaves_the_state_out(host, D):
    assert frac(host, D.BERIBERI, float("nan")) is None
    assert frac(host, D.DEHYD, 1.0, dehyd=float("nan")) is None
    assert frac(host, D.STARVATION, 1.0, p=float("nan")) is None
    rec = record(host, thiamine=(4, float("nan")), iron=3)
    d = D.step(rec, 1.0, 100.0)
    assert d.state == 7 and d.active is True and d.frac[3] is None             # beriberi skipped this minute
    rec.nutrients.iron.x = 0
    assert D.step(rec, 1.0, 100.0).active is False


# --- the combine step and the cap -------------------------------------------------------------------------------

def two_states(h, combine, pace=1):
    """Starvation (Vanilla pace, at f 0.6 after this step) and beriberi (f 0.5): a record stepped once."""
    T = 100 / 3.564
    rec = record(h, unfed=40.0, thiamine=(4, 420.0))
    rec.drain.bmi0 = 22.0
    rec.drain.stH = 0.4 * T - 1 / 60
    return h.K.drain.step(rec, 1.0, 100.0, False, opt(h, pace, combine)), rec


def test_combine_rules_order(host, D):
    # worst >= multiply >= add for the same fractions; 0.6 and 0.5 give 50, 30, 10
    want = {1: 50.0, 2: 30.0, 3: 10.0}
    for c, target in want.items():
        d, _ = two_states(host, c)
        assert d.frac[1] == pytest.approx(0.6, abs=1e-9) and d.frac[3] == pytest.approx(0.5, abs=1e-9)
        assert abs(d.target - target) < 1e-9, c
        assert d.state == 3 and d.mask == 1 + 4
    d, _ = two_states(host, 9)                                                   # an unknown rule reads multiply
    assert d.target == pytest.approx(30.0, abs=1e-9)


def test_the_combine_properties(host, D):
    rng = random.Random(17)
    for _ in range(300):
        n = rng.randint(1, 4)
        fs = [rng.choice([0.0, rng.random(), 1.0]) for _ in range(n)]
        out = {}
        for c in (1, 2, 3):
            d = host.table({"active": True, "frac": {i + 1: f for i, f in enumerate(fs)}})
            out[c] = D.combine(d, opt(host, 3, c))
        assert out[1] >= out[2] - 1e-12 >= out[3] - 2e-12                      # worst >= multiply >= add
        assert out[1] == pytest.approx(100 * min(fs), abs=1e-9)
        assert out[2] == pytest.approx(100 * math.prod(fs), abs=1e-9)
        assert out[3] == pytest.approx(100 * max(0.0, 1 - sum(1 - f for f in fs)), abs=1e-9)
        for c in (1, 2):
            assert (out[c] == 0) == (min(fs) == 0)                               # 0 only when some fraction is 0
    assert D.combine(host.table({"active": False, "frac": {1: 0.2}}), opt(host)) == 100


def test_the_rate_is_the_sum_of_the_active_rates(host, D):
    d, _ = two_states(host, 2)
    assert d.rate == pytest.approx(3.564 * 24 + 100 * 24 / 840, abs=1e-9)
    assert d.drainThisMinute == pytest.approx(d.rate / 1440, abs=TOL)
    rec = record(host, thiamine=(4, 500), dehyd=6.0, iron=3)
    d = D.step(rec, 2.0, 100.0)
    assert d.rate == pytest.approx(17.82 * 24 + 100 * 24 / 840 + 100, abs=1e-9)
    assert d.drainThisMinute == pytest.approx(d.rate * 2 / 1440, abs=TOL)


def test_the_state_is_the_smallest_fraction_and_a_tie_keeps_the_earlier_code(host, D):
    d = D.step(record(host, thiamine=(4, 500), iron=3), 1.0, 100.0)            # beriberi 1 - 500/840, iron 1 - 1/24/60
    assert d.state == 3 and d.frac[3] == pytest.approx(1 - 500 / 840, abs=1e-12)
    tie = D.step(record(host, vitC=(4, 0), thiamine=(4, 0)), 1.0, 100.0)
    assert tie.state == 2 and tie.target == 100                                # a tie keeps the earlier code


def test_take_never_passes_the_target(host, D):
    d = host.table({"active": True, "target": 40.0, "drainThisMinute": 0.5})
    assert D.take(d, 60.0) == 0.5
    assert D.take(d, 40.2) == pytest.approx(0.2, abs=1e-12)
    assert D.take(d, 40.0) == 0 and D.take(d, 30.0) == 0                      # at or under the target: nothing
    assert D.take(d, float("nan")) == 0 and D.take(d, None) == 0
    d.active = False
    assert D.take(d, 60.0) == 0


def test_health_follows_a_compounding_target_at_the_capped_rate(host, D):
    # two states at once: health falls at most rate x dtM / 1440 a minute and never under the target
    rec = record(host, unfed=40.0, thiamine=(4, 0.0))
    health = 100.0
    for m in range(0, 3000):
        d = D.step(rec, 1.0, 100.0 + m / 60, False, opt(host, 2, 2))
        rec.nutrients.thiamine.ah = rec.nutrients.thiamine.ah + 1 / 60
        take = D.take(d, health)
        assert take <= d.rate / 1440 + 1e-12
        health -= take
        assert health >= d.target - 1e-9
    assert health == pytest.approx(d.target, abs=0.5)


def test_vanillas_regeneration_tier(host, D):
    a = D.regenAddition
    assert a(0, 0, 0, False) == 0.002 and a(1, 1, 1, False) == 0.002                 # #2354 standard
    assert a(2, 0, 0, False) == 0.0013 and a(0, 0, 2, False) == 0.0013                # level 2: reduced
    assert a(0, 3, 0, False) == 0.0008 and a(0, 0, 4, False) == 0.0008                # level 3, or SICK 4
    assert a(4, 0, 0, False) == 0 and a(0, 4, 3, False) == 0                          # HUNGRY or THIRST 4 (#2721)
    assert a(3, 3, 3, True) == 0.02 and a(0, 4, 0, True) == 0                         # asleep; #0515 zeroes it at 4
    assert D.UNITS_PER_MIN == 2 and D.PART_SPREAD == pytest.approx(17 / 5.05, abs=TOL)


def test_the_heal_reaches_the_target_and_never_passes_it(host, D):
    d = host.table({"active": True, "target": 50.0})
    assert D.heal(d, 20.0, 0.24, 1.0) == pytest.approx(0.24, abs=TOL)               # vanilla's pace, uncapped
    assert D.heal(d, 49.95, 0.24, 1.0) == pytest.approx(0.05 * 17 / 5.05, abs=1e-9)  # capped at the target
    assert D.heal(d, 49.995, 0.24, 1.0) == 0 and D.heal(d, 60.0, 0.24, 1.0) == 0    # at or above it
    assert D.heal(d, float("nan"), 0.24, 1.0) == 0 and D.heal(d, 20.0, float("nan"), 1.0) == 0
    health = 20.0
    for _ in range(2000):
        health += D.heal(d, health, 0.24, 1.0) * 5.05 / 17
        assert health <= 50.0 + 1e-9
    assert health == pytest.approx(50.0, abs=0.011)
    d.active = False
    assert D.heal(d, 20.0, 0.24, 1.0) == 0


def test_the_heal_lifts_health_toward_a_risen_target_after_a_state_ends(host, D):
    d, rec = two_states(host, 2)
    health = d.target                                                           # held at 30 by both states
    assert D.heal(d, health, 0.24, 1.0) == 0
    rec.nutrients.thiamine.g = 3                                                # beriberi ends: starvation alone
    d = D.step(rec, 1.0, 100.0 + 1 / 60, False, opt(host, 1, 2))
    assert d.mask == 1 and d.target > 59 and D.take(d, health) == 0
    assert D.heal(d, health, 0.24, 1.0) == pytest.approx(0.24, abs=TOL)


def test_a_pace_switch_mid_state_moves_the_target_at_the_next_step(host, D):
    rec = record(host, unfed=40.0)
    for m in range(0, 120):
        d = D.step(rec, 1.0, 100.0 + m / 60, False, opt(host, 3, 2))
    real = d.target
    d = D.step(rec, 1.0, 102.0, False, opt(host, 1, 2))
    assert d.target == pytest.approx(100 * (1 - d.stH * 3.564 / 100), abs=1e-9) and d.target != real
    d = D.step(rec, 1.0, 102.0 + 1 / 60, False, opt(host, 2, 2))
    assert d.target == pytest.approx(100 * curve(d.stH, 336.0, D.solveA(3.564, 336.0)), abs=1e-6)


def test_the_step_lays_no_table_per_minute(host, D):
    rec = record(host, unfed=40.0, thiamine=(4, 10.0), dehyd=5.0)
    d = D.step(rec, 1.0, 100.0)
    f0, in0, opt0 = d.frac, D.IN, D.OPT
    for m in range(1, 50):
        d = D.step(rec, 1.0, 100.0 + m / 60)
        assert host.rt.eval("rawequal")(d.frac, f0) and host.rt.eval("rawequal")(D.IN, in0)
    assert host.rt.eval("rawequal")(D.OPT, opt0)
    assert sorted(host.py(d.frac)) == [1, 3, 6]


def test_the_step_reads_the_module_options_when_none_are_passed(host, D):
    rec = record(host, dehyd=5.0)
    D.OPT.pace = 1
    try:
        d = D.step(rec, 1.0, 100.0)
        assert d.frac[6] == pytest.approx(1 - (1 / 60) * 17.82 / 100, abs=1e-12)  # Vanilla pace off D.OPT
    finally:
        D.OPT.pace = 3


# --- the smoothed BMI clock (spec section 1.2a, rulings T1-4 and T2-1) -------------------------------------------

def starving(h, lm=52.02, fm=10.0, day=4, at=100.0):
    return record(h, unfed=40.0, lm=lm, fm=fm, day=day, at=at, lastAgeH=at)


def test_the_clock_opens_at_the_record_day_start_at_the_calibrated_bmi_rate(host, D):
    # ruling T2-1: the anchor is the open record day's start (dayStartH 96), the rate the calibration body's BMI loss
    rec = starving(host)
    bmi = 62.02 / H2
    d = D.step(rec, 1.0, 100.0)
    assert D.STARVE_DBMI == pytest.approx(D.STARVE_DPDT * (D.CAL_BMI0 - 12), abs=TOL)
    assert (d.bClose, d.bRate, d.pAt, d.pS) == (pytest.approx(bmi, abs=TOL), D.STARVE_DBMI, 96.0, 0)
    assert d.bmi0 == pytest.approx(bmi - 4 * D.STARVE_DBMI, abs=1e-12)          # the estimate at the onset: p opens at 0
    d = D.step(rec, 60.0, 110.0)                                                 # 10 h later, no close
    p = 10 * D.STARVE_DBMI / (d.bmi0 - 12)
    assert d.pS == pytest.approx(p, abs=1e-15)
    assert d.frac[1] == pytest.approx(curve(p, 1.0, D.A_STARVE), abs=1e-12)


def test_a_close_re_anchors_on_the_true_bmi_and_the_spans_rate(host, D):
    rec = starving(host)
    d = D.step(rec, 1.0, 100.0)
    bmi0 = d.bmi0
    rec.body.fm = rec.body.fm - 0.6                                             # the close's loss
    rec.body.dayStartH = 120.0
    d = D.step(rec, 1.0, 120.5)
    new = (62.02 - 0.6) / H2
    assert d.bClose == pytest.approx(new, abs=1e-12) and d.pAt == 120.0
    assert d.bRate == pytest.approx(0.6 / H2 / 24, abs=1e-12)                  # the closed span 96-120
    assert d.pS == pytest.approx((bmi0 - (new - d.bRate * 0.5)) / (bmi0 - 12), abs=1e-12)


def test_a_held_state_across_two_closes_books_the_two_day_loss_over_48_hours(host, D):
    # review F1's second defect: a fed spell held across two closes reads one rate over the whole span, not one day
    rec = starving(host)
    rec.body.recentDays = 3
    rec.body.inDayClosed, rec.body.inDay2, rec.body.inDay3 = 0.0, 0.0, 0.0
    D.step(rec, 60.0, 100.0)
    assert rec.drain.acuteH > 0
    rec.satiety.M = 400.0                                                        # a meal spell: the state held
    d = D.step(rec, 1.0, 101.0)
    assert d.starving is False and d.pAt == 96.0 and d.bmi0 > 0
    rec.body.fm = rec.body.fm - 0.6                                             # two closes' loss while held
    rec.body.dayStartH = 144.0
    rec.satiety.M = 0.0
    d = D.step(rec, 1.0, 145.0)
    assert d.starving is True and d.pAt == 144.0
    assert d.bRate == pytest.approx(0.6 / H2 / 48, abs=1e-12)


def test_the_clock_never_falls_within_the_state(host, D):
    rec = starving(host)
    D.step(rec, 1.0, 100.0)
    D.step(rec, 60.0, 119.0)
    high = rec.drain.pS
    rec.body.dayStartH = 120.0                                                  # a close with no loss at all
    d = D.step(rec, 1.0, 120.0)
    assert d.bRate == 0 and d.pS == high                                        # the estimate held, never lowered
    t0 = d.target
    rec.body.fm = rec.body.fm + 2.0                                             # a gain: the rate floors at 0
    rec.body.dayStartH = 144.0
    d = D.step(rec, 1.0, 144.0)
    assert d.bRate == 0 and d.pS == high and d.target == t0


def test_the_target_falls_smoothly_across_closes_and_health_keeps_to_the_cap(host, D):
    # the calibration body (its onset estimate at CAL_BMI0) losing 0.3 kg a record day, stepped every minute for 5
    # days with a close each 24 h: from the onset the target never rises and never drops more than the cap allows in a
    # minute (1 % for the onset estimate's span against the calibration's), and health keeps to it
    mass = (D.CAL_BMI0 + 4 * D.STARVE_DBMI) * H2
    rec = starving(host, lm=52.02, fm=mass - 52.02, day=4, at=100.0)
    health, prev_target = 100.0, 100.0
    for m in range(0, 5 * 1440):
        age = 100.0 + m / 60
        if age >= rec.body.dayStartH + 24:
            w = rec.body.lm + rec.body.fm
            rec.body.lm = rec.body.lm - 0.3 * rec.body.lm / w
            rec.body.fm = rec.body.fm - 0.3 * rec.body.fm / w
            rec.body.dayStartH = rec.body.dayStartH + 24
        d = D.step(rec, 1.0, age)
        assert d.target <= prev_target + 1e-12
        assert prev_target - d.target <= 1.01 * d.rate / 1440, m
        prev_target = d.target
        take = D.take(d, health)
        assert take <= d.rate / 1440 + 1e-12
        health -= take
        assert health >= d.target - 1e-9
    assert prev_target < 60


def test_the_s2d_fast_drops_the_target_no_faster_than_the_cap(host, D):
    # ruling T2-1 on the replay host: the guide's fast with water (FRESH, the replay's water), 4 days: the largest
    # one-minute target drop is at most the cap (1 %), and health stays within 0.01 of the target throughout
    import os
    import sys
    tools = os.path.join(REPO, "tools")
    if tools not in sys.path:
        sys.path.insert(0, tools)
    import mod_guide_series as G
    rows, _ = G.server_run([G.FRESH] + G.autodrops(4), 4 * G.DAY_MIN, ("drain.target",))
    prev = None
    for r in rows:
        t = r.get("drain.target")
        if t is None:                                                          # a row before the record's first step
            continue
        if prev is not None:
            assert prev - t <= 1.01 * 85.536 / 1440, r["age"]
        assert r[G.HEALTH] - t < 0.01, r["age"]
        prev = t
    assert prev < 90


def days_to_death(h, lm, fm):
    rec = starving(h, lm=lm, fm=fm, day=4, at=100.0)
    bmi12 = None
    for hour in range(0, 24 * 2000):
        age = 100.0 + hour
        if age >= rec.body.dayStartH + 24:
            w = rec.body.lm + rec.body.fm
            rec.body.lm = rec.body.lm - 0.3 * rec.body.lm / w
            rec.body.fm = rec.body.fm - 0.3 * rec.body.fm / w
            rec.body.dayStartH = rec.body.dayStartH + 24
        if bmi12 is None and (rec.body.lm + rec.body.fm) / H2 <= 12:
            bmi12 = hour / 24
        d = h.K.drain.step(rec, 60.0, age)
        if d.target == 0:
            return hour / 24, bmi12, d
    raise AssertionError("no death")


def test_starvation_on_bmi_progress_reaches_0_near_bmi_12_and_a_heavier_body_later(host, D):
    lean, lean12, d = days_to_death(host, 52.02, 10.0)
    assert d.state == 1 and d.pS == 1 and d.frac[1] == 0
    assert lean12 is None or abs(lean - lean12) <= 1.0                          # the estimate within a day of BMI 12
    assert (52.02 + 10.0 - 0.3 * lean) / H2 == pytest.approx(12, abs=0.3 / H2 * 1.5)
    heavy, _, _ = days_to_death(host, 52.02, 30.0)
    assert heavy > lean
    assert heavy - lean == pytest.approx(20.0 / 0.3, abs=1.5)                  # the extra 20 kg at 0.3 kg a day


def test_a_72_h_logout_mid_state_changes_nothing(host, D):
    # nothing changes offline (Plan 16): the resume moves pAt with body.dayStartH, so the twin that never left and
    # the record that came back 72 h later read the same clock, the same fraction and the same target
    def stepped():
        rec = starving(host)
        rec.body.lastAgeH = 100.0
        for m in range(0, 600):
            age = 100.0 + m / 60
            if age >= rec.body.dayStartH + 24:
                rec.body.fm = rec.body.fm - 0.3
                rec.body.dayStartH = rec.body.dayStartH + 24
            D.step(rec, 1.0, age)
            rec.nutrients.lastAgeH = age
            rec.body.lastAgeH = age
        return rec
    twin, back = stepped(), stepped()
    last = 100.0 + 599 / 60
    assert host.K.resume.resume(back, last + 72.0) == pytest.approx(72.0, abs=1e-9)
    assert back.drain.pAt == pytest.approx(twin.drain.pAt + 72.0, abs=1e-9)
    a = D.step(twin, 1.0, last + 1 / 60)
    b = D.step(back, 1.0, last + 72.0 + 1 / 60)
    for k in ("pS", "bClose", "bRate", "stH", "target", "rate"):
        assert b[k] == pytest.approx(a[k], abs=1e-12), k


FIELDS = ("pS", "bClose", "bRate", "stH", "dhH", "target", "rate", "state", "mask")


@pytest.mark.parametrize("pace", [1, 2, 3])
@pytest.mark.parametrize("leave_m", [1319, 1320, 1321])
def test_a_72_h_logout_either_side_of_a_close_changes_nothing_for_48_hours(host, D, pace, leave_m):
    # review F6: logouts either side of the 120 h close (from age 106, dayStartH 96), starvation, dehydration and
    # beriberi active, the twin and the returned record stepped every minute for 48 h after with a close each 24 h
    o = opt(host, pace, 2)

    def new():
        rec = record(host, unfed=40.0, dehyd=6.0, thiamine=(4, 100.0), day=4, at=106.0, lastAgeH=106.0)
        rec.body.lastAgeH = 106.0
        return rec

    def minute(rec, age):
        if age >= rec.body.dayStartH + 24:
            rec.body.fm = rec.body.fm - 0.3
            rec.body.dayStartH = rec.body.dayStartH + 24
        d = D.step(rec, 1.0, age, False, o)
        rec.nutrients.lastAgeH = age
        rec.body.lastAgeH = age
        return d

    twin, back = new(), new()
    for m in range(0, leave_m):
        age = 106.0 + m / 60
        minute(twin, age)
        minute(back, age)
    last = 106.0 + (leave_m - 1) / 60
    host.K.resume.resume(back, last + 72.0)
    for m in range(1, 48 * 60 + 1):
        a = minute(twin, last + m / 60)
        b = minute(back, last + 72.0 + m / 60)
        for k in FIELDS:
            assert b[k] == pytest.approx(a[k], abs=1e-9), (k, m)
        assert b.pAt - 72.0 == pytest.approx(a.pAt, abs=1e-9), m
    assert twin.drain.mask == 1 + 4 + 32


def test_a_missing_anchor_re_anchors_at_the_record_day_start(host, D):
    rec = starving(host)
    D.step(rec, 1.0, 100.0)
    D.step(rec, 60.0, 110.0)
    bmi0, high = rec.drain.bmi0, rec.drain.pS
    rec.drain.pAt = float("nan")                                                # a corrupt file's anchor
    rec.body.fm = rec.body.fm - 1.0
    D.ensure(rec)
    assert rec.drain.pAt is None
    d = D.step(rec, 1.0, 111.0)
    assert d.pAt == 96.0 and d.bRate == D.STARVE_DBMI and d.bClose == pytest.approx(61.02 / H2, abs=1e-12)
    assert d.bmi0 == bmi0 and d.pS >= high                                      # mid-state: the onset BMI kept


def test_an_unread_record_day_anchors_at_the_minute(host, D):
    rec = starving(host)
    rec.body.dayStartH = None                                                   # no record day yet (a heal's to lay)
    d = D.step(rec, 1.0, 100.0)
    assert d.pAt == 100.0 and d.bmi0 == pytest.approx(62.02 / H2, abs=TOL) and d.pS == 0


def test_a_corrupt_onset_bmi_re_onsets_and_re_anchors(host, D):
    rec = starving(host)
    D.step(rec, 1.0, 100.0)
    rec.body.fm = rec.body.fm - 1.0
    rec.body.dayStartH = 120.0
    D.step(rec, 1.0, 120.0)                       # a close: the anchor moved
    rec.drain.bmi0 = float("nan")                 # a corrupt file's onset BMI
    d = D.step(rec, 1.0, 121.0)
    assert d.bmi0 == pytest.approx((52.02 + 9.0) / H2, abs=1e-9)   # re-onset at the BMI now
    assert d.pAt == rec.body.dayStartH and d.bRate == D.STARVE_DBMI   # re-anchored, not carried


def test_the_dehydration_hours_accumulate_and_reset(host, D):
    rec = record(host, dehyd=5.0)
    for _ in range(90):
        D.step(rec, 1.0, 100.0)
    assert rec.drain.dhH == pytest.approx(1.5, abs=1e-9)
    rec.fluids.dehydPct = 3.0
    D.step(rec, 1.0, 100.0)
    assert rec.drain.dhH == 0 and rec.drain.active is False


# --- the unfed hours, the trailing 72 h and the phases (Plan 15 Task 6 fix 1) -------------------------------------
# test_the_starved_hours, of the calendar-day counter K.drain.starvedH, is deleted with the function it tested (fix 1:
# the acute onset counts unfed hours continuously); the count is reset by name.

def test_the_starvation_phases(host, D):
    p = D.starvePhase
    assert [p(0), p(29.9), p(30), p(71.9), p(72), p(335.9), p(336), p(5000)] == [0, 0, 1, 1, 2, 2, 3, 3]
    assert host.py(D.STARVE_PHASE_H) == {1: 30, 2: 72, 3: 336}
    assert D.STARVE_ONSET_H == D.STARVE_PHASE_H[1]                            # weakness from the drain's onset


# --- the step -----------------------------------------------------------------------------------------------------

def test_a_fresh_drain_table_and_its_heal(host, D):
    assert host.py(D.new()) == {"bmi0": 0, "naH": 0, "feH": 0, "stH": 0, "dhH": 0, "bClose": 0, "bRate": 0, "pS": 0,
                                "active": False, "state": 0, "mask": 0, "target": 100, "frac": {}, "rate": 0,
                                "drainThisMinute": 0, "starvedH": 0, "acuteH": 0, "starving": False,
                                "starveAcute": False, "dehydrated": False, "spell": False}
    rec = host.table({})
    d = D.ensure(rec)
    assert host.rt.eval("rawequal")(rec.drain, d) and d.bmi0 == 0
    d.bmi0, d.naH, d.feH = float("nan"), float("inf"), "x"
    d.stH, d.dhH, d.bClose, d.bRate, d.pS = None, float("nan"), "x", float("-inf"), None
    d.acuteH, d.fedAgeH, d.pAt, d.frac = -1.0, float("nan"), float("inf"), 3
    D.ensure(rec)
    assert (d.bmi0, d.naH, d.feH, d.acuteH) == (0, 0, 0, 0)
    assert (d.stH, d.dhH, d.bClose, d.bRate, d.pS) == (0, 0, 0, 0, 0)
    assert d.fedAgeH is None and d.pAt is None                               # a non-finite stamp heals to first sight
    assert host.py(d.frac) == {}


def test_a_record_with_no_state_reads_no_target(host, D):
    rec = record(host)
    d = D.step(rec, 1.0, 100.0)
    assert (d.active, d.state, d.target, d.rate, d.drainThisMinute) == (False, 0, 100, 0, 0)
    assert d.starvedH == 0 and d.fedAgeH == 100.0                             # fed: the stamp at the minute
    assert D.take(d, 80.0) == 0
    bare = host.table({"body": {}})
    assert D.step(bare, 1.0, 100.0).active is False                         # a record missing its sub-tables


def test_each_state_starts_at_its_onset(host, D):
    cases = [
        (dict(unfed=30.0), 100.0, 1), (dict(vitC=(4, 0)), 100.0, 2), (dict(thiamine=(4, 10)), 100.0, 3),
        (dict(niacin=(4, 10)), 100.0, 4), (dict(na=111.9), 100.0, 5), (dict(dehyd=4.0), 100.0, 6),
        (dict(iron=3), 100.0, 7),
    ]
    rates = {1: 3.564 * 24, 2: 2400 / 2160, 3: 2400 / 840, 4: 2400 / 4320, 5: 400, 6: 17.82 * 24, 7: 100}
    for kw, age, code in cases:
        d = D.step(record(host, **kw), 1.0, age)
        assert d.active is True and d.state == code, kw
        assert d.rate == pytest.approx(rates[code], abs=1e-9)
        assert d.drainThisMinute == pytest.approx(rates[code] / 1440, abs=TOL)
        assert 0 < d.target <= 100 and d.mask == 2 ** (code - 1)
    under = [(dict(unfed=29.99), 100.0), (dict(vitC=(3, 9999)), 100.0), (dict(thiamine=(3, 9999)), 100.0),
             (dict(niacin=(3, 9999)), 100.0), (dict(na=112.0), 100.0), (dict(dehyd=3.99), 100.0), (dict(iron=2), 100.0)]
    for kw, age in under:
        assert D.step(record(host, **kw), 1.0, age).active is False, kw


def test_the_starving_and_dehydrated_flags_follow_their_states_whichever_fraction_wins(host, D):
    # Plan 15 Task 5: the writer lifts its HUNGER and THIRST caps on these flags (K.hybrid.caps), so each follows its
    # own state's onset, not the winning code
    d = D.step(record(host), 1.0, 100.0)
    assert (d.starving, d.dehydrated) == (False, False)
    d = D.step(record(host, unfed=30.0), 1.0, 100.0)
    assert (d.starving, d.starveAcute, d.dehydrated) == (True, True, False)   # the acute onset (Plan 15 Task 6)
    d = D.step(record(host, dehyd=4.0), 1.0, 100.0)
    assert (d.starving, d.dehydrated) == (False, True)
    assert D.step(record(host, dehyd=3.99), 1.0, 100.0).dehydrated is False
    d = D.step(record(host, unfed=30.0, dehyd=4.0, thiamine=(4, 800)), 1.0, 100.0)
    assert d.state == 3 and (d.starving, d.dehydrated) == (True, True)       # beriberi's fraction wins; both flags hold
    chronic = record(host, fm=12.9 * H2 - 52.02, inDay=1000.0)
    d = D.step(chronic, 1.0, 100.0)
    assert d.starving is True and d.starveAcute is False                     # the chronic-BMI onset counts too, not acute
    rec = record(host, dehyd=6.0)
    D.step(rec, 1.0, 100.0)
    rec.fluids.dehydPct = 1.0
    assert D.step(rec, 1.0, 100.0 + 1 / 60).dehydrated is False               # cleared with the state
    d = D.step(host.table({"body": {}}), 1.0, 100.0)
    assert d.starving is False and d.starveAcute is False                    # a record missing its sub-tables


def test_the_onset_bmi_is_stamped_once_and_cleared_when_starvation_ends(host, D):
    rec = record(host, unfed=48.0)
    d = D.step(rec, 1.0, 100.0)
    bmi0 = 62.02 / H2 - 4 * D.STARVE_DBMI                                     # T2-1: the estimate at the onset
    assert d.bmi0 == pytest.approx(bmi0, abs=TOL) and d.target == pytest.approx(100, abs=1e-9)
    rec.body.fm = 5.0
    D.step(rec, 1.0, 100.0 + 1 / 60)
    assert d.bmi0 == pytest.approx(bmi0, abs=TOL)                             # held while the state lasts
    assert d.target < 100 and d.stH == pytest.approx(2 / 60, abs=1e-12)
    rec.satiety.M = 400.0                                                     # a meal ends it (a meal spell, H1)
    D.step(rec, 1.0, 100.0 + 2 / 60)
    assert d.active is False and d.bmi0 == 0
    assert (d.stH, d.bClose, d.bRate, d.pS, d.pAt) == (0, 0, 0, 0, None)     # the starvation clocks released


def test_the_sodium_and_iron_hours_accumulate_and_reset(host, D):
    rec = record(host, na=100.0, iron=3)
    for _ in range(60):
        D.step(rec, 1.0, 100.0)
    d = rec.drain
    assert d.naH == pytest.approx(1.0, abs=1e-9) and d.feH == pytest.approx(1.0, abs=1e-9)
    assert d.state == 5 and d.target == pytest.approx(100 * (5 / 6) * (23 / 24), abs=1e-9)   # 1 h into each, multiplied
    rec.fluids.naPlasma = 140.0
    rec.nutrients.iron.x = 0
    D.step(rec, 1.0, 100.0)
    assert (d.naH, d.feH, d.active) == (0, 0, False)


def test_the_world_age_defaults_to_the_nutrients_clock(host, D):
    rec = record(host, unfed=36.0, lastAgeH=100.0)
    assert D.step(rec, 1.0, None).starvedH == 36
    assert rec.drain.active is True


def test_the_drain_scales_with_the_day_length_for_the_time_clock_curves_only(host, D):
    # ruling T2-2: Realistic's severity curves are fixed in game time, their cap vanilla's rate at the calibration's
    # 90-minute day; Vanilla and Shortened follow the server's day length; the lines are per game day whatever it is
    d = D.step(record(host, dehyd=8.0), 1.0, 100.0, False, opt(host, 3, 2, 60))
    assert d.rate == pytest.approx(17.82 * 24, abs=1e-9)
    for pace in (1, 2):
        d = D.step(record(host, dehyd=8.0), 1.0, 100.0, False, opt(host, pace, 2, 60))
        assert d.rate == pytest.approx(11.88 * 24, abs=1e-9)
    d = D.step(record(host, thiamine=(4, 1.0)), 1.0, 100.0, False, opt(host, 3, 2, 60))
    assert d.rate == pytest.approx(2400 / 840, abs=1e-9)


def test_realistic_dehydration_at_a_60_minute_day_keeps_health_on_the_target(host, D):
    # ruling T2-2: from the onset, the deficit rising at the calibration's rate, health within 1e-6 of the target for
    # the first 2 h
    with open(CALIBRATION, encoding="utf-8") as fh:
        dpdt = json.load(fh)["dehyd_dpdt_per_h"]
    rec = record(host, dehyd=4.0)
    health = 100.0
    for m in range(0, 120):
        rec.fluids.dehydPct = 4.0 + 11.0 * dpdt * m / 60
        d = D.step(rec, 1.0, 100.0 + m / 60, False, opt(host, 3, 2, 60))
        health -= D.take(d, health)
        assert abs(health - d.target) < 1e-6, m


# --- fix 1: the chronic-BMI onset (M3) ---------------------------------------------------------------------------

def test_a_bmi_under_13_is_starvation_whatever_the_days_intake(host, D):
    # BMI_CHRONIC: a low eater (6 kcal/kg today, no starved day) at BMI 12.9 starves; at 13.1 not
    assert D.BMI_CHRONIC == 13
    lm = 30.0
    fed = lambda bmi: record(host, inDay=6.0 * bmi * H2, lm=lm, fm=bmi * H2 - lm)
    d = D.step(fed(12.9), 1.0, 100.0)
    assert d.active is True and d.state == 1 and d.starvedH == 0
    assert d.bmi0 == pytest.approx(12.9 - 4 * D.STARVE_DBMI, abs=1e-9) and d.target == pytest.approx(100, abs=1e-9)
    assert D.step(fed(13.1), 1.0, 100.0).active is False
    rec = fed(12.9)
    D.step(rec, 1.0, 100.0)
    rec.body.fm = 12.45 * H2 - lm                                             # toward BMI 12, at a close
    rec.body.dayStartH = 120.0
    d = D.step(rec, 1.0, 120.0)
    p = (d.bmi0 - 12.45) / (d.bmi0 - 12)
    assert d.pS == pytest.approx(p, abs=1e-9)
    assert d.target == pytest.approx(100 * curve(p, 1.0, D.A_STARVE), abs=1e-9)


@pytest.mark.parametrize("body", sorted(FAST_DEATHS))
def test_a_water_only_fast_kills_the_default_body_and_a_90_kg_body_by_beriberi(host, body):
    """End to end (the Task 4 review's M2, Plan 15 Task 4b): the whole server pipeline (tools/replay_live.replay_arm),
    water only (1 L every 6 h, the guide's 4 L a day), until health reaches 0. Thiamine reaches the clinical grade at
    day 42 with none eaten, so wet beriberi kills at about day 77 (42 + 840 h). Plan 16 Task 5 (the deficit arm without
    the fat ceiling) keeps the lean, so neither body reaches BMI 12 first, and the 90 kg body's larger lean water need
    outran the old ration of 0.5 L every 6 h (a dehydration death at day 30.2): the ration rose to 4 L a day."""
    import os
    import sys
    tools = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))),
                         "tools")
    if tools not in sys.path:
        sys.path.insert(0, tools)
    import replay_live as RL
    weight, days, death_day, death_state = FAST_DEATHS[body]
    dtM = 1.0
    events = [{"minute": int(k * 360 / dtM), "kind": "drink", "fluid": "Water", "litres": 1.0} for k in range(days * 4)]
    paths = ["drain.state", "drain.target", "nutrients.thiamine.g"]
    deaths = []
    clinical = []
    orig = RL.ServerReplay.row

    def row(self, p):
        out = orig(self, p)
        st = self.p.st.body
        out["health"] = 100 - st.reduced + st.added
        return out
    RL.ServerReplay.row = row
    kw = {} if weight is None else {"player": {"weight": weight}}
    try:
        rows, _ = RL.replay_arm(events, minutes=int(days * 1440 / dtM), start_age=100.0, dtM=dtM, paths=paths, **kw)
    finally:
        RL.ServerReplay.row = orig
    t0 = rows[0]["age"] - dtM / 60
    for r in rows:
        if not clinical and r["nutrients.thiamine.g"] == 4:
            clinical.append((r["age"] - t0) / 24)
        if r["health"] <= 1e-6:
            deaths.append(((r["age"] - t0) / 24, r["drain.state"]))
            break
    assert deaths, "no death in %d days" % days
    day, state = deaths[0]
    assert state == death_state
    assert day == pytest.approx(death_day, abs=0.1)
    assert clinical[0] == pytest.approx(42, abs=0.01)    # both bodies: clinical at day 42 with none eaten


# --- Plan 15 Task 6 fix 1: the unfed hours and the trailing 72 h -----------------------------------------------------

def test_the_unfed_hours_count_across_a_record_day_with_no_reset(host, D):
    rec = record(host, unfed=0.0, at=23.5, day=0)
    assert D.step(rec, 1.0, 23.5).starvedH == 0
    rec.body.dayStartH = 24.0                                                  # the record day closes at 24
    d = D.step(rec, 1.0, 24.5)
    assert d.starvedH == pytest.approx(1.0, abs=TOL) and d.fedAgeH == 23.5
    rec.body.inDay = 10000.0                                                   # the day's intake no longer matters
    assert D.step(rec, 1.0, 26.0).starvedH == pytest.approx(2.5, abs=TOL)


def test_a_pool_at_fed_m_stamps_and_reads_0(host, D):
    rec = record(host, unfed=20.0)
    rec.satiety.M = host.K.hungerCurve.FED_M
    d = D.step(rec, 1.0, 100.0)
    assert d.starvedH == 0 and d.fedAgeH == 100.0
    rec.satiety.M = host.K.hungerCurve.FED_M * 0.999
    assert D.step(rec, 1.0, 101.0).starvedH == pytest.approx(1.0, abs=TOL)


def test_the_acute_onset_at_30_unfed_hours(host, D):
    assert D.STARVE_ONSET_H == 30
    assert D.step(record(host, unfed=29.99), 1.0, 100.0).starveAcute is False
    assert D.step(record(host, unfed=30.0), 1.0, 100.0).starveAcute is True


def test_first_sight_and_an_unseeded_pool_stamp_and_read_0(host, D):
    rec = record(host)
    rec.satiety = None
    d = D.step(rec, 1.0, 100.0)
    assert d.starvedH == 0 and d.fedAgeH == 100.0
    rec.satiety = host.table({})                                               # M not seeded yet
    assert D.step(rec, 1.0, 140.0).starvedH == 0
    assert D.unfedH(host.table({}), None, None) == 0                           # no clock: none
    assert D.unfedH(host.table({"fedAgeH": float("nan")}), host.table({"M": 0}), 50.0) == 0   # a bad stamp: first sight


def test_the_acute_clock_runs_on_through_a_snack_inside_the_state(host, D):
    rec = record(host, unfed=40.0)
    for m in range(60):
        d = D.step(rec, 1.0, 100.0 + m / 60)
    assert d.starveAcute is True and d.acuteH == pytest.approx(1.0, abs=1e-9)
    rec.satiety.M = 10.0                                                       # a floret: fed, but no meal spell (H1)
    d = D.step(rec, 1.0, 101.0)
    assert d.starveAcute is True and d.spell is False and d.starvedH > 40    # the unfed clock runs on
    rec.satiety.M = 400.0                                                      # a 200 kcal snack's pool or more
    d = D.step(rec, 1.0, 101.0 + 1 / 60)
    assert d.starveAcute is False and d.acuteH == 0 and d.starvedH == 0       # no recent window yet: the state ends


def days_record(h, today, closed, at=100.0):
    """A record with the recent intake laid: today's absorbed kcal and the three closed days (newest first)."""
    rec = record(h, unfed=0.0, at=at)
    rec.body.inDay = today
    rec.body.inDayClosed, rec.body.inDay2, rec.body.inDay3 = closed
    rec.body.recentDays = 3
    return rec


def test_the_recent_intake_is_today_and_three_closed_days(host, D):
    assert D.RECENT_MIN_KCAL == 600
    rec = days_record(host, 50.0, (100.0, 200.0, 250.0))
    assert D.recentKcal(rec.body) == 600.0
    stomach = host.table({"buffer": {"calories": 90.0}})
    assert D.recentKcal(rec.body, stomach) == 690.0                            # eaten, still in the stomach (fix 3)
    rec.body.recentDays = 2                                                    # fewer than three closes seen
    assert D.recentKcal(rec.body) is None
    rec.body.recentDays = 3
    rec.body.inDay3 = None
    assert D.recentKcal(rec.body) is None
    body = host.table({"inDay": 7.0, "inDayClosed": 1.0, "inDay2": 2.0, "inDay3": 3.0})
    D.closeDay(body)
    assert (body.inDayClosed, body.inDay2, body.inDay3, body.recentDays) == (7.0, 1.0, 2.0, 1)
    D.closeDay(body)
    D.closeDay(body)
    D.closeDay(body)
    assert body.recentDays == 3                                                # counted up to RECENT_DAYS


def test_600_kcal_counts_as_low_within_the_tolerance(host, D):
    rec = days_record(host, 0.0, (200.0, 200.0, 200.0000000030673))            # three absorbed snacks, as live
    rec.satiety.M = 0.0
    assert D.step(rec, 1.0, 100.0).starveAcute is True
    rec.body.inDay3 = 200.00001
    assert D.step(rec, 1.0, 100.0 + 1 / 60).starveAcute is False


def test_a_body_loaded_before_its_third_close_counts_no_phantom_day(host, D):
    # re-review L2: K.store.closeDefault reads a loaded body's missing closed day as the resting expenditure; that
    # value rotates down, but the window waits for three closes the body itself made
    rec = days_record(host, 0.0, (None, None, None))
    rec.body.recentDays = None
    host.K.store.closeDefault(rec)
    assert rec.body.inDayClosed > 1000                                         # the default resting day
    for _ in range(2):
        D.closeDay(rec.body)
        assert D.recentKcal(rec.body) is None
    D.closeDay(rec.body)
    assert D.recentKcal(rec.body) == 0.0                                       # the default has rotated out


def test_low_recent_intake_holds_the_acute_state_only_while_unfed(host, D):
    rec = days_record(host, 0.0, (200.0, 200.0, 200.0))
    rec.satiety.M = 0.0
    d = D.step(rec, 1.0, 100.0)
    assert d.starveAcute is True and d.recentKcal == 600.0                    # 600 or less, unfed: acute
    rec.satiety.M = 10.0                                                       # a floret: no meal spell (H1)
    d = D.step(rec, 1.0, 100.0 + 0.5 / 60)
    assert d.starveAcute is True                                               # the fallback holds
    rec.satiety.M = 400.0                                                      # a snack: a meal spell
    d = D.step(rec, 1.0, 100.0 + 1 / 60)
    assert d.starveAcute is False and d.starving is False                      # the moodle minimum lifts at once
    assert d.acuteH > 0 and d.bmi0 > 0                                         # the clock and the onset BMI wait
    rec.satiety.M = 0.0
    d = D.step(rec, 1.0, 100.0 + 2 / 60)
    assert d.starveAcute is True and d.starvedH >= 30                          # back, the phases not reset
    rec.body.inDayClosed = 201.0                                               # over 600: the fallback clears
    rec.satiety.M = 400.0
    d = D.step(rec, 1.0, 100.0 + 3 / 60)
    assert d.starveAcute is False and d.acuteH == 0 and d.bmi0 == 0


def test_a_200_kcal_snack_every_33_h_still_enters_the_acute_state(host, D):
    # the controller's rulings on the review's weak spot: a snack resets the unfed clock, but today and the three closed
    # record days holding 600 kcal or less (about 200 kcal a day; up to three such snacks, 600) hold the acute onset
    # whenever the pool is unfed again; a fed spell after each snack lifts it for its few hours only
    rec = days_record(host, 0.0, (None, None, None))
    rec.body.inDayClosed = None
    acute, unfed_hours, fed_hours = [], 0, 0
    M = 0.0
    for hour in range(0, 24 * 10):
        a = 100.0 + hour
        if hour > 0 and hour % 24 == 0:
            D.closeDay(rec.body)
            rec.body.inDay = 0.0
        if hour % 33 == 0:
            rec.body.inDay = rec.body.inDay + 200.0
            M = 400.0
        rec.satiety.M = M
        d = D.step(rec, 60.0, a)
        M = M * 0.5 ** (1 / 0.583749)                                          # the pool clears (MEAL_HALF_LIFE_H)
        if hour >= 96:
            assert d.recentKcal <= 600
            if rec.satiety.M < host.K.hungerCurve.FED_M:
                unfed_hours += 1
                acute.append(d.starveAcute)
            else:
                fed_hours += 1
                assert d.starveAcute is False
    assert all(acute) and len(acute) > 100 and fed_hours > 0
    assert d.bmi0 > 0                                                          # the onset BMI held through the snacks


def test_an_offline_gap_neither_counts_as_unfed_nor_moves_the_window(host, D):
    # Plan 15 Task 6 fix 2 (re-review H1), under Plan 16 Task 2's freeze: a 200 h logout 5 h after the pool emptied
    # comes back exactly 5 h unfed (the resume moves drain.fedAgeH by the whole gap; until Plan 16 the return
    # integrated one hour and read 6)
    rec = record(host, unfed=5.0, at=100.0)
    rec.body.inDayClosed, rec.body.inDay2, rec.body.inDay3 = 2000.0, 2000.0, 2000.0
    rec.body.recentDays = 3
    rec.acute = host.K.acute.new(90.0)
    rec.acute.lastFedAgeH, rec.acute.lastVigAgeH = 95.0, 95.0                  # the adapter lays these
    assert host.K.resume.resume(rec, 300.0) == 200.0                           # the last step: nutrients.lastAgeH 100
    d = D.step(rec, 1.0, 300.0)
    assert d.starvedH == pytest.approx(5.0, abs=1e-9) and d.starveAcute is False
    assert D.starvePhase(d.starvedH) == 0
    assert d.recentKcal == 6000.0                                              # the record days did not move


def test_a_stamp_ahead_of_the_clock_heals_to_the_minute(host, D):
    rec = record(host, unfed=0.0, at=500.0)
    rec.satiety.M = 0.0
    d = D.step(rec, 1.0, 100.0)
    assert d.fedAgeH == 100.0 and d.starvedH == 0


def test_the_clocks_survive_a_restart(host, D):
    rec = record(host, unfed=40.0)
    D.step(rec, 1.0, 100.0)
    saved = host.py(host.K.store.inputsOnly(rec))["drain"]                     # what a save keeps
    assert set(saved) == {"bmi0", "naH", "feH", "fedAgeH", "acuteH", "spell", "stH", "dhH", "bClose", "bRate", "pAt",
                          "pS"}                                                # Plan 17 Task 2: the state hours and the BMI clock
    assert saved["fedAgeH"] == 60.0
    rec.body.inDay2, rec.body.inDay3 = 1.0, 2.0
    body = host.py(host.K.store.inputsOnly(rec))["body"]
    assert body["inDay2"] == 1.0 and body["inDay3"] == 2.0
    rec.body.recentDays = 3
    assert host.py(host.K.store.inputsOnly(rec))["body"]["recentDays"] == 3


# --- Plan 15 close, H1: only a meal spell suspends the fallback or ends the state ---------------------------------

def test_the_meal_spell_opens_at_suspend_m_and_closes_under_fed_m(host, D):
    assert D.SUSPEND_M == 236.44
    d = host.table({"spell": False})
    D.spellStep(d, D.SUSPEND_M - 1e-6)
    assert d.spell is False and D.mealFed(d, 200.0) is False                   # fed, but not a meal spell
    D.spellStep(d, D.SUSPEND_M)
    assert d.spell is True and D.mealFed(d, D.SUSPEND_M) is True
    D.spellStep(d, host.K.hungerCurve.FED_M)                                   # held down to FED_M
    assert d.spell is True and D.mealFed(d, host.K.hungerCurve.FED_M) is True
    D.spellStep(d, host.K.hungerCurve.FED_M * 0.999)
    assert d.spell is False
    D.spellStep(d, float("nan"))
    assert d.spell is False and D.mealFed(d, float("nan")) is False


def test_a_200_kcal_mixed_snack_lands_suspend_m(host, D):
    v = host.table({"proteins": 200 * 0.15 / 4, "carbs": 200 * 0.5 / 4, "lipids": 200 * 0.35 / 9, "calories": 200.0})
    assert host.K.satiety.weigh(v) == pytest.approx(D.SUSPEND_M, abs=0.005)


def test_a_corrupt_spell_heals_to_false(host, D):
    rec = record(host, unfed=5.0)
    rec.drain.spell = 3
    D.ensure(rec)
    assert rec.drain.spell is False


def test_a_floret_every_hour_after_a_3_day_fast_keeps_the_state_through_the_pipeline():
    # close-review H1: one Base.Broccoli (11.02 kcal) an hour holds the pool at FED_M or more for about 70 min, so with
    # the curve's fed threshold as the suspension the state never ran; the intake (264 kcal a day) is over the
    # fallback's window, so only the meal spell keeps the state the fast opened
    import os
    import sys
    tools = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))),
                         "tools")
    if tools not in sys.path:
        sys.path.insert(0, tools)
    import fit_hunger_curve as F
    import replay_live as RL
    day = F.DAY
    n = 10 * day
    ev = F.water(10) + [{"minute": m, "kind": "meal", "size": 11.02, "plate": ["Base.Broccoli"]}
                        for m in range(3 * day, n, 60)]
    be = RL.ServerReplay(hour_offset=F.HOUR_OFFSET, rng="half", sleep_allowed=False)
    rows = RL.run(be, RL.synthetic_ages(n), sorted(ev, key=lambda e: e["minute"]),
                  list(F.PATHS) + ["drain.active", "drain.recentKcal"], start_age=0.0)
    after = rows[3 * day:8 * day]                                              # days 3-7 (the controller's ruling)
    assert max(r["satiety.M"] for r in after) >= be.K.hungerCurve.FED_M        # each floret feeds the curve
    assert max(r["drain.recentKcal"] for r in after) > 600                     # over the fallback's window
    share = sum(1 for r in after if r["drain.starving"] and r["drain.active"]) / len(after)
    assert share >= 0.9


# --- Plan 15 close, ruling M2: Overlay runs no starvation or dehydration state ------------------------------------

def test_overlay_leaves_out_starvation_and_dehydration_and_keeps_the_rest(host, D):
    rec = record(host, unfed=40.0, dehyd=8.0, vitC=(4, 10.0))
    d = D.step(rec, 1.0, 100.0, True)
    assert d.starving is False and d.dehydrated is False                       # vanilla owns them in Mode 2
    assert d.starveAcute is True and d.starvedH >= 40 and d.bmi0 == 0           # the clock runs, no onset BMI
    assert d.active is True and d.state == D.SCURVY and d.mask == 2             # the deficiency drain still runs
    d = D.step(rec, 1.0, 100.0 + 1 / 60, False)
    assert d.starving is True and d.dehydrated is True and d.mask == 1 + 2 + 32
