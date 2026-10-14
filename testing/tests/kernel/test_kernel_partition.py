"""The disuse arm, the alcohol gate and the day close (NR_Kernel_Partition.lua), Plan 3 Task 9; the Plan 3 lean arms
(gProt, gEnergy, headroom, leanGain, protection, deficit, surplus, day and their constants, FM_MIN and LM_MIN_RATIO
among them) are removed in Plan 13 Task 12: the lean-mass arms (forbes, training, surplusLean, deficitLean) are
tested against the oracle in test_strength_parity.py and test_strength_day.py, and the floors are
K.strength.DEFAULTS' fmMin and fMinShare (ruling 13-35).

NR_Kernel_Partition.lua is a kernel file (its name is NR_Kernel*), so the session `host` fixture loads it
through its glob and already has NutritionRevamp.kernel.partition. Every expectation below is
hand-computed from the file's constants: Alpert's fat ceiling 69 kcal/kg fat/d (S0056); Hall's tissue
densities 1816 and 9441 kcal/kg (S0126 open, design-phase-v1); the alcohol gate 0.5 g/kg and 0.65 (S0718, S0631);
the disuse curve 0.171 ln(1 + t/22) (fitted to S0069, log shape S0612).
"""
import math

import pytest

TOL = 1e-9


def _close(a, b, tol=TOL):
    return abs(a - b) < tol


def _ring(values):
    return {i + 1: v for i, v in enumerate(values)}


def _body(host, **kw):
    d = dict(fm=14.4, lm=65.6, lx=0.0, fmRef=14.4, ebDay=0.0, alcDay=0.0, tDisuse=0, lm0dis=65.6)
    d.update(kw)
    return host.table(d)


def _f(t):
    return 0.171 * math.log(1 + t / 22)


# --- constants ---

def test_constants(host):
    p = host.K.partition
    assert p.FAT_CEIL_KCAL == 69 and p.RHO_LEAN == 1816 and p.RHO_FAT == 9441
    assert p.ALC_THRESH == 0.5 and p.G_ALC == 0.65
    assert p.DISUSE_A == 0.171 and p.DISUSE_T == 22


def test_the_plan_3_lean_arms_are_gone(host):
    # spec section 9.2 and the plan's file table: the lean-mass arms replace them; the floors moved to DEFAULTS
    p = host.K.partition
    for name in ("gProt", "gEnergy", "headroom", "leanGain", "protection", "deficit", "surplus", "day", "G0",
                 "LM_CAP_RATIO", "P_LO", "P_HI", "SURPLUS_RAMP", "DEFICIT_HALF_P", "DEFICIT_HALF_DSTR",
                 "DEFICIT_HALF", "PROT_STR", "PROT_P", "PROT_FLOOR", "FM_MIN", "LM_MIN_RATIO"):
        assert p[name] is None, name
    D = host.K.strength.DEFAULTS
    assert D.fmMin == 0.5 and D.fMinShare == 0.35


def test_the_lean_arms_sit_beside_the_fat_ceiling():
    # the Task 7 review's carry (Task 12 amendment 6): the lean-mass arms follow the densities, before the disuse arm
    import os
    path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))),
                        "mod", "NutritionRevamp", "common", "media", "lua", "shared", "NR_Kernel_Partition.lua")
    with open(path, encoding="utf-8") as fh:
        src = fh.read()
    order = [src.index(k) for k in ("K.partition.FAT_CEIL_KCAL =", "K.partition.RHO_FAT =",
                                    "function K.partition.forbes(", "function K.partition.deficitLean(",
                                    "function K.partition.disuse(", "function K.partition.closeDay(")]
    assert order == sorted(order)


# --- the gates ---

@pytest.mark.parametrize("alc, want", [(0, 1), (0.5, 1), (0.51, 0.65), (1.5, 0.65)])
def test_g_alc(host, alc, want):
    assert host.K.partition.gAlc(alc) == want


# --- disuse ---

def test_disuse_fraction(host):
    p = host.K.partition
    assert _close(p.disuseFraction(5), 0.171 * math.log(1.227273), 1e-6)
    # the plan printed 0.035021; 0.171 * ln(1 + 5/22) = 0.0350198, which rounds to 0.035020
    assert _close(p.disuseFraction(5), 0.035020, 1e-6)
    assert p.disuseFraction(0) == 0


def test_disuse_day_five(host):
    b = _body(host, ebDay=-500, tDisuse=5, lm=64.0)
    dfm, dlm = host.K.partition.disuse(b)
    assert _close(dlm, -65.6 * (_f(5) - _f(4)))
    assert _close(dfm, -500 / 9441)


def test_disuse_deficit_beyond_the_ceiling_is_unpaid(host):
    b = _body(host, ebDay=-2000, tDisuse=1)
    dfm, dlm = host.K.partition.disuse(b)
    assert _close(dfm, -993.6 / 9441)
    assert _close(dlm, -65.6 * _f(1))


def test_disuse_guards_a_zero_day_as_day_one(host):
    # Close fix wave (T9 review): tDisuse 0 reads as day 1, the same loss, no f(-1) term and no NaN.
    b0 = _body(host, ebDay=-500, tDisuse=0)
    b1 = _body(host, ebDay=-500, tDisuse=1)
    dfm0, dlm0 = host.K.partition.disuse(b0)
    dfm1, dlm1 = host.K.partition.disuse(b1)
    assert dlm0 == dlm1 and dfm0 == dfm1
    assert dlm0 == dlm0
    assert _close(dlm0, -65.6 * _f(1))


def test_disuse_surplus_is_stored_as_fat(host):
    b = _body(host, ebDay=300, tDisuse=2)
    dfm, dlm = host.K.partition.disuse(b)
    assert _close(dfm, 300 / 9441)
    assert _close(dlm, -65.6 * (_f(2) - _f(1)))


# --- the day close and the week ---

def test_close_day_rotates_and_zeroes(host):
    b = _body(host, ebDay=-321, fm=14.0, lm=64.0, lx=1.0, inDay=2100, eeDay=2421, actKcalDay=400, exKcalDay=150, pDay=90,
              carbDay=250, lipDay=70, alcDay=14, dayIndex=9,
              eb7=_ring([1, 2, 3, 4, 5, 6, 7]), mass7=_ring([80, 81, 82, 83, 84, 85, 86]),
              p7=_ring([0] * 7))
    host.K.partition.closeDay(b)
    py = host.py(b)
    assert "lastCloseAgeH" not in py                     # the trailing window runs on the clock (Plan 11d Task 9c)
    assert list(py["eb7"].values()) == [2, 3, 4, 5, 6, 7, -321]
    assert list(py["mass7"].values()) == [81, 82, 83, 84, 85, 86, 79.0]   # fm + lm + lx (ruling 13-20)
    for k in ("inDay", "eeDay", "ebDay", "actKcalDay", "exKcalDay", "pDay", "carbDay", "lipDay", "alcDay"):
        assert py[k] == 0, k
    assert py["dayIndex"] == 10


def test_close_day_keeps_the_closed_day_protein_in_the_newest_cell(host):
    # closeDay pushes pDay into the newest cell of p7 (NR_Server_Effects' protein week) before it zeroes the day's
    # macros; since Plan 11d Task 9c no carbohydrate or lipid ring is kept (the trailing window reads the clock)
    b = _body(host, ebDay=0, fm=14.0, lm=65.0, inDay=0, eeDay=0, actKcalDay=0, pDay=96, carbDay=310,
              lipDay=72, alcDay=0, dayIndex=3, eb7=_ring([0] * 7), mass7=_ring([79] * 7),
              p7=_ring([10, 20, 30, 40, 50, 60, 70]))
    host.K.partition.closeDay(b)
    py = host.py(b)
    assert list(py["p7"].values()) == [20, 30, 40, 50, 60, 70, 96]
    assert "carb7" not in py and "lip7" not in py
    assert py["pDay"] == 0 and py["carbDay"] == 0 and py["lipDay"] == 0


@pytest.mark.parametrize("ring, want", [
    ([100, -200, 50, 0, 0, 0, 0], True),
    ([100, -50, 0, 0, 0, 0, 0], False),
    ([0] * 7, False),
])
def test_deficit_week(host, ring, want):
    b = _body(host, eb7=_ring(ring))
    assert host.K.partition.deficitWeek(b) is want

