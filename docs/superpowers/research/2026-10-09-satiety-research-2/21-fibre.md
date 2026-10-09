# Satiety research 2, fibre harvest (2026-10-09)

The harvest report of Task 21 of Satiety research 2 (2026-10-09), followed by its citation review. The review's corrections stand over the report wherever they disagree; the rows in docs/reference/science.tsv carry the corrected cells.

# Task 21 report: fibre and satiety (Satiety research 2)

Model: claude-opus-5-5. Status: DONE. Part file: `21-science-part.tsv`, 42 rows (S21.1–S21.42): 41 settled, 1 open, 0 unverified. `science_delta.py apply --dry-run` maps them to S1337–S1378. On a scratch copy of the register, both `science_check.py --register <copy>` and `--part` read 0 findings.

Every settled row was resolved against Europe PMC (title, first author, year), and every number comes from the abstract. Four papers were also read in full text from Europe PMC: Salleh 2019 (PMC6352252), Sanders 2021 (PMC8321865), Chambers 2015 (PMC4680171), and Flood-Obbagy 2009 (abstract only; the full text did not download).

These rows were already in the register and were not minted again: S0487 (Wanders, appetite 59% vs 14%), S1236 (Clark & Slavin), S1237 (Salleh per-type d), S1238 (Wolever), S1239 (Benini), S1240 (van Nieuwenhoven), S1226 (Holt) and S0486 (Reynolds, disease risk). S21.1 (Wanders) and S21.2 (Salleh) add values those rows do not carry.

## 1. Fibre type

| id | source | key value | grade | quality markers |
|---|---|---|---|---|
| S21.1 | Wanders 2011 | viscous fibre reduced acute energy intake (EI) in 69% of comparisons, against 30% for less viscous fibre; no dose-response | MA | vote count, 26 acute-EI comparisons; no pooled effect size |
| S21.2 | Salleh 2019 | d on EI: guar -0.90 (CI -1.83, 0.03); β-glucan -0.44 (-0.91, 0.04); alginate -0.42 (-0.84, 0.01); polydextrose -0.36 (-0.56, -0.17) | MA | high risk of bias; guar I² 95.8%, alginate I² 80.9%; 2–4 studies per type |
| S21.3 | Poutanen 2017 | 51 of 90 comparisons efficacious on ≥1 outcome; viscosity, molecular weight and fermentability did not predict efficacy; gel-forming fibre consistently efficacious (few comparisons) | MA | systematic search, 49 articles; no certainty rating |
| S21.4 | Machalias 2026 | cereal fibre gives favourable appetite ratings but limited EI effect; rye and oat stronger; wheat, barley, resistant starch and soluble corn fibre weak | MA | 48 crossovers; quality checklist; no pooled estimate |
| S21.5 | Warrilow 2019 | no fat-fibre interaction on satiety | MA | 12 studies |
| S21.6 | Ibarra 2015 | polydextrose: lunch EI SMD 0.35 (I² 0); lunch EI % = -0.67 × g; daily EI % = -0.35 × g; daily EI not significant in the meta-analysis itself | MA | 6 and 3 studies; authors are with the polydextrose supplier |
| S21.7 | Ibarra 2016 | polydextrose: only desire to eat, satiation period (SMD 0.24); no other VAS effect | MA | 7 studies |
| S21.8 | Liber 2013 | inulin-type fructans: 5 RCTs null on appetite, 11 RCTs null on EI | MA | 15 adult RCTs, n = 545 |
| S21.9 | Amini 2021 | resistant starch (RS): appetite AUC WMD -1.375 mm·min; ≥25 g -4.513; RS2 -4.808; RS1 null | MA | 4 studies, I² 94.5% |
| S21.10 | White 2020 | RS2 at 45 g/d for 12 wk: null on VAS, hormones, buffet EI and free-living EI | RCT | n = 59 analysed |
| S21.11 | Hughes 2022 | RS2 wheat: PYY up, GIP down, VAS null | RCT | n = 30; hormone readings are mechanism-only |
| S21.12 | Georg Jensen 2012 | alginate preload: low volume EI -8.0% (P = 0.040) with no VAS change; high volume VAS improved but EI -5.5% (ns) | RCT | n = 20, double-blind |
| S21.13 | Paxman 2008 | strong-gelling alginate for 7 d: -134.8 kcal/d (7%) | RCT | n = 68 crossover |
| S21.14 | Odunsi 2010 | alginate capsules for 10 d: null on gastric emptying (GE), gastric volume, satiation, intake and hormones | RCT | n = 48, allocation concealed |
| S21.15 | Pelkman 2007 | gelled alginate-pectin drink: -12% daily EI in low-restraint women only | RCT | n = 29 |
| S21.16 | Brum 2016 | psyllium 6.8 g: lower inter-meal hunger, higher fullness | RCT | sponsor-affiliated; no intake outcome |
| S21.17 | Samra 2007 | 33 g insoluble-fibre cereal: ad-lib intake 937 kcal against 1109 for a low-fibre cereal matched for weight and volume | RCT | small crossover, men only |

**Verdict.**
- **Best estimate.** Isolated fibre has a small acute effect on intake at best.
  - Polydextrose is the only fibre with a pooled acute EI effect whose CI excludes zero: d -0.36, about -0.67% of the next meal per gram.
  - The viscous fibres (guar, β-glucan, alginate) have medium point estimates, but every CI crosses zero, and the evidence base is 2–3 trials per fibre at high risk of bias.
  - Fructans (S21.8) and RS2 in the large trial (S21.10) are null on behaviour.
- **Certainty: low.** The reasons are high risk of bias, very few trials per fibre type, high I² where pooling exists, industry authorship on the positive polydextrose and psyllium reviews, and no GRADE rating on any acute review.
- **What lower-quality evidence claims and the best evidence does not support:**
  - "Viscous fibre reliably cuts intake." Wanders' 69% is a vote count, and Salleh's pooled CIs include zero.
  - "Fermentable fibre sates." The Cani 2006 pilot (n = 10) shows it, but Liber's 11 null RCTs do not.
  - "RS sates." The Amini MA shows it, from 4 studies at I² 94.5%; the larger White 2020 RCT is null.
- **Two disagreements are minted as paired settled rows.** The evidence weight favours the null side of each:
  - Amini against White: White is the larger and longer RCT, and it measured intake.
  - Georg Jensen and Paxman against Odunsi: Odunsi's design is stronger (allocation concealed, measured GE), although its capsules may gel less than a drink.
- **Gel-forming fibre is the one property that survives the pooled reviews** (S21.3, S21.22). Its evidence is thin.

## 2. Dose-response

| id | source | key value | grade |
|---|---|---|---|
| S21.6 | Ibarra 2015 | lunch EI % = -0.67 × polydextrose g (R² 0.80); daily EI % = -0.35 × g (R² 0.68) | MA |
| S21.9 | Amini 2021 | RS effect only clear at ≥25 g (WMD -4.513 against -0.799 mm·min below 25 g) | MA |
| S21.16 | Brum 2016 | psyllium 6.8 and 10.2 g better than 3.4 g | RCT |
| S21.29 | Sanders 2021 | whole-grain EI effect significant only above 90.1 g of whole grain | MA |
| S21.36 | Rahmani 2019 | β-glucan ≥4 g/d raised EI in a subgroup | MA |
| S21.42 | open | a pooled per-gram effect for viscous fibre in a whole-food meal | — |

**Verdict.**
- **Best estimate.** No per-gram effect is established for any food fibre.
  - Polydextrose's slope (-0.67%/g at the next meal, -0.35%/g over the day) is the only pooled one. It was fitted on 6 and 3 studies with industry authors, using a snack-delivered isolated fibre.
  - Wanders (S21.1) and Clark & Slavin (S1236) both found no dose-response across fibres.
- **Certainty: very low.**
- **Effect thresholds** sit around 25 g for resistant starch, 6.8 g for psyllium, and about 90 g of whole-grain food. Those are doses no single game food item carries as isolated fibre.

## 3. Mechanisms with a behavioural outcome

| id | source | mechanism | key value | grade |
|---|---|---|---|---|
| S21.20 | Marciani 2000 | viscosity | a 1000-fold viscosity range delays GE only slightly; satiety AUC rises with viscosity | RCT, n = 8 |
| S21.21 | Marciani 2001 | viscosity against nutrients, and distension | nutrients delay GE 46→76 min, viscosity less; fullness linear in gastric volume (R² 0.98) | RCT, n = 12 |
| S21.22 | Hoad 2004 | gel lumps, antral distension | GE unchanged, but fullness at the same gastric volume is higher for viscous meals; strong gel lowers hunger at 115 and 240 min | RCT, n = 12 |
| S21.23 | French & Read 1994 | GE against absorption | guar's delay in returning hunger correlates with GE for low-fat soup only; much larger and GE-independent with fat | RCT, n = 8 |
| S21.24 | Chambers 2015 | colonic propionate (SCFA, GLP-1, PYY) | -14% (162 kcal) buffet intake at 300 min; fewer people gaining ≥3% weight over 24 wk | RCT, n = 20 / 60 |
| S21.25 | Cani 2006 | fermentation over 2 wk | 16 g/d oligofructose: -5% daily EI | RCT pilot, n = 10 |
| S21.26 | Nilsson 2008 | second meal | breath H₂ correlates with next-morning satiety, r = 0.27 | RCT, n = 15 |
| S21.27 | Nilsson 2013 | second meal, 11–14 h | brown-bean dinner: next-morning hunger -15% (p = 0.05), PYY +51% | RCT, n = 16 |
| S21.32 | Haber 1977 | chewing and ingestion rate | juice eaten 11× faster than whole apple; at equal rate, juice < puree < apple for satiety | RCT, n = 10 |
| S21.11 | Hughes 2022 | hormones only | PYY up with no VAS change: mechanism-only | RCT |

**Verdict.**
- **Viscosity.** Viscosity sates more through how the stomach senses its volume (fullness per mL; S21.21, S21.22) than through delayed emptying (S21.20, S21.22; Wolever S1238 slowed GE without moving appetite).
- **Size of the effect.** It is a modest VAS effect on hunger and fullness. Its link to intake is unproven: S21.12's high-volume arm moved VAS but not intake.
- **Fermentation.** Its behavioural effects are plausible but rest on single small RCTs:
  - an engineered propionate ester (S21.24);
  - a 10-person pilot (S21.25);
  - a borderline p = 0.05 hunger reading the next morning (S21.27).
  - Liber's 11 null RCTs on fructans (S21.8) and White's null (S21.10) weigh against it.
- **Chewing and ingestion rate.** These matter, but they belong to food form (Task 24), not to fibre as a nutrient.
- **Certainty: low** for viscosity and distension, **very low** for fermentation.
- **Lower-quality evidence and the hormones.** Hormone readings (PYY, GLP-1) move more readily than behaviour (S21.11, S21.27, Chambers). The narrative reviews' "fibre → GLP-1/PYY → satiety" chain (for example Akhlaghi 2024, not minted) outruns the behavioural data.

## 4. Time course: acute against chronic

| id | source | key value | grade | quality |
|---|---|---|---|---|
| S21.33 | Jovanovski 2020 | viscous fibre ≥4 wk, ad-lib diet: -0.33 kg (CI -0.51, -0.14) | MA | 62 trials, n = 3877; GRADE moderate |
| S21.34 | Jovanovski 2021 | the same within calorie restriction: -0.81 kg | MA | 15 trials, n = 1347; GRADE moderate |
| S21.35 | Thompson 2017 | isolated soluble fibre: -2.52 kg (CI -4.25, -0.79) | MA | 12 RCTs, considerable heterogeneity |
| S21.36 | Rahmani 2019 | β-glucan: -0.77 kg, with no EI change | MA | 20 RCTs |
| S21.37 | Sood 2008 / Zalewski 2015 | glucomannan -0.79 kg; later review: short-term only | MA | 14 studies, n = 531 |
| S21.38 | Gibb 2023 | psyllium -2.1 kg over 4.8 months | MA | 6 studies, industry authors |
| S21.40 | Reynolds 2019 | whole-diet trials: significantly lower bodyweight at higher fibre | MA | GRADE moderate (fibre); kg value not resolved |
| S21.41 | Miketinas 2019 | fibre the strongest predictor of 6-month weight loss (β -0.37) | COH | secondary analysis |
| S21.13, S21.15 | Paxman, Pelkman | 7-day alginate: -7% and -12% daily EI | RCT | small |

**Verdict.**
- **Best estimate.** Chronic viscous-fibre intake lowers body weight by about a third of a kilogram over weeks to months on an ad-libitum diet: -0.33 kg, GRADE moderate.
  - Inference: over trials of roughly 4–12+ weeks, that is a deficit in the order of tens of kcal/day. It is not a measurable change in hunger.
  - The larger figures (Thompson -2.52 kg, Gibb -2.1 kg) come from fewer, more heterogeneous or industry-authored studies. The larger and better-graded Jovanovski pool does not support them.
- **Certainty: moderate** for the small weight effect, **low** for any chronic intake or hunger mechanism.
- **Weight without intake.** Rahmani finds weight loss with no measurable EI change, so the weight effect cannot be read as a satiety effect. Malabsorption and energy dilution are candidates, but the abstracts do not show which.

## 5. Whole foods against isolated fibre

| id | source | key value | grade | quality |
|---|---|---|---|---|
| S21.28 | Li 2014, pulses | satiety iAUC ×1.31 (CI 1.09, 1.58; I² 0); second-meal intake not affected (MD -19.94 kcal, ns) | MA | 9 small trials |
| S21.39 | Kim 2016, pulses | -0.34 kg over a median 6 wk at 132 g/d | MA | 21 trials, n = 940 |
| S21.29 | Sanders 2021, whole grain | hunger SMD -0.34, fullness 0.49; matched by calories: hunger -0.10 (ns), fullness 0.19 (ns); matched by available carbohydrate: hunger -0.44, fullness 0.57; EI -0.11 (ns) | MA | 32 RCTs, GRADE moderate; industry-funded |
| S21.30 | Flood-Obbagy 2009, apple | whole apple preload: -15% (187 kcal) lunch intake against no preload, and less than applesauce or juice at equal weight, energy and ingestion rate; fibre added to juice did nothing | RCT | n = 58 |
| S21.31 | Krishnasamy 2020, apple | GE t50 65 min whole against 41 puree and 38 juice; whole more filling than juice | RCT | n = 18 |
| S21.32 | Haber 1977, apple | intact > puree > juice for satiety at equal ingestion rate | RCT | n = 10 |

**Verdict.**
- **Best estimate.** Most of the whole-food effect is mass, water, energy density and food structure, not fibre as a nutrient. The best evidence is Sanders (GRADE moderate):
  - when whole and refined grain are matched by calories, or by calories and volume, hunger and fullness differences vanish;
  - they appear only when whole-grain arms are matched by available carbohydrate, which makes the portion bigger. Sanders' authors draw that reading themselves.
- **The apple data agree.** Adding the apple's own fibre to juice did not sate (S21.30). It is the intact structure that slows emptying (S21.31) and ingestion (S21.32), not the fibre grams.
- **Pulses** raise rated satiety but not the next meal's intake (S21.28).
- **Certainty: moderate** that whole-food fibre adds little beyond mass and energy density. **Low** for any residual structural effect, which is real for intact fruit but small.

## 6. Fibre and gastric emptying rate

| id | source | key value | grade |
|---|---|---|---|
| S21.18 | Schwartz 1982 | 20 g/d pectin for 4 wk: GE half-time about 2× (reversible within 3 wk); cellulose: no change | EXP |
| S21.19 | Revheim 2024 | β-glucan oat bread: T½ +18 min, lag +14 min against whole-wheat bread | RCT |
| S21.31 | Krishnasamy 2020 | whole apple 65 min against puree 41 and juice 38 (t50) | RCT |
| S21.21 | Marciani 2001 | nutrients slow GE more than viscosity (46→76 min) | RCT |
| S21.20, S21.22 | Marciani 2000, Hoad 2004 | viscosity and gels barely change GE | RCT |
| S21.14 | Odunsi 2010 | alginate capsules: no GE change | RCT |

**Verdict.**
- **No pooled estimate exists.** S1269 stays open, and the 2026-10-09 searches found no meta-analysis of fibre on GE either.
- **What the trials show:**
  - **Insoluble fibre** (cellulose) does not slow GE.
  - **Viscous soluble fibre:**
    - It slows GE variably: +18 min (Revheim), about 2× after weeks of 20 g/d pectin (Schwartz), 285 against 105 min (Wolever S1238), and nothing at ≤4.5 g guar (S1240).
    - A meal's energy content slows emptying more than its viscosity does (Marciani 2001).
    - Slowed GE often fails to move appetite (S1238, S21.22).
  - **Food structure.** An intact apple empties about 1.6× slower than puree or juice.
- **Certainty: low.**
- **How it would enter a stomach model:** as a multiplier on the solid lane's zero-order energy-emptying rate (ruling 11c-4), driven by viscous fibre grams per meal. Its size is unsettled:
  - about 1.2× (an inference from +18 min on Revheim's bread) to 2.7× (Wolever);
  - the Wolever and Hoad readings show that the slowing does not reliably translate into hunger.
- The model would gain little behaviourally from adding it.

## What the evidence says about the current model

**Supported:**
- **Ruling 11c-6 / #3626:** fibre counts only through its mass, and fibre's own satiety effect is not modelled.
  - The best-graded evidence agrees: Sanders' calorie-matched null (GRADE moderate), Clark & Slavin's 78% null on intake (S1236), Salleh's non-significant viscous-fibre CIs, Liber's null for fructans, White's 12-week RS2 null, Wolever's GE-without-appetite reading, and Flood-Obbagy's "added fibre did not sate".
  - The whole-food effects the mod should reproduce (apple, pulses, whole grain) are carried by the food's water, mass and lower energy density, which the vector already holds.
- **Fill by mass, fullness linear in gastric volume:** Marciani 2001 (R² 0.98 for nutrient meals) agrees with Goetze (the earlier harvest).

**Against, with the size of the discrepancy:**
- **Samra 2007 (S21.17).** 33 g of insoluble fibre in a cereal matched for weight and volume cut intake 75 min later by 172 kcal (937 against 1109 kcal, about 15.5%). The model reads 0, since both cereals have equal mass. This is a single small crossover in men, with appetite not different from the low-fibre cereal. Low certainty; not enough to overturn neutral.
- **Gel-forming fibre (Hoad, Paxman, Pelkman).** About 7–12% less daily intake, or higher fullness at equal gastric volume. The model reads 0. No vanilla Project Zomboid food is a gel-forming fibre supplement, so this falls outside the game's food set.
- **Polydextrose slope.** -0.67% next-meal intake per gram. The model reads 0. Polydextrose is an additive, not in game foods.

**Left out by the model, with size and certainty:**
1. **The second-meal effect.** A high-fibre evening meal lowers next-morning hunger by about 15% (S21.27; p = 0.05, n = 16), with fermentation markers (S21.26 r = 0.27).
   - The mod would read a day's fermentable fibre grams and reduce hunger 11–14 h later.
   - Size: about 15% of a hunger rating, once. Certainty: very low.
   - Recommendation: leave out.
2. **Viscous-fibre slowing of gastric emptying.** A multiplier of about 1.2–2.7× on the solid lane's emptying time, from viscous fibre grams.
   - The mod would need a viscous/soluble split in each food's fibre vector, which the data do not carry.
   - Certainty: low; the effect on hunger is unproven.
   - Recommendation: leave out. If ever added, gate it on a game choice and pin it to S1238 and S21.19.
3. **Food structure and ingestion rate** (intact against pureed against juiced): about a 1.6× GE difference (S21.31), and 15% lower next-meal intake for whole fruit against juice at equal weight and energy (S21.30).
   - The game's lanes partly carry this, because juice is a drink in the liquid lane, but puree against whole is not distinguishable.
   - Certainty: moderate for the direction.
   - This belongs to Task 24 (food form and oral processing). It is flagged here because it is what "high-fibre whole food sates more" mostly means.
4. **Chronic weight.** Viscous fibre gives -0.33 kg over weeks (GRADE moderate).
   - The mod has no reason to model it as satiety. Rahmani shows weight loss without intake change, and the size is under 50 kcal/day (inference).
   - If the mod ever models fibre's energy, the relevant row is fibre's own energy yield (about 2 kcal/g for fermentable fibre), not satiety. That row is not harvested here.

## Slug requests and supersede candidates

- **Slug requests:** none. Fibre-effect rows use `fibre` (the S1236–S1240 precedent). Whole-food rows (pulses, whole grain, apple) use `satiety`.
- **Supersede candidate: S1237 → S21.2.**
  - S1237's parameter says "the reading of an effect for specific soluble fibres", and it lists d values without their CIs.
  - The full text shows that guar (CI -1.83, 0.03), β-glucan (-0.91, 0.04) and alginate (-0.84, 0.01) are all non-significant. Only polydextrose (-0.56, -0.17) excludes zero.
  - S21.2 carries the CIs and I². S1237 as worded overstates the positive reading on which the 11c-6 pairing partly rests. The neutral ruling is unaffected, and is in fact strengthened.
- **S1269 (open):** stays open, with no meta-analysis found. New single readings to add to its range on settle or at review: S21.18, S21.19, S21.31.
- **S21.40 (Reynolds bodyweight):** minted settled with a qualitative value only, because the kg figure is in the paywalled full text. The controller may prefer to fold it into S0486 rather than keep a separate row.

## Concerns

1. **The source cell.** The brief's text `Satiety research 2, fibre harvest (2026-10-09)` fails `SOURCE_RX` (`<path>.md § …`). I followed the Plan 11c precedent: `docs/superpowers/specs/2026-10-08-satiety-physiology-design.md § 5. Evidence (the harvest), Satiety research 2, fibre harvest (2026-10-09)`. The other six harvesters will hit the same rule.
2. **Industry authorship.** It is noted in the range cell of S21.6 (polydextrose supplier), S21.16 and S21.38 (psyllium maker) and S21.29 (General Mills funding).
3. **Grades.**
   - Controlled crossovers are graded RCT per science.md, including Marciani, Hoad, French & Read, Haber and Flood-Obbagy, whose abstracts do not state randomisation.
   - Schwartz 1982 (sequential diet periods, parallel groups) is EXP.
   - Machalias 2026, Poutanen 2017 and Liber 2013 are systematic reviews without a pooled effect, graded MA per the vocabulary.
4. **Chambers 2015.** The acute 14% (162 kcal) figure is from the full-text discussion. "4% vs 25% (6 of 24)" quotes the results without the propionate arm's numerator, which the text gives only as 4%.
5. **Europe PMC throttling.** It returned 503s and timeouts during the harvest. Every row cited was resolved on a successful call, but Wanders 2011 and Clark & Slavin 2013 full texts are not open, so their numbers are abstract-only.

## Review corrections (2026-10-09, 21-review.md)

The citation review's corrections stand over the text above wherever they disagree; read 21-review.md. The supersede S1237 -> S21.2 is upheld: Salleh 2019's guar, beta-glucan, alginate and pectin effects are non-significant and only polydextrose excludes zero; #3626's bound moves to the successor in the mint commit. The 172 kcal insoluble-fibre reading (Samra) is not an isolated fibre effect: white bread with no added fibre, matched for energy, macronutrients, volume and weight, came in at 970 kcal beside the high-fibre cereal's 937 (both below the low-fibre cereal's 1109), so it does not argue against #3626. The whole-grain finding: GRADE moderate rates the positive pooled effects, not the calorie-matched subgroup, which is non-significant (hunger -0.10, -0.33 to 0.14; fullness 0.19, -0.18 to 0.57) with CIs including the overall effect; there is no calories-and-volume subgroup for fullness, and energy intake was non-significant under either matching; section 5's certainty is low. Chambers 2015 (S21.24) gives 1 of 25, and its 24-week intake null (p = 0.972) belongs in the fermentation verdict. The 'about 1.2x' from Revheim's +18 min is this report's arithmetic and is withdrawn. Li 2014's MD -19.94 has no unit in the abstract.

---

# Citation review

Model: claude-opus-5-5

# Task 21 citation review (fibre and satiety)

**Verdict: FAIL.** There are 9 row defects (S21.2 must be fixed before it can supersede S1237) and 4 report defects. The citations themselves are clean.

## What was checked

- **Citations.** I resolved all 41 settled rows (42 PMIDs; S21.37 carries two) through Europe PMC `EXT_ID:<pmid> AND SRC:MED`, resultType=core. Every row's title, first author, year, journal, volume, pages, doi and pmid match its record, Machalias 2026 (Nutr Rev 84:47-68) included. No citation defect was found.
- **Values.** I read each abstract against its value, range, population and grade.
- **Full texts** read from Europe PMC:
  - Salleh 2019 (PMC6352252)
  - Chambers 2015 (PMC4680171)
  - Sanders 2021 (PMC8321865)
  - Gibb 2023 (PMC10389520), for the disclosure
  - Revheim 2024 (PMC10949669), in part
  - Flood-Obbagy 2009 (PMC2664987) returned no full text, so its row was checked against the abstract, which carries every number in the row.
- **Author affiliations** came from the Europe PMC records for Ibarra 2015 and 2016, Brum 2016 and Gibb 2023.
- **Dry run.** `science_delta.py apply --dry-run` maps the 42 rows to S1337–S1378.

## Supersede ruling: S1237 → S21.2, upheld on condition

- **S1237 does overstate Salleh.**
  - The full text gives every pooled d with its CI. Guar is -0.90 (-1.83, 0.03; I² 95.8%, random effects). β-glucan is -0.44 (-0.91 to 0.04; fixed). Alginate is -0.42 (-0.84, 0.01; I² 80.9%, random). Pectin is -0.26 (-0.53, 0.02; fixed).
  - All four are called "non-significant" in the text. Only polydextrose, -0.36 (-0.56, -0.17; fixed), excludes zero.
  - S1237's parameter says "(the reading of an effect for specific soluble fibres)", and #3626's bound reads it as "specific soluble fibres lowered later intake". That reading is not what the pooled results show.
- **The condition.** A superseded row's value, grade and citation cells are emptied, so S21.2 must carry everything S1237 carries. As filed it drops pectin -0.26 and the list of the four test products that were individually significant. Defect 1 fixes both.
- **The controller's follow-up.** #3626's bound in `docs/reference/claims.tsv` names S1237. It moves to S21.2's minted id in the same commit as the supersede (CLAUDE.md § 4.4).

## Defects

1. **S21.2, `value`.** Pectin is missing, and so are the per-fibre model and n. Replace the cell with:
   `pooled Cohen's d on energy intake: guar gum -0.90 (95% CI -1.83, 0.03; I2 = 95.8%; random effects; n = 3); beta-glucan -0.44 (95% CI -0.91 to 0.04; I2 = 0%; fixed effects; n = 2); alginate -0.42 (95% CI -0.84, 0.01; I2 = 80.9%; random effects; n = 2); polydextrose -0.36 (95% CI -0.56, -0.17; I2 = 0%; fixed effects; n = 4); pectin -0.26 (95% CI -0.53, 0.02; I2 = 0%; fixed effects; n = 2); only four test products significantly reduced energy intake: 5 g alginate and 5 g guar gum in milk beverages, 9 g alginate in chocolate cookies and 25 g polydextrose in chocolate-flavoured beverages`

2. **S21.2, `range`.** "31 studies" is wrong. The paper has 15 RCT articles covering 17 interventional studies and 31 soluble-fibre types, doses or viscosities; 21 fibres from 10 articles were meta-analysed. The paper also prints polydextrose's upper CI bound two ways. Replace the cell with:
   `15 RCT articles (17 interventional studies; 31 soluble-fibre types, doses or viscosities), 21 fibres from 10 articles meta-analysed; n = pooled studies per fibre; risk of bias high: only four studies clearly reported randomisation and only one was double-blinded (low Jadad scores); energy intake measured 90 to 240 min after the fibre; the polydextrose upper bound is printed both -0.017 and -0.17 (either excludes zero); no certainty rating given`

3. **S21.24, `value`.**
   - "4% vs 25% (6 of 24)" leaves out a numerator the full text gives: "One of 25 participants … (4%)". The report's concern 4 is wrong on this point.
   - The acute figure should be the Results' own numbers, not the Discussion's rounded "14%".
   - The row also omits the 24-week ad libitum intake null (p = 0.972) and the absence of any subjective-appetite effect. Both bear directly on satiety.
   - Replace the cell with:
   `acute 10 g inulin-propionate ester vs inulin-control: buffet intake 300 min after a standard breakfast fell from 1175 kcal (95% CI 957 to 1392) to 1013 kcal (95% CI 816 to 1210) (p < 0.01), a mean reduction of 13.8%, with higher PYY and GLP-1 at 240-420 min and no suppression of subjective appetite; 24 weeks of 10 g/day vs inulin-control: >= 3% weight gain in 1 of 25 (4%) vs 6 of 24 (25%) (p = 0.036), >= 5% in none vs 4 of 24 (17%) (p = 0.033); weight change -1.02 kg (95% CI -2.10 to 0.04) vs 0.38 kg (95% CI -0.95 to 1.72), p = 0.099; change in ad libitum meal intake at week 24 not different between groups (p = 0.972)`

4. **S21.24, `range` and `population`.**
   - The long-term trial randomised 60 and analysed 49.
   - The acute volunteers are not described as overweight; the Discussion calls them "healthy subjects".
   - `range`: `acute randomised controlled crossover (n = 20); long-term randomised double-blind placebo-controlled parallel trial, 60 randomised, 49 analysed; no certainty rating given`
   - `population`: `acute: 20 volunteers (healthy subjects, per the discussion); long-term: overweight adults aged 40-65 y, BMI 25-40`

5. **S21.6, `range`.** Alhoniemi is with Avoltus Oy, not the supplier. Ibarra, Olli and Tiihonen are with DuPont Nutrition & Health. Replace the cell with:
   `6 studies in the lunch analysis, 3 in the rest-of-day and daily analyses; PRISMA; Ibarra, Olli and Tiihonen are with DuPont Nutrition & Health (the polydextrose supplier), Alhoniemi with Avoltus Oy; no certainty rating given`

6. **S21.7, `range`.** It has the same DuPont authors as S21.6, but its industry authorship is not noted. Replace the cell with:
   `7 studies; Ibarra, Olli and Tiihonen are with DuPont Nutrition & Health (the polydextrose supplier), Alhoniemi with Avoltus Oy; no certainty rating given`

7. **S21.16, `range`.** Both Brum and Gibb are Procter & Gamble, not Gibb alone. Replace the cell with:
   `two sequential randomised double-blind placebo-controlled crossover trials; Brum and Gibb are with Procter & Gamble, maker of the psyllium product (Metamucil); no intake outcome`

8. **S21.33, `value`.** The cell lists body fat among the reductions, but the abstract reads "with no change in body fat". Replace the cell with:
   `-0.33 kg (95% CI -0.51, -0.14; P = 0.004); BMI -0.28 (-0.42, -0.14); waist -0.63 cm (-1.11, -0.16); no change in body fat (-0.78%; 95% CI -1.56, 0.00; P = 0.05); greater reductions in overweight people and those with diabetes or metabolic syndrome`

9. **S21.9 and S21.13, `parameter`.** The report says both are paired disagreements, but only the null side names the pairing (S21.10, S21.14). Harvest rule: both rows of a pair name the disagreement.
   - S21.9: `subjective appetite after acute resistant starch, by dose and type (the pooled positive reading; S21.10 is the large-trial null)`
   - S21.13: `daily energy intake over 7 days of preprandial strong-gelling sodium alginate vs control (free-living; the positive reading against S21.14's alginate null)`

## Report defects (21-report.md; the rows are not affected)

1. **The 172 kcal implication.**
   - Samra's abstract groups the high-fibre cereal (937 kcal) with white bread (970 kcal). White bread has no added fibre and was matched to the cereal for energy, macronutrients, volume and weight. Both came in below the low-fibre cereal (1109 kcal).
   - The 172 kcal is therefore the high-fibre cereal against one low-fibre comparator. It is not an isolated effect of insoluble fibre: an equal-mass, equal-energy food without fibre almost matched it.
   - The § 1 table should show white bread at 970. The "Against" bullet should say the fibre-specific effect is not isolated. That weakens the discrepancy further and leaves #3626 better supported, not less.

2. **The whole-grain matched-energy finding.**
   - The ruling has the right direction: Sanders' authors themselves say the carbohydrate-matched arms fed a larger volume.
   - Its certainty is overstated. GRADE moderate rates the pooled overall effects, which are positive. It does not rate the calorie-matched subgroup:
     - hunger: 7 comparisons from 4 studies, -0.10 (-0.33, 0.14);
     - fullness: 5 comparisons from 3 studies, 0.19 (-0.18, 0.57).
   - The subgroup's CIs include the overall effect, so it is a non-significant subgroup, not a demonstrated null.
   - The paper has no calories-and-volume subgroup for fullness ("insufficient studies"), so "hunger and fullness differences vanish" under calories-and-volume matching is half unsupported.
   - Energy intake did not differ by matching either: carbohydrate-matched -0.13 (ns), calorie-matched -0.08 (ns).
   - Rewrite § 5's certainty as **low** that whole-grain fibre adds nothing beyond mass and energy density.

3. **Concern 4 (Chambers) is wrong.** The text gives 1 of 25 (see defect 3). The chronic intake null (p = 0.972) belongs in the § 3 fermentation verdict as evidence against a chronic satiety effect.

4. **§ 6's "about 1.2×" from Revheim's +18 min is harvester arithmetic on a baseline the row does not carry.** The abstract gives no control T½, and the ±18 min is a difference. Either take the paper's absolute T½ values into S21.19 and recompute, or drop the 1.2× figure. Wolever's 2.7× (285/105) is sound arithmetic on S1238.

## Residuals (no action required)

- **Grades.** I agree with them: the uncontrolled-randomisation crossovers as RCT, Schwartz as EXP, Miketinas as COH (a regression derived from trial data), and Poutanen, Liber and Machalias as MA.
- **S21.40 (Reynolds bodyweight).** The row's wording "certainty for dietary fibre and critical outcomes graded moderate" is accurate. The report's § 4 table cell "GRADE moderate (fibre)" next to a bodyweight row implies a bodyweight-specific GRADE, which the abstract does not give. The controller may fold the row into S0486 as the report suggests.
- **Li 2014's second-meal MD -19.94.** The abstract carries no unit, and the report's "kcal" is unverified. The row cell is correctly unit-less.
- **Id order.** The other harvesters' parts (22–27) will shift the minted ids. The dry-run mapping S1337–S1378 holds only if Task 21 is applied first.
- **The source-cell `SOURCE_RX` workaround (concern 1)** is the controller's ruling to make for all seven harvesters.
