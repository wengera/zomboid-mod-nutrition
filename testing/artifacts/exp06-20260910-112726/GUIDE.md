# `exp06-20260910-112726` reading guide

**`exp06-20260910-112726/recipes.json`** — produced by `testing/experiments/s06_recipes.py`,
the slice-06 recipe cross-check, together with the harness commands it drives
(`server/PZTestKit_Server_Recipes.lua`: `recipes.count` / `recipes.evolved` /
`recipes.craft`). Script, commands and artifact landed in one commit (`21fa79d`).

**Skew (slice 06's final fix wave).** Both the driver and the harness command file have since
been edited, and **no measured number in this file moves**. What changed, and why each is
harmless to the readings:

- *Harness*, `collect()` in `PZTestKit_Server_Recipes.lua`: it now takes the owner and the
  method name (so an absent getter answers `itemsError` instead of looking like an empty
  list), and it keeps `items` and `itemFullTypes` index-aligned by writing the placeholder
  `?no-full-type` for an element that answers a label but no full type, reporting
  `itemFullTypesAligned: false` when it does. On 42.20.4 every element of all fifteen probes
  answered both, so a re-run produces the same lists with neither new key present.
- *Driver*, `s06_recipes.py`: (a) `summary.per_recipe.<name>.ok` is now
  `block.matched is True` instead of `not block.mismatches` — a recipe with **no dataset
  record** returns `matched: false` with an *empty* `mismatches` list and was scoring as a
  pass; all ten probes here had a record, so the verdict is identical (10/10 either way).
  (b) `INPUT_SUBLINE_NOTE` and the `EVOLVED` axis strings were corrected (see the errata
  below), so the *text* of `meta.input_subline_note`, the `inputCount` rows' `basis` and
  `evolved.<name>.axis` in this file differ from the script at HEAD. (c) `load_json` /
  `git_say` / `git_dirty` / `doctor` / `num` moved verbatim into `_common.py`. None of (a)–(c)
  reads or writes a game value.

**Errata (this file is immutable; the corrections live here).**

- The `comparison` block, and with it `summary.craft_all_matched` / `fields_mismatched`,
  records two `inputCount` mismatches that the **scanner has since resolved** — `6694568`
  adopted the loader's sub-line model, so `data/recipes.json` now reads `inputCount` 9 and 2.
  The same comparator replayed offline at HEAD against this artifact gives **10 of 10 recipes,
  77 of 77 fields, `mismatches []`**. Those two summary keys are already *do not cite* below;
  this is the number that replaces them.
- `meta.input_subline_note` (and every `inputCount` row's `basis`) puts both sub-line arms in
  one span. They are two: the `-` arm is `CraftRecipe.LoadIO @218–@317 L589–L604`
  (`consumeFromItemScript`), the `+` arm the earlier `@122–@215 L574–L588`
  (`createToItemScript`). Everything else the note says is right, and the corrected text is in
  the script at HEAD.
- `evolved.Salad.axis` and `evolved.SaladClay.axis` assert the plan's **187**. The measurement
  in this same file says **189** and the plan is what is wrong (see the *do not cite* row on
  `salad_matches_plan`). The axis strings are prose the driver carried in; they were corrected
  at HEAD and cannot be corrected here.

The run is clean — `server_errors []`, `client_quit rc=0`, `server_stopped rc=0`, doctor
all-`ok` (recorded in `meta.doctor`), 89.1 s wall, dataset `ab26d41` with
`dataset_dirty false` and the sha256 of the bytes actually read. It makes **no world change**
at all: it reads `ScriptManager` and nothing else — no `settimespeed`, no sandbox write, no
character write, no spawn.

It carries **two readings, and only one of them is a verdict**:

- **`counts` and `comparison`** — the measurement. `recipes.count` answered
  **craft 969 / evolved 63 / legacy 0 / unique 0**, matching the plan's expectations and
  `data/recipes.json`'s own `meta.counts` on all three of the compared rows; ten craft recipes
  were compared field for field against their dataset rows, **77 fields, 75 matched**. Ten of
  those 77 are the **live-vs-live** `outputListSize` row — `getOutputCount()` against the
  length of the list the command itself walked, two reads of one `ArrayList` — so the
  dataset-versus-game count is **67 fields, 65 matched** at run time, and **67 of 67** once the
  scanner adopted the loader's sub-line model (the offline replay above). Quote the 67 when the
  question is "does the dataset describe what the game loaded"; the raw 77 includes a row that
  never touches the dataset.
- **`evolved`** — five `EvolvedRecipe` replies **recorded verbatim and compared against
  nothing**, by controller ruling (`meta.sequencing`): this run happened *before* slice 06
  task 3, so `data/evolved-recipes.json` did not exist. `summary.evolved_observations` is
  labelled as observations for exactly that reason. The evidence is the full `items` /
  `itemFullTypes` lists under `evolved.<name>.reply`; tasks 3 and 5 own the verdict.

**Do not cite from this file:**

| Key | Value in the file | Why not |
|---|---|---|
| `summary.craft_all_matched` and `summary.fields_mismatched` | `false` and `2` | True as defined, and **misleading as evidence about the scanner**. Both mismatches are the same field — `inputCount`, on `MakePizza` (10 vs 9) and `MakeMilkFromPowderBucket` (3 vs 2) — and neither side lost an input. `CraftRecipe.LoadIO @218–@317` attaches a `-` (or `+`) prefixed line inside an `inputs` block to the **preceding** input as `consumeFromItemScript` / `createToItemScript` and adds it to `ioLines`, never to `inputs`, and `getInputCount()` is `inputs.size()` (`@0–@7 L257`). The dataset's `inputs` array is flat and keeps those sub-lines as rows of their own, so it carries *more* than the game's counter. Both rows record `top_level: 9` / `top_level: 2` with `top_level_matches: true` — the dataset's line list with the sub-lines removed equals the game's count exactly. Cite `summary.fields_mismatched_other` (**0**) beside them, or `summary.per_recipe`. |
| `summary.evolved_observations.salad_matches_plan` / `.salad_clay_matches_plan` | `false` (against `plan_expected_187`) | **The plan's 187 is the wrong number, not the measurement.** `getPossibleItems()` answered **189** for both `Salad` and `SaladClay` (identical sets — `Salad`'s and `SaladClay`'s 189 names differ in nothing). Of those 189, **187 are `kind == "food"` and 2 are `kind == "drainable"`** — `Base.Vinegar2` and `Base.Vinegar_Jug`, the two drainables the slice-06 plan itself counts (`374 items carry EvolvedRecipe (372 food, 2 drainable)`) but which its Salad expectation left out. Verified independently offline: a scan of `media/scripts/**/*.txt` for items whose `EvolvedRecipe` key matches `Salad` (case-insensitively, aliases applied) returns exactly the same 189 names, 0 extra and 0 missing. An expansion that reproduces the game must include drainables. |

Two further readings this file evidences, both of which a scanner has to match:

- **`isCookable()` is set by the presence of the `Cookable` key, not by its value.**
  `evolved.AddBaitToChum.reply.isCookable` is **`true`** while
  `media/scripts/generated/recipes/recipes_fishing_evolvedrecipe.txt:9` writes
  `Cookable = false`. `EvolvedRecipe.Load @142–@157 L102–L104` matches the key and stores
  `iconst_1` — the parsed value is never read. `AddBaitToChum` is the only one of the 63 that
  writes `Cookable = false`, so it is the only recipe where the two disagree.
- **`getResultItem()` strips the module.** The reply's `getResultItem` reads `Salad`,
  `SaladClay`, `ConeIcecreamToppings`, `PotOfSoupRecipe`, `Chum` — not the `Base.`-prefixed
  strings the scripts write. `EvolvedRecipe.getResultItem @0–@22 L685–L688` splits the stored
  value on `.` and returns **`split("\.")[1]`, the second element** — not "the last part":
  on a value with two dots it answers the middle segment, and on a bare `Salad` (no dot) the
  split has one element and index 1 does not exist. Every shipped `ResultItem` is
  `Module.Type`, so on 42.20.4 the two readings coincide. `getFullResultItem @0–@4 L692` is
  the raw one, and this command does not read it. Compare against the stripped name, or
  against `getBaseItem`, which **is** full (`Base.Bowl`, `Base.Pot`, `Base.Chum`).
- **`getPossibleItems()` is filled through BOTH `Item.OnScriptsLoaded` arms.** An item's
  `EvolvedRecipe = <Name>:<use>` key is resolved by the exact-name lookup
  `getEvolvedRecipe(key)` (`@43–@59 L3033–L3035`, case-**sensitive**) *and* by a pass over
  every recipe whose `Template` `equalsIgnoreCase` the key (`@122–@140 L3039`,
  case-**insensitive**). `SaladClay` is the proof: **no item writes a `SaladClay` key at all**,
  so its whole 189-item list arrives through the Template arm, and an expansion that models
  only the name arm predicts an empty list for it. `ConeIcecream` is the other half of the
  same reading — `Base.Cinnamon` writes `ConeIceCream:1`, which only the case-insensitive arm
  matches.
