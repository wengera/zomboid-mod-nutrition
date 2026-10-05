"""The functional factor, the ceiling, the write policy, the carry factor and the band remap
(NR_Kernel_Strength.lua), Plan 3 Task 10.

NR_Kernel_Strength.lua is a kernel file (its name is NR_Kernel*), so the session `host` fixture loads it
through its glob and already has NutritionRevamp.kernel.strength. Every expectation below is
hand-computed from the file's constants: the neural target 0.18 x dStr (S0585); the rising, falling and
immobilised time constants 14, 60 and 10 days (S0086; S0655 open, design-phase-v1; S0070/S0612); the
memory floor 0.80 x exp(-dt/300) after 14 days held (S0655 open, design-phase-v1); the cumulative deficit's
10-day decay, 50000 kcal full scale and -0.10 (S0601, S0602); the disuse residual -0.325 ln(1 + t/22)
(fitted to S0070); the factor clamp [0.55, 1.25] and 10 levels per doubling (game choices); L_MAX 10
(#2118, ruling 9); the write policy's 6 h rise hold and 1 h fall spacing (ruling 10); the acute carry
terms (S0623, S0624, S0763, S0762, S0765, S0626, S0633, S0651) clamped [-0.20, 0.03] (a game choice); the
carry delta traitCarry x (1 + eAcute) (ruling 11); the band remap WEAK 0-1, FEEBLE 2-4, none 5, STOUT
6-8, STRONG >= 9 (#2157).
"""
import math

import pytest

TOL = 1e-9

# The Strength XP ladder: getTotalXpForLevel(L) for L = 1..10 (#2102). 37500 is level 5's total, 67500
# level 6's; getTotalXpForLevel(11) == getTotalXpForLevel(10) (#2859), so the Java cap is 10 (#2118).
LADDER = [1500, 4500, 10500, 19500, 37500, 67500, 127500, 217500, 337500, 487500]


def _close(a, b, tol=TOL):
    return abs(a - b) < tol


def _ring(values):
    return {i + 1: v for i, v in enumerate(values)}


def _body(host, **kw):
    d = dict(n=0.0, nPeak=0.0, tPeakD=0, nHist=_ring([0.0] * 14), cumDef=0.0, tDisuse=0, ebDay=0.0,
             shownL=5, riseHeldH=0.0, lastFallAge=0.0)
    d.update(kw)
    return host.table(d)


# --- constants ---

def test_constants(host):
    s = host.K.strength
    assert s.N_TARGET_K == 0.18 and s.TAU_RISE == 14 and s.TAU_FALL == 60 and s.TAU_IMMOB == 10
    assert s.MEM_RETAIN == 0.80 and s.MEM_TAU == 300 and s.MEM_HOLD_DAYS == 14
    assert s.CUMDEF_TAU == 10 and s.CUMDEF_FULL == 50000 and s.E_ENERGY_MAX == -0.10
    assert s.DISUSE_K == -0.325 and s.DISUSE_T == 22
    assert s.F_MIN == 0.55 and s.F_MAX == 1.25 and s.LEVELS_PER_DOUBLING == 10 and s.L_MAX == 10
    assert s.RISE_HOLD_H == 6 and s.FALL_MIN_H == 1
    assert s.DEHYD_STEP1 == -0.03 and s.DEHYD_STEP2 == -0.06
    assert s.DEHYD_PCT1 == 2 and s.DEHYD_PCT2 == 4 and s.DEHYD_SWEAT_K == 1.5
    assert s.SLEEP_KNEE_H == 18 and s.SLEEP_PER_H == -0.004 and s.SLEEP_CAP == -0.08
    assert s.SLEEP_AM_FACTOR == 0.5 and s.AM_FROM_H == 6 and s.AM_TO_H == 12
    assert s.CAFFEINE_BONUS == 0.02 and s.VITD_PENALTY == -0.03
    assert s.FAT_PER_10PT == -0.03 and s.FAT_KNEE == 0.30
    assert s.E_ACUTE_MIN == -0.20 and s.E_ACUTE_MAX == 0.03


def test_bands_table(host):
    bands = host.py(host.K.strength.BANDS)
    assert [bands[i][1] for i in range(1, 6)] == [1, 4, 5, 8, 10]
    assert [bands[i].get(2) for i in range(1, 6)] == ["WEAK", "FEEBLE", None, "STOUT", "STRONG"]


# --- the neural term ---

def test_neural_rises_toward_target_over_one_tau(host):
    b = _body(host)
    host.K.strength.neuralStep(b, 0.5, False, False, 14)
    assert _close(b.n, 0.09 * (1 - math.exp(-1)))


def test_neural_rise_composes_per_minute(host):
    b = _body(host)
    for _ in range(14 * 24):
        host.K.strength.neuralStep(b, 0.5, False, False, 1 / 24)
    assert _close(b.n, 0.09 * (1 - math.exp(-1)), 1e-12)


def test_neural_falling_maintained_holds(host):
    b = _body(host, n=0.09)
    host.K.strength.neuralStep(b, 0.0, True, False, 30)
    assert b.n == 0.09


def test_neural_maintained_does_not_hold_a_rise(host):
    b = _body(host)
    host.K.strength.neuralStep(b, 0.5, True, False, 14)
    assert _close(b.n, 0.09 * (1 - math.exp(-1)))


def test_neural_falling_immobilised_uses_tau_10(host):
    b = _body(host, n=0.1)
    host.K.strength.neuralStep(b, 0.0, False, True, 10)
    assert _close(b.n, 0.1 * math.exp(-1))


def test_neural_falling_uses_tau_60(host):
    b = _body(host, n=0.1)
    host.K.strength.neuralStep(b, 0.0, False, False, 60)
    assert _close(b.n, 0.1 * math.exp(-1))


def test_neural_at_target_unchanged(host):
    b = _body(host, n=0.09)
    host.K.strength.neuralStep(b, 0.5, False, False, 5)
    assert _close(b.n, 0.09)


# --- the day close: the ring, the held peak, the cumulative deficit ---

def test_close_day_peak_after_fourteen_days_held(host):
    b = _body(host, n=0.09)
    for d in range(1, 14):
        host.K.strength.closeDay(b, d)
        assert b.nPeak == 0
    host.K.strength.closeDay(b, 14)
    assert _close(b.nPeak, 0.09) and b.tPeakD == 14
    hist = host.py(b.nHist)
    assert [hist[i] for i in range(1, 15)] == [0.09] * 14


def test_close_day_one_high_day_then_zeros_no_peak(host):
    b = _body(host, n=0.09)
    host.K.strength.closeDay(b, 1)
    b.n = 0.0
    for d in range(2, 30):
        host.K.strength.closeDay(b, d)
    assert b.nPeak == 0 and b.tPeakD == 0


def test_close_day_ring_shifts_oldest_out(host):
    b = _body(host, nHist=_ring([float(i) for i in range(1, 15)]), n=99.0)
    host.K.strength.closeDay(b, 3)
    hist = host.py(b.nHist)
    assert [hist[i] for i in range(1, 15)] == [float(i) for i in range(2, 15)] + [99.0]
    assert b.nPeak == 2.0 and b.tPeakD == 3


def test_close_day_peak_not_lowered(host):
    b = _body(host, nPeak=0.2, tPeakD=5, n=0.09, nHist=_ring([0.09] * 14))
    host.K.strength.closeDay(b, 40)
    assert b.nPeak == 0.2 and b.tPeakD == 5


def test_cum_def_decays_and_adds_deficit(host):
    b = _body(host, cumDef=10000.0, ebDay=-800.0)
    host.K.strength.closeDay(b, 1)
    assert _close(b.cumDef, 10000 * math.exp(-0.1) + 800)


def test_cum_def_surplus_only_decays(host):
    b = _body(host, cumDef=10000.0, ebDay=600.0)
    host.K.strength.closeDay(b, 1)
    assert _close(b.cumDef, 10000 * math.exp(-0.1))


# --- the memory floor and the slow factor ---

def test_floor_at_peak_day(host):
    b = _body(host, nPeak=0.1, tPeakD=50)
    assert _close(host.K.strength.floorF(b, 50), 1.08)


def test_floor_three_hundred_days_later(host):
    b = _body(host, nPeak=0.1, tPeakD=50)
    assert _close(host.K.strength.floorF(b, 350), 1 + 0.08 * math.exp(-1))


def test_fslow_replete(host):
    assert _close(host.K.strength.fSlow(_body(host), 10), 1.0)


def test_fslow_neural(host):
    assert _close(host.K.strength.fSlow(_body(host, n=0.09), 10), 1.09)


def test_fslow_floor_wins_over_lower_n(host):
    b = _body(host, n=0.0, nPeak=0.1, tPeakD=10)
    assert _close(host.K.strength.fSlow(b, 10), 1.08)


def test_fslow_cum_def_half(host):
    assert _close(host.K.strength.fSlow(_body(host, cumDef=25000.0), 10), 0.95)


def test_fslow_cum_def_saturates(host):
    assert _close(host.K.strength.fSlow(_body(host, cumDef=90000.0), 10), 0.90)


def test_fslow_disuse_day_5(host):
    got = host.K.strength.fSlow(_body(host, tDisuse=5), 10)
    assert _close(got, 1 + (-0.325 * math.log(1 + 5 / 22)))
    assert abs(got - 0.933443) < 2e-6  # the plan rounds ln(1.227273); exact 0.9334418


@pytest.mark.parametrize("kw, want", [
    (dict(n=0.5), 1.25),
    (dict(tDisuse=400, cumDef=60000.0), 0.55),
])
def test_fslow_clamps(host, kw, want):
    assert _close(host.K.strength.fSlow(_body(host, **kw), 10), want)


# --- the ceiling ---

@pytest.mark.parametrize("l0, lm, lm0, f, want", [
    (5, 65.6, 65.6, 1, 5),
    (5, 78.72, 65.6, 1, 8),
    (5, 59.04, 65.6, 0.95, 3),
    (9, 131.2, 65.6, 1, 10),
    (1, 20, 65.6, 0.55, 0),
])
def test_ceiling(host, l0, lm, lm0, f, want):
    assert host.K.strength.ceiling(l0, lm, lm0, f) == want


# --- the XP-implied level ---

@pytest.mark.parametrize("xp, want", [
    (0, 0), (1499, 0), (1500, 1), (19499, 3), (20000, 4), (37500, 5), (67499, 5), (67500, 6),
    (487499, 9), (487500, 10), (500000, 10),
])
def test_xp_level(host, xp, want):
    assert host.K.strength.xpLevel(xp, host.table(_ring(LADDER))) == want


# --- the write policy ---

def test_policy_falls_one_level_per_hour(host):
    s = host.K.strength
    b = _body(host, shownL=5, lastFallAge=0.0)
    assert s.policy(b, 5, 3, 100, 1 / 60) == 4
    assert b.shownL == 4 and b.lastFallAge == 100
    assert s.policy(b, 5, 3, 100 + 10 / 60, 10 / 60) == 4
    assert s.policy(b, 5, 3, 101, 50 / 60) == 3
    assert b.lastFallAge == 101
    assert s.policy(b, 5, 3, 102, 1) == 3


def test_policy_rises_one_level_after_six_hours_held(host):
    s = host.K.strength
    b = _body(host, shownL=5)
    got = [s.policy(b, 7, 8, 100 + h, 1) for h in range(1, 7)]
    assert got == [5, 5, 5, 5, 5, 6]
    assert b.riseHeldH == 0 and b.shownL == 6


def test_policy_rise_hold_resets_when_ceiling_drops(host):
    s = host.K.strength
    b = _body(host, shownL=5)
    for h in range(1, 6):
        s.policy(b, 7, 8, 100 + h, 1)
    assert b.riseHeldH == 5
    s.policy(b, 7, 5, 106, 1)
    assert b.riseHeldH == 0 and b.shownL == 5


def test_policy_never_above_vanilla(host):
    s = host.K.strength
    b = _body(host, shownL=5)
    for h in range(1, 49):
        assert s.policy(b, 5, 8, 100 + h, 1) == 5


def test_policy_follows_vanilla_down_at_once(host):
    s = host.K.strength
    b = _body(host, shownL=7, lastFallAge=100.0)
    assert s.policy(b, 4, 10, 100.5, 1 / 60) == 4
    assert b.shownL == 4


# --- the band remap ---

@pytest.mark.parametrize("level, want", [
    (0, "WEAK"), (1, "WEAK"), (2, "FEEBLE"), (4, "FEEBLE"), (5, None), (6, "STOUT"), (8, "STOUT"),
    (9, "STRONG"), (10, "STRONG"), (11, "STRONG"),
])
def test_band_of(host, level, want):
    assert host.K.strength.bandOf(level) == want


# --- the acute carry factor ---

def _ea(host, dehyd=0, sweat=False, awake=10, hour=15, caf=False, vitd=False, bf=0.18):
    return host.K.strength.eAcute(dehyd, sweat, awake, hour, caf, vitd, bf)


@pytest.mark.parametrize("kw, want", [
    (dict(), 0.0),
    (dict(dehyd=2), -0.03),
    (dict(dehyd=3.9, sweat=True), -0.045),
    (dict(dehyd=4), -0.06),
    (dict(dehyd=4, sweat=True), -0.09),
    (dict(dehyd=1.9, sweat=True), 0.0),
    (dict(awake=28), -0.04),
    (dict(awake=28, hour=8), -0.02),
    (dict(awake=28, hour=6), -0.02),
    (dict(awake=28, hour=12), -0.04),
    (dict(awake=60), -0.08),
    (dict(awake=18), 0.0),
    (dict(caf=True), 0.02),
    (dict(vitd=True), -0.03),
    (dict(bf=0.33), -0.009),
    (dict(bf=0.30), 0.0),
    (dict(dehyd=5, sweat=True, awake=60, vitd=True, bf=0.6), -0.20),
])
def test_e_acute(host, kw, want):
    assert _close(_ea(host, **kw), want)


def test_e_acute_upper_clamp(host):
    s = host.K.strength
    old = s.CAFFEINE_BONUS
    s.CAFFEINE_BONUS = 0.10
    try:
        assert _close(_ea(host, caf=True), 0.03)
    finally:
        s.CAFFEINE_BONUS = old


# --- the carry delta ---

def test_carry_delta(host):
    assert _close(host.K.strength.carryDelta(1.5, -0.1), 1.35)
    assert _close(host.K.strength.carryDelta(0.75, 0.0), 0.75)
