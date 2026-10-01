# Tools
Verified against 42.20.4 (b0bbce05d5) · 2026-09-26 · scope: every tracked tool under `tools/` — what each reads and writes, its rules with their engine standing, its conventions — and the register grammar the claims tools enforce; the datasets the scanners write are `datasets.md`'s.

<a id="doc-lint"></a>
## `doc_lint.py` — the documentation lint

`python tools/doc_lint.py [target ...] [--root DIR]` walks the named files and directories, or the whole repository when none is named, and lints every Markdown file it meets.
The documentation lint has five rules — a build stamp in four named directories, a placeholder ban, a non-empty sources section in those same directories, a standalone evidence grade in every body row of a table with an evidence column, and the four mirror header keys — printing one finding per line and exiting 1 if any fired; it skips the plan and scratch trees, the board and every README [#1947].
The stamp it requires is the line `Verified against: 42.20.4`, which is not the page contract's stamp; `page_lint.py` checks that one.
The lint's rule scoping and reported paths are relative to the repository root and not to the target, so narrowing the target can never silently switch a rule off [#1948].
The lint's table splitter strips and splits a row on the pipe character with no escape handling, so an escaped pipe inside a cell still splits the row and shifts every later cell one place, which in a table with an evidence column either fails a correctly graded row or grades the wrong cell [#1949].
The splitter is deliberately simple, so a cell that needs a pipe is rewritten, with the alternatives named in prose, rather than escaped [#1949].
`doc_lint` stamps one file, `docs/reference/wall-map.md`, beside stamped-directory constants whose directories are gone from the tree, and its `sources` and `grades` rules run on stamped files only [#1675].

<a id="mod-lint"></a>
## `mod_lint.py` — the layout lint (`L0`)

`python tools/mod_lint.py [<mod folder>|<workshop id> ...] [--workshop-dir D]` lints one mod folder, every mod a workshop item ships when the target is all digits, or every mod under the workshop root when no target is named, and prints one `mod: LEVEL: rule: detail` line per finding, then a count line.
The layout lint runs nine static rules over a mod folder — five errors, three warnings and one informational — exits 1 only when an error fired, resolves the mod-info file newest version folder first then older ones then the common folder then the mod root, and is deliberately standalone so the tools directory stays runnable without the game [#1836]:

| Rule | Level | Check as coded |
|---|---|---|
| `version-dir` | ERROR | at least one child folder matching `^42(\.\d+){0,2}$` (b41-flat and unversioned mods fail here) |
| `mod-info` | ERROR | a `mod.info` exists in **some** version folder, in `common/`, or at the mod root |
| `mod-info-place` | WARN | there is a version folder and the **newest** one holds the `mod.info`; the detail names where it actually is, and says the expectation is **this lint's model**, not a read of the engine |
| `id` | ERROR | the resolved `mod.info` declares a non-empty `id=` |
| `id-agree` | ERROR | every `mod.info` a **resolver can reach** declares the same `id` — the chain below, plus anything the wider `42*` glob in `mods.mod_id_of` catches. A disagreement there decides the mod's id by which file was opened first |
| `id-drift` | WARN | a `mod.info` **outside** that chain (a `LEGACY/42.12/mod.info`, a vendored copy) declares a different id. No resolver can reach it, so it cannot change anyone's answer — worth knowing, not a defect |
| `media` | WARN | `media/` exists inside the chosen version folder |
| `loadstring` | ERROR | no `\bloadstring\s*\(` in any `.lua` under the folder (removed from the engine in 42.20.x) |
| `folder-id` | INFO | folder name == the resolved `id` |

The lint's version folders sort by parsed tuple and not by string, and the orchestrator's own resolver sorts the same way, with a test holding the two together on every layout the corpus ships; a string sort of the resolver's glob would pick a different file on six installed mods, all six declaring the same id in both, which is what the agreement rule exists to stop being luck [#1837].

`tools/mod_lint.py` runs nine `L0` rules before any server boots — five errors, three warnings and one informational — and their standing against the engine, as read on 2026-09-11, is this [#0857/C/snapshot]:

| Rule | Level | Standing |
|---|---|---|
| `version-dir` | ERROR | model, deliberately strict: the engine tolerates a mod with no version dir at all (`getModVersionDirName` returns `"42"`, that path does not exist, and `common/` carries both the id and the media). No installed mod ships that shape — all 230 have one — so the rule has never fired on the corpus, and it stays an ERROR for *our* mods, where a missing version dir is a packaging mistake |
| `mod-info` | ERROR | engine reading, widened: the engine needs a `mod.info` in the build's version dir **or** `common/`, and warns `can't find mod.info in mod dir` otherwise |
| `mod-info-place` | WARN | **now a bounded engine reading.** The version dir's `mod.info` is the one that supplies the id; `common/` is the fallback |
| `id` | ERROR | engine reading — an unparsed or missing `id=` leaves `Mod.id` at its constructor default `undefined_id` |
| `id-agree` | ERROR | **stricter than the engine needs, and kept.** The engine opens one file, so a disagreement cannot change today's id; but the flagged file becomes authoritative the moment the version dir's `mod.info` is removed or the build moves past that version dir |
| `id-drift` | WARN | unchanged — an out-of-chain copy no resolver can reach |
| `media` | WARN | **an intent check, not a load failure** — measured a version dir with a `mod.info` and no `media/` loading its whole `common/` payload |
| `loadstring` | ERROR | unchanged — removed from the engine in 42.20.x |
| `folder-id` | INFO | **now an engine reading, and correctly informational** — the folder name is never consulted |

The engine tolerates a mod with no version dir at all: `getModVersionDirName` returns `42`, that path does not exist, and `common/` carries both the id and the media — so the lint's error is deliberately stricter than the engine, and it has never fired on the corpus because all 230 installed mods ship one, as the corpus stood on 2026-09-11 [#0858/C/snapshot].
An unparsed or missing `id=` leaves `Mod.id` at its constructor default `undefined_id`, which is why the lint treats it as an error; this is read from the jar, not measured [#0860/C/C-only].
The lint's `id-agree` error is stricter than the engine needs and is kept anyway: the engine opens one file, so a disagreement cannot change today's id, but the flagged file becomes authoritative the moment the version dir's `mod.info` is removed or the build moves past that version dir — a reading of the lint against the engine chain, not a measurement [#0861/C/C-only].

The standings that are measured statements rather than conventions rest each on one run of one build.
The lint's `mod-info-place` warning is a bounded engine reading: the version dir's `mod.info` is the one that supplies the id and `common/` is the fallback, measured with one probe per boot on the dedicated-server requested-id lookup only, the client's own mod-list call site never exercised [#0859/M/n=1].
The lint's `media` warning is an intent check and not a load failure: a version dir holding a `mod.info` and no `media/` loaded its whole `common/` payload, in one session with one purpose-built mod [#0862/M/n=1].
The lint's `folder-id` informational finding is an engine reading and correctly informational: the folder name is never consulted, measured with one probe per boot on the dedicated-server path, server side only [#0863/M/n=1].
The lint's media-root model of a newest version folder stays a model in one respect only: it ignores the engine's ceiling of the running build, which is invisible on a corpus whose version dirs top out at `42.20.1`, as swept on 2026-09-10 17:47 [#0864/C/snapshot].

Recomputed over the read-only workshop tree on 2026-09-11, `mod_lint.info_chain` is a superset of the engine's chain — it tries every version folder and the mod root where the engine tries one version folder and `common/` — and across the 230 installed folders the two pick the same file on 229 and differ only on `3396446795/MoodleFramework`, which ships `mod.info` in `42.0/` and `common/` only, so the lint opens `42.0/mod.info` and the engine opens `common/mod.info`; both declare the same id, so no id moves [#0824/C/snapshot].
The five other `mod.info`-placement warnings on the corpus, recomputed the same day, are not chain discrepancies: all five ship `mod.info` in `common/` and in no version dir, so the lint and the engine open the same file, and the one that also ships a root `mod.info` with the same id ships it where neither reader ever looks [#0879/C/snapshot].
The 230-folder installed corpus scored 84 findings — three errors, thirty warnings and 51 informational — in about thirteen seconds cold on the sweep of 2026-09-10 13:47; the tree is live, so a sweep is quoted with its date [#1838/C/snapshot].
The sweep's findings by rule and its reproduction the next day are unverified and are stated under [Open](#open).

<a id="mod-inventory-tool"></a>
## `mod_inventory.py` — the corpus inventory

`python tools/mod_inventory.py [--out PATH] [--dry-run]` writes `data/mod-inventory.json` by default, one record per mod folder, whose columns are [datasets.md § mod-inventory](datasets.md#mod-inventory).
`--out` names the file the sweep writes, so a re-sweep that is to be cited goes to a new dated file and a cited snapshot is never overwritten, `--dry-run` sweeps and prints the summary and writes nothing, and `--help` writes nothing ([datasets.md#mod-inventory](datasets.md#mod-inventory)).
Each record also carries `surfaces`, the census of named vanilla surfaces a mod hooks, wraps or writes, with each surface's hit count and first site, whose shape is [datasets.md § mod-inventory](datasets.md#mod-inventory), and the console summary ends with one line per surface counting the mods that hit it.
The inventory tool sweeps the same workshop root as the layout lint and writes the inventory file in about two seconds, as timed on the sweep of 2026-09-10 17:47, byte-stable on every platform, then prints the class histogram, the dynamic-compiler and flat-layout lists, the top twenty by Lua size, the two nutrition signals side by side and a folder-name-against-id block [#1950/C/snapshot].
Identity is the layout lint's answer and not a second opinion: the inventory imports the lint's version-folder, chain, read and media-root functions, so the resolved id is the id the running build resolves and is empty when no mod-info file exists anywhere, never the folder name, which is kept beside it [#1951].
All three of the inventory's script regular expressions read the file comment-stripped, because the engine's parser and the food scanner both ignore block and line comments and a definition inside a comment is not a definition — and the inventory imports the scanner's own stripper rather than keeping a second opinion about what the engine skips [#1952].
`mod_inventory` computes `signals`, `stats` and `lua_kb` over the single folder `mod_lint.media_root` resolves, so for a two-tree mod its row is a partial view — on Auto Cook, as swept on 2026-09-10, it hides 7 of 10 Lua files, 1 238 of 2 155 lines, the mod's only event registration, its only vanilla patch and its entire translation set — and a `media_at` list with two entries is the flag that says so [#1309/C/snapshot].
Every run is a dated snapshot: the workshop tree is live and Steam rewrites folders under it, so the file carries no build stamp and the sweep date in its documentation is the stamp every count quotes ([#1915/C/snapshot], [datasets.md#mod-inventory](datasets.md#mod-inventory), [lessons.md#corpus-drift](../platform/lessons.md#corpus-drift)).
The workshop tree is read and never written.

<a id="food-scan"></a>
## `food_scan.py` — the food scanner and the shared script parser

`python tools/food_scan.py` takes no argument and writes `data/food-items.json` and `data/food-items.csv` from the install's `media/scripts/generated/` tree.
The food scanner parses the generated scripts of `42.20.4` and writes the food dataset pair, printing its four bucket counts; display names come from the two English translation files, every join miss is recorded in the metadata rather than papered over, and an absent script key is empty in the flat file and null in the JSON, never zero [#1957/C/snapshot].
Which script blocks enter the dataset is decided by one selection call, `food_scan.select` ([#0610/C/snapshot], [datasets.md#kinds](datasets.md#kinds)).
The food scanner holds the shared script parser and it is nesting-aware, so a component's keys never flatten onto the item that owns it; its interface is a parse call, a block iterator, a parent-aware walk, a named-child lookup, a raw-values accessor matched the loader's case-insensitive way, two coercion helpers, a key canonicaliser, a known-key test, the 114-key type table and a translation loader [#1958].
The shared block reader makes a `Block` of `kind`, `name`, `module`, `file`, `line`, `props` (last write wins, as the loader does), `entries` (every `Key = Value` in file order, so a repeated key survives), `lines` and `blocks`, and on the `42.20.4` scripts `entries` carries 3 512 repeated prop lines `props` cannot see — 145 `fluid =` lines over 68 `Fluids` blocks and 34 `SoundMap` lines in `drainable.txt` [#0642/C/snapshot].
A block header is decided by lookahead — a non-`Key = Value` line whose next logical line is an opening brace, with `kind` the first token and `name` the rest — which is what parses the 156 shipped blocks carrying a multi-word or numeric name; all 34 683 blocks of the `42.20.4` script tree then parse with 0 anonymous opens [#0643/C/snapshot].
The `42.20.4` fluid files write float literals on int-typed keys — 141 values such as `UnhappyChange = -10.0` and `StressChange = 0.0` — and the scanner's `coerce` returns `int` for an integral literal, so one `KEY_TYPES` entry stays one Python type [#0657/C/snapshot].
The parser reads a file comment-stripped: `_strip_comments` blanks block and line comments before any line is read and keeps the line count, so a recorded line number stays true, and the inventory imports the same stripper ([§ `mod_inventory`](#mod-inventory-tool)).
The parser half of the module is shared with the recipe scanner and the dataset half is the food scanner's own, so a change to the parser is read against the module docstring first.

<a id="recipe-scan"></a>
## `recipe_scan.py` — the recipe scanner

`python tools/recipe_scan.py --out-dir data` writes the craft-recipe pair `data/recipes.json` and `data/recipes.csv` and the evolved-recipe pair `data/evolved-recipes.json` and `data/evolved-recipes.csv`, creating the output directory if it is missing; `--root` points it at a different `media/` and `--food` at a different food dataset, and the counts it prints are [datasets.md § counts](datasets.md#counts).
The recipe scanner walks all 1 004 `media/scripts/**/*.txt` files of the `42.20.4` install and hardcodes no directory [#0683/C/snapshot].
The recipe scanner imports the food scanner's parser and never walks the script grammar itself, and it reads the food dataset for nutrition through a field map so that script-case names and the dataset's lower-case columns both resolve; both of its output pairs are byte-stable across runs [#1959].
The shared parser accepts identifier keys only, so the 1 599 dotted mapper lines of the `42.20.4` recipes land in a block's `lines` rather than its `props` — deliberately, because dotted keys in `props` would collapse the 56 mappers that name one result twice down to their last source — and the dataset keeps them lossless in `itemMapperPairs` [#0768/C/snapshot].
A craft's nutrition delta is computed only where every consumed input and every output resolves to a row of the food dataset, and a delta term is taken only from a per-item row; everything else is left empty with its reason named, never zero ([#0717], [#1904/C/arith.], [datasets.md#columns](datasets.md#columns)).
An input amount is a count of uses unless its line carries `flags[ItemCount]` ([#1901], [cooking-and-recipes.md#uses](../facts/cooking-and-recipes.md#uses)).
The entity build recipes that sit inside a `component CraftRecipe` are censused and not scanned ([#0681/C/snapshot], [datasets.md#counts](datasets.md#counts)).
Whether an output mapper that writes only a `default` should resolve to that default is the scanner's open question, under [Open](#open).

<a id="workshop-search"></a>
## `workshop_search.py` — the Workshop sweep

`python tools/workshop_search.py` sweeps a fixed set of search terms against the build-tagged, ready-to-use browse section of the public Workshop, one page per term with no pagination, and joins the results to the inventory ([#1932/W/snapshot], [datasets.md#workshop-rows](datasets.md#workshop-rows)).
Its query surface is a handful of flags: `--details` reads item pages for size, posted and updated dates, `--details-ids` narrows that pass to a declared subset in which `installed` expands to every row that joined to the corpus, `--details-pause` spaces the reads, `--fill` re-reads the failed rows and with `--include-not-requested` and `--fill-ids` tops up rows never asked for, `--catalog-ids` with `--out` reads item pages for ids named from outside, and `--out-dir` and `--corpus` move the output and the inventory it joins.
Nothing in the workshop sweep is subscribed, downloaded or written under the workshop root: pages are read once and never faster than one request a second, and only the extracted facts are recorded — no page is mirrored [#1933].
The join key is the workshop id and never the mod id, because a Workshop page has no idea what id a mod declares [#1954].
The compressed flag is mandatory on every fetch — without it the transfer hands back compressed bytes and every pattern misses, 5 876 unreadable bytes against about 686 000 readable — and the browse page is rendered client-side with per-deploy obfuscated class names, so the only things read off it are the item link and the thumbnail's alternative text, while the item page is the older server-rendered template whose two-or-three statistic divisions are what make a never-updated item a fact rather than a gap [#1953].
A result row is in one of three states, held in one field: `fetched`, `not_requested` or `failed`, and its `error` is a fetch failure and never a decision ([#1938/C/snapshot], [datasets.md#workshop-rows](datasets.md#workshop-rows)).
An item-page read can come back as the generic Workshop landing page with a success code and neither of the two markers the parser needs, which is the failure state the row-status field exists for, so every fetch is checked for both markers, retried once and then recorded as failed [#1940/C/snapshot].
The completeness counter `counts.details_incomplete` is the guard against a naive parser recording such a page as an item that ships no statistics, and must stay at zero [#1940/C/snapshot].
The retry budget is per failure mode and not per URL — one retry after five seconds on a transport error or an empty body, and one more after five seconds when the body came back as a template the parser cannot read — so a URL that fails both ways costs up to three fetches and ten seconds of sleeping [#1956].
Nothing retries a third time and no failure raises: it is recorded on the row [#1956].
The details pass asks only for a declared subset because a read may not land, and a later top-up pass fills not-requested rows without re-sweeping — a re-sweep would change the trend-sorted row set and the fetch stamp with it [#1942/C/snapshot].
The catalog pass is a third route and neither of the other two: item pages for ids named from outside, no browse pass, no join, its own file and a per-row fetch stamp because there is no browse stamp to inherit [#1943/C/snapshot].
Flag combinations that cannot mean what they say are usage errors and not quiet no-ops — five of them are named: `--details-ids` without `--details`, `--fill-ids` without `--include-not-requested`, `--fill` beside `--details` or `--details-ids`, `--catalog-ids` beside any of them, and `--out` without `--catalog-ids` — because a combination that parses cleanly and does nothing costs a whole pass on a read that may not land [#1955].
How many item pages a session may read is not modelled, and the tool quotes no figure for it.

<a id="wiki-mirror"></a>
## `wiki_mirror.py` — the wiki mirror

`python tools/wiki_mirror.py <Page> ["Another page" ...]` writes one `references/wiki-mirrors/<slug>.md` per page, the slug taken from the page name.
The mirror tool fetches each wiki page as raw wikitext with a browser user agent, because a plain fetcher is refused, and writes a mirror carrying a four-key provenance header — source, fetch date, the wiki's own page version or an unstamped marker, and the licence — then a digest stub and the raw text in a fence; the placeholder rule keeps an un-digested mirror visible until it is digested by hand [#1946].
A mirror is re-read through its hand-written digest, which says what the page claims that the library uses or contradicts and what to verify in code first, and through the raw wikitext beneath it, which is kept verbatim so no fact is lost to summarising.
A mirror is cited through a `wiki:` pointer naming its path and its fetch date or page version, grades `W`, and is cited for corroboration only: where a mirror and the code disagree, the code wins and the disagreement is a `contradiction` row on the page that owns the mechanism.
The mirrors README records every absent page with its date and every redirect with its target, so an absent page is not re-fetched blindly.
No wiki mirror exists for food spoilage: as fetched on 2026-09-10, the food-spoilage page returns a 404 and the refrigerator and freezer pages both redirect to the appliances page, whose section is headed fridges as of `42.8.0` [#0370/W/snapshot].

<a id="claims-tools"></a>
## The claims tools

The claims tools keep the register `docs/reference/claims.tsv` and the pages that cite it consistent; the rules they enforce are the spec's, and this section states the tools' conventions and the grammar they read.

- `claimslib.py` has no command line: it holds the register's schema — its columns, kinds, statuses, bound tokens, pointer forms and id blocks — its TSV reader and writer, and the tag, pointer and bound grammars, and it runs inside the harvest, the checker, the delta applier and the page lint, which import it.
- `claims_harvest.py` runs by hand and never from a gate: `candidates <md…> --out <tsv>` lists every graded table row and graded paragraph line of the docs it is given as a harvest checklist, `merge` rewrites the register and `claims-coverage.md` whole from the harvest parts (a directory, `docs/reference/parts/`, that no longer exists, so a `merge` run today would write a header-only register over the live one), and `do-not-cite <artifacts README> --out <csv>` re-derives `docs/reference/do-not-cite.csv`, the list the checker's pointer rule reads, from that README's do-not-cite blocks.
- `claims_check.py` reads the register, every tagged page and skill, the do-not-cite list, the run aliases and the harness Lua, writes nothing except under `--fix-tags` (which rewrites tag suffixes from the register) and prints a register slice under `--view`, exits `1` on any finding but an untagged-number warning, and runs before every commit that touches `docs/`, `.claude/skills/`, `testing/PZTestKit/`, `testing/artifacts/`, `testing/experiments/` or `tools/bus_inventory.py`, with `--partial` while an owner page is unwritten and `--allow-provisional` while a delta is unapplied.
- `claims_delta.py` is the controller's tool: `apply <delta.tsv> --pages <page.md>…` reads a page task's delta file, mints the next free id for each `add`, supersedes a `split` parent with its children or a `supersede` parent with its one child, retargets an owner or changes a status in the register, and rewrites the provisional tags on the named pages; it exits `1` and writes nothing on an invalid delta, refuses a row already `superseded`, and runs exactly once per delta file after a `--dry-run` preview, because a second apply mints a second row for the same `add`.
- `page_lint.py` reads the pages it is given and the register and writes nothing; it checks the page contract — the stamp, the section set and order, the anchors against the register's owners, the rule-line shape, the closing `Not covered:` line, the narrative markers, the prose cap, the worked-example paths and the links — or, on this page and `datasets.md`, the reference profile's stamp, anchors, links and narrative markers only, exits `1` on a finding, and runs before every commit that touches `docs/areas`, `docs/platform` or `docs/facts`, with `--partial` while a linked page is unwritten, and under `--allow-provisional` admits a provisional tag on a rule or key-fact line.
- `bus_inventory.py`, the bus inventory generator, renders the harness command reference `docs/reference/harness-commands.md` from a three-part comment block (`-- @args`, `-- @reply`, `-- @purpose`) above each `TK.register` site, one row per site and side, and a site missing any of the three fails the run and is listed on standard error; its check mode `--check` exits 1 when the file on disk is not a fresh render, and a harness commit that adds or changes a command edits the block and regenerates in the same commit [#1961].
- `luabalance.py`, the Lua balance tool, strips comments and strings and then prints the bracket deltas, the block-end depth and the count of lines where the depth went negative, exiting 1 unless every file balances; it is run on every Lua file a harness commit touches, on the committed copy first and then the working tree [#1960].

### The register grammar

- A register row is one tab-separated line whose columns are, in order, `id`, `claim`, `grade`, `pointer`, `bound`, `status`, `successor`, `kind`, `source` and `owner`.
- An `id` is `#` and four digits, and a page task that needs a row the register lacks writes a provisional id `T<task>.<n>` that the delta applier replaces.
- The `grade` is `C` for a read of code, the jar or a file, `M` for a measurement with a committed artifact, and `W` for a wiki or web page, which is corroboration only.
- The `status` is `settled`, `open`, `unverified` or `superseded`, and a superseded row names its successor and is never tagged on a page.
- The `bound` cell opens with a controlled token — `none`, `n=<count>`, `one-side`, `C-only`, `one-fixture`, `arith.`, `inference`, `uncommitted` or `snapshot` — and the rest of the cell states the restriction in words; an `inference` bound is never graded `M`.
- The `owner` is `<layer>/<page>.md#<anchor>`, and the owner page carries the row's tag at that anchor.
- A tag is the id in brackets followed by a suffix written from the row — the grade, then the bound token unless it is `none`, then the status unless it is `settled` — so a measurement on one run carries `/M/n=1` and an open code read with a snapshot bound carries `/C/snapshot/open`; the exception is a settled `C` row with no bound, which carries no suffix at all.
- A pointer cell holds one or more pointers, each `<form>:<payload>`, separated by `;` wherever the `;` is not inside quoted anchor text, and a row's grade is the strongest grade among its pointers' forms, `M` over `C` over `W`.
- `jar:<Class>.<method> @<offset>[-@<offset>] L<line>[-L<line>]` is a read of the decompiled game jar and grades `C`.
- `run:<run-id> <artifact file> <key>` is a measured reading and grades `M`: the run's folder exists under `testing/artifacts/` or is aliased in `docs/reference/run-aliases.csv`, and the key is neither listed in `docs/reference/do-not-cite.csv` nor a child of a listed key.
- A `run:` pointer to a run that left no artifact folder is admitted only on an `unverified` or `superseded` row whose bound opens `uncommitted: <run-id>`.
- `wiki:<mirror path> <fetch date or page version>` is a wiki mirror and grades `W`, with no anchor text.
- `web:<data file or page> <fetch date>` is a fetched source that is not the wiki, such as a Workshop metadata snapshot or a licence page, and grades `W`, with no anchor text.
- `lua:<path>:<line>[-<line>] "<anchor text>"` is a file of the game install named by its path relative to the install's `media/` directory, so a Lua file reads `lua:lua/shared/…` and a script reads `lua:scripts/generated/…`, and it grades `C`.
- `mod:<workshop id>/mods/<ModName>/<tree>/<path>:<line> "<anchor>"` is an installed workshop mod's file as it lies on disk under the workshop root, `<tree>` being the version folder or `common` the file sits in, and it grades `C`; a file at the mod root, such as a `HowTo.txt` beside `mods/`, omits the `<tree>` segment.
- `repo:<path>:<line> "<anchor text>"` is a file in this repository and grades `C`: the path exists and names none of the pre-restructure docs (readable at the tag `research-program-v1`).
- `tool:<path>:<line>` is a tool's own code at a line, in this repository or in the jar toolchain (`pz-b42/`), and grades `C`, with no anchor text.
- `data:<what was read> <date>` is a scan whose output is the evidence and grades `C`, in one of the four readings below.
- The anchor text of a `lua:`, `mod:` or `repo:` pointer is a quoted fragment of the cited line, so a cite whose line number drifts is re-located by content, and a `;` inside the quotes never splits the cell.
- A path with a space in it is written with `%20` for each space, because the path of an anchored pointer runs to the first whitespace: `mod:2503622437/mods/Skill%20Recovery%20Journal/42.20.1/media/lua/shared/…`.
- The first reading of `data:` is a committed dataset with the date of the scan that wrote it, such as `data:data/mod-inventory.json swept 2026-09-10 17:47`.
- The second reading of `data:` is a read of the read-only install's corpus, which keeps its `media/` prefix where a `lua:` path drops it, such as `data:media/scripts/generated/fluids.txt 2026-09-10`, or of the jar as a file, `data:projectzomboid.jar 2026-09-10`.
- The third reading of `data:` is a tool sweep whose output was not committed, written `data:tools/<tool>.py <what was swept>, <date>`, which cannot be re-read, so a claim that rests on it is `unverified`.
- The fourth reading of `data:` is a hand scan of the read-only install, written `data:media/<dir> grep <literal>, <date>`, or of the read-only workshop tree, written `data:workshop/content/108600 grep <literal>, <date>`, one pointer per literal; neither can be re-read, so a claim that rests on one is `unverified` and its bound opens `snapshot <date>;`.

<a id="conventions"></a>
## Conventions

Every tool here is standard-library-only Python in the same parser style as the jar toolchain's own scanners, which were proven against the generated-script grammar including capitalised script directories and version-folder resolution [#1962].
Each command-line tool runs from the repository root as `python tools/<name>.py`, takes its targets, where it has any, as positional arguments and its options as long flags, and prints its findings or its census to standard output; the claims harvest and delta tools take a subcommand first, and `claimslib.py` has no command line.
A lint exits `1` when a finding fired and `0` otherwise, and a warning never fails a run; `mod_lint.py` fails on an error only, never on a warning or an informational finding.
A scanner writes its datasets under `data/`, a generator writes under `docs/reference/`, and `wiki_mirror.py` writes under `references/wiki-mirrors/`; the game install and the workshop tree are read and never written.
A count read off a live tree — the workshop corpus or the public Workshop — is quoted with the date of the sweep that produced it and never with the day it is quoted, and a count read off the install's scripts carries the build it was read from.
A module's docstring is the reference for its own internals, and `tools/README.md` gives each tool's command line and outputs.
The tools' tests live in `tools/tests/` and run with `python -m pytest tools/tests -q`.

## Open
<a id="open"></a>

- Whether the recipe scanner should widen its output-mapper rule to take a `default` as a type — with one vanilla case today, a mod shipping a mapper with only a `default` would have its outputs silently resolve to nothing, and the vanilla data does not force the decision — settled by scanning a mod that ships such a mapper and reading what `meta.outputMapperIssues` records for it [#0783/C/snapshot/open].
- That the lint sweep reproduced at 04:27 on 2026-09-11 reads 84 findings — 3 errors, 30 warnings and 51 informational — across 230 mods, of which 51 are folder-name findings, 24 media findings, 6 `mod.info`-placement findings and 3 errors on two known mods, is unverified: the sweep output was not committed, and a workshop change twenty minutes later moved the corpus; re-measure by re-running the sweep and committing its output with its date [#0865/C/snapshot/unverified].
- That the corpus sweep of 2026-09-10 13:47 found, by rule, no version-directory findings over 230 folders, two errors on the one mod with no mod-info file anywhere, one agreement error on a mod declaring two different ids across three files all in the resolution chain, no drift findings, six placement warnings, 24 media warnings on mods shipping their content only in the common folder, no dynamic-compiler findings and 51 informational folder-name findings, is unverified: the sweep output was not committed; re-measure by re-running the sweep and committing its output with its date [#1839/C/snapshot/unverified].
