# Strength redesign: the neural factor and general strength (harvest 2026-10-14)

This harvest sizes the second part of the proposed strength model, `strength = F^b · N`. The first part, F^b, is the muscle term: lean mass grows by the fitted law in the earlier harvests (`science-report.md`, `hypertrophy-science-report.md`). N is a general, transferable neural factor. The Strength level must stand for **generalisable strength**, not for skill at one trained lift.

**Scope ruling (Angus, relayed mid-task).** Everything that gives Strength XP is treated as one general full-body workout. The model therefore has one training signal and no per-exercise, per-movement or task-skill state. Here the specificity evidence is used for one job only: to size how much of the neural gain counts as general.

**Citations**

- `S6.n` ids are provisional rows in `neural-part.tsv`: 52 rows, of which 49 are settled and 3 open.
- Four-digit ids are rows already in `docs/reference/science.tsv`, cited rather than re-filed: S0085, S0086, S0585, S0586, S0587, S0589, S0610, S0611, S0618, S1931, S1932, S1937, S1939 and S2002.
- `S1.n` and `H.n` ids are rows in the earlier part files of this redesign.

**How the sources were resolved**

- Every settled row's record was resolved through PubMed E-utilities (efetch XML: title, authors, journal, year, DOI).
- Each row's numbers were read from the abstract, unless the row names the full text.
- Full texts were read from Europe PMC for Maden-Wilkinson 2020 (PMC7191505), Saeterbakken 2025 (PMC12296774) and Morton 2016 (PMC4967245).
- The Mitchell 2012 full text could not be fetched (HTTP 500), so its row rests on the abstract.

**Labels**

- **derived** marks arithmetic that is mine. None of it is in a TSV cell.
- **game choice** marks a constant the studies do not pin.

Model: claude-opus-5-5.

## 1. Specificity and transfer

**The trained lift gains far more than any untrained test of the same muscles.**

| study | trained-task gain | untrained-task gain (same trainees) |
|---|---|---|
| Rutherford & Jones 1986 (S6.1) | training weights about +200 % | isometric force +15–20 % |
| Rutherford, Greig 1986 (S6.2) | weights +160–200 % | isometric force +3–20 %; isokinetic cycling power unchanged |
| Knight & Kamen 2001 (S6.15) | 10-RM loads +66 to +77 % | isometric strength +30 to +36 % |
| Rutherford & Jones 1986, isometric arm (S6.1) | isometric force of the trained leg about +40 % | contralateral leg not significant |

- **Rutherford's reading (S6.1):** a large part of the gain in lifting weights is better coordination of the stabilising muscles, not more force from the prime mover.
- **Meta-analyses agree on the ratio:**
  - Saeterbakken 2025 (S6.4), 43 studies, 1660 participants: dynamic RT gives SMD 0.98 on the trained dynamic test and 0.42 on a non-trained isometric test. The ratio is 2.2–2.6 whatever the training status (untrained 1.27 vs 0.58; trained 0.75 vs 0.29). Changes in hypertrophy and muscle activity did not predict either effect.
  - Spitz 2023 (S6.5), against a time-matched control: d 1.84 on the trained movement and d 0.8 on a non-trained movement of the same muscles.
  - **derived:** the non-trained effect is 0.43 of the trained effect in both meta-analyses (0.42/0.98 and 0.8/1.84). This holds in SMD units, which are not percent units.
  - James 2024 (S6.6), in trained athletes: dynamic and position-matched isometric changes barely agree (reliability coefficient 16 %, CV 109 %).
- **Load and practice move the 1RM, not general strength:**
  - Mattocks 2017 (S6.7): practising the 1RM test alone, with up to five singles a visit, matched 8 wk of high-volume training for 1RM, isometric and isokinetic gains, despite less hypertrophy.
  - Heavy loads beat light loads for 1RM but not for isometric strength. This holds in Schoenfeld 2017 (S6.9) and in Mitchell 2012 (S6.10), where isometric gains did not differ, P = 0.92.
  - Buckner 2017 (S6.8) states that the 1RM is a skill.
  - In trained men, Morton 2016 (S6.11) found that only the bench press differed between loads (+9 vs +14 kg).
- **Joint mechanics of the transfer.** Single-joint training transfers more to isometric strength than multi-joint training (SMD 0.70 vs 0.33, S6.4). Multi-joint lifts carry more coordination, which stays with the lift.

**Verdict for the model:** general strength, read as a non-trained test of the trained muscles, gains about 40–45 % of the trained-task effect size, and about 10–20 % in absolute terms over 12 wk in novices. The rest of the 1RM gain is task skill: coordination, stabilisers and practice. The design excludes it.

## 2. General neural adaptations

| mechanism | magnitude | time course | transfer |
|---|---|---|---|
| **Voluntary activation** (twitch interpolation) | baseline already > 95 %; +2 to +3 points with training (S6.15, S6.16, S6.17); TMS VA pooled MD 1.41, NS (S6.19); no change at 4 wk in Wilson 2023 (S6.18) | within 2–4 wk, then flat | general to the muscle (a property of the drive to it), but too small to matter: at most about +3 % force |
| **Motor-unit discharge rate** | +3.3 pps at submaximal plateaus (S6.22); +4 pps (S0586); maximal rate +15 % young, +49 % older over 6 wk, rising within the first week (S6.23); +8–11 % with MVF +17.6 % in older adults (S0585); unchanged in Pucci 2006 (S6.16) and Wilson 2023 (S6.18) | 1–4 wk | not separable from task in these designs; cross-education studies find no firing-rate change in the untrained limb (S6.28) |
| **V-wave / descending drive** | V-wave +50 % (S6.21), +57 % (S6.17); pooled SMD 0.62 (S6.19) | 4–14 wk | the central component; it rises in the untrained limb with cross-education (S6.28) |
| **Antagonist coactivation** | −20 % after week 1 (S6.24); 41 → 32 % in the elderly over 8 wk (S6.49); progressively lower with years of training (antagonist EMG at the common torque −69 % at 4 yr vs untrained, S6.31) | fast early drop, then a slow tail over years | partly general: the untrained leg's coactivation fell 13 % (S6.24) |
| **Intracortical inhibition** | SICI SMD −1.00, silent period −0.66 (S6.20); same direction in S6.19 | weeks | central |
| **Cross-education** | pooled +11.9 % (CI 9.1–14.8) (S6.25); about 8 % of initial strength, roughly half of the trained side's gain, or one-quarter in the largest RCT (S6.26); 21 % in the RCTs that measured neural variables (S6.27) | 6 wk; rises further over 6 wk without training (S6.28) | general by construction: an untrained limb |

**What the mechanisms add up to in novices.**

- **Specific tension (force per PCSA) carries the early gain.** After 9 wk, MVC rose +26 to +31 %, PCSA +6 % and specific tension +17 to +20 %, with activation +3 % (S6.37, S6.38).
- **Specific tension is not all neural.** Single-fibre specific tension is unchanged, and lateral force transmission is the candidate (S6.39). Folland & Williams (S6.30) also list pennation and density.
- **In the first 35 days**, MVC rose +39 % with EMG +35 % while CSA rose 6.5–7.4 % (S6.29).
- **Agonist EMG change is the best single predictor of individual gains:** 30.6 % of the variance against 18.7 % for volume (S6.12). The test there was the trained task.
- **Moritani & deVries (S0086):** neural factors dominate for the first 3–5 weeks.

**Transferable share.** The training-specific results apply: maximal and explosive training raise different EMG phases (S6.13, S6.14). Two pieces of evidence bound the general share of the neural gain:

- **Cross-education:** about half to one-quarter of the trained side's gain appears in an untrained limb (S6.26). That is central drive, reachable from any task.
- **Non-trained isometric tests** gain about 0.43 of the trained-task effect (S6.4, S6.5), and part of that is hypertrophy.

**derived:** in absolute terms, for a novice over about 12 wk, the general neural share is about +8–10 % of force:

- A non-trained isometric test gains about +15 % (S6.1, S6.3: eccentric +11 %, concentric +15 %).
- Muscle-size growth is about +5–8 % over the same period (S6.3, S6.10, S6.37).
- The residual is about 1.15/1.06 ≈ 1.08–1.10.

## 3. The long-term split

**The key cross-sectional data (Folland's group, Loughborough), with the same untrained pool in each:**

| comparison | strength | muscle size | residual (not size) |
|---|---|---|---|
| 12 wk vs untrained (S6.31) | MVT +15 % | **derived:** ACSA +5.6 % (1.50/1.42) | **derived:** ≈ 1.09 |
| 4 yr vs untrained (S6.31) | MVT +60 % | ACSA +50 % | **derived:** ≈ 1.07 |
| 4 yr vs untrained (S6.32) | MVT +60 % | volume +56 %, PCSA +41 %, effective PCSA +40 % | specific tension +8 % (+9 % in the abstract); moment arm +4 % (height) |
| 4–6 yr vs untrained (S6.33) | MVT +66 to +71 % (elbow flexors, knee extensors) | +54 to +56 % | Mmax-normalised agonist EMG not different |
| ≥ 3 yr vs untrained (S6.34) | MVT +66 % | ACSA +54 % | explosive gain explained by size, not activation |

**Reading.**

1. **Muscle size explains most of the long-term gap.** Quadriceps volume alone explained MVT (R² = 0.81, S6.32), and effective PCSA × specific tension × moment arm reproduces it (**derived:** 1.40 × 1.08 × 1.04 ≈ 1.57 against 1.60 measured).
2. **The non-size residual at 4 years, ≈ +7–9 %, is no larger than at 12 weeks, ≈ +9 %.**
   - Agonist EMG at MVT was the same in the 12-wk and 4-yr groups, and both were higher than untrained (S6.31).
   - Once normalised to Mmax, long-term trained men show no agonist EMG difference at all (S6.33, S0587).
   - The general neural factor therefore saturates within months and does not grow over years.
   - Antagonist coactivation is the one mechanism that keeps improving (S6.31). Its size in net torque is not reported.
3. **The specific-tension residual is partly intrinsic, not neural.** Myosin spacing is 7 % tighter in trained muscle, and fibre number is 34 % higher (S6.35). Corticospinal excitability is lower, which the authors read as efficiency, not more drive (S6.36). An N_max of about 1.08–1.10 is therefore an upper bound on the neural part.
4. **Older force-per-area work.** After 6 months, torque per unit area was +12 % with no change in maximum IEMG (S6.40). Ikai & Fukunaga's ultrasound comparison was not readable, because the records have no abstract (S6.41, open). Maughan (S0082) gives untrained force per CSA with no trained contrast.

**The exponent b. This is the important correction.** The 0.67 in S0085 is a cross-size law: geometric similarity, where height and fascicle length scale with mass. The game fixes height at 1.70 m, so between people of one height:

- **Fixed height:** strength follows muscle volume almost one-to-one. The trained group is +60 % in MVT and +56 % in volume (S6.32).
- **Allowing for the trained group's 4 % greater height:**
  - **derived:** torque scales with h³ and area with h², so height accounts for a factor of 1.12 in torque.
  - **derived:** the height-matched figures are effective PCSA +30 % and volume +39 %.
  - **derived:** the exponent of contractile area on volume is ln 1.30 / ln 1.39 ≈ 0.79, below 1 because fascicles lengthen +11 % (S6.32, S6.29).
- **Strength sports across weight classes** give b on body mass of 0.55 in general, falling to 0.47 at the elite top (S6.42). These are cross-height numbers with fat in the mass, so they do not apply at fixed height.
- **Whole-body FFM is a poor F.** About half of FFM is not skeletal muscle: men carry 33 kg of skeletal muscle, 38.4 % of body mass (S6.44). The trained group's body mass was +25 % against quadriceps volume +56 % (S6.32). A power law on FFM would need b ≈ 1.6–1.7 (**derived** in § 6) to reproduce the trained/untrained ratio. An exponent near 0.8 applied to the skeletal-muscle part of FFM does it with a physical basis.

## 4. Detraining and retraining

| study | after training of | detraining | muscle | general strength / neural |
|---|---|---|---|---|
| Kubo 2010 (S1937) | 3 mo isometric | 3 mo | CSA back to baseline by 1 mo | strength and neural activation unchanged over 3 mo |
| Hortobágyi 1993 (S1939) | years (power athletes) | 14 d | type II area −6.4 % | isometric −7 % NS, 1RMs < 2 % |
| Häkkinen 2000 (S6.49) | 24 wk | 3 wk / 24 wk | CSA fell over 24 wk | 3 wk: isometric −6 % (middle-aged); 24 wk: isometric −12 / −9 %, 1RM −6 / −4 % |
| Häkkinen 1985 (S6.47) | 24 wk, men used to lifting | 12 wk | fibre areas fell | strength fall correlated with the IEMG fall |
| Narici 1989 (S6.46) | 60 d | 40 d | — | detraining time course similar to training (n = 4) |
| Andersen 2005 (S6.50) | 3 mo | 3 mo | CSA gain lost | isokinetic and EMG gains lost |
| Green & Gabriel 2018 (S6.28) | 6 wk unilateral | 6 wk | — | contralateral (purely central) strength **rose further** |
| Ogasawara (S1931, S1932) | 6 wk | 3 wk | no CSA loss | no 1RM loss |
| Bosquet 2013 (S0610) | mixed | dose-dependent | — | maximal force SMD −0.46 |

**Reading.**

- **Neural first, muscle later, on the way up; on the way down the order reverses.** Muscle size falls within a month (S1937), while general strength and activation hold for 1–3 months (S1937, S6.49, S1939).
- **Losses over 3–6 months are real but partial:** isometric force −9 to −12 % over 24 wk (S6.49), and short-term gains lost by 3 mo (S6.50).
- **No study separates the neural decay of a long-term trainee from muscle loss** (S6.51, open).
- **Retraining is fast:** the trained 1RM was back in < 8 wk (S0618), and regain outpaced continued training (S2002).

## 5. Calibration for a 4-year trainee

- **Measured (single-joint isometric, trained muscle groups):**
  - +60 % (knee extensors, 4.0 ± 0.8 yr; S6.31, S6.32);
  - +66 % (≥ 3 yr; S6.34);
  - +66 to +71 % (elbow flexors and knee extensors, 4–6 yr; S6.33).
- **Height:** the trained group was 183 vs 176 cm (S6.32).
  - **derived:** height-matched torque ratio ≈ 1.60 / 1.124 ≈ **1.42**.
  - **derived:** the same through mechanisms, effective-PCSA ratio 1.30 × specific tension 1.08 ≈ 1.40.
- **Split (derived):** of ln 1.42, the muscle term (effective PCSA, 1.30) carries about 75 %. Specific tension (1.08) carries about 22 %, and it is the upper bound on N.
- **Caveats:**
  - These are single-joint tests of the trained muscles. No study measures a multi-task battery at matched height (S6.52, open).
  - A full-body trainee trains all major groups, and the elbow-flexor and knee-extensor ratios agree (S6.33).
  - The 4-yr groups are self-selected, and responders persist (S0589). The ratio includes some genetics.
  - "Near-perfect" training would sit at or above these means.
- **Target ratio R = general strength (level 10) / general strength (level 5) = 1.45 (game choice; range 1.40–1.60).**
  - 1.40–1.42 is the height-matched reading.
  - 1.60–1.70 is the raw reading.
  - 1.45 allows "near-perfect" a little above the cohort mean.
  - Of R, N contributes 1.08–1.10 and muscle the remaining ≈ 1.32–1.34.

## 6. Proposed model

`S = (M / M5)^b · N`, with general strength S normalised to the untrained average (S = 1 at level 5).

| constant | value | basis |
|---|---|---|
| F | skeletal-muscle part of lean mass: M = FFM − F0 | strength follows muscle, not whole FFM (S6.32, S6.44) |
| F0 | 27 kg (game choice) | non-muscle FFM of the level-5 adult at 1.70 m. **derived:** FFMI 18 gives FFM 52.0 kg; skeletal muscle ≈ 38.4 % of a 65 kg body ≈ 25 kg (S6.44); 52 − 25 = 27 |
| M5 | 25 kg | as above. Lean gained in training is treated as muscle (game choice) |
| b | **0.8** (range 0.67–1.0) | fixed-height contractile area vs volume (**derived** 0.79, S6.32); 0.67 is the cross-size floor (S0085); 1.0 is the no-fascicle-growth ceiling |
| N | 1 (untrained) to N_max | general neural factor: central drive, coactivation, activation |
| N_max | **1.10** (range 1.07–1.12), the same for every training status | 12-wk residual ≈ 4-yr residual ≈ 1.07–1.09; specific tension +8 % (S6.31, S6.32, S6.33); +0.01–0.02 allowance for the coactivation tail (S6.31). The status-independent value is a game choice |
| rise | dN/dt = g · (N_max − N) / τ_up, with **τ_up = 3 wk** (game choice) | neural gains appear in week 1 (S6.23, S6.24), are large by 3–5 wk (S0086, S6.16, S6.29) and are complete by about 12 wk (S6.31) |
| g (signal) | g = min(1, W / W_sat), where W is the weekly training signal and **W_sat ≈ the signal of about 4–5 hard sets a week** (game choice) | strength, unlike size, plateaus at about 5 weekly sets (H.2); practice alone gives the full neural gain (S6.7) |
| fall | after a **grace of 3 wk** without signal, dN/dt = −(N − 1) / τ_down, with **τ_down = 12 wk** (game choice; range 8–16) | no loss at 2–3 wk (S1939, S1931, S1932, S6.49); activation held over 3 mo (S1937); partial losses by 3–6 mo (S6.49, S6.50); the central component can persist (S6.28) |
| retraining | the same τ_up from wherever N stands | fast return (S0618, S2002) |
| level | **level = 5 + 5 · (S − 1)/(R − 1), R = 1.45** (game choice) | **derived:** one level ≈ 9 % of untrained-average strength; S = 1.90 at level 15 |

**Checks (all derived).**

| check | inputs | result |
|---|---|---|
| novice, 10 wk | FFM +1.54 kg (S1.9); N = 1 + 0.10·(1 − e^(−10/3)) = 1.096 | muscle term 1.062^0.8 = 1.049; S = 1.15. This matches the +15 % non-trained isometric gains (S6.1, S6.3) |
| N's share of the gain | — | about 80 % of the general gain at 4 wk (N 1.074 against muscle term ≈ 1.019); about 66 % at 10 wk (ln 1.096 / ln 1.150); falling below 25 % at 4 yr |
| 4-yr trainee | about +11 kg lean (between the first-year +7.2 kg and the +14.5 kg natural limit of the earlier harvests) | M = 36 kg, (36/25)^0.8 = 1.34, × N 1.10 = **1.47 ≈ R**, so level ≈ 10.2 |
| detrained 6 mo after 4 yr | N with τ_down 12 wk after a 3-wk grace | N falls to ≈ 1.02 (1 + 0.10·e^(−23/12)); the muscle loss follows the lean-mass law |

**Why not b on whole FFM.**

- **derived:** at FFMI 18 → 22 (52.0 → 63.6 kg), reaching 1.45/1.10 needs b = ln 1.318 / ln 1.223 ≈ 1.37.
- **derived:** at the +11 kg case it needs ln 1.318 / ln 1.212 ≈ 1.43.
- Either value has no physical basis and would make the untrained low end too steep.
- The F0 offset carries the physics, since non-muscle FFM produces no force.

**What is left out by design (the scope ruling).** The model has no task-skill term. The 1RM-only gains (+60 to +200 % in trained lifts, S6.1, S6.2, S6.15) are not general strength, and the levels do not show them.

**Open.**

- S6.41: Ikai & Fukunaga, trained vs untrained force per CSA.
- S6.51: the neural decay rate in long-term trainees.
- S6.52: a multi-task, height-matched 4-yr ratio. R = 1.45 is therefore a game choice anchored on single-joint data.
