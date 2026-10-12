"""Satiety from physiology (Plan 11c Task 3; spec § 3.1 and § 5a; the meal pool M, Plan 11g Task 6c, spec § 7):
K.satiety.fill, fullness, weigh, mealFeed, mealClear, drain, mealRead, sated, target, seedMeal, discomfort and circadian,
K.stomach.satietyMass and K.hybrid.DEFICIT_FLOOR, on the kernel host. Hand-computed from the constants; the oracle
(test_satiety_meal_studies.py) replays the studies. The physical fill is read against K.stomach.CAPACITY_MAX_G (ruling
11c-19) and the satiety F counted up to K.stomach.CAPACITY_HARD_G; the circadian term is ruling 11c-24's. Structure D
(spec § 5b, ruling 11c-30, Plan 11c Task 4), its pool P replaced by the gut stage G in Plan 11g Task 4 and G by the meal
pool M (fed at the eat) in Task 6c: the read mealRead(M) = 1 - 1 / (1 + 3 (M / MEAL_REQ)^MEAL_STEEP), seedMeal its
inverse capped at MEAL_SEED_MAX, and the satiety mass weighting drunk liquid at LIQUID_WEIGHT."""
import math
import os
import re

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
SHARED = os.path.join(REPO, "mod", "NutritionRevamp", "common", "media", "lua", "shared")
NAMES = ("W_PROTEIN", "W_CARB", "W_FAT", "W_NEUTRAL", "MEAL_HALF_LIFE_H", "MEAL_REQ", "MEAL_STEEP", "FULL_WEIGHT",
         "LIQUID_WEIGHT", "MEAL_SEED_MAX", "DISCOMFORT_MAX", "ATWATER_P", "ATWATER_C", "ATWATER_F", "CIRCADIAN_A", "CIRCADIAN_PEAK_H",
         "PROTEIN_FILL")
# the joint fit's constants (Plan 11g Task 6c, tools/fit_gut_satiety.py, fit-11g-20261012b), each at the value the fit chose
FIT = {"FULL_WEIGHT": 0.5, "MEAL_HALF_LIFE_H": 0.6, "MEAL_REQ": 4.47214, "MEAL_STEEP": 0.0559017, "LIQUID_WEIGHT": 0.0151122,
       "PROTEIN_FILL": 8, "W_FAT": 0.894427, "W_PROTEIN": 2.5}


def _vec(host, **kw):
    v = host.K.vector["new"]()
    for k, val in kw.items():
        v[k] = val
    return v


def test_the_constants(host):
    S = host.K.satiety
    assert {k: S[k] for k in FIT} == FIT
    assert (S.W_CARB, S.W_NEUTRAL) == (1, 1)
    assert (S.MEAL_SEED_MAX, S.DISCOMFORT_MAX) == (1190, 100)
    assert S.P50 is None and S.PN_MAX is None                        # retired by structure D (ruling 11c-30)
    for gone in ("P_REQ", "HALF_LIFE_H", "P_SEED_MAX", "STEEP", "feed", "decay", "post", "seedP"):
        assert S[gone] is None, gone                                 # the meal pool P, retired in Plan 11g Task 4
    assert (S.ATWATER_P, S.ATWATER_C, S.ATWATER_F) == (4, 4, 9)
    assert (S.CIRCADIAN_A, S.CIRCADIAN_PEAK_H) == (0.085, 19.8333)
    assert host.K.hybrid.DEFICIT_FLOOR == 0.02                       # refit, Plan 11f Task 2c fix 1 (ruling 2b-3, widened search); 0 from Task 2c, 1.0 from Plan 11d Task 9d


def test_each_constant_names_its_row_or_its_label():
    with open(os.path.join(SHARED, "NR_Kernel_Satiety.lua"), encoding="utf-8") as fh:
        src = fh.read()
    for name in NAMES:
        line = re.search(r"^K\.satiety\.%s = .*$" % name, src, re.M).group(0)
        assert re.search(r"S\d{4}|game choice|neutral|CharacterStat", line), name
    assert "provisional" not in src.lower()                             # Plan 11g Task 6: every constant labelled
    for name in FIT:
        line = re.search(r"^K\.satiety\.%s = .*$" % name, src, re.M).group(0)
        assert "game choice, fitted in Plan 11g Task 6c against S" in line, name    # the label the brief sets
        assert "(tools/fit_gut_satiety.py, fit-11g-20261012b)" in line, name        # the fit and its artifact
        assert len(re.findall(r"S\d{4}", line)) >= 2, name                          # the rows that bound it
    for name in ("W_PROTEIN", "W_FAT", "MEAL_HALF_LIFE_H", "MEAL_REQ", "MEAL_STEEP"):
        line = re.search(r"^K\.satiety\.%s = .*$" % name, src, re.M).group(0)
        assert re.search(r"S12(68|70) open", line), name                 # an open row is named open, never as evidence
    line = re.search(r"^K\.satiety\.MEAL_SEED_MAX = .*$", src, re.M).group(0)
    assert "game choice (ruling 11c-30; re-derived in Plan 11g Task 6c)" in line and "0.196" in line
    for name in ("CIRCADIAN_A", "CIRCADIAN_PEAK_H"):
        line = re.search(r"^K\.satiety\.%s = .*$" % name, src, re.M).group(0)
        assert "S1273" in line, name                                     # Scheer 2013, minted as S1273
    with open(os.path.join(SHARED, "NR_Kernel_Hybrid.lua"), encoding="utf-8") as fh:
        hyb = fh.read()
    line = re.search(r"^K\.hybrid\.DEFICIT_FLOOR = .*$", hyb, re.M).group(0)
    assert "game choice, refit on the shipped pipeline against Karl 2021 as reported (Plan 11f ruling 2b-3, widened search)" in line
    assert "S1271 open" in line and "S1254" in line
    assert all(s in line for s in ("S1613", "S1614", "S1255", "S1325")), line   # the rows it was fitted to


def test_fill_is_mass_over_the_maximal_capacity_clamped(host):
    cap = host.K.stomach.CAPACITY_MAX_G
    assert cap == 730
    assert host.call("satiety.fill", 365, cap) == 0.5
    assert host.call("satiety.fill", 900, cap) == 1
    assert host.call("satiety.fill", -5, cap) == 0


def test_weigh_splits_the_calories_by_atwater_share(host):
    v = _vec(host, calories=400, proteins=25, carbs=50, lipids=200 / 9)      # 100, 200 and 200 kcal by Atwater
    S = host.K.satiety
    assert host.call("satiety.weigh", v) == pytest.approx(400 * (S.W_PROTEIN * 100 + 200 + S.W_FAT * 200) / 500)


def test_the_delivered_calories_govern_the_energy(host):
    # macros summing to 500 kcal by Atwater on a vector that delivered 250 kcal: weighed at 250 (spec § 3.2)
    v = _vec(host, calories=250, proteins=25, carbs=50, lipids=200 / 9)
    S = host.K.satiety
    assert host.call("satiety.weigh", v) == pytest.approx(250 * (S.W_PROTEIN * 100 + 200 + S.W_FAT * 200) / 500)


def test_a_vector_with_no_macros_takes_the_neutral_weight(host):
    assert host.call("satiety.weigh", _vec(host, calories=120)) == 120
    assert host.call("satiety.weigh", _vec(host)) == 0


def test_meal_feed_adds_the_weighted_kcal_of_what_was_eaten(host):
    v = _vec(host, calories=100, proteins=0, carbs=25, lipids=0)
    assert host.call("satiety.mealFeed", 10.0, v) == 10.0 + host.call("satiety.weigh", v)
    assert host.call("satiety.mealFeed", 50, _vec(host, calories=100, carbs=25)) == pytest.approx(150)
    assert host.call("satiety.mealFeed", 50, _vec(host, calories=40, proteins=10)) == pytest.approx(
        50 + 40 * host.K.satiety.W_PROTEIN)                                                            # W_PROTEIN
    assert host.call("satiety.mealFeed", 7, _vec(host)) == 7                                              # nothing eaten


def test_meal_clears_first_order_at_its_half_life(host):
    hl = host.K.satiety.MEAL_HALF_LIFE_H
    assert abs(host.call("satiety.mealClear", 8.0, hl, 1) - 4.0) < 1e-9
    assert host.call("satiety.mealClear", 8.0, 0, 1) == 8.0
    assert host.call("satiety.mealClear", 8.0, -1, 1) == 8.0
    assert host.call("satiety.mealClear", 80, 2 * hl, 1) == pytest.approx(20)
    assert host.call("satiety.mealClear", 80, hl, 1.5) == pytest.approx(80 * 2 ** -1.5)   # the trait scales the clearance


def test_the_step_api_is_gone(host):
    # Plan 11g Task 6c: K.satiety.drain only clears M (the eat feeds it), so the feed-then-clear step is retired
    assert host.K.satiety.mealStep is None and host.K.satiety.gStep is None and host.K.satiety.gFeed is None


def test_drain_steps_the_stomach_and_clears_m_in_one_minute_substeps(host):
    # Plan 11g Task 6 (KIN.drain's loop moved to the kernel so the stand-ins share it), Task 6c: a 3-minute drain is
    # three one-minute drains, M cleared on each and fed by none; a sub-minute or zero step is one substep; no pool
    # leaves M alone
    meal = _vec(host, calories=600, proteins=22.5, carbs=75, lipids=23.3, water=300)
    run = host.rt.eval("""function(meal, steps, withPool)
        local K = NutritionRevamp.kernel
        local st = K.stomach.new()
        K.stomach.ingest(st, meal)
        local pool = nil
        if withPool then pool = { M = 40, trait = 1.5 } end
        local kcal = 0
        for i = 1, #steps do kcal = kcal + K.satiety.drain(st, steps[i], pool).calories end
        local M = nil
        if pool ~= nil then M = pool.M end
        return M, kcal, st.buffer.calories
    end""")
    m3, k3, b3 = run(meal, host.rt.table(*([3.0] * 20)), True)
    m1, k1, b1 = run(meal, host.rt.table(*([1.0] * 60)), True)
    assert m3 == pytest.approx(m1, rel=1e-12) and k3 == pytest.approx(k1, rel=1e-12) and b3 == pytest.approx(b1, rel=1e-12)
    assert m1 == pytest.approx(host.call("satiety.mealClear", 40, 1.0, 1.5), rel=1e-12)    # an hour's clearance, no feed
    m0, k0, _ = run(meal, host.rt.table(0.0, 0.5, 1.0 + 1e-7), True)
    assert k0 > 0 and 0 < m0 < 40
    none, kn, bn = run(meal, host.rt.table(*([1.0] * 60)), False)
    assert none is None and kn == pytest.approx(k1, rel=1e-12) and bn == pytest.approx(b1, rel=1e-12)


def test_meal_clear_reads_the_named_half_life(host):
    S = host.K.satiety
    old = S.MEAL_HALF_LIFE_H
    S.MEAL_HALF_LIFE_H = 2.0
    try:
        assert host.call("satiety.mealClear", 80, 2.0, 1) == pytest.approx(40)
    finally:
        S.MEAL_HALF_LIFE_H = old                                    # the saved value, so a mutated constant survives
    assert host.call("satiety.mealClear", 80, old, 1) == pytest.approx(40)


def test_meal_read_is_the_request_level_at_g_req_on_an_empty_stomach(host):
    greq = host.K.satiety.MEAL_REQ
    assert abs(host.call("satiety.mealRead", greq) - 0.75) < 1e-9
    assert host.call("satiety.mealRead", 0) == 0
    assert host.call("satiety.mealRead", -3) == 0
    for M in (0.01, 1, 60, 650, 1e6):
        x = (M / greq) ** host.K.satiety.MEAL_STEEP
        assert host.call("satiety.mealRead", M) == pytest.approx(1 - 1 / (1 + 3 * x)), M


def test_meal_read_is_near_logarithmic(host):
    # each tenfold of M moves the read's odds by the same factor, 10^MEAL_STEEP
    k = 10 ** host.K.satiety.MEAL_STEEP
    odds = [host.call("satiety.mealRead", M) / (1 - host.call("satiety.mealRead", M)) for M in (6, 60, 600)]
    assert odds[1] / odds[0] == pytest.approx(k) and odds[2] / odds[1] == pytest.approx(k)


def test_meal_read_reads_the_named_constants(host):
    S = host.K.satiety
    base = host.call("satiety.mealRead", 60)
    req, steep = S.MEAL_REQ, S.MEAL_STEEP
    S.MEAL_REQ = 12
    S.MEAL_STEEP = 0.05
    try:
        assert host.call("satiety.mealRead", 60) == pytest.approx(1 - 1 / (1 + 3 * 5 ** 0.05))
    finally:
        S.MEAL_REQ, S.MEAL_STEEP = req, steep
    S.MEAL_REQ = 6
    S.MEAL_STEEP = 0.16
    try:
        assert host.call("satiety.mealRead", 60) == pytest.approx(1 - 1 / (1 + 3 * 10 ** 0.16))
    finally:
        S.MEAL_REQ, S.MEAL_STEEP = req, steep
    assert host.call("satiety.mealRead", 60) == base


def test_sated_compounds_the_two_signals(host):
    assert host.call("satiety.sated", 0, 0) == 0
    fw = host.K.satiety.FULL_WEIGHT
    assert host.call("satiety.sated", 1, 0) == pytest.approx(fw)
    assert host.call("satiety.sated", 0, 0.5) == 0.5
    assert host.call("satiety.sated", 1, 0.5) == pytest.approx(1 - (1 - fw) * 0.5)


def test_sated_is_clamped_to_one_past_full(host):
    # Plan 11g spec § 7: F counts to the hard capacity, so FULL_WEIGHT x F can pass 1; the product then reads 1, never
    # more, whatever the meal pool reads
    fw = host.K.satiety.FULL_WEIGHT
    over = 1.2 / fw
    for mn in (0, 0.3, 0.9, 0.999):
        assert host.call("satiety.sated", over, mn) == 1, mn
    assert host.call("satiety.sated", 1 / fw, 0.4) == pytest.approx(1)
    assert host.call("satiety.sated", -1, 0) == 0                       # and never below 0


def test_target_is_the_hunger_target_of_the_sated_read(host):
    for F, M, es in ((0, 6, 1), (0.6, 120, 1.2), (0.3, 0, 0.9), (1, 1300, 1.5)):
        z = host.call("satiety.sated", F, host.call("satiety.mealRead", M))
        assert host.call("satiety.target", F, M, es) == host.call("hybrid.hungerTarget", z, es), (F, M, es)
    assert host.call("satiety.target", 0, host.K.satiety.MEAL_REQ, 1) == pytest.approx(0.25)   # MEAL_REQ, empty: the request


def test_fullness_is_the_fullness_mass_over_the_maximal_capacity(host):
    st = host.K.stomach["new"]()
    assert host.call("satiety.fullness", st) == 0
    host.call("stomach.ingest", st, _vec(host, water=200, proteins=20, carbs=25, lipids=10, fibre=4, calories=270))
    host.call("stomach.ingestLiquid", st, _vec(host, water=356))
    want = host.call("stomach.fullnessMass", st) / host.K.stomach.CAPACITY_MAX_G
    assert host.call("satiety.fullness", st) == pytest.approx(want)


def test_fullness_counts_past_the_comfortable_maximum_to_the_hard_capacity(host):
    # Plan 11g spec § 7 (S1250, S1253): F = fullness mass / CAPACITY_MAX_G, clamped to [0, CAPACITY_HARD_G /
    # CAPACITY_MAX_G] = 1100 / 730; the physical fill (record.stomachFill) still clamps at 1
    cap, hard = host.K.stomach.CAPACITY_MAX_G, host.K.stomach.CAPACITY_HARD_G
    assert (cap, hard) == (730, 1100)
    st = host.K.stomach["new"]()
    host.call("stomach.ingest", st, _vec(host, water=900))
    assert host.call("satiety.fullness", st) == pytest.approx(900 / 730)          # past 1: a fuller stomach sates more
    assert host.call("stomach.fill", st) == 1                                     # the physical fill stays clamped
    host.call("stomach.ingest", st, _vec(host, water=2000))
    assert host.call("satiety.fullness", st) == pytest.approx(1100 / 730)         # clamped at the hard capacity
    S = host.K.stomach
    old = S.CAPACITY_HARD_G
    S.CAPACITY_HARD_G = 900
    try:
        assert host.call("satiety.fullness", st) == pytest.approx(900 / 730)      # the ceiling reads the named constant
    finally:
        S.CAPACITY_HARD_G = old


@pytest.mark.parametrize("hunger,F,es", [(0.31, 0.6, 1), (0.25, 0, 1), (0.6, 0.2, 1.2), (0.2, 0.3, 0.9)])
def test_seed_meal_inverts_the_hunger_function(host, hunger, F, es):
    M = host.call("satiety.seedMeal", hunger, F, es)
    z = host.call("satiety.sated", F, host.call("satiety.mealRead", M))
    assert host.call("hybrid.hungerTarget", z, es) == pytest.approx(hunger)


def test_seed_meal_inverts_the_read_and_caps(host):
    g = host.call("satiety.seedMeal", 0.25, 0.0, 1.0)
    sated = host.call("satiety.sated", 0.0, host.call("satiety.mealRead", g))
    assert abs(host.call("hybrid.hungerTarget", sated, 1.0) - 0.25) < 1e-6
    assert host.call("satiety.seedMeal", 0.0, 0.0, 1.0) == host.K.satiety.MEAL_SEED_MAX


def test_seed_meal_reads_meal_req_at_the_request(host):
    assert host.call("satiety.seedMeal", 0.25, 0, 1) == pytest.approx(host.K.satiety.MEAL_REQ)


def test_seed_meal_clamps_what_it_cannot_reach(host):
    S = host.K.satiety
    assert host.call("satiety.seedMeal", 0, 0, 1) == 1190               # HUNGER 0: the cap, about a large meal's M
    assert host.call("satiety.seedMeal", 0.01, 0, 1) == 1190            # an inverse past the cap is capped
    assert host.call("satiety.seedMeal", 0.195, 0, 1) == 1190           # an empty stomach's floor is 0.196 (Plan 11g Task 6c)
    assert round(1 - host.call("satiety.mealRead", 1190), 3) == 0.196
    M = host.call("satiety.seedMeal", 0.247, 0, 1)                      # below the cap, the exact inverse
    assert M == pytest.approx(S.MEAL_REQ * (0.753 / (3 * 0.247)) ** (1 / S.MEAL_STEEP)) and M < 1190
    assert host.call("satiety.seedMeal", 0.6, 0.9, 0.8) == 0            # hungrier than an empty M gives at this F
    assert host.call("satiety.seedMeal", 0.3, 0, 0) == 0                # no energy state
    assert host.call("satiety.seedMeal", 0.3, 2.5, 1) == 0              # a fullness past 1 / FULL_WEIGHT
    assert host.call("satiety.seedMeal", 0, 1 / S.FULL_WEIGHT, 1) in (0, 1190)   # a fullness at 1 / FULL_WEIGHT: 0 or the cap


def test_seed_meal_reads_the_cap_constant(host):
    S = host.K.satiety
    old = S.MEAL_SEED_MAX
    S.MEAL_SEED_MAX = 500
    try:
        assert host.call("satiety.seedMeal", 0, 0, 1) == 500
        assert host.call("satiety.seedMeal", 0.2, 0, 1) == 500
    finally:
        S.MEAL_SEED_MAX = old


def test_seed_meal_returns_zero_for_non_finite_inputs(host):
    # Plan 11c Task 3 review: a NaN input looped NaN through the pool; a non-finite input seeds an empty M
    nan, inf = float("nan"), float("inf")
    for args in ((nan, 0, 1), (0.3, nan, 1), (0.3, 0, nan), (inf, 0, 1), (-inf, 0, 1), (0.3, inf, 1), (0.3, -inf, 1),
                 (0.3, 0, inf), (0.3, 0, -inf)):
        assert host.call("satiety.seedMeal", *args) == 0, args


def test_seed_meal_is_finite_and_non_negative_over_a_grid(host):
    # as the Plan 11c Task 3 review did: no negative, NaN or infinite M for finite inputs; inside the cap the read inverts
    hungers = [-0.5, 0, 1e-9, 0.01, 0.1, 0.2, 0.25, 0.3, 0.45, 0.69, 0.9, 1, 1.5]
    fills = [-1, 0, 0.1, 0.5, 0.9, 1, 1 / 0.6, 1 / host.K.satiety.FULL_WEIGHT, 2, 5]
    states = [-1, 0, 1e-9, 0.5, 0.8, 1, 1.2, 1.5, 3]
    for h in hungers:
        for F in fills:
            for es in states:
                M = host.call("satiety.seedMeal", h, F, es)
                assert M == M and 0 <= M <= 1190, (h, F, es, M)
                if 0 < M < 1190 and 0 <= h <= 1 and 0 <= F <= 1:          # hungerTarget clamps to [0, 1]
                    z = host.call("satiety.sated", F, host.call("satiety.mealRead", M))
                    assert host.call("hybrid.hungerTarget", z, es) == pytest.approx(h, abs=1e-9), (h, F, es)


def test_the_file_is_grouped_into_its_sections():
    # Plan 11g Task 4's refactor: constants first, then fullness, the meal pool, the read and composition, the seed,
    # discomfort and the factors, each opened by its one-line header; no constant is assigned below the block
    with open(os.path.join(SHARED, "NR_Kernel_Satiety.lua"), encoding="utf-8") as fh:
        src = fh.read()
    heads = ["-- Constants:", "-- Fullness:", "-- The meal pool M", "-- The read and composition", "-- The seed",
             "-- Discomfort:", "-- The circadian, acute, sleep and nicotine factors"]
    at = [src.index(h) for h in heads]
    assert at == sorted(at), at
    gut = src[src.index("-- The meal pool M"):].splitlines()[0]
    assert gut.endswith(".") and len(gut) <= 120, gut                       # the meal pool's header is one line
    first_fn = src.index("\nfunction ")
    for m in re.finditer(r"^K\.satiety\.[A-Z_]+(\.[a-z]+)? = ", src, re.M):
        assert m.start() < first_fn, m.group(0)


def test_satiety_mass_weights_the_liquid_lane(host):
    # structure D: the solid lane mass plus LIQUID_WEIGHT x the liquid lane (S1231 / S1233)
    st = host.K.stomach["new"]()
    host.call("stomach.ingest", st, _vec(host, water=200, proteins=20, carbs=25, lipids=10, fibre=4, calories=270))
    host.call("stomach.ingestLiquid", st, _vec(host, water=356))
    assert host.call("stomach.satietyMass", st) == pytest.approx(259 + host.K.satiety.LIQUID_WEIGHT * 356)
    assert host.call("stomach.mass", st) == pytest.approx(259 + 356)          # the soft cap still reads both whole
    old = host.K.satiety.LIQUID_WEIGHT
    host.K.satiety.LIQUID_WEIGHT = 0.5
    try:
        st.liquid = 100
        assert host.call("stomach.satietyMass", st) == pytest.approx(259 + 50)
    finally:
        host.K.satiety.LIQUID_WEIGHT = old


def test_discomfort_is_linear_from_the_soft_cap_to_the_hard_capacity(host):
    assert host.call("satiety.discomfort", 700, 730, 1100) == 0
    assert host.call("satiety.discomfort", 915, 730, 1100) == pytest.approx(50)
    assert host.call("satiety.discomfort", 1500, 730, 1100) == 100


@pytest.mark.parametrize("hour,expected", [(19 + 50 / 60, 1.085), (7 + 50 / 60, 0.915), (13 + 50 / 60, 1.0),
                                           (1 + 50 / 60, 1.0)])
def test_circadian_peaks_at_19_50_and_troughs_at_07_50(host, hour, expected):
    assert host.call("satiety.circadian", hour) == pytest.approx(expected, abs=1e-5)


def test_circadian_is_periodic_across_midnight(host):
    for h in (23.5, 0.25, 6, 19.8333):
        assert host.call("satiety.circadian", h) == pytest.approx(host.call("satiety.circadian", h + 24))
        assert host.call("satiety.circadian", h) == pytest.approx(host.call("satiety.circadian", h - 24))
    a = host.call("satiety.circadian", 23.99)
    b = host.call("satiety.circadian", 0.01)
    assert abs(a - b) < 1e-3                                         # continuous through 00:00
    c = 1 + 0.085 * math.cos(2 * math.pi * (0 - 19.8333) / 24)
    assert host.call("satiety.circadian", 0) == pytest.approx(c)


def test_hunger_target_reads_the_named_deficit_floor(host):
    # follow-up pin: hungerTarget's value is unchanged by naming its coefficient
    assert host.call("hybrid.hungerTarget", 1, 1.5) == pytest.approx(0.02 * 0.5)     # Plan 11f Task 2c fix 1: 0.02 (0 from Task 2c, 1.0 before)
    # the coefficient is read from the constant, not a literal: patch it and the value follows
    host.K.hybrid.DEFICIT_FLOOR = 0.3
    try:
        assert host.call("hybrid.hungerTarget", 1, 1.5) == pytest.approx(0.3 * 0.5)
    finally:
        host.K.hybrid.DEFICIT_FLOOR = 0.02
    assert host.call("hybrid.hungerTarget", 0.7, 1.5) == pytest.approx(0.3 * 1.5 + 0.02 * 0.5)


@pytest.mark.parametrize("E", [50, 300, 650, 1200])
def test_solid_rate_agrees_with_the_closed_forms_instantaneous_rate(host, E):
    # Task 2 review: solidRate is never called by solidFraction's closed form, so a constant change in either is
    # caught here: the energy leaving over a vanishing step, per minute, is solidRate(E).
    dt = 1e-4
    rate = E * host.call("stomach.solidFraction", E, dt) / dt
    assert rate == pytest.approx(host.call("stomach.solidRate", E), rel=1e-3)


# --- the sleep-debt hunger factor (Plan 11d Task 3, ruling 11d-2; spec § 5d) ------------------------------------------

def test_sleep_factor_shape(host):
    S = host.K.satiety
    assert S.sleepFactor(0) == 1 and S.sleepFactor(-3) == 1 and S.sleepFactor(float("nan")) == 1
    assert S.sleepFactor(S.SLEEP_DEBT_FULL_H) == 1 + S.SLEEP_MAX
    assert S.sleepFactor(10 * S.SLEEP_DEBT_FULL_H) == 1 + S.SLEEP_MAX
    assert S.sleepFactor(S.SLEEP_DEBT_FULL_H / 2) == 1 + S.SLEEP_MAX / 2


def test_sleep_factor_reads_a_non_finite_debt_as_none(host):
    S = host.K.satiety
    assert S.sleepFactor(float("inf")) == 1 and S.sleepFactor(float("-inf")) == 1
    assert S.sleepFactor(1.0) == pytest.approx(1 + S.SLEEP_MAX / S.SLEEP_DEBT_FULL_H)


def test_sleep_constants_and_their_derivation(host):
    S = host.K.satiety
    assert (S.SLEEP_MAX, S.SLEEP_DEBT_FULL_H) == (0.18, 2)
    # one night of 5.5 h (S1565's restriction to 5.5 h or less) against the acute kernel's need books need - 5.5 at
    # the window's close
    assert S.SLEEP_DEBT_FULL_H == host.K.acute.SLEEP_NEED_H - 5.5
    with open(os.path.join(SHARED, "NR_Kernel_Satiety.lua"), encoding="utf-8") as fh:
        src = fh.read()
    for name in ("SLEEP_MAX", "SLEEP_DEBT_FULL_H"):
        line = re.search(r"^K\.satiety\.%s = .*$" % name, src, re.M).group(0)
        assert "game choice, Plan 11d (ruling 11d-2)" in line, name
        for row in ("S1284", "S1565", "S1564", "S1567"):
            assert row in line, (name, row)
    assert "S1568" in src and "S1282" in src                        # step against graded: not settled


# --- the protein fill (Plan 11d Task 5, ruling 11d-5; spec § 5d) ---------------------------------------------------

def test_protein_fill_names_its_label_and_rows():
    with open(os.path.join(SHARED, "NR_Kernel_Satiety.lua"), encoding="utf-8") as fh:
        src = fh.read()
    line = re.search(r"^K\.satiety\.PROTEIN_FILL = .*$", src, re.M).group(0)
    assert "game choice, fitted in Plan 11g Task 6c" in line and "(ruling 11d-5" in line
    assert "no row names gastric fullness from protein" in line
    for row in ("S1222", "S1380", "S1383", "S1384"):
        assert row in line, row


def test_fullness_mass_adds_the_protein_term_to_the_satiety_mass(host):
    # the satiety mass (the solid lane plus a fifth of drunk liquid) plus PROTEIN_FILL x the solid lane's protein
    st = host.K.stomach["new"]()
    host.call("stomach.ingest", st, _vec(host, water=200, proteins=20, carbs=25, lipids=10, fibre=4, calories=270))
    host.call("stomach.ingestLiquid", st, _vec(host, water=356))
    lw, pf = host.K.satiety.LIQUID_WEIGHT, host.K.satiety.PROTEIN_FILL
    assert host.call("stomach.satietyMass", st) == pytest.approx(259 + lw * 356)           # its callers unchanged
    assert host.call("stomach.fullnessMass", st) == pytest.approx(259 + lw * 356 + pf * 20)
    assert host.call("stomach.mass", st) == pytest.approx(259 + 356)                        # the soft cap: no term
    assert host.call("stomach.fill", st) == pytest.approx((259 + lw * 356) / 730)           # stomachFill: no term (T5-2)


def test_a_drinks_protein_fills_from_the_solid_lane(host):
    # ingestLiquid lands a drink's non-water keys, its protein among them, in the solid buffer (ruling 11c-12)
    st = host.K.stomach["new"]()
    host.call("stomach.ingestLiquid", st, _vec(host, water=300, proteins=25, calories=100))
    S = host.K.satiety
    assert host.call("stomach.fullnessMass", st) == pytest.approx(25 + S.LIQUID_WEIGHT * 300 + S.PROTEIN_FILL * 25)


def test_a_protein_free_stomach_reads_the_satiety_mass(host):
    st = host.K.stomach["new"]()
    host.call("stomach.ingest", st, _vec(host, water=300, carbs=40, lipids=10, calories=250))
    assert host.call("stomach.fullnessMass", st) == host.call("stomach.satietyMass", st)
    assert host.call("stomach.fill", st) == pytest.approx(350 / 730)


def test_the_protein_term_reads_the_constant_and_clamps_at_one(host):
    S = host.K.satiety
    st = host.K.stomach["new"]()
    host.call("stomach.ingest", st, _vec(host, water=100, proteins=10, calories=40))
    old = S.PROTEIN_FILL
    S.PROTEIN_FILL = 3
    try:
        assert host.call("stomach.fullnessMass", st) == pytest.approx(110 + 30)
        S.PROTEIN_FILL = 100
        assert host.call("satiety.fill", host.call("stomach.fullnessMass", st), 730) == 1   # 1110 g past 730: F clamps
    finally:
        S.PROTEIN_FILL = old                                     # the saved value, never a literal (Plan 11g Task 6)
    assert host.call("stomach.fullnessMass", st) == pytest.approx(110 + 10 * old)


def test_the_protein_term_fades_as_the_lane_empties(host):
    # the protein leaves in proportion to the lane's energy (drain), so the term falls hour by hour with the meal and
    # is all but gone once the energy is out (397 kcal in about 3.9 h at RATE_BASE 1.25 and RATE_PER_KCAL 0.0025; an
    # hour's step never empties more than water's fraction, 1 - 2^(-60/13), so under 1 % of the term is left at 4 h)
    st = host.K.stomach["new"]()
    host.call("stomach.ingest", st, _vec(host, water=300, proteins=30, carbs=40, lipids=13, calories=397))
    terms = []
    for _ in range(4):
        terms.append(host.call("stomach.fullnessMass", st) - host.call("stomach.satietyMass", st))
        host.call("stomach.drain", st, 1.0)
    pf = host.K.satiety.PROTEIN_FILL
    assert terms[0] == pytest.approx(pf * 30)
    assert all(a > b > 0 for a, b in zip(terms, terms[1:])), terms
    left = host.call("stomach.fullnessMass", st) - host.call("stomach.satietyMass", st)
    assert 0 < left < 0.01 * terms[0], (terms, left)
    assert left == pytest.approx(pf * st.buffer.proteins)


def test_stomach_fill_stays_physical_whatever_the_protein_fill(host):
    # ruling T5-2: record.stomachFill (K.stomach.fill) gates physical emptiness (NUT.FED_FILL, ACUTE_EMPTY_FILL) in grams
    # of contents, so PROTEIN_FILL never reaches it; a 150 g cooked chicken breast (about 46.5 g protein, 5.4 g fat,
    # 98 g water, 248 kcal) reads its own mass over 730 at any PROTEIN_FILL
    S = host.K.satiety
    st = host.K.stomach["new"]()
    host.call("stomach.ingest", st, _vec(host, water=98.1, proteins=46.5, lipids=5.4, calories=248))
    f8 = host.call("stomach.fill", st)
    old = S.PROTEIN_FILL
    S.PROTEIN_FILL = 0
    try:
        f0 = host.call("stomach.fill", st)
    finally:
        S.PROTEIN_FILL = old
    assert f8 == f0 == pytest.approx(150 / 730)


# --- the nicotine-withdrawal hunger factor (Plan 11e Task 2, rulings 11e-2 and T2-A) -------------------------------

def test_nicotine_factor_shape(host):
    S = host.K.satiety
    assert S.nicotineFactor(0, 0) == 1 and S.nicotineFactor(-0.2, 0) == 1           # no withdrawal: none
    assert S.nicotineFactor(0.51, 0) == 1 + S.NIC_MAX                                # at the cap, at the anchor
    assert S.nicotineFactor(5.0, 0) == 1 + S.NIC_MAX                                 # w clamped at the cap
    assert S.nicotineFactor(0.255, 0) == pytest.approx(1 + S.NIC_MAX / 2)            # w / 0.51
    assert S.nicotineFactor(0.51, 91) == pytest.approx(1 + S.NIC_MAX / 2)            # halfway along the fade
    assert S.nicotineFactor(0.51, 45.5) == pytest.approx(1 + S.NIC_MAX * 0.75)       # the fade is linear
    assert S.nicotineFactor(0.51, 182) == 1 and S.nicotineFactor(0.51, 400) == 1     # gone by 26 weeks


@pytest.mark.parametrize("w,d", [(float("nan"), 0), (float("inf"), 0), (float("-inf"), 0), (0.51, float("nan")),
                                 (0.51, float("inf")), (0.51, float("-inf")), (0.51, -1)])
def test_nicotine_factor_reads_a_non_finite_or_negative_input_as_none(host, w, d):
    assert host.K.satiety.nicotineFactor(w, d) == 1


def test_nicotine_constants_and_their_labels(host):
    S = host.K.satiety
    assert (S.NIC_MAX, S.NIC_FADE_DAYS, S.NIC_WITHDRAWAL_MAX) == (0.1313, 182, 0.51)
    with open(os.path.join(SHARED, "NR_Kernel_Satiety.lua"), encoding="utf-8") as fh:
        src = fh.read()
    for name in ("NIC_MAX", "NIC_FADE_DAYS"):
        line = re.search(r"^K\.satiety\.%s = .*$" % name, src, re.M).group(0)
        assert "game choice, Plan 11e (" in line and "11e-2" in line, name
        for s in ("S1576", "S1577", "n = 13", "low certainty"):
            assert s in line, (name, s)
    line = re.search(r"^K\.satiety\.NIC_WITHDRAWAL_MAX = .*$", src, re.M).group(0)
    assert "CharacterStat.NICOTINE_WITHDRAWAL" in line and "#3632" in line
    assert "keeps smoking" in src                                    # the habit never fades (ruling T2-A)
    line = re.search(r"^K\.satiety\.NIC_MAX = .*$", src, re.M).group(0)
    for s in ("T2-D", "48-day mean", "an ASSUMPTION (the row gives no baseline intake)"):
        assert s in line, s                                          # the fit and its labelled baseline
