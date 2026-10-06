# Tools

Builds on the pz-b42 toolchain (`C:\Users\Angus\pz-b42\tools\` — pzdis.py jar
disassembler + `pz.sh` wrapper, item/vehicle/tile scanners). Don't duplicate;
import patterns from there.

## Intake pipeline

- `fdc_fetch.py` -- `python tools/fdc_fetch.py [--dir tools/.fdc] [--verify]`
  Downloads the four FoodData Central pipeline sources (SR Legacy CSV zip,
  Foundation CSV zip, the retention-factors CSV, the iodine PDF) with urllib,
  no key, into the gitignored `tools/.fdc/`, and writes `manifest.json` (name,
  url, filename, bytes, sha256, fetched). Skips a file whose sha256 matches;
  `--verify` re-hashes and exits 1 on a mismatch; a 404 fails naming the URL.
  Module API: `sources()` returns a deep copy of the `SOURCES` list.
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
  `docs/feasibility`, `docs/mods-survey/teardowns` — directories the code still
  names, all four gone from the tree, so today the one stamped doc is
  `docs/reference/wall-map.md` — carry
  `Verified against: 42.20.4`), `placeholder` (`TODO`/`TBD`/
  `_digest pending_`), `sources` (stamped docs only: a `## Sources` heading
  with at least one non-blank line before the next `## ` heading), `grades`
  (stamped docs only: every body row of a table with an `Ev` column opens its `Ev` cell with a C/M/W grade, optionally bold; a letter inside a later tag does not count),
  `mirror-header` (the four header keys above, on every mirror). Skips
  `docs/superpowers/` and `docs/progress.md` (constants the code still carries,
  both gone from the tree), `.superpowers/` (SDD scratch) and
  every `README.md`.
  Rule scoping and reported paths are relative to the **repo root**, not to
  the target, so `python tools/doc_lint.py docs/reference/wall-map.md`
  reports the same findings the full scan does for that file — narrowing the
  target can never silently switch a rule off. `--root DIR` points that root
  somewhere else (the tests lint a temp tree that way); module API:
  `lint(targets, repo_root=None) -> [Finding(path, line, rule, detail)]`.
  **Table trap (2026-09-11, slice 10).** `_tables()` splits a row by stripping
  and splitting on `|` with no escape handling, so a backslash-escaped `\|`
  inside a cell **still splits the row** and shifts every later cell one place.
  In a table with an `Ev` column that either fails a correctly graded row or
  grades the wrong cell. Rewrite the cell (name the alternatives in prose)
  rather than escaping the pipe; the splitter is deliberately simple.

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
  checks as coded, lives in [`docs/reference/tools.md#mod-lint`](../docs/reference/tools.md#mod-lint)
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
  sweep are in [`docs/reference/tools.md#mod-lint`](../docs/reference/tools.md#mod-lint).

- `mod_inventory.py` — `python tools/mod_inventory.py [--out PATH] [--dry-run]`
  Sweeps the same workshop root as `mod_lint` and writes
  `data/mod-inventory.json` — one record per mod folder, **230 across 179
  workshop items at 2026-09-10 17:47**, ~2 s, byte-stable (LF, utf-8, on every
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
  (15 for Long Term Preservation, where the first cut of the field read 47;
  492 for `KATTAJ1 Military Pack`, where the second cut read 1 because `-`
  ended the name — 6630 over the corpus, 2026-09-10 17:47).
  **All three script regexes read the file comment-stripped**, because the
  engine's parser and `tools/food_scan.parse_script` both ignore `/* */` and
  `//` and a definition inside a comment is not a definition: `mod_inventory`
  **imports `food_scan._strip_comments`** rather than keeping a second opinion
  about what the engine skips, the same delegation `resolve()` makes to
  `mod_lint` for identity. It moved the two corpus mods that comment a
  definition out — Long Term Preservation 17 → **15** items and 135 → **117**
  keys, `ZVirusVaccine42BETA` 102 → **86** — and nothing else (881 rather than
  899 across the nine script-signal mods, 2026-09-10 17:47;
  [`../docs/facts/other-mods/catalog.md#sweep`](../docs/facts/other-mods/catalog.md#sweep)).
  One caveat remains before the
  field is read as food: it counts **every** item definition, clothing and
  vehicles included (288 for `Horse`), so food is counted by hand off the
  `Type = Food` blocks. `sandbox_options` reads all three roots a build could
  load the file from — the live folder, the mod root and **`common/`** —
  **55 rows**, 11 of which keep `sandbox-options.txt` only in `common/media`
  and read `false` before that root was checked. Everything but
  `bytes` describes the **newest version folder only** — the de-duplication a
  per-mod record needs, since a mod may ship the same scripts in three folders.
  `common/media`, which the build **also** loads, is not counted here and this
  scan asserts no merge rule of its own — though the rule itself is no longer
  open: slice 11 **measured** it (`td3-20260911-001948`) as the version folder's
  file winning a same-relative-path collision while `common/` supplies everything
  the version folder does not ship, both in one Lua state, bounded to a mod whose
  version folder ships colliding files. The scan is unchanged by that, so
  **`media_at` is still the guard on a zero**: **177 rows**
  list a `common/media` this scan did not read; on 111 of the 153 that also have a
  live `media/`, a `stats` bucket reads 0 while that folder holds the file kind, and
  with the 24 blank rows that is 135 of the 177 (2026-09-10).
  `live_media: false` is the narrower fact — the **24 rows** whose whole content
  sits in `common/media`, so the entire record is blank. (Measured 2026-09-10:
  no `common/media` in the corpus carries a nutrition key, so nothing is hidden
  from the catalog.) Every field, the counts above and the
  `workshop_item_mtime` caveat are documented in
  [`docs/reference/datasets.md#mod-inventory`](../docs/reference/datasets.md#mod-inventory). Stdlib only bar
  `mod_lint` beside it; the workshop tree is read, never written.
  `--out` names the file the sweep writes (default `data/mod-inventory.json`,
  the 2026-09-10 snapshot the register cites, so a re-sweep that is to be cited
  goes to a new dated file such as `data/mod-inventory-2026-09-28.json`), and
  `--dry-run` sweeps and prints the summary and writes nothing; `--help` writes
  nothing either. Each record also carries `surfaces`, the census of fourteen
  named vanilla surfaces (`SURFACES`: the stat hook, hook registrations, eat,
  drink, tooltip and character-info wraps, MoodleFramework, trait, health,
  carry, stat and perk writes, player-field syncs, sandbox declarations) with
  each hit surface's count and first `path:line`, and the summary ends with one
  line per surface counting the mods that hit it.

- `workshop_search.py` — `python tools/workshop_search.py [--details]
  [--details-ids IDS] [--details-pause S] [--fill [--include-not-requested]
  [--fill-ids IDS|N]] [--catalog-ids IDS [--out F]] [--out-dir D] [--corpus F]`
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
  **`--catalog-ids <ids>` is a third pass and neither of those**: item pages for
  ids named from outside, no browse pass, no join, its own file
  (`--out`, default `data/workshop-catalog-details.json`), one row per id with
  a per-row `fetched_at` because there is no browse stamp to inherit. It exists
  because a mod no term returns is unreachable by the other two — `--details-ids`
  rejects it by name and `--fill` has no row to fill — which is the case for
  **eight of the nine mods** in
  [`../docs/facts/other-mods/catalog.md#status`](../docs/facts/other-mods/catalog.md#status).
  Run once, 2026-09-10 17:46: **9 requested, 9 fetched, 0 failed**;
  columns and the readings in
  [`docs/reference/datasets.md#workshop-rows`](../docs/reference/datasets.md#workshop-rows).
  **Flag combinations that cannot mean what they say are usage errors**, not
  quiet no-ops — `--details-ids` without `--details`, `--fill-ids` without
  `--include-not-requested` (a bare fill repairs failures only), `--fill` beside
  `--details`/`--details-ids`, `--catalog-ids` beside any of them, `--out`
  without `--catalog-ids`. Each of those parsed cleanly and did nothing before,
  which on a read that may not land costs a whole pass.
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
  load-bearing rows are documented in
  [`docs/reference/datasets.md#workshop-rows`](../docs/reference/datasets.md#workshop-rows).

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
  rule and `meta` are documented in [`docs/reference/datasets.md#columns`](../docs/reference/datasets.md#columns), [`#kinds`](../docs/reference/datasets.md#kinds) and [`#schemas`](../docs/reference/datasets.md#schemas).
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
  [`docs/facts/food-item-model.md#script-keys`](../docs/facts/food-item-model.md#script-keys)), `load_translations`. `recipe_scan.py`
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
  runs. Columns, the JSON shapes and `meta` are documented in
  [`docs/reference/datasets.md#schemas`](../docs/reference/datasets.md#schemas) § Recipes and § Evolved recipes; the model, the refusals and the live
  cross-check are [`docs/facts/cooking-and-recipes.md#dataset-fidelity`](../docs/facts/cooking-and-recipes.md#dataset-fidelity).

## Mod lints

- `kahlua_lint.py` — `python tools/kahlua_lint.py mod testing/experiments`
  Dialect lint over every Lua file under the paths given (comments and strings
  blanked first). Five rules: `goto` (the keyword or a `::label::`), `format-d`
  (an integer conversion inside `string.format`), `java-length` (`#` on a call
  result), `java-pairs` (`pairs`/`ipairs` over a call result), `loadstring`.
  Prints `path:line: rule: detail` and `N findings`; exit 1 on any finding.
- `hotpath_lint.py` — `python tools/hotpath_lint.py mod`
  Fast-path lint. Inside a `-- @fastpath` ... `-- @endfastpath` region it bars a
  table constructor, `..`, `pcall`/`xpcall`/`error`/`assert`, `string.`/`tostring`/
  `table.` calls, `^` and `math.exp|pow|log|sqrt`, loops, and a method call on a
  receiver outside the file's `-- @hoisted` list; one line per region marked
  `-- @rimguard` may carry the single `pcall`. On `NR_Kernel*.lua` it adds
  `kernel-shape` (only `function NutritionRevamp.kernel.<path>(` or
  `function K.<path>(`), `kernel-oneline` (no code after `then`/`else`/`do`/`repeat`/a
  `function` header on its line and no `X and Y or Z` value pick, because the coverage gate
  is line-granular) and `kernel-java` (no Java-side global named).
- The kernel tests under `testing/tests/kernel/` need `lupa` 2.8 (`python -m pip install lupa==2.8`): the mod's pure kernel runs offline under its Lua 5.1 runtime, and the suite fails rather than skips without it.

## Reference tooling

- `luabalance.py` — `python tools/luabalance.py <lua file> [...]`
  Bracket / block-`end` balance read-through for harness Lua (slice-08 shape, moved
  into the tree by the restructure). Strips comments and strings, then prints the
  delta of `{}` `()` `[]`, the `end`-depth and the count of lines where the depth
  went negative; exits 1 unless every file is `BALANCED`. Run it on every Lua file
  a harness commit touches, on the HEAD copy first and then the working tree.

- `claimslib.py` — no CLI. The claims register schema (`COLUMNS`, `KINDS`, `STATUSES`,
  `BOUND_TOKENS`, `POINTER_FORMS`, the id `BLOCKS`), TSV read/write, and the tag, pointer
  and bound grammars shared by `claims_harvest.py` and `claims_check.py`. The spec is
  `2026-09-17-reference-restructure-design.md` (the restructure spec, readable at the parent of the cut commit) § The claims register.

- `claims_harvest.py` — `python tools/claims_harvest.py candidates <md…> --out <tsv>` |
  `do-not-cite <artifacts README> --out <csv>` | `merge [--parts DIR] [--register TSV] [--coverage MD]`.
  `candidates` lists every body row of a table with an `Ev` column and every paragraph
  line carrying a grade mark (outside code fences), with the section heading, the evidence
  cell, the grade letters and run ids it names — the harvest checklist, not the register.
  `do-not-cite` turns the README's **Do not cite** blocks into `run,key,value,why,read_instead`
  rows (a prose restriction with no key has `key = *`). `merge` concatenates
  `parts/claims-*.tsv` sorted by id (a duplicate id fails), writes the register, and stitches
  `parts/coverage-*.md` under a totals table.

- `bus_inventory.py` — `python tools/bus_inventory.py [--lua-dir DIR] [--out FILE] [--check]`
  Generates `docs/reference/harness-commands.md` (one row per `TK.register` site and side:
  name · side · `file:line` · args · reply keys · purpose) from the `-- @args` / `-- @reply` /
  `-- @purpose` comment block directly above each site; a site without all three fails the
  run and is listed on stderr. `--check` exits 1 when the file on disk is not a fresh render.
  A harness commit that adds or changes a command edits the block and regenerates in the
  same commit (`claims_check.py` rule 5 enforces it).

- `reference_gen.py` — `python tools/reference_gen.py cited-by [--page docs/reference/artifacts.md] [--write | --check]` |
  `contradictions [--readme references/wiki-mirrors/README.md] [--write | --check]`.
  The reference's two generated sections, rendered from the register. `cited-by` fills the `Cited by`
  cell of every `## Contents` row of the artifacts register with the owner pages of the live rows whose
  pointer carries `run:<that run id>` (a row citing an alias in `run-aliases.csv` counts for the alias's
  line and its real run's), sorted and deduplicated, as links relative to `docs/reference/`; `—` when no
  row cites the run. `contradictions` writes a `## Contradictions` section: one table per mirror in the
  README's `## Mirrors` order (`| Row | The code says | The mirror says | Owner |`: the row's full tag, its
  claim, its bound's words after `mirror wrong:`, its owner page) from the live `contradiction` rows whose
  `wiki:` pointer names that mirror, between the markers `<!-- reference_gen: contradictions start -->`
  and `<!-- reference_gen: contradictions end -->` (appended at the end of the README when absent).
  `--write` rewrites only those cells or that section; `--check` exits 1 naming each drift (`section
  missing` on a README with no markers) and is `claims_check.py` rule 10; with neither it prints the render.

- `claims_check.py` — `python tools/claims_check.py [--register TSV] [--register-only] [--partial]
  [--staged] [--allow-provisional] [--fix-tags] [--view LAYER|LAYER/PAGE.md]
  [--section-map] [--root DIR]`
  The register checker (spec § The checker). Rules: `schema` (columns, grammars, duplicate ids,
  contiguity from each id sub-block's first id — or the slice's own first id when a `--register`
  part holds a continuation slice — within the block's last id, successors), `pointer` (`run:`
  folders exist or are aliased in `run-aliases.csv` — a `run:` pointer to an artifact-less run
  is allowed only on an `unverified` or `superseded` row whose bound starts `uncommitted:` —
  keys are neither listed in `do-not-cite.csv` nor a child of a listed key (`<listed>.<rest>`
  or `<listed>[<index>` is restricted too; an ancestor of a listed key is not — R34), `repo:`
  paths exist and name none of the pre-restructure docs or plans (the docs are
  at the tag `research-program-v1`; rule 3b `pointer-line`: a `repo:` pointer's quoted text must be
  on its cited line or range of the working-tree file, an artifact path, a line-less pointer and a
  `superseded` row exempt),
  `owner` (each row's owner page carries its tag), `tag` (every tag in `docs/{areas,platform,facts}`,
  the three reference pages that own register rows (`datasets.md`, `tools.md`, and `wall-map.md`)
  and the skills resolves
  and carries the canonical suffix; provisional `[T…]` tags fail),
  `untagged` (warning only: a number without a tag outside fences, tables and `## Procedure`;
  a digit inside a markdown link target is not a number, though the link text still counts;
  never under `docs/reference/`), `generator` (`harness-commands.md` is a fresh render of the
  `bus_inventory.py` scan, labelled with its `label_for`), `skill` (every `## Rules quoted` line is
  verbatim on a `## Read first` page), `example` (`## Worked examples` paths exist), fix-tags and
  views (rule 8: `--fix-tags` writes each tag's suffix from the register; `--view LAYER|LAYER/PAGE.md`
  prints a register slice), `rules-dup` (rule 9: for each pair of pages under `docs/areas` and
  `docs/platform` and each tag-id set both carry on a `## Rules` line, a finding fires only when the
  two pages share no byte-identical line for that set, once per page on its first line of that set;
  a page's several rules on one set are never compared with each other, so a verbatim copy of one
  rule is clean beside the other rules its source page carries on the same set), `refgen` (rule 10:
  the two generated sections are fresh renders of `reference_gen.py` — the `Cited by` column of
  `docs/reference/artifacts.md` and the `## Contradictions` section of
  `references/wiki-mirrors/README.md`; a drift, an absent file or a README without its markers
  is a finding on the file).
  `--register-only` = schema + pointer (Phase 1; every harvest part is checked this way);
  `--partial` lets `owner` skip pages not yet written (Phases 2–3); `--staged` skips when nothing
  relevant is staged; `--allow-provisional` tolerates a `[T<task>.<n>]` tag an unapplied delta
  still owns; `--fix-tags` rewrites suffixes from the register across the files `tag` reads;
  `--view LAYER` prints a layer's rows, `--view LAYER/PAGE.md` one page's.
  Exit 1 iff a non-warning finding. Run it before every commit that touches `docs/`,
  `.claude/skills/`, `testing/PZTestKit/`, `testing/artifacts/`, `testing/experiments/` or
  `tools/bus_inventory.py`, `tools/reference_gen.py` or `references/wiki-mirrors/`.

- `claims_delta.py` — `python tools/claims_delta.py apply <delta.tsv> --pages <page.md>… [--register TSV] [--dry-run]`.
  The controller's tool for a page task's delta file (spec § The claims register, "Deltas in Phases 2 and 3";
  the file shape is `restructure-2-page-procedure.md` (the Phase 2 page procedure, readable at the parent of the cut commit) § 6): mints the next free id for
  each `add`, supersedes a `split` parent with its two children, retargets an owner, changes a status; rewrites
  the provisional tags on the named pages and re-canonicalises them; prints every change and any provisional
  tag it did not cover; exits 1 and writes nothing on an invalid delta. Never deletes a row. Not idempotent: preview
  with `--dry-run`, then apply exactly once — a second apply mints a second row for the same `add`. A delta naming a row that is already
  `superseded` is refused, and a `retarget` whose new owner page is not among `--pages` is noted.
  `supersede <id>` makes the `add` its `successor` cell names (a provisional id, wherever it sits) the row's single successor, or the one `add` directly after it when the cell is empty (the two-child form is `split`); a cell naming no `add` is refused (the cell was once ignored, review-t16 I1);
  a successor that already exists is `status` with a `successor` cell.

- `page_lint.py` — `python tools/page_lint.py <page.md>… [--partial] [--allow-provisional] [--register TSV] [--cap N]`. The page
  contract (spec § The page contract) as rules for `docs/areas`, `docs/platform`, `docs/facts`: the stamp
  line, the section set and order per layer, the `<a id>` anchors against the register's owners, the
  rule-line shape, the closing `Not covered:` line, the narrative markers, the prose cap (400; 500 on the four
  pages the spec allows; under 150 warns, except on `facts/other-mods/` pages and
  `areas/open-questions.md`), worked-example paths (a cell with no `file:lines` is its own finding),
  relative links and their anchors — the anchor half runs only for targets under `docs/areas`,
  `docs/platform` and `docs/facts` (`datasets.md`, `tools.md` and `wall-map.md` carry `<a id>` anchors and are fragment-checked;
  `wall-map.md` is a link target only, never a page this lint is passed, since `doc_lint.py` owns it; other
  `docs/reference/` pages are not), a fragment that is not a
  lowercase slug (`a-z`, `0-9`, `-`, `_`) is a finding, and `--partial` skips a target page not written yet.
  A `## ` line inside a code fence never opens a section. Two pages have their own profile:
  `areas/open-questions.md` takes the sections `Index`, `Decisions`, `Experiments`, `See also`, reports
  `open-index` for any `open` register row with no tag on the page, and has no prose floor; the reference
  profile (`reference/datasets.md`, `reference/tools.md`) checks the stamp, the anchors against the
  register, the links and the narrative markers only (no section set, rule lines, walls, worked examples,
  cap or floor) and prints `(no cap)`. Prints the prose count per page; exit 1 on a finding.
  `--allow-provisional` admits a provisional tag on a rule or key-fact line.

- `sciencelib.py` — no CLI. The science register schema (`COLUMNS`, `GRADES`, `RANK`, `STATUSES`,
  `TOPICS`, the controlled topic vocabulary), TSV read/write, `validate_row`, `resolve_grade`
  (a report's grade token to a grade: `CASE` maps to `COH`, a slashed pair takes the left-most
  member of `RANK`, `MODEL` never pairs) and the id, token, citation and source grammars shared by
  `science_check.py` and `science_delta.py`. The page is `docs/reference/science.md`.

- `science_check.py` — `python tools/science_check.py [--register TSV] [--part TSV] [--scan PATH…] [--staged] [--root DIR]`
  Two rules. `schema` checks the header, the cell count, the id form, contiguity from `S0001`,
  duplicates, the topic and grade vocabularies on every row that is not open, the status, a
  non-empty value and a `doi:`/`pmid:`/`url:`/`isbn:` citation on every settled, unverified or
  superseded row, the source form, and a successor present exactly when superseded and naming
  a live row. `scan` (under `--scan`) resolves every `S<dddd>` token in the named `.lua`, `.md`,
  `.py`, `.toml` and `.txt` files against the register; the register and its page are skipped, and
  `--scan` is given the mod's tree, never `tools/` or `docs/`. `--part` checks a task's part file
  with provisional ids and skips contiguity; `--staged` skips the run when nothing staged is under
  the register or a scanned path. Prints `path:line: rule: detail` per finding and `N findings`;
  exit 1 on any.

- `science_delta.py` — `python tools/science_delta.py apply <part.tsv> [--register TSV] [--dry-run] [--allow-duplicate]` |
  `status <Sdddd> <status> [--successor Sdddd[, Sdddd]] [--register TSV]` |
  `settle <Sdddd> --topic T --grade G --value V --citation C [--range R] [--population P] [--status unverified]`.
  The controller's tool. `apply` validates every row of a part file (a bad row aborts before
  anything is written, naming its line; a real id, a repeated provisional id or a row whose parameter,
  citation and source already sit in the register is refused unless `--allow-duplicate`), mints
  the next free id for each in file order, appends them and prints `S2.1 -> S0001` per row and
  `rows: N`. `status` changes one row's status and successor (a comma list), refuses a row already superseded, a
  successor that is missing, superseded or the row itself, and `--successor` without `superseded`; an open
  row may be superseded with its cells empty. `settle` fills an open row's cells and sets it `settled`
  (or `unverified`), validating the result. Never deletes a row.

## Planned (P4)

- `mod_food_diff.py` — which installed mods add/override Food items (compat
  matrix for the item pass).

Conventions: stdlib-only python, same parser style as
`pz-b42/tools/insulation_scan.py` (proven against the generated-script DSL,
including capital-`Scripts` mod dirs and version-folder resolution).
