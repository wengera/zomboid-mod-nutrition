# Plan 11c — Satiety from Physiology Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace Task 15's vanilla-keyed satiety scalar with satiety from physiology: a stomach with two lanes (a solid lane that empties energy at a zero-order rate, a liquid lane for drunk water), fullness read from the stomach's mass, and a post-absorptive pool P fed by the energy leaving the stomach. Hunger is `K.hybrid.hungerTarget(sated(F, post(P)), energyState)`, written once a player-minute by the writer. A soft cap floors DISCOMFORT past 730 g. Records migrate to version 4. Task 15's pieces and `NR.SatietyBulk` retire. Every piece is test-first under the lupa host, and an oracle replays published meal studies, accepted after a mutation pass.

**Architecture:** The new arithmetic lives in two pure kernel files, `NR_Kernel_Stomach.lua` and `NR_Kernel_Satiety.lua`. Tasks 2 and 3 append it beside the old code, so nothing moves and the golden trace stays byte for byte. Task 4's oracle replays the studies through those kernels. Task 6, the switch, rewires the adapters in one behaviour change named **"satiety from physiology"**, the only re-record of the golden trace in this plan:
- kinetics drains both lanes and hands `ctx.emptied` on;
- the intake routes a drink's water to the liquid lane and stops reading `getHungerChange`;
- the writer feeds, decays and reads P;
- the store moves to v4;
- the first-order stomach retires.

Task 7 adds the soft cap as a writer floor, after Task 5's 42.21 read of vanilla's overeating and of DISCOMFORT. Task 8 adds the guard lists and CROSS rows. Task 9 retires Task 15's satiety pieces and the option. Task 10 writes the area page and its register rows.

**Tech Stack:**
- The mod's Lua: the Kahlua subset, run for tests on the `lupa` 2.8 Lua 5.1 host (`testing/tests/kernel/conftest.py`, `server_host.py`).
- Python 3 tests (pytest).
- The claims register and its delta tool (`tools/claims_delta.py`), and the science register (`docs/reference/science.tsv`, read only here).
- The jar toolchain at `C:\Users\Angus\pz-b42`: `./pz.sh grep|methods|refs|dump`, read-only. Read its `WORKSPACE.md` first.

**Spec:** `docs/superpowers/specs/2026-10-08-satiety-physiology-design.md`, read whole. Its § 5a (the harvest's outcome, rulings 11c-4 to 11c-8) overrides § 3 where they disagree. The ledger is `.superpowers/sdd/2026-10-08-plan-11c-satiety/progress.md`. It holds rulings 11c-1 to 11c-3, Task 1 and Task 1b. The science rows are S1222–S1272 (minted at 1f9fccc), plus S0130 (superseded by S1272) and S0131 (settled). Executors read the spec's § 5a and their task before starting.

## Global Constraints

Everything in Plan 11a's Global Constraints holds (`docs/superpowers/plans/2026-10-08-plan-11a-build.md`), and through it Plans 1–10's. CLAUDE.md §§ 3–7 are binding: the § 3 gates, § 4's register and science discipline, § 5's Kahlua rules, § 6's process and model policy, and § 7's line endings. The following are added or restated for this plan.

### Order and the build

- **Plan 11a closes first.** No Plan 11c task edits `mod/` (and none is dispatched at all) until Plan 11a's ledger `.superpowers/sdd/2026-10-08-plan-11a-build/progress.md` carries `Task 20: complete`.
  - Task 1 (the harvest) and Task 1b (the science tool) ran before the plan was written, are complete, and touched no `mod/` Lua beyond the controller's comment-only S1272 rewording at 1f9fccc.
- **The build is 42.21** (CLAUDE.md § 2): Steam buildid `25485521`, revision `4a0e9546ec`. Jar reads are on 42.21, and the food data is the 2026-10-08 scan.
- **No live boot in this plan.** Every reading is offline, on the lupa host or the jar. Plan 11b's live acceptance and release run after this plan closes, on this model (spec § 8 end).

### Performance (Rule 6)

- **Rule 6** (CLAUDE.md § 1, Angus 2026-10-07): no noticeable hitching at the 60-player design load. Per-tick work is admitted only where a measurement shows it reduces hitching, and a design is judged by its worst server frame and how often that frame comes.
- This plan adds **no per-tick work**. Everything new runs inside the existing once-a-player-minute pipeline (kinetics, writer) in the budgeted queue.
- **Each mod task reports its lupa cost per writer step beside Task 15's figures**: `W.satiety` 0.70 µs, and `W.step` 5.10 → 5.85 µs (Plan 11a Task 15 report, `bench_t15.py`). Measure with the line hook off, as `test_plan4_steady_state.py` does.
  - Task 2 reports `K.stomach.drain` against `K.stomach.empty`.
  - Task 6 reports `W.step`, `W.satiety` and the kinetics minute.
  - Task 7 reports `W.step` with the soft cap.
  - The script is `.superpowers/sdd/2026-10-08-plan-11c-satiety/bench_11c.py` (Task 2 Step 6 writes it). The figures go in the report, never in a page.

### Golden trace and oracle

- **The golden-trace rule** (CLAUDE.md § 6; Plan 10 rulings 3 and R0-1): `testing/tests/kernel/golden/trace-1.0.0.json` is re-recorded (`python testing/tests/kernel/golden_trace.py --write`) by **Task 6 only**.
  - The re-record lands in the same commit as the behaviour change it records, named **"satiety from physiology"** in the commit subject and the report.
  - Its report walks the changed leaves: it lists the first differing leaf of every changed snapshot and traces two of them to the line of code that moved them. It also states the `printed_count` before and after.
  - Every other task keeps `test_golden_trace.py` green byte for byte. A task whose trace moves in a way its task does not name stops and reports; it never re-records.
  - The trace's stand-in players have no `getStats`, so the writer never hoists in the trace. Task 7's soft cap and Task 6's writer changes do not move it. The stomach, the intake, the store and kinetics do.
- **The oracle mutation rule** (CLAUDE.md § 6): `test_satiety_meal_studies.py` is accepted only after its reviewer's mutation pass (Task 4 Step 6).
  - Each constant it guards is patched at run time on a fresh host: to its neutral or off value, ×2 and ×0.5. The constants are `W_PROTEIN`, `HALF_LIFE_H`, `P50`, `FULL_WEIGHT`, `LIQUID_PER_KCAL`, `WATER_HALF_MIN`, `RATE_BASE`, `RATE_PER_KCAL` and `DEFICIT_FLOOR`. The liquid lane's routing is swapped as well.
  - Each mutation must fail at least one oracle test. A surviving mutation is a FAIL of the oracle, fixed by a test the controller rules on, never by loosening a band.

### Code rules

- **Test-first:** every new behaviour and every defect is first a failing test, run and seen to FAIL on the pre-change tree. The report quotes the failing run's last line.
  - A test that passes on the pre-change tree is a **follow-up pin**, labelled so in the task and the report.
  - A task with no red run is sent back.
- **Kernel files are pure and one statement per line**: `if c then` / statement / `end` on separate lines. `python -m pytest testing/tests/kernel -q` keeps `test_zz_coverage.py` green, at 100 % of kernel lines.
  - A `for … in pairs(…)` loop whose body ends in an `if … end` leaves that `end` unexecuted under the Lua 5.1 line hook, so such a body calls a kernel helper.
- **Kahlua everywhere:** no `goto`, no `%d` or `%x` on a float (no `string.format` on a kernel number at all), and no `#` on a Java list.
- **Adapters read, call and write:** new arithmetic goes in a kernel function. An adapter may branch on presence, side, mode and finiteness.
- **A traced module's `stats` table gains no key** (`golden_trace.py` `STATS_NAMES`: `bus.effects, effects, fast, intake, kinetics, metabolism, nutrients, reconcile, store, strength, training, weight`). New counters go on `NR.server.writer.stats` (untraced) or a new table.
- **One kernel suite at a time:** `test_golden_trace.py` and `test_zz_coverage.py` read the whole tree. So every task that edits `mod/` Lua or a kernel test runs in the one serial lane (the Execution order below).
- **Append, never insert, in Tasks 2 and 3:** their new kernel code goes at the end of its file, so no existing line moves. Task 3's one in-place edit, `hungerTarget`'s line, keeps the line count. Later tasks shift lines.
  - Every `mod/` task runs `PYTHONIOENCODING=utf-8 python tools/claims_check.py --allow-provisional` (the full run) after its edit.
  - Its report lists each `pointer-line` or `pointer-quote` finding: the row, the old line and the new line.
  - Implementers never edit `docs/reference/claims.tsv`. The controller re-anchors at the wave close in one register commit (CLAUDE.md § 4).

### Gates, files and science

- **The `mod/` gates on every mod commit** (CLAUDE.md § 3), each at 0 ERROR or 0 findings: `python tools/mod_lint.py mod/NutritionRevamp`, `python tools/release_pack.py check mod/NutritionRevamp`, `python tools/kahlua_lint.py mod testing/experiments testing/PZTestKit`, `python tools/hotpath_lint.py mod` and `python tools/science_check.py --scan mod`.
  - `python -m pytest tools/tests testing/tests -q` stays at or above the baseline Task 0 ledgers, with no failure. Each task reports its collected and passed counts; a task that deletes tests says how many and why.
- **CRLF files** (`file <path>` before every edit; CLAUDE.md § 7): `test_kernel_stomach.py`, `test_intake_shape.py`, `test_kinetics.py`, `test_nutrients_shape.py`, `test_metabolism_shape.py`, `test_server_reconcile_shape.py`, `test_kernel_hybrid.py` and `test_plan4_steady_state.py` are CRLF in the working tree. So are the docs pages `docs/areas/body-effects.md`, `docs/facts/eating-pipeline.md`, `docs/facts/character-stats.md` and `docs/platform/sandbox-options.md`.
  - An edit reads and writes with `newline=''` and keeps each file's endings. New test files are LF.
- **Science (CLAUDE.md § 4.8, spec § 5a):** every constant the mod ships names its settled science row in its comment, or is labelled **game choice**, or **labelled inference** (with the row it is inferred from), exactly as § 5a rules.
  - No comment names S0130 (superseded) or an open row as evidence: S1268, S1269, S1270 and S1271 appear only as "open" beside a game choice.
  - `python tools/science_check.py --scan mod` reads 0.
- **New evidence is minted through delta files**: `.superpowers/sdd/2026-10-08-plan-11c-satiety/task-<N>-claims-delta.tsv`.
  - The provisional ids are `T117<NN>.<n>`, with `<NN>` the two-digit task number: Task 5's are `T11705.n` and Task 10's are `T11710.n`. Each matches `claimslib.PROVISIONAL_ID_RX`, and none collides with Plan 11a's `T11NN` or Plan 11b's `T113N`.
  - Each delta is dry-run with `python tools/claims_delta.py apply <delta> --pages <page> [...] --dry-run`.
  - A page commit carrying provisional tags passes `PYTHONIOENCODING=utf-8 python tools/claims_check.py --staged --allow-provisional`. The controller applies the delta at the wave close and then runs the checker without the allowance.
  - The next free register id is read off `docs/reference/claims.tsv` at the mint (#3588 on 2026-10-08, if Plan 11a's close mints none).
- **Commits** are pathspec commits: `git add -- <new files>` for new files only, then `git commit -m "<subject>" -- <every touched path>`.
  - Never `--amend`, `git stash`, `checkout --`, `reset`, `restore`, `add -N`, `add -f` or an index-wide command, and never set a `GIT_*` variable.
  - On `.git/index.lock`, retry once after two seconds.
  - No Claude attribution. Implementers never push.
- **The mod version stays 1.0.0.** Plan 11b's release sets 1.0.1. The record version moves 3 → 4 (Task 6).

### Models

- **Models (CLAUDE.md § 6):** every dispatch names its model and asks for the exact model id in the return. One on an older version is re-dispatched.
  - Opus (`model: "opus"`) takes the kernel, the oracle, the jar reads, the wiring and the evidence pages.
  - Sonnet (`model: "sonnet"`) takes the spelled-out retirement.

## Rulings this plan takes

The ledger already holds 11c-1 to 11c-8. Task 0 writes each of these into the ledger as `Ruling: <what> — <why> — cost if wrong: <…>`.

- **11c-9: Kernels first and additive, one switch.** Tasks 2 and 3 append new functions beside the old ones, Task 4 tests them, and Task 6 rewires every adapter and retires the first-order stomach in one commit with the one golden re-record.
  - Why: the stomach's record shape (`bulk` against `liquid`) and the store's v4 move together. Splitting them would re-record the trace twice or leave a half-wired record.
  - Cost if wrong: a large Task 6 diff, reviewed whole.
- **11c-10: Mass is read off the buffers, never stored.** `K.stomach.mass(stomach)` is `massOf(buffer) + liquid`, and there is no `stomach.mass` field (spec § 3.1 names one).
  - Why: a stored sum would be a second copy that a heal or a migration could desync. The read is five additions.
  - `stomach.liquid` is read `or 0`, so a v3-shaped stomach drains safely before its first load.
  - Cost if wrong: none found.
- **11c-11: The emptied vector rides the minute's context.** Kinetics hands this minute's emptied vector on `ctx.emptied` (transient, never on the record). The writer feeds P from it, then decays P over its own elapsed world age, at `trait × sd`: the appetite traits (#0485, vanilla's game numbers) times vanilla's `StatsDecrease` sandbox multiplier, which scaled Task 15's step.
  - Spec § 3.1's `decay(P, dtH, halfLifeH, trait)` takes that product as its `trait`.
  - Why: the writer holds the trait handles, and kinetics already allocates the emptied vector each minute.
  - Cost if wrong: an operator who set StatsDecrease expects hunger to follow it. It does.
- **11c-12: A drink's water goes to the liquid lane and everything else to the solid buffer.** This is the energy budget of ruling 11c-5, so a sugary drink empties at the energy rate.
  - The drink action, world water and the writer's auto-drink sip land by `K.stomach.ingestLiquid`.
  - An eat and a reconciled intake land by `K.stomach.ingest`, with a food's water staying with the food.
  - Cost if wrong: a drink's micronutrients leave with the solid lane's energy rather than with its water.
- **11c-13: The soft cap is a writer floor, not an intake add.** This deviates from spec § 3.1, gated on Task 5's J2.
  - While `K.stomach.mass > 730 g`, the writer floors DISCOMFORT once a game minute at `100 × clamp((mass − 730) / (1100 − 730), 0, 1)`, in both modes, and never lowers it.
  - Why: vanilla's `BodyDamage.UpdateDiscomfort` relaxes DISCOMFORT toward its own target at `0.005 × GameTime.getMultiplier()` per update. This was spot-read on 42.21 while writing this plan, and Task 5 cites it. So a one-off add at the eat would fade within real minutes while the stomach stays over capacity for an hour; the floor holds while the mass does.
  - If Task 5 finds DISCOMFORT absent from what the client receives, or recomputed so that a floor cannot hold, the controller amends Task 7 before it runs.
  - Cost if wrong: a once-a-minute sawtooth like PANIC's (#3400).
- **11c-14: The two fill thresholds keep their numbers on the new fill.**
  - `NUT.FED_FILL` 0.05 is now about 21 g of stomach mass.
  - `K.nutrients.ACUTE_EMPTY_FILL` 0.2 is now about 86 g.
  - Both are labelled game choices and their comments say so.
  - Cost if wrong: the alcohol-fasting and acute-dose terms read "empty" a little differently. Plan 11b's acceptance reads them.
- **11c-15: A record with no stomach starts with an empty one.** This covers a new record, a respawn and a v3 migration (spec § 4). `K.stomach.seedFull` retires, and P is seeded from HUNGER at the writer's first minute, so the character's hunger carries over.
  - Cost if wrong: none; the seed is what keeps the feel.
- **11c-16: `record.satiety = { P = <number>, v = 4 }`.**
  - `v` is the seeded mark that replaces `satietyStepped`.
  - The writer re-seeds when `satiety` is not a table, or `v ~= 4`, or `P` is not finite. That is the pre-step heal, counted in `W.stats.seeded`.
  - A P the step itself makes non-finite is re-stamped from its pre-step value (`W.stats.guarded`).
  - Cost if wrong: none found.
- **11c-17: The oracle reads a study's meal request at HUNGER 0.25,** vanilla's HUNGRY level 2 (Appendix D's ladder 0.15, 0.25, 0.45, 0.70; #0508 is its level-4 rung). This is a game choice that maps a spontaneous meal request onto the moodle a player acts on.
  - The oracle names what it does not reproduce (Task 4's docstring): S1247's dose slope, S1224's absolute delays, and S1231's 17-minute arm.
  - Cost if wrong: a calibration against the wrong rung, visible in Plan 11b's play.
- **11c-18: The fitted constants.** These were measured on a Python mirror of the kernels below on 2026-10-08. The implementers re-measure on the lupa host.
  - **The fit:** `HALF_LIFE_H` 2.0 h, `P50` 150 weighted kcal, `W_PROTEIN` 2.5 and `FULL_WEIGHT` 0.5.
  - **What it gives:**
    - A 650 kcal mixed meal returns hunger to 0.25 at minute 274.
    - Marmonier's protein snack delay over its carbohydrate delay is 197 / 110 = 1.79.
    - Callahan's three preloads take 85, 164 and 342 min.
    - A soup's mean hunger is 0.0153 below its casserole with water over 3 h.
    - A water load half-empties at 13 min, and the thin shakes at 24 and 72 min.
    - Hunt's 540 kcal meal empties 2.414 kcal/min over its first hour, with a slope of 0.75 kcal/min.
    - A 650 kcal meal's t50/t90 is 133/285 = 0.467.
    - A 25 % deficit raises the pre-meal hunger by 0.0833.
  - All are game choices or labelled inferences (Task 2 and Task 3 comments).
  - Cost if wrong: Plan 11b's play re-tunes within the oracle's bands.

## File structure

`mod/...` below is `mod/NutritionRevamp/common/media/lua`; `<ws>` is `.superpowers/sdd/2026-10-08-plan-11c-satiety`.

| path | responsibility | task |
|---|---|---|
| `<ws>/task-1-science-part.tsv`, `task-1-settle.sh` (done); `docs/reference/science.tsv` (S1222–S1272, minted 1f9fccc) | the harvest | 1 (done) |
| `tools/sciencelib.py`, `tools/science_delta.py`, `docs/reference/science.md` (done, cc965bb) | the `satiety` topic; a gap closed by supersede | 1b (done) |
| `mod/.../shared/NR_Kernel_Stomach.lua` (appended); `testing/tests/kernel/test_kernel_stomach_lanes.py` (new); `<ws>/bench_11c.py` | fill by mass, the two lanes, the zero-order energy lane | 2 |
| `mod/.../shared/NR_Kernel_Satiety.lua` (appended), `mod/.../shared/NR_Kernel_Hybrid.lua` (`DEFICIT_FLOOR`); `testing/tests/kernel/test_kernel_satiety_physiology.py` (new) | fill, weigh, feed, decay, post, sated, seedP, discomfort | 3 |
| `testing/tests/kernel/test_satiety_meal_studies.py` (new); `<ws>/mutate_11c.py` (reviewer) | the oracle and its mutation pass | 4 |
| `<ws>/task-5-jar-memo.md`, `<ws>/task-5-claims-delta.tsv`; `docs/facts/eating-pipeline.md`, `docs/facts/character-stats.md`, `docs/platform/sandbox-options.md` (tagged sentences) | the 42.21 reads: overeating, DISCOMFORT, a removed sandbox key | 5 |
| `mod/.../shared/NR_Kernel_Stomach.lua`, `NR_Kernel_Store.lua`, `NR_Kernel_Nutrients.lua` (a comment); `mod/.../server/NR_Server_Kinetics.lua`, `NR_Server_Intake.lua`, `NR_Server_Writer.lua`, `NR_Server_Nutrients.lua`, `NR_Server_Reconcile.lua`; tests `test_kernel_stomach.py`, `test_kernel_stomach_lanes.py`, `test_kinetics.py`, `test_intake_shape.py`, `test_writer_shape.py`, `test_kernel_store.py`, `test_store_file_shape.py`, `test_server_reconcile_shape.py`, `test_nutrients_shape.py`, `test_metabolism_shape.py`, `test_plan4_steady_state.py`; `golden/trace-1.0.0.json` | the switch, and v4 | 6 |
| `mod/.../shared/NR_Kernel_Hybrid.lua` (`input`, `write`), `mod/.../server/NR_Server_Writer.lua`; `testing/tests/kernel/test_soft_cap.py` (new), `test_writer_shape.py` (ENV, STATS, limitation four) | the soft cap | 7 |
| `mod/.../server/NR_Server_Kinetics.lua` (`KIN.GUARD`); `testing/tests/kernel/test_heal_once.py`, `test_kinetics.py` | the guard list and the CROSS rows | 8 |
| `mod/.../shared/NR_Kernel_Satiety.lua`, `mod/.../server/NR_Server_Writer.lua`, `NR_Server_Options.lua`, `mod/NutritionRevamp/42.20.4/media/sandbox-options.txt`, `mod/.../shared/Translate/EN/Sandbox.json`; delete `testing/tests/kernel/test_satiety_default.py`; `test_kernel_satiety.py`, `test_writer_shape.py` | retire Task 15's pieces and `NR.SatietyBulk` | 9 |
| `docs/areas/body-effects.md`, `<ws>/task-10-claims-delta.tsv` (and `.claude/skills/nutrition-body-effects/SKILL.md` only if the checker names it) | the area page and its register rows | 10 |
| the ledger, `CLAUDE.md` § 3's count, the memory files | the close | 11 |

## Execution order

- **Gate.** Task 0 (controller) first waits for Plan 11a's `Task 20: complete`.
- **Lane M** runs in the shared worktree and is strictly serial; each task starts after the previous one's `Task N: complete` line:
  - Task 2 (Opus);
  - Task 3 (Opus);
  - Task 4 (Opus, with an Opus mutation-pass reviewer);
  - Task 6 (Opus; the one re-record; needs Task 5's J4 answer);
  - Task 7 (Opus; needs Task 5's J1 and J2, and the controller's ruling on them);
  - Task 8 (Opus);
  - Task 9 (Sonnet; needs Task 5's J3);
  - Task 10 (Opus).
- **Lane D** holds Task 5 (Opus), which runs beside Tasks 2–4 in the shared worktree. It edits no `mod/` file and runs no kernel suite; its files (`docs/facts/*`, `docs/platform/sandbox-options.md`, the workspace) are disjoint from lane M's.
- **The controller's checkpoints:**
  - It applies Task 5's delta at Task 5's close, before Task 6 starts.
  - It re-anchors the pointer shifts after Task 6 and after Task 9.
  - It applies Task 10's delta at Task 10's close.
  - Reviews are read-only and fresh, on the tier each heading names.
- **Workspace files.** Every task's `task-N-amendments.md` is written with the Write tool and listed on disk before the dispatch (CLAUDE.md § 6). `<ws>` paths in a dispatch are written out in full.

---

### Task 0: The workspace — controller

- [ ] **Step 1: Confirm the gate and the workspace.**
  - Confirm `grep -c "^Task 20: complete" .superpowers/sdd/2026-10-08-plan-11a-build/progress.md` reads `1`. Until it does, nothing below is dispatched.
  - Ledger these lines:
    - the plan's path;
    - the rulings 11c-9 to 11c-18 above, as `Ruling:` lines;
    - the golden sha256 (`python -c "import hashlib;print(hashlib.sha256(open('testing/tests/kernel/golden/trace-1.0.0.json','rb').read()).hexdigest())"`);
    - the pytest baseline (`python -m pytest tools/tests testing/tests -q -p no:cacheprovider`, its last line);
    - the kernel suite's count (`python -m pytest testing/tests/kernel -q -p no:cacheprovider`);
    - the next register id (the last `#` id in `docs/reference/claims.tsv` plus one).
- [ ] **Step 2: Record the done tasks.** These are already in the ledger:
  - `Task 1: complete` (the harvest; mint 1f9fccc: S1222–S1272; S0130 superseded by S1272; S0131 settled);
  - `Task 1b: complete` (cc965bb: the `satiety` topic; `gap_closed` drops `topic`).

  Ledger that both are recorded as done in this plan and that the spec's § 5a (1dc3e6d) is the design this plan builds.
- [ ] **Step 3: Dispatch.** Write `task-2-amendments.md` and `task-5-amendments.md` with the Write tool and list them. Then dispatch Task 2 (lane M) and Task 5 (lane D).

---

## Phase A — Done before the plan

### Task 1: The harvest — DONE (Opus implementer, Opus reviewer; Sonnet fix-1)

Rows S1222–S1272 were minted at 1f9fccc. S0130 was superseded by S1272 (Moore 1981: solid emptying is linear) and S0131 was settled (Hunt 1985: about 2.5 kcal/min). Rulings 11c-1 to 11c-3 and the review's defects D1–D15 are in the ledger. The design implications are the spec's § 5a, rulings 11c-4 to 11c-8. Nothing remains.

### Task 1b: The science tool — DONE (Sonnet implementer; controller check)

At cc965bb, `satiety` was added to `TOPICS`, `gap_closed` drops `topic`, and `science.md` was updated. Nothing remains.

---

## Phase B — The kernels and the oracle

### Task 2: The stomach's two lanes — Opus implementer, Opus reviewer

The lane is M, and the task starts after Task 0 Step 3. It appends to `NR_Kernel_Stomach.lua` the fill by mass, the liquid lane and the zero-order energy lane (spec § 5a rulings 11c-4, 11c-5 and 11c-8). Nothing calls them yet: the existing `empty`, `bulkOf` and their callers are untouched, so the golden trace and every existing test stay byte for byte.

**Files:**
- Modify: `mod/NutritionRevamp/common/media/lua/shared/NR_Kernel_Stomach.lua`, appending after the last line (`K.stomach.fill`) only.
- Create: `testing/tests/kernel/test_kernel_stomach_lanes.py` (LF).
- Create (workspace, never committed): `.superpowers/sdd/2026-10-08-plan-11c-satiety/bench_11c.py`.

**Interfaces:**
- Consumes: `K.vector.new()`, `K.vector.add(dst, src, scale)`, `K.vector.KEYS`, `K.min`, `K.max` and `K.clamp`, all existing.
- Produces, for Tasks 3, 4, 6, 7 and 8:
  - The constants: `K.stomach.RATE_BASE = 1.25` (kcal/min), `K.stomach.RATE_PER_KCAL = 0.0025` (per min), `K.stomach.WATER_HALF_MIN = 13` (min), `K.stomach.LIQUID_PER_KCAL = 0.12` (min per kcal), `K.stomach.CAPACITY_G = 430`, `K.stomach.CAPACITY_MAX_G = 730` and `K.stomach.CAPACITY_HARD_G = 1100`.
  - `K.stomach.massOf(vector) -> grams`, `K.stomach.mass(stomach) -> grams` and `K.stomach.water(stomach) -> grams`.
  - `K.stomach.ingestLiquid(stomach, vector) -> stomach`: the vector's water goes to `stomach.liquid` and every other key to `stomach.buffer`; the vector itself is unchanged.
  - `K.stomach.solidRate(energyKcal) -> kcal/min`, `K.stomach.waterFraction(dtM, halfMin) -> 0..1`, `K.stomach.liquidHalfMin(energyKcal) -> min` and `K.stomach.solidFraction(energyKcal, dtM) -> 0..1`.
  - `K.stomach.drain(stomach, dtH) -> emptied vector` (fresh). The buffer and the liquid lane keep the rest.

- [ ] **Step 1: Write the failing tests.** Create `testing/tests/kernel/test_kernel_stomach_lanes.py`:

```python
"""The stomach's two lanes (Plan 11c Task 2; spec § 5a rulings 11c-4, 11c-5 and 11c-8): fill by mass, a solid lane
that empties energy at a zero-order rate rising with the buffered energy (S0131, a labelled inference for solids),
never faster than water's half-time (S1245), and a liquid lane of drunk water whose half-time grows with the solid
lane's energy (S1234 over S1245, a labelled inference). Hand-computed from the constants."""
import math
import os
import re

import pytest

LN2 = 0.6931471805599453
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
STOMACH = os.path.join(REPO, "mod", "NutritionRevamp", "common", "media", "lua", "shared", "NR_Kernel_Stomach.lua")
NAMES = ("RATE_BASE", "RATE_PER_KCAL", "WATER_HALF_MIN", "LIQUID_PER_KCAL", "CAPACITY_G", "CAPACITY_MAX_G",
         "CAPACITY_HARD_G")


def _vec(host, **kw):
    v = host.K.vector["new"]()
    for k, val in kw.items():
        v[k] = val
    return v


def _closed(E, dtM):
    """The solid fraction in doubles: the closed form of dE/dt = -(1.25 + 0.0025 E), capped at water's."""
    fw = 1 - math.exp(-LN2 * dtM / 13) if dtM > 0 else 0.0
    if E <= 0:
        return fw
    left = (E + 1.25 / 0.0025) * math.exp(-0.0025 * dtM) - 1.25 / 0.0025
    fe = 1.0 if left <= 0 else max(0.0, 1 - left / E)
    return min(fe, fw)


def test_the_constants(host):
    s = host.K.stomach
    assert (s.RATE_BASE, s.RATE_PER_KCAL, s.WATER_HALF_MIN, s.LIQUID_PER_KCAL) == (1.25, 0.0025, 13, 0.12)
    assert (s.CAPACITY_G, s.CAPACITY_MAX_G, s.CAPACITY_HARD_G) == (430, 730, 1100)


def test_each_constant_names_its_row_or_its_label():
    with open(STOMACH, encoding="utf-8") as fh:
        src = fh.read()
    for name in NAMES:
        line = re.search(r"^K\.stomach\.%s = .*$" % name, src, re.M).group(0)
        assert ("labelled inference" in line and re.search(r"S\d{4}", line)) or "S1245 (Mudie" in line, name


def test_mass_of_a_vector_is_its_water_macros_and_fibre_in_grams(host):
    v = _vec(host, calories=95, proteins=0.5, carbs=25.1, lipids=0.3, fibre=4.4, water=155.8, iron=0.2)
    assert host.K.stomach.massOf(v) == pytest.approx(155.8 + 0.5 + 25.1 + 0.3 + 4.4)
    assert host.K.stomach.mass(host.K.stomach["new"]()) == 0


def test_ingest_liquid_puts_the_water_in_the_liquid_lane_and_the_rest_in_the_buffer(host):
    st = host.K.stomach["new"]()
    v = _vec(host, calories=100, carbs=25, water=375, sodium=10)
    out = host.K.stomach.ingestLiquid(st, v)
    assert host.rt.eval("rawequal")(out, st)
    assert st.liquid == 375 and st.buffer.water == 0
    assert (st.buffer.calories, st.buffer.carbs, st.buffer.sodium) == (100, 25, 10)
    assert v.water == 375                                       # the landed vector is left as it was
    assert host.K.stomach.mass(st) == pytest.approx(400)
    assert host.K.stomach.water(st) == pytest.approx(375)


def test_ingest_liquid_keeps_the_buffers_own_water_bit_for_bit(host):
    st = host.K.stomach["new"]()
    host.K.stomach.ingest(st, _vec(host, calories=200, water=0.1))
    host.K.stomach.ingestLiquid(st, _vec(host, water=0.2))
    assert st.buffer.water == 0.1 and st.liquid == pytest.approx(0.2)
    assert host.K.stomach.water(st) == pytest.approx(0.3)


def test_the_solid_rate_rises_with_the_buffered_energy(host):
    assert host.K.stomach.solidRate(0) == 1.25
    assert host.K.stomach.solidRate(600) - host.K.stomach.solidRate(300) == pytest.approx(0.75)   # S0131: +0.72


@pytest.mark.parametrize("E,dtM", [(650, 1), (650, 60), (40, 1), (40, 60), (3, 1), (3, 5), (1, 5)])
def test_the_solid_fraction_is_the_closed_form_capped_at_waters(host, E, dtM):
    assert host.K.stomach.solidFraction(E, dtM) == pytest.approx(_closed(E, dtM), rel=1e-12, abs=1e-15)


def test_a_solid_lane_with_no_energy_empties_like_water(host):
    assert host.K.stomach.solidFraction(0, 13) == pytest.approx(0.5)
    assert host.K.stomach.solidFraction(-1, 13) == pytest.approx(0.5)


def test_no_time_empties_nothing(host):
    assert host.K.stomach.solidFraction(650, 0) == 0
    assert host.K.stomach.waterFraction(0, 13) == 0
    assert host.K.stomach.waterFraction(-5, 13) == 0


def test_the_liquid_half_time_grows_with_the_solid_energy(host):
    assert host.K.stomach.liquidHalfMin(0) == 13
    assert host.K.stomach.liquidHalfMin(500) == pytest.approx(73)
    assert host.K.stomach.liquidHalfMin(-3) == 13


def test_drain_moves_the_solid_share_of_every_key_and_the_liquids_share_of_water(host):
    st = host.K.stomach["new"]()
    host.K.stomach.ingest(st, _vec(host, calories=650, proteins=24.375, carbs=81.25, lipids=25.0, fibre=6, water=300,
                                   iron=4))
    host.K.stomach.ingestLiquid(st, _vec(host, water=250))
    f = _closed(650, 30)
    fl = 1 - math.exp(-LN2 * 30 / (13 + 0.12 * 650))
    em = host.K.stomach.drain(st, 0.5)
    assert em.calories == pytest.approx(650 * f) and em.iron == pytest.approx(4 * f)
    assert em.water == pytest.approx(300 * f + 250 * fl)
    assert st.buffer.calories == pytest.approx(650 * (1 - f)) and st.buffer.water == pytest.approx(300 * (1 - f))
    assert st.liquid == pytest.approx(250 * (1 - fl))


def test_drain_over_no_time_moves_nothing(host):
    st = host.K.stomach["new"]()
    host.K.stomach.ingest(st, _vec(host, calories=95, water=155.8))
    host.K.stomach.ingestLiquid(st, _vec(host, water=100))
    em = host.py(host.K.stomach.drain(st, 0))
    assert all(v == 0 for v in em.values())
    assert st.buffer.calories == 95 and st.liquid == 100


def test_a_stomach_without_a_liquid_lane_drains_as_empty(host):
    # a v3-shaped stomach (no liquid field) before its first load: read as 0 (ruling 11c-10)
    st = host.K.stomach["new"]()
    st.liquid = None
    host.K.stomach.ingest(st, _vec(host, calories=100, water=50))
    em = host.K.stomach.drain(st, 1 / 60)
    assert em.water == pytest.approx(50 * _closed(100, 1)) and st.liquid == 0
```

- [ ] **Step 2: Run them to see them fail.**

Run: `python -m pytest testing/tests/kernel/test_kernel_stomach_lanes.py -q -p no:cacheprovider`
Expected: FAIL. `RATE_BASE` is nil (`AssertionError` on `test_the_constants`), and `attempt to call a nil value (field 'massOf')` and its like. Quote the last line in the report.

- [ ] **Step 3: Append the implementation** to the end of `NR_Kernel_Stomach.lua`, after the `K.stomach.fill` function's closing `end`:

```lua

-- Plan 11c (spec § 5a rulings 11c-4, 11c-5 and 11c-8): fill by mass and the stomach's two lanes. Appended below the
-- Plan 2 code so no line above moves; the first-order pieces above (HALF_TIME_H, FULL_BULK, bulkOf, seedFull,
-- compositionScale, emptyFraction, empty) retire in Task 6 once nothing calls them. The solid lane (stomach.buffer)
-- empties energy at a zero-order rate that rises with the energy it holds, every other key leaving in the same
-- proportion, never faster than water; the liquid lane (stomach.liquid, grams of drunk water) half-empties in
-- WATER_HALF_MIN plus LIQUID_PER_KCAL per kcal in the solid lane. stomach.liquid is read `or 0` (ruling 11c-10).
K.stomach.RATE_BASE = 1.25 -- S0131 (labelled inference, ruling 11c-4): kcal/min at no load, fitted so the rate reads Hunt 1985's overall 2.5 kcal/min at its mean load; liquid carbohydrate meals applied to solids
K.stomach.RATE_PER_KCAL = 0.0025 -- S0131 (labelled inference, ruling 11c-4): per min, the rise with load (+0.72 kcal/min for +300 kcal of volume, +0.62 for +240 kcal of density: 0.0024 and 0.0026 per kcal)
K.stomach.WATER_HALF_MIN = 13 -- S1245 (Mudie 2014: 240 mL of water half-empties in 13 +/- 1 min, fasted); the fastest either lane empties
K.stomach.LIQUID_PER_KCAL = 0.12 -- S1234 over S1245 (labelled inference, ruling 11c-5): min of liquid half-time per kcal in the solid lane, fitted to Camps 2016's thin 100 and 500 kcal shakes (26.5 and 69.5 min) over water's 13 min
K.stomach.CAPACITY_G = 430 -- S1250 (labelled inference, ruling 11c-8): the comfortable capacity, van Dyck 2016's 428 mL of water to satiation taken as stomach mass at density 1
K.stomach.CAPACITY_MAX_G = 730 -- S1250 (labelled inference, ruling 11c-8): the soft cap, 734 mL of water to maximum fullness; S1251's slow nutrient drinks (937-1048 mL) bound it above
K.stomach.CAPACITY_HARD_G = 1100 -- S1253 (labelled inference): the soft cap's full scale, a balloon at maximal discomfort in lean subjects (1100 mL, n = 4)

-- A vector's mass in grams: its water, macronutrients and fibre (the vector's gram keys; calories are energy, not mass).
function K.stomach.massOf(vector)
    return vector.water + vector.proteins + vector.carbs + vector.lipids + vector.fibre
end

-- The stomach's mass: the solid buffer's mass plus the liquid lane.
function K.stomach.mass(stomach)
    return K.stomach.massOf(stomach.buffer) + (stomach.liquid or 0)
end

-- The stomach's still-unabsorbed water in both lanes (the thirst view's pending water, ruling T1-1).
function K.stomach.water(stomach)
    return stomach.buffer.water + (stomach.liquid or 0)
end

-- A drink: its water into the liquid lane, every other key (its energy among them, ruling 11c-5) into the solid
-- buffer, whose own water is kept bit for bit. The vector is not changed. Returns the stomach.
function K.stomach.ingestLiquid(stomach, vector)
    local own = stomach.buffer.water
    K.vector.add(stomach.buffer, vector, 1)
    stomach.buffer.water = own
    stomach.liquid = (stomach.liquid or 0) + (vector.water or 0)
    return stomach
end

-- The solid lane's energy delivery at energy E: RATE_BASE + RATE_PER_KCAL x E kcal a minute.
function K.stomach.solidRate(energy)
    return K.stomach.RATE_BASE + K.stomach.RATE_PER_KCAL * energy
end

-- A first-order lane's emptied fraction over dtM minutes at a half-time of halfMin minutes; nothing for no time.
function K.stomach.waterFraction(dtM, halfMin)
    if dtM <= 0 then
        return 0
    end
    return 1 - math.exp(-0.6931471805599453 * dtM / halfMin)
end

-- The liquid lane's half-time with E kcal in the solid lane (ruling 11c-5).
function K.stomach.liquidHalfMin(energy)
    return K.stomach.WATER_HALF_MIN + K.stomach.LIQUID_PER_KCAL * K.max(energy, 0)
end

-- The solid lane's emptied fraction over dtM minutes holding E kcal: the closed form of dE/dt = -(a + k E) over the
-- step (a whole buffer when the step outlasts its energy), never more than water's fraction; a lane with no energy
-- (salt, a pill, fibre alone) empties like water.
function K.stomach.solidFraction(energy, dtM)
    local fw = K.stomach.waterFraction(dtM, K.stomach.WATER_HALF_MIN)
    if energy <= 0 then
        return fw
    end
    local a = K.stomach.RATE_BASE
    local k = K.stomach.RATE_PER_KCAL
    local left = energy - a * dtM
    if k > 0 then
        left = (energy + a / k) * math.exp(-k * dtM) - a / k
    end
    local fe = 1
    if left > 0 then
        fe = K.max(0, 1 - left / energy)
    end
    return K.min(fe, fw)
end

-- Empty both lanes over dtH game hours: the solid fraction of every buffered key and the liquid lane's share of its
-- water move out as a fresh vector (the liquid's share added to its water); the buffer and the lane keep the rest.
-- The solid lane's energy before the step sets both fractions.
function K.stomach.drain(stomach, dtH)
    local dtM = dtH * 60
    local energy = stomach.buffer.calories
    local f = K.stomach.solidFraction(energy, dtM)
    local fl = K.stomach.waterFraction(dtM, K.stomach.liquidHalfMin(energy))
    local emptied = K.vector.add(K.vector.new(), stomach.buffer, f)
    local keys = K.vector.KEYS
    for i = 1, #keys do
        local k = keys[i]
        stomach.buffer[k] = stomach.buffer[k] * (1 - f)
    end
    local liquid = stomach.liquid or 0
    local lw = liquid * fl
    stomach.liquid = liquid - lw
    emptied.water = emptied.water + lw
    return emptied
end
```

Keep the file's line endings (`file` it first; it is UTF-8 LF).

- [ ] **Step 4: Run the tests to see them pass, then the kernel suite.**

Run: `python -m pytest testing/tests/kernel/test_kernel_stomach_lanes.py -q -p no:cacheprovider`
Expected: every test passes.

Run: `python -m pytest testing/tests/kernel -q -p no:cacheprovider`
Expected: all pass, `test_zz_coverage.py` included (every appended line runs), and `test_golden_trace.py` reproduces byte for byte.

- [ ] **Step 5: The gates.** Run these:
  - `python tools/mod_lint.py mod/NutritionRevamp` (0 ERROR);
  - `python tools/release_pack.py check mod/NutritionRevamp` (0 ERROR);
  - `python tools/kahlua_lint.py mod testing/experiments testing/PZTestKit` (0);
  - `python tools/hotpath_lint.py mod` (0);
  - `python tools/science_check.py --scan mod` (0);
  - `PYTHONIOENCODING=utf-8 python tools/claims_check.py --allow-provisional` (0; nothing moved);
  - `python -m pytest tools/tests testing/tests -q -p no:cacheprovider` (the baseline plus this file's tests).

- [ ] **Step 6: The cost (Rule 6).** Write `.superpowers/sdd/2026-10-08-plan-11c-satiety/bench_11c.py` with the Write tool:

```python
"""Plan 11c bench (workspace, never committed): the lupa cost of the stomach's drain, and (from Task 6) the writer
step, W.satiety and the kinetics minute. The line hook is off inside the timer, as test_plan4_steady_state.py's
replay does. Run from the repository root: python .superpowers/sdd/2026-10-08-plan-11c-satiety/bench_11c.py"""
import sys

sys.path.insert(0, "testing/tests")
from kernel.conftest import LuaHost  # noqa: E402

TIMER = r"""
function(fn, n, a, b, c, d, e, f, g)
    local hook, mask = debug.gethook()
    debug.sethook()
    local t0 = os.clock()
    for i = 1, n do
        fn(a, b, c, d, e, f, g)
    end
    local us = (os.clock() - t0) / n * 1e6
    debug.sethook(hook, mask)
    return us
end
"""
MEAL = r"""
function()
    local K = NutritionRevamp.kernel
    local st = K.stomach.new()
    local v = K.vector.new()
    v.calories = 650
    v.proteins = 24
    v.carbs = 81
    v.lipids = 25
    v.water = 300
    v.fibre = 6
    K.stomach.ingest(st, v)
    st.liquid = 250
    return st
end
"""


def best(h, fn, n, *args):
    t = h.rt.eval(TIMER)
    return min(t(fn, n, *args) for _ in range(5))


def stomach_costs():
    h = LuaHost()
    st = h.rt.eval(MEAL)()
    print("K.stomach.drain us", round(best(h, h.K.stomach.drain, 20000, st, 1 / 60), 3))
    st2 = h.rt.eval(MEAL)()
    if h.K.stomach.empty is not None:
        print("K.stomach.empty us", round(best(h, h.K.stomach.empty, 20000, st2, 1 / 60), 3))


if __name__ == "__main__":
    stomach_costs()
```

Run it and put both figures in the report. A drain that costs more than about twice `empty` is named as a concern; it runs once a player-minute, never per tick.

- [ ] **Step 7: Commit.**

```bash
git add -- testing/tests/kernel/test_kernel_stomach_lanes.py
git commit -m "Stomach: fill by mass and two lanes, a zero-order energy lane (Plan 11c Task 2)" -- mod/NutritionRevamp/common/media/lua/shared/NR_Kernel_Stomach.lua testing/tests/kernel/test_kernel_stomach_lanes.py
```

The report gives the red run's last line, the green counts, the gate results, the bench figures and the model id.

---

### Task 3: The satiety kernel — Opus implementer, Opus reviewer

The lane is M, after Task 2. It appends to `NR_Kernel_Satiety.lua`: fill, weigh, feed, decay, post, sated, seedP and discomfort (spec § 3.1 as § 5a amends it). It moves `hungerTarget`'s deficit coefficient into a named constant, `K.hybrid.DEFICIT_FLOOR`, with the same value and on the same line. Task 15's functions are untouched (Task 9 retires them), and nothing calls the new ones yet. The golden trace stays byte for byte.

**Files:**
- Modify: `mod/NutritionRevamp/common/media/lua/shared/NR_Kernel_Satiety.lua`, appending after the last line only.
- Modify: `mod/NutritionRevamp/common/media/lua/shared/NR_Kernel_Hybrid.lua`. Line 39 is edited in place (`0.15` becomes `K.hybrid.DEFICIT_FLOOR`), and one constant is appended at the end.
- Create: `testing/tests/kernel/test_kernel_satiety_physiology.py` (LF).

**Interfaces:**
- Consumes: `K.clamp`, `K.max` and `K.min`; `K.hybrid.hungerTarget(x, es)`; and the vector keys `calories`, `proteins`, `carbs` and `lipids`.
- Produces:
  - `K.satiety.W_PROTEIN = 2.5`, `W_CARB = 1`, `W_FAT = 1`, `W_NEUTRAL = 1`, `HALF_LIFE_H = 2.0`, `P50 = 150`, `FULL_WEIGHT = 0.5`, `PN_MAX = 0.99`, `DISCOMFORT_MAX = 100`, `ATWATER_P = 4`, `ATWATER_C = 4` and `ATWATER_F = 9`.
  - `K.satiety.fill(mass, capacity) -> F`.
  - `K.satiety.weigh(vector) -> weighted kcal` and `K.satiety.feed(P, vector) -> P`.
  - `K.satiety.decay(P, dtH, halfLifeH, trait) -> P`, `K.satiety.post(P) -> Pn` and `K.satiety.sated(F, Pn) -> Z`.
  - `K.satiety.seedP(hunger, F, energyState) -> P`.
  - `K.satiety.discomfort(mass, capMax, capHard) -> 0..DISCOMFORT_MAX`.
  - `K.hybrid.DEFICIT_FLOOR = 0.15`.

- [ ] **Step 1: Write the failing tests.** Create `testing/tests/kernel/test_kernel_satiety_physiology.py`:

```python
"""Satiety from physiology (Plan 11c Task 3; spec § 3.1 and § 5a): K.satiety.fill, weigh, feed, decay, post, sated,
seedP and discomfort, and K.hybrid.DEFICIT_FLOOR, on the kernel host. Hand-computed from the constants; the oracle
(test_satiety_meal_studies.py) replays the studies."""
import os
import re

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
SHARED = os.path.join(REPO, "mod", "NutritionRevamp", "common", "media", "lua", "shared")
NAMES = ("W_PROTEIN", "W_CARB", "W_FAT", "W_NEUTRAL", "HALF_LIFE_H", "P50", "FULL_WEIGHT", "PN_MAX", "DISCOMFORT_MAX",
         "ATWATER_P", "ATWATER_C", "ATWATER_F")


def _vec(host, **kw):
    v = host.K.vector["new"]()
    for k, val in kw.items():
        v[k] = val
    return v


def test_the_constants(host):
    S = host.K.satiety
    assert (S.W_PROTEIN, S.W_CARB, S.W_FAT, S.W_NEUTRAL) == (2.5, 1, 1, 1)
    assert (S.HALF_LIFE_H, S.P50, S.FULL_WEIGHT, S.PN_MAX, S.DISCOMFORT_MAX) == (2.0, 150, 0.5, 0.99, 100)
    assert (S.ATWATER_P, S.ATWATER_C, S.ATWATER_F) == (4, 4, 9)
    assert host.K.hybrid.DEFICIT_FLOOR == 0.15


def test_each_constant_names_its_row_or_its_label():
    with open(os.path.join(SHARED, "NR_Kernel_Satiety.lua"), encoding="utf-8") as fh:
        src = fh.read()
    for name in NAMES:
        line = re.search(r"^K\.satiety\.%s = .*$" % name, src, re.M).group(0)
        assert re.search(r"S\d{4}|game choice|neutral|CharacterStat", line), name
    for name in ("W_PROTEIN", "HALF_LIFE_H", "P50"):
        line = re.search(r"^K\.satiety\.%s = .*$" % name, src, re.M).group(0)
        assert "game choice" in line and "open" in line, name           # an open row is never cited as evidence
    with open(os.path.join(SHARED, "NR_Kernel_Hybrid.lua"), encoding="utf-8") as fh:
        hyb = fh.read()
    line = re.search(r"^K\.hybrid\.DEFICIT_FLOOR = .*$", hyb, re.M).group(0)
    assert "game choice" in line and "S1271 open" in line


def test_fill_is_mass_over_capacity_clamped(host):
    assert host.call("satiety.fill", 215, 430) == 0.5
    assert host.call("satiety.fill", 900, 430) == 1
    assert host.call("satiety.fill", -5, 430) == 0


def test_weigh_splits_the_calories_by_atwater_share(host):
    v = _vec(host, calories=400, proteins=25, carbs=50, lipids=200 / 9)      # 100, 200 and 200 kcal by Atwater
    assert host.call("satiety.weigh", v) == pytest.approx(400 * (2.5 * 100 + 200 + 200) / 500)


def test_the_delivered_calories_govern_the_energy(host):
    # macros summing to 500 kcal by Atwater on a vector that delivered 250 kcal: weighed at 250 (spec § 3.2)
    v = _vec(host, calories=250, proteins=25, carbs=50, lipids=200 / 9)
    assert host.call("satiety.weigh", v) == pytest.approx(250 * (2.5 * 100 + 200 + 200) / 500)


def test_a_vector_with_no_macros_takes_the_neutral_weight(host):
    assert host.call("satiety.weigh", _vec(host, calories=120)) == 120
    assert host.call("satiety.weigh", _vec(host)) == 0


def test_feed_adds_the_weighed_kcal(host):
    assert host.call("satiety.feed", 50, _vec(host, calories=100, carbs=25)) == pytest.approx(150)
    assert host.call("satiety.feed", 50, _vec(host, calories=40, proteins=10)) == pytest.approx(150)


def test_decay_halves_the_pool_each_half_life(host):
    assert host.call("satiety.decay", 80, 2.0, 2.0, 1) == pytest.approx(40)
    assert host.call("satiety.decay", 80, 2.0, 2.0, 1.5) == pytest.approx(80 * 2 ** -1.5)
    assert host.call("satiety.decay", 80, 0, 2.0, 1) == 80
    assert host.call("satiety.decay", 80, -1, 2.0, 1) == 80


def test_post_saturates_at_its_half_point(host):
    assert host.call("satiety.post", 150) == 0.5
    assert host.call("satiety.post", 450) == 0.75
    assert host.call("satiety.post", 0) == 0
    assert host.call("satiety.post", -3) == 0


def test_sated_compounds_the_two_signals(host):
    assert host.call("satiety.sated", 0, 0) == 0
    assert host.call("satiety.sated", 1, 0) == 0.5
    assert host.call("satiety.sated", 0, 0.5) == 0.5
    assert host.call("satiety.sated", 1, 0.5) == 0.75


@pytest.mark.parametrize("hunger,F,es", [(0.31, 0.6, 1), (0.25, 0, 1), (0.5, 0.2, 1.4), (0.2, 0.3, 0.9)])
def test_seed_p_inverts_the_hunger_function(host, hunger, F, es):
    P = host.call("satiety.seedP", hunger, F, es)
    z = host.call("satiety.sated", F, host.call("satiety.post", P))
    assert host.call("hybrid.hungerTarget", z, es) == pytest.approx(hunger)


def test_seed_p_clamps_what_it_cannot_reach(host):
    P = host.call("satiety.seedP", 0, 0, 1)                          # HUNGER 0: the ceiling, a finite pool
    assert P == pytest.approx(150 * 0.99 / 0.01) and host.call("satiety.post", P) == pytest.approx(0.99)
    assert host.call("satiety.seedP", 0.6, 0.9, 0.8) == 0            # hungrier than an empty pool gives at this F
    assert host.call("satiety.seedP", 0.3, 0, 0) == 0                # no energy state
    assert host.call("satiety.seedP", 0.3, 2.5, 1) == 0              # a fullness past 1 / FULL_WEIGHT


def test_discomfort_is_linear_from_the_soft_cap_to_the_hard_capacity(host):
    assert host.call("satiety.discomfort", 700, 730, 1100) == 0
    assert host.call("satiety.discomfort", 915, 730, 1100) == pytest.approx(50)
    assert host.call("satiety.discomfort", 1500, 730, 1100) == 100


def test_hunger_target_reads_the_named_deficit_floor(host):
    assert host.call("hybrid.hungerTarget", 1, 1.5) == pytest.approx(0.15 * 0.5)
    assert host.call("hybrid.hungerTarget", 0.7, 1.5) == pytest.approx(0.3 * 1.5 + 0.15 * 0.5)
```

- [ ] **Step 2: Run them to see them fail.**

Run: `python -m pytest testing/tests/kernel/test_kernel_satiety_physiology.py -q -p no:cacheprovider`
Expected: FAIL (`W_PROTEIN` is nil; `attempt to call a nil value (field 'fill')`). `test_hunger_target_reads_the_named_deficit_floor` passes on the pre-change tree: it is a **follow-up pin**, and the report labels it so.

- [ ] **Step 3: Edit `NR_Kernel_Hybrid.lua`.**
  - Replace line 39's body in place, keeping its line, so that it reads:

```lua
    return K.clamp((1 - x) * energyState + K.hybrid.DEFICIT_FLOOR * K.max(0, energyState - 1), 0, 1)
```

  - Change the comment above it (lines 35–37) in place, keeping three lines:

```lua
-- The hunger target from a fill-like scalar x (0 empty .. 1 sated: since Plan 11c the satiety read Z) and the energy
-- state (Plan 3 ruling 14, moved from the takeover's K.fast.hungerTarget): (1 - x) x energyState, plus a deficit
-- floor DEFICIT_FLOOR x (energyState - 1), clamped to [0, 1].
```

  - Append at the end of the file:

```lua

K.hybrid.DEFICIT_FLOOR = 0.15 -- game choice (S1271 open; Plan 3 ruling 14): the deficit floor's coefficient; S1254 sets its direction and S1255 bounds it (CALERIE 2: < 10 mm over 2 y at a 25 % deficit), which the oracle checks
```

- [ ] **Step 4: Append the satiety implementation** at the end of `NR_Kernel_Satiety.lua`:

```lua

-- Plan 11c (spec § 3.1 and § 5a): satiety from physiology. Two signals sate: the stomach's fullness F (its mass over
-- its comfortable capacity, K.stomach.CAPACITY_G) and a post-absorptive pool P of weighted kcal, fed by the energy
-- leaving the stomach and decaying first-order. Hunger is K.hybrid.hungerTarget(sated(F, post(P)), energyState).
-- Appended below Task 15's code so no line above moves; Task 9 retires that code. Pure; one statement a line.
K.satiety.W_PROTEIN = 2.5 -- game choice (S1268 open; ruling 11c-7): protein satiates more per kcal (S1222, S1223, S1224); the size is fitted so the oracle's Marmonier replay lands its protein-to-carbohydrate delay ratio in 1.5-2.0 (S1224: 60 against 34 min)
K.satiety.W_CARB = 1 -- neutral (ruling 11c-7): carbohydrate against fat is disputed (S1226, S1227, S1228, S1229), so both take the common weight; not an evidenced tie
K.satiety.W_FAT = 1 -- neutral (ruling 11c-7), as W_CARB
K.satiety.W_NEUTRAL = 1 -- neutral (spec § 3.1): the common weight of a vector with no macronutrient grams
K.satiety.HALF_LIFE_H = 2.0 -- game choice (S1270 open): P's half-life in game hours, fitted with P50 and W_PROTEIN so a 650 kcal mixed meal's hunger returns in 4-5 h (S1247: 247-321 min; S1248: 320-425 min)
K.satiety.P50 = 150 -- game choice (S1270 open): the pool's half-point in weighted kcal, fitted with HALF_LIFE_H
K.satiety.FULL_WEIGHT = 0.5 -- game choice (no row): fullness's weight in the sated product, bounded by the oracle's S1231 null and S1232 direction; S1235 has fullness track gastric volume
K.satiety.PN_MAX = 0.99 -- game choice: seedP's ceiling on the post-absorptive read, so a HUNGER of 0 seeds a finite pool (99 x P50)
K.satiety.DISCOMFORT_MAX = 100 -- not science: the DISCOMFORT stat's range, 0-100 (CharacterStat.<clinit> registers 'Discomfort' with 0.0 and 100.0; Task 5 cites it on 42.21)
K.satiety.ATWATER_P = 4 -- S1209 (Atwater general factors: protein 4.0 kcal/g)
K.satiety.ATWATER_C = 4 -- S1209 (carbohydrate 4.0 kcal/g)
K.satiety.ATWATER_F = 9 -- S1209 (fat 9.0 kcal/g)

-- The fullness F: mass over capacity, clamped to [0, 1] (liquid and food taken at density 1, ruling 11c-8).
function K.satiety.fill(mass, capacity)
    return K.clamp(mass / capacity, 0, 1)
end

-- A vector's weighted kcal: its delivered calories split by the Atwater share of its protein, carbohydrate and fat
-- grams, each share times its weight; a vector with no macronutrient grams takes the neutral weight.
function K.satiety.weigh(vector)
    local p = K.satiety.ATWATER_P * vector.proteins
    local c = K.satiety.ATWATER_C * vector.carbs
    local f = K.satiety.ATWATER_F * vector.lipids
    local atwater = p + c + f
    if atwater <= 0 then
        return vector.calories * K.satiety.W_NEUTRAL
    end
    return vector.calories * (K.satiety.W_PROTEIN * p + K.satiety.W_CARB * c + K.satiety.W_FAT * f) / atwater
end

-- Feed the pool with the vector that left the stomach this step.
function K.satiety.feed(P, vector)
    return P + K.satiety.weigh(vector)
end

-- First-order decay over dtH game hours at the half-life, scaled by trait (the appetite trait times the sandbox's
-- stats-decrease multiplier, ruling 11c-11); nothing for no time.
function K.satiety.decay(P, dtH, halfLifeH, trait)
    if dtH <= 0 then
        return P
    end
    return P * math.exp(-0.6931471805599453 * dtH * trait / halfLifeH)
end

-- The saturating post-absorptive read P / (P + P50), in [0, 1).
function K.satiety.post(P)
    if P <= 0 then
        return 0
    end
    return P / (P + K.satiety.P50)
end

-- Sated: either signal sates and together they compound, 1 - (1 - FULL_WEIGHT x F) x (1 - Pn).
function K.satiety.sated(F, Pn)
    return 1 - (1 - K.satiety.FULL_WEIGHT * F) * (1 - Pn)
end

-- The migration seed (spec § 4): the P for which hungerTarget(sated(F, post(P)), energyState) equals hunger, its
-- read clamped to [0, PN_MAX]; 0 where no P reaches it.
function K.satiety.seedP(hunger, F, energyState)
    if energyState <= 0 then
        return 0
    end
    local free = (hunger - K.hybrid.DEFICIT_FLOOR * K.max(0, energyState - 1)) / energyState
    local rest = 1 - K.satiety.FULL_WEIGHT * F
    if rest <= 0 then
        return 0
    end
    local pn = K.clamp(1 - free / rest, 0, K.satiety.PN_MAX)
    return K.satiety.P50 * pn / (1 - pn)
end

-- The soft cap's discomfort (ruling 11c-13): 0 up to capMax grams, DISCOMFORT_MAX at capHard, linear between.
function K.satiety.discomfort(mass, capMax, capHard)
    return K.satiety.DISCOMFORT_MAX * K.clamp((mass - capMax) / (capHard - capMax), 0, 1)
end
```

- [ ] **Step 5: Run the tests, the kernel suite and the hybrid tests.**

Run: `python -m pytest testing/tests/kernel/test_kernel_satiety_physiology.py testing/tests/kernel/test_kernel_hybrid.py -q -p no:cacheprovider`
Expected: all pass.

Run: `python -m pytest testing/tests/kernel -q -p no:cacheprovider`
Expected: all pass. Coverage stays at 100 %, and the golden trace reproduces byte for byte (`hungerTarget`'s value is unchanged).

- [ ] **Step 6: The gates**, as Task 2 Step 5. The full `claims_check` may name a row quoting `NR_Kernel_Hybrid.lua:39` or its comment lines (`pointer-quote`). List each one for the controller; do not edit the register.

- [ ] **Step 7: Commit.**

```bash
git add -- testing/tests/kernel/test_kernel_satiety_physiology.py
git commit -m "Satiety kernel: fill, weigh, feed, decay, post, sated, seedP, discomfort (Plan 11c Task 3)" -- mod/NutritionRevamp/common/media/lua/shared/NR_Kernel_Satiety.lua mod/NutritionRevamp/common/media/lua/shared/NR_Kernel_Hybrid.lua testing/tests/kernel/test_kernel_satiety_physiology.py
```

---
### Task 4: The oracle — the meal studies replayed — Opus implementer, Opus reviewer (the mutation pass)

The lane is M, after Task 3. This task creates `testing/tests/kernel/test_satiety_meal_studies.py`. It replays the published protocols through the real kernels, one step a game minute, in the order the server's kinetics and writer run them: drain, feed, decay, read. Each test names its science rows. The file is the oracle of CLAUDE.md § 6: it is accepted only after its reviewer's mutation pass (Step 6). No `mod/` file changes.

**Files:**
- Create: `testing/tests/kernel/test_satiety_meal_studies.py` (LF).
- Create (reviewer's workspace, never committed): `.superpowers/sdd/2026-10-08-plan-11c-satiety/mutate_11c.py`.

**Interfaces:**
- Consumes, from Task 2: `K.stomach.new`, `ingest`, `ingestLiquid`, `drain`, `mass`, `solidRate` and `CAPACITY_G`.
- Consumes, from Task 3: `K.satiety.fill`, `feed`, `decay`, `post`, `sated`, `seedP`, `HALF_LIFE_H`, `K.hybrid.hungerTarget` and `K.hybrid.DEFICIT_FLOOR`.
- Consumes, existing: `K.energy.state(eb24h, fatDep, g)`.
- Produces: every test function takes only `host`, so the mutation script calls each one on a patched host. No test uses `parametrize`.

- [ ] **Step 1: Write the oracle.** Create `testing/tests/kernel/test_satiety_meal_studies.py`:

```python
"""The satiety oracle (Plan 11c Task 4; spec § 6): published protocols replayed through the real kernels -- the
stomach's two lanes (K.stomach), the satiety pool (K.satiety) and the hunger function (K.hybrid.hungerTarget) -- one
step a game minute, in the order the server's kinetics and writer steps run them (drain, feed, decay, read). Each test
names the science rows it rests on (docs/reference/science.tsv) and asserts the model lands inside the study's range or
ordering; a band that is not the study's own is labelled the oracle's tolerance.

The meal request is read at HUNGER 0.25, vanilla's HUNGRY level 2 (Appendix D's ladder 0.15, 0.25, 0.45, 0.70; #0508
is its level-4 rung): a game choice mapping a study's spontaneous meal request onto the moodle a player acts on
(ruling 11c-17). A replay starts at that request with an empty stomach, P = seedP(0.25, 0, 1), at energy balance
(energyState 1) unless a test says otherwise.

What the model does not reproduce, named so a reader does not take the oracle for more than it is:
- S1247's dose slope: the model's interval grows faster with preload energy than Callahan 2004's 247-321 min over
  7.5-33 % of daily energy (a 190 kcal preload returns hunger in well under 247 min); the oracle asserts the order.
- S1224's absolute delays (25-60 min): the model's snack keeps the stomach delivering energy for over an hour, so
  its delays are longer; the oracle asserts the order and the protein-to-carbohydrate ratio.
- S1231's 17-minute lunch: both the soup and the casserole with its water exceed the comfortable capacity, where
  fullness is clamped at 1, so the soup test reads Marciani's 3-hour window (S1232); S1231's null for water drunk
  alongside is checked within the oracle's 0.07 tolerance instead.

Accepted only after the mutation pass (CLAUDE.md § 6; Plan 11c Task 4 Step 6): each of W_PROTEIN, HALF_LIFE_H, P50,
FULL_WEIGHT, LIQUID_PER_KCAL, WATER_HALF_MIN, RATE_BASE, RATE_PER_KCAL and DEFICIT_FLOOR patched one at a time to its
neutral or off value, x2 and x0.5, and the liquid lane's routing swapped, fails at least one test below. Every test
takes only `host`, so the reviewer's script calls each on a patched host.
"""
import pytest

H_REQ = 0.25                    # the meal request: vanilla's HUNGRY level 2 (ruling 11c-17, a game choice)

# The replay runs with the coverage line hook off (every line it runs is covered by the kernels' own tests).
REPLAY = r"""
function(events, minutes, P0, es)
    local K = NutritionRevamp.kernel
    local hook, mask = debug.gethook()
    debug.sethook()
    local st = K.stomach.new()
    local P = P0
    local hs = {}
    local ms = {}
    for m = 0, minutes - 1 do
        local list = events[m]
        if list ~= nil then
            for i = 1, #list do
                local e = list[i]
                local v = K.vector.new()
                for k, x in pairs(e.vec) do
                    v[k] = x
                end
                if e.kind == "drink" then
                    K.stomach.ingestLiquid(st, v)
                else
                    K.stomach.ingest(st, v)
                end
            end
        end
        local emptied = K.stomach.drain(st, 1 / 60)
        P = K.satiety.feed(P, emptied)
        P = K.satiety.decay(P, 1 / 60, K.satiety.HALF_LIFE_H, 1)
        local F = K.satiety.fill(K.stomach.mass(st), K.stomach.CAPACITY_G)
        hs[m + 1] = K.hybrid.hungerTarget(K.satiety.sated(F, K.satiety.post(P)), es)
        ms[m + 1] = K.stomach.mass(st)
    end
    debug.sethook(hook, mask)
    return hs, ms
end
"""

ENERGY = r"""
function(vec, minutes, drink)
    local K = NutritionRevamp.kernel
    local hook, mask = debug.gethook()
    debug.sethook()
    local st = K.stomach.new()
    local v = K.vector.new()
    for k, x in pairs(vec) do
        v[k] = x
    end
    if drink then
        K.stomach.ingestLiquid(st, v)
    else
        K.stomach.ingest(st, v)
    end
    local out = {}
    for m = 1, minutes do
        K.stomach.drain(st, 1 / 60)
        out[m] = st.buffer.calories
    end
    debug.sethook(hook, mask)
    return out
end
"""


# --- the meals (grams; Atwater 4/4/9 for the macronutrient shares) ------------------------------------------------

def mixed(kcal, water=300.0, fibre=6.0, p=0.15, c=0.50, f=0.35):
    """A mixed meal: 15 % protein, 50 % carbohydrate, 35 % fat by energy (an illustrative meal, a game choice)."""
    return {"calories": kcal, "proteins": kcal * p / 4, "carbs": kcal * c / 4, "lipids": kcal * f / 9,
            "water": water, "fibre": fibre}


def snack(kcal, main, share, water=150.0):
    """A preload whose main macronutrient carries `share` of its energy and the other two split the rest."""
    s = {"proteins": (1 - share) / 2, "carbs": (1 - share) / 2, "lipids": (1 - share) / 2}
    s[main] = share
    return {"calories": kcal, "proteins": kcal * s["proteins"] / 4, "carbs": kcal * s["carbs"] / 4,
            "lipids": kcal * s["lipids"] / 9, "water": water}


def preload(kcal, water=400.0):
    """A liquid preload of fixed volume (S1247's preloads were equal in volume): 50/20/30 carbohydrate/protein/fat."""
    return {"calories": kcal, "carbs": kcal * 0.5 / 4, "proteins": kcal * 0.2 / 4, "lipids": kcal * 0.3 / 9,
            "water": water}


def shake(kcal, ml=500.0):
    """S1234's 500 mL dairy shake: 50 % carbohydrate, 20 % protein, 30 % fat by energy, water the rest of its mass."""
    solids = kcal * 0.5 / 4 + kcal * 0.2 / 4 + kcal * 0.3 / 9
    return {"calories": kcal, "carbs": kcal * 0.5 / 4, "proteins": kcal * 0.2 / 4, "lipids": kcal * 0.3 / 9,
            "water": ml - solids}


CASSEROLE = {"calories": 270.0, "proteins": 20.0, "carbs": 25.0, "lipids": 10.0, "water": 200.0, "fibre": 4.0}
SOUP = dict(CASSEROLE, water=CASSEROLE["water"] + 356.0)     # S1231: the same casserole with its 356 g of water in it
WATER = {"water": 356.0}                                      # the same water drunk alongside


def mass_of(vec):
    return sum(vec.get(k, 0.0) for k in ("water", "proteins", "carbs", "lipids", "fibre"))


# --- the replay ---------------------------------------------------------------------------------------------------

def lua_events(host, events):
    t = host.rt.table()
    for minute, items in events.items():
        lst = host.rt.table()
        for i, (kind, vec) in enumerate(items, 1):
            lst[i] = host.table({"kind": kind, "vec": vec})
        t[minute] = lst
    return t


def start_p(host, es=1.0):
    return host.call("satiety.seedP", H_REQ, 0, es)


def start_hunger(host, es=1.0):
    z = host.call("satiety.sated", 0, host.call("satiety.post", start_p(host, es)))
    return host.call("hybrid.hungerTarget", z, es)


def replay(host, events, minutes, P0=None, es=1.0):
    if P0 is None:
        P0 = start_p(host, es)
    hs, ms = host.rt.eval(REPLAY)(lua_events(host, events), minutes, P0, es)
    return [hs[i] for i in range(1, minutes + 1)], [ms[i] for i in range(1, minutes + 1)]


def returns_at(hs, h0, after=5):
    """The minute (1-based, after the event at minute 0) at which hunger is back at h0, or None."""
    for i, x in enumerate(hs):
        if i > after and x >= h0 - 1e-12:
            return i + 1
    return None


def half_emptied(host, events, minutes=600):
    m0 = sum(mass_of(v) for items in events.values() for _, v in items)
    _, ms = replay(host, events, minutes, P0=0)
    for i, m in enumerate(ms):
        if m <= m0 / 2:
            return i + 1
    return None


# --- time to returning hunger (S1247, S1248; spec § 2 item 2) --------------------------------------------------------

def test_a_650_kcal_mixed_meal_holds_hunger_off_for_four_to_five_hours(host):
    # S1247: 247-321 min to a meal request after liquid preloads; S1248: 320-425 min lunch to dinner, time-blinded;
    # the spec's anchor is 4-5 game hours, inside both and slightly conservative (spec § 5a)
    hs, _ = replay(host, {0: [("food", mixed(650))]}, 900)
    t = returns_at(hs, start_hunger(host))
    assert t is not None and 240 <= t <= 300, t


def test_a_larger_preload_holds_hunger_off_longer(host):
    # S1247: 7.5, 16 and 33 % of a 2500 kcal day (a game-choice reference day) as equal-volume liquid preloads; the
    # intervals rose with energy (P = 0.015). The oracle asserts the order only (the docstring's first limit).
    h0 = start_hunger(host)
    ts = [returns_at(replay(host, {0: [("drink", preload(k))]}, 900)[0], h0) for k in (190.0, 400.0, 825.0)]
    assert None not in ts and ts[0] < ts[1] < ts[2], ts


# --- protein against carbohydrate and fat (S1222, S1223, S1224; ruling 11c-7) -----------------------------------------

def test_a_protein_snack_delays_the_next_meal_more_than_carbohydrate_or_fat(host):
    # S1224 (Marmonier 2000): a 1 MJ (239 kcal) snack 240 min after the start of lunch, in a satiety state, delayed
    # the dinner request by 60 min (77 % protein), 34 min (84 % carbohydrate) and 25 min (58 % fat)
    h0 = start_hunger(host)
    base = returns_at(replay(host, {0: [("food", mixed(650))]}, 1500)[0], h0)
    assert base is not None and base > 240, base          # the snack lands in a satiety state, as in the protocol
    delay = {}
    for name, main, share in (("p", "proteins", 0.77), ("c", "carbs", 0.84), ("f", "lipids", 0.58)):
        hs, _ = replay(host, {0: [("food", mixed(650))], 240: [("food", snack(239.0, main, share))]}, 1500)
        delay[name] = returns_at(hs, h0, after=245) - base
    assert delay["p"] > delay["c"] and delay["p"] > delay["f"], delay
    assert 1.5 <= delay["p"] / delay["c"] <= 2.0, delay  # S1224: 60 / 34 = 1.76; the band is the oracle's tolerance


def test_a_protein_preload_leaves_less_hunger_than_an_isoenergetic_carbohydrate_one(host):
    # S1222 (Kohanmoo 2020, MA: hunger -7 mm), S1223 (Dhillon 2016, MA: fullness AUC up over 240 min): direction
    hp, _ = replay(host, {0: [("food", snack(400.0, "proteins", 0.40))]}, 240)
    hc, _ = replay(host, {0: [("food", snack(400.0, "carbs", 0.40))]}, 240)
    assert sum(c - p for p, c in zip(hp, hc)) / 240 > 0


# --- volume: water in the food against water drunk alongside (S1231, S1232; ruling 11c-5) ----------------------------

def test_soup_sates_more_than_the_same_casserole_with_its_water_drunk(host):
    # S1232 (Marciani 2012): the soup reduced hunger over 3 h and its gastric volume fell more slowly
    hs_s, ms_s = replay(host, {0: [("food", SOUP)]}, 180)
    hs_w, ms_w = replay(host, {0: [("food", CASSEROLE), ("drink", WATER)]}, 180)
    assert sum(w - s for s, w in zip(hs_s, hs_w)) / 180 > 0
    assert ms_s[59] > ms_w[59] and ms_s[119] > ms_w[119]


def test_water_drunk_alongside_adds_little_at_the_lunch(host):
    # S1231 (Rolls 1999): water served as a beverage did not affect satiety (1657 against 1639 kJ at lunch, 17 min on);
    # the model's water still sits in the liquid lane then, so the null is checked within 0.07 -- the oracle's
    # tolerance, S1222's 7 mm pooled protein effect taken as the smallest effect the literature calls real
    hs_c, _ = replay(host, {0: [("food", CASSEROLE)]}, 17)
    hs_w, _ = replay(host, {0: [("food", CASSEROLE), ("drink", WATER)]}, 17)
    assert 0 <= hs_c[16] - hs_w[16] <= 0.07, hs_c[16] - hs_w[16]


# --- gastric emptying (S1245, S1234, S0131, S1272; rulings 11c-4 and 11c-5) -------------------------------------------

def test_water_alone_half_empties_in_about_13_minutes(host):
    # S1245 (Mudie 2014): 240 mL of water, T50 13 +/- 1 min (SEM); the band is +/- 2 SEM
    t = half_emptied(host, {0: [("drink", {"water": 240.0})]})
    assert t is not None and 11 <= t <= 15, t


def test_thin_shakes_half_empty_by_their_energy(host):
    # S1234 (Camps 2016): thin 500 mL shakes, 100 kcal 26.5 +/- 3.0 min and 500 kcal 69.5 +/- 5.9 min; bands +/- 2 SEM
    t100 = half_emptied(host, {0: [("drink", shake(100.0))]})
    t500 = half_emptied(host, {0: [("drink", shake(500.0))]})
    assert t100 is not None and 20.5 <= t100 <= 32.5, t100
    assert t500 is not None and 57.7 <= t500 <= 81.3, t500


def test_the_solid_lane_empties_about_two_to_three_kcal_a_minute(host):
    # S0131 (Hunt 1985): an overall mean 2.5 kcal/min over glucose-polymer meals of 300-600 mL at 0.5-2.0 kcal/mL;
    # a 450 mL meal at 1.2 kcal/mL, its first hour; the band 2-3 is spec § 5a's "about 2-3 kcal/min"
    left = host.rt.eval(ENERGY)(host.table({"calories": 540.0, "carbs": 135.0, "water": 315.0}), 60, True)
    rate = (540.0 - left[60]) / 60
    assert 2.0 <= rate <= 3.0, rate


def test_the_solid_rate_rises_with_load_as_hunts_volume_doubling(host):
    # S0131: doubling the volume from 300 to 600 mL raised the steady rate by a mean 0.72 kcal/min (at 1 kcal/mL);
    # the band 0.5-1.0 is the oracle's tolerance
    rise = host.call("stomach.solidRate", 600.0) - host.call("stomach.solidRate", 300.0)
    assert 0.5 <= rise <= 1.0, rise


def test_a_solid_meal_empties_its_energy_near_linearly(host):
    # S1272 (Moore 1981): solid-phase emptying is linear, not exponential. t50 / t90 is 0.556 for a linear course and
    # 0.301 for an exponential one; the model must sit nearer the linear (above their midpoint 0.428)
    left = host.rt.eval(ENERGY)(host.table(mixed(650)), 600, False)
    seq = [left[i] for i in range(1, 601)]
    t50 = next(i + 1 for i, e in enumerate(seq) if e <= 325.0)
    t90 = next(i + 1 for i, e in enumerate(seq) if e <= 65.0)
    assert t50 / t90 > (0.5556 + 0.3010) / 2, (t50, t90)


# --- the deficit drive (S1254, S1255; the floor a game choice, S1271 open) ----------------------------------------

def test_a_25_percent_deficit_raises_the_pre_meal_hunger_by_less_than_ten_points(host):
    # a 25 % deficit of a 2500 kcal day (CALERIE 2's target; the day a game choice) through K.energy.state;
    # S1254 (Polidori 2016): appetite rises under a deficit; S1255 (Dorling 2020): VAS hunger rose < 10 mm over 2 y
    es = host.call("energy.state", -625.0, 0, 1)
    z = host.call("satiety.sated", 0, host.call("satiety.post", start_p(host)))
    rise = host.call("hybrid.hungerTarget", z, es) - host.call("hybrid.hungerTarget", z, 1.0)
    assert 0 < rise <= 0.10, rise


def test_the_deficit_floor_is_its_game_choice(host):
    # a pin, not evidence: the floor's coefficient is a game choice (S1271 open); a full stomach under a deficit
    # still reads the floor
    es = host.call("energy.state", -625.0, 0, 1)
    assert host.K.hybrid.DEFICIT_FLOOR == 0.15
    assert host.call("hybrid.hungerTarget", 1, es) == pytest.approx(0.15 * (es - 1))
```

- [ ] **Step 2: Run it on the tree.** The kernels exist (Tasks 2 and 3), so the oracle is green the moment it is written; that is its nature as an oracle and not a red-run task. Its red run is the mutation pass (Step 6).

Run: `python -m pytest testing/tests/kernel/test_satiety_meal_studies.py -v -p no:cacheprovider`
Expected: 13 passed.

These are the expected readings. They were measured on a Python mirror of the kernels on 2026-10-08, and the lupa run must agree to the minute or within 1e-6:
- the 650 kcal interval: 274 min;
- the preloads: 85, 164 and 342 min;
- the Marmonier base: 274; the delays: p 197, c 110 and f 125 (a ratio of 1.79);
- the Kohanmoo mean: 0.008;
- the soup mean: 0.0153, with masses ahead by 93.5 g at minute 60 and 67.6 g at minute 120;
- the 17-minute water arm: 0.0585;
- water: 13 min; the shakes: 24 and 72 min;
- Hunt: 2.414 kcal/min; the slope: 0.75;
- t50/t90: 133/285;
- the deficit rise: 0.0833.

Put the lupa readings in the report. Print them with a scratch script, never by editing the test.

A test that fails on the tree is a STOP: report it with its reading and do not change a band. The controller rules on it, either fixing a constant in Tasks 2–3 through a fix round or changing the test's protocol reading with the reason ledgered.

- [ ] **Step 3: The suite.**

Run: `python -m pytest testing/tests/kernel -q -p no:cacheprovider`
Expected: all pass. The golden trace is unchanged and coverage is unchanged (the replay turns the line hook off and touches no new kernel line).

- [ ] **Step 4: The gates.** No `mod/` file changed, so run `python -m pytest tools/tests testing/tests -q -p no:cacheprovider` and `PYTHONIOENCODING=utf-8 python tools/claims_check.py --staged --allow-provisional` (it skips when nothing staged is under its paths).

- [ ] **Step 5: Commit.**

```bash
git add -- testing/tests/kernel/test_satiety_meal_studies.py
git commit -m "Oracle: the satiety meal studies replayed through the kernels (Plan 11c Task 4)" -- testing/tests/kernel/test_satiety_meal_studies.py
```

- [ ] **Step 6 (the reviewer, Opus, read-only): The mutation pass.** The reviewer writes `.superpowers/sdd/2026-10-08-plan-11c-satiety/mutate_11c.py` with the Write tool and runs it from the repository root. It edits no tracked file: every mutation is a field set on a fresh host's kernel table.

```python
"""Plan 11c Task 4 review: the oracle's mutation pass (CLAUDE.md § 6). Each mutation patches one constant (or the
liquid lane's routing) on a fresh kernel host and runs every oracle test on it; each must fail at least one test.
Workspace only: no tracked file is edited."""
import sys

sys.path.insert(0, "testing/tests")
from kernel.conftest import LuaHost  # noqa: E402
from kernel import test_satiety_meal_studies as O  # noqa: E402

TESTS = [getattr(O, n) for n in sorted(dir(O)) if n.startswith("test_")]
MUTATIONS = [
    ("satiety", "W_PROTEIN", [1, 5.0, 1.25]),
    ("satiety", "HALF_LIFE_H", [4.0, 1.0]),
    ("satiety", "P50", [300, 75]),
    ("satiety", "FULL_WEIGHT", [0, 1.0, 0.25]),
    ("stomach", "LIQUID_PER_KCAL", [0, 0.24, 0.06]),
    ("stomach", "WATER_HALF_MIN", [26, 6.5]),
    ("stomach", "RATE_BASE", [2.5, 0.625]),
    ("stomach", "RATE_PER_KCAL", [0.005, 0.00125]),
    ("hybrid", "DEFICIT_FLOOR", [0, 0.3]),
]


def failing(h):
    out = []
    for t in TESTS:
        try:
            t(h)
        except AssertionError:
            out.append(t.__name__)
    return out


base = failing(LuaHost())
print("unpatched:", base)
assert base == [], "the oracle must pass unpatched"
survivors = []
for mod, name, values in MUTATIONS:
    for v in values:
        h = LuaHost()
        h.K[mod][name] = v
        f = failing(h)
        print(mod, name, v, "->", len(f), f)
        if not f:
            survivors.append((mod, name, v))
h = LuaHost()
h.K.stomach.ingestLiquid = h.K.stomach.ingest           # the liquid lane's routing swapped: a drink lands as food
f = failing(h)
print("routing -> ", len(f), f)
if not f:
    survivors.append(("stomach", "ingestLiquid", "ingest"))
print("SURVIVORS:", survivors)
```

The expected result (the Python mirror, 2026-10-08) is that every mutation fails at least one test:
- `W_PROTEIN` 1 / 5 / 1.25 fail the Marmonier ratio (0.99, 2.06 and 1.12);
- `HALF_LIFE_H` 4 / 1 fail the 650 kcal interval (461 and 130 min);
- `P50` 300 / 75 fail it too (162 and 407 min);
- `FULL_WEIGHT` 0 fails the soup (a difference of exactly 0), 1 fails the water arm (0.117) and 0.25 fails the Marmonier ratio (2.24);
- `LIQUID_PER_KCAL` 0 / 0.24 / 0.06 fail the shakes (18, 105 and 49 min for the 500 kcal shake);
- `WATER_HALF_MIN` 26 / 6.5 fail the water load (27 and 7 min);
- `RATE_BASE` 2.5 / 0.625 fail Hunt's rate (3.58 and 1.83);
- `RATE_PER_KCAL` 0.005 / 0.00125 fail Hunt's rate and its slope;
- `DEFICIT_FLOOR` 0 fails the pin and 0.3 fails the CALERIE bound (0.1146);
- the routing swap fails the soup (equal arms).

A survivor is a FAIL of the task, sent to a fix round. The fix adds a test resting on a study (never a looser band), and the controller rules on it. The review reports the full printout, the unpatched run and the model id.

---

### Task 5: The 42.21 reads — vanilla's overeating, DISCOMFORT, a removed sandbox key — Opus implementer, Opus reviewer

The lane is D, beside Tasks 2–4, after Task 0 Step 3. It edits no `mod/` file and runs no kernel suite. This task answers on the 42.21 jar and the 42.21 vanilla Lua the questions the soft cap (Task 7), the switch (Task 6) and the retirement (Task 9) rest on. It records each answer as a register row with its page sentence, through a delta. Read `C:\Users\Angus\pz-b42\WORKSPACE.md` and `docs/platform/jar-research.md` first, and cite each reading as `Class.method @off L<n>` (`docs/reference/jar-method-notes.md`). Vanilla Lua is read under `D:\SteamLibrary\steamapps\common\ProjectZomboid\media\lua`, which is read-only.

**Files:**
- Create (workspace): `.superpowers/sdd/2026-10-08-plan-11c-satiety/task-5-jar-memo.md` and `task-5-claims-delta.tsv`.
- Modify (tagged sentences, provisional `T11705.n`): `docs/facts/eating-pipeline.md` (J1, J4), `docs/facts/character-stats.md` (J2) and `docs/platform/sandbox-options.md` (J3). These are CRLF files: edit them with `newline=''`.

**Interfaces:**
- Produces, for Task 7, the J1 and J2 answers in the memo: what vanilla does when a full character eats; the DISCOMFORT stat's range, its update and relaxation, and whether the client receives the server's value. The controller rules on Task 7 from them.
- Produces, for Task 9, the J3 answer: what the 42.21 loader does with a sandbox key no option declares.
- Produces, for Task 6, the J4 answer: an eat another mod makes through a direct `Eat` reaches the stomach through the reconcile path.

- [ ] **Step 1: J1, what vanilla does when a full character eats.**
  - Read `ISEatFoodAction:isValidStart` in `media/lua/shared/TimedActions/ISEatFoodAction.lua`. It was spot-read while writing this plan, at line 14: `return self.character:getMoodles():getMoodleLevel(MoodleType.FOOD_EATEN) < 3`, so vanilla refuses to *start* an eat at the FOOD_EATEN moodle's level 3.
  - Read what raises that moodle:
    - `./pz.sh methods zombie/characters/BodyDamage/BodyDamage | grep -i "food"` (the `JustAteFood` overloads, `getHealthFromFoodTimer`, `getHealthFromFoodTimeByHunger`);
    - `./pz.sh dump zombie/characters/BodyDamage/BodyDamage JustAteFood --desc "(Lzombie/inventory/types/Food;FZ)"`;
    - the FOOD_EATEN level thresholds in `zombie/characters/Moodles/Moodles` (`./pz.sh grep FoodEaten`, then `dump` its update).
  - Read whether `IsoGameCharacter.Eat` does anything else when HUNGER is already 0 (`./pz.sh dump zombie/characters/IsoGameCharacter Eat --desc "(Lzombie/inventory/InventoryItem;FZ)"`): a sickness, a stat or a refusal.
  - Write each fact with its cite. Under the hybrid writer (Mode 1), state also when an eat leaves HUNGER at 0, which is what fills the timer (#0054, #0503).
- [ ] **Step 2: J2, DISCOMFORT.**
  - The range: `./pz.sh dump zombie/characters/CharacterStat '<clinit>'`, the `'Discomfort'` registration with its min and max. It was spot-read at `L14`: `fconst_0`, `ldc 100.0`, `fconst_0`.
  - The update: `./pz.sh dump zombie/characters/BodyDamage/BodyDamage UpdateDiscomfort`. It was spot-read at `L3275`–`L3323`: a target is summed from the corpse drag, clothing, the bed asleep, the three moodles and vehicles, times the intoxication factor, clamped and ×100; the current value then relaxes toward it at `0.005 × GameTime.getMultiplier()`. Confirm the relaxation's form and both directions from the dump past L3323.
  - Who calls `UpdateDiscomfort`, and is it server-side for a dedicated server's players? Use `./pz.sh refs` and `grep`.
  - Does the player-stats packet carry DISCOMFORT to the client? Read `docs/facts/wire-packets.md` first, then the packet's field list on the jar.
  - The answer the controller needs is one line: **can a server-side floor written once a minute hold DISCOMFORT high enough for the client's moodle to show?**
- [ ] **Step 3: J3, a removed sandbox key.** Read what the 42.21 loader does with a key under `SandboxVars.NR` that no option declares, for each place a server keeps sandbox values:
  - the server's `<server>_SandboxVars.lua`: `SandboxOptions.loadServerLuaFile` → `readLuaFile` → the table walk, and `getOptionByName` returning null;
  - the world's `map_sand.bin`: `SandboxOptions.load(ByteBuffer)`;
  - the server `.ini`, which holds no sandbox option; say so with the reading.

  The answer is whether the key is skipped silently, logged, or an error, with the cite for each path. If it is not ignored, the memo says what Task 9 must do (for example, keep a hidden declared option) and the controller rules before Task 9.
- [ ] **Step 4: J4, a direct `Eat` reaches the stomach.** This is a read of the mod's own code, not the jar. `NR_Server_Reconcile.lua`'s step lands a missed rise of the vanilla macro stores through `IN.land` (lines 91–96 at the plan's writing), so it reaches the stomach's solid buffer as macros only (no water or fibre mass).
  - Cite the lines with a `repo:` pointer, and name the limit: a direct `DrinkFluid` adds no macro store when the fluid carries none, so the reconcile path does not see a water-only drink.
  - Task 6 pins this with a test.
- [ ] **Step 5: The memo and the delta.**
  - Write `task-5-jar-memo.md`: one section per question (J1–J4), each with its cites and a one-line answer, and at its end **"For Task 7"** and **"For Task 9"**: what the answers mean for ruling 11c-13 and for the option's removal.
  - Write `task-5-claims-delta.tsv`: one `add` per fact, ids `T11705.1` onward, grade `C` for a jar or Lua reading, kind `mechanism`, source `Plan 11c Task 5 (desk), the 42.21 reads` and owner the page anchor. The bound says `re-read on 42.21 (buildid 25485521)`.
  - Add each fact's sentence on its owner page with its provisional tag, in the page's own voice (`docs/platform/page-standard.md` if present, else the neighbouring sentences).
  - Dry-run: `python tools/claims_delta.py apply .superpowers/sdd/2026-10-08-plan-11c-satiety/task-5-claims-delta.tsv --pages docs/facts/eating-pipeline.md docs/facts/character-stats.md docs/platform/sandbox-options.md --dry-run`.
  - Run `python tools/page_lint.py docs/facts/eating-pipeline.md docs/facts/character-stats.md docs/platform/sandbox-options.md` (0).
- [ ] **Step 6: Commit the pages.** The memo and delta stay in the workspace.

```bash
PYTHONIOENCODING=utf-8 python tools/claims_check.py --staged --allow-provisional
git commit -m "Facts: vanilla's overeating, DISCOMFORT and a removed sandbox key on 42.21 (Plan 11c Task 5)" -- docs/facts/eating-pipeline.md docs/facts/character-stats.md docs/platform/sandbox-options.md
```

The checker must read 0 findings before the commit.

The controller applies the delta at Task 5's close, runs the full checker without the allowance, and ledgers the ruling on Task 7: ruling 11c-13 stands, or the controller writes `task-7-amendments.md` with the changed effect.

---

## Phase C — Wiring

### Task 6: The switch — satiety from physiology — Opus implementer, Opus reviewer

The lane is M, after Task 4 (and Task 5's J4). This task is the plan's one behaviour change and its one golden re-record, named **"satiety from physiology"**:
- kinetics drains both lanes and hands the emptied vector on `ctx.emptied`;
- the intake lands a drink's water in the liquid lane and stops reading `getHungerChange` (`IN.sate` goes);
- the auto-drink sip lands in the liquid lane, and the thirst view reads both lanes' water;
- every new stomach starts empty (`seedFull` retires);
- the writer seeds, feeds, decays and reads P, and writes `hungerTarget(sated(F, post(P)), energyState)`;
- the store moves to version 4;
- the first-order stomach (`HALF_TIME_H`, `FULL_BULK`, `bulkOf`, `seedFull`, `compositionScale`, `emptyFraction`, `empty`) retires with its tests.

`<ws>` is `.superpowers/sdd/2026-10-08-plan-11c-satiety`. Work through the steps in order. Commit once, at Step 9, so that no commit has a red golden test.

**Files:**
- Modify (mod): `mod/.../shared/NR_Kernel_Stomach.lua` (the header, `new`, `ingest`, `fill`, and deleting the first-order pieces), `mod/.../shared/NR_Kernel_Store.lua` (VERSION, INPUTS, `new`, `defaults`, `load` and comments), `mod/.../shared/NR_Kernel_Nutrients.lua` (the `ACUTE_EMPTY_FILL` comment, in place), `mod/.../server/NR_Server_Kinetics.lua`, `NR_Server_Intake.lua`, `NR_Server_Writer.lua`, `NR_Server_Nutrients.lua` and `NR_Server_Reconcile.lua`.
- Modify (tests): `testing/tests/kernel/test_kernel_stomach.py` (CRLF), `test_kinetics.py` (CRLF), `test_intake_shape.py` (CRLF), `test_writer_shape.py`, `test_kernel_store.py`, `test_store_file_shape.py`, `test_server_reconcile_shape.py` (CRLF), `test_nutrients_shape.py` (CRLF), `test_metabolism_shape.py` (CRLF) and `test_plan4_steady_state.py` (CRLF).
- Re-record: `testing/tests/kernel/golden/trace-1.0.0.json`.
- Create (workspace): `<ws>/task-6-golden-walk.py`; extend `<ws>/bench_11c.py`.

**Interfaces:**
- Consumes everything Tasks 2 and 3 produce.
- Produces:
  - `K.stomach.new() -> { buffer = <vector>, liquid = 0 }`, with no `bulk`.
  - `K.stomach.ingest(stomach, vector)`, which adds to the buffer only.
  - `K.stomach.fill(stomach) -> K.satiety.fill(K.stomach.mass(stomach), K.stomach.CAPACITY_G)`.
  - `ctx.emptied` (kinetics → writer, transient).
  - `IN.land(record, username, vec, lane)`, where `lane == "liquid"` routes by `K.stomach.ingestLiquid`.
  - `record.satiety = { P = <number>, v = 4 }` and `W.stats.guarded`.
  - `K.store.VERSION = 4`; INPUTS gain `satiety.P`, `satiety.v` and `stomach.liquid`, and lose `satiety`, `satietyStepped` and `stomach.bulk`.
  - `W.satiety(h, player, record, eng, inp, es, ctx)`.

- [ ] **Step 1: Write the failing tests: the stomach, kinetics and the plan-4 replay.**

  **`test_kernel_stomach.py`** (CRLF; keep the endings):
  - In `test_constants`, delete the two lines `assert s.HALF_TIME_H == 2.0` and `assert s.FULL_BULK == 8.0`.
  - Replace `test_new_is_an_empty_buffer` with:

```python
def test_new_is_an_empty_buffer_and_an_empty_liquid_lane(host):
    st = host.py(host.K.stomach["new"]())
    assert st["liquid"] == 0 and "bulk" not in st
    assert set(st["buffer"].keys()) == set(host.K.vector.KEYS.values())
    assert all(v == 0 for v in st["buffer"].values())
```

  - Replace `test_ingest_raises_bulk_and_fills_the_buffer` with:

```python
def test_ingest_fills_the_buffer_and_keeps_a_foods_water_with_it(host):
    st = host.K.stomach["new"]()
    out = host.K.stomach.ingest(st, _apple(host))
    assert _same(host, out, st)
    assert abs(st.buffer.calories - 95) < TOL
    assert abs(st.buffer.fibre - 4.4) < TOL
    assert abs(st.buffer.water - 155.8) < TOL and st.liquid == 0
    host.K.stomach.ingest(st, _apple(host))
    assert abs(st.buffer.calories - 190) < TOL
```

  - Delete these tests outright, since the functions they test retire: `test_bulk_of_an_apple`, the five `test_composition_scale_*`, the four `test_empty_fraction_*`, `test_empty_one_half_time_moves_half_of_every_key`, `test_a_fattier_buffer_empties_slower`, `test_empty_zero_dt_moves_nothing` and `test_seed_full_sets_the_bulk_to_full_and_leaves_the_buffer`.
  - In `test_absorb_with_the_meal_context_reads_the_whole_meal`, replace `emptied = host.K.stomach.empty(st, 1 / 60)` with `emptied = host.K.stomach.drain(st, 1 / 60)`. Also replace the last line, `assert share["iron"] / emptied.iron > 0.179`, with `assert share["iron"] / emptied.iron > 0.178   # the zero-order first minute moves ~1.9 mg of phytate`.
  - Replace `test_absorb_with_a_context_reads_the_meals_lipids` with:

```python
def test_absorb_with_a_context_reads_the_meals_lipids(host):
    # the first minute of a 30 g-fat meal: the factor reads the buffer's 30 g (0.99995), not the minute's share
    st = host.K.stomach.new()
    host.K.stomach.ingest(st, _vec(host, calories=270.0, lipids=30.0, retinol=900.0, vitK=120.0, vitD=15.0))
    ctx = host.K.stomach.context(st, host.rt.table())
    emptied = host.K.stomach.drain(st, 1 / 60)
    out = host.py(host.K.stomach.absorb(emptied, ctx))
    f = 1 - math.exp(-10.0)
    assert abs(f - 0.9999546000702375) < 1e-12
    assert abs(out["retinol"] / emptied.retinol - f) < 1e-12
    assert abs(out["vitK"] / emptied.vitK - f) < 1e-12
    assert abs(out["vitD"] / emptied.vitD - (0.76 + (1 - 0.76) * f)) < 1e-12
    share = host.py(host.K.stomach.absorb(emptied))  # no ctx: the per-share reading, unchanged
    assert abs(share["retinol"] / emptied.retinol - max(0.05, 1 - math.exp(-emptied.lipids / 3))) < 1e-12
```

  - Replace `test_fill_after_an_apple_and_it_falls_on_empty` and `test_fill_clamps_at_one` with:

```python
def test_fill_after_an_apple_is_its_mass_over_the_comfortable_capacity_and_it_falls(host):
    st = host.K.stomach["new"]()
    host.K.stomach.ingest(st, _apple(host))
    f0 = host.K.stomach.fill(st)
    assert abs(f0 - (155.8 + 4.4) / 430) < TOL                       # water and fibre; the apple stub has no macros
    host.K.stomach.drain(st, 1.0)
    assert host.K.stomach.fill(st) < f0


def test_fill_clamps_at_one_and_counts_the_liquid_lane(host):
    st = host.K.stomach["new"]()
    host.K.stomach.ingestLiquid(st, _vec(host, water=5000))
    assert host.K.stomach.fill(st) == 1
    st2 = host.K.stomach["new"]()
    host.K.stomach.ingestLiquid(st2, _vec(host, water=215))
    assert abs(host.K.stomach.fill(st2) - 0.5) < TOL
```

  - Replace `_meal_replay_py`, `MEAL_REPLAY` and `test_a_30g_fat_meal_over_a_day_absorbs_the_replayed_fraction` with:

```python
def _frac(E, dtM):
    fw = 1 - math.exp(-LN2 * dtM / 13)
    if E <= 0:
        return fw
    left = (E + 1.25 / 0.0025) * math.exp(-0.0025 * dtM) - 1.25 / 0.0025
    fe = 1.0 if left <= 0 else max(0.0, 1 - left / E)
    return min(fe, fw)


def _meal_replay_py(n=1440):
    """K.stomach.ingest/context/drain/absorb recomputed in doubles over n one-minute steps of one meal."""
    b = dict(calories=270.0, lipids=30.0, retinol=900.0, vitK=120.0, vitD=15.0)
    tot = dict(retinol=0.0, vitK=0.0, vitD=0.0)
    for _ in range(n):
        lip = b["lipids"]                                            # the context, before the emptying
        f = _frac(b["calories"], 1.0)
        em = {k: 0 + v * f for k, v in b.items()}
        for k in b:
            b[k] = b[k] * (1 - f)
        fat = min(max(1 - math.exp(-lip / 3), 0.05), 1.0)
        tot["retinol"] += em["retinol"] * 1.0 * fat
        tot["vitK"] += em["vitK"] * 1.0 * fat
        tot["vitD"] += em["vitD"] * 1.0 * (0.76 + (1 - 0.76) * fat)
    return tot, b


MEAL_REPLAY = r"""
function(n)
    local K = NutritionRevamp.kernel
    local st = K.stomach.new()
    local meal = K.vector.new()
    meal.calories = 270
    meal.lipids = 30
    meal.retinol = 900
    meal.vitK = 120
    meal.vitD = 15
    K.stomach.ingest(st, meal)
    local ctx = {}
    local tot = { retinol = 0, vitK = 0, vitD = 0 }
    for i = 1, n do
        K.stomach.context(st, ctx)
        local out = K.stomach.absorb(K.stomach.drain(st, 1 / 60), ctx)
        tot.retinol = tot.retinol + out.retinol
        tot.vitK = tot.vitK + out.vitK
        tot.vitD = tot.vitD + out.vitD
    end
    return tot, st.buffer.lipids
end
"""


def test_a_30g_fat_meal_over_a_day_absorbs_the_replayed_fraction(host):
    # Rulings T19-1 and T19-6 on Plan 11c's zero-order lane: the buffer's lipids empty with the vitamins, so the
    # factor 1 - exp(-L/3) eases over the meal; the replay in doubles gives 0.901761 of the retinol and vitK
    exp_tot, exp_buf = _meal_replay_py()
    tot, lip = host.rt.eval(MEAL_REPLAY)(1440)
    assert abs(exp_tot["retinol"] / 900 - 0.9017608084148669) < 1e-12
    assert abs(tot.retinol / 900 - exp_tot["retinol"] / 900) < 1e-6
    assert abs(tot.vitK / 120 - exp_tot["vitK"] / 120) < 1e-6
    assert abs(tot.vitK / 120 - 0.9017608084148657) < 1e-6
    # vitamin D at 0.76 + 0.24 x the factor per minute
    assert abs(tot.vitD / 15 - exp_tot["vitD"] / 15) < 1e-6
    assert abs(tot.vitD / 15 - 0.9764225940195675) < 1e-6
    assert abs(lip - exp_buf["lipids"]) < 1e-9                       # under 1e-20 g left after the day
    assert tot.retinol / 900 > 18 * 0.05
```

  **`test_plan4_steady_state.py`** (CRLF):
  - In `REPLAY`, replace `K.stomach.empty(st, 1 / 60)` with `K.stomach.drain(st, 1 / 60)`.
  - Under `MEAL = dict(...)`, add `MEAL_KCAL = 490.0                  # the Lua meal's calories (REPLAY), which set the zero-order lane`.
  - In `_replay_py`:
    - start `b` as `dict(lipids=0.0, retinol=0.0, vitK=0.0, calories=0.0)`;
    - in the meal branch, after the `for k, v in MEAL.items()` loop, add `b["calories"] = b["calories"] + MEAL_KCAL`;
    - replace the two lines computing `cs` and `f` with `f = _frac(b["calories"], 1.0)`, with `_frac` copied from `test_kernel_stomach.py` above, verbatim, as a module function, beside `LN2 = 0.6931471805599453` (the file has no `LN2`).
  - Replace the four literals with the Python mirror's values (2026-10-08): `efrac` `0.7138916612921502`, `epA` `0.8834645470568487`, `epK` `0.9894153856691867` and `eminK` `0.9074649197628905`. Keep every agreement assertion.
  - Rewrite the docstring's numbers: "three 10 g-fat meals a day absorb 71 % of their fat-soluble load (0.7139 of the 60-day retinol); vitA's liver p is 0.883 at day 60 (lowest 0.882 over days 30-60) and vitK's 0.989 (lowest 0.907 over days 30-60, grade 1)".
  - Keep the comment's line about the brief's expectations, since vitA p ≥ 0.85 and vitK grade 1 are still met.
  - If `gA == 1 and p2A == 1` no longer holds on the lupa run, STOP and report the reading. That is a nutrition behaviour change this plan does not name.

  **`test_kinetics.py`** (CRLF):
  - In `NEWREC`, delete the line `NutritionRevamp.kernel.stomach.seedFull(r.stomach)`.
  - In `RAISING`, wrap `K.stomach.drain` in place of `K.stomach.empty` (all three lines).
  - Replace the tests from `test_first_call_seeds_and_stamps` through `test_nan_bulk_and_a_nan_pool_key_resets_the_pool` (with `POISON` and `FINITE_POOL`) with:

```python
LN2 = 0.6931471805599453


def _frac(E, dtM):
    fw = 1 - math.exp(-LN2 * dtM / 13)
    if E <= 0:
        return fw
    left = (E + 1.25 / 0.0025) * math.exp(-0.0025 * dtM) - 1.25 / 0.0025
    fe = 1.0 if left <= 0 else max(0.0, 1 - left / E)
    return min(fe, fw)


def test_first_call_lays_an_empty_stomach_and_stamps(kin_host):
    h = kin_host
    K = h.G.NutritionRevamp.kernel
    record = h.rt.table()
    run(h, record, 100.0)
    assert record["stomach"]["liquid"] == 0 and record["stomach"]["bulk"] is None
    for k in K.vector.KEYS.values():
        assert record["pool"][k] == 0
        assert record["stomach"]["buffer"][k] == 0
    assert record["stomachFill"] == 0                    # spec § 4: a record with no stomach starts empty
    assert abs(record["kineticsAge"] - 100.0) < TOL


def test_first_call_leaves_a_buffer_untouched(kin_host):
    h = kin_host
    record = h.rt.table()
    stomach = h.rt.eval(NEWREC)(100, True)
    record["stomach"] = stomach["stomach"]
    record["pool"] = stomach["pool"]
    run(h, record, 100.0)  # no kineticsAge yet: dtH is 0
    assert abs(record["stomach"]["buffer"]["calories"] - 100) < TOL
    assert abs(record["pool"]["calories"]) < TOL


def test_the_liquid_lane_half_empties_on_waters_half_time_with_no_energy(kin_host):
    h = kin_host
    record = rec(h, 0)
    record["stomach"]["liquid"] = 215.0
    run(h, record, 100.0)
    run(h, record, 100.0 + 13 / 60)
    assert abs(record["stomach"]["liquid"] - 107.5) < 1e-9
    assert abs(record["stomachFill"] - 107.5 / 430) < 1e-9


def test_second_call_moves_the_zero_order_share_into_the_pool(kin_host):
    h = kin_host
    record = rec(h, 100)
    run(h, record, 100.0)
    run(h, record, 101.0)
    f = _frac(100, 60)
    assert abs(record["pool"]["calories"] - 100 * f) < 1e-9
    assert abs(record["stomach"]["buffer"]["calories"] - 100 * (1 - f)) < 1e-9


def test_the_emptied_vector_rides_the_context(kin_host):
    h = kin_host
    record = rec(h, 100)
    run(h, record, 100.0)
    run(h, record, 101.0)
    assert abs(h.G.NR_TEST_PIPE.emptied.calories - 100 * _frac(100, 60)) < 1e-9
    run(h, record, 101.0)                                 # no elapsed time: the handoff is cleared
    assert h.G.NR_TEST_PIPE.emptied is None


@pytest.mark.parametrize("age", [100.0, 99.0])
def test_zero_or_backwards_delta_empties_nothing(kin_host, age):
    h = kin_host
    record = rec(h, 100)
    run(h, record, 100.0)
    run(h, record, age)
    assert abs(record["stomach"]["buffer"]["calories"] - 100) < TOL
    assert abs(record["pool"]["calories"]) < TOL
    assert record["stomachFill"] == 0                    # energy with no mass reads empty
    assert abs(record["kineticsAge"] - age) < TOL


def test_pcall_keeps_the_walk_alive(kin_host):
    h = kin_host
    record = rec(h, 100)
    run(h, record, 100.0)
    before = KIN(h).stats.minutes
    ok, err = h.rt.eval(RAISING)(record, 102.0)
    assert ok is True  # minute itself did not raise
    assert isinstance(KIN(h).lastError, str) and "boom" in KIN(h).lastError
    assert KIN(h).stats.minutes == before + 1
    assert abs(record["stomach"]["buffer"]["calories"] - 100) < TOL


def test_stats_count_minutes_and_players(kin_host):
    h = kin_host
    record = rec(h, 0)
    m0, p0 = KIN(h).stats.minutes, KIN(h).stats.players
    run(h, record, 100.0)
    run(h, record, 101.0)
    assert KIN(h).stats.minutes == m0 + 2
    assert KIN(h).stats.players == p0 + 2


POISON = r"""
function(age, field)
    local K = NutritionRevamp.kernel
    local r = { stomach = K.stomach.new(), pool = K.vector.new() }
    if field == "liquid" then
        r.stomach.liquid = 0 / 0
    else
        r.stomach.buffer.calories = 0 / 0
    end
    r.pool.calories = 0 / 0
    r.kineticsAge = age
    return r
end
"""


@pytest.mark.parametrize("field", ["liquid", "calories"])
@pytest.mark.parametrize("age", [None, 99.0])  # the first sight (dt 0) and a later minute (dt 1 h)
def test_a_nan_stomach_self_heals_empty(kin_host, age, field):
    h = kin_host
    K = h.G.NutritionRevamp.kernel
    record = h.rt.eval(POISON)(age, field)
    f0 = KIN(h).stats.failures
    KIN(h).lastError = None
    run(h, record, 100.0)
    assert record["stomachFill"] == 0 and record["stomach"]["liquid"] == 0
    for k in K.vector.KEYS.values():
        assert record["stomach"]["buffer"][k] == 0
        assert record["pool"][k] == 0
    assert isinstance(KIN(h).lastError, str) and "non-finite stomach fill" in KIN(h).lastError
    assert KIN(h).stats.failures == f0 + 1


FINITE_POOL = r"""
function(age, nanPool)
    local K = NutritionRevamp.kernel
    local r = { stomach = K.stomach.new(), pool = K.vector.new() }
    r.stomach.liquid = 0 / 0
    r.pool.calories = 40
    if nanPool then r.pool.iron = 0 / 0 end
    r.kineticsAge = age
    return r
end
"""


def test_a_nan_stomach_keeps_a_finite_pool(kin_host):
    # at first sight (dt 0): nothing drains, so the NaN never reaches the pool and a finite pool is kept; on a later
    # minute the drain carries the NaN into the pool first, and the pool's own check resets it (the test above)
    h = kin_host
    record = h.rt.eval(FINITE_POOL)(None, False)
    f0 = KIN(h).stats.failures
    run(h, record, 100.0)
    assert record["stomachFill"] == 0 and record["stomach"]["liquid"] == 0
    assert abs(record["pool"]["calories"] - 40) < TOL
    assert KIN(h).stats.failures == f0 + 1


def test_a_nan_stomach_and_a_nan_pool_key_resets_the_pool(kin_host):
    h = kin_host
    K = h.G.NutritionRevamp.kernel
    record = h.rt.eval(FINITE_POOL)(None, True)
    run(h, record, 100.0)
    assert record["stomachFill"] == 0
    for k in K.vector.KEYS.values():
        assert record["pool"][k] == 0
```

  Add `import math` to the file's imports. `test_the_meal_context_is_passed_from_the_buffer` and the clock tests stay as they are; they read ratios, and `stomachFill > fill0 - 0.01` holds on an empty stomach.

- [ ] **Step 2: Write the failing tests: the intake, the nutrients, the reconcile and the store.**

  **`test_intake_shape.py`** (CRLF):
  - In `test_server_path_eat_lands_in_the_stomach`, replace `assert rec["stomach"]["bulk"] > 0` with `assert h.K.stomach.mass(rec["stomach"]) > 0 and rec["stomach"]["liquid"] == 0`.
  - In `DRINK_STUBS`, replace the returned `NutritionRevamp.kernel.stomach.bulkOf(expected)` with `expected`.
  - In `test_server_path_drink_lands_the_cola`, rename the fifth unpacked name to `expected`, and replace the lines from `assert expected_bulk > 0` through the `full_bulk` assertion with:

```python
    assert expected.water > 0 and expected.calories > 0
    st = rec["stomach"]
    assert abs(st["liquid"] - expected.water) < TOL                       # the drink's water: the liquid lane (11c-12)
    assert st["buffer"]["water"] == 0                                     # a fresh stomach starts empty (11c-15)
    assert abs(st["buffer"]["calories"] - expected.calories) < TOL        # its energy: the solid lane's budget (11c-5)
```

  - In the share-0.25 eat test, delete the two lines `full = h.K.stomach.FULL_BULK` and the `bulk` assertion after it, and add `assert rec["stomach"]["liquid"] == 0`.
  - In `test_world_water_step_lands_its_litres`, replace the buffer-water assertion with `assert abs(rec["stomach"]["liquid"] - 250.0) < TOL and rec["stomach"]["buffer"]["water"] == 0`.
  - In `test_world_water_uses_the_water_seed_when_the_data_has_it`, replace the buffer-water assertion with `assert abs(rec["stomach"]["liquid"] - 500.0) < TOL`; the sodium assertion stays.
  - Delete everything from the line `# --- Plan 11 Task 15: an eat raises the satiety scalar by its laddered relief times the bulk factor -----------` to the end of the file (Task 15's `IN.sate` tests). Append:

```python
# --- Plan 11c: a drink's water lands in the liquid lane; the intake reads no hunger change -----------------------

def test_a_liquid_landing_puts_the_water_in_the_liquid_lane(rec_host):
    h = rec_host
    record = _record(h)
    record["stomach"] = h.K.stomach.new()
    I(h).lastIngested["u"] = None
    I(h).land(record, "u", _vec(h, water=300.0, calories=42.0, carbs=10.5, sodium=4.0), "liquid")
    st = record["stomach"]
    assert st["liquid"] == 300.0 and st["buffer"]["water"] == 0
    assert st["buffer"]["calories"] == 42.0 and st["buffer"]["sodium"] == 4.0
    assert I(h).lastIngested["u"]["water"] == 300.0                      # ingested as drunk
    I(h).lastError = None


def test_a_food_landing_keeps_its_water_in_the_buffer(rec_host):
    h = rec_host
    record = _record(h)
    record["stomach"] = h.K.stomach.new()
    I(h).land(record, "u", _vec(h, water=120.0, calories=200.0))
    assert record["stomach"]["buffer"]["water"] == 120.0 and record["stomach"]["liquid"] == 0
    I(h).lastError = None


def test_the_intake_no_longer_reads_a_hunger_change():
    with open(INTAKE_LUA, encoding="utf-8") as fh:
        src = fh.read()
    assert 'read(item, "getHungerChange")' not in src                     # the eat's laddered relief (Task 15)
    assert '"getProperties"), "getHungerChange")' not in src              # the drink's fluid hunger (Task 15 fix 1)
    assert "IN.sate" not in src
```

  - Define `INTAKE_LUA` beside the file's other path constants if it has none: `INTAKE_LUA = os.path.join(REPO, "mod", "NutritionRevamp", "common", "media", "lua", "server", "NR_Server_Intake.lua")`, using the file's existing `REPO` or `os` import (read the file's head first).

  **`test_nutrients_shape.py`** (CRLF):
  - Replace `test_an_auto_drink_drop_lands_in_the_stomach` with:

```python
def test_an_auto_drink_drop_lands_in_the_liquid_lane(nut_host):
    h = nut_host
    p = player(h)
    record = fresh(h, p)
    liquid0 = record["stomach"]["liquid"] or 0
    water0 = record["stomach"]["buffer"]["water"]
    record["fluids"]["autoDrop"] = 0.2
    alone(h, p, record, 100.0 + 1 / 60)
    assert abs(record["stomach"]["liquid"] - liquid0 - 400.0) < 1e-9   # 2 L per THIRST x 0.2
    assert record["stomach"]["buffer"]["water"] == water0
    assert record["fluids"]["autoDrop"] == 0
    # a record with no stomach yet gets an empty one (ruling 11c-15)
    record["stomach"] = None
    record["fluids"]["autoDrop"] = 0.1
    alone(h, p, record, 100.0 + 2 / 60)
    assert abs(record["stomach"]["liquid"] - 200.0) < 1e-9
    assert record["stomach"]["buffer"]["water"] == 0
```

  - Append, after `test_the_thirst_view_reads_the_stomach_pending_water`:

```python
def test_the_thirst_view_reads_the_liquid_lanes_water_too(nut_host):
    h = nut_host
    p = player(h)
    record = fresh(h, p)
    for i in range(1, 11):
        chain(h, p, record, 100.0 + i)
    before = record["fluids"]["thirstTarget"]
    record["stomach"]["liquid"] = 1000.0
    alone(h, p, record, 110.0 + 1 / 60)
    f = record["fluids"]
    assert abs(f["dehydPct"] - f["viewPct"] - 100 * 1.0 / 80.0) < 1e-6   # ruling T1-1, both lanes' water
    assert f["thirstTarget"] < before
```

  **`test_metabolism_shape.py`** (CRLF): in `test_kinetics_hands_off_the_absorbed_vector`, delete the line `K.stomach.seedFull(record.stomach)`.

  **`test_writer_shape.py`**: in `test_the_intake_marks_a_landing`, replace `rec.stomach = h.K.stomach.seedFull(h.K.stomach.new())` with `rec.stomach = h.K.stomach.new()`.

  **`test_server_reconcile_shape.py`** (CRLF):
  - In `test_a_rise_with_no_wrapped_eat_lands_the_macros_only`, append `assert rec["stomach"]["liquid"] == 0                                 # J4: a reconciled intake reaches the solid buffer, macros only`. It is red on the pre-change tree, where the seeded stomach has no `liquid`.
  - In `test_a_v1_record_migrates_at_first_sight_in_place_with_one_log_line`, change `== 3` to `== 4` and `"v1 -> v3"` to `"v1 -> v4"`.
  - In `test_a_new_record_is_made_by_the_kernel_at_the_current_version`, change `rec["v"] == 3` to `rec["v"] == 4`.

  **`test_store_file_shape.py`**: change `r.v == 3 and r.satiety is None` to `r.v == 4 and r.satiety is None`.

  **`test_kernel_store.py`**:
  - `test_version_is_three_and_inputs_are_dotted_strings` becomes `test_version_is_four_and_inputs_are_dotted_strings`, with `assert S(host).VERSION == 4`.
  - Replace `test_new_is_the_identity_record_at_version_three` with:

```python
def test_new_is_the_identity_record_at_version_four(host):
    assert host.py(S(host).new("bob", 12.5)) == {"v": 4, "username": "bob", "firstSeen": 12.5, "lastSeen": 12.5,
                                               "resets": 0, "dead": False}
```

  - In `test_load_of_a_v1_record_keeps_the_inputs_and_drops_the_derived`, change `r["v"] == 3` to `r["v"] == 4`. Replace the two stomach lines with:

```python
    assert r["stomach"]["buffer"]["calories"] == 300 and "bulk" not in r["stomach"] and r["stomach"]["liquid"] == 0
    assert r["stomachFill"] == 0                                             # recomputed: energy alone has no mass
```

  - In `test_load_of_a_record_with_no_version_and_with_v1_is_the_same`, change `a["v"] == 3` to `a["v"] == 4`.
  - In `test_a_missing_input_keeps_the_constructor_default`, change the stomach line to `assert r["stomach"]["buffer"]["calories"] == 0 and r["stomachFill"] == 0 and r["stomach"]["liquid"] == 0`.
  - Replace `test_a_stored_stomach_with_no_bulk_loads_full` with:

```python
def test_a_stored_stomach_loads_its_buffer_and_liquid_and_its_fill_from_mass(host):
    r = host.py(S(host).load(host.table({"stomach": {"buffer": {"water": 215}}}), order(host), recs(host)))
    assert r["stomach"]["liquid"] == 0 and r["stomachFill"] == 0.5
    r = host.py(S(host).load(host.table({"stomach": {"liquid": 430}}), order(host), recs(host)))
    assert r["stomachFill"] == 1
    r = host.py(S(host).load(host.table({"stomach": {"bulk": 8}}), order(host), recs(host)))     # a v3 stomach
    assert "bulk" not in r["stomach"] and r["stomachFill"] == 0
```

  - In both `fillInPlace` tests, change `== 3` to `== 4` (`rec["v"]` and `target["v"]`).
  - Replace the five Task 11/15 satiety tests (`test_a_new_record_seeds_satiety_full` through `test_a_loaded_record_keeps_its_satiety`) with:

```python
def test_a_new_record_has_no_satiety_for_the_writer_to_seed(host):
    assert S(host).new("a", 1.0).satiety is None


def test_the_pool_and_its_mark_are_inputs_and_the_v3_fields_are_not(host):
    assert S(host).isInput("satiety.P") and S(host).isInput("satiety.v") and S(host).isInput("stomach.liquid")
    assert not S(host).isInput("satiety") and not S(host).isInput("satietyStepped")
    assert not S(host).isInput("stomach.bulk")


def test_a_v3_scalar_and_its_mark_are_dropped_on_load(host):
    raw = host.rt.eval("{ v = 3, username = 'a', firstSeen = 1.0, lastSeen = 2.0, resets = 0, dead = false, satiety = 0.4, satietyStepped = true }")
    rec = S(host).load(raw, None, None)
    assert rec.v == 4 and rec.satiety is None and rec.satietyStepped is None


def test_a_loaded_record_without_satiety_keeps_it_unset(host):
    raw = host.rt.eval("{ v = 2, username = 'a', firstSeen = 1.0, lastSeen = 2.0, resets = 0, dead = false }")
    rec = S(host).load(raw, None, None)
    assert rec.v == 4 and rec.satiety is None


def test_a_loaded_v4_record_keeps_its_pool(host):
    raw = host.rt.eval("{ v = 4, username = 'a', firstSeen = 1.0, lastSeen = 2.0, resets = 0, dead = false, satiety = { P = 88, v = 4, junk = 1 } }")
    rec = S(host).load(raw, None, None)
    assert rec.satiety.P == 88 and rec.satiety.v == 4 and rec.satiety.junk is None
```

- [ ] **Step 3: Write the failing tests: the writer.** In `test_writer_shape.py`:
  - Make `record()`'s literal start `{ stomachFill = 0.6, satiety = { P = 112.5, v = 4 }, body = …`, replacing `satietyStepped = true`. With F 0.6, the default P gives HUNGER `(1 - 0.5 × 0.6) × (1 - 112.5 / 262.5) = 0.4`, which is the 0.4 the existing tests read.
  - Remove the keyword argument from every remaining `record(h, satiety=0.6)` call, making it `record(h)`.
  - Replace `test_the_stomach_fill_no_longer_drives_hunger` with:

```python
def test_the_stomach_fill_drives_hunger_through_its_weight():
    h = boot()
    p = player(h)
    rec = record(h)
    rec.stomachFill = 0.0
    step(h, p, rec, 1)
    assert p.st.sets.HUNGER == pytest.approx(1 - 112.5 / 262.5)            # (1 - 0.5 x 0) x (1 - post(P))
    p2 = player(h, "b")
    rec2 = record(h)
    rec2.stomachFill = float("nan")                                        # a non-finite fill reads empty
    step(h, p2, rec2, 1, name="b")
    assert p2.st.sets.HUNGER == pytest.approx(1 - 112.5 / 262.5)
```

  - Delete the whole Task 15 section: from `# --- Plan 11 Task 15: the satiety scalar in the writer ---` through `test_the_sandbox_decrease_multiplier_scales_the_decay`, including the `moodle` helper. Keep `test_the_satiety_bulk_option_reads_its_range`, which Task 9 retires.
  - Delete `test_moving_without_running_decays_at_the_idle_rate`, `test_a_melee_swing_decays_at_the_exercise_rate` and `test_a_gap_over_sixty_minutes_decays_over_3600_seconds_only`, with their section heading.
  - In `test_a_dry_writer_computes_and_sets_nothing`, replace `assert rec.satiety == 0.6 and rec.satietyStepped is True   # the scalar neither stepped nor re-marked` with `assert rec.satiety.P == 112.5 and rec.satiety.v == 4       # the pool neither fed, decayed nor seeded`.
  - Replace `LIMITATION_FOUR` with:

```python
LIMITATION_FOUR = (
    "HUNGER, THIRST and FATIGUE are written once a game minute; an eat or a drink shows at once and the next write "
    "overwrites it with the satiety target (the stomach's fullness and the post-absorptive pool P through the energy "
    "term, capped at 0.69), so an eat stays through the stomach it filled and the pool its emptied energy feeds; an "
    "eat another mod makes through a direct Eat call reaches the stomach through the reconcile path a minute late and "
    "as its macros only (no water or fibre mass), and a drink another mod makes through a direct DrinkFluid call "
    "outside the intake's wraps is not seen; P decays by a game-choice half-life on game time, asleep or awake, so a "
    "night's sleep ends hungry")
```

  - Rename `test_limitation_four_names_the_overwrite_and_the_scalar` to `test_limitation_four_names_the_overwrite_and_the_pool`, with its comment `# the self-report prints the count: kept at 11`.
  - Append the new section at the end of the file:

```python
# --- Plan 11c: satiety from physiology in the writer ------------------------------------------------------------

def step_ctx(h, p, rec, minute, ctx, name="a"):
    h.T.age = 100.0 + minute / 60
    h.NR.server.writer.step(name, p, rec, ctx)


def emptied(h, **kw):
    v = h.K.vector.new()
    for k, x in kw.items():
        v[k] = x
    return v


def test_a_record_with_p_writes_its_hunger_through_fullness_and_the_pool():
    h = boot()
    p = player(h)
    step(h, p, record(h), 1)
    assert p.st.sets.HUNGER == pytest.approx(0.4)                          # (1 - 0.5 x 0.6) x (1 - 112.5 / 262.5)


def test_the_energy_term_raises_the_hunger_of_a_deficit():
    h = boot()
    p = player(h)
    rec = record(h)
    rec.body.energyState = 1.5
    step(h, p, rec, 1)
    assert p.st.sets.HUNGER == pytest.approx(0.4 * 1.5 + 0.15 * 0.5)


def test_a_record_without_satiety_seeds_p_from_hunger():
    h = boot()
    p = player(h)
    p.st.v.HUNGER = 0.31
    rec = record(h)
    rec.satiety = None
    step(h, p, rec, 1)
    assert rec.satiety.v == 4 and h.NR.server.writer.stats.seeded == 1
    assert rec.satiety.P == pytest.approx(h.K.satiety.seedP(0.31, 0.6, 1))
    assert p.st.sets.HUNGER == pytest.approx(0.31)


def test_a_new_record_writes_back_the_hunger_it_read():
    h = boot()
    p = player(h)
    p.st.v.HUNGER = 0.4
    rec = h.K.store.new("a", 100.0)
    assert rec.satiety is None
    step(h, p, rec, 1)
    assert p.st.sets.HUNGER == pytest.approx(0.4)
    step(h, p, rec, 2)
    assert h.NR.server.writer.stats.seeded == 1                            # seeded once, then stepped


def test_a_stepped_pool_survives_a_restart():
    h = boot()
    p = player(h)
    rec = record(h)
    step(h, p, rec, 1)
    back = h.K.store.load(h.K.store.inputsOnly(rec), None, None)
    assert back.satiety.P == pytest.approx(112.5) and back.satiety.v == 4
    back.stomachFill = 0.6                                                  # kinetics stamps it each minute
    p2 = player(h)                                                          # the restart: a new object, a new hoist
    step(h, p2, back, 1)
    assert h.NR.server.writer.stats.seeded == 0 and p2.st.sets.HUNGER == pytest.approx(0.4)


def test_a_v3_record_is_seeded_once():
    h = boot()
    p = player(h)
    p.st.v.HUNGER = 0.35
    raw = h.rt.eval("{ v = 3, username = 'a', firstSeen = 1.0, lastSeen = 2.0, resets = 0, dead = false, satiety = 0.6, satietyStepped = true }")
    rec = h.K.store.load(raw, None, None)
    assert rec.satiety is None and rec.satietyStepped is None and rec.v == 4
    step(h, p, rec, 1)
    assert p.st.sets.HUNGER == pytest.approx(0.35)
    step(h, p, rec, 2)
    assert h.NR.server.writer.stats.seeded == 1


def test_a_non_finite_or_unmarked_pool_is_seeded_again():
    h = boot()
    p = player(h)
    p.st.v.HUNGER = 0.31
    rec = record(h)
    rec.satiety.P = float("nan")
    step(h, p, rec, 1)
    assert p.st.sets.HUNGER == pytest.approx(0.31) and h.NR.server.writer.stats.seeded == 1
    p2 = player(h, "b")
    p2.st.v.HUNGER = 0.31
    rec2 = record(h)
    rec2.satiety.v = 3
    step(h, p2, rec2, 1, name="b")
    assert p2.st.sets.HUNGER == pytest.approx(0.31) and h.NR.server.writer.stats.seeded == 2


def test_p_halves_over_its_half_life_of_game_time():
    h = boot()
    p = player(h)
    rec = record(h)
    step(h, p, rec, 1)
    step(h, p, rec, 121)                                                    # two game hours
    assert rec.satiety.P == pytest.approx(112.5 / 2)


def test_sleep_does_not_slow_the_decay():
    h = boot()
    p = player(h)
    p.asleep = True
    rec = record(h)
    step(h, p, rec, 1)
    step(h, p, rec, 121)
    assert rec.satiety.P == pytest.approx(112.5 / 2)                       # spec § 4: P runs on game time asleep too


def test_hearty_appetite_scales_the_decay_by_one_and_a_half():
    h = boot()
    p = player(h)
    p.getCharacterTraits = h.rt.eval("function(s) return { get = function(c, t) return t == 'HA' end } end")
    rec = record(h)
    step(h, p, rec, 1)
    step(h, p, rec, 121)
    assert rec.satiety.P == pytest.approx(112.5 * 2 ** -1.5)               # #0485, vanilla's game number


def test_light_eater_scales_the_decay_by_three_quarters():
    h = boot()
    p = player(h)
    p.getCharacterTraits = h.rt.eval("function(s) return { get = function(c, t) return t == 'LE' end } end")
    rec = record(h)
    step(h, p, rec, 1)
    step(h, p, rec, 121)
    assert rec.satiety.P == pytest.approx(112.5 * 2 ** -0.75)


def test_the_sandbox_decrease_multiplier_scales_the_decay():
    h = boot()
    h.G.getSandboxOptions = h.rt.eval("function() return { getStatsDecreaseMultiplier = function(s) return 2 end } end")
    p = player(h)
    rec = record(h)
    step(h, p, rec, 1)
    step(h, p, rec, 121)
    assert rec.satiety.P == pytest.approx(112.5 * 2 ** -2)                 # ruling 11c-11: trait x sd


def test_the_minutes_emptied_energy_feeds_p():
    h = boot()
    p = player(h)
    rec = record(h)
    step_ctx(h, p, rec, 1, h.rt.table(emptied=emptied(h, calories=100, carbs=25)))
    assert rec.satiety.P == pytest.approx(212.5)                            # the first write: fed, no time to decay
    step_ctx(h, p, rec, 2, h.rt.table(emptied=emptied(h, calories=40, proteins=10)))
    assert rec.satiety.P == pytest.approx((212.5 + 40 * 2.5) * 2 ** (-1 / 120))


def test_a_gap_over_sixty_minutes_decays_over_one_hour_only():
    h = boot()
    p = player(h)
    rec = record(h)
    step(h, p, rec, 1)
    step(h, p, rec, 181)                                                    # three game hours since the last write
    assert rec.satiety.P == pytest.approx(112.5 * 2 ** -0.5)


def test_overlay_steps_p_without_writing_hunger():
    h = boot(mode=2)
    p = player(h)
    rec = record(h)
    step(h, p, rec, 1)
    step(h, p, rec, 121)
    assert p.st.sets.HUNGER is None and rec.satiety.P == pytest.approx(112.5 / 2)


def test_a_p_the_step_made_non_finite_is_restamped():
    h = boot()
    p = player(h)
    rec = record(h)
    step(h, p, rec, 1)
    orig = h.K.satiety.decay
    h.K.satiety.decay = h.rt.eval("function(P, dtH, hl, t) return 0 / 0 end")
    try:
        step(h, p, rec, 2)
    finally:
        h.K.satiety.decay = orig
    assert rec.satiety.P == pytest.approx(112.5) and h.NR.server.writer.stats.guarded == 1
    assert p.st.sets.HUNGER == pytest.approx(0.4)
```

- [ ] **Step 4: Run the changed files to see them fail.**

Run: `python -m pytest testing/tests/kernel/test_kernel_stomach.py testing/tests/kernel/test_kinetics.py testing/tests/kernel/test_intake_shape.py testing/tests/kernel/test_writer_shape.py testing/tests/kernel/test_kernel_store.py testing/tests/kernel/test_store_file_shape.py testing/tests/kernel/test_server_reconcile_shape.py testing/tests/kernel/test_nutrients_shape.py testing/tests/kernel/test_metabolism_shape.py testing/tests/kernel/test_plan4_steady_state.py -q -p no:cacheprovider`

Expected: many failures, among them `liquid` None, `VERSION == 4`, `IN.sate` still in the source and `record.satiety` a number. Quote the last line. Tests that pass already are **follow-up pins**; list them by name. The `drain` rewrites of the context tests are among them, since `drain` exists since Task 2.

- [ ] **Step 5: The stomach and store kernels.**

  **`NR_Kernel_Stomach.lua`:**
  - Replace the header (lines 1–20, through `-- NR_Kernel_Vector.lua, so every K.vector and K.retention reference is at call time, never at load.`) with:

```lua
-- NR_Kernel_Stomach.lua -- the stomach's two lanes and absorption into the pool (spec § 4.2, § 4.4; Plan 11c spec
-- § 5a). A food lands in the solid buffer, its water with it (ingest); a drink's water lands in the liquid lane and
-- its other keys, its energy among them, in the buffer (ingestLiquid, ruling 11c-12). The slow clock empties both
-- lanes per step (drain): the solid lane's energy at a zero-order rate rising with the energy it holds, every other
-- key in the same proportion, never faster than water; the liquid lane first-order at a half-time that grows with the
-- solid lane's energy. Absorption applies per-nutrient bioavailability and the phytate/vitamin-C iron interaction
-- (absorb); the absorbed vector accumulates into the pool (toPool). The unabsorbed remainder is discarded.
-- Ruling T17-1 (x151r #2981): the factor reads the meal in the stomach, not the share emptied this
-- minute. The slow clock takes K.stomach.context(stomach) -- the buffer's phytate, vitC and calcium
-- BEFORE the minute's emptying -- and hands it to absorb(emptied, ctx), so a 400 mg phytate loaf reads
-- 400 mg. absorb(emptied) with no ctx keeps the Plan 2 reading off the emptied vector itself. Ruling T19-1 extends the
-- context to the fat factor: ctx carries the buffer's lipids. Caffeine and ethanol never enter the buffer (ruling
-- T17-2: the intake landing diverts them to the acute kernel's gut lane), so their BIOAVAIL entries stay 1.0 and unused.
-- The emptying constants rest on settled rows as labelled inferences (Plan 11c's block below); the absorption factors
-- cite settled rows. Pure: tables in, tables out, no Java. Slow-clock code with no @fastpath region, so math.exp and
-- the bounded `for` over K.vector.KEYS (a Lua table the kernel built, so `#` is a Lua length) are allowed. This file
-- sorts before NR_Kernel_Vector.lua, so every K.vector and K.retention reference is at call time, never at load.
```

  - Delete `K.stomach.HALF_TIME_H` and its comment, `K.stomach.FULL_BULK` and its comment, and the functions `bulkOf`, `seedFull`, `compositionScale`, `emptyFraction` and `empty`, with their comments.
  - Replace `new`, `ingest` and `fill` with:

```lua
-- A fresh stomach: an all-zero solid buffer and an empty liquid lane (spec § 4, ruling 11c-15: a record with no
-- stomach starts empty).
function K.stomach.new()
    local stomach = {}
    stomach.buffer = K.vector.new()
    stomach.liquid = 0
    return stomach
end

-- A food into the solid buffer, its water with it (a food's water stays with the food, spec § 3.1); returns the
-- stomach.
function K.stomach.ingest(stomach, vector)
    K.vector.add(stomach.buffer, vector, 1)
    return stomach
end
```

```lua
-- The fullness F the writer, the acute dose test and the mirror read: the stomach's mass over its comfortable
-- capacity, clamped to [0, 1] (K.satiety.fill, ruling 11c-8).
function K.stomach.fill(stomach)
    return K.satiety.fill(K.stomach.mass(stomach), K.stomach.CAPACITY_G)
end
```

  - In the Plan 11c block's comment (Task 2), replace `the first-order pieces above (...) retire in Task 6 once nothing calls them.` with `the first-order pieces it replaced retired in Task 6.`

  **`NR_Kernel_Store.lua`:**
  - Replace the version comment and VERSION line with:

```lua
-- The record version: 1 is Plan 1's identity-only S.new with the sub-tables laid lazily beside it; 2 is
-- the inputs-only contract below; 3 is v2 plus the satiety scalar; 4 is satiety from physiology (Plan 11c).
K.store.VERSION = 4 -- schema version: 4 replaces satiety (a scalar) and satietyStepped with satiety.P and its mark satiety.v, and stomach.bulk with stomach.liquid (Plan 11c)
```

  - Replace the INPUTS satiety comment and line with:

```lua
    -- the post-absorptive satiety pool P (weighted kcal) and its mark v = 4, which the writer seeds from HUNGER when
    -- absent, unmarked or non-finite (Plan 11c; a v3 scalar and its satietyStepped mark are dropped by this list)
    "satiety.P", "satiety.v",
```

  - Replace the kinetics comment's second and third lines and the line `"kineticsAge", "stomach.bulk", "stomach.buffer.*", "pool.*",` with:

```lua
    -- kinetics (NR_Server_Kinetics, K.stomach): the clock stamp the next minute's dtH reads, the liquid lane and the
    -- solid buffer (ingest and ingestLiquid add, drain empties), the absorbed pool (toPool accumulates; a diagnostic
    -- no step reads back, kept because it cannot be rebuilt)
    "kineticsAge", "stomach.liquid", "stomach.buffer.*", "pool.*",
```

  - In `K.store.new`, delete the line `r.satiety = 1 -- a placeholder: ...`.
  - In `K.store.defaults`, replace the stomach line with `rec.stomach = K.stomach.new() -- an empty stomach (ruling 11c-15); the stored buffer and liquid lane overwrite it, a v3 bulk is dropped`. Insert, before the `if type(raw.pool)` line:

```lua
    if type(raw.satiety) == "table" then
        rec.satiety = {} -- the stored pool and mark overwrite it; a v3 scalar is not a table and is dropped
    end
```

  - In `K.store.load`, delete the three lines `if raw.satiety == nil then` / `rec.satiety = nil ...` / `end`.

  **`NR_Kernel_Nutrients.lua`:** replace the comment on the `ACUTE_EMPTY_FILL` line, in place and on the same line, with `-- game choice, ruling 18 (S1032 gives the direction only); since Plan 11c the fill is mass over 430 g, so 0.2 is about 86 g (ruling 11c-14)`.

- [ ] **Step 6: The adapters.**

  **`NR_Server_Kinetics.lua`:**
  - Replace lines 1–18 (the header through `-- ruling T11).`) with:

```lua
-- NR_Server_Kinetics.lua -- the slow-clock drive of the stomach (spec § 4.2, § 4.4; Plan 11c): once per player per
-- game minute, inside the budgeted queue, both lanes empty over the game hours since the last run (K.stomach.drain:
-- the solid lane's energy at a zero-order rate, the liquid lane's water first-order), the emptied vector is absorbed,
-- the absorbed vector accumulates into the pool, the emptied vector rides the minute's context to the writer, which
-- feeds the satiety pool P from it (ruling 11c-11), and the fullness F (the stomach's mass over its comfortable
-- capacity) is stamped on the record as record.stomachFill for the writer and the mirror to read. A record with no
-- stomach starts with an empty one (spec § 4, ruling 11c-15); hunger carries over through P, which the writer seeds
-- from HUNGER at its first minute. The energy-state term is NR_Server_Metabolism's per-minute stamp
-- (record.body.energyState; the writer reads nil or NaN as 1).
```

  - Replace the `step` function with:

```lua
local function step(username, player, record, ctx)
    local age = NR.worldAge()
    if age == nil then
        if ctx ~= nil then
            ctx.absorbed = nil
            ctx.mealCa = nil
            ctx.emptied = nil
        end
        KIN.badAge = (KIN.badAge or 0) + 1        -- a minute with no clock read is skipped, never stamped 0
        return
    end
    if record.stomach == nil then
        record.stomach = K.stomach.new()              -- an empty stomach (spec § 4, ruling 11c-15)
    end
    if record.pool == nil then
        record.pool = K.vector.new()
    end
    local last = record.kineticsAge
    local dtH = 0
    if last ~= nil then
        dtH = K.max(age - last, 0)
    end
    record.kineticsAge = age
    if dtH > 0 then
        local meal = K.stomach.context(record.stomach, KIN.ctx)   -- the meal, before this minute's emptying
        local emptied = K.stomach.drain(record.stomach, dtH)
        local absorbed = K.stomach.absorb(emptied, meal)
        K.stomach.toPool(record.pool, absorbed)
        if ctx ~= nil then ctx.absorbed = absorbed end            -- the handoff to Metabolism, then Nutrients
        if ctx ~= nil then ctx.mealCa = meal.calcium end
        if ctx ~= nil then ctx.emptied = emptied end              -- the writer feeds P from it (ruling 11c-11)
    elseif ctx ~= nil then
        ctx.absorbed = nil
        ctx.mealCa = nil
        ctx.emptied = nil
    end
    local fill = K.stomach.fill(record.stomach)
    -- the self-heal for #2833: a non-finite fill or solid-lane energy (a stomach a NaN intake poisoned before the
    -- landing guard, or a corrupt record) is never stamped -- K.clamp passes NaN through -- so the stomach is reset
    -- empty and the record heals on this minute instead of writing NaN into the satiety read. The POOL is reset only
    -- when one of its own keys is non-finite. NR.server.intake.isFinite is the one finiteness test, read at call time.
    if not NR.finite(fill) or not NR.finite(record.stomach.buffer.calories) then
        record.stomach = K.stomach.new()
        local isFinite = NR.server.intake.isFinite
        local keys = K.vector.KEYS
        for i = 1, #keys do
            if not isFinite(record.pool[keys[i]]) then
                record.pool = K.vector.new()
                break
            end
        end
        fill = 0
        KIN.stats.failures = KIN.stats.failures + 1
        KIN.lastError = "kinetics: non-finite stomach fill for " .. tostring(username) .. "; stomach reset empty"
        NR.log.say(2, KIN.lastError)
    end
    record.stomachFill = fill
    KIN.stats.players = KIN.stats.players + 1
end
```

  **`NR_Server_Intake.lua`:**
  - In the header's landing list, replace `--  5. K.stomach.ingest.` with `--  5. K.stomach.ingest, or K.stomach.ingestLiquid for a drink (Plan 11c ruling 11c-12: its water in the liquid lane).`
  - `IN.land` becomes:

```lua
function IN.land(record, username, vec, lane)
    IN.landed[username] = true                     -- the writer's sip fold skips this minute (Plan 11 ruling 7)
    IN.addIngested(username, vec)
    local ok, flagged = pcall(IN.acuteAtEat, record, vec)
    if ok then
        IN.stats.acuteFlags = IN.stats.acuteFlags + flagged
    else
        IN.stats.acuteFailures = IN.stats.acuteFailures + 1
        IN.lastError = "acute test failed: " .. tostring(flagged)
        NR.log.say(2, "intake: " .. IN.lastError)
    end
    vec.vitB12 = K.interact.b12Ceiling(vec.vitB12 or 0)
    IN.pendingAlc[username] = (IN.pendingAlc[username] or 0) + (vec.ethanol or 0)
    IN.pendingCaf[username] = (IN.pendingCaf[username] or 0) + (vec.caffeine or 0)
    vec.ethanol = 0
    vec.caffeine = 0
    if lane == "liquid" then
        K.stomach.ingestLiquid(record.stomach, vec)
    else
        K.stomach.ingest(record.stomach, vec)
    end
    return vec
end
```

  - Its comment gains: `lane "liquid" (a drink, world water) lands the water in the liquid lane; anything else lands as food.`
  - In `IN.readBefore`, delete the line `b.hungerChange = read(item, "getHungerChange")   -- the laddered relief getter …`.
  - In `IN.readAfterAndLand`, replace the stomach line with `record.stomach = record.stomach or K.stomach.new()  -- an empty stomach, as kinetics lays it (ruling 11c-15)`, and delete the line `IN.sate(record, b.hungerChange, frac, K.stomach.bulkOf(vec))`.
  - Delete `IN.sate` and its comment block (from `-- Decision 2 (c), Task 15: an eat's or a drink's relief raises the satiety scalar` through its `end`).
  - In `IN.readDrinkBefore`, delete the two comment lines and the line `d.hungerChange = read(read(fc, "getProperties"), "getHungerChange")`.
  - In `IN.readDrinkAfterAndLand`, replace the stomach line with the same `K.stomach.new()` line, replace `IN.land(record, d.username, vec)` with `IN.land(record, d.username, vec, "liquid")`, and delete the line `IN.sate(record, d.hungerChange, litres / d.litresBefore, nil) …`.
  - In `IN.readWorldAfterAndLand`, replace `record.stomach = record.stomach or K.stomach.seedFull(K.stomach.new())` with `record.stomach = record.stomach or K.stomach.new()`, and `IN.land(record, d.username, vec)` with `IN.land(record, d.username, vec, "liquid")`.

  **`NR_Server_Reconcile.lua`:** replace `record.stomach = record.stomach or K.stomach.seedFull(K.stomach.new())  -- as the intake seeds an early eat` with `record.stomach = record.stomach or K.stomach.new()  -- an empty stomach, as the intake lays one (ruling 11c-15)`. The landing stays `IN.land(record, username, vec)`: macros only, into the solid buffer (J4).

  **`NR_Server_Nutrients.lua`:**
  - Replace the `NUT.FED_FILL` comment, in place, with `-- game choice: a stomach below 5 % of its comfortable capacity (about 21 g of mass since Plan 11c, ruling 11c-14) is empty for the alcohol-fasting glucose term`.
  - Replace the auto-drink and pending-water block, from `local stomach = record.stomach` through `f.viewPct = K.fluids.dehydPct(f, w, pendingG)           -- ruling T1-1`, with:

```lua
    local stomach = record.stomach
    if f.autoDrop > 0 then
        -- the writer's sip (THIRST's fall below its last write), converted to litres, lands as a drink: the liquid lane
        if stomach == nil then
            stomach = K.stomach.new()
            record.stomach = stomach
        end
        if NUT.waterVec == nil then NUT.waterVec = K.vector.new() end
        NUT.waterVec.water = NUT.LITRES_PER_THIRST * f.autoDrop * 1000
        K.stomach.ingestLiquid(stomach, NUT.waterVec)
        f.autoDrop = 0
    end
    f.dehydPct = K.fluids.dehydPct(f, w, 0)
    local pendingG = 0                                      -- both lanes' still-unabsorbed water (ruling T1-1)
    if stomach ~= nil and stomach.buffer ~= nil then
        local g = K.stomach.water(stomach)
        if finite(g) then pendingG = g end
    end
    f.viewPct = K.fluids.dehydPct(f, w, pendingG)           -- ruling T1-1
```

  **`NR_Server_Writer.lua`:**
  - Replace the header's two sentences `The HUNGER target is 1 - S, the satiety scalar (Task 15; NR_Kernel_Satiety.lua), stepped here at the rates saved at boot.` with `The HUNGER target is hungerTarget(sated(F, post(P)), energyState): the stomach's fullness F and the post-absorptive pool P (Plan 11c; NR_Kernel_Satiety.lua), P fed by the minute's emptied energy and decayed here.`
  - `W.stats` gains `guarded = 0`.
  - Replace limitation 4 with the text of `LIMITATION_FOUR` (Step 3), kept as one Lua string.
  - Replace `W.satiety` and its comment with:

```lua
-- Plan 11c: the satiety pool P (spec § 3.1, § 5a). A record whose satiety is absent, unmarked (v ~= 4) or non-finite
-- is seeded so the HUNGER it writes equals the HUNGER it read (K.satiety.seedP; ruling 11c-16; counted in seeded);
-- the minute's emptied vector (kinetics, ctx.emptied) feeds P, which then decays over the elapsed world age at the
-- half-life, scaled by the appetite trait (#0485) and the sandbox's stats-decrease multiplier (ruling 11c-11); a P
-- the step itself makes non-finite is re-stamped from its pre-step value (counted in guarded); the target is read
-- through the energy term.
function W.satiety(h, player, record, eng, inp, es, ctx)
    local F = finiteOr(record.stomachFill, 0)
    local s = record.satiety
    if type(s) ~= "table" or s.v ~= 4 or not NR.finite(s.P) then
        s = { P = K.satiety.seedP(inp.hunger, F, es), v = 4 }
        record.satiety = s
        W.stats.seeded = W.stats.seeded + 1
    end
    local P0 = s.P
    local T = CharacterTrait
    local tr = K.satiety.trait(T ~= nil and trait(h, T.HEARTY_APPETITE), T ~= nil and trait(h, T.LIGHT_EATER))
    if ctx ~= nil and ctx.emptied ~= nil then
        s.P = K.satiety.feed(s.P, ctx.emptied)
    end
    s.P = K.satiety.decay(s.P, K.clamp(inp.dtS, 0, W.c.maxStepS) / 3600, K.satiety.HALF_LIFE_H, tr * eng.sd)
    if not NR.finite(s.P) then
        s.P = P0
        W.stats.guarded = W.stats.guarded + 1
    end
    inp.hungerTarget = K.hybrid.hungerTarget(K.satiety.sated(F, K.satiety.post(s.P)), es)
end
```

  - In `W.step`, replace `W.satiety(h, player, record, eng, inp, es)` with `W.satiety(h, player, record, eng, inp, es, ctx)`.
  - Leave `W.rates`, its boot lines and `h.swipe` for Task 9.
  - Edit the dry-seam comment's parenthesis `(the satiety step and its mark, ...)` to `(the satiety pool's seed, feed and decay, the sip fold, the landing mark)`.

- [ ] **Step 7: Run the changed tests, then the kernel suite.**

Run the Step 4 command. Expected: all pass. Then run `grep -rn "seedFull\|bulkOf\|FULL_BULK\|HALF_TIME_H\|compositionScale\|emptyFraction\|stomach\.empty\b\|\.bulk\b\|satietyStepped\|IN\.sate\|hungerChange" mod testing/tests testing/PZTestKit` and list every hit in the report. Each remaining hit must be one of these:
- a comment naming what was retired;
- `scriptHunger`'s `getHungerChange` read in `IN.readBefore`;
- Task 15's `K.satiety.relief(hungerChange, frac)`, which Task 9 retires;
- the stand-in `getHungerChange` script stubs in the tests;
- a test asserting that a retired field is absent;
- `test_satiety_default.py`, which Task 9 retires.

Any other hit is a missed caller.

Run: `python -m pytest testing/tests/kernel -q -p no:cacheprovider`
Expected: everything passes except `test_golden_trace.py::test_the_golden_trace_of_1_0_0_is_reproduced`, the named change. Any other failure is a STOP.

- [ ] **Step 8: Re-record the golden trace under its named change and walk the leaves.**

Run: `python testing/tests/kernel/golden_trace.py --write`

Write `<ws>/task-6-golden-walk.py` with the Write tool:

```python
"""Plan 11c Task 6: the golden trace's changed leaves under "satiety from physiology" (workspace, never committed).
Run from the repository root after golden_trace.py --write."""
import json
import subprocess

GOLDEN = "testing/tests/kernel/golden/trace-1.0.0.json"
old = json.loads(subprocess.run(["git", "show", "HEAD:" + GOLDEN], capture_output=True, text=True,
                                check=True).stdout)
with open(GOLDEN, encoding="utf-8") as fh:
    new = json.load(fh)


def leaves(x, path=""):
    if isinstance(x, dict):
        for k in sorted(x, key=str):
            yield from leaves(x[k], path + "/" + str(k))
    elif isinstance(x, list):
        for i, v in enumerate(x):
            yield from leaves(v, path + "/" + str(i))
    else:
        yield path, x


def keyed(snaps):
    if isinstance(snaps, dict):
        return {str(k): v for k, v in snaps.items()}
    return {str(i): v for i, v in enumerate(snaps)}


print("printed_count", old.get("printed_count"), "->", new.get("printed_count"))
so, sn = keyed(old["snapshots"]), keyed(new["snapshots"])
for key in sorted(set(so) | set(sn), key=lambda s: (len(s), s)):
    a = dict(leaves(so.get(key, {})))
    b = dict(leaves(sn.get(key, {})))
    diff = sorted(k for k in set(a) | set(b) if a.get(k) != b.get(k))
    first = diff[0] if diff else None
    print("snapshot", key, "changed", len(diff), "first", first, a.get(first), "->", b.get(first))
```

Run it and paste its output in the report. Then trace two changed leaves to the line that moved them, for example:
- a record's `stomach/liquid` appearing at 0, from `K.stomach.new`;
- a `stomachFill` that moved from bulk over 8 to mass over 430, from `K.stomach.fill` and `K.stomach.mass`.

Name `printed_count` before and after, and why it moved if it did. A leaf whose cause is not one of this task's named changes is a STOP.

Run: `python -m pytest testing/tests/kernel -q -p no:cacheprovider`
Expected: all pass, the golden included.

- [ ] **Step 9: Gates, cost and commit.**
  - Run Task 2 Step 5's gates. The full `claims_check` lists every pointer this task's line moves shift; list them in the report, for example #3343's `NR_Kernel_Stomach.lua:120` quote (`emptyFraction`, now deleted). The controller re-anchors #3343 to an `@<sha>` pointer at the commit before this one; Task 10 supersedes it.
  - Extend `<ws>/bench_11c.py` with this function and call it from `__main__` after `stomach_costs()`:

```python
KCORE = r"""
function(st, pool, ctx)
    local K = NutritionRevamp.kernel
    local meal = K.stomach.context(st, ctx)
    local emptied = K.stomach.drain(st, 1 / 60)
    K.stomach.toPool(pool, K.stomach.absorb(emptied, meal))
end
"""


def writer_costs():
    from kernel.test_writer_shape import boot, player, record, step
    h = boot()
    p = player(h)
    rec = record(h)
    step(h, p, rec, 1)
    W = h.NR.server.writer
    print("W.step us", round(best(h, W.step, 20000, "a", p, rec, None), 3), "(Task 15: 5.85)")
    print("W.satiety us", round(best(h, W.satiety, 20000, W.h["a"], p, rec, W.inp["a"], W.input, 1, None), 3),
          "(Task 15: 0.70)")
    st = h.rt.eval(MEAL)()
    pool = h.K.vector.new()
    print("kinetics core us", round(best(h, h.rt.eval(KCORE), 20000, st, pool, h.rt.table()), 3))
```

  - Run it and report the three figures beside Task 15's.
  - Commit:

```bash
git commit -m "Satiety from physiology: two-lane stomach, the pool P in the writer, record v4; golden re-recorded (Plan 11c Task 6)" -- mod/NutritionRevamp/common/media/lua/shared/NR_Kernel_Stomach.lua mod/NutritionRevamp/common/media/lua/shared/NR_Kernel_Store.lua mod/NutritionRevamp/common/media/lua/shared/NR_Kernel_Nutrients.lua mod/NutritionRevamp/common/media/lua/server/NR_Server_Kinetics.lua mod/NutritionRevamp/common/media/lua/server/NR_Server_Intake.lua mod/NutritionRevamp/common/media/lua/server/NR_Server_Writer.lua mod/NutritionRevamp/common/media/lua/server/NR_Server_Nutrients.lua mod/NutritionRevamp/common/media/lua/server/NR_Server_Reconcile.lua testing/tests/kernel/test_kernel_stomach.py testing/tests/kernel/test_kinetics.py testing/tests/kernel/test_intake_shape.py testing/tests/kernel/test_writer_shape.py testing/tests/kernel/test_kernel_store.py testing/tests/kernel/test_store_file_shape.py testing/tests/kernel/test_server_reconcile_shape.py testing/tests/kernel/test_nutrients_shape.py testing/tests/kernel/test_metabolism_shape.py testing/tests/kernel/test_plan4_steady_state.py testing/tests/kernel/golden/trace-1.0.0.json
```

The report gives:
- the red run's last line and the follow-up pins;
- the green counts, with the number of tests deleted and why;
- the golden walk and the two traced leaves;
- `printed_count`;
- the pointer findings;
- the bench figures;
- the model id.

---
### Task 7: The soft cap — Opus implementer, Opus reviewer

The lane is M, after Task 6 and after the controller's ruling on Task 5's J1 and J2 (ruling 11c-13 stands, or `task-7-amendments.md` changes the effect). Past `K.stomach.CAPACITY_MAX_G` (730 g) of stomach mass, the writer floors DISCOMFORT once a game minute at `K.satiety.discomfort(mass, 730, 1100)`, which runs 0 at 730 g to 100 at 1100 g. It does this in both modes and never lowers DISCOMFORT. Nothing blocks an eat. Vanilla relaxes DISCOMFORT toward its own target between writes (Task 5 J2). The golden trace stays byte for byte, because its stand-ins have no `getStats` and the writer never hoists there.

**Files:**
- Modify: `mod/.../shared/NR_Kernel_Hybrid.lua` (`input`, `write`, the header) and `mod/.../server/NR_Server_Writer.lua` (`W.step`, limitation 4).
- Modify: `testing/tests/kernel/test_writer_shape.py`: `ENV`'s `CharacterStat` gains `DISCOMFORT = "DISCOMFORT"`, `STATS` gains `DISCOMFORT = 0`, and `LIMITATION_FOUR` gains its clause.
- Create: `testing/tests/kernel/test_soft_cap.py` (LF).

**Interfaces:**
- Consumes, from Task 2: `K.stomach.mass`, `K.stomach.CAPACITY_MAX_G` and `K.stomach.CAPACITY_HARD_G`.
- Consumes, from Task 3: `K.satiety.discomfort(mass, capMax, capHard)`.
- Consumes: `CharacterStat.DISCOMFORT`, whose range is 0–100 (Task 5 J2).
- Produces: `K.hybrid.input()` gains `discomfort = 0` and `discomfortTarget = 0`, and `K.hybrid.write` gains `out.discomfort`, which is nil for no write.

- [ ] **Step 1: Write the failing tests.**
  - In `test_writer_shape.py`, add `DISCOMFORT = "DISCOMFORT"` to `ENV`'s `CharacterStat` table and `DISCOMFORT = 0` to `STATS`.
  - Append to `LIMITATION_FOUR`'s last string, before its closing parenthesis, `"; past 730 g in the stomach the writer floors DISCOMFORT once a game minute (the soft cap, never a block), and vanilla's own refusal to start an eat at the FOOD_EATEN moodle's level 3 stands"`.
  - Create `testing/tests/kernel/test_soft_cap.py`:

```python
"""The soft cap (Plan 11c Task 7; ruling 11c-13 on Task 5's J1 and J2): past 730 g of stomach mass the writer floors
DISCOMFORT once a game minute at 100 x (mass - 730) / (1100 - 730), in both modes, never lowering it and never
blocking an eat (spec § 2 item 4). The thresholds are labelled inferences (S1250, S1253; ruling 11c-8)."""
import pytest

from .test_writer_shape import boot, player, record, step

WATER = "function(g) local v = NutritionRevamp.kernel.vector.new() v.water = g return v end"


def holding(h, rec, grams):
    st = h.K.stomach.new()
    h.K.stomach.ingestLiquid(st, h.rt.eval(WATER)(grams))
    rec.stomach = st


def test_the_input_starts_at_no_discomfort(host):
    inp = host.call("hybrid.input")
    assert inp.discomfort == 0 and inp.discomfortTarget == 0


def test_write_floors_discomfort_at_its_target(host):
    inp = host.call("hybrid.input")
    out = host.call("hybrid.output")
    c = host.call("hybrid.defaults")
    inp.discomfortTarget = 40
    inp.discomfort = 10
    host.call("hybrid.write", inp, out, c)
    assert out.discomfort == 40
    inp.discomfort = 50
    host.call("hybrid.write", inp, out, c)
    assert out.discomfort is None                                     # a floor: never lowered
    inp.discomfortTarget = 0
    inp.discomfort = 0
    host.call("hybrid.write", inp, out, c)
    assert out.discomfort is None


def test_a_stomach_past_its_soft_cap_floors_discomfort():
    h = boot()
    p = player(h)
    rec = record(h)
    holding(h, rec, 915.0)
    step(h, p, rec, 1)
    assert p.st.sets.DISCOMFORT == pytest.approx(50)                  # (915 - 730) / (1100 - 730) x 100


def test_a_stomach_under_the_cap_writes_no_discomfort():
    h = boot()
    p = player(h)
    rec = record(h)
    holding(h, rec, 700.0)
    step(h, p, rec, 1)
    assert p.st.sets.DISCOMFORT is None


def test_a_higher_discomfort_is_never_lowered():
    h = boot()
    p = player(h)
    p.st.v.DISCOMFORT = 80
    rec = record(h)
    holding(h, rec, 915.0)
    step(h, p, rec, 1)
    assert p.st.sets.DISCOMFORT is None


def test_overlay_writes_the_soft_cap_too():
    h = boot(mode=2)
    p = player(h)
    rec = record(h)
    holding(h, rec, 1500.0)
    step(h, p, rec, 1)
    assert p.st.sets.DISCOMFORT == 100 and p.st.sets.HUNGER is None


def test_a_record_with_no_stomach_writes_no_discomfort():
    h = boot()
    p = player(h)
    rec = record(h)
    step(h, p, rec, 1)
    assert rec.stomach is None and p.st.sets.DISCOMFORT is None


def test_the_cap_never_blocks_an_eat():
    h = boot()
    rec = record(h)
    holding(h, rec, 2000.0)
    rec.pool = h.K.vector.new()
    food = h.rt.eval("function() local v = NutritionRevamp.kernel.vector.new() v.water = 100 v.calories = 200 return v end")()
    h.NR.server.intake.land(rec, "a", food)
    assert h.K.stomach.mass(rec.stomach) == pytest.approx(2100)
```

- [ ] **Step 2: Run them to see them fail.**

Run: `python -m pytest testing/tests/kernel/test_soft_cap.py testing/tests/kernel/test_writer_shape.py -q -p no:cacheprovider`
Expected: FAIL. `inp.discomfort` is nil, `DISCOMFORT` is never set, and the limitation text differs. `test_a_stomach_under_the_cap_writes_no_discomfort`, `test_a_higher_discomfort_is_never_lowered`, `test_a_record_with_no_stomach_writes_no_discomfort` and `test_the_cap_never_blocks_an_eat` pass on the pre-change tree: they are **follow-up pins**, and the report labels them so.

- [ ] **Step 3: Write the kernel.** In `NR_Kernel_Hybrid.lua`:
  - In `K.hybrid.input()`, change the last field line `endurance = 1, lastEndurance = nil, rmod = 1,` to `endurance = 1, lastEndurance = nil, rmod = 1, discomfort = 0, discomfortTarget = 0,`.
  - In `K.hybrid.write`, after the `out.intox` block (`if it ~= nil and it == it then` … `end`), insert:

```lua
    out.discomfort = nil
    if inp.discomfortTarget > 0 and inp.discomfort < inp.discomfortTarget then
        out.discomfort = inp.discomfortTarget
    end
```

  - In the header, replace `Mode 2 (Overlay) writes everything but the first three.` with `Mode 2 (Overlay) writes everything but the first three; since Plan 11c the soft cap's DISCOMFORT floor is written in both modes.`

- [ ] **Step 4: Write the writer.** In `NR_Server_Writer.lua`'s `W.step`:
  - After the line `inp.rmod = finiteOr(body.rmod, 1)`, insert:

```lua
    inp.discomfort = get(h, CS.DISCOMFORT) or 0
    inp.discomfortTarget = 0
    local st = record.stomach
    if st ~= nil then
        inp.discomfortTarget = K.satiety.discomfort(K.stomach.mass(st), K.stomach.CAPACITY_MAX_G, K.stomach.CAPACITY_HARD_G)
    end
```

  - After `set(h, CS.ENDURANCE, out.endurance)`, insert `set(h, CS.DISCOMFORT, out.discomfort)`.
  - Replace limitation 4's string with the new `LIMITATION_FOUR` text. The count stays 11.
  - In the header, replace `INTOXICATION through K.hybrid.write,` with `INTOXICATION (and, since Plan 11c ruling 11c-13, the soft cap's DISCOMFORT floor past 730 g of stomach mass) through K.hybrid.write,`.

A NaN mass reads a NaN target, and `NaN > 0` is false, so it writes nothing; the kinetics self-heal resets the stomach on its next minute.

- [ ] **Step 5: Run the tests and the suite.**

Run: `python -m pytest testing/tests/kernel/test_soft_cap.py testing/tests/kernel/test_writer_shape.py testing/tests/kernel/test_kernel_hybrid.py testing/tests/kernel/test_heal_once.py -q -p no:cacheprovider`
Expected: all pass. `test_heal_once`'s writer-reads test proxies only `body`, `fluids`, `acute` and `effects` until Task 8, so it is unchanged.

Run: `python -m pytest testing/tests/kernel -q -p no:cacheprovider`
Expected: all pass, with the golden byte for byte and coverage at 100 %.

- [ ] **Step 6: Gates, cost and commit.** Run Task 2 Step 5's gates and list the pointer findings (the hybrid and writer lines shift). Run `bench_11c.py` and report `W.step` with the soft cap beside Task 6's figure and Task 15's 5.85 µs.

```bash
git add -- testing/tests/kernel/test_soft_cap.py
git commit -m "Soft cap: the writer floors DISCOMFORT past 730 g of stomach mass (Plan 11c Task 7)" -- mod/NutritionRevamp/common/media/lua/shared/NR_Kernel_Hybrid.lua mod/NutritionRevamp/common/media/lua/server/NR_Server_Writer.lua testing/tests/kernel/test_soft_cap.py testing/tests/kernel/test_writer_shape.py
```

---

### Task 8: The guard lists and the CROSS rows — Opus implementer, Opus reviewer

The lane is M, after Task 7. Kinetics names the stomach fields its self-heal guards in two lists, `KIN.GUARD = { "liquid" }` and `KIN.GUARD_BUFFER = { "calories" }`, and resets the stomach empty when any is non-finite. `test_heal_once.py`'s CROSS table gains these rows:
- kinetics' `stomach.liquid`, read by the nutrients step (the pending water), by the writer (the soft cap's mass) and by the store;
- kinetics' `stomach.buffer.calories`, read by the store.

The writer-reads test proxies the stomach as well. P is the writer's own state, which no other step reads in the minute; its guard is in the writer (Task 6, `W.stats.seeded` and `W.stats.guarded`). The golden trace stays byte for byte.

**Files:**
- Modify: `mod/.../server/NR_Server_Kinetics.lua`.
- Modify: `testing/tests/kernel/test_heal_once.py` (LF) and `testing/tests/kernel/test_kinetics.py` (CRLF).

**Interfaces:**
- Consumes, from Task 6: the kinetics self-heal.
- Produces: `NR.server.kinetics.GUARD` and `NR.server.kinetics.GUARD_BUFFER`, which are Lua arrays of field names.

- [ ] **Step 1: Write the failing tests.** In `test_heal_once.py`:
  - Append to the `CROSS` expression, after its `effects` rows:

```python
    + _rows("kinetics", "stomach", [("nutrients", ("liquid",)), ("writer", ("liquid",)), ("store", ("liquid",))])
    + _rows("kinetics", "stomach.buffer", [("store", ("calories",))])
```

  - Make `NEAR_END` `{"metabolism": "energy.state", "nutrients": "acute.iu", "effects": "effects.drain", "kinetics": "stomach.fill"}`.
  - In `test_the_guard_lists_are_step_1s_table`, append:

```python
    assert lua(N.kinetics.GUARD) == want("kinetics", "stomach")
    assert lua(N.kinetics.GUARD_BUFFER) == want("kinetics", "stomach.buffer")
```

  - Make `SUB_PRODUCER` `{"body": "metabolism", "fluids": "nutrients", "acute": "nutrients", "effects": "effects", "stomach": "kinetics"}`.
  - Make `WRITER_UNGUARDED` `{"acute.frozen", "fluids.autoDrop", "stomach.buffer"}`. Extend its comment with `; the stomach's buffer table, whose gram keys the kinetics heal reaches through the fill and whose energy GUARD_BUFFER names (the writer reads the mass only)`.
  - In `PROXY`, change the list to `{ "body", "fluids", "acute", "effects", "stomach" }`.
  - In `test_the_writers_cross_rows_are_its_reads`, add `rec.stomach = h.K.stomach.new()` after `rec = record(h)`.
  - In the module docstring, append the sentence `Kinetics (Plan 11c Task 8) heals by resetting the stomach empty rather than re-stamping: its GUARD lists name the fields that reset fires on; the writer's own pool P is guarded inside the writer (test_writer_shape.py).`

  In `test_kinetics.py` (CRLF), append:

```python
def test_the_guard_lists_name_the_liquid_lane_and_the_energy(kin_host):
    h = kin_host
    assert list(KIN(h).GUARD.values()) == ["liquid"]
    assert list(KIN(h).GUARD_BUFFER.values()) == ["calories"]
```

- [ ] **Step 2: Run them to see them fail.**

Run: `python -m pytest testing/tests/kernel/test_heal_once.py testing/tests/kernel/test_kinetics.py -q -p no:cacheprovider`
Expected: FAIL on the two guard-list tests (`N.kinetics.GUARD` is nil) and on the injection case (`kinetics`, `stomach`, `liquid`). A liquid lane made non-finite after the fill was read escapes Task 6's check, which reads the fill and the energy only. The injection case (`kinetics`, `stomach.buffer`, `calories`) and the writer-reads test pass on the pre-change tree: they are **follow-up pins**, and the report labels them so.

- [ ] **Step 3: Write the guard lists.** In `NR_Server_Kinetics.lua`, after `local KIN = NR.server.kinetics`, insert:

```lua
-- The stomach fields a later step reads that this step's arithmetic can leave non-finite (test_heal_once.py CROSS,
-- Plan 11c Task 8): a non-finite one resets the stomach empty with the fill. The gram keys reach the fill through the
-- mass; the liquid lane and the solid lane's energy are named.
KIN.GUARD = { "liquid" }
KIN.GUARD_BUFFER = { "calories" }

local function nonFinite(stomach)
    for i = 1, #KIN.GUARD do
        if not NR.finite(stomach[KIN.GUARD[i]]) then return true end
    end
    for i = 1, #KIN.GUARD_BUFFER do
        if not NR.finite(stomach.buffer[KIN.GUARD_BUFFER[i]]) then return true end
    end
    return false
end
```

  Then replace the heal's condition `if not NR.finite(fill) or not NR.finite(record.stomach.buffer.calories) then` with `if not NR.finite(fill) or nonFinite(record.stomach) then`.

- [ ] **Step 4: Run the tests and the suite.**

Run: `python -m pytest testing/tests/kernel/test_heal_once.py testing/tests/kernel/test_kinetics.py -q -p no:cacheprovider`
Expected: all pass.

Run: `python -m pytest testing/tests/kernel -q -p no:cacheprovider`
Expected: all pass, with the golden byte for byte.

- [ ] **Step 5: Gates and commit.** Run Task 2 Step 5's gates and list the pointer findings.

```bash
git commit -m "Heal once: kinetics' guard lists and the stomach's CROSS rows (Plan 11c Task 8)" -- mod/NutritionRevamp/common/media/lua/server/NR_Server_Kinetics.lua testing/tests/kernel/test_heal_once.py testing/tests/kernel/test_kinetics.py
```

---

## Phase D — Retirement, documentation and the close

### Task 9: Retire Task 15's pieces and NR.SatietyBulk — Sonnet implementer, Sonnet reviewer

The lane is M, after Task 8 and after the controller's reading of Task 5's J3.
- If J3 found the removed key ignored on every path, this task runs as written.
- If not, `task-9-amendments.md` carries the controller's ruling (for example, a hidden declared option kept for load) and this task runs that instead.

This task retires the following; every step is spelled out below. The golden trace stays byte for byte, because the options table and the writer's fields are not traced.
- Task 15's satiety kernel pieces: `R0`, `LO`, `HI`, `BETA`, `defaults`, `rate`, `step`, `relief`, `bulkFactor`, `add` and `seed`. `HEARTY`, `LIGHT` and `trait` stay (spec § 3.4).
- The writer's `W.rates` and its boot lines.
- The writer's melee-swing hoist (`h.swipe`).
- The `NR.SatietyBulk` option, its two translation strings and `NR.server.options.satietyBulk`.
- `test_satiety_default.py`.

**Files:**
- Modify: `mod/NutritionRevamp/common/media/lua/shared/NR_Kernel_Satiety.lua`, `mod/.../server/NR_Server_Writer.lua`, `mod/.../server/NR_Server_Options.lua`, `mod/NutritionRevamp/42.20.4/media/sandbox-options.txt` and `mod/.../shared/Translate/EN/Sandbox.json`.
- Modify: `testing/tests/kernel/test_kernel_satiety.py` and `testing/tests/kernel/test_writer_shape.py`.
- Delete: `testing/tests/kernel/test_satiety_default.py` (`git rm`).

**Interfaces:**
- Consumes nothing new.
- Produces: `K.satiety` keeps `HEARTY`, `LIGHT`, `trait` and Tasks 3's functions; `NR.server.options` has no `satietyBulk`; and `NR.server.writer` has no `rates`.

- [ ] **Step 1: Write the failing tests.**
  - Replace `testing/tests/kernel/test_kernel_satiety.py` whole with:

```python
"""The satiety kernel's Task 15 pieces are retired (Plan 11c Task 9); the appetite traits stay, vanilla's game numbers
(#0485), applied to the pool's decay (spec § 3.4). Satiety from physiology is test_kernel_satiety_physiology.py."""


def test_traits_scale_the_decay(host):
    assert host.call("satiety.trait", True, False) == 1.5 and host.call("satiety.trait", False, True) == 0.75
    assert host.call("satiety.trait", False, False) == 1


def test_the_trait_constants_are_vanillas(host):
    S = host.K.satiety
    assert (S.HEARTY, S.LIGHT) == (1.5, 0.75)


def test_task_15s_pieces_are_retired(host):
    S = host.K.satiety
    for name in ("R0", "LO", "HI", "BETA", "defaults", "rate", "step", "relief", "bulkFactor", "add", "seed"):
        assert S[name] is None, name
```

  - In `test_writer_shape.py`, replace `test_the_satiety_bulk_option_reads_its_range` with:

```python
def test_the_satiety_bulk_option_and_task_15s_writer_pieces_are_retired():
    h = boot()
    assert h.NR.server.options.satietyBulk is None
    assert h.NR.server.writer.rates is None
    h.G.SwipeStatePlayer = h.rt.eval("{ instance = function() return NR_T end }")
    p = player(h)
    step(h, p, record(h), 1)
    assert h.NR.server.writer.h["a"].swipe is None                # exercise no longer sates: no swing handle
    txt = os.path.join(REPO, "mod", "NutritionRevamp", "42.20.4", "media", "sandbox-options.txt")
    js = os.path.join(REPO, "mod", "NutritionRevamp", "common", "media", "lua", "shared", "Translate", "EN",
                      "Sandbox.json")
    for path in (txt, js):
        with open(path, encoding="utf-8") as fh:
            assert "SatietyBulk" not in fh.read(), path
```

- [ ] **Step 2: Run them to see them fail.**

Run: `python -m pytest testing/tests/kernel/test_kernel_satiety.py testing/tests/kernel/test_writer_shape.py -q -p no:cacheprovider`
Expected: FAIL on `test_task_15s_pieces_are_retired` (`R0` is 2.5079) and on the writer retirement test (`satietyBulk` is 0.25). The two trait tests pass: they are **follow-up pins**.

- [ ] **Step 3: Retire the code.**

  **`NR_Kernel_Satiety.lua`:**
  - Delete the lines from `K.satiety.R0 = 2.5079` through `K.satiety.BETA = 0.25 …`.
  - Delete the functions `defaults`, `rate`, `step`, `relief`, `bulkFactor`, `add` and `seed`, with their comments.
  - Keep `K.satiety.HEARTY`, `K.satiety.LIGHT` and `function K.satiety.trait`, and everything Task 3 appended.
  - Replace the file's first five comment lines with:

```lua
-- NR_Kernel_Satiety.lua -- satiety from physiology (Plan 11c; spec docs/superpowers/specs/2026-10-08-satiety-physiology-
-- design.md § 3.1 and § 5a). The writer reads hunger as K.hybrid.hungerTarget(sated(F, post(P)), energyState) once a
-- player-minute: F the stomach's fullness, P a post-absorptive pool of weighted kcal that the emptied energy feeds.
-- Task 15's vanilla-keyed scalar (its relief, bulk factor and vanilla's rates) retired in Plan 11c Task 9; the appetite
-- traits stay, vanilla's game numbers (#0485), applied to P's decay. Pure; one statement a line for the coverage gate.
```

  - Edit the `HEARTY` and `LIGHT` comments in place to `-- #0485: vanilla's game number, not science (spec § 3.4)`.

  **`NR_Server_Writer.lua`:**
  - In the `NR.server.writer = {` constructor, delete `rates = nil, `.
  - In `W.boot`, delete the comment `-- the satiety scalar's rates (Task 15): …` and the four lines that build `W.rates`.
  - In `W.hoist`, delete the four lines from `if SwipeStatePlayer ~= nil and SwipeStatePlayer.instance ~= nil then` through its `end`, and change `unhappyLast = 0, swipe = nil }` to `unhappyLast = 0 }`. `NR_Server_Metabolism.lua` keeps its own swipe read; leave it.

  **`NR_Server_Options.lua`:**
  - Delete the three comment lines from `-- The Plan 11 option (Decision 2 (c), ruling 9): satietyBulk,`.
  - Change `recordKeepDays = 30, satietyBulk = 0.25 }` to `recordKeepDays = 30 }`.
  - Delete the line `O.satietyBulk = readLeaf(sv, "SatietyBulk", 0.25, 0.25, 0.5, true)`.

  **`42.20.4/media/sandbox-options.txt`:** delete the `/* Plan 11 option (Decision 2 (c), ruling 9). SatietyBulk: …` comment, the `option NR.SatietyBulk` block through its closing `}`, and the blank line before the comment. The file then ends with the `NR.RecordKeepDays` block's `}` and the file's own final newline.

  **`Translate/EN/Sandbox.json`:** delete the two `Sandbox_NR_SatietyBulk` lines, and remove the trailing comma from the `"Sandbox_NR_RecordKeepDays_tooltip"` line, which is now the last key. The file stays valid JSON: check it with `python -c "import json;json.load(open('mod/NutritionRevamp/common/media/lua/shared/Translate/EN/Sandbox.json',encoding='utf-8'))"`.

  **Delete the Appendix D oracle:** `git rm -- testing/tests/kernel/test_satiety_default.py`. Its model is Task 15's, and Task 4's oracle replaces it.

- [ ] **Step 4: Run the tests, the grep and the suite.**

Run: `python -m pytest testing/tests/kernel/test_kernel_satiety.py testing/tests/kernel/test_writer_shape.py testing/tests/kernel/test_translations.py -q -p no:cacheprovider`
Expected: all pass.

Run: `grep -rn "satietyBulk\|SatietyBulk\|K\.satiety\.relief\|bulkFactor\|K\.satiety\.add\b\|K\.satiety\.seed\b\|K\.satiety\.rate\|K\.satiety\.step\|K\.satiety\.defaults\|W\.rates\|h\.swipe" mod testing/tests testing/PZTestKit`
Expected: the only hits are the retirement tests' own strings.

Run: `python -m pytest testing/tests/kernel -q -p no:cacheprovider`
Expected: all pass, with the golden byte for byte and coverage at 100 %.

- [ ] **Step 5: Gates and commit.**
  - Run Task 2 Step 5's gates, and in addition `python tools/release_pack.py check mod/NutritionRevamp`; the sandbox file and the translation keys must still pair. List the pointer findings: the satiety and writer lines shift.

```bash
git rm -- testing/tests/kernel/test_satiety_default.py
git commit -m "Retire Task 15's satiety scalar and NR.SatietyBulk (Plan 11c Task 9)" -- mod/NutritionRevamp/common/media/lua/shared/NR_Kernel_Satiety.lua mod/NutritionRevamp/common/media/lua/server/NR_Server_Writer.lua mod/NutritionRevamp/common/media/lua/server/NR_Server_Options.lua mod/NutritionRevamp/42.20.4/media/sandbox-options.txt mod/NutritionRevamp/common/media/lua/shared/Translate/EN/Sandbox.json testing/tests/kernel/test_kernel_satiety.py testing/tests/kernel/test_writer_shape.py testing/tests/kernel/test_satiety_default.py
```

  - The report states the deleted test count (`test_satiety_default.py`'s cases and the old `test_kernel_satiety.py` cases) and why.

---

### Task 10: The area page and its register rows — Opus implementer, Opus reviewer

The lane is M, after Task 9 and after the controller's re-anchor of Tasks 6–9's pointer shifts, so the code lines are final. This task writes the "Hunger from satiety" subsection on `docs/areas/body-effects.md` and its rule, re-tenses the two Plan 11a worked examples whose kernels this plan replaced, and files the register rows as a delta. Every row with a `repo:` pointer quotes the line it names, read off the tree at this task's start with `grep -n`; line numbers are never copied from this plan. Each claim's numbers sit at the path its pointer names (CLAUDE.md § 4.9). A row whose evidence is the mod's own line is `C/inference`, with the line as the worked example (ruling T12-1).

**Files:**
- Modify: `docs/areas/body-effects.md` (CRLF; edit it with `newline=''`).
- Create (workspace): `.superpowers/sdd/2026-10-08-plan-11c-satiety/task-10-claims-delta.tsv`.

**Interfaces:**
- Consumes: the final code lines of Tasks 2–9; the oracle's assertion lines (Task 4); and register rows #3343, #3344 and #3345.
- Produces: the anchor `areas/body-effects.md#hunger-from-satiety`; provisional rows `T11710.1` to `T11710.8`; a supersede of #3343 onto `T11710.3`.

- [ ] **Step 1: Write the delta.** Write `task-10-claims-delta.tsv` with the Write tool, with the header `op	id	claim	grade	pointer	bound	status	successor	kind	source	owner	reason` and these rows. Every row has `status` `settled`, `source` `Plan 11c Task 10 (desk), satiety from physiology` and `owner` `areas/body-effects.md#hunger-from-satiety` (the rule row's owner is `areas/body-effects.md#rules`). Each pointer is `repo:<path>:<line> "<quoted text>"`, one per listed line, joined by `; `.

  1. **`add T11710.1`**, grade `C`, kind `mechanism`.
     - Claim: "A mod can empty a stomach's energy at a zero-order rate that rises with the energy held, and in the worked example, this mod's kernel empties 1.25 + 0.0025 E kcal a game minute from a solid lane holding E kcal, moves every other key out in the same proportion, and never empties faster than water's 13-minute half-time."
     - Pointer: the `NR_Kernel_Stomach.lua` lines `K.stomach.RATE_BASE = 1.25`, `K.stomach.RATE_PER_KCAL = 0.0025`, `K.stomach.WATER_HALF_MIN = 13` and `return K.min(fe, fw)`.
     - Bound: `inference; the mod's own lines as the worked example (ruling T12-1); the physiology is S0131 (a labelled inference for solids, spec § 5a ruling 11c-4) and S1245 in docs/reference/science.tsv`.
  2. **`add T11710.2`**, grade `C`, kind `mechanism`.
     - Claim: "A mod can keep drunk water in a lane of its own that empties first-order and slows as the food beside it carries more energy, and in the worked example, this mod's kernel half-empties a drink's water in 13 minutes plus 0.12 minutes per kcal the solid lane holds, while the drink's energy joins the solid lane."
     - Pointer: the `NR_Kernel_Stomach.lua` lines `K.stomach.LIQUID_PER_KCAL = 0.12` and `return K.stomach.WATER_HALF_MIN + K.stomach.LIQUID_PER_KCAL * K.max(energy, 0)`, and the `ingestLiquid` line `stomach.buffer.water = own`.
     - Bound: `inference; the mod's own lines (ruling T12-1); S1234 over S1245, a labelled inference (ruling 11c-5)`.
  3. **`add T11710.3`**, grade `C`, kind `mechanism`.
     - Claim: "A mod can derive hunger from what the stomach holds and what it has delivered, and in the worked example, this mod's writer sets HUNGER to (1 - Z) x energyState plus 0.15 x (energyState - 1) above an energyState of 1, with Z = 1 - (1 - 0.5 F)(1 - P / (P + 150)), F the stomach's mass over 430 g and P a pool of weighted kcal fed by the energy leaving the stomach (protein 2.5, carbohydrate and fat 1) that halves every 2 game hours."
     - Pointer: the `NR_Kernel_Satiety.lua` lines `K.satiety.W_PROTEIN = 2.5`, `K.satiety.HALF_LIFE_H = 2.0`, `K.satiety.P50 = 150`, `K.satiety.FULL_WEIGHT = 0.5` and `return 1 - (1 - K.satiety.FULL_WEIGHT * F) * (1 - Pn)`; the `NR_Kernel_Hybrid.lua` lines `return K.clamp((1 - x) * energyState + K.hybrid.DEFICIT_FLOOR * K.max(0, energyState - 1), 0, 1)` and `K.hybrid.DEFICIT_FLOOR = 0.15`; the `NR_Kernel_Stomach.lua` line `K.stomach.CAPACITY_G = 430`; and the `NR_Server_Writer.lua` line `inp.hungerTarget = K.hybrid.hungerTarget(K.satiety.sated(F, K.satiety.post(s.P)), es)`.
     - Bound: `inference; the mod's own lines (ruling T12-1); W_PROTEIN, HALF_LIFE_H, P50 and FULL_WEIGHT are game choices (S1268 and S1270 open), the 430 g a labelled inference from S1250 (ruling 11c-8), the floor's 0.15 a game choice (S1271 open)`.
  4. **`supersede #3343`**, successor `T11710.3`; reason `Plan 11c replaced the first-order stomach half-time the claim's worked example reads`.
  5. **`add T11710.4`**, grade `C`, kind `mechanism`.
     - Claim: "In the worked example's offline replay, a 650 kcal mixed meal eaten at HUNGER 0.25 brings HUNGER back to 0.25 between 240 and 300 game minutes later, a 239 kcal protein snack at minute 240 delays that return 1.5 to 2.0 times as long as a carbohydrate one, and a soup holds hunger lower over three hours than its casserole with the water drunk."
     - Pointer: the `testing/tests/kernel/test_satiety_meal_studies.py` lines `assert t is not None and 240 <= t <= 300, t`, `assert 1.5 <= delay["p"] / delay["c"] <= 2.0, delay  # S1224: 60 / 34 = 1.76; the band is the oracle's tolerance` and `assert sum(w - s for s, w in zip(hs_s, hs_w)) / 180 > 0`.
     - Bound: `inference; an offline replay of the kernels under lupa (the oracle, Plan 11c Task 4, accepted after its mutation pass); the protocols are S1247 and S1248, S1224, S1232; the meal request read at HUNGER 0.25 is a game choice (ruling 11c-17)`.
  6. **`add T11710.5`**, grade `C`, kind `bound`.
     - Claim: "The worked example's model does not reproduce three study readings: its interval grows faster with a preload's energy than Callahan 2004's, a snack's delay of the next meal is longer than Marmonier 2000's 25 to 60 minutes, and both of Rolls 1999's 17-minute preloads read at full fullness."
     - Pointer: the oracle docstring's three bullet lines, from `- S1247's dose slope:` to `alongside is checked within the oracle's 0.07 tolerance instead.`.
     - Bound: `inference; the oracle's own statement of its limits (Plan 11c ruling 11c-17)`.
  7. **`add T11710.6`**, grade `C`, kind `mechanism`.
     - Claim: "A mod can make overeating uncomfortable without blocking it, and in the worked example, while the stomach holds more than 730 g this mod's writer floors DISCOMFORT once a game minute at 100 x (mass - 730) / (1100 - 730), in both modes, never lowering it."
     - Pointer: the `NR_Kernel_Satiety.lua` line `return K.satiety.DISCOMFORT_MAX * K.clamp((mass - capMax) / (capHard - capMax), 0, 1)`; the `NR_Kernel_Stomach.lua` lines `K.stomach.CAPACITY_MAX_G = 730` and `K.stomach.CAPACITY_HARD_G = 1100`; and the `NR_Server_Writer.lua` line `set(h, CS.DISCOMFORT, out.discomfort)`.
     - Bound: `inference; the mod's own lines (ruling T12-1); the 730 g and 1100 g are labelled inferences from S1250 and S1253 (ruling 11c-8); vanilla's DISCOMFORT relaxation is Task 5's T11705 row (the minted id at Task 5's mint)`. Write the minted id; the controller supplies it in `task-10-amendments.md`.
  8. **`add T11710.7`**, grade `C`, kind `mechanism`.
     - Claim: "A mod that replaces its hunger state can carry each character's hunger across the change, and in the worked example, a version-3 record's satiety scalar and its mark are dropped at load, and the writer seeds the pool P at its first minute so the HUNGER it then writes equals the HUNGER it read."
     - Pointer: the `NR_Kernel_Store.lua` lines `K.store.VERSION = 4 …` (quote its first 30 characters) and `"satiety.P", "satiety.v",`; and the `NR_Server_Writer.lua` line `s = { P = K.satiety.seedP(inp.hunger, F, es), v = 4 }`.
     - Bound: `inference; the mod's own lines (ruling T12-1); the seed inverts the hunger function (test_kernel_satiety_physiology.py)`.
  9. **`add T11710.8`**, grade `C`, kind `rule`.
     - Claim: the rule line's text (Step 2) without its leading `- ` and its tags.
     - Pointer: copied from T11710.3's pointer.
     - Bound: `inference; a reading of T11710.3 and T11710.4`. The controller rewrites both provisional ids to minted ids in its bound pass at the mint, as 249c1cc did.

- [ ] **Step 2: Write the page.** In `docs/areas/body-effects.md`:
  - **The new subsection.** Insert it after the paragraph `The mod's own live readings of this seat are on [testing-your-mod](testing-your-mod.md#scenario-inputs).` and before `<a id="perk-level"></a>`:

```markdown
<a id="hunger-from-satiety"></a>
### Hunger from satiety

A mod that owns HUNGER through the once-a-minute write still has to decide what hunger follows, and the physiology answers it with the stomach and what the stomach has delivered rather than with an item's hunger value.
<the T11710.1 claim sentence> [T11710.1/C/inference]
<the T11710.2 claim sentence> [T11710.2/C/inference]
<the T11710.3 claim sentence> [T11710.3/C/inference]
<the T11710.4 claim sentence> [T11710.4/C/inference]
<the T11710.5 claim sentence> [T11710.5/C/inference]
<the T11710.6 claim sentence> [T11710.6/C/inference]
<the T11710.7 claim sentence> [T11710.7/C/inference]
The cited physiology behind each constant, and which constants are game choices, is in [the science register](../reference/science.md), under the satiety topic.
```

    Each `<the T11710.n claim sentence>` is that row's claim text from Step 1, copied byte for byte. That is a copy instruction, not a placeholder: the page sentence and the register claim are the same words.

  - **The superseded worked example.** Delete line 96's sentence ("A takeover can pace hunger as a stomach that empties with a half-time T, …", tagged #3343). Its successor's sentence lives in the new subsection, and the apply tool rewrites no tag that is gone.
  - **The two re-tensed sentences.** In the sentences tagged #3344 and #3345, change `this mod's kernels run offline` and `this mod's kernel model run offline` to `this mod's Plan 11a kernels (42784ff) run offline` and `this mod's Plan 11a kernel model (42784ff) run offline`. Their rows' bounds already pin 42784ff, so the rows are untouched.
  - **The rule.** Append under `## Rules`, as the last rule line:

```markdown
- Derive a character's hunger from what its stomach holds and what it has delivered, never from an item's hunger value: the stomach's fullness and a pool fed by the energy that leaves it carry protein's extra satiety, a soup's volume and a meal's size, where an item's hunger value carries only vanilla's per-item calibration [T11710.8/C/inference] [T11710.3/C/inference].
```

- [ ] **Step 3: Dry-run and lint.**
  - `python tools/claims_delta.py apply .superpowers/sdd/2026-10-08-plan-11c-satiety/task-10-claims-delta.tsv --pages docs/areas/body-effects.md --dry-run` (no error);
  - `python tools/page_lint.py docs/areas/body-effects.md` (0);
  - `PYTHONIOENCODING=utf-8 python tools/claims_check.py --allow-provisional` (0, beyond the pointer-only re-anchors already folded in by the controller).

  If the checker names `.claude/skills/nutrition-body-effects/SKILL.md` (a quoted rule out of sync), report it to the controller; this task does not edit the skill.

- [ ] **Step 4: Commit the page.** The delta stays in the workspace for the controller.

```bash
PYTHONIOENCODING=utf-8 python tools/claims_check.py --staged --allow-provisional
git commit -m "Body effects: hunger from satiety, its worked examples and rule (Plan 11c Task 10)" -- docs/areas/body-effects.md
```

The checker must read 0 before the commit.

- [ ] **Step 5: The controller's mint.**
  - Apply the delta (`python tools/claims_delta.py apply <delta> --pages docs/areas/body-effects.md`).
  - Run the bound pass for T11710.6 and T11710.8.
  - Run `python tools/reference_gen.py cited-by --check` and `contradictions --check`.
  - Run the full checker without the allowance (0).
  - Re-read one minted claim from the register.
  - Commit the register and the page together.

---

### Task 11: The close of Plan 11c — controller (Opus reviews)

- [ ] **Step 1: The whole-pass review.** Dispatch two fresh read-only Opus reviewers in parallel, each with the review package `scripts/review-package docs/superpowers/plans/2026-10-08-plan-11c-satiety.md <Task 2's parent> HEAD` (artifact JSON excluded).
  - **Review A: spec coverage and the oracle.** Every item of spec §§ 3–8 as § 5a amends it maps to code or to a named limitation. Every shipped constant names its row or label exactly as § 5a rules. The reviewer re-samples the mutation pass on four mutations of its choosing (`mutate_11c.py`), and re-reads two oracle protocols against their S rows.
  - **Review B: a line-level bug review.** It covers the plan's mod commits: Kahlua rules, the one-statement-per-line rule, NaN paths, the v3 → v4 migration on a real v3 record, the liquid lane under the auto-drink sip, the soft cap in Mode 2, and the ghost dry seam with the new fields.
- [ ] **Step 2: The fix wave.** One consolidated wave of fresh implementers on disjoint files: Opus for mod code, Sonnet for spelled-out edits. Then a scoped re-review of each fix.
- [ ] **Step 3: The § 3 gates, in their own calls.**
  - Every `mod/` gate.
  - `PYTHONIOENCODING=utf-8 python tools/claims_check.py` (the full run, 0, no allowance).
  - `python tools/science_check.py` and `--scan mod` (0).
  - `python tools/page_lint.py` on every page touched (0).
  - `python tools/reference_gen.py cited-by --check` and `contradictions --check`.
  - `python -m pytest tools/tests testing/tests -q`. Its passed count goes into CLAUDE.md § 3's count line as "N passed on <date> at the Plan 11c close", prepending to the line's history and never dropping.
  - The golden sha256, ledgered.
- [ ] **Step 4: Push and record.**
  - Push `main`.
  - Update `C:\Users\Angus\.claude\projects\C--Users-Angus\memory\pz-nutrition-mod-project.md` and its `MEMORY.md` index: Plan 11c closed, record v4, the register and science ids, the pytest count, and what Plan 11b now acts on.
  - Ledger `Task 11: complete`.
  - Write the Plan 11b amendments the close found into `.superpowers/sdd/2026-10-08-plan-11b-live-release/` before 11b starts:
    - historical drivers such as `testing/experiments/x132_coboot.py` read `stomach.bulk`, so a new driver reads `stomach.liquid` and `stomachFill`;
    - 11b's acceptance reads the soft cap, the sleep-ends-hungry limit and the two fill thresholds of ruling 11c-14;
    - 11b's README and CHANGELOG name satiety from physiology and the retired `NR.SatietyBulk`.

---

## Self-Review

**1. Spec coverage** (spec §§ 1–8, as § 5a amends § 3):

| spec item | task |
|---|---|
| § 2.1 two signals F and P; § 3.1 `K.satiety` fill, feed, decay, post, sated, seedP | 3 (kernel), 6 (writer) |
| § 2.2 a 650–700 kcal meal satisfies 4–5 h | 3 (constants), 4 (`test_a_650_kcal_mixed_meal…`) |
| § 2.3 the deficit drive D | 3 (`DEFICIT_FLOOR`), 4 (the CALERIE bound and pin) |
| § 2.4 the soft cap, never a block | 5 (J1, J2), 7 |
| § 2.5 every constant on a settled row or labelled | 2, 3 (label tests), Global Constraints |
| § 3.1 fill by mass, `massOf`, `stomach.mass` (ruling 11c-10: read, not stored) | 2, 6 |
| § 3.1 the liquid lane; § 5a 11c-5 | 2, 6 (the intake routes), 4 (water, shakes, soup) |
| § 3.1 the emptied vector feeds P | 6 (`ctx.emptied`, ruling 11c-11) |
| § 5a 11c-4 the zero-order energy lane replaces `emptyFraction` | 2, 6 (retired), 4 (Hunt, linearity) |
| § 5a 11c-6 fibre neutral, through mass only | 2 (`massOf`; fibre has no weight in `weigh`) |
| § 5a 11c-7 protein weighted, carbohydrate = fat | 3, 4 (Marmonier, Kohanmoo) |
| § 5a 11c-8 capacity 430 g and the cap 730 g | 2, 7 |
| § 3.2 the per-minute order: drain, feed, decay, F, Z, HUNGER capped 0.69 | 6 (kinetics, then the writer, then `K.hybrid.write`'s cap) |
| § 3.3 the queue, the writer's once a minute, the store, the heals, the bus | unchanged; 8 (guards and CROSS) |
| § 3.4 Task 15's pieces, `NR.SatietyBulk`, `IN.sate`'s read, the drink special case, `satietyStepped`, the rate-based decay go; the traits stay | 6 (`IN.sate`, the drink case, `satietyStepped`), 9 (the rest) |
| § 4 migration v3 → v4 and the empty stomach | 6 |
| § 4 cooking, partial eats, zero-energy items, sleep, overlay, non-finite P | 6 (writer tests: sleep, overlay, non-finite), 2 (no-energy lane) |
| § 4 a direct `Eat` reaches the stomach via reconcile | 5 (J4), 6 (the reconcile pin, limitation 4) |
| § 6 the oracle, three or more replays citing S rows, and the mutation pass | 4 |
| § 6 the golden moves under "satiety from physiology", leaves walked and two traced | 6 Step 8 |
| § 7 Rule 6, the cost beside 0.70 µs | 2, 6, 7 (`bench_11c.py`) |
| § 8.5 the removed key is ignored, confirmed on the jar | 5 (J3), 9 |
| § 8.6 the documentation and register rows; the limitation count kept | 10; 6 and 7 (limitation 4, count 11) |
| § 8.7 the close | 11 |

No spec requirement is without a task. One deviation is ruled and flagged: the soft cap sits in the writer, not the intake (ruling 11c-13).

**2. Placeholder scan.**
- The plan contains no "TBD" or "TODO" and no "similar to Task N"; every code step carries its code.
- Two steps defer to a reading that only the task itself can make, and say so explicitly: the register pointers' line numbers (Task 10 reads them off the final tree with `grep -n`), and the minted id of Task 5's DISCOMFORT row (supplied by the controller in `task-10-amendments.md`).
- Task 10's `<the T11710.n claim sentence>` lines are explicit copy instructions from Step 1's rows.

**3. Type and name consistency.**
- `K.stomach.drain(stomach, dtH)` takes game hours everywhere: Task 2, the oracle's `1 / 60`, and kinetics' `dtH`.
- `K.satiety.decay(P, dtH, halfLifeH, trait)` takes hours: the writer passes `clamp(dtS) / 3600` and the oracle `1 / 60`.
- `K.satiety.feed(P, vector)` takes the emptied vector (`ctx.emptied`) in the writer and the oracle.
- `K.satiety.seedP(hunger, F, energyState)` has the same order in Task 3, Task 4's `start_p` and Task 6's writer.
- `K.satiety.discomfort(mass, capMax, capHard)` has the same order in Tasks 3 and 7.
- `record.satiety = { P, v = 4 }` is the same in Task 6's writer, the store's INPUTS (`satiety.P`, `satiety.v`) and every test.
- `stomach.liquid` is the same in Tasks 2, 6 and 8 and in the INPUTS.
- `KIN.GUARD` and `KIN.GUARD_BUFFER` are the same in Task 8's code and its tests.
- The vector's keys are `calories`, `proteins`, `carbs`, `lipids`, `fibre` and `water` (`K.vector.KEYS`), never the spec's prose names "protein" and "carbohydrates".
