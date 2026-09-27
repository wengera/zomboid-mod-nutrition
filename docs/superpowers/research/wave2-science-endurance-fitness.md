# Science: endurance, cardiorespiratory fitness and their nutritional determinants

Research note for the realism nutrition mod, wave 2. Scope: how aerobic fitness is trained and lost, and how
carbohydrate and energy availability, iron, hydration, caffeine, protein, micronutrients, alcohol, sleep and
body composition move endurance capacity — with the engine mapping the mod needs. Compiled 2026-09-27 against
design spec §§ 4.1, 4.3, 4.5, 7 and the jar reading `jar-endurance-fatigue-sleep.md` §§ Summary, B.

## How to read this

Grades, strongest first — the same set the science register uses:

| Grade | Meaning |
|---|---|
| `MA` | Meta-analysis or systematic review |
| `RCT` | Randomised controlled trial, controlled crossover, or a primary human training/inpatient trial (the population cell says when a trial was single-arm and uncontrolled) |
| `COH` | Cohort, observational, family study, or a regression derived from a measured cross-section |
| `AUTH` | Authoritative report (IOC/ACSM/IOM consensus or position stand, WHO, DRI) |
| `TXT` | Narrative review, textbook chapter, or modelling paper |

Every citation below was verified by fetching its Europe PMC record over the REST API and confirming that
title, authors, journal and year match the citation as written; every number quoted comes from that record's
own abstract. Nothing here is quoted from memory. Where a widely repeated number lives only in a paywalled
full text and no record I fetched carried it, the row says **unverified** and the number must not ship.

Three standing cautions for this particular subject:

- **Two different quantities.** "VO₂max" and "endurance performance" (time to exhaustion, time trial) move
  together but not at the same rate and not always in the same direction. Hickson's reduced-training series is
  the cleanest demonstration: VO₂max held while long-term endurance fell. The mod has one latent variable, so
  it is modelling the *endurance-performance* quantity and using VO₂max literature as its proxy; say so.
- **Population transfer.** Nearly all of this is healthy 18-45-year-olds, athletes, or clinic patients, in
  laboratories, well fed, on a schedule. None of it is people running from zombies on scavenged food. Treat
  each number as a central tendency to widen, not a constant.
- **Trainability is heritable and wildly variable.** The same 20-week programme moves one person's VO₂max by
  nothing and another's by more than a litre per minute (Bouchard 1999). A single-track game model is picking
  the population mean by construction; a per-character trainability roll is the honest alternative and is
  proposed as a game choice, not as evidence.

Where a row restates something already in `science-energy-body.md` (hydration thresholds especially), the row
says so; this note adds the later syntheses and the endurance-specific reading rather than re-deriving them.
Three sibling wave-2 reports overlap this one at the edges and the controller should dedupe the register rows
across all four: `wave2-science-fatigue-sleep.md` (sleep and fatigue — it also cites Craven 2022, which appears
here only for its endurance coefficient), `wave2-science-strength-training.md` (the strength side of training
adaptation) and `wave2-jar-training-signals.md` (which engine events report training). Where a number appears in
two reports it needs **one** register row, and this note's use of it should be re-pointed at that row.

## 1. Training and aerobic fitness

| parameter | value / equation | range or uncertainty | population | grade | citation |
|---|---|---|---|---|---|
| VO₂max gain, continuous endurance training vs no-exercise control | **+4.9 mL·kg⁻¹·min⁻¹** ("possibly large beneficial effect") | 95 % confidence limits **±1.4** | 28 controlled trials, 723 participants, healthy 18-45 y (25.1 ± 5 y), baseline VO₂max 40.8 ± 7.9 mL·kg⁻¹·min⁻¹, training ≥2 wk | MA | Milanović, Sporiš & Weston 2015, Sports Med, PMID 26243014, doi:10.1007/s40279-015-0365-0 |
| VO₂max gain, HIIT vs no-exercise control | **+5.5 mL·kg⁻¹·min⁻¹** ("likely large") | ±1.2 | as above | MA | Milanović 2015 (as above) |
| HIIT advantage over continuous training | **+1.2 mL·kg⁻¹·min⁻¹** ("possibly small beneficial") | ±0.9 | as above | MA | Milanović 2015 (as above) |
| Effect of *low* starting fitness on the gain | endurance training **+1.4** (±2.0); HIIT **+3.2** (±1.9) mL·kg⁻¹·min⁻¹ extra | overlapping limits for the endurance arm; the HIIT modifier is "likely moderate" | as above | MA | Milanović 2015 (as above) |
| Effect of longer programme duration on the gain | endurance **+2.2** (±3.0); HIIT **+3.0** (±1.9) mL·kg⁻¹·min⁻¹ extra | limits cross zero for the endurance arm | as above | MA | Milanović 2015 (as above) |
| VO₂max gain, interval training, absolute | **+0.51 L·min⁻¹** | 95 % CI 0.43-0.60; I² = 70, random effects. A 9-study/72-subject subset using *longer* intervals gained **~0.8-0.9 L·min⁻¹** with "a marked response in all subjects" | 37 studies / 40 training groups, 334 subjects (120 women), sedentary-to-recreationally-active, <45 y, 6-13 wk, ≥3 d/wk, ≥10 min high-intensity work | MA | Bacon, Carter, Ogle & Joyner 2013, PLoS One, PMID 24066036, doi:10.1371/journal.pone.0073182 |
| Intensity dose-response for VO₂max | **None detectable.** Meta-regression on intensity, session dose, baseline VO₂max and total volume: Q₄ = 1.36, p = 0.85, **R² = 0.05**. Tertiles ~60-70 %, ~80-92.5 %, ~100-250 % VO₂max gave **+0.29 ± 0.15, +0.26 ± 0.10, +0.35 ± 0.17 L·min⁻¹** (ES 0.77, 0.68, 0.80), no significant difference — despite significantly lower session dose and total volume in the higher tertiles | the null is the finding; it constrains any monotone intensity term | 28 studies, young healthy adults (23 ± 1 y, VO₂max 3.4 ± 0.8 L·min⁻¹) | MA | Scribbans, Vecsey, Hankinson, Foster & Gurd 2016, Int J Exerc Sci, PMID 27182424, doi:10.70252/hhbr9374 |
| Time course of adaptation | VO₂max rises for the **first 3 weeks** and then stays constant unless the work rate is raised; **half-time of the rise t½ = 10.3 and 10.8 days** across two successive 4- and 5-wk blocks; total **+23 % over 9 wk**. Submaximal heart rate and blood lactate also fall within 2-3 wk of each step-up | n = 9, single-arm, no control group | 9 adults, 40 min/d, 6 d/wk cycling + running | RCT (single-arm longitudinal) | Hickson, Hagberg, Ehsani & Holloszy 1981, Med Sci Sports Exerc, PMID 7219130, doi:10.1249/00005768-198101000-00012 |
| Maintenance at reduced **frequency** | After 10 wk at 6 d/wk (VO₂max +25 % cycling, +20 % treadmill), dropping to **4 d/wk or 2 d/wk** at unchanged intensity and duration held VO₂max at trained level, checked at 5-wk intervals, **for 15 weeks** | n = 12; both reduced groups behaved the same | 12 adults (mean 23 y) | RCT (parallel reduced-training arms) | Hickson & Rosenkoetter 1981, Med Sci Sports Exerc, PMID 7219129, doi:10.1249/00005768-198101000-00011 |
| Maintenance at reduced **duration** | Cutting 40 min/d to **26 or 13 min/d** held VO₂max and ~5-min endurance for 15 wk; long-term (≥2 h) endurance held in the 26-min group but fell **10 % (139 → 123 min)** in the 13-min group; LV mass stayed +15-20 % | n = 13 | 13 adults, same programme | RCT (parallel reduced-training arms) | Hickson, Kanakis, Davis, Moore & Rich 1982, J Appl Physiol, PMID 6214534, doi:10.1152/jappl.1982.53.1.225 |
| Reduced **intensity** is *not* substitutable | Cutting work rate by ⅓ or ⅔ at unchanged frequency and duration **lost** VO₂max (still above pre-training); long-term endurance fell **21 % (184 → 145 min)** at ⅓ and **30 % (202 → 141 min)** at ⅔; calculated LV mass returned to control values in both | n = 12; the ⅔ group lost more than the ⅓ group | 12 adults, 10 wk of training then 15 wk reduced | RCT (parallel reduced-training arms) | Hickson, Foster, Pollock, Galassi & Rich 1985, J Appl Physiol, PMID 3156841, doi:10.1152/jappl.1985.58.2.492 |
| Detraining, short-term cessation (<4 wk) | VO₂max **ES = −0.62** | 95 % CI −0.94 to −0.31, p < 0.01, I² = 35.3 % | 21 studies of trained individuals, from 3315 screened | MA | Zheng, Pan, Jiang & Shen 2022, Biomed Res Int, PMID 36017396, doi:10.1155/2022/2130993 |
| Detraining, long-term cessation (>4 wk) | VO₂max **ES = −1.42**, significantly larger than short-term (Q = 6.5, p = 0.01) | 95 % CI −1.99 to −0.84, I² = 76.3 %, Egger p < 0.01 (small-study bias likely) | as above | MA | Zheng 2022 (as above) |
| What detraining takes away, mechanism | Recently acquired VO₂max gains are **completely lost**; a long-trained athlete's VO₂max "declines markedly but remains above control values". Carriers: blood volume, cardiac dimensions, ventilatory efficiency, stroke volume; then capillarisation, a-vO₂ difference, oxidative enzyme activity; muscle glycogen returns to baseline and the lactate threshold falls. Losses can be limited by reduced training **as long as intensity is maintained** | narrative review, two parts, split at 4 weeks | trained athletes and recently trained individuals | TXT | Mujika & Padilla 2000, Sports Med, Part I PMID 10966148, doi:10.2165/00007256-200030020-00002; Part II PMID 10999420, doi:10.2165/00007256-200030030-00001 |
| Bed rest (total inactivity) | VO₂max declines **linearly** with days: **−0.30 %/day** when expressed as L·min⁻¹, **−0.43 %/day** when normalised to body weight (difference not statistically significant) | 80 studies since 1949, 949 participants (>90 % men), median age 24.5 y, bed rest 1-90 days. **15-26 % of the variance in the decline is explained by pre-bed-rest VO₂max** — the fitter lose more. Neither body-weight nor lean-mass loss was associated with the VO₂max decline | strict bed rest, no countermeasures | MA | Ried-Larsen, Aarts & Joyner 2017, J Appl Physiol, PMID 28705999, doi:10.1152/japplphysiol.00415.2017 |
| Individual variability in trainability | Mean gain **≈+400 mL·min⁻¹** over a standardised 20-wk programme, but "some individuals experiencing little or no gain, whereas others gained **>1.0 L·min⁻¹**"; between-family variance 2.5× within-family; **heritability of the response ≈47 %** | the spread, not the mean, is the finding | 481 sedentary adults from 98 two-generation families, 20 wk cycle training | COH (family study) | Bouchard, An, Rice, Skinner, Wilmore, Gagnon, Pérusse, Leon & Rao 1999, J Appl Physiol, PMID 10484570, doi:10.1152/jappl.1999.87.3.1003 |
| Prescription floor for maintaining fitness | **≥30 min/d on ≥5 d/wk moderate (≥150 min/wk)**, or ≥20 min/d on ≥3 d/wk vigorous (≥75 min/wk), or a combination totalling **≥500-1000 MET·min/wk**; resistance work on 2-3 d/wk | position stand; also states that people doing *less* than the target still benefit | apparently healthy adults of all ages | AUTH | Garber et al. (ACSM position stand) 2011, Med Sci Sports Exerc, PMID 21694556, doi:10.1249/mss.0b013e318213fefb |
| Adding training on top of an already-trained state | Of 11 supplementary modalities, five beat continuing normal training: blood-flow-restriction training, HIIT, intermittent hypoxic training, SIT and small-sided games; HIIT and SIT were the most consistent, with a dose-response NMA over 31 studies | Bayesian NMA; confidence assessed with CINeMA | 61 studies, healthy trained athletes | MA | Li, Zhou, Li, Shibo, Wang, Feng & Wu 2026, Front Physiol, PMID 42597392, doi:10.3389/fphys.2026.1906583 |

**Interpretation.** Four numbers do most of the work for a game. First, the *size* of the whole trainable
range is modest and bounded: about **+5 mL·kg⁻¹·min⁻¹**, or roughly **+15-25 %** of an untrained person's
VO₂max, is the meta-analytic expectation from weeks of real training (Milanović; Hickson's +23 % over 9 wk),
with the extraordinary responders reaching about **+1 L·min⁻¹** (Bacon, Bouchard) — so a latent fitness
variable that can double a character's capacity is unphysiological. Second, the *rate* is fast and
self-limiting: a half-time near **10-11 days** and a plateau within about **3 weeks** at any fixed workload
(Hickson 1981), which is exactly the shape of a first-order approach to a stimulus-dependent ceiling and maps
cleanly onto a per-day exponential update. Third, **intensity buys the gain but frequency and duration only
have to defend it**: 2 d/wk at maintained intensity held a 25 % gain for 15 weeks, and so did a two-thirds cut
in session length, but a one-third cut in *intensity* lost ground immediately (Hickson 1981/1982/1985) — the
asymmetry is the single most game-relevant finding in this section, because it says a survivor who sprints
hard twice a week keeps their fitness while one who strolls all day does not build it. Fourth, loss is slower
than gain but not slow: **−0.3 to −0.43 %/day under total bed rest** (Ried-Larsen), a pooled short-cessation
effect of ES −0.62 rising to −1.42 past four weeks (Zheng), and a fitter character losing proportionally more
(Ried-Larsen's 15-26 % of variance). The intensity dose-response null (Scribbans) is worth respecting: within
the range humans actually train, total oxidative stimulus matters more than where on the intensity spectrum it
was delivered, so the mod should not award a steep intensity exponent — a coarse three-band intensity (walk /
run / sprint-and-fight) is as much resolution as the evidence supports.

## 2. Carbohydrate and energy availability

| parameter | value / equation | range or uncertainty | population | grade | citation |
|---|---|---|---|---|---|
| Resting muscle glycogen, normative | **462 ± 132 mmol·kg⁻¹ dry muscle** at normal CHO availability and VO₂max 53 ± 8 mL·kg⁻¹·min⁻¹ | SD as shown; the MA's own stated purpose is to supply normative values | meta-regression over 181 biopsy studies of continuous/intermittent cycling and running in healthy participants | MA | Areta & Hopkins 2018, Sports Med, PMID 29923148, doi:10.1007/s40279-018-0941-1 |
| Diet moves the resting store | **High CHO availability +102 mmol·kg⁻¹** (±47, 90 % CL) — a moderate increase; **low availability (depletion + low-CHO diet) −253 mmol·kg⁻¹** (±30) — a *very large* decrease | high = ≥6 g·kg⁻¹·d⁻¹ for ≥3 d or ≥7 g·kg⁻¹·d⁻¹ for ≥2 d | as above | MA | Areta & Hopkins 2018 (as above) |
| Fitness moves the resting store | **+10 mL·kg⁻¹·min⁻¹ VO₂max → +67 mmol·kg⁻¹** (±15) at normal CHO, +29 (±44) at low, +80 (±40) at high | so a trained character stores more glycogen — a second, independent route from fitness to endurance capacity | as above | MA | Areta & Hopkins 2018 (as above) |
| Glycogen *use* scales with intensity, not fitness | A 30 %-of-VO₂max increase in intensity raised utilisation by 41 (±20) mmol·kg⁻¹ at 5 min and **87-134 mmol·kg⁻¹ at all later timepoints**; a +10 mL·kg⁻¹·min⁻¹ VO₂max difference had "mainly clear trivial effects"; CHO ingestion and continuous-vs-intermittent mode also trivial. Running used **70 mmol·kg⁻¹ less than cycling** (±32) | a starting store 200 mmol·kg⁻¹ higher raised use at fatigue by 143 (±33) — a higher store is partly spent, not banked | as above | MA | Areta & Hopkins 2018 (as above) |
| Glycogen depletion rate, hard exercise | **51.5 ± 5.4 mmol GU·kg⁻¹·h⁻¹** over the first 2 h at 71 ± 1 % VO₂max, slowing to **23.0 ± 14.3** in the third hour | n = 7 | 7 endurance-trained cyclists, exercise to fatigue | RCT (crossover) | Coyle, Coggan, Hemmert & Ivy 1986, J Appl Physiol, PMID 3525502, doi:10.1152/jappl.1986.61.1.165 |
| Hypoglycaemia at the point of fatigue | Fatigue on placebo came at **3.02 ± 0.19 h**, preceded by plasma glucose falling to **2.5 ± 0.5 mM** and RER from 0.85 to 0.80. CHO feeding (2.0 g·kg⁻¹ then 0.4 g·kg⁻¹ every 20 min) held glucose at 4.2-5.2 mM and extended time to fatigue to **4.02 ± 0.33 h (+33 %, p < 0.01)** — *with muscle glycogen use unchanged over the first 3 h* | n = 7 | as above | RCT (crossover) | Coyle et al. 1986 (as above) |
| Carbohydrate supplementation and performance, pooled | **82 % of 61 randomised performance trials (50/61) showed a statistically significant benefit** over water placebo; 18 % no change. A **significant correlation (p = 0.0036) between total exercise duration and the size of the percent benefit** | n = 679 subjects; all-out or endurance protocols, no team sports, CHO-only vs water | mixed trained adults | MA | Stellingwerff & Cox 2014, Appl Physiol Nutr Metab, PMID 24951297, doi:10.1139/apnm-2014-0027 |
| Two different mechanisms by duration | **~1 h exercise:** benefit is central (oral CHO receptors, reward centres); "the type and (or) amount of CHO and its ability to be absorbed and oxidized appear completely irrelevant". **>2 h:** the mechanism is delivery — **>90 g/h** CHO oxidation, with multiple transportable carbohydrates (glucose:fructose) helping | this is why a game's CHO effect must be duration-dependent, not a flat buff | as above | MA | Stellingwerff & Cox 2014 (as above) |
| Ketogenic low-CHO high-fat diet, pooled | **No significant effect on VO₂max, time to exhaustion, HRmax or RPE**; a significant overall effect only on substrate oxidation (RER) | 10 studies met criteria; the authors call for higher-quality interventions | endurance athletes | MA | Cao, Lei, Wang & Cheng 2021, Nutrients, PMID 34445057, doi:10.3390/nu13082896 |
| Ketogenic diet, the controlled elite trial | 3 wk intensified training raised VO₂peak in all three diet groups (p < 0.001, 90 % CI 2.55-5.20 %), but the LCHF group (<50 g/d CHO, 78 % energy as fat) **increased the O₂ cost of race walking at race-relevant speeds** and LCHF **"impairs performance in elite endurance athletes despite a significant improvement in peak aerobic capacity"**. Peak fat oxidation reached 1.57 ± 0.32 g·min⁻¹ | n = 29 in three isoenergetic arms (HCHO 9, PCHO 10, LCHF 10) | world-class elite race walkers | RCT | Burke, Ross, Garvican-Lewis, Welvaert, Heikura, Forbes, Mirtschin, Cato, Strobel, Sharma & Hawley 2017, J Physiol, PMID 28012184, doi:10.1113/JP273230 |
| Keto adaptation, the mechanism and its limit | Fat oxidation roughly **doubles to ~1.5 g·min⁻¹** within 3-4 weeks and possibly 5-10 days, and the intensity of peak fat oxidation shifts from **~45 % to ~70 % of VO₂max**; but keto-adaptation "may impair the muscle's ability to use glycogen for oxidative fates", compromising performance **above ~80 % VO₂max**, and individual responsiveness is "varied, with extremes at both ends" | evidence for glycogen normalisation with long adaptation is called "weak" | elite endurance athletes | TXT | Burke 2021, J Physiol, PMID 32358802, doi:10.1113/JP278928 |
| Intermittent fasting (Ramadan), pooled | **Deleterious on mean and peak power (Wingate, repeated sprint) and on morning sprint performance; aerobic performance, strength, jump height, fatigue index and total work not affected** | 11 studies, random effects, Downs & Black quality assessment; the authors conclude most parameters were unaffected | athletes fasting during Ramadan (daytime food *and fluid* restriction) | MA | Abaïdia, Daab & Bouzid 2020, Sports Med, PMID 31960369, doi:10.1007/s40279-020-01257-0 |
| Low energy availability, the threshold | LH pulsatility "was unaffected by an energy availability of **30 kcal/kg LBM·d**", but below that threshold pulse frequency fell and amplitude rose (p < 0.04); the pattern tracked plasma glucose, β-hydroxybutyrate, GH and cortisol | n = 29; 5-day exposures at 45 vs 10/20/30 kcal·kg LBM⁻¹·d⁻¹, exercise 15 kcal·kg LBM⁻¹·d⁻¹ at 70 % VO₂max | 29 regularly menstruating, habitually sedentary young women of normal body composition | RCT (randomised crossover) | Loucks & Thuma 2003, J Clin Endocrinol Metab, PMID 12519869, doi:10.1210/jc.2002-020369 |
| Low energy availability and measured performance | Ovarian-suppressed swimmers, with significantly lower energy intake and energy availability, showed a **9.8 % decline in 400-m swim velocity over 12 weeks against an 8.2 % improvement in the cyclic group** — an ~18-point swing | n = 10 (5 per group); prospective, not randomised; adolescent females only | 10 junior elite female swimmers, 15-17 y, 12-wk season | COH (prospective) | Vanheest, Rodgers, Mahoney & De Souza 2014, Med Sci Sports Exerc, PMID 23846160, doi:10.1249/mss.0b013e3182a32b72 |
| REDs, the consensus frame | REDs is "a syndrome of deleterious health and performance outcomes experienced by female **and male** athletes exposed to low energy availability (LEA; inadequate energy intake in relation to exercise energy expenditure)"; the 2023 update adds "emerging data demonstrating the growing role of **low carbohydrate availability**", introduces a Physiological Model distinguishing **problematic from adaptable LEA exposure** with individual moderating factors, and a Clinical Assessment Tool v2 based on accumulated severity | >170 original papers since the 2018 statement; a consensus, not a pooled estimate | male and female athletes | AUTH (consensus) | Mountjoy et al. 2023, Br J Sports Med, PMID 37752011, doi:10.1136/bjsports-2023-106994; the 2018 update is Mountjoy et al. 2018, Br J Sports Med, PMID 29773536, doi:10.1136/bjsports-2018-099193 (record verified; Europe PMC carries no abstract for it, so nothing is quoted from it) |

**Interpretation.** Carbohydrate is the one nutritional lever in this whole note whose endurance effect is
large, fast-acting and consistently measured, and the mod should treat it accordingly. The store itself is
well-quantified: about **460 mmol·kg⁻¹ dry muscle** at a normal diet, moving **+100 on a high-CHO diet and
−250 when depleted and kept low** (Areta & Hopkins) — a swing of roughly ±25-55 % that is bigger than
anything training does to VO₂max, and it refills or empties in *days*, not weeks. Depletion is the classic
mechanism of endurance failure: hard work spends about **50 mmol·kg⁻¹·h⁻¹**, so a few hours of running empties
a normal store, and at that point plasma glucose falls to **2.5 mM** and the athlete stops (Coyle) — feeding
carbohydrate at the same glycogen use bought a **third more time**, which is the single cleanest "eating
restores endurance *capacity*, not just hunger" result available. Carbohydrate's benefit grows with the
duration of the effort (Stellingwerff & Cox's p = 0.0036 correlation), and below about an hour the effect is
partly central — a fact that lets the mod justify an immediate, small "just ate something sweet" endurance
credit without pretending it is metabolic. The low-carb story is the mirror image and is worth encoding as a
*trade*: fat oxidation doubles within days to weeks and the crossover shifts from 45 % to 70 % of VO₂max, but
economy worsens, high-intensity work above ~80 % VO₂max is impaired, and pooled performance effects are null
(Burke 2017/2021; Cao 2021) — so a meat-and-fat survivor should walk and forage well and sprint and fight
badly, which is both evidenced and good play. Energy availability is the slow, structural version of the same
thing: **below 30 kcal·kg LBM⁻¹·d⁻¹** the endocrine axis starts to fail (Loucks & Thuma), and the one
prospective performance measurement available shows an **~18-percentage-point swing in a season** between
energy-replete and energy-deficient athletes (Vanheest) — small n, adolescent females, so it sets the order of
magnitude of a multi-week trainability penalty and no more. Finally, the Ramadan meta-analysis is the useful
corrective for the acute case: a day of not eating costs **power and sprints**, not aerobic capacity or total
work (Abaïdia) — so the mod's short-term fasting penalty belongs on burst output and on the endurance *floor*,
not on the walking economy.

## 3. Iron and anaemia

| parameter | value / equation | range or uncertainty | population | grade | citation |
|---|---|---|---|---|---|
| Iron-deficiency anaemia and aerobic capacity | "A **strong causal effect** of severe iron-deficiency anaemia (SIDA) and moderate IDA (MIDA) on aerobic capacity in animals and humans"; presumed mechanism reduced oxygen transport, with tissue iron deficiency contributing through reduced cellular oxidative capacity | 29 research reports reviewed along a SIDA → MIDA → IDNA continuum; a critical review, not a pooled estimate | animal and human studies; field and laboratory | MA (systematic critical review) | Haas & Brownlie 2001, J Nutr, PMID 11160598, doi:10.1093/jn/131.2.676S |
| Iron deficiency and endurance vs efficiency | Endurance capacity "also compromised in SIDA and MIDA", but the strong animal mechanism (cellular oxidative capacity) "**has not been demonstrated in humans**". **Energetic efficiency was affected at *all* levels of iron deficiency in humans, in the laboratory and the field** — including iron deficiency without anaemia. Reduced field work productivity is likely from anaemia and oxygen transport | the IDNA effects are called "more subtle" but affecting far more people | as above | MA | Haas & Brownlie 2001 (as above) |
| Iron supplementation, women of reproductive age | **Relative VO₂max +2.35 mL·kg⁻¹·min⁻¹** (95 % CI 0.82-3.88, p = 0.003, 18 studies); absolute VO₂max +0.11 L·min⁻¹ (0.03-0.20, p = 0.01, 9 studies); overall **SMD 0.37** (0.11-0.62, p = 0.005, 20 studies) | Only 3 of 24 studies were at overall low risk of bias | 24 RCTs of daily oral iron vs control in women of reproductive age, from 6757 titles screened | MA | Pasricha, Low, Thompson, Farrell & De-Regil 2014, J Nutr, PMID 24717371, doi:10.3945/jn.113.189589 |
| Submaximal cost falls with repletion | Heart rate at a defined workload **−4.05 bpm** (95 % CI −7.25 to −0.85, p = 0.01, 6 studies) and the **proportion of VO₂max required −2.68 %** (−4.94 to −0.41, p = 0.02, 6 studies) | as above | as above | MA | Pasricha 2014 (as above) |
| Iron treatment in **non-anaemic** iron-deficient endurance athletes | Large effects on ferritin (Hedges' g = 1.088, 95 % CI 0.914-1.263), serum iron (1.004) and transferrin saturation (0.741); **moderate** effects on haemoglobin (0.695, 0.533-0.836) and **VO₂max (g = 0.610, 95 % CI 0.399-0.821, p < 0.001)** | 17 studies; regression showed treatments lasting **beyond 80 days had the least effect on ferritin** | iron-deficient non-anaemic (IDNA) endurance athletes | MA | Burden, Morton, Richards, Whyte & Pedlar 2015, Br J Sports Med, PMID 25361786, doi:10.1136/bjsports-2014-093624 |
| The contradicting result in general adults | Iron supplementation **reduced self-reported fatigue (SMD −0.38, 95 % CI −0.52 to −0.23, I² = 0 %, 4 trials, 714 participants)** but showed **no effect on objective physical capacity: VO₂max SMD 0.11 (95 % CI −0.15 to 0.37, I² = 0 %, 9 trials, 235 participants)** or timed exercise tests | 18 unique trials, 1170 patients, from 11 580 citations; primary care, not athletes | iron-deficient non-anaemic adults ≥18 y | MA | Houston, Hurrie, Graham, Perija, Rimmer, Rabbani, Bernstein, Turgeon, Fergusson, Houston, Abou-Setta & Zarychanski 2018, BMJ Open, PMID 29626044, doi:10.1136/bmjopen-2017-019240 |
| The same contradiction, athletes, 2024 | Oral iron raised ferritin (SMD 1.27, 95 % CI 0.44-2.10, p = 0.006) but haemoglobin (SMD 1.31, −0.29 to 2.93, p = 0.099), sTfR and transferrin saturation were unaltered; **VO₂max only a trend (SMD 0.49, 95 % CI −0.09 to 1.07, p = 0.086)**; GRADE quality moderate to low | 13 studies, n = 449; PROSPERO CRD42022330230 | healthy adult athletes | MA | Šmid, Golja, Hadžić, Abazović, Drole & Paravlic 2024, Sports Med, PMID 38407751, doi:10.1007/s40279-024-01992-8 |
| Repletion changes the *training response*, 6 weeks | 100 mg ferrous sulfate/day for 6 wk with 4 wk of training: both groups improved 15-km cycle time, but **the improvement was significantly greater in the iron group (p = 0.04)**, partly attributable to rises in ferritin and Hb | n = 42, randomised double-blind | 42 iron-depleted (ferritin <16 µg/L), non-anaemic (Hb >12 g/dL) women, 18-33 y | RCT | Hinton, Giordano, Brownlie & Haas 2000, J Appl Physiol, PMID 10710409, doi:10.1152/jappl.2000.88.3.1103 |
| Repletion and VO₂max adaptation, 6 weeks | 50 mg FeSO₄ twice daily for 6 wk with 4 wk of cycle training: VO₂max improved in both arms but **significantly more in the iron group**, with Hb and haematocrit *unchanged* — and stratification showed the effect came entirely from the subjects with the worst baseline iron status (sTfR > 8.0 mg/L) | n = 41, randomised double-blind | 41 untrained, iron-depleted, non-anaemic women | RCT | Brownlie, Utermohlen, Hinton, Giordano & Haas 2002, Am J Clin Nutr, PMID 11916761, doi:10.1093/ajcn/75.4.734 |
| Time course of haemoglobin rise with oral iron | **Unverified.** The commonly quoted "~1 g/dL per 2-3 weeks" could not be matched to any record I fetched; the BSG guideline record is verified (Snook et al. 2021, Gut, PMID 34497146, doi:10.1136/gutjnl-2021-325210) but its abstract carries no rate. The evidenced statement is the *functional* one: **6 weeks of repletion is enough to change the aerobic training response** (Hinton 2000; Brownlie 2002), and ferritin repletion effects are largely realised **within ~80 days** (Burden 2015) | — | — | — | do not ship a per-week Hb figure; see Gaps |

**Interpretation.** Iron splits cleanly into two regimes and the mod should model them as two different things.
**Anaemic** iron deficiency is a large, mechanistically settled hit to aerobic capacity — oxygen transport is
simply reduced, the effect is causal, and it shows up in the field as lost work productivity (Haas & Brownlie)
— so a clinical-grade iron deficiency deserves the biggest single nutritional penalty in the model.
**Non-anaemic** iron deficiency is where the literature genuinely disagrees: pooled across IDNA *endurance
athletes* the VO₂max effect of repletion is moderate and clearly positive (Burden, g = 0.61), pooled across
IDNA *general adults* it is null while **fatigue still falls** (Houston, SMD −0.38 with I² = 0 %), and the 2024
athlete meta-analysis put VO₂max back to a non-significant trend (Šmid, p = 0.086). The reconciliation that
fits all three is that marginal iron deficiency costs **perceived effort and the ability to adapt to training**
before it costs measured capacity — which is exactly what the two 6-week repletion RCTs found: the iron groups
did not start fitter, they *got* fitter faster (Hinton; Brownlie), and Brownlie's stratification showed the
benefit lived entirely in the worst-off subjects. For a game that is a gift, because it maps onto two different
engine surfaces: marginal iron should slow the *gain* of the trained-capacity variable and raise fatigue
accrual, while anaemic iron should cut the capacity itself. The magnitude anchor for the anaemic case is
Pasricha's **+2.35 mL·kg⁻¹·min⁻¹** VO₂max and **−4 bpm / −2.7 % of VO₂max** at a fixed workload, i.e. roughly a
5 % capacity difference and a similar-sized change in the cost of doing the same work. Timescale: weeks, not
days — 6 weeks was enough to change the training response, and ferritin gains are mostly banked inside ~80
days, so the mod's iron pool should have a repletion time constant in the **3-8 week** range and a depletion
time constant longer than that.

## 4. Hydration

The baseline water-requirement and sweat-rate numbers are already in `science-energy-body.md` § 7 and are not
repeated. This section is only about the **endurance threshold argument**, which the design already turned into
a ruling (spec § 4.4, assumption 11), and what the later syntheses do to it.

| parameter | value / equation | range or uncertainty | population | grade | citation |
|---|---|---|---|---|---|
| The review consensus threshold | "a **≥2 % dehydration threshold** for impaired endurance exercise performance mediated by volume loss"; in contrast "**no clear threshold or plausible mechanism(s)** support the marginal, but potentially important, impairment in strength, and power"; the cognitive effect "appears small and related primarily to distraction or discomfort" | a structured review, not a pooled estimate; the review's own frame is that the impact "is therefore likely dependent upon the makeup of the task itself" | comprehensive review of the dehydration literature | TXT | Cheuvront & Kenefick 2014, Compr Physiol, PMID 24692140, doi:10.1002/cphy.c130017 |
| The counter-pole, self-paced exercise | Dehydration of a mean 2.20 % body mass in self-paced (time-trial) cycling produced **+0.06 %** change in performance — not significant; drinking to thirst beat both under- and over-drinking | 5 studies, 39 subjects, 13 effect estimates; mean 26.0 °C, 61 % RH, 68 % VO₂max, 86 min trials | trained cyclists | MA | Goulet 2011, Br J Sports Med, PMID 21454440, doi:10.1136/bjsm.2010.077966 |
| **The reconciliation, and the row that matters most for a game** | Splitting laboratory studies by protocol: under **time-trial (self-paced)** exercise dehydration *increased* performance by 0.09 ± 2.60 % (p = 0.9); under **clamped fixed-intensity** exercise it *reduced* it by **1.91 ± 1.53 % (p < 0.05)**, and only under fixed intensity did **≥2 % body-mass loss** impair endurance capacity (p = 0.03). Conclusion: "EID ≤ 4 % bodyweight is very unlikely to impair EP under real-world exercise conditions (time-trial type exercise)"; under fixed intensity, "which may have some relevance for **military and occupational settings**, EID ≥ 2 % bodyweight is associated with a reduction in endurance capacity"; "the 2 % bodyweight loss rule has been established from findings of studies using [non-ecologically-valid] exercise protocols" | 15 articles, 28 effect estimates, 122 subjects | laboratory endurance trials | MA | Goulet 2013, Br J Sports Med, PMID 22763119, doi:10.1136/bjsports-2012-090958 |
| Starting *already* hypohydrated (as opposed to drying out during the effort) | AEP impaired by **2.4 ± 0.8 % (95 % CI 0.8-4.0)**; **VO₂peak −2.4 ± 0.8 % (0.7-4.0)**; **VO₂ at lactate threshold −4.4 ± 1.4 % (1.7-7.1)** | 15 manuscripts, 21/10/9 effect estimates, 186 subjects; mean body-mass deficit **3.6 ± 1.0 %** (range 1.7-5.6); mean test 22.3 ± 13.5 min | well-controlled human studies, ≥18 y, hypohydration induced ≥1 h before exercise | MA | Deshayes, Jeker & Goulet 2020, Sports Med, PMID 31728846, doi:10.1007/s40279-019-01223-5 |
| Muscle endurance and strength *do* fall — the correction to the "no strength effect" line | **Muscle endurance −8.3 ± 2.3 %** (p < 0.05, upper −8.4, lower −8.2); **strength −5.5 ± 1.0 %** (p < 0.05); **anaerobic power −5.8 ± 2.3 %** (p < 0.05); anaerobic capacity (−3.5 ± 2.3 %) and vertical jump (+0.9 ± 0.7 %) not significant. **No significant correlation with the *degree* of hypohydration**, and active (exercise/heat) dehydration cost an extra 5.4 ± 1.9 % (2.76-fold) over passive dehydration | 28 manuscripts; the dose-independence and the active/passive gap both suggest the effect is partly the *route* to dehydration, not the water deficit itself; the authors include Cheuvront, Kenefick and Goulet | mixed adults; trained subjects lost 3.3 % more (text truncated in the record at that point) | MA | Savoie, Kenefick, Ely, Cheuvront & Goulet 2015, Sports Med, PMID 26178327, doi:10.1007/s40279-015-0349-0 |
| Heat × hydration, the mechanism | Dehydration to ~4 % body-mass loss brings "hyperthermia, hyperventilation, cardiovascular strain with reductions in brain, skeletal muscle and skin blood perfusion, **greater reliance on muscle glycogen**, alterations in neural activity and, in some conditions, compromised muscle metabolism and aerobic capacity". The strain "can be attenuated or even prevented by: (1) ingesting fluids during exercise, (2) exercising in cold environments, and/or (3) working at intensities that require a small fraction of the overall body functional capacity" — cardiac output and muscle metabolism are stable at rest or small-muscle work but impaired during whole-body moderate-to-intense exercise | narrative physiological review | exercising humans | TXT | Trangmar & González-Alonso 2019, Sports Med, PMID 30671905, doi:10.1007/s40279-018-1033-y |
| Heat × hydration, the dose-response | "The magnitude of increase in core temperature and HR and the decline in SV are **graded in proportion to the amount of dehydration** accrued"; core-temperature rise correlated with serum osmolality and sodium | n = 8, four replacement conditions (0, 20, 48, 81 % of sweat loss) | 8 trained cyclists, 2 h moderate exercise in warm conditions | RCT (crossover) | Montain & Coyle 1992, J Appl Physiol, PMID 1447078, doi:10.1152/jappl.1992.73.4.1340 |
| Exercise-associated hyponatraemia | Serum [Na⁺] **<135 mmol·L⁻¹** during or within 24 h of sustained exercise; the proximate cause is overconsumption of hypotonic fluid, with non-osmotic vasopressin secretion contributing. Reported incidence **7-15 %** in marathon runners (symptomatic plus asymptomatic) | consensus statement; incidence figures carried over from `science-energy-body.md` § 7, which cites them to Klingert et al. 2022, doi:10.3390/jcm11226775 | endurance athletes | AUTH (consensus) | Hew-Butler et al. 2015, Clin J Sport Med, PMID 26102445, doi:10.1097/JSM.0000000000000221 |

**Interpretation.** The design's existing ruling — mild penalty from 2 %, steepening toward 4 % — survives the
later evidence, and Goulet 2013 gives it a mechanism the spec did not have. The apparent contradiction between
Cheuvront's ≥2 % threshold and Goulet's "nothing up to 4 %" is not a contradiction about physiology; it is a
difference between **self-paced** and **fixed-intensity** work. Under self-paced exercise a dehydrated athlete
slows down a little and finishes in the same time (+0.09 %); under **clamped intensity** — where the pace is
imposed and the only available response is to fail — dehydration costs about **1.9 % of power and lowers
endurance capacity from 2 % body-mass loss**, and Goulet explicitly names "military and occupational settings"
as where that case applies. **A Project Zomboid character is the clamped case**: the engine sets the run speed,
the player holds the key, and endurance is precisely the reserve that runs out. So the mod is entitled to the
2 % threshold on the *capacity* (endurance drain and floor) while remaining honest that a self-pacing human
would just walk slower. Two further numbers matter. Starting a day already dry is worse than drying out during
it: at a 3.6 % deficit, aerobic performance is down 2.4 % and **VO₂ at lactate threshold down 4.4 %**
(Deshayes) — the sub-maximal cost rises faster than the peak, which is the right shape for a drain multiplier
rather than a capacity cut. And the "dehydration does not affect strength" line in the earlier report needs
softening: the dedicated meta-analysis by largely the same authors found **muscle endurance −8.3 %** and
**strength −5.5 %** (Savoie), though with no correlation to the size of the deficit and a large active-versus-
passive confound, so the honest reading is "a real but dose-insensitive penalty, plausibly mediated by the heat
and effort that produced the dehydration". That last point is the argument for combining dehydration with heat
**multiplicatively** rather than additively: the strain is graded in proportion to the deficit (Montain &
Coyle), dehydration drives greater glycogen reliance (Trangmar), and the whole complex only bites during
whole-body moderate-to-hard work — all three of which the engine already has state for. Overdrinking must keep
a cost: hyponatraemia below 135 mmol/L at 7-15 % incidence in marathoners means chugging water is not free.

## 5. Other nutrients and substances

Caffeine pharmacokinetics, diuresis and sleep effects, and alcohol diuresis and sleep architecture, are already
in `science-minerals-fibre-fats.md` (§§ Caffeine, Alcohol) and are not repeated; magnesium's DRIs and the cramp
Cochrane review are in the same file. This section adds only the **endurance and recovery** side.

| parameter | value / equation | range or uncertainty | population | grade | citation |
|---|---|---|---|---|---|
| Caffeine, endurance, pooled | **3-6 mg/kg** gives mean power output **+3.03 ± 3.07 %** (ES 0.23 ± 0.15) and time-trial completion time **+2.22 ± 2.59 %** (ES 0.41 ± 0.2) | 46 randomised placebo-controlled studies; **2 studies found slower time trials and 5 found lower power** — real non-responders | trained adults | MA | Southward, Rutherfurd-Markwick & Ali 2018, Sports Med, PMID 29876876, doi:10.1007/s40279-018-0939-8 (also cited in `science-minerals-fibre-fats.md`) |
| Caffeine across all exercise types | Ergogenic for aerobic endurance, muscle strength, muscle endurance, power, jumping and speed; **"the magnitude of the effect of caffeine is generally greater for aerobic as compared with anaerobic exercise"**; GRADE quality generally moderate, some low to very low; "not all analyses provided a definite direction for the effect … when considering the 95 % prediction interval" | umbrella review of 11 reviews containing 21 meta-analyses; most primary studies were in young men | mixed | MA (umbrella) | Grgic, Grgic, Pickering, Schoenfeld, Bishop & Pedisic 2020, Br J Sports Med, PMID 30926628, doi:10.1136/bjsports-2018-100278 |
| Caffeine tolerance, measured | Acute 3 mg/kg raised 30-min work output in both groups before supplementation (caffeine group 383.3 ± 75.0 vs 344.9 ± 80.3 kJ, ES 0.49, p = 0.001). **After 28 days of 1.5-3.0 mg·kg⁻¹·d⁻¹ the benefit was gone** (precaf 383.3 ± 75.0 vs postcaf 358.0 ± 89.8 kJ, ES 0.31, p = 0.025) while the placebo group retained it (ES 0.05, NS). Circulating caffeine, hormones and substrate oxidation did not differ | n = 18, randomised, parallel; low-habitual consumers (<75 mg/d) only | 18 low-habitual caffeine consumers | RCT | Beaumont, Cordery, Funnell, Mears, James & Watson 2017, J Sports Sci, PMID 27762662, doi:10.1080/02640414.2016.1241421 |
| Protein during endurance training, pooled | **Time to exhaustion SMD 0.45 (95 % CI 0.15-0.76, p < 0.01)**; lean body mass SMD 0.13 (−0.01 to 0.28, p = 0.07); **VO₂max overall not significant**, with a subgroup hint that untrained individuals gain more (SMD 0.21); no significant effect on body weight, fat mass, or aerobic/anaerobic capacity | 23 randomised cross-over trials, 1146 participants; PROSPERO CRD420251034453 | endurance-training adults | MA | Xiao, Deng, Sun, Li & Gao 2025, Front Nutr, PMID 40851900, doi:10.3389/fnut.2025.1663860 |
| Vitamin D and physical performance | **Of 13 RCTs, only 7 measured physical performance and "none demonstrated a significant effect of vitamin D suppl[ementation]"**. Supplementation did raise 25(OH)D in insufficient athletes: **+15.2 ng/mL** at 3000 IU/d (95 % CI 10.7-19.7, I² = 0 %) and **+27.8 ng/mL** at 5000 IU/d (16.9-38.8, I² = 78 %) at >45° latitude, both reaching sufficiency in winter | 13 RCTs (2005-2016), 532 athletes randomised, 433 with complete data; sufficiency cut-off 30 ng/mL | athletes | MA | Farrokhyar, Sivakumar, Savage, Koziarz, Jamshidi, Ayeni, Peterson & Bhandari 2017, Sports Med, PMID 28577257, doi:10.1007/s40279-017-0749-4 |
| B vitamins and exercise capacity | "Active individuals with **poor or marginal nutritional status for a B-vitamin may have decreased ability to perform exercise at high intensities**." Exercise "may increase the requirements for **riboflavin and vitamin B-6**"; data for folate and B-12 are limited. Thiamin, riboflavin and B-6 serve energy-producing pathways; folate and B-12 serve cell synthesis and repair | narrative review; no pooled effect size, and no dose-response | active individuals and athletes | TXT | Woolf & Manore 2006, Int J Sport Nutr Exerc Metab, PMID 17240780, doi:10.1123/ijsnem.16.5.453 |
| Magnesium and endurance | **No endurance-specific synthesis found.** The nearest verified evidence is that magnesium supplements are "unlikely [to provide] clinically meaningful cramp prophylaxis … at any of the dosages used" (Cochrane, 11 trials, 735 participants) — cited in `science-minerals-fibre-fats.md` § Magnesium to Garrison et al. 2020, doi:10.1002/14651858.CD009402.pub3. Treat any magnesium-to-endurance coefficient as a mod judgement | — | — | — | see Gaps |
| Alcohol and recovery | Acute alcohol at athlete-typical volumes "may negatively alter normal immunoendocrine function, blood flow and protein synthesis so that **recovery from skeletal muscle injury may be impaired**"; rehydration and **glycogen resynthesis** are affected "to a lesser extent". A post-exercise dose of about **0.5 g/kg body weight is unlikely to impact most aspects of recovery** | narrative review; male athletes only; effect depends on timing, dose, recovery time available and injury status | male athletes | TXT | Barnes 2014, Sports Med, PMID 24748461, doi:10.1007/s40279-014-0192-8 |
| Sleep loss and physical performance, pooled | Mean **%Δ = −7.56 %** (95 % CI −11.9 to −3.13, p = 0.001, I² = 98.1 %), **significant for every exercise category** (anaerobic power, speed/power endurance, HIIE, strength, endurance, strength-endurance, skill) | 227 outcome measures from 69 publications; n = 959 (89 %) male; sleep loss defined as ≤6 h in any 24 h vs >6 h control. **I² = 98.1 %** — the pooled mean hides enormous heterogeneity | mostly male athletes and active adults | MA | Craven, McCartney, Desbrow, Sabapathy, Bellinger, Roberts & Irwin 2022, Sports Med, PMID 35708888, doi:10.1007/s40279-022-01706-y |
| Sleep loss, the usable dose-response | **≈0.4 % performance decrease for every hour awake before exercise**, for deprivation and late-restriction protocols. Only **deprivation and late restriction** (waking earlier than normal) produced consistent negative effects — *early* restriction (delayed sleep onset) did not. Tasks performed in the **PM were consistently impaired while AM tasks were largely unaffected** | the time-awake slope is the single most directly implementable number in this section | as above | MA | Craven 2022 (as above) |
| Sleep loss, mechanism and caveat | "Research indicates **some maximal physical efforts and gross motor performances can be maintained**", while "the few published studies investigating the effect of sleep loss on performance **in athletes** report a reduction in **sport-specific** performance"; effects on physiological responses are "equivocal", but reduced sleep quality and quantity "could result in an **autonomic nervous system imbalance, simulating symptoms of the overtraining syndrome**", and pro-inflammatory cytokines rise. Cognitive performance is consistently "slower and less accurate" | narrative review; the authors' own conclusion is that the extent and mechanism "remain uncertain" | athletes | TXT | Fullagar, Skorski, Duffield, Hammes, Coutts & Meyer 2015, Sports Med, PMID 25315456, doi:10.1007/s40279-014-0260-0 |

**Interpretation.** Only two substances here deserve a first-class place in an endurance model, and they pull in
opposite directions. **Caffeine** is a genuine, small, fast ergogenic: about **+3 % power and +2 % time-trial**
at 3-6 mg/kg (Southward), bigger for aerobic than anaerobic work (Grgic), and — importantly for a mod that
already tracks intake — **it tolerates out completely in four weeks of daily use** (Beaumont), with the
tolerance living in the response, not the plasma level. That is a ready-made game loop: coffee helps, daily
coffee stops helping, and a few days off restores it. **Sleep loss** is the largest single non-nutritional
penalty in the whole note: pooled **−7.6 %** across every category of physical performance, with a clean
**≈0.4 % per hour awake** slope (Craven) — but read the I² of 98.1 % as a warning that the pooled mean is a
centre of mass, not a constant, and note that only *deprivation* and *early waking* hurt, not late bedtimes,
and that afternoon performance suffers while morning performance mostly does not. **Protein** earns a modest
place: time to exhaustion improves (SMD 0.45) while VO₂max does not (Xiao), which is exactly the "endurance
without capacity" pattern the mod should express through the recovery term rather than the capacity term.
**Vitamin D** should be explicitly *neutral* for endurance in this mod — seven RCTs measured performance and
none found an effect (Farrokhyar) — even though the design has other, defensible reasons to model vitamin D
(respiratory infection risk, § 4.5). **B vitamins** have a mechanism and a plausible direction ("decreased
ability to perform exercise at high intensities" at marginal status) but no effect size, so they belong in the
model as a threshold effect at *deficient* grades only, never as a graded multiplier. **Magnesium** has no
endurance evidence I could verify and should carry no endurance coefficient. **Alcohol's** endurance cost is
indirect and belongs on recovery, glycogen resynthesis and the sleep channel — with a real threshold at
**~0.5 g/kg**, below which the evidence says most of recovery is unaffected.

## 6. Body composition

`science-energy-body.md` § 9 already covers the mortality curve, walking economy per kilogram (Browning: net
metabolic rate per kg is 0-6 % *lower* in obese adults, i.e. per-kg economy is not impaired) and fat as
insulation. This section adds the endurance-specific experiments.

| parameter | value / equation | range or uncertainty | population | grade | citation |
|---|---|---|---|---|---|
| **The load-carriage coefficient for excess mass** | Each **+5 % of body mass added to the trunk** cost, on average, **−2.4 mL·kg⁻¹·min⁻¹ of VO₂max expressed per kg total weight, −35 s of treadmill run time and −89 m of 12-min run distance**. Added weight did *not* systematically change VO₂max in L·min⁻¹ or per kg fat-free weight. "These decreases were a direct consequence of the increased energy cost of running at submaximal speeds" | n = 6, within-subject, four conditions (0, +5, +10, +15 % added weight); the effect was systematic and significant across conditions, so linear interpolation over 0-15 % is defensible | 6 subjects, treadmill + 12-min run | RCT (within-subject crossover) | Cureton, Sparling, Evans, Johnson, Kong & Purvis 1978, Med Sci Sports, PMID 723510 (no DOI assigned; Europe PMC record verified) |
| Excess fat explains a large share of a real performance gap | Adding external trunk weight to men until their % excess weight matched a matched woman's % body fat (**+7.5 % on average**) closed **32 % of the sex difference in treadmill run time (1.3 min)** and **30 % of the 12-min run gap (173 m)**, via a 38 % reduction in the sex difference in O₂ per kg FFM at submaximal speeds and a 65 % reduction in the VO₂max-per-total-weight gap | n = 10 F + 10 M regular distance runners | trained distance runners | RCT (within-subject added weight) | Cureton & Sparling 1980, Med Sci Sports Exerc, PMID 7421479, doi:10.1249/00005768-198024000-00011 |
| Fat mass does not reduce *capacity*, only capacity *per kilogram* | **FFM was the strongest determinant of VO₂max (r = 0.87, p < 0.0001)**; after adjusting for FFM, fat mass had no significant influence. Obese vs lean: absolute VO₂max **higher** (1.56 ± 0.40 vs 1.24 ± 0.27 L·min⁻¹), per body weight **much lower (32.0 ± 4.1 vs 44.2 ± 3.2 mL·kg⁻¹·min⁻¹)**, per FFM **no difference (59.2 ± 4.9 vs 57.9 ± 5.8 mL·kg FFM⁻¹·min⁻¹)**. Sub-maximal capacity was significantly worse in the obese (higher HR and higher % VO₂max at a given workload) | Study 1: 129 children across a wide body-composition spectrum, DXA; Study 2: 31 overweight women before/after weight loss, 4-compartment model. **Children, not adults** — the cleanest statement of the principle, in the wrong population | COH (cross-sectional + before/after) | Goran, Fields, Hunter, Herd & Weinsier 2000, Int J Obes, PMID 10918530, doi:10.1038/sj.ijo.0801241 |
| Fat and heat tolerance, mass and heat production controlled | At a **fixed absolute heat production (550 W)** in mass-matched pairs, high-body-fat men had a **greater rise in rectal temperature over 60 min (0.87 ± 0.18 vs 0.66 ± 0.21 °C, p = 0.02)** while sweat rate, whole-body sweat loss and net heat loss were statistically identical — so the same heat load raises core temperature more in a fatter body. When intensity was instead set per kg **lean** mass (7.5 W/kg LBM), the lean group got hotter, because the absolute heat load was then higher | n = 9 + 9; 88.7 ± 8.4 vs 90.1 ± 7.9 kg total mass (p = 0.72) with 10.8 ± 3.6 % vs 32.0 ± 5.6 % body fat; 60 min cycling at 28.1 °C, 26 % RH. Proposed mechanism: lower mean specific heat capacity or impaired subcutaneous heat conduction | RCT (matched-pair crossover) | Dervis, Coombs, Chaseling, Filingeri, Smoljanic & Jay 2016, J Appl Physiol, PMID 26702025, doi:10.1152/japplphysiol.00906.2015 |
| Low lean mass and endurance | **No direct endurance synthesis found.** The evidenced statement is the inverse of the Goran result: because VO₂max scales with FFM (r = 0.87) and is independent of FM once FFM is held, **losing lean mass lowers absolute aerobic capacity roughly in proportion**, while losing fat mass raises capacity per kilogram without changing it absolutely. Any coefficient on low lean mass beyond that proportionality is a mod judgement | — | — | — (derived from Goran 2000) | see Gaps |

**Interpretation.** Body composition acts on endurance through **two separate channels with opposite signs**,
and the Cureton experiments are the rare case of a number a game can use directly. Channel one is **mass
carried**: strapping 5 % of body mass to the trunk cost 2.4 mL·kg⁻¹·min⁻¹ of weight-relative VO₂max, 35 s of
run time and 89 m of 12-minute distance, purely because submaximal running got more expensive (Cureton 1978) —
and since the effect was systematic across 5, 10 and 15 %, a **linear penalty of roughly 0.5 % of endurance
performance per 1 % of excess body mass** is defensible over that range. This is not a special fat mechanic: it
is identical to load carriage, which the design already models via the Pandolf terms, so **the cleanest
implementation is to feed excess fat mass into the same load term as inventory weight** rather than inventing a
separate obesity coefficient. Channel two is **capacity itself**, which fat does *not* reduce: absolute VO₂max
tracks fat-free mass (r = 0.87) and is unchanged per kilogram of FFM in the obese (Goran) — so in the mod, a
character's aerobic *capacity* should scale with **lean** mass and the fat only makes them carry it. Fat's third
effect is thermal and it cuts the other way from insulation: at the *same* heat production in a mass-matched
body, a fat body's core temperature rises **0.2 °C more per hour** with no compensating sweat response
(Dervis) — so vanilla's existing fatness term in the Thermoregulator (which insulates, per the jar reading § E)
is only half the story, and a realism mod has evidence to make fat both warmer in the cold *and* worse in the
heat, which pairs neatly with the hyperthermia multiplier already in the engine's endurance drain. Low lean
mass has no direct endurance literature I could verify; the honest model is proportionality to FFM inherited
from Goran, which the design's existing lean-mass machinery (spec § 4.3) already supplies.

## 7. Engine mapping (speculative)

**Everything in this section is speculative design, not evidence.** Each proposal names the rows above it rests
on; where a number is a game choice with no evidence behind it, it says so. The engine facts come from
`jar-endurance-fatigue-sleep.md` §§ A-F and are cited to that report's own offsets, not re-read here.

### 7.0 Four engine facts that constrain every choice below

| # | Engine fact | Consequence for the model | Source |
|---|---|---|---|
| E1 | **`Hook.CalculateStats` may not actually stop the endurance model.** `IsoGameCharacter.calculateStats @60 L10208` calls `updateEndurance()`, but that resolves to the *base* `IsoGameCharacter.updateEndurance` — three instructions of housekeeping. The real drain-and-regen model is `IsoPlayer.updateEndurance`, a **separate private method** reached from `IsoPlayer.updateInternal2 @938 L2408` and `@2139 L2661`, which the hook does not sit in front of | **Gate before any endurance work.** If this reading holds, takeover mode owns hunger, thirst, fatigue, stress, morale and fitness but **not** endurance, and endurance must be handled overlay-style: let vanilla's updater run, then write the corrected value in the same tick. The kernel formula is unchanged either way; only the adapter differs. Verify with a live run (a `Hook.CalculateStats` handler that returns while a character sprints — does endurance still fall?) before building the adapter | `jar-endurance-fatigue-sleep.md` §§ B, C |
| E2 | **Endurance carries no `deltaMinutesPerDay`.** Unlike hunger, thirst and fatigue, every arm of `updateEndurance` is `GameTime.getMultiplier()` only | Per-tick endurance rates must stay day-length-invariant to match vanilla, but the **latent capacity variable must integrate in game days**, so the slow clock (not the fast clock) owns it and must read game time, not ticks | § B |
| E3 | **On a server with `SleepAllowed` or `SleepNeeded` false, `Stats.reset(FATIGUE)` fires every tick, *before* the Lua hook.** Fatigue is pinned at 0 and unreachable | Vanilla's `(1 − 0.85·fatigue)` regen gate is dead on such servers, and so is any sleep effect routed through the FATIGUE stat. **Sleep debt must live in the mod's own modData**, with the fatigue stat treated as a display mirror that may be wiped | § C |
| E4 | Endurance is `ORDERED_STATS[3]` and rides the 1 Hz full snapshot, so a client write is erased; the `ENDURANCE` moodle costs 0.15 of base speed and 0.07 of combat speed **per level** and each side recomputes its own moodles from its own stats copy; `IsoGameCharacter.exert(float)` is `public` and Lua-callable; item scripts' `EnduranceChange` is set by **no vanilla item** | All writes server-side, and the speed and combat consequences arrive on the client for free once the snapshot lands — **no packet work for the movement penalty**. `exert()` is the seat for event-driven costs (a swing, a fall, a scare). `EnduranceChange` is free space for an immediate food or caffeine credit | §§ A, B, D |

### 7.1 The latent variable: trained aerobic capacity (`TAC`)

One scalar per character, in mod modData, dimensionless, **normalised so that an untrained adult is 1.00**:

```
TAC ∈ [0.80, 1.25]        start 1.00 (an untrained survivor)
```

The bounds come from § 1. The ceiling **+25 %** is the top of the meta-analytic trainable range
(Milanović's +4.9-5.5 mL·kg⁻¹·min⁻¹ on a 40.8 baseline is +12-13 %; Bacon's +0.51 L·min⁻¹ on 3.4 is +15 %;
Hickson's 9-week programme reached +23 %; Bouchard's extraordinary responders reached ~+30 %), so 1.25 is the
"as fit as weeks of hard training can make you" mark and 1.30 would be defensible only as a trait. The floor
**0.80** is the deconditioned end; Ried-Larsen's linear bed-rest decline would reach further, but a survivor
who walks at all never gets there, so the floor is a game choice bounding the exponential below.

**Update, once per game day** (slow clock, on the day boundary):

```
S_vol   = clamp(weekly_minutes_at_intensity_band>=1 / 240, 0, 1)      -- 240 = 40 min x 6 d, Hickson's programme
target  = 1.00 + 0.25 * S_vol
hard_days = count of the last 7 game days with >=10 cumulative minutes in band 2
maintained = (hard_days >= 2)                                          -- Hickson & Rosenkoetter 1981

if target > TAC:   TAC += (target - TAC) / TAU_GAIN * G_nut * dt_days   -- TAU_GAIN = 15 d
elseif not maintained: TAC -= (TAC - 0.80) / TAU_LOSS * dt_days         -- TAU_LOSS = 84 d
-- else: hold
```

Intensity bands, mapped onto engine states the fast clock already distinguishes: **band 0** idle, sitting,
sleeping, walking unloaded; **band 1** running, or walking under heavy load (the engine's own second drain arm);
**band 2** sprinting, dragging a corpse, or sustained melee — plus whatever the design's exercise actions and
Fitness XP events report (spec § 7 assumption 6).

| constant | value | where it comes from |
|---|---|---|
| `TAU_GAIN` | **15 game days** | Hickson 1981's half-time of 10.3-10.8 d: τ = t½/ln 2 ≈ 15. Check: 21 days of full stimulus gives +18.8 % (75 % of the way — "constant after 3 wk"); 63 days gives **+24.6 %**, against Hickson's measured **+23 % at 9 weeks** |
| `TAU_LOSS` | **84 game days** | Chosen so the decay rate *at the ceiling* equals Ried-Larsen's bed-rest figure: (1.25 − 0.80)/84 = 0.00536/d = **0.43 %/day of current value** ✓. And because the rate is proportional to the gap, a modestly trained character at TAC 1.05 loses only 0.28 %/day — which reproduces Ried-Larsen's finding that **pre-bed-rest fitness explained 15-26 % of the variance in the decline** without any extra term |
| ceiling coefficient `0.25` | **+25 %** | § 1, Milanović / Bacon / Hickson / Bouchard, above |
| floor `0.80` | −20 % | game choice bounding the exponential; the evidence (Ried-Larsen) is linear and unbounded over 1-90 days |
| `maintained` rule: **2 hard days in 7, ≥10 min each** | — | Hickson & Rosenkoetter 1981 (2 d/wk at maintained intensity held a 25 % gain for 15 weeks) and Hickson 1985 (a one-third cut in *intensity* lost ground at unchanged frequency and duration). **This asymmetry is the section's single most important design consequence** |
| `S_vol` denominator `240 min/wk` | — | Hickson's 40 min/d × 6 d/wk programme; ACSM's ≥150 min/wk moderate floor sits at S_vol = 0.63, giving target 1.16 |

`G_nut` gates the *gain* only — a malnourished character cannot adapt, but does not lose fitness faster for it
(the evidence is about impaired adaptation, not accelerated decay):

```
G_nut = G_iron * G_protein * min(G_energy, G_sleep)      clamped to (0, 1]
```

| term | value | rests on |
|---|---|---|
| `G_iron` | replete 1.00 · marginal **0.70** · depleted **0.40** · clinical 0.40 | Hinton 2000 and Brownlie 2002: iron-replete arms *adapted faster* to identical training, with the benefit concentrated in the worst-off subjects. The exact split is inference |
| `G_protein` | adequate 1.00 · low **0.85** | Xiao 2025, TTE SMD 0.45, LBM SMD 0.13 (NS) — small, so a small coefficient |
| `G_energy` | EA ≥ 30 kcal·kg LBM⁻¹·d⁻¹ → 1.00 · below → **0.50** | Loucks & Thuma 2003 for the threshold; Vanheest 2014's 9.8 % decline against an 8.2 % improvement over a 12-week season for the magnitude |
| `G_sleep` | debt < 8 h → 1.00 · scaling to **0.70** at severe debt | Fullagar 2015 ("autonomic nervous system imbalance, simulating symptoms of the overtraining syndrome"); the number is inference |
| **`min(G_energy, G_sleep)`, not their product** | — | REDs' 2023 Physiological Model and Fullagar both frame LEA and sleep loss as converging on one syndrome with shared moderators; multiplying them would double-count it. Taking the worse of the two is the honest composition |

### 7.2 Drain and regeneration

The mod supplies **two coefficients per player**, `D_mod` and `R_mod`, rebuilt only when a grade changes (spec
§ 4.5) and multiplied into the vanilla shapes, which stay intact:

```
drain  = base_rate * M_trait * 2.3 * PacingMod(Fitness) * HyperthermiaMod * Asthma * load * sneak * D_mod
regen  = imobile * sandboxRegenMult * RecoveryMod(Fitness, traits) * state_factor * (1 - k*fatigue) * R_mod
```

Keeping vanilla's `PacingMod` and `RecoveryMod` untouched is what honours the design's ruling that the Fitness
perk stays vanilla's (spec § 7 assumption 15). It also sets the scale: vanilla's perk spans 0.90 → 0.43 on drain
and 0.70 → 1.60 on regen, so the mod's whole latent range below is deliberately **smaller than the perk**.

```
D_mod = D_cap * D_glyc * D_hydr * D_heat * D_fat * D_iron * D_sleep * D_caf      capped at 2.50
R_mod = R_cap * R_glyc * R_prot * R_iron * R_hydr * R_sleep * R_alc * R_bal      floored at 0.25
```

| coefficient | formula | at its extremes | rests on |
|---|---|---|---|
| `D_cap` | `TAC^-0.8` | TAC 1.25 → **0.84**; TAC 0.80 → **1.26** | § 1. The sub-unit exponent encodes Hickson's dissociation between VO₂max and endurance performance — capacity gains do not pass through 1:1 |
| `R_cap` | `TAC^1.2` | 1.25 → **1.31**; 0.80 → **0.76** | § 1, and the engine's own design: `getRecoveryMod` is where vanilla already puts the Fitness ladder, so recovery is the right surface for conditioning |
| `D_glyc` | `1 + 0.35*(1-g)^2`, `g` = glycogen fraction of a 460 mmol·kg⁻¹ reference store | g 1.0 → 1.00; 0.5 → **1.09**; 0.0 → **1.35** | Areta & Hopkins 2018 for the 460 reference and the ±100/−250 diet swing; Coyle 1986 for the size — CHO feeding bought +33 % time to fatigue, so 1.35 at empty, *not* the 1.6 a steeper curve would give. The quadratic keeps it flat while the store is comfortable, matching intensity-driven glycogenolysis |
| `R_glyc` | `0.5 + 0.5*g` | g 0 → **0.50** | inference from Coyle (the fed condition sustained CHO oxidation "from sources other than muscle glycogen") and Stellingwerff & Cox's duration relation |
| `D_hydr` | `1 + 0.03*max(0,d-2) + 0.09*max(0,d-4)`, `d` = % body-mass deficit | d 2 → 1.00; 3.6 → **1.05**; 4 → 1.06; 6 → **1.30** | § 4. The kink at 2 % and the steepening at 4 % **is** the design's existing ruling (spec § 7 assumption 11); the slope at 3.6 % reproduces Deshayes' −2.4 % AEP, and the whole shape is licensed by Goulet 2013's fixed-intensity arm (−1.91 % power, ≥2 % threshold) — which is the case a PZ character is in |
| `R_hydr` | `1 - 0.05*max(0,d-2)`, floor 0.70 | d 6 → **0.80** | § 4, same rows; splitting the dehydration penalty across drain and regen keeps either arm from carrying an implausible coefficient |
| `D_heat` | replace vanilla's `getHyperthermiaMod` ladder (1.0 at every level but 4, then 2.0) with **1.00 / 1.10 / 1.25 / 1.50 / 2.00** at hyperthermia moodle levels 0-4, then multiply by `1 + 0.10*(d/4)*(heatLevel/2)` | level 2, d 4 → 1.25 × 1.10 = **1.38** | Montain & Coyle 1992 (strain graded in proportion to the deficit) and Trangmar & González-Alonso 2019 (dehydration raises glycogen reliance; strain preventable by cold environments) for the **multiplicative** interaction. The ladder's four values are inference, but the report calls vanilla's gate "a bug" and a monotone ladder is strictly more defensible than a step at level 4 alone |
| `D_fat` | `1 + 0.008 * excess_mass_percent` | +15 % excess mass → **1.12** | Cureton 1978: +5 % trunk mass cost 35 s of treadmill run time and 89 m of 12-min distance — about 0.5-1.1 % of performance per 1 % of mass, so 0.8 % is the midpoint. **Prefer feeding excess fat mass into the same load term as inventory weight** rather than shipping this as a separate coefficient: Cureton's mechanism is load carriage, which the design already models (spec § 4.3, Pandolf) |
| `D_iron` | replete 1.00 · marginal 1.03 · depleted 1.08 · clinical **1.20** | — | Pasricha 2014: repletion cut the % of VO₂max needed at a fixed workload by **2.68 %** and heart rate by 4 bpm → the marginal and depleted rungs. The 1.20 clinical rung extrapolates Haas & Brownlie's "strong causal effect" for anaemia and is **inference** |
| `R_iron` | replete 1.00 · marginal 0.95 · depleted 0.88 · clinical **0.75** | — | Deliberately **larger than `D_iron`**, because Houston 2018 found repletion cut *fatigue* (SMD −0.38, I² = 0 %) while leaving VO₂max untouched (SMD 0.11) — iron's best-evidenced endurance channel is recovery and perceived effort, not capacity |
| `D_sleep` | `1 + 0.004*max(0, hours_awake - 16)`, cap 1.20 | 30 h awake → **1.06**; 66 h → 1.20 | Craven 2022's **≈0.4 % per hour awake**, which is a slope, directly. Driven by hours awake and the mod's own debt store (E3), *not* by bedtime: Craven found early restriction (late bedtime) harmless and only deprivation and early waking costly |
| `R_sleep` | `1 - 0.01*debt_hours`, floor 0.60 | 20 h debt → **0.80** | Craven 2022 pooled −7.56 %, but with I² = 98.1 %, so the pooled mean licenses the *direction* and a conservative magnitude only |
| `D_caf` | `1 - 0.03 * dose_effect * (1 - tolerance)` | fully effective 3-6 mg/kg dose → **0.97** | Southward 2018 (+3.03 % power). `tolerance` rises with habitual intake and decays over ~4 weeks per Beaumont 2017, which found the benefit *entirely* gone after 28 days of 1.5-3.0 mg·kg⁻¹·d⁻¹ |
| `R_alc` | `1 - 0.15*clamp((g_per_kg - 0.5)/0.5, 0, 1)` | 0.5 g/kg → **1.00** (no penalty); 1.0 g/kg → **0.85** | Barnes 2014: ~0.5 g/kg "is unlikely to impact most aspects of recovery", so the penalty *starts* there and saturates at double that dose; glycogen resynthesis is affected "to a lesser extent" than muscle repair, which is why the coefficient is small |
| `R_bal` | `1.05` while every tracked nutrient sits replete | — | **Game choice**, the design's existing `BalanceBonus` dial (spec § 4.5, § 7 assumption 16). No evidence supports a supra-normal bonus; the label must ship with it |
| `D_mod` cap 2.50 / `R_mod` floor 0.25 | — | — | **Game choice.** A product of seven penalties can reach 3-4×, which no physiology supports and no player would survive; the cap is the statement that no single day is worse than "drains twice as fast, recovers a quarter as fast" |

### 7.3 How the states combine

**Multiplicative, with two named exceptions.** Three arguments for the product form: the evidence for the one
interaction that has been measured is graded and proportional, not additive (Montain & Coyle; Trangmar's
"depends on the functional demand"); the states act through genuinely different bottlenecks (oxygen transport
for iron, substrate for glycogen, plasma volume and thermal strain for hydration, central drive for sleep), and
independent bottlenecks on one flux compose multiplicatively; and **the engine is already a pure product** —
every term in `updateEndurance` is a factor, so a multiplicative mod coefficient composes with vanilla without
redefining any vanilla term. The exceptions:

1. **LEA and sleep debt take the worse of the two, not the product**, on the adaptation gate (§ 7.1) — REDs 2023
   and Fullagar 2015 both treat them as one syndrome with shared moderators, so multiplying double-counts.
2. **The cap and floor** are hard, because an unbounded product is unphysiological (§ 7.2, last row).

A third case worth a ruling rather than a formula: **iron × glycogen** are multiplicative in the model but the
evidence for either at *marginal* grades is weak (Houston's null; Areta's normative spread), so both marginal
rungs are deliberately small (1.03 and 1.09) and the model's teeth are at the depleted and clinical rungs.

### 7.4 What a balanced, hydrated, iron-replete character gets, relative to vanilla

**Exact parity, by construction.** Every coefficient above evaluates to 1.00 at `TAC = 1.00`, full glycogen,
`d < 2 %`, replete iron, no sleep debt, no heat, no excess fat, no caffeine, no alcohol — so a server that
installs the mod and plays a well-fed character sees **vanilla's endurance numbers unchanged**. That is the
right default for three reasons: it makes every deviation legible as a named state rather than a global rebalance;
it keeps the mod's compatibility story honest (spec § 4.9); and it means the acceptance test for the endurance
kernel is "reproduce vanilla bit-close in the replete state", which the design already wants for the takeover
handler (spec § 4.1, § 8).

Around that parity point:

| state | `D_mod` | `R_mod` | reading |
|---|---|---|---|
| Replete, untrained (the parity point) | **1.00** | **1.00** | vanilla |
| Replete, untrained, `BalanceBonus` on | 1.00 | **1.05** | a 5 % recovery credit, labelled a game choice |
| Conditioned (TAC 1.25), replete | **0.84** | **1.31** | worth almost exactly **two vanilla Fitness levels**: the perk's level 0→2 span is drain 0.90→0.75 (−17 %) and regen 0.70→0.90 (+29 %). Its full 0→10 span is −52 % drain and +129 % regen, so the mod's latent variable is deliberately **a fifth of the perk's authority** |
| Deconditioned (TAC 0.80), replete | 1.26 | 0.76 | the cost of a month of sitting in a safehouse |
| Well-fed but 4 % dehydrated in the heat (level 2) | 1.06 × 1.38 = **1.46** | 0.90 | the strongest short-term penalty in the model, and the best-evidenced |
| Glycogen empty, 30 h awake, replete otherwise | 1.35 × 1.06 = **1.43** | 0.50 × 0.80 = **0.40** | the "bonk" — and note recovery is hit harder than drain, which is the right shape for a state that a meal fixes |
| Anaemic, LEA, 5 % dehydrated, glycogen low, 30 h awake, TAC 0.80 | product 2.6 → **capped 2.50** | product 0.19 → **floored 0.25** | worst case: twice the drain, a quarter of the recovery — desperate but survivable, and `TAC` is additionally frozen because `G_nut` ≈ 0.14 |

### 7.5 Fitness perk, XP and the interface

The perk is untouched: `updateFitness` keeps awarding XP from running and exercise, and the takeover handler
must **reproduce it faithfully** rather than modify it (E1's gate applies to whether the handler owns it at all).
That leaves the character with two fitness numbers — a vanilla perk level and the mod's `TAC` — which will
diverge, so the interface (spec § 4.7) should show both, e.g. *Fitness 5 · conditioning 1.12 (rising)*, and the
panel's conditioning line should name the binding constraint when `G_nut < 1` (*"conditioning held back: iron
depleted"*). That single string does more for a player's understanding of the model than any number in it.

## Proposed model

Everything an implementer needs, in one place. The kernel functions are side-free and Kahlua-safe (no `goto`,
no integer format of a float, no `#` on a Java list); all state arrives as a plain table.

### Constants

```lua
-- latent capacity
TAC_MIN        = 0.80     -- game choice (floor on an unbounded exponential)
TAC_MAX        = 1.25     -- MA-anchored: +25 % trainable range
TAC_START      = 1.00     -- an untrained adult, = vanilla parity
TAU_GAIN_DAYS  = 15.0     -- Hickson 1981 t-half 10.3-10.8 d
TAU_LOSS_DAYS  = 84.0     -- calibrated to Ried-Larsen -0.43 %/d at the ceiling
VOL_WEEK_FULL  = 240.0    -- minutes/week at band >= 1 for a full stimulus (40 min x 6 d)
HARD_DAY_MIN   = 10.0     -- minutes in band 2 that make a day "hard"
HARD_DAYS_KEEP = 2        -- hard days per 7 that suspend decay  (Hickson & Rosenkoetter 1981)

-- drain / regen exponents and coefficients
CAP_DRAIN_EXP  = -0.8 ;  CAP_REGEN_EXP  = 1.2
GLYC_DRAIN_K   = 0.35 ;  GLYC_REGEN_FLOOR = 0.50
HYDR_D_K1      = 0.03 ;  HYDR_D_K2      = 0.09 ;  HYDR_D_T1 = 2.0 ; HYDR_D_T2 = 4.0
HYDR_R_K       = 0.05 ;  HYDR_R_FLOOR   = 0.70
HEAT_LADDER    = {1.00, 1.10, 1.25, 1.50, 2.00}     -- hyperthermia moodle levels 0..4
HEAT_HYDR_K    = 0.10
FAT_LOAD_K     = 0.008   -- per 1 % excess body mass (Cureton 1978)
IRON_DRAIN     = {1.00, 1.03, 1.08, 1.20}           -- replete, marginal, depleted, clinical
IRON_REGEN     = {1.00, 0.95, 0.88, 0.75}
SLEEP_D_K      = 0.004 ; SLEEP_D_T = 16.0 ; SLEEP_D_CAP = 1.20   -- Craven 2022, 0.4 %/h awake
SLEEP_R_K      = 0.01  ; SLEEP_R_FLOOR = 0.60
CAF_K          = 0.03  ; CAF_TOLERANCE_DAYS = 28   -- Southward 2018 ; Beaumont 2017
ALC_THRESHOLD  = 0.5   ; ALC_K = 0.15              -- g/kg, Barnes 2014
BALANCE_BONUS  = 1.05                               -- GAME CHOICE, dial, default on
D_MOD_CAP      = 2.50 ; R_MOD_FLOOR = 0.25          -- GAME CHOICE
EA_THRESHOLD   = 30.0  -- kcal / kg lean mass / day (Loucks & Thuma 2003)
GLYC_REF_MMOL  = 460.0 -- mmol/kg dry muscle, normal-CHO reference (Areta & Hopkins 2018)
```

### Equations

```
-- once per game day, slow clock
S_vol      = clamp(week_minutes_band1plus / VOL_WEEK_FULL, 0, 1)
target     = 1.00 + (TAC_MAX - 1.00) * S_vol
maintained = (hard_days_in_last_7 >= HARD_DAYS_KEEP)
G_nut      = G_iron * G_protein * min(G_energy, G_sleep)
if target > TAC then
   TAC = TAC + (target - TAC) / TAU_GAIN_DAYS * G_nut * dt_days
elseif not maintained then
   TAC = TAC - (TAC - TAC_MIN) / TAU_LOSS_DAYS * dt_days
end
TAC = clamp(TAC, TAC_MIN, TAC_MAX)

-- on any grade change, slow clock; read per tick by the fast clock
D_mod = min(D_MOD_CAP,
            TAC^CAP_DRAIN_EXP
          * (1 + GLYC_DRAIN_K*(1-g)^2)
          * (1 + HYDR_D_K1*max(0,d-HYDR_D_T1) + HYDR_D_K2*max(0,d-HYDR_D_T2))
          * HEAT_LADDER[heat+1] * (1 + HEAT_HYDR_K*(d/4)*(heat/2))
          * (1 + FAT_LOAD_K*excess_pct)
          * IRON_DRAIN[iron_grade]
          * min(SLEEP_D_CAP, 1 + SLEEP_D_K*max(0, hours_awake - SLEEP_D_T))
          * (1 - CAF_K*caf_dose_effect*(1-caf_tolerance)))
R_mod = max(R_MOD_FLOOR,
            TAC^CAP_REGEN_EXP
          * (GLYC_REGEN_FLOOR + (1-GLYC_REGEN_FLOOR)*g)
          * prot_factor
          * IRON_REGEN[iron_grade]
          * max(HYDR_R_FLOOR, 1 - HYDR_R_K*max(0,d-HYDR_D_T1))
          * max(SLEEP_R_FLOOR, 1 - SLEEP_R_K*debt_hours)
          * (1 - ALC_K*clamp((g_per_kg - ALC_THRESHOLD)/ALC_THRESHOLD, 0, 1))
          * balance_bonus)

-- applied in the vanilla shapes, which are not otherwise touched
drain = base_rate * M_trait * 2.3 * PacingMod(Fitness) * Asthma * load * sneak * D_mod
regen = imobile * sandboxRegenMult * RecoveryMod(Fitness, traits) * state_factor * (1 - k*fatigue) * R_mod
```

Note that `D_mod` **absorbs** vanilla's `getHyperthermiaMod`, which is therefore dropped from the drain line —
the engine's own version returns 1.0 at hyperthermia levels 1-3 and 2.0 only at level 4, which the jar report
reads as a gate bug; the ladder above replaces it monotonically.

### Register rows to mint (science register)

Nineteen rows, one per number the mod would ship from this note. Ids are the controller's to assign from a
reserved block (spec § 4 rule 2); `status` is `active` unless marked. Source report for all of them:
`wave2-science-endurance-fitness.md`.

| parameter | value | grade | citation |
|---|---|---|---|
| VO₂max gain, continuous endurance training vs control | +4.9 mL·kg⁻¹·min⁻¹ (±1.4) | MA | Milanović 2015, doi:10.1007/s40279-015-0365-0 |
| VO₂max gain, HIIT vs control | +5.5 mL·kg⁻¹·min⁻¹ (±1.2) | MA | Milanović 2015, as above |
| VO₂max gain, interval training, absolute | +0.51 L·min⁻¹ (95 % CI 0.43-0.60) | MA | Bacon 2013, doi:10.1371/journal.pone.0073182 |
| Intensity dose-response for VO₂max | null (Q₄ = 1.36, p = 0.85, R² = 0.05) | MA | Scribbans 2016, doi:10.70252/hhbr9374 |
| Time course of VO₂max adaptation | t½ = 10.3-10.8 d; plateau ~3 wk; +23 % at 9 wk | RCT | Hickson 1981, doi:10.1249/00005768-198101000-00012 |
| Frequency needed to *maintain* a gain | 2 d/wk at maintained intensity, 15 wk | RCT | Hickson & Rosenkoetter 1981, doi:10.1249/00005768-198101000-00011 |
| Duration needed to maintain a gain | 13-26 min/d holds VO₂max; 13 min loses 10 % of ≥2 h endurance | RCT | Hickson 1982, doi:10.1152/jappl.1982.53.1.225 |
| Intensity cut loses the gain | ⅓ cut loses VO₂max and 21 % of long endurance; ⅔ cut loses 30 % | RCT | Hickson 1985, doi:10.1152/jappl.1985.58.2.492 |
| Detraining, VO₂max, short vs long cessation | ES −0.62 (<4 wk) vs −1.42 (>4 wk), Q = 6.5, p = 0.01 | MA | Zheng 2022, doi:10.1155/2022/2130993 |
| Bed-rest VO₂max decline | −0.30 %/d (L·min⁻¹), −0.43 %/d (per kg); 15-26 % of variance from baseline fitness | MA | Ried-Larsen 2017, doi:10.1152/japplphysiol.00415.2017 |
| Trainability spread and heritability | mean ≈+400 mL·min⁻¹, range ~0 to >1.0 L·min⁻¹, h² ≈ 47 % | COH | Bouchard 1999, doi:10.1152/jappl.1999.87.3.1003 |
| Resting muscle glycogen, normative and diet swing | 462 ± 132 mmol·kg⁻¹; +102 high CHO, −253 low | MA | Areta & Hopkins 2018, doi:10.1007/s40279-018-0941-1 |
| Glycogen depletion rate and hypoglycaemic fatigue | 51.5 mmol·kg⁻¹·h⁻¹ at 71 % VO₂max; fatigue at 3.02 h, glucose 2.5 mM; CHO feeding +33 % | RCT | Coyle 1986, doi:10.1152/jappl.1986.61.1.165 |
| Ketogenic diet and endurance | pooled null on VO₂max/TTE/RPE; economy worsens; >80 % VO₂max impaired | MA + RCT | Cao 2021, doi:10.3390/nu13082896; Burke 2017, doi:10.1113/JP273230 |
| Low-energy-availability threshold | 30 kcal·kg LBM⁻¹·d⁻¹ | RCT | Loucks & Thuma 2003, doi:10.1210/jc.2002-020369 |
| Iron repletion, VO₂max and submaximal cost | +2.35 mL·kg⁻¹·min⁻¹; −4.05 bpm; −2.68 % of VO₂max at fixed load | MA | Pasricha 2014, doi:10.3945/jn.113.189589 |
| Iron, fatigue vs capacity split | fatigue SMD −0.38, VO₂max SMD 0.11 (NS) in IDNA adults; VO₂max g = 0.61 in IDNA athletes | MA | Houston 2018, doi:10.1136/bmjopen-2017-019240; Burden 2015, doi:10.1136/bjsports-2014-093624 |
| Dehydration, fixed-intensity vs self-paced | −1.91 ± 1.53 % power clamped (≥2 % BM, p = 0.03) vs +0.09 ± 2.60 % self-paced | MA | Goulet 2013, doi:10.1136/bjsports-2012-090958 |
| Pre-exercise hypohydration | AEP −2.4 %, VO₂peak −2.4 %, VO₂ at LT −4.4 % at 3.6 % BM deficit | MA | Deshayes 2020, doi:10.1007/s40279-019-01223-5 |
| Hypohydration, muscle endurance and strength | −8.3 ± 2.3 % and −5.5 ± 1.0 %, dose-independent | MA | Savoie 2015, doi:10.1007/s40279-015-0349-0 |
| Fat × heat, mass and heat production matched | ΔT_re 0.87 vs 0.66 °C over 60 min (p = 0.02) | RCT | Dervis 2016, doi:10.1152/japplphysiol.00906.2015 |
| Excess mass and running performance | +5 % mass → −2.4 mL·kg⁻¹·min⁻¹, −35 s run time, −89 m 12-min distance | RCT | Cureton 1978, PMID 723510 |
| Capacity scales with FFM, not FM | FFM r = 0.87 with VO₂max; per-FFM VO₂max identical in obese vs lean | COH | Goran 2000, doi:10.1038/sj.ijo.0801241 |
| Caffeine and endurance | +3.03 % power, +2.22 % time trial at 3-6 mg/kg | MA | Southward 2018, doi:10.1007/s40279-018-0939-8 |
| Caffeine tolerance | benefit fully lost after 28 d of 1.5-3.0 mg·kg⁻¹·d⁻¹ | RCT | Beaumont 2017, doi:10.1080/02640414.2016.1241421 |
| Protein and endurance | TTE SMD 0.45 (0.15-0.76); VO₂max NS | MA | Xiao 2025, doi:10.3389/fnut.2025.1663860 |
| Vitamin D and performance | no significant effect in any of 7 measuring RCTs | MA | Farrokhyar 2017, doi:10.1007/s40279-017-0749-4 |
| Sleep loss and performance | pooled −7.56 %; **≈0.4 % per hour awake** | MA | Craven 2022, doi:10.1007/s40279-022-01706-y |
| Alcohol and recovery threshold | ~0.5 g/kg unlikely to impair most of recovery | TXT | Barnes 2014, doi:10.1007/s40279-014-0192-8 |

### Game choices, listed for the re-review

Each of these is a decision with no evidence behind it, in the spec § 7 sense; every one is open at review.

1. `TAC` bounds 0.80-1.25 and the parity point at 1.00 (the ceiling is MA-anchored; the **floor** is a choice).
2. `TAU_LOSS = 84 d` — calibrated to Ried-Larsen *given* the 0.80 floor, so it moves if the floor moves.
3. The three-band intensity classification and which engine states fall in which band.
4. `D_mod` cap 2.50 and `R_mod` floor 0.25.
5. The exponents −0.8 and +1.2 on `TAC` (their *sum* is what sets how much conditioning is worth; the split
   between drain and regen is a choice, weighted toward regen because that is where vanilla puts Fitness).
6. Replacing `getHyperthermiaMod`'s ladder — defensible (the jar report calls the vanilla gate a bug) but a change.
7. `BALANCE_BONUS = 1.05`, on by default (already an approved dial, restated).
8. Splitting each state's penalty across drain and regen rather than putting it all on one.
9. Iron's clinical rungs (1.20 / 0.75) — extrapolations beyond the measured marginal and depleted rungs.
10. `min(G_energy, G_sleep)` instead of their product.
11. Showing both the perk level and `TAC` in the panel, with a named binding constraint.
12. Feeding excess fat mass into the load term instead of a standalone `D_fat` (recommended, but a change to § 4.3).

## Gaps

**Unverified or absent numbers — none of these may ship.**

1. **Haemoglobin response rate to oral iron.** The commonly quoted "~1 g/dL per 2-3 weeks" matched no record I
   fetched; the BSG guideline's abstract (PMID 34497146) carries no rate and its full text was not retrieved.
   The mod's iron repletion time constant therefore rests on the *functional* evidence (6 weeks changed the
   training response; ferritin gains largely banked within ~80 days), not on a haematological rate.
2. **Magnesium and endurance.** No endurance-specific synthesis found at all. Any magnesium-to-endurance
   coefficient would be invention. The nearest verified evidence is negative (magnesium does not prevent cramps).
3. **B-vitamin effect sizes.** Woolf & Manore give direction and mechanism ("decreased ability to perform
   exercise at high intensities" at marginal status) but no magnitude and no dose-response, so B vitamins can
   only be a threshold effect at *deficient* grades, never a graded multiplier.
4. **Low lean mass and endurance, directly.** Nothing measured; the model inherits proportionality to fat-free
   mass from Goran 2000's r = 0.87 and nothing more.
5. **Acute fasting and *aerobic* endurance.** The Ramadan meta-analysis is the best available and it is
   confounded by daytime fluid restriction and circadian shift, and it found aerobic performance *unaffected*.
   No clean "N hours fasted costs X % of endurance capacity" number exists in what I verified. The mod's acute
   fasting penalty must therefore route through glycogen and hypoglycaemia (Coyle), not through a fasting term.
6. **The hyperthermia ladder's four values** (1.10 / 1.25 / 1.50 / 2.00) are inference; the evidence establishes
   that the interaction is graded and multiplicative (Montain & Coyle; Trangmar), not the rungs.
7. **`TAC` exponents.** Nothing in the literature partitions a fitness gain between "drains slower" and
   "recovers faster"; −0.8 / +1.2 is a modelling choice informed only by where vanilla puts its own Fitness
   ladders.
8. **Trainability variance is not modelled.** Bouchard's 47 % heritability and the ~0-to-1.0 L·min⁻¹ response
   range are real and large; a single-track `TAC` silently picks the population mean. A per-character
   trainability multiplier drawn at creation would be more honest, and is proposed nowhere above because it
   interacts with the design's trait system, which is out of this note's scope.
9. **Everything is laboratory-clean.** No study cited here measured anyone doing weeks of manual labour on
   scavenged food while frightened. The population cells say so; the transfer is the mod's assumption, not the
   literature's.
10. **`science-energy-body.md`'s dehydration row needs softening.** That report states, from Cheuvront &
    Kenefick, that strength and power penalties from dehydration are "explicitly unsupported". Savoie et al.
    2015 — with Cheuvront and Kenefick among its authors — pooled **−8.3 % muscle endurance and −5.5 %
    strength**. The two are reconcilable (dose-independence, active-vs-passive confound) but the flat
    "unsupported" line should not be carried into a claim.
11. **EFSA water adequate intakes** remain unverified from the earlier report (403 on every route) and are not
    used here.

**Engine gates, not science gaps** — carried forward for the plan that owns endurance:

- **E1 is the big one:** whether `Hook.CalculateStats` stops `IsoPlayer.updateEndurance` at all. The jar reading
  says it does not (two separate private methods, reached from `calculateStats` and `updateInternal2`
  respectively), which would mean endurance needs overlay handling even in takeover mode. Measure it live before
  building the adapter.
- Whether the `ENDURANCE` moodle's speed penalty really arrives client-side from a server-only stat write
  (the jar reading says each side recomputes its own moodles; it has not been measured).
- The fatigue pin on a sleep-disabled server (E3) makes the mod's sleep-debt store mandatory; confirm the
  server-option gate on the fixture's sandbox values.
- Whether `EnduranceChange` on a script item actually reaches the client through the post-`Eat`
  `SyncPlayerStatsPacket` (the mask includes endurance, per the jar reading, but no vanilla item sets the field,
  so the path has never run).

## Bibliography

Every entry below was verified by fetching its Europe PMC record (`/europepmc/webservices/rest/search?query=DOI:<doi>`
or `EXT_ID:<pmid>`, `resultType=core`) on 2026-09-27 and matching title, authors, journal and year against the
citation as written. Alphabetical by first author.

1. Abaïdia AE, Daab W, Bouzid MA. Effects of Ramadan Fasting on Physical Performance: A Systematic Review with Meta-analysis. *Sports Med* 2020. PMID 31960369, doi:10.1007/s40279-020-01257-0
2. Areta JL, Hopkins WG. Skeletal Muscle Glycogen Content at Rest and During Endurance Exercise in Humans: A Meta-Analysis. *Sports Med* 2018. PMID 29923148, doi:10.1007/s40279-018-0941-1
3. Bacon AP, Carter RE, Ogle EA, Joyner MJ. VO2max trainability and high intensity interval training in humans: a meta-analysis. *PLoS One* 2013. PMID 24066036, doi:10.1371/journal.pone.0073182
4. Barnes MJ. Alcohol: impact on sports performance and recovery in male athletes. *Sports Med* 2014. PMID 24748461, doi:10.1007/s40279-014-0192-8
5. Beaumont R, Cordery P, Funnell M, Mears S, James L, Watson P. Chronic ingestion of a low dose of caffeine induces tolerance to the performance benefits of caffeine. *J Sports Sci* 2017. PMID 27762662, doi:10.1080/02640414.2016.1241421
6. Bouchard C, An P, Rice T, Skinner JS, Wilmore JH, Gagnon J, Pérusse L, Leon AS, Rao DC. Familial aggregation of VO₂max response to exercise training: results from the HERITAGE Family Study. *J Appl Physiol* 1999. PMID 10484570, doi:10.1152/jappl.1999.87.3.1003
7. Brownlie T, Utermohlen V, Hinton PS, Giordano C, Haas JD. Marginal iron deficiency without anemia impairs aerobic adaptation among previously untrained women. *Am J Clin Nutr* 2002. PMID 11916761, doi:10.1093/ajcn/75.4.734
8. Burden RJ, Morton K, Richards T, Whyte GP, Pedlar CR. Is iron treatment beneficial in iron-deficient but non-anaemic (IDNA) endurance athletes? A systematic review and meta-analysis. *Br J Sports Med* 2015. PMID 25361786, doi:10.1136/bjsports-2014-093624
9. Burke LM. Ketogenic low-CHO, high-fat diet: the future of elite endurance sport? *J Physiol* 2021. PMID 32358802, doi:10.1113/JP278928
10. Burke LM, Ross ML, Garvican-Lewis LA, Welvaert M, Heikura IA, Forbes SG, Mirtschin JG, Cato LE, Strobel N, Sharma AP, Hawley JA. Low carbohydrate, high fat diet impairs exercise economy and negates the performance benefit from intensified training in elite race walkers. *J Physiol* 2017. PMID 28012184, doi:10.1113/JP273230
11. Cao J, Lei S, Wang X, Cheng S. The Effect of a Ketogenic Low-Carbohydrate, High-Fat Diet on Aerobic Capacity and Exercise Performance in Endurance Athletes: A Systematic Review and Meta-Analysis. *Nutrients* 2021. PMID 34445057, doi:10.3390/nu13082896
12. Cheuvront SN, Kenefick RW. Dehydration: physiology, assessment, and performance effects. *Compr Physiol* 2014. PMID 24692140, doi:10.1002/cphy.c130017
13. Coyle EF, Coggan AR, Hemmert MK, Ivy JL. Muscle glycogen utilization during prolonged strenuous exercise when fed carbohydrate. *J Appl Physiol* 1986. PMID 3525502, doi:10.1152/jappl.1986.61.1.165
14. Craven J, McCartney D, Desbrow B, Sabapathy S, Bellinger P, Roberts L, Irwin C. Effects of Acute Sleep Loss on Physical Performance: A Systematic and Meta-Analytical Review. *Sports Med* 2022. PMID 35708888, doi:10.1007/s40279-022-01706-y
15. Cureton KJ, Sparling PB. Distance running performance and metabolic responses to running in men and women with excess weight experimentally equated. *Med Sci Sports Exerc* 1980. PMID 7421479, doi:10.1249/00005768-198024000-00011
16. Cureton KJ, Sparling PB, Evans BW, Johnson SM, Kong UD, Purvis JW. Effect of experimental alterations in excess weight on aerobic capacity and distance running performance. *Med Sci Sports* 1978. PMID 723510 (no DOI assigned)
17. Dervis S, Coombs GB, Chaseling GK, Filingeri D, Smoljanic J, Jay O. A comparison of thermoregulatory responses to exercise between mass-matched groups with large differences in body fat. *J Appl Physiol* 2016. PMID 26702025, doi:10.1152/japplphysiol.00906.2015
18. Deshayes TA, Jeker D, Goulet EDB. Impact of Pre-exercise Hypohydration on Aerobic Exercise Performance, Peak Oxygen Consumption and Oxygen Consumption at Lactate Threshold: A Systematic Review with Meta-analysis. *Sports Med* 2020. PMID 31728846, doi:10.1007/s40279-019-01223-5
19. Farrokhyar F, Sivakumar G, Savage K, Koziarz A, Jamshidi S, Ayeni OR, Peterson D, Bhandari M. Effects of Vitamin D Supplementation on Serum 25-Hydroxyvitamin D Concentrations and Physical Performance in Athletes: A Systematic Review and Meta-analysis of Randomized Controlled Trials. *Sports Med* 2017. PMID 28577257, doi:10.1007/s40279-017-0749-4
20. Fullagar HH, Skorski S, Duffield R, Hammes D, Coutts AJ, Meyer T. Sleep and athletic performance: the effects of sleep loss on exercise performance, and physiological and cognitive responses to exercise. *Sports Med* 2015. PMID 25315456, doi:10.1007/s40279-014-0260-0
21. Garber CE, Blissmer B, Deschenes MR, Franklin BA, Lamonte MJ, Lee IM, Nieman DC, Swain DP; American College of Sports Medicine. ACSM position stand: Quantity and quality of exercise for developing and maintaining cardiorespiratory, musculoskeletal, and neuromotor fitness in apparently healthy adults. *Med Sci Sports Exerc* 2011. PMID 21694556, doi:10.1249/mss.0b013e318213fefb
22. Goran M, Fields DA, Hunter GR, Herd SL, Weinsier RL. Total body fat does not influence maximal aerobic capacity. *Int J Obes Relat Metab Disord* 2000. PMID 10918530, doi:10.1038/sj.ijo.0801241
23. Goulet ED. Effect of exercise-induced dehydration on time-trial exercise performance: a meta-analysis. *Br J Sports Med* 2011. PMID 21454440, doi:10.1136/bjsm.2010.077966
24. Goulet ED. Effect of exercise-induced dehydration on endurance performance: evaluating the impact of exercise protocols on outcomes using a meta-analytic procedure. *Br J Sports Med* 2013. PMID 22763119, doi:10.1136/bjsports-2012-090958
25. Grgic J, Grgic I, Pickering C, Schoenfeld BJ, Bishop DJ, Pedisic Z. Wake up and smell the coffee: caffeine supplementation and exercise performance — an umbrella review of 21 published meta-analyses. *Br J Sports Med* 2020. PMID 30926628, doi:10.1136/bjsports-2018-100278
26. Haas JD, Brownlie T. Iron deficiency and reduced work capacity: a critical review of the research to determine a causal relationship. *J Nutr* 2001. PMID 11160598, doi:10.1093/jn/131.2.676S
27. Hew-Butler T, Rosner MH, Fowkes-Godek S, Dugas JP, Hoffman MD, Lewis DP, Maughan RJ, Miller KC, Montain SJ, Rehrer NJ, Roberts WO, Rogers IR, Siegel AJ, Stuempfle KJ, Winger JM, Verbalis JG. Statement of the Third International Exercise-Associated Hyponatremia Consensus Development Conference, Carlsbad, California, 2015. *Clin J Sport Med* 2015. PMID 26102445, doi:10.1097/JSM.0000000000000221
28. Hickson RC, Foster C, Pollock ML, Galassi TM, Rich S. Reduced training intensities and loss of aerobic power, endurance, and cardiac growth. *J Appl Physiol* 1985. PMID 3156841, doi:10.1152/jappl.1985.58.2.492
29. Hickson RC, Hagberg JM, Ehsani AA, Holloszy JO. Time course of the adaptive responses of aerobic power and heart rate to training. *Med Sci Sports Exerc* 1981. PMID 7219130, doi:10.1249/00005768-198101000-00012
30. Hickson RC, Kanakis C, Davis JR, Moore AM, Rich S. Reduced training duration effects on aerobic power, endurance, and cardiac growth. *J Appl Physiol* 1982. PMID 6214534, doi:10.1152/jappl.1982.53.1.225
31. Hickson RC, Rosenkoetter MA. Reduced training frequencies and maintenance of increased aerobic power. *Med Sci Sports Exerc* 1981. PMID 7219129, doi:10.1249/00005768-198101000-00011
32. Hinton PS, Giordano C, Brownlie T, Haas JD. Iron supplementation improves endurance after training in iron-depleted, nonanemic women. *J Appl Physiol* 2000. PMID 10710409, doi:10.1152/jappl.2000.88.3.1103
33. Houston BL, Hurrie D, Graham J, Perija B, Rimmer E, Rabbani R, Bernstein CN, Turgeon AF, Fergusson DA, Houston DS, Abou-Setta AM, Zarychanski R. Efficacy of iron supplementation on fatigue and physical capacity in non-anaemic iron-deficient adults: a systematic review of randomised controlled trials. *BMJ Open* 2018. PMID 29626044, doi:10.1136/bmjopen-2017-019240
34. Li D, Zhou F, Li X, Shibo K, Wang J, Feng X, Wu J. Comparative and dose-response effects of supplementary exercise training on VO₂max in trained athletes: a Systematic Review and Bayesian network meta-analysis. *Front Physiol* 2026. PMID 42597392, doi:10.3389/fphys.2026.1906583
35. Loucks AB, Thuma JR. Luteinizing hormone pulsatility is disrupted at a threshold of energy availability in regularly menstruating women. *J Clin Endocrinol Metab* 2003. PMID 12519869, doi:10.1210/jc.2002-020369
36. Milanović Z, Sporiš G, Weston M. Effectiveness of High-Intensity Interval Training (HIT) and Continuous Endurance Training for VO2max Improvements: A Systematic Review and Meta-Analysis of Controlled Trials. *Sports Med* 2015. PMID 26243014, doi:10.1007/s40279-015-0365-0
37. Montain SJ, Coyle EF. Influence of graded dehydration on hyperthermia and cardiovascular drift during exercise. *J Appl Physiol* 1992. PMID 1447078, doi:10.1152/jappl.1992.73.4.1340
38. Mountjoy M, Ackerman KE, Bailey DM, Burke LM, Constantini N, Hackney AC, Heikura IA, Melin A, Pensgaard AM, Stellingwerff T, Sundgot-Borgen JK, Torstveit MK, Jacobsen AU, Verhagen E, Budgett R, Engebretsen L, Erdener U. 2023 International Olympic Committee's (IOC) consensus statement on Relative Energy Deficiency in Sport (REDs). *Br J Sports Med* 2023. PMID 37752011, doi:10.1136/bjsports-2023-106994
39. Mountjoy M, Sundgot-Borgen JK, Burke LM, Ackerman KE, Blauwet C, Constantini N, Lebrun C, Lundy B, Melin AK, Meyer NL, Sherman RT, Tenforde AS, Klungland Torstveit M, Budgett R. IOC consensus statement on relative energy deficiency in sport (RED-S): 2018 update. *Br J Sports Med* 2018. PMID 29773536, doi:10.1136/bjsports-2018-099193 — record verified; **Europe PMC carries no abstract, so nothing is quoted from it**
40. Mujika I, Padilla S. Detraining: loss of training-induced physiological and performance adaptations. Part I: short term insufficient training stimulus. *Sports Med* 2000. PMID 10966148, doi:10.2165/00007256-200030020-00002
41. Mujika I, Padilla S. Detraining: loss of training-induced physiological and performance adaptations. Part II: Long term insufficient training stimulus. *Sports Med* 2000. PMID 10999420, doi:10.2165/00007256-200030030-00001
42. Pasricha SR, Low M, Thompson J, Farrell A, De-Regil LM. Iron supplementation benefits physical performance in women of reproductive age: a systematic review and meta-analysis. *J Nutr* 2014. PMID 24717371, doi:10.3945/jn.113.189589
43. Ried-Larsen M, Aarts HM, Joyner MJ. Effects of strict prolonged bed rest on cardiorespiratory fitness: systematic review and meta-analysis. *J Appl Physiol* 2017. PMID 28705999, doi:10.1152/japplphysiol.00415.2017
44. Savoie FA, Kenefick RW, Ely BR, Cheuvront SN, Goulet ED. Effect of Hypohydration on Muscle Endurance, Strength, Anaerobic Power and Capacity and Vertical Jumping Ability: A Meta-Analysis. *Sports Med* 2015. PMID 26178327, doi:10.1007/s40279-015-0349-0
45. Scribbans TD, Vecsey S, Hankinson PB, Foster WS, Gurd BJ. The Effect of Training Intensity on VO₂max in Young Healthy Adults: A Meta-Regression and Meta-Analysis. *Int J Exerc Sci* 2016. PMID 27182424, doi:10.70252/hhbr9374
46. Šmid AN, Golja P, Hadžić V, Abazović E, Drole K, Paravlic AH. Effects of Oral Iron Supplementation on Blood Iron Status in Athletes: A Systematic Review, Meta-Analysis and Meta-Regression of Randomized Controlled Trials. *Sports Med* 2024. PMID 38407751, doi:10.1007/s40279-024-01992-8
47. Snook J, Bhala N, Beales ILP, Cannings D, Kightley C, Logan RP, Pritchard DM, Sidhu R, Surgenor S, Thomas W, Verma AM, Goddard AF. British Society of Gastroenterology guidelines for the management of iron deficiency anaemia in adults. *Gut* 2021. PMID 34497146, doi:10.1136/gutjnl-2021-325210 — record verified; **abstract carries no haemoglobin response rate**, see Gaps
48. Southward K, Rutherfurd-Markwick KJ, Ali A. The Effect of Acute Caffeine Ingestion on Endurance Performance: A Systematic Review and Meta-Analysis. *Sports Med* 2018. PMID 29876876, doi:10.1007/s40279-018-0939-8
49. Stellingwerff T, Cox GR. Systematic review: Carbohydrate supplementation on exercise performance or capacity of varying durations. *Appl Physiol Nutr Metab* 2014. PMID 24951297, doi:10.1139/apnm-2014-0027
50. Trangmar SJ, González-Alonso J. Heat, Hydration and the Human Brain, Heart and Skeletal Muscles. *Sports Med* 2019. PMID 30671905, doi:10.1007/s40279-018-1033-y
51. Vanheest JL, Rodgers CD, Mahoney CE, De Souza MJ. Ovarian suppression impairs sport performance in junior elite female swimmers. *Med Sci Sports Exerc* 2014. PMID 23846160, doi:10.1249/mss.0b013e3182a32b72
52. Woolf K, Manore MM. B-vitamins and exercise: does exercise alter requirements? *Int J Sport Nutr Exerc Metab* 2006. PMID 17240780, doi:10.1123/ijsnem.16.5.453
53. Xiao Y, Deng Z, Sun W, Li J, Gao W. Effects of protein supplementation on body composition, physiological adaptations, and performance during endurance training: a systematic review and meta-analysis. *Front Nutr* 2025. PMID 40851900, doi:10.3389/fnut.2025.1663860
54. Zheng J, Pan T, Jiang Y, Shen Y. Effects of Short- and Long-Term Detraining on Maximal Oxygen Uptake in Athletes: A Systematic Review and Meta-Analysis. *Biomed Res Int* 2022. PMID 36017396, doi:10.1155/2022/2130993

**Cited from sibling reports, not re-verified here** (each was verified in the report that owns it):
Bergström, Hermansen, Hultman & Saltin 1967, *Acta Physiol Scand*, PMID 5584523, doi:10.1111/j.1748-1716.1967.tb03720.x
(record verified; **Europe PMC carries no abstract**, so the classic 57/114/167-minute figures are *not* quoted
anywhere above); Garrison et al. 2020 Cochrane magnesium/cramps, doi:10.1002/14651858.CD009402.pub3;
Klingert et al. 2022 hyponatraemia incidence, doi:10.3390/jcm11226775; Browning et al. on obese walking economy
and the ACSM 2007 fluid position stand, both in `science-energy-body.md`.
