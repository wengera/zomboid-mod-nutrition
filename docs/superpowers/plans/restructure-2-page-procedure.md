# The page procedure — binding for every page task of `restructure-2-platform-facts.md`

Every page task (Tasks 3–23 of the plan) follows this procedure exactly. The task text names only what is particular to the page: its rows, anchors, sources, worked-example candidates, length cap and special rules. The spec is `docs/superpowers/specs/2026-09-17-reference-restructure-design.md` (§ The page contract, § The claims register "Deltas in Phases 2 and 3", the "Tag grammar" paragraph, the "Writing rules" paragraph, the placement rules under § The target tree); where this file and the spec disagree, the spec wins.

## 1. Inputs

- **Your rows:** `python tools/claims_check.py --view <layer>/<page>.md` prints every register row whose `owner` names your page, one TSV row per line in register column order (`id claim grade pointer bound status successor kind source owner`). A row's `owner` anchor is the section it belongs under. Superseded rows are yours too: they are not tagged on the page, but their successors are, and a superseded row's `claim` tells you what the page must no longer say.
- **The anchor plan:** your page's section of `docs/superpowers/plans/restructure-anchors.md` — the anchors, in order, with one line each on what goes there. An anchor with no rows still gets its heading and its prose (a reading of the rows around it, or of the mechanism the old doc states without a number), or a one-line "no measured row; see …" pointer; it never gets a number without a tag.
- **The old source docs** named in your rows' `source` cells (`docs/vanilla/…`, `docs/modding/…`, `docs/mods-survey/…`, `docs/testing/…`; they exist until Phase 4). Read them for the mechanism prose, the annotated code blocks and the tables. The register carries the claims; the old doc carries the shape.
- **The register grammar:** `tools/claimslib.py` (`canonical_suffix`, `TAG_RX`, `BLOCKS`); the tag grammar is spec § The checker and the generator, "Tag grammar".
- **Neighbours:** `docs/reference/wall-map.md` does not exist yet — the wall map is still `docs/modding/wall-map.md`; a `verdict` row you cite is a register id, never a row letter. `docs/reference/experiments.md` § Named experiments holds every `X<N>`. Pages written in parallel with yours may not exist yet: link them anyway (`../facts/wire-packets.md#desyncs`); the page lint's `--partial` mode skips a missing target.

## 2. Outputs

- `docs/<layer>/<page>.md` — the page, LF, UTF-8, under the contract below.
- `.superpowers/sdd/restructure-2-platform-facts/task-<N>-delta.tsv` — your delta file (§ 6), only if you need one. You never edit `docs/reference/claims.tsv`.
- `.superpowers/sdd/restructure-2-platform-facts/task-<N>-report.md` — the report (§ 9).

## 3. The page shape

```markdown
# <Title>
Verified against 42.20.4 (b0bbce05d5) · 2026-09-22 · scope: <one line: what this page owns and what it hands off>

## Rules                    platform/ only — see § 4
## Key facts                facts/ only — see § 4
## How it works             the anchors of the anchor plan, in its order, each as an <a id> + ### heading
## Walls and bounds         see § 5; ends with a line starting "Not covered:"
## Open                     see § 5
## Worked examples          platform/ pages with code shapes (the task says which); optional elsewhere
## Procedure                harness.md and jar-research.md only
## See also                 the pages this one rests on or hands off to, one line each
```

- The stamp is line 2 exactly in that shape; the date is the day you write it.
- **Anchors.** Every anchor of your page's anchor-plan section, in the plan's order, is a subsection under the section that owns it: an HTML anchor line, then a `###` heading, then the prose:

  ```markdown
  <a id="per-key-merge"></a>
  ### The per-key merge
  ```

  `#walls` is the `## Walls and bounds` section itself and `#open` is `## Open` (put the `<a id>` line directly under the `##` heading); `#sandbox` is a `###` under How it works holding the page's sandbox-option table; `#procedure` is the `## Procedure` section. Every register row owned by your page has its anchor present (the page lint checks this from the register), and no anchor appears twice.
- **Sections.** The order above is fixed. `platform/` pages carry `## Rules`; `facts/` pages carry `## Key facts` instead and no `## Rules`. `platform/overview.md` carries `## Coverage` in place of `## Walls and bounds`. The `facts/other-mods/` pages map their anchors into the contract: `#what-it-does`, `#architecture`, `#data-model`, `#mp` under `## How it works`; `#techniques` is `## Key facts` (one tagged line per technique); `#pitfalls` and `#compat` under `## Walls and bounds`; `#open` is `## Open`. `catalog.md`: `#sweep`, `#status`, `#api-surface`, `#corpus-facts` under `## How it works`.

## 4. Writing the sentences

- **A tag** is `[#0417]` typed by you; `python tools/claims_check.py --fix-tags` appends the canonical suffix (`[#0417/M/n=1]`, `[#0417/C/open]` …). Several ids in one bracket: `[#0417, #0512]`. A tag closes the sentence (or the table caption, or the code-block caption) that states the row's claim. No other citation form appears on the page: no run ids in prose unless the sentence also carries a tag whose pointer names that run; no `@offsets`; no doc names; no dates except the stamp and a dated count's own date.
- **A rule line** (`## Rules`): `- <imperative>: <the one-clause reason — the mechanism, never the history> [#tags].` A rule whose safety depends on its bound carries the bound in the line. Ten to twenty lines.
- **A key-fact line** (`## Key facts`): `- <declarative sentence with its numbers and units> [#tags].` Eight to fifteen lines, the page's load-bearing numbers.
- **The number lives on the owner page.** A row owned by your page is stated with its number here, tagged. A row owned by another page is cited by tag or linked (`the 1 Hz staircase ([#1191/M], facts/wire-packets.md#staircase)`) and its number is not repeated. A row owned by your page under a different anchor is stated once, at its anchor; other anchors refer to it.
- **Bounds as facts.** State the register's bound in words where the reader needs it ("measured on the dedicated-server path only"; "read from the code, not measured" for an `inference` bound). Never as a caveat about the process.
- **Present tense, current truth only.** No "previously", "corrected", "resolved in", "the review found", "this slice", "RESOLVED", "CONTESTED" (the narrative regex fails the page); no session narratives (a run is cited by its tag, never described); no history of how a claim was found.
- **Tables** (a `table` row): the table verbatim from the old doc, its caption tagged once; the row's claim (what the table is, its count and date) is the caption sentence. Numbers inside a tagged table carry no tags of their own. A dataset-shaped table with per-food or per-recipe values does not enter the page — the dataset is the pointer.
- **Annotated code blocks** (an `order` row): the block verbatim from the old doc under a caption tagged once; the inline offsets inside it are the pointer and are not re-tagged.
- **A `verdict` row** (a wall-map row) is cited by its register id from `## Walls and bounds` or from the prose; the map's row letter never appears.
- **Names are not numbers.** A version or build number (`42.20.4`), a run id (`x121-20260911-030023`), an artifact key path, a jar offset, a workshop id or any identifier goes in a code span; rule 4 strips code spans before its digit test, so these never need a tag and never count as untagged numbers.
- **Every number outside a code block and a tagged table carries a tag** (rule 4 warns on a digit without a tag; the page lint counts the warnings; the target is zero — a number that has no row is a delta, not an untagged sentence, and a number that is a version, a line count of your own page or a heading level is rewritten in words).
- **One sentence per line.** Prose paragraphs are written one sentence per physical line (a paragraph is consecutive sentence lines; a blank line separates paragraphs). The tag then closes its own line, a diff shows one claim per hunk, and the page lint's prose count means what the spec's cap means.
- **Length.** 150–400 lines of prose (the task says 500 where the spec allows) counted as sentence lines; tagged tables, index rows under `## Open`, code blocks, anchor lines and headings do not count. The page lint prints the count.

## 5. `## Walls and bounds` and `## Open`

- `## Walls and bounds` holds, as one line each: every `bound` row owned by your page (the restriction as a fact, tagged); every `contradiction` row (`The mirror says <its words>; the code does <the claim> [#tag]` — the row's bound carries the mirror's words); every wall the anchor plan names for the page, citing the `verdict` row's id; and, last, one line beginning `Not covered:` naming the adjacent surface the library never read (from the spec § Coverage and the old doc's own boundary statements).
- `## Open` holds one line per `open` row owned by the page (`- <the question> — settled by <the check>; -> X<N> [#tag]`), one line per `unverified` row (`- <the claim> is unverified: <the bound's reason>; re-measure by <the check> [#tag]`), and the decisions the design must take that the page's rows force, each with the fact that forces it and no recommendation. An `unverified` row is never quoted as a fact anywhere else on the page.

## 6. Deltas — when the register does not fit the page

You never edit the register. Where a sentence needs a row the register lacks, or a row's owner, status or grain is wrong for the page, write the sentence with a **provisional tag** `[T<task>.<n>]` (`n` counting from 1, unique within your task) and file the row in `task-<N>-delta.tsv` (tab-separated, header line, one delta per line):

```
op	id	claim	grade	pointer	bound	status	successor	kind	source	owner	reason
add	T7.1	<one sentence>	C	jar:…	none	settled		mechanism	docs/vanilla/x.md § Y	facts/x.md#anchor	<why the register lacks it>
retarget	#0417									facts/x.md#other	<why this anchor, not the old one>
status	#0512				uncommitted: x121-20260911-030023; <the restriction>	unverified					<why unverified, not settled>
split	#0600										<why two claims>
add	T7.2	<child one>	C	jar:…	none	settled		mechanism	docs/vanilla/x.md § Y	facts/x.md#anchor	split of #0600
add	T7.3	<child two>	C	jar:…	none	settled		mechanism	docs/vanilla/x.md § Y	facts/x.md#anchor	split of #0600
```

- `add`: a claim the register lacks — only a claim the old doc states with evidence (a pointer you re-located); the restructure mints no new measurements. The controller mints the next free id and rewrites your `[T7.1]` to it.
- `retarget`: a row whose right anchor is another anchor of your page, or another page (say which page and why; a cross-page retarget is the controller's call).
- `status`: `settled -> open` (the old doc marks it unsettled and the harvest did not), `settled -> unverified` (its only evidence is restricted). The new `bound` goes in the `bound` column (an `unverified` row citing an artifact-less run needs a bound starting `uncommitted: <run-id>`, or the pointer rule fails); `reason` carries the why. Every line has exactly twelve cells — a tab for every empty column.
- `split`: one row that states two falsifiable claims; the parent goes `superseded` with the two `add` lines as successors; on the page you tag the children's provisional ids.
- The controller applies the delta with `python tools/claims_delta.py apply <delta> --pages docs/<layer>/<page>.md` in a `Register: task N delta` commit before your review; the reviewer sees real tags. Until then your local checks run with `--allow-provisional`. A delta never names a row that is already `superseded` (the tool refuses it); a `retarget` to another page is applied only if the controller agrees, so say why in `reason`.

## 7. Validate before you commit

```bash
cd /c/Users/Angus/repos/project_zomboid
python tools/claims_check.py --partial --allow-provisional     # 0 findings (warnings are rule 4: aim for 0)
# never run --fix-tags: it rewrites every tagged file in the tree and races the writers beside you; write each suffix by hand from --view (grade, bound token, status: [#0417/M/n=1], [#0417/C/open]; nothing for a settled C row with no bound) and let rule 2 tell you which one is stale
python tools/page_lint.py docs/<layer>/<page>.md --partial     # 0 findings; note the prose count it prints
```

Rule 1 fails when a row owned by your page is not tagged on it; rule 2 fails on a tag the register lacks or a stale suffix (fix the suffix by hand; the controller runs `--fix-tags` once at the wave close); a link to a page a later phase writes (`../areas/…`, `../reference/wall-map.md`, `../reference/datasets.md`, `../reference/tools.md`) is allowed — `--partial` skips it now and the Phase 4 close resolves it; the page lint fails on a missing section, a wrong section order, a missing anchor, a `## Rules` or `## Key facts` line without a tag, a `## Walls and bounds` without a closing `Not covered:` line, a narrative marker, a prose count over the cap, a `## Worked examples` path that does not exist, or a link whose target page or anchor is missing. Fix every finding; never commit with one. `python -m pytest tools/tests -q` is not needed for a page (no code).

## 8. Commit

One pathspec commit for the page: `git add docs/<layer>/<page>.md && git commit -m "Page: <layer>/<page>" -- docs/<layer>/<page>.md`. Never `--amend`. No push. No other file changes: not the register, not the anchor plan, not an old doc, not a driver or a probe mod, not another page. The delta file and the report live in the SDD workspace (gitignored).

## 9. Report

`task-<N>-report.md`: rows owned (count) and tagged (count, must be equal after deltas); rows cited from other pages (ids); deltas filed (each line's op, id and reason); the prose line count and the rule-4 warning count; the anchors that have no rows and what you wrote under them; the ten sentences you are least sure of, each with its tag and why; concerns. Return to the controller only: status, the commit, the one-line count (`<page>: N rows tagged, M prose lines, K deltas`), concerns.

## 10. What the reviewer checks (so you know the bar)

A fresh reviewer runs the same three commands and then reads the page against `--view`: every owned row tagged at its anchor and stated faithfully (the sentence says what the claim says, with the row's numbers and its bound where it matters); no number without a tag; no number restated from another page's row; every table and code block verbatim against the old doc; every wall and open row present; the section order and the anchors against the anchor plan; the narrative regex clean; each delta justified (an `add` has re-locatable evidence; a `retarget` names a real anchor; a `status` change matches the old doc); the prose within the cap; the `## Worked examples` paths real and the shapes they claim to show present at those lines; the writing rules of spec § The page contract.
