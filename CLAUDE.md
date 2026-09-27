# CLAUDE.md — the agent handoff and router

Read §§ 1–3 before touching anything, § 5 before any live run, § 6 before running a plan, and § 9 for where the work stands.

## 1. What this repo is

This repository is an agent-facing reference for modding Project Zomboid Build 42; its first consumer is a realism nutrition mod — nutrients tracked mod-side beyond the vanilla macros, a rebalance of the vanilla food items, multiplayer first.
[docs/areas/](docs/areas/) is the nutrition lens, [docs/platform/](docs/platform/) general modding knowledge, [docs/facts/](docs/facts/) the measured vanilla food and nutrition mechanics, and [docs/reference/](docs/reference/) the claims register with the datasets, tools, experiments, jar notes and generated harness commands.
Every claim on a page carries a tag naming its row in [the register](docs/reference/claims.tsv), and the row carries the grade and the pointer to its evidence; [README.md](README.md) is the map and the tag grammar, [STRATEGY.md](STRATEGY.md) the charter.
The pages state what the game does and what a mod can and cannot change; the mod's design is not in this tree, and a root file names pages, never claims.

Route a task by its shape and read the pages in the order given; stop when the task is answered.

| Task shape | Pages, in reading order | Skill |
|---|---|---|
| add a mod nutrient | [areas/new-nutrients](docs/areas/new-nutrients.md) → [platform/mp-model](docs/platform/mp-model.md) → [facts/wire-packets](docs/facts/wire-packets.md) | `nutrition-new-nutrients` |
| override a vanilla food | [areas/item-pass](docs/areas/item-pass.md) → [platform/loader-and-scripts](docs/platform/loader-and-scripts.md) → [facts/food-item-model](docs/facts/food-item-model.md) | `nutrition-item-pass` |
| hook eating or cooking | [areas/eat-and-cook-hooks](docs/areas/eat-and-cook-hooks.md) → [platform/lua-platform#script-hooks](docs/platform/lua-platform.md#script-hooks) → [facts/eating-pipeline](docs/facts/eating-pipeline.md) | `nutrition-eat-and-cook-hooks` |
| sync mod state | [areas/mp-sync](docs/areas/mp-sync.md) → [platform/mp-model](docs/platform/mp-model.md) → [facts/wire-packets](docs/facts/wire-packets.md) | `nutrition-mp-sync` |
| show a value or a moodle | [areas/ui-and-moodles](docs/areas/ui-and-moodles.md) → [platform/lua-platform#registries](docs/platform/lua-platform.md#registries) | `nutrition-ui-and-moodles` |
| package or ship | [areas/packaging](docs/areas/packaging.md) → [platform/mod-anatomy](docs/platform/mod-anatomy.md) | `nutrition-packaging` |
| test a mod live | [areas/testing-your-mod](docs/areas/testing-your-mod.md) → [platform/harness](docs/platform/harness.md) → [reference/harness-commands](docs/reference/harness-commands.md) | `nutrition-testing-your-mod` |
| run or change the harness | [platform/harness](docs/platform/harness.md) → [reference/harness-commands](docs/reference/harness-commands.md) → § 5 | `pz-mod-testing` |
| answer from the jar | [platform/jar-research](docs/platform/jar-research.md) → [reference/jar-method-notes](docs/reference/jar-method-notes.md) | `pz-jar-research` |
| a PZ modding task outside nutrition | [platform/overview#coverage](docs/platform/overview.md#coverage) → the platform page its [routing table](docs/platform/overview.md#routing) names | `pz-modding-platform` |
| a vanilla food, body, spoilage or cooking number | [platform/overview#routing](docs/platform/overview.md#routing) → the facts page it names | — |
| what another mod already does | [facts/other-mods/catalog](docs/facts/other-mods/catalog.md) → that mod's own page | — |
| a standing rule or an anti-pattern | [platform/lessons](docs/platform/lessons.md) | — |
| a dataset column | [reference/datasets](docs/reference/datasets.md) | — |
| a tool | [reference/tools](docs/reference/tools.md) | — |
| what is still open | [areas/open-questions](docs/areas/open-questions.md) → [reference/experiments](docs/reference/experiments.md) | — |

The skills under `.claude/skills/` route the same way: each description fires on its row's task shape, and its `## Read first` opens that row's pages.

## 2. Ground truth

- **Build:** `42.20.4` · jar `b0bbce05d5`; a claim holds on this build and is re-read on any other.
- The local install `D:\SteamLibrary\steamapps\common\ProjectZomboid` and the workshop folder `D:\SteamLibrary\steamapps\workshop\content\108600` are read-only, always.
- The jar toolchain lives at `C:\Users\Angus\pz-b42`: read its `WORKSPACE.md` first, treat it as read-only from here, and verify every Java claim through `./pz.sh grep|methods|refs|dump <class> [method]`; [platform/jar-research](docs/platform/jar-research.md) turns a reading into a citable claim.
- The library is dedicated-server multiplayer evidence; single-player is never claimed.
- Owner: Angus. Remote: `https://github.com/wengera/zomboid-mod-nutrition.git`, branch `main`; pushes work from this checkout.

## 3. Gates before any commit

Run every gate a commit's paths trigger; each ends at zero findings or green.

- `python tools/claims_check.py --staged` → 0 findings before every commit that touches `docs/`, `.claude/skills/`, `testing/PZTestKit/`, `testing/artifacts/`, `testing/experiments/` or `tools/bus_inventory.py` (it says so and skips when nothing staged is under those paths); add `--partial` until the cut, because the wall map's rows have no owner page before it moves.
- `python tools/page_lint.py <the pages touched> --partial` → 0 before any commit that touches a page under `docs/areas/`, `docs/platform/` or `docs/facts/`, or `docs/reference/datasets.md` or `docs/reference/tools.md`; without `--partial` from the cut on.
- `python tools/bus_inventory.py --check` → in sync after any harness edit.
- `python tools/doc_lint.py docs/reference/wall-map.md` → 0 from the cut on (the wall map moves to that path at the cut); until then `python tools/doc_lint.py docs/mods-survey docs/modding` → 0 and `python tools/doc_lint.py docs/vanilla docs/modding docs/testing references docs/mods-survey/nutrition-mods.md` → 0.
- `python -m pytest tools/tests testing/tests -q` green: 383 passed on 2026-09-26, and the count never drops.

## 4. Extending the reference

A claim is minted in the commit that lands its evidence, never later.

1. **A new measurement:** the run's JSON is copied byte-identical to `testing/artifacts/<run-id>/` with a row in the artifacts register (run id · file · what it measured · its reading guide) and its keys in `docs/reference/do-not-cite.csv` (empty allowed; a listed key is never cited); the same commit adds the register rows and the tagged sentences on their owner pages, green under the checker.
2. **Ids:** the next unused id; the checker fails a duplicate or a gap; a parallel SDD wave reserves an id block per task in its ledger before dispatch.
3. **Settling an open row:** the row keeps its id and goes `open -> settled` with its pointer and bound filled; the owner sentence is rewritten to the settled form, its line leaves `docs/areas/open-questions.md`, and its rows in `docs/reference/experiments.md` and the wall map's experiment table are marked `run <run-id>`; a reading that comes back unmeasured or trivial stays `open` with the run named in `bound`.
4. **Superseding:** a claim a run overturns keeps its id and goes `superseded` with `successor`; every page tagging it moves to the successor in the same commit.
5. **A harness change** (a new `TK.register`, a changed reply) lands in its own commit with its comment block, `tools/luabalance.py` green and `tools/bus_inventory.py` regenerating `docs/reference/harness-commands.md`, before the run that uses it.
6. **A rule line edit** re-syncs the skills that quote it in the same commit; the checker fails otherwise.
7. **Who runs the checker:** the committer, `--staged`, before every commit that touches its trigger paths (§ 3); an SDD reviewer re-runs it on the review package.

## 5. Harness rules

The instrument is [platform/harness](docs/platform/harness.md) (the run procedure is its [`## Procedure`](docs/platform/harness.md#procedure)); the command table is [reference/harness-commands](docs/reference/harness-commands.md).

- `python testing/pzt doctor` before every boot.
- One live game session at a time, repository-wide.
- Never `-safemode`.
- A harness change lands before the run that uses it, in its own commit, with the balance check (`python tools/luabalance.py <lua files>`, the HEAD copies first, then the working tree) and the command table regenerated (`python tools/bus_inventory.py`); the next acceptance run is its smoke test.
- A driver (`testing/experiments/*.py`) is never edited after its run; a post-run edit is a skew note.
- A reading that comes back trivial, unmeasured or falsified is written as such and never re-run to make a number prettier.
- Artifacts are committed byte-identical to the run copy, each with a row in the artifacts register (`testing/artifacts/README.md`, which moves to `docs/reference/artifacts.md` at the cut).
- A raising probe is gated on the server side with its profile's `[client] timeout` set low, and `pzt run` is expected to fail: the grade comes off the artifact.
- A stray `ProjectZomboid64.exe` predating a session is Angus's own client: never kill it (`doctor` checks game Java only).
- Fixture caches (`testing/fixtures/default/cache/`) and run folders (`testing/runs/`) are per-machine and gitignored.
- Kahlua rules for every harness and experiment Lua file: no `goto`, no `%d` on floats, no `#` on Java lists.
- The experiment mods (`testing/experiments/TKX_*`) are installed only through test profiles, never into the fixture.
- Standing rule: live-server experiments and trial and error are encouraged, and the harness is improved as the work goes whenever that makes a measurement better — before the run, under the rules above.

## 6. Process

- Every plan runs with `superpowers:subagent-driven-development`; `superpowers:writing-plans` writes a plan, `superpowers:brainstorming` opens any new design, and `superpowers:verification-before-completion` precedes any claim that work is done.
- Fable leads on the main thread; every implementer and reviewer is a fresh Opus subagent (`model: "opus"`, always specified); if Opus is rate-limited, wait for the reset or ask Angus which model to substitute — never downgrade silently.
- The skill lives at `C:\Users\Angus\.claude\plugins\cache\superpowers-marketplace\superpowers\6.3.0\skills\subagent-driven-development\`: `scripts/sdd-workspace PLAN_FILE` creates the plan's workspace, `scripts/task-brief PLAN_FILE N` writes a task brief, and `scripts/review-package PLAN_FILE BASE HEAD` builds a review diff for a contiguous range.
- Per-plan ledgers `.superpowers/sdd/<plan-basename>/progress.md` (gitignored) are the only ledgers, and the whole per-plan workspace beside them (briefs, reports, deltas, review packages) is kept, never deleted, whatever the skill's cleanup step says. The first line names the plan; every dispatch, report, review and ruling is a line in it; after compaction trust the ledger and `git log`, not memory; a task with a `Task <N>: complete` line is done, and work resumes at the first task without one.
- Per task: the controller writes `task-N-amendments.md` (what the brief cannot know) → a fresh implementer writes `task-N-report.md` and returns only status, commit, one line of verification and concerns → the review package is `review-tN.diff`, `git show -U8` of the task's own commits with artifact JSON excluded → a fresh read-only reviewer checks spec compliance and quality → each fix round is a fresh implementer with `task-N-fix-K-brief.md` → a scoped re-review → the controller applies tiny residuals → `Task N: complete`.
- A plan closes after a whole-pass review, one consolidated fix wave and its re-review: the controller runs § 3, pushes, and updates this file and the memory file (§ 8).
- Rulings are written `Ruling: <what> — <why> — cost if wrong: <…>`. A ruling about the platform becomes a rule on [platform/lessons](docs/platform/lessons.md) with its mechanism row; a ruling about how this repository works becomes a rule in this file; a ruling a later agent must know is never only a ledger row.
- Commits are pathspec commits (`git commit -m "…" -- <paths>`), never `--amend`, with no Claude attribution and a succinct subject line; implementers never push — the controller pushes at a plan's close.
- Proceed to completion and ledger each decision for review instead of asking; ask only before a destructive action or one outside this worktree.
- Implementers run in parallel only on disjoint files; reviewers are read-only, may overlap anything, and read an implementer's committed content with `git show <commit>:<path>`; research subagents are sent off as the work goes.
- The register is read-only for page writers: a new or changed claim is a delta file the controller applies with `tools/claims_delta.py`, and a writer never runs `claims_check.py --fix-tags` (the controller runs it once per wave close).

## 7. Environment gotchas

- The Bash tool's cwd resets between calls: `cd /c/Users/Angus/repos/project_zomboid` in every call, or edits land in the home directory.
- Long Bash heredocs with apostrophes fail to parse: write briefs and long files with the Write tool, and keep Bash-embedded Python apostrophe-free.
- CRLF survivors in the working tree: `docs/progress.md`, `docs/decisions.md`, `docs/modding/patterns.md`, `docs/testing/README.md`, `tools/README.md` (CRLF with a few LF lines), `testing/PZTestKit/PZTestKit/42/media/lua/shared/PZTestKit_Core.lua`, `testing/PZTestKit/PZTestKit/42/media/lua/server/PZTestKit_Server.lua`, `tools/mod_lint.py`, `tools/tests/test_mod_lint.py`, `testing/fixtures/default/fixture.json` and the `references/wiki-mirrors/` pages; edit them with `newline=''` handling and preserve the endings, and check any other file with `file <path>` first.
- `core.autocrlf=true` here; `.gitattributes` pins the `TKX_ItemOverride` translation file to CRLF and `docs/reference/**` and `.claude/**` to LF.
- A stray `ProjectZomboid64.exe` predating a session is Angus's own client, never killed (§ 5).
- The harness client runs `-debug`, so an unguarded mod Lua error parks it in the debugger: [the raising-probe rule](docs/platform/lessons.md#rules).
- The workshop corpus drifts under a running session, so every count is dated: [the corpus-drift rule](docs/platform/lessons.md#corpus-drift).

## 8. Memory

The memory file is `C:\Users\Angus\.claude\projects\C--Users-Angus\memory\pz-nutrition-mod-project.md`, indexed by the `MEMORY.md` beside it; update both at every plan's close. Angus's standing rules sit beside it in `git-commit-style.md` and `pz-harness-iteration.md`.

## 9. Restructure status and resume point

Transitional: this section is removed at the Phase 4 close.

- The research program closed at the tag `research-program-v1`; the restructure runs under the spec `docs/superpowers/specs/2026-09-17-reference-restructure-design.md`, which is the authority until the cut.
- Phase 1 (the claims register, the checker, the generator) closed: `79c7969..c37d007`, close `77e923f`; ledger `.superpowers/sdd/restructure-1-register/progress.md`.
- Phase 2 (`docs/platform/` and `docs/facts/`) closed: `e8ebc2c..81407e9`, close `74bb475`; ledger `.superpowers/sdd/restructure-2-platform-facts/progress.md`.
- Phase 3 (`docs/areas/`, the skills, the roots, the datasets and tools pages) closed: `<Phase 3 range>`; ledger `.superpowers/sdd/restructure-3-areas-skills-roots/progress.md`.
- Phase 4 next: write `docs/superpowers/plans/restructure-4-cut.md` with `superpowers:writing-plans` from the spec § Execution Phase 4 — the wall-map move with its `Ev`-cell rewrite from the `old section -> ids` map (`python tools/claims_check.py --section-map`), `artifacts.md` moved whole with `Cited by` regenerated, the wiki-mirror contradiction table, the deletion of the old docs, ledgers and plans by pathspec in one commit, the acceptance run, every lint without `--partial`, the fresh-session skill test, the push — taking the Phase 4 obligations in `.superpowers/sdd/restructure-3-areas-skills-roots/deferred-minors-3.md` as inputs; then run it as § 6 describes.
- The wall map (`docs/modding/wall-map.md`) and the artifacts register (`testing/artifacts/README.md`) move into `docs/reference/` at the cut, as `wall-map.md` and `artifacts.md`.
- `docs/vanilla/`, `docs/modding/`, `docs/mods-survey/` and `docs/testing/` are the pre-restructure docs: readable until the cut, and forever at the tag `research-program-v1`.
- `docs/progress.md` and `docs/decisions.md` are frozen: never extend them; rulings go in the plan's ledger.
