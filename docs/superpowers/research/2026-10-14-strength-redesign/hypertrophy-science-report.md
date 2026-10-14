# Strength redesign: hypertrophy dose, training status, substrate and memory (harvest 2026-10-14)

This harvest extends `science-report.md`, the lean-mass harvest of the same day, and corrects it where newer work disagrees. It does not repeat that report. The design under study:

- Strength is a pure function of fat-free mass (FFMI at a fixed 1.70 m).
- One level is 0.5 FFMI, which is 1.445 kg.
- Vanilla Strength XP becomes a training signal only.
- Lean mass grows only when signal, protein and energy act together.
- Progress slows with training status in two ways: the possible gain shrinks, and the stimulus needed to grow rises.

**Citations**

- `H.n` ids are provisional rows in `hypertrophy-science-part.tsv`: 68 rows, of which 62 are settled, 1 unverified and 5 open.
- `S1.n` ids are rows of the earlier part file.
- Four-digit ids are rows already in `docs/reference/science.tsv`, reused rather than duplicated.

**How the sources were resolved**

- Every settled row's record was resolved through PubMed E-utilities (efetch XML: title, authors, journal, year, DOI). Its numbers were read from the abstract, unless the row names the full-text section.
- Full texts were read from PMC for Trommelen 2023, Räntilä 2025, Seaborne 2018 and Serrano 2025.
- Pelland 2026 numbers come from its SportRxiv preprint (v2, September 2024), because the journal text is paywalled.

**Labels**

- Arithmetic that is mine is labelled **derived**.
- Every model constant the studies do not pin is labelled **game choice**.

Model: claude-opus-5-5.

## 1. Volume dose-response

**Shape: square root, not log, with no clear plateau.** Pelland's Bayesian meta-regression (67 studies, 2058 participants) is the 2024–2026 reference. Its findings:

- **Best-fit model:** the square-root model fits hypertrophy best (H.1).
- **Slope:** the marginal slope is +0.24 % muscle size per weekly fractional set (95 % CrI 0.15–0.33 %) at the mean of 12.25 sets.
- **Plateau:** the authors find diminishing returns but no clear plateau. The intervals at the top are still compatible with a plateau or an inverted U, because few studies exceed about 25 sets.
- **Strength:** strength follows a reciprocal model with a functional plateau at about 5 sets (H.2). Hypertrophy keeps paying long after strength stops (S0577).
- **Agreement with Schoenfeld 2017:** Schoenfeld's linear +0.37 % per set (S0579) is the same signal read with a linear model.

**Minimum effective dose and diminishing returns (H.1, Table 2A).** Pelland measures returns in tiers of one smallest detectable effect size, which is 2.05 % muscle size.

| weekly fractional sets | sets needed for one more detectable increment |
|---|---|
| 4 | the minimum effective dose |
| 5–10 | about 6 |
| 11–18 | about 8.5 |
| 19–29 | about 10.75 |
| 30–42 | about 12.5 |
| 43+ | unclear |

- **Derived:** the tier points fit `gain ≈ 1.8 % × (√S − 0.9)` per typical 8–12-wk study. The fit recovers each tier within about 0.2 % and the published slope at 12.25 sets (0.26 vs 0.24 %/set).
- The −0.9 intercept puts zero response near 1 set/wk. That intercept is a property of the fitted curve, marginalised over training status, not a measured threshold.

**Trained subjects.** The newer trials in trained people do not show a clean dose-response above about 12 sets:

- Baz-Valle 2022 (H.3), trained young men: 12–20 vs >20 sets did not differ for the quadriceps (p = 0.19) or the biceps (p = 0.59). Only the triceps favoured >20 sets (p = 0.01).
- Aube 2022 (H.5), lifters squatting about 2× body mass: 12, 18 and 24 weekly sets gave equal thickness and regional FFM. The point estimates were highest at 12 sets.
- Enes 2024 (H.6), men with 5.1 years of training: progressing volume gave a possible small benefit that "appeared to plateau" (p = 0.067).
- Enes 2025 (H.7), trained women: a 4-set progression beat a constant 22 sets for vastus lateralis CSA (p = 0.029).
- Schoenfeld 2019 (H.4), trained men: hypertrophy rose with 1, 3 and 5 sets per exercise. Strength did not.
- Camargo 2025 (H.10) reviews the conflict as unresolved between a saturation point and method artefacts.

**Untrained subjects.**

- Even 1 set/exercise grows muscle: +3.7 % CSA in 12 wk against +5.2 % with 3 sets. Only 13 of 34 people showed a clear benefit of the extra volume (H.8).
- In older adults, 51 of 85 did not respond to single sets, and they did respond to 4 (H.9).

**Does the response differ by training status?**

- Pelland adjusts for training status but runs the volume × status interaction only in its supplementary materials, which were not read (open row H.65).
- Lopez 2021 (H.17): untrained participants gain more hypertrophy (p = 0.033), and trained participants gain more from more sessions (p = 0.031–0.045).
- Effort matters for size, not for strength:
  - Hypertrophy rises as sets end closer to failure (H.11).
  - Training to failure adds only a trivial ES of 0.19 (H.12).

## 2. Maintenance dose

**The maintenance dose is small.**

- **Bickel 2011 (H.13).** After 16 wk of training, one-third and one-ninth of the training dose both kept hypertrophy for 32 wk in adults aged 20–35, and the one-third dose kept adding fibre size. Neither dose kept hypertrophy in adults aged 60–75. Strength was largely retained even with no training.
- **Tavares 2017 (H.14).** 1 or 2 sessions/wk at 50–57 % of the volume-load kept QCSA and 1RM for 8 wk. Stopping lost 5.4 % QCSA.
- **Rønnestad 2011 (H.15).** In professional players, 1 session/wk kept strength for 12 wk, and 1 session per fortnight did not.
- **Spiering 2021 (S0616).** 1 session/wk at 1 set per exercise, with relative load kept, maintains size for up to 32 wk in young people.
- **Coleman 2024 (H.16).** A 1-wk break does nothing to hypertrophy.

**Does maintenance rise with training status?** No study measures it, so this is open row H.64. All the maintenance trials started from 8–16-wk novices or older adults. Spiering says the data for athletes are insufficient. What the data do show is that maintenance rises with age (H.13).

## 3. Training status and the response

**Per-bout synthesis is smaller and shorter in the trained state.**

- **Mixed muscle protein:**
  - Tang 2008 (H.18): the trained leg's FSR peaked higher at 4 h (+162 % vs +108 %) but was back to rest by 28 h, while the untrained leg stayed +70 %.
  - Phillips 1999 (H.20) found the same attenuation, and breakdown rose only in the untrained.
  - Damas 2015 (H.23) states it as a review: a shorter, earlier peak gives a smaller overall synthetic response.
- **Myofibrillar protein (the hypertrophic fraction):** the evidence is mixed.
  - Kim 2005 (H.19): after training, the bout stimulated mixed MPS only in the untrained leg, while myofibrillar MPS rose equally in both legs.
  - Wilkinson 2008 (H.21): the myofibrillar response fell from +67 % untrained to +36 % after 10 wk.
- **Damage confounds the early response.** Damas 2016 (H.22): week-1 MyoPS is high but tracks muscle damage. Only from week 3 does MyoPS correlate with growth (r ≈ 0.9). Part of the "attenuation" is the loss of damage-repair synthesis through the repeated-bout effect (H.31), not a loss of growth signal.
- **Signalling.** In rats, mTOR signalling desensitises after 12–18 bouts and is restored by 12 days off (H.24, a rodent result).

**Gains per unit of stimulus.**

- Trained subjects gain less fat-free mass: 0.98 vs 1.54 kg in about 10 wk (S1.9), and untrained participants gain more hypertrophy (H.17).
- Long-trained strength athletes gained nothing in 21 wk of a novice programme (S1.11).

**Do trained people need more volume to progress?** The indirect evidence says yes, relative to their own habitual volume:

- **Scarpelli 2022 (H.26).** Volume set at 1.2× each person's logged habitual volume beat a standard 22 sets: +1.08 cm² CSA (CI 0.04–2.11), ES 0.75.
- **Camargo 2023 (H.27).** Hypertrophy correlated with the change in sets over habitual volume (rs 0.35–0.44). Raising volume more than 50 % beat cutting it.
- **Against:** Aube 2022 (H.5), where more sets added nothing in strong lifters. Damas 2019 (H.25), where varying the programme and adding volume raised MyoPS but not CSA.
- **Intrinsic variation dwarfs programme variation.** Between-subject variation was about 40 times the within-subject (between-leg) variation (H.25).

No study measures a growth threshold as a function of training status. The "rising threshold" is an inference from these readings.

**What limits the ceiling.**

- **Responsiveness is individual and reproducible.**
  - Size response ranges −11 to +30 % in 287 untrained adults (H.28).
  - Two identical training periods give correlated responses (r = 0.70–0.76, H.29).
  - 13 of 34 people gain more from more volume, tied to ribosome accumulation (H.8).
- **High responders differ in biology** (H.30): ribosome biogenesis, satellite-cell proliferation, androgen receptor content and microRNAs. Single candidate genes explain little.
- **A tonic brake exists** (section 8).
- **The natural FFMI limit stays Kouri's 25.0 in men** (S1.1). There is still no female limit (S1.34).

## 4. mTOR and MPS: the signal and the substrate

**The signal needs mTORC1.**

- Rapamycin blocks the roughly 40 % contraction-induced rise in human MPS (H.34).
- mTOR kinase inside the muscle fibre is necessary for load-induced hypertrophy in mice (H.35).

**Signal without substrate builds nothing.**

- **Fasted.** After a fasted bout, net muscle balance improves but stays negative at every point up to 48 h (H.33). Exercise alone does not accrete protein.
- **Fed.** With amino acids, synthesis rises 291 % after exercise against 141 % at rest (H.32): the effects multiply rather than add.
- **Deficit.** Exercise also rescues synthesis: 5 days of deficit cut resting MyoPS by 27 %, a bout restored it, and protein after the bout lifted it 16–34 % above rested balance (H.45).

**Protein dose per meal: the ceiling has gone.**

- Witard 2014 found 20 g of whey saturated acute MyoPS after leg exercise (H.36).
- Macnaughton 2016 found 40 g beat 20 g after whole-body exercise (H.37).
- Trommelen 2023 found that after 100 g of protein, myofibrillar synthesis was about 20 % higher in the first 4 h and about 40 % higher over 4–12 h than after 25 g. The response lasted more than 12 h, and oxidation was less than 15 % of the extra protein (H.38; amino-acid release is S1847).
- This **corrects** the per-meal saturation of S0065 (Moore 2015, 0.24 g/kg) as a cap on anabolism. It stands as an acute 4-h reading only.
- Practical guidance is 0.4 g/kg/meal over at least 4 meals (H.39).
- Even distribution has no effect on MPS in the one RCT (S0597).

**Protein dose per day.**

- The plateau stays at 1.62 g/kg (S0591).
- Lean gain becomes significant at ≥ 1.6 g/kg in adults under 65 (S0592).
- Tagawa 2020 (H.40, 105 trials) adds a knee at 1.3 g/kg: +0.39 kg lean mass per +0.1 g/kg below the knee and +0.12 kg above it, with no hard plateau up to 3.5 g/kg. This is a spline association, and its per-step size reads large.

**Protein or a surplus without training.**

- **Protein alone adds no lean mass.**
  - 1.3 against 0.8 g/kg for 6 months in older men without training: +0.31 kg (CI −0.46 to 1.08) (H.41).
  - 4.4 g/kg in trained people who kept their training unchanged: no change in FFM (H.42).
  - 3.4 against 2.3 g/kg under heavy training: equal FFM gain of +1.5 kg (H.43).
  - A protein-only surplus of +10 % added 0.00 kg body protein (S0606).
  - Leaf & Antonio review protein overfeeding as adding little fat (H.44).
- **An energy surplus alone adds some lean mass, but not clearly muscle.**
  - +40 % energy for 8 wk added +2.87–3.18 kg lean mass at 15–25 % protein, and none at 5 % (S0605).
  - Total body protein rose +0.44 kg in 6 wk at +40 % (S0606).
  - The lean share of a weight change follows initial fatness (Forbes, S0054, S0055; the coefficient is open in S1056).
  - Whether overfeeding FFM is muscle, rather than water, glycogen, organ or adipose-tissue lean, is open row H.67.

## 5. Energy status

**A deficit blunts lean gain.**

- About −500 kcal/d prevents lean gain, and strength still rises (S1.28).
- Mechanisms:
  - lower resting MyoPS (H.45);
  - endocrine anabolic resistance: IGF-1 fell 18–27 % against 8 % in balance, even with whey (H.46).
- **The exception is novices with very high protein.** Untrained men at 2.4 g/kg gained 1.2 kg lean in a 40 % deficit (S0064).
- In trained athletes cutting, ≥ 10 weekly sets per muscle spared lean mass. Raising volume during the diet looked better than cutting it, but the evidence is thin (H.47).

**Surplus.**

- **Trained lifters.** A 5 % and a 15 % surplus did not differ in muscle. The 15 % surplus added fat (S1.29), and elite athletes on a planned surplus gained fat, not extra lean (S1.30).
- **Untrained lifters.** A large surplus raised FFM (S1.31).
- The guidance is 0.25–0.5 % of body weight per week for novices and intermediates, slower for advanced lifters (S1.32). The optimum has never been validated (S1.33).
- The "Ribeiro 2023 bulking study" in the brief could not be located in PubMed or Crossref (open row H.66). Helms 2023 (S1.29) is the bulking RCT that exists.

**Recomposition.** Barakat 2020 reports that trained people recompose with progressive training, 1.6–2.4 g/kg protein and a near-maintenance energy status. It is **unverified** (H.48), because its record resolves but its text was readable only through secondary summaries. Novices recompose even in a deep deficit (S0064).

## 6. Rate of gain by training status

There are still no lean-mass data following untrained starters through years 2–5, so S1.35 stays open. What is new is the shape over years, from strength records:

- **Steele 2023 (H.49), 14 690 clients on minimal-dose training (1×/wk).**
  - Strength follows a linear-log curve and practically plateaus by 1–2 years.
  - It rises +30–50 % in year 1 and reaches +50–60 % by year 6.
- **Latella 2024 (H.50), powerlifters.**
  - Strength rises +7.5–12.5 % in year 1 and up to about 20 % after 10 years.

Both put about half or more of a decade's gain in year 1. That agrees with the halving coach model (S1.15). Under the linear-log fit, small gains continue rather than stopping at an asymptote.

The rate data remain:

- the 10-wk trial gains (S1.9, S1.10);
- the already-trained athletes (S1.12, S1.13, S1.14);
- the coach models: McDonald (S1.15, settled as TXT) and Aragon (S1.16). The Aragon primary still was not found; only secondary pages repeat it, so S1.16 stays unverified.

## 7. Detraining and muscle memory, newer work

**Rates of loss.**

- **Räntilä 2025 (H.51), Table 1.** The train/detrain/retrain values:

  | site | before | after training | after detraining | after retraining |
  |---|---|---|---|---|
  | vastus lateralis CSA | 26.2 | 30.3 | 27.2 | 31.3 cm² |
  | biceps brachii CSA | 9.1 | 10.6 | 9.8 | 11.3 cm² |

- **Derived from H.51:** 76 % (VL) and 53 % (BB) of the 10-wk gain was lost in 10 wk. As exponential half-lives, that is 4.9 and 9.2 wk.
- Larger gains were lost faster (r = −0.67, H.29).
- **Older adults.**
  - 12–24 wk off: a non-significant loss (d −0.60).
  - 31–52 wk off: a significant loss (d −1.11) (H.59).
  - One year after a 24-wk programme, the quadriceps gain was entirely lost (H.58).
- Pooled across exercise RCTs, lean gains are not significant at any follow-up (S1.27).
- Strength persists far longer than size (S0078, H.13, S0610).

**Regain: the human data, honestly.**

- **Equal to naive.** Räntilä (H.51): the second 10-wk block's size gain did not differ from the first. Training from a higher detrained floor regained the loss plus about the novice increment, so the rate matched the naive rate.
- **Faster than continued training.** Halonen 2024 (H.52, same cohort): the first 5 wk of retraining outgained the continuous group's weeks 10–15. Both groups ended equal. That compares retraining with slowed continued training, not with naive muscle.
- **Faster than naive, once.** Seaborne 2018 (H.53, 7 men): the 7-wk reload added 2.02 kg leg lean mass against 1.27 kg on first loading, with the advantage significant after correction (p = 0.022). This is the one human reading of a faster-than-naive regrowth. It has no control for order effects.
- **No advantage.** Psilander 2019 (S0078) and Cumming 2024 (S1.19).
- **Strength regain.** Strength comes back within 8 wk in older men (S0618).

Taken together, human muscle regrows at least at the naive rate, sometimes faster. The rodent advantage is clear (Wen 2021, H.56; S1.22). No human data cover an advanced lifter's regain (open row H.68).

**Mechanism: corrections to the earlier harvest.**

- The myonuclear-permanence account no longer holds for humans:
  - Rahmati 2022 (H.54, 147 articles): human myonuclei are lost with atrophy.
  - Mice lose acquired myonuclei within 6 months of detraining (H.55).
  - The 2025 critical review moves memory to the methylome, transcriptome and proteome (H.60).
- This **contradicts S1.21's "stable for at least 15 years and might be permanent"** as an explanation of human regain.
- What persists:
  - the epigenetic marks through 7 wk of unloading (S0620);
  - a proteomic signature through 10 wk of detraining (H.57);
  - in mice, a methylation memory with no difference in myonuclei (H.56).
- How long these persist beyond 10 wk is unknown.

## 8. The set-point premise

**For the premise: the body returns to a baseline and holds lean mass down.**

- Without stimulus, trained muscle returns to baseline within 10–52 wk (H.51, H.53, H.58, S0078).
- After starvation, hyperphagia tracks the fat-free-mass deficit independently of fat (S1616).
- A tonic molecular brake exists:
  - Myostatin knockout doubles or triples mouse muscle (H.61).
  - A human loss-of-function mutation gives gross hypertrophy (H.62).
  - Activin-receptor blockade added +1.70 kg lean mass in 48 wk without a training programme (H.63).
- Anabolic signalling desensitises with repeated identical bouts (H.24).

**Against the premise as an energy cost.**

- Muscle costs only 13 kcal/kg/d at rest (S0011). The 14.5 kg between untrained and the natural limit costs about 190 kcal/d (**derived**).
- The maintenance dose is small (H.13, H.14, S0616).
- Nothing shows the maintenance dose rising with lean mass (H.64).
- The defensible reading: gained muscle is cheap to keep with a little loading, but the set point pulls it back within months when loading stops.

## Model implications

The model is stated in kilograms of fat-free mass F, with the untrained set point F₀ and the natural ceiling F_c. That keeps it independent of the level mapping.

- **Status:** s = (F − F₀)/(F_c − F₀), so s is 0 untrained and 1 at the ceiling. Training status is where a character sits on its own headroom, so the rate depends on the level, not on elapsed time.
- **Signal:** S is the weekly training signal in **effective hard sets per muscle group**, counted fractionally.

The mapping from vanilla Strength XP to S is a **game choice**:

- One near-failure set counts 1. Basis: H.11, H.12.
- Low-effort carrying counts a fraction of a set.
- Indirect work counts 0.5. Basis: the fractional method, H.1.

**Level mapping caveat.** At 1.70 m and 0.5 FFMI per level, one level is 1.445 kg. With level 5 at FFMI 18 and a neutral natural limit of FFMI 23 (S1.1, S1.34), the ceiling sits at level 15, and a good first year (+7.2 kg) reaches level 10. If the perk is capped at 10, years 2–5 are invisible.

The fix is the owner's call:

- keep F continuous and display min(10, level);
- lower the level-5 anchor;
- or let level 10 mean the natural ceiling, at 1 FFMI per level as in the earlier harvest.

### a. Signal to anabolic response

`G(S, s) = clip( (√min(S, S_cap) − √S_g(s)) / (√S_ref − √S_g0), 0, ∞ )`, with `S_g(s) = S_g0 · e^{β·s}`.

| constant | value | basis |
|---|---|---|
| shape | square root of weekly sets | Pelland's best fit (H.1); the derived fit 1.8 % × (√S − 0.9) |
| S_g0 | 1 set/wk | **game choice** rounded from the derived zero-response point of about 0.8–0.9 sets (H.1) and the response to 1 set in novices (H.8) |
| S_ref | 12 sets/wk | Pelland's mean, 12.25 (H.1); ≥ 10 sets (S0576); normalises G = 1 for a novice |
| S_cap | 30 sets/wk | **game choice**: data are thin above about 25–30 sets (H.1); trained trials show no gain from 12 to 24 (H.3, H.5, H.6) |
| β | 2.5 | **game choice**: S_g is 3.5 sets at s = 0.5, 6.5 at s = 0.75 and 12 at s = 1. Basis: novices grow on 1 set (H.8); trained growth tracks volume above habitual (H.26, H.27), with an optimum of 12–20 sets for the trained (H.3); trained people respond less (H.17, S1.9); the desensitisation (H.24, H.18) |

- A novice gets 1.82× the response from 30 sets as from 12. Pelland's derived curve gives 1.77×.
- A fixed weekly dose has a steady state, s\* = ln(S/S_g0)/β: 4 sets reach s ≈ 0.55 and 12 sets reach the ceiling. Volume needed grows exponentially in status. That is the owner's second mechanism.
- **Optional:** a per-character responsiveness multiplier, lognormal with a median of 1. Basis: H.25, H.28, H.29. Its spread is a **game choice**.

### b. Maintenance threshold

`S_m(s) = m · S_g(s)`, with m = 1/3.

- **Basis:**
  - one-third and one-ninth doses kept size in the young (H.13);
  - about half the volume-load at 1–2 sessions kept size (H.14);
  - 1 session per week kept strength in professionals (H.15);
  - S0616.
- S_m runs from 0.3 sets at s = 0 to 4 sets (about one session) at the ceiling.
- **The rise with s is a game choice.** The premise wants it, and the desensitisation (H.24) and return-to-baseline evidence (section 8) fit it, but no study measures it (H.64).
- **Grace:** none while S ≥ S_m. Otherwise 2 wk before loss starts. Basis: S1.18, S1.26, H.16.

### c. Protein and energy gates

**Protein gate f_p.** This is revised from the earlier report.

| daily protein (g/kg) | f_p | basis |
|---|---|---|
| ≤ 0.4 | 0 | **game choice**; fasted exercise leaves net balance negative (H.33) |
| 0.8 | 0.5 | **game choice** at the RDA (S0509) |
| 1.3 | 0.92 | **derived**: Tagawa's knee carries 84 % of the 0.8–1.6 gain (H.40) |
| ≥ 1.6 | 1.0 | S0591, S0592 |

- f_p multiplies the signal and never adds on its own. Basis: H.32, H.41, H.42, S0606.
- No per-meal cap: H.38 and H.37 correct S0065 as a cap. The 24-h intake is the window, a **game choice**.

**Energy gate f_e(ΔE, s), with ΔE in kcal/d against maintenance.**

- **Zero point E₀.** f_e is 0 at ΔE ≤ E₀ = −500 kcal/d (S1.28, H.45, H.46).
- **Novice deepening (game choice).** Deepen E₀ for novices with high protein, toward −40 % of energy at s = 0 and protein ≥ 2.4 g/kg (S0064):
  - `E₀ = −500 · (1 + 1.4·(1 − s)²·clip((p − 1.6)/0.8, 0, 1))`.
- **Rising branch.** f_e is 0.85 at balance and 1.0 at a +5 % surplus, flat above.
  - **Changed from the earlier report's** 0.8 and +10 %: in trained lifters 5 % ≈ 15 % for muscle (S1.29), and the planned surplus added only fat (S1.30).
  - The values themselves are a **game choice**.
- **Surplus without signal.** A surplus without the signal adds no Strength. Overfeeding FFM goes to a non-muscle compartment or is ignored (S0605, S0606, H.67), a **game choice**.

### d. Ceiling and per-level slowdown

`dF/dt = k · (F_c − F) · G(S, s) · f_p · f_e`, with k = 0.0107 per week.

- k is **calibrated** so that 20 sets/wk with full gates gives +7.2 kg in year 1. That is the neutral 0.75× McDonald male year (S1.15), the earlier report's anchor.
- At 10 wk and 12 sets, the model gives +1.44 kg, against +1.54 kg for untrained FFM in about 10 wk (S1.9).
- F_c is at FFMI 23 neutral (S1.1, S1.34), so F_c − F₀ = 14.45 kg at 1.70 m.

**Simulated cumulative gain in kg, gates = 1, β = 2.5 (derived):**

| weekly sets | yr 1 | yr 2 | yr 3 | yr 4 | yr 5 | level at yr 5 (0.5 FFMI/level) |
|---|---|---|---|---|---|---|
| 6 | 3.6 | 5.7 | 7.0 | 7.9 | 8.5 | 10.9 |
| 12 | 5.6 | 8.3 | 9.8 | 10.8 | 11.4 | 12.9 |
| 20 | 7.2 | 10.2 | 11.7 | 12.5 | 13.1 | 14.0 |
| 30 | 8.5 | 11.5 | 12.8 | 13.5 | 13.9 | 14.6 |

- The yearly increments roughly halve for 20 sets: 7.2, 3.0, 1.5, 0.9, 0.5 kg. That matches McDonald (S1.15) and the year-1 dominance of the strength curves (H.49, H.50).
- Low-volume training stalls early, through the threshold, as the owner wants.

### e. Detraining and regain

**Loss.**

- When S < S_m(s) beyond the grace period, `dF/dt = −λ · (F − F₀) · (1 − S/S_m)`, decaying toward the set point F₀.
- λ = ln 2 / 6 wk.
- **Basis:** the derived half-lives of 4.9–9.2 wk (H.51), back to baseline by 20 wk (S0078), gone within a year (H.58), S1.27.
- The simulated novice keeps 37 % of a 10-wk gain after 10 wk off. Räntilä kept 24–47 %.

**Regain.**

- Store the peak F_peak.
- While F < F_peak, the growth rate is `max(k·(F_c − F)·G, (ln 2 / T_r)·(F_peak − F)·min(1, G))·f_p·f_e`, with T_r = 6 wk.
- It is a max, not a sum. That keeps a novice's retraining at about the naive rate: the simulated second block gains 0.94× the first, as in H.51.
- It lets an advanced lifter regain a 20-wk loss in about 43 wk instead of the 147 wk that the headroom term alone gives. **Derived:** without a memory term, regain takes as long as the original build, which no human study shows.
- T_r is a **game choice** between Halonen's fast early regain (H.52) and Seaborne's 1.6× reload (H.53).
- F_peak decays toward F with a half-life of 2 years, a **game choice**. Retained marks are measured only to 7–10 wk (S0620, H.57), and human myonuclei are not permanent (H.54, H.60).

### Weakest links

1. **β, the rising growth threshold.** No study measures the stimulus needed to grow as a function of training status. It rests on indirect trained-volume readings (H.26, H.27, H.17) and on rat desensitisation (H.24). Some trained trials contradict it (H.5, H.25).
2. **The multi-year lean-gain curve (k, F_c).** k is calibrated to a coach model (S1.15), and S1.35 is still open. The strength-record curves (H.49, H.50) give the shape, not lean kilograms. There is still no female ceiling (S1.34).
3. **Regain and maintenance for advanced lifters (T_r, the F_peak decay, m rising with s).** Every human detraining and retraining study used novices or older adults (H.51–H.53, H.58, H.64, H.68). The advanced-lifter behaviour is entirely game choice.

## Gaps

Open rows:

- **H.64:** the maintenance dose by training status.
- **H.65:** the volume × status interaction.
- **H.66:** "Ribeiro 2023" not located.
- **H.67:** whether overfeeding FFM is muscle.
- **H.68:** the human retraining rate against naive.

Earlier open rows that remain open: S1.34, S1.35, S1.36 (now refined by H.51–H.53 and H.68), S1056 and S1117.

Row-format note: the checker's provisional id form is `S<task>.<n>`. The part file uses `H.n` as briefed, and a copy renamed to `S2.n` passes `science_check.py --part` with 0 findings.
