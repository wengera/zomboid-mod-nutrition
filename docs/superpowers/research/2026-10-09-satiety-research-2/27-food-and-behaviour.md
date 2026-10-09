# Satiety research 2, food-side and behavioural effects harvest (2026-10-09)

The harvest report of Task 27 of Satiety research 2 (2026-10-09), followed by its citation review. The review's corrections stand over the report wherever they disagree; the rows in docs/reference/science.tsv carry the corrected cells.

# Task 27 report: food-side and behavioural effects on hunger

Model: claude-opus-5-5. Harvest of 2026-10-09. The part file `27-science-part.tsv` holds 43 rows: 39 settled, 4 open and 0 unverified. Its dry run applies cleanly, and a full apply to a scratch copy of the register (minting S1337–S1379 there) passes `science_check.py` with 0 findings. `science_check.py --part` also reads 0.

**How citations were resolved.** Europe PMC's REST API was down for the whole session (502/503 errors and 30 s timeouts). Every abstract was read through PubMed E-utilities instead, whose records Europe PMC mirrors. Every DOI was then resolved through Crossref, and title, first author and year matched for all 38 distinct records. Crossref gives Boswell 2016 and Ferriday 2011 their online-first years (2015 and 2010); the rows carry the print year. Where only the abstract was readable, every number in the rows comes from it. Each full text I tried (Epstein 2011) was restricted to the abstract.

**The source cell.** The brief asks for "Satiety research 2, <topic> harvest (2026-10-09)", but `SOURCE_RX` requires `<x>.md § <heading>`. The rows therefore read `.superpowers/sdd/2026-10-09-satiety-research-2/27-report.md § Satiety research 2, food-side and behavioural effects harvest (2026-10-09)`. The controller may rewrite it uniformly across the seven parts.

No study cited here was already in the register; I grepped every author and title first.

## 1. Sensory-specific satiety, variety and monotony

| id | key value | grade | quality markers |
|---|---|---|---|
| S27.1 | variety in a meal raises intake, Hedges' g 0.405 (0.259–0.552) | MA | 30 studies (39 comparisons); I² 84%; risk of bias high; no GRADE |
| S27.2 | a four-course meal with a different food per course: +60% energy | EXP | one study, n 48 |
| S27.3 | the pleasantness drop peaks at 2 min; a second course at 60 min is eaten equally whether same or different | EXP | one study, small |
| S27.4 | sensory-specific satiety is keyed to taste (sweet or savoury) more than to fat; no BMI difference | EXP | n 44 |
| S27.5 | the same meal served daily: faster habituation and less intake than served weekly | RCT | n 32; no effect size in the abstract |
| S27.6 | the same lunch for 5 days: acceptance and intake fall; staples (potato) resist | EXP | n not given |
| S27.7 | weekly for 10 weeks: monotony raises boredom and lowers intake; free choice protects | EXP | N 105 |
| S27.8 | 15–22 days of daily chocolate: liking and desire fall, ad-libitum intake rises (dissociation) | RCT | N 29 and 53 |
| S27.9 | field rations as the sole food give low intake and weight loss; the same rations in a cafeteria give normal intake | TXT | programme review |
| S27.10 | daily meal-replacement bars over 30 days: lower intake, weight loss, worse mood; menu fatigue named | COH | analog missions |
| S27.11 | self-selected foods over 6–12 months: acceptability did not fall | COH | 15 astronauts |

**Verdict.**
- **Within a meal.** Variety raises intake by a small-to-medium standardised amount (g ≈ 0.4). Certainty is moderate for the direction and low for the size, because risk of bias is high and I² is 84% and unexplained.
- **How long sensory-specific satiety lasts.** The intake effect is short-lived. By 60 min a second course of the same food is eaten as freely as a different one (S27.3). That is one small study, so certainty is low.
- **Across days, liking.** Repeated daily exposure consistently lowers liking and desire. Certainty is moderate: five studies, every one in the same direction.
- **Across days, intake.** The effect on intake is inconsistent. Intake falls in S27.5, S27.6, S27.7 and S27.10; in S27.8 it does not fall with liking (the abstract does not split its rise in intake by group); and it holds in the cafeteria arm of S27.9. Certainty is low.
- **Free choice and staples.** Free choice among a few options (S27.7, S27.11) and staple foods (S27.6) blunt the decline.
- **What the weaker evidence over-reaches on.** The field claim that "monotony reduces intake" (S1329 and S27.9) is confounded by the eating context. The same rations are eaten normally in a cafeteria. So the field shortfall cannot be read as a monotony effect size.

## 2. Palatability

| id | key value | grade | quality markers |
|---|---|---|---|
| S27.12 | less pleasant and unpleasant soups: ad-libitum intake about 65% and 40% of the pleasant soup; no effect on later hunger or intake | EXP | within-subjects, N 35 |
| S27.13 | about 20% more of the food at hand is eaten when the next food is 90 rather than 15 min away | EXP | the same study, N 35 |
| S27.14 | about 100 g of intake per scale point of liking (9-point scale), within subjects | EXP | n not given |
| S27.15 | the preferred food raises desire to eat; hunger is higher 2 h after the preferred meal | EXP | n 12 |

**Verdict.**
- **Satiation.** Palatability changes satiation (how much is eaten at the meal) strongly: an unpleasant version is eaten at 40–65% of the pleasant amount. Certainty is low-to-moderate, from several consistent small experiments; no meta-analysis was found.
- **Satiety.** Palatability does not change satiety, meaning later hunger and intake (S27.12, N 35, measured by intake). Hill 1984 (S27.15, n 12, ratings only) reads higher hunger 2 h after the preferred food. The weight of evidence favours S27.12: it is larger and measures intake.

## 3. Spoilage, staleness and disgust

| id | key value | grade | quality markers |
|---|---|---|---|
| S27.16 | protein-source foods are prominent targets of learned food aversions | COH | survey; n not given |
| S27.17 | 15 h without food lowers the disgust response to unpalatable-food pictures | EXP | facial EMG; mechanism only |
| S27.18 | open: the effect of spoilage cues on intake, as an effect size | — | none found |
| S27.19 | open: how common and how lasting an aversion is after food-borne illness | — | Garb 1974 and Logue 1981 had no readable abstract |

**Verdict.** No controlled human study gives an intake effect size for stale, mouldy or off-smelling food, so certainty is very low. Two directions are supported:
- an illness after eating can teach a lasting aversion, with protein foods the most frequent targets;
- hunger blunts food disgust (mechanism only).

## 4. Meal frequency, regularity and breakfast

| id | key value | grade | quality markers |
|---|---|---|---|
| S27.20 | eating frequency: 8 of 13 intake studies and 11 of 17 anthropometric studies were null | MA | vote count; no pooling; 25 studies |
| S27.21 | six meals against three: hunger AUC 41850 against 36612 mm·24 h, desire 47061 against 41170 (P = 0.03) | RCT | crossover, n 15 |
| S27.22 | a preload as one meal against five nibbles: 26.6% more eaten at the next meal | EXP | n 8 |
| S27.23 | breakfast adds 259.79 kcal/d (78.87–440.71) | MA | 10 trials; I² 80%; low quality per the authors |
| S27.24 | breakfast: +539 kcal/d intake (157–920) and +442 kcal/d activity thermogenesis | RCT | n 33, 6 wk |
| S27.25 | skipping a 624 kcal breakfast: lunch +144 kcal, a net deficit of 408 kcal | RCT | crossovers; n not given |

**Verdict.**
- **Meal frequency.** The best estimate is no material effect on intake or appetite. The systematic review is mostly null, and Cameron 2010, read but not minted, was null over 8 weeks. Certainty is low.
- **The disagreement.** S27.21 (more hunger on six meals) and S27.22 (less intake after nibbling) point in opposite directions, and each is a small single trial. The evidence weight favours the null.
- **A skipped meal.** It is compensated incompletely. A skipped breakfast lowers daily intake by about 260 kcal (MA, low quality). In the cleanest crossover only about 23% of the skipped energy came back at lunch. Certainty is moderate for the direction.

## 5. The drive after a deficit: short fasts and starvation hyperphagia

| id | key value | grade | quality markers |
|---|---|---|---|
| S27.26 | a 36 h fast (about 12 MJ deficit): next day 12.2 against 10.2 MJ | EXP | crossover, n 24 |
| S27.27 | 24 h at 25% of requirement: +7% intake on day 2; day 3 not different | RCT | crossover, n 18 |
| S27.28 | anticipating restriction: +6% the day before, +14% at breakfast after; 46% of the deficit offset (intake and activity) | RCT | crossover, n 14 |
| S27.29 | Minnesota refeeding hyperphagia tracks fat recovery (r −0.6) and fat-free-mass recovery (r −0.5), independently | EXP | re-analysis, n 12 |
| S27.30 | after a 10% weight loss, VAS satiation is blunted; leptin replacement restores it | RCT | single-blind crossover, n 10 |
| S27.31 | open: the size and duration of ad-libitum refeeding hyperphagia | — | the Keys 1950 monograph was not resolved |

**Verdict.**
- **Acute deficits of 1–1.5 days** raise the next day's intake by only about 7–20% of a day's intake. That recovers about 15–25% of the deficit, and the effect is gone by day 3. Certainty is moderate: three crossovers agree.
- **Long deficits.** Hyperphagia after long semi-starvation is real and long-lasting (high certainty for the direction; S0060, S1254 and S1256 already in the register). It is driven by both lost fat and lost lean tissue (low certainty: one re-analysis, n 12). Its size in kcal/d is open.
- **What the weaker evidence says.** Lower-quality writing presents a one-day fast as a strong drive to overeat. The trials do not support that.

## 6. Social facilitation

| id | key value | grade | quality markers |
|---|---|---|---|
| S27.32 | eating with friends against alone: SMD 0.76 (0.48–1.03) | MA | 42 studies reviewed; k not given; no GRADE |
| S27.33 | eating with strangers or acquaintances against alone: SMD 0.21 (−0.10 to 0.51), not significant | MA | same review |
| S27.34 | free-living: meal size is a power function of the number present; large groups eat >75% more | COH | 153 adults, 3800 meals |
| S27.35 | eating with others breaks the link between meal size and the next intermeal interval | COH | 63 adults |

**Verdict.** Eating with familiar people raises intake by a moderate-to-large standardised amount; eating with strangers does not. Certainty is moderate: a meta-analysis, but with no GRADE rating. In two studies within the review (S27.32), the social effect was partly mediated by longer meal durations and the perceived appropriateness of eating, not by a change in physiology. The free-living ">75%" figure is observational and confounded by the type of occasion (feasts, restaurants).

## 7. Cue reactivity

| id | key value | grade | quality markers |
|---|---|---|---|
| S27.36 | cue reactivity and craving predict eating: r 0.33 | MA | 45 reports, 3,292 participants |
| S27.37 | 60 s of seeing and smelling food raises rated hunger, desire and salivation | EXP | n 104 |
| S27.38 | sniffing a food odour for 10 min: +11 to +12 mm appetite for that food, −7 mm for savoury; intake and general appetite unchanged | EXP | n 61 |

**Verdict.** Food cues raise rated appetite for the cued food quickly. The size is about 10 mm on a 100 mm scale for an odour (S27.38), with low certainty. Odour cues do not reliably raise intake: the odour trial was null, and the meta-analysis found olfactory cues weaker than visual ones. Cue reactivity predicts eating over time at r 0.33 (moderate certainty, trait-level).

## 8. Anything else with a solid evidence base

| id | key value | grade | quality markers |
|---|---|---|---|
| S27.39 | a larger portion, package or unit: SMD 0.38 (0.29–0.46); adults 0.46 | MA | 58 studies, 6,603 participants; **GRADE moderate** |
| S27.40 | portions 50% larger: +423 kcal/d, sustained for 11 days | EXP | crossover, n 23 |
| S27.41 | distraction while eating: later intake SMD 0.419 (0.195–0.642); concurrent intake not significant | MA | 50 studies (2026) |
| S27.42 | fat-free mass predicts the size of one meal, R² 0.46 | COH | n 191 |
| S27.43 | cold or cool drinks against warm during exercise: about 50% more drunk (ES 1.4) | MA | 5 studies pooled |

**Verdict.**
- **Portion size.** The portion-size effect is the best-graded finding of this harvest (GRADE moderate), and it does not wear off over 11 days.
- **Distraction.** It raises the next meal's intake, likely through weaker memory of the meal. Certainty is moderate.
- **Body size.** Lean mass sets meal size (moderate: one cohort plus a consistent research programme).
- **Drink temperature.** Cool drinks are drunk more, with low certainty because only five studies are pooled. This overlaps Task 24's food-temperature item.

## What the evidence says about the current model

**What it supports:**
- **P is unchanged by palatability, spoilage and variety (ruling 11c-27 feeds P from the eaten vector's kcal).** Palatability changes satiation, not later satiety (S27.12). The vanilla hunger divisors for stale (÷1.3) and rotten (÷2.2) food (#0031, #0032) have no physiological basis. Spoiled food delivers the same kcal (#0036), and no study shows that staleness lowers satiety per kcal. Feeding P from kcal therefore correctly ignores those divisors.
- **No meal-frequency term.** The evidence is mostly null (S27.20). The model's near-logarithmic read of P (STEEP 0.08) should still be checked, see below.
- **A modest deficit drive, and the 0.15 floor's label.** Short fasts are under-compensated (S27.26–S27.28), and chronic weight loss adds about 100 kcal/d per kg lost (S1254). Both fit a weak, slow energy-state term, not a strong same-day rebound.

**What it argues against, or should be checked as a replay.** None of these is a contradiction yet; each is a calibration target:
1. **The day after a fast.** After 36 h with no food, the next day's intake at the request level should be about 1.2× maintenance (12.2/10.2 MJ, S27.26). After a day at 25%, it should be about 1.07× (S27.27), back to 1.0× by the third day. If the energy-state term drives displayed hunger high enough that a player who missed a day eats much more than about 1.2× the next day, the model over-reacts. This can be tested in the oracle: replay a 36 h fast, then feed to the request.
2. **Grazing against meals.** On 2,000 kcal eaten as six isoenergetic meals against three, the 24 h mean displayed hunger should differ by no more than the 14% Ohkawara reports (41850/36612 = 1.14; S27.21). The null reading (S27.20) says less. Because the post read is concave in P, many small feeds could hold P lower on average. If the model gives grazing a much higher mean hunger than meals, it disagrees with both rows. The size is unknown until it is run.

**What the model leaves out:**
- **Monotony across days.** This has moderate certainty for liking and low certainty for intake.
  - *The evidence:* repeated daily exposure lowers liking and raises boredom. Daily exposure habituates while weekly exposure does not (S27.5), which gives a decay of the order of days. Staple foods resist, and free choice among a few options protects.
  - *Where it belongs:* the mood channel, not hunger. Vanilla already carries per-item `BoredomChange` and `UnhappyChange` (#0041–#0043).
  - *What the mod would read:* a per-player count of recent eats by food type, or by taste class (sweet against savoury, S27.4), decaying over about a week. It changes nothing in hunger or P.
  - *What it would change:* the Bored and Unhappy deltas at the eat, growing with repeats of the same type, with staples (bread, rice, potatoes, oats) exempt.
  - *Cost:* one table lookup per eat, so no per-tick work.
  - *Size:* no row gives a boredom-units slope, so the slope is a game choice resting on S27.5–S27.8.
- **Variety within a meal (sensory-specific satiety).** Moderate certainty; g 0.4; +60% over a four-course meal (S27.2).
  - The player sets the quantity eaten, so the only lever is fullness per kcal. The model would have to raise fullness for repeats of the same food within about an hour (S27.3).
  - This is hedonic, not physiological, so under the satiety-physiology charter it is better named as a non-reproduction than built.
- **The drive from lost lean tissue (S27.29).** Low certainty; correlation r −0.5.
  - The deficit drive could read lean-mass loss as well as fat or weight loss, if the body model tracks it.
  - No row gives a slope per kg of lean mass. Keep it open until one does.
- **Blunted satiation after weight loss (S27.30).** Mechanism plus VAS; the size is not given in the abstract. This is a candidate refinement: a lower FULL_WEIGHT after sustained weight loss. It is not shippable without a size.
- **Body size and meal size (S27.42).** Moderate certainty, R² 0.46. CAPACITY_MAX_G is one constant at present. A larger, leaner character eats bigger meals. The mod could scale capacity, or P_REQ, by the character's energy requirement or weight, which the mod already reads. The slope is not in the abstract.
- **Social facilitation (S27.32–S27.35).** Moderate certainty: SMD 0.76 with friends and none with strangers.
  - *Mechanism:* longer meals, not physiology. In free living, meal size stops predicting the gap to the next meal when eating with others (S27.35).
  - *Multiplayer reading:* a satiety change would have to read faction or friend players nearby at the eat, which is one query per eat.
  - *Recommendation:* name it as a non-reproduction, because the player sets the meal size and no physiological term exists to scale.
- **Cue reactivity (S27.37–S27.38).** Low certainty for intake. The effect is a brief +10 mm of appetite near food or cooking smells. Modelling it needs proximity scans on a cadence, which Rule 6 argues against for so small and brief an effect. Do not model it.
- **Anticipated scarcity (S27.13, S27.28).** People eat about 20% more of the food in front of them when the next food is 90 min away rather than 15, and about 6% more the day before a known restriction. This is a behavioural fact about players and needs no model term.
- **Portion size and distraction (S27.39–S27.41).** These are strong behavioural effects that the player's own choice already stands in for. No model term is needed.
- **Learned aversion after food poisoning (S27.16, S27.19 open).** The direction is supported but the size is not. A game could raise unhappiness when the food type that last caused FOOD_SICKNESS is eaten again. It is unevidenced in size.

## Slug requests and supersede candidates

**Slug.** No new slug is required. Two rows sit under `general`: S27.16 (learned aversion) and S27.17 (hunger lowers disgust). If the controller wants the hedonic rows off `satiety`, the optional slug would be `hedonics`, covering sensory-specific satiety, palatability, monotony, disgust and aversion. The reason: they measure liking and acceptance rather than meal-level satiation, and the monotony rows feed a mood mechanic, not hunger.

**Supersede candidates.** None of the existing rows is contradicted. Two are refined:
- **S1329** (IOM: underconsumption of rations in the field). S27.9 adds that the same rations are eaten normally in a cafeteria setting, so the shortfall is contextual. It should stand beside S1329, not supersede it.
- **S1336** (open: appetite under weeks of heavy labour with scarce or unpalatable food). It stays open. S27.9 and S27.10 bear on it but do not measure labourers.

## Concerns

- **Ohkawara's arm order.** The abstract lists the hunger AUCs without labels, then states that both were greater during six meals than three. S27.21 assigns the first figure to six meals on that sentence. A reviewer should check this against the full text, PMC4391809.
- **Sizes absent from the abstracts.** Several rows (S27.5, S27.6, S27.10, S27.30) carry the direction only, because the effect sizes are in full texts I could not read.
- **The open rows' sources.** The Keys 1950 monograph and Garb & Stunkard 1974 could not be read; they are the open rows S27.31 and S27.19.
- **Overlap with other tasks.** S27.43 (drink temperature) may overlap Task 24. S27.26–S27.28 (acute fasts) may overlap Task 26's states. Both are filed here because neither brief named them.

---

# Citation review

# Task 27 citation review (food-side and behavioural effects)

Model: claude-opus-5-5. Reviewer, read-only. 2026-10-09.

Verdict: FAIL (row-level fixes, no fabricated or unresolvable citation).

## Method
- All 38 distinct PMIDs fetched through PubMed E-utilities (Europe PMC REST returned 500); title, first author, year, journal, volume/pages, DOI and PMID matched for every settled row. Author diacritics (Hoefling, McNeil) are correct UTF-8 in the part file.
- Every value, range and population checked against the abstract. Full texts read: Ohkawara 2013 (PMC4391809, text and Figures 5-6), Embling 2021 (PMC7948867, children included).
- No cited PMID is already in science.tsv or in parts 22-26.
- `science_delta.py apply --dry-run` 43 rows; `science_check.py --part` 0 findings.

## S27.21 arm assignment
Confirmed. Ohkawara Figure 5 (hunger 24-h AUC bars): 3M about 36,600, 6M about 41,800. So 41850 and 47061 are the six-meal arm, and 36612 and 41170 the three-meal arm. The full text also gives the fullness AUCs: 3M 37,220 +/- 2,492 and 6M 34,261 +/- 2,447 mm-24 h, P = 0.22. The row is right but ambiguous: its parameter reads "three vs six" while the value lists the six-meal figure first (defect 2).

## Defects
1. S27.8, value. The abstract does not attribute experiment 2's rise in intake to the exposed groups. It reads "Pleasantness and desire to eat chocolate declined over time with this being more pronounced for F and V subjects. However, ad libitum intake increased over time". The row puts the rise in intake on the fixed and rising groups. That is the misread-baseline class of defect: the control group may share the rise. Corrected cell: `with 67 g/1473 kJ of chocolate daily for 22 days, pleasantness of taste and desire to eat chocolate declined significantly while bread and butter (95 g/1355 kJ daily) showed no such change; over 15 days, pleasantness and desire to eat chocolate declined over time, more so in the fixed and variable daily-chocolate groups than in controls given chocolate only on test days, while ad libitum intake increased over time (the abstract does not split the intake rise by group); neither experiment showed a decline in intake commensurate with the decline in pleasantness`
2. S27.21, value. The arm labels are implicit and run opposite to the parameter's order. Corrected cell: `hunger AUC 41850 +/- 2255 mm.24 h on six meals vs 36612 +/- 2556 on three, and desire-to-eat AUC 47061 +/- 1791 on six vs 41170 +/- 2574 on three (both P = 0.03; arm order confirmed against Figure 5 of the full text, PMC4391809); fullness AUC not different (37220 +/- 2492 on three vs 34261 +/- 2447 on six, P = 0.22); 24-h energy expenditure and fat oxidation not different`
3. S27.12, S27.13, S27.22, S27.26, S27.38 and S27.40, grade. science.md defines `RCT` to include "a controlled crossover", and the register grades all 23 of its crossover rows RCT. Each of these sources is a controlled crossover or within-subjects design:
   - S27.12 and S27.13: within-subjects repeated measures;
   - S27.22: a two-day crossover;
   - S27.26: a two-treatment crossover;
   - S27.38: a crossover with randomised order;
   - S27.40: two 11-day periods, each participant in both.
   `EXP` is reserved for a non-randomised depletion or dosing experiment. Corrected cell for each: `RCT`
4. S27.15, parameter. The rule in harvest-common says a disagreement is minted as two settled rows whose parameter names it. The report weighs S27.15 against S27.12 (§ 2), but neither parameter names that disagreement. Corrected cell: `hunger and desire to eat during and 2 h after small equicaloric meals of highly vs less preferred food (the reading that palatability raises later hunger, against De Graaf 1999)`
5. S27.36, population. "mixed adult samples" is not in the abstract, which names no age restriction; it reports only that age did not moderate. Corrected cell: `participants of 45 published reports (body mass index, age and dietary restraint did not moderate the effect)`
6. Report § 6 verdict. "The two reviews point to longer meals as the mechanism (S27.32)" misreads the source. Ruddock 2019 is one review, and it says "In 2 studies ... partly mediated by longer meal durations and the perceived appropriateness of eating". Corrected sentence: `In two studies within the review (S27.32), the social effect was partly mediated by longer meal durations and the perceived appropriateness of eating, not by a change in physiology.`
7. Report § 1 verdict, "Across days, intake", follows from defect 1. "but rises in S27.8" reads the rise in intake as an exposure effect. Corrected sentence: `The effect on intake is inconsistent. Intake falls in S27.5, S27.6, S27.7 and S27.10; in S27.8 it does not fall with liking (the abstract does not split its rise in intake by group); and it holds in the cafeteria arm of S27.9. Certainty is low.`

## Residuals (no correction dictated)
- **Designs the abstracts leave open.** The abstract does not settle the design of S27.2, S27.3, S27.4, S27.6, S27.14 or S27.15 (between-groups or within-subject crossover). EXP stands unless the controller reads the full texts.
- **Topic slugs.** S27.30 (Kissileff: obese adults after a 10% weight loss) is filed under `starvation`; `satiety` fits better, since its measure is satiation. S27.28 sits under `satiety` while its siblings S27.26 and S27.27 sit under `starvation`. This is a consistency call for the controller.
- **S27.22.** The source's own "26.6% more" does not match its own means: 5111/3752 is 36.2% more. The row correctly carries the source's figures. A reader should not recompute from them.
- **S27.20.** The vote counts (8 of 13, 11 of 17) mix human and animal studies. The population cell says so, but the report's verdict on meal frequency leans on it as if the counts were human only.
- **Report § 5, "recovers roughly 15-30% of the deficit".** The rows support about 17% (Johnstone: 2.0 of about 12 MJ) and about 23% from intake alone in James 2020 (260 + 223 of 2064 kcal). Clayton's share cannot be computed from the abstract, and nothing reaches 30%. "about 15-25%" is closer.
- **Report § 6, "only a few experimental studies per arm".** The abstract does not give k, so the rows do not support this phrase.
