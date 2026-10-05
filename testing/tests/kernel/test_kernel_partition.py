"""The daily deficit and surplus partition, the lean-gain law and disuse (NR_Kernel_Partition.lua),
Plan 3 Task 9.

NR_Kernel_Partition.lua is a kernel file (its name is NR_Kernel*), so the session `host` fixture loads it
through its glob and already has NutritionRevamp.kernel.partition. Every expectation below is
hand-computed from the file's constants: Alpert's fat ceiling 69 kcal/kg fat/d (S0056); Hall's tissue
densities 1816 and 9441 kcal/kg (S0126 open, design-phase-v1); the protection weights 0.55 and 0.15 with
the 0.30 floor (S0072, S0601; the floor a game choice); the hypertrophy base rate 0.050 kg/d (S0125
open, design-phase-v1); the protein gate 0.8 .. 1.6 g/kg/d (S0509, S0591/S0592); the surplus ramp 500
kcal (a game choice); the deficit half-rate at p >= 2.0 and dStr >= 0.5 (S0064); the lean cap 1.25 x lm0
(a game choice); the alcohol gate 0.5 g/kg and 0.65 (S0718, S0631); the disuse curve 0.171 ln(1 + t/22)
(fitted to S0069, log shape S0612); the FM_MIN / LM_MIN_RATIO guards (game choices). Ruling 7: fat pays
the energy the protection spares beyond the ceiling, so every arm's mass balance closes.
"""
import math

import pytest

TOL = 1e-9


def _close(a, b, tol=TOL):
    return abs(a - b) < tol


def _ring(values):
    return {i + 1: v for i, v in enumerate(values)}


def _body(host, **kw):
    d = dict(fm=14.4, lm=65.6, lm0=65.6, fmRef=14.4, r=1.0, ebDay=0.0, alcDay=0.0, tDisuse=0,
             lm0dis=65.6)
    d.update(kw)
    return host.table(d)


def _f(t):
    return 0.171 * math.log(1 + t / 22)


# --- constants ---

def test_constants(host):
    p = host.K.partition
    assert p.FAT_CEIL_KCAL == 69 and p.RHO_LEAN == 1816 and p.RHO_FAT == 9441
    assert p.PROT_STR == 0.55 and p.PROT_P == 0.15 and p.PROT_FLOOR == 0.30
    assert p.G0 == 0.050 and p.P_LO == 0.8 and p.P_HI == 1.6 and p.SURPLUS_RAMP == 500
    assert p.DEFICIT_HALF_P == 2.0 and p.DEFICIT_HALF_DSTR == 0.5 and p.DEFICIT_HALF == 0.5
    assert p.LM_CAP_RATIO == 1.25 and p.ALC_THRESH == 0.5 and p.G_ALC == 0.65
    assert p.DISUSE_A == 0.171 and p.DISUSE_T == 22
    assert p.FM_MIN == 0.5 and p.LM_MIN_RATIO == 0.35


# --- the gates ---

@pytest.mark.parametrize("p, want", [(1.2, 0.5), (0.5, 0.0), (2.0, 1.0), (0.8, 0.0), (1.6, 1.0)])
def test_g_prot(host, p, want):
    assert _close(host.K.partition.gProt(p), want)


@pytest.mark.parametrize("eb, p, dstr, want", [
    (600, 1, 0, 1.0),
    (250, 1, 0, 0.5),
    (0, 1, 0, 0.0),
    (-100, 2.0, 0.5, 0.5),
    (-100, 1.9, 0.5, 0.0),
    (-100, 2.0, 0.4, 0.0),
])
def test_g_energy(host, eb, p, dstr, want):
    assert _close(host.K.partition.gEnergy(eb, p, dstr), want)


@pytest.mark.parametrize("lm, lm0, want", [
    (65.6, 65.6, 1.0), (82, 65.6, 0.0), (73.8, 65.6, 0.5), (90, 65.6, 0.0), (60, 65.6, 1.0),
])
def test_headroom(host, lm, lm0, want):
    assert _close(host.K.partition.headroom(lm, lm0), want)


@pytest.mark.parametrize("alc, want", [(0, 1), (0.5, 1), (0.51, 0.65), (1.5, 0.65)])
def test_g_alc(host, alc, want):
    assert host.K.partition.gAlc(alc) == want


@pytest.mark.parametrize("dstr, gp, want", [(0, 0, 1.0), (0.5, 1, 0.575), (1, 1, 0.30), (1, 0, 0.45)])
def test_protection(host, dstr, gp, want):
    assert _close(host.K.partition.protection(dstr, gp), want)


# --- the lean-gain law ---

def test_lean_gain_hand_value(host):
    b = _body(host, ebDay=600)
    assert _close(host.K.partition.leanGain(b, 0.5, 0.5, 1.6), 0.025)


def test_lean_gain_alcohol_gate(host):
    # 60 g alcohol over 80 kg = 0.75 g/kg > 0.5, so the product carries 0.65.
    b = _body(host, ebDay=600, alcDay=60)
    assert _close(host.K.partition.leanGain(b, 0.5, 0.5, 1.6), 0.025 * 0.65)


def test_lean_gain_responder_and_headroom(host):
    b = _body(host, ebDay=250, r=1.4, lm=73.8)
    # 0.05 * 1.4 * 1 * gProt(1.2) 0.5 * gEnergy 0.5 * headroom 0.5
    assert _close(host.K.partition.leanGain(b, 1.0, 0.0, 1.2), 0.05 * 1.4 * 0.5 * 0.5 * 0.5)


# --- the deficit arm ---

def test_deficit_untrained(host):
    b = _body(host, ebDay=-2000)
    dfm, dlm = host.K.partition.deficit(b, 0, 0)
    assert _close(dlm, -1006.4 / 1816)
    assert _close(dlm, -0.554185, 1e-6)
    assert _close(dfm, -993.6 / 9441)
    assert _close(dfm, -0.105243, 1e-6)


def test_deficit_protected(host):
    b = _body(host, ebDay=-2000)
    dfm, dlm = host.K.partition.deficit(b, 0.5, 1)
    assert _close(dlm, -1006.4 / 1816 * 0.575)
    assert _close(dlm, -0.318657, 1e-6)
    assert _close(dfm, -(993.6 + 1006.4 * 0.425) / 9441)
    assert _close(dfm, -0.150548, 1e-6)


def test_deficit_mass_balance_closes(host):
    b = _body(host, ebDay=-2000)
    dfm, dlm = host.K.partition.deficit(b, 0.5, 1)
    assert _close(-(dfm * 9441 + dlm * 1816), 2000, 1e-6)


def test_deficit_under_the_cap(host):
    b = _body(host, ebDay=-500)
    dfm, dlm = host.K.partition.deficit(b, 0, 0)
    assert dlm == 0
    assert _close(dfm, -500 / 9441)


# --- the surplus arm ---

def test_surplus_hand_value(host):
    b = _body(host, ebDay=600)
    dfm, dlm = host.K.partition.surplus(b, 0.5, 0.5, 1.6)
    assert _close(dlm, 0.025)
    assert _close(dfm, (600 - 45.4) / 9441)
    assert _close(dfm, 0.058744, 1e-6)


def test_surplus_untrained_is_all_fat(host):
    b = _body(host, ebDay=600)
    dfm, dlm = host.K.partition.surplus(b, 0, 0.5, 1.6)
    assert dlm == 0
    assert _close(dfm, 600 / 9441)


def test_tiny_surplus_caps_lean_at_what_it_pays(host):
    # leanGain = 0.05 * 1 * 1 * gEnergy(10) 0.02 = 0.001 kg; the surplus pays only 10/1816 = 0.0055,
    # so with dHyp 1 the cap does not bind; with r 10 it does (0.01 > 0.0055).
    b = _body(host, ebDay=10, r=10)
    dfm, dlm = host.K.partition.surplus(b, 1.0, 0.5, 1.6)
    assert _close(dlm, 10 / 1816)
    assert _close(dfm, 0)


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


# --- one day ---

def test_day_deficit_applies_and_keeps_fm_ref(host):
    b = _body(host, ebDay=-2000)
    dfm, dlm = host.K.partition.day(b, 0, 0, 0.5, False)
    py = host.py(b)
    assert _close(dfm, -993.6 / 9441) and _close(dlm, -1006.4 / 1816)
    assert _close(py["fm"], 14.4 - 993.6 / 9441)
    assert _close(py["lm"], 65.6 - 1006.4 / 1816)
    assert py["fmRef"] == 14.4


def test_day_surplus_rebases_fm_ref_upward(host):
    b = _body(host, ebDay=600)
    dfm, dlm = host.K.partition.day(b, 0.5, 0.5, 1.6, False)
    py = host.py(b)
    assert _close(dlm, 0.025)
    assert _close(py["lm"], 65.625)
    assert _close(py["fm"], 14.4 + (600 - 45.4) / 9441)
    assert py["fmRef"] == py["fm"]


def test_day_immobilised_takes_the_disuse_arm(host):
    b = _body(host, ebDay=600, tDisuse=5)
    dfm, dlm = host.K.partition.day(b, 1.0, 1.0, 2.0, True)
    assert _close(dlm, -65.6 * (_f(5) - _f(4)))
    assert _close(dfm, 600 / 9441)


def test_day_floors_fm_and_lm(host):
    b = _body(host, fm=0.501, lm=23.0, ebDay=-5000)
    host.K.partition.day(b, 0, 0, 0.5, False)
    py = host.py(b)
    assert py["fm"] == 0.5
    assert _close(py["lm"], 0.35 * 65.6)


# --- the day close and the week ---

def test_close_day_rotates_and_zeroes(host):
    b = _body(host, ebDay=-321, fm=14.0, lm=65.0, inDay=2100, eeDay=2421, actKcalDay=400, exKcalDay=150, pDay=90,
              carbDay=250, lipDay=70, alcDay=14, dayIndex=9,
              eb7=_ring([1, 2, 3, 4, 5, 6, 7]), mass7=_ring([80, 81, 82, 83, 84, 85, 86]),
              p7=_ring([0] * 7), carb7=_ring([0] * 7), lip7=_ring([0] * 7))
    host.K.partition.closeDay(b, 247.0)
    py = host.py(b)
    assert py["lastCloseAgeH"] == 247.0
    assert list(py["eb7"].values()) == [2, 3, 4, 5, 6, 7, -321]
    assert list(py["mass7"].values()) == [81, 82, 83, 84, 85, 86, 79.0]
    for k in ("inDay", "eeDay", "ebDay", "actKcalDay", "exKcalDay", "pDay", "carbDay", "lipDay", "alcDay"):
        assert py[k] == 0, k
    assert py["dayIndex"] == 10


def test_close_day_keeps_the_closed_day_macros_in_the_newest_cell(host):
    # Task 15: the legacy mirror blends today with yesterday, so closeDay pushes pDay, carbDay and
    # lipDay into the newest cell of p7, carb7 and lip7 before it zeroes them.
    b = _body(host, ebDay=0, fm=14.0, lm=65.0, inDay=0, eeDay=0, actKcalDay=0, pDay=96, carbDay=310,
              lipDay=72, alcDay=0, dayIndex=3, eb7=_ring([0] * 7), mass7=_ring([79] * 7),
              p7=_ring([10, 20, 30, 40, 50, 60, 70]), carb7=_ring([1, 2, 3, 4, 5, 6, 7]),
              lip7=_ring([7, 6, 5, 4, 3, 2, 1]))
    host.K.partition.closeDay(b, 79.0)
    py = host.py(b)
    assert py["lastCloseAgeH"] == 79.0
    assert list(py["p7"].values()) == [20, 30, 40, 50, 60, 70, 96]
    assert list(py["carb7"].values()) == [2, 3, 4, 5, 6, 7, 310]
    assert list(py["lip7"].values()) == [6, 5, 4, 3, 2, 1, 72]
    assert py["pDay"] == 0 and py["carbDay"] == 0 and py["lipDay"] == 0


@pytest.mark.parametrize("ring, want", [
    ([100, -200, 50, 0, 0, 0, 0], True),
    ([100, -50, 0, 0, 0, 0, 0], False),
    ([0] * 7, False),
])
def test_deficit_week(host, ring, want):
    b = _body(host, eb7=_ring(ring))
    assert host.K.partition.deficitWeek(b) is want


def test_day_deficit_half_credit_runs(host):
    # Ruling W-3: p 2.4, dStr 0.6, dHyp 0.5 in a deficit -> leanGain 0.050 * r 1 * 0.5 * gProt 1 *
    # gEnergy 0.5 * headroom 1 * gAlc 1 = 0.0125 kg, fat paying it at 1816 / 9441
    b = _body(host, ebDay=-2000)
    dfm, dlm = host.K.partition.day(b, 0.5, 0.6, 2.4, False)
    prot = max(1 - 0.55 * 0.6 - 0.15 * 1, 0.30)                        # 0.52
    gain = 0.050 * 1.0 * 0.5 * 1 * 0.5 * 1 * 1
    assert _close(gain, 0.0125)
    lean_loss = 1006.4 / 1816 * prot
    assert _close(dlm, -lean_loss + gain)
    assert _close(dfm, -(993.6 + 1006.4 * (1 - prot)) / 9441 - gain * 1816 / 9441)
    assert _close(dfm * 9441 + dlm * 1816, -2000, 1e-6)                # the balance identity holds
    py = host.py(b)
    assert _close(py["lm"], 65.6 - lean_loss + gain)


def test_day_deficit_no_half_credit_below_the_protein_edge(host):
    # Ruling W-3: at p 1.6 the deficit gate reads 0, so the deficit arm stands unchanged
    b = _body(host, ebDay=-2000)
    dfm, dlm = host.K.partition.day(b, 0.5, 0.6, 1.6, False)
    want_fm, want_lm = host.K.partition.deficit(_body(host, ebDay=-2000), 0.6, 1.0)
    assert dlm == want_lm and dfm == want_fm
    assert _close(dfm * 9441 + dlm * 1816, -2000, 1e-6)


def test_day_deficit_reads_the_protein_gate_from_p(host):
    # p 1.6 -> gProt 1 -> protection 1 - 0.15 = 0.85 at dStr 0
    b = _body(host, ebDay=-2000)
    dfm, dlm = host.K.partition.day(b, 0, 0, 1.6, False)
    assert _close(dlm, -1006.4 / 1816 * 0.85)
    assert _close(dfm, -(993.6 + 1006.4 * 0.15) / 9441)
