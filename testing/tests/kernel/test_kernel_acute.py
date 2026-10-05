"""Caffeine, alcohol, glycogen and glucose, sleep, the impairment unit and refeeding (NR_Kernel_Acute.lua),
Plan 4 Task 9.

NR_Kernel_Acute.lua is a kernel file (its name is NR_Kernel*), so the session `host` fixture loads it through
its glob and already has NutritionRevamp.kernel.acute. Every expectation below was recomputed in Python
doubles from the file's constants before it was written (the expression sits in the comment beside it):
caffeine t1/2 5.0 h (S0793) and 9.7 h slow (S0793's arm; S0794; open S1103), the effect at 3 mg/kg (S0531,
S0626), tolerance toward mean/400 on tau 7 d (S0807; tau_down open S0848), withdrawal 12/36/120 h (S0805);
Widmark r 0.68/0.55 (open S1104), beta 0.015 %/h (open S1105), the hangover (open S0854), the alcohol IU
knots (S0893, S0905); glycogen 462 (S0679), +102/-253 (S0680; open S1108), 51.5 mmol/kg/h at MET 7.5
(S0683; open S1107), shivering 52 (S0049); blood glucose 5.0 (S0684), 2.5 under exertion (open S1109), 3.0
alcohol-fasting (S1015; open S1110), tau 15 min / 1 h (open S1111); sleep chi_w 18.2 / chi_s 4.2 (S0733,
S0734; debt terms open S1114), need 7.5 h (S0740), the window debt and the 0.5 repayment (S0742, S0743;
open S1113), the nap rule (open S1112), circ 0.12 at 04:00 (S0736; open S0861); the IU terms (S0892,
S0894/S0895, S0897/S0898, S0906, S0899/S0900; zero point open S1115); refeeding (S0115-S0117; open
S1116/S1117). Two briefing hand values were corrected in doubles: the slow-metaboliser load after 5 h is
200 * 2 ** (-5 / 9.7) = 139.9136 (not 139.94), and S after 24 h awake is 1 - 0.83 * exp(-24 / 18.2) =
0.777985 (not 0.7777). Time is game hours throughout (ruling T5-1).
"""
import math
import pytest

TOL = 1e-9
MIN = 1 / 60


def _close(a, b, tol=TOL):
    return abs(a - b) < tol


def _new(host, ageH=0.0):
    return host.K.acute.new(ageH)


def _list(host, t):
    return list(host.py(t).values())


def test_constants(host):
    A = host.K.acute
    assert (A.AV, A.CAF_ABSORB, A.CAF_THALF_H, A.CAF_THALF_SLOW_H, A.CAF_SLOW_SHARE) == (1, 1.0, 5.0, 9.7, 0.5)
    assert (A.CAF_MEAN_H, A.CAF_TOL_REF, A.CAF_TOL_TAU_H, A.CAF_WD_TOL, A.CAF_WD_LOW_MG) == (168, 400, 168, 0.25, 10.7)
    assert (A.CAF_WD_ONSET_H, A.CAF_WD_PEAK_H, A.CAF_WD_END_H, A.CAF_EFFECT_MGKG) == (12, 36, 120, 3)
    assert _list(host, A.WIDMARK_R) == [0.68, 0.55]
    assert (A.BETA, A.HANG_PEAK, A.HANG_H, A.IU_ALC_CAP) == (0.015, 0.05, 6, 2.0)
    assert [_list(host, k) for k in _list(host, A.IU_ALC_KNOTS)] == [[0, 0], [0.03, 0.30], [0.05, 1.00], [0.08, 1.60]]
    assert (A.GLYC_REF, A.GLYC_HIGH, A.GLYC_LOW, A.GLYC_PIVOT, A.GLYC_SPAN, A.GLYC_TAU_H, A.GLYC_MAX) == (462, 102, 253, 3, 3, 24, 600)
    assert (A.USE_WORK, A.USE_MET_LO, A.USE_MET_SPAN, A.USE_MAX, A.USE_SHIVER, A.SHIVER_SPAN) == (51.5, 3, 4.5, 1.6, 52, 2.5)
    assert (A.BG_NORMAL, A.BG_EXERTION, A.BG_EX_G, A.BG_EX_MET, A.BG_ALC_FAST, A.BG_ALC_FAST_H) == (5.0, 2.5, 0.2, 6, 3.0, 12)
    assert (A.BG_TAU_CHO_H, A.BG_TAU_H, A.BG_MIN, A.BG_MAX, A.IU_BG_HI, A.IU_BG_LO, A.IU_BG_MAX) == (0.25, 1, 2.0, 8.0, 3.5, 3.0, 0.90)
    assert (A.SLEEP_NEED_H, A.CHI_W, A.CHI_S, A.CHI_W_DEBT, A.CHI_W_DEBT_MAX, A.S_FLOOR_DEBT, A.S_FLOOR_MAX) == (7.5, 18.2, 4.2, 0.02, 20, 0.01, 0.25)
    assert (A.S_RESTED, A.NAP_MIN_H, A.WINDOW_H, A.DEBT_MAX, A.REPAY, A.CIRC_AMP, A.CIRC_PEAK_H) == (0.17, 1, 24, 40, 0.5, 0.12, 4)
    assert (A.IU_SLEEP_ZERO_H, A.IU_SLEEP_SPAN_H, A.IU_SLEEP_DEBT_H, A.IU_SLEEP_MAX) == (16, 8, 10.5, 1.5)
    assert (A.IU_DEHYD_FROM, A.IU_DEHYD_KNEE, A.IU_DEHYD_SLOPE1, A.IU_DEHYD_SLOPE2, A.IU_DEHYD_MAX) == (1, 2, 0.45, 0.22, 0.89)
    assert _list(host, A.IU_IRON) == [0, 0, 0.38, 0.76]
    assert (A.CREDIT_BASE, A.CREDIT_GAIN, A.CREDIT_MG, A.IU_MAX) == (0.50, 0.60, 200, 2.5)
    assert (A.LOW_KCAL_KG, A.HEIGHT_M, A.MASS_WINDOW_H) == (5, 1.75, 2160)
    assert (A.RISK_BMI_HIGH, A.RISK_LOSS_HIGH, A.RISK_DAYS_HIGH, A.RISK_BMI_MOD, A.RISK_LOSS_MOD, A.RISK_DAYS_MOD) == (16, 0.15, 10, 18.5, 0.10, 5)
    assert (A.REFEED_DAYS, A.RESTART_KCAL_KG, A.RESTART_LOW_KCAL_KG, A.RESTART_LOW_BMI, A.REFEED_P) == (7, 10, 5, 14, 0.23)


def test_new_state_shape(host):
    a = host.py(_new(host, 100.0))
    assert a == dict(av=1, caf=0, cafMean=0, cafTol=0, cafLowH=0, wdH=-1, wd=0, slowMet=False, alc=0, bac=0,
                     alcPeak=0, hangH=0, hang=0, glyc=462, g=1, bg=5.0, awakeH=0, debtH=0, sleptH=0,
                     winStartH=100.0, winSleptH=0, S=0.17, circ=0, frozen=False, starvedDays=0, lowDay=False,
                     mass90max=0, mass90ageH=100.0, bmi=0, refeedRisk=0, refeedDayN=-1, refeedEvent=False, iu=0)


def test_draw_slow_met(host):
    A = host.K.acute
    assert A.drawSlowMet(0.49) is True
    assert A.drawSlowMet(0.5) is False


# ---- caffeine ----

def test_caffeine_halflife_normal_and_slow(host):
    A = host.K.acute
    a = _new(host)
    A.caffeine(a, 200, 80, 0)
    A.caffeine(a, 0, 80, 5)
    assert _close(a.caf, 100.0)  # 200 * exp(-ln2 * 5 / 5)
    b = _new(host)
    b.slowMet = True
    A.caffeine(b, 200, 80, 0)
    for _ in range(300):
        A.caffeine(b, 0, 80, MIN)
    assert _close(b.caf, 139.91358827433697, 1e-9)  # 200 * exp(-ln2 * 5 / 9.7); the briefing's 139.94 is a slip


def test_caf_effect_and_active(host):
    A = host.K.acute
    a = _new(host)
    a.caf = 240
    assert _close(A.cafEffect(a, 80), 1.0)  # 240 / (3 * 80)
    assert A.caffeineActive(a, 80) is True
    a.caf = 120
    assert _close(A.cafEffect(a, 80), 0.5)
    assert A.caffeineActive(a, 80) is False
    a.caf = 1000
    assert A.cafEffect(a, 80) == 1


def test_caffeine_mean_is_a_daily_rate(host):
    A = host.K.acute
    a = _new(host)
    a.cafMean = 400
    for _ in range(1440):
        A.caffeine(a, 400 / 1440, 80, MIN)  # sample (400/1440) * 24 / (1/60) = 400 mg/day
    assert _close(a.cafMean, 400, 1e-9)
    b = _new(host)
    A.caffeine(b, 140, 80, 0)
    assert _close(b.cafMean, 20.0)  # a dose-only step adds dose * 24 / 168 = dose / 7


def test_caffeine_tolerance_tau_7d_both_ways(host):
    A = host.K.acute
    a = _new(host)
    a.cafMean = 400
    for _ in range(7 * 1440):
        A.caffeine(a, 400 / 1440, 80, MIN)
    assert _close(a.cafTol, 0.6321205588285577, 1e-9)  # 1 - exp(-1), the exact step
    # the decay: cafMean 0 holds the target at 0; one week takes the tolerance down by exp(-1)
    b = _new(host)
    b.cafTol = 0.8
    b.caf = 100
    A.caffeine(b, 0, 80, 168)
    assert _close(b.cafTol, 0.8 * math.exp(-1), 1e-12)  # 0.29430...


def test_withdrawal_gated_and_shaped(host):
    A = host.K.acute
    a = _new(host)
    a.cafTol = 0.5
    for _ in range(6 * 60):
        A.caffeine(a, 0, 80, MIN)
    assert _close(a.cafLowH, 6, 1e-9)
    assert a.wd == 0 and a.wdH == -1  # before the 12 h onset
    for _ in range(30 * 60):
        A.caffeine(a, 0, 80, MIN)
    # cafTol 0.5 * exp(-36/168) = 0.40356 > 0.25: still gated in
    assert _close(a.cafTol, 0.5 * math.exp(-36 / 168), 1e-9)
    assert _close(a.wd, 1.0, 1e-9)  # (36 - 12) / 24 at the peak
    assert _close(a.wdH, 24, 1e-9)
    for _ in range(42 * 60):
        A.caffeine(a, 0, 80, MIN)
    assert _close(a.wd, 0.5, 1e-9)  # (120 - 78) / 84; cafTol 0.5 * exp(-78/168) = 0.3143 > 0.25
    assert _close(a.wdH, 66, 1e-9)
    # rising arm midpoint: 24 h -> (24 - 12) / 24 = 0.5
    b = _new(host)
    b.cafTol = 0.5
    A.caffeine(b, 0, 80, 24)
    assert _close(b.wd, 0.5) and _close(b.wdH, 12)
    # past 120 h: 0
    c = _new(host)
    c.cafTol = 1.0
    c.cafMean = 400
    A.caffeine(c, 0, 80, 121)
    assert c.wd == 0 and c.wdH == -1


def test_withdrawal_not_gated(host):
    A = host.K.acute
    a = _new(host)
    a.cafTol = 0.2  # below 0.25: no withdrawal however long abstinent
    A.caffeine(a, 0, 80, 40)
    assert a.cafLowH == 0 and a.wd == 0
    b = _new(host)
    b.cafTol = 0.5
    b.cafLowH = 30
    A.caffeine(b, 200, 80, MIN)  # a dose resets the abstinence clock
    assert b.cafLowH == 0 and b.wd == 0 and b.wdH == -1


# ---- alcohol ----

def test_widmark_instantaneous_and_elimination(host):
    A = host.K.acute
    a = _new(host)
    A.alcohol(a, 31.6, 80, 1, 0)
    assert _close(a.bac, 0.05808823529411765)  # 31.6 / (10 * 0.68 * 80)
    assert _close(a.alcPeak, a.bac)
    A.alcohol(a, 0, 80, 1, 1)
    assert _close(a.alc, 23.44, 1e-12)  # 31.6 - 0.015 * 0.68 * 80 * 10
    assert _close(a.bac, 0.04308823529411765, 1e-12)  # 23.44 / 544
    assert _close(a.alcPeak, 0.05808823529411765)  # the peak holds


def test_widmark_female(host):
    A = host.K.acute
    a = _new(host)
    A.alcohol(a, 31.6, 60, 2, 0)
    assert _close(a.bac, 0.09575757575757576)  # 31.6 / (10 * 0.55 * 60)


def test_hangover_starts_counts_down_and_ends(host):
    A = host.K.acute
    a = _new(host)
    A.alcohol(a, 31.6, 80, 1, 0)  # peak 0.0580882
    A.alcohol(a, 0, 80, 1, 10)  # 31.6 - 81.6 -> 0: bac 0, and the hangover starts on that step
    assert a.alc == 0 and a.bac == 0
    assert a.hang == 1
    assert _close(a.hangH, 6 * 0.05808823529411765 / 0.05)  # 6.97059 h
    A.alcohol(a, 0, 80, 1, 6)
    assert a.hang == 1 and _close(a.hangH, 6 * 0.05808823529411765 / 0.05 - 6)
    A.alcohol(a, 0, 80, 1, 1)
    assert a.hang == 0 and a.hangH == 0 and a.alcPeak == 0


def test_hangover_sub_threshold_peak_clears(host):
    A = host.K.acute
    a = _new(host)
    A.alcohol(a, 10, 80, 1, 0)  # 10 / 544 = 0.01838 < 0.05
    A.alcohol(a, 0, 80, 1, 5)
    assert a.bac == 0 and a.hang == 0 and a.alcPeak == 0


def test_drinking_during_hangover_starts_fresh(host):
    A = host.K.acute
    a = _new(host)
    a.hang = 1
    a.hangH = 5
    a.alcPeak = 0.08
    A.alcohol(a, 5.44, 80, 1, 0)  # 5.44 / 544 = 0.01
    assert a.hang == 0 and a.hangH == 0
    assert _close(a.alcPeak, 0.01)


def test_iu_alcohol(host):
    A = host.K.acute
    assert A.iuAlcohol(0) == 0
    assert _close(A.iuAlcohol(0.015), 0.15)  # 0.30 * 0.015 / 0.03
    assert _close(A.iuAlcohol(0.03), 0.30)
    assert _close(A.iuAlcohol(0.04), 0.65)  # 0.30 + 0.70 * 0.5
    assert _close(A.iuAlcohol(0.05), 1.00)
    assert _close(A.iuAlcohol(0.065), 1.30)  # 1.00 + 0.60 * 0.5
    assert _close(A.iuAlcohol(0.08), 1.60)
    assert _close(A.iuAlcohol(0.09), 1.80)  # the last segment extended: 1.60 + 20 * 0.01
    assert A.iuAlcohol(0.2) == 2.0  # capped


# ---- glycogen and glucose ----

def test_glycogen_work(host):
    A = host.K.acute
    a = _new(host)
    A.glycogen(a, 7.5, 1.0, 6, 1)
    assert _close(a.glyc, 410.5)  # 462 - 51.5
    assert _close(a.g, 410.5 / 462)


def test_glycogen_shivering(host):
    A = host.K.acute
    a = _new(host)
    A.glycogen(a, 1.0, 3.5, 6, 1.5)
    assert _close(a.glyc, 384.0)  # 462 - 52 * 1.5 = -78 (S0049: 410 -> 332)


def test_glycogen_resting_repletion(host):
    A = host.K.acute
    a = _new(host)
    a.glyc = 400
    for _ in range(1440):
        A.glycogen(a, 1.0, 1.0, 6, MIN)
    assert _close(a.glyc, 503.66777164788346, 1e-9)  # 400 + (564 - 400) * (1 - exp(-1))
    assert a.g == 1  # 503.7 / 462 clamps to 1


def test_glycogen_target(host):
    A = host.K.acute
    assert _close(A.glycTarget(6), 564)
    assert _close(A.glycTarget(3), 462)
    assert _close(A.glycTarget(0), 209)  # 462 - 253
    assert _close(A.glycTarget(4.5), 513)  # 462 + 102 * 0.5


def test_glycogen_clamps(host):
    A = host.K.acute
    a = _new(host)
    a.glyc = 20
    A.glycogen(a, 12, 1.0, 6, 1)  # 51.5 * 1.6 = 82.4 > 20
    assert a.glyc == 0 and a.g == 0
    b = _new(host)
    b.glyc = 700
    A.glycogen(b, 1.0, 1.0, 6, MIN)
    assert b.glyc == 600


def test_bg_stays_normal_fasting(host):
    A = host.K.acute
    a = _new(host)
    for _ in range(12 * 60):
        A.glucose(a, 1.0, 0, 0, 12, MIN)
    assert _close(a.bg, 5.0)


def test_bg_falls_under_exertion_and_recovers(host):
    A = host.K.acute
    a = _new(host)
    a.g = 0.1
    for _ in range(120):
        A.glucose(a, 7, 0, 0, 0, MIN)
    assert _close(a.bg, 2.838338208091532, 1e-9)  # 2.5 + 2.5 * exp(-2)
    assert a.bg < 3.0
    for _ in range(60):
        A.glucose(a, 7, 1.0, 0, 0, MIN)  # carbohydrate absorbed each minute: toward 5.0 on 15 min
    assert _close(a.bg, 5.0 - (5.0 - 2.838338208091532) * math.exp(-4), 1e-9)  # 4.96041


def test_bg_exertion_needs_low_glycogen(host):
    A = host.K.acute
    a = _new(host)
    a.g = 0.5
    A.glucose(a, 9, 0, 0, 0, 2)
    assert _close(a.bg, 5.0)


def test_bg_alcohol_fasting(host):
    A = host.K.acute
    a = _new(host)
    A.glucose(a, 1.0, 0, 0.05, 13, 1)
    assert _close(a.bg, 3.0 + 2.0 * math.exp(-1))  # 3.73576
    b = _new(host)
    A.glucose(b, 1.0, 0, 0.05, 11, 1)
    assert _close(b.bg, 5.0)


def test_bg_clamp(host):
    A = host.K.acute
    a = _new(host)
    a.bg = 9
    A.glucose(a, 1.0, 0, 0, 0, MIN)
    assert a.bg == 8.0
    a.bg = 1
    A.glucose(a, 1.0, 0, 0, 0, MIN)
    assert a.bg == 2.0


def test_iu_glucose(host):
    A = host.K.acute
    assert A.iuGlucose(5.0) == 0
    assert A.iuGlucose(3.5) == 0
    assert _close(A.iuGlucose(3.25), 0.45)  # 0.9 * 0.25 / 0.5
    assert _close(A.iuGlucose(3.0), 0.90)
    assert _close(A.iuGlucose(2.0), 0.90)


# ---- sleep ----

def _awake(host, a, hours, ageH0, needFactor=1.0, hour0=8.0):
    A = host.K.acute
    n = int(round(hours * 60))
    for i in range(1, n + 1):
        A.sleepMinute(a, False, (hour0 + i / 60) % 24, needFactor, ageH0 + i / 60, MIN, False)
    return ageH0 + n / 60


def _sleep(host, a, hours, ageH0, needFactor=1.0, hour0=22.0):
    A = host.K.acute
    n = int(round(hours * 60))
    for i in range(1, n + 1):
        A.sleepMinute(a, True, (hour0 + i / 60) % 24, needFactor, ageH0 + i / 60, MIN, False)
    return ageH0 + n / 60


def test_sleep_24h_awake(host):
    a = _new(host, 0.0)
    _awake(host, a, 23.5, 0.0)
    assert _close(a.awakeH, 23.5, 1e-9)
    s = host.K.acute.sleepMinute
    for i in range(1, 31):
        s(a, False, 8.0, 1.0, 23.5 + i / 60, MIN, False)
    assert _close(a.awakeH, 24, 1e-9)
    assert _close(a.S, 0.7779851254490823, 1e-9)  # 1 - 0.83 * exp(-24 / 18.2); the briefing's 0.7777 a slip
    assert a.frozen is False


def test_sleep_window_short_sleep_accrues_debt(host):
    A = host.K.acute
    a = _new(host, 0.0)
    t = _awake(host, a, 19, 0.0)
    t = _sleep(host, a, 5, t)
    assert _close(a.debtH, 2.5, 1e-9)  # window closed at 24 h: 7.5 - 5
    assert a.winSleptH == 0 and _close(a.winStartH, 24)
    A.sleepMinute(a, False, 3.0, 1.0, t + MIN, MIN, False)  # wake after 5 h asleep: awake resets
    assert _close(a.awakeH, MIN) and a.sleptH == 0


def test_sleep_window_long_sleep_repays(host):
    a = _new(host, 0.0)
    a.debtH = 2.5
    t = _awake(host, a, 14.5, 0.0)
    t = _sleep(host, a, 9.5, t)
    assert _close(a.debtH, 1.5, 1e-9)  # 2.5 - 0.5 * (9.5 - 7.5)


def test_sleep_need_factor(host):
    A = host.K.acute
    a = _new(host, 0.0)
    a.winSleptH = 5
    A.sleepMinute(a, False, 12.0, 1.3, 24.0, MIN, False)
    assert _close(a.debtH, 7.5 * 1.3 - 5)  # 4.75


def test_debt_clamps(host):
    A = host.K.acute
    a = _new(host, 0.0)
    a.debtH = 39
    A.sleepMinute(a, False, 12.0, 1.0, 24.0, MIN, False)
    assert a.debtH == 40
    b = _new(host, 0.0)
    b.debtH = 1
    b.winSleptH = 12
    A.sleepMinute(b, True, 6.0, 1.0, 24.0, MIN, False)
    assert b.debtH == 0  # 1 - 0.5 * (12 + 1/60 - 7.5) < 0


def test_nap_does_not_reset_awake(host):
    A = host.K.acute
    a = _new(host, 0.0)
    a.awakeH = 10
    for i in range(30):
        A.sleepMinute(a, True, 14.0, 1.0, 1.0, MIN, False)
    assert _close(a.awakeH, 10) and _close(a.sleptH, 0.5, 1e-9)
    A.sleepMinute(a, False, 14.5, 1.0, 1.0, MIN, False)
    assert _close(a.awakeH, 10 + MIN) and a.sleptH == 0


def test_sleep_s_floor_and_debt_shortened_chi(host):
    A = host.K.acute
    a = _new(host, 0.0)
    a.debtH = 40
    a.S = 0.3
    A.sleepMinute(a, True, 2.0, 1.0, 1.0, 10, False)
    assert _close(a.S, 0.25)  # 0.3 * exp(-10/4.2) = 0.028 < floor min(0.4, 0.25)
    b = _new(host, 0.0)
    b.debtH = 10
    b.S = 0.2
    A.sleepMinute(b, True, 2.0, 1.0, 1.0, 1, False)
    assert _close(b.S, 0.2 * math.exp(-1 / 4.2))  # 0.15761 > floor 0.10
    c = _new(host, 0.0)
    c.debtH = 30
    A.sleepMinute(c, False, 12.0, 1.0, 1.0, 1, False)
    assert _close(c.S, 1 - 0.83 * math.exp(-1 / (18.2 / 1.4)))  # chi_w / (1 + 0.02 * min(30, 20))


def test_circ(host):
    A = host.K.acute
    a = _new(host, 0.0)
    A.sleepMinute(a, False, 4.0, 1.0, 0.0, MIN, False)
    assert _close(a.circ, 0.12)
    A.sleepMinute(a, False, 16.0, 1.0, 0.0, MIN, False)
    assert _close(a.circ, -0.12)
    A.sleepMinute(a, False, 10.0, 1.0, 0.0, MIN, False)
    assert _close(a.circ, 0.12 * math.cos(2 * math.pi * 6 / 24), 1e-12)  # 0


def test_sleep_freeze_holds_every_field(host):
    A = host.K.acute
    a = _new(host, 0.0)
    a.awakeH = 30
    a.debtH = 12
    a.sleptH = 2
    a.winSleptH = 3
    a.S = 0.9
    for i in range(1, 3 * 1440 + 1):
        A.sleepMinute(a, i % 2 == 0, 12.0, 1.0, i / 60, MIN, True)
    assert a.frozen is True
    assert (a.awakeH, a.debtH, a.sleptH, a.winSleptH, a.S) == (0, 0, 0, 0, 0.17)
    assert _close(a.winStartH, 3 * 24)  # the window restarts at each frozen minute
    assert _close(a.circ, 0.12 * math.cos(2 * math.pi * 8 / 24), 1e-12)
    A.sleepMinute(a, False, 12.0, 1.0, 72 + MIN, MIN, False)  # re-enabled: a fresh window, no debt
    assert a.frozen is False and a.debtH == 0 and _close(a.awakeH, MIN)


# ---- the impairment unit ----

def test_iu_sleep(host):
    A = host.K.acute
    a = _new(host)
    a.awakeH = 24
    assert _close(A.iuSleep(a), 1.0)
    a.awakeH = 20
    assert _close(A.iuSleep(a), 0.5)
    a.awakeH = 10
    assert A.iuSleep(a) == 0
    a.debtH = 10.5
    assert _close(A.iuSleep(a), 1.0)
    a.awakeH = 30
    assert A.iuSleep(a) == 1.5  # capped


def test_iu_dehyd(host):
    A = host.K.acute
    assert A.iuDehyd(0.5) == 0
    assert _close(A.iuDehyd(1.5), 0.225)
    assert _close(A.iuDehyd(2), 0.45)
    assert _close(A.iuDehyd(3), 0.67)  # 0.45 + 0.22
    assert _close(A.iuDehyd(6), 0.89)  # 0.45 + 0.88 capped


def test_iu_terms_and_iron(host):
    A = host.K.acute
    a = _new(host)
    assert A.iu(a, 0, 1) == 0
    assert A.iu(a, 0, 2) == 0
    assert _close(A.iu(a, 0, 3), 0.38)
    assert _close(A.iu(a, 0, 4), 0.76)
    assert _close(a.iu, 0.76)
    a.bac = 0.065
    a.bg = 3.25
    assert _close(A.iu(a, 3, 1), 1.30 + 0.67 + 0.45)  # 2.42, under the cap


def test_iu_caffeine_credit(host):
    A = host.K.acute
    a = _new(host)
    a.awakeH = 24
    assert _close(A.iu(a, 0, 1), 0.5)  # credit min(1.0, 0.5 + 0) = 0.5: capped 0.5 at C 0
    a.caf = 200
    assert _close(A.iu(a, 0, 1), 0.0)  # credit min(1.0, 1.1) = 1.0
    a.caf = 100
    assert _close(A.iu(a, 0, 1), 0.2)  # credit 0.5 + 0.3 = 0.8
    r = _new(host)
    r.caf = 400
    r.bac = 0.03
    assert _close(A.iu(r, 0, 1), 0.30)  # rested: credit min(0, ...) = 0; caffeine offsets no alcohol


def test_iu_sum_capped(host):
    A = host.K.acute
    a = _new(host)
    a.awakeH = 40
    a.debtH = 20
    a.bac = 0.2
    a.bg = 2.0
    a.caf = 1000
    assert A.iu(a, 6, 4) == 2.5  # 1.5 + 2.0 + 0.89 + 0.9 + 0.76 - min(1.5, 1.1) = 4.95 -> 2.5


# ---- refeeding ----

def _days(host, a, kcal, n, w=70, day0=0):
    for d in range(n):
        host.K.acute.refeedDay(a, kcal, w, (day0 + d + 1) * 24.0, False, False, False)


def test_refeed_starved_days_risk_and_event(host):
    A = host.K.acute
    for roll, expect in ((0.1, True), (0.5, False)):
        a = _new(host)
        _days(host, a, 2, 11)
        assert a.starvedDays == 11 and a.lowDay is True
        assert a.refeedRisk == 2  # 11 > 10
        assert A.refeedEvent(a, 2, roll) is False  # no window yet
        A.refeedDay(a, 12, 70, 12 * 24.0, False, False, False)
        assert a.refeedDayN == 0 and a.starvedDays == 0 and a.refeedRisk == 2  # the risk holds in the window
        assert A.refeedEvent(a, 12, roll) is expect  # 12 > 10 and roll < 0.23
        assert a.refeedEvent is expect and a.refeedDayN == 1


def test_refeed_window_runs_seven_days_then_recomputes(host):
    A = host.K.acute
    a = _new(host)
    _days(host, a, 2, 11)
    A.refeedDay(a, 8, 70, 12 * 24.0, False, False, False)
    assert A.refeedEvent(a, 8, 0.0) is False  # within the restart limit
    for d in range(6):
        A.refeedDay(a, 30, 70, (13 + d) * 24.0, False, False, False)
        A.refeedEvent(a, 30, 0.9)
    assert a.refeedDayN == 7
    A.refeedDay(a, 30, 70, 19 * 24.0, False, False, False)
    assert a.refeedRisk == 2  # held through the close that ends the window
    assert A.refeedEvent(a, 30, 0.0) is False and a.refeedDayN == -1
    A.refeedDay(a, 30, 70, 20 * 24.0, False, False, False)
    assert a.refeedRisk == 0  # recomputed: BMI 22.86, no loss, no starvation


def test_refeed_low_bmi_restart_limit(host):
    A = host.K.acute
    a = _new(host)
    a.refeedRisk = 2
    a.lowDay = True
    A.refeedDay(a, 7, 42, 24.0, False, False, False)  # BMI 42 / 3.0625 = 13.71 <= 14
    assert a.refeedDayN == 0 and _close(a.bmi, 42 / 1.75 ** 2)
    assert A.refeedEvent(a, 7, 0.0) is True  # 7 > 5


def test_refeed_no_window_without_a_low_day(host):
    A = host.K.acute
    a = _new(host)
    a.refeedRisk = 2
    A.refeedDay(a, 30, 45, 24.0, False, False, False)  # BMI 14.7 < 16: high, but fed
    assert a.refeedDayN == -1 and a.refeedRisk == 2
    assert A.refeedEvent(a, 30, 0.0) is False


def test_refeed_high_criteria(host):
    A = host.K.acute
    a = _new(host)
    A.refeedDay(a, 30, 70, 24.0, True, False, False)
    assert a.refeedRisk == 2  # potassium depleted
    b = _new(host)
    A.refeedDay(b, 30, 70, 24.0, False, True, False)
    assert b.refeedRisk == 2  # magnesium depleted
    c = _new(host)
    A.refeedDay(c, 30, 80, 24.0, False, False, False)
    A.refeedDay(c, 30, 67, 48.0, False, False, False)
    assert _close((80 - 67) / 80, 0.1625) and c.refeedRisk == 2  # loss 16.25 % > 15 %
    d = _new(host)
    A.refeedDay(d, 30, 48, 24.0, False, False, False)
    assert d.refeedRisk == 2  # BMI 15.67 < 16


def test_refeed_moderate_criteria(host):
    A = host.K.acute
    a = _new(host)
    A.refeedDay(a, 30, 70, 24.0, False, False, True)
    assert a.refeedRisk == 1  # alcohol history alone
    b = _new(host)
    A.refeedDay(b, 30, 55, 24.0, False, False, True)
    assert b.refeedRisk == 2  # BMI 17.96 < 18.5 and alcohol history
    c = _new(host)
    A.refeedDay(c, 30, 80, 24.0, False, False, False)
    A.refeedDay(c, 30, 70, 48.0, False, False, False)
    assert c.refeedRisk == 1  # loss 12.5 % > 10 %
    d = _new(host)
    _days(host, d, 2, 6)
    assert d.starvedDays == 6 and d.refeedRisk == 1  # 6 > 5
    e = _new(host)
    A.refeedDay(e, 30, 70, 24.0, False, False, False)
    assert e.refeedRisk == 0 and e.lowDay is False


def test_mass90_tracker(host):
    A = host.K.acute
    a = _new(host, 0.0)
    A.refeedDay(a, 30, 80, 24.0, False, False, False)
    assert a.mass90max == 80 and a.mass90ageH == 24.0
    A.refeedDay(a, 30, 75, 48.0, False, False, False)
    assert a.mass90max == 80  # a lower mass keeps the maximum
    A.refeedDay(a, 30, 75, 24.0 + 2160 + 1, False, False, False)
    assert a.mass90max == 75 and a.mass90ageH == 24.0 + 2161  # the maximum expired after 90 days
