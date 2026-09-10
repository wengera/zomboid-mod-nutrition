# Slice 02 (P1c) — food item model & lifecycle — research notes

**Verified against: 42.20.4** (jar `D:\SteamLibrary\steamapps\common\ProjectZomboid\projectzomboid.jar`,
scripts `media/scripts/generated/`) · 2026-09-10 · code-reading steps only.

Evidence grades: **C** read from bytecode/Lua/scripts (everything below unless marked),
**M** measured on the live dedicated server, **W** wiki mirror. Every claim here is **Ev = C**;
the (M) steps of Tasks 2–4 are a later dispatch and are specified under *Experiment inputs*.

Citation form: `zombie/inventory/types/Food.update() @<bytecode offset> L<source line>`; script
files by block name and line; Lua by `file:line`.

Prior findings cited, not re-derived: `docs/vanilla/eating-pipeline.md` (intake arithmetic, the
full state-modifier table, server authority), `docs/superpowers/plans/01-notes.md` (the five
near-identical `Food` getters), `docs/testing/spikes.md` S6 (item-state ownership).

---

## Q1 — Script keys for food and drainable items, and the loader

### The loader

One method parses every `Key = Value` line of an `item` block for **all** item types:
`zombie/scripting/objects/Item.DoParam(String,String)` — an 11 920-byte if/else chain of
`key.trim().equalsIgnoreCase("<Key>")` tests, **440 comparisons / 396 distinct keys**
(`Item.DoParam(Ljava/lang/String;Ljava/lang/String;)V @0 L1969` … `@11920 L3008`). The one-arg
`Item.DoParam(String) @0 L1951` merely splits on the first `=` and delegates (`@38 L1960`).

**Unknown keys are not dropped and do not throw.** The fall-through at
`Item.DoParam @11805 L2992` traces to `DebugType.DetailedInfo` and then writes the key into the
item's `defaultModData` Lua table — as a `Double` if the value parses, otherwise as the raw
`String` (`@11832–@11894 L2993–L3003`). So a "dead" key silently becomes mod data readable from
Lua via the instantiated item's mod data. Malformed *values* on a known key do throw:
`InvalidParameterException(key, item.name)` at `@11898–@11919 L3005–L3006`.

Value types, as parsed:

| pattern in the loader | meaning |
|---|---|
| `Integer.parseInt(v)` | int |
| `Float.parseFloat(v)` | float |
| `Boolean.parseBoolean(v)` | bool — only the literal `true` (any case) is true |
| `v.equalsIgnoreCase("true")` | bool — same effective semantics, different code path |
| `v.trim().split(";")` + `Arrays.asList` / `ArrayList.add` | list |
| bare `putfield` | string |

### The two inventories

Generated with `grep -oE "^\s*[A-Za-z]+\s*=" <file> | sed 's/[ =]//g' | sort | uniq -c | sort -rn`:

- `.superpowers/sdd/02-food-item-model/food-keys.txt` — **78 distinct keys** over 722
  `ItemType = base:food` blocks (`media/scripts/generated/items/food.txt`, 15 525 lines).
- `.superpowers/sdd/02-food-item-model/drainable-keys.txt` — **82 distinct keys** over 150
  `ItemType = base:drainable` blocks (`drainable.txt`, 2 420 lines).
- Union: **114 distinct keys**, 46 of them shared.

### Dead keys — 2 of 114

| Key | Where | Why dead |
|---|---|---|
| `IsWaterSource` | `drainable.txt:83`, only on `item TestWaterMug` | no branch in `Item.DoParam`; the literal exists only in `generation/builders/ItemBuilder.class` (the *script generator*, not the runtime) |
| `RainFactor` | `drainable.txt:84`, only on `item TestWaterMug` | no branch in `Item.DoParam`; recognised only by `zombie/scripting/entity/components/fluids/FluidContainerScript` **inside a `component FluidContainer { … }` block**, never at item top level |

Both land in `defaultModData` at runtime. `TestWaterMug` is the only item in either file that
carries them, so this is a test-item leftover, not a live feature.

Two further keys are **parsed but effectively unread on the item instance** — see Q6
(`CannedFood`) and Q7 (`Poison`, `UseForPoison`). They are *not* dead keys in the loader sense.

### Key reference table

All 114 keys. `food`/`drain` = occurrence count in each generated file. `Ev = C` on every row.

| Key | Type | food | drain | Java field / getter | Runtime effect |
|---|---|---:|---:|---|---|
| `ActivatedItem` | bool("true") | 0 | 17 | `Item.activatedItem` `@6608 L2551` | item can be switched on (torches) |
| `AlcoholPower` | float | 0 | 2 | `Item.alcoholPower` `@7763 L2639` | drunkenness per use |
| `AnimalFeedType` | string | 22 | 2 | `Item.animalFeedType` `@1412 L2104` | which animals will eat it |
| `AttachmentType` | string | 0 | 2 | `Item.attachmentType` `@9468 L2774` | hotbar/attachment slot |
| `BadCold` | bool("true") | 61 | 0 | `Item.badCold` → `Food.setBadCold` (`InstanceItem @843 L1588`) | `getUnhappyChange +2` when `isBadCold && isCookable && isCooked && heat < 1.3` (slice 01 table) |
| `BadInMicrowave` | bool("true") | 115 | 0 | `Item.badInMicrowave` → `Food.setBadInMicrowave` (`InstanceItem @825 L1586`) | on the cook transition in a `microwave` container: `unhappyChange = 5`, `boredomChange = 5`, `cookedInMicrowave = 1` (`Food.update @719–@752 L472–L475`) |
| `BoredomChange` | int | 5 | 0 | `Item.boredomChange` `@1553 L2116` | BOREDOM at eat time; +30 frozen / +20 burnt / +10 stale / +20 rotten (slice 01) |
| `Calories` | float | 597 | 2 | `Item.calories` → `Food.setCalories` (`InstanceItem @772 L1581`) | nutrition; **not** rescaled at instantiation, **no** state modifier (slice 01) |
| `CannedFood` | bool(parseBoolean) | 41 | 0 | `Item.cannedFood` (no getter, not copied to the instance) | read only via the *script* object: `InventoryItem.getStringItemType()` → `"CannedFood"`, `ItemPickerJava.getLootType()`, and the spawn-rot exemption in `ItemPickerJava.rotItem @17–@28` — see Q6 |
| `CanStoreWater` | bool("true") | 0 | 1 | `Item.canStoreWater` `@361 L2003` | legacy water flag (B42 uses fluid components) |
| `cantBeConsolided` | bool("true") | 0 | 54 | `Item.cantBeConsolided` `@9190 L2752` | blocks the "consolidate" UI action |
| `CantBeFrozen` | bool("true") | 51 | 2 | `Item.cantBeFrozen` → **inverted** `Food.setCanBeFrozen(!cantBeFrozen)` (`InstanceItem @790–@804 L1583`) | gates `isFreezing()`/`isThawing()` (`Food.isFreezing @6 L2191`) — an item that cannot be frozen never accumulates `freezingTime` and so never gets the ×0 age rate |
| `CantEat` | bool(parseBoolean) | 96 | 1 | `Item.cantEat` / `Item.isCantEat()` | hides the Eat option; **also** exempts a `CannedFood` item from spawn rot (`ItemPickerJava.rotItem @24–@28`) |
| `Carbohydrates` | float | 597 | 2 | `Item.carbohydrates` → `Food.setCarbohydrates` | as `Calories` |
| `ChanceToSpawnDamaged` | int | 0 | 3 | `Item.chanceToSpawnDamaged` `@6311 L2529` | loot condition roll |
| `ColorBlue`/`ColorGreen`/`ColorRed` | int | 4 each | 0 | `Item.colorBlue/Green/Red` `@8951/@8927/@8903 L2733/L2731/L2729` | item tint; copied to an evolved-recipe result (`EvolvedRecipe.addItem @51–@107 L274–L277`) |
| `ConditionLowerStandard` | float | 0 | 1 | `Item.conditionLowerNormal` `@9348 L2764` | wear rate |
| `ConditionMax` | int | 12 | 10 | `Item.conditionMax` `@3607 L2309` | durability ceiling |
| `ConsolidateOption` | string | 0 | 16 | `Item.consolidateOption` `@9516 L2778` | consolidate menu label |
| `CookingSound` | string | 198 | 1 | `Item.cookingSound` `@1484 L2110` → `Food.getCookingSound()` | played while `shouldPlayCookingSound()` (client only: `@0–@7 L595–L597`) |
| `CustomContextMenu` | string | 33 | 4 | `Item.customContextMenu` `@6983 L2579` | menu label override (`Drink` etc.) |
| `CustomEatSound` | string | 119 | 1 | `Item.customEatSound` `@7631 L2629` | eat SFX |
| `DangerousUncooked` | bool("true") | 81 | 0 | `Item.dangerousUncooked` → `Food.setbDangerousUncooked` | 75 % poison roll (5 % with tag `EGG`) in `BodyDamage.JustAteFood @555–@676 L669–L696` (slice 01); also propagates onto an evolved-recipe result (`EvolvedRecipe.addItem @1016–@1043 L383-384`) and blocks a raw ingredient when the result is not cookable (`checkItemCanBeUse @232–@258 L243`) |
| `DaysFresh` | int | 497 | 0 | `Item.daysFresh` → `Food.setOffAge` (`InstanceItem @601–@604 L1562`) | the stale threshold in **days**; absent ⇒ `offAge` stays `1 000 000 000` |
| `DaysTotallyRotten` | int | 497 | 0 | `Item.daysTotallyRotten` → `Food.setOffAgeMax` (`InstanceItem @610–@613 L1563`) | the rotten threshold in **days**; `offAgeMax == 1 000 000 000` is the "never ages" sentinel (`Food.canAge @1–@7 L2577`) |
| `DisappearOnUse` | bool("true") | 0 | 18 | `Item.disappearOnUse` `@5791 L2487` | destroy at 0 uses |
| `DisplayCategory` | string | 722 | 150 | `Item.displayCategory` `@6794 L2565` | inventory grouping |
| `DoubleClickRecipe` | string | 4 | 12 | `Item.doubleClickRecipe` `@11065 L2928` | recipe fired by double-click |
| `Eattime` | int | 17 | 2 | `Item.eatTime` `@11686 L2982` | hard override of `maxTime` when `> 0` (`ISEatFoodAction.lua:247`, slice 01) |
| `EatType` | string | 266 | 7 | `Item.eatType` `@10470 L2884` | animation set; `popcan` forces `maxTime = 160` (slice 01) |
| `enduranceChange` | float | 1 | 0 | `Item.enduranceChange` `@1247 L2090` | ENDURANCE at eat time; ÷3 burnt, ÷2 stale, ×2 cooked (slice 01) |
| `EquipSound` | string | 0 | 1 | `Item.equipSound` `@2641 L2216` | SFX |
| `EvolvedRecipe` | list of `Name:use[\|Cooked]` | 372 | 2 | `Item.evolvedRecipe` (raw strings) **and** `Item.itemRecipeMap` (`ItemRecipe{itemName, module, use, cooked}`) `@9916–@10247 L2820–L2865` | registers the item as an ingredient; `use` is hunger *points* (÷100 → hunger units at `EvolvedRecipe.addItem @518–@545 L333`). Aliases applied at parse: `RicePot`/`RicePan` → `Rice`, `PastaPot`/`PastaPan` → `Pasta`, `Roasted Vegetables` → `Stir fry` (`@10124–@10192 L2849–L2856`) |
| `EvolvedRecipeName` | string | 172 | 1 | `Item.evolvedRecipeName` `@9131 L2747` + `Translator.setDefaultItemEvolvedRecipeName` | the name this ingredient contributes to the generated dish name (`ISAddItemInRecipe.checkName`) |
| `fatigueChange` | float | 3 | 1 | `Item.fatigueChange` `@1223 L2088` | FATIGUE at eat time |
| `FillFromDispenserSound` / `FillFromTapSound` | string | 0 | 1 each | `Item.fillFromDispenserSound` `@7655 L2631` / `.fillFromTapSound` `@7709 L2635` | SFX |
| `FireFuelRatio` | float | 0 | 5 | `Item.fireFuelRatio` `@11761 L2988` | burn value as fuel |
| `FishingLure` | bool(parseBoolean) | 41 | 0 | `Item.fishingLure` `@7115 L2589` | usable as bait |
| `fluReduction` | int | 2 | 0 | `Item.fluReduction` `@8783 L2719` | `bodyDamage.coldReduction += fluReduction*f` (slice 01) |
| `FoodSicknessChange` | int | 8 | 4 | `Item.foodSicknessChange` `@8807 L2721` | cures FOOD_SICKNESS + POISON when negative, gated by the edible-buff timer (slice 01) |
| `FoodType` | string | 362 | 2 | `Item.foodType` `@415 L2007` | evolved-recipe category grouping in the context menu (`ISInventoryPaneContextMenu.getEvoItemCategories`) |
| `GoodHot` | bool("true") | 148 | 0 | `Item.goodHot` → `Food.setGoodHot` (`InstanceItem @834 L1587`) | `getUnhappyChange −2` when `isGoodHot && isCookable && isCooked && heat > 1.3` (slice 01) |
| `HerbalistType` | string | 18 | 0 | `Item.herbalistType` `@5659 L2477` | herbalist knowledge gating |
| `HungerChange` | float | 606 | 2 | `Item.hungerChange` `@1175 L2084` → `Food.hungChange` **÷ 100** at `InstanceItem @546–@595` | the item's hunger relief; also seeds `baseHunger` |
| `Icon` | string | 720 | 150 | `Item.icon` + `itemName`, `normalTexture`, `worldTextureName`, `worldTexture` `@532 L2017` | textures |
| `IconColorMask` | string | 0 | 3 | `Item.iconColorMask` `@11113 L2932` | icon tinting mask |
| `IconsForTexture` | list | 2 | 0 | `Item.iconsForTexture` `@10714 L2900` | per-texture icon set |
| `InverseCoughProbability` | int | 6 | 1 | `Item.inverseCoughProbability` `@8831 L2723` | cold-cough suppression |
| `InverseCoughProbabilitySmoker` | int | 6 | 1 | `Item.inverseCoughProbabilitySmoker` `@8855 L2725` | as above, smoker trait |
| `IsCookable` | bool("true") | 251 | 1 | `Item.isCookable` → `Food.setIsCookable` (`InstanceItem @619–@622 L1564`) | gates the whole cooking block of `Food.update @49–@60 L372`; **also cleared to `false`** when a burnt item starts a fire (`Food.update @1147 L517`) |
| `IsDung` | bool(parseBoolean) | 10 | 0 | `Item.isDung` `@3114 L2265` | fertiliser |
| `IsWaterSource` | **DEAD** | 0 | 1 | — | no loader branch; ends up in `defaultModData` |
| `ItemType` | string | 722 | 150 | `Item.itemType` (`ItemType.get(ResourceLocation.of(v))`) `@307 L1999` | picks the `InventoryItem` subclass in `InstanceItem` |
| `KeepOnDeplete` | bool("true"), **inverted** | 0 | 18 | `Item.disappearOnUse = !("true")` `@9241–@9266 L2756` | alias of `DisappearOnUse` with the sense flipped |
| `LightDistance` | int | 0 | 17 | `Item.lightDistance` `@6716 L2559` | torch |
| `LightStrength` | float | 0 | 17 | `Item.lightStrength` `@6662 L2555` | torch |
| `Lipids` | float | 597 | 2 | `Item.lipids` → `Food.setLipids` | as `Calories` |
| `MakeUpType` | string | 0 | 3 | `Item.makeUpType` `@9492 L2776` | cosmetics |
| `MechanicsItem` | bool(parseBoolean) | 0 | 3 | `Item.mechanicsItem` `@996 L2067` | loot category |
| `Medical` | bool(parseBoolean) | 1 | 7 | `Item.medical` `@948 L2063` | loot category |
| `MetalValue` | float | 0 | 30 | `Item.metalValue` `@256 L1995` | scrapping |
| `MinutesToBurn` | int | 246 | 0 | `Item.minutesToBurn` → `Food.setMinutesToBurn` | `cookingTime > minutesToBurn` ⇒ burnt (`Food.update @894–@913 L494–L496`) |
| `MinutesToCook` | int | 249 | 0 | `Item.minutesToCook` → `Food.setMinutesToCook` (`InstanceItem @628–@632 L1565`) | `cookingTime > minutesToCook` ⇒ cooked (`Food.update @186–@221 L397`) |
| `OnCooked` | string | 11 | 0 | `Item.onCooked` → `Food.setOnCooked` (`InstanceItem @702–@705 L1573`) | Lua/`RecipeCodeOnCooked` hook fired on the cook transition (`Food.update @627–@718 L462–L467`); dotted names are split on `.` and resolved as `table.field` |
| `OnCreate` | string | 21 | 4 | `Item.luaCreate` `@11017 L2924` | Lua hook at instantiation |
| `OnEat` | string | 19 | 4 | `Item.onEat` → `Food.setOnEat` | Lua hook fired inside `Eat` after nutrition, before consume (slice 01) |
| `OpeningRecipe` | string | 18 | 0 | `Item.openingRecipe` `@11041 L2926` | the recipe that opens a sealed can |
| `Packaged` | bool("true") | 129 | 2 | `Item.packaged` → `Food.setPackaged` (`InstanceItem @781–@787 L1582`) | `Food.isPackaged() @0 L2147` — a pure flag; **no Java reader in the jar and no vanilla Lua reader** (Q6) |
| `painReduction` | int | 2 | 0 | `Item.painReduction` `@8879 L2727` | `bodyDamage.painReduction += painReduction*f` (slice 01) |
| `PoisonPower` | int | 4 | 0 | `Item.poisonPower` `@477 L2011` → `Food.poisonPower` (`InstanceItem @531`) | POISON/PAIN at eat time (slice 01); drains fully into an evolved-recipe result (`EvolvedRecipe.addPoison @67–@107 L535–L539`) |
| `PourType` | string | 49 | 23 | `Item.pourType` `@10494 L2886` | pour animation/SFX |
| `primaryAnimMask` | string | 0 | 18 | `Item.primaryAnimMask` `@10302 L2870` | animation |
| `Proteins` | float | 597 | 2 | `Item.proteins` → `Food.setProteins` | as `Calories` |
| `RainFactor` | **DEAD** | 0 | 1 | — | only valid inside a `component FluidContainer` block |
| `ReduceInfectionPower` | float | 3 | 0 | `Item.reduceInfectionPower` `@7817 L2643` | wound-infection reduction; summed for herbal-tea ingredients (`EvolvedRecipe.addItem @679–@692 L344`) |
| `RemoveNegativeEffectOnCooked` | bool("true") | 5 | 0 | `Item.removeNegativeEffectOnCooked` → `Food.setRemoveNegativeEffectOnCooked` | on the cook transition, zeroes `thirstChange`, `unhappyChange`, `boredomChange` **if positive** — permanent, one-shot (`Food.update @578–@626 L451–L459`) |
| `RemoveUnhappinessWhenCooked` | bool(parseBoolean) | 36 | 0 | `Item.removeUnhappinessWhenCooked` `@1628 L2122` | on the cook transition, `setUnhappyChange(0)` (`Food.update @418–@432 L424-L425`) — read off the **script** object, not the instance |
| `ReplaceInPrimaryHand` / `ReplaceInSecondHand` | string | 0 | 6 each | `Item.replaceInPrimaryHand` `@10422 L2880` / `.replaceInSecondHand` `@10398 L2878` | held-model swap |
| `ReplaceOnCooked` | list (`;`) | 3 | 0 | `Item.replaceOnCooked` (`Arrays.asList(split(";"))`) `@6950 L2577` → `Food.setReplaceOnCooked` | on the cook transition **and only if not rotten**, each name is `AddItem`-ed to the container with `copyConditionStatesFrom(this)`, then the original is removed and `Food.update` **returns** — the item is replaced, never flagged cooked (`Food.update @224–@412 L398–L421`) |
| `ReplaceOnDeplete` | string | 0 | 42 | `Item.replaceOnDeplete` `@1652 L2124` | drainable → empty container |
| `ReplaceOnExtinguish` | string | 0 | 6 | `Item.replaceOnExtinguish` `@1673 L2126` | torch burnout |
| `ReplaceOnRotten` | string | 8 | 0 | `Item.replaceOnRotten` → `Food.setReplaceOnRotten` (`InstanceItem @807–@813 L1584`) | forces `updateRotting` to age the item every tick and, once rotten, create the replacement, copy `age` + condition states, and destroy the original (`Food.updateRotting @20–@226 L662–L694`) |
| `ReplaceOnUse` | string | 110 | 0 | `Item.replaceOnUse` `@3724 L2319` | container left behind when consumed; also the weight base in `Eat`'s custom-weight branch (slice 01) |
| `RequireInHandOrInventory` | list | 6 | 1 | `Item.requireInHandOrInventory` `@4961 L2423` | use precondition |
| `Researchablerecipes` | list | 1 | 26 | `Item.addResearchableRecipe(…)` `@9651 L2792` | learnable-by-research recipes |
| `ScaleWorldIcon` | float | 0 | 1 | `Item.scaleWorldIcon` `@1044 L2071` | world sprite scale |
| `secondaryAnimMask` | string | 0 | 18 | `Item.secondaryAnimMask` `@10326 L2872` | animation |
| `SoundMap` | list → HashMap | 40 | 34 | `Item.soundMap` `@5396 L2455` | per-event sound overrides |
| `Spice` | bool("true") | 109 | 2 | `Item.spice` → `Food.setSpice` (`InstanceItem @675–@678 L1570`) | takes the ingredient down the **spice branch** of `EvolvedRecipe.addItem @582–@775 L336–L359`: no hunger/nutrition transfer, does not count against `MaxItems`, only once per dish (`isSpiceAdded`) |
| `StaticModel` / `WorldStaticModel` | string | 532/718 | 73/150 | `Item.staticModel` `@10254 L2866` / `.worldStaticModel` `@10278 L2868` | models |
| `StaticModelsByIndex` / `WorldStaticModelsByIndex` | list | 2 each | 0 | `Item.staticModelsByIndex` `@11305 L2950` / `.worldStaticModelsByIndex` `@11374 L2956` | per-index models |
| `StressChange` | int | 28 | 3 | `Item.stressChange` `@1578 L2118` | STRESS at eat time; ÷4 burnt, ÷1.3 stale, ÷2 rotten, ×1.3 cooked (slice 01) |
| `SurvivalGear` | bool(parseBoolean) | 2 | 22 | `Item.survivalGear` `@1020 L2069` | loot category |
| `Tags` | list (`;`) → `Set<ItemTag>` | 401 | 118 | `Item.tags` (via `ItemTag.get(ResourceLocation.of(v))`) `@4243 L2362` | drives `ALREADY_COOKED`, `NO_COOKING_XP`, `DRIED_FOOD`, `HERBAL_TEA`, `BOOSTS_FLU_RECOVERY`, `ALCOHOLIC_BEVERAGE`, `GOOD_FROZEN`, `EGG` — all read in `Food.update` / `EvolvedRecipe.addItem` / `JustAteFood` |
| `ThirstChange` | float | 112 | 0 | `Item.thirstChange` `@1199 L2086` → `Food.thirstChange` **÷ 100** | THIRST at eat time; ÷5 burnt beats ÷2 cooked (slice 01) |
| `ticksPerEquipUse` | int | 0 | 3 | `Item.ticksPerEquipUse` `@5764 L2485` | drain rate while equipped |
| `Tooltip` | string | 61 | 49 | `Item.tooltip` `@6770 L2563` | translated tooltip key |
| `TorchCone` | bool("true") | 0 | 17 | `Item.torchCone` `@6689 L2557` | light shape |
| `TorchDot` | float | 0 | 6 | `Item.torchDot` `@5962 L2501` | light shape |
| `UnequipSound` | string | 0 | 1 | `Item.unequipSound` `@2662 L2218` | SFX |
| `UnhappyChange` | int | 292 | 2 | `Item.unhappyChange` `@1603 L2120` | UNHAPPINESS at eat time; +30 frozen / +20 burnt / +10 stale / +20 rotten, ±2 for badCold/goodHot (slice 01) |
| `UseDelta` | float | 2 | 146 | `Item.useDelta` `@5938 L2499` | fraction consumed per use |
| `UseWhileEquipped` | bool("true") | 2 | 134 | `Item.useWhileEquipped` `@5710 L2481` | drains while held |
| `UseWhileUnequipped` | bool("true") | 0 | 1 | `Item.useWhileUnequipped` `@5737 L2483` | drains in the bag |
| `UseWorldItem` | bool(parseBoolean) | 0 | 1 | `Item.useWorldItem` `@924 L2061` | usable from the ground |
| `VehicleType` | int | 0 | 3 | `Item.vehicleType` `@9276 L2758` | vehicle part |
| `Weight` | float | 722 | 150 | `Item.actualWeight` (and `weight`) `@1089 L2075` | encumbrance |
| `WeightEmpty` | float | 2 | 9 | `Item.weightEmpty` `@1151 L2082` | weight when depleted |

---

## Q2 — The aging model

### Fields (all on `InventoryItem`, not `Food`)

| Field | Accessor | Units | Set from |
|---|---|---|---|
| `age` | `getAge()F @0 L2527` / `setAge(F) @0 L2531` | **days** (float) | `setAutoAge()` at loot spawn, then `updateAge` |
| `offAge` | `getOffAge()I @0 L2607` / `setOffAge(I) @0 L2611` | days (int) | script `DaysFresh`, default `1 000 000 000` |
| `offAgeMax` | `getOffAgeMax()I @0 L2615` / `setOffAgeMax(I) @0 L2619` | days (int) | script `DaysTotallyRotten`, default `1 000 000 000` |
| `lastAged` | (field) | game **world hours** | `updateAge` |
| `freezingTime` | `Food.getFreezingTime()F @0 L2155` / `setFreezingTime(F) @0 L2159` | percent 0–100 | `updateFreezing`, `freeze()` |
| `lastFrozenUpdate` | (field) | game world hours | `updateFreezing` |
| `frozen` | `Food.isFrozen()Z @0 L2174` / `setFrozen(Z) @0 L2178` | bool | **only** `Food.setFreezingTime` flips it (see below) |
| `rotten` | `Food.setRotten(Z) @0 L1846` | bool | **write-only — see below** |
| `rottenTime` | `Food.getRottenTime()F @0 L2306` | — | written only by `IsoCompost.update`; **zero readers in the jar**; has no script key |

### `isFresh` / `isRotten` / `canAge`

```java
boolean canAge()   { return getOffAgeMax() != 1_000_000_000; }        // @1–@7  L2577
boolean isFresh()  { if (isFertilized()) return true;                 // @0–@8  L1839-L1840
                     return age <  (float) offAge; }                  // @9–@27 L1842
boolean isRotten() { if (isFertilized()) return false;                // @0–@8  L1832-L1833
                     return age >= (float) offAgeMax; }               // @9–@27 L1835
```

"Stale" is the un-named middle band `offAge <= age < offAgeMax` (that is how
`Food.getHungerChange` tests it, slice 01).

> **`setRotten(boolean)` is inert.** `Food.setRotten(Z) @0–@5 L1846-L1847` writes the field
> `Food.rotten`, and **nothing in the jar ever reads that field** — `isRotten()` reads `age`.
> This is the code-level confirmation of slice 01's measured "`setRotten(true)` did not stick"
> (`docs/vanilla/eating-pipeline.md`, modifier table). Vanilla itself never trusts it alone:
> `ItemPickerJava.rotItem @59–@70 L2253-L2254` calls `setRotten(true)` **and then**
> `setAge(getOffAgeMax())`.

### The tick — `Food.updateAge`

```java
void updateAge() {                                   // @0–@10 L732-L733
    updateAge(updateAgeRate.Check());                // static UpdateLimit(1000 ms), Food.<clinit> @0–@10 L72
}                                                    // the boolean is the SYNC gate, not the age gate

void updateAge(boolean sync) {                                                  // L736
    float nowH = (float) GameTime.getInstance().getWorldAgeHours();             // @0  L736
    ItemContainer c = getOutermostContainer();                                  // @8  L738
    updateFreezing(c, nowH);                                                    // @13 L739
    lastAged = GameTime.checkHours(lastAged, nowH);                             // @19 L741
    if (nowH <= lastAged) return;                                               // @35 L742
    double dH = nowH - lastAged;                                                // @44 L743

    // --- heat tracks the container -------------------------------------------------
    if (c != null && heat != c.getTemprature()) {                               // @53 L744
        if (dH < 1/3.0) {                                                       // @69 L745   (20 min)
            if (!IsoWorld.instance.getCell().getProcessItems().contains(this)) {// @78 L746
                heat = GameTime.instance.Lerp(heat, c.getTemprature(),
                                              (float) dH / (1/3f));             // @94 L747
                IsoWorld.instance.getCell().addToProcessItems(this);            // @119 L748
            }
        } else heat = c.getTemprature();                                        // @132 L751
    }

    // --- rate modifiers -------------------------------------------------------------
    if (isFrozen())                       dH *= 0.0;                            // @140 L754-755  FROZEN STOPS AGING
    else if (isInFridge(c) || isInFreezer(c)) {                                 // @156 L756
        if (c.getSourceGrid() != null && c.getSourceGrid().haveElectricity())
            dH *= getFridgeFactor();                                            // @172–@197 L757/L760
        else if (SandboxOptions.instance.getElecShutModifier() > -1
                 && lastAged < getElecShutModifier()*24) {                      // @202 L761
            float cut = Math.min(getElecShutModifier()*24, nowH);               // @230 L762
            dH = (cut - lastAged) * getFridgeFactor();                          // @246 L763
            if (nowH > getElecShutModifier()*24)                                // @261 L765
                dH += nowH - getElecShutModifier()*24;                          // @276 L766
        }
    }

    boolean wasFresh  = !burnt && offAge    < 1_000_000_000 && age <  offAge;   // @294 L771
    boolean wasRotten = !burnt && offAgeMax < 1_000_000_000 && age >= offAgeMax;// @331 L772

    age += (dH * getFoodRotSpeed()) / 24.0;                                     // @368 L774   <-- THE FORMULA
    lastAged = nowH;                                                            // @391 L775

    boolean isFreshNow  = …same test…;                                          // @396 L777
    boolean isRottenNow = …same test…;                                          // @433 L778
    if (!GameServer.server && (wasFresh != isFreshNow || wasRotten != isRottenNow))
        LuaEventManager.triggerEvent("OnContainerUpdate", this);                // @470 L779-780
    if (sync && GameServer.server) GameServer.sendItemStats(this);              // @497 L782-783
}
```

`burnt` short-circuits both transition tests, so a burnt item never fires `OnContainerUpdate`
for rot — but its `age` still advances.

### Every constant

| Constant | Value | Source |
|---|---|---|
| never-ages sentinel | `1 000 000 000` (`offAge`/`offAgeMax` default) | `Food.canAge @4 L2577`, `updateRotting @5 L654`, `shouldUpdateInWorld @11 L1318` |
| age unit conversion | `age += hours × rotSpeed / 24` | `Food.updateAge(Z) @382 L774` |
| frozen multiplier | **× 0.0** | `Food.updateAge(Z) @147–@151 L755` |
| fridge/freezer multiplier (powered) | `getFridgeFactor()` | `Food.updateAge(Z) @189–@197 L760` |
| `getFridgeFactor()` | sandbox `FridgeFactor` (enum 1–6, **default 3**): 1→`0.4`, 2→`0.3`, **3→`0.2`**, 4→`0.1`, 5→`0.03`, 6→`0.0` | `Food.getFridgeFactor @9 tableswitch L710–L716`; option decl `SandboxOptions.<init> @1113 L134` |
| `getFoodRotSpeed()` | sandbox `FoodRotSpeed` (enum 1–5, **default 3**): 1→`1.7`, 2→`1.4`, **3→`1.0`**, 4→`0.7`, 5→`0.4` | `Food.getFoodRotSpeed @9 tableswitch L721–L726`; option decl `SandboxOptions.<init> @1094 L133` |
| electricity-shutoff window | `elecShutModifier × 24` hours | `Food.updateAge(Z) @202–@292 L761–L766` |
| heat lerp window | `1/3` hour (20 game-min) | `Food.updateAge(Z) @71 L745` |
| sync rate limit | `UpdateLimit(1000)` ms | `Food.<clinit> @4 L72` |
| rotten-food removal | `daysForRottenFoodRemoval`, default **−1** (min −1, max 2 147 483 647) | `SandboxOptions.<init> @1570–@1580 L168`; **every shipped preset sets −1** (`media/lua/shared/Sandbox/{Apocalypse,Extinction,Outbreak,Rising}.lua:96`, `SixMonthsLater.lua:71`) |

All four shipped presets use `FoodRotSpeed = 3` and `FridgeFactor = 3` except `Outbreak.lua:66`
(`FridgeFactor = 4` → `0.1`). So at default settings **a powered fridge ages food at 0.2× and a
freezer, once the item is actually frozen, at 0.0×.**

### Fridge vs freezer — the container tests

```java
boolean isInFridge (ItemContainer c) { return c != null && c.isFridge();  }   // Food @0–@16 L2719
boolean isInFreezer(ItemContainer c) { return c != null && c.isFreezer(); }   // Food @0–@16 L2723
```

`ItemContainer.isFreezer() @0–@55 L4057–L4061`: type equals `ContainerType.FREEZER.toString()`
or the literal `"freezer"`. `ItemContainer.isFridge() @0–@101 L4065–L4081`: **returns false if
`isFreezer()`** (`@21–@29 L4069-L4070`), then type equals `ContainerType.FRIDGE.toString()` or
`"fridge"`, else the parent `IsoObject` has property `IsoPropertyType.IS_FRIDGE`.

`ItemContainer.getTemprature() @0–@225 L2681–L2707` — the only source of `Food.heat`:

| condition | temperature |
|---|---|
| `customTemperature != 0` | that value |
| powered fridge or freezer | `0.2` |
| powered stove or `type == "microwave"` with an `IsoStove` parent | `IsoStove.getCurrentTemperature()` = `(currentTemperature + 100) / 100` |
| `IsoBarbecue` parent | `IsoBarbecue.getTemperature()` |
| `IsoFireplace` parent | `IsoFireplace.getTemperature()` |
| unpowered fridge/freezer, still inside the elec-shutoff window, and time-of-day < 13:00 | `Lerp(0.2, 1, (timeOfDay − 7) / 6)` |
| everything else | `1.0` |

### Freezing — `Food.updateFreezing(ItemContainer, float nowH)`

```java
lastFrozenUpdate = GameTime.checkHours(lastFrozenUpdate, nowH);      // @0  L846
if (nowH <= lastFrozenUpdate) return;                                // @12 L847
float dH = nowH - lastFrozenUpdate;                                  // @21 L848
// two local constants, never read from script or sandbox:
final float FREEZE_HOURS = 4.0f;                                     // @28 L849
final float THAW_HOURS   = 1.5f;                                     // @33 L850
if (isFreezing()) {                                                  // @38 L851
    setFertilized(false);                                            // @45 L852
    setFreezingTime(getFreezingTime() + dH/4.0f*100.0f);             // @50 L853   → 4 h to freeze
}
if (isThawing()) {                                                   // @68 L855
    float t = 1.5f;                                                  // @75 L856
    if (isInFridge(c) && c.isPowered()) t *= 2.0f;                   // @80 L857–859  → 3 h in a fridge
    if (c != null && c.getTemprature() > 1.0f) t /= 6.0f;            // @101 L862-863 → 0.25 h when hot
    setFreezingTime(getFreezingTime() - dH/t*100.0f);                // @122 L865
}
lastFrozenUpdate = nowH;                                             // @139 L867
```

`freezingTime` is a **0–100 percentage**, and `setFreezingTime` is what actually flips `frozen`:

```java
void setFreezingTime(float v) {                    // Food @0 L2159
    if (v >= 100f) { setFrozen(true);  v = 100f; } // @0–@17  L2160-L2161
    else if (v <= 0f) { v = 0f; setFrozen(false); }// @20–@32 L2162–L2164
    freezingTime = v;                              // @33 L2166
}
boolean isFreezing() { return canBeFrozen() && freezingTime < 100 && isInFreezer(c) && c.isPowered(); }  // @0–@37 L2190–L2194
boolean isThawing()  { return canBeFrozen() && freezingTime > 0 && (!isInFreezer(c) || !c.isPowered()); }// @0–@45 L2198–L2205
void freeze()        { setFreezingTime(100f); }    // @0–@7 L2170-L2171
```

So `setFrozen(true)` **alone is as inert as `setRotten(true)` is for rot in one direction**: it
sets the flag (and the ×0 age rate follows immediately, because `updateAge` reads `isFrozen()`),
but the very next `updateFreezing` tick sees `isThawing()` (freezingTime still 0) and will drive
`setFreezingTime(negative)` → `setFrozen(false)`. **Use `freeze()`** (or `setFreezingTime(100)`)
in experiments, not `setFrozen(true)`.

### Spawn-time age — `Food.setAutoAge()`

Called from exactly one place: `ItemPickerJava.doRollItemInternal` (loot generation).

```java
ItemContainer c = getOutermostContainer();                                     // @0  L790
float days = (float) GameTime.getInstance().getWorldAgeHours() / 24f;          // @5  L791
days += (SandboxOptions.instance.timeSinceApo.getValue() - 1) * 30;            // @17 L794   30 days per step
float eff = days;                                                              // @35 L796
if (isInFridge(c) || isInFreezer(c)) {                                         // @37 L798
    int esm = SandboxOptions.instance.elecShutModifier.getValue();             // @53 L799
    if (esm > -1) {                                                            // @64 L800
        float cut = Math.min(esm, days);                                       // @70 L801
        if (isInFridge(c) || !canBeFrozen()) {                                 // @79 L803
            eff = eff - cut + cut * getFridgeFactor();                         // @94–@107 L804-805
        } else {                       // freezer AND freezable
            float acc = cut, ft = 100f;                                        // @112–@119 L808-809
            if (days > cut) {
                float extraH = (days - cut) * 24f;                             // @128 L812
                float f9 = 1440f / GameTime.getInstance().getMinutesPerDay() * 60f * 5f;  // @138 L814
                ft -= 0.0096f * f9 * extraH;                                   // @163 L816   (0.0096 = @158 L815)
                if (ft > 0) acc += extraH / 24f;                               // @177–@193 L817–L819
                else { acc += (100f / (0.0096f * f9)) / 24f; ft = 0f; }        // @198–@221 L822–L824
            }
            eff = eff - acc + acc * 0.0f;                                      // @224–@235 L828-829   frozen time counts 0
            setFreezingTime(ft);                                               // @236 L831
        }
    }
}
age = eff * getFoodRotSpeed();                                                 // @242 L836
lastAged = (float) GameTime.getInstance().getWorldAgeHours();                  // @252 L837
lastFrozenUpdate = lastAged;                                                   // @263 L838
if (c != null) setHeat(c.getTemprature());                                     // @271 L840-841
```

`ItemPickerJava.rotItem(item) @0–@124 L2246–L2263` runs separately at spawn on some loot rolls:

```java
Item script = item.getScriptItem();
if (item instanceof Food f) {
    if (script.cannedFood && script.cantEat) return;          // @17–@28   sealed cans are exempt
    if (f.getOffAgeMax() >= 1_000_000_000) return;            // @31–@38
    if (f.isRotten()) return;                                 // @41–@48 L2248-L2249
    if (Rand.Next(100) < 75) {                                // @49–@56 L2252
        f.setRotten(true);                                    // @59 L2253   (inert)
        f.setAge(f.getOffAgeMax());                           // @64 L2254   (what actually rots it)
    } else if (f.isFresh() && Rand.Next(100) < 95) {
        f.setAge(f.getOffAge());                              // @93 L2257   make it stale
    }
}
```

### Removal / replacement — `Food.updateRotting(ItemContainer)`

```java
if (offAgeMax == 1_000_000_000) return;                                      // @0–@12  L654-655
if (GameClient.client) return;                                               // @13–@19 L658-659   MP CLIENT NEVER ROTS
if (replaceOnRotten != null && !replaceOnRotten.isEmpty()) {                 // @20 L662
    updateAge();                                                             // @37 L663   <-- ages every tick
    if (isRotten()) {
        InventoryItem n = InventoryItemFactory.CreateItem(module + "." + replaceOnRotten, this);  // @48–@65 L665
        if (n == null) { warn; destroyThisItem(); return; }                  // @66–@93 L666–L669
        n.setAge(getAge()); n.copyConditionStatesFrom(this);                 // @94–@106 L671-672
        …place in world square or container, server → sendAddItemToContainer…// @107–@221 L674–L690
        destroyThisItem();                                                   // @222 L693
    }
} else if (SandboxOptions.instance.daysForRottenFoodRemoval.getValue() >= 0) {// @227–@236 L698
    if (container != null && container.parent instanceof IsoCompost) return;  // @239–@253 L699-700
    updateAge(false);                                                         // @254 L702
    if (getAge() > getOffAgeMax() + daysForRottenFoodRemoval) destroyThisItem();  // @259–@283 L703-704
}
```

### Who drives it

`IsoCell.ProcessItems(Iterator) @28 L2625` calls `InventoryItem.update()` on every entry of
`IsoCell.processItems`, then drops any whose `finishupdate()` returns true (`@35 L2626`). Items
join that list from `ItemContainer.AddItem`, `IsoWorldInventoryObject.update`, and
`Food.updateAge(Z) @119 L748` (the heat-lerp branch re-arms it). Separately,
`IsoGameCharacter.updateInternal() @1911–@1925 L9295-L9296` calls
`recursiveItemUpdater(this.inventory)` for every non-zombie character every tick, which walks the
inventory recursively and calls `InventoryItem.update()` on each item (`recursiveItemUpdater
@44–@54 L9410-L9411`) — **with no side guard**.

The complete list of `Food.updateAge` call sites in the jar (reverse-reference scan of the whole
constant pool):

| caller | guard |
|---|---|
| `Food.update() @44 L370` | `if (GameServer.server)` — and only when `getOutermostContainer() != null` |
| `Food.updateRotting @37 L663` | `ReplaceOnRotten` set (and not `GameClient.client`) |
| `Food.updateRotting @254 L702` | `daysForRottenFoodRemoval >= 0` (and not `GameClient.client`) |
| `Food.OnAddedToContainer @0–@7 L2518-L2519` | `if (GameServer.server)` |
| `Food.OnBeforeRemoveFromContainer @0–@7 L2525-L2526` | `if (GameServer.server)` |
| `IsoCompost.update @255 L106` | compost bin only |
| `ISWorldObjectContextMenuLogic.handleGrabWorldItem` | picking an item off the ground |

`GameServer.server` is written in exactly two places — `GameServer.main(String[])` and
`GameWindow.mainThreadInit @345 L654` (only when the `server` launch arg is `"true"`) — so it is
**true only in a dedicated/host server process**. See Q8 and *Open / uncertain* #1 for what that
implies in single-player.

---

## Q3 — What aging does to hunger and the four nutrients

**Do not re-derive `Eat`.** `docs/vanilla/eating-pipeline.md` ("Every modifier, in one table")
already establishes, Ev C+M:

- `getHungerChange()` (the value that drives the HUNGER stat) applies, in this priority order:
  cooked `×1.3` → burnt `max(|h|/3, 0.01)` → **stale (`offAge ≤ age < offAgeMax`)
  `max(|h|/1.3, 0.01)`** → **rotten (`age ≥ offAgeMax`) `max(|h|/2.2, 0.01)`**
  (`Food.getHungerChange @11–@129 L1686–L1704`).
- `getThirstChange()` has **no rot branch at all** — burnt `/5` beats cooked `/2` and rot does
  nothing (`Food.getThirstChange @0–@28 L1866–L1875`; measured: rotten apple still −0.07).
- **`getCalories/getCarbohydrates/getProteins/getLipids` are bare `getfield` reads with no
  cooked / burnt / rotten / frozen modifier** (`Food.getCalories @0 L2139` and siblings). The
  only nutrition modifier in the game is `Eat`'s `÷5` for **burnt** items. Measured: rotten
  bread delivered its full 532 kcal / 99 g carbs (`exp01-20260910-003929`).
- Rot also moves `getStressChange` (`/2`), `getFoodSicknessChange` (`/2.2`), `getBoredomChange`
  and `getUnhappyChange` (`+20` each), and adds the rot-sickness POISON roll in
  `BodyDamage.JustAteFood @677–@953 L703–L743`. `getEnduranceChange` has a stale branch (`/2`)
  but no rot branch.

**What aging itself writes to the item** — this is the new part, and the list is short. Across
`Food.updateAge(Z)`, `updateFreezing` and `updateRotting`, the *only* item fields written are:

| field | written by |
|---|---|
| `age` | `updateAge(Z) @388 L774` |
| `lastAged` | `updateAge(Z) @32 L741`, `@393 L775` |
| `heat` | `updateAge(Z) @116 L747` / `@137 L751` |
| `freezingTime` (+ `frozen` via its setter) | `updateFreezing @65 L853` / `@135 L865` |
| `lastFrozenUpdate` | `updateFreezing @9 L846`, `@141 L867` |
| `fertilized` → false | `updateFreezing @45–@49 L852` (freezing kills a fertilized egg) |

**Aging never touches `hungChange`, `thirstChange`, `calories`, `carbohydrates`, `proteins`,
`lipids`, `unhappyChange`, `boredomChange` or `stressChange`.** All rot effects are computed at
read time by the `Food` getters. Consequence for the nutrition mod: the stored macros of a food
item are a pure function of its script values and how much of it has been eaten — rot is a *view*,
not a mutation, and a mod that wants rot to cost calories has to change `Eat` or the getters, not
the item.

Two exceptions worth flagging, both from *cooking* rather than aging:
`RemoveNegativeEffectOnCooked` permanently zeroes positive `thirstChange`/`unhappyChange`/
`boredomChange` (`Food.update @578–@626 L451–L459`), and cooked rice/pasta gets its age clock
rewritten to `age=0, offAge=1, offAgeMax=2` (`Food.update @563–@575 L444–L446`).

---

## Q4 — Cooking

### Per-key behaviour

| Key / accessor | What it does |
|---|---|
| `IsCookable` → `InventoryItem.isCookable()Z @0 L2553` | gates the entire cooking block: `if (isCookable && !isFrozen() && heat > 1.6f)` (`Food.update @49–@71 L372-L373`). Set to `false` at `@1147 L517` when a burnt item ignites |
| `MinutesToCook` → `getMinutesToCook()F @0 L2569` | `cookingTime > minutesToCook` ⇒ cook transition (`Food.update @200–@209 L397`) |
| `MinutesToBurn` → `getMinutesToBurn()F @0 L2577` | `cookingTime > minutesToBurn` ⇒ `burnt = true; setCooked(false)` (`Food.update @894–@913 L494–L496`) |
| `CookingTime` → `getCookingTime()F @0 L2561` / `setCookingTime(F) @0 L2565` | the accumulator, in **game minutes of heat**; also serialised in `ItemStatsPacket` |
| `isCooked()Z @0 L2585` / `setCooked(Z) @0 L2589` | `setCooked(true)` **also raises `cookingTime` to `minutesToCook` if it is below** (`@5–@28 L2590-L2591`) — that is why slice 01 found `setCooked` ungated and sticky, even on an `IsCookable = false` item |
| `isBurnt()Z @0 L2596` / `setBurnt(Z) @0 L2600` | symmetric: raises `cookingTime` to `minutesToBurn` (`@5–@28 L2601-L2602`) |
| `ReplaceOnCooked` → `Food.getReplaceOnCooked()List` | on the cook transition **and only if `!isRotten()`**: each name is `container.AddItem(name)`-ed, `copyConditionStatesFrom(this)`, the original is removed from the container and pushed to `IsoCell.addToProcessItemsRemove`, and `Food.update` **returns early** (`@224–@412 L398–L421`). The item is therefore *never* flagged cooked |
| `RemoveNegativeEffectOnCooked` → `isRemoveNegativeEffectOnCooked()Z` | on the cook transition, each of `thirstChange`, `unhappyChange`, `boredomChange` is set to 0 **if `> 0`** (`@578–@626 L451–L459`). Permanent, one-shot, nutrition untouched |
| `RemoveUnhappinessWhenCooked` | read off `getScriptItem().removeUnhappinessWhenCooked`; `setUnhappyChange(0)` on the cook transition (`@418–@432 L424-L425`) |
| `DangerousUncooked` → `isbDangerousUncooked()Z` | no effect in `Food.update`; consumed by `JustAteFood` (slice 01) and by `EvolvedRecipe` (Q5) |
| `BadInMicrowave` → `isBadInMicrowave()Z` | if the container `isMicrowave()`, the cook transition sets `unhappyChange = 5`, `boredomChange = 5`, `cookedInMicrowave = 1` (`@719–@752 L472–L475`); the same is applied to a `ReplaceOnCooked` product (`@319–@356 L406–L409`) |
| `GoodHot` / `BadCold` (heat) | read only by `Food.getUnhappyChange @124–@195 L1645–L1649`: `−2` if `isGoodHot && isCookable && isCooked && heat > 1.3`; `+2` if `isBadCold && isCookable && isCooked && heat < 1.3` (slice 01) |
| `getHeat()F @0 L1787` / `setHeat(F) @0 L1799` | raw `Food.heat`; **1.0 = ambient**, `0.2` = powered fridge/freezer, `(stoveTemp+100)/100` on a stove |
| `getInvHeat()F @0–@32 L1792–L1795` | UI-facing remap: `heat > 1` → `(heat − 1)/2`; else `1 − (heat − 0.2)/0.8` |

### The cooking driver

There is **no separate oven/campfire cooking class**. `zombie/inventory/types/Food.update()` is
the driver; the appliance only supplies `ItemContainer.getTemprature()`.

```java
void Food.update() {                                                            // L359
    calculateTimeMultiplier();                                                  // @0  L359
    if (hasTag(ItemTag.ALREADY_COOKED)) setCooked(true);                        // @4–@16 L361-L362
    updateTemperature();                                                        // @19 L364
    checkEggHatch(null);                                                        // @23 L365
    ItemContainer c = getOutermostContainer();                                  // @29 L367
    if (c != null) {
        if (GameServer.server) updateAge(false);                                // @38–@46 L369-L370

        if (isCookable && !isFrozen()) {                                        // @49–@60 L372
            if (heat <= 1.6f) goto ROT;                                         // @63–@71 L373   <-- HEAT GATE
            setFertilized(false);                                               // @74 L374
            int minute = GameTime.getInstance().getMinutes();                   // @79 L375
            if (minute != lastCookMinute) {                                     // @86 L377   ONE TICK PER GAME MINUTE
                if (GameServer.server) GameServer.sendItemStats(this);          // @94–@101 L378-379
                lastCookMinute = minute;                                        // @104 L381
                float d = heat / 1.5f;                                          // @109 L382
                if (c.getTemprature() <= 1.6f) d *= 0.05f;                      // @118–@134 L384-385  (residual heat)
                cookingTime += d;                                               // @135 L387
                if (shouldPlayCookingSound()) ItemSoundManager.addItem(this);   // @145 L389-390
                if (isTainted && cookingTime > min(minutesToCook, 10f))
                    isTainted = false;                                          // @156–@183 L393-394   boiling purifies
                if (!isCooked() && !burnt
                    && (cookingTime > minutesToCook || cookingTime > minutesToBurn)) {   // @186–@221 L397
                    if (getReplaceOnCooked() != null && !isRotten()) { …replace, return; } // @224–@412 L398–L421
                    setCooked(true);                                            // @413 L423
                    if (getScriptItem().removeUnhappinessWhenCooked) setUnhappyChange(0); // @418 L424-425
                    if (type ∈ {RicePot, PastaPot, RicePan, PastaPan, WaterPotRice,
                                WaterPotPasta, WaterSaucepanRice, WaterSaucepanPasta,
                                RiceBowl, PastaBowl})
                        { setAge(0); setOffAge(1); setOffAgeMax(2); }           // @563–@575 L444–L446
                    if (isRemoveNegativeEffectOnCooked()) { …zero the 3 positives… }      // @578 L451–L459
                    …OnCooked Lua hook…                                         // @627–@718 L462–L467
                    if (isBadInMicrowave() && c.isMicrowave()) { unhappy=5; boredom=5; }  // @719 L472–L475
                    if (chef != null && !hasTag(NO_COOKING_XP) && !isRotten())
                        award 10.0f Cooking XP to chef                          // @755–@891 L478–L487
                }
                if (cookingTime > minutesToBurn) { burnt = true; setCooked(false); }      // @894 L494–L496
                if (GameServer.server) GameServer.sendItemStats(this);          // @916–@923 L499-500
                // --- kitchen fire ---
                if (c.getParent() != null && c.getParent().hasGridPower() && burnt
                    && cookingTime >= 50.0f
                    && cookingTime >= minutesToCook*2 + minutesToBurn/2
                    && Rand.Next(Rand.AdjustForFramerate(200)) == 0) {          // @926–@1004 L503–L509
                    boolean isCampfire = "Campfire".equals(c.getParent().getName())
                                         || c.getParent() instanceof IsoFireplace;        // @1007–@1099 L511–L513
                    if (!isCampfire && c.sourceGrid != null) {
                        IsoFireManager.StartFire(cell, c.sourceGrid, true, 500000);       // @1123–@1144 L516
                        isCookable = false;                                     // @1147 L517
                    }
                }
            }
        } else if (isTainted && heat > 1.6f && !isFrozen()) {                   // @1155–@1177 L523
            // tainted-water boiling for NON-cookable containers
            int minute = GameTime.getInstance().getMinutes();                   // @1180 L524
            if (minute != lastCookMinute) {
                lastCookMinute = minute;                                        // @1195 L526
                float d = 1.0f;                                                 // @1200 L527
                if (c.getTemprature() <= 1.6f) d *= 0.2f;                       // @1202–@1218 L528-529
                cookingTime += d;                                               // @1219 L531
                if (cookingTime > 10.0f) isTainted = false;                     // @1229–@1242 L532-533
                if (GameServer.server) GameServer.sendItemStats(this);          // @1245–@1252 L535-536
            }
        }
    }
ROT:
    updateRotting(c);                                                           // @1255 L543
}
```

**Minute counters and constants**

| Constant | Value | Source |
|---|---|---|
| cooking heat gate | `heat > 1.6f` (item heat) and `container.getTemprature() > 1.6f` for the full rate | `Food.update @67 L373`, `@122 L384` |
| tick granularity | one per distinct `GameTime.getMinutes()` — **one game minute** | `Food.update @86 L377` |
| cook rate | `cookingTime += heat / 1.5f` per game minute | `Food.update @113 L382` |
| residual-heat rate | `× 0.05f` when the *container* is at/below 1.6 (item still hot, appliance off) | `Food.update @130 L385` |
| taint purge (cookable) | `cookingTime > min(minutesToCook, 10.0f)` | `Food.update @171 L393` |
| taint purge (non-cookable) | `+1.0f` per minute (`× 0.2f` residual), threshold `10.0f` | `Food.update @1200/@1214/@1233 L527–L532` |
| fire threshold | `burnt && cookingTime ≥ 50.0f && cookingTime ≥ minutesToCook*2 + minutesToBurn/2` | `Food.update @967/@982–@990 L503–L508` |
| fire roll | `Rand.Next(Rand.AdjustForFramerate(200)) == 0` per minute; fire strength `500000` | `Food.update @995–@1001 L509`, `@1141 L516` |
| cooking XP | `10.0f` Cooking, skipped for `NO_COOKING_XP` or rotten | `Food.update @809/@879 L481/L486` |
| microwave penalty | `unhappyChange = 5.0f`, `boredomChange = 5.0f` | `Food.update @339/@347/@737/@745 L407-408/L473-474` |

`IsoStove` supplies the heat. `IsoStove.getCurrentTemperature()F @0–@12 L443` returns
`(currentTemperature + 100) / 100`, so `heat > 1.6` needs `currentTemperature > 60`. The ramp, in
`IsoStove.update()`:

| state | change per frame |
|---|---|
| activated, `currentTemperature < maxTemperature` | `+ max((maxTemperature − currentTemperature)/700f, 0.05f) × GameTime.getMultiplier()`, clamped to max (`@386–@443 L117–L123`) |
| activated, `currentTemperature > maxTemperature` | `− (currentTemperature − maxTemperature)/1000f × multiplier`, floored at 0 (`@461–@500 L126–L128`) |
| not activated | `− 0.1f × multiplier`, floored at 0 (`@506–@542 L132–L134`) |
| microwave | instant: `currentTemperature = maxTemperature` when on, `0` when off (`@545–@581 L138–L143`) |

`InventoryItem.calculateTimeMultiplier() @0–@71 L1331–L1340` — on the server,
`timeMultiplier = GameTime.getMultiplierFromTimeDelta(clamp(now − lastUpdateMs, 0, 6000) × 0.001f)`;
everywhere else `timeMultiplier = GameTime.getInstance().getMultiplier()`. It feeds
`Food.updateTemperature() @5 L626`, which accumulates `timeMultiplier / 1.6f` and only acts once
the accumulator passes `10.0f` (`@21 L627`), then decays `heat` toward the container temperature
at `0.001f × accumulator` per step with a floor of `max(0.2f, containerTemp)` (`@83–@123 L639–L641`).

---

## Q5 — Evolved recipes

### Script side

`media/scripts/generated/evolvedrecipes.txt` — **62 `evolvedrecipe` blocks**. Loader:
`EvolvedRecipe.Load(String,String)` `@0–@29 L67–L71` (splits on `[{}]`, then `,`) →
`EvolvedRecipe.Load(String,String[])`, which recognises exactly these keys:

| Key | Field | Count in evolvedrecipes.txt |
|---|---|---|
| `BaseItem` | `baseItem` `@78–@89` | 62 |
| `Name` | `displayName` (via `Translator.getRecipeName`) + `originalname` `@97–@117` | 62 |
| `ResultItem` | `resultItem` `@125–@136` | 62 |
| `Cookable` | `cookable` `@144–@154` | 44 |
| `MaxItems` | `maxItems` (`Integer.parseInt`) `@162–@176` | 62 |
| `AddIngredientIfCooked` | `addIngredientIfCooked` `@184–@198` | 37 |
| `AddIngredientSound` | `addIngredientSound` `@206–@220` | 11 |
| `CanAddSpicesEmpty` | `canAddSpicesEmpty` `@228–@242` | 42 |
| `IsHidden` | `hidden` `@250–@264` | **0 — loader-only** |
| `AllowFrozenItem` | `allowFrozenItem` `@272–@286` | **0 — loader-only** |
| `Template` | `template` `@294–@305`, `@348` | 62 |
| `MinimumWater` | `minimumWater` (`Float.parseFloat`) `@313–@330` | 20 |

An item joins a recipe's ingredient list through its own `EvolvedRecipe = <Name>:<use>[|Cooked]`
key. `Item.OnScriptsLoaded(ScriptLoadMode) @0–@234 L3029–L3047` walks `Item.itemRecipeMap` and
puts `itemsList[itemName] = ItemRecipe{use, cooked}` on (a) the recipe whose **name** equals the
key, and (b) **every recipe whose `Template` equals the key**. If neither matches it logs an error
and throws `InvalidParameterException` (`@179–@210 L3045–L3047`). That is how `Salad:10` on a
carrot reaches `Salad`, `SaladClay`, … which all declare `Template = Salad`.

### The summation — `EvolvedRecipe.addItem(base, ingredient, chef)`

`zombie/scripting/objects/EvolvedRecipe.addItem(…)L… @0–@1928 L265–L487`. Returns the (possibly
replaced) base item.

```java
int  cookLvl   = chef.getPerkLevel(Perks.Cooking);            // @0  L265
ItemContainer srcC = ingredient.getContainer();               // @9  L266

// ---------- PHASE A: first ingredient turns the BASE into the RESULT ----------
if (!isResultItem(base)) {                                    // @15 L269
    Food baseFood = (base instanceof Food) ? (Food) base : null;                // @23 L270
    InventoryItem result = InventoryItemFactory.CreateItem(resultItem);         // @37 L271
    if (result == null) goto PHASE_B;                                           // @46 L273
    if (base tint != (1,1,1)) copy ColorRed/Green/Blue to result;               // @51–@107 L274–L277
    if (base.getModelIndex() != -1) result.setModelIndex(base.getModelIndex()); // @108–@122 L279-280
    if (base instanceof HandWeapon) { result.setConditionFrom(base);
        result.getModData()[base.getType()] = condition/conditionMax; }         // @125–@170 L282–L284
    InventoryItem old = base; base = result;                                    // @171–@176 L287-288

    if (base instanceof Food rf) {
        rf.setCalories(0); rf.setCarbohydrates(0);
        rf.setProteins(0); rf.setLipids(0);                                     // @190–@211 L291–L294  ZERO START
        base.setIsCookable(this.cookable);                                      // @214 L296          <-- `Cookable`
        if (baseFood != null) { rf.setHungChange(baseFood.getHungChange());
                                rf.setBaseHunger(baseFood.getBaseHunger()); }   // @222–@250 L298-299
        else                  { rf.setHungChange(0); rf.setBaseHunger(0); }     // @256–@265 L301-302

        // proportional age carry-over
        if (old instanceof Food && old.getOffAgeMax() != 1e9
                                && base.getOffAgeMax() != 1e9) {                // @268–@294 L304
            float ratio = old.getAge() / old.getOffAgeMax();                    // @297 L305
            base.setAge(base.getOffAgeMax() * ratio);                           // @311 L306
        }
        if (baseFood != null) {          // the pot's OWN food values seed the dish
            rf.setTainted(baseFood.isTainted());                                // @338 L309
            rf.setCalories(baseFood.getCalories());                             // @348 L310
            rf.setProteins(baseFood.getProteins());                             // @358 L311
            rf.setLipids(baseFood.getLipids());                                 // @368 L312
            rf.setCarbohydrates(baseFood.getCarbohydrates());                   // @378 L313
            rf.setThirstChange(baseFood.getThirstChange());                     // @388 L314
        }
    }
    base.setUnhappyChange(0); base.setBoredomChange(0);                         // @398–@405 L318-319
    base.setCondition(old.getCondition(), false);
    base.setFavorite(old.isFavorite());                                         // @408–@426 L320-321
    chef.getInventory().Remove(old); chef.getInventory().AddItem(base);         // @429–@446 L323-324
    if (GameServer.server) GameServer.sendReplaceItemInContainer(inv, old, base);// @447–@460 L325-326
}

// ---------- PHASE B: merge the ingredient ----------
ItemRecipe ir = itemsList.get(ingredient.getType());                            // @463 L331
if (ir == null || ir.use <= -1) goto TAIL;                                      // @476–@502 L331

if (ingredient instanceof Food ing) {                                           // @505 L332
    float hunger = ir.use / 100.0f;                                             // @518 L333   script `Name:use`
    Food res = (Food) base;                                                     // @547 L334
    boolean herbalTea = res.hasTag(HERBAL_TEA) && ing.hasTag(HERBAL_TEA);       // @553 L335

    // ---- SPICE: no hunger, no macros, returns immediately ----
    if (ing.isSpice() && base instanceof Food) {                                // @582 L336
        if (herbalTea) {                                                        // @610 L339
            res.foodSicknessChange += ing.foodSicknessChange;                   // @615 L340
            res.painReduction      += ing.painReduction;                        // @631 L341
            res.fluReduction       += ing.fluReduction;                         // @647 L342
            res.stressChange       += ing.stressChange;                         // @663 L343
            res.reduceInfectionPower += ing.reduceInfectionPower;               // @679 L344
            if (ing.enduranceChange > 0) res.enduranceChange += ing.enduranceChange;  // @695 L346-347
            if (res.foodSicknessChange > 12) res.setFoodSicknessChange(12);     // @721 L350-351
            if (ing.hasTag(BOOSTS_FLU_RECOVERY)) res.fluReduction += 5;         // @738 L353-354
        }
        useSpice(ing, (Food) base, hunger, cookLvl, chef);                      // @761 L358
        return base;                                                            // @774 L359
    }

    // ---- rotten ingredient: only cooks 7+ can use one, and it contributes almost nothing ----
    boolean partial = false;                                                    // @776 L361
    if (ing.isRotten()) {                                                       // @779 L363
        if (cookLvl == 7 || cookLvl == 8) hunger = |0.05 * ing.getBaseHunger()|;// @800–@855 L366-367
        else if (cookLvl == 9 || cookLvl == 10) hunger = |0.10 * ing.getBaseHunger()|; // @860–@915 L368-369
        partial = true;                                                         // @917 L371
    }                                                                           // (DECIMAL_FORMAT, HALF_EVEN)

    // ---- a part-eaten ingredient cannot give more than it has left ----
    if (|ing.getHungerChange()| < hunger) {                                     // @920 L373
        hunger = |DECIMAL_FORMAT(ing.getHungerChange())|;   // RoundingMode.DOWN // @934–@972 L374–L376
        partial = true;                                                         // @974 L377
    }

    if (base instanceof Food) {
        res.setHungChange (res.getHungChange()  - hunger);                      // @990 L380
        res.setBaseHunger (res.getBaseHunger()  - hunger);                      // @1003 L381
        if (ing.isbDangerousUncooked() && !ing.isCooked() && !ing.isBurnt())
            res.setbDangerousUncooked(true);                                    // @1016–@1043 L383-384

        // duplicate-ingredient / over-stuffing penalty
        int dupes = count(base.extraItems == ingredient.getFullType());         // @1046–@1099 L388–L392
        if (base.extraItems.size() - 2 > cookLvl)                               // @1102 L398
            dupes += (base.extraItems.size() - 2) - cookLvl * 3;                // @1123 L399

        float hungerAfterSkill = hunger - (3f * cookLvl / 100f) * hunger;       // @1142 L401   3 %/level LESS
        float share = min(|hungerAfterSkill / ing.getHungChange()|, 1f);        // @1159–@1180 L402–L404

        base.setUnhappyChange(res.getUnhappyChangeUnmodified() - (5 - dupes*5));// @1182 L406
        if (base.getUnhappyChange() > 25f) base.setUnhappyChange(25f);          // @1199 L408-409

        float skillBonus = 1f + cookLvl / 15f;                                  // @1217 L411   +6.67 %/level MORE

        // ===== THE NUTRITION SUMMATION =====
        res.setCalories     (res.getCalories()      + ing.getCalories()      * skillBonus * share);  // @1228 L412
        res.setProteins     (res.getProteins()      + ing.getProteins()      * skillBonus * share);  // @1250 L413
        res.setCarbohydrates(res.getCarbohydrates() + ing.getCarbohydrates() * skillBonus * share);  // @1272 L414
        res.setLipids       (res.getLipids()        + ing.getLipids()        * skillBonus * share);  // @1294 L415

        float thirst = ing.getThirstChangeUnmodified() * skillBonus * share;    // @1316 L416
        if (!ing.hasTag(DRIED_FOOD))
            res.setThirstChange(res.getThirstChangeUnmodified() + thirst);      // @1329–@1350 L417-418

        if (ing.isCooked()) hungerAfterSkill /= 1.3;                            // @1353–@1369 L420-421

        // ---- what is left of the ingredient ----
        ing.setHungChange (ing.getHungChange()  + hungerAfterSkill);            // @1371 L424
        ing.setBaseHunger (ing.getBaseHunger()  + hungerAfterSkill);            // @1384 L425
        ing.setThirstChange(ing.getThirstChange() - thirst);                    // @1397 L426
        ing.setUnhappyChange(ing.getUnhappyChange() - ing.getUnhappyChange()*share);  // @1410 L427
        ing.setCalories     (ing.getCalories()      - ing.getCalories()      * share); // @1429 L428
        ing.setProteins     (ing.getProteins()      - ing.getProteins()      * share); // @1448 L429
        ing.setCarbohydrates(ing.getCarbohydrates() - ing.getCarbohydrates() * share); // @1467 L430
        ing.setLipids       (ing.getLipids()        - ing.getLipids()        * share); // @1486 L431

        if (res.hasTag(ALCOHOLIC_BEVERAGE) && ing.isAlcoholic()) res.setAlcoholic(true);  // @1505 L432-433
        if (herbalTea) { …the same medicinal sums as the spice branch… }        // @1530–@1652 L436–L447

        if (ing.getHungerChange() > -0.02 || partial) ingredient.UseAndSync();  // @1655–@1674 L450-451
        if (ing.getFatigueChange() < 0) {                                       // @1677 L454
            base.setFatigueChange(ing.getFatigueChange() * share);              // @1687 L455
            ing.setFatigueChange(f - f * share);                                // @1699 L456
        }
    }
} else if (ingredient.getScriptItem().isSpice() && base instanceof Food) {      // @1721 L459
    useSpice(ingredient, (Food) base, 1, cookLvl, chef); return base;           // @1744–@1756 L460-461
} else ingredient.UseAndSync();                                                 // @1757 L463

TAIL:
base.addExtraItem(ingredient.getFullType());                                    // @1761 L465
if (GameServer.server)                                                          // @1769 L466
    INetworkPacket.send(ItemStats, owner, {base.getContainer(), base})          // @1788–@1819 L468
    or INetworkPacket.sendToRelative(ItemStats, chef.x, chef.y, {container, this});  // @1822–@1848 L470
if (ingredient instanceof Food f && f.getPoisonPower() > 0)
    addPoison(ingredient, base, chef, srcC);                                    // @1851–@1878 L475-476
checkUniqueRecipe(base);                                                        // @1881 L479
award 3.0f Cooking XP;                                                          // @1886–@1924 L481–L484
return base;                                                                    // @1927 L487
```

**Net effect on nutrition.** The dish's macros are `Σ over ingredients (ingredientMacro ×
(1 + cookLvl/15) × share)`, where `share = min(|hunger×(1 − 0.03·cookLvl) / ing.hungChange|, 1)`.
Cooking skill therefore **inflates** the dish's calories twice over: `skillBonus` scales the
transfer up, and because the same amount of hunger is bought for less of the ingredient
(`hungerAfterSkill` shrinks by 3 %/level), the ingredient survives longer. A level-10 cook moves
`1.667 ×` the macros per unit of hunger a level-0 cook does. **This is the single largest
nutrition-side lever in the vanilla game and the nutrition mod must decide whether to keep it.**

> **Correction (measured, `exp02-20260910-030433`):** the `1.667 ×` in the sentence above is wrong —
> it is the **dish-gain / ingredient-loss** ratio (calorie creation), not the dish-size factor.
> Macros per unit of *dish* hunger rise only **`1.1667 ×`** at Cooking 10 (Salad: 25.0 → 29.1667 kcal
> for the same −0.11 hunger), because `skillBonus` is cancelled by the `(1 − 0.03·lvl)` shrink inside
> `share`. See `docs/vanilla/food-item-model.md` § Evolved recipes.

The `*_UNMODIFIED` getters are used for thirst and unhappiness (`getThirstChangeUnmodified`,
`getUnhappyChangeUnmodified`) so cooked/rotten multipliers are not baked into the dish — but the
rotten *discount* is applied explicitly through `hunger`, and the four macro getters are already
unmodified by state (Q3), so **a rotten ingredient contributes its full calories** scaled only by
`share` — and `share` collapses to ~5–10 % of `baseHunger` for a rotten item, so in practice rot
costs the dish most of its nutrition through the `share` term, not through the macro values.

### Gating — which ingredients the menu offers

`EvolvedRecipe.getItemsCanBeUse(chef, base, containerList) @0–… L161–…`:

- `!base.haveExtraItems() && getMinimumWater() > 0 && !hasMinimumWater(base)` → **empty list**
  (`@30–@56 L167-168`).
- `!base.haveExtraItems() && getMinimumWater() == 0 && base.getFluidContainer() != null &&
  !fluidContainer.isEmpty()` → **empty list** (`@57–@92 L170–L175`) — a dry recipe refuses a base
  that already holds fluid.
- `hasMinimumWater(item) @0–@43 L658–L669`: the base must have a `FluidContainer`, it must be
  `isAllCategory(FluidCategory.Water)`, and `getFilledRatio() >= getMinimumWater()`.

`EvolvedRecipe.checkItemCanBeUse(…)` per candidate:

| gate | source |
|---|---|
| `itemsList.get(type).use == -1` → not usable | `@70–@77 L218` |
| spice + `isResultItem(base)` → usable iff `!isSpiceAdded(base, item)` (once each) | `@88–@111 L220-221` |
| spice + base not yet the result → usable iff `canAddSpicesEmpty` | `@116–@124 L222-223` |
| **non-spice: usable only while `!base.haveExtraItems() \|\| base.extraItems.size() < maxItems`** | `@161–@179 L230` |
| burnt ingredient → never usable | `@126–@137 L225-226`, `@182–@193 L231-232` |
| rotten ingredient → usable only at **Cooking ≥ 7** | `@140–@158 L227-228`, `@196–@212 L235-236` |
| frozen ingredient → not usable unless `allowFrozenItem` | `@214–@230 L239-240` |
| `DangerousUncooked` + not cooked + the *result* item is not cookable → rejected | `@232–@258 L243` |

`needToBeCooked(item) @0–@55 L153–L157` compares the ingredient's `ItemRecipe.cooked` flag (the
`|Cooked` suffix on the item's `EvolvedRecipe` key) against `isCooked()`/`isBurnt()`.

### What cooking the result changes

Nothing special — the dish is an ordinary `Food` whose `isCookable` was set from the recipe's
`Cookable` key (`addItem @214 L296`), so it goes through the same `Food.update` cooking block
(Q4): `MinutesToCook`/`MinutesToBurn` come from the **result item's own script block**, and the
`RicePot`/`PastaPot`/… type list resets `age=0, offAge=1, offAgeMax=2` on the cook transition.
`ISAddItemInRecipe.checkTemperature` averages the heats when an ingredient is added
(`media/lua/shared/TimedActions/ISAddItemInRecipe.lua:90–95`), so adding hot food pre-heats a dish.

### Lua entry points

| Site | What it does |
|---|---|
| `media/lua/client/ISUI/ISInventoryPaneContextMenu.lua:332` | `tests.evorecipe = RecipeManager.getEvolvedRecipe(testItem, playerObj, containerList, true)` — the menu probe |
| `…:287–288` | `getEvolvedRecipes():get(i)` — full recipe enumeration for the "no recipes" test |
| `…:4238` `ISInventoryPaneContextMenu.doEvorecipeMenu(context, items, player, evorecipe, baseItem, containerList)` | builds the submenu; calls `evorecipe2:getItemsCanBeUse(player, baseItem, containerList)` (`:4241`), groups by `FoodType` (`:4245`), labels each entry with `getRealEvolvedItemUse(evoItem, evorecipe2, cookingLvl)` (`:4279`) |
| `…:4266` and `…:4297` | `subMenuRecipe:addOption(…, ISInventoryPaneContextMenu.onAddItemInEvoRecipe, baseItem, item, player)` |
| `…:2372–2390` `onAddItemInEvoRecipe(recipe, baseItem, usedItem, player)` | transfers both items into the player's inventory if needed, sets `setChef(username)` on each `Food`, then `ISTimedActionQueue.add(ISAddItemInRecipe:new(playerObj, recipe, baseItem, usedItem))` (`:2389`) |
| `media/lua/shared/TimedActions/ISAddItemInRecipe.lua:70` | **`self.baseItem = self.recipe:addItem(self.baseItem, self.usedItem, self.character)`** — the Lua→Java bridge, inside `:complete()` |
| `…:72` / `:78` | `ISAddItemInRecipe.checkName(baseItem, recipe)` then `checkTemperature(baseItem, usedItem, recipe)` |
| `…:80–85` | `if isServer() then sendItemStats(self.baseItem); if usedItem:getContainer() then sendItemStats(self.usedItem) end end` |
| `…:10–19` `isValidStart()` | `isServer()` → always true; on a client, `inventory:containsID(baseItem:getID()) and recipe:isItemUsableInRecipe(character, baseItem, usedItem:getID())` |
| `…:1–3` | `local max_total = 3; local max_base = max_total` — name-generation limits, not ingredient limits |

`SandboxVars.EnablePoisoning` gates poisoning in the menu: `== 2` disables it entirely, `== 3`
disables it for `Base.Bleach` only (`ISInventoryPaneContextMenu.lua:4270`, `:4288`).

---

## Q6 — Packaged, canned, ReplaceOnUse

### `Packaged`

Parsed at `Item.DoParam @9071–@9094 L2743` (`v.trim().equalsIgnoreCase("true")`), copied to the
instance at `Item.InstanceItem @781–@787 L1582`, readable as `Food.isPackaged()Z @0 L2147`.
A whole-jar reverse-reference scan finds **no Java caller of `isPackaged()`**, and `grep -rni
packaged media/lua` finds no vanilla Lua reader either. It is a pure marker flag — mods and the
script generators use it; the runtime does not. 129 food blocks and 2 drainables set it.

### `CannedFood`

Parsed at `Item.DoParam @972 L2065` (`Boolean.parseBoolean`) into `Item.cannedFood`. There is
**no getter on `Item`** and it is **not copied into the `Food` instance** by `InstanceItem`. It is
nevertheless read, always through `item.getScriptItem()`:

| reader | effect |
|---|---|
| `InventoryItem.getStringItemType() @38–@47 L3984-L3985` | returns `"CannedFood"` instead of `"Food"` for the item-type string |
| `ItemPickerJava.getLootType(Item)` | `"CannedFood"` loot type → the `cannedFoodLootModifier` derived from sandbox `CannedFoodLootNew` |
| `ItemPickerJava.rotItem(InventoryItem) @17–@28 L2247` | **`if (script.cannedFood && script.cantEat) return;`** — a sealed can is exempt from the 75 % spawn-rot roll |
| `ItemPickerJava.trashItem` / `trashItemLooted` / `trashItemRats` / `wearDownItem` | same script flag, spawn-time damage exemptions |

**Do canned items have `DaysFresh`?** Split cleanly, and the split is the mechanic:

| group | count | `DaysFresh` |
|---|---|---|
| sealed cans (`CannedFood = true`, `CantEat = true`, `Packaged = true`, `OpeningRecipe = …`) — `CannedBolognese`, `TinnedBeans`, `MysteryCan`, `DentedCan`, `Dogfood`, `WaterRationCan`, … | **22** | **absent** ⇒ `offAge`/`offAgeMax` stay at `1 000 000 000` ⇒ `canAge()` false ⇒ **never rots, never removed, `updateRotting` returns at `@12 L655`** |
| opened variants (`*Open`, `OpenBeans`) — e.g. `CannedBologneseOpen` (`food.txt:3644`) | **19** | **present** — `DaysFresh = 3`, `DaysTotallyRotten = 5`, plus `HungerChange`, `EvolvedRecipe`, `ReplaceOnUse = Base.TinCanEmpty`, `IsCookable` |

Of 129 `Packaged = true` blocks, 52 carry `DaysFresh` and 75 do not.

Home canning is a *different* mechanic entirely: `OnCooked = RecipeCodeOnCooked.cannedFood`
(89 blocks in `food.txt`) →

```java
void RecipeCodeOnCooked.cannedFood(Food f) {          // L11–L15
    float ratio = f.getAge() / f.getOffAgeMax();      // @0  L11
    f.setOffAgeMax(1560);                             // @11 L12   ~4.3 years
    f.setOffAge(730);                                 // @18 L13   ~2 years
    f.setAge(f.getOffAgeMax() * ratio);               // @25 L14   preserve the fraction
}
```

### `ReplaceOnUse`

`Item.replaceOnUse` `@3724 L2319`, copied to the instance at `InstanceItem @657`. Two consumers
that matter here: `Eat`'s custom-weight branch uses the replacement item's actual weight as the
weight floor (`IsoGameCharacter.Eat @884–@960 L5832–L5839`, slice 01), and the Lua context menu /
`ISDumpContentsAction` build the leftover container (`ISInventoryPaneContextMenu.lua:4079`,
`:4093-4094`; `ISDumpContentsAction.lua:70-71`, `:85`).

---

## Q7 — Poison

Eat-time effects are already documented — see the `poison power`, `tainted`, `rot sickness roll`
and `dangerous uncooked` rows of `docs/vanilla/eating-pipeline.md`
(`BodyDamage.JustAteFood @0–@953 L587–L743`). What is new here is how poison *rides on the item*.

Four loader keys, all recognised by `Item.DoParam`:

| Key | Parse | Item field | In `food.txt` / `drainable.txt` |
|---|---|---|---|
| `Poison` | bool | `Item.poison` `@388–@405` → `Food.poison` (`InstanceItem @501–@504`) | **0 occurrences** |
| `PoisonDetectionLevel` | int | `Item.poisonDetectionLevel` `@439–@453` → `Food.poisonDetectionLevel` (`InstanceItem @510`) | **0 occurrences** |
| `PoisonPower` | int | `Item.poisonPower` `@463–@477 L2011` → `Food.poisonPower` (`InstanceItem @531`) | 4 food blocks |
| `UseForPoison` | int | `Item.useForPoison` `@487–@501` → `Food.useForPoison` | **0 occurrences** |

Reader status (whole-jar reverse-reference scan):

- `Food.isPoison()Z @0 L1909` — **no Java caller, no vanilla Lua caller.** Exposed to Kahlua only.
- `Food.getUseForPoison()I` — **no Java caller, no vanilla Lua caller.** Serialised in
  `Food.save` (bit `131072`) and `Food.load`, and nothing else.
- `Food.getPoisonDetectionLevel()I` — read by `IsoGameCharacter.isKnownPoison(InventoryItem)`
  (whether the player can tell), `UsedItemProperties.addInventoryItem` (crafting carry-over),
  `Food.copyPoisonFrom`, `ItemStatsPacket.setData`, `EvolvedRecipe.addPoison`, and
  `media/lua/client/Foraging/ISForageIcon.lua:25`.
- `Food.getPoisonLevelForRecipe()I @0 L1922` — read only by `EvolvedRecipe.getItemsCanBeUse`.
- `Food.getPoisonPower()I` — `JustAteFood`, `EvolvedRecipe.addItem @1866 L475`, `ItemStatsPacket`.

Poisoning a dish — `EvolvedRecipe.addPoison(ingredient, result, chef, container) @0–… L526–…`:

```java
if (result.getPoisonDetectionLevel() == -1) result.setPoisonDetectionLevel(0);   // @19–@31 L528-529
result.poisonDetectionLevel += ingredient.poisonDetectionLevel;                  // @34–@47 L531
if (result.poisonDetectionLevel > 10) result.setPoisonDetectionLevel(10);        // @50–@64 L532-533
int p = ingredient.getPoisonPower();                                             // @67 L535
result.setPoisonPower(result.getPoisonPower() + p);                              // @84 L538
ingredient.setPoisonPower(ingredient.getPoisonPower() - p);                      // @97 L539   drained fully
result.getModData()["addedPoisonBy"] = chef.getFullName();                       // @110 L541
LoggerManager.getLogger("user").write("Char %s poisoned item %s with power %d"); // @127–@177 L543–L546
if (GameServer.server) INetworkPacket.send(ItemStats, …);                        // @180–… L548–L552
```

So `PoisonDetectionLevel` is capped at **10** and accumulates; `PoisonPower` transfers whole and
zeroes the source. `SandboxVars.EnablePoisoning` gates the UI path only
(`ISInventoryPaneContextMenu.lua:4270`, `:4288`).

---

## Q8 — MP inputs

### Which side ages items

| side | `GameServer.server` | `GameClient.client` | ages food? |
|---|---|---|---|
| dedicated / host server | true | false | **yes** — `Food.update @38–@46 L369-370` calls `updateAge(false)` every tick for any item whose `getOutermostContainer() != null`; plus `OnAddedToContainer @0–@7 L2518-2519` and `OnBeforeRemoveFromContainer @0–@7 L2525-2526`, both `if (GameServer.server)` |
| MP client | false | true | **no** — `Food.update` skips the `updateAge` call, and `Food.updateRotting @13–@19 L658-659` returns immediately on `GameClient.client` |
| single-player | false | false | only via `updateRotting`, i.e. only when the item has `ReplaceOnRotten` (`@37 L663`) or sandbox `DaysForRottenFoodRemoval >= 0` (`@254 L702`) — **and every shipped preset sets it to −1**. See *Open / uncertain* #1 |

The tick itself comes from `IsoGameCharacter.updateInternal() @1918–@1925 L9296` →
`recursiveItemUpdater(inventory)` → `InventoryItem.update()` (no side guard), and from
`IsoCell.ProcessItems @28 L2625` for world/container items.

### How an age change reaches the other side

**It does not — not through any stats packet.** Enumerating `ItemStatsPacket.setData` and
`applyItemStats`, the packet carries exactly:

`condition, uses, usedDelta, fluidContainer(capacity+fluids), itemHeat, frozen, tainted, heat,
cooked, burnt, cookingTime, minutesToCook, minutesToBurn, hungChange, calories, proteins, lipids,
carbohydrates, thirstChange, fluReduction, painReduction, endChange, foodSicknessChange,
stressChange, fatigueChange, unhappyChange, boredomChange, poisonPower, poisonDetectionLevel,
alcoholic, baseHunger, extraItems, spices, actualWeightUnmodded, customName/name, fertilized,
fertilizedTime, wet, wetCooldown`.

**`age`, `offAge`, `offAgeMax`, `lastAged`, `freezingTime` and `rotten` are NOT in it.**
`SyncItemFieldsPacket.setData` is even thinner on the food side (`Food.getHungChange`,
`getActualWeightUnmodded`) and also carries no age. A reverse-reference scan for callers of
`InventoryItem.setAge` / `Food.setAge` returns **no packet class at all**.

Age travels only inside the **full item serialization**: `Food.save(ByteBuffer,boolean)` writes
`age @8`, `lastAged @17`, `offAge @539/@562`, `offAgeMax @570/@593`, `freezingTime`,
`lastFrozenUpdate`, `rottenTime`, `compostTime` (a bit-flag scheme — a field is only written when
it differs from the default), and `Food.load` restores them (`age @195`, `lastAged @203`,
`offAge @110/@631`, `offAgeMax @117/@652`, `freezingTime @147/@771`, `setFrozen @785`). The MP
carriers of that blob are `GameClient.receiveSendItemListNet`, `GameClient.receiveInvMngGetItem`,
`GameServer.receiveInvMngUpdateItem`, `IsoWorldInventoryObject.load/loadChange`, `EquipPacket`,
`TradingUIAddItemPacket`, `CompressIdenticalItems.load` — i.e. whenever the item is
(re)transmitted whole, not when its stats change.

**Practical consequence:** a client's displayed freshness for an item already in its inventory can
be stale indefinitely; it refreshes when the item is re-sent. When the server *does* cross a rot
threshold it calls `GameServer.sendItemStats(this)` (`updateAge(Z) @497–@510 L782-783`, only when
the `sync` flag is set — i.e. only from the no-arg `updateAge()`, rate-limited to 1 Hz by
`UpdateLimit(1000)`), and that packet **does not carry the new age** — only the derived
cooked/burnt/nutrition fields. `Food.update`'s own aging call passes `sync = false`
(`@45 L370`), so it never syncs at all.

The `OnContainerUpdate` Lua event fires on a fresh/rotten transition **only when
`!GameServer.server`** (`updateAge(Z) @470–@496 L779-780`) — i.e. in single-player, never on a
dedicated server, and never on a client because the client never runs `updateAge`.

Consistent with slice 01 / spikes S6: `sendItemStats` is `GameServer.sendItemStats`, server→client
only, a silent no-op on a client; there is no client→server item-field push
(`docs/testing/spikes.md` S6). Cooking is likewise server-driven: both `sendItemStats` calls in
`Food.update` (`@101 L379`, `@923 L500`) are `if (GameServer.server)`.

---

## Experiment inputs (for the later live dispatch)

### Exact setters / getters

| purpose | call | note |
|---|---|---|
| read age | `item:getAge()` | float days |
| set age | `item:setAge(days)` | plain field write, ungated |
| read thresholds | `item:getOffAge()`, `item:getOffAgeMax()` | ints; `1000000000` ⇒ never ages |
| force rotten | **`item:setAge(item:getOffAgeMax() + 1)`** | `setRotten(true)` is inert (Q2) — slice 01's fallback is the *only* route |
| force stale | `item:setAge(item:getOffAge())` | matches `ItemPickerJava.rotItem @93 L2257` |
| force fresh | `item:setAge(0)` | already in `item.state … fresh` |
| force frozen | **`item:freeze()`** or `item:setFreezingTime(100)` | `setFrozen(true)` alone is undone by the next `updateFreezing` tick (Q2). `item.state … frozen` currently uses `setFrozen` — expect it to decay |
| read frozen | `item:isFrozen()`, `item:getFreezingTime()` | 0–100 |
| force cooked | `item:setCooked(true)` | also raises `cookingTime` to `minutesToCook` |
| force burnt | `item:setBurnt(true)` | also raises `cookingTime` to `minutesToBurn` |
| cooking accumulator | `item:getCookingTime()` / `setCookingTime(v)` | game minutes |
| heat | `item:getHeat()` / `setHeat(v)` | 1.0 ambient, 0.2 fridge, `>1.6` cooks |
| force a full age tick | `item:updateAge(true)` (or `updateAge()`) | exposed on `Food`; the `true` argument also fires `sendItemStats` on the server |
| container context | `item:getOutermostContainer()`, `c:isFridge()`, `c:isFreezer()`, `c:isPowered()`, `c:getTemprature()` | |
| sandbox rates | `SandboxVars.FoodRotSpeed`, `SandboxVars.FridgeFactor`, `SandboxVars.DaysForRottenFoodRemoval`, `SandboxVars.ElecShutModifier` | `sandbox.set` already exists in the harness |

### Preconditions

1. **Aging only runs on the server.** Any `item.age`-style probe on the *client* measures nothing
   but the client's stale copy. The T2-step-4 accelerated test (`settimespeed 30`, one game day)
   must read the age **on the server** (`witness.item` style round-trip), not on the client — and
   the expected client-side answer is "unchanged", which is itself the finding.
2. **Fridge/freezer logic needs a real container.** `isInFridge`/`isInFreezer` test
   `ItemContainer.isFridge()`/`isFreezer()`, which need `type == "fridge"`/`"freezer"` (or
   `ContainerType.FRIDGE`, or the parent's `IsFridge` property). A player inventory is neither. The
   fridge multiplier additionally needs `container.getSourceGrid().haveElectricity()`, so the test
   fridge must be a placed appliance on a powered square. Alternative for a pure-arithmetic test:
   set `container.customTemperature` — `getTemprature()` short-circuits on it (`@0–@13 L2681-2682`).
3. **Freezing needs a *powered freezer*.** `isFreezing()` requires
   `canBeFrozen() && freezingTime < 100 && isInFreezer(c) && c.isPowered()`. Outside one, use
   `freeze()` directly and then confirm the ×0 age rate before `updateFreezing` thaws it.
4. **Cooking needs `heat > 1.6`** on the item *and* `container.getTemprature() > 1.6` for the full
   rate (a stove above `currentTemperature = 60`). To exercise the transitions without an
   appliance, write `setCookingTime(minutesToCook + 1)` and call `item:update()` — or just use the
   ungated `setCooked`/`setBurnt`.
5. **Evolved-recipe base items.** `Base.Pot` recipes (`Soup`, `Stew`) declare
   `MinimumWater = 0.9`, so `getItemsCanBeUse` returns an empty list unless the pot's fluid
   container is ≥ 90 % water. Use **`evolvedrecipe Salad`** instead: `BaseItem = Base.Bowl`,
   `ResultItem = Base.Salad`, `MaxItems = 6`, **no `MinimumWater`, no `Cookable`**
   (`evolvedrecipes.txt`, block `Salad`). Caveat: with `MinimumWater == 0` the base must have
   either no fluid container or an *empty* one.
6. **Ingredients must be in a container the recipe scans**: `getItemsCanBeUse` adds
   `chef.getInventory()` to the container list, so the player's own inventory is enough.
   Rotten ingredients need Cooking ≥ 7; frozen ones are refused (`AllowFrozenItem` is never set in
   vanilla); burnt ones always refused.
7. **Cooking level dominates the summation.** Fix `Perks.Cooking` explicitly before any
   evolved-recipe measurement; at level 0, `skillBonus = 1` and `hungerAfterSkill = hunger`.

### Commands slice 01 already provides

`testing/PZTestKit/PZTestKit/42/media/lua/client/PZTestKit_Client.lua`:

- `item.script <fullType>` — `HungerChange, ThirstChange, Calories, Carbohydrates, Lipids,
  Proteins, DaysFresh, DaysTotallyRotten, IsCookable, MinutesToCook, MinutesToBurn` (`:220-221`).
  Measured limitation: the four macro keys come back **absent** — Kahlua does not expose them on
  the script `Item` (`:231-234`), so per-item macros must come from an instantiated item.
- `item.state <fullType> [cooked|burnt|rotten|frozen|fresh]` (`:284`) — returns
  `fullType, cooked, burnt, rotten, frozen, age, hungChange, baseHunger, calories, carbs, lipids,
  proteins, id, uses, spawned`. Already has the `setRotten` → `setAge(offAgeMax+1)` fallback
  (`:290-296`).
- `eat <fullType> [fraction]` (`:305`) — direct `IsoGameCharacter.Eat`; `eat.action` for the real
  MP path.
- `witness.item <…>` (client `:*`), `nutrition.get/set`, `stats.set`, `sandbox.set`,
  `item.spawn`, `item.tamper`, `time.snapshot`, server-side `time.multiplier`, `nutrition.get/set`.
- **There is no server-side `item.set`** — the server module registers only `time.multiplier`,
  `players`, `nutrition.get`, `nutrition.set`, `stats.set`
  (`…/media/lua/server/PZTestKit_Server.lua`).

### New harness commands the M steps need

1. **`item.age <fullType> <days>`** (client) — `it:setAge(days)`, return `itemState(it)`. Useful
   for the pure-arithmetic reads (`isFresh`, `isRotten`, `getHungChange`, macros) which are all
   local getters. Add `age.tick` = `it:updateAge(true)` so the harness can force one aging step
   without waiting for a tick.
2. **`item.set <user> <fullType> <field> <value>` (SERVER)** plus an explicit
   `sendItemStats(item)` — this is the missing piece. Because the client cannot age and cannot
   push item fields (spikes S6), every measured aging/cooking result has to be produced on the
   server. Fields needed: `age`, `offAge`, `offAgeMax`, `freezingTime`, `cookingTime`, `heat`,
   `cooked`, `burnt`. Note that `sendItemStats` **will not carry `age` back to the client** (Q8) —
   so the command must also *report* the server-side reading directly (witness-style), not rely on
   the client re-reading the item.
3. **`item.read <user> <fullType>` (SERVER)** — the server's own `itemState`, to compare against
   the client's. This is the only way to observe aging at all, and it directly answers Task 2
   step 4.
4. **`recipe.add <baseType> <ingredientType>` (client)** — locate the `EvolvedRecipe` via
   `getEvolvedRecipes()` / `RecipeManager.getEvolvedRecipe`, then either call
   `recipe:addItem(base, ingredient, player)` directly (matching `ISAddItemInRecipe.lua:70`) or
   queue `ISAddItemInRecipe:new(player, recipe, base, used)`. Return `itemState` for both the new
   base and the leftover ingredient. Add `recipe.list <baseType>` returning
   `recipe:getItemsCanBeUse(player, base, nil)` so a blocked precondition (water, MaxItems,
   frozen, burnt) is diagnosable rather than a silent empty menu.
5. **`skill.set Cooking <n>`** — the summation is skill-dependent in two places; without pinning
   the level the numbers are unreproducible.
6. Optional: **`container.spawn <type>`** or a `customTemperature` setter, to get a fridge/freezer
   context without hunting for a powered appliance in the fixture world.

### Suggested measurement targets

- Q2: with `FoodRotSpeed = 3` (1.0) and one game day elapsed, `Δage` should be exactly `1.0`;
  in a powered fridge, `0.2`; frozen, `0.0`.
- Q3: at `age = offAge − ε`, `offAge + ε`, `offAgeMax + ε` — `getHungChange` unchanged at all
  three (it is the raw field), `Eat`'s hunger delta scaled by 1 / 1/1.3 / 1/2.2, and the four
  macros **identical at all three** (this is the headline prediction).
- Q4: `cookingTime` should advance by `heat/1.5` per game minute on a stove at max heat
  (`heat = 2.0` ⇒ `1.333`/min), so a `MinutesToCook = 10` item cooks in ~7.5 game minutes, not 10.
- Q5: with Cooking 0, dish calories = `Σ ing.calories × share`; with Cooking 10, `× 1.667` and a
  larger `share`. Two carrots into a `Base.Bowl` Salad is the cheapest probe.

---

## Open / uncertain

1. **Does food age at all in single-player at default settings?** The code says no: `Food.update`
   gates `updateAge` on `GameServer.server` (`@38 L369`), `updateRotting` returns early on
   `GameClient.client` and otherwise only ages when `ReplaceOnRotten` is set or
   `DaysForRottenFoodRemoval >= 0` — and all five shipped presets set it to `−1`. The container
   hooks `OnAddedToContainer`/`OnBeforeRemoveFromContainer` are also server-gated. That leaves
   `IsoCompost.update` and `ISWorldObjectContextMenuLogic.handleGrabWorldItem` as the only SP
   aging paths. This is either a real 42.20.4 regression or a call site I have not found. **The
   harness runs a dedicated server, where this does not bite**, so it does not block slice 02 —
   but it must not be stated as fact in a shipped doc without an SP measurement.
2. **Where is `updateAge(true)` (the syncing form) actually called from?** Only the no-arg
   `Food.updateAge() @0–@10 L732-733` passes the `UpdateLimit` result, and its only caller is
   `updateRotting @37 L663` (the `ReplaceOnRotten` branch) plus `IsoCompost`. So on a dedicated
   server the 1 Hz `sendItemStats` on a rot transition effectively never fires for ordinary food.
   Worth confirming against a live server log.
3. **Client-side rot display in MP.** If the client never ages and `ItemStatsPacket` carries no
   age, the client's freshness readout must come from the last full serialization. Whether the
   server re-sends inventory items periodically (and how often) is not established here —
   `GameClient.receiveSendItemListNet` exists but its trigger cadence was not traced.
4. **`tableswitch` enum ordinals.** I decoded `getFridgeFactor`/`getFoodRotSpeed` from the raw
   switch table (cases 1–6 / 1–5, default = case 3). The *labels* attached to those ordinals
   ("Very Low", "Normal", …) come from the translation keys `FridgeEffect`/`FoodSpoil` and were
   not read; only the numeric mapping is Ev C.
5. **`RottenTime`.** `Food.rottenTime` has a getter, a setter, save/load support and no script
   key; the only writer is `IsoCompost.update` and there are **zero readers** in the jar. It looks
   vestigial, but a Lua/mod reader outside `media/lua` would not show in this scan.
6. **`Poison` / `UseForPoison`.** Both parse into `Food` fields with no Java or vanilla-Lua
   reader. `isPoison()` in particular looks like it should gate something. Flagged as
   loader-supported, runtime-inert; a mod-facing API rather than a mechanic.
7. **`Packaged` and `CannedFood` on the instance.** `Packaged` is copied to the item and never
   read; `CannedFood` is never copied and is read only from the script object. If the nutrition
   mod wants "sealed" semantics it should key off `getOffAgeMax() == 1000000000` (or the
   `CantEat` + `OpeningRecipe` pair), not off `isPackaged()`.
8. **`AddIngredientIfCooked` and `CanAddSpicesEmpty`** are parsed by `EvolvedRecipe.Load`
   (`@184–@198`, `@228–@242`) and `canAddSpicesEmpty` is read in `checkItemCanBeUse @117 L222`,
   but I did not trace a reader for `addIngredientIfCooked` (37 blocks use it). Possibly consumed
   in the part of `checkItemCanBeUse` beyond offset 258, which I did not fully dump.
9. **`EvolvedRecipe.useSpice`** (two overloads) was not dumped — the spice branch's actual effect
   on the dish (beyond the herbal-tea sums) is therefore unread. It matters only if the mod cares
   about spices.
10. **`InventoryItem.getStringItemType()`** returning `"CannedFood"` was read only around the
    canned branch; the rest of its type ladder was not enumerated.
