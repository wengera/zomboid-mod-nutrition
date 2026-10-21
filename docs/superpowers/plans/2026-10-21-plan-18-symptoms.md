# Plan 18: symptoms through vanilla's moodles — implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** While a lethal cause runs, punish the living character through vanilla's own Endurance, Pain, Stress and Unhappy moodles. Each scales with the cause's progress toward death, with no new moodles.

**Architecture:**
- A per-cause symptom table in the effects data reads each cause's progress `p_i = 1 − D.frac[code]` from the drain kernel.
- The composer folds the rows: endurance takes the lowest cap, pain sums per body part under a cap, and the stress and unhappiness floors take the highest.
- The server adapters write each minute:
  - added pain per body part;
  - the ENDURANCE cap through the existing writer;
  - the floors through the existing ops.

**Tech stack:** Kahlua kernels with lupa tests, the server Lua adapters, the live harness (`testing/pzt`, `xlib.py`), and the guide generator.

**Spec:** `docs/superpowers/specs/2026-10-21-symptoms-design.md`. Read it in full before any task.

## Global Constraints

- CLAUDE.md §§ 3–6 bind every task: the gates, register deltas, live rules, pathspec commits, and no index-wide git.
- The full pytest runs before any register apply that supersedes a row the guide cites (CLAUDE.md § 6).
- A driver refuses unknown arguments.
- The clock is `p_i = 1 − D.frac[code]` for codes 1–7, so it follows `NR.DeathPace` and eases during R2 recovery.
- **Pain** applies only while a cause is active (its ceiling falling; `D.mask`), not while it is merely recovering (`D.recovering`).
- **Overlap:** endurance takes the minimum cap; pain sums per body part under a cap; stress and unhappiness take the maximum floor.
- **Severity** scales the symptom magnitudes; the health lines stay unscaled.
- **Overlay mode:** no starvation or dehydration symptoms.
- **Rule 6:**
  - no per-tick work;
  - zero added cost with no cause active;
  - a bench and a Java-call count before and after.
- The magnitudes are game choices set from Task 1's live readings, and every one is named in the kernel with its register row.

---

### Task 1: The live probe of the levers

**Files:**
- Create: an experiment mod under `testing/experiments/TKX_Symptoms/` if no harness command reaches `BodyPart.setAdditionalPain` or the endurance cap. The harness has `lua.call` with up to four scalar arguments. Prefer a tiny server-side test function in the experiment mod, called by `lua.call`.
- Create: `testing/experiments/x49_lib.py` (from `x48b_lib.py`, importing `xlib.py`) and `x491_levers.py`.
- Create: profile `testing/profiles/x49-levers.toml` on fixture `default`, with sleep on (so the fatigue rows are also observable) and `Nutrition = false`.
- Create: offline tests.

**Readings.** Each is graded with a falsifier and an offline failing case.
- **P1:** a server-set added pain of a stated value on the lower torso shows the client's Pain moodle at the level vanilla's thresholds predict. Read the jar's moodle thresholds first, as CLAUDE.md § 5 requires.
- **P2:** the decay between minutes when re-set each minute: its size per game minute and per day length.
- **P3:** the added pain after a relog, and after a server restart, with the value saved or lost.
- **P4:** an ENDURANCE cap at each of several values shows the Endurance moodle level on the client, and endurance's climb between the minute writes.
- **P5:** stress and unhappiness floors at stated values show their moodle levels.

Each part is one session of under 10 minutes; split them as needed. Every CLAUDE.md § 5 rule applies. Drivers are committed and STOP for the controller's review before the first boot. Artifacts go in with their rows; the owner-sentence candidates are a delta file.

---

### Task 2: The symptom kernel

**Files:**
- Modify: `mod/NutritionRevamp/common/media/lua/shared/NR_Data_Effects.lua`, adding the per-cause symptom rows.
- Modify: the composer (`NR_Kernel_Effects*` or wherever the effects composer lives; grep `K.effects`), adding the progress clock, the shapes (`flat`, `linear`, `knots`) and the overlap folds.
- Test: `testing/tests/kernel/test_symptoms.py`.

**Interfaces:**
- **Produces:**
  - the composer outputs `E.enduranceCap` (the minimum over the Overfull row and the causes);
  - `E.pain[partIndex]`, the summed and capped added pain per body part, 0 when none;
  - `E.stressFloor` and `E.unhappyFloor` (the maximum);
  - a flag for whether any pain is active.
- **Consumes:**
  - `record.drain.frac`, `mask` and `recovering` (Plan 17);
  - the Severity dial;
  - the Overlay flag.

**Steps:**
- [ ] **Step 1:** Write the failing tests:
  - the clock reads `1 − frac`;
  - each shape at `p` 0, 0.5 and 1;
  - pain only when the code's bit is in `mask`;
  - the overlap folds;
  - Severity scaling;
  - Overlay drops codes 1 and 6;
  - recovery eases the endurance cap and the floors with `p`;
  - no table allocation per step.
- [ ] **Step 2:** Implement with the magnitudes from Task 1's readings, each a named constant with a "game choice" comment and, where a reading backs it, its run id.
- [ ] **Step 3:** Run the gates and the full pytest. Re-record the golden in its own commit under "Plan 18: symptoms through vanilla's moodles".

---

### Task 3: The adapters and Rule 6

**Files:**
- Modify: `NR_Server_Effects.lua` and/or `NR_Server_Writer.lua`:
  - the added pain per body part, re-set each minute while the target is above 0 and left to decay once it is 0;
  - the ENDURANCE cap extended to `E.enduranceCap` (the Overfull clamp generalised; read Plan 15 Task 8's code);
  - the floors through the existing ops.
- Modify: `tools/replay_live.py` to carry the pain targets and the endurance cap in its rows.
- Test: the adapter tests (the stub records Java calls), and an extension of `tools/bench_drain.py`.

**Steps:**
- [ ] **Step 1:** Failing tests:
  - the pain writer is called once per painful part a minute and never with no cause;
  - the endurance cap path is unchanged when only Overfull applies;
  - the Java-call count is +0 with no cause active.
- [ ] **Step 2:** Implement.
- [ ] **Step 3:** Run the gates, the bench, the Java-call count and the full pytest.

---

### Task 4: Live acceptance

A Realistic fast with water on fixture `default`. Seed the starvation onset as in x484, plus a deficiency at clinical as in x481. Grades:
- the Pain moodle on the client while starvation is active, with the lower torso's added pain matching the replay;
- the Endurance moodle at the level the cap predicts at the run's progress, in server and client reads;
- the stress and unhappiness floors at their predicted moodles;
- after a lapse (a snack), the pain decays and the endurance cap eases with recovery;
- each graded against the HEAD replay of the run's own inputs.

Drivers are reviewed before the boot, followed by a live review and the delta.

---

### Task 5: The guide

- Each cause's guide section and the fast chart's notes name the symptoms (Exertion, Pain, Stress, Unhappy) and when they appear.
- An S2d note or tab shows the endurance cap and pain over the default fast, if it reads well.
- The limitations: the flat pain is a placeholder for researched shapes; the body parts are game choices.
- The guide tests and a render check.

---

### Task 6: The register and pages

- Rows for:
  - the symptom table and its folds;
  - the pain and endurance mechanisms, with Task 1's readings;
  - the live acceptance;
  - the game-choice magnitudes.
- Open rows for the research plan: hunger-pang time course, deeper aches, sleep disturbance, the deficiency prodromes, and per-symptom onsets.
- Supersede any row Plan 18 changes, such as the Overfull-only endurance clamp.
- The body-effects owner sentences.
- A trial apply in which the guide tests pass.

---

### Task 7: Re-stage and the smoke boot

Re-stage from mod/'s head, then one smoke boot (x485's design): options, join, no mod error, and the client shows the Pain moodle when a seeded starvation is active.

---

### Task 8: Close

- The whole-pass review, one consolidated fix wave, and its re-review.
- README, CHANGELOG and COMPATIBILITY.
- The gates and the CLAUDE.md baseline.
- The memory files.
- Push, and ask Angus about the guide republish.
