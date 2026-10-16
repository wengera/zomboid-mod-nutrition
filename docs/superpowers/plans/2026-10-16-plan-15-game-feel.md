# Plan 15: game feel — implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task by task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Intertwine Nutrition Revamp with the game. Subjective things (pacing, magnitudes, presentation) move toward vanilla; objective things stay science-supported. Health drains become damage to a floor that reaches 0 only at each state's real death point.

**Architecture:** The study-fitted kernels stay the model of record. New layers sit between the model and the game:
- a calibrated hunger writer;
- a drain-and-floor engine;
- cap lifting, with vanilla's level-4 drain suppressed and its other drains re-applied;
- the food-timer bridge for Well Fed and the eating block.

The water base and the stomach's satiety mass are re-based on the new science rows. The moodles and panel are pruned and extended. Coffee and beer get game sizes, with a realism option.

**Tech stack:**
- Kahlua Lua, in mod/NutritionRevamp/common/media/lua: shared kernels, server, client;
- Python tools and pytest with the lupa 2.8 kernel host;
- the harness, testing/pzt with PZTestKit and the testing/experiments drivers on xlib.py;
- the jar toolchain at C:\Users\Angus\pz-b42.

**Spec:** docs/superpowers/specs/2026-10-16-game-feel-design.md. Its sources are the decision log at .superpowers/sdd/game-feel-review/decisions.md, the research in docs/superpowers/research/2026-10-16-game-feel/ (science rows S2209–S2262), and the game-code checks in .superpowers/sdd/game-feel-research/jar-checks.md with their draft delta jar-checks-delta.tsv.

## Global constraints
1. **The tuning rule (spec § 1).**
   - Subjective follows vanilla: pacing, effect sizes, when a crisis lands, presentation.
   - Objective follows science: which effects happen, their order, triggers, and real energy and water needs.
   - Every game choice is labelled in its code comment ("game choice") and named in spec § 10.
2. **Health drains signal damage, not lethality.**
   - A state drains to a floor that deepens on science's clock and reaches 0 only at its death point.
   - There is no toggle, so `NR.DeficienciesCanKill` is removed. The mod is unreleased, so there is no migration (CLAUDE.md § 6).
3. **Floors stay above 10 health until a state's final stage.** At 10 or below, vanilla wakes any sleeper every tick (jar-checks Check 2).
4. **Science values cite their S-rows.** The new rows are S2209–S2262, and every number a task ships rests on a settled row or is labelled a game choice. Use these values verbatim:
   - β = 0.05;
   - basal water = `2000 + 32 × (lm − 52.02)` g a day;
   - starvation death at BMI 12;
   - dehydration death at a 17 % body-water deficit;
   - beriberi death about 5 weeks after clinical onset.
5. **Rule 6: no noticeable hitching at 60 players.**
   - No per-tick work, except where a measurement shows it is needed.
   - Bench any per-minute change before and after, with the Java call-count stub (CLAUDE.md § 6).
6. **The golden trace** re-records only under named causes, in the commit that moves it. The study oracles read the model's pre-curve hunger, h_model.
7. **CLAUDE.md §§ 3–6 apply in full:**
   - the gates;
   - the register process and its deltas;
   - the live rules (one session at a time, the 12 GB memory gate, foreground waits, drivers frozen after their run, the staged copy);
   - SDD process with the models named;
   - pathspec commits;
   - refactoring as the work goes.

## File structure
| File | Responsibility | Tasks |
|---|---|---|
| `shared/NR_Kernel_Fluids.lua` | the basal water base by lean mass, and the thirst traits on basal | 3 |
| `shared/NR_Kernel_Drain.lua` (new) | the drain-and-floor engine: per-state floor curves, the death points, the drain rate per game day | 4 |
| `shared/NR_Kernel_Effects.lua`, `shared/NR_Data_Effects.lua` | lethal-state conditions moved to the drain engine; the starvation and dehydration effect order; the panic band; `DRAIN_RATE` retired into NR_Kernel_Drain | 4 |
| `server/NR_Server_Effects.lua`, `server/NR_Server_Writer.lua` | applying drains through `ReduceGeneralHealth`; suppressing regeneration and the food heal; lifting the caps; vanilla's level-4 constant and the re-applied drains | 4, 5 |
| `shared/NR_Kernel_Hybrid.lua` | the caps (they become conditional) and the calibrated hunger curve | 5, 6 |
| `shared/NR_Kernel_Satiety.lua`, `shared/NR_Kernel_Stomach.lua` | the satiety mass with β × the volume excess | 7 |
| `tools/food_nutrients.py`, `data/food-nutrient-map/`, the generated `NR_Data_Nutrients.lua` | the `ml_per_g` column from USDA portions | 7 |
| `server/NR_Server_Writer.lua` (food-timer bridge) | `setHealthFromFoodTimer` from fullness; `setHealthFromFood` handling; the Overfull effects | 8 |
| `shared/NR_Kernel_View.lua`, `client/NR_Client_Moodles.lua`, `client/NR_Client_Panel.lua`, `client/NR_Client_Tooltip.lua`, `server/NR_Server_Options.lua`, the sandbox and translation files | the moodles removed or filtered, the dead zones, the hide option, the panel lines, the tooltip line | 9 |
| `shared/NR_Kernel_Acute.lua` | caffeine and alcohol game sizes, and the realism option | 10 |
| `testing/experiments/x45_*`, `testing/profiles/x45-*` | the live sessions | 2, 11 |
| `docs/`, `tools/mod_guide_series.py`, `docs/mod-guide/` | the registers, pages and guide | 1, 12, 13 |

---

### Task 1: Mint the game-code findings (Opus; docs lane)
**Files:** `docs/reference/claims.tsv` (via a delta), with owner sentences on `docs/facts/eating-pipeline.md`, `docs/facts/character-stats.md` and `docs/facts/body-and-weight.md`.

- [ ] **Step 1:** Rename `.superpowers/sdd/game-feel-research/jar-checks-delta.tsv`'s J1.1–J2.3 to T1.n (claims_delta accepts only T ids). Give each row an owner on the facts page its subject belongs to, and write that owner sentence with its tag.
- [ ] **Step 2:** Re-anchor the 42.20.4 line pointers the checks found stale: #0516 to L2358–L2360, and #0522 to `ISInventoryPane.lua:990/993`. These go in as status rows with byte-identical bound prefixes.
- [ ] **Step 3:** Trial-apply on a `git archive` copy with the repository's objects as alternates, then run the full `claims_check`, and `page_lint` on each touched page.
- [ ] **Step 4:** Whole-delta review (Opus), then a fix round, then the controller's apply, `--fix-tags` and a commit.

### Task 2: Live spike on vanilla's level-4 drain constant (Opus; live)
**Files:** a new `testing/experiments/x451_capspike.py` (starting from `x44_guide_lib.py`), `testing/profiles/x45-mod.toml` (booting the staged copy), and `testing/artifacts/x451-*`.

**Interfaces:**
- Produces: the measured behaviour of option B before Task 5 builds it.
  - **The constant:** its exact name and route, as jar-checks Check 3 names it, and whether `lua.setpath` or a new harness command can set it from server Lua.
  - **The drains it carries:** with the constant at 0, which of sickness, bleeding, heavy load and under 35 kg stop.
  - **Persistence:** whether the value survives a reload.

- [ ] **Step 1:** Read jar-checks.md Check 3. Write the driver with offline grades and failing cases (CLAUDE.md § 5):
  - set HUNGER to 0.8 with the constant at 0, and read that health holds with no starvation drain;
  - then apply a bleed (or a sickness) and read that health still falls;
  - restore the constant and read that the starvation drain returns;
  - reload and read the constant again.
- [ ] **Step 2:** If a harness command is needed, add it in its own commit first (CLAUDE.md § 5).
- [ ] **Step 3:** Run the session. Commit the artifact with its row, guide and do-not-cite keys. Report the findings Task 5 builds on.

### Task 3: The water base and the thirst traits (Opus; mod lane)
**Files:** `shared/NR_Kernel_Fluids.lua` (`K.fluids.AI`, the basal loss), `server/NR_Server_Nutrients.lua` or the fluids caller (traits and StatsDecrease), and the tests in `testing/tests/kernel/`.

**Interfaces:**
- Produces: `K.fluids.basalG(lm, traitScale)`, returning g a day as `(2000 + 32 × (lm − 52.02)) × traitScale`.
  - `traitScale` is 1.5 for High Thirst, 0.5 for Low Thirst and 1 otherwise, times the StatsDecrease factor.
  - It is sex-neutral and replaces `K.fluids.AI` everywhere it is read.

- [ ] **Step 1:** Failing tests:
  - the default body (lm 52.02) gives 2000;
  - lm 40 gives 1615.36 (2000 + 32 × −12.02);
  - High Thirst gives ×1.5;
  - with sweat on top, basal is unchanged;
  - no sex index is read.
- [ ] **Step 2:** Implement it, citing S2216–S2230 and the game choice of the 52.02 anchor.
- [ ] **Step 3:** Re-point the thirst oracles. Moved study pins are re-pinned with their misses stated, never silently.
- [ ] **Step 4:** Re-record the golden under "Plan 15 Task 3: the water base by lean mass (S2216–S2230)". Run the bench before and after.
- [ ] **Step 5:** Run the gates and the full pytest, then commit.

### Task 4: The drain-and-floor engine (Opus; mod lane)
**Files:**
- create `shared/NR_Kernel_Drain.lua`;
- modify `shared/NR_Kernel_Effects.lua`, `shared/NR_Data_Effects.lua` and `server/NR_Server_Effects.lua`;
- remove `NR.DeficienciesCanKill` from `server/NR_Server_Options.lua`, the sandbox options and the translations.

**Interfaces:**
- Produces:
  - `K.drain.states` — per state, {onset test, first floor, death point, floor curve};
  - `K.drain.floor(state, tSinceOnsetH, body)` — the floor health, monotonically falling, > 10 until the final stage;
  - `K.drain.rate(state)` — health per game day;
  - `K.drain.step(record, dtM)` — returns {active, targetFloor, drainThisMinute}.

**The states:**
- **Starvation:** onset is true starvation, as the PE grade the mod already tracks defines it. The first floor is 50 at about 2.5–4 days. The death point is BMI 12 from `body.lm + body.fm` and height.
- **Dehydration:** the first floor is 50 at about 35 h; the death point is a 17 % deficit.
- **Wet beriberi:** the death point is 5 weeks after clinical onset.
- **Scurvy and pellagra:** the death points are game choices of months; name the values.
- **Sodium and iron:** their existing conditions are kept.

- [ ] **Step 1:** Failing tests, per state:
  - the floor schedule;
  - the floor stays above 10 until the final stage;
  - it reaches 0 exactly at the death point;
  - the BMI death point moves with body fat, so a heavier body lasts longer;
  - removing `DeficienciesCanKill` leaves no reader.
- [ ] **Step 2:** Implement the engine.
  - Move the lethal codes from `K.effects.DRAIN_RATE` and `effects.lethal` into it.
  - The effect order follows spec § 3.3: the starvation phases, and dehydration at 2, 3–4, 4–6 and 10 %. Panic moves from 1.5 % to the 4–6 % band.
  - Cite each row.
- [ ] **Step 3: The server.**
  - Apply the drain through `ReduceGeneralHealth` once a minute, never below the floor.
  - While any state is active: zero regeneration and `setHealthFromFood(0)` (jar-checks Check 2).
  - Keep the per-minute cost under the Rule 6 bench.
- [ ] **Step 4:** Re-record the golden under its named cause, with the leaves attributed. Run the gates and the full pytest, then commit.

### Task 5: Lifting the caps under option B (Opus; mod lane)
**Files:** `shared/NR_Kernel_Hybrid.lua` (`hungerCap`, `thirstCap` and `KILL_CAP` become conditional) and `server/NR_Server_Writer.lua` (the constant and the re-applied drains).

**Interfaces:**
- Consumes: Task 2's measured constant route, and Task 4's `K.drain.step`.
- Produces: `K.hybrid.caps(state)`.
  - Hunger is capped at 0.69 unless starvation is active, when it may rise to 1.
  - Thirst is capped at 0.83 unless Parched (the 6 % deficit band), when it may rise to 1.
  - The writer sets vanilla's drain constant to 0 while HUNGER or THIRST is at level 4, re-applies the constant's other drains (sickness, bleeding, heavy load, under 35 kg) at vanilla's rates, and re-writes it after a load.

- [ ] **Step 1:** Failing tests: the caps by state; the constant written to 0 only at level 4; the re-applied drains equal vanilla's rates from their claims.
- [ ] **Step 2:** Implement, then bench.
- [ ] **Step 3:** Re-record the golden. Run the gates and the full pytest, then commit.

### Task 6: The calibrated hunger writer (Opus; mod lane)
**Files:** `shared/NR_Kernel_Hybrid.lua` (or a new `NR_Kernel_HungerCurve.lua`), the writer, and the oracles in `testing/tests/kernel/*_oracles.py`.

**Interfaces:**
- Produces: `K.hungerCurve.write(h_model, state)` → H.
  - A monotone piecewise-linear curve, with knots as labelled game choices.
  - A satisfying meal (about 667 kcal, a third of 2,000) reads H ≈ 0.
  - Peckish (H > 0.15) comes at about 4 h after it, and Hungry (H > 0.25) at 6–8 h.
  - A meal of 200 kcal or less moves H less than a meal.
  - Above the fasting plateau, H hands over to Task 5's starvation lift.
  - A dead zone of 0.02 sits at each threshold.
  - The circadian dip applies only when fed.
  - The model's own value stays readable for the oracles.

- [ ] **Step 1:** Fit the knots on the replay (tools/replay_live.py ServerReplay) against vanilla's cadence. Use the vanilla model, tools/vanilla_model.py, as the target for the three-meal day, with a stability check (CLAUDE.md § 6, fits).
- [ ] **Step 2:** Failing tests: the cadence, the snack, a fast never falls, the dead zone, and the oracles still reading h_model.
- [ ] **Step 3:** Implement, then bench. Re-record the golden. Run the gates and the full pytest, then commit.

### Task 7: Fullness by weight and volume (Opus; data and mod lanes)
**Files:** `tools/food_nutrients.py`, `data/food-nutrient-map/`, the generated `NR_Data_Nutrients.lua`, and `shared/NR_Kernel_Satiety.lua` / `NR_Kernel_Stomach.lua`.

**Interfaces:**
- Produces:
  - `ml_per_g` per food, from the USDA SR Legacy portions (S2212), following the parse rules in volume-report.md § 4. Items with no measure take 1.0.
  - The satiety mass becomes `massOf(buffer) + K.satiety.BETA × volumeExcess + LIQUID_WEIGHT × liquid`, where `volumeExcess = Σ(ml_per_g − 1) × solid grams` and `BETA` is 0.05.

- [ ] **Step 1:** Data. Extend the tool and the mapping. `--check` must be in sync, and a test covers the parse pitfalls:
  - fl oz;
  - crumbs against cubes;
  - the cooked id for WaterPot items.
- [ ] **Step 2:** Failing tests: the volume-report worked examples as the mod's foods give them (bread, popcorn, raw broccoli at β 0.05); water unchanged.
- [ ] **Step 3:** Implement. Re-run the satiety oracles and report any that move; β is small, so the moves should be small. Re-record the golden. Run the gates and the full pytest, then commit.

### Task 8: The food-timer bridge and the Overfull effects (Opus; mod lane)
**Files:** `server/NR_Server_Writer.lua` (or a new `NR_Server_FoodTimer.lua`), `shared/NR_Data_Effects.lua` (the Overfull rows) and `shared/NR_Kernel_View.lua` (the fullness level).

**Interfaces:**
- Produces: each minute, `setHealthFromFoodTimer(t)`.
  - t is in 1–3200 while sated; that is Well Fed.
  - t is above 3200 at Overfull 4, which triggers vanilla's eating refusal.
  - t is 0 otherwise.
- Also each minute, `setHealthFromFood(x)`. While a Task 4 drain is active it is 0; otherwise it is a gentle heal, a labelled game choice.
- The bridge re-writes both after a load.
- The Overfull effects:
  - level 3: a movement and endurance penalty of vanilla size;
  - level 4: nausea, a FOOD_SICKNESS rung. Design a vomit chance or leave it out, and say which in the report.

- [ ] **Step 1:** Failing tests: the timer mapping, the drain gate on the heal, and the reload.
- [ ] **Step 2:** Implement, then bench. Re-record the golden. Run the gates and the full pytest, then commit.

### Task 9: Moodles, panel and tooltip (Opus; mod lane, client)
**Files:** `shared/NR_Kernel_View.lua`, `client/NR_Client_Moodles.lua`, `client/NR_Client_Panel.lua`, `client/NR_Client_Tooltip.lua`, `server/NR_Server_Options.lua`, the sandbox and translation JSON, and the icons.

- [ ] **Step 1: Remove** the Energy and Hydration moodles: their view keys, icons, translations and options text. The internal energy state stays.
- [ ] **Step 2: The Deficiency moodle** reads only nutrients whose grade drives an effect, read from `NR_Data_Effects`, with a test keeping its list in step with the effects.
- [ ] **Step 3: The monotony mood-floor dead zone** of 0.02 of its threshold, and a new client option hiding level 1 of Stimulant, Sleep and Excess.
- [ ] **Step 4: Panel lines:**
  - the active drain state ("weakened by starvation" and the like);
  - a weight trend from a 7-day mass slope: "losing", "steady" or "gaining", with a labelled threshold;
  - dehydration %.
- [ ] **Step 5: The tooltip** replaces vanilla's hunger line with "fills you for about N h" (from h_model's replay of the item alone, precomputed per item type, not per frame) and the kcal.
- [ ] **Step 6:** Run the gates (mod_lint, release_pack, kahlua and hotpath lints), the full pytest and the client tests, then commit.

### Task 10: Coffee, beer and the realism option (Opus; mod lane)
**Files:** `shared/NR_Kernel_Acute.lua`, `server/NR_Server_Options.lua`, the sandbox files and the translations.

**Interfaces:**
- Produces: `NR.StimulantRealism` (Game, the default, or Realistic).
- **Game sizes:**
  - a cup's peak fatigue offset at about 2× vanilla's −0.025 (`CAF_OFF_MAX` set so one standard cup peaks at about −0.05);
  - intoxication about 6 per beer;
  - a mild hangover (`HANG_H` and its effect sizes reduced).
- **Realistic** keeps today's constants.

- [ ] **Step 1:** Failing tests for both modes: a cup's peak; four beers peaking at about 20 (Game) or about 31 (Realistic); the hangover length.
- [ ] **Step 2:** Implement, labelling the Game constants as game choices. Re-record the golden. Run the gates and the full pytest, then commit.

### Task 11: Live sessions (Opus; live)
**Files:** `testing/experiments/x452_*.py` to `x457_*.py`, starting from `x44_guide_lib.py` with a new `x45_lib`; the profiles `x45-mod.toml` and `x45-mod-sleep.toml`, booting the staged copy; and the artifacts.

- [ ] **Step 1:** Write the drivers offline, with every grade's failing case. The sessions:
  - x452: a three-meal day, with the cadence and Well Fed against vanilla's;
  - x453: overeating, where raw broccoli eaten stops at Overfull 4 with a refused eat;
  - x454: starvation, where the cap lifts, Starving shows, health reaches the first floor, and eating then recovers it;
  - x455: starvation with a bleed, where the bleed still drains;
  - x456: no water, with Parched and the first floor at about 35 h;
  - x457: High Thirst on and off.

  Each session stays under 10 minutes. A longer one is split.
- [ ] **Step 2:** Review the drivers (Opus), then run the sessions one at a time and commit each artifact.
- [ ] **Step 3:** A live-evidence review (Opus), then a fix round.

### Task 12: Registers and pages (Opus; docs lane)
- [ ] **Step 1: One delta** that:
  - supersedes the rows describing the old caps, the Energy and Hydration moodles, the water base (`K.fluids.AI`), the stimulant strengths, the lethal drain times and `NR.DeficienciesCanKill`, each with a successor;
  - mints the mod-mechanism C/inference rows for the drain engine, the curve, the bridge, the water base and the volume term;
  - mints the x451–x457 readings as M rows;
  - updates the owner sentences on the area pages, with `page_lint` at 0.
- [ ] **Step 2:** Trial apply, whole-delta review, fix round, then the controller's apply.

### Task 13: The player guide (Opus)
- [ ] **Step 1:** Update `tools/mod_guide_series.py` for every chart the changes move: H1, S1, S2, S2d, S5c, S6, SH1, SV1 and the moodle text. Add notes 10f and 10g.
- [ ] **Step 2:** Update the page text for the new mechanics, the moodle list, starvation and dehydration, and Well Fed. The fact-check rules apply.
- [ ] **Step 3:** `--write` then `--check`, the page tests, a render, and a review.

### Task 14: The close (controller)
- [ ] The whole-pass review, one consolidated fix wave and its re-review.
- [ ] The README, CHANGELOG and COMPATIBILITY.
- [ ] Every § 3 gate, the full pytest, the CLAUDE.md baseline, the memory files and the push.
- [ ] Re-publish the guide artifact.

## Self-review
| Spec section | Task |
|---|---|
| § 2.1 | 6 |
| § 2.2 | 7 |
| § 2.3 | 8 |
| § 2.4 | 8 |
| § 2.5 | 9 (tooltip) |
| § 3.1 | 2, 5 |
| § 3.2 | 4 |
| § 3.3 | 4 |
| § 3.4 | 3 |
| § 4 | 9 |
| § 5 | 10 |
| § 7 | 11 |
| § 8 | 1, 12, 13 |
| § 10 | named in each task |

- **Interfaces:** `K.drain.step` (Task 4) is consumed by Tasks 5 and 8. h_model (Task 6) is consumed by Task 9's tooltip.
- **Order:** Task 2 measures before Task 5 builds. Task 4 comes before Tasks 5 and 6, because the writer hands over to the drain states.
