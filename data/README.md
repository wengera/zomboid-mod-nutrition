# Data

Generated datasets (do not hand-edit): food-items, evolved-recipes, mod
overlays. Regenerate with tools/ scanners. The **JSON** of a pair carries the
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
