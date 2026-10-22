# Plan 19 Task 4: the food hedonics harvest

Model: claude-opus-5-5. Harvested 2026-10-21 for the four hedonics rules of the Plan 19 spec (`docs/superpowers/specs/2026-10-21-dials-and-hedonics-design.md` § B.2), against the gaps the brainstorm's science read named (`.superpowers/sdd/plan-19-brainstorm/science.md` § 2, G1, G2, G4, G6, G8, G9, G12, G13).

Every citation was resolved against its record through Europe PMC (title, first author, year, journal, volume and pages matched) or Crossref (the two book records). A value was taken only from text read in this harvest: an abstract where that was all that was open, and the full text for Rolls 1981 (the SSIB "Ingestive Classics" copy of the journal PDF) and the IOM 1995 chapter (the National Academies reading page). A record whose text could not be read is an open row with the reason. No number below is the harvester's own arithmetic except where a cell says "ratio computed here".

The rules, for the mapping (spec § B.2):

- **R1** plain-energy unpalatability: the unpalatable-energy share of the last 24 online hours drives an unhappiness floor; a plain energy food is one with more than a threshold share of its energy from a single macro.
- **R2** cooking quality: a cooked or evolved dish's unhappiness relief scales with the cook's Cooking level.
- **R3** alliesthesia: a food's sad UnhappyChange is scaled down while the character is Hungry or above.
- **R4** monotony by taste class: the same-food floor also counts a taste class (sweet, savoury, fatty, bland staple).

## 1. Fat and sugar hedonics (R1)

**Drewnowski A, Greenwood MR 1983**, Physiol Behav 30:629-633, doi:10.1016/0031-9384(83)90232-9, pmid:6878464. Abstract read; the full text is not open.

- Sixteen normal-weight subjects rated 20 mixtures of milk, cream and sugar for sweetness, fatness, creaminess and overall pleasantness.
- Intensity rose as power functions of concentration, with no mixture suppression.
- Hedonic ratings first rose and then fell with increasing sucrose, but kept rising with dairy fat. Adding sucrose greatly enhanced the hedonic rating of high-fat stimuli.
- Overnight fasting did not change the perception or hedonics of sweet or fatty tastes.

Reading for R1: sugar has a hedonic optimum and is unpleasant past it; fat combined with sugar is the liked region. The study does **not** show plain fat is unpleasant: fat was always in a dairy liquid, and liking kept rising with it. "Plain fat eaten straight is grim" stays vanilla's own per-item value (Butter +20, oils +50), not a science magnitude. The optimum's location is in the full text, which was not read (open row).

Reading for R3: the fasting null is evidence **against** a hunger-driven rise in the pleasantness of sweet and fatty tastes after one overnight fast. It is paired with Cabanac below as a disagreement.

**Fazzino TL, Rohde K, Sullivan DK 2019**, Obesity 27:1761-1768, doi:10.1002/oby.22639, pmid:31689013. Abstract read.

- A quantitative definition of hyper-palatable foods, drawn from the literature's descriptive definitions, falls into three clusters: fat and sodium (more than 25 % of kcal from fat, at least 0.30 % sodium by weight); fat and simple sugars (more than 20 % of kcal from fat and more than 20 % from sugar); carbohydrates and sodium (more than 40 % of kcal from carbohydrate, at least 0.20 % sodium by weight).
- 62 % (4 795 of 7 757) of FNDDS foods met a criterion.

Reading for R1: palatability in this definition is a property of a **combination** of two components, never of one macro alone. That backs the rule's shape: a food whose energy is almost all one macro, with no pairing, falls outside every cluster. The thresholds are a definition, not a measured liking, so they back the classification's shape; the rule's own threshold (the spec's example 80 %) stays a game choice.

## 2. Sensory-specific satiety (R4, and a size bound for R3)

**Rolls BJ, Rolls ET, Rowe EA, Sweeney K 1981**, Physiol Behav 27:137-142, doi:10.1016/0031-9384(81)90310-3, pmid:7267792. Full text read.

- Experiment 1 (n 32): subjects rated the taste pleasantness of eight foods on a +2 (very pleasant) to -2 (very unpleasant) scale, ate one food to satiety for lunch (four per food), and re-rated at 2 and 20 min.
  - At 2 min the eaten food changed by -0.97 ± 0.12 (SEM) and the seven uneaten foods by -0.27 ± 0.05 (t(31) = 5.47, p < 0.001).
  - At 20 min the eaten food was still -0.83 ± 0.15 against -0.26 ± 0.05 (t(31) = 3.6, p < 0.001).
  - The effect held for seven of the eight foods; roast beef stayed pleasant.
- Experiment 2 (n 24): a first course of sausages or cheese on crackers, then an unexpected second course of the same or the other food.
  - Liking of the eaten food changed by -1.06 ± 0.18 against +0.01 ± 0.03 for the seven not eaten.
  - Second-course intake was 2937 ± 525 kJ when the food differed (n 8) against 1394 ± 323 kJ when it was the same (n 16), p < 0.01.
  - The change in liking correlated with second-course intake as a share of the first course, Spearman rho 0.68.
  - Eating sausages lowered the liking of chicken (another meat), and eating sausages or cheese on crackers tended to raise the liking of the sweet foods (cookies, raisins, bananas).
- The absolute rating of a food eaten to satiety fell to about indifferent: -0.33 ± 0.15 from 0.78 ± 0.13 before (Experiment 1) and 0.08 ± 0.19 from 1.06 ± 0.12 (Experiment 2). The authors suggest a food is eaten until it stops tasting pleasant, so eating stops before it becomes aversive.

Readings:

- **R4:** the drop is specific to the food eaten, about 3.6 times the drop of foods not eaten at 2 min (ratio computed here, 0.97 / 0.27), and it spreads to a similar food (meat to meat) while a different taste class (sweet) holds or rises. This backs keying monotony on a taste class beside the item. Within-meal SSS is short-lived (S1590), so this row backs the class key and the direction, not the across-day slope. The across-day rows are S1592 to S1595.
- **R4 and R1, a bound:** repetition brings a food to neutral, not to aversive. A monotony floor that takes a liked food past neutral into sadness has no support here. Where the floor makes the character sad, that comes from vanilla's pacing, not this row.
- **R3, a size anchor:** eating to satiety lowered the pleasantness of foods *not eaten* by about 0.27 points of a 4-point scale (about 7 % of the range, computed here). That is the non-specific, state-driven part. The inverse (how much hunger raises pleasantness) is not measured here.

## 3. Alliesthesia (R3)

**Cabanac M 1971**, Science 173:1103-1107, doi:10.1126/science.173.4002.1103, pmid:5098954. Abstract read; the full text is not open.

- A stimulus can feel pleasant or unpleasant depending on the subject's internal state. Cabanac names this alliesthesia and proposes it as an adequate motivation for food intake.
- No size is in the abstract.

**Cabanac M, Duclaux R 1970**, Science 168:496-497, doi:10.1126/science.168.3930.496, pmid:5436087. Abstract read.

- In normal subjects, ingesting glucose turned the sucrose taste from pleasant to unpleasant. In obese subjects it did not.

Readings for R3:

- **The direction (settled):** the internal state moves pleasantness, and repletion turns a sweet taste unpleasant (Cabanac and Duclaux 1970), beside S1604's facial-EMG reading after 15 h of fasting.
- **The disagreement:** Drewnowski 1983 found no effect of an overnight fast on sweet or fat hedonics. These are two settled rows; choosing between them is a ruling. The weight of the two: Cabanac's effect is between a glucose load and none, the post-load state, while Drewnowski's contrast is fasted against ordinary. So the evidence favours "repletion lowers pleasantness" over "hunger raises it". R3 as written (sad items ease when Hungry) is the hunger side, the weaker one.
- **No size:** no row gives a pleasantness-by-hunger curve. The R3 scale factor and the Hungry gate are game choices (an open row names the gap).

## 4. Cooked against raw, and cooking skill (R2)

**Wobber V, Hare B, Wrangham R 2008**, J Hum Evol 55:340-348, doi:10.1016/j.jhevol.2008.03.003, pmid:18486186. Abstract read.

- In preference tests with plant and animal foods, several captive great-ape populations tended to prefer food cooked over raw, with important exceptions.

**Koebnick C, Strassner C, Hoffmann I, Leitzmann C 1999**, Ann Nutr Metab 43:69-79, doi:10.1159/000012770, pmid:10436305. Abstract read.

- 513 long-term raw-food dieters (3.7 years; 216 men, 297 women) lost 9.9 kg (men) and 12 kg (women) on average from the start of the diet.
- BMI was below 18.5 in 14.7 % of men and 25.0 % of women, and weight was negatively related to the raw share and the duration.
- About 30 % of women under 45 had partial to complete amenorrhoea.

**Wolfson JA, Bleich SN 2015**, Public Health Nutr 18:1397-1406, doi:10.1017/S1368980014001943, pmid:25399031. Abstract read.

- NHANES 2007-2010, n 9 569 adults. Against households cooking dinner 0-1 times a week, those cooking 6-7 times ate fewer kilojoules (9 054 v. 9 627 kJ/d, P = 0.002), less fat (81 v. 86 g, P = 0.016) and less sugar (119 v. 135 g, P < 0.001).

**Hartmann C, Dohle S, Siegrist M 2013**, Appetite 65:125-131, doi:10.1016/j.appet.2013.01.016, pmid:23402717. Abstract read.

- Swiss Food Panel, n 4 436. Cooking enjoyment was the strongest predictor of cooking skill.
- Skill correlated positively with weekly vegetable intake and negatively with convenience food, holding health consciousness constant.

**Utter J, Denny S, Lucassen M, Dyson B 2016**, J Nutr Educ Behav 48:35-41.e1, doi:10.1016/j.jneb.2015.08.016, pmid:26411900. Abstract read.

- Youth'12, n 8 500 New Zealand secondary students. The greatest cooking ability went with meeting the fruit and vegetable advice (OR 2.1, 95 % CI 1.6-2.8), lower depressive symptoms (P < .01) and greater mental well-being (P < .01), and also with higher BMI (P < .01).

Readings for R2:

- That cooked food is preferred to raw has an animal-model direction (Wobber), and a raw diet's energy cost has a human cohort (Koebnick, energy and weight, not palatability). Vanilla's cooked flags and RemoveUnhappinessWhenCooked already carry this.
- Cooking skill goes with diet quality (Wolfson, Hartmann) and, in adolescents, with well-being (Utter). These are cross-sectional associations of the *cook's* traits and habits, not the eater's enjoyment of a dish by the cook's skill.
- **No row measures how much more a skilled cook's dish is enjoyed.** R2's direction is plausible and loosely backed (Utter's well-being, Hartmann's enjoyment and skill link). Its curve and size are game choices (an open row names the gap).

## 5. Ration monotony over days (R4)

**Kramer FM, Lesher LL, Meiselman HL 2001**, Appetite 36:239-240, doi:10.1006/appe.2001.0395, pmid:11358349. The record resolves (title, authors, year and pages match), but it is a two-page conference abstract with no abstract text in PubMed. The publisher page returned 403, and no open copy was found. Open row.

**Meiselman HL, Hirsch ES, Popper RD 1988.** A book chapter (in Thomson DMH, ed., *Food Acceptability*, Elsevier); no Europe PMC or Crossref record was resolved in this harvest. Open row.

**Meiselman HL 1995**, "Introduction to the concepts and issues underlying underconsumption of field rations", in Institute of Medicine, *Not Eating Enough*, National Academy Press, pp. 57-64, doi:10.17226/5002, isbn:9780309053419. Chapter text read on the National Academies reading page.

- A 34-day NRDEC field test fed 3 MREs a day (3 600 kcal offered). The MRE group ate 2 189 kcal a day on average, and intake declined continuously to 1 681 kcal at the end. Soldiers lost 3.7 kg (4.7 % of body weight, up to 11 %) and rated the food 7.05 on the 9-point hedonic scale (Hirsch et al 1985).
- MIT students fed 3 MREs a day for 45 days ate 3 149 kcal a day, declining over the 45 days. They lost 0.7 kg and rated the food 6.05 (Hirsch and Kramer 1993; Kramer et al 1992).
- The chapter attributes the 1 000 kcal gap to the eating situation, not to the food.

Reading for R4: on one repeated ration, intake declines over weeks in both settings. The level is set by context (S1596 already says so), so this row is a direction for a slow, across-weeks term, not a monotony slope. It does not back a mood size.

## 6. Neophobia (optional)

**Pliner P, Hobden K 1992**, Appetite 19:105-120, doi:10.1016/0195-6663(92)90014-W, pmid:1489209. Abstract read.

- A 10-item Food Neophobia Scale (reluctance to eat or avoidance of novel foods). It has satisfactory test-retest reliability and internal consistency, and it predicted food selection in three laboratory validations.
- Scores correlated with trait anxiety, age, experience seeking, general neophobia and familiarity with unusual foods, and not with gender.

Reading: no rule uses it. It is the trait counterweight to R4: a novel food is avoided, not favoured. A "novelty bonus" would have no support here.

## 7. Map: rule, dial, source

| rule | dial | settled source | direction | size |
|---|---|---|---|---|
| R1 | which foods count as plain (single-macro share threshold) | Fazzino 2019 (combinations define palatability); Drewnowski 1983 (sugar optimum, fat liked with sugar) | a pairing is palatable, a single component is not | game choice (the 80 % example) |
| R1 | the floor curve on the unpalatable-energy share | S1599 (40-65 % intake when unpleasant), S1601 | unpalatable food is eaten less | game choice for the mood size |
| R2 | preparation quality by Cooking level | Utter 2016 (ability and well-being, COH); Hartmann 2013; Wolfson 2015 (diet quality only); Wobber 2008 (cooked preferred) | more skill, more relief: loosely backed | game choice |
| R3 | the hunger scale factor on sad UnhappyChange | Cabanac 1971; Cabanac and Duclaux 1970; S1604; against Drewnowski 1983 (fasting null) | repletion lowers pleasantness (settled); hunger raises it (disputed) | game choice; Rolls 1981's -0.27 of 4 points for the non-specific drop is the one anchor |
| R3 | the gate (Hungry or above) | none | n/a | game choice |
| R4 | taste-class weight against item weight | Rolls 1981 (the eaten food drops about 3.6 times the uneaten; a similar food drops, the sweet class holds) | a class key is backed | the class weight is a game choice; the ratio is within one meal |
| R4 | the floor's ceiling | Rolls 1981 (a satiated food reaches neutral, not aversive) | monotony to neutral | bound: no science for taking a food below neutral |
| R4 | the across-day decay | S1592-S1595; Meiselman 1995 chapter (intake declines over 34-45 days) | slow, over days to weeks | game choice |

## 8. Gaps left open

- Kramer, Lesher and Meiselman 2001 (text not readable).
- Meiselman, Hirsch and Popper 1988 (record not resolved).
- The location of Drewnowski 1983's sugar-fat optimum (full text not read).
- The size of hunger's effect on pleasantness (no pleasantness-by-hunger curve read).
- Cooking skill against the eater's enjoyment of a dish (no study found).
