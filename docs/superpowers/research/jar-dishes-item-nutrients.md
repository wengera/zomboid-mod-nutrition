# Per-instance nutrition: dishes, splits, meat and fluids — a jar read

Build `42.20.4` · jar `b0bbce05d5` · read 2026-09-27 · toolchain `C:\Users\Angus\pz-b42` (`./pz.sh grep|methods|refs|dump`), access flags from a scratch constant-pool parser rebuilt over `tools/cp.py` this session, exposure from a whole read of `LuaManager$Exposer.exposeAll()` (3 055 instruction lines).
Every cite below is `Class.method @off L<n>` from a dump taken in this session; every absence is a jar-wide grep whose exact search string is named.
Shipped-Lua cites are `media/lua/<path>:<lines>` under `D:\SteamLibrary\steamapps\common\ProjectZomboid`, read read-only.

## Summary for the design

An evolved dish does carry its ingredient list on the instance, as `InventoryItem.extraItems`, an `ArrayList<String>` of ingredient **full types** and nothing else — no amount, no hunger share, no order guarantee beyond insertion order, and a repeated ingredient appears once per add so counts per type are recoverable.
The list saves and loads (as registry short ids), and it crosses server to client on `ItemStatsPacket`; it is absent from `SyncItemFieldsPacket` entirely, so `syncItemFields()` never moves it.
Spices ride a second list, `Food.spices`, also full types, also saved and also on `ItemStatsPacket`.
So a server-side handler at eat time can read a dish's ingredient types off the instance, but it cannot read what each ingredient actually contributed: the hunger share depended on the chef's Cooking level, on the ingredient instance's own remaining `hungChange`, on its rotten flag and on a clamp, and none of those four is recorded anywhere on the dish.
What a mod can reconstruct instead is the *nominal* share per ingredient type, because `EvolvedRecipe.getItemsList()` is exposed and gives `ItemRecipe.getUse()` per ingredient type, and `use / 100` is the nominal hunger that type spends; normalising those nominal shares against the dish's own `hungChange` is an inference the library has not measured.
`EvolvedRecipe.addItem` writes nothing into item modData except one key on one branch — a `HandWeapon` base item gets a condition ratio rawset under its own type name — so a mod nutrient riding the base item's default modData reaches the dish **not at all**; the dish is a fresh `InventoryItemFactory.CreateItem(resultItem)` and therefore carries its own result type's default modData, one copy, deep.
`addItem` calls no Lua function and fires no event: the whole 893-instruction body holds exactly one Kahlua reference, that HandWeapon rawset, and no `LuaManager.caller` and no `triggerEvent` anywhere.
The practical hook for a dish is therefore a server-side wrapper of `ISAddItemInRecipe:complete` (shared Lua, lines 66–88), which sits either side of the one `recipe:addItem(...)` call and can read the base item before and after it.
The craft-recipe split arm is not called `PassNutritionThroughFood` — that string is not in the jar at all; the real flag is `InputFlag.InheritFood` and the site is `CraftRecipeData.createOutputItems`, which calls `output.copyFoodFromSplit(input, OutputScript.getIntAmount())`.
That split copies nutrition divided by the output amount, plus frozen, cooked/burnt, temperature, poison, age **and the input's `extraItems` and `spices` lists** — and no modData at all, so a mod nutrient in the input's item modData does not reach the outputs.
The craft `OnCreate` hook does fire with the consumed items still reachable: `CraftRecipeData.luaCallOnCreate(character)` passes the recipe-data object itself to Lua, and that object exposes `getAllConsumedItems()`, `getAllRecordedConsumedItems()`, `getFirstInputItemWithFlag(...)` and `getAllCreatedItems()` — so a mod can propagate its own nutrients across a split, and the shipped Lua already does exactly this shape, writing a consumed-full-type → count map into the single output's modData at `ISHandcraftAction.lua:236–247`.
There is a second, separate craft summation in Java, `RecipeCodeOnCreate.copyFoodValuesFromList`, which sums the consumed foods' `baseHunger` and four macros onto the first created item (omelette, sushi); it too touches no modData.
Per-animal meat variation is a Lua path, not the Java one: `ButcheringUtil.modifyMeat` scales hunger and all four macros by `size × meatRatio × hungerBoost`, but with an **independent** `ZombRandFloat(0.9, 1.1)` roll per field, so the scale factor is recoverable from the instance only to within about ±11 per cent per field — `instance:getBaseHunger()` against `getScriptItem():getHungerChange()/100` gives `ratio × r_hunger`, which is not the `ratio × r_calories` the calorie column got.
`Food.copyNutritionFromRatio` has no caller anywhere in the jar and none in the shipped Lua, so on this build the split path reaches it only through `copyFoodFromSplit`; its own ratio is exactly recoverable because it is `1/amount` from the output script, not a random roll.
Item modData is fully reachable at eat time on the server — `InventoryItem.getModData()` is public on an exposed class and lazily creates the instance's own table — and the script's default modData is a genuine **deep, recursive, per-instance copy** (`copyModData` wipes then `LuaManager.copyTable`), not a shared reference, so writing to one instance's nutrient key cannot corrupt the type default or any sibling instance.
`Food.multiplyFoodValues` touches modData not at all: its whole body is 15 field multiplications and a return, read end to end.
Fluids are the one genuine wall: `FluidDefinitionScript` has **no** default arm — an unrecognised key in a `fluid` block or in its `properties` block is logged as an error and, under `Core.debug`, throws, and nothing stores it — so a per-fluid mod nutrient must live in a Lua table keyed by `fluid:getFluidTypeString()` (never null on a `Fluid` object, unlike the script's own getter) and never on the fluid script.
Reading the mix on an instance is fully served: `item:getFluidContainer()` then `getAmount()` (litres), `createFluidSample()` → `size()`/`getFluid(i)`/`getPercentage(i)`, plus `getRatioForFluid(fluid)`, `getSpecificFluidAmount(fluid)`, `isMixture()` and `getPrimaryFluid()`; `FluidInstance` itself is **not** exposed, which is why the sample is the iteration route.
The wrapper target for drinking is `ISDrinkFluidAction:updateEat(delta)` (`media/lua/shared/TimedActions/ISDrinkFluidAction.lua:109–120`), which computes an incremental `deltaToConsume` and calls `DrinkFluid` once per tick; a mod wrapping it reads the container's litres and mix before the call and again after, and the difference is the litres actually drunk.

## A — do evolved dishes carry their ingredient list?

Yes, as full-type strings with no amount. The list lives on `InventoryItem`, not on `Food`, so `Food` inherits it.

| member | signature | flags | exposed? | side | cite |
|---|---|---|---|---|---|
| `InventoryItem.extraItems` | `Ljava/util/ArrayList;` | public (field) | n/a (field) | both | `InventoryItem.addExtraItem @0–@27 L3136–L3141` |
| `InventoryItem.getExtraItems` | `()Ljava/util/ArrayList;` | public | yes (`InventoryItem` in exposer set) | both | `InventoryItem.getExtraItems @0 L3148` |
| `InventoryItem.haveExtraItems` | `()Z` | public | yes | both | `InventoryItem.haveExtraItems @0–@22 L3144` |
| `InventoryItem.addExtraItem` | `(Ljava/lang/String;)V` | public | yes | both | `InventoryItem.addExtraItem @0–@27 L3136–L3141` (lazy-creates the list, appends the string) |
| `InventoryItem.addExtraItem` | `(Lzombie/scripting/objects/ItemKey;)V` | public | yes | both | `InventoryItem.addExtraItem @0–@8 L3132–L3133` (delegates via `ItemKey.toString()`) |
| `InventoryItem.getExtraItemsWeight` | `()F` | public | yes | both | `InventoryItem.getExtraItemsWeight @24–@69 L3158–L3164` — each string is fed to `InventoryItemFactory.CreateItem`, i.e. the strings are item full types; the sum is ×0.6 |
| `Food.spices` | `Ljava/util/ArrayList;` | public (field) | n/a | both | `EvolvedRecipe.useSpice @9–@38 L617–L620` (lazy-creates, appends `usedItem.getFullType()`) |
| `Food.getSpices` / `Food.setSpices` | `()Ljava/util/ArrayList;` / `(Ljava/util/ArrayList;)V` | public / public | yes (`Food` in exposer set) | both | member list + `Food.copyExtraItems @42–@64 L2698–L2699` |
| `Food.getExtraItems` | — | **not declared on `Food`** | inherited | both | `methods zombie/inventory/types/Food` has no `getExtraItems`; `Food extends InventoryItem` (super-class read this session) |
| `InventoryItem.save` (extraItems arm) | `(Ljava/nio/ByteBuffer;Z)V` | public | n/a | both | `InventoryItem.save @435–@511 L1662–L1665` — bit flag `32`, then `putInt(size)`, then per entry `WorldDictionary.getItemRegistryID(String)` → `putShort` |
| `InventoryItem.load` (extraItems arm) | `(Ljava/nio/ByteBuffer;I)V` | public | n/a | both | `InventoryItem.load @632–@686 L1956–L1959` — `getShort` → `WorldDictionary.getItemTypeFromID` → new `ArrayList<String>` |
| `Food.save` (spices arm) | `(Ljava/nio/ByteBuffer;Z)V` | public | n/a | both | `Food.save @416–@483 L990–L995` — bit flag `256`, `put((byte) size)`, then `GameWindow.WriteString` per entry |
| `Food.load` (spices arm) | `(Ljava/nio/ByteBuffer;I)V` | public | n/a | both | `Food.load @522–@568 L1195–L1199` — `get()` byte count, `GameWindow.ReadString` per entry |
| `ItemStatsPacket.setData` | `([Ljava/lang/Object;)V` | — | no (packet class absent from exposer set) | server sender | `ItemStatsPacket.setData @413–@468 L205–L211` — clears then `addAll` from `Food.extraItems` and `Food.spices` |
| `ItemStatsPacket.write` | `(Lzombie/core/network/ByteBufferWriter;)V` | — | no | server | `@654–@718 L333–L338` extraItems behind flag `4194304`, count as **one byte**, each entry `putUTF`; `@721–@787 L340–L345` spices behind flag `8388608`, same shape |
| `ItemStatsPacket.parse` | `(…)V` | — | no | receiver | `@546–@596 L445–L449` and `@599–@649 L452–L456` — both lists are `clear()`ed **before** the flag test, so neither can carry a stale value |
| `ItemStatsPacket.applyItemStats` | `(Lzombie/inventory/InventoryItem;)V` | — | no | receiver | `@282–@318 L556–L560` extraItems, `@351–@387 L565–L569` spices — lazy-create, `clear()`, `addAll` |
| `SyncItemFieldsPacket` | — | — | no | — | **absent**: jar-wide `grep extraItems` returns exactly `InventoryItem.class`, `ItemStatsPacket.class`, `EvolvedRecipe.class`; jar-wide `grep spices` adds only `Food.class`. `SyncItemFieldsPacket.setData` names 32 packet fields and neither list is among them (`moddata` is) |

Where the summation writes the list: `EvolvedRecipe.addItem @1757–@1766 L463–L465` calls `dish.addExtraItem(usedItem.getFullType())` — after the whole macro transfer, and only on the non-spice branch; the spice branch returns at `@1755 L461` before it.
Then `@1769–@1848 L466–L470` sends `PacketType.ItemStats` with `{container, dish}` when `GameServer.server`, to the owning player if the container's parent is an `IsoPlayer` and `sendToRelative` otherwise.

**What the list does and does not preserve.** It preserves the ingredient's full type and, because every add appends, the number of times each type was added — the duplicate scan at `addItem @1049–@1099 L389–L392` reads exactly that, comparing each stored string to `usedItem.getFullType()`. It does **not** preserve the hunger each ingredient contributed: the only per-ingredient number in the block, `hunger = itemRecipe.use / 100f` at `@518–@545 L333`, is consumed into the dish's `hungChange` and never stored per entry. Nor is the Cooking level, the ingredient's remaining `hungChange`, its rotten flag, or the clamp outcome recorded. Absences confirmed by jar-wide greps that return "no class contains that literal": `extraItemsAmount`, `extraItemAmount`, `extraItemUses`, `extraItemsHunger`, `ingredientAmount`.

So a server-side handler at eat time **can** compute mod nutrients from the list, but only from per-type values, not from measured shares. The recoverable inputs are: the type list with counts (instance), the recipe's nominal `use` per type (`EvolvedRecipe.getItemsList()` → `ItemRecipe.getUse()`, both public on exposed classes), and the dish's own `hungChange`/`baseHunger`. Joining the two needs a module strip: `extraItems` holds `getFullType()` (`Base.Lettuce`) while `getItemsList()` is keyed by `getType()` (`Lettuce`) — `addItem @463–@471 L331` reads `itemsList.get(item.getType())`.

Two traps on the wire. The packet writes the list length as a **byte**, so a list longer than 127 would truncate silently (`MaxItems` caps vanilla well below that). And `getExtraItemsWeight` instantiates a fresh item per entry on every call, which makes it an expensive read to put on a per-tick path.

## B — what the evolved summation writes, and what it does not

| member | signature | flags | exposed? | side | cite |
|---|---|---|---|---|---|
| `EvolvedRecipe.addItem` | `(Lzombie/inventory/InventoryItem;Lzombie/inventory/InventoryItem;Lzombie/characters/IsoGameCharacter;)Lzombie/inventory/InventoryItem;` | public | yes (`EvolvedRecipe` in exposer set) | wherever `ISAddItemInRecipe:complete` runs; server sends the packet | dump read whole, 893 lines |
| result item creation | — | — | — | — | `addItem @37–@44 L271` — `InventoryItemFactory.CreateItem(this.resultItem)`; a **fresh instance**, so it gets its own type's default modData |
| macro zeroing (phase A) | — | — | — | — | `addItem @190–@211 L291–L294` — `setCalories/setCarbohydrates/setProteins/setLipids(0)` |
| hunger re-seed from base | — | — | — | — | `addItem @222–@265 L297–L302` — `setHungChange`/`setBaseHunger` from the base food, else both 0 |
| macro re-seed from base | — | — | — | — | `addItem @338–@395 L309–L314` — tainted, calories, proteins, lipids, carbohydrates, `thirstChange` copied from the base food |
| age carry-across | — | — | — | — | `addItem @268–@320 L304–L306` — `newAge = newOffAgeMax × oldAge / oldOffAgeMax`, only when neither `offAgeMax` is `1000000000` |
| mood zeroing | — | — | — | — | `addItem @398–@405 L318–L319` — `setUnhappyChange(0)`, `setBoredomChange(0)` |
| condition / favourite / colour / model | — | — | — | — | `addItem @51–@135 L274–L283`, `@408–@426 L320–L321` |
| **the only modData write** | — | — | — | — | `addItem @125–@166 L282–L284` — gated on `baseItem instanceof HandWeapon`; `dish.getModData().rawset(base.getType(), base.getCondition()/base.getConditionMax())`. Nothing else in the body touches a Kahlua table |
| per-ingredient hunger | — | — | — | — | `addItem @518–@545 L333` — `hunger = itemRecipe.use / 100f` |
| spice branch | `useSpice(InventoryItem,Food,II,IsoGameCharacter)V` | **private** | no (private) | same | `addItem @1721–@1755 L459–L461`; `EvolvedRecipe.useSpice @9–@38 L617–L620` appends `getFullType()` to `Food.spices` and returns — no hunger, no macros |
| ingredient append | — | — | — | — | `addItem @1757–@1766 L463–L465` |
| `ItemStats` send | — | — | — | server only | `addItem @1769–@1848 L466–L470`, gated on `GameServer.server` |
| Cooking XP | — | — | — | branches on side | `addItem @1886–@1924 L481–L484` — `GameServer.addXp(player, Cooking, 3.0)` on the server, `getXp().AddXP` when not a client |
| **no Lua hook, no event** | — | — | — | — | the whole `addItem` dump (893 lines) contains exactly one Kahlua reference, the `rawset` at `@166`; there is no `LuaManager.caller`, no `LuaManager.getFunctionObject`, no `triggerEvent`, no `pcall*`. Jar-wide `grep OnEvolvedRecipe` and `grep OnAddItemInRecipe`: "no class contains that literal" |

**Does the dish get anything from an ingredient's modData?** No. The only modData write in `addItem` is the HandWeapon condition key, and it copies from the *base* item's condition, not from any modData. A mod nutrient riding an ingredient's default modData is therefore invisible to the dish, and a mod nutrient riding the *base* item's modData is also lost, because the result is a new instance whose table is wiped and re-seeded from the **result type's** default modData (`Item.InstanceItem @3477–@3482 L1868` → `InventoryItem.copyModData @0–@29 L2906–L2912`).

**The skill scaling.** Already settled in the library and re-confirmed by the same body: `hungerAfterSkill = hunger − (3 × cookLvl / 100) × hunger`, `share = min(|hungerAfterSkill / ing.getHungChange()|, 1)`, `skillBonus = 1 + cookLvl / 15`, the dish gaining `macro × skillBonus × share` while the ingredient loses `macro × share`. The perk level is read at `addItem @0–@7 L265` from `character.getPerkLevel(Perks.Cooking)`, so it is the level of whichever process runs the method.

**Where a mod can stand instead.** `ISAddItemInRecipe:complete` (`media/lua/shared/TimedActions/ISAddItemInRecipe.lua:66–88`) is the sole Lua-to-Java bridge into the summation: it calls `self.recipe:addItem(self.baseItem, self.usedItem, self.character)` at line 70 and, when `isServer()`, `sendItemStats` on both items at lines 80–85. A `server/`-side wrapper of `complete` sees the base item, the used item and the chef **before** the call and the finished dish after it, which is the only place both ingredient instance and dish exist together.

## C — craft recipes: the split arm

The string the library's prose calls "pass its food on" is not in the jar. Jar-wide greps returning "no class contains that literal": `PassNutritionThroughFood`, `PassNutrition`, `NutritionThroughFood`. The real flag is `InputFlag.InheritFood`; jar-wide `grep InheritFood` returns `generation/CraftRecipeScriptGenerator.class`, `zombie/entity/components/crafting/InputFlag.class`, `zombie/entity/components/crafting/recipe/CraftRecipeData.class`.

| member | signature | flags | exposed? | side | cite |
|---|---|---|---|---|---|
| `CraftRecipeData.createOutputItems` | `(OutputScript;ItemDataList;Z;CacheData;IsoGameCharacter;)Z` | **private** | no (private) | server/host | `@1096–@1143 L1542–L1544` — `getFirstInputItemWithFlag(InputFlag.InheritFood)`, then `output.copyFoodFromSplit(input, outputScript.getIntAmount())` |
| `Food.copyFoodFromSplit` | `(Lzombie/inventory/types/Food;I)V` | public | yes | both | `@0–@33 L2704–L2710` — `copyNutritionFromSplit`, `copyFrozenFrom`, `copyCookedBurntFrom`, `copyTemperatureFrom`, `copyPoisonFrom`, `copyAgeFrom`, `copyExtraItems`. No modData |
| `Food.copyNutritionFromSplit` | `(Lzombie/inventory/types/Food;I)V` | public | yes | both | `@0–@6 L2673` — `copyNutritionFromRatio(src, 1f / amount)` |
| `Food.copyNutritionFrom` | `(Lzombie/inventory/types/Food;)V` | public | yes | both | `@0–@3 L2669` — `copyNutritionFromSplit(src, 1)` |
| `Food.copyNutritionFromRatio` | `(Lzombie/inventory/types/Food;F)V` | public | yes | both | `@0–@87 L2677–L2685` — nine fields, each `src.getX() × ratio`: `baseHunger`, `hungChange`, `carbohydrates`, `lipids`, `proteins`, `calories`, `unhappyChange`, `thirstChange`, `boredomChange`. **No modData, no extraItems** |
| `Food.copyExtraItems` | `(Lzombie/inventory/types/Food;)V` | public | yes | both | `@0–@64 L2693–L2699` — `addExtraItem` per string, then `setSpices(src.getSpices())`, which **shares the ArrayList reference** rather than copying it |
| `CraftRecipeData.createOutputsInternal` | `(ZLjava/util/List;IsoGameCharacter;)Z` | — | — | **not a client**: throws `RuntimeException 'Cannot call with testOnly==false on client.'` | `@0–@20 L784–L785` |
| `CraftRecipeData.luaCallOnCreate` | `(Lzombie/characters/IsoGameCharacter;)V` | public | yes (`CraftRecipeData` in exposer set) | caller's side | `@8–@32 L471–L473` — `LuaManager.caller.protectedCallVoid(thread, fn, this, character)`: the hook receives the **recipe-data object** and the character |
| `CraftLogicSystem.stop` | `(CraftLogic;CraftRecipeData;Z;ResourceGroup;)V` | — | — | returns immediately when `GameClient.client` | `@0–@6 L167–L168`; `@39–@52 L182–L183` — `createOutputs(...)` then, on success, `luaCallOnCreate()` |
| `CraftRecipeData.getAllConsumedItems` | `()Ljava/util/ArrayList;` | public | yes | — | `@0–@11 L2199` → `@0–@95 L2220–L2235`, which walks `inputs` and calls `InputScriptData.addAppliedItemsToList` → `CacheData.addAppliedItemsToList @0–@8 L1868–L1869` over the private final `appliedItems` list |
| `CraftRecipeData.getAllRecordedConsumedItems` | `()Ljava/util/ArrayList;` | public | yes | — | member list (flags parsed); same family, `isRecordInput`-filtered arm at `@64–@85 L2230–L2233` |
| `CraftRecipeData.getFirstInputItemWithFlag` | `(InputFlag;)Lzombie/inventory/InventoryItem;` / `(Ljava/lang/String;)…` | public / public | yes; `InputFlag` also in exposer set | — | member list (flags parsed) |
| `CraftRecipeData.getAllCreatedItems` | `()Ljava/util/ArrayList;` | public | yes | — | member list (flags parsed) |
| `RecipeCodeOnCreate.copyFoodValuesFromList` | `(CraftRecipeData;Ljava/util/List;)V` | public static | yes (`RecipeCodeOnCreate` in exposer set) | server/host | `@0–@166 L420–L436` — sums each input `Food`'s `baseHunger`, `calories`, `carbohydrates`, `proteins`, `lipids` (skipping a spice unless it is `FISH_ROE`) onto `getAllCreatedItems().getFirst()`. No modData, no extraItems |
| `RecipeCodeOnCreate.makeOmelette` | `(CraftRecipeData;IsoGameCharacter;)V` | public static | yes | server/host | `@0–@8 L416` — `copyFoodValuesFromList(data, getConsumedItems(data, ItemTag.EGG))` |

**What the split copies.** Macros and the two hunger fields divided by the output amount, plus mood deltas, thirst, frozen/cooked/burnt/temperature/poison/age, plus the input's ingredient and spice lists. Item modData is not among them — `copyFoodFromSplit` names seven callees and none of them is a modData copy, and `copyNutritionFromRatio`'s body is nine setter calls with nothing else.

**Can a mod propagate its own nutrients through the split?** Yes, through `OnCreate`, and the shipped Lua already demonstrates the exact shape. `ISHandcraftAction:performRecipe` (`media/lua/shared/TimedActions/ISHandcraftAction.lua:221–249`) calls `self.logic:getRecipeData():luaCallOnCreate(self.character)` at line 233 and then, when there is exactly one output item, walks `getAllConsumedItems()` and writes `modData[item:getFullType()] = count` onto the output at lines 236–247. A mod's own `OnCreate` function gets the same `CraftRecipeData` and can read `getAllConsumedItems()` / `getFirstInputItemWithFlag("InheritFood")` and write its nutrient keys onto `getAllCreatedItems()`.

**Ordering caveat, unsettled.** In the entity path, `createOutputs` (which internally runs `destroyAllSurvivingDestroyInputs` at `createOutputsInternal @123 L811`) completes **before** `luaCallOnCreate`; in the hand-craft path the Lua calls `luaCallOnCreate` before `processDestroyAndUsedItems`. Whether a consumed input's own macros have already been decremented by the use-spend at `OnCreate` time was not read; the objects themselves are still reachable in `appliedItems` either way.

## D — per-instance base variation and whether the factor is recoverable

| member | signature | flags | exposed? | side | cite |
|---|---|---|---|---|---|
| `IsoAnimal.modifyMeat` | `(Lzombie/inventory/types/Food;FF)V` | **public static** | yes (`IsoAnimal` in exposer set) | caller's | `@0–@93 L3859–L3863` |
| — what it scales | — | — | — | — | `hungChange = baseHunger × f1 × f2 × Rand.Next(0.9,1.1)` `@0–@19 L3859`; then `baseHunger = getHungerChange()` (the **state-modified** getter) `@22–@27 L3860`; then `calories` `@30–@49 L3861`, `lipids` `@52–@71 L3862`, `proteins` `@74–@93 L3863` — each with its **own** `Rand.Next(0.9,1.1)` call. `carbohydrates` untouched |
| — callers | — | — | — | — | jar-wide `grep modifyMeat` returns only `zombie/characters/animals/IsoAnimal.class`, and the shipped Lua's only `modifyMeat` hits are the Lua function `ButcheringUtil.modifyMeat`; so no other Java class and no shipped Lua file calls the Java method |
| `ButcheringUtil.modifyMeat` (Lua) | `(item, size, meatRatio, hungerBoost, rotten, deathAge)` | Lua | n/a | `shared/` file | `media/lua/shared/Definitions/animal/ButcheringUtil.lua:426–447` — `ratio = size × meatRatio × hungerBoost`; then `setHungChange(getBaseHunger() × ratio × ZombRandFloat(0.9,1.1))`, `setBaseHunger(getHungerChange())`, then calories, lipids, proteins **and carbohydrates**, each with its own `ZombRandFloat(0.9,1.1)`; then `setAge(...)`. Called from lines 332 and 393 of the same file |
| `Food.copyNutritionFromRatio` | `(Lzombie/inventory/types/Food;F)V` | public | yes | both | `@0–@87 L2677–L2685` (see § C) |
| — its callers | — | — | — | — | jar-wide `grep copyNutritionFromRatio`, `grep copyNutritionFromSplit`, `grep copyNutritionFrom` each return only `zombie/inventory/types/Food.class`; the shipped Lua contains no `copyNutrition` hit at all. So on this build the only reachable route into it is `copyFoodFromSplit`, called from `createOutputItems` |
| `Item.InstanceItem` (hunger) | `(Ljava/lang/String;Z)Lzombie/inventory/InventoryItem;` | public | yes (`Item` in exposer set) | both | `@559–@582 L1559–L1560` — `hungChange = script.hungerChange / 100`, `baseHunger = script.hungerChange / 100` |
| `Item.InstanceItem` (macros) | same | public | yes | both | `@745–@778 L1578–L1581` — the four macros copied **unscaled** from the script fields |
| `Item.getHungerChange` | `()F` | public | yes | both | `@0–@4 L555` — bare read of the public `Item.hungerChange` field |
| `Item.calories` / `carbohydrates` / `lipids` / `proteins` | `F` | **private, no getter** | no reader from Lua | — | the full member list of `zombie/scripting/objects/Item` contains no `getCalories`, `getCarbohydrates`, `getLipids` or `getProteins`; `./pz.sh dump zombie/scripting/objects/Item getCalories` answers `method not found` |

**Recoverability.** For hunger, exactly one factor is recoverable: `instance:getBaseHunger() ÷ (instance:getScriptItem():getHungerChange() / 100)` equals `ratio × r_hunger`. For calories it is `instance:getCalories() ÷ scriptCalories`, equal to `ratio × r_calories`. Because the rolls are independent draws from `[0.9, 1.1]`, the two differ by up to a factor of `1.1/0.9 ≈ 1.22`, i.e. a per-field disagreement of about ±11 per cent around `ratio`. A mod that scales its own per-type nutrient values by the hunger-derived factor therefore inherits that jitter rather than matching the vanilla calorie column; scaling by the calorie-derived factor matches calories exactly and mismatches hunger by the same band. `ratio` itself is separately recoverable at butcher time (from `carcass:getAnimalSize()` and `getMeatRatio()`, both public on the exposed `IsoAnimal`) but nothing records it on the meat item.

A second obstacle: the script's per-type macros cannot be read off `getScriptItem()` at all — the four fields are private with no getter. The workable route is a fresh instance, `instanceItem("Base.SteakRaw"):getCalories()` (`LuaManager$GlobalObject.instanceItem(String) @0–@4 L4928` → `InventoryItemFactory.CreateItem`), or the mod's own data table. Note `InventoryItemFactory` itself is **not** in the exposer class set; the `instanceItem` global is the door.

For `copyNutritionFromRatio` the factor is exact and recoverable from the recipe rather than the instance: it is `1 / OutputScript.getIntAmount()`, read at `createOutputItems @1139–@1143 L1544`. One asymmetry worth knowing: the method reads `src.getThirstChange()` — the **cooked-ladder** getter — and writes through `setThirstChange`, the raw setter, which is the same shape as the known `ItemStatsPacket` thirst defect, so a split of a cooked food halves its thirst a second time.

## E — item modData reachability at eat time on the server

| member | signature | flags | exposed? | side | cite |
|---|---|---|---|---|---|
| `InventoryItem.getModData` | `()Lse/krka/kahlua/vm/KahluaTable;` | public | yes | both | `@0–@21 L427–L430` — returns the private `table` field, lazily creating it from `LuaManager.platform.newTable()` |
| `InventoryItem.table` | `Lse/krka/kahlua/vm/KahluaTable;` | **private** | via the getter only | — | same dump |
| `InventoryItem.hasModData` | `()Z` | public | yes | both | `@0–@24 L423` — true only when the table is non-null **and** non-empty, so it is a "has any keys" test, not a "was ever created" test |
| `InventoryItem.copyModData` | `(Lse/krka/kahlua/vm/KahluaTable;)V` | public | yes | both | `@0–@29 L2906–L2912` — wipes the item's table, returns early on a null source, else `LuaManager.copyTable(getModData(), source)` |
| `InventoryItem.CopyModData` | `(Lse/krka/kahlua/vm/KahluaTable;)V` | public | yes | both | `@0–@5 L2902–L2903` — capital-C alias delegating to the above |
| `LuaManager.copyTable` | `(KahluaTable;KahluaTable;)KahluaTable;` | — | — | both | `@35–@106 L1602–L1611` — iterates the source; a value that is itself a `KahluaTable` is **recursed** through `copyTable(null, nested)` and the fresh copy is rawset, otherwise the value is rawset directly. So the copy is deep |
| `Item.DoParam` default arm | `(Ljava/lang/String;Ljava/lang/String;)V` | public | yes | both | `@11832–@11890 L2993–L3002` — lazy-creates `Item.defaultModData`, then `rawset(key.trim(), Double.valueOf(Double.parseDouble(value)))`, falling back on `NumberFormatException` to `rawset(key.trim(), value)`. The `InvalidParameterException` at `@11898–@11919 L3005–L3006` is the outer catch for a *recognised* key with a bad value, not this arm |
| `Item.InstanceItem` modData copy | `(Ljava/lang/String;Z)Lzombie/inventory/InventoryItem;` | public | yes | both | `@3477–@3482 L1868` — unconditional `newItem.copyModData(this.defaultModData)` |
| `Food.multiplyFoodValues` | `(F)V` | public | yes | both | `@0–@156 L2288–L2303`, read end to end: fifteen `setX(getX() × f)` calls (`boredomChange`, `unhappyChange`, `hungChange`, `fluReduction`, `thirstChange`, `painReduction`, `foodSicknessChange`, `endChange`, `stressChange`, `fatigueChange`, `calories`, `carbohydrates`, `proteins`, `lipids`, `poisonPower`) and `return`. **No modData reference, no `extraItems`, no `spices`** — the body contains no `getModData`, no `KahluaTable` and no `table` getfield |

**Deep copy or shared reference?** Deep, per instance, recursively. `copyModData` calls `getModData()`, which creates a brand-new table for the instance, and `LuaManager.copyTable` then recurses into nested tables rather than aliasing them. A mod nutrient written as a script key therefore lands as a fresh per-instance value, and mutating it on one apple cannot reach the type default or another apple. The one caveat: `copyModData` **wipes** the instance table first, so anything a mod wrote onto an instance before `InstanceItem`'s copy step would be lost — but that step runs during construction, so in practice no mod code can precede it.

`getModData()` on an item with no script keys is not a no-op: it creates and caches an empty table, and `hasModData()` then still answers false. A census that uses `getModData()` to decide whether an item "has" mod data will therefore always see a table.

## F — fluid containers

### The fluid definition: no default arm, so no free unrecognised key

| member | signature | flags | exposed? | side | cite |
|---|---|---|---|---|---|
| `FluidDefinitionScript.Load` | `(Ljava/lang/String;Ljava/lang/String;)V` | public | yes (`FluidDefinitionScript` in exposer set) | both (scripts load per side) | value keys `displayName`, `colorReference`, `color` at `@124–@245 L279–L288`; sub-blocks `blendWhiteList`, `blendBlackList`, `categories`, `properties`, `poison` at `@386–@520 L309–L320`. **Default arms**: `@316–@348 L301–L303` (value) and `@523–@562 L322–L324` (block) — each logs `DebugType.General.error(...)` and, when `Core.debug`, throws `new Exception("FluidDefinition error.")`. Nothing is stored |
| `FluidDefinitionScript.LoadProperties` | `(Lzombie/scripting/ScriptParser$Block;)V` | **private** | no | both | fifteen `equalsIgnoreCase` keys, each `Float.parseFloat` into a `PropertyValue`; default arm at `@414–@449 L404–L406` — `DebugType.General.error(key, value, fullType)` then, under `Core.debug`, `throw new Exception("FluidDefinition error.")`. **No storage of the key** |

So there is **no** analogue of the item parser's default modData arm anywhere on the fluid path. A per-fluid mod nutrient cannot ride a fluid block; it must live in a Lua table the mod owns. The safe key is the `Fluid` object's own type string:

| member | signature | flags | exposed? | side | cite |
|---|---|---|---|---|---|
| `Fluid.getFluidTypeString` | `()Ljava/lang/String;` | public | yes (`Fluid` in exposer set) | both | `@0–@4 L336`; set non-null by **both** constructors — `Fluid.<init>(FluidType) @30–@35 L267` writes `fluidType.toString()`, `Fluid.<init>(String) @26–@34 L272` writes the modded name. This is *not* the same field as `FluidDefinitionScript.getFluidTypeString()`, which is null for the 27 built-ins (library #0654) |
| `Fluid.Get` | `(Ljava/lang/String;)Lzombie/entity/components/fluids/Fluid;` | public static | yes | both | member list (flags parsed) |
| `Fluid.getAllFluids` | `()Ljava/util/ArrayList;` | public static | yes | both | member list (flags parsed) |
| `Fluid.getProperties` | `()Lzombie/entity/components/fluids/SealedFluidProperties;` | public | yes (`SealedFluidProperties` also in exposer set) | both | member list — this is the **per-litre** block |
| `Fluid.getScript` | `()Lzombie/scripting/objects/FluidDefinitionScript;` | public | yes | both | member list |

### Reading the mix and the amounts on an instance

| member | signature | flags | exposed? | side | cite |
|---|---|---|---|---|---|
| `GameEntity.getFluidContainer` | `()Lzombie/entity/components/fluids/FluidContainer;` | public final | yes (`GameEntity` and `FluidContainer` both in exposer set) | both | member list (flags parsed); `InventoryItem extends GameEntity` (super-class read this session); the shipped Lua uses it at `ISDrinkFluidAction.lua:131` |
| `InventoryItem.getFluidContainerFromSelfOrWorldItem` | `()…FluidContainer;` | public | yes | both | member list |
| `FluidContainer.getAmount` | `()F` | public | yes | both | `@0–@8 L587–L588` — calls `recalculateCaches()` then returns `amountCache`; **litres** |
| `FluidContainer.getCapacity` / `getFilledRatio` | `()F` | public / public | yes | both | member list (flags parsed) |
| `FluidContainer.getPrimaryFluid` / `getPrimaryFluidAmount` | `()Fluid;` / `()F` | public | yes | both | member list |
| `FluidContainer.getRatioForFluid` | `(Fluid;)F` | public | yes | both | `@0–@44 L1160–L1165` — walks the private `fluids` list and returns that `FluidInstance.getPercentage()`, i.e. a **proportion**, 0 when absent |
| `FluidContainer.getSpecificFluidAmount` | `(Fluid;)F` | public | yes | both | `@0–@59 L773–@783` — 0 when empty or absent, else the matching instance's amount |
| `FluidContainer.createFluidSample` | `()FluidSample;` / `(F)FluidSample;` | public | yes (`FluidSample` in exposer set) | both | `@0–@8 L789` delegates to `createFluidSample(getAmount())`; `@0–@32… L798–L800` allocates a pooled `FluidSample` and adds each `FluidInstance` |
| `FluidContainer.isMixture` / `getProperties` | `()Z` / `()SealedFluidProperties;` | public | yes | both | member list — `getProperties()` is already litres-weighted (library #0630) |
| `FluidSample.size` / `getFluid(int)` / `getPercentage(int)` / `getAmount` / `getPrimaryFluid` / `release` | — | all public | yes | both | member list (flags parsed) — this is the per-fluid iteration route |
| `FluidInstance` | — | — | **no** — absent from the exposer class set (0 hits in the whole `exposeAll()` dump) | — | so Lua cannot hold a `FluidInstance`; iterate through a `FluidSample` instead |
| `FluidConsume` | — | `extends SealedFluidProperties` | yes | — | super-class read this session; its own members are only `getAmount`/`setAmount` and the poison effect, so it carries the **aggregate** nutrition of what was removed and **no per-fluid breakdown** |
| `IsoGameCharacter.DrinkFluid` | `(FluidContainer;FZ)Z` | public | yes | server on the live path | `@0–@100 L5873–L5881` writes the four macros from `container.getProperties() × f` into `Nutrition` before anything is removed; `@103–@140 L5883–L5885` computes tainted/bleach then `removeFluid(getAmount() × f, true)` → a `FluidConsume`; `@142 L5888` onward takes the stats from that. **No modData reference and no Lua call anywhere in the body** (grep of the whole 352-line 5-overload dump for `modData`, `LuaManager`, `triggerEvent`: nothing) |

So litres consumed by one `DrinkFluid` call is exactly `container.getAmount() × f` measured before the call, and the mix proportions must be sampled before the removal — `FluidConsume` does not carry them.

### The Lua driver: which method to wrap

`media/lua/shared/TimedActions/ISDrinkFluidAction.lua`:

- `:updateEat(delta)` — lines **109–120**. Computes `targetRatio = delta × self.targetConsumedRatio`, `consumedRatio = self.startRatio − fluidContainer:getFilledRatio()`, `ratioToConsume = targetRatio − consumedRatio`, `deltaToConsume = ratioToConsume / fluidContainer:getFilledRatio()`, then `self.character:DrinkFluid(self.item, deltaToConsume, self.useUtensil)` and `self.item:syncItemFields()`. This is the **only** call site of `DrinkFluid` in the shipped Lua.
- Callers: `:update()` line **29**, guarded `if not isClient()`; `:animEvent("drinkFluid")` line **45**, guarded `if isServer()`; `:complete()` line **105**, `self:updateEat(1)` **unguarded**.
- `:serverStart()` line 39 emits the `drinkFluid` anim event via `emulateAnimEvent`.
- Construction, lines 126–177, snapshots `startRatio`, `endRatio` and `targetConsumedRatio` from the container up front, and derives the duration from `fluidContainer:getProperties():getHungerChange()`.

A server-side wrapper of `ISDrinkFluidAction.updateEat` therefore runs once per incremental sip on the server. Before calling through it can read `self.fluidContainer:getAmount()` (litres), `createFluidSample()` (per-fluid proportions, released after use), `getPrimaryFluid()` and `isMixture()`; after calling through it can read `getAmount()` again, and the difference is the litres actually drunk. Because the driver is idempotent by construction — it consumes only the gap between the target ratio and what has already gone — a wrapper that accumulates per-call litres will sum to the container's whole consumed amount without double counting. `ISDrinkFromBottle` is not on this path at all (library #0670).

## G — absences, each proved by a jar-wide grep

Every row below is a `./pz.sh grep <string>` over all ~23.7k class entries; the toolchain's result cap is `--max 60` and no scan here came near it.

| search string | result | what it proves |
|---|---|---|
| `PassNutritionThroughFood` | no class contains that literal | the name the library's prose uses for the split arm is not in the jar in any form |
| `PassNutrition` | no class contains that literal | nor any shorter form of it |
| `NutritionThroughFood` | no class contains that literal | nor any suffix of it |
| `extraItems` | `InventoryItem.class`, `ItemStatsPacket.class`, `EvolvedRecipe.class` | the ingredient list is absent from `SyncItemFieldsPacket` (and from `Food.class`, which reaches it through the inherited getter) |
| `spices` | `InventoryItem.class`, `Food.class`, `ItemStatsPacket.class`, `EvolvedRecipe.class` | same for the spice list |
| `getSpices` | `Food.class`, `EvolvedRecipe.class` | no packet or save class calls the spice getter by name |
| `copyExtraItems` | `Food.class` | no Java class outside `Food` calls it; the only path in is `copyFoodFromSplit` |
| `copyNutritionFromRatio` | `Food.class` | **no Java caller anywhere**; combined with a `grep copyNutrition` over `media/lua` returning nothing, the method has no shipped caller at all |
| `copyNutritionFrom` | `Food.class` | same |
| `copyNutritionFromSplit` | `Food.class` | same |
| `modifyMeat` | `IsoAnimal.class` | no other Java class calls the Java overload; the shipped Lua's only `modifyMeat` hits are the Lua function `ButcheringUtil.modifyMeat`, so the Java method has no shipped caller outside `IsoAnimal` itself |
| `InheritFood` | `generation/CraftRecipeScriptGenerator.class`, `crafting/InputFlag.class`, `crafting/recipe/CraftRecipeData.class` | the split flag's whole footprint: one generator, the enum, one consumer |
| `extraItemsAmount` | no class contains that literal | no per-entry amount field on the ingredient list |
| `extraItemAmount` | no class contains that literal | same |
| `extraItemUses` | no class contains that literal | same |
| `extraItemsHunger` | no class contains that literal | same |
| `ingredientAmount` | no class contains that literal | same |
| `OnEvolvedRecipe` | no class contains that literal | no Lua event name for the evolved summation |
| `OnAddItemInRecipe` | no class contains that literal | same |
| `luaCallOnCreate` | `CraftLogicSystem.class`, `DryingLogicSystem.class`, `FurnaceLogicSystem.class`, `CraftRecipeData.class` | the craft `OnCreate` dispatch has exactly three Java callers, all entity logic systems; the hand-craft path calls it from Lua instead |

Two non-grep absences, each from a member list read whole:

- `zombie/scripting/objects/Item` declares **no** `getCalories`, `getCarbohydrates`, `getLipids` or `getProteins`; the four fields are private. A mod cannot read a type's script macros off `getScriptItem()`.
- `zombie/entity/components/fluids/FluidContainer` declares **no** `getFluids()`; the `fluids` field is `private final`. Per-fluid iteration goes through `createFluidSample()`.

Three exposure absences, from the whole `LuaManager$Exposer.exposeAll()` dump read end to end: `FluidInstance`, `InventoryItemFactory`, and both packet classes (`ItemStatsPacket`, `SyncItemFieldsPacket`) are not in the exposer's class set.

## Claims candidates

Each line is worded as a claim, grade **C**, bound **C-only** (a static bytecode read of one jar of build 42.20.4 / `b0bbce05d5`; nothing below was measured on a live session).

1. An evolved dish's ingredient list is `InventoryItem.extraItems`, an `ArrayList` of ingredient **full types** with no amount, appended once per add — `jar:InventoryItem.addExtraItem @0–@27 L3136–L3141`; `jar:InventoryItem.getExtraItemsWeight @24–@69 L3158–L3164`.
2. `EvolvedRecipe.addItem` appends the ingredient's full type to the dish's `extraItems` after the whole macro transfer and only on the non-spice branch — `jar:EvolvedRecipe.addItem @1757–@1766 L463–L465`.
3. A spice is appended to a second list, `Food.spices`, also as a full type, and the spice branch returns before the ingredient append — `jar:EvolvedRecipe.useSpice @9–@38 L617–L620`; `jar:EvolvedRecipe.addItem @1721–@1755 L459–L461`.
4. `extraItems` is saved behind bit flag 32 as a count plus one registry short id per entry, and loaded back through `WorldDictionary.getItemTypeFromID` — `jar:InventoryItem.save @435–@511 L1662–L1665`; `jar:InventoryItem.load @632–@686 L1956–L1959`.
5. `Food.spices` is saved behind bit flag 256 as a byte count plus one written string per entry — `jar:Food.save @416–@483 L990–L995`; `jar:Food.load @522–@568 L1195–L1199`.
6. `ItemStatsPacket` carries both lists — `extraItems` behind flag 4194304 and `spices` behind flag 8388608, each as a **byte** count plus UTF strings — and the receiver clears each list before the flag test, so neither can carry a stale value — `jar:ItemStatsPacket.setData @413–@468 L205–L211`; `jar:ItemStatsPacket.write @654–@787 L333–L345`; `jar:ItemStatsPacket.parse @546–@649 L445–L456`; `jar:ItemStatsPacket.applyItemStats @282–@318 L556–L560, @351–@387 L565–L569`.
7. `SyncItemFieldsPacket` carries neither list: a jar-wide grep for `extraItems` returns only `InventoryItem`, `ItemStatsPacket` and `EvolvedRecipe`, and for `spices` adds only `Food` — `jar:jar-wide grep extraItems`; `jar:jar-wide grep spices`.
8. The dish records the ingredient's type and the number of times it was added, and records nothing about the hunger it contributed: the per-ingredient hunger is consumed into the dish's `hungChange` and never stored, and no per-entry amount identifier exists in the jar — `jar:EvolvedRecipe.addItem @518–@545 L333`; `jar:jar-wide grep extraItemsAmount`, `extraItemAmount`, `extraItemUses`, `extraItemsHunger`, `ingredientAmount`.
9. `extraItems` is keyed by `getFullType()` while `EvolvedRecipe.getItemsList()` is keyed by `getType()`, so joining the dish's list to the recipe's `use` values needs a module strip — `jar:EvolvedRecipe.addItem @463–@471 L331`; `jar:InventoryItem.addExtraItem @0–@27 L3136–L3141`.
10. `EvolvedRecipe.addItem` writes exactly one item-modData key, and only when the base item is a `HandWeapon`: the base's condition ratio rawset under the base's own type name — `jar:EvolvedRecipe.addItem @125–@166 L282–L284`.
11. An evolved dish is a fresh instance built from its result type, so it receives that type's default modData and nothing from the base item's or the ingredients' modData — `jar:EvolvedRecipe.addItem @37–@44 L271`; `jar:Item.InstanceItem @3477–@3482 L1868`.
12. `EvolvedRecipe.addItem` calls no Lua function and fires no event: its whole body holds one Kahlua reference, the HandWeapon rawset, and no `LuaManager.caller`, `getFunctionObject` or `triggerEvent` — `jar:EvolvedRecipe.addItem @0–@1928 L265–L487 (whole body)`; `jar:jar-wide grep OnEvolvedRecipe`; `jar:jar-wide grep OnAddItemInRecipe`.
13. `ISAddItemInRecipe:complete` is the sole Lua bridge into the evolved summation and calls `recipe:addItem(baseItem, usedItem, character)` with a server-gated `sendItemStats` on both items after it, so a server-side wrapper of it sees ingredient and dish together — `lua:media/lua/shared/TimedActions/ISAddItemInRecipe.lua:66-88`.
14. The craft split flag is `InputFlag.InheritFood`, and `PassNutritionThroughFood` does not exist in the jar in any form — `jar:CraftRecipeData.createOutputItems @1096–@1143 L1542–L1544`; `jar:jar-wide grep PassNutritionThroughFood`.
15. The `InheritFood` arm calls `output.copyFoodFromSplit(input, OutputScript.getIntAmount())`, which copies nutrition at `1/amount`, plus frozen, cooked/burnt, temperature, poison, age and the input's `extraItems` and `spices`, and no modData — `jar:CraftRecipeData.createOutputItems @1135–@1143 L1544`; `jar:Food.copyFoodFromSplit @0–@33 L2704–L2710`.
16. `Food.copyNutritionFromRatio` multiplies nine fields — `baseHunger`, `hungChange`, the four macros, `unhappyChange`, `thirstChange`, `boredomChange` — and touches no modData and no item list — `jar:Food.copyNutritionFromRatio @0–@87 L2677–L2685`.
17. `Food.copyNutritionFromRatio` reads the cooked-ladder thirst getter and writes through the raw setter, so a split of a cooked food halves its thirst a second time — `jar:Food.copyNutritionFromRatio @70–@77 L2684`.
18. `Food.copyExtraItems` copies the ingredient list entry by entry but assigns the spice list by reference, so a split output and its input share one spice `ArrayList` — `jar:Food.copyExtraItems @0–@64 L2693–L2699`.
19. Craft output creation refuses to run on a client: `createOutputsInternal` throws `RuntimeException("Cannot call with testOnly==false on client.")` — `jar:CraftRecipeData.createOutputsInternal @0–@20 L784–L785`.
20. The craft `OnCreate` hook receives the `CraftRecipeData` object and the character, and fires after the outputs are created — `jar:CraftRecipeData.luaCallOnCreate @8–@32 L471–L473`; `jar:CraftLogicSystem.stop @39–@52 L182–L183`.
21. `CraftRecipeData` exposes the consumed and created instances to Lua through `getAllConsumedItems`, `getAllRecordedConsumedItems`, `getFirstInputItemWithFlag` and `getAllCreatedItems`, all public on a class in the exposer set — `jar:CraftRecipeData.getAllConsumedItems @0–@95 L2220–L2235`; `jar:CacheData.addAppliedItemsToList @0–@8 L1868–L1869`; `jar:LuaManager$Exposer.exposeAll() dump`.
22. The shipped hand-craft Lua already writes a consumed-full-type-to-count map into a single output's item modData right after `OnCreate`, which is the propagation shape a mod nutrient can reuse — `lua:media/lua/shared/Entity/TimedActions/ISHandcraftAction.lua:221-249`.
23. A second craft summation exists in Java: `RecipeCodeOnCreate.copyFoodValuesFromList` sums the consumed foods' `baseHunger` and four macros onto the first created item, skipping spices unless the item is fish roe, and touches no modData — `jar:RecipeCodeOnCreate.copyFoodValuesFromList @0–@166 L420–L436`; `jar:RecipeCodeOnCreate.makeOmelette @0–@8 L416`.
24. `IsoAnimal.modifyMeat` is `public static` and scales hunger, calories, lipids and proteins by `f1 × f2 ×` an **independent** `Rand.Next(0.9, 1.1)` per field, leaving carbohydrates untouched, and sets `baseHunger` from the state-modified hunger getter — `jar:IsoAnimal.modifyMeat @0–@93 L3859–L3863`.
25. The Java `modifyMeat` has no shipped caller: a jar-wide grep returns only `IsoAnimal.class` and the shipped Lua's only `modifyMeat` hits are the Lua function `ButcheringUtil.modifyMeat` — `jar:jar-wide grep modifyMeat`; `lua:media/lua/shared/Definitions/animal/ButcheringUtil.lua:332,393,426`.
26. The live butchering scale is Lua: `ButcheringUtil.modifyMeat` applies `size × meatRatio × hungerBoost` to hunger and all **five** nutrition columns, each with its own `ZombRandFloat(0.9, 1.1)` — `lua:media/lua/shared/Definitions/animal/ButcheringUtil.lua:426-447`.
27. The butcher scale factor is therefore recoverable from a meat instance only per field and only to within about ±11 per cent of the shared ratio, because each field carried an independent jitter draw — `lua:media/lua/shared/Definitions/animal/ButcheringUtil.lua:438-443`; `jar:IsoAnimal.modifyMeat @0–@93 L3859–L3863` (inference; the arithmetic is the part a re-reader redoes).
28. The script hunger value is recoverable from an instance because `InstanceItem` writes both `hungChange` and `baseHunger` as `script.hungerChange / 100` and the script getter is public — `jar:Item.InstanceItem @559–@582 L1559–L1560`; `jar:Item.getHungerChange @0–@4 L555`.
29. The script's four macros are **not** readable through `getScriptItem()`: `Item.calories`, `carbohydrates`, `lipids` and `proteins` are private fields and `Item` declares no getter for any of them, so a per-type macro must be read off a fresh instance through the `instanceItem` global — `jar:Item` member list and constant-pool flags; `jar:LuaManager$GlobalObject.instanceItem(String) @0–@4 L4928`.
30. `InventoryItem.getModData()` is public on an exposed class and lazily creates the instance's own table, while `hasModData()` answers false for a created-but-empty table — `jar:InventoryItem.getModData @0–@21 L427–L430`; `jar:InventoryItem.hasModData @0–@24 L423`.
31. An unrecognised key in an `item` block is rawset into the script's `defaultModData` as a `Double` when it parses as one and as the raw string otherwise — `jar:Item.DoParam @11832–@11890 L2993–L3002`.
32. Every instance receives a deep, recursive, per-instance copy of its type's default modData rather than a shared reference: `InstanceItem` calls `copyModData`, which wipes the instance table and runs `LuaManager.copyTable`, which recurses into nested tables — `jar:Item.InstanceItem @3477–@3482 L1868`; `jar:InventoryItem.copyModData @0–@29 L2906–L2912`; `jar:LuaManager.copyTable @35–@106 L1602–L1611`.
33. `Food.multiplyFoodValues` touches no modData, no `extraItems` and no `spices`: its whole body is fifteen field multiplications and a return — `jar:Food.multiplyFoodValues @0–@156 L2288–L2303 (whole body)`.
34. A fluid block has no default arm: an unrecognised value key or sub-block is logged as a `DebugType.General` error and throws under `Core.debug`, and nothing stores it — `jar:FluidDefinitionScript.Load @316–@348 L301–L303`; `jar:FluidDefinitionScript.Load @523–@562 L322–L324`.
35. A fluid's `properties` block has no default arm either: an unrecognised property key is logged as an error and throws under `Core.debug`, and is not stored — `jar:FluidDefinitionScript.LoadProperties @414–@449 L404–L406`.
36. A per-fluid mod nutrient must therefore live in a mod-owned Lua table keyed by `Fluid.getFluidTypeString()`, which both `Fluid` constructors set non-null — unlike the script object's same-named getter — `jar:Fluid.<init>(FluidType) @30–@35 L267`; `jar:Fluid.<init>(String) @26–@34 L272`; `jar:Fluid.getFluidTypeString @0–@4 L336`.
37. A container's mix is readable from Lua through `createFluidSample()` plus `FluidSample.size/getFluid(i)/getPercentage(i)/getAmount`, and `FluidContainer` declares no `getFluids()` while `FluidInstance` is absent from the exposer's class set — `jar:FluidContainer.createFluidSample @0–@8 L789`; `jar:FluidContainer` member list; `jar:LuaManager$Exposer.exposeAll() dump`.
38. `FluidContainer.getRatioForFluid` returns a proportion and `getSpecificFluidAmount` returns litres, both by walking the private `fluids` list — `jar:FluidContainer.getRatioForFluid @0–@44 L1160–L1165`; `jar:FluidContainer.getSpecificFluidAmount @0–@59 L773–L783`.
39. One `DrinkFluid` call removes exactly `container.getAmount() × f` litres, writes the four macros from the litres-weighted container properties before the removal, and touches no modData and no Lua hook — `jar:IsoGameCharacter.DrinkFluid(FluidContainer,float,boolean) @0–@140 L5873–L5885`.
40. `FluidConsume extends SealedFluidProperties` and carries the removed aggregate's nutrition with no per-fluid breakdown, so a mod must sample the mix before the removal — `jar:FluidConsume` super-class read; `jar:FluidConsume` member list.
41. `ISDrinkFluidAction.updateEat` is the only shipped call site of `DrinkFluid`, is reached from `update` when not a client, from the `drinkFluid` anim event when a server, and unguarded from `complete`, and is idempotent because it consumes only the gap between the target ratio and what has already gone — `lua:media/lua/shared/TimedActions/ISDrinkFluidAction.lua:26-48,104-120`.
42. `InventoryItemFactory` is absent from the exposer's class set, so a mod reaches item construction through the `instanceItem` global rather than the factory — `jar:LuaManager$Exposer.exposeAll() dump`; `jar:LuaManager$GlobalObject.instanceItem(String) @0–@4 L4928`.

## Not read

- **Whether the consumed input instances still hold their pre-craft macros at `OnCreate` time.** `consumeInputsInternal` runs before `createOutputs`, and a use-spend scales a drainable food's macros, so an input read in `OnCreate` may already be partially drained. Neither `consumeInputsInternal` nor `processDestroyAndUsedItems` was dumped. Settled by one dump of each, or by a live read inside an `OnCreate` handler.
- **Which side `ISAddItemInRecipe:complete` and `ISHandcraftAction:performRecipe` actually run on, on a dedicated server.** The bodies are side-agnostic; only the `isServer()`-gated `sendItemStats` and the `createOutputsInternal` client throw hint at it. This is a run question, not a jar question.
- **The element type of `CacheData.appliedItems`.** The field descriptor is a type-erased `ArrayList`; the shipped Lua treats the elements as `InventoryItem` (`item:getFullType()`), and `InputScriptData.getFirstInputItem()` returns `InventoryItem`, which is corroboration rather than proof.
- **The spice branch of the evolved summation beyond `useSpice`.** The private `useSpice(Food,Food,FI,IsoGameCharacter)` overload was not dumped; only the `(InventoryItem,Food,II,IsoGameCharacter)` one. This is the library's existing open row #0381.
- **Whether `EvolvedRecipe.addItem` can be called from Lua on an arbitrary base item** — the method is public on an exposed class, but nothing here tested a Lua call or its arity resolution.
- **How `FluidSample` pooling behaves under a mod that forgets `release()`.** `FluidSample.Alloc` is a pool and `release()` exists; the pool's own size and failure mode were not read.
- **`FluidContainer.save`/`load`/`saveSyncData`/`loadSyncData`** — whether and how the mix crosses the wire on its own packets, as opposed to riding `SyncItemFieldsPacket`'s `fluidContainer` field. Not dumped.
- **`DryingLogicSystem` and `FurnaceLogicSystem`** — the two other Java callers of `luaCallOnCreate`; their ordering relative to output creation was not read, only `CraftLogicSystem.stop`'s.
- **`Item.DoParam(String)`** — the single-argument overload; only the two-argument one was dumped, so a valueless unrecognised key's fate is unread.
- Nothing here was measured on a live session, so every "side" column entry is a bytecode-readable gate rather than an observation of which process reached it.
