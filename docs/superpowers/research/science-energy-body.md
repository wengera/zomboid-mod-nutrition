# Science: energy, body composition, muscle, hydration, starvation

Research note for the realism nutrition mod. Scope: resting and activity energy expenditure, body-composition
dynamics, protein and muscle, "muscle memory", strength, hydration, starvation and excess adiposity.
Compiled 2026-09-27.

## How to read this

Grades, strongest first:

| Grade | Meaning |
|---|---|
| `MA` | Meta-analysis or systematic review |
| `RCT` | Randomised controlled trial (or a controlled crossover/inpatient trial) |
| `COH` | Cohort, observational, or a regression derived from a measured cross-section |
| `AUTH` | Authoritative report (IOM/NASEM DRI, EFSA, WHO, ACSM position stand, consensus statement) |
| `TXT` | Narrative review, textbook chapter, or modelling paper |

Every citation in this document was verified by fetching its Europe PMC / PubMed / publisher record and
confirming that title, authors, journal and year match the citation as written. A claim that could not be
verified against a primary record is marked **unverified** inline and must not be used as evidence.

Two recurring cautions:

- **Abstract-level numbers only.** Where a coefficient or effect size appears below, it was taken from the
  paper's own abstract or from a record I fetched. Where a widely quoted number lives only in a paywalled
  full text, it is marked **unverified**.
- **Population transfer.** Almost all of this literature is in healthy young-to-middle-aged adults, athletes,
  or overweight/obese adults in clinics. None of it was measured on people doing multi-week manual labour
  under food scarcity while fighting. Treat every number as a central tendency to be widened, not a constant.

Units: energy in kcal/d unless stated; `W` = body weight (kg), `H` = height (cm), `A` = age (y),
`FFM` = fat-free mass (kg), `FM` = fat mass (kg), `LBM` = lean body mass (kg).

## 1. Resting energy expenditure

| effect or parameter | value / equation | range or uncertainty | population | grade | citation |
|---|---|---|---|---|---|
| Mifflin–St Jeor REE, combined | `REE = 9.99·W + 6.25·H − 4.92·A + 166·sex − 161` (sex: male 1, female 0) | R² = 0.71 | 498 healthy adults, 19–78 y (mean 45 ± 14), 251 M / 247 F, 264 normal-weight and 234 obese, US, indirect calorimetry | COH | Mifflin et al. 1990, Am J Clin Nutr, PMID 2305711, doi:10.1093/ajcn/51.2.241 |
| Mifflin–St Jeor, men | `REE = 10·W + 6.25·H − 5·A + 5` | simplification did not reduce predictive value | as above | COH | Mifflin et al. 1990 (as above) |
| Mifflin–St Jeor, women | `REE = 10·W + 6.25·H − 5·A − 161` | as above | as above | COH | Mifflin et al. 1990 (as above) |
| REE from FFM alone (same cohort) | `REE = 19.7·FFM + 413` | R² = 0.64 — the best single predictor in that cohort | as above | COH | Mifflin et al. 1990 (as above) |
| REE from body weight alone | `REE = 15.1·W + 371` | R² = 0.56 | as above | COH | Mifflin et al. 1990 (as above) |
| Cunningham / Katch–McArdle lean-mass equation | `REE = 370 + 21.6·FFM` | explains 65–90 % of REE variance across studies; no independent contribution of FM in the general population (FM may predict in obese women) | synthetic review of adult two-compartment studies over a broad weight range | TXT (synthesis of COH studies) | Cunningham 1991, Am J Clin Nutr, PMID 1957828, doi:10.1093/ajcn/54.6.963 |
| Earlier Cunningham reanalysis | `RMR = 500 + 22·LBM` — **unverified** (the 1980 abstract record I fetched does not carry the coefficients) | — | normal adults | COH | Cunningham 1980, Am J Clin Nutr, PMID 7435418, doi:10.1093/ajcn/33.11.2372 |
| Revised Harris–Benedict (Roza & Shizgal) | Precision ≈ ±14 % in normally nourished subjects; REE tracks **body cell mass** and is independent of age and sex once body cell mass is accounted for; unreliable in malnutrition, where it **underestimates** measured REE | ±14 % | 239 original Harris–Benedict subjects + 98 published subjects over wider age ranges; tested in 74 normally nourished and malnourished patients | COH | Roza & Shizgal 1984, Am J Clin Nutr, PMID 6741850, doi:10.1093/ajcn/40.1.168 |
| Revised Harris–Benedict coefficients | men `88.362 + 13.397·W + 4.799·H − 5.677·A`; women `447.593 + 9.247·W + 3.098·H − 4.330·A` — **unverified**: the coefficients are not in the abstract and the full text was paywalled to this run | — | — | — | Roza & Shizgal 1984 (record verified; coefficients not) |
| Most accurate equation per validation review | Mifflin–St Jeor "was the most reliable, predicting RMR within 10 % of measured in more nonobese and obese individuals than any other equation" (vs Harris–Benedict, Owen, WHO/FAO/UNU) | "noteworthy errors and limitations exist when it is applied to individuals"; older adults and US ethnic minorities under-represented | systematic review of validation studies in healthy nonobese and obese adults | MA | Frankenfield, Roth-Yousey & Compher 2005, J Am Diet Assoc, PMID 15883556, doi:10.1016/j.jada.2005.02.005 |
| Organ/tissue specific metabolic rates (Elia's values, evaluated) | liver 200, brain 240, heart 440, kidneys 440, **skeletal muscle 13**, **adipose tissue 4.5**, residual 12 — all kcal·kg⁻¹·d⁻¹ | confirmed for younger adults; minor downward adjustment appropriate above 50 y | 131 healthy adults in three age groups, MRI organ volumes + indirect calorimetry | COH | Wang et al. 2010, Am J Clin Nutr, PMID 20962155, doi:10.3945/ajcn.2010.29885 |
| Organ-tissue model of REE | REE can be modelled from measured organ/tissue masses and metabolically active tissue mass | — | adults, MRI + indirect calorimetry | COH | Gallagher et al. 1998, Am J Physiol, PMID 9688626, doi:10.1152/ajpendo.1998.275.2.E249 |
| Adaptive thermogenesis after weight loss — existence | AT reported in 27 of 33 studies; significant AT for REE in 23 studies (82.8 % of those measuring REE), for TDEE in 4 (80 %), for sleeping EE in 2 (100 %). **But** "well-designed studies reported lower or non-significant values for AT", and AT "seems to be attenuated, or non-existent, after periods of weight stabilisation/neutral energy balance" | large heterogeneity in how AT is quantified and in its magnitude | 33 studies, 2528 adults | MA | Nunes et al. 2022, Br J Nutr, PMID 33762040, doi:10.1017/S0007114521001094 |
| Adaptive thermogenesis — persistence | After ≥10 % weight loss maintained >1 y, total EE, non-resting EE and (less so) REE were significantly lower than in never-reduced matched controls: "declines in energy expenditure favouring the regain of lost weight persist well beyond the period of dynamic weight loss" | 7 matched subject trios, inpatient, controlled liquid-formula diets — small n | weight-reduced adults | RCT-adjacent (controlled inpatient) | Rosenbaum et al. 2008, Am J Clin Nutr, PMID 18842775, doi:10.1093/ajcn/88.4.906 |
| Adaptive thermogenesis — review of mechanism | Narrative review of AT in humans, its measurement and its role in resisting weight loss | — | humans | TXT | Rosenbaum & Leibel 2010, Int J Obes (Lond), PMID 20935667, doi:10.1038/ijo.2010.184 |
| What AT tracks (Minnesota re-analysis) | The reduction in thermogenesis (ΔBMR adjusted for ΔFFM and ΔFM) correlated positively with the degree of **fat-mass** depletion (r ≈ 0.5, p < 0.01) during both loss and recovery, and **not** with FFM depletion; residual variance predicted by pre-starvation % fat and cormic index | r ≈ 0.5 | re-analysis of the 32 men of the Minnesota semi-starvation experiment, at weeks 12 and 24 of semi-starvation and week 12 of restricted refeeding | COH (re-analysis of a controlled experiment) | Dulloo & Jacquet 1998, Am J Clin Nutr, PMID 9734736, doi:10.1093/ajcn/68.3.599 |
| AT is required to fit the Minnesota data | A mechanistic model of energy metabolism reproduced the measured RMR of the Minnesota experiment only with an explicit adaptive-thermogenesis term | — | model fitted to the Minnesota experiment, validated against a short-term caloric-restriction study | TXT (model) | Hall 2006, Am J Physiol Endocrinol Metab, PMID 16449298, doi:10.1152/ajpendo.00523.2005 |

**For a game model.** Use Mifflin–St Jeor for the baseline resting burn when the character is described by
weight, height, age and sex — it is the equation the one systematic review on the question puts first, and its
coefficients are verified. If the mod tracks fat and lean mass separately (which a realism nutrition mod
probably should), prefer a lean-mass form: `REE = 370 + 21.6·FFM` (Cunningham) or `REE = 19.7·FFM + 413`
(Mifflin's own FFM regression) — they agree closely across the plausible FFM range and remove the need to
model sex and age separately. Do **not** model REE as proportional to total mass with a single coefficient:
the organ-tissue numbers show why. Skeletal muscle burns only ~13 kcal·kg⁻¹·d⁻¹ and adipose ~4.5, while liver,
brain, heart and kidney burn 200–440; so the ~20 kcal·kg⁻¹·d⁻¹ slope of a whole-body FFM regression is an
artefact of organs co-varying with FFM in a cross-section, and adding 1 kg of trained muscle in-game should
add on the order of 13 kcal/d, not 20. Adaptive thermogenesis is real but modest and contested: the safest
implementation is a small multiplicative REE suppression that grows with **fat depletion** (Dulloo &
Jacquet's finding), saturating at perhaps 10–15 %, and that decays away once weight is stable again (Nunes).
Resist a large "starvation mode" — the best-designed studies in the systematic review found the smallest
effect, and there is no verified basis for a suppression that halves maintenance calories. One asymmetry is
worth keeping because it is well supported: predictive equations **underestimate** REE in the malnourished
(Roza & Shizgal), so a starved character should not be modelled as unusually efficient per kg of remaining
tissue.

## 2. Activity energy expenditure

By convention 1 MET = 1 kcal·kg⁻¹·h⁻¹ (3.5 ml O₂·kg⁻¹·min⁻¹), so a MET value converts directly:
`kcal/h = MET × body mass (kg)`. All MET values below were read from the official Compendium of Physical
Activities website, which publishes the **2024 Adult Compendium** (Herrmann et al. 2024). The 2011 Compendium
asked for in the brief is the previous edition (Ainsworth et al. 2011, 821 activity codes, 68 % with measured
MET values); its values are **not identical** — sleeping was 0.9 MET in 2011 and is 1.0 MET in 2024 — so the
values here are cited to the 2024 edition and the 2011 paper is cited only for the edition and its coverage.

| effect or parameter | value / equation | range or uncertainty | population | grade | citation |
|---|---|---|---|---|---|
| Sleeping | 1.0 MET | — | adults 19–59 y | AUTH | Herrmann et al. 2024, J Sport Health Sci, PMID 38242596, doi:10.1016/j.jshs.2023.10.010 |
| Lying quietly awake; sitting quietly | 1.0 MET (sitting fidgeting 1.5) | — | as above | AUTH | Herrmann et al. 2024 |
| Standing quietly | 1.3 MET (standing fidgeting 1.5) | — | as above | AUTH | Herrmann et al. 2024 |
| Walking 3.2–3.9 km/h (2.0–2.4 mph) | 2.8 MET | — | as above | AUTH | Herrmann et al. 2024 |
| Walking 4.0 km/h (2.5 mph) | 3.0 MET | — | as above | AUTH | Herrmann et al. 2024 |
| Walking 4.5–5.5 km/h (2.8–3.4 mph) | 3.8 MET | — | as above | AUTH | Herrmann et al. 2024 |
| Walking 5.6–6.3 km/h (3.5–3.9 mph) | 4.8 MET | — | as above | AUTH | Herrmann et al. 2024 |
| Walking 6.4–7.1 km/h (4.0–4.4 mph) | 5.5 MET | — | as above | AUTH | Herrmann et al. 2024 |
| Walking 7.2–7.9 km/h (4.5–4.9 mph) | 7.0 MET | — | as above | AUTH | Herrmann et al. 2024 |
| Walking 8.0–8.9 km/h (5.0–5.5 mph) | 8.5 MET | — | as above | AUTH | Herrmann et al. 2024 |
| Jogging, general, self-selected pace | 7.5 MET | jogging in place 4.8 | as above | AUTH | Herrmann et al. 2024 |
| Running 9.7–10.1 km/h (6–6.3 mph, 10 min/mile) | 9.3 MET | — | as above | AUTH | Herrmann et al. 2024 |
| Running 12.1 km/h (7.5 mph, 8 min/mile) | 11.8 MET | — | as above | AUTH | Herrmann et al. 2024 |
| Running 12.9 km/h (8 mph, 7.5 min/mile) | 12.0 MET | — | as above | AUTH | Herrmann et al. 2024 |
| Running 16.1 km/h (10 mph, 6 min/mile) | 14.8 MET | — | as above | AUTH | Herrmann et al. 2024 |
| Running 19.3 km/h (12 mph, 5 min/mile) | 18.5 MET | — | as above | AUTH | Herrmann et al. 2024 |
| Running 22.5 km/h (14 mph, 4.3 min/mile) | 23.0 MET — the Compendium's highest listed value | **Sprinting proper has no Compendium entry.** Any value above 23 MET is extrapolation, and a true all-out sprint is anaerobic, so a steady-state MET model does not describe it at all | as above | AUTH | Herrmann et al. 2024; the 2011 edition's range was 0.9 (sleeping) to 23 MET (running 14 mph), Ainsworth et al. 2011, PMID 21681120 |
| Walking with a load, level ground | "Carrying 5 to 14 lb load, level ground, moderate pace" 4.0 MET; "Carrying 15–155 lb load, level ground or downstairs, slow pace" 4.5 MET; "Carrying 50 to 150 pound load, level ground, moderate pace" 6.5 MET | The Compendium's load bands are very wide (15–155 lb in one entry), so it is a poor instrument for modelling a load gradient — use Pandolf for that | as above | AUTH | Herrmann et al. 2024 |
| Backpacking / hiking with a daypack | backpacking 7.0 MET; walking with a daypack, level, in a city 3.5 MET; hiking with a daypack, organized walking 7.8 MET | — | as above | AUTH | Herrmann et al. 2024 |
| Carrying loads **upstairs** | 1–15 lb 5.5 MET; 16–24 lb 6.0; 25–49 lb 8.0; 50–74 lb 10.0; >74 lb 12.0 MET | monotone in load — usable as a gradient | as above | AUTH | Herrmann et al. 2024 |
| Chopping wood | "Chopping wood, splitting logs, moderate effort" 4.5 MET; "vigorous effort" 6.5 MET. Occupational forestry, axe chopping with a 1.25 kg axe: 19 blows/min 5.0; 35 blows/min 8.0; **51 blows/min 17.5 MET** | The 17.5 MET entry is an extreme, short-duration work rate, not a sustainable one | as above | AUTH | Herrmann et al. 2024 |
| Carrying / stacking wood | light-to-moderate effort 4.1 MET; moderate effort 5.5 MET | — | as above | AUTH | Herrmann et al. 2024 |
| Construction and carpentry | carpentry light 2.5, moderate 4.3, heavy/vigorous 7.0 MET; construction, outside, remodeling 4.0; roofing 6.0; "carpentry, sawing hardwood, planing and drilling wood, moderate-to-vigorous" 6.0; hammering nails 3.0; home repair vigorous 6.0; using heavy power tools (pneumatic) 6.3 MET | — | as above | AUTH | Herrmann et al. 2024 |
| Digging and shovelling | "Shoveling, digging ditches" 7.3 MET; shovelling >16 lb/min, deep digging, vigorous 8.8; 10–15 lb/min vigorous 6.5; <10 lb/min moderate 5.0; garden digging/spading light-to-moderate 3.5, general 5.0, vigorous 7.3; shovelling dirt or mud 5.5; shovelling snow by hand 5.3–7.5 MET | — | as above | AUTH | Herrmann et al. 2024 |
| Fighting-like effort | boxing in ring, general **12.3 MET**; boxing sparring 7.8; punching bag 5.8 (60 b/min 7.0, 120 b/min 8.5, 180 b/min 10.8); martial arts moderate pace 10.3; taekwondo combat simulation 14.3; judo 11.3; kickboxing 7.3; competitive wrestling (5-min match) 6.0 MET | Combat MET values are for trained athletes in bouts of minutes, not for sustained work | as above | AUTH | Herrmann et al. 2024 |
| Climbing | rock or mountain climbing 8.0 MET; ascending rock, high difficulty 7.3; low-to-moderate difficulty 5.8; speed climbing, very difficult 10.5; rappelling 5.0 MET | — | as above | AUTH | Herrmann et al. 2024 |
| kcal per kg per km, walking (**derived**) | Gross ≈ **0.76–0.81** kcal·kg⁻¹·km⁻¹ across 5–7 km/h; net of rest ≈ **0.56–0.67**, rising with speed. (Derived: 3.8 MET ÷ 4.99 km/h = 0.76; 4.8 ÷ 5.95 = 0.81; 5.5 ÷ 6.76 = 0.81) | derived arithmetic from verified MET values and the MET definition, not a measured regression | as above | AUTH (derived) | Herrmann et al. 2024 (MET values); arithmetic mine |
| kcal per kg per km, running (**derived**) | Gross ≈ **0.92–0.96** kcal·kg⁻¹·km⁻¹; net of rest ≈ **0.86**, and remarkably **flat with speed**. (Derived: 9.3 ÷ 9.66 = 0.96; 12.0 ÷ 12.87 = 0.93; 14.8 ÷ 16.09 = 0.92) | as above | as above | AUTH (derived) | Herrmann et al. 2024 (MET values); arithmetic mine |
| Measured energy cost of 1600 m | Running 481 ± 20 kJ vs walking 340 ± 14 kJ on a treadmill (track: 480 ± 23 vs 334 ± 14 kJ) at 2.82 and 1.41 m·s⁻¹. Running costs more than walking for the same distance | Per-kg normalisation not possible from the abstract (mean body mass not reported there) | 24 subjects, indirect calorimetry, treadmill and track | RCT (crossover) | Hall C et al. 2004, Med Sci Sports Exerc, PMID 15570150, doi:10.1249/01.MSS.0000147584.87788.0E |
| Which prediction equations work | For **running**, the Léger and ACSM equations predicted measured cost well (ACSM total error −20 kJ per 1600 m); for **walking**, the ACSM and **Pandolf** equations predicted it well (Pandolf error −10.0 kJ). McArdle's table and van der Walt's equation overestimated; Epstein's underestimated running | — | as above | RCT | Hall C et al. 2004 (as above) |
| Pandolf load-carriage metabolic equation | `M = 1.5·W + 2.0·(W+L)·(L/W)² + η·(W+L)·(1.5·V² + 0.35·V·G)` with M in watts, W = body mass (kg), L = load (kg), V = speed (m·s⁻¹), G = grade (%), η = terrain factor. **The coefficient set is unverified**: the citation is verified but the primary paper carries no abstract in the indexing records and its full text was paywalled to this run, so the coefficients above come from secondary reproductions | The equation is known to **under-predict** the metabolic rate of contemporary military load carriage (see Gaps) | soldiers standing or walking very slowly with loads | AUTH (citation verified; coefficients unverified) | Pandolf, Givoni & Goldman 1977, J Appl Physiol, PMID 908672, doi:10.1152/jappl.1977.43.4.577 |
| Terrain factors (η) | Primary source for terrain coefficients. Commonly reproduced values — blacktop/treadmill 1.0, dirt road 1.1, light brush 1.2, heavy brush 1.5, swampy bog 1.8, loose sand 2.1, soft snow 15/25/35 cm 2.5/3.3/4.1 — are **unverified** against the primary text | as above | measured across blacktop, dirt road, light brush, heavy brush, swampy bog and loose sand | AUTH (citation verified; values unverified) | Soule & Goldman 1972, J Appl Physiol, PMID 5038861, doi:10.1152/jappl.1972.32.5.706 |
| Cold exposure: peak shivering thermogenesis | **Shiv_peak = 4.9 ± 0.8 × resting metabolic rate**, i.e. 22.1 ± 4.2 ml O₂·kg⁻¹·min⁻¹, equal to **41.7 ± 5.1 % of V̇O₂max**. Prediction: `Shiv_peak (ml O₂·kg⁻¹·min⁻¹) = 30.5 + 0.348·V̇O₂max − 0.909·BMI − 0.233·age` (p = 0.0001, r² = 0.872) | ±0.8 × RMR; n = 15 | 15 adults (4 women), mean 24.7 y, 72.1 kg, 22.3 % fat, V̇O₂max 53.2, immersed in 8 °C then 20 °C water | RCT | Eyolfson et al. 2001, Eur J Appl Physiol, PMID 11394237, doi:10.1007/s004210000329 |
| Cold exposure: sustained shivering rate and its fuel | Metabolic rate rose to **3.5 ± 0.3 × resting** during 90 min immersion in 18 °C water; vastus lateralis glycogen fell from 410 ± 15 to 332 ± 18 mmol glucose·kg dry muscle⁻¹ in every subject (p < 0.001), proving muscle glycogen is a substrate for shivering | ±0.3 × resting; n = 14 | 14 seminude subjects, 18 °C water, 90 min or until T_re 35.5 °C | RCT | Martineau & Jacobs 1988, J Appl Physiol, PMID 3209549, doi:10.1152/jappl.1988.65.5.2046 |
| Cold: fuel selection and survival | Shivering can be sustained for hours on varied fuel mixtures; on a glycogen-depletion model, **selective recruitment of fuel-specific muscle fibres, not the fuel mixture itself, gives a substantial survival advantage** in the cold | qualitative | review | TXT | Haman 2006, J Appl Physiol, PMID 16614367, doi:10.1152/japplphysiol.01088.2005; Haman & Blondin 2017, Temperature (Austin), PMID 28944268, doi:10.1080/23328940.2017.1328999 |

**For a game model.** MET × body mass × hours is the right backbone for activity burn, and it is cheap: one
table lookup per activity state. The verified numbers give a clean ladder — idle 1.0, standing 1.3, walking
2.8–8.5 depending on pace, jogging 7.5, running 9.3–23, heavy labour 5–9, combat 8–14, climbing 6–10. Two
things deserve special handling. First, **load**: the Compendium's load bands are useless as a gradient
(one entry spans 15–155 lb), so use the upstairs series (5.5 → 12.0 MET from <15 lb to >74 lb) for vertical
work and the Pandolf form for horizontal load carriage, with the caveat that its coefficients here are
unverified and that it is known to under-predict modern heavy-load carriage. Pandolf's structure is the
valuable part regardless of coefficients: cost rises with the **square** of the load-to-body-mass ratio, with
the **square** of speed, and multiplicatively with a terrain factor — so a heavy pack on soft ground at speed
is punitive in a way a linear model never captures, and terrain multipliers from 1.0 (road) to ~2.1 (sand) to
~4 (deep snow) are the right order of magnitude. Second, **sprinting is not in this framework at all**; the
Compendium stops at 23 MET and an all-out sprint is anaerobic, so model sprinting as a depletable stamina
resource rather than as a very high MET. For distance-based costs the derived constants are convenient and
well anchored: roughly **0.8 kcal/kg/km walking and 0.95 kcal/kg/km running gross**, with net running cost
almost independent of speed — so running a given distance costs about the same whatever the pace, but running
*fast* costs more per hour. Cold is worth modelling: shivering tops out near **5× resting** and about 42 % of
V̇O₂max, it burns muscle glycogen, and a lean, low-BMI character shivers harder (the Eyolfson equation has a
negative BMI term) — which combines neatly with § 9's insulation result to make body fat genuinely protective
in the cold.

## 3. Body composition dynamics

| effect or parameter | value / equation | range or uncertainty | population | grade | citation |
|---|---|---|---|---|---|
| The "3500 kcal per pound" rule | 3500 kcal/lb = 32.2 MJ/kg ≈ 7700 kcal per kg of body weight lost | It "approximately matches the predicted energy density of lost weight in obese subjects with an initial body fat above 30 kg but overestimates the cumulative energy deficit required per unit weight loss for people with lower initial body fat" | modelling, checked against published weight-loss data from obese and lean subjects | TXT (model on COH data) | Hall 2008, Int J Obes (Lond), PMID 17848938, doi:10.1038/sj.ijo.0803720 |
| Direction of the energy-density effect | Required cumulative deficit per kg lost **rises** with initial body fat, and **falls** as weight loss continues (because a growing share of the loss is lean tissue, which has a much lower energy density than fat) | qualitative, direction well supported | as above | TXT | Hall 2008 (as above) |
| Why men lose more weight than women at the same deficit | Women typically carry more fat at the same body weight, so their lost weight has a higher energy density | qualitative | as above | TXT | Hall 2008 (as above) |
| Forbes partition, extended | Forbes's equation gives the fat-free share of a weight change as a function of initial body fat; Hall extended it to finite (macroscopic) weight changes and re-expressed it via an energy-partitioning **P-ratio**. Predictions matched human under- and over-feeding data. Magnitude of the weight change has a *weak* effect for modest changes (so Forbes's original form is adequate there) but Forbes's original consistently **underestimates** FFM loss for very large losses (e.g. post-bariatric) | — | derivation checked against human underfeeding and overfeeding experiments | TXT (model on RCT/COH data) | Hall 2007, Br J Nutr, PMID 17367567, doi:10.1017/S0007114507691946 |
| Forbes's own statement of the effect | Body fat content influences the body-composition response to nutrition and exercise: the fatter the starting body, the smaller the lean share of a weight change | — | humans, review of the author's own datasets | TXT | Forbes 2000, Ann N Y Acad Sci, PMID 10865771, doi:10.1111/j.1749-6632.2000.tb06482.x |
| Maximum energy transfer rate out of the fat store | **290 ± 25 kJ·kg fat⁻¹·d⁻¹** (≈ 69 ± 6 kcal·kg fat⁻¹·d⁻¹). A dietary restriction exceeding what the fat store can supply at this rate causes an immediate decrease in fat-free mass; a less severe deficit does not deplete FFM | ±25 kJ/kg/d | derived from experimental data on underfed subjects maintaining moderate activity | TXT (model on RCT/COH data) | Alpert 2005, J Theor Biol, PMID 15615615, doi:10.1016/j.jtbi.2004.08.029 |
| RMR vs FFM slope in hypophagia | Average RMR of hypophagic subjects fell linearly with FFM, slope **249 ± 25 kJ·kg FFM⁻¹·d⁻¹** (≈ 59 kcal·kg⁻¹·d⁻¹) — the author notes this disagrees with cross-sectional measurements in diverse groups | ±25 kJ/kg/d | underfed subjects | TXT | Alpert 2005 (as above) |
| Energy density of weight loss in semi-starvation | Dedicated analysis of the energy density of lost weight under semi-starvation | — | semi-starved humans | TXT | Alpert 1988, Int J Obes, PMID 3235270 (no DOI in record) |
| Overfeeding partitioning, between-individual variance | +4.2 MJ/d (≈ +1000 kcal/d) for 84 of 100 days produced weight gains of **4.3 to 13.3 kg** — a threefold range at an identical energy surplus. Variance **between** twin pairs was ~3× that **within** pairs, for body weight, fat gain and fat distribution | 4.3–13.3 kg; genetic control of partitioning | 12 pairs of identical young adult male twins, inpatient-controlled overfeeding | RCT | Bouchard et al. 1990, N Engl J Med, PMID 2336074, doi:10.1056/NEJM199005243222101 |
| De novo lipogenesis and fat overshoot on refeeding | Refeeding after semi-starvation caused an elevation of de novo lipogenesis which, with increased fat intake, produced **rapid repletion and overshoot of body fat**. Continuing pre-starvation diet and activity eventually restored original weight and composition, but fat mass was predicted to need **more than one additional year** to come within 5 % of its original value | model prediction, fitted to the Minnesota experiment | Minnesota semi-starvation and refeeding | TXT (model) | Hall 2006, Am J Physiol Endocrinol Metab, PMID 16449298, doi:10.1152/ajpendo.00523.2005 |

**For a game model.** Do not use a single kcal-per-kg constant for weight change. The defensible minimum is a
two-compartment store (fat, lean) with distinct energy densities, and a partition rule whose lean share falls
as fat mass rises — that is exactly the Forbes/Hall result, and it makes a lean character lose lean tissue
fast and a fat character lose mostly fat, which is the correct and dramatically useful behaviour. The 7700
kcal/kg figure is fine as the *observed* energy density of weight lost by a fat character and wrong for a lean
one; treat it as an output of the model, not an input. Alpert's 290 kJ·kg fat⁻¹·d⁻¹ ceiling is the single most
useful number here for a survival game: it converts a character's fat mass directly into a maximum sustainable
daily deficit that fat can cover, and any deficit beyond it comes out of lean mass immediately. For a 70 kg
character with 10 kg fat that is ~2900 kJ/d ≈ 690 kcal/d from fat; a larger deficit starts eating muscle the
same day. Refeeding should overshoot fat and restore lean more slowly — both are supported (Hall 2006) — and
the overshoot is a good mechanic. What is **not** supported is a fixed "you regain X kg per week" rate:
Bouchard shows a threefold individual spread in the response to an identical surplus, so a game should pick a
per-character partitioning constant and keep it, rather than pretending the population mean applies to
everyone.

## 4. Protein and muscle

| effect or parameter | value / equation | range or uncertainty | population | grade | citation |
|---|---|---|---|---|---|
| Protein intake beyond which resistance-training gains plateau | **1.62 g·kg⁻¹·d⁻¹** total protein; intakes above this gave no further benefit | The widely quoted 95 % CI of 1.03–2.20 g·kg⁻¹·d⁻¹ is **unverified** here (not in the abstract record) | 49 RCTs, 1863 participants, resistance training ≥6 wk | MA | Morton et al. 2018, Br J Sports Med, PMID 28698222, doi:10.1136/bjsports-2017-097608 |
| Effect size of protein supplementation with resistance training | 1RM strength **+2.49 kg**, fat-free mass **+0.30 kg**, plus increased muscle size, vs control | effect diminished with advancing age, increased in already resistance-trained individuals | as above | MA | Morton et al. 2018 (as above) |
| Protein intake during an energy deficit | **1.6–2.4 g·kg⁻¹·d⁻¹**, position within the range set by the severity of the deficit and the training load | recommendation range, not a measured optimum | elite athletes losing weight | TXT (expert review of RCT evidence) | Hector & Phillips 2018, Int J Sport Nutr Exerc Metab, PMID 29182451, doi:10.1123/ijsnem.2017-0273 |
| Protein dose in a 40 % deficit with heavy training | 2.4 vs 1.2 g·kg⁻¹·d⁻¹ over 4 wk: lean mass **+1.2 ± 1.0 kg** vs **+0.1 ± 1.0 kg**; fat mass **−4.8 ± 1.6 kg** vs **−3.5 ± 1.4 kg**. Exercise performance improved similarly in both | ±1.0 kg SD on lean change — individual variation is as large as the mean effect | 40 young men, 4 wk, 40 % caloric deficit, resistance + HIIT 6 d/wk, single-blind RCT | RCT | Longland et al. 2016, Am J Clin Nutr, PMID 26817506, doi:10.3945/ajcn.115.119339 |
| Per-meal protein dose to maximally stimulate myofibrillar protein synthesis | Young men **0.24 ± 0.06 g·kg body mass⁻¹** per meal (0.25 ± 0.13 g·kg LBM⁻¹); older men **0.40 ± 0.19 g·kg⁻¹** (0.60 ± 0.29 g·kg LBM⁻¹) | SDs as shown; older men "are less sensitive to low protein intakes" | pooled young (~22 y) and older (~71 y) men, 0–40 g protein doses | COH (pooled re-analysis of trials) | Moore et al. 2015, J Gerontol A Biol Sci Med Sci, PMID 25056502, doi:10.1093/gerona/glu103 |
| Lean-mass gain rate achievable in a deficit | **+1.2 kg lean in 4 weeks** ≈ 0.3 kg/wk, with high protein + 6 d/wk training in a 40 % deficit | ±1.0 kg SD | untrained/recreationally active young men | RCT | Longland et al. 2016 (as above) |
| Hypertrophy rate with training, magnitude | Quadriceps CSA **+~17 %** and muscle thickness +~10 % over 10 weeks of unilateral strength training (≈0.24 %/d on CSA) | single trial | 9 men, 10 women, 10 wk | RCT | Psilander et al. 2019, J Appl Physiol, PMID 30991013, doi:10.1152/japplphysiol.00917.2018 |
| Dose–response for hypertrophy | Given sufficient frequency, intensity and volume, dynamic, accommodating and isometric resistance all induce significant hypertrophy "at an impressive rate"; no mode or muscle-action type is demonstrably superior | The review's numerical rate table is **not** in the abstract, so no per-week rate is quoted here as verified | comprehensive review, quadriceps femoris and elbow flexors | MA | Wernbom, Augustsson & Thomeé 2007, Sports Med, PMID 17326698, doi:10.2165/00007256-200737030-00004 |
| Muscle loss during immobilisation | Quadriceps CSA **−3.5 ± 0.5 %** after 5 days and **−8.4 ± 2.8 %** after 14 days of one-legged knee immobilisation (≈0.7 %/d early, ≈0.6 %/d averaged over 14 d). Muscle myostatin mRNA doubled | ±0.5 % and ±2.8 % | 24 healthy young men | RCT | Wall et al. 2014, Acta Physiol (Oxf), PMID 24168489, doi:10.1111/apha.12190 |
| Strength loss during immobilisation | **−9.0 %** at 5 days, **−22.9 %** at 14 days | — | as above | RCT | Wall et al. 2014 (as above) |
| Mechanism of disuse atrophy | Short-term disuse lowers myofibrillar protein synthesis and induces anabolic resistance to protein ingestion; review of short-term disuse atrophy and its implications | — | healthy young and older men | TXT / RCT | Wall, Dirks & van Loon 2013, Ageing Res Rev, PMID 23948422, doi:10.1016/j.arr.2013.07.003; Wall et al. 2016, Am J Physiol Endocrinol Metab, PMID 26578714, doi:10.1152/ajpendo.00227.2015 |
| Lean share of weight loss with and without exercise | **81 %** of energy-restriction-only groups, but only **39 %** of energy-restriction-plus-exercise groups, lost ≥15 % of their body-weight loss as fat-free mass | 52 studies; middle-aged and older adults only | overweight/obese adults >50 y, BMI >25 | MA | Weinheimer, Sands & Campbell 2010, Nutr Rev, PMID 20591106, doi:10.1111/j.1753-4887.2010.00298.x |
| Upper limits of protein intake | Gut can absorb amino acids at **1.3–10 g/h**. A suggested maximum safe intake is **~2–2.5 g·kg⁻¹·d⁻¹** (≈25 % of energy, ≈176 g/d for an 80 kg person on 12 000 kJ/d); the theoretical maximum safe range for 80 kg is 285–365 g/d. Protein above **~35 % of total energy** produces hyperaminoacidaemia, hyperammonaemia, hyperinsulinaemia, nausea, diarrhoea "and even death (the 'rabbit starvation syndrome')" | review-level synthesis; the 35 %-of-energy ceiling is the load-bearing number | humans | TXT | Bilsborough & Mann 2006, Int J Sport Nutr Exerc Metab, PMID 16779921, doi:10.1123/ijsnem.16.2.129 |

**For a game model.** Protein has two distinct jobs and they need different thresholds. For *retention* under
a deficit, the evidence supports a target in the 1.6–2.4 g·kg⁻¹·d⁻¹ band, with the top of the band justified
only when the deficit is severe and training heavy (Hector & Phillips; Longland). For *gain*, the plateau is
~1.6 g·kg⁻¹·d⁻¹ (Morton) — above that, more protein buys nothing, which is an important anti-exploit
property for a mod. Model the protein effect as a modifier on the lean/fat partition ratio, not as a direct
muscle-building resource: Longland's high-protein group gained lean *and* lost more fat in a 40 % deficit,
which is exactly a partition shift. Per-meal distribution is supported well enough to justify a mechanic
(~0.24 g/kg per meal saturates synthesis in young adults, Moore 2015), so four moderate protein meals beat one
huge one; do not model a leucine threshold as a separate nutrient, because the verified evidence is about total
protein per meal, not about leucine dosing in a free-living diet. Disuse numbers give a clean, well-measured
rate for an injured or bed-ridden character: roughly **0.7 % of muscle CSA per day early**, with **strength
falling ~2.5× faster than size** (−9 % strength vs −3.5 % CSA at 5 days) — that asymmetry is a real and
game-useful finding. Exercise, not protein alone, is what protects lean mass during restriction (Weinheimer:
39 % vs 81 % of groups losing ≥15 % of weight as FFM), so a character who works hard while underfed should
lose a much smaller lean share than a sedentary one. Finally, a protein ceiling is evidenced and worth
modelling as a hard penalty: above ~35 % of energy from protein, the literature describes real toxicity, so a
mod that lets a player live on lean rabbit meat should punish it.

## 5. "Muscle memory"

| effect or parameter | value / equation | range or uncertainty | population | grade | citation |
|---|---|---|---|---|---|
| Myonuclear permanence (rodent) | Myonuclei acquired during overload **precede** hypertrophy and are **not lost** on detraining | — | mouse, in vivo time-lapse of single fibres | RCT (animal) | Bruusgaard et al. 2010, Proc Natl Acad Sci USA, PMID 20713720, doi:10.1073/pnas.0913935107 |
| No myonuclear loss during atrophy (rodent) | No loss of myonuclei over weeks of muscle atrophy | — | mouse | RCT (animal) | Bruusgaard & Gundersen 2008, J Clin Invest, PMID 18317591, doi:10.1172/JCI34022 |
| Cellular memory from a transient anabolic exposure (rodent) | An episodic anabolic-steroid exposure left a cellular memory that aided later overload hypertrophy "long after" the exposure | — | mouse | RCT (animal) | Egner et al. 2013, J Physiol, PMID 24167222, doi:10.1113/jphysiol.2013.264457 |
| Whether myonuclei are ever lost | Follow-up study directly asking the question in humans and animals | — | human and animal | RCT / TXT | Eftestøl et al. 2020, J Appl Physiol, PMID 31854249, doi:10.1152/japplphysiol.00761.2019 |
| Human test: train → detrain → retrain | 10 wk unilateral training: CSA **+~17 %**, thickness +~10 %, strength +~20 %, **myonuclear number unchanged**. 20 wk detraining: thickness and CSA returned to baseline but **strength remained elevated**. 5 wk bilateral retraining: the previously trained and the previously untrained leg responded **similarly**. Authors: the results neither strongly support nor refute human muscle memory, because the expected markers did not appear | single trial, n = 19 | 9 men, 10 women | RCT | Psilander et al. 2019, J Appl Physiol, PMID 30991013, doi:10.1152/japplphysiol.00917.2018 |
| Human test in older men | 12 wk training → 12 wk detraining → 12 wk retraining: gained strength, power and fibre-type changes were **partially preserved** through detraining, and maximal strength was recovered in **under 8 weeks** of retraining. Fibre growth during retraining correlated with myonuclear addition | n = 30 older + 10 young controls | older men | RCT | Blocquiaux et al. 2020, Exp Gerontol, PMID 32017951, doi:10.1016/j.exger.2020.110860 (corrigendum PMID 32147251, doi:10.1016/j.exger.2020.110897) |
| Human test in trained women | 20 wk training → 30–32 wk detraining → 6 wk retraining: fibre CSA remained relatively stable through detraining (type IIb % rose); 6 wk retraining significantly increased fast-fibre CSA in previously trained **and** previously untrained women. "Rapid muscular adaptations occur as a result of strength training in previously trained as well as non-previously trained women" | n = 6 retrained | women | RCT | Staron et al. 1991, J Appl Physiol, PMID 1827108, doi:10.1152/jappl.1991.70.2.631 |
| State of the hypothesis | The "muscle memory by myonuclear permanence" mechanism rests mainly on rodent models; "whether the postulated mechanism also holds true in humans remains largely ambiguous" | — | review of animal and human studies, plus new analysis of the authors' own prior training studies | TXT | Snijders et al. 2020, Acta Physiol (Oxf), PMID 32175681, doi:10.1111/apha.13465 |
| Framing review | Review of the muscle-memory concept and its implications | — | — | TXT | Gundersen et al. 2018, J Physiol, PMID 30145845, doi:10.1113/JP276354 |

**For a game model.** Faster regain of previously held lean mass can be justified, but **not** by myonuclear
permanence in humans — that mechanism is solid in rodents (Bruusgaard, Egner) and explicitly unresolved in
humans (Snijders; Psilander found no myonuclear change at all, and no advantage for the previously trained
leg). What *is* supported in humans is weaker and differently shaped: strength and fibre-type adaptations
partly survive detraining even when size does not (Psilander, Staron), and maximal strength returns in under
8 weeks of retraining in older men (Blocquiaux). So the defensible mechanic is a **strength/skill memory**
rather than a mass memory: after lean mass is lost, let the character's strength and work capacity come back
substantially faster than the mass itself, and let retraining restore prior peak strength in weeks rather than
months. If the mod also wants faster mass regain, label it a gameplay concession or rest it on the fat/lean
partitioning result from § 3 (a leaner body preferentially rebuilds lean tissue on refeeding) rather than
citing muscle memory. Do not claim a permanent, lifelong "trained once, always easier" bonus for lean mass —
the one human trial designed to detect exactly that (Psilander) found the previously trained and untrained
legs responded the same.

## 6. Strength vs lean mass

| effect or parameter | value / equation | range or uncertainty | population | grade | citation |
|---|---|---|---|---|---|
| Strength vs muscle cross-sectional area | Significant positive correlation between knee-extensor maximum voluntary force and mid-thigh extensor CSA in both sexes (p < 0.01). Force per unit CSA: **9.49 ± 1.34** (men) vs **8.92 ± 1.11** (women), not significantly different | Wide inter-individual spread: "the variation between subjects is such that strength is not a useful predictive index of muscle cross-sectional area" | 25 young men, 25 young women, CT imaging | COH | Maughan, Watson & Weir 1983, J Physiol, PMID 6875963, doi:10.1113/jphysiol.1983.sp014658 |
| Strength vs lean body mass | r = **0.50** (p < 0.01) in men; **no** significant correlation in women | — | as above | COH | Maughan et al. 1983 (as above) |
| Strength vs body weight | **No** significant correlation in either sex | — | as above | COH | Maughan et al. 1983 (as above) |
| Allometric scaling of strength to body size | Normalise as `S = F / mᵇ` with **b = 0.67 for muscle force** (dynamometer) and **b = 1 for muscle torque** (isokinetic) | recommended exponents, derived from geometric similarity and empirical review | humans, strength-testing methodology | TXT | Jaric 2002, Sports Med, PMID 12141882, doi:10.2165/00007256-200232100-00002 |
| Neural vs hypertrophic share of early strength gain | Neural factors "accounted for the larger proportion of the initial strength increment"; thereafter both contribute, with **hypertrophy becoming dominant after the first 3 to 5 weeks**. Cross-education to the untrained contralateral limb supports a neural locus | 7 men, 8 women, 8 wk — small n, 1979 methods | young adults, isotonic training | RCT | Moritani & deVries 1979, Am J Phys Med, PMID 453338 (no DOI in record) |
| Strength loss per unit muscle loss in disuse | 5 days immobilisation: CSA −3.5 %, strength −9.0 %; 14 days: CSA −8.4 %, strength −22.9 % → strength falls roughly **2.5–2.7× faster** than cross-sectional area | ratio computed from the two reported series | 24 healthy young men | RCT | Wall et al. 2014, Acta Physiol (Oxf), PMID 24168489, doi:10.1111/apha.12190 |

**For a game model.** Derive strength from lean mass, but with a per-character multiplier, because the measured
force-per-CSA spread is large and CSA does not predict strength well (Maughan). Scale absolute strength to
lean mass roughly linearly and scale *relative* performance (anything the character must move their own body
through — climbing, sprinting, vaulting) with the allometric exponent, i.e. strength-to-mass falls as mass
rises: Jaric's b = 0.67 for force is the citable basis. Early training gains should be mostly "skill" for the
first 3–5 weeks and only then mass-driven (Moritani & deVries) — a clean justification for a fast initial
strength ramp that does not yet change the character's body. In disuse or starvation, decay strength about
2.5× faster than lean mass (Wall 2014): a character who has been bed-ridden or starved loses functional
capacity well ahead of visible mass, and recovers it faster too (§ 5). Avoid modelling strength as a function
of total body weight; the measured correlation with body weight is zero (Maughan), so a heavier character is
not automatically stronger.

## 7. Hydration

| effect or parameter | value / equation | range or uncertainty | population | grade | citation |
|---|---|---|---|---|---|
| Daily total water requirement (IOM/NASEM adequate intake) | "A daily water intake of **3.7 L for adult men and 2.7 L for adult women** meets the needs of the vast majority of persons" (total water: drinking water + beverages + food) | An AI, not a requirement: it is the population median intake of apparently well-hydrated people, and the report itself notes wide individual variation | US/Canadian adults | AUTH | Sawka, Cheuvront & Carter 2005, Nutr Rev, PMID 16028570, doi:10.1111/j.1753-4887.2005.tb00152.x; primary report: *Dietary Reference Intakes for Water, Potassium, Sodium, Chloride, and Sulfate*, National Academies Press 2005, doi:10.17226/10925 (ISBN 0-309-09169-1) |
| EFSA adequate intake for total water | 2.5 L/d men, 2.0 L/d women — **unverified**: the EFSA Journal record (doi:10.2903/j.efsa.2010.1459) returned HTTP 403 on every route tried and no peer-reviewed record I fetched quoted the values | — | — | — | not verified; see Gaps |
| Whole-body sweating rate by sport | American football **1.51 ± 0.70 L/h**; endurance **1.28 ± 0.57**; basketball **0.95 ± 0.42**; soccer **0.94 ± 0.38**; baseball **0.83 ± 0.34 L/h**. Between-sport differences remained significant after ANCOVA | SDs as shown — the spread within a sport is roughly half the mean | 1303 athletes, observational testing 2000–2017, standardised absorbent-patch + body-mass method | COH | Barnes et al. 2019, J Sports Sci, PMID 31230518, doi:10.1080/02640414.2019.1633159 |
| What modulates sweat rate | Exercise intensity, environmental conditions, heat acclimation, aerobic capacity, body size and composition, wearing of protective equipment, sex, maturation, ageing, diet and hydration status | review of methodology and of intra/inter-individual variability | athletes | TXT | Baker 2017, Sports Med, PMID 28332116, doi:10.1007/s40279-017-0691-5 |
| Target during exercise | Prevent "excessive dehydration (>2 % body weight loss)" and electrolyte imbalance; because sweat rates vary individually, replacement programmes should be customised | position stand | exercising adults | AUTH | American College of Sports Medicine (Sawka et al.) 2007, Med Sci Sports Exerc, PMID 17277604, doi:10.1249/mss.0b013e31802ca597 |
| Endurance performance threshold | "A **≥2 % dehydration threshold** for impaired endurance exercise performance mediated by volume loss." In contrast, "no clear threshold or plausible mechanism(s) support the marginal, but potentially important, impairment in strength and power", and the cognitive effect "appears small and related primarily to distraction or discomfort" | The impact depends on the task's makeup (endurance vs strength vs cognitive vs motor) | comprehensive review of the dehydration and performance literature (a structured review, not a pooled meta-analysis) | TXT | Cheuvront & Kenefick 2014, Compr Physiol, PMID 24692140, doi:10.1002/cphy.c130017 |
| Counter-evidence in self-paced exercise | Dehydration of a mean **2.20 % body mass** during self-paced exercise produced a **non-significant +0.06 %** change in endurance performance. Drinking to thirst outperformed both under- and over-drinking. Conclusion: dehydration up to **4 %** body-mass loss does not impair cycling performance in outdoor conditions; intensity and duration matter more | 5 cycling studies, 39 subjects, 13 effect estimates; mean 26.0 °C, 61 % RH, 68 % V̇O₂max, 86 min trials | trained cyclists, time trials | MA | Goulet 2011, Br J Sports Med, PMID 21454440, doi:10.1136/bjsm.2010.077966 |
| Cognitive impairment threshold | Impairment "small but significant", with significant heterogeneity; **executive function, attention and motor coordination** significantly impaired; effect size scaled with body-mass loss, and impairment was greater for studies reporting **>2 %** body-mass loss than ≤2 % | 33 studies, 280 effect estimates, 413 subjects, 1–6 % body-mass loss | mixed adult | MA | Wittbrodt & Millard-Stafford 2018, Med Sci Sports Exerc, PMID 29933347, doi:10.1249/MSS.0000000000001682 |
| Mild dehydration, men | At **1.59 ± 0.42 %** body-mass loss without hyperthermia: visual-vigilance errors increased (p = 0.048), visual working-memory response latency slowed (p = 0.021); fatigue and tension/anxiety increased at rest (p = 0.040, 0.029) and fatigue during exercise (p = 0.026). Resting gastrointestinal temperature unchanged | n = 26 | 26 men, age 20.0 ± 0.3 y, three randomised single-blind trials, 3 × 40 min treadmill walks at 5.6 km/h, 5 % grade, 27.7 °C | RCT (crossover) | Ganio et al. 2011, Br J Nutr, PMID 21736786, doi:10.1017/S0007114511002005 |
| Mild dehydration, women | At **1.36 ± 0.16 %** body-mass loss: adverse effects at rest and during exercise on vigour-activity, fatigue-inertia and total mood disturbance, and on task difficulty, concentration and headache. "**Most aspects of cognitive performance were not affected**" | n = 25 | 25 women, age 23.0 ± 0.6 y, three 8 h placebo-controlled trials | RCT (crossover) | Armstrong et al. 2012, J Nutr, PMID 22190027, doi:10.3945/jn.111.142000 |
| Hydration, cognition and mood — review | Particular cognitive abilities and mood states are positively influenced by water consumption, most clearly in the elderly and children; the review flags inconsistent cognitive measures and insufficient objective hydration assessment as key limitations | narrative review | humans | TXT | Masento et al. 2014, Br J Nutr, PMID 24480458, doi:10.1017/S0007114513004455 |
| Hypohydration and heat tolerance | "The magnitude of increase in core temperature and HR and the decline in SV are **graded in proportion to the amount of dehydration** accrued during exercise." Core-temperature rise correlated with serum osmolality and sodium | 8 subjects; 4 fluid conditions (none, 20 %, 48 %, 81 % of sweat loss replaced) | 8 trained cyclists, 2 h moderate-intensity exercise in warm conditions | RCT (crossover) | Montain & Coyle 1992, J Appl Physiol, PMID 1447078, doi:10.1152/jappl.1992.73.4.1340 |
| Hyponatraemia from overdrinking | Exercise-associated hyponatraemia = serum [Na⁺] **<135 mmol·L⁻¹** during or within 24 h of sustained exercise; the proximate cause is overconsumption of hypotonic fluid (with non-osmotic vasopressin secretion contributing) | Reported incidence **7–15 %** in marathon runners for symptomatic plus asymptomatic cases | endurance athletes | AUTH (consensus) | Hew-Butler et al. 2015, Clin J Sport Med, PMID 26102445, doi:10.1097/JSM.0000000000000221; definition quoted from Armstrong et al. 2025, Open Access J Sports Med, PMID 41280657, doi:10.2147/OAJSM.S556848; incidence from Klingert et al. 2022, J Clin Med, PMID 36431252, doi:10.3390/jcm11226775; mechanism from Seal & Kavouras 2022, Auton Neurosci, PMID 35016044, doi:10.1016/j.autneu.2021.102930 |
| Time to death without water | **No verified quantitative source found.** See Gaps | — | — | — | — |

**For a game model.** Baseline water need is a well-behaved number: ~3.7 L/d for men and ~2.7 L/d for women
as *total* water including food, so a mod that counts only drinking should target roughly 2.0–2.5 L/d of fluid
and credit food moisture separately. Sweat is where the interesting variance lives — 0.8 to 1.5 L/h as a
*sport* mean, with individual SDs of ±0.4–0.7 L/h — so a rate of about **1 L/h for hard work, scaling up with
heat and load and down when idle**, is well supported, and the sweat rate should modulate with temperature and
exertion rather than being fixed. On performance, the literature is genuinely split and the mod should not
pretend otherwise: the ≥2 % threshold is the review consensus for endurance (Cheuvront & Kenefick) but a
cycling meta-analysis found no impairment up to 4 % in self-paced outdoor exercise (Goulet). The defensible
compromise is a **gentle** endurance penalty starting near 2 % body-mass loss and steepening past 4 %, not a
cliff at 2 %. The cognitive and mood effects are the better-supported game mechanic, and they start *earlier*:
at only 1.4–1.6 % body-mass loss, measured effects were on **mood, fatigue, perceived task difficulty,
headache, concentration, vigilance and working memory** — not on strength. So thirst should first make the
character feel and behave worse (a moodle, attention and accuracy penalties) and only later slow them down;
strength and power penalties from dehydration alone are explicitly **unsupported** (Cheuvront & Kenefick).
Heat interacts multiplicatively and is graded, not thresholded (Montain & Coyle): each increment of dehydration
raises core temperature and heart rate, so dehydration should be an input to a heat-strain model rather than a
separate silo. Finally, overdrinking deserves a real penalty: hyponatraemia below 135 mmol/L Na⁺ from drinking
too much hypotonic fluid is a genuine and occasionally fatal condition at 7–15 % incidence in marathoners, so
chugging water should not be a free action.

## 8. Starvation timeline

| effect or parameter | value / equation | range or uncertainty | population | grade | citation |
|---|---|---|---|---|---|
| Weight-loss rate in total fasting | "Early in fasting weight loss is rapid, averaging **0.9 kg per day during the first week** and slowing to **0.3 kg per day by the third week**; early rapid weight loss is primarily due to **negative sodium balance**" | Most fasting studies used obese subjects, so "results may not always apply to lean persons" | fasting humans, mostly obese | TXT | Kerndt et al. 1982, West J Med, PMID 6758355 (no DOI in record) |
| Fuel sequence, days 1–3 and onward | Early fasting: "a high rate of **gluconeogenesis with amino acids as the primary substrates**". As fasting continues, "progressive **ketosis** develops due to the mobilization and oxidation of fatty acids. As ketone levels rise they replace glucose as the primary energy source in the central nervous system, thereby decreasing the need for gluconeogenesis and **sparing protein catabolism**" | qualitative sequence, well established | as above | TXT | Kerndt et al. 1982 (as above) |
| Hormonal signature of fasting | Insulin and T₃ fall; glucagon and reverse T₃ rise | — | as above | TXT | Kerndt et al. 1982 (as above) |
| Direct measurement of the brain's switch to ketones | Catheterisation of cerebral vessels during 5–6 weeks of starvation showed **β-hydroxybutyrate and acetoacetate replaced glucose as the predominant fuel for brain metabolism** | n = 3 — the foundational measurement, very small | 3 obese patients, 5–6 wk starvation | RCT-adjacent (inpatient measurement) | Owen et al. 1967, J Clin Invest, PMID 6061736, doi:10.1172/JCI105650 |
| Why protein sparing permits long survival | D-β-hydroxybutyrate's use by brain "not only has permitted man to survive prolonged starvation", but is more efficient than glucose at providing cellular energy in ischaemic states | narrative/biographical review | humans | TXT | Cahill 2006, Annu Rev Nutr, PMID 16848698, doi:10.1146/annurev.nutr.26.061505.111258; also Cahill 1970, N Engl J Med, PMID 4915800, doi:10.1056/NEJM197003192821209 and Cahill 1998, Am J Clin Nutr, PMID 9665088, doi:10.1093/ajcn/68.1.1 (both verified records without abstracts) |
| Glycogen store size in grams | **Not verified.** No source I fetched gave total liver or muscle glycogen in grams. The one verified quantitative datum is a muscle *concentration*: vastus lateralis 410 ± 15 mmol glucose·kg dry muscle⁻¹ before cold exposure, falling to 332 ± 18 after 90 min shivering | — | 14 adults | RCT | Martineau & Jacobs 1988, J Appl Physiol, PMID 3209549, doi:10.1152/jappl.1988.65.5.2046 |
| The 30–70 day survival range | **Not verified.** The commonly cited hunger-strike range could not be pinned to a fetched primary source: the Peel 1997 BMJ editorial's record is verified but its full text was inaccessible (403/500 on every route), and the Lieberson 2004 *Scientific American* piece is not indexed with a DOI or PMID. Do not cite a specific day count as evidenced | — | — | — | Peel 1997, BMJ, PMID 9353494, doi:10.1136/bmj.315.7112.829 — **record verified, content not read** |
| BMI at which death occurs | A BMI of **<10 kg/m²** can be compatible with life given specialised care. Famine oedema occurred equally in men and women, but men had more severe oedema and a poorer prognosis at any given severity. "Survival from these extremes of emaciation has never before been recorded, and many of the BMI values documented here are below the level of **12**, previously thought to mark the limit of human adaptation to starvation" | 573 inpatients; contributing factors named as high ambient temperature, tall Somali phenotype, gradual reduction in intake, and prior chronic energy deficiency | 573 adult inpatients, 1992–93 Somali famine, Baidoa therapeutic feeding centre | COH | Collins 1995, Nat Med, PMID 7585185, doi:10.1038/nm0895-810; the earlier BMI-limit framing is Henry 1990, Eur J Clin Nutr, PMID 2364921 (record verified, no abstract or DOI in the record) |
| Semi-starvation: magnitude and symptoms | Participants "were subjected to semistarvation in which **most lost >25 % of their weight**, and many experienced **anaemia, fatigue, apathy, extreme weakness, irritability, neurological deficits, and lower extremity oedema**" | 36 volunteers (32 completed the metabolic series re-analysed by Dulloo & Jacquet) | 36 conscientious objectors, Minnesota Starvation Experiment, University of Minnesota, WWII | COH (controlled experiment, reported historically) | Kalm & Semba 2005, J Nutr, PMID 15930436, doi:10.1093/jn/135.6.1347. The primary is Keys A et al., *The Biology of Human Starvation*, University of Minnesota Press, 1950 — a book with **no DOI or PMID**; its content here is taken from Kalm & Semba's verified account, not read directly |
| Refeeding syndrome — definition | "The potentially fatal shifts in fluids and electrolytes that may occur in malnourished patients receiving artificial refeeding (whether enterally or parenterally)" | — | malnourished patients | AUTH (clinical review citing NICE) | Mehanna, Moledina & Travis 2008, BMJ, PMID 18583681, doi:10.1136/bmj.a301 |
| Refeeding syndrome — who is at high risk (NICE criteria) | **One or more** of: BMI <16; unintentional weight loss >15 % in 3–6 months; little or no intake >10 days; low potassium, phosphate or magnesium before feeding. **Or two or more** of: BMI <18.5; weight loss >10 % in 3–6 months; little or no intake >5 days; history of alcohol or drug misuse | — | as above | AUTH | Mehanna et al. 2008 (as above) |
| Refeeding syndrome — safe restart rate | Start at a maximum of **0.042 MJ·kg⁻¹·24 h⁻¹** (≈10 kcal·kg⁻¹·d⁻¹); for the severely malnourished (BMI ≤14, or negligible intake ≥2 weeks) a maximum of **0.021 MJ·kg⁻¹·24 h⁻¹** (≈5 kcal·kg⁻¹·d⁻¹). Increase gradually over **4–7 days** to full requirements, with cardiac monitoring for the most severe | — | as above | AUTH | Mehanna et al. 2008 (as above) |
| Refeeding syndrome — how common | Pooled incidence **23 % (95 % CI 15–33)** across 28 studies of critically ill patients, with no association with mortality; a second review reported **35 % (95 % CI 27–44)** across 49 studies of 24 778 critically ill patients | The two pooled estimates disagree substantially; both report substantial heterogeneity | critically ill adults (not otherwise-healthy starved adults) | MA | Schneider et al. 2026, Sci Rep, PMID 41735500, doi:10.1038/s41598-026-41063-8; Xie et al. 2026, Clin Nutr, PMID 42624024, doi:10.1016/j.clnu.2026.106734 |

**For a game model.** The timeline has three phases and each has a distinct, citable behaviour. **Days 1–3**:
weight falls fast (≈0.9 kg/d in week one) but most of that is water and sodium, not tissue — so a game that
converts early weight loss into lost strength is wrong, and the honest model separates a fast-moving water
compartment from slow-moving fat and lean compartments. Gluconeogenesis from amino acids dominates, so this is
the window in which lean mass is genuinely being burned fastest. **Days ~3 onward**: ketosis rises, the brain
switches to β-hydroxybutyrate (directly measured, Owen 1967), and protein catabolism is spared — weight loss
slows to ≈0.3 kg/d by week three. That gives a natural and dramatically useful shape: a nasty first few days,
then a grim plateau. **Weeks to months**: survival is limited by fat reserves, and the endpoint is a
body-composition threshold rather than a clock. BMI 12 was long taken as the limit and BMI <10 has been
survived with care (Collins 1995), so a fat/lean floor is a better death condition than "N days without food".
For the semi-starvation state, the measured symptom set — apathy, irritability, extreme weakness, fatigue,
oedema, anaemia, neurological deficits — is exactly a list of moodles and stat penalties, and it is the
best-evidenced part of § 8. Refeeding is worth a mechanic and the numbers are precise: a character who is
severely starved and then eats freely should suffer, and the clinical safe rate is only **5–10 kcal·kg⁻¹·d⁻¹
for the first 4–7 days** — which is about 350–700 kcal/d for a 70 kg character, far below maintenance. Two
things to avoid: do not state a day count for death by starvation as if it were evidenced (the 30–70 day range
could not be verified here), and do not model glycogen in grams from this document, because no verified figure
for total store size was found.

## 9. Obesity and excess

| effect or parameter | value / equation | range or uncertainty | population | grade | citation |
|---|---|---|---|---|---|
| All-cause mortality vs BMI | Mortality minimal at BMI 20.0–25.0. HR (ref 22.5–<25.0): BMI 15.0–<18.5 **1.51** (1.43–1.59); 18.5–<20.0 **1.13** (1.09–1.17); 25.0–<27.5 **1.07** (1.07–1.08); 27.5–<30.0 **1.20** (1.18–1.22); 30.0–<35.0 **1.45** (1.41–1.48); 35.0–<40.0 **1.94** (1.87–2.01); 40.0–<60.0 **2.76** (2.60–2.92) | 95 % CIs as shown; HR per +5 kg/m² above 25: 1.29–1.39 by continent; larger in the young (1.52 at 35–49 y) and in men (1.51 vs 1.30) | 3 951 455 never-smokers without chronic disease at recruitment, surviving ≥5 y, from 239 prospective studies on four continents; 385 879 deaths; median follow-up 13.7 y | MA (individual-participant-data) | Global BMI Mortality Collaboration 2016, Lancet, PMID 27423262, doi:10.1016/S0140-6736(16)30175-1 |
| Body fat and thermoregulation | Subcutaneous fat is genuine insulation — obese individuals cool more slowly than lean ones in cool water — but it also **reduces heat dissipation capacity**. "Obesity may have a significant impact on thermoregulatory physiology, but the converse is much less likely" | narrative review | humans and animals | TXT | Speakman 2018, Handb Clin Neurol, PMID 30454605, doi:10.1016/B978-0-444-63912-7.00026-6 |
| Walking economy per kg | Net metabolic rate per kg was "**0–6 % less** in obese compared with nonobese adults" across 11 speed/grade combinations (0.50–1.75 m/s, −3° to +9°). External mechanical work was not affected by obesity. Conclusion: "obesity does not impair walking economy" | contradicts earlier reports; n = 51 | 32 obese (102.1 ± 15.6 kg, BMI 33.9 ± 3.6) and 19 nonobese (64.4 ± 10.6 kg, BMI 21.6 ± 2.0) adults, dual-belt force treadmill | COH (controlled measurement) | Browning et al. 2013, J Appl Physiol, PMID 23412900, doi:10.1152/japplphysiol.00765.2012 |
| Absolute cost of moving a fat body (**derived**) | Because per-kg economy is not impaired (Browning) but net cost per km is ~0.86 kcal·kg⁻¹·km⁻¹ (§ 2), extra fat mass costs energy **in proportion to the mass carried** while adding no power output; and because relative strength scales as roughly m⁰·⁶⁷ (§ 6), the penalty lands on body-relative tasks (climbing, sprinting, vaulting) rather than on walking efficiency | inference from three verified results, not a measured effect | — | derived | Browning et al. 2013; Herrmann et al. 2024; Jaric 2002 |
| Musculoskeletal injury risk | Severely obese individuals had **2.56× greater odds** of work-related musculoskeletal injury; 80.8 % of the cohort was overweight or obese | single occupational cohort; self-reported injury history | probation officers (occupational cohort) | COH | Mota et al. 2019, Med Sci Sports Exerc, PMID 30925576, doi:10.1249/MSS.0000000000001996 |

**For a game model.** The mortality curve is the one very large, very clean result here and it is U-shaped in
both directions — being underweight (BMI 15–18.5, HR 1.51) is about as dangerous as grade-1 obesity (HR 1.45),
and grade-3 obesity roughly triples mortality. That justifies a two-sided health penalty rather than a
fat-is-only-bad rule, which matters for a game where players will starve characters deliberately. The
thermoregulation result gives a genuinely two-sided mechanic: a fat character should resist cold better and
overheat faster in exertion or heat. The endurance penalty should come from carried mass, not from inefficiency:
Browning's measurement is that obese adults are *not* less economical per kg, so model fat as dead weight —
every kg of fat costs its share of the ~0.86 kcal·kg⁻¹·km⁻¹ running cost and contributes no power, which
automatically produces a worse power-to-weight ratio without any special-casing. Injury risk has one usable
occupational anchor (2.56× odds of musculoskeletal injury in the severely obese), enough to justify a modest
sprain/strain multiplier but not a large one. Note carefully what these numbers are **not**: a 13-year
all-cause mortality hazard ratio in never-smokers is not a within-days survival modifier, and converting
HR 2.76 into a per-day death chance in a zombie apocalypse has no support in this literature. Use adiposity to
modulate cold tolerance, heat tolerance, carried-mass cost and the relative-strength penalty from §§ 2 and 6,
and use the mortality curve only as a justification for the *shape* of a long-run health penalty at both
extremes.

## Gaps

What I looked for and could not verify. Each of these is a place where the mod must either use an unevidenced
number knowingly, or commission its own reading.

1. **Revised Harris–Benedict coefficients (Roza & Shizgal 1984).** The paper's record and its ±14 % precision
   claim are verified; the coefficient set that circulates everywhere
   (`88.362 + 13.397W + 4.799H − 5.677A` for men) is not in the abstract and the AJCN/ScienceDirect full texts
   returned HTTP 403. Since Frankenfield 2005 puts Mifflin–St Jeor first anyway, this is a gap the mod can
   simply route around.
2. **Cunningham 1980 coefficients** (`RMR = 500 + 22·LBM`) — same problem, same workaround (use Cunningham
   1991's verified `370 + 21.6·FFM`).
3. **Pandolf 1977 equation coefficients and Soule & Goldman 1972 terrain factors.** Both citations are verified;
   neither primary carries an abstract in the indexing records, and I found no open-access paper that
   reproduces the full equation with coefficients (the PLOS ONE real-world walking paper and the *Experimental
   Physiology* load-carriage editorial both only cite it). The coefficient and η values in § 2 are from
   secondary reproductions and are marked unverified. Related and also unverified: the widely reported finding
   that the Pandolf equation **under-predicts** contemporary heavy military load carriage (the paper exists on
   ScienceDirect but was not fetchable).
4. **Morton 2018's 95 % CI on the 1.62 g/kg/d breakpoint** (usually quoted as 1.03–2.20). The point estimate is
   verified from the abstract; the interval is not.
5. **Wernbom 2007's numerical hypertrophy-rate table.** The review is the right source for "% CSA gain per
   week" but its dose–response numbers live in the paywalled full text. § 4 substitutes verified per-trial
   rates (Psilander: +17 % CSA in 10 wk; Longland: +1.2 kg lean in 4 wk).
6. **EFSA 2010 adequate intakes for total water** (usually 2.5 L/d men, 2.0 L/d women). Every route to the
   EFSA Journal record returned HTTP 403, and none of the peer-reviewed papers I fetched quoted the numbers.
   The IOM/NASEM values (3.7 / 2.7 L/d) *are* verified, via Sawka et al. 2005 and the NAP catalogue record.
7. **Time to death without water.** No verified quantitative source found at all. The commonly repeated
   "3 days" is folklore as far as this run could establish.
8. **The 30–70 day starvation survival range.** Peel 1997's BMJ record is verified but its full text was
   unreachable (403 on bmj.com, 500 on the Europe PMC full-text API, and the PMC HTML/PDF returned only
   wrappers). Lieberson 2004 in *Scientific American* has no DOI or PMID and is therefore unusable as
   evidence. Henry 1990's "limits of human survival" abstract is not in the indexing records either. Collins
   1995 (BMI <10 survivable with care; BMI 12 previously thought the limit) is the strongest verified
   substitute, and it is a *composition* threshold, not a duration.
9. **Total liver and muscle glycogen in grams.** Repeated searches returned only concentrations
   (mmol·kg dry muscle⁻¹) or unrelated glycogen-storage-disease papers. The "~100 g liver + ~400 g muscle"
   figure could not be verified.
10. **Keys 1950, *The Biology of Human Starvation*.** A book with no DOI or PMID; not directly read. All
    Minnesota content here is via Kalm & Semba 2005 (verified) and Dulloo & Jacquet 1998 (verified re-analysis).
11. **Fat-mass energy density and lean-mass energy density as explicit coefficients** (the ~9440 kcal/kg and
    ~1800 kcal/kg used inside Hall's models). Hall 2008's abstract gives only the 32.2 MJ/kg rule-of-thumb;
    the per-compartment densities are in the paywalled model appendices. § 3 therefore reasons in terms of the
    *rule* and the *partition*, not in terms of two verified densities.
12. **Body fat and sprint/endurance running performance.** The only quantitative sources found were two
    unreviewed preprints (Research Square and Preprints.org) on sex differences in body fat and running, which
    I have not used. § 9 substitutes a derivation from Browning 2013 plus the § 2 energy cost and § 6 allometry.
13. **Obesity and heat tolerance as a quantified effect size.** Speakman 2018 establishes the direction
    (insulation up, dissipation down) but not a magnitude; the one quantitative paper found (an obese-men
    precooling trial reporting ~160–194 mL greater fluid loss) is too thin and too indirect to use.
14. **Hew-Butler 2015's own numeric thresholds.** The consensus statement's record is verified but its abstract
    is not in the indexing records, so the <135 mmol/L definition and the 7–15 % incidence in § 7 are cited to
    other verified papers that state them.
15. **Protein–energy malnutrition consequences (immune function, wound healing) as effect sizes.** Searches
    returned mostly rodent, paediatric, elderly or dialysis populations — directionally consistent (reduced
    lymphocyte proliferation, impaired cell-mediated immunity) but with no effect size transferable to a
    healthy adult under acute food scarcity. Not stated as a table row for that reason.

## Bibliography

Every entry below was verified by fetching its Europe PMC, PubMed, National Academies or publisher record and
confirming title, authors, journal and year. Entries marked *(record only)* are papers whose bibliographic
record was verified but whose abstract or full text was not readable in this run — their content is not used as
evidence except where explicitly attributed to a second, readable source.

- Ainsworth BE, Haskell WL, Herrmann SD, Meckes N, Bassett DR, Tudor-Locke C, Greer JL, Vezina J, Whitt-Glover MC, Leon AS. 2011 Compendium of Physical Activities: a second update of codes and MET values. *Med Sci Sports Exerc* 2011. PMID 21681120, doi:10.1249/MSS.0b013e31821ece12
- Alpert SS. The energy density of weight loss in semistarvation. *Int J Obes* 1988. PMID 3235270 *(record only; no DOI in record)*
- Alpert SS. A limit on the energy transfer rate from the human fat store in hypophagia. *J Theor Biol* 2005. PMID 15615615, doi:10.1016/j.jtbi.2004.08.029
- American College of Sports Medicine; Sawka MN, Burke LM, Eichner ER, Maughan RJ, Montain SJ, Stachenfeld NS. Position stand: exercise and fluid replacement. *Med Sci Sports Exerc* 2007. PMID 17277604, doi:10.1249/mss.0b013e31802ca597
- Armstrong LE, Ganio MS, Casa DJ, Lee EC, McDermott BP, Klau JF, Jimenez L, Le Bellego L, Chevillotte E, Lieberman HR. Mild dehydration affects mood in healthy young women. *J Nutr* 2012. PMID 22190027, doi:10.3945/jn.111.142000
- Armstrong LE, McDermott BP, Young SL, Casa DJ. Exercise-associated hyponatremia: serum sodium, symptomatology, severity, and sport specificity. *Open Access J Sports Med* 2025. PMID 41280657, doi:10.2147/OAJSM.S556848
- Baker LB. Sweating rate and sweat sodium concentration in athletes: a review of methodology and intra/interindividual variability. *Sports Med* 2017. PMID 28332116, doi:10.1007/s40279-017-0691-5
- Barnes KA, Anderson ML, Stofan JR, Dalrymple KJ, Reimel AJ, Roberts TJ, Randell RK, Ungaro CT, Baker LB. Normative data for sweating rate, sweat sodium concentration, and sweat sodium loss in athletes: an update and analysis by sport. *J Sports Sci* 2019. PMID 31230518, doi:10.1080/02640414.2019.1633159
- Bilsborough S, Mann N. A review of issues of dietary protein intake in humans. *Int J Sport Nutr Exerc Metab* 2006. PMID 16779921, doi:10.1123/ijsnem.16.2.129
- Blocquiaux S, Gorski T, Van Roie E, Ramaekers M, Van Thienen R, Nielens H, Delecluse C, De Bock K, Thomis M. The effect of resistance training, detraining and retraining on muscle strength and power, myofibre size, satellite cells and myonuclei in older men. *Exp Gerontol* 2020. PMID 32017951, doi:10.1016/j.exger.2020.110860 (corrigendum PMID 32147251, doi:10.1016/j.exger.2020.110897)
- Bouchard C, Tremblay A, Després JP, Nadeau A, Lupien PJ, Thériault G, Dussault J, Moorjani S, Pinault S, Fournier G. The response to long-term overfeeding in identical twins. *N Engl J Med* 1990. PMID 2336074, doi:10.1056/NEJM199005243222101
- Browning RC, Reynolds MM, Board WJ, Walters KA, Reiser RF. Obesity does not impair walking economy across a range of speeds and grades. *J Appl Physiol* 2013. PMID 23412900, doi:10.1152/japplphysiol.00765.2012
- Bruusgaard JC, Gundersen K. In vivo time-lapse microscopy reveals no loss of murine myonuclei during weeks of muscle atrophy. *J Clin Invest* 2008. PMID 18317591, doi:10.1172/JCI34022
- Bruusgaard JC, Johansen IB, Egner IM, Rana ZA, Gundersen K. Myonuclei acquired by overload exercise precede hypertrophy and are not lost on detraining. *Proc Natl Acad Sci USA* 2010. PMID 20713720, doi:10.1073/pnas.0913935107
- Cahill GF Jr. Starvation in man. *N Engl J Med* 1970. PMID 4915800, doi:10.1056/NEJM197003192821209 *(record only)*
- Cahill GF Jr. Survival in starvation. *Am J Clin Nutr* 1998. PMID 9665088, doi:10.1093/ajcn/68.1.1 *(record only; editorial)*
- Cahill GF Jr. Fuel metabolism in starvation. *Annu Rev Nutr* 2006. PMID 16848698, doi:10.1146/annurev.nutr.26.061505.111258
- Cheuvront SN, Kenefick RW. Dehydration: physiology, assessment, and performance effects. *Compr Physiol* 2014. PMID 24692140, doi:10.1002/cphy.c130017
- Collins S. The limit of human adaptation to starvation. *Nat Med* 1995. PMID 7585185, doi:10.1038/nm0895-810
- Cunningham JJ. A reanalysis of the factors influencing basal metabolic rate in normal adults. *Am J Clin Nutr* 1980. PMID 7435418, doi:10.1093/ajcn/33.11.2372 *(record only)*
- Cunningham JJ. Body composition as a determinant of energy expenditure: a synthetic review and a proposed general prediction equation. *Am J Clin Nutr* 1991. PMID 1957828, doi:10.1093/ajcn/54.6.963
- Dulloo AG, Jacquet J. Adaptive reduction in basal metabolic rate in response to food deprivation in humans: a role for feedback signals from fat stores. *Am J Clin Nutr* 1998. PMID 9734736, doi:10.1093/ajcn/68.3.599
- Eftestøl E, Psilander N, Cumming KT, Juvkam I, Ekblom M, Sunding K, Wernbom M, Holmberg HC, Ekblom B, Bruusgaard JC, Raastad T, Gundersen K. Muscle memory: are myonuclei ever lost? *J Appl Physiol* 2020. PMID 31854249, doi:10.1152/japplphysiol.00761.2019
- Egner IM, Bruusgaard JC, Eftestøl E, Gundersen K. A cellular memory mechanism aids overload hypertrophy in muscle long after an episodic exposure to anabolic steroids. *J Physiol* 2013. PMID 24167222, doi:10.1113/jphysiol.2013.264457
- Eyolfson DA, Tikuisis P, Xu X, Weseen G, Giesbrecht GG. Measurement and prediction of peak shivering intensity in humans. *Eur J Appl Physiol* 2001. PMID 11394237, doi:10.1007/s004210000329
- Forbes GB. Body fat content influences the body composition response to nutrition and exercise. *Ann N Y Acad Sci* 2000. PMID 10865771, doi:10.1111/j.1749-6632.2000.tb06482.x
- Frankenfield D, Roth-Yousey L, Compher C. Comparison of predictive equations for resting metabolic rate in healthy nonobese and obese adults: a systematic review. *J Am Diet Assoc* 2005. PMID 15883556, doi:10.1016/j.jada.2005.02.005
- Gallagher D, Belmonte D, Deurenberg P, Wang Z, Krasnow N, Pi-Sunyer FX, Heymsfield SB. Organ-tissue mass measurement allows modeling of REE and metabolically active tissue mass. *Am J Physiol* 1998. PMID 9688626, doi:10.1152/ajpendo.1998.275.2.E249
- Ganio MS, Armstrong LE, Casa DJ, McDermott BP, Lee EC, Yamamoto LM, Marzano S, Lopez RM, Jimenez L, Le Bellego L, Chevillotte E, Lieberman HR. Mild dehydration impairs cognitive performance and mood of men. *Br J Nutr* 2011. PMID 21736786, doi:10.1017/S0007114511002005
- Global BMI Mortality Collaboration; Di Angelantonio E, Bhupathiraju SN, Wormser D, Gao P, Kaptoge S, et al. Body-mass index and all-cause mortality: individual-participant-data meta-analysis of 239 prospective studies in four continents. *Lancet* 2016. PMID 27423262, doi:10.1016/S0140-6736(16)30175-1
- Goulet ED. Effect of exercise-induced dehydration on time-trial exercise performance: a meta-analysis. *Br J Sports Med* 2011. PMID 21454440, doi:10.1136/bjsm.2010.077966
- Gundersen K, Bruusgaard JC, Egner IM, Eftestøl E, Bengtsen M. Muscle memory: virtues of your youth? *J Physiol* 2018. PMID 30145845, doi:10.1113/JP276354
- Hall C, Figueroa A, Fernhall B, Kanaley JA. Energy expenditure of walking and running: comparison with prediction equations. *Med Sci Sports Exerc* 2004. PMID 15570150, doi:10.1249/01.MSS.0000147584.87788.0E
- Hall KD. Computational model of in vivo human energy metabolism during semistarvation and refeeding. *Am J Physiol Endocrinol Metab* 2006. PMID 16449298, doi:10.1152/ajpendo.00523.2005
- Hall KD. Body fat and fat-free mass inter-relationships: Forbes's theory revisited. *Br J Nutr* 2007. PMID 17367567, doi:10.1017/S0007114507691946
- Hall KD. What is the required energy deficit per unit weight loss? *Int J Obes (Lond)* 2008. PMID 17848938, doi:10.1038/sj.ijo.0803720
- Haman F. Shivering in the cold: from mechanisms of fuel selection to survival. *J Appl Physiol* 2006. PMID 16614367, doi:10.1152/japplphysiol.01088.2005
- Haman F, Blondin DP. Shivering thermogenesis in humans: origin, contribution and metabolic requirement. *Temperature (Austin)* 2017. PMID 28944268, doi:10.1080/23328940.2017.1328999
- Hector AJ, Phillips SM. Protein recommendations for weight loss in elite athletes: a focus on body composition and performance. *Int J Sport Nutr Exerc Metab* 2018. PMID 29182451, doi:10.1123/ijsnem.2017-0273
- Henry CJ. Body mass index and the limits of human survival. *Eur J Clin Nutr* 1990. PMID 2364921 *(record only; no DOI in record)*
- Herrmann SD, Willis EA, Ainsworth BE, Barreira TV, Hastert M, Kracht CL, Schuna JM, Cai Z, Quan M, Tudor-Locke C, Whitt-Glover MC, Jacobs DR. 2024 Adult Compendium of Physical Activities: a third update of the energy costs of human activities. *J Sport Health Sci* 2024. PMID 38242596, doi:10.1016/j.jshs.2023.10.010
- Hew-Butler T, Rosner MH, Fowkes-Godek S, Dugas JP, Hoffman MD, Lewis DP, Maughan RJ, Miller KC, Montain SJ, Rehrer NJ, Roberts WO, Rogers IR, Siegel AJ, Stuempfle KJ, Winger JM, Verbalis JG. Statement of the Third International Exercise-Associated Hyponatremia Consensus Development Conference, Carlsbad, California, 2015. *Clin J Sport Med* 2015. PMID 26102445, doi:10.1097/JSM.0000000000000221 *(record only)*
- Institute of Medicine. *Dietary Reference Intakes for Water, Potassium, Sodium, Chloride, and Sulfate*. National Academies Press, 2005. doi:10.17226/10925 (ISBN 0-309-09169-1)
- Jaric S. Muscle strength testing: use of normalisation for body size. *Sports Med* 2002. PMID 12141882, doi:10.2165/00007256-200232100-00002
- Kalm LM, Semba RD. They starved so that others be better fed: remembering Ancel Keys and the Minnesota experiment. *J Nutr* 2005. PMID 15930436, doi:10.1093/jn/135.6.1347
- Kerndt PR, Naughton JL, Driscoll CE, Loxterkamp DA. Fasting: the history, pathophysiology and complications. *West J Med* 1982. PMID 6758355 *(no DOI in record)*
- Klingert M, Nikolaidis PT, Weiss K, Thuany M, Chlíbková D, Knechtle B. Exercise-associated hyponatremia in marathon runners. *J Clin Med* 2022. PMID 36431252, doi:10.3390/jcm11226775
- Longland TM, Oikawa SY, Mitchell CJ, Devries MC, Phillips SM. Higher compared with lower dietary protein during an energy deficit combined with intense exercise promotes greater lean mass gain and fat mass loss: a randomized trial. *Am J Clin Nutr* 2016. PMID 26817506, doi:10.3945/ajcn.115.119339
- Martineau L, Jacobs I. Muscle glycogen utilization during shivering thermogenesis in humans. *J Appl Physiol* 1988. PMID 3209549, doi:10.1152/jappl.1988.65.5.2046
- Masento NA, Golightly M, Field DT, Butler LT, van Reekum CM. Effects of hydration status on cognitive performance and mood. *Br J Nutr* 2014. PMID 24480458, doi:10.1017/S0007114513004455
- Maughan RJ, Watson JS, Weir J. Strength and cross-sectional area of human skeletal muscle. *J Physiol* 1983. PMID 6875963, doi:10.1113/jphysiol.1983.sp014658
- Mehanna HM, Moledina J, Travis J. Refeeding syndrome: what it is, and how to prevent and treat it. *BMJ* 2008. PMID 18583681, doi:10.1136/bmj.a301
- Mifflin MD, St Jeor ST, Hill LA, Scott BJ, Daugherty SA, Koh YO. A new predictive equation for resting energy expenditure in healthy individuals. *Am J Clin Nutr* 1990. PMID 2305711, doi:10.1093/ajcn/51.2.241
- Montain SJ, Coyle EF. Influence of graded dehydration on hyperthermia and cardiovascular drift during exercise. *J Appl Physiol* 1992. PMID 1447078, doi:10.1152/jappl.1992.73.4.1340
- Moore DR, Churchward-Venne TA, Witard O, Breen L, Burd NA, Tipton KD, Phillips SM. Protein ingestion to stimulate myofibrillar protein synthesis requires greater relative protein intakes in healthy older versus younger men. *J Gerontol A Biol Sci Med Sci* 2015. PMID 25056502, doi:10.1093/gerona/glu103
- Moritani T, deVries HA. Neural factors versus hypertrophy in the time course of muscle strength gain. *Am J Phys Med* 1979. PMID 453338 *(no DOI in record)*
- Morton RW, Murphy KT, McKellar SR, Schoenfeld BJ, Henselmans M, Helms E, Aragon AA, Devries MC, Banfield L, Krieger JW, Phillips SM. A systematic review, meta-analysis and meta-regression of the effect of protein supplementation on resistance training-induced gains in muscle mass and strength in healthy adults. *Br J Sports Med* 2018. PMID 28698222, doi:10.1136/bjsports-2017-097608
- Mota JA, Kerr ZY, Gerstner GR, Giuliani HK, Ryan ED. Obesity prevalence and musculoskeletal injury history in probation officers. *Med Sci Sports Exerc* 2019. PMID 30925576, doi:10.1249/MSS.0000000000001996
- Nunes CL, Casanova N, Francisco R, Bosy-Westphal A, Hopkins M, Sardinha LB, Silva AM. Does adaptive thermogenesis occur after weight loss in adults? A systematic review. *Br J Nutr* 2022. PMID 33762040, doi:10.1017/S0007114521001094
- Owen OE, Morgan AP, Kemp HG, Sullivan JM, Herrera MG, Cahill GF Jr. Brain metabolism during fasting. *J Clin Invest* 1967. PMID 6061736, doi:10.1172/JCI105650
- Pandolf KB, Givoni B, Goldman RF. Predicting energy expenditure with loads while standing or walking very slowly. *J Appl Physiol Respir Environ Exerc Physiol* 1977. PMID 908672, doi:10.1152/jappl.1977.43.4.577 *(record only)*
- Peel M. Hunger strikes. *BMJ* 1997;315(7112):829–30. PMID 9353494, doi:10.1136/bmj.315.7112.829 *(record only)*
- Psilander N, Eftestøl E, Cumming KT, Juvkam I, Ekblom MM, Sunding K, Wernbom M, Holmberg HC, Ekblom B, Bruusgaard JC, Raastad T, Gundersen K. Effects of training, detraining, and retraining on strength, hypertrophy, and myonuclear number in human skeletal muscle. *J Appl Physiol* 2019. PMID 30991013, doi:10.1152/japplphysiol.00917.2018
- Rosenbaum M, Hirsch J, Gallagher DA, Leibel RL. Long-term persistence of adaptive thermogenesis in subjects who have maintained a reduced body weight. *Am J Clin Nutr* 2008. PMID 18842775, doi:10.1093/ajcn/88.4.906
- Rosenbaum M, Leibel RL. Adaptive thermogenesis in humans. *Int J Obes (Lond)* 2010. PMID 20935667, doi:10.1038/ijo.2010.184
- Roza AM, Shizgal HM. The Harris Benedict equation reevaluated: resting energy requirements and the body cell mass. *Am J Clin Nutr* 1984. PMID 6741850, doi:10.1093/ajcn/40.1.168
- Sawka MN, Cheuvront SN, Carter R. Human water needs. *Nutr Rev* 2005. PMID 16028570, doi:10.1111/j.1753-4887.2005.tb00152.x
- Schneider L, Nedel WL, Perez AV, et al. Incidence and mortality of refeeding syndrome in critically ill patients: a systematic review and meta-analysis. *Sci Rep* 2026. PMID 41735500, doi:10.1038/s41598-026-41063-8
- Seal AD, Kavouras SA. A review of risk factors and prevention strategies for exercise-associated hyponatremia. *Auton Neurosci* 2022. PMID 35016044, doi:10.1016/j.autneu.2021.102930
- Snijders T, Aussieker T, Holwerda A, Parise G, van Loon LJC, Verdijk LB. The concept of skeletal muscle memory: evidence from animal and human studies. *Acta Physiol (Oxf)* 2020. PMID 32175681, doi:10.1111/apha.13465
- Soule RG, Goldman RF. Terrain coefficients for energy cost prediction. *J Appl Physiol* 1972. PMID 5038861, doi:10.1152/jappl.1972.32.5.706 *(record only)*
- Speakman JR. Obesity and thermoregulation. *Handb Clin Neurol* 2018. PMID 30454605, doi:10.1016/B978-0-444-63912-7.00026-6
- Staron RS, Leonardi MJ, Karapondo DL, Malicky ES, Falkel JE, Hagerman FC, Hikida RS. Strength and skeletal muscle adaptations in heavy-resistance-trained women after detraining and retraining. *J Appl Physiol* 1991. PMID 1827108, doi:10.1152/jappl.1991.70.2.631
- Wall BT, Dirks ML, van Loon LJ. Skeletal muscle atrophy during short-term disuse: implications for age-related sarcopenia. *Ageing Res Rev* 2013. PMID 23948422, doi:10.1016/j.arr.2013.07.003
- Wall BT, Dirks ML, Snijders T, Senden JM, Dolmans J, van Loon LJ. Substantial skeletal muscle loss occurs during only 5 days of disuse. *Acta Physiol (Oxf)* 2014. PMID 24168489, doi:10.1111/apha.12190
- Wall BT, Dirks ML, Snijders T, van Dijk JW, Fritsch M, Verdijk LB, van Loon LJ. Short-term muscle disuse lowers myofibrillar protein synthesis rates and induces anabolic resistance to protein ingestion. *Am J Physiol Endocrinol Metab* 2016. PMID 26578714, doi:10.1152/ajpendo.00227.2015
- Wang Z, Ying Z, Bosy-Westphal A, Zhang J, Schautz B, Later W, Heymsfield SB, Müller MJ. Specific metabolic rates of major organs and tissues across adulthood: evaluation by mechanistic model of resting energy expenditure. *Am J Clin Nutr* 2010. PMID 20962155, doi:10.3945/ajcn.2010.29885
- Weinheimer EM, Sands LP, Campbell WW. A systematic review of the separate and combined effects of energy restriction and exercise on fat-free mass in middle-aged and older adults: implications for sarcopenic obesity. *Nutr Rev* 2010. PMID 20591106, doi:10.1111/j.1753-4887.2010.00298.x
- Wernbom M, Augustsson J, Thomeé R. The influence of frequency, intensity, volume and mode of strength training on whole muscle cross-sectional area in humans. *Sports Med* 2007. PMID 17326698, doi:10.2165/00007256-200737030-00004
- Wittbrodt MT, Millard-Stafford M. Dehydration impairs cognitive performance: a meta-analysis. *Med Sci Sports Exerc* 2018. PMID 29933347, doi:10.1249/MSS.0000000000001682
- Xie H, Hao T, Niu W, et al. Incidence and risk factors of refeeding syndrome in critically ill patients: a systematic review and meta-analysis. *Clin Nutr* 2026. PMID 42624024, doi:10.1016/j.clnu.2026.106734

**Not used as evidence** (looked for, not verifiable): Lieberson AD, *Scientific American* 2004 on survival
without food — no DOI or PMID, not indexed; Kacem et al. 2023 on body fat and running performance — preprints
only (doi:10.20944/preprints202311.1371.v1 and doi:10.21203/rs.3.rs-3021048/v1), not peer reviewed; EFSA Panel
on Dietetic Products, Nutrition and Allergies, "Scientific opinion on dietary reference values for water",
*EFSA Journal* 2010;8(3):1459, doi:10.2903/j.efsa.2010.1459 — citation believed correct but the record was
unreachable (HTTP 403) and its values are therefore not quoted.
