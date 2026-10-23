# `scenario-20261004-184114` reading guide

**`scenario-20261004-184114/scenario-nutrition_3day_fast.json`** (the fast-off arm),
**`scenario-20261004-185129/scenario-nutrition_3day_gain.json`** (the gain-off arm) and
**`scenario-20261004-190146/scenario-nutrition_3day_fast.json`** (the fast-on control) — written by
`pzt scenario` at commit `afc42a9` with the working tree clean (harness and scenario Lua unchanged since the
2026-09-10 scenario runs' hardening), one run after another in one live window, each booting and tearing down
its own session after a clean `doctor`. Plan 1 Task 12: **X7** and **X41**. Profiles `x13-nutrition-off`
(`[sandbox] Nutrition = false`; its `[[verify]]` row read `SandboxVars.Nutrition` `false` on the server in
both off arms) and `x13-nutrition-on` (no sandbox block; the row read `true`); PZTestKit only, no other
mod. Every run: 73 hourly samples over 72.0 game-hours, `cadence.ticks_per_world_min 1.0` at 7.99
game-minutes per wall second and no `cadence_suspect` key, `server_errors` empty, no `STACK TRACE` line,
`client_quit rc=0`, `server_stopped rc=0 errors=0`. sha256 `8a4eab21…0254298b` (26 634 bytes),
`bc9487fd…ad63c6d2` (28 035 bytes), `b9504534…d0e9e` (31 783 bytes), each byte-for-byte identical to its
run copy. **Skew-free**: no driver; the three CLI runs replace the "thin driver" experiments.md's X7 row
proposed (a ruling of the task's amendments), and nothing in the harness was edited after them.

How to read them. `test.samples[k]` (k = 0–72) is the server's `Nutrition` object read once a game-hour —
`calories`, `carbs`, `lipids`, `proteins`, `weight`, `hunger`, `thirst`, `health`, `asleep`, `dead`,
`worldAge` — taken before hunger and thirst are re-pinned to 0, so each sample's hunger and thirst are one
game-hour's rise from 0. `test.log` holds the setup line (weight 80, every store 0) and, on the gain arm,
one `fed +2000` line per dose with the store before, after and asked; the doses are server-side
`setCalories` writes, not eats.

- **Fast-off** (`scenario-20261004-184114`): `calories`, `carbs`, `lipids`, `proteins` read `0` and
  `weight` `80` at all 73 samples, maximum deviation 0. Hunger about 0.034 and thirst about 0.0288 at each
  sample.
- **Gain-off** (`scenario-20261004-185129`): `calories` 2000 for samples 0–11, 3700 from sample 12 on (the
  second dose asked 4000 and the setter clamped it; the next four doses left 3700); between doses the store
  held to the last digit. The macro stores read `0` and `weight` `80` at all 73 samples: eleven game-hours
  at 2000 kcal and sixty at 3700, above the 1000-kcal gain threshold at 80 kg, with no weight movement.
- **Fast-on control** (`scenario-20261004-190146`): every store and weight moved from the first hour
  (calories −57.1, carbs −12.46, lipids −4.02, proteins −3.06, weight −0.00035 kg at sample 1); calories
  reached the −2200 floor and carbs the −500 floor; weight 80 → 78.574 kg, measured −1.426 against the
  evaluator's predicted −1.412, inside its 0.212 tolerance — the same four numbers as
  `scenario-20260910-055029`.

**Do not cite from these files:**

| Key | Value in the file | Why not |
|---|---|---|
| everything measured here, as a population | — | **`n = 1` run per arm**, one fixture, one player, one build. |
| `scenario-20261004-184114` `result`, `evaluation.within_tolerance` | `PASS`, `true` | Trivial: the fast scenario sets calories to 0, inside the weight model's dead band at 80 kg, so with the burn frozen the evaluator predicts 0 kg whatever `updateWeight` does. It is not evidence that the model holds; read `test.samples`. |
| `scenario-20261004-185129` `result`, `evaluation.within_tolerance`, `evaluation.predicted_delta_kg`, `evaluation.residual_kg`, `evaluation.predicted_kg_per_game_day` | `FAIL`, `false`, `2.878`, `−2.878`, `0.959` | The evaluator integrates vanilla's weight model as if `Nutrition.update` ran; with the option off it does not, so the prediction and the failure measure the evaluator's premise, not the game. The run's reading is the flat `test.samples`. |
