# Datasets
Verified against 42.20.4 (b0bbce05d5) · 2026-09-26 · scope: the committed datasets under `data/` — the column authority, the four item kinds, every dated count, the mod-inventory snapshot and its partial-view caveat, the workshop rows and the CSV and JSON schemas; how far a dataset matches the running game is `facts/`, and the scanners that write the datasets are `reference/tools.md`.

<a id="columns"></a>
## Columns

The generated datasets are `data/food-items.*`, `data/recipes.*` and `data/evolved-recipes.*`, each a CSV and JSON pair read off the `42.20.4` scripts and never hand-edited; `data/mod-inventory.json` and `data/workshop-search.*` are dated snapshots of a live tree and a live website, whose columns are [Mod inventory](#mod-inventory) and [Workshop rows](#workshop-rows).
This section is the column authority for the generated three: what the load-bearing columns mean, which are derived and which are read, and how absence is written.
The full column lists, one table per file, are [Schemas](#schemas); the scanners that write the files are [`food_scan.py`](tools.md#food-scan) and [`recipe_scan.py`](tools.md#recipe-scan).

### Food items

The food dataset's eleven derived columns — `nutrition_basis`, `fluid_share`, `fluid_fill_litres`, `fluid_pick_random`, `drinkable` and the six `*_per_container` — are arithmetic on scanned constants, and every other value is a line in a shipped file whose record names its `source_file` and `source_line`, in the 2026-09-10 scan of the `42.20.4` install (jar `b0bbce05d5`) [#0601/C/snapshot].

Read the nutrition basis before reading a nutrition column: an item's food keys are per item while a fluid's properties are per litre, a drink row's nutrition is joined from a fluid, every row says which unit it is in, and summing a nutrition column across kinds without looking at the basis is wrong by the capacity factor [#1881].

`nutrition_source` is derived and says where a row's nutrition came from — the item's own food keys, a named fluid, or nothing at all — while `nutrition_basis` says which unit the fourteen nutrition columns are in: per item, per litre, or empty for the 280 rows that name no source, in the 2026-09-10 scan of `42.20.4` [#1884/C/snapshot].
Carrying no nutrition value is a wider set than naming no source, by the ten fluid-sourced rows joined to a fluid with no `Properties` block or with only an `alcohol` line; the dated total is [Counts](#counts) [#1884/C/snapshot].
In the 2026-09-10 scan, 653 rows fill their nutrition columns from their own script keys (`nutrition_source = food_keys`, `nutrition_basis = per_item`) and 280 name no nutrition source at all — 78 food, 141 drainable and 61 empty containers [#0622/C/snapshot].
In the 2026-09-10 scan, 72 rows are containers whose nutrition columns are the first listed fluid's `Properties` and are therefore per litre (`nutrition_source = fluid:<id>`, `nutrition_basis = per_litre`) [#0623/C/snapshot].

The fluid join takes the first fluid a container lists: the source becomes that fluid, the basis becomes per litre, and the fourteen nutrition columns come from that fluid's `Properties` block instead of the item's own keys [#1886/C/snapshot].
`nutrition_source` is `fluid:<id>` whenever a first fluid exists, even when that fluid writes no `Properties` block (10 of the 61), and no fluid-container item in `42.20.4` writes a nutrition key of its own, so the join never overwrites an item value, in the 2026-09-10 scan [#0626/C/snapshot].
A fluid-sourced row with empty nutrition is therefore a correct row and not a gap, and three fluid properties — `alcohol`, `fluReduction` and `painReduction` — have no column and stay in the fluid record's `properties_raw`, on build `42.20.4` as scanned 2026-09-10 [#1886/C/snapshot].

A fluid's properties are the effect of one litre, so the joined columns on a container row are in a different unit from the same columns on a food row; the chain below is a jar read on `42.20.4` whose arithmetic the drink probe measured ([food-item-model.md](../facts/food-item-model.md#dataset-fidelity)) [#1891/C/C-only]:

- **The loader stores the script value as written.** `FluidDefinitionScript.LoadProperties` parses each of the fifteen keys with `Float.parseFloat` and no arithmetic.
- **The container multiplies by its litres.** `FluidContainer.recalculateCaches` does `propertiesCache.addFromMultiplied(fluid.getProperties(), litres)`, so `FluidContainer.getProperties()` is already litres-weighted.
- **Drinking spends that aggregate.** `IsoGameCharacter.DrinkFluid` writes `nutrition.setX(getX() + fc.getProperties().getX() * f)`, with `f` the share of the contents drunk — so a full container drunk to the bottom delivers exactly columns 52–57.
- **The litres are the full container's.** `getInitialAmount()` defaults to `Capacity` when the script writes no initial amount, `addInitialFluid` multiplies it by the share and `addFluid` clamps it to the capacity — which is `fluid_fill_litres`. 14 containers **do** write one, and spawn part-filled: see the caveat below.

Units are script units on both sides, so an item's and a fluid's hunger and thirst numbers are directly comparable and both become stat-bar units by dividing by one hundred: the hundredfold division is not applied in the dataset for a fluid or for an item, and the unhappiness, food-sickness, alcohol, flu-reduction and pain-reduction values are unscaled on both sides as well, as read on one build [#1893].
The dataset applies the ÷100 on neither side: a fluid's `HungerChange` and an item's are both stored raw, so a Cola can's `hunger_change_per_container` of −3.6 is directly comparable to an apple's `hunger_change` of −16 and both become stat-bar units by dividing by 100 [#0638].
A fluid row's `unhappy_change` is applied twice when drunk, once to boredom and once to unhappiness, so a mood delta off this dataset is twice the column times `fluid_fill_litres`, a jar read on `42.20.4` [#1895/C/C-only].
`endurance_change` carries a latent unit trap between an item row and a fluid row, which [eating-pipeline.md](../facts/eating-pipeline.md#fluid-path) owns [#0666/C/snapshot].

Three fill columns are derived: the share (`fluid_share`) is the first fluid line's second field, or one when the line writes only an id, and the fill in litres (`fluid_fill_litres`) is `fluid_capacity` times that share clamped to the capacity, which equals the capacity on all 72 filled rows on `42.20.4` [#1887/C/snapshot].
Every share on that build is one except a single debug bucket's ten, in the 2026-09-10 scan [#1887/C/snapshot].
The six `*_per_container` columns are the per-litre value multiplied by `fluid_fill_litres`, so they are the nutrition of a full container and not of a spawned one; they are empty on every row that is not a container and on a container whose fluid writes no such key, because multiplying a key that was never written is still nothing and not zero [#1888/C/arith.].
That derivation is stated with its arithmetic per column in the food CSV table under [Schemas](#schemas) [#1888/C/arith.].
`drinkable` is derived from a capacity threshold of three litres (`fluid_capacity <= 3.0`), which is the gate the inventory context menu puts on the drink option, and sixteen of the 133 containers fail it and can only be poured or emptied, in the 2026-09-10 scan of `42.20.4` [#1889/C/snapshot].

In the 2026-09-10 scan, 14 of the 133 `component FluidContainer` blocks also write `InitialPercentMin` and `InitialPercentMax` and spawn part-filled; twelve of the fourteen list a fluid, and the scanner models none of them, so `fluid_fill_litres` is always a full container's figure [#0658/C/snapshot].
The fill-litres column is a full container and fourteen containers spawn part-filled: the two initial-percent keys are read into an amount range, and the initial amount returns the minimum when the two are equal and a uniform draw otherwise, rolled once per container before the share multiply and the capacity clamp — and the value is litres and not a percentage despite the key name, since nothing multiplies it by the capacity [#1897/C/C-only].
That is a jar read on `42.20.4`; the scanner does not model the draw, so on those rows `fluid_fill_litres` and the six per-container columns are the full-container figures [#1897/C/C-only].

Five containers list several different fluids and the row carries only the first's — `Base.Flask`, `Base.PopBottle`, `Base.PopBottleRare`, `Base.SodaCan` and `Base.WaterBottle`, with `Base.Flask` reporting Gin's 2 630 kcal though the same flask can hold Rum, Scotch, Vodka or Whiskey — while `fluid_ids` keeps the whole set, in the 2026-09-10 scan [#0656/C/snapshot].
A pick-random container's nutrition is one of several fills and not the whole truth: the component draws one of the listed fluids when the random flag (`PickRandomFluid`) is set and fills with every listed fluid when it is not, nine containers set it, five of those list several different fluids, and the row carries only the first one's nutrition — so anything that averages or worst-cases a spawn must do it from the whole fluid set the row keeps, not from the row [#1898/C/C-only].
That is a jar read on `42.20.4`, and the other four multi-line containers repeat a single id and so have nothing to pick between [#1898/C/C-only].

An absent script key is the empty string in the CSV and `null` in the JSON, never a zero, and a script that really writes zero still prints zero; absence is load-bearing, because the engine's own defaults are not zero for every key [#1883, #0618].
The JSON also distinguishes `null` (a row that is not a container) from an empty list (a container listing no fluid), where the CSV writes an empty cell for both [#0618].
An absent `Properties` key means the engine uses zero and not unknown, because the fluid definition registers all fifteen properties at zero on construction — but the dataset still reports it empty, because no line in the file wrote it; a fluid with no `Properties` block at all gets a null properties object and contributes nothing to anything, a jar read on `42.20.4` [#1896/C/C-only].

The item-level script-key union over `items/food.txt` and `items/drainable.txt` is exactly the 114 documented keys, with 0 unknown, in the 2026-09-10 scan; that holds over those two files only, and 60 further keys ride along on fluid-container items in the other files [#0605/C/snapshot].
`meta.unknown_keys` is 60 and is a scope statement rather than a defect: 50 are item keys outside the 114-key union riding along on fluid-container items in `normal.txt`, `weapon.txt`, `clothing.txt` and `container.txt`, and the other ten are `Capacity`, `fluid`, `PickRandomFluid`, `DisplayName`, `ColorReference`, `Categories` and the four fluid-only property shapes, in the 2026-09-10 scan [#0673/C/snapshot].

Every item record carries `id`, `module`, `name`, `display_name`, `display_category`, `food_type`, `item_type` and `tags`, and 6 ids have no EN display name, in the 2026-09-10 scan [#0606/C/snapshot].
Display names come from `EN/ItemName.json` (4 889 entries keyed `Module.Name`) and `EN/Fluids.json` (197 entries keyed `Fluid_Name_<id>`), as shipped with `42.20.4` and read 2026-09-10 [#0644/C/snapshot].
The discriminating control for an unresolved display name is the translation table: six base-module foods are absent from the 4 889-entry vanilla item-name table and carry a null display name in the dataset, while the control item (`Base.Steak`) is present in it, in the 2026-09-10 sweep [#1430/C/snapshot].

### Recipes

Every value in `data/recipes.*` and `data/evolved-recipes.*` is a line in a shipped file named by the record's `sourceFile` and `sourceLine`, and every craft `delta`, every `at0` and `at10` contribution and every `replacements[].delta` is arithmetic on those values resting on one measured input-amount rule, in the 2026-09-10 scan of the `42.20.4` install (jar `b0bbce05d5`) [#0676/C/snapshot].

An input amount is a count of uses and not of items unless the line carries an item-count flag (`flags[ItemCount]`), and for a food one use is one raw hunger-change point — so a forty-use line on one food is one whole tub (`item 40 [Base.MincedMeat]`) and a ten-use line on another is a third of one (`item 10 [Base.Icecream]`) [#1901].
The rule's measured half is the use probe that [cooking-and-recipes.md](../facts/cooking-and-recipes.md#uses) owns [#1901].
A recipe's `nutrition_delta` is the sum of the outputs times their own script macros minus the sum of what each consumed input line really spends, per macro, over calories, carbohydrates, lipids, proteins, `hungerChange` and `thirstChange` [#0698].
A delta term is taken only from a row whose `nutrition_basis` is `per_item`: a `per_litre` row contributes `fluid-sourced` and an empty basis `no-nutrition`, so the dataset never adds a per-litre number to a per-item one [#0717].
A drink and a row with no nutrition key are refused by name in `deltaReason` and never converted, so the two units are never added together, and the refusal is recorded per recipe with the blocker that fired [#1902].
Fluid IO lines are recorded verbatim and excluded from the macro delta because a fluid's nutrition is per litre, and the 53 recipes carrying fluid IO are flagged `fluidIO`, in the 2026-09-10 scan [#0697/C/snapshot].

A delta is refused rather than guessed: the record carries `delta: null` and a machine-readable `deltaReason` naming the offending lines verbatim, the blocker kinds being `tags-only`, `multi-type`, `wildcard`, `variable-amount`, mapper-shaped outputs, `no-outputs`, `not-in-dataset`, `no-nutrition` and `fluid-sourced`; 938 of the 969 recipes are refused and 31 resolve, in the 2026-09-10 scan [#0715/C/snapshot].
The `delta*` columns are empty and never zero when `deltaReason` says why, and `deltaAbsentMacros` names every term that summed as zero because that block writes no such line — so the null-for-zero substitution is never silent, over nine named blockers and 969 recipes [#1904/C/arith.].
A resolvable row that writes no line for one macro sums that macro as 0 and names it in `delta.absentMacros`, so a zero always stays readable as measured, absent or substituted [#0716].
The destroyed-waste block (`destroyWaste`) is null unless one of its six macros is non-zero, and no recipe on `42.20.4` publishes one: the single round-up row wastes a drainable that writes no macro key at all, so six zeroes would read as a measured zero destroyed, in the 2026-09-10 scan [#1908/C/snapshot].

An output `mapper:<name>` resolves to every key of that mapper except the literal `default` [#0696].
A bracketed type list splits on semicolons and an entry may carry a per-alternative count, as `2:Base.BurlapPiece` does in `SewFootwrap`: 86 such prefixes over 68 distinct pairs in the 2026-09-10 scan, with the count kept readable in the line's `raw` [#0693/C/snapshot].
`variable[<min>:<max>]` amounts appear on 66 lines over 33 recipes in the 2026-09-10 scan, all of them drying racks and on both sides of each recipe, and the dataset writes the amount as `null` with a `variable` range and refuses the delta [#0691/C/snapshot].

The top-level key census of the 969 `craftRecipe` blocks runs to 19 keys, 13 of them declared columns from `time` at 969 down to `Tooltip` at 38 and 6 landing untyped in the record's `props`, from `overlayStyle` at 34 down to `ResearchAny` at 1, in the 2026-09-10 scan [#0684/C/snapshot]:

| Fact | Value |
|---|---|
| top-level keys, by how many of the 969 blocks write them | `time` 969, `Tags` 969, `category` 935, `timedAction` 889, `xpAward` 560, `SkillRequired` 458, `NeedToBeLearn` 385, `AutoLearnAll` 160, `OnCreate` 146, `AutoLearnAny` 126, `AllowBatchCraft` 112, `MetaRecipe` 72, `Tooltip` 38 — each a declared column — then `overlayStyle` 34, `OnTest` 20, `recipeGroup` 9, `Icon` 4, `ResearchSkillLevel` 2, `ResearchAny` 1, which land untyped in the record's `props` |

### Evolved recipes

On all 6 881 evolved-recipe ingredient rows the consumption share at Cooking 10 (`share10`) is exactly seven tenths of the level-zero share (`share0`), with no exceptions including the 59 clamped rows — the clamp is what makes the relation hold, because it caps the hunger asked for at the ingredient's own hunger change before the skill reduction [#1911/C/arith.].
That is arithmetic over script values in the 2026-09-10 scan of `42.20.4`, the summation itself cited from [cooking-and-recipes.md](../facts/cooking-and-recipes.md#evolved) rather than re-derived [#1911/C/arith.].
A spice ingredient row is a measured zero in hunger, share and every macro, the branch being modelled, where a null in these datasets means the source writes nothing; the one summation branch not modelled per row is the rotten ingredient at Cooking 7 and above, which needs an instance's state rather than script data, in the 2026-09-10 scan [#1912/C/snapshot].
The `cookable` flag in the evolved-recipe dataset is the script value while the game's own `isCookable()` answers on the presence of the key, so one of the 63 recipes (`AddBaitToChum`) writes false here and the engine says true — the only one where the two differ, in the 2026-09-10 scan [#1913/C/snapshot].

<a id="kinds"></a>
## Kinds

The food dataset's selection rule is four buckets with first match winning — every base-food item, every base-drainable item, every item owning a fluid-container component and every fluid definition — and because the three item rules are disjoint on `42.20.4` the flat file has 1 005 rows, fluids being joined into those rows and kept whole in the JSON rather than given rows of their own; the ordering is a guard against a mod rather than a live tie-break, in the 2026-09-10 scan [#1882/C/snapshot]:

| kind | rule | count |
|---|---|---|
| `food` | every `item` in `items/food.txt` with `ItemType = base:food` | 722 |
| `drainable` | every `item` in `items/drainable.txt` with `ItemType = base:drainable` | 150 |
| `fluid_container` | every `item` in any `items/*.txt` owning a `component FluidContainer` | 133 |
| `fluid` | every `fluid` in `fluids.txt`, `fluids_Alcoholic.txt`, `fluids_Beverages.txt` | 61 |

`food_scan.select` applies the four rules with first match winning; the three item rules are disjoint on `42.20.4` only, so the ordering never fires there, and it is still enforced and covered by a synthetic fixture because a mod can break it, as scanned 2026-09-10 [#0610/C/snapshot].
The `food` bucket is every `item` block in `items/food.txt` (15 525 lines) whose `ItemType` is `base:food` — 722 records in the 2026-09-10 scan — and that file is the only one in the install holding such a block [#0611/C/snapshot].
The `drainable` bucket is every `item` block in `items/drainable.txt` (2 420 lines) whose `ItemType` is `base:drainable` — 150 records in the 2026-09-10 scan, of which only `Base.Vinegar2` and `Base.Vinegar_Jug` carry a `Calories` line, both `0.0` [#0612/C/snapshot].
The `fluid_container` bucket is every `item` block in any of the 15 `items/*.txt` owning a `component FluidContainer` — 133 records in the 2026-09-10 scan, 125 in `normal.txt`, 4 in `clothing.txt`, 2 in `container.txt`, 2 in `weapon.txt` and none in `food.txt` or `drainable.txt` [#0613/C/snapshot].
That count is a code read only: the script `Item` exposes no component accessor, so it has no live census route [#0613/C/snapshot].
The `fluid` bucket is every `fluid` block in `fluids.txt` (20), `fluids_Alcoholic.txt` (18) and `fluids_Beverages.txt` (23) — 61 definitions over 465 / 646 / 740 lines in the 2026-09-10 scan, 51 of them carrying a `Properties` block and 44 a `Calories` line [#0614/C/snapshot].
`ItemType.toString()` returns the `ResourceLocation` form `base:food` on this build, and the census records it raw in `byType`, so a registry rename would be visible rather than silently zeroing a bucket — measured on two boots of the default fixture on `42.20.4`, the second of which left no committed artifact [#0616/M/n=2].

<a id="counts"></a>
## Counts

Every count below is stated with the stamp of the scan it rests on, and a re-scan mints a successor row rather than editing a number; the corpus counts carry their sweep stamps at [Mod inventory](#mod-inventory) and the Workshop counts theirs at [Workshop rows](#workshop-rows).

### Food items

`data/food-items.json` holds 1 005 item records and 61 fluid records, built from 18 shipped files under `media/scripts/generated/`, in the 2026-09-10 scan of `42.20.4` (jar `b0bbce05d5`) [#0602/C/snapshot].
A `module Base` food pass covers 722 `base:food` items, or 1 005 records once drainables and fluid containers are counted — one census of `42.20.4` on 2026-09-10, with mod-added foods outside a `module Base` pass [#1228/M/n=1].
`media/scripts/generated/items/food.txt` holds 722 `base:food` blocks over 15 525 lines and `drainable.txt` holds 150 `base:drainable` blocks over 2 420 lines, as shipped and read 2026-09-10 [#0216/C/snapshot].
290 rows carry no nutrition value in the 2026-09-10 scan, ten more than the 280 that name no source: the extra ten are `per_litre` rows joined to a fluid whose `Properties` block is absent or holds only `alcohol` [#0625/C/snapshot].
The 133 containers are 63 single-fluid, 9 pick-random and 61 empty in the 2026-09-10 scan, and `fluid_fill_litres` equals `fluid_capacity` on all 72 filled rows because every `:share` suffix in the files is 1.0 bar `Base.BucketWaterDebug`'s `Water:10.0`, which the capacity clamp takes back to its 10 L capacity [#0627/C/snapshot].
On `42.20.4` `food.txt` carries 41 blocks with `CannedFood` true, 21 of them sealed with `CantEat` also true and 20 openable or opened, 127 blocks with `Packaged` true and 2 with it false plus 2 more in `drainable.txt`, and 10 blocks whose `OnCooked` is the home-canning code, re-counted directly from `food.txt` on 2026-09-10 [#0312/C/snapshot].
Seventeen of the 21 sealed cans declare an `OpeningRecipe`, and 19 of the 20 openable canned items declare rot thresholds — 2 and 4 days on eleven, 5 and 7 on five, 3 and 5 on two and 4 and 7 on one — while `CannedMilk` declares neither and so never ages, in the 2026-09-10 count [#0314/C/snapshot].
Of the 127 `food.txt` blocks that set `Packaged` true, 52 carry `DaysFresh` and 75 do not, and 225 of the 722 `base:food` blocks declare no `DaysFresh` at all and therefore never age, in the 2026-09-10 count [#0315/C/snapshot].
Exactly one of the 722 `base:food` blocks sets `DaysFresh` equal to `DaysTotallyRotten`, all 497 blocks that declare either threshold declare both, and the smallest non-zero gap is one day on 29 items, in the 2026-09-10 count [#0382/C/snapshot].
`42.20.4`'s own `media/scripts` declares 5 092 distinct `module Base` item names when parsed comment-stripped as the engine reads it, lower than the 5 105 raw item lines the same files hold, in the 2026-09-10 17:47 sweep [#1572/C/snapshot].

### Recipes

The 2026-09-10 scan found 969 `craftRecipe` blocks in 74 files, 63 `evolvedrecipe` blocks and 0 legacy `recipe` blocks [#0677/C/snapshot].
The 969 `craftRecipe` blocks live in 74 files — 42 under `generated/recipes/` and 32 under `generated/entities/*/{craftRecipes,cratRecipes,workstations}/`, including the shipped typo `cratRecipes` — in the 2026-09-10 scan [#0682/C/snapshot].
202 further `inputs` blocks in the script tree belong to a `component CraftRecipe`, an entity's own build recipe, and are censused as `meta.counts.componentCraftRecipes` outside the 969 scanned blocks, which is why a raw grep of the scripts counts 138 more `mode:` lines than this dataset does, in the 2026-09-10 scan [#0681/C/snapshot].
Sub-blocks over the 969 recipes are `inputs` 969, `outputs` 958, `itemMapper` 225 and `overlayMapper` 3, in the 2026-09-10 scan [#0685/C/snapshot].
37 recipes yield no item — 11 ship no `outputs` block at all and 26 ship an empty one — and all 37 mutate an input through `OnCreate` instead, reading `deltaReason: no-outputs`, in the 2026-09-10 scan; the 11 is the 969 blocks less the 958 `outputs` blocks [#0686/C/snapshot].
IO lines over the 969 recipes are 3 355 `inputs/item` plus 55 `inputs/-fluid`, making 3 410 input lines, and 988 `outputs/item` lines, with no vanilla line a bare `fluid` or an `energy`, in the 2026-09-10 scan [#0687/C/snapshot].
Scoped to the 969 `craftRecipe` blocks, the `mode:` values are `keep` 1 366, `destroy` 242 and `mixture` 26 on fluid lines only, and the flags are `MayDegradeLight` 975, `Prop2` 384, `Prop1` 320, `IsNotDull` 214, `ItemCount` 182, `InheritFoodAge` 46 and `InheritFood` 17, in the 2026-09-10 scan [#0688/C/snapshot].
A raw grep of every script file counts the 202 `component CraftRecipe` blocks as well and reports `keep` 1 502, `destroy` 244, `MayDegradeLight` 1 016, `Prop1` 440, `IsNotDull` 219 and `ItemCount` 185, in the 2026-09-10 scan [#0688/C/snapshot].
`itemMapper` blocks hold 1 599 `Result = Source` pairs over 225 mappers, 134 of which also write the literal key `default`, which is not a result type, and 56 of which name one result twice; the 3 `overlayMapper` blocks each carry a `default` and 5 pairs, with 3 input lines ending in a bare `overlayMapper` token, in the 2026-09-10 scan [#0690/C/snapshot].
One mapper resolves to nothing: `ExtractIronFromIronOre`'s `SmeltMapper` writes only a `default`, so under the stated rule its output carries an empty type list, and the case is recorded in `meta.outputMapperIssues` rather than special-cased, in the 2026-09-10 scan [#0769/C/snapshot].
Exactly one vanilla row rounds a `mode:destroy` charge up, `UnpackCigarettes`, and its `destroyWaste` is `null` because the drainable it destroys writes no macro key at all, so `meta.counts.recipesWithDestroyWaste` is 0 and the round-up lives in the row's `delta.notes`, in the 2026-09-10 scan [#0705/C/snapshot].
375 recipes touch a food item, measured as any item line on either side naming a `food` or `drainable` row; the nearest alternative definitions give 305 single-type lines only, 182 outputs only, 150 of kind food and 141 both sides, and `recipesWithFoodOutput` is 182 while `recipesTouchingDatasetRow` is 413, in the 2026-09-10 scan [#0770/C/snapshot].
The figure is definition-dependent — about a hundred alternative definitions were tried — which is why the dataset emits all three counters beside it [#0770/C/snapshot].
The `replacements` array is 163 links a food row declares — three on cooking, eight on rotting, 110 on use and 42 on depletion — of which twelve carry a delta and 151 are refused by name, 114 for no nutrition and 37 for not being in the dataset, in the 2026-09-10 scan; each link's source line is the item block's header line, the way every other record anchors, and not the line of the replacement key [#1909/C/snapshot].
The live craft-recipe count with `SKITTLE_LongTermPreservation4220` loaded is 977: the vanilla scan's 969 blocks plus the mod's own 8, which is the same census on either side of the mod rather than a disagreement — a dated count of one install plus one mod, from the 2026-09-10 sweep [#1456/C/snapshot].

### Evolved recipes

`media/scripts/generated/evolvedrecipes.txt` holds 62 `evolvedrecipe` blocks, as shipped and read 2026-09-10 [#0279/C/snapshot].
The evolved census is 63 recipes — 62 in `evolvedrecipes.txt` plus `AddBaitToChum` in `recipes/recipes_fishing_evolvedrecipe.txt` — over 374 carrier items (372 food and 2 drainable) writing 2 446 key parts across 31 distinct keys, 213 of the parts carrying the `Cooked` suffix, in the 2026-09-10 scan [#0724/C/snapshot].
The evolved-recipe join is the game's and not a name match: an item's `EvolvedRecipe` key reaches a recipe through an exact-name lookup and through every recipe whose template matches case-insensitively, with five parse-time aliases applied first (`RicePot` and `RicePan` to `Rice`, `PastaPot` and `PastaPan` to `Pasta`, `Roasted Vegetables` to `Stir fry`) — 374 carriers across 63 recipes yielding 6 902 joins that collapse to 6 881 rows, 21 landing on the same pair twice, with none unmatched, in the 2026-09-10 scan [#1910/C/snapshot].
It is not a product, since a carrier writes as many key parts as it writes and each part reaches however many recipes match it [#1910/C/snapshot].
The 21 that land on a recipe-and-item pair twice do so through an alias or through both arms and each repeats the same `use`, so the row keeps the last key written and names the collapsed ones in `duplicateKeys`, the 6 902 key-part-and-recipe pairs collapsing to 6 881 dataset rows with 0 unmatched keys in the 2026-09-10 scan [#0725/C/snapshot].
Over `items/food.txt` alone the evolved pair count is 6 858, emitted as `meta.counts.pairsFromFoodTxt`, so an expansion that filters to food reports 187 `Salad` ingredients and two false unmatched keys, in the 2026-09-10 scan [#0764/C/snapshot].
Seventeen vanilla `EvolvedRecipe` keys ask for more hunger than the ingredient carries, across 59 of the 6 881 ingredient rows of the evolved-recipe dataset, in the 2026-09-10 scan [#0289/C/snapshot].

<a id="mod-inventory"></a>
## Mod inventory

`data/mod-inventory.json`, written by [`mod_inventory.py`](tools.md#mod-inventory-tool) from the installed workshop tree, is one record per mod folder — 230 records across 179 workshop items in the 2026-09-10 17:47 sweep — read off shipped files only, so nothing in it is measured in a running game and a signal count is a count of pattern hits and not of behaviour [#1914/C/snapshot].
The tree is live and Steam rewrites it underneath, so every count from it carries the sweep stamp [#1914/C/snapshot].
The inventory's record is 21 enumerated fields covering a JSON record's 23 keys: the resolved id and the folder-name fallback, the name and the author, the requirements, the layout, the version-folder list, which mod-info file the id came from, the live-media flag and the media-roots list, the file counts, the pattern-hit signals and their per-key breakdown, the item-definition count, the declared modules, the top events, the Lua size, the on-disk bytes, the item modification time, the sandbox-options flag, the two identity keys and the class bucket [#1925/C/snapshot].
Two of the 21 rows pair two keys each — the name with the author and the workshop id with the folder — which is why the enumeration is 21 rows where the JSON record carries 23 keys, in the 2026-09-10 17:47 sweep [#1925/C/snapshot]:

| Field | Type | Meaning |
|---|---|---|
| `mod_id` | string | `id=` from the resolved `mod.info`; `""` when there is none |
| `mod_id_fallback` | string | the folder name — for reporting, never for a profile |
| `name` / `author` | string | `name=` / `author=` from the same file; `?` when absent **or declared empty** — `name=` with nothing after it says no more than a missing line (3 rows have no name, 56 no author; `3701820916/gasmask` is the one empty `author=`) |
| `require` | list | `require=` split on commas with the leading `\` stripped (`\Base,\OtherMod`) |
| `layout` | string | the folder the running build reads: a version folder (`42.20.1`), `common`, or `flat(b41?)` |
| `version_dirs` | list | every `42[.x[.y]]/` folder, newest first, tuple-sorted (`42.20.1 > 42.20 > 42.9 > 42`) |
| `mod_info_at` | string/null | which `mod.info` the id came from, relative to the mod folder (224 rows a version folder, 5 `common/mod.info`, 1 `null`) |
| `live_media` | bool | is there a `media/` inside the `layout` folder at all? **`false` on 24 rows** — everything below this line is counted under `<live>/media`, so on those 24 every count is zero because nothing was scanned, not because nothing is shipped. `true` does **not** mean the record is complete: read `media_at` for that |
| `media_at` | list | every `media/` folder in the mod, one level deep, sorted (`["42.20/media", "common/media"]`). Present on every row, and **the guard on a zero**: a `common/media` in it (**177 rows**) is content the build loads and this scan did not count, whether the row is one of the 24 blank ones or one of the 153 that also have a live `media/`. No row in the corpus has an empty list |
| `stats` | dict | file counts under `<live>/media`: `lua_client` / `lua_server` / `lua_shared` (by path), `script_files` (`.txt` under a `scripts` path), `models`, `tile_packs`, `map_files`, `sounds`. Absent keys are zero |
| `signals` | dict | regex hit counts, absent when zero — 18 Lua signals (`events_add`, `send_client_cmd`, `on_client_cmd`, `send_server_cmd`, `mod_data`, `transmit_mod_data`, `monkey_patch`, `pcall`, `loadstring`, `getfilewriter`, `sandbox_vars`, `timed_action_new`, `ui_panel`, `require_line`, `global_write_vanilla`, `onplayerupdate`, `everyoneminute`, `food_nutrition`) plus `script_nutrition` |
| `script_nutrition_keys` | dict | per-key counts behind `script_nutrition` |
| `script_item_blocks` | int | item **definitions** — `item <Name>` alone on its line, brace optional, the name matched as `\w[\w.-]*` so hyphenated ids count — over **every** `.txt` under `<live>/media/**/scripts`, not only the ones carrying a nutrition key, and over the file **comment-stripped** (`food_scan._strip_comments`, the rule `parse_script` applies), so a definition inside `/* … */` is not one. An exact count, not a bound (6630 over the corpus, 2026-09-10 17:47) |
| `script_modules` | list | every `module <name>` declared in those same `.txt` files, sorted |
| `top_events` | list | the 8 most-used `Events.<X>.Add` names, `[name, count]` |
| `lua_kb` | int | total `.lua` characters read, in KiB |
| `bytes` | int | the **whole** mod folder on disk, every version folder included — what a subscriber downloads (7.01 GiB over the corpus) |
| `workshop_item_mtime` | string/null | ISO-8601 mtime of the `<workshop-id>/` folder — see the caveat below. Non-null on all 230 rows here; `null` when `scan_mod` is called on a mod folder with no workshop item above it, since the mod folder's own mtime is a different fact |
| `sandbox_options` | bool | a `media/sandbox-options.txt` under the live folder, the mod root **or `common/`** — all three roots a build could load one from. **55 rows true** (2026-09-10 17:47); **11 of them keep the file only in `common/media`** (`3398090604`, `3404074048`, `3645980077`, four mods in `3662913642`, `3671176591`, `3763759011`, `3772533498`, `3789019583`), and read `false` before that root was checked. A profile reads sandbox options off this field, so a false "no options" is the dangerous direction |
| `workshop_id` / `folder` | string | the item id and the mod folder name; together they are the record's key |
| `class` | string | `systems(light-lua)` 175, `other` 31, `systems(heavy-lua)` 15, `content(scripts-only)` 5, `content(3d+lua)` 4 — `classify()`'s buckets, in that order of frequency. `other` is the 31 rows whose `stats` came back empty, and they split two ways: **24** have no `<live>/media` at all (`live_media` false — every file is in `common/media`: over the 24, 1 004 `.png`, 191 `.json`, 163 `.fbx`, 119 `.xml`, 105 `.lua`, 65 `.txt`, 13 `.tiles`, 12 `.pack`, and only 6 of the 24 ship any pack or tiles) and **7** have one holding only file kinds `stats` has no bucket for — measured 2026-09-10: **182 `.json`** (133 of them `KnoxBuildworks_Vanilla_Expanded` map definitions and manifests, 49 `lua/shared/Translate/**` strings, 16 of those from the same Knox item), **21 `.txt`** (more translations, plus `AnimSets/` and `actiongroups/` folder placeholders), **4 `.frag`** shaders (`SomewhatWater`) and **1 `.xml`** (`PALSJs Poofs`' hair styles) — and **no `.png`/`.dds`/`.tga` between them**, so they are not "textures". Never read `other` as "ships nothing" |

The inventory carries no `meta` block and no build stamp, unlike the four generated datasets, because it describes a live tree; the sweep date in its documentation is the stamp, and a count quoted from it must carry that stamp and never today's date [#1915/C/snapshot].
Regenerating it takes about two seconds and is byte-stable, the same tree in giving the same bytes out, as of the 2026-09-10 17:47 sweep [#1915/C/snapshot].
Seven of the inventory's rows carry different file counts in the 2026-09-10 sweep than in the 2026-09-09 one: two because the resolver reads the newest version folder and those rows' newest folder is not the one an older rule picked, and five because Steam rewrote those items' files between the sweeps [#1916/C/snapshot].
`workshop_item_mtime` is a download stamp and not an update stamp: Steam rewrites the mod folder inside an item without touching the item folder, so the item folder of `3490370700` still read 2026-08-12 while its mod folder was rewritten at 13:47 on 2026-09-10, and the corpus range 2026-08-12 to 2026-09-04 is the shape of one subscriber's download history, a three-week window [#1571/C/snapshot, #1924/C/snapshot].
A real last-updated date comes from the Workshop page instead, which [Workshop rows](#workshop-rows) records for the catalogued items [#1571/C/snapshot, #1924/C/snapshot].

### Identity

`mod_id` is the id the running build resolves and is the empty string when no mod-info file exists anywhere, never the folder name, which is kept beside it as `mod_id_fallback` — so a profile's mod id reads `mod_id` and never the folder [#1917/C/snapshot].
In the 2026-09-10 17:47 sweep one row has no mod-info file anywhere and is invisible to the workshop index, and an older copy of this dataset carries a folder name in place of the declared id on twenty of the 230 rows [#1917/C/snapshot].
20 of the 230 corpus rows carry no `mod.info` at the folder root, so a reader of that path alone falls back to the folder name for their id, in the 2026-09-10 17:47 sweep [#1556/C/snapshot].
Over the whole corpus, 52 installed workshop folders carry a name that differs from their declared id, and they load by id in normal play; `mod_lint`'s informational folder-name check counts 51 of them, having no id to compare on the 52nd, in the 2026-09-10 17:47 sweep [#0837/C/snapshot].
After a workshop change at 2026-09-11 04:47 a live sweep reads that pair as 51 and 50, while the committed snapshot keeps its own [#0837/C/snapshot].
The corpus holds 229 distinct ids over 230 folders with no duplicates, the one gap being the mod with no mod-info file, so the workshop index's 229 entries are a missing mod and not a collision; if a duplicate ever appears the index keeps whichever it globs first, so that mod must be resolved by workshop id and never by bare id — one corpus and one build, in the 2026-09-10 17:47 sweep [#1840/C/snapshot].

### Scope and the partial view

Everything except the on-disk byte count (`bytes`) describes the newest version folder only, which is a de-duplication rule and not a claim about what the game loads: a mod shipping the same scripts in three folders must not have them counted three times, so one folder is chosen and it is the one the build runs [#1918].
The nutrition signal scan reads the live version folder only, so a mod shipping the same scripts in three version folders is counted once [#1562].
An older version folder or a B41-layout root `media/` folder is genuinely ignored by the running build, but a `common/media` folder is not — it is a shipped layout the build also loads, and its content is simply not counted here, on one corpus and one build [#1919].
How the build merges the version folder with `common/` is [mod-anatomy.md](../platform/mod-anatomy.md#version-dirs)'s.

`data/mod-inventory.json`'s `signals`, `stats` and `top_events` are computed over the live version folder only, so a `common/`-heavy mod is under-read — for `AutoCook` they miss 7 of 10 Lua files and 1 238 of 2 155 lines, its only event registration, its only vanilla patch and its whole translation set — and a `media_at` that lists a `common/media` is the flag, on 177 of 230 rows in the 2026-09-10 17:47 sweep; never read a zero in those columns as an absence [#1218/C/snapshot].
`media_at` is the guard on a zero: 177 of the 230 rows list a `common/media` the scan did not read, so a zero in the file counts or the signal counts is only trustworthy where that root is absent from the list, in the 2026-09-10 17:47 sweep [#1920/C/snapshot].
A zero in a corpus record's `stats` or `signals` is trustworthy only when `media_at` does not include `common/media`; `live_media: false` marks the much narrower set of 24 rows with no live `media/` at all, so every readiness statement reads `media_at` rather than `live_media` — the signal scan counts under the live `media/` alone and asserts no merge rule between the two folders, as of 2026-09-10 [#1560/C/snapshot].
The false live-media flag marks something narrower: the 24 rows with no live `media/` at all, whose whole record is therefore blank, in the 2026-09-10 17:47 sweep [#1922/C/snapshot].
A true live-media flag does not mean the record is complete: on 111 of the 153 rows that have both a live `media/` and a `common/media`, a `stats` bucket reads zero while the common folder holds exactly that kind of file — 2 527 models, 120 sounds, fifteen tile packs, 92 Lua files and three script files reported as zero on those rows alone, and the true uncounted total is larger, in the 2026-09-10 17:47 sweep [#1921/C/snapshot].
A row whose bucket is non-zero can have more of the same kind in the common folder as well [#1921/C/snapshot].
The measured impact of the `common/media` gap on the nutrition question is none: every `common/media` in the corpus was swept twice on 2026-09-10 for the ten script nutrition keys and not one carries a single key, so no nutrition candidate is hidden by the scan's scope — for any other question, check `media_at` before believing a zero [#1923/C/snapshot].
The corpus event counts are a floor by construction, because the census sums each record's `top_events`, which keeps only a mod's eight most-used events, so an absence below the histogram's cut is a floor artefact and not a zero, as of the 2026-09-10 sweep [#0891/C/snapshot].

### The signals

The two nutrition signals are counted from different files and neither alone is the catalog: the runtime signal greps Lua for the nutrition getter, the four macro setters or a hunger-change line and hits eleven mods, while the script signal greps the live script text for ten item-definition keys and hits nine mods, with exactly one mod showing both and nineteen showing at least one, in the 2026-09-10 17:47 sweep, both script-side counts reading the file comment-stripped [#1926/C/snapshot].
`signals.food_nutrition` counts hits of `getNutrition()`, `setCalories`, `setProteins`, `setLipids`, `setCarbohydrates` or `HungerChange` in any `.lua` under the live version folder [#1575].
`signals.script_nutrition` counts `Calories`, `Carbohydrates`, `Lipids`, `Proteins`, `HungerChange`, `ThirstChange`, `DaysFresh`, `DaysTotallyRotten`, `FoodType` or `EvolvedRecipe` at the start of a line in a `.txt` under the live `media/**/scripts`, read comment-stripped as the engine reads it [#1592].
`signals.monkey_patch` counts the save-and-wrap idiom `local original... = X.y` and is a different signal from `signals.global_write_vanilla`, which counts `function IS...:` headers: `AutoCook` reads 0 on the first and 21 on the second in the 2026-09-10 17:47 sweep [#1578/C/snapshot].
The [catalog's](../facts/other-mods/catalog.md#sweep) `net` column, which is `send_client_cmd` plus `on_client_cmd` plus `send_server_cmd` only, is a floor, because the inventory carries no signal for `OnServerCommand` and `SkillRecoveryJournal` has 3 of those on top of its 23 counted sites, in the 2026-09-10 17:47 sweep [#1576/C/snapshot].
The declared-modules field (`script_modules`) is the override question: a mod writing `module Base` overrides vanilla items while a mod's own module only adds new ones, and the value is the raw token after the module keyword, so a module written with the opening brace on the same line is recorded with the brace attached (`LabItems{`), in the 2026-09-10 17:47 sweep [#1927/C/snapshot].

`script_item_blocks` counts every item definition in a mod's live script files, clothing and vehicles included, and is not a food count; the field is a count, not a bound [#1593].
The item-definition count is exact and not a bound — an item keyword and a name alone on a line, brace optional, over every script file under the live `media/` with comments stripped — 6 630 over the corpus in the 2026-09-10 17:47 sweep, and it counts every item definition including clothing and vehicles, so food has to be counted by hand off the food-type blocks [#1928/C/snapshot].
Anchoring the name to the end of the line is what separates a definition from a recipe's inputs and outputs [#1928/C/snapshot].
The count separates a definition from a recipe's input and output lines by anchoring the name to the end of the line, keeps a hyphenated id by widening the name class beyond word characters and a dot (`\w[\w.-]*`), and reads the file comment-stripped [#1929/C/snapshot].
Over the corpus in the 2026-09-10 17:47 sweep, the end-of-line anchor removes 16 074 recipe lines from 113 of the 230 rows, the widened name class recovers 491 definitions on one mod and changes no other row, and comment-stripping removes 18 from two rows; on vanilla's own scripts both name classes read the same 5 105 definitions [#1929/C/snapshot].
171 of the corpus's 2 401 live script files carry a block comment, and stripping them moved two rows only: one mod from seventeen definitions to fifteen and another from 102 to 86, each of whose affected files is commented out whole in one block, in the 2026-09-10 17:47 sweep; the line-comment token is stripped for the same reason and changes nothing here [#1930/C/snapshot].
The nine script-signal mods define 881 items between them in the 2026-09-10 17:47 sweep, and that figure must be quoted as items defined rather than food items, because it counts definitions in every script file [#1931/C/snapshot].
Read without comment-stripping the figure is 899, and the hyphen widening leaves it unchanged, in the 2026-09-10 17:47 sweep [#1931/C/snapshot].

<a id="workshop-rows"></a>
## Workshop rows

`data/workshop-search.*`, written by [`workshop_search.py`](tools.md#workshop-search), is eight terms against the `Build 42`-tagged ready-to-use browse section, one page per term with no pagination, joined to the inventory on `workshop_id`: 212 results over eight terms collapse to 180 distinct items because 29 ids appear under more than one term, three of them installed, with no term failures, in the 2026-09-10 16:26 fetch [#1932/W/snapshot].
Steam is live and the trend sort reorders hourly, so no count is quotable without the fetch stamp, and two browse passes 34 minutes apart returned the same totals and the same three installed ids, which says the answer held for half an hour and not that it is stable [#1932/W/snapshot].

A workshop row that is not installed cannot be linted, profiled, booted or measured from this repository, so 177 of the 180 rows are graded as a page reading — a title, a size and a date — and each carries the exact unblocking action; the three installed rows are graded as code readings only because they join to an inventory record read off shipped files, and the grade belongs to the inventory and never to the page, in the 2026-09-10 16:26 fetch [#1934/W/snapshot].
Teardown picks come only from the installed corpus, however relevant a page row looks [#1934/W/snapshot].
The sweep is a trend-sorted top-thirty-per-term slice of the Workshop and neither a census of it nor a second inventory: 176 of the 179 installed workshop items are returned by none of the eight terms, and none of the three installed hits is a nutrition mod — a car, a bottle-capacity tweak and a skill-cap mod (`93townCar`, `BigBottles`, `BeyondTen`) matched the search text, in the 2026-09-10 16:26 fetch against the inventory as it stood at 16:20 that day [#1935/W/snapshot].
The installed mod that writes both nutrition signals (`3774789651`) is in none of the eight pages while a third-party patch to it (`3796644824`) is, so absence from this dataset is not evidence about a mod and a missing id must never be read as no such mod, in the 2026-09-10 16:26 fetch [#1936/W/snapshot].

A workshop row says which of three things happened to it in `details_status`: `fetched` means an item page was read, `not_requested` means no page was asked for and nothing about the item is claimed, and `failed` means a page was asked for and could not be read, with the error saying why [#1938/C/snapshot].
In the committed file, stamped 2026-09-10 16:56, fifteen rows are fetched, 165 not requested and none failed; read that field before the three statistic columns, because the error field is a fetch failure and nothing else [#1938/C/snapshot].
The fields of a row, `details_status` among them, as the committed file writes them [#1938/C/snapshot]:

| Field | Type | Meaning |
|---|---|---|
| `workshop_id` | string | the Steam item id, all digits — **the join key**, and the row's identity. Unique across the 180 rows |
| `title` | string | the `alt` text of the item thumbnail on the browse page, HTML-unescaped. The item page's own `workshopItemTitle` is read too but not stored: the browse title is present on every row |
| `terms` | list | every swept term whose page returned this id, in sweep order. **Never empty** — a row exists because some term returned it. `;`-joined in the CSV |
| `installed` | bool | does `workshop_id` match a record in `data/mod-inventory.json`? **3 true / 177 false** (2026-09-10 16:26) |
| `mod_ids` | list | the resolved `mod_id`s of every corpus record under that item, sorted; `[]` when not installed. A list because one workshop item may hold several mods (230 records across 179 items). `;`-joined in the CSV |
| `size` | string/null | `File Size` from the item page, verbatim (`453.434 KB`) — `null` on every row that is not `details_status: fetched` |
| `posted` | string/null | `Posted` from the item page, verbatim (`May 31 @ 7:55am`; a year appears only when it is not the current one) |
| `updated` | string/null | `Updated` from the item page — **on a `fetched` row `null` means the item has never been updated since posting**, because the page then renders only two stats. On any other row it means nothing at all: read `details_status` first. Three of the 15 fetched rows are genuinely never-updated (`3430945294`, `3782835400`, `3796644824`) |
| `details_status` | string | `fetched` / `not_requested` / `failed` — what happened to this row's item page, and the field that says whether `size`/`posted`/`updated` mean anything. **15 / 165 / 0** (2026-09-10 16:56). Also a CSV column, after `updated` |
| `error` | string/null | **a fetch failure and nothing else**: a `curl rc=…` transport failure, or an unrecognised item-page template (Steam's landing page at 200). `null` on every `fetched` and every `not_requested` row — a row nobody asked for did not fail. **`null` on all 180 rows here** |
| `grade` | string | `C` for an installed row (it joins to a file-read inventory record), `W` for every other. **JSON only** — derive it from `installed` in the CSV |
| `unblock` | string/null | the exact action that would make a W row measurable: *subscribe to `<id>` in Steam, let it download, re-run `tools/mod_inventory.py`*. `null` on installed rows. **JSON only** |

On a fetched row a null update date means the item has never been updated since posting, because the page then renders only two statistics, while on any other row it means nothing at all; three of the fifteen fetched rows are genuinely never-updated, as read 2026-09-10 16:56 [#1939/W/snapshot].
In the committed file of the 2026-09-10 16:26 sweep (commit `ce7cd72`) the dataset's own census reads `details_status` 15 `fetched`, 165 `not_requested` and 0 `failed`, and that field rather than any count in prose is the census; details were fetched for a declared subset of named ids only [#1602/W/snapshot].
The repair pass stamped `meta.fill` 2026-09-10 16:56 read six more item pages, taking `details_requested` from 9 to 15 and the never-asked-for rows from 171 to 165 and recording those rows as `details_status: not_requested` rather than as an error string, while the 212 results, 180 distinct ids, 3 installed rows and 0 term failures are unchanged [#1603/W/snapshot].
`not_requested` records a decision about the run, not a fetch failure, and the topped-up file is the one committed as `ce7cd72` [#1603/W/snapshot].

Six not-installed items are load-bearing for this library — a nutrition-sync fix for the very problem this library exists to characterise, a patch claiming to launder the top teardown pick's nutrition, the largest nutrition overhaul with its add-on, a small recent take, a third same-month overhaul and the B41-era ancestor — each recorded with its id, title, size and two dates and nothing more, as fetched 2026-09-10 16:26; every row is a page reading, and until one is subscribed nothing below the title is known [#1937/W/snapshot]:

| `workshop_id` | Title | Size | Posted | Updated | Why it is load-bearing |
|---|---|---|---|---|---|
| `3736275816` | ApocalipseBR - Nutrition Sync Fix | 453.434 KB | May 31 @ 7:55am | May 31 @ 11:18am | **someone else hit the MP nutrition-sync problem this library exists to characterise** and shipped a fix for it. Subscribing is the only way to read how; until then we know a title, a size and two dates |
| `3796644824` | [NUTRITION LAUNDERING PATCH + FEATURES] Long Term Preservation | 471.224 KB | Sep 6 @ 12:58am | *never* | **a third-party patch to our own top teardown pick** (`3774789651`, installed, 117 `script_nutrition` hits) — its title claims the preservation mod launders nutrition, which is a claim about a mod we *can* read. Subscribe to compare the two script sets; the patch is 4 days old and has never been updated |
| `3690404044` | Nutrition Makes Sense | 1.042 MB | Mar 22 @ 4:57pm | Aug 18 @ 5:01pm | the largest of the nutrition-overhaul group, and the one with an add-on ecosystem (`3796753621` Nutrition Makes Sense Immersive Addon is in the same page) |
| `3785515388` | Reasonable Nutrition | 145.008 KB | Aug 17 @ 7:44pm | Aug 26 @ 3:49pm | a small, recent take on the same problem — the cheapest comparison read if only one of these is ever subscribed |
| `3782835400` | Realistic Nutrition | 636.708 KB | Aug 13 @ 10:59am | *never* | third of the three same-month "nutrition" overhauls; never updated since posting |
| `3078272807` | Nutrition Tweaker Enhanced | 503.836 KB | Nov 10, 2023 @ 2:19am | Jul 22, 2025 @ 1:35pm | the B41-era ancestor still carrying the `Build 42` tag — the only one of the six older than this year |

`data/workshop-catalog-details.json` is the same item-page read for ids that are not sweep rows, one row per catalogued item with `workshop_id`, `title`, `size`, `posted`, `updated`, `details_status`, `error` and a per-row `fetched_at`, and no `terms`, `installed`, `mod_ids`, `grade` or `unblock`, because no browse page returned those ids and nothing in it is joined to anything.
A workshop page's title and size are the item's and not a mod's, two of the nine catalogued items shipping several mods each, and the size matched the sum of the item's mod folders exactly on all nine — a genuine cross-check of two independent readings, which says the local tree is the size of what the Workshop served at the 2026-09-10 17:46 read, Steam dividing by a thousand and truncating at three decimals [#1944/W/snapshot].
The catalog pass answers the one question the download stamp cannot — when the author last uploaded — and the two disagree in both directions without either being wrong: one item has never been updated since posting yet its folder was written a month later, and another was updated on the page hours before the read while its item folder still reads a month earlier, in the 2026-09-10 17:46 read [#1945/W/snapshot].
Of those nine items one was read twice by two routes at different hours, both reads agreeing on its size and update date, and a page date says nothing about what the mod does [#1945/W/snapshot].

<a id="schemas"></a>
## Schemas

The flat half of a generated dataset pair carries no build stamp: any line above the header breaks every reader, so the pair's JSON metadata and the dataset documentation are what date it, which is read as one stamp per pair rather than one per file [#1967].
The JSON twin is written in the same run from the same metadata, so the provenance of the two halves cannot disagree [#1967].

### Food items

`data/food-items.csv` is 1 006 lines (header plus 1 005 rows) and 61 columns — 59 declared plus `source_file` and `source_line` — with one row per item, zero quoted cells, LF endings and no build stamp, while the JSON is 2.35 MB against the CSV's 237 KB, 41 126 of its lines being a null column value and `props_raw` another 474 KB, in the 2026-09-10 scan [#0639/C/snapshot].
Fluids are joined into their container's row and also kept whole under the JSON's `fluids` key; they are never rows of their own [#0617].
The food dataset's JSON is a `meta` block, an item array and a fluid array, both sorted by id — 1 005 items and 61 fluids in the 2026-09-10 scan of `42.20.4` — where an item record carries every declared column, absent as `null`, plus `props_raw`: the item block's own key-and-value lines verbatim, untyped and unsplit, with a key written twice becoming a list [#0640, #1899/C/snapshot].
Nested blocks are not flattened into `props_raw`, so a container's `Capacity` reaches the record only as `fluid_capacity` [#0640, #1899/C/snapshot].
A fluid record additionally keeps `properties_raw`, `categories`, `poison` and its own source anchor, and it has no basis and no per-container fields, having no capacity of its own to multiply by [#0640, #1899/C/snapshot].
A fluid record carries `id`, `module`, `name`, `kind`, `display_name`, `display_name_key`, `color_reference`, `categories`, the nutrition columns (always per litre), `properties_raw` (the `Properties` block verbatim), `poison` (the `Poison` block, or `null`), `props_raw`, `source_file` and `source_line`.
Types follow the loader: only the literal `true` is true, and an integer-typed key holding an integral float literal comes back as an integer (`UnhappyChange = -10.0` reads `-10`); the fluid files put float literals on 141 integer-typed values and every one is integral [#1890].

The food dataset's flat file is 61 columns — 59 declared plus the source file and line — with booleans printed as words and list columns joined by semicolons, and every record naming the file and line it came from, in the 2026-09-10 scan of `42.20.4` [#1885/C/snapshot]:

| # | Column | Type | From |
|---|---|---|---|
| 1 | `id` | string | derived: `<module>.<name>`, e.g. `Base.Apple` |
| 2 | `module` | string | the enclosing `module` block |
| 3 | `name` | string | the `item` / `fluid` block name |
| 4 | `kind` | string | derived: `food`, `drainable` or `fluid_container` |
| 5 | `display_name` | string | `lua/shared/Translate/EN/ItemName.json[<id>]`; empty for the 6 ids with no EN entry |
| 6 | `display_category` | string | `DisplayCategory` |
| 7 | `food_type` | string | `FoodType` |
| 8 | `item_type` | string | `ItemType` |
| 9 | `tags` | list `;` | `Tags` |
| 10 | `nutrition_source` | string | derived: `food_keys`, or `fluid:<id>` when the row's nutrition was joined from a fluid; empty when the row carries no nutrition key at all (then `nutrition_basis` is empty too) |
| 11 | `nutrition_basis` | string | derived: **which unit columns 12–17 and 31–38 are in** — `per_item` for a row that fills them from its own keys, `per_litre` for a fluid-sourced row, empty for the 280 rows that name no nutrition source. (Carrying no nutrition *value* is a wider set: 290 rows do, the extra 10 being `per_litre` rows joined to a fluid with no `Properties` block or with only `alcohol`.) |
| 12 | `calories` | float | `Calories` |
| 13 | `carbohydrates` | float | `Carbohydrates` |
| 14 | `lipids` | float | `Lipids` |
| 15 | `proteins` | float | `Proteins` |
| 16 | `hunger_change` | float | `HungerChange` |
| 17 | `thirst_change` | float | `ThirstChange` |
| 18 | `days_fresh` | int | `DaysFresh` |
| 19 | `days_totally_rotten` | int | `DaysTotallyRotten` |
| 20 | `cant_be_frozen` | bool | `CantBeFrozen` |
| 21 | `is_cookable` | bool | `IsCookable` |
| 22 | `minutes_to_cook` | int | `MinutesToCook` |
| 23 | `minutes_to_burn` | int | `MinutesToBurn` |
| 24 | `dangerous_uncooked` | bool | `DangerousUncooked` |
| 25 | `packaged` | bool | `Packaged` |
| 26 | `canned_food` | bool | `CannedFood` |
| 27 | `cant_eat` | bool | `CantEat` |
| 28 | `spice` | bool | `Spice` |
| 29 | `good_hot` | bool | `GoodHot` |
| 30 | `bad_cold` | bool | `BadCold` |
| 31 | `unhappy_change` | int | `UnhappyChange` |
| 32 | `boredom_change` | int | `BoredomChange` |
| 33 | `stress_change` | int | `StressChange` |
| 34 | `fatigue_change` | float | `fatigueChange` |
| 35 | `endurance_change` | float | `enduranceChange` |
| 36 | `food_sickness_change` | int | `FoodSicknessChange` (the fluid files spell it `foodSicknessChange`; both land here) |
| 37 | `poison_power` | int | `PoisonPower` |
| 38 | `alcohol_power` | float | `AlcoholPower` — the item key, never the fluid's `alcohol` |
| 39 | `evolved_recipe` | list `;` | `EvolvedRecipe` (`Cake:16` parts, `\|Cooked` suffix intact) |
| 40 | `evolved_recipe_name` | string | `EvolvedRecipeName` |
| 41 | `replace_on_cooked` | list `;` | `ReplaceOnCooked` (list-typed in the key table, so a single target is a one-item list) |
| 42 | `replace_on_rotten` | string | `ReplaceOnRotten` |
| 43 | `replace_on_use` | string | `ReplaceOnUse` |
| 44 | `on_cooked` | string | `OnCooked` |
| 45 | `on_eat` | string | `OnEat` |
| 46 | `fluid_capacity` | float | `component FluidContainer`'s `Capacity`, in litres |
| 47 | `fluid_ids` | list `;` | each `Fluids.fluid` value's first `:` field, in file order — a pick-random container either repeats one id (`HairDyeCommon` lists `HairDye` 8 times) or lists several different ones, and then only the first fills the nutrition columns. In the JSON, `[]` is a container that lists no fluid (an empty vessel, 61 of them) and `null` is a row that is not a container |
| 48 | `fluid_share` | float | derived: the **first** `fluid =` value's second `:` field (`Cola:1.0` → `1.0`), or `1.0` when the line writes only an id. Empty on a container that lists no fluid. Every 42.20.4 share is `1.0` except `Base.BucketWaterDebug`'s `Water:10.0` |
| 49 | `fluid_fill_litres` | float | derived: `min(fluid_capacity × fluid_share, fluid_capacity)` — the litres of a **full** container at the listed share, and the multiplier of columns 52–57. Equals `fluid_capacity` on all 72 filled rows in 42.20.4. **It is not always the spawn fill:** 14 containers also write `InitialPercentMin` / `InitialPercentMax` (`InitialPercentMin = 0.0` / `InitialPercentMax = 1.0` on `Base.Flask`; counted as `meta.counts.fluid_containers_initial_percent`) and spawn part-filled at a random draw this column does not model |
| 50 | `fluid_pick_random` | bool | the component's `PickRandomFluid` — the container fills from a pool, so its nutrition is **one draw**, not the item's value. `false` on a container that does not write the key (124 of the 133); empty on a row that is not a container |
| 51 | `drinkable` | bool | derived: `fluid_capacity <= 3.0`, the gate `ISInventoryPaneContextMenu.lua` puts on the Drink menu. 16 of the 133 containers fail it and can only be poured or emptied |
| 52 | `calories_per_container` | float | derived: `calories × fluid_fill_litres` — the nutrition of a **full** container, not of a spawned one (col. 49) |
| 53 | `carbohydrates_per_container` | float | derived: `carbohydrates × fluid_fill_litres` — full container |
| 54 | `lipids_per_container` | float | derived: `lipids × fluid_fill_litres` — full container |
| 55 | `proteins_per_container` | float | derived: `proteins × fluid_fill_litres` — full container |
| 56 | `hunger_change_per_container` | float | derived: `hunger_change × fluid_fill_litres` — full container |
| 57 | `thirst_change_per_container` | float | derived: `thirst_change × fluid_fill_litres` — full container |
| 58 | `weight` | float | `Weight` |
| 59 | `replace_on_deplete` | string | `ReplaceOnDeplete` — what a drainable becomes when it runs out (42 rows carry one) |
| 60 | `source_file` | string | path under `media/scripts/generated/`, e.g. `items/food.txt` |
| 61 | `source_line` | int | 1-based line of the block's header |

The JSON's `meta` records the build, the jar hash, the 18 source paths, ten counts and every join miss — `unresolved_links` 37, `missing_display_names` 6, `unresolved_fluid_refs` 0 and `unknown_keys` 60 — in the 2026-09-10 scan [#0641/C/snapshot].
The food dataset's metadata carries the build, the disassembled jar hash the key table was checked against, the generation date, the tool, the eighteen script paths read, a counts block, the unknown keys kept raw, the unresolved replacement links, the ids with no English name and the unresolved fluid references — so every join miss is recorded rather than papered over, in the 2026-09-10 scan of `42.20.4` [#1900/C/snapshot]:

| Key | Meaning |
|---|---|
| `build` | game build the scripts were read from (`42.20.4`) |
| `jar_hash` | the disassembled jar this build's key table was checked against (`b0bbce05d5`) |
| `generated` | UTC date of the run |
| `tool` | `tools/food_scan.py` |
| `sources` | the 18 script paths read, relative to `media/scripts/generated/` |
| `counts` | `food`, `drainable`, `fluid_container`, `fluids`, `multi_fluid_containers` (containers whose `fluid_ids` holds more than one distinct id), `fluid_containers_filled` / `fluid_containers_pick_random` / `fluid_containers_empty` (the fill split over the same 133 rows: 72 list a fluid to spawn holding, 9 of those from a pool, and 61 list none), `fluid_containers_initial_percent` (14 — the subset of those 133 that also writes `InitialPercentMin` / `InitialPercentMax` and therefore spawns **part**-filled at a random draw, so `fluid_fill_litres` is its full-container figure and not its spawn fill), `unresolved_links` |
| `unknown_keys` | every script key the dataset carries that the item key table does not cover, so it is kept as a raw string — weapon and clothing keys ride along on fluid-container items, and `DisplayName`, `ColorReference`, `alcohol` and the `Poison` block are the fluid files' own. Three entries are listed without being raw: the component's `Capacity`, `fluid` and `PickRandomFluid`, which never reach a `props_raw` because the dataset types them itself into `fluid_capacity`, `fluid_ids` / `fluid_share` and `fluid_pick_random`; they are listed because the **key** is outside the item table, not because the value stayed a string |
| `unresolved_links` | `{item, key, target}` for every `ReplaceOnCooked` / `ReplaceOnRotten` / `ReplaceOnUse` / `ReplaceOnDeplete` target that is not a record of this dataset — mostly pans and empty containers, plus `Base.HotDrinkRed` → `Base.MugRed`, which 42.20.4 names but never defines |
| `missing_display_names` | ids with no EN name; a fluid appears as `fluid:<id>` |
| `unresolved_fluid_refs` | `{item, fluid_id}` for a `Fluids.fluid` naming a fluid no file defines (empty in 42.20.4) |

All four `ReplaceOn*` keys — `ReplaceOnCooked`, `ReplaceOnRotten`, `ReplaceOnUse` and `ReplaceOnDeplete` — have a column of their own and are resolved against the dataset's own ids, so a row shows the link and `meta` shows the miss; each is kept verbatim in `props_raw` as well.

### Recipes

`data/recipes.csv` is 969 rows and 37 columns with IO lines joined into `inputsRaw` and `outputsRaw`, and `data/recipes.json` is a `meta` block with 969 recipes and 163 replacements, indented by one and sorted by name at 3.4 MB, in the 2026-09-10 scan [#0735/C/snapshot].
An absent key is the empty string in the CSV, never `0`, exactly as in the food dataset; booleans print `true` or `false`, and list columns join their parts with `;`.
The recipe dataset is one row per craft-recipe block, 969 of them over 74 files, with 37 flat columns; every value read off a script line names its own source file and line, and the delta block is arithmetic on those lines and on the food dataset, in the 2026-09-10 scan of `42.20.4` [#1903/C/snapshot]:

| # | Column | Type | From |
|---|---|---|---|
| 1 | `name` | string | the `craftRecipe` block name — unique across the 969 |
| 2 | `module` | string | the enclosing `module` block (`Base` on every vanilla recipe) |
| 3 | `category` | string | `category` (935 blocks write one) |
| 4 | `time` | int | `time` |
| 5 | `timedAction` | string | `timedAction` |
| 6 | `tags` | list `;` | `Tags` |
| 7 | `skillRequired` | list `;` | `SkillRequired`, parts kept whole (`Blacksmith:0`) |
| 8 | `xpAward` | list `;` | `xpAward`, parts kept whole (`Blacksmith:10`) |
| 9 | `needToBeLearn` | bool | `NeedToBeLearn` |
| 10 | `autoLearnAll` | list `;` | `AutoLearnAll` |
| 11 | `autoLearnAny` | list `;` | `AutoLearnAny` |
| 12 | `allowBatchCraft` | bool | `AllowBatchCraft` |
| 13 | `metaRecipe` | string | `MetaRecipe` |
| 14 | `onCreate` | string | `OnCreate` — the Lua hook the 37 output-less recipes mutate their input through |
| 15 | `tooltip` | string | `Tooltip` |
| 16 | `inputTypes` | list `;` | derived: every distinct type named by an input **item** line, sorted, sub-lines included |
| 17 | `inputTags` | list `;` | derived: the same over `tags[…]` inputs (`base:bowl`) |
| 18 | `inputFluids` | list `;` | derived: every `-fluid` line's fluid ids, plus `category:<Name>` for a line naming categories instead |
| 19 | `inputCount` | int | derived: **the loader's own `inputs.size()`** — a `-`/`+` sub-line belongs to the input above it and does not count |
| 20 | `outputTypes` | list `;` | derived: every distinct output type, a `mapper:<name>` line resolved to every result of that mapper except the literal `default` |
| 21 | `itemMappers` | list `;` | the mapper names this recipe declares |
| 22 | `fluidIO` | bool | derived: the recipe has at least one fluid line (53 recipes). Fluid nutrition is **not** in the delta |
| 23 | `split` | bool | derived: an input carries `flags[InheritFood]`, so each output takes `1/outputCount` of the *consumed instance's* macros and the delta is 0 by construction (17 recipes) |
| 24 | `datasetTypes` | list `;` | derived: the IO types that are a `data/food-items.json` row **at all**, vessels included |
| 25 | `foodItemTypes` | list `;` | derived: the `food` / `drainable` subset of column 24 — the rows a delta may weigh |
| 26 | `deltaCalories` | float | derived: Σ(outputs × their own script macros) − Σ(what each consumed input really spends). Empty — never `0` — when `deltaReason` says why |
| 27 | `deltaCarbohydrates` | float | derived, same rule |
| 28 | `deltaLipids` | float | derived, same rule |
| 29 | `deltaProteins` | float | derived, same rule |
| 30 | `deltaHungerChange` | float | derived, same rule, in raw script points (`/100` for stat-bar units) |
| 31 | `deltaThirstChange` | float | derived, same rule |
| 32 | `deltaAbsentMacros` | list `;` | `<id>:<macro>` for every term that summed as `0` because that block writes no such line — the null-for-0 substitution, never silent |
| 33 | `deltaReason` | string | why the delta is refused, blockers joined with ` ; ` and each naming its line verbatim: `tags-only`, `multi-type`, `wildcard`, `variable-amount`, `no-outputs`, `not-in-dataset`, `no-nutrition`, `fluid-sourced`, `no-type` |
| 34 | `inputsRaw` | string | every input line verbatim, joined with ` \| ` — the **flat** reading, a parent's sub-lines following it, so no line is hidden |
| 35 | `outputsRaw` | string | every output line verbatim, same join |
| 36 | `sourceFile` | string | path under `media/scripts/generated/`, e.g. `recipes/recipes_cooking.txt` |
| 37 | `sourceLine` | int | 1-based line of the block's header |

The delta's `notes` and `destroyWaste` are JSON-only — a list of sentences and a six-macro dict — and the `delta*` columns are the whole of the delta the flat file carries.
A recipe record in the JSON carries every column above except the six derived `input*` and `output*` flattenings, which it keeps structured instead, plus `inputs`, `outputs`, `itemMappers`, `itemMapperPairs`, `itemMapperDefaults`, `overlayMapper`, `props` and `delta`.
A parsed recipe input or output line carries all seventeen fields whether or not it writes them — `kind`, `amount`, `variable`, `types`, `tags`, `categories`, `mode`, `flags`, `mappers`, `mapper`, `overlayMapper`, `extras`, `consumed` (`mode != "keep"`), `amountIsItemCount`, `amountUses`, `subLines` and `raw` — with a null block when the block is absent and an empty one when it is present and empty, eleven and 26 recipes respectively, in the 2026-09-10 scan of `42.20.4` [#1906/C/snapshot].
An item-mapper contract dictionary (`itemMappers`) keeps only the last source of a repeated result, so the dataset carries the ordered pair list (`itemMapperPairs`) beside it — 56 mappers name one result twice, and the dictionary alone would lose a pair — over 225 mappers, 134 of which write the `default` that `itemMapperDefaults` holds, in the 2026-09-10 scan [#1907/C/snapshot].
`overlayMapper` is the `{default, pairs}` of an `overlayMapper` block or `null`; `props` holds every key no column claims, raw (`overlayStyle`, `OnTest`, `recipeGroup`, `Icon`, `ResearchSkillLevel` and `ResearchAny` on `42.20.4`); and `delta` is `{calories, carbohydrates, lipids, proteins, hungerChange, thirstChange, absentMacros, destroyWaste, notes}` or `null` with the reason in `deltaReason`, `notes` naming each weighing decision that is not the plain rule.
`data/recipes.json` holds 163 replacement records of `from`, `to`, `trigger`, `sourceFile`, `sourceLine`, `delta` and `deltaReason`, sorted by trigger, each anchored on the item block's header line rather than on the `ReplaceOn*` key a few lines below it, in the 2026-09-10 scan [#0751/C/snapshot].
Both recipe JSONs are byte-stable within one UTC day — two scanner runs produce identical files, asserted by two install-gated tests — and the only field that can differ between runs is `meta.generated`, which is today's UTC date [#0737].
The recipe JSON is byte-stable across runs within one UTC day because the generation stamp is today's UTC date and is the one line a rebuild after midnight changes, as generated 2026-09-10 on `42.20.4` [#1905/C/snapshot].
`meta.sources` records the scripts root, the files each record was read from and `data/food-items.json` with its own build, jar and generated stamps, so a rebuild of one half against a stale other half is visible in the file [#0738].
The `meta` keys of `data/recipes.json`, the `counts` cell being the 2026-09-10 scan's census [#0735/C/snapshot, #0738]:

| Key | Meaning |
|---|---|
| `build` / `generated` / `tool` | `42.20.4 (b0bbce05d5)`, the UTC date of the run, `tools/recipe_scan.py` |
| `sources` | `scripts` (the root walked), `files` (the 74 a recipe was read from) and `food_items` — the joined dataset's own `path` / `build` / `jar_hash` / `generated`, so a rebuild of one half against a stale other half is visible in the file |
| `counts` | `craftRecipes` 969, `files` 74, `scriptFiles` 1004, `legacyRecipeBlocks` 0, `componentCraftRecipes` 202 (an entity's own build recipes — counted because a raw grep of the scripts sees their `inputs` blocks too, **not** rows of this dataset), `itemMappers` 225, `overlayMappers` 3, `recipesWithoutOutputs` 11, `recipesWithEmptyOutputs` 26, `fluidRecipes` 53, `outputItemTypes` 1693, `outputItemTypesInDataset` 295, `outputItemTypesInFoodDataset` 262, `recipesTouchingDatasetRow` 413, `recipesTouchingFood` 375, `recipesWithFoodOutput` 182, `foodJoinMisses` 0, `recipesWithDelta` 31, `recipesWithNonZeroCalorieDelta` 15, `recipesWithCaloriesAbsentOnEverySide` 3, `splitRecipes` 17, `splitRecipesWithDelta` 8, `recipesWithDestroyWaste` **0** (rows publishing a non-null `destroyWaste`; the one `mode:destroy` round-up, `UnpackCigarettes`, wastes a drainable that carries no macros), `inputSubLines` 55 |
| `outputMapperIssues` | `{recipe, mapper, why}` for a mapper an output names that resolves to no type — one row in 42.20.4 (`ExtractIronFromIronOre` / `SmeltMapper`, which writes only a `default`) |
| `foodJoinMisses` | every output type that `items/food.txt` really defines and `data/food-items.json` has no row for — empty in 42.20.4, and the file says so rather than leaving it implied |

### Evolved recipes

`data/evolved-recipes.csv` is 6 881 rows and 13 columns, one per recipe-and-ingredient pair, and `data/evolved-recipes.json` is a `meta` block with 63 recipes and 0 unmatched keys at 7.7 MB, carrying the full `at0` and `at10` blocks the CSV only samples, in the 2026-09-10 scan [#0736/C/snapshot]:

| # | Column | Type | From |
|---|---|---|---|
| 1 | `recipe` | string | the `evolvedrecipe` block name |
| 2 | `resultItem` | string | `ResultItem`, as written (`Base.Salad`) — the game's own `getResultItem()` strips the module |
| 3 | `item` | string | the ingredient's full type (`Base.Lettuce`) |
| 4 | `use` | int | the `<use>` half of the item's `EvolvedRecipe` key: hunger points the key asks for |
| 5 | `requiresCooked` | bool | the key's `Cooked` suffix |
| 6 | `spice` | bool | the item's `Spice` — a spice transfers no hunger and no macros |
| 7 | `share0` | float | derived: the fraction of the ingredient consumed at Cooking 0 |
| 8 | `kcal0` | float | derived: what it adds to the dish at Cooking 0 |
| 9 | `carbs0` | float | derived, same level |
| 10 | `lipids0` | float | derived, same level |
| 11 | `proteins0` | float | derived, same level |
| 12 | `share10` | float | derived: the fraction consumed at Cooking 10. On **all 6 881 rows** `share10 == 0.70 × share0`, with **no exceptions — the 59 clamped rows included**. The clamp is what makes the relation hold: it caps `hunger` at the ingredient's own `abs(HungerChange)` *before* the skill reduction, so `share` is `(1 − 0.03 × level)` of the level-0 share instead of saturating at 1.0 |
| 13 | `kcal10` | float | derived: what it adds at Cooking 10 (`×1.6667` skill bonus on a smaller share) |

A recipe record in the JSON carries `name`, `module`, `sourceFile`, `sourceLine`, `displayName` (the `Name` key), `baseItem`, `resultItem`, `template`, `maxItems`, `cookable`, `canAddSpicesEmpty`, `addIngredientIfCooked`, `addIngredientSound`, `minimumWater`, `isHidden`, `allowFrozenItem` (the two loader-only keys, `null` on every recipe), `props` and `ingredients`, `cookable` being the script value ([Columns](#columns)).
An ingredient row carries `item`, `key` (the raw script part, such as `ConeIceCream:1`), `duplicateKeys` (the keys collapsed into this row), `use`, `requiresCooked`, `spice`, `evolvedRecipeName`, `resolvedVia` (`name`, `template` or `both`), `absentMacros` (which of the macros the item writes no line for, so a `0.0` contribution is readable as absent rather than measured), `sourceFile`, `sourceLine`, and the two contribution blocks `at0` and `at10`.
A contribution block carries `use`, `hunger`, `hungerAfterSkill`, `share`, `skillBonus`, `hungerClamped` (the key asked for more hunger than the item carries, so the game's clamp bit), `thirstSkipped` (the item is tagged `DRIED_FOOD`, so its thirst line is skipped), `spice`, `reason`, `note`, then `calories`, `carbohydrates`, `lipids`, `proteins` and `thirstChange`, its floats rounded to six places.
`unmatchedKeys` records `EvolvedRecipe` keys that reach no recipe, and an unmatched key is recorded, never guessed at; `meta` carries `build`, `generated`, `tool` and `sources` as the recipe JSON does, `cookingLevels`, and a `counts` block whose census is [Counts](#counts).

### Mod inventory and workshop search

`data/mod-inventory.json` is a bare JSON array with no CSV twin; its record and fields are [Mod inventory](#mod-inventory).
`data/workshop-search.json` is a `meta` block and a `results` array, and `data/workshop-search.csv` is the same rows flat without the JSON-only `grade` and `unblock`; the row shape is [Workshop rows](#workshop-rows).
Its `meta` carries `build`, `generated`, `fetched` (the stamp every count needs), `tool`, `terms`, `source_url_pattern` (the browse and item URL templates, so a row can be re-checked by hand), `details_ids` (which rows the details pass was allowed to ask for, kept as the tokens passed), `corpus` (the inventory path and its size as the join read it), `per_term`, `counts` and `notes`.
`counts.details_incomplete` must stay zero, because a read that reports no error owes the row a file size.
`meta.fill` is a list with one `{at, ids, fetched, failed}` entry per `--fill` pass: a fill re-reads rows without re-sweeping, so the row set, the terms and `meta.fetched` stay as the browse pass left them and the file still says when each column was read.

<a id="fidelity-links"></a>
## Fidelity links

This page owns no measurement of a dataset against the running game; the rows that measured them live on the `facts/` pages and are linked here without their numbers.

- The food dataset against the game — the script-manager census [#0608/M/n=2], the live fluid id set [#0615/M/n=2], the field-for-field spot checks [#0609/M/n=10], the drink rows' missing `Food` getters [#0604/M/n=2], the absent-against-zero read-backs [#0619/M/n=1, #0620/M/n=1, #0621/M/n=1], the fluid join [#0624/M/n=2] and the drink probe of the per-litre arithmetic [#0631/M/n=1, #0634/M/n=1, #0635/M/n=1, #0636/M/n=1, #0637/M/n=3] — is [food-item-model.md](../facts/food-item-model.md#dataset-fidelity).
- The recipe datasets against the game — the script-manager census [#0679/M/n=1], the craft field-for-field comparison and its offline replay [#0680/M/n=10, #0762/C/arith.], and the live evolved ingredient lists with their set-equality [#0726/M/n=5, #0727/M/arith.] — are [cooking-and-recipes.md](../facts/cooking-and-recipes.md#dataset-fidelity).
- The evolved dataset against the game — the generated `Salad` rows against the measured dish [#0734/M/arith.] — is [cooking-and-recipes.md](../facts/cooking-and-recipes.md#evolved), and the item-to-recipe join checked live — the `Salad:` key count, the `Cookable` presence read and the module-stripped result item [#0763/M/n=2, #0766/M/n=1, #0767/M/n=5] — is [cooking-and-recipes.md](../facts/cooking-and-recipes.md#evolved-join).
- The measured half of the input-amount rule every craft delta rests on, the per-use probe [#0712/M/n=3], is [cooking-and-recipes.md](../facts/cooking-and-recipes.md#uses).
- Why the dataset answers what an item is on either side — both sides load the same script definitions and no packet carries one — is [loader-and-scripts.md](../platform/loader-and-scripts.md#per-side-load) [#0646/C/inference].

## Open
<a id="open"></a>

- Whether the 16 unresolved `ReplaceOn*` targets should be resolved against a wider item scan is open: 15 are ordinary items outside the food and drink set and the sixteenth is the `Base.MugRed` defect, an item `42.20.4` names but never defines, in the 2026-09-10 scan — settled by an item scan wider than the food and drink set showing whether any of the 15 ordinary targets is an item a nutrition consumer of the dataset needs [#0663/C/snapshot/open].
- Four fluid-only property shapes have no row in the 114-key table — `alcohol` in a fluid's `Properties` and the `Poison` block's `maxEffect`, `minAmount` and `diluteRatio` — while `fluReduction` and `painReduction` are not among them, being in the table and merely having no column, in the 2026-09-10 scan — settled by giving the four shapes rows in [the key reference](../facts/food-item-model.md#script-keys) [#0664/C/snapshot/open].
- A pick-random row's nutrition numbers are one draw and not an expectation over the pool, so anything that averages or worst-cases a spawn has to fan out through `fluid_ids` into the `fluids` records, in the 2026-09-10 scan — settled by a decision on whether the dataset publishes an expectation over the pool, which no scan computes [#0665/C/snapshot/open].
- Fluid containers have no live census route: the script `Item` exposes no component accessor to Kahlua, so the 133 count is scanner-only and only fluid definitions can be read back, a code read with no live route on `42.20.4` — settled by a live read of an item's components, which that build does not expose [#0672/C/C-only/open].
- How the game picks a container's spawn fill between `InitialPercentMin` and `InitialPercentMax` is read but not measured, and whether the dataset should carry the two bounds as columns is open with it; no run has watched a part-filled container spawn, both drinks measured being full containers — settled by spawning several `Base.WineOpen` and reading each instance's fill, whose draws against its range separate a uniform draw in litres from a fixed fraction [#0674/C/C-only/open].
- Whether the 202 `component CraftRecipe` entity build recipes belong in a third dataset, and whether any of them consumes food, is open; they are outside the recipe scan's scope and `meta.counts.componentCraftRecipes` keeps the two universes reconcilable, in the 2026-09-10 scan — settled by scanning those blocks' `inputs` against the food dataset [#0777/C/snapshot/open].
- `data/food-items.json` carries no `UseDelta` column, so the drainable charging rule is unconditional where the jar's own test is drainable and `UseDelta` below 1; both vanilla drainable inputs are cigarette packs with null macros, but a modded drainable food input with real macros would be weighed at 0 with only the note saying why, in the 2026-09-10 scan — settled by a `UseDelta` column the rule can test [#0781/C/snapshot/open].
- How many item pages a session may read is not modelled and no figure should be quoted for it: what is recorded is four dated observations and no rule fitted to them — a run that reached the alternate template after three item pages, a run that met it from the first request, the committed sweep that read all nine pages it asked for unthrottled, and a top-up pass thirty minutes later that read six more in 24 seconds unthrottled — four observations on one afternoon, 2026-09-10, from one machine; settled only by more observations than that afternoon's four [#1941/C/snapshot].
