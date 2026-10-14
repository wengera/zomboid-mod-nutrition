"""The training signal (NR_Kernel_Training.lua), Plan 3 Task 8; the aerobic side only since Plan 13 Task 12
(ruling 13-18: the resistance side -- event, loadMinute, actionMinute, decay, doses and their constants -- is removed).

NR_Kernel_Training.lua is a kernel file (its name is NR_Kernel*), so the session `host` fixture loads it
through its glob and already has NutritionRevamp.kernel.training. Every expectation below is hand-computed
from the file's constants: the engine's resting MET floor 1.5 (Metabolics.Default; spec § 7 item 35);
vanilla's heavy-load factors {1, 1.5, 1.9, 2.3, 2.8} (#2255); the mass reference 80 kg (#0453); the
band METs 6.0 and 9.0 (a game choice, § 7 item 31); the climb credits (#2632); the hard-day floor 10 band-2
minutes (the endurance report).
"""
import math

import pytest

TOL = 1e-9


def _close(a, b):
    return abs(a - b) < TOL


def _ring(pairs):
    return {i + 1: {1: a, 2: b} for i, (a, b) in enumerate(pairs)}


def _body(host, **kw):
    d = dict(metMinDay=0.0, band1Day=0.0, band2Day=0.0, bandWeek=_ring([(0, 0)] * 7))
    d.update(kw)
    return host.table(d)


# --- constants ---

def test_scalar_constants(host):
    t = host.K.training
    assert t.MET_FLOOR == 1.5 and t.MASS_REF == 80
    assert t.BAND1_MET == 6.0 and t.BAND2_MET == 9.0
    assert t.HARD_DAY_MIN == 10


def test_the_resistance_side_is_gone(host):
    # ruling 13-18: the Strength signal is the AddXP capture's (K.strength.signalClose); nothing of the old side stays
    t = host.K.training
    for name in ("event", "loadMinute", "actionMinute", "decay", "doses", "W_STR", "TAU_V_DAYS", "K_STR", "K_HYP",
                 "MAINTAIN_HIGH", "S_REP_ARMS", "S_REP_LEGS", "S_HIT", "S_TREE", "S_LOAD_HIGH_PER_MIN",
                 "S_LOAD_MOD_PER_MIN", "S_ACTION_MOD_PER_MIN", "S_ACTION_HIGH_PER_MIN"):
        assert t[name] is None, name


def test_table_constants(host):
    t = host.K.training
    assert host.py(t.LOAD_MULT) == {1: 1, 2: 1.5, 3: 1.9, 4: 2.3, 5: 2.8}
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
