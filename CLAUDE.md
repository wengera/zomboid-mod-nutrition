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
| performance, hitching or the server cost of a change | [platform/performance](docs/platform/performance.md) → [platform/lessons#rules](docs/platform/lessons.md#rules) → [platform/server-lifecycle#tick-order](docs/platform/server-lifecycle.md#tick-order) → [platform/harness](docs/platform/harness.md) | `pz-modding-platform` |
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

Rule 6 (Angus, 2026-10-07): the mod's goal is no noticeable hitching at the 60-player design load; per-tick work is admitted only where a measurement shows it reduces hitching, and a design is judged by its worst server frame and how often that frame comes. The method is [platform/performance#budget](docs/platform/performance.md#budget); the thresholds are Plan 10c's ruling 2, in its plan.
The skills under `.claude/skills/` route the same way: each description fires on its row's task shape, and its `## Read first` opens that row's pages.
The pre-restructure library is readable at the tag `research-program-v1`, and the restructure's own spec and plans at the parent of the cut commit `9dfc74b`.

## 2. Ground truth

- **Build:** `42.21` since 2026-10-08 (the server prints `version=42.21.0 4a0e9546ec`; Steam buildid `25485521`) · jar `4a0e9546ec`; a claim holds on the build it was read on — 42.20.4 (jar `b0bbce05d5`) for every row unless its bound says it was re-read on 42.21 — and is re-read on any other; the food dataset is the 2026-10-08 scan of 42.21.0, and the item pass reaches a later build's foods only after a re-scan; both fixtures (`default`, `two`) are provisioned on 42.21.0.
- The local install `D:\SteamLibrary\steamapps\common\ProjectZomboid` and the workshop folder `D:\SteamLibrary\steamapps\workshop\content\108600` are read-only, always.
- The jar toolchain lives at `C:\Users\Angus\pz-b42`: read its `WORKSPACE.md` first, treat it as read-only from here, and verify every Java claim through `./pz.sh grep|methods|refs|dump <class> [method]`; [platform/jar-research](docs/platform/jar-research.md) turns a reading into a citable claim.
- The library is dedicated-server multiplayer evidence; single-player is never claimed.
- Owner: Angus. Remote: `https://github.com/wengera/zomboid-mod-nutrition.git`, branch `main`; pushes work from this checkout.

## 3. Gates before any commit

Run every gate a commit's paths trigger; each ends at zero findings or green.

- `python tools/claims_check.py --staged` → 0 findings before every commit that touches `docs/`, `.claude/skills/`, `testing/PZTestKit/`, `testing/artifacts/`, `testing/experiments/`, `tools/bus_inventory.py`, `tools/reference_gen.py` or `references/wiki-mirrors/` (it says so and skips when nothing staged is under those paths).
- `python tools/science_check.py --staged` → 0 findings before every commit that touches `docs/reference/science.tsv` (it says so and skips otherwise); `python tools/science_check.py --scan mod` → 0 findings before any commit that touches `mod/`, and it is never pointed at `tools/` or `docs/`.
- `python tools/mod_lint.py mod/NutritionRevamp` → 0 ERROR before any commit that touches `mod/`.
- `python tools/release_pack.py check mod/NutritionRevamp` → 0 ERROR before any commit that touches `mod/`.
- `python tools/kahlua_lint.py mod testing/experiments testing/PZTestKit` → 0 findings and `python tools/hotpath_lint.py mod` → 0 findings before any commit that touches `mod/`, an experiment mod or the harness mod.
- `python tools/page_lint.py <the pages touched>` → 0 before any commit that touches a page under `docs/areas/`, `docs/platform/` or `docs/facts/`, or `docs/reference/datasets.md` or `docs/reference/tools.md` (those two under its reference profile).
- `python tools/doc_lint.py docs/reference/wall-map.md references` → 0 before any commit that touches the wall map or `references/`.
- `python tools/reference_gen.py cited-by --check` and `python tools/reference_gen.py contradictions --check` → in sync: the artifacts register's `Cited by` column and the mirrors' `## Contradictions` section are rendered from the register, the checker's rule 10 runs both (so `claims_check.py --staged` covers a commit touching the register, `docs/reference/artifacts.md` or `references/wiki-mirrors/`), and `--write` in place of `--check` regenerates them.
- `python tools/bus_inventory.py --check` → in sync after any harness edit.
- `PYTHONIOENCODING=utf-8 python tools/claims_check.py` (the full run, not `--staged`) → 0 after any commit that touches `mod/` or `tools/README.md`: a mod edit shifts the register's `repo:mod/…` pointers and the staged gate does not trigger on `mod/` (Plan 5: #3012 after 6307559).
- `python tools/food_nutrients.py --check` → in sync before any commit that touches `data/food-nutrient-map/`, `data/fdc-extract.json`, `data/food-nutrients.*`, the generated mod files (`NR_Data_Nutrients.lua`, `NR_Data_Infer.lua`, `NR_ItemPass_Food.txt`) or the tool; `--write` regenerates, and a generated file is never edited by hand.
- `python tools/recipe_conservation.py --check` → in sync before any commit that touches `data/recipes.json`, `data/food-nutrients.*`, `data/recipe-conservation.json` or the tool; recipe conservation is a report, never a fix (Plan 11a rulings T16-3, T17-1).
- `python -m pytest tools/tests testing/tests -q` green: 3473 passed on 2026-10-09 at the Plan 11e close; 3340 at the Plan 11d close (the cleanup of Task 9b deleted tests of removed compatibility code by name); 3264 passed on 2026-10-08 at the Plan 11c close (reset by name in that plan, rulings T6-1 and T9-1: deleted tests of the retired stomach and Task 15 satiety code); 2979 at the Plan 11a close (the baseline reset by name twice in that plan, rulings T8-1 and T14-1: deleted tests of dead code, never live code; 2637 at the Plan 10c close; 2634 at the Plan 10 and 10b closes; 2544 at the Plan 9 close; 2506 at the Plan 8 close; 2416 at the Plan 7 close; 2100 at the Plan 6 close; 1855 at the Plan 5 close; 1552 at the Plan 4 close on 2026-10-05, 1216 at the Plan 3 close, 676 at the Plan 2 close the same day; 489 at the 2026-10-04 Plan 1 close), and the count never drops.

## 4. Extending the reference

A claim is minted in the commit that lands its evidence, never later.

1. **A new measurement:** the run's JSON is copied byte-identical to `testing/artifacts/<run-id>/` with a row in the artifacts register (run id · file · what it measured · its reading guide) and its keys in `docs/reference/do-not-cite.csv` (empty allowed; a listed key is never cited); the same commit adds the register rows and the tagged sentences on their owner pages, green under the checker; the artifact-row commit re-runs the full checker and re-anchors the `artifacts.md` pointers its new row shifts.
   An artifact may land in its own controller commit, with its artifacts row, its do-not-cite rows and its re-anchor; its register rows then follow at the task's mint within the same plan, and a row is never minted before its owner sentence (rulings M-1, D-1).
2. **Ids:** the next unused id; the checker fails a duplicate or a gap; a parallel SDD wave reserves an id block per task in its ledger before dispatch; a wave whose writers never touch the register reserves no block, because the controller mints serially from the delta files at the wave's close.
3. **Settling an open row:** the row keeps its id and goes `open -> settled` with its pointer and bound filled; the owner sentence is rewritten to the settled form, its line leaves `docs/areas/open-questions.md`, and its rows in `docs/reference/experiments.md` and the wall map's experiment table are marked `run <run-id>`; a reading that comes back unmeasured or trivial stays `open` with the run named in `bound`.
4. **Superseding:** a claim a run overturns keeps its id and goes `superseded` with `successor`; every page tagging it moves to the successor in the same commit.
5. **A harness change** (a new `TK.register`, a changed reply) lands in its own commit with its comment block, `tools/luabalance.py` green and `tools/bus_inventory.py` regenerating `docs/reference/harness-commands.md`, before the run that uses it.
6. **A rule line edit** re-syncs the skills that quote it in the same commit; the checker fails otherwise.
7. **Who runs the checker:** the committer, `--staged`, before every commit that touches its trigger paths (§ 3); an SDD reviewer re-runs it on the review package.
8. **A science number:** a value the mod ships rests on a `settled` row of `docs/reference/science.tsv`; a writer files rows in a part file the controller applies with `tools/science_delta.py`, and every settled row's citation was resolved against its record before minting; the page is [reference/science](docs/reference/science.md).
9. **A live row's text:** every number in a claim sits at a path its pointer names, unrounded beyond the sample; a mechanism read off the mod's own code is written in the bound as inference, never as the claim; the checker does not match a wildcard `do-not-cite` key (`phases.*.watch.raw`), so a wildcard is a review check (the five Plan 4 live reviews each returned five to nine such defects). A pointer never names a parent of a do-not-cite key nor a verdict-level copy of one (the checker flags neither): the reviewer checks parents by hand, and every Plan 8 live review found such parents on the first pass.
10. **The apply tool rewrites plain provisional tags only:** a suffixed tag (`[T4.1/M/n=1]`) or a `#T4.1` form is rewritten by the controller by regex over every touched page, `experiments.md` included. The controller's regex runs over the touched pages only, never the register (old bounds carry stale provisional refs) and never `docs/superpowers/` (a plan record carries its own T-numbering, Plan 7 Task 4), and its `[##` cleanup matches tag brackets only (it hit a heading link once); a provisional ref also sits INSIDE a combined bracket (`[#3315/M/n=1, T7.1/C/inference]`, the rule-row form), so the regex matches `T<n>.<m>` before a `/` anywhere, not only after `[` (Plan 9 Task 7).

## 5. Harness rules

The instrument is [platform/harness](docs/platform/harness.md) (the run procedure is its [`## Procedure`](docs/platform/harness.md#procedure)); the command table is [reference/harness-commands](docs/reference/harness-commands.md).

- `python testing/pzt doctor` before every boot.
- A release profile boots the STAGED copy (`tools/release_pack.py stage`), never `mod/` directly, so the bytes a server would download are the bytes under test (x201).
- A release client raised on once (x202) answered through the raise, and the `-debug` client parked, so the server-side gate stays: [platform/lua-platform#debug-break](docs/platform/lua-platform.md#debug-break).
- `pzt run`, `pzt provision` and `pzt scenario` run the layout lint on every `path=` mod folder and stop on an ERROR before seeding (Plan 9 Task 3).
- One live game session at a time, repository-wide.
- A live session boots only with at least 12 GB of host memory free, read and ledgered before the boot. A driver longer than about 15 minutes of wall time is split into separate sessions, each with its own driver: Claude Code's background-shell reaper killed x242 mid-run for memory, and the 60-ghost sessions took free memory down to 0.55 GB (Plan 10c ruling H2-1).
- A two-client run is one session: `pzt run` attaches the profile's `clients` one at a time, each ready before the next (Plan 8 Task 1).
- Never `-safemode`.
- A harness change lands before the run that uses it, in its own commit, with the balance check (`python tools/luabalance.py <lua files>`, the HEAD copies first, then the working tree) and the command table regenerated (`python tools/bus_inventory.py`); the next acceptance run is its smoke test.
- A driver (`testing/experiments/*.py`) is never edited after its run; a post-run edit is a skew note.
- A driver's run prefix and profile constants name its own file and profile, checked before its commit: in Plan 10c, x243b ran under x243a's prefix and profile, so its artifact folder is `x243a-20261007-162255`.
- A driver's store read precedes its write by at most one slow minute when the legacy mirror is on, or the landing measures the mirror's rewrite (x193's D; the rule is on [areas/testing-your-mod#rules](docs/areas/testing-your-mod.md#rules)).
- A reading that comes back trivial, unmeasured or falsified is written as such and never re-run to make a number prettier.
- An aborted boot that took no reading is not a run: its driver runs unchanged and its run folder is left as is (ruling B3-1, x151r2's first attempt, killed by the host for memory).
- A driver that crashes before any reading is taken (a TypeError at its first phase) is not a run either, and the one edit that fixes the crash is allowed before the real run, named in the artifact's reading guide — distinct from a host kill, where the driver runs unchanged (ruling B3-2, x171p's first attempt).
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
- Row `#2808` is the living harness-inventory count tethered to the generated command table: a harness commit that changes the table's count line updates `#2808`'s claim text and quote, and `#1235`'s quote, in the same commit (rule 3b fails otherwise) — the one register edit a harness implementer may make.
- A profile's `[server]` keys (`SleepAllowed`, `SleepNeeded`) reach the server ini at seed; the fixture's default is false/false, so a sleep reading needs a profile that sets both true (x151s).
- `lua.setpath` (both sides since Plan 7) is the drivers' only setter of a plain Lua field (a dotted-path scalar from `_G`; `globalmoddata.setpath` assigns into a global modData table) and `lua.call` (both sides) the only caller of a plain Lua function with up to four scalar arguments; no chunk runner exists because `loadstring` is removed on 42.20.x.
- A driver's server-log pattern excludes its own probe names: the harness echoes a client-side probe's name into the server log, and a grep for it reads the echo as a hit (x183's arm I, falsified twice by its own grep).

## 6. Process

- Every plan runs with `superpowers:subagent-driven-development`; `superpowers:writing-plans` writes a plan, `superpowers:brainstorming` opens any new design, and `superpowers:verification-before-completion` precedes any claim that work is done. A spec or plan is written under `docs/superpowers/` (the directory is recreated when needed), tracked while its program runs, and kept after its close as the program record together with its research reports (the 2026-10-05 ruling, following the precedent every plan so far has set); the pages and the register are what a reader cites.
- Fable leads on the main thread; every implementer and reviewer is a fresh subagent with its model named in the dispatch (`model:` always specified), sized to the task (Angus, 2026-10-04) and run on the current 5.x models (Angus, 2026-10-05): the high-stakes tier — a harvest, a live citation or evidence read, a whole-pass review or any task where a fabrication would pass unnoticed — passes `model: "opus"` (Opus 5.5); the spelled-out tier — a task whose code, tests or edits the brief spells out, a scoped re-review of a small fix diff, a root-file edit — passes `model: "sonnet"` (Sonnet 5.5). The Agent picker offers only family aliases with no version pin, so the version each alias lands on is set by the Claude Code default-model config; both aliases were verified on 2026-10-05 by the subagents' own model-id reports (`claude-opus-5-5`, `claude-sonnet-5-5`), and every dispatch asks the subagent to report its exact model id in its return — one that comes back on an older version is re-dispatched, never kept. The controller ledgers the sizing per wave; if a tier's model is rate-limited, wait for the reset or ask Angus which model to substitute — never downgrade silently.
- The skill lives at `C:\Users\Angus\.claude\plugins\cache\superpowers-marketplace\superpowers\6.3.0\skills\subagent-driven-development\`: `scripts/sdd-workspace PLAN_FILE` creates the plan's workspace, `scripts/task-brief PLAN_FILE N` writes a task brief, and `scripts/review-package PLAN_FILE BASE HEAD` builds a review diff for a contiguous range.
- Per-plan ledgers `.superpowers/sdd/<plan-basename>/progress.md` (gitignored) are the only ledgers, and the whole per-plan workspace beside them (briefs, reports, deltas, review packages) is kept, never deleted, whatever the skill's cleanup step says. The first line names the plan; every dispatch, report, review and ruling is a line in it; after compaction trust the ledger and `git log`, not memory; a task with a `Task <N>: complete` line is done, and work resumes at the first task without one.
- Per task: the controller writes `task-N-amendments.md` (what the brief cannot know) → a fresh implementer writes `task-N-report.md` and returns only status, commit, one line of verification and concerns → the review package is `review-tN.diff`, `git show -U8` of the task's own commits with artifact JSON excluded → a fresh read-only reviewer checks spec compliance and quality → each fix round is a fresh implementer with `task-N-fix-K-brief.md` → a scoped re-review → the controller applies tiny residuals → `Task N: complete`.
- A dispatch names only briefs and amendments already on disk. The controller writes them with the Write tool and lists them before dispatching: in Plan 10c, two agents were dispatched against files a failed heredoc never wrote.
- A plan closes after a whole-pass review, one consolidated fix wave and its re-review: the controller runs § 3, pushes, and updates this file and the memory file (§ 8).
- Rulings are written `Ruling: <what> — <why> — cost if wrong: <…>`. A ruling about the platform becomes a rule on [platform/lessons](docs/platform/lessons.md) with its mechanism row; a ruling about how this repository works becomes a rule in this file; a ruling a later agent must know is never only a ledger row.
- Commits are pathspec commits (`git commit -m "…" -- <paths>`), never `--amend`, with no Claude attribution and a succinct subject line; implementers never push — the controller pushes at a plan's close.
- Proceed to completion and ledger each decision for review instead of asking; ask only before a destructive action or one outside this worktree.
- A mapping curator's fix round that is small and spot-checked by the controller on its diff takes no separate re-review when the close's whole-pass review re-samples the merged data (Plan 6 ruling T4-11).
- Implementers run in parallel only on disjoint files; reviewers are read-only, may overlap anything, and read an implementer's committed content with `git show <commit>:<path>`; research subagents are sent off as the work goes.
- In a delta a `supersede` names its successor in the `successor` cell; the add row may sit anywhere.
- The register is read-only for page writers: a new or changed claim is a delta file the controller applies with `tools/claims_delta.py`, and a writer never runs `claims_check.py --fix-tags` (the controller runs it once per wave close).
- A `status` row in a delta writes only `status` and `bound`: a correction pass that changes a claim, pointer, grade or kind is applied with `tools/claims_delta.py apply` AND the controller's fill step that copies those cells from the delta (the Plan 5 gate-1 lesson: every Plan 4 correction pass had landed status and bound only, and the claim and pointer cells were replayed at a8fc4b2); a verified apply re-reads one corrected claim from the register before committing.
- A `status` row's bound starts with the register's current bound byte for byte, copied from `claims.tsv` as UTF-8 and never through a re-encoding console. The controller diffs that prefix before the apply, because the dry run does not catch a mojibake bound (Plan 10c, #3419).
- An added `rule` row (an area page's own imperative) rests on register rows: its pointer is a C pointer copied from a row it rests on, its bound reads `inference; a reading of <ids>`, and its page line carries the resting row's tag beside its own; a rule resting only on M rows takes a `repo:` pointer to the line that carries its clause (ruling T15-1).
- A rule copied from a page that states it outside `## Rules` is copied byte-identically and diffed by hand at review, because the checker's `rules-dup` rule reads `## Rules` lines only.
- A skill's quoted rule line keeps the row's numbers; the skill's own text carries none.
- A register `source` cell is harvest provenance and is never renumbered when the doc it names is rewritten.
- A subagent never runs `git stash`, `git checkout --`, `git reset` or any index-wide command in the shared worktree; it commits by pathspec only, and retries once after two seconds on `.git/index.lock`.
- A controller fix after a FAIL takes a scoped re-review unless the fix is a pointer-only, comment-only or tag-only edit that the full checker and the gate it fell under verify mechanically; a wording change to a claim always takes one (ruling T9-1, Plan 8).
- A fix round's wording re-review may be deferred to the next whole-delta review before the mint, but only when the ledger names the deferral and that review lists each deferred item as passed (Plan 10c rulings H2-2, H4-3, H5-1).
- A `C/inference` row whose evidence is the mod's own line may own an area-page sentence when the sentence states what a mod can do and the mod's line is the worked example (ruling T12-1, Plan 7).
- The controller runs a test in its own call and never chains a commit after it in one command: a chained command commits past a red test (Plan 7's icon_gen residual took three commits).
- Lanes and worktrees (Plan 11a ruling 1): one serial lane edits `mod/` Lua, kernel tests and files the kernel host loads; a docs lane may run beside it; a pure-kernel or docs-only task may run in a worktree. A worktree task reaches `main` only by the controller's `git cherry-pick` after its `Task N: complete` line — the one allowed non-pathspec commit form, run by the controller alone, in its own call, with no shared-tree implementer mid-commit and `git diff --cached --quiet` exiting 0; a conflict is aborted and ruled on. A fix round for a worktree task runs in a fresh worktree that cherry-picks the task's commits first; a fresh worktree may run `git merge --ff-only main` once before any edit (ruling W-1).
- A game update is re-baselined before any build work (Plan 11a ruling 17, Task R): inventory every row the plans, the mod and the area rules cite; re-read each on the new jar with `tools/jar_recheck.py` (holds → a bound note; moved → re-anchor; changed → supersede and move its pages); re-scan the food and recipe data; re-provision both fixtures; run one smoke against the previous slow-minute reading; update § 2.
- Code the mod has removed is cited with a pinned-commit pointer, `repo:<path>@<commit>:<line> "<quote>"`, which `claims_check` resolves through `git show`; pin to the last commit holding the code the claim describes, never a later one (the first #3456 pin chose a commit already past the change, Plan 11a's wave close).
- A mutation is run on a scratch copy (`git archive HEAD | tar -x -C <scratch>`), never on a tracked file restored afterwards: three Plan 11a fix rounds mutated tracked files.
- No engine mechanism is asserted in a question to Angus without a register row or a jar read behind it: the chips question offered a same-name `craftRecipe` override, which appends on 42.21 (Plan 11a Task 16).
- A refactor of the server adapters is proven by the golden trace (`testing/tests/kernel/test_golden_trace.py`) reproduced byte for byte. The trace is re-recorded only by a plan that names the behaviour change it records, in the same commit; an oracle's own review rounds may re-record it from a frozen tree until the first refactor commit lands (Plan 10 rulings 3 and R0-1).
- An oracle (a golden trace, a property harness) is accepted only after a mutation pass: its reviewer patches the code it guards and shows each plausible change fails it; Plan 10's first trace missed six of seventeen mutations.
- A commit that adds an artifacts-register row re-anchors, in the same commit, every `repo:docs/reference/artifacts.md:` pointer the row shifts (`#1254`, `#1504` and any other the full checker names); five Plan 10 artifact commits left the checker red until a follow-up; an implementer who may not edit the register stages the artifact files and hands the commit to the controller, who folds the re-anchor in (Plan 10b: 061630a needed 5e0b230).
- A commit named in a page, a row or a brief takes its plan label from `git log -1 --format=%s <sha>`, never from memory: Plan 11c's Task 10 brief labelled 42784ff "Plan 11a" and the review caught it (it is Plan 10's).
- The mod is unreleased: no migration, store version, legacy-field drop or compatibility fallback for an older save is written, and any found is removed; a corrupt file heals to a fresh record instead (Angus, 2026-10-09; Plan 11d Task 9b, ruling C9-10). The rule lapses at the first release.
- A task whose change reaches the golden trace re-records it in its own commit under a named cause, every moved leaf attributed, so every commit stays green; a plan names its changes, not one re-record (Plan 11d ruling T2-1).
- A task that changes the line a register claim quotes, before the task that rewrites the claim, pins that pointer to the last commit holding the line (`repo:<path>@<commit>:<line>`), keeping the full checker at 0; the rewrite task removes the pin (Plan 11d rulings T7-3 and T1-4).
- The controller reads the checker's findings count before committing and stops on a non-zero count; a grep of the count in a chained command is not a gate (Plan 10: 1de05d0, 8593c10).

## 7. Environment gotchas

- `release/` is gitignored staging; `preview.png` beside the staged item is Angus's to supply, 256×256 (absent on 2026-10-06; `stage` WARNs).
- The Bash tool's cwd resets between calls: `cd /c/Users/Angus/repos/project_zomboid` in every call, or edits land in the home directory.
- Long Bash heredocs with apostrophes fail to parse: write briefs and long files with the Write tool, and keep Bash-embedded Python apostrophe-free.
- CRLF survivors in the working tree: `tools/README.md` (CRLF with a few LF lines), `tools/mod_lint.py`, `tools/tests/test_mod_lint.py`, `testing/PZTestKit/PZTestKit/42/media/lua/shared/PZTestKit_Core.lua`, `testing/PZTestKit/PZTestKit/42/media/lua/server/PZTestKit_Server.lua`, `testing/experiments/s03_body.py`, `testing/fixtures/default/fixture.json` (which `file` reports as JSON without naming its endings) and the `references/wiki-mirrors/` pages; edit them with `newline=''` handling and preserve the endings, and check any other file with `file <path>` first.
- `core.autocrlf=true` here; `.gitattributes` pins the `TKX_ItemOverride` translation file to CRLF and `docs/reference/**` and `.claude/**` to LF.
- PNG files under `mod/` (`mod/**/*.png`) are pinned `binary` in `.gitattributes`: autocrlf rewrote six PNG blobs once (Plan 7 Task 9).
- A stray `ProjectZomboid64.exe` predating a session is Angus's own client, never killed (§ 5).
- `lupa` 2.8 is the kernel tests' Lua 5.1 host (`python -m pip install lupa==2.8`), and the kernel coverage gate is line-granular, so the kernel files `NR_Kernel*.lua` are written one statement per line.
- The harness client runs `-debug`, so an unguarded mod Lua error parks it in the debugger: [the raising-probe rule](docs/platform/lessons.md#rules).
- The workshop corpus drifts under a running session, so every count is dated: [the corpus-drift rule](docs/platform/lessons.md#corpus-drift).

## 8. Memory

The memory file is `C:\Users\Angus\.claude\projects\C--Users-Angus\memory\pz-nutrition-mod-project.md`, indexed by the `MEMORY.md` beside it; update both at every plan's close. Angus's standing rules sit beside it in `git-commit-style.md` and `pz-harness-iteration.md`.
