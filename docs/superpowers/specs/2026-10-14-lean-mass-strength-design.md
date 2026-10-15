# Lean-mass Strength and body-composition traits: design

Status: draft for Angus's review, 2026-10-14. Brainstormed in the session that closed Plan 12; each section below was presented and approved in turn, with the rulings in § 11.

Research behind it (copied to `docs/superpowers/research/2026-10-14-strength-redesign/` in the plan's first task, before any science row is minted):
- `vanilla-strength-rate.md`: vanilla Strength XP sources, pacing and days to level 10 on 42.21.
- `science-report.md` and `lean-science-part.tsv`: the first harvest (FFMI scale, multi-year gains, regain, gates).
- `hypertrophy-science-report.md` and `hypertrophy-science-part.tsv`: the 2015-2026 hypertrophy harvest (68 rows, 62 resolved). Its rows were minted as S1951-S2017 and the first harvest's as S1915-S1950 (commit b6b73a49); the spec cites the minted ids.
- `trait-levers.md`: the engine's creation-trait levers, read on the 42.21 jar `4a0e9546ec`.
- `advanced-recomp-report.md` and `advanced-recomp-part.tsv` (ids `S3.n`): recomposition and the surplus in advanced natural lifters, the basis of the status-dependent energy gate (§ 5); `review-science-part.tsv` (ids `S4.n`): the review's harvest, Kelly 2009's FMI bands included. Minted as S2018-S2048 and S2049-S2061.
- `neural-report.md` (ids `S6.n`, minted as S2090-S2141) and `innate-report.md` (ids `S7.n`, minted as S2142-S2172): the general neural factor and the innate force per unit muscle, the basis of the strength level (§ 2).

## 1. Goal

The Strength level becomes a reading of the character's general strength: its lean mass, a trained neural factor and an innate factor fixed at creation (§ 2).

Vanilla Strength XP stops building the level. It becomes a training signal, the analogue of the resistance-exercise stimulus that drives mTORC1 and muscle protein synthesis. On its own it builds nothing: lean mass grows only when the signal, enough protein and enough energy act together.

Progress gets harder in two ways as a character trains:
- the gain still available shrinks roughly exponentially;
- the signal needed to grow, and not merely hold, rises.

Lost lean mass comes back fast. The weight and strength traits describe the body (its composition, and for the strength traits an innate force per unit muscle), are offered at creation for their points, and set the starting body. Nothing changes while a player is offline.

## 2. The scale

### 2.1 The strength level (what the player sees)

```
S = ((F − F_nm) / M5)^b · N0 · T        general strength; S = 1 for the untrained average
L = 5 + 5 · (S − 1) / (R − 1)           the shown level, linear in S all the way, with no stretch above 10
```

| Symbol | Value | Basis |
|---|---|---|
| F | fat-free mass, kg (the body's `lm`) | — |
| F_nm | 27 kg, the non-muscle part of fat-free mass (game choice) | skeletal muscle is about 38.4 % of a man's body mass (S2133), about 25 kg of the average's 52.0 kg of F; non-muscle FFM produces no force |
| M5 | F5 − F_nm = 25.02 kg, with F5 = 52.02 kg the untrained average's F (FFMI 18.0 at 1.70 m) | defined so that S = 1 exactly at the average (a literal 25 kg would put the average at S = 1.00064) |
| b | 0.8 (range 0.67–1.0) | at a fixed height, contractile area grows with muscle volume to the power 0.79, derived from the 4-year trained against untrained comparison (S2121); 0.67 is the cross-size floor (S0085), 1.0 the ceiling with no fascicle growth |
| N0 | the innate force per unit muscle, fixed at creation by the muscle trait: Strong 1.14, Stout 1.07, none 1.0, Feeble 0.915, Weak 0.82 | § 2.3 |
| T | the trained general neural factor, from 1 untrained to T_max = 1.10 | § 2.2; it rises (§ 4) and decays (§ 6) |
| R | the S of the untrained average after Y years of perfect training, Y = `NR.StrengthYearsToLevel10` (default 4): R = 1.5651 | § 2.4 |

- One level is (R − 1)/5 of the average's untrained strength: 11.3 % at the default.
- At or below F_nm, S is 0 and the level is 5 − 5/(R − 1) (−3.85 at the default).
- The Strength perk shows `clamp(floor(L + 1e-9), 0, 10)`. The 1e-9 keeps a start built exactly on a level from flooring one level low through rounding: Stout's start reads 6.999999999999997 and Weak's 0.9999999999999982 in double precision. The XP bar shows the fraction toward the next level.
- Above 10, see § 7. The mod's panel always shows the true level, for example "Strength 12.3".
- **One general signal (Angus, § 11).** Every Strength-XP source counts as one general full-body workout. The model has one training signal and no exercise-specific or task-skill term. The trained lift gains far more than a non-trained test of the same muscles (S2090, S2091; the non-trained effect is about 0.43 of the trained one, S2093, S2094), and practising the test alone moves the 1RM as much as training (S2096): that skill share is left out by design.

### 2.2 The neural factor T
- **Size.** Non-trained isometric tests gain about 0.43 of the trained-task effect, and part of that is muscle (S2093, S2094). The strength left after muscle size is about +9 % after 12 weeks and about +7 to +9 % after 4 years (S2120, S2121, S2122): the general neural factor saturates within months and does not grow over years. T_max = 1.10 (range 1.07–1.12), the same for every training status (game choice). An N_max near 1.10 is an upper bound on the neural part, since part of the residual is intrinsic (S2124).
- **Rise.** Neural gains appear in the first week (S2112, S2113), are large by 3–5 weeks (S0086, S2118) and are complete by about 12 weeks (S2120): τ_up = 3 weeks (game choice). Strength, unlike size, plateaus at about 5 weekly sets (S1952), and practice alone gives the full neural gain (S2096): the signal saturates at W_sat = 5 hard sets a week (game choice, inside the harvest's 4–5).
- **Decay.** General strength and activation hold for 1–3 months of detraining (S1937, S1939, S2138) and are partly lost by 3–6 months (S2138, S2139): a 21-day grace, then τ_down = 12 weeks (game choice; range 8–16). No study separates the neural decay of a long-term trainee from muscle loss (S2140, open).
- **What it gives.** At full signal T is 1.0283 after 1 week, 1.0736 after 4 and 1.0964 after 10; after 6 months off it is back to 1.0147.

### 2.3 The innate factor N0
- **The spread.** Force per unit muscle varies between untrained adults with a CV of 11–16 % in one muscle group (S2142, S2143, S0082, S2121), and total untrained strength with a CV of about 17 % (S2145). The whole-body size-independent SD is taken as 10 % (game choice; S2170 open: every measured spread is one muscle group).
- **Innate and lasting.** The size-independent part is heritable (S2162, S2166, S2158) and survives training: trained and untrained men keep the same spread of specific tension (S2121), torque per volume is the same in athletes and controls (S2146), and the ranking holds through 10 weeks of training (S2169). It is therefore a creation-time property, fully persistent (game choice; S2172 open for an individual over years).
- **Per trait.** A trait's N0 is the expected size-independent share of its strength gap, N0 = S_trait^0.35 with 0.35 = 0.10²/0.17², capped at |ln N0| ≤ 0.2 (two size-independent SDs), which binds only Weak (0.82; uncapped 0.749). The values were derived in the innate harvest at R ≈ 1.566 and are fixed numbers: they do not move with Y. The same N0 applies to both sexes, since force per unit size does not differ between them (S0082, S2144).
- **What it is.** Specific tension plus activation, mostly intrinsic rather than neural (S2143, S2150). It is not fibre type, which does not carry maximal force per unit muscle between people (S2142, S2154).

### 2.4 R, the biology level and what the scale gives
- **R.** R is the S of the untrained average (N0 = 1) after Y years of perfect training, with T = T_max. Perfect training is 20 hard sets a week, 2.0 g/kg/day of protein and a surplus of +10 % of TDEE, so every gate of § 5 is 1. R is read off the growth law's full-gate step from the average's creation body. At Y = 4, F = 65.88 kg and R = 1.5651. Y = 1, 2, 3, 6 and 10 give 1.3675, 1.4814, 1.5350, 1.5970 and 1.6233.
- **R's inputs.** R reads the growth law's fitted constants and the default T_max, never the server's other options. `NR.StrengthRate` and the other growth options therefore still change how fast a character reaches level 10. R is recomputed only when `NR.StrengthYearsToLevel10` changes.
- **Calibration.** A 4-year trainee is +60 % in knee-extensor torque and about +42 % at matched height (S2120, S2121); R = 1.565 sits between the two. No study measures a multi-task, height-matched ratio (S2141, open).
- **The biology level.** The growth law (§§ 5–6), its fit and its anchors keep their own linear coordinate in FFMI:

```
FFMI     = F / H²                       H = 1.70 m, fixed, sex-neutral; one shared constant, which K.acute.HEIGHT_M (1.75 today) also reads, so every BMI in the mod uses 1.70
bioLevel = 5 + (FFMI − 18.0) / 0.5      one bio level ≈ 1.445 kg of fat-free mass F
```

  - The natural cap (`NR.StrengthCapLevel`, 16.5), the fit's anchor (bio level 15 at 5 years), the levels in §§ 5–6 and § 5.2's record are bio levels. A player never sees one.
  - The kernel names the two scales apart: `K.strength.bioLevel` and `fOfBio` for the growth law, `K.strength.level` and `fOfLevel` for the shown level.
  - At creation the untrained average is at bio level 5 (FFMI 18.0, F = 52.02 kg). The untrained natural cap is bio level 16.5 (FFMI 23.75), under Kouri's natural limit of 25.0 normalised to 1.80 m, which is 24.37 raw at 1.70 m (S1915), by Kouri's normalisation FFMI_norm = FFMI + 6.3 · (1.8 − h) (the coefficient 6.3 is Kouri 1995's, S1915).
  - Every trait's natural cap is clamped at that limit: F = 24.37 · 1.70² = 70.43 kg (`ffmiNatural` 25.0 normalised, fixed; ruling 13-47). Stout's and Strong's caps, which would sit 2.32 and 4.42 kg above the untrained cap (70.96 kg and 73.06 kg, FFMI 24.55 and 25.28 raw), are clamped to it; the other three are under it. S1918 (26.4 % of collegiate football players exceed 25 normalised) is why the limit is a clamp and not a wall, but the mod keeps a character inside Kouri's natural limit.
- **What the scale gives.** Shown levels under perfect training from creation, with T rising from 1 (the growth law's exact daily step, point T; the cap is the level of F_c at T_max):

| Trait | N0 | Start F, kg | Start | 4 wk | 10 wk | 6 mo | 1 yr | 2 yr | 4 yr | 10 yr | Cap |
|---|---|---|---|---|---|---|---|---|---|---|---|
| none | 1.0 | 52.02 | 5.00 | 5.91 | 6.49 | 7.33 | 8.25 | 9.26 | 10.00 | 10.51 | 10.78 |
| Stout | 1.07 | 56.66 | 7.00 | 8.01 | 8.57 | 9.28 | 10.06 | 10.92 | 11.59 | 12.08 | 12.34 |
| Strong | 1.14 | 60.86 | 9.00 | 10.09 | 10.59 | 11.10 | 11.64 | 12.25 | 12.76 | 13.17 | 13.40 |
| Feeble | 0.915 | 47.30 | 3.00 | 3.79 | 4.37 | 5.29 | 6.30 | 7.39 | 8.17 | 8.67 | 8.93 |
| Weak | 0.82 | 42.12 | 1.00 | 1.85 | 2.42 | 3.37 | 4.41 | 5.51 | 6.28 | 6.76 | 6.99 |

  - The early levels are mostly neural: of the average's +0.91 at 4 weeks, T carries about 70 % in log terms (T = 1.0736 of S = 1.103).
  - Strong passes 10 after 25 days, through T, and Stout after 348 days (23 and 329 before ruling 13-47's clamp). The average needs the full 4 years (day 1461).
  - Feeble and Weak never reach 10.

## 3. Creation

### 3.1 What is offered
The creation screen offers 8 body traits: Weak, Feeble, Stout and Strong (muscle) at their vanilla costs, and Overweight and Obese (fat) and Underweight and Very Underweight (thin) at costs the mod sets, because vanilla gives those four `Cost = 0` and the creation lists show only a positive or a negative cost (trait-levers § 1.3). Overweight and Underweight carry `Cost = -6` and Obese and Very Underweight `Cost = -10`, so they give 6 and 10 points (Angus, 2026-10-14; § 11). The sign is vanilla's: a negative cost gives points, as Feeble's `Cost = -6` and Weak's `Cost = -10` do (trait-levers § 1.3), so the four mirror Feeble and Weak. Emaciated is reached only in play.

On 42.21, the five weight-band traits are hidden profession traits (`IsProfessionTrait = true`) that the creation lists filter out (trait-levers § 1).

The mod restates the full definition block of each offered trait in a shared script, named `base:<id>` in `module Base`, because a same-name block replaces the whole definition and resets every omitted key (trait-levers § 2). Each restated block:
- sets `IsProfessionTrait = false`;
- keep vanilla's Strength `XPBoosts` on the four muscle blocks (so the creation climb lands on the pick's band, Task 17 fix 1) and drop the Fitness `XPBoosts` on the weight blocks;
- keeps vanilla's cost (the four weight traits take the costs above) and exclusions, and adds the missing pairs: Obese and Overweight both ways, every pair inside a family (the four muscle traits, the four fat and thin traits), and Underweight and Very Underweight against Weak and Feeble, both ways (§ 3.2).

Weight Gain and Weight Loss are restated without their `GrantedTraits`. They keep their place as intake-rate traits in the body model.

The descriptions are rewritten through the `UI_trait_*` translation keys to say what each trait now does.

### 3.2 What a pick does
A server `OnNewGame(player)` handler, guarded by `isServer()`, runs after vanilla's `applyTraits` and before the save (trait-levers §§ 3–4). It:
1. **Validates the picks.** The point total must be legal and no two picks may exclude each other; any illegal pick is stripped, latest first, and logged. The server checks neither of these itself.
2. **Builds the body:**

| Pick | N0 | Lean F at the start (shown level at T = 1) | Set point F0 | Natural cap Fc | Peak P | Fat |
|---|---|---|---|---|---|---|
| none | 1.0 | 52.02 kg (level 5; FFMI 18.0) | the start | 68.64 kg (bio 16.5) | the start | FMI 4.5 kg/m² (13.0 kg at 1.70 m; the middle of Kelly 2009's male normal 3–6): 65.0 kg, BMI 22.5, 20 % fat |
| Feeble | 0.915 | 47.30 kg, −4.72 (level 3; FFMI 16.37) | 49.66 kg (−2.36) | 66.28 kg | F0 | as picked |
| Weak | 0.82 | 42.12 kg, −9.90 (level 1, the floor; FFMI 14.57) | 47.07 kg (−4.95) | 63.69 kg | F0 | as picked |
| Stout | 1.07 | 56.66 kg, +4.64 (level 7; FFMI 19.61) | 54.34 kg (+2.32) | 70.43 kg (clamped; 70.96 unclamped) | the start | as picked |
| Strong | 1.14 | 60.86 kg, +8.84 (level 9; FFMI 21.06) | 56.44 kg (+4.42) | 70.43 kg (clamped; 73.06 unclamped) | the start | as picked |
| Overweight | — | unchanged | unchanged | unchanged | — | FMI 7.5 at the average lean (21.7 kg): 73.7 kg, BMI 25.5, 29.4 % fat |
| Obese | — | unchanged | unchanged | unchanged | — | FMI 10.5 at the average lean (30.3 kg; the middle of Kelly's male obese class I, 9–12): 82.4 kg, BMI 28.5, 36.8 % fat |
| Underweight | — | lowered to reach BMI 18.0 at FMI 1.5 (47.69 kg of F; 4.3 kg of fat, 8 % fat; Gallagher's male fat at BMI 18 is about 7 %, S1905 equation), never raised | unchanged | unchanged | unchanged | FMI 1.5 |
| Very Underweight | — | lowered to reach BMI 16.5 at FMI 1.0 (44.80 kg of F; 2.9 kg of fat, 6 % fat), above the 4 % starvation floor, never raised | unchanged | unchanged | unchanged | FMI 1.0 |

   - **The start (Angus).** Each muscle trait keeps its vanilla start level: Weak 1, Feeble 3, none 5, Stout 7, Strong 9. The start F solves L(F, N0, T = 1) = the start level (§ 2.1). It is reached through the trait's N0 and its lean: for Strong, N0 carries about a third of the log strength gap, and the lean +8.84 kg rather than the +14.9 kg a lean-only start would need. A changed Y moves R and with it the starts.
   - **A profession's Strength boost (Angus, 2026-10-15).** A profession's Strength `XPBoosts` (vanilla's Farmer, Fire Officer, Fitness Instructor and Lumberjack carry `Strength=1`) raises the start like a small trait: the start level is the pick's plus the boost, clamped to [0, 10] so the native perk is reachable, and F solves L(F, N0, T = 1) = that level at the pick's own N0; the boost adds no innate factor. F0, Fc and P then follow F by the rules below, as for a trait, and a thin pick's cap applies after the boost. A no-pick Farmer starts at level 6 (55.60 kg), a Stout one at 8 (60.12 kg), and a Strong Lumberjack at 10 (64.18 kg); a boost of +2 on Strong also lands at 10. First sight reads the boost off the profession the same way and infers the muscle pick from the native level as creation does, and an unreadable boost reads 0 (§ 11).
   - **The set point and the cap (Angus).** Half of the start's lean difference from the average is permanent, and the cap moves by the same half: F0 = F5 + 0.5 · (F − F5) and Fc = Fc5 + 0.5 · (F − F5), where F5 is the average's F, Fc5 the untrained cap (bio 16.5) and 0.5 is `NR.StrengthTraitShare`. Then every Fc is clamped at the natural FFMI limit: Fc = min(Fc5 + 0.5 · (F − F5), ffmiNaturalRaw · H²) with ffmiNaturalRaw = ffmiNatural − 6.3 · (1.8 − H) = 24.37 and `ffmiNatural` = 25.0 normalised (Kouri's limit, S1915; fixed, not an option). The limit is 70.43 kg, so Strong's and Stout's caps are clamped (shown cap levels 13.40 and 12.34, down from 14.23 and 12.50) and none, Feeble and Weak (10.78, 8.93, 6.99) are unchanged.
   - **The other half.** Stout's and Strong's other half is trained muscle above F0, which detrains toward F0 without training (§ 6): an idle Strong character settles at level 7.64, in Stout's band, and an idle Stout at 6.32. Feeble's and Weak's other half is deconditioning below F0 and below P, so it comes back on the regain path (§ 6). Weak's permanent base, its F0, reads level 2.23, in Feeble's band.
   - **The peak** starts at max(F, F0).
   - **Year 1.** Weak gains the most absolute lean in year 1 (+10.99 kg against the average's +7.82 and Strong's +5.34 on perfect training), because its headroom to the cap is the largest. Relative gains are similar across people (S0589).
   - **The Weak floor (Angus).** Weak's start is level 1, at −9.90 kg (FFMI 14.57) with N0 0.82, the innate harvest's cap. At 1.70 m Weak's level-1 start lies about 3.5 total SDs of untrained strength below the mean (ln 0.547 / 0.17), so most of its gap has to be thin muscle (innate report § 6).
   - **The anti-stacking rule (Angus).** Underweight and Very Underweight exclude Weak and Feeble. At Weak's start F neither thin target lowers anything (42.12 kg lies below both), and Underweight lowers nothing at Feeble's (47.30 kg lies below its 47.69 kg): those picks would give points with no downside. Feeble with Very Underweight would cost 0.68 levels; it is excluded with the other three, since thin already means lost lean and the rule then reads one family against the other. A creation test (§ 12.1) enumerates every legal pick set and asserts that each point-giving body trait makes the created body measurably worse.
   - **Thin traits are depletion.** The lean they remove is below the remembered peak, so it comes back on the fast regain path (§ 6) and leaves F0 and the cap alone. Their starts are level 3.75 (Underweight) and 2.89 (Very Underweight) with no muscle pick, 4.28 and 3.36 with Stout, and 4.81 and 3.83 with Strong.
   - **Weight Gain and Weight Loss** give points for an intake rate in play and change no created body; the anti-stacking test covers the 8 body traits.
   - **Fat bands** are read through the character's effective sex (§ 8.1, § 13): the male cuts unless `NR.SexSpecific` is on.
   - **The fat start scales with lean (Angus, 2026-10-15; § 11).** A fat or no weight pick's fat is fm = FMI[pick] · H² · F / Favg, where F is the start lean (after a profession's boost) and Favg = fOfBio(5) = 52.02 kg, the untrained average's. The table's kg are the average's; every start sits at its band middle's body-fat share whatever the muscle pick: 20 % for none, 29.4 % for Overweight, 36.8 % for Obese (male table). None + Obese is 30.3 kg of fat and 82.4 kg; Strong + Obese 35.5 kg and 96.4 kg; Weak + Obese 24.6 kg and 66.7 kg; a Strong character with no weight pick starts at 15.2 kg of fat, 20 %, not at a fixed 13.0 kg. The female table (7.0, 11.0, 15.0) scales the same way. A thin pick's fat is its FMI times H², unscaled: thin is depletion, and its fat is the very-lean floor.
   - **Weight** = F + fat mass. This replaces `K.body.split`'s band-anchored split of vanilla's starting weight.
3. **Writes the weight, the Strength level (§ 7) and the body traits (§ 8).** Vanilla's creation band swap on `LevelPerk` can leave a trait the player never picked, for example Out of Shape after Weight Gain (trait-levers § 3). The handler's trait write is final.

## 4. The training signal

- **Capture.** A server `AddXP` listener adds every positive Strength gain into today's slot of a 7-slot daily ring, after dividing out vanilla's multipliers: the protein factor the engine applied (×1.5 when 50 < proteins < 300, ×0.7 below −300; #2112, measured #2900) and the sandbox XP multiplier (`Global` under `GlobalToggle`, else the per-perk Strength value), so protein enters only through f_p and the XP sandbox does not scale biology.
- **Source weights.** A grant made while an `ISFitnessAction` runs counts 1; any other grant (melee hits, carrying, trees, barricades) counts `NR.StrengthIncidentalWeight` (default 0.35). Basis: hypertrophy rises with proximity to failure (S1961, S1962), indirect work counts fractionally (S1951). Without it, a survivor's incidental XP (about 500 a game day on the 90-minute day, vanilla-strength-rate § 4) reads about 10 sets a week and drives a never-trained character to level 14.4 in 10 years (sim, S = 10).
- **Conversion.** Weekly hard sets S = the ring's sum ÷ `NR.StrengthXPPerSet`. The default for `NR.StrengthXPPerSet` is the Strength XP of one vanilla Fitness set taken to exhaustion, measured by a live calibration run before the constant ships (§ 10). The calibration run x423-20261015-040740 measured 360 (one push-up set to exhaustion, 60 reps × 6, n = 1, Fitness 5, Strength 5), which is the shipped default; the calibration reads push-ups with the protein factor divided out.
- **The neural factor T** reads the same weekly S (§ 2.2). At each closed day, g = min(1, S/W_sat) and T rises toward T_max, integrated exactly over the day: T ← T_max − (T_max − T) · exp(−g · ts / (7 · τ_up)), with τ_up in weeks and ts the biology clock (§ 10). Once its grace has passed (§ 6), a day decays T instead. One signal drives both F and T, with no exercise specificity (Angus, § 11).
- **The XP never moves the level.** The next level write (§ 7) restores the level from F, N0 and T.
- **Replaced:** the resistance side of `NR_Kernel_Training` (the set-equivalents per rep, hit and tree). The aerobic side stays.

## 5. Growth

The levels in §§ 5–6 and in § 5.2's record are bio levels (§ 2.4), the growth law's own coordinate, not the shown level.

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
| k | the five-year shape | fitted (with β in place) so that an untrained average character on 20 sets a week with full gates reaches bio level 15 at 5 years (Angus: "Five year shape, tunable in settings"). Fitted: k = 0.00991 per week (point R, kept by point S since the anchor runs at full gates; 0.00874 under the draft's β 2.5, S_g0 1, flat set cap). The average character then reaches bio level 10 in 0.89 years (the shown level 10 takes Y years, § 2.4) and gains 7.8, 3.5, 1.7, 0.9 and 0.6 kg in years 1-5, against McDonald scaled ×0.75 (S1929) of 6.8–8.5, 3.4–4.1, 1.7–2.0 and 0.7–1.0 |
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

Point T refits point S's model with the full-growth surplus shrinking with status, E_full(s) = surplus_full · (1 − full_drop · s) · TDEE (the surplus harvest's § 8, S2062–S2089). Its predecessor is point S, which refitted point R with the status-dependent gate and a full-growth surplus of +10 % at every status; S's record is kept as written. Point S's constants are held, and full_drop and the f_bal drop are fitted jointly on a grid inside the report's bounds: full_drop 0.3 to 0.7 (+7 % to +3 % at the cap) and the f_bal drop 0 to 0.7 (f_bal(1) from 1 to 0.3). Angus's anchor stays a hard constraint: k is re-solved so that the average character reaches bio level 15 in 5 years on 20 sets at full gates, and it comes back unchanged (0.00991), since the anchor runs at full gates. The registry is S's 48 oracles, with Helms 2023's three re-graded, plus 10 new ones (58 in all):
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
- **The neural factor's decay.**
  - A day with S below m · W_sat advances a counter `Tgrace`, and any other day resets it. That threshold is the maintenance share of the saturating signal, 1.67 sets a week at the defaults, the same at every status.
  - After 21 consecutive such days (divided by ts), each further such day decays T toward 1, integrated exactly over the day: T ← 1 + (T − 1) · exp(−ts / (7 · τ_down)), with τ_down = 12 weeks. A decaying day does not raise T.
  - While the counter is inside its grace, T still rises at g (§ 4). Retraining rises at τ_up from wherever T stands (S0618, S2002). T is the same at every status.
  - A 2-week break moves T not at all (S1931, S1939). Six months off after full training take it from 1.10 to about 1.015.

- **Unidentified constants (m7):** the maintenance share m = 1/3 (Bickel S1963; S2014 open), λ_r = 6 weeks (S2002, S2003 between) and the labile-lean cap 0.05·F (Bray's 2.9 kg, about 5 % of FFM) rest on no oracle, and the stability probe reads flat on them. They are game choices.

## 7. Writing the level, and BeyondTen

At day close, and once at creation, the server computes the shown level L = level(F, N0, T) (§ 2.1), whose perk level is floor(L + 1e-9):
- **floor(L) ≤ 9:** if the native Strength level differs, the server sets it and pins native XP at that level's starting total plus the fraction toward the next level (the bar); the `AddXP` listener re-pins at once when a grant crosses a level total (event-driven, no tick work).
- **floor(L) ≥ 10:** native level 10, with native XP parked at the level-9 total (337 500), so the `AddXP` event keeps firing with the full amount (vanilla returns before the event once XP reaches the level-10 total, #2109); the vanilla ten-minute level check is guarded so the parked XP never loses the level, as BeyondTen does (#2850, #2856). A Task 0 check confirms grants at level 10 reach the listener at full size.
  - Vanilla's `XpUpdate` band swap then moves Weak, Feeble, Stout and Strong. A Task 0 live check confirms the swap fires on the mod's write.
  - The short-term carry factor (dehydration, sleep, caffeine) stays as it is.
- **floor(L) > 10 with BeyondTen loaded** (`BT.API_VERSION == 1`):
  - native Strength stays at 10;
  - the server writes BeyondTen's stored XP for L through `BT.SetStoredXP(player, Perks.Strength, value)`, server-authoritative, with the value from BeyondTen's own `GetTotalMasteryCost`;
  - native XP is never written while the native level is 10, because BeyondTen parks its reservoir there.
- **floor(L) > 10 without BeyondTen:** the perk shows 10; the extra F still counts in weight and in the panel.
- **How far above 10.** Under perfect training, the untrained average passes 10 only after Y years and approaches 10.78, its cap with T_max. Stout's cap is 12.34 and Strong's 13.40 (ruling 13-47 clamps both at the natural FFMI limit; they were 12.50 and 14.23 before it), which Strong approaches only past 10 years (13.17 at 10 years). BeyondTen therefore holds at most about 3.4 levels, only for Stout and Strong, and only after years of training; ruling 13-42's clamp at 15 is not reached at the defaults.

## 8. Body traits in play

Three axes are read at day close, from the record:

| Axis | Measure | Trait switches (vanilla traits, for the engine-only penalties) |
|---|---|---|
| Fat load | lean-scaled fat index, fat kg / (H² · lm / Favg), against Kelly 2009 (PMID 19753111) cuts through the effective sex (§ 13): male (White subjects' table) overweight above 6, obese above 9 kg/m² (S2056); each cut in kg is cut · H² · lm / Favg, so the male cuts are 25 % and 33.3 % body fat for every lean (Angus, 2026-10-15; § 11) | Overweight above 6, Obese above 9 |
| Muscle | the shown strength level (§ 2.1) | Weak, Feeble, Stout, Strong through vanilla's own band swap (§ 7) |
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
- **Lean scaling (Angus, 2026-10-15):** the fat cuts scale with the body's lean, cutFat(k) = FAT_CUTS[sex][k] · H² · lm / Favg, with lm the body's lean (not lx) and Favg = 52.02 kg the untrained average's; a muscular body carries more fat before a fat trait applies. A Strong start (60.86 kg of lean) crosses Overweight's cut at 20.29 kg of fat and switches at 21.30 kg, against 17.34 and 18.21 kg at the average lean. The thinness axis still reads the BMI from lm + fm (ruling 13-15).
- **Damping:** a switch needs a margin of 0.5 BMI or 0.3 FMI past its cut, the FMI margin scaled by lm / Favg like the cut, and switches are checked once a day.
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
| N0 | the innate force per unit muscle, fixed at creation from the muscle pick (§ 2.3) |
| T | the trained neural factor, from 1 to T_max (§§ 2.2, 4, 6) |
| Tgrace | days below the neural maintenance signal (§ 6) |

`lm` is F.

### 9.2 Removed (the mod is unreleased: no migration)
- `NR_Kernel_Strength`'s old neural term (`n`, its targets and history; the T of § 2.2 replaces it), memory floor, cumulative deficit, disuse term, fSlow ceiling and the rise-hold and hourly-fall write policy;
- the resistance side of `NR_Kernel_Training`; the deficit protection's dose input `dStr` becomes T = min(1, S/10) from the § 4 signal;
- `K.partition.leanGain`, `headroom`, `gEnergy`, `G0`, `LM_CAP_RATIO`, `P_LO`, `P_HI`, `SURPLUS_RAMP` and `DEFICIT_HALF*` (§ 5.1 replaces them); `gAlc` stays, as a factor on g (§ 5);
- `K.body.split` and its build offsets; the heal and store fallbacks that call it (`NR_Kernel_Heal`, `NR_Kernel_Store`) build the § 3.2 no-trait body instead;
- `lm0`, where F0 replaces it; `lm0dis` stays (the disuse arm's own anchor);
- `body.r`, unless the plan keeps a per-character responsiveness factor (S1975, S1978, S1979), in which case it multiplies k.

### 9.3 Offline time (Angus: "I do not expect character stats to change when they are offline")
- The record's day calendar (`dayIndex`, the day stamps) advances only on game days the player is online.
- A reconnect after any gap resumes the calendar where it stopped. The day-close catch-up (`MAX_CLOSES`) closes no missed days.
- Every daily and weekly ring is audited (`p7`, `eb7`, `mass7`, `bandWeek`, `sig7` and the training rings), and so are the grace counters (`grace`, `Tgrace`), T's rise and decay, and P's decay: each counts only online days.

### 9.4 Cost (Rule 6)
- The `AddXP` listener is an event-driven add, with no per-tick work.
- Growth, traits and the level write run at day close, once per player per online game day. The plan benches the day close before and after.

## 10. Sandbox options

The options follow the existing `NR.<Name>` pattern in `42.21/media/sandbox-options.txt`. Every default is a cited value or a labelled game choice; "Fixed" means a kernel constant, not an option.

| Name | Type | Min | Max | Default | Basis |
|---|---|---|---|---|---|
| H (height) | fixed | — | — | 1.70 m, shared with K.acute | ruling; M2 |
| `NR.StrengthTimeScale` (the biology clock: 1.0 means one game day is one biological day): multiplies the per-day growth, detraining, regain and peak-decay rates and divides the grace days; S stays the ring's sets per 7 game days, unscaled | double | 0.25 | 30 | 1.0 | ruling; OnsetSpeed precedent; M5, M12 |
| `NR.StrengthXPPerSet` | double | 50 | 2000 | 360 (measured, x423) | vanilla-strength-rate § 4; calibration run |
| `NR.StrengthIncidentalWeight` (new) | double | 0 | 1 | 0.35 | S1951 fractional, S1961, S1962; game choice; C6 |
| `NR.StrengthCapLevel` (the untrained natural cap, in bio levels, § 2.4) | double | 12 | 20 | 16.5 | ruling; S1915, m3 |
| `NR.StrengthTraitShare` (the share of a muscle trait's start lean difference applied to the set point and the cap, § 3.2) | double | 0 | 1 | 0.5 | Angus |
| `NR.StrengthYearsToLevel10` (new; Y, the years of perfect training that bring the untrained average to level 10; R is recomputed when it changes, § 2.4) | double | 1 | 10 | 4 | Angus; S2120, S2121 (S2141 open) |
| `NR.StrengthNeuralMax` (T_max, new) | double | 1.0 | 1.15 | 1.10 | S2120, S2121, S2122 (the harvest's range 1.07–1.12); game choice |
| `NR.StrengthNeuralRiseWeeks` (τ_up, new) | double | 1 | 8 | 3 | S2112, S2113, S0086, S2118; game choice |
| `NR.StrengthNeuralDecayWeeks` (τ_down, new) | double | 4 | 26 | 12 | S1937, S2138, S2139 (the harvest's range 8–16); game choice; S2140 open |
| `NR.StrengthNeuralGraceDays` (new) | integer | 0 | 60 | 21 | S1939, S1931, S2138; game choice |
| `NR.StrengthNeuralSaturationSets` (W_sat, sets/wk, new) | double | 1 | 12 | 5 | S1952, S2096; game choice |
| b | fixed | — | — | 0.8 | S2121 (derived 0.79), S0085 |
| F_nm and M5 | fixed | — | — | 27 kg; F5 − F_nm = 25.02 kg | S2133; game choice |
| N0 per trait | fixed | — | — | Strong 1.14, Stout 1.07, none 1.0, Feeble 0.915, Weak 0.82 | S2142, S2143, S2145, S2162, S2166; game choice (S2170 open) |
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

At load the options are checked: if S_g0 · e^(0.87β) ≥ S_max(0.87), bio level 15 is unreachable at any rate; the server logs the combination and falls back to the defaults for β, S_g0 and S_max1.

Pointless or dangerous options, kept out:
- A raw `NR.StrengthRate` = k: its meaning shifts with β, S_g0 and S_max1, so the option is a multiplier on the fitted k.
- A raw R: R is derived from `NR.StrengthYearsToLevel10`, so level 10 keeps its meaning.
- `NR.StrengthThreshold` above about 1.0 at β 3: the anchor becomes unreachable (the guard above).
- `NR.StrengthTimeScale` above about 7 with a daily Euler step: it overshoots, so the detraining and decay steps are integrated exactly.
- `NR.StrengthMaintainShare` 0: detraining never runs, which may be intended; the option's tooltip says so.

## 11. Rulings made in the brainstorm

- **Height.** Ruling: the growth law's bio level is FFMI at a fixed 1.70 m, sex-neutral — Angus's choice ("assume average height always and make it gender-indifferent for now") — cost if wrong: none planned; a sex term is excluded by the ruling below.
- **Stimulus.** Ruling: vanilla Strength XP is the training signal and replaces the mod's own resistance set-equivalents — Angus chose "Vanilla Strength XP", and the calibration ties it to one hard set — cost if wrong: incidental carrying may count as more sets than real training does, and a per-source discount is added.
- **Time.** Ruling: one game day is one biological day by default, with a sandbox multiplier — Angus's choice — cost if wrong: most characters never reach high levels on default servers; operators compress it.
- **Threshold.** Ruling: the growth threshold rises with status, β = 3.0 (fitted, point R), sandbox-tunable — Angus's premise, with mixed evidence — cost if wrong: advanced characters stall early; β = 0 restores headroom-only.
- **Curve.** Ruling: the growth law's five-year shape (bio level 15 at 5 years), with the cap at bio 16.5, chosen over the literature's first year — Angus: "Five year shape, tunable in settings" — cost if wrong: none measured; the fitted curve's year 1 (7.8 kg) sits inside the literature calibration (6.8–8.5 kg).
- **Traits.** Ruling: the vanilla strength-trait order is kept (Weak is the stronger penalty) — Angus — cost if wrong: none at the engine level.
- **Creation.** Ruling: 8 traits offered, Emaciated excluded, and the picks are re-validated on the server — Angus — cost if wrong: validation code that a live check must prove sees the whole pick list.
- **Peak memory.** Ruling: P decays with a 2-year half-life, not permanently — Rahmati 2022 and Serrano 2025 overturn the first harvest's "might be permanent" (S1935) — cost if wrong: regain after a multi-year break is slower than players expect.
- **No sex-specific rules by default.** Ruling: one mod-wide option, `NR.SexSpecific` (default off); when it is off every character uses the male values everywhere the mod indexes by sex (§ 13) — Angus (2026-10-14): "I dont want gender specific rules, base game treats them equally", then "we can flag this as an option however, just default it to off", then "Lets just use male values for females if its disabled" — cost if wrong: by default a female character's requirements and body bands are the male studies' values (for example the iron requirement and the fat bands).
- **Energy gate.** Ruling: the growth gate's energy factor depends on training status, with f_bal(s) = 1 − 0.5 · s at balance, full at the full-growth surplus (+10 % of TDEE at s = 0, falling with status under the ruling below), and zero at E₀(s) = −650 · (1 − 0.5 · s) times the protein term (point S). The deficit side keeps the Forbes share and Alpert's ceiling with no training-age term, and the stricter premise stays as `NR.StrengthTrainedNeedsSurplus`, default 0 — Angus (2026-10-14): "Adopt the training-status-dependent energy gate … as the default, and refit the constants", the values being "starting values, not fixed", fitted within the report's bounds — cost if wrong: f_bal at the cap is weakly identified (0.3 to 1 all fit), and no trial compares a surplus with maintenance in near-ceiling naturals (S2046), so an advanced character's gain at maintenance may be off by up to a factor of two either way; the headroom term keeps either inside DXA noise.
- **Full-growth surplus.** Ruling: the surplus that opens the growth gate fully shrinks with status, E_full(s) = 0.10 · (1 − 0.5 · s) · TDEE, +10 % untrained and +5 % at the cap, with f_bal(s) = 1 − 0.5 · s, E₀ and the deficit side kept (point T, § 5.2) — Angus (2026-10-14): "a slight surplus over a long time with good training and protein has to build more muscle than zero caloric surplus"; the surplus harvest supports it in direction and mechanism (S2064, S2076, S2069) and finds the size undetectable in 8–12 weeks (S2062, S2063; S2089 open) — cost if wrong: the advanced character's surplus advantage is unmeasured (S2046 open); at s = 0.9 a year at +5 % gains +0.26 kg against +0.15 kg at maintenance, inside DXA noise either way, and the fit is flat on the slope from 0.3 to 0.7.
- **Creation costs.** Ruling: Overweight and Underweight take `Cost = -6`, and Obese and Very Underweight `Cost = -10`, in vanilla's sign, where a negative cost gives points as Weak's `-10` does — Angus (2026-10-14): "Overweight and Underweight give 6 points; Obese and Very Underweight give 10" — cost if wrong: a fat or thin start becomes a cheap point source if its play penalties are mild; the costs are script values that a later plan can retune.
- **Strength level.** Ruling: the shown level is linear in general strength all the way, S = ((F − F_nm)/M5)^b · N0 · T and L = 5 + 5 · (S − 1)/(R − 1), with no stretch above 10, and level 10 is the strength of the untrained average after `NR.StrengthYearsToLevel10` years (default 4) of perfect training; the growth law keeps its bio level as its own coordinate — Angus (2026-10-14): the level is linear in strength all the way, with no stretch above 10, and level 10 is the general strength of 4 years of perfect training, adjustable — cost if wrong: R rests on single-joint 4-year data (S2141 open); b at 0.67 or 1.0 moves R from 1.565 to 1.478 or 1.709.
- **Neural factor.** Ruling: strength combines muscle, a trained neural factor T and an innate factor N0; T is one general factor from 1 to 1.10, rising with τ_up = 3 weeks and decaying with τ_down = 12 weeks after a 21-day grace, and every Strength-XP source counts as one general full-body workout — Angus (2026-10-14): "a neural skill factor is appropriate but lets make sure that matches studies on what that actually gives us, as the strength as far as a stat needs to be generalizable strength and not specific to a movement which the neural signalling is strongest for", and every Strength-XP source is one general full-body workout with no exercise specificity — cost if wrong: the neural decay of a long-term trainee is unmeasured (S2140), and T_max is an upper bound that includes some intrinsic tension (S2124).
- **Innate factor.** Ruling: each strength trait carries an innate force per unit muscle N0 (Strong 1.14, Stout 1.07, Feeble 0.915, Weak 0.82), fixed at creation and fully persistent — Angus (2026-10-14): "something like strong can also assume better neural activation depending on how the research supports it"; the innate harvest supports a heritable size-independent factor, mostly intrinsic rather than neural (S2143, S2162) — cost if wrong: the whole-body SD (S2170) and the individual persistence (S2172) are open; across the harvest's range of the regression share Strong's N0 runs from 1.086 to 1.204.
- **Trait starts.** Ruling: the strength traits keep their vanilla start levels (Weak 1, Feeble 3, none 5, Stout 7, Strong 9), reached through N0 plus lean; half of the start's lean difference is the permanent set point F0, and the natural cap moves by the same half — Angus (2026-10-14): "strong requires 10kg extra ... their base lean mass ... permanently +5kg" — cost if wrong: an idle Strong character detrains to level 7.64, out of the Strong band.
- **Natural cap.** Ruling: every trait's Fc is clamped at the natural FFMI limit, Kouri's 25.0 normalised to 1.80 m (S1915), which at the fixed 1.70 m is raw FFMI 24.37 (by Kouri's normalisation FFMI_norm = FFMI + 6.3 · (1.8 − h); the coefficient 6.3 is Kouri's, S1915) and F = 70.43 kg; Strong's cap becomes 13.40 and Stout's 12.34 (from 14.23 and 12.50), and none, Feeble and Weak are unchanged; the constant `ffmiNatural` = 25.0 is fixed, not an option — the controller (2026-10-14), as no natural trait should sit above the natural limit — cost if wrong: a server that wants an enhanced Strong character has no option for it, and Strong's and Stout's trajectories flatten near the cap; the cap is no longer the trait-shifted untrained cap for those two.
- **Profession Strength boost.** Ruling: a profession's Strength boost counts toward the creation body like a small muscle trait: the start level is `startLevel[pick] + boost`, clamped to [0, 10], built through the pick's N0 with no innate factor of its own; F0, Fc (with the natural-cap clamp), the thin cap and P follow the raised F as for a trait; creation and first sight read the boost off the profession's definition, 0 when unreadable; the anti-stacking rule still holds at each boost 0, 1 and 2 — Angus (2026-10-15): "Treat it like a small trait" — cost if wrong: a Strong Lumberjack starts at the level-10 ceiling with no headroom from its pick's extra point, and a first-sight body reads the pick off the native level, so a Stout pick under +1 whose native level fell from 8 to 6 before first sight is read as no pick.
- **First sight's muscle pick.** Ruling: first sight infers the muscle pick from the native Strength level net of the profession's and other held traits' boosts (vanilla's boost table), falling back to the held band at a clamp — the held band misreads a boosted profession's own band as a pick — cost if wrong: a Stout under +1 detrained to 6 before first sight is read as no pick. It replaces ruling 13-6's held-band reading (Task 17b fix 1).
- **Lean-scaled fat cuts and fat starts.** Ruling: the Overweight and Obese cuts and their margin scale with the body's lean, cutFat(k) = FAT_CUTS[sex][k] · H² · lm / Favg (Favg = fOfBio(5) = 52.02 kg), so the male cuts sit at 25 % and 33.3 % body fat for every lean; the creation fat of a fat or no weight pick scales the same way, fm = FMI[pick] · H² · F / Favg, with Obese moved from FMI 12.5 to 10.5, the middle of the male obese class I (9–12), so each start sits mid-band at 20 %, 29.4 % and 36.8 % body fat; fat creation stays fat-only, with no Forbes companion lean; the thin picks keep their BMI and FMI targets — Angus (2026-10-15): "Doesnt it make sense for more muscular individuals to be able to hold more total bodyfat than someone without musculature?", then chose "Yes, lean-scaled", the option that stated Obese starts at about 37 % — cost if wrong: a Strong character carries about 3 kg more fat than an average one before Overweight applies, and a Weak one about 3.3 kg less; Kelly's FMI cuts were fitted on the population's lean, not per individual.
- **Weak floor and anti-stacking.** Ruling: Weak's start is level 1, at −9.90 kg of lean (FFMI 14.57) with N0 0.82; Underweight and Very Underweight exclude Weak and Feeble; a creation test enumerates every legal pick set and asserts that each point-giving body trait makes the created body measurably worse — Angus (2026-10-14): "a floor is acceptable but we need to make sure that at player creation they cant take advantage of the floor by stacking things that give points but dont add downsides, or remove some of the traits" — cost if wrong: two fewer legal combinations.

## 12. Testing and evidence

### 12.1 Kernel tests (lupa)
Each check has a mutation pass that shows it fails:
- the growth anchor: on 20 sets with full gates, an average character reaches bio level 15 at 5 years;
- the strength level: L is linear in S, `level` and `fOfLevel` invert each other, and each start floors to its own level; on perfect training with T rising, the average reaches shown level 10 at Y = 4 years (± 0.02), and each trait's levels from 4 weeks to 10 years and its cap match § 2.4's table (± 0.01); Feeble and Weak stay below 10 for 10 years;
- R: 1.5651 at Y = 4 and 1.4814 at Y = 2, recomputed when `NR.StrengthYearsToLevel10` changes and only then; the growth options leave it unchanged;
- T: 1.0736 after 4 weeks at full signal; g scales the rise below W_sat; T holds through the 21-day grace and then decays with τ_down = 12 weeks; ts scales both and divides the grace;
- N0: fixed at creation per trait, unchanged by training, detraining and the heal;
- the creation pick sets: every legal set of the 8 body traits is built, for both sexes, and each point-giving trait in it (Weak, Feeble, Overweight, Obese, Underweight, Very Underweight) makes the body measurably worse than the same set without it, by a shown level at least 0.5 lower (Weak, Feeble and the thin picks) or a fat rung higher (the fat picks); Weak with either thin pick and Feeble with Underweight are shown to fail that test, which is why they are excluded (Feeble with Very Underweight is excluded with them by the same rule);
- a low weekly volume stalls where S_g(s) = S;
- protein or a surplus without the signal gives ΔF = 0;
- the status-dependent gate at s = 0.9 with F near F_c, over 8 weeks: balance gives ΔF < 0.5 %; +10 % gives no more than twice the balance gain, under 1 %, mostly as fat; −500 kcal/day at contest fat gives ΔF ≤ 0;
- detraining has a half-life of 6 weeks after a 14-day grace;
- retraining a novice takes no longer than the first block (Räntilä);
- the creation table in § 3.2, cell by cell;
- the natural cap: every trait's Fc is at most ffmiNaturalRaw · H² (70.43 kg), Strong's and Stout's are clamped to it (shown cap levels 13.40 and 12.34) and none, Feeble and Weak are not (10.78, 8.93, 6.99); a mutation without the clamp fails;
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
