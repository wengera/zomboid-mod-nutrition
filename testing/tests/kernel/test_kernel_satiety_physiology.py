"""Satiety from physiology (Plan 11c Task 3; spec § 3.1 and § 5a): K.satiety.fill, weigh, feed, decay, post, sated,
seedP, discomfort and circadian, K.stomach.satietyMass and K.hybrid.DEFICIT_FLOOR, on the kernel host. Hand-computed
from the constants; the oracle (test_satiety_meal_studies.py) replays the studies. Fullness is read against
K.stomach.CAPACITY_MAX_G (ruling 11c-19); the circadian term is ruling 11c-24's. Structure D (spec § 5b, ruling 11c-30,
Plan 11c Task 4): the read post(P) = 1 - 1 / (1 + 3 (P / P_REQ)^STEEP), seedP its inverse capped at P_SEED_MAX, and the
satiety mass weighting drunk liquid at LIQUID_WEIGHT."""
import math
import os
import re

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
SHARED = os.path.join(REPO, "mod", "NutritionRevamp", "common", "media", "lua", "shared")
NAMES = ("W_PROTEIN", "W_CARB", "W_FAT", "W_NEUTRAL", "HALF_LIFE_H", "P_REQ", "STEEP", "FULL_WEIGHT", "LIQUID_WEIGHT",
         "P_SEED_MAX", "DISCOMFORT_MAX", "ATWATER_P", "ATWATER_C", "ATWATER_F", "CIRCADIAN_A", "CIRCADIAN_PEAK_H",
         "PROTEIN_FILL")
FITTED = ("W_PROTEIN", "HALF_LIFE_H", "P_REQ", "STEEP", "FULL_WEIGHT", "LIQUID_WEIGHT")


def _vec(host, **kw):
    v = host.K.vector["new"]()
    for k, val in kw.items():
        v[k] = val
    return v


def test_the_constants(host):
    S = host.K.satiety
    assert (S.W_PROTEIN, S.W_CARB, S.W_FAT, S.W_NEUTRAL) == (2.5, 1, 1, 1)
    assert (S.HALF_LIFE_H, S.P_REQ, S.STEEP, S.FULL_WEIGHT, S.LIQUID_WEIGHT) == (0.7, 6, 0.05, 0.55, 0.2)
    assert (S.P_SEED_MAX, S.DISCOMFORT_MAX, S.PROTEIN_FILL) == (1300, 100, 8)
    assert S.P50 is None and S.PN_MAX is None                        # retired by structure D (ruling 11c-30)
    assert (S.ATWATER_P, S.ATWATER_C, S.ATWATER_F) == (4, 4, 9)
    assert (S.CIRCADIAN_A, S.CIRCADIAN_PEAK_H) == (0.085, 19.8333)
    assert host.K.hybrid.DEFICIT_FLOOR == 0.15


def test_each_constant_names_its_row_or_its_label():
    with open(os.path.join(SHARED, "NR_Kernel_Satiety.lua"), encoding="utf-8") as fh:
        src = fh.read()
    for name in NAMES:
        line = re.search(r"^K\.satiety\.%s = .*$" % name, src, re.M).group(0)
        assert re.search(r"S\d{4}|game choice|neutral|CharacterStat", line), name
    for name in FITTED:
        line = re.search(r"^K\.satiety\.%s = .*$" % name, src, re.M).group(0)
        assert "game choice, fitted in Task 4 (Plan 11c)" in line, name  # the label the amendments set
        assert re.search(r"S\d{4}", line), name                          # the rows it was fitted against
    for name in ("W_PROTEIN", "HALF_LIFE_H", "P_REQ", "STEEP"):
        line = re.search(r"^K\.satiety\.%s = .*$" % name, src, re.M).group(0)
        assert "open" in line, name                                      # an open row is never cited as evidence
    for name in ("STEEP", "FULL_WEIGHT"):
        line = re.search(r"^K\.satiety\.%s = .*$" % name, src, re.M).group(0)
        assert "refit in Plan 11d Task 5 (ruling 11d-5)" in line, name   # the joint refit with PROTEIN_FILL
    line = re.search(r"^K\.satiety\.P_SEED_MAX = .*$", src, re.M).group(0)
    assert "game choice" in line
    for name in ("CIRCADIAN_A", "CIRCADIAN_PEAK_H"):
        line = re.search(r"^K\.satiety\.%s = .*$" % name, src, re.M).group(0)
        assert "S1273" in line, name                                     # Scheer 2013, minted as S1273
    with open(os.path.join(SHARED, "NR_Kernel_Hybrid.lua"), encoding="utf-8") as fh:
        hyb = fh.read()
    line = re.search(r"^K\.hybrid\.DEFICIT_FLOOR = .*$", hyb, re.M).group(0)
    assert "game choice" in line and "S1271 open" in line


def test_fill_is_mass_over_the_maximal_capacity_clamped(host):
    cap = host.K.stomach.CAPACITY_MAX_G
    assert cap == 730
    assert host.call("satiety.fill", 365, cap) == 0.5
    assert host.call("satiety.fill", 900, cap) == 1
    assert host.call("satiety.fill", -5, cap) == 0


def test_the_comfortable_capacity_reads_its_share_of_the_maximum(host):
    # ruling 11c-19: fullness is linear in volume up to the tolerated maximum (Goetze 2007), so 430 g is 430/730
    F = host.call("satiety.fill", host.K.stomach.CAPACITY_G, host.K.stomach.CAPACITY_MAX_G)
    assert F == pytest.approx(430 / 730)


def test_weigh_splits_the_calories_by_atwater_share(host):
    v = _vec(host, calories=400, proteins=25, carbs=50, lipids=200 / 9)      # 100, 200 and 200 kcal by Atwater
    assert host.call("satiety.weigh", v) == pytest.approx(400 * (2.5 * 100 + 200 + 200) / 500)


def test_the_delivered_calories_govern_the_energy(host):
    # macros summing to 500 kcal by Atwater on a vector that delivered 250 kcal: weighed at 250 (spec § 3.2)
    v = _vec(host, calories=250, proteins=25, carbs=50, lipids=200 / 9)
    assert host.call("satiety.weigh", v) == pytest.approx(250 * (2.5 * 100 + 200 + 200) / 500)


def test_a_vector_with_no_macros_takes_the_neutral_weight(host):
    assert host.call("satiety.weigh", _vec(host, calories=120)) == 120
    assert host.call("satiety.weigh", _vec(host)) == 0


def test_feed_adds_the_weighed_kcal(host):
    assert host.call("satiety.feed", 50, _vec(host, calories=100, carbs=25)) == pytest.approx(150)
    assert host.call("satiety.feed", 50, _vec(host, calories=40, proteins=10)) == pytest.approx(150)


def test_decay_halves_the_pool_each_half_life(host):
    assert host.call("satiety.decay", 80, 2.0, 2.0, 1) == pytest.approx(40)
    assert host.call("satiety.decay", 80, 2.0, 2.0, 1.5) == pytest.approx(80 * 2 ** -1.5)
    assert host.call("satiety.decay", 80, 0, 2.0, 1) == 80
    assert host.call("satiety.decay", 80, -1, 2.0, 1) == 80


def test_post_reads_the_request_level_at_p_req(host):
    # structure D: 1 - 1 / (1 + 3 (P / P_REQ)^STEEP); at P_REQ an empty stomach reads the request, 1 - Pn = 0.25
    assert host.call("satiety.post", 6) == pytest.approx(0.75)
    for P in (0.01, 1, 60, 650, 1e6):
        x = (P / 6) ** 0.05
        assert host.call("satiety.post", P) == pytest.approx(1 - 1 / (1 + 3 * x)), P
    assert host.call("satiety.post", 0) == 0
    assert host.call("satiety.post", -3) == 0


def test_post_is_near_logarithmic(host):
    # STEEP 0.05 (Plan 11d Task 5): each tenfold of P moves the read's odds by the same factor, 10^0.05
    odds = [host.call("satiety.post", P) / (1 - host.call("satiety.post", P)) for P in (6, 60, 600)]
    assert odds[1] / odds[0] == pytest.approx(10 ** 0.05) and odds[2] / odds[1] == pytest.approx(10 ** 0.05)


def test_post_reads_the_named_constants(host):
    S = host.K.satiety
    base = host.call("satiety.post", 60)
    S.P_REQ = 12
    try:
        assert host.call("satiety.post", 60) == pytest.approx(1 - 1 / (1 + 3 * 5 ** 0.05))
    finally:
        S.P_REQ = 6
    S.STEEP = 0.16
    try:
        assert host.call("satiety.post", 60) == pytest.approx(1 - 1 / (1 + 3 * 10 ** 0.16))
    finally:
        S.STEEP = 0.05
    assert host.call("satiety.post", 60) == base


def test_sated_compounds_the_two_signals(host):
    assert host.call("satiety.sated", 0, 0) == 0
    assert host.call("satiety.sated", 1, 0) == pytest.approx(0.55)
    assert host.call("satiety.sated", 0, 0.5) == 0.5
    assert host.call("satiety.sated", 1, 0.5) == pytest.approx(0.775)


@pytest.mark.parametrize("hunger,F,es", [(0.31, 0.6, 1), (0.25, 0, 1), (0.5, 0.2, 1.4), (0.2, 0.3, 0.9)])
def test_seed_p_inverts_the_hunger_function(host, hunger, F, es):
    P = host.call("satiety.seedP", hunger, F, es)
    z = host.call("satiety.sated", F, host.call("satiety.post", P))
    assert host.call("hybrid.hungerTarget", z, es) == pytest.approx(hunger)


def test_seed_p_reads_p_req_at_the_request(host):
    assert host.call("satiety.seedP", 0.25, 0, 1) == pytest.approx(6)


def test_seed_p_clamps_what_it_cannot_reach(host):
    assert host.call("satiety.seedP", 0, 0, 1) == 1300               # HUNGER 0: the cap, the pool of a large meal
    assert host.call("satiety.seedP", 0.01, 0, 1) == 1300            # an inverse past the cap (about 1e20) is capped
    assert host.call("satiety.seedP", 0.2, 0, 1) == 1300             # STEEP 0.05: an empty stomach's floor is 0.203
    P = host.call("satiety.seedP", 0.22, 0, 1)                       # below the cap, the exact inverse
    assert P == pytest.approx(6 * (0.78 / (3 * 0.22)) ** (1 / 0.05)) and P < 1300
    assert host.call("satiety.seedP", 0.6, 0.9, 0.8) == 0            # hungrier than an empty pool gives at this F
    assert host.call("satiety.seedP", 0.3, 0, 0) == 0                # no energy state
    assert host.call("satiety.seedP", 0.3, 2.5, 1) == 0              # a fullness past 1 / FULL_WEIGHT
    assert host.call("satiety.seedP", 0, 1 / 0.55, 1) in (0, 1300)    # a fullness at 1 / FULL_WEIGHT: 0 or the cap


def test_seed_p_reads_the_cap_constant(host):
    S = host.K.satiety
    S.P_SEED_MAX = 500
    try:
        assert host.call("satiety.seedP", 0, 0, 1) == 500
    finally:
        S.P_SEED_MAX = 1300


def test_seed_p_returns_zero_for_non_finite_inputs(host):
    # Task 3 review: a NaN input looped NaN through the pool; a non-finite input now seeds an empty pool
    nan, inf = float("nan"), float("inf")
    for args in ((nan, 0, 1), (0.3, nan, 1), (0.3, 0, nan), (inf, 0, 1), (-inf, 0, 1), (0.3, inf, 1), (0.3, -inf, 1),
                 (0.3, 0, inf), (0.3, 0, -inf)):
        assert host.call("satiety.seedP", *args) == 0, args


def test_seed_p_is_finite_and_non_negative_over_a_grid(host):
    # as the Task 3 review did: no negative, NaN or infinite P for finite inputs; inside the cap the read inverts
    hungers = [-0.5, 0, 1e-9, 0.01, 0.1, 0.2, 0.25, 0.3, 0.45, 0.69, 0.9, 1, 1.5]
    fills = [-1, 0, 0.1, 0.5, 0.9, 1, 1 / 0.6, 1 / 0.55, 2, 5]
    states = [-1, 0, 1e-9, 0.5, 0.8, 1, 1.2, 1.5, 3]
    for h in hungers:
        for F in fills:
            for es in states:
                P = host.call("satiety.seedP", h, F, es)
                assert P == P and 0 <= P <= 1300, (h, F, es, P)
                if 0 < P < 1300 and 0 <= h <= 1 and 0 <= F <= 1:          # hungerTarget clamps to [0, 1]
                    z = host.call("satiety.sated", F, host.call("satiety.post", P))
                    assert host.call("hybrid.hungerTarget", z, es) == pytest.approx(h, abs=1e-9), (h, F, es)


def test_satiety_mass_weights_the_liquid_lane(host):
    # structure D: the solid lane mass plus LIQUID_WEIGHT x the liquid lane (drunk water at a fifth, S1231 / S1233)
    st = host.K.stomach["new"]()
    host.call("stomach.ingest", st, _vec(host, water=200, proteins=20, carbs=25, lipids=10, fibre=4, calories=270))
    host.call("stomach.ingestLiquid", st, _vec(host, water=356))
    assert host.call("stomach.satietyMass", st) == pytest.approx(259 + 0.2 * 356)
    assert host.call("stomach.mass", st) == pytest.approx(259 + 356)          # the soft cap still reads both whole
    st.liquid = None
    assert host.call("stomach.satietyMass", st) == pytest.approx(259)
    host.K.satiety.LIQUID_WEIGHT = 0.5
    try:
        st.liquid = 100
        assert host.call("stomach.satietyMass", st) == pytest.approx(259 + 50)
    finally:
        host.K.satiety.LIQUID_WEIGHT = 0.2


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
    assert host.call("hybrid.hungerTarget", 1, 1.5) == pytest.approx(0.15 * 0.5)
    # the coefficient is read from the constant, not a literal: patch it and the value follows
    host.K.hybrid.DEFICIT_FLOOR = 0.3
    try:
        assert host.call("hybrid.hungerTarget", 1, 1.5) == pytest.approx(0.3 * 0.5)
    finally:
        host.K.hybrid.DEFICIT_FLOOR = 0.15
    assert host.call("hybrid.hungerTarget", 0.7, 1.5) == pytest.approx(0.3 * 1.5 + 0.15 * 0.5)


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
    assert "game choice, Plan 11d (ruling 11d-5" in line
    assert "no row names gastric fullness from protein" in line
    for row in ("S1222", "S1380", "S1383", "S1231", "S1233", "S1247", "S1384"):
        assert row in line, row


def test_fullness_mass_adds_the_protein_term_to_the_satiety_mass(host):
    # the satiety mass (the solid lane plus a fifth of drunk liquid) plus PROTEIN_FILL x the solid lane's protein
    st = host.K.stomach["new"]()
    host.call("stomach.ingest", st, _vec(host, water=200, proteins=20, carbs=25, lipids=10, fibre=4, calories=270))
    host.call("stomach.ingestLiquid", st, _vec(host, water=356))
    assert host.call("stomach.satietyMass", st) == pytest.approx(259 + 0.2 * 356)          # its callers unchanged
    assert host.call("stomach.fullnessMass", st) == pytest.approx(259 + 0.2 * 356 + 8 * 20)
    assert host.call("stomach.mass", st) == pytest.approx(259 + 356)                        # the soft cap: no term
    assert host.call("stomach.fill", st) == pytest.approx((259 + 0.2 * 356) / 730)          # stomachFill: no term (T5-2)


def test_a_drinks_protein_fills_from_the_solid_lane(host):
    # ingestLiquid lands a drink's non-water keys, its protein among them, in the solid buffer (ruling 11c-12)
    st = host.K.stomach["new"]()
    host.call("stomach.ingestLiquid", st, _vec(host, water=300, proteins=25, calories=100))
    assert host.call("stomach.fullnessMass", st) == pytest.approx(25 + 0.2 * 300 + 8 * 25)


def test_a_protein_free_stomach_reads_the_satiety_mass(host):
    st = host.K.stomach["new"]()
    host.call("stomach.ingest", st, _vec(host, water=300, carbs=40, lipids=10, calories=250))
    assert host.call("stomach.fullnessMass", st) == host.call("stomach.satietyMass", st)
    assert host.call("stomach.fill", st) == pytest.approx(350 / 730)


def test_the_protein_term_reads_the_constant_and_clamps_at_one(host):
    S = host.K.satiety
    st = host.K.stomach["new"]()
    host.call("stomach.ingest", st, _vec(host, water=100, proteins=10, calories=40))
    S.PROTEIN_FILL = 3
    try:
        assert host.call("stomach.fullnessMass", st) == pytest.approx(110 + 30)
        S.PROTEIN_FILL = 100
        assert host.call("satiety.fill", host.call("stomach.fullnessMass", st), 730) == 1   # 1110 g past 730: F clamps
    finally:
        S.PROTEIN_FILL = 8
    assert host.call("stomach.fullnessMass", st) == pytest.approx(110 + 80)


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
    assert terms[0] == pytest.approx(8 * 30)
    assert all(a > b > 0 for a, b in zip(terms, terms[1:])), terms
    left = host.call("stomach.fullnessMass", st) - host.call("stomach.satietyMass", st)
    assert 0 < left < 0.01 * terms[0], (terms, left)
    assert left == pytest.approx(8 * st.buffer.proteins)


def test_stomach_fill_stays_physical_whatever_the_protein_fill(host):
    # ruling T5-2: record.stomachFill (K.stomach.fill) gates physical emptiness (NUT.FED_FILL, ACUTE_EMPTY_FILL) in grams
    # of contents, so PROTEIN_FILL never reaches it; a 150 g cooked chicken breast (about 46.5 g protein, 5.4 g fat,
    # 98 g water, 248 kcal) reads its own mass over 730 at any PROTEIN_FILL
    S = host.K.satiety
    st = host.K.stomach["new"]()
    host.call("stomach.ingest", st, _vec(host, water=98.1, proteins=46.5, lipids=5.4, calories=248))
    f8 = host.call("stomach.fill", st)
    S.PROTEIN_FILL = 0
    try:
        f0 = host.call("stomach.fill", st)
    finally:
        S.PROTEIN_FILL = 8
    assert f8 == f0 == pytest.approx(150 / 730)
