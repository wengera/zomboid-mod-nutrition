# Plan 20: slim the docs and comments — design

## Why

Angus asked on 2026-10-23 to "slim up comments and documentation to optimize its usefulness for the current state and avoiding pitfalls/problems we ran into getting there and research/notes helpful for moving forward … make everything more succinct and relevant, trim the fluff, make it more useful without dredging thru pages and pages."

The starting sizes, measured at 7d247fc2:

| Item | Size |
|---|---|
| CLAUDE.md | 247 lines, about 9,100 words |
| Pages (areas, platform, facts) | about 340,000 words |
| Reference layer | about 1.5M words; `claims.tsv` has 3,995 rows, 297 of them superseded; `artifacts.md` is over 1,800 lines |
| `docs/superpowers/` | 141 files, about 918,000 words |
| Mod Lua | 22,478 lines, about 7,300 of them comments |

## Decisions (Angus, 2026-10-23)

- **A: the evidence system stays.** Every claim on a page keeps its tag and register row, and the slimming works inside that system.
- **3: distil the history, then archive it.** Notes from `docs/superpowers/` that are still useful move into the pages or `docs/reference/research-notes.md`. The tree is tagged `program-record-v19`, the closed plans' files are removed, and `docs/superpowers/HISTORY.md` indexes them.
- **b: mod comments keep the why, the pitfalls and one short provenance id.** History narration goes.
- **i: the reference layer is split, not rewritten.**
  - Superseded rows move to `claims-archive.tsv`.
  - Each run's reading guide moves to `testing/artifacts/<run>/GUIDE.md`, and `artifacts.md` keeps only its table.
  - Bounds stay as written.
- **β: CLAUDE.md shrinks to about 140 lines.** It keeps its rules as one line each; the incident stories move to `docs/process/lessons.md`.
- **y: a new `retired` status.** A row that is true but no longer worth a page sentence moves to the archive file, where it stays citable.

## Workstreams, in order

1. **Tooling.** The checker and the delta tool learn the archive file and the `retired` status:
   - ids are unique and gap-free across both files;
   - a page tag naming an archived id fails;
   - archived superseded rows are not resolved;
   - retired rows are pinned to the commit where they last held;
   - `claims_delta.py` gains a `retire` operation;
   - `reference_gen` counts both files;
   - a pinned pointer accepts a tag name (`repo:<path>@program-record-v19:<line>`).

   Two new tools come with it:
   - per-folder `GUIDE.md` support in the artifacts tooling;
   - a comment-id lint, which checks that a dial-reading line's trailing `#N`/`S####` id appears in its row's `src`.

   All of these get tests.
2. **Reference split.**
   - The 297 superseded rows move to the archive.
   - The reading guides move into their artifact folders, and `artifacts.md` shrinks to its table.
   - Pointers into `artifacts.md` are re-anchored.
3. **History distil and archive.**
   - Research readers each take a group of plans and return short notes files, which the controller merges into `research-notes.md` and the pages.
   - The tag is cut.
   - Pinned pointers into `docs/superpowers/` are rewritten to the tag form.
   - The closed plans' files are removed, and `HISTORY.md` gets one entry per plan: what it built, its key rulings, and its commit range.
4. **CLAUDE.md to about 140 lines.**
   - It keeps the router, the ground truth, a compact gate table, and the live-run and register rules inline, one line each.
   - The stories go to `docs/process/lessons.md`, grouped by topic: live runs, register and deltas, reviews and agents, git and worktrees, fits and oracles, and tools. Each entry gives the rule, the incident in one or two lines, and a citation.
   - Skills that quote rule lines are re-synced.
   - `docs/platform/lessons.md` stays the home of engine rules.
5. **Page pass.** Every area, platform and facts page is rewritten to the order Rules (pitfalls first), How it works (current state only), Walls, Open.
   - Narration and duplication come out, and each fact gets one owner page; other pages link to it.
   - A row left with no sentence is re-homed or retired. A row is retired only if no dial src, kernel comment, area rule, skill, guide or open-questions line cites it, and it is not an artifact's only reading. A reviewer checks every retirement list, and the first page's list gets a second reviewer.
   - The work goes by layer in waves of three or four pages, area pages first. Writers in a wave own disjoint files, and the controller mints serially at each wave's close.
6. **Mod comment pass.**
   - History narration is deleted, and the remaining comments become the why plus one short id.
   - Pointers are requoted.
   - It runs domain by domain in one serial lane, with each wave reviewed.
   - The comment-id lint becomes a § 3 gate.
7. **Close.**
   - A light trim of README, STRATEGY and the skills.
   - A whole-pass review, the fix wave, CLAUDE.md, memory, and the push.

## Guards

- **Checker gates.** After every commit, the full claims_check reads 0, page_lint on the touched pages reads 0, and doc_lint and reference_gen are green.
- **Meaning-bearing edits.** Any change to a claim's text, a bound's limit, or a retirement goes through a delta and the controller's apply.
- **Mod behaviour.** The comment pass keeps:
  - the golden trace byte-identical;
  - every generated file in sync;
  - the guide data changed in its commit lines only;
  - the bench's Java calls unchanged.

  A comment edit that changes code is a stop.
- **Tests.** The test count never drops, and the new checker rules get tests.
- **Page-pass tag audit.** The reviewer diffs the old page's tags against the new page, the pages the facts were re-homed to, and the retirement list. Every tag must land in one of them.

## Targets

These are guidance, not gates; meaning beats length.

| Item | Target |
|---|---|
| CLAUDE.md | about 140 lines |
| Area pages | at least 40 % shorter |
| Platform and facts pages | at least 30 % shorter |
| Live `claims.tsv` | under 3,000 rows |
| `artifacts.md` | under 300 lines |
| `docs/superpowers/` | `HISTORY.md` plus the open plan only |
| Mod comment lines | at least 30 % fewer |

## Done when

- A cold agent can answer "what is the pitfall before I do X" from at most three files: the router, the area page's Rules, and `docs/process/lessons.md`.
- All gates are green and the whole-pass review passes.

## Not in this plan

- Changing any claim's meaning or any mod value.
- Rewriting the bounds.
- Loosening the evidence system.
