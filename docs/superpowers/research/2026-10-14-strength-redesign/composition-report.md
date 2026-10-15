# The fat share of weight lost: converting S1254 to per kg of fat (Plan 13 strength research, harvest 10)

Model: claude-opus-5-5. Written 2026-10-15, read-only. Every record was resolved on Europe PMC by PMID and DOI (title, first author and year matched). Each number in the part file was read in the record's abstract or in its open full text: Polidori 2016 on PMC5108589; McCrimmon 2020 on PMC6997246; Jobanputra 2026 on PMC13282017; Heymsfield 2014 on PMC3970209; Jahangiri 2023 on PMC10597985. The part file is `.superpowers/sdd/strength-research/composition-part.tsv` (S10.1 to S10.10). `science_check.py --part` reports 0 findings on it.

## Why

S1254 (Polidori 2016) gives the appetite feedback as about 100 kcal/day per kg of body weight lost. The mod's low-fat hunger term reads fat depletion, so the oracle needs the gain per kg of fat. The conversion divides by the fat share of the weight lost:

    kcal/day per kg of fat lost = (kcal/day per kg of weight lost) / (fat share of weight lost)

## § 1. Canagliflozin and SGLT2 inhibitor DXA

| Row | Source | Arm, time | Fat share of the loss | Per kg fat (from 100) |
|---|---|---|---|---|
| S10.1 | McCrimmon 2020, SUSTAIN 8 DXA substudy | canagliflozin 300 mg, 52 wk | 2.6 / (2.6 + 1.5) = **0.63** | 158 |
| S10.2 | Jobanputra 2026, meta-analysis | SGLT2i, pooled (15 trials) | 1 − 0.21 = 0.79 (CI 0.67 to 0.91) | 127 (110 to 149) |
| S10.3 | Bolinder 2012 | dapagliflozin 10 mg, 24 wk, placebo-corrected | 1.48 / 2.08 = 0.71 | 141 |
| S10.4 | Bolinder 2014 | dapagliflozin 10 mg, 102 wk, within arm | 2.80 / 4.54 = 0.62 | 162 |
| S10.5 | Jahangiri 2023, tabulating Blonde 2016 | canagliflozin 100 / 300 mg, 26 wk, older adults | 1.9/2.5 = 0.76 and 2.4/3.2 = 0.75, fat over weight lost | 132 / 133 |
| S10.6 | Cefalu 2013, CANTATA-SU | DXA substudy | open: the primary is paywalled | — |

The shares are divisions of the reported means. The divisions are my own and the means are the sources'. None of the papers reports a share with its own CI, except the meta-analysis (S10.2).

- **S10.1 is the closest match to Polidori's population.** It uses the same drug and dose (canagliflozin 300 mg) and the same duration (52 weeks). Its arm is near-identical: body weight 87.6 kg against Polidori's 87 kg, BMI 32.3 against 32, age 58.6 against 55, all with type 2 diabetes. Its weakness is that it has no placebo arm. The share comes from the treated arm's own change, which matches how Polidori fits k_P (to the treated arm's weight course). The denominator is fat plus lean mass, so bone mineral content is excluded. The authors give the total as 4.1 kg against a whole-trial weight loss of 4.2 kg.
- **Lean change is lean, not muscle.** DXA lean mass includes water and glycogen. Early weight loss on SGLT2 inhibitors includes some fluid from osmotic diuresis. At 52 weeks, part of the "lean" loss is therefore likely water, not tissue. This pushes the measured fat share down relative to a tissue-only share (inference: no register row backs the osmotic-water claim).
- **The dapagliflozin arms bracket the canagliflozin reading.** Bolinder 2014 at 102 weeks, within arm, gives 0.62. Bolinder 2012 at 24 weeks, placebo-corrected, gives 0.71. These rows are a related population, and they are clear enough to stand as rows.
- **CANTATA-SU (Cefalu 2013): no primary body-composition reading.** The "about two thirds fat" figure in the brief appears only on the manufacturer's medical-information page. That page states "~2/3 … fat mass and ~1/3 from total lean mass, including water" across the CANTATA-SU and older-adult DXA studies. It cites a 2012 congress abstract (Toubro) that has no resolvable record. The Lancet paper's abstract has no body-composition number. S10.6 is therefore filed `open`. The older-adult study's 26-week numbers (S10.5, from a review's table) read 0.75 to 0.76 of the weight lost (fat over weight lost), above "two thirds". The same review's Table 3 gives CANTATA-SU at 52 weeks (S10.6's population cell): weight -4.4 / -4.2 kg and fat-free mass -0.9 / -1.1 kg, a fat share of about 0.74-0.80 by complement from a table whose baselines do not add up. It weighs against 0.63 as the centre.

## § 2. The general rule

- **S10.7, the Quarter FFM Rule.** It says about 0.25 of weight lost is fat-free mass and 0.75 is fat. Heymsfield 2014 traces it to Webster 1984, where the excess weight of obese women was 0.22 lean and 0.78 fat, and concludes the rule "is at best an approximation that has a limited mechanistic basis". S2051 already holds the rule and its origin. The review's cross-sectional mid-range estimates of dFFM/dW are 0.37 for men and 0.32 for women.
- **S10.8, the Forbes curve.** FFM = 10.4 ln(FM) + 14.2, so dFFM/dW = 10.4 / (10.4 + FM). The fat share of a small change is therefore FM / (FM + 10.4), and the fatter the start, the larger the fat share. This extends S0054 and S0055, which give only the direction of the effect. S1056 is the open row for a fitted coefficient; S10.8's 10.4 kg constant may serve it, and the controller can rule on that.
- **S10.9, measured diet-induced loss.** Chaston 2007 (as reported in Heymsfield 2014) found dFFM/dW of 27 ± 7 % in men and 20 ± 7 % in women. That gives fat shares of 0.73 and 0.80. Harder restriction raised the FFM share. The exercise trials (0.27 sedentary against 0.13 and 0.17 with exercise) are S2052.

At the SUSTAIN 8 canagliflozin arm's measured starting fat mass of 32.5 kg (S10.1), the Forbes share is 32.5 / 42.9 = **0.76**. This is the same as the quarter rule's 0.75.

## § 3. Polidori 2016's text

- **No composition was measured.** Polidori analysed 153 completers on canagliflozin 300 mg in the 52-week placebo-controlled CANTATA-M monotherapy trial (Stenlöf 2014). The paper reports no DXA or any other body-composition measure.
- **The model partitions with Forbes.** The weight change is split by α = dFFM/dFM = C/FM, with C = 10.4 kg and FM held at its initial value. The energy densities are ρ_FM = 9300 kcal/kg and ρ_FFM = 1100 kcal/kg, and β = 0.24 (S10.10). Each subject's initial FM was estimated by the model from baseline characteristics and is not reported.
- **The fitted gain is k_P = 95 kcal/day per kg of body weight.** The abstract rounds it to "~100". The feedback equation, ΔEI = −k_P × ΔBW, is written on body weight, not on fat.
- **The share implicit in the model is the Forbes share.** At this population's likely fat mass it is about 0.76, using the SUSTAIN 8 arm's 32.5 kg as a proxy. Polidori's own FM₀ is unreported, so this is inference.

## The conversion

| Fat share used | Basis | kcal/d per kg fat (k = 100) | (k_P = 95) |
|---|---|---|---|
| **0.63** | **S10.1, measured, same drug, dose, duration and population** | **158** | **150** |
| 0.62 to 0.71 | S10.3, S10.4, dapagliflozin DXA | 141 to 162 | 134 to 154 |
| 0.75 to 0.76 | S10.5, canagliflozin 26 wk, older adults | 132 to 133 | 125 to 127 |
| 0.79 (0.67 to 0.91) | S10.2, SGLT2i meta-analysis | 127 (110 to 149) | 120 (104 to 142) |
| 0.75 to 0.76 | S10.7 quarter rule; S10.8 Forbes at FM 32.5 kg (the share Polidori's model assumes) | 132 to 133 | 125 to 127 |

**Recommendation.** Use a fat share of **0.63** (S10.1). The per-kg-fat target is then **about 160 kcal/day per kg of fat lost**: 158 from "~100", or 150 from the fitted k_P = 95. The measured SGLT2-inhibitor range is 0.62 to 0.79 (S10.1 to S10.5; with S10.5 corrected the canagliflozin readings span 0.63 to 0.80, and 0.63 is the low end of that span, not its centre), which gives **127 to 162**. The meta-analysis CI widens this to 110 to 162.

The controller's ruling converts with Polidori's own Forbes share, 0.76 (S10.10, S10.8), giving 95/0.76 = 125 kcal/d per kg of fat; the canagliflozin readings span about 125-160.

Two cautions for the controller's ruling:

1. **The measured share and Polidori's model disagree.** The measured DXA share (0.63) counts water lost from lean mass as non-fat. Polidori's model assumes the Forbes share (about 0.76). Converting with 0.76 instead gives about 132 kcal/day per kg of fat. The controller's ruling names the measured composition, which is 0.63. If the oracle's fat state is tissue fat and the lean loss is partly water, the true tissue share lies between the two.
2. **The pooled share is more fat-heavy than the single arm.** The SGLT2i meta-analysis (0.79) pools 15 trials with mixed methods (DXA, BIA, MRI). That makes it the broadest evidence but a looser match to Polidori's drug and dose.

## Gaps

- **CANTATA-SU's DXA arm numbers (S10.6)** are unread. The Lancet full text, or the FDA 2013 briefing document for canagliflozin, would settle them.
- **Blonde 2016's primary text** was not read; S10.5 rests on Jahangiri 2023's table. The review also mislabels the substudy in its prose, which is noted in the row.
- **Polidori's per-subject initial fat mass** is not reported, so the Forbes share implicit in S1254 can only be estimated from a proxy population.
