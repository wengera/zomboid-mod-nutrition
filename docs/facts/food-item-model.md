# Food item model
Verified against 42.20.4 (b0bbce05d5) · 2026-09-22 · scope: what a food item is — its state axes, the setters that write nothing, the item-level script keys, the poison fields, and how far the shipped food dataset matches the running game; aging rates, thresholds and containers are `facts/spoilage.md`, intake arithmetic is `facts/eating-pipeline.md`, and what crosses the wire is `facts/wire-packets.md`.

## Key facts

- A food item's age axis stores `age` in days as a float with `offAge` and `offAgeMax` in whole days, and derives fresh, an un-named stale band, rotten and "never ages" from those three numbers rather than storing any of them [#0201].
- The cooking axis stores `cookingTime` in game minutes of heat beside `heat`, `lastCookMinute` and the `cooked` and `burnt` flags, and `Food.update` is its only driver [#0202].
- The freezing axis stores `freezingTime` as a 0–100 percentage beside `lastFrozenUpdate` and the `frozen` flag, and takes its freezing and thawing predicates from the container [#0203].
- The three axes cross at only two points: `isFrozen()` zeroes the age rate and closes the cooking block, and `burnt` short-circuits both rot transition tests [#0204].
- `Food.setRotten(boolean)` writes a field that nothing in the jar reads, and `isRotten()` answers from `age` instead: an `age` of 4.1 against an `offAgeMax` of 4 reads rotten with no setter call [#0205/C/C-only, #0206/M/n=1].
- The routes that do move state are `setAge(offAgeMax + 1)` or `setAge(offAge)` for rot and `freeze()` or `setFreezingTime(100)` for freezing [#0210].
- A non-custom-weight food's displayed weight is derived from its remaining hunger fraction, so rewriting `HungerChange` moves the weight unless `CustomWeight = true` opts the item out [#1214/C/C-only].
- The item-level script-key reference is 114 distinct keys: 78 over the 722 `base:food` blocks and 82 over the 150 `base:drainable` blocks, 46 of them shared [#0215/C/snapshot].
- `Item.InstanceItem(String)` divides `HungerChange` and `ThirstChange` by 100 on the way onto the instance and inverts `CantBeFrozen` into a can-be-frozen setter [#0323].
- Of the four poison keys the loader recognises, only `PoisonPower` is carried by anything that ships, on four `food.txt` blocks and no drainable block [#0317/C/snapshot].
- Eating a poisoned item adds `poisonPower * f` to POISON and `poisonPower * f / 6` to PAIN, halved with Iron Gut unless the item type is `Bleach` and doubled with Weak Stomach [#0050].
- The game's own `ScriptManager` counts 722 `base:food` items, 150 `base:drainable` items and 61 fluid definitions, each equal to the shipped scan on two independent boots [#0608/M/n=2].
- Ten spot-checked items match the live game field for field: 182 fields compared, 170 matched, 12 not applicable, 0 mismatched [#0609/M/n=10].
- An absent script key takes the engine's own default, which is not always zero: an item writing neither shelf-life key reads back the never-ages sentinel on both its script object and its instance [#0619/M/n=1].
- A drink's nutrition lives on its fluid and is stated per litre: a full 0.3 L cola can reports 120 kcal against the fluid's per-litre 400 [#0604/M/n=2, #0631/M/n=1].

## How it works

This page is in five parts: the axes an item's state moves on, the setters that do not move them, the keys that seed them, the poison fields, and how far the shipped dataset agrees with the running game.
Everything here is the model one item carries in memory; what a client's copy of that model is allowed to be is [`wire-packets.md`](wire-packets.md#desyncs).

<a id="state-axes"></a>
### The three state axes

A food item is one `Food` instance, and its state moves on three axes that are stored separately and read back through derived predicates.
Nothing on the item holds a freshness or a doneness value; every such reading is computed at the moment it is asked for.
The practical consequence is that a mod reads a predicate and never a stored flag, because the predicate is a function of the numbers while the flag is not.

A food item's age axis stores `age` in days as a float with `offAge` and `offAgeMax` in whole days and `lastAged` in world hours, and derives `isFresh()` as `age < offAge`, `isRotten()` as `age >= offAgeMax`, an un-named stale band between the two and `canAge()` as `offAgeMax != 1000000000` [#0201].
The rate that moves `age`, the container multipliers that scale it and the thresholds a script writes into the two bounds are [`spoilage.md`](spoilage.md#formula); this page owns only the shape of the axis.

A food item's cooking axis stores `cookingTime` in game minutes of heat alongside `heat`, `lastCookMinute` and the `cooked` and `burnt` flags, and `Food.update` is its only driver [#0202].
The gates that decide when that driver flips a flag are [`cooking-and-recipes.md`](cooking-and-recipes.md#cook-block), and which side runs the driver and how often is [`spoilage.md`](spoilage.md#writes).

A food item's freezing axis stores `freezingTime` as a 0–100 percentage with `lastFrozenUpdate` and the `frozen` flag, is written by `Food.updateFreezing` and `freeze()`, and takes its `isFreezing()` and `isThawing()` predicates from the container together with `canBeFrozen()` [#0203].
The container is therefore part of the state: an item that cannot be frozen never accumulates a freezing percentage at all, and one sitting in a player's inventory is in neither a fridge nor a freezer.

The three state axes cross at only two points: `isFrozen()` zeroes the age rate and closes the cooking block, and `burnt` short-circuits both rot transition tests, so a burnt item never fires the container-update event for rot while its `age` still advances [#0204].
Everywhere else the three are independent, which is why a frozen, burnt, rotten item is a reachable state rather than a contradiction.
A rebalance therefore has three clocks to think about, and only the frozen and the burnt flags couple any two of them.

The cooking flags can also be written directly, and the script does not police them.
`setCooked` and `setBurnt` stick on an item whose script says `IsCookable = false`, and the state modifiers then apply in full — four matrix rows on one fixture, where uncookable bread flagged cooked gave 1.3 times its hunger relief and flagged burnt a fifth of its calories [#0062/M/one-fixture].

Weight is the fourth reading that moves with state, and it too is derived rather than stored.
`Food.getActualWeight` has two arms: with `isCustomWeight` false it returns the script weight scaled by the hunger fraction, and with `isCustomWeight` true it takes the guarded `InventoryItem` route instead [#1029].
So a non-custom-weight food's displayed weight derives from its remaining hunger fraction, and `CustomWeight = true` opts out of that derivation — read from the code rather than measured, and the consequence is that rewriting `HungerChange` is not weight-neutral [#1214/C/C-only].
The weight split is the custom-weight flag choosing an arm: the server's true flag routes the actual-weight getter through the guarded inventory-item route and returns 0, while the client's false flag recomputes script weight times the hunger fraction and returns 0.35 [#1424/M/n=1].
That is one session on one mod item, with the arms themselves read from the jar and the floats rounded to six decimals.

A second guard sits in front of the unmodded-weight getter.
`getActualWeightUnmodded()` returns 0 whenever `getDisplayName()` equals `getFullType()`, so an item with no translation entry reports weight 0 wherever its name does not resolve [#1027/M/n=1].
That zero is the display-name guard rather than a weight reading, and it was taken on one session across items written for the test.
What it costs a mod is under [Walls and bounds](#walls).
Weight is the axis a nutrition rebalance moves without meaning to, which is why it sits here rather than with the body model.

<a id="dead-setters"></a>
### The setters that write nothing

Three of this model's setters look authoritative and are not.
Each writes a field, and the field is either read by nothing or overwritten by the next tick.
They fail in three different ways, so each is worth naming on its own.
What they cost a mod is the same: a state change made the obvious way either does nothing at all, or survives only until the next tick on the side that ticks.

`Food.setRotten(boolean)` writes a field that nothing in the jar reads [#0205/C/C-only].
That reading is a whole-jar reverse-reference scan, so a reader outside the jar would not show in it; inside the jar there is none.

`setRotten(true)` does not stick on an item; the working route to a rotten item is `setAge(getOffAgeMax() + 1)` [#0063/M/n=1].
The probe behind that is a single smoke reading on one item, where the rotten predicate was still false after the call and the age route turned it true.

The reason is the derivation.
`isRotten()` derives from `age`: setting `age` to 4.1 on an item whose `offAgeMax` is 4 makes the item read rotten with no `setRotten` call [#0206/M/n=1].
That is one item on one fixture, a client-side age write against a server-spawned item.

The freeze flag has the mirror problem, for the opposite reason.
`setFrozen(true)` is undone by the next `updateFreezing` tick on a server, because `isThawing()` is true while `freezingTime` is still 0 [#0207/C/C-only].
Off a server it survives, and the reason is a call graph rather than a guard.
`updateFreezing` has exactly one caller in the jar and every ticking route into `updateAge` is server-gated, so on a multiplayer client nothing thaws the `frozen` flag except toggling a generator near a powered fridge or freezer or an explicit Lua `item:updateAge()` [#0208/C/C-only].
Both of those are code readings rather than measurements, and whether the same holds in single-player at default settings is unsettled.
The asymmetry matters to a probe as much as to a mod, because a freeze that holds on a client is not evidence that the same freeze holds on a server.

The same shape is visible in vanilla's own code, which writes the flag and the number together rather than choosing between them.
Vanilla never trusts either rot flag alone: `ItemPickerJava.rotItem` calls `setRotten(true)` and then `setAge(getOffAgeMax())` [#0209].
The pair is the pattern worth copying, and the age write is the half that does the work.

The routes that do change an item's rot and freeze state are `setAge(offAgeMax + 1)` or `setAge(offAge)` for rot and `freeze()` or `setFreezingTime(100)` for freezing [#0210].
Anything that wants a state change to survive a tick uses those and reads the predicate back rather than the flag.
A probe that sets a flag and then reads that same flag back passes on all three setters and is still wrong about the item.

<a id="script-keys"></a>
### The script keys

Every `Key = Value` line of an `item` block reaches the same loader method, whatever the item type; what that method does with a key it knows, a key it does not and a repeated block is [`loader-and-scripts.md`](../platform/loader-and-scripts.md#script-dsl).
This section owns the key list itself, and the four keys whose behaviour is not visible from the list.

`Item.InstanceItem(String)` copies the script fields onto the `Food` instance, dividing `HungerChange` and `ThirstChange` by 100 and inverting `CantBeFrozen` into a can-be-frozen setter [#0323].
The division is why a script's hunger figure and an instance's never read the same, and the inversion is why an item's script says what it cannot do while its instance says what it can.

**The item-level script-key reference.** 114 distinct keys — 78 over the 722 `base:food` blocks of `food.txt` and 82 over the 150 `base:drainable` blocks of `drainable.txt`, 46 of them shared — each row giving the key's type, its occurrence count in each file, its Java field or getter and its runtime effect, read on `42.20.4`; the occurrence counts are a dated read of the two generated script files, 2026-09-10 [#0215/C/snapshot].

| Key | Type | food | drain | Java field / getter | Runtime effect | Ev |
|---|---|---:|---:|---|---|---|
| `ActivatedItem` | bool | 0 | 17 | `Item.activatedItem` `@6608 L2551` | item can be switched on (torches) | C |
| `AlcoholPower` | float | 0 | 2 | `Item.alcoholPower` `@7763 L2639` | drunkenness per use | C |
| `AnimalFeedType` | string | 22 | 2 | `Item.animalFeedType` `@1412 L2104` | which animals will eat it | C |
| `AttachmentType` | string | 0 | 2 | `Item.attachmentType` `@9468 L2774` | hotbar/attachment slot | C |
| `BadCold` | bool | 61 | 0 | `Item.badCold` → `Food.setBadCold` (`InstanceItem @843 L1588`) | `getUnhappyChange +2` when `isBadCold && isCookable && isCooked && heat < 1.3` | C |
| `BadInMicrowave` | bool | 115 | 0 | `Item.badInMicrowave` → `Food.setBadInMicrowave` (`InstanceItem @825 L1586`) | on the cook transition in a `microwave` container: `unhappyChange = 5`, `boredomChange = 5`, `cookedInMicrowave = 1` (`Food.update @719–@752 L472–L475`) | C |
| `BoredomChange` | int | 5 | 0 | `Item.boredomChange` `@1553 L2116` | BOREDOM at eat time; +30 frozen / +20 burnt / +10 stale / +20 rotten (slice 01) | C |
| `Calories` | float | 597 | 2 | `Item.calories` → `Food.setCalories` (`InstanceItem @772 L1581`) | stored unscaled; **no state modifier at any age** — the only nutrition modifier in the game is `Eat`'s ÷5 for burnt (slice 01) | C+M |
| `CannedFood` | bool | 41 | 0 | `Item.cannedFood` — **no getter, not copied to the instance** | read only off the *script* object: `InventoryItem.getStringItemType()`, `ItemPickerJava.getLootType`, and the sealed-can spawn-rot exemption (`ItemPickerJava.rotItem @17–@28 L2247`) | C |
| `CanStoreWater` | bool | 0 | 1 | `Item.canStoreWater` `@361 L2003` | legacy water flag (B42 uses fluid components) | C |
| `cantBeConsolided` | bool | 0 | 54 | `Item.cantBeConsolided` `@9190 L2752` | blocks the "consolidate" UI action | C |
| `CantBeFrozen` | bool | 51 | 2 | `Item.cantBeFrozen` → **inverted** `Food.setCanBeFrozen(!v)` (`InstanceItem @790–@804 L1583`) | gates `isFreezing()`/`isThawing()`; an item that cannot be frozen never accumulates `freezingTime` and so never gets the ×0 age rate | C |
| `CantEat` | bool | 96 | 1 | `Item.cantEat` / `isCantEat()` | hides the Eat option; with `CannedFood` it also exempts the item from the 75 % spawn-rot roll | C |
| `Carbohydrates` | float | 597 | 2 | `Item.carbohydrates` → `Food.setCarbohydrates` | as `Calories` | C+M |
| `ChanceToSpawnDamaged` | int | 0 | 3 | `Item.chanceToSpawnDamaged` `@6311 L2529` | loot condition roll | C |
| `ColorBlue` | int | 4 | 0 | `Item.colorBlue` `@8951 L2733` | item tint; copied onto an evolved-recipe result (`EvolvedRecipe.addItem @51–@107 L274–L277`) | C |
| `ColorGreen` | int | 4 | 0 | `Item.colorGreen` `@8927 L2731` | as `ColorBlue` | C |
| `ColorRed` | int | 4 | 0 | `Item.colorRed` `@8903 L2729` | as `ColorBlue` | C |
| `ConditionLowerStandard` | float | 0 | 1 | `Item.conditionLowerNormal` `@9348 L2764` | wear rate | C |
| `ConditionMax` | int | 12 | 10 | `Item.conditionMax` `@3607 L2309` | durability ceiling | C |
| `ConsolidateOption` | string | 0 | 16 | `Item.consolidateOption` `@9516 L2778` | consolidate menu label | C |
| `CookingSound` | string | 198 | 1 | `Item.cookingSound` `@1484 L2110` → `Food.getCookingSound()` | played while `shouldPlayCookingSound()` (client only, `@0–@7 L595–L597`) | C |
| `CustomContextMenu` | string | 33 | 4 | `Item.customContextMenu` `@6983 L2579` | menu label override (`Drink` etc.) | C |
| `CustomEatSound` | string | 119 | 1 | `Item.customEatSound` `@7631 L2629` | eat SFX | C |
| `DangerousUncooked` | bool | 81 | 0 | `Item.dangerousUncooked` → `Food.setbDangerousUncooked` | 75 % poison roll (5 % with tag `EGG`) in `BodyDamage.JustAteFood @555–@676 L669–L696` (slice 01); propagates onto an evolved-recipe result and blocks a raw ingredient when the result is not cookable | C |
| `DaysFresh` | int | 497 | 0 | `Item.daysFresh` → `Food.setOffAge` (`InstanceItem @601–@604 L1562`) | the **stale** threshold in days; absent ⇒ `offAge` stays `1000000000` | C+M |
| `DaysTotallyRotten` | int | 497 | 0 | `Item.daysTotallyRotten` → `Food.setOffAgeMax` (`InstanceItem @610–@613 L1563`) | the **rotten** threshold in days; `1000000000` is the never-ages sentinel (`Food.canAge @1–@7 L2577`) | C+M |
| `DisappearOnUse` | bool | 0 | 18 | `Item.disappearOnUse` `@5791 L2487` | destroy at 0 uses | C |
| `DisplayCategory` | string | 722 | 150 | `Item.displayCategory` `@6794 L2565` | inventory grouping | C |
| `DoubleClickRecipe` | string | 4 | 12 | `Item.doubleClickRecipe` `@11065 L2928` | recipe fired by double-click | C |
| `Eattime` | int | 17 | 2 | `Item.eatTime` `@11686 L2982` | hard override of `maxTime` when `> 0` (`ISEatFoodAction.lua:247`, slice 01) | C |
| `EatType` | string | 266 | 7 | `Item.eatType` `@10470 L2884` | animation set; `popcan` forces `maxTime = 160` (slice 01) | C |
| `enduranceChange` | float | 1 | 0 | `Item.enduranceChange` `@1247 L2090` | ENDURANCE at eat time; ÷3 burnt, ÷2 stale, ×2 cooked, **no rot branch** (slice 01) | C |
| `EquipSound` | string | 0 | 1 | `Item.equipSound` `@2641 L2216` | SFX | C |
| `EvolvedRecipe` | list of `Name:use`, optionally suffixed `Cooked` after a pipe | 372 | 2 | `Item.evolvedRecipe` + `Item.itemRecipeMap` `@9916–@10247 L2820–L2865` | registers the item as an ingredient; `use` is hunger **points** (÷100 at `EvolvedRecipe.addItem @518–@545 L333`). Parse-time aliases: `RicePot`/`RicePan` → `Rice`, `PastaPot`/`PastaPan` → `Pasta`, `Roasted Vegetables` → `Stir fry` | C+M |
| `EvolvedRecipeName` | string | 172 | 1 | `Item.evolvedRecipeName` `@9131 L2747` + `Translator.setDefaultItemEvolvedRecipeName` | the name this ingredient contributes to the generated dish name | C |
| `fatigueChange` | float | 3 | 1 | `Item.fatigueChange` `@1223 L2088` | FATIGUE at eat time; a negative value also transfers to an evolved-recipe dish by `share` | C |
| `FillFromDispenserSound` | string | 0 | 1 | `Item.fillFromDispenserSound` `@7655 L2631` | SFX | C |
| `FillFromTapSound` | string | 0 | 1 | `Item.fillFromTapSound` `@7709 L2635` | SFX | C |
| `FireFuelRatio` | float | 0 | 5 | `Item.fireFuelRatio` `@11761 L2988` | burn value as fuel | C |
| `FishingLure` | bool | 41 | 0 | `Item.fishingLure` `@7115 L2589` | usable as bait | C |
| `fluReduction` | int | 2 | 0 | `Item.fluReduction` `@8783 L2719` | `bodyDamage.coldReduction += fluReduction × f` (slice 01); summed for herbal-tea ingredients | C |
| `FoodSicknessChange` | int | 8 | 4 | `Item.foodSicknessChange` `@8807 L2721` | cures FOOD_SICKNESS + POISON when negative, gated by the edible-buff timer (slice 01); capped at 12 on a herbal-tea dish | C |
| `FoodType` | string | 362 | 2 | `Item.foodType` `@415 L2007` | evolved-recipe grouping in the context menu (`ISInventoryPaneContextMenu.getEvoItemCategories`) | C |
| `GoodHot` | bool | 148 | 0 | `Item.goodHot` → `Food.setGoodHot` (`InstanceItem @834 L1587`) | `getUnhappyChange −2` when `isGoodHot && isCookable && isCooked && heat > 1.3` | C |
| `HerbalistType` | string | 18 | 0 | `Item.herbalistType` `@5659 L2477` | herbalist knowledge gating | C |
| `HungerChange` | float | 606 | 2 | `Item.hungerChange` `@1175 L2084` → `Food.hungChange` **÷ 100** (`InstanceItem @546–@595`) | the item's raw hunger relief; also seeds `baseHunger`. Never modified by age — the state ladder lives in `getHungerChange()` | C+M |
| `Icon` | string | 720 | 150 | `Item.icon` (+ `itemName`, `normalTexture`, `worldTextureName`) `@532 L2017` | textures | C |
| `IconColorMask` | string | 0 | 3 | `Item.iconColorMask` `@11113 L2932` | icon tinting mask | C |
| `IconsForTexture` | list | 2 | 0 | `Item.iconsForTexture` `@10714 L2900` | per-texture icon set | C |
| `InverseCoughProbability` | int | 6 | 1 | `Item.inverseCoughProbability` `@8831 L2723` | cold-cough suppression | C |
| `InverseCoughProbabilitySmoker` | int | 6 | 1 | `Item.inverseCoughProbabilitySmoker` `@8855 L2725` | as above, smoker trait | C |
| `IsCookable` | bool | 251 | 1 | `Item.isCookable` → `Food.setIsCookable` (`InstanceItem @619–@622 L1564`) | gates the whole cooking block (`Food.update @49–@60 L372`); **cleared to false** when a burnt item starts a fire (`@1147 L517`); an evolved dish gets it from the recipe's `Cookable` key instead | C+M |
| `IsDung` | bool | 10 | 0 | `Item.isDung` `@3114 L2265` | fertiliser | C |
| `IsWaterSource` | **dead key (not read by 42.20.4)** | 0 | 1 | — | no branch in `Item.DoParam`; the literal exists only in the *script generator* (`generation/builders/ItemBuilder.class`). Lands in `defaultModData`. Only on `item TestWaterMug` (`drainable.txt:83`) | C |
| `ItemType` | string | 722 | 150 | `Item.itemType` (`ItemType.get(ResourceLocation.of(v))`) `@307 L1999` | picks the `InventoryItem` subclass in `InstanceItem` | C |
| `KeepOnDeplete` | bool, **inverted** | 0 | 18 | `Item.disappearOnUse = !v` `@9241–@9266 L2756` | alias of `DisappearOnUse` with the sense flipped | C |
| `LightDistance` | int | 0 | 17 | `Item.lightDistance` `@6716 L2559` | torch | C |
| `LightStrength` | float | 0 | 17 | `Item.lightStrength` `@6662 L2555` | torch | C |
| `Lipids` | float | 597 | 2 | `Item.lipids` → `Food.setLipids` | as `Calories`; the wiki's "Fat" column | C+M |
| `MakeUpType` | string | 0 | 3 | `Item.makeUpType` `@9492 L2776` | cosmetics | C |
| `MechanicsItem` | bool | 0 | 3 | `Item.mechanicsItem` `@996 L2067` | loot category | C |
| `Medical` | bool | 1 | 7 | `Item.medical` `@948 L2063` | loot category | C |
| `MetalValue` | float | 0 | 30 | `Item.metalValue` `@256 L1995` | scrapping | C |
| `MinutesToBurn` | int | 246 | 0 | `Item.minutesToBurn` → `Food.setMinutesToBurn` | `cookingTime > minutesToBurn` ⇒ `burnt = true; setCooked(false)` (`Food.update @894–@913 L494–L496`) | C+M |
| `MinutesToCook` | int | 249 | 0 | `Item.minutesToCook` → `Food.setMinutesToCook` (`InstanceItem @628–@632 L1565`) | `cookingTime > minutesToCook` ⇒ cook transition (`Food.update @186–@221 L397`) | C+M |
| `OnCooked` | string | 11 | 0 | `Item.onCooked` → `Food.setOnCooked` (`InstanceItem @702–@705 L1573`) | Lua / `RecipeCodeOnCooked` hook on the cook transition (`Food.update @627–@718 L462–L467`); dotted names resolve as `table.field`. Only two values ship: `RecipeCodeOnCooked.cannedFood` (10 blocks) and `RecipeCodeOnCooked.nameCakePrep` (1) | C |
| `OnCreate` | string | 21 | 4 | `Item.luaCreate` `@11017 L2924` | Lua hook at instantiation | C |
| `OnEat` | string | 19 | 4 | `Item.onEat` → `Food.setOnEat` | Lua hook fired inside `Eat`, after nutrition and before consume (slice 01) | C |
| `OpeningRecipe` | string | 18 | 0 | `Item.openingRecipe` `@11041 L2926` | the recipe that opens a sealed can | C |
| `Packaged` | bool | 129 | 2 | `Item.packaged` → `Food.setPackaged` (`InstanceItem @781–@787 L1582`) | pure marker: `Food.isPackaged() @0 L2147` has **no Java caller and no vanilla Lua reader** | C |
| `painReduction` | int | 2 | 0 | `Item.painReduction` `@8879 L2727` | `bodyDamage.painReduction += painReduction × f` (slice 01) | C |
| `PoisonPower` | int | 4 | 0 | `Item.poisonPower` `@463–@477 L2011` → `Food.poisonPower` (`InstanceItem @531`) | POISON/PAIN at eat time (slice 01); drains **whole** into an evolved-recipe result (`EvolvedRecipe.addPoison @67–@107 L535–L539`) | C |
| `PourType` | string | 49 | 23 | `Item.pourType` `@10494 L2886` | pour animation/SFX | C |
| `primaryAnimMask` | string | 0 | 18 | `Item.primaryAnimMask` `@10302 L2870` | animation | C |
| `Proteins` | float | 597 | 2 | `Item.proteins` → `Food.setProteins` | as `Calories` | C+M |
| `RainFactor` | **dead key (not read by 42.20.4)** | 0 | 1 | — | no branch in `Item.DoParam`; recognised only by `FluidContainerScript` **inside a `component FluidContainer { … }` block**, never at item top level. Only on `item TestWaterMug` (`drainable.txt:84`) | C |
| `ReduceInfectionPower` | float | 3 | 0 | `Item.reduceInfectionPower` `@7817 L2643` | wound-infection reduction; summed for herbal-tea ingredients (`EvolvedRecipe.addItem @679–@692 L344`) | C |
| `RemoveNegativeEffectOnCooked` | bool | 5 | 0 | `Item.removeNegativeEffectOnCooked` → `Food.setRemoveNegativeEffectOnCooked` | on the cook transition zeroes `thirstChange`, `unhappyChange`, `boredomChange` **if positive** — permanent, one-shot, nutrition untouched (`Food.update @578–@626 L451–L459`) | C |
| `RemoveUnhappinessWhenCooked` | bool | 36 | 0 | `Item.removeUnhappinessWhenCooked` `@1628 L2122` | on the cook transition `setUnhappyChange(0)` (`Food.update @418–@432 L424-L425`) — read off the **script** object, not the instance | C |
| `ReplaceInPrimaryHand` | string | 0 | 6 | `Item.replaceInPrimaryHand` `@10422 L2880` | held-model swap | C |
| `ReplaceInSecondHand` | string | 0 | 6 | `Item.replaceInSecondHand` `@10398 L2878` | held-model swap | C |
| `ReplaceOnCooked` | list (`;`) | 3 | 0 | `Item.replaceOnCooked` `@6950 L2577` → `Food.setReplaceOnCooked` | on the cook transition **and only if not rotten**: each name is `AddItem`-ed with `copyConditionStatesFrom(this)`, the original is removed and `Food.update` **returns** — the item is replaced, never flagged cooked (`@224–@412 L398–L421`) | C |
| `ReplaceOnDeplete` | string | 0 | 42 | `Item.replaceOnDeplete` `@1652 L2124` | drainable → empty container | C |
| `ReplaceOnExtinguish` | string | 0 | 6 | `Item.replaceOnExtinguish` `@1673 L2126` | torch burnout | C |
| `ReplaceOnRotten` | string | 8 | 0 | `Item.replaceOnRotten` → `Food.setReplaceOnRotten` (`InstanceItem @807–@813 L1584`) | makes `updateRotting` age the item **every tick** and, once rotten, create the replacement, copy `age` + condition states and destroy the original (`Food.updateRotting @20–@226 L662–L694`) | C |
| `ReplaceOnUse` | string | 110 | 0 | `Item.replaceOnUse` `@3724 L2319` (instance `@657`) | leftover container when consumed; also the weight floor in `Eat`'s custom-weight branch (slice 01) | C |
| `RequireInHandOrInventory` | list | 6 | 1 | `Item.requireInHandOrInventory` `@4961 L2423` | use precondition | C |
| `Researchablerecipes` | list | 1 | 26 | `Item.addResearchableRecipe(…)` `@9651 L2792` | learnable-by-research recipes | C |
| `ScaleWorldIcon` | float | 0 | 1 | `Item.scaleWorldIcon` `@1044 L2071` | world sprite scale | C |
| `secondaryAnimMask` | string | 0 | 18 | `Item.secondaryAnimMask` `@10326 L2872` | animation | C |
| `SoundMap` | list → HashMap | 40 | 34 | `Item.soundMap` `@5396 L2455` | per-event sound overrides | C |
| `Spice` | bool | 109 | 2 | `Item.spice` → `Food.setSpice` (`InstanceItem @675–@678 L1570`) | takes the ingredient down the **spice branch** of `EvolvedRecipe.addItem @582–@775 L336–L359`: no hunger and no macro transfer, does not count against `MaxItems`, once per dish (`isSpiceAdded`) | C |
| `StaticModel` | string | 532 | 73 | `Item.staticModel` `@10254 L2866` | model | C |
| `StaticModelsByIndex` | list | 2 | 0 | `Item.staticModelsByIndex` `@11305 L2950` | per-index models | C |
| `StressChange` | int | 28 | 3 | `Item.stressChange` `@1578 L2118` | STRESS at eat time; ÷4 burnt, ÷1.3 stale, ÷2 rotten, ×1.3 cooked (slice 01) | C |
| `SurvivalGear` | bool | 2 | 22 | `Item.survivalGear` `@1020 L2069` | loot category | C |
| `Tags` | list (`;`) → `Set<ItemTag>` | 401 | 118 | `Item.tags` (`ItemTag.get(ResourceLocation.of(v))`) `@4243 L2362` | drives `ALREADY_COOKED`, `NO_COOKING_XP`, `DRIED_FOOD`, `HERBAL_TEA`, `BOOSTS_FLU_RECOVERY`, `ALCOHOLIC_BEVERAGE`, `GOOD_FROZEN`, `EGG` — read in `Food.update`, `EvolvedRecipe.addItem` and `JustAteFood` | C |
| `ThirstChange` | float | 112 | 0 | `Item.thirstChange` `@1199 L2086` → `Food.thirstChange` **÷ 100** | THIRST at eat time; ÷5 burnt beats ÷2 cooked and **rot does not touch it** (slice 01) | C |
| `ticksPerEquipUse` | int | 0 | 3 | `Item.ticksPerEquipUse` `@5764 L2485` | drain rate while equipped | C |
| `Tooltip` | string | 61 | 49 | `Item.tooltip` `@6770 L2563` | translated tooltip key | C |
| `TorchCone` | bool | 0 | 17 | `Item.torchCone` `@6689 L2557` | light shape | C |
| `TorchDot` | float | 0 | 6 | `Item.torchDot` `@5962 L2501` | light shape | C |
| `UnequipSound` | string | 0 | 1 | `Item.unequipSound` `@2662 L2218` | SFX | C |
| `UnhappyChange` | int | 292 | 2 | `Item.unhappyChange` `@1603 L2120` | UNHAPPINESS at eat time; +30 frozen / +20 burnt / +10 stale / +20 rotten, ±2 for `BadCold`/`GoodHot` (slice 01) | C |
| `UseDelta` | float | 2 | 146 | `Item.useDelta` `@5938 L2499` | fraction consumed per use | C |
| `UseWhileEquipped` | bool | 2 | 134 | `Item.useWhileEquipped` `@5710 L2481` | drains while held | C |
| `UseWhileUnequipped` | bool | 0 | 1 | `Item.useWhileUnequipped` `@5737 L2483` | drains in the bag | C |
| `UseWorldItem` | bool | 0 | 1 | `Item.useWorldItem` `@924 L2061` | usable from the ground | C |
| `VehicleType` | int | 0 | 3 | `Item.vehicleType` `@9276 L2758` | vehicle part | C |
| `Weight` | float | 722 | 150 | `Item.actualWeight` (and `weight`) `@1089 L2075` | encumbrance | C |
| `WeightEmpty` | float | 2 | 9 | `Item.weightEmpty` `@1151 L2082` | weight when depleted | C |
| `WorldStaticModel` | string | 718 | 150 | `Item.worldStaticModel` `@10278 L2868` | model | C |
| `WorldStaticModelsByIndex` | list | 2 | 0 | `Item.worldStaticModelsByIndex` `@11374 L2956` | per-index models | C |

The two count columns are occurrence counts in each of the two generated files, so a key with no occurrences in one of them is simply unused by that file's blocks.
The runtime-effect column is what the engine does with a value, which is the column a rebalance reads; the per-item values themselves are the dataset.
How a value is typed as it is parsed belongs to the loader rather than to any key ([#0214], [`loader-and-scripts.md`](../platform/loader-and-scripts.md#script-dsl)).

Four of those rows need stating outside the table, because what they do is an absence.
A key that parses into nowhere looks, in the table, exactly like a key that works.

`IsWaterSource` has no branch in `Item.DoParam` on `42.20.4` — the literal survives only in the script generator's `ItemBuilder` class — so it lands in `defaultModData`, and it is carried by one shipped item, `item TestWaterMug` [#0217/C/snapshot].

`RainFactor` has no branch in `Item.DoParam` and is recognised only by `FluidContainerScript` inside a `component FluidContainer` block, never at item top level, so at item level it lands in `defaultModData`, and it is carried by the same one shipped item [#0218/C/snapshot].
Both land there by the loader's default arm, which writes an unrecognised key into the item's default modData rather than dropping it or throwing ([#0212], [`loader-and-scripts.md`](../platform/loader-and-scripts.md#default-moddata)).
That arm is also the route a mod nutrient can ride into a vanilla block.

`Eattime` is the script-parser spelling of the eat-duration key, it has no Java consumer, and its only use is the Lua duration override [#0100/C/snapshot].
The spelling is the trap: the getter is camel-cased and the key is not.
What the eat action does with the value is [`eating-pipeline.md`](eating-pipeline.md#eat-type).

A mod restating one of these keys does not replace the item's block.
The restatement merges per key with the last body winning ([#1006/M/n=1], [`loader-and-scripts.md`](../platform/loader-and-scripts.md#per-key-merge)), and the bodies replay sorted by stored script path rather than by load order ([#1055/M/n=2], [`loader-and-scripts.md`](../platform/loader-and-scripts.md#sorted-replay)).
Per-item values for every key in the table are the dataset rather than this page: [`datasets.md`](../reference/datasets.md).

<a id="poison"></a>
### The poison fields

Four loader keys carry poison and only one of them is set by anything that ships, so three of the four are a mod-facing surface rather than a mechanic.
Which of these fields the item packet carries to a client is [`wire-packets.md`](wire-packets.md#item-stats-packet).

`PoisonPower` parses into the instance's poison power, is set by four `food.txt` blocks and no drainable block, and is read by the eat-time body-damage path, by the evolved summation and by `ItemStatsPacket` [#0317/C/snapshot].
It is the only one of the four that a shipped item actually sets.

`Poison` parses into an instance field but `Food.isPoison()` has no Java and no vanilla-Lua caller — it is exposed to Kahlua only — and no shipped item sets the key [#0318/C/C-only].

`PoisonDetectionLevel` parses into an instance field, is set by no shipped item, and is read by the character's known-poison check, the used-item properties, the poison copy helper, `ItemStatsPacket.setData`, the poison transfer and the forage icon [#0319].

`UseForPoison` parses into an instance field, is set by no shipped item, and its getter has no Java and no vanilla-Lua caller although the value is serialised under bit 131072 in the item's save and load [#0320/C/C-only].
The reader scans behind those three are the jar plus the vanilla Lua tree, so a reader outside both would not show in them, and the source gives no bytecode offset for the use-for-poison getter.
`PoisonDetectionLevel` therefore has live readers but no shipped setter, while `Poison` and `UseForPoison` have neither, so a mod writing those two is writing for itself.

Poisoning a dish accumulates `poisonDetectionLevel` with a cap of 10, transfers `poisonPower` whole and zeroes the source item, writes the chef's name into the dish's modData under an added-poison-by key, and writes the event to the user log [#0321].
The transfer being whole rather than shared is what makes one poisoned ingredient enough.

The sandbox option `EnablePoisoning` gates only the user-interface path: a value of 2 disables poisoning entirely and 3 disables it for bleach [#0322].
The gate is in the context menu, so a dish poisoned by any route that does not go through that menu is not gated at all.

What a poison number does at eat time is four independent branches inside `BodyDamage.JustAteFood`, applied or rolled in turn.

- `JustAteFood` adds `poisonPower * f` to POISON and `poisonPower * f / 6` to PAIN, halving the poison with Iron Gut unless the item type is `Bleach` and doubling it with Weak Stomach [#0050].
- A tainted item adds `20.0 * f` to POISON and `10.0 * f / 6` to PAIN [#0051].
- The rot sickness roll fires at `clamp(age - offAgeMax, 1, 5) / (offAgeMax - offAge) * 100` per cent, or at 100 per cent when `offAgeMax <= offAge`, halved by Iron Gut, doubled by Weak Stomach and skipped when the character is already infected; a hit adds `5 * abs(hungChange * 10) * f` to POISON and a miss adds `2 * abs(hungChange * 10) * f` [#0052].
- A dangerous uncooked item zeroes `healthFromFoodTimer` and rolls at 75 per cent, or 5 per cent with the `EGG` tag, halved by Iron Gut and zero for eggs with it, doubled by Weak Stomach; on a hit, when the character is not infected and the item is not burnt, it adds `15.0 * f` to POISON [#0053].

The first two are unconditional additions and the last two are rolls, so a rebalance that moves an item's hunger figure moves the rot roll's payload with it.
Nothing in this section is measured: all four keys, the dish transfer and the four eat-time branches are code readings on this build.

<a id="dataset-fidelity"></a>
### How far the dataset matches the running game

The shipped food dataset is a read of the generated script files, and its columns are [`datasets.md`](../reference/datasets.md).
What this section owns is the measured distance between that read and the running game: a census, ten field-for-field spot checks, three absent-against-zero read-backs, the fluid join and a three-drink probe.
The five check types are unlike one another — a count, a field-for-field comparison, a read-back of absence, a join and a behavioural probe — so that one class of scanner error cannot pass all of them.
What they license is reading the dataset instead of booting the game for any question about what an item *is*, because a mod reading these columns is reading the same load-time definition both sides start from ([#0646/C/inference], [`loader-and-scripts.md`](../platform/loader-and-scripts.md#per-side-load)).
What they do not license is reading it for what an instance currently is: an instance's state is the axes above, and the dataset carries only the script's seed values.

The game's own `ScriptManager` counted 722 `base:food` items, 150 `base:drainable` items and 61 fluid definitions, each equal to the scan, on two independent boots [#0608/M/n=2].
The live fluid id set is exactly equal to the 61 `fluid` script blocks in both directions [#0615/M/n=2].
Both counts rest on two boots of the default fixture, the second of which left no committed artifact and is reproduced inside the first.
The fluid-container bucket has no live census route at all and is therefore scanner-only.

Ten spot-checked items matched the live game field for field: 182 fields compared, 170 matched, 12 not applicable, 0 mismatched, and no substitution was needed [#0609/M/n=10].
The twelve not-applicable readings are a finding about drinks rather than a gap.
A fluid container's live instance answers the four `InventoryItem` ageing and cooking getters — 1000000000 / 1000000000 / 60 / 120 — and none of the six `Food` nutrition getters, so a drink's nutrition is reachable only through its fluid [#0604/M/n=2].
That is the two drinks of the ten, on one boot of the default fixture, read server-side.

Absence in the dataset is load-bearing, and the live read-backs confirm it in both directions.
`Base.CannedCorn` writes neither `DaysFresh` nor `DaysTotallyRotten`, and both its script object and its instance read back the 1000000000 sentinel, so an absent key's engine default is not always 0 [#0619/M/n=1].
`Base.RatKing` writes `DaysFresh = DaysTotallyRotten = 0` and its instance reads back `offAge 0 / offAgeMax 0`, so it spawns already rotten [#0620/M/n=1].
`Base.BreadSlices` writes `MinutesToCook 4` and no `MinutesToBurn` and reads back 4 / 120, so the unwritten half of a block takes its own default independently [#0621/M/n=1].
Each of the three is one item on one boot of the default fixture, read server-side — enough to show that a zero and an absence are different values, not enough to enumerate every key's default.

The join that puts a fluid's numbers on a container row was checked against the game rather than assumed.
The fluid join was checked live on all six nutrition fields against the game's own `fluid.script` reading of Cola and JuiceGrape [#0624/M/n=2].
Two fluids on one boot; that run's own transform labels are not citable, while its numbers and its match verdicts are.

A fluid's numbers are per litre and the container multiplies them, which is the one place a dataset reader can be off by the size of the container.
A full `Base.Pop2` container reported `calories 120.000008`, not Cola's per-litre 400 [#0631/M/n=1].
Drinking a whole 0.3 L Cola can (`Base.Pop2`, f = 1.0) wrote +120.000031 kcal and +31.200001 g carbohydrates and moved HUNGER −0.036 and THIRST −0.090, leaving the can empty [#0634/M/n=1].
Drinking half a 0.3 L Cola can (f = 0.5) wrote +60.0 kcal and +15.6 g carbohydrates and moved HUNGER −0.018 and THIRST −0.045, leaving 0.15 L, so `f` is a share of the current contents and not of the capacity [#0635/M/n=1].
Drinking a whole 0.2 L JuiceBox (`Base.JuiceBox`, JuiceGrape, f = 1.0) wrote +80.0 kcal and +23.999996 g carbohydrates and moved HUNGER −0.020 and THIRST −0.060, leaving it empty [#0636/M/n=1].
`healthFromFoodTimer` gained the truncated float32 sum `(int)(|hungerChange| × 13000)` on each drink — 468, 234 and 260 [#0637/M/n=3].
All of the drink readings are one drink each on one boot of the default fixture, taken server-side with both snapshots inside a single Lua call, so no world time passes between them.
A reader that ignores the unit is wrong by the size of the container rather than by a rounding, which is why the basis is a column of the dataset rather than a footnote to it.
Every measured reading in this section was taken on the server side of a live session, so each is the authoritative copy rather than a client's.

## Walls and bounds
<a id="walls"></a>

The item model's bounds are mostly the shape of the scans behind it, and its one mirror correction is about state rather than about values.

The mirror says the nutritional-values rows are state-free; the code agrees for the macros, which are bare field reads with no cooked, burnt, rotten or frozen modifier, but its hunger column is the raw script value divided by 100 at instantiation and so an identity column rather than an arithmetic one, and its fat column is the script and Java lipids [#0369/M/n=1].

A mod item's display name equals its full type on both sides before and after cooking while a vanilla control resolves its name on both sides and keeps 0.3 everywhere, so this dedicated server resolves vanilla item names perfectly well and the failure is not server-wide [#1426/M/n=2].
Two items on one session, differing in more than one way at once, so the reading supports exactly "not dedicated-server-wide" and "this item's name does not resolve".

A mod cannot ship a food absent from the translation table and have its weight arrive: the unmodded-weight guard returns zero and the item packet fills the wire's weight field from that getter [#1166/C/C-only].

A mod can run the per-key merge across every `base:food` item only with a workaround, and the derived weight moves with any rewritten hunger value [#1181/M/n=1].

A mod can put a custom key inside a vanilla `item` block, because the loader's default arm writes an unrecognised key into the item's default modData [#1125/C/C-only].

The dead-setter and one-caller readings are whole-jar reverse-reference scans over the jar and the vanilla Lua tree, so a reader living outside both — another mod, or a call from a UI script — would not appear in any of them.

Every measured reading on this page comes from the default fixture on a single build, and the repeated ones repeat within one run or across two boots rather than across fixtures or worlds.

The contradiction above is the only mirror row this page corrects; the mirror's aging, fridge and freezer claims are [`spoilage.md`](spoilage.md#walls).

Not covered: the item model was read for food, drainables and fluid containers only — the other item types that share the same loader, the fluid-container census inside the running game, the spawn-fill draw a part-filled container takes, and any item-name table other than the shipped English one were never read.

## Open
<a id="open"></a>

- `Food.rottenTime` has a getter, a setter and save and load support, no script key, one writer in the compost update and zero readers, and `Poison` and `UseForPoison` parse into fields with no Java or vanilla-Lua reader, so all three look like mod-facing API rather than mechanics — settled by a reader scan that reaches outside the jar and the vanilla Lua tree, which no scan behind this page does [#0379/C/C-only/open].
- An item absent from the vanilla item-name table reading its display name as its full type and its unmodded weight as 0 on client and server identically, inside vanilla, is unverified: its only measured reading rests on a restricted artifact key, on one absent-name item beside one control in one session; re-measure by reading the display name and the unmodded weight of an absent-name vanilla food beside a named control on both sides, in a run whose key carries no restriction [#1427/M/n=1/unverified].
- Whether 42.20.4 ever loads a B41-layout item-name translation file stays open by design, because separating it from the no-entry case needs an item-name JSON added to a mod tree, which is a write under the read-only workshop folder — settled by repeating the pair inside a writable copy of that tree [#1429/C/C-only/open].
- The design must decide whether a rebalanced food sets `CustomWeight = true`: a non-custom-weight food's displayed weight derives from its remaining hunger fraction, so every rewritten hunger value moves a weight as well [#1214/C/C-only].
- The design must decide whether every mod-added food ships a translation entry: an untranslated item's unmodded weight reads zero and that zero is what the wire carries [#1027/M/n=1, #1166/C/C-only].
- The design must decide whether a mod nutrient rides an unrecognised key inside the vanilla `item` block or lives in a store of its own: the loader's default arm accepts the key and puts it in the item's default modData rather than rejecting the block ([#0212], [#1125/C/C-only]).

## See also

- [`spoilage.md`](spoilage.md#formula) — the aging formula, the rot thresholds and the container multipliers that move the age axis.
- [`cooking-and-recipes.md`](cooking-and-recipes.md#cook-block) — the cook block that drives the cooking axis, and the evolved summation that reads the poison power.
- [`eating-pipeline.md`](eating-pipeline.md#modifiers) — what the eat path does with these keys and these state flags.
- [`wire-packets.md`](wire-packets.md#item-stats-packet) — which of these fields the item packet carries and which it omits.
- [`loader-and-scripts.md`](../platform/loader-and-scripts.md#per-key-merge) — the loader that parses every key here, the per-key merge and the sorted replay.
- [`mod-anatomy.md`](../platform/mod-anatomy.md#translations) — where a mod's item-name table has to live for a new food's name, and therefore its weight, to resolve.
- [`datasets.md`](../reference/datasets.md) — the per-item and per-fluid columns, and every value this page does not restate.
