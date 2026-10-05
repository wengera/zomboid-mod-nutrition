"""Trained aerobic capacity and the two endurance coefficients (NR_Kernel_Aerobic.lua), Plan 3 Task 11.

NR_Kernel_Aerobic.lua is a kernel file (its name is NR_Kernel*), so the session `host` fixture loads it
through its glob and already has NutritionRevamp.kernel.aerobic. Every expectation below is hand-computed
from the file's constants: TAC clamped [0.80, 1.25] (floor a game choice; ceiling S0661/S0662/S0666); the
gain on 15 days toward 1 + 0.25 x the weekly volume over 240 minutes (S0668); the loss on 84 days toward
the floor (calibrated to S0675) unless two hard days held it (S0669); the protein gate 0.85 below 0.8
g/kg/d (S0715, S0509); the energy gate 0.5 below 30 kcal per kg lean (S0691/S0692); the sleep gate 1 at
8 h of debt to 0.70 at 24 h (S0721; a game choice); the excess-fat percentage over the sex's normal-band
fat at 80 kg (S1051 open, design-phase-v1; Ruling T6-1); the drain coefficient TAC^-0.8 x glycogen x
dehydration x heat x fat load x iron x hours awake x caffeine capped at 2.5, and the regeneration
coefficient TAC^1.2 x glycogen x protein x iron x dehydration x sleep debt x alcohol x balance floored at
0.25 (game choices § 7 item 31; S0684, S0706/S0707, S0730 open, S1021, S0723, S0696/S0697/S0694, S0699,
S0763, S0531, S0762, S0718).
"""
import math

import pytest

TOL = 1e-9


def _close(a, b, tol=TOL):
    return abs(a - b) < tol


def _body(host, tac):
    return host.table(dict(tac=tac))


def _tac(host, tac, week, hard, gi=1.0, gp=1.0, ge=1.0, gs=1.0, dtD=1.0):
    body = host.K.aerobic.tacDay(_body(host, tac), week, hard, gi, gp, ge, gs, dtD)
    return body.tac


# The neutral drain and regeneration arguments: TAC 1, glycogen full, no dehydration, heat 0, no excess
# fat, iron replete, 10 h awake, no caffeine; protein factor 1, no sleep debt, no alcohol, no bonus.
D0 = dict(tac=1.0, g=1.0, dehydPct=0.0, heatLevel=0, excessPct=0.0, ironGrade=1, hoursAwake=10.0,
          cafEffect=0.0, cafTol=0.0)
R0 = dict(tac=1.0, g=1.0, protFactor=1.0, ironGrade=1, dehydPct=0.0, debtH=0.0, alcGPerKg=0.0,
          balanceBonus=1.0)


def _dmod(host, **kw):
    a = dict(D0)
    a.update(kw)
    return host.K.aerobic.dmod(a["tac"], a["g"], a["dehydPct"], a["heatLevel"], a["excessPct"],
                               a["ironGrade"], a["hoursAwake"], a["cafEffect"], a["cafTol"])


def _rmod(host, **kw):
    a = dict(R0)
    a.update(kw)
    return host.K.aerobic.rmod(a["tac"], a["g"], a["protFactor"], a["ironGrade"], a["dehydPct"], a["debtH"],
                               a["alcGPerKg"], a["balanceBonus"])


def test_constants(host):
    A = host.K.aerobic
    assert (A.TAC_MIN, A.TAC_MAX, A.TAU_GAIN, A.TAU_LOSS) == (0.80, 1.25, 15, 84)
    assert (A.VOL_WEEK_FULL, A.HARD_DAYS_KEEP, A.G_PROT_LOW, A.P_LOW) == (240, 2, 0.85, 0.8)
    assert (A.EA_THRESHOLD, A.G_ENERGY_LOW, A.G_SLEEP_SEVERE) == (30, 0.5, 0.70)
    assert list(host.py(A.G_IRON).values()) == [1.0, 0.7, 0.4, 0.4]
    assert (A.EXP_D, A.EXP_R, A.D_CAP, A.R_FLOOR, A.GLYC_D) == (-0.8, 1.2, 2.5, 0.25, 0.35)
    assert (A.HYDR_T1, A.HYDR_K1, A.HYDR_T2, A.HYDR_K2) == (2, 0.03, 4, 0.09)
    assert list(host.py(A.HEAT).values()) == [1.0, 1.10, 1.25, 1.50, 2.00]
    assert (A.HEAT_HYDR_K, A.FAT_LOAD_K) == (0.10, 0.008)
    assert list(host.py(A.IRON_D).values()) == [1.0, 1.03, 1.08, 1.20]
    assert list(host.py(A.IRON_R).values()) == [1.0, 0.95, 0.88, 0.75]
    assert (A.AWAKE_KNEE, A.AWAKE_K, A.AWAKE_CAP, A.CAF_K) == (18, 0.004, 1.20, 0.03)
    assert (A.HYDR_R_K, A.HYDR_R_FLOOR, A.DEBT_R_K, A.DEBT_R_FLOOR, A.ALC_K, A.ALC_T) == (0.05, 0.70, 0.01, 0.60, 0.15, 0.5)


def test_fm_normal_80_reads_the_body_anchors(host):
    # Ruling T6-1: the excess reference is the sex's normal-band fat at 80 kg, a reading of K.body's anchors
    fm = host.py(host.K.aerobic.FM_NORMAL_80)
    assert _close(fm[1], 14.4) and _close(fm[2], 22.4)
    assert _close(fm[1], host.K.body.BF_MALE[4] * 80) and _close(fm[2], host.K.body.BF_FEMALE[4] * 80)


def test_gprot(host):
    assert host.K.aerobic.gProt(1.0) == 1
    assert host.K.aerobic.gProt(0.8) == 1                    # the edge reads adequate
    assert host.K.aerobic.gProt(0.7) == 0.85


def test_genergy(host):
    assert (2400 - 300) / 65.6 == pytest.approx(32.0, abs=0.05)
    assert host.K.aerobic.gEnergy(2400, 300, 65.6) == 1
    assert (1500 - 300) / 65.6 == pytest.approx(18.3, abs=0.05)
    assert host.K.aerobic.gEnergy(1500, 300, 65.6) == 0.5
    assert host.K.aerobic.gEnergy(30 * 60 + 300, 300, 60) == 1   # EA exactly 30 reads available


def test_gsleep(host):
    assert host.K.aerobic.gSleep(0) == 1
    assert host.K.aerobic.gSleep(8) == 1
    assert _close(host.K.aerobic.gSleep(16), 0.85)
    assert _close(host.K.aerobic.gSleep(24), 0.70)
    assert _close(host.K.aerobic.gSleep(100), 0.70)


def test_tac_gain_full_volume(host):
    assert _close(_tac(host, 1.0, 240, 2), 1.0 + 0.25 / 15)
    assert _close(_tac(host, 1.0, 240, 2), 1.016667, 1e-6)
    assert _close(_tac(host, 1.0, 480, 0), 1.0 + 0.25 / 15)          # volume saturates at 240 min
    assert _close(_tac(host, 1.0, 120, 0), 1.0 + 0.125 / 15)          # half volume, target 1.125


def test_tac_loss_and_maintenance(host):
    assert _close(_tac(host, 1.2, 0, 0), 1.2 - 0.4 / 84)
    assert _close(_tac(host, 1.2, 0, 0), 1.195238, 1e-6)
    assert _tac(host, 1.2, 0, 2) == 1.2                                # two hard days hold the gain
    assert _close(_tac(host, 1.2, 0, 1), 1.2 - 0.4 / 84)              # one is not enough


def test_tac_gates_scale_the_rise(host):
    full = _tac(host, 1.0, 240, 2) - 1.0
    assert _close(_tac(host, 1.0, 240, 2, ge=0.5) - 1.0, full * 0.5)
    assert _close(_tac(host, 1.0, 240, 2, gs=0.7, ge=1.0) - 1.0, full * 0.7)      # min(Genergy, Gsleep)
    assert _close(_tac(host, 1.0, 240, 2, gs=0.7, ge=0.5) - 1.0, full * 0.5)
    assert _close(_tac(host, 1.0, 240, 2, gi=0.7, gp=0.85) - 1.0, full * 0.7 * 0.85)


def test_tac_clamps(host):
    assert _tac(host, 1.0, 240, 2, dtD=100) == 1.25
    assert _tac(host, 1.3, 240, 0) == 1.25
    assert _tac(host, 0.7, 0, 0, gi=0.0) == 0.80


def test_tac_returns_the_body(host):
    body = _body(host, 1.0)
    out = host.K.aerobic.tacDay(body, 240, 2, 1, 1, 1, 1, 1)
    assert host.rt.eval("rawequal")(out, body)


def test_excess_pct(host):
    assert _close(host.K.aerobic.excessPct(20, 14.4, 80), 7.0)
    assert host.K.aerobic.excessPct(10, 14.4, 80) == 0


def test_dmod_neutral_is_exactly_one(host):
    assert _dmod(host) == 1


def test_dmod_tac(host):
    assert _close(_dmod(host, tac=1.1), 1.1 ** -0.8)
    assert _close(_dmod(host, tac=1.1), 0.926592, 1e-5)          # the plan's rounding; exact 0.9265863


@pytest.mark.parametrize("kw,factor", [
    (dict(g=0.0), 1.35),                                             # glycogen empty, S0684
    (dict(g=0.5), 1 + 0.35 * 0.25),
    (dict(dehydPct=2.0), 1.0),                                       # below the first threshold
    (dict(dehydPct=3.0), 1.03),
    (dict(dehydPct=5.0), 1 + 0.09 + 0.09),
    (dict(heatLevel=2), 1.25),                                       # HEAT index 3
    (dict(heatLevel=4), 2.00),
    (dict(heatLevel=2, dehydPct=4.0), 1.25 * (1 + 0.10 * 1 * 1) * 1.06),
    (dict(excessPct=10.0), 1.08),
    (dict(ironGrade=4), 1.20),
    (dict(ironGrade=2), 1.03),
    (dict(hoursAwake=18.0), 1.0),                                    # the knee, ruling 11
    (dict(hoursAwake=28.0), 1.04),
    (dict(hoursAwake=100.0), 1.20),                                  # capped
    (dict(cafEffect=1.0, cafTol=0.0), 0.97),
    (dict(cafEffect=1.0, cafTol=0.5), 0.985),
])
def test_dmod_terms(host, kw, factor):
    assert _close(_dmod(host, **kw), factor)


def test_dmod_stacked_worst_case_caps(host):
    v = _dmod(host, tac=0.8, g=0.0, dehydPct=6.0, heatLevel=4, excessPct=30.0, ironGrade=4, hoursAwake=100.0)
    assert v == 2.5


def test_rmod_neutral_is_exactly_one(host):
    assert _rmod(host) == 1


def test_rmod_tac(host):
    assert _close(_rmod(host, tac=1.1), 1.1 ** 1.2)
    assert _close(_rmod(host, tac=1.1), 1.121171, 1e-5)          # the plan's rounding; exact 1.1211694


@pytest.mark.parametrize("kw,factor", [
    (dict(g=0.0), 0.5),
    (dict(protFactor=0.85), 0.85),
    (dict(ironGrade=4), 0.75),
    (dict(ironGrade=3), 0.88),
    (dict(dehydPct=4.0), 0.9),
    (dict(dehydPct=20.0), 0.70),                                     # dehydration floor
    (dict(debtH=10.0), 0.9),
    (dict(debtH=100.0), 0.6),                                        # sleep-debt floor
    (dict(alcGPerKg=0.5), 1.0),                                      # at the threshold
    (dict(alcGPerKg=0.75), 1 - 0.15 * 0.5),
    (dict(alcGPerKg=1.0), 0.85),
    (dict(alcGPerKg=3.0), 0.85),                                     # saturated
    (dict(balanceBonus=1.05), 1.05),
])
def test_rmod_terms(host, kw, factor):
    assert _close(_rmod(host, **kw), factor)


def test_rmod_stacked_worst_case_floors(host):
    v = _rmod(host, tac=0.8, g=0.0, protFactor=0.85, ironGrade=4, dehydPct=20.0, debtH=100.0, alcGPerKg=3.0)
    assert v == 0.25
