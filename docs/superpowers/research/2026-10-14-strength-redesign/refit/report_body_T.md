# Point T (refit 2): the full-growth surplus shrinks with status

Predecessor: point S (`compact_S.json`, kept as recorded). Source: the surplus harvest (`../surplus-report.md` § 8; science rows S2062-S2089).

## The change

```
f_e = f_bal(s) + (1 - f_bal(s)) * min(1, E / E_full(s))   for E >= 0
E_full(s) = surplus_full * (1 - full_drop * s) * TDEE       surplus_full 0.10, full_drop 0.5: +10 % untrained, +5 % at the cap
f_bal(s) = fbal0 * (1 - fbal_drop * s)                      kept; E0 and the deficit side kept
```

## Constants

| Constant | Point T | Point S |
|---|---|---|
| k | 0.00991 | 0.00991 |
| beta | 3.0 | 3.0 |
| Sg0 | 0.5 | 0.5 |
| Smax1 | 12.0 | 12.0 |
| E0 | -650.0 | -650.0 |
| E0_drop | 0.5 | 0.5 |
| fbal0 | 1.0 | 1.0 |
| fbal_drop | 0.5 | 0.5 |
| surplus_full | 0.1 | 0.1 |
| full_drop | 0.5 | (absent: E_full flat, 0) |
| a_nov | 6.0 | 6.0 |
| trained_need | 0.0 | 0.0 |
| forbes_c | 10.4 | 10.4 |
| wT | 0.35 | 0.35 |
| wP | 0.6 | 0.6 |
| pdef_hi | 1.6 | 1.6 |
| prot_floor | 0.1 | 0.1 |
| x_max_frac | 0.05 | 0.05 |
| x_tau_d | 28.0 | 28.0 |
| m | 0.33333 | 0.33333 |
| grace_d | 14 | 14 |
| detrain_hl_wk | 6.0 | 6.0 |
| regain_hl_wk | 6.0 | 6.0 |
| peak_hl_yr | 2.0 | 2.0 |
| detrain_status | 2.0 | 2.0 |

Score 0.5282; without Garthe 2011's slow arm 0.2529. Point S scored on the new registry: 1.5267 (it fails only the new degenerate check, full_drop = 0). fit sha256 `e535f9a6ad5204cf6ecd77d9cf6228d4b903eba53c7b9877f6bfb2cf037c4203`.

## The fit

- Point S's constants held; `full_drop` (c) and `fbal_drop` fitted jointly on a grid inside the report's bounds: c in 0.3-0.7 (+3 to +7 % at the cap, report § 8 item 3), fbal_drop in 0-0.7 (f_bal(1) in 0.3-1, item 1). 54 candidates (the 5 x 9 grid and a fine fbal_drop scan); k re-solved for the anchor (unchanged, 0.00991: the anchor runs at full gates).
- Joint optimum with every weighted oracle: c 0.40, fbal_drop 0.10 (Garthe 2011's slow arm pulls fbal_drop down, as at point S). Without that arm: c 0.30, fbal_drop 0.50.
- **c is flat:** score 0.5275 / 0.5278 / 0.5282 / 0.5286 / 0.5287 over 0.3-0.7 (without Garthe slow 0.2522 / 0.2526 / 0.2529 / 0.2533 / 0.2535). Its only identifying oracle is the new degenerate check `deg_full_status`, which passes from 0.3 up and fails at 0. The optimum without Garthe slow sits at the lower bound 0.3 by 0.0007 of score (bound reported); c is held at the report's 0.5, a game choice inside the bound.
- **fbal_drop:** the fine scan without Garthe slow (value, score, without Garthe slow, chk2 ratio): (0.4, 0.5194, 0.2544, 1.5506); (0.45, 0.5238, 0.2536, 1.6663); (0.5, 0.5282, 0.2529, 1.8009); (0.525, 0.5304, 0.2525, 1.8768); (0.55, 0.5327, 0.2522, 1.9595); (0.56, 0.5336, 0.2520, 1.9947); (0.57, 0.5354, 0.2529, 2.0311); (0.58, 0.5401, 0.2565, 2.0690); (0.6, 0.5594, 0.2737, 2.1491). Its optimum (0.56) sits 0.005 below the edge of report check 2 (surplus gain <= 2x balance at s = 0.9), so its x1.05 probe crosses the band; 0.5 is within 0.001 of that optimum and stays inside under x1.05. Held at 0.5.
- At a grid bound (as at point S): Sg0, Smax1, fbal0, pdef_hi. `surplus_full` at 0.05 reads a cliff (score 1.5361): the degenerate check's probes are at +5 % and +10 %, and at e_full 0.05 both statuses saturate at +5 %, so it reads 0. That is a limit of the check's probes, not an evidence miss.

## New and re-graded oracles

- **Helms 2023 re-graded (S2062, S2063):** MOD ("+5 %") reported +489 kcal/d and HIGH ("+15 %") +719 kcal/d over their maintenance phases; both gained 3.3 kg; no muscle-thickness difference against maintenance (BF10 0.32-0.77). The three weighted Helms oracles now run at +489 and +719 kcal/d, MAIN at balance; MAIN at its reported +169, and the two body-mass gains, are report-only.
- **Henselmans 2026 (S2064, S2065):** s 0.7 (a judgment inside 0.6-0.8; the FFMI was not reported), 8 wk, 16 sets/wk, 2.0 g/kg, fat 14 kg, TDEE 2700, habitual intake taken as balance; contrasts +250 (Atwater) and +485 kcal/d (self-report). Lean (F + lx) contrast inside the DXA CI -0.19 to 1.69 kg; muscle contrast as % of F inside the elbow-flexor CI over an assumed 4.0 cm baseline (-2.25 to +4.75 %; relative thickness read as relative muscle, a stated assumption).
- **Angus's ruling as a direction oracle:** a year at +5 % of TDEE (20 sets, 2.0 g/kg) builds more muscle than balance at s = 0.9 and s = 0.6 (pass/fail).
- **Degenerate-read check `deg_full_status`:** the share of the +10 % gain that +5 % reaches over 8 wk is higher at s = 0.9 than at s = 0.5 by at least 0.05; at c = 0 it reads 0.0013 and fails.

## Oracle table (point T)

| Oracle | Value | Band | Miss | Weight | Source |
|---|---|---|---|---|---|
| year1_kg_20sets | 7.5565 | 6.8 to 8.5 | 0.000 | 1 | S1.15 McDonald x0.75 (first-harvest calibration) |
| yr2_over_yr1 | 0.4495 | 0.4 to 0.6 | 0.000 | 1 | S1.15 halving; H.49/H.50 year-1 dominance |
| yr3_over_yr2 | 0.5007 | 0.4 to 0.65 | 0.000 | 1 | S1.15 halving |
| benito_10wk_kg | 1.4507 | 1.12 to 1.96 | 0.000 | 1 | S1.9 Benito 2020 untrained FFM +1.54 (CI 1.12-1.96) |
| pelland_30_over_12 | 1.6204 | 1.55 to 2 | 0.000 | 1 | H.1 Pelland sqrt fit, derived 1.77 |
| h8_3_over_9 | 0.4615 | 0.5 to 0.9 | 0.096 | 1 | H.8 1 vs 3 sets: +3.7 vs +5.2 % (0.71) |
| aube_24_over_12 | 1.4441 | 0.7 to 1.4 | 0.063 | 1 | H.5 Aube 2022 advanced: 12=18=24 sets |
| longland_hp_lean | 0.5229 | 0.6 to 1.8 | 0.064 | 1 | S0064 Longland 2.4 g/kg -40 %: +1.2 +/- 1.0 kg |
| longland_lp_lean | -0.4213 | -0.4 to 0.6 | 0.021 | 1 | S0064 Longland 1.2 g/kg: +0.1 +/- 1.0 kg |
| longland_hp_fat | -3.6595 | -5 to -3 | 0.000 | 0 | S0064 fat -4.8 +/- 1.6 kg (energy side; report) |
| garthe11_slow_lean | 0.2753 | 0.8 to 1.8 | 0.525 | 1 | Garthe 2011 (PMID 21558571) -19 %: LBM +2.1 % |
| garthe11_fast_lean | -0.1564 | -0.6 to 0.4 | 0.000 | 1 | Garthe 2011 -30 %: LBM -0.2 % |
| mk_minus500_lean | -0.2075 | -0.3 to 0.3 | 0.000 | 1 | S1.28 Murphy & Koehler: -500 kcal/d -> no lean gain |
| trained_maint_8wk | 0.4071 | 0.1 to 1.5 | 0.000 | 1 | Helms 2023 MAIN; Antonio 2015 (PMID 26500462) FFM +1.5 |
| trained_maint_premise | 0.4071 | -0.1 to 0.1 | 1.535 | 0 | Angus premise: trained ~0 at maintenance |
| helms23_high719_over_maint | 1.3279 | 0.8 to 1.6 | 0.000 | 1 | S2062/S2063 Helms 2023 HIGH (+719 kcal/d reported): no MT difference |
| garthe13_lean_ratio | 1.0661 | 0.8 to 1.35 | 0.000 | 1 | S1.30 Garthe 2013: LBM gain not different |
| garthe13_fat_diff | 3.3242 | 0.8 to 2.5 | 0.485 | 1 | S1.30 Garthe 2013: FM +15 % vs +3 % |
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
| deg_surplus_2pct | 0.0049 | > 1e-05 (pass/fail) | 0.000 | 1 | degenerate check: +2 % surplus moves lean |
| deg_sets_5pct | 0.0373 | > 1e-05 (pass/fail) | 0.000 | 1 | degenerate check: +5 % sets moves lean |
| moro16_maint_8wk | 0.0175 | -0.3 to 0.8 | 0.000 | 1 | S3.1 Moro 2016: FFM +0.64/+0.48 kg n.s. (+0.86/+0.64 %) |
| moro16_tre_minus250 | -0.0726 | -0.5 to 0.8 | 0.000 | 1 | S3.1 Moro 2016 TRE: fat 10.90->9.28; -250 kcal/d inferred; FFM held |
| isola25_controls_46wk | 0.1383 | -1 to 1 | 0.000 | 1 | S3.2 Isola 2025: controls no systematic change |
| helms23_mod489_over_maint | 1.3279 | 0.8 to 1.6 | 0.000 | 1 | S2062/S2063 Helms 2023 MOD (+489 kcal/d reported) = maintenance |
| helms23_high719_minus_maint | 0.1335 | -0.3 to 0.5 | 0.000 | 1 | S2062 Helms 2023 HIGH (+719): within one noise band, 8 wk |
| helms23_mod_minus_main169 | 0.0248 | -0.3 to 0.5 | 0.000 | 0 | S2062 MAIN at its reported +169 (report) |
| helms23_mod_mass_kg | 3.3371 | 2.5 to 4.1 | 0.000 | 0 | S2033 MOD body mass +3.3 +/- 0.8 kg (report) |
| helms23_high_mass_kg | 4.7014 | 1.8 to 4.8 | 0.000 | 0 | S2033 HIGH body mass +3.3 +/- 1.5 kg (report) |
| hens26_lean_250 | 0.0936 | -0.19 to 1.69 | 0.000 | 1 | S2064/S2065 Henselmans 2026 DXA lean CI, +250 (Atwater) |
| hens26_lean_485 | 0.0936 | -0.19 to 1.69 | 0.000 | 1 | S2064/S2065 Henselmans 2026 DXA lean CI, +485 (self-report) |
| hens26_muscle_pct_250 | 0.1471 | -2.25 to 4.75 | 0.000 | 1 | S2064 elbow-flexor CI as % of 4.0 cm, +250 |
| hens26_muscle_pct_485 | 0.1471 | -2.25 to 4.75 | 0.000 | 1 | S2064 elbow-flexor CI as % of 4.0 cm, +485 |
| angus_surplus5_1yr_s09 | 0.1020 | > 1e-06 (pass/fail) | 0.000 | 1 | Angus ruling: +5 % for a year beats balance at s = 0.9 |
| angus_surplus5_1yr_s06 | 0.4466 | > 1e-06 (pass/fail) | 0.000 | 1 | Angus ruling: +5 % for a year beats balance at s = 0.6 |
| deg_full_status | 0.2365 | > 0.05 (pass/fail) | 0.000 | 1 | degenerate check: E_full shrinks with s (share of +10 % reached at +5 %) |
| chk1_s09_bal_dF_pct | 0.0382 | 0 to 0.5 | 0.000 | 1 | report sec. 9 check 1: dF < 0.5 % at balance, 8 wk |
| chk1_s09_bal_fat_kg | -0.0049 | -0.5 to 0.5 | 0.000 | 1 | report sec. 9 check 1: fat steady |
| chk2_s09_surplus_over_bal | 1.8009 | 1 to 2 | 0.000 | 1 | report sec. 9 check 2: <= 2x balance |
| chk2_s09_surplus_dF_pct | 0.0688 | 0 to 1 | 0.000 | 1 | report sec. 9 check 2: < 1 % |
| chk2_s09_surplus_fat_share | 0.9738 | 0.5 to 1 | 0.000 | 1 | report sec. 9 check 2: fat carries most of the weight |
| chk4_s09_contest_minus500 | -1.3206 | -5 to 0 | 0.000 | 1 | report sec. 9 check 4: dF <= 0 at contest fat |
| deg_surplus_2pct_s09 | 0.0075 | > 1e-06 (pass/fail) | 0.000 | 1 | degenerate check: +2 % surplus moves lean at s = 0.9 |
| deg_fbal_status | 0.0336 | > 1e-09 (pass/fail) | 0.000 | 0 | degenerate check: balance growth per headroom falls with s |
| buechel26_contest_ffm | -0.5635 | -2.6 to -0.9 | 0.198 | 0 | S3.4 Buechel 2026 contest prep (mixed sex; report) |
| roth23_minus30pct_lean | -0.2699 | -1.2 to -0.3 | 0.033 | 0 | S3.11 Roth 2023 trained men -30 % (report) |

## Named conflicts (the same set as point S)

- h8_3_over_9: 0.4615 against 0.5 to 0.9 (miss 0.096).
- aube_24_over_12: 1.4441 against 0.7 to 1.4 (miss 0.063).
- longland_hp_lean: 0.5229 against 0.6 to 1.8 (miss 0.064).
- longland_lp_lean: -0.4213 against -0.4 to 0.6 (miss 0.021).
- garthe11_slow_lean: 0.2753 against 0.8 to 1.8 (miss 0.525).
- garthe13_fat_diff: 3.3242 against 0.8 to 2.5 (miss 0.485).
- Garthe 2011's slow arm cannot be met with Murphy & Koehler at a status-dependent gate; Garthe 2013's fat difference belongs to the energy side; the growth misses (H.8, Aube) are point R's.
- Henselmans's DXA point estimate (+0.76 kg) is far above the model's contrast (0.09 kg); the model sits inside the interval, near its lower end, and part of the measured difference is expected glycogen and water (S2039).

## Profiles (value -> score / score without Garthe 2011 slow)

- beta: 1.5 -> 0.8396 / 0.4385; 2 -> 0.7008 / 0.3242; 2.5 -> 0.6053 / 0.2664; 3 -> 0.5282 / 0.2529; 3.5 -> 0.7225 / 0.5770
- Sg0: 0.5 -> 0.5282 / 0.2529; 0.7 -> 0.6018 / 0.4046; 0.85 -> 1.5478 / 1.4363; 1 -> 12.1427 / 12.1416
- Smax1: 12 -> 0.5282 / 0.2529; 15 -> 0.7099 / 0.3867; 20 -> 1.2665 / 0.9157; 30 -> 1.5756 / 1.2248
- E0: -400 -> 1.0582 / 0.4244; -500 -> 0.8343 / 0.4057; -575 -> 0.6001 / 0.2624; -650 -> 0.5282 / 0.2529; -800 -> 0.4465 / 0.2496; -1000 -> 0.3884 / 0.2488
- E0_drop: 0 -> 0.4825 / 0.2527; 0.25 -> 0.5036 / 0.2528; 0.4 -> 0.5179 / 0.2529; 0.5 -> 0.5282 / 0.2529; 0.6 -> 0.5391 / 0.2529; 0.75 -> 0.5569 / 0.2530
- fbal0: 0.85 -> 0.6239 / 0.2772; 0.925 -> 0.5668 / 0.2570; 1 -> 0.5282 / 0.2529
- fbal_drop: 0 -> 5.4862 / 5.2604; 0.1 -> 0.4942 / 0.2589; 0.2 -> 0.5024 / 0.2574; 0.25 -> 0.5066 / 0.2566; 0.3 -> 0.5108 / 0.2559; 0.4 -> 0.5194 / 0.2544; 0.5 -> 0.5282 / 0.2529; 0.6 -> 0.5594 / 0.2737; 0.7 -> 0.9909 / 0.6945
- a_nov: 0 -> 1.4987 / 0.6016; 1.4 -> 1.0460 / 0.4290; 2.8 -> 0.7565 / 0.2983; 4.2 -> 0.6238 / 0.2655; 6 -> 0.5282 / 0.2529; 8 -> 0.4653 / 0.2493
- surplus_full: 0.05 -> 1.5361 / 1.2609; 0.075 -> 0.5318 / 0.2565; 0.1 -> 0.5282 / 0.2529; 0.15 -> 0.5246 / 0.2493
- full_drop: 0.3 -> 0.5275 / 0.2522; 0.4 -> 0.5278 / 0.2526; 0.5 -> 0.5282 / 0.2529; 0.6 -> 0.5286 / 0.2533; 0.7 -> 0.5287 / 0.2535
- wT: 0.2 -> 0.8977 / 0.4046; 0.35 -> 0.5282 / 0.2529; 0.5 -> 0.5277 / 0.2525; 0.65 -> 0.5308 / 0.2555
- wP: 0.3 -> 1.6518 / 0.6598; 0.45 -> 0.7849 / 0.2919; 0.6 -> 0.5282 / 0.2529; 0.75 -> 0.5277 / 0.2525
- prot_floor: 0.05 -> 0.4435 / 0.2491; 0.1 -> 0.5282 / 0.2529; 0.15 -> 0.6353 / 0.2611; 0.3 -> 1.1771 / 0.3777
- pdef_hi: 1.6 -> 0.5282 / 0.2529; 2 -> 0.6694 / 0.2952; 2.4 -> 1.1061 / 0.3926; 2.8 -> 1.5183 / 0.5263
- detrain_hl_wk: 4.9 -> 0.5282 / 0.2529; 6 -> 0.5282 / 0.2529; 7 -> 0.5339 / 0.2587; 8 -> 0.6078 / 0.3325; 9.2 -> 0.8284 / 0.5531
- regain_hl_wk: 3 -> 0.5282 / 0.2529; 4 -> 0.5282 / 0.2529; 6 -> 0.5282 / 0.2529; 8 -> 0.5282 / 0.2529
- m: 0.2 -> 0.5282 / 0.2529; 0.333 -> 0.5282 / 0.2529; 0.5 -> 0.5282 / 0.2529
- grace_d: 7 -> 0.5282 / 0.2529; 14 -> 0.5282 / 0.2529; 21 -> 0.5299 / 0.2547
- detrain_status: 0 -> 0.5282 / 0.2529; 1 -> 0.5282 / 0.2529; 2 -> 0.5282 / 0.2529; 3 -> 0.5282 / 0.2529

## Stability (x0.95 and x1.05: score, oracles moved)

- k: [0.5557, 49], [0.503, 49]
- beta: [0.5215, 48], [0.545, 48]
- Sg0: [0.5222, 48], [0.5361, 48]
- Smax1: [0.5242, 20], [0.5392, 20]
- E0: [0.554, 9], [0.5059, 9]
- E0_drop: [0.5255, 8], [0.5309, 8]
- fbal0: [0.5534, 45], [1.5053, 45]
- fbal_drop: [0.526, 44], [0.5304, 44]
- a_nov: [0.5407, 8], [0.5166, 8]
- surplus_full: [0.5288, 14], [0.5277, 14]
- wT: [0.5297, 3], [0.5277, 3]
- wP: [0.5294, 5], [0.5277, 5]
- prot_floor: [0.5187, 9], [0.5378, 9]
- pdef_hi: [0.5277, 4], [0.531, 5]
- detrain_hl_wk: [0.5282, 3], [0.5282, 3]
- regain_hl_wk: [0.5282, 1], [0.5282, 1]
- m: [0.5282, 0], [0.5282, 0] FLAT
- grace_d: [0.5282, 2], [0.5282, 0]
- forbes_c: [0.5225, 15], [0.5342, 15]
- x_max_frac: [0.5282, 0], [0.5282, 0] FLAT
- detrain_status: [0.5282, 2], [0.5282, 2]
- full_drop: [0.5281, 14], [0.5283, 14]

`fbal0` x1.05 is a gate above 1 (its physical bound), as at point S; `m` and `x_max_frac` are flat, as at point S.

## One year for trained lifters (20 sets/wk, 2.0 g/kg, TDEE 2800, fat 11 kg; muscle F in kg)

| s (level) | Point | Maintenance | +5 % | +10 % | Bulk +10 % 18 wk / cut -500 8 wk, x2 |
|---|---|---|---|---|---|
| 0.9 (15.35) | T | +0.15 (fat -0.03, L 15.46) | +0.26 (fat +5.35, L 15.53) | +0.27 (fat +10.74, L 15.53) | -0.06 (fat +1.55, L 15.31) |
| 0.9 (15.35) | S | +0.15 (fat -0.03, L 15.46) | +0.21 (fat +5.36, L 15.50) | +0.27 (fat +10.74, L 15.53) | -0.06 (fat +1.55, L 15.31) |
| 0.6 (11.90) | T | +1.71 (fat -0.33, L 13.09) | +2.16 (fat +4.98, L 13.39) | +2.29 (fat +10.35, L 13.49) | +1.63 (fat +1.23, L 13.03) |
| 0.6 (11.90) | S | +1.71 (fat -0.33, L 13.09) | +2.01 (fat +5.01, L 13.29) | +2.29 (fat +10.35, L 13.49) | +1.63 (fat +1.23, L 13.03) |

- At s = 0.9, +5 % for a year gains nearly what +10 % does (the gate is full at +5.5 %), and more than balance; under point S, +5 % bought half the step from balance to +10 %.
- Bulk +10 % and the cut are unchanged from point S: +10 % is at or above E_full at every status in both points.
- At s = 0.9 the bulk-cut cycles net less muscle than a year at maintenance: each cut at -500 kcal/d, 2.4 g/kg removes about what the bulk added at that headroom.
- The fat column is the offline model's: TDEE is held fixed as weight rises, so a year at +5 % stores about 5 kg of fat.
- Untrained and novice runs, the per-trait trajectories, detraining and regain are unchanged from point S (f_bal(0) = 1; the anchor runs at full gates): `scenarios_T.txt`.
