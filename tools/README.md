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

- `mod_lint.py` — `python tools/mod_lint.py [<mod folder>|<workshop id> ...] [--workshop-dir D]`
  The **L0** layout check: is this folder even shaped like a B42 mod? An
  all-digits target is a workshop item id and expands to
  `<WORKSHOP_DIR>/<id>/mods/*`; no arguments at all sweeps every mod under the
  workshop root (`D:\SteamLibrary\steamapps\workshop\content\108600`,
  `--workshop-dir` to point elsewhere). Prints `mod: LEVEL: rule: detail`, then
  `N finding(s): a ERROR, b WARN, c INFO across M mod(s)`; **exit 1 iff an ERROR
  fired** (WARN and INFO exit 0). **Nine rules** — five ERROR (`version-dir`,
  `mod-info`, `id`, `id-agree`, `loadstring`), three WARN (`mod-info-place`,
  `id-drift`, `media`) and one INFO (`folder-id`). The table, with what each one
  checks as coded, lives in [`docs/testing/profiles.md`](../docs/testing/profiles.md) § L0
  and in the module docstring; it is not restated here. Version folders sort by
  parsed tuple, not by string, so `42.20.1 > 42.20 > 42.9 > 42`, and
  `pzt.mods.mod_id_of` resolves the same way (`testing/tests/test_mods_resolution.py`
  holds the two together). Module API mirrors `doc_lint.py`:
  `Finding(path, level, rule, detail)`, `lint_mod(mod_dir, name=None)`,
  `lint(targets, workshop_dir=None)`, plus `version_dirs` / `read_info` /
  `info_chain` / `media_root` / `mod_dirs` / `display_name`. Deliberately
  **standalone** — stdlib only, no import of `testing/pzt` — so `tools/` stays
  runnable without the game. The installed 230-folder corpus scored **84 findings
  (3 ERROR, 30 WARN, 51 INFO) at 2026-09-10 13:47**, ~13 s cold; the tree is
  live, so quote a sweep with its date — the rows and the drift since the first
  sweep are in [`docs/testing/profiles.md`](../docs/testing/profiles.md) § L0.

- `mod_inventory.py` — `python tools/mod_inventory.py`
  Sweeps the same workshop root as `mod_lint` and writes
  `data/mod-inventory.json` — one record per mod folder, **230 across 179
  workshop items at 2026-09-10 16:20**, ~2 s, byte-stable (LF, utf-8, on every
  platform) — then prints the class histogram, the `loadstring` and b41-flat
  lists, the top 20 by lua size,
  the two nutrition signals side by side, and a folder-name-≠-id block (**52
  rows**; `mod_lint`'s `folder-id` INFO counts 51, having no id to compare on
  the 52nd). **Identity is `mod_lint`'s answer, not a second opinion**:
  `resolve()` imports `version_dirs` / `info_chain` / `read_info` /
  `media_root`, so `mod_id` is the id the running build resolves and is **`""`**
  when no `mod.info` exists anywhere (1 row) — never the folder name, which is
  kept beside it as `mod_id_fallback`. Two independent nutrition signals,
  because neither alone is the catalog: `signals.food_nutrition` greps `.lua`
  for the runtime API (11 mods) and `signals.script_nutrition` greps
  `<live>/media/**/scripts/*.txt` for the item-definition keys (9 mods, 1
  overlap); `script_item_blocks` beside them counts item
  definitions, recipe `item 1 [Base.X]` lines excluded and hyphenated ids kept
  (17 for Long Term Preservation, where the first cut of the field read 47;
  492 for `KATTAJ1 Military Pack`, where the second cut read 1 because `-`
  ended the name — 6648 over the corpus, 2026-09-10). Two caveats before that
  field is read as food: it counts **every** item definition, clothing and
  vehicles included (288 for `Horse`), so food is counted by hand off the
  `Type = Food` blocks; and it does **not** strip `/* */` comment blocks, which
  the engine and `tools/food_scan.parse_script` both do, so it over-counts the
  two corpus mods that comment a definition out — Long Term Preservation 17
  against **15** live, `ZVirusVaccine42BETA` 102 against **86** (881 rather than
  899 across the nine script-signal mods, measured 2026-09-10;
  [`../docs/mods-survey/nutrition-mods.md`](../docs/mods-survey/nutrition-mods.md)
  § Discrepancies row 1 and § Open questions Q2). Everything but
  `bytes` describes the **newest version folder only** — the de-duplication a
  per-mod record needs, since a mod may ship the same scripts in three folders.
  `common/media`, which the build **also** loads, is not counted here and no
  merge rule is asserted, so **`media_at` is the guard on a zero**: **177 rows**
  list a `common/media` this scan did not read; on 111 of the 153 that also have a
  live `media/`, a `stats` bucket reads 0 while that folder holds the file kind, and
  with the 24 blank rows that is 135 of the 177 (2026-09-10).
  `live_media: false` is the narrower fact — the **24 rows** whose whole content
  sits in `common/media`, so the entire record is blank. (Measured 2026-09-10:
  no `common/media` in the corpus carries a nutrition key, so nothing is hidden
  from the catalog.) Every field, the counts above and the
  `workshop_item_mtime` caveat are documented in
  [`data/README.md`](../data/README.md) § mod-inventory. Stdlib only bar
  `mod_lint` beside it; the workshop tree is read, never written.

- `workshop_search.py` — `python tools/workshop_search.py [--details]
  [--details-ids IDS] [--details-pause S] [--fill [--include-not-requested]
  [--fill-ids IDS|N]] [--out-dir D] [--corpus F]`
  The **outward** half of the catalog: what nutrition-relevant B42 mods exist on
  the public Workshop, and which of them are installed here. Eight terms
  (`nutrition`, `vitamin`, `malnutrition`, `diet`, `hydration`, `food overhaul`,
  `cooking overhaul`, `spoilage`) against the `Build 42`-tagged ready-to-use
  browse section, one page each (Steam serves 30 a page; the tool does not
  paginate), then a join to `data/mod-inventory.json` and
  `data/workshop-search.json` + `.csv`. **212 results → 180 distinct items, 3
  installed, fetched 2026-09-10 16:26** (`meta.fetched`; the run itself
  16:25:31–16:26:22), of which **15 rows carry item-page stats and 165 were
  never asked for, 0 failed** (2026-09-10 16:56, after one `--fill` pass).
  Stdlib + `subprocess` curl in
  `wiki_mirror.py`'s shape; nothing is subscribed and nothing is written under
  the workshop root.
  **`--compressed` is mandatory** — without it curl hands back gzip bytes and
  every regex misses (5 876 unreadable bytes against ~686 000 readable). The
  browse page is React-rendered with per-deploy obfuscated class names, so the
  only things read off it are the `filedetails/?id=N` href and the thumbnail's
  `alt` title; the item page is the older server-rendered template
  (`workshopItemTitle`, two or three `detailsStatRight` divs — two means the item
  has never been updated, so `updated` is `null` as a fact, not as a gap).
  **The join key is `workshop_id`, never `mod_id`**: a Workshop page has no idea
  what id a mod declares, and 20 corpus ids moved in this slice.
  **An item page can answer 200 with a page the parser cannot read** — the
  generic Workshop landing page, no `workshopItemTitle` and no
  `detailsStatRight` — so a naive run records rows of silent `null`s: the first
  run of this tool recorded **177 (2026-09-10 15:52, output discarded)**. Every
  fetch is now checked for the markers its parser needs (**both** item markers,
  and `browsesort` or a result anchor on a browse page); a body without them is
  a failure, retried once, then recorded; `counts.details_incomplete` must stay
  0. **How many item pages a session may read is not modelled and no figure is
  quoted for it** — the record is four dated observations from 2026-09-10 with
  no rule fitted to them: 15:45, 8 browse pages then 3 item pages then the
  alternate template; 15:58, the alternate template from the first request;
  16:25 (the committed sweep), 8 browse pages then all **9** item pages it asked
  for, none throttled; 16:55, a fill pass 30 minutes later reading **6** more in
  24 s, none throttled. Because a read may not land, `--details-ids` asks only
  for a **declared subset** — a list in which `installed` expands to every row
  that joined to the corpus, and an id this sweep did not return is rejected by
  name rather than counted as requested.
  **Three row states, one field.** `details_status` is `fetched`,
  `not_requested` (nobody asked for it — `error` is `null` and nothing about the
  item is claimed) or `failed` (asked for, unreadable — `error` says why), so
  `error` is a fetch failure and never a decision. `--fill` re-fetches every
  `failed` row; `--fill --include-not-requested [--fill-ids <ids|N>]` also tops
  up `not_requested` rows, named or the first N in dataset order (a bare number
  under 7 digits is a count, since a workshop id is 9–10). Either way the row
  set, the terms and `meta.fetched` are left alone — a re-sweep would change the
  trend-sorted row set — and each pass appends `{at, ids, fetched, failed}` to
  `meta.fill`.
  **The retry budget is per failure mode, not per URL**: `fetch_once_retried`
  spends the one allowed retry after 5 s on a transport error or an empty body,
  and `fetch_usable` retries once more after 5 s when the body came back as a
  template the parser cannot read — so a URL that fails both ways costs **up to
  3 curls and 10 s** of sleeping, where the brief costed one retry. Nothing
  retries a third time and no failure raises: it is recorded on the row.
  **A not-installed row is graded `W`** and carries the exact unblocking action
  (`subscribe to <id> in Steam, let it download, re-run tools/mod_inventory.py`):
  it cannot be linted, profiled, booted or measured from this repo, so teardown
  picks come only from the installed corpus. Columns, `meta` and the
  load-bearing rows are documented in [`data/README.md`](../data/README.md)
  § workshop-search.

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
