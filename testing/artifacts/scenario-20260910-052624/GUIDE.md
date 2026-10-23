# `scenario-20260910-052624` reading guide

**`scenario-20260910-052624/scenario-nutrition_3day_gain.json`** (run 1, the unwatered
attempt), **`scenario-20260910-054012/scenario-nutrition_3day_gain.json`** (run 2) and
**`scenario-20260910-055029/scenario-nutrition_3day_fast.json`** (run 3) — produced by
`pzt scenario` with the scenario file that landed at commit `707c878`, running on slice 03's
`752d748` harness (`harness.install` copies the mod from the working tree at boot; see
concern 5 of slice 04's task-3 report, in the SDD workspace, outside the tree). Slice 04's **fix round
1** and the test-layer hardening at `dd84a37` changed three things these files therefore
predate. **No measured number in them moves** — every rate is a fit against `worldAge` and
nothing in the changes touches sampling — and the evaluator was re-run against all three
offline, reproducing every stored key.

- **Every sample now carries `thirst`**, read the same way `hunger` is
  (`Stats:get(CharacterStat.THIRST)`). Absent from all three files. That absence is why run 1's
  health-drain attribution had to be settled on the jar rather than read off the trace: the run
  measured the drain's *rate* (−17.820 health per game-hour of world time, four consecutive
  full hours) but never sampled the stat it was keyed on.
- **A dead subject now fails the run** (`evaluation.dead_any` is no longer diagnosis only), and
  the evaluation carries `within_tolerance`, on a death `reason`, and — only when the last
  sample actually has a `thirst` value (`scenarios_nutrition.py:148-149`) — `thirst_end`. These
  files have none of those keys, and because none of them carries a `thirst` column at all (the
  bullet above), **re-evaluating these three can only ever add `within_tolerance`, plus `reason`
  on run 1**; `thirst_end` waits for a run made after the column landed.
  **Re-evaluated offline with the evaluator at HEAD: run 1
  `FAIL` (dead, and its residual was already outside tolerance either way), runs 2 and 3
  `PASS`, with every numeric key in the stored `evaluation` block reproduced unchanged** —
  `measured_delta_kg` / `predicted_delta_kg` / `residual_kg` / `tolerance_kg` of
  `1.073 / 2.688 / −1.615 / 0.403`, `2.526 / 2.551 / −0.025 / 0.383` and
  `−1.426 / −1.412 / −0.014 / 0.212`. So the stored `result` fields still stand as written.
- **The run report is now written before the artifact** and the artifact write is guarded, so a
  failure there costs the evidence file rather than the whole run. Immaterial to these three:
  all six files landed.

**Do not cite from `scenario-20260910-052624` (run 1):**

| Key | Value in the file | Why not |
|---|---|---|
| `evaluation.carb_drain_per_game_day` | `−300.3` | Whole-run fit. The subject died at game-hour 35 and `Nutrition.update` stops on a corpse, so the partial pre-death hour (h34→h35, a −9.57 carb step against a −12.59 full hour) is inside the window and the 37 dead hours contribute nothing. Over the alive window the same fit gives **−302.4 /game-day**, which is the figure that matches `0.0035 × 86 400` and the one runs 2 and 3 return over their whole traces. |
| `evaluation.calorie_burn_per_game_day` | `−1389.9` | Same contamination, same cause: **−1399.7 /game-day** over the alive window. |
| `evaluation.measured_delta_kg`, `measured_kg_per_game_day`, `weight_end_kg`, `calories_end`, `carbs_end`, `lipids_end`, `hunger_end`, `health_end` | `1.073`, `0.358`, `81.073`, `3700`, `−437.9`, `−141.4`, `0.7`, `0` | Corpse readings taken 37 game-hours after the stores stopped moving. The live model check on this run is the **alive window**: measured **+1.045 kg** vs predicted **+1.057** over 34 game-hours. |
