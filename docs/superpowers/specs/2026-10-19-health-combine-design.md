# Plan 17: the health curve and the combining options — design

Angus, 2026-10-19, a brainstorm in chat:
- the guide's fast chart shows no vanilla health line;
- starvation's health should drop fast when vanilla's would, then taper on a logarithmic tail to the real death;
- each untreated cause damages health on its own, and several at once compound;
- the range from vanilla to fully realistic becomes two sandbox options.

Every decision below is his, made in that brainstorm.

## 1. The health model

### 1.1 One remaining fraction per state

Each lethal state of `NR_Kernel_Drain.lua` keeps a **remaining fraction** `f`: 1 at its onset, 0 at its death point.

| State | Clock | Shape |
|---|---|---|
| Starvation | Realistic pace: BMI progress `p = (bmi0 − bmi) / (bmi0 − 12)`. Shortened pace: hours since onset | the curve (§ 1.2), unbroken to 0. No final stage (Angus: "forget the short tail rule on hunger"). |
| Dehydration | Realistic pace: deficit progress from 4 % to 15 %, then the final stage from 15 % to 17 %. Shortened pace: hours since onset | Realistic: the curve from 1 to 0.1 over 4–15 %, then linear from 0.1 to 0 over 15–17 %, the final stage kept (§ 1.4). Shortened: the curve, unbroken to 0. |
| Beriberi, scurvy, pellagra | hours at the clinical grade | linear from 1 to 0 at the current death times (840 h, 2160 h, 4320 h). Angus: deficiencies are the mod's own, and linear is fine. |
| Severe hyponatraemia, the iron rung | hours in the state | linear from 1 to 0 at the current death times (6 h, 24 h) |

Every onset rule stays as it is: the acute and chronic starvation onsets, the 4 % dehydration onset, the clinical grade, the sodium and iron rungs, the meal-spell suspension and the Overlay exclusions.

### 1.2 The curve

`f(τ) = 1 − ln(1 + a·τ) / ln(1 + a·T)`, where τ is the clock since onset and T is the death point on that clock.
- `f(0) = 1` and `f(T) = 0`. The opening slope is `a / ln(1 + a·T)`, and the curve flattens after it.
- `a` is chosen so that the opening slope in health equals **vanilla's own drain rate** for that cause (§ 2.1).
- As `a → 0` the curve becomes the straight line `1 − τ/T`. A solved `a` at or below a small epsilon takes the line. This is what makes Vanilla pace exact.

`a` is set in one of two ways:
- **Time clocks** (Shortened pace): solve `100·a / ln(1 + a·T) = r` by Newton, where `r` is vanilla's rate in health per game hour at the server's day length. It is cached per (T, day length) and re-solved when the day length changes, never every minute.
- **Severity clocks** (Realistic starvation by BMI, Realistic dehydration by deficit): `a` is a fixed constant per state, calibrated offline (§ 4.1). It is set so that the default creation body, on the guide's fast (water, no food) at the 90-minute day, opens at vanilla's rate.

  A heavier body loses BMI more slowly, so it opens more gently in time as well as dying later. Recorded as a game choice.

### 1.3 Combining: `NR.HealthCombine`

The minute's **target** is computed from every active state's fraction `f_i`:
- **Worst only:** `100 · min f_i`. This is today's rule; health reaches 0 only at one cause's death point.
- **Multiply** (default): `100 · Π f_i`. Health still reaches 0 only at one cause's death point, but several causes compound.
- **Add:** `100 · max(0, 1 − Σ (1 − f_i))`. Losses add, so the body can give up before any single cause's death point. This is vanilla's own stacking of the hunger and thirst level-4 drains (#0516).

With no state active there is no target, and vanilla regeneration and the food heal resume, as now.

### 1.4 Following the target

- **The drain:** health falls toward the target by at most `cap · dtM / 1440` a minute. `cap` is the sum of the active states' **rates**, in health per game day:
  - for a curve state, its opening rate in health per game day (vanilla's rate at the day length);
  - for a linear state, `100 · 24 / T_hours`.

  This lets health keep up with a compounding target and keeps a target that jumps down from landing as a cliff. A jump comes from a new onset, a pace or combine change mid-game, or a fraction recomputed after a weight gain. `K.drain.take` keeps its contract: never past the target.
- **Healing:** `K.drain.heal` keeps its contract: vanilla's regeneration lifts health toward the target and never above it. Ending a state removes its fraction, so the target rises and health heals back toward it.
- **Sleep:** vanilla wakes a sleeper on every tick at health 10 or below (#3900).
  - Starvation's unbroken curve and the linear deficiencies now spend their last stretch under 10. For example, beriberi's last 84 h and pellagra's last 18 days.
  - Only Realistic dehydration keeps a final stage, from 15 % to 17 %.
  - This goes on the limitations list and the guide.
- **The record:** `record.drain` carries `target` in place of `targetFloor`, plus one fraction per active code, `frac[code]`. The panel and mirror codes are unchanged; `state` is the code with the smallest fraction.

## 2. The options

### 2.1 Vanilla's rates (jar reads already in the register)

The hunger level-4 term is 3.3e-4 health per multiplier unit and the thirst term 1.65e-3 (#0516). The terms carry the multiplier without the day factor (#0518), and a game minute holds `2 × dayMinutes` units (#2922). Per game hour:
- `r_hunger = 0.0396 · dayMinutes`: 3.564 at 90 min, 2.376 at 60 min;
- `r_thirst = 0.198 · dayMinutes`: 17.82 at 90 min, 11.88 at 60 min.

The day length comes from `NR.read.dayMin(ctx, K.drain.DAY_MINUTES)`, which already exists.

### 2.2 `NR.DeathPace` (enum: Vanilla, Shortened, Realistic; default Realistic)

| Pace | Starvation T | Dehydration T |
|---|---|---|
| Vanilla | `100 / r_hunger` game hours from onset, a straight line: 28.06 h at 90 min | `100 / r_thirst` game hours: 5.61 h at 90 min |
| Shortened | 336 game hours (14 days), the curve on hours | 48 game hours (2 days), the curve on hours |
| Realistic | BMI 12, the curve on BMI progress | 17 %, the curve to 15 %, then the final stage |

- The deficiencies and the sodium and iron rungs are the same at every pace.
- The onsets are the mod's own at every pace. The mod's Starving shows at 34.45 h after the last meal against vanilla's 34.84 h. The mod's dehydration opens at 32.88 h from a fresh record against vanilla's level-4 thirst at 29.13 h (#0175).
- The 336 h and 48 h are game choices, approved by Angus.

### 2.3 `NR.HealthCombine` (enum: Worst only, Multiply, Add; default Multiply)

As § 1.3. Vanilla pace with Add is the "plain vanilla" corner.

### 2.4 Reading the options

- Both options are read once a server minute beside `NR.sleepOn()`, in `NR_Server_Options.lua`, not per player. They are passed into `K.drain.step` as two integers and a day length, with no allocation.
- A change takes effect within a game minute, with no changed hook.
- Both get translations in `Sandbox.json` (EN), in the house style of `NR.Mode` and `NR.Severity`.
- The removed constants go:
  - `FIRST_FLOOR`;
  - `STARVE_RATE`;
  - `DEF_HOLD_H`, `DEF_FINAL_H` and `DEF_RATE`;
  - `ACUTE_FINAL_H`;
  - `BMI_KNEE` (starvation's final stage);
  - `timeKnots`;
  - `starveFloor`.

  `SLEEP_FLOOR` is kept only for dehydration's final stage. No compatibility shim: the mod is unreleased.

## 3. Rule 6

- There is no per-tick work. Each player-minute adds at most two `math.log` calls per active curve state, plus a product. Newton runs only when (T, day length) changes.
- The plan benches the drain step before and after on lupa, and counts Java calls per player-minute with a recording stub against the build before. The target is +0 per player and +2 per server minute for the two option reads.

## 4. Proof

### 4.1 The calibration tool

`tools/calibrate_drain_curve.py` replays the default creation body's fast with water at the 90-minute day, through the replay host. It reads the BMI and deficit progress rate at each onset, and solves `a_starve` and `a_dehyd` so the opening slope equals `r_hunger` and `r_thirst` at 90 min.

It writes a compact artifact under `testing/artifacts/` and has a `--check` mode. The constants in the kernel carry their artifact pointer.

### 4.2 Kernel tests

- each curve's ends, its opening slope and its monotonicity, and the `a → 0` line;
- each combine rule;
- the properties: Worst ≥ Multiply ≥ Add at every minute; under Worst and Multiply, the target is 0 only when some `f_i` is 0;
- the drain never passes the target and the cap holds;
- healing lifts health to the target after a state ends.

A mutation pass on these tests (CLAUDE.md § 6) is part of the review.

### 4.3 The vanilla oracle

Vanilla pace with Add, on the replay host, reproduces `tools/vanilla_model.py`'s fast death time, 62.9 h from the last meal on its schedule. The tolerance is the difference between the two onsets (34.45 against 34.84 h) plus one minute, stated in the test.

### 4.4 The golden trace

It is re-recorded in its own commit under the named cause "Plan 17: the remaining-fraction drain", with every moved leaf attributed.

### 4.5 Live

One session of under 10 minutes on the staged copy:
- **(a)** Realistic with Multiply: the onset drain matches the HEAD replay of the run's own inputs, which ties the opening slope to vanilla's rate.
- **(b)** Vanilla with Add: the starving character dies on vanilla's clock, against the replay and x442.
- **(c)** An admin switch of `NR.HealthCombine` mid-state is followed within a game minute.

A split into two sessions is allowed. Every CLAUDE.md § 5 rule applies.

### 4.6 Pre-upload re-check

The upload copy changes, so after the plan:
- it is re-staged;
- the options read-back boot (x471's design) is repeated with the two new options set away from their defaults;
- the one-byte checksum boot is not repeated, because that mechanism is the engine's, not the mod's.

## 5. Guide

The fast chart (S2d) gets these tabs:
- **Health:** the mod's line (Realistic, Multiply), with vanilla's model and live health lines on the same axis.
- **Pace:** a starving body with water and vitamins, so starvation alone, under Vanilla, Shortened and Realistic.
- **Combining:** a fast with water and no vitamins, starvation and then beriberi, under Worst only, Multiply and Add.
- **No water, body mass and vanilla weight:** kept, updated to the new model.

Every sentence and number on the page reads the data, and each new series is a kernel replay. Also updated:
- the options section;
- the limitations: the sleep wake-ups under 10; Add can kill before any one cause's death point;
- the stale constants in the notes (`STARVE_RATE`, `FIRST_FLOOR` and others).

## 6. Register and pages

- **Superseded:**
  - the live drain-rate readings #3938 (x454, 25 a day to the first floor), #3940 and #3941 (x456);
  - the floor-mechanism rows (the first floor, the hold, the knee, lowest-floor-wins, the 25-a-day rate) and their pages, each moved to a successor.
- **New rows:**
  - the curve;
  - the combine step;
  - the options and the vanilla-rate formula (resting on #0516, #0518 and #2922);
  - the calibration artifact;
  - the new live readings.
- **The body-effects owner sentences** are rewritten.

## 7. Game choices

- the curve's form and its opening at vanilla's rate;
- `a_starve` and `a_dehyd` (calibrated at the default body and the 90-minute day);
- Shortened's 336 h and 48 h;
- the defaults Realistic and Multiply;
- the drain cap as the sum of the active rates;
- dehydration's final stage kept at Realistic only;
- the linear deficiency and rung lines at their current death times.

## 8. Not changed

- the onsets and the starvation effect phases (`STARVE_PHASE_H`);
- refeeding;
- the HUNGER and THIRST caps;
- Overlay mode's exclusions;
- vanilla's regeneration terms;
- the death mechanics the adapter already uses to reach health 0.
