# Lean-mass Strength and body-composition traits: design

Status: draft for Angus's review, 2026-10-14. Brainstormed in the session that closed Plan 12; each section below was presented and approved in turn, with the rulings in § 11.

Research behind it (copied to `docs/superpowers/research/2026-10-14-strength-redesign/` in the plan's first task, before any science row is minted):
- `vanilla-strength-rate.md`: vanilla Strength XP sources, pacing and days to level 10 on 42.21.
- `science-report.md` and `lean-science-part.tsv`: the first harvest (FFMI scale, multi-year gains, regain, gates).
- `hypertrophy-science-report.md` and `hypertrophy-science-part.tsv`: the 2015-2026 hypertrophy harvest (68 rows, 62 resolved). Its rows were minted as S1951-S2017 and the first harvest's as S1915-S1950 (commit b6b73a49); the spec cites the minted ids.
- `trait-levers.md`: the engine's creation-trait levers, read on the 42.21 jar `4a0e9546ec`.
- `advanced-recomp-report.md` and `advanced-recomp-part.tsv` (ids `S3.n`): recomposition and the surplus in advanced natural lifters, the basis of the status-dependent energy gate (§ 5); `review-science-part.tsv` (ids `S4.n`): the review's harvest, Kelly 2009's FMI bands included. Minted as S2018-S2048 and S2049-S2061.

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
- The untrained natural cap is level 16.5 (FFMI 23.75), under Kouri's natural limit of 25.0 normalised to 1.80 m, which is 24.37 raw at 1.70 m (S1915); Strong's cap, 18.5 (24.75), sits just above it, inside the soft limit (S1918).
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
- **Source weights.** A grant made while an `ISFitnessAction` runs counts 1; any other grant (melee hits, carrying, trees, barricades) counts `NR.StrengthIncidentalWeight` (default 0.35). Basis: hypertrophy rises with proximity to failure (S1961, S1962), indirect work counts fractionally (S1951). Without it, a survivor's incidental XP (about 500 a game day on the 90-minute day, vanilla-strength-rate § 4) reads about 10 sets a week and drives a never-trained character to level 14.4 in 10 years (sim, S = 10).
- **Conversion.** Weekly hard sets S = the ring's sum ÷ `NR.StrengthXPPerSet`. The default for `NR.StrengthXPPerSet` is the Strength XP of one vanilla Fitness set taken to exhaustion, measured by a live calibration run before the constant ships (§ 10). Until then it ships the provisional default 346 (one push-up bout from full endurance to the 0.25 stop, before vanilla's protein factor; vanilla-strength-rate § 4), which the calibration run replaces; the calibration reads push-ups with the protein factor divided out.
- **The XP never moves the level.** The next level write (§ 7) restores the level from F.
- **Replaced:** the resistance side of `NR_Kernel_Training` (the set-equivalents per rep, hit and tree). The aerobic side stays.

## 5. Growth

Every symbol is per character: F₀ is the set point, F_c the natural cap, P the remembered peak, and status s = (F − F₀)/(F_c − F₀), clamped to [0, 1].

```
S_g(s) = S_g0 · e^(β·s)                                     growth threshold, weekly hard sets
S_max(s) = S_max0 − (S_max0 − S_max1) · s                    the set cap falls with status (S1953, S1955, S1956)
G      = max(0, √min(S, S_max(s)) − √S_g(s)) / (√S_ref − √S_g0)   the signal's response; S_ref = 12 (S1951)
dF/dt  = k · (F_c − F) · G · f_p · f_e · f_alc              per week, applied at day close as 1/7; f_alc is K.partition.gAlc (0.65 above 0.5 g alcohol/kg/day, S0718, S0631)
```

| Constant | Default | Basis |
|---|---|---|
| S_g0 | 0.5 set | fitted (point R, bound reported); novices grow on about 1 set a week (S1958, S1951) |
| β | 3.0 | fitted (point R); a game choice in basis: the threshold rises from 0.5 set to 2.2 at s = 0.5 and 10 at s = 1. Indirect support from S1976, S1977, S1967 and S1974; contradicted by S1955 and S1975 (Aube 2022, Damas 2019); `NR.StrengthThresholdRise` = 0 disables the rise |
| S_max(s) | 30 sets untrained (S_max0) falling to 12 at s = 1 (S_max1, `NR.StrengthTrainedSetCap`) | the square-root fit's upper range (Pelland 2024/2026); the trained plateau bridges Pelland (S1951) and the advanced trials (S1953, S1955, S1956); fitted, point R |
| √ shape | — | Pelland's best fit of weekly sets against hypertrophy |
| k | the five-year shape | fitted (with β in place) so that an untrained average character on 20 sets a week with full gates reaches level 15 at 5 years (Angus: "Five year shape, tunable in settings"). The level-10 time and the per-trait times are then read off the fitted curve. Fitted: k = 0.00991 per week (point R, kept by point S since the anchor runs at full gates; 0.00874 under the draft's β 2.5, S_g0 1, flat set cap). The average character then reaches level 10 in 0.89 years and gains 7.8, 3.5, 1.7, 0.9 and 0.6 kg in years 1-5, against McDonald scaled ×0.75 (S1929) of 6.8–8.5, 3.4–4.1, 1.7–2.0 and 0.7–1.0 |
| f_p | 0 at 0.4 g/kg/day, 0.5 at 0.8, 0.92 at 1.3, 1.0 at 1.6 and up; linear between | Morton 2018 (S0591), Tagawa 2020's 1.3 g/kg knee, the RDA (S0509). No per-meal cap: Trommelen 2023 (100 g against 25 g) |
| f_e | 0 at E₀(s, p) or deeper; linear to f_bal(s) at balance; linear from there to 1.0 at the full-growth surplus E_full(s) = surplus_full · (1 − full_drop · s) · TDEE, with surplus_full = 0.10 and full_drop = 0.5: +10 % of TDEE untrained, +7.5 % at s = 0.5, +5 % at the cap. f_bal(s) = 1 − 0.5 · s: 1.0 untrained, 0.75 at s = 0.5, 0.5 at the cap. E₀(s, p) = −650 · (1 − 0.5 · s) · (1 + 6.0 · (1 − s)² · clip((p − 1.6)/0.8, 0, 1)) kcal/day: −650 untrained and −325 at the cap before the protein term | The status-dependent gate of the advanced-recomposition harvest (§ 9 of its report), adopted by Angus on 2026-10-14 and refitted as point S; the full-growth surplus that shrinks with status is the surplus harvest's (§ 8 of its report), refitted as point T (§ 5.2). **f_bal:** Helms 2023 (S1943, S2033, S2063: maintenance against a moderate and a large surplus gave no different muscle thickness at an intermediate level, group-model BF10 0.32–0.77 at every site); Moro 2016 (S2018: DXA FFM +0.64 and +0.48 kg, both n.s., over 8 weeks at 100 % of needs near FFMI 23); Isola 2025 (S2019: physique controls without systematic change over about 46 weeks); Ahtiainen 2003 (S1925). Henselmans 2026 (S2064, S2065: in men of about 10 years' training, about +250 to +485 kcal/d over habitual intake for 8 weeks gave DXA lean +0.76 kg, 95 % CI −0.19 to 1.69, with elbow-flexor thickness +0.05 cm, −0.09 to 0.19). f_bal(1) is weakly identified, since anything from 0.3 to 1 fits; 0.5 follows Hatamoto's energy-accretion hint (S0606). **E_full:** the ISSN position stand (S2069), Iraki 2019 (S1946) and Garthe 2013's authors (S2068: 200–300 kcal/d for highly trained athletes) put the advanced lifter's surplus below the novice's. Helms 2023's "+5 %" arm reported +489 kcal/d over its maintenance phase and its "+15 %" arm +719 (S2062), and both gained 3.3 kg (S2033), so the trial holds no small-surplus arm. Beyond the full point a surplus adds fat only (Helms 2023; Garthe 2013, S1944; Gavanda 2026, S2037). The mechanism makes balance a brake that a small surplus lifts: muscle protein synthesis falls about 19 % at 80 % of needs (S2076), while the energy deposited in new muscle is a few kcal a day near the ceiling (S2070). full_drop's slope and the linear ramp are game choices; the fit is flat on full_drop from 0.3 to 0.7. **E₀:** Murphy & Koehler 2022 (S1942: −500 stops net lean gain in mostly sedentary novices, met here as growth minus the § 5.1 loss); Garthe 2011 (S2029: a −19 % deficit allowed a DXA lean gain, −30 % did not); Moro 2016's time-restricted arm (S2018: fat 10.90 to 9.28 kg with FFM held; the deficit of about −250 kcal/day is an inference from that loss); Roth 2023 (S2028); Longland 2016 (S0064) for the protein deepening |

- **Signal, protein and energy multiply.** Without the signal, protein and a surplus build no muscle. Overfeeding's lean share goes to a new labile-lean field `lx` (§ 5.1), which counts in weight but not in the level or REE (Bray 2012, S0605; whether it is muscle is open, S2016).
- **Protein** is the closed day's grams per kg from the existing `p7` ring.
- **Energy** is the closed day's balance from the existing `eb7` ring.
- **Low volume stalls** where S_g(s) meets S: that is the "harder even to grow" effect.

### 5.1 The energy and protein partition

The growth law above replaces `K.partition.leanGain`, `K.partition.headroom`, `G0`, `LM_CAP_RATIO`, `gEnergy` and the `DEFICIT_HALF*` constants. The partition keeps its role as the only writer of `fm`, `lm` and the new `lx`, once per closed day:

- **Surplus (E ≥ 0).** The day's growth g is paid first at RHO_LEAN. The remainder R splits with the lean weight share x = forbes(M) · clip((p − 0.8)/0.8, 0, 1) · (1 − T) into `lx` (capped at 0.05 · F) and fat. forbes(M) = 10.4/(10.4 + M) (Forbes, S0054, S0055; coefficient open, S1056), and T = min(1, S/10) (S1997). If g exceeds the surplus, fat pays the difference. At balance, `lx` decays toward 0 on a 28-day time constant.
- **Deficit (E < 0).** The lean weight share is forbes(M) · prot, with prot = clip(1 − 0.35 · T − 0.6 · clip((p − 0.8)/0.8, 0, 1), 0.10, 1) (Mettler 2010, PMID 19927027; Pasiakos 2013, PMID 23739654; Weinheimer 2010, S0072; Heymsfield 2014, PMID 24447775; Helms 2014, S0599; Cava 2017, S0609). Fat pays the rest up to Alpert's ceiling (S0056); the overflow is split by prot as the kernel does today. `lx` pays any lean loss first. The growth g still runs (recomposition) and is funded from fat. There is no separate training-age term: the larger lean loss of male physique athletes in contest preparation (S2020, S2021, S2022) reads as a leanness effect, which the Forbes share and Alpert's ceiling already carry.
- **Trained characters and the surplus.** By default the gate at balance falls with status, f_bal(s) = 1 − 0.5 · s, and the surplus that opens it fully shrinks with status, from +10 % of TDEE untrained to +5 % at the cap (§ 5). A slight surplus held over a long time therefore builds more muscle than balance at every trained status, and a surplus beyond E_full(s) adds only fat. Most of the slowing near the cap comes from the headroom term k · (F_c − F), not from energy: at s = 0.9, a year on 20 sets at 2.0 g/kg gains +0.15 kg at maintenance, +0.26 kg at +5 % and +0.27 kg at +10 % (point T; point S gave +0.21 kg at +5 %). No trial in natural lifters near their ceiling compares a surplus with maintenance by a direct muscle measure (S2046, open), and no meta-analysis pools the surplus-against-balance contrast in trained lifters (S2089, open). In intermediates (Helms 2023, S1943, S2033, S2062) and elite non-lifters (Garthe 2013, S1944), the surplus added fat, not detectably more muscle; in men of about 10 years' training, Henselmans 2026's extra energy (S2064, S2065) moved DXA lean +0.76 kg with an interval from −0.19 to 1.69 kg, and muscle thickness by about nothing. Antonio 2015's +1.5 kg (S1993, S2038) and Garthe 2011's +2.1 % (S2029) sit inside DXA's glycogen and water band (Bone 2017, S2039). `NR.StrengthTrainedNeedsSurplus` (0 by default) further scales the gate at balance by (1 − value · s): at 1, a trained character gains little at maintenance and nets lean only through surplus and cut cycles, Angus's stricter premise. No trial compares bulk-cut cycles with maintenance over a year, and the bulk-cut recommendation is practitioner consensus (Iraki 2019, S1946). Under point T, two cycles of 18 weeks at +10 % and 8 weeks at −500 kcal/day net −0.06 kg of muscle at s = 0.9 against +0.15 kg at maintenance, and +1.63 kg at s = 0.6 against +1.71 kg: near the ceiling each cut removes about what its bulk added.
- **Not modelled.** Protein's extra energy cost (Antonio 2014, PMID 24834017: no fat gain on +800 kcal of protein) belongs to the energy model, not to the partition.

### 5.2 The fit (point T)

Point T refits point S's model with the full-growth surplus shrinking with status, E_full(s) = surplus_full · (1 − full_drop · s) · TDEE (the surplus harvest's § 8, S2062–S2089). Its predecessor is point S, which refitted point R with the status-dependent gate and a full-growth surplus of +10 % at every status; S's record is kept as written. Point S's constants are held, and full_drop and the f_bal drop are fitted jointly on a grid inside the report's bounds: full_drop 0.3 to 0.7 (+7 % to +3 % at the cap) and the f_bal drop 0 to 0.7 (f_bal(1) from 1 to 0.3). Angus's anchor stays a hard constraint: k is re-solved so that the average character reaches level 15 in 5 years on 20 sets at full gates, and it comes back unchanged (0.00991), since the anchor runs at full gates. The registry is S's 48 oracles, with Helms 2023's three re-graded, plus 10 new ones (58 in all):
- Helms 2023 re-graded (S2062, S2063): the "+5 %" arm at its reported +489 kcal/d and the "+15 %" arm at +719 kcal/d over maintenance, against no muscle-thickness difference; the maintenance arm at its own reported +169 kcal/d, and both surplus arms' 3.3 kg body-mass gain (S2033), are report only;
- Henselmans 2026 (S2064, S2065) at s = 0.7 (a judgment; the FFMI was not reported), 8 weeks, 16 sets, 2.0 g/kg, at +250 and +485 kcal/d over habitual intake taken as balance: the lean contrast inside the DXA interval −0.19 to 1.69 kg, and the muscle contrast inside the elbow-flexor interval read as a share of an assumed 4.0 cm thickness (−2.25 to +4.75 %);
- Angus's ruling (§ 11) as a direction check: a year at +5 % beats a year at balance at s = 0.9 and s = 0.6;
- a degenerate-read check on full_drop: the share of the +10 % gain that +5 % reaches over 8 weeks must be higher at s = 0.9 than at s = 0.5 by at least 0.05. It reads 0.0013 at full_drop = 0, so point S fails it (score 1.5267 on the new registry against T's 0.5282).

Every new weighted oracle passes. Henselmans reads +0.09 kg of lean and +0.15 % of muscle at both energy contrasts, since both lie above E_full(0.7); the model sits inside the interval, near its lower end, under the trial's +0.76 kg point estimate, part of which is expected glycogen and water (S2039). At s = 0.9 over 8 weeks, balance still gives ΔF = 0.04 % with fat steady, +10 % gives 1.8 × the balance gain, and −500 kcal/day at 3.5 kg of fat gives ΔF = −1.3 kg, as at point S.

**Fitted gate.**
- full_drop = 0.5, the report's value. The fit is flat on it: 0.3 to 0.7 move the score by under 0.0013, and the optimum without Garthe 2011's slow arm sits at the lower bound 0.3 by 0.0007 (bound reported). Only the degenerate check identifies it, and it passes from 0.3 up.
- The f_bal drop stays 0.5. With every oracle, the joint optimum is 0.1, pulled by Garthe 2011's slow arm as at point S. Without that arm the optimum is 0.56, which sits 0.005 below the edge of the § 9 check that a +10 % surplus gives at most twice the balance gain at s = 0.9, so its ×1.05 probe crosses the band. 0.5 is within 0.001 of that optimum and stays inside under ×1.05.
- Every other constant is point S's: β 3.0, S_g0 0.5, S_max1 12, E₀ −650, E0_drop 0.5, a_nov 6.0, f_bal(0) 1.0, surplus_full 0.10, wT 0.35, wP 0.6, the floor 0.10 and p_hi 1.6 g/kg. The profiles over S's grids return them, and the same constants as at S sit at a grid bound (S_g0, S_max1, f_bal(0), p_hi). surplus_full at 0.05 reads a cliff only because the degenerate check's probes, at +5 % and +10 %, both saturate there.
- The ×0.95 and ×1.05 probes move every constant's score by under 0.03, except f_bal(0) at ×1.05, a gate above 1, as at point S.

**What changes in play.** Over a year on 20 sets at 2.0 g/kg, +5 % now gains nearly what +10 % does: +0.26 against +0.27 kg at s = 0.9, and +2.16 against +2.29 kg at s = 0.6 (point S: +0.21 and +2.01). Maintenance, +10 %, the bulk-cut cycles, the novice cases, the per-trait trajectories, detraining and regain are unchanged from point S.

**Named conflicts** (the same set as point S):
- Garthe 2011's slow arm (0.28 kg against 0.8–1.8) cannot be met at a status-dependent gate together with Murphy & Koehler (S1942). Meeting it needs E₀ near −1000 with no status drop, which is the free fit, outside the report's bounds.
- Garthe 2013's fat difference (3.3 kg against 0.8–2.5) belongs to the energy side.
- Longland's high-protein arm (+0.52 kg against 0.6–1.8) misses narrowly.
- Buechel's contest-prep FFM loss (−0.56 kg against −0.9 to −2.6; mixed sex, report only) is under-read: the leanness penalty is mild.
- The growth misses S1958 and Aube 2022 are R's.

The record is in `docs/superpowers/research/2026-10-14-strength-redesign/refit/`: point T's compact fit `compact_T.json`, its oracle, profile and stability read-out `final_T.txt` and `report_body_T.md`, and its scenarios `scenarios_T.txt`; point S's `compact_S.json`, `final_S.txt`, `report_body.md` and `scenarios_S.txt` as recorded; point R's inputs under `fit-R/`.

## 6. Maintenance, detraining and regain

- **Maintenance threshold:** S_m(s) = S_g(s)/3 (Bickel 2011, Spiering 2021). That it holds at every status is a game choice (S2014).
- **Grace:** after 14 consecutive online days with S below S_m, detraining starts. Any day at or above S_m resets the counter.
- **Detraining:** `dF/dt = −λ(s) · (F − F₀) · (1 − S/S_m)`, with λ(s) = ln 2 / (6 weeks · (1 + 2s)): 6 weeks for a novice (Räntilä 2025, S2001: 4.9–9.2 weeks), 18 weeks at the cap. The status term is a game choice resting on S1938 (loss follows the build's time course); no study measures advanced detraining (S2014, S2017). It acts only while F > F₀, and is integrated exactly per closed day (F − F₀ multiplied by exp(−λ·Δt)), so no time scale overshoots F₀.
- **Starvation** takes F through the existing partition deficit arm, independent of training.
- **Remembered peak P:** P = max(P, F) at each day close. P decays toward F with a 2-year half-life (Rahmati 2022 meta and Serrano 2025: human myonuclei are not permanent; the memory is epigenetic, Seaborne 2018).
- **Regain:** while F < P, dF/dt = max(the § 5 growth, λ_r · (P − F) · min(1, G) · f_p · f_e), with λ_r = ln 2 / 6 weeks. The max form reproduces Räntilä's equal second block (0.94 of the first under point S; the sum form overshoots and is not used). Retraining is at least as fast as naive training (Räntilä 2025 equal blocks; Seaborne 2018 1.6×, n = 7). Its use for advanced lifters is a game choice (S2017).

- **Unidentified constants (m7):** the maintenance share m = 1/3 (Bickel S1963; S2014 open), λ_r = 6 weeks (S2002, S2003 between) and the labile-lean cap 0.05·F (Bray's 2.9 kg, about 5 % of FFM) rest on no oracle, and the stability probe reads flat on them. They are game choices.

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
| Fat load | fat-mass index (fat kg / H²), Kelly 2009 (PMID 19753111) cuts through the effective sex (§ 13): male (White subjects' table) overweight above 6, obese above 9 kg/m² (S2056) | Overweight above 6, Obese above 9 |
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
- `body.r`, unless the plan keeps a per-character responsiveness factor (S1975, S1978, S1979), in which case it multiplies k.

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
| `NR.StrengthIncidentalWeight` (new) | double | 0 | 1 | 0.35 | S1951 fractional, S1961, S1962; game choice; C6 |
| `NR.StrengthCapLevel` | double | 12 | 20 | 16.5 | ruling; S1915, m3 |
| `NR.StrengthTraitCapShare` | double | 0 | 1 | 0.5 | Angus |
| `NR.StrengthRate` (a multiplier on the fitted k = 0.00991/wk) | double | 0.25 | 4 | 1.0 | fit R, kept by S; anchor |
| `NR.StrengthThreshold` (S_g0, sets/wk) | double | 0.25 | 1.0 | 0.5 | fit (bound reported); S1951, S1958; guarded, M6 |
| `NR.StrengthThresholdRise` (β) | double | 0 | 4 | 3.0 | fit; S1976, S1977, S1967, S1974 (against S1955, S1975); guarded |
| S_ref | fixed | — | — | 12 | S1951 |
| S_max0 | fixed | — | — | 30 | S1951 (data thin above 25–30) |
| `NR.StrengthTrainedSetCap` (S_max1, new) | double | 8 | 30 | 12 | fit (bound reported); S1953, S1955, S1956 |
| f_p knots | fixed | — | — | 0 @ 0.4, 0.5 @ 0.8, 0.92 @ 1.3, 1.0 @ 1.6 g/kg | S0591, S0592, S1990, S0509 |
| `NR.StrengthProteinFull` (scales the knots) | double | 1.0 | 3.0 | 1.6 | S0591, S0592 |
| `NR.StrengthDeficitZero` (E₀ at s = 0, kcal/day) | double | −2000 | −200 | −650 | fit S (the free fits run to −1000, pulled by Garthe 2011's slow arm alone); S1942, S0064, S2029, S2018 |
| `NR.StrengthDeficitZeroStatusDrop` (new; E₀(s) = E₀ · (1 − value · s)) | double | 0 | 0.9 | 0.5 | Angus's gate (−325 at the cap); flat in the fit; S2018 |
| `NR.StrengthNoviceDeficitDepth` (a_nov, new) | double | 0 | 10 | 6.0 | fit S (the fits run to the grid bound 8, pulled by Garthe 2011's slow arm; without it, 8 gains under 0.004 of score); S0064 |
| `NR.StrengthBalanceGate` (f_bal at s = 0, new) | double | 0.5 | 1.0 | 1.0 | fit S, at its physical bound (the gate never exceeds 1); S1943, S2033 |
| `NR.StrengthBalanceGateStatusDrop` (new; f_bal(s) = f_bal · (1 − value · s)) | double | 0 | 0.7 | 0.5 | Angus's gate; fit S (the best value without Garthe 2011's slow arm); S2018, S2019, S1925, S0606 |
| `NR.StrengthSurplusFull` (new; the surplus, as a share of TDEE, that opens the gate fully at s = 0) | double | 0.02 | 0.30 | 0.10 | Angus's gate; flat in the fit from 0.075 to 0.15 (point T); S1943, S2033, S1944, S2037, S1946 |
| `NR.StrengthSurplusFullStatusDrop` (new; E_full(s) = `NR.StrengthSurplusFull` · (1 − value · s) · TDEE) | double | 0 | 0.9 | 0.5 | the surplus harvest's gate (+5 % at the cap); fit T, flat (0.3–0.7 within 0.0013 of score); S2069, S2068, S1946, S2062, S2064 |
| `NR.StrengthTrainedNeedsSurplus` (new) | double | 0 | 1 | 0 | evidence default; 1 = Angus's premise (item 10) |
| forbes c | fixed | — | — | 10.4 kg | S0054, S0055 (S1056 open) |
| `NR.LeanLossTrainingProtect` (wT, new) | double | 0 | 0.9 | 0.35 | fit; S0072, S1997, S0609 |
| `NR.LeanLossProteinProtect` (wP, new) | double | 0 | 0.9 | 0.6 | fit S (0.75 scores the same); Mettler 2010, Pasiakos 2013, S0599 |
| `NR.LeanLossProtectFloor` (the prot floor, new) | double | 0 | 0.5 | 0.10 | fit S (0.05 scores 0.085 lower, all but 0.004 of it through Garthe 2011's slow arm) |
| `NR.LeanLossProteinFull` (p_hi, g/kg/day of full protein protection, new) | double | 1.2 | 3.0 | 1.6 | fit S, at its grid bound (1.6–2.8; 2.0 costs 0.14 of score); S0599 (2.3–3.1 g/kg FFM), S0064 |
| labile-lean cap / decay | fixed | — | — | 0.05·F / 28 d | S0605 (game choice, S2016) |
| `NR.StrengthMaintainShare` | double | 0.1 | 1.0 | 0.333 | S1963, S0616 (unidentified; S2014 open) |
| `NR.StrengthGraceDays` | integer | 0 | 60 | 14 | S1932, S1940, S1966 |
| `NR.StrengthDetrainHalfLifeWeeks` | double | 2 | 26 | 6 | S2001 |
| `NR.StrengthDetrainStatusSlowing` (new) | double | 0 | 4 | 2.0 | S1938 (game choice; S2014, S2017) |
| `NR.StrengthRegainHalfLifeWeeks` | double | 1 | 26 | 6 | S2002, S2003 (unidentified) |
| `NR.StrengthPeakHalfLifeYears` | double | 0.25 | 20 | 2 | S2004, S2010, S0620, S2007 |
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
- **Peak memory.** Ruling: P decays with a 2-year half-life, not permanently — Rahmati 2022 and Serrano 2025 overturn the first harvest's "might be permanent" (S1935) — cost if wrong: regain after a multi-year break is slower than players expect.
- **No sex-specific rules by default.** Ruling: one mod-wide option, `NR.SexSpecific` (default off); when it is off every character uses the male values everywhere the mod indexes by sex (§ 13) — Angus (2026-10-14): "I dont want gender specific rules, base game treats them equally", then "we can flag this as an option however, just default it to off", then "Lets just use male values for females if its disabled" — cost if wrong: by default a female character's requirements and body bands are the male studies' values (for example the iron requirement and the fat bands).
- **Energy gate.** Ruling: the growth gate's energy factor depends on training status, with f_bal(s) = 1 − 0.5 · s at balance, full at the full-growth surplus (+10 % of TDEE at s = 0, falling with status under the ruling below), and zero at E₀(s) = −650 · (1 − 0.5 · s) times the protein term (point S). The deficit side keeps the Forbes share and Alpert's ceiling with no training-age term, and the stricter premise stays as `NR.StrengthTrainedNeedsSurplus`, default 0 — Angus (2026-10-14): "Adopt the training-status-dependent energy gate … as the default, and refit the constants", the values being "starting values, not fixed", fitted within the report's bounds — cost if wrong: f_bal at the cap is weakly identified (0.3 to 1 all fit), and no trial compares a surplus with maintenance in near-ceiling naturals (S2046), so an advanced character's gain at maintenance may be off by up to a factor of two either way; the headroom term keeps either inside DXA noise.
- **Full-growth surplus.** Ruling: the surplus that opens the growth gate fully shrinks with status, E_full(s) = 0.10 · (1 − 0.5 · s) · TDEE, +10 % untrained and +5 % at the cap, with f_bal(s) = 1 − 0.5 · s, E₀ and the deficit side kept (point T, § 5.2) — Angus (2026-10-14): "a slight surplus over a long time with good training and protein has to build more muscle than zero caloric surplus"; the surplus harvest supports it in direction and mechanism (S2064, S2076, S2069) and finds the size undetectable in 8–12 weeks (S2062, S2063; S2089 open) — cost if wrong: the advanced character's surplus advantage is unmeasured (S2046 open); at s = 0.9 a year at +5 % gains +0.26 kg against +0.15 kg at maintenance, inside DXA noise either way, and the fit is flat on the slope from 0.3 to 0.7.
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
- The first harvest's S1935 ("might be permanent") and the per-meal cap reading of S0065 are qualified or superseded by the newer rows.
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
- Age (PZ has no age stat, though the evidence would support an older-adult maintenance rise, S1963), sleep's effect on synthesis and illness (neither harvested). The per-meal window is none, which is correct (Trommelen, S1988). The energy cost of lean is already in REE (`NR_Kernel_Energy.lua:263` reads `body.lm`; S0011).
