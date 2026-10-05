# CLAUDE.md — the agent handoff and router

Read §§ 1–3 before touching anything, § 5 before any live run, and § 6 before running a plan.

## 1. What this repo is

This repository is an agent-facing reference for modding Project Zomboid Build 42; its first consumer is a realism nutrition mod — nutrients tracked mod-side beyond the vanilla macros, a rebalance of the vanilla food items, multiplayer first — whose tree is `mod/NutritionRevamp/` here.
[docs/areas/](docs/areas/) is the nutrition lens, [docs/platform/](docs/platform/) general modding knowledge, [docs/facts/](docs/facts/) the measured vanilla food and nutrition mechanics, and [docs/reference/](docs/reference/) the claims register and the science register of cited nutrition-science values, with the datasets, tools, experiments, jar notes, generated harness commands, wall map and artifacts register.
Every claim on a page carries a tag naming its row in [the register](docs/reference/claims.tsv), and the row carries the grade and the pointer to its evidence; [README.md](README.md) is the map and the tag grammar, [STRATEGY.md](STRATEGY.md) the charter.
The pages state what the game does and what a mod can and cannot change; the mod's design is not in this tree, and a root file names pages, never claims.

Route a task by its shape and read the pages in the order given; stop when the task is answered.

| Task shape | Pages, in reading order | Skill |
|---|---|---|
| add a mod nutrient | [areas/new-nutrients](docs/areas/new-nutrients.md) → [platform/mp-model](docs/platform/mp-model.md) → [facts/wire-packets](docs/facts/wire-packets.md) | `nutrition-new-nutrients` |
| override a vanilla food | [areas/item-pass](docs/areas/item-pass.md) → [platform/loader-and-scripts](docs/platform/loader-and-scripts.md) → [facts/food-item-model](docs/facts/food-item-model.md) | `nutrition-item-pass` |
| hook eating or cooking | [areas/eat-and-cook-hooks](docs/areas/eat-and-cook-hooks.md) → [platform/lua-platform#script-hooks](docs/platform/lua-platform.md#script-hooks) → [facts/eating-pipeline](docs/facts/eating-pipeline.md) | `nutrition-eat-and-cook-hooks` |
| drive a stat, a perk level, a trait, health or carry capacity from mod state | [areas/body-effects](docs/areas/body-effects.md) → [facts/character-stats](docs/facts/character-stats.md) → [facts/body-and-weight](docs/facts/body-and-weight.md) → [facts/perks-and-strength](docs/facts/perks-and-strength.md) → [platform/lua-platform#hooks](docs/platform/lua-platform.md#hooks) | `nutrition-body-effects` |
| sync mod state | [areas/mp-sync](docs/areas/mp-sync.md) → [platform/mp-model](docs/platform/mp-model.md) → [facts/wire-packets](docs/facts/wire-packets.md) | `nutrition-mp-sync` |
| the server's player lifecycle or global modData | [platform/server-lifecycle](docs/platform/server-lifecycle.md) → [areas/mp-sync](docs/areas/mp-sync.md) | `nutrition-mp-sync` |
| show a value or a moodle | [areas/ui-and-moodles](docs/areas/ui-and-moodles.md) → [platform/lua-platform#registries](docs/platform/lua-platform.md#registries) | `nutrition-ui-and-moodles` |
| build a panel, a keybind, a tooltip line or a character-info tab | [platform/client-ui](docs/platform/client-ui.md) → [areas/ui-and-moodles](docs/areas/ui-and-moodles.md) | `nutrition-ui-and-moodles` |
| package or ship | [areas/packaging](docs/areas/packaging.md) → [platform/mod-anatomy](docs/platform/mod-anatomy.md) | `nutrition-packaging` |
| declare or read a sandbox option | [platform/sandbox-options](docs/platform/sandbox-options.md) → [areas/testing-your-mod](docs/areas/testing-your-mod.md) | `pz-modding-platform` |
| test a mod live | [areas/testing-your-mod](docs/areas/testing-your-mod.md) → [platform/harness](docs/platform/harness.md) → [reference/harness-commands](docs/reference/harness-commands.md) | `nutrition-testing-your-mod` |
| run or change the harness | [platform/harness](docs/platform/harness.md) → [reference/harness-commands](docs/reference/harness-commands.md) → § 5 | `pz-mod-testing` |
| answer from the jar | [platform/jar-research](docs/platform/jar-research.md) → [reference/jar-method-notes](docs/reference/jar-method-notes.md) | `pz-jar-research` |
| a PZ modding task outside nutrition | [platform/overview#coverage](docs/platform/overview.md#coverage) → the platform page its [routing table](docs/platform/overview.md#routing) names | `pz-modding-platform` |
| work on the mod's code | [areas/testing-your-mod](docs/areas/testing-your-mod.md) → [platform/lessons#rules](docs/platform/lessons.md#rules) → the mod's tree `mod/NutritionRevamp/` | `nutrition-testing-your-mod` |
| a vanilla food, body, spoilage or cooking number | [platform/overview#routing](docs/platform/overview.md#routing) → the facts page it names | — |
| what another mod already does | [facts/other-mods/catalog](docs/facts/other-mods/catalog.md) → that mod's own page | — |
| a standing rule or an anti-pattern | [platform/lessons](docs/platform/lessons.md) | — |
| a dataset column | [reference/datasets](docs/reference/datasets.md) | — |
| a tool | [reference/tools](docs/reference/tools.md) | — |
| what is still open | [areas/open-questions](docs/areas/open-questions.md) → [reference/experiments](docs/reference/experiments.md) | — |
| cite a nutrition-science value | [reference/science](docs/reference/science.md) → [the register](docs/reference/science.tsv) | — |

The skills under `.claude/skills/` route the same way: each description fires on its row's task shape, and its `## Read first` opens that row's pages.
The pre-restructure library is readable at the tag `research-program-v1`, and the restructure's own spec and plans at the parent of the cut commit `9dfc74b`.

## 2. Ground truth

- **Build:** `42.20.4` · jar `b0bbce05d5`; a claim holds on this build and is re-read on any other.
- The local install `D:\SteamLibrary\steamapps\common\ProjectZomboid` and the workshop folder `D:\SteamLibrary\steamapps\workshop\content\108600` are read-only, always.
- The jar toolchain lives at `C:\Users\Angus\pz-b42`: read its `WORKSPACE.md` first, treat it as read-only from here, and verify every Java claim through `./pz.sh grep|methods|refs|dump <class> [method]`; [platform/jar-research](docs/platform/jar-research.md) turns a reading into a citable claim.
- The library is dedicated-server multiplayer evidence; single-player is never claimed.
- Owner: Angus. Remote: `https://github.com/wengera/zomboid-mod-nutrition.git`, branch `main`; pushes work from this checkout.

## 3. Gates before any commit

Run every gate a commit's paths trigger; each ends at zero findings or green.

- `python tools/claims_check.py --staged` → 0 findings before every commit that touches `docs/`, `.claude/skills/`, `testing/PZTestKit/`, `testing/artifacts/`, `testing/experiments/`, `tools/bus_inventory.py`, `tools/reference_gen.py` or `references/wiki-mirrors/` (it says so and skips when nothing staged is under those paths).
- `python tools/science_check.py --staged` → 0 findings before every commit that touches `docs/reference/science.tsv` (it says so and skips otherwise); `python tools/science_check.py --scan mod` → 0 findings before any commit that touches `mod/`, and it is never pointed at `tools/` or `docs/`.
- `python tools/mod_lint.py mod/NutritionRevamp` → 0 ERROR before any commit that touches `mod/`.
- `python tools/kahlua_lint.py mod testing/experiments testing/PZTestKit` → 0 findings and `python tools/hotpath_lint.py mod` → 0 findings before any commit that touches `mod/`, an experiment mod or the harness mod.
- `python tools/page_lint.py <the pages touched>` → 0 before any commit that touches a page under `docs/areas/`, `docs/platform/` or `docs/facts/`, or `docs/reference/datasets.md` or `docs/reference/tools.md` (those two under its reference profile).
- `python tools/doc_lint.py docs/reference/wall-map.md references` → 0 before any commit that touches the wall map or `references/`.
- `python tools/reference_gen.py cited-by --check` and `python tools/reference_gen.py contradictions --check` → in sync: the artifacts register's `Cited by` column and the mirrors' `## Contradictions` section are rendered from the register, the checker's rule 10 runs both (so `claims_check.py --staged` covers a commit touching the register, `docs/reference/artifacts.md` or `references/wiki-mirrors/`), and `--write` in place of `--check` regenerates them.
- `python tools/bus_inventory.py --check` → in sync after any harness edit.
- `python -m pytest tools/tests testing/tests -q` green: 676 passed on 2026-10-05 (489 at the 2026-10-04 Plan 1 close), and the count never drops.

## 4. Extending the reference

A claim is minted in the commit that lands its evidence, never later.

1. **A new measurement:** the run's JSON is copied byte-identical to `testing/artifacts/<run-id>/` with a row in the artifacts register (run id · file · what it measured · its reading guide) and its keys in `docs/reference/do-not-cite.csv` (empty allowed; a listed key is never cited); the same commit adds the register rows and the tagged sentences on their owner pages, green under the checker; the artifact-row commit re-runs the full checker and re-anchors the `artifacts.md` pointers its new row shifts.
2. **Ids:** the next unused id; the checker fails a duplicate or a gap; a parallel SDD wave reserves an id block per task in its ledger before dispatch; a wave whose writers never touch the register reserves no block, because the controller mints serially from the delta files at the wave's close.
3. **Settling an open row:** the row keeps its id and goes `open -> settled` with its pointer and bound filled; the owner sentence is rewritten to the settled form, its line leaves `docs/areas/open-questions.md`, and its rows in `docs/reference/experiments.md` and the wall map's experiment table are marked `run <run-id>`; a reading that comes back unmeasured or trivial stays `open` with the run named in `bound`.
4. **Superseding:** a claim a run overturns keeps its id and goes `superseded` with `successor`; every page tagging it moves to the successor in the same commit.
5. **A harness change** (a new `TK.register`, a changed reply) lands in its own commit with its comment block, `tools/luabalance.py` green and `tools/bus_inventory.py` regenerating `docs/reference/harness-commands.md`, before the run that uses it.
6. **A rule line edit** re-syncs the skills that quote it in the same commit; the checker fails otherwise.
7. **Who runs the checker:** the committer, `--staged`, before every commit that touches its trigger paths (§ 3); an SDD reviewer re-runs it on the review package.
8. **A science number:** a value the mod ships rests on a `settled` row of `docs/reference/science.tsv`; a writer files rows in a part file the controller applies with `tools/science_delta.py`, and every settled row's citation was resolved against its record before minting; the page is [reference/science](docs/reference/science.md).

## 5. Harness rules

The instrument is [platform/harness](docs/platform/harness.md) (the run procedure is its [`## Procedure`](docs/platform/harness.md#procedure)); the command table is [reference/harness-commands](docs/reference/harness-commands.md).

- `python testing/pzt doctor` before every boot.
- One live game session at a time, repository-wide.
- Never `-safemode`.
- A harness change lands before the run that uses it, in its own commit, with the balance check (`python tools/luabalance.py <lua files>`, the HEAD copies first, then the working tree) and the command table regenerated (`python tools/bus_inventory.py`); the next acceptance run is its smoke test.
- A driver (`testing/experiments/*.py`) is never edited after its run; a post-run edit is a skew note.
- A reading that comes back trivial, unmeasured or falsified is written as such and never re-run to make a number prettier.
- Artifacts are committed byte-identical to the run copy: a committed run's files go under `testing/artifacts/<run-id>/` and its row into the artifacts register, [reference/artifacts](docs/reference/artifacts.md).
- A raising probe is gated on the server side with its profile's `[client] timeout` set low, and `pzt run` is expected to fail: the grade comes off the artifact.
- A stray `ProjectZomboid64.exe` predating a session is Angus's own client: never kill it (`doctor` checks game Java only).
- Fixture caches (`testing/fixtures/default/cache/`) and run folders (`testing/runs/`) are per-machine and gitignored.
- Kahlua rules for every harness and experiment Lua file: no `goto`, no `%d` on floats, no `#` on Java lists.
- The experiment mods (`testing/experiments/TKX_*`) are installed only through test profiles, never into the fixture.
- A harness Lua edit appends new sites at the end of its file; an edit that shifts lines re-anchors every `repo:` pointer into that file in the same commit (`claims_check` rule 3b fails otherwise).
- Standing rule: live-server experiments and trial and error are encouraged, and the harness is improved as the work goes whenever that makes a measurement better — before the run, under the rules above.
- A live boot of the mod never overlaps an offline edit under `mod/`: the boot loads the whole tree and a half-saved file parks the `-debug` client; a live task waits for the mod/ tree to be quiescent, and an offline mod/ task waits for the session to end (Plan 2 ruling).
- An acceptance profile for the mod sets `Nutrition = false`, the design's precondition (ruling T18-1; x141b ran without it).
- Row `#2808` is the living harness-inventory count tethered to the generated command table: a harness commit that changes the table's count line updates `#2808`'s claim text and quote in the same commit (rule 3b fails otherwise) — the one register edit a harness implementer may make.

## 6. Process

- Every plan runs with `superpowers:subagent-driven-development`; `superpowers:writing-plans` writes a plan, `superpowers:brainstorming` opens any new design, and `superpowers:verification-before-completion` precedes any claim that work is done. A spec or plan is written under `docs/superpowers/` (the directory is recreated when needed), tracked while its program runs, and kept after its close as the program record together with its research reports (the 2026-10-05 ruling, following the precedent every plan so far has set); the pages and the register are what a reader cites.
- Fable leads on the main thread; every implementer and reviewer is a fresh subagent with its model named in the dispatch (`model:` always specified), sized to the task (Angus, 2026-10-04) and run on the current 5.x models (Angus, 2026-10-05): the high-stakes tier — a harvest, a live citation or evidence read, a whole-pass review or any task where a fabrication would pass unnoticed — passes `model: "opus"` (Opus 5.5); the spelled-out tier — a task whose code, tests or edits the brief spells out, a scoped re-review of a small fix diff, a root-file edit — passes `model: "sonnet"` (Sonnet 5.5). The Agent picker offers only family aliases with no version pin, so the version each alias lands on is set by the Claude Code default-model config; both aliases were verified on 2026-10-05 by the subagents' own model-id reports (`claude-opus-5-5`, `claude-sonnet-5-5`), and every dispatch asks the subagent to report its exact model id in its return — one that comes back on an older version is re-dispatched, never kept. The controller ledgers the sizing per wave; if a tier's model is rate-limited, wait for the reset or ask Angus which model to substitute — never downgrade silently.
- The skill lives at `C:\Users\Angus\.claude\plugins\cache\superpowers-marketplace\superpowers\6.3.0\skills\subagent-driven-development\`: `scripts/sdd-workspace PLAN_FILE` creates the plan's workspace, `scripts/task-brief PLAN_FILE N` writes a task brief, and `scripts/review-package PLAN_FILE BASE HEAD` builds a review diff for a contiguous range.
- Per-plan ledgers `.superpowers/sdd/<plan-basename>/progress.md` (gitignored) are the only ledgers, and the whole per-plan workspace beside them (briefs, reports, deltas, review packages) is kept, never deleted, whatever the skill's cleanup step says. The first line names the plan; every dispatch, report, review and ruling is a line in it; after compaction trust the ledger and `git log`, not memory; a task with a `Task <N>: complete` line is done, and work resumes at the first task without one.
- Per task: the controller writes `task-N-amendments.md` (what the brief cannot know) → a fresh implementer writes `task-N-report.md` and returns only status, commit, one line of verification and concerns → the review package is `review-tN.diff`, `git show -U8` of the task's own commits with artifact JSON excluded → a fresh read-only reviewer checks spec compliance and quality → each fix round is a fresh implementer with `task-N-fix-K-brief.md` → a scoped re-review → the controller applies tiny residuals → `Task N: complete`.
- A plan closes after a whole-pass review, one consolidated fix wave and its re-review: the controller runs § 3, pushes, and updates this file and the memory file (§ 8).
- Rulings are written `Ruling: <what> — <why> — cost if wrong: <…>`. A ruling about the platform becomes a rule on [platform/lessons](docs/platform/lessons.md) with its mechanism row; a ruling about how this repository works becomes a rule in this file; a ruling a later agent must know is never only a ledger row.
- Commits are pathspec commits (`git commit -m "…" -- <paths>`), never `--amend`, with no Claude attribution and a succinct subject line; implementers never push — the controller pushes at a plan's close.
- Proceed to completion and ledger each decision for review instead of asking; ask only before a destructive action or one outside this worktree.
- Implementers run in parallel only on disjoint files; reviewers are read-only, may overlap anything, and read an implementer's committed content with `git show <commit>:<path>`; research subagents are sent off as the work goes.
- In a delta a `supersede` names its successor in the `successor` cell; the add row may sit anywhere.
- The register is read-only for page writers: a new or changed claim is a delta file the controller applies with `tools/claims_delta.py`, and a writer never runs `claims_check.py --fix-tags` (the controller runs it once per wave close).
- An added `rule` row (an area page's own imperative) rests on register rows: its pointer is a C pointer copied from a row it rests on, its bound reads `inference; a reading of <ids>`, and its page line carries the resting row's tag beside its own.
- A rule copied from a page that states it outside `## Rules` is copied byte-identically and diffed by hand at review, because the checker's `rules-dup` rule reads `## Rules` lines only.
- A skill's quoted rule line keeps the row's numbers; the skill's own text carries none.
- A register `source` cell is harvest provenance and is never renumbered when the doc it names is rewritten.
- A subagent never runs `git stash`, `git checkout --`, `git reset` or any index-wide command in the shared worktree; it commits by pathspec only, and retries once after two seconds on `.git/index.lock`.

## 7. Environment gotchas

- The Bash tool's cwd resets between calls: `cd /c/Users/Angus/repos/project_zomboid` in every call, or edits land in the home directory.
- Long Bash heredocs with apostrophes fail to parse: write briefs and long files with the Write tool, and keep Bash-embedded Python apostrophe-free.
- CRLF survivors in the working tree: `tools/README.md` (CRLF with a few LF lines), `tools/mod_lint.py`, `tools/tests/test_mod_lint.py`, `testing/PZTestKit/PZTestKit/42/media/lua/shared/PZTestKit_Core.lua`, `testing/PZTestKit/PZTestKit/42/media/lua/server/PZTestKit_Server.lua`, `testing/experiments/s03_body.py`, `testing/fixtures/default/fixture.json` (which `file` reports as JSON without naming its endings) and the `references/wiki-mirrors/` pages; edit them with `newline=''` handling and preserve the endings, and check any other file with `file <path>` first.
- `core.autocrlf=true` here; `.gitattributes` pins the `TKX_ItemOverride` translation file to CRLF and `docs/reference/**` and `.claude/**` to LF.
- A stray `ProjectZomboid64.exe` predating a session is Angus's own client, never killed (§ 5).
- `lupa` 2.8 is the kernel tests' Lua 5.1 host (`python -m pip install lupa==2.8`), and the kernel coverage gate is line-granular, so the kernel files `NR_Kernel*.lua` are written one statement per line.
- The harness client runs `-debug`, so an unguarded mod Lua error parks it in the debugger: [the raising-probe rule](docs/platform/lessons.md#rules).
- The workshop corpus drifts under a running session, so every count is dated: [the corpus-drift rule](docs/platform/lessons.md#corpus-drift).

## 8. Memory

The memory file is `C:\Users\Angus\.claude\projects\C--Users-Angus\memory\pz-nutrition-mod-project.md`, indexed by the `MEMORY.md` beside it; update both at every plan's close. Angus's standing rules sit beside it in `git-commit-style.md` and `pz-harness-iteration.md`.
