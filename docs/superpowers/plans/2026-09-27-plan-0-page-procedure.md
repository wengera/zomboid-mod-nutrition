# The page procedure — binding for every page task of `2026-09-28-plan-0a-claims-pass.md` (Part A) and every harvest task of `2026-09-28-plan-0b-science-register.md` (Part B)

Every page task (Plan 0a Tasks 5–27) follows Part A exactly; every harvest task (Plan 0b Tasks 2–15) follows Part B exactly. The task text names only what is particular to the task: its sources, the candidate lines it owns, its anchors, its supersessions and fan-out sentences, its cap and its special rules. The spec is `docs/superpowers/specs/2026-09-27-nutrition-mod-design.md` (§ 0, § 3, § 8, § 9); the page contract, the tag grammar and the writing rules are the restructure spec's (`docs/superpowers/specs/2026-09-17-reference-restructure-design.md`, readable at the parent of commit `9dfc74b`), as `tools/page_lint.py` and `tools/claims_check.py` enforce them today. Where this file and a spec disagree, the spec wins; where the tools and this file disagree, the tools win and the disagreement is a concern in the report. The dispatch-common file the controller names in your amendments carries the plan's § Global Constraints, the supersession fan-out table and the dataset stamps; read it with this file.

## Part A — page tasks

### A1. Inputs

- **Your candidate lines.** The task names one or more research reports under `docs/superpowers/research/` and, for each, the numbered lines of its `## Claims candidates` section (or the rows of its candidates table) that your task owns. Every owned line becomes exactly one `add` delta and one tagged sentence on your page, unless the task marks it `drop` (a duplicate of a register row or of another task's line, the survivor named) or `route` (another task owns it). A line the task does not mention is not yours; if you think it should be, say so in the report and leave it.
- **The report body.** The report's sections above `## Claims candidates` carry the mechanism prose, the decoded switches, the formulas and the tables. The candidate line is the claim; the body is the shape. Read the sections your lines cite.
- **The controller notes.** `docs/superpowers/research/_CONTROLLER-NOTES.md` N1 to N6 are candidate lines too, assigned to tasks by the plan bullet by bullet; each names the register rows it touches.
- **Your existing rows** (update tasks only). `python tools/claims_check.py --view <layer>/<page>.md` prints every register row whose `owner` names your page, one TSV row per line in register column order. A row's anchor is the section it belongs under. A superseded row is yours too: its successor is tagged, it is not, and its claim tells you what the page must no longer say.
- **The supersession fan-out.** The plan's table lists every row this plan supersedes or re-bounds, every page and line that tags it today, and the task that rewrites each sentence. **Never tag a parent from that table.** A sentence of yours that must refer to one links the successor's anchor with no tag, or cites a surviving sibling row (`#0183` for the recovery multipliers). A sentence on your page the table assigns to you is rewritten as the table says: to the successor's real id when the supersession landed in an earlier wave, to a tagless link to the successor's anchor when it lands in your wave or later. A sentence the table assigns to a later task keeps the parent's tag, which gains `/superseded` at the wave close and is listed until that task rewrites it.
- **The register grammar.** `tools/claimslib.py` (`COLUMNS`, `KINDS`, `STATUSES`, `BOUND_TOKENS`, `POINTER_FORMS`, `canonical_suffix`, `TAG_RX`) and `docs/reference/tools.md` § The register grammar (four `data:` readings after Plan 0a Task 1). Read both before you write a pointer.
- **The dataset stamps.** The dispatch-common file's `## The dataset stamp` block names the inventory file (`data/mod-inventory-2026-09-28.json`), its stamp, its counts and the fourteen surfaces it records, and after Plan 0a Task 15 the Workshop details snapshot and the ids it fetched; every `data:` and `web:` pointer of yours copies its file and stamp from there.
- **Neighbours.** Pages written in parallel with yours may not exist yet or may not yet carry the row you want to lean on: link them by anchor (`../facts/perks-and-strength.md#xp-grants`, or `../../facts/…` from a `facts/other-mods/` page) and never tag a row another task of your wave is minting (§ A4). The page lint's `--partial` mode skips a missing target. `docs/reference/experiments.md` § Named experiments and `docs/areas/open-questions.md` § Experiments hold every `X<N>` including the ones Plan 0a Tasks 3 and 4 minted, so an `-> X<N>` you write resolves and its open row has a real id you cite.

### A2. Outputs

- `docs/<layer>/<page>.md` — the page (new or updated), LF, UTF-8, under the contract (§ A3).
- Any second file the task names (a platform page gaining one anchor's rows, a skill file, a dataset), edited only where the task says.
- `.superpowers/sdd/2026-09-28-plan-0a-claims-pass/task-<N>-delta.tsv` — your delta file (§ A6), and `task-<N>-delta-b.tsv` when § A6 says so. You never edit `docs/reference/claims.tsv`.
- `.superpowers/sdd/2026-09-28-plan-0a-claims-pass/task-<N>-report.md` — the report (§ A9).

### A3. The page shape

```markdown
# <Title>
Verified against 42.20.4 (b0bbce05d5) · 2026-09-<dd> · scope: <one line: what this page owns and what it hands off>

## Rules                    platform/ and areas/ — see § A4
## Key facts                facts/ — see § A4
## How it works             the anchors the task names, in its order, each as an <a id> + ### heading
## Options                  areas/ only: the shapes a mod can take on this surface, one ### per option, no recommendation
## Walls and bounds         see § A5; ends with a line starting "Not covered:"
## Open                     see § A5
## Worked examples          optional; every path it names exists
## See also                 the pages this one rests on or hands off to, one line each
```

- The stamp is line 2 exactly in that shape; the date is the day you write it. An update task rewrites the stamp's date and, if the scope line changes, the scope.
- **Anchors.** Every anchor the task names, in the task's order, is a subsection under the section that owns it: an HTML anchor line, then a `###` heading, then the prose:

  ```markdown
  <a id="xp-grants"></a>
  ### Experience grants and their gates
  ```

  `#walls` is the `## Walls and bounds` section itself and `#open` is `## Open` (the `<a id>` line sits directly under the `##` heading). Every register row owned by your page has its anchor present (the page lint checks this from the register), and no anchor appears twice. An update task keeps every existing anchor and adds the ones the task names; an existing anchor's name is never changed (`#effect-paths`, not `#effect-path`).
- **Sections.** The order above is fixed. `platform/` pages carry `## Rules`; `facts/` pages carry `## Key facts` and no `## Rules`; `areas/` pages carry `## Rules` and `## Options`. The `facts/other-mods/` pages map their anchors into the contract: `#what-it-does`, `#architecture`, `#data-model`, `#mp` under `## How it works`; `#techniques` is `## Key facts` (one tagged line per technique); `#pitfalls` and `#compat` under `## Walls and bounds`; `#open` is `## Open`.

### A4. Writing the sentences

- **A tag** is `[#0417]` typed by you for an existing row and `[T<task>.<n>]` for a row you are minting (§ A6). `python tools/claims_check.py --fix-tags` appends the canonical suffix later; until then write the suffix by hand for an existing row (`[#0417/M/n=1]`, `[#0417/C/C-only]`, nothing for a settled `C` row with no bound) and leave a provisional tag bare. A sentence minting two rows carries them in two brackets, `[T4.5] [T4.6]`, or writes a real id first in a mixed bracket, `[#0417, T4.5]`: the lint's rule-line regex and the checker's rule 4 both need a real id or a lone provisional bracket. A tag closes the sentence (or the table caption, or the code-block caption) that states the row's claim. No other citation form appears on the page: no run ids in prose unless the sentence also carries a tag whose pointer names that run; no `@offsets`; no doc or report names; no dates except the stamp and a dated count's own date.
- **A rule line** (`## Rules`): `- <imperative>: <the one-clause reason — the mechanism, never the history> [#tags].` A rule whose safety depends on its bound carries the bound in the line. A rule you mint is a `rule` row (§ A6) resting on mechanism rows: its pointer is copied from a row it rests on, its bound reads `inference; a reading of <ids>`, and the line carries the resting rows' tags beside its own. A rule that rests on a measurement (the successor of `#1114`) keeps the measurement's grade `M`, its `run:` arm and its `n=` bound instead: an `inference` bound is never graded `M`. A rule another page already states is linked, never restated: two `## Rules` lines on the same tag set must be byte-identical (rule 9), and only a task that owns both pages writes one.
- **A key-fact line** (`## Key facts`): `- <declarative sentence with its numbers and units> [#tags].` Eight to fifteen lines, the page's load-bearing numbers.
- **The number lives on the owner page.** A row owned by your page is stated with its number here, tagged. A row owned by another page is cited by tag (an existing row) or linked by anchor (a row another task is minting), and its number is not repeated. A row owned by your page under a different anchor is stated once, at its anchor; other anchors refer to it. A sentence that carries no number and no claim of its own — "the packet that carries the trait list is stated at mp-model.md#sync-globals" — needs no tag.
- **Bounds as facts.** State the register's bound in words where the reader needs it ("read from the bytecode and not exercised on a live server" for `C-only`; "swept on 2026-09-28; the corpus drifts" for `snapshot`; "read from the code, not measured" for `inference`; "the arithmetic is the part a re-reader redoes" for `arith.`). Never as a caveat about the process.
- **Present tense, current truth only.** No "previously", "corrected", "resolved in", "the review found", "this slice", "RESOLVED", "CONTESTED" (the narrative regex fails the page); no run narratives; no history of how a claim was found; no report names. A supersession is invisible on the page: the page states the current claim and nothing about the old one.
- **Tables and code blocks.** A table (a `table` row) is captioned once, tagged; numbers inside a tagged table carry no tags of their own. A decoded switch, a formula or an annotated bytecode block from the report goes in a fenced block under a caption tagged once; the offsets inside it are the pointer and are not re-tagged.
- **Names are not numbers.** A version or build number, a run id, a jar offset, a workshop id, a mask value written as code (`0x07`, `32`) or any identifier goes in a code span; rule 4 strips code spans before its digit test.
- **Every number outside a code span, a code block and a tagged table carries a tag.** Rule 4 warns on a digit without a tag; the target is zero. A number that has no row is a delta, not an untagged sentence.
- **One sentence per line.** Prose paragraphs are written one sentence per physical line; a blank line separates paragraphs. A diff then shows one claim per hunk.
- **Length.** 150–400 lines of prose (500 where the task says) counted as sentence lines; tagged tables, index rows under `## Open`, code blocks, anchor lines and headings do not count. The page lint prints the count; the floor is a warning and a task may accept it. An update task's count is the whole page's.

### A5. `## Walls and bounds` and `## Open`

- `## Walls and bounds` holds, as one line each: every `bound` row owned by your page (the restriction as a fact, tagged); every proved absence (a jar-wide grep row, tagged, worded "the engine has no …"); every wall the task names, citing the wall-map `verdict` row's id where one exists (the map's row letter never appears; `#1161` is superseded in this plan — link the wall map by its path from your page, `../reference/wall-map.md#g4`, or `../../reference/wall-map.md#g4` from `facts/other-mods/`); and, last, one line beginning `Not covered:` naming the adjacent surface the library never read (from the report's `## Not read` section, the spec's coverage table and the page's own boundary).
- `## Open` holds one line per `open` row owned by the page (`- <the question> — settled by <the check>; -> X<N> [#tag]`), one line per `unverified` row (`- <the claim> is unverified: <the bound's reason>; re-measure by <the check> [#tag]`), and the decisions the design must take that the page's rows force, each with the fact that forces it and no recommendation. An `unverified` row is never quoted as a fact anywhere else on the page. An `X<N>` the task names is linked to `../areas/open-questions.md#x<n>` on its line and its open row is cited by its real id. An `open` row you mint is indexed by the controller at the wave close; you do not edit `open-questions.md`.

### A6. Deltas — how your lines become rows

You never edit the register. Every owned candidate line, every rule you mint and every open row you mint is a line of `task-<N>-delta.tsv` (tab-separated, header line, one delta per line, exactly twelve cells per line — a tab for every empty column):

```
op	id	claim	grade	pointer	bound	status	successor	kind	source	owner	reason
add	T5.1	<one sentence>	C	jar:IsoGameCharacter$XP.AddXP @107–@190 L14203–L14208	C-only; read from the bytecode, not exercised on a live server	settled		mechanism	docs/superpowers/research/jar-perks-strength.md § Claims candidates 6	facts/perks-and-strength.md#xp-grants	candidate 6
supersede	#0137										falsified by T5.1 (N1); the contradiction retires
add	T5.2	<the successor's sentence>	C	jar:…	C-only; …	settled		mechanism	docs/superpowers/research/_CONTROLLER-NOTES.md § N1	facts/perks-and-strength.md#xp-grants	successor of #0137
status	#0514				C-only; the tier switch decoded low 0 high 3, default at the asleep block	settled					bound tightened from inference (health report A.3)
retarget	#0417									facts/x.md#other	<why this anchor, not the old one>
```

- `add`: one row per owned line. `id` is `T<task>.<n>`, `n` counting from 1 and unique within your task. `claim` is one falsifiable sentence in the page's voice (the candidate's wording, tightened; a claim the candidate states with two facts becomes two rows). `grade` follows the pointer form. `bound` opens with a token from `BOUND_TOKENS` and states the restriction in words: `C-only; …` for a jar or file read, `snapshot <stamp>; …` for a corpus or Workshop reading against a committed dataset, `arith.; …` for a derived number, `inference; a reading of <ids>` for a rule or an inference. `kind` is `mechanism` by default, `count` for a count, `bound` for a restriction, `open` for an open question (status `open`), `rule` for an imperative (area and platform pages only), `contradiction` when a mirror disagrees, `verdict` on the wall map only. `source` is `docs/superpowers/research/<report>.md § <heading> <line-number>` for a report line or `docs/superpowers/research/_CONTROLLER-NOTES.md § N<k>` for a note. `owner` is `<layer>/<page>.md#<anchor>`, an anchor of your page. `reason` names the candidate line or the note.
- **Pointers.** Every pointer is one of the forms in `docs/reference/tools.md` § The register grammar. Translate the reports' shorthand: `install:<path>` → `lua:<path relative to media/>:<line> "<anchor text>"`; `ws:<id>/…` → `mod:<id>/mods/<Name>/<tree>/<path>:<line> "<anchor text>"`; `file:media/lua/…` → `lua:lua/…:<line> "<anchor>"`; `C: Class.method @a-b La-Lb` → `jar:Class.method @a–@b La–Lb`; a corpus count or absence → `data:data/mod-inventory-2026-09-28.json swept <the stamp>`; a public-Workshop reading → `web:data/workshop-catalog-details-2026-09-28.json 2026-09-28`; a hand scan of the install → `data:media/<dir> grep <literal>, <date>` (the fourth reading; the row is `unverified`). A `lua:`, `mod:` or `repo:` pointer carries a quoted fragment of the cited line, which you read from the file to write; a report line without one is not a finished pointer. A jar-wide grep is `jar:jar-wide grep <literal>`; a member list is `jar:<Class> member list`; an exposer test is `jar:LuaManager$Exposer.exposeAll() dump`. A `repo:` pointer never names a path under `docs/superpowers/`.
- **Re-location.** Before you mint it, re-read on the jar (`C:\Users\Angus\pz-b42\pz.sh dump|methods|grep`, read-only) or in the file every cite that (a) a `## Key facts` or `## Rules` line carries, (b) a successor row carries, (c) an `arith.` row's arithmetic rests on, and (d) one in five of the rest, chosen by taking every fifth owned line. A cite that re-locates at a different offset or line is corrected; a cite that does not re-locate at all is dropped with the line, and the report names it. The report lists every cite re-read and its outcome.
- `supersede`: names a real register id and is followed immediately by exactly one `add` line, which becomes the parent's successor; the parent goes `superseded`, and its tag is rewritten to the child on the pages the controller passes with `--pages` — your own, and any whose fan-out sentence an earlier task already rewrote. Every other page keeps the parent's tag with `/superseded` until its task rewrites the sentence. You rewrite the fan-out sentences on your pages and no other.
- `split`: one row that states two claims; the parent goes `superseded` with the two following `add` lines as successors.
- `status`: a status or bound change on an existing row (`settled -> open`, `open -> settled`, a tightened bound), or the closing of an open row onto a successor that already exists (`status … superseded` with the real `#dddd` in the successor cell). A `status` never rewrites a tag: the fan-out table assigns every sentence. A `status` whose successor is a row your own delta mints goes in a second file `task-<N>-delta-b.tsv` with the successor written as its `T<N>.<m>` id; the controller rewrites that cell to the real id after applying your first file and then applies the second with `--pages <your page>`.
- `retarget`: a row whose right anchor is another anchor of your page or another page; a cross-page retarget is applied only if the controller agrees, so say why.
- A delta never names a row that is already `superseded` (the tool refuses it), and never names a parent another task supersedes.
- The controller applies every delta at the wave's close, in task order, in one commit for the wave; `--pages` is always a subset of the checker's tagged files (`docs/areas`, `docs/platform`, `docs/facts`, `docs/reference/datasets.md`, `docs/reference/tools.md`, `docs/reference/wall-map.md`, `.claude/skills/*/SKILL.md`) and never `docs/superpowers/`, `docs/reference/claims.tsv` or `docs/reference/claims-coverage.md`. Your per-task review therefore reads provisional tags with `--allow-provisional`, and the real tags are checked at the wave-close read.

### A7. Validate before you commit

```bash
cd /c/Users/Angus/repos/project_zomboid
python tools/claims_check.py --partial --allow-provisional                       # 0 findings (warnings are rule 4: aim for 0)
python tools/page_lint.py docs/<layer>/<page>.md --partial --allow-provisional   # 0 findings; note the prose count it prints
python tools/page_lint.py <every other page you touched> --partial --allow-provisional
python tools/claims_check.py --staged --partial --allow-provisional              # after staging, the CLAUDE.md § 3 gate as ruled for the plan
```

Never run `--fix-tags`: it rewrites every tagged file in the tree and races the writers beside you; the controller runs it once at each wave's close. Rule 1 fails when a row owned by your page is not tagged on it; rule 2 fails on a tag the register lacks or a stale suffix; rule 6 fails when a skill's quoted rule line is not verbatim on its page (a task that changes a `## Rules` line re-syncs the skill in the same commit, byte-identically); rule 9 fails when two pages carry a rule on the same tag set with no byte-identical line (the `#1104` line is left byte-identical on every page until Plan 0a Task 27). The page lint fails on a missing section, a wrong section order, a missing anchor, a `## Rules` or `## Key facts` line without a tag, a `## Walls and bounds` without a closing `Not covered:` line, a narrative marker, a prose count over the cap, a `## Worked examples` path that does not exist, or a link whose target page or anchor is missing. Fix every finding; never commit with one.

### A8. Commit

One pathspec commit for the task's pages: `git add <pages> && git commit -m "Page: <layer>/<page>" -- <pages>` (a task with two pages names both in the subject; a task that also commits a dataset names it). Never `--amend`. No push. No other file changes: not the register, not a report, not a tool, not another task's page. The delta file and the report live in the SDD workspace (gitignored).

### A9. Report

`task-<N>-report.md`: owned lines (count), rows minted (count, equal after drops), lines dropped (each with the surviving row or line); rows cited from other pages (ids); anchors linked without a tag (page#anchor); supersessions filed (parent, child) and fan-out sentences rewritten (page:line); the `delta-b` file if any; cites re-read (each with its outcome); the prose line count and the rule-4 warning count; the anchors that have no rows and what you wrote under them; the ten sentences you are least sure of, each with its tag and why; concerns. Return to the controller only: status, the commit, the one-line count (`<page>: N rows minted, M prose lines, K supersessions, J cites re-read`), concerns.

### A10. What the reviewer checks (so you know the bar)

A fresh reviewer runs the same commands and then reads the page against the delta file and the report's candidate lines: every owned line minted once and stated faithfully at its anchor (the sentence says what the candidate says, with the candidate's numbers and its bound where it matters); no number without a tag; no number restated from another page's row; no tag on a parent the fan-out table names; every pointer in a legal form with re-locatable anchor text and the right file and stamp, and a fresh sample of five cites re-read on the jar or in the file by the reviewer; every drop justified by the survivor named; every supersession's child a faithful correction of its parent and every fan-out sentence the table assigns the task rewritten; every wall and open row present; the section order and the anchors against the task; the narrative regex clean; the prose within the cap; the skill re-synced where a rule line changed; no rule restated from another page; the writing rules above.

## Part B — harvest tasks

### B1. Inputs

- **Your report sections** — the task names one science report under `docs/superpowers/research/` and the sections of it you own, its `## Gaps` section included where the task says. The report's `## How to read this` states its grades; its per-topic tables carry the `parameter | value | range | population | grade | citation` rows; its `## Proposed model` (wave 2), `## Engine mapping` or `Interpretation for a game model` paragraphs (wave 1) are design and are not rows; its `## Gaps` lines that name a missing quantity are open rows; its `## Bibliography` is the citation index.
- **The register grammar.** `tools/sciencelib.py` (`COLUMNS`, `TOPICS`, `GRADES`, `RANK`, `resolve_grade`, `STATUSES`, `CITATION_RX`, `SOURCE_RX`) and `docs/reference/science.md`.
- **The shipped values and the corrections** the task names (spec § 4.3–§ 4.5, § 7 items 1–2, 9–12, 30–36, § 9).

### B2. Outputs

- `.superpowers/sdd/2026-09-28-plan-0b-science-register/task-<N>-science.tsv` — your part file (§ B3). You never edit `docs/reference/science.tsv` or `tools/sciencelib.py`.
- `.superpowers/sdd/2026-09-28-plan-0b-science-register/task-<N>-report.md` — the report (§ B5), with the digest paragraph and any slug request.
- No page and no commit: the controller applies your part file with `python tools/science_delta.py apply <part>` at the wave's close and pastes your digest into `docs/reference/science.md` § Sources.

### B3. Rows

The part file is tab-separated with the register's header exactly and one row per line:

```
id	topic	parameter	value	range	population	grade	citation	source	status	successor
S10.1	protein	protein intake at which resistance-training gains in fat-free mass plateau	1.62 g/kg/day	95% CI 1.03–2.20	healthy adults under resistance training, 49 studies n=1863	MA	Morton RW et al 2018, Br J Sports Med 52:376–384; doi:10.1136/bjsports-2017-097608; pmid:28698222	docs/superpowers/research/wave2-science-strength-training.md § 2	settled	
S3.7		half-life of hepatic vitamin A stores						docs/superpowers/research/science-vitamins.md § Vitamin A	open	
```

- **One row per table line whose citation the report verified by fetch**, and one per graded paragraph number that has no table line. A table line marked "not verified in this run" or graded `—` becomes an `open` row (empty topic, grade, value, range and citation; the parameter named; `population` may say what would settle it). A number the report marks **unverified** inline becomes an `unverified` row carrying the number and the citation as written. A `## Gaps` line that names a missing quantity becomes an `open` row.
- `id` is `S<task>.<n>`, `n` from 1, unique within the task. `topic` is one slug of `TOPICS` — the nutrient's own slug for a nutrient row, the system's slug for a system row, `general` for a cross-cutting row; a slug the vocabulary lacks is **requested in your report** with the rows that need it (write those rows with the slug you request, so `--part` fails on them alone until the controller adds it), never added by you. `parameter` is a noun phrase naming the quantity, with the direction of effect where the row is an effect ("strength change under 24 h sleep deprivation"). `value` carries the number and its unit, or the qualitative finding for a non-numeric row ("no supported effect on cognition"). `range` is the uncertainty or spread as the report gives it. `population` is the population and context. `grade` is the report's token through `resolve_grade`: `MA`, `RCT`, `COH`, `AUTH`, `TXT` stand; `EXP` and `MODEL` are grades of their own; `CASE` → `COH`; a slashed pair takes the left-most member of `RANK = (MA, RCT, EXP, COH, AUTH, TXT)` whichever order it is written in; `MODEL` never pairs (a model beside a trial is two rows); `INF` and `GAME` lines are not rows. `citation` is `<first author> et al <year>, <journal> <volume:pages>;` then `doi:<doi>` and/or `pmid:<digits>`, lowercase prefixes with a colon and no space; an authority report with no DOI carries `url:<https://…>` and a textbook `isbn:<digits>`; two citations in one cell are separated by `; `. **Every report writes `PMID <digits>`** and four also write `DOI 10.…`: script the rewrite over your sections once (`PMID ` → `pmid:`; `DOI ` → `doi:` where it occurs; a bare `PMC…` dropped) before you build a cell. `source` is `docs/superpowers/research/<report>.md § <heading>` with one space either side of the section sign. `status` is `settled`, `open` or `unverified`; `successor` is empty.
- **Game choices are not rows.** A constant the report labels a choice (a saturation constant it proposes, a clamp, a cadence, a dial's default) is design; where the report grounds a proposed constant in a cited value, the cited value is the row and the proposal is not.
- **Two irreconcilable sources are two `settled` rows** whose `parameter` names the disagreement; the choice between them is the design's ruling, not a row.
- **Corrections.** Where the task names a spec § 9 correction, the row carries the corrected reading and both citations (the earlier and the update), and the report says which line it replaced.
- **Verification.** Before you mint it, resolve through Europe PMC (`https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=DOI:<doi>&format=json`) or Crossref (`https://api.crossref.org/works/<doi>`), matching title, first author and year against the cell: every row whose value the task names as shipped, every tenth row of your part file, and every row the report itself marks unverified. A citation that does not resolve is fixed from the record or the row goes `unverified` with the reason in `population`. The report lists every citation resolved.

### B4. Validate before you hand over

```bash
cd /c/Users/Angus/repos/project_zomboid
python tools/science_check.py --part .superpowers/sdd/2026-09-28-plan-0b-science-register/task-<N>-science.tsv   # 0 findings, or only the rows carrying a slug you requested
```

The checker in `--part` mode accepts provisional ids and checks everything else: the header, the cell count, the topic and grade on every row that is not open, the status, the citation form on a settled or unverified row, the empty value on a settled row, the source form.

### B5. Report

`task-<N>-report.md`: table lines read (count), rows written (count) by status, grade and topic, table lines not minted and why (game choices, duplicates within the report), citations resolved (each with its outcome), corrections applied, any slug requested with the rows that need it, the five-sentence digest paragraph for `science.md` § Sources (what the sections cover, the population caveat, the largest gap), the ten rows you are least sure of and why, concerns. Return to the controller only: status, the part file path, the one-line count (`<report> <sections>: N rows (a settled, b open, c unverified), K citations resolved, slugs requested: <list or none>`), concerns.

### B6. What the reviewer checks

A fresh reviewer runs the checker on the part file and reads it against the report sections: every verified table line present once with its numbers, range, population, topic and grade as the report gives them and the mapping states; no proposed-model constant minted; every `open` row a real gap or an ungraded line, ungraded itself; every citation in the cell form, and a fresh sample of ten resolved through Europe PMC or Crossref by the reviewer; the shipped values the task names all present and `settled`; the corrections applied as the spec states them; every `## Gaps` line the task owns accounted for.
