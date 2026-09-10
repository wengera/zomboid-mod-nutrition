# Nutrition core — weight, calories, macros

**Verified against: 42.20.4 (`b0bbce05d5`)** — `zombie.characters.BodyDamage.Nutrition`
(pzdis), 2026-09-04; re-read unchanged and partly measured 2026-09-10 (slice 01);
slice-03 corrections 2026-09-10; the weight model run against the live dedicated
server over three game-days 2026-09-10 (slice 04, § Verified on server).
Migrated from pz-b42 `findings/nutrition-weight.md`. Intake — how food fills these
stores — is [eating-pipeline.md](eating-pipeline.md).

## Weight model (`Nutrition.updateWeight`)

*Evidence: **C** — `Nutrition.updateWeight()V @0 L138` onward, re-read unchanged on the
42.20.4 jar by `docs/superpowers/plans/01-notes.md` Q5.*

```
gainThreshold = 1000 + (weight - 80) × 40        # w70: 600 · w80: 1000 · w90: 1400
    trait Weight Gain  (weight < 90): base 700
    trait Weight Loss  (weight > 70): base 1800
loseThreshold = min(0, (weight - 70) × 30)       # ≥70: any negative calories
                                                 # w60: needs < −300 to keep losing
if calories > gainThreshold:
    rate = 1.3e-5 /game-sec × min(1, calories/4000)     # 1.12 kg/game-day at 4000, but the
                                                        # store clamps at 3700 → ≤1.039 kg/day
    if carbs > 700 OR lipids > 700:   rate ×3           # ≤3.117 kg/game-day after that clamp
    elif carbs > 400 OR lipids > 400: rate ×2
elif calories < loseThreshold:
    rate = 8.5e-6 × min(1, |calories|/2500)             # 0.73 kg/day at −2500, but the store
                                                        # clamps at −2200 → ≤0.646 kg/game-day
```

Rounding convention: every kg/game-day figure in this file is quoted to **three decimals** — the
clamped ceilings `1.039` · `3.117` · `0.646` here and in the table below, and the measured rates
in § Verified on server.

Every branch above except the macro multipliers was run against the live server over
three game-days; the runs, the residuals and what they do *not* cover are below in
§ [Verified on server](#verified-on-server-slice-04).

The five terms of that block, with what each is worth and how it is graded (the formulas are
**not** repeated here — read them off the block above):

| Term (block above) | Value | Ev |
|---|---|---|
| `gainThreshold` | w70 600 · w80 1000 · w90 1400 | C `updateWeight()V @0 L138` onward; **M (bounded, not measured)** — run 2 stayed in the gain branch for all 72 game-hours, so the threshold was never crossed downward: its calorie minimum, 1362.8, only bounds the threshold from above over w 80–82.5 (1000…1101) — `scenario-20260910-054012`, [`scenario-nutrition_3day_gain.json`](../../testing/artifacts/scenario-20260910-054012/scenario-nutrition_3day_gain.json) |
| gain `rate` | 1.12 kg/game-day at a 4000 kcal store; ≤1.039 under the 3700 clamp | C; **M** **+2.526 kg** measured over 72.0 game-hours against **+2.551** integrated from that run's own calorie trace (0.842 vs 0.850 kg/game-day) — same run/artifact |
| the `×2` / `×3` carb and lipid multipliers | ≤3.117 kg/game-day after the calorie clamp | C (the two multiplier branches of the same method) — **not exercised** by either scenario: both macro stores only ever drain (see § Verified on server, *what it does not cover*) |
| `loseThreshold` | 0 at w ≥ 70 — any negative calorie total loses | C; **M** run 3 crossed it inside the first game-hour (first sample after the reset: −57.3 kcal) — `scenario-20260910-055029`, [`scenario-nutrition_3day_fast.json`](../../testing/artifacts/scenario-20260910-055029/scenario-nutrition_3day_fast.json) |
| loss `rate` | 0.73 kg/game-day at −2500; ≤0.646 under the −2200 floor | C; **M** **−1.426 kg** measured against **−1.412** predicted, and day 3 — spent entirely on the floor — lost **0.646 kg** against `8.5e-6 × 2200/2500 × 86 400` = 0.646 — same run/artifact |

Weight bands (`applyTraitFromWeight`, re-checked every ~2000 updates) — the
comparisons are **inclusive at both ends**: Emaciated ≤50 · Very Underweight
50–65 (`>50`, `≤65`) · Underweight 65–75 (`>65`, `≤75`) · **normal the open
interval (75, 85)** · Overweight 85–100 (`≥85`, `<100`) · Obese ≥100. Corrected
2026-09-10 by slice 03, which read the comparisons and measured the 100 / 85 / 75
edges on the server — full table, the trait effects outside `Nutrition`, and the
`characterHaveWeightTrouble` bug in [body-stats.md](body-stats.md) § Weight bands.

**Store clamps** (settled in slice 01): calories `[-2200, 3700]`, carbohydrates /
proteins / lipids `[-500, 1000]` each — `Nutrition.setCalories @1 L321, @12 L324` and
the three macro setters `@1/@12` (C), measured exactly on the server bus in run
`exp01-20260910-003929` (M). The calorie ceiling caps `min(1, calories/4000)` at 0.925,
so the plain gain rate never exceeds ≈1.039 kg/game-day and the loss rate never exceeds
≈0.646 kg/game-day — see [eating-pipeline.md](eating-pipeline.md) § Inputs for the
3-day scenario. Both branches have now been run on the server (below); the **loss**
ceiling was reached and matched exactly, while the **gain** ceiling stays a bound the
runs stayed under, because a fed store sawtooths beneath the clamp instead of sitting
on it.

## Verified on server (slice 04)

Three unattended `pzt scenario` runs on the live dedicated server, 2026-09-10: fixture
`default`, build 42.20.4, side **server**, subject `admin`, `settimespeed 30`, **73 hourly
samples over 72.0 game-hours** each, **0 server error lines** in all three, and `EveryOneMinute`
measured at **1.000 ticks per game-minute** (7.99–8.00 game-minutes per wall second).

*Three wall-clock marks, from a fresh clone.* The committed artifacts carry
`cadence.wall_s` = **540.4–540.6 s**: the test window itself, `test.run` to the result doc, timed
inside the game (`startedWall` → `t`). ≈**593 s** is that same instant on the *runner's* clock,
which starts at server launch and therefore includes the ~53 s of boot and client attach; **603 s**
adds teardown. Only the first is in `testing/artifacts/`; the other two are timeline marks in the
run report under `testing/runs/<run id>/` (gitignored), which is why a clone can reconcile them
but not re-derive them.

The scenario
(`server/scenarios/PZTestKit_Scenario_Nutrition.lua`) only drives the world and records the
server's `Nutrition` object once a game-hour; the check is Python
(`testing/pzt/scenarios_nutrition.py`): it integrates the model above sample-to-sample over
each run's **own measured calorie and macro trace** and compares the weight it predicts with
the weight the server reported, inside `max(15 % of the predicted delta, 0.05 kg)`. Command,
test-layer API and result-doc shape: [`docs/testing/README.md`](../testing/README.md)
§ Scenarios and the test layer.

| # | Run id | Scenario | Measured Δ | Predicted Δ | Residual | Tol | Verdict | Ev |
|---|---|---|---|---|---|---|---|---|
| 1 | `scenario-20260910-052624` | `nutrition_3day_gain`, hunger/thirst **not** pinned | **+1.045** over the 34 alive game-hours (the file's whole-trace `+1.073` is a corpse reading — **do not cite**) | **+1.057** alive · 2.688 whole trace | **−0.012** alive · −1.615 | 0.159 · 0.403 | **FAIL** — the subject died at game-hour 35 | **M** [`scenario-nutrition_3day_gain.json`](../../testing/artifacts/scenario-20260910-052624/scenario-nutrition_3day_gain.json); the whole-trace keys of this run are listed under *do not cite* in [`testing/artifacts/README.md`](../../testing/artifacts/README.md) |
| 2 | `scenario-20260910-054012` | `nutrition_3day_gain`, hunger/thirst pinned after every sample | **+2.526 kg** | +2.551 | **−0.025** | 0.383 | **PASS** | **M** [`scenario-nutrition_3day_gain.json`](../../testing/artifacts/scenario-20260910-054012/scenario-nutrition_3day_gain.json) |
| 3 | `scenario-20260910-055029` | `nutrition_3day_fast`, no intake | **−1.426 kg** | −1.412 | **−0.014** | 0.212 | **PASS** | **M** [`scenario-nutrition_3day_fast.json`](../../testing/artifacts/scenario-20260910-055029/scenario-nutrition_3day_fast.json) |

**The residuals are the check's own quadrature, not model error.** Hourly samples integrated
with the calorie value at the *start* of each interval bias the integral by ~0.025 kg over
three game-days; re-integrating the same samples with the interval **midpoint** instead
(crediting each dose at the interval end, where the feed actually landed) collapses the
residuals to **−0.0003 kg** (run 2) and **−0.0002 kg** (run 3). So the decoded model
reproduces on the server to well under a gram over three game-days, and ~0.03 kg per three
game-days is the floor of what this check can resolve.

**What the runs pin down, beyond the two branch rates.**

- **The 3700 ceiling is what bounds a fed character, not the rate constant.** Run 2 asked for
  12 000 kcal in six +2 000 doses (hours 0, 12, 24, 36, 48, 60 — one dose of 4 000 would be
  truncated on contact) and the store kept **7 210: 4 790 kcal lost to the clamp**, every loss
  logged before/after/asked and parsed back out by the evaluator. Its whole-run **0.842
  kg/game-day** is short of the **1.039** ceiling above (`1.3e-5 × 3700/4000 × 86 400`, what a
  store *pinned* at the clamp would give) and further short of the **1.12** an unclamped 4 000
  kcal store implies — but the two shortfalls have different causes, and the run separates them:
  - **Day 1 is a ramp, and it is what drags the three-day mean down.** The store starts at 0 and
    the first dose only reaches 2 000, so day 1 averages `min(1, calories/4000)` = **0.583** and
    gains **0.647 kg**. Over all 72 hours the time-averaged factor is **0.757**, and that is the
    figure the whole-run rate answers to: `1.3e-5 × 0.757 × 86 400` = **0.850 kg/game-day**,
    against 0.842 measured — the ~1 % gap being the check's own left-endpoint quadrature (below),
    not a second effect.
  - **Days 2–3 alone gain 0.940 kg/game-day, at a factor of ≈0.84** — the trace oscillates
    between the 3700 ceiling and ~2 990 there, so the factor sits near 0.84 rather than the
    0.925 a pinned store would give (only **4 of the 73 samples** are actually at the ceiling).
  So neither figure measures the ceiling: 0.842 is a three-day mean containing an empty store,
  and 0.940 is what a *sawtoothing* store at this dose does. **M**, run 2.
- **The −2200 floor bounds starvation the same way.** Run 3 reached the floor at game-hour 39
  (38.2 h predicted at a flat 80 kg; it arrives later because the burn falls with the weight)
  and spent day 3 entirely on it, losing **0.646 kg** — the derived clamped-fast ceiling
  `8.5e-6 × 2200/2500 × 86 400` = **0.646** (0.646272 exactly), confirmed to three decimals.
  Day 1 loses only 0.204 kg and day 2 0.576 kg: the rate scales with the deficit, so a fast
  ramps. **M**, run 3.
- **Cross-checks read off the same samples** (diagnosis, not assertions — see below). Idle
  calorie burn **−1 408.1 / −1 385.0 / −1 399.7 kcal per game-day** (run 2, run 3, run 1's alive
  window) against −1 402.5 / −1 379.5 / −1 390.2 predicted by `0.016 × weight/80 × 86 400` at
  each run's interval-mean weight — **+0.4 / +0.4 / +0.7 %**, the burn model of
  [body-stats.md](body-stats.md) § Passive burn re-confirmed at a second cadence. Carbohydrate
  drain **−302.4 per game-day** against `0.0035 × 86 400` — exact, in runs 2 and 3 over their
  whole traces and in run 1 over its alive window — and carbs hit their −500 floor in run 2 at
  the **game-hour 40.0** sample (predicted 39.7 h, inside the same hourly interval). **M**.

**What the check does not cover.**

- **One assertion: the weight delta over the run.** No burn rate, no threshold crossing and no
  macro multiplier is asserted; every figure in the bullet above is a cross-check fitted off
  the same samples afterwards.
- **Hourly resolution, left-endpoint integration.** The check cannot resolve a systematic model
  error smaller than its own ≈0.03 kg / 3 game-days bias.
- **The ×2 / ×3 carb and lipid multipliers stay C-only.** Both macro stores start at 0 and only
  drain (−0.0035/game-second), so reaching the +400 threshold needs the *intake* side
  (`Eat`/`EatFoodPacket`, [eating-pipeline.md](eating-pipeline.md)), not `setCalories`; run 2
  ended at carbs −500 / lipids −292.9. A slice that wants those branches must feed real items.
- **One narrow slice of the weight axis**: 78.5–82.5 kg, no weight-band trait held, no
  `Weight Gain` / `Weight Loss` trait threshold base, and no `Nutrition = false` control run.
- These are `setCalories` runs, so nothing here tests intake, food items, or the sandbox gate.
- The three artifacts **predate slice 04's fix round 1**: the `thirst` sample column and the
  evaluator's dead-subject verdict landed after them and have not been exercised live (the
  scenario's own die-early abort was in place for runs 2 and 3, and never fired). The delta,
  and an offline re-evaluation reproducing every stored number, are disclosed in
  [`testing/artifacts/README.md`](../../testing/artifacts/README.md).

**Finding — `setCalories` is not food** (run 1, `scenario-20260910-052624`, Ev **M**). The
first attempt fed the calorie store and nothing else. `setCalories` fills `Nutrition` and never
touches `CharacterStat.HUNGER` / `THIRST`, so the fed character dehydrated on the vanilla
clock: health fell 100 → 0 from **≈29.13 game-hours** at **−17.820029 health per game-hour on
this fixture's 90-minute day** (the rate is per *multiplier* unit, so it is 11.88/game-hour on
the 60-minute default — [body-stats.md](body-stats.md) § Discrepancies row 6) and the subject
**died at game-hour 35**, with HUNGRY never above level 3 (hunger peaked at
0.699892 against a strict `> 0.70`). That rate is `BodyDamage.Update`'s **`THIRST == 4`**
branch — five times the `HUNGRY == 4` one — whose constants, day-length dependence and jar
citations are in [body-stats.md](body-stats.md) § What each level does (the health-loss row)
and § Discrepancies row 6. Two consequences:

- **`Nutrition.update` stops on a corpse, and weight freezes at the death value.** From the
  first dead sample, weight, carbohydrates, lipids, proteins, hunger and health are bit-flat
  for 37 game-hours (carbs frozen at −437.888763, nowhere near their −500 floor, so it is not a
  clamp). Calories are the exception and they prove the point: they step to 3 700 at the
  hour-36 dose and hold, because `setCalories` is an external write that still lands on a
  corpse while the update that would drain it does not run. Half that run measured a dead man.
- **Anything that fills the calorie store must manage hunger and thirst too** — a mod granting
  nutrition, a debug command, a test scenario. Unattended, the level-4 thirst drain kills in
  ~35 game-hours **on this fixture's 90-minute day**. On the 60-minute default it is ~38: the
  level-4 crossing at ≈29.13 game-hours is day-length independent (thirst accumulation carries
  `getDeltaMinutesPerDay()`), but the health term does not, so 100 health takes 8.4 game-hours to
  drain at 11.88/game-hour instead of 5.6 at 17.82 ([body-stats.md](body-stats.md)
  § Discrepancies row 6). Run 2 therefore resets both stats to 0 after every sample, and the
  sampler ends the run on the first dead sample.

**The pin is a control, not a thumb on the scale.** `updateWeight` reads calories,
carbohydrates and lipids only, and `updateCalories`' branches are posture, weight and the
thermoregulator — neither method has a hunger or thirst term ([body-stats.md](body-stats.md)
§ Passive burn). And the unpinned run fits the same model as the pinned one: run 1's 34 alive
game-hours give **+1.045 kg measured against +1.057 predicted** (residual −0.012, tolerance
0.159) at an idle burn of −1 399.7 kcal/game-day, against run 2's −1 408.1 over three full days.

## Macro effects — the complete list (vanilla)

*Evidence: **C** — `Nutrition.updateWeight`, `IsoGameCharacter.getRecoveryMod`,
`canAddFitnessXp`.*

- **Calories**: the only driver of weight (above).
- **Carbs / lipids**: weight-gain *rate multipliers* only (thresholds above).
- **Proteins**: never touch weight, and **have no reachable effect in vanilla at
  all**. `IsoGameCharacter.getRecoveryMod` (endurance/muscle recovery) is base
  0.7→1.6 by Fitness × trait mods, and then applies **lipids < −1000 → ×0.5,
  < −1500 → ×0.2, proteins identically** (`getRecoveryMod @187–@236 L4663–L4667`,
  C) — but those two branches are **dead code**: `Nutrition.setLipids` and
  `setProteins` clamp the stores at **−500** (`@1/@12`, C, measured exactly in run
  `exp01-20260910-003929`, M), so neither threshold can ever be crossed. Corrected
  2026-09-10 by slice 03; the *trait* multipliers in the same method (Obese ×0.4,
  Overweight ×0.7, Very Underweight ×0.7, Emaciated ×0.3, `@111–@186 L4649–L4659`)
  are live — see [body-stats.md](body-stats.md) § Every effect of the weight
  traits.
- Fitness/Strength XP gating (`canAddFitnessXp`) is weight-trait based
  (Emaciated/Obese/Very Underweight block at Fitness ≥6, Overweight at ≥9, and
  plain Underweight **never** — `characterHaveWeightTrouble` tests
  `VERY_UNDERWEIGHT` twice and `UNDERWEIGHT` never) — NOT protein.

**Design-relevant emptiness:** protein surplus, carb store as energy, and any
notion of diet *quality* are dead space in vanilla — prime territory for the
mod, and why parallel nutrient stats have no vanilla collision.

## Open questions

- `Nutrition.caloriesMax` / `caloriesMin` (`updateCalories @319–@358 L121–L125`)
  are maintained but no reader was found — possibly UI/debug only.

Resolved in slice 01: the store clamps (above) and the sandbox options that touch
nutrition — exactly one, `Nutrition`, and it gates only `Nutrition.update()`
(drain, calorie burn, weight), never intake
([eating-pipeline.md](eating-pipeline.md) § The sandbox `Nutrition` option).

Resolved in slice 03, all in [body-stats.md](body-stats.md):

- **`updateCalories` — the whole passive burn model.** Five branches with their
  constants and per-game-day numbers; the thermoregulator `energyMultiplier` and
  the swipe/climb/timed-action modifier reach the **asleep and idle branches
  only**; the idle rate and the `weight/80` term are measured (M,
  `exp03-20260910-045523`). Movement and sleep branches remain C.
- **The sandbox picture for the body side.** `Nutrition` (above) plus exactly one
  more, `StatsDecrease`, which multiplies hunger/thirst/fatigue and **never**
  calories — its 1→2.0 … 5→0.65 mapping is now measured, not inferred.
- **`characterHaveWeightTrouble` exact composition** — and it has a duplicated
  test, so plain Underweight never counts as weight trouble.
- **Nutritionist trait: display-only, confirmed** — `Food.DoTooltip` is the only
  reader in the jar.

## MP behavior

Corrected 2026-09-10 by slice 01; the previous text had the direction reversed.

- **The server computes; the client mirrors.** On a multiplayer client
  `Nutrition.update()` skips the macro drain and `updateCalories()` entirely
  (`Nutrition.update @42 L75`, C) — only the server runs them. The client does
  reach `updateWeight()` (`@106 L81`, C), but **computes the weight delta and
  discards it**: a `GameClient.client` early-out at `updateWeight @317–@320 L198`
  sits *before* `setWeight` (`@323 L199`), before the trait counter and before
  `applyTraitFromWeight` (`@349 L202`). So client-side weight comes only from
  `Nutrition.load` in the packets, and **the weight band traits never apply
  client-side**. Corrected 2026-09-10 by slice 03 and measured: a client
  `setWeight(105)` read back 105 with `hasTrait(Obese)` false, then reverted to the
  server's 80 within 3 s, `Obese` still false (M, `exp03-20260910-045523` —
  [`testing/artifacts/exp03-20260910-045523/body.json`](../../testing/artifacts/exp03-20260910-045523/body.json)).
  Hunger, thirst, endurance and fatigue are server-only in the same way — see
  [body-stats.md](body-stats.md) § MP behaviour.
- The server pushes the whole `Nutrition` object (calories, proteins, lipids,
  carbohydrates, weight) at eat time via `EatFoodPacket` and again every second
  via `PlayerStatsPacket` on a 1000 ms `UpdateLimit` (C).
- **Measured** (run `exp01-20260910-000351`, M): a client-side
  `setCalories(3000)` never reached the server and was back to the server's value
  within 3 s; a server-side `setCalories(2500)` reached the client within 3 s.
  `CharacterStat.HUNGER`/`THIRST` behave the same way (run
  `exp01-20260910-003929`, M). A modded nutrient store must therefore be mutated
  server-side and pushed, or live in player modData with an explicit transmit.
- Nutrition values persist via character save (`Nutrition.save/load @0 L209/L217`,
  C). What the server validates on an incoming write is still unmeasured — the
  probes above show client writes are simply overwritten by the next push rather
  than rejected, which is a different mechanism from validation.

## Sources

- Jar (pzdis, 42.20.4 `b0bbce05d5`): `zombie/characters/BodyDamage/Nutrition`
  (`update`, `updateCalories`, `updateWeight`, `applyTraitFromWeight`, the four
  clamping setters, `save`/`load`); `zombie/characters/IsoGameCharacter.getRecoveryMod`;
  `canAddFitnessXp`.
- Code map: `docs/superpowers/plans/01-notes.md` Q5 (re-read of `Nutrition.update`
  and `updateWeight` on this jar).
- Measured: run `exp01-20260910-000351`
  ([`testing/artifacts/exp01-20260910-000351/eat-smoke.json`](../../testing/artifacts/exp01-20260910-000351/eat-smoke.json))
  and run `exp01-20260910-003929`
  ([`testing/artifacts/exp01-20260910-003929/eat-matrix.json`](../../testing/artifacts/exp01-20260910-003929/eat-matrix.json)).
  The full run directories with their logs stay local under `testing/runs/<run id>/`, which
  is gitignored.
- Measured (slice 03): run `exp03-20260910-045523`
  ([`testing/artifacts/exp03-20260910-045523/body.json`](../../testing/artifacts/exp03-20260910-045523/body.json))
  — the weight-band edges, the client weight write, and the burn/decay rates.
- Measured (slice 04, § Verified on server): the three 3-game-day server runs
  `scenario-20260910-052624`
  ([`scenario-nutrition_3day_gain.json`](../../testing/artifacts/scenario-20260910-052624/scenario-nutrition_3day_gain.json)),
  `scenario-20260910-054012`
  ([`scenario-nutrition_3day_gain.json`](../../testing/artifacts/scenario-20260910-054012/scenario-nutrition_3day_gain.json))
  and `scenario-20260910-055029`
  ([`scenario-nutrition_3day_fast.json`](../../testing/artifacts/scenario-20260910-055029/scenario-nutrition_3day_fast.json)).
  Scenario: `testing/PZTestKit/PZTestKit/42/media/lua/server/scenarios/PZTestKit_Scenario_Nutrition.lua`;
  model check and tolerance: `testing/pzt/scenarios_nutrition.py`; runner:
  `testing/pzt/scenario.py` (`python testing/pzt scenario <name>`), documented in
  [`docs/testing/README.md`](../testing/README.md).
- Body side (passive burn, hunger/thirst, moodles, weight-band effects):
  [body-stats.md](body-stats.md).
- Intake side and the full modifier table: [eating-pipeline.md](eating-pipeline.md).
- Origin: pz-b42 `findings/nutrition-weight.md` (2026-09-04).
