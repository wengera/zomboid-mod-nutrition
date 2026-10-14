"""The strength-level reference (Plan 13 Task 2b, ruling 13-45): R, the trait starts, the neural factor and the
verified perfect-training table of spec section 2.4, at the plan's tolerances first, then the run pinned to 1e-9."""
import math
import pytest
from . import strength_level as sl

MARKS = (28, 70, 182, 365, 730, 1460, 3650)
TABLE = {  # shown level at MARKS under perfect training, and the cap (Fc at Tmax)
    "none":   ((5.91, 6.49, 7.33, 8.25, 9.26, 10.00, 10.51), 10.78),
    "STOUT":  ((8.02, 8.57, 9.28, 10.07, 10.93, 11.60, 12.09), 12.36),
    "STRONG": ((10.09, 10.59, 11.10, 11.65, 12.26, 12.77, 13.18), 13.42),
    "FEEBLE": ((3.79, 4.37, 5.29, 6.30, 7.39, 8.17, 8.67), 8.93),
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
    ("STOUT", 56.661, 54.341, 70.487),   # clamped (70.958 before ruling 13-47)
    ("STRONG", 60.857, 56.438, 70.487),  # clamped (73.056 before ruling 13-47)
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
    # past the grace, a day below the threshold decays T and never raises it
    T1, g1 = sl.neural_day(1.05, 21, 1.6)
    assert g1 == 22 and abs(T1 - (1 + 0.05 * math.exp(-1 / 84))) < 1e-12
    # the biology clock divides the grace and scales the day
    T2, g2 = sl.neural_day(1.05, 11, 0.0, ts=2.0)
    assert g2 == 12 and abs(T2 - (1 + 0.05 * math.exp(-2 / 84))) < 1e-12
    T3, g3 = sl.neural_day(1.0, 0, 20.0, ts=2.0)
    assert g3 == 0 and abs(T3 - (1.1 - 0.1 * math.exp(-2 / 21))) < 1e-12


# The run pinned (Task 2b Step 4): per trait the start (F, F0, Fc, Pk), the shown level at MARKS and the cap, read off
# strength_level at its commit, so a later kernel or reference change that moves one is named. Strong reaches level 10
# on day 24, Stout on day 346 and the average on day 1461 (spec section 2.4).
PINS = {
    "none": ((52.019999999999996, 52.019999999999996, 68.63749999999999, 52.019999999999996),
             (5.914866664738792, 6.489325095514365, 7.329083967899694, 8.251566815917508, 9.25959681120353,
              9.999999999999972, 10.514954966977193), 10.780339412084205),
    "STOUT": ((56.66119618774994, 54.340598093874966, 70.4871, 56.66119618774994),
              (8.01557372064922, 8.571086688049233, 9.284505860388345, 10.068387231482813, 10.931697196198186,
               11.599670102666442, 12.092523474026539), 12.358131233948914),
    "STRONG": ((60.85672078038634, 56.43836039019317, 70.4871, 60.85672078038634),
               (10.091970524415503, 10.593562957963837, 11.102496281327436, 11.649706177713433, 12.259701300397108,
                12.772471418415146, 13.182686706247598), 13.4183432581585),
    "FEEBLE": ((47.29591525798105, 49.65795762899052, 66.27545762899052, 49.65795762899052),
               (3.794417305455324, 4.365110583340395, 5.2905166934851255, 6.302618137722927, 7.394605917378753,
                8.16575930291771, 8.674079459340815), 8.925960004960753),
    "WEAK": ((42.115244731130076, 47.067622365565036, 63.68512236556503, 47.067622365565036),
             (1.8534298209899336, 2.4206927017413076, 3.370362190401066, 4.408708473297587, 5.514497774278342,
              6.276023364913936, 6.758859987112048), 6.9916057307013055),
}


def test_the_natural_limit():
    assert abs(sl.FFMI_NATURAL_RAW - 24.39) < 1e-9
    assert abs(sl.FC_LIMIT - 70.4871) < 1e-9


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
