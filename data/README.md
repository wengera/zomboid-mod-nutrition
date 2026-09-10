# Data

Generated datasets (do not hand-edit): food-items, recipes, evolved-recipes,
mod overlays. Regenerate with tools/ scanners. The **JSON** of a pair carries the
build it was generated from, in its `meta` block; the **CSV deliberately
carries no stamp row** — a `meta` line above the header would break every
`csv.reader` consumer — and is documented instead by its JSON twin's `meta`
and by this file (logged in [`docs/decisions.md`](../docs/decisions.md),
2026-09-10, slice 05).

## food-items

`data/food-items.json` + `data/food-items.csv`, written by
`python tools/food_scan.py` from the 42.20.4 scripts under
`media/scripts/generated/`. Evidence grade **C** throughout: every value is a
line in a shipped script file, and every record names the file and line it
came from — bar the columns marked *derived* below, which are arithmetic on
those lines (`C (arith.)`) and show their arithmetic. Nothing is measured,
inferred or defaulted here — the live checks are `testing/`, and a key a
script does not write has no value in this dataset.

**Read `nutrition_basis` before you read a nutrition column.** An item's food
keys are per item; a fluid's `Properties` are per **litre**, and a drink row's
nutrition is joined from a fluid. `Base.Apple` really is 95 kcal, but
`Base.Pop2` is not 400 kcal — Cola is 400 kcal per litre and the can holds
0.3 L, so the can is 120. Every row says which unit it is in, and a
fluid-sourced row also carries the multiplied-out
`*_per_container` columns; summing `calories` across kinds without looking at
`nutrition_basis` is wrong by the capacity factor. See § Per litre, not per
item.

**The selection rule** (`food_scan.select`, four rules, first match wins):

| kind | rule | count |
|---|---|---|
| `food` | every `item` in `items/food.txt` with `ItemType = base:food` | 722 |
| `drainable` | every `item` in `items/drainable.txt` with `ItemType = base:drainable` | 150 |
| `fluid_container` | every `item` in any `items/*.txt` owning a `component FluidContainer` | 133 |
| `fluid` | every `fluid` in `fluids.txt`, `fluids_Alcoholic.txt`, `fluids_Beverages.txt` | 61 |

The three item rules are disjoint in 42.20.4, so the CSV has 1005 rows.
Fluids are joined into those rows and also kept whole under the JSON's
`fluids` key; they are never rows of their own.

### CSV columns

61 columns: the 59 below plus the trailing `source_file`, `source_line`.
**An absent key is the empty string, never `0`** — `Base.Salt` has no
`Calories` line, so its `calories` cell is empty, and a script that really
writes `0` still prints `0`. In the JSON the same absence is `null`. Booleans
print as `true` / `false`; list columns join their parts with `;`.

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
| 11 | `nutrition_basis` | string | derived: **which unit columns 12–17 and 31–38 are in** — `per_item` for a row that fills them from its own keys, `per_litre` for a fluid-sourced row, empty for the 280 rows that name no nutrition source. (Carrying no nutrition *value* is a wider set: 290 rows do, the extra 10 being `per_litre` rows joined to a fluid with no `Properties` block or with only `alcohol`.) See § Per litre, not per item |
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
| 47 | `fluid_ids` | list `;` | each `Fluids.fluid` value's first `:` field, in file order — a pick-random container either repeats one id (`HairDyeCommon` lists `HairDye` 8 times) or lists several different ones, and then only the first fills the nutrition columns: see the fluid join below. In the JSON, `[]` is a container that lists no fluid (an empty vessel, 61 of them) and `null` is a row that is not a container |
| 48 | `fluid_share` | float | derived: the **first** `fluid =` value's second `:` field (`Cola:1.0` → `1.0`), or `1.0` when the line writes only an id. Empty on a container that lists no fluid. Every 42.20.4 share is `1.0` except `Base.BucketWaterDebug`'s `Water:10.0` |
| 49 | `fluid_fill_litres` | float | derived: `min(fluid_capacity × fluid_share, fluid_capacity)` — the litres of a **full** container at the listed share, and the multiplier of columns 52–57. Equals `fluid_capacity` on all 72 filled rows in 42.20.4. **It is not always the spawn fill:** 14 containers also write `InitialPercentMin` / `InitialPercentMax` (`items/normal.txt:14314`–`:14315`, `InitialPercentMin = 0.0` / `InitialPercentMax = 1.0` on `Base.Flask`; counted as `meta.counts.fluid_containers_initial_percent`) and spawn part-filled at a random draw this column does not model — see § Per litre, not per item |
| 50 | `fluid_pick_random` | bool | the component's `PickRandomFluid` — the container fills from a pool, so its nutrition is **one draw**, not the item's value. `false` on a container that does not write the key (124 of the 133); empty on a row that is not a container |
| 51 | `drinkable` | bool | derived: `fluid_capacity <= 3.0`, the gate `ISInventoryPaneContextMenu.lua:2318` puts on the Drink menu. 16 of the 133 containers fail it and can only be poured or emptied |
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

Columns 48–57 are empty on every row that is not a `fluid_container`, and
52–57 are empty on a container that lists no fluid or whose fluid writes no
such key — `× 10 L` of a key `fluid Water` never writes is still nothing, not
`0.0`.

Types follow the loader (`Item.DoParam`), via `food_scan.KEY_TYPES`: only the
literal `true` is true, and an int-typed key holding an integral float literal
comes back as an int (`UnhappyChange = -10.0` → `-10`).

**The fluid join.** A `fluid_container` row takes the **first** fluid its
`Fluids` block lists: `nutrition_source` becomes `fluid:<id>`,
`nutrition_basis` becomes `per_litre`, and columns 12–17 and 31–38 come from
that fluid's `Properties` block instead of the item's own keys. In 42.20.4 no
fluid-container item writes a nutrition key of its own, so nothing is
overwritten; 10 of the 61 fluids have no `Properties` block at all, so
`fluid:HairDye` with empty nutrition is a correct row, not a gap. `alcohol`,
`fluReduction` and `painReduction` have no column and stay in the fluid
record's `properties_raw`.

### Per litre, not per item

A `fluid`'s `Properties` are the effect of **one litre** of that fluid, so the
joined columns on a `fluid_container` row are in a different unit from the same
columns on a `food` row. `nutrition_basis` records which, and columns 52–57
resolve it. The chain below is grade **C**, from the 42.20.4 jar; the
arithmetic it produces is **C + M** since the drink probe (see *Measured*
below). The whole read, with every address, is
[`.superpowers/sdd/05-food-scanner/q3-fluid-nutrition-notes.md`](../.superpowers/sdd/05-food-scanner/q3-fluid-nutrition-notes.md).

- **The loader stores the script value as written.**
  `FluidDefinitionScript.LoadProperties @0–@453 L367–L410` parses each of the
  fifteen keys with `Float.parseFloat` and no arithmetic.
- **The container multiplies by its litres.**
  `FluidContainer.recalculateCaches @222–@250 L631–L632` does
  `propertiesCache.addFromMultiplied(fluid.getProperties(), litres)`, so
  `FluidContainer.getProperties()` is already litres-weighted.
- **Drinking spends that aggregate.**
  `IsoGameCharacter.DrinkFluid @23–@100 L5878–L5881` writes
  `nutrition.setX(getX() + fc.getProperties().getX() * f)`, with `f` the share
  of the contents drunk — so a full container drunk to the bottom delivers
  exactly columns 52–57.
- **The litres are the full container's.** `getInitialAmount()` defaults to
  `Capacity` when the script writes no initial amount
  (`FluidContainerScript @0–@11 L387-L388`), `addInitialFluid @11–@17 L132`
  multiplies it by the share and `addFluid @30–@45 L1003-L1004` clamps it to
  the capacity — which is `fluid_fill_litres`. 14 containers **do** write one,
  and spawn part-filled: see the caveat below.

`Base.Pop2`, worked through: Cola is `Calories = 400`, `Carbohydrates = 104`,
`HungerChange = -12`, `ThirstChange = -30` per litre
(`fluids_Beverages.txt:14`–`:19`); the can's `Capacity` is `0.3` and its share
`1.0`, so `fluid_fill_litres = 0.3` and the can delivers `120.0` kcal, `31.2` g
carbs, `-3.6` hunger and `-9.0` thirst. The raw per-litre values stay in
columns 12–17 unchanged.

**Units are script units on both sides, so the two are comparable.** The
`/100` that turns `hunger_change` / `thirst_change` / `stress_change` /
`fatigue_change` into stat-bar units is **not** applied here, for a fluid or
for an item: `FluidDefinitionScript.getHungerChange @0–@10 L186` divides,
`getCalories @0–@7 L202` does not, and `Item.InstanceItem` does the same on the
item side. So a can's `hunger_change_per_container` of `-3.6` is directly
comparable to an apple's `hunger_change` of `-16`, and both become stat units
by dividing by 100. Three traps that follow from the same asymmetry:

- `endurance_change` is `/100` for an **item** (`Item.InstanceItem`) but **not**
  for a fluid (`FluidDefinitionScript.getEnduranceChange @0–@7 L230`). No
  shipped fluid writes a non-zero one, so this is latent — but a modded fluid
  would be off by 100×.
- `unhappy_change` on a fluid row is applied **twice** when drunk:
  `DrinkFluid @222–@237 L5893` adds it to BOREDOM and `@238–@253 L5894` adds it
  again to UNHAPPINESS. A mood delta off this dataset is
  `2 × unhappy_change × fluid_fill_litres`.
- `unhappy_change`, `food_sickness_change` and the uncolumned `alcohol` /
  `fluReduction` / `painReduction` are unscaled on both sides.

An absent `Properties` key means the engine uses `0`, not "unknown"
(`FluidDefinitionScript.<init> @80–@229 L101–L116` registers all fifteen with
`addProperty(name, 0.0f)`) — but the dataset still reports it empty, because no
line in the file wrote it. A fluid with no `Properties` block at all
(`Fluid.setScript @45–@49 L281`) gets `properties = null` and contributes
nothing to anything.

**Measured, and no longer C-only.** Slice 05's live drink probe
(`exp05b-20260910-093307`,
[`drink-probe.json`](../testing/artifacts/exp05b-20260910-093307/drink-probe.json))
drank three containers on the dedicated server, reading both stores on either
side of the single `DrinkFluid` call. A full 0.3 L `Base.Pop2` wrote
**+120.000031 kcal**, **+31.200001 g** carbs, **−0.036** hunger and **−0.090**
thirst — columns 52–57 exactly, with the `/100` applied to the two stat
columns on the way to `Stats`. The same can at `f = 0.5` wrote **+60.0** /
**+15.6** and was left holding 0.15 L; a 0.2 L `Base.JuiceBox` wrote **+80.0** /
**+23.999996**. So `per-litre × fluid_fill_litres × f` is **C + M**, on two
fluids, two capacities and two fractions, and slice 01's open question #11 is
closed. Cite the artifact's `atomic` / `container` blocks — `summary.all_matched`
is a *do not cite* row in
[`testing/artifacts/README.md`](../testing/artifacts/README.md).

**`fluid_fill_litres` is a full container, and 14 containers spawn
part-filled.** `InitialPercentMin` / `InitialPercentMax` are read into
`initialAmountMin` / `initialAmountMax` (`FluidContainerScript.load @207–@261
L202–L207`), and `getInitialAmount @12–@40 L390–L393` then returns `min` when
the two are equal and `Rand.Next(min, max)` — a uniform draw — otherwise. It is
rolled once per container in `readFromScript @93–@106 L108`, before the
`:share` multiply and the capacity clamp. **The value is litres, not a
percentage**, despite the key name: nothing multiplies it by `Capacity`. So
`Base.CanteenCowboy` (`Capacity 1.8`, `0.0`–`1.0`) spawns holding at most 1 L
of its 1.8, `Base.WineOpen` (`Capacity 1.0`, `0.05`–`0.85`,
`items/normal.txt:6630`–`:6631`) can never spawn full, and `Base.WaterDish`
(`Capacity 0.3`, `0.05`–`0.95`) is clamped back to 0.3 whenever the draw
exceeds it. The 14 are `meta.counts.fluid_containers_initial_percent`, 12 of
them listing a fluid; the scanner does not model the draw, so on those rows
`fluid_fill_litres` and columns 52–57 are the **full**-container figures and
what spawns is a random fraction of them. Every other filled row spawns full.
Ev **C**, from the 42.20.4 jar.

**A pick-random container's nutrition is one of several fills, not the whole
truth.** `FluidContainer.readFromScript @142–@183 L112–L115` draws **one** of
the listed fluids with `Rand.Next(size)` when the component sets
`PickRandomFluid`, and fills the container with **every** listed fluid when it
does not (`@186–@228 L116–L119`). Nine containers set it and so carry
`fluid_pick_random = true`; five of those list several *different* fluids — `Base.Flask`,
`Base.PopBottle`, `Base.PopBottleRare`, `Base.SodaCan`, `Base.WaterBottle`,
counted as `meta.counts.multi_fluid_containers` — and the row carries only the
**first** one's nutrition: `Base.Flask` reports Gin's 2 630 kcal though the
same flask can hold Rum, Scotch, Vodka or Whiskey, and `Base.PopBottle`
reports Cola's 400 though the `ColaDiet` it may hold instead is `0.0`.
`fluid_ids` keeps the whole set, so the alternatives are one lookup into
`fluids` away; anything that averages or worst-cases a spawn must do it from
there, not from the row. The other four multi-line containers repeat a single
id (`HairDyeCommon` lists `HairDye` 8 times) and so have nothing to pick
between.

### JSON

`{"meta": {...}, "items": [...], "fluids": [...]}`, `indent=1`, items and
fluids sorted by `id`. An item record carries every column above (absent =
`null`) plus `props_raw`: the item block's own `Key = Value` lines verbatim,
untyped and unsplit, keys sorted, a key written twice becoming a list (the 7
repeated `SoundMap` lines survive there). Nested blocks are not flattened into
it — a container's `Capacity` reaches the record only as `fluid_capacity`.

A fluid record carries `id`, `module`, `name`, `kind`, `display_name`,
`display_name_key`, `color_reference`, `categories`, the 14 nutrition columns
above — always **per litre**, which is why a fluid record has no
`nutrition_basis` and no `*_per_container` field: it has no capacity of its own
to multiply by — `properties_raw` (the `Properties` block verbatim), `poison`
(the `Poison` block, or `null`), `props_raw`, `source_file` and `source_line`.

`meta` keys:

| Key | Meaning |
|---|---|
| `build` | game build the scripts were read from (`42.20.4`) |
| `jar_hash` | the disassembled jar this build's key table was checked against (`b0bbce05d5`) |
| `generated` | UTC date of the run |
| `tool` | `tools/food_scan.py` |
| `sources` | the 18 script paths read, relative to `media/scripts/generated/` |
| `counts` | `food`, `drainable`, `fluid_container`, `fluids`, `multi_fluid_containers` (containers whose `fluid_ids` holds more than one distinct id — see the fluid join), `fluid_containers_filled` / `fluid_containers_pick_random` / `fluid_containers_empty` (the fill split over the same 133 rows: 72 list a fluid to spawn holding, 9 of those from a pool, and 61 list none), `fluid_containers_initial_percent` (14 — the subset of those 133 that also writes `InitialPercentMin` / `InitialPercentMax` and therefore spawns **part**-filled at a random draw, so `fluid_fill_litres` is its full-container figure and not its spawn fill; see § Per litre, not per item), `unresolved_links` |
| `unknown_keys` | every script key the dataset carries that the item key table does not cover, so it is kept as a raw string — weapon and clothing keys ride along on fluid-container items, and `DisplayName`, `ColorReference`, `alcohol` and the `Poison` block are the fluid files' own. Three entries are listed without being raw: the component's `Capacity`, `fluid` and `PickRandomFluid`, which never reach a `props_raw` because the dataset types them itself into `fluid_capacity`, `fluid_ids` / `fluid_share` and `fluid_pick_random`; they are listed because the **key** is outside the item table, not because the value stayed a string |
| `unresolved_links` | `{item, key, target}` for every `ReplaceOnCooked` / `ReplaceOnRotten` / `ReplaceOnUse` / `ReplaceOnDeplete` target that is not a record of this dataset — mostly pans and empty containers, plus `Base.HotDrinkRed` → `Base.MugRed`, which 42.20.4 names but never defines |
| `missing_display_names` | ids with no EN name; a fluid appears as `fluid:<id>` |
| `unresolved_fluid_refs` | `{item, fluid_id}` for a `Fluids.fluid` naming a fluid no file defines (empty in 42.20.4) |

All four `ReplaceOn*` keys — `ReplaceOnCooked`, `ReplaceOnRotten`,
`ReplaceOnUse`, `ReplaceOnDeplete` — have a column of their own and are
resolved against the dataset's own ids, so a row shows the link and `meta`
shows the miss. Each is kept verbatim in `props_raw` as well.

## recipes

`data/recipes.json` + `data/recipes.csv`, written by
`python tools/recipe_scan.py --out-dir data` from the 42.20.4 scripts under
`media/scripts/` — **one row per `craftRecipe` block**, 969 of them in 74
files, with its inputs and outputs parsed line by line. Evidence grade **C**
for everything read off a script line (every record names its
`sourceFile:sourceLine`); the `delta` block is `C (arith.)` — arithmetic on
those lines and on `data/food-items.json`, under a rule whose measured half is
`testing/artifacts/exp06b-20260910-120123/use-probe.json`. The mechanism, the
refusals and the live cross-check are
[`docs/vanilla/recipes-dataset-notes.md`](../docs/vanilla/recipes-dataset-notes.md);
this section is the column authority.

**An input amount is a count of *uses*, not of items, unless the line carries
`flags[ItemCount]`** — and for a `Food` one use is one raw `HungerChange`
point, so `item 40 [Base.MincedMeat]` is one whole tub and
`item 10 [Base.Icecream]` is a third of one. Every `delta*` column is computed
that way. **A delta term is only ever taken from a `nutrition_basis =
per_item` row**: a drink (`per_litre`) and a row with no nutrition key are
refused by name in `deltaReason`, never converted, so the two units of
§ Per litre, not per item are never added together.

### CSV columns

37 columns, one row per recipe, 969 rows. **An absent key is the empty string,
never `0`**, exactly as in food-items; booleans print `true` / `false`; list
columns join their parts with `;`.

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
| 19 | `inputCount` | int | derived: **the loader's own `inputs.size()`** — a `-`/`+` sub-line belongs to the input above it and does not count (`CraftRecipe.LoadIO @218–@317`, `getInputCount @0–@7 L257`) |
| 20 | `outputTypes` | list `;` | derived: every distinct output type, a `mapper:<name>` line resolved to every result of that mapper except the literal `default` |
| 21 | `itemMappers` | list `;` | the mapper names this recipe declares |
| 22 | `fluidIO` | bool | derived: the recipe has at least one fluid line (53 recipes). Fluid nutrition is **not** in the delta |
| 23 | `split` | bool | derived: an input carries `flags[InheritFood]`, so each output takes `1/outputCount` of the *consumed instance's* macros and the delta is 0 by construction (17 recipes) |
| 24 | `datasetTypes` | list `;` | derived: the IO types that are a `data/food-items.json` row **at all**, vessels included |
| 25 | `foodItemTypes` | list `;` | derived: the `food` / `drainable` subset of column 24 — the rows a delta may weigh |
| 26 | `deltaCalories` | float | derived `C (arith.)`: Σ(outputs × their own script macros) − Σ(what each consumed input really spends). Empty — never `0` — when `deltaReason` says why |
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

The delta's `notes` and `destroyWaste` are **JSON-only** (a list of sentences
and a six-macro dict); columns 26–32 are the whole of the delta the flat file
carries.

### JSON

`{"meta": {...}, "recipes": [...969...], "replacements": [...163...]}`,
`indent=1`, recipes sorted by `name`, LF endings, byte-stable across runs
**within one UTC day** — `meta.generated` is today's UTC *date*, so it is the
one line a rebuild after midnight UTC changes. A
recipe record carries every column above except the six derived `input*` /
`output*` flattenings, which it keeps structured instead, plus:

- **`inputs` / `outputs`** — the parsed IO lines. `null` when the block is
  absent and `[]` when it is present and empty (11 and 26 recipes). Every line
  carries all 17 fields whether or not it writes them: `kind` (`item` /
  `fluid`), `amount`, `variable` (`"1:20"` for a `variable[…]` line, and then
  `amount` is `null`), `types`, `tags`, `categories`, `mode`, `flags`,
  `mappers`, `mapper`, `overlayMapper`, `extras`, `consumed`
  (**`mode != "keep"`**), `amountIsItemCount`, `amountUses`, `subLines` (the
  `-`/`+` lines the loader attaches to this one) and `raw`.
- **`itemMappers`** `{mapper: {result: source}}` — the contract dict, which
  keeps the *last* source of a repeated result — beside **`itemMapperPairs`**
  `{mapper: [[result, source], …]}`, every line in file order (56 mappers name
  one result twice, so the dict alone would lose a pair), and
  **`itemMapperDefaults`** `{mapper: default|null}` (134 mappers write one).
- **`overlayMapper`** — the `{default, pairs}` of an `overlayMapper` block
  (3 recipes), or `null`.
- **`props`** — every key no column claims, raw: `overlayStyle`, `OnTest`,
  `recipeGroup`, `Icon`, `ResearchSkillLevel`, `ResearchAny` in 42.20.4.
- **`delta`** — `{calories, carbohydrates, lipids, proteins, hungerChange,
  thirstChange, absentMacros, destroyWaste, notes}`, or `null` with the reason
  in `deltaReason`. `destroyWaste` is the six macros of the remainder a
  `mode:destroy` line annihilates beyond what it charges, and is **`null`
  unless one of those six is non-zero** — 0 recipes in 42.20.4. One row
  (`UnpackCigarettes`) does round its charge up to a whole item, but the item
  is the drainable `Base.CigarettePack`, which writes no macro key at all, so
  there is nothing to publish and six zeroes would read as a measured "0.0 kcal
  destroyed". `notes` names each weighing decision that is not the plain rule
  (a drainable input, a food with no usable `HungerChange`, a destroy round-up
  — and, on that one row, which of the two wins).

**`replacements`** is a third top-level array, after `recipes`, holding one
record per `ReplaceOn{Cooked,Rotten,Use,Deplete}` link a food row declares:
`{from, to, trigger, sourceFile, sourceLine, delta, deltaReason}`, sorted by
trigger (cooked, rotten, use, deplete) then source then target. 163 links —
**3 cooked, 8 rotten, 110 use, 42 deplete** — of which 12 carry a delta and 151
are refused by name (114 `no-nutrition`, 37 `not-in-dataset`). `sourceLine` is
the **item block's** header line, the way every other record here anchors, not
the line of the `ReplaceOn*` key. The delta is one item for one item, with the
same `absentMacros` rule as a recipe delta.

`meta` keys:

| Key | Meaning |
|---|---|
| `build` / `generated` / `tool` | `42.20.4 (b0bbce05d5)`, the UTC date of the run, `tools/recipe_scan.py` |
| `sources` | `scripts` (the root walked), `files` (the 74 a recipe was read from) and `food_items` — the joined dataset's own `path` / `build` / `jar_hash` / `generated`, so a rebuild of one half against a stale other half is visible in the file |
| `counts` | `craftRecipes` 969, `files` 74, `scriptFiles` 1004, `legacyRecipeBlocks` 0, `componentCraftRecipes` 202 (an entity's own build recipes — counted because a raw grep of the scripts sees their `inputs` blocks too, **not** rows of this dataset), `itemMappers` 225, `overlayMappers` 3, `recipesWithoutOutputs` 11, `recipesWithEmptyOutputs` 26, `fluidRecipes` 53, `outputItemTypes` 1693, `outputItemTypesInDataset` 295, `outputItemTypesInFoodDataset` 262, `recipesTouchingDatasetRow` 413, `recipesTouchingFood` 375, `recipesWithFoodOutput` 182, `foodJoinMisses` 0, `recipesWithDelta` 31, `recipesWithNonZeroCalorieDelta` 15, `recipesWithCaloriesAbsentOnEverySide` 3, `splitRecipes` 17, `splitRecipesWithDelta` 8, `recipesWithDestroyWaste` **0** (rows publishing a non-null `destroyWaste`; the one `mode:destroy` round-up, `UnpackCigarettes`, wastes a drainable that carries no macros — see the `delta` bullet above), `inputSubLines` 55 |
| `outputMapperIssues` | `{recipe, mapper, why}` for a mapper an output names that resolves to no type — one row in 42.20.4 (`ExtractIronFromIronOre` / `SmeltMapper`, which writes only a `default`) |
| `foodJoinMisses` | every output type that `items/food.txt` really defines and `data/food-items.json` has no row for — empty in 42.20.4, and the file says so rather than leaving it implied |

## evolved-recipes

`data/evolved-recipes.json` + `data/evolved-recipes.csv`, written by the same
run of `tools/recipe_scan.py` — **the 63 `evolvedrecipe` blocks** (62 in
`generated/evolvedrecipes.txt`, `AddBaitToChum` in
`generated/recipes/recipes_fishing_evolvedrecipe.txt`) resolved to their
ingredient lists the way the game resolves them, each ingredient carrying what
it contributes to the dish at Cooking **0** and Cooking **10**. Grade **C** for
the script values, `C (arith.)` for the two contribution blocks — the
summation itself is
[`docs/vanilla/food-item-model.md`](../docs/vanilla/food-item-model.md)
§ Evolved recipes, cited and not re-derived.

**The join is the game's, not a name match.** An item's
`EvolvedRecipe = <Name>:<use>` key reaches a recipe through an exact-name
lookup **and** through every recipe whose `Template` matches
case-insensitively, with five parse-time aliases applied first
(`RicePot`/`RicePan` → `Rice`, `PastaPot`/`PastaPan` → `Pasta`,
`Roasted Vegetables` → `Stir fry`). **374 carriers joined across 63 recipes**
yield **6 902** (key part, recipe) joins → **6 881 rows** (21 land on the same
(recipe, item) pair twice and are collapsed, with the collapsed keys kept),
**0 unmatched**. It is not a product: a carrier writes as many key parts as it
writes, and each part reaches however many recipes match it.

### CSV columns

13 columns, one row per (recipe, ingredient) pair, 6 881 rows — the sampled
reading; the JSON carries both contribution blocks in full.

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

### JSON

`{"meta": {...}, "recipes": [...63...], "unmatchedKeys": []}`, `indent=1`. A
recipe record carries `name`, `module`, `sourceFile`, `sourceLine`,
`displayName` (the `Name` key), `baseItem`, `resultItem`, `template`,
`maxItems`, `cookable`, `canAddSpicesEmpty`, `addIngredientIfCooked`,
`addIngredientSound`, `minimumWater`, `isHidden`, `allowFrozenItem` (the two
loader-only keys, `null` on all 63), `props` and `ingredients`. **`cookable` is
the script value**: the game's `isCookable()` answers on the *presence* of the
key, so `AddBaitToChum` writes `false` here and the engine says `true` — the
only one of the 63 where the two differ.

An ingredient row carries `item`, `key` (the raw script part, e.g.
`ConeIceCream:1`), `duplicateKeys` (the keys collapsed into this row), `use`,
`requiresCooked`, `spice`, `evolvedRecipeName`, `resolvedVia`
(`name` / `template` / `both` — **`name` alone never happens in vanilla**),
`absentMacros` (which of the five macros the item writes no line for, so a
`0.0` contribution is readable as absent rather than measured), `sourceFile`,
`sourceLine`, and `at0` / `at10`.

A contribution block (`at0`, `at10`) carries `use`, `hunger`,
`hungerAfterSkill`, `share`, `skillBonus`, `hungerClamped` (the key asked for
more hunger than the item carries, so the game's clamp bit — 59 rows),
`thirstSkipped` (the item is tagged `DRIED_FOOD`, so its thirst line is skipped
— 27 rows), `spice`, `reason`, `note`, then `calories`, `carbohydrates`,
`lipids`, `proteins`, `thirstChange`. Floats are rounded to 6 places. A spice
row is **0** in hunger, share and every macro — a *measured* zero, the branch
being modelled; `null` in these datasets means the source writes nothing. The
one branch of the summation not modelled per row is the **rotten** ingredient
(Cooking ≥ 7), which needs an instance's state rather than script data.

`unmatchedKeys` records `EvolvedRecipe` keys that reach no recipe — empty in
42.20.4, and an unmatched key would be recorded, never guessed at.

`meta` keys: `build` / `generated` / `tool` / `sources` as above (its `files`
are the two evolved-recipe scripts), `cookingLevels` `[0, 10]`, and `counts` —
`evolvedRecipes` 63, `carriers` 374 (`carriersFood` 372, `carriersDrainable`
2), `keyParts` 2446, `distinctKeys` 31, `aliasedKeyParts` 5, `cookedSuffixes`
213, `pairs` 6902, `pairsFromFoodTxt` 6858 (the same join counted over
`items/food.txt` alone — the figure that omits the two vinegars), `ingredients`
6881, `duplicateJoins` 21, `unmatchedKeys` 0, `resolvedViaName` 0 /
`resolvedViaTemplate` 4748 / `resolvedViaBoth` 2133, `spiceIngredients` 2522,
`ingredientsRefusedByBasis` 0, `hungerClampRows` 59, `driedFoodThirstRows` 27,
`duplicateRecipeNames` 0.

## mod-inventory

`data/mod-inventory.json`, written by `python tools/mod_inventory.py` from the
**installed workshop tree**
(`D:\SteamLibrary\steamapps\workshop\content\108600`, read and never written) —
one record per mod folder, a bare JSON array, `indent=1`. **230 records across
179 workshop items, swept 2026-09-10 17:47.** Evidence grade **C** for
everything read off a shipped file (`mod.info` values, file counts, regex hit
counts); nothing here is measured in a running game, and a signal count is a
count of regex hits, not of behaviour.

**No `meta` block, and no build stamp** — unlike the four datasets above, this
one describes a *live* tree that Steam rewrites under you (item `3490370700`
was rewritten mid-slice on 2026-09-10 at 13:47). **7 rows' `stats` moved
between the 09-09 and 09-10 sweeps, for two different reasons**: the two
`Skill Recovery Journal` rows (`2503622437`, `3782784855`) moved because the
resolution fix reads their `42.20.1/` folder where the old rule fell back to an
older one, and the other five (`3490370700` ×2, `3623584152`, `3703948448`,
`3745960616`) because Steam rewrote those items' files between the sweeps. Only
2 of the 7 are item `3490370700`. The sweep date above is the stamp; quote a
count from this dataset with it.

**The 17:47 sweep against the 16:20 one is the fix and nothing else.** Exactly
**13 rows** differ, all of them for a reason in the tool: 11 `sandbox_options`
false → true (`common/media` is now read), and 2 script rows losing
commented-out content — `SKITTLE_LongTermPreservation4220`
`script_item_blocks` 17 → **15** with `script_nutrition` 135 → **117**, and
`ZVirusVaccine42BETA` 102 → **86**. No other row moved a byte in that 87
minutes, which is a reading about Steam (it rewrote nothing in the window), not
a guarantee about the next one.

Regenerating is cheap (~2 s) and byte-stable:
the same tree in gives the same bytes out, LF-terminated on every platform
(the writer pins `encoding="utf-8", newline="\n"`, so the file no longer picks
up CRLF when it is generated on Windows — the committed blob was already LF,
`core.autocrlf` having normalised it, so this changed no committed byte).

**`mod_id` is the id the game resolves, and it may be `""`.** The record no
longer falls back to the folder name. Resolution is not this tool's opinion:
`resolve()` calls [`tools/mod_lint.py`](../tools/mod_lint.py)'s `version_dirs`
/ `info_chain` / `read_info` / `media_root`, so `mod.info` is read from the
**newest `42[.x[.y]]/` folder** first, then `common/`, then the mod root — the
order documented in [`docs/testing/profiles.md`](../docs/testing/profiles.md)
§ L0. The pre-slice-08 dataset had its own weaker rule (a `42[.N]` regex, and
only `<mod>/mod.info` was read), so **20 of the 230 rows carried a folder name
instead of the declared id** — including `LongTermPreservation4220`, which
really declares `SKITTLE_LongTermPreservation4220`. A profile's `[[mods]] id`
must be the resolved id, so read `mod_id`, never `folder`. One row's `mod_id`
is `""`: `3782784855/Skill Recovery Journal` ships no `mod.info` anywhere and
is invisible to `pzt.mods.workshop_index()` (229 ids for 230 folders). **52
rows** have `mod_id != mod_id_fallback` — `mod_lint`'s `folder-id` INFO counts
51 of them, because it cannot compare a folder against an id that does not
exist.

**Everything except `bytes` describes the newest version folder only** — the
one `layout` names — and that is a de-duplication rule, not a claim about what
the game loads. A mod that ships the same scripts in `42.14/`, `42.20/` and
`common/` (`ZVirusVaccine42BETA` does) must not have them counted three times,
so one folder is chosen and it is the one the build runs.

Two different kinds of content fall outside it, and only one of them is dead:

- An **older `42.x/`** or a **b41 root `media/`** is genuinely ignored by the
  running build. `3041122351/63Type2Van` writes nutrition keys **only** in its
  root `media/` copy, so its B42 script signal is 0 and its b41 one is 7 — it
  does not touch nutrition on 42.20.4.
- **`common/media` is not.** It is a shipped layout the build *also* loads
  ([`docs/modding/README.md`](../docs/modding/README.md) "picks the highest
  `42.x` ≤ game build; `common/` shared",
  [`docs/modding/patterns.md`](../docs/modding/patterns.md) § 10,
  `mod_lint.media_root`). Its content is simply **not counted here**, and this
  dataset asserts no rule for how the two folders combine — the resolution
  order is still open question 1 in
  [`docs/testing/profiles.md`](../docs/testing/profiles.md) § L0. **177 of the
  230 rows have a `common/media` this scan did not read** (2026-09-10), so a
  zero in `stats` or `signals` is only trustworthy when `media_at` does *not*
  include `common/media` — that list is the guard. `live_media: false` marks
  something narrower: the **24** rows with no live `media/` at all, whose whole
  record is therefore blank.

Do not read `live_media: true` as "the record is complete". On **111** of the
153 rows that have both a live `media/` and a `common/media`, a `stats` bucket
reads 0 while `common/media` holds exactly that kind of file (2026-09-10):
`HayesCustoms` records `models: 0` over 1268 `.fbx` there, `MorePlushies` over
154, and `ZVirusVaccine42BETA` — a `live_media: true` row — hides 12 models, 5
tile packs and 18 sounds the same way. On those 111 rows alone that is 2527
models, 120 sounds, 15 tile packs, 67 client / 13 shared / 12 server Lua files and 3
script files the dataset reports as zero; the true
uncounted total is larger, since a row whose bucket is non-zero can have more
of the same kind in `common/media` as well.

**Measured impact of that gap on the nutrition question: none.** Every
`common/media` in the corpus was swept for the ten `script_nutrition` keys on
2026-09-10 (twice: rounds 1 and 2) and **not one carries a single key**, so no
nutrition candidate is hidden by the scope. For any other question — model
counts, lua architecture, sounds — check `media_at` before believing a zero.

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

**`workshop_item_mtime` is a download stamp, not an update stamp.** Steam
rewrites the mod folder inside an item without touching the item folder:
`3490370700` still reads `2026-08-12T00:03:04` while its
`mods/73fordFalcon/` was rewritten at `2026-09-10 13:47`. Corpus range
`2026-08-12` … `2026-09-04`. For a real "last updated" date, use the Workshop
page.

### The two nutrition signals

Neither column alone is the catalog, and they are counted from different files.
Both script-side counts read the file **comment-stripped**, exactly as
`tools/food_scan.parse_script` does and as the engine's own parser does:
`tools/mod_inventory.py` imports `food_scan._strip_comments` rather than
keeping a second opinion about what the engine ignores, the same delegation
`resolve()` makes to `mod_lint` for identity:

- `signals.food_nutrition` — `getNutrition()`, `setCalories` / `setProteins` /
  `setLipids` / `setCarbohydrates`, or `HungerChange` in any `.lua` under the
  live folder. **11 mods**, led by `simpleStatus` 12, `CleanUI` 11,
  `SkillRecoveryJournal` 8.
- `signals.script_nutrition` — `Calories`, `Carbohydrates`, `Lipids`,
  `Proteins`, `HungerChange`, `ThirstChange`, `DaysFresh`,
  `DaysTotallyRotten`, `FoodType` or `EvolvedRecipe` at the start of a line in
  a `.txt` under `<live>/media/**/scripts`. **9 mods**:
  `SKITTLE_LongTermPreservation4220` 117, `Horse` 116, `OCsPacking` 76,
  `ZVirusVaccine42BETA` 36, `GirthsTweaks` 26, `JadePackingSD` 18, `69mini` 7,
  `SDQuests` 6, `biogas` 1.
- **One mod shows both**: `SKITTLE_LongTermPreservation4220` (117 script, 4
  lua). 19 mods show at least one.

`script_modules` is the override question: a mod writing **`module Base`
overrides vanilla items**; `module <Own>` only adds new ones. Long Term
Preservation declares `module Skittles` alone, so its 15 item definitions all
add.
The value is the raw token after `module`, so a `module LabItems{` written
with the brace on the same line is recorded as `LabItems{`
(`ZVirusVaccine42BETA`).

`script_item_blocks` is an **exact** count of item definitions: `item <Name>`
alone on its line, with or without the opening brace, in the file with its
comments stripped. Anchoring the name to
the end of the line is what separates a definition from a `craftRecipe`'s
inputs and outputs, which are written `item 1 [Base.Bowl]` / `item 1
Base.DriedApple` at the same indentation. The first version of this field used
`^\s*item\s+(\S+)` and could not tell them apart, which inflated it on **113
of the 230 rows** (22231 lines down to 6157 definitions): Long Term
Preservation read 47 for 15 real items, `JadePackingSD` 923 for 125, and three
rows that only ever write recipe inputs — `3621968227/SWMisc_Patches`,
`3624538051/QualityEnhancements`, `3645980077/ProjectArcade` — now read 0,
correctly.

The second cut fixed the opposite error. The name class was `\w[\w.]*`, which
stops at a **hyphen**, and an item id may contain one: `3470426196/KATTAJ1
Military Pack` writes `item Military_ArmsProtectionLower_Patriot_Light-Black`
with the brace on the next line, so 491 of its 492 definitions matched nothing
and the row read **1**. `\w[\w.-]*` recovers exactly those 491 and changes no
other row (corpus total 6157 → **6648**, 2026-09-10); `-` is the only character
outside `[\w.]` any id in the corpus uses, and on vanilla 42.20.4's
`media/scripts` both regexes read the same **5105** definitions, so the widening
adds no false positive on either corpus.

The third cut fixed a **comment** error. All three script regexes ran over the
raw file, so a definition its author had commented out was counted as one; the
engine's parser and `food_scan.parse_script` both ignore `/* … */` and `//`, so
`mod_inventory` strips them first now. **171 of the corpus's 2401 live script
files carry a block comment**, and stripping moved exactly two rows (6648 →
**6630**, 2026-09-10 17:47): `SKITTLE_LongTermPreservation4220` 17 → **15**,
and `ZVirusVaccine42BETA` 102 → **86**, whose `LabItemsOld.txt` (12
definitions) and `LabTestZone.txt` (2) are each commented out **whole**, in one
block. `//` is stripped for the same reason and changes nothing here: one file
in the corpus contains the token and no count in it moves.

The nine `script_nutrition` mods read 15 · 288 · 308 · 86 · 14 · 125 · 32 · 12
· 1 in the order listed above — **881** together (2026-09-10 17:47; 899 before
the comment fix, and unchanged by the hyphen fix — none of
them uses a hyphenated id). Quote it as "items defined"; it counts definitions
in every script file, so for a mod that also ships clothing or vehicles it is
not "food items defined".

## workshop-search

`data/workshop-search.json` + `data/workshop-search.csv`, written by
[`tools/workshop_search.py`](../tools/README.md) from the **public Steam
Workshop browse pages** — eight search terms against the `Build 42`-tagged,
ready-to-use section, one page per term (Steam serves 30 results a page and the
tool does not paginate), then a second pass over a declared subset of item
pages for size/posted/updated, joined to [§ mod-inventory](#mod-inventory) on
`workshop_id`. **212 results over 8 terms → 180 distinct items, 3 of them
installed, fetched 2026-09-10 16:26** (the run itself ran 16:25:31–16:26:22).
A `meta` block and a `results` array, `indent=1`; the CSV is the same 180 rows
flat, **10 columns** (`details_status` after `updated`), minus `grade` and
`unblock` — **14 500 bytes at 2026-09-10 16:56**, half the 30 427 of the first
encoding, which spent a 107-character sentence on each of 171 rows to say that
the row had not been asked for.

**Steam is live and `browsesort=trend` reorders hourly, so every count below
carries the fetch stamp and none of them is quotable without it.** Two browse
passes 34 minutes apart on 2026-09-10 — 15:52 and 16:26 — returned the same
212 / 180 / 3 and the same three installed ids, which says the answer held for
half an hour, not that it is stable. Nothing here was subscribed, downloaded
or written under the workshop root: pages were read once and never faster than
one request a second (browse pages 1 s apart, item pages 4 s), and only the
extracted facts (id, title, size, posted, updated) are recorded — no page is
mirrored.

### The hard constraint: a Workshop row is not a measurable mod

**A result that is not installed cannot be linted, profiled, booted or measured
from this repo.** The workshop tree is read-only here and subscribing needs
Steam and a human, so **177 of the 180 rows (2026-09-10 16:26) are graded W**
— a page title, a size and a date, nothing read off a shipped file — and
every one of them carries the exact `unblock` action that would change that:
*subscribe to `<id>` in Steam, let it download, re-run
`python tools/mod_inventory.py`*. The **3 installed rows** are graded **C**
only because they join to a record in `mod-inventory`, which *is* read off
shipped files; the grade belongs to the inventory, never to the Workshop page.
**Teardown picks come only from the installed corpus** — a W row cannot be
one, however relevant it looks.

### Per term (2026-09-10 16:26)

| Term | Results | Installed | Note |
|---|---|---|---|
| `nutrition` | 30 | 0 | the whole page is third-party nutrition work and **not one item of it is installed here** |
| `vitamin` | 30 | 0 | |
| `malnutrition` | 2 | 0 | the only term that does not fill a page — `3441138219` Protein Shake [B42] and `3516166810` Red Days |
| `diet` | 30 | 1 | the hit is a car mod (see below) |
| `hydration` | 30 | 2 | |
| `food overhaul` | 30 | 0 | |
| `cooking overhaul` | 30 | 0 | |
| `spoilage` | 30 | 0 | |

212 result rows collapse to **180 distinct ids** because **29 ids appear under
more than one term** (`3791169924` Realistic Blood & Transfusion System [B42]
under `nutrition`, `hydration` and `spoilage`); `terms` on the row keeps all
of them, in the order the terms were swept. **0 term failures** — every one
of the eight browse pages parsed.

### The three installed hits (2026-09-10 16:26)

| `workshop_id` | `mod_ids` | Title | Term | Ev |
|---|---|---|---|---|
| `2932547723` | `93townCar` | '93 Lincoln Town Car + Limo | `diet` | C |
| `3759421894` | `BigBottles` | Big Bottles | `hydration` | C |
| `3765241705` | `BeyondTen` | Beyond Ten - Level 15 Skills [B41/B42] | `hydration` | C |

**None of the three is a nutrition mod.** A car, a bottle-capacity tweak and a
skill-cap mod matched the search text, and that is the whole overlap between
what the Workshop surfaces for these terms and what is installed here.

Two facts about coverage follow from that, and both bound what this dataset
may be used for:

- **176 of the 179 installed workshop items are not returned by any of the
  eight terms** (the 16:26 sweep against the inventory as it stood at
  2026-09-10 16:20, 230 records / 179 items) — this is a trend-sorted
  top-30-per-term slice of the Workshop, not a census of it and not a second
  inventory.
- **`3774789651` Long Term Preservation — the installed mod that writes both
  nutrition signals — is in none of the eight pages**, while `3796644824`, a
  third-party patch *to* it, is. Absence from this dataset is not evidence
  about a mod; do not read a missing id as "no such mod".

### The load-bearing not-installed items (2026-09-10 16:26)

Titles and ids verbatim from `data/workshop-search.json`. Every row is **W**,
and the unblock action is the same sentence on each: *subscribe to `<id>` in
Steam, let it download, re-run `python tools/mod_inventory.py`* — which is
what would move it into `mod-inventory` and make it lintable, profilable and
measurable. Until then nothing below is a teardown candidate.

| `workshop_id` | Title | Size | Posted | Updated | Why it is load-bearing | Ev |
|---|---|---|---|---|---|---|
| `3736275816` | ApocalipseBR - Nutrition Sync Fix | 453.434 KB | May 31 @ 7:55am | May 31 @ 11:18am | **someone else hit the MP nutrition-sync problem this library exists to characterise** and shipped a fix for it. Subscribing is the only way to read how; until then we know a title, a size and two dates | W |
| `3796644824` | [NUTRITION LAUNDERING PATCH + FEATURES] Long Term Preservation | 471.224 KB | Sep 6 @ 12:58am | *never* | **a third-party patch to our own top teardown pick** (`3774789651`, installed, 117 `script_nutrition` hits) — its title claims the preservation mod launders nutrition, which is a claim about a mod we *can* read. Subscribe to compare the two script sets; the patch is 4 days old and has never been updated | W |
| `3690404044` | Nutrition Makes Sense | 1.042 MB | Mar 22 @ 4:57pm | Aug 18 @ 5:01pm | the largest of the nutrition-overhaul group, and the one with an add-on ecosystem (`3796753621` Nutrition Makes Sense Immersive Addon is in the same page) | W |
| `3785515388` | Reasonable Nutrition | 145.008 KB | Aug 17 @ 7:44pm | Aug 26 @ 3:49pm | a small, recent take on the same problem — the cheapest comparison read if only one of these is ever subscribed | W |
| `3782835400` | Realistic Nutrition | 636.708 KB | Aug 13 @ 10:59am | *never* | third of the three same-month "nutrition" overhauls; never updated since posting | W |
| `3078272807` | Nutrition Tweaker Enhanced | 503.836 KB | Nov 10, 2023 @ 2:19am | Jul 22, 2025 @ 1:35pm | the B41-era ancestor still carrying the `Build 42` tag — the only one of the six older than this year | W |

### The six rows topped up at 16:56 (`meta.fill`)

The first six `not_requested` rows carrying the `nutrition` term, in dataset
order, re-read half an hour after the sweep by
`--fill --include-not-requested`. Same W grade, same unblock action, same
`meta.fetched`: only the three stat columns and `details_status` moved.

| `workshop_id` | Title | Size | Posted | Updated | Ev |
|---|---|---|---|---|---|
| `3354834585` | Comidas Tipicas Venezolanas [WIP] | 2.653 MB | Oct 25, 2024 @ 10:40pm | Sep 6 @ 8:29pm | W |
| `3388844542` | Minimal Display Bars + Nutritions + Discomfort [B41/B42.20] | 6.523 MB | Dec 21, 2024 @ 11:44am | Sep 6 @ 2:05am | W |
| `3426165280` | Fix NaN Nutrition Stats | 240.428 KB | Feb 12, 2025 @ 10:29am | Feb 13, 2025 @ 2:00am | W |
| `3430945294` | Eliaz Nutritionist Magazine B42 | 609.386 KB | Feb 20, 2025 @ 6:21am | *never* | W |
| `3492090092` | TwisTonFire - Calories & Nutrition | 1.794 MB | Jun 2, 2025 @ 6:18am | Mar 21 @ 11:45pm | W |
| `3653719735` | BloodNutrition | 96.658 KB | Jan 25 @ 7:07am | Jan 25 @ 7:18am | W |

`3796753621` Nutrition Makes Sense Immersive Addon is named in the docs and is
still `not_requested` — **W**, same unblock action, and nothing about it is
claimed here beyond its title and the terms that returned it.

### Why 165 rows have no size, posted or updated — and the three row states

Every row says which of three things happened to it in **`details_status`**,
and it is the only field to read before the three stat columns:

- **`fetched` (15 rows, 2026-09-10 16:56)** — an item page was read. `size` and
  `posted` are real; `updated` is real or genuinely absent (see the field
  table). `error` is `null`.
- **`not_requested` (165 rows, 2026-09-10 16:56)** — no item page was asked for: the row was
  outside `meta.details_ids` and outside the fill pass. `error` is `null`, the
  three stat columns are `null`, and **nothing about the item is claimed**.
  This is a statement about what this repo asked for, never about the mod.
- **`failed` (0 rows, 2026-09-10 16:56)** — an item page was asked for and could not be read.
  `error` says why: a `curl rc=…` transport failure, or Steam's alternate
  item-page template. **No row in the committed file is `failed`.**

`error` is therefore a fetch failure and nothing else. It said something else
in the first encoding of this dataset — 171 rows carried a 107-character
sentence explaining that they had not been asked for, which read in the CSV
(where `grade` and `unblock` do not exist) as "171 of 180 failed". The rows
were re-encoded onto `details_status` on 2026-09-10 without refetching a page;
`meta.notes` records that, and `meta.fetched` is still the sweep's.

**The failure mode `failed` exists for is real, and it answers 200.** A
`filedetails/?id=N` read can come back as the **generic Workshop landing
page** — no `workshopItemTitle`, no `detailsStatRight` — so curl reports
success and a naive parser records an item that ships no stats. The first run
of this tool did exactly that: **177 rows of silent nulls at 15:52, which is
why that output was discarded and never committed.** The tool now requires both
item markers in a body, retries once, and records a miss as `failed`;
`counts.details_incomplete` (**0** here) is the guard that would have caught the
first run.

**How many item pages a session may read is not modelled here, and no figure
should be quoted for it.** What is recorded is four dated observations from
2026-09-10 and no rule fitted to them: **15:45** — 8 browse pages, then 3 item
pages, then the alternate template; **15:58** — the alternate template from the
first request; **16:25** (the committed sweep) — 8 browse pages, then all 9 item
pages it asked for, none throttled; **16:55** — a `--fill` pass 30 minutes
later read 6 more item pages 4 s apart in 24 s, none throttled, for 15 item
pages read in that half hour. Because a read may not land, the details pass
asks only for a **declared subset** (`meta.details_ids`) and a later
`--fill --include-not-requested [--fill-ids <ids|N>]` tops up
`not_requested` rows without re-sweeping — a re-sweep would change the
trend-sorted row set and the `meta.fetched` stamp with it.

At 16:26 the subset was the 3 installed rows plus the 6 nutrition items named
above (7 tokens → 9 ids); at 16:56 the fill added 6 more. **15 of 180
requested, 15 read, 0 failed, 0 rows with a null size and no error.**

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

`meta` carries `build` (`42.20.4 (b0bbce05d5)`), `generated`, **`fetched`** (the
stamp every count needs), `tool`, `terms`, `source_url_pattern` (the browse and
item URL templates, so a row can be re-checked by hand), `details_ids` (which
rows the details pass was allowed to ask for: `"none"`, `"all"`, or the list of
tokens actually passed — **kept as passed, so it is shorter than the count of
ids: the `installed` token expands at run time, and the 7 tokens here became 9
ids**), `corpus` (the inventory path and its 230 records / 179 items as the
join read them), `per_term` (results and error per term), `counts` (the census
above, including `details_incomplete` — **which must stay 0**: a read that
reports no error owes the row a file size, and it read 177 on the first run)
and `notes` (the reader caveats: the trend stamp, the alternate item-page
template and the four dated observations, the three `details_status` states,
the W constraint, and the schema re-encode).

**`meta.fill`** is a list, one entry per `--fill` pass, each
`{at, ids, fetched, failed}`: a fill re-reads rows without re-sweeping, so the
row set, the terms and `meta.fetched` stay as the browse pass left them and the
file still says when each column was read. The committed file has **one** entry
— `at 2026-09-10 16:56`, the six `nutrition` rows in the table above, 6 fetched
/ 0 failed — so 9 of its 15 fetched rows were read at 16:25:31–16:26:22 and 6
at 16:55:37–16:56:01. `counts.details_requested` counts both passes (15), which
is why `details_requested == details_fetched + detail_failures` still holds.

### workshop-catalog-details — the nine catalogued mods (2026-09-10 17:46)

`data/workshop-catalog-details.json`, written by
`python tools/workshop_search.py --catalog-ids <ids>` — the **same item-page
read as `--details`, for ids that are not sweep rows**. Eight of the nine mods
in [`docs/mods-survey/nutrition-mods.md`](../docs/mods-survey/nutrition-mods.md)
§ B42 status are returned by none of the eight search terms, so neither
`--details-ids` (which rejects an id the sweep did not return, on purpose) nor
`--fill` (which has no row to fill) can reach them, and the table's *Workshop
updated* column had nothing to put in it. This file is that column.

**One pass, 2026-09-10 17:46:08–17:46:49: 9 requested, 9 fetched, 0 failed, 0
incomplete**, 4 s apart, one retry per failure mode available and none needed.
Row shape — `workshop_id`, `title`, `size`, `posted`, `updated`,
`details_status`, `error`, **`fetched_at`** — and no `terms`, `installed`,
`mod_ids`, `grade` or `unblock`: no browse page returned these ids and nothing
here is joined to anything. `fetched_at` is per row because there is no browse
pass whose `meta.fetched` would cover them. Every reading is **W**: it is what
a Workshop page said at that minute.

| `workshop_id` | Mod id(s) it holds | Title on the page | Size | Posted | Updated |
|---|---|---|---|---|---|
| `3774789651` | `SKITTLE_LongTermPreservation4220` | Long Term Preservation [42.20] | 239.131 KB | Jul 30 @ 6:31pm | *never* |
| `2867431511` | `simpleStatus` | [B41\|B42] Simple Status | 1.132 MB | Sep 25, 2022 @ 12:57am | Apr 5 @ 5:37pm |
| `3388721641` | `AutoCook` | Auto Cook | 129.161 KB | Dec 21, 2024 @ 8:53am | Sep 6 @ 9:04pm |
| `2503622437` | `SkillRecoveryJournal` | Skill Recovery Journal | 4.460 MB | May 31, 2021 @ 8:28am | Sep 4 @ 8:57am |
| `3396446795` | `MoodleFramework` | Moodle Framework | 180.592 KB | Dec 30, 2024 @ 3:04pm | Sep 7 @ 5:15am |
| `3498347699` | `SomewhatTraits`, `SomewhatTraitsCore`, `SomewhatTraitsSkills` | Somewhat Traits | 1.737 MB | Jun 13, 2025 @ 9:58am | Aug 10 @ 3:03am |
| `3437629766` | `CleanUI` | CleanUI [B42] | 11.300 MB | Mar 3, 2025 @ 1:05am | Sep 7 @ 5:57am |
| `3624538051` | `BaseQuests`, `Economy`, `ItemQuality`, `QualityEnhancements`, `QuestSystem` | Quest System | 3.641 MB | Dec 15, 2025 @ 9:22am | Sep 10 @ 4:53am |
| `3765241705` | `BeyondTen` | Beyond Ten - Level 15 Skills [B41/B42] | 348.184 KB | Jul 15 @ 6:22am | Sep 4 @ 1:25pm |

**`title` and `size` are the item's, not a mod's.** Two of the nine ship
several mods, and the page knows only the item: `3498347699` is titled *Somewhat
Traits* and `3624538051` *Quest System*. **`size` is the sum of the item's mod
folders and matched `bytes` exactly on all nine** — 1 737 473 for the three
Somewhat mods against `1.737 MB`, 3 641 208 for the five Girth ones against
`3.641 MB`, and so on to the byte (Steam divides by 1000 and truncates at three
decimals). That is a genuine cross-check of two independent readings, and it
says the local tree is the size of what the Workshop serves today.

**What it answers, and what it does not.** It answers the one question
`workshop_item_mtime` cannot: when the **author** last uploaded, against a
download stamp that only says when Steam last wrote here. The two disagree in
both directions and neither is wrong — `3774789651` has **never been updated**
since it was posted on Jul 30, yet its item folder was written 2026-09-01;
`3624538051` was updated on the page 2026-09-10 at 4:53am, hours before this
read, while its item folder still reads 2026-08-12. A page date is **W** and
says nothing about what the mod does.

**`3765241705` was read twice by two routes**, once by the sweep's details pass
at 16:26 and once here at 17:46, and both read `348.184 KB` /
`Sep 4 @ 1:25pm`. The catalog quotes it as **C + W** for that reason.
