# Plan 12: polish, code review and refactor before the upload

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development. Steps use checkbox (`- [ ]`) syntax.

**Goal:** before Angus uploads 1.0.0, find and fix real defects in the shipped mod, refactor where the code's structure or performance improves, extract the experiment drivers' shared helpers into one module, and clear the small pending items, so the staged release is the best the evidence supports.

**Authority:** Angus, 2026-10-13: "continue thru to any remaining pending items or otherwise polish, code review, and refactor"; "unattended, dont pause for questions, pivot to another task if something doesn't have an ideal recommended path". CLAUDE.md § 6 standing rule: until the release, every task refactors heavily as it goes. There is no spec; rulings are provisional and recorded in the ledger.

## Global constraints
- **The golden trace** (`testing/tests/kernel/test_golden_trace.py`) is reproduced byte for byte by every refactor. A behaviour change is a fix with a named cause and re-records the golden in its own commit (CLAUDE.md § 6).
- **Rule 6:** no per-tick work. A change on the hot path is benched before and after.
- **Every § 3 gate** runs for each commit's paths. Run the full `claims_check` after any edit to a file the register points into.
- **No live boot unless a fix needs a live reading.** Any boot follows § 5.
- **Re-stage at the close.** The release is re-staged at the close (`release_pack.py stage mod/NutritionRevamp --out release`), so the staged bytes are the reviewed bytes.

## Tasks

### Task 1: the whole-mod code review (three Opus reviewers in parallel, read-only)
Three areas, each with its own reviewer:
- **R1:** the kernels, `mod/NutritionRevamp/common/media/lua/shared/NR_Kernel*.lua` and `NR_Data_*.lua`.
- **R2:** the server adapters, `.../lua/server/*.lua`.
- **R3:** the client and UI, `.../lua/client/*.lua`, plus the scripts, translations and `mod.info`.

Each reviewer reads every line for:
- correctness: logic, edge cases, nil, NaN, units, sex, death and respawn, disconnect;
- Kahlua and engine hazards;
- multiplayer authority;
- performance under Rule 6;
- structure: duplication, dead code, unclear abstraction, misnamed or misplaced code.

Every finding states a concrete scenario and is classed as a **bug** (a defect a player or server can hit), a **refactor** (structure or performance, no behaviour change), or a **nit**. Output: `task-1-R<n>-findings.md`.

### Task 2: the bug fix wave (Opus implementer; serial mod lane)
1. The controller verifies and triages the Task 1 bugs. Two rulings apply:
   - a bug whose fix changes the design is ruled on, or deferred to Angus in the close report;
   - a bug with a clear fix is fixed test-first.
2. Each fix is its own commit, with its test and a golden re-record only under a named cause.
3. A reviewer (Opus) checks the wave.

### Task 3: the refactor wave (Opus implementer; serial mod lane, after Task 2)
1. The controller ranks the Task 1 refactors by maintainability gain against risk.
2. The implementer does the ranked list with the golden byte-identical, re-anchoring every register pointer it moves.
3. A reviewer (Opus) checks it, with a mutation spot-check that the golden still guards each touched path.

### Task 4: the drivers' shared module (Sonnet implementer; testing lane, parallel with Tasks 2-3)
- Extract the session helpers every recent driver copies into `testing/experiments/xlib.py`, with offline tests that exercise each helper's error path:
  - `run_phase`;
  - ping and liveness, and the wall budget;
  - the deployed-marker check, read once;
  - the staged-manifest gate;
  - the food spawn confirmed by `item.get`;
  - `grep_noecho`;
  - the abort and teardown.
- Frozen drivers are never edited.
- CLAUDE.md § 5's "a new experiment lib starts from the latest lib" points at the module.

### Task 5: the pending items (controller; docs lane)
- **S1076 and S0554**, uncited by any mod line: a status note or a decision.
- **#3788** (C-2's first-minute eat): design a method that does not join under a slowed clock. If no method is clean, the row stays open with the reason.
- **The early-ending burpee set** (x404, 50.98 of 60 game minutes): read the artifact and the client's endurance threshold, and settle it or write it open.
- **The 139-character comment at `PZTestKit_Server.lua:4468`**, if Task 4 touches that file anyway.

### Task 6: the close
1. A whole-pass review and one fix wave.
2. Every § 3 gate.
3. Re-stage the release.
4. Update CLAUDE.md and memory.
5. Push.
6. A close report for Angus: the deferred design decisions and anything for the upload.
