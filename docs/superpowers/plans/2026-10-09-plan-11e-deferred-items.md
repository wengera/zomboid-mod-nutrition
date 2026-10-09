# Plan 11e: the deferred items, built now — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build everything Plan 11d deferred, since the mod is an unreleased complete revamp and nothing waits (Angus, 2026-10-09: "no reason to defer anything since we are looking to build a complete revamp and it hasnt been released yet"). That covers four pieces:
- monotony on repeated foods;
- nicotine-withdrawal hunger;
- the golden trace recording written hunger;
- the loose ends.

**Architecture:**
- **Monotony** is a per-player record of recent eats by food type, read once per eat. It produces the BOREDOM and UNHAPPINESS changes the eat delivers, and it never enters hunger (ruling 11d-9).
- **Nicotine withdrawal** is a hunger factor in the writer's composition. It reads the server-side NICOTINE_WITHDRAWAL stat and the time since the last smoke (#3630–#3637).
- **The golden trace** gains a stats stand-in, so the writer runs inside it and its written hunger is recorded.

**Tech Stack:**
- Lua 5.1 (Kahlua) mod code.
- Kernel tests in Python under `lupa` 2.8.
- The repository's register tools.

**Spec:**
- `docs/superpowers/specs/2026-10-09-satiety-revisit-memo.md`: C11 (monotony), C12 (nicotine) and § 5.
- `docs/superpowers/specs/2026-10-08-satiety-physiology-design.md` § 5d, rulings 11d-7 and 11d-9.
- The research reports under `docs/superpowers/research/2026-10-09-satiety-research-2/`: 26-player-states.md (nicotine) and 27-food-and-behaviour.md (monotony).

## Global Constraints
- **Repository rules.** CLAUDE.md governs: §§ 3, 5–7, and the § 6 rules added at the Plan 11d close.
- **No compatibility code.** The mod is unreleased: no migration, version mark or compatibility fallback. Change the record freely.
- **Rule 6.** No per-tick work. Monotony runs once per eat; the nicotine factor runs once per writer minute. Each task reports its lupa µs.
- **Constants.** A shipped constant names its S row, or is labelled "game choice, Plan 11e (ruling <n>)" with the rows it rests on.
- **The golden.**
  - It stands at `2d3b6fdb88e115d4e87716a7a7f163cb1914e24466a9a7ef7d51cd22e06986fe`.
  - A task that moves it re-records it in its own commit, under a named cause, with every leaf attributed.
- **Pointers.** A task that changes a line a register claim quotes pins that pointer to the last commit holding the line. Task 4 rewrites it. Implementers never edit the register; they list findings.
- **Oracles.** Every new assertion passes a mutation pass on a scratch copy (`git -c core.autocrlf=false archive HEAD | tar -x -C <scratch>`).
- **Lane.** Tasks 1–3 run serially in lane M; Task 4 runs in the docs lane after them.
- **Commits and git.**
  - Pathspec commits; implementers never push.
  - Never run stash, `checkout --`, reset, restore, `add -N`, `add -f`, or any index-wide command.
  - Never set GIT_*.
- **Baseline.** Kernel 2552, pytest 3340.

## The rulings this plan carries (the controller ledgers them at Task 0)
- **11e-1 (monotony).**
  - Each eat of a food type already eaten in the past 7 game days adds a BOREDOM and UNHAPPINESS change. The change grows with the count of recent eats of that type, and decays as the type goes uneaten.
  - The direction follows S1592–S1595 and S1597. S1596 shows that context (field rations) drives the intake fall more than the food itself, which is why monotony goes into mood, not intake.
  - The slope and the window are game choices.
  - Staple foods (bread, rice, potato, pasta, oats; S1593 and S1594, where free choice and staples resist) take a reduced slope. Their list is a game choice, read from the food data's categories.
  - Nothing reads it into hunger.
- **11e-2 (nicotine).**
  - The written hunger takes a factor 1 + NIC_MAX × w, where:
    - w is NICOTINE_WITHDRAWAL / 0.51 (the stat's cap, #3633);
    - the factor fades with the days since the last smoke, gone by 26 weeks (S1577);
    - NIC_MAX is anchored on S1576's +227 kcal/d, about 0.11 of a 2,000 kcal day.
  - Only a character with the Smoker trait (or one who ever had it) can carry withdrawal (#3630).
  - S1576 is one experiment with 13 women, so the size is low certainty and is labelled as such.
- **11e-3 (golden).** The golden scenario gains a `getStats` stand-in, so `W.step` writes and the trace records the written HUNGER, THIRST and FATIGUE. The named change is "the golden records the written stats".
- **11e-4 (loose ends).**
  - #3422's sentence and row are rewritten to the current record and the slot-file store.
  - The six-against-three reading at es live (0.970 per the Task 4 review) is re-run and pinned in the oracle, or corrected.
  - S1335 stays an open evidence gap with no time constant. It is not a deferral, and its page line says so.

---

### Task 0: The workspace and the rulings (controller)
- [ ] Create `.superpowers/sdd/2026-10-09-plan-11e-deferred-items/progress.md`. Ledger the baseline (golden sha, kernel 2552, pytest 3340) and rulings 11e-1 to 11e-4.
- [ ] Write `task-1-amendments.md`, then dispatch Task 1.

### Task 1: The golden records the written stats (ruling 11e-3) — Opus, lane M
**Files:**
- `testing/tests/kernel/golden_trace.py`, the scenario's environment stand-ins
- `testing/tests/kernel/test_golden_trace.py`
- `testing/tests/kernel/golden/trace-1.0.0.json`, re-recorded

**Interfaces:**
- Produces: the golden snapshot carries `records/<user>/written/{HUNGER,THIRST,FATIGUE}` per snapshot, or the trace's equivalent stats leaf.
- [ ] **Step 1.** Read `golden_trace.py`: why the writer never writes ("getStats stays absent"). Add a stats stand-in object per player, as test_writer_shape.py's player stand-in does, so `W.step` runs its full composition, and record the written values at each snapshot.
- [ ] **Step 2.** Run the golden test; it fails, because the trace changed.
- [ ] **Step 3.** Re-record under "the golden records the written stats (Plan 11e Task 1, ruling 11e-3)". Walk the leaves:
  - the new written-stat leaves are added;
  - any existing leaf that moves must be attributed (the writer now running may mark pushes);
  - an unexplained leaf is a stop.
- [ ] **Step 4.** Mutation pass on a scratch copy. Each of these must now fail the golden:
  - `sleepFactor` unwired;
  - the circadian factor dropped;
  - `W.satietyF` replaced by the stamp;
  - DEFICIT_FLOOR at 0.15.
- [ ] **Step 5.** Run the gates and commit: "Golden: records the written stats (Plan 11e Task 1, ruling 11e-3)".

### Task 2: Nicotine-withdrawal hunger (ruling 11e-2) — Opus, lane M
**Files:**
- `NR_Kernel_Satiety.lua`: append `NIC_MAX`, `NIC_FADE_DAYS` and `K.satiety.nicotineFactor(withdrawal, daysSinceSmoke)`
- `NR_Server_Writer.lua`: the composition, through `W.satietyFactor`, and the seed inverse
- `test_kernel_satiety_physiology.py`
- `test_writer_shape.py`
- `test_satiety_meal_studies.py`: an S1576 replay

**Interfaces:**
- Produces: `K.satiety.nicotineFactor(w, d) -> number >= 1`.
  - It is 1 for non-finite or non-positive inputs.
  - Otherwise it is `1 + NIC_MAX × clamp(w / 0.51, 0, 1) × fade(d)`, where `fade` is 1 at d = 0 and 0 at `NIC_FADE_DAYS` = 182.
- [ ] **Step 1.** Read how the server reads NICOTINE_WITHDRAWAL and `getTimeSinceLastSmoke` (#3630–#3637; NR's stat-reading seam in the writer). If the time since the last smoke is not readable server-side, fade on the stat alone, and say so.
- [ ] **Step 2: Failing tests.**
  - The factor's shape: 1 at w = 0, `1 + NIC_MAX` at the cap with d = 0, halfway along the fade, and 1 at d ≥ 182.
  - The writer: hunger is multiplied by the factor, the seed divides by it, and a non-number stat reads 1.
  - The replay: a quitting smoker's next-day intake ratio under the 11c-31 mapping is 1 + NIC_MAX, within the band of S1576's 227 kcal on an assumed 2,000 kcal day (1.08–1.14).
- [ ] **Step 3.** Implement. Fit `NIC_MAX` to S1576 (about 0.11). Label both constants with ruling 11e-2 and rows S1576 and S1577, and name the low certainty (one experiment, n = 13).
- [ ] **Step 4.** Run the tests and the kernel suite. Re-record the golden if it moves: "the nicotine factor wired (Plan 11e Task 2, ruling 11e-2)". The golden's stand-ins carry no smoker, so it should not move; say so either way.
- [ ] **Step 5.** Mutation pass:
  - NIC_MAX ×2 and ×0.5;
  - the fade removed;
  - the factor unwired from the seed.
- [ ] **Step 6.** Append to LIMITATION_FOUR (its count rule kept): "nicotine withdrawal raises hunger by a factor anchored on one small trial, fading over 26 weeks". Run the gates and commit.

### Task 3: Monotony at the eat (ruling 11e-1) — Opus, lane M
**Files:**
- New kernel `NR_Kernel_Monotony.lua`, or appended to an existing kernel if the implementer finds a better home and says why. It holds `K.monotony.new()`, `K.monotony.record(m, typeKey, ageH)`, `K.monotony.delta(m, typeKey, ageH, staple) -> boredom, unhappy` and `K.monotony.prune(m, ageH)`.
- The intake (`NR_Server_Intake.lua`), where the eat lands and the delta is applied.
- The store's INPUTS (`record.monotony`).
- The heal and guard lists.
- Tests: a new `test_kernel_monotony.py`, plus the intake and store shape tests.

**Interfaces:**
- Produces: `record.monotony = { t = { [typeKey] = { n = <count>, last = <ageH> } } }`, pruned beyond 7 game days.
- [ ] **Step 1: Read first.**
  - How vanilla applies a food's boredom and unhappiness at an eat on 42.21: #0041–#0043, the eating pipeline page, and `IsoGameCharacter.Eat`'s stat writes.
  - Whether the server can add to BOREDOM and UNHAPPINESS at an eat, and how the mod's effects floors (Plan 5) write UNHAPPINESS without fighting them.
  - Choose the seam:
    - an add at the eat on the server (the ItemStatsPacket path, or a direct stats add after vanilla's own);
    - or a pending delta the writer applies on its next minute.
  - Cite each mechanism you rely on by its row or by a jar read. CLAUDE.md § 6 forbids asserting an engine mechanism without one.
- [ ] **Step 2: Design the delta.**
  - BOREDOM and UNHAPPINESS each rise by `MONO_SLOPE × max(0, n − 1)` per eat, capped at `MONO_CAP`, where n counts recent eats of the type decayed with a 3-day half-life inside the 7-day window.
  - Staples take `MONO_STAPLE` × the slope. The staple list comes from the food data's categories, named in the code.
  - Anchor the sizes on vanilla's own per-item scale (#0042: stale +10, rotten +20). The fifth eat of one type in a week should feel like a stale item, about +10. These are game choices that rest on S1592–S1595 and S1597 for direction.
  - The typeKey is the item's full type. Note in the comment that S1594 found free choice resists monotony; the player choosing variety is the mechanic.
- [ ] **Step 3: Failing tests.**
  - The kernel's shape: the first eat gives 0; repeats grow; the delta decays after days uneaten; staples are reduced; the cap holds; pruning works.
  - The intake applies the delta exactly once per eat, including a partial eat (scaled by fraction).
  - It never touches HUNGER.
  - The store round-trips the record.
  - The heal handles a corrupt `monotony` table by resetting it.
- [ ] **Step 4.** Implement, then run the tests and the kernel suite. Re-record the golden if the scenario's eats move a leaf: "monotony at the eat (Plan 11e Task 3, ruling 11e-1)".
- [ ] **Step 5.** Mutation pass:
  - the slope ×2 and ×0.5;
  - the decay removed;
  - the staple reduction removed;
  - the delta applied to HUNGER.
- [ ] **Step 6.** Cost: µs per eat, and the record size per player (a pruned table). Run the gates and commit.

### Task 4: The register, pages and loose ends (ruling 11e-4) — Opus, docs lane, after Tasks 1–3
- [ ] **Rows and sentences for Tasks 1–3.**
  - The golden's written stats go on testing-your-mod, wherever the golden is described.
  - The nicotine factor goes on body-effects#hunger-from-satiety.
  - Monotony goes on body-effects, or on the ui-and-moodles mood section; name the owner.
  - Each is a C/inference row whose worked example is the mod's own line (T12-1), with its S rows in the bound.
- [ ] **#3422.** A status row rewrites the claim and its server-lifecycle.md:115 sentence to the current record (with `trail`) and the slot files. Re-measure the record size from the golden trace's records, and keep every number at its pointer's path.
- [ ] **The six-vs-three reading.** Re-run it with es live in the oracle, pin it in a test (Task 4 may append a test; this is the one test edit a docs task makes, and it says so), and correct #3641 if the pinned value differs.
- [ ] **Pinned pointers.** Rewrite every pointer that Tasks 1–3 pinned.
- [ ] **S1335.** Its page line on body-effects (the exercise lag's bound) names it as an open evidence gap: no study gives the time constant.
- [ ] **Checks and mint.**
  - Dry-run the delta.
  - Run page_lint.
  - Run the staged checker with the allowance, and a full-checker simulation of the mint; both must read 0.
  - The controller mints after the review.

### Task 5: The close (controller; Opus reviews)
- [ ] Run one whole-pass Opus review, then one fix wave and its re-review.
- [ ] Run the § 3 gates, each in its own call.
- [ ] Update CLAUDE.md § 3's count and the memory files, and add the 11b amendments: a live read of monotony's mood deltas and of nicotine hunger on a Smoker.
- [ ] Push.

---

## Self-Review
1. **Coverage.** Every deferral named at the Plan 11d close is covered:
   - monotony (11d-9): Task 3;
   - nicotine (C12; the jar read is done): Task 2;
   - the golden's blindness: Task 1;
   - #3422: Task 4;
   - the 0.970 re-run: Task 4;
   - S1335: Task 4.

   The evidence-neutral items (illness, nausea, heat, sugary drinks, ketosis, the aperitif, aerated volume, eating rate) are not deferrals. They stay neutral under the measured-or-neutral rule, and the controller's report to Angus says so.
2. **Placeholders.** The fitted values (NIC_MAX, MONO_SLOPE, MONO_CAP, MONO_STAPLE) come from fits or anchors the tasks name.
3. **Consistency.** `K.satiety.nicotineFactor` and `K.monotony.*` are named once. `W.satietyFactor` is the writer's existing factor helper, which Task 2 extends.
