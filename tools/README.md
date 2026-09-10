# Tools

Builds on the pz-b42 toolchain (`C:\Users\Angus\pz-b42\tools\` — pzdis.py jar
disassembler + `pz.sh` wrapper, item/vehicle/tile scanners). Don't duplicate;
import patterns from there.

## Intake pipeline

- `wiki_mirror.py` — `python tools/wiki_mirror.py <Page> ["Another page" ...]`
  Fetches each PZwiki page as raw wikitext (curl with a browser UA — plain
  fetchers get 403) and writes `references/wiki-mirrors/<slug>.md`: provenance
  header (`**Source:**`, `**Fetched:**`, `**Wiki page version:**` from
  `{{Page version|X}}` or `unstamped`, `**License:**` CC BY-NC-SA 3.0), a
  `## Digest` stub reading `_digest pending_`, then `## Wikitext` with the raw
  text in a fence. Method rule 3 in STRATEGY.md: mirror, then digest by hand —
  the placeholder lint keeps an un-digested mirror visible until you do.
- `doc_lint.py` — `python tools/doc_lint.py [target ...] [--root DIR]`
  Targets are files or directories (directories are walked); the default is
  the whole repo. Prints `path:line: rule: detail` per finding, then a count;
  exits 1 if any. Rules: `stamp` (docs under `docs/vanilla`, `docs/modding`,
  `docs/feasibility`, `docs/mods-survey/teardowns` carry
  `Verified against: 42.20.4`), `placeholder` (`TODO`/`TBD`/
  `_digest pending_`), `sources` (in those same docs, a `## Sources` heading
  with at least one non-blank line before the next `## ` heading), `grades`
  (every body row of a table with an `Ev` column has a C/M/W evidence grade),
  `mirror-header` (the four header keys above, on every mirror). Skips
  `docs/superpowers/`, `.superpowers/` (SDD scratch), `docs/progress.md` and
  every `README.md`.
  Rule scoping and reported paths are relative to the **repo root**, not to
  the target, so `python tools/doc_lint.py docs/vanilla/nutrition-core.md`
  reports the same findings the full scan does for that file — narrowing the
  target can never silently switch a rule off. `--root DIR` points that root
  somewhere else (the tests lint a temp tree that way); module API:
  `lint(targets, repo_root=None) -> [Finding(path, line, rule, detail)]`.

- `food_scan.py` — `python tools/food_scan.py`
  Parses the 42.20.4 scripts under `media/scripts/generated/` and writes
  `data/food-items.json` + `data/food-items.csv` (1005 items, 61 columns, 61
  fluids), printing
  `food 722 · drainable 150 · fluid_container 133 · fluids 61`.
  Four source groups, one per `kind`: `items/food.txt` → `food` (every
  `base:food` item, 722), `items/drainable.txt` → `drainable` (every
  `base:drainable` item, 150), every `items/*.txt` scanned for
  `component FluidContainer` → `fluid_container` (133), and `fluids.txt` +
  `fluids_Alcoholic.txt` + `fluids_Beverages.txt` → `fluid` (61 — joined into
  the container rows and kept whole under the JSON's `fluids` key, never CSV
  rows of their own). Display names come from
  `lua/shared/Translate/EN/{ItemName,Fluids}.json`; every join miss is
  recorded in `meta` rather than papered over, and an absent script key is
  empty in the CSV and `null` in the JSON — never `0`. Columns, the selection
  rule and `meta` are documented in `data/README.md`.
  It also holds the **shared script-DSL parser** — nesting-aware, so a
  component's keys never flatten onto the item that owns it:
  `parse_script(text, path)`, `iter_blocks`, `walk` (the same walk, yielding
  `(parent, block)` where real parenthood matters), `named(block, name)` (the
  first child block with that name — `Fluids`, `Properties`, `Poison`),
  `values(block, key)` (every raw value the block writes to a key, in file
  order, matched the loader's case-insensitive way — a `Block` carries
  `entries`, every `Key = Value` line, beside `props`, which is
  last-write-wins, so a repeated key survives), `coerce` / `coerce_props`,
  `canonical_key`, `is_known_key`, `KEY_TYPES` (the 114 keys of
  `docs/vanilla/food-item-model.md`), `load_translations`. `recipe_scan.py`
  imports it; read the module docstring before changing it.

- `recipe_scan.py` — `python tools/recipe_scan.py --out-dir data`
  (also `--root` for a different `media/`, `--food` for a different
  `data/food-items.json`; the out-dir is created if it does not exist).
  Parses the same 42.20.4 scripts and writes **four** files:
  `data/recipes.json` + `data/recipes.csv` (969 `craftRecipe` rows, 37 CSV
  columns — inputs, outputs, item mappers, fluids, and the nutrition delta
  where every consumed input and every output resolves) and
  `data/evolved-recipes.json` + `data/evolved-recipes.csv` (the 63
  `evolvedrecipe` blocks joined to 6 881 ingredient rows, each with what it
  contributes to the dish at Cooking 0 and Cooking 10). `data/recipes.json`
  additionally carries a `replacements` array — the 163 `ReplaceOn*` links
  (3 cooked, 8 rotten, 110 use, 42 deplete) with the delta each swap moves.
  It prints its census, ending
  `163 ReplaceOn* links (3 cooked, 8 rotten, 110 use, 42 deplete)`.
  It **imports `food_scan`'s parser** (`sys.path` insert + `import
  food_scan`) and never walks the DSL itself, and it reads
  `data/food-items.json` for nutrition — through `FOOD_FIELDS`, so this plan's
  script-case names and the dataset's lowercase columns both resolve. Two
  rules a consumer has to know: an input amount is a count of **uses** unless
  the line carries `flags[ItemCount]`, and a delta term is only taken from a
  `nutrition_basis = per_item` row. Both output pairs are byte-stable across
  runs. Columns, the JSON shapes and `meta` are documented in `data/README.md`
  § recipes and § evolved-recipes; the model, the refusals and the live
  cross-check are `docs/vanilla/recipes-dataset-notes.md`.

## Planned (P4)

- `mod_food_diff.py` — which installed mods add/override Food items (compat
  matrix for the item pass).

Conventions: stdlib-only python, same parser style as
`pz-b42/tools/insulation_scan.py` (proven against the generated-script DSL,
including capital-`Scripts` mod dirs and version-folder resolution).
