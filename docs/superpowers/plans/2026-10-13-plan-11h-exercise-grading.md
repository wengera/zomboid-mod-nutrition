# Plan 11h: Exercise grading (C-2) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bill each Fitness exercise at its own published intensity: the general/moderate codes of the 2024 Compendium, read server-side from the exercise type. Keep every set's acute hunger suppression, and re-check the fits the change moves.

**Architecture:**
- A file-scope wrapper on `ISFitnessAction.serverStart`/`serverStop` records `self.exeDataType` per username.
- `K.energy.EXERCISE_MET` maps a type to its MET. `billClass` bills it while the exercise flag is set, and falls back to the flat 6.0 with a counter.
- `W.vigorous` reads a Fitness set as resistance-vigorous from the flag, before the MET test.

**Tech Stack:** Lua 5.1 (Kahlua) kernels, lupa tests, `tools/fit_deficit_drive.py`, `testing/pzt` for the live run.

**Spec:** `docs/superpowers/specs/2026-10-13-exercise-grading-design.md` (approved by Angus, 2026-10-13). The spike report is `.superpowers/sdd/c2-exercise-grading/spike-report.md`.

## Global Constraints
- **CLAUDE.md governs.** §§ 3–7 apply. In particular:
  - run the full `claims_check` after any commit that touches a file the register points into;
  - pin only lines the change rewrote, and re-anchor lines it only moved;
  - count Java calls with a stub for any per-minute adapter change (Rule 6);
  - refactor as you go;
  - no backward compatibility.
- **The Fitness function.** Never wrap or replace `ISFitnessAction.new`.
- **The intensity table** carries the general/moderate codes: squats 3.0, pushups 3.8, situp 3.8, burpees 7.5, barbellcurl, dumbbellpress and bicepscurl 3.5. Each sits on a settled science row. The curl and press codes are labelled approximate game choices.
- **Models.** Opus for evidence, the build, the live run and the reviews; Sonnet for spelled-out fixes and scoped re-reviews. The model is always named.

### Task 0: Workspace and ledger (controller)
- [ ] Run `scripts/sdd-workspace` from the repository root for this plan.
- [ ] The ledger records HEAD, the pytest count (3945), the golden sha, the next register id (#3721) and the next science id (S1895).

### Task 1: The science rows (Opus citation review, then the controller's mint)
- [ ] An Opus reviewer runs the citation review of `.superpowers/sdd/c2-exercise-grading/c2-rows.tsv`, in the 11g Task 2 format: it writes a review and a corrections file.
- [ ] A Sonnet applier applies the corrections verbatim.
- [ ] The controller mints from S1895 with `tools/science_delta.py`, runs `science_check` → 0, and commits.

### Task 2: The build (Opus; lane M)
**Files:**
- Create the server Fitness file holding the wrapper, beside the existing training hooks.
- Modify `NR_Kernel_Energy.lua` (`EXERCISE_MET` beside the class table; `billClass`).
- Modify `NR_Server_Metabolism.lua` (pass the recorded type), `NR_Server_Writer.lua` (`W.vigorous` reads the flag first) and `NR_Server_Training` (read the real type first).
- Modify the departure pruning.
- Add tests.

- [ ] **Step 1: Tests first.**
  - the table values and their rows;
  - the wrapper calls the original and records then clears the type, with no record when `new` is untouched;
  - the fallback bills 6.0 and counts;
  - every Fitness minute is vigorous whatever its MET;
  - Training prefers the real type;
  - a stub-counting test: no added per-minute Java call.
- [ ] **Step 2: Build it.** Write the code to the spec's §§ 2–4.
- [ ] **Step 3: Mutation pass** on a scratch copy: the table off by ×2, the fallback removed, vigorous gated on MET, the wrapper not calling the original.
- [ ] **Step 4: Golden and gates.**
  - Re-record the golden under "Plan 11h Task 2: Fitness billed at the exercise's own MET". Attribute every moved leaf; if the golden has no Fitness player, say so and add none.
  - Run the § 3 gates and full pytest. Pin or re-anchor every moved pointer.

### Task 3: The refit check (Opus; lane M)
- [ ] Re-run the exercise-lag oracles, the server-path energy oracles (`test_replay_live_energy.py`), the x29/x35 replays and `tools/fit_deficit_drive.py` at HEAD.
- [ ] Report every oracle that moved and every one that left its band.
- [ ] Refit `EX_BYPASS_*` and the span only if a deficit oracle leaves its band. Otherwise re-pin the moved readings with a Task 3 note.
- [ ] Replays of rings recorded before this plan (x29, x35) replay at a recorded-build constants snapshot, as GUT_11G does.

### Task 4: The live run (Opus; live; one or two sessions)
- [ ] Build a new lib `x37_fitness_lib.py` and a driver: one set of each of the seven types, about 3–5 minutes of exercise each, at the shipping DayLength if the budget allows, otherwise DayLength 1.
- [ ] Read the wrapper's record through `lua.read`, the billed MET per minute through the ring, live against the replay, and the client's moodles with same-second pairs.
- [ ] Commit the lib, the driver and the grade before the boot. Stage the artifacts, never commit them. CLAUDE.md § 5 governs.

### Task 5: The record (Opus; docs lane, the 11g Task 9 process)
- [ ] Artifacts rows for the Task 4 run.
- [ ] Register rows:
  - the wrapper route (the three jar reads, as C rows);
  - the table;
  - the fallback;
  - the flag-first vigorous test;
  - the live readings.
- [ ] Rewrite every row that names the flat Fitness 6.0 (#2905, the C-17 rows, #3694 and others).
- [ ] A lessons rule: "never wrap `ISFitnessAction.new`", with its mechanism rows.
- [ ] Pages: `body-effects` and the activity pages.
- [ ] Mark C-2 built in research 04.
- [ ] Amend the 11b amendments.
- [ ] Run the whole-delta review, then the controller applies.

### Task 6: The close (controller; Opus whole-pass review)
- [ ] The whole-pass review, one fix wave and its re-review.
- [ ] The § 3 gates.
- [ ] Update CLAUDE.md and memory.
- [ ] Push.
- [ ] Report to Angus.

## Self-Review
- **Coverage.** Spec § 2 → Task 2 (and Task 4 live). § 3 → Tasks 1 and 2. § 4 → Task 2. § 5 → Tasks 2–4. § 6 → Task 2. § 7 → Tasks 4 and 5.
- **Placeholders.** None. The MET values are fixed by the spec, and the refit happens only on a named failure.
- **Names.** `K.energy.EXERCISE_MET`, `billClass` and `W.vigorous` are used consistently.
