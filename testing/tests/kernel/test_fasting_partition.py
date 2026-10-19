"""A water-only fast on the deficit arm without Alpert's ceiling (Plan 16 Task 5; spec section 3).

The guide's fast (tools/mod_guide_series.py: the whole server pipeline on the lupa host from a fresh record at HUNGER 0,
sleep off, 4 L of water a day in eight drinks, no food) for the three bodies of spec section 3.3: the default body
(65.0 kg, 13.0 kg fat), Obese (82.4 kg, 30.34 kg fat) and Gaunt (VERY_UNDERWEIGHT, 55.6 kg, 3.62 kg fat). The deficit
now splits by Forbes' share alone (S1056, S0054), and these replays are read against the fasting rows S2278-S2283,
S2243 and S0104. Where the replay misses a row's band the miss is named, pinned and asserted still outside it.

The energy share is lean's share of the energy the body gave up over an interval: dLean * 1816 / (dLean * 1816 +
dFat * 9441) (S0126's densities, the kernel's RHO_LEAN and RHO_FAT), lean being body.lm + body.lx.
"""
import math
import os
import sys

import pytest

TOOLS = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))),
                     "tools")
RL_KCAL, RF_KCAL = 1816.0, 9441.0
BODIES = {"default": ([], 78), "obese": (["OBESE"], 78), "gaunt": (["VERY_UNDERWEIGHT"], 47)}
PATHS = ("body.fm", "body.lm", "body.lx", "acute.bmi")


def _fast(traits, days):
    if TOOLS not in sys.path:
        sys.path.insert(0, TOOLS)
    import mod_guide_series as G
    rows, be = G.server_run([G.FRESH] + G.autodrops(days), days * G.DAY_MIN, PATHS, player={"traits": list(traits)},
                            sparse=PATHS, every=G.DAY_MIN)
    daily = [(rows[k]["body.fm"], rows[k]["body.lm"] + rows[k]["body.lx"]) for k in G.day_ends(days)]
    return daily, G.viability(rows, be.K)


@pytest.fixture(scope="module")
def fast():
    return {name: _fast(traits, days) for name, (traits, days) in BODIES.items()}


def energy_share(daily, a, b):
    """Lean's share of the energy given up between day closes a and b."""
    el = (daily[a][1] - daily[b][1]) * RL_KCAL
    ef = (daily[a][0] - daily[b][0]) * RF_KCAL
    return el / (el + ef)


def lost_pct(daily, d):
    return 100.0 * (1.0 - sum(daily[d]) / sum(daily[0]))


def elia_tee(fat_pct):
    """The Task 1 report's log-linear fit through S2278's digitised points, % of BMR, read as a share of TEE at Elia's
    TEE/BMR of 1.3 (partition-report section 3; the fit is the report's, not a register value)."""
    return 38.2 * math.exp(-0.0406 * fat_pct) / 1.3 / 100.0


# --- the deaths (spec section 3.3: whatever kills first on the science, not tuned) ---------------------------------

# Plan 17 Task 2: the gaunt body's starvation death reads 40.90 (was 41.14 on the floor's BMI staircase): the smoothed
# BMI clock (spec section 1.2a) reaches 1 within the record day before the close that takes BMI under 12
@pytest.mark.parametrize("name, day, state", [("default", 77.23, "beriberi"), ("obese", 77.23, "beriberi"),
                                              ("gaunt", 40.90, "starvation")])
def test_each_body_dies_of_what_the_science_gives_first(fast, name, day, state):
    v = fast[name][1]
    assert v["death_name"] == state
    assert v["death_age"] / 24.0 == pytest.approx(day, abs=0.01)


# --- the lean share of energy (S2282 Jackson, S2283 Benedict, S2278 Elia) ------------------------------------------

def test_the_default_share_sits_in_jacksons_range_to_day_30(fast):
    # readings, not S2282's own window (its 13.0-17.1 % is over the whole 44-day fast: the near-miss below); days
    # 14-30 alone read 0.174 (Benedict's, below)
    daily = fast["default"][0]
    for a, b in ((0, 14), (0, 30)):
        assert 0.130 <= energy_share(daily, a, b) <= 0.171, (a, b)


def test_the_default_share_over_jacksons_44_days_is_a_near_miss(fast):
    # named near-miss (Plan 16 Task 5 review F1): on S2282's own window, days 0-44, the share reads 0.176, just over
    # its 17.1 % (Forbes' share rises as fat falls)
    s = energy_share(fast["default"][0], 0, 44)
    assert s == pytest.approx(0.176, abs=0.002)
    assert s > 0.171


def test_the_default_share_after_day_13_is_benedicts(fast):
    # S2283: after the thirteenth day about 17.5 % of the heat came from protein (a lean man, to day 31)
    assert energy_share(fast["default"][0], 13, 31) == pytest.approx(0.175, abs=0.015)


def test_the_default_share_rises_past_jacksons_range_after_day_30(fast):
    # named: Forbes' share rises as fat falls (the Task 1 report's caveat; S2279 and S2281 report little change over a
    # month in lean subjects); days 30-45 read 0.216, above S2282's 17.1 %
    s = energy_share(fast["default"][0], 30, 45)
    assert s == pytest.approx(0.216, abs=0.002)
    assert s > 0.171


@pytest.mark.parametrize("name, fat_pct", [("default", 20.0), ("obese", 36.8)])
def test_the_share_over_a_month_follows_elias_curve(fast, name, fat_pct):
    # S2278 (Elia's compilation, fasts over 16 days): within a third either way of the curve at the body's fat
    s = energy_share(fast[name][0], 0, 31)
    assert 0.75 <= s / elia_tee(fat_pct) <= 1.33


def test_the_obese_share_is_about_7_percent(fast):
    # S2278 at 37-41 % fat and the report's Owen 1998 (7 % late in a 21-day obese fast)
    daily = fast["obese"][0]
    for a, b in ((0, 14), (14, 30), (30, 45)):
        assert 0.04 <= energy_share(daily, a, b) <= 0.10, (a, b)


def test_the_gaunt_share_overshoots_elias_curve(fast):
    # named non-reproduction (the Task 1 report, section 9): Forbes runs high at the very lean end, 0.41 over days
    # 0-14 against the curve's about 0.23 of TEE at 6.5 % fat; too few lean points in S2278 to fit a correction
    s = energy_share(fast["gaunt"][0], 0, 14)
    assert s == pytest.approx(0.409, abs=0.002)
    assert s / elia_tee(6.5) > 1.33


# --- the mass lost (S2243, S2282, S0104) ----------------------------------------------------------------------------

def test_the_default_loss_by_day_43_sits_between_the_strikers_and_jackson(fast):
    # S2243: about 18 % by day 43 (eight hunger strikers); S2282: 25.5 % by day 44 (a non-obese man)
    assert 18.0 <= lost_pct(fast["default"][0], 43) <= 25.5


def test_the_obese_body_loses_less_by_day_43(fast):
    # named: the Obese body's loss is mostly fat at 9441 kcal/kg, 13.8 % by day 43, under S2243's 18 %
    assert lost_pct(fast["obese"][0], 43) == pytest.approx(13.8, abs=0.1)
    assert lost_pct(fast["obese"][0], 43) < 18.0


@pytest.mark.parametrize("name", ["default", "obese"])
def test_week_three_loses_about_0_3_kg_a_day(fast, name):
    daily = fast[name][0]
    assert 0.25 <= (sum(daily[14]) - sum(daily[21])) / 7.0 <= 0.35       # S0104: 0.3 kg/d by the third week


def test_the_gaunt_body_loses_faster_in_week_three(fast):
    # named: Gaunt pays about half its energy from lean at 1816 kcal/kg, 0.51 kg/d, over S0104's mostly obese 0.3
    daily = fast["gaunt"][0]
    rate = (sum(daily[14]) - sum(daily[21])) / 7.0
    assert rate == pytest.approx(0.510, abs=0.005)
    assert rate > 0.35


# --- the fat floor ----------------------------------------------------------------------------------------------------

def test_the_fat_floor_can_be_reached(fast, host):
    # the ceiling held Gaunt's fat at 8.4 % at its death; on Forbes' share fat reaches the floor (K.strength.DEFAULTS'
    # fmMin, a game choice) at day close 46, after the starvation death at day 41.14
    daily = fast["gaunt"][0]
    fm_min = host.K.strength.DEFAULTS.fmMin
    first = next(d for d, (fm, _) in enumerate(daily) if fm <= fm_min + 1e-9)
    assert first == 46
    assert daily[41][0] == pytest.approx(0.616, abs=0.01)                 # fat at the last day close before the death


# --- the arm itself ----------------------------------------------------------------------------------------------------

def test_the_deficit_arm_reads_no_ceiling(host):
    # a total fast's day at 2.0 kg fat: Forbes' share splits the whole deficit, far past the old 69 * fm kcal/d
    D = host.K.strength.DEFAULTS
    body = host.table({"fm": 2.0, "lm": 50.0, "lx": 0.0})
    dF, dX, dM = host.call("partition.deficitLean", body, 0.0, 0.0, 0.0, -1800.0, D, 1.0)
    s = 10.4 / 12.4
    dW = 1800.0 / (s * RL_KCAL + (1 - s) * RF_KCAL)
    assert dF == pytest.approx(-s * dW, rel=1e-12)
    assert dM == pytest.approx(-(1 - s) * dW, rel=1e-12)
    assert -dM * RF_KCAL > 69 * 2.0


# --- the fat floor conserves energy (Plan 16 Task 5 fix 1, review F2) -----------------------------------------------

def _floor_body(host):
    return host.table({"lm": 50.0, "F0": 50.0, "Fc": 60.0, "Pk": 50.0, "fm": 0.5, "lx": 0.0, "grace": 0,
                       "T": 1.0, "Tgrace": 0})


def test_a_protected_body_at_the_fat_floor_pays_the_whole_deficit_from_lean(host):
    # trained (20 sets a week) and on 2.0 g/kg protein, prot at its floor: with fat at fmMin the whole deficit is paid
    # by lean at 1816 kcal/kg, so the day's mass change carries the deficit's energy (no floor clamp drops it)
    D = host.K.strength.DEFAULTS
    b = _floor_body(host)
    dF, dX, dM = host.call("partition.deficitLean", b, 0.0, 20.0, 2.0, -1500.0, D, 1.0)
    assert dM == pytest.approx(0.0, abs=1e-12)
    assert (dF + dX) * RL_KCAL == pytest.approx(-1500.0, rel=1e-12)


def test_the_floor_split_pays_the_part_past_the_floor_from_lean(host):
    # just above the floor the fat side pays down to fmMin and the rest goes to lean, energy for energy
    D = host.K.strength.DEFAULTS
    b = host.table({"lm": 50.0, "fm": 0.52, "lx": 0.0})
    dF, dX, dM = host.call("partition.deficitLean", b, 0.0, 0.0, 0.0, -1800.0, D, 1.0)
    assert dM == pytest.approx(-0.02, abs=1e-12)
    assert (dF + dX) * RL_KCAL + dM * RF_KCAL == pytest.approx(-1800.0, rel=1e-12)


def test_a_protected_body_at_the_floor_starves_on_the_conserved_clock(host):
    # a trained, protein-fed body held at -1500 kcal/d from the fat floor: each closed day's mass loss is the day's
    # energy at the lean density, so lean falls to the BMI-12 starvation point (S2234) on the day the energy says;
    # before fix 1 the floor clamp dropped about 98 % of the deficit and such a body barely lost mass
    D = host.K.strength.DEFAULTS
    H2 = float(host.K.HEIGHT_M) ** 2
    b = _floor_body(host)
    E = -1500.0
    days = 0
    while (b.lm + b.lx + b.fm) / H2 > 12.0 and days < 200:
        m0 = b.lm + b.lx + b.fm
        e0 = (b.lm + b.lx) * RL_KCAL + b.fm * RF_KCAL
        dF, dX, dM = host.call("strength.day", b, 20.0, 2.0, E, 2600.0, 0.0, D, 1.0)
        days += 1
        assert b.fm == pytest.approx(D.fmMin, abs=1e-12)
        e1 = (b.lm + b.lx) * RL_KCAL + b.fm * RF_KCAL
        if b.lm > D.fMinShare * b.F0:
            assert e1 - e0 == pytest.approx(E, rel=1e-6), days            # the energy lost is the day's deficit
            assert m0 - (b.lm + b.lx + b.fm) == pytest.approx(-E / RL_KCAL, rel=1e-6)
    want = math.ceil((50.5 - 12.0 * H2) / (1500.0 / RL_KCAL))
    assert days == want
