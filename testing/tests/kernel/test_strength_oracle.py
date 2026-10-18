"""The strength fit's tracked oracle (Plan 13 Task 2): point T reproduces compact_T.json, and the exact mode of
ruling 13-2 keeps every weighted pass and is pinned oracle by oracle."""
import json, math, os
import pytest
from . import strength_model as sm
from . import strength_oracles as so

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
COMPACT = os.path.join(REPO, "docs", "superpowers", "research", "2026-10-14-strength-redesign", "refit", "compact_T.json")

def _compact():
    with open(COMPACT, encoding="utf-8") as fh:
        return json.load(fh)

def test_point_t_is_the_record():
    chosen = _compact()["chosen"]
    for k, v in chosen.items():
        if k == "infeasible":
            continue
        assert sm.POINT_T[k] == v, k

def test_the_record_score_and_every_oracle_reproduce():
    c = _compact()
    total, rows = so.score(dict(sm.POINT_T), True)
    assert abs(total - c["score"]) < 1e-12
    by = {r[0]: r for r in rows}
    for o in c["oracles"]:
        assert abs(by[o["name"]][1] - o["value"]) < 1e-12, o["name"]

def test_exact_mode_keeps_every_weighted_pass():
    c = _compact()
    P = dict(sm.POINT_T, exact=True, ts=1.0)
    _, rows = so.score(P, True)
    was = {o["name"]: o for o in c["oracles"]}
    for name, value, lo, hi, miss, weight, src in rows:
        if weight and was[name]["miss"] == 0.0:
            assert lo <= value <= hi, name

def test_exact_detraining_halves_in_its_half_life():
    P = dict(sm.POINT_T, exact=True, ts=1.0, grace_d=0, detrain_status=0.0)
    b = sm.Body(P, 10.0, 16.5, 13.0, F0L=5.0)
    F0 = b.F0
    gap0 = b.F - F0
    hl_days = 7 * P["detrain_hl_wk"]
    # S = 0, energy balance, no protein: growth and regain are 0, the detraining runs alone
    b.Pk = b.F
    assert hl_days == int(hl_days)
    for _ in range(int(hl_days)):
        b.day(0.0, 0.0, 0.0)
    # exact integration: 42 one-day factors exp(-lam/7) compose to 1/2 (the Euler form gives 0.4976)
    assert abs((b.F - F0) / gap0 - 0.5) < 1e-9


# The exact-mode re-score (ruling 13-2, ts = 1) of every registry oracle at point T, pinned so a later kernel or
# oracle change that moves one is named. Against the record only rantila_kept_frac and rantila_block2_over_1 moved.
# Task 11c (regain integrated exactly, Task 11 review I-2) moved buechel26_contest_ffm only, by 7.5e-7: a weight-0
# report oracle outside its band under the record and still outside it; the total did not move. Plan 16 Task 5 (the
# deficit arm without Alpert's ceiling) moved seven: garthe11_fast_lean, pasiakos and chk4 inside their bands, the
# report-only buechel26 and roth23 still outside theirs, and both Mettler shares out of their bands, which the
# controller's ruling made report only (strength_oracles.py); the weighted total did not move.
EXACT_TOTAL = 0.5281803643283429
EXACT_PINS = {
    'year1_kg_20sets': 7.556450473517981,
    'yr2_over_yr1': 0.449515999957318,
    'yr3_over_yr2': 0.5006506265905187,
    'benito_10wk_kg': 1.450737011169302,
    'pelland_30_over_12': 1.6204123296614585,
    'h8_3_over_9': 0.461450492485093,
    'aube_24_over_12': 1.4441203885109244,
    'longland_hp_lean': 0.5228650003064317,
    'longland_lp_lean': -0.4212890038820234,
    'longland_hp_fat': -3.6595194196119643,
    'garthe11_slow_lean': 0.2753374222817513,
    'garthe11_fast_lean': -0.04433432933299741,  # Plan 16 Task 5 (no deficit ceiling): was -0.15637476335611922
    'mk_minus500_lean': -0.20754013114804337,
    'trained_maint_8wk': 0.4070969717299633,
    'trained_maint_premise': 0.4070969717299633,
    'helms23_high719_over_maint': 1.3278647632358014,
    'garthe13_lean_ratio': 1.0661433036295154,
    'garthe13_fat_diff': 3.3242176760555857,
    'mettler_lp_share': 0.24066195679209607,  # Plan 16 Task 5: was 0.56921909092098; report only, out of its band
    'mettler_hp_share': 0.0347015680866988,  # Plan 16 Task 5: was 0.18229532621015493; report only, out of its band
    'quarter_rule_share': 0.22456898837071676,
    'pasiakos_0.8_minus_1.6': 0.2555406025158306,  # Plan 16 Task 5: was 0.16236486696560648
    'bray_15pct_lean': 2.406793930650174,
    'bray_5pct_lean': 0.0,
    'bray_muscle_no_signal': 0.0,
    'rantila_kept_frac': 0.4329891097125966,
    'rantila_block2_over_1': 0.9381123244959031,
    'bickel_third_kept': 1.6474688711361072,
    'bickel_ninth_kept': 1.2635505579688542,
    'detrain_halflife_wk': 6.714285714285714,
    'deg_protein_2pct': 0.028544837088148256,
    'deg_surplus_2pct': 0.004867698919170493,
    'deg_sets_5pct': 0.03731060019653398,
    'moro16_maint_8wk': 0.017457598071018765,
    'moro16_tre_minus250': -0.07263419796433368,
    'isola25_controls_46wk': 0.13830074298451223,
    'helms23_mod489_over_maint': 1.3278647632358014,
    'helms23_high719_minus_maint': 0.13347275225025612,
    'helms23_mod_minus_main169': 0.024831249353262308,
    'helms23_mod_mass_kg': 3.337129980441617,
    'helms23_high_mass_kg': 4.701392240795386,
    'hens26_lean_250': 0.09360316611577701,
    'hens26_lean_485': 0.09360316611577701,
    'hens26_muscle_pct_250': 0.14705397863512606,
    'hens26_muscle_pct_485': 0.14705397863512606,
    'angus_surplus5_1yr_s09': 0.10203542219502992,
    'angus_surplus5_1yr_s06': 0.4465679245379661,
    'deg_full_status': 0.2365113444397896,
    'chk1_s09_bal_dF_pct': 0.0382115616234641,
    'chk1_s09_bal_fat_kg': -0.004922777634895681,
    'chk2_s09_surplus_over_bal': 1.800885682691589,
    'chk2_s09_surplus_dF_pct': 0.06881465424098386,
    'chk2_s09_surplus_fat_share': 0.9737739607933508,
    'chk4_s09_contest_minus500': -0.2666653123043403,  # Plan 16 Task 5: was -1.3205987075961332
    'deg_surplus_2pct_s09': 0.007505486325641186,
    'deg_fbal_status': 0.03359525461830324,
    'buechel26_contest_ffm': -0.3796933184718938,  # Plan 16 Task 5: was -0.563547266810744 (Task 11c: -0.5635465188507567)
    'roth23_minus30pct_lean': -0.0753223916043595,  # Plan 16 Task 5: was -0.26987869282115895
}


def test_exact_mode_pins():
    total, rows = so.score(dict(sm.POINT_T, exact=True, ts=1.0), True)
    assert abs(total - EXACT_TOTAL) < 1e-9
    assert [r[0] for r in rows] == list(EXACT_PINS)
    for name, value, *_ in rows:
        assert abs(value - EXACT_PINS[name]) < 1e-9, name


# ---------------------------------------------------------------- ruling 13-2's forms, one day each (fix round 1)
def _P(**kw):
    return dict(sm.POINT_T, exact=True, **kw)


def test_exact_ts_scales_growth_not_its_energy():
    # (a) at balance: the lean gained doubles at ts = 2, the fat that funds it does not
    out = {}
    for ts in (1.0, 2.0):
        b = sm.Body(_P(ts=ts), 5.0, 16.5, 13.0)
        F, M = b.F, b.M
        b.day(20.0, 2.0, 0.0)
        out[ts] = (b.F - F, b.M - M)
    assert out[1.0][0] > 0
    assert abs(out[2.0][0] - 2 * out[1.0][0]) < 1e-12
    assert abs(out[2.0][1] - out[1.0][1]) < 1e-12


def test_exact_ts_surplus_charge():
    # (b) a surplus day: growth's energy is charged at grow / ts, so the fat change does not depend on ts
    out = {}
    for ts in (1.0, 2.0):
        b = sm.Body(_P(ts=ts), 5.0, 16.5, 13.0)
        M = b.M
        b.day(20.0, 0.5, 5.0)
        out[ts] = b.M - M
    assert abs(out[2.0] - out[1.0]) < 1e-12


def test_exact_ts_deficit_charge():
    # (c) a deficit day: the recomposition's fat draw is charged at grow / ts
    out = {}
    for ts in (1.0, 2.0):
        b = sm.Body(_P(ts=ts), 5.0, 16.5, 13.0)
        M = b.M
        b.day(20.0, 2.0, -100.0)
        out[ts] = b.M - M
    assert abs(out[2.0] - out[1.0]) < 1e-12


def test_exact_grace_divided_by_ts():
    # (d) grace_d = 14 at ts = 2 is 7 days: F holds through day 7 and falls on day 8
    b = sm.Body(_P(ts=2.0, grace_d=14), 10.0, 16.5, 13.0, F0L=5.0)
    b.Pk = b.F
    F = [b.F]
    for _ in range(8):
        b.day(0.0, 0.0, 0.0)
        F.append(b.F)
    assert F[7] == F[0]
    assert F[8] < F[7]


def test_exact_one_day_detraining():
    # (e) with the status term on: F - F0 falls by exp(-lam(s) * ts / 7) in one day
    for ts in (1.0, 3.0):
        P = _P(ts=ts, grace_d=0)
        b = sm.Body(P, 10.0, 16.5, 13.0, F0L=5.0)
        s = b.s()
        gap = b.F - b.F0
        lam = math.log(2) / (P["detrain_hl_wk"] * (1.0 + P["detrain_status"] * s))
        b.day(0.0, 0.0, 0.0)
        assert abs((b.F - b.F0) - gap * math.exp(-lam * ts / 7.0)) < 1e-12, ts


def test_exact_peak_decay_ts():
    # (f) the peak's gap above F decays by exp(-dec * ts) a day
    for ts in (1.0, 3.0):
        P = _P(ts=ts)
        b = sm.Body(P, 10.0, 16.5, 13.0, F0L=10.0, peakL=12.0)
        gap = b.Pk - b.F
        b.day(0.0, 0.0, 0.0)
        dec = math.log(2) / (P["peak_hl_yr"] * 365.0)
        assert abs((b.Pk - b.F) - gap * math.exp(-dec * ts)) < 1e-12, ts


def test_exact_labile_decay_unscaled_by_ts():
    # (g) the labile lean decays by 1/x_tau_d on a day growth eats the surplus and on a deficit day (after the
    # deficit's own draw), at the same factor at ts = 1 and 2: the decay runs on the food clock (ruling 13-3)
    for ts in (1.0, 2.0):
        P = _P(ts=ts)
        b = sm.Body(P, 5.0, 16.5, 13.0)
        b.X = 1.0
        b.day(20.0, 2.0, 1.0)
        assert abs(b.X - (1.0 - 1.0 / P["x_tau_d"])) < 1e-12, ts
        b = sm.Body(P, 5.0, 16.5, 13.0)
        b.X = 1.0
        b.day(0.0, 2.0, -200.0)
        # the same day without the decay: S = 0 grows nothing, so the fit's own step differs only by it
        c = sm.Body(dict(P, exact=False), 5.0, 16.5, 13.0)
        c.X = 1.0
        c.day(0.0, 2.0, -200.0)
        assert 0.0 < c.X < 1.0
        assert abs(b.X - c.X * (1.0 - 1.0 / P["x_tau_d"])) < 1e-12, ts


def test_exact_no_labile_decay_while_surplus_remains():
    # (h) a surplus day with rest > 0 and xs = 0 (S >= S_def) leaves X unchanged
    b = sm.Body(_P(ts=1.0), 5.0, 16.5, 13.0)
    b.X = 1.0
    b.day(20.0, 2.0, 1000.0)
    assert b.X == 1.0


# ---------------------------------------------------------------- Task 11c: regain integrated exactly (Task 11 review I-2)
def _regain_day(P, b, S, p, E, tdee=2600.0):
    """The exact mode's day regain, ts applied: (Pk - F) (1 - exp(-lr min(1, G) gates ts / 7))."""
    s = b.s()
    G = sm.Gsig(P, S, s)
    gates = sm.fp(P, p) * sm.fe(P, E, s, p, tdee)
    lr = math.log(2) / P["regain_hl_wk"]
    return (b.Pk - b.F) * (1.0 - math.exp(-lr * min(1.0, G) * gates * P["ts"] / 7.0))


def test_exact_regain_never_passes_the_peak():
    # ts 30 and a 1-week half-life, both inside the option ranges: the Euler form's daily fraction is
    # ln2 * 30 / 7 = 2.97, which sent F past Pk; the exact form closes at most the whole gap
    # (a regain day: the regain arm above the growth arm, read before the day; growth may carry F past Pk)
    P = _P(ts=30.0, regain_hl_wk=1.0)
    b = sm.Body(P, 6.0, 16.5, 13.0, F0L=5.0, peakL=14.0)
    regain_days = 0
    for _ in range(60):
        Pk = b.Pk
        s = b.s()
        grow = max(0.0, P["k"] * (b.Fc - b.F) * sm.Gsig(P, 20.0, s) * sm.fp(P, 2.0) * sm.fe(P, 260.0, s, 2.0, 2600.0) / 7.0 * 30.0)
        rg = _regain_day(P, b, 20.0, 2.0, 260.0) if b.F < b.Pk else 0.0
        b.day(20.0, 2.0, 260.0)
        if rg > grow:
            regain_days += 1
            assert b.F <= Pk
    assert regain_days > 0


def test_exact_regain_is_the_integrated_form():
    # a regain day at ts 1, 2 and 30: the day's F gain is max(grow * ts, regain_day) at balance-free gates
    for ts in (1.0, 2.0, 30.0):
        for hl in (1.0, 6.0):
            P = _P(ts=ts, regain_hl_wk=hl)
            b = sm.Body(P, 6.0, 16.5, 13.0, F0L=5.0, peakL=14.0)
            s = b.s()
            G = sm.Gsig(P, 20.0, s)
            gates = sm.fp(P, 2.0) * sm.fe(P, 260.0, s, 2.0, 2600.0)
            grow = P["k"] * (b.Fc - b.F) * G * gates / 7.0 * ts
            want = max(grow, _regain_day(P, b, 20.0, 2.0, 260.0))
            F = b.F
            b.day(20.0, 2.0, 260.0)
            assert abs((b.F - F) - want) < 1e-12, (ts, hl)


def test_euler_regain_fails_the_peak_bound():
    # the mutation: the fit's Euler arm (the non-exact path, ts applied by hand) passes the peak at ts 30, hl 1
    P = dict(sm.POINT_T, regain_hl_wk=1.0)
    b = sm.Body(P, 6.0, 16.5, 13.0, F0L=5.0, peakL=14.0)
    s = b.s()
    G = sm.Gsig(P, 20.0, s)
    gates = sm.fp(P, 2.0) * sm.fe(P, 260.0, s, 2.0, 2600.0)
    euler = math.log(2) / P["regain_hl_wk"] * (b.Pk - b.F) * min(1.0, G) * gates / 7.0 * 30.0
    assert b.F + euler > b.Pk


# ---------------------------------------------------------------- Plan 16 Task 5: the named non-reproductions
@pytest.mark.parametrize("name", ["mettler_lp_share", "mettler_hp_share"])
def test_the_mettler_shares_are_named_non_reproductions(name):
    # report only since the deficit arm dropped the fat ceiling (the controller's ruling): pinned at their readings
    # (test_exact_mode_pins) and asserted still outside their bands, so one that comes back inside fails and is
    # promoted back to a weighted target
    _, rows = so.score(dict(sm.POINT_T, exact=True, ts=1.0), True)
    row = {r[0]: r for r in rows}[name]
    _, value, lo, hi, miss, weight, _ = row
    assert weight == 0
    assert not (lo <= value <= hi) and miss > 0
    assert abs(value - EXACT_PINS[name]) < 1e-9
