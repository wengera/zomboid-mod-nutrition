# The harvest procedure — binding for every harvest task of `restructure-1-register.md`

Every harvest task (Tasks 11–20 of the plan) follows this procedure exactly. The task text names only what is particular to it: its source files, its id sub-block, its part-file names, its special rules and its expected row count. The spec is `docs/superpowers/specs/2026-09-17-reference-restructure-design.md` § The claims register; where this file and the spec disagree, the spec wins.

## 1. Inputs

- The candidates file for your group, generated in your first step: `python tools/claims_harvest.py candidates <your source files> --out .superpowers/sdd/restructure-1-register/candidates-<group>.tsv`. One row per evidence-table row and per graded paragraph, with `source`, `line`, `section`, `kind_hint`, `cells`, `ev`, `grades`, `run_ids`. It is a checklist, not the output: every candidate must end up in your coverage part as harvested, superseded, dropped or unverified.
- The source files themselves. Read them in full; the candidate rows carry the cells, not the prose around them, and the prose carries the bounds.
- The anchor plan `docs/superpowers/plans/restructure-anchors.md`: every `owner` you write is `page#anchor` from it. An anchor it lacks is written as `page#<new-slug>` and listed under `## Anchors proposed` in your coverage part; the merge task folds them into the anchor plan.
- The schema and grammars in `tools/claimslib.py` (read the constants at its top: `COLUMNS`, `KINDS`, `STATUSES`, `BOUND_TOKENS`, `POINTER_FORMS`, `BLOCKS`).
- `docs/reference/run-aliases.csv` and `docs/reference/do-not-cite.csv` (the checker reads them for rule 3).

## 2. Outputs

- `docs/reference/parts/claims-<group>.tsv`: the register header line, then your rows, ids ascending, contiguous from your sub-block's first id. Tab-separated, no quoting, LF, UTF-8. A tab or newline never appears inside a cell.
- `docs/reference/parts/coverage-<group>.md`: for each source file, one `### <file>` heading, then one line per section in reading order: `- § <section> — candidates N → rows #0101–#0117, #0120; superseded: #0118 (-> #0119); dropped: 2 (<reason each>); unverified: #0121`. Then `## Anchors proposed` (a list of `page#slug — one line on what goes there`) and `## Totals` (rows by kind, by grade, by status). This file is the `old section -> ids` map the wall-map rewrite and the Phase 2 writers use, so every section that had a candidate appears, even with `rows: none (why)`.

## 3. The grain rule (from the spec, restated as the test you apply to every candidate)

A row is the smallest sentence one measurement or one dump could falsify, carrying one grade and the pointers that establish that sentence.

- **Split** when two numbers rest on different pointers, different sides or different bounds. A cell graded `M (runs exp01…, exp03…)` that states two readings is two rows. A wall-map row is one `verdict` row plus one `mechanism` or `bound` row per fact its cells state that no other source carries, plus one `open` row per `-> X<N>` it names.
- **Keep together** when several numbers are one reading off one artifact key or one dump: the five clamp numbers of one setter family, the three arms of one run's matrix read from one key.
- **Collapse** a dataset-shaped table (a key list, a field list, a census, a schema, a sample table with uniform column meaning) into one `table` row whose claim states what the table is, its row count and its date, plus one row per exception the prose singles out. The page will carry the table verbatim under that one tag. The 114 script keys, the 31 craft deltas, the 30-row simpleStatus band table, the 26-row experiment table are `table` rows.
- **Per-food and per-recipe values never enter the register.** The dataset is the pointer. A row exists only where a page states the value as an example, a control or a measured subject (the apple's 95 kcal as the worked example is a row; the other 1,004 foods are not).
- A `C+M` cell is one row with two pointers. A `W vs C` or `W + C` cell is one `contradiction` row (claim = the code-side fact; a `wiki:` pointer for the mirror; bound `mirror wrong: <the mirror's words>`; owner = the facts page's `#walls` anchor). `C (arith.)` is a row with bound `arith.`. An inference ("the consequence is our reasoning, not measured") is a `C` row with bound `inference`, never `M`.
- A KEEP/FILTER entry or a rule stated in the source is a `rule` row whose pointer(s) are the mechanism rows' pointers it rests on.
- A code block whose claim is an order of operations (the `Eat` transcript, the five-branch burn, the aging formula, the cook block) is one `order` row: claim = what the order establishes in one sentence; pointer = the block's site range; the page keeps the block verbatim under that tag.
- Narrative is not harvested: how a claim was found, reviewed, previously stated or corrected. A dated-correction site ("corrected 2026-09-10", "RESOLVED", "CONTESTED", "re-scoped") becomes a `superseded` row (the old statement, its old pointer, `successor` = the id of the current statement's row) — the old statement is a row so the tag history survives.

## 4. Writing a row

- `id`: the next id in your sub-block. Never skip. If you run out, stop, write the rows you have, and report `BLOCKED: sub-block exhausted at #NNNN with K candidates left`; the controller assigns a continuation range.
- `claim`: one sentence, present tense, numbers and units included, no citation text inside it (no run ids, no `@offsets`, no "measured in slice 03"). It must be true on its own when read beside the bound. Write the mechanism, never the story.
- `grade`: the strongest grade among your pointers (`M` > `C` > `W`).
- `pointer`: convert the source's evidence cell. `Class.method @off L<n>` → `jar:Class.method @off L<n>`. A run id with a key → `run:<run-id> <file> <json.key.path>`; the file is the JSON under `testing/artifacts/<run-id>/` (when the run has one JSON, that one; the key path as the doc writes it). A wiki mirror → `wiki:<mirror file> <page version or fetch date>`. A vanilla Lua or script line → `lua:<path under media/>:<line> "<anchor text>"` with the quoted text you re-located. A workshop mod file → `mod:<workshop id>/<tree>/<path>:<line> "<anchor text>"`. Harness code, drivers, tests → `repo:<path>:<line> "<anchor text>"`. A dataset or corpus read → `data:<file> <sweep or fetch stamp>`. A behaviour of the disassembler or a tool → `tool:<repo>/<path>:<line>`. Several pointers: `; `-separated. A pointer you cannot re-locate is written as the source wrote it and the row goes `unverified`.
- `bound`: the controlled first token (`none`, `n=1`/`n=2`…, `one-side`, `C-only`, `one-fixture`, `arith.`, `inference`, `uncommitted: <run-id>`, `snapshot <date>`), then free text with everything the source states as a limit: side, fixture, build, the do-not-cite reading restriction quoted. A bound the source states and you drop is a defect.
- `status`: `settled` by default; `open` for an open question or a wall-map `UNKNOWN`; `superseded` for a dated-correction site's old statement (with `successor`); `unverified` for a claim the source marks not re-verified, or whose only run has no artifact folder (then `bound` starts `uncommitted: <run-id>`).
- `successor`: only when `status = superseded`; one id, or two for a split.
- `kind`: from the vocabulary; `mechanism` is the default for a fact about the game.
- `source`: `<file> § <section>`; several `; `-separated when the same claim appears in several places (one row, several sources — do not write the duplicate as a second row).
- `owner`: `page#anchor` from the anchor plan, by the placement rule: `platform/` if the mechanism would hold for a weapon or UI mod; `facts/` if a measured property of the food, body or nutrition systems; `areas/` only as a nutrition-design reading; `reference/wall-map.md#<row>` for a wall-map `verdict` row.

## 5. Validate before you commit

```bash
cd /c/Users/Angus/repos/project_zomboid
python tools/claims_check.py --register docs/reference/parts/claims-<group>.tsv --register-only
```

Expected: `0 findings`. It checks the header, every column's grammar, id uniqueness and contiguity within your sub-block, pointer forms and anchor text, grade = strongest pointer, `successor` consistency, and rule 3 on every `run:` pointer (the run folder exists or is aliased; the key is not in `do-not-cite.csv`). Fix every finding; never commit with one.

Then: `python -m pytest tools/tests -q` still green.

## 6. Commit

One pathspec commit for the two part files: `git commit -m "Harvest: <group>" -- docs/reference/parts/claims-<group>.tsv docs/reference/parts/coverage-<group>.md`. Never `--amend`. No push. No other file changes — the anchor plan, the register and other groups' parts are not yours.

## 7. Report

`task-N-report.md` in the SDD workspace: rows written by kind, grade and status; candidates accounted for (harvested / collapsed into / superseded / dropped / unverified, with counts that sum to the candidate count); anchors proposed; the ten rows you are least sure of, each with why; concerns. Return to the controller only: status, the commit, the one-line count, concerns.

## 8. What the reviewer checks (so you know the bar)

A fresh reviewer samples at least one in ten rows per kind against the source lines, and every `superseded`, `unverified` and `contradiction` row: the claim is true as stated, the numbers match the source, the pointer is the source's evidence converted correctly, the bound carries every limit the source states, the kind and owner follow the rules above, the grain rule was applied (no bundled cell left as one row; no dataset table exploded into rows), no narrative in any claim, and the coverage part accounts for every candidate.
