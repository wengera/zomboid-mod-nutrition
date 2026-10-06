# food-nutrient-map

The hand-curated mapping from every record of `data/food-items.json` (the 2026-09-10 scan, 42.20.4)
to a composition source: one row per dataset id, across six part CSVs. It is the only hand-edited
input of the item-pass pipeline, `tools/food_nutrients.py` (Plan 6). The tool merges the parts in
**filename order** and requires each dataset id **exactly once** across all of them; a row may live
in any part, so a curator moves a row between parts freely. The rows are keyed on the dataset id,
never on the display name (231 rows share a name).

## Files

`fluids.csv`, `grains-legumes.csv`, `manufactured.csv`, `meat-fish-egg-dairy.csv`, `no-nutrition.csv`,
`produce.csv`. Each is UTF-8, LF, `csv.QUOTE_MINIMAL`, the header below on line 1, **no stamp row**
(the dataset rule, `data/README.md`), sorted by `pz_id`.

## Schema

| column | content |
|---|---|
| `pz_id` | the dataset `id` verbatim (`Base.Apple`; a fluid's bare id, `Water`) — the join key |
| `pz_display` | the dataset `display_name`, for review only; the tool never reads it |
| `pz_kind` | `food`, `drainable`, `fluid_container` or `fluid`; must equal the dataset's `kind` |
| `family` | the four-macro tuple `Calories\|Carbohydrates\|Lipids\|Proteins` as the dataset CSV prints each cell; empty when any of the four is absent; written by the seed, a review aid (ruling 3) |
| `fdc_id` | the composition source's id; empty only when `no_nutrition_reason` is set |
| `fdc_source` | `sr_legacy`, `foundation`, `iodine_db_r4`, `literature`, `derived` |
| `fdc_description` | the source's description verbatim, so a wrong mapping is visible in review |
| `confidence` | `exact`, `close`, `proxy`, `guess` (the rubric in the Plan 6 briefing § C) |
| `portion_grams` | the mass the item's numbers describe; never derived from `Weight` |
| `portion_source` | `vanilla_implied`, `fdc_portion:<seq_num>`, `judgement` (ruling 4) |
| `cook_retention_code` | a `Retn_Code` of `NutrientRetention.csv`; only on an `IsCookable` record |
| `state_baseline` | `raw`, `cooked`, `canned`, `dried`, `frozen`, `prepared` — the state as spawned (ruling 5) |
| `iodine_ref` | the row of `data/iodine-db-r4.csv` the food's iodine comes from (ruling 8) |
| `phytate_mg_100g` | phytate, mg per 100 g, from the literature (ruling 9); `0` where the literature places zero, empty where unknown |
| `phytate_source` | the science row the phytate value rests on |
| `no_nutrition_reason` | `not_food`, `empty_container`, `fluid_sourced`, `inedible_body_part`, `hazard`, `vessel_only`, `spice_only`, `tobacco_or_drug` |
| `notes` | free text; required on a `guess` and on a row that leaves its family's `fdc_id` |

## The seed

`python tools/food_nutrients.py --seed-map` writes all six parts once, one row per dataset record
(1 005 items + 61 fluids = 1 066 rows), filling `pz_id`, `pz_display`, `pz_kind`, `family` and a
guessed `no_nutrition_reason`; every other cell is empty. It never overwrites: a part CSV already in
the directory refuses always, and an existing non-empty directory refuses unless `--force` (which
seeds beside non-CSV files such as this page, never over a part).

**The part rule**, first match wins:

1. a `fluid` record → `fluids`;
2. a `drainable` or a `fluid_container` → `no-nutrition`;
3. a `food` record whose `nutrition_basis` is empty, or `Spice = true`, or `CantEat = true` with
   none of the four macros → `no-nutrition` (a `CantEat` food that carries macros — a sealed can —
   stays a food record and goes by rule 4);
4. the remaining foods by `FoodType`:
   - `produce`: `Berry`, `Citrus`, `Fruits`, `Greens`, `Herb`, `HotPepper`, `Mushroom`, `Nut`, `Seed`,
     `Vegetable`, `Vegetables`;
   - `grains-legumes`: `Bean`, `Bread`, `Pasta`, `Rice`, `Thickener`;
   - `meat-fish-egg-dairy`: `Bacon`, `Beef`, `Cheese`, `Egg`, `Fish`, `Game`, `Insect` (animal
     protein), `Meat`, `Milk`, `Poultry`, `Roe`, `Sausage`, `Seafood`, `Venison`;
   - `manufactured`: `Candy`, `CatFood`, `Chocolate`, `Cocoa`, `Coffee`, `DogFood`, `Dressing`, `Juice`,
     `NoExplicit`, `Oil`, `Stock`, `Sugar`, `Tea`, any value not listed, and every food with no
     `FoodType` (641 dataset rows write none). No row is special-cased by its name.

The 43 named `FoodType` values of the dataset are each in exactly one list; a test fails when a
re-scan brings a new one.

**The pre-filled reason**, first match wins (a guess; the curator confirms or clears it):

1. `hazard` — the id contains `Bleach`, `RatPoison` or `CorrectionFluid` (any kind, the fluid `Bleach`
   included);
2. `tobacco_or_drug` — the id contains `Cigarette`, `Tobacco` or `Pills`;
3. `inedible_body_part` — a `food` id with a token `Head`, `Skull`, `Corpse`, `Hide` or `Leather`
   after a `.` or `_` (`Base.Cow_Head_Angus`, `Base.CorpseAnimal`; not `Base.SunflowerHead`);
4. `not_food` — every other `drainable` (the two vinegars included: their `Calories = 0.0` is not
   nutrition);
5. `fluid_sourced` / `empty_container` — a `fluid_container` that lists a fluid / lists none;
6. `spice_only` — `Spice = true`;
7. `vessel_only` — a `food` whose display name contains `Bowl`, `Pot` or `Pan` and which carries
   none of the four macros;
8. else empty.

The seed of 2026-10-06: `produce` 95, `grains-legumes` 23, `meat-fish-egg-dairy` 89, `manufactured`
313, `fluids` 61, `no-nutrition` 485; reasons `not_food` 138, `fluid_sourced` 71, `empty_container`
61, `spice_only` 109, `inedible_body_part` 42, `tobacco_or_drug` 15, `hazard` 4, `vessel_only` 0;
626 rows unfilled; 342 families over the 644 per-item food rows (the empty tuple counted as one).

## The check

`python tools/food_nutrients.py --check-map [--allow-unfilled]` prints every violation and the
counts (`rows`, `parts`, `by_kind`, `by_reason`, `by_confidence`, `filled`, `unfilled`, `families`,
`families_split`, `guesses`, `unmapped`, `orphans`, `duplicates`) and exits 1 on a violation:

- every part's header is the schema;
- every dataset id is in exactly one row (`unmapped`, `duplicates` — the later file named), and
  every row's id is a dataset id (`orphans`);
- `pz_kind` equals the dataset's `kind`;
- every enum cell is empty or in its enum;
- `fdc_id` and `no_nutrition_reason` are never both set, and one of them is set unless
  `--allow-unfilled` (the curation waves run with it; the build refuses an unfilled row);
- a row with an `fdc_id` names its `fdc_source` and `confidence`;
- a `guess` carries `notes` (the guess budget is 40, ruling 10);
- `cook_retention_code` is an integer and only on an `IsCookable` record;
- `portion_grams` is a positive number and `phytate_mg_100g` a number ≥ 0;
- in a family of per-item food rows whose mapped rows name more than one `fdc_id`, every row off the
  family's most common `fdc_id` carries `notes` (`families_split` counts the split families, noted
  or not);
- the `iodine_ref` and `phytate_source` referential checks are Task 5's (`MAP_REF_CHECKS`).

## Curating

- Map a family once and copy its row across the family; leave a family only with `notes`.
- Set the portion with `python tools/food_nutrients.py --implied-portion <pz_id|all> [--fdc <id>]`:
  it prints each macro's implied mass `vanilla / (fdc_per_100g / 100)` and their spread `max/min`;
  at ≥ 2 usable macros and a spread ≤ 1.1 it proposes `vanilla_implied` with the mean mass, else it
  lists the FDC portions as `fdc_portion:<seq_num>` with their modifier strings verbatim; with none
  fitting, the mass is a `judgement` with `notes`. Never `Weight`.
- A `fluid` row is per litre; a container's composition lives on its fluids (`fluid_sourced`).
- An evolved dish's base item is `vessel_only`: its composition is summed from its ingredients.
