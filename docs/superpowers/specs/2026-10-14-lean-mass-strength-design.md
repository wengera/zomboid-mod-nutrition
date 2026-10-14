# Lean-mass Strength and body-composition traits: design

Status: draft for Angus's review, 2026-10-14. Brainstormed in the session that closed Plan 12; each section below was presented and approved in turn, with the rulings in § 11.

Research behind it (copied to `docs/superpowers/research/2026-10-14-strength-redesign/` in the plan's first task, before any science row is minted):
- `vanilla-strength-rate.md`: vanilla Strength XP sources, pacing and days to level 10 on 42.21.
- `science-report.md` and `lean-science-part.tsv`: the first harvest (FFMI scale, multi-year gains, regain, gates).
- `hypertrophy-science-report.md` and `hypertrophy-science-part.tsv`: the 2015-2026 hypertrophy harvest (68 rows, 62 resolved). Its ids `H.n` and the first harvest's `S1.n` are provisional and become `S` ids at the mint.
- `trait-levers.md`: the engine's creation-trait levers, read on the 42.21 jar `4a0e9546ec`.
- `advanced-recomp-report.md` and `advanced-recomp-part.tsv` (ids `S3.n`): recomposition and the surplus in advanced natural lifters, the basis of the status-dependent energy gate (§ 5); `review-science-part.tsv` (ids `S4.n`): the review's harvest, Kelly 2009's FMI bands included. Both id sets are provisional like the others.

## 1. Goal

The Strength level becomes a pure reading of the character's lean mass.

Vanilla Strength XP stops building the level. It becomes a training signal, the analogue of the resistance-exercise stimulus that drives mTORC1 and muscle protein synthesis. On its own it builds nothing: lean mass grows only when the signal, enough protein and enough energy act together.

Progress gets harder in two ways as a character trains:
- the gain still available shrinks roughly exponentially;
- the signal needed to grow, and not merely hold, rises.

Lost lean mass comes back fast. The weight and strength traits describe body composition, are offered at creation for their points, and set the starting body. Nothing changes while a player is offline.

## 2. The scale

```
FFMI  = F / H²                         H = 1.70 m, fixed, sex-neutral; one shared constant, which K.acute.HEIGHT_M (1.75 today) also reads, so every BMI in the mod uses 1.70
level = 5 + (FFMI − 18.0) / 0.5        one level ≈ 1.445 kg of fat-free mass F
```

- At creation, the untrained average is level 5 (FFMI 18.0, F = 52.0 kg).
- The untrained natural cap is level 16.5 (FFMI 23.75), under Kouri's natural limit of 25.0 normalised to 1.80 m, which is 24.37 raw at 1.70 m (S1.1); Strong's cap, 18.5 (24.75), sits just above it, inside the soft limit (S1.4).
- The Strength perk shows `clamp(floor(level), 0, 10)`; the XP bar shows the fraction toward the next level.
- Above 10, see § 7. The mod's panel always shows the true level, for example "Strength 12.3".

## 3. Creation

### 3.1 What is offered
The creation screen offers 8 body traits: Weak, Feeble, Stout and Strong (muscle) at their vanilla costs, and Overweight and Obese (fat) and Underweight and Very Underweight (thin) at costs the mod sets, because vanilla gives those four `Cost = 0` and the creation lists show only a positive or a negative cost (trait-levers § 1.3). Overweight and Underweight carry `Cost = -6` and Obese and Very Underweight `Cost = -10`, so they give 6 and 10 points (Angus, 2026-10-14; § 11). The sign is vanilla's: a negative cost gives points, as Feeble's `Cost = -6` and Weak's `Cost = -10` do (trait-levers § 1.3), so the four mirror Feeble and Weak. Emaciated is reached only in play.

On 42.21, the five weight-band traits are hidden profession traits (`IsProfessionTrait = true`) that the creation lists filter out (trait-levers § 1).

The mod restates the full definition block of each offered trait in a shared script, named `base:<id>` in `module Base`, because a same-name block replaces the whole definition and resets every omitted key (trait-levers § 2). Each restated block:
- sets `IsProfessionTrait = false`;
- drops the vanilla Strength and Fitness `XPBoosts`, since the body now sets those levels;
- keeps vanilla's cost (the four weight traits take the costs above) and exclusions, and adds the missing pairs: Obese and Overweight both ways, and every pair inside a family (the four muscle traits, the four fat and thin traits).

Weight Gain and Weight Loss are restated without their `GrantedTraits`. They keep their place as intake-rate traits in the body model.

The descriptions are rewritten through the `UI_trait_*` translation keys to say what each trait now does.

### 3.2 What a pick does
A server `OnNewGame(player)` handler, guarded by `isServer()`, runs after vanilla's `applyTraits` and before the save (trait-levers §§ 3–4). It:
1. **Validates the picks.** The point total must be legal and no two picks may exclude each other; any illegal pick is stripped, latest first, and logged. The server checks neither of these itself.
2. **Builds the body:**

| Pick | Lean (F) | Natural cap | Set point | Fat |
|---|---|---|---|---|
| none | level 5 | level 16.5 | the start | FMI 4.5 kg/m² (13.0 kg at 1.70 m; the middle of Kelly 2009's male normal 3–6): 65.0 kg, BMI 22.5, 20 % fat |
| Feeble (−2) | level 3 | level 15.5 | the start | as picked |
| Weak (−5) | level 0 | level 14.0 | the start | as picked |
| Stout (+2) | level 7 | level 17.5 | the start | as picked |
| Strong (+4) | level 9 | level 18.5 | the start | as picked |
| Overweight | unchanged | unchanged | — | FMI 7.5 (21.7 kg): 73.7 kg, BMI 25.5 |
| Obese | unchanged | unchanged | — | FMI 12.5 (36.1 kg): 88.2 kg, BMI 30.5 |
| Underweight | lowered to reach BMI 18.0 at FMI 1.5 (4.3 kg, 8 % fat; Gallagher's male fat at BMI 18 is about 7 %, S1905 equation) | unchanged | the muscle pick's level | FMI 1.5 |
| Very Underweight | lowered to reach BMI 16.5 at FMI 1.0 (2.9 kg, 6 % fat), above the 4 % starvation floor | unchanged | the muscle pick's level | FMI 1.0 |

   - **Cap rule (Angus):** a muscle trait moves the start by its full vanilla Strength offset and the natural cap by half of it.
   - **Consequence of the cap rule (m5):** Weak gains the most absolute lean in year 1 (+9.5 kg against the average's +7.8 under points R and S, which share the growth constants), because the half-offset cap gives it the most headroom; relative gains are similar across people (S0589).
   - **Thin traits are depletion.** The lean they remove is below the remembered peak, which starts at the set point, so it comes back on the fast regain path (§ 6) and leaves the cap alone.
   - **Fat bands** are read through the character's effective sex (§ 8.1, § 13): the male cuts unless `NR.SexSpecific` is on.
   - **Weight** = F + fat mass. This replaces `K.body.split`'s band-anchored split of vanilla's starting weight.
3. **Writes the weight, the Strength level (§ 7) and the body traits (§ 8).** Vanilla's creation band swap on `LevelPerk` can leave a trait the player never picked, for example Out of Shape after Weight Gain (trait-levers § 3). The handler's trait write is final.

## 4. The training signal

- **Capture.** A server `AddXP` listener adds every positive Strength gain into today's slot of a 7-slot daily ring, after dividing out vanilla's multipliers: the protein factor the engine applied (×1.5 when 50 < proteins < 300, ×0.7 below −300; #2112, measured #2900) and the sandbox XP multiplier (`Global` under `GlobalToggle`, else the per-perk Strength value), so protein enters only through f_p and the XP sandbox does not scale biology.
- **Source weights.** A grant made while an `ISFitnessAction` runs counts 1; any other grant (melee hits, carrying, trees, barricades) counts `NR.StrengthIncidentalWeight` (default 0.35). Basis: hypertrophy rises with proximity to failure (H.11, H.12), indirect work counts fractionally (H.1). Without it, a survivor's incidental XP (about 500 a game day on the 90-minute day, vanilla-strength-rate § 4) reads about 10 sets a week and drives a never-trained character to level 14.4 in 10 years (sim, S = 10).
- **Conversion.** Weekly hard sets S = the ring's sum ÷ `NR.StrengthXPPerSet`. The default for `NR.StrengthXPPerSet` is the Strength XP of one vanilla Fitness set taken to exhaustion, measured by a live calibration run before the constant ships (§ 10). Until then it ships the provisional default 346 (one push-up bout from full endurance to the 0.25 stop, before vanilla's protein factor; vanilla-strength-rate § 4), which the calibration run replaces; the calibration reads push-ups with the protein factor divided out.
- **The XP never moves the level.** The next level write (§ 7) restores the level from F.
- **Replaced:** the resistance side of `NR_Kernel_Training` (the set-equivalents per rep, hit and tree). The aerobic side stays.

## 5. Growth

Every symbol is per character: F₀ is the set point, F_c the natural cap, P the remembered peak, and status s = (F − F₀)/(F_c − F₀), clamped to [0, 1].

```
S_g(s) = S_g0 · e^(β·s)                                     growth threshold, weekly hard sets
S_max(s) = S_max0 − (S_max0 − S_max1) · s                    the set cap falls with status (H.3, H.5, H.6)
G      = max(0, √min(S, S_max(s)) − √S_g(s)) / (√S_ref − √S_g0)   the signal's response; S_ref = 12 (H.1)
dF/dt  = k · (F_c − F) · G · f_p · f_e · f_alc              per week, applied at day close as 1/7; f_alc is K.partition.gAlc (0.65 above 0.5 g alcohol/kg/day, S0718, S0631)
```

| Constant | Default | Basis |
|---|---|---|
| S_g0 | 0.5 set | fitted (point R, bound reported); novices grow on about 1 set a week (H.8, H.1) |
| β | 3.0 | fitted (point R); a game choice in basis: the threshold rises from 0.5 set to 2.2 at s = 0.5 and 10 at s = 1. Indirect support from H.26, H.27, H.17 and H.24; contradicted by H.5 and H.25 (Aube 2022, Damas 2019); `NR.StrengthThresholdRise` = 0 disables the rise |
| S_max(s) | 30 sets untrained (S_max0) falling to 12 at s = 1 (S_max1, `NR.StrengthTrainedSetCap`) | the square-root fit's upper range (Pelland 2024/2026); the trained plateau bridges Pelland (H.1) and the advanced trials (H.3, H.5, H.6); fitted, point R |
| √ shape | — | Pelland's best fit of weekly sets against hypertrophy |
| k | the five-year shape | fitted (with β in place) so that an untrained average character on 20 sets a week with full gates reaches level 15 at 5 years (Angus: "Five year shape, tunable in settings"). The level-10 time and the per-trait times are then read off the fitted curve. Fitted: k = 0.00991 per week (point R, kept by point S since the anchor runs at full gates; 0.00874 under the draft's β 2.5, S_g0 1, flat set cap). The average character then reaches level 10 in 0.89 years and gains 7.8, 3.5, 1.7, 0.9 and 0.6 kg in years 1-5, against McDonald scaled ×0.75 (S1.15) of 6.8–8.5, 3.4–4.1, 1.7–2.0 and 0.7–1.0 |
| f_p | 0 at 0.4 g/kg/day, 0.5 at 0.8, 0.92 at 1.3, 1.0 at 1.6 and up; linear between | Morton 2018 (S0591), Tagawa 2020's 1.3 g/kg knee, the RDA (S0509). No per-meal cap: Trommelen 2023 (100 g against 25 g) |
| f_e | 0 at E₀(s, p) or deeper; linear to f_bal(s) at balance; linear from there to 1.0 at a surplus of surplus_full = 10 % of TDEE, at every status. f_bal(s) = 1 − 0.5 · s: 1.0 untrained, 0.75 at s = 0.5, 0.5 at the cap. E₀(s, p) = −650 · (1 − 0.5 · s) · (1 + 6.0 · (1 − s)² · clip((p − 1.6)/0.8, 0, 1)) kcal/day: −650 untrained and −325 at the cap before the protein term | The status-dependent gate of the advanced-recomposition harvest (§ 9 of its report), adopted by Angus on 2026-10-14 and refitted as point S (§ 5.2). **f_bal:** Helms 2023 (S1.29, S3.16: maintenance, +5 % and +15 % gave no different muscle thickness at an intermediate level); Moro 2016 (S3.1: DXA FFM +0.64 and +0.48 kg, both n.s., over 8 weeks at 100 % of needs near FFMI 23); Isola 2025 (S3.2: physique controls without systematic change over about 46 weeks); Ahtiainen 2003 (S1.11). f_bal(1) is weakly identified, since anything from 0.3 to 1 fits; 0.5 follows Hatamoto's energy-accretion hint (S0606). **surplus_full:** Helms 2023, Garthe 2013 (S1.30), Gavanda 2026 (S3.20) and Iraki 2019 (S1.32): beyond about +10 %, a surplus adds fat only, at every status. **E₀:** Murphy & Koehler 2022 (S1.28: −500 stops net lean gain in mostly sedentary novices, met here as growth minus the § 5.1 loss); Garthe 2011 (S3.12: a −19 % deficit allowed a DXA lean gain, −30 % did not); Moro 2016's time-restricted arm (S3.1: fat 10.90 to 9.28 kg with FFM held; the deficit of about −250 kcal/day is an inference from that loss); Roth 2023 (S3.11); Longland 2016 (S0064) for the protein deepening |

- **Signal, protein and energy multiply.** Without the signal, protein and a surplus build no muscle. Overfeeding's lean share goes to a new labile-lean field `lx` (§ 5.1), which counts in weight but not in the level or REE (Bray 2012, S0605; whether it is muscle is open, H.67).
- **Protein** is the closed day's grams per kg from the existing `p7` ring.
- **Energy** is the closed day's balance from the existing `eb7` ring.
- **Low volume stalls** where S_g(s) meets S: that is the "harder even to grow" effect.

### 5.1 The energy and protein partition

The growth law above replaces `K.partition.leanGain`, `K.partition.headroom`, `G0`, `LM_CAP_RATIO`, `gEnergy` and the `DEFICIT_HALF*` constants. The partition keeps its role as the only writer of `fm`, `lm` and the new `lx`, once per closed day:

- **Surplus (E ≥ 0).** The day's growth g is paid first at RHO_LEAN. The remainder R splits with the lean weight share x = forbes(M) · clip((p − 0.8)/0.8, 0, 1) · (1 − T) into `lx` (capped at 0.05 · F) and fat. forbes(M) = 10.4/(10.4 + M) (Forbes, S0054, S0055; coefficient open, S1056), and T = min(1, S/10) (H.47). If g exceeds the surplus, fat pays the difference. At balance, `lx` decays toward 0 on a 28-day time constant.
- **Deficit (E < 0).** The lean weight share is forbes(M) · prot, with prot = clip(1 − 0.35 · T − 0.6 · clip((p − 0.8)/0.8, 0, 1), 0.10, 1) (Mettler 2010, PMID 19927027; Pasiakos 2013, PMID 23739654; Weinheimer 2010, S0072; Heymsfield 2014, PMID 24447775; Helms 2014, S0599; Cava 2017, S0609). Fat pays the rest up to Alpert's ceiling (S0056); the overflow is split by prot as the kernel does today. `lx` pays any lean loss first. The growth g still runs (recomposition) and is funded from fat. There is no separate training-age term: the larger lean loss of male physique athletes in contest preparation (S3.3, S3.4, S3.5) reads as a leanness effect, which the Forbes share and Alpert's ceiling already carry.
- **Trained characters and the surplus.** By default the gate at balance falls with status, f_bal(s) = 1 − 0.5 · s, and a +10 % surplus opens it fully at every status (§ 5). Most of the slowing near the cap comes from the headroom term k · (F_c − F), not from energy: at s = 0.9, a year at maintenance on 20 sets gains +0.15 kg (point S). No trial in natural lifters near their ceiling compares a surplus with maintenance by a direct muscle measure (S3.29, open). In intermediates (Helms 2023, S1.29, S3.16) and elite non-lifters (Garthe 2013, S1.30), the surplus added fat, not detectably more muscle. Antonio 2015's +1.5 kg (H.43, S3.21) and Garthe 2011's +2.1 % (S3.12) sit inside DXA's glycogen and water band (Bone 2017, S3.22). `NR.StrengthTrainedNeedsSurplus` (0 by default) further scales the gate at balance by (1 − value · s): at 1, a trained character gains little at maintenance and nets lean only through surplus and cut cycles, Angus's stricter premise. No trial compares bulk-cut cycles with maintenance over a year; the bulk-cut recommendation is practitioner consensus (Iraki 2019, S1.32).
- **Not modelled.** Protein's extra energy cost (Antonio 2014, PMID 24834017: no fat gain on +800 kcal of protein) belongs to the energy model, not to the partition.

### 5.2 The fit (point S)

Point S refits point R's model with the status-dependent gate. The method is a grouped coordinate search over growth, energy, deficit and memory grids, with Angus's anchor as a hard constraint: k is re-solved for every growth candidate so that the average character reaches level 15 in 5 years on 20 sets at full gates. The registry is R's 33 oracles plus 15 new ones:
- Moro 2016 (S3.1) at maintenance and in its time-restricted arm;
- Isola 2025's controls (S3.2);
- Helms 2023's +5 % and +15 % arms against maintenance (S1.29, S3.16);
- the report's four § 9 checks at s = 0.9, F near F_c;
- a degenerate check at s = 0.9;
- Buechel 2026 (S3.4) and Roth 2023 (S3.11), report only.

Every new weighted oracle passes. At s = 0.9 over 8 weeks:
- balance gives ΔF = 0.04 % with fat steady;
- +10 % gives 1.8 × the balance gain, 0.07 % of F, with 97 % of the weight gain as fat;
- −500 kcal/day at 3.5 kg of fat gives ΔF = −1.3 kg.

The growth constants come back unchanged from R (β 3.0, S_g0 0.5, S_max1 12, k 0.00991). The trajectories, the regain and the detraining runs therefore match R's.

**Fitted gate.**
- E₀ = −650 and a_nov = 6.0. The free fits run both to their grid bounds (−1000, 8.0), pulled by Garthe 2011's slow arm alone (S3.12: +2.1 % DXA lean, inside the glycogen and water band, S3.22). Without that oracle, moving past (−650, 6.0) gains under 0.004 of score.
- E0_drop 0.5, f_bal(0) 1.0, f_bal drop 0.5 and surplus_full 0.10 are Angus's values. The fit is flat on E0_drop and surplus_full, f_bal drop 0.5 is the best value without Garthe's slow arm, and f_bal(0) sits at its physical bound of 1.
- The deficit side refits to p_hi 1.6 g/kg, at its grid bound; wT 0.35, wP 0.6 and the floor 0.10 are unchanged.

**Named conflicts.**
- Garthe 2011's slow arm (0.28 kg against 0.8–1.8) cannot be met at a status-dependent gate together with Murphy & Koehler (S1.28). Meeting it needs E₀ near −1000 with no status drop, which is the free fit, outside the report's bounds.
- Garthe 2013's fat difference (3.3 kg against 0.8–2.5) belongs to the energy side.
- Longland's high-protein arm (+0.52 kg against 0.6–1.8) misses narrowly.
- Buechel's contest-prep FFM loss (−0.56 kg against −0.9 to −2.6; mixed sex, report only) is under-read: the leanness penalty is mild.
- The growth misses H.8 and Aube 2022 are R's.

The record is in `refit-report.md`.

## 6. Maintenance, detraining and regain

- **Maintenance threshold:** S_m(s) = S_g(s)/3 (Bickel 2011, Spiering 2021). That it holds at every status is a game choice (H.64).
- **Grace:** after 14 consecutive online days with S below S_m, detraining starts. Any day at or above S_m resets the counter.
- **Detraining:** `dF/dt = −λ(s) · (F − F₀) · (1 − S/S_m)`, with λ(s) = ln 2 / (6 weeks · (1 + 2s)): 6 weeks for a novice (Räntilä 2025, H.51: 4.9–9.2 weeks), 18 weeks at the cap. The status term is a game choice resting on S1.24 (loss follows the build's time course); no study measures advanced detraining (H.64, H.68). It acts only while F > F₀, and is integrated exactly per closed day (F − F₀ multiplied by exp(−λ·Δt)), so no time scale overshoots F₀.
- **Starvation** takes F through the existing partition deficit arm, independent of training.
- **Remembered peak P:** P = max(P, F) at each day close. P decays toward F with a 2-year half-life (Rahmati 2022 meta and Serrano 2025: human myonuclei are not permanent; the memory is epigenetic, Seaborne 2018).
- **Regain:** while F < P, dF/dt = max(the § 5 growth, λ_r · (P − F) · min(1, G) · f_p · f_e), with λ_r = ln 2 / 6 weeks. The max form reproduces Räntilä's equal second block (0.94 of the first under point S; the sum form overshoots and is not used). Retraining is at least as fast as naive training (Räntilä 2025 equal blocks; Seaborne 2018 1.6×, n = 7). Its use for advanced lifters is a game choice (H.68).

- **Unidentified constants (m7):** the maintenance share m = 1/3 (Bickel H.13; H.64 open), λ_r = 6 weeks (H.52, H.53 between) and the labile-lean cap 0.05·F (Bray's 2.9 kg, about 5 % of FFM) rest on no oracle, and the stability probe reads flat on them. They are game choices.

## 7. Writing the level, and BeyondTen

At day close, and once at creation, the server computes level L from F:
- **floor(L) ≤ 9:** if the native Strength level differs, the server sets it and pins native XP at that level's starting total plus the fraction toward the next level (the bar); the `AddXP` listener re-pins at once when a grant crosses a level total (event-driven, no tick work).
- **floor(L) ≥ 10:** native level 10, with native XP parked at the level-9 total (337 500), so the `AddXP` event keeps firing with the full amount (vanilla returns before the event once XP reaches the level-10 total, #2109); the vanilla ten-minute level check is guarded so the parked XP never loses the level, as BeyondTen does (#2850, #2856). A Task 0 check confirms grants at level 10 reach the listener at full size.
  - Vanilla's `XpUpdate` band swap then moves Weak, Feeble, Stout and Strong. A Task 0 live check confirms the swap fires on the mod's write.
  - The short-term carry factor (dehydration, sleep, caffeine) stays as it is.
- **floor(L) > 10 with BeyondTen loaded** (`BT.API_VERSION == 1`):
  - native Strength stays at 10;
  - the server writes BeyondTen's stored XP for L through `BT.SetStoredXP(player, Perks.Strength, value)`, server-authoritative, with the value from BeyondTen's own `GetTotalMasteryCost`;
  - native XP is never written while the native level is 10, because BeyondTen parks its reservoir there.
- **floor(L) > 10 without BeyondTen:** the perk shows 10; the extra F still counts in weight and in the panel.

## 8. Body traits in play

Three axes are read at day close, from the record:

| Axis | Measure | Trait switches (vanilla traits, for the engine-only penalties) |
|---|---|---|
| Fat load | fat-mass index (fat kg / H²), Kelly 2009 (PMID 19753111) cuts through the effective sex (§ 13): male (White subjects' table) overweight above 6, obese above 9 kg/m² (S4.9) | Overweight above 6, Obese above 9 |
| Muscle | the lean level | Weak, Feeble, Stout, Strong through vanilla's own band swap (§ 7) |
| Thinness | BMI at H, from F + fat | Underweight below 18.5, Very Underweight below 17, Emaciated below 16 (the WHO thinness grades) |

### 8.1 The fat bands

The panel's Body fat word reads the mod's existing `K.view.FAT_CUTS_*`, and the fat traits read the FMI cuts of § 8, both through the character's effective sex (§ 13), so by default every character reads the male values:

| Band | Body fat from (male table) |
|---|---|
| Very lean | below 6 % (S1910) |
| Lean | 6 % |
| Healthy | 8 % (S1905) |
| High | 20 % |
| Very high | 25 % |

The lean scale is sex-neutral and ignores the option.

- **Precedence:** a thinness trait excludes the fat traits.
- **Damping:** a switch needs a margin of 0.5 BMI or 0.3 FMI past its cut, and switches are checked once a day.
- **Writes:** server-side through `getCharacterTraits():add/remove` (wall map G3), followed by the trait push (`NR.pushTraits`, #2099, #2603). `NR_Server_Weight`'s band refresh and repair through `applyTraitFromWeight` (vanilla's 65/75/85/100 kg bands) are removed: the § 8 axes own the five band traits. The engine's own refresh does not run while `Nutrition = false` (#2644).
- **Effects:**
  - The vanilla traits keep the effects only the engine applies: run speed, endurance drain, climbing, falls, grappling, the recovery multiplier and the Fitness XP gate.
  - The mod's continuous effects (the per-kg activity bill, the endurance and thermal steps) are unchanged; any tuning of them is outside this spec.
- **Supersedes** the Section 1b fat-only Underweight rule: a starved character turns Underweight by losing both fat and muscle.

## 9. State, removals and offline time

### 9.1 New fields on `record.body`
| Field | Meaning |
|---|---|
| F0 | the set point |
| Fc | the natural cap |
| P | the remembered peak |
| sig7 | the 7-day Strength XP ring |
| grace | days below maintenance |
| lx | the labile lean (water, glycogen, organ): weight only (§ 5.1) |

`lm` is F.

### 9.2 Removed (the mod is unreleased: no migration)
- `NR_Kernel_Strength`'s neural term, memory floor, cumulative deficit, disuse term, fSlow ceiling and the rise-hold and hourly-fall write policy;
- the resistance side of `NR_Kernel_Training`; the deficit protection's dose input `dStr` becomes T = min(1, S/10) from the § 4 signal;
- `K.partition.leanGain`, `headroom`, `gEnergy`, `G0`, `LM_CAP_RATIO`, `P_LO`, `P_HI`, `SURPLUS_RAMP` and `DEFICIT_HALF*` (§ 5.1 replaces them); `gAlc` stays, as a factor on g (§ 5);
- `K.body.split` and its build offsets; the heal and store fallbacks that call it (`NR_Kernel_Heal`, `NR_Kernel_Store`) build the § 3.2 no-trait body instead;
- `lm0`, where F0 replaces it; `lm0dis` stays (the disuse arm's own anchor);
- `body.r`, unless the plan keeps a per-character responsiveness factor (H.25, H.28, H.29), in which case it multiplies k.

### 9.3 Offline time (Angus: "I do not expect character stats to change when they are offline")
- The record's day calendar (`dayIndex`, the day stamps) advances only on game days the player is online.
- A reconnect after any gap resumes the calendar where it stopped. The day-close catch-up (`MAX_CLOSES`) closes no missed days.
- Every daily and weekly ring is audited (`p7`, `eb7`, `mass7`, `bandWeek`, `sig7` and the training rings), and so are the grace counter and P's decay: each counts only online days.

### 9.4 Cost (Rule 6)
- The `AddXP` listener is an event-driven add, with no per-tick work.
- Growth, traits and the level write run at day close, once per player per online game day. The plan benches the day close before and after.

## 10. Sandbox options

The options follow the existing `NR.<Name>` pattern in `42.21/media/sandbox-options.txt`. Every default is a cited value or a labelled game choice; "Fixed" means a kernel constant, not an option.

| Name | Type | Min | Max | Default | Basis |
|---|---|---|---|---|---|
| H (height) | fixed | — | — | 1.70 m, shared with K.acute | ruling; M2 |
| `NR.StrengthTimeScale` (the biology clock: 1.0 means one game day is one biological day): multiplies the per-day growth, detraining, regain and peak-decay rates and divides the grace days; S stays the ring's sets per 7 game days, unscaled | double | 0.25 | 30 | 1.0 | ruling; OnsetSpeed precedent; M5, M12 |
| `NR.StrengthXPPerSet` | double | 50 | 2000 | 346 (provisional) | vanilla-strength-rate § 4; calibration run |
| `NR.StrengthIncidentalWeight` (new) | double | 0 | 1 | 0.35 | H.1 fractional, H.11, H.12; game choice; C6 |
| `NR.StrengthCapLevel` | double | 12 | 20 | 16.5 | ruling; S1.1, m3 |
| `NR.StrengthTraitCapShare` | double | 0 | 1 | 0.5 | Angus |
| `NR.StrengthRate` (a multiplier on the fitted k = 0.00991/wk) | double | 0.25 | 4 | 1.0 | fit R, kept by S; anchor |
| `NR.StrengthThreshold` (S_g0, sets/wk) | double | 0.25 | 1.0 | 0.5 | fit (bound reported); H.1, H.8; guarded, M6 |
| `NR.StrengthThresholdRise` (β) | double | 0 | 4 | 3.0 | fit; H.26, H.27, H.17, H.24 (against H.5, H.25); guarded |
| S_ref | fixed | — | — | 12 | H.1 |
| S_max0 | fixed | — | — | 30 | H.1 (data thin above 25–30) |
| `NR.StrengthTrainedSetCap` (S_max1, new) | double | 8 | 30 | 12 | fit (bound reported); H.3, H.5, H.6 |
| f_p knots | fixed | — | — | 0 @ 0.4, 0.5 @ 0.8, 0.92 @ 1.3, 1.0 @ 1.6 g/kg | S0591, S0592, H.40, S0509 |
| `NR.StrengthProteinFull` (scales the knots) | double | 1.0 | 3.0 | 1.6 | S0591, S0592 |
| `NR.StrengthDeficitZero` (E₀ at s = 0, kcal/day) | double | −2000 | −200 | −650 | fit S (the free fits run to −1000, pulled by Garthe 2011's slow arm alone); S1.28, S0064, S3.12, S3.1 |
| `NR.StrengthDeficitZeroStatusDrop` (new; E₀(s) = E₀ · (1 − value · s)) | double | 0 | 0.9 | 0.5 | Angus's gate (−325 at the cap); flat in the fit; S3.1 |
| `NR.StrengthNoviceDeficitDepth` (a_nov, new) | double | 0 | 10 | 6.0 | fit S (the fits run to the grid bound 8, pulled by Garthe 2011's slow arm; without it, 8 gains under 0.004 of score); S0064 |
| `NR.StrengthBalanceGate` (f_bal at s = 0, new) | double | 0.5 | 1.0 | 1.0 | fit S, at its physical bound (the gate never exceeds 1); S1.29, S3.16 |
| `NR.StrengthBalanceGateStatusDrop` (new; f_bal(s) = f_bal · (1 − value · s)) | double | 0 | 0.7 | 0.5 | Angus's gate; fit S (the best value without Garthe 2011's slow arm); S3.1, S3.2, S1.11, S0606 |
| `NR.StrengthSurplusFull` (new; the surplus, as a share of TDEE, that opens the gate fully) | double | 0.02 | 0.30 | 0.10 | Angus's gate; flat in the fit (0.05–0.15 within 0.02 of score); S1.29, S3.16, S1.30, S3.20, S1.32 |
| `NR.StrengthTrainedNeedsSurplus` (new) | double | 0 | 1 | 0 | evidence default; 1 = Angus's premise (item 10) |
| forbes c | fixed | — | — | 10.4 kg | S0054, S0055 (S1056 open) |
| `NR.LeanLossTrainingProtect` (wT, new) | double | 0 | 0.9 | 0.35 | fit; S0072, H.47, S0609 |
| `NR.LeanLossProteinProtect` (wP, new) | double | 0 | 0.9 | 0.6 | fit S (0.75 scores the same); Mettler 2010, Pasiakos 2013, S0599 |
| `NR.LeanLossProtectFloor` (the prot floor, new) | double | 0 | 0.5 | 0.10 | fit S (0.05 scores 0.085 lower, all but 0.004 of it through Garthe 2011's slow arm) |
| `NR.LeanLossProteinFull` (p_hi, g/kg/day of full protein protection, new) | double | 1.2 | 3.0 | 1.6 | fit S, at its grid bound (1.6–2.8; 2.0 costs 0.14 of score); S0599 (2.3–3.1 g/kg FFM), S0064 |
| labile-lean cap / decay | fixed | — | — | 0.05·F / 28 d | S0605 (game choice, H.67) |
| `NR.StrengthMaintainShare` | double | 0.1 | 1.0 | 0.333 | H.13, S0616 (unidentified; H.64 open) |
| `NR.StrengthGraceDays` | integer | 0 | 60 | 14 | S1.18, S1.26, H.16 |
| `NR.StrengthDetrainHalfLifeWeeks` | double | 2 | 26 | 6 | H.51 |
| `NR.StrengthDetrainStatusSlowing` (new) | double | 0 | 4 | 2.0 | S1.24 (game choice; H.64, H.68) |
| `NR.StrengthRegainHalfLifeWeeks` | double | 1 | 26 | 6 | H.52, H.53 (unidentified) |
| `NR.StrengthPeakHalfLifeYears` | double | 0.25 | 20 | 2 | H.54, H.60, S0620, H.57 |
| `NR.SexSpecific` | boolean | — | — | false | Angus |

At load the options are checked: if S_g0 · e^(0.87β) ≥ S_max(0.87), level 15 is unreachable at any rate; the server logs the combination and falls back to the defaults for β, S_g0 and S_max1.

Pointless or dangerous options, kept out:
- A raw `NR.StrengthRate` = k: its meaning shifts with β, S_g0 and S_max1, so the option is a multiplier on the fitted k.
- `NR.StrengthThreshold` above about 1.0 at β 3: the anchor becomes unreachable (the guard above).
- `NR.StrengthTimeScale` above about 7 with a daily Euler step: it overshoots, so the detraining and decay steps are integrated exactly.
- `NR.StrengthMaintainShare` 0: detraining never runs, which may be intended; the option's tooltip says so.

## 11. Rulings made in the brainstorm

- **Scale.** Ruling: the level is FFMI at a fixed 1.70 m, sex-neutral — Angus's choice ("assume average height always and make it gender-indifferent for now") — cost if wrong: none planned; a sex term is excluded by the ruling below.
- **Stimulus.** Ruling: vanilla Strength XP is the training signal and replaces the mod's own resistance set-equivalents — Angus chose "Vanilla Strength XP", and the calibration ties it to one hard set — cost if wrong: incidental carrying may count as more sets than real training does, and a per-source discount is added.
- **Time.** Ruling: one game day is one biological day by default, with a sandbox multiplier — Angus's choice — cost if wrong: most characters never reach high levels on default servers; operators compress it.
- **Threshold.** Ruling: the growth threshold rises with status, β = 3.0 (fitted, point R), sandbox-tunable — Angus's premise, with mixed evidence — cost if wrong: advanced characters stall early; β = 0 restores headroom-only.
- **Curve.** Ruling: the five-year shape, with the cap at 16.5, chosen over the literature's first year — Angus: "Five year shape, tunable in settings" — cost if wrong: none measured; the fitted curve's year 1 (7.8 kg) sits inside the literature calibration (6.8–8.5 kg).
- **Traits.** Ruling: the vanilla strength-trait order is kept (Weak is the stronger penalty) — Angus — cost if wrong: none at the engine level.
- **Creation.** Ruling: 8 traits offered, Emaciated excluded, and the picks are re-validated on the server — Angus — cost if wrong: validation code that a live check must prove sees the whole pick list.
- **Peak memory.** Ruling: P decays with a 2-year half-life, not permanently — Rahmati 2022 and Serrano 2025 overturn the first harvest's "might be permanent" (S1.21) — cost if wrong: regain after a multi-year break is slower than players expect.
- **No sex-specific rules by default.** Ruling: one mod-wide option, `NR.SexSpecific` (default off); when it is off every character uses the male values everywhere the mod indexes by sex (§ 13) — Angus (2026-10-14): "I dont want gender specific rules, base game treats them equally", then "we can flag this as an option however, just default it to off", then "Lets just use male values for females if its disabled" — cost if wrong: by default a female character's requirements and body bands are the male studies' values (for example the iron requirement and the fat bands).
- **Energy gate.** Ruling: the growth gate's energy factor depends on training status, with f_bal(s) = 1 − 0.5 · s at balance, full at +10 % of TDEE at every status, and zero at E₀(s) = −650 · (1 − 0.5 · s) times the protein term (point S). The deficit side keeps the Forbes share and Alpert's ceiling with no training-age term, and the stricter premise stays as `NR.StrengthTrainedNeedsSurplus`, default 0 — Angus (2026-10-14): "Adopt the training-status-dependent energy gate … as the default, and refit the constants", the values being "starting values, not fixed", fitted within the report's bounds — cost if wrong: f_bal at the cap is weakly identified (0.3 to 1 all fit), and no trial compares a surplus with maintenance in near-ceiling naturals (S3.29), so an advanced character's gain at maintenance may be off by up to a factor of two either way; the headroom term keeps either inside DXA noise.
- **Creation costs.** Ruling: Overweight and Underweight take `Cost = -6`, and Obese and Very Underweight `Cost = -10`, in vanilla's sign, where a negative cost gives points as Weak's `-10` does — Angus (2026-10-14): "Overweight and Underweight give 6 points; Obese and Very Underweight give 10" — cost if wrong: a fat or thin start becomes a cheap point source if its play penalties are mild; the costs are script values that a later plan can retune.

## 12. Testing and evidence

### 12.1 Kernel tests (lupa)
Each check has a mutation pass that shows it fails:
- the curve: on 20 sets with full gates, an average character reaches level 15 at 5 years; Weak never reaches 15; Feeble is below the average at every year; Stout and Strong reach 15 sooner;
- a low weekly volume stalls where S_g(s) = S;
- protein or a surplus without the signal gives ΔF = 0;
- the status-dependent gate at s = 0.9 with F near F_c, over 8 weeks: balance gives ΔF < 0.5 %; +10 % gives no more than twice the balance gain, under 1 %, mostly as fat; −500 kcal/day at contest fat gives ΔF ≤ 0;
- detraining has a half-life of 6 weeks after a 14-day grace;
- retraining a novice takes no longer than the first block (Räntilä);
- the creation table in § 3.2, cell by cell;
- the trait switches, with their damping;
- no state changes across an offline gap.

The golden trace is re-recorded under named causes.

### 12.2 Live (harness, § 5 rules)
- **Task 0 checks:**
  - a restated trait block replaces vanilla's on both sides;
  - the Lua list edits bind;
  - the client sees the server's definitions;
  - the `OnNewGame` writes reach the client;
  - an illegal pick list reaches `OnNewGame`;
  - vanilla's band swap fires on the mod's level write;
  - the `AddXP` listener sees every Strength source.
- **The XP-per-set calibration run:** one push-up set from full endurance to the 0.25 stop, at a protein store between −300 and 50 (factor 1), its Strength XP logged against wall time.
- **A BeyondTen run** with the workshop mod in a test profile.
- **An offline-gap run:** a disconnect over several game days changes no stat.

### 12.3 Registers
- The two harvests' rows are minted after their reports are copied into the research folder.
- The first harvest's S1.21 ("might be permanent") and the per-meal cap reading of S0065 are qualified or superseded by the newer rows.
- The stale claim rows #0529 and #3344 (the 90-minute default day) and #2115 and #2116 (the 42.21 carry roll) are corrected.

## 13. The mod-wide sex option

`NR.SexSpecific` (boolean, default off) decides each character's effective sex index: the engine's `isFemale` when the option is on, and 1 (male) for everyone when it is off.

- **Stored raw, resolved at use.** `record.body.sex` keeps the engine's value, and one helper resolves the effective index wherever the mod reads it. Changing the option mid-save then takes effect at once and needs no record rewrite.
- **Server readers:** the nutrient requirements and the choline factor (`NR_Server_Nutrients`), fluids, the Widmark r, iron and calcium (`NR_Kernel_Interact`), the heal reference (`NR_Kernel_Heal`) and the effects (`NR_Server_Effects`).
- **Client readers:** the Body fat word (`NR_Client_View`) and the tooltip's sex (`NR_Client_Tooltip`) read the option from SandboxVars.
- **Tests:** with the option off, a female character's every sex-indexed output equals a male's. With it on, today's values are unchanged, so the golden trace does not move for a male character.

## 14. Out of scope

- A height term on the lean scale. A sex term is excluded by ruling, not deferred.
- Tuning the mod's continuous fat-load effects.
- Fitness (aerobic) levels.
- Any change to vanilla's carry formula beyond the Strength level it reads.
- Age (PZ has no age stat, though the evidence would support an older-adult maintenance rise, H.13), sleep's effect on synthesis and illness (neither harvested). The per-meal window is none, which is correct (Trommelen, H.38). The energy cost of lean is already in REE (`NR_Kernel_Energy.lua:263` reads `body.lm`; S0011).
