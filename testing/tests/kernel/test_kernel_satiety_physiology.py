"""Satiety from physiology (Plan 11c Task 3; spec § 3.1 and § 5a): K.satiety.fill, weigh, feed, decay, post, sated,
seedP, discomfort and circadian, and K.hybrid.DEFICIT_FLOOR, on the kernel host. Hand-computed from the constants; the
oracle (test_satiety_meal_studies.py) replays the studies. Fullness is read against K.stomach.CAPACITY_MAX_G (ruling
11c-19); the circadian term is ruling 11c-24's."""
import math
import os
import re

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
SHARED = os.path.join(REPO, "mod", "NutritionRevamp", "common", "media", "lua", "shared")
NAMES = ("W_PROTEIN", "W_CARB", "W_FAT", "W_NEUTRAL", "HALF_LIFE_H", "P50", "FULL_WEIGHT", "PN_MAX", "DISCOMFORT_MAX",
         "ATWATER_P", "ATWATER_C", "ATWATER_F", "CIRCADIAN_A", "CIRCADIAN_PEAK_H")


def _vec(host, **kw):
    v = host.K.vector["new"]()
    for k, val in kw.items():
        v[k] = val
    return v


def test_the_constants(host):
    S = host.K.satiety
    assert (S.W_PROTEIN, S.W_CARB, S.W_FAT, S.W_NEUTRAL) == (2.5, 1, 1, 1)
    assert (S.HALF_LIFE_H, S.P50, S.FULL_WEIGHT, S.PN_MAX, S.DISCOMFORT_MAX) == (2.0, 150, 0.5, 0.99, 100)
    assert (S.ATWATER_P, S.ATWATER_C, S.ATWATER_F) == (4, 4, 9)
    assert (S.CIRCADIAN_A, S.CIRCADIAN_PEAK_H) == (0.085, 19.8333)
    assert host.K.hybrid.DEFICIT_FLOOR == 0.15


def test_each_constant_names_its_row_or_its_label():
    with open(os.path.join(SHARED, "NR_Kernel_Satiety.lua"), encoding="utf-8") as fh:
        src = fh.read()
    for name in NAMES:
        line = re.search(r"^K\.satiety\.%s = .*$" % name, src, re.M).group(0)
        assert re.search(r"S\d{4}|S1\.\d+|game choice|neutral|CharacterStat", line), name
    for name in ("W_PROTEIN", "HALF_LIFE_H", "P50"):
        line = re.search(r"^K\.satiety\.%s = .*$" % name, src, re.M).group(0)
        assert "game choice" in line and "open" in line, name           # an open row is never cited as evidence
        assert "fitted in Task 4" in line, name                          # a provisional fit (the amendments)
    for name in ("CIRCADIAN_A", "CIRCADIAN_PEAK_H"):
        line = re.search(r"^K\.satiety\.%s = .*$" % name, src, re.M).group(0)
        assert "S1.52" in line, name                                     # Scheer 2013, provisional until minted
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


def test_post_saturates_at_its_half_point(host):
    assert host.call("satiety.post", 150) == 0.5
    assert host.call("satiety.post", 450) == 0.75
    assert host.call("satiety.post", 0) == 0
    assert host.call("satiety.post", -3) == 0


def test_sated_compounds_the_two_signals(host):
    assert host.call("satiety.sated", 0, 0) == 0
    assert host.call("satiety.sated", 1, 0) == 0.5
    assert host.call("satiety.sated", 0, 0.5) == 0.5
    assert host.call("satiety.sated", 1, 0.5) == 0.75


@pytest.mark.parametrize("hunger,F,es", [(0.31, 0.6, 1), (0.25, 0, 1), (0.5, 0.2, 1.4), (0.2, 0.3, 0.9)])
def test_seed_p_inverts_the_hunger_function(host, hunger, F, es):
    P = host.call("satiety.seedP", hunger, F, es)
    z = host.call("satiety.sated", F, host.call("satiety.post", P))
    assert host.call("hybrid.hungerTarget", z, es) == pytest.approx(hunger)


def test_seed_p_clamps_what_it_cannot_reach(host):
    P = host.call("satiety.seedP", 0, 0, 1)                          # HUNGER 0: the ceiling, a finite pool
    assert P == pytest.approx(150 * 0.99 / 0.01) and host.call("satiety.post", P) == pytest.approx(0.99)
    assert host.call("satiety.seedP", 0.6, 0.9, 0.8) == 0            # hungrier than an empty pool gives at this F
    assert host.call("satiety.seedP", 0.3, 0, 0) == 0                # no energy state
    assert host.call("satiety.seedP", 0.3, 2.5, 1) == 0              # a fullness past 1 / FULL_WEIGHT
    assert host.call("satiety.seedP", 0, 2, 1) == 0                  # a fullness at 1 / FULL_WEIGHT exactly (0 / 0)


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
    assert host.call("hybrid.hungerTarget", 0.7, 1.5) == pytest.approx(0.3 * 1.5 + 0.15 * 0.5)


@pytest.mark.parametrize("E", [50, 300, 650, 1200])
def test_solid_rate_agrees_with_the_closed_forms_instantaneous_rate(host, E):
    # Task 2 review: solidRate is never called by solidFraction's closed form, so a constant change in either is
    # caught here: the energy leaving over a vanishing step, per minute, is solidRate(E).
    dt = 1e-4
    rate = E * host.call("stomach.solidFraction", E, dt) / dt
    assert rate == pytest.approx(host.call("stomach.solidRate", E), rel=1e-3)
