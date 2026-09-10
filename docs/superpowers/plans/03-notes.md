# 03 — Body side: passive burn, hunger/thirst, weight bands, moodles (Tasks 1–2 notes)

**Scope:** code reading only. Nothing built, nothing run, no source changed.
Answers the seven questions of the slice-03 brief
(`.superpowers/sdd/03-body-side/research-brief.md`).

**Sources**

| | |
|---|---|
| jar | `D:\SteamLibrary\steamapps\common\ProjectZomboid\projectzomboid.jar`, B42 **42.20.4** (`b0bbce05d5`) |
| disassembler | `C:\Users\Angus\pz-b42\pz.sh` (pzdis; numeric literals resolved inline) |
| Lua | `D:\SteamLibrary\steamapps\common\ProjectZomboid\media\lua\` |
| scripts | `.../media/scripts/generated/characters/character_traits.txt` |
| prior findings cited, not re-derived | `docs/vanilla/nutrition-core.md`, `docs/vanilla/eating-pipeline.md`, `docs/superpowers/plans/01-notes.md` |

**Citation form.** `zombie/characters/BodyDamage/Nutrition.updateCalories @125 L106` =
bytecode offset in that method's dump; `L…` is the source-line label pzdis prints
alongside. Lua as `defines.lua:14`. **Ev**: `C` = read from bytecode/Lua/scripts,
`M` = measured (run id given), `I` = arithmetic inference from C values (flagged inline).

---

## Q0 — The time unit (needed by every formula below)

Two different per-frame idioms appear, and **they are the same unit**. Ev C.

```
GameTime.getTimeDeltaFromMultiplier(m) = m / 0.8 / multiplierBias / 60      # @0–@13 L1017
GameTime.getTimeDelta()                = getTimeDeltaFromMultiplier(getMultiplier())   # @0 L1013
GameTime.getGameWorldSecondsSinceLastUpdate() = getTimeDelta() * 1440 / minutesPerDay  # @0–@13 L214-L215
GameTime.getDeltaMinutesPerDay()       = 30 / minutesPerDay                 # @0–@6 L440
multiplierBias = 1.0f                  # only write in the jar: GameTime.<init> @34–@35 L83
```

Substituting `multiplierBias = 1`:

```
gameWorldSecondsSinceLastUpdate = getMultiplier() * 30 / minutesPerDay
                                = getMultiplier() * getDeltaMinutesPerDay()      # exact identity
```

**Consequence.** `updateCalories` scales by `getGameWorldSecondsSinceLastUpdate()`;
`updateThirst` / `updateStats_Awake` / `updateStats_Sleeping` scale by
`getMultiplier() * getDeltaMinutesPerDay()`. Those are the *same* quantity, so every
constant in this document — calories, hunger, thirst, macro drain — is **per game-world
second**, and a game day is 86 400 of them. Ev C (identity), I (the substitution).

> The macro drain constants in `docs/vanilla/eating-pipeline.md`
> (−0.0035 / −0.00113 / −0.00086 per game-world second) were measured at 99.0 % of the
> coded rate (M, `exp01-20260910-003929`), which independently confirms this unit.

---

## Q1 — `Nutrition.updateCalories`: the full passive-burn formula

`zombie/characters/BodyDamage/Nutrition.updateCalories()V`, 359 bytes, `L88–L127`.
Ev **C** throughout.

```java
void updateCalories() {
    float mod = 1.0f;                                                    // @0   L88
    if (!parent.getCharacterActions().isEmpty())                         // @2   L89
        mod = ((BaseAction) parent.getCharacterActions().get(0)).caloriesModifier;   // @15 L90
    if (parent.isCurrentState(SwipeStatePlayer.instance())
     || parent.isCurrentState(ClimbOverFenceState.instance())
     || parent.isCurrentState(ClimbThroughWindowState.instance()))       // @33  L93
        mod = 8.0f;                                                      // @72  L94

    float energy = 1.0f;                                                 // @75  L98
    if (parent.getBodyDamage() != null
     && parent.getBodyDamage().getThermoregulator() != null)             // @77  L99
        energy = (float) parent.getBodyDamage()
                     .getThermoregulator().getEnergyMultiplier();        // @100 L100

    float w = (float) (getWeight() / 80.0);                              // @115 L104
    float dt = GameTime.getInstance().getGameWorldSecondsSinceLastUpdate();

    if (parent.IsRunning() && parent.isPlayerMoving()) {                 // @125 L106
        mod = 1.0f;                                                      // @145 L107
        setCalories(getCalories() - 0.13f * mod * w * dt);               // @147 L108   <- no `energy`
    } else if (parent.isSprinting() && parent.isPlayerMoving()) {        // @172 L109
        mod = 1.3f;                                                      // @192 L110
        setCalories(getCalories() - 0.13f * mod * w * dt);               // @195 L111   <- no `energy`
    } else if (parent.isPlayerMoving()) {                                // @220 L112
        mod = 0.6f;                                                      // @230 L113
        setCalories(getCalories() - 0.13f * mod * w * dt);               // @233 L114   <- no `energy`
    } else if (parent.isAsleep()) {                                      // @258 L115
        setCalories(getCalories() - 0.003f * mod * energy * w * dt);     // @268 L116
    } else {                                                             // @295 L118
        setCalories(getCalories() - 0.016f * mod * energy * w * dt);
    }

    if (getCalories() > caloriesMax) caloriesMax = getCalories();        // @319 L121-L122
    if (getCalories() < caloriesMin) caloriesMin = getCalories();        // @339 L124-L125
}                                                                        // @359 L127
```

### Three things the prior docs did not have

1. **The thermoregulator energy multiplier applies only at rest.** `energy` (local slot 2)
   is loaded in the *asleep* (`@277`) and *idle* (`@304`) branches and **nowhere else** —
   the three moving branches never touch it (`@147–@165`, `@195–@213`, `@233–@251`).
   Cold therefore raises resting burn and does nothing to running burn. Ev C.
2. **The action / swipe / climb multiplier is also rest-only in practice.** All three
   moving branches *overwrite* `mod` with 1.0 / 1.3 / 0.6 before using it
   (`@145 L107`, `@192 L110`, `@230 L113`). So the 8.0 from
   `SwipeStatePlayer` / `ClimbOverFenceState` / `ClimbThroughWindowState`, and any
   `caloriesModifier` from a timed action, only ever multiply the **0.003 asleep** or
   **0.016 idle** rate. Attacking while standing still burns `0.016 × 8`; attacking while
   running burns the plain running rate. Ev C.
3. `energy` is `Thermoregulator.energyMultiplier`, a bare field read
   (`Thermoregulator.getEnergyMultiplier @0–@4 L334`), rebuilt every tick by
   `Thermoregulator.updateBodyMultipliers()V @0–@198 L1095–L1118`:

```java
energyMultiplier = fluidsMultiplier = fatigueMultiplier = 1.0;        // @0–@12 L1095-L1097
float p = PZMath.abs(primTotal); p *= p;                              // @15–@26 L1099-L1100
if (primTotal < 0) { energyMultiplier += 0.05 * p; fatigueMultiplier += 0.25 * p; }   // @36 L1102-L1103
else if (primTotal > 0) { fluidsMultiplier += 0.25 * p; fatigueMultiplier += 0.25 * p; } // @77 L1105-L1106
float s = PZMath.abs(secTotal); s *= s;                               // @105–@116 L1109-L1110
if (secTotal < 0) { energyMultiplier += 0.10 * s; fatigueMultiplier += 0.75 * s; }    // @126 L1112-L1113
else if (secTotal > 0) { fluidsMultiplier += 3.75 * s; fatigueMultiplier += 1.75 * s; } // @168 L1115-L1116
```

   `primTotal` / `secTotal` are written once per tick at
   `Thermoregulator.updateNodes @593–@600 L1088-L1089`. **`energyMultiplier ≥ 1.0`
   always, and only the *cold* side (negative totals) raises it** — heat raises
   `fluidsMultiplier` (which is `getThirstMultiplier()`, Q2) and `fatigueMultiplier`
   instead. Ev C.

### `caloriesModifier` values (Lua-side, `BaseAction.caloriesModifier`)

Set from the Lua action table by
`LuaTimedActionNew.<init> @73–@81 L39` (rawget `'caloriesModifier'`) → `@209–@220 L57`.
Default `1` (`ISBaseTimedAction.lua:181`). 30 assignments in `media/lua`; the distinct
values are **0.5** (ISReadABook.lua:510, ISResearchRecipe.lua:159, ISRestAction.lua:251),
**2** (ISDismantleAction.lua:109), **3** (ISFitnessAction.lua:222),
**4** (ISMultiStageBuild.lua:187, ISPaintAction.lua:106, ISPaintSignAction.lua:59,
ISWallpaperAction.lua:98, ISHarvestPlantAction.lua:89, ISShovelAction.lua:85,
ISDryMyself.lua:89, ISFixAction.lua:57, ISFixGenerator.lua:91, ISFixVehiclePartAction.lua:65),
**5** (ISPlowAction.lua:153, ISCleanBlood.lua:122, ISCleanGraffiti.lua:88, ISFillGrave.lua:113),
**8** (ISBuildAction.lua:274, ISPlasterAction.lua:63, ISShovelGround.lua:182,
ISBarricadeAction.lua:197, ISLightFromKindle.lua:169, ISChopTreeAction.lua:118,
ISDestroyStuffAction.lua:340, ISPickAxeGroundCoverItem.lua:216, ISPickupBrokenGlass.lua:58,
ISRemoveBrokenGlass.lua:59). Ev C.

### kcal per game-day (arithmetic, Ev I from the C constants)

At weight 80 (`w = 1.0`), `energy = 1.0`, `mod = 1.0`, one game day = 86 400 game-seconds:

| State | kcal / game-second | × 86 400 = kcal / game-day |
|---|---|---|
| asleep | 0.003 | **259.2** |
| **idle (at rest)** | 0.016 | **1 382.4** |
| walking | 0.13 × 0.6 = 0.078 | **6 739.2** |
| **running** | 0.13 × 1.0 = 0.13 | **11 232** |
| sprinting | 0.13 × 1.3 = 0.169 | **14 601.6** |
| idle + swiping/climbing (`mod` 8) | 0.016 × 8 = 0.128 | **11 059.2** |
| idle + `ISBuildAction` (`caloriesModifier` 8) | 0.128 | **11 059.2** |
| idle + `ISReadABook` (`caloriesModifier` 0.5) | 0.008 | **691.2** |
| idle at weight 100 (`w = 1.25`) | 0.020 | **1 728** |
| running at weight 100 | 0.1625 | **14 040** |
| idle, cold, `energy = 1.15` | 0.0184 | **1 589.8** |

**Cross-check against slice 01's measurement.** Idle on the fixture measured
**0.259 kcal per real second** (0.256 in the earlier run) at `settimespeed 1`
(M, `exp01-20260910-003929`). `0.259 / 0.016 = 16.19`, i.e. ≈16.2 game-seconds elapsed
per real second on that fixture at `energy = 1` and `w ≈ 1.01` (weight ≈ 81); the earlier
run's 0.256 is exactly `0.016 × 16 × 1.00`. The coded idle branch reproduces the measured
number to within the weight ratio. Ev C+M+I. The scale factor 16.2 is a property of that
fixture's `minutesPerDay` and framerate, not of the formula — see **Experiment inputs**
for the scale-free ratio tests that avoid depending on it.

**Store clamps still bind** (settled in slice 01, restated): calories clamp to
`[-2200, 3700]` (`Nutrition.setCalories @1 L321, @12 L324`, C+M). At idle a starved
character hits the −2200 floor and burn stops mattering; sustained running (11 232 kcal /
game-day) crosses the whole 5 900-kcal store range in ~12.6 game-hours.

**Guards** (unchanged from slice 01, re-read on this jar, C):
`Nutrition.update @0 L65-L66` sandbox `Nutrition`; `@13/@31 L68–L72` dead / god-mode;
`@42 L75` `!GameClient.client` gates the macro drain **and** `updateCalories()`;
`IsoPlayer.updateInternal2 @392–@402 L2306-L2307` is the only caller and is gated by
`SystemDisabler.doCharacterStats`.

---

## Q2 — Hunger and thirst: where and how fast

**B42 has no `getHunger()` on `Stats`.** Confirmed again on this jar: `IsoGameCharacter`'s
only hunger/thirst methods are `updateThirst()`, `getRunningThirstReduction()`,
`getThirstMultiplier()`, `getHungerMultiplier()`; `IsoPlayer` has none; `BodyDamage` has
only `getHealthFromFoodTimeByHunger()`. The stat route is
`getStats():get(CharacterStat.HUNGER / .THIRST)` (C+M, slice 01).
`CharacterStat.<clinit>`: `Hunger` `[0,1]` default 0 (`@91–@99`), `Thirst` `[0,1]` default 0
(`@231–@239`), `Endurance` `[0,1]` default **1** (`@45–@53 L15`), `Fatigue` `[0,1]` default 0
(`@56–@64 L16`). Ev C.

### The dispatcher and its side guard

```
IsoGameCharacter.updateInternal @1548–@1557 L9229-L9230
    if (SystemDisabler.doCharacterStats) calculateStats();

IsoGameCharacter.calculateStats()V  L10196–L10221
    if (isAnimal()) return;                                              // @0  L10196-L10197
    if (GameServer.server && !(sleepAllowed && sleepNeeded))              // @8  L10200
        stats.reset(FATIGUE);                                             // @38 L10201
    if (LuaHookManager.TriggerHook("CalculateStats", this)) return;       // @49 L10204-L10205
    updateEndurance();      // @60 L10208
    updateTripping();       // @64 L10210
    updateThirst();         // @68 L10212
    updateStress();         // @72 L10214
    updateStats_WakeState();// @76 L10216
    updateMorale();         // @80 L10218
    updateFitness();        // @84 L10220

IsoGameCharacter.updateStats_WakeState()V  L10224–L10234
    if (isAnimal()) return;                                               // @0  L10224-L10225
    if (GameServer.server                                                 // @8  L10227
        || (!GameClient.client && IsoPlayer.getInstance() == this)) {
        if (asleep) updateStats_Sleeping(); else updateStats_Awake();      // @27 L10228–L10231
    }
```

**Side answer (feeds Q7).** `updateStats_WakeState @8–@26 L10227` and the identical guard
in `updateThirst @38–@73 L10377` mean **hunger and thirst tick on the server and never on
an MP client**. In singleplayer they tick only for `IsoPlayer.getInstance()`. Ev C.

**Mod hook worth recording:** `LuaHookManager.TriggerHook("CalculateStats", character)`
returning true skips endurance, tripping, thirst, stress, **hunger**, morale and fitness
for that tick — the single cleanest vanilla interception point for a nutrition mod
(`calculateStats @49–@59 L10204-L10205`, C).

### Thirst — `IsoGameCharacter.updateThirst()V` `L10367–L10385`

```java
float t = 1.0f;                                            // @0   L10367
if (traits.get(HIGH_THIRST)) t *= 2.0f;                    // @2   L10369-L10370
if (traits.get(LOW_THIRST))  t *= 0.5f;                    // @19  L10373-L10374

if (GameServer.server                                       // @38  L10377
 || (!GameClient.client && IsoPlayer.getInstance() == this)) {
    if (isoPlayer != null && isoPlayer.isGhostMode()) { /* skip */ }
    else if (asleep) {                                      // @74  L10378
        stats.add(THIRST, thirstSleepingIncrease
                        * SandboxOptions.getStatsDecreaseMultiplier()
                        * GameTime.getMultiplier()
                        * GameTime.getDeltaMinutesPerDay()
                        * t);                               // @81–@121 L10379
    } else {                                                // @125 L10381
        stats.add(THIRST, thirstIncrease
                        * SandboxOptions.getStatsDecreaseMultiplier()
                        * GameTime.getMultiplier()
                        * getRunningThirstReduction()
                        * GameTime.getDeltaMinutesPerDay()
                        * t
                        * getThirstMultiplier());           // @125–@175 L10381
    }
}
autoDrink();                                                // @176 L10384
```

- `getRunningThirstReduction()D @0–@21 L10388–L10391`: **1.2** when
  `this == IsoPlayer.getInstance() && IsoPlayer.getInstance().IsRunning()`, else 1.0.
  Despite the name it *raises* thirst 20 % while running. It is gated on the local
  instance, so on a dedicated server it is almost certainly always 1.0 — flagged in
  **Open / uncertain**.
- `getThirstMultiplier()D @0–@29 L14948–L14951` = `Thermoregulator.getFluidsMultiplier()`
  (1.0 if no body damage / thermoregulator). Per Q1's `updateBodyMultipliers`, that is
  `1 + 0.25·primTotal² + 3.75·secTotal²` on the **hot** side only — heat makes you
  thirsty, cold does not.
- The **asleep branch applies neither** `getRunningThirstReduction()` nor
  `getThirstMultiplier()` — only the trait factor. Ev C.
- `autoDrink()V L11727–…`: returns immediately on `GameClient.client` (`@0–@6 L11727-L11728`);
  on the server requires `player.getAutoDrink()` (`@7–@34 L11730-L11731`); requires
  `Core.getOptionAutoDrink()`; skipped while asleep / grappling / knocked down / falling /
  aiming / climbing (`@45–@87 L11736-L11737`); fires the Lua hook `"AutoDrink"`
  (`@88–@98 L11739-L11740`); then requires `THIRST > 0.1` (`@99–@116 L11743-L11744`).

### Hunger — `IsoGameCharacter.updateStats_Awake()V` `L10242–L10285`

```java
float appetite = getAppetiteMultiplier();                                    // @171 L10266
boolean exercising = (this instanceof IsoPlayer
                      && ((IsoPlayer) this).IsRunning() && isPlayerMoving()) // @177 L10267
                     || isCurrentState(SwipeStatePlayer.instance());         // @201

if (exercising) {
    if (moodles.getMoodleLevel(FOOD_EATEN) == 0)                             // @211 L10268
        stats.add(HUNGER, hungerIncreaseWhenExercise / 3.0
                        * statsDecreaseMultiplier * appetite
                        * getMultiplier() * getDeltaMinutesPerDay()
                        * getHungerMultiplier());                            // @224 L10269
    else
        stats.add(HUNGER, hungerIncreaseWhenExercise
                        * statsDecreaseMultiplier * appetite
                        * getMultiplier() * getDeltaMinutesPerDay()
                        * getHungerMultiplier());                            // @278 L10271
} else {
    if (moodles.getMoodleLevel(FOOD_EATEN) == 0)                             // @328 L10275
        stats.add(HUNGER, hungerIncrease
                        * statsDecreaseMultiplier * appetite
                        * getMultiplier() * getDeltaMinutesPerDay()
                        * getHungerMultiplier());                            // @341 L10276
    else
        stats.add(HUNGER, hungerIncreaseWhenWellFed          // = 0
                        * statsDecreaseMultiplier
                        * getMultiplier() * getDeltaMinutesPerDay()
                        * getHungerMultiplier());            // NOTE: no appetite term  // @391 L10278
}
```

Sleeping (`IsoPlayer.updateStats_Sleeping()V`, overrides the `IsoGameCharacter` version):

```java
if (moodles.getMoodleLevel(FOOD_EATEN) == 0) {                               // @423 L3357
    float appetite = getAppetiteMultiplier();                                // @436 L3358
    stats.add(HUNGER, hungerIncreaseWhileAsleep * statsDecreaseMultiplier * appetite
                    * getMultiplier() * getDeltaMinutesPerDay() * getHungerMultiplier()); // @441 L3359
} else {
    stats.add(HUNGER, hungerIncreaseWhenWellFed * statsDecreaseMultiplier    // @490 L3361
                    * hungerIncreaseWhileAsleep * statsDecreaseMultiplier    // (both factors twice — copy/paste,
                    * getMultiplier() * getHungerMultiplier()                //  moot because the constant is 0)
                    * getDeltaMinutesPerDay());
}
```

- `getHungerMultiplier()D @0–@1 L14955` is a hard `return 1.0` — a dead hook, the hunger
  counterpart of `getThirstMultiplier()`. There is **no thermoregulator term on hunger**. Ev C.
- `getAppetiteMultiplier()F @0–@52 L10322–L10329`:

```java
float a = 1.0f - stats.get(HUNGER);           // @0–@12 L10322
if (traits.get(HEARTY_APPETITE)) a *= 1.5f;   // @13–@31 L10323-L10324
if (traits.get(LIGHT_EATER))     a *= 0.75f;  // @32–@50 L10326-L10327
return a;                                     // @51 L10329
```

### The constants

`ZomboidGlobals` is loaded from the **Lua** global table `ZomboidGlobals`
(`ZomboidGlobals.Load()V @0–@13 L67`, `rawget` per key), defined at
`media/lua/shared/defines.lua:1`. Ev C.

| Key | `defines.lua` | value | line |
|---|---|---|---|
| `ThirstIncrease` | `0.0000040 * 2` | **8.0e-6** | `:9` |
| `ThirstSleepingIncrease` | `0.0000010` | **1.0e-6** | `:10` |
| `ThirstLevelToAutoDrink` | `0.1` | 0.1 | `:11` |
| `ThirstLevelReductionOnAutoDrink` | `0.1` | 0.1 | `:12` |
| `HungerIncrease` | `0.0000032 * 3` | **9.6e-6** | `:14` |
| `HungerIncreaseWhenWellFed` | `0` | **0** | `:15` |
| `HungerIncreaseWhenExercise` | `0.0000032 * 6` | **1.92e-5** | `:16` |
| `HungerIncreaseWhileAsleep` | `0.0000010` | **1.0e-6** | `:17` |
| `FatigueIncrease` | `0.0000345` | 3.45e-5 | `:19` |
| `SleepFatigueReduction` | `0.000003` | 3.0e-6 | `:34` |
| `RunningEnduranceReduce` | `0.0000520` | 5.2e-5 | `:5` |
| `SprintingEnduranceReduce` | `0.0004550` | 4.55e-4 | `:6` |
| `ImobileEnduranceIncrease` | `0.0000930/3` | 3.1e-5 | `:7` |

### Sandbox

The **only** sandbox multiplier on hunger/thirst is `StatsDecrease`.
`SandboxOptions.<init> @990–@1006 L127`: `newEnumOption("StatsDecrease", 5, 3)`
(5 values, default **3**), translation key `StatDecrease`.
`SandboxOptions.getStatsDecreaseMultiplier()D @0–@65 L545–L550` is a `tableswitch` over
the enum value with bodies `2.0 / 1.6 / 0.8 / 0.65` and default `1.0`; with 5 keys, 4
bodies and the default emitted last, the mapping is **1 → 2.0, 2 → 1.6, 3 → 1.0
(default), 4 → 0.8, 5 → 0.65**. Ev C for the values, **I** for the key↔value pairing
(pzdis does not print the jump table) — flagged in **Open / uncertain**, and it is one of
the cheapest things to settle live.

A scan of `SandboxOptions`' method list for `hunger|thirst|stat|nutrition|food|multiplier`
returns only `getStatsDecreaseMultiplier`, `getEnduranceRegenMultiplier` and the two loot
multipliers — there is **no** dedicated hunger or thirst sandbox option. The nutrition
side has exactly one option (`Nutrition`, gating `Nutrition.update()` only), settled in
slice 01. Ev C.

### Traits

`CharacterTrait.<clinit>` registers by string: `HeartyAppetite` (`@304 L45`),
`LightEater` (`@436 L60`), **`HighThirst`** (`@346 L50`), **`LowThirst`** (`@445 L61`),
`Nutritionist` / `Nutritionist2` (`@526/@535 L70-L71`), `WeightGain` (`@796 L100`),
`WeightLoss` (`@805 L101`), `Emaciated` (`@200 L32`), `Obese` (`@544 L72`),
`Overweight` (`@580 L76`), `Underweight` (`@751 L95`), `Very Underweight` (`@769 L97`).
**There is no trait called "Thirsty"** — the brief's name maps to `HighThirst`. Ev C.

### Per-game-day arithmetic (Ev I from the C constants)

Hunger is **not linear**: `appetite = (1 − H)` makes it a first-order approach.
With `k = HungerIncrease × statsDecreaseMultiplier × traitFactor` per game-second,

```
dH/dt = k · (1 − H)        =>        H(t) = 1 − e^(−k·t)
```

At default sandbox (`×1.0`), no trait, awake, idle, `FOOD_EATEN` level 0:
`k = 9.6e-6 /game-s`, time constant `1/k = 104 167 game-s = 28.94 game-hours`.

| Milestone | plain `k` = 9.6e-6 | Hearty Appetite (×1.5) | Light Eater (×0.75) |
|---|---|---|---|
| H = 0.15 (Hungry lvl 1) | 4.70 game-h | 3.13 game-h | 6.27 game-h |
| H = 0.25 (lvl 2) | 8.32 game-h | 5.55 game-h | 11.10 game-h |
| H = 0.45 (lvl 3) | 17.30 game-h | 11.53 game-h | 23.06 game-h |
| H = 0.70 (lvl 4) | 34.84 game-h | 23.23 game-h | 46.45 game-h |
| H after 1 game-day | 0.5637 | 0.7118 | 0.4633 |

Other hunger regimes, per game-second, same `(1 − H)` factor:
asleep **1.0e-6** (0.0864 · (1−H) per game-day);
exercising with no `FOOD_EATEN` moodle **6.4e-6** — *lower than idle*;
exercising with `FOOD_EATEN` ≥ 1 **1.92e-5** (2× idle);
idle or asleep with `FOOD_EATEN` ≥ 1 **0** (hunger freezes).

Thirst **is** linear (no `(1 − T)` term):

| Milestone | plain 8.0e-6 | HighThirst (×2) | LowThirst (×0.5) |
|---|---|---|---|
| T = 0.12 (Thirsty lvl 1) | 4.17 game-h | 2.08 | 8.33 |
| T = 0.25 (lvl 2) | 8.68 game-h | 4.34 | 17.36 |
| T = 0.70 (lvl 3) | 24.31 game-h | 12.15 | 48.61 |
| T = 0.84 (lvl 4) | 29.17 game-h | 14.58 | 58.33 |
| T = 1.00 (max) | 34.72 game-h | 17.36 | 69.44 |
| T after 1 game-day | 0.6912 | 1.0 (clamped) | 0.3456 |

Asleep thirst 1.0e-6/game-s = 0.0864/game-day; running ×1.2 (local player only);
hot weather ×`fluidsMultiplier`. `autoDrink` holds T near 0.1 when enabled with a water
source in inventory.

**Two vanilla oddities worth flagging for design.**
(a) Exercising on an empty stomach makes you hungry *more slowly* than standing still
(6.4e-6 vs 9.6e-6) — the `/3.0` at `updateStats_Awake @234 L10269` is applied to the
"no `FOOD_EATEN` moodle" branch, i.e. exactly when you are *not* full.
(b) While the `FOOD_EATEN` moodle is up and you are not exercising, hunger does not rise
at all, and the appetite factor is dropped from that branch entirely. Ev C.

---

## Q3 — What "hunger" is relative to calories

**They are two independent stores with no direct coupling in either direction.** Ev C.

| Direction | Verdict | Evidence |
|---|---|---|
| hunger → calorie burn | **none** | `Nutrition.updateCalories @0–@318 L88–L118` reads `characterActions`, three AI states, `Thermoregulator`, `getWeight()` and `GameTime`. It never touches `Stats` or `CharacterStat.HUNGER`. |
| calories → hunger | **none** | `updateStats_Awake @171–@433 L10266–L10278` and `updateStats_Sleeping @423–@543 L3357–L3361` read `getAppetiteMultiplier()`, the `FOOD_EATEN` moodle, `SandboxOptions`, `GameTime` and two traits. Neither reads `Nutrition`. |
| hunger → hunger | **yes, self-damping** | `getAppetiteMultiplier @0–@12 L10322` = `1 − stats.get(HUNGER)`. Hunger is the only stat that feeds its own rate. |
| calories → weight → calories | **yes** | `updateCalories @115 L104` scales by `getWeight()/80`, and `updateWeight` moves weight from calories — the one genuine feedback loop on the nutrition side. |

**What links them in practice** is upstream and downstream, not in these two updaters:

- **Upstream:** `IsoGameCharacter.Eat` writes `stats.add(HUNGER, getHungerChange()*f)` and
  `nutrition.setCalories(... + getCalories()*f)` from the *same* item with the *same* `f`
  (`Eat @163 L5769`, `@281 L5778`; eating-pipeline.md). They move together only because
  the script author made `HungerChange` and `Calories` proportional — nothing enforces it.
  The `[0,1]` clamp on HUNGER discards overshoot while the calories are all kept
  (C+M, slice 01).
- **Downstream, one indirect link:** the `FOOD_EATEN` moodle gates the hunger rate
  (Q2), and that moodle is driven by `BodyDamage.healthFromFoodTimer`, which
  `JustAteFood` fills from `|getHungerChange()| × f × 13000` — from **hunger change, not
  calories** (`JustAteFood @454–@538 L650–L660`; `getHealthFromFoodTimeByHunger @0 L754`
  returns a flat `13000.0`). So a 0-calorie, high-hunger item suppresses hunger growth
  exactly as well as a 900-kcal meal.

**Design consequence.** A mod that adds nutrient stores can drive them from calories, from
hunger, or from neither, without colliding with any vanilla coupling. The only vanilla
number that reads *both* is nothing at all.

---

## Q4 — Weight bands → traits → effects

### The bands — `Nutrition.applyTraitFromWeight()V` `L247–L268` (Ev C)

All five traits are removed first (`@0–@62 L247–L251`), then re-added:

```java
if (weight >= 100)                 traits.add(OBESE);              // @65  L253-L254
if (weight >= 85 && weight < 100)  traits.add(OVERWEIGHT);         // @89  L256-L257
if (weight >  65 && weight <= 75)  traits.add(UNDERWEIGHT);        // @124 L259-L260
if (weight >  50 && weight <= 65)  traits.add(VERY_UNDERWEIGHT);   // @159 L262-L263
if (weight <= 50)                  traits.add(EMACIATED);          // @194 L265-L266
```

**Correction to `docs/vanilla/nutrition-core.md`.** That doc records "Emaciated <50 …
Obese >100". The comparisons are `dcmpl/iflt` at `@72-@73` and `dcmpg/ifgt` at
`@201-@202`: the boundaries are **inclusive** — `weight == 100` is Obese and
`weight == 50` is Emaciated. Normal is the open interval **(75, 85)**; `75` is
Underweight and `85` is Overweight. Ev C.

Applied every **2000** `updateWeight` calls: `updateWeight @329–@357 L200–L203`
increments `updatedWeight`, and at `>= 2000` calls `applyTraitFromWeight()` and resets
the counter. Ev C.

**New MP finding — `updateWeight` writes nothing on a client.**
`updateWeight @317–@320 L198`: `getstatic GameClient.client; ifne 358` sits **before**
`setWeight(...)` (`@323 L199`), before the counter increment and before
`applyTraitFromWeight()`. So on an MP client `updateWeight()` runs the whole calculation
and then discards it; the client's weight comes only from `Nutrition.load` in the packets,
and **`applyTraitFromWeight` never runs client-side**. This refines the statement in
`nutrition-core.md` §MP behavior and `01-notes.md` Q5 that the client "does still run
`updateWeight()` … from the calorie value it last received" — it runs it, but the result
is thrown away. Whether the weight traits reach the client by some other sync path is an
open item. Ev C.

### `applyWeightFromTraits()V` `L225–L240` (character creation / trait grant) — Ev C

`EMACIATED → 50`, `VERY_UNDERWEIGHT → 60`, `UNDERWEIGHT → 70`, `OVERWEIGHT → 95`,
`OBESE → 105` (`@0/@20/@40/@60/@80 L226/L229/L232/L235/L238`). Sequential `if`s, not
`else if` — with two traits set the last matching one wins (Obese > Overweight >
Underweight > Very Underweight > Emaciated in write order). Note `applyWeightFromTraits`
sets 60/70/95/105, which sit **inside** the bands `applyTraitFromWeight` would assign, so
the round trip is stable.

### `characterHaveWeightTrouble()Z` `L271` — Ev C, and it has a bug

```java
return hasTrait(EMACIATED)          // @0
    || hasTrait(OBESE)             // @13
    || hasTrait(VERY_UNDERWEIGHT)  // @26
    || hasTrait(VERY_UNDERWEIGHT)  // @39  <-- duplicated
    || hasTrait(OVERWEIGHT);       // @52
```

`VERY_UNDERWEIGHT` is tested twice and **`UNDERWEIGHT` is never tested** — almost
certainly a copy/paste slip. Consequence: plain Underweight is not "weight trouble".

### `canAddFitnessXp()Z` `L275–L280` — Ev C

```java
if (getPerkLevel(Fitness) >= 9 && characterHaveWeightTrouble()) return false;  // @0–@23 L275-L276
if (getPerkLevel(Fitness) >= 6)                                                // @24 L277
    return !(hasTrait(EMACIATED) || hasTrait(OBESE) || hasTrait(VERY_UNDERWEIGHT)); // @39–@83 L278
return true;                                                                   // @84 L280
```

Extends `nutrition-core.md`: at Fitness **≥ 9** `OVERWEIGHT` blocks too (via
`characterHaveWeightTrouble`), while at 6–8 it does not; and thanks to the duplicate above,
plain `UNDERWEIGHT` never blocks at any level.

### Effects of the weight traits *outside* `Nutrition`

The trait **scripts** carry no stat modifiers — only starting-XP offsets
(`media/scripts/generated/characters/character_traits.txt`, Ev C):

| Trait | script line | `XPBoosts` | `GrantedTraits` |
|---|---|---|---|
| `base:obese` | `:743` | `Fitness=-2` | — |
| `base:overweight` | `:788` | `Fitness=-1` | — |
| `base:underweight` | `:978` | `Fitness=-1` | — |
| `base:very underweight` | `:1002` | `Fitness=-2` | — |
| `base:emaciated` | `:281` | **none** | — |
| `base:weightgain` | `:1037` | — | `base:overweight` |
| `base:weightloss` | `:1048` | — | `base:underweight` |

Everything else is Java. A jar-wide scan for the field names `OBESE`, `OVERWEIGHT`,
`UNDERWEIGHT`, `VERY_UNDERWEIGHT`, `EMACIATED` returns, besides `CharacterTrait`,
`CharacterTraits`, `Nutrition` and the script generator, exactly:
`IsoGameCharacter`, `IsoPlayer`, `IsoMovingObject`, `ClimbOverFenceState`,
`ClimbSheetRopeState` (debug print only). `Book` hits are book *titles*
(`Book.<clinit>` — "Fathetic: The Thinking That Keeps You Overweight" etc.) and carry no
mechanic. Ev C.

| Reader | Effect | Obese | Overweight | Underweight | V.Under | Emaciated | Cite |
|---|---|---|---|---|---|---|---|
| `IsoPlayer.updateInternal2` | **run speed** (only applied when the speed factor is already > 1, i.e. running/sprinting) | ×0.85 | ×0.99 | — | — | — | `@2042–@2079 L2644–L2648` |
| `IsoPlayer.updateInternal2` | run speed, **raw weight** gate | `weight > 120` → ×0.97 | | | | | `@2080–@2099 L2650-L2651` |
| `IsoPlayer.updateEndurance` | endurance-drain multiplier while running/sprinting/dragging (base **1.4**, Athletic 0.8, then ×2.3) | — | **2.9** | — | — | — | `@109–@157 L3450–L3459` |
| `IsoPlayer.updateEndurance` | same multiplier in the heavy-load (`HEAVY_LOAD > 2`) walking branch (base 1.4, then ×3.0) | — | **2.9** | — | — | — | `@392–@435 L3486–L3495` |
| `IsoGameCharacter.getRecoveryMod` | endurance/muscle **recovery** multiplier (after the Fitness curve 0.7→1.6) | ×0.4 | ×0.7 | — | ×0.7 | ×0.3 | `@111–@186 L4649–L4659` |
| `IsoGameCharacter.getClimbingFailChanceFloat` | climb-success score (higher = safer); Obese/Overweight are `else if` | −25 | −15 | — | — | — | `@113–@153 L17330–L17333` |
| `IsoGameCharacter.getClimbRopeSpeed` | rope-climb speed tier (int, later clamped to 0–10 and mapped to a speed); Obese/Overweight are `else if` | −2 | −1 | — | — | — | `@68–@102 L17412–L17415` |
| `IsoGameCharacter.calculateGrappleEffectivenessFromTraits` | grapple effectiveness | **×1.05** | **×1.10** | — | ×0.8 | ×0.6 | `@21–@77 L8722–L8731` |
| `IsoGameCharacter.handleLandingImpact` | fall-damage multiplier (`Obese ∨ Emaciated` first, else `Overweight ∨ V.Under`) | ×1.4 | ×1.2 | — | ×1.2 | ×1.4 | `@210–@280 L2227–L2230` |
| `IsoGameCharacter.handleLandingImpact` | second, integer landing-severity term (same grouping) | +20 | +10 | — | +10 | +20 | `@664–@724 L2295–L2298` |
| `IsoGameCharacter.attackFromWindowsLunge` | window-lunge score (higher = better; `max(5, n)` at the end); V.Under is added **twice** (+20 then +10) | −10 | −5 | — | **+30** | — | `@295–@365 L15210–L15226` |
| `ClimbOverFenceState.shouldFallAfterVaultOver` | vault-fall chance % (`Rand.Next(100) < n − Fitness`); V.Under added **twice** (+20 then +10) | +20 | +10 | — | **+30** | — | `@178–@259 L582–L597` |
| `IsoMovingObject.separate` | bump-trip score `n` (trip if `Rand.Next(n) == 0`; base `10 − 3·bumpNbr + Fitness + Strength − 2·DRUNK`, clamped `[1, 80]`) | −8 | −4 | **−4** | −8 | — | `@780–@835 L1356–L1366` |
| `Nutrition.canAddFitnessXp` | blocks Fitness/Strength XP | ≥ 6 | ≥ 9 | never | ≥ 6 | ≥ 6 | `canAddFitnessXp @0–@85 L275–L280` |
| script `XPBoosts` | starting Fitness level offset | −2 | −1 | −1 | −2 | none | `character_traits.txt` above |

**Anomalies in that table, all Ev C, all worth a design note:**

- **Obese has no endurance penalty.** `updateEndurance` branches on `OVERWEIGHT` only; the
  two traits are mutually exclusive (`character_traits.txt:751`), so an obese character
  drains endurance at the *base* 1.4 rate while a merely overweight one drains at 2.9.
- **Being heavy helps you grapple.** Overweight ×1.10 and Obese ×1.05 are the only
  positive weight modifiers in the game; the underweight side is penalised (×0.8 / ×0.6).
- **Very Underweight is double-counted** in both `attackFromWindowsLunge` and
  `shouldFallAfterVaultOver` (+20 then +10 = +30), making it worse than Obese (+20) at
  both. Matches the duplicate-check style of `characterHaveWeightTrouble` — the same
  copy/paste family of bugs.
- **Emaciated is missing from most of them** — no speed, endurance, climb, rope or
  bump-trip term, and no `XPBoosts`. It shows up only in `getRecoveryMod` (×0.3),
  grapple (×0.6), fall damage (×1.4 / +20) and the XP gate.
- **Raw weight is read directly exactly once outside `Nutrition`**:
  `IsoPlayer.updateInternal2 @2080–@2099 L2650-L2651`, `weight > 120 → run speed ×0.97`.
  Everything else goes through the traits.

**Correction to `docs/vanilla/nutrition-core.md` § Macro effects.** That doc lists the
`getRecoveryMod` lipid/protein deficit penalties (`< −1000 → ×0.5`, `< −1500 → ×0.2`,
`getRecoveryMod @187–@236+ L4663–L4667`) as live effects. They are **unreachable**:
`Nutrition.setLipids` / `setProteins` clamp at **−500** (`@1/@12`, C+M slice 01), so
neither threshold can ever be crossed. They are dead code in vanilla. Ev C+M+I.
The *trait* multipliers in the same method (Obese ×0.4 etc., `@111–@186`) are live.

---

## Q5 — Moodles driven by nutrition

**They are not script-registered.** `find media/scripts -iname "*moodle*"` returns
nothing. `MoodleType` is a registry of Java statics
(`MoodleType.<clinit> @0–@205 L7–L32`, 27 entries) and the thresholds live in
`MoodleStat.<clinit> @0–@369 L9–L29`, a Java-side `MoodleStat.register(type, min, lowest,
moderate, highest, maximum)` table. The brief's assumption that they come from
`media/scripts` is wrong for 42.20.4. Ev C.

Lua-visible enum names are the **static field names**, confirmed by usage:
`MoodleType.FOOD_EATEN` (`ISEatFoodAction.lua:14`, `ISDrinkFluidAction.lua:7`,
`ISInventoryPane.lua:986`, `ISInventoryPaneContextMenu.lua:500`, `:2313`), so the three
of interest are **`MoodleType.HUNGRY`**, **`MoodleType.THIRST`**, **`MoodleType.FOOD_EATEN`**
(the display strings are `Hungry`, `Thirst`, `FoodEaten`). Levels are
`Moodle$MoodleLevel` ordinals **0–4** (`Min/Low/Moderate/High/Max`,
`Moodle$MoodleLevel.<clinit>`). `Moodles.getMoodleLevel(type)` returns that int
(`@0–@16 L40`). Ev C.

**There is no weight moodle.** The 27 registered types contain nothing weight-related;
`HeavyLoad` is inventory encumbrance (`MoodleStat.HEAVY_LOAD @352–@366 L29`, thresholds
0 / 1 / 1.25 / 1.5 / 1.75 on the carry-weight ratio), not body weight. Ev C.

### Thresholds (`MoodleStat.<clinit>`, Ev C)

| Moodle | min | lvl 1 (`>`) | lvl 2 (`>`) | lvl 3 (`>`) | lvl 4 (`>`) | cite |
|---|---|---|---|---|---|---|
| `HUNGRY` (stat `HUNGER`, 0–1) | 0 | **0.15** | **0.25** | **0.45** | **0.70** | `@64–@79 L13` |
| `THIRST` (stat `THIRST`, 0–1) | 0 | **0.12** | **0.25** | **0.70** | **0.84** | `@172–@187 L19` |
| `ENDURANCE` (inverted) | 0.75 | 0.5 | 0.25 | 0.10 | 0 | `@10–@25 L10` |
| `HEAVY_LOAD` | 0 | 1.0 | 1.25 | 1.5 | 1.75 | `@352–@366 L29` |

`Moodle.Update()Z` evaluates them with plain `>` in ascending order, last match wins:
HUNGRY at `@474–@580 L163–L175` (gated on `getBodyDamage().getHealth() != 0`),
THIRST at `@1145–@1270 L266–L275` (no health gate). Ev C.
`MoodleStat` exposes `get(MoodleType)` plus `setLowestThreshold` etc., so a mod can
retune these at runtime without a Java patch — worth noting for the mod design.

`FOOD_EATEN` is **not** threshold-driven; it reads the food timer
(`Moodle.Update @2306–@2454 L435–L447`, gated on health != 0):

| Level | Condition | Ev |
|---|---|---|
| 1 | `healthFromFoodTimer > 0` | C `@2331–@2352 L437-L438` |
| 2 | `> standardHealthFromFoodTime` (**1600**) | C `@2353–@2384 L440-L441` |
| 3 | `> 2 × 1600 = 3200` | C `@2385–@2418 L443-L444` |
| 4 | `> 3 × 1600 = 4800` | C `@2419–@2454 L446-L447` |

`standardHealthFromFoodTime = 1600` (`BodyDamage.<init> @97–@100 L80`).
The timer decays `−1 × GameTime.getMultiplier()` per tick
(`BodyDamage.Update @575–@590 L2273`) and is filled by
`JustAteFood` with `|getHungerChange()| × f × 13000`, doubled if cooked, hard-capped at
**11000** (`JustAteFood @454–@538 L650–L660`). Ev C.

### What each level *does*

| Consumer | Effect | Cite | Ev |
|---|---|---|---|
| `BodyDamage.UpdateStrength` | carry capacity: `n = 0`; HUNGRY lvl 2 → `n += 1`, lvl 3 → `+2`, lvl 4 → `+2`; THIRST identically; SICK 2/3/4 → `+1/+2/+3`; BLEEDING/INJURED likewise. Then `setMaxWeight((int)(maxWeightBase × weightMod) − n)`, floored at 0, then `× getMaxWeightDelta()` for players | `@2–@61 L2062–L2069` (hunger), `@62–@121 L2071–L2078` (thirst), `@302–@383 L2113–L2121` | C |
| `BodyDamage.Update` | health **regeneration** tier: `n = 0`; `HUNGRY == 2 ∨ SICK == 2 ∨ THIRST == 2 → n = 1`; `== 3 → n = 2`; `HUNGRY == 4 ∨ THIRST == 4 → n = 3` (note SICK 4 is **not** in this one); `asleep → n = −1`. Then `health += standardHealthAddition (0.002)` / `reducedHealthAddition (0.0013)` / `severlyReducedHealthAddition (0.0008)` / `0.0` × `GameTime.getMultiplier()` | `@591–@838 L2274–L2312`; constants `BodyDamage.<init> @61–@81 L74–L77` | C, key mapping **I** |
| `BodyDamage.Update` | asleep: if `HUNGRY == 4 ∨ THIRST == 4`, the sleeping health addition (`0.02`) is zeroed | `@839–@924 L2316–L2323` | C |
| `BodyDamage.Update` | **health loss**: `HUNGRY == 4` → `healthReductionFromSevereBadMoodles / 50 × multiplier` = `0.0165/50 = 3.3e-4` per multiplier unit, added to the reduction total | `@1134–@1172 L2356–L2358`; constant `<init> @91–@93 L79` | C |
| `BodyDamage.Update` | `FOOD_EATEN` level > 0 speeds poison decay by `1.5e-4 × level` on top of `poisonLevelDecrease` | `@1028–@1090 L2349–L2353` | C |
| `IsoGameCharacter.updateStats_Awake` / `IsoPlayer.updateStats_Sleeping` | `FOOD_EATEN` level gates the **hunger rate** (Q2) | `@211/@328 L10268/L10275`, `@423 L3357` | C |
| `ISEatFoodAction.lua:14`, `ISDrinkFluidAction.lua:7` | `isValidStart` false at `FOOD_EATEN >= 3` — "can't eat more" | Lua | C |
| `ISInventoryPane.lua:986`, `:989`; `ISInventoryPaneContextMenu.lua:500`, `:2313` | UI gating of eat/drink at `FOOD_EATEN >= 3` | Lua | C |
| `IsoGameCharacter.getClimbRopeSpeed`, `getClimbingFailChanceFloat`, `IsoMovingObject.separate` | read `DRUNK`, `ENDURANCE`, `PAIN`, `HEAVY_LOAD` — **not** `HUNGRY`/`THIRST` | dumps above | C |

**Negative result worth recording:** a whole-jar scan for `HUNGRY` finds it only in
`ParameterMoodles` (audio), `BodyDamage`, `Moodle`, `MoodleStat`, `Book` (a title), the
`MoodleType` registry and `MoodleTextureSet`/`MoodlesUI` (display); and
`grep -rn "MoodleType.HUNGRY" media/lua` and `MoodleType.THIRST` return **nothing**.
So **the Hungry and Thirsty moodles have no movement-speed, damage, or XP effect at all** —
their entire mechanical footprint is the three `BodyDamage` rows above (carry capacity,
health regen tier, health loss at level 4). Ev C.

---

## Q6 — Traits, with each reader

| Trait (`CharacterTrait` field / string) | Effect | Sole reader(s) | Ev |
|---|---|---|---|
| `HEARTY_APPETITE` / `HeartyAppetite` | appetite ×1.5 → hunger rises 1.5× faster | `IsoGameCharacter.getAppetiteMultiplier @13–@31 L10323-L10324`. Jar-wide the field appears only in `CharacterTrait`, the script generator and `IsoGameCharacter` | C |
| `LIGHT_EATER` / `LightEater` | appetite ×0.75 | `getAppetiteMultiplier @32–@50 L10326-L10327`; same jar-wide scan | C |
| `HIGH_THIRST` / `HighThirst` | thirst ×2 (both awake and asleep branches) | `IsoGameCharacter.updateThirst @2–@18 L10369-L10370`; only reader in the jar | C |
| `LOW_THIRST` / `LowThirst` | thirst ×0.5 | `updateThirst @19–@37 L10373-L10374`; only reader | C |
| `NUTRITIONIST` / `NUTRITIONIST2` | **display only — confirmed.** Gates the "Nutrition / Calories / Carbohydrates / …" tooltip block | `Food.DoTooltip @1269–@1291 L1522` — the *only* reader in the whole jar; `grep -rn Nutritionist media/lua` finds no gameplay use | C |
| `WEIGHT_GAIN` / `WeightGain` | `gainThreshold = 700` when `weight < 90`; script also grants `base:overweight` at creation | `Nutrition.updateWeight @21–@48 L149-L150`; `character_traits.txt:1044` | C |
| `WEIGHT_LOSS` / `WeightLoss` | `gainThreshold = 1800` when `weight > 70`; script grants `base:underweight` | `Nutrition.updateWeight @49–@76 L152-L153`; `character_traits.txt:1055` | C |
| `OBESE`/`OVERWEIGHT`/`UNDERWEIGHT`/`VERY_UNDERWEIGHT`/`EMACIATED` | see the Q4 table | — | C |

`NUTRITIONIST` resolves the open question in `docs/vanilla/nutrition-core.md`
("Nutritionist trait: display-only? unconfirmed") — **yes, display-only**, Ev C.
Note it is `Nutritionist` (cost 2) and `Nutritionist2` (profession variant, cost 0,
mutually exclusive), and `Food.DoTooltip` accepts either.

---

## Q7 — MP inputs

Slice 01 established that the **server** runs `Nutrition.update` (drain, `updateCalories`,
`updateWeight`) and pushes `Nutrition` at 1 Hz. Everything below either confirms that or
adds the hunger/thirst/endurance half. Ev C throughout except where marked.

| Path | Which side runs it | Guard |
|---|---|---|
| `Nutrition.update` — macro drain + `updateCalories()` | **server only** | `Nutrition.update @42 L75` `!GameClient.client` (restated from slice 01) |
| `Nutrition.updateWeight` — the *computation* | both | no guard at `@0 L138` |
| `Nutrition.updateWeight` — the `setWeight` **write** + `applyTraitFromWeight` | **server only** | **new:** `updateWeight @317–@320 L198` `GameClient.client → skip` sits before `@323 L199 setWeight` and `@349 L202 applyTraitFromWeight` |
| **hunger** (`updateStats_Awake` / `updateStats_Sleeping`) | **server only** in MP; in SP only for `IsoPlayer.getInstance()` | `updateStats_WakeState @8–@26 L10227`: `GameServer.server ∨ (!GameClient.client ∧ IsoPlayer.getInstance() == this)` |
| **thirst** (`updateThirst`) | same | `updateThirst @38–@73 L10377` — identical guard, plus a `isGhostMode()` skip |
| `autoDrink` | **server only** (and needs `player.getAutoDrink()`) | `autoDrink @0–@6 L11727-L11728`, `@7–@34 L11730-L11731` |
| **endurance** (`IsoPlayer.updateEndurance`) | **server only** | `updateEndurance @0–@13 L3427-L3428`: `if (!isAnimal() && GameClient.client) return;` |
| `calculateStats` (the whole block) | gated by `SystemDisabler.doCharacterStats` and the `"CalculateStats"` Lua hook | `IsoGameCharacter.updateInternal @1548–@1557 L9229-L9230`; `calculateStats @49–@59 L10204-L10205` |
| moodle recompute (`Moodles.Update` → `Moodle.Update`) | **both sides** — it is a pure function of local stats | `Moodles.Update @0–@49 L60–L65` has no side guard |

**`PlayerStatsPacket` payload.** The class is
`zombie/network/packets/character/PlayerStatsPacket` (not `.../packets/`);
`write(ByteBufferWriter)V @0–@74 L31–L40`:

```java
PlayerID.write(bb);                                        // @0  L31
getPlayer().getStats().save(bb.bb);                        // @5  L33   <-- every stat
getPlayer().getNutrition().save(bb.bb);                    // @19 L34   <-- calories, proteins, lipids, carbs, weight
bb.putFloat(getPlayer().getTimeSinceLastSmoke());          // @33 L35
getPlayer().getBodyDamage().saveMainFields(bb.bb);         // @44 L36
```

`Stats.save(ByteBuffer)V @0–@39 L55–L58` writes **one float per entry of
`CharacterStat.ORDERED_STATS`** — the whole registry, so **HUNGER, THIRST, ENDURANCE and
FATIGUE are all carried**, along with Anger, Boredom, Discomfort, Fitness, FoodSickness,
Idleness, Intoxication, Morale, NicotineWithdrawal, Pain, Panic, Poison, Sanity, Sickness,
Stress, Temperature, Unhappiness, Wetness, ZombieFever, ZombieInfection
(`CharacterStat.<clinit> @10–@283 L12–L35`). There is no per-field bitmask on this packet:
it is an unconditional full snapshot at 1 Hz
(`NetworkPlayerManager.<clinit>` `UpdateLimit(1000)` → `NetworkPlayerAI.syncStats`, slice 01).

The moodles themselves are **not** transmitted — they are recomputed on each side from the
stats and `BodyDamage` fields that *are* transmitted. Ev C.

Consistent with the measurements already on file: a client-side `stats.set hunger 0.9` was
back to the server's value inside 3 s, a server-side `0.4` reached the client
(M, `exp01-20260910-003929`).

---

## Threshold / multiplier table — everything found in this slice

Ev **C** unless marked. 102 rows.

| Item | Value | Effect | Source | Ev |
|---|---|---|---|---|
| `multiplierBias` | 1.0 | makes `gameWorldSecondsSinceLastUpdate == getMultiplier()·getDeltaMinutesPerDay()` | `GameTime.<init> @34–@35 L83` | C |
| game day | 86 400 game-seconds | denominator for every rate here | definition | C |
| burn base, running | 0.13 /game-s | `−0.13 · mod · (w/80) · dt`, `mod` forced to 1.0 | `Nutrition.updateCalories @145–@165 L107-L108` | C |
| burn base, sprinting | 0.13 × **1.3** = 0.169 | same shape | `updateCalories @192–@213 L110-L111` | C |
| burn base, walking | 0.13 × **0.6** = 0.078 | same shape | `updateCalories @230–@251 L113-L114` | C |
| burn base, asleep | **0.003** /game-s | `−0.003 · mod · energy · (w/80) · dt` | `updateCalories @268–@289 L116` | C |
| burn base, idle | **0.016** /game-s | `−0.016 · mod · energy · (w/80) · dt` | `updateCalories @295–@316 L118` | C |
| swipe / climb-fence / climb-window | `mod = 8.0` | only reaches the asleep & idle branches | `updateCalories @33–@74 L93-L94` | C |
| action `caloriesModifier` | 0.5 / 1 / 2 / 3 / 4 / 5 / 8 | `mod` from the front `CharacterAction`; same rest-only reach | `updateCalories @2–@32 L89-L90`; `ISBaseTimedAction.lua:181` + 29 overrides | C |
| weight term | `getWeight() / 80.0` | linear on every burn branch | `updateCalories @115–@124 L104` | C |
| thermoregulator energy | `≥ 1.0`, cold only | multiplies **asleep and idle burn only** | `updateCalories @277/@304`; `Thermoregulator.updateBodyMultipliers @36–@141 L1102–L1113` | C |
| energy, primary cold | `+0.05 · primTotal²` | | `updateBodyMultipliers @36–@50 L1102` | C |
| energy, secondary cold | `+0.10 · secTotal²` | | `updateBodyMultipliers @126–@140 L1112` | C |
| fluids (thirst) mult, primary heat | `+0.25 · primTotal²` | multiplies awake thirst | `updateBodyMultipliers @77–@90 L1105` | C |
| fluids (thirst) mult, secondary heat | `+3.75 · secTotal²` | multiplies awake thirst | `updateBodyMultipliers @168–@182 L1115` | C |
| fatigue mult | `+0.25/+0.25/+0.75/+1.75 · total²` | cold-prim / heat-prim / cold-sec / heat-sec | `updateBodyMultipliers L1103/L1106/L1113/L1116` | C |
| kcal/game-day, asleep @ w80 | **259.2** | `0.003 × 86400` | derived | I |
| kcal/game-day, idle @ w80 | **1 382.4** | `0.016 × 86400` | derived | I |
| kcal/game-day, walking @ w80 | **6 739.2** | | derived | I |
| kcal/game-day, running @ w80 | **11 232** | | derived | I |
| kcal/game-day, sprinting @ w80 | **14 601.6** | | derived | I |
| kcal/game-day, idle + swipe @ w80 | **11 059.2** | `0.128 × 86400` | derived | I |
| idle burn, measured | 0.259 kcal / **real** s | ⇒ ≈16.2 game-s per real-s on the fixture | `exp01-20260910-003929` | M |
| calorie store clamp | `[−2200, 3700]` | caps the model | `Nutrition.setCalories @1/@12` | C+M |
| macro store clamp | `[−500, 1000]` each | makes the `getRecoveryMod` macro penalties unreachable | `setCarbohydrates/setProteins/setLipids @1/@12` | C+M |
| `HungerIncrease` | **9.6e-6** /game-s | idle awake hunger rate | `defines.lua:14`; `updateStats_Awake @348 L10276` | C |
| `HungerIncreaseWhenExercise` | **1.92e-5** /game-s | used with `FOOD_EATEN ≥ 1` while exercising | `defines.lua:16`; `@285 L10271` | C |
| `HungerIncreaseWhenExercise / 3` | **6.4e-6** /game-s | used with `FOOD_EATEN == 0` while exercising — *below* the idle rate | `@231–@237 L10269` | C |
| `HungerIncreaseWhileAsleep` | **1.0e-6** /game-s | | `defines.lua:17`; `IsoPlayer.updateStats_Sleeping @448 L3359` | C |
| `HungerIncreaseWhenWellFed` | **0** | hunger frozen while `FOOD_EATEN ≥ 1` and not exercising | `defines.lua:15`; `@398 L10278`, `@497 L3361` | C |
| appetite factor | `1 − stats.get(HUNGER)` | self-damping; hunger approaches 1 exponentially | `getAppetiteMultiplier @0–@12 L10322` | C |
| Hearty Appetite | ×1.5 on appetite | | `getAppetiteMultiplier @13–@31 L10323-L10324` | C |
| Light Eater | ×0.75 on appetite | | `getAppetiteMultiplier @32–@50 L10326-L10327` | C |
| `getHungerMultiplier()` | hard **1.0** | dead hook; no thermoregulator term on hunger | `IsoGameCharacter.getHungerMultiplier @0–@1 L14955` | C |
| hunger time constant, default | `1/k` = 28.94 game-h | `k = 9.6e-6` | derived | I |
| hunger, 1 game-day, default | H = **0.5637** | `1 − e^{−0.82944}` | derived | I |
| hunger to lvl 1 / 2 / 3 / 4 | 4.70 / 8.32 / 17.30 / 34.84 game-h | at default sandbox, no trait | derived | I |
| `ThirstIncrease` | **8.0e-6** /game-s | awake thirst, linear | `defines.lua:9`; `updateThirst @132 L10381` | C |
| `ThirstSleepingIncrease` | **1.0e-6** /game-s | asleep thirst; no running/heat term | `defines.lua:10`; `updateThirst @88 L10379` | C |
| running thirst | ×**1.2** | only when `this == IsoPlayer.getInstance()` and it is running | `getRunningThirstReduction @16–@19 L10389` | C |
| High Thirst | ×**2.0** | both branches | `updateThirst @2–@18 L10369-L10370` | C |
| Low Thirst | ×**0.5** | both branches | `updateThirst @19–@37 L10373-L10374` | C |
| `ThirstLevelToAutoDrink` | 0.1 | autoDrink floor | `defines.lua:11`; `autoDrink @99–@116 L11743` | C |
| `ThirstLevelReductionOnAutoDrink` | 0.1 | | `defines.lua:12` | C |
| thirst, 1 game-day, default | T = **0.6912** | linear | derived | I |
| thirst to lvl 1 / 2 / 3 / 4 | 4.17 / 8.68 / 24.31 / 29.17 game-h | | derived | I |
| `StatsDecrease` sandbox | 1→2.0, 2→1.6, **3→1.0 (default)**, 4→0.8, 5→0.65 | multiplies hunger, thirst, fatigue (not calories) | `SandboxOptions.getStatsDecreaseMultiplier @0–@65 L545–L550`; `<init> @990–@1006 L127` | C (values) / I (key order) |
| macro drain, carbs | −0.0035 /game-s | slice 01 | `Nutrition.update @48 L76` | C+M |
| macro drain, lipids | −0.00113 /game-s | slice 01 | `@66 L77` | C+M |
| macro drain, proteins | −0.00086 /game-s | slice 01 | `@84 L78` | C+M |
| band: Obese | `weight >= 100` | **inclusive** | `applyTraitFromWeight @65–@88 L253-L254` | C |
| band: Overweight | `85 <= weight < 100` | | `@89–@123 L256-L257` | C |
| band: normal | `75 < weight < 85` | open interval | complement of the five | C |
| band: Underweight | `65 < weight <= 75` | | `@124–@158 L259-L260` | C |
| band: Very Underweight | `50 < weight <= 65` | | `@159–@193 L262-L263` | C |
| band: Emaciated | `weight <= 50` | **inclusive** | `@194–@217 L265-L266` | C |
| band re-check period | every **2000** `updateWeight` calls | server-side only | `updateWeight @329–@357 L200–L203` | C |
| `applyWeightFromTraits` | 50 / 60 / 70 / 95 / 105 kg | Emaciated / V.Under / Under / Over / Obese | `@0–@100 L226–L238` | C |
| `characterHaveWeightTrouble` | Emaciated ∨ Obese ∨ V.Under (**twice**) ∨ Overweight | Underweight never counted — bug | `@0–@70 L271` | C |
| `canAddFitnessXp`, Fitness ≥ 9 | blocked by any weight trouble (adds Overweight) | | `@0–@23 L275-L276` | C |
| `canAddFitnessXp`, Fitness 6–8 | blocked by Emaciated / Obese / V.Under only | | `@24–@83 L277-L278` | C |
| run speed, Obese | ×**0.85** | only while the speed factor already > 1 | `IsoPlayer.updateInternal2 @2061–@2079 L2647-L2648` | C |
| run speed, Overweight | ×**0.99** | | `@2042–@2060 L2644-L2645` | C |
| run speed, raw weight | `weight > 120` → ×**0.97** | the only direct weight read outside `Nutrition` | `@2080–@2099 L2650-L2651` | C |
| endurance drain mult, base | 1.4 (then ×2.3, ×pacing, ×hyperthermia) | | `IsoPlayer.updateEndurance @109–@165 L3450–L3460` | C |
| endurance drain mult, Overweight | **2.9** | Obese has **no** endurance branch | `@114–@131 L3451-L3452` | C |
| endurance drain mult, Athletic | 0.8 | | `@132–@149 L3454-L3455` | C |
| `getRecoveryMod` Fitness curve | 0.7 → 1.6 over Fitness 0–10 | | `getRecoveryMod @8–@110 L4616–L4647` | C |
| `getRecoveryMod` Obese / Overweight / V.Under / Emaciated | ×0.4 / ×0.7 / ×0.7 / ×0.3 | | `@111–@186 L4649–L4659` | C |
| `getRecoveryMod` lipid/protein deficit | ×0.5 below −1000, ×0.2 below −1500 | **unreachable** — store clamps at −500 | `@187–@236 L4663–L4667` + `setLipids @1/@12` | C+M+I |
| climb-fail score, Obese / Overweight | −25 / −15 (`else if`) | | `getClimbingFailChanceFloat @113–@153 L17330–L17333` | C |
| rope-climb tier, Obese / Overweight | −2 / −1 (`else if`) | tier clamped 0–10 | `getClimbRopeSpeed @68–@102 L17412–L17415` | C |
| grapple, V.Under / Emaciated / Overweight / Obese | ×0.8 / ×0.6 / ×**1.10** / ×**1.05** | only positive weight modifiers in the game | `calculateGrappleEffectivenessFromTraits @21–@77 L8722–L8731` | C |
| fall damage, Obese ∨ Emaciated | ×1.4 | | `handleLandingImpact @210–@244 L2227-L2228` | C |
| fall damage, Overweight ∨ V.Under | ×1.2 | | `@247–@280 L2229-L2230` | C |
| landing severity, Obese ∨ Emaciated / Overweight ∨ V.Under | +20 / +10 | | `@664–@724 L2295–L2298` | C |
| window-lunge score, V.Under / Obese / Overweight | +30 (20 + 10, duplicated) / −10 / −5 | `max(5, n)` at the end | `attackFromWindowsLunge @295–@365 L15210–L15226` | C |
| vault-fall %, V.Under / Obese / Overweight | +30 (duplicated) / +20 / +10 | `Rand.Next(100) < n − Fitness` | `ClimbOverFenceState.shouldFallAfterVaultOver @178–@259 L582–L597` | C |
| bump-trip score, V.Under / Under / Obese / Overweight | −8 / −4 / −8 / −4 | base `10 − 3·bumpNbr + Fitness + Strength − 2·DRUNK`, clamp `[1, 80]`, trip if `Rand.Next(n) == 0` | `IsoMovingObject.separate @694–@897 L1344–L1376` | C |
| script `XPBoosts` | Obese −2, Overweight −1, Underweight −1, V.Under −2, Emaciated **none** | starting Fitness offset | `character_traits.txt:743/788/978/1002/281` | C |
| `WeightGain` / `WeightLoss` granted traits | `overweight` / `underweight` | at creation | `character_traits.txt:1044/1055` | C |
| gain threshold | `1000 + (weight − 80)·40` | slice 01, re-read unchanged | `updateWeight @77–@94 L157-L158` | C |
| gain threshold, Weight Gain (`w < 90`) | base **700** | | `updateWeight @21–@48 L149-L150` | C |
| gain threshold, Weight Loss (`w > 70`) | base **1800** | | `updateWeight @49–@76 L152-L153` | C |
| lose threshold | `min(0, (weight − 70)·30)` | slice 01 | `updateWeight @95–@112 L159-L160` | C |
| weight loss rate | `8.5e-6 · min(1, \|cal\|/2500)` | ≤0.646 kg/game-day after the −2200 clamp | `updateWeight @260–@306 L186–L193` | C+I |
| `HUNGRY` moodle thresholds | 0.15 / 0.25 / 0.45 / 0.70 | strict `>` | `MoodleStat.<clinit> @64–@79 L13` | C |
| `THIRST` moodle thresholds | 0.12 / 0.25 / 0.70 / 0.84 | strict `>` | `MoodleStat.<clinit> @172–@187 L19` | C |
| `HEAVY_LOAD` moodle thresholds | 1.0 / 1.25 / 1.5 / 1.75 | carry ratio, not body weight | `MoodleStat.<clinit> @352–@366 L29` | C |
| `FOOD_EATEN` thresholds | timer > 0 / 1600 / 3200 / 4800 | `standardHealthFromFoodTime = 1600` | `Moodle.Update @2331–@2454 L437–L447`; `BodyDamage.<init> @97–@100 L80` | C |
| `healthFromFoodTimer` fill | `\|hungerChange\| · f · 13000`, ×2 if cooked, cap **11000** | from hunger, not calories | `JustAteFood @454–@538 L650–L660`; `getHealthFromFoodTimeByHunger @0 L754` | C |
| `healthFromFoodTimer` decay | `−1 × GameTime.getMultiplier()` per tick | | `BodyDamage.Update @575–@590 L2273` | C |
| eat gate | `FOOD_EATEN >= 3` blocks eating and drinking | | `ISEatFoodAction.lua:14`, `ISDrinkFluidAction.lua:7` | C |
| carry-capacity penalty | HUNGRY lvl 2/3/4 → −1/−2/−2 kg; THIRST identically | additive with SICK/BLEEDING/INJURED | `BodyDamage.UpdateStrength @2–@121 L2062–L2078`, `@302–@327 L2113` | C |
| health regen additions | 0.002 / 0.0013 / 0.0008 / 0.0 (standard / reduced / severely / none) | tier from `max(HUNGRY, SICK, THIRST)` level | `BodyDamage.Update @752–@838 L2301–L2312`; `<init> @61–@75 L74–L76` | C, tier map I |
| sleeping health addition | 0.02, **zeroed** if HUNGRY or THIRST is level 4 | | `BodyDamage.Update @875–@924 L2320–L2323`; `<init> @79–@81 L77` | C |
| health loss at HUNGRY level 4 | `0.0165 / 50` = **3.3e-4** per multiplier unit | | `BodyDamage.Update @1151–@1172 L2357-L2358`; `<init> @91–@93 L79` | C |
| `FOOD_EATEN` poison bonus | extra `1.5e-4 × level` poison decay | | `BodyDamage.Update @1044–@1090 L2350–L2353` | C |
| moodle levels | 0 Min / 1 Low / 2 Moderate / 3 High / 4 Max | | `Moodle$MoodleLevel.<clinit>` | C |
| `Nutritionist` / `Nutritionist2` | **display only** | sole reader | `Food.DoTooltip @1269–@1291 L1522` | C |
| `"CalculateStats"` Lua hook | returning true skips endurance, tripping, thirst, stress, **hunger**, morale, fitness | | `IsoGameCharacter.calculateStats @49–@59 L10204-L10205` | C |
| `"AutoDrink"` Lua hook | returning true skips autoDrink | | `autoDrink @88–@98 L11739-L11740` | C |

---

## Experiment inputs (for the later live dispatch)

### Where to sample and how often

1. **Sample on the SERVER.** Hunger, thirst, endurance, calories, macros and weight are
   all server-authoritative in MP (Q7). Client reads are a mirror lagging up to the 1 Hz
   `PlayerStatsPacket`. Reuse the slice-01 harness pattern: server-side
   `nutrition.set` / `stats.set` to prime, server-side reads to assert, client reads only
   as a convergence witness.
2. **Sample at 1 Hz for ≥ 300 s of wall time per condition.** The rates are 1e-6-scale per
   game-second; at the fixture's ≈16 game-s per real-s, hunger moves ~1.5e-4 per real
   second, so a 300 s window moves ~0.047 — comfortably above float noise, and short
   enough that the `(1 − H)` damping stays within 5 % of linear.
3. **Freeze the confounders** each run: `settimespeed 1`, player standing still indoors at
   a neutral temperature (so `energyMultiplier`/`fluidsMultiplier` stay at 1.0), no timed
   action queued (`caloriesModifier` would replace `mod`), `FOOD_EATEN` level 0 (wait out
   `healthFromFoodTimer`, or assert it is 0 before starting).

### Scale-free ratio tests (preferred — no dependence on the game-second scale)

Sample `calories`, `hunger`, `thirst`, `weight` in the same tick and compare **ratios**;
these hold whatever `minutesPerDay` and framerate the fixture uses. All are predictions
from C constants:

| Ratio | Predicted value (idle, no traits, sandbox `StatsDecrease = 3`) |
|---|---|
| `Δthirst / Δhunger` | `8.0e-6 / (9.6e-6 · (1 − H))` = **0.8333 / (1 − H)** |
| `Δcalories / Δhunger` | `0.016·(w/80) / (9.6e-6 · (1 − H))` = **1666.7 · (w/80) / (1 − H)** |
| `Δcarbs / Δcalories` (idle) | `0.0035 / (0.016·(w/80))` = **0.21875 / (w/80)** |
| `Δhunger(asleep) / Δhunger(idle)` | `1.0e-6 / 9.6e-6` = **0.10417** |
| `Δthirst(asleep) / Δthirst(idle)` | `1.0e-6 / 8.0e-6` = **0.125** |
| `Δcalories(running) / Δcalories(idle)` | `0.13 / 0.016` = **8.125** |
| `Δcalories(sprint) / Δcalories(idle)` | `0.169 / 0.016` = **10.5625** |
| `Δcalories(walk) / Δcalories(idle)` | `0.078 / 0.016` = **4.875** |
| `Δcalories(idle, swiping) / Δcalories(idle)` | **8.0** |
| `Δcalories(idle) at w=100 / at w=80` | **1.25** |

Establish the fixture's game-seconds-per-real-second **once** from the idle calorie burn
(`gsPerRealSec = Δcal_perRealSec / (0.016 · weight/80)`), then every absolute prediction
below follows.

### Absolute predictions once the scale factor is known

With `S` = game-seconds per real second (≈16.2 on the slice-01 fixture):

- idle calories: `0.016 · (w/80) · S` kcal/real-s (slice 01: 0.259 at w≈81)
- idle hunger: `9.6e-6 · (1 − H) · M · S` per real-s (`M` = StatsDecrease multiplier)
- awake thirst: `8.0e-6 · M · S · fluidsMult · runMod` per real-s
- asleep calories: `0.003 · (w/80) · energy · S`
- running calories: `0.13 · (w/80) · S`

### The matrix to run

| # | Condition | Set on the server | Read | Asserts |
|---|---|---|---|---|
| 1 | idle baseline | nothing; wait `FOOD_EATEN == 0` | cal, hunger, thirst, carbs, weight @1 Hz ×300 s | all ratios above; establishes `S` |
| 2 | asleep | force sleep | same | calorie ratio 0.1875 (0.003/0.016), hunger 0.10417, thirst 0.125 |
| 3 | walking | scripted walk loop | cal, hunger | calories ×4.875; hunger *still* the idle 9.6e-6 (walking is **not** "exercising") |
| 4 | running | scripted run loop | cal, hunger, thirst, endurance | calories ×8.125; hunger drops to `6.4e-6·(1−H)` (×0.6667 of idle) while `FOOD_EATEN == 0`; thirst ×1.2 **only if** `IsoPlayer.getInstance() == this` — this row settles that open item |
| 5 | swiping in place | attack a fence/wall while stationary | cal | calories ×8.0 |
| 6 | timed action | queue an `ISBuildAction` (`caloriesModifier = 8`) while stationary | cal | calories ×8.0 (proves the action path, distinct from row 5) |
| 7 | weight scaling | `nutrition.set weight 100`, then `120`, then `60` | cal | ×1.25, ×1.50, ×0.75 vs w80 |
| 8 | `FOOD_EATEN` gate | eat a large item, then sample | hunger, `getMoodleLevel(FOOD_EATEN)` | hunger rate → **0** while level ≥ 1 and idle; jumps to `1.92e-5·(1−H)` if the player then runs |
| 9 | traits | Hearty Appetite / Light Eater / HighThirst / LowThirst | hunger, thirst | ×1.5 / ×0.75 / ×2 / ×0.5 |
| 10 | sandbox | `StatsDecrease` 1..5 | hunger, thirst, cal | hunger/thirst ×2.0/1.6/1.0/0.8/0.65; **calories unchanged** (`updateCalories` reads no sandbox multiplier) — also settles the key↔value mapping |
| 11 | moodle sweep | `stats.set hunger` to 0.10, 0.16, 0.26, 0.46, 0.71; same for thirst at 0.10, 0.13, 0.26, 0.71, 0.85 | `getMoodleLevel` | levels 0,1,2,3,4 in order |
| 12 | weight-band sweep | `nutrition.set weight` to 45, 50, 55, 65, 70, 75, 80, 85, 95, 100, 105 | `hasTrait(...)`, `getMaxWeight`, run speed | band boundaries **inclusive at 50 and 100**; needs the ≤2000-tick trait refresh (see caveat) |
| 13 | MP authority | client-side `stats.set hunger 0.9` and `thirst 0.9` | server + client @1 Hz ×5 s | client value reverts within the 1 Hz push (already M in slice 01 — a regression check only) |
| 14 | client weight write | client-side `nutrition.set weight 105` | client `getWeight()`, `hasTrait(Obese)`, server weight | **new prediction:** the client write survives only until the next packet, and `applyTraitFromWeight` never fires client-side |

### Exact Lua to use

```lua
-- moodle levels (enum names confirmed against the jar and media/lua)
local m = getPlayer():getMoodles()
m:getMoodleLevel(MoodleType.HUNGRY)      -- 0..4
m:getMoodleLevel(MoodleType.THIRST)      -- note: THIRST, not "THIRSTY"
m:getMoodleLevel(MoodleType.FOOD_EATEN)
m:getMoodleLevel(MoodleType.HEAVY_LOAD)
m:getMoodleLevel(MoodleType.ENDURANCE)

-- stats (no getHunger()/getThirst() exists in B42)
local s = getPlayer():getStats()
s:get(CharacterStat.HUNGER); s:get(CharacterStat.THIRST)
s:get(CharacterStat.ENDURANCE); s:get(CharacterStat.FATIGUE)
s:set(CharacterStat.HUNGER, 0.46)        -- server-side only; clamped [0,1]

-- nutrition
local n = getPlayer():getNutrition()
n:getCalories(); n:getCarbohydrates(); n:getProteins(); n:getLipids(); n:getWeight()
n:setCalories(2500); n:setWeight(105.0)  -- server-side only

-- weight traits
local p = getPlayer()
p:hasTrait("Obese"); p:hasTrait("Overweight"); p:hasTrait("Underweight")
p:hasTrait("Very Underweight"); p:hasTrait("Emaciated")   -- note the SPACE in "Very Underweight"

-- food-eaten timer (drives the FOOD_EATEN moodle)
local bd = p:getBodyDamage()
bd:getHealthFromFoodTimer(); bd:getStandardHealthFromFoodTime()   -- expect 1600

-- carry capacity (the one measurable Hungry/Thirsty effect)
p:getMaxWeight()

-- sandbox
getSandboxOptions():getOptionByName("StatsDecrease"):getValue()
```

### Caveats the harness must handle

- **Weight traits refresh lazily.** `applyTraitFromWeight` runs only every 2000
  `updateWeight` calls (`updateWeight @339–@357 L201–L203`). After a `setWeight`, either
  wait out the counter or call `getNutrition():applyTraitFromWeight()` directly — it is a
  public no-arg method and is Lua-reachable.
- **The trait string for Very Underweight contains a space** (`'Very Underweight'`,
  `CharacterTrait.<clinit> @769 L97`) and Out of Shape likewise (`'Out of Shape'`).
- **`nutrition.set weight` and `stats.set` must go to the server bus.** A client write to
  either is discarded within 3 s (M, slice 01).
- **`hungerIncreaseWhenWellFed = 0` will read as an exactly flat hunger series** in row 8 —
  assert equality, not a small slope.
- **Row 4's thirst multiplier may not fire on a dedicated server** — that is the point of
  the row; a null result there confirms the `IsoPlayer.getInstance()` gate.
- **Prime `FOOD_EATEN` to 0 before every hunger row.** The moodle survives across
  conditions for up to 11000/`multiplier` ticks and silently zeroes the hunger rate.

---

## Open / uncertain

1. **`getStatsDecreaseMultiplier` key↔value mapping is inferred.** pzdis does not print
   the `tableswitch` jump table. The values (2.0 / 1.6 / 0.8 / 0.65, default 1.0) and the
   option shape (`newEnumOption("StatsDecrease", 5, 3)`) are C; the pairing
   `1→2.0, 2→1.6, 3→1.0, 4→0.8, 5→0.65` is I. Row 10 of the matrix settles it.
2. **`BodyDamage.Update` health-tier switch mapping is inferred** for the same reason:
   which of `n ∈ {−1,0,1,2,3}` maps to standard / reduced / severely-reduced / zero. The
   four bodies and the constants are C.
3. **`getRunningThirstReduction` on a dedicated server.** It is gated on
   `this == IsoPlayer.getInstance()`; on a headless server that is probably never true, so
   running may not increase thirst in MP at all. Unmeasured.
4. **Split-screen / secondary players.** `updateStats_WakeState` and `updateThirst` run in
   SP only when `IsoPlayer.getInstance() == this`. Whether players 2–4 in split-screen
   therefore never accrue hunger/thirst locally is unverified — it depends on what
   `IsoPlayer.getInstance()` returns during their update pass.
5. **Do the weight traits reach an MP client at all?** `applyTraitFromWeight` never runs
   client-side (`updateWeight @317 L198`), and `PlayerStatsPacket` carries `Stats`,
   `Nutrition`, `timeSinceLastSmoke` and `BodyDamage.saveMainFields` — **not**
   `CharacterTraits`. `CharacterTraits` has `write`/`read` methods, so some other packet
   presumably carries them, but that path was not traced. If it is not synced, client-side
   run speed, climb and fall-damage modifiers would disagree with the server. Row 14.
6. **`Nutrition.caloriesMax` / `caloriesMin`** (`updateCalories @319–@358 L121–L125`)
   are still maintained with no reader found — unchanged from the slice-01 open list.
7. **`primTotal` / `secTotal` range** is unknown, so the numeric size of the
   thermoregulator energy multiplier is unbounded here. `updateNodes @593–@600 L1088-L1089`
   writes them from a loop I did not fully trace. Practical impact: the cold-weather
   burn bonus is `1 + 0.05·p² + 0.10·s²` but I cannot say how large `p`, `s` get.
8. **`Moodles.Update` has no side guard**, so both sides recompute moodles from their own
   stats. On a client whose stats are 1 s stale this should be harmless, but a moodle-level
   read taken client-side immediately after a server stat write may lag — worth a note if
   any experiment reads moodle levels client-side.
9. **`applyWeightFromTraits` write order.** Sequential `if`s, so a character created with
   two weight traits (blocked by `MutuallyExclusiveTraits` in the UI, but a mod could do
   it) ends at the last matching branch. Not exercised.
10. **`healthFromFoodTimer` decay unit.** It decays by `1 × GameTime.getMultiplier()` per
    `BodyDamage.Update`, i.e. per *frame-normalised* tick, not per game-second — so the
    `FOOD_EATEN` moodle's real duration depends on framerate and time speed differently
    from every other rate in this document. Unmeasured; it matters for row 8's timing.
