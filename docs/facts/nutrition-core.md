# Nutrition core — calories, macros and weight
Verified against 42.20.4 (b0bbce05d5) · 2026-10-01 · scope: the `Nutrition` object's stores, the weight model that reads them and the client command that writes weight, the clamps that bound them and the three-game-day server check of that model; intake belongs to `facts/eating-pipeline.md`, passive burn and the weight bands to `facts/body-and-weight.md`, and ownership of the weight quantity to `platform/mp-model.md`.

## Key facts

- Calories are the only driver of weight, and carbohydrates and lipids act on it only as multipliers of the gain rate [#0180].
- Proteins never touch weight; outside the weight model their recovery branches below -1000 and -1500 are dead under the -500 clamp, and their one live reader is the Strength experience branch [T18.18].
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

`Nutrition` is a per-player object of floats — calories, carbohydrates, proteins, lipids and weight — reached from Lua as `player:getNutrition()`.
Four setters write the four intake stores and clamp as they write, and one update method carries three arms: the macro drain, the calorie burn and the weight move.
Nothing else on the object is reachable, because it is a closed value object with no mod-data table, no generic accessor and no registration call [#1121/C/C-only].
A mod therefore puts its own nutrient beside these floats rather than inside them.

The three arms are worth holding apart when reading anything below.
The drain is a fixed per-game-second subtraction from each of the three macro stores, so a macro falls whatever the character is doing.
The burn subtracts from calories according to what the body is doing, and its branches belong to [facts/body-and-weight.md](body-and-weight.md#passive-burn).
The weight move reads the stores the other two arms have just left and turns them into a direction and a rate.
A write from outside competes with an arm rather than replacing it: a calorie write lands in a store the burn is still emptying, and a macro write lands in one the drain is still emptying.

Everything on this page is the server's behaviour, because a multiplayer client runs neither the drain nor the burn and holds only the number the server pushed it ([#0117], [platform/mp-model.md](../platform/mp-model.md#ownership)).
The whole update sits behind one sandbox boolean, which takes all three arms together while intake carries on unguarded ([#0067], [facts/eating-pipeline.md](eating-pipeline.md#sandbox)).
Turning that boolean off is the only nutrition-side lever the platform offers, and it is an all-or-nothing one.

The rest of the section is read in the order the update evaluates things.
The weight model is the arithmetic and the cadence it runs at; the clamps are the ranges every store is held to; the server check is what a live run made of the two together; and the macro effects are what the stores do once they hold a value.

<a id="weight-model"></a>
### The weight model

The weight model is a branch, a rate and a pair of multipliers, evaluated afresh on every tick of the character it belongs to.
It keeps no accumulator and no timer of its own, so there is no window in which a change to the stores is ignored and none in which one is applied twice.

The weight update runs once per character update tick with no timer gate, reached from the player update through the two internal update steps, which are gated only on the character-stats disabler, and then through the nutrition update [#0902/C/C-only].

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

Read the block as three questions asked in order: which way is the character moving, how fast, and by how much is that speed multiplied.
The answers are all functions of the calorie store and the current weight, with the two macro stores entering only at the last question.

The first question is the pair of thresholds.
The weight-gain threshold is `1000 + (weight - 80) x 40`, which is 600 at 70 kg, 1000 at 80 kg and 1400 at 90 kg [#0149/C/C-only].
That arm is a code reading rather than a measurement: the threshold was never crossed downward, because the run that fed a character stayed in the gain branch for all seventy-two game-hours, so its calorie minimum bounds the threshold only from above, over the slice of the weight axis it walked [#0149/C/C-only].
The Weight Gain trait replaces the gain threshold's base with 700 below 90 kg and the Weight Loss trait replaces it with 1800 above 70 kg; neither base was exercised, because no weight-band or appetite trait was held in any of the three server runs [#0150/C/C-only].
The weight-loss threshold is `min(0, (weight - 70) x 30)`, so at 70 kg or more any negative calorie total loses weight, while at 60 kg it takes less than -300 [#0151/M/one-fixture].
The loss side is measured only near 80 kg, where the fasting run crossed the threshold inside its first game-hour, at -57.3 kcal [#0151/M/one-fixture].

The trait bases are a replacement of the base term rather than a multiplier laid over it, so a trait either moves the whole threshold or leaves it alone.
They are also the only place in the model where a trait appears at all, which is why a mod that wants a trait to change how weight behaves has to reach the trait's own effect rather than this formula.

The two thresholds leave a dead band between them, and the band is where an ordinary character spends most of its time.
A store that is positive but under the gain threshold moves the weight in neither direction, because the gain branch has not been entered and the loss branch needs a store below the loss threshold.
The band is widest at high weights, where the gain threshold rises with the weight and the loss threshold has already flattened, so a heavier character needs a fuller store to keep gaining and any deficit at all to start losing.
A mod that wants weight to answer to its own nutrient model has to reproduce both edges, not only the rates, because the edges are what decide whether anything happens at all.

The second question is the rate, and it is a constant scaled by how full the store is.
Both arms use the same shape: a per-game-second constant times a saturating factor that reaches one when the store is full enough and falls towards zero as the store approaches its threshold.
Because the setters clamp the store below the value at which either factor would saturate, neither arm can ever run at its nominal constant, and the ceilings quoted here are what the clamp allows rather than what the formula permits.
The gain rate is `1.3e-5` kg per game-second times `min(1, calories/4000)`, which is 1.12 kg per game-day at a 4000 kcal store and at most 1.039 kg per game-day under the 3700 clamp; the per-day figures are arithmetic on the formula and the measured clamp, and no run reached the ceiling [#0152/C/arith.].
The loss rate is `8.5e-6` kg per game-second times `min(1, abs(calories)/2500)`, which is 0.73 kg per game-day at -2500 kcal and at most 0.646 kg per game-day under the -2200 floor, the per-day figures again derived from the formula and the measured floor [#0154/C/arith.].

The third question is the macro multiplier, and it is the one branch of the model no run has entered.
The gain rate is multiplied by 3 when carbohydrates or lipids exceed 700 and by 2 when either exceeds 400, which caps gain at 3.117 kg per game-day under the calorie clamp [#0153/C/arith.].
Both multiplier branches are code-only, because both macro stores only drain when calories are written directly, and the fed run ended at carbohydrates -500 and lipids -292.9 [#0153/C/arith.].
Reaching either threshold therefore needs the intake side rather than a calorie write, which is [facts/eating-pipeline.md](eating-pipeline.md#modifiers).

The model reads three of the five stores and nothing else.
`updateWeight` reads calories, carbohydrates and lipids only, and neither it nor `updateCalories` has a hunger or thirst term, so pinning hunger and thirst in a scenario is a control rather than a thumb on the scale [#0178].
Hunger and thirst are a separate axis that shares a body but not a formula, which is why a character can be starving on one axis and gaining weight on the other.
Their own accumulation and their coupling to the calorie store are [facts/body-and-weight.md](body-and-weight.md#coupling).

What drains the macros between weight updates is fixed in Java.
The three macro decay rates inside `Nutrition.update` are hard-coded Java floats: 0.0035000001080334187, 0.001129999989643693 and 0.000859999970998615, in deliberate contrast to the Lua globals that carry the hunger and thirst rates [#1193/C/C-only].
The calorie side of the same update is the passive burn, whose branches are [facts/body-and-weight.md](body-and-weight.md#passive-burn), and its rate is corroborated from the other end by a teardown session: over that session's longest write-free window of 38.947 seconds the server's calories fell at 0.250296 per real second against a derived 0.2560552, a ratio of 0.9775, so the derived rate was used for every band and the energy multiplier is corroborated to about 2 per cent [#1494/M/n=1].
That corroboration rests on the long window alone; the session's three short windows scatter by about 20 per cent and are not quotable, because a few seconds at a quarter of a kilocalorie per second is a change of about a kilocalorie and a half against a quantised store [#1494/M/n=1].

The cadence has a consequence a mod feels immediately.
A model evaluated per character update tick is driven by the update loop rather than by a clock, so a Lua reproduction of it has to be hung off the same loop or carry its own accumulator.
There is no event the platform fires when the weight moves, and no per-hour or per-day hook to attach a slower model to, so the choice is between running every tick and integrating by hand between runs.

The method also publishes which way the weight is moving, and it does so before it stops on a client.
All three weight-direction flags are written at four sites inside `Nutrition.updateWeight`, every one of them ahead of the method's client skip [#2006/C/C-only].
That ordering is why a client can derive a weight direction it cannot derive a weight: the skip itself, and the discarded delta behind it, are [platform/mp-model.md](../platform/mp-model.md#ownership) ([#1097/M/n=1]), and the measured agreement of the flags across sides is [facts/body-and-weight.md](body-and-weight.md#weight-traits) ([#1100/M/n=1]).
For a mod this is the one piece of the weight model a client-side reader may use directly: the direction is derived locally on both sides from the same stores, while the quantity has to arrive from the server.
Reading the flags costs nothing and needs no transport, which makes them the cheapest signal available to a user interface that wants to show which way a character is heading.

The weight value also has a writer outside the model that any logged-in client can reach.
Vanilla's `player` `setWeight` client command, whose packet type requires only the login capability every connected client holds, sets any online player's weight on the server through `getPlayerByOnlineID(args.id)` and `getNutrition():setWeight(args.weight)`, with no admin check in its handler, in the `OnClientCommand` dispatch or in the Java receiver, and the player-stats admin panel sends it [T18.13].
The model then carries on from whatever value that command leaves, so a weight a mod writes on the server can be replaced between two of its own writes by a client that sends the command; this is read from the files and the bytecode and not exercised on a live server [T18.13].

<a id="clamps"></a>
### The store clamps

The clamps are the most load-bearing numbers on this page, because they bound the model above, they bound anything a mod writes, and they are the reason one whole vanilla effect is unreachable.
Every write into a store passes a clamp inside its setter, so a mod can never park a value outside the range the setter allows, whatever it asks for.
`Nutrition.setCalories` clamps the calorie store to the range -2200 to 3700 [#0022/M/n=2].
`Nutrition.setCarbohydrates`, `setProteins` and `setLipids` each clamp their store to the range -500 to 1000 [#0023/M/n=2].
Both signs of both clamps were probed once each on the server bus and landed exactly on the limits, which is why the ceilings and floors above are measured rather than read [#0022/M/n=2, #0023/M/n=2].

The clamps are two-sided, and the negative side is a working range rather than an error state.
Nothing clamps the calorie store at zero: a write of -100 read back -102.5664 on the server and -102.10 on the client, each side having run its own decay ticks since the write, so the pair is two readings of "not clamped" rather than a sync figure [#0901/M/n=1, #1102/M/n=1, #1197/M/n=1].
Negative stores are a normal state, and the loss arm of the weight model is real rather than an artefact of a floor [#0901/M/n=1, #1102/M/n=1, #1197/M/n=1].

A macro floor is reached in ordinary play rather than only under a deliberate write.
Carbohydrates hit their -500 floor in the fed run at the game-hour 40.0 sample, against 39.7 predicted, the crossing resolved only to the hourly sample [#0169/M/one-fixture].
That is the drain arriving at the floor on its own, without a single macro write, and the prediction that matched it came straight from the hard-coded decay rate.
The practical reading for a mod is that a macro store spends much of a long session pinned at its floor, so any design that treats a macro as a reservoir has to supply the reservoir itself.

A clamp truncates on contact and says nothing about it.
The setter returns no signal, writes the limit and carries on, so a dose larger than the remaining headroom is lost in silence rather than banked or refused, whether it came from a mod write or from a meal.
What the intake side does before it reaches these setters — the fraction rescaling, the burnt divisor and the rest of the modifier ladder — is [facts/eating-pipeline.md](eating-pipeline.md#modifiers).

Two consequences follow for a mod that keeps its own nutrient.
A vanilla store is a poor place to smuggle a mod quantity, because the clamp truncates silently and the drain moves the value between reads.
A mod store of its own needs an explicit range decision, and vanilla's own answer — a wide band on the calorie axis and a narrower, asymmetric one on each macro — is the only worked example the platform offers.

<a id="verified"></a>
### The model against three game-days on the server

The weight model is checked against the live dedicated server over three game-days, three times, each run's predicted weight delta integrated from that run's own calorie trace rather than from a nominal schedule.
The check has one shape: a scenario drives the world and records the server's `Nutrition` object once a game-hour, and a checker outside the game replays the formula above over those samples and compares the weight it predicts with the weight the server reports, inside a tolerance that is a fraction of the predicted delta with a floor in kilograms.
Integrating each run's own trace is what makes the comparison a test of the model rather than of the dosing schedule, because a clamp or a missed dose changes both sides of it equally.

| run | scenario | measured | predicted | residual | tolerance | claim |
|---|---|---|---|---|---|---|
| `scenario-20260910-052624` | gain, hunger and thirst unpinned | +1.045 kg over 34 alive game-hours | +1.057 kg | -0.012 | 0.159 | [#0158/M/one-fixture] |
| `scenario-20260910-054012` | gain, hunger and thirst pinned after every sample | +2.526 kg over 72.0 game-hours | +2.551 kg | -0.025 | 0.383 | [#0159/M/one-fixture] |
| `scenario-20260910-055029` | fast, no intake at all | -1.426 kg over 72.0 game-hours | -1.412 kg | -0.014 | 0.212 | [#0160/M/one-fixture] |

The unpinned run failed because its subject died at game-hour 35, so its live model check is the thirty-four alive game-hours; the whole-trace evaluation keys of that run are corpse readings taken thirty-seven game-hours after the stores stopped moving and are not citable [#0158/M/one-fixture].
The two runs that completed are one fixture each, the fed one with hunger and thirst reset after every sample and the fasting one with no intake at all [#0159/M/one-fixture, #0160/M/one-fixture].
One fixture is the bound that matters most here: the same fixture, the same build, the same dedicated-server path and the same admin character in every run, with the game clock accelerated and the day length a setting the fixture carries.
Every rate on this page is per game-second or per game-day for that reason, and a reading quoted in real seconds is only meaningful beside the day length it was taken at.

The residuals are the check's own quadrature rather than model error.
Integrating hourly samples at each interval's left endpoint biases the predicted weight by about 0.025 kg over three game-days, and re-integrating the same samples at the interval midpoint collapses the residuals to -0.0003 kg and -0.0002 kg, so about 0.03 kg per three game-days is the floor of what the check can resolve [#0164/M/one-fixture].
The midpoint figures come from an offline re-integration of the same two committed artifacts rather than from a fourth run [#0164/M/one-fixture].

What bounds a fed character is the ceiling, not the rate constant.
The fed run asked for 12000 kcal in six 2000 kcal doses and the store kept 7210, losing 4790 kcal to the clamp, the doses landing at game-hours 0, 12, 24, 36, 48 and 60 [#0165/M/one-fixture].
Day one of that run is a ramp: the store starts empty and the first dose only reaches 2000 kcal, so the day averages a `min(1, calories/4000)` factor of 0.583 and gains 0.647 kg, and the seventy-two-hour time-averaged factor of 0.757 gives 0.850 kg per game-day against 0.842 measured, the remaining gap being the check's own left-endpoint quadrature rather than a second effect [#0162/M/one-fixture].
Days two and three gain 0.940 kg per game-day at an average factor of about 0.84, the calorie trace oscillating between the 3700 ceiling and about 2990; only four of the seventy-three samples sit at the ceiling, so this measures a sawtoothing store at this dose rather than the factor a pinned store would give [#0163/M/one-fixture].

The floor bounds starvation the same way, and the fast ramps into it.
The fasting run reached the -2200 floor at game-hour 39 against 38.2 predicted at a flat 80 kg, arriving later because the burn falls with the weight, and its loss ramps with the deficit: 0.204 kg on day one and 0.576 kg on day two [#0166/M/one-fixture].
A game-day spent entirely on the -2200 calorie floor lost 0.646 kg, against the derived `8.5e-6 x 2200/2500 x 86400` of 0.646272, confirmed to three decimals on day three of that run [#0161/M/one-fixture].

The check is narrower than the numbers around it suggest, and the narrowness is a property of the evidence rather than of the model.
The three-day check asserts one thing, the weight delta over the run, across a 78.5 to 82.5 kg slice with no weight-band trait held, no trait threshold base, no `Nutrition = false` control and no intake, every run driving `setCalories` directly [#0170/M/one-fixture].
No burn rate, threshold crossing or macro multiplier is asserted, and every other figure in this subsection is a cross-check fitted off the same samples afterwards [#0170/M/one-fixture].

Half of the failed run measures a corpse, and that window settles two things about the update.
`Nutrition.update` stops on a corpse: weight, carbohydrates, lipids, proteins, hunger and health stay bit-flat for the thirty-seven game-hours after death, with carbohydrates frozen at -437.888763, short of their -500 floor [#0176/M/one-fixture].
An external `setCalories` write still lands on a corpse: calories stepped to 3700 at the hour-36 dose and held while every store the update drives stayed frozen [#0177/M/one-fixture].
Both readings come off the sample trace rather than off that run's evaluation keys, which are not citable [#0176/M/one-fixture, #0177/M/one-fixture].
The split between the two is the useful part: the update is what stops, while an external write into a store is not gated on the character being alive.
Anything that fills a calorie store from outside therefore has to manage hunger and thirst as well, because the calorie store answers to the writer while the body answers to its own clocks.

What the runs are good for, and what they are not, is worth stating plainly.
They establish that the decoded model reproduces on a live server to well under the check's own resolution over three game-days, on both the gain and the loss arm.
They establish nothing about the multiplier branches, about any threshold base a trait would install, or about what happens when the sandbox gate is off.
A mod that reuses these rates inherits both halves of that, and the second half is the one worth re-measuring before the rates are trusted outside the slice they were walked on.

The shape of the check is reusable even where its numbers are not.
Drive one store from the server, sample the whole object on a fixed game-clock cadence, integrate the model over the samples the run actually produced, and compare against the quantity the server reports rather than against the one the driver asked for.
That is what turns a formula read off bytecode into a statement about a live server, and it is the same shape any replacement model would have to pass before it could be trusted in play.

<a id="macro-effects"></a>
### What each macro does once stored

Calories are the only driver of weight, and carbohydrates and lipids act on it only as multipliers of the gain rate [#0180].
Proteins never touch weight; their two readers outside the weight model are `getRecoveryMod`, whose lipid and protein branches below -1000 (times 0.5) and below -1500 (times 0.2) can never fire because the setters clamp both stores at -500, and the Strength branch of `XP.AddXP`, which is live because its thresholds lie inside the clamp range and is stated at [perks-and-strength.md#xp-grants](perks-and-strength.md#xp-grants) [T18.18].
The clamp half of that reading is measured on both signs on the server bus, while the dead recovery branches and the live Strength branch are a code reading [T18.18].
The live multipliers in the same recovery method are the weight-band traits, which are [facts/body-and-weight.md](body-and-weight.md#weight-traits).

The Fitness experience gate in the same neighbourhood is keyed on the weight-band traits rather than on any macro, so it is not a protein reader, and it belongs to [facts/body-and-weight.md](body-and-weight.md#weight-traits).

Those floats are the whole of the object's serialised form, in a fixed order that `Nutrition.save` writes and `Nutrition.load` reads back ([#0108], [facts/wire-packets.md](wire-packets.md#player-stats-packet)).
A protein value therefore survives every round trip the object makes, and the one reader that acts on it is the Strength experience branch.

So the complete list of live consumers of the four intake stores is short.
Calories drive the weight direction and the weight rate; carbohydrates and lipids scale the gain rate and nothing else; proteins are written, drained, clamped and saved, and act only by scaling Strength experience.

The consequence for a nutrition mod is the emptiness rather than the numbers.
The carbohydrate store as an energy pool and any notion of diet quality are dead space in this build, and a protein surplus has exactly one vanilla consumer, Strength experience gain, so a parallel nutrient store collides with vanilla only where it moves the vanilla protein store [T18.18].
It also means a mod cannot express a nutrient by leaning on an existing macro's effects, because outside the gain multipliers and the Strength branch there are none to lean on.
Every consequence a mod nutrient is to have must therefore be written by the mod, and the vanilla behaviour it has to avoid disturbing is the gain multiplier pair and, where it writes the protein store, the Strength branch.

## Walls and bounds
<a id="walls"></a>

The nutrition core is one of the most closed surfaces in the platform: the object cannot be extended or replaced, its constants are compiled in, and the one switch that reaches it turns the whole model off rather than tuning it.
What follows is that set of restrictions as facts, each with the mechanism that closes it.

No class in the jar contains the literal `setNutrition` in any identifier form, so the `Nutrition` object cannot be substituted [#1185/C/C-only].
`Nutrition.update` is not among the seven updaters a `CalculateStats` handler skips: it hangs off `BodyDamage.Update` at `updateInternal`, so a true return does not stop the macro drain [#1192/C/C-only].
The thresholds and rates inside the weight update are fixed on this build, and the only nutrition-side lever is the sandbox boolean, whose consequence is that the weight and trait coupling goes with it [#1127/C/C-only].
A client cannot own the weight quantity at all, so anything keyed on a weight band is evaluated on the server or fed an explicitly transmitted value ([#1097/M/n=1], [platform/mp-model.md](../platform/mp-model.md#ownership)).
The whole weight model is measured across one narrow slice of the weight axis, with no weight-band or appetite trait held and no control run with the sandbox gate off, and the bound is stated with the check itself at [the server check](#verified).
The macro multiplier branches of the gain rate have never been entered by a run, so their arithmetic ceiling is derived rather than observed, as the weight model above states.
The drain cannot be stopped one store at a time either: the sandbox gate is the whole update or nothing, and the stat hook that skips the other updaters does not reach it.
The direction flags are the only part of the weight model a client may act on, and they carry a direction rather than a magnitude.
Every reading here is a dedicated server with one client, one fixture and one admin character; single-player is never claimed.
Not covered: the character model, the animation system and the interface, which read the weight value and which this library never opened; and the two maintained calorie extremes, whose readers are the open row below.

## Open
<a id="open"></a>

- Whether `Nutrition.caloriesMax` and `caloriesMin` have any reader at all is unsettled: they are maintained but a jar-wide reader scan found none, so they are possibly interface or debug only — settled by a fresh jar-wide reader scan of both fields on this build, with the exposer dump beside it [#0190/C/snapshot/open].
- Decision the design must take: whether the mod reproduces vanilla's three arms in Lua behind the sandbox gate or lives beside them, forced by the gate taking the drain, the burn and the weight arm together while intake carries on unguarded ([#0067], [facts/eating-pipeline.md](eating-pipeline.md#sandbox)).
- Decision the design must take: whether a mod nutrient is stored with the same two-sided clamp shape as vanilla's, forced by the clamps above being two-sided and by negative stores being an ordinary state rather than an error state.
- Decision the design must take: whether the mod's own weight model keeps a macro multiplier at all, forced by vanilla's multiplier branches never having been entered by a run and so carrying no measured behaviour to match.
- Decision the design must take: whether the mod's weight model accepts a weight written through vanilla's `setWeight` client command or overrides it, forced by that command writing any online player's weight for any logged-in client with no admin check [T18.13].
- Decision the design must take: whether the mod writes the vanilla protein store from its own protein model, forced by the Strength experience branch reading that store directly [T18.18].

## See also

- [facts/eating-pipeline.md](eating-pipeline.md) — how food fills these four stores, the modifier ladder it passes through, and the sandbox option that gates the update.
- [facts/body-and-weight.md](body-and-weight.md) — the passive burn branches that move the calorie store, the weight bands the weight value falls into, and what each band trait does.
- [facts/perks-and-strength.md](perks-and-strength.md#xp-grants) — the experience grants, the protein branch on Strength experience and the Fitness gate's caller.
- [platform/mp-model.md](../platform/mp-model.md) — which side owns each quantity, the push that carries it, and what a client's copy is.
- [facts/wire-packets.md](wire-packets.md) — the field contracts of the packets that carry these stores, and the measured desyncs.
- [reference/experiments.md](../reference/experiments.md) — the named experiments the open row above points at, with the profile, driver and discriminating reading each one needs.
