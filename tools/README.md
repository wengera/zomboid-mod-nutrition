# Tools

Builds on the pz-b42 toolchain (`C:\Users\Angus\pz-b42\tools\` — pzdis.py jar
disassembler + `pz.sh` wrapper, item/vehicle/tile scanners). Don't duplicate;
import patterns from there.

## Planned (P4)

- `food_scan.py` — every item with Food type across vanilla + workshop:
  HungerChange, Calories, Carbohydrates, Lipids, Proteins, ThirstChange,
  Unhappy/Boredom/Stress changes, DaysFresh/DaysTotallyRotten, Cooked/
  DangerousUncooked/Poison, FoodType, EvolvedRecipe roles, tags →
  `data/food-items.{json,csv}`. This dataset drives the full item pass.
- `evolved_recipes.py` — evolvedrecipe graph (base items, ingredients,
  nutrition math) → `data/evolved-recipes.json`.
- `mod_food_diff.py` — which installed mods add/override Food items (compat
  matrix for the item pass).

Conventions: stdlib-only python, same parser style as
`pz-b42/tools/insulation_scan.py` (proven against the generated-script DSL,
including capital-`Scripts` mod dirs and version-folder resolution).
