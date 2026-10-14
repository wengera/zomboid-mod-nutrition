# Pre-mint citation review: lean-science-part.tsv

Reviewer model: claude-opus-5-5. Read-only; 2026-10-14.
Method: every PMID resolved through PubMed efetch (title, first author, year, journal, DOI matched for all 33 settled rows); full text read in PMC/Europe PMC for Hull 2011 (PMC3306818, Tables 2-3), Benito 2020 (PMC7068252), Trexler 2017a (PMC5438288) and Trexler 2017b (PMC4878695); the McDonald page read at bodyrecomposition.com, its two tables read off the page images. Duplicates checked against `docs/reference/science.tsv` and the other three part files: no duplicate (the register's S0617/S0078 Psilander rows and S0074-S0076/S0621 rodent rows are different studies; S0077 is Eftestol 2020, not 2022; S3.16 in advanced-recomp is a declared second reading of Helms 2023, not a copy of S1.29).

## Verdicts

- S1.1 PASS. Kouri 1995 abstract: 25.0 limit, 20 Mr America winners mean 25.4, the 6.3 x (1.80 - height) correction, users above 25 and some above 30, "preliminary".
- S1.2 PASS. Schutz 2002 abstract: median FFMI 18-34 y 18.9 (men) and 15.4 (women), no age difference in men, modest rise in women.
- S1.3 PASS. Hull 2011 Tables 2 and 3 give every mean, SD, age and height in the row; mid-20s and mid-40s turning points and the faster male decline are in the Results.
- S1.4 PASS. Abstract: 62 (26.4 %) above 25, 97.5th percentile 28.1, linemen highest; the full text confirms no independent drug testing.
- S1.5 PASS. Magee 2024 abstract: 21.5 +/- 1.9 vs 17.9 +/- 1.8; throwers 25.7, volleyball 19.9, basketball 18.9, rowers 16.9; air-displacement plethysmography.
- S1.6 PASS. Blue 2019 abstract: 16.9 +/- 1.7, range 13.3-25.5, medians 15.1 (XC) to 18.0 (football).
- S1.7 PASS. Abe 2020 abstract: largest SM index 13.2, about 77 % of the largest male athlete, similar difference in nonathletes; one athlete above 13.
- S1.8 PASS. Gonzalez-Cano 2024 abstract: FFMI 23.83 +/- 0.90 vs 22.80 +/- 0.22; LBM 69.80 +/- 3.78 vs 64.49 +/- 2.35; n = 11 (6 PRO, 5 AMA), 24.8 +/- 2.3 y.
- S1.9 FIX. The numbers are right (abstract and full text section 3.3), but every effect in Benito 2020 is a pre-post change within the training groups (the forest plots pair post and pre means of the same group), not a contrast with non-training controls; the row must say so.
  - `range` -> `pre-post change within the training groups (post minus pre means), not a contrast with non-training controls; I2 = 0 %; 111 studies, 158 groups, 1927 participants; of the covariates only sets per workout explained the variance, negatively; trained = more than one year of resistance-training experience`
- S1.10 FIX. The category estimates are of fat-free mass only ("Performing a more detailed analysis of the training status on FFM"), not of whole-body muscle mass, and are pre-post within-group changes; "rests on a handful of groups" is not in the record.
  - `parameter` -> `fat-free-mass gain from resistance training by training-experience category (no clean training-age gradient)`
  - `range` -> `FFM groups only; pre-post within-group changes; categories coded by reported experience (sedentary, active without resistance training, up to 1, 2 and 3 years, 4 years or more); the experienced categories have wide intervals and the 4 y+ estimate has I2 = 41 %`
- S1.11 PASS. Ahtiainen 2003 abstract: +20.9 % force and +5.6 % CSA (non-strength athletes) vs +3.9 % and -1.8 % (strength athletes), 21 wk, MRI.
- S1.12 FIX. The numbers are in the abstract, but the "-1.3" is a change in body-fat percentage, which the cell's "body fat -1.3 +/- 2.5 %" leaves ambiguous; "DXA every March" holds only for the four-year subset (the one-year series ran March, May, July, March); "athletes arrived with prior high-school training" is not in the record.
  - `value` -> `one year: lean mass +2.8 +/- 2.8 kg, body-fat percentage -1.3 +/- 2.5 (n = 57); four years: lean mass +4.3 +/- 3.0 kg, weight +6.6 +/- 4.1 kg (n = 13)`
  - `range` -> `DXA; the one-year change ran from March to the following March with May and July reads between, and the four-year subset was read every March; mean +/- SD; already well-trained Division I players, not a curve from untrained`
- S1.13 PASS. Stodden 2010 abstract: most significant improvements in year 1, years 2-4 inconsistent, bench press improved through 4 years; 84 Division IA players.
- S1.14 PASS. Hakkinen 1988 abstract: fibre area +5.9 % NS, isometric force +4.9 % NS, total lifting result +2.8 % (p < 0.05), 9 elite lifters.
- S1.15 PASS. Page dated 19 June 2009, updated 7 June 2020; the "Rates of Muscular Gain in Males" table reads 1.5-2 lb/month and 20-25 lb (year 1), 1 lb and 10-12 lb, 0.5 lb and 5-6 lb, 2-3 lb (year 4); 40-50 lb total; women roughly half; older individuals slower; "averages ... assumptions about proper training and nutrition".
- S1.16 PASS. The page's Aragon/Helms table reads 1-1.5, 0.5-1 and 0.25-0.5 % bodyweight/month; women 0.5-0.75, 0.25-0.5, at most 0.25 %. Status `unverified` is honest: the primary statement by Aragon or Helms was not read.
- S1.17 PASS. Ogasawara 2013 abstract: 14 men randomly divided, 75 % 1RM 3 x 10, 3 d/wk; CTR's rate of gain fell after the first 6 wk; second retraining cycle higher than CTR; overall similar. RCT is right.
- S1.18 PASS. Ogasawara 2011 abstract: n = 15, no significant decrease after 3 wk detraining, retraining gains similar to initial, 15-wk totals similar. Allocation is "divided", not stated random, so EXP is right.
- S1.19 PASS. Cumming 2024 abstract: myonuclei +13 +/- 17 % and +33 +/- 23 %, fCSA +30 +/- 43 % (P = 0.069), 33 % more type 2 myonuclei than control after detraining, larger type 2 fCSA after retraining (P = 0.035) with no difference in delta; physiological benefit undetermined.
- S1.20 PASS. Horwath 2025 abstract: 6 patients (5 men, 1 woman), 43 +/- 15 y; fibre volume -13 % (P = 0.077), volume per myonucleus -20 % (P = 0.008), type I and II CSA unchanged, myonuclei not lost.
- S1.21 PASS. Gundersen 2016 abstract: faster regain in previously large fibres, myonuclei stable for at least 15 years and might be permanent, harder to recruit in the elderly.
- S1.22 FIX. The +13 % myonuclear accretion was not significant (p = 0.057); the cell states it as a finding.
  - `value` -> `juvenile training: fibre CSA +21 % (p = 0.0035), myonuclei +13 % (p = 0.057, not significant); after 10 wk detraining CSA matched naive controls but myonuclei stayed +15 % (p = 0.033); 2 wk adult climbing: +19 % CSA in previously trained rats vs little effect in naive; surgical overload +20 % vs no significant increase in naive`
- S1.23 PASS. Kubo 2010 abstract: strength +40.5 % at 3 months, CSA significant only at the end of training, CSA back at 1 month and stiffness at 2 months of detraining, strength and activation unchanged; n = 8.
- S1.24 PASS. Narici 1989 abstract: CSA +8.5 +/- 1.4 %, MVC +20.8 +/- 5.4 % (mean +/- SEM, n = 4), detraining time course similar to training.
- S1.25 PASS. Hortobagyi 1993 abstract: bench -1.7 %, squat -0.9 %, isometric -7 % (NS); eccentric -12 % (P < 0.05); type II area -6.4 % (P < 0.05), type I unchanged; 12 power athletes, 14 d.
- S1.26 FIX. The randomisation was whey vs carbohydrate; the detraining reading is a within-group change over time, which the range cell must say so the RCT grade is not read as a randomised detraining contrast.
  - `range` -> `n = 20, randomised to 25 g whey or carbohydrate; 4 wk training, 2 wk detraining, 4 wk retraining; the detraining reading is a within-group change over time, not a randomised contrast; lean mass by DXA, rectus femoris CSA by ultrasound`
- S1.27 FIX. Every subgroup in Zhang 2026 compares post-detraining with the pre-intervention baseline (the Methods: "comparing pre-intervention ... to post-detraining"), not with a control arm; "residual benefit" must be read that way.
  - `range` -> `86 RCTs, n = 5670; exercise of any kind, not only resistance training; each subgroup compares post-detraining with the pre-intervention baseline, not with a non-exercising control; read from the abstract`
- S1.28 PASS. Murphy 2022 abstract: ES -0.57 (p = 0.02) for lean mass, -0.31 (p = 0.28) for strength, about 500 kcal/day deficit prevented lean gain in the pooled meta-regression.
- S1.29 PASS. Helms 2023 abstract: BF10 9.9 and 14.5 (bench), 4.2 (skinfolds vs maintenance), 14.3 / R2 0.49 and 1.4 / R2 0.24; 17 completers of 21; the full text confirms the at-least-one-year resistance-training inclusion.
- S1.30 PASS. Garthe 2013 abstract: 3585 +/- 601 vs 2964 +/- 884 kcal, BW +3.9 +/- 0.6 vs +1.5 +/- 0.4 %, FM +15 +/- 4 vs +3 +/- 3 %, LBM gain not different, 1RM +6-12 %; randomised, n = 21 + 18.
- S1.31 PASS. Rozenek 2002 abstract: 2010 kcal supplement, BM +3.1 +/- 3.1 and +3.1 +/- 2.2 kg, FFM +2.9 +/- 3.4 and +3.4 +/- 2.5 kg, significant vs control, strength not different; 73 men randomly divided.
- S1.32 PASS. Iraki 2019 abstract and Table 1: 10-20 % surplus, 0.25-0.5 %/wk for novice/intermediate, advanced more conservative, protein 1.6-2.2 g/kg/day.
- S1.33 PASS. Slater 2019 abstract: the specific surplus is unknown, anabolic stimulus from a surplus even without training, the sweet spot never validated in a resistance-training population.
- S1.34 PASS (open row; empty grade, value and citation; the gap is honestly named).
- S1.35 PASS (open row).
- S1.36 PASS (open row; note for the controller: Psilander 2019 is already in the register as S0617 and S0078).

## Count

36 rows: 30 PASS, 6 FIX (S1.9, S1.10, S1.12, S1.22, S1.26, S1.27), 0 DROP.
