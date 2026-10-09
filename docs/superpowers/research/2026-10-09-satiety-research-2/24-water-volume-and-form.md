# Satiety research 2, water, volume, energy density and food form harvest (2026-10-09)

The harvest report of Task 24 of Satiety research 2 (2026-10-09), followed by its citation review. The review's corrections stand over the report wherever they disagree; the rows in docs/reference/science.tsv carry the corrected cells.

# Task 24 report: water, volume, energy density and food form

Model: claude-opus-5-5. Part file: `24-science-part.tsv`, 43 rows. 40 are settled, 3 are open and none are unverified. On a scratch copy of the register, `science_delta.py apply --dry-run` and a full apply both passed (S24.1 → S1337 … S24.43 → S1379 on today's register). `science_check.py` on that copy, and `--part` on the part file, each read 0 findings.

Every settled citation was resolved through the Europe PMC REST API, and its title, first author and year were matched. Every number was read from the abstract. Where Europe PMC has the full text, it was read too: Robinson 2022 (PMC9026919) and Stribiţcaia 2020 (PMC7395742). No study cited here was already in the register (checked by pmid). The ones it already holds are S1229–S1235, S1250–S1253 and S1264–S1267. They are cited below by id and were not minted again.

## 1. Water drunk with or before a meal

| id | finding | grade | quality markers |
|---|---|---|---|
| S24.1 | Davy 2008: 500 mL 30 min before breakfast gave 500 vs 574 kcal (−13 %) | RCT | n = 24 obese adults aged about 61; crossover |
| S24.2 | Van Walleghen 2007: 30 min water preload. Young 892 vs 913 kcal (null). Older 682 vs 624 kcal (P = 0.02). Fullness rose in all | RCT | n = 29 young and 21 older |
| S24.3 | Dennis 2010: acute 498 vs 541 kcal at baseline, 480 vs 506 (NS) at 12 weeks. Weight loss about 2 kg greater | RCT | n = 48 aged 55–75; 12 weeks |
| S24.4 | Corney 2016: 568 mL drunk under 1 min before the meal gave 2551 vs 1967 kJ (−23 %) in young men | RCT | n = 14 |
| S24.5 | Jeong 2018: 300 mL before the meal 123.3 g, none 161.7 g, after the meal 163.3 g | RCT | n = 15, weak |
| S24.6 | Parretti 2015: −1.3 kg (95 % CI −2.4 to −0.1) at 12 weeks; adjusted −1.2 (−2.4 to 0.07) | RCT | n = 84 obese adults |
| S24.7 | Daniels & Popkin 2010: sugar-sweetened beverage vs water before a meal, total intake +7.8 % (−7.5 to 18.9); non-nutritive sweetener vs water −1.3 %; milk or juice +14.9 % | MA (SR) | averages, not pooled; "sparse, inconclusive" |
| S24.8 | open: no meta-analysis of pre-meal water | — | — |
| S24.9 | Himaya 1998: chunky soup > strained soup > vegetables with water, for both hunger and intake | RCT | n = 22 men; no magnitudes in the abstract |
| S24.10 | Flood & Rolls 2007: soup gave −20 % meal energy (134 kcal); the soup's form had no effect | RCT | n = 60 |
| S24.11 | Clegg 2013: gastric-emptying t½ smooth soup > chunky > solid; fullness higher after smooth soup | RCT | n = 12 |
| S24.12 | Rolls 2004: low-energy-density salad −7 % / −12 %; high-energy-density salad +8 % / +17 % | RCT | n = 42 women |
| (S1231, existing) | Rolls 1999: soup 1209 kJ vs casserole with water 1657 kJ | RCT | n = 24 |
| (S1232, existing) | Marciani 2012: soup kept gastric volume up and lowered hunger | RCT | n = 22 / 18 |

**Verdict, pre-meal water.**
- **Best estimate.** A 375–568 mL water load cuts the next meal by about 8–13 % in older adults when drunk 30 min before (S24.1, S24.2). It cuts the meal by about 23 % in young men when drunk immediately before (S24.4). In young adults it does nothing when drunk 30 min before (S24.2).
- **Over time.** The effect attenuates over 12 weeks of habitual use (S24.3). Its chronic effect on weight is about 1–2 kg over 12 weeks (S24.3, S24.6). Water drunk after the meal does nothing (S24.5).
- **Certainty: low.** No meta-analysis exists (S24.8). The evidence is a handful of crossovers of 14–60 people. One group (Davy) supplies three of the trials, and the results are heterogeneous by age and timing.
- **Not supported by the better evidence.** "Water before meals sates everyone" fails: young adults show a null at 30 min.
- **How the pieces fit.** Water's fast emptying (t½ about 13 min, S1245) reconciles the timing results. After 30 min about 80 % has left the stomach, so only an immediate load is still distending the stomach at the meal.

**Verdict, water in food vs beside it.**
- **Best estimate.** Water bound into a food (soup, a low-energy-density first course) lowers the next meal by about 12–27 %: S1231's 27 %, S24.10's 20 % and S24.12's 12 %. The same water drunk beside the food does nothing (S1231). The direction is replicated by Himaya (S24.9). The mechanism is gastric retention (S1232, S24.11).
- **Certainty: moderate.** It rests on several independent RCTs from two labs. Magnitudes vary by preload size and timing, and there is no pooled estimate.
- **What does not matter.** The soup's form, chunky or puréed, does not matter (S24.10). Himaya's chunky-soup advantage is the one weak dissent and comes without magnitudes.

## 2. Energy density

| id | finding | grade | quality markers |
|---|---|---|---|
| (S1230, existing) | Robinson 2022, daily intake: SMD −1.002 | MA | 31 studies, 90 effects, I² 92.1 % |
| S24.13 | Robinson 2022, all foods manipulated: −855.85 kcal/d (I² 97.4 %); outliers removed −709.01. Slope b −1510.70 per kcal/g, outliers removed −309.31 (−115.91 to −502.71) | MA | 8 studies; custom risk-of-bias checklist, which did not predict effects; no GRADE |
| S24.14 | Robinson 2022, compensation: non-manipulated foods only +35 kcal (NS). 77 % of a served-kcal difference reaches daily intake (b −0.774) | MA | 7 studies, 16 effects |
| S24.15 | Rouhani 2017: at equal energy, a low-energy-density preload lowers the next meal (CI −138.71, −57.33). At equal weight it raises it (CI 9.72, 56.19). Overall null | MA | 39 studies; "remarkable" heterogeneity; CIs only |
| S24.16 | Bell 1998: people eat equal weight, so energy tracks density (1800 / 1519 / 1376 kcal); hunger equal | RCT | n = 18 women, 2-day blocks |
| S24.17 | Rolls 2006: −25 % energy density gave −24 % intake (575 kcal/d); −25 % portion gave −10 %. The effects are additive and hunger is unchanged | RCT | n = 24 women, 2-day blocks |
| (S1229, existing) | Rolls 1999: 4.4 vs 6.7 kJ/g gave −16 %; fat itself null | RCT | n = 34 |

**Verdict.**
- **Best estimate.** People eat a roughly constant weight of food, so intake scales almost 1:1 with energy density over 1–4 days (S24.16, S24.17). About 77 % of a served-energy difference survives to the daily total, with negligible compensation later (S24.14, +35 kcal NS).
- **Per kcal/g.** The slope is −309 kcal/d per kcal/g once outliers are removed (S24.13), with a wide CI. The raw −1510 is driven by outliers.
- **Certainty: moderate.** The direction is high-certainty: an MA of 31 studies, consistent across designs. The size is low-certainty: I² is 85–100 %, the studies are short laboratory ones, and the weight effect is NS at −0.7 kg (S1230).
- **Not supported by the better evidence.** The idea that low-density meals are compensated at the next meal is not supported (S24.14, S24.36 Bolhuis, S1231 "no compensation at dinner"). Rouhani's overall null comes from mixing equal-weight and equal-energy designs, and its subgroups agree with Robinson.

## 3. Liquid against solid calories; viscosity; semi-solids

| id | finding | grade | quality markers |
|---|---|---|---|
| S24.18 | Stribiţcaia 2020, form. Hunger −5.00 mm; solid vs liquid −6.58 mm (I² 39 %); semi-solid vs liquid null. Fullness null (I² 91 %). Intake −26.2 kcal NS; solid vs liquid −55.5 kcal (p = 0.05) | MA | 16 / 12 / 12 subgroups, 651 participants; 1 of 29 studies at low risk of bias; no GRADE |
| S24.19 | Stribiţcaia 2020, viscosity. Hunger −2.10 mm (NS). Fullness +5.20 mm. Intake −66.7 kcal (NS) | MA | 9–11 subgroups, 155–191 participants; I² 59–76 % |
| S24.20 | Cassady 2012: perceived gastric liquid gave 2311 vs 1897 kcal/d | RCT | n = 52; 4-arm crossover |
| S24.21 | Flood-Obbagy 2009: whole apple −15 % (187 kcal) and below applesauce and juice; fibre added to juice did nothing | RCT | n = 58 |
| S24.22 | Stull 2008: liquid meal replacement gave +13.4 % at the next meal and higher hunger AUC | RCT | n = 24 aged 50–80 |
| S24.23 | Zijlstra 2008: liquid 809 g vs semi-solid 566 g (+30 %). With the eating rate fixed the gap is 12 % (NS) | RCT | n = 108 / 49 |
| S24.24 | Mattes & Rothacker 2001: a thick shake lowers hunger longer, with no change in the time to the next meal, its size or 24-h intake | RCT | n = 84 |
| (S1264–S1267, existing) | DiMeglio 2000; Mourao 2007 (+12–19 %/d on beverage days); Almiron-Roig 2013 meta-regression; 2003 review "inconclusive" | RCT / MA / TXT | |

**Verdict.**
- **Liquid vs solid, best estimate.** A beverage is modestly less satiating than its matched solid: hunger about 5–7 mm higher on a 100 mm scale (S24.18). The acute next-meal effect is at most about 55 kcal (S24.18). Daily intake is about 12–20 % higher on beverage days (S1265, S24.20), and liquid sugar is not compensated over weeks (S1264, single small trial).
- **Liquid vs solid, certainty: low to moderate.** The MA is consistent on hunger, but its intake effect is borderline. Risk of bias is mostly unclear, and Cassady shows part of the effect is cognitive (perceived form).
- **Viscosity, best estimate.** Thicker means a little more fullness (+5.2 mm) but no reliable effect on hunger or intake (S24.19, S24.24). Certainty is moderate for the null on behaviour.
- **Semi-solids.** They are not different from liquids in the MA (S24.18). Zijlstra's +30 % is largely an eating-rate effect (S24.23).
- **Not supported by the better evidence.** The common claim that "thick drinks / viscous foods suppress appetite" is supported only on a fullness scale, not on intake or the time to the next meal.

## 4. Gastric distension and volume; aerated foods

| id | finding | grade | quality markers |
|---|---|---|---|
| S24.25 | Geliebter, Westreich & Gage 1988: a balloon of 400 mL or more reduces lunch intake | RCT | n = 8 (4 lean, 4 obese); random order |
| S24.26 | Oesch 2006: transient fundus distension of 400–800 mL does not reduce intake; hunger falls only at 600–800 mL | RCT | n = 24 men; double-blind |
| S24.27 | Rolls 2000: air-whipped shake at 600 vs 300 mL, same mass and energy, gave −12 % lunch intake | RCT | n = 28 men |
| S24.28 | Osterholt 2007: more-aerated snack gave −21 % energy (70 kcal) despite +73 % volume eaten | RCT | n = 28 |
| S24.29 | Murray 2015: foams (490 mL vs 140 mL, 110 kcal) gave a larger gastric volume (MRI) and lower hunger; return to baseline 197 vs 248 min (less-stable vs stable foam) | RCT | n = 18 men |
| (S1233, S1250–S1253, existing) | Volume at constant energy (Rolls 1998); water-load satiation of 428 mL and maximum of 734 mL; nutrient drink about 1 L; balloon about 1.1 L | RCT / COH | |

**Verdict.**
- **Best estimate.** Gastric volume present during and after the meal sates. A sustained load of 400 mL or more cuts intake (S24.25). Doubling a preload's volume with air, at constant mass and energy, cuts the next meal by about 12 % (S24.27, S1233 by water). A transient pre-meal distension that is removed before eating does not (S24.26).
- **Certainty: low to moderate.** The direction holds across three labs. The trials are small, and the balloon evidence (n = 8 against n = 24) disagrees on whether pure distension alone moves intake.
- **Where the weight falls.** The weight favours "volume that stays in the stomach through the meal acts". Oesch's balloon was deflated, while Geliebter's, the foams and the shakes stayed.
- **Volume, not mass.** Air raises volume without mass (S24.27, S24.28, S24.29), which a mass-based model cannot see.

## 5. Oral processing

| id | finding | grade | quality markers |
|---|---|---|---|
| S24.30 | Robinson 2014: slower eating gives lower intake, SMD 0.45 (0.25–0.65). No effect on hunger at the end of the meal or up to 3.5 h | MA | 22 studies; large heterogeneity |
| S24.31 | Krop 2018: chewing-related oral processing; intake ES −0.28 (−0.36 to −0.19), hunger ES −0.20 (−0.30 to −0.11) | MA | 40 studies, 70 subgroups |
| S24.32 | Miquel-Kergoat 2015: hunger −2.31 VAS points; chewing cut intake in 10 of 16 trials | MA | I² 93.4 %, publication bias |
| S24.33 | Li 2011: 40 vs 15 chews gave −11.9 % | RCT | n = 30 men |
| S24.34 | Zhu & Hollis 2014: 150 % / 200 % chews gave −9.5 % / −14.8 %; appetite unchanged | RCT | n = 45 |
| S24.35 | Zijlstra 2009: small vs large bites gave 313–382 vs 432–476 g; a longer oral processing time gave less | RCT | n = 22 |
| S24.36 | Bolhuis 2014: hard vs soft foods gave −13 % at lunch, not compensated at dinner | RCT | n = 50 |
| S24.37 | Andrade 2008: slow 579 vs quick 646 kcal; slow eaters drank more water | RCT | n = 30 women |
| S24.38 | Andrade 2012: with water fixed, no intake difference; hunger lower at 1 h | RCT | n = 30 women |

**Verdict.**
- **Best estimate.** Slower eating, more chews, smaller bites and harder texture reduce the size of an ad-libitum meal by about 10–15 % (SMD about 0.3–0.45; S24.30, S24.31, S24.33–S24.36). They barely move hunger afterwards (Robinson: null up to 3.5 h; Krop ES −0.20; Miquel −2.3 mm).
- **Certainty.** Moderate for satiation (meal size), from two independent MAs agreeing in direction. Low for any post-meal satiety effect.
- **Not supported by the better evidence.** "Eating slowly keeps you full longer" is not supported. Part of the slow-eating effect may be extra water drunk at the meal (S24.38 against S24.37).

## 6. Food temperature

| id | finding | grade | quality markers |
|---|---|---|---|
| S24.39 | Sun 1988: a cold drink empties more slowly at first; warm does not differ; the stomach is back at body temperature in 20–30 min | EXP | n = 6; mechanism only |
| S24.40 | Mishima 2009: at 60 °C the lag phase is shorter, with no change in t½ | EXP | n = 25 + 25; mechanism only |
| S24.41 | open: no controlled trial of serving temperature with an intake outcome | — | — |

**Verdict.** There is no behavioural evidence. The gastric effects are transient (20–30 min) and inconsistent: hot speeds the lag phase, cold slows initial emptying. Certainty is very low.
- **Not minted.** Hamid 2024 (pmid 39176010, n = 13) reports higher GLP-1 and CCK after hot meals, correlated with recalled intake. It is mechanism-only with a recall outcome.
- **Not minted.** Langeveld 2016 (ambient cold, no intake change) belongs to the thermal and exercise harvest rather than to food temperature, and S1316 already covers it.

## 7. Thirst against hunger confusion

| id | finding | grade | quality markers |
|---|---|---|---|
| S24.42 | McKiernan 2009: thirst vs drinking r = 0.03; hunger vs intake r = 0.30; 75 % of fluid is drunk around meals | COH | n = 50, 7 days hourly |
| S24.43 | open: no experimental test that thirst is misread as hunger | — | — |

**Verdict.** The popular claim that "thirst is mistaken for hunger" has no experimental support located. The one measured observation is that both sensations are loosely coupled to intake (S24.42). Mattes 2010 (narrative, pmid 20060847) says the same and was not minted. Certainty is very low, and there is nothing to model.

## 8. What the evidence says about the current model (spec § 5b)

### Supported

1. **Liquid lane and `LIQUID_WEIGHT` 0.2.** A drink's water counts at a fifth in satiety mass and empties fast. This is supported by S1231, the 30-min young-adult null (S24.2), Jeong's null for water after the meal (S24.5), and the fast emptying of water (S1245).
   - Corney (S24.4) argues the weight is too low for water drunk immediately before eating: −23 % intake.
   - Worked through the model: 568 mL × 0.2 = 114 g. That gives F + 0.156 against 730 g, so Z rises by about 0.094 through FULL_WEIGHT 0.6, and under the spec's intake mapping intake falls about 9 %.
   - The model therefore under-reads Corney by about 2.5×. It sits near the older-adult 30-min effect (−8.5 to −13 %, S24.1 and S24.2), although that effect needs most of the water already emptied, which the model reads as near zero.
   - Net: the 0.2 is a defensible middle. No change is recommended, because the age and timing dependence is low-certainty and the game has no age.
2. **Food water stays with the food** (solid lane). Soups and low-energy-density first courses sate by their whole mass (S1231, S24.9, S24.10, S24.12). Soup form does not matter (S24.10), and the model treats chunky and puréed soup alike. In game terms, soups, stews and salads, whose vectors carry high water grams, sate more per kcal through F. That is correct.
3. **Energy density through fullness.**
   - The spec's 31 % fewer kcal to the same hunger at 1.05 vs 1.6 kcal/g is an elasticity of about 0.9.
   - That matches Rolls 2006 (−25 % density gave −24 % intake, about 0.96) and Bell 1998 (equal weight eaten).
   - It sits inside Robinson 2022's 77 % pass-through (S24.14).
   - No compensation at the next meal (S24.14, S24.36) is consistent with the spec's "time to the request is unchanged".
4. **Viscosity, temperature and eating rate left neutral.** None of them moves intake or later hunger reliably: S24.19, S24.24, S24.30, S24.38, S24.39–S24.41. Neutral under rule 5 is the evidence-weighted choice.
5. **Capacity.** Comfortable capacity of about 430 g and a soft cap of about 730 g (ruling 11c-8) are consistent with Geliebter's 400 mL intake threshold (S24.25). Oesch's null (S24.26) applies to a deflated balloon, not to retained food.
6. **Thirst and hunger independent.** No evidence links them (S24.42, S24.43).

### Argued against, or left out

1. **Volume at equal mass (air).**
   - Rolls 2000 (S24.27, −12 % for 2× volume), Osterholt (S24.28, −21 %) and Murray (S24.29, larger gastric volume and lower hunger) show that volume, not mass, distends. The model reads mass at density 1, so it gives zero effect.
   - Size: moderate, about 12–21 % of the next intake for a doubled volume. Certainty: low to moderate (three RCTs, n = 18–28).
   - Game terms: it matters only for the few aerated items (popcorn, puffed or crisp snacks, whipped cream).
   - Recommended: a per-item volume factor, read from the item's data, that scales its contribution to the satiety mass. A density value would have to be sourced per item. This is low priority, and it should be named as a limitation if skipped.
2. **Liquid vs solid calories beyond water.**
   - The model already discounts a drink's water. A drink's kcal still feed P at full weight, so a juice or milk sates through P almost like the matched solid, with only the fullness term reduced.
   - The evidence for an extra liquid-kcal penalty is low certainty: hunger +5–7 mm, next meal +55 kcal borderline (S24.18), daily intake +12–20 % (S1265, S24.20).
   - **Worked example: apple against juice.** The present structure already separates them by mass.
     - The model reads apple at F + 0.36 × 0.6.
     - It reads juice at F + 0.07 × 0.6.
     - That plausibly covers Flood-Obbagy's ranking (S24.21).
   - Neutral on the kcal side remains justified (ruling 11c-7 territory). The limitation string should say so.
3. **Oral processing and eating rate** move meal size by about 10–15 %, which is satiation, but not hunger afterwards. The model governs post-meal hunger, and the player chooses how much to eat, so nothing is lost. Any "hard food / slow eat" bonus would contradict Robinson 2014's null on hunger.
4. **Pre-meal water timing and age.** The real effect depends on age (larger in older people) and on timing: water drunk 30 min ahead is mostly gone, while water drunk immediately before still acts. Neither dependence is modelled. The game has no age, and the liquid lane's fast emptying already gives the timing shape, so no change is recommended.

## 9. Slug requests and supersede candidates

- **Slugs:** none requested. Water-preload intake outcomes are filed under `satiety`, gastric mechanism rows under `digestion`, daily energy-density intake under `energy` (following S1230), and Parretti's weight outcome under `body-composition`.
- **Supersede candidates:** none. No existing row is contradicted.
  - S1231 is replicated in direction (S24.9, S24.10).
  - S1230 is extended, not contradicted (S24.13, S24.14).
  - S1253 (Geliebter 1988, Physiol Behav) is a different record from S24.25 (Geliebter, Westreich & Gage 1988, Am J Clin Nutr). Both stand.

## 10. Concerns

- **The source cell.** harvest-common.md says it reads "Satiety research 2, <topic> harvest (2026-10-09)". `sciencelib.SOURCE_RX` requires `<path>.md § …`, so the literal form fails validation. I used `.superpowers/sdd/2026-10-09-satiety-research-2/harvest-topics.md § Task 24, Satiety research 2, water, volume, energy density and food form harvest (2026-10-09)`. The controller may want one form across all seven parts.
- **Rouhani 2017 (S24.15).** The abstract gives only CIs, with no point estimates or units. The row says so, and the full text was not available.
- **Stribiţcaia 2020 (S24.18, S24.19).** The abstract and the Results disagree on the hunger estimate (−4.97 vs −5.00 mm) and on the viscosity hunger CI's upper bound (1.18 vs 0.18). The rows carry the Results' figures and name the discrepancy.
- **Miquel-Kergoat 2015 (S24.32).** Its CI is printed as [−4.67, −1.38] around −2.31. It is quoted as printed.
- **Weak rows.** Several key rows are single small crossovers: S24.4 (n = 14), S24.5 (n = 15), S24.25 (n = 8) and S24.39 (n = 6). Each carries its n in the range or the population cell.
- **Provisional ids.** The dry-run's S1337–S1379 mapping assumes today's register. With seven parallel parts, the controller's apply order sets the real ids.
- **Europe PMC throttling.** It returned HTTP 503 under parallel load, and the retries succeeded. No number was taken from a secondary source.

## Review corrections (2026-10-09, 24-review.md)

The citation review's corrections stand over the text above wherever they disagree; read 24-review.md items 4-8 and its residuals. In short: pre-meal water in older adults is 375-500 mL (Corney's 568 mL is young men); Dennis 2010's week-12 null is in the pooled sample of both arms and does not show habituation; eating rate does move meal size (S24.30) though not later hunger, and the player governs it; Osterholt's 21 % is intake of the aerated food itself (satiation), the next-meal effect of doubled volume is about 12 % (S24.27); delete Bolhuis (S24.36) from the energy-density verdict; Robinson 2022 was already S1230 (S24.13 and S24.14 carry values it does not); the model's -9 % for a 568 mL glass holds only from an empty stomach and ignores emptying during the meal; Cassady (S24.20) is the cognitive component of liquid calories (+21.8 % on preloads perceived as liquid), not a beverage-day effect; S24.2's age dependence rests on within-group tests with no reported interaction.

---

# Citation review

Model: claude-opus-5-5

# Task 24 citation review (water, volume, energy density and food form)

FAIL

All 40 settled rows were resolved by pmid through Europe PMC (core) and PubMed efetch. Every title, first author, year, journal, volume and pages, doi and pmid matches. The full texts of Robinson 2022 (PMC9026919), Stribitcaia 2020 (PMC7395742) and Dennis 2010 (PMC2859815, through the NCBI BioC route) were read. Every grade fits science.md: Daniels 2010 is a systematic review, so MA; the crossovers are RCT; Sun 1988 and Mishima 2009 are EXP; McKiernan 2009 is COH. `science_check.py --part` reads 0. Every other row's value, range and population matches its abstract.

## Defects

1. **S24.3, the `parameter` and `range` cells: a pooled-sample result read as habituation.**
   - What the source does: Dennis 2010 analysed the 12-week test meals in the pooled sample of both arms ("In the pooled sample, mean ad libitum breakfast meal EI was lower in the WP condition ... at baseline ... but not at week 12"). It also found "no significant group by condition differences ... in breakfast meal EI".
   - Why the cell is wrong: only the water arm drank water before meals. The week-12 null therefore cannot be read as attenuation by "12 weeks of habitual pre-meal water".
   - Corrected `parameter`: `ad libitum breakfast energy intake after a 500 mL water preload vs no preload, at baseline and at week 12 of a 12-week hypocaloric-diet trial, in the pooled sample of both arms (the reading that the acute effect was not significant at week 12; not a habituation effect, since only the water arm drank water before meals and no group-by-condition difference was found)`
   - Corrected `range`: `12-week randomised trial of a hypocaloric diet with or without 500 mL water before each main meal; test meals analysed in the pooled sample of both arms, with no significant group-by-condition difference in breakfast energy intake in absolute or relative terms; weight loss about 2 kg greater in the water group (beta -0.87 vs -0.60, a 44% greater decline); no certainty rating given`

2. **S24.14, the `value` cell: a rounded number and a missing subgroup qualifier.**
   - Rounded: the source gives 35.08 kcal (95% CI -28.32 to 98.48, p = .278, I2 = 95.15), not "35 kcal".
   - Unqualified: the source restricts b = -0.774 to "studies that did not manipulate energy density of all foods/meals". The cell gives it without that restriction.
   - Corrected `value`: `manipulated meals -330.78 kcal (95% CI -224.27 to -437.29, I2 = 100%), with intake at later non-manipulated foods up by a non-significant 35.08 kcal (95% CI -28.32 to 98.48, p = .278, I2 = 95.15) after the lower energy-density food; among studies not manipulating all foods, a 100 kcal difference in energy served predicted a 77 kcal difference in daily energy intake (b = -0.774, 95% CI -0.644 to -0.905)`

3. **S24.18, the `range` cell: the risk-of-bias wording is not the source's, and an abstract discrepancy is unnamed.**
   - Risk of bias: the cell says "1 study low risk, most unclear". The full text gives 1 study low, 25 medium and 3 high.
   - Unnamed discrepancy: the abstract prints the form-on-intake CI as (-61.72, -9.35) and calls it "a moderate effect". The Results give -61.7 to 9.4, p = 0.149. The row names the hunger discrepancies but not this one.
   - Corrected `range`: `29 studies reviewed; form pooled from 16 subgroups for hunger, 12 for fullness (263 participants) and 12 for intake (458 participants), 651 participants in all; risk of bias: 1 study low, 25 medium, 3 high; the abstract prints the intake CI as -61.72 to -9.35 and calls it a moderate effect, the Results -61.7 to 9.4 (p = 0.149); the authors advise cautious interpretation; read from the full text (PMC7395742); no GRADE rating given`

4. **Report § 1, the pre-meal water verdict: a dose mislabelled and the Dennis misreading carried forward.**
   - "A 375–568 mL water load cuts the next meal by about 8–13 % in older adults": the older-adult trials used 375–500 mL. The 568 mL load is Corney's, in young men.
   - "The effect attenuates over 12 weeks of habitual use (S24.3)": see defect 1.
   - Corrected: "A 375–500 mL water load drunk 30 min before cuts the next meal by about 8–13 % in older adults (S24.1, S24.2) … In Dennis's pooled sample the acute effect was no longer significant at week 12 (P = 0.069; S24.3). With no group-by-condition difference, the trial does not show habituation."

5. **Report § 8 "Supported" 4: the text contradicts S24.30.**
   - It says "None of them moves intake or later hunger reliably: S24.19, S24.24, S24.30 …". S24.30 is a significant intake effect (SMD 0.45, P < 0.0001).
   - Corrected: "None of them moves later hunger reliably (S24.19, S24.24, S24.30, S24.38, S24.39–S24.41). Eating rate does move meal size (S24.30), which the player governs (see 'Argued against' 3)."

6. **Report § 8 "Argued against" 1: satiation read as next-meal satiety.**
   - It says "about 12–21 % of the next intake for a doubled volume". Osterholt's 21 % (S24.28) is the ad-libitum intake of the aerated snack itself, which is satiation, at 0.45 against 1.00 kcal/mL (about 2.2x the volume). It is not the next meal. Only Rolls 2000's 12 % (S24.27) is a next-meal effect for doubled volume.
   - Corrected: "Size: about 12 % of the next meal for a doubled volume (S24.27), and 21 % less of the aerated food itself eaten at about 2.2x the volume (S24.28, satiation)."

7. **Report § 2 verdict: an off-topic row cited for energy-density compensation.**
   - It cites "S24.36 Bolhuis" against compensation for low-density meals. Bolhuis manipulated hardness, not energy density.
   - Fix: delete "S24.36 Bolhuis," from that sentence.

8. **Report introduction: a false statement about the register.**
   - "No study cited here was already in the register (checked by pmid)" is false. Robinson 2022 (pmid 35459185) is S1230, and S24.13 and S24.14 add new values from it, which is permitted.
   - Corrected: "Only Robinson 2022 (S1230) was already in the register; S24.13 and S24.14 carry values S1230 does not."

## Residuals

- **The −9 % model claim checks out.**
  - The arithmetic: 568 × 0.2 = 113.6 g; 113.6 / 730 = 0.156; 0.6 × 0.156 = 0.093. Hunger is scaled by about 0.907, so intake is −9.3 % under the spec's 650 × hunger / 0.25 mapping. The constants are read from NR_Kernel_Stomach.lua:188 and NR_Kernel_Satiety.lua:34-35. Against Corney's −22.9 % (2551 → 1967 kJ), that is a 2.5x under-read.
  - The claim holds only from an empty stomach (F = 0, and Pn unchanged because water carries no kcal), and it ignores emptying during the meal. The report should say so in one clause.
- **Report § 3, "12–20 % higher on beverage days (S1265, S24.20)".** Cassady's comparison is perceived-liquid against perceived-solid days, with every preload a gastric liquid. It reads +21.8 % (2311 vs 1897), so it does not sit inside 12–20 %. Recommended: cite Cassady as the cognitive component, not as a beverage-day effect.
- **S24.2's "age-dependent" reading.** It rests on separate within-age tests; the abstract reports no age × condition interaction. The parameter already frames it as a reading, which is acceptable, but the controller may wish to note it.
- **S24.18's value cell.** It cites "(abstract -4.97 mm)" but not the abstract's hunger CI (-8.13, -1.80). This is optional to add.
- **S24.39.** "In proportion to the intragastric temperature drop" paraphrases "significantly correlated with". Suggested wording: "correlated with the intragastric temperature difference (p < 0.01)".
- **Open row S24.8.** A PubMed title and abstract search on 2026-10-09, for water preload or pre-meal water with meta-analysis or systematic review, returned 0 records. The open row stands.
- **The source-cell form** raised in the report's concerns is the controller's call across all seven parts.
