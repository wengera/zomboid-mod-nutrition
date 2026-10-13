# Exercise grading (C-2): each Fitness exercise billed at its own intensity — design

- **Status:** design approved by Angus, 2026-10-13. Decisions: "Approve" the design; bill the general/moderate intensity.
- **Source:** mechanism candidate C-2, Plan 11f (`docs/superpowers/research/2026-10-10-live-study-replays/04-mechanism-candidates.md`).
- **Spike:** `.superpowers/sdd/c2-exercise-grading/spike-report.md`. Its rows are in `c2-rows.tsv`.

## 1. Why
Since C-17 (Plan 11f), every minute while the server's exercise flag is set bills the flat `Fitness` class at 6.0 MET. A light stretch therefore costs the same calories, sweat, glycogen and exercise lag as burpees. The engine cannot tell the exercises apart either: its own server-side rate applies a flat 6.0 to every exercise (#2634).

## 2. Reading the exercise type on the server
- **Java cannot give it.** `getCurrentExe()` returns `Fitness$FitnessExercise`, whose `type` field has no getter (#2180, #2901). Reflection works only on a `-debug` server (#2736). The server's action stack is empty during a set (#2878).
- **The route.**
  - The client sends `ISFitnessAction`'s arguments by the parameter names of `new`, so `exeDataType` crosses the wire. Read: `NetTimedAction.set @58–@139 L44–L51`.
  - The server rebuilds the action through `ISFitnessAction.new` (#2932).
  - The server calls `serverStart` by a `rawget` that falls through to the class table. Read: `NetTimedAction.start @0–@57 L102–L110`, with `KahluaTableImpl.rawget @92–@122 L126–L127`.
  - The mod therefore wraps `ISFitnessAction.serverStart` and `serverStop` once, at file scope. The wrapper calls the original, then records `self.exeDataType` per username, cleared at stop and at departure. That is one call per set, with no per-tick work.
- **Never wrap `ISFitnessAction.new`.** A `function(self, ...)` wrapper has no named parameters, so the client sends no arguments and Fitness breaks for everyone. This is a platform lesson: it becomes a rule on `lessons.md` with its jar rows.
- **Trust.** The type is client-asserted, but it is the same string vanilla trusts for the set's reps and XP.
- **Fallback.** With no recorded type, the minute bills the flat 6.0, as today, and a counter records it. This covers a modded exercise, another mod replacing the wrapper, or a reconnect mid-set.

## 3. Billing
- **The table.** Add `K.energy.EXERCISE_MET`, keyed by type, from the 2024 Adult Compendium of Physical Activities (Herrmann 2024). Angus chose the general/moderate codes:

  | type | Compendium code | MET | match |
  |---|---|---|---|
  | squats | 02056 | 3.0 | named |
  | pushups | 02022 | 3.8 | named |
  | situp | 02022 | 3.8 | named |
  | burpees | 02020 (calisthenics, vigorous) | 7.5 | named |
  | barbellcurl | 02054 | 3.5 | approximate, a game choice |
  | dumbbellpress | 02054 | 3.5 | approximate, a game choice |
  | bicepscurl | 02054 | 3.5 | approximate, a game choice |

  Burpees take their own code, the only one for burpees. The choice between general and vigorous codes is labelled a game choice (Angus, 2026-10-13).
- **`billClass`.** While the exercise flag is set, a minute bills the recorded type's MET; with no type, it bills Fitness 6.0. Everything else C-17 built stays: the idle bill on a still fall, the Walking5kmh cap on a moving one, and the EPOC pool fed from the minute's exercise kcal.
- **The Strength-grant inference** in `NR_Server_Training` reads the real type first, and keeps the inference as its fallback.

## 4. The acute hunger suppression
Resistance work suppresses hunger regardless of load (S1508, S1509, S1301), and aerobic suppression has a relative threshold (S1305, S1302). So `W.vigorous` reads a Fitness set as resistance-vigorous from the exercise flag, before any MET test. Graded billing therefore never removes the suppression from a light set. The 6.0 bar stays for aerobic work.

## 5. Acceptance
- **Kernel tests** cover the table, the fallback and its counter, the wrapper's record and clear, and the flag-first vigorous test.
- **The refit.** Lower bills move exercise kcal, sweat, glycogen and the exercise lag, so the exercise-lag oracles and the replays that read an exercise set (x29, x35) are re-read. `EX_BYPASS_*` and the deficit oracles are re-checked with `tools/fit_deficit_drive.py`, and refit only if an oracle leaves its band.
- **The golden** is re-recorded under a named cause.
- **One live run** of all seven types:
  - the wrapper records each type;
  - the bill equals the table;
  - live equals the replay;
  - the client still shows the moodles.
- **Rule 6.** Add a stub-counting test: no added per-minute Java call.

## 6. Refactor (CLAUDE.md § 6)
- The activity-class table and `EXERCISE_MET` live together, as one data section in `NR_Kernel_Energy.lua`.
- The Fitness wrapper lives in one server file, with the existing Fitness hooks (training) next to it.

## 7. Risks
- The wrapper route is unproven live until the run.
- A mod that wraps `ISFitnessAction.new` breaks vanilla Fitness, not just ours. A mod that re-installs a `serverStart` wrapper can shadow ours, and then the fallback bills 6.0.
- The client asserts the type.
- The curl and press codes are approximate.
