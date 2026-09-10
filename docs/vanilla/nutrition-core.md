# Nutrition core — weight, calories, macros

**Verified against: 42.20.4 (`b0bbce05d5`)** — `zombie.characters.BodyDamage.Nutrition`
(pzdis), 2026-09-04; re-read unchanged and partly measured 2026-09-10 (slice 01).
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
                                                        # store clamps at 3700 → ≤1.04 kg/day
    if carbs > 700 OR lipids > 700:   rate ×3           # ≤3.12 kg/game-day after that clamp
    elif carbs > 400 OR lipids > 400: rate ×2
elif calories < loseThreshold:
    rate = 8.5e-6 × min(1, |calories|/2500)             # 0.73 kg/day at −2500, but the store
                                                        # clamps at −2200 → ≤0.65 kg/game-day
```

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
3-day scenario.

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
- Body side (passive burn, hunger/thirst, moodles, weight-band effects):
  [body-stats.md](body-stats.md).
- Intake side and the full modifier table: [eating-pipeline.md](eating-pipeline.md).
- Origin: pz-b42 `findings/nutrition-weight.md` (2026-09-04).
