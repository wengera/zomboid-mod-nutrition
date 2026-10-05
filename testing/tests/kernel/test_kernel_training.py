"""The training signal (NR_Kernel_Training.lua), Plan 3 Task 8.

NR_Kernel_Training.lua is a kernel file (its name is NR_Kernel*), so the session `host` fixture loads it
through its glob and already has NutritionRevamp.kernel.training. Every expectation below is hand-computed
from the file's constants: the engine's resting MET floor 1.5 (Metabolics.Default; spec § 7 item 35);
vanilla's heavy-load factors {1, 1.5, 1.9, 2.3, 2.8} (#2255); the mass reference 80 kg (#0453); the
band METs 6.0 and 9.0 (a game choice, § 7 item 31); the weekly accumulator time constant 7 d (S0576/S0577);
the dose half-saturations K_STR 4 (S0582) and K_HYP 10 (S0576); the strength weights by class (S0575);
the set-equivalents (game choices, § 7 item 30); the maintenance floor 1 high set-equivalent (S0616);
the climb credits (#2632); the hard-day floor 10 band-2 minutes (the endurance report).
"""
import math

import pytest

TOL = 1e-9


def _close(a, b):
    return abs(a - b) < TOL


def _ring(pairs):
    return {i + 1: {1: a, 2: b} for i, (a, b) in enumerate(pairs)}


def _body(host, **kw):
    d = dict(vStr=0.0, vHyp=0.0, vStrHigh=0.0, metMinDay=0.0, band1Day=0.0, band2Day=0.0,
             bandWeek=_ring([(0, 0)] * 7))
    d.update(kw)
    return host.table(d)


# --- constants ---

def test_scalar_constants(host):
    t = host.K.training
    assert t.MET_FLOOR == 1.5 and t.MASS_REF == 80
    assert t.BAND1_MET == 6.0 and t.BAND2_MET == 9.0
    assert t.TAU_V_DAYS == 7 and t.K_STR == 4 and t.K_HYP == 10
    assert t.MAINTAIN_HIGH == 1 and t.HARD_DAY_MIN == 10


def test_set_equivalents(host):
    t = host.K.training
    assert t.S_REP_ARMS == 0.10 and t.S_REP_LEGS == 0.05 and t.S_HIT == 0.05 and t.S_TREE == 0.07
    assert t.S_LOAD_HIGH_PER_MIN == 0.10 and t.S_LOAD_MOD_PER_MIN == 0.05
    assert t.S_ACTION_MOD_PER_MIN == 0.02 and t.S_ACTION_HIGH_PER_MIN == 0.04


def test_table_constants(host):
    t = host.K.training
    assert host.py(t.LOAD_MULT) == {1: 1, 2: 1.5, 3: 1.9, 4: 2.3, 5: 2.8}
    assert host.py(t.W_STR) == dict(low=0.5, moderate=0.8, high=1.0)
    assert host.py(t.CLIMB_MET) == dict(JumpFence=4.0, ClimbRope=8.0)


# --- metMinutes ---

@pytest.mark.parametrize("met, level, w, dt, want", [
    (3.1, 0, 80, 1, 1.6),
    (6.9, 2, 100, 1, 5.4 * 1.9 * 1.25),
    (1.0, 0, 80, 1, 0.0),
    (1.5, 0, 80, 1, 0.0),
    (3.1, 4, 80, 2, 1.6 * 2.8 * 2),
    (3.1, 9, 80, 1, 1.6 * 2.8),
    (3.1, -3, 80, 1, 1.6),
])
def test_met_minutes(host, met, level, w, dt, want):
    assert _close(host.call("training.metMinutes", met, level, w, dt), want)


def test_met_minutes_hand_value(host):
    assert _close(host.call("training.metMinutes", 6.9, 2, 100, 1), 12.825)


# --- band ---

@pytest.mark.parametrize("met, exercising, swiping, want", [
    (6.9, False, False, 1),
    (6.0, False, False, 1),
    (9.5, False, False, 2),
    (9.0, False, False, 2),
    (3.1, True, False, 2),
    (3.1, False, True, 2),
    (1.5, False, False, 0),
    (5.99, False, False, 0),
])
def test_band(host, met, exercising, swiping, want):
    assert host.call("training.band", met, exercising, swiping) == want


# --- sample ---

def test_sample_band0_banks_met_minutes_only(host):
    b = _body(host)
    assert host.call("training.sample", b, 3.1, 0, 80, False, False, 1) == 0
    assert _close(b.metMinDay, 1.6) and b.band1Day == 0 and b.band2Day == 0


def test_sample_band1_adds_band1_only(host):
    b = _body(host)
    assert host.call("training.sample", b, 6.9, 0, 80, False, False, 2) == 1
    assert _close(b.metMinDay, 5.4 * 2) and b.band1Day == 2 and b.band2Day == 0


def test_sample_band2_adds_both_and_accumulates(host):
    b = _body(host, metMinDay=1.0, band1Day=3.0, band2Day=1.0)
    assert host.call("training.sample", b, 3.1, 0, 80, True, False, 1) == 2
    assert _close(b.metMinDay, 2.6) and b.band1Day == 4 and b.band2Day == 2


# --- climbCredit ---

def test_climb_credit_fence(host):
    b = _body(host)
    assert _close(host.call("training.climbCredit", b, "JumpFence", 80), 2.5)
    assert _close(b.metMinDay, 2.5)


def test_climb_credit_rope_scales_by_mass(host):
    b = _body(host, metMinDay=1.0)
    assert _close(host.call("training.climbCredit", b, "ClimbRope", 100), 6.5 * 1.25)
    assert _close(b.metMinDay, 1.0 + 6.5 * 1.25)


@pytest.mark.parametrize("cls", [None, "Unknown"])
def test_climb_credit_unknown_class_is_zero(host, cls):
    b = _body(host, metMinDay=1.0)
    assert host.call("training.climbCredit", b, cls, 80) == 0
    assert b.metMinDay == 1.0


# --- event ---

def test_event_moderate(host):
    b = _body(host)
    host.call("training.event", b, 0.10, "moderate", None)
    assert _close(b.vStr, 0.08) and _close(b.vHyp, 0.10) and b.vStrHigh == 0


def test_event_low(host):
    b = _body(host)
    host.call("training.event", b, 0.10, "low")
    assert _close(b.vStr, 0.05) and _close(b.vHyp, 0.10) and b.vStrHigh == 0


def test_event_high_with_hits(host):
    b = _body(host, vStr=1.0, vHyp=2.0, vStrHigh=0.5)
    host.call("training.event", b, 0.10, "high", 3)
    assert _close(b.vStr, 1.3) and _close(b.vHyp, 2.3) and _close(b.vStrHigh, 0.8)


def test_event_hits_floor_at_one(host):
    b = _body(host)
    host.call("training.event", b, 0.10, "high", 0)
    assert _close(b.vStr, 0.10) and _close(b.vHyp, 0.10) and _close(b.vStrHigh, 0.10)


# --- loadMinute ---

@pytest.mark.parametrize("carried, vstr, vhyp, vhigh", [
    (90, 0.10, 0.10, 0.10),
    (80, 0.10, 0.10, 0.10),
    (60, 0.04, 0.05, 0.0),
    (50, 0.04, 0.05, 0.0),
    (40, 0.0, 0.0, 0.0),
])
def test_load_minute(host, carried, vstr, vhyp, vhigh):
    b = _body(host)
    host.call("training.loadMinute", b, carried, 100, 1)
    assert _close(b.vStr, vstr) and _close(b.vHyp, vhyp) and _close(b.vStrHigh, vhigh)


def test_load_minute_scales_by_dt(host):
    b = _body(host)
    host.call("training.loadMinute", b, 90, 100, 3)
    assert _close(b.vHyp, 0.30) and _close(b.vStrHigh, 0.30)


# --- actionMinute ---

@pytest.mark.parametrize("modifier, moving, vstr, vhyp, vhigh", [
    (8, False, 0.04, 0.04, 0.04),
    (4, False, 0.016, 0.02, 0.0),
    (8, True, 0.0, 0.0, 0.0),
    (3, False, 0.0, 0.0, 0.0),
])
def test_action_minute(host, modifier, moving, vstr, vhyp, vhigh):
    b = _body(host)
    host.call("training.actionMinute", b, modifier, moving, 1)
    assert _close(b.vStr, vstr) and _close(b.vHyp, vhyp) and _close(b.vStrHigh, vhigh)


# --- decay ---

def test_decay_one_time_constant(host):
    b = _body(host, vStr=4.0, vHyp=10.0, vStrHigh=1.0)
    host.call("training.decay", b, 7 * 1440)
    d = math.exp(-1)
    assert _close(b.vStr, 4.0 * d) and _close(b.vHyp, 10.0 * d) and _close(b.vStrHigh, d)


def test_decay_one_minute(host):
    b = _body(host, vStr=2.0, vHyp=2.0, vStrHigh=2.0)
    host.call("training.decay", b, 1)
    d = math.exp(-1 / (7 * 1440))
    assert _close(b.vStr, 2.0 * d) and _close(b.vHyp, 2.0 * d) and _close(b.vStrHigh, 2.0 * d)


# --- doses ---

def test_doses_half_saturation(host):
    b = _body(host, vStr=4.0, vHyp=10.0, vStrHigh=1.0)
    d_str, d_hyp, maintained = host.call("training.doses", b)
    assert _close(d_str, 0.5) and _close(d_hyp, 0.5) and maintained is True


def test_doses_zero_and_not_maintained(host):
    b = _body(host, vStrHigh=0.99)
    d_str, d_hyp, maintained = host.call("training.doses", b)
    assert d_str == 0 and d_hyp == 0 and maintained is False


# --- closeDay ---

def test_close_day_rotates_and_zeroes(host):
    pairs = [(i, 10 * i) for i in range(1, 8)]
    b = _body(host, bandWeek=_ring(pairs), metMinDay=99.0, band1Day=45.0, band2Day=12.0)
    host.call("training.closeDay", b)
    ring = host.py(b.bandWeek)
    assert len(ring) == 7
    want = pairs[1:] + [(45, 12)]
    assert [(ring[i][1], ring[i][2]) for i in range(1, 8)] == want
    assert b.metMinDay == 0 and b.band1Day == 0 and b.band2Day == 0


def test_close_day_slots_stay_distinct_tables(host):
    b = _body(host, band1Day=5.0, band2Day=1.0)
    host.call("training.closeDay", b)
    b.bandWeek[6][1] = 77
    assert b.bandWeek[7][1] == 5 and b.bandWeek[5][1] == 0


# --- weekMinutes ---

def test_week_minutes(host):
    pairs = [(30, 12), (20, 10), (15, 9.9), (0, 0), (40, 5), (10, 0), (5, 0)]
    b = _body(host, bandWeek=_ring(pairs))
    m1, hard = host.call("training.weekMinutes", b)
    assert _close(m1, 120) and hard == 2


def test_week_minutes_empty(host):
    m1, hard = host.call("training.weekMinutes", _body(host))
    assert m1 == 0 and hard == 0
