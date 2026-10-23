# Plan 20: slim the docs and comments — implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Make the repo's documentation and the mod's comments succinct and current:
- the pitfalls stay findable;
- the still-useful research is kept;
- the fluff and history are archived.

The evidence system stays.

**Architecture:**
- First, the tooling learns two things: an archive register for superseded and retired rows, and per-run guide files.
- Then the reference layer is split, the history is distilled and archived to a tag, CLAUDE.md is rewritten around a lessons file, the pages are rewritten in waves, and the mod's comments are trimmed.
- Every step is checker-green, and none changes a claim's meaning or a mod value.

**Spec:** `docs/superpowers/specs/2026-10-23-slim-docs-design.md` (read it in full).

## Global Constraints

- CLAUDE.md §§ 3–6 bind every task: the gates, deltas through the controller's apply, pathspec commits, no index-wide git, and never setting GIT_DIR or any GIT_* variable.
- No claim changes meaning, no mod value changes, and the test count never drops.
- After every commit:
  - the full claims_check reads 0;
  - page_lint reads 0 on the touched pages;
  - doc_lint and reference_gen are green.
- The mod comment pass:
  - keeps the golden trace byte-identical;
  - keeps every generated file in sync;
  - changes only the guide data's commit lines;
  - leaves the bench's Java calls unchanged.
- A row is retired only when all of these hold:
  - no dial src, kernel comment, area rule, skill, guide or open-questions line cites it;
  - it is not an artifact's only reading;
  - a reviewer agreed.
- Targets are guidance, and meaning beats length:

  | What | Target |
  |---|---|
  | CLAUDE.md | about 140 lines |
  | Area pages | at least 40 % shorter |
  | Platform and facts pages | at least 30 % shorter |
  | Live `claims.tsv` | under 3,000 rows |
  | `artifacts.md` | under 300 lines |
  | Mod comment lines | at least 30 % fewer |

---

### Task 1: Tooling (tools lane)

**Files:**
- Modify: `tools/claims_check.py`, `tools/claims_delta.py`, `tools/reference_gen.py`, and the artifacts/do-not-cite readers in the checker.
- Create: `docs/reference/claims-archive.tsv`, empty with its header; `tools/comment_id_lint.py`.
- Test: `tools/tests/test_claims_check.py`, `test_claims_delta.py`, `test_reference_gen.py`, and a new `test_comment_id_lint.py`.

**Produces:**
- **The archive file.** It has the same columns as the register. Ids are unique and gap-free across both files.
  - A page tag naming an archived id is a finding.
  - Archived superseded rows' pointers are not resolved.
  - Archived retired rows' pointers are resolved only in their pinned form (`@<commit or tag>`).
- **The `retired` status.** `claims_delta.py` gains a `retire` op, which moves a row to the archive with its bound appended `; retired <date>: <reason>` and its pointers pinned at HEAD, and an `archive-superseded` op.
- **Pins.** A pinned pointer accepts a tag name.
- **`reference_gen`.** cited-by counts both files.
- **Artifact guides.** The checker reads an artifact's guide from `testing/artifacts/<run>/GUIDE.md` when `artifacts.md`'s row links it, and the wildcard-sentence rule applies there.
- **The comment-id lint.** `comment_id_lint.py mod/NutritionRevamp` checks that a line reading `K.dials.get("<id>")` whose trailing comment names `#NNNN` or `S####` has each of them in the row's src. It reports findings only; it becomes a gate in Task 6.

**Steps:**
- [ ] Write failing tests for each rule: an archived id tagged on a page; a gap across files; a duplicate across files; a superseded archived pointer that is never resolved; a retired pointer at a tag; a cited-by count over both files; the guide-file wildcard; a comment id missing from src.
- [ ] Implement each rule.
- [ ] Run the gates and the full pytest.
- [ ] Commit by pathspec.

### Task 2: The reference split

**Files:** `docs/reference/claims.tsv`, `claims-archive.tsv`, `artifacts.md`, `testing/artifacts/*/GUIDE.md`, and every page whose tags name a superseded row (there should be none at HEAD; confirm it).

**Steps:**
- [ ] Move the 297 superseded rows to the archive through `claims_delta.py archive-superseded` (a controller apply).
- [ ] Move each run's reading guide verbatim into `testing/artifacts/<run>/GUIDE.md`. `artifacts.md` keeps one row per run: run id, files, what it measured, guide link.
- [ ] Re-anchor every `repo:docs/reference/artifacts.md` pointer to the table row or the guide file.
- [ ] Run the full claims_check (0), reference_gen, and the full pytest.
- [ ] Commit by pathspec.

### Task 3: Distil and archive the history

**Files:** `docs/superpowers/**`, `docs/reference/research-notes.md` (create), `docs/superpowers/HISTORY.md` (create), and the pages that take notes.

**Steps:**
- [ ] Opus research readers, one per plan group, read the reports, specs and plans. Each returns a notes file with:
  - open mechanism candidates;
  - unfinished findings and their evidence;
  - ideas Angus asked for later;
  - pitfalls not yet in the lessons or the pages.

  Only items still true at HEAD go in, each with its source path.
- [ ] Merge the notes into `research-notes.md`, or into a page's Open section where they belong. Write `HISTORY.md` with one entry per plan: what it built, its key rulings, its commit range, and its register range.
- [ ] Cut the tag `program-record-v19` at the commit before the removal.
- [ ] Rewrite every register pointer into `docs/superpowers/` files to the `@program-record-v19` form. Leave source cells as provenance.
- [ ] Remove the closed plans' files, keeping `HISTORY.md` and Plan 20's own spec and plan.
- [ ] Add a CLAUDE.md § 1 line: the record lives at the tag.
- [ ] Run the gates and commit.

### Task 4: CLAUDE.md and the lessons file

**Files:** `CLAUDE.md`, `docs/process/lessons.md` (create), and the `.claude/skills/*` that quote rule lines.

**Steps:**
- [ ] Write `docs/process/lessons.md`, grouped into: live runs; register and deltas; reviews and agents; git and worktrees; fits and oracles; tools and gates. Each entry gives the rule, the incident in one or two lines, and its citation. Every § 5 and § 6 rule's story moves there.
- [ ] Rewrite CLAUDE.md to about 140 lines:
  - § 1: the router, plus the history-tag line;
  - § 2: ground truth;
  - § 3: the gates as one compact table;
  - § 4: extending the reference, as short rules;
  - §§ 5–6: one-line rules, each linking its lessons group;
  - § 7: environment;
  - § 8: memory.

  Keep every rule; drop only stories and citations. Keep the baseline as its latest count plus a pointer to the lessons file for the history of the count.
- [ ] Re-sync the skills that quote a rule line (the checker fails otherwise).
- [ ] Have a reviewer diff every old rule against the new file and the lessons file. A rule lost from both is a FAIL.
- [ ] Commit.

### Task 5: The page pass (waves)

**Files:** `docs/areas/*.md` first, then `docs/platform/*.md`, then `docs/facts/**/*.md`.

**Per wave** (three or four pages, disjoint writers):
- [ ] Each page is rewritten to the order Rules (pitfalls first), How it works (current state only), Walls, Open.
  - Narration and duplication come out, and each fact has one owner page; the others link.
  - A writer returns: the new page, a re-home list (tag to its new page), and a retirement delta (rows that meet the retire rule, each with its reason).
  - Writers never edit the register.
- [ ] A reviewer diffs the old page's tags against the new page, the re-home list and the retirement list; every tag must land. The reviewer checks the retire rule per row and that no sentence's meaning changed. The first wave's retirement lists get a second reviewer.
- [ ] The controller applies the wave's deltas, running the § 4.10 regex on the touched pages and the fill step. Then the full claims_check (0), page_lint (0), the guide tests, and the commit.

### Task 6: The mod comment pass (mod lane)

**Files:** `mod/NutritionRevamp/**.lua`, excluding the generated files, by domain as the dial waves ran.

**Per wave:**
- [ ] Delete the history narration: plan and task numbers, "moved from", "was", old values.
- [ ] Trim each comment to the why or the pitfall plus one short id. A dial-reading line keeps an id only if it is in the row's src.
- [ ] Requote every register pointer to a changed comment line.
- [ ] Keep the golden trace byte-identical and the generated files in sync; the guide changes only its commit lines; the bench's Java calls are unchanged.
- [ ] A reviewer checks the diff is comments only. A token change outside a comment is a FAIL.

At the end:
- [ ] Make `comment_id_lint` a § 3 gate.

### Task 7: Close

- [ ] Give README, STRATEGY and the skills' bodies a light trim.
- [ ] A whole-pass review (Opus). Its "done when" check: a cold agent answers "the pitfall before X" from the router, the area page's Rules and `docs/process/lessons.md`.
- [ ] One consolidated fix wave and its re-review.
- [ ] Run the gates and the full pytest.
- [ ] Update CLAUDE.md's baseline and the memory files.
- [ ] Push.
