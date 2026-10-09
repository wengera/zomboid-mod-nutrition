# Satiety research 2, player states harvest (2026-10-09)

The harvest report of Task 26 of Satiety research 2 (2026-10-09), followed by its citation review. The review's corrections stand over the report wherever they disagree; the rows in docs/reference/science.tsv carry the corrected cells.

# Task 26 report: other player states that change hunger (Satiety research 2)

Model: claude-opus-5-5. Part file `26-science-part.tsv`: 49 rows (S26.1-S26.49), 44 settled, 5 open, 0 unverified. `science_delta.py apply --dry-run` passes; a full apply to a scratch copy of the register mints S1337-S1385 and `science_check.py` reads 0 findings on that copy and on `--part`.

Every settled citation was resolved against Europe PMC (or NCBI E-utilities when Europe PMC returned 503) by title, first author and year, and every number was read from the abstract, or from the PMC full text for Jeschke 2008 (REE 130-140 % predicted), Li 2026 (Table 2) and Eiler 2015 (+7 %, 34 %). The Hill 2022 subgroup values come from the authors' preprint on OSF (doi:10.31234/osf.io/fjqsd), whose overall g matches the published abstract; the row says so and carries both records.

The source cell uses the spec path (`docs/superpowers/specs/2026-10-08-satiety-physiology-design.md § 5, Satiety research 2, player-state harvest (2026-10-09)`). The source text `harvest-common.md` prescribes fails `sciencelib.SOURCE_RX`, which requires `<report>.md § <heading>`.

No study in this part was already in the register. S1316 (Millet 2021, cold +g 0.44 and heat g -0.39) and S1282-S1285 (sleep) were extended, not duplicated. Grigg 2023 (S1315) is a different paper from Grigg 2025 (S26.33).

## 1. Acute illness and infection

| id | key value | grade | quality markers |
|---|---|---|---|
| S26.1 | total intake -5-6 %, non-breast-milk foods -20-30 % during diarrhoea or fever | COH | 131 infants, 1615 observation days; no rating |
| S26.2 | > half of inpatients do not finish the meal; HR death 2.10 at a quarter eaten, 3.02 at nothing | COH | 16,290 inpatients; no rating |
| S26.3 | cytokine mechanism of the anorexia of infection | TXT | mechanism only |
| S26.4 | endotoxin sickness symptoms (a composite that includes reduced appetite) are confined to the acute phase; none 24-72 h | RCT | n = 18 men; composite scale, not appetite alone |
| S26.5 | open: the size and duration of adult appetite loss in a common infection | — | — |
| S26.6 | open: the REE rise per °C of fever | — | — |

**Verdict.** Illness lowers intake. The direction is certain; the size is low-certainty.
- The one quantified reading comes from infants: about a 5 % fall in total intake and a 20-30 % fall in solid food on symptom days, and it ends when the symptoms end.
- The hospital survey shows that most inpatients eat less than they are served. It does not separate illness from hospital food.
- The human endotoxin model ties sickness symptoms to the cytokine peak, within hours, with nothing left at 24-72 h. It gives no hunger rating on its own.
- No adult trial was found. The figure often quoted, that fever raises metabolic rate by 10-13 % per °C, was not resolved here, and S26.6 stays open.
- The mouse force-feeding study (Murray 1979, pmid:283688) supports anorexia as a host defence. It is animal evidence and was not minted.

## 2. Nausea and motion sickness

| id | key value | grade | quality markers |
|---|---|---|---|
| S26.7 | 47 % of a drink still in the stomach at 1 h after motion sickness | EXP | n not given in the abstract |
| S26.8 | oral-caecal transit 144 min vs 107 min in the susceptible group; r = 0.43 with symptoms | EXP | n = 45 |
| S26.9 | open: nausea's effect on hunger or intake | — | — |

**Verdict.** Motion sickness slows gastric emptying and transit (low certainty: small, old, non-randomised studies).
- No human measurement of hunger or intake under nausea was found.
- The mechanism points to food staying in the stomach longer, which already reads as fullness in this model. The effect on hunger is unmeasured.

## 3. Injury, pain, surgery and burns

| id | key value | grade | quality markers |
|---|---|---|---|
| S26.10 | REE 130-140 % of predicted after a severe burn, peaking at 2 weeks and still raised at discharge | COH | n = 242 children, > 30 % TBSA |
| S26.11 | appetite falls through the first 7 days after abdominal surgery | COH | n = 169; questionnaire |
| S26.12 | open: pain or a non-burn injury on hunger or intake | — | — |

**Verdict.** The hypermetabolism is certain for severe burns (moderate certainty; paediatric, single centre). Clinically, appetite does not rise to meet it: it falls after surgery (low certainty).
- No controlled reading of pain on hunger was found.
- Expenditure and appetite diverge after injury. That is the reverse of the model's deficit drive, which raises hunger as the energy state falls.

## 4. Psychological stress, anxiety and acute fear

| id | key value | grade | quality markers |
|---|---|---|---|
| S26.13 | stress and overall intake g 0.114 (0.061, 0.166); unhealthy food 0.116, healthy food -0.111 | MA | k = 54, N = 119,820, I² 93.6 %; 30 of 54 studies weak |
| S26.14 | laboratory-induced g 0.156 (k = 22, I² 51.7 %); strong-quality studies g 0.039 (k = 5) | MA | preprint subgroups |
| S26.15 | 42 % eat less, 38 % eat more under stress | COH | n = 212 students, self-report |
| S26.16 | an anticipated-speech stressor did not change total intake | EXP | n = 68 |
| S26.17 | eating without hunger 965 vs 794 kJ after acute stress | RCT | n = 129 |
| S26.18 | high cortisol reactors ate more after stress | RCT | n = 59 women |
| S26.19 | Trier test: no change in laboratory intake; evening intake higher | RCT | n = 87 women |
| S26.20 | exam stress: no general change in intake; it rose or fell with anxiety and support | COH | n = 179 |

**Verdict.** The best estimate is a trivial positive association between stress and intake: g ≈ 0.11 overall and g 0.04 in the 5 strong studies.
- Certainty is low. Heterogeneity is about 94 % and most studies are weak.
- The direction differs by person. Self-report splits about evenly between eating more and eating less (S26.15). Naturalistic and exam stress shows no main effect (S26.20).
- The Hill discussion section says acute stress inhibits appetite and physical threat ("anxious/frightened", "threat of attack by a dog") cuts snacking. Those are cited claims in the review's discussion, not pooled effects, and no row carries them.
- The lower-quality positives that the best evidence does not support as a general effect:
  - the snack-intake rise after laboratory stressors (S26.17, +22 %);
  - the cortisol-reactor finding (S26.18).
  
  Both hold in subgroups, such as disinhibited eaters and high reactors, and do not hold on average (S26.16, S26.19).
- **Disagreement.** The moderate-quality and weak studies give g ≈ 0.12-0.15; the strong ones give 0.039. The weight of evidence favours a near-null effect on the amount eaten, with a shift in the choice of food.
- A cortisol change alone is not a satiety effect. No hormone-only row was minted.

## 5. Low mood, depression and boredom

| id | key value | grade | quality markers |
|---|---|---|---|
| S26.21 | induced negative emotion raises eating only in restrained eaters; positive emotion raises eating in everyone | MA | 56 studies, 3670 participants; high heterogeneity |
| S26.22 | induced negative mood raises intake generally; small per meal | MA | 33 studies, 2491 participants |
| S26.23 | more chocolate eaten during 1 h of boredom | RCT | n = 30, crossover |
| S26.24 | diary boredom predicts kcal; induced boredom raises snacking | EXP | three studies |

**Verdict.** Mood shifts the amount eaten little (low certainty).
- The two meta-analyses disagree on negative mood:
  - Evers 2018 is the larger and later one, and finds an effect in restrained eaters only;
  - Cardi 2015 finds a general small effect.
  
  The weight favours Evers, which is larger, more recent and models moderators. In unrestrained people, negative mood does not change intake.
- Positive mood raises intake in both.
- Boredom raises snacking when snacks are at hand. The evidence is small experiments with no reported sizes, so the effect size is very low certainty.
- Depression changes appetite in both directions. Simmons 2016 (pmid:26806872) shows a neural split, and no prevalence was resolved, so no row was minted.

## 6. Sleep loss (extending S1282-S1285)

| id | key value | grade | quality markers |
|---|---|---|---|
| S26.25 | partial sleep loss: intake +385 kcal (252, 517), no change in expenditure | MA | 11 studies, n = 172 |
| S26.26 | ≤ 5.5 h: SMD 0.37, +204 kcal/d (112, 295) | MA | 15 studies after risk-of-bias appraisal |
| S26.27 | one 4 h night: +559 kcal (22 %) the next day, hunger up before breakfast and dinner | RCT | n = 12 men |
| S26.28 | 5 days of short sleep: TDEE +5 %, intake beyond need, +0.82 kg; recovery sleep reverses it | EXP | n = 16 inpatients |
| S26.29 | total vs partial loss: late-night intake comparable (p = 0.12) | EXP | n = 66 |

**Verdict.** Sleep loss raises intake by about 200-385 kcal/day.
- The best pooled estimates are +204 kcal (Fenton, after risk-of-bias selection) and +385 kcal (Al Khatib). With Zhu 2019 (S1284) at +253 kcal and a hunger rise of 13.4 mm, the moderate-certainty band is 200-400 kcal/d.
- The single-trial +559 kcal (S26.27) sits above the pooled estimates.
- Total deprivation does not raise intake beyond 4 h sleep (S26.29), so the effect looks like a step at about ≤ 5.5 h rather than proportional to the hours lost.
- The effect starts the next day and reverses on recovery sleep (S26.28).

## 7. Temperature (extending S1316)

| id | key value | grade | quality markers |
|---|---|---|---|
| S26.30 | 19 °C vs 23.5 °C: +411 kcal/d (13 %) while cold, none the next day | RCT | n = 47 |
| S26.31 | 2.5 h at 18 °C: no change in hunger or intake | EXP | n = 10 |
| S26.32 | walking at 8 °C vs 20 °C: 1299 vs 1172 kcal at the next meal | RCT | n = 16 |
| S26.33 | 16 °C water immersion: 2783 vs about 1850 kJ at the next meal | RCT | n = 15 |
| S26.34 | torso and foot heating: -176 kcal (-329, -23) | RCT | n = 16 |

**Verdict.** Cold raises intake and heat lowers it, by a small amount and only while exposed or straight after.
- S1316's pooled g is 0.44 for cold and -0.39 for heat, moderate certainty, from 13 RCTs.
- Sizes: about +10-13 % in a day of mild cold, +10-50 % at the meal right after a strong cold exposure (water), and about -17 % at the meal after heating.
- Hunger ratings do not move in most of these trials (S26.33, S26.34; Langeveld null). The effect shows in intake, not in VAS.
- The effect is gone the day after (S26.30).

## 8. Drugs

### Nicotine

| id | key value | grade | quality markers |
|---|---|---|---|
| S26.35 | nasal nicotine cut hunger (only after a caloric load) and meal intake | RCT | n = 20 men |
| S26.36 | 2 mg gum lowered appetite ratings | RCT | n = 50 |
| S26.37 | quitting: +1.12 kg at 1 month to +4.67 kg at 12 months | MA | 62 RCTs |
| S26.38 | quitting: +227 kcal/d over 48 days, 69 % of the gain | EXP | n = 13 women |
| S26.39 | quitting: intake up at 2 weeks, back to baseline by 26 weeks | RCT | n = 95 |

**Verdict.**
- Acute nicotine lowers appetite modestly. The direction has moderate certainty; the size is unquantified, from small trials.
- Withdrawal raises intake by about 200-250 kcal/d in the first weeks. It fades by about 6 months, while the weight stays. The weight gain is high-certainty (MA); the intake size is low-certainty (one small EXP).

### Alcohol

| id | key value | grade | quality markers |
|---|---|---|---|
| S26.40 | food intake +343 kJ (161, 525); total intake +1072 kJ | MA | 12 studies; heterogeneity and small-study effects |
| S26.41 | 24 g ethanol: lunch 7301 vs 6479 kJ | RCT | n = 26 men |
| S26.42 | 32 g vs 8 g: lunch 5786 vs 4928 kJ; hunger up all day | RCT | n = 12 men |
| S26.43 | IV alcohol clamp: +7 % intake | RCT | n = 35 women |

**Verdict.** An alcoholic drink before a meal raises the food eaten by about 340 kJ (≈ 80 kcal), and the drink's own energy is not compensated (moderate certainty).
- The effect appears from about 24 g of ethanol and not at 8 g (S26.42).
- Pharmacological alcohol alone, with no taste or calories, gives a smaller rise (+7 %), so part of the effect is cue and context.

### Caffeine

| id | key value | grade | quality markers |
|---|---|---|---|
| S26.44 | 1 mg/kg: breakfast -10 %; 3 mg/kg: no change; none out of the laboratory | RCT | n = 50 |
| S26.45 | caffeine or coffee: no change in lunch intake or gastric emptying | RCT | n = 12 |
| S26.46 | coffee at 3 mg/kg: no change in appetite or intake | RCT | n = 16 men |

**Verdict.** Caffeine has no reliable effect on hunger or intake (moderate certainty for a null).
- The one positive reading is a non-monotonic -10 % at the low dose only, transient and absent outside the laboratory.
- Schubert's 2017 narrative review (pmid:28446037), which says caffeine "may suppress" intake 0.5-4 h before a meal, is not supported by the trials. It was not minted.

## 9. Thirst and dehydration

| id | key value | grade | quality markers |
|---|---|---|---|
| S26.47 | 2.8 % body-mass loss: breakfast 4612 vs 4237 kJ (P = 0.436); lower fullness | RCT | n = 10 men |
| S26.48 | 1.9 % loss: intake 1953 vs 2027 kJ; hunger the same; thirst +27-32 mm | RCT | n = 16 |
| S26.49 | open: dehydration beyond 3 % | — | — |

**Verdict.** Mild dehydration (≤ 3 %) leaves hunger and intake unchanged (moderate certainty; two RCTs agree).
- The animal dehydration-anorexia has no human reading at deeper deficits (S26.49 open).

## What this says about the current model

The model reads its hunger as `min(0.69, hungerTarget(Z, es) × circadian(h) × acuteFactor(S))`. Nothing in it reads illness, mood, stress, temperature, nicotine, alcohol, caffeine, sleep debt or hydration.

### Shipped choices the evidence supports
- **Stress, Panic, Unhappy, Bored, Thirsty (mild) and caffeine are all neutral for hunger.** The best evidence for each is a near-null or a split by person:
  - stress, g 0.04 in strong studies;
  - negative mood, null outside restrained eaters;
  - thirst, two null RCTs;
  - caffeine, three null or transient RCTs.
  
  The current omission matches rule 5 ("mixed or absent → no special effect").
- **Alcohol calories feed the pool at their macronutrient weights (#3622).** The evidence goes further, but in the opposite direction from extra satiety: alcohol energy is not compensated. Keeping alcohol's calories as plain energy, with no ethanol satiety bonus, is consistent with it.

### What the evidence argues against
- **Injury and burns under the deficit drive.** A badly hurt or burned character spends 130-140 % of predicted REE (S26.10). If the mod raises expenditure for injury, the deficit drive will raise hunger. The clinical evidence (S26.11, S26.2) says appetite falls. The discrepancy is direction, not size. Its certainty is low, because these are hospital populations.
- **Illness.** A character with FOOD_SICKNESS or SICKNESS today gets no appetite cut. The evidence says intake falls by about 5-30 % while the symptoms last (S26.1, infants) and ends with them (S26.4). The size is low-certainty; the direction is high-certainty.

### What the model leaves out, by size and certainty
1. **Sleep debt** (moderate certainty, +200-400 kcal/d, about 10-20 % of daily intake).
   - It would read the mod's sleep-debt state, or a night under about 5.5 h.
   - It would multiply hunger the next day, or raise the energy-state term, by a step rather than in proportion to the hours lost (S26.29).
   - It would reverse on a full night (S26.28).
   - The largest, best-evidenced omission. S1284 gives +13.4 mm VAS directly.
2. **Ambient cold and heat** (moderate certainty; g 0.44 and -0.39 in S1316; about +13 % per cold day, about -17 % at the meal after heating).
   - It would read the thermoregulator or the Hypothermia and Hyperthermia moodles.
   - It would act only while exposed (S26.30: none the next day).
   - VAS hunger often does not move, so it acts on how much is eaten.
   - The mod has no intake-size lever: the player chooses what to eat. The only lever is hunger, which overstates the evidence. The spec already names cold as "no same-day term now".
3. **Acute illness** (direction high, size low).
   - It would read FOOD_SICKNESS and SICKNESS (the fever term), and later infection.
   - It would multiply hunger down while they are raised, with no carry-over (S26.4).
   - The size is a game choice resting on S26.1 (-5-6 % total, -20-30 % solids), with S26.5 open.
4. **Nicotine.** Acute suppression is small and unquantified. Withdrawal is about +227 kcal/d for weeks (S26.38) and fades by about 26 weeks (S26.39).
   - It would read the smoker trait and time since the last cigarette, raising hunger during the first 2-12 weeks without cigarettes.
   - The withdrawal rise rests on one EXP of 13 women (S26.38), so the size is low-certainty.
5. **Alcohol's aperitif effect** (moderate certainty; +343 kJ ≈ 80 kcal at the next meal; threshold above 8 g and present at 24 g).
   - It would read the mod's acute ethanol state and lift hunger for the next meal.
   - It is small next to the meal-pool terms, and could be left neutral.
6. **Motion sickness and nausea** slow gastric emptying, but the effect on hunger is unmeasured (S26.9). Leave it neutral.
7. **Boredom.** The direction is positive and small, and only when food is at hand; the size has very low certainty. Leave it neutral.

## Slug requests and supersede candidates

- **Slugs:** none needed. A `nicotine` slug would help if smoking rows grow; for now S26.37 sits under `body-composition` and the intake rows under `satiety`.
- **Supersede candidates:** none. S1284 (Zhu 2019, +252.8 kcal/d) sits between the two new pooled estimates. All three are consistent, so no supersede.
- **Concerns:**
  1. The source-cell format of `harvest-common.md` fails the validator, so the spec path was used.
  2. S26.14's subgroup numbers are read from the preprint and not from the published tables, which were not accessible. The published version may differ slightly.
  3. Wood 1987 has no DOI and no n in its abstract.
  4. The grades of S26.18 (Epel) and S26.35 (Perkins) assume a controlled crossover. Neither abstract states randomisation, so EXP is the alternative.
  5. Europe PMC returned 503 for most of the session. Several fetches went through NCBI E-utilities instead.

## Review corrections (2026-10-09, 26-review.md)

The citation review's corrections stand over the text above wherever they disagree; read 26-review.md. S26.32 is dropped as a duplicate of S25.36 (Crabtree 2015). Sleep: total deprivation and 4 h restriction gave comparable late-night intake over unequal windows (S26.29), and next-day intake was consistent within individuals across the two; morning hunger after total deprivation exceeded that after 4.5 h sleep (S1282). Whether the effect is a step or graded by hours lost is not settled by these rows (drop 'by a step' from implication 1). Alcohol: lunch intake was higher after 32 g than after 8 g (S26.42) and after 24 g than after an alcohol-free lager (S26.41); no row tests 8 g against 0 g. Temperature: S1316's pooled g is 0.44 for cold and -0.39 for heat, from 13 RCTs; the row gives no certainty rating. Boredom: the eating experiment compared a boring film against a sad one, not a low-boredom one (S26.24). Illness: the no-carry-over reading of S26.4 rests on a combined symptom score, an inference about appetite. Stress: the strong studies' g = 0.039 is small but still significant (p = .018).

---

# Citation review

Model: claude-opus-5-5

# Task 26 citation review (read-only)

FAIL

Method: all 43 distinct PMIDs (44 settled rows) were fetched from NCBI E-utilities (Europe PMC returned 503). Title, first author, year, journal, volume and pages, DOI and PMID match the record for every settled row. Every abstract number was checked. Full texts were read for Engler 2023 (PMC10623394; the GASE composite includes reduced appetite; randomised, double-blind, placebo-controlled crossover), Jeschke 2008 (PMC3905467; 130-140 % predicted, peak at 2 weeks, n = 212), Langeveld 2016 (PMC5002965), Moynihan 2015 (PMC4381486), Li 2026 (PMC13251514, Table 2), Eiler 2015 (PMC4493764; 7 %, 34 %, 9-30 %, pseudo-randomised counterbalanced) and Hill 2022. For Hill, the OSF file behind doi:10.31234/osf.io/fjqsd is `HPR_ACCEPTED.pdf`, the accepted manuscript. Every S26.13 and S26.14 value matches its text and Table 1 exactly: 0.114 [0.061, 0.166], I2 93.556, 0.116 [0.055, 0.177], -0.111 [-0.165, -0.056], 30/19/5, 0.156 k = 22 n = 1,213 I2 51.721 %, 0.100 k = 32 n = 118,607 I2 95.953 %, Q(1) = 0.621 p = .431, strong 0.039 [0.007, 0.071] k = 5 n = 2,277, moderate 0.147, weak 0.115, Q(2) = 5.990 p = .050.

No row cell holds the harvester's own arithmetic. Every percentage in a row (5-6 %, 20-30 %, 22 %, 13 %, about 10 %, +30 %, 69 %, 7 %, 34 %) is the source's own.

## Grade rulings
- **S26.35, Perkins 1991.** RCT stands. The row's reading is nicotine against placebo inside a four-session, within-subject, placebo-controlled design. That is the crossover contrast itself, and science.md counts a controlled crossover as RCT.
- **S26.18, Epel 2001.** EXP. The stress and control sessions are within-subject, but the row's reading is high against low cortisol reactors. That is an observed split: reactor status was measured, not assigned. The abstract does not state the session order. The contrast the row carries is not the controlled crossover contrast, so the RCT grade overstates it.

## Defects
1. **S26.18, `grade` and `range`.** The contrast is an observed split of reactors, not a randomised or crossover contrast (ruling above). Corrected cells:
   - grade: `EXP`
   - range: `stress and control sessions on different days, within subject; high and low cortisol reactors are an observed split, not assigned; session order not stated in the abstract; amounts not in the abstract; no certainty rating given`
2. **S26.31, `grade` and `range`.** The full text says "one of the days the subjects were tested under thermoneutrality and the other day under mild cold exposure, they were blinded to the setting and tests were performed in a random order". That is a randomised-order, blinded crossover, so it is RCT, not EXP. Corrected cells:
   - grade: `RCT`
   - range: `crossover, two days about two weeks apart, blinded to the setting, in random order; no certainty rating given`
3. **S26.39, `grade` and `range`.** The randomisation was of the quit date (week 2 against week 6). The row's values are within-subject changes from baseline in self-selected abstainers, not a randomised contrast. That is the same kind of reading as Stamford's S26.38, which is graded EXP. Corrected cells:
   - grade: `EXP`
   - range: `95 smokers randomised to early (week 2) or late (week 6) quit dates; the intake changes are within-subject changes from baseline in self-selected abstainers, not the randomised contrast; amounts not in the abstract; no certainty rating given`
4. **S26.24, `value`.** This is the between-arm defect class. In Study 3, the experiment that measured consumption, the comparator was an induced-sadness condition, not low boredom. The full text reads: "boredom specificity was tested against another negative experience, sadness"; "Relative to participants who watched a sad movie…". Study 2's outcome was a self-reported desire to snack. Corrected value: `in the diary, state boredom positively predicted calorie, fat, carbohydrate and protein consumption; a high- against low-boredom task raised the self-reported desire to snack rather than eat something healthy among people high in objective self-awareness; in the consumption experiment, a boring film raised intake of less healthy and of exciting healthy foods against a sad film (not a neutral or low-boredom film) among people high in objective self-awareness`
5. **S26.24, `population`.** Corrected population: `33 adults in a 7-day diary (Limerick), 79 students (Study 2) and 44 students (Study 3), University of Limerick`
6. **S26.22, `value`.** The abstract's "the size of the effect across a single meal is small" qualifies the positive-mood strategy for anorexia and bulimia nervosa. It does not describe negative mood in general. The row, and the report's "Cardi 2015 finds a general small effect", attach it to the wrong effect. Corrected value: `induced negative mood was significantly associated with greater food intake, especially in restrained and binge eaters; positive mood was also associated with greater caloric intake across groups; the authors call the effect across a single meal small when proposing positive-mood strategies for anorexia and bulimia nervosa`
7. **S26.14, `range`.** Two changes:
   - The source is the accepted manuscript, not a preprint.
   - The pairwise quality contrasts were not significant. The report's verdict, "the weight of evidence favours a near-null effect", leans on the strong-study g, so this quality marker carries weight.
   
   Corrected range: `subgroup values read from the authors' accepted manuscript on OSF (HPR_ACCEPTED.pdf; Table 1 and Results), whose overall g 0.114 matches the published abstract; study quality did not moderate overall, Q(2) = 5.990, p = .050, and no pairwise quality contrast was significant (strong vs weak Q(1) = 3.183, p = .074; strong vs moderate Q(1) = 3.449, p = .063); strong-quality I2 <1%`
8. **Range cells for meta-analyses that give no certainty rating.** harvest-common.md requires "no certainty rating given". Corrected range cells:
   - S26.37: `62 studies of randomised cessation trials, random-effects inverse variance; no certainty rating given`
   - S26.25: `17 studies (n = 496) reviewed, 11 (n = 172) meta-analysed, random effects; I2 computed, value not in the abstract; no certainty rating given`
   - S26.21: `56 experimental studies, 3670 participants, random effects; heterogeneity high; pooled effect sizes not in the abstract; no certainty rating given`
   - S26.22: `33 laboratory studies, 2491 participants; pooled effect sizes not in the abstract; no certainty rating given`
9. **S26.32, the whole row.** It duplicates S25.36 in `25-science-part.tsv`: the same study, Crabtree and Blannin 2015 (pmid 24870575), with the same values. The controller keeps one row, S25.36 because it was minted first, and drops S26.32. The report's temperature table then cites S25.36 for that study.
10. **26-report.md, § 6 and implication 1 (the sleep "step").** The report says: "Total deprivation does not raise intake beyond 4 h sleep (S26.29), so the effect looks like a step … rather than proportional to the hours lost". It also says the effect should apply "by a step rather than in proportion to the hours lost (S26.29)". S26.29 does not support either claim:
    - Its only between-condition intake comparison is the late-night window, and the two windows differ in length (22:00-04:00 against 22:00-06:00).
    - Its next-day reading is an intraclass correlation, which is within-person consistency, not equality of intake.
    - The register's S1282 (Schmid 2008) found morning hunger of 3.9 after total deprivation against 2.2 after 4.5 h (P = 0.041), which points the other way.
    
    Corrected text: `Total deprivation and 4 h restriction gave comparable late-night intake over unequal windows (S26.29), and next-day intake was consistent within individuals across the two; morning hunger after total deprivation exceeded that after 4.5 h sleep (S1282). Whether the effect is a step or graded by hours lost is not settled by these rows.` Implication 1 drops the "by a step" clause.
11. **26-report.md, the alcohol verdict and implication 5.** The report says: "The effect appears from about 24 g of ethanol and not at 8 g (S26.42)" and "threshold above 8 g". Caton's abstract compares 32 g against 8 g only, and gives no 8 g against 0 g lunch result. Corrected text: `Lunch intake was higher after 32 g than after 8 g (S26.42) and after 24 g than after an alcohol-free lager (S26.41); no row tests 8 g against 0 g.`
12. **26-report.md, § 7.** The report says "S1316's pooled g is 0.44 for cold and -0.39 for heat, moderate certainty". S1316 carries no certainty rating. Corrected text: `S1316's pooled g is 0.44 for cold and -0.39 for heat, from 13 RCTs; the row gives no certainty rating.`

## Residuals (no correction dictated)
- **S26.28, Markwald 2013, graded EXP.** The full text was unreachable: PMC returned a captcha, PNAS returned 403 and Europe PMC returned 503. If participants were randomised to condition order, the grade is RCT. Check this before minting if possible.
- **S26.38, Stamford 1986, graded EXP.** This is an uncontrolled before-after reading of cessation, not a dosing experiment. COH is arguable. The controller rules.
- **S26.7, Wood 1987.** The 47 % is set against the 14 % of a drug arm. The abstract gives no placebo residual. The row is accurate but could note that.
- **S26.23, Havermans 2015.** "a total of 30 participants" is ambiguous between 30 in each experiment and 30 in all. The row says 30 per experiment.
- **26-report.md, illness.** "ends with them (S26.4)" and "no carry-over (S26.4)" are read from a composite symptom score, not from appetite or intake. Mark them as inference.
- **26-report.md, the stress verdict.** It should add that the strong-study g of 0.039 is still significant (p = .018), and that the quality contrasts were not significant (defect 7).
- **Source cell.** The source cell uses the spec path in place of the text harvest-common.md prescribes, which the harvester says fails `SOURCE_RX`. The controller rules.
- **Hill 2022.** The harvester's concern 2 is resolved: the OSF file is the accepted manuscript, and its values match the row.
