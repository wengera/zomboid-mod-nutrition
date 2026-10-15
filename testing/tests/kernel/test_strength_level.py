"""The strength-level reference (Plan 13 Task 2b, ruling 13-45): R, the trait starts, the neural factor and the
verified perfect-training table of spec section 2.4, at the plan's tolerances first, then the run pinned to 1e-9."""
import math
import pytest
from . import strength_level as sl

MARKS = (28, 70, 182, 365, 730, 1460, 3650)
TABLE = {  # shown level at MARKS under perfect training, and the cap (Fc at Tmax); Stout and Strong at Kouri's 6.3
    # (Task 11c, regain integrated exactly: Feeble's day 70 reads 4.3648, so 4.36; spec section 2.4 printed 4.37)
    "none":   ((5.91, 6.49, 7.33, 8.25, 9.26, 10.00, 10.51), 10.78),
    "STOUT":  ((8.01, 8.57, 9.28, 10.06, 10.92, 11.59, 12.08), 12.34),
    "STRONG": ((10.09, 10.59, 11.10, 11.64, 12.25, 12.76, 13.17), 13.40),
    "FEEBLE": ((3.79, 4.36, 5.29, 6.30, 7.39, 8.17, 8.67), 8.93),
    "WEAK":   ((1.85, 2.42, 3.37, 4.41, 5.51, 6.28, 6.76), 6.99),
}


def test_R_reads_the_years():
    assert abs(sl.R_of(4.0) - 1.5651015746939971) < 1e-12
    assert abs(sl.R_of(2.0) - 1.4814209731145318) < 1e-12


def test_the_average_is_level_5_exactly():
    assert sl.S_of(sl.F5, 1.0, 1.0) == 1.0
    assert abs(sl.level(sl.F5, 1.0, 1.0) - 5.0) < 1e-12


@pytest.mark.parametrize("trait, F, F0, Fc", [
    ("none", 52.020, 52.020, 68.6375),
    ("STOUT", 56.661, 54.341, 70.429),   # clamped (70.958 before ruling 13-47)
    ("STRONG", 60.857, 56.438, 70.429),  # clamped (73.056 before ruling 13-47)
    ("FEEBLE", 47.296, 49.658, 66.275),
    ("WEAK", 42.115, 47.068, 63.685),
])
def test_trait_starts(trait, F, F0, Fc):
    s = sl.trait_start(trait)
    assert abs(s[0] - F) < 5e-4 and abs(s[1] - F0) < 5e-4 and abs(s[2] - Fc) < 5e-4
    assert s[3] == max(s[0], s[1])


def test_each_start_floors_to_its_own_level():
    for t, L in sl.LEVEL_MODEL["startLevel"].items():
        x = sl.level(sl.trait_start(t)[0], sl.LEVEL_MODEL["N0"][t], 1.0)
        assert math.floor(x + 1e-9) == L


@pytest.mark.parametrize("trait", list(TABLE))
def test_perfect_training_table(trait):
    levels = sl.perfect_run(trait, MARKS[-1])
    for day, want in zip(MARKS, TABLE[trait][0]):
        assert abs(levels[day - 1] - want) <= 0.005, (trait, day)
    F, F0, Fc, Pk = sl.trait_start(trait)
    cap = sl.level(Fc, sl.LEVEL_MODEL["N0"][trait], sl.LEVEL_MODEL["Tmax"])
    assert abs(cap - TABLE[trait][1]) <= 0.005


def test_the_neural_rise_grace_and_decay():
    T, g = 1.0, 0
    for _ in range(28):
        T, g = sl.neural_day(T, g, 20.0)
    assert abs(T - (1.1 - 0.1 * math.exp(-28 / 21))) < 1e-12
    T0 = T
    for _ in range(21):
        T, g = sl.neural_day(T, g, 0.0)
    # bitwise: Tmax - T is exact by Sterbenz's lemma, so Tmax - (Tmax - T) * exp(0) is exactly the representable T
    assert T == T0
    for _ in range(84):
        T, g = sl.neural_day(T, g, 0.0)
    assert abs((T - 1) / (T0 - 1) - math.exp(-1.0)) < 1e-12


def test_the_neural_signal_saturates_at_Wsat_and_counts_below_m_Wsat():
    # half the saturating signal rises at half the rate; the grace counter counts days below m * Wsat (5/3 sets)
    T, g = 1.0, 0
    for _ in range(7):
        T, g = sl.neural_day(T, g, 2.5)
    assert abs(T - (1.1 - 0.1 * math.exp(-0.5 * 7 / 21))) < 1e-12
    assert g == 0
    assert sl.neural_day(T, 5, 1.6)[1] == 6
    assert sl.neural_day(T, 5, 1.7)[1] == 0
    assert sl.neural_day(T, 5, sl.strength_model.POINT_T["m"] * sl.LEVEL_MODEL["Wsat"])[1] == 0
    # past the grace, a day below the threshold decays T and never raises it
    T1, g1 = sl.neural_day(1.05, 21, 1.6)
    assert g1 == 22 and abs(T1 - (1 + 0.05 * math.exp(-1 / 84))) < 1e-12
    # the biology clock divides the grace and scales the day
    T2, g2 = sl.neural_day(1.05, 11, 0.0, ts=2.0)
    assert g2 == 12 and abs(T2 - (1 + 0.05 * math.exp(-2 / 84))) < 1e-12
    T3, g3 = sl.neural_day(1.0, 0, 20.0, ts=2.0)
    assert g3 == 0 and abs(T3 - (1.1 - 0.1 * math.exp(-2 / 21))) < 1e-12


# The run pinned (Task 2b Step 4): per trait the start (F, F0, Fc, Pk), the shown level at MARKS and the cap, read off
# strength_level at its commit, so a later kernel or reference change that moves one is named. The perk (the floor of
# L + 1e-9) reaches 10 on day 25 for Strong, 348 for Stout and 1460 for the average (Kouri's 6.3; 24 and 346 at the
# plan's 6.1; the average's level is 9.999999999999972 on day 1460, so the epsilon floors it to 10 there, not 1461).
# Task 11c (regain integrated exactly, Task 11 review I-2) re-pinned Feeble's and Weak's marks: both start below their
# set point, so Pk = F0 > F and the regain arm runs; the starts, the caps and the other three traits did not move.
PINS = {
    "none": ((52.019999999999996, 52.019999999999996, 68.63749999999999, 52.019999999999996),
             (5.914866664738792, 6.489325095514365, 7.329083967899694, 8.251566815917508, 9.25959681120353,
              9.999999999999972, 10.514954966977193), 10.780339412084205),
    "STOUT": ((56.66119618774994, 54.340598093874966, 70.4293, 56.66119618774994),
              (8.014629782167917, 8.568809961967647, 9.27935346914515, 10.059975758233968, 10.919738785854552,
               11.585131559115801, 12.076201337494084), 12.340896936205269),
    "STRONG": ((60.85672078038634, 56.43836039019317, 70.4293, 60.85672078038634),
               (10.091002627525707, 10.5912219146116, 11.097165682296666, 11.640857920285434, 12.24710002542624,
                12.757069392540332, 13.165322673051223), 13.399981482992372),
    "FEEBLE": ((47.29591525798105, 49.65795762899052, 66.27545762899052, 49.65795762899052),
               (3.7940841625896202, 4.364801060394077, 5.290286549825111, 6.302471383810081, 7.394541908417363,
                8.165740227277375, 8.674076397010245), 8.925960004960753),
    "WEAK": ((42.115244731130076, 47.067622365565036, 63.68512236556503, 47.067622365565036),
             (1.8502304430344552, 2.416974737534753, 3.3675609933157054, 4.406949504355513, 5.5137383162164495,
              6.275806450836546, 6.758826354983146), 6.9916057307013055),
}


def test_the_natural_limit():
    assert sl.KOURI_COEF == 6.3   # Kouri 1995 (PMID 7496846)
    assert abs(sl.FFMI_NATURAL_RAW - 24.37) < 1e-9
    assert abs(sl.FC_LIMIT - 70.4293) < 1e-9


@pytest.mark.parametrize("trait", list(PINS))
def test_the_run_is_pinned(trait):
    start, marks, cap = PINS[trait]
    s = sl.trait_start(trait)
    for got, want in zip(s, start):
        assert abs(got - want) < 1e-9, (trait, "start")
    levels = sl.perfect_run(trait, MARKS[-1])
    for day, want in zip(MARKS, marks):
        assert abs(levels[day - 1] - want) < 1e-9, (trait, day)
    got = sl.level(s[2], sl.LEVEL_MODEL["N0"][trait], sl.LEVEL_MODEL["Tmax"])
    assert abs(got - cap) < 1e-9, (trait, "cap")


@pytest.mark.parametrize("trait, day", [("STRONG", 25), ("STOUT", 348), ("none", 1460), ("FEEBLE", None),
                                        ("WEAK", None)])
def test_the_day_the_perk_reaches_10(trait, day):
    levels = sl.perfect_run(trait, MARKS[-1])
    first = next((i + 1 for i, x in enumerate(levels) if math.floor(x + 1e-9) >= 10), None)
    assert first == day


def test_the_floor_below_Fnm():
    R = sl.R_of(4.0)
    assert sl.S_of(sl.LEVEL_MODEL["Fnm"], 1.0, 1.0) == 0.0
    assert sl.S_of(20.0, 1.14, 1.1) == 0.0
    assert abs(sl.level(20.0, 1.0, 1.0) - (5.0 - 5.0 / (R - 1.0))) < 1e-12
    assert abs(sl.level(20.0, 1.0, 1.0) - (-3.85)) < 0.005   # spec 2.1
    assert sl.F_of_level(-5.0, 1.0, 1.0) == sl.LEVEL_MODEL["Fnm"]


def test_trait_start_takes_a_profession_boost_like_a_small_trait():
    # Task 17b: the start level is the pick's plus the boost, clamped to [0, 10]; the boost adds no innate factor
    assert sl.start_level("STRONG", 1) == sl.start_level("STRONG", 2) == 10
    assert sl.start_level("none", 1) == 6 and sl.start_level("WEAK", -3) == 0
    assert sl.trait_start("STOUT", prof=0) == sl.trait_start("STOUT")
    F = sl.trait_start("none", prof=1)[0]
    assert abs(sl.level(F, 1.0, 1.0) - 6.0) < 1e-9
    F = sl.trait_start("STOUT", prof=1)[0]
    assert abs(sl.level(F, sl.LEVEL_MODEL["N0"]["STOUT"], 1.0) - 8.0) < 1e-9
