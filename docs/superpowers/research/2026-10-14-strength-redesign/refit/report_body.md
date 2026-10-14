| Constant | Point S |
|---|---|
| k | 0.00991 |
| beta | 3.0 |
| Sg0 | 0.5 |
| Smax1 | 12.0 |
| E0 | -650.0 |
| E0_drop | 0.5 |
| fbal0 | 1.0 |
| fbal_drop | 0.5 |
| a_nov | 6.0 |
| surplus_full | 0.1 |
| trained_need | 0.0 |
| wT | 0.35 |
| wP | 0.6 |
| prot_floor | 0.1 |
| pdef_hi | 1.6 |
| forbes_c | 10.4 |
| detrain_hl_wk | 6.0 |
| detrain_status | 2.0 |
| regain_hl_wk | 6.0 |
| m | 0.33333 |
| grace_d | 14 |
| peak_hl_yr | 2.0 |
| x_max_frac | 0.05 |
| x_tau_d | 28.0 |

Score 0.5267; without Garthe 2011's slow arm 0.2514. fit sha256 `f9f781e6205303d6514011bbc523ce98d85eb7b753e8c33c9759fafc2da86569`.

## Oracle table (point S)

| Oracle | Value | Band | Miss | Weight | Source |
|---|---|---|---|---|---|
| year1_kg_20sets | 7.4903 | 6.8 to 8.5 | 0.000 | 1 | S1.15 McDonald x0.75 (first-harvest calibration) |
| yr2_over_yr1 | 0.4388 | 0.4 to 0.6 | 0.000 | 1 | S1.15 halving; H.49/H.50 year-1 dominance |
| yr3_over_yr2 | 0.4995 | 0.4 to 0.65 | 0.000 | 1 | S1.15 halving |
| benito_10wk_kg | 1.4507 | 1.12 to 1.96 | 0.000 | 1 | S1.9 Benito 2020 untrained FFM +1.54 (CI 1.12-1.96) |
| pelland_30_over_12 | 1.6195 | 1.55 to 2 | 0.000 | 1 | H.1 Pelland sqrt fit, derived 1.77 |
| h8_3_over_9 | 0.4616 | 0.5 to 0.9 | 0.096 | 1 | H.8 1 vs 3 sets: +3.7 vs +5.2 % (0.71) |
| aube_24_over_12 | 1.4455 | 0.7 to 1.4 | 0.065 | 1 | H.5 Aube 2022 advanced: 12=18=24 sets |
| longland_hp_lean | 0.5229 | 0.6 to 1.8 | 0.064 | 1 | S0064 Longland 2.4 g/kg -40 %: +1.2 +/- 1.0 kg |
| longland_lp_lean | -0.4213 | -0.4 to 0.6 | 0.021 | 1 | S0064 Longland 1.2 g/kg: +0.1 +/- 1.0 kg |
| longland_hp_fat | -3.6595 | -5 to -3 | 0.000 | 0 | S0064 fat -4.8 +/- 1.6 kg (energy side; report) |
| garthe11_slow_lean | 0.2753 | 0.8 to 1.8 | 0.525 | 1 | Garthe 2011 (PMID 21558571) -19 %: LBM +2.1 % |
| garthe11_fast_lean | -0.1564 | -0.6 to 0.4 | 0.000 | 1 | Garthe 2011 -30 %: LBM -0.2 % |
| mk_minus500_lean | -0.2075 | -0.3 to 0.3 | 0.000 | 1 | S1.28 Murphy & Koehler: -500 kcal/d -> no lean gain |
| trained_maint_8wk | 0.4071 | 0.1 to 1.5 | 0.000 | 1 | Helms 2023 MAIN; Antonio 2015 (PMID 26500462) FFM +1.5 |
| trained_maint_premise | 0.4071 | -0.1 to 0.1 | 1.535 | 0 | Angus premise: trained ~0 at maintenance |
| helms23_15pct_over_maint | 1.3279 | 0.8 to 1.6 | 0.000 | 1 | S1.29 Helms 2023: no MT difference by surplus |
| garthe13_lean_ratio | 1.0838 | 0.8 to 1.35 | 0.000 | 1 | S1.30 Garthe 2013: LBM gain not different |
| garthe13_fat_diff | 3.3212 | 0.8 to 2.5 | 0.483 | 1 | S1.30 Garthe 2013: FM +15 % vs +3 % |
| mettler_lp_share | 0.5692 | 0.35 to 0.7 | 0.000 | 1 | Mettler 2010 (PMID 19927027) 1.0 g/kg: 1.6 of 3.0 kg lean |
| mettler_hp_share | 0.1823 | 0.05 to 0.35 | 0.000 | 1 | Mettler 2010 2.3 g/kg: 0.3 of 1.5 kg lean |
| quarter_rule_share | 0.2246 | 0.15 to 0.35 | 0.000 | 1 | Heymsfield 2014 (PMID 24447775); S0072 Weinheimer |
| pasiakos_0.8_minus_1.6 | 0.1624 | 0.1 to 0.5 | 0.000 | 1 | Pasiakos 2013 (PMID 23739654) direction (abstract) |
| bray_15pct_lean | 2.4068 | 1.5 to 3.5 | 0.000 | 1 | S0605 Bray 2012: lean +2.87 kg at 15 % protein |
| bray_5pct_lean | 0.0000 | -0.7 to 0.5 | 0.000 | 1 | S0605 Bray 2012: no lean gain at 5 % |
| bray_muscle_no_signal | 0.0000 | -0.05 to 0.05 | 0.000 | 1 | H.41/H.42/S0606: no muscle without the signal |
| rantila_kept_frac | 0.4302 | 0.24 to 0.47 | 0.000 | 1 | H.51 Räntilä 2025: 24-47 % kept after 10 wk off |
| rantila_block2_over_1 | 0.9385 | 0.8 to 1.25 | 0.000 | 1 | H.51 Räntilä: block 2 = block 1 |
| bickel_third_kept | 1.6475 | 0.85 to 1.8 | 0.000 | 1 | H.13 Bickel 2011: 1/3 dose kept size 32 wk |
| bickel_ninth_kept | 1.2636 | 0.85 to 1.4 | 0.000 | 1 | H.13 Bickel 2011: 1/9 dose kept size 32 wk |
| detrain_halflife_wk | 6.7143 | 4.9 to 9.2 | 0.000 | 1 | H.51 Räntilä derived 4.9-9.2 wk |
| deg_protein_2pct | 0.0285 | > 1e-05 (pass/fail) | 0.000 | 1 | degenerate check: +2 % protein moves lean |
| deg_surplus_2pct | 0.0047 | > 1e-05 (pass/fail) | 0.000 | 1 | degenerate check: +2 % surplus moves lean |
| deg_sets_5pct | 0.0373 | > 1e-05 (pass/fail) | 0.000 | 1 | degenerate check: +5 % sets moves lean |
| moro16_maint_8wk | 0.0175 | -0.3 to 0.8 | 0.000 | 1 | S3.1 Moro 2016: FFM +0.64/+0.48 kg n.s. (+0.86/+0.64 %) |
| moro16_tre_minus250 | -0.0726 | -0.5 to 0.8 | 0.000 | 1 | S3.1 Moro 2016 TRE: fat 10.90->9.28; -250 kcal/d inferred; FFM held |
| isola25_controls_46wk | 0.1383 | -1 to 1 | 0.000 | 1 | S3.2 Isola 2025: controls no systematic change |
| helms23_5pct_over_maint | 1.1643 | 0.8 to 1.6 | 0.000 | 1 | S1.29/S3.16 Helms 2023: +5 % = maintenance |
| helms23_15pct_minus_maint | 0.1335 | -0.3 to 0.5 | 0.000 | 1 | S3.16 report check 3: within one noise band, 8 wk |
| chk1_s09_bal_dF_pct | 0.0382 | 0 to 0.5 | 0.000 | 1 | report sec. 9 check 1: dF < 0.5 % at balance, 8 wk |
| chk1_s09_bal_fat_kg | -0.0049 | -0.5 to 0.5 | 0.000 | 1 | report sec. 9 check 1: fat steady |
| chk2_s09_surplus_over_bal | 1.8009 | 1 to 2 | 0.000 | 1 | report sec. 9 check 2: <= 2x balance |
| chk2_s09_surplus_dF_pct | 0.0688 | 0 to 1 | 0.000 | 1 | report sec. 9 check 2: < 1 % |
| chk2_s09_surplus_fat_share | 0.9738 | 0.5 to 1 | 0.000 | 1 | report sec. 9 check 2: fat carries most of the weight |
| chk4_s09_contest_minus500 | -1.3206 | -5 to 0 | 0.000 | 1 | report sec. 9 check 4: dF <= 0 at contest fat |
| deg_surplus_2pct_s09 | 0.0041 | > 1e-06 (pass/fail) | 0.000 | 1 | degenerate check: +2 % surplus moves lean at s = 0.9 |
| deg_fbal_status | 0.0336 | > 1e-09 (pass/fail) | 0.000 | 0 | degenerate check: balance growth per headroom falls with s |
| buechel26_contest_ffm | -0.5635 | -2.6 to -0.9 | 0.198 | 0 | S3.4 Buechel 2026 contest prep (mixed sex; report) |
| roth23_minus30pct_lean | -0.2699 | -1.2 to -0.3 | 0.033 | 0 | S3.11 Roth 2023 trained men -30 % (report) |

## Profiles (value → score / score without Garthe 2011 slow)

- beta: 1.5 → 0.8550 / 0.4539; 2 → 0.7102 / 0.3336; 2.5 → 0.6038 / 0.2649; 3 → 0.5267 / 0.2514; 3.5 → 0.7153 / 0.5698
- Sg0: 0.5 → 0.5267 / 0.2514; 0.7 → 0.6141 / 0.4170; 0.85 → 1.5019 / 1.3904; 1 → 9.8308 / 9.8297
- Smax1: 12 → 0.5267 / 0.2514; 15 → 0.7096 / 0.3864; 20 → 1.2701 / 0.9193; 30 → 1.5783 / 1.2275
- E0: -400 → 1.0567 / 0.4228; -500 → 0.8328 / 0.4042; -575 → 0.5986 / 0.2609; -650 → 0.5267 / 0.2514; -800 → 0.4450 / 0.2481; -1000 → 0.3869 / 0.2473
- E0_drop: 0 → 0.4809 / 0.2512; 0.25 → 0.5021 / 0.2513; 0.4 → 0.5164 / 0.2513; 0.5 → 0.5267 / 0.2514; 0.6 → 0.5376 / 0.2514; 0.75 → 0.5554 / 0.2515
- fbal0: 0.85 → 0.6210 / 0.2743; 0.925 → 0.5646 / 0.2548; 1 → 0.5267 / 0.2514
- fbal_drop: 0 → 2.4862 / 2.2604; 0.25 → 0.5058 / 0.2558; 0.5 → 0.5267 / 0.2514; 0.7 → 0.9888 / 0.6924
- a_nov: 0 → 1.4972 / 0.6001; 1.4 → 1.0445 / 0.4275; 2.8 → 0.7550 / 0.2968; 4.2 → 0.6222 / 0.2640; 6 → 0.5267 / 0.2514; 8 → 0.4637 / 0.2477
- surplus_full: 0.05 → 0.5361 / 0.2609; 0.075 → 0.5298 / 0.2545; 0.1 → 0.5267 / 0.2514; 0.15 → 0.5236 / 0.2483
- wT: 0.2 → 0.8961 / 0.4031; 0.35 → 0.5267 / 0.2514; 0.5 → 0.5262 / 0.2509; 0.65 → 0.5293 / 0.2540
- wP: 0.3 → 1.6503 / 0.6582; 0.45 → 0.7834 / 0.2903; 0.6 → 0.5267 / 0.2514; 0.75 → 0.5262 / 0.2509
- prot_floor: 0.05 → 0.4419 / 0.2476; 0.1 → 0.5267 / 0.2514; 0.15 → 0.6337 / 0.2596; 0.3 → 1.1756 / 0.3762
- pdef_hi: 1.6 → 0.5267 / 0.2514; 2 → 0.6679 / 0.2937; 2.4 → 1.1046 / 0.3911; 2.8 → 1.5168 / 0.5247
- detrain_hl_wk: 4.9 → 0.5267 / 0.2514; 6 → 0.5267 / 0.2514; 7 → 0.5324 / 0.2571; 8 → 0.6063 / 0.3310; 9.2 → 0.8269 / 0.5516
- regain_hl_wk: 3 → 0.5267 / 0.2514; 4 → 0.5267 / 0.2514; 6 → 0.5267 / 0.2514; 8 → 0.5267 / 0.2514
- m: 0.2 → 0.5267 / 0.2514; 0.333 → 0.5267 / 0.2514; 0.5 → 0.5267 / 0.2514
- grace_d: 7 → 0.5267 / 0.2514; 14 → 0.5267 / 0.2514; 21 → 0.5284 / 0.2531
- detrain_status: 0 → 0.5267 / 0.2514; 1 → 0.5267 / 0.2514; 2 → 0.5267 / 0.2514; 3 → 0.5267 / 0.2514

## Stability (×0.95 and ×1.05: score, oracles moved)

- k: [0.5542, 39], [0.5014, 39]
- beta: [0.5197, 38], [0.5438, 38]
- Sg0: [0.5205, 38], [0.5347, 38]
- Smax1: [0.5224, 17], [0.5379, 17]
- E0: [0.5524, 9], [0.5044, 9]
- E0_drop: [0.524, 8], [0.5293, 8]
- fbal0: [0.5514, 37], [1.5042, 37]
- fbal_drop: [0.5245, 36], [0.5288, 36]
- a_nov: [0.5392, 8], [0.5151, 8]
- surplus_full: [0.5271, 11], [0.5262, 14]
- wT: [0.5282, 3], [0.5262, 3]
- wP: [0.5279, 5], [0.5262, 5]
- prot_floor: [0.5172, 9], [0.5363, 9]
- pdef_hi: [0.5262, 4], [0.5295, 5]
- detrain_hl_wk: [0.5267, 3], [0.5267, 3]
- regain_hl_wk: [0.5267, 1], [0.5267, 1]
- m: [0.5267, 0], [0.5267, 0] FLAT
- grace_d: [0.5267, 2], [0.5267, 0]
- forbes_c: [0.5209, 15], [0.5327, 15]
- x_max_frac: [0.5267, 0], [0.5267, 0] FLAT
- detrain_status: [0.5267, 2], [0.5267, 2]

At a grid bound: Sg0, Smax1, fbal0, pdef_hi
