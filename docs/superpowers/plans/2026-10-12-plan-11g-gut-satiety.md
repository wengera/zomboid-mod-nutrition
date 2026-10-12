# Plan 11g: Gut satiety (C-1) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the meal pool P (fed in full at the eat, half-life 0.7 h) with a gut stage G fed by what the stomach empties each minute, weighted by nutrient and cleared over hours. Then refit the satiety constants and the deficit drive so each is fitted to its own studies.

**Architecture:**
- `K.satiety` loses P (`feed`, `decay` at `HALF_LIFE_H`, `post`, `seedP`) and gains:
  - `gFeed(G, emptied)` → G;
  - `gClear(G, dtH, trait)` → G;
  - `gRead(G)` → [0, 1);
  - `seedG(hunger, F, es)` → G.
- **Who calls what:**
  - `NR_Server_Kinetics` already drains the stomach each minute, and feeds G with the emptied vector;
  - `NR_Server_Writer` clears, reads and seeds G where it handled P;
  - `NR_Server_Intake` stops feeding at the eat.
- **The absorbed stage A** (`aFeed`/`aClear`/`aRead`, `record.satiety.A`) is built only under the stage rule (Task 6).

**Tech Stack:**
- Lua 5.1 (Kahlua) kernels, one statement a line.
- Python tests on lupa 2.8.
- `tools/replay_live.py`.
- `testing/pzt` for the live checks.

**Spec:** `docs/superpowers/specs/2026-10-12-gut-satiety-design.md` (approved by Angus, 2026-10-12).

## Global Constraints
- **CLAUDE.md governs.** § 3 gates every commit. § 4 governs claims and science rows. § 5 governs every live step. § 6 governs process.
- **Refactor heavily as you go** (§ 6, Angus 2026-10-12). Each code task names its refactor scope; each review judges structure, abstraction and performance beside correctness.
- **No backward compatibility.** The mod is unreleased: `record.satiety.P` is removed, not migrated, and a corrupt record heals to fresh.
- **Rule 6.** No per-tick work. G's feed, clearance and read live inside the per-minute steps that already run. Bench the kernel cost with lupa before and after Task 4.
- **Constants and kernel style.**
  - Every constant sits on a settled `science.tsv` row or is labelled `game choice` with the rows that bound it.
  - Provisional constants carry `provisional, refit in Plan 11g Task 6`, and no provisional label survives Task 6.
  - Kernel files keep one statement a line (the coverage gate). Kahlua rules apply.
- **The golden trace** (`testing/tests/kernel/golden/trace-1.0.0.json`) is re-recorded only in a commit that names its cause (ruling T2-1).
- **The stage rule.** G alone first. A is added only on a named failing time-course oracle that A fixes.
- **Frozen files.** Drivers and libs under `testing/experiments/` are never edited after their run.
  - A test of a frozen lib that reads the removed `satiety.P` is deleted by name, under a ledgered ruling, as dead-code tests were in Plans 11a, 11c and 11d.
  - The pytest count drops only by those names, and the § 3 baseline is reset by name at the close.
- **Models.** Opus for harvests, citation reviews, fits, live runs and every review of evidence. Sonnet for spelled-out edits and scoped re-reviews. The model is always named.

## Rulings this plan carries
- **11g-1 (order).** Plan 11g runs before Plan 11b. Angus chose C-1 next on 2026-10-12, and 11b's acceptance must test the final satiety model. Cost if wrong: none.
- **11g-2 (the oracles before the build).** Task 3 encodes every new study oracle against today's P model. Each one is pinned at today's reading, as a named distance, so the change is visible. Task 6 turns each into a target assertion. Cost if wrong: none.
- **11g-3 (the named non-reproductions).** These are re-read under G:
  - S1224's absolute snack delays (model 193/159/167 min against 60/34/25);
  - S1228's fasted 1 MJ drinks (236 against 65/126 min);
  - S1272's 1,692 g meal.

  A G that reproduces any of them makes it a target. Otherwise it stays named, with its new reading.

## File structure
| File | Change |
|---|---|
| `mod/.../shared/NR_Kernel_Satiety.lua` | P removed; G added. Restructured into sections (fullness, gut stage, read, composition, seed, factors), with each constant's long label moved into one constants block at the top |
| `mod/.../server/NR_Server_Kinetics.lua` | feeds G from `KIN.drain`'s emptied vector |
| `mod/.../server/NR_Server_Writer.lua` | clears, reads and seeds G; P's branch removed |
| `mod/.../server/NR_Server_Intake.lua` | `IN.feed` and its call sites removed |
| `mod/.../shared/NR_Kernel_Store.lua` | INPUTS `satiety.P` → `satiety.G` (and `satiety.A` if Task 6 adds it) |
| `tools/replay_live.py` | P → G |
| `tools/fit_gut_satiety.py` (new) | the joint fit (Task 6), committed, with its output staged under `testing/artifacts/fit-11g-<date>/` |
| `testing/tests/kernel/test_satiety_gut_oracle.py` (new) | the new time-course, protein and surplus oracles |
| `testing/tests/kernel/test_kernel_satiety_physiology.py`, `test_satiety_meal_studies.py`, `test_writer_shape.py`, `test_heal_once.py`, `test_kernel_store.py`, `test_intake_shape.py`, `test_replay_live_*.py`, `tools/tests/test_replay_live.py` | P → G |
| `docs/superpowers/research/2026-10-12-gut-satiety/` (new) | the harvest reports and science part files |

---

### Task 0: Gate and workspace (controller)
- [ ] **Step 1: Create the workspace.** From the repository root (CLAUDE.md § 6), run `C:\Users\Angus\.claude\plugins\cache\superpowers-marketplace\superpowers\6.3.0\skills\subagent-driven-development\scripts\sdd-workspace docs/superpowers/plans/2026-10-12-plan-11g-gut-satiety.md`.
- [ ] **Step 2: Open the ledger.** Its first line names the plan, followed by:
  - rulings 11g-1 to 11g-3;
  - HEAD;
  - the pytest count (`python -m pytest tools/tests testing/tests -q`, expect 3828);
  - the golden sha256 (expect `7f8ea84a…afed`);
  - the next register id (#3696) and the next science id (S1799).
- [ ] **Step 3: Pre-flight scan.** Scan the plan for conflicts (the SDD skill's table) and ledger the table.

### Task 1: The harvest (three Opus research agents in parallel; docs lane)
**Files:**
- Create `docs/superpowers/research/2026-10-12-gut-satiety/11-hormone-time-courses.md` and `11-rows.tsv`.
- Create `12-transit-absorption.md` and `12-rows.tsv`.
- Create `13-surplus-repeated-meals.md` and `13-rows.tsv`.

Every row file uses the `science.tsv` columns, with provisional ids reserved per agent:
- 11: S1799–S1858;
- 12: S1859–S1918;
- 13: S1919–S1978.

The controller renumbers at the mint.

- [ ] **Step 1: Agent 11, hormone and hunger time courses.**
  - **What to collect:** studies reporting CCK, PYY, GLP-1 and ghrelin at 0–6 h after a meal of stated kcal and composition, with hunger or fullness (VAS) on the same timeline wherever reported.
  - **Contrasts to cover:**
    - meal size, at least three sizes across about 250–1,000 kcal;
    - protein against carbohydrate against fat at equal kcal;
    - fibre;
    - liquid against solid.
  - **Per row:** the value, its unit, n, the timepoints, and the figure or table it came from.
  - **The report states:**
    - whether hunger ratings show one post-absorptive phase or two (an early CCK phase in minutes, a late PYY/GLP-1 phase in hours);
    - the apparent half-times of each phase;
    - which macronutrient contrasts are robust and which are null.
- [ ] **Step 2: Agent 12, nutrient transit and absorption.**
  - **What to collect:**
    - small-intestinal transit times;
    - plasma glucose and amino-acid appearance curves after meals of known size;
    - duodenal or intestinal nutrient-infusion studies with hunger or intake outcomes, which separate the gut signal from gastric distension.
  - **The report states:** a defensible first-order clearance half-life for a gut signal, with its range.
- [ ] **Step 3: Agent 13, surplus and repeated meals.**
  - **What to collect:**
    - Karl 2021's well-fed arm (reuse `docs/superpowers/research/2026-10-10-live-study-replays/03-karl-2021-facts.md`): the daily hunger suppression and its protocol;
    - overfeeding studies of 1 to 14 days with hunger ratings;
    - studies on whether satiety builds up across a day's meals (a meal's effect on the next meal's hunger).
  - **The report states:** the figure a G model must hit for a surplus day, and its tolerance.
- [ ] **Step 4: Each agent's return.** Each agent commits its report and row file by pathspec. It never edits `science.tsv`, never installs a package (§ 6), and reports its exact model id.

### Task 2: Citation review and mint (an Opus reviewer per harvest; controller mints)
- [ ] **Step 1: Review.** For each harvest, an Opus reviewer resolves every row's citation against its record (DOI, PubMed or publisher page). It writes `task-2-review-<n>.md` with a corrections file in the reviewer's format, as used in 11f.
- [ ] **Step 2: Apply the corrections.** A Sonnet applier applies them verbatim.
- [ ] **Step 3: Mint.** The controller applies each part file with `python tools/science_delta.py`, renumbering from S1799. Then it runs `python tools/science_check.py --staged` → 0 and commits.
- [ ] **Step 4: The stage verdict.** Ledger the harvest's verdict on one stage against two, as evidence only. The stage rule still decides in Task 6.

### Task 3: The oracles against today's model (Opus; lane M, tests only)
**Files:**
- Create `testing/tests/kernel/test_satiety_gut_oracle.py`.

**Interfaces:**
- **Consumes:** the minted rows (Task 2), and today's replay harness. Reuse `test_satiety_meal_studies.py`'s `REPLAY` Lua chunk pattern: one step a game minute with eats, the stomach drain, the pool, F, and displayed hunger.
- **Produces** these functions, each taking only `host` (the mutation-script convention in `test_satiety_meal_studies.py`'s docstring):
  - `time_course(host, kcal, composition, minutes)` → a list of displayed HUNGER, one value a minute;
  - `protein_contrast(host)` → a dict of hunger differences at the study's timepoints;
  - `surplus_day(host)` → the mean daily hunger, fed against request.

- [ ] **Step 1: Write the oracle module.**
  - One test per new oracle in spec § 4: two or three meal sizes, one protein-against-carbohydrate pair, and Karl's well-fed arm.
  - Each test reads today's model and pins its distance to the study figure, for example `assert abs(model - pinned) < 1e-6`. Its docstring names the study row, the target and the tolerance Task 6 will assert.
  - Re-read the three non-reproductions of ruling 11g-3 and pin them the same way.
- [ ] **Step 2: Run them.** `python -m pytest testing/tests/kernel/test_satiety_gut_oracle.py -q`. Expect PASS: each pins today's reading.
- [ ] **Step 3: Commit.** `git commit -m "Plan 11g Task 3: the gut-satiety oracles pinned at today's P model" -- testing/tests/kernel/test_satiety_gut_oracle.py`

### Task 4: The G build and the satiety refactor (Opus; lane M)
**Files:**
- Modify `NR_Kernel_Satiety.lua`, `NR_Server_Kinetics.lua`, `NR_Server_Writer.lua`, `NR_Server_Intake.lua` and `NR_Kernel_Store.lua`.
- Modify `tools/replay_live.py`.
- Modify the tests in the file-structure table.

**Interfaces:**
- **Produces** these functions, with the code below:
  - `K.satiety.gFeed(G, emptied)`
  - `K.satiety.gClear(G, dtH, trait)`
  - `K.satiety.gRead(G)`
  - `K.satiety.seedG(hunger, F, es)`
  - the constants `G_REQ`, `G_STEEP`, `G_HALF_LIFE_H` and `G_SEED_MAX`
- **Unchanged:** `K.satiety.sated(F, Gn)` keeps its signature, and `K.satiety.weigh(vector)` its body.

- [ ] **Step 1: Bench the baseline.** Bench today's writer and kinetics satiety path per player-minute (lupa, the 11f bench pattern). Ledger the figure.
- [ ] **Step 2: Write the failing kernel tests** in `test_kernel_satiety_physiology.py`:
  ```python
  def test_g_feed_adds_the_weighted_kcal_of_what_emptied(host):
      K = host.K
      v = host.vector(calories=100, proteins=0, carbs=25, lipids=0)
      assert host.call("K.satiety.gFeed", 10.0, v) == 10.0 + host.call("K.satiety.weigh", v)

  def test_g_clears_first_order_at_its_half_life(host):
      hl = host.get("K.satiety.G_HALF_LIFE_H")
      assert abs(host.call("K.satiety.gClear", 8.0, hl, 1) - 4.0) < 1e-9
      assert host.call("K.satiety.gClear", 8.0, 0, 1) == 8.0

  def test_g_read_is_the_request_level_at_g_req_on_an_empty_stomach(host):
      greq = host.get("K.satiety.G_REQ")
      assert abs(host.call("K.satiety.gRead", greq) - 0.75) < 1e-9
      assert host.call("K.satiety.gRead", 0) == 0

  def test_seed_g_inverts_the_read_and_caps(host):
      g = host.call("K.satiety.seedG", 0.25, 0.0, 1.0)
      sated = host.call("K.satiety.sated", 0.0, host.call("K.satiety.gRead", g))
      assert abs(host.call("K.hybrid.hungerTarget", sated, 1.0) - 0.25) < 1e-6
      assert host.call("K.satiety.seedG", 0.0, 0.0, 1.0) == host.get("K.satiety.G_SEED_MAX")
  ```
  These match the existing host helpers in that file. Adapt `host.vector` and `host.call` to whatever helpers it already defines, rather than inventing new ones.
- [ ] **Step 3: Run them.** `python -m pytest testing/tests/kernel/test_kernel_satiety_physiology.py -q -k "g_"`. Expect FAIL: the functions are not defined.
- [ ] **Step 4: Implement the kernel.** In `NR_Kernel_Satiety.lua`, delete `feed`, `decay`, `post`, `seedP`, `P_REQ`, `HALF_LIFE_H` and `P_SEED_MAX`, and add:
  ```lua
  K.satiety.G_REQ = 6 -- provisional, refit in Plan 11g Task 6 (P_REQ's Plan 11c fit carried over): G in weighted kcal at which an empty stomach reads the request level 0.25
  K.satiety.G_STEEP = 0.05 -- provisional, refit in Plan 11g Task 6 (STEEP's Plan 11d fit carried over): the read's exponent
  K.satiety.G_HALF_LIFE_H = 0.7 -- provisional, refit in Plan 11g Task 6 (HALF_LIFE_H's Plan 11c fit carried over): G's clearance half-life in game hours
  K.satiety.G_SEED_MAX = 1300 -- provisional, refit in Plan 11g Task 6 (P_SEED_MAX carried over): the seed's cap

  function K.satiety.gFeed(G, emptied)
      return G + K.satiety.weigh(emptied)
  end

  function K.satiety.gClear(G, dtH, trait)
      if dtH <= 0 then
          return G
      end
      return G * math.exp(-0.6931471805599453 * dtH * trait / K.satiety.G_HALF_LIFE_H)
  end

  function K.satiety.gRead(G)
      if G <= 0 then
          return 0
      end
      local x = math.exp(K.satiety.G_STEEP * math.log(G / K.satiety.G_REQ))
      return 1 - 1 / (1 + 3 * x)
  end
  ```
  - `seedG` is today's `seedP` body with `P_REQ`, `STEEP` and `P_SEED_MAX` replaced by `G_REQ`, `G_STEEP` and `G_SEED_MAX`.
  - `STEEP` goes once `G_STEEP` replaces it. Grep every reader first.
  - **The refactor:** reorganize the file into these sections, each with a one-line header comment:
    - constants;
    - fullness;
    - the gut stage;
    - the read and composition;
    - the seed;
    - discomfort;
    - the circadian, acute, sleep and nicotine factors.
  - Move each constant's long provenance label into the constants block, as one line per constant.
- [ ] **Step 5: Wire the servers.**
  - **`NR_Server_Kinetics` step:** after `KIN.drain` returns `emptied`, if `record.satiety` is a table and `record.satiety.G` is finite, set `record.satiety.G = K.satiety.gFeed(record.satiety.G, emptied)`. Keep the previous value when the result is not finite, and count the guard as the step's other guards are counted.
  - **`NR_Server_Writer`:** at the P branch (around lines 207–220), replace `seedP` with `seedG`, and `decay(s.P, dtH, HALF_LIFE_H, …)` with `gClear(s.G, dtH, …)`. Replace `post(s.P)` with `gRead(s.G)`, and rename `s.P` to `s.G` throughout.
  - **`NR_Server_Intake`:** delete `IN.feed` and its call sites. Rewrite the comment above it to say satiety now comes from the stomach's emptying (Kinetics).
  - **`NR_Kernel_Store` INPUTS:** `"satiety.P"` becomes `"satiety.G"`.
  - **`tools/replay_live.py`:** P becomes G. Read its stand-in for the kinetics step and feed G there.
- [ ] **Step 6: Port the tests.**
  - Every test in the file-structure table moves from P to G. A test whose subject was the eat-time feed is rewritten to assert the feed at emptying.
  - The oracles in `test_satiety_meal_studies.py` keep their study targets and tolerances. A replay that now misses its tolerance under the provisional constants is pinned at its new reading, with a docstring line naming Task 6. Use the same pattern as Task 3 for that pin.
  - Tests of frozen libs (`testing/tests/test_x31_nicotine_lib.py`, `test_x32_nicotine_lib.py`) that read `satiety.P`: delete each such test by name and ledger the names (Global Constraints).
- [ ] **Step 7: Run the gates.** Full pytest in its own call. Then mutate on a scratch copy (`git archive HEAD | tar -x -C <scratch>`):
  - the feed removed;
  - clearance at ×2 and ×0.5;
  - `seedG` uncapped.

  Each must fail a test. Then run the § 3 mod gates, `bus_inventory --check`, and the full `claims_check`. Pin or re-anchor every moved register pointer in the same commit (§ 6).
- [ ] **Step 8: Re-record the golden** in the same commit, under the cause "Plan 11g Task 4: satiety from the gut stage G fed at emptying (P removed)", with every moved leaf attributed in the report.
- [ ] **Step 9: Bench after** with the same rig as Step 1. Ledger the delta.
- [ ] **Step 10: Commit by pathspec**, without chaining it after a test: `git commit -m "Plan 11g Task 4: the gut stage G replaces the meal pool P (fed at emptying), satiety kernel restructured; golden re-recorded" -- <paths>`

### Task 5: The joint fit tool (Opus; tools lane)
**Files:**
- Create `tools/fit_gut_satiety.py`.
- Create `tools/tests/test_fit_gut_satiety.py`.

**Interfaces:**
- **Consumes:** the oracle functions of Task 3 and the meal-study replays.
- **Produces:** `python tools/fit_gut_satiety.py --grid <spec> --out <dir>`. It writes `fit.json`, holding every candidate's loss per oracle and the chosen point. `--stage A` adds A's constants to the search.

- [ ] **Step 1: Write the failing tool test.** On a two-point grid, the tool returns the point with the lower summed relative miss and writes `fit.json` with one entry per oracle.
- [ ] **Step 2: Run it.** Expect FAIL.
- [ ] **Step 3: Implement it.**
  - The search runs a grid, then refines coordinate by coordinate over `FULL_WEIGHT`, `G_REQ`, `G_STEEP` and `G_HALF_LIFE_H`, plus any nutrient weight the harvest supports.
  - The loss is the sum, over every hard oracle in spec § 4, of each oracle's relative miss beyond its tolerance.
  - It patches constants on the lupa host, never on a tracked file.
- [ ] **Step 4: Run and commit.** Run the tool's tests, then commit `tools/fit_gut_satiety.py` and its test by pathspec.

### Task 6: The fit, the stage rule and the targets (Opus; lane M)
**Files:**
- Modify `NR_Kernel_Satiety.lua` (the constants and their labels).
- Modify `test_satiety_gut_oracle.py` and `test_satiety_meal_studies.py`.
- Modify the golden.

- [ ] **Step 1: Run the fit for G alone.** Run `python tools/fit_gut_satiety.py`. Stage its output byte-identical under `testing/artifacts/fit-11g-<date>/`.
- [ ] **Step 2: Apply the stage rule.** If an oracle still fails and the harvest shows a second phase:
  - run `--stage A`;
  - build A as `aFeed` from `gClear`'s cleared amount, plus `aClear` and `aRead`, with the same patterns and tests as Task 4 Steps 2–4;
  - `record.satiety.A` joins INPUTS;
  - `sated` gains a third factor.

  Otherwise ledger "single stage".
- [ ] **Step 3: Set the constants.** Each carries a label: a settled row, or `game choice, fitted in Plan 11g Task 6 against <rows>`. No provisional label remains (grep for `provisional`).
- [ ] **Step 4: Turn the pins into targets.**
  - Each Task 3 and Task 4 pin becomes a target assertion at its tolerance.
  - A target the fit cannot reach stays pinned as a named non-reproduction, with its reading and a ledgered ruling.
  - Ruling 11g-3's three are re-read and turned into targets or kept named.
- [ ] **Step 5: Mutation pass** on a scratch copy. Every fitted constant at ×2 and ×0.5 must fail an oracle. Ledger the table.
- [ ] **Step 6: Gates, golden and commit.** Run full pytest, the gates, and the full `claims_check`. Re-record the golden under "Plan 11g Task 6: the gut-satiety fit". Commit.

### Task 7: The deficit-drive refit on deficit studies alone (Opus; lane M)
**Files:**
- Modify `NR_Kernel_Energy.lua` (`BALANCE_SPAN_KCAL`, `EX_BYPASS_LO`/`HI`).
- Modify `NR_Kernel_Hybrid.lua` (`DEFICIT_FLOOR`).
- Modify `testing/tests/kernel/test_replay_live_energy.py`.

- [ ] **Step 1: Re-run the server-path oracles.** Run `test_replay_live_energy.py` (Whybrow, King, E-MECHANIC, Karl's deficit arm) under the Task 6 model, and record which pass.
- [ ] **Step 2: Refit on the deficit arms only.** Refit the three constants with Karl's well-fed arm out of the loss, now carried by G (Task 6's surplus oracle). Use the Plan 11f Task 2c widened-search method (its report is in the 11f workspace).
- [ ] **Step 3: Set the labels.** Set the constants with labels naming the deficit rows they were fitted on. Every oracle passes; a miss is a named, ruled non-reproduction.
- [ ] **Step 4: The refactor.** Move the deficit drive's pieces into one cohesive section, or into a module if that reads better. Today they sit across `NR_Kernel_Energy` (the balance and the bypass) and `NR_Kernel_Hybrid` (the floor and `hungerTarget`). Re-anchor every pointer in the same commit.
- [ ] **Step 5: Mutation, gates, golden and commit.** Mutate on a scratch copy. Run full pytest, the gates, and the full `claims_check`. Re-record the golden under "Plan 11g Task 7: the deficit drive refit on deficit studies". Commit.

### Task 8: Live checks (Opus; live; two sessions or more)
**Files:**
- Create `testing/experiments/x36_gut_lib.py`, the drivers `x361_*.py`, the profile `x36-gut.toml` and `x36_grade.py`.
- Create the tests `testing/tests/test_x36_gut_lib.py`, on fake clocks.

- [ ] **Step 1: Build from the newest lib.** Copy patterns from `x35_exercise_lib.py` and `x34_monotony_lib.py`: autodrop events, `>=` event placement, and same-second client/server pairs (§ 5). Ring paths include `satiety.G` (and `satiety.A`), the stomach's buffer kcal, and HUNGER.
- [ ] **Step 2: A meal time course.** Eat two meals of different size (TKX_StudyFoods). Ring HUNGER and G every minute for 4 to 6 game hours. Grade live against the replay at the 11f tolerances.
- [ ] **Step 3: A surplus day.** Three large meals. Grade the day's mean HUNGER against the replay, and report the distance to Karl's well-fed figure as a reading (ruling 8-R).
- [ ] **Step 4: Stage the artifacts.** Stage byte-identical, never commit. Write the report with the artifacts rows, the do-not-cite leaves and the candidate claims, as in the 11f tasks.

### Task 9: The record (Opus; docs lane)
- [ ] **Step 1: Delta and pages.**
  - Supersede or rewrite every register row describing P: #3622 and its family on `body-effects#hunger-from-satiety`, and the 11c/11d satiety rows.
  - Add rows for G, the fit, the deficit refit and the live readings.
  - Update `docs/areas/body-effects.md#hunger-from-satiety`.
  - Remove or rewrite any C-1 line in `open-questions.md`.
- [ ] **Step 2: Mark the candidate built.** In `04-mechanism-candidates.md`, mark C-1 as built.
- [ ] **Step 3: The 11b amendments.** Rewrite them so the satiety acceptance reads G.
- [ ] **Step 4: Process.** Follow the 11f Task 10 process: delta files, a trial apply on a `git archive` copy, a whole-delta review, then the controller's apply.

### Task 10: The close (controller; an Opus whole-pass review)
- [ ] **Step 1: Review and fix.** The whole-pass review (structure and performance included), one fix wave, and its re-review.
- [ ] **Step 2: Gates and records.** Run the § 3 gates, and reset the pytest baseline by name if Task 4 deleted frozen-lib tests. Update CLAUDE.md and the memory files, then push.
- [ ] **Step 3: Report to Angus.** Cover:
  - the stage verdict;
  - each oracle before and after;
  - the deficit constants before and after;
  - the live readings;
  - the non-reproductions;
  - new mechanism candidates.

---

## Self-Review
- **Coverage.** Spec § 2 → Tasks 1–2. Spec § 3 → Tasks 4 and 6. Spec § 4 → Tasks 3, 6 and 7. The refactor clause (§ 5a) → Tasks 4 and 7, plus every review. Spec § 6's risks → the stage rule, the mutation passes and the named non-reproductions.
- **No placeholders.** The fitted values are outputs of Task 6 by design. Task 4 carries explicit provisional values and labels, and Task 6 removes every provisional label.
- **Name consistency.** `gFeed`, `gClear`, `gRead`, `seedG`, `G_REQ`, `G_STEEP`, `G_HALF_LIFE_H`, `G_SEED_MAX` and `record.satiety.G` are used identically in Tasks 4–9. The A stage's names (`aFeed`, `aClear`, `aRead`, `record.satiety.A`) appear only under Task 6's stage rule.
