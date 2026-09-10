# Food item model & lifecycle — script keys, aging, cooking, evolved recipes

**Verified against: 42.20.4 (`b0bbce05d5`)** · 2026-09-10 · slice 02 (P1c).
Evidence grades: **C** read from bytecode/Lua/scripts, **M** measured on the live
dedicated server, **W** wiki mirror (secondary). Every **M** row names its run inline; **C+M**
means a code reading confirmed by that same run, and slice 02 has exactly one —
`exp02-20260910-030433`
([`lifecycle.json`](../../testing/artifacts/exp02-20260910-030433/lifecycle.json)).
Intake arithmetic is **not** repeated here — how these values reach `Stats` and
`Nutrition` is [eating-pipeline.md](eating-pipeline.md).

## Summary

1. A food item is one `zombie/inventory/types/Food` instance with three independent state axes —
   an age clock (`age` against `offAge`/`offAgeMax`), a cooking accumulator (`cookingTime` against
   `minutesToCook`/`minutesToBurn`) and a freezing percentage (`freezingTime` 0–100) — all seeded
   from script keys parsed by a single loader method, `Item.DoParam`, which is shared by every item
   type in the game.
2. Aging is one line — `age += ΔgameHours × FoodRotSpeed / 24` — multiplied by **0** while frozen
   and by `FridgeFactor` (default `0.2`) inside a *powered* fridge or freezer. Rot is a **view, not
   a mutation**: aging writes only `age`, `lastAged`, `heat`, `freezingTime`, `lastFrozenUpdate` and
   `fertilized`, so the four macros read identical at every age (measured at four) and only the
   read-time getters degrade.
3. Cooking needs no appliance *object*: `Food.update` is the whole driver, accumulating
   `heat / 1.5` (×`0.05` when the container itself is cool) per game minute and flipping `cooked`
   past `minutesToCook` and `burnt` past `minutesToBurn`, with burning clearing `cooked` —
   reproduced on a live server with the item sitting in a player's inventory.
4. Evolved recipes are the only place in the game where a skill touches nutrition:
   `dish.macro += ingredient.macro × (1 + cookLvl/15) × share`. Measured, the same dish hunger buys
   **1.1667×** the macros at Cooking 10 that it does at Cooking 0 — and because the ingredient loses
   only its `share`, ~17 % of a level-10 dish's calories are created from nothing.
5. In multiplayer the server owns the entire lifecycle: a client never runs `updateAge` or
   `updateRotting`, and `age`, `offAge`, `offAgeMax` and `freezingTime` are not in `ItemStatsPacket`.
   Measured: a server-side `age` never reached the client — not on `sendItemStats`, not on
   `updateAge(true)`, not across a full accelerated game day — while `calories`, `burnt`,
   `cookingTime` and `heat` did.

---

## Model

### The three state axes

| Axis | Stored on the instance | Derived predicate | Set by | Ev |
|---|---|---|---|---|
| Age | `age` (days, float), `offAge`, `offAgeMax` (days, int), `lastAged` (world hours) | `isFresh() = age < offAge`; **stale** = `offAge ≤ age < offAgeMax` (un-named in code); `isRotten() = age >= offAgeMax`; `canAge() = offAgeMax != 1000000000` | `setAutoAge()` at loot spawn, then `Food.updateAge` | C |
| Cooking | `cookingTime` (game minutes of heat), `heat`, `lastCookMinute`, flags `cooked` / `burnt` | `cookingTime > minutesToCook` ⇒ cooked; `> minutesToBurn` ⇒ burnt | `Food.update` (the only driver) | C |
| Freezing | `freezingTime` (0–100 %), `lastFrozenUpdate`, flag `frozen` | `isFreezing()` / `isThawing()` from container + `canBeFrozen()` | `Food.updateFreezing`, `freeze()` | C |

The three are almost independent: freezing gates aging (×0) and gates the cooking block
(`isCookable && !isFrozen()`), and burning suppresses the fresh/rotten transition events — but
nothing else crosses over. Ev C (`Food.updateAge(Z) @140–@151 L754-755`,
`Food.update @49–@71 L372-L373`, `@294–@331 L771-772`).

> **Two setters that do not work.** `Food.setRotten(boolean) @0–@5 L1846-L1847` writes a field
> **nothing in the jar reads** — `isRotten()` reads `age`. And `setFrozen(true)` is undone by the
> next `updateFreezing` tick, because `isThawing()` is true while `freezingTime` is still 0. Vanilla
> itself never trusts either alone: `ItemPickerJava.rotItem @59–@70 L2253-L2254` calls
> `setRotten(true)` *and then* `setAge(getOffAgeMax())`. The working routes are
> `setAge(offAgeMax + 1)` / `setAge(offAge)` and `freeze()` / `setFreezingTime(100)` (Ev C;
> confirmed by slice 01's "`setRotten(true)` did not stick" and by phase (a) of run
> `exp02-20260910-030433`, where `rotten` went true purely from `setAge(4.1)`).

### Key reference — all 114 script keys

One method parses every `Key = Value` line of an `item` block for **all** item types:
`zombie/scripting/objects/Item.DoParam(String,String) @0 L1969 … @11920 L3008` — an if/else chain
of 440 `equalsIgnoreCase` comparisons over 396 distinct keys. **An unknown key is not dropped and
does not throw**: the fall-through at `@11805 L2992` writes it into the item's `defaultModData` as a
`Double` if the value parses and a `String` otherwise (`@11832–@11894 L2993–L3003`), so a "dead" key
silently becomes mod data readable from Lua. A malformed *value* on a known key does throw
(`InvalidParameterException(key, item.name)`, `@11898–@11919 L3005–L3006`). Ev C.

The table below is the union of the two generated files — **78 keys** over 722
`ItemType = base:food` blocks (`media/scripts/generated/items/food.txt`, 15 525 lines) and **82**
over 150 `base:drainable` blocks (`drainable.txt`, 2 420 lines): **114 distinct, 46 shared**.
`food` / `drain` are occurrence counts in each file. Bytecode offsets are in `Item.DoParam` unless
another method is named. Rows marked **C+M** are measured in § Aging, § Cooking or § Evolved
recipes below, all from run `exp02-20260910-030433`
([`lifecycle.json`](../../testing/artifacts/exp02-20260910-030433/lifecycle.json)).

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

**Dead keys: 2 of 114** — `IsWaterSource` (`drainable.txt:83`) and `RainFactor` (`:84`), both only on
`item TestWaterMug`, both silently becoming `defaultModData`. Two more of the 114 are parsed but
effectively unread on the item instance: `Packaged` (copied over, then read by nothing) and
`CannedFood` (never copied; read only off the script object) — see § Packaging. Two further keys the
loader recognises, `Poison` and `UseForPoison`, have no reader at all *and* appear in neither file —
see § Poison. Ev C.

Value types as parsed: `Integer.parseInt` (int), `Float.parseFloat` (float),
`Boolean.parseBoolean` **or** `equalsIgnoreCase("true")` (bool — only the literal `true` is true),
`trim().split(";")` (list), bare `putfield` (string). Ev C.

### Aging

```java
// zombie/inventory/types/Food.updateAge(boolean sync)   @0–@510  L736–L783
float nowH = GameTime.getInstance().getWorldAgeHours();          // @0   L736
ItemContainer c = getOutermostContainer();                       // @8   L738
updateFreezing(c, nowH);                                         // @13  L739
lastAged = GameTime.checkHours(lastAged, nowH);                  // @19  L741   (last<0 ? now : min(last,now))
if (nowH <= lastAged) return;                                    // @35  L742
double dH = nowH - lastAged;                                     // @44  L743

// heat tracks the container: lerp over a 1/3-hour window, else snap
if (c != null && heat != c.getTemprature()) { … }                // @53–@139 L744–L751

// ---- rate modifiers ----
if (isFrozen())                        dH *= 0.0;                // @140 L754-755   FROZEN STOPS AGING
else if (isInFridge(c) || isInFreezer(c)) {                      // @156 L756
    if (c.getSourceGrid() != null && c.getSourceGrid().haveElectricity())
        dH *= getFridgeFactor();                                 // @172 L757/L760
    else if (elecShutModifier > -1 && lastAged < elecShutModifier*24) {
        float cut = Math.min(elecShutModifier*24, nowH);         // @230 L762
        dH = (cut - lastAged) * getFridgeFactor();               // @246 L763
        if (nowH > elecShutModifier*24) dH += nowH - elecShutModifier*24;   // @261 L765-766
    }
}

boolean wasFresh  = !burnt && offAge    < 1e9 && age <  offAge;  // @294 L771
boolean wasRotten = !burnt && offAgeMax < 1e9 && age >= offAgeMax;// @331 L772

age      += (dH * getFoodRotSpeed()) / 24.0;                     // @368 L774   <-- THE FORMULA
lastAged  = nowH;                                                // @391 L775

if (!GameServer.server && (fresh or rotten flipped))
    LuaEventManager.triggerEvent("OnContainerUpdate", this);     // @470 L779-780
if (sync && GameServer.server) GameServer.sendItemStats(this);   // @497 L782-783
```

`burnt` short-circuits both transition tests, so a burnt item never fires `OnContainerUpdate` for
rot — but its `age` still advances. Ev C.

**Every constant on the aging path.**

| Constant | Value | Source | Ev |
|---|---|---|---|
| never-ages sentinel | `1000000000` (default `offAge` / `offAgeMax`) | `Food.canAge @4 L2577`, `updateRotting @5 L654` | C |
| age unit conversion | `age += hours × rotSpeed / 24` | `Food.updateAge(Z) @368 L774` | C+M |
| frozen multiplier | **× 0.0** | `Food.updateAge(Z) @147–@151 L755` | C+M |
| fridge/freezer multiplier (powered) | `getFridgeFactor()` | `Food.updateAge(Z) @189–@197 L760` | C |
| `getFridgeFactor()` | sandbox `FridgeFactor`, enum 1–6, **default 3**: 1→`0.4`, 2→`0.3`, **3→`0.2`**, 4→`0.1`, 5→`0.03`, 6→`0.0` | `Food.getFridgeFactor @9 tableswitch L710–L716`; `SandboxOptions.<init> @1113 L134` | C |
| `getFoodRotSpeed()` | sandbox `FoodRotSpeed`, enum 1–5, **default 3**: 1→`1.7`, 2→`1.4`, **3→`1.0`**, 4→`0.7`, 5→`0.4` | `Food.getFoodRotSpeed @9 tableswitch L721–L726`; `SandboxOptions.<init> @1094 L133` | C |
| electricity-shutoff window | `elecShutModifier × 24` hours; the whole unpowered-fridge grace branch needs `elecShutModifier > -1`. Four presets ship `14`, `SixMonthsLater.lua:13` ships `-1` (grace disabled) | `Food.updateAge(Z) @202–@292 L761–L766` | C |
| heat lerp window | `1/3` hour (20 game-minutes) | `Food.updateAge(Z) @71 L745` | C |
| freeze time | `freezingTime += ΔH / 4 × 100` ⇒ **4 game-hours** to 100 % | `Food.updateFreezing @50 L853` | C |
| thaw time | `freezingTime -= ΔH / t × 100`, `t = 1.5` h, `× 2` in a powered fridge, `÷ 6` when the container is above 1.0 | `Food.updateFreezing @75–@122 L856–L865` | C |
| `frozen` flip points | only at the boundaries: `>= 100` ⇒ `setFrozen(true)`, `<= 0` ⇒ `setFrozen(false)` | `Food.setFreezingTime @0–@33 L2160–L2166` | C+M |
| sync rate limit | `UpdateLimit(1000)` ms, and only on the no-arg `updateAge()` | `Food.<clinit> @4 L72` | C |
| rotten-food removal | sandbox `DaysForRottenFoodRemoval`, default **−1** (disabled); **every shipped preset sets −1** | `SandboxOptions.<init> @1570–@1580 L168`; `media/lua/shared/Sandbox/{Apocalypse,Extinction,Outbreak,Rising}.lua:96`, `SixMonthsLater.lua:71` | C |

All five shipped presets use `FoodRotSpeed = 3` (`Apocalypse`, `Extinction`, `Outbreak`, `Rising`
`:65`, `SixMonthsLater:40`) and `FridgeFactor = 3` except `Outbreak.lua:66` (`FridgeFactor = 4` →
`0.1`, i.e. 10× rather than 5×). So at defaults **a powered fridge ages food at 0.2× and a freezer,
once the item is actually frozen, at 0.0×** — stopped, not divided. Ev C.

**Fridge vs freezer, and where `heat` comes from.** `isInFridge(c)` / `isInFreezer(c)` are thin
wrappers over `ItemContainer.isFridge()` / `isFreezer()` (`Food @0–@16 L2719/L2723`).
`isFreezer() @0–@55 L4057–L4061` tests `type == ContainerType.FREEZER.toString()` or the literal
`"freezer"`; `isFridge() @0–@101 L4065–L4081` **returns false if `isFreezer()`** first, then tests
`"fridge"`, else the parent `IsoObject` property `IsoPropertyType.IS_FRIDGE`. A player inventory is
neither. `ItemContainer.getTemprature() @0–@225 L2681–L2707` is the only source of `Food.heat`:

| Container condition | `getTemprature()` | Ev |
|---|---|---|
| `customTemperature != 0` | that value (short-circuits everything below) | C |
| powered fridge or freezer | `0.2` | C |
| powered stove, or `type == "microwave"` with an `IsoStove` parent | `IsoStove.getCurrentTemperature()` = `(currentTemperature + 100) / 100` | C |
| `IsoBarbecue` / `IsoFireplace` parent | that object's `getTemperature()` | C |
| unpowered fridge/freezer, inside the elec-shutoff window, time-of-day < 13:00 | `Lerp(0.2, 1, (timeOfDay − 7) / 6)` | C |
| everything else | `1.0` (ambient) | C |

**Spawn-time age.** `Food.setAutoAge()` is called from exactly one place —
`ItemPickerJava.doRollItemInternal` (loot generation) — and pre-ages an item by the world age plus
`(timeSinceApo − 1) × 30` days, discounting the time it "spent" in a fridge (`× getFridgeFactor()`)
or a freezer (counted as 0, with `freezingTime` set from the leftover), then multiplies by
`getFoodRotSpeed()` (`@0–@263 L790–L838`). Separately, `ItemPickerJava.rotItem @0–@124
L2246–L2263` gives 75 % of spawned perishables `setAge(getOffAgeMax())` and 95 % of the remainder
`setAge(getOffAge())` — with a **sealed can exemption** (`script.cannedFood && script.cantEat`,
`@17–@28`). Ev C.

**Removal and replacement.** `Food.updateRotting(ItemContainer)` returns immediately when
`offAgeMax == 1e9` (`@0–@12 L654-655`) **and on any MP client** (`@13–@19 L658-659`). With
`ReplaceOnRotten` set it calls `updateAge()` every tick and, once rotten, creates the replacement,
copies `age` and the condition states, and destroys the original (`@20–@226 L662–L694`). Otherwise
it only acts when `DaysForRottenFoodRemoval >= 0` — destroying the item past
`offAgeMax + daysForRottenFoodRemoval` — which no shipped preset enables. Ev C.

**Measured — the getters as a function of age.** `Base.Steak` (`DaysFresh 2`,
`DaysTotallyRotten 4`, `HungerChange -40`, 220 kcal / 0 carbs / 9.35 lipids / 31.62 proteins),
client-side `setAge` on a server-spawned item; nothing is aging here, this isolates the getters.

| `age` | `isFresh` | `isRotten` | `getHungChange` (stored) | `getHungerChange` (read-time) | kcal | carbs | lipids | proteins | Ev |
|---:|---|---|---:|---:|---:|---:|---:|---:|---|
| 0 | true | false | −0.4 | −0.4 | 220 | 0 | 9.35 | 31.62 | **M** `exp02-20260910-030433` |
| 1.9 | true | false | −0.4 | −0.4 | 220 | 0 | 9.35 | 31.62 | **M** `exp02-20260910-030433` |
| 2.1 | **false** | false | −0.4 | **−0.307692** (= 0.4/1.3) | 220 | 0 | 9.35 | 31.62 | **M** `exp02-20260910-030433` |
| 4.1 | false | **true** | −0.4 | **−0.181818** (= 0.4/2.2) | 220 | 0 | 9.35 | 31.62 | **M** `exp02-20260910-030433` |

The stale band is real and un-named — at `age 2.1` both `isFresh` and `isRotten` are false. The four
macros are **identical at every age**, confirmed at the getter level rather than inferred from an
`Eat` delta; the full state-modifier ladder is in [eating-pipeline.md](eating-pipeline.md).

**Measured — the rate and the frozen multiplier.**

| Quantity | Measured | Code prediction | Ev |
|---|---:|---:|---|
| Δ`age` over one accelerated game day (`settimespeed 30`, 24.56 game-h, `FoodRotSpeed 3`) — **server** | **1.00777** | 1.02320 (`ΔH_containing/24`, 1.5 % short — see Open questions) | **M** `exp02-20260910-030433` |
| Δ`age` over the same day — **client** | **0** | 0 (a client never runs `updateAge`) | **M** `exp02-20260910-030433` |
| Δ`age` for one forced `updateAge(true)` tick | 0.000388 | — (the server *is* aging) | **M** `exp02-20260910-030433` |
| Δ`age` while frozen, over 1.172 game-h | **0.000000** | **0.0** (`dH *= 0.0`) | **M** `exp02-20260910-030433` |
| `frozen` at `freezingTime = 44.6` | still **true** | true — the flag only flips at 0 and 100 | **M** `exp02-20260910-030433` |
| thaw rate out of a player inventory | 47.25 %/game-h (this run) | 66.7 %/game-h (`t = 1.5` h) — **do not quote**, see Open questions | **M** `exp02-20260910-030433` |

Sandbox as measured: `FoodRotSpeed 3`, `FridgeFactor 3`, `DaysForRottenFoodRemoval −1`,
`ElecShutModifier 14`. Fridge and freezer *container* multipliers were **not** measured — they need
a placed, powered appliance (see Open questions); the ×0 frozen rate, which needs none, was measured
instead.

**What aging writes.** Across `updateAge`, `updateFreezing` and `updateRotting` the only item fields
written are `age`, `lastAged`, `heat`, `freezingTime` (plus `frozen` via its setter),
`lastFrozenUpdate` and `fertilized` → false. **Aging never touches `hungChange`, `thirstChange`,
`calories`, `carbohydrates`, `proteins`, `lipids`, `unhappyChange`, `boredomChange` or
`stressChange`** — every rot effect is computed at read time by the `Food` getters (Ev C, confirmed
by the table above, M). *Consequence for the nutrition mod:* a food item's stored macros are a pure
function of its script values and how much of it has been eaten. A mod that wants rot to cost
calories has to change `Eat` or the getters, not the item.

### Cooking

There is **no separate oven or campfire class**: `zombie/inventory/types/Food.update()` is the
driver and the appliance only supplies `ItemContainer.getTemprature()`.

```java
void Food.update() {                                                     // L359
    calculateTimeMultiplier();                                           // @0  L359
    if (hasTag(ALREADY_COOKED)) setCooked(true);                         // @4  L361-362
    updateTemperature(); checkEggHatch(null);                            // @19 L364-365
    ItemContainer c = getOutermostContainer();                           // @29 L367
    if (c != null) {
        if (GameServer.server) updateAge(false);                         // @38 L369-370
        if (isCookable && !isFrozen()) {
            if (heat <= 1.6f) goto ROT;                                  // @63 L373   HEAT GATE
            int minute = GameTime.getInstance().getMinutes();
            if (minute != lastCookMinute) {                              // @86 L377   ONE TICK / GAME MINUTE
                lastCookMinute = minute;
                float d = heat / 1.5f;                                   // @109 L382
                if (c.getTemprature() <= 1.6f) d *= 0.05f;               // @118 L384-385  residual heat
                cookingTime += d;                                        // @135 L387
                if (isTainted && cookingTime > min(minutesToCook, 10f)) isTainted = false;  // @156 L393-394
                if (!isCooked() && !burnt
                    && (cookingTime > minutesToCook || cookingTime > minutesToBurn)) {      // @186 L397
                    if (getReplaceOnCooked() != null && !isRotten()) { …replace…; return; } // @224 L398–421
                    setCooked(true);                                     // @413 L423
                    …removeUnhappinessWhenCooked, rice/pasta clock reset,
                      RemoveNegativeEffectOnCooked, OnCooked hook, microwave penalty…
                    if (chef != null && !hasTag(NO_COOKING_XP) && !isRotten()) award 10 Cooking XP;
                }
                if (cookingTime > minutesToBurn) { burnt = true; setCooked(false); }        // @894 L494–496
                …kitchen-fire roll…
            }
        } else if (isTainted && heat > 1.6f && !isFrozen()) { …boil tainted water… }        // @1155 L523
    }
ROT: updateRotting(c);                                                   // @1255 L543
}
```

| Key / accessor / constant | Behaviour | Ev |
|---|---|---|
| `IsCookable` → `isCookable()Z @0 L2553` | gates the whole block: `isCookable && !isFrozen() && heat > 1.6f` (`@49–@71 L372-373`); set **false** at `@1147 L517` when a burnt item ignites | C |
| cooking heat gate | item `heat > 1.6f`; the *container* must also exceed 1.6 for the full rate | C+M |
| tick granularity | one per distinct `GameTime.getMinutes()` — one game minute (`@86 L377`) | C |
| cook rate | `cookingTime += heat / 1.5f` per game minute (`@109 L382`) | C+M |
| residual-heat factor | `× 0.05f` when `container.getTemprature() <= 1.6` (hot item, cool container) (`@130 L385`) | C+M |
| `MinutesToCook` → `getMinutesToCook()F @0 L2569` | `cookingTime > minutesToCook` ⇒ `setCooked(true)` (`@186–@221 L397`) | C+M |
| `MinutesToBurn` → `getMinutesToBurn()F @0 L2577` | `cookingTime > minutesToBurn` ⇒ `burnt = true; setCooked(false)` (`@894–@913 L494–496`) | C+M |
| `setCooked(true)` / `setBurnt(true)` | **ungated and sticky** — each also raises `cookingTime` to its threshold if below (`@5–@28 L2590-2591` / `L2601-2602`), which is why slice 01 could cook an `IsCookable = false` item | C |
| `ReplaceOnCooked` | on the transition and only if `!isRotten()`: `AddItem` each name, `copyConditionStatesFrom(this)`, remove the original, **return** — the item is never flagged cooked | C |
| `RemoveNegativeEffectOnCooked` | zeroes `thirstChange`/`unhappyChange`/`boredomChange` **if positive**, once, permanently (`@578–@626 L451–459`) | C |
| rice/pasta clock reset | for 10 named types (`RicePot`, `PastaPot`, `RicePan`, `PastaPan`, `WaterPot*`, `WaterSaucepan*`, `RiceBowl`, `PastaBowl`) the cook transition writes `age = 0, offAge = 1, offAgeMax = 2` (`@563–@575 L444–446`) | C |
| `BadInMicrowave` + `c.isMicrowave()` | `unhappyChange = 5`, `boredomChange = 5`, `cookedInMicrowave = 1` (`@719–@752 L472–475`) | C |
| taint purge | cookable: `cookingTime > min(minutesToCook, 10)`; non-cookable containers: `+1.0`/min (`× 0.2` residual) past `10.0` | C |
| cooking XP | `10.0f` Cooking on the cook transition, skipped for tag `NO_COOKING_XP` or a rotten item (`@755–@891 L478–487`) | C |
| kitchen fire | `burnt && cookingTime >= 50 && cookingTime >= minutesToCook×2 + minutesToBurn/2`, then `Rand.Next(AdjustForFramerate(200)) == 0` per minute, on a powered non-campfire grid; strength `500000`, and `isCookable` is cleared (`@926–@1147 L503–517`) | C |
| `GoodHot` / `BadCold` | read only by `getUnhappyChange @124–@195 L1645–1649`: `−2` if `isGoodHot && isCookable && isCooked && heat > 1.3`; `+2` if `isBadCold && … && heat < 1.3` | C |
| `getHeat()` / `getInvHeat()` | raw `Food.heat` (**1.0 = ambient**, `0.2` powered fridge, `(stoveTemp+100)/100` on a stove); the UI remap is `heat > 1 ? (heat−1)/2 : 1 − (heat−0.2)/0.8` | C |
| stove ramp | `IsoStove.getCurrentTemperature() = (currentTemperature + 100)/100`, so `heat > 1.6` needs `currentTemperature > 60`; a microwave jumps straight to `maxTemperature` | C |

**Measured — both transitions with no appliance at all.** `Base.Steak`
(`MinutesToCook 50`, `MinutesToBurn 70`) in a player's inventory, primed server-side with
`heat 2.0` + `lastCookMinute -1` + a `cookingTime` just past the threshold, then one `item:update()`:

| Step | `cookingTime` | `cooked` | `burnt` | `heat` | Ev |
|---|---:|---|---|---:|---|
| primed to `minutesToCook + 1` | 51 | false | false | 2.0 | **M** `exp02-20260910-030433` |
| after `item:update()` | 51.059658 | **true** | false | 1.78979 | **M** `exp02-20260910-030433` |
| primed to `minutesToBurn + 1` | 71 | true | false | 2.0 | **M** `exp02-20260910-030433` |
| after `item:update()` | 71.061172 | **false** | **true** | 1.83512 | **M** `exp02-20260910-030433` |

The per-minute rate is confirmed to five decimal places **including** the residual-heat factor: the
cook tick added `+0.059658` against `heat/1.5 × 0.05 = 0.059660` at `heat 1.78979`, and the burn
tick `+0.061172` against `0.061171` at `1.83512` — the `× 0.05` applies because the container (a
player inventory) sits at temperature 1.0. Burning **clears** `cooked`. Nutrition is untouched by
cooking: 220 kcal before and after, raw `hungChange` still −0.4 while `getHungerChange` reads
−0.133333 (the burnt `max(|h|/3, 0.01)` branch). Ev M, `exp02-20260910-030433`.

`heat` cannot be pinned: `Food.update` runs `updateTemperature` and `updateAge` before the cooking
block, both of which pull `heat` toward the container temperature (2.0 → 1.79 within one call), so a
longer cooking experiment needs a real appliance. Ev M, same run.

### Evolved recipes

`media/scripts/generated/evolvedrecipes.txt` holds **62 `evolvedrecipe` blocks**; an item joins one
through its own `EvolvedRecipe = <Name>:<use>[|Cooked]` key. `Item.OnScriptsLoaded @0–@234
L3029–L3047` attaches the item to the recipe whose **name** matches *and* to **every recipe whose
`Template` equals that key** — that is how `Salad:10` on a carrot reaches `Salad`, `SaladClay`, ….
An unmatched key throws `InvalidParameterException`. Recipe keys: `BaseItem`, `Name`, `ResultItem`,
`Cookable` (44), `MaxItems`, `AddIngredientIfCooked` (37), `AddIngredientSound` (11),
`CanAddSpicesEmpty` (42), `Template`, `MinimumWater` (20), plus `IsHidden` and `AllowFrozenItem`
which are loader-only (**0 uses**). Ev C.

**The summation** — `EvolvedRecipe.addItem(base, ingredient, chef) @0–@1928 L265–L487`. Phase A
turns the base into the `ResultItem` with **zeroed macros**, then re-seeds them from the base food
itself (a pot of water contributes its own values) and carries the age across *proportionally*
(`newAge = newOffAgeMax × oldAge/oldOffAgeMax`, only when both have real thresholds). Phase B merges
one ingredient:

```java
float hunger           = itemRecipe.use / 100.0f;                        // @518 L333
if (ingredient.isRotten())   hunger = 0.05 or 0.10 × |baseHunger|;       // @800–@915 L366–369  (Cooking 7-8 / 9-10)
if (|ing.getHungerChange()| < hunger) hunger = |DECIMAL_FORMAT(ing.getHungerChange())|;  // @934 L374–376
float hungerAfterSkill = hunger - (3f * cookLvl / 100f) * hunger;        // @1142 L401   −3 %/level
float share            = min(|hungerAfterSkill / ing.getHungChange()|, 1f);              // @1159 L402–404
float skillBonus       = 1f + cookLvl / 15f;                             // @1217 L411   +6.67 %/level

dish.calories      += ing.getCalories()      * skillBonus * share;       // @1228 L412
dish.proteins      += ing.getProteins()      * skillBonus * share;       // @1250 L413
dish.carbohydrates += ing.getCarbohydrates() * skillBonus * share;       // @1272 L414
dish.lipids        += ing.getLipids()        * skillBonus * share;       // @1294 L415
float thirst = ing.getThirstChangeUnmodified() * skillBonus * share;     // @1316 L416  (skipped for tag DRIED_FOOD)

dish.hungChange -= hunger;  dish.baseHunger -= hunger;                   // @990/@1003 L380-381
if (ing.isCooked()) hungerAfterSkill /= 1.3;                             // @1353 L420-421
ing.hungChange  += hungerAfterSkill;   ing.baseHunger += hungerAfterSkill;// @1371 L424-425
ing.calories    -= ing.calories * share;  … same for the other three …   // @1429–@1486 L428–431
```

| Term | Value | Note | Ev |
|---|---|---|---|
| `hunger` | `use / 100` | the script `Name:use` points, in hunger units | C+M |
| rotten ingredient | `0.05 × baseHunger` at Cooking 7–8, `0.10 ×` at 9–10; **refused below Cooking 7** | rounding `DECIMAL_FORMAT`, `HALF_EVEN` | C |
| `hungerAfterSkill` | `hunger × (1 − 0.03 × cookLvl)` | ⇒ 70 % of the ingredient consumed at Cooking 10 | C+M |
| `share` | `min(abs(hungerAfterSkill / ing.hungChange), 1)` | capped at the whole ingredient | C+M |
| `skillBonus` | `1 + cookLvl / 15` | 1.0 at level 0, 1.6667 at level 10 | C+M |
| macros per unit of **dish hunger** | `skillBonus × (1 − 0.03 × cookLvl)` while `share < 1` | **1.0** at level 0, **1.1667** at level 10 — and 1.168 at level **9**, so level 10 is fractionally *worse* than level 9 | C+M |
| dish gain ÷ ingredient loss | `skillBonus` = up to **1.6667** | the dish gains `macro × skillBonus × share`, the ingredient loses only `macro × share` | C+M |
| spice branch | no hunger, no macros, does not count against `MaxItems`, once per dish (`isSpiceAdded`) | herbal-tea ingredients additionally sum `foodSicknessChange` (cap 12), `painReduction`, `fluReduction`, `stressChange`, `reduceInfectionPower` | C |
| unhappiness | `unhappyChange = unmodified − (5 − dupes×5)`, clamped at `+25` | plus an over-stuffing term once `extraItems.size() − 2 > cookLvl`; `boredomChange` is zeroed once in phase A and **never touched again** | C |
| ingredient gating | `use == -1` unusable · burnt never usable · rotten needs Cooking ≥ 7 · frozen refused unless `AllowFrozenItem` (never set in vanilla) | `DangerousUncooked` + uncooked + non-cookable result rejected · non-spice usable only while `extraItems.size() < MaxItems` · `MinimumWater` needs the base's fluid container ≥ that ratio of water | C |

**Measured — Salad, two cooking levels.** `Base.Bowl` + `Base.Lettuce` (`Salad:5`, 54 kcal,
`hungChange −0.15`) + `Base.Tomato` (`Salad:6`, 14 kcal, `hungChange −0.12`), via
`recipe:addItem(base, ingredient, chef)` — the exact Lua→Java bridge `ISAddItemInRecipe.lua:70`
uses, which runs headlessly with no UI. Fresh ingredients per round; the perk level pinned on the
**server** (a client-only write is not authoritative — see § MP behaviour).

| | Cooking 0 | Cooking 10 | Predicted | Ev |
|---|---:|---:|---|---|
| `skillBonus` | 1.0 | 1.6667 | `1 + lvl/15` | **M** `exp02-20260910-030433` |
| lettuce `share` | 0.33333 | 0.23333 | ×0.70 at level 10 | **M** `exp02-20260910-030433` |
| tomato `share` | 0.5 | 0.35 | ×0.70 at level 10 | **M** `exp02-20260910-030433` |
| **dish kcal** | **24.999998** | **29.166666** | 25.0 / 29.1667 | **M** `exp02-20260910-030433` |
| dish carbs | 5.193333 | 6.058888 | 5.1933 / 6.0589 | **M** `exp02-20260910-030433` |
| dish lipids | 0.28 | 0.326667 | 0.28 / 0.3267 | **M** `exp02-20260910-030433` |
| dish proteins | 2.283333 | 2.663889 | 2.2833 / 2.6639 | **M** `exp02-20260910-030433` |
| dish `hungChange` | **−0.11** | **−0.11** | `−(0.05 + 0.06)` — identical | **M** `exp02-20260910-030433` |
| dish `thirstChange` | −0.063333 | −0.073889 | scaled by `skillBonus × share` | **M** `exp02-20260910-030433` |
| lettuce left / tomato left (kcal) | 36.0 / 7.0 | 41.400002 / 9.1 | ingredient loses `macro × share` | **M** `exp02-20260910-030433` |
| ingredient consumed? | no | no | `share < 1` both times | **M** `exp02-20260910-030433` |

Every predicted cell matches to six decimal places. Two consequences the mod has to decide about:

- **Cooking skill does not make a bigger meal — it makes a richer one.** The dish's hunger is −0.11
  at both levels; only its macros move, by `skillBonus × (1 − 0.03·lvl)` = **1.1667×** at Cooking 10.
- **Cooking skill creates calories out of nothing.** 68 kcal of ingredients produced 68.0 kcal of
  outputs at level 0 (exactly conservative: 25.0 dish + 36.0 + 7.0) and **79.667** at level 10
  (29.167 + 41.4 + 9.1) — **+17.2 %**, because the dish gains `macro × skillBonus × share` while the
  ingredient loses only `macro × share`. Ev M, `exp02-20260910-030433`.

> **Correction to an earlier reading.** `docs/superpowers/plans/02-notes.md` Q5 concluded "a
> level-10 cook moves 1.667× the macros per unit of hunger a level-0 cook does". That is wrong as
> written: 1.6667 is the **dish-gain / ingredient-loss** ratio (the creation factor); the macros per
> unit of *dish hunger* go up by **1.1667×**, because `skillBonus` is cancelled by the
> `(1 − 0.03·lvl)` shrink inside `share`. The notes' reasoning ("the ingredient survives longer") is
> right; the number attached to it was not. Ev M, `exp02-20260910-030433`.

### Packaging, cans and `ReplaceOnUse`

| Mechanism | What it actually does | Ev |
|---|---|---|
| `Packaged` (129 `food.txt` lines — **127 `true`**, 2 `false` — plus 2 in `drainable.txt`) | copied to the instance, readable as `Food.isPackaged()Z @0 L2147` — and **nothing reads it**: no Java caller in the jar, no vanilla Lua reader. A pure marker for scripts and mods | C |
| `CannedFood` (41 blocks) | never copied to the instance and has no getter; read only through `item.getScriptItem()` — `InventoryItem.getStringItemType() @38–@47 L3984-3985` returns `"CannedFood"`, `ItemPickerJava.getLootType` maps it to the `CannedFoodLootNew` sandbox modifier, and `rotItem @17–@28 L2247` exempts `cannedFood && cantEat` from the 75 % spawn-rot roll | C |
| **sealed cans** — the `CannedFood = true` **and** `CantEat = true` pair: **21 items** (14 `Canned*` — `CannedBolognese`, `CannedCorn`, `CannedPeaches`, … — plus `TinnedBeans`, `TinnedSoup`, `TunaTin`, `MysteryCan`, `DentedCan`, `Dogfood`, `WaterRationCan`), all 21 also `Packaged = true`, 17 with an `OpeningRecipe` | **not one of them declares `DaysFresh`**, so `offAge`/`offAgeMax` stay at `1000000000`, `canAge()` is false and `updateRotting` returns at `@12 L655`: they never rot and are never removed | C |
| **the other 20 `CannedFood` items** — the openable/opened variants (`CannedBologneseOpen` at `food.txt:3644`, `OpenBeans`, `CannedMilk`, …) | 19 of the 20 declare thresholds — `DaysFresh`/`DaysTotallyRotten` of 2/4 (11 items), 5/7 (5), 3/5 (2), 4/7 (1) — plus `HungerChange`, `EvolvedRecipe`, `ReplaceOnUse = Base.TinCanEmpty` and `IsCookable`. **Opening a can is what starts its clock.** The exception is `CannedMilk`, which declares neither threshold and so never ages either | C |
| home canning — `OnCooked = RecipeCodeOnCooked.cannedFood` (**10** food blocks) | `ratio = age/offAgeMax; setOffAgeMax(1560); setOffAge(730); setAge(offAgeMax × ratio)` (`L11–L15`) — ~2 years to stale, ~4.3 years to rotten, preserving the fraction consumed | C |
| `ReplaceOnUse` (110 blocks) | the leftover container: `Eat`'s custom-weight branch uses the replacement's weight as the floor (slice 01), and the context menu / `ISDumpContentsAction` build it (`ISInventoryPaneContextMenu.lua:4079`, `:4093-4094`; `ISDumpContentsAction.lua:70-71`) | C |

Of the 127 food blocks that set `Packaged = true`, 52 carry `DaysFresh` and 75 do not — so the flag
says nothing about whether an item rots. **For "sealed" semantics a mod should key off
`getOffAgeMax() == 1000000000`** (or the `CannedFood` + `CantEat` pair), never off `isPackaged()`.
More broadly, **225 of the 722 `base:food` blocks declare no `DaysFresh` at all** and therefore never
age. Ev C.

*(The five counts in this subsection were re-counted directly from
`media/scripts/generated/items/food.txt` on 42.20.4 and correct
`docs/superpowers/plans/02-notes.md` Q6, which gives 129 `Packaged = true` blocks, 22 sealed cans and
89 `RecipeCodeOnCooked.cannedFood` blocks — the file has 127, 21 and 10. Its 19 opened variants is
right, once stated as "19 of the 20 non-sealed `CannedFood` items".)*

### Poison

Four loader keys, all recognised by `Item.DoParam`; only one is used by any shipped item.

| Key | Parse → field | food / drain occurrences | Reader status | Ev |
|---|---|---|---|---|
| `PoisonPower` | int → `Food.poisonPower` (`@463–@477 L2011`, instance `@531`) | **4** / 0 | `BodyDamage.JustAteFood` (POISON/PAIN at eat time, slice 01), `EvolvedRecipe.addItem @1866 L475`, `ItemStatsPacket` | C |
| `Poison` | bool → `Food.poison` (`@388–@405`, instance `@501–@504`) | **0** / 0 | `Food.isPoison()Z @0 L1909` has **no Java and no vanilla-Lua caller** — exposed to Kahlua only | C |
| `PoisonDetectionLevel` | int → `Food.poisonDetectionLevel` (`@439–@453`, instance `@510`) | **0** / 0 | `IsoGameCharacter.isKnownPoison`, `UsedItemProperties.addInventoryItem`, `Food.copyPoisonFrom`, `ItemStatsPacket.setData`, `EvolvedRecipe.addPoison`, `ISForageIcon.lua:25` | C |
| `UseForPoison` | int → `Food.useForPoison` (`@487–@501`) | **0** / 0 | **no reader at all** — serialised in `Food.save` (bit `131072`) / `Food.load` and nothing else | C |

Poisoning a dish (`EvolvedRecipe.addPoison @0–… L526–…`): `poisonDetectionLevel` accumulates and is
**capped at 10**, `poisonPower` transfers **whole** and zeroes the source, the chef's name is written
to the dish's modData under `addedPoisonBy`, and the event is written to the `user` log. Sandbox
`EnablePoisoning` gates the **UI path only** — `== 2` disables poisoning entirely, `== 3` disables it
for `Base.Bleach` (`ISInventoryPaneContextMenu.lua:4270`, `:4288`). Ev C.

---

## Code map

| Class / method | Role | Ev |
|---|---|---|
| `zombie/scripting/objects/Item.DoParam(String,String)` | the single script-key parser for every item type; unknown keys → `defaultModData` | C |
| `zombie/scripting/objects/Item.InstanceItem(String)` | copies script fields onto the `Food` instance (`HungerChange`/`ThirstChange` ÷100, `CantBeFrozen` inverted) | C |
| `zombie/scripting/objects/Item.OnScriptsLoaded(ScriptLoadMode)` | binds each item's `EvolvedRecipe` key to the recipe and to every `Template` match | C |
| `zombie/inventory/types/Food.update()` | the tick: temperature, server-side aging, the whole cooking block, then `updateRotting` | C+M |
| `Food.updateAge(boolean)` | the age formula and its rate modifiers; the `sync` flag drives `GameServer.sendItemStats` | C+M |
| `Food.updateFreezing(ItemContainer,float)` | `freezingTime` in and out; `setFreezingTime` is what flips `frozen` | C+M |
| `Food.updateRotting(ItemContainer)` | `ReplaceOnRotten` replacement and `DaysForRottenFoodRemoval` deletion; **returns on any client** | C |
| `Food.setAutoAge()` | spawn-time pre-aging (world age + `timeSinceApo`, fridge/freezer discount) | C |
| `Food.isFresh()` / `isRotten()` / `canAge()` / `getHungerChange()` | the read-time state ladder — the only place rot has any effect | C+M |
| `zombie/inventory/ItemContainer.isFridge()` / `isFreezer()` / `getTemprature()` | container classification and the single source of `Food.heat` | C |
| `zombie/scripting/objects/EvolvedRecipe.addItem/addPoison/checkItemCanBeUse/getItemsCanBeUse` | the dish summation, poison transfer and ingredient gating | C+M |
| `zombie/scripting/objects/RecipeCodeOnCooked.cannedFood` | home canning: rewrites `offAge`/`offAgeMax` to 730/1560 days | C |
| `zombie/inventory/ItemPickerJava.doRollItemInternal` / `rotItem` | loot-time aging and the 75 % spawn-rot roll with its sealed-can exemption | C |
| `zombie/iso/IsoCell.ProcessItems`, `IsoGameCharacter.recursiveItemUpdater` | what actually calls `InventoryItem.update()` — world/container items and every non-zombie character's inventory, per tick, with no side guard | C |
| `zombie/network/packets/ItemStatsPacket` (`setData` / `applyItemStats`) | the 38-field item stats packet — see § MP behaviour for what is *not* in it | C+M |
| `media/lua/shared/TimedActions/ISAddItemInRecipe.lua:70` | `recipe:addItem(base, used, character)` — the only Lua→Java bridge into the summation | C+M |
| `media/lua/client/ISUI/ISInventoryPaneContextMenu.lua:332`, `:4238–4297`, `:2372–2390` | the evolved-recipe menu: probe, submenu build, and the action queue | C |

---

## MP behaviour

**Owning side: the server, for the entire lifecycle.** `Food.update` gates its `updateAge` call on
`GameServer.server` (`@38–@46 L369-370`), `Food.updateRotting` returns immediately on
`GameClient.client` (`@13–@19 L658-659`), and the container hooks `OnAddedToContainer` /
`OnBeforeRemoveFromContainer` are server-gated too. `GameServer.server` is written in only two
places (`GameServer.main`, `GameWindow.mainThreadInit @345 L654` when the `server` launch arg is
`"true"`), so it is true only in a dedicated/host server process. Both `sendItemStats` calls inside
the cooking block are likewise `if (GameServer.server)`. There is no client→server item-field push
at all ([`../testing/spikes.md`](../testing/spikes.md) §S6). Ev C.

**Age travels only in the full item serialization.** `Food.save`/`load` write `age`, `lastAged`,
`offAge`, `offAgeMax`, `freezingTime`, `lastFrozenUpdate`, `rottenTime` and `compostTime` under a
bit-flag scheme, and the MP carriers of that blob are `GameClient.receiveSendItemListNet`,
`receiveInvMngGetItem`, `GameServer.receiveInvMngUpdateItem`, `IsoWorldInventoryObject.load`,
`EquipPacket`, `TradingUIAddItemPacket` and `CompressIdenticalItems.load` — i.e. whenever the item is
(re)transmitted whole, never when its stats change. A reverse-reference scan for callers of
`setAge` returns **no packet class at all**. Ev C.

**Per field.** `ItemStatsPacket` carries 38 fields; the ones that matter here, graded by what was
actually put to the test — a field only carries information when the two sides were first made to
*differ* on it:

| Field | Owning side | In `ItemStatsPacket`? | Evidence | Ev |
|---|---|---|---|---|
| `age` | server (only the server runs `updateAge`) | **no** | server 3.250943 → client **0** after an explicit `sendItemStats`; server 3.251331 → client **0** after `updateAge(true)` (the syncing form); server +1.00777 → client **0** over a full accelerated game day; server 3.5 → client **0** in the ownership phase | **M** `exp02-20260910-030433` |
| `calories` | server | **yes** | `item.set … calories 999` server-side → client read back **999** | **M** `exp02-20260910-030433` |
| `burnt` | server | **yes** | client received `false → true` after the burn transition | **M** `exp02-20260910-030433` |
| `cookingTime` | server | **yes** | client received `0 → 71.061172` | **M** `exp02-20260910-030433` |
| `heat` | server | **yes** | client received `1 → 1.83512` | **M** `exp02-20260910-030433` |
| `cooked` | server | yes (in the field list) | **not measured** — both sides read `false`, and a match is uninformative | C |
| `offAge`, `offAgeMax`, `freezingTime`, `lastAged` | server | **no** (absent from the field list) | code reading of `ItemStatsPacket.setData` / `applyItemStats` only; no run has made them differ | C |
| `frozen` | server | yes (the boolean is in the list; the 0–100 `freezingTime` behind it is not) | code reading only | C |
| `hungChange`, `baseHunger`, `carbohydrates`, `proteins`, `lipids`, `thirstChange` | server | yes | code reading only — never made to differ in any run | C |
| `minutesToCook`, `minutesToBurn`, `poisonPower`, `poisonDetectionLevel`, `extraItems`, `spices`, `condition`, `uses` | server | yes | code reading only | C |
| `rotten` (the field) | — | no | irrelevant: nothing reads it on either side (`isRotten()` derives from `age`) | C |
| Cooking **perk level** (drives the evolved-recipe summation) | server | n/a (character sync, not `ItemStatsPacket`) | a server-side `setPerkLevelDebug` went `0 → 10` and the *very next* bus command — a client read — already reported `10`, with no sleep between; the teardown repeated it downward (`10 → 0`). The client-side call was a no-op both times | **M** `exp02-20260910-030433` |

**Effect of a client-side change.** A client-side `setAge` moves only the client's copy and is never
pushed (no client→server item path); the server's value is unaffected and the client's is not
corrected either, because nothing re-sends `age` until the item is serialised whole. A client-side
perk write is worse: it reads back correct locally and is then **overwritten** by the server's copy,
so an evolved recipe built "at Cooking 10" can silently run at level 0. Pin skills and item state on
the **server** bus. Ev C+M (`exp02-20260910-030433`; the perk overwrite itself was seen in this
session series' uncommitted shakedown run, so it is stated here as the reason the server-side
command exists, not as a measured row).

**Practical consequences for a mod.**

1. **A client's displayed freshness can be arbitrarily stale.** It is whatever the last full
   serialization said. When the server crosses a rot threshold it calls
   `GameServer.sendItemStats(this)` (`updateAge(Z) @497 L782-783`) — but only when the `sync` flag is
   set, i.e. only from the no-arg `updateAge()`, and that packet does not carry the new age anyway.
   `Food.update`'s own aging call passes `sync = false`. Ev C.
2. **`OnContainerUpdate` never fires on a dedicated server** (`if (!GameServer.server)`,
   `@470 L779-780`) and never on a client (which does not run `updateAge`) — so a mod cannot hang
   rot-transition logic on that event in MP. Ev C.
3. **Aging must be read on the server.** Any `item.age`-style client probe measures the client's
   stale copy, which is the finding, not the number. Ev M, `exp02-20260910-030433`.
4. **The measured evolved-recipe arithmetic is not an MP storage claim.** `addItem`'s
   `Remove(old)` / `AddItem(result)` ran client-side in the harness (its
   `sendReplaceItemInContainer` branch is `GameServer.server`-gated), so the server still held the
   Bowl and the untouched ingredients. The summation is pure Java arithmetic that both sides run
   identically; what an MP server stores after a real `ISAddItemInRecipe` was not measured.
   Ev M (caveat), `exp02-20260910-030433`.

---

## Discrepancies vs the wiki

| # | Wiki claim (mirror, page version) | Code / measurement | Ev |
|---|---|---|---|
| 1 | "when a food item is placed in a the freezer compartment, the spoil rate is reduced by **25 times**" ([fridge.md](../../references/wiki-mirrors/fridge.md), **41.78.19**) | No `25` appears anywhere on the aging path. A freezer applies the *same* `getFridgeFactor()` as a fridge while the item is unfrozen; once `freezingTime` reaches 100 the rate is **×0.0** — stopped, not divided. Measured: Δ`age` = 0.000000 over 1.17 game-h while frozen | W vs C+M `exp02-20260910-030433` |
| 2 | "the spoil rate is reduced by **5 times**" in a fridge ([fridge.md](../../references/wiki-mirrors/fridge.md), 41.78.19; repeated as "increases spoil time by 5 times" in [food.md](../../references/wiki-mirrors/food.md), **42.20.0**) | True only as the *default*: `FridgeFactor` is a 1–6 sandbox enum (`0.4 / 0.3 / 0.2 / 0.1 / 0.03 / 0.0`) whose default 3 is the 5×, and it applies only when `getSourceGrid().haveElectricity()`. The `Outbreak` preset ships `4` (0.1 = 10×), and unpowered food reverts to full rate once the `ElecShutModifier` window closes | W vs C |
| 3 | "freezing it will completely stop decay when the food is fully frozen" ([food.md](../../references/wiki-mirrors/food.md), 42.20.0) | **Correct**, and exact: `dH *= 0.0`, measured Δ`age` = 0.000000. The page's "as long as it will not thaw in between" is also right — thawing is continuous (`freezingTime` decays) and `frozen` only flips at the 0/100 boundaries | W confirmed by C+M `exp02-20260910-030433` |
| 4 | "As food begins to rot, its effects will become more negative" — reads as blanket ([food.md](../../references/wiki-mirrors/food.md), 42.20.0) | Rot leaves **all four macros untouched**: 220 kcal / 0 / 9.35 / 31.62 identical at ages 0, 1.9, 2.1 and 4.1. Only `getHungerChange` (÷2.2), stress (÷2), boredom/unhappiness (+20) and the sickness roll degrade; thirst and endurance have no rot branch at all | W vs C+M `exp02-20260910-030433` |
| 5 | "every ingredient adds −5 boredom **and** unhappiness the first time; three of the same negates the bonus, more than three adds a penalty" ([evolved-recipes.md](../../references/wiki-mirrors/evolved-recipes.md), **41.78.19**) | Two errors against `EvolvedRecipe.addItem`: `boredomChange` is zeroed once in phase A and never touched again — only `unhappyChange` moves, as `−(5 − dupes×5)` clamped at `+25` plus an over-stuffing term — and the off-by-one: the bonus already stops on the **second** identical copy and the penalty starts on the third | W vs C |
| 6 | The recipe roster, ~35 rows, no `Template` mechanism ([evolved-recipes.md](../../references/wiki-mirrors/evolved-recipes.md), 41.78.19) | 42.20.4 loads **62** `evolvedrecipe` blocks, and an item's `EvolvedRecipe = Name:use` attaches both to the matching recipe **and** to every recipe whose `Template` equals that key. Verify any roster entry or hunger figure against `EvolvedRecipe.Load` / `Item.OnScriptsLoaded`, not that table | W vs C |
| 7 | Per-level table: ingredient consumed falls 100 % → 70 % while nutrition added per ingredient rises 100 % → **117 %**, "level 10 lands slightly below level 9" ([cooking.md](../../references/wiki-mirrors/cooking.md), **42.18.0**) | **The wiki is right and our own first code reading was wrong.** Consumption is `1 − 0.03·lvl` = 0.70 at level 10 (measured: lettuce `share` 0.33333 → 0.23333, exactly ×0.70) and macros per unit of dish hunger are `skillBonus × (1 − 0.03·lvl)` = **1.16667** at level 10 against **1.168** at level 9 — the page's "slightly below" is real, and holds while `share < 1`. (Our own digest on [evolved-recipes.md](../../references/wiki-mirrors/evolved-recipes.md) repeats the `1.67×` reading and needs the same correction) | W confirmed by C+M `exp02-20260910-030433` |
| 8 | "An evolved recipe inherits the age of its base ingredient only" ([cooking.md](../../references/wiki-mirrors/cooking.md), 42.18.0) | Nearly right, but **proportional**, not inherited: phase A sets `newAge = newOffAgeMax × (oldAge / oldOffAgeMax)` and only when *both* items have real thresholds (neither at the `1000000000` sentinel); ingredients contribute no age at all | W vs C |
| 9 | The Fridges table as a refrigeration roster ([appliances.md](../../references/wiki-mirrors/appliances.md), **42.8.0**) | Groups tiles by *category*, not by container type, and carries no spoilage, power or temperature figure whatsoever. `ItemContainer.isFridge()` returns **false** for anything that is already a freezer, so Generic Cooled Shelves and White Display Counter are the likeliest false positives. The page's own banner says tiles were removed during B42 unstable | W vs C |
| 10 | Nutritional-values rows are state-free ([nutritional-values.md](../../references/wiki-mirrors/nutritional-values.md), **42.20.0**) | Correct for the macros — bare `getfield` reads, no cooked/burnt/rotten/frozen modifier, measured identical at four ages — but its hunger column is the raw script value (÷100 at instantiation) and so an identity column, not an arithmetic one; its "Fat" column is the script/Java `Lipids` | W vs C+M `exp02-20260910-030433` |

No mirror exists for a dedicated spoilage page: **"Food spoilage" 404s** (2026-09-10), and
**"Refrigerator" and "Freezer" both redirect** to `Appliances#Refrigerators` (whose section is
actually headed `== Fridges ==` as of 42.8.0) — see
[`references/wiki-mirrors/README.md`](../../references/wiki-mirrors/README.md).

---

## Open questions

1. **Phase (c) is 1.5 % short of the age formula.** Measured Δ`age` = **1.00777** against
   **1.02320** predicted over the containing window (server world-age 2.400196 → 26.956989 =
   24.556793 game-h) at `FoodRotSpeed 3`. The item's aging window strictly *contains* the wait
   loop's clock samples, so it had **more** time than the samples saw — the wrong sign for the
   obvious explanations. `GameTime.checkHours` was read to rule out clock clamping
   (`last < 0 ? now : min(last, now)`, which discards nothing). Unexplained; the qualitative result
   (≈1 day of age per game day) is unaffected. (M, `exp02-20260910-030433` — note the artifact's
   `summary.c.expectedAtRotSpeed1 = 1.0209` is the same prediction over the narrower *wait* window,
   which flatters the gap to 1.3 %; the containing window is computed from the two `serverWorldAge`
   stamps the artifact also carries.)
2. **The thaw rate does not reproduce.** Phase (d) measured **47.25 %/game-hour** (2.12 h to thaw)
   against the code's `t = 1.5` h (66.7 %/h); the same script measured 67.8 %/h (1.48 h) in the
   uncommitted shakedown run `exp02-20260910-025434` — same time speed, same container. **Do not
   quote a thaw number as measured** without a third run. The Δ`age` = 0 result the phase exists for
   reproduced in both.
3. **A stray `cookingTime` arrives on the wrong item — probably a real sync defect.** After
   `item.set … Base.Apple calories 999` + `sendItemStats(apple)`, the client's apple came back with
   `cookingTime = 71.119644` — the steak's `cookingTime` at the previous `sendItemStats`, a value
   the apple never had on either side (server 0, client baseline 0). Same item id on both sides, an
   empty baseline diff, a single field diverging, and `minutesToCook`/`minutesToBurn` correct on
   both — so it is not a harness lookup ambiguity. Working reading: an `ItemStatsPacket` write/read
   asymmetry for `cookingTime` on a **non-cookable** item (a field not re-initialised between
   sends). It reproduced in the shakedown run with that run's then-current steak value, and survived
   cooling the steak below the cooking gate. Three discriminating runs would settle it: (i) set the
   steak's `cookingTime` to a distinctive value, sync steak then apple, and see whether the apple
   tracks it; (ii) sync the apple twice with no steak send in between; (iii) sync an apple in a
   session where no cookable item was ever synced. **Mod-relevant hazard:** any mod that reads
   `getCookingTime()` client-side on non-cookable food may be reading another item's value.
   (M, `exp02-20260910-030433`.)
4. **The fridge and freezer *container* multipliers are unmeasured.** `isInFridge`/`isInFreezer`
   need a real placed appliance whose container type is `fridge`/`freezer` (or whose parent carries
   `IsoPropertyType.IS_FRIDGE`), on a square where `getSourceGrid().haveElectricity()` — which the
   fixture world does not provide at the spawn point. The cheapest route for a future run is
   `container.customTemperature`, which short-circuits `getTemprature()` (`@0–@13 L2681-2682`),
   or spawning an appliance. Only the ×0 frozen rate (which needs no appliance, via `freeze()`) has
   been measured.
5. **Does food age at all in single-player at default settings?** Code says no: `Food.update` gates
   `updateAge` on `GameServer.server`, `updateRotting` returns on clients and otherwise needs
   `ReplaceOnRotten` or `DaysForRottenFoodRemoval >= 0` (−1 in all five shipped presets), and the
   container hooks are server-gated — leaving only `IsoCompost.update` and
   `ISWorldObjectContextMenuLogic.handleGrabWorldItem`. Either a real 42.20.4 regression or a call
   site not yet found. The harness runs a dedicated server, so it does not bite here; it must not be
   stated as fact without an SP measurement.
6. **Where is the syncing `updateAge(true)` actually called from?** Only the no-arg
   `Food.updateAge()` passes the `UpdateLimit` result, and its callers are `updateRotting`'s
   `ReplaceOnRotten` branch and `IsoCompost` — so on a dedicated server the 1 Hz `sendItemStats` on a
   rot transition effectively never fires for ordinary food. Worth confirming against a live log.
7. **Client-side rot display refresh cadence in MP.** If the client never ages and no stats packet
   carries `age`, freshness comes from the last full serialization; whether and how often the server
   re-sends inventory items was not traced (`GameClient.receiveSendItemListNet` exists).
8. **`cooked` in `ItemStatsPacket` is C, not M** — both sides were already `false` when read. One
   divergence test (set `cooked` server-side only, then read the client) would upgrade it.
9. **Enum labels.** `getFridgeFactor` / `getFoodRotSpeed` were decoded from the raw `tableswitch`
   (cases 1–6 / 1–5, default 3); the translation labels ("Very Low", "Normal", …) were not read.
   Only the numeric mapping is C.
10. **Vestigial and mod-facing fields.** `Food.rottenTime` has a getter, a setter and save/load
    support, no script key, one writer (`IsoCompost.update`) and **zero readers**. `Poison` and
    `UseForPoison` parse into fields with no Java or vanilla-Lua reader. Both look like mod-facing
    API rather than mechanics, but a reader outside `media/lua` would not show in these scans.
11. **Two evolved-recipe corners were not dumped**: a reader for `AddIngredientIfCooked` (37 recipe
    blocks use it) was not traced beyond `checkItemCanBeUse @258`, and `EvolvedRecipe.useSpice` (two
    overloads) was not dumped, so the spice branch's effect beyond the herbal-tea sums is unread.
12. **`DaysFresh == DaysTotallyRotten` items** (slice 01's open question 10, the rot-roll denominator
    that takes the 100 % branch in `JustAteFood @759 L720`): a parse of all 722 `base:food` blocks
    finds **exactly one** — `item RatKing` (`media/scripts/generated/items/food.txt:15417`), with
    both keys at `0`, so it spawns already rotten (`age 0 >= offAgeMax 0`) while `canAge()` is still
    true. All 497 items that declare either threshold declare both; the smallest non-zero gap is 1
    day (29 items). Ev C — the *behaviour* of that item at eat time is still unmeasured.

---

## Sources

**Jar (pzdis, 42.20.4 `b0bbce05d5`, `D:\SteamLibrary\steamapps\common\ProjectZomboid\projectzomboid.jar`)**
`zombie/inventory/types/Food` (`update`, `updateAge(Z)`, `updateFreezing`, `updateRotting`,
`setAutoAge`, `setFreezingTime`, `freeze`, `isFreezing`, `isThawing`, `isFresh`, `isRotten`,
`canAge`, `getFridgeFactor`, `getFoodRotSpeed`, `getHungerChange`, `getThirstChange`, `getCalories`
and siblings, `setCooked`, `setBurnt`, `setRotten`, `isPackaged`, `isPoison`, `getUseForPoison`,
`save`, `load`); `zombie/inventory/InventoryItem` (`getAge`, `setAge`, `getOffAge`, `getOffAgeMax`,
`isCookable`, `getCookingTime`, `getStringItemType`, `update`, `calculateTimeMultiplier`);
`zombie/inventory/ItemContainer` (`isFridge`, `isFreezer`, `getTemprature`, `AddItem`);
`zombie/scripting/objects/Item` (`DoParam`, `InstanceItem`, `OnScriptsLoaded`);
`zombie/scripting/objects/EvolvedRecipe` (`Load`, `addItem`, `addPoison`, `checkItemCanBeUse`,
`getItemsCanBeUse`, `hasMinimumWater`, `needToBeCooked`); `zombie/scripting/objects/RecipeCodeOnCooked`;
`zombie/inventory/ItemPickerJava` (`doRollItemInternal`, `rotItem`, `getLootType`);
`zombie/iso/IsoCell.ProcessItems`, `zombie/iso/objects/IsoStove`, `IsoCompost`;
`zombie/characters/IsoGameCharacter` (`updateInternal`, `recursiveItemUpdater`, `isKnownPoison`);
`zombie/network/packets/ItemStatsPacket`, `SyncItemFieldsPacket`; `zombie/GameTime.checkHours`;
`zombie/SandboxOptions`.

**Lua (`D:\SteamLibrary\steamapps\common\ProjectZomboid\media\lua`)**
`shared/TimedActions/ISAddItemInRecipe.lua`, `client/ISUI/ISInventoryPaneContextMenu.lua`,
`client/ISUI/ISDumpContentsAction.lua` path (`shared/TimedActions/ISDumpContentsAction.lua`),
`client/Foraging/ISForageIcon.lua`, `shared/Sandbox/{Apocalypse,Extinction,Outbreak,Rising,SixMonthsLater}.lua`.

**Scripts (`media/scripts/generated/`)** `items/food.txt` (722 `base:food` blocks, 15 525 lines;
`item RatKing` at `:15417`, `item CannedBologneseOpen` at `:3644`), `items/drainable.txt`
(150 `base:drainable` blocks, 2 420 lines; `item TestWaterMug` at `:83-84`), `evolvedrecipes.txt`
(62 `evolvedrecipe` blocks, block `Salad`). Key inventories:
`.superpowers/sdd/02-food-item-model/food-keys.txt` (78 keys) and `drainable-keys.txt` (82 keys),
114 distinct.

**Measured run.** `exp02-20260910-030433` —
[`testing/artifacts/exp02-20260910-030433/lifecycle.json`](../../testing/artifacts/exp02-20260910-030433/lifecycle.json)
(sha256 `8cce2fa9…`), one live session, seven phases (client-side getter arithmetic, server-age
visibility, one accelerated game day, frozen, cooking transitions, the evolved-recipe summation, MP
ownership), 329 s wall, **0 server errors**, fixture `default`. Script:
`testing/experiments/s02_lifecycle.py`. Sandbox as measured: `FoodRotSpeed 3`, `FridgeFactor 3`,
`DaysForRottenFoodRemoval −1`, `ElecShutModifier 14`. The harness commands this run added are listed
in [`../testing/README.md`](../testing/README.md). An earlier shakedown run of the same script
(`exp02-20260910-025434`) is **not** committed and is cited here only where it is named as
non-evidence (the thaw-rate disagreement and the perk-overwrite rationale).

**Wiki mirrors** [fridge.md](../../references/wiki-mirrors/fridge.md) (page version 41.78.19),
[evolved-recipes.md](../../references/wiki-mirrors/evolved-recipes.md) (41.78.19),
[appliances.md](../../references/wiki-mirrors/appliances.md) (42.8.0),
[food.md](../../references/wiki-mirrors/food.md) (42.20.0),
[nutritional-values.md](../../references/wiki-mirrors/nutritional-values.md) (42.20.0),
[cooking.md](../../references/wiki-mirrors/cooking.md) (42.18.0). Absent: "Food spoilage" (404,
2026-09-10); "Refrigerator" and "Freezer" redirect to `Appliances`.

**Prior work in this library** [eating-pipeline.md](eating-pipeline.md) (slice 01 — the intake
arithmetic and the full state-modifier table this document deliberately does not repeat),
[nutrition-core.md](nutrition-core.md), [../testing/spikes.md](../testing/spikes.md) §S6 (item-state
ownership), `docs/superpowers/plans/02-notes.md` (the Q1–Q8 code map behind every C claim here; its
Q5 "1.667×" wording is corrected in § Evolved recipes),
`.superpowers/sdd/02-food-item-model/task-M-report.md` (the measured run's own report).
