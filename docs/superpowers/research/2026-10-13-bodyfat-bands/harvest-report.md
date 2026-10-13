# Body-fat band harvest (plan 11b, 2026-10-13)

> Minted 2026-10-13 as S1904-S1912 (provisional S1.1-S1.9). An Opus review corrected the cells before the mint: S1909's intercept (-1.7), S1904/S1905's population (671 African American and white adults, Table 4), the S1904/S1905 range wording, S1908's n contradiction, S1909's population scope and its DXA CV of 3-4 %; the register's cells are authoritative where this report differs. The men's 6 % Very-lean edge is a game choice within S1910 (ruling T2-10).

Harvester: claude-opus-5-5. Part file: `bodyfat-science-part.tsv`, 9 rows, provisional S1.1-S1.9; `science_delta.py apply --dry-run` mints them S1904-S1912 against the register as of this harvest.

## plan-11b bodyfat harvest (2026-10-13)

### How each record was resolved

- **Gallagher 2000** (S1.1-S1.6): the metadata and abstract come from Europe PMC (pmid 10966886, doi 10.1093/ajcn/72.3.694, title, authors, 72(3):694-701). The tables come from a full-text PDF of the published article, the AJCN copy stamped "Downloaded from ajcn.nutrition.org by guest on January 28, 2016", hosted at `musclesound-public.s3.amazonaws.com/support/Am+J+Clin+Nutr-2000-Gallagher-694-701+(1).pdf`. The publisher pages (OUP, ScienceDirect, ajcn.nutrition.org) returned 403/404. I read Table 3 from a rendered page image (p 699), because the text layer scrambled the men's columns, and Tables 4 and 5 from the text layer. I checked Table 4 against Equation 5 by hand: women at age 30 give 21.0 / 33.0 / 39.0 and men 8.1 / 19.6 / 25.0. Tables 5 and 6-7 match the same way.
- **Friedl 1994** (S1.7): read from the Europe PMC abstract (pmid 8002550); every number in the row is in the abstract.
- **Hulmi 2016** (S1.8): read from the Europe PMC abstract and the PMC full text, PMC5222856, Results § body composition and the Discussion.
- **ACE chart** (S1.9): only secondary copies were found, for example a TomTom manual page and other reproductions. No ACE primary record or method was located, so the row is `unverified` and should ship nothing.

### Row evidence

| Row | Where in the record | Content |
|---|---|---|
| S1.1 | Table 4 (women), p 699; Equation 5, p 697 | Combined African American + white, 4C. Women 20-39 y: 21 / 33 / 39 %. 40-59 y: 23 / 34 / 40 %. 60-79 y: 24 / 36 / 42 %. Ages centred on 30, 50 and 70 y. |
| S1.2 | Table 4 (men) | Men 20-39 y: 8 / 20 / 25 %. 40-59 y: 11 / 22 / 28 %. 60-79 y: 13 / 25 / 30 %. |
| S1.3 | Table 3 (women), p 699; Equation 4 | Order is African American / Asian / white. 20-39 y at BMI <18.5: 20/25/21; at >=25: 32/35/33; at >=30: 38/40/39. 40-59 y: 21/25/23, 34/36/35, 39/41/41. 60-79 y: 23/26/25, 35/36/38, 41/41/43. |
| S1.4 | Table 3 (men) | Order is African American / Asian / white. 20-39 y: 8/13/8, 20/23/21, 26/28/26. 40-59 y: 9/13/11, 22/24/23, 27/29/29. 60-79 y: 11/14/13, 23/24/25, 29/29/31. |
| S1.5 | Table 5, p 700; Equations 6 (n 322, SEE 2.91) and 7 (n 633, SEE 3.49) | Asian women by age: 25/25/25, 35/35/36, 40/41/41. Asian men: 13/13/14, 23/24/24, 28/29/29. |
| S1.6 | Abstract (SEE 2.8-5.4); Equation 5 (SEE 4.98); Figure 3 legend (DXA = −1.7 + 1.06 x 4C, R 0.95, SEE 3.2); Results (4C 10/30/50 % -> DXA 8.9/30.1/51.3 %) | These are the prediction and method spreads. |
| S1.7 | Abstract | The male floor is 4-6 % (DXA), about 2.5 kg of fat. Start: 14.3 % (6-26). End: 5.8 +/- 1.8 % (4-11). |
| S1.8 | Results and Discussion, PMC5222856 | DXA fell from 23.1 +/- 5.6 % to 12.7 +/- 4.0 %. 6 of 27 women were below 10 %. Hormones fell and menstrual irregularities rose. The authors cite "12-14 %" as a suggested female minimum from Meyer et al 2013, which I did not resolve. |
| S1.9 | Secondary copies only | ACE categories, men / women: essential 2-5 / 10-13; athletes 6-13 / 14-20; fitness 14-17 / 21-24; average 18-24 / 25-31; obese >=25 / >=32. |

**Central value.** Use Table 4 (S1.1, S1.2), the combined African American + white table the authors present "for practical purposes". Take the 20-39 y column unless the mod tracks age. The Asian columns (S1.3-S1.5) run 2-5 points higher at BMI 18.5.

The authors write that the BMI < 18.5 percentages "have large CIs and should be applied cautiously". Only 2.6 % of the men and 6.0 % of the women had a BMI below 18.5. The bottom of the Healthy band is therefore the weakest of the Gallagher cuts.

### Existing rows: reuse, not duplicate

- **S1051 (open)** asks for the "body-fat fraction from body weight (or BMI), age and sex". Gallagher's Equation 5 answers it directly, so I put it in no part row. The controller can settle S1051 instead:
  - **`--value`:** `%BF = 64.5 - 848 x (1/BMI) + 0.079 x age - 16.4 x sex + 0.05 x sex x age + 39.0 x sex x (1/BMI); sex = 1 male, 0 female`.
  - **`--range`:** `multiple R = 0.86, SEE = 4.98 % fat; 4C reference; BMI <= 35`.
  - **`--grade`:** COH.
  - **`--citation`:** as on S1.1.
  - **`--population`:** the Gallagher population, African American and white only.
  - **Where the signs come from:** the PDF text layer drops the minus signs. I fixed each sign by reproducing every Table 4 cell to within 0.5, which the signs above do.
- **S1167 (open)** asks for the essential-fat floor by sex; the plan ships 0.04 for men and 0.10 for women.
  - S1.7 (Friedl) answers the male half: 4-6 %, which supports BF_MIN = 0.04.
  - No resolvable female floor was found. S1.8 is a measured lean end (12.7 % DXA mean, with endocrine disruption), not an exhaustion floor.
  - I left S1167 for the controller. It could be settled for men only, or stay open.
- The mod's `K.body.BF_MIN = {0.04, 0.12}` is cited to S1051 in the code, but its 0.12 for women differs from Plan 5 ruling 13's 0.10 under S1167. See concerns.

### Proposed cut table (20-39 y, the panel's five words)

| Word | Men | Rests on | Women | Rests on |
|---|---|---|---|---|
| Very lean | < 6 % | gc: S1.7, the top of Friedl's 4-6 % floor | < 13 % | gc: S1.8 (12.7 % DXA mean at endocrine cost), rounded; S1.9's 10-13 essential band agrees but is unverified |
| Lean | 6 - 8 % | S1.7 to S1.2 | 13 - 21 % | gc lower edge; S1.1 upper edge |
| Healthy | 8 - 20 % | S1.2 (BMI 18.5 to 25) | 21 - 33 % | S1.1 (BMI 18.5 to 25) |
| High | 20 - 25 % | S1.2 (BMI 25 to 30) | 33 - 39 % | S1.1 (BMI 25 to 30) |
| Very high | >= 25 % | S1.2 (BMI 30) | >= 39 % | S1.1 (BMI 30) |

- **Age.** If the mod carries age, the 40-59 and 60-79 columns of S1.1 and S1.2 shift the three Gallagher cuts up by 1-5 points.
- **Very-lean / Lean cut, men (6 %).** This is gc in a weak sense: Friedl gives a range (4-6 %). 6 is the upper edge, chosen so that "Very lean" means at or near the floor. 5 is the alternative.
- **Men's Lean band.** It is only 2 points wide, 6-8 %, because Gallagher's BMI 18.5 male value is low. If that is too narrow for play, 5 % for the Very-lean cut is the gc alternative.

### Hysteresis evidence

- **Prediction error.** The SEE of predicting %BF from BMI, age and sex is 4.98 % fat for Equation 5, and 2.8-5.4 across the models (S1.6).
- **Method spread.** DXA against 4C has an SEE of 3.2 % fat.
- **No test-retest precision.** These are regression standard errors, not repeat-measurement precision; no repeat-measurement precision figure was harvested.
- **What a boundary band could rest on.** A band of a few tenths to about 1 % fat would be a game choice. The cited spreads (3-5 %) are larger than the Lean band itself, so they argue that the word is approximate, not for a band of that width.

## Concerns

1. **The brief's `source` string fails the schema.** It asks for `plan-11b bodyfat harvest (2026-10-13)`, but `sciencelib.SOURCE_RX` requires `<path>.md § <section>`. The rows use `.superpowers/sdd/2026-10-08-plan-11b-live-release/bodyfat-harvest-report.md § plan-11b bodyfat harvest (2026-10-13)`, which the dry run accepts.
2. **Gallagher's tables come from a third-party-hosted PDF of the article.** It is the publisher's own typeset PDF, but the publisher's site could not be reached. The abstract and metadata were resolved through Europe PMC.
3. **The women's floor is unresolved.**
   - Meyer et al 2013 (doi 10.1136/bjsports-2013-092561) is cited by Hulmi for "12-14 %". Its abstract does not contain the figure, so it was not minted.
   - ACE (S1.9) is unverified.
   - The mod's 0.12 for women and the Plan 5 ruling's 0.10 disagree with each other, and neither has a settled row.
4. **S1051 can be settled from Equation 5.** This replaces a game-choice split with a cited one, which may move the golden trace if the mod adopts it. That is the controller's ruling.
