# Data

Generated datasets (do not hand-edit): food-items, evolved-recipes, mod
overlays. Regenerate with tools/ scanners; each file carries the game build
it was generated from.

## food-items

`data/food-items.json` + `data/food-items.csv`, written by
`python tools/food_scan.py` from the 42.20.4 scripts under
`media/scripts/generated/`. Evidence grade **C** throughout: every value is a
line in a shipped script file, and every record names the file and line it
came from. Nothing is measured, inferred or defaulted here — the live checks
are `testing/`, and a key a script does not write has no value in this
dataset.

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

49 columns: the 47 below plus the trailing `source_file`, `source_line`.
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
| 10 | `nutrition_source` | string | derived: `food_keys`, or `fluid:<id>` when the row's nutrition was joined from a fluid |
| 11 | `calories` | float | `Calories` |
| 12 | `carbohydrates` | float | `Carbohydrates` |
| 13 | `lipids` | float | `Lipids` |
| 14 | `proteins` | float | `Proteins` |
| 15 | `hunger_change` | float | `HungerChange` |
| 16 | `thirst_change` | float | `ThirstChange` |
| 17 | `days_fresh` | int | `DaysFresh` |
| 18 | `days_totally_rotten` | int | `DaysTotallyRotten` |
| 19 | `cant_be_frozen` | bool | `CantBeFrozen` |
| 20 | `is_cookable` | bool | `IsCookable` |
| 21 | `minutes_to_cook` | int | `MinutesToCook` |
| 22 | `minutes_to_burn` | int | `MinutesToBurn` |
| 23 | `dangerous_uncooked` | bool | `DangerousUncooked` |
| 24 | `packaged` | bool | `Packaged` |
| 25 | `canned_food` | bool | `CannedFood` |
| 26 | `cant_eat` | bool | `CantEat` |
| 27 | `spice` | bool | `Spice` |
| 28 | `good_hot` | bool | `GoodHot` |
| 29 | `bad_cold` | bool | `BadCold` |
| 30 | `unhappy_change` | int | `UnhappyChange` |
| 31 | `boredom_change` | int | `BoredomChange` |
| 32 | `stress_change` | int | `StressChange` |
| 33 | `fatigue_change` | float | `fatigueChange` |
| 34 | `endurance_change` | float | `enduranceChange` |
| 35 | `food_sickness_change` | int | `FoodSicknessChange` (the fluid files spell it `foodSicknessChange`; both land here) |
| 36 | `poison_power` | int | `PoisonPower` |
| 37 | `alcohol_power` | float | `AlcoholPower` — the item key, never the fluid's `alcohol` |
| 38 | `evolved_recipe` | list `;` | `EvolvedRecipe` (`Cake:16` parts, `\|Cooked` suffix intact) |
| 39 | `evolved_recipe_name` | string | `EvolvedRecipeName` |
| 40 | `replace_on_cooked` | list `;` | `ReplaceOnCooked` (list-typed in the key table, so a single target is a one-item list) |
| 41 | `replace_on_rotten` | string | `ReplaceOnRotten` |
| 42 | `replace_on_use` | string | `ReplaceOnUse` |
| 43 | `on_cooked` | string | `OnCooked` |
| 44 | `on_eat` | string | `OnEat` |
| 45 | `fluid_capacity` | float | `component FluidContainer`'s `Capacity`, in litres |
| 46 | `fluid_ids` | list `;` | each `Fluids.fluid` value's first `:` field, in file order — a pick-random container repeats one id (`HairDyeCommon` lists `HairDye` 8 times). In the JSON, `[]` is a container that lists no fluid (an empty jar, 59 of them) and `null` is a row that is not a container |
| 47 | `weight` | float | `Weight` |
| 48 | `source_file` | string | path under `media/scripts/generated/`, e.g. `items/food.txt` |
| 49 | `source_line` | int | 1-based line of the block's header |

Types follow the loader (`Item.DoParam`), via `food_scan.KEY_TYPES`: only the
literal `true` is true, and an int-typed key holding an integral float literal
comes back as an int (`UnhappyChange = -10.0` → `-10`).

**The fluid join.** A `fluid_container` row takes the **first** fluid its
`Fluids` block lists: `nutrition_source` becomes `fluid:<id>`, and columns
11–16 and 30–37 come from that fluid's `Properties` block instead of the
item's own keys. In 42.20.4 no fluid-container item writes a nutrition key of
its own, so nothing is overwritten; 10 of the 61 fluids have no `Properties`
block at all, so `fluid:HairDye` with empty nutrition is a correct row, not a
gap. `alcohol`, `fluReduction` and `painReduction` have no column and stay in
the fluid record's `properties_raw`.

### JSON

`{"meta": {...}, "items": [...], "fluids": [...]}`, `indent=1`, items and
fluids sorted by `id`. An item record carries every column above (absent =
`null`) plus `props_raw`: the item block's own `Key = Value` lines verbatim,
untyped and unsplit, keys sorted, a key written twice becoming a list (the 7
repeated `SoundMap` lines survive there). Nested blocks are not flattened into
it — a container's `Capacity` reaches the record only as `fluid_capacity`.

A fluid record carries `id`, `module`, `name`, `kind`, `display_name`,
`display_name_key`, `color_reference`, `categories`, the 14 nutrition columns
above, `properties_raw` (the `Properties` block verbatim), `poison` (the
`Poison` block, or `null`), `props_raw`, `source_file` and `source_line`.

`meta` keys:

| Key | Meaning |
|---|---|
| `build` | game build the scripts were read from (`42.20.4`) |
| `jar_hash` | the disassembled jar this build's key table was checked against (`b0bbce05d5`) |
| `generated` | UTC date of the run |
| `tool` | `tools/food_scan.py` |
| `sources` | the 18 script paths read, relative to `media/scripts/generated/` |
| `counts` | `food`, `drainable`, `fluid_container`, `fluids`, `unresolved_links` |
| `unknown_keys` | every script key the dataset carries that the item key table does not cover, so it is kept as a raw string — weapon and clothing keys ride along on fluid-container items, and `DisplayName`, `ColorReference`, `alcohol` and the `Poison` block are the fluid files' own |
| `unresolved_links` | `{item, key, target}` for every `ReplaceOnCooked` / `ReplaceOnRotten` / `ReplaceOnUse` / `ReplaceOnDeplete` target that is not a record of this dataset — mostly pans and empty containers, plus `Base.HotDrinkRed` → `Base.MugRed`, which 42.20.4 names but never defines |
| `missing_display_names` | ids with no EN name; a fluid appears as `fluid:<id>` |
| `unresolved_fluid_refs` | `{item, fluid_id}` for a `Fluids.fluid` naming a fluid no file defines (empty in 42.20.4) |

`ReplaceOnDeplete` has no column of its own — it is read for
`unresolved_links` and kept verbatim in `props_raw`.
