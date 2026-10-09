# Plan 11d: the satiety revisit — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Land the revisit memo's twelve decisions (Angus, 2026-10-09: "Take all 12, plan, run it"). This brings the shipped satiety model in line with the quality-weighted evidence of Satiety research 2 (rows S1337–S1663).

**Architecture:**
- Four kernel changes are appended to the satiety and energy kernels, each fitted against replays of the studies in the two oracles:
  - the acute term's faster post-bout decay (C1);
  - the exercise lag's gain (C4);
  - a sleep-debt hunger factor (C2);
  - a protein fullness term, which ships only if the oracle holds (C5).
- Two replays are added as diagnostics: the 36 h fast and six meals against three (C3).
- One adapter task wires the kernel changes into the writer, with one golden re-record named "satiety revisit".
- Two jar reads (C7, C12) and the pages and rows run in the docs lane.
- Decisions 6, 8, 9, 10, 11 and C14 are named limitations, deferrals or a design rule; no mechanism changes for them.

**Tech Stack:**
- Lua 5.1 (Kahlua) mod code.
- Kernel tests in Python under `lupa` 2.8.
- The repository's register tools: `claims_delta.py`, `science_delta.py`, `claims_check.py` and `science_check.py`.

**Spec:** `docs/superpowers/specs/2026-10-09-satiety-revisit-memo.md`, its §§ 2 and 5 and its addendum. It amends `docs/superpowers/specs/2026-10-08-satiety-physiology-design.md` §§ 5b–5c. Executors read both, plus the reports and reviews under `docs/superpowers/research/2026-10-09-satiety-research-2/`.

## Global Constraints

- **Repository rules.**
  - CLAUDE.md governs every task: the § 3 gates, the § 5 Kahlua rules, the § 6 process, and the § 7 CRLF files.
  - Kernel files (`NR_Kernel*.lua`) are written one statement per line.
- **Rule 6.** No per-tick work. Every new term runs once per player-minute or once per eat. Each task reports its lupa µs cost.
- **Constants.**
  - A shipped constant names its S row, or is labelled "game choice, Plan 11d (ruling <n>)" with the rows it was fitted against.
  - The hunger mapping is ruling 11c-31: 65 mm VAS reads as HUNGER 0.25, so 260 mm per unit. It is a labelled assumption with no row.
- **The two oracles.**
  - `test_satiety_meal_studies.py` and `test_satiety_activity.py` hold their hard replays at 1.1×. S1233 stays at 1.15×. The Marmonier differences and the activity bands keep their stated tolerances.
  - A task that changes a constant re-runs both files.
  - A new or changed oracle assertion passes a mutation pass run on a scratch copy (`git -c core.autocrlf=false archive HEAD | tar -x -C <scratch>`), never on a tracked file.
- **The golden trace.** It is `9e6f230b27ecaabe5d1471c29269500a4bab0a2c7f73ed1c0d4d3403dc981961` at plan start. It is re-recorded once, in Task 6, under the named change "satiety revisit". Every leaf that moves must be attributed to a named cause.
- **Register pointers.** Rows #3613–#3626 point into `NR_Kernel_Satiety.lua`, `NR_Kernel_Energy.lua`, `NR_Kernel_Stomach.lua`, `NR_Kernel_Hybrid.lua`, `NR_Server_Writer.lua` and the oracle tests.
  - Append new code at the end of a file wherever possible.
  - Any line shift is a pointer finding. The implementer lists it by row and new line for the controller's re-anchor; implementers never edit `claims.tsv` or `science.tsv`.
- **Commits and git.**
  - Commits are pathspec commits. Implementers never push.
  - Never run stash, `checkout --`, reset, restore, `add -N`, `add -f` or any index-wide git command.
  - Never set GIT_* variables.
- **Starting counts.** pytest 3264, kernel 2476. A count drop is reset only by name, for deleted tests of retired code.
- **Lanes.**
  - Lane M is the one serial lane for `mod/` Lua and the kernel tests: Tasks 1, 2, 3, 4, 5, 6 in that order.
  - Lane D runs beside it: Task 7, then Task 8 after Task 6.

---

### Task 0: The workspace, the rulings and the spec addendum (controller)

**Files:**
- Create: `.superpowers/sdd/2026-10-09-plan-11d-satiety-revisit/progress.md` (gitignored).
- Modify: `docs/superpowers/specs/2026-10-08-satiety-physiology-design.md`: append § 5d.
- Modify: `docs/reference/science.tsv`: supersede S1334 through `science_delta.py status`.

- [ ] **Step 1: Read the baseline into the ledger.** Ledger these three values:

```bash
cd /c/Users/Angus/repos/project_zomboid
sha256sum testing/tests/kernel/golden/trace-1.0.0.json
python -m pytest testing/tests/kernel -q -p no:cacheprovider 2>/dev/null | grep -E "[0-9]+ passed" | tail -1
python -m pytest tools/tests testing/tests -q -p no:cacheprovider 2>/dev/null | grep -E "[0-9]+ passed" | tail -1
```

  Expected: `9e6f230b…1961`, 2476 passed and 3264 passed.

- [ ] **Step 2: Ledger the plan's rulings,** each in the form `Ruling: <what> — <why> — cost if wrong`.
  - **11d-1 (C1):** the acute term decays faster than it rises. The rise half-life stays 0.5 h, the decay half-life is fitted near 0.15 h, and ACUTE_MAX stays 0.7.
  - **11d-2 (C2):** a sleep-debt hunger factor, graded on `record.acute.debtH`, capped at the pooled size and reversing as the debt is repaid.
  - **11d-3 (C3):** the 36 h fast and the six-against-three meal replays are pinned readings. A failure is a finding to rule on, not to patch.
  - **11d-4 (C4):** the exercise lag gains an `EX_LAG_GAIN` near 0.7, with τ refit.
  - **11d-5 (C5):** a protein fullness term, shipped only if every hard replay holds at 1.1×. Otherwise it stays a named non-reproduction.
  - **11d-6 (C6, C8, C9, C13, C14 and eating rate):** neutral and named in LIMITATION_FOUR and #3622.
  - **11d-7 (C7, C12):** jar reads of SICKNESS and NICOTINE_WITHDRAWAL come before any term.
  - **11d-8 (C10):** resistance work stays at 0.5.
  - **11d-9 (C11):** monotony is a separate mood design after Plan 11b and never enters hunger.
  - **11d-10 (C15):** any future injury expenditure must not feed the deficit drive.
  - **11d-11:** this plan runs before Plan 11b.

- [ ] **Step 3: Supersede S1334 with the pooled readings that answer it.**

```bash
python tools/science_delta.py status S1334 superseded --successor "S1500, S1502"
python tools/science_check.py
```

  Expected: `S1334 status -> superseded (successor S1500, S1502)`, then `0 findings`.

- [ ] **Step 4: Append § 5d to the satiety spec,** before `## 6.`. It records decisions 1–12 as rulings 11d-1 to 11d-11, each with its rows, using the text in Step 2. Write it with a Python `newline=''` edit and check the file's endings with `file` first.

- [ ] **Step 5: Run the gates, commit and dispatch.**
  - Run `python tools/science_check.py --staged` and `PYTHONIOENCODING=utf-8 python tools/claims_check.py --staged`; both must read 0.
  - Commit: `git commit -m "Satiety spec § 5d: the revisit's rulings; S1334 superseded by S1500 and S1502 (Plan 11d Task 0)" -- docs/superpowers/specs/2026-10-08-satiety-physiology-design.md docs/reference/science.tsv`
  - Write `task-1-amendments.md` and `task-7-amendments.md`, list them, then dispatch Task 1 (lane M) and Task 7 (lane D).

---

### Task 1: The acute term's post-bout decay (C1) — Opus implementer, Opus reviewer

**Files:**
- Modify: `mod/NutritionRevamp/common/media/lua/shared/NR_Kernel_Satiety.lua`. Edit `exerciseSuppression` (near :137) and add a constant.
- Modify: `testing/tests/kernel/test_satiety_activity.py`, the ES band test near :313.
- Modify: `testing/tests/kernel/test_kernel_satiety_activity.py`.

**Interfaces:**
- Produces:
  - `K.satiety.ACUTE_DECAY_HALF_LIFE_H`, a number.
  - `K.satiety.exerciseSuppression(S, dtH, vigorous, kind)`, with the signature unchanged. It rises with `ACUTE_HALF_LIFE_H` while vigorous and decays with `ACUTE_DECAY_HALF_LIFE_H` otherwise.

- [ ] **Step 1: Write the failing tests.**
  - **Unit test (`test_kernel_satiety_activity.py`):**

```python
def test_the_decay_is_faster_than_the_rise(host):
    S = host.K.satiety
    assert S.ACUTE_DECAY_HALF_LIFE_H < S.ACUTE_HALF_LIFE_H
    up = S.exerciseSuppression(0.0, S.ACUTE_HALF_LIFE_H, True, "aerobic")
    assert abs(up - 0.5) < 1e-9                      # half way up in one rise half-life
    down = S.exerciseSuppression(1.0, S.ACUTE_DECAY_HALF_LIFE_H, False, None)
    assert abs(down - 0.5) < 1e-9                    # half way down in one decay half-life
```

  - **Replay (`test_satiety_activity.py`):** replace the ES band test with pooled-mm readings. Use the file's existing replay helper for a 60-min aerobic bout at trial hours 0–1, and its `MM_PER_UNIT = 260` mapping, or add that constant beside the 11c-31 docstring.

```python
def test_the_bout_tracks_the_pooled_mm_readings():
    # S1502 (King 2017, 17 crossovers, n = 192): hunger about -33 % during the bout;
    # S1500 (Hu 2023 MA): -8.465 mm immediately after, nothing at 30-90 min.
    r = replay_bout(minutes=60, kind="aerobic")      # the file's helper; returns hunger by minute vs control
    during = r.mean_ratio(0, 60)                     # mean exercise/control hunger over the bout
    assert 0.67 / 1.1 <= during <= min(1.0, 0.67 * 1.1)
    mm_at_30_after = r.mm_difference(90)             # minute 90 = 30 min after the bout
    assert abs(mm_at_30_after) <= 8.465              # no larger than the pooled immediate-post effect
```

  - Keep the gone-by-1.5 h, King 2010, King 2011 (cold and steady state), Whybrow and Karl tests unchanged.

- [ ] **Step 2: Run the tests and watch them fail.**

```bash
python -m pytest testing/tests/kernel/test_kernel_satiety_activity.py testing/tests/kernel/test_satiety_activity.py -q -p no:cacheprovider
```

  Expected: FAIL. The constant is absent, and the old kernel reads about −26 % at 30 min after the bout.

- [ ] **Step 3: Change the kernel.** Append the constant after the last line of the file, and change the decay branch of `exerciseSuppression` in place:

```lua
K.satiety.ACUTE_DECAY_HALF_LIFE_H = 0.15 -- game choice, Plan 11d (ruling 11d-1): the post-bout decay, fitted to S1500 (no effect 30-90 min after) and S1502 (-33 % during); the rise keeps ACUTE_HALF_LIFE_H
```

  - In the not-vigorous path, use `K.satiety.ACUTE_DECAY_HALF_LIFE_H` in place of `K.satiety.ACUTE_HALF_LIFE_H`.
  - Keep one statement per line, and the no-time clamp branch.
  - Fit the decay within 0.10–0.25 h to pass the new replay with the Karl replay unchanged, and state the fitted value and its two readings in the comment.

- [ ] **Step 4: Run both oracle files, then the kernel suite,** each in its own call. All must pass. If the Karl vigorous arm leaves its band, stop and report: ruling 11d-1 assumed it holds.

- [ ] **Step 5: Mutation pass, on a scratch copy.** Each of these must fail a test:
  - the decay half-life × 2;
  - the decay half-life × 0.5;
  - the decay set equal to the rise;
  - the rise and decay half-lives swapped.

- [ ] **Step 6: Run the gates and commit.**
  - Run kahlua_lint, hotpath_lint and the full claims_check. List any pointer finding.
  - Commit: `git commit -m "Satiety: the acute term decays faster than it rises (Plan 11d Task 1, ruling 11d-1)" -- <the three files>`

---

### Task 2: The exercise lag's gain (C4) — Opus implementer, Opus reviewer

**Files:**
- Modify: `NR_Kernel_Energy.lua`: `exerciseLag` or `lagged`; append `EX_LAG_GAIN`; refit `EX_LAG_TAU_D`.
- Modify: `test_satiety_activity.py` and `test_kernel_satiety_activity.py`.

**Interfaces:**
- Produces:
  - `K.energy.EX_LAG_GAIN`, a number.
  - `K.energy.lagged(L)`, which returns `EX_LAG_GAIN × max(L, 0)` for a finite L, and 0 otherwise.
  - `activityState`'s bypass ramp keeps raising the effective lag toward the whole exercise share (ruling 11c-32 amended). A bypassed share is not scaled by the gain.

- [ ] **Step 1: Write the failing tests.**

```python
def test_the_lag_plateaus_below_the_whole_share(host):
    E = host.K.energy
    L = 0.0
    for _ in range(24 * 7 * 24):                     # 24 weeks of hours at a steady 300 kcal/d of exercise
        L = E.exerciseLag(L, 300.0 / 24, 1.0)
    share = E.lagged(L) / 300.0
    assert 0.53 / 1.1 <= share <= 0.89 * 1.1         # S1320's DLW reading: 53-89 % of achieved expenditure
```

  - Re-fit the Whybrow replay so that the days 3–16 mean is about 0.30, within 1.5× (S1318).
  - Add `test_e_mechanic_at_24_weeks`: the share at 24 weeks lies within 0.53–0.89, cited to S1320 and the review's reading of Martin 2019 Table 2.
  - Keep King 2011 steady state, Karl and the ramp unit tests.

- [ ] **Step 2: Run the tests and watch them fail.** Expected: the unit lag reads about 1.0 at 24 weeks.

- [ ] **Step 3: Change the kernel.**
  - Append `K.energy.EX_LAG_GAIN = 0.7 -- game choice, Plan 11d (ruling 11d-4): the plateau share, the middle of S1320's 53-89 % (DLW, 24 weeks); S1516's self-report pool reads about 0 and is weighted lower`.
  - Apply the gain in `lagged`.
  - Refit `EX_LAG_TAU_D`, near 16 d, so Whybrow's days 3–16 hold. Update its comment to name both readings.

- [ ] **Step 4: Run both oracle files and the kernel suite,** each in its own call. All must pass.

- [ ] **Step 5: Mutation pass, on a scratch copy.** Each of these must fail a test:
  - the gain × 1/0.7 (back to unit);
  - the gain × 0.5;
  - τ × 2;
  - τ × 0.5;
  - the gain applied to the bypassed share.

- [ ] **Step 6: Run the gates and commit.**
  - The same gates as Task 1.
  - Commit: `git commit -m "Energy: the exercise lag plateaus at a gain below one (Plan 11d Task 2, ruling 11d-4)" -- <files>`

---

### Task 3: The sleep-debt hunger factor (C2) — Opus implementer, Opus reviewer

**Files:**
- Modify: `NR_Kernel_Satiety.lua`. Append `SLEEP_MAX`, `SLEEP_DEBT_FULL_H` and `K.satiety.sleepFactor(debtH)`.
- Test: `testing/tests/kernel/test_kernel_satiety_physiology.py` (unit) and `test_satiety_meal_studies.py` (replay).

**Interfaces:**
- Consumes: the meaning of `record.acute.debtH` in game hours. Read `NR_Kernel_Acute.lua` around :192, :411–:432 and :480.
- Produces: `K.satiety.sleepFactor(debtH) -> number ≥ 1`. It is 1 at a debt of 0 or less, or a non-finite debt. It is `1 + SLEEP_MAX × clamp(debtH / SLEEP_DEBT_FULL_H, 0, 1)` otherwise.

- [ ] **Step 1: Write the failing tests.**

```python
def test_sleep_factor_shape(host):
    S = host.K.satiety
    assert S.sleepFactor(0) == 1 and S.sleepFactor(-3) == 1 and S.sleepFactor(float("nan")) == 1
    assert S.sleepFactor(S.SLEEP_DEBT_FULL_H) == 1 + S.SLEEP_MAX
    assert S.sleepFactor(10 * S.SLEEP_DEBT_FULL_H) == 1 + S.SLEEP_MAX
    assert S.sleepFactor(S.SLEEP_DEBT_FULL_H / 2) == 1 + S.SLEEP_MAX / 2
```

  - **Replay (`test_satiety_meal_studies.py`).** Take a character at the request level, 0.25, after one short night that the acute kernel books as a full debt. At the request, the written hunger rises by S1284's +13.4 mm, within 1.5×. Under the 11c-31 mapping, the implied next-day intake ratio, 650 kcal × hunger / 0.25 summed over the day's meals, lies within 1.10–1.19 (S1284 +252.8 kcal/d, S1565 +204 kcal/d, on an assumed 2,000 kcal day). That day is a labelled assumption.

- [ ] **Step 2: Run the tests and watch them fail.**

- [ ] **Step 3: Implement the factor.** Append it with one statement per line. Both constants are labelled game choices citing S1284, S1565, S1564 and S1567 (it reverses with recovery).
  - `SLEEP_DEBT_FULL_H` is the debt the acute kernel books for one night at ≤ 5.5 h. Read that off its accounting and state the derivation.
  - The comment names that a step against a graded rise is not settled (S1568, S1282).

- [ ] **Step 4: Run the tests and the kernel suite.**

- [ ] **Step 5: Mutation pass, on a scratch copy.** Each of these must fail a test:
  - `SLEEP_MAX` × 2;
  - `SLEEP_MAX` × 0.5;
  - the clamp removed;
  - a non-finite debt passed through.

- [ ] **Step 6: Run the gates and commit:** `"Satiety: a sleep-debt hunger factor (Plan 11d Task 3, ruling 11d-2)"`.

---

### Task 4: The diagnostic replays — a 36 h fast, and six meals against three (C3) — Opus implementer, Opus reviewer

**Files:**
- Modify: `testing/tests/kernel/test_satiety_meal_studies.py`. This task makes no mod change.

- [ ] **Step 1: Write the two replays as pinned readings.**
  - **The 36 h fast (S1613, S1614).** Replay a 36 h fast through the full kernels, with `activityState` as the energy state, glycogen through `K.energy`'s path and the deficit floor. Then replay the next day's meals at the request level, under the 11c-31 intake mapping.
    - Report the next-day intake ratio against a fed control day; the study reads 12.2/10.2 MJ, which is 1.20.
    - Report day 3's ratio; the study reads 1.0.
    - Pin both model values to 3 decimals.
    - Assert only the direction: the next day is above 1, and day 3 is below day 2.
  - **Six meals against three (S1608, S1607).** At equal daily energy, the mean hunger AUC ratio. The study reads 1.14, and the vote count is null. Pin the model's value, and assert it lies within [0.9, 1.3].
  - **Glycogen (C9).** In the fast replay, log `g` and the glycogen term's contribution to the energy state. Pin `g` at 36 h, and state in the docstring whether a low-carbohydrate day runs `g` down.

- [ ] **Step 2: Run them.** A pinned value that falls outside its stated study reading is reported as a finding for ruling 11d-3, never patched.

- [ ] **Step 3: Mutation pass.** `DEFICIT_FLOOR` × 2 and the glycogen term removed must each change a pin.

- [ ] **Step 4: Commit:** `"Oracle: the 36 h fast and six-against-three meal replays pinned (Plan 11d Task 4, ruling 11d-3)"`.

---

### Task 5: The protein fullness spike, then the term if it holds (C5) — Opus implementer, Opus reviewer

**Files:**
- Spike: a scratch copy only, under the scratchpad at `11d-t5/`.
- Ship only if Step 3 passes:
  - modify `NR_Kernel_Satiety.lua` or `NR_Kernel_Stomach.lua` (the fill path);
  - modify `test_satiety_meal_studies.py` and `test_kernel_satiety_physiology.py`.

**Interfaces:**
- Produces, if shipped: `K.satiety.PROTEIN_FILL`, a number, and a fill that reads the satiety mass plus `PROTEIN_FILL × (protein grams in the solid lane)` against `CAPACITY_MAX_G`. `satietyMass`'s callers are unchanged. `fill`'s signature is unchanged; the stomach is passed in.

- [ ] **Step 1: The spike.** In scratch, add the protein term to F and grid `PROTEIN_FILL` jointly with `FULL_WEIGHT`. P_REQ and STEEP may be refit only if the grid needs them.

- [ ] **Step 2: The targets.**
  - The protein contrast (30 % against 10 % protein at 400 kcal, mean over 240 min) reads at least 0.0125, half the 0.025 target, and at most 0.04 (S1222, S1380, S1383; mapping 11c-31).
  - Every hard replay stays within 1.1×.
  - Marmonier's differences stay within 1.5×.
  - S1233 stays within 1.15×.
  - Whey against carbohydrate (S1384, null) is checked and reported, never asserted.

- [ ] **Step 3: The decision.**
  - **If one configuration meets every target**, ship it. Write the unit and oracle tests, pin the protein contrast, run the mutation pass (`PROTEIN_FILL` × 2, × 0.5, and 0), and commit `"Satiety: protein fills while it is in the stomach (Plan 11d Task 5, ruling 11d-5)"`.
  - **If none does**, ship nothing. Report the best configuration's worst ratio. Protein stays a named non-reproduction (#3622), and the report says so.

---

### Task 6: The adapters, the limitation and the golden (C1–C5 wired) — Opus implementer, Opus reviewer

**Files:**
- Modify: `mod/.../server/NR_Server_Writer.lua`:
  - `W.satiety`'s composition and seed;
  - LIMITATION_FOUR, appended;
  - its test copy in `test_writer_shape.py`.
- Modify: `NR_Server_Metabolism.lua`, only if C4's gain needs an adapter change. Expected: none, because the kernel applies it.
- Re-record: `testing/tests/kernel/golden/trace-1.0.0.json`.
- Extend: the workspace `bench_11d.py`.

**Interfaces:**
- Consumes:
  - `K.satiety.sleepFactor(debtH)` (Task 3);
  - `ACUTE_DECAY_HALF_LIFE_H` (Task 1);
  - `EX_LAG_GAIN` (Task 2);
  - `PROTEIN_FILL` (Task 5, if shipped).
- Produces: the written hunger `min(0.69, hungerTarget(sated(F, post(P)), es) × circadian(h) × acuteFactor(S) × sleepFactor(debtH))`. Its seed inverse divides by the same three factors, with a guarded divisor.

- [ ] **Step 1: Write the failing writer tests.**
  - A record with `acute.debtH` at full debt writes hunger × (1 + SLEEP_MAX), capped at 0.69.
  - The seed writes back the read HUNGER with debt > 0, at two clock hours, with S > 0.
  - A non-finite `debtH` reads factor 1.
  - LIMITATION_FOUR names the new clauses below.

- [ ] **Step 2: Wire the sleep factor** into the composition and the seed. Read `debtH` from `record.acute`. Leave the rest as it is.

- [ ] **Step 3: Append to LIMITATION_FOUR** these clauses, keeping its count rule:
  - "hunger rises after short sleep by a factor capped at the pooled size, whether a step or graded is unsettled";
  - "heat's lowering of intake is not modelled (cold reaches hunger through its expenditure)";
  - "sugary drinks, ketosis, alcohol's aperitif effect, aerated foods' volume and eating rate are neutral";
  - "injury adds no expenditure".

- [ ] **Step 4: Run the changed tests, then the kernel suite.**

- [ ] **Step 5: Re-record the golden** under "satiety revisit".
  - Walk the leaves.
  - Attribute every moved leaf to Task 1, 2, 3, 5 or the sleep wiring, using intermediate scratch re-records.
  - A leaf without a named cause is a stop.

- [ ] **Step 6: Cost, gates and commit.**
  - Bench one writer player-minute before and after.
  - Run every `mod/` gate and the full claims_check, and list the pointer findings.
  - Commit: `"Satiety revisit: the adapters, the limitation and the golden (Plan 11d Task 6)"`.

---

### Task 7: The jar reads — SICKNESS and NICOTINE_WITHDRAWAL on a 42.21 dedicated server (C7, C12) — Opus implementer, Opus reviewer (lane D)

**Files:**
- Modify: the `docs/facts/` page the reads belong to (`docs/facts/character-stats.md` for the stats). Check its line endings.
- Create: `.superpowers/sdd/2026-10-09-plan-11d-satiety-revisit/task-7-claims-delta.tsv`.

- [ ] **Step 1: Read the jar.** Use `C:\Users\Angus\pz-b42` and its `WORKSPACE.md`, with `./pz.sh grep|methods|refs|dump`, read-only.
  - What raises and lowers `CharacterStat.SICKNESS` and `NICOTINE_WITHDRAWAL` on 42.21: infection, zombification, colds, the smoker trait and its timers.
  - Whether each update runs on a dedicated server or client-side only.
  - Each claim takes the line it rests on.
- [ ] **Step 2: Write the facts sentences and a delta of provisional rows** `T11d07.n`, following [platform/jar-research](docs/platform/jar-research.md).
- [ ] **Step 3: Check and commit.**
  - Dry-run the delta, run page_lint on the page, and run `claims_check --staged --allow-provisional` (0).
  - Commit the page. The controller mints.
- [ ] **Step 4: Report.** Say whether a SICKNESS-driven appetite term (C7 (b)) or a NICOTINE_WITHDRAWAL hunger term (C12 (b)) is readable on the server. The answer feeds a later ruling, not this plan.

---

### Task 8: The pages and rows — Opus implementer, Opus reviewer (lane D, after Task 6)

**Files:**
- Modify: `docs/areas/body-effects.md#hunger-from-satiety` (CRLF).
- Create: `.superpowers/sdd/2026-10-09-plan-11d-satiety-revisit/task-8-claims-delta.tsv`.

- [ ] **Step 1: Write the status rows for the changed mechanisms.** Each claim and pointer is copied from HEAD, and each bound starts with the register's bound byte for byte.
  - #3616: the acute decay.
  - #3617: the lag gain and τ.
  - #3614: the composition with the sleep factor.
  - #3615 or #3613, if Task 5 shipped.
  - #3622: add the named neutrals of ruling 11d-6, and protein's outcome.
- [ ] **Step 2: Write the add rows.**
  - The sleep-debt factor.
  - The C3 replays' pinned readings, as a verdict row.
  - The design rule of ruling 11d-10: rule form T15-1, resting on #3617 and the S rows.
- [ ] **Step 3: Write the page sentences.** Each is byte-identical to its claim.
- [ ] **Step 4: Check and commit.**
  - Dry-run the delta, run page_lint, and run `claims_check --staged --allow-provisional` (0).
  - Commit the page. The controller mints.

---

### Task 9: The close (controller; Opus reviews)

- [ ] **Step 1: The whole-pass reviews.** Run two Opus reviews in parallel:
  - A: spec coverage and the oracles, with a mutation re-sample;
  - B: a line-level bug review.
- [ ] **Step 2: The fix wave.** Run one consolidated fix wave, then its re-review.
- [ ] **Step 3: The § 3 gates,** each in its own call. Write the pytest count into CLAUDE.md § 3 as "N passed on <date> at the Plan 11d close". Ledger the golden sha.
- [ ] **Step 4: Push and record.**
  - Push `main`.
  - Update the user-scope memory file and its index, and the project memory.
  - Append the 11d items to `.superpowers/sdd/2026-10-08-plan-11b-live-release/11c-amendments.md`. The live acceptance reads the sleep factor after a short night, the acute decay after chopping, and the lag over a week.
  - Ledger `Plan 11d: complete`.

---

## Self-Review

1. **Spec coverage.** Each of the memo's decisions maps to a task or ruling:

| Decision | Covered by |
|---|---|
| 1 (C1) | Task 1 |
| 2 (C2) | Task 3 and Task 6 |
| 3 (C3) | Task 4 |
| 4 (C4) | Task 2 |
| 5 (C5) | Task 5 |
| 6 (C6) | Task 6's limitation and Task 8's #3622 |
| 7 (C7) | Task 7 |
| 8 (C8, C9, C13, C14) | Task 6's limitation and Task 8 |
| 9 (C10) | Ruling 11d-8; no change |
| 10 (C11) | Ruling 11d-9; the 11b amendments in Task 9 |
| 11 (C15) | Ruling 11d-10, and Task 8's rule row |
| 12 (packaging) | Rulings 11d-11 and the one golden in Task 6 |

  - The memo addendum's eating-rate naming is in Task 6's limitation.
  - The withdrawal of protein damping the deficit drive needs no task.
  - S1334's supersede is in Task 0.

2. **Placeholders.**
   - The fitted constants (the decay of about 0.15, τ of about 16 d, `PROTEIN_FILL` and `SLEEP_DEBT_FULL_H`) are produced by their task's fit against stated targets. Each task gives the target band and the rows, never a bare "tune".
   - `<files>` in commit lines means exactly the task's **Files** list.

3. **Consistency.**
   - The composition in Task 6 uses the names Tasks 1–3 and 5 produce: `ACUTE_DECAY_HALF_LIFE_H`, `EX_LAG_GAIN`, `sleepFactor`, `PROTEIN_FILL`.
   - `lagged` keeps its signature.
   - `exerciseSuppression` keeps its signature.
