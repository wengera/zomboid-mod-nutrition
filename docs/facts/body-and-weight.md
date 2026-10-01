# Body and weight
Verified against 42.20.4 (b0bbce05d5) · 2026-10-01 · scope: what the body does with the stores between meals — passive burn, the engine's metabolic-rate classes, hunger, thirst, the moodles, the weight bands and the traits that scale them; intake and the weight formula itself are handed off.

## Key facts

- Every rate on this page is per game-world second, of which a game day holds 86 400 [#0451].
- Calorie burn at rest is 0.016 kcal per game-second at 80 kg, 1 382.4 per game-day, and scales linearly with weight over 80 [#0455, #0461/M/n=1].
- Hunger and thirst are separate needs on `[0,1]`, read through `getStats():get(CharacterStat.HUNGER)` and the `THIRST` enum; there is no `getHunger()` on `Stats` in this build [#0467/M].
- Awake, idle and with no food-eaten moodle, hunger rises at 9.6e-6 per game-second times one minus the current hunger, so it approaches its maximum and never reaches it [#0470/M/n=1, #0474/M/n=1].
- Awake thirst rises at 8.0e-6 per game-second with no damping term and reaches its maximum in 34.72 game-hours [#0476/M/n=1, #0496/C/arith.].
- Nothing scales the calorie burn but the character's weight: across 60 to 120 kg the hunger and thirst rates stayed flat at 0.9999 to 1.0000 of prediction while calories tracked 0.75, 1.25 and 1.50 times the 80 kg rate [#0488/M/n=1].
- While the `FOOD_EATEN` moodle is up and the character is not exercising, the hunger constant is 0 and hunger freezes bit-exactly [#0473, #0524/M/n=1].
- The `HUNGRY` moodle fires above 0.15, 0.25, 0.45 and 0.70, and `THIRST` above 0.12, 0.25, 0.70 and 0.84, on a strict greater-than [#0508/M/n=1, #0509/M/n=1].
- A level-4 thirst costs 11.88 health per game-hour on the 60-minute default day and 17.82 on a 90-minute one, five times the level-4 hunger term [#0518/C/arith.].
- The weight bands are inclusive at both ends — Emaciated at 50 kg or less, Obese at 100 or more — with no band trait at all in the open interval between 75 and 85 [#0531/M/n=1].
- A band trait is re-applied only once every 2000 weight updates, so the trait lags the weight [#0534/C/C-only].
- The body side has two sandbox options: `StatsDecrease`, an enum of 1 to 5 defaulting to 3 and mapping to 2.0, 1.6, 1.0, 0.8 and 0.65, and the boolean `Nutrition` [#0483/M/n=1, #0555].
- The macro stores drain alongside the calories, carbohydrates at 0.0035, lipids at 0.00113 and proteins at 0.00086 per game-second [#0069/M/one-fixture].
- A weight band reaches the rest of the game through 14 jar readers outside `Nutrition`, none of them measured [#0541/C/C-only].

## How it works

<a id="time-unit"></a>
### The time unit

Every body-side rate is stated per game-world second, of which a game day holds 86 400, and the two rate idioms in the code — `Nutrition`'s `getGameWorldSecondsSinceLastUpdate()` and `IsoGameCharacter`'s `getMultiplier()` times `getDeltaMinutesPerDay()` — reduce to the same quantity because `GameTime.multiplierBias` is 1.0 [#0451].
Two quantities on this page do not carry the second factor and therefore scale with the day length instead: the severe-moodle health terms and the health-from-food timer, both stated at their own anchors.

A rate quoted per real second belongs to the time-speed setting and not to the model, so every rate figure below is stated in game time and the wall-clock readings say so; a reading taken at an accelerated speed is then directly comparable with a baseline one [#0451].

<a id="passive-burn"></a>
### Passive burn

`Nutrition.updateCalories` computes a modifier from the first queued character action and from the swipe and climb states, reads the thermoregulator energy multiplier, then tests five mutually exclusive branches in one fixed order — running while moving, sprinting while moving, moving, asleep, otherwise idle — and subtracts rate times mod times weight-over-80 times the elapsed game-seconds from the calorie store [#0453].

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

The modifier is written in that order and then overwritten: the first queued action's `caloriesModifier`, then 8.0 in the swipe, fence-climb and window-climb states, then 1.0, 1.3 or 0.6 on the three moving branches, so a timed action's modifier and the climb override reach the burn only while the character is not moving [#0462] [#0453] [#0070/M/one-fixture].
Every branch is scaled by the character's weight over 80, and the thermoregulator's energy multiplier enters the asleep and idle branches only [#0187/C/C-only] [#0453].

The five branches, their rate at 80 kg and the per-game-day figure each implies, with the weight ratio the character's weight over 80 and the external modifier 8.0 while swiping or climbing and otherwise the queued action's `caloriesModifier`; only the idle branch is measured, and that reading is a wall-clock one taken on a fixture whose clock runs 16.0 game-seconds to the real second: 0.259 kcal per real second at time speed 1, and 0.256 in an earlier run [#0070/M/one-fixture].

| Branch | kcal per game-second at 80 kg | kcal per game-day | external modifier reaches it | thermoregulator energy reaches it | Row |
|---|---|---|---|---|---|
| asleep | 0.003 | 259.2 | yes | yes | [#0454] |
| idle | 0.016 | 1 382.4 | yes | yes | [#0455] |
| walking | 0.13 × 0.6 = 0.078 | 6 739.2 | no — overwritten to 0.6 | no | [#0457/C/C-only] |
| running | 0.13 | 11 232 | no — overwritten to 1.0 | no | [#0458/C/C-only] |
| sprinting | 0.13 × 1.3 = 0.169 | 14 601.6 | no — overwritten to 1.3 | no | [#0459/C/C-only] |
| idle while swiping or climbing, and idle under `ISBuildAction` | 0.128 | 11 059.2 | modifier 8 | yes | [#0460/C/C-only] |
| idle under `ISReadABook` | 0.008 | 691.2 | modifier 0.5 | yes | [#0460/C/C-only] |
| idle at 100, 120 and 60 kg | 0.020 / 0.024 / 0.012 | 1 728 / 2 073.6 / 1 036.8 | yes | yes | [#0461/M/n=1] |

Only the idle branch is measured; the moving and asleep branches are read from the code, and the per-game-day column is arithmetic on the coded constant [#0454, #0455].
The walking branch was not measured because the run's server saw the moving flag in only a handful of samples, and the running and sprinting branches were never entered at all, so their constants stand on the bytecode alone [#0457/C/C-only, #0458/C/C-only].
Neither the swipe and climb path nor the timed-action path was measured either: both need a real target or a real build site, and neither is one harness command [#0460/C/C-only].

Measured idle calorie burn runs at 1.0049 times the coded rate, r-squared 1.000000, over 233 samples and 1.420 game-hours on one uncontrolled fixture, so the excess reads as a character sitting very slightly cold rather than as a constant [#0456/M/n=1].
The weight term is measured across the band: the ratios against 80 kg came back 1.2496, 1.4991 and 0.7503 against a predicted 1.25, 1.50 and 0.75, at 24 samples per weight window [#0461/M/n=1].
Idle burn re-measured at a second cadence gives minus 1 408.1, minus 1 385.0 and minus 1 399.7 kcal per game-day across three server runs against minus 1 402.5, minus 1 379.5 and minus 1 390.2 predicted at each run's interval-mean weight, within 0.4 to 0.7 per cent — cross-checks fitted off the same samples rather than assertions [#0167/M/one-fixture].

The thermoregulator's energy multiplier and the swipe, climb and timed-action modifier reach the asleep and idle branches only: the energy term is loaded in those two branches and nowhere else, so cold raises resting burn and does nothing to moving burn, and all three moving branches overwrite the modifier before using it, so the swipe and climb constant of 8.0 and every timed action's `caloriesModifier` are rest-only in practice [#0187/C/C-only, #0462/C/none].
`caloriesModifier` defaults to 1 on `ISBaseTimedAction` and takes 30 assignments in the install's Lua with six distinct values, counted once on 2026-09-10: 0.5 for reading, researching and resting, 2 for dismantling, 3 for `ISFitnessAction`, 4 for building stages, painting, wallpapering, harvesting, shovelling and fixing, 5 for plowing, cleaning blood and graffiti and filling graves, and 8 for `ISBuildAction`, plastering, barricading, chopping trees and breaking glass [#0463/C/snapshot].
The values span 0.5, on reading, researching and resting, to 8, on building, plastering, shovelling ground, lighting a kindling fire, barricading, chopping trees, destroying, pickaxing ground cover and clearing broken glass, around the default of 1 [#2638/C/C-only].

A server-side reader of the modifier has three facts to work with.
`BaseAction` is not in the exposer's class set while `LuaTimedActionNew` is, so the Java field is not reachable from Lua, and a Lua-created action's modifier is the `caloriesModifier` key of the table its `getTable` returns [#2640/C/C-only].
The action's type name is `getMetaType`, which returns the `Type` string of the action table's metatable, or the empty string when there is no table or no metatable [#2639/C/C-only].
`ISTimedActionQueue` is defined in a client file a dedicated server does not load, so the server's view of a character's actions is the Java stack `getCharacterActions()`, the same stack the burn reads; whether that stack holds a connected client's action is not measured [#2641/C/C-only].

Alongside the calorie burn, `Nutrition.update` drains carbohydrates by 0.0035, lipids by 0.00113 and proteins by 0.00086 per game-world second; only the carbohydrate rate is fitted, at 0.00347 per game-second over a control window, 99.0 per cent of the coded rate [#0069/M/one-fixture].
Over three game-days the carbohydrate drain measured minus 302.4 per game-day against the coded rate times a game-day, exact in both whole traces and in the first run's alive window [#0168/M/one-fixture].
Sustained running at the running branch's rate crosses the whole 5 900 kcal range of the calorie store in about 12.6 game-hours, arithmetic on the coded constant and the store clamps ([nutrition-core.md#clamps](nutrition-core.md#clamps)) [#0465/C/arith.].
`Nutrition.update` returns early for a dead or god-mode character, and its only caller is the second internal player update step, itself gated by the character-stats disabler [#0466].
The store this burn drains is clamped at both ends, so an idle starving character reaches the floor and the burn stops mattering ([nutrition-core.md#clamps](nutrition-core.md#clamps)).

<a id="metabolic-rate"></a>
### The metabolic-rate classes

The engine carries its own activity scale: `Metabolics` is a 24-value enum of activity classes in MET, in the exposer's class set, with the getters `getMet`, `getWm2`, `getW` and `getBtuHr` and the static converters `MetToWm2`, `MetToW` and `MetToBtuHr` [#2631/C/C-only].
The exposure is read from the exposer's constant pool rather than from a read of the exposer dump end to end [#2631/C/C-only].

The 24 classes and their values in MET, as the enum's static initialiser writes them [#2632/C/C-only]:

| Class | MET | Class | MET |
|---|---|---|---|
| `Sleeping` | 0.8 | `LightWork` | 3.2 |
| `SeatedResting` | 1.0 | `MediumWork` | 3.9 |
| `StandingAtRest` | 1.1 | `JumpFence` | 4.0 |
| `SedentaryActivity` | 1.2 | `DiggingSpade` | 5.5 |
| `DrivingCar` | 1.4 | `Fitness` | 6.0 |
| `Default` | 1.5 | `HeavyWork` | 6.0 |
| `LightDomestic` | 1.6 | `Running10kmh` | 6.9 |
| `Walking2kmh` | 1.9 | `ClimbRope` | 8.0 |
| `HeavyDomestic` | 2.0 | `ForestryAxe` | 8.0 |
| `UsingTools` | 2.5 | `FitnessHeavy` | 9.0 |
| `DefaultExercise` | 3.0 | `Running15kmh` | 9.5 |
| `Walking5kmh` | 3.1 | `MAX` | 10.3 |

`Thermoregulator.updateMetabolicRate` starts every update from `Default` and raises its target through a setter that keeps the larger value and caps it at `MAX`: a weapon-type-keyed class while attacking, `Running15kmh` while moving and sprinting, `Running10kmh` while moving and running, `Walking2kmh` while moving and sneaking, `Walking5kmh` while moving with `currentSpeed` above 0, and `Fitness` while an exercise is current [#2633/C/C-only].
Each class is therefore a floor rather than an assignment: the exercise class never lowers a sprinting target, and among the classes the highest one that applies sets the floor the next two terms start from [#2633/C/C-only].
The target is then raised twice more through the same setter: to at least `clamp01(1 - endurance)` times `DefaultExercise` times the thermoregulator's `getEnergy()`, so a tired character's target can sit above a class below that floor, which tops out at `DefaultExercise` times the energy, and then by the factor `1 + 0.35 × clamp01(carried weight / max weight)²`, so a loaded character's target rises up to 1.35 times, capped at `MAX` [#2649/C/C-only].
So the target can differ from the class when the character is tired or loaded, and a reading of the rate against a class has to hold endurance and load still or account for both [#2649/C/C-only].
The exercise class is the flat `Metabolics.Fitness` at 6.0, never the exercise's own `metabolics`; a per-exercise class such as `FitnessHeavy` at 9.0 reaches the thermoregulator through `ISFitnessAction:update`'s per-frame `setMetabolicTarget`, the timed action [exercise-and-training.md#exercise-path](exercise-and-training.md#exercise-path) describes [#2634/C/C-only].
`IsoGameCharacter` declares no metabolic-rate getter, only the two `setMetabolicTarget` overloads, so the rate is read through `getBodyDamage():getThermoregulator()`, whose `getMetabolicRate`, `getMetabolicTarget` and `getMetabolicRateReal` are public [#2635/C/C-only].
The classification is read from the bytecode and never measured, and whether a connected player's thermoregulator is classified on the server at all is open below [#2633/C/C-only].

<a id="hunger-thirst"></a>
### Hunger and thirst

Hunger and thirst are read through `getStats():get(CharacterStat.HUNGER)` and the `THIRST` enum, both on `[0,1]` with default 0; there is no `getHunger()` on `Stats` in this build, an absence that rests on the class's 34-method list [#0467/M].
`IsoGameCharacter.updateInternal` calls `calculateStats()`, which runs `updateThirst()` and `updateStats_WakeState()` — itself picking the awake or the sleeping updater — alongside endurance, tripping, stress, morale and fitness [#0468].
That dispatcher is also the cleanest interception point a mod has on this side, which is the Lua platform page's business ([../platform/lua-platform.md#hooks](../platform/lua-platform.md#hooks)).

| Constant | Value per game-second | Where it applies | Row |
|---|---|---|---|
| `HungerIncrease` | 9.6e-6 | awake, no `FOOD_EATEN` moodle, not exercising | [#0470/M/n=1] |
| `HungerIncreaseWhenExercise / 3` | 6.4e-6 | exercising with no `FOOD_EATEN` moodle — below the idle rate | [#0471/C/C-only] |
| `HungerIncreaseWhenExercise` | 1.92e-5 | exercising with the moodle up — twice idle | [#0471/C/C-only] |
| `HungerIncreaseWhileAsleep` | 1.0e-6 | asleep, no `FOOD_EATEN` moodle | [#0472/C/C-only] |
| `HungerIncreaseWhenWellFed` | 0 | not exercising with the moodle up, awake or asleep — hunger freezes | [#0473] |
| `ThirstIncrease` | 8.0e-6 | awake; linear, no damping term | [#0476/M/n=1] |
| `ThirstSleepingIncrease` | 1.0e-6 | asleep; neither the running term nor the heat term applies | [#0477/C/C-only] |
| `ThirstLevelToAutoDrink` | 0.1 | the level thirst must exceed for an auto-drink | [#0480/C/C-only] |
| `ThirstLevelReductionOnAutoDrink` | 0.1 | the amount an auto-drink removes | [#0480/C/C-only] |

Exercising means running while moving, or swiping [#0471/C/C-only].
Neither exercising branch was measured, and the one that runs while the food-eaten moodle is down is the lower of the two: exercising on an empty stomach makes a character hungry more slowly than standing still does [#0471/C/C-only].

Both awake rates are measured on the dedicated-server path at one fixture: hunger fitted 7.4912e-6 against a predicted 7.4916e-6 at a mean hunger of 0.2196 with r-squared 0.99996, and thirst 7.99999e-6 at ratio 1.0000 with r-squared 1.000000, over 233 samples [#0470/M/n=1, #0476/M/n=1].
The asleep arms of both stats are read from the code and never measured, because the written sleep state did not persist in the run [#0472/C/C-only, #0477/C/C-only].
The appetite factor is one minus the current hunger and multiplies every hunger branch except the well-fed one, so hunger is the only stat that damps its own rate; the factor is required to fit every one of the run's 11 windows and tracks it to four significant figures [#0474/M/n=1].
The well-fed branch drops the appetite factor from the expression entirely, which is moot because its rate constant is 0 [#0499].
The auto-drink constants are read from the code and not measured [#0480/C/C-only].

Left alone, the thirst clock kills: a fed subject whose hunger and thirst were not pinned lost health from 100 to 0 starting at about 29.13 game-hours, at 17.820029 health per game-hour on a 90-minute-day fixture, and died at game-hour 35 [#0173/M/one-fixture].
The level-4 thirst crossing at about 29.13 game-hours is day-length independent because thirst accumulation carries the delta-minutes-per-day factor, while the health drain does not, so 100 health takes 8.4 game-hours at 11.88 per game-hour on the 60-minute default against 5.6 game-hours at 17.82 on a 90-minute day; the 60-minute arm is arithmetic on the measured one [#0175/C/arith.].

<a id="multipliers"></a>
### The multipliers

| Multiplier | What it multiplies | Value | Row |
|---|---|---|---|
| thermoregulator `energyMultiplier` | the asleep and idle calorie branches only | 1.0 plus 0.05 times the primary total squared when that total is negative, plus 0.10 times the secondary total squared when that total is negative — at least 1.0 always, raised only by cold | [#0464] |
| `getHungerMultiplier()` | nothing | a hard return of 1.0: there is no thermoregulator term on hunger | [#0475] |
| `getThirstMultiplier()` | the awake thirst branch alone | the thermoregulator's `fluidsMultiplier`, 1 plus 0.25 times the primary total squared plus 3.75 times the secondary total squared, hot side only | [#0478] |
| `getRunningThirstReduction()` | awake thirst while running | 1.2 — it raises thirst rather than reducing it — and gated on the character being the local player instance | [#0479/C/C-only] |
| trait Hearty Appetite / Light Eater | hunger and nothing else | 1.5 / 0.75 | [#0485/M/n=1] |
| trait High Thirst / Low Thirst | thirst and nothing else, on both branches, unconditionally | 2.0 / 0.5 | [#0486/M/n=1] |
| running against idle | the calorie burn | 8.125 | [#0487/C/arith.] |
| body weight | the calorie burn and nothing else | weight over 80 | [#0488/M/n=1] |

Heat raises the thirst and fatigue multipliers while cold raises the energy one, and the primary and secondary totals' real ranges were never traced, so the size of the cold-weather burn bonus is unbounded here [#0464].
Hunger carries no environmental term at all: its multiplier hook is a hard return, so the only things that scale hunger are the sandbox setting, the appetite factor and the two appetite traits [#0475, #0485/M/n=1].
`getAppetiteMultiplier` is the only reader of the two appetite traits in the jar and `updateThirst` the only reader of the two thirst traits; there is no trait called Thirsty [#0485/M/n=1, #0486/M/n=1].
The four trait multipliers are measured at one fixture with 24 samples per window: 0.9997 for Hearty Appetite, 1.0001 for Light Eater, 1.0000 for Low Thirst, and 0.9948 for High Thirst, whose window sat about 0.5 per cent low across all five needs and macros together, so that shortfall is the whole window rather than a thirst-specific error [#0485/M/n=1, #0486/M/n=1].
The running ratio is arithmetic on the coded running and idle constants; the running branch itself is unmeasured, and the running thirst factor is read from the code only [#0487/C/arith., #0479/C/C-only].

<a id="fill-times"></a>
### How fast each stat fills

Hunger is a first-order approach rather than a linear fill: its derivative is k times one minus hunger, with k the product of `HungerIncrease`, the sandbox multiplier and the appetite trait, so hunger follows one minus e to the minus k t [#0489].
The hunger time constant at default settings is 104 167 game-seconds, or 28.94 game-hours [#0490/C/arith.].
Thirst has no damping term and fills linearly [#0491].
The fill times below are arithmetic on the coded constants at the default `StatsDecrease` setting, awake, idle and with no `FOOD_EATEN` moodle; the value each milestone stands at is in brackets.

| Milestone | Hunger, plain | Hearty Appetite | Light Eater | Thirst, plain | High Thirst | Low Thirst | Row |
|---|---|---|---|---|---|---|---|
| moodle level 1 | 4.70 game-h (0.15) | 3.13 | 6.27 | 4.17 game-h (0.12) | 2.08 | 8.33 | [#0492/C/arith.] |
| moodle level 2 | 8.32 game-h (0.25) | 5.55 | 11.10 | 8.68 game-h (0.25) | 4.34 | 17.36 | [#0493/C/arith.] |
| moodle level 3 | 17.30 game-h (0.45) | 11.53 | 23.06 | 24.31 game-h (0.70) | 12.15 | 48.61 | [#0494/C/arith.] |
| moodle level 4 | 34.84 game-h (0.70) | 23.22 | 46.45 | 29.17 game-h (0.84) | 14.58 | 58.33 | [#0495/C/arith.] |
| maximum, 1.0 | asymptotic | asymptotic | asymptotic | 34.72 game-h | 17.36 | 69.44 | [#0496/C/arith.] |
| after one game-day | 0.5637 | 0.7118 | 0.4632 | 0.6912 | 1.0, clamped | 0.3456 | [#0497/C/arith.] |

Asleep, hunger rises 0.0864 times one minus hunger per game-day and thirst 0.0864 per game-day, arithmetic on constants whose branch was never measured [#0498/C/arith.].
Because thirst is linear, a thirst trait scales every thirst milestone by the same factor, while an appetite trait moves the hunger curve's time constant and therefore shifts each hunger milestone by a different amount [#0491, #0492/C/arith.].
The two curves also cross: thirst reaches its first moodle level before hunger does, and hunger reaches its last one before thirst does [#0492/C/arith., #0495/C/arith.].

<a id="coupling"></a>
### Where hunger and calories meet, and where they do not

Hunger never feeds the calorie burn: `updateCalories` reads the queued actions, three AI states, the thermoregulator, the character's weight and the game clock, and never reads `Stats` [#0500].
Calories never feed hunger: the awake and sleeping hunger updaters read appetite, the `FOOD_EATEN` moodle, the sandbox multiplier, the game clock and two traits, and never read `Nutrition` [#0501].
`setCalories` fills the `Nutrition` store and never touches `CharacterStat.HUNGER` or `THIRST`, observed as hunger and thirst rising through a run that dosed calories only [#0172/M/one-fixture].
Weight is the only quantity on this page that feeds back into another one.
Calories and weight form the one genuine feedback loop in the body model: `updateCalories` scales the burn by the character's weight over 80 and `updateWeight` moves weight out of the calorie store ([nutrition-core.md#weight-model](nutrition-core.md#weight-model)) [#0502].
The only link between the calorie store and hunger is indirect: the `FOOD_EATEN` moodle gates the hunger rate, and its timer is filled from the absolute hunger change of the food eaten rather than from its calories, with `getHealthFromFoodTimeByHunger` returning a flat 13000 [#0503].
So a zero-calorie item with a large hunger value suppresses hunger growth exactly as well as a large meal does, and a mod that adds its own stores can drive them from calories, from hunger or from neither without colliding with a vanilla coupling [#0503, #0500].

<a id="moodles"></a>
### The moodles

The Lua-visible moodle names are the static field names `MoodleType.HUNGRY`, `MoodleType.THIRST` — not `THIRSTY` — and `MoodleType.FOOD_EATEN`; their display strings are `Hungry`, `Thirst` and `FoodEaten`, and levels are `MoodleLevel` ordinals 0 to 4 from Min to Max, which `Moodles.getMoodleLevel` returns as an int [#0505/M/n=1].
There is no weight moodle: nothing weight-related is registered, and `HeavyLoad` is inventory encumbrance measured on the carry-weight ratio [#0506].
Only 20 of the 26 moodle types carry a `MoodleStat` at all, read from the type's member list on 2026-09-17 [#1199/C/C-only].
`Moodle.Update` evaluates thresholds with a plain greater-than in ascending order so the last match wins; the `HUNGRY` block is gated on the character's health being non-zero and the `THIRST` block carries no health gate [#0507].
Retuning one of these thresholds at runtime needs the stat object, and reaching it from Lua is the Lua platform page's wall ([../platform/lua-platform.md#registries](../platform/lua-platform.md#registries)).
Each side recomputes its own moodles from its own copy of the stats, so a moodle read on a client can lag a server write ([../platform/mp-model.md#what-a-client-copy-is](../platform/mp-model.md#what-a-client-copy-is)).

| Moodle | Driven by | Level 1 | Level 2 | Level 3 | Level 4 | Row |
|---|---|---|---|---|---|---|
| `HUNGRY` | `HUNGER` on `[0,1]` | 0.15 | 0.25 | 0.45 | 0.70 | [#0508/M/n=1] |
| `THIRST` | `THIRST` on `[0,1]` | 0.12 | 0.25 | 0.70 | 0.84 | [#0509/M/n=1] |
| `ENDURANCE` | endurance, inverted, minimum 0.75 | 0.5 | 0.25 | 0.10 | 0 | [#0510/C/C-only] |
| `HEAVY_LOAD` | the carry ratio | 1.0 | 1.25 | 1.5 | 1.75 | [#0510/C/C-only] |
| `FOOD_EATEN` | `BodyDamage.healthFromFoodTimer`, not a stat | 0 | 1600 | 3200 | 4800 | [#0511/M/n=1] |

Both hunger thresholds and both thirst thresholds read back correctly from probes either side of every level, and a timer of 197 597 read back as level 4; the endurance and heavy-load rows are read from the code only [#0508/M/n=1, #0509/M/n=1, #0510/C/C-only, #0511/M/n=1].
The 1600 that separates the first two food-eaten levels is the standard health-from-food time [#0511/M/n=1].

What each level does:

| Consumer | Effect | Row |
|---|---|---|
| `BodyDamage.UpdateStrength` | carry capacity: a `HUNGRY` level 2 adds 1 and levels 3 and 4 add 2, `THIRST` behaves identically, `SICK` 2, 3 and 4 add 1, 2 and 3, and bleeding and injured contribute likewise; the total is subtracted from the base max weight times the weight modifier and floored at 0 | [#0513/M/n=1] |
| `BodyDamage.Update` | the health-regeneration tier: `HUNGRY`, `SICK` or `THIRST` at level 2 gives tier 1, level 3 gives tier 2, `HUNGRY` or `THIRST` at level 4 gives tier 3 with `SICK` 4 absent from this branch, and being asleep gives tier minus 1; each tier selects one of the regeneration constants at [health-surfaces.md#regeneration](health-surfaces.md#regeneration) through the decoded switch stated there | [#0514/C/C-only] |
| `BodyDamage.Update` | while asleep, a `HUNGRY` or `THIRST` level of 4 zeroes the 0.02 sleeping health addition | [#0515/C/C-only] |
| `BodyDamage.Update` | the severe-moodle health loss: at `HUNGRY` level 4 the constant over 50, that is 0.0165 over 50 or 3.3e-4 per multiplier unit, and at `THIRST` level 4 the same constant over 10, 1.65e-3 per multiplier unit and five times the hunger one; both are added into one reduction total, which `ReduceGeneralHealth` applies whole to overall body health because the per-part division by max and by the damage modifier cancels against the overall-health sum | [#0516] |
| `BodyDamage.Update` | a `FOOD_EATEN` level above 0 speeds poison decay by 1.5e-4 times the level on top of the normal poison-level decrease | [#0520/C/C-only] |
| `ISEatFoodAction`, `ISDrinkFluidAction` | the eat and drink timed actions refuse to start at a `FOOD_EATEN` level of 3 or more | [#0521/C/C-only] |
| the inventory pane and its context menu | the eat and drink options are gated at a `FOOD_EATEN` level of 3 or more | [#0522/C/C-only] |

The zeroed sleeping health addition, the poison-decay term and the two eat blocks are read from the code and were not measured [#0515/C/C-only, #0520/C/C-only, #0521/C/C-only, #0522/C/C-only].
The carry-capacity ladder is measured: `getMaxWeight` read 12, 12, 11, 10 and 10 across levels 0 to 4 on the hunger and the thirst moodle independently [#0513/M/n=1].
The tier-to-constant mapping of the regeneration branch is a reading of the bytecode's switch, decoded at [health-surfaces.md#regeneration](health-surfaces.md#regeneration), and no tier was measured [#0514/C/C-only].
The severe-moodle health terms carry the game-time multiplier without the delta-minutes-per-day factor, so in game time they scale with the day length over 30: the `THIRST` level 4 term costs 11.88 health per game-hour on the 60-minute default day and 17.82 on a 90-minute one, and the `HUNGRY` level 4 term 2.376 and 3.564 respectively [#0518/C/arith.].
The thirst term is the measured one, at 17.820029 health per game-hour against a predicted 17.820000, a ratio of 1.000002, fitted as a least-squares slope over one run's health samples on a 90-minute-day fixture with the hunger moodle never above level 3 [#0519/M/arith.].
That run's hunger peaked at 0.699892 against a strict greater-than-0.70 threshold, so `HUNGRY` never rose above level 3 [#0174/M/one-fixture].
The strict comparison is what makes that possible: a stat that approaches a threshold without exceeding it never raises the level, which matters most for hunger, whose own curve is asymptotic [#0507, #0174/M/one-fixture].

The rest is a negative result and it is load-bearing: the Hungry and Thirsty moodles have no movement-speed, damage or XP effect at all — a whole-jar scan for `HUNGRY` dated 2026-09-10 finds it only in the audio parameter class, `BodyDamage`, `Moodle`, `MoodleStat`, a book title, the `MoodleType` registry and the two display classes, and the install's Lua names neither `MoodleType.HUNGRY` nor `MoodleType.THIRST` anywhere [#0523/C/snapshot].

The `FOOD_EATEN` gate is the one moodle effect the runs pinned down in detail.
At level 4 and idle, hunger is bit-exactly frozen: nine consecutive server samples over 1.065 game-hours, 3 833 game-seconds, all read a hunger of 0.200000 where the idle rate would have added 0.0294, while thirst ran at 7.99989e-6 and calories at minus 0.0160771 per game-second in the same samples, so the gate is on hunger alone [#0524/M/n=1].
With the gate down the coded rate resumes exactly: over the next 15 samples and 1.863 game-hours hunger rose at 9.2564e-6 per game-second against a predicted 9.2551e-6 at a mean hunger of 0.0359, a ratio of 1.0001 [#0525/M/n=1].

A real eat resets the health-from-food timer rather than adding to a primed one: a queued eat action on a steak took the timer from 186 096 to 0, hunger from 0.200 to 0.0046 and calories up by 212 [#0526/M/n=1].
The timer decays at a fixed game-time rate of 3.000 units per game-world second on a 90-minute-day fixture, flat across nine samples covering 11 500.6 units over 3 833.5 game-seconds [#0527/M/n=1].
It decays by 1 times the game-time multiplier per `BodyDamage.Update` tick, carrying that multiplier but not the delta-minutes-per-day factor every stat rate carries, so the decay is the day length over 30 units per game-second — 3.0 on a 90-minute day and 2.0 on the 60-minute default — frame-rate independent and, in game time, independent of the time-speed setting, because the multiplier itself scales with speed and read 4.78 to 4.80 at speed 1 and 143.5 to 144.0 at speed 30 [#0529/M/n=1].
So the 11 000-unit `JustAteFood` cap is about an hour of game time: 11 000 over 3.0 is 3 667 game-seconds, or 1.02 game-hours, and one moodle level of 1 600 units is about 8.9 game-minutes; in wall-clock terms on that fixture that is about 7.7 real seconds at time speed 30 and about 3.8 real minutes at speed 1 [#0528/M/arith.].
The fill path itself is unmeasured: `JustAteFood` fills the timer from the absolute hunger change times a factor times 13000, doubled if the food is cooked and capped at 11 000, and the run's gate was supplied by a direct timer write rather than by a fill [#0530/C/C-only].

<a id="weight-bands"></a>
### The weight bands

`Nutrition.applyTraitFromWeight` removes all five band traits and re-adds one by weight, with both ends of each range inclusive and no band trait at all in the open interval between 75 and 85 kg, re-checked about every 2000 updates; `applyWeightFromTraits` writes a band's weight at character creation [#0155/M/one-fixture, #0531/M/n=1, #0533/C/C-only].

| Band | Condition | Weight written at creation |
|---|---|---|
| Obese | 100 kg or more | 105 |
| Overweight | 85 kg up to but not including 100 | 95 |
| normal | the open interval between 75 and 85 | — |
| Underweight | above 65 up to and including 75 | 70 |
| Very Underweight | above 50 up to and including 65 | 60 |
| Emaciated | 50 kg or less | 50 |

The 100, 85, 75 and 80 kg edges are measured on the dedicated-server path, and the 45, 55, 95 and 105 kg interiors too; the 50 and 65 kg edges are read from the code only, because both probes read back 50.000099 and 65.000099 — the server had already nudged the weight past the boundary before the comparison ran, the gain arm firing because the primed store exceeded the threshold that [nutrition-core.md#weight-model](nutrition-core.md#weight-model) gives, which is minus 200 at 50 kg and 400 at 65 kg, both below the 500 kcal the probe had primed [#0531/M/n=1].
The refresh runs only once every 2000 `updateWeight` calls, so a weight change is not reflected in the band traits until the counter rolls; the figure is read from the bytecode and the counter's phase was unknown at the probe, so the measurement bounds the period below rather than measuring it [#0534/C/C-only].
Unforced, the refresh did not fire within 60 s of dedicated-server time: with weight moved from 80 to 105 and no forced refresh, 29 polls over 59.8 s all read the Obese trait false at a weight of 105 [#0535/M/n=1].
`getNutrition():applyTraitFromWeight()` is public, Lua-reachable and applies the band trait instantly; it is the route every measured band reading used [#0536/M/n=1].
A character created inside a band starts at the band's own weight rather than at its edge, and those five creation weights are read from the code and not measured [#0533/C/C-only].

The weight formula that feeds all of this — the gain and loss thresholds, the rates and the macro multipliers — is [nutrition-core.md#weight-model](nutrition-core.md#weight-model).
One correction belongs here rather than there: `setIncWeightLot(true)` fires on the double-gain arm as well as the triple, that is from carbohydrates or lipids above 400 rather than above 700, so a display suffix driven by the flag appears from 400 [#1101, #1491/C/C-only].
The session that read the flag exercised the 700 side only, at carbohydrates 800, so the double arm was never entered and a probe at 500 would measure it directly [#1491/C/C-only].

<a id="weight-traits"></a>
### What a weight band does

Every effect of the weight-band traits outside `Nutrition` is these 14 jar readers and their per-trait values, read from the jar on 2026-09-10 and none of it measured; the script XP boosts are a script fact and are stated below rather than inside the table [#0541/C/C-only].

| Reader | Effect | Obese | Overweight | Underweight | V.Under | Emaciated |
|---|---|---|---|---|---|---|
| `IsoPlayer.updateInternal2` | run speed, applied only when the speed factor is already above 1, that is running or sprinting | ×0.85 | ×0.99 | — | — | — |
| `IsoPlayer.updateInternal2` | run speed, raw weight gate — the only direct weight read outside `Nutrition` | `weight > 120` → ×0.97 | | | | |
| `IsoPlayer.updateEndurance` | endurance-drain multiplier while running, sprinting or dragging (base 1.4, Athletic 0.8, then ×2.3) | — | 2.9 | — | — | — |
| `IsoPlayer.updateEndurance` | the same multiplier in the heavy-load (`HEAVY_LOAD > 2`) walking branch (base 1.4, then ×3.0) | — | 2.9 | — | — | — |
| `IsoGameCharacter.getRecoveryMod` | endurance and muscle recovery multiplier, after the Fitness curve 0.7→1.6 | ×0.4 | ×0.7 | — | ×0.7 | ×0.3 |
| `getClimbingFailChanceFloat` | climb-success score, higher is safer; Obese and Overweight are `else if` | −25 | −15 | — | — | — |
| `getClimbRopeSpeed` | rope-climb tier, an int clamped 0–10; `else if` | −2 | −1 | — | — | — |
| `calculateGrappleEffectivenessFromTraits` | grapple effectiveness | ×1.05 | ×1.10 | — | ×0.8 | ×0.6 |
| `handleLandingImpact` | fall-damage multiplier (Obese or Emaciated first, else Overweight or V.Under) | ×1.4 | ×1.2 | — | ×1.2 | ×1.4 |
| `handleLandingImpact` | integer landing-severity term, same grouping | +20 | +10 | — | +10 | +20 |
| `attackFromWindowsLunge` | window-lunge score, `max(5, n)` at the end; V.Under added twice | −10 | −5 | — | +30 | — |
| `ClimbOverFenceState.shouldFallAfterVaultOver` | vault-fall chance, `Rand.Next(100) < n − Fitness`; V.Under added twice | +20 | +10 | — | +30 | — |
| `IsoMovingObject.separate` | bump-trip score `n`, trip if `Rand.Next(n) == 0`; base `10 − 3·bumpNbr + Fitness + Strength − 2·DRUNK`, clamped `[1,80]` | −8 | −4 | −4 | −8 | — |
| `Nutrition.canAddFitnessXp` | blocks Fitness XP from a Fitness level | ≥ 6 | ≥ 9 | never | ≥ 6 | ≥ 6 |

A mod that keys an effect on a weight band inherits all of those readers unchanged, because only one of them reads the weight itself — the run-speed gate above 120 kg — and the rest test the trait [#0541/C/C-only].

The five weight-band trait scripts carry no stat modifiers, only a starting Fitness XP offset: minus 2 for Obese, minus 1 for Overweight, minus 1 for Underweight, minus 2 for Very Underweight and none at all for Emaciated [#0539/C/C-only].
Besides the trait classes, `Nutrition` and the script generator, the five band trait fields are read in only five classes in the jar — `IsoGameCharacter`, `IsoPlayer`, `IsoMovingObject`, `ClimbOverFenceState` and `ClimbSheetRopeState` — and the last only prints them for debug, in a jar-wide scan dated 2026-09-10 [#0540/C/snapshot].
The weight-trait multipliers inside `getRecoveryMod` are live: Obese times 0.4, Overweight times 0.7, Very Underweight times 0.7 and Emaciated times 0.3 — unlike the macro branches of the same method, which are dead code ([nutrition-core.md#macro-effects](nutrition-core.md#macro-effects)) [#0183].
Fitness experience is gated by the weight-band traits and Strength experience is not: `XP.AddXP` returns before adding any Fitness experience when `canAddFitnessXp` is false, while a Strength gain passes no band test and is scaled by the protein store instead, whose branch is [perks-and-strength.md#xp-grants](perks-and-strength.md#xp-grants) [#2111/C/C-only] [#2112/C/C-only].
`Nutrition.canAddFitnessXp` returns false, and so blocks Fitness experience, at Fitness 9 or above with any weight trouble, so Overweight blocks too; at Fitness 6 to 8 only under Emaciated, Obese or Very Underweight; and never below Fitness 6 [#2647/C/C-only].
`characterHaveWeightTrouble` tests `VERY_UNDERWEIGHT` twice and `UNDERWEIGHT` never, so plain Underweight is not weight trouble and, through `canAddFitnessXp`, never blocks XP at any Fitness level [#0185, #0537/C/C-only].

Four of those readers are worth a design note because their numbers do not run the way the band names suggest.
Obese carries no endurance penalty: `updateEndurance` branches on Overweight only and the two traits are mutually exclusive, so an obese character drains endurance at the base 1.4 rate while a merely overweight one drains at 2.9 [#0542/C/C-only].
Overweight at 1.10 and Obese at 1.05 on grapple effectiveness are the only positive weight-trait modifiers in the game; the underweight side is penalised at 0.8 and 0.6 [#0543/C/C-only].
Very Underweight is added twice in both the window-lunge score and the vault-fall chance, 20 then 10 for a total of 30, which makes it worse than Obese at both [#0544/C/C-only].
Emaciated is absent from most of these readers — no run-speed, endurance, climb, rope or bump-trip term and no script XP boost — and appears only in the recovery multiplier, grapple effectiveness, fall damage and the Fitness XP gate, on the same jar scan dated 2026-09-10 [#0545/C/snapshot].

A client cannot derive the band, but it can derive the direction: the three weight-direction flags `isIncWeight`, `isIncWeightLot` and `isDecWeight` are all set ahead of `updateWeight`'s client skip, so a client does compute them [#1098].
Driven to plus 1500 kcal the three flags read true, false, false on both sides, and driven to minus 100 kcal they read false, false, true on both sides, each matching the arm recomputed from that snapshot's own macros — two arms driven on purpose, so this is measured on the arms that could have disagreed [#1100/M/n=1].
On the arm where all three flags are false they agree across sides at all six snapshots of an earlier session, on a character whose trait lists came back empty on both sides, so that reading carries no information about a character that holds a band trait [#1099/M/n=1].
Unforced, `applyTraitFromWeight` runs only once every 2000 `updateWeight` calls and did not fire within 60 s of dedicated-server time, while called directly from Lua the traits apply instantly — so a trait-keyed effect reads a band that lags the weight unless the mod forces the refresh [#1194/M/n=1].
The refresh itself is a full replace of the band and silent: `applyTraitFromWeight` removes exactly the five band traits and no other, adds back the one the weight's band names, adds none in the open interval between 75 and 85 kg, and pushes nothing — no packet, no player-fields send and no dirty flag [#2642/C/C-only].
So a band trait another mod grants for its own reason is gone at the next call, and a client sees the new band only on a later push of the trait list, which [../platform/mp-model.md#ownership](../platform/mp-model.md#ownership) traces [#2642/C/C-only].

<a id="traits"></a>
### The other traits in the nutrition path

The Nutritionist trait is display-only: it gates the nutrition, calories and carbohydrates block of the food tooltip, `Food.DoTooltip` is its only reader in the whole jar as scanned on 2026-09-10, and the install's Lua has no gameplay use of it [#0189/C/snapshot, #0546/C/snapshot].
There are two Nutritionist traits — `Nutritionist` at cost 2 and the mutually exclusive profession variant `Nutritionist2` at cost 0 — and the food tooltip accepts either [#0547/C/C-only].
The Weight Gain trait raises the weight-gain threshold to 700 while the character is under 90 kg, and its script grants the Overweight trait at creation [#0548/C/C-only].
The Weight Loss trait raises the weight-gain threshold to 1800 while the character is over 70 kg, and its script grants the Underweight trait at creation [#0549/C/C-only].
Neither Nutritionist variant changes a number this page states; both only reveal one [#0546/C/snapshot, #0547/C/C-only].
The two weight-direction traits are the only traits on this page that move a threshold in the weight formula rather than a rate [#0548/C/C-only, #0549/C/C-only].
Two registry trait strings contain a space, `Very Underweight` and `Out of Shape`, and the wiki's display names differ from the registry strings again [#0552/C/C-only].
The jar exposes only a trait test taking a trait object and one taking a trait array — there is no string overload — the game's own Lua route adds through the character's trait collection, and traits are not carried in the player-stats packet ([wire-packets.md#player-stats-packet](wire-packets.md#player-stats-packet), [../platform/lua-platform.md#registries](../platform/lua-platform.md#registries)) [#0917/C/C-only].

<a id="sandbox"></a>
### The body-side sandbox options

| Option | Values | What it multiplies or gates | What it does not touch | Row |
|---|---|---|---|---|
| `StatsDecrease` | an enum of 1 to 5, default 3, mapping to 2.0, 1.6, 1.0, 0.8 and 0.65 | hunger, thirst and fatigue | calories — `updateCalories` reads no sandbox multiplier at all | [#0188/M/one-fixture, #0483/M/n=1, #0553] |
| `Nutrition` | boolean, default true | `Nutrition.update`, and therefore the macro drain, the calorie burn and the weight update | intake, which keeps filling the stores, and hunger and thirst, which live in `IsoGameCharacter` | [#0555] |
| none | — | there is no dedicated hunger, thirst or calorie-burn option | — | [#0554/C/snapshot] |

All five `StatsDecrease` mappings were read directly off the live server rather than inferred, and at the extremes the measured hunger and thirst rates scale exactly as the multiplier predicts — hunger 0.9996 at setting 1 and 1.0002 at setting 5, thirst 1.0000 at both — while the calorie ratio stays at 1.0054 and 1.0050, unchanged [#0483/M/n=1, #0484/M/n=1].
`StatsDecrease` is the only sandbox option that touches hunger or thirst: a scan of `SandboxOptions`' method list dated 2026-09-10 for hunger, thirst, stat, nutrition, food and multiplier returns only `getStatsDecreaseMultiplier`, `getEnduranceRegenMultiplier` and two loot multipliers [#0554/C/snapshot].
What the `Nutrition` option gates it gates whole, and what it leaves running it leaves running: intake is [eating-pipeline.md#sandbox](eating-pipeline.md#sandbox) [#0555].
With the option off the character screen's weight arrow stops moving: vanilla writes the three weight-trend flags it reads only inside `updateWeight`, which the option's early return skips, so the arrow holds the last update's direction [#2644/C/C-only].
The food tooltip's nutrition block opens on any of three gates — the debug `tooltipInfo` option in debug mode, a packaged food whose label the viewer can read (not Illiterate, not too dark to read, and the item carrying no `NoLabel` modData), or the viewer's Nutritionist traits — and `Food.DoTooltip` references no sandbox option anywhere, so the block shows the same with the option on or off [#2645/C/C-only].
Whether anything outside `Nutrition.update` moves weight while the option is off is open below.
So a server that wants hunger and thirst to move more slowly has one dial, and a server that wants the calorie burn to move more slowly has none [#0553, #0554/C/snapshot].

## Walls and bounds
<a id="walls"></a>

Every measured rate on this page is one fixture and one run on the dedicated-server path, fitted against the world clock read from the same snapshot, so the time-speed setting cancels; the moving and asleep burn branches, the swipe and timed-action modifier paths, the auto-drink constants and every weight-trait reader are read from the code and never measured.

Where a mirror and the jar disagree the code wins, and each mirror keeps the wiki page version it was fetched at.

The mirror says hunger ticks a flat 4.32 per cent per in-game hour; the code gives 3.456 per cent per game-hour at zero hunger, falling as hunger rises, a first-order approach rather than a linear fill, and the mirror's per-tick figure is the Lua literal quoted before its multiplication by 3 [#0574/M/n=1].
The mirror says health regeneration is cut about 25 per cent at the first hunger level and then 25, 55 and 100 per cent; the code fires the tier only from level 2 and runs 0.002, 0.0013, 0.0008 then 0.0, that is minus 35, 60 and 100 per cent, with level 1 having no effect at all [#0575/C/C-only].
The mirror says each Hungry level decreases body heat generation and that every positive level heals 750 per cent faster; the code has no thermoregulator read of the moodle and no healing multiplier attached to it — its whole footprint is carry capacity, the regeneration tier, the zeroed sleeping health addition at level 4, the level 4 health loss, and for `FOOD_EATEN` the hunger gate, the poison-decay term and the eat block at level 3 [#0576/C/C-only].
The mirror says the thirst thresholds are above 13 per cent and above 85 per cent; the code fires at 0.12, 0.25, 0.70 and 0.84 on a strict greater-than, off by a point at both ends [#0577/M/n=1].
The mirror says sprinting carries the same 1.2 thirst factor as running; the code returns that factor only for the local player instance while the running flag is set, which is a different flag from sprinting, and the asleep thirst branch applies neither it nor the heat term [#0578/C/C-only].
The mirror says health drains a flat 22 per cent per in-game hour at the top thirst level; the branch is real and is the harshest severe-moodle term of its class at five times the hunger branch, but its rate is day-length dependent — 11.88 per cent per game-hour on the 60-minute default day and 17.82 per cent on a 90-minute one — and matches no standard day length at 22 per cent [#0579/M/arith.].
The mirror's moodle index has no FoodEaten entry and folds the well-fed state into Hungry; the code registers a distinct `FOOD_EATEN` moodle that is not threshold-driven from a stat at all but reads the health-from-food timer against 1600, and it is that moodle rather than `HUNGRY` that gates the hunger rate [#0580/M/n=1].
The mirror gives weight bands of 35 to 50, 51 to 65, 66 to 75, 76 to 85 as none, 86 to 100 and 101 to 130 on this same build; the comparisons are inclusive at both ends — 100 kg or more for Obese, 50 kg or less for Emaciated, 85 for Overweight, 75 for Underweight and the open interval between 75 and 85 for normal — and the 35 and 130 endpoints are the weight-change floor and ceiling rather than band edges [#0581/M/n=1].
The mirror gives display names Fast and Slow Metabolism and Very Low, Low, High and Very High Weight; the API strings are `WeightLoss` and `WeightGain` and `Very Underweight`, `Underweight`, `Overweight` and `Obese`, and `getKnownTraits` returns them lowercased, so a display name must never be matched on [#0582/M/n=1].
The mirror says Overweight's starting weight is 90 and that Obese caps fitness at 7; `applyWeightFromTraits` writes 95 kg for Overweight, and `canAddFitnessXp` blocks from Fitness 6 for Obese, Emaciated and Very Underweight and from Fitness 9 for Overweight, while plain Underweight never blocks [#0583/C/C-only].
The mirror says Nutritionist improves foraging; the trait has exactly one reader in the jar, the food tooltip, and no gameplay use in the install's Lua [#0584/C/C-only].
The mirror gives per-trait melee-damage and climb-failure percentages for Emaciated, Underweight and Very Underweight; no reader on this jar applies either to them, and the climb-failure score branches on Obese and Overweight alone [#0585/C/C-only].
The mirror says High Thirst makes you twice as thirsty when dying of thirst; the doubling is unconditional — both thirst branches, every thirst level, no health term — and it was measured at moderate thirst [#0586/M/n=1].
The mirror gives a per-level endurance-loss curve from 90 to 43 per cent; the endurance-drain multiplier is composed from a base of 1.4, Overweight 2.9, Athletic 0.8 and a 2.3 stage before pacing and hyperthermia, and the only per-level Fitness curve read in that area is on recovery, running 0.7 to 1.6 [#0587/C/C-only].
The mirror says Fitness reduces damage taken from long falls and gives a flat 2 per cent per level trip reduction; the landing handler's only trait terms are the weight ones, and Fitness enters the vault-fall chance as a subtraction inside a random roll and the bump-trip score additively inside a clamp of 1 to 80, neither of which is a percentage [#0588/C/C-only].
The mirror never mentions the cold side's body effect; the thermoregulator's cold-side energy multiplier multiplies resting and sleeping calorie burn and nothing else, because the three moving branches never read it [#0589/C/C-only].
The mirror tells a modder to call `hasTrait` with a String literal; on this build `hasTrait` takes only `CharacterTrait` or `CharacterTrait[]` and there is no String overload [#1260/C/C-only].

Not covered: the temperature model behind the thermoregulator's primary and secondary totals; which weapon type selects which metabolic-rate class while attacking, and how far the rate moves toward its target per update; and the moodle texture and UI layer.

## Open
<a id="open"></a>

- The walking, running and sprinting burn constants are unmeasured — the run's server saw the moving flag in 5 of 52 samples, one consecutive pair, and never saw the running flag, so the run flag did not reach the server's copy of the character — settled by the walk, run and sprint ratio tests against idle, 4.875, 8.125 and 10.5625 [#0591/M/n=1/open].
- The asleep burn branch is unmeasured: the sleep write held on the immediate read-back but did not persist, and the next row's 52 server samples all read the character awake with idle-rate burn about 27 s later, so whether the sleep was walked off or never persisted is undetermined — settled by a sleep arm that verifies the state on the server before the window opens [#0592/M/n=1/open].
- Whether the 1.2 running thirst factor ever fires on a dedicated server is unknown: it is gated on the character being the local player instance, which on a headless server is probably never true, so running may not raise thirst in multiplayer at all — settled by the same running branch the burn constants need [#0593/C/C-only/open].
- The real range of the thermoregulator's energy multiplier is unknown: the primary and secondary totals are written by a node loop that was not traced, so the size of the cold-weather burn bonus is unbounded here, and the reading near 1.005 seen in the run is one uncontrolled fixture — settled by a temperature-controlled pair of idle windows [#0594/C/C-only/open].
- Whether split-screen players 2 to 4 accrue hunger or thirst locally is unverified: in single-player the wake-state and thirst updaters run only for the local player instance — settled by a split-screen boot, which no run in this library has exercised [#0596/C/C-only/open].
- The write order of `applyWeightFromTraits` is not exercised: its branches are sequential ifs, so a character carrying two weight traits — blocked in the UI, but reachable by a mod — would end at the last matching branch — settled by a probe that adds two band traits from Lua and reads the written weight back [#0597/C/C-only/open].
- Not settled: the 50 kg and 65 kg band edges rest on the code alone, because the server nudged the weight past each boundary before the comparison ran; priming calories below the gain threshold for those weights measures them [#0531/M/n=1].
- Whether the thermoregulator's metabolic-rate classification tracks a connected player's state on the server or sits at its default — settled by server reads of the metabolic rate while the client idles, walks and runs, against the class each state names, with endurance and carried load held still or accounted for, because both raise the target above its class [#2649/C/C-only]; -> [X37](../areas/open-questions.md#x37) [#2088/C/open].
- Whether body weight drifts with the vanilla `Nutrition` option off and no mod weight write — settled by three accelerated game-days of hourly server weight with the option off, beside the same run with it on; -> [X41](../areas/open-questions.md#x41) [#2090/C/open].
- The rows above without a named experiment are costed in [../reference/experiments.md](../reference/experiments.md).
- Decision: whether the mod's own nutrient stores are driven from hunger, from calories or from neither — the two vanilla stores have no coupling in either direction [#0500, #0501].
- Decision: whether a weight band is evaluated server-side or derived on the client from the three weight-direction flags, which a client does compute [#1098] — the band trait itself lags the weight by up to 2000 weight updates [#0534/C/C-only].
- Decision: whether hunger and thirst are retuned through the sandbox multiplier or the updaters are replaced — `StatsDecrease` scales hunger, thirst and fatigue together and never calories [#0553].
- Decision: whether a trait-keyed effect reads a vanilla band trait at all, given that its name comes back lowercased and no string overload of the trait test exists [#0582/M/n=1, #1260/C/C-only].
- Decision: whether an activity-scaled mod quantity reads the engine's metabolic-rate classes or classifies the player itself — the classes are floors raised within one update, endurance and carried load raise the target above them, and none of it is measured on a server [#2633/C/C-only] [#2649/C/C-only].
- Decision: whether the mod refreshes the band traits after its own weight write, given that each refresh removes all five band traits, re-adds one and pushes nothing [#2642/C/C-only].

## See also

- [nutrition-core.md#weight-model](nutrition-core.md#weight-model) — the weight formula the bands read, its thresholds and rates, and the store clamps.
- [eating-pipeline.md#eat](eating-pipeline.md#eat) — the intake side that fills the stores this page drains.
- [wire-packets.md#player-stats-packet](wire-packets.md#player-stats-packet) — the packet that carries these stats, and what it leaves out.
- [../platform/mp-model.md#ownership](../platform/mp-model.md#ownership) — which side owns each of these quantities, what the other side holds instead, and the two pushes that carry a character's trait list.
- [health-surfaces.md#regeneration](health-surfaces.md#regeneration) — the regeneration constants the moodle tiers select, and the decoded switch.
- [perks-and-strength.md#xp-grants](perks-and-strength.md#xp-grants) — the experience grants, the protein branch on Strength and the caller of the Fitness gate.
- [endurance-fatigue-sleep.md](endurance-fatigue-sleep.md) — endurance, fatigue and sleep beyond the weight-trait readers listed here.
- [exercise-and-training.md](exercise-and-training.md) — the `Fitness` object, the exercise path and the metabolic target it sets.
- [../platform/lua-platform.md#registries](../platform/lua-platform.md#registries) — registering a moodle type or a trait, and what registration does not give.
- [../reference/experiments.md](../reference/experiments.md) — the costed experiments and their riders.
