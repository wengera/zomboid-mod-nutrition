# Nutrition core — calories, macros and weight
Verified against 42.20.4 (b0bbce05d5) · 2026-10-01 · scope: the `Nutrition` object's stores, the weight model that reads them and the client command that writes weight, the clamps that bound them and the three-game-day server check of that model; intake belongs to `facts/eating-pipeline.md`, passive burn and the weight bands to `facts/body-and-weight.md`, and ownership of the weight quantity to `platform/mp-model.md`.

## Key facts

- Calories are the only driver of weight, and carbohydrates and lipids act on it only as multipliers of the gain rate [#0180].
- Proteins never touch weight; outside the weight model their recovery branches below -1000 and -1500 are dead under the -500 clamp, and their one live reader is the Strength experience branch [#2648/M/n=2].
- `Nutrition.setCalories` clamps the calorie store to the range -2200 to 3700 [#0022/M/n=2].
- `Nutrition.setCarbohydrates`, `setProteins` and `setLipids` each clamp their store to the range -500 to 1000 [#0023/M/n=2].
- Nothing clamps a store at zero: a calorie write of -100 reads back -102.5664 on the server and -102.10 on the client [#0901/M/n=1, #1102/M/n=1, #1197/M/n=1].
- The weight-gain threshold is `1000 + (weight - 80) x 40`, which is 600 at 70 kg, 1000 at 80 kg and 1400 at 90 kg [#0149/C/C-only].
- The weight-loss threshold is `min(0, (weight - 70) x 30)`, so at 70 kg or more any negative calorie total loses weight [#0151/M/one-fixture].
- The gain rate is `1.3e-5` kg per game-second times `min(1, calories/4000)`, at most 1.039 kg per game-day under the 3700 clamp [#0152/C/arith.].
- The gain rate is multiplied by 3 when carbohydrates or lipids exceed 700 and by 2 when either exceeds 400, which caps gain at 3.117 kg per game-day [#0153/C/arith.].
- The loss rate is `8.5e-6` kg per game-second times `min(1, abs(calories)/2500)`, at most 0.646 kg per game-day under the -2200 floor [#0154/C/arith.].
- The three macro decay rates inside `Nutrition.update` are hard-coded Java floats: 0.0035000001080334187, 0.001129999989643693 and 0.000859999970998615 [#1193/C/C-only].
- Over three game-days on the dedicated server the pinned gain run added 2.526 kg against 2.551 kg predicted [#0159/M/one-fixture], and the fasting run lost 1.426 kg against 1.412 kg predicted [#0160/M/one-fixture].

## How it works

The readings that follow ran on the build their rows' bounds name; they read that build, not the release.

`Nutrition` is a per-player object of floats — calories, carbohydrates, proteins, lipids and weight — reached from Lua as `player:getNutrition()`; it is a closed value object with no mod-data table, no generic accessor and no registration call, so a mod puts its own nutrient beside these floats [#1121/C/C-only].
Four setters write the four intake stores and clamp as they write, and one update method carries three arms: the macro drain (a fixed per-game-second subtraction), the calorie burn ([facts/body-and-weight.md](body-and-weight.md#passive-burn)) and the weight move, which reads the stores the other two have just left.
A write from outside competes with an arm rather than replacing it: a calorie write lands in a store the burn is still emptying, and a macro write in one the drain is still emptying.
Everything here is the server's behaviour, because a multiplayer client runs neither the drain nor the burn and holds only the number the server pushed it ([#0117], [platform/mp-model.md](../platform/mp-model.md#ownership)).
The whole update sits behind one sandbox boolean, which takes all three arms together while intake carries on unguarded ([#0067], [facts/eating-pipeline.md](eating-pipeline.md#sandbox)).

<a id="weight-model"></a>
### The weight model

A fresh character starts at 80 kg with a calorie store of 800 kcal, both set by `Nutrition`'s constructor, before a weight trait moves the weight [#3880/C/C-only].
The weight update runs once per character update tick with no timer gate, reached from the player update through the two internal update steps, which are gated only on the character-stats disabler, and then through the nutrition update [#0902/C/C-only].
It keeps no accumulator or timer of its own, and no event fires when the weight moves, so a Lua reproduction hangs off the same update loop or integrates by hand between runs.

```
IsoPlayer.update @8
  -> IsoPlayer.updateInternal1 @51 L2200
  -> IsoPlayer.updateInternal2 @392-@402 L2306-L2307    # gated only on SystemDisabler.doCharacterStats
  -> Nutrition.update @107 L81
  -> Nutrition.updateWeight
```

The model itself, as the method computes it [#0149/C/C-only, #0150/C/C-only, #0151/M/one-fixture, #0152/C/arith., #0153/C/arith., #0154/C/arith.]:

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

The gain threshold is a code reading: the fed run stayed in the gain branch for all seventy-two game-hours, so its calorie minimum bounds the threshold only from above, over the slice of the weight axis it walked [#0149/C/C-only].
The Weight Gain trait replaces the gain threshold's base with 700 below 90 kg and the Weight Loss trait replaces it with 1800 above 70 kg; neither base was exercised, because no weight-band or appetite trait was held in any of the three server runs [#0150/C/C-only].
Below 70 kg the loss threshold turns negative, so at 60 kg it takes less than -300; the loss side is measured only near 80 kg, where the fasting run crossed the threshold inside its first game-hour, at -57.3 kcal [#0151/M/one-fixture].
Between the two thresholds lies a dead band where weight moves in neither direction; it widens with weight, so a mod that wants weight to answer to its own model has to reproduce both edges, not only the rates.

Both rates are a per-game-second constant times a saturating factor, and the setters clamp the store below the value at which either factor would saturate, so neither arm runs at its nominal constant.
The gain rate, `1.3e-5` kg per game-second times `min(1, calories/4000)`, is 1.12 kg per game-day at a 4000 kcal store and at most 1.039 kg per game-day under the 3700 clamp; the per-day figures are arithmetic on the formula and the measured clamp, and no run reached the ceiling [#0152/C/arith.].
The loss rate, `8.5e-6` kg per game-second times `min(1, abs(calories)/2500)`, is 0.73 kg per game-day at -2500 kcal and at most 0.646 kg per game-day under the -2200 floor, again derived from the formula and the measured floor [#0154/C/arith.].
The macro multipliers, times 3 above 700 and times 2 above 400 of carbohydrates or lipids for a 3.117 kg per game-day cap under the calorie clamp, are code-only: no run has entered either branch, because both macro stores only drain when calories are written directly, and the fed run ended at carbohydrates -500 and lipids -292.9 [#0153/C/arith.]; reaching them needs the intake side, [facts/eating-pipeline.md](eating-pipeline.md#modifiers).

`updateWeight` reads calories, carbohydrates and lipids only, and neither it nor `updateCalories` has a hunger or thirst term, so pinning hunger and thirst in a scenario is a control rather than a thumb on the scale [#0178]; their own accumulation and coupling are [facts/body-and-weight.md](body-and-weight.md#coupling).
The macro drain's rates, 0.0035000001080334187, 0.001129999989643693 and 0.000859999970998615, are hard-coded Java floats inside `Nutrition.update`, unlike the Lua globals that carry the hunger and thirst rates [#1193/C/C-only].
The burn's rate is corroborated from the other end by a teardown session: over its longest write-free window of 38.947 seconds the server's calories fell at 0.250296 per real second against a derived 0.2560552, a ratio of 0.9775, so the derived rate was used for every band and the energy multiplier is corroborated to about 2 per cent; the session's three short windows scatter by about 20 per cent and are not quotable [#1494/M/n=1].

All three weight-direction flags are written at four sites inside `Nutrition.updateWeight`, every one of them ahead of the method's client skip [#2006/C/C-only].
So a client derives a weight direction but not a weight: the skip and its discarded delta are [platform/mp-model.md](../platform/mp-model.md#ownership) ([#1097/M/n=1]), and the flags' measured cross-side agreement is [facts/body-and-weight.md](body-and-weight.md#weight-traits) ([#1100/M/n=1]); the flags are the cheapest signal a client interface has for which way a character is heading.

Vanilla's `player` `setWeight` client command, whose packet type requires only the login capability every connected client holds, sets any online player's weight on the server through `getPlayerByOnlineID(args.id)` and `getNutrition():setWeight(args.weight)`, with no admin check in its handler, in the `OnClientCommand` dispatch or in the Java receiver, and the player-stats admin panel sends it [#2643/C/C-only].
The model carries on from whatever value that command leaves, so a weight a mod writes on the server can be replaced between two of its own writes by a client; this is read from the files and the bytecode and not exercised on a live server [#2643/C/C-only].

<a id="clamps"></a>
### The store clamps

Every write passes a clamp inside its setter: `Nutrition.setCalories` holds the calorie store to -2200 to 3700, and `setCarbohydrates`, `setProteins` and `setLipids` each hold theirs to -500 to 1000; both signs of both clamps were probed once each on the server bus and landed exactly on the limits [#0022/M/n=2, #0023/M/n=2].
Nothing clamps the calorie store at zero, so negative stores are a normal state: a write of -100 read back -102.5664 on the server and -102.10 on the client, each side having run its own decay ticks since the write, so the pair is two readings of "not clamped" rather than a sync figure [#0901/M/n=1, #1102/M/n=1, #1197/M/n=1].
Carbohydrates hit their -500 floor in the fed run at the game-hour 40.0 sample, against 39.7 predicted, the crossing resolved only to the hourly sample [#0169/M/one-fixture]; the drain alone reaches a macro floor, so a macro store spends much of a long session pinned there.
A clamp truncates on contact and returns no signal, so a dose larger than the headroom is lost in silence, whether it came from a mod write or a meal; the intake side's modifier ladder before these setters is [facts/eating-pipeline.md](eating-pipeline.md#modifiers).
A vanilla store is therefore a poor place to smuggle a mod quantity, and a mod store of its own needs an explicit range decision.

<a id="verified"></a>
### The model against three game-days on the server

A scenario drives one store from the server and records the `Nutrition` object once a game-hour; a checker replays the formula over each run's own calorie trace and compares the predicted weight with the server's, inside a tolerance that is a fraction of the predicted delta with a floor in kilograms.

| run | scenario | measured | predicted | residual | tolerance | claim |
|---|---|---|---|---|---|---|
| `scenario-20260910-052624` | gain, hunger and thirst unpinned | +1.045 kg over 34 alive game-hours | +1.057 kg | -0.012 | 0.159 | [#0158/M/one-fixture] |
| `scenario-20260910-054012` | gain, hunger and thirst pinned after every sample | +2.526 kg over 72.0 game-hours | +2.551 kg | -0.025 | 0.383 | [#0159/M/one-fixture] |
| `scenario-20260910-055029` | fast, no intake at all | -1.426 kg over 72.0 game-hours | -1.412 kg | -0.014 | 0.212 | [#0160/M/one-fixture] |

The unpinned run failed because its subject died at game-hour 35, so its live model check is the thirty-four alive game-hours; that run's whole-trace evaluation keys are corpse readings and are not citable [#0158/M/one-fixture].
The two completed runs are one fixture each, the fed one with hunger and thirst reset after every sample and the fasting one with no intake at all [#0159/M/one-fixture, #0160/M/one-fixture]; every run used the same fixture, build, server path and admin character with the clock accelerated, so a reading quoted in real seconds means something only beside its day length.
Integrating hourly samples at each interval's left endpoint biases the predicted weight by about 0.025 kg over three game-days, and an offline midpoint re-integration of the same samples collapses the residuals to -0.0003 kg and -0.0002 kg, so about 0.03 kg per three game-days is the floor of what the check can resolve [#0164/M/one-fixture].
On build 42.21 the formula, integrated from each session's own start state, matched a surplus on one character over two sessions from world age 2.4652042388916016: its store written to 3000 kcal at 80 kg and seven `Base.TunaTinOpen` eaten, the weight read 80.02469593645765 kg at world age 3.0934629440307617 and 81.4192053475972 at 38.50537109375, every hourly read within 0.00031931595052014927 kg of the formula in the first session and 0.0005957867189749777 in the second [#3884/M/n=1].

The 3700 kcal ceiling, not the rate constant, bounds a fed character: the fed run asked for 12000 kcal in six 2000 kcal doses at game-hours 0, 12, 24, 36, 48 and 60, and the store kept 7210, losing 4790 kcal to the clamp [#0165/M/one-fixture].
Day one is a ramp: the first dose only reaches 2000 kcal, so the day averages a `min(1, calories/4000)` factor of 0.583 and gains 0.647 kg, and the seventy-two-hour time-averaged factor of 0.757 gives 0.850 kg per game-day against 0.842 measured, the gap being the check's own quadrature [#0162/M/one-fixture].
Days two and three gain 0.940 kg per game-day at an average factor of about 0.84, the calorie trace oscillating between the 3700 ceiling and about 2990; only four of the seventy-three samples sit at the ceiling, so this measures a sawtoothing store rather than a pinned one [#0163/M/one-fixture].
The fasting run reached the -2200 floor at game-hour 39 against 38.2 predicted at a flat 80 kg, arriving later because the burn falls with the weight, and its loss ramps with the deficit: 0.204 kg on day one and 0.576 kg on day two [#0166/M/one-fixture].
A game-day spent entirely on the -2200 calorie floor lost 0.646 kg, against the derived `8.5e-6 x 2200/2500 x 86400` of 0.646272, confirmed to three decimals on day three of that run [#0161/M/one-fixture].

The three-day check asserts one thing, the weight delta over the run, across a 78.5 to 82.5 kg slice with no weight-band trait held, no trait threshold base, no `Nutrition = false` control and no intake, every run driving `setCalories` directly [#0170/M/one-fixture].
No burn rate, threshold crossing or macro multiplier is asserted, and every other figure in this subsection is a cross-check fitted off the same samples afterwards [#0170/M/one-fixture].

The failed run's corpse window settles two things, both read off the sample trace rather than off that run's evaluation keys.
`Nutrition.update` stops on a corpse: weight, carbohydrates, lipids, proteins, hunger and health stay bit-flat for the thirty-seven game-hours after death, with carbohydrates frozen at -437.888763, short of their -500 floor [#0176/M/one-fixture].
An external `setCalories` write still lands on a corpse: calories stepped to 3700 at the hour-36 dose and held while every store the update drives stayed frozen [#0177/M/one-fixture].
So the update stops while an external store write is not gated on the character being alive, and anything that fills a calorie store from outside has to manage hunger and thirst as well.

<a id="macro-effects"></a>
### What each macro does once stored

Of the four intake stores, calories alone drive weight, and carbohydrates and lipids act on it only as multipliers of the gain rate [#0180].
Proteins never touch weight; their two readers outside the weight model are `getRecoveryMod`, whose lipid and protein branches below -1000 (times 0.5) and below -1500 (times 0.2) can never fire because the setters clamp both stores at -500, and the Strength branch of `XP.AddXP`, which is live because its thresholds lie inside the clamp range and is stated at [perks-and-strength.md#xp-grants](perks-and-strength.md#xp-grants); the clamp half is measured on both signs on the server bus, the two branches are a code reading [#2648/M/n=2].
The live multipliers in that recovery method, and the Fitness experience gate beside it, are keyed on the weight-band traits rather than on any macro: [facts/body-and-weight.md](body-and-weight.md#weight-traits).
Those floats are the whole of the object's serialised form, in a fixed order that `Nutrition.save` writes and `Nutrition.load` reads back ([#0108], [facts/wire-packets.md](wire-packets.md#player-stats-packet)), so a protein value survives every round trip.
The carbohydrate store as an energy pool and any notion of diet quality are dead space in this build, and a protein surplus has exactly one vanilla consumer, Strength experience gain, so a parallel nutrient store collides with vanilla only where it moves the vanilla protein store [#2648/M/n=2].
Every consequence a mod nutrient is to have must therefore be written by the mod; the vanilla behaviour it must not disturb is the gain multiplier pair and, where it writes the protein store, the Strength branch.

## Walls and bounds
<a id="walls"></a>

No class in the jar contains the literal `setNutrition` in any identifier form, so the `Nutrition` object cannot be substituted [#1185/C/C-only].
`Nutrition.update` is not among the seven updaters a `CalculateStats` handler skips: it hangs off `BodyDamage.Update` at `updateInternal`, so registering a handler does not stop the macro drain [#2744/C/C-only].
The thresholds and rates inside the weight update are fixed on this build, and the only nutrition-side lever is the sandbox boolean, whose consequence is that the weight and trait coupling goes with it [#1127/C/C-only].
A client cannot own the weight quantity at all, so anything keyed on a weight band is evaluated on the server or fed an explicitly transmitted value ([#1097/M/n=1], [platform/mp-model.md](../platform/mp-model.md#ownership)).
The whole weight model is measured across one narrow slice of the weight axis, with no weight-band or appetite trait held and no control run with the sandbox gate off; the bound is stated with the check at [the server check](#verified), and the macro multiplier branches are derived rather than observed.
Every reading here is a dedicated server with one client, one fixture and one admin character; single-player is never claimed.
Not covered: the character model, the animation system and the interface, which read the weight value and which this library never opened; and the two maintained calorie extremes, whose readers are the open row below.

## Open
<a id="open"></a>

- Whether `Nutrition.caloriesMax` and `caloriesMin` have any reader at all is unsettled: they are maintained but a jar-wide reader scan found none, so they are possibly interface or debug only — settled by a fresh jar-wide reader scan of both fields on this build, with the exposer dump beside it [#0190/C/snapshot/open].
- Decision the design must take: whether the mod reproduces vanilla's three arms in Lua behind the sandbox gate or lives beside them, forced by the gate taking the drain, the burn and the weight arm together while intake carries on unguarded ([#0067], [facts/eating-pipeline.md](eating-pipeline.md#sandbox)).
- Decision the design must take: whether a mod nutrient is stored with the same two-sided clamp shape as vanilla's, forced by the clamps above being two-sided and by negative stores being an ordinary state rather than an error state.
- Decision the design must take: whether the mod's own weight model keeps a macro multiplier at all, forced by vanilla's multiplier branches never having been entered by a run and so carrying no measured behaviour to match.
- Decision the design must take: whether the mod's weight model accepts a weight written through vanilla's `setWeight` client command or overrides it, forced by that command writing any online player's weight for any logged-in client with no admin check [#2643/C/C-only].
- Decision the design must take: whether the mod writes the vanilla protein store from its own protein model, forced by the Strength experience branch reading that store directly [#2648/M/n=2].

## See also

- [facts/eating-pipeline.md](eating-pipeline.md) and [facts/body-and-weight.md](body-and-weight.md) — how food fills these stores, and the passive burn, weight bands and band traits.
- [facts/perks-and-strength.md](perks-and-strength.md#xp-grants) — the experience grants, the protein branch on Strength experience and the Fitness gate's caller.
- [platform/mp-model.md](../platform/mp-model.md) and [facts/wire-packets.md](wire-packets.md) — which side owns each quantity, and the packets that carry these stores.
- [reference/experiments.md](../reference/experiments.md) — the named experiments the open row above points at.
