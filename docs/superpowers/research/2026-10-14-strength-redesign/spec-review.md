# Realism review of the lean-mass Strength spec

Reviewer model: claude-opus-5-5. Read-only review of `docs/superpowers/specs/2026-10-14-lean-mass-strength-design.md` (draft of 2026-10-14) against the two harvests, the vanilla rate and trait-lever notes, the mod's kernels and the register. Every simulation is offline, in the scratchpad only:

- scratchpad `strev/` = `C:\Users\Angus\AppData\Local\Temp\claude\C--Users-Angus-repos-project-zomboid\e5eaf55d-0ef3-42a5-b6e6-4827b799b827\scratchpad\strev\`
- `model.py` (the proposed model with both partitions), `oracles.py` (the oracle registry), `fit.py` (the fit, profile, stability and bound report), `scenarios.py` (trajectories, novice cases, trained pair), `creation.py`, `detrain_alt.py`, `interior.py`, `rescore.py`;
- outputs: `fit_A_unconstrained.txt`, `fit_C.txt` (constrained best fit), `fit_B.txt` (Angus's premise scored), `interior.txt` (the recommended point R), `scenarios.txt` (spec, C, B), `scenarios_R.txt`, `detrain_alt.txt`, `rescore.txt`; the fitted points `fitted_C.json`, `fitted_B.json`, `fitted_R.json`, `fitted_A_unconstrained.json`;
- the PubMed and Crossref reads for item 10: `pm.py`, `ab.py`, `abs1.txt`, `abs2.txt`.

## Counts

| Severity | Count |
|---|---|
| Critical | 6 |
| Major | 13 |
| Minor | 10 |

The five most important changes, in order:
1. **Item 10, the partition.** Write the energy and protein partition into the spec (§ 5.1 below): a Forbes-based deficit arm with protein and training protection, a surplus arm whose lean share is the growth law, a labile-lean compartment for untrained overfeeding, and an energy gate whose zero point deepens for novices on high protein. It replaces `K.partition.leanGain` rather than sitting beside it.
2. **The level-10 XP pin kills the signal.** At native level 10 the spec pins XP at the level's start total, which is the cap, so vanilla `AddXP` returns before the Lua `AddXP` event and the mod sees no training at all. Park the XP at the level-9 total, as BeyondTen does.
3. **The weight-band refresh fights the new traits.** `NR_Server_Weight` re-applies vanilla's kilogram bands every minute, and the spec's default 60–65 kg body reads Very Underweight or Underweight there. Retire that refresh, and let the § 8 axes own the five traits.
4. **The fat traits don't match the lean scale.** Male percent-fat cuts on a sex-neutral lean scale call a BMI-22.5 body "High" fat and a BMI-24 body "Very high". Move the fat traits to fat-mass-index bands (Kelly 2009). The default body becomes 65.0 kg, BMI 22.5, 20 % fat.
5. **Clean the training signal and fix its constants.** Divide vanilla's protein ×1.5/×0.7 and the sandbox XP multiplier out of the signal, and weight carrying and melee by source. Adopt the fitted point R: β 3.0, S_g0 0.5, a status-falling set cap of 12 at s = 1, E₀ −800, k re-solved to 0.00991. Each value comes with its bound and conflict report.

---

## Item 10: protein, surplus and deficit as one non-linear partition (top priority)

### 10.0 What the spec says now, and why it is not enough

The spec's § 5 has one energy gate f_e and one protein gate f_p, and both multiply growth only. It says nothing about four things:
- how a surplus splits into fat and lean;
- what a deficit costs in lean, by protein, training and fatness;
- whether a trained character needs a surplus;
- what the existing `NR_Kernel_Partition` keeps doing.

That kernel already has a lean-gain arm (`G0 = 0.050` kg/day, `LM_CAP_RATIO = 1.25`, its own `gProt`, `gEnergy` and `DEFICIT_HALF*`; `NR_Kernel_Partition.lua:26-45, 56-96`). It also has a deficit arm that pays every kcal from fat up to Alpert's ceiling and only the overflow from lean (`:108-120`). So at a −500 kcal/day deficit, a character with more than about 7 kg of fat loses **no** lean at all, with or without protein or training. That contradicts:
- Weinheimer's 81 % (S0072);
- Heymsfield's "one-fourth" rule (PMID 24447775);
- Mettler (PMID 19927027);
- Pasiakos (PMID 23739654).

### 10.1 The evidence, (a)–(e)

Every citation below was resolved by PMID through NCBI E-utilities, or by DOI through Crossref (Barakat). The numbers come from the abstracts, read in `abs1.txt` and `abs2.txt`. Only one source is secondary: the Murphy & Koehler study-population note, which comes from a co-author's article (mysportscience.com) and is marked as such. Four-digit ids are rows already in `docs/reference/science.tsv`.

**(a) Recomposition by training status**

- **Longland 2016 (S0064, PMID 26817506).** Overweight young men in a 40 % deficit, training 6 d/wk, for 4 wk:
  - at 2.4 g/kg: lean +1.2 ± 1.0 kg, fat −4.8 ± 1.6 kg;
  - at 1.2 g/kg: lean +0.1 ± 1.0 kg, fat −3.5 ± 1.4 kg.

  This is the novice-recomposition anchor.
- **Campbell 2018 (PMID 29405780).** Aspiring female physique athletes, 8 wk of resistance training (energy not controlled):
  - at 2.5 g/kg: fat-free mass +2.1 kg and fat mass −1.1 kg;
  - at 0.9 g/kg: +0.6 kg and −0.7 kg (not significant).
- **Garthe 2011 (PMID 21558571).** Elite athletes with 4 resistance sessions a week:
  - 0.7 %/wk weight loss (19 % energy cut) for 8.5 wk: lean +2.1 % and fat −31 %;
  - 1.4 %/wk (30 % cut): lean −0.2 %, unchanged.

  So trained athletes can recompose in a moderate deficit, but not in a large one.
- **Antonio 2015 (PMID 26500462).** Trained men and women (4.9 ± 4.1 y), 3.4 g/kg protein, a new periodised programme, 8 wk: FFM +1.5 ± 2.2 kg, fat −1.7 ± 2.3 kg, body weight −0.1 kg. That is recomposition in the trained, at about maintenance.
- **Barakat 2020** (*Strength Cond J* 42(5):7-21, doi:10.1519/SSC.0000000000000584; not in PubMed, abstract read through Crossref): "although many suggest that this only occurs in untrained/novice and overweight/obese populations, there is a substantial amount of literature demonstrating this body recomposition phenomenon in resistance-trained individuals". A narrative review.
- **Murphy & Koehler 2022 (S1.28, PMID 34623696).** About −500 kcal/day prevents lean gain (meta-regression), and strength gains are unaffected. The co-author's own write-up adds that "almost all studies were conducted in sedentary individuals … the present analysis lacked sufficient data on trained individuals" (secondary). So the −500 zero point is a novice reading, and the paper gives **no** trained-against-untrained split.
- **Helms 2014 (S0599, PMID 24092765).** Lean, trained, energy-restricted athletes need 2.3–3.1 g/kg FFM, scaled up with leanness and the size of the deficit.
- **Chappell 2018 (PMID 29371857).** Natural bodybuilders prepare over 22 ± 9 wk on high protein. It is a diet survey, with no lean-mass outcome.

Does the zero point depend on status and protein?
- **Protein, yes:** Longland's 2.4 against 1.2 g/kg in the same 40 % deficit.
- **Status, weakly:** the novice evidence tolerates deeper deficits (Longland). The trained evidence supports recomposition only in moderate deficits (Garthe 2011, 19 % against 30 %) and at about maintenance (Antonio 2015).

The fit below makes the zero point deepen with protein, mostly for novices (`a_nov`).

**(b) The surplus partition by training status**

- **Bray 2012 (S0605, PMID 22215165).** Untrained subjects, no training, +954 kcal/d for 8 wk:
  - lean +2.87 kg at 15 % protein and +3.18 kg at 25 %, none at 5 %;
  - fat rose similarly in all arms.

  Whether that lean is muscle is open (H.67), and total body protein rose only 0.44 kg in Rosenbaum (S0606).
- **Garthe 2013 (S1.30, PMID 23679146).** Elite athletes adding 4 strength sessions: a guided surplus (3585 against 2964 kcal) gave body weight +3.9 % against +1.5 % and fat mass +15 % against +3 %, with lean gain **not different**.
- **Helms 2023 (S1.29, PMID 37914977).** Trained lifters at maintenance, +5 % and +15 % for 8 wk:
  - muscle thickness shows "no evidence supporting the group model";
  - body-mass change predicts skinfold change (R² 0.49) and only weakly biceps thickness (R² 0.24).
- **Slater 2019 (S1.33, PMID 31482093):** "the specific energy surplus required to facilitate muscle hypertrophy is unknown" and the "sweet spot … has never been validated".
- **Iraki 2019 (S1.32, PMID 31247944):** +10–20 % and 0.25–0.5 % of body weight per week for novice and intermediate lifters; "advanced bodybuilders should be more conservative".
- **Ribeiro 2023** is still not located (H.66).

The reading: above maintenance, in trained people, the extra energy goes to fat. In untrained, untrained-for-it people a surplus adds lean, but Bray's lean comes without training and is probably non-muscle.

**(c) The deficit partition: the lean share of weight lost**

- **Forbes/Hall (S0054, S0055).** The lean share falls as initial fat rises. Forbes' curve gives ΔFFM/ΔW = 10.4/(10.4 + FM); the coefficient row S1056 is open.
- **Heymsfield 2014 (PMID 24447775):** about one quarter FFM for typical dieting, smaller with exercise.
- **Weinheimer 2010 (S0072):** 81 % of diet-only groups against 39 % of diet-plus-exercise groups lost at least 15 % of their weight as FFM.
- **Mettler 2010 (PMID 19927027).** Trained athletes on 60 % of habitual energy for 2 wk:
  - at about 1.0 g/kg: lean −1.6 of −3.0 kg;
  - at about 2.3 g/kg: lean −0.3 of −1.5 kg.
- **Pasiakos 2013 (PMID 23739654).** A 40 % deficit for 21 d: the FFM share of the loss is lower at 1.6 and 2.4 than at 0.8 g/kg. The direction comes from the abstract; the full text was not readable, so no share is cited.
- **Cava 2017 (S0609):** protein and resistance exercise limit the loss.
- **Helms 2014 (S0599):** leaner and more trained people need more protein.

**(d) Protein excess at balance or in a surplus**

- **Antonio 2014 (PMID 24834017).** Trained subjects at 4.4 against 1.8 g/kg, with about +800 kcal of reported protein over 8 wk: no change in fat mass.
- **Antonio 2016 crossover (PMID 26778925):** 2.6 against 3.3 g/kg in trained men, no body-composition change.
- **Bray 2012:** the 5 % protein arm stored most of the excess as fat, while the 15 % and 25 % arms stored more as lean. Fat gain was similar across the arms.

This is an **energy-side** finding (protein's thermic cost, oxidation, self-reported intake), not a partition one. A partition that books every surplus kcal to fat cannot reproduce it, and should not try. It is listed as a named conflict below.

**(e) Bulk-cut cycles against maintenance for trained people**

No trial compares a year of bulk-cut cycles with a year at maintenance in trained lifters. The recommendation to bulk and then cut is practitioner consensus (Iraki 2019, a narrative review). The only trials in trained people run the other way:
- surplus size does not change muscle (Helms 2023, Garthe 2013);
- maintenance and moderate deficits permit recomposition (Antonio 2015, Garthe 2011, Barakat 2020).

**Angus's premise — that trained people gain ~0 lean at maintenance and need surplus plus cut cycles — is not supported by the trials that exist.** It is a defensible gameplay choice, and it is offered below as an option.

### 10.2 The proposed functional form (fits `NR_Kernel_Partition`, replaces its lean arm)

The record keeps `fm` (fat M) and `lm` (muscle lean F, the level). It gains one field, `lx`, the labile lean X: water, glycogen and organ lean. X counts in weight, but not in the level or in REE.

Per closed day, with:
- E the day's balance (kcal), p the protein (g/kg/d) and S the weekly hard sets;
- s the status, G the signal (§ 5), and T = min(1, S/10), the training protection (H.47: at least 10 weekly sets spared lean in cutting);

each step is:

1. **The growth law,** as § 5:
   ```
   g = k·(F_c − F)·G·f_p(p)·f_e(E, s, p)
   ```
   where:
   - S_max(s) = 30 − (30 − S_max1)·s, with S_max1 = 12;
   - f_e = 0 at E ≤ E₀(s, p), rising linearly to f_bal at E = 0 and to 1 at E = +surplus_full·TDEE;
   - E₀(s, p) = E₀·(1 + a_nov·(1 − s)²·clip((p − 1.6)/0.8, 0, 1)).
2. **The surplus arm (E ≥ 0).** Muscle growth is paid first at RHO_LEAN (1816 kcal/kg). The rest R is split:
   - lean weight share x = forbes(M)·clip((p − 0.8)/0.8, 0, 1)·(1 − T), where forbes(M) = 10.4/(10.4 + M);
   - X gains x·ΔW, capped at X ≤ 0.05·F;
   - the remainder is fat at RHO_FAT.
   - At balance, X decays on a 28-day time constant.

   If growth exceeds the surplus, fat pays the difference (recomposition at RHO_LEAN/RHO_FAT, as the partition's deficit arm already does).
3. **The deficit arm (E < 0).**
   - The protection is prot = clip(1 − wT·T − wP·clip((p − 0.8)/(p_hi − 0.8), 0, 1), floor, 1).
   - The lean weight share is forbes(M)·prot. Fat pays the rest up to Alpert's ceiling (69 kcal/kg fat/day).
   - The overflow beyond the ceiling is split as the kernel already splits it: lean pays the overflow × prot, and fat pays the spared share beyond the ceiling.
   - X pays any lean loss first.
   - Growth g still runs (recomposition), funded from fat.
4. **Detraining and regain** follow § 6, with the fixes of M3 and M7.

How the requested non-linearity enters:
- the √ signal and the exponential threshold;
- the piecewise energy gate whose zero moves with protein and status;
- the Forbes share, which falls with fat mass;
- the clipped protection;
- the Alpert overflow at low fat;
- the X cap.

### 10.3 The oracle registry

There are 33 entries, in `oracles.py`. Each is scored as distance outside its band over the band width, squared; a degenerate check scores 1 if it fails. Where a trial does not report its training volume, TDEE or fat mass, the oracle states its own assumption.

| Oracle | Band | Source |
|---|---|---|
| Year-1 kg at 20 sets | 6.8–8.5 | S1.15 ×0.75 (first harvest) |
| Year 2 over year 1 | 0.40–0.60 | S1.15; H.49, H.50 |
| Year 3 over year 2 | 0.40–0.65 | S1.15 |
| Untrained, 10 wk, ~12 sets | +1.12–1.96 kg | S1.9 Benito |
| Novice gain at 30 over 12 sets | 1.55–2.00 | H.1 Pelland (derived 1.77) |
| Gain at 3 over 9 sets | 0.50–0.90 | H.8 (+3.7 against +5.2 %) |
| Advanced, 24 over 12 sets | 0.70–1.40 | H.5 Aube (12 = 18 = 24) |
| Longland lean at 2.4 g/kg | +0.6–1.8 | S0064 |
| Longland lean at 1.2 g/kg | −0.4–+0.6 | S0064 |
| Longland fat | −5.0 to −3.0 (report only) | S0064 |
| Garthe 2011, −19 % | lean +0.8–1.8 | PMID 21558571 |
| Garthe 2011, −30 % | lean −0.6–+0.4 | PMID 21558571 |
| Murphy & Koehler at −500 | lean −0.3–+0.3 | S1.28 |
| Trained at maintenance, 8 wk | +0.1–1.5 | Helms 2023; Antonio 2015 |
| Trained at maintenance, Angus premise | −0.1–+0.1 (report only; weighted in variant B) | Angus |
| Trained, +15 % over maintenance | 0.8–1.6 | S1.29 |
| Garthe 2013, +600 against +150, lean ratio | 0.8–1.35 | S1.30 |
| Garthe 2013 fat difference | 0.8–2.5 kg | S1.30 |
| Mettler lean share at 1.0 g/kg | 0.35–0.70 | PMID 19927027 |
| Mettler lean share at 2.3 g/kg | 0.05–0.35 | PMID 19927027 |
| Quarter rule (diet only, obese) | 0.15–0.35 | PMID 24447775; S0072 |
| Pasiakos share, 0.8 minus 1.6 g/kg | 0.10–0.50 | PMID 23739654 (direction) |
| Bray lean at 15 % protein | +1.5–3.5 | S0605 |
| Bray lean at 5 % protein | −0.7–+0.5 | S0605 |
| Bray muscle with no signal | ±0.05 | H.41, H.42, S0606 |
| Räntilä share kept after 10 wk off | 0.24–0.47 | H.51 |
| Räntilä block 2 over block 1 | 0.80–1.25 | H.51 |
| Bickel, ⅓ dose, 32 wk, share kept | 0.85–1.80 | H.13 |
| Bickel, ⅑ dose | 0.85–1.40 | H.13 |
| Detraining half-life (novice) | 4.9–9.2 wk | H.51 |
| Degenerate: +2 % protein, +2 % surplus, +5 % sets | must each move lean | fit rules |

**Hard constraint.** An average character goes from level 5 to level 15 in 5 years at 20 sets with full gates; k is re-solved by bisection for every candidate. A candidate where the threshold meets the set cap below level 15 is scored infeasible.

### 10.4 The fit

**The grid.** The search is grouped coordinate descent: each group's full grid is searched with the others held, and rounds repeat until nothing improves.

| Group | Grid |
|---|---|
| Growth | β {1.5, 2, 2.5, 3, 3.5} × S_g0 {0.5, 0.7, 0.85, 1.0, 1.3} × S_max1 {12, 15, 20, 30}, with k re-solved each time |
| Energy | E₀ {−400, −500, −650, −800, −1000} × f_bal {0.7, 0.85, 1.0} × a_nov {0, 0.7, 1.4, 2.1, 2.8} × surplus_full {0.03, 0.05, 0.10} |
| Deficit | wT {0.2, 0.35, 0.5, 0.65} × wP {0.3, 0.45, 0.6, 0.75} × floor {0.05, 0.1, 0.15, 0.3} × p_hi {1.6, 2.0, 2.4, 2.8} |
| Memory | detraining half-life {4.9, 6, 7, 8, 9.2} wk × regain half-life {1, 2, 3, 4, 6, 8} wk × m {0.11, 0.2, 0.333, 0.5} × grace {7, 14, 21, 28} d × regain form {max, sum} |

**The candidate counts.**
- Constrained run C: 1541 candidates per round, two rounds, **3082 evaluated**. The second round improved nothing.
- Unconstrained run A, with wider grids: 2064 per round, 4128 evaluated.
- Premise run B: 2216 per round, 4432 evaluated.

**The results.**

| Point | Score | Notes |
|---|---|---|
| Spec as written | 6.61 | with the controller's k; Smax1 30 |
| A (unconstrained) | 0.24 | ran to its grid edges: β 5, S_g0 0.1, E₀ −2000, a_nov 5, wP 0.75, floor 0. Rejected: degenerate (the energy gate is effectively absent in any deficit). |
| **C (constrained best)** | **0.402** | k 0.009906, β 3.0, S_g0 0.5, S_max1 12, E₀ −1000, f_bal 0.85, a_nov 2.8, surplus_full 0.10, wT 0.35, wP 0.75, floor 0.05, p_hi 1.6, detrain 6 wk, regain 6 wk, m ⅓, grace 14 d, regain = max |
| **R (recommended, interior)** | **0.905** | C, with E₀ −800, a_nov 1.4, wP 0.6, floor 0.10, p_hi 2.0, surplus_full 0.05 and detrain_status 2.0; k 0.00991 |
| B (premise weighted) | 1.22 | trained_need 1.0 (at its bound) still leaves the trained gaining +0.23 kg in 8 wk at maintenance, and it breaks Helms 2023 (1.99) and year 1 (6.72 kg) |

**Bound report for C.** Eight constants sit at the edge of the constrained grid:
- **S_g0 0.5**, its lower edge. H.1's derived zero response is 0.8–0.9 sets, and H.8 pulls lower.
- **S_max1 12**, its lower edge. Aube pulls lower.
- **E₀ −1000, a_nov 2.8, wP 0.75, floor 0.05 and p_hi 1.6**, all pulled by the short-trial recomposition oracles, Longland and Garthe 2011.
- **surplus_full 0.10**, an edge but almost flat (± 0.007).

Each constrained edge was set at a defensible physiological limit, and the unconstrained run shows the oracles pull past every one of them. So **C is not accepted as-is**.

R moves the recomposition constants back inside the grid, at a cost of +0.50 in score, all of it from three oracles:
- Longland at 2.4 g/kg: +0.17 against ≥ +0.6;
- Longland at 1.2 g/kg: −0.56 against ≥ −0.4;
- Garthe 2011 slow: +0.10 against ≥ +0.8.

Those oracles read DXA lean over 4–8.5 wk, which includes the glycogen and water a high-carbohydrate, high-protein diet adds. The model's muscle term cannot, and should not, carry that.

**Recommendation: adopt R as the defaults, and keep C's values as the sandbox maxima.**

**The conflicts: these oracles cannot all be met together.**
1. **Short-trial recomposition** (Longland, Garthe 2011, Campbell) **against the slow-tissue rate** (Benito 10-wk +1.54 kg, and the year-1 anchor). Longland's +1.2 kg in 4 wk is about 0.3 kg/wk, more than the model's maximum novice rate of about 0.19 kg/wk. Meeting it needs an energy gate that never closes for novices.
2. **Murphy & Koehler's zero at −500** (sedentary novices) **against Garthe 2011's trained gain at −19 %.** The model meets Murphy & Koehler only as growth minus loss, not as a closed gate.
3. **Pelland's √ with no plateau** (H.1) **against Aube 2022 and Baz-Valle** (no benefit above 12 sets in advanced lifters). A status-falling set cap (S_max1 12) is the bridge, and Aube still misses slightly (1.44 against ≤ 1.40).
4. **H.8's low-volume ratio** (0.71) **against the anchor shape.** The model reads 0.46. A lower S_g0 meets H.8 but breaks year 1 and the halving.
5. **Garthe 2013's fat difference** (measured about +1.2 kg, model +3.3 kg) and **Antonio 2014's zero fat gain on +800 kcal of protein.** These are on the energy side (protein's thermic cost, adaptive expenditure, diary intakes), outside the partition. Not fitted.
6. **Angus's premise against the trained evidence** (Helms 2023, Garthe 2013, Antonio 2015, Barakat 2020). Under R a trained character gains +2.85 kg in a year at maintenance; the premise asks for about 0.

**Stability of R** (`interior.txt`), with each constant probed at ×0.95 and ×1.05:
- **No cliff.** The largest move is p_hi: 0.789 at ×0.95 and 1.019 at ×1.05. Every other constant moves the score by less than 0.07.
- **Three constants read flat:** the regain half-life (no oracle engages it under the max form, since Räntilä's novices regain through growth), m (Bickel's doses sit far above S_m at novice status), and x_max_frac.
- **detrain_status** moves only two oracles, and no score.

The flat constants are **unidentified by the evidence**: each keeps its literature or game-choice default and is reported as such.

**Profiles of C** (`fit_C.txt`):
- S_g0 has a **cliff** from 0.85 (1.43) to 1.0 (8.46), and **1.3 is infeasible**: the anchor is unreachable when S_g0·e^(β·0.87) ≥ S_max(0.87).
- Every other profile is smooth.

**The degenerate checks** pass at R: +2 % protein moves lean +0.023 kg in 10 wk, +2 % surplus +0.066, and +5 % sets +0.033. Run A's f_bal = 1.0 failed the surplus check, which is how A's flat energy gate was caught.

### 10.5 The cases Angus asked for (point R; `scenarios_R.txt`)

**The novice cases.** An average untrained character at 20 sets for 16 wk. Each cell is muscle F and fat change in kg; labile lean was 0 throughout.

| Case | wk 4 | wk 8 | wk 12 | wk 16 |
|---|---|---|---|---|
| Recomp, −500, 2.4 g/kg, fat 8.5 kg | +0.46 / −1.57 | +0.79 / −3.12 | +0.92 / −4.63 | +0.89 / −6.10 (lean stalls as fat nears its floor) |
| Recomp, −500, 2.4 g/kg, fat 20 kg | +0.50 / −1.58 | +0.97 / −3.15 | +1.40 / −4.72 | +1.81 / −6.28 |
| Maintenance, 1.6 g/kg | +0.74 / −0.14 | +1.44 / −0.28 | +2.11 / −0.41 | +2.73 / −0.53 |
| Surplus +10 % (+260), 1.6 g/kg | +0.87 / +0.60 | +1.68 / +1.22 | +2.44 / +1.84 | +3.15 / +2.48 |

How these compare with the trials:
- **Longland's own conditions** (−1200 kcal, 4 wk): R gives lean +0.17 and fat −3.59 at 2.4 g/kg, and −0.56 / −3.45 at 1.2 g/kg. Measured: +1.2 / −4.8 and +0.1 / −3.5. The direction and the protein contrast are right; the size is low, which is conflict 1.
- **Campbell 2018** (8 wk at 2.5 g/kg, energy uncontrolled): FFM +2.1 against the model's +1.44 at maintenance.
- **Garthe 2011 SR:** LBM about +1.3 kg against the model's +0.10 at s = 0.2.

**The trained pair.** A character at s = 0.5 (level 10.75), 20 sets, one year:

| Year | Muscle | Fat | Level |
|---|---|---|---|
| Maintenance, 2.0 g/kg | +2.85 kg | −0.55 kg | 12.72 |
| Bulk +10 % for 18 wk, then cut −500 at 2.4 g/kg for 8 wk, twice | +2.55 kg | +1.05 kg | 12.51 |
| Bulk +20 % / cut, twice | +2.59 kg | +8.52 kg | 12.54 |
| Variant B (premise), maintenance | +1.52 kg | −0.29 kg | — |
| Variant B (premise), bulk +10 % / cut | +2.28 kg | +1.10 kg | — |

So **only under the premise does bulk-cut beat maintenance**: by +0.76 kg of muscle a year, for +1.4 kg of fat. Under the evidence-led point, maintenance matches or beats bulk-cut for muscle, and leaves the character leaner.

### 10.6 Spec edits for item 10

**Edit 10-A, in § 5's table.**

Old:
```
| f_e | 0 at −500 kcal/day or deeper, 0.85 at balance, 1.0 at a 5 % surplus | Murphy & Koehler 2022; Helms, Iraki, Slater: a larger surplus adds fat only |
```
New:
```
| f_e | 0 at E₀(s, p) or deeper, linear to 0.85 at balance, 1.0 at a +5 % surplus; E₀(s, p) = −800 · (1 + 1.4 · (1 − s)² · clip((p − 1.6)/0.8, 0, 1)) kcal/day | Murphy & Koehler 2022 (S1.28: −500 stops net lean gain in mostly sedentary novices, met here as growth minus the § 5.1 loss); Longland 2016 (S0064) for the protein deepening; Garthe 2011 (PMID 21558571) for trained recomposition in a moderate deficit; Helms 2023 (S1.29) and Garthe 2013 (S1.30): a larger surplus adds fat only. Fitted, point R of the 2026-10-14 review |
```

**Edit 10-B, in § 5's first bullet list.**

Old:
```
- **Signal, protein and energy multiply.** Without the signal, protein and a surplus build no muscle; overfeeding's lean share goes to the non-muscle lean the body model already holds (H.67 open; a game choice).
```
New:
```
- **Signal, protein and energy multiply.** Without the signal, protein and a surplus build no muscle. Overfeeding's lean share goes to a new labile-lean field `lx` (§ 5.1), which counts in weight but not in the level or REE (Bray 2012, S0605; whether it is muscle is open, H.67).
```

**Edit 10-C. Insert after § 5's last bullet:**

```
### 5.1 The energy and protein partition

The growth law above replaces `K.partition.leanGain`, `K.partition.headroom`, `G0`, `LM_CAP_RATIO`, `gEnergy` and the `DEFICIT_HALF*` constants. The partition keeps its role as the only writer of `fm`, `lm` and the new `lx`, once per closed day:

- **Surplus (E ≥ 0).** The day's growth g is paid first at RHO_LEAN. The remainder R splits with the lean weight share x = forbes(M) · clip((p − 0.8)/0.8, 0, 1) · (1 − T) into `lx` (capped at 0.05 · F) and fat. forbes(M) = 10.4/(10.4 + M) (Forbes, S0054, S0055; coefficient open, S1056), and T = min(1, S/10) (H.47). If g exceeds the surplus, fat pays the difference. At balance, `lx` decays toward 0 on a 28-day time constant.
- **Deficit (E < 0).** The lean weight share is forbes(M) · prot, with prot = clip(1 − 0.35 · T − 0.6 · clip((p − 0.8)/1.2, 0, 1), 0.10, 1) (Mettler 2010, PMID 19927027; Pasiakos 2013, PMID 23739654; Weinheimer 2010, S0072; Heymsfield 2014, PMID 24447775; Helms 2014, S0599; Cava 2017, S0609). Fat pays the rest up to Alpert's ceiling (S0056); the overflow is split by prot as the kernel does today. `lx` pays any lean loss first. The growth g still runs (recomposition) and is funded from fat.
- **Trained characters and the surplus.** By default a trained character grows at maintenance as the evidence shows (Helms 2023, S1.29; Garthe 2013, S1.30; Antonio 2015, PMID 26500462; Barakat 2020, doi:10.1519/SSC.0000000000000584). `NR.StrengthTrainedNeedsSurplus` (0 by default) scales the gate at balance by (1 − value · s): at 1, a trained character gains little at maintenance and nets lean only through surplus and cut cycles, Angus's premise. No trial compares bulk-cut cycles with maintenance over a year; the bulk-cut recommendation is practitioner consensus (Iraki 2019, S1.32).
- **Not modelled.** Protein's extra energy cost (Antonio 2014, PMID 24834017: no fat gain on +800 kcal of protein) belongs to the energy model, not to the partition.
```

**Edit 10-D, in § 9.1's field table.**

Old:
```
| grace | days below maintenance |
```
New:
```
| grace | days below maintenance |
| lx | the labile lean (water, glycogen, organ): weight only (§ 5.1) |
```

**Edit 10-E, in § 9.2.**

Old:
```
- the resistance side of `NR_Kernel_Training`;
```
New:
```
- the resistance side of `NR_Kernel_Training`; the deficit protection's dose input `dStr` becomes T = min(1, S/10) from the § 4 signal;
- `K.partition.leanGain`, `headroom`, `gEnergy`, `G0`, `LM_CAP_RATIO`, `P_LO`, `P_HI`, `SURPLUS_RAMP` and `DEFICIT_HALF*` (§ 5.1 replaces them); `gAlc` stays, as a factor on g (§ 5);
```

---

## Findings by severity

Each finding gives its evidence and an exact spec edit. Old text is quoted from the spec as it stands.

### Critical

**C1. At level 10, native XP pinned at the level's start equals the cap, so the training signal stops.**

- **Evidence.** `AddXP` returns at `@198–@221` when `amount ≥ 0 and xp ≥ totalXpForLevel(10)`, before the Lua event at `@1346–@1364` (`docs/facts/perks-and-strength.md:70-82`, #2109, #2125). The event also passes the clamped change made (`@824–@861`).
- **Consequence.** With XP at 487 500 every grant is dropped, so S reads 0. After 14 days the character detrains from the top. Below level 10, a fractional bar near the next total also clips the day's grants.
- **The fix has a precedent.** BeyondTen parks a level-10 perk's XP at the level-9 total (337 500) and wraps the rust level check so it never loses the level (#2850, #2856; `docs/facts/other-mods/beyondten.md:37,73`).
- **In-day crossings at low levels.** Levels 0→1 cost 1500 XP, about 4 exhaustion sets, so a native `LevelPerk` can fire mid-day and swap the band traits until day close.

Spec edit, § 7, first bullet. Old:
```
- **floor(L) ≤ 10:** if the native Strength level differs, the server sets it and pins native XP at that level's starting total.
```
New:
```
- **floor(L) ≤ 9:** if the native Strength level differs, the server sets it and pins native XP at that level's starting total plus the fraction toward the next level (the bar); the `AddXP` listener re-pins at once when a grant crosses a level total (event-driven, no tick work).
- **floor(L) ≥ 10:** native level 10, with native XP parked at the level-9 total (337 500), so the `AddXP` event keeps firing with the full amount (vanilla returns before the event once XP reaches the level-10 total, #2109); the vanilla ten-minute level check is guarded so the parked XP never loses the level, as BeyondTen does (#2850, #2856). A Task 0 check confirms grants at level 10 reach the listener at full size.
```

**C2. The growth law duplicates the partition's lean arm, and the deficit protection loses its input.**

- **Evidence.** `NR_Kernel_Partition.lua:26-96` (G0 0.05 kg/d, LM_CAP_RATIO, gProt 0 at 0.8 g/kg, gEnergy 0 at balance, DEFICIT_HALF). `NR_Server_Metabolism.lua:308-310` feeds `dStr` and `dHyp` from `K.training.doses`, which § 9.2 removes.
- **Consequence.** If both arms run, F grows twice. If the resistance side goes, the deficit protection (`PROT_STR · dStr`) silently drops to 0. The energy gate would double-penalise a deficit: § 5's f_e closes growth, while the partition's deficit arm pays lean on top. Both are intended, but only as § 5.1 defines them.
- **Edit.** Item 10's edits 10-C and 10-E.

**C3. `NR_Server_Weight` re-applies vanilla's kilogram bands every minute and will overwrite § 8.**

- **Evidence.** `NR_Server_Weight.lua:137-150` calls `applyTraitFromWeight` on a band change and as a repair. `K.body.band` uses 50/65/75/85/100 kg (`NR_Kernel_Body.lua:84-101`; `docs/facts/body-and-weight.md:293-305`).
- **Consequence.** The spec's default character is 60.5 kg (65.0 kg under M1), which reads Very Underweight (50–65 kg) or Underweight (65–75 kg) in vanilla terms. The repair arm would add those traits back every minute against § 8's day-close write.

Spec edit, § 8.1, the "Writes" bullet. Old:
```
- **Writes:** server-side through `getCharacterTraits():add/remove` (wall map G3).
```
New:
```
- **Writes:** server-side through `getCharacterTraits():add/remove` (wall map G3), followed by the trait push (`NR.pushTraits`, #2099, #2603). `NR_Server_Weight`'s band refresh and repair through `applyTraitFromWeight` (vanilla's 65/75/85/100 kg bands) are removed: the § 8 axes own the five band traits. The engine's own refresh does not run while `Nutrition = false` (#2644).
```

**C4. The partition is unspecified.** See item 10. This is counted Critical because the realism goal ("untrained can recomp; a deficit costs lean without protein or training") cannot be met by § 5 alone.

**C5. "Offered at their vanilla costs" makes the four fat and thin traits invisible.**

- **Evidence.** Obese, Overweight, Underweight and Very Underweight all ship `Cost = 0` (trait-levers § 1.3). The creation lists admit only `cost > 0` to the good list or `cost < 0` to the bad list (`CharacterCreationProfession.lua:901, :912`). A cost-0 trait that is not free can only appear through the re-add leak (trait-levers § 3.5).

Spec edit, § 3.1, first paragraph. Old:
```
The creation screen offers 8 body traits at their vanilla costs: Weak, Feeble, Stout and Strong (muscle), Overweight and Obese (fat), and Underweight and Very Underweight (thin). Emaciated is reached only in play.
```
New:
```
The creation screen offers 8 body traits: Weak, Feeble, Stout and Strong (muscle) at their vanilla costs, and Overweight and Obese (fat) and Underweight and Very Underweight (thin) at costs the mod sets, because vanilla gives those four `Cost = 0` and the creation lists show only a positive or a negative cost (trait-levers § 1.3). Proposed: Overweight −6 and Obese −10, Underweight −6 and Very Underweight −10 (a game choice mirroring Feeble and Weak; Angus to confirm). Emaciated is reached only in play.
```

**C6. The signal is contaminated by vanilla's protein multiplier and the sandbox XP multiplier.**

- **Evidence.** The `AddXP` event carries the amount after protein ×1.5 (store 50–300) or ×0.7 (below −300) (#2112). It was measured live: a push-up rep fires at 4.2 = 6 × 0.7 (#2900). The amount is also after the sandbox `Global` multiplier (vanilla-strength-rate § 2).
- **Consequence.** The legacy mirror maps protein above about 1.07 g/kg into the ×1.5 arm (`NR_Kernel_Body.lua:125-137`). A character at 1.6 g/kg therefore counts 1.5× the sets **and** gets f_p = 1: protein is counted twice, and an XP-multiplier server multiplies S.

Spec edit, § 4, the Capture bullet. Old:
```
- **Capture.** A server `AddXP` listener adds every Strength gain (exercise, carrying, melee) into today's slot of a 7-slot daily ring.
```
New:
```
- **Capture.** A server `AddXP` listener adds every positive Strength gain into today's slot of a 7-slot daily ring, after dividing out vanilla's multipliers: the protein factor the engine applied (×1.5 when 50 < proteins < 300, ×0.7 below −300; #2112, measured #2900) and the sandbox XP multiplier (`Global` under `GlobalToggle`, else the per-perk Strength value), so protein enters only through f_p and the XP sandbox does not scale biology.
- **Source weights.** A grant made while an `ISFitnessAction` runs counts 1; any other grant (melee hits, carrying, trees, barricades) counts `NR.StrengthIncidentalWeight` (default 0.35). Basis: hypertrophy rises with proximity to failure (H.11, H.12), indirect work counts fractionally (H.1). Without it, a survivor's incidental XP (about 500 a game day on the 90-minute day, vanilla-strength-rate § 4) reads about 10 sets a week and drives a never-trained character to level 14.4 in 10 years (sim, S = 10).
```

### Major

**M1. The fat traits on male percent cuts don't match a sex-neutral lean.**

At F = 52.0 kg, the male cuts 8 / 20 / 25 % fall at BMI 19.6 / 22.5 / 24.0 (`creation.py`). As written:
- an Overweight pick (High band midpoint, 22.5 %) is BMI 23.2;
- an Obese pick is BMI 25.7, taking 30 % for the open-ended band;
- the Very high band has no top, so "its middle" is undefined.

The fix is fat-mass-index bands, which are height-normalised and independent of lean, so they suit a sex-neutral FFMI. Kelly 2009 (NHANES DXA, PMID 19753111; Table 3 text: overweight FMI > 6 men / > 9 women, obese ≥ 9 / ≥ 13). The male cuts by default follow Angus's sex ruling; the female cuts apply under `NR.SexSpecific`. The lower normal bound of 3 for men was not read from Table 4, which did not render; it is marked unverified.

The proposed creation bodies:

| Pick | Weight | BMI | % fat | FMI |
|---|---|---|---|---|
| No trait (FMI 4.5, the middle of normal) | 65.0 kg | 22.5 | 20 % | 4.5 |
| Overweight (FMI 7.5) | 73.7 kg | 25.5 | 29 % | 7.5 |
| Obese (FMI 12.5) | 88.2 kg | 30.5 | 41 % | 12.5 |

The panel's Body fat word may keep the percent table.

Spec edit, § 3.2 table, rows "none", "Overweight", "Obese". Old:
```
| none | level 5 | level 16.5 | the start | the middle of the Healthy band |
```
New:
```
| none | level 5 | level 16.5 | the start | FMI 4.5 kg/m² (13.0 kg at 1.70 m; the middle of Kelly 2009's male normal 3–6): 65.0 kg, BMI 22.5, 20 % fat |
```
Old:
```
| Overweight | unchanged | unchanged | — | the middle of the High band |
| Obese | unchanged | unchanged | — | the middle of the Very high band |
```
New:
```
| Overweight | unchanged | unchanged | — | FMI 7.5 (21.7 kg): 73.7 kg, BMI 25.5 |
| Obese | unchanged | unchanged | — | FMI 12.5 (36.1 kg): 88.2 kg, BMI 30.5 |
```

And § 8, the Fat load row. Old:
```
| Fat load | body-fat % in the sex-neutral bands of § 8.1 | Overweight at High, Obese at Very high |
```
New:
```
| Fat load | fat-mass index (fat kg / H²), Kelly 2009 (PMID 19753111) cuts through the effective sex (§ 14): male overweight > 6, obese ≥ 9 | Overweight above 6, Obese at 9 or more |
```

**M2. Two heights, which make the thin picks near-lethal at creation.**

- **Evidence.** `K.acute.HEIGHT_M = 1.75` (`NR_Kernel_Acute.lua:150`) feeds the BMI of the PE grade and the lethal checks. The spec uses 1.70.
- **Consequence.** Very Underweight at BMI 16.5 at 1.70 reads 15.6 at 1.75: PE grade 4 at creation (`NR_Kernel_Effects.lua:291-300`). At 5 % fat it sits 1 point above the starvation-lethal floor of 4 % (`K.effects.BF_FLOOR`, open S1167), which a deficit day under Alpert's ceiling (2.4 kg fat → 165 kcal/day) reaches fast.

Spec edit, § 2. Old:
```
FFMI  = F / H²                         H = 1.70 m, fixed, sex-neutral
```
New:
```
FFMI  = F / H²                         H = 1.70 m, fixed, sex-neutral; one shared constant, which K.acute.HEIGHT_M (1.75 today) also reads, so every BMI in the mod uses 1.70
```

§ 3.2 table, thin rows. Old:
```
| Underweight | lowered to reach BMI 18.0 at the Very lean fat | unchanged | the muscle pick's level | the Very lean band |
| Very Underweight | lowered to reach BMI 16.5 at the Very lean fat | unchanged | the muscle pick's level | the Very lean band |
```
New:
```
| Underweight | lowered to reach BMI 18.0 at FMI 1.5 (4.3 kg, 8 % fat; Gallagher's male fat at BMI 18 is about 7 %, S1905 equation) | unchanged | the muscle pick's level | FMI 1.5 |
| Very Underweight | lowered to reach BMI 16.5 at FMI 1.0 (2.9 kg, 6 % fat), above the 4 % starvation floor | unchanged | the muscle pick's level | FMI 1.0 |
```
With no muscle pick, Underweight starts at level 2.0 and Very Underweight at level 0.0. A Very Underweight start at about Strength 0 is realistic: Minnesota men ended semistarvation near 5–6 % fat at about that thinness.

**M3. Detraining erases multi-year gains in months.**

- **The size of the loss.** A 6-week half-life on all of F − F₀ means a year-3 lifter (level 13.7) keeps 79 % at 4 wk, 31 % at 12 wk and 8 % at 24 wk. After 26 weeks off, a 5-year lifter falls from 15.0 to 5.6 (`scenarios.txt`, spec and C).
- **Why it is wrong.** S1.24 says detraining follows the training time course. The 4.9–9.2-week half-life is Räntilä's 10-week novices (H.51). No data cover advanced lifters (H.64, H.68).
- **The proposal.** Scale the half-life with status: 6 wk × (1 + 2s). The novice oracles are unchanged (`rescore.txt`: Räntilä kept 0.43). A year-3 lifter keeps 91 / 59 / 25 % at 4 / 12 / 24 wk (`detrain_alt.txt`). It is unidentified by the evidence, so it is a game choice.

Spec edit, § 6. Old:
```
- **Detraining:** `dF/dt = −λ · (F − F₀) · (1 − S/S_m)`, with λ = ln 2 / 6 weeks (Räntilä 2025: 4.9–9.2 weeks). It acts only while F > F₀.
```
New:
```
- **Detraining:** `dF/dt = −λ(s) · (F − F₀) · (1 − S/S_m)`, with λ(s) = ln 2 / (6 weeks · (1 + 2s)): 6 weeks for a novice (Räntilä 2025, H.51: 4.9–9.2 weeks), 18 weeks at the cap. The status term is a game choice resting on S1.24 (loss follows the build's time course); no study measures advanced detraining (H.64, H.68). It acts only while F > F₀, and is integrated exactly per closed day (F − F₀ multiplied by exp(−λ·Δt)), so no time scale overshoots F₀.
```

**M4. Regain carries no protein or energy gate, so a starving character regains muscle.**

- **Evidence.** In the spec's § 6 regain term, only min(1, G) multiplies. The hypertrophy report's own form carries f_p·f_e (hypertrophy-science-report § e).

Spec edit, § 6. Old:
```
- **Regain:** while F < P, dF/dt = max(the § 5 growth, λ_r · (P − F) · min(1, G)), with λ_r = ln 2 / 6 weeks.
```
New:
```
- **Regain:** while F < P, dF/dt = max(the § 5 growth, λ_r · (P − F) · min(1, G) · f_p · f_e), with λ_r = ln 2 / 6 weeks. The max form reproduces Räntilä's equal second block (0.96 of the first under point R; the sum form overshoots and is not used).
```

**M5. The time scale's meaning is undefined.**

The spec does not say which rates `NR.StrengthTimeScale` multiplies, or whether S is counted per game week or per biological week. The recommended reading:
- it multiplies the per-day rates of growth, detraining, regain and peak decay;
- it divides the grace days;
- **it never rescales S.** Training is real-time paced (vanilla-strength-rate § 4), so a player cannot train more per game day on a compressed clock.

Spec edit, § 10 table. Old:
```
| `NR.StrengthTimeScale` (the biology clock: 1.0 means one game day is one real day) | 1.0 |
```
New:
```
| `NR.StrengthTimeScale` (the biology clock: 1.0 means one game day is one biological day): multiplies the per-day growth, detraining, regain and peak-decay rates and divides the grace days; S stays the ring's sets per 7 game days, unscaled | 1.0 |
```

**M6. G's denominator hardcodes S_g0 = 1, and option combinations can make the anchor unreachable.**

- **The denominator.** With S_g0 as an option, (√12 − 1) must become (√12 − √S_g0).
- **The anchor.** Under the fitted cap, S_g0 = 1.3 with β = 3 has no k that reaches level 15 (`fit_C.txt`, profile). Generally the anchor fails when S_g0·e^(β·0.87) ≥ S_max(0.87).

Spec edit, § 5. Old:
```
G      = max(0, √min(S, S_max) − √S_g(s)) / (√12 − 1)       the signal's response
```
New:
```
S_max(s) = S_max0 − (S_max0 − S_max1) · s                    the set cap falls with status (H.3, H.5, H.6)
G      = max(0, √min(S, S_max(s)) − √S_g(s)) / (√S_ref − √S_g0)   the signal's response; S_ref = 12 (H.1)
```

And § 10 gains a guard sentence after the table:
```
At load the options are checked: if S_g0 · e^(0.87β) ≥ S_max(0.87), level 15 is unreachable at any rate; the server logs the combination and falls back to the defaults for β, S_g0 and S_max1.
```

**M7. The year-1 cost line is stale.**

The controller's sim and this review agree: the five-year shape gives +7.25 kg in year 1 under the spec's constants, and +7.82 under R, inside the literature's 6.8–8.5.

Spec edit, § 5 table, the k row. Old:
```
A headroom-only sketch gave about 1.4 years to level 10 and about 5.5 kg in year 1, against the literature calibration's 7.2 kg |
```
New:
```
Fitted: k = 0.00991 per week (point R; 0.00874 under the draft's β 2.5, S_g0 1, flat set cap). The average character then reaches level 10 in 0.89 years and gains 7.8, 3.5, 1.7, 0.9 and 0.6 kg in years 1-5, against McDonald scaled ×0.75 (S1.15) of 6.8–8.5, 3.4–4.1, 1.7–2.0 and 0.7–1.0 |
```

§ 11, the Curve ruling. Old:
```
cost if wrong: year 1 is slower than the studies by about 1.7 kg.
```
New:
```
cost if wrong: none measured; the fitted curve's year 1 (7.8 kg) sits inside the literature calibration (6.8–8.5 kg).
```

**M8. `NR.StrengthXPPerSet` has no default, but a `double` option must ship one.**

- **Evidence.** The pattern in `42.21/media/sandbox-options.txt` has every double option declaring a default.
- **The value.** Vanilla-strength-rate § 4 gives one push-up exhaustion bout at about 346 XP (58 reps × 6) before protein.

Spec edit, § 4, Conversion bullet. Old:
```
Until then it carries no default and the kernel tests use a placeholder.
```
New:
```
Until then it ships the provisional default 346 (one push-up bout from full endurance to the 0.25 stop, before vanilla's protein factor; vanilla-strength-rate § 4), which the calibration run replaces; the calibration reads push-ups with the protein factor divided out.
```

**M9. The trained plateau.** The fit puts the trained set cap at 12 sets. That bridges Pelland (H.1) and the advanced trials (H.3, H.5, H.6). Adopt S_max1 = 12 (edit M6), and add the option (table below).

**M10. The removals miss three dependants.**

- `K.body.split` is the heal and store fallback (`NR_Kernel_Heal.lua:43`, `NR_Kernel_Store.lua:190`).
- `lm0dis` is the disuse curve's own anchor, the lean at the start of immobilisation (`NR_Server_Metabolism.lua:303`), not a set point, so F₀ cannot replace it.
- `body.r` (the responder constant) is unaddressed.

Spec edit, § 9.2. Old:
```
- `K.body.split` and its build offsets;
- `lm0`/`lm0dis` where F0 replaces them.
```
New:
```
- `K.body.split` and its build offsets; the heal and store fallbacks that call it (`NR_Kernel_Heal`, `NR_Kernel_Store`) build the § 3.2 no-trait body instead;
- `lm0`, where F0 replaces it; `lm0dis` stays (the disuse arm's own anchor);
- `body.r`, unless the plan keeps a per-character responsiveness factor (H.25, H.28, H.29), in which case it multiplies k.
```

**M11. Alcohol drops out.** The partition's alcohol gate (`NR_Kernel_Partition.lua:43-45, 81-86`; S0718, S0631) multiplies today's lean gain. The new law must keep it.

Spec edit, § 5. Old:
```
dF/dt  = k · (F_c − F) · G · f_p · f_e                      per week, applied at day close as 1/7
```
New:
```
dF/dt  = k · (F_c − F) · G · f_p · f_e · f_alc              per week, applied at day close as 1/7; f_alc is K.partition.gAlc (0.65 above 0.5 g alcohol/kg/day, S0718, S0631)
```

**M12. The time scale and the half-lives at extreme values.** A daily Euler step overshoots once λ·TimeScale/7 nears 1: TimeScale 30 with a 2-week detraining half-life gives a factor of 1.49. The exact-exponential wording in M3 fixes it, and the option ranges below keep the product bounded.

**M13. The fat traits, in play.** Under FMI bands (M1) the precedence and damping still hold. The margin of "1 percentage point of body fat" becomes 0.3 FMI, about 0.9 kg at 1.70 m.

Spec edit, § 8.1. Old:
```
- **Damping:** a switch needs a margin of 0.5 BMI or 1 percentage point of body fat past its cut, and switches are checked once a day.
```
New:
```
- **Damping:** a switch needs a margin of 0.5 BMI or 0.3 FMI past its cut, and switches are checked once a day.
```

### Minor

**m1. The § numbering jumps from 12 to 14.** Renumber "## 14. The mod-wide sex option" as "## 13." and "## 15. Out of scope" as "## 14.", and update the three "§ 14" references (§ 8.1 line 139, the § 10 table line 207 and the § 11 ruling line 219) to "§ 13". The § 3.2 line edited in m2 already cites § 13.

**m2. Two lines still call the fat bands sex-neutral,** though § 8.1 reads them through the effective sex.

§ 3.2. Old:
```
   - **Fat bands** are one sex-neutral table (§ 8.1).
```
New:
```
   - **Fat bands** are read through the character's effective sex (§ 8.1, § 13): the male cuts unless `NR.SexSpecific` is on.
```

§ 8.1. Old:
```
The traits and the panel's Body fat word read the mod's existing `K.view.FAT_CUTS_*` through the character's effective sex (§ 14), so by default every character reads the male table:
```
New:
```
The panel's Body fat word reads the mod's existing `K.view.FAT_CUTS_*`, and the fat traits read the FMI cuts of § 8, both through the character's effective sex (§ 13), so by default every character reads the male values:
```

**m3. The Kouri basis needs its height.** 25.0 is normalised to 1.80 m (S1.1: FFMI + 6.3 × (1.80 − h)), so at 1.70 m the equivalent raw FFMI is 24.37. Strong's cap of 18.5 (FFMI 24.75) sits about 1 kg above it, inside the soft limit (S1.4: 26 % of football players exceed 25).

§ 2. Old:
```
- The untrained natural cap is level 16.5 (FFMI 23.75), under the about-25 natural limit (Kouri; first harvest).
```
New:
```
- The untrained natural cap is level 16.5 (FFMI 23.75), under Kouri's natural limit of 25.0 normalised to 1.80 m, which is 24.37 raw at 1.70 m (S1.1); Strong's cap, 18.5 (24.75), sits just above it, inside the soft limit (S1.4).
```

**m4. Two kernel tests depend on the constants.** Under R, Feeble reaches only 14.79 in 10 years.

§ 12.1. Old:
```
- the curve: on 20 sets with full gates, an average character reaches level 15 at 5 years; Weak never reaches 15; Feeble reaches it later than the average; Stout and Strong reach it sooner;
```
New:
```
- the curve: on 20 sets with full gates, an average character reaches level 15 at 5 years; Weak never reaches 15; Feeble is below the average at every year; Stout and Strong reach 15 sooner;
```

**m5. Weak gains the most absolute lean in year 1** (+9.5 kg against the average's +7.8 under R), because the half-offset cap rule gives it the most headroom. Relative gains are similar across people (S0589). This is noted as a consequence of Angus's cap rule, not a change.

**m6. `NR.StrengthMaintainShare` "1/3" is not a valid double literal.** Write 0.333 (edit in the options table below).

**m7. m, the regain half-life and the labile-lean cap are unidentified by any oracle** (the stability probe reads flat). They keep their game-choice defaults and are labelled so in the spec's table:
- m = ⅓ (Bickel H.13, as a ratio of the growth threshold, H.64 open);
- λ_r = 6 wk (H.52, H.53 between);
- the labile-lean cap 0.05·F (Bray's 2.9 kg ≈ 5 % of FFM).

**m8. The XP-per-set calibration should name the exercise and the protein state.** Push-ups are 6 XP a rep and burpees 4 (vanilla-strength-rate § 3a). § 12.2. Old:
```
- **The XP-per-set calibration run:** one Fitness set to exhaustion, its Strength XP logged against wall time.
```
New:
```
- **The XP-per-set calibration run:** one push-up set from full endurance to the 0.25 stop, at a protein store between −300 and 50 (factor 1), its Strength XP logged against wall time.
```

**m9. A Weak pick sits on the Underweight cut.** Under the draft's 14 % fat it is BMI 18.02, right on the cut less the margin (18.0), so it would flicker. The FMI default (M1) moves it to BMI 20.0.

**m10. Out of scope, recorded so the plan does not re-ask.**
- **Age:** PZ has no age stat, though the evidence would support an older-adult maintenance rise (H.13).
- **Sleep's effect on synthesis:** not harvested.
- **Illness:** not harvested.
- **The per-meal window:** none, which is correct (Trommelen H.38).
- **The energy cost of lean:** already in REE (`NR_Kernel_Energy.lua:263` reads `body.lm`; S0011, 13 kcal/kg/d, about 190 kcal/d across the cap).

---

## Answers to the brief's checks not covered above

**1. Constants.** Every § 5–6 constant now cites a fitted value or a named game choice (the table below).
- f_p's knots stand: S0591, S0592, H.40 and S0509 are read correctly.
- S_max 30 is a game choice at Pelland's thin top (H.1), correctly labelled.
- **β 2.5 → 3.0, fitted.** Its basis stays indirect (H.26, H.27, H.17, H.24), against H.5 and H.25.

**2. Trajectories (point R, `scenarios_R.txt`).**

Levels at years 1–10 on 20 sets:

| Pick | Years 1–10 | To L10 | To L15 |
|---|---|---|---|
| Weak | 6.59, 9.50, 10.89, 11.68, 12.17, 12.51, 12.76, 12.95, 13.09, 13.21 | 2.29 y | never |
| Feeble | 8.89 … 14.79 | 1.34 y | none in 10 y |
| No trait | 10.41, 12.81, 13.95, 14.59, 15.00, 15.28 … 15.85 | 0.89 y | 5.0 y |
| Stout | — | 0.50 y | 2.79 y |
| Strong | — | 0.16 y | 1.69 y |

- **Year-by-year kg (average):** 7.82, 3.47, 1.65, 0.92, 0.59.
- **Low-volume stalls** (level at year 10): S 3 → 11.30, S 6 → 13.64, S 10 → 15.08, S 30 → 15.86.
- **Detraining from year 3** with the status term: 91 / 59 / 25 % kept at 4 / 12 / 24 wk.
- **Regain after 26 weeks off:**
  - novice (1 yr): 10.41 → 5.75, with 90 % of the loss back in 26 wk;
  - advanced (5 yr): 15.0 → 7.35, with 80 % back in about 27 wk and 90 % in 66 wk.

  The advanced 90 % is slow because P decays over the gap. Human data stop at 20 weeks (H.68).

**3–4. The creation body and the thin picks.** M1 and M2. With no trait, the draft gives 60.5 kg, BMI 20.9, 14 % fat. The proposal is 65.0 kg, BMI 22.5, 20 % fat. Vanilla's 80 kg is BMI 27.7 at 1.70 m, overweight.

**5. The kernel overlap.** C2 and item 10.

**6. The traits.** WHO cuts at a fixed height are fine once the height is unified (M2). The fat cuts, damping, precedence and Emaciated-in-play are covered in M1, M13 and § 8.

**7. Missing realism.**
- **Alcohol:** M11.
- **Injury and disuse:** keep the partition's disuse arm and `lm0dis`, M10.
- **Overfeeding's lean share:** item 10.
- **The rest:** out of scope, m10.

**8. Composition of the multipliers.** C6, M5 and M12. The XP multiplier is divided out of S; the time scale does not touch S; and k is exposed as a multiplier on the fitted value (below), so an operator never sets a raw k that the other options have invalidated.

**9. Consistency.** M7, m1, m2 and m4.

---

## Final recommended defaults and sandbox options

Each option follows the `NR.<Name>` pattern of `42.21/media/sandbox-options.txt`. "Fixed" means a kernel constant, not an option.

| Name | Type | Min | Max | Default | Basis |
|---|---|---|---|---|---|
| H (height) | fixed | — | — | 1.70 m, shared with K.acute | ruling; M2 |
| `NR.StrengthTimeScale` | double | 0.25 | 30 | 1.0 | ruling; OnsetSpeed precedent; M5, M12 |
| `NR.StrengthXPPerSet` | double | 50 | 2000 | 346 (provisional) | vanilla-strength-rate § 4; calibration run |
| `NR.StrengthIncidentalWeight` (new) | double | 0 | 1 | 0.35 | H.1 fractional, H.11, H.12; game choice; C6 |
| `NR.StrengthCapLevel` | double | 12 | 20 | 16.5 | ruling; S1.1, m3 |
| `NR.StrengthTraitCapShare` | double | 0 | 1 | 0.5 | Angus |
| `NR.StrengthRate` (a multiplier on the fitted k = 0.00991/wk) | double | 0.25 | 4 | 1.0 | fit R; anchor |
| `NR.StrengthThreshold` (S_g0, sets/wk) | double | 0.25 | 1.0 | 0.5 | fit (bound reported); H.1, H.8; guarded, M6 |
| `NR.StrengthThresholdRise` (β) | double | 0 | 4 | 3.0 | fit; H.26, H.27, H.17, H.24 (against H.5, H.25); guarded |
| S_ref | fixed | — | — | 12 | H.1 |
| S_max0 | fixed | — | — | 30 | H.1 (data thin above 25–30) |
| `NR.StrengthTrainedSetCap` (S_max1, new) | double | 8 | 30 | 12 | fit (bound reported); H.3, H.5, H.6 |
| f_p knots | fixed | — | — | 0 @ 0.4, 0.5 @ 0.8, 0.92 @ 1.3, 1.0 @ 1.6 g/kg | S0591, S0592, H.40, S0509 |
| `NR.StrengthProteinFull` (scales the knots) | double | 1.0 | 3.0 | 1.6 | S0591, S0592 |
| `NR.StrengthDeficitZero` (E₀) | double | −2000 | −200 | −800 | fit R (C −1000 at bound); S1.28, S0064, Garthe 2011 |
| `NR.StrengthNoviceDeficitDepth` (a_nov, new) | double | 0 | 3 | 1.4 | fit R (C 2.8 at bound); S0064 |
| `NR.StrengthBalanceGate` (f_bal, new) | double | 0.5 | 1.0 | 0.85 | fit; S1.29, S1.30 |
| surplus_full | fixed | — | — | +5 % of TDEE | S1.29 (5 % = 15 % for muscle); flat in the fit |
| `NR.StrengthTrainedNeedsSurplus` (new) | double | 0 | 1 | 0 | evidence default; 1 = Angus's premise (item 10) |
| forbes c | fixed | — | — | 10.4 kg | S0054, S0055 (S1056 open) |
| `NR.LeanLossTrainingProtect` (wT, new) | double | 0 | 0.9 | 0.35 | fit; S0072, H.47, S0609 |
| `NR.LeanLossProteinProtect` (wP, new) | double | 0 | 0.9 | 0.6 | fit R (C 0.75 at bound); Mettler 2010, Pasiakos 2013, S0599 |
| prot floor | fixed | — | — | 0.10 | fit R (C 0.05 at bound) |
| protein full protection p_hi | fixed | — | — | 2.0 g/kg | fit R; S0599 (2.3–3.1 g/kg FFM), S0064 |
| labile-lean cap / decay | fixed | — | — | 0.05·F / 28 d | S0605 (game choice, H.67) |
| `NR.StrengthMaintainShare` | double | 0.1 | 1.0 | 0.333 | H.13, S0616 (unidentified; H.64 open) |
| `NR.StrengthGraceDays` | integer | 0 | 60 | 14 | S1.18, S1.26, H.16 |
| `NR.StrengthDetrainHalfLifeWeeks` | double | 2 | 26 | 6 | H.51 |
| `NR.StrengthDetrainStatusSlowing` (new) | double | 0 | 4 | 2.0 | S1.24 (game choice; H.64, H.68) |
| `NR.StrengthRegainHalfLifeWeeks` | double | 1 | 26 | 6 | H.52, H.53 (unidentified) |
| `NR.StrengthPeakHalfLifeYears` | double | 0.25 | 20 | 2 | H.54, H.60, S0620, H.57 |
| `NR.SexSpecific` | boolean | — | — | false | Angus |

The old `NR.StrengthDeficitZero` default of −500 is replaced; Murphy & Koehler's −500 is met as the net of growth and loss.

Pointless or dangerous options:
- **A raw `NR.StrengthRate` = k.** Its meaning shifts with β, S_g0 and S_max1, so expose a multiplier instead.
- **`NR.StrengthThreshold` above about 1.0 at β 3.** The anchor becomes unreachable (M6 guard).
- **TimeScale above about 7 with a daily Euler step.** It overshoots (M12: integrate exactly).
- **`NR.StrengthMaintainShare` 0.** Detraining never runs, which may be intended. Allowed, but say so in the option's tooltip.

---

## Simulation outputs relied on

The controller's `sim_strength.py`, re-run unchanged:
```
k/week 0.00874
Weak yrs1-10 [6.1, 9.01, 10.59, 11.54, 12.17, 12.6, 12.91, 13.14, 13.31, 13.44]
Feeble yrs1-10 [8.45, 11.04, 12.45, 13.31, 13.86, 14.25, 14.52, 14.73, 14.88, 15.0]
none yrs1-10 [10.01, 12.4, 13.7, 14.48, 15.0, 15.35, 15.6, 15.79, 15.93, 16.04]
Stout yrs1-10 [11.58, 13.76, 14.94, 15.66, 16.13, 16.45, 16.68, 16.85, 16.98, 17.08]
Strong yrs1-10 [13.14, 15.11, 16.18, 16.83, 17.26, 17.55, 17.76, 17.91, 18.03, 18.12]
year1 kg neutral 7.24
S 3 neutral 10y 9.67 y1kg 1.89
S 6 neutral 10y 12.55 y1kg 3.54
S 10 neutral 10y 14.41 y1kg 4.99
S 20 neutral 10y 16.04 y1kg 7.24
S 30 neutral 10y 16.39 y1kg 8.68
```

The appendices below are pasted from the scratchpad files named above.

### Appendix 1: fit C (constrained best), `fit_C.txt` (the oracle, profile, stability and bound lines; the FITTED line truncated)
```
variant C candidates per round 1541
start score 6.6113
round 1 group growth   score 3.9145  {'beta': 3.0, 'Sg0': 0.5, 'Smax1': 12.0}
round 1 group energy   score 1.3959  {'E0': -1000.0, 'fe_bal': 0.85, 'a_nov': 2.8, 'surplus_full': 0.1}
round 1 group deficit  score 0.4018  {'wT': 0.35, 'wP': 0.75, 'prot_floor': 0.05, 'pdef_hi': 1.6}
round 1 group memory   score 0.4018  {'detrain_hl_wk': 6.0, 'regain_hl_wk': 6.0, 'm': 0.3333333333333333, 'grace_d': 14, 'regain_sum': False}
round 2 group growth   score 0.4018  {'beta': 3.0, 'Sg0': 0.5, 'Smax1': 12.0}
round 2 group energy   score 0.4018  {'E0': -1000.0, 'fe_bal': 0.85, 'a_nov': 2.8, 'surplus_full': 0.1}
round 2 group deficit  score 0.4018  {'wT': 0.35, 'wP': 0.75, 'prot_floor': 0.05, 'pdef_hi': 1.6}
round 2 group memory   score 0.4018  {'detrain_hl_wk': 6.0, 'regain_hl_wk': 6.0, 'm': 0.3333333333333333, 'grace_d': 14, 'regain_sum': False}
evaluated 3082 best 0.4018
FITTED {"k": 0.009906, "beta": 3.0, "Sg0": 0.5, "Sref": 12.0, "Smax": 30.0, "Smax1": 12.0, "E0": -1000.0, "fe_bal": 0.85, "surplus_full": 0.1, "a_nov": 2.8, "trained_need": 0.0, "forbes_c": 10.4, "wT": 0.35, "S_def": 10.0, "wP": 0.75, "pdef_lo": 0.8, "pdef_hi"
ORACLE year1_kg_20sets               7.4361 [  6.800,  8.500] miss 0.000 w1  S1.15 McDonald x0.75 (first-harvest calibration)
ORACLE yr2_over_yr1                  0.4685 [  0.400,  0.600] miss 0.000 w1  S1.15 halving; H.49/H.50 year-1 dominance
ORACLE yr3_over_yr2                  0.4941 [  0.400,  0.650] miss 0.000 w1  S1.15 halving
ORACLE benito_10wk_kg                1.2713 [  1.120,  1.960] miss 0.000 w1  S1.9 Benito 2020 untrained FFM +1.54 (CI 1.12-1.96)
ORACLE pelland_30_over_12            1.6363 [  1.550,  2.000] miss 0.000 w1  H.1 Pelland sqrt fit, derived 1.77
ORACLE h8_3_over_9                   0.4580 [  0.500,  0.900] miss 0.105 w1  H.8 1 vs 3 sets: +3.7 vs +5.2 % (0.71)
ORACLE aube_24_over_12               1.4437 [  0.700,  1.400] miss 0.062 w1  H.5 Aube 2022 advanced: 12=18=24 sets
ORACLE longland_hp_lean              0.4536 [  0.600,  1.800] miss 0.122 w1  S0064 Longland 2.4 g/kg -40 %: +1.2 +/- 1.0 kg
ORACLE longland_lp_lean             -0.3245 [ -0.400,  0.600] miss 0.000 w1  S0064 Longland 1.2 g/kg: +0.1 +/- 1.0 kg
ORACLE longland_hp_fat              -3.6462 [ -5.000, -3.000] miss 0.000 w0  S0064 fat -4.8 +/- 1.6 kg (energy side; report)
ORACLE garthe11_slow_lean            0.4286 [  0.800,  1.800] miss 0.371 w1  Garthe 2011 (PMID 21558571) -19 %: LBM +2.1 %
ORACLE garthe11_fast_lean            0.0585 [ -0.600,  0.400] miss 0.000 w1  Garthe 2011 -30 %: LBM -0.2 %
ORACLE mk_minus500_lean              0.1757 [ -0.300,  0.300] miss 0.000 w1  S1.28 Murphy & Koehler: -500 kcal/d -> no lean gain
ORACLE trained_maint_8wk             0.4628 [  0.100,  1.500] miss 0.000 w1  Helms 2023 MAIN; Antonio 2015 (PMID 26500462) FFM +1.5
ORACLE trained_maint_premise         0.4628 [ -0.100,  0.100] miss 1.814 w0  Angus premise: trained ~0 at maintenance
ORACLE helms23_15pct_over_maint      1.1680 [  0.800,  1.600] miss 0.000 w1  S1.29 Helms 2023: no MT difference by surplus
ORACLE garthe13_lean_ratio           1.0758 [  0.800,  1.350] miss 0.000 w1  S1.30 Garthe 2013: LBM gain not different
ORACLE garthe13_fat_diff             3.3225 [  0.800,  2.500] miss 0.484 w1  S1.30 Garthe 2013: FM +15 % vs +3 %
ORACLE mettler_lp_share              0.5482 [  0.350,  0.700] miss 0.000 w1  Mettler 2010 (PMID 19927027) 1.0 g/kg: 1.6 of 3.0 kg lean
ORACLE mettler_hp_share              0.0826 [  0.050,  0.350] miss 0.000 w1  Mettler 2010 2.3 g/kg: 0.3 of 1.5 kg lean
ORACLE quarter_rule_share            0.2200 [  0.150,  0.350] miss 0.000 w1  Heymsfield 2014 (PMID 24447775); S0072 Weinheimer
ORACLE pasiakos_0.8_minus_1.6        0.2438 [  0.100,  0.500] miss 0.000 w1  Pasiakos 2013 (PMID 23739654) direction (abstract)
ORACLE bray_15pct_lean               2.4068 [  1.500,  3.500] miss 0.000 w1  S0605 Bray 2012: lean +2.87 kg at 15 % protein
ORACLE bray_5pct_lean                0.0000 [ -0.700,  0.500] miss 0.000 w1  S0605 Bray 2012: no lean gain at 5 %
ORACLE bray_muscle_no_signal         0.0000 [ -0.050,  0.050] miss 0.000 w1  H.41/H.42/S0606: no muscle without the signal
ORACLE rantila_kept_frac             0.3938 [  0.240,  0.470] miss 0.000 w1  H.51 Räntilä 2025: 24-47 % kept after 10 wk off
ORACLE rantila_block2_over_1         0.9619 [  0.800,  1.250] miss 0.000 w1  H.51 Räntilä: block 2 = block 1
ORACLE bickel_third_kept             1.7269 [  0.850,  1.800] miss 0.000 w1  H.13 Bickel 2011: 1/3 dose kept size 32 wk
ORACLE bickel_ninth_kept             1.2951 [  0.850,  1.400] miss 0.000 w1  H.13 Bickel 2011: 1/9 dose kept size 32 wk
ORACLE detrain_halflife_wk           6.0000 [  4.900,  9.200] miss 0.000 w1  H.51 Räntilä derived 4.9-9.2 wk
ORACLE deg_protein_2pct              0.0256 [  0.000, 99.000] miss 0.000 w1  degenerate check: +2 % protein moves lean
ORACLE deg_surplus_2pct              0.0375 [  0.000, 99.000] miss 0.000 w1  degenerate check: +2 % surplus moves lean
ORACLE deg_sets_5pct                 0.0334 [  0.000, 99.000] miss 0.000 w1  degenerate check: +5 % sets moves lean
profile beta           [(1.5, 0.8336), (2.0, 0.6335), (2.5, 0.4756), (3.0, 0.4018), (3.5, 0.5849)]
profile Sg0            [(0.5, 0.4018), (0.7, 0.4698), (0.85, 1.4325), (1.0, 8.4555), (1.3, 1000000.0)]
profile Smax1          [(12.0, 0.4018), (15.0, 0.5784), (20.0, 1.1443), (30.0, 1.4524)]
profile E0             [(-400.0, 1.2077), (-500.0, 0.8724), (-650.0, 0.6016), (-800.0, 0.4838), (-1000.0, 0.4018)]
profile fe_bal         [(0.7, 0.4965), (0.85, 0.4018), (1.0, 1.3397)]
profile a_nov          [(0.0, 0.8132), (0.7, 0.5994), (1.4, 0.4892), (2.1, 0.4351), (2.8, 0.4018)]
profile surplus_full   [(0.03, 0.4091), (0.05, 0.4091), (0.1, 0.4018)]
profile wT             [(0.2, 0.4167), (0.35, 0.4018), (0.5, 0.4293), (0.65, 0.5525)]
profile wP             [(0.3, 1.5096), (0.45, 0.7407), (0.6, 0.4023), (0.75, 0.4018)]
profile prot_floor     [(0.05, 0.4018), (0.1, 0.486), (0.15, 0.5932), (0.3, 1.1293)]
profile pdef_hi        [(1.6, 0.4018), (2.0, 0.4096), (2.4, 0.6598), (2.8, 0.938)]
profile detrain_hl_wk  [(4.9, 0.4019), (6.0, 0.4018), (7.0, 0.4018), (8.0, 0.4165), (9.2, 0.5101)]
profile regain_hl_wk   [(1.0, 0.4018), (2.0, 0.4018), (3.0, 0.4018), (4.0, 0.4018), (6.0, 0.4018), (8.0, 0.4018)]
profile m              [(0.11, 0.4018), (0.2, 0.4018), (0.333, 0.4018), (0.5, 0.4018)]
profile grace_d        [(7, 0.4018), (14, 0.4018), (21, 0.4018), (28, 0.4157)]
profile regain_sum     [(False, 0.4018), (True, 0.4018)]
stab k              base 0.4018  x0.95 -> 0.4272 (24 oracles move)  x1.05 -> 0.3787 (24 move)
stab beta           base 0.4018  x0.95 -> 0.3956 (24 oracles move)  x1.05 -> 0.4182 (24 move)
stab Sg0            base 0.4018  x0.95 -> 0.3959 (24 oracles move)  x1.05 -> 0.4097 (24 move)
stab Smax1          base 0.4018  x0.95 -> 0.3979 (6 oracles move)  x1.05 -> 0.4128 (6 move)
stab E0             base 0.4018  x0.95 -> 0.4175 (6 oracles move)  x1.05 -> 0.3883 (6 move)
stab fe_bal         base 0.4018  x0.95 -> 0.4243 (24 oracles move)  x1.05 -> 0.3815 (24 move)
stab a_nov          base 0.4018  x0.95 -> 0.4075 (5 oracles move)  x1.05 -> 0.3966 (5 move)
stab surplus_full   base 0.4018  x0.95 -> 0.4022 (9 oracles move)  x1.05 -> 0.4015 (9 move)
stab wT             base 0.4018  x0.95 -> 0.4018 (3 oracles move)  x1.05 -> 0.4018 (3 move)
stab wP             base 0.4018  x0.95 -> 0.4018 (5 oracles move)  x1.05 -> 0.4018 (5 move)
stab prot_floor     base 0.4018  x0.95 -> 0.3982 (5 oracles move)  x1.05 -> 0.4055 (5 move)
stab pdef_hi        base 0.4018  x0.95 -> 0.4018 (4 oracles move)  x1.05 -> 0.4018 (5 move)
stab detrain_hl_wk  base 0.4018  x0.95 -> 0.4018 (3 oracles move)  x1.05 -> 0.4018 (3 move)
stab regain_hl_wk   base 0.4018  x0.95 -> 0.4018 (0 oracles move)  x1.05 -> 0.4018 (0 move)  FLAT
stab m              base 0.4018  x0.95 -> 0.4018 (0 oracles move)  x1.05 -> 0.4018 (0 move)  FLAT
stab grace_d        base 0.4018  x0.95 -> 0.4018 (2 oracles move)  x1.05 -> 0.4018 (0 move)
stab forbes_c       base 0.4018  x0.95 -> 0.3997 (11 oracles move)  x1.05 -> 0.4039 (11 move)
stab x_max_frac     base 0.4018  x0.95 -> 0.4018 (0 oracles move)  x1.05 -> 0.4018 (0 move)  FLAT
BOUND Sg0            = 0.5 (grid 0.5..1.3)
BOUND Smax1          = 12.0 (grid 12.0..30.0)
BOUND E0             = -1000.0 (grid -400.0..-1000.0)
BOUND a_nov          = 2.8 (grid 0.0..2.8)
BOUND surplus_full   = 0.1 (grid 0.03..0.1)
BOUND wP             = 0.75 (grid 0.3..0.75)
BOUND prot_floor     = 0.05 (grid 0.05..0.3)
BOUND pdef_hi        = 1.6 (grid 1.6..2.8)
```

### Appendix 2: point R (recommended), `interior.txt`
```
R k 0.00991
R score 0.9050
ORACLE year1_kg_20sets               7.8238 [  6.800,  8.500] miss 0.000 w1  S1.15 McDonald x0.75 (first-harvest calibration)
ORACLE yr2_over_yr1                  0.4416 [  0.400,  0.600] miss 0.000 w1  S1.15 halving; H.49/H.50 year-1 dominance
ORACLE yr3_over_yr2                  0.4773 [  0.400,  0.650] miss 0.000 w1  S1.15 halving
ORACLE benito_10wk_kg                1.2713 [  1.120,  1.960] miss 0.000 w1  S1.9 Benito 2020 untrained FFM +1.54 (CI 1.12-1.96)
ORACLE pelland_30_over_12            1.6295 [  1.550,  2.000] miss 0.000 w1  H.1 Pelland sqrt fit, derived 1.77
ORACLE h8_3_over_9                   0.4589 [  0.500,  0.900] miss 0.103 w1  H.8 1 vs 3 sets: +3.7 vs +5.2 % (0.71)
ORACLE aube_24_over_12               1.4421 [  0.700,  1.400] miss 0.060 w1  H.5 Aube 2022 advanced: 12=18=24 sets
ORACLE longland_hp_lean              0.1691 [  0.600,  1.800] miss 0.359 w1  S0064 Longland 2.4 g/kg -40 %: +1.2 +/- 1.0 kg
ORACLE longland_lp_lean             -0.5566 [ -0.400,  0.600] miss 0.157 w1  S0064 Longland 1.2 g/kg: +0.1 +/- 1.0 kg
ORACLE longland_hp_fat              -3.5915 [ -5.000, -3.000] miss 0.000 w0  S0064 fat -4.8 +/- 1.6 kg (energy side; report)
ORACLE garthe11_slow_lean            0.0968 [  0.800,  1.800] miss 0.703 w1  Garthe 2011 (PMID 21558571) -19 %: LBM +2.1 %
ORACLE garthe11_fast_lean           -0.3690 [ -0.600,  0.400] miss 0.000 w1  Garthe 2011 -30 %: LBM -0.2 %
ORACLE mk_minus500_lean             -0.2586 [ -0.300,  0.300] miss 0.000 w1  S1.28 Murphy & Koehler: -500 kcal/d -> no lean gain
ORACLE trained_maint_8wk             0.4628 [  0.100,  1.500] miss 0.000 w1  Helms 2023 MAIN; Antonio 2015 (PMID 26500462) FFM +1.5
ORACLE trained_maint_premise         0.4628 [ -0.100,  0.100] miss 1.814 w0  Angus premise: trained ~0 at maintenance
ORACLE helms23_15pct_over_maint      1.1680 [  0.800,  1.600] miss 0.000 w1  S1.29 Helms 2023: no MT difference by surplus
ORACLE garthe13_lean_ratio           1.0000 [  0.800,  1.350] miss 0.000 w1  S1.30 Garthe 2013: LBM gain not different
ORACLE garthe13_fat_diff             3.3365 [  0.800,  2.500] miss 0.492 w1  S1.30 Garthe 2013: FM +15 % vs +3 %
ORACLE mettler_lp_share              0.5946 [  0.350,  0.700] miss 0.000 w1  Mettler 2010 (PMID 19927027) 1.0 g/kg: 1.6 of 3.0 kg lean
ORACLE mettler_hp_share              0.1939 [  0.050,  0.350] miss 0.000 w1  Mettler 2010 2.3 g/kg: 0.3 of 1.5 kg lean
ORACLE quarter_rule_share            0.2306 [  0.150,  0.350] miss 0.000 w1  Heymsfield 2014 (PMID 24447775); S0072 Weinheimer
ORACLE pasiakos_0.8_minus_1.6        0.0884 [  0.100,  0.500] miss 0.029 w1  Pasiakos 2013 (PMID 23739654) direction (abstract)
ORACLE bray_15pct_lean               2.4068 [  1.500,  3.500] miss 0.000 w1  S0605 Bray 2012: lean +2.87 kg at 15 % protein
ORACLE bray_5pct_lean                0.0000 [ -0.700,  0.500] miss 0.000 w1  S0605 Bray 2012: no lean gain at 5 %
ORACLE bray_muscle_no_signal         0.0000 [ -0.050,  0.050] miss 0.000 w1  H.41/H.42/S0606: no muscle without the signal
ORACLE rantila_kept_frac             0.4256 [  0.240,  0.470] miss 0.000 w1  H.51 Räntilä 2025: 24-47 % kept after 10 wk off
ORACLE rantila_block2_over_1         0.9589 [  0.800,  1.250] miss 0.000 w1  H.51 Räntilä: block 2 = block 1
ORACLE bickel_third_kept             1.7269 [  0.850,  1.800] miss 0.000 w1  H.13 Bickel 2011: 1/3 dose kept size 32 wk
ORACLE bickel_ninth_kept             1.2951 [  0.850,  1.400] miss 0.000 w1  H.13 Bickel 2011: 1/9 dose kept size 32 wk
ORACLE detrain_halflife_wk           6.5714 [  4.900,  9.200] miss 0.000 w1  H.51 Räntilä derived 4.9-9.2 wk
ORACLE deg_protein_2pct              0.0256 [  0.000, 99.000] miss 0.000 w1  degenerate check: +2 % protein moves lean
ORACLE deg_surplus_2pct              0.0748 [  0.000, 99.000] miss 0.000 w1  degenerate check: +2 % surplus moves lean
ORACLE deg_sets_5pct                 0.0334 [  0.000, 99.000] miss 0.000 w1  degenerate check: +5 % sets moves lean
stab k              base 0.9050 [(0.95, 0.939, 22), (1.05, 0.872, 22)]
stab beta           base 0.9050 [(0.95, 0.8986, 21), (1.05, 0.9215, 21)]
stab Sg0            base 0.9050 [(0.95, 0.8991, 21), (1.05, 0.9128, 21)]
stab Smax1          base 0.9050 [(0.95, 0.9014, 6), (1.05, 0.9157, 6)]
stab E0             base 0.9050 [(0.95, 0.9572, 5), (1.05, 0.8597, 6)]
stab fe_bal         base 0.9050 [(0.95, 0.9385, 16), (1.05, 0.8725, 16)]
stab a_nov          base 0.9050 [(0.95, 0.9199, 4), (1.05, 0.8911, 4)]
stab surplus_full   base 0.9050 [(0.95, 0.905, 1), (1.05, 0.9043, 9)]
stab wT             base 0.9050 [(0.95, 0.9595, 5), (1.05, 0.8544, 5)]
stab wP             base 0.9050 [(0.95, 0.9775, 7), (1.05, 0.8387, 7)]
stab prot_floor     base 0.9050 [(0.95, 0.9017, 3), (1.05, 0.9084, 3)]
stab pdef_hi        base 0.9050 [(0.95, 0.789, 7), (1.05, 1.0192, 7)]
stab detrain_hl_wk  base 0.9050 [(0.95, 0.905, 3), (1.05, 0.905, 3)]
stab regain_hl_wk   base 0.9050 [(0.95, 0.905, 0), (1.05, 0.905, 0)]  FLAT
stab m              base 0.9050 [(0.95, 0.905, 0), (1.05, 0.905, 0)]  FLAT
stab grace_d        base 0.9050 [(0.95, 0.905, 2), (1.05, 0.905, 0)]
stab forbes_c       base 0.9050 [(0.95, 0.8862, 11), (1.05, 0.9243, 11)]
stab detrain_status base 0.9050 [(0.95, 0.905, 2), (1.05, 0.905, 2)]
```

### Appendix 3: variant B (Angus's premise weighted), `fit_B.txt`, summary and oracle lines
```
variant B candidates per round 2216
start score 7.6845
round 1 group growth   score 5.1036  {'beta': 2.5, 'Sg0': 0.5, 'Smax1': 15.0}
round 1 group energy   score 2.3910  {'E0': -1000.0, 'fe_bal': 1.0, 'a_nov': 2.8, 'surplus_full': 0.03, 'trained_need': 1.0}
round 1 group deficit  score 1.2208  {'wT': 0.35, 'wP': 0.75, 'prot_floor': 0.05, 'pdef_hi': 1.6}
round 1 group memory   score 1.2208  {'detrain_hl_wk': 6.0, 'regain_hl_wk': 6.0, 'm': 0.3333333333333333, 'grace_d': 14, 'regain_sum': False}
round 2 group growth   score 1.2208  {'beta': 2.5, 'Sg0': 0.5, 'Smax1': 15.0}
round 2 group energy   score 1.2208  {'E0': -1000.0, 'fe_bal': 1.0, 'a_nov': 2.8, 'surplus_full': 0.03, 'trained_need': 1.0}
round 2 group deficit  score 1.2208  {'wT': 0.35, 'wP': 0.75, 'prot_floor': 0.05, 'pdef_hi': 1.6}
round 2 group memory   score 1.2208  {'detrain_hl_wk': 6.0, 'regain_hl_wk': 6.0, 'm': 0.3333333333333333, 'grace_d': 14, 'regain_sum': False}
evaluated 4432 best 1.2208
FITTED {"k": 0.007763, "beta": 2.5, "Sg0": 0.5, "Sref": 12.0, "Smax": 30.0, "Smax1": 15.0, "E0": -1000.0, "fe_bal": 1.0, "surplus_full": 0.03, "a_nov": 2.8, "trained_need": 1.0, "forbes_c": 10.4, "wT": 0.35, "S_def": 10.0, "wP": 0.75, "pdef_lo": 0.8, "pdef_hi"
ORACLE year1_kg_20sets               6.7207 [  6.800,  8.500] miss 0.047 w1  S1.15 McDonald x0.75 (first-harvest calibration)
ORACLE yr2_over_yr1                  0.5397 [  0.400,  0.600] miss 0.000 w1  S1.15 halving; H.49/H.50 year-1 dominance
ORACLE yr3_over_yr2                  0.5731 [  0.400,  0.650] miss 0.000 w1  S1.15 halving
ORACLE benito_10wk_kg                1.1406 [  1.120,  1.960] miss 0.000 w1  S1.9 Benito 2020 untrained FFM +1.54 (CI 1.12-1.96)
ORACLE pelland_30_over_12            1.6552 [  1.550,  2.000] miss 0.000 w1  H.1 Pelland sqrt fit, derived 1.77
ORACLE h8_3_over_9                   0.4564 [  0.500,  0.900] miss 0.109 w1  H.8 1 vs 3 sets: +3.7 vs +5.2 % (0.71)
ORACLE aube_24_over_12               1.5010 [  0.700,  1.400] miss 0.144 w1  H.5 Aube 2022 advanced: 12=18=24 sets
ORACLE longland_hp_lean              0.4096 [  0.600,  1.800] miss 0.159 w1  S0064 Longland 2.4 g/kg -40 %: +1.2 +/- 1.0 kg
ORACLE longland_lp_lean             -0.3245 [ -0.400,  0.600] miss 0.000 w1  S0064 Longland 1.2 g/kg: +0.1 +/- 1.0 kg
ORACLE longland_hp_fat              -3.6377 [ -5.000, -3.000] miss 0.000 w0  S0064 fat -4.8 +/- 1.6 kg (energy side; report)
ORACLE garthe11_slow_lean            0.3004 [  0.800,  1.800] miss 0.500 w1  Garthe 2011 (PMID 21558571) -19 %: LBM +2.1 %
ORACLE garthe11_fast_lean            0.0090 [ -0.600,  0.400] miss 0.000 w1  Garthe 2011 -30 %: LBM -0.2 %
ORACLE mk_minus500_lean              0.1294 [ -0.300,  0.300] miss 0.000 w1  S1.28 Murphy & Koehler: -500 kcal/d -> no lean gain
ORACLE trained_maint_8wk             0.2312 [  0.100,  1.500] miss 0.000 w0  Helms 2023 MAIN; Antonio 2015 (PMID 26500462) FFM +1.5
ORACLE trained_maint_premise         0.2312 [ -0.100,  0.100] miss 0.656 w1  Angus premise: trained ~0 at maintenance
ORACLE helms23_15pct_over_maint      1.9907 [  0.800,  1.600] miss 0.488 w1  S1.29 Helms 2023: no MT difference by surplus
ORACLE garthe13_lean_ratio           1.0000 [  0.800,  1.350] miss 0.000 w1  S1.30 Garthe 2013: LBM gain not different
ORACLE garthe13_fat_diff             3.3365 [  0.800,  2.500] miss 0.492 w1  S1.30 Garthe 2013: FM +15 % vs +3 %
ORACLE mettler_lp_share              0.5482 [  0.350,  0.700] miss 0.000 w1  Mettler 2010 (PMID 19927027) 1.0 g/kg: 1.6 of 3.0 kg lean
ORACLE mettler_hp_share              0.0923 [  0.050,  0.350] miss 0.000 w1  Mettler 2010 2.3 g/kg: 0.3 of 1.5 kg lean
ORACLE quarter_rule_share            0.2200 [  0.150,  0.350] miss 0.000 w1  Heymsfield 2014 (PMID 24447775); S0072 Weinheimer
ORACLE pasiakos_0.8_minus_1.6        0.2438 [  0.100,  0.500] miss 0.000 w1  Pasiakos 2013 (PMID 23739654) direction (abstract)
ORACLE bray_15pct_lean               2.4068 [  1.500,  3.500] miss 0.000 w1  S0605 Bray 2012: lean +2.87 kg at 15 % protein
ORACLE bray_5pct_lean                0.0000 [ -0.700,  0.500] miss 0.000 w1  S0605 Bray 2012: no lean gain at 5 %
ORACLE bray_muscle_no_signal         0.0000 [ -0.050,  0.050] miss 0.000 w1  H.41/H.42/S0606: no muscle without the signal
ORACLE rantila_kept_frac             0.3938 [  0.240,  0.470] miss 0.000 w1  H.51 Räntilä 2025: 24-47 % kept after 10 wk off
ORACLE rantila_block2_over_1         0.9465 [  0.800,  1.250] miss 0.000 w1  H.51 Räntilä: block 2 = block 1
ORACLE bickel_third_kept             1.6755 [  0.850,  1.800] miss 0.000 w1  H.13 Bickel 2011: 1/3 dose kept size 32 wk
ORACLE bickel_ninth_kept             1.2968 [  0.850,  1.400] miss 0.000 w1  H.13 Bickel 2011: 1/9 dose kept size 32 wk
ORACLE detrain_halflife_wk           6.0000 [  4.900,  9.200] miss 0.000 w1  H.51 Räntilä derived 4.9-9.2 wk
ORACLE deg_protein_2pct              0.0225 [  0.000, 99.000] miss 0.000 w1  degenerate check: +2 % protein moves lean
ORACLE deg_surplus_2pct              0.0201 [  0.000, 99.000] miss 0.000 w1  degenerate check: +2 % surplus moves lean
ORACLE deg_sets_5pct                 0.0292 [  0.000, 99.000] miss 0.000 w1  degenerate check: +5 % sets moves lean
BOUND Sg0            = 0.5 (grid 0.5..1.3)
BOUND E0             = -1000.0 (grid -400.0..-1000.0)
BOUND fe_bal         = 1.0 (grid 0.7..1.0)
BOUND a_nov          = 2.8 (grid 0.0..2.8)
BOUND surplus_full   = 0.03 (grid 0.03..0.1)
BOUND trained_need   = 1.0 (grid 0.0..1.0)
BOUND wP             = 0.75 (grid 0.3..0.75)
BOUND prot_floor     = 0.05 (grid 0.05..0.3)
BOUND pdef_hi        = 1.6 (grid 1.6..2.8)
```

### Appendix 4: unconstrained run A, `fit_A_unconstrained.txt`, summary and bound lines
```
variant A candidates per round 2064
start score 6.6113
round 1 group growth   score 3.8750  {'beta': 5.0, 'Sg0': 0.1, 'Smax1': 12.0}
round 1 group energy   score 0.7335  {'E0': -2000.0, 'fe_bal': 0.85, 'a_nov': 5.0, 'surplus_full': 0.1}
round 1 group deficit  score 0.2408  {'wT': 0.2, 'wP': 0.75, 'prot_floor': 0.0, 'pdef_hi': 1.6}
round 1 group memory   score 0.2408  {'detrain_hl_wk': 6.0, 'regain_hl_wk': 6.0, 'm': 0.3333333333333333, 'grace_d': 14, 'regain_sum': False}
round 2 group growth   score 0.2408  {'beta': 5.0, 'Sg0': 0.1, 'Smax1': 12.0}
round 2 group energy   score 0.2408  {'E0': -2000.0, 'fe_bal': 0.85, 'a_nov': 5.0, 'surplus_full': 0.1}
round 2 group deficit  score 0.2408  {'wT': 0.2, 'wP': 0.75, 'prot_floor': 0.0, 'pdef_hi': 1.6}
round 2 group memory   score 0.2408  {'detrain_hl_wk': 6.0, 'regain_hl_wk': 6.0, 'm': 0.3333333333333333, 'grace_d': 14, 'regain_sum': False}
evaluated 4128 best 0.2408
FITTED {"k": 0.010936, "beta": 5.0, "Sg0": 0.1, "Sref": 12.0, "Smax": 30.0, "Smax1": 12.0, "E0": -2000.0, "fe_bal": 0.85, "surplus_full": 0.1, "a_nov": 5.0, "trained_need": 0.0, "forbes_c": 10.4, "wT": 0.2, "S_def": 10.0, "wP": 0.75, "pdef_lo": 0.8, "pdef_hi":
BOUND beta           = 5.0 (grid 1.0..5.0)
BOUND Sg0            = 0.1 (grid 0.1..1.3)
BOUND E0             = -2000.0 (grid -400.0..-2000.0)
BOUND a_nov          = 5.0 (grid 0.0..5.0)
BOUND surplus_full   = 0.1 (grid 0.03..0.1)
BOUND wT             = 0.2 (grid 0.2..0.65)
BOUND wP             = 0.75 (grid 0.3..0.75)
BOUND prot_floor     = 0.0 (grid 0.0..0.3)
```

### Appendix 5: scenarios for point R, `scenarios_R.txt`
```
== R: k = 0.00991
  Weak    levels yr1-10 [6.59, 9.5, 10.89, 11.68, 12.17, 12.51, 12.76, 12.95, 13.09, 13.21]  yrs to L10 2.29  to L15 None
  Feeble  levels yr1-10 [8.89, 11.48, 12.72, 13.43, 13.87, 14.17, 14.39, 14.56, 14.69, 14.79]  yrs to L10 1.34  to L15 None
  none    levels yr1-10 [10.41, 12.81, 13.95, 14.59, 15.0, 15.28, 15.48, 15.63, 15.75, 15.85]  yrs to L10 0.89  to L15 5.0
  Stout   levels yr1-10 [11.94, 14.13, 15.17, 15.76, 16.13, 16.39, 16.57, 16.71, 16.82, 16.9]  yrs to L10 0.5  to L15 2.79
  Strong  levels yr1-10 [13.47, 15.45, 16.39, 16.92, 17.26, 17.49, 17.66, 17.78, 17.88, 17.96]  yrs to L10 0.16  to L15 1.69
  average, kg gained per year at 20 sets: [7.82, 3.47, 1.65, 0.92, 0.59]
  S= 3 sets/wk: level yr1 6.83 yr5 10.14 yr10 11.30 (y1 kg 2.64)
  S= 6 sets/wk: level yr1 7.94 yr5 12.30 yr10 13.64 (y1 kg 4.25)
  S=10 sets/wk: level yr1 8.91 yr5 13.77 yr10 15.08 (y1 kg 5.65)
  S=15 sets/wk: level yr1 9.77 yr5 14.77 yr10 15.79 (y1 kg 6.89)
  S=20 sets/wk: level yr1 10.41 yr5 15.00 yr10 15.85 (y1 kg 7.82)
  S=30 sets/wk: level yr1 10.87 yr5 15.05 yr10 15.86 (y1 kg 8.48)
  detraining from L 13.95 (yr 3): (week, level, share of gain kept) [(4, 13.15, 0.911), (12, 10.3, 0.593), (24, 7.25, 0.251)]
  regain novice 1 yr: peak L 10.41, after 26 wk off L 5.75, weeks to recover 90 % of the loss: 26
  regain advanced 5 yr: peak L 15.00, after 26 wk off L 7.35, weeks to recover 90 % of the loss: 66
== R: novice cases (average untrained, 1.70 m, 14 % fat = 8.5 kg; and an overweight novice, 20 kg fat)
  fat0  8.47 kg | recomp -500 kcal, 2.4 g/kg     (week, dMuscle, dLabileLean, dFat) [(1, 0.119, 0.0, -0.394), (2, 0.236, 0.0, -0.787), (4, 0.461, 0.0, -1.572), (8, 0.785, 0.0, -3.117), (12, 0.924, 0.0, -4.626), (16, 0.889, 0.0, -6.103)]
  fat0  8.47 kg | maintenance, 1.6 g/kg          (week, dMuscle, dLabileLean, dFat) [(1, 0.19, 0.0, -0.037), (2, 0.377, 0.0, -0.073), (4, 0.743, 0.0, -0.143), (8, 1.444, 0.0, -0.278), (12, 2.105, 0.0, -0.405), (16, 2.728, 0.0, -0.525)]
  fat0  8.47 kg | surplus +10 % (+260), 1.6 g/kg (week, dMuscle, dLabileLean, dFat) [(1, 0.223, 0.0, 0.15), (2, 0.442, 0.0, 0.3), (4, 0.87, 0.0, 0.604), (8, 1.682, 0.0, 1.219), (12, 2.44, 0.0, 1.844), (16, 3.148, 0.0, 2.479)]
  fat0 20.00 kg | recomp -500 kcal, 2.4 g/kg     (week, dMuscle, dLabileLean, dFat) [(1, 0.127, 0.0, -0.395), (2, 0.253, 0.0, -0.79), (4, 0.498, 0.0, -1.579), (8, 0.965, 0.0, -3.151), (12, 1.403, 0.0, -4.719), (16, 1.814, 0.0, -6.281)]
  fat0 20.00 kg | maintenance, 1.6 g/kg          (week, dMuscle, dLabileLean, dFat) [(1, 0.19, 0.0, -0.037), (2, 0.377, 0.0, -0.073), (4, 0.743, 0.0, -0.143), (8, 1.444, 0.0, -0.278), (12, 2.105, 0.0, -0.405), (16, 2.728, 0.0, -0.525)]
  fat0 20.00 kg | surplus +10 % (+260), 1.6 g/kg (week, dMuscle, dLabileLean, dFat) [(1, 0.223, 0.0, 0.15), (2, 0.442, 0.0, 0.3), (4, 0.87, 0.0, 0.604), (8, 1.682, 0.0, 1.219), (12, 2.44, 0.0, 1.844), (16, 3.148, 0.0, 2.479)]
  Longland conditions p=2.4, -1200 kcal, 4 wk: lean +0.17 (muscle +0.17, labile +0.00), fat -3.59
  Longland conditions p=1.2, -1200 kcal, 4 wk: lean -0.56 (muscle -0.56, labile +0.00), fat -3.45
== R: trained character (s = 0.5, level 10.75), one year, 20 sets/wk
  maintenance, 2.0 g/kg: muscle +2.85 kg, labile +0.00, fat -0.55, level 10.75 -> 12.72
  bulk +10 % / cut -500 x2: muscle +2.55 kg, labile +0.00, fat +1.05, level -> 12.51  [('bulk1', 1.4, 3.47), ('cut1', 1.49, 0.48), ('bulk2', 2.52, 4.02), ('cut2', 2.55, 1.05)]
  bulk +20 % / cut -500 x2: muscle +2.59 kg, labile +0.00, fat +8.52, level -> 12.54  [('bulk1', 1.4, 7.2), ('cut1', 1.51, 4.22), ('bulk2', 2.54, 11.49), ('cut2', 2.59, 8.52)]
  (novice, same year at maintenance: muscle +7.01, fat -1.35)

```

### Appendix 6: scenarios for the spec's constants and for C and B, `scenarios.txt`
```
== spec: k = 0.00876
  Weak    levels yr1-10 [6.11, 9.02, 10.6, 11.55, 12.17, 12.6, 12.91, 13.14, 13.31, 13.45]  yrs to L10 2.56  to L15 None
  Feeble  levels yr1-10 [8.46, 11.05, 12.46, 13.31, 13.87, 14.25, 14.53, 14.73, 14.89, 15.01]  yrs to L10 1.52  to L15 9.94
  none    levels yr1-10 [10.02, 12.41, 13.7, 14.49, 15.0, 15.35, 15.61, 15.79, 15.94, 16.05]  yrs to L10 0.99  to L15 5.0
  Stout   levels yr1-10 [11.59, 13.76, 14.95, 15.66, 16.13, 16.45, 16.68, 16.86, 16.99, 17.09]  yrs to L10 0.56  to L15 3.06
  Strong  levels yr1-10 [13.15, 15.12, 16.19, 16.84, 17.26, 17.55, 17.76, 17.92, 18.03, 18.13]  yrs to L10 0.18  to L15 1.92
  average, kg gained per year at 20 sets: [7.25, 3.45, 1.86, 1.14, 0.74]
  S= 3 sets/wk: level yr1 6.31 yr5 8.78 yr10 9.67 (y1 kg 1.89)
  S= 6 sets/wk: level yr1 7.45 yr5 11.30 yr10 12.55 (y1 kg 3.54)
  S=10 sets/wk: level yr1 8.46 yr5 13.06 yr10 14.41 (y1 kg 5.00)
  S=15 sets/wk: level yr1 9.35 yr5 14.28 yr10 15.53 (y1 kg 6.29)
  S=20 sets/wk: level yr1 10.02 yr5 15.00 yr10 16.05 (y1 kg 7.25)
  S=30 sets/wk: level yr1 11.02 yr5 15.76 yr10 16.40 (y1 kg 8.70)
  detraining from L 13.70 (yr 3): (week, level, share of gain kept) [(4, 11.89, 0.792), (12, 7.72, 0.312), (24, 5.67, 0.077)]
  regain novice 1 yr: peak L 10.02, after 26 wk off L 5.31, weeks to recover 90 % of the loss: 27
  regain advanced 5 yr: peak L 15.00, after 26 wk off L 5.61, weeks to recover 90 % of the loss: 72
== spec: novice cases (average untrained, 1.70 m, 14 % fat = 8.5 kg; and an overweight novice, 20 kg fat)
  fat0  8.47 kg | recomp -500 kcal, 2.4 g/kg     (week, dMuscle, dLabileLean, dFat) [(1, 0.056, 0.0, -0.382), (2, 0.11, 0.0, -0.763), (4, 0.213, 0.0, -1.524), (8, 0.224, 0.0, -3.009), (12, -0.085, 0.0, -4.432), (16, -0.697, 0.0, -5.797)]
  fat0  8.47 kg | maintenance, 1.6 g/kg          (week, dMuscle, dLabileLean, dFat) [(1, 0.173, 0.0, -0.033), (2, 0.344, 0.0, -0.066), (4, 0.679, 0.0, -0.131), (8, 1.32, 0.0, -0.254), (12, 1.926, 0.0, -0.371), (16, 2.5, 0.0, -0.481)]
  fat0  8.47 kg | surplus +10 % (+260), 1.6 g/kg (week, dMuscle, dLabileLean, dFat) [(1, 0.204, 0.0, 0.154), (2, 0.404, 0.0, 0.308), (4, 0.795, 0.0, 0.618), (8, 1.538, 0.0, 1.246), (12, 2.234, 0.0, 1.884), (16, 2.886, 0.0, 2.529)]
  fat0 20.00 kg | recomp -500 kcal, 2.4 g/kg     (week, dMuscle, dLabileLean, dFat) [(1, 0.074, 0.0, -0.385), (2, 0.147, 0.0, -0.77), (4, 0.289, 0.0, -1.538), (8, 0.557, 0.0, -3.073), (12, 0.804, 0.0, -4.603), (16, 1.031, 0.0, -6.13)]
  fat0 20.00 kg | maintenance, 1.6 g/kg          (week, dMuscle, dLabileLean, dFat) [(1, 0.173, 0.0, -0.033), (2, 0.344, 0.0, -0.066), (4, 0.679, 0.0, -0.131), (8, 1.32, 0.0, -0.254), (12, 1.926, 0.0, -0.371), (16, 2.5, 0.0, -0.481)]
  fat0 20.00 kg | surplus +10 % (+260), 1.6 g/kg (week, dMuscle, dLabileLean, dFat) [(1, 0.204, 0.0, 0.154), (2, 0.404, 0.0, 0.308), (4, 0.795, 0.0, 0.618), (8, 1.538, 0.0, 1.246), (12, 2.234, 0.0, 1.884), (16, 2.886, 0.0, 2.529)]
  Longland conditions p=2.4, -1200 kcal, 4 wk: lean -0.23 (muscle -0.23, labile +0.00), fat -3.51
  Longland conditions p=1.2, -1200 kcal, 4 wk: lean -0.68 (muscle -0.68, labile +0.00), fat -3.43
== spec: trained character (s = 0.5, level 10.75), one year, 20 sets/wk
  maintenance, 2.0 g/kg: muscle +2.60 kg, labile +0.00, fat -0.50, level 10.75 -> 12.55
  bulk +10 % / cut -500 x2: muscle +1.85 kg, labile +0.00, fat +1.19, level -> 12.03  [('bulk1', 1.23, 3.5), ('cut1', 1.04, 0.57), ('bulk2', 2.06, 4.11), ('cut2', 1.85, 1.19)]
  bulk +20 % / cut -500 x2: muscle +1.95 kg, labile +0.00, fat +8.64, level -> 12.10  [('bulk1', 1.23, 7.24), ('cut1', 1.08, 4.3), ('bulk2', 2.09, 11.58), ('cut2', 1.95, 8.64)]
  (novice, same year at maintenance: muscle +6.49, fat -1.25)

== C: k = 0.00991
  Weak    levels yr1-10 [6.26, 9.2, 10.65, 11.48, 12.01, 12.38, 12.64, 12.84, 13.0, 13.12]  yrs to L10 2.48  to L15 None
  Feeble  levels yr1-10 [8.59, 11.21, 12.51, 13.25, 13.72, 14.05, 14.29, 14.46, 14.6, 14.72]  yrs to L10 1.44  to L15 None
  none    levels yr1-10 [10.15, 12.56, 13.75, 14.43, 14.87, 15.17, 15.38, 15.55, 15.68, 15.78]  yrs to L10 0.96  to L15 5.41
  Stout   levels yr1-10 [11.7, 13.9, 14.99, 15.61, 16.01, 16.28, 16.48, 16.63, 16.75, 16.84]  yrs to L10 0.54  to L15 3.02
  Strong  levels yr1-10 [13.25, 15.24, 16.23, 16.79, 17.15, 17.4, 17.58, 17.71, 17.82, 17.9]  yrs to L10 0.18  to L15 1.83
  average, kg gained per year at 20 sets: [7.44, 3.48, 1.72, 0.98, 0.64]
  S= 3 sets/wk: level yr1 6.72 yr5 9.97 yr10 11.21 (y1 kg 2.49)
  S= 6 sets/wk: level yr1 7.77 yr5 12.11 yr10 13.53 (y1 kg 4.00)
  S=10 sets/wk: level yr1 8.69 yr5 13.58 yr10 14.97 (y1 kg 5.33)
  S=15 sets/wk: level yr1 9.52 yr5 14.60 yr10 15.71 (y1 kg 6.53)
  S=20 sets/wk: level yr1 10.15 yr5 14.87 yr10 15.78 (y1 kg 7.44)
  S=30 sets/wk: level yr1 10.62 yr5 14.92 yr10 15.79 (y1 kg 8.12)
  detraining from L 13.75 (yr 3): (week, level, share of gain kept) [(4, 11.93, 0.792), (12, 7.73, 0.312), (24, 5.67, 0.077)]
  regain novice 1 yr: peak L 10.15, after 26 wk off L 5.31, weeks to recover 90 % of the loss: 28
  regain advanced 5 yr: peak L 14.87, after 26 wk off L 5.60, weeks to recover 90 % of the loss: 76
== C: novice cases (average untrained, 1.70 m, 14 % fat = 8.5 kg; and an overweight novice, 20 kg fat)
  fat0  8.47 kg | recomp -500 kcal, 2.4 g/kg     (week, dMuscle, dLabileLean, dFat) [(1, 0.154, 0.0, -0.4), (2, 0.306, 0.0, -0.8), (4, 0.601, 0.0, -1.598), (8, 1.107, 0.0, -3.179), (12, 1.499, 0.0, -4.737), (16, 1.782, 0.0, -6.274)]
  fat0  8.47 kg | maintenance, 1.6 g/kg          (week, dMuscle, dLabileLean, dFat) [(1, 0.19, 0.0, -0.037), (2, 0.377, 0.0, -0.073), (4, 0.743, 0.0, -0.143), (8, 1.444, 0.0, -0.278), (12, 2.105, 0.0, -0.405), (16, 2.728, 0.0, -0.525)]
  fat0  8.47 kg | surplus +10 % (+260), 1.6 g/kg (week, dMuscle, dLabileLean, dFat) [(1, 0.223, 0.0, 0.15), (2, 0.442, 0.0, 0.3), (4, 0.87, 0.0, 0.604), (8, 1.682, 0.0, 1.219), (12, 2.44, 0.0, 1.844), (16, 3.148, 0.0, 2.479)]
  fat0 20.00 kg | recomp -500 kcal, 2.4 g/kg     (week, dMuscle, dLabileLean, dFat) [(1, 0.158, 0.0, -0.401), (2, 0.314, 0.0, -0.802), (4, 0.619, 0.0, -1.602), (8, 1.201, 0.0, -3.197), (12, 1.748, 0.0, -4.785), (16, 2.262, 0.0, -6.367)]
  fat0 20.00 kg | maintenance, 1.6 g/kg          (week, dMuscle, dLabileLean, dFat) [(1, 0.19, 0.0, -0.037), (2, 0.377, 0.0, -0.073), (4, 0.743, 0.0, -0.143), (8, 1.444, 0.0, -0.278), (12, 2.105, 0.0, -0.405), (16, 2.728, 0.0, -0.525)]
  fat0 20.00 kg | surplus +10 % (+260), 1.6 g/kg (week, dMuscle, dLabileLean, dFat) [(1, 0.223, 0.0, 0.15), (2, 0.442, 0.0, 0.3), (4, 0.87, 0.0, 0.604), (8, 1.682, 0.0, 1.219), (12, 2.44, 0.0, 1.844), (16, 3.148, 0.0, 2.479)]
  Longland conditions p=2.4, -1200 kcal, 4 wk: lean +0.45 (muscle +0.45, labile +0.00), fat -3.65
  Longland conditions p=1.2, -1200 kcal, 4 wk: lean -0.32 (muscle -0.32, labile +0.00), fat -3.50
== C: trained character (s = 0.5, level 10.75), one year, 20 sets/wk
  maintenance, 2.0 g/kg: muscle +2.85 kg, labile +0.00, fat -0.55, level 10.75 -> 12.72
  bulk +10 % / cut -500 x2: muscle +2.76 kg, labile +0.00, fat +1.01, level -> 12.66  [('bulk1', 1.4, 3.47), ('cut1', 1.63, 0.46), ('bulk2', 2.63, 4.0), ('cut2', 2.76, 1.01)]
  bulk +20 % / cut -500 x2: muscle +2.79 kg, labile +0.00, fat +8.48, level -> 12.68  [('bulk1', 1.4, 7.2), ('cut1', 1.64, 4.19), ('bulk2', 2.64, 11.47), ('cut2', 2.79, 8.48)]
  (novice, same year at maintenance: muscle +7.01, fat -1.35)

== B: k = 0.00776
  Weak    levels yr1-10 [5.66, 8.72, 10.47, 11.51, 12.17, 12.63, 12.95, 13.18, 13.36, 13.5]  yrs to L10 2.67  to L15 None
  Feeble  levels yr1-10 [8.06, 10.78, 12.35, 13.27, 13.87, 14.27, 14.56, 14.77, 14.93, 15.05]  yrs to L10 1.65  to L15 9.56
  none    levels yr1-10 [9.65, 12.16, 13.6, 14.45, 15.0, 15.37, 15.64, 15.83, 15.98, 16.09]  yrs to L10 1.11  to L15 5.0
  Stout   levels yr1-10 [11.25, 13.54, 14.85, 15.63, 16.13, 16.47, 16.71, 16.89, 17.02, 17.12]  yrs to L10 0.64  to L15 3.16
  Strong  levels yr1-10 [12.84, 14.92, 16.1, 16.81, 17.26, 17.57, 17.79, 17.95, 18.07, 18.16]  yrs to L10 0.21  to L15 2.06
  average, kg gained per year at 20 sets: [6.72, 3.63, 2.08, 1.23, 0.79]
  S= 3 sets/wk: level yr1 6.51 yr5 9.87 yr10 11.55 (y1 kg 2.18)
  S= 6 sets/wk: level yr1 7.45 yr5 12.02 yr10 13.89 (y1 kg 3.54)
  S=10 sets/wk: level yr1 8.30 yr5 13.50 yr10 15.23 (y1 kg 4.77)
  S=15 sets/wk: level yr1 9.06 yr5 14.51 yr10 15.92 (y1 kg 5.87)
  S=20 sets/wk: level yr1 9.65 yr5 15.00 yr10 16.09 (y1 kg 6.72)
  S=30 sets/wk: level yr1 10.22 yr5 15.10 yr10 16.11 (y1 kg 7.54)
  detraining from L 13.60 (yr 3): (week, level, share of gain kept) [(4, 11.81, 0.792), (12, 7.68, 0.312), (24, 5.66, 0.077)]
  regain novice 1 yr: peak L 9.65, after 26 wk off L 5.28, weeks to recover 90 % of the loss: 27
  regain advanced 5 yr: peak L 15.00, after 26 wk off L 5.61, weeks to recover 90 % of the loss: 67
== B: novice cases (average untrained, 1.70 m, 14 % fat = 8.5 kg; and an overweight novice, 20 kg fat)
  fat0  8.47 kg | recomp -500 kcal, 2.4 g/kg     (week, dMuscle, dLabileLean, dFat) [(1, 0.141, 0.0, -0.398), (2, 0.279, 0.0, -0.795), (4, 0.543, 0.0, -1.587), (8, 0.983, 0.0, -3.155), (12, 1.303, 0.0, -4.699), (16, 1.513, 0.0, -6.223)]
  fat0  8.47 kg | maintenance, 1.6 g/kg          (week, dMuscle, dLabileLean, dFat) [(1, 0.174, 0.0, -0.034), (2, 0.345, 0.0, -0.066), (4, 0.674, 0.0, -0.13), (8, 1.289, 0.0, -0.248), (12, 1.854, 0.0, -0.357), (16, 2.374, 0.0, -0.457)]
  fat0  8.47 kg | surplus +10 % (+260), 1.6 g/kg (week, dMuscle, dLabileLean, dFat) [(1, 0.175, 0.0, 0.159), (2, 0.348, 0.0, 0.319), (4, 0.687, 0.0, 0.639), (8, 1.339, 0.0, 1.285), (12, 1.959, 0.0, 1.937), (16, 2.547, 0.0, 2.594)]
  fat0 20.00 kg | recomp -500 kcal, 2.4 g/kg     (week, dMuscle, dLabileLean, dFat) [(1, 0.145, 0.0, -0.399), (2, 0.287, 0.0, -0.797), (4, 0.561, 0.0, -1.591), (8, 1.074, 0.0, -3.172), (12, 1.544, 0.0, -4.746), (16, 1.977, 0.0, -6.312)]
  fat0 20.00 kg | maintenance, 1.6 g/kg          (week, dMuscle, dLabileLean, dFat) [(1, 0.174, 0.0, -0.034), (2, 0.345, 0.0, -0.066), (4, 0.674, 0.0, -0.13), (8, 1.289, 0.0, -0.248), (12, 1.854, 0.0, -0.357), (16, 2.374, 0.0, -0.457)]
  fat0 20.00 kg | surplus +10 % (+260), 1.6 g/kg (week, dMuscle, dLabileLean, dFat) [(1, 0.175, 0.0, 0.159), (2, 0.348, 0.0, 0.319), (4, 0.687, 0.0, 0.639), (8, 1.339, 0.0, 1.285), (12, 1.959, 0.0, 1.937), (16, 2.547, 0.0, 2.594)]
  Longland conditions p=2.4, -1200 kcal, 4 wk: lean +0.41 (muscle +0.41, labile +0.00), fat -3.64
  Longland conditions p=1.2, -1200 kcal, 4 wk: lean -0.32 (muscle -0.32, labile +0.00), fat -3.50
== B: trained character (s = 0.5, level 10.75), one year, 20 sets/wk
  maintenance, 2.0 g/kg: muscle +1.52 kg, labile +0.00, fat -0.29, level 10.75 -> 11.80
  bulk +10 % / cut -500 x2: muscle +2.28 kg, labile +0.00, fat +1.10, level -> 12.33  [('bulk1', 1.2, 3.51), ('cut1', 1.27, 0.53), ('bulk2', 2.26, 4.07), ('cut2', 2.28, 1.1)]
  bulk +20 % / cut -500 x2: muscle +2.30 kg, labile +0.00, fat +8.57, level -> 12.34  [('bulk1', 1.2, 7.24), ('cut1', 1.28, 4.26), ('bulk2', 2.26, 11.55), ('cut2', 2.3, 8.57)]
  (novice, same year at maintenance: muscle +5.70, fat -1.10)

```

### Appendix 7: the creation bodies, `creation.py`
```
-- spec as written (male %% table: Healthy mid 14 %%, High mid 22.5 %%, Very high 'mid' taken as 30 %%; thin at 5 %%)
none (fat Healthy mid 14%)         F 52.02 (L  5.00) fat  8.47 W 60.49 BMI 20.93 %fat 14.0 FMI 2.93 PE@1.75 1 PE@1.70 1
Feeble (fat Healthy mid 14%)       F 49.13 (L  3.00) fat  8.00 W 57.13 BMI 19.77 %fat 14.0 FMI 2.77 PE@1.75 1 PE@1.70 1
Weak (fat Healthy mid 14%)         F 44.79 (L  0.00) fat  7.29 W 52.09 BMI 18.02 %fat 14.0 FMI 2.52 PE@1.75 2 PE@1.70 2
Stout (fat Healthy mid 14%)        F 54.91 (L  7.00) fat  8.94 W 63.85 BMI 22.09 %fat 14.0 FMI 3.09 PE@1.75 1 PE@1.70 1
Strong (fat Healthy mid 14%)       F 57.80 (L  9.00) fat  9.41 W 67.21 BMI 23.26 %fat 14.0 FMI 3.26 PE@1.75 1 PE@1.70 1
Overweight (22.5%)                 F 52.02 (L  5.00) fat 15.10 W 67.12 BMI 23.23 %fat 22.5 FMI 5.23 PE@1.75 1 PE@1.70 1
Obese (30%)                        F 52.02 (L  5.00) fat 22.29 W 74.31 BMI 25.71 %fat 30.0 FMI 7.71 PE@1.75 1 PE@1.70 1
Underweight BMI 18.0 @5%           F 49.42 (L  3.20) fat  2.60 W 52.02 BMI 18.00 %fat  5.0 FMI 0.90 PE@1.75 3 PE@1.70 2
Very Underweight BMI 16.5 @5%      F 45.30 (L  0.35) fat  2.38 W 47.68 BMI 16.50 %fat  5.0 FMI 0.82 PE@1.75 4 PE@1.70 3
-- the %%-fat cuts 8/20/25 at the neutral average lean F = 52.0 kg, in BMI:
   %fat  6 -> W 55.3 BMI 19.15 FMI 1.15
   %fat  8 -> W 56.5 BMI 19.57 FMI 1.57
   %fat 20 -> W 65.0 BMI 22.50 FMI 4.50
   %fat 25 -> W 69.4 BMI 24.00 FMI 6.00
-- proposed (FMI bands, Kelly 2009 male: normal 3-6, overweight 6-9, obese >= 9)
none (FMI 4.5)                     F 52.02 (L  5.00) fat 13.00 W 65.02 BMI 22.50 %fat 20.0 FMI 4.50 PE@1.75 1 PE@1.70 1
Feeble (FMI 4.5)                   F 49.13 (L  3.00) fat 13.00 W 62.13 BMI 21.50 %fat 20.9 FMI 4.50 PE@1.75 1 PE@1.70 1
Weak (FMI 4.5)                     F 44.79 (L  0.00) fat 13.00 W 57.80 BMI 20.00 %fat 22.5 FMI 4.50 PE@1.75 1 PE@1.70 1
Stout (FMI 4.5)                    F 54.91 (L  7.00) fat 13.00 W 67.91 BMI 23.50 %fat 19.1 FMI 4.50 PE@1.75 1 PE@1.70 1
Strong (FMI 4.5)                   F 57.80 (L  9.00) fat 13.00 W 70.80 BMI 24.50 %fat 18.4 FMI 4.50 PE@1.75 1 PE@1.70 1
Overweight (FMI 7.5)               F 52.02 (L  5.00) fat 21.67 W 73.69 BMI 25.50 %fat 29.4 FMI 7.50 PE@1.75 1 PE@1.70 1
Obese (FMI 11)                     F 52.02 (L  5.00) fat 31.79 W 83.81 BMI 29.00 %fat 37.9 FMI 11.00 PE@1.75 1 PE@1.70 1
Underweight BMI 18.0 @FMI 1.5      F 47.68 (L  2.00) fat  4.33 W 52.02 BMI 18.00 %fat  8.3 FMI 1.50 PE@1.75 3 PE@1.70 2
Very Underweight BMI 16.5 @FMI 1.0 F 44.79 (L  0.00) fat  2.89 W 47.68 BMI 16.50 %fat  6.1 FMI 1.00 PE@1.75 4 PE@1.70 3
Very Underweight BMI 16.5 @6%      F 44.82 (L  0.02) fat  2.86 W 47.68 BMI 16.50 %fat  6.0 FMI 0.99 PE@1.75 4 PE@1.70 3
```

### Appendix 8: the detraining status term, `detrain_alt.txt` (first run, with the trained-state detraining oracle) and `rescore.txt` (with the corrected novice-state oracle)
```
detrain_status 0.0 | yr3 L 13.75 detrain [(4, 11.93, 0.792), (12, 7.73, 0.312), (24, 5.67, 0.077)] | advanced peak 14.87 off26wk 5.60 regain wk80 29 wk90 76 | rantila kept 0.394 block2/1 0.962 | score 0.4018
detrain_status 1.0 | yr3 L 13.75 detrain [(4, 12.64, 0.873), (12, 9.11, 0.47), (24, 6.3, 0.149)] | advanced peak 14.87 off26wk 6.28 regain wk80 27 wk90 72 | rantila kept 0.410 block2/1 0.960 | score 0.4018
detrain_status 2.0 | yr3 L 13.75 detrain [(4, 12.96, 0.91), (12, 10.15, 0.588), (24, 7.15, 0.246)] | advanced peak 14.87 off26wk 7.29 regain wk80 27 wk90 69 | rantila kept 0.426 block2/1 0.959 | score 0.6060
detrain_status 3.0 | yr3 L 13.75 detrain [(4, 13.14, 0.93), (12, 10.85, 0.669), (24, 8.04, 0.348)] | advanced peak 14.87 off26wk 8.36 regain wk80 27 wk90 68 | rantila kept 0.441 block2/1 0.957 | score 1.5748
detrain_status 0.0 score 0.4018 [('rantila_kept_frac', 0.394), ('rantila_block2_over_1', 0.962), ('bickel_third_kept', 1.727), ('detrain_halflife_wk', 6.0)]
detrain_status 1.0 score 0.4018 [('rantila_kept_frac', 0.41), ('rantila_block2_over_1', 0.96), ('bickel_third_kept', 1.727), ('detrain_halflife_wk', 6.286)]
detrain_status 2.0 score 0.4018 [('rantila_kept_frac', 0.426), ('rantila_block2_over_1', 0.959), ('bickel_third_kept', 1.727), ('detrain_halflife_wk', 6.571)]
detrain_status 3.0 score 0.4018 [('rantila_kept_frac', 0.441), ('rantila_block2_over_1', 0.957), ('bickel_third_kept', 1.727), ('detrain_halflife_wk', 6.857)]
```

Note on the registry: the detraining half-life oracle first measured a trained state (s = 0.6); it was corrected to Räntilä's novice population before R was scored. C's score is unchanged by the correction (0.4018, `rescore.txt` at detrain_status 0).
