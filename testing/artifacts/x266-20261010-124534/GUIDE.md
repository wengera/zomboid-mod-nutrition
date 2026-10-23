# `x266-20261010-124534` reading guide

**`x266-20261010-124534/circadian.json`**, **`MANIFEST.json`**, the ring pages **`minute-ring-admin-1.json`**, **`minute-ring-admin-721.json`**, **`minute-ring-admin-1441.json`**, **`minute-ring-admin-2161.json`**, **`minute-ring-admin-2881.json`** and **`minute-ring-admin-3008.json`**, the replay's inputs **`start.json`**, **`start-stats.json`**, **`player.json`** and **`events.json`**, **`replay.json`**, and **`slot-p_00610064006d0069006e_a.json`** and **`_b.json`** — produced by `testing/experiments/x266_circadian.py` on `x26_meals_lib.py`, written before the boot and committed at `b21c392`, unedited since; on HEAD `c235fad` (`TKX_StudyFoods` `77fcca7`; the same harness and `replay_live` commits; `mod/` not booted)
(589.8 s wall; `circadian.json` 192826 bytes, sha256 `24f1fb37…ae6eea3e`, byte-for-byte identical to the run copy; `MANIFEST.json` the same staged manifest, sha256 `5207b717…f246434c`). **Plan 11f Task 4, session 6**: the same build, fixture, client, staged copy and settings; free memory 16.66 GB before the boot; every verify row ok; `server_error_count` 0; `admin` not parked; no mod not found.

How to read it. As session 1. Every eat is a `TKX.Mixed650`: W1 at the first request (13:59), then at 19:07 on days 0 and 1 (E19d0, E19d1) and 08:06 on days 1 and 2 (E08d1, E08d2), the admin awake throughout with sleep off. The session passes the 24 h window close at ring row 1491 (`replay.json` `rows[1439]`, age 28.12), so the replay's matches, the no-factor arm after it and the factor graded against the replay are read from `x26-regrade-20261010/x266.json`.
- **R5FAC**, the circadian factor (live HUNGER over the no-factor replay against 1 + A cos(2π(tod − PEAK_H)/24) at the writing drain's hour, A 0.085 and PEAK_H 19.8333 parsed from `NR_Kernel_Satiety.lua`): read the regrade's `readings.factor`: 2955 rows, max relative error 0.00125 (0.125 %), none over 1 %. The run's own `verdicts.R5FAC` reads falsified (max 15.2 %, 1519 rows over) by the tool's sleep factor; its `max_rel_replay` (2.2e-16, the replay's own factor against the formula) is unaffected.
- **R5REQ and the fixed meals** (`readings.fixed_meals.<meal>.live_return_min`, the live minutes to the next request): W1 252.27, E19d0 292.26, E08d1 289.52, E19d1 196.17, E08d2 244.01. The regrade's `readings.fixed_meals` reads the replay 252.27, 293.06, 289.52, 196.17 and 245.12 (all ok) and the no-factor replay 294.57, 315.42, 275.17, 228.08 and 225.50, with `es_before` 1.060, 1.039, 1.131, 1.158 and 1.168. The factor lengthens the 08:00 returns (+14.4 and +18.5 min against no factor) and shortens the 19:00 ones (−23.2 and −31.9).
- **Wake-up HUNGER** at 07:00 after a 19:00 dinner (`readings.wakes.<wake>.live`): 0.32795 on day 1 and 0.34386 on day 2; the regrade's replay reads 0.32766 and 0.34348 (`readings.wakes.<wake>.replay_hunger`).
- **The energy state**: `body.energyState` reads 1.003 on the first ring row (age 3.284) and 1.165 on the last (age 53.517) on this two-meal day; the Task 4 report's "1.04 to 1.17" is the `es_before` of the first and last meal.
- **REPLAY**: the run-time diff reads falsified, HUNGER over on 1519 of 2955 rows from ring row 1491; the regrade reads ok: HUNGER max 4.30e-4, `body.energyState` 1.26e-3, `satiety.L` and `satiety.P` 0, no auto-drink injected. The run's `replay.diff_extra` is ok as written.
- **The ring**: 6 pages, 3015 rows from age 3.284 to 53.517; errors and overwritten 0.
- **F** and **Z**: the flush landed on the first poll; no mod error line, `server_errors` empty, `admin` not parked.

**Do not cite from this file:**

| Key | Value in the file | Why not |
|---|---|---|
| everything measured here, as a population | — | `n = 1` run, one fixture, one character, one host. |
| `session`, `predictions`, `deviations`, `world_changes`, `meta.phase_note`, `meta.staged_at`, `verdicts.*.predicted` | the driver's tables and text | Written before the run; not readings. |
| `profile`, `doctor`, `timeline`, `steps[*].epoch_ms_before`, `steps[*].epoch_ms_after` | settings, pre-run checks, walls | Not readings. |
| `phases.S.nutrition` calories, carbs, lipids, proteins, weight; `steps[*].ack` the same keys; `steps[*].ack.before`; `replay.inputs.player.macros`, `.weight`; `player.json` `macros`, `weight` | −9.40, −300, −70, −400; 80 | The vanilla Nutrition block under Nutrition false, not the mod's body. |
| `phases.W.lastWrite_before`, `phases.W.lastWrite` | epoch ms | Wall-clock stamps. |
| `phases.S.autodrink.after` | false | The setter's read-back; the flag does not hold (#2941). |
| `verdicts.REPLAY.observed`, `verdicts.REPLAY.verdict`, `replay.diff`; `replay.json` `diff` | falsified; HUNGER 0.0702 over 1519 rows | F-T4-1; read the regrade's `regrade.diff`. |
| `verdicts.R5FAC.verdict`, `verdicts.R5FAC.observed.max_rel_live`, `.over_1pct`, `.over_n` | falsified; 0.1516; 1519 | The factor against the sleep-allowed replay; read the regrade's `readings.factor`. |
| `verdicts.R5REQ.verdict`; `verdicts.R5REQ.observed` and `readings.requests` `E08d1`, `E19d1`, `E08d2` `.replay_min`, `.diff_min`, `.tol_min`, `.ok`; `readings.fixed_meals` `E08d1`, `E19d1`, `E08d2` `.replay_return_min`, `.nofactor_return_min`; `readings.wakes.WAKE_d2.replay` | falsified; 205.77, 122.01, 174.46; 0.40530 | The sleep-allowed tool past the window close; read the regrade's `readings.requests`, `readings.fixed_meals` and `readings.wakes`. |
| `replay.json` `rows[1439]` to `rows[2964]` | ring rows 1491 to 3016 | The sleep-allowed replay past the window close. |
