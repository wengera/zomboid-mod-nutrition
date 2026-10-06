# Plan 6 — Item Pass Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the Plan 2 seed table with a pipeline-generated per-type nutrient table covering every record of the food dataset, and ship the `module Base` partial blocks that re-base the four vanilla macros on every mapped food, so that what a player eats carries measured composition rather than vanilla's numbers.

**Architecture:** One tool under `tools/` (`food_nutrients.py`, with `fdc_fetch.py` beside it and no network inside the pipeline) reads a hand-curated mapping (a directory of part CSVs, one row per dataset id), the committed FDC extract (the SR Legacy rows the mapping cites, with their portions and the retention codes), the iodine and phytate side tables and the food dataset, and emits `data/food-nutrients.json` + `.csv`; from that it emits two shipped artefacts into the mod tree: the generated `NR_Data_Nutrients.lua` (the loader API Plan 2 fixed, every vector key in the units contract, items per item and fluids per litre) and the script file `NR_ItemPass_Food.txt` (one partial block per mapped food re-basing `Calories`, `Carbohydrates`, `Proteins`, `Lipids` only). Two live gates settle the block shape (X15) and the checksum kick (X16) before the emitters run; one acceptance boot reads the pass live. A fallback inference and a declared-nutrients modData contract cover foods outside the pass.

**Tech Stack:** Python 3.13 stdlib (the scanners' conventions: `food_scan.py`, `recipe_scan.py`), `pdftotext` (Git's mingw) for the iodine PDF, `lupa` 2.8 for the generated Lua table's tests, the harness (`pzt`, PZTestKit, TKX probes, profiles), the claims and science registers and their delta tools.

**Spec:** `docs/superpowers/specs/2026-09-27-nutrition-mod-design.md` — § 4.6 (default), § 4.2 (the four-source vector the table feeds), § 4.9 (the layout: `common/` holds the data table; mod-unique script basenames; the rival-pass load-order rule; the declared-nutrients contract for food-content mods), § 5 row 6 (gates X15, X16), § 7 items 18, 19, 43, § 8. The research report `docs/superpowers/research/food-data-pipeline.md` is the planning briefing: its `LOCAL`/`EXTRACT` figures are re-measured by the tasks that land them and minted then, never quoted from the report.

## Global Constraints

Everything in Plan 5's Global Constraints holds (`docs/superpowers/plans/2026-10-06-plan-5-effects.md`), and through it Plans 2–4's. Plan 6 adds:

- **The units contract is `NR.data.UNITS`** (`NR_Data_Nutrients.lua`, Plan 2): per item for an item, per litre for a fluid; kcal, g, mg, µg exactly as listed, phytate in **milligrams** (the Plan 2 close lesson), ASCII `ug`; every `K.vector.KEYS` key written on every entry; a generated value in any other unit is a defect the unit test catches.
- **Absence is `null` in the JSON and never `0`** (#0618, the dataset's rule); the Lua emitter writes `0` for a null because the kernel sums numbers, and the JSON keeps the distinction for a reviewer.
- **The mapping is keyed on the dataset id and never on the display name** (231 rows share a name); it is generated from `data/food-items.csv`'s own id list, never from a wish list; a record with neither a mapping nor a closed-enum reason fails the coverage test.
- **Portion mass is never derived from `Weight`** (the report's measurement: 0.06× to 2.83× off); the three-step rule in ruling 4.
- **The four macros only.** The script blocks re-base `Calories`, `Carbohydrates`, `Proteins`, `Lipids`; `HungerChange` and `ThirstChange` are never named (spec § 4.6: hunger is the model's and the hunger key drives recipe cost, the portion menu, the cancel guard and displayed weight); drinks are re-based only in the per-fluid Lua table because `fluid` block merging is unread (#2682).
- **The script file is byte-identical on both sides by construction**: LF endings, deterministic order (sorted by id), no timestamp; the checksum gate hashes content with CRs dropped (#1182) and X16 measures the kick.
- **Every number rests on a row**: the literature values the pipeline uses (Atwater factors, ethanol's 7 kcal/g, the insect compositions, the canning review, the phytate table) are science rows; the dataset counts are `C/snapshot` rows minted in the commit that lands the file; the tool's own judgements (`guess` rows, the burnt and rotten factors already in `K.retention`) are labelled as judgements.
- **Pytest floor 1855**; the close writes the new count into CLAUDE.md § 3.
- **Rulings this plan takes** (each a ledger line and a `Ruling:` row at the close; 2–17 are controller defaults listed for Angus's § 7 re-review):
  1. **One plan for § 5 row 6,** measure-first on the script shape: Task 1 (fetch) → Task 2 (the join core) → Task 3 (the mapping seed) → Tasks 4a–4d (the four curation waves, parallel) → Task 5 (the extract) → Task 6 (the output and its checks) ∥ Task 7 (the gate probes and profiles) → Task 8 (X15 + X16 live) → Task 9 (the emitters) → Task 10 (the fallback and the contract) → Task 11 (the acceptance profile) → Task 12 (the acceptance boot) → Task 13 (docs) → Task 14 (close).
  2. **The mapping is a directory of part CSVs** (`data/food-nutrient-map/<part>.csv`, one schema, merged by the tool in filename order, one row per id across all parts, a duplicate id a hard error) so the curation waves run in parallel on disjoint files; the spec's "curated mapping with a confidence column" is the merged table.
  3. **Map by composition family**: the seed groups the per-item food rows by their four-macro tuple into a `family` column (the tuple's string); a curator maps one row of a family and the tool's `--check-map` reports every family whose rows disagree on `fdc_id` without a `notes` entry; a family is a review aid, never a rule the tool applies.
  4. **The portion rule, in order**: the four vanilla macros' implied mass where their spread is ≤ 1.1× (`portion_source = vanilla_implied`); else an FDC `food_portion.gram_weight` whose modifier string is recorded verbatim (`fdc_portion:<seq_num>`); else a labelled judgement; never `Weight`.
  5. **The baseline state is as spawned** (`raw`, `canned` on the `CannedFood` rows, `dried`, `frozen`, `prepared` on the manufactured foods) and a measured FDC entry in that state is preferred over a factor; `cook_retention_code` is recorded in the JSON on the `IsCookable` rows but **not applied at runtime this plan** — the runtime retention stays Plan 2's class model (`K.retention`, design-phase-v1), re-read against the per-record codes in a later plan; the cost: a class band in place of a per-record cooked loss.
  6. **Every mapped food record is re-based** from `per_item = per_100g × portion_grams / 100`, the vanilla macros kept in the JSON's `vanilla` block for review; the Lua table's four macros equal the block's values, so the vector and the vanilla stores agree on every re-based food.
  7. **All 61 fluids are mapped** (per litre; the container's first-fluid join is the dataset's, not the table's); ethanol grams per litre come from the fluid's `alcohol` property × 789 g/L and the fluid's energy reconciles 7 kcal/g of ethanol with its FDC entry; the nine `PickRandomFluid` and the 14 part-filled containers resolve on the instance, which the intake wrap already reads.
  8. **Iodine** comes from the USDA/FDA/ODS-NIH iodine database Release 4 PDF, extracted with `pdftotext` into `data/iodine-db-r4.csv` (one row per food the mapping cites, with the PDF page), joined by a `iodine_ref` column in the mapping; a food without a row reads `null`.
  9. **Phytate** comes from the literature (Schlemmer et al. 2009's compilation, a science row per family value used) as a `phytate_mg_100g` column with its source in the mapping; zero on foods the literature places at zero (meat, fruit, dairy), `null` where unknown.
  10. **Insects and other FDC gaps** are `guess` rows from the literature (Rumpold & Schlüter 2013), each with `notes`; the guess budget is pinned at 40 and a growth fails the test.
  11. **The script block's shape is the measured one at emit time**: `DisplayCategory`, `ItemType` and the four macros until X15 settles; if X15 reads the `ItemType`-omitted block merging, the emitter drops `DisplayCategory` and `ItemType` and X15's row is the measurement it rests on; the emitter task dispatches after Task 8's row lands.
  12. **The script file lives at `mod/NutritionRevamp/common/media/scripts/NR_ItemPass_Food.txt`** (one file, mod-unique basename, no `template_` prefix, no vanilla relative path, spec § 4.9); `common/` is measured for Lua (#1318) and the X15 boot ships the probe's script under `common/` so the same reading covers scripts.
  13. **The fallback inference**: a food with no table entry takes a vector from its four macros and `FoodType` through per-`FoodType` density templates (micronutrient per kcal medians of the mapped records of that type, emitted by the tool as `NR_Data_Infer.lua`), labelled `inferred` in the intake's `source`; a food with neither macros nor type contributes nothing (as today).
  14. **The declared-nutrients contract**: a food-content mod declares a vector in its item's script as `NR_Nutrients = <key>:<value>;...` (an unrecognised key lands in default modData, #0212 — the measured route), read by the intake wrap before the table and before inference, in the units contract; absent keys 0; the key is documented on `docs/areas/new-nutrients.md`.
  15. **`python tools/food_nutrients.py --check`** is a CLAUDE.md § 3 gate: the generated JSON, CSV, Lua table, inference templates and script file are in sync with the mapping, the extract and the dataset (regenerated with `--write`), as `bus_inventory --check` is for the command table.
  16. **The dataset is the 2026-09-10 scan** (`data/food-items.*`, 42.20.4); the pass reaches a later build's foods only after a re-scan; the acceptance boot's `items.count` must read 722 base foods (no block declares a new item).
  17. **Not this plan:** the panel and tooltip (7), the sync hardening and reconciliation (8), the self-report line and release notes (9), X19 (the sort key), applying per-record retention codes at runtime, FNDDS mixed dishes, caffeine beyond coffee's and tea's fluids (Plan 4 already models the acute state from the vector's `caffeine` key, which the fluid table fills).

## Execution order

Task 0 → Task 1 (Sonnet) → Task 2 (Opus) → Task 3 (Opus) → Tasks 4a ∥ 4b ∥ 4c ∥ 4d (Opus each, Opus reviews) ∥ Task 7 (Sonnet) → Task 5 (Opus) → Task 6 (Opus) → Task 8 (Opus, live; needs Task 7) → Task 9 (Opus; needs Tasks 6 and 8) → Task 10 (Opus) → Task 11 (Sonnet) → Task 12 (Opus, live) → Task 13 (Sonnet; Opus review) → Task 14. Reviews are read-only and run alongside anything; a live boot never overlaps an edit under `mod/`.

## File structure

| path | responsibility | task |
|---|---|---|
| `tools/fdc_fetch.py` | downloads the four source files into a gitignored scratch dir, records sha256 and bytes; never writes `data/` | 1 |
| `tools/food_nutrients.py` | the pipeline: the nutrient-id map, the key table, the mapping loader and checker, the seed, the extract builder, the output and its checks, the three emitters, `--check` | 2, 3, 5, 6, 9, 10 |
| `tools/tests/test_food_nutrients.py` | the test surface (unittest under pytest; fixtures quoted verbatim with their `fdc_id` anchors) | 2–10 |
| `data/food-nutrient-map/*.csv` | the hand-curated mapping parts | 3, 4a–4d |
| `data/iodine-db-r4.csv`, `data/phytate-literature.csv` | the two side tables with page/citation columns | 4b, 4c |
| `data/fdc-extract.json` | the committed FDC subset with `meta.sources` provenance | 5 |
| `data/food-nutrients.json`, `data/food-nutrients.csv` | the output | 6 |
| `mod/NutritionRevamp/common/media/lua/shared/NR_Data_Nutrients.lua` | GENERATED: the per-type and per-fluid tables behind the Plan 2 loader API | 9 |
| `mod/NutritionRevamp/common/media/scripts/NR_ItemPass_Food.txt` | GENERATED: the partial blocks | 9 |
| `mod/NutritionRevamp/common/media/lua/shared/NR_Data_Infer.lua` | GENERATED: the per-FoodType density templates | 10 |
| `mod/NutritionRevamp/common/media/lua/shared/NR_Kernel_Vector.lua`, `server/NR_Server_Intake.lua` | the inference and the declared-nutrients read | 10 |
| `testing/experiments/TKX_PartialBlock/`, `TKX_PartialBlock2/`, `TKX_ChecksumA/`, `TKX_ChecksumB/`, `TKX_ChecksumCR/` | the gate probes | 7 |
| `testing/profiles/x17-partial.toml`, `x17-checksum.toml`, `x17-checksum-cr.toml`, `x17-itempass.toml` | the profiles | 7, 11 |
| `testing/experiments/x171_scripts.py`, `x172_itempass.py` | the drivers | 8, 12 |
| `testing/tests/kernel/test_data_nutrients_shape.py` | the generated table under lupa: every key, units, the loader copies, no NaN | 9 |
| `docs/areas/item-pass.md`, `docs/areas/new-nutrients.md`, `docs/reference/datasets.md`, `docs/reference/tools.md`, `docs/reference/science.md` + `science.tsv`, `docs/facts/other-mods/catalog.md`, CLAUDE.md | the documentation delta | 13 |

---

### Task 0: The workspace — controller

- [ ] `bash "$S/sdd-workspace" docs/superpowers/plans/2026-10-06-plan-6-item-pass.md`; copy the research report into `briefings/`; write `briefings/plan6-key-table.md` (the key→FDC nutrient number table of Task 2, as the controller's draft the task verifies); the first ledger line names the plan, the next free register id (#3133), science id (S1181) and experiment id (X111).

---

### Task 1: `tools/fdc_fetch.py` — Sonnet implementer, Sonnet reviewer

**Files:** create `tools/fdc_fetch.py`, `tools/tests/test_fdc_fetch.py`; modify `tools/README.md` (one entry), `.gitignore` (`tools/.fdc/`).

**Produces:** `python tools/fdc_fetch.py [--dir tools/.fdc]` downloads four files with `urllib` (no key): `https://fdc.nal.usda.gov/fdc-datasets/FoodData_Central_sr_legacy_food_csv_2018-04.zip`, `https://fdc.nal.usda.gov/fdc-datasets/FoodData_Central_foundation_food_csv_2026-04-30.zip` (the report's dated name; if 404, the index page's current Foundation CSV link, recorded), the retention CSV `https://ndownloader.figshare.com/files/44488754` (saved `NutrientRetention.csv`), and `https://www.ars.usda.gov/ARSUserFiles/80400535/DATA/Iodine/IODINE_DATABASE_RELEASE_4_PER_100G.pdf`; writes `tools/.fdc/manifest.json` `{name, url, bytes, sha256, fetched (UTC date)}`; skips a file whose sha256 already matches; `--verify` re-hashes. A function `sources()` returns the list the pipeline's `meta.sources` copies. Tests mock `urlopen` with a tiny byte string and assert the manifest row and the skip; no network in tests.

- [ ] Write the failing tests (the manifest shape; the skip on a matching hash; `sources()` names four entries with `licence`).
- [ ] Implement; run; commit `Tools: fdc_fetch - the four FDC source files into a gitignored scratch dir with a sha256 manifest` -- the three files + README + .gitignore.
- [ ] Run it for real once (`python tools/fdc_fetch.py`) and report the four sha256 values and byte counts in the task report (the controller ledgers them; the SR Legacy zip must be 6 074 592 B).

---

### Task 2: The join core — the nutrient-id map, the key table, the loaders — Opus implementer, Opus reviewer

**Files:** create `tools/food_nutrients.py`, `tools/tests/test_food_nutrients.py`.

**Interfaces (produced):**
- `KEYS`: the 31 vector keys in `K.vector.KEYS` order (copied from `NR_Kernel_Vector.lua` and pinned by a test that reads the Lua file).
- `FDC_NUTRIENT_NBR = {key: [nutrient_nbr, ...]}` — the legacy numbers tried in order: `calories [208]`, `proteins [203]`, `lipids [204]`, `carbs [205]`, `fibre [291]`, `water [255]`, `vitC [401]`, `iron [303]`, `retinol [319]`, `carotene [321]`, `vitD [328]`, `vitE [323]`, `vitK [430]`, `thiamine [404]`, `riboflavin [405]`, `niacin [406]`, `vitB6 [415]`, `folate [435, 417]`, `vitB12 [418]`, `choline [421]`, `sodium [307]`, `potassium [306]`, `calcium [301]`, `magnesium [304]`, `zinc [309]`, `iodine [314]`, `selenium [317]`, `efa [618, 619]` (summed: linoleic 18:2 + linolenic 18:3), `caffeine [262]`, `ethanol [221]`; `phytate` has no FDC number (ruling 9). The task VERIFIES each number against `nutrient.csv` (name and unit) and corrects the table where the draft is wrong, reporting each correction.
- `UNIT_OF = {key: unit}` copied from `NR.data.UNITS` and pinned by a test reading the Lua file; a conversion table from FDC's unit (`KCAL`, `G`, `MG`, `UG`, `IU`) to the contract's; `IU` only on a key whose number is IU (none in the table — a test asserts no IU unit meets a contract key).
- `load_nutrient_map(zip_or_dir) -> {nutrient_nbr: nutrient_id}` from `nutrient.csv`; `load_food_nutrients(zip_or_dir, fdc_ids) -> {fdc_id: {key: amount_per_100g or None}}` joining on `nutrient.id`; `load_portions(zip_or_dir, fdc_ids) -> {fdc_id: [{seq_num, amount, measure_unit, modifier, gram_weight}]}`; `load_foods(zip_or_dir, fdc_ids) -> {fdc_id: {description, data_type, food_category}}`; `load_retention(csv_path) -> {retn_code: {nutrient_nbr: factor}}` that RAISES on a non-integer `Retn_Factor` (the 24 shifted rows on code 5005; a test pins exactly 24 such rows when the real file is present, else skips).
- `atwater(record) -> float` in the fibre-aware form `4·(carb − fibre) + 2·fibre + 4·protein + 9·fat + 7·ethanol`.

- [ ] Tests first: the key list and units pinned from the Lua files; the nutrient map built from a verbatim ten-row `nutrient.csv` fixture (quoted from the zip with `id,name,unit_name,nutrient_nbr` — e.g. `1008,Energy,KCAL,208`); the join returning None for an absent nutrient and never 0; a join on the legacy number alone returning nothing; the retention loader raising on `Sep-75`; `atwater` on a worked row.
- [ ] Implement against the real zip in `tools/.fdc/` when present (`HAVE_FDC` skips otherwise, as `test_food_scan.py` skips without the install); run; commit `Tools: food_nutrients - the FDC join core (nutrient-id map, the 31-key table, the loaders, the fibre-aware Atwater)`.
- [ ] Report: every key's resolved `nutrient.id`, name and unit; the SR Legacy coverage count per key (foods carrying a value); any draft number corrected.

---

### Task 3: The mapping seed and checker — Opus implementer, Opus reviewer

**Files:** modify `tools/food_nutrients.py`; create `data/food-nutrient-map/README.md` and the seeded parts; tests.

**Interfaces (produced):**
- The mapping schema (every part file): `pz_id, pz_display, pz_kind, family, fdc_id, fdc_source, fdc_description, confidence, portion_grams, portion_source, cook_retention_code, state_baseline, iodine_ref, phytate_mg_100g, phytate_source, no_nutrition_reason, notes` — the report's columns plus `family`, `iodine_ref`, `phytate_mg_100g`, `phytate_source`. Enums: `fdc_source ∈ {sr_legacy, foundation, iodine_db_r4, literature, derived}`; `confidence ∈ {exact, close, proxy, guess}`; `portion_source ∈ {vanilla_implied, fdc_portion:<seq>, judgement}`; `state_baseline ∈ {raw, cooked, canned, dried, frozen, prepared}`; `no_nutrition_reason ∈ {not_food, empty_container, fluid_sourced, inedible_body_part, hazard, vessel_only, spice_only, tobacco_or_drug}`.
- `python tools/food_nutrients.py --seed-map`: from `data/food-items.json`, one row per record (1 005 items + 61 fluids) into parts by the dataset's own columns: `produce.csv` (FoodType in Fruits/Vegetables/Greens/Mushroom/Herb… — the task reads the 44 values and groups), `grains-legumes.csv`, `meat-fish-egg-dairy.csv`, `manufactured.csv` (packaged, sweets, prepared, the rest), `fluids.csv` (the 61 fluid records), `no-nutrition.csv` (the 290 zero-nutrition rows, the 111 spices and the 96 `CantEat` rows, pre-filled with a `no_nutrition_reason` guess the curator confirms); `family` = the four-macro tuple string; never overwrites an existing part (`--seed-map --force` only onto an empty directory).
- `python tools/food_nutrients.py --check-map`: every dataset id present exactly once across the parts; no orphan; `pz_kind` matches the dataset; enums closed; `fdc_id` present ⇔ `no_nutrition_reason` empty; `guess` ⇒ `notes`; `cook_retention_code` only on `IsCookable` rows; a family whose rows disagree on `fdc_id` without `notes`; counts printed (`by_confidence`, `by_reason`, `guesses`, `unmapped`).

- [ ] Tests: the seed on a five-record synthetic dataset; `--check-map` on each violation; the part merge order and the duplicate error.
- [ ] Run the seed for real; commit `Data: the food-nutrient mapping seeded from the 2026-09-10 dataset (six parts, 1 066 rows, reasons pre-filled)`.
- [ ] Report: the part sizes; the pre-filled reason counts; the 342-family count re-measured.

---

### Task 4a–4d: The curation waves — Opus implementers (parallel, disjoint parts), Opus reviewers

Each wave edits ONLY its part file(s) and its side table; the tool's `--check-map` runs clean on the merged set at the end of each wave (another wave's unfilled rows are allowed while `--check-map --allow-unfilled` is passed; the final check after 4d passes without it).

- **4a `produce.csv` + `grains-legumes.csv`** (≈ 300 rows): SR Legacy ids by family; `state_baseline` (dried on the dried rows; canned on the canned vegetable rows); `portion_grams` by ruling 4 (the implied mass computed by `--implied-portion <pz_id>`, a helper Task 3 adds, printing the four implied masses and their spread); `cook_retention_code` on the cookable rows from the vegetable/grain groups (`WATER USED` for a pot ingredient, `DRAINED` otherwise — the method named in `notes`); `phytate_mg_100g` on the grain and legume rows from `data/phytate-literature.csv`.
- **4b `meat-fish-egg-dairy.csv`** (≈ 200 rows) + `data/iodine-db-r4.csv`: the meats (`proxy` for game meats as the report resolves: venison 173855, rabbit 174347, frog 168148), fish, eggs, dairy; `raw` baselines; the iodine side table built with `pdftotext tools/.fdc/IODINE_DATABASE_RELEASE_4_PER_100G.pdf -layout` for the dairy, egg, fish, seaweed and bread rows the mapping cites (`food, iodine_ug_100g, page`), each row's PDF page recorded; `iodine_ref` set on those rows.
- **4c `manufactured.csv`** (≈ 250 rows) + `data/phytate-literature.csv`: packaged, sweets, breads, snacks, prepared foods, the insect rows (`guess`, Rumpold & Schlüter 2013, `notes`), the `prepared` baselines; the phytate table (family, mg/100 g, Schlemmer 2009 table reference) that 4a also reads — 4c writes it FIRST (its first commit) so 4a can read it: the controller dispatches 4c's side-table commit before 4a.
- **4d `fluids.csv` + `no-nutrition.csv`**: all 61 fluids (per litre: SR Legacy's beverage entries; `ethanol` from the `alcohol` property × 789; the energy reconciliation noted per alcoholic fluid; coffee's and tea's caffeine from 262), and every reason row confirmed or corrected (`hazard` on Bleach; `vessel_only` on the Bowl/Pot/Pan vessels; `fluid_sourced` on the 72 containers; `not_food` on the drainables).

Each wave: tests none (data); gates `--check-map --allow-unfilled` clean on its part; commit `Data: mapping wave <x> - <part> (<n> rows; <k> exact, <m> close, <p> proxy, <q> guess)`; the report lists every `guess` and every `proxy` with its reason, and the ten hardest rows. Each reviewer samples 30 rows against the FDC zip (`food.csv` description for the `fdc_id`; the portion against the implied mass) and fails a wave on one wrong id.

---

### Task 5: The extract — Opus implementer, Opus reviewer

**Files:** modify `tools/food_nutrients.py`; create `data/fdc-extract.json`.

**Produces:** `python tools/food_nutrients.py --build-extract` reads the merged mapping and the zips, writes `data/fdc-extract.json` `{"meta": {build, jar_hash, generated (UTC date), tool, sources (from fdc_fetch.sources() + the manifest's sha256/bytes), counts}, "foods": {fdc_id: {description, data_type, food_category, nutrients: {key: {amount, unit, nutrient_id}}, portions: [...]}}, "retention": {code: {description, factors: {nutrient_nbr: pct}}}, "iodine": {...}, "phytate": {...}}` — only the cited ids and codes; `indent=1`, LF, sorted keys, byte-stable within one UTC day; `meta.counts` publishes `foods`, `retention_codes`, `missing_nutrients` (per key the cited ids without a value).

- [ ] Tests: the extract on a synthetic two-food zip (a `zipfile` built in a temp dir); byte stability; the `null` rule.
- [ ] Build for real; commit `Data: fdc-extract - the <n> SR Legacy foods and <k> retention codes the mapping cites, with provenance`; report the size and the `missing_nutrients` counts.

---

### Task 6: The output and its checks — Opus implementer, Opus reviewer

**Files:** modify `tools/food_nutrients.py`; create `data/food-nutrients.json`, `data/food-nutrients.csv`; modify `data/README.md`.

**Produces:** `python tools/food_nutrients.py --build` reads the dataset, the mapping, the extract (never the zips) and writes the output: one record per id (the report's record: `pz_id, kind, basis, portion_grams, portion_source, fdc_id, fdc_source, confidence, state_baseline, cook_retention_code, per_100g {31 keys}, per_item or per_litre {31 keys}, vanilla {calories, carbohydrates, lipids, proteins, hunger, thirst}, checks {atwater_ratio, energy_vs_fdc_ratio, out_of_range [], proximate_sum, notes}`), fluids per litre; `meta.counts` (`items, mapped, no_nutrition, by_confidence, by_state_baseline, by_reason, fluids, cook_retention_set, atwater_outliers, portion_source_counts, guesses`), `meta.unmapped == []`, `meta.orphan_mappings == []`; the checks: Atwater within ±10 % (±25 % where fibre is null) against FDC's energy, the per-nutrient sanity ranges (the report's table, as constants with their hardest-case comment), the proximate sum ≤ 102 g, fibre ≤ carbohydrate, retention ≤ 100 on every cited code; violations NAMED in `checks.out_of_range`, never clamped; the CSV twin with no stamp row.

- [ ] Tests: the schema; the units round trip `per_item = per_100g × portion / 100` to 1e-6; the basis never mixed; coverage; the guess budget ≤ 40; byte stability; the checks on synthetic violations.
- [ ] Build; commit `Data: food-nutrients - <n> items and 61 fluids from the mapping and the extract, with the Atwater, range and proximate checks`; report every `out_of_range` violation (a real one is a mapping defect → a fix round on the wave that owns the row).

---

### Task 7: The gate probes and profiles — Sonnet implementer, Sonnet reviewer

**Files:** create `testing/experiments/TKX_PartialBlock/` (`42.20/mod.info`, `common/media/scripts/tkx_partial_block.txt`: `module Base { item Orange { DisplayCategory = Food, Calories = 400.0, NR_Nutrients = fibre:12;vitC:3, } }` — `ItemType` OMITTED; the script under `common/` on purpose, ruling 12), `TKX_PartialBlock2/` (`item Orange { DisplayCategory = Food, ItemType = base:food, NR_Nutrients = fibre:13;vitC:4, }` — a second mod's block on an already-populated default modData; basename `tkx_partial_block2.txt` sorting after), `TKX_ChecksumA/` and `TKX_ChecksumB/` (identical `42.20/media/scripts/tkx_checksum.txt` declaring one `module TKX item ChecksumProbe` but for ONE byte that is not a CR: `Weight = 0.2` vs `Weight = 0.3`), `TKX_ChecksumCR/` (A's file with CRLF endings — the control); profiles `x17-partial.toml` (PZTestKit + TKX_PartialBlock + TKX_PartialBlock2; verify rows on `items.count` and `lua.global TK.version`), `x17-checksum.toml` (TKX_ChecksumA server-side, the driver passes B to the client through `session.make_client(mod_sources=…)`; `[client] timeout = 60`; `pzt run` EXPECTED to fail), `x17-checksum-cr.toml` (A server, CR client; expected to connect).

- [ ] `python tools/mod_lint.py` on each probe 0 ERROR; `kahlua_lint` 0; `python -m pytest testing/tests -q` (the profile tests) green; one commit per probe pair and one for the profiles; never boots.

---

### Task 8: X15 and X16 live — Opus implementer (live), Opus reviewer

Two sessions. **X15** (`x17-partial`, one boot): server `items.count` (`foodByModule.Base` 722 — the partial block declared nothing new); `item.script Base.Orange` both sides; client `item.spawn Base.Orange` then `witness.fields item <id> getCalories,getCarbohydrates,getLipids,getProteins,getHungChange` both sides (400 / vanilla / vanilla / vanilla / −0.12 if the `ItemType`-omitted block merged; the Food instantiation question answered by the getters resolving at all); `witness.moddata item:<id> NR_Nutrients` both sides (the second mod's `fibre:13;vitC:4` wins if a second partial block lands on populated default modData, else the first's); the X15 row either way. **X16** (`x17-checksum` then `x17-checksum-cr`, two boots): the boot is the action; readings from the server log (`Timed out connection because checksum was different`, the `AntiCheat` line, the userlog row) and the client stdout (`kickReason`, `serverDisconnected`) against `ChecksumPacket.getReason`'s strings; the CR arm must connect (`lua.global TK.version` on the client). Artifacts under `testing/artifacts/x171-<id>/`; the delta (X15 → #1018/#1281 settled or bounded; X16 → #1282; new rows provisional `T8.n`; X ids from X111 for any new question); the pages (`docs/platform/loader-and-scripts.md`, `docs/platform/mod-anatomy.md#checksum-gate`, `docs/areas/item-pass.md`, `experiments.md`, `open-questions.md`); the live-row rules (every number at its raw path; a falsified prediction stated).

- [ ] Commits `Run x171p: X15 - the ItemType-omitted partial block and a second mod's block (driver, artifact, register row, do-not-cite)` and `Run x171c: X16 - the one-byte checksum kick and the CR control (driver, artifacts, register row)`.

---

### Task 9: The emitters — the Lua table and the script file — Opus implementer, Opus reviewer

**Files:** modify `tools/food_nutrients.py`; REGENERATE `mod/NutritionRevamp/common/media/lua/shared/NR_Data_Nutrients.lua`; create `mod/NutritionRevamp/common/media/scripts/NR_ItemPass_Food.txt`, `testing/tests/kernel/test_data_nutrients_shape.py`.

**Produces:** `--emit-lua`: the file keeps Plan 2's header role, `NR.data.UNITS` byte-identical, the loader API `NR.data.nutrients.get(fullType)` / `NR.data.fluids.get(fluid)` returning copies, and replaces the seed tables with GENERATED tables (`-- GENERATED by tools/food_nutrients.py from data/food-nutrients.json (<UTC date>); do not edit` + the provenance line naming the extract's sources); one line per entry, every `K.vector.KEYS` key, `0` for null, numbers printed with `repr`-stable formatting (`%.6g` is NOT stable — use Python's shortest round-trip `repr` and a test that re-reads the Lua under lupa and compares to the JSON to 1e-9); items per item (the macros = `per_item`), fluids per litre; a `-- SOURCE <pz_id> <fdc_id> <confidence>` comment per entry. `--emit-scripts`: `NR_ItemPass_Food.txt` with `module Base { ... }` and one block per mapped FOOD record (kind `food`, `fdc_id` set) in the shape ruling 11 and Task 8's row fix (`DisplayCategory = <the dataset's value>`, `ItemType = base:food` unless X15 read them droppable), `Calories`, `Carbohydrates`, `Proteins`, `Lipids` from `per_item` printed as the script's float form (`%.2f` — the dataset's own precision; a test pins the format), sorted by id, LF, four-space indent as vanilla's files; a `//` header comment (mods use `//`; the parser strips it — verify `_strip_comments` handles it and that the engine's loader does: `ScriptManager` strips `//` per the Plan 2 reading in `food_scan.py`'s docstring); NEVER `HungerChange`/`ThirstChange`; no drainable, container or fluid block. `--check` compares every generated file to a fresh emission.

- [ ] Tests: the lupa shape test (every entry has every key, every value a finite number, the loader returns a copy, `UNITS` unchanged, the Apple entry equals the JSON's); the script emitter on a three-record synthetic output (the exact text); `--check` detects a hand edit.
- [ ] Emit; `python tools/mod_lint.py mod/NutritionRevamp` 0 ERROR; `kahlua_lint` 0; `python tools/food_scan.py`-style parse of the emitted file through `food_scan.parse_script` (a test: every block parses, every key known to `food_scan.COLUMNS`); the full suite green; commit `Mod: the generated nutrient table (<n> items, 61 fluids) and the item-pass script file (<m> partial blocks re-basing the four macros)`.

---

### Task 10: The fallback inference and the declared-nutrients contract — Opus implementer, Opus reviewer

**Files:** modify `tools/food_nutrients.py` (`--emit-infer`), create `mod/NutritionRevamp/common/media/lua/shared/NR_Data_Infer.lua` (GENERATED), modify `NR_Kernel_Vector.lua` (`K.vector.infer(macros, foodType, templates)`, `K.vector.declared(str)`), `NR_Server_Intake.lua` (the lookup chain: declared → table → inferred → missing; `source` names which), tests.

**Produces:** `NR_Data_Infer.lua`: per `FoodType` (the 44 values + `_default`), the median per-kcal density of every micronutrient key over the mapped records of that type (water and fibre per gram of carbohydrate; `_default` over all mapped foods); `K.vector.infer` multiplies by the item's calories (fibre by carbs) and returns the vector with the four macros as read; `K.vector.declared` parses `fibre:12;vitC:3` (the units contract; unknown keys ignored and reported; a malformed value → nil whole); the intake wrap reads the item's default modData key `NR_Nutrients` (through `getModData()` — the measured route for an unrecognised script key, #0212, confirmed live by Task 8's X15 reading) before the table; `source` gains `declared` and `inferred`; a limitation string names the inference as a judgement from the pass's own medians.

- [ ] Tests first (kernel: infer on a synthetic template; declared parsing incl. malformed; the chain order in the intake shape test); the emitter test; coverage 100 % on the kernel file; `hotpath_lint` 0 (slow path only); commit `Mod: the fallback inference from FoodType density templates and the NR_Nutrients declared-vector contract`.

---

### Task 11: The acceptance profile — Sonnet implementer, Sonnet reviewer

**Files:** `testing/profiles/x17-itempass.toml` (PZTestKit + NutritionRevamp Mode 1 + TKX_ItemOverride — its `module TKX` `FibreBar` is the unmapped modded food — + a new `TKX_DeclaredFood` whose `module TKX item DeclaredBar` carries `NR_Nutrients = fibre:9;vitC:40;iron:2`; `Nutrition = false`; DayLength 1; the NR dials default; `[server]` sleep false/false — no sleep arm), verify rows (`items.count` food 722 server-side; `item.script Base.Apple` both sides). Header: what the boot reads. One commit; never boots.

---

### Task 12: The acceptance boot — Opus implementer (live), Opus reviewer

Profile `x17-itempass`, one boot. **Arms:** (A) the load: no script error in either log; `items.count` `foodByModule.Base` 722 and `total` unchanged against the fixture baseline (+ the two TKX items); boot time and `tick.rate` against x161b's 10.10/s (the generated table's load cost; the file size on disk stated); (B) ten re-based foods sampled across confidence levels: client `item.spawn` + `witness.fields item … getCalories,getCarbohydrates,getLipids,getProteins,getHungChange,getThirstChange` both sides equal the script file's values and hunger/thirst equal vanilla's (the dataset); (C) a re-based apple eaten (the x132e eat shape: server `inventory.add` + the client eat) lands the TABLE's vector in `record.nutrients`' ingested (the mod's own intake reading: `vitC` 8.4 → the FDC per-item value; the macros equal the block's); (D) `TKX.FibreBar` eaten → `source = inferred`, the vector = the `_default`/its-type template × its calories (recomputed offline from `NR_Data_Infer.lua`); (E) `TKX.DeclaredBar` eaten → `source = declared`, fibre 9, vitC 40, iron 2 at the raw path; (F) a fluid drunk (the x151s coffee shape) → the fluid table's per-litre vector × litres (caffeine lands on `acute.caf`); (G) `witness.moddata item:<apple id> NR_Nutrients` reads nothing on a vanilla food (the pass declares no mod key); (H) the checksum: both sides connected all session (the normal arm of X16). Artifact `x172-<id>/itempass.json`; the rows (the mod-on-itself rows on testing-your-mod#scenario-inputs; a game fact on its facts page; X ids from the next free); the live-row rules.

- [ ] Commit `Run x172: the item pass live - 722 foods held, ten re-based foods on both sides, the table, inferred and declared vectors landing, the fluid table, cost (driver, artifact, register row, do-not-cite)`.

---

### Task 13: The documentation delta — Sonnet implementer, Opus reviewer

Rule rows on `docs/areas/item-pass.md#rules` (the pass's contract as rules resting on this plan's rows: the block shape as measured by X15; the four macros only with the vector equal to the block; absence as null; the portion rule; per-litre fluids in the table only; the declared-nutrients contract; the inference as a labelled fallback; the generated files never hand-edited); `docs/areas/new-nutrients.md` (the `NR_Nutrients` contract section: the key, the units, the precedence); `docs/reference/datasets.md` (the three new datasets with their counts as `C/snapshot` rows, columns, the `meta` blocks, the mapping schema and enums; the re-measured 342 families, 290 reasons, the guess count); `docs/reference/tools.md` (`food_nutrients.py`, `fdc_fetch.py` entries with every flag); `docs/reference/science.md` + the part file (the Atwater factors 4/4/9 with fibre 2 and ethanol 7, Rumpold & Schlüter 2013's insect values used, Rickman 2007, the USDA R6 factors used — settled rows with citations resolved; Schlemmer 2009's phytate values); `docs/facts/other-mods/catalog.md` (the rival-pass load-order rule tagged with the X15 second-mod row); `docs/platform/mod-anatomy.md` (the checksum gate's measured arm from X16); CLAUDE.md § 3 (`food_nutrients.py --check` gate; `<COUNT>`), § 2 (the dataset's scan date beside the build); the skills `nutrition-item-pass` and `nutrition-new-nutrients` re-synced; `mod.info`'s description (the Plan 6 build). Gates as Plan 5's Task 15.

---

### Task 14: The close — Opus whole-pass review, fix wave, gates, memory, push

As Plan 5's Task 16: the whole-pass checklist (every generated file in sync under `--check`; every mapping `guess`/`proxy` with a note; the sampled rows against the extract; the units contract; the script file's shape against X15's row and byte-identity; the inference templates' medians re-derivable; every live row re-read against its artifact; every § 3 gate; the type-list drift) → one consolidated fix wave (mapping/tool half Opus; docs half Sonnet) → re-review → `--write` and a third boot only if a generated file changed → § 3 → CLAUDE.md § 3 → memory (PLAN 6 block before PLAN 5's) → push → the Rulings block and the § 7 list → `Plan 6: complete`.

---

## Self-Review

**Spec coverage (§ 4.6):** the tool under `tools/` in the scanners' conventions → Tasks 1–3, 5–6, 9; the curated mapping with a confidence column → Tasks 3–4; the SR Legacy extract subset with provenance → Task 5; the nutrient-id join on FDC's internal ids → Task 2; iodine from the iodine database → ruling 8, Task 4b; cooked and raw states from measured SR entries where they exist and retention factors otherwise → ruling 5, Tasks 4a–4c (recorded; the runtime stays Plan 2's model — stated); the Atwater cross-check with per-nutrient sanity ranges → Task 6; `data/food-nutrients.json` → Task 6; the Lua data table → Task 9; the `module Base` partial blocks re-basing the four macros → Task 9; hunger and thirst untouched → the Global Constraint; drinks only in the per-fluid table → ruling 7; records without a mapping carry a reason and the coverage test → Tasks 3, 6; by composition family → ruling 3. § 5 row 6's gates X15, X16 → Tasks 7–8. § 4.9's declared-nutrients contract and the inferred vector → ruling 13–14, Task 10; the rival-pass load-order rule → Task 13. ✓

**Placeholder scan:** every task names its files, flags, schema and tests; the key table's numbers are the controller's draft and Task 2 verifies each against `nutrient.csv` (stated as such, not a placeholder). ✓

**Type consistency:** `K.vector.KEYS` (31) and `NR.data.UNITS` are the contract throughout; `NR.data.nutrients.get` / `NR.data.fluids.get` unchanged; the mapping schema of Task 3 is what Tasks 4–6 read; `per_item` / `per_litre` / `per_100g` blocks named identically in Tasks 5, 6, 9; `source` values `declared`/`inferred` in Tasks 10 and 12. ✓

**Boundary risks:** the curation is the cost centre (~1 066 rows, four Opus waves) and a wrong `fdc_id` passes every automated check — the wave reviews sample 30 rows each against the zip; the generated Lua table is ~1 000 entries × 31 keys (≈ 300 KB) loaded once per side — the acceptance measures boot time and tick rate; the script file re-bases 600+ foods at once and a malformed value aborts the load (#1188) — the emitter's parse-back test and the acceptance's first arm catch it; X16 is a raising experiment whose boot is the action; the inference templates rest on the pass's own medians and are labelled a judgement.
