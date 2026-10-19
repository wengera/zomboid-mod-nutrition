# Plan 17: the health curve and the combining options — implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the drain's "lowest floor wins" with one remaining fraction per lethal state:
- starvation and dehydration on a curve that opens at vanilla's rate and tapers to the real death;
- the deficiencies and the sodium and iron rungs linear;

and add two sandbox options, `NR.DeathPace` and `NR.HealthCombine`, spanning plain vanilla to strict realism.

**Architecture:** `NR_Kernel_Drain.lua` computes a fraction per active state and combines them into one target with the option's rule (worst, multiply or add). Health drains toward the target at the sum of the active states' rates, and vanilla regeneration heals toward it. The two options and the day length are read once a server minute in `NR_Server_Options.lua` and passed to `K.drain.step`. The severity-clock curve constants are calibrated offline by a new tool against the replay host.

**Tech stack:**
- Kahlua (Lua 5.1) kernels, with tests through lupa 2.8 (`testing/tests/kernel/`);
- Python tools under `tools/`;
- the live harness `testing/pzt` and `testing/experiments/xlib.py`;
- the guide generator `tools/mod_guide_series.py` → `docs/mod-guide/`.

**Spec:** `docs/superpowers/specs/2026-10-19-health-combine-design.md` (commit 7b784c4c). Read it in full before any task.

## Global Constraints

- CLAUDE.md §§ 3–6 bind every task: the gates, register deltas, the live rules, pathspec commits, no index-wide git commands (stash, `checkout --`, reset, restore, `add -N`, `add -f`, a bare add), and the golden re-recorded only under a named cause.
- **The curve:** `f(τ) = 1 − ln(1 + a·τ) / ln(1 + a·T)`. When `a ≤ K.drain.A_EPS` (1e-9), it is the line `1 − τ/T`.
- **Vanilla's rates in health per game hour:** `r_hunger = 0.0396 · dayMinutes` and `r_thirst = 0.198 · dayMinutes` (#0516, #0518, #2922).
- **Paces:**
  - Vanilla: starvation `100 / r_hunger` h, dehydration `100 / r_thirst` h, both linear.
  - Shortened: starvation 336 h, dehydration 48 h, both on the curve over hours.
  - Realistic: starvation to BMI 12 on BMI progress; dehydration curve 4 % → 15 % to fraction 0.1, then linear to 0 at 17 %.
- **Deficiencies and rungs:** linear, at 840 h (beriberi), 2160 h (scurvy), 4320 h (pellagra), 6 h (sodium), 24 h (iron), at every pace.
- **Combine:** Worst `100·min f`; Multiply `100·Π f`; Add `100·max(0, 1 − Σ(1 − f))`.
- **Defaults:** `NR.DeathPace` 3 (Realistic) and `NR.HealthCombine` 2 (Multiply).
- **The drain cap** a game day is the sum of the active rates:
  - a curve state's rate is its vanilla rate × 24;
  - a linear state's rate is `100 · 24 / T_h`;
  - Vanilla-pace lines take their vanilla rate × 24.
- **No compatibility shim** (the mod is unreleased). The constants named in spec § 2.4 are removed.
- **Rule 6:** no per-tick work. The bench and the Java-call count are compared before and after (spec § 3).
- **Every commit stays green:** pytest, the full claims_check, and `mod_guide_data --check` after any mod/ commit.

---

### Task 1: The curve calibration tool

**Files:**
- Create: `tools/calibrate_drain_curve.py`
- Create: `tools/tests/test_calibrate_drain_curve.py`
- Create: `testing/artifacts/calibrate-drain-20261019/calibration.json` (the tool's compact output)

**Interfaces:**
- Consumes:
  - the replay host `tools/replay_live.py` (`ServerReplay`) and the guide's fast setup in `tools/mod_guide_series.py`: `_vanilla_fast`, the S2d kernel job `j_s2d` with `AUTODROP_G` / `AUTODROP_MIN` water and the `FRESH` start; read how `result("j_s2d")` builds its run;
  - the dry job `j_s2d_dry` for dehydration.
- Produces: `calibration.json` with `a_starve`, `a_dehyd`, `starve_dpdt_per_h`, `dehyd_dpdt_per_h`, `r_hunger_90`, `r_thirst_90`, `day_minutes` 90, the inputs' sha256, and `tool_commit`. `--check` exits non-zero if a recomputation differs.

- [ ] **Step 1: Write the failing tests** for the solver, the pure part:

```python
from tools.calibrate_drain_curve import solve_a, opening_slope

def test_opening_slope_is_a_over_log():
    assert abs(opening_slope(0.24, 1800.0) - 0.24 / __import__("math").log(1 + 0.24 * 1800.0)) < 1e-12

def test_solve_a_meets_the_target_slope():
    a = solve_a(target=3.564 / 100.0, span=1800.0)
    assert abs(opening_slope(a, 1800.0) - 3.564 / 100.0) < 1e-9

def test_solve_a_gives_the_line_when_the_target_is_at_or_under_the_mean_slope():
    assert solve_a(target=1.0 / 1800.0, span=1800.0) == 0.0
    assert solve_a(target=0.5 / 1800.0, span=1800.0) == 0.0
```

  Here `opening_slope(a, T) = a / ln(1 + a·T)` is the fraction lost per clock unit at τ = 0.

  **Severity clocks:** the clock is the progress `p` itself (T = 1), and the time slope is `opening_slope(A, 1) · dp/dt`. So `a_starve` solves `opening_slope(A, 1) = r_hunger_90 / 100 / starve_dpdt_per_h`, and likewise for dehydration.
- [ ] **Step 2: Run** `python -m pytest tools/tests/test_calibrate_drain_curve.py -q` and expect an ImportError.
- [ ] **Step 3: Implement** `solve_a` by bisection on `log a` over [1e-9, 1e9], 200 iterations. It returns 0.0 when `target ≤ 1/span·(1 + 1e-12)`.
- [ ] **Step 4: Implement the replay read.**
  - Run the S2d with-water job's body to its starvation onset, then 24 game hours past it. Read `starve_dpdt_per_h = ((bmi0 − bmi(onset + 24 h)) / (bmi0 − 12)) / 24`.
  - From the dry job, read `dehyd_dpdt_per_h = ((d(onset + 6 h) − 4) / (15 − 4)) / 6`, the deficit in per cent.
  - Both are measured windows, a game choice recorded in the JSON as `window_h`.
- [ ] **Step 5:** Write the artifact with `--write` and verify `--check` passes. Add tests that `--check` fails when one input byte changes (use a temp copy) and that both `a` values are finite and positive. If either `a` comes out 0, report it as a concern and do not force it.
- [ ] **Step 6:** Commit by pathspec: the tool, the tests, the artifact folder, and an artifacts.md row with its reading guide and do-not-cite rows. Re-anchor every shifted `artifacts.md` pointer, and run the full claims_check (0).

---

### Task 2: The kernel — fractions, the curve, the combine step and the cap

**Files:**
- Modify: `mod/NutritionRevamp/common/media/lua/shared/NR_Kernel_Drain.lua` (whole engine)
- Modify: every reader of `targetFloor`, `FIRST_FLOOR`, `STARVE_RATE`, `DEF_RATE`, `DEF_HOLD_H`, `DEF_FINAL_H`, `ACUTE_FINAL_H`, `BMI_KNEE`, `timeKnots` and `starveFloor`. Find them with `grep -rn` over `mod tools testing`. Expected: `NR_Server_Effects.lua` (`targetFloor` → `target`), `tools/mod_guide_series.py` (the S2d notes; keep the generator running and patch the notes minimally — Task 6 rewrites them), and the replay host if it names them.
- Modify: `testing/tests/kernel/test_kernel_drain.py` (rewritten for the new model; tests of removed code deleted by name in the report)
- Modify: `testing/tests/kernel/golden/*` (re-recorded, own commit)

**Interfaces:**
- Consumes: `a_starve` and `a_dehyd` from Task 1's artifact, copied into the kernel with a comment naming the artifact.
- Produces:
  - `K.drain.OPT = { pace = 3, combine = 2, dayMin = 90 }`, a module table the adapter overwrites each minute (no allocation);
  - `K.drain.PACE_VANILLA = 1`, `PACE_SHORT = 2`, `PACE_REAL = 3`;
  - `K.drain.COMBINE_WORST = 1`, `COMBINE_MULTIPLY = 2`, `COMBINE_ADD = 3`;
  - `K.drain.rVanilla(code, dayMin)`: health per game hour (hunger for starvation, thirst for dehydration, nil otherwise);
  - `K.drain.curve(tau, T, a)`: the remaining fraction;
  - `K.drain.solveA(r, T)`: the time-clock `a`, health per game hour against hours, cached in `K.drain.ACACHE` by key;
  - `K.drain.fraction(code, tH, inp, opt)`: the state's fraction and its rate in health per game day (two returns);
  - `K.drain.combine(D, opt)`;
  - the record fields `D.target` (100 with none), `D.frac[code]` (nil when inactive), `D.rate` (the sum, health per game day) and `D.state` (the code with the smallest fraction; a tie keeps the earlier code);
  - `K.drain.step(record, dtM, ageH, overlay, opt)`, where `opt` nil reads `K.drain.OPT`;
  - `K.drain.take(D, health)` and `K.drain.heal(D, health, yPerMin, dtM)`, which keep their contracts against `D.target`.

- [ ] **Step 1: Write the failing kernel tests** in `test_kernel_drain.py`, using the file's `host` and `D` fixtures. The core cases:

```python
import math

def test_the_curve_ends_and_opening_slope(host, D):
    K = host.K
    assert K.drain.curve(0.0, 336.0, 0.05) == 1.0
    assert abs(K.drain.curve(336.0, 336.0, 0.05)) < 1e-12
    s = (1.0 - K.drain.curve(1e-6, 336.0, 0.05)) / 1e-6
    assert abs(s - 0.05 / math.log(1 + 0.05 * 336.0)) < 1e-6

def test_the_curve_is_the_line_at_a_zero(host, D):
    assert abs(host.K.drain.curve(84.0, 336.0, 0.0) - 0.75) < 1e-12

def test_solve_a_opens_at_vanillas_rate(host, D):
    K = host.K
    r = float(K.drain.rVanilla(K.drain.STARVATION, 90))
    assert abs(r - 3.564) < 1e-9
    a = K.drain.solveA(r, 336.0)
    assert abs(100 * a / math.log(1 + a * 336.0) - r) < 1e-6

def test_vanilla_pace_is_vanillas_line(host, D):
    K = host.K
    T = 100 / 3.564
    f, rate = K.drain.fraction(K.drain.STARVATION, T / 2, None, {"pace": 1, "combine": 3, "dayMin": 90})
    assert abs(f - 0.5) < 1e-9 and abs(rate - 3.564 * 24) < 1e-9

def test_combine_rules_order(host, D):
    # worst >= multiply >= add for the same fractions; 0.6 and 0.5 give 50, 30, 10
    ...
```

  The last test builds a record with two states active (starvation and beriberi) and steps it under each combine value, asserting targets 50, 30 and 10 within 1e-9. Use the file's `record(...)` builder, extended.

  Also cover:
  - each deficiency or rung is linear to 0 at its T at every pace;
  - Realistic dehydration's 0.1 knee at 15 % and 0 at 17 %;
  - Shortened dehydration reaches 0 at 48 h with no knee;
  - starvation on BMI progress reaches 0 at BMI 12, and a heavier body later;
  - `take` never passes `target`, and `drainThisMinute = rate · dtM / 1440` with `rate` the sum;
  - `heal` lifts health toward a risen target after a state ends;
  - Overlay still excludes starvation and dehydration;
  - `D.state` is the smallest-fraction code;
  - a pace switch mid-state moves the target at the next step;
  - no table is allocated per step (count `D.frac` identity across steps).
- [ ] **Step 2:** Run `python -m pytest testing/tests/kernel/test_kernel_drain.py -q` and expect failures.
- [ ] **Step 3: Implement.** The core, one statement per line (the kernel coverage gate):

```lua
K.drain.A_EPS = 1e-9 -- below it the curve is the line, no row needed
K.drain.R_HUNGER = 0.0396 -- health per game hour per real minute of day length: 3.3e-4 x 120 (#0516, #0518, #2922)
K.drain.R_THIRST = 0.198 -- health per game hour per real minute of day length: 1.65e-3 x 120 (#0516, #0518, #2922)
K.drain.SHORT_STARVE_H = 336 -- Shortened starvation, 14 game days: game choice (spec section 2.2)
K.drain.SHORT_DEHYD_H = 48 -- Shortened dehydration, 2 game days: game choice (spec section 2.2)
K.drain.A_STARVE = <from calibrate-drain-20261019/calibration.json a_starve> -- game choice (spec section 1.2)
K.drain.A_DEHYD = <from calibrate-drain-20261019/calibration.json a_dehyd> -- game choice (spec section 1.2)
K.drain.DEHYD_FINAL = 0.1 -- the fraction at the 15 % knee, dehydration's final stage (spec section 1.1)

function K.drain.curve(tau, T, a)
    if not (T > 0) then
        return 0
    end
    local t = K.clamp(tau, 0, T)
    if not (a > K.drain.A_EPS) then
        return 1 - t / T
    end
    return 1 - math.log(1 + a * t) / math.log(1 + a * T)
end
```

  - `solveA(r, T)`: returns 0 when `r ≤ 100 / T`. Otherwise it bisects `log a` over [1e-9, 1e9] with 200 iterations, cached in `K.drain.ACACHE[T .. ":" .. r]`. The key is a string, and a new day length or pace adds an entry, never one per minute.
  - `fraction(code, tH, inp, opt)` returns `(f, ratePerDay)` per spec §§ 1.1 and 2.2. The BMI progress is `(inp.bmi0 − bmi) / (inp.bmi0 − K.drain.BMI_DEATH)`, clamped to [0, 1]. A non-finite input returns nil, and the state is left out for the minute, as now.
  - `combine` folds `D.frac` into `D.target` by `opt.combine`.
  - `step` keeps every onset branch as it is and replaces `consider`'s floor logic with `fraction` plus combine.
- [ ] **Step 4:** Run the kernel tests and the full kernel suite. Expect only the golden test to fail.
- [ ] **Step 5:** Grep and fix every reader of the removed names (see Files), keeping `tools/mod_guide_series.py` generating. Run `python tools/mod_guide_data.py --write` and then `--check`.
- [ ] **Step 6:** Commit the kernel, its tests and the readers by pathspec, but not the golden. First run `python tools/hotpath_lint.py mod`, `kahlua_lint`, `mod_lint`, `release_pack check` and `science_check --scan mod` (all 0). The register pointers that this commit moves are re-anchored, and lines it rewrote are pinned (CLAUDE.md § 6), with the full claims_check at 0.
- [ ] **Step 7:** Re-record the golden in its own commit under "Plan 17: the remaining-fraction drain", every moved leaf attributed in the commit message and the report. Then run the full pytest in its own call, saved to a file and read from its summary line.

---

### Task 3: The options, the adapter, the replay host and Rule 6

**Files:**
- Modify: `mod/NutritionRevamp/42.21/media/sandbox-options.txt` (two enums after `NR.StimulantRealism`, in its style)
- Modify: `mod/NutritionRevamp/common/media/lua/shared/Translate/EN/Sandbox.json` (the names, tooltips and value names)
- Modify: `mod/NutritionRevamp/common/media/lua/server/NR_Server_Options.lua` (`deathPace` and `healthCombine` in `NR.server.options`, read in the poll like `stimulantRealism`, logged on change)
- Modify: `mod/NutritionRevamp/common/media/lua/server/NR_Server_Effects.lua`. Before `K.drain.step`, write `K.drain.OPT.pace`, `.combine` and `.dayMin` (`NR.read.dayMin(ctx, K.drain.DAY_MINUTES)`) once per server minute, not per player. Hoist the write to where the minute's shared reads live.
- Modify: `tools/replay_live.py` (the replay host sets `K.drain.OPT` from a `death_pace` / `health_combine` / `day_minutes` input, defaulting to 3, 2, 90)
- Modify: `tools/bench_slot.py`, or add a drain bench beside it
- Create: `testing/tests/kernel/test_drain_options.py`

**Interfaces:**
- Consumes: Task 2's `K.drain.OPT`, `K.drain.step(..., opt)`, and the pace and combine constants.
- Produces:
  - `NR.server.options.deathPace` (1–3) and `.healthCombine` (1–3);
  - replay inputs `death_pace`, `health_combine` and `day_minutes`.

- [ ] **Step 1: Write the failing tests:**
  - **The option read:** a stub sandbox with `NR.DeathPace` 1 and `NR.HealthCombine` 3 sets `K.drain.OPT` 1, 3, 90 after one server minute. Follow the existing options tests' pattern; grep for `stimulantRealism` under `testing/tests`.
  - **The vanilla oracle** (spec § 4.3): on the replay host, a fresh default body with no food and the S2d water, Vanilla pace and Add, dies (health 0) within the stated tolerance of `tools/vanilla_model.py`'s fast death time. The tolerance is the onset difference, 34.84 − 34.45 h, plus 1 game minute, and the test names it.
  - **The properties** (spec § 4.2) over a replayed 90-day fast with water and no vitamins, at every pace: the target under Worst ≥ under Multiply ≥ under Add at every minute; under Worst and Multiply, health 0 only where some fraction is 0.
- [ ] **Step 2:** Run them and expect them to fail.
- [ ] **Step 3: Implement** the files above. The sandbox enum style, copied from `NR.StimulantRealism`:

```
option NR.DeathPace
{
    type = enum, numValues = 3, default = 3,
    page = NutritionRevamp, translation = NR_DeathPace, valueTranslation = NR_DeathPaceValues,
}

option NR.HealthCombine
{
    type = enum, numValues = 3, default = 2,
    page = NutritionRevamp, translation = NR_HealthCombine, valueTranslation = NR_HealthCombineValues,
}
```

  The translations, in plain player words:
  - **Death pace:** Vanilla ("hunger and thirst kill on vanilla's clock"); Shortened ("starvation in about two weeks, dehydration in two days"); Realistic ("the real death points: a starving body at BMI 12, dehydration at a 17 % water loss").
  - **Health combining:** Worst only ("only the worst problem counts"); Multiply ("several problems compound"); Add ("losses add up, so several problems can kill before any one would").
- [ ] **Step 4:** Run the tests and expect them to pass. Run `mod_lint`, `release_pack check`, `kahlua_lint`, `hotpath_lint` and `science_check --scan mod` (all 0). Run `python tools/release_pack.py stage --dry-run`, or the check, to confirm the sandbox file parses.
- [ ] **Step 5: Rule 6.** Run the bench and the Java-call count before (on a `git archive` of Task 1's head) and after. Put the numbers in the report. The target is +0 per player-minute and +2 per server minute; anything more is a finding.
- [ ] **Step 6:** Commit by pathspec, regenerate the guide data after the mod/ commit, run the full claims_check (0), and run the full pytest in its own call.

---

### Task 4: Live readings (controller-gated, CLAUDE.md § 5)

**Files:**
- Create: `testing/experiments/x48_lib.py`, starting from `testing/experiments/x47_lib.py` and importing `xlib.py`
- Create: `testing/experiments/x481_curve.py` and `x482_vanilla.py`
- Create: `testing/profiles/x48-curve.toml` and `x48-vanilla.toml` (fixture `default`, the staged copy, `Nutrition = false`, sleep off)
- Create: `testing/tests/test_x48_lib.py`
- Artifacts: `testing/artifacts/x481-*/`, `x482-*/`

**Interfaces:**
- Consumes: the Task 3 options and the replay inputs.
- Produces: artifacts for Task 6's live rows and Task 5's chart notes.

- [ ] **Step 1: x481, Realistic with Multiply.**
  - Seed a fresh record past the acute onset: set the unfed clock near `STARVE_ONSET_H`, as x454 did; read its driver.
  - Hold 60 game minutes at speed. Then `record.set` beriberi's thiamine to the clinical grade at hour X, so two states combine.
  - Mid-run, set `NR.DeathPace` 2 through the sandbox command x464 used for the sleep toggle; grep its driver.
  - Grades:
    - every ring row's health and target match the HEAD replay of the run's own inputs within 0.002 (`x46_lib.REPLAY_TOL`);
    - the opening drain rate is within 1 % of `r_hunger(dayMin) · 24`;
    - the target follows the pace switch within one game minute.
- [ ] **Step 2: x482, Vanilla with Add.**
  - Same seed, with `NR.DeathPace` 1 and `NR.HealthCombine` 3.
  - Hold until death, or for 10 minutes of wall time at most. Use `time.multiplier` so that vanilla's ~28 game hours fit.
  - Grades: death within the replay's tolerance of the replay's death, and against x442's 36.45 h after its write (report the difference, do not grade on it, because the onsets differ).
- [ ] **Step 3:** Write offline tests that fail each grade, with a fake bus answering the real reply shapes, and pre-boot checks against the real staged copy. Commit the drivers before the first boot.
- [ ] **Step 4:** Re-stage (`tools/release_pack.py stage`). Run `doctor`, check at least 12 GB free and ledger it. Run each session in a foreground polling Bash call under 10 minutes. Commit the artifacts byte-identical with artifacts.md rows, reading guides, do-not-cite rows and the re-anchor. Write owner-sentence candidates in the report.

---

### Task 5: The guide

**Files:**
- Modify: `tools/mod_guide_series.py` (S2d)
- Modify: `docs/mod-guide/charts.js` (S2d's tabs)
- Modify: `docs/mod-guide/index.html` (the S2d prose, the options section, the limitations)
- Modify: the guide's test files under `tools/tests/` that cover S2d
- Regenerate: `docs/mod-guide/data.json`

**Interfaces:**
- Consumes: the Task 3 replay inputs and the Task 4 artifacts.
- Produces: series `S2d-m-pace-vanilla`, `S2d-m-pace-short` and `S2d-m-pace-real` (starvation alone: water plus thiamine, vitamin C and niacin held adequate in the replay), and `S2d-m-comb-worst`, `S2d-m-comb-mult` and `S2d-m-comb-add` (water, no vitamins).

- [ ] **Step 1: Write the failing tests** for the new series:
  - each ends at its death;
  - Worst ≥ Multiply ≥ Add pointwise;
  - the Vanilla-pace line dies within the oracle's tolerance of `S2d-v-model-health`'s end;
  - charts.js's S2d `Health` tab lists `S2d-m-drain`, `S2d-v-model-health` and `S2d-v-live-health`.
- [ ] **Step 2: Implement the series and the tabs:**
  - **Health:** the mod at its defaults plus vanilla's model and live lines;
  - **Pace;**
  - **Combining;**
  - **Without water, body mass and vanilla weight:** kept and re-run.

  Rewrite every S2d note so that it reads the new constants (no `FIRST_FLOOR` or `STARVE_RATE`) and says what the line shows, in player words. The x481 and x482 lines are drawn only if they pass the drawing rule (CLAUDE.md § 5).
- [ ] **Step 3: Update index.html:**
  - the S2d chart note;
  - the options section with both options, plainly;
  - the limitations: under health 10 vanilla wakes a sleeper, and starvation's tail and the deficiencies' last stretch spend time there; Add can kill before any one cause's death point;
  - remove every stale floor sentence (grep "first floor", "floor of 50", "25 a game day").
- [ ] **Step 4:** Regenerate the data and run `--check`. Run the guide tests (`-k guide`), the full claims_check and the full pytest in its own call. Then do a render check of the S2d tabs in the DOM.
- [ ] **Step 5:** Commit by pathspec.

---

### Task 6: The register and pages

**Files:**
- Create: `.superpowers/sdd/2026-10-19-plan-17-health-combine/task-6-delta.tsv` (the controller applies it)
- Modify: `docs/areas/body-effects.md` and every page tagging a superseded row (find them with the checker)

- [ ] **Step 1:** Supersede #3938, #3940 and #3941, and every floor-mechanism row (grep the register for `FIRST_FLOOR`, `STARVE_RATE`, `DEF_HOLD_H`, `starveFloor`, `timeKnots`, "first floor" and "lowest floor"), each with its successor.
- [ ] **Step 2:** Add rows for:
  - the curve, the combine step, the cap and the options, as C rows citing the kernel lines (`C/inference` where they are game choices);
  - the vanilla-rate formula, resting on #0516, #0518 and #2922;
  - the calibration artifact;
  - the x481 and x482 readings, as M rows with every number at its pointer, unrounded, and no do-not-cite parent.
- [ ] **Step 3:** Rewrite the owner sentences with provisional tags. Run a trial apply on a `git archive` copy with alternates, plus the § 4.10 regex; the full claims_check and page_lint read 0. Leave the pages uncommitted only if they carry provisional tags; the controller applies.

---

### Task 7: The re-stage and the options read-back boot

**Files:**
- Create: `testing/experiments/x483_options.py` (from x471's design), `testing/profiles/x48-options.toml`, and its tests

- [ ] **Step 1:** Re-stage from mod/'s final head.
- [ ] **Step 2:** One boot on fixture `two`: `NR.DeathPace` 2 and `NR.HealthCombine` 3 set in the server's options file and read back on the server, the admin and bob (`NutritionRevamp.server.options.deathPace` / `.healthCombine`). It also grades the clean 1.0.0 join. Same rules as Task 4 Step 4.
- [ ] **Step 3:** Commit the artifacts with their rows. Write the owner-sentence candidates as `task-7-delta.tsv`.

---

### Task 8: Close

- [ ] **Step 1:** The whole-pass review (Opus), one consolidated fix wave, and its re-review.
- [ ] **Step 2:** The mod README, CHANGELOG ("Before the upload": the health curve and the two options) and COMPATIBILITY.
- [ ] **Step 3:** Run every CLAUDE.md § 3 gate. Run the full pytest from its saved summary; it never drops, and any deleted tests are named.
- [ ] **Step 4:** Update the CLAUDE.md baseline. Update the memory files: the subjective-vanilla memory's "no toggle" now names the two options as Angus's choice.
- [ ] **Step 5:** Push and republish the guide (ask Angus where: the old artifact link is gone under the new account).
