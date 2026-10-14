# Lean-mass Strength and body-composition traits: design

Status: draft for Angus's review, 2026-10-14. Brainstormed in the session that closed Plan 12; each section below was presented and approved in turn, with the rulings in § 11.

Research behind it (copied to `docs/superpowers/research/2026-10-14-strength-redesign/` in the plan's first task, before any science row is minted):
- `vanilla-strength-rate.md`: vanilla Strength XP sources, pacing and days to level 10 on 42.21.
- `science-report.md` and `lean-science-part.tsv`: the first harvest (FFMI scale, multi-year gains, regain, gates).
- `hypertrophy-science-report.md` and `hypertrophy-science-part.tsv`: the 2015-2026 hypertrophy harvest (68 rows, 62 resolved). Its ids `H.n` and the first harvest's `S1.n` are provisional and become `S` ids at the mint.
- `trait-levers.md`: the engine's creation-trait levers, read on the 42.21 jar `4a0e9546ec`.

## 1. Goal

The Strength level becomes a pure reading of the character's lean mass.

Vanilla Strength XP stops building the level. It becomes a training signal, the analogue of the resistance-exercise stimulus that drives mTORC1 and muscle protein synthesis. On its own it builds nothing: lean mass grows only when the signal, enough protein and enough energy act together.

Progress gets harder in two ways as a character trains:
- the gain still available shrinks roughly exponentially;
- the signal needed to grow, and not merely hold, rises.

Lost lean mass comes back fast. The weight and strength traits describe body composition, are offered at creation for their points, and set the starting body. Nothing changes while a player is offline.

## 2. The scale

```
FFMI  = F / H²                         H = 1.70 m, fixed, sex-neutral
level = 5 + (FFMI − 18.0) / 0.5        one level ≈ 1.445 kg of fat-free mass F
```

- At creation, the untrained average is level 5 (FFMI 18.0, F = 52.0 kg).
- The untrained natural cap is level 16.5 (FFMI 23.75), under the about-25 natural limit (Kouri; first harvest).
- The Strength perk shows `clamp(floor(level), 0, 10)`; the XP bar shows the fraction toward the next level.
- Above 10, see § 7. The mod's panel always shows the true level, for example "Strength 12.3".

## 3. Creation

### 3.1 What is offered
The creation screen offers 8 body traits at their vanilla costs: Weak, Feeble, Stout and Strong (muscle), Overweight and Obese (fat), and Underweight and Very Underweight (thin). Emaciated is reached only in play.

On 42.21, the five weight-band traits are hidden profession traits (`IsProfessionTrait = true`) that the creation lists filter out (trait-levers § 1).

The mod restates the full definition block of each offered trait in a shared script, named `base:<id>` in `module Base`, because a same-name block replaces the whole definition and resets every omitted key (trait-levers § 2). Each restated block:
- sets `IsProfessionTrait = false`;
- drops the vanilla Strength and Fitness `XPBoosts`, since the body now sets those levels;
- keeps vanilla's cost and exclusions, and adds the missing pairs: Obese and Overweight both ways, and every pair inside a family (the four muscle traits, the four fat and thin traits).

Weight Gain and Weight Loss are restated without their `GrantedTraits`. They keep their place as intake-rate traits in the body model.

The descriptions are rewritten through the `UI_trait_*` translation keys to say what each trait now does.

### 3.2 What a pick does
A server `OnNewGame(player)` handler, guarded by `isServer()`, runs after vanilla's `applyTraits` and before the save (trait-levers §§ 3–4). It:
1. **Validates the picks.** The point total must be legal and no two picks may exclude each other; any illegal pick is stripped, latest first, and logged. The server checks neither of these itself.
2. **Builds the body:**

| Pick | Lean (F) | Natural cap | Set point | Fat |
|---|---|---|---|---|
| none | level 5 | level 16.5 | the start | the middle of the Healthy band |
| Feeble (−2) | level 3 | level 15.5 | the start | as picked |
| Weak (−5) | level 0 | level 14.0 | the start | as picked |
| Stout (+2) | level 7 | level 17.5 | the start | as picked |
| Strong (+4) | level 9 | level 18.5 | the start | as picked |
| Overweight | unchanged | unchanged | — | the middle of the High band |
| Obese | unchanged | unchanged | — | the middle of the Very high band |
| Underweight | lowered to reach BMI 18.0 at the Very lean fat | unchanged | the muscle pick's level | the Very lean band |
| Very Underweight | lowered to reach BMI 16.5 at the Very lean fat | unchanged | the muscle pick's level | the Very lean band |

   - **Cap rule (Angus):** a muscle trait moves the start by its full vanilla Strength offset and the natural cap by half of it.
   - **Thin traits are depletion.** The lean they remove is below the remembered peak, which starts at the set point, so it comes back on the fast regain path (§ 6) and leaves the cap alone.
   - **Fat bands** are one sex-neutral table (§ 8.1).
   - **Weight** = F + fat mass. This replaces `K.body.split`'s band-anchored split of vanilla's starting weight.
3. **Writes the weight, the Strength level (§ 7) and the body traits (§ 8).** Vanilla's creation band swap on `LevelPerk` can leave a trait the player never picked, for example Out of Shape after Weight Gain (trait-levers § 3). The handler's trait write is final.

## 4. The training signal

- **Capture.** A server `AddXP` listener adds every Strength gain (exercise, carrying, melee) into today's slot of a 7-slot daily ring.
- **Conversion.** Weekly hard sets S = the ring's sum ÷ `NR.StrengthXPPerSet`. The default for `NR.StrengthXPPerSet` is the Strength XP of one vanilla Fitness set taken to exhaustion, measured by a live calibration run before the constant ships (§ 10). Until then it carries no default and the kernel tests use a placeholder.
- **The XP never moves the level.** The next level write (§ 7) restores the level from F.
- **Replaced:** the resistance side of `NR_Kernel_Training` (the set-equivalents per rep, hit and tree). The aerobic side stays.

## 5. Growth

Every symbol is per character: F₀ is the set point, F_c the natural cap, P the remembered peak, and status s = (F − F₀)/(F_c − F₀), clamped to [0, 1].

```
S_g(s) = S_g0 · e^(β·s)                                     growth threshold, weekly hard sets
G      = max(0, √min(S, S_max) − √S_g(s)) / (√12 − 1)       the signal's response
dF/dt  = k · (F_c − F) · G · f_p · f_e                      per week, applied at day close as 1/7
```

| Constant | Default | Basis |
|---|---|---|
| S_g0 | 1 set | novices grow on 1 set a week (H.8) |
| β | 2.5 | game choice: the threshold rises from 1 set to 3.5 at s = 0.5 and 12 at s = 1. Indirect support from H.26, H.27, H.17 and H.24; contradicted by H.5 and H.25 (Aube 2022, Damas 2019); `NR.StrengthThresholdRise` = 0 disables the rise |
| S_max | 30 sets | the square-root fit's upper range (Pelland 2024/2026) |
| √ shape | — | Pelland's best fit of weekly sets against hypertrophy |
| k | the five-year shape | fitted (with β in place) so that an untrained average character on 20 sets a week with full gates reaches level 15 at 5 years (Angus: "Five year shape, tunable in settings"). The level-10 time and the per-trait times are then read off the fitted curve. A headroom-only sketch gave about 1.4 years to level 10 and about 5.5 kg in year 1, against the literature calibration's 7.2 kg |
| f_p | 0 at 0.4 g/kg/day, 0.5 at 0.8, 0.92 at 1.3, 1.0 at 1.6 and up; linear between | Morton 2018 (S0591), Tagawa 2020's 1.3 g/kg knee, the RDA (S0509). No per-meal cap: Trommelen 2023 (100 g against 25 g) |
| f_e | 0 at −500 kcal/day or deeper, 0.85 at balance, 1.0 at a 5 % surplus | Murphy & Koehler 2022; Helms, Iraki, Slater: a larger surplus adds fat only |

- **Signal, protein and energy multiply.** Without the signal, protein and a surplus build no muscle; overfeeding's lean share goes to the non-muscle lean the body model already holds (H.67 open; a game choice).
- **Protein** is the closed day's grams per kg from the existing `p7` ring.
- **Energy** is the closed day's balance from the existing `eb7` ring.
- **Low volume stalls** where S_g(s) meets S: that is the "harder even to grow" effect.

## 6. Maintenance, detraining and regain

- **Maintenance threshold:** S_m(s) = S_g(s)/3 (Bickel 2011, Spiering 2021). That it holds at every status is a game choice (H.64).
- **Grace:** after 14 consecutive online days with S below S_m, detraining starts. Any day at or above S_m resets the counter.
- **Detraining:** `dF/dt = −λ · (F − F₀) · (1 − S/S_m)`, with λ = ln 2 / 6 weeks (Räntilä 2025: 4.9–9.2 weeks). It acts only while F > F₀.
- **Starvation** takes F through the existing partition deficit arm, independent of training.
- **Remembered peak P:** P = max(P, F) at each day close. P decays toward F with a 2-year half-life (Rahmati 2022 meta and Serrano 2025: human myonuclei are not permanent; the memory is epigenetic, Seaborne 2018).
- **Regain:** while F < P, dF/dt = max(the § 5 growth, λ_r · (P − F) · min(1, G)), with λ_r = ln 2 / 6 weeks. Retraining is at least as fast as naive training (Räntilä 2025 equal blocks; Seaborne 2018 1.6×, n = 7). Its use for advanced lifters is a game choice (H.68).

## 7. Writing the level, and BeyondTen

At day close, and once at creation, the server computes level L from F:
- **floor(L) ≤ 10:** if the native Strength level differs, the server sets it and pins native XP at that level's starting total.
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
| Fat load | body-fat % in the sex-neutral bands of § 8.1 | Overweight at High, Obese at Very high |
| Muscle | the lean level | Weak, Feeble, Stout, Strong through vanilla's own band swap (§ 7) |
| Thinness | BMI at H, from F + fat | Underweight below 18.5, Very Underweight below 17, Emaciated below 16 (the WHO thinness grades) |

### 8.1 The fat bands

The traits and the panel's Body fat word read the mod's existing `K.view.FAT_CUTS_*` through the character's effective sex (§ 14), so by default every character reads the male table:

| Band | Body fat from (male table) |
|---|---|
| Very lean | below 6 % (S1910) |
| Lean | 6 % |
| Healthy | 8 % (S1905) |
| High | 20 % |
| Very high | 25 % |

The lean scale is sex-neutral and ignores the option.

- **Precedence:** a thinness trait excludes the fat traits.
- **Damping:** a switch needs a margin of 0.5 BMI or 1 percentage point of body fat past its cut, and switches are checked once a day.
- **Writes:** server-side through `getCharacterTraits():add/remove` (wall map G3).
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

`lm` is F.

### 9.2 Removed (the mod is unreleased: no migration)
- `NR_Kernel_Strength`'s neural term, memory floor, cumulative deficit, disuse term, fSlow ceiling and the rise-hold and hourly-fall write policy;
- the resistance side of `NR_Kernel_Training`;
- `K.body.split` and its build offsets;
- `lm0`/`lm0dis` where F0 replaces them.

### 9.3 Offline time (Angus: "I do not expect character stats to change when they are offline")
- The record's day calendar (`dayIndex`, the day stamps) advances only on game days the player is online.
- A reconnect after any gap resumes the calendar where it stopped. The day-close catch-up (`MAX_CLOSES`) closes no missed days.
- Every daily and weekly ring is audited (`p7`, `eb7`, `mass7`, `bandWeek`, `sig7` and the training rings), and so are the grace counter and P's decay: each counts only online days.

### 9.4 Cost (Rule 6)
- The `AddXP` listener is an event-driven add, with no per-tick work.
- Growth, traits and the level write run at day close, once per player per online game day. The plan benches the day close before and after.

## 10. Sandbox options

The options follow the existing `NR.<Name>` pattern in `42.21/media/sandbox-options.txt`. Every default is the cited value above.

| Option | Default |
|---|---|
| `NR.StrengthTimeScale` (the biology clock: 1.0 means one game day is one real day) | 1.0 |
| `NR.StrengthXPPerSet` | from the calibration run |
| `NR.StrengthCapLevel` (the untrained natural cap) | 16.5 |
| `NR.StrengthTraitCapShare` | 0.5 |
| `NR.StrengthRate` (k) | the five-year shape |
| `NR.StrengthThreshold` (S_g0) | 1 |
| `NR.StrengthThresholdRise` (β) | 2.5 |
| `NR.StrengthMaintainShare` | 1/3 |
| `NR.StrengthGraceDays` | 14 |
| `NR.StrengthDetrainHalfLifeWeeks` | 6 |
| `NR.StrengthRegainHalfLifeWeeks` | 6 |
| `NR.StrengthPeakHalfLifeYears` | 2 |
| `NR.StrengthProteinFull` (g/kg) | 1.6 |
| `NR.StrengthDeficitZero` (kcal) | −500 |
| `NR.SexSpecific` (mod-wide, § 14) | off |

## 11. Rulings made in the brainstorm

- **Scale.** Ruling: the level is FFMI at a fixed 1.70 m, sex-neutral — Angus's choice ("assume average height always and make it gender-indifferent for now") — cost if wrong: none planned; a sex term is excluded by the ruling below.
- **Stimulus.** Ruling: vanilla Strength XP is the training signal and replaces the mod's own resistance set-equivalents — Angus chose "Vanilla Strength XP", and the calibration ties it to one hard set — cost if wrong: incidental carrying may count as more sets than real training does, and a per-source discount is added.
- **Time.** Ruling: one game day is one biological day by default, with a sandbox multiplier — Angus's choice — cost if wrong: most characters never reach high levels on default servers; operators compress it.
- **Threshold.** Ruling: the growth threshold rises with status, β = 2.5, sandbox-tunable — Angus's premise, with mixed evidence — cost if wrong: advanced characters stall early; β = 0 restores headroom-only.
- **Curve.** Ruling: the five-year shape, with the cap at 16.5, chosen over the literature's first year — Angus: "Five year shape, tunable in settings" — cost if wrong: year 1 is slower than the studies by about 1.7 kg.
- **Traits.** Ruling: the vanilla strength-trait order is kept (Weak is the stronger penalty) — Angus — cost if wrong: none at the engine level.
- **Creation.** Ruling: 8 traits offered, Emaciated excluded, and the picks are re-validated on the server — Angus — cost if wrong: validation code that a live check must prove sees the whole pick list.
- **Peak memory.** Ruling: P decays with a 2-year half-life, not permanently — Rahmati 2022 and Serrano 2025 overturn the first harvest's "might be permanent" (S1.21) — cost if wrong: regain after a multi-year break is slower than players expect.
- **No sex-specific rules by default.** Ruling: one mod-wide option, `NR.SexSpecific` (default off); when it is off every character uses the male values everywhere the mod indexes by sex (§ 14) — Angus (2026-10-14): "I dont want gender specific rules, base game treats them equally", then "we can flag this as an option however, just default it to off", then "Lets just use male values for females if its disabled" — cost if wrong: by default a female character's requirements and body bands are the male studies' values (for example the iron requirement and the fat bands).

## 12. Testing and evidence

### 12.1 Kernel tests (lupa)
Each check has a mutation pass that shows it fails:
- the curve: on 20 sets with full gates, an average character reaches level 15 at 5 years; Weak never reaches 15; Feeble reaches it later than the average; Stout and Strong reach it sooner;
- a low weekly volume stalls where S_g(s) = S;
- protein or a surplus without the signal gives ΔF = 0;
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
- **The XP-per-set calibration run:** one Fitness set to exhaustion, its Strength XP logged against wall time.
- **A BeyondTen run** with the workshop mod in a test profile.
- **An offline-gap run:** a disconnect over several game days changes no stat.

### 12.3 Registers
- The two harvests' rows are minted after their reports are copied into the research folder.
- The first harvest's S1.21 ("might be permanent") and the per-meal cap reading of S0065 are qualified or superseded by the newer rows.
- The stale claim rows #0529 and #3344 (the 90-minute default day) and #2115 and #2116 (the 42.21 carry roll) are corrected.

## 14. The mod-wide sex option

`NR.SexSpecific` (boolean, default off) decides each character's effective sex index: the engine's `isFemale` when the option is on, and 1 (male) for everyone when it is off.

- **Stored raw, resolved at use.** `record.body.sex` keeps the engine's value, and one helper resolves the effective index wherever the mod reads it. Changing the option mid-save then takes effect at once and needs no record rewrite.
- **Server readers:** the nutrient requirements and the choline factor (`NR_Server_Nutrients`), fluids, the Widmark r, iron and calcium (`NR_Kernel_Interact`), the heal reference (`NR_Kernel_Heal`) and the effects (`NR_Server_Effects`).
- **Client readers:** the Body fat word (`NR_Client_View`) and the tooltip's sex (`NR_Client_Tooltip`) read the option from SandboxVars.
- **Tests:** with the option off, a female character's every sex-indexed output equals a male's. With it on, today's values are unchanged, so the golden trace does not move for a male character.

## 15. Out of scope

- A height term on the lean scale. A sex term is excluded by ruling, not deferred.
- Tuning the mod's continuous fat-load effects.
- Fitness (aerobic) levels.
- Any change to vanilla's carry formula beyond the Strength level it reads.
