# Science wave 2: strength, training, detraining and the acute modifiers

Research note for the realism nutrition mod, refining § 4.3, § 4.5 and § 7 of
`docs/superpowers/specs/2026-09-27-nutrition-mod-design.md` and sections 4 to 6 of
`docs/superpowers/research/science-energy-body.md`. Scope: the dose-response of resistance training on
strength and size, protein and energy as the anabolic substrate, detraining and retraining, the acute
states that move maximal strength, the micronutrients with a strength effect, the strength-to-lean-mass
relation, and the engine mapping. Compiled 2026-09-27.

## How to read this

Grades, strongest first:

| Grade | Meaning |
|---|---|
| `MA` | Meta-analysis, network meta-analysis, meta-regression or systematic review |
| `RCT` | Randomised controlled trial, controlled crossover, or inpatient controlled trial |
| `COH` | Cohort, observational, cross-section, or a regression derived from one |
| `AUTH` | Authoritative report (ACSM position stand, IOC/IOM consensus, DRI) |
| `TXT` | Narrative review, editorial, textbook chapter or modelling paper |

**Verified by fetch.** Every citation below was resolved through the Europe PMC REST record for its DOI or
PMID, and title, author list, journal and year were matched against the citation as written before the row
was allowed to stand. Where a number is quoted, it came from the abstract of the record I fetched, not from
a secondary source. A number that lives only in a paywalled full text is marked **unverified** inline and is
not used as evidence and not carried into `## Proposed model`. Web search was unavailable for this wave, so
the whole literature sweep ran through Europe PMC's own search index; that biases discovery toward indexed
biomedical journals and away from sports-science outlets Europe PMC does not index, which is named in
`## Gaps`.

Two cautions carried forward from `science-energy-body.md` and reinforced by this wave:

- **Population transfer.** Almost every trial here is 6 to 20 weeks of supervised gym training in healthy
  young adults, with a handful in older adults and athletes. None of it measures a person doing months of
  unstructured heavy manual labour on scavenged food. Every number is a central tendency to be widened.
- **Individual response dominates the mean.** Hubal's 585-subject cohort found 1RM responses from 0 % to
  +250 % and cross-sectional-area responses from −2 % to +59 % over an identical 12-week programme. Any
  single population-mean rate the mod ships is a choice about where in that distribution the character sits,
  and that choice should be a per-character constant, not a global one.

Units: `1RM` = one-repetition maximum; `CSA` = muscle cross-sectional area; `MVF`/`MVC` = maximal voluntary
force/contraction; `FFM` = fat-free mass (kg); `LBM` = lean body mass (kg); `ES`/`SMD` = effect size /
standardised mean difference; `g·kg⁻¹·d⁻¹` = grams per kilogram body mass per day.

## 1. Training dose and strength gain

| parameter | value / equation | range or uncertainty | population | grade | citation |
|---|---|---|---|---|---|
| Any resistance training vs no exercise, strength | All 12 prescriptions tested beat non-exercise control; best-ranked (higher load >80 % 1RM, multiset, 3×/wk) **SMD 1.60** vs control | 95 % credible interval 1.38–1.82; threshold analysis "extremely robust" | 178 RCTs, n = 5097, 45 % women, healthy adults | MA | Currier et al. 2023, Br J Sports Med, PMID 37414459, doi:10.1136/bjsports-2023-106807 |
| Any resistance training vs no exercise, hypertrophy | All 12 prescriptions beat control; best-ranked (higher load, multiset, 2×/wk) **SMD 0.66** vs control; **all load prescriptions promoted hypertrophy comparably** | 95 % CrI 0.47–0.85 | 119 RCTs, n = 3364, 47 % women | MA | Currier et al. 2023 (as above) |
| Load is what separates strength from size | Strength maximised by load >80 % 1RM; hypertrophy indifferent to load but responsive to sets | the single clearest dissociation in the network | as above | MA | Currier et al. 2023 (as above) |
| Current authoritative prescription | Strength: load **≥80 % 1RM**, full range of motion, **2–3 sets**, early in the session, **≥2 sessions/wk**. Hypertrophy: **≥10 sets/wk** per muscle plus eccentric overload. Training to momentary fatigue, equipment, set structure, time under tension, BFR and periodisation did **not** consistently change outcomes | overview of 137 systematic reviews, >30 000 participants; supersedes the 2009 stand | healthy adults ≥18 y, interventions 6–52 wk | AUTH (overview of MAs) | Currier et al. 2026, Med Sci Sports Exerc, PMID 41843416, doi:10.1249/mss.0000000000003897 |
| Volume dose-response shape | Posterior probability that the volume slope exceeds zero is **100 %** for both hypertrophy and strength, but both best-fit models show **diminishing returns, considerably more pronounced for strength** | Bayesian multi-level meta-regression; adjusted for duration and training status | 67 studies, n = 2058, 79 % male, mean age 25.2 ± 5.2 y | MA | Pelland et al. 2026, Sports Med, PMID 41343037, doi:10.1007/s40279-025-02344-w |
| Frequency dose-response shape | Frequency slope exceeds zero with probability **100 % for strength** (diminishing returns) but **<100 % for hypertrophy**, i.e. compatible with a negligible effect on size | same models; "fractional" set-counting was the best-supported quantification | as above | MA | Pelland et al. 2026 (as above) |
| Volume → hypertrophy, per-set increment | Each additional weekly set per muscle adds **ES +0.023**, ≈ **+0.37 % gain** in muscle size; higher vs lower volume within study ES difference 0.241 ≈ **+3.9 %** | p = 0.002 continuous, p = 0.03 categorical; the <5 / 5–9 / 10+ three-level split was only a trend (p = 0.074) | 34 treatment groups, 15 studies | MA | Schoenfeld, Ogborn & Krieger 2017, J Sports Sci, PMID 27433992, doi:10.1080/02640414.2016.1210197 |
| Volume → strength, per-set increment | High vs low weekly sets ES difference only **+0.18** (95 % CI 0.06–0.30, p = 0.003); absolute pre-post ES 0.82 low-volume vs 1.01 high-volume | multi-joint +0.18, isolation +0.23; medium vs low only +0.15 | 61 treatment groups, 9 studies, restrictive inclusion | MA | Ralston et al. 2017, Sports Med, PMID 28755103, doi:10.1007/s40279-017-0762-7 |
| Frequency → strength | ES rises **0.74 → 0.82 → 0.93 → 1.08** for 1, 2, 3 and 4+ sessions/wk (p = 0.003); but **volume-equated subgroup is null** (p = 0.421), so frequency works mostly by carrying volume | significant for multi-joint 1RM and upper body; not for single-joint or lower body | 22 studies | MA | Grgic et al. 2018, Sports Med, PMID 29470825, doi:10.1007/s40279-018-0872-x |
| Optimal dose by training status | Untrained: **60 % 1RM, 3 d/wk, 4 sets** per muscle. Recreationally trained: **80 % 1RM, 2 d/wk, 4 sets**. Athletes: **85 % 1RM, 2 d/wk, 8 sets** | derived from 177 studies and 1803 ES across two meta-analyses | untrained, recreationally trained, competitive athletes | MA | Rhea et al. 2003, Med Sci Sports Exerc, PMID 12618576, doi:10.1249/01.MSS.0000053727.63505.D4; Peterson, Rhea & Alvar 2004, J Strength Cond Res, PMID 15142003, doi:10.1519/R-12842.1; synthesised in Peterson, Rhea & Alvar 2005, J Strength Cond Res, PMID 16287373, doi:10.1519/R-16874.1 |
| Minimum effective dose, trained men | **One set of 6–12 reps at ~70–85 % 1RM, 2–3×/wk, at high effort** raised 1RM significantly in every included study; pooled **+12.09 kg** overall 1RM (95 % CI 8.16–16.03), squat **+17.48 kg** (8.51–26.46), bench press **+8.25 kg** (0.68–15.83) | only 6 studies met inclusion, 5 pooled; study durations vary, so this is a per-study not per-week figure | resistance-trained men | MA | Androulakis-Korakakis, Fisher & Steele 2020, Sports Med, PMID 31797219, doi:10.1007/s40279-019-01236-0 |
| Early strength gain is neural, then hypertrophic | Neural factors accounted for the larger share of the **initial** strength increment; **hypertrophy became dominant after the first 3–5 weeks**; cross-education to the untrained contralateral arm supports the neural locus | n = 15, 8 wk, 1979 methods — small and old, but still the standard citation for the crossover point | 7 men, 8 women, isotonic training | RCT | Moritani & deVries 1979, Am J Phys Med, PMID 453338 (no DOI in record) |
| A measured neural-only gain | 4 wk isometric dorsiflexor training: **MVF +17.6 %** with motor-unit discharge rate +8.2 % at recruitment and +11.3 % at constant force, and **no change in recruitment thresholds**; discharge-rate change correlated with MVF change (r = 0.54–0.57) | n = 13 trained vs 10 control | older adults, 71 ± 4 y | RCT | Casolo et al. 2026, J Physiol, PMID 41823343, doi:10.1113/JP290541 |
| The neural mechanism is specific | 4 wk isometric training raised maximal force via **+~4 spikes/s discharge rate at the plateau phase**, while leaving rate of force development and motoneuron recruitment speed unchanged | motor-unit decomposition plus matched simulation | young adults | RCT | Del Vecchio et al. 2022, J Appl Physiol, PMID 34792405, doi:10.1152/japplphysiol.00218.2021 |
| What is still unresolved about the neural share | Review of what is and is not known about neural adaptation to resistance training; surface EMG amplitude is confounded by muscle size, so historical "neural share" estimates from EMG are not clean | explicitly a knowns/unknowns framing | humans | TXT | Škarabot et al. 2021, Eur J Appl Physiol, PMID 33355714, doi:10.1007/s00421-020-04567-3; Škarabot et al. 2021, J Appl Physiol, PMID 34166110, doi:10.1152/japplphysiol.00094.2021 |
| Hypertrophy is nevertheless causal for strength | Argues exercise-induced myofibrillar hypertrophy is a contributory cause of strength gain, against the position that size changes do not contribute | editorial, not data | — | TXT | Taber et al. 2019, Sports Med, PMID 31016546, doi:10.1007/s40279-019-01107-8 |
| Between-person spread of the response | 12 wk unilateral elbow-flexor training: **1RM +0 % to +250 %**, MVC **−32 % to +149 %**, biceps CSA **−2 % to +59 %**. Men gained 2.5 % more CSA; women gained more *relative* strength | the spread, not the mean, is the finding | 585 adults (342 women, 243 men), 8 centres | COH (multi-centre intervention cohort) | Hubal et al. 2005, Med Sci Sports Exerc, PMID 15947721 (no DOI in record) |
| A measured 10-week untrained rate | Quadriceps CSA **+~17 %**, thickness +~10 %, strength **+~20 %** over 10 wk unilateral training (≈ **2 %/wk on strength, 1.7 %/wk on CSA**) | single trial, n = 19 | 9 men, 10 women, untrained | RCT | Psilander et al. 2019, J Appl Physiol, PMID 30991013, doi:10.1152/japplphysiol.00917.2018 |

**Interpretation.** The 2023 network meta-analysis and the 2026 ACSM overview agree on the shape the mod
needs: *any* training beats none by a large margin, and within training, **load is the lever for strength and
volume is the lever for size**. That maps onto the game almost too neatly — heavy work (carrying loads,
chopping, fighting) is the high-load stimulus, and repetitive exercise actions are the volume stimulus. The
dose-response is monotonic but saturating in both, and the 2026 meta-regression is explicit that saturation is
*steeper for strength than for hypertrophy*: a character who trains hard should hit the strength plateau
quickly and keep accruing size slowly, which is exactly the behaviour a levelled perk wants. Frequency is
the weakest of the three levers once volume is held constant (Grgic's volume-equated subgroup is null), so a
mod should count total daily work, not "did they train today", and use frequency only as a small multiplier.
The minimum effective dose is genuinely tiny — one hard set of 6–12 reps two or three times a week raised
trained men's 1RM by about 12 kg — which justifies a low training-signal threshold for *maintenance* and a
much higher one for *gain*. The early-gain question has a clean answer with a caveat: Moritani's 3-to-5-week
crossover from neural to hypertrophic is still the standard citation and is directly supported by modern
motor-unit work showing +17.6 % force in four weeks with no size change, but Škarabot's review warns that the
old EMG-based partition of the "neural share" was confounded by muscle size, so the crossover *timing* is
better supported than any specific percentage split. The practical consequence for the mod is a two-term
strength model: a fast neural/skill term that can move within days to a few weeks and needs no tissue, and a
slow mass term that needs lean tissue and protein. Finally, Hubal's spread is the single most important number
for a game: an identical programme produced everything from no gain to a tripled 1RM, so a per-character
responder multiplier drawn once and kept is more faithful than the population mean.

## 2. Protein and energy

| parameter | value / equation | range or uncertainty | population | grade | citation |
|---|---|---|---|---|---|
| Protein plateau for training gains | **1.62 g·kg⁻¹·d⁻¹** total protein; above this, no further benefit. Effects of supplementation: 1RM **+2.49 kg**, FFM **+0.30 kg** | the widely quoted 95 % CI 1.03–2.20 g·kg⁻¹·d⁻¹ is not in the record's abstract and remains **unverified**; effect diminished with age, larger in already-trained | 49 RCTs, n = 1863, resistance training ≥6 wk | MA | Morton et al. 2018, Br J Sports Med, PMID 28698222, doi:10.1136/bjsports-2017-097608 |
| Protein → lean body mass, updated | Extra protein with resistance exercise raises LBM **SMD 0.22** (95 % CI 0.14–0.30, 62 studies, moderate evidence). The LBM effect became significant only at **≥1.6 g·kg⁻¹·d⁻¹ in adults <65 y** (1.2–1.59 g·kg⁻¹·d⁻¹ sufficed in adults ≥65 y) | small effect; graded moderate for LBM, **low** for strength | 74 RCTs, healthy non-obese adults | MA | Nunes et al. 2022, J Cachexia Sarcopenia Muscle, PMID 35187864, doi:10.1002/jcsm.12922 |
| Protein → strength, updated | Lower-body strength **SMD 0.40** at ≥1.6 g·kg⁻¹·d⁻¹ with training (19 studies); bench press **SMD 0.18** in adults <65 y (32 studies); **handgrip unclear**; physical-function tests marginal | low level of evidence on all strength outcomes | as above | MA | Nunes et al. 2022 (as above) |
| Baseline protein requirement, method-dependent | Non-athletes **0.64 g·kg⁻¹·d⁻¹** by nitrogen balance vs **0.88** by indicator amino-acid oxidation (+36 %); athletes **1.27** vs **1.61** (+27 %) | IAAO runs ~30 % above NB across age and sex subgroups | 43 NB studies (n = 777), 17 IAAO studies (n = 186) | MA | Tagawa et al. 2025, J Nutr, PMID 40914512, doi:10.1016/j.tjnut.2025.08.036 |
| Per-meal dose saturating myofibrillar protein synthesis | Young men **0.24 ± 0.06 g·kg body mass⁻¹** per meal (0.25 ± 0.13 g·kg LBM⁻¹); older men **0.40 ± 0.19 g·kg⁻¹** (0.60 ± 0.29 g·kg LBM⁻¹) | SDs as shown | pooled young (~22 y) and older (~71 y) men, 0–40 g doses | COH (pooled re-analysis) | Moore et al. 2015, J Gerontol A Biol Sci Med Sci, PMID 25056502, doi:10.1093/gerona/glu103 |
| Leucine trigger hypothesis | **16 of 29** eligible studies gave sufficient support; **13 of those 16 were in older adults** and **14 of 16 used isolated proteins**. The hypothesis has "most application" in older adults and with isolated protein, not with protein-rich whole foods | qualitative systematic review, no pooled effect | young and older adults, rest and post-exercise | MA (qualitative SR) | Zaromskyte et al. 2021, Front Nutr, PMID 34307436, doi:10.3389/fnut.2021.685165 |
| Protein distribution across meals | Even distribution is **associated** with higher muscle mass but **not** with strength or protein turnover; the concept is not supported by strong interventional evidence | one SR finds association only; a companion review questions the concept; a direct RCT in older adults found no MPS difference between even and skewed distribution | healthy adults; older adults for the RCT | MA + RCT | Jespersen & Agergaard 2021, Eur J Nutr, PMID 33550490, doi:10.1007/s00394-021-02487-2; Hudson, Bergia & Campbell 2020, Nutrients, PMID 32429355, doi:10.3390/nu12051441; Justesen et al. 2022, Nutrients, PMID 36364705, doi:10.3390/nu14214442 |
| Protein target in an energy deficit | **1.6–2.4 g·kg⁻¹·d⁻¹**, position in the range set by deficit severity and training load | recommendation, not a measured optimum | elite athletes losing weight | TXT (expert review of RCTs) | Hector & Phillips 2018, Int J Sport Nutr Exerc Metab, PMID 29182451, doi:10.1123/ijsnem.2017-0273 |
| Protein target scaled to FFM in lean trained athletes | **2.3–3.1 g·kg FFM⁻¹·d⁻¹**, scaled up with severity of restriction and with leanness. Across 13 study groups, body fat fell 0.5–6.6 % and FFM fell 0.3–2.7 kg in 9 of 13; the one lean, heavily restricted group that held FFM without a novel training stimulus ate **2.5–2.6 g·kg⁻¹·d⁻¹** | 6 studies only | energy-restricted resistance-trained adults (men ≤23 % fat, women ≤35 %) | MA (small SR) | Helms et al. 2014, Int J Sport Nutr Exerc Metab, PMID 24092765, doi:10.1123/ijsnem.2013-0054 |
| Protein dose in a 40 % deficit with heavy training | 2.4 vs 1.2 g·kg⁻¹·d⁻¹ over 4 wk: lean mass **+1.2 ± 1.0 kg** vs **+0.1 ± 1.0 kg**; fat mass **−4.8 ± 1.6** vs **−3.5 ± 1.4 kg**. Performance improved similarly in both | ±1.0 kg SD — individual variation equals the mean effect | 40 young men, 4 wk, 40 % deficit, resistance + HIIT 6 d/wk | RCT | Longland et al. 2016, Am J Clin Nutr, PMID 26817506, doi:10.3945/ajcn.115.119339 |
| Protein does **not** rescue an extreme deficit | 10-day military field exercise at **−4300 kcal·d⁻¹**: 2.0 vs 1.0 g·kg⁻¹·d⁻¹ made **no difference** to body mass (−6.1 / −5.2 %), fat mass (−40.5 / −33.4 %), 1RM bench press (**−9.5 / −9.7 %**), 1RM leg press (**−7.8 / −8.3 %**) or jump height (**−14.7 / −14.6 %**). **Fat-free mass did not change.** Testosterone and IGF-1 fell, cortisol rose, creatine kinase rose; after **7 days of recovery most variables had returned to near baseline**, jump height excepted | n = 19 per arm, not blinded to diet; single trial | young military personnel | RCT | Øfsteng et al. 2020, Scand J Med Sci Sports, PMID 32034812, doi:10.1111/sms.13634 |
| Cumulative deficit → strength loss, dose-response | Change in lower-body performance tracks **total** energy balance, not daily deficit or duration: strength r² = **0.836**, power r² = 0.764. **−5686 to −19 109 kcal total** for a 0–2 % decline; **−39 243 to −59 377 kcal total** for a 7–10 % decline | 9 studies, 15 subgroups; military operations | military personnel in the field | MA (meta-regression) | Murphy et al. 2018, Sports Med, PMID 29949108, doi:10.1007/s40279-018-0945-x |
| Exercise, not protein, protects lean mass under restriction | **81 %** of energy-restriction-only groups but only **39 %** of restriction-plus-exercise groups lost ≥15 % of their weight loss as fat-free mass | 52 studies; **the exercise was "mainly aerobic training"**, so resistance work would plausibly protect more; insufficient data for a true meta-analysis, so these are proportions of groups | overweight/obese adults ≥50 y, BMI >25 | MA (systematic review, unpooled) | Weinheimer, Sands & Campbell 2010, Nutr Rev, PMID 20591106, doi:10.1111/j.1753-4887.2010.00298.x |
| Prolonged deficit without training | Semi-starvation: most participants lost **>25 % of body weight** and experienced anaemia, fatigue, apathy, **extreme weakness**, irritability, neurological deficits and lower-extremity oedema | historical account of the Minnesota Starvation Experiment; the primary 1950 monograph is not indexed and its per-week strength series is **unverified** here | 36 healthy young men, 24 wk semi-starvation | TXT (historical) | Kalm & Semba 2005, J Nutr, PMID 15930436, doi:10.1093/jn/135.6.1347 |
| Surplus **without** training: fat is calorie-driven, lean is protein-gated | 8 wk inpatient overfeeding at **+954 kcal·d⁻¹** (+40 %): weight gain **3.16 kg** at 5 % protein vs **6.05 kg** at 15 % and **6.51 kg** at 25 %. **Body fat rose similarly in all three** and was 50–>90 % of the excess stored calories. Lean body mass rose **+2.87 kg** (15 %) and **+3.18 kg** (25 %) but **not at all** at 5 % protein; resting expenditure rose only in the two higher-protein arms | n = 25, single-blind, fully controlled inpatient | healthy weight-stable adults 18–35 y, BMI 19–30 | RCT | Bray et al. 2012, JAMA, PMID 22215165, doi:10.1001/jama.2011.1918 |
| Energy surplus is itself anabolic given protein | 6 wk with adequate protein in both arms: **+40 % energy surplus** raised total body protein by **+0.44 kg (+3.7 %)** (95 % CI 0.21–0.67); a **+10 % surplus from protein alone raised it 0.00 kg**. Protein gain correlated with fat gain (r = 0.820) | n = 23; 4-compartment body composition | healthy young men | RCT | Hatamoto et al. 2024, Clin Nutr, PMID 39423761, doi:10.1016/j.clnu.2024.09.035 |
| Protein ceiling | Gut absorbs amino acids at 1.3–10 g/h; suggested maximum safe intake **~2–2.5 g·kg⁻¹·d⁻¹**; above **~35 % of total energy** from protein comes hyperaminoacidaemia, hyperammonaemia, nausea, diarrhoea "and even death (the 'rabbit starvation syndrome')" | review-level synthesis; the 35 %-of-energy ceiling is the load-bearing number | humans | TXT | Bilsborough & Mann 2006, Int J Sport Nutr Exerc Metab, PMID 16779921, doi:10.1123/ijsnem.16.2.129 |
| Low energy availability as a syndrome | REDs: sustained low energy availability impairs multiple systems including musculoskeletal, with a clinical assessment tool and severity tiers | consensus statement, not an effect size | athletes of both sexes | AUTH | Mountjoy et al. 2023, Br J Sports Med, PMID 37752011, doi:10.1136/bjsports-2023-106994 (correction PMID 38325885) |
| Preserving muscle during weight loss | Review of the mechanisms and the interventions (protein, resistance exercise) that limit lean loss during deliberate weight loss | narrative | adults losing weight | TXT | Cava, Yeat & Mittendorfer 2017, Adv Nutr, PMID 28507015, doi:10.3945/an.116.014506 |

**Interpretation.** The protein picture has firmed up since Morton 2018 and the direction of the update
matters for the mod. Nunes's 74-RCT meta-analysis puts the *effect size* of extra protein at SMD 0.22 for lean
mass and grades the strength evidence "low" — protein is a permissive factor, not a driver, and the mod should
model it as a gate on the partition rather than as fuel that builds muscle. The gate sits at **1.6 g·kg⁻¹·d⁻¹**
in adults under 65, which is now supported twice independently (Morton's plateau, Nunes's threshold), and the
baseline requirement is **0.6–0.9 g·kg⁻¹·d⁻¹** depending on method (Tagawa). That gives three clean
breakpoints for a status ladder: below ~0.8 is deficient, 0.8–1.6 is maintenance, ≥1.6 unlocks gain, and
≥2.0–2.4 is the retention target when the character is in deficit and working hard. Per-meal distribution is
*weaker* evidence than the design assumed: Moore's 0.24 g/kg saturation point is solid, but the leucine trigger
is supported mainly in older adults eating isolated proteins, and the distribution literature finds
association without intervention effect. The earlier ruling not to model leucine as a separate nutrient is
confirmed, and a per-meal cap on the protein that counts toward the anabolic signal is defensible while a
*penalty* for skewed distribution is not. The most important new finding for the game is Øfsteng: at
−4300 kcal/day with heavy work for ten days, 1RM fell 8–10 % and jump height 15 % **with no measurable
fat-free-mass loss at all**, doubling the protein changed nothing, and a week of recovery restored almost
everything. Combined with Murphy's meta-regression — strength decline tracks *cumulative* deficit, r² = 0.84,
with a 7–10 % loss at roughly −40 000 to −60 000 kcal total — this says the mod needs a fast, reversible
"energetic/functional" strength penalty driven by cumulative deficit that is entirely separate from lean-mass
loss. On the surplus side, Bray's inpatient trial is the cleanest evidence available: calories alone set fat
gain, protein alone sets whether any of the surplus becomes lean, and a 5 %-protein surplus built literally
zero lean mass over eight weeks. Hatamoto adds the mirror: a +10 % surplus from protein alone built no body
protein either, while +40 % did. So the mod's surplus partition needs **both** an energy surplus and adequate
protein to add lean, and an energy surplus alone always adds fat.

## 3. Detraining and retraining

| parameter | value / equation | range or uncertainty | population | grade | citation |
|---|---|---|---|---|---|
| Strength loss on training cessation | **Submaximal strength SMD −0.62** (95 % CI −0.80 to −0.45); **maximal force SMD −0.46** (−0.54 to −0.37); **maximal power SMD −0.20** (−0.28 to −0.13); all p < 0.01. A **dose-response with cessation duration** was identified. Effect larger in adults >65 y and larger in inactive people than in recreational athletes for force and power | 103 of 284 screened studies; moderators were training status, sex, age, cessation duration; the per-week decay curve is not in the abstract and is **unverified** | mixed: inactive, recreational, athletes, young and old | MA | Bosquet et al. 2013, Scand J Med Sci Sports, PMID 23347054, doi:10.1111/sms.12047 |
| Detraining, the standard narrative account | Two-part review of short-term (<4 wk) and long-term insufficient training stimulus, plus a dedicated review of the muscular characteristics of detraining | still the standard descriptive reference; superseded on strength effect sizes by Bosquet 2013 | humans, athletes and non-athletes | TXT | Mujika & Padilla 2000, Sports Med, PMID 10966148, doi:10.2165/00007256-200030020-00002 (Part I) and PMID 10999420, doi:10.2165/00007256-200030030-00001 (Part II); Mujika & Padilla 2001, Med Sci Sports Exerc, PMID 11474330, doi:10.1097/00005768-200108000-00009 |
| Bed-rest decay is logarithmic, not linear | Pooled 5–120 day bed rest: **logarithmic** decline in both knee-extensor strength and CSA, steepest in the earliest days and plateauing later | n = 318 healthy adults, 5–120 d | healthy adults | MA (pooled systematic review) | Marusic et al. 2021, J Appl Physiol, PMID 33703945, doi:10.1152/japplphysiol.00363.2020 |
| Strength falls faster than mass, and the gap closes | Ratio between strength decline and atrophy is **4.2 at day 5**, **2.4 at day 14**, stabilising at **1.9 after ~35 days**. Over the whole range **~79 % of strength loss is explained by atrophy**, the rest by fibre mechanics, excitation-contraction coupling, architecture, tendon stiffness, denervation and supraspinal change | the abstract labels the quantity "ratio of muscle atrophy to strength decline" while stating strength declines much faster, so the label and the prose disagree; read as strength-decline ÷ atrophy, consistent with Wall 2014 | as above | MA | Marusic et al. 2021 (as above) |
| Unilateral immobilisation rates | Quadriceps CSA **−3.5 ± 0.5 %** at 5 d and **−8.4 ± 2.8 %** at 14 d (≈0.7 %/d early); strength **−9.0 %** at 5 d and **−22.9 %** at 14 d → strength falls **~2.5–2.7×** faster than size. Muscle myostatin mRNA doubled | ±0.5 % and ±2.8 % | 24 healthy young men, one-legged knee immobilisation | RCT | Wall et al. 2014, Acta Physiol (Oxf), PMID 24168489, doi:10.1111/apha.12190 |
| Bed rest in older adults, 10 days | Isotonic knee-extensor strength **−13.2 ± 4.1 %** (p = 0.004), stair-climbing power **−14 ± 4.1 %**, aerobic capacity −12 %, while standard physical-performance batteries were **unchanged** | n = 11, 67 ± 5 y, eucaloric diet at the protein RDA | healthy older adults | RCT (controlled inpatient) | Kortebein et al. 2008, J Gerontol A Biol Sci Med Sci, PMID 18948558, doi:10.1093/gerona/63.10.1076 |
| Maintenance dose | Strength and muscle size can be maintained **up to 32 weeks** in younger people with as little as **1 session per week and 1 set per exercise**, provided **relative load is maintained**; older people may need 2 sessions and 2–3 sets. Intensity, not frequency or volume, is the variable that preserves performance | narrative review; "insufficient data" for athletes and military | general populations, younger and older | TXT | Spiering et al. 2021, J Strength Cond Res, PMID 33629972, doi:10.1519/JSC.0000000000003964 |
| Human train → detrain → retrain, young | 10 wk training: CSA **+~17 %**, thickness +~10 %, strength **+~20 %**, **myonuclear number unchanged**. 20 wk detraining: size returned to baseline but **strength remained elevated**. 5 wk bilateral retraining: the previously trained and previously untrained legs responded **similarly**. Authors conclude the results neither strongly support nor refute human muscle memory | n = 19; the designed test of the myonuclear hypothesis found no myonuclear change and no retraining advantage | 9 men, 10 women | RCT | Psilander et al. 2019, J Appl Physiol, PMID 30991013, doi:10.1152/japplphysiol.00917.2018 |
| Human train → detrain → retrain, older | 12 wk training: knee-extension strength and power **+10 to +36 %**; type IIax fibre frequency halved. 12 wk detraining: strength and power lost only **−5 to −15 %**, with trends for type II CSA −17 %, type II satellite cells −30 %, type II myonuclei −12 %. **Less than 8 weeks of retraining restored post-training 1RM.** 12 wk retraining: type II CSA +29 %, satellite cells +72 %, myonuclei +13 %, with CSA change correlated to myonuclear change (r = 0.40–0.73) | n = 30 trained + 10 controls; biopsy subset of 6 | older men | RCT | Blocquiaux et al. 2020, Exp Gerontol, PMID 32017951, doi:10.1016/j.exger.2020.110860 (corrigendum PMID 32147251, doi:10.1016/j.exger.2020.110897) |
| Human retraining in previously trained women | 20 wk training → 30–32 wk detraining → 6 wk retraining: fibre CSA relatively stable through detraining (type IIb % rose); 6 wk retraining raised fast-fibre CSA in previously trained **and** previously untrained women | n = 6 retrained | women | RCT | Staron et al. 1991, J Appl Physiol, PMID 1827108, doi:10.1152/jappl.1991.70.2.631 |
| Epigenetic memory, human | Genome-wide methylation after load → unload → reload: **18 816 hypomethylated CpGs after reloading vs 9153 after the earlier loading**; *AXIN1, GRIK2, CAMK4, TRAF1* stayed hypomethylated through unloading (when mass had returned to control levels); *UBR5, RPL35a, HEG1, PLA2G16, SETD3* showed the largest hypomethylation, expression and mass increases on reloading | small n, single study, molecular endpoints — no strength or mass rate is derived from it | adult human vastus lateralis | RCT (molecular) | Seaborne et al. 2018, Sci Rep, PMID 29382913, doi:10.1038/s41598-018-20287-3 |
| Myonuclear permanence, rodent | Myonuclei acquired during overload **precede** hypertrophy and are **not lost** on detraining; no myonuclear loss over weeks of atrophy; an episodic anabolic-steroid exposure left a cellular memory aiding later overload hypertrophy long after | rodent, does not transfer to humans on its own | mouse | RCT (animal) | Bruusgaard et al. 2010, PNAS, PMID 20713720, doi:10.1073/pnas.0913935107; Bruusgaard & Gundersen 2008, J Clin Invest, PMID 18317591, doi:10.1172/JCI34022; Egner et al. 2013, J Physiol, PMID 24167222, doi:10.1113/jphysiol.2013.264457 |
| Status of the myonuclear hypothesis in humans | "Whether the postulated mechanism also holds true in humans remains largely ambiguous"; the follow-up asking directly whether myonuclei are ever lost, and the framing review, are both open-ended | reviews, not new data | human and animal | TXT | Snijders et al. 2020, Acta Physiol (Oxf), PMID 32175681, doi:10.1111/apha.13465; Eftestøl et al. 2020, J Appl Physiol, PMID 31854249, doi:10.1152/japplphysiol.00761.2019; Gundersen et al. 2018, J Physiol, PMID 30145845, doi:10.1113/JP276354 |

**Interpretation.** What the mod can defend is sharper than "muscle memory". Three findings are solid and
mutually consistent. First, **strength decays faster than mass and by a shrinking multiple**: 2.5–4× faster in
the first week, ~2.4× at two weeks, settling near 1.9× after five weeks (Wall; Marusic), and the decay is
logarithmic — steepest immediately, plateauing later — not linear. Second, **the maintenance threshold is
far below the gain threshold**: one hard set per week at maintained relative load holds strength and size for
up to 32 weeks (Spiering), which in game terms means an occasional fight or a day of hauling should be enough
to prevent decay while doing nothing near enough to drive gain. Third, **retraining to a prior peak is fast**:
Blocquiaux's older men regained their post-training 1RM in under eight weeks despite twelve weeks of
detraining, and their strength had only fallen 5–15 % over that detraining period while fibre size trended
down 17 %. That is the citable basis for "strength memory": the ceiling that comes back quickly is the
*functional* ceiling, and it comes back quickly because it never fell as far as the tissue did. What is **not**
supported is a mass-regain advantage: Psilander's trial was designed to detect exactly that and found the
previously trained and previously untrained legs responded identically, with no myonuclear change to explain
one. Seaborne's methylation data show a molecular memory exists, but it yields no rate a mod can use, and
Snijders's review is explicit that the mechanism is unresolved in humans. So the mod's rule should be: lean
mass regrows at ordinary hypertrophy rates with no bonus, and the Strength level tracks a fast functional
variable that both falls and returns ahead of the mass. Bosquet's dose-response with cessation duration and
its larger effect in inactive than in trained people also justifies making the decay rate depend on how
recently the character was active, which the engine's own Fitness regularity store already models in shape.

## 4. Acute nutrition and strength

| parameter | value / equation | range or uncertainty | population | grade | citation |
|---|---|---|---|---|---|
| Hypohydration → strength, narrative standard | Hypohydration consistently attenuates **strength by ~2 %**, **power by ~3 %** and **high-intensity endurance (30 s–2 min) by ~10 %**, once methodological confounders are accounted for. The relationships with **mode, degree and rate** of water loss "remain unclear due to a lack of suitably uninfluenced data"; the mechanism is probably neuromuscular, not cardiovascular or metabolic | the review's own caveat is that degree of hypohydration could not be related to decrement size | athletic, military and industrial settings | TXT (critical review) | Judelson et al. 2007, Sports Med, PMID 17887814, doi:10.2165/00007256-200737100-00006 |
| Hypohydration → strength, meta-analysed | Muscle endurance **−8.3 ± 2.3 %**; **muscle strength −5.5 ± 1.0 %** (upper body −6.2 ± 1.1, lower body −3.7 ± 1.8, difference NS); anaerobic power **−5.8 ± 2.3 %**; anaerobic capacity −3.5 ± 2.3 % (NS); **vertical jump +0.9 ± 0.7 % (NS)**. **No significant correlation between the degree of hypohydration and any decrement.** Active (exercise/heat) dehydration cost an extra **5.4 ± 1.9 %** (2.76-fold) vs passive; trained individuals lost **3.3 ± 1.7 % less** (p = 0.06) | 28 manuscripts, 85 effect estimates across 7 outcomes | mixed trained and untrained adults | MA | Savoie et al. 2015, Sports Med, PMID 26178327, doi:10.1007/s40279-015-0349-0 |
| Acute sleep loss → physical performance | Overall **−7.56 %** change in performance (95 % CI −11.9 to −3.13, p = 0.001, I² = 98 %); **significant for every exercise category including strength** (66 strength outcome measures). Consistent negative effects only with **deprivation and late restriction** (earlier-than-normal waking), not with delayed sleep onset. **~0.4 % decrement per additional hour awake** before the task. PM tasks consistently impaired; **AM tasks largely unaffected** | I² = 98 % — extremely heterogeneous; 89 % male | 69 publications, 227 outcomes; "sleep loss" = ≤6 h in 24 h | MA | Craven et al. 2022, Sports Med, PMID 35708888, doi:10.1007/s40279-022-01706-y |
| Caffeine → strength and power | Maximal strength **SMD 0.20** (95 % CI 0.03–0.36, p = 0.023); power **SMD 0.17** (0.00–0.34, p = 0.047). Upper-body strength **SMD 0.21** significant; **lower-body strength SMD 0.15 not significant** (p = 0.147) | 10 studies per outcome; blinding effectiveness poorly controlled; little female data | mostly young men | MA | Grgic et al. 2018, J Int Soc Sports Nutr, PMID 29527137, doi:10.1186/s12970-018-0216-0 |
| Caffeine, the umbrella verdict | Ergogenic across aerobic endurance, muscle strength, muscle endurance, power, jumping and speed; **moderate** GRADE quality for muscle endurance, strength, anaerobic power and aerobic endurance; effect generally **greater for aerobic than anaerobic** exercise; not all analyses had a definite direction once the 95 % prediction interval was considered | 11 reviews, 21 meta-analyses; mostly young men | healthy adults | MA (umbrella) | Grgic et al. 2020, Br J Sports Med, PMID 30926628, doi:10.1136/bjsports-2018-100278 |
| Carbohydrate availability → strength performance | "Carbohydrate intake per se is unlikely to [affect] strength training performance in a fed state in workouts consisting of up to 10 sets per muscle group." Acutely, higher carbohydrate did **not** improve performance in 13 of 19 studies; benefit appeared mainly with **fasted control groups** and workouts over 10 sets. **No dose-response.** After glycogen depletion, benefit appeared vs placebo in 3 studies but **not against isocaloric controls**. **None** of the 7 short-term (2–7 d) manipulations helped; 15 of 17 long-term studies showed no effect | 49 studies; the review flags the lack of isocaloric controls and sensory-matched placebos as the main weakness | strength trainees and athletes (39 studies), recreationally active, untrained | MA (systematic review, unpooled) | Henselmans et al. 2022, Nutrients, PMID 35215506, doi:10.3390/nu14040856 |
| Carbohydrate → hypertrophy | Pooled **SMD 0.15, p = 0.23** — no significant effect of higher carbohydrate on muscle size under isonitrogenous conditions; isocaloric subgroup SMD 0.15 (p = 0.60) | 11 studies; GRADE certainty **low** because of imprecision and moderate risk of bias | healthy adults in resistance training | MA | Henselmans, Vårvik & Izquierdo 2026, Sports Med, PMID 41712097, doi:10.1007/s40279-025-02341-z |
| Alcohol → recovery and performance | **~0.5 g·kg⁻¹ body weight is unlikely to impair most aspects of recovery.** At the doses athletes actually drink, acute alcohol may negatively alter immunoendocrine function, blood flow and protein synthesis so that recovery from muscle injury is impaired; rehydration and glycogen resynthesis are affected less | narrative review; dose-dependence is the load-bearing claim | male athletes | TXT | Barnes 2014, Sports Med, PMID 24748461, doi:10.1007/s40279-014-0192-8 |
| Alcohol → muscle protein synthesis | **1.5 g·kg⁻¹** (12 ± 2 standard drinks) after concurrent exercise reduced myofibrillar protein synthesis by **24 %** when co-ingested with 25 g whey and by **37 %** with carbohydrate, vs protein alone; mTOR(Ser2448) phosphorylation was lower with both alcohol arms | n = 8, randomised crossover | physically active men | RCT | Parr et al. 2014, PLoS One, PMID 24533082, doi:10.1371/journal.pone.0088384 |
| Hypoglycaemia → maximal strength | **No usable evidence found.** Europe PMC returned no trial or review measuring maximal voluntary strength under experimentally induced hypoglycaemia in healthy adults; the carbohydrate-availability literature above is the closest proxy and is null | — | — | — | gap, see `## Gaps` |

**Interpretation.** The acute levers split cleanly into ones the mod should implement and ones it should not.
**Dehydration is real and larger than the design's earlier reading suggested.** Judelson's ~2 % on strength is
the oft-quoted figure, but the 2015 meta-analysis — which is the stronger grade and covers 28 studies —
puts strength at **−5.5 %** and muscle endurance at **−8.3 %**, with upper body worse than lower and vertical
jump entirely unaffected. Two of its findings are directly useful: hypohydration produced by *exercise and
heat* costs about 5 % more than the same water deficit produced passively, and **the size of the decrement did
not correlate with the size of the water deficit** in either review. That second point argues against a smooth
strength-versus-hydration curve; a two-step penalty (a small one once mild dehydration is present, a larger one
at severe) is more faithful than a linear ramp, which also fits the existing 2 %-to-4 % body-mass ruling in
§ 4.4 of the spec. **Sleep loss is the largest acute effect here**: −7.6 % across all performance, significant
for strength specifically, with a clean −0.4 % per hour awake that maps straight onto a sleep-debt variable,
and a time-of-day pattern (afternoon and evening impaired, morning spared) that a game with a clock can
actually express. **Caffeine is real but small** — SMD 0.20 on strength, and not even significant for lower
body — so a few percent at most, and honestly the aerobic/endurance side is where caffeine belongs. **Alcohol's
strength effect should be modelled as a recovery penalty, not a strength penalty**: the measured effect is a
24–37 % suppression of myofibrillar protein synthesis at heavy doses, with a ~0.5 g/kg threshold below which
little happens, so alcohol belongs in the lean-mass-gain term, not the acute strength term. And the clearest
negative finding in this whole wave is that **carbohydrate availability barely touches strength**: neither
acute intake, nor glycogen depletion against an isocaloric control, nor 2-to-7-day manipulation, nor long-term
intake moved strength performance, and the 2026 meta-analysis finds no carbohydrate effect on hypertrophy
either. The mod should therefore *not* give low carbohydrate a strength penalty; carbohydrate's place is
endurance, fatigue and the energy budget, which is where the engine already routes it.

## 5. Micronutrients and strength

| parameter | value / equation | range or uncertainty | population | grade | citation |
|---|---|---|---|---|---|
| Vitamin D → muscle strength | Global muscle strength **SMD 0.17** (p = 0.02) — "small but significant". **No** effect on muscle mass (SMD 0.058, p = 0.52) or muscle power (SMD 0.057, p = 0.657). Effect **significantly larger where baseline 25(OH)D was <30 nmol/L**, and larger in adults ≥65 y (**SMD 0.25**, 95 % CI 0.01–0.48) than younger (**SMD 0.03**, 95 % CI −0.08 to 0.14) | 30 RCTs, n = 5615, mean age 61.1 y; all forms and doses pooled | mostly older adults | MA | Beaudart et al. 2014, J Clin Endocrinol Metab, PMID 25033068, doi:10.1210/jc.2014-1742 |
| Vitamin D → strength in young healthy adults | Upper-limb strength **SMD 0.32** (95 % CI 0.10–0.54, p = 0.005); lower-limb **SMD 0.32** (0.01–0.63, p = 0.04) | only 7 trials, n = 310, 67 % female, ages 21.5–31.5 y, 4 wk to 6 mo, 4000 IU/d to 60 000 IU/wk. **This contradicts Beaudart's younger-adult subgroup (SMD 0.03)**; Beaudart is the larger and better-powered synthesis, Tomlinson the one restricted to the right age band | healthy adults 18–40 y | MA | Tomlinson, Joseph & Angioi 2015, J Sci Med Sport, PMID 25156880, doi:10.1016/j.jsams.2014.07.022 |
| Iron deficiency → work capacity | Strong **causal** effect of severe and moderate iron-deficiency anaemia on **aerobic capacity** in animals and humans, mechanism reduced oxygen transport; endurance also compromised; **energetic efficiency affected at all levels of iron deficiency**, including deficiency without anaemia; reduced work productivity in field studies | 29 research reports; the outcomes are aerobic and productivity, **not maximal strength** | humans and animals, all levels of deficiency | MA (critical systematic review) | Haas & Brownlie 2001, J Nutr, PMID 11160598, doi:10.1093/jn/131.2.676S |
| Iron supplementation → performance | VO₂max **+2.35 mL·kg⁻¹·min⁻¹** (95 % CI 0.82–3.88, p = 0.003, 18 studies); overall VO₂max **SMD 0.37** (0.11–0.62); submaximal heart rate **−4.05 bpm** and −2.68 % of VO₂max to reach the same workload | 24 studies, 22 with extractable data; only 3 at overall low risk of bias; **no strength outcome reported** | women of reproductive age | MA | Pasricha et al. 2014, J Nutr, PMID 24717371, doi:10.3945/jn.113.189589 |
| Minerals other than iron → muscle outcomes | Of calcium, iron, magnesium, phosphorus, potassium, selenium, sodium and zinc, only **10 studies** met inclusion. Magnesium, selenium and iron **intake** and zinc **intake** were positively associated with **physical performance** (one observational study each); magnesium supplementation improved physical performance in **one** RCT; magnesium, selenium, calcium and phosphorus intakes were associated with sarcopenia prevalence. **No study at all** was found for sodium or potassium | overwhelmingly observational; the review's own conclusion is that RCTs are needed | healthy or frail older adults, mean age ≥65 y | MA (systematic review) | van Dronkelaar et al. 2018, J Am Med Dir Assoc, PMID 28711425, doi:10.1016/j.jamda.2017.05.026 |
| Zinc → muscle mass and strength | Dietary zinc intake **associated** with skeletal muscle mass and strength | cross-sectional, children and adolescents — wrong population for this mod and association only; the 1982 controlled study is the only older direct test and is not a usable effect size | children and adolescents | COH | Kong & Ma 2024, Clin Pediatr (Phila), PMID 37139808, doi:10.1177/00099228231171242; earlier direct test Krotkiewski et al. 1982, Acta Physiol Scand, PMID 7168359, doi:10.1111/j.1748-1716.1982.tb07146.x |
| Omega-3 → fat-free mass and strength | **No clear effect.** FFM **SMD 0.26** (95 % CI −1.14 to 1.66, p = 0.60); muscle strength **SMD −0.02** (−0.38 to 0.34, p = 0.92) across 22 dependent effects | 4 studies for FFM, 8 for strength; GRADE certainty **very low** | healthy adults without obesity | MA | Silva, Simões & Artioli 2026, Nutrition, PMID 42735611, doi:10.1016/j.nut.2026.113378 |
| Omega-3 → protein synthesis | Separate synthesis of the effect of n-3 PUFA on muscle and whole-body protein synthesis | consulted for direction only; no effect size taken | adults | MA | Therdyothin et al. 2025, Nutr Rev, PMID 38777807, doi:10.1093/nutrit/nuae055 |
| Creatine → strength and power | Creatine + resistance training vs placebo: bench/chest press **+1.43 kg** (p = 0.002), squat **+5.64 kg** (p = 0.001), vertical jump **+1.48 cm** (p = 0.01), Wingate peak power **+47.8 W** (p = 0.004). **Handgrip (+4.26 kg, p = 0.10) and leg press (+3.13 kg, p = 0.11) not significant.** Significant in **younger adults but not older**, and in **males but not females** | 69 studies, n = 1937 | adults, mixed training status | MA | Kazeminasab et al. 2025, Nutrients, PMID 40944139, doi:10.3390/nu17172748 |
| Dietary creatine, relevance | Position stand: supplementation raises intramuscular creatine and is safe up to 30 g/d for 5 y; "significant health benefits may be provided by ensuring habitual low dietary creatine ingestion (e.g. **3 g/day**) throughout the lifespan" | the per-kilogram creatine content of raw meat is **not verified here** — see `## Gaps` | healthy individuals and patients | AUTH | Kreider et al. 2017, J Int Soc Sports Nutr, PMID 28615996, doi:10.1186/s12970-017-0173-z |
| Earlier creatine strength synthesis | Upper-limb strength benefit from creatine supplementation | superseded for effect sizes by Kazeminasab 2025; cited for the record | adults | MA | Lanhers et al. 2017, Sports Med, PMID 27328852, doi:10.1007/s40279-016-0571-4 |

**Interpretation.** The micronutrient effects on *maximal strength* are all small, and several the mod might have
expected are null. **Vitamin D is the only micronutrient with a defensible direct strength effect**, and it is
conditional: SMD 0.17 overall, concentrated in people who started genuinely deficient (<30 nmol/L) and in older
adults, with **no** effect on muscle mass or power. There is a real contradiction in the literature for young
adults — Beaudart's younger subgroup is SMD 0.03 while Tomlinson's young-adult-only meta-analysis is SMD 0.32
— and since the mod's characters are mostly young adults, the honest reading is that a vitamin D strength
bonus should be small and should trigger only at a *deficient* grade, not as a reward for repletion. **Iron's
effect is aerobic, not strength**: both the causal review and the supplementation meta-analysis measure VO₂max,
endurance, heart rate and work productivity, and neither reports a maximal-strength outcome. So iron belongs on
the mod's endurance and work-capacity surfaces, which is where the existing design already routes it, and it
should not move the Strength ceiling. **Magnesium and zinc have essentially no interventional support** — one
RCT for magnesium and physical performance, associations only for zinc, and nothing for sodium or potassium in
the whole systematic review — so they should not carry a strength effect at all; they belong in the cramp,
fatigue and general-symptom ladders. **Omega-3 is null** on both fat-free mass and strength at very low
certainty, so the design should drop any omega-3 strength or lean-mass term. **Creatine is the one food-linked
compound with a real strength effect**, and it is meat-linked, which is game-relevant: +5.6 kg on squat and
+1.4 kg on bench with training, but null for handgrip and leg press and null in older adults and in women.
Given that the effect is for *supplementation on top of a normal diet* and the mod would be modelling dietary
creatine from meat, the defensible mechanic is a small anabolic/power credit for a consistently meat-containing
diet rather than a creatine nutrient with its own pool — and the meat-content figure needed to size it is not
verified in this wave.

## 6. Strength vs lean mass

| parameter | value / equation | range or uncertainty | population | grade | citation |
|---|---|---|---|---|---|
| Strength vs muscle CSA | Significant positive correlation between knee-extensor MVC and mid-thigh extensor CSA in both sexes (p < 0.01). Force per unit CSA **9.49 ± 1.34** (men) vs **8.92 ± 1.11** (women), NS | "the variation between subjects is such that strength is not a useful predictive index of muscle cross-sectional area" | 25 young men, 25 young women, CT | COH | Maughan, Watson & Weir 1983, J Physiol, PMID 6875963, doi:10.1113/jphysiol.1983.sp014658 |
| Strength vs lean body mass | **r = 0.50** (p < 0.01) in men; **no significant correlation in women** | — | as above | COH | Maughan et al. 1983 (as above) |
| Strength vs total body weight | **No significant correlation in either sex** | — | as above | COH | Maughan et al. 1983 (as above) |
| Allometric exponent for body-size normalisation | Normalise as **S = F / mᵇ** with **b = 0.67 for muscle force** (dynamometry) and **b = 1 for muscle torque** (isokinetic) | recommended exponents from geometric similarity plus empirical review | humans, strength-testing methodology | TXT | Jaric 2002, Sports Med, PMID 12141882, doi:10.2165/00007256-200232100-00002 |
| What actually explains a trained person's strength | Long-term trained (4.0 ± 0.8 y) vs untrained: maximal voluntary torque **+60 %**, muscle volume **+56 %**, physiological CSA **+41 %**, but specific tension only **+9 %** and patellar-tendon moment arm only **+4 %**. **Muscle size was the primary explanation.** Volume came mostly from PCSA (+41 %, sarcomeres in parallel) rather than fascicle length (+11 %) | n = 16 trained vs 52 untrained, cross-sectional | young men | COH | Maden-Wilkinson et al. 2020, J Appl Physiol, PMID 31873069, doi:10.1152/japplphysiol.00224.2019 |
| Force per unit muscle area, best estimate | Human muscle specific tension best estimate **26.8 N·cm⁻²**; the literature's reported range is **2 to 73 N·cm⁻²**, and the accepted mammalian figure is 22.5 N·cm⁻² | 30 studies, 96 values, weighted by directness of measurement; the spread is a methodological artefact as much as biology | human in vivo | MA (systematic review) | Persad et al. 2024, J Appl Physiol, PMID 39169839, doi:10.1152/japplphysiol.00296.2024 |
| The contrary position on size → strength | Argues exercise-induced changes in muscle size do **not** contribute to exercise-induced changes in strength; answered by the opposing editorial in the same journal | both are argument, not new data; the disagreement is about *change*, not about the cross-sectional relation | — | TXT | Loenneke et al. 2019, Sports Med, PMID 31020548, doi:10.1007/s40279-019-01106-9; Taber et al. 2019, Sports Med, PMID 31016546, doi:10.1007/s40279-019-01107-8 |
| Strength per unit lean in the obese | Absolute isokinetic strength **larger** in obese than lean women (except knee flexion and handgrip, NS). Correlations with FFM low to moderate in both (lean r = 0.28–0.53; obese r = 0.29–0.49); **no** correlation with fat mass in lean, weak positive (r = 0.21–0.39) in obese. **After allometric correction for FFM, every strength measure was at least 6 % lower in the obese**, except trunk flexion which was ≥8 % stronger | n = 173 obese (BMI 37.8 ± 5.3) vs 80 lean (BMI 22.0 ± 2.2), matched for age and physical activity | women, mean age ~40 y | COH | Hulens et al. 2001, Int J Obes Relat Metab Disord, PMID 11360150, doi:10.1038/sj.ijo.0801560 |
| The obesity pattern, generalised | Consensus: obese individuals **at any age** have greater **absolute** maximum strength — adiposity acts as a chronic overload on the antigravity muscles — but are **weaker when strength is normalised to body mass**. Evidence for strength normalised to *muscle mass* (muscle quality) is "limited" and discrepant | explicitly flags that co-activation, architecture and activity-level measurement confound the muscle-quality question | adolescents to old age | TXT | Tomlinson et al. 2016, Biogerontology, PMID 26667010, doi:10.1007/s10522-015-9626-4 |
| Strength loss per unit muscle loss in disuse | Strength falls **~2.5–4×** faster than CSA early, converging to ~1.9× after ~35 days; ~79 % of bed-rest strength loss is explained by atrophy | see § 3 | young men; pooled bed-rest cohort | RCT + MA | Wall et al. 2014, PMID 24168489, doi:10.1111/apha.12190; Marusic et al. 2021, PMID 33703945, doi:10.1152/japplphysiol.00363.2020 |
| Neural vs hypertrophic share over time | Neural dominates the initial increment; **hypertrophy dominant after the first 3–5 weeks** | see § 1 | young adults | RCT | Moritani & deVries 1979, Am J Phys Med, PMID 453338 (no DOI in record) |

**Interpretation.** Three numbers are enough to build the mapping, and one popular shortcut is wrong. The
shortcut first: **do not derive strength from total body weight.** Maughan measured zero correlation between
body weight and strength, and Hulens's obese cohort shows exactly why — they are absolutely stronger because
they carry more, and once fat-free mass is scaled out they are **at least 6 % weaker** than lean controls at
the same FFM. So in the mod, fat mass must contribute nothing to strength and should if anything impose a small
penalty, while total mass raises the *cost* of everything the character does. Second, **cross-sectionally,
muscle size really is the explanation for strength**: Maden-Wilkinson's trained group was 60 % stronger with
56 % more muscle volume, 41 % more PCSA and only 9 % more specific tension, so force per unit lean tissue is
close to a constant across trained and untrained people and the mod can treat lean mass as the ceiling-setting
variable with confidence. Third, **the per-person multiplier is large and must be a character constant**:
Maughan's r = 0.50 in men and no significant correlation at all in women, plus Persad's 2-to-73 N·cm⁻² spread in
measured specific tension, mean a single deterministic strength-from-lean function would be a fiction. The
allometric exponent is the remaining subtlety and it resolves cleanly for a game: use a roughly **linear** map
from lean mass to *absolute* strength (what the character can lift, carry and swing) and apply Jaric's
**b ≈ 0.67** only when scaling *relative* performance — climbing, vaulting, sprinting, anything where the
character moves their own body — so that a heavy character's strength-to-mass ratio falls as they grow. The
Loenneke/Taber disagreement is worth noting but does not change the design: it concerns whether *changes* in
size cause *changes* in strength within an individual, and both sides agree the cross-sectional relation is
strong, which is all the mod's ceiling needs. The disuse asymmetry from § 3 then completes the picture: the
ceiling should fall faster than mass and return faster than mass, converging on the mass-determined value over
about five weeks.

## 7. Engine mapping — speculative

**This section is speculative and is labelled as such.** Nothing below is measured. Each row is a design
proposal: a lever the engine exposes, the functional form proposed for it, and the evidence rows and jar
readings the form rests on. Grade `GAME` means a pure game choice with no evidence behind the number;
grade `INF` means an inference whose *shape* comes from an evidence row but whose constant is chosen.
The jar readings are cited as the claims candidates of `docs/superpowers/research/jar-perks-strength.md`,
which Plan 0 will mint as register rows.

| lever / parameter | proposed form | range or uncertainty | population | grade | rests on |
|---|---|---|---|---|---|
| Who owns the Strength level | The mod **clamps** the level down, never grants XP: `L_shown = min(L_vanilla_from_XP, L_ceiling)` written with `setPerkLevelDebug` | removes the anti-cheat question entirely and preserves vanilla XP by construction; the cost is that lean-mass gain *permits* a level rather than granting it | — | INF | jar candidates 13 (level moves only through four calls, two with no Java caller), 24 (`GameServer.addXp` refreshes the anticheat snapshot), 25 (XP-growth trip at `1000 × maxMult × maxBoostMult`); spec § 7 item 8 |
| Strength ceiling from lean mass | `L_ceiling = clamp(floor(L0 + k·log₂(m·F) + 0.5), 0, 10)` with `m = LM/LM0` and `k = 10` levels per doubling of strength | `k = 10` is read off the engine's own trait multipliers (WEAK 0.75 → STRONG 1.5 is a factor of 2 across ~10 levels); make it a sandbox dial | — | INF | Maughan 1983 (strength ∝ lean, r = 0.50 men, no correlation with body weight); Maden-Wilkinson 2020 (+56 % volume → +60 % torque, specific tension only +9 %); jar candidate on the Lua trait ladder and `IsoPlayer.<init>` trait deltas |
| Why the reference is `LM0`, not an absolute | Anchoring on the character's **own** starting lean mass makes `L_ceiling = L0` at creation for every build, so a level-10 start is never clipped and a level-0 start is never gifted | rounding uses `+0.5` so the creation state lands exactly on `L0` | — | GAME | brief requirement; Hubal 2005 (0 %–250 % response spread makes any absolute lean→strength constant a fiction) |
| Per-character responder constant `R` | Drawn once at creation from a bounded distribution (e.g. lognormal truncated to [0.5, 1.8], median 1.0), stored, never redrawn; multiplies the lean-gain rate only | the spread is real; the distribution shape is a game choice | — | INF | Hubal 2005 (1RM +0 % to +250 % on one programme); Bouchard 1990 (4.3–13.3 kg weight gain at an identical surplus); Persad 2024 (specific tension 2–73 N·cm⁻²) |
| Training signal from engine events | Convert Strength/Fitness XP grants and exercise repetitions into **weekly set-equivalents** in two accumulators, `V_hyp` and `V_str`, with indirect work counted at 0.5 ("fractional" quantification) | the per-event conversion constants (hits per set, minutes of load carriage per set) are pure game choices | — | INF | Pelland 2026 (fractional counting best supported; volume and frequency have different dose-responses for size and strength); jar candidates 44 (exercise `incStats` arms→strXp 4, chest→2), and the `XpUpdate.lua` grants (Strength 2 above 50 % carry, 2 on tree hit, `getLastHitCount()` per melee hit) |
| Intensity weighting | Strength accrual weighted by load class (`0.5` low / `0.8` moderate / `1.0` high); hypertrophy accrual weighted `1.0` at every load | the dissociation is the strongest finding in the network meta-analysis; the three weights are chosen | healthy adults | INF | Currier 2023 (higher load >80 % 1RM maximises strength, all loads comparable for hypertrophy); Currier 2026 ACSM stand (≥80 % 1RM for strength, ≥10 sets/wk for hypertrophy) |
| Saturating dose-response | `D = V/(V + K)` with `K_hyp = 10` and `K_str = 4` weekly set-equivalents | monotone with diminishing returns, saturating earlier for strength — the shape is evidenced, the half-max constants are chosen to land on the authoritative thresholds | healthy adults | INF | Pelland 2026 (diminishing returns, more pronounced for strength); Currier 2026 (≥10 sets/wk); Rhea 2003 / Peterson 2005 (4 sets per muscle optimal untrained, 8 in athletes) |
| Maintenance threshold | Decay of the neural term is **switched off entirely** while `V_str ≥ 1` weekly set-equivalent at high intensity | one hard set a week is the measured maintenance dose; in game terms an occasional fight or a day of hauling | younger adults | INF | Spiering 2021 (1 session/wk, 1 set/exercise maintains strength and size up to 32 wk if relative load is held); Androulakis-Korakakis 2020 (1 set 6–12 reps at 70–85 % 1RM, 2–3×/wk raises 1RM) |
| Acute states → carry capacity, not the level | Acute, fast-reverting terms are applied through `setMaxWeightDelta`, never to the perk level | a ±3 % effect cannot be expressed in a discrete 0–10 integer without visible flicker, and the engine already applies HUNGRY/THIRST/SICK/INJURED penalties at the same point | — | INF | jar candidates 29 (`setMaxWeightBase`/`setMaxWeightDelta` public, no Java caller, re-read every recompute) and 31 (`setMaxWeight` is overwritten on the next body-damage update); the `BodyDamage.UpdateStrength` moodle-penalty reading |
| Level-write cadence and hysteresis | Recompute every game minute, write at most once per game hour, only when the target differs by ≥1; rises require the ceiling to hold for 6 consecutive game hours, falls apply immediately at ≤1 level per hour | asymmetric on purpose: loss should feel responsive, gain earned | — | GAME | spec § 6 performance budgets; jar candidate 16 (a level change from a client pushes `SyncPerks`) |
| What must **not** get a strength term | Carbohydrate availability, iron, magnesium, zinc, omega-3 | each is a null or aerobic-only finding in § 4 and § 5; giving any of them a strength effect would be unevidenced | healthy adults | INF | Henselmans 2022 and 2026 (carbohydrate null on strength and on hypertrophy); Haas & Brownlie 2001 and Pasricha 2014 (iron effects are aerobic); van Dronkelaar 2018 (no interventional support for magnesium or zinc on strength); Silva 2026 (omega-3 null) |
| Vanilla's own protein branch | The engine already multiplies Strength XP by 1.5 when `50 < proteins < 300` and by 0.7 when `proteins < −300`; the mod must decide whether to leave it, since it takes takeover of the nutrition stats | interacts with the clamp design: if the mod writes the vanilla `proteins` stat, it moves vanilla XP accrual too | — | INF | controller note N1 and the superseded rows 0137 / 0181; jar reading of `IsoGameCharacter$XP.AddXP @107–@190` |

**Interpretation.** The single most useful realisation from mapping the evidence onto the levers is that the
mod does not need to grant Strength XP at all. Vanilla already awards Strength XP for exactly the activities
the literature says build strength — heavy melee swings, chopping, carrying over half capacity, and the arms
and chest components of the exercise actions — and the anti-cheat only ever watches XP *growth*. If the mod's
lean-mass model produces a **ceiling** and the mod's only write is `setPerkLevelDebug(Strength,
min(L_from_XP, L_ceiling))`, then vanilla XP is preserved by construction, the anti-cheat is never involved,
and the "strength memory" the design wants falls out for free: when the ceiling recovers, the previously earned
XP is still there and the level snaps back the moment the body can support it. The second realisation is the
split between the level and the delta. The perk level is a coarse integer and the engine gives a separate,
continuous, uncontested multiplier in `setMaxWeightDelta`, so the slow structural terms (lean mass, the
training-driven neural factor, cumulative energy debt) belong in the level while the fast reverting terms
(dehydration, sleep debt, caffeine, adiposity) belong in the delta alongside vanilla's own moodle penalties.
Third, the evidence supports a **two-term** strength model, not one: a fast functional term that can move
±10–20 % within days to weeks with no tissue change at all (Moritani's 3-to-5-week neural phase, Casolo's
+17.6 % in four weeks, Øfsteng's −9 % in ten days with *zero* fat-free-mass loss) and a slow mass term. Every
behaviour the design wants — fast loss under starvation, fast recovery on refeeding, slow genuine growth —
comes out of that split without any appeal to muscle memory in the tissue.

## Proposed model

Equations, constants and what each rests on. `GAME` marks a game choice with no evidence behind the number.
All rates are per game day at 1× unless stated. `LM`, `FM` in kg; energy in kcal.

### State to persist

```
LM, FM                   lean and fat mass (kg)                       -- spec § 4.3
LM0                      lean mass at character creation (kg)         -- the ceiling's reference
L0                       Strength level at character creation (0-10)   -- traits and profession
R                        responder constant, drawn once                -- Hubal 2005, Bouchard 1990
V_str, V_hyp             weekly set-equivalent accumulators
n_neural, n_peak, t_peak the neural/skill term, its held peak and when
CumDef                   decaying cumulative energy deficit (kcal)
t_disuse                 consecutive days immobilised
```

### 1. Training signal (event-driven, then decayed)

On every Strength- or Fitness-XP event and every exercise repetition, add set-equivalents `s` and a load
class `i ∈ {low, moderate, high}`:

```
s_from_event:                                          [GAME conversion constants]
  exercise repetition (arms or chest term)   s = 0.10,  i = moderate
  melee hit, weapon mass > 2 kg              s = 0.05,  i = high
  melee hit, weapon mass <= 2 kg             s = 0.05,  i = moderate
  tree-chop hit (OnWeaponHitTree)            s = 0.07,  i = high
  load carriage per 10 game minutes
      inventory > 80 % of capacity           s = 1.00,  i = high
      inventory > 50 % of capacity           s = 0.50,  i = moderate
  indirect work (legs/abs exercise, light)   s as above, counted at 0.5   [Pelland 2026]

w_str  = { low 0.50, moderate 0.80, high 1.00 }        [Currier 2023, Currier 2026]
w_hyp  = 1.00 at every load class                      [Currier 2023: loads comparable]

per event:   V_str += w_str(i)·s ;   V_hyp += w_hyp(i)·s
per minute:  V_x  *= exp(-Δt / τ_V),   τ_V = 7 d       [the literature's own weekly unit]

D_str = V_str / (V_str + K_str),  K_str = 4             [Pelland 2026 shape; Rhea 2003 4-set optimum]
D_hyp = V_hyp / (V_hyp + K_hyp),  K_hyp = 10           [Currier 2026 >=10 sets/wk]
maintained = (V_str at high load >= 1)                 [Spiering 2021]
```

### 2. Protein, counted per meal

```
per eat:  P_day += min(protein_g_in_meal, 0.24 · body_mass_kg)      [Moore 2015]
P = P_day / body_mass_kg                                             (g·kg⁻¹·d⁻¹)

g_protein = clamp((P - 0.8) / (1.6 - 0.8), 0, 1)
   0.8 = maintenance requirement   [Tagawa 2025: IAAO 0.88 non-athlete, NB 0.64]
   1.6 = the gain threshold        [Morton 2018 plateau 1.62; Nunes 2022 threshold >=1.6 under 65 y]

No leucine term and no penalty for skewed distribution.
   [Zaromskyte 2021: leucine trigger supported mainly in older adults on isolated protein]
   [Jespersen 2021, Hudson 2020, Justesen 2022: distribution is association, not effect]
```

### 3. Lean mass, daily

**Gain.** Requires training *and* protein *and* (almost always) an energy surplus:

```
g_energy = 0                                if balance B < 0 and not (P >= 2.0 and D_str >= 0.5)
         = 0.5                              if B < 0 and P >= 2.0 and D_str >= 0.5   [Longland 2016]
         = clamp(B / 500, 0, 1)             if B >= 0                    [Bray 2012, Hatamoto 2024]

headroom h = clamp((LM_cap - LM) / (LM_cap - LM0), 0, 1),  LM_cap = 1.25·LM0   [GAME cap]

ΔLM_gain = G0 · R · D_hyp · g_protein · g_energy · h · g_alcohol      (kg/d)
G0 = 0.050 kg/d  (= 0.35 kg/wk)
   [Longland 2016: +1.2 kg lean in 4 wk = 0.30 kg/wk, in a 40 % deficit]
   [Bray 2012: +2.87 to +3.18 kg LBM in 8 wk = 0.36-0.40 kg/wk, no resistance training]
   [Psilander 2019: +17 % quadriceps CSA in 10 wk = 1.7 %/wk]
   [Hatamoto 2024: +0.44 kg body protein in 6 wk on a +40 % surplus]
g_alcohol = 0.65 on a day with alcohol above 0.5 g·kg⁻¹              [Parr 2014 -24 to -37 % MPS; Barnes 2014 threshold]
```

**Loss under deficit.** Fat pays first to Alpert's ceiling, lean pays the overflow, and work protects it:

```
Fat_capacity  = 69 · FM                       kcal/d       [Alpert 2005: 290 ± 25 kJ·kg fat⁻¹·d⁻¹]
Overflow      = max(0, Deficit - Fat_capacity)
ΔLM_loss_raw  = Overflow / ρ_lean,   ρ_lean ≈ 1100 kcal/kg  [needs its own science row; see Gaps]

protection    = clamp(1 - 0.55·D_str - 0.15·g_protein, 0.30, 1)
   0.55 rests on Weinheimer 2010 (81 % -> 39 % of groups losing >=15 % of loss as FFM, a ~52 % relative drop)
        -- caveat: that exercise was "mainly aerobic", so 0.55 is if anything conservative for heavy work
   0.15 is deliberately small, because Øfsteng 2020 found doubling protein changed nothing at -4300 kcal/d
   floor 0.30 so that no combination of training and protein makes a severe deficit free

ΔLM_loss = ΔLM_loss_raw · protection
```

**Loss under disuse** (immobilised, `V_str ≈ 0`), applied *instead of* ordinary decay:

```
cumulative fractional CSA loss  L(t) = 0.171 · ln(1 + t/22)     t in days
   fitted to Wall 2014: L(5) = 3.5 %, L(14) = 8.4 %             [Wall 2014]
   logarithmic form, steepest first, plateauing                 [Marusic 2021]
```

### 4. The functional factor `F`

```
F_slow = max(1 + n_neural, F_floor) + e_energy + e_disuse,   clamped to [0.55, 1.25]

-- neural / skill term
n_target = 0.18 · D_str                       [Casolo 2026 +17.6 % MVF in 4 wk; Del Vecchio 2022]
dn/dt    = (n_target - n_neural) / τ_n
  τ_n = 14 d rising                           [Moritani 1979: neural phase, hypertrophy dominant after 3-5 wk]
  τ_n = ∞  (no decay) while `maintained`      [Spiering 2021]
  τ_n = 60 d falling when untrained but mobile [Bosquet 2013: SMD -0.46 max force, dose-response in duration;
                                                Blocquiaux 2020: only -5 to -15 % over 12 wk detraining]
  τ_n = 10 d falling when immobilised          [Wall 2014, Marusic 2021]

-- strength memory: the floor under the neural term
n_peak  = the highest n_neural held for >= 14 consecutive days
F_floor = 1 + n_peak · 0.80 · exp(-(t - t_peak) / 300 d)
   0.80 initial retention and τ = 300 d put the retained share at ~0.60 after 12 weeks,
   inside Blocquiaux 2020's measured band (a 10-36 % gain, of which only 5-15 % was lost in 12 wk)
   and consistent with Staron 1991 (fibre CSA stable through 30-32 wk detraining)
   Retraining then reaches ~95 % of target in ~4 weeks from the floor, versus Blocquiaux's
   "<8 weeks to regain post-training 1RM" and Staron's 6 weeks.

-- cumulative energy debt (fast, reversible, independent of mass)
CumDef  += max(0, TDEE - intake) per day, then  *= exp(-Δt / 10 d)
e_energy = -0.10 · clamp(CumDef / 50000, 0, 1)
   [Murphy 2018: -39 243 to -59 377 kcal total EB -> 7-10 % lower-body performance decline, r² = 0.836]
   [Øfsteng 2020: 10 d at -4300 kcal/d = -43 000 kcal -> 1RM -8 to -10 %, FFM unchanged,
    and near-full recovery in 7 days -- which is what the 10-day decay reproduces]

-- disuse residual, over and above the mass loss it causes
e_disuse = -0.325 · ln(1 + t_disuse/22)
   Check against Wall 2014: at 5 d, mass term 0.965 × functional 0.9335 = 0.901 -> -9.9 % (measured -9.0 %);
   at 14 d, 0.916 × 0.840 = 0.769 -> -23.1 % (measured -22.9 %).
```

### 5. The Strength ceiling and the level write

```
m         = LM / LM0
L_ceiling = clamp(floor(L0 + k·log₂(m · F_slow) + 0.5), 0, 10),   k = 10      [GAME k, from the trait span]
L_vanilla = level implied by the character's untouched Strength XP
L_shown   = min(L_vanilla, L_ceiling)

write:  setPerkLevelDebug(Perks.Strength, L_shown)
  - at most once per game hour, only when L_shown changes
  - a rise requires L_ceiling >= L_shown + 1 held for 6 consecutive game hours
  - a fall applies at the next hourly tick, at most 1 level per hour
  - never call LoseLevel (it would touch XP); never grant XP, so the anti-cheat is never engaged
    [jar candidates 13, 24, 25; spec § 7 item 8]
```

Worked sanity checks, with `L0 = 5`:

| situation | m | F_slow | ΔL | `L_ceiling` |
|---|---|---|---|---|
| creation | 1.00 | 1.00 | 0.0 | 5 |
| 4 weeks of hard work, no mass change yet | 1.00 | 1.15 | +2.0 | 7 |
| 10 days at −4300 kcal/d, heavy work (Øfsteng) | 1.00 | 0.91 | −1.4 | 4 |
| 10 % lean lost, still working | 0.90 | 1.10 | −0.1 | 5 |
| 20 % lean lost, sedentary and starving | 0.80 | 0.85 | −5.6 | 0 |
| 14 days immobilised | 0.92 | 0.84 | −3.8 | 1 |
| +20 % lean after months of surplus and work | 1.20 | 1.18 | +5.0 | 10 (needs the XP too) |

### 6. Acute states → carry capacity

Sum the terms, clamp, and apply through the delta only. **Nothing here touches the perk level.**

```
e_acute = Σ terms, clamped to [-0.20, +0.03]

  dehydration >= 2 % body mass water deficit        -0.03      [Judelson 2007 ~2 % on strength]
  dehydration >= 4 % body mass water deficit        -0.06      [Savoie 2015: strength -5.5 ± 1.0 %,
                                                                upper body -6.2 %, jump unaffected]
  the deficit arose from sweat/heat rather than
    from not drinking                               × 1.5 on the above   [Savoie 2015: active dehydration
                                                                 costs 5.4 ± 1.9 % more, a 2.76-fold effect]
  sleep debt, per hour awake beyond 18 h            -0.004, capped at -0.08   [Craven 2022: -0.4 %/h awake,
                                                                 overall -7.56 %]
    and halved between dawn and noon                                       [Craven 2022: AM largely unaffected]
  caffeine inside its active window                 +0.02      [Grgic 2018: strength SMD 0.20, upper body only]
  clinical vitamin D deficiency                     -0.03      [Beaudart 2014: SMD 0.17, concentrated below
                                                                 30 nmol/L; no effect on mass or power]
  body fat fraction above 30 %, per 10 points over  -0.03      [Hulens 2001: >=6 % weaker at matched FFM;
                                                                 Tomlinson 2016: weaker normalised to mass]
  carbohydrate availability, blood glucose          0          [Henselmans 2022, 2026: null]
  iron, magnesium, zinc, omega-3                    0 on strength         [§ 5 — routed to endurance instead]

write:  setMaxWeightDelta( trait_delta · (1 + e_acute) · (m · F_slow) / 2^((L_shown - L0)/k) )
```

The trailing factor is the part of the continuous strength ratio that the discrete level rounding did not
express, so total carry capacity ends up proportional to `m · F_slow · (1 + e_acute)` with the level carrying
the integer part and the delta the remainder. `setMaxWeightBase` is left at vanilla, because
`BodyDamage.UpdateStrength` already multiplies the base by the level-derived weight mod, and writing both
would double-count (jar candidates 29 and 31).

### 7. Cadence and budget

| clock | work |
|---|---|
| on the XP / exercise event | add set-equivalents to `V_str`, `V_hyp`; no allocation |
| per game minute | decay the accumulators, integrate `n_neural`, recompute `F_slow`, `e_acute` and `L_ceiling` from cached scalars |
| per game hour | the level write, if it changed; the `setMaxWeightDelta` write on change |
| per game day | the mass partition: `ΔLM_gain`, `ΔLM_loss`, fat, `CumDef` bookkeeping |

### What is a game choice, listed once

`k = 10` levels per strength doubling (read off the trait multipliers, not measured); `LM_cap = 1.25·LM0`;
every event-to-set-equivalent conversion constant; the `R` distribution's shape; `K_str = 4` and `K_hyp = 10`
as half-max points; the `[0.55, 1.25]` clamp on `F_slow`; the `[−0.20, +0.03]` clamp on `e_acute`; the 6-hour
rise hysteresis and the 1-level-per-hour fall rate; `B_full = 500` kcal for the surplus ramp; the decision to
route acute states to the delta rather than the level.

## Gaps

**Method gaps in this wave.**

1. **Web search was unavailable** (the session's search budget was exhausted before this task began), so the
   entire literature sweep ran through the Europe PMC REST search index. Europe PMC indexes the journals that
   matter most here — *Sports Medicine*, *BJSM*, *MSSE*, *J Appl Physiol*, *AJCN*, *Nutrients*, *JSCR* — so
   coverage of meta-analyses is probably good, but preprints (SportRxiv in particular), some conference
   proceedings and the grey literature were not reachable. Any conclusion that depends on a single most-recent
   synthesis should be re-swept with a real search engine before it ships.
2. **Abstract-level extraction only.** Every number above comes from the abstract of the record I fetched. Where
   a constant lives only in a paywalled full text it is marked unverified below and is not used.

**Evidence gaps that block a number the model wants.**

3. **Hypoglycaemia → maximal strength: no evidence found.** Europe PMC returned no trial or review measuring
   maximal voluntary strength under experimentally induced hypoglycaemia in healthy adults. The carbohydrate
   literature is the closest proxy and is null (Henselmans 2022, 2026). The mod should therefore apply no
   strength penalty for low blood glucose, but this is an absence of evidence, not evidence of absence.
4. **Lean-tissue energy density.** The proposed model divides the deficit overflow by `ρ_lean ≈ 1100 kcal/kg`.
   That constant was **not verified in this wave**; it needs its own science-register row sourced from the
   Hall/Forbes partitioning literature already in `science-energy-body.md § 3` before any number rests on it.
5. **Creatine content of raw meat.** Kreider 2017 verifies that ~3 g/day habitual dietary creatine is
   beneficial, but the per-kilogram creatine content of beef, pork, chicken and fish — the figure needed to
   size a meat-linked credit — is **not verified**. It needs a food-composition source, which is the item-pass
   pipeline's territory, not this report's.
6. **Morton 2018's confidence interval.** The widely quoted 95 % CI of 1.03–2.20 g·kg⁻¹·d⁻¹ around the
   1.62 plateau is **not in the abstract record** and remains unverified. Nunes 2022 independently supports the
   ≥1.6 threshold, so the model does not depend on the interval.
7. **Bosquet 2013's decay curve.** The meta-analysis reports a dose-response between cessation duration and
   effect size but the abstract gives no per-week function. The `τ_n = 60 d` falling time constant is therefore
   an inference calibrated against Blocquiaux's measured 12-week loss, not a fitted curve.
8. **Wernbom 2007's per-week hypertrophy rate table** is still paywalled, carried over unresolved from wave 1.
   The `G0 = 0.35 kg/wk` cap rests on Longland, Bray, Psilander and Hatamoto instead.
9. **The Minnesota Starvation Experiment's strength series.** Only the 2005 historical account is indexed and
   verified; the 1950 monograph's week-by-week strength and grip data are not reachable, so the model's
   prolonged-deficit-without-training behaviour rests on Øfsteng and Murphy (short, heavy-work deficits) rather
   than on true long semi-starvation.
10. **No multi-stressor evidence.** Nothing measures maximal strength in a person simultaneously
    underfed, sleep-deprived, dehydrated and doing heavy physical work — which is the game's normal state. The
    proposed model composes the terms multiplicatively (additively in log₂ space) and clamps the total, which is
    an untested assumption and the largest single risk in § 7.
11. **Sex coverage is thin throughout.** Pelland 2026 is 79 % male; Craven 2022 is 89 % male; the caffeine and
    creatine subgroup effects are significant in men and not in women; Maughan found strength correlated with
    lean mass in men (r = 0.50) and **not at all** in women. A sex term in the mod would be unevidenced in
    either direction.

**Contradictions a ruling must settle.**

12. **Vitamin D in young adults.** Beaudart 2014's under-65 subgroup is SMD 0.03 (95 % CI −0.08 to 0.14) —
    effectively nothing — while Tomlinson 2015, restricted to 18–40-year-olds, reports SMD 0.32 for both upper
    and lower limbs. Beaudart is far larger (30 RCTs, n = 5615 vs 7 trials, n = 310); Tomlinson is the one in
    the right age band. The proposed model takes the conservative reading (a small penalty at clinical
    deficiency, no bonus for repletion) and this needs a ruling.
13. **Marusic 2021's ratio label.** The abstract calls the quantity "the ratio of muscle atrophy to strength
    decline" (4.2 at day 5) while the surrounding prose states that strength declines much faster than atrophy.
    Read as strength-decline ÷ atrophy it is consistent with Wall 2014 (2.6 at day 5); read literally it is
    not. The model takes the former. A full-text check would settle it.
14. **Whether the fast strength term should also touch the level or only carry capacity.** § 7 routes acute
    states to `setMaxWeightDelta` on the argument that a 3 % effect cannot live in a 0–10 integer. That is a
    design judgement, not evidence, and it makes dehydration and sleep loss invisible in the character's
    displayed Strength level.

**Engine questions this report cannot answer.**

15. Whether a server-side Lua `setPerkLevelDebug` survives the next `PlayerXp` push, and whether the exposed
    but uncurated setters resolve under Kahlua — both named as harness questions in
    `jar-perks-strength.md § Not read`, and both gate the whole clamp design.
16. Which server option enables the XP anti-cheat and whether its default action is log, kick or ban — unread
    in the jar. The clamp design avoids the question by never granting XP, but any future XP grant reopens it.
17. Whether the mod should leave vanilla's own Strength-XP protein multiplier (`50 < proteins < 300` → ×1.5)
    in place once the mod owns the `proteins` stat. Under the clamp design this changes how fast `L_vanilla`
    rises, which is now a gameplay lever the mod controls indirectly.

## Bibliography

Every citation used above, once, with the identifier its Europe PMC record carries. All were verified by
fetching the record and matching title, authors, journal and year.

1. Alpert SS. A limit on the energy transfer rate from the human fat store in hypophagia. *J Theor Biol* 2005. PMID 15615615, doi:10.1016/j.jtbi.2004.08.029
2. Androulakis-Korakakis P, Fisher JP, Steele J. The minimum effective training dose required to increase 1RM strength in resistance-trained men: a systematic review and meta-analysis. *Sports Med* 2020. PMID 31797219, doi:10.1007/s40279-019-01236-0
3. Barnes MJ. Alcohol: impact on sports performance and recovery in male athletes. *Sports Med* 2014. PMID 24748461, doi:10.1007/s40279-014-0192-8
4. Beaudart C, Buckinx F, Rabenda V, et al. The effects of vitamin D on skeletal muscle strength, muscle mass, and muscle power: a systematic review and meta-analysis of randomized controlled trials. *J Clin Endocrinol Metab* 2014. PMID 25033068, doi:10.1210/jc.2014-1742
5. Bilsborough S, Mann N. A review of issues of dietary protein intake in humans. *Int J Sport Nutr Exerc Metab* 2006. PMID 16779921, doi:10.1123/ijsnem.16.2.129
6. Blocquiaux S, Gorski T, Van Roie E, et al. The effect of resistance training, detraining and retraining on muscle strength and power, myofibre size, satellite cells and myonuclei in older men. *Exp Gerontol* 2020. PMID 32017951, doi:10.1016/j.exger.2020.110860 — corrigendum PMID 32147251, doi:10.1016/j.exger.2020.110897
7. Bosquet L, Berryman N, Dupuy O, et al. Effect of training cessation on muscular performance: a meta-analysis. *Scand J Med Sci Sports* 2013. PMID 23347054, doi:10.1111/sms.12047
8. Bouchard C, Tremblay A, Després JP, et al. The response to long-term overfeeding in identical twins. *N Engl J Med* 1990. PMID 2336074, doi:10.1056/NEJM199005243222101
9. Bray GA, Smith SR, de Jonge L, et al. Effect of dietary protein content on weight gain, energy expenditure, and body composition during overeating: a randomized controlled trial. *JAMA* 2012. PMID 22215165, doi:10.1001/jama.2011.1918
10. Bruusgaard JC, Gundersen K. In vivo time-lapse microscopy reveals no loss of murine myonuclei during weeks of muscle atrophy. *J Clin Invest* 2008. PMID 18317591, doi:10.1172/JCI34022
11. Bruusgaard JC, Johansen IB, Egner IM, et al. Myonuclei acquired by overload exercise precede hypertrophy and are not lost on detraining. *PNAS* 2010. PMID 20713720, doi:10.1073/pnas.0913935107
12. Casolo A, Del Vecchio S, Goodlich BI, et al. Ageing does not impair motor neuron adaptations: comparable motor unit responses to strength training in young and older adults. *J Physiol* 2026. PMID 41823343, doi:10.1113/JP290541
13. Cava E, Yeat NC, Mittendorfer B. Preserving healthy muscle during weight loss. *Adv Nutr* 2017. PMID 28507015, doi:10.3945/an.116.014506
14. Craven J, McCartney D, Desbrow B, et al. Effects of acute sleep loss on physical performance: a systematic and meta-analytical review. *Sports Med* 2022. PMID 35708888, doi:10.1007/s40279-022-01706-y
15. Currier BS, Mcleod JC, Banfield L, et al. Resistance training prescription for muscle strength and hypertrophy in healthy adults: a systematic review and Bayesian network meta-analysis. *Br J Sports Med* 2023. PMID 37414459, doi:10.1136/bjsports-2023-106807
16. Currier BS, D'Souza AC, Singh MAF, et al. American College of Sports Medicine position stand. Resistance training prescription for muscle function, hypertrophy, and physical performance in healthy adults: an overview of reviews. *Med Sci Sports Exerc* 2026. PMID 41843416, doi:10.1249/MSS.0000000000003897
17. Del Vecchio A, Casolo A, Dideriksen JL, et al. Lack of increased rate of force development after strength training is explained by specific neural, not muscular, motor unit adaptations. *J Appl Physiol* 2022. PMID 34792405, doi:10.1152/japplphysiol.00218.2021
18. Eftestøl E, Psilander N, Cumming KT, et al. Muscle memory: are myonuclei ever lost? *J Appl Physiol* 2020. PMID 31854249, doi:10.1152/japplphysiol.00761.2019
19. Egner IM, Bruusgaard JC, Eftestøl E, Gundersen K. A cellular memory mechanism aids overload hypertrophy in muscle long after an episodic exposure to anabolic steroids. *J Physiol* 2013. PMID 24167222, doi:10.1113/jphysiol.2013.264457
20. Grgic J, Trexler ET, Lazinica B, Pedisic Z. Effects of caffeine intake on muscle strength and power: a systematic review and meta-analysis. *J Int Soc Sports Nutr* 2018. PMID 29527137, doi:10.1186/s12970-018-0216-0
21. Grgic J, Schoenfeld BJ, Davies TB, et al. Effect of resistance training frequency on gains in muscular strength: a systematic review and meta-analysis. *Sports Med* 2018. PMID 29470825, doi:10.1007/s40279-018-0872-x
22. Grgic J, Grgic I, Pickering C, et al. Wake up and smell the coffee: caffeine supplementation and exercise performance — an umbrella review of 21 published meta-analyses. *Br J Sports Med* 2020. PMID 30926628, doi:10.1136/bjsports-2018-100278
23. Gundersen K, Bruusgaard JC, Egner IM, et al. Muscle memory: virtues of your youth? *J Physiol* 2018. PMID 30145845, doi:10.1113/JP276354
24. Haas JD, Brownlie T. Iron deficiency and reduced work capacity: a critical review of the research to determine a causal relationship. *J Nutr* 2001. PMID 11160598, doi:10.1093/jn/131.2.676S
25. Hatamoto Y, Tanoue Y, Tagawa R, et al. Greater energy surplus promotes body protein accretion in healthy young men: a randomized clinical trial. *Clin Nutr* 2024. PMID 39423761, doi:10.1016/j.clnu.2024.09.035
26. Hector AJ, Phillips SM. Protein recommendations for weight loss in elite athletes: a focus on body composition and performance. *Int J Sport Nutr Exerc Metab* 2018. PMID 29182451, doi:10.1123/ijsnem.2017-0273
27. Helms ER, Zinn C, Rowlands DS, Brown SR. A systematic review of dietary protein during caloric restriction in resistance trained lean athletes: a case for higher intakes. *Int J Sport Nutr Exerc Metab* 2014. PMID 24092765, doi:10.1123/ijsnem.2013-0054
28. Henselmans M, Bjørnsen T, Hedderman R, Vårvik FT. The effect of carbohydrate intake on strength and resistance training performance: a systematic review. *Nutrients* 2022. PMID 35215506, doi:10.3390/nu14040856
29. Henselmans M, Vårvik FT, Izquierdo M. The effect of carbohydrate intake on muscle hypertrophy: a systematic review and meta-analysis. *Sports Med* 2026. PMID 41712097, doi:10.1007/s40279-025-02341-z
30. Hubal MJ, Gordish-Dressman H, Thompson PD, et al. Variability in muscle size and strength gain after unilateral resistance training. *Med Sci Sports Exerc* 2005. PMID 15947721 (no DOI in record)
31. Hudson JL, Bergia RE 3rd, Campbell WW. Protein distribution and muscle-related outcomes: does the evidence support the concept? *Nutrients* 2020. PMID 32429355, doi:10.3390/nu12051441
32. Hulens M, Vansant G, Lysens R, et al. Study of differences in peripheral muscle strength of lean versus obese women: an allometric approach. *Int J Obes Relat Metab Disord* 2001. PMID 11360150, doi:10.1038/sj.ijo.0801560
33. Jaric S. Muscle strength testing: use of normalisation for body size. *Sports Med* 2002. PMID 12141882, doi:10.2165/00007256-200232100-00002
34. Jespersen SE, Agergaard J. Evenness of dietary protein distribution is associated with higher muscle mass but not muscle strength or protein turnover in healthy adults: a systematic review. *Eur J Nutr* 2021. PMID 33550490, doi:10.1007/s00394-021-02487-2
35. Judelson DA, Maresh CM, Anderson JM, et al. Hydration and muscular performance: does fluid balance affect strength, power and high-intensity endurance? *Sports Med* 2007. PMID 17887814, doi:10.2165/00007256-200737100-00006
36. Justesen TEH, Jespersen SE, Tagmose Thomsen T, et al. Comparing even with skewed dietary protein distribution shows no difference in muscle protein synthesis or amino acid utilization in healthy older individuals: a randomized controlled trial. *Nutrients* 2022. PMID 36364705, doi:10.3390/nu14214442
37. Kalm LM, Semba RD. They starved so that others be better fed: remembering Ancel Keys and the Minnesota experiment. *J Nutr* 2005. PMID 15930436, doi:10.1093/jn/135.6.1347
38. Kazeminasab F, Kerchi AB, Sharafifard F, et al. The effects of creatine supplementation on upper- and lower-body strength and power: a systematic review and meta-analysis. *Nutrients* 2025. PMID 40944139, doi:10.3390/nu17172748
39. Kong FS, Ma CM. Dietary zinc intakes are associated with skeletal muscle mass and strength in children and adolescents. *Clin Pediatr (Phila)* 2024. PMID 37139808, doi:10.1177/00099228231171242
40. Kortebein P, Symons TB, Ferrando A, et al. Functional impact of 10 days of bed rest in healthy older adults. *J Gerontol A Biol Sci Med Sci* 2008. PMID 18948558, doi:10.1093/gerona/63.10.1076
41. Kreider RB, Kalman DS, Antonio J, et al. International Society of Sports Nutrition position stand: safety and efficacy of creatine supplementation in exercise, sport, and medicine. *J Int Soc Sports Nutr* 2017. PMID 28615996, doi:10.1186/s12970-017-0173-z
42. Krotkiewski M, Gudmundsson M, Backström P, Mandroukas K. Zinc and muscle strength and endurance. *Acta Physiol Scand* 1982. PMID 7168359, doi:10.1111/j.1748-1716.1982.tb07146.x
43. Lanhers C, Pereira B, Naughton G, et al. Creatine supplementation and upper limb strength performance: a systematic review and meta-analysis. *Sports Med* 2017. PMID 27328852, doi:10.1007/s40279-016-0571-4
44. Loenneke JP, Buckner SL, Dankel SJ, Abe T. Exercise-induced changes in muscle size do not contribute to exercise-induced changes in muscle strength. *Sports Med* 2019. PMID 31020548, doi:10.1007/s40279-019-01106-9
45. Longland TM, Oikawa SY, Mitchell CJ, et al. Higher compared with lower dietary protein during an energy deficit combined with intense exercise promotes greater lean mass gain and fat mass loss: a randomized trial. *Am J Clin Nutr* 2016. PMID 26817506, doi:10.3945/ajcn.115.119339
46. Maden-Wilkinson TM, Balshaw TG, Massey GJ, Folland JP. What makes long-term resistance-trained individuals so strong? A comparison of skeletal muscle morphology, architecture, and joint mechanics. *J Appl Physiol* 2020. PMID 31873069, doi:10.1152/japplphysiol.00224.2019
47. Marusic U, Narici M, Simunic B, et al. Nonuniform loss of muscle strength and atrophy during bed rest: a systematic review. *J Appl Physiol* 2021. PMID 33703945, doi:10.1152/japplphysiol.00363.2020
48. Maughan RJ, Watson JS, Weir J. Strength and cross-sectional area of human skeletal muscle. *J Physiol* 1983. PMID 6875963, doi:10.1113/jphysiol.1983.sp014658
49. Moore DR, Churchward-Venne TA, Witard O, et al. Protein ingestion to stimulate myofibrillar protein synthesis requires greater relative protein intakes in healthy older versus younger men. *J Gerontol A Biol Sci Med Sci* 2015. PMID 25056502, doi:10.1093/gerona/glu103
50. Moritani T, deVries HA. Neural factors versus hypertrophy in the time course of muscle strength gain. *Am J Phys Med* 1979. PMID 453338 (no DOI in record)
51. Morton RW, Murphy KT, McKellar SR, et al. A systematic review, meta-analysis and meta-regression of the effect of protein supplementation on resistance training-induced gains in muscle mass and strength in healthy adults. *Br J Sports Med* 2018. PMID 28698222, doi:10.1136/bjsports-2017-097608
52. Mountjoy M, Ackerman KE, Bailey DM, et al. 2023 International Olympic Committee's (IOC) consensus statement on Relative Energy Deficiency in Sport (REDs). *Br J Sports Med* 2023. PMID 37752011, doi:10.1136/bjsports-2023-106994 — correction PMID 38325885, doi:10.1136/bjsports-2023-106994corr1
53. Mujika I, Padilla S. Detraining: loss of training-induced physiological and performance adaptations. Part I: short term insufficient training stimulus. *Sports Med* 2000. PMID 10966148, doi:10.2165/00007256-200030020-00002
54. Mujika I, Padilla S. Detraining: loss of training-induced physiological and performance adaptations. Part II: long term insufficient training stimulus. *Sports Med* 2000. PMID 10999420, doi:10.2165/00007256-200030030-00001
55. Mujika I, Padilla S. Muscular characteristics of detraining in humans. *Med Sci Sports Exerc* 2001. PMID 11474330, doi:10.1097/00005768-200108000-00009
56. Murphy NE, Carrigan CT, Karl JP, et al. Threshold of energy deficit and lower-body performance declines in military personnel: a meta-regression. *Sports Med* 2018. PMID 29949108, doi:10.1007/s40279-018-0945-x
57. Nunes EA, Colenso-Semple L, McKellar SR, et al. Systematic review and meta-analysis of protein intake to support muscle mass and function in healthy adults. *J Cachexia Sarcopenia Muscle* 2022. PMID 35187864, doi:10.1002/jcsm.12922
58. Øfsteng SJ, Garthe I, Jøsok Ø, et al. No effect of increasing protein intake during military exercise with severe energy deficit on body composition and performance. *Scand J Med Sci Sports* 2020. PMID 32034812, doi:10.1111/sms.13634
59. Parr EB, Camera DM, Areta JL, et al. Alcohol ingestion impairs maximal post-exercise rates of myofibrillar protein synthesis following a single bout of concurrent training. *PLoS One* 2014. PMID 24533082, doi:10.1371/journal.pone.0088384
60. Pasricha SR, Low M, Thompson J, et al. Iron supplementation benefits physical performance in women of reproductive age: a systematic review and meta-analysis. *J Nutr* 2014. PMID 24717371, doi:10.3945/jn.113.189589
61. Pelland JC, Remmert JF, Robinson ZP, et al. The resistance training dose response: meta-regressions exploring the effects of weekly volume and frequency on muscle hypertrophy and strength gains. *Sports Med* 2026. PMID 41343037, doi:10.1007/s40279-025-02344-w
62. Persad LS, Wang Z, Pino PA, et al. Specific tension of human muscle in vivo: a systematic review. *J Appl Physiol* 2024. PMID 39169839, doi:10.1152/japplphysiol.00296.2024
63. Peterson MD, Rhea MR, Alvar BA. Maximizing strength development in athletes: a meta-analysis to determine the dose-response relationship. *J Strength Cond Res* 2004. PMID 15142003, doi:10.1519/R-12842.1
64. Peterson MD, Rhea MR, Alvar BA. Applications of the dose-response for muscular strength development: a review of meta-analytic efficacy and reliability for designing training prescription. *J Strength Cond Res* 2005. PMID 16287373, doi:10.1519/R-16874.1
65. Psilander N, Eftestøl E, Cumming KT, et al. Effects of training, detraining, and retraining on strength, hypertrophy, and myonuclear number in human skeletal muscle. *J Appl Physiol* 2019. PMID 30991013, doi:10.1152/japplphysiol.00917.2018
66. Ralston GW, Kilgore L, Wyatt FB, Baker JS. The effect of weekly set volume on strength gain: a meta-analysis. *Sports Med* 2017. PMID 28755103, doi:10.1007/s40279-017-0762-7
67. Rhea MR, Alvar BA, Burkett LN, Ball SD. A meta-analysis to determine the dose response for strength development. *Med Sci Sports Exerc* 2003. PMID 12618576, doi:10.1249/01.MSS.0000053727.63505.D4
68. Savoie FA, Kenefick RW, Ely BR, et al. Effect of hypohydration on muscle endurance, strength, anaerobic power and capacity and vertical jumping ability: a meta-analysis. *Sports Med* 2015. PMID 26178327, doi:10.1007/s40279-015-0349-0
69. Schoenfeld BJ, Ogborn D, Krieger JW. Dose-response relationship between weekly resistance training volume and increases in muscle mass: a systematic review and meta-analysis. *J Sports Sci* 2017. PMID 27433992, doi:10.1080/02640414.2016.1210197
70. Seaborne RA, Strauss J, Cocks M, et al. Human skeletal muscle possesses an epigenetic memory of hypertrophy. *Sci Rep* 2018. PMID 29382913, doi:10.1038/s41598-018-20287-3
71. Silva AMF, Simões MO, Artioli GG. Omega-3 supplementation shows no clear benefit for fat-free mass or muscle strength in healthy adults: a systematic review and meta-analysis of randomized controlled trials. *Nutrition* 2026. PMID 42735611, doi:10.1016/j.nut.2026.113378
72. Škarabot J, Brownstein CG, Casolo A, et al. The knowns and unknowns of neural adaptations to resistance training. *Eur J Appl Physiol* 2021. PMID 33355714, doi:10.1007/s00421-020-04567-3
73. Škarabot J, Balshaw TG, Maeo S, et al. Neural adaptations to long-term resistance training: evidence for the confounding effect of muscle size on the interpretation of surface electromyography. *J Appl Physiol* 2021. PMID 34166110, doi:10.1152/japplphysiol.00094.2021
74. Snijders T, Aussieker T, Holwerda A, et al. The concept of skeletal muscle memory: evidence from animal and human studies. *Acta Physiol (Oxf)* 2020. PMID 32175681, doi:10.1111/apha.13465
75. Spiering BA, Mujika I, Sharp MA, Foulis SA. Maintaining physical performance: the minimal dose of exercise needed to preserve endurance and strength over time. *J Strength Cond Res* 2021. PMID 33629972, doi:10.1519/JSC.0000000000003964
76. Staron RS, Leonardi MJ, Karapondo DL, et al. Strength and skeletal muscle adaptations in heavy-resistance-trained women after detraining and retraining. *J Appl Physiol* 1991. PMID 1827108, doi:10.1152/jappl.1991.70.2.631
77. Taber CB, Vigotsky A, Nuckols G, Haun CT. Exercise-induced myofibrillar hypertrophy is a contributory cause of gains in muscle strength. *Sports Med* 2019. PMID 31016546, doi:10.1007/s40279-019-01107-8
78. Tagawa R, Watanabe D, Inoue Y, et al. Comparison of protein requirements based on the nitrogen balance and indicator amino acid oxidation methods: an umbrella review and meta-analysis. *J Nutr* 2025. PMID 40914512, doi:10.1016/j.tjnut.2025.08.036
79. Therdyothin A, Prokopidis K, Galli F, et al. The effects of omega-3 polyunsaturated fatty acids on muscle and whole-body protein synthesis: a systematic review and meta-analysis. *Nutr Rev* 2025. PMID 38777807, doi:10.1093/nutrit/nuae055
80. Tomlinson DJ, Erskine RM, Morse CI, et al. The impact of obesity on skeletal muscle strength and structure through adolescence to old age. *Biogerontology* 2016. PMID 26667010, doi:10.1007/s10522-015-9626-4
81. Tomlinson PB, Joseph C, Angioi M. Effects of vitamin D supplementation on upper and lower body muscle strength levels in healthy individuals. A systematic review with meta-analysis. *J Sci Med Sport* 2015. PMID 25156880, doi:10.1016/j.jsams.2014.07.022
82. van Dronkelaar C, van Velzen A, Abdelrazek M, et al. Minerals and sarcopenia; the role of calcium, iron, magnesium, phosphorus, potassium, selenium, sodium, and zinc on muscle mass, muscle strength, and physical performance in older adults: a systematic review. *J Am Med Dir Assoc* 2018. PMID 28711425, doi:10.1016/j.jamda.2017.05.026
83. Wall BT, Dirks ML, Snijders T, et al. Substantial skeletal muscle loss occurs during only 5 days of disuse. *Acta Physiol (Oxf)* 2014. PMID 24168489, doi:10.1111/apha.12190
84. Weinheimer EM, Sands LP, Campbell WW. A systematic review of the separate and combined effects of energy restriction and exercise on fat-free mass in middle-aged and older adults: implications for sarcopenic obesity. *Nutr Rev* 2010. PMID 20591106, doi:10.1111/j.1753-4887.2010.00298.x
85. Zaromskyte G, Prokopidis K, Ioannidis T, et al. Evaluating the leucine trigger hypothesis to explain the post-prandial regulation of muscle protein synthesis in young and older adults: a systematic review. *Front Nutr* 2021. PMID 34307436, doi:10.3389/fnut.2021.685165
