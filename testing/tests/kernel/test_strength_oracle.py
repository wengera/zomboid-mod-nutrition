"""The strength fit's tracked oracle (Plan 13 Task 2): point T reproduces compact_T.json, and the exact mode of
ruling 13-2 keeps every weighted pass and is pinned oracle by oracle."""
import json, os
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
    for _ in range(int(round(hl_days))):
        b.day(0.0, 0.0, 0.0)
    assert abs((b.F - F0) / gap0 - 0.5) < 0.01


# The exact-mode re-score (ruling 13-2, ts = 1) of every registry oracle at point T, pinned so a later kernel or
# oracle change that moves one is named. Against the record only rantila_kept_frac and rantila_block2_over_1 moved.
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
    'garthe11_fast_lean': -0.15637476335611922,
    'mk_minus500_lean': -0.20754013114804337,
    'trained_maint_8wk': 0.4070969717299633,
    'trained_maint_premise': 0.4070969717299633,
    'helms23_high719_over_maint': 1.3278647632358014,
    'garthe13_lean_ratio': 1.0661433036295154,
    'garthe13_fat_diff': 3.3242176760555857,
    'mettler_lp_share': 0.56921909092098,
    'mettler_hp_share': 0.18229532621015493,
    'quarter_rule_share': 0.22456898837071676,
    'pasiakos_0.8_minus_1.6': 0.16236486696560648,
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
    'chk4_s09_contest_minus500': -1.3205987075961332,
    'deg_surplus_2pct_s09': 0.007505486325641186,
    'deg_fbal_status': 0.03359525461830324,
    'buechel26_contest_ffm': -0.5635465188507567,
    'roth23_minus30pct_lean': -0.26987869282115895,
}


def test_exact_mode_pins():
    total, rows = so.score(dict(sm.POINT_T, exact=True, ts=1.0), True)
    assert abs(total - EXACT_TOTAL) < 1e-9
    assert [r[0] for r in rows] == list(EXACT_PINS)
    for name, value, *_ in rows:
        assert abs(value - EXACT_PINS[name]) < 1e-9, name
