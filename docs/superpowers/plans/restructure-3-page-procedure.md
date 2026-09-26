# The Phase 3 page procedure — binding for every page, skill and root task of `restructure-3-areas-skills-roots.md`

The Phase 2 procedure `restructure-2-page-procedure.md` applies to every Phase 3 page task exactly as written (inputs, the page shape, the sentence rules, walls and open, deltas, validation, commit, report), with the amendments below. Where this file and the Phase 2 procedure disagree, this file wins; where either disagrees with the spec `docs/superpowers/specs/2026-09-17-reference-restructure-design.md`, the spec wins. Rulings R1–R16 of the Phase 2 ledger bind here too; the ones a writer meets are restated where they apply.

## A1. Workspace and names

- The SDD workspace is `.superpowers/sdd/restructure-3-areas-skills-roots/`; a task's delta file is `task-<N>-delta.tsv` and its report `task-<N>-report.md` there. Provisional ids are `T<task>.<n>` (`T5.1`, `T5.2`, …) — the applier recognises no other shape.
- The stamp date is the day the page is written.
- Commits: `Page: areas/<page>` for an area page; `Reference: <page>` for `reference/datasets.md` and `reference/tools.md`; `Skills: the ten project skills`; `Roots: README and STRATEGY`; `CLAUDE.md: rewrite`. Pathspec, never `--amend`, no push, no attribution line, no other file.
- A writer never runs `claims_check.py --fix-tags` (R8): every suffix is written by hand from the register row (`[#0417/M/n=1]`, `[#0417/C/open]`, nothing for a settled C row with no bound) and rule 2 reports the stale ones. The controller runs `--fix-tags` once at each wave close.

## A2. Inputs for an area page

- **Your rows:** `python tools/claims_check.py --view areas/<page>.md` — one to eight rows; every one is tagged at its anchor. The page is a reading of the two layers below, so most of what it cites is owned elsewhere.
- **The rows you cite:** `python tools/claims_check.py --view platform/<page>.md` and `--view facts/<page>.md` for the pages your anchor-plan section names; `python tools/claims_check.py --view reference/wall-map.md` for the wall map's `verdict` rows (the register id is the citation; the map's row letter never appears on the page — R-Phase 2 § 4); `python tools/claims_check.py --view areas/open-questions.md` for the open rows that carry an `X` id.
- **The Phase 2 pages themselves** (`docs/platform/*.md`, `docs/facts/*.md`): read the pages you cite; link their anchors (`../platform/mp-model.md#packets`). The page lint checks every fragment against a real `<a id>`.
- **The old docs for the readings' shape** (they exist until Phase 4): `docs/modding/wall-map.md` (§ The map, § Named experiments, § What the library cannot yet measure), `docs/modding/patterns.md` (§ KEEP, § FILTER OUT), `docs/modding/item-overrides.md`, `docs/modding/anatomy.md`, `docs/modding/lua-api.md`, `docs/mods-survey/teardowns/*.md`, `docs/testing/profiles.md`, `docs/testing/README.md`; the slice-14 inputs `.superpowers/sdd/14-feasibility-notes/stale-cold-start.md` and `slice-13-bounds.md` (gitignored; read them, never cite them — a `source` cell names a tracked doc).
- **The experiments:** `docs/reference/experiments.md` § Named experiments holds every `X<N>` spec; `areas/open-questions.md#x<n>` is the page anchor an `X` id links to (it may not exist yet — link it anyway under `--partial`).

## A3. `## Rules` on an area page (10–20 lines)

Every line is `- <imperative>: <the one-clause reason — the mechanism, never the history> [#tags].` and comes from one of three places:

1. **A copy of a `platform/` page's rule line, byte-identical, tags included.** The spec's cross-page rule: a rule that belongs to two areas appears on both pages only as the byte-identical line with the same tags; the checker's `rules-dup` rule groups `## Rules` lines under `docs/areas` and `docs/platform` by their tag-id set and fails any two that differ. Copy the line with the Read tool's exact text; never paraphrase.
2. **A `rule` row the register already owns to your page** (`--view areas/<page>.md`), stated with its bound where the bound carries the safety ("a client can derive a weight direction, never a weight").
3. **An `add` delta of `kind` `rule`** for an imperative the area needs that no page states. A rule row rests on the register rows its reason cites and mints no measurement: its `pointer` is copied from the strongest row it rests on, its `grade` follows that pointer's form, its `bound` reads `inference; a reading of <the ids it rests on>` (the shape of `#0128`), its `source` is the old doc that states the reading (`docs/modding/wall-map.md § <section>`, `docs/modding/patterns.md § KEEP`, …) or, where none does, `docs/areas/<page>.md § Rules`; its `owner` is your page's `#rules`-bearing section — write `areas/<page>.md#<the anchor whose reading the rule closes>` (a page has no `#rules` anchor; the imperative sits in `## Rules` and the row's owner names the How-it-works or options anchor it belongs to, as the harness page does). The tag on the rule line is the provisional id until the controller mints.

At most half the lines are new `add` rows; prefer a copy where a platform page already says it. A rule that two area pages both need is written once, on the first page committed, and copied byte-identically onto the second (the controller resolves a race by ruling).

## A4. `## Options` (areas only)

One table, columns exactly `| option | what it costs | which wall it hits | tags |`; one row per option the anchor-plan bullet names, in wall-map row order (the order of the verdict rows' map ids A1 … J5 as `docs/modding/wall-map.md` § The map lists them; an option no map row covers comes last); each row's `tags` cell cites a `verdict` row or a register id (`[#1674/W/snapshot]`); no row is marked preferred, recommended or chosen, in any wording; the table is followed by exactly one line, the decision the design must take, written as a question. A page whose anchor plan names two options tables (`new-nutrients`: `#store-options` and `#effect-paths`; `packaging`: `#compat-options` sits under `## Options`, the readings under `## How it works`) puts each table under its own `<a id>` + `###` inside `## Options`, in anchor-plan order. The section order is the contract's: `## Rules`, `## How it works`, `## Options`, `## Walls and bounds`, `## Open`, `## Worked examples` (optional), `## See also`; an options anchor therefore lives under `## Options` even where the anchor plan lists it first.

## A5. `## Walls and bounds` and `## Open` on an area page

- A wall line cites the `verdict` or mechanism row that closes it (`- No route registers a moodle from Lua: the registry gives a type and no rendering ([#0884/C], [lua-platform.md#registries](../platform/lua-platform.md#registries)).`) and restates no number. The four experiments the folded feasibility notes could not be written without are stated as walls on their pages, in the spec's words: X29 on `ui-and-moodles` ("no measured moodle route exists"), X4 on `new-nutrients` and `ui-and-moodles` ("the trait sync path is untraced"), X5 on `ui-and-moodles` (the translation override is unmeasured), X13 on `eat-and-cook-hooks` (the drink path's interceptability is unmeasured) — each citing the open row that carries the `X` id and linking `open-questions.md#x<n>`. The section ends with a `Not covered:` line.
- `## Open` holds one line per open row the area rests on (`- <the question> — settled by <the check>; -> X<N> ([#tag], [open-questions.md#x<n>](open-questions.md#x<n>))`), the `unverified` rows the page cites (R15/R16: an unverified row is never quoted as a fact; its line states the claim's numbers only where the page owns the row — an area page owns none, so it names the row and links its owner's `#open`), and the decisions the design must take that the page's rows force, each with the fact that forces it and no recommendation.

## A6. Numbers on an area page

An area page owns almost no numbers. A number belongs on its owner page; the area page links or cites (`the 1 Hz push ([#1191/M], [wire-packets.md#staircase](../facts/wire-packets.md#staircase))` restates the cadence because that sentence carries the tag whose row owns it — that is a citation, not a restatement; a bare "once a second" elsewhere on the page without the tag is a rule-4 warning and a restatement). Write readings in words; cite the row where the reader needs the figure. Rule 4's target is zero warnings, as in Phase 2.

## A7. `areas/open-questions.md`

The page is the open list; it carries neither `#walls` nor `#open`. Its shape:

```markdown
# Open questions
Verified against 42.20.4 (b0bbce05d5) · <date> · scope: <one line>

## Index
<a id="index"></a>
| id | question | owner | X | settled by |
|---|---|---|---|---|
| [#0783/C/open] | <the row's claim, verbatim> | [tools.md](../reference/tools.md#open) | — | <the check, one clause> |
…one line per `open` row in the register, every layer, ordered by id…

## Decisions
<a id="decisions"></a>
- <the decision, as the area page states it> — forced by <the fact> ([<page>.md#open](<page>.md#open)).
…one line per decision line on the seven area pages' `## Open`…

## Experiments
<a id="x2"></a>
### X2 — <the question, from reference/experiments.md>
- <each open row owned at #x2, one line, its claim stated with its numbers> [#tag].
- Settled by: <the check as a pointer: [experiments.md § X2](../reference/experiments.md#…)>.
…one subsection per anchor of the anchor plan, in its order…

## See also
```

The page lint's section list for this page is `Index`, `Decisions`, `Experiments`, `See also`; it checks that every `open` row in the register carries a tag somewhere on the page (`open-index`), and it applies no prose floor. The 11 `superseded` rows owned at `#x<n>` are not tagged (their successors are, on their owners); the subsection may say in one clause what the successor settled, citing the successor. The index cells carry full tags so rule 2 validates their suffixes. The page never restates an experiment spec: the `Settled by` line is a pointer into `reference/experiments.md`.

## A8. `reference/datasets.md` and `reference/tools.md`

Outside the page contract's section shape, but owners like any other page and tagged like any other page (rules 1 and 2 apply; rule 4 does not run under `docs/reference/`; the page lint's `reference` profile checks the stamp, the anchors against the register, the links and the narrative regex, and nothing else). Shape: line 1 the title, line 2 the stamp, then one `<a id="<anchor>">` + `## <heading>` per anchor of the page's anchor-plan section, in its order, `## Open` last with `<a id="open">`. `table` rows carry their table verbatim from the old doc (R10: minus `Ev`/`Cite`/`Evidence` columns and inline citations; R12: every other cell verbatim); `count` rows are dated in their own sentence; an `unverified` row is a `## Open` line stating its numbers (R16) and appears nowhere else; a `superseded` row is not tagged. Present tense, no narrative markers, names in code spans (R3), one sentence per line (R5). No prose cap and no floor. `tools.md#claims-tools` also states the register grammar in the tree (the Phase 1 obligation): the nine pointer forms including `web:`, the `%20` rule for a path with a space, the on-disk `mod:` form (`mod:<workshop id>/mods/<ModName>/<tree>/<path>:<line> "<anchor>"`), the `lua:` path relative to the game `media/` directory, and the three readings of `data:` (a committed dataset with a date; a read-only-install corpus read, which keeps its `media/` prefix; a tool sweep whose output was not committed, which is `unverified`) — as the tool's conventions, in words, without tags (they are the spec's rules, not claims).

## A9. Skills

`.claude/skills/<name>/SKILL.md`, ten of them, each at most 60 lines including the frontmatter:

```markdown
---
name: nutrition-mp-sync
description: <the trigger sentence: the concrete identifiers, file names and verbs the task would touch, key use case first; under 1,000 characters>
---
## Read first
- docs/areas/mp-sync.md
- docs/platform/mp-model.md
- docs/facts/wire-packets.md

## Rules quoted
- <a line copied verbatim, tag included, from the ## Rules of a Read-first page>
…at most eight…

## Also
- <two or three cross-page pointers, one line each>
```

`paths:` in the frontmatter only for `pz-mod-testing` (`paths: ["testing/**"]`). `## Read first` lists two to four existing pages as `docs/...` paths (the checker reads them by that path); `## Rules quoted` lines must be byte-identical to lines in those pages' `## Rules` (checker rule 6 fails otherwise), chosen for the hazards an agent meets before it reads. `pz-modding-platform` carries a `## Coverage` section quoting `platform/overview.md` § Coverage's opening four sentences verbatim, and its description says it does not fire on a nutrition task. A skill never states a number of its own and never duplicates a page.

## A10. The roots

`README.md`, `STRATEGY.md` and `CLAUDE.md` are outside the page contract and outside rule 4; they carry no register tags (a root file names pages, never claims) and no number except the build `42.20.4`, the jar hash and a count that is a link's label. Present tense; no program history (no slice numbers, no phase letters, no dates other than the stamp-style build line); every path they name exists at commit time (the Phase 4 move of `wall-map.md` and `artifacts.md` is named as "moves at the cut" in one clause, never linked as if present).

## A11. Gates before a commit

```bash
cd /c/Users/Angus/repos/project_zomboid
python tools/claims_check.py --partial --allow-provisional         # 0 findings; rule 4 warnings aimed at 0
python tools/page_lint.py docs/<layer>/<page>.md --partial         # 0 findings (areas, and the two reference pages under the reference profile)
grep -nP '\b(previously|corrected 20|resolved (in|by) slice|RESOLVED 20|CONTESTED|the review found|this slice)(?![A-Za-z])' <the file>   # nothing
```

For a skill task: `python tools/claims_check.py --partial` (rule 6) and `wc -l .claude/skills/*/SKILL.md` (every file ≤ 60). For a root task: the grep, and `python -X utf8 - <<EOF` link check the task text gives. For `CLAUDE.md`: additionally `python tools/doc_lint.py docs/mods-survey docs/modding` and the second doc_lint line still pass (they read nothing in `CLAUDE.md`, but the close runs them).

## A12. Report

As Phase 2 § 9, plus for an area page: the rule lines by source (copied / owned / added), each copied line's source page; for `open-questions.md`: the index row count against `grep -c` of open rows in the register; for the skills: the description length per skill and the quoted-rule count per skill; for the roots: the list of paths named and the check that each exists.
