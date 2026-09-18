# CLAUDE.md — handoff for whoever picks this repo up next

Last updated 2026-09-17 (slices 12 and 13 closed; slice 14 in progress). Everything an agent needs to resume seamlessly is here or one hop away. Read this file top to bottom before touching anything.

## 1. What this repo is

A **reference library** for a future Project Zomboid **Build 42** mod: a realism nutrition overhaul with new mod-side nutrients and a full food-item rebalance, **multiplayer-first**. The library is the deliverable of this phase; mod design comes after it. Everything here is *evidence*: what the game does (measured on a live server + client, or read from the decompiled jar), what other mods do, and what a mod can and cannot change.

- Owner: Angus (`asdobson@proton.me`). Remote: `https://github.com/wengera/zomboid-mod-nutrition.git`, branch `main`, pushes work.
- Ground truth: the local **42.20.4** install (jar `b0bbce05d5`) at `D:\SteamLibrary\steamapps\common\ProjectZomboid` and the workshop folder `D:\SteamLibrary\steamapps\workshop\content\108600` — both **read-only, always**.
- Jar toolchain: `C:\Users\Angus\pz-b42` — read its `WORKSPACE.md` first; `./pz.sh grep|methods|refs|dump <class> [method]` is how every Java claim is verified.

## 2. Read these first, in this order

1. `STRATEGY.md` — the charter: goals, method rules, the P1–P5 pillars.
2. `docs/progress.md` — the **board** (one row per slice, status, commit range, outcome), § Resume notes, § Ripples (findings addressed to later slices — not optional).
3. `docs/decisions.md` — the **ledger** of every ruling (five-cell rows; ~200 rows; no index yet).
4. `docs/superpowers/specs/2026-09-09-research-slices-design.md` — the research program spec: 14 question-driven slices in waves, the eight-part plan template, the unattended protocol, the evidence standard, the tooling per wave.
5. The plan of the slice you are resuming (`docs/superpowers/plans/NN-*.md`) and its SDD workspace (`.superpowers/sdd/<plan-basename>/progress.md` — the per-plan ledger; see § 5).
6. `docs/modding/patterns.md` § Measured MP sync facts — the canonical measured facts; `docs/testing/README.md` — the harness and its command bus; `docs/testing/profiles.md` — how a mod goes under test.

## 3. Status snapshot (2026-09-17)

Slices 01–13 are **done and pushed** (12 closed `f36a860..17a683b`, close `75e277c`; 13 closed `2019621..91fda27`, close `c3e60a0`). Slice 14 (feasibility notes) was **closed unrun**: its six design areas are written once as `docs/areas/` by the restructure. The research program is **closed at the tag `research-program-v1`** — everything the program produced (plans, specs, ledgers, the old doc tree) is reachable there forever.

The repo is now being restructured into an agent-facing reference under `docs/superpowers/specs/2026-09-17-reference-restructure-design.md` (APPROVED 2026-09-17). Four phases: 0 close (done at the tag) · 1 the claims register, checker and generator (`docs/superpowers/plans/restructure-1-register.md`) · 2 `platform/` + `facts/` pages · 3 `areas/` + skills + roots · 4 the cut. Until Phase 4 lands, the old tree (`docs/vanilla`, `docs/modding`, `docs/mods-survey`, `docs/testing`) remains the readable reference and `docs/progress.md` / `docs/decisions.md` are frozen — do not extend them; rulings go in the plan's SDD ledger.

## 4. Resume point — do exactly this

1. Read the spec, then the plan in progress (`docs/superpowers/plans/restructure-1-register.md`; later plans are named `restructure-2-…`, `restructure-3-…`, `restructure-4-…`) and its SDD ledger `.superpowers/sdd/<plan-basename>/progress.md`.
2. Run the plan with `superpowers:subagent-driven-development` exactly as § 5 describes. Tasks with a `Task <N>: complete` line are done; resume at the first without one.
3. At each plan's close: run the gates in § 6, push, update this section and the memory file.

## 5. The process — superpowers subagent-driven development (SDD)

Invoke the skill **`superpowers:subagent-driven-development`** at the start of every session that executes a plan (and `superpowers:writing-plans` when a plan must be written; `superpowers:brainstorming` for any new design; `superpowers:verification-before-completion` before claiming anything done). The loop, as this project runs it:

- **Workspace per plan:** `.superpowers/sdd/<plan-basename>/` (gitignored, **kept** for review — never delete). Created by the skill's `scripts/sdd-workspace PLAN_FILE`; task briefs by `scripts/task-brief PLAN_FILE N` (the skill lives at `C:\Users\Angus\.claude\plugins\cache\superpowers-marketplace\superpowers\6.3.0\skills\subagent-driven-development\`).
- **Ledger** `progress.md` in the workspace: first line names the plan; every dispatch, report, review, ruling. Rulings are written `Ruling: <what> — <why> — cost if wrong: <…>`. After compaction, trust the ledger and `git log`, not memory.
- **Per task:** the controller writes `task-N-amendments.md` (what the brief cannot know: interfaces from earlier tasks, corrections, file ownership) → dispatches a **fresh Opus implementer** with the brief + amendments + a report path (`task-N-report.md`; the implementer returns only status / commit / one-line verification / concerns) → builds a **review package** (`review-tN.diff` = `git show -U8` of the task's own commits, artifact JSON excluded) → dispatches a fresh Opus reviewer (read-only; spec compliance + quality; C/M/W lens) → fix rounds are **fresh implementers** with a `task-N-fix-K-brief.md` (SendMessage is unavailable here) → scoped re-review → the controller applies tiny residuals directly → `Task N: complete` in the ledger.
- **Whole-pass review** at the end, one consolidated fix wave, re-review, residuals, then the **close**: the controller flips the board row with a `closeNN.py` (`.superpowers/sdd/_tools/`), removes the resume note, commits `Slice NN: close (board)`, pushes, updates memory.
- **Parallelism:** implementers only on **disjoint files**; reviewers are read-only and may overlap anything; a reviewer running beside an implementer reads committed content via `git show <commit>:<path>`. **One live game session at a time, program-wide.**
- **Commits:** brief subject lines, **no Claude attribution**, **pathspec commits** (`git commit -m "…" -- <paths>`), **never `--amend`** (an amend once rewrote another implementer's commit — decisions ledger). Slices do not push and do not flip their board row; the controller does at the close.
- **Rulings, not questions:** the user's standing instruction is to proceed to completion and ledger decisions for review; ask only for destructive or out-of-worktree actions.
- **Claims files:** for sessions, the controller distils each review into `session-N-claims.md` (claims with grade, bound, artifact key; a DO-NOT-CITE list); doc tasks cite from those, not from raw reports. Reviewer corrections are appended as `## Corrections` and supersede.

## 6. Evidence standard (what every reviewer enforces)

- Grades **C** (code/jar read, `Class.method @offset L<line>` or `path:line`, tree-qualified `common/` vs `42.x/` for mods), **M** (measured: run id + `testing/artifacts/<run-id>/<file>.json` key), **W** (wiki mirror + fetch date, corroboration only). Every claim row in `docs/vanilla`, `docs/modding`, `docs/feasibility`, `docs/mods-survey/teardowns` carries one; `tools/doc_lint.py` enforces the stamp `Verified against: 42.20.4`, a non-empty `## Sources`, no placeholder markers, and a standalone C/M/W letter in every row of any table with an `Ev` header (`M4` fails; `M (run …)` passes).
- Gates before any commit that touches docs: `python tools/doc_lint.py docs/mods-survey docs/modding` → 0; `python tools/doc_lint.py docs/vanilla docs/modding docs/testing references docs/mods-survey/nutrition-mods.md` → 0; `python -m pytest tools/tests testing/tests -q` green (283 at last count; never let it drop).
- Every `~:NN` line cite is **re-located by content** before it is quoted (files move constantly). Every count is dated. Bounds are written down (n, one fixture, one build, dedicated-server path); a bound that is dropped is a defect.
- Artifacts are committed byte-identical to the run copy with a row in `testing/artifacts/README.md`; a driver is never edited after its run (a post-run edit is a skew note); readings that come back trivial / unmeasured / falsified are written as such — never re-run to make a number prettier.
- **Do-not-cite tables** in `testing/artifacts/README.md`: a key with a row is not citable; a key without one is.

## 7. Tooling

- **`pzt`** (`testing/pzt/`): `python testing/pzt doctor` (no java up, ports free, fixture matched — run before every boot), `python testing/pzt run --profile <name> --hold N` (acceptance run), scenarios, `session.verify`. Profiles in `testing/profiles/*.toml` (`fixture`, `[[mods]]` with `id` + `workshop_id` or `path`, `[sandbox]` merged, `[[verify]]` bus probes whose `expect` is a substring of `json.dumps(ack)`, `[client] timeout`). Never `-safemode`.
- **Harness mod `PZTestKit`** (`testing/PZTestKit/PZTestKit/42/media/lua/{shared,server,client}/`): global `TK`, `TK.register(name, fn)`, every Java member through `TK.call` (index-first guard — kept as practice: a caught nil call is silent). The command inventory is `docs/testing/README.md` § Command bus (server `nutrition.*`, `stats.get`, `item.*`, `moddata.set`, `recipes.*` readers, `items.count`; client `eat.action`, `moddata.transmit`; shared `witness.fields`, `witness.moddata`, `lua.global`, `text.get`, `item.script`). **Kahlua rules:** no `goto`, no `%d` on floats, no `#` on Java lists. Harness changes land **before** a live run in their own commit with the README inventory line and the **balance check** (`python .superpowers/sdd/_tools/luabalance.py <lua files>` — bracket deltas + `end`-depth, HEAD copies first, then the working tree); the next acceptance run is the smoke test. Standing rule: iterate on the harness as you go when it makes a measurement better.
- **Drivers** (`testing/experiments/*.py`): the house shape is `td3_autocook.py` / `x121_overrides.py` — provenance keys (`commit`, `harness_lua_commit`, `harness_lua_dirty`, `doctor_clean`, `acceptance_run`), client-first paired reads, wall-bracketed steps with measured offsets, `field_count` asserts, the re-ask-once guard, per-scope modData exclusion sets, client grep limits ≥ 2 × predicted (the client console prints each mod's block twice), predictions/observations/verdicts (`as_predicted | falsified | trivial | unmeasured`), try/except/finally that always saves the artifact.
- **Lint/data tools:** `tools/doc_lint.py`, `tools/mod_lint.py` (mod.info/layout rules; `mod-info-place` is a bounded measured statement since slice 12), `tools/mod_inventory.py`, `tools/food_scan.py`, `tools/recipe_scan.py`, `tools/workshop_search.py`; datasets under `data/` with `data/README.md`.
- **Experiment mods** (`testing/experiments/TKX_*`, mod ids `TKX_*`): A ItemOverride, B Nutrient, C EatHook, D `tkx-loader-probe` (two mod.infos), E CommonOnly, F ZWatermelon, G PcallProbe, H RaiseProbe — installed only through test profiles, never in the fixture.

## 8. Environment gotchas (all bit us)

- The Bash tool's **cwd resets** between calls — `cd /c/Users/Angus/repos/project_zomboid` in every call, or edits land in the home dir.
- Long Bash heredocs with apostrophes fail to parse — write briefs and long files with the **Write** tool; keep Bash-embedded Python apostrophe-free.
- `docs/progress.md`, `docs/decisions.md`, `docs/modding/patterns.md`, `docs/testing/README.md` and several READMEs are **CRLF**; edit with `newline=''` handling and preserve. `core.autocrlf=true` here; `.gitattributes` pins the B41-layout test translation file to CRLF.
- The harness client runs `-debug`: an **unguarded mod Lua error parks it in the Lua debugger's modal break** (x127) — a raising probe must be gated on the server side and its profile's `[client] timeout` set low.
- A stray `ProjectZomboid64.exe` predating a session is the user's own client — never kill it; `doctor` checks java only.
- The workshop corpus **drifts** (Steam rewrote a mod.info mid-slice): `data/mod-inventory.json` is a dated snapshot (2026-09-10 17:47); date every count.
- Subagents: Opus (`model: "opus"`), always specified; the lead is Fable. If Opus is rate-limited, wait for the reset or ask Angus which model to substitute — do not silently downgrade.

## 9. Memory and the user's standing rules

Standing rules from Angus, verbatim in spirit: commits with no Claude attribution and succinct messages; Opus for all subagents, Fable on the main thread; experiments and trial-and-error on the live server are encouraged; proceed to completion and ledger decisions for review instead of asking; fire off subagents for research as you go; iterate to improve the harness as you go when it makes sense.

## 10. Key measured facts (pointers, not restatements)

`docs/modding/patterns.md` § Measured MP sync facts + KEEP/FILTER rows own the canonical prose. Headlines from slice 12 (`docs/modding/{anatomy,item-overrides,lua-api}.md`): a partial `item` block **merges per key** (the script reset is a no-op); script bodies replay **sorted by stored script path**, independent of `Mods=` position, last body wins per key; the live `mod.info` chain reads the version dir's file first (`searchForModInfo` is dead code) — one id per folder, folder name irrelevant; an empty version dir costs nothing; a dedicated server resolves no display name and `getText` never reaches item names; `OnEat` fires on both sides and a server-side wrapper of `ISEatFoodAction.complete` runs before `Eat`; a mod's `server/` Lua also runs in the MP client VM (guard with `isServer()`); `transmitModData` replaces server→client and wipes client→server; the weight flags agree on both non-trivial arms; `pcall` **catches** a Kahlua nil call (the old "uncatchable" rule is falsified), an unguarded raise aborts only its own handler on the server. Open items for 13/14: `.superpowers/sdd/wave-4/not-settled.md` and `.superpowers/sdd/13-wall-map/slice-12-outcomes.md`.
