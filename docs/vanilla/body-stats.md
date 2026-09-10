# Body stats — passive burn, hunger, thirst, moodles, weight bands

**Verified against: 42.20.4 (`b0bbce05d5`)** · 2026-09-10 · slice 03 (P1b).
Evidence grades: **C** read from bytecode/Lua/scripts, **M** measured on the live
dedicated server (run id + artifact path given), **W** wiki mirror (secondary).
`C (arith.)` = arithmetic on C constants, shown inline.
The intake side — how food *fills* these stores — is
[eating-pipeline.md](eating-pipeline.md); the item itself is
[food-item-model.md](food-item-model.md); the calories→weight model is
[nutrition-core.md](nutrition-core.md). This document covers what the body does with
the stores between meals.

## Summary

1. **Calorie burn and hunger are two unrelated clocks.** `Nutrition.updateCalories`
   drains a kcal store at `0.016 × (weight/80)` per game-second at rest (1 382 kcal per
   game-day at 80 kg); `IsoGameCharacter.updateStats_Awake` raises a separate `[0,1]`
   hunger need at `9.6e-6 × (1 − hunger)` per game-second. Neither reads the other. Both
   were measured to within 0.5 % of the coded constants.
2. **Only the resting branches are modifiable.** The thermoregulator's cold-weather
   `energyMultiplier` and the 8.0 swipe/climb and timed-action `caloriesModifier`
   multiply the asleep and idle branches only — the three moving branches overwrite the
   modifier with a fixed 1.0 / 1.3 / 0.6 and never read `energy`. Attacking while
   standing still burns 8× resting; attacking while running burns the plain running rate.
3. **Hunger is a first-order approach, thirst is linear.** Appetite is `1 − hunger`, so
   hunger rises `1 − e^(−kt)` with a 28.9 game-hour time constant; thirst has no damping
   term and fills in 34.7 game-hours. The sandbox `StatsDecrease` option (1→×2.0 …
   5→×0.65) and four traits scale them; **nothing scales the calorie burn but weight**.
4. **The moodles' entire mechanical footprint is four `BodyDamage` rows** — carry
   capacity, the health-regeneration tier, the zeroing of the sleeping health addition at
   HUNGRY 4 ∨ THIRST 4, and a health loss at HUNGRY level 4. There is
   no weight moodle, and `FOOD_EATEN` (fed from *hunger change*, never from calories)
   freezes the hunger rate outright while it is up.
5. **In MP every one of these stats is server-owned.** Hunger, thirst, endurance and the
   whole `Nutrition` object tick only on the server and arrive by a 1 Hz full-snapshot
   `PlayerStatsPacket`; a client runs `updateWeight()` and **throws the result away**
   (a `GameClient.client` skip sits before `setWeight`), so weight traits never apply
   client-side. Measured: a client weight write of 105 reverted to 80 with `Obese` never
   set.

---

## Model

### Time unit

Every rate here is **per game-world second**; a game day is 86 400 of them. Both idioms
in the code (`getGameWorldSecondsSinceLastUpdate()` in `Nutrition`,
`getMultiplier() × getDeltaMinutesPerDay()` in `IsoGameCharacter`) reduce to the same
quantity because `GameTime.multiplierBias == 1.0`
(`GameTime.<init> @34–@35 L83`) — the identity and its derivation are in
[`docs/superpowers/plans/03-notes.md`](../superpowers/plans/03-notes.md) Q0 (C). The run
below fitted every rate against `worldAge` read from the same snapshot, so `settimespeed`
cancels and the accelerated windows are directly comparable with the baseline (M).

### Passive burn — `Nutrition.updateCalories`

`zombie/characters/BodyDamage/Nutrition.updateCalories()V`, `L88–L127`. Five mutually
exclusive branches, tested in this order; `w = getWeight()/80`, `dt` = game-seconds since
the last update:

```java
float mod = 1.0f;                                           // @0   L88
if (!parent.getCharacterActions().isEmpty())
    mod = characterActions.get(0).caloriesModifier;          // @15  L90
if (isCurrentState(SwipeStatePlayer | ClimbOverFenceState | ClimbThroughWindowState))
    mod = 8.0f;                                              // @72  L94
float energy = 1.0f;
if (bodyDamage != null && bodyDamage.getThermoregulator() != null)
    energy = thermoregulator.getEnergyMultiplier();          // @100 L100

if      (IsRunning()   && isPlayerMoving()) { mod = 1.0f; cal -= 0.13f  * mod * w * dt; }  // @145 L107-L108
else if (isSprinting() && isPlayerMoving()) { mod = 1.3f; cal -= 0.13f  * mod * w * dt; }  // @192 L110-L111
else if (isPlayerMoving())                  { mod = 0.6f; cal -= 0.13f  * mod * w * dt; }  // @230 L113-L114
else if (isAsleep())                        {            cal -= 0.003f * mod * energy * w * dt; } // @268 L116
else                                        {            cal -= 0.016f * mod * energy * w * dt; } // @295 L118
```

| Branch | Rate /game-s at w = 80 | kcal / game-day | external `mod` reaches it? | `energy` reaches it? | Ev |
|---|---|---|---|---|---|
| asleep | 0.003 | 259.2 | yes | yes | C `updateCalories @268–@289 L116`; per-day C (arith.) `× 86 400` |
| **idle (at rest)** | **0.016** | **1 382.4** | yes | yes | C `@295–@316 L118`; **M** ratio 1.0049, r² 1.000000, n = 233 over 1.420 game-h — `exp03-20260910-045523`, [`body.json`](../../testing/artifacts/exp03-20260910-045523/body.json) |
| walking | 0.13 × 0.6 = 0.078 | 6 739.2 | **no** — overwritten to 0.6 | **no** | C `@230–@251 L113-L114`; not measured (see Open questions) |
| running | 0.13 × 1.0 = 0.13 | 11 232 | **no** — overwritten to 1.0 | **no** | C `@145–@165 L107-L108`; not measured |
| sprinting | 0.13 × 1.3 = 0.169 | 14 601.6 | **no** — overwritten to 1.3 | **no** | C `@192–@213 L110-L111`; not measured |
| idle + swipe / climb fence / climb window | 0.016 × 8 = 0.128 | 11 059.2 | `mod = 8.0` | yes | C `@33–@74 L93-L94`; not measured |
| idle + `ISBuildAction` (`caloriesModifier` 8) | 0.128 | 11 059.2 | yes | yes | C `@2–@32 L89-L90`; `ISBuildAction.lua:274`; not measured |
| idle + `ISReadABook` (`caloriesModifier` 0.5) | 0.008 | 691.2 | yes | yes | C; `ISReadABook.lua:510`; not measured |
| idle at weight 100 (`w = 1.25`) | 0.020 | 1 728 | yes | yes | C `@115–@124 L104`; **M** ×1.2496 vs w80 — `exp03-20260910-045523`, [`body.json`](../../testing/artifacts/exp03-20260910-045523/body.json) |
| idle at weight 120 / 60 | 0.024 / 0.012 | 2 073.6 / 1 036.8 | yes | yes | C; **M** ×1.4991 / ×0.7503 — same run/artifact |

**Two structural facts the modifier table above encodes.** (a) `energy` (local slot 2) is
loaded at `@277` (asleep) and `@304` (idle) and **nowhere else**, so cold raises resting
burn and does nothing to running burn. (b) all three moving branches *overwrite* `mod`
before using it (`@145 L107`, `@192 L110`, `@230 L113`), so the 8.0 swipe/climb constant
and every timed action's `caloriesModifier` are rest-only in practice. Ev C
([03-notes.md](../superpowers/plans/03-notes.md) Q1).

`caloriesModifier` defaults to 1 (`ISBaseTimedAction.lua:181`) and takes 30 assignments in
`media/lua`; the distinct values are **0.5** (reading, researching, resting), **2**
(dismantling), **3** (`ISFitnessAction`), **4** (building stages, painting, wallpapering,
harvesting, shovelling, fixing), **5** (plowing, cleaning blood/graffiti, filling graves)
and **8** (`ISBuildAction`, plastering, barricading, chopping trees, breaking glass). Ev C.

The thermoregulator term is `Thermoregulator.energyMultiplier`, rebuilt every tick by
`updateBodyMultipliers()V @0–@198 L1095–L1118`:

```
energyMultiplier = 1.0
if (primTotal < 0) energyMultiplier += 0.05 · primTotal²      // @36  L1102   cold, primary
if (secTotal  < 0) energyMultiplier += 0.10 · secTotal²       // @126 L1112   cold, secondary
```

It is **≥ 1.0 always and raised only by cold**; heat instead raises `fluidsMultiplier`
(which is `getThirstMultiplier()`, below) and `fatigueMultiplier`. Ev C.

> **Tentative reading, n = 1.** Idle calorie burn came out **1.0045–1.0055 ×** the coded
> 0.016 in **ten of the eleven** idle windows of the run, while the macro drains —
> computed in the *same* method against the same `dt` — sat at ~1.000 in 9 of the 11
> windows. In the eleventh (`rows.r9_traits.windows[2]`, High Thirst) every stat reads
> ~0.995 *together* — calories 0.9999 against all six needs/macros at 0.9948 — i.e. that
> whole window is offset, not the calorie term alone. The only term in
> the code that separates those two numbers is `energy`, so this fixture's character
> plausibly sat at `energyMultiplier ≈ 1.005` (very slightly cold). Nothing controlled the
> temperature and the run has one fixture, so this is **not** a constant: a 0.5 %
> systematic between the two `dt` routes is not excluded. M (as an observation)
> `exp03-20260910-045523`, [`body.json`](../../testing/artifacts/exp03-20260910-045523/body.json);
> the interpretation is C+inference. `primTotal`/`secTotal` ranges remain unknown (Open
> questions).

**Store clamps still bind.** Calories clamp to `[−2200, 3700]`
(`Nutrition.setCalories @1 L321, @12 L324`, C; measured exactly in run
`exp01-20260910-003929`, M — [nutrition-core.md](nutrition-core.md) § Store clamps). At
idle a starved character reaches the −2200 floor and the burn stops mattering; sustained
running (11 232 kcal/game-day) crosses the whole 5 900 kcal store range in ≈ 12.6
game-hours (C, arith.).

**Guards.** `Nutrition.update @0 L65-L66` sandbox `Nutrition`; `@13/@31 L68–L72` dead /
god-mode; `@42 L75` `!GameClient.client` gates the macro drain **and** `updateCalories()`;
`IsoPlayer.updateInternal2 @392–@402 L2306-L2307` is the only caller, itself gated by
`SystemDisabler.doCharacterStats`. Ev C.

### Hunger and thirst

There is **no `getHunger()` on `Stats` in B42**: the route is
`getStats():get(CharacterStat.HUNGER / .THIRST)`, both `[0,1]` with default 0
(`CharacterStat.<clinit> @91–@99`, `@231–@239`). Ev: the route every live snapshot
answered with (M, run below); `Stats`' 34-method list is what rules the old getter out
(C) — the harness tries the enum route first and short-circuits, so its `getHunger()` /
`.hunger` fallbacks were never exercised
([eating-pipeline.md](eating-pipeline.md) § Open questions, `docs/progress.md`).

Dispatch: `IsoGameCharacter.updateInternal @1548–@1557 L9229-L9230` →
`calculateStats() L10196–L10221` → `updateThirst()`, `updateStats_WakeState()` (which
picks `updateStats_Awake` or `updateStats_Sleeping`), plus endurance, tripping, stress,
morale and fitness. `LuaHookManager.TriggerHook("CalculateStats", character)` returning
true skips **all of them** for that tick (`@49–@59 L10204-L10205`) — the cleanest vanilla
interception point for a nutrition mod. Ev C.

```java
// hunger — IsoGameCharacter.updateStats_Awake()V  L10242–L10285
appetite   = getAppetiteMultiplier();                       // (1 − HUNGER) × traits   @171 L10266
exercising = (IsRunning() && isPlayerMoving()) || isCurrentState(SwipeStatePlayer);  // @177 L10267
rate = exercising ? (FOOD_EATEN == 0 ? HungerIncreaseWhenExercise/3 : HungerIncreaseWhenExercise)
                  : (FOOD_EATEN == 0 ? HungerIncrease              : HungerIncreaseWhenWellFed);
stats.add(HUNGER, rate × statsDecreaseMultiplier × appetite × dt × getHungerMultiplier());
        // the well-fed branch (@391 L10278) drops the appetite term entirely — moot, its constant is 0

// thirst — IsoGameCharacter.updateThirst()V  L10367–L10385
t = 1.0 × (HIGH_THIRST ? 2.0 : 1) × (LOW_THIRST ? 0.5 : 1);                    // @2/@19 L10369-L10374
asleep : stats.add(THIRST, ThirstSleepingIncrease × statsDecrease × dt × t);   // @81  L10379
awake  : stats.add(THIRST, ThirstIncrease × statsDecrease × getRunningThirstReduction()
                           × dt × t × getThirstMultiplier());                  // @125 L10381
```

| Constant | Value /game-s | Where it applies | Source | Ev |
|---|---|---|---|---|
| `HungerIncrease` | **9.6e-6** | awake, `FOOD_EATEN == 0`, not exercising | `defines.lua:14` (`0.0000032 * 3`); `updateStats_Awake @348 L10276` | C; **M** ratio 1.0000 (measured 7.4912e-6 vs predicted 7.4916e-6 at H̄ = 0.2196, r² 0.99996) — `exp03-20260910-045523`, [`body.json`](../../testing/artifacts/exp03-20260910-045523/body.json) |
| `HungerIncreaseWhenExercise / 3` | **6.4e-6** | exercising **and** `FOOD_EATEN == 0` — *below* the idle rate | `defines.lua:16`; `@231–@237 L10269` | C |
| `HungerIncreaseWhenExercise` | **1.92e-5** | exercising with `FOOD_EATEN ≥ 1` — 2× idle | `defines.lua:16`; `@285 L10271` | C |
| `HungerIncreaseWhileAsleep` | **1.0e-6** | asleep, `FOOD_EATEN == 0` | `defines.lua:17`; `IsoPlayer.updateStats_Sleeping @448 L3359` | C |
| `HungerIncreaseWhenWellFed` | **0** | not exercising, `FOOD_EATEN ≥ 1` — hunger freezes | `defines.lua:15`; `@398 L10278`, `@497 L3361` | C; **M** bit-exactly flat (below) — same run/artifact |
| appetite factor | `1 − stats.get(HUNGER)` | multiplies every hunger branch but the well-fed one | `getAppetiteMultiplier @0–@12 L10322` | C; **M** — the fits track `(1 − H̄)` to 4 s.f. in all 11 windows, same run/artifact |
| `getHungerMultiplier()` | hard **1.0** | dead hook — there is **no** thermoregulator term on hunger | `IsoGameCharacter.getHungerMultiplier @0–@1 L14955` | C |
| `ThirstIncrease` | **8.0e-6** | awake; linear, no damping term | `defines.lua:9` (`0.0000040 * 2`); `updateThirst @132 L10381` | C; **M** ratio 1.0000 (7.99999e-6, r² 1.000000) — same run/artifact |
| `ThirstSleepingIncrease` | **1.0e-6** | asleep; neither the running nor the heat term applies | `defines.lua:10`; `@88 L10379` | C |
| `getThirstMultiplier()` | `Thermoregulator.getFluidsMultiplier()` = `1 + 0.25·primTotal² + 3.75·secTotal²`, **hot side only** | awake branch only | `@0–@29 L14948–L14951`; `updateBodyMultipliers L1105/L1115` | C |
| `getRunningThirstReduction()` | ×**1.2** while running (it *raises* thirst) | gated on `this == IsoPlayer.getInstance()` — on a dedicated server probably never | `@0–@21 L10388–L10391` | C |
| `ThirstLevelToAutoDrink` | 0.1 | `autoDrink` needs `THIRST > 0.1` | `defines.lua:11`; `autoDrink @99–@116 L11743` | C |
| `ThirstLevelReductionOnAutoDrink` | 0.1 | amount removed per auto-drink | `defines.lua:12` | C |

`autoDrink()` is server-only (`@0–@6 L11727-L11728` returns on `GameClient.client`),
additionally needs `player.getAutoDrink()` and `Core.getOptionAutoDrink()`, is skipped
while asleep / grappling / knocked down / falling / aiming / climbing
(`@45–@87 L11736-L11737`), and fires the Lua hook `"AutoDrink"` (`@88–@98 L11739-L11740`).
Ev C.

#### Multipliers on hunger and thirst

| Multiplier | Hunger | Thirst | Calories | Source | Ev |
|---|---|---|---|---|---|
| sandbox `StatsDecrease` = 1 | ×2.0 | ×2.0 | — | `SandboxOptions.getStatsDecreaseMultiplier @0–@65 L545–L550` | C; **M** hunger 0.9996 / thirst 1.0000 vs predicted, calories ratio 1.0054 (unchanged) — `exp03-20260910-045523`, [`body.json`](../../testing/artifacts/exp03-20260910-045523/body.json) |
| `StatsDecrease` = 2 | ×1.6 | ×1.6 | — | same | C; **M** multiplier read directly from `SandboxOptions:getStatsDecreaseMultiplier()` — same run/artifact |
| `StatsDecrease` = 3 (**default**) | ×1.0 | ×1.0 | — | `<init> @990–@1006 L127` `newEnumOption("StatsDecrease", 5, 3)` | C; **M** — same run/artifact |
| `StatsDecrease` = 4 | ×0.8 | ×0.8 | — | same | C; **M** — same run/artifact |
| `StatsDecrease` = 5 | ×0.65 | ×0.65 | — | same | C; **M** hunger 1.0002 / thirst 1.0000, calories 1.0050 (unchanged) — same run/artifact |
| trait Hearty Appetite | ×1.5 | — | — | `getAppetiteMultiplier @13–@31 L10323-L10324` | C; **M** 0.9997 — same run/artifact |
| trait Light Eater | ×0.75 | — | — | `@32–@50 L10326-L10327` | C; **M** 1.0001 — same run/artifact |
| trait High Thirst | — | ×2.0 (both branches) | — | `updateThirst @2–@18 L10369-L10370` | C; **M** 0.9948 — same run/artifact |
| trait Low Thirst | — | ×0.5 (both branches) | — | `@19–@37 L10373-L10374` | C; **M** 1.0000 — same run/artifact |
| running | — | ×1.2, local player only | ×8.125 vs idle | `getRunningThirstReduction`; `updateCalories` branch | C |
| cold (`energyMultiplier`) | — | — | ×`1 + 0.05p² + 0.10s²`, **rest only** | `updateBodyMultipliers @36/@126` | C |
| heat (`fluidsMultiplier`) | — | ×`1 + 0.25p² + 3.75s²` | — | `@77/@168 L1105/L1115` | C |
| body weight | — | — | ×`weight/80` | `updateCalories @115 L104` | C; **M** hunger and thirst flat (0.9999–1.0000) across 60–120 kg while calories tracked ×0.75/×1.25/×1.50 — same run/artifact |

**`StatsDecrease` is the only sandbox option on hunger or thirst.** A scan of
`SandboxOptions`' method list for `hunger|thirst|stat|nutrition|food|multiplier` returns
only `getStatsDecreaseMultiplier`, `getEnduranceRegenMultiplier` and two loot multipliers.
Ev C. Its key→value mapping was inferred from the bytecode and is now read directly off
the live server, so it is **M**, not inference. The one nutrition-side option,
`Nutrition`, gates `Nutrition.update()` (drain, burn, weight) and nothing else — settled
in slice 01 ([eating-pipeline.md](eating-pipeline.md) § The sandbox `Nutrition` option).

#### How fast they actually fill

Hunger is **not linear**: with `k = HungerIncrease × statsDecrease × appetiteTrait`,
`dH/dt = k(1 − H)`, so `H(t) = 1 − e^(−kt)` and `1/k = 104 167 game-s = 28.94 game-h` at
default settings. Thirst has no `(1 − T)` term and is linear. All rows below are C (arith.)
on the C constants, at `StatsDecrease = 3`, awake, idle, `FOOD_EATEN` 0:

| Milestone | Hunger, plain | Hearty Appetite ×1.5 | Light Eater ×0.75 | Thirst, plain | High Thirst ×2 | Low Thirst ×0.5 | Ev |
|---|---|---|---|---|---|---|---|
| moodle level 1 | 4.70 game-h (H 0.15) | 3.13 | 6.27 | 4.17 game-h (T 0.12) | 2.08 | 8.33 | C (arith.) |
| moodle level 2 | 8.32 game-h (0.25) | 5.55 | 11.10 | 8.68 game-h (0.25) | 4.34 | 17.36 | C (arith.) |
| moodle level 3 | 17.30 game-h (0.45) | 11.53 | 23.06 | 24.31 game-h (0.70) | 12.15 | 48.61 | C (arith.) |
| moodle level 4 | 34.84 game-h (0.70) | 23.22 | 46.45 | 29.17 game-h (0.84) | 14.58 | 58.33 | C (arith.) |
| maximum (1.0) | asymptotic | asymptotic | asymptotic | 34.72 game-h | 17.36 | 69.44 | C (arith.) |
| after 1 game-day | 0.5637 | 0.7118 | 0.4632 | 0.6912 | 1.0 (clamped) | 0.3456 | C (arith.) |

Other regimes, per game-second: asleep hunger 1.0e-6 (0.0864 · (1−H) per game-day),
asleep thirst 1.0e-6 (0.0864/game-day); exercising with no `FOOD_EATEN` **6.4e-6**;
exercising with `FOOD_EATEN ≥ 1` **1.92e-5**; idle or asleep with `FOOD_EATEN ≥ 1`
**0**. Ev C.

**Two vanilla oddities worth a design note** (Ev C). (a) Exercising on an empty stomach
makes you hungry *more slowly* than standing still (6.4e-6 vs 9.6e-6): the `/3.0` at
`@234 L10269` lands on the "no `FOOD_EATEN` moodle" branch, i.e. exactly when you are not
full. (b) While `FOOD_EATEN` is up and you are not exercising, hunger does not rise at
all and the appetite factor is dropped from the expression entirely.

### Hunger versus calories

They are **two independent stores with no direct coupling in either direction**. Ev C
([03-notes.md](../superpowers/plans/03-notes.md) Q3).

| Direction | Verdict | Evidence | Ev |
|---|---|---|---|
| hunger → calorie burn | **none** | `updateCalories @0–@318 L88–L118` reads actions, three AI states, `Thermoregulator`, `getWeight()` and `GameTime` — never `Stats` | C |
| calories → hunger | **none** | `updateStats_Awake @171–@433` and `updateStats_Sleeping @423–@543` read appetite, the `FOOD_EATEN` moodle, sandbox, `GameTime` and two traits — never `Nutrition` | C |
| hunger → hunger | **yes, self-damping** | `getAppetiteMultiplier` = `1 − stats.get(HUNGER)`; the only stat that feeds its own rate | C; **M** — the `(1 − H̄)` factor is required to fit every measured window, `exp03-20260910-045523`, [`body.json`](../../testing/artifacts/exp03-20260910-045523/body.json) |
| calories → weight → calories | **yes** | `updateCalories @115 L104` scales by `getWeight()/80` and `updateWeight` moves weight from calories — the one genuine feedback loop | C; **M** ×1.2496 / ×1.4991 / ×0.7503 at 100 / 120 / 60 kg — same run/artifact |
| the indirect link | `FOOD_EATEN` gates the hunger rate, and its timer is filled from `abs(getHungerChange()) × f × 13000` — from **hunger change, not calories** | `JustAteFood @454–@538 L650–L660`; `getHealthFromFoodTimeByHunger @0 L754` returns a flat 13000 | C |

**Design consequence.** A 0-calorie, high-hunger item suppresses hunger growth exactly as
well as a 900-kcal meal, and a mod that adds nutrient stores can drive them from calories,
from hunger or from neither without colliding with any vanilla coupling.

### Moodles

Moodles are **not script-registered** in 42.20.4: `find media/scripts -iname "*moodle*"`
returns nothing. `MoodleType` is a registry of 27 Java statics
(`MoodleType.<clinit> @0–@205 L7–L32`) and the thresholds live in
`MoodleStat.<clinit> @0–@369 L9–L29`. The Lua-visible names are the static field names —
**`MoodleType.HUNGRY`**, **`MoodleType.THIRST`** (not `THIRSTY`) and
**`MoodleType.FOOD_EATEN`**; the display strings are `Hungry`, `Thirst`, `FoodEaten`.
Levels are `Moodle$MoodleLevel` ordinals 0–4 (Min / Low / Moderate / High / Max) and
`Moodles.getMoodleLevel(type)` returns that int (`@0–@16 L40`). Ev C, with the enum names
confirmed on the live server (M).

**There is no weight moodle.** Nothing weight-related is registered; `HeavyLoad` is
inventory encumbrance (thresholds 1.0 / 1.25 / 1.5 / 1.75 on the carry-weight *ratio*).
Ev C.

`Moodle.Update()Z` evaluates thresholds with plain `>` in ascending order, last match
wins: HUNGRY at `@474–@580 L163–L175` (gated on `getBodyDamage().getHealth() != 0`),
THIRST at `@1145–@1270 L266–L275` (no health gate). Ev C.

| Moodle | Stat | lvl 1 `>` | lvl 2 `>` | lvl 3 `>` | lvl 4 `>` | Cite | Ev |
|---|---|---|---|---|---|---|---|
| `HUNGRY` | `HUNGER` `[0,1]` | **0.15** | **0.25** | **0.45** | **0.70** | `MoodleStat.<clinit> @64–@79 L13` | C; **M** all five levels read back correctly from probes at 0.10 / 0.16 / 0.26 / 0.46 / 0.71 — `exp03-20260910-045523`, [`body.json`](../../testing/artifacts/exp03-20260910-045523/body.json) |
| `THIRST` | `THIRST` `[0,1]` | **0.12** | **0.25** | **0.70** | **0.84** | `@172–@187 L19` | C; **M** all five levels from probes at 0.10 / 0.13 / 0.26 / 0.71 / 0.85 — same run/artifact |
| `ENDURANCE` (inverted, min 0.75) | `ENDURANCE` | 0.5 | 0.25 | 0.10 | 0 | `@10–@25 L10` | C |
| `HEAVY_LOAD` | carry ratio | 1.0 | 1.25 | 1.5 | 1.75 | `@352–@366 L29` | C |
| `FOOD_EATEN` | `BodyDamage.healthFromFoodTimer` | `> 0` | `> 1600` | `> 3200` | `> 4800` | `Moodle.Update @2331–@2454 L437–L447`; `standardHealthFromFoodTime = 1600` at `BodyDamage.<init> @97–@100 L80` | C; **M** a timer of 197 597 read as level 4 — same run/artifact |

`MoodleStat` exposes `get(MoodleType)` plus `setLowestThreshold` and friends, so a mod can
retune every threshold at runtime with no Java patch. Ev C.

#### What each level does

| Consumer | Effect | Cite | Ev |
|---|---|---|---|
| `BodyDamage.UpdateStrength` | **carry capacity**: `n = 0`; HUNGRY lvl 2 → `n += 1`, lvl 3 → `+2`, lvl 4 → `+2`; THIRST identically; SICK 2/3/4 → `+1/+2/+3`; BLEEDING/INJURED likewise. Then `setMaxWeight((int)(maxWeightBase × weightMod) − n)`, floored at 0 | `@2–@61 L2062–L2069` (hunger), `@62–@121 L2071–L2078` (thirst), `@302–@383 L2113–L2121` | C; **M** `getMaxWeight()` = 12 / 12 / 11 / 10 / 10 across levels 0–4, on both moodles independently — `exp03-20260910-045523`, [`body.json`](../../testing/artifacts/exp03-20260910-045523/body.json) |
| `BodyDamage.Update` | **health-regeneration tier**: `n = 0`; `HUNGRY == 2 ∨ SICK == 2 ∨ THIRST == 2 → n = 1`; `== 3 → n = 2`; `HUNGRY == 4 ∨ THIRST == 4 → n = 3` (SICK 4 is **not** in this one); `asleep → n = −1`. Additions `0.002 / 0.0013 / 0.0008 / 0.0` × `GameTime.getMultiplier()` | `@591–@838 L2274–L2312`; constants `<init> @61–@81 L74–L77` | C (the tier↔constant mapping is inferred from the branch order; the wiki's Thirsty page independently quotes −35 / −60 / −100 %, which is exactly this set — W corroboration, [thirsty.md](../../references/wiki-mirrors/thirsty.md)) |
| `BodyDamage.Update` | asleep: if `HUNGRY == 4 ∨ THIRST == 4`, the sleeping health addition (0.02) is **zeroed** | `@839–@924 L2316–L2323` | C |
| `BodyDamage.Update` | **health loss** at `HUNGRY == 4`: `healthReductionFromSevereBadMoodles / 50` = `0.0165/50` = **3.3e-4** per multiplier unit, added to the reduction total. THIRST has no such branch | `@1134–@1172 L2356–L2358`; `<init> @91–@93 L79` | C |
| `BodyDamage.Update` | `FOOD_EATEN > 0` speeds **poison decay** by `1.5e-4 × level` on top of `poisonLevelDecrease` | `@1028–@1090 L2349–L2353` | C |
| `updateStats_Awake` / `updateStats_Sleeping` | `FOOD_EATEN` level gates the **hunger rate** (above) | `@211/@328 L10268/L10275`, `@423 L3357` | C; **M** (the measured table below) `exp03-20260910-045523` ([`body.json`](../../testing/artifacts/exp03-20260910-045523/body.json)) |
| `ISEatFoodAction.lua:14`, `ISDrinkFluidAction.lua:7` | `isValidStart` false at `FOOD_EATEN >= 3` — "can't eat more" | Lua | C |
| `ISInventoryPane.lua:986`, `:989`; `ISInventoryPaneContextMenu.lua:500`, `:2313` | UI gating of eat/drink at `FOOD_EATEN >= 3` | Lua | C |

**Negative result, and it is load-bearing.** A whole-jar scan for `HUNGRY` finds it only
in `ParameterMoodles` (audio), `BodyDamage`, `Moodle`, `MoodleStat`, `Book` (a book
title), the `MoodleType` registry and `MoodleTextureSet`/`MoodlesUI` (display); and
`grep -rn "MoodleType.HUNGRY" media/lua` and `MoodleType.THIRST` return **nothing**. So
the Hungry and Thirsty moodles have **no movement-speed, damage or XP effect at all** —
their entire mechanical footprint is the rows above. Ev C.

#### `FOOD_EATEN` — the gate, measured

| Finding | Numbers | Ev |
|---|---|---|
| Hunger is **bit-exactly** frozen at `FOOD_EATEN` level 4 while idle | 9 consecutive server samples over 1.065 game-h (3 833 game-s) all read `hunger = 0.200000`; the idle rate would have added **+0.0294** | **M** `exp03-20260910-045523`, [`body.json`](../../testing/artifacts/exp03-20260910-045523/body.json) (`rows.r8_food_eaten.raw`, samples 0–8) |
| The gate is on **hunger alone** | in the same 9 samples thirst ran at 7.99989e-6 (ratio 1.0000) and calories at −0.0160771 (ratio 1.0048) | **M** same run/artifact |
| With the gate down the coded rate resumes exactly | next 15 samples over 1.863 game-h: hunger 9.2564e-6 vs predicted 9.2551e-6 (`9.6e-6·(1−H̄)`, H̄ = 0.0359) → ratio **1.0001** | **M** same run/artifact |
| A real eat **resets** the timer rather than adding to a primed one | the queued `ISEatFoodAction` on a `Base.Steak` completed 9 samples into the window and took `healthFromFoodTimer` from **186 096 → 0**, hunger 0.200 → 0.0046, calories +212 | **M** same run/artifact (samples 8→9) |
| The timer decays at a fixed **game-time** rate | **3.000 units per game-world second**, flat across samples 0–8 (per-interval 2.99998 / 2.99999 / 3.00001 / 3.00001 / 3.00002 / 3.00000 / 3.00001 / 2.99998; 11 500.6 units over 3 833.5 game-s). The `1 437 units per real second` in that window is just `3.000 × S` at `settimespeed 30` — the wall-clock figure, not the mechanism | **M** same run/artifact (`rows.r8_food_eaten.raw`, samples 0–8, fitted against `worldAge` from the same snapshot) |
| So the `JustAteFood` cap is about an hour of **game** time | 11 000 / 3.0 ≈ 3 667 game-s = **1.02 game-hours**; one moodle level (1 600) ≈ **8.9 game-minutes**. In wall-clock terms that is ≈7.7 real seconds at `settimespeed 30` and ≈3.8 real minutes at speed 1 on this fixture — the "under 8 real seconds" reading is a property of speed 30, not of the timer | C (arith.) on the row above + **M** same run/artifact |
| Why 3.000 — and what it does *not* depend on | The timer decays `−1 × GameTime.getMultiplier()` per `BodyDamage.Update` tick (`@575–@590 L2273`), i.e. with `getMultiplier()` **but without** the `getDeltaMinutesPerDay()` factor every stat rate in this document carries. Since `gameWorldSeconds = getMultiplier() × getDeltaMinutesPerDay()` and `getDeltaMinutesPerDay() = 30 / minutesPerDay`, the decay is **`minutesPerDay / 30` per game-second**: 3.0 on this fixture's 90-minute day (its clock, `S = 16.0` game-s/real-s = `86 400/(90 · 60)`, agrees), **2.0** on the 60-minute default. It is therefore frame-rate independent, and in *game* time independent of `settimespeed` — `getMultiplier()` itself scales with speed (4.78–4.80 at ×1, 143.5–144.0 at ×30, artifact `mult`), which is exactly what cancels | C ([03-notes.md](../superpowers/plans/03-notes.md) Q0 and the `healthFromFoodTimer` row) + **M** same run/artifact |

The `JustAteFood` fill path itself (`|hungerChange| × f × 13000`, ×2 if cooked, capped at
11 000 — `@454–@538 L650–L660`, C) is **unmeasured**: the real eat above had not raised
the timer within the 6 s allowed before the window, so the gate was supplied by a direct
timer write. What is measured is the gate's behaviour and the timer→level mapping.

### Weight bands and their effects

`Nutrition.applyTraitFromWeight()V L247–L268` removes all five band traits
(`@0–@62 L247–L251`) and re-adds:

| Band | Condition | `applyWeightFromTraits` sets | Cite | Ev |
|---|---|---|---|---|
| Obese | `weight >= 100` — **inclusive** | 105 | `@65–@88 L253-L254`; `@80 L238` | C; **M** weight exactly 100 → `obese`; 105 → `obese` — `exp03-20260910-045523`, [`body.json`](../../testing/artifacts/exp03-20260910-045523/body.json) |
| Overweight | `85 <= weight < 100` | 95 | `@89–@123 L256-L257`; `@60 L235` | C; **M** exactly 85 → `overweight`; 95 → `overweight` — same run/artifact |
| *normal* | `75 < weight < 85` — **open interval** | — | complement of the five | C; **M** 80 carries no band trait — same run/artifact |
| Underweight | `65 < weight <= 75` | 70 | `@124–@158 L259-L260`; `@40 L232` | C; **M** exactly 75 → `underweight`; 70 → `underweight` — same run/artifact |
| Very Underweight | `50 < weight <= 65` | 60 | `@159–@193 L262-L263`; `@20 L229` | C; **M** 55 → `veryUnderweight` — same run/artifact. The **65 edge itself is not measured** (see below) |
| Emaciated | `weight <= 50` — **inclusive** | 50 | `@194–@217 L265-L266`; `@0 L226` | C; **M** 45 → `emaciated` — same run/artifact. The **50 edge itself is not measured** |

This **corrects** the band line previously in [nutrition-core.md](nutrition-core.md)
("Emaciated <50 … Obese >100"): the comparisons are `dcmpl/iflt` at `@72-@73` and
`dcmpg/ifgt` at `@201-@202`, so both ends are inclusive.

> **Why 50 and 65 are C, not M.** Both probes read back **50.000099** and **65.000099**:
> the server had already nudged the weight past the boundary before
> `applyTraitFromWeight` ran, so the comparison never saw the boundary value. The nudge is
> itself the coded mechanism — `updateWeight` gains weight while calories exceed
> `1000 + (w−80)·40`, which is **−200** at w = 50 and **400** at w = 65, both below the
> 500 kcal the probe had primed. At 70 / 75 / 80 / 85 / 95 / 100 / 105 that threshold sits
> above 500, the weight held exactly, and those rows are clean. To close it, prime
> calories below `(w−80)·40 + 1000` for the low weights (e.g. −550 at w = 45–65).
> The artifact's `summary.r12.allBandsMatch: false` is this drift artifact, not
> counter-evidence.

**Refresh cadence.** `applyTraitFromWeight` runs only every **2000** `updateWeight` calls
(`updateWeight @329–@357 L200–L203`, C). Unforced, it did **not** fire within 60 s: with
weight moved 80 → 105 and no forced refresh, 29 polls over 59.8 s all read
`obese = false` at `weight = 105` (M, `exp03-20260910-045523`,
[`body.json`](../../testing/artifacts/exp03-20260910-045523/body.json)). The counter's
phase at the start of the probe is unknown, so 60 s is a **lower bound** on the period,
not a measurement of it — the ≤2000-call figure stays **C**.
`getNutrition():applyTraitFromWeight()` is public, Lua-reachable and applies instantly
(M, same run) — the route every band row above used.

#### `characterHaveWeightTrouble` has a bug

```java
return hasTrait(EMACIATED) || hasTrait(OBESE)
    || hasTrait(VERY_UNDERWEIGHT) || hasTrait(VERY_UNDERWEIGHT)   // @26 and @39 — duplicated
    || hasTrait(OVERWEIGHT);                                       // @52
```

`VERY_UNDERWEIGHT` is tested twice and **`UNDERWEIGHT` is never tested**
(`@0–@70 L271`, C). Consequence: plain Underweight is not "weight trouble", and via
`canAddFitnessXp` it never blocks XP at any Fitness level. This closes the
`characterHaveWeightTrouble` open question in [nutrition-core.md](nutrition-core.md).

`canAddFitnessXp()Z L275–L280` (C): at Fitness **≥ 9** any weight trouble blocks (so
Overweight blocks too); at Fitness **6–8** only `EMACIATED ∨ OBESE ∨ VERY_UNDERWEIGHT`
block; below 6 nothing blocks.

#### Every effect of the weight traits outside `Nutrition`

The trait **scripts** carry no stat modifiers — only starting-XP offsets
(`media/scripts/generated/characters/character_traits.txt`): `base:obese :743`
`Fitness=-2`, `base:overweight :788` `-1`, `base:underweight :978` `-1`,
`base:very underweight :1002` `-2`, `base:emaciated :281` **none**;
`base:weightgain :1037` grants `base:overweight`, `base:weightloss :1048` grants
`base:underweight`. Everything else is Java. A jar-wide scan for the five trait fields
returns, besides `CharacterTrait`, `CharacterTraits`, `Nutrition` and the script
generator, only `IsoGameCharacter`, `IsoPlayer`, `IsoMovingObject`, `ClimbOverFenceState`
and `ClimbSheetRopeState` (debug print only). Ev C throughout — none of this table was
measured.

| Reader | Effect | Obese | Overweight | Underweight | V.Under | Emaciated | Cite | Ev |
|---|---|---|---|---|---|---|---|---|
| `IsoPlayer.updateInternal2` | **run speed** (applied only when the speed factor is already > 1, i.e. running/sprinting) | ×0.85 | ×0.99 | — | — | — | `@2042–@2079 L2644–L2648` | C |
| `IsoPlayer.updateInternal2` | run speed, **raw weight** gate — the only direct weight read outside `Nutrition` | `weight > 120` → ×0.97 | | | | | `@2080–@2099 L2650-L2651` | C |
| `IsoPlayer.updateEndurance` | endurance-drain multiplier while running/sprinting/dragging (base 1.4, Athletic 0.8, then ×2.3) | — | **2.9** | — | — | — | `@109–@157 L3450–L3459` | C |
| `IsoPlayer.updateEndurance` | same multiplier in the heavy-load (`HEAVY_LOAD > 2`) walking branch (base 1.4, then ×3.0) | — | **2.9** | — | — | — | `@392–@435 L3486–L3495` | C |
| `IsoGameCharacter.getRecoveryMod` | endurance/muscle **recovery** multiplier, after the Fitness curve 0.7→1.6 | ×0.4 | ×0.7 | — | ×0.7 | ×0.3 | `@111–@186 L4649–L4659` | C |
| `getClimbingFailChanceFloat` | climb-success score (higher = safer); Obese/Overweight are `else if` | −25 | −15 | — | — | — | `@113–@153 L17330–L17333` | C |
| `getClimbRopeSpeed` | rope-climb tier (int, clamped 0–10); `else if` | −2 | −1 | — | — | — | `@68–@102 L17412–L17415` | C |
| `calculateGrappleEffectivenessFromTraits` | grapple effectiveness | **×1.05** | **×1.10** | — | ×0.8 | ×0.6 | `@21–@77 L8722–L8731` | C |
| `handleLandingImpact` | fall-damage multiplier (`Obese ∨ Emaciated` first, else `Overweight ∨ V.Under`) | ×1.4 | ×1.2 | — | ×1.2 | ×1.4 | `@210–@280 L2227–L2230` | C |
| `handleLandingImpact` | integer landing-severity term (same grouping) | +20 | +10 | — | +10 | +20 | `@664–@724 L2295–L2298` | C |
| `attackFromWindowsLunge` | window-lunge score (`max(5, n)` at the end); V.Under added **twice** | −10 | −5 | — | **+30** | — | `@295–@365 L15210–L15226` | C |
| `ClimbOverFenceState.shouldFallAfterVaultOver` | vault-fall chance % (`Rand.Next(100) < n − Fitness`); V.Under added **twice** | +20 | +10 | — | **+30** | — | `@178–@259 L582–L597` | C |
| `IsoMovingObject.separate` | bump-trip score `n` (trip if `Rand.Next(n) == 0`; base `10 − 3·bumpNbr + Fitness + Strength − 2·DRUNK`, clamped `[1,80]`) | −8 | −4 | **−4** | −8 | — | `@780–@835 L1356–L1366` | C |
| `Nutrition.canAddFitnessXp` | blocks Fitness/Strength XP from Fitness level | ≥ 6 | ≥ 9 | **never** | ≥ 6 | ≥ 6 | `@0–@85 L275–L280` | C |
| script `XPBoosts` | starting Fitness level offset | −2 | −1 | −1 | −2 | none | `character_traits.txt` above | C |

**Anomalies in that table, all C, all worth a design note.**

- **Obese has no endurance penalty.** `updateEndurance` branches on `OVERWEIGHT` only, and
  the two traits are mutually exclusive (`character_traits.txt:751`), so an obese
  character drains endurance at the *base* 1.4 rate while a merely overweight one drains
  at 2.9.
- **Being heavy helps you grapple** — Overweight ×1.10 and Obese ×1.05 are the only
  positive weight modifiers in the game; the underweight side is penalised.
- **Very Underweight is double-counted** in both `attackFromWindowsLunge` and
  `shouldFallAfterVaultOver` (+20 then +10 = +30), making it worse than Obese at both —
  the same copy/paste family as `characterHaveWeightTrouble`.
- **Emaciated is missing from most readers** — no speed, endurance, climb, rope or
  bump-trip term and no `XPBoosts`; it appears only in `getRecoveryMod`, grapple, fall
  damage and the XP gate.

#### The appetite, thirst and weight traits, with their readers

| Trait (`CharacterTrait` field / registry string) | Effect | Sole reader(s) | Ev |
|---|---|---|---|
| `HEARTY_APPETITE` / `HeartyAppetite` | appetite ×1.5 | `getAppetiteMultiplier @13–@31 L10323-L10324` — jar-wide, the field appears only in `CharacterTrait`, the script generator and `IsoGameCharacter` | C; **M** 0.9997, no cross-talk onto thirst — `exp03-20260910-045523`, [`body.json`](../../testing/artifacts/exp03-20260910-045523/body.json) |
| `LIGHT_EATER` / `LightEater` | appetite ×0.75 | `@32–@50 L10326-L10327`; same scan | C; **M** 1.0001 — same run/artifact |
| `HIGH_THIRST` / `HighThirst` | thirst ×2, both branches, unconditional | `updateThirst @2–@18 L10369-L10370`; only reader in the jar | C; **M** 0.9948 — same run/artifact |
| `LOW_THIRST` / `LowThirst` | thirst ×0.5, both branches | `@19–@37 L10373-L10374`; only reader | C; **M** 1.0000 — same run/artifact |
| `NUTRITIONIST` / `NUTRITIONIST2` | **display only** — gates the Nutrition/Calories/Carbohydrates tooltip block | `Food.DoTooltip @1269–@1291 L1522`, the only reader in the whole jar; `grep -rn Nutritionist media/lua` finds no gameplay use | C |
| `WEIGHT_GAIN` / `WeightGain` | `gainThreshold = 700` when `weight < 90`; script grants `base:overweight` at creation | `Nutrition.updateWeight @21–@48 L149-L150`; `character_traits.txt:1044` | C |
| `WEIGHT_LOSS` / `WeightLoss` | `gainThreshold = 1800` when `weight > 70`; script grants `base:underweight` | `@49–@76 L152-L153`; `character_traits.txt:1055` | C |
| the five band traits | see the tables above | — | C |

`NUTRITIONIST` closes the "display-only?" open question in
[nutrition-core.md](nutrition-core.md): **yes**, display-only. Note it is `Nutritionist`
(cost 2) and `Nutritionist2` (profession variant, cost 0, mutually exclusive) and
`Food.DoTooltip` accepts either. **There is no trait called "Thirsty"** — the plan's name
maps to `HighThirst`. Ev C.

> **Two `hasTrait` traps, both live — but graded differently.** (a) **M**, from the run's
> harness (the artifact's `traitList` values): `CharacterTrait:getName()` returns the name
> **lowercased**: adding
> `CharacterTrait.HEARTY_APPETITE` puts `"heartyappetite"` in `getKnownTraits()` and
> weight 105 puts `"obese"` there — a name comparison against the registry spelling reads
> false on a trait that is demonstrably applied. (b) **C** (grep + inference; the String
> form was never called on the live server): in B42 `hasTrait` takes a
> **`CharacterTrait` enum, not a String** — all 71 call sites in `media/lua` pass the enum
> (e.g. `ISBuildAction.lua:269`); passing a String risks an argument mismatch Kahlua does
> not let `pcall` catch. Also note the registry strings for `Very Underweight` and
> `Out of Shape` contain a **space**, and the wiki's display names differ again
> ([Discrepancies](#discrepancies-vs-the-wiki-mirrors)).

### Sandbox options that touch the body side

| Option | Values | What it multiplies | What it does **not** touch | Cite | Ev |
|---|---|---|---|---|---|
| `StatsDecrease` | enum 1–5, default **3** → ×2.0 / ×1.6 / ×1.0 / ×0.8 / ×0.65 | hunger, thirst, fatigue | **calories** — `updateCalories` reads no sandbox multiplier at all | `SandboxOptions.<init> @990–@1006 L127`; `getStatsDecreaseMultiplier @0–@65 L545–L550` | C; **M** all five mappings read directly, and the calorie ratio stayed 1.005 at both extremes — `exp03-20260910-045523`, [`body.json`](../../testing/artifacts/exp03-20260910-045523/body.json) |
| `Nutrition` | boolean, default true | gates `Nutrition.update()` — macro drain, `updateCalories`, `updateWeight` | intake (`Eat`/`DrinkFluid` keep filling the stores), and hunger/thirst, which live in `IsoGameCharacter` and are not gated by it | `Nutrition.update @0 L65-L66`; [eating-pipeline.md](eating-pipeline.md) | C |
| *(none)* | — | there is **no** dedicated hunger, thirst or calorie-burn sandbox option | — | scan of `SandboxOptions`' method list for hunger / thirst / stat / nutrition / food / multiplier returns only `getStatsDecreaseMultiplier`, `getEnduranceRegenMultiplier` and two loot multipliers | C |

`SandboxOptions:set(name, value)` applied **live on the server with no push** in the run
(M, same artifact) — worth knowing for experiments; the client-side flip caveat from slice
01 ([eating-pipeline.md](eating-pipeline.md) § Open questions) is unaffected.

---

## Code map

| Path | Where | What it does | Ev |
|---|---|---|---|
| `Nutrition.update` | jar `L65–L86` | sandbox/dead/god-mode guards, `!GameClient.client` gate, macro drain, `updateCalories()`, `updateWeight()` | C |
| `Nutrition.updateCalories` | jar `L88–L127` | the five-branch burn model above; also maintains `caloriesMax`/`caloriesMin` (`@319–@358 L121–L125`) for which no reader exists | C |
| `Nutrition.applyTraitFromWeight` / `applyWeightFromTraits` | jar `L247–L268` / `L225–L240` | weight → band traits (every 2000 calls) and traits → weight (creation) | C |
| `Nutrition.characterHaveWeightTrouble` / `canAddFitnessXp` | jar `L271` / `L275–L280` | the XP gate and its duplicated-test bug | C |
| `IsoGameCharacter.updateInternal` → `calculateStats` | jar `L9229` → `L10196–L10221` | dispatcher; `"CalculateStats"` Lua hook short-circuits the lot | C |
| `IsoGameCharacter.updateStats_WakeState` / `updateStats_Awake` | jar `L10224–L10234` / `L10242–L10285` | the side guard and the awake hunger branch | C |
| `IsoPlayer.updateStats_Sleeping` | jar `L3357–L3361` | asleep hunger (overrides the `IsoGameCharacter` version; its well-fed branch applies both factors twice — moot, the constant is 0) | C |
| `IsoGameCharacter.updateThirst` / `autoDrink` | jar `L10367–L10385` / `L11727–…` | thirst, its trait/heat/running terms, and the auto-drink gates | C |
| `IsoGameCharacter.getAppetiteMultiplier` / `getHungerMultiplier` / `getThirstMultiplier` / `getRunningThirstReduction` | jar `L10322` / `L14955` / `L14948` / `L10388` | the four rate multipliers; `getHungerMultiplier` is a hard `return 1.0` | C |
| `Thermoregulator.updateBodyMultipliers` / `getEnergyMultiplier` | jar `L1095–L1118` / `L334` | `energyMultiplier`, `fluidsMultiplier`, `fatigueMultiplier` | C |
| `MoodleType.<clinit>` / `MoodleStat.<clinit>` / `Moodle.Update` / `Moodles.getMoodleLevel` | jar `L7–L32` / `L9–L29` / `L163–L447` / `L40` | the 27 types, the threshold table, level evaluation, the Lua-facing read | C |
| `BodyDamage.UpdateStrength` / `.Update` / `.JustAteFood` | jar `L2062–L2121` / `L2273–L2358` / `L650–L660` | carry capacity, regen tier, health loss, poison decay, the `healthFromFoodTimer` fill and decay | C |
| `ZomboidGlobals` | jar `L67`, values from `media/lua/shared/defines.lua:1` | every hunger/thirst constant is a **Lua** global read at load — a mod can change them before load | C |
| `SandboxOptions` | jar `L127`, `L545–L550` | `StatsDecrease`, `Nutrition` | C |
| `zombie/network/packets/character/PlayerStatsPacket.write` | jar `L31–L40` | the 1 Hz snapshot (below) | C |
| harness | `testing/experiments/s03_body.py`, server-side `stats.get` (atomic clock + nutrition + stats + moodles + traits + carry capacity + food timer), `nutrition.applytraits`, `foodtimer.set` | the measured run | M `exp03-20260910-045523` ([`body.json`](../../testing/artifacts/exp03-20260910-045523/body.json)) |

Full bytecode transcripts, offsets and the 102-row constant table:
[`docs/superpowers/plans/03-notes.md`](../superpowers/plans/03-notes.md).

---

## MP behaviour

**Every stat in this document is server-owned.** The client recomputes moodles from its
own (up to 1 s stale) mirror and computes a weight it then discards.

| Stat / path | Which side runs it | Guard | Ev |
|---|---|---|---|
| macro drain + `updateCalories()` | **server only** | `Nutrition.update @42 L75` `!GameClient.client` | C (restated from slice 01) |
| `Nutrition.updateWeight` — the *computation* | both | no guard at `@0 L138` | C |
| `updateWeight` — the `setWeight` **write** and `applyTraitFromWeight` | **server only** | `updateWeight @317–@320 L198`: `getstatic GameClient.client; ifne 358` sits **before** `setWeight` (`@323 L199`), before the counter increment and before `applyTraitFromWeight` (`@349 L202`) | C; **M** row 14 below — `exp03-20260910-045523` ([`body.json`](../../testing/artifacts/exp03-20260910-045523/body.json)) |
| **hunger** (`updateStats_Awake` / `_Sleeping`) | **server only** in MP; in SP only for `IsoPlayer.getInstance()` | `updateStats_WakeState @8–@26 L10227`: `GameServer.server ∨ (!GameClient.client ∧ IsoPlayer.getInstance() == this)` | C; **M** row 13 below — `exp03-20260910-045523` ([`body.json`](../../testing/artifacts/exp03-20260910-045523/body.json)) |
| **thirst** (`updateThirst`) | same | `@38–@73 L10377` — identical guard, plus an `isGhostMode()` skip | C |
| `autoDrink` | **server only**, and needs `player.getAutoDrink()` | `@0–@6 L11727-L11728`, `@7–@34 L11730-L11731` | C |
| **endurance** (`IsoPlayer.updateEndurance`) | **server only** | `@0–@13 L3427-L3428`: `if (!isAnimal() && GameClient.client) return;` | C |
| **fatigue** | server resets `FATIGUE` unless sleep is allowed *and* needed | `calculateStats @8–@48 L10200-L10201` | C |
| moodle recompute (`Moodles.Update` → `Moodle.Update`) | **both sides** — a pure function of local stats | `Moodles.Update @0–@49 L60–L65`, no side guard | C |

**The packet.** `zombie/network/packets/character/PlayerStatsPacket.write(ByteBufferWriter)V
@0–@74 L31–L40` is an unconditional full snapshot at 1 Hz
(`NetworkPlayerManager.<clinit>` `UpdateLimit(1000)` → `NetworkPlayerAI.syncStats`):

```java
PlayerID.write(bb);                                   // @0  L31
getPlayer().getStats().save(bb.bb);                   // @5  L33  — one float per CharacterStat.ORDERED_STATS
getPlayer().getNutrition().save(bb.bb);               // @19 L34  — calories, proteins, lipids, carbs, weight
bb.putFloat(getPlayer().getTimeSinceLastSmoke());     // @33 L35
getPlayer().getBodyDamage().saveMainFields(bb.bb);    // @44 L36
```

`Stats.save @0–@39 L55–L58` writes the **whole registry**, so HUNGER, THIRST, ENDURANCE
and FATIGUE all ride along with Anger, Boredom, Discomfort, Fitness, FoodSickness,
Idleness, Intoxication, Morale, NicotineWithdrawal, Pain, Panic, Poison, Sanity, Sickness,
Stress, Temperature, Unhappiness, Wetness, ZombieFever and ZombieInfection
(`CharacterStat.<clinit> @10–@283 L12–L35`). There is no per-field bitmask. **Moodles are
not transmitted** — each side recomputes them. **`CharacterTraits` is not in this packet
either**, which is why the client-discard finding below matters. Ev C.

### Measured

| # | Probe | Result | Ev |
|---|---|---|---|
| 14 | **client-side `nutrition.set weight 105`** | client read back **105** immediately with `hasTrait(Obese)` **false**; after 3 s (≥3 packets) the client read **80** and `Obese` still **false**; the server read 80 throughout | **M** `exp03-20260910-045523`, [`body.json`](../../testing/artifacts/exp03-20260910-045523/body.json) |
| 14 | interpretation | both halves of the `updateWeight @317 L198` prediction hold: the client write survives only until the next packet, and **`applyTraitFromWeight` never fires client-side** — the client held weight 105 and still reported no `Obese`. It is a statement about `applyTraitFromWeight` only: the server's own weight was 80, so no band trait existed to sync | C+M same run/artifact |
| 13 | **client-side `stats.set hunger 0.9`** against a server pinned to 0.3 | client read 0.9 at t = 0.51 s and **0.3004 at t = 1.42 s**; the server never left 0.3007 — the revert lands inside **1.5 s**, consistent with the 1 Hz push (a tighter bound than slice 01's 3 s) | **M** same run/artifact |
| — | client mirror generally | the client witness was read only at session start, at the row-1 boundaries and in rows 13/14; every rate in this document is a **server-side** fit | **M** same run/artifact |

**What a mod must do.** Hunger, thirst, endurance, fatigue, calories, macros and weight all
have exactly one owner: the server. A client-side write to any of them is erased by the
next `PlayerStatsPacket` — measured within **1.5 s** for hunger (row 13, sampled at
~0.5 s) and within **3 s** for weight (row 14, whose read-back was only taken at 3 s);
the 1 Hz push is the bound behind both. The three viable shapes — server-side mutation via
the command bus, player modData with an explicit `transmitModData()`, or accepting
client-only semantics — are the same ones the intake side reaches
([eating-pipeline.md](eating-pipeline.md) § MP behaviour;
[../modding/patterns.md](../modding/patterns.md) § Measured MP sync facts). Two extras
specific to the body side: (a) because the constants come from the **Lua** `ZomboidGlobals`
table (`defines.lua`), a mod that rewrites them must do so on the side that runs the
updater — the server; (b) because `Moodles.Update` has no side guard, a client-side moodle
read taken immediately after a server stat write can lag by up to one push.

---

## Discrepancies vs the wiki mirrors

Code wins; the mirrors preserve each page's own version stamp.

| # | Wiki claim (mirror, page version) | Code / measurement | Ev |
|---|---|---|---|
| 1 | Hungry ticks a flat `4.32 %` per in-game hour ([hungry.md](../../references/wiki-mirrors/hungry.md), 42.12.3) | `9.6e-6 × 3600` = **3.456 %/game-hour at H = 0**, and falling as hunger rises — a first-order approach, not a linear fill. The page's `0.00032 %`/tick is `defines.lua:14`'s literal `0.0000032` *before* its `* 3` | W vs C+M `exp03-20260910-045523` ([`body.json`](../../testing/artifacts/exp03-20260910-045523/body.json)) |
| 2 | Health regeneration is cut ~25 % at Peckish, then 25 / 55 / 100 % ([hungry.md](../../references/wiki-mirrors/hungry.md), 42.12.3) | The tier fires only from `HUNGRY == 2` and runs `0.002 → 0.0013 → 0.0008 → 0.0`, i.e. **−35 / −60 / −100 %**, with level 1 having no effect at all. The sister Thirsty page quotes exactly −35 / −60 / −100, corroborating the code | W vs C (+W [thirsty.md](../../references/wiki-mirrors/thirsty.md)) |
| 3 | Each Hungry level decreases "body heat generation"; every positive level heals 750 % faster ([hungry.md](../../references/wiki-mirrors/hungry.md), 42.12.3) | No thermoregulator read of `HUNGRY` exists and no healing multiplier: the whole footprint is carry capacity, the regen tier, the zeroed sleeping health addition at level 4, the level-4 health loss, and for `FOOD_EATEN` the hunger gate, `1.5e-4 × level` poison decay and the `>= 3` eat block | W vs C |
| 4 | Thirsty thresholds "above 13 %" and "above 85 %" ([thirsty.md](../../references/wiki-mirrors/thirsty.md), 42.12.3) | `MoodleStat.<clinit>`'s THIRST row is **0.12 / 0.25 / 0.70 / 0.84**, strict `>` — off by a point at both ends | W vs C+M — all five levels read back on the server, `exp03-20260910-045523` ([`body.json`](../../testing/artifacts/exp03-20260910-045523/body.json)) |
| 5 | Sprinting carries the same ×1.2 thirst as running ([thirsty.md](../../references/wiki-mirrors/thirsty.md), 42.12.3) | `getRunningThirstReduction` returns 1.2 only for `IsoPlayer.getInstance().IsRunning()` — a different flag from `isSprinting()`, and gated on the local instance, so on a dedicated server it may never fire; the asleep branch applies neither it nor the heat term | W vs C |
| 6 | Health drains `22 %` per in-game hour at Dying of Thirst ([thirsty.md](../../references/wiki-mirrors/thirsty.md), 42.12.3) | The severe-moodle health loss is on a **`HUNGRY == 4`** branch only (`0.0165/50` = 3.3e-4 per multiplier unit, per frame-normalised tick, not per game-hour); `THIRST == 4` appears only where the *sleeping* health addition is zeroed | W vs C |
| 7 | The moodle index has no `FoodEaten` entry, folding the well-fed state into Hungry ([moodle.md](../../references/wiki-mirrors/moodle.md), 42.13.2) | `MoodleType.<clinit>` registers a distinct `FOOD_EATEN` that is not threshold-driven at all — it reads `healthFromFoodTimer` against 1600 — and it is `FOOD_EATEN`, not `HUNGRY`, that gates the hunger rate | W vs C+M — the moodle gate and the timer→level mapping measured, `exp03-20260910-045523` ([`body.json`](../../testing/artifacts/exp03-20260910-045523/body.json)) |
| 8 | The trait page's weight bands are 35–50 / 51–65 / 66–75 / 76–85 none / 86–100 / 101–130 ([trait.md](../../references/wiki-mirrors/trait.md), **42.20.4** — the same build, so this is a live contradiction) | `applyTraitFromWeight`'s comparisons are inclusive at both ends: `>= 100` Obese, `<= 50` Emaciated, 85 Overweight, 75 Underweight, normal the open interval (75, 85). The 35 and 130 endpoints are the weight-change floor and ceiling, not band edges | W vs C+M — 100 / 85 / 75 / 80 measured, `exp03-20260910-045523` ([`body.json`](../../testing/artifacts/exp03-20260910-045523/body.json)) |
| 9 | Display names: Fast / Slow Metabolism and Very Low / Low / High / Very High Weight ([trait.md](../../references/wiki-mirrors/trait.md), 42.20.4) | The API strings are `WeightLoss` / `WeightGain` and `Very Underweight` / `Underweight` / `Overweight` / `Obese` — and `getKnownTraits()` returns them **lowercased**. Never match on a display name | W vs C+M — the lowercased `getKnownTraits()` names observed in the run, `exp03-20260910-045523` ([`body.json`](../../testing/artifacts/exp03-20260910-045523/body.json)) |
| 10 | Overweight's starting weight is 90; Obese caps fitness at 7 ([trait.md](../../references/wiki-mirrors/trait.md), 42.20.4) | `applyWeightFromTraits` writes **95**; `canAddFitnessXp` blocks from Fitness **6** for Obese / Emaciated / Very Underweight and from **9** for Overweight, and plain Underweight never blocks | W vs C |
| 11 | Nutritionist "improves foraging" ([trait.md](../../references/wiki-mirrors/trait.md), 42.20.4) | `Food.DoTooltip @1269–@1291 L1522` is the only reader in the jar and `media/lua` has no gameplay use — display-only | W vs C |
| 12 | Per-trait melee-damage and climb-failure percentages for Emaciated / Underweight / Very Underweight ([trait.md](../../references/wiki-mirrors/trait.md), 42.20.4) | No reader on this jar: `getClimbingFailChanceFloat` branches on Obese and Overweight alone, and the whole-jar scan finds the five trait fields in only five classes | W vs C |
| 13 | High Thirst makes you "twice as thirsty when dying of thirst" ([trait.md](../../references/wiki-mirrors/trait.md), 42.20.4) | The ×2 at `updateThirst @2–@18` is unconditional — both branches, every thirst level, no health term | W vs C+M — ×2 measured at moderate thirst, `exp03-20260910-045523` ([`body.json`](../../testing/artifacts/exp03-20260910-045523/body.json)) |
| 14 | A per-level endurance **loss** curve 90 % → 43 % ([fitness.md](../../references/wiki-mirrors/fitness.md), 42.18.0) | `updateEndurance` composes base 1.4, Overweight 2.9, Athletic 0.8 and a ×2.3 stage (then pacing and hyperthermia); the only per-level Fitness curve read in that area is on **recovery** (0.7 → 1.6, which the page's recovery column matches exactly). The page's own footnote hedges the loss column | W vs C |
| 15 | Fitness reduces "damage taken from long falls" and gives a flat 2 %/level trip reduction ([fitness.md](../../references/wiki-mirrors/fitness.md), 42.18.0) | `handleLandingImpact`'s only trait terms are the weight ones; Fitness enters `shouldFallAfterVaultOver` as `Rand.Next(100) < n − Fitness` (a chance) and `IsoMovingObject.separate` additively inside a `[1,80]` clamp — neither is a percentage | W vs C |
| 16 | The moodle page never mentions the cold side's body effect ([moodle.md](../../references/wiki-mirrors/moodle.md), 42.13.2) | `energyMultiplier` (`1 + 0.05p² + 0.10s²`, cold only) multiplies **resting and sleeping calorie burn and nothing else**; the three moving branches never read it | W vs C |

Where the mirrors are right and it is worth saying so: the Hungry thresholds
(0.15 / 0.25 / 0.45 / 0.70) and its carry-capacity ladder, the Thirsty base rate
(2.875 %/game-hour = `8.0e-6 × 3600` = 2.88 %) and its sleeping ×0.125
(`1.0e-6 / 8.0e-6`), the auto-drink floor at 10 %, the appetite/thirst trait multipliers,
the `getRecoveryMod` 40 / 70 / 30 % figures and the Fitness recovery curve all match the
jar exactly. The Hungry and Moodle pages' headline — "nutrition and hunger are entirely
separate mechanics; burning or gaining calories has no effect on this moodle" — is
confirmed in both directions.

---

## Open questions

1. **The moving branches are unmeasured.** The run's one movement attempt got the client
   walking, but the server saw `isPlayerMoving()` in only **5 of 52** samples (one
   consecutive pair) and `IsRunning()` **never** — the run flag did not reach the server's
   copy of the character on the `ISWalkToTimedAction` + `setRunning(true)` route. No
   defensible slope exists for walking, and the running branch was never entered at all,
   so the walk / run / sprint constants (0.078 / 0.13 / 0.169) stay **C**. The
   `Δcalories(walk)/Δcalories(idle) = 4.875`, `×8.125` and `×10.5625` ratio tests remain
   the cheapest way to close this. (M, `exp03-20260910-045523`: the sample counts.)
2. **The asleep branch is unmeasured.** `setAsleep(true)` was written and held on the
   immediate read-back (M — read-back recorded in the T3 review and the smoke run, **not**
   in the committed artifact, whose `rows.r2_asleep` holds only the abort error), but sleep did
   **not** persist: the next row's 52 server samples all read `asleep: false` with
   idle-rate burn ~27 s later. Whether the sleep was walked off or never persisted at all
   is undetermined. The asleep rates (0.003 kcal, 1.0e-6 hunger, 1.0e-6 thirst) stay
   **C**. The row itself aborted ~27 s in on a Windows `os.replace` race in the command
   bus, since fixed with a retry in `testing/pzt/bus.py`.
3. **The 50 kg and 65 kg band edges are unmeasured** (see the weight-band note): re-run
   with calories primed below `(w−80)·40 + 1000` for the low weights.
4. **The `applyTraitFromWeight` period.** 60 s of dedicated-server time did not roll the
   ≤2000-call counter, and the counter's phase at probe start was unknown, so the period
   is bounded below only.
5. **The swipe/climb `mod = 8.0` and the timed-action `caloriesModifier` paths are
   unmeasured** — both need a real target or a real build site, neither of which is one
   harness command.
6. **`getRunningThirstReduction` on a dedicated server.** Gated on
   `this == IsoPlayer.getInstance()`, which on a headless server is probably never true —
   so running may not raise thirst in MP at all. Unmeasured (it needs the running branch
   from item 1).
7. **`energyMultiplier`'s real range.** `primTotal` / `secTotal` are written by
   `Thermoregulator.updateNodes @593–@600 L1088-L1089` from a loop that was not traced, so
   the size of the cold-weather burn bonus is unbounded here; the ≈1.005 reading above is
   one uncontrolled fixture.
8. **The `BodyDamage.Update` health-tier switch mapping** (which `n ∈ {−1,0,1,2,3}` maps
   to standard / reduced / severely-reduced / zero) is inferred from branch order; the four
   bodies and the constants are C, and the wiki's Thirsty page corroborates the ordering.
9. **`JustAteFood`'s real fill** (`|hungerChange| × f × 13000`, ×2 cooked, cap 11 000) is
   unmeasured — the run's real eat reset the timer to 0 rather than filling it within the
   window allowed.
10. **Do the weight band traits reach an MP client at all?** `applyTraitFromWeight` never
    runs client-side and `PlayerStatsPacket` does not carry `CharacterTraits`.
    `CharacterTraits` has `write`/`read` methods, so some other packet presumably carries
    them, but that path was not traced. If they are not synced, client-side run speed,
    climb and fall-damage modifiers would disagree with the server. Row 14 measured only
    that `applyTraitFromWeight` does not fire client-side.
11. **Split-screen / secondary players.** `updateStats_WakeState` and `updateThirst` run
    in SP only when `IsoPlayer.getInstance() == this`; whether players 2–4 therefore never
    accrue hunger or thirst locally is unverified.
12. **`applyWeightFromTraits` write order.** Sequential `if`s, so a character with two
    weight traits (blocked in the UI, but a mod could do it) ends at the last matching
    branch. Not exercised.
13. **`Nutrition.caloriesMax` / `caloriesMin`** are still maintained with no reader found
    — unchanged from the slice-01 open list.

---

## Sources

**Jar (pzdis, 42.20.4 `b0bbce05d5`, `D:\SteamLibrary\steamapps\common\ProjectZomboid\projectzomboid.jar`)**
`zombie/characters/BodyDamage/Nutrition` (`update`, `updateCalories`, `updateWeight`,
`applyTraitFromWeight`, `applyWeightFromTraits`, `characterHaveWeightTrouble`,
`canAddFitnessXp`, `setCalories`); `zombie/characters/IsoGameCharacter`
(`updateInternal`, `calculateStats`, `updateStats_WakeState`, `updateStats_Awake`,
`updateThirst`, `autoDrink`, `getAppetiteMultiplier`, `getHungerMultiplier`,
`getThirstMultiplier`, `getRunningThirstReduction`, `getRecoveryMod`,
`getClimbingFailChanceFloat`, `getClimbRopeSpeed`,
`calculateGrappleEffectivenessFromTraits`, `handleLandingImpact`,
`attackFromWindowsLunge`); `zombie/characters/IsoPlayer` (`updateInternal2`,
`updateEndurance`, `updateStats_Sleeping`); `zombie/characters/IsoMovingObject.separate`;
`zombie/ai/states/ClimbOverFenceState.shouldFallAfterVaultOver`;
`zombie/characters/BodyDamage/BodyDamage` (`Update`, `UpdateStrength`, `JustAteFood`,
`<init>`, `getHealthFromFoodTimeByHunger`);
`zombie/characters/BodyDamage/Thermoregulator` (`updateBodyMultipliers`,
`getEnergyMultiplier`, `getFluidsMultiplier`, `updateNodes`);
`zombie/characters/Moodles/{Moodle,Moodles,MoodleType,MoodleStat}`;
`zombie/characters/{Stats,CharacterStat,CharacterTrait,CharacterTraits}`;
`zombie/GameTime`; `zombie/ZomboidGlobals`; `zombie/SandboxOptions`;
`zombie/network/packets/character/PlayerStatsPacket`; `zombie/network/NetworkPlayerManager`,
`NetworkPlayerAI.syncStats`; `zombie/inventory/types/Food.DoTooltip`.

**Lua and scripts (`D:\SteamLibrary\steamapps\common\ProjectZomboid\media`)**
`lua/shared/defines.lua` (the `ZomboidGlobals` table — every hunger/thirst constant);
`lua/shared/TimedActions/{ISBaseTimedAction,ISEatFoodAction,ISDrinkFluidAction}.lua`;
the 30 `caloriesModifier` assignments listed in
[03-notes.md](../superpowers/plans/03-notes.md) Q1;
`lua/client/ISUI/{ISInventoryPane,ISInventoryPaneContextMenu}.lua`;
`scripts/generated/characters/character_traits.txt`.

**Code map** [`docs/superpowers/plans/03-notes.md`](../superpowers/plans/03-notes.md) —
full bytecode transcripts with offsets, the 102-row threshold table and the experiment
inputs this slice's run executed.

**Measured run.** `exp03-20260910-045523` — fixture `default`, build 42.20.4, one live
session, 1047 s wall, **0 server errors**; artifact
[`testing/artifacts/exp03-20260910-045523/body.json`](../../testing/artifacts/exp03-20260910-045523/body.json)
(the file every **M** row here cites), report
`.superpowers/sdd/03-body-side/task-3-report.md`. Every rate is a least-squares slope
against `worldAge` from the *same* snapshot, so `settimespeed` cancels; the idle baseline
ran 319 s at `settimespeed 1` (233 samples), every other condition 23 s at
`settimespeed 30` (24 samples, ≈3.06 game-hours each). All rate samples are server-side.
The fixture's clock was `S = 16.027` game-s per real-s (idle 0.2577 kcal/real-s at 80 kg),
reproducing slice 01's 0.259 — i.e. a **90-minute in-game day**, `86 400/(90 · 60) = 16.0`,
which is what fixes the `FOOD_EATEN` timer's 3.0 units/game-s above.
*Three keys in that artifact must not be cited*: `summary.r3_6.row3_walking.ratio`
(a whole-window fit over 5 sparse moving samples), `summary.r8.hungerExactlyFlat: false`
(a whole-window fit straddling the eat — the split-window analysis above is the valid one)
and `summary.r12.allBandsMatch: false` (the 50/65 kg drift artifact). Earlier runs cited
here: `exp01-20260910-003929` (store clamps, macro drain, hunger/thirst authority) and
`exp01-20260910-000351` (nutrition authority) — see
[eating-pipeline.md](eating-pipeline.md) § Sources. Full run directories stay local under
`testing/runs/<run id>/` (gitignored).

**Wiki mirrors** (CC BY-NC-SA 3.0, PZwiki contributors; each file records its own page
version): [hungry.md](../../references/wiki-mirrors/hungry.md) 42.12.3,
[thirsty.md](../../references/wiki-mirrors/thirsty.md) 42.12.3,
[moodle.md](../../references/wiki-mirrors/moodle.md) 42.13.2,
[trait.md](../../references/wiki-mirrors/trait.md) **42.20.4**,
[fitness.md](../../references/wiki-mirrors/fitness.md) 42.18.0,
[nutrition.md](../../references/wiki-mirrors/nutrition.md) 42.11.0.

**Prior slices** [eating-pipeline.md](eating-pipeline.md) (slice 01, intake and MP
authority), [food-item-model.md](food-item-model.md) (slice 02, the item),
[nutrition-core.md](nutrition-core.md) (calories → weight).
