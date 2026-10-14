# A small surplus against maintenance in trained lifters

Harvested on 2026-10-14 by `claude-opus-5-5`, read-only. Every citation was resolved by PMID through NCBI E-utilities. Full texts were read through PMC (efetch XML, or the PMC page) where they are open. Barakat 2020 was read through Ovid, where it is open under CC BY-NC-ND. Where only an abstract was read, the row says so.

The rows are in `surplus-part.tsv` (provisional ids S5.1 to S5.30). Rows already in the register are cited by their ids: Helms 2023 S1943 and S2033, Garthe 2013 S1944, Rozenek 2002 S1945, Murphy & Koehler 2022 S1942, Iraki 2019 S1946, Slater 2019 S1947, Areta 2014 S1995, Murphy & Koehler 2020 S1996, Moro 2016 S2018, Isola 2023 S2019, Smith 2021 S2035, Blake 2025 S2036, Gavanda 2026 S2037, Spillane 2016 S2034, Bone 2017 S2039, Haun 2019 S2042, Hatamoto 2024 S0606, Forbes S0054 and S0055, Trexler 2017 S1926, and McDonald S1929.

Arithmetic labelled "computed here" is mine and appears in no row.

## 1. Direct trials in trained lifters

### Helms 2023, re-read in full (S1943, S2033; new S5.1, S5.2)

**There are no effect sizes or credible intervals for the arm contrasts.**
- The paper reports Bayes factors for a group model against the null (Table 6), and group change scores as mean ± SD (Table 1).
- The Statistics section says data are "means ± 95% credible interval … unless otherwise specified", but Table 1 is labelled mean ± SD.
- No between-arm difference, standardised effect or interval is given for any muscle-thickness site.
- Helms 2023 measured no lean mass: no DXA, no BIA, no 4C.

**The group-model BF10 for muscle thickness was below 1 at every site:**

| Site | BF10 |
|---|---|
| vastus lateralis | 0.35 |
| lateral VI | 0.32 |
| anterior VI | 0.33 |
| rectus femoris | 0.77 |
| triceps | 0.52 |
| biceps | 0.35 |

**Per-arm changes in cm (Table 1, mean ± SD):**

| Site | MAIN | MOD ("+5 %") | HIGH ("+15 %") | MOD − MAIN, computed here | HIGH − MAIN, computed here |
|---|---|---|---|---|---|
| VL | 0.05 ± 0.24 | 0.14 ± 0.16 | 0.11 ± 0.21 | +0.09 | +0.06 |
| lateral VI | 0.03 ± 0.30 | 0.02 ± 0.13 | −0.04 ± 0.19 | −0.01 | −0.07 |
| anterior VI | 0.26 ± 0.62 | 0.26 ± 0.28 | 0.11 ± 0.35 | 0.00 | −0.15 |
| RF | −0.22 ± 0.56 | 0.15 ± 0.16 | −0.21 ± 0.26 | +0.37 | +0.01 |
| triceps | 0.08 ± 0.39 | −0.25 ± 0.57 | 0.11 ± 0.37 | −0.33 | +0.03 |
| biceps | 0.25 ± 0.37 | 0.19 ± 0.10 | 0.34 ± 0.54 | −0.06 | +0.09 |

- Across the six sites, the MOD − MAIN differences run from −0.33 to +0.37 cm, with no consistent sign. The HIGH − MAIN differences run from −0.15 to +0.09 cm.
- The within-arm SDs (0.10-0.62 cm, n = 5-6) are several times the differences.
- Nothing here measures a +5 %-against-maintenance effect.

**The "+5 %" arm was not a 5 % surplus (S5.1, Table 2).**
- Self-reported intake rose from its own maintenance phase by:
  - MAIN: +169 ± 205 kcal/d (2358 to 2527);
  - MOD: +489 ± 184 (2645 to 3135);
  - HIGH: +719 ± 189 (2535 to 3253).
- Computed here, that is about +7 %, +18 % and +28 % over each arm's own maintenance-phase intake.
- MOD and HIGH both gained 3.3 kg, about 0.5 % of body mass a week (computed here). MOD's target was 0.4-0.6 % per two weeks.
- The discussion concedes this: "both MOD and HIGH, on average, were in a similar energy surplus … a prescribed 5% surplus is too small to be logistically feasible for most participants, on average, and in practice becomes a larger surplus."
- **Helms 2023 is therefore a maintenance-against-moderate-to-large-surplus trial.** It contains no small-surplus arm.

**The regression on body-mass change** was the authors' post hoc rescue after the COVID shortfall:
- biceps thickness: BF10 1.4, R² 0.24;
- every other site: BF10 0.43-0.63;
- skinfolds: BF10 14.3, R² 0.49.

The authors speculate that "hypertrophy can only be augmented by an energy surplus when the stimulus for a given muscle is sufficiently potent". The biceps got 18 sets a week; the quadriceps got 9.

### Henselmans 2026: the most trained cohort in any surplus contrast (new; S5.3, S5.4)

**Design.**
- Population: 20 resistance-trained men with **9.7 ± 6.1 y of training**, squat 1.9 ± 0.4 × body mass, BMI 26.7 ± 2.7.
- Arms: a daily protein-only supplement (30 g protein, 4 g carbohydrate) against protein plus carbohydrate (30 g protein, 54 g carbohydrate), 8 wk each.
- A quasi-randomised (alternating), double-blinded, counterbalanced crossover. Participants kept their habitual training and diet.
- Volume load did not differ: 14 quadriceps and 18 elbow-flexor sets a week.
- Measures:
  - DXA lean mass (SEM 0.36 kg);
  - ultrasound thickness of the lateral thigh (SEM 0.12 cm) and elbow flexors (SEM 0.06 cm);
  - panoramic vastus lateralis CSA (SEM 0.5 cm²).
- Each was analysed by linear mixed models, with first-period ANCOVAs as a sensitivity check.

**The energy contrast it achieved:**
- +485 kcal/d by self-report (95 % CI 99 to 871; 2751 ± 645 against 2266 ± 672 kcal/d);
- carbohydrate +33 g/d (1 to 65);
- **the Atwater sum of the reported macronutrients differed by only 251 kcal/d**;
- protein 178 against 173 g/d.

The true contrast is somewhere between about 250 and 485 kcal/d. Computed here, that is roughly 9-18 % of the carbohydrate condition's reported intake. Whether either condition was a surplus against true maintenance is unknown: both are habitual diets.

**Outcomes (CHO − PRO, estimated marginal means, 95 % CI):**

| Outcome | PRO | CHO | Difference (95 % CI) | p |
|---|---|---|---|---|
| DXA lean mass (kg) | −0.20 ± 0.33 | +0.55 ± 0.33 | **+0.76 (−0.19 to 1.69)** | 0.109 |
| fat mass (kg) | +0.33 ± 0.24 | +0.48 ± 0.23 | +0.15 (−0.42 to 0.71) | 0.588 |
| elbow-flexor thickness (cm) | −0.05 | +0.03 | +0.05 (−0.09 to 0.19) | 0.484 |
| lateral-thigh thickness (cm) | −0.05 | −0.02 | +0.03 (−0.27 to 0.31) | 0.805 |
| VL CSA (cm²) | +1.82 | +1.36 | −0.45 (−3.40 to 2.49) | 0.751 |
| squat 1RM (kg) | +5.24 | +6.77 | +1.53 (−3.52 to 6.57) | 0.534 |

**Reading:**
- This is the only trial with a direct muscle measure in lifters of about 10 years' training that contrasts more energy against less at a small margin. The margin is the one the owner means.
- The DXA lean point estimate favours the extra energy by 0.76 kg in 8 weeks, with an interval from a small loss to a large gain.
- The direct muscle measures sit at zero with intervals of about ±0.1-0.3 cm. The VL CSA leans the other way.
- Some of the DXA difference is expected to be glycogen and its water, since the extra energy was carbohydrate (Bone 2017, S2039: glycogen loading alone moves DXA lean 2-3 %).
- On habitual intake (the PRO arm), these trained men gained no lean mass and no muscle thickness in 8 weeks. That is a within-condition change, not a contrast.

### Other trials

**Sanchez 2024 (S5.5).**
- Population: 32 athletes (19 M, 13 F), all given +500 kcal/d of extra food, with supervised resistance training 3 d/wk for 10 wk.
- Result: total body mass +2.2 ± 1.3 kg, of which DXA lean +1.5 ± 1.1 kg.
- The two snack types differed in weight gain (1.6 against 2.7 kg) but not in lean gain (1.2 against 1.9 kg, p = 0.136).
- There is no maintenance arm, so it is not a surplus-against-balance contrast. It says only that +500 kcal with training in athletes put most of the DXA-measured gain into lean.

**Hambre 2012 (S5.6).**
- Population: 24 untrained men, 12 wk of training.
- Arms: an extra 1350 kcal fast-food meal a day against 33 g whey a day.
- Result: body weight 75.1 to 78.7 kg and DXA lean 59.7 to 61.8 kg overall, "without differences between the groups".
- The fast-food arm did not gain more weight, so its intended surplus was probably compensated. This is weak evidence and untrained.

**Garthe 2013, the lean numbers (S5.7, S5.8; S1944 is the abstract).**
- The full text is paywalled. Two secondary reports give its numbers:
  - Iraki 2019 (PMC full text): the counselled-surplus group's LBM gain was larger but "failed to reach statistical significance (1.7 kg vs. 1.2 kg, respectively)", with fat mass +1.1 against +0.2 kg. "The researchers concluded that a 200–300 kcal per day surplus in highly trained athletes might be more appropriate than 500 kcal."
  - Aragon 2017 (ISSN position stand): the counselled group ate 3585 kcal/d, "544 kcal increase from baseline intake", against 2964 kcal/d in the ad libitum group, "128 kcal decrease from baseline".
- Ribeiro 2019's lower-body split (0.5 against 0.0 kg, in the previous harvest) is a different reading of the same trial.
- Baseline training status is not reported by subgroup in any source I could read. The population is elite athletes from mixed sports adding four strength sessions a week.

**Rozenek 2002 (S1945)** is untrained and has nothing to add. Its supplements were +2010 kcal/d and both groups' protein rose.

**Registered trials, not re-read:** Blake 2025 (S2036), Gavanda 2026 (S2037), Spillane 2016 (S2034), Smith 2021 (S2035) and Ribeiro 2019 (S2032) are covered in the previous harvest.

The pattern over every trained surplus contrast found:

| Trial | Training | Energy contrast | Lean (whole-body) | Muscle-specific |
|---|---|---|---|---|
| Henselmans 2026 | 9.7 y | +250 to +485 kcal/d over habitual | DXA LM **+0.76 kg (−0.19, 1.69)**, 8 wk | thickness +0.03 to +0.05 cm, CSA −0.45 cm², all CIs across 0 |
| Garthe 2013 (via Iraki, Aragon) | elite, non-lifters | about +670 kcal/d between arms | LBM +1.7 vs +1.2 kg n.s., 8-12 wk | none |
| Helms 2023 | ≥ 1 y, intermediate | about +320 (MOD) and +550 (HIGH) kcal/d over MAIN's reported rise | none measured | sites −0.33 to +0.37 cm, no consistent sign |
| Gavanda 2026 (S2037) | trained | the time-restricted arm ate about 15 % under a 300-500 kcal target | FFM +1.34 vs +1.38 kg (BIA) | none |
| Spillane 2016 (S2034) | trained | two overfeeding arms, no control | lean n.s. (p = 0.068) | none |

The between-arm contrasts for Garthe (544 kcal up against 128 kcal down from baseline, S5.8), Henselmans (the Atwater and self-report bounds) and Helms (each surplus arm's reported intake rise less MAIN's +169) are computed here from S5.1 and S5.4.

In every case:
- the whole-body lean point estimate is equal or a little larger with more energy (+0.5 and +0.76 kg in the two trials that report one);
- the confidence intervals include zero;
- the direct muscle measures show nothing;
- fat goes up with the surplus whenever weight goes up.

## 2. Meta-analyses

**Murphy & Koehler 2022 (S1942).**
- The full text could not be read: the Wiley PDF returned 403, mediaTUM sits behind a bot wall, and the Unpaywall link is a Wiley "pdfdirect" that is also blocked.
- The abstract's meta-regression is of lean mass on "the magnitude of the energy deficit". Analysis A compares a deficit with a "parallel control group without an energy deficit". The abstract says nothing of a surplus.
- Whether any pooled study had a surplus arm, and whether the regression line was extrapolated above balance, is not readable. It is filed as open row S5.28.
- A secondary interview (mysportscience.com, Koehler quoted) says "resistance training at energy balance always led to gains in lean mass". That is not the record and is not filed.

**No meta-analysis of a surplus against balance** in trained or untrained lifters was found. The searches were PubMed 2019-2026 for energy surplus, hypercaloric, overfeeding or bulking with resistance training and hypertrophy, lean mass or muscle thickness, plus "Pelland energy". Pelland 2024/2026 (S1951) reports no energy moderator.

**Benito 2020 (S1923, S1924)** pools resistance-training trials by training status and has no energy term.

The meta-analytic evidence is entirely about the deficit side.

## 3. Mechanism

### 3.1 How much energy new muscle needs, and whether fat can supply it

**Composition and stored energy.** Slater 2019 (S5.9), with Barakat 2020's composition agreeing:
- skeletal muscle is about "75% water, 20% protein, and 5% fat, glycogen and other minerals and metabolites";
- "the energy stored in 1 kg of muscle is ~5,000–5,200 kJ, with ~3,400 kJ from protein, ~1,400–1,500 kJ from fat, and ~300–450 kJ from muscle glycogen".

**Deposition cost, energy stored plus synthesis** (Slater 2019, S5.9):
- Forbes's figure: "the energy cost of depositing 1 kg of SMM was 7,440 kJ·kg⁻¹";
- from Joosen & Westerterp's 29.4 kJ/g protein: about 6,050 kJ/kg;
- translation alone: "4 high energy phosphate bonds per peptide bond … or 3.6 kJ·g⁻¹ of protein synthesized".

**Hall 2008's model densities (S5.11)**, which settle the open row S0126 in part:
- lean-mass change ρL = 7.6 MJ/kg, with an assumed hydration of 1.6 g water per g protein;
- fat change ρF = 39.5 MJ/kg;
- glycogen 17.6, protein 19.7 and fat 39.5 MJ/kg.

ρL is a model value for lean change, not for wet muscle. It is close to Forbes's deposition cost by coincidence, not by definition.

**What that costs a day** (computed here, at 7440 kJ/kg, about 1780 kcal/kg, the spec's RHO_LEAN of 1816 being about the same):

| Rate of muscle gain | Cost |
|---|---|
| McDonald year 1, 9-11 kg/yr (S1929) | about 45-55 kcal/d |
| McDonald year 3, 2.3-2.7 kg/yr | about 11-13 kcal/d |
| McDonald year 4, 0.9-1.4 kg/yr | about 4-7 kcal/d |
| Henselmans's framing: "even a kilo of muscle per month … less than 100 kcal per day" | about 59 kcal/d at this density |

**Can a lean lifter's fat pay for it?** Computed here:
- an 80 kg lifter at 10 % body fat carries 8 kg of fat, about 75 000 kcal;
- a year of advanced gain (2 kg at about 1780 kcal/kg) costs about 3600 kcal, roughly 0.4 kg of fat.

**Energy as substrate is never limiting for a trained lifter.** Even a novice's whole first year costs about 2 kg of fat. A surplus, if it helps, cannot help by supplying the building material. It can only help through the anabolic signal (§ 3.2) or by preventing the leanness penalty that weight-stable recomposition eventually meets (§ 3.4).

Slater 2019 says the same in its own words: "To date, the authors are not aware of any studies that have clearly demonstrated a consistent energy cost of tissue accumulation". Its recommended surplus rests on the stored-energy arithmetic plus caution (§ 5).

### 3.2 Energy status and muscle protein synthesis

**Deficit against balance (well measured):**
- Areta 2014 (S1995): postabsorptive MPS 27 % lower at 30 than at 45 kcal/kg FFM/d. A resistance bout restored it to rested-balance rates, and protein after the bout raised it above.
- Pasiakos 2010 (S5.16): 10 d at about 80 % of energy needs with protein held at 1.5 g/kg. Mixed-muscle FSR 0.06 ± 0.01 against 0.074 ± 0.01 %/h, "reduced approximately 19%", with Akt and 4E-BP1 phosphorylation lower. The population was physically active adults, not lifters.

**Surplus against balance (one study, untrained, whole-body, not muscle):**
- Welle 1989 (S5.15): 10 d of carbohydrate overfeeding (+1600 kcal/d) in 11 untrained men.
  - Urinary nitrogen fell 27 % against weight maintenance, so protein was accreted.
  - The postabsorptive whole-body synthesis index (leucine flux minus oxidation) rose 12 ± 3 %.
  - Insulin, glucagon and T3 each rose about 20 %.
- No study was found that measures myofibrillar FSR at a surplus against balance in trained people. Open row S5.29.

**Insulin, the main carrier of an energy surplus's anabolic signal, is permissive and not additive once amino acids are supplied:**
- Abdulla 2016 meta-analysis (S5.17): insulin infusion did not change MPS overall (WMD 3.90, 95 % CI −0.74 to 8.55). It raised MPS only when amino-acid availability rose, and it lowered breakdown (WMD −15.46, −19.74 to −11.18).
- Trommelen 2015 (S5.21), a systematic review: "exogenous insulin administered systemically does not increase muscle protein synthesis in healthy, young adults"; the rise seen with insulin plus amino acids "is attributed to the hyperaminoacidemia".
- Bell 2005 (S5.18): a high-energy clamp (162 kcal/h) that lowered blood amino acids left MPS unchanged (39 ± 6 to 30 ± 7). "decreased blood amino acid concentrations override the positive effect of insulin on muscle protein synthesis even if excess energy is provided."

For a lifter already at 1.6-2.2 g/kg of protein, the extra insulin of a small surplus adds, at most, a little anti-proteolysis.

### 3.3 Hormones and glycogen

**IGF-1 and testosterone.**
- Forbes 1989 (S5.14): 3 wk of mixed-diet overfeeding in untrained women raised plasma IGF-1, testosterone and insulin. 46 % of the 4.3 kg gain was LBM. The authors propose the three hormones' "combined anabolic effect" as the cause.
- The deficit side is measured in trained people:
  - Murphy & Koehler 2020 (S1996): IGF-1 falls under 3 d of restriction in lifters with 6 y of training;
  - Isola 2025 (S5.27): IGF-1 fell in competing physique athletes, and "Decreases in IGF-1 were also associated with higher loss in FFM".
- No surplus-against-balance hormone study in trained lifters was found.

**Glycogen.**
- Camera 2012 (S5.19): starting resistance exercise with low muscle glycogen did not lower the anabolic signal or 4-h myofibrillar MPS (nutrient 0.070 ± 0.022 against 0.068 ± 0.018 %/h).
- So a surplus's fuller glycogen stores are not, on this evidence, an anabolic signal.
- What they do is raise DXA lean (S2039), which inflates every DXA "lean gain" in a carbohydrate surplus.

### 3.4 The Forbes partition in lean people

- Forbes 2000 (S5.13): in overfeeding experiments of at least 3 weeks, "the weight gain of thin people comprises 60-70% lean tissues, whereas in the obese it is 30-40%".
- Forbes 1986 (S5.12): pooled 48 overfed adults, with an energy cost of 33.7 kJ/g gained and 43.6 % of the gain as LBM by means (38.4 % by regression).
- These are untrained, mostly non-exercising subjects.

**What that implies for a lean lifter in a surplus:**
- The Forbes share predicts a large lean fraction of any surplus.
- The trained trials (§ 1) show the extra weight going to fat, not to measured muscle: Helms skinfolds, Garthe fat mass, Gavanda.
- **Inference:** in trained lifters, the Forbes lean share of a surplus is mostly non-contractile lean. That is organ, water, glycogen and connective tissue, which is the spec's labile `lx`. The contractile part is capped by the training-limited growth term, not by energy.
- The spec already carries this split (§ 5.1). The evidence here supports it.

**Weight-stable recomposition and its limit.** At balance, a lifter who gains muscle must lose fat. Computed here, that is about 0.19 kg of fat per kg of muscle at the densities above. Over years at a fixed intake, a lean lifter drifts leaner and meets the Forbes and Alpert penalties of § 3 of the previous harvest. A slight surplus keeps fat level while muscle grows.

**This is the strongest mechanistic form of the owner's argument.** It is not that a surplus feeds the muscle. It is that a surplus stops slow recomposition from walking the lifter into the leanness zone where lean is lost. The model already produces this through fat mass and the Forbes share. It does not need the energy gate to do it.

## 4. Long-horizon observational data

None of these cohorts measured energy intake against expenditure well enough to grade a surplus against balance. They are listed for what they bound.

**Trexler 2017 (S1926), NCAA football:**
- one year: lean +2.8 ± 2.8 kg, body fat −1.3 ± 2.5 percentage points (n = 57);
- four years: lean +4.3 ± 3.0 kg on weight +6.6 ± 4.1 kg (n = 13). Computed here, about two-thirds of the multi-year gain was lean.

**Binkley 2015 (S5.26), NCAA Division I football:**
- in-season: weight −1.3 kg and DXA lean −1.4 kg;
- by the following spring: weight "did not increase … but improvement in body composition was noted", with lean +2.2 kg and fat −1.4 kg.

Lean was regained at stable weight, which is recomposition after a seasonal loss, not new tissue at maintenance.

**Rugby cohorts:**
- McHugh 2021: one professional team over 7 y, with no significant composition change.
- Jones 2018: elite league players over 6 y, where lean-mass change fell with age (r = −0.70).

Neither relates the change to energy. They have no rows.

**Sumo:**
- Kondo 1994 (S5.24): professional wrestlers at 26.1 % fat carried more FFM than highly trained bodybuilders at 10.9 %. Six had over 100 kg of FFM, and the largest had 121.3 kg at 33 % fat. The authors put an upper limit near 0.7 kg FFM per cm of stature.
  - This is cross-sectional. It shows that a large, sustained surplus with heavy training carries FFM far past the bodybuilders' level, but the sumo FFM includes the lean tissue that supports a large fat mass. It is not evidence about a small surplus.
- Ogawa 2024 (S5.25): junior wrestlers aged about 15, with energy balance by doubly labelled water at 5.6 ± 213 kcal/d. FFM rose 2.1 kg in 6 months while fat mass did not change. They were adolescents and growing, so this does not transfer to adults.

**Post-contest recovery** (Buechel 2026 S2021, Chappell 2021 S2027, Rossow 2013 via Barakat S5.23, Isola 2023 S2019):
- the recovery surplus restores lean lost in the diet;
- it is regain after a deficit, not new muscle above a stable baseline;
- the Isola controls, the non-dieting physique athletes, "showed no systematic changes" over about 46 weeks (S2019).

**Weight-class athletes moving up a class, and natural FFMI trajectories with weight gain:** no study found (PubMed 2026-10-14).

## 5. Expert positions

| Source | Surplus recommended | By status | Basis |
|---|---|---|---|
| Iraki 2019 (S1946) | about 10-20 %; 0.25-0.5 % of body weight a week | advanced at "the lower end … or even … more conservative" | reasoning from rate-limited growth and fat risk; cites Garthe 2013 and Rozenek 2002 |
| Garthe 2013's authors (via Iraki; S5.7) | 200-300 kcal/d "in highly trained athletes", rather than 500 | highly trained | their own trial's fat gain |
| Slater 2019 (S5.10; S1947) | "start conservatively with an energy surplus within the range of ~1,500–2,000 kJ·day⁻¹" | none given | stored-energy arithmetic; states that no study has quantified the cost of accretion |
| Aragon 2017, ISSN diets stand (S5.8) | no number; "Larger caloric surpluses are more appropriate for untrained subjects … smaller caloric surpluses are appropriate for more advanced trainees" | yes, qualitatively | the deficit-MPS study (Pasiakos 2010) plus Garthe 2013 and Rozenek 2002; concedes "some advanced trainees will require larger surpluses" |
| Helms 2023 (S1943) | "conservative energy surpluses scaled to RT experience of 5-20 % … more advanced trainees consume smaller surpluses" | yes | their own trial, which could not deliver a 5 % surplus |
| Larson-Meyer 2022 (S5.20) | reports the guideline of about +300-500 kcal/d for about 0.45 kg/wk, "mostly as lean body mass" | none | concludes "research on intentional weight gain is lacking" and the 0.45 kg/wk lean target "may be difficult for some athletes to achieve" |
| Barakat 2020 (S5.22) | none | — | recomposition happens in trained people; heterogeneous designs |
| Morton | not found as a surplus recommendation | — | Morton 2018 (S0591) is a protein meta-analysis with no energy term |

Every expert who states a number for trained or advanced lifters puts it **at or below about 10 %, or about 200-500 kcal/d**, and smaller for the more advanced. All of them reason from practice, from mechanism, or from Garthe 2013's fat gain. None cites a trial showing that the advanced need a surplus to grow.

The rationale for "smaller when advanced" is fat avoidance: the slower the growth, the smaller the surplus it can use.

## 6. Barakat 2020's tables (open row S2047)

The paper is open access through Ovid (CC BY-NC-ND; the DOI resolves to Ovid). Rows S5.22 and S5.23 settle S2047 and partly settle S2048.

**Table 2: no nutrition reported, 4 studies.**

| Study | Population | Measure | Change |
|---|---|---|---|
| Alcaraz | ≥ 1 y | DXA | FFM +1.5 and +1.2 kg |
| Colquhoun | ≥ 6 months | A-mode ultrasound | FFM +1.7 and +2.6 |
| Wilborn | ≥ 1 y, Division III basketball | DXA | FFM +1.5 and +1.4 |
| Yue | about 3 y | Bod Pod | FFM +1.2 and +1.4 |

Fat changes were small or non-significant. Energy is "NR" (not recorded) for every study.

**Table 3: nutrition data provided, 8 studies.**

| Study | Population | Energy | Measure | Change |
|---|---|---|---|---|
| Antonio 2015 | 2.4 and 4.9 y | NP 2119, HP 2614 kcal | Bod Pod | FFM +1.5 and +1.5 |
| Antonio 2014 | 8.9 ± 6.7 y | NP 2052, HP 2835 kcal | Bod Pod | FFM +1.3 and +1.9, n.s. |
| Campbell | aspiring female physique athletes, ≥ 3 months | — | A-mode | FFM +2.1 and +0.6 |
| Cribb | ≥ 2 y | — | DXA | FFM +5.0 and +0.8 |
| Haun | trained men | "aimed for a 500 calorie surplus" | DXA | FFM +2.3, +1.7 and +2.9 |
| Kreipke | ≥ 1 y | — | DXA | FFM +1.1 and +1.3 |
| Slater HMB | elite water polo and rowers, about 7 y of resistance training | "increased mean energy intake 224 kJ/kg/d" | DXA | LBM +0.9, +1.2 and +3.5 |
| Rauch | Division II volleyball | — | DXA | FFM +2.7 and +2.7 |

**Table 4: physique-athlete case studies.**

| Case | Body fat or fat mass | Fat-free mass |
|---|---|---|
| Halliday | — | FFM held at 44.3 kg |
| Kistler | FM −10.4 kg | FFM −6.6 kg |
| Pardue | BF 13.4 to 9.6 % in prep, 17.2 % in recovery | no FFM given |
| Petrizzo | FM −8.0 | FFM +0.7 |
| Rohrig | FM −11.4 | FFM +1.3 |
| Rossow | BF 14.8 to 4.5 % | prep FFM −2.8 kg, "Recovery: (FFM −0.2 kg)" |

**What the tables do and do not contain:**
- No study in Tables 2-3 controls or verifies energy balance.
- No study measures muscle directly except Colquhoun and Campbell, by A-mode ultrasound, which estimates FFM from skinfold-type equations.
- Most lean measures are DXA or Bod Pod, inside the glycogen and water band (S2039).
- Training ages run from 3 months to about 9 y. Only Antonio 2014 (8.9 y, Bod Pod, n.s.) and Slater's HMB athletes (about 7 y, DXA) are long-trained.
- The one listed study with a prescribed surplus (Haun, +500 kcal) produced the largest DXA FFM gains. Haun 2019's own biopsies (S2042) show that this gain diluted actin and myosin by about 30 %.

**The table supports "trained people gain FFM while losing a little fat over 4-10 weeks by DXA or Bod Pod".** It says nothing about whether a surplus beats balance.

**Rossow's recovery FFM (−0.2 kg)** is ambiguous in Barakat's table, either against baseline or against the end of the diet. S5.23 quotes it as printed.

## 7. Verdict

**Does a small sustained surplus beat maintenance for muscle gain in trained or advanced lifters?**
- **Probably yes in direction, and small in size.**
- **Measured, it is indistinguishable from zero in muscle-specific outcomes over 8-12 weeks.**
- **Over long horizons it is unmeasured.**

**Confidence: low.** Grading:
- **The direction (small surplus ≥ balance): low to moderate.** Every trained contrast has a whole-body lean point estimate at or above zero with more energy: Henselmans +0.76 kg, Garthe +0.5 kg, Gavanda about 0. The mechanism of deficit-side suppression makes balance a weaker anabolic state than a slight surplus: MPS −19 to −27 %, and IGF-1 falls with deficit. Nothing points the other way.
- **The size: low.** The best interval (Henselmans) runs from −0.19 to +1.69 kg of DXA lean in 8 weeks, part of which is glycogen and water. The direct muscle intervals (±0.1-0.3 cm) include zero and modest effects alike. No trial in near-ceiling naturals exists (S2046 stays open).
- **That a large surplus (≥ about +15 %) adds fat and not measurable muscle in trained people: moderate** (Helms, Garthe, Gavanda, Spillane; the experts agree).

**Best direct evidence:** Henselmans 2026 (S5.3).
- Lifters with 9.7 y of training, a contrast of about 250-485 kcal/d over habitual intake, 8 wk, crossover.
- DXA lean +0.76 kg (95 % CI −0.19 to 1.69, p = 0.109).
- Elbow-flexor thickness +0.05 cm (−0.09 to 0.19), lateral-thigh thickness +0.03 cm (−0.27 to 0.31), VL CSA −0.45 cm² (−3.40 to 2.49).

Helms 2023 tests maintenance against a moderate-to-large surplus, not a small one: its "+5 %" arm reported +18 %. It reports Bayes factors, not intervals, and every muscle site favours the null (BF10 0.32-0.77).

**What the mechanism argues:**
- A surplus is not physically required as substrate. Muscle accretion costs well under 1 % of TDEE for a trained lifter, and fat stores cover years of it.
- What a slight surplus does is remove the deficit-side brake: lower MPS, lower IGF-1, and the leanness penalty that weight-stable recomposition walks into over time.
- Above balance, the anabolic levers are weak once protein is adequate. Insulin is permissive only with amino acids. Hormonal rises are shown only with large surpluses in untrained subjects. Glycogen is not an MPS signal.
- **So the mechanism predicts a gate that rises from balance to a small surplus and then flattens.** It does not predict a gate that keeps rising with surplus size, and it does not support a hard zero at balance.

**On the owner's position:** "a slight surplus over a long time … has to build more muscle than zero surplus" is supported in direction and in mechanism. The mechanism here is that balance is a mild brake and long-term balance drifts the lifter leaner. It is not that the muscle needs the calories. The size of the advantage is not measured; the data bound it at "not detectable in 8-12 weeks".

## 8. The energy gate

The current gate (spec § 5, point S):
- f_bal(s) = 1 − 0.5·s;
- full at +10 % of TDEE at every s;
- E₀ = −650·(1 − 0.5·s) times the protein term.

### Proposed form

```
f_e(E, s, p) = 0                                                for E ≤ E₀(s, p)
             = f_bal(s) · (E − E₀) / (0 − E₀)                   for E₀ < E < 0
             = f_bal(s) + (1 − f_bal(s)) · min(1, E / E_full(s)) for E ≥ 0

f_bal(s)  = 1 − d_bal · s                 d_bal = 0.5   (unchanged)
E_full(s) = e_full · (1 − d_full · s) · TDEE   e_full = 0.10, d_full = 0.5   (new: 10 % untrained, 5 % at the cap)
E₀(s, p)  unchanged (−650 · (1 − 0.5·s) · protein term)
```

At s = 1, balance gives 0.5, a +2.5 % surplus 0.75 and +5 % the full rate. At s = 0 the gate is unchanged: 1.0 at balance, and the surplus side is moot.

### Each constant, with its basis and what is a game choice

**1. d_bal = 0.5, kept.**
- The data bound f_bal(1) only weakly:
  - Moro 2016 (S2018): +0.5-0.6 kg FFM n.s. at maintenance, FFMI about 23;
  - Henselmans's habitual (PRO) condition: LM −0.20 ± 0.33 kg, thickness about 0;
  - Isola's controls: no change in 46 weeks.
- All three are consistent with anything from 0 to 1, because the headroom term already holds the gain at a near-ceiling status inside measurement noise.
- Henselmans's positive LM point estimate with more energy, in the most trained cohort, nudges toward f_bal < 1. The mechanism (balance is a brake, but substrate is not limiting) argues against 0.
- **Recommendation:** keep 0.5 as the evidence-neutral midpoint. Do not lower it by default. The owner's stricter premise remains available through `NR.StrengthTrainedNeedsSurplus` (gate at balance × (1 − value·s); at 1 the gate at balance is 0 at the cap).
- **Game choice:** the value itself, anywhere in [0.3, 1]. Going lower has no trial support.

**2. e_full = 0.10 at s = 0, kept.**
- Untrained lean gain is not energy-gated above balance in the model (f_bal(0) = 1), so the value is inert there.
- It matches Iraki's 10 % lower bound for novices and intermediates.

**3. d_full = 0.5, new: the full-rate surplus halves to +5 % at the cap.** Its bases:
- **Expert consensus by status:** Iraki (advanced at the lower end of 10-20 % or below), Garthe's authors (200-300 kcal/d in highly trained athletes), Aragon 2017 (smaller for the advanced), Helms 2023 (5-20 % scaled to experience, the advanced smaller).
- **The trials:** Henselmans's positive lean estimate came at a contrast of about 250-485 kcal/d. Helms's "+5 %" arm, in reality about +18 %, did no better than +28 %.
- **The mechanism:** the energy a near-ceiling lifter can put into muscle is a few kcal a day (§ 3.1). If the gate's surplus side models the removal of the deficit brake, it saturates once the brake is off, and the margin needed to be sure of being off it is smaller when weight is stable and growth is slow.
- **Game choice:** the slope (0.5), the linear ramp, and 5 % rather than 3 % or 7 % at the cap. The fit was flat on surplus_full over 0.05-0.15 (spec § 5.2), so this changes no fitted oracle materially.

**4. E₀ unchanged.** Nothing here moves the deficit side. Pasiakos 2010 (MPS −19 % at 80 % of needs, S5.16) and Areta 2014 (S1995) support the existing penalty below balance.

**5. The ramp shape, a game choice.**
- Linear is the simplest, and the fit is flat.
- A concave ramp, `min(1, E/E_full)^0.5`, would put most of the restoration in the first percent or two, closer to the mechanism.
- Nothing measured distinguishes the two. Keep linear unless playtesting asks for a sharper "eat a little more" reward.

### Oracles this harvest adds to the fit (offline, against point S's registry)

1. **Henselmans 2026 (S5.3).**
   - Setup: s about 0.6-0.8 (9.7 y, squat 1.9 × body mass, BMI 26.7; the FFMI was not reported, so s is a judgment), 8 weeks at about 14-18 weekly sets, protein about 2 g/kg, energy +250 to +485 kcal/d against habitual.
   - Pass: the model's (F + lx) difference lies inside −0.19 to +1.69 kg, and its F difference lies inside the muscle intervals.
   - Point S already passes this by construction (an advanced 8-week gain of hundredths of a kilogram), and so does the proposed form. It constrains nothing upward; it fails a model that makes the surplus produce more than about 1.7 kg of extra lean in 8 weeks.
2. **Garthe 2013 via Iraki (S5.7).**
   - Setup: a lean difference of +0.5 kg, n.s., at about +670 kcal/d between arms over 8-12 weeks in elite non-lifters (s about 0.2-0.4, a judgment).
   - This is report-only, since the SD is not readable.
3. **Helms 2023 (S5.1).**
   - Re-grade the existing oracles with MOD at about +18 % and HIGH at about +28 % of reported maintenance-phase intake, not +5 % and +15 % (computed here from Table 2). Both arms gained the same 3.3 kg.
   - The spec's Helms oracles assume +5 % and +15 %. Under the proposed gate both arms sit above E_full at any s ≥ 0, so they predict the same muscle, matching the data.

## Gaps

- **S2046 stays open:** no trial in near-ceiling naturals compares a small surplus with verified maintenance by a direct muscle measure. Henselmans 2026 is the nearest: about 10 y of training, but habitual intake rather than verified balance, and 8 weeks.
- **S5.28 (open):** Murphy & Koehler 2022's full text, for whether the meta-regression included any surplus condition and its slope above balance. Wiley, mediaTUM and the Unpaywall link were all blocked.
- **S5.29 (open):** myofibrillar protein synthesis at a surplus against balance in trained people. Only Welle 1989's whole-body, untrained, carbohydrate-overfeeding index exists.
- **S5.30 (open):** a pooled estimate of the surplus-against-balance effect on muscle-specific hypertrophy in trained lifters. No meta-analysis exists.
- **Garthe 2013** by baseline training status: the full text is paywalled (Taylor & Francis), and no secondary source splits it.
- **Rozenek 2002:** untrained, nothing further.
- **Hulmi's post-contest recovery** (lean against weight regain) and **Pardue 2017's lean numbers**: not found beyond what is registered. Barakat gives Pardue's body-fat percentages only.
- **Weight-class athletes moving up**, and **natural FFMI trajectories against weight gain**: no studies found.
- **Hall 2010's deposition costs** (ηL, ηF; PMC2838532) are not open in full text. Only the 2008 densities were read (S5.11).

Sources, all resolved by PMID: 37914977 (PMC10620361), 42356347 (PMC13305566), 38537251, 22935042, 23679146, 31247944 (PMC6680710), 28630601 (PMC5470183), 31482093 (PMC6710320), 17848938 (PMC2376744), 3479191, 10865771, 2648795, 2782403, 20164371, 26404065, 25646407, 16030064, 22628371, 35233712, 28548340, 38933620, 26313574, 39261323 (PMC11829922), 34623696, 40219022, 33361498, 33930935, 28281879, 29016472. Barakat 2020 by DOI 10.1519/SSC.0000000000000584 (Ovid full text).
