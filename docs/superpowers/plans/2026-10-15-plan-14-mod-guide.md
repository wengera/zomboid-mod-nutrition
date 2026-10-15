# Plan 14: the Nutrition Revamp player guide — implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task by task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A player-facing interactive web guide to Nutrition Revamp: every system, how it differs from vanilla, what can and can no longer happen. Its charts compare vanilla with the mod using tested values, each value traced to its source.

**Architecture:**
- **Two generators.** A vanilla model (`tools/vanilla_model.py`) and a data generator (`tools/mod_guide_data.py`) build `docs/mod-guide/data.json` from three sources:
  - committed live artifacts;
  - offline replays of the mod's kernel (`tools/replay_live.py`'s `ServerReplay`);
  - the vanilla model, validated against new vanilla-baseline live runs.
- **The page.** A static page (`docs/mod-guide/index.html` with `charts.js`) reads only `data.json`.
- **The gate.** A `--check` gate keeps the page in sync with the mod.

**Tech stack:** Python 3 with lupa 2.8 (the kernel host), the existing harness `testing/pzt` with `testing/experiments/xlib.py`, HTML/CSS/JS with Chart.js from cdnjs, and the claude.ai Artifact tool.

**Spec:** `docs/superpowers/specs/2026-10-15-mod-guide-design.md`

## Global constraints
- The reader is players. The main text is plain; these terms appear only inside "The science" boxes: MET, FMI, kernel, fatDep, partition, oracle, and S-ids or #-ids (spec § 4.2).
- Every number on the page comes from `docs/mod-guide/data.json`. No number is typed into the HTML (spec § 3.1, § 4.1).
- Every series carries a badge from spec § 3.2's five, and provenance:
  - **artifact:** run id, file and JSON path, never a `docs/reference/do-not-cite.csv` key or a parent of one;
  - **kernel:** commit, script and inputs;
  - **vanilla model:** formula ids with their claim ids;
  - **study:** an S-id.
- Charts use the default sandbox options and a male character (`NR.SexSpecific` is off by default).
- Values are stored unrounded. They are rounded for display only, and the hover shows the stored value.
- The guide carries no register tags. Live readings and jar reads are minted as claims per CLAUDE.md § 4, in the commit that lands their evidence.
- CLAUDE.md §§ 3–6 govern everything:
  - pathspec commits;
  - § 5 live rules, including the controller-made detached launch for a session over 10 minutes after Angus approves it;
  - artifact commits with their row, guide and do-not-cite keys;
  - SDD process, rulings in the ledger.
- The page follows the `artifact-design` skill's contract, loaded before the page is written:
  - a 2–4 word title;
  - colour tokens on `:root` with the dark-mode blocks;
  - scripts from cdnjs only;
  - phone width with a 16px gutter.
- Out of scope: the Workshop description, the operator README, a modder guide, translation.

## File structure

| File | Responsibility |
|---|---|
| `docs/superpowers/research/2026-10-15-mod-guide/source-map.md` | every chart and promise mapped to its source, with gaps listed (Task 1) |
| `tools/vanilla_model.py` | vanilla hunger, thirst, the weight store and Strength experience as named, claim-cited formulas (Task 2) |
| `tools/tests/test_vanilla_model.py` | its tests and mutation cases |
| `tools/mod_guide_data.py` | the series schema, the provenance validators, the sources (artifact, kernel, vanilla, study), and `--check`/`--write` (Tasks 3, 4, 8) |
| `tools/mod_guide_series.py` | the series definitions, one function per chart, kept apart from the machinery (Tasks 4, 8) |
| `tools/tests/test_mod_guide_data.py` | schema, provenance, the do-not-cite guard, determinism and mutation tests |
| `docs/mod-guide/data.json` | the generated data (never hand-edited) |
| `testing/profiles/x44-vanilla.toml`, `testing/experiments/x44_vanilla_lib.py`, `x441_*.py`…`x444_*.py` | the vanilla-baseline profile, lib and drivers (Tasks 5, 6) |
| `docs/mod-guide/index.html`, `docs/mod-guide/charts.js` | the page and its chart layer (Tasks 9, 10) |

---

### Task 1: The source map (Opus, research; read-only except its report)
**Files:** Create `docs/superpowers/research/2026-10-15-mod-guide/source-map.md`.

- [ ] **Step 1: List every chart and table.**
  - Each of H1–H4 (spec § 2.1), each scenario S1–S6 (2 to 4 charts each) and each systems section (at most 2 charts each) gets a chart id, a title, axes, and the series it needs (vanilla and/or mod).
  - Keep the total at or below 40 charts.
- [ ] **Step 2: Map each mod series to its source.**
  - Prefer a committed artifact (`docs/reference/artifacts.md` lists every run with its reading guide).
  - Otherwise a kernel replay: name the inputs and the `ServerReplay` or kernel entry point in `tools/replay_live.py`, and the live run that shows the replay matches the game.
  - Otherwise a gap.
- [ ] **Step 3: Map each vanilla series.**
  - Use a measured row on `docs/facts/` (name the claim id), or the vanilla model with the formulas it needs, each with its claim id.
  - A formula with no claim is a jar read for Task 2: name the class and method with `C:\Users\Angus\pz-b42\pz.sh`.
- [ ] **Step 4: List every "can happen" and "no longer happens" promise.**
  - Collect the candidates from the operator README `mod/NutritionRevamp/README.md` and the area pages.
  - Give each its supporting claim or S-id. A promise with none is dropped or marked as needing a reading.
- [ ] **Step 5: Plan the vanilla-baseline sessions V1–V4 against the gaps** (spec § 3.4).
  - Give each its readings, game hours, DayLength, the harness commands from `docs/reference/harness-commands.md`, and its estimated wall time.
  - List any modded gap run.
- [ ] **Step 6:** Write the map as tables and return the gap list.

### Task 2: The vanilla model (Opus)
**Files:** Create `tools/vanilla_model.py` and `tools/tests/test_vanilla_model.py`. Modify `docs/reference/claims.tsv` (via a delta) only if a jar read is minted.

**Interfaces**
- **Produces:** `vanilla_model.simulate(scenario: dict) -> dict[str, list[tuple[float, float]]]`.
  - The scenario is `{"hours": float, "dt_min": float, "events": [{"t_h": float, "kind": "eat"|"drink"|"exercise"|"sleep", ...}], "start": {...}}`.
  - It returns named series in game hours: `hunger`, `thirst`, `weight_kg`, `calories_store`, `strength_xp`, `strength_level`.
- **Produces:** `vanilla_model.FORMULAS: dict[str, dict]`, each `{"claims": ["#NNNN", ...], "doc": str}`.

- [ ] **Step 1: Write failing tests**, each pinning a formula to the measured value its claim gives. Examples:
  - the passive hunger rise per game hour at the default DayLength;
  - the weight change per day from the calorie store's thresholds;
  - Strength experience per push-up rep.

  Read each value off its register row; never invent one.
- [ ] **Step 2: Implement the formulas** as small named functions, each citing its claim ids in `FORMULAS`.
- [ ] **Step 3: Make the tests pass.**
- [ ] **Step 4: Run the mutation pass** on a scratch `git archive` copy. Each formula changed by ±10 % fails a test.
- [ ] **Step 5: Mint any jar read** the source map named as a C row through a delta the controller applies (CLAUDE.md § 6).
- [ ] **Step 6: Commit** (pathspec).

### Task 3: The data machinery (Opus)
**Files:** Create `tools/mod_guide_data.py` and `tools/tests/test_mod_guide_data.py`. Modify CLAUDE.md § 3 to add the gate (spec § 5).

**Interfaces**
- **Produces:** the series schema.

  ```python
  SERIES = {"id": str, "chart": str, "label": str, "units": {"x": str, "y": str},
            "badge": "live"|"kernel"|"vanilla-live"|"vanilla-model"|"study",
            "points": [[x, y], ...],
            "provenance": {"kind": "artifact", "run": str, "file": str, "path": str}
                        | {"kind": "kernel", "commit": str, "script": str, "inputs": dict, "proof_run": str}
                        | {"kind": "vanilla-model", "formulas": [str], "claims": [str]}
                        | {"kind": "study", "science": str}}
  ```
- **Produces:**
  - `read_artifact(run, file, path) -> Any`, which refuses a do-not-cite key or a parent of one;
  - `build(series_defs) -> dict`;
  - the CLI `python tools/mod_guide_data.py --check|--write`.

- [ ] **Step 1: Write failing tests.**
  - the schema rejects a missing badge or provenance;
  - `read_artifact` refuses a do-not-cite key and a parent of one;
  - the output is deterministic (sorted keys, stable floats);
  - `--check` fails when one point differs.
- [ ] **Step 2: Implement.**
  - A kernel provenance records `git rev-parse HEAD` of `mod/`'s last commit (`git log -1 --format=%h -- mod`), so a mod change moves `data.json`.
  - JSON is written with `sort_keys=True` and `indent=1`.
- [ ] **Step 3: Make the tests pass.**
- [ ] **Step 4: Add the CLAUDE.md § 3 gate line** (spec § 5's paths).
- [ ] **Step 5: Commit.**

### Task 4: The series from existing evidence (Opus)
**Files:** Create `tools/mod_guide_series.py`. Generate `docs/mod-guide/data.json`. Extend the tests.

- [ ] **Step 1: One function per chart** in the source map whose sources all exist: artifacts, kernel replays, vanilla-model series from facts rows, and studies.
  - A kernel replay runs the mod's kernel at HEAD through `tools/replay_live.py` (`ServerReplay`) or the kernel host in `testing/tests/kernel/`.
  - Its `proof_run` names the live run that shows the replay matches.
- [ ] **Step 2: Test each series:**
  - non-empty;
  - its provenance resolves;
  - one value re-derived independently in the test from the artifact or a direct kernel call.
- [ ] **Step 3:** Run `--write`, then `--check`.
- [ ] **Step 4: Commit**, then run the full `claims_check` (the tool reads `repo:` paths only if it adds pointers; none expected).

### Task 5: The vanilla-baseline profile, lib and drivers (Opus; offline only)
**Files:** Create `testing/profiles/x44-vanilla.toml`, `testing/experiments/x44_vanilla_lib.py`, the drivers `x441_meal_fast.py`, `x442_one_food.py`, `x443_strength.py` and `x444_drinks.py`, and `testing/tests/test_x44_vanilla_lib.py`.

- [ ] **Step 1: The profile.**
  - The fixture `default`, with the mod not loaded (PZTestKit only) and `Nutrition = true`. This is the vanilla game.
  - DayLength and the multipliers come from the source map.
  - The profile names its own file (CLAUDE.md § 5).
- [ ] **Step 2: The lib.** It starts from `x43c_strength_lib.py` and uses `xlib.py`.
- [ ] **Step 3: The drivers**, each with:
  - its readings from the source map;
  - grades predicted by `vanilla_model.simulate` for the same events, each with an offline failing case;
  - pre-boot checks run offline against a real run layout.
- [ ] **Step 4: Commit before any boot.**

### Task 6: The vanilla-baseline sessions V1–V4 (Opus live; the controller launches any session over 10 minutes after Angus approves)
- [ ] **Step 1:** For each session:
  - run `pzt doctor`;
  - read and ledger free memory (12 GB gate);
  - run the driver in a foreground polling wait, or let the controller make a detached launch;
  - commit its artifact with its row, guide, do-not-cite keys and the `artifacts.md` re-anchor.
- [ ] **Step 2: Report each grade.** A model miss outside its band is a finding for Task 7, never re-run to make a number fit (CLAUDE.md § 5).
- [ ] **Step 3: Run any modded gap run** the source map lists, under the same rules, on the staged copy (`tools/release_pack.py stage`).

### Task 7: Validate the vanilla model (Opus)
- [ ] **Step 1:** Compare `vanilla_model.simulate` with V1–V4, quantity by quantity. Record each miss in `data.json`'s `validation` block: quantity, run, model value, live value, relative miss.
- [ ] **Step 2: Fix a formula only from a jar read**, never by fitting to the run. A miss with no jar cause is stated on the page as a limitation of that chart.
- [ ] **Step 3: Mint V1–V4's live readings** as M claims (a delta per CLAUDE.md § 4 and § 6; whole-delta review; the controller applies).
- [ ] **Step 4: Commit.**

### Task 8: The series from the new runs (Sonnet)
- [ ] **Step 1:** Add the vanilla-live series and the gap-run series to `tools/mod_guide_series.py`, with tests as Task 4 Step 2.
- [ ] **Step 2:** `--write`, `--check`, commit.

### Task 9: The page, At a glance and the Systems reference (Opus)
**Files:** Create `docs/mod-guide/index.html` and `docs/mod-guide/charts.js`.

- [ ] **Step 1:** Load the `artifact-design` skill and follow its contract (Global constraints).
- [ ] **Step 2: `charts.js`.**
  - `renderChart(el, chartId, data)` draws every series of that chart from `data.json`, with a vanilla/mod toggle when both exist, hover at full precision, and badges that open a provenance popover.
  - `fill(el, seriesId, pick)` writes a prose number.
- [ ] **Step 3: The At-a-glance section:** the table and H1–H4.
- [ ] **Step 4: The Systems reference.** Twelve sections, each with: Vanilla / This mod / charts / What can happen / What no longer happens / The science (a collapsed `<details>`).
- [ ] **Step 5: Back matter:** options, compatibility, limitations, references.
- [ ] **Step 6: Test.**
  - A headless check script `tools/tests/test_mod_guide_page.py` parses `index.html` and asserts:
    - every chart id and series id it references exists in `data.json`;
    - no digit run in the prose outside a `fill` target or a `<details>` box;
    - no forbidden term (Global constraints) outside `<details>`.
  - The digit rule exempts headings that name levels such as "level 10" only if listed in an allow-list in the test.
- [ ] **Step 7: Commit.**

### Task 10: The scenarios (Opus)
- [ ] **Step 1:** Write S1–S6 per spec § 2.2, charts from the source map, linking into the Systems anchors.
- [ ] **Step 2:** Extend the page test, then commit.

### Task 11: The reviews (Opus, read-only), one consolidated fix wave, re-review
- [ ] **Step 1: The fact-check review.**
  - Every sentence is checked against the register, the science register or `data.json`.
  - Every promise is checked.
  - Six series are re-derived from their sources.
  - The plain-language read.
  - The page renders: open it in a browser via the Artifact preview, or run a headless check if available.
- [ ] **Step 2:** One fix wave, then a scoped re-review.

### Task 12: Publish and close (controller)
- [ ] **Step 1:** Publish `docs/mod-guide/index.html` as a private artifact with `files` (`charts.js`, `data.json`). Give Angus the link.
- [ ] **Step 2:** Every § 3 gate, the full pytest in its own call, and CLAUDE.md (§ 3 baseline, the new gate, the router row "the player guide").
- [ ] **Step 3:** Update the memory files, push, and report.

## Self-review
- **Spec coverage:**

  | Spec section | Task |
  |---|---|
  | § 2.1 | 9 |
  | § 2.2 | 10 |
  | § 2.3 | 9 |
  | § 2.4 | 9 |
  | § 3.1 | 3, 4, 8 |
  | § 3.2 | 3 (schema), 9 (display) |
  | § 3.3 | 2, 7 |
  | § 3.4 | 1, 5, 6 |
  | § 3.5 | 4, 9 |
  | § 4.1–4.3 | 9, 12 |
  | § 5 | 3 |
  | § 6 | 2, 3, 9, 11 |
  | § 7 | Global constraints |

- **Types:** `simulate` (Task 2) is consumed in Tasks 5 and 7. The `SERIES` schema (Task 3) is consumed in Tasks 4, 8 and 9. `renderChart` and `fill` (Task 9) are consumed in Task 10.
- **Placeholders:** the chart list and the session designs are produced by Task 1, by design, because they depend on what evidence exists. Every later task reads them from the source map.
