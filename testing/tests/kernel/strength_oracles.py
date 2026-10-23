"""The strength fit's oracle registry, tracked as a kernel-test oracle (Plan 13 Task 2).

Copied on 2026-10-14 from the fit record's oracles.py, now data/fits/strength-refit-T/oracles.py (tracked at
5987ac7a; sha256 685257b96e18a07035d8722bcfdf56019f1f374207668711268b78b78ccec22e), byte for byte except the model
import, which reads the tracked strength_model, and the two Mettler rows' weight and source (Plan 16 Task 5: report
only). score(P) re-scores any parameter table; with P['exact'] true it
scores ruling 13-2's exact forms, which test_strength_oracle.py pins.
"""
# Oracle registry: each cited human reading the model must reproduce, with its row, value and band.
# A trial's unreported conditions (TDEE, fat mass, weekly sets, protein) are stated per oracle as
# assumptions; they are part of the oracle, not of the model.
import math
from .strength_model import Body, creation, F_of, L_of, DEFAULT

KG_LEVEL = 0.5 * 1.70 * 1.70


def run(b, days, S, p, E, tdee=2600.0):
    for _ in range(days):
        b.day(S, p, E, tdee)
    return b


def body_at(P, L, fat, cap=16.5, F0L=5.0):
    return Body(P, L, cap, fat, F0L=F0L)


def L_at_s(s, F0L=5.0, cap=16.5):
    return F0L + s * (cap - F0L)


# ---------------------------------------------------------------- oracles
def o_year1(P):
    b = creation(P)
    run(b, 365, 20, 2.0, 0.05 * 2600)  # full gates
    return (L_of(b.F) - 5) * KG_LEVEL


def _yearly(P):
    b = creation(P)
    out = []
    prev = b.F
    for y in range(3):
        run(b, 365, 20, 2.0, 0.05 * 2600)
        out.append(b.F - prev)
        prev = b.F
    return out


def o_halving2(P):
    y = _yearly(P)
    return y[1] / y[0]


def o_halving3(P):
    y = _yearly(P)
    return y[2] / y[1]


def o_benito(P):
    # untrained, ~12 sets/wk, habitual ~1.3 g/kg, energy balance, 10.4 wk
    b = creation(P)
    F0 = b.F
    run(b, 73, 12, 1.3, 0.0)
    return b.F + b.X - F0


def _novice_gain(P, S, weeks=10):
    b = creation(P)
    F0 = b.F
    run(b, 7 * weeks, S, 1.6, 0.05 * 2600)
    return b.F - F0


def o_pelland_ratio(P):
    return _novice_gain(P, 30) / max(1e-9, _novice_gain(P, 12))


def o_h8_ratio(P):
    # 1 vs 3 sets per exercise, ~3 sessions: 3 vs 9 weekly sets, 12 wk (+3.7 vs +5.2 % CSA)
    return _novice_gain(P, 3, 12) / max(1e-9, _novice_gain(P, 9, 12))


def o_aube(P):
    # advanced lifters (squat ~2x BW): s = 0.75, 8 wk, 24 vs 12 sets, 2 g/kg, small surplus
    def g(S):
        b = body_at(P, L_at_s(0.75), 9.0)
        b.Pk = b.F
        F0 = b.F
        run(b, 56, S, 2.0, 0.05 * 2700, 2700)
        return b.F - F0
    return g(24) / max(1e-9, g(12))


def _longland(P, p):
    # overweight young men, untrained, ~25 kg fat, 6 d/wk training (~20 sets), 40 % deficit of 3000 kcal, 4 wk
    b = body_at(P, 5.0, 25.0)
    F0, X0, M0 = b.F, b.X, b.M
    run(b, 28, 20, p, -1200.0, 3000)
    return (b.F + b.X - F0 - X0), (b.M - M0)


def o_longland_hp_lean(P):
    return _longland(P, 2.4)[0]


def o_longland_lp_lean(P):
    return _longland(P, 1.2)[0]


def o_longland_hp_fat(P):
    return _longland(P, 2.4)[1]


def _garthe11(P, E, days):
    # elite athletes, ~72 kg, ~10 kg fat, 4 RT sessions/wk (~12 sets), s = 0.3, ~1.8 g/kg (assumed)
    b = body_at(P, L_at_s(0.2), 14.0)
    b.Pk = b.F
    F0 = b.F
    run(b, days, 12, 1.8, E, 3000)
    return b.F + b.X - F0


def o_garthe11_slow(P):
    return _garthe11(P, -0.19 * 3000, 60)


def o_garthe11_fast(P):
    return _garthe11(P, -0.30 * 3000, 37)


def o_mk_500(P):
    # Murphy & Koehler meta-regression: mostly sedentary novices, -500 kcal/d -> lean ~0; ~10 wk, 1.2 g/kg, 12 sets
    b = body_at(P, 5.0, 20.0)
    F0 = b.F
    run(b, 70, 12, 1.2, -500.0)
    return b.F + b.X - F0


def _trained_maint(P, E):
    # trained (s = 0.5), 15 sets, 2.0 g/kg, 8 wk (Helms 2023, Antonio 2015)
    b = body_at(P, L_at_s(0.5), 11.0)
    b.Pk = b.F
    F0 = b.F
    run(b, 56, 15, 2.0, E, 2800)
    return b.F - F0


def o_trained_maint(P):
    return _trained_maint(P, 0.0)


def o_helms23_ratio(P):
    # refit 2 re-grade (S2062): HIGH ("+15 %") reported +719 kcal/d over its maintenance phase, not +15 %
    return _trained_maint(P, 719.0) / max(1e-9, _trained_maint(P, 0.0))


def _garthe13(P, E):
    b = body_at(P, L_at_s(0.3), 10.0)
    b.Pk = b.F
    F0, M0 = b.F, b.M
    run(b, 70, 14, 1.8, E, 3000)
    return b.F + b.X - F0, b.M - M0


def o_garthe13_lean_ratio(P):
    return _garthe13(P, 600.0)[0] / max(1e-9, _garthe13(P, 150.0)[0])


def o_garthe13_fat_diff(P):
    return _garthe13(P, 600.0)[1] - _garthe13(P, 150.0)[1]


def _deficit_share(P, L, fat, S, p, E, days, tdee):
    b = body_at(P, L, fat)
    b.Pk = b.F
    F0, X0, M0 = b.F, b.X, b.M
    run(b, days, S, p, E, tdee)
    dl = (b.F + b.X) - (F0 + X0)
    dm = b.M - M0
    return -dl / max(1e-9, -(dl + dm))


def o_mettler_lp(P):
    return _deficit_share(P, L_at_s(0.4), 12.0, 12, 1.0, -1200.0, 14, 3000)


def o_mettler_hp(P):
    return _deficit_share(P, L_at_s(0.4), 12.0, 12, 2.3, -1200.0, 14, 3000)


def o_quarter_rule(P):
    # diet only, obese (35 kg fat), 0.9 g/kg, -600 kcal, 12 wk (Heymsfield 2014, Weinheimer 2010)
    return _deficit_share(P, 5.0, 35.0, 0, 0.9, -600.0, 84, 2600)


def o_pasiakos_diff(P):
    a = _deficit_share(P, 5.0, 15.0, 0, 0.8, -1100.0, 21, 2800)
    c = _deficit_share(P, 5.0, 15.0, 0, 1.6, -1100.0, 21, 2800)
    return a - c


def _bray(P, p):
    b = body_at(P, 5.0, 20.0)
    F0, X0 = b.F, b.X
    run(b, 56, 0, p, 954.0, 2400)
    return (b.F + b.X) - (F0 + X0), b.F - F0


def o_bray_15(P):
    return _bray(P, 1.8)[0]


def o_bray_5(P):
    return _bray(P, 0.6)[0]


def o_bray_muscle(P):
    return _bray(P, 1.8)[1]


def _rantila(P):
    # novices, 10 wk training (~9 sets), 10 wk off, 10 wk retraining; ~1.6 g/kg, balance
    b = creation(P)
    F0 = b.F
    run(b, 70, 9, 1.6, 0.0)
    g1 = b.F - F0
    Ft = b.F
    run(b, 70, 0, 1.6, 0.0)
    kept = (b.F - F0) / max(1e-9, g1)
    Fd = b.F
    run(b, 70, 9, 1.6, 0.0)
    g2 = b.F - Fd
    # Räntilä's second block gained the loss plus the novice increment: total gain of block 2 vs block 1
    return kept, g2 / max(1e-9, g1)   # block 2's gain from the detrained floor against block 1's (VL 4.1 vs 4.1 cm2)


def o_rantila_kept(P):
    return _rantila(P)[0]


def o_rantila_retrain(P):
    return _rantila(P)[1]


def _bickel(P, S_after):
    b = creation(P)
    F0 = b.F
    run(b, 112, 27, 1.6, 0.0)
    g = b.F - F0
    run(b, 224, S_after, 1.6, 0.0)
    return (b.F - F0) / max(1e-9, g)


def o_bickel_third(P):
    return _bickel(P, 9)


def o_bickel_ninth(P):
    return _bickel(P, 3)


def o_detrain_hl(P):
    # a novice after 10 wk of training (Räntilä's population) stops: the half-life of F - F0 after the grace, in weeks
    b = creation(P)
    run(b, 70, 9, 1.6, 0.0)
    run(b, int(round(P['grace_d'])) + 1, 0, 1.6, 0.0)
    a = b.F - b.F0
    n = 0
    while b.F - b.F0 > a / 2 and n < 2000:
        b.day(0, 1.6, 0.0)
        n += 1
    return n / 7.0


def _deg(P, which):
    def lean(S, p, E):
        b = creation(P)
        F0 = b.F
        run(b, 70, S, p, E)
        return b.F - F0
    base = lean(12, 1.2, 0.0)
    if which == 'p':
        return lean(12, 1.2 * 1.02, 0.0) - base
    if which == 'E':
        return lean(12, 1.2, 0.02 * 2600) - base
    return lean(12 * 1.05, 1.2, 0.0) - base


def o_deg_p(P):
    return _deg(P, 'p')


def o_deg_E(P):
    return _deg(P, 'E')


def o_deg_S(P):
    return _deg(P, 'S')


# ---------------------------------------------------------------- advanced-status oracles (advanced-recomp-report)
def _adv(P, s, fat, S, p, E, days, tdee=2900.0):
    b = body_at(P, L_at_s(s), fat)
    b.Pk = b.F
    F0, X0, M0 = b.F, b.X, b.M
    run(b, days, S, p, E, tdee)
    return b.F - F0, b.X - X0, b.M - M0, F0


# Moro 2016 (S3.1, as corrected by the citation review): >= 5 y trained, FFMI ~23.3 (computed; level 15.6, s = 0.92),
# fat mass 10.90 / 11.36 kg at baseline, 100 % of needs, ~1.9 g/kg, standardised programme (~15 sets/wk assumed),
# 8 wk: DXA FFM 73.08 -> 73.72 (TRE) and 73.93 -> 74.41 kg (normal), both n.s.
def o_moro_maint(P):
    dF, dX, dM, _ = _adv(P, 0.92, 11.36, 15, 1.9, 0.0, 56)
    return dF + dX


def o_moro_tre(P):
    # the time-restricted arm: printed fat 10.90 -> 9.28 kg; ~ -250 kcal/d is an inference from that loss; FFM held
    dF, dX, dM, _ = _adv(P, 0.92, 10.90, 15, 1.9, -250.0, 56)
    return dF + dX


# Isola 2025 (S3.2, PMC11829922): non-dieting physique controls, ~46 wk, "no systematic changes" (DXA, ultrasound);
# energy not set (balance assumed), s = 0.9, ~12 % fat
def o_isola(P):
    dF, dX, dM, _ = _adv(P, 0.9, 9.0, 15, 2.0, 0.0, 322)
    return dF + dX


def _helms_arm_full(P, E):
    # refit 2: E in kcal/d, the arm's reported intake rise over its own maintenance phase (S2062, Table 2)
    b = body_at(P, L_at_s(0.5), 11.0)
    b.Pk = b.F
    F0, X0, M0 = b.F, b.X, b.M
    run(b, 56, 15, 2.0, E, 2800)
    return b.F - F0, (b.F + b.X + b.M) - (F0 + X0 + M0)


def _helms_arm(P, E):
    return _helms_arm_full(P, E)[0]


# Helms 2023 re-graded (S2062, S2063; refit 2): the "+5 %" arm (MOD) reported +489 kcal/d and the "+15 %" arm
# (HIGH) +719 kcal/d over their maintenance phases; both gained 3.3 kg; no muscle-thickness difference against
# maintenance (group-model BF10 0.32-0.77). MAIN is taken at balance (its +169 kcal/d is graded report-only).
def o_helms23_5(P):
    return _helms_arm(P, 489.0) / max(1e-9, _helms_arm(P, 0.0))


def o_helms23_15_minus_maint(P):
    # report check 3: at s = 0.5 balance and HIGH within one noise band over 8 wk (0.5 kg FFM)
    return _helms_arm(P, 719.0) - _helms_arm(P, 0.0)


def o_helms23_mod_minus_main169(P):
    # report only: MAIN at its own reported +169 kcal/d rather than balance
    return _helms_arm(P, 489.0) - _helms_arm(P, 169.0)


def o_helms23_mod_mass(P):
    # report only: MOD body mass +3.3 +/- 0.8 kg (S2033), from self-reported intake
    return _helms_arm_full(P, 489.0)[1]


def o_helms23_high_mass(P):
    # report only: HIGH body mass +3.3 +/- 1.5 kg (S2033)
    return _helms_arm_full(P, 719.0)[1]


# Henselmans 2026 (S2064, S2065; refit 2): 20 men trained 9.7 +/- 6.1 y (squat 1.9 x BM; FFMI not reported, so
# s = 0.7 is a judgment inside 0.6-0.8), 8-wk crossover, 14-18 weekly sets (16 here), protein 178 g/d (~2.0 g/kg),
# habitual intake taken as balance, the contrast +250 (Atwater) to +485 kcal/d (self-report), TDEE ~2700, fat 14 kg
# (BMI 26.7). DXA lean CHO - PRO +0.76 kg (95 % CI -0.19 to 1.69); elbow-flexor thickness +0.05 cm (-0.09 to 0.19).
def _henselmans(P, E):
    def arm(e):
        b = body_at(P, L_at_s(0.7), 14.0)
        b.Pk = b.F
        F0, X0 = b.F, b.X
        run(b, 56, 16, 2.0, e, 2700.0)
        return (b.F + b.X) - (F0 + X0), b.F - F0, F0
    lean1, f1, F0 = arm(E)
    lean0, f0, _ = arm(0.0)
    return lean1 - lean0, 100.0 * (f1 - f0) / F0


def o_hens_lean_250(P):
    return _henselmans(P, 250.0)[0]


def o_hens_lean_485(P):
    return _henselmans(P, 485.0)[0]


def o_hens_muscle_250(P):
    return _henselmans(P, 250.0)[1]


def o_hens_muscle_485(P):
    # the muscle contrast as % of F; the band is the elbow-flexor CI over an assumed 4.0 cm trained baseline
    # (-0.09/4.0 to +0.19/4.0 = -2.25 to +4.75 %), relative thickness read as relative muscle (a stated assumption)
    return _henselmans(P, 485.0)[1]


# Angus (2026-10-14) as a direction oracle: "a slight surplus over a long time with good training and protein has
# to build more muscle than zero caloric surplus". One year, 20 sets, 2.0 g/kg, +5 % of TDEE against balance.
def _year_contrast(P, s, frac):
    def yr(e):
        b = body_at(P, L_at_s(s), 11.0)
        b.Pk = b.F
        F0 = b.F
        run(b, 364, 20, 2.0, e, 2800.0)
        return b.F - F0
    return yr(frac * 2800.0) - yr(0.0)


def o_angus_slight_surplus_s09(P):
    return _year_contrast(P, 0.9, 0.05)


def o_angus_slight_surplus_s06(P):
    return _year_contrast(P, 0.6, 0.05)


def o_deg_full_status(P):
    # degenerate-read check on full_drop: the share of the +10 % gain reached at +5 % rises with status
    # (E_full shrinks); at full_drop = 0 both shares are about 0.5 and the difference about 0, which fails
    def share(s):
        b0 = _adv(P, s, 9.0, 15, 2.0, 0.0, 56)[0]
        b5 = _adv(P, s, 9.0, 15, 2.0, 0.05 * 2900, 56)[0]
        b10 = _adv(P, s, 9.0, 15, 2.0, 0.10 * 2900, 56)[0]
        return (b5 - b0) / max(1e-12, b10 - b0)
    return share(0.9) - share(0.5)


# report section 9 checks at s = 0.9, F near F_c
def o_chk1_bal_pct(P):
    dF, dX, dM, F0 = _adv(P, 0.9, 9.0, 15, 2.0, 0.0, 56)
    return 100.0 * dF / F0


def o_chk1_bal_fat(P):
    return _adv(P, 0.9, 9.0, 15, 2.0, 0.0, 56)[2]


def o_chk2_ratio(P):
    a = _adv(P, 0.9, 9.0, 15, 2.0, 0.10 * 2900, 56)[0]
    b = _adv(P, 0.9, 9.0, 15, 2.0, 0.0, 56)[0]
    return a / max(1e-9, b)


def o_chk2_pct(P):
    dF, dX, dM, F0 = _adv(P, 0.9, 9.0, 15, 2.0, 0.10 * 2900, 56)
    return 100.0 * dF / F0


def o_chk2_fat_share(P):
    dF, dX, dM, F0 = _adv(P, 0.9, 9.0, 15, 2.0, 0.10 * 2900, 56)
    return dM / max(1e-9, dF + dX + dM)


def o_chk4_contest(P):
    # s = 0.9 at contest leanness (~5 % fat, 3.5 kg), -500 kcal/d, 2.5 g/kg, training kept, 8 wk: dF <= 0
    return _adv(P, 0.9, 3.5, 15, 2.5, -500.0, 56)[0]


def o_deg_E_adv(P):
    # degenerate check at s = 0.9: +2 % surplus moves lean
    a = _adv(P, 0.9, 9.0, 15, 2.0, 0.02 * 2900, 56)[0]
    b = _adv(P, 0.9, 9.0, 15, 2.0, 0.0, 56)[0]
    return a - b


def o_deg_fbal(P):
    # degenerate check: the trained gate at balance responds to status (s = 0.5 vs 0.9 per unit headroom)
    def per(s):
        dF, dX, dM, F0 = _adv(P, s, 9.0, 15, 2.0, 0.0, 56)
        Fc = body_at(P, L_at_s(s), 9.0).Fc
        return dF / (Fc - F0)
    return per(0.5) - per(0.9)


# report-only contest-prep readings (mixed sex or uncertain conditions)
def o_buechel(P):
    # Buechel 2026 (S3.4): ~21 wk, FM -5.8 kg (here ~ -370 kcal/d), FFM -1.7 [-2.6, -0.9]; 8 M + 11 F
    dF, dX, dM, _ = _adv(P, 0.9, 9.0, 15, 2.5, -370.0, 147)
    return dF + dX


def o_roth23(P):
    # Roth 2023 (S3.11): trained men, 30 kcal/kg (~ -800 kcal/d), ~2.4 g/kg, 6 wk: DXA lean -0.51 / -0.92
    dF, dX, dM, _ = _adv(P, 0.5, 12.0, 15, 2.4, -800.0, 42, 3200.0)
    return dF + dX


ADV = [
    ("moro16_maint_8wk", o_moro_maint, -0.30, 0.80, "S3.1 Moro 2016: FFM +0.64/+0.48 kg n.s. (+0.86/+0.64 %)", 1),
    ("moro16_tre_minus250", o_moro_tre, -0.50, 0.80, "S3.1 Moro 2016 TRE: fat 10.90->9.28; -250 kcal/d inferred; FFM held", 1),
    ("isola25_controls_46wk", o_isola, -1.00, 1.00, "S3.2 Isola 2025: controls no systematic change", 1),
    ("helms23_mod489_over_maint", o_helms23_5, 0.80, 1.60, "S2062/S2063 Helms 2023 MOD (+489 kcal/d reported) = maintenance", 1),
    ("helms23_high719_minus_maint", o_helms23_15_minus_maint, -0.30, 0.50, "S2062 Helms 2023 HIGH (+719): within one noise band, 8 wk", 1),
    ("helms23_mod_minus_main169", o_helms23_mod_minus_main169, -0.30, 0.50, "S2062 MAIN at its reported +169 (report)", 0),
    ("helms23_mod_mass_kg", o_helms23_mod_mass, 2.50, 4.10, "S2033 MOD body mass +3.3 +/- 0.8 kg (report)", 0),
    ("helms23_high_mass_kg", o_helms23_high_mass, 1.80, 4.80, "S2033 HIGH body mass +3.3 +/- 1.5 kg (report)", 0),
    ("hens26_lean_250", o_hens_lean_250, -0.19, 1.69, "S2064/S2065 Henselmans 2026 DXA lean CI, +250 (Atwater)", 1),
    ("hens26_lean_485", o_hens_lean_485, -0.19, 1.69, "S2064/S2065 Henselmans 2026 DXA lean CI, +485 (self-report)", 1),
    ("hens26_muscle_pct_250", o_hens_muscle_250, -2.25, 4.75, "S2064 elbow-flexor CI as % of 4.0 cm, +250", 1),
    ("hens26_muscle_pct_485", o_hens_muscle_485, -2.25, 4.75, "S2064 elbow-flexor CI as % of 4.0 cm, +485", 1),
    ("angus_surplus5_1yr_s09", o_angus_slight_surplus_s09, 1e-6, 99, "Angus ruling: +5 % for a year beats balance at s = 0.9", 1),
    ("angus_surplus5_1yr_s06", o_angus_slight_surplus_s06, 1e-6, 99, "Angus ruling: +5 % for a year beats balance at s = 0.6", 1),
    ("deg_full_status", o_deg_full_status, 0.05, 99, "degenerate check: E_full shrinks with s (share of +10 % reached at +5 %)", 1),
    ("chk1_s09_bal_dF_pct", o_chk1_bal_pct, 0.00, 0.50, "report sec. 9 check 1: dF < 0.5 % at balance, 8 wk", 1),
    ("chk1_s09_bal_fat_kg", o_chk1_bal_fat, -0.50, 0.50, "report sec. 9 check 1: fat steady", 1),
    ("chk2_s09_surplus_over_bal", o_chk2_ratio, 1.00, 2.00, "report sec. 9 check 2: <= 2x balance", 1),
    ("chk2_s09_surplus_dF_pct", o_chk2_pct, 0.00, 1.00, "report sec. 9 check 2: < 1 %", 1),
    ("chk2_s09_surplus_fat_share", o_chk2_fat_share, 0.50, 1.00, "report sec. 9 check 2: fat carries most of the weight", 1),
    ("chk4_s09_contest_minus500", o_chk4_contest, -5.00, 0.00, "report sec. 9 check 4: dF <= 0 at contest fat", 1),
    ("deg_surplus_2pct_s09", o_deg_E_adv, 1e-6, 99, "degenerate check: +2 % surplus moves lean at s = 0.9", 1),
    ("deg_fbal_status", o_deg_fbal, 1e-9, 99, "degenerate check: balance growth per headroom falls with s", 0),
    ("buechel26_contest_ffm", o_buechel, -2.60, -0.90, "S3.4 Buechel 2026 contest prep (mixed sex; report)", 0),
    ("roth23_minus30pct_lean", o_roth23, -1.20, -0.30, "S3.11 Roth 2023 trained men -30 % (report)", 0),
]


# (name, fn, lo, hi, source, weight). A band (lo, hi); weight 0 = report only.
REGISTRY = [
    ("year1_kg_20sets", o_year1, 6.8, 8.5, "S1.15 McDonald x0.75 (first-harvest calibration)", 1),
    ("yr2_over_yr1", o_halving2, 0.40, 0.60, "S1.15 halving; H.49/H.50 year-1 dominance", 1),
    ("yr3_over_yr2", o_halving3, 0.40, 0.65, "S1.15 halving", 1),
    ("benito_10wk_kg", o_benito, 1.12, 1.96, "S1.9 Benito 2020 untrained FFM +1.54 (CI 1.12-1.96)", 1),
    ("pelland_30_over_12", o_pelland_ratio, 1.55, 2.00, "H.1 Pelland sqrt fit, derived 1.77", 1),
    ("h8_3_over_9", o_h8_ratio, 0.50, 0.90, "H.8 1 vs 3 sets: +3.7 vs +5.2 % (0.71)", 1),
    ("aube_24_over_12", o_aube, 0.70, 1.40, "H.5 Aube 2022 advanced: 12=18=24 sets", 1),
    ("longland_hp_lean", o_longland_hp_lean, 0.60, 1.80, "S0064 Longland 2.4 g/kg -40 %: +1.2 +/- 1.0 kg", 1),
    ("longland_lp_lean", o_longland_lp_lean, -0.40, 0.60, "S0064 Longland 1.2 g/kg: +0.1 +/- 1.0 kg", 1),
    ("longland_hp_fat", o_longland_hp_fat, -5.00, -3.00, "S0064 fat -4.8 +/- 1.6 kg (energy side; report)", 0),
    ("garthe11_slow_lean", o_garthe11_slow, 0.80, 1.80, "Garthe 2011 (PMID 21558571) -19 %: LBM +2.1 %", 1),
    ("garthe11_fast_lean", o_garthe11_fast, -0.60, 0.40, "Garthe 2011 -30 %: LBM -0.2 %", 1),
    ("mk_minus500_lean", o_mk_500, -0.30, 0.30, "S1.28 Murphy & Koehler: -500 kcal/d -> no lean gain", 1),
    ("trained_maint_8wk", o_trained_maint, 0.10, 1.50, "Helms 2023 MAIN; Antonio 2015 (PMID 26500462) FFM +1.5", 1),
    ("trained_maint_premise", o_trained_maint, -0.10, 0.10, "Angus premise: trained ~0 at maintenance", 0),
    ("helms23_high719_over_maint", o_helms23_ratio, 0.80, 1.60, "S2062/S2063 Helms 2023 HIGH (+719 kcal/d reported): no MT difference", 1),
    ("garthe13_lean_ratio", o_garthe13_lean_ratio, 0.80, 1.35, "S1.30 Garthe 2013: LBM gain not different", 1),
    ("garthe13_fat_diff", o_garthe13_fat_diff, 0.80, 2.50, "S1.30 Garthe 2013: FM +15 % vs +3 %", 1),
    # Plan 16 Task 5 (controller ruling): report only, two named non-reproductions. The deficit arm now follows
    # Forbes (S1056, S2278-S2288); the old Alpert ceiling sent the overflow above 69 kcal/kg fat/d to lean, which is
    # what met these bands at 12 kg fat and -1200 kcal/d. Mettler's 14-day DXA lean includes the early glycogen and
    # its water, a reserve the model's lean (F + X, X already the labile water, glycogen and organ) does not carry
    # apart, so no DXA-equivalent reading exists; the protection weights are not re-fitted. The same change moved the
    # two longer report-only deficit studies further out the same way (buechel26_contest_ffm -0.564 -> -0.380,
    # roth23_minus30pct_lean -0.270 -> -0.075, both less lean lost), where an early glycogen-water artefact is small:
    # the protection weights wT and wP, fitted under the ceiling, may now under-predict lean loss in fed training
    # deficits (review F3), for a later re-fit to weigh.
    ("mettler_lp_share", o_mettler_lp, 0.35, 0.70, "Mettler 2010 (PMID 19927027) 1.0 g/kg: 1.6 of 3.0 kg lean (report)", 0),
    ("mettler_hp_share", o_mettler_hp, 0.05, 0.35, "Mettler 2010 2.3 g/kg: 0.3 of 1.5 kg lean (report)", 0),
    ("quarter_rule_share", o_quarter_rule, 0.15, 0.35, "Heymsfield 2014 (PMID 24447775); S0072 Weinheimer", 1),
    ("pasiakos_0.8_minus_1.6", o_pasiakos_diff, 0.10, 0.50, "Pasiakos 2013 (PMID 23739654) direction (abstract)", 1),
    ("bray_15pct_lean", o_bray_15, 1.50, 3.50, "S0605 Bray 2012: lean +2.87 kg at 15 % protein", 1),
    ("bray_5pct_lean", o_bray_5, -0.70, 0.50, "S0605 Bray 2012: no lean gain at 5 %", 1),
    ("bray_muscle_no_signal", o_bray_muscle, -0.05, 0.05, "H.41/H.42/S0606: no muscle without the signal", 1),
    ("rantila_kept_frac", o_rantila_kept, 0.24, 0.47, "H.51 Räntilä 2025: 24-47 % kept after 10 wk off", 1),
    ("rantila_block2_over_1", o_rantila_retrain, 0.80, 1.25, "H.51 Räntilä: block 2 = block 1", 1),
    ("bickel_third_kept", o_bickel_third, 0.85, 1.80, "H.13 Bickel 2011: 1/3 dose kept size 32 wk", 1),
    ("bickel_ninth_kept", o_bickel_ninth, 0.85, 1.40, "H.13 Bickel 2011: 1/9 dose kept size 32 wk", 1),
    ("detrain_halflife_wk", o_detrain_hl, 4.9, 9.2, "H.51 Räntilä derived 4.9-9.2 wk", 1),
    ("deg_protein_2pct", o_deg_p, 1e-5, 99, "degenerate check: +2 % protein moves lean", 1),
    ("deg_surplus_2pct", o_deg_E, 1e-5, 99, "degenerate check: +2 % surplus moves lean", 1),
    ("deg_sets_5pct", o_deg_S, 1e-5, 99, "degenerate check: +5 % sets moves lean", 1),
] + ADV


def miss(v, lo, hi):
    if v != v:
        return 10.0
    if hi >= 99:   # a degenerate check: pass/fail
        return 0.0 if v > lo else 1.0
    if lo <= v <= hi:
        return 0.0
    w = max(hi - lo, 1e-3)
    return (lo - v) / w if v < lo else (v - hi) / w


def score(P, verbose=False):
    if P.get('infeasible'):
        return (1e6, []) if verbose else 1e6
    tot = 0.0
    rows = []
    for name, fn, lo, hi, src, wgt in REGISTRY:
        v = fn(P)
        m = miss(v, lo, hi)
        tot += wgt * m * m
        rows.append((name, v, lo, hi, m, wgt, src))
    if verbose:
        return tot, rows
    return tot
