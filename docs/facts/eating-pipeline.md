# The eating pipeline
Verified against 42.20.4 (b0bbce05d5) · 2026-10-01 · scope: what a food item or a fluid container delivers to a player's stats and `Nutrition` when it is eaten or drunk — the getters, the fraction, the modifier ladder, the leftover, the drink path and its Lua drivers, the duration and the sandbox gate; the hook dispatch and the packet field lists are handed off.

## Key facts

- One method does all of it: `IsoGameCharacter.Eat` writes the five stats, then the four nutrients, then pain, cold and the sickness cure, then `JustAteFood`, then the server's sends, then the `OnEat` hook, and consumes or rescales the item last [#0006].
- The fraction is a share of the whole item, not of what is left: when `baseHunger` and `hungChange` are both non-zero, `f = clamp01(baseHunger * f / hungChange)` [#0014/M/one-fixture].
- Nutrition is written before the `OnEat` hook fires and before the item is consumed, so a hook sees the post-intake store and the pre-consume item [#0008].
- Burnt divides the four nutrients by 5, and that is the only nutrition modifier: otherwise they are bare field reads with no cooked, burnt, rotten or frozen branch [#0019/M/one-fixture, #0036/M/one-fixture].
- Hunger is state-modified: cooked at times 1.3 takes precedence over burnt, which divides by 3, with stale dividing by 1.3 and rotten by 2.2 [#0029/M/one-fixture, #0030/M/one-fixture, #0031, #0032/M/one-fixture].
- Thirst runs the opposite precedence: burnt divides by 5.0 and beats cooked, which divides by 2.0 [#0033/M/one-fixture, #0034/M/one-fixture].
- HUNGER and THIRST are clamped to 0 to 1 on every write, so overshoot is silently discarded [#0021/M/one-fixture].
- `Item.InstanceItem` divides the script's `HungerChange`, `ThirstChange` and `EnduranceChange` by 100 and stores `Calories`, `Carbohydrates`, `Lipids` and `Proteins` unscaled [#0011/M/one-fixture].
- A fluid's `Properties` are the effect of one litre, the container multiplies them by its litres, and a drink spends that aggregate times the fraction drunk [#0630, #0633].
- The sandbox `Nutrition` option gates only `Nutrition.update()` — drain, calorie burn and weight — and never the `Eat` and `DrinkFluid` store writes [#0067].
- Vanilla has no overeating effect in Java, and its one cap, the refusal at FOOD_EATEN level 3, is client Lua except in the open-and-eat craft, whose Java refuses at the same level [#3596/C/C-only] [#3597/C/C-only] [#3599/C/C-only] [#0522/C/C-only] [#3895/C/C-only].

## How it works

Each reading holds on the build its row's bound names: the stamp's build unless the bound names a re-read or a later run.

<a id="getters"></a>
### The five `Food` getters

Five getters differ by a letter; reading the wrong one is the commonest intake error.

- `getBaseHunger()` returns the item's stored `baseHunger` unchanged and is read only by the fraction rescale, so an eat fraction means a share of the whole item rather than of what is left [#0001].
- `getHungChange()` is a bare read of the instance's remaining `hungChange` with no state modifiers; it drives the fraction rescale and both crumb rules, it is what `multiplyFoodValues` shrinks, and it is what `Eat` zeroes when the item is finished [#0002].
- `getHungerChange()` is the state-modified hunger value — the cooked, burnt, stale and rotten ladders, each floored at 0.01 with the sign kept — and drives the HUNGER stat [#0003].
- `getThirstChange()` is the state-modified thirst value that drives the THIRST stat, and its raw value also gates the second crumb rule [#0004].
- `getThirstChangeUnmodified()` is a bare read of `thirstChange` and is what `multiplyFoodValues` reads, so cooked and burnt multipliers are never baked into the leftover [#0005].

The two state-modified getters are the only ones on the intake path: a five-item, five-state matrix found no other intake number that moved with item state [#0102/M/one-fixture].
A mod reads `getHungerChange` and `getThirstChange` for what the player will receive, and `getHungChange` and `getThirstChangeUnmodified` for what the item still stores; a value read through the modified pair and written back onto the item compounds the state ladder each time.

<a id="eat"></a>
### The order of writes inside `Eat`

`IsoGameCharacter.Eat(InventoryItem,float,boolean)` writes in one fixed order: the fraction is clamped and rescaled, then the five stats, then the four nutrition setters, then pain and cold reduction and the food-sickness cure, then `JustAteFood`, then the server's packet sends, then the `OnEat` hook, and only then is the item consumed or scaled down and synced [#0006].
The other two overloads are trampolines: `Eat(item,f)` calls `Eat(item,f,false)` and `Eat(item)` calls `Eat(item,1.0f)` [#0007].
Nutrition is written before the `OnEat` hook fires and before the item is consumed, so a hook sees the post-intake `Nutrition` and the pre-consume item [#0008].
`BodyDamage.JustAteFood(food, f, useUtensil)` is the only use of the `useUtensil` argument inside `Eat` [#0009], so a utensil changes mood and duration and never intake.
`Eat` adds the item's endurance and fatigue changes times the fraction to the `ENDURANCE` and `FATIGUE` stats, and the server's follow-up player-stats send names both in its mask [#0017/M/one-fixture, #0115].
Which items write an endurance change is [food-item-model#script-keys](../facts/food-item-model.md#script-keys); how `OnEat` resolves and which side calls it is [lua-platform#script-hooks](../platform/lua-platform.md#script-hooks); the packets sent from inside the method are [wire-packets#eat-food-packet](../facts/wire-packets.md#eat-food-packet).

The eat action's completion step runs server-only and a Lua wrapper of it fires before the eat hook (the server recorded wrapper then hook, the client the hook only), so a mod that needs the item intact before the eat consumes it sits in the wrapper, which installs on the client too and stays silent there [#0928/M/n=1].

The custom-weight write multiplies by `f0`, the clamped argument, and not by the rescaled `f`, so on a part-eaten custom-weight item weight and hunger drift apart; the bytecode fixes which local is used and the size of the drift is unmeasured [#0010/C/inference].

A `Food` item that carries a `ThirstChange` goes through `Eat` exactly like solid food, its thirst and macros scaled by the same fraction, and `CustomMenuOption = Drink` changes only the animation and the duration formula — measured on one drink item across five states [#0083/M/one-fixture].
That path shares no code with the fluid containers below.

<a id="modifiers"></a>
### The modifier ladder

Every modifier an intake passes through, in the order `Eat` and its callees apply them.
The four nutrient stores' own clamps are [nutrition-core#clamps](../facts/nutrition-core.md#clamps) ([#0022/M/n=2], [#0023/M/n=2]); the poison, taint, rot-sickness and dangerous-uncooked rolls in `JustAteFood` are [food-item-model#poison](../facts/food-item-model.md#poison) ([#0050], [#0051], [#0052], [#0053]).

| Modifier | Applies to | Effect |
|---|---|---|
| argument clamp | the fraction | `f = PZMath.clamp(f, 0, 1)`, before anything else [#0013] |
| `baseHunger` rescale | the fraction | when `baseHunger` and `hungChange` are both non-zero, `f = clamp01(baseHunger * f / hungChange)`; a half-eaten apple at menu fraction 1.0 gave 47.5 kcal rather than 95 [#0014/M/one-fixture] |
| hunger crumb rule | the fraction | promoted to 1 when `hungChange` is negative and the leftover `hungChange * (1 - f)` would be greater than -0.01 [#0015] |
| thirst crumb rule | the fraction | promoted to 1 when `hungChange` is 0, `thirstChange` is negative and the leftover `thirstChange * (1 - f)` would be greater than -0.01 [#0016] |
| fraction scaling | THIRST, HUNGER, ENDURANCE, STRESS, FATIGUE | each getter times the rescaled fraction is added to its stat; one item at a quarter gave -0.04 hunger and -0.0175 thirst [#0017/M/one-fixture] |
| fraction scaling | calories, carbohydrates, proteins, lipids | each times the rescaled fraction is added to the player's store; an apple at 1.0, 0.5 and 0.25 gave 95, 47.5 and 23.75 kcal, exact on all six numeric fields [#0018/M/one-fixture] |
| burnt | the four nutrients | divided by 5; apple 95 to 19, steak 220 to 44, bread 532 to 106.4, carrots 25 to 5 [#0019/M/one-fixture] |
| non-player guard | the four nutrients | skipped when `Type.tryCastTo(this, IsoPlayer.class)` is null, so an animal or an NPC gets stats, pain, cold and sickness but no nutrient write [#0020] |
| stat clamp | HUNGER, THIRST | registered with a minimum of 0 and a maximum of 1, every write clamped, overshoot silently discarded; a satiated character kept all 532 kcal of rotten bread and about none of its hunger relief [#0021/M/one-fixture] |
| fraction scaling | pain reduction, cold reduction | `getPainReduction() * f` and `getFluReduction() * f` added to the body's two reductions [#0024] |
| food-sickness cure | FOOD_SICKNESS, POISON | `abs(foodSicknessChange) * f` removed from both, when FOOD_SICKNESS is above its minimum, the item's value is negative and the edible-buff timer has expired [#0025] |
| Iron Gut | the edible-buff timer | re-armed to `Rand.Next(80, 150)` [#0026] |
| Weak Stomach | the edible-buff timer | re-armed to `Rand.Next(200, 280)` [#0027] |
| neither stomach trait | the edible-buff timer | re-armed to `Rand.Next(120, 230)` [#0028] |
| cooked | `getHungerChange` | times 1.3, taking precedence over burnt and rot; one item, -0.16 to -0.208 [#0029/M/one-fixture] |
| burnt | `getHungerChange` | `max(abs(h)/3.0, 0.01)` with the sign kept; one item, -0.0533 [#0030/M/one-fixture] |
| stale, `offAge <= age < offAgeMax` | `getHungerChange` | `max(abs(h)/1.3, 0.01)` with the sign kept [#0031] |
| rotten, `age >= offAgeMax` | `getHungerChange` | `max(abs(h)/2.2, 0.01)` with the sign kept; one item, -0.0727 [#0032/M/one-fixture] |
| burnt | `getThirstChange` | divided by 5.0, taking precedence over cooked, the opposite order to hunger; two items [#0033/M/one-fixture] |
| cooked | `getThirstChange` | divided by 2.0; two items [#0034/M/one-fixture] |
| rotten | `getThirstChange` | nothing, there is no rotten branch: a rotten apple still gave -0.07 and a rotten hot drink -0.20 [#0035/M/one-fixture] |
| none | `getCalories`, `getCarbohydrates`, `getLipids`, `getProteins` | bare field reads with no cooked, burnt, rotten or frozen modifier; the matrix's cooked, rotten and frozen rows all delivered full values, rotten bread 532 kcal and 99 g of carbohydrate [#0036/M/one-fixture] |
| frozen | the six intake numbers | none of them: all five matrix items identical fresh against frozen; frozen moves boredom and unhappiness only [#0037/M/one-fixture] |
| burnt / stale / cooked | `getEnduranceChange` | divided by 3 / divided by 2 / times 2 [#0038] |
| burnt / stale / rotten / cooked | `getStressChange` | divided by 4 / by 1.3 / by 2 / times 1.3 [#0039] |
| burnt / stale / rotten / cooked | `getFoodSicknessChange` | divided by 3 / by 1.3 / by 2.2 / times 1.3, truncated to int [#0040] |
| frozen | `getBoredomChange`, `getUnhappyChange` | plus 30 each, unless the type is `Icecream` or the item carries the `GOOD_FROZEN` tag [#0041] |
| burnt / stale / rotten | `getBoredomChange`, `getUnhappyChange` | plus 20 / plus 10 / plus 20 each [#0042] |
| bad-cold / good-hot | `getUnhappyChange` | plus 2 when bad-cold, cookable, cooked and below 1.3 heat; minus 2 when good-hot, cookable, cooked and above 1.3 heat [#0043] |
| fertilized | boredom, unhappiness, stress | every modifier bypassed and the raw field returned, and `isRotten()` forced false [#0044] |
| `RemoveNegativeEffectOnCooked` | `thirstChange`, `unhappyChange`, `boredomChange` | each set to 0 if positive on the cook transition, permanently and once, nutrition untouched [#0045] |
| `removeUnhappinessWhenCooked` | `unhappyChange` | set to 0 on the cook transition [#0046] |
| utensil | BOREDOM | with a utensil, times 1.25 when `boredomChange * f` is negative, else times 0.75; without one, times 1 [#4153/C/C-only] |
| utensil | UNHAPPINESS | with a utensil, times 1.25 when `unhappyChange * f` is negative, else times 0.75; without one, times 1 [#4154/C/C-only] |
| HUNGER at its minimum | `healthFromFoodTimer` | plus `abs(getHungerChange()) * f * getHealthFromFoodTimeByHunger()`, doubled for a cooked item, capped at 11000.0 [#0054] |
| alcoholic | intoxication | routed to `JustDrankBooze(food, f)` [#0055] |
| Tutorial game mode | the sickness rolls | `JustAteFood` returns early, after the mood writes and before the sickness rolls [#0056] |
| none | `Nutrition.weight` | `Eat` never writes it: its nutrition block writes the four nutrient setters and nothing else, the weight delta 0.0000 on every matrix row [#0061/M/one-fixture] |

Item state moves hunger, thirst, endurance, stress, food sickness, boredom and unhappiness and never the four nutrients, and the hunger and thirst ladders run opposite precedence, so a design that models cooking or rot through the nutrient columns models something vanilla leaves flat.

<a id="partial"></a>
### Partial eating

The eat menu offers the fractions 1, 0.5 and 0.25 [#0078].
Half is offered only when `abs(hungerChange * 100)` is at least 2 and at least half of `baseHunger`, and Quarter only when it is at least 4 and at least a quarter of `baseHunger` [#0079].
`baseHunger` is initialised equal to `hungChange` at instantiation and is not scaled by `multiplyFoodValues`, so it keeps the full-portion value while `hungChange` shrinks [#0080].
Because the fraction is a share of the whole item, a quarter of a half-eaten item asks for half of what is left, and a leftover half-apple eaten at menu fraction 1.0 delivers 47.5 kcal rather than 95 — one item, measured on the server [#0081/M/one-fixture].
The same rescale arithmetic is duplicated in Lua for the eat tooltip and the utensil-scrape sound, so a mod that changes the rescale has three sites to keep in step [#0082].
Read live around three quarter eats of one Banana, the drop in raw hunger over the base hunger was 0.25 each time while the drop over the hunger before the eat was 0.25, 0.333 and 0.5, `Eat`'s rescaled fraction, so a share of the whole item and a fraction of what is left are two different numbers on every eat after the first [#2831/M/n=1].
A partial eat lowers the item's stored calories, carbohydrates, proteins, lipids and `hungChange` by one factor, `multiplyFoodValues(1 - share)`, and never its `baseHunger`, so the ratio of stored calories to `hungChange` survives every partial eat and `getCalories() * getBaseHunger() / getHungChange()` read before an eat is the calories the instance held when `baseHunger` equalled `hungChange` [#3326/C/C-only].
The HUNGER an eat applies is the state-modified hunger times that fraction, added to the stat and clamped to its range, the fraction taken as 1 whenever what would remain of `hungChange` sits above -0.01; Eat Half and Eat Quarter request 0.5 and 0.25, which the eat action passes to `Eat` unchanged [#3556/C/C-only].
The raw `hungChange` is the portion three vanilla spending paths divide by — `Eat`'s fraction, a use-based `consumeHunger` and an evolved recipe's share of an ingredient — so a write to an instance's `hungChange` alone moves how much of the item each later portion takes, while a change to the HUNGER an eat already applied moves none of them [#3557/C/C-only].

The remainder is scaled by `multiplyFoodValues(1 - f)`, which multiplies fifteen stored fields including calories, carbohydrates, proteins and lipids, and truncates `fluReduction`, `foodSicknessChange` and `poisonPower` to int so those three erode faster than linearly; half an apple left `calories 47.5` and `hungChange -0.08` [#0057/M/one-fixture].
At a fraction of exactly 1 the item's `hungChange` is set to 0 and `UseAndSync()` consumes it [#0058/M/one-fixture].
It does not stay 0: by the jar's reading the consume step divides by the zeroed `hungChange` and leaves the finished item's raw hunger and scaled fields NaN, and a server-side wrapper computing its share from `getHungChange()` read NaN on two finishing eats, the item's own fields not read directly, so a reader after the eat treats a finishing eat as the whole remainder rather than divide by what the item says [#2832/M/n=1].
After the multiply, an item whose old `hungChange` was 0, whose old thirst was negative and whose new thirst is greater than -0.01 has its `hungChange` set to 0 and is consumed, the crumb rule applied to what is left [#0059].
Otherwise a custom-weight item's weight becomes `(w - base) - f0 * (w - base) + base`, where `base` is the actual weight of its `replaceOnUse` item and 0 when it has none [#0060].

A cancelled eat resolves on the server, and two guards there can make it apply nothing at all — no stats, no nutrition, no leftover scaling and no consumption ([#0112], [mp-model#ownership](../platform/mp-model.md#ownership)); an item pass that rewrites hunger values can land a value under that threshold and silently disable partial eating for that item.
The guard sits on the cancel route only: a completed eat of an item whose hunger was driven under it, against a full-size base hunger, delivered the whole item, because the rescale clamps to 1 there [#2836/M/n=1].

<a id="fluid-path"></a>
### The drink path and the per-litre chain

A B42 drink is not a `Food` item: it is a `base:normal` item carrying a `component FluidContainer` joined to a `fluid` definition in `generated/fluids*.txt`, and `media/scripts/fluids/` does not exist — read from the script tree on the stamped build, not measured [#0603/C/snapshot].
The loader stores a fluid's `Properties` as written: fifteen `equalsIgnoreCase` keys, each through `Float.parseFloat`, with no arithmetic [#0628].
Four of the fluid's getters divide the stored value by 100 — `getHungerChange`, `getThirstChange`, `getStressChange` and `getFatigueChange` — while `getCalories` and the three macro getters do not [#0629].
The container multiplies the fluid's `Properties` by the litres it holds, so `getProperties()` is already litres-weighted and the per-litre convention lives in the container, never in the loader [#0630].
Those litres are a full container's: the initial amount defaults to `Capacity` when the script writes none, the `:share` suffix multiplies it and the add clamps to the capacity [#0632/C/snapshot].
Drinking spends that litres-weighted aggregate times the fraction drunk [#0633].
The fraction is a share of the container's current contents, not of its capacity, so a second half takes half of what is left [#1733/C/C-only].
Measured, a full 0.3-litre can wrote 120.000031 calories, 31.200001 grams of carbohydrate, minus 0.036 hunger and minus 0.090 thirst — the per-container columns exactly, the hundredfold division applied to the two stat columns — and the same can at half wrote 60.0 and 15.6 and was left holding 0.15 litres [#1892/M/n=1].
A sealed bottle takes no fluid: `Base.BeerBottle` and `Base.BeerImported`, scripted with `Opened = false` and an opening recipe, each read back 0 litres after a server-side fill of 0.3 into a capacity of 0.30000001192092896 [#3889/M/n=1].
`InitialPercentMin` and `InitialPercentMax` land in `initialAmountMin` and `initialAmountMax`, and the initial amount is the minimum when the two are equal and a uniform `Rand.Next(min, max)` otherwise, rolled once per container when it is read from its script [#0659].
That value is litres despite the key name — nothing multiplies it by `Capacity` — so a water dish's 0.05 to 0.95 draw is clamped back to its 0.3-litre capacity and a cowboy canteen never spawns above 1 litre of its 1.8 [#0660].

`DrinkFluid` shares no code with `Eat`.
It writes calories, carbohydrates, proteins and lipids from the container's `SealedFluidProperties` before any fluid is removed, with no burnt divisor and no other modifier [#0064/C/C-only].
It takes THIRST, HUNGER, ENDURANCE, STRESS, FATIGUE, BOREDOM and UNHAPPINESS from the `FluidConsume` that removing the fluid returns, and does not re-multiply them by the fraction [#0065/C/C-only].
It takes POISON from the container, multiplies it by 0.75 when the fluid is tainted, zeroes it with Iron Gut when tainted and otherwise halves it unless the primary fluid is bleach, and with Weak Stomach multiplies it by 1.2 when tainted or by 2 otherwise [#0066/C/C-only].
Four overloads funnel into the one method, which has no fraction clamp, no `baseHunger` rescale, no crumb rules, no `OnEat` hook, no `JustAteFood` and no eat packet, and never reads its boolean third argument [#0084/C/C-only]; its whole body holds no modData reference and no Lua call [#2687/C/C-only].
`FluidConsume` extends `SealedFluidProperties` and declares only an amount and a poison effect of its own, so it carries the removed aggregate's nutrition with no per-fluid breakdown and the mix has to be sampled before the removal [#2688/C/C-only].
Drinking completes on the server and sends only the player-stats sync, with no eat packet, so a drink's calories reach a client only on the once-a-second player-stats packet [#0649]; that packet's contract is [wire-packets#player-stats-packet](../facts/wire-packets.md#player-stats-packet).
When the removed `FluidConsume` carries alcohol, `DrinkFluid` hands it to `BodyDamage.JustDrankBoozeFluid` after its seven stat writes, and on a server its closing player-stats sync carries intoxication in its bitmask [#2925/C/C-only].
Beer's fluid carries 0.05 alcohol per litre, so a litre of beer drunk at hunger 0.6 or below adds 20 intoxication and half a litre 10 [#2926/C/arith.]; the writer and the decay are [the stat's](character-stats.md#tick-order).

The drink action has one `DrinkFluid` call, in `ISDrinkFluidAction:updateEat`, which `complete` reaches unguarded and which calls `syncItemFields()` right after each `DrinkFluid` [#2689/C/C-only].
The action calls it incrementally, consuming only the difference between the target ratio and what has already gone, so the call is idempotent; the update makes it when the process is not a client and the animation event when it is a server [#0085/C/C-only].
On a live server, the game's own drink action on a full 0.3-litre cola can made a wrapper of `updateEat` and `complete` count 29 `updateEat` calls and one `complete` on the server and 0 on the client (the client's install not witnessed), and a half juice box added 32 calls and one completion, none on the client [#2825/M/n=1].
The timed action delivered what the direct call delivers, a full can 120.48 kcal after a drift correction and the half juice box 40.12, so the incremental calls sum to the container [#0148/M/n=1].
A direct `DrinkFluid` call, the harness's shipped `drink` command, moved the store by the same 120 kcal and neither wrapper counted it, so a drink-action wrapper sees the action route and nothing else [#2827/M/n=1].
The drink path is therefore interceptable the way the eat path is, through a server-side wrapper of the drink action's `updateEat` and `complete`, and a wrapper there misses the direct `DrinkFluid` route [#1279/M/n=1].
A drink action on a container the server has never seen raises in the server's `ISDrinkFluidAction.new` and drinks nothing [#2943/M/n=1].

Drinking from a world water source takes a second route: `ISTakeWaterAction`, queued with no item, moves the litres into a temporary container and calls `DrinkFluid` on it with a fraction of 1 before disposing of the container, so a wrapper of the drink action's `updateEat` never sees it [#2690/C/C-only].
Its `new` sets the litres to drink to twice THIRST, capped by the source, and records twice THIRST as its start, and each `updateUse` transfers the target share less what it counts as drunk, which it reads back from THIRST itself [#2930/C/C-only].
Each step's litres pass through `transferFluid(_amount)`, which moves `_amount` litres into a temporary container of that capacity and drinks all of it, reached from `update` off a client, from the `takeFluid` animation event on a server and from `complete` [#2931/C/C-only].
On a server the action is built by calling the type's `new` with the client's arguments, so the THIRST it starts from is the server's [#2932/C/C-only].
Measured live, the world-source drink runs on the server: queued from the client on a source 5.7 tiles away it dropped the server's THIRST from 0.4099 to 0.0012 within 7.3 s, and no drink wrapper saw it [#2942/M/n=1].

The auto-drink is a third route, a direct `DrinkFluid` call.
It takes its water from the first water-only item in the top-level inventory list, every fluid in the `Water` category, skipping a tainted one only while the tainted-water text is on and taking one under 0.12 litres unless it is a bag [#2927/C/C-only].
The only `Water`-category fluids are water, tainted water and carbonated water, each worth 0.5 thirst per litre, so its `min(amount, 2 × thirst)` litres lower THIRST by half their volume and a THIRST drop across the call is twice that drop in litres [#2928/C/arith.].
It keeps no timer or cooldown, so a caller that restores THIRST between calls gets a drink on every call [#2929/C/C-only].
Measured live under a `CalculateStats` handler's call: THIRST held just under 0.1 drank nothing, crossing 0.1 drank 0.2001 litres, and THIRST written to 0.3 emptied the canteen's remaining 0.4289 litres by the next server tick and read 0.08608 at the first probe after the write, both branches of `min(amount, 2 × thirst)` [#2939/M/n=1].
No action wrapper saw any of the 0.9 litres it drank: a wrapper of `ISDrinkFluidAction:updateEat` counts none of it [#2940/M/n=1].
Under zeroed rise rates and a once-a-minute THIRST write the auto-drink still fires and its drop survives to the next write: a write of THIRST 0.3 with a 0.9-litre canteen drew a 0.6-litre drink within two server ticks and THIRST 0, held at all 36 per-tick samples to the next write; that write's 0.3 drank the remaining 0.3 litres within two ticks and left THIRST 0.15, held at all 36 samples to the next write [#3382/M/n=1].
The server's `autoDrink` flag does not hold a Lua write: `setAutoDrink(false)` read back false and was true again 13.8 s later, so it cannot keep a player from auto-drinking, and the `AutoDrink` hook is unmeasured [#2941/M/n=1, #2769/C/C-only].
How a container's mix is read from Lua, and why a per-fluid mod value cannot ride the fluid block, are [food-item-model#fluid-blocks](../facts/food-item-model.md#fluid-blocks).

Six traps sit on this path.
An endurance change is divided by 100 for an item but not for a fluid, and no shipped fluid writes a non-zero one, so a modded fluid's endurance value would be off by a hundredfold — read from the script tree on the stamped build, not measured [#0666/C/snapshot].
A fluid's `unhappyChange` is applied twice when the container is drunk, once to BOREDOM and once to UNHAPPINESS, so one drink moves both moodles by the container's whole aggregate: minus 3 on a full 0.3-litre cola can and minus 10 on a 0.2-litre juice box, the doubling being in the application rather than in the number [#0667/M/n=2].
`foodSicknessChange` has the opposite sign convention on the two paths, the drink path requiring a value above 0 and the eat path one below 0, and all 61 fluids write 0 [#0668/C/snapshot].
The fraction is unclamped in `DrinkFluid`, and the nutrition block multiplies before any clamp, so a fraction outside 0 to 1 would deliver nutrition the container never gave up [#0669].
`ISDrinkFromBottle` does not call `DrinkFluid` at all: it hardcodes a thirst change of -0.1 per use and delivers zero nutrition, and its only caller chain starts at a function with no caller anywhere in the shipped Lua, so it is dead code on this build [#0670/C/snapshot].
`FluidDefinitionScript.Load` sets the enum fluid type and leaves the type string null when the fluid's name matches a built-in constant, and sets the modded type plus the string otherwise, the two routes mutually exclusive, so the string names only 34 of the 61 definitions and a fluid census pairs the string with the enum [#0654/M/n=2].

<a id="pill-path"></a>
### The pill path

For a `PillsVitamins` item `JustTookPill` adds the item's fatigue change to FATIGUE, halved when INTOXICATION is above 10, and then its stress change to STRESS [#2954/C/C-only].
It ends by calling the pill item's `OnEat` Lua function, when the drainable names one, with the item and the character, and then uses the item up one step [#2955/C/C-only].
Measured live, the action runs on the server: a `Base.PillsVitamins`, the caffeine-pill item with `fatigueChange = -4.0`, taken through the game's pill action lost one use on the server's copy, 1.0 to 0.8, and raised STRESS to 0.0077 and 0.0071 on two boots; with sleep allowed and needed FATIGUE fell from 0.6040 to 0.5641, and with sleep disabled no fatigue change showed [#2952/M/n=1].
What a mod's eat and drink wrappers see of a pill is [new-nutrients#record-engine](../areas/new-nutrients.md#record-engine).

<a id="eat-type"></a>
### `EatType`

`EatType` has no Java consumer and never touches hunger, thirst or nutrition: a jar-wide scan on 2026-09-10 found no site for it, only script generators [#0096/C/snapshot].
It picks the eat animation's food type and the second-hand utensil model, and the two pot types override the hand models with the item itself [#0097].
A two-hand bowl takes the spoon on its own early-return branch, while a can, a can drink, a two-hand item and a plate take the fork-or-spoon branch, and both branches feed the utensil flag [#0098].
A can or can drink eaten with a utensil plays the canned-scrape sound once the action passes 0.7 of its duration, and only when this eat finishes the item [#0099].
An item pass may therefore set it for presentation alone; the key itself is [food-item-model#script-keys](../facts/food-item-model.md#script-keys).

<a id="duration"></a>
### The eat duration

The eat action sets its budget to 232 times the eating loop for food and 171 times the loop for a drink-type item, with the loop stepping to 2 and 3 at a hunger consumed of 30 and 80 for food or a thirst of 3 and 6 for a drink; one whole fresh apple reported a budget of 232.24, which is 232 times a loop of 1 times a body-temperature modifier of about 1.001 [#0071/M/one-fixture].
An item that consumes no hunger gets 460 [#0072].
A positive `EatTime` on the item hard-overrides the computed value [#0073].
A pop-can eat type gets 160 [#0074].
A character with the instant-timed-action cheat gets 1 [#0076].
Eating with a utensil subtracts 1 from the eating loop when it is at least 2, which the drink branch undoes for drink-type items by reassigning the loop [#0049].
The base timed action then multiplies the budget by `(1 + UNHAPPY/4) x (1 + DRUNK/4) x (1 + handPain/300) x getTimedActionTimeModifier()`, the hand-pain term skipped because the eat action ignores hand wounds [#0075].
The lines that compute a budget before all of this are dead, unconditionally overwritten by the loop arithmetic [#0101].
The action refuses to start at a food-eaten moodle level of 3 or higher, and the menu shows a cannot-eat-more tooltip instead [#0077].

The real multiplayer path lands about 5.5 s after the action is queued — one session on a dedicated server with one client [#1189/M/n=1].
A timed action's `maxTime` tick budget does not scale with `settimespeed`: on a dedicated server at DayLength 1 an eat with `maxTime` 464.04 took 10.194 s of driver wall from the queue to the polled landing at `settimespeed 5` (a game-time multiplier of 23.80) and one with `maxTime` 464.11 took 10.091 s at a multiplier of 0.80, so the eat's span in game time grows with the clock's speed [#0141/M/n=1].
No duration term changes what a completed eat delivers, so a measurement that needs a known intake drives the store on the server rather than queuing timed eats.

<a id="overeating"></a>
### Eating when full

`IsoGameCharacter.Eat` refuses only an item that is not `Food`: it has no branch on the eater's HUNGER, and the only character stat it reads is FOOD_SICKNESS, for the sickness cure [#3596/C/C-only].
An eat at HUNGER 0 therefore still adds every macro in full, while the stat clamp discards the hunger it would have removed [#0021/M/one-fixture].
`JustAteFood` reads HUNGER once, at the health-from-food timer's gate, and its other stat writes are poison, pain, boredom and unhappiness [#3597/C/C-only], beside an alcoholic item's intoxication through `JustDrankBooze` [#2924/C/C-only].
Neither method names DISCOMFORT, so vanilla adds no sickness, discomfort or other stat for eating while full [#3597/C/C-only].
`Eat` adds the item's hunger change before it calls `JustAteFood`, so the gate reads the HUNGER the eat leaves: an eat fills the timer, and so can raise the FOOD_EATEN moodle, only when `abs(getHungerChange() * f)` is at least the HUNGER it found, whatever wrote that HUNGER last [#3598/C/inference].
A mod that writes HUNGER on the server therefore decides which eats raise the moodle, because HUNGER left above an item's hunger change keeps that item from filling the timer at all [#3598/C/inference].
A drink fills the same timer with no such gate: `DrinkFluid` sets it to `(int)(timer + abs(hungerChange) × 13000)`, the drunk fluid's hunger change, with no HUNGER test, no cooked doubling and no 11000 cap, so any drink whose hunger change adds a whole unit raises the timer, and with it the FOOD_EATEN moodle, whatever HUNGER reads [#3893/C/C-only].

The refusal at FOOD_EATEN level 3 lives in client Lua for the eat and drink actions: the inventory menus hide the eat [#0522/C/C-only] and the action queue refuses a queued one [#3599/C/C-only].
The actions' `isValidStart` is called only by the client's action queue when it starts the next queued action, an action queued into an empty queue begins without it, and no class in the jar names `isValidStart`, so a server-side `Eat`, another mod's or one a mod drives, meets no cap [#3599/C/C-only].
Vanilla's Lua reads the FOOD_EATEN moodle at six sites and each refuses at level 3 or more: the eat action's and the drink action's `isValidStart`, the drink's for any fluid, water included, the inventory pane's double-click eat and its open-and-eat, the context menu's Eat option, greyed with the cannot-eat-more tooltip, and its drink option for a fluid whose hunger change is not 0, beside the jar's one site, the open-and-eat craft [#3927/C/C-only].
That Java site is `RecipeCodeOnCreate.openAndEat`, which returns before it queues the eat when the FOOD_EATEN moodle is at level 3 or more or the recipe's eat percentage is at or below 0; on a server it would otherwise send the owning client the command that queues `ISEatFoodAction` [#3895/C/C-only].
In the worked example played live at Overfull 4, with the client reading FOOD_EATEN 3, the eat action's `isValidStart` answered false at the client and an eat the harness queued regardless landed, the stomach going from 1104 to 1134 g and the intake's eat count from 1 to 2 [#3936/M/n=1].
That build had no server-side refusal; the worked example now refuses such an eat on the server, as [eat-and-cook-hooks#side-choice](../areas/eat-and-cook-hooks.md#side-choice) records [#3989/M/n=1].
In multiplayer the client's FOOD_EATEN moodle follows the server's timer: the client's body-damage tick returns before the timer's decay, the timer reaches the client inside the body-damage main fields of the eat's push and of the 1 Hz player-stats packet, and each side recomputes its moodles from its own copy, so a server-side `setHealthFromFoodTimer` reaches the client's moodle and its eat gates with no client write [#3896/C/inference].
Vanilla has no vomiting a mod can trigger: the jar names `Vomit` only in two voice sound keys, `VoiceFemaleVomit` and `VoiceMaleVomit`, read by no other class, and the sound-script generator; the lowercase `vomit` names no class, and no Lua file under `media/lua` names it [#3928/C/C-only].

<a id="script-scale"></a>
### The script-to-instance scale

`Item.InstanceItem` divides the script's `HungerChange`, `ThirstChange` and `EnduranceChange` by 100 at instantiation, while `Calories`, `Carbohydrates`, `Lipids` and `Proteins` are stored unscaled [#0011/M/one-fixture].
`Base.Apple` carries `hungChange -0.16`, `thirstChange -0.07`, `calories 95.0` and `carbohydrates 25.13` on an instantiated item, from script values `HungerChange -16`, `ThirstChange -7`, `Calories 95.0` and `Carbohydrates 25.13` [#0012/M/one-fixture].
An item pass writes script units and an eat reads instance units, a hundredfold apart on three keys and equal on four; every other per-food and per-fluid value is in [the datasets](../reference/datasets.md).

<a id="sandbox"></a>
### The `Nutrition` sandbox option

The option gates the update tick and never the intake.

| Question | What is the case |
|---|---|
| what it gates | only `Nutrition.update()` — one early return skips the macro drain, the calorie update and the weight update, leaving the `Eat` and `DrinkFluid` store writes untouched [#0067] |
| what reads it | a whole-jar scan on 2026-09-10 returns exactly two sites, the constructor that creates the option and `Nutrition.update` [#0088/C/snapshot] |
| its default | a Java default of false, while every shipped preset sets it true [#0086] |
| what the fixture reads | `Nutrition = true` [#0087/M/one-fixture] |
| with it off | the stores keep filling to their clamps and nothing burns them, weight freezes, and the save file and the multiplayer packets still carry the values — read off the absence of any sandbox guard on the store-writing path, not measured [#0089/C/inference] |
| what it froze, measured | all three arms: with it off the three macro stores, calories and weight held at every one of 73 hourly samples over three accelerated game-days, fasting and dosed, while the fasting run with it on moved each in its first game-hour; calories held above the gain threshold for eleven game-hours with weight unmoved, so the weight arm froze on its own [#1277/M/n=1] |
| a calorie write with it off | a server-side `setCalories` still lands and still clamps at 3700, and the written value holds to the last digit between writes, so the ceiling lives in the setter; the eat itself was not driven [#2754/M/n=1] |
| a second gate above it | `Nutrition.update` is not called at all when `SystemDisabler.doCharacterStats` is false [#0068] |
| flipping it at runtime | a flip through `getSandboxOptions():set(name, value)` takes and reads back in both directions, on one client-local flip each way with no push, so what it did to the server-side drain is not established [#0090/M/n=1] |
| the Lua mirror | `SandboxVars.Nutrition` stays stale after a runtime flip of the Java option [#0091/M/n=1] |
| pushing a flip | the setter writes only the local `ConfigOption`; pushing it to the server needs `SandboxOptions.sendToServer()`, the admin panel's route [#0092] |
| what one session read of the gates | two of the update's three gates read false on both sides throughout, so neither was seen blocking; the third, the sandbox switch, has no bus reader and was not read, and the two sides' world clocks had not diverged [#1501/M/n=1] |

The drain, burn and weight model it gates are [body-and-weight#passive-burn](../facts/body-and-weight.md#passive-burn) and [nutrition-core#weight-model](../facts/nutrition-core.md#weight-model).
The option cannot stop a store from filling, which is why a mod that owns the macro model turns the tick off and runs its own.

## Walls and bounds
<a id="walls"></a>

Every measured number on this page comes from the dedicated-server path with one client, on the fixture's defaults; single player is never claimed.
The eat matrix is one fixture across five items and five states, the partial-eat arms are one item each, the direct drink probe read the server only and the timed-action drink is one can of each of two fluids in one session [#0102/M/one-fixture, #0018/M/one-fixture, #0081/M/one-fixture, #2825/M/n=1].
The nutrition mirror's gain and loss formulas and its calorie and macro ceilings match the jar and the measured clamps, so the mirror corroborates those two points and nothing else, its page being nine minors stale [#0132/M/one-fixture].

- The mirror's blanket claim that rot makes food's effects more negative is wrong: rot leaves the four nutrients, thirst and endurance untouched and degrades only hunger (divided by 2.2), stress (divided by 2), boredom and unhappiness (plus 20) and the sickness roll; rotten bread delivered its full 532 kcal and 99 g of carbohydrate [#0133/M/one-fixture].
- The mirror never quantifies burnt; it is the one real nutrition modifier, `Eat` dividing all four nutrients by 5 while thirst is divided by 5 and hunger by 3, measured on four items [#0134/M/one-fixture].
- The mirror's state-free nutritional values hold for the macros but not for hunger, scaled by 1.3 cooked, a third burnt, 1.3 stale and 2.2 rotten; its hunger column is the raw script value [#0135/M/one-fixture].
- The mirror's always-on weight simulation is wrong: the sandbox option gates the update tick — drain, burn and weight — while intake continues unguarded [#0136].
- Protein reaches one vanilla consumer on this build, the Strength experience grant ([perks-and-strength#xp-grants](perks-and-strength.md#xp-grants)); its only other reader outside the weight model is the recovery modifier ([nutrition-core#macro-effects](nutrition-core.md#macro-effects)).
- `Eat` has no skill term on the intake path; the Cooking skill raises an evolved dish's macros at build time and leaves its hunger unchanged, so the mirror's claim that cooking increases the nutrition of evolved recipes holds for the macros and not for hunger, as [cooking-and-recipes#evolved](cooking-and-recipes.md#evolved) measures [#2691/M/n=1].

The walls these mechanisms close are stated once each on the wall map.
A mod can run its intake math where `Eat` runs, which is the server ([#1128/M/n=1]).
Intercepting an eat before vanilla's numbers land needs a server-side Lua wrapper of the eat action's completion step ([#1129/M/n=1], [lua-platform#script-hooks](../platform/lua-platform.md#script-hooks)).
Correcting intake afterwards from `OnEat` is a workaround rather than a hook that runs first ([#1130/M/n=1]).
A partial or cancelled eat is handled, with the two cancel guards above as the catch ([#1132/C/C-only]); a direct `Eat` still moves the macro stores [#0006] [#0067].
The drink path is hooked through a server-side wrapper of the drink action rather than a named hook ([#1133/M/n=1]).
Turning vanilla nutrition off and owning the macro model is the sandbox option's one lever ([#1127/C/C-only], [#1136/C/C-only]).
Not covered: the food-to-health loop and the sickness rolls beyond their call sites, the fluid container's own save and sync routines, and single player; what a cooked or crafted item carries into the eat is [cooking-and-recipes#evolved](cooking-and-recipes.md#evolved).

## Open
<a id="open"></a>

- How far weight and hunger drift apart on a part-eaten custom-weight item, and whether the `f0` write is intentional — settled by eating a canned food a quarter at a time and logging its weight, `hungChange` and `baseHunger` at each step; no `X` id [#0142/C/open].
- Which items ever set `baseHunger` different from `hungChange` at spawn — a split carries a part-eaten input's unequal pair onto its output, and `RecipeCodeOnCreate.makeCoffee` and `ItemStatsPacket.applyItemStats` are unread; settled by reading those two writers and whether an `InheritFood` input can be part-eaten; no `X` id [#0143/C/open].
- What `getHealthFromFoodTimeByHunger()` returns — settled by a jar dump of the method, which scales the food-to-health loop rather than intake; no `X` id [#0146/C/open].
- Whether any vanilla item sets `DaysFresh` equal to `DaysTotallyRotten`, the shape that makes the rot-roll denominator take the hundred-per-cent branch — settled by scanning the food script for that pair; no `X` id [#0147/C/open].
- Two drink corners are unmeasured, cancel semantics and the 100 ms animation-event cadence under an accelerated clock, and the client's arrival is bounded only to a poll — settled by a drink cancelled partway and a drink at a raised time speed, each read on both sides; no `X` id [#2829/M/n=1/open].
- Decision: whether the mod's intake math runs in a server-side wrapper of the eat action's completion step or in `OnEat` — by the time `OnEat` fires, `Eat` has already written every stat and every nutrient [#0008].
- Decision: whether a rebalanced hunger value may land under the magnitude the cancel guard tests — a cancelled eat of such an item applies nothing at all ([#0112], [mp-model#ownership](../platform/mp-model.md#ownership)).
- Decision: whether the mod ships expecting the sandbox `Nutrition` option on or off — with it off the stores keep filling to their clamps and nothing burns them [#0089/C/inference].
- Decision: whether the mod's own nutrient numbers for a container are per litre or per container — a fluid's properties are per litre and the container multiplies them by its litres [#0630].
- Decision: whether the mod's drink accounting wraps the drink action's `updateEat` alone or also the world-water route, which never passes through the drink action [#2690/C/C-only].
- Whether a script `OnEat` given to the vitamin pill by a mod's item block runs on the server when the pill is taken — settled by a pill taken with one assigned, counting its calls on both sides; -> [X59](../areas/open-questions.md#x59) [#2960/C/C-only/open].

## See also

- [lua-platform#script-hooks](../platform/lua-platform.md#script-hooks) — how `OnEat` resolves and where a server-side wrapper of a timed action sits.
- [mp-model#ownership](../platform/mp-model.md#ownership) — which side owns the stores, and where a cancelled eat resolves.
- [wire-packets#eat-food-packet](../facts/wire-packets.md#eat-food-packet) — what the eat packet carries.
- [nutrition-core#clamps](../facts/nutrition-core.md#clamps) — the store clamps every intake ends against.
- [reference/experiments](../reference/experiments.md) — the named experiments the open rows point at.
