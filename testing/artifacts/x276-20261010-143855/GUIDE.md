# `x276-20261010-143855` reading guide

**`x276-20261010-143855/energy-6.json`**, **`MANIFEST.json`**, the ring pages **`minute-ring-admin-1.json`**, **`minute-ring-admin-721.json`**, **`minute-ring-admin-1441.json`**, **`minute-ring-admin-2161.json`** and **`minute-ring-admin-2770.json`**, the replay's inputs **`start.json`**, **`start-stats.json`**, **`player.json`** and **`events.json`**, **`replay.json`**, and **`slot-p_00610064006d0069006e_a.json`** and **`_b.json`** — produced by `testing/experiments/x276_sixmeals_fresh.py` on `x27_energy_lib.py` (at `1240988`), written after x273's death and before its own boot, committed at `228d26f` (14:38:44, eleven seconds before the run id's stamp), unedited since; on HEAD `228d26f` (the same harness, `TKX_StudyFoods` and `replay_live` commits; `mod/` not booted)
(533.6 s wall; `energy-6.json` 254678 bytes, sha256 `0824b8f1…34951dd5`, byte-for-byte identical to the run copy; `MANIFEST.json` the same staged manifest). **Plan 11f Task 5, research row 8 on a fresh fixture**: one boot of `x27-energy` on fixture `default`, not the chain; the same build, staged copy and settings, with no water stops; free memory 16.97 GB before the boot; every verify row ok; `server_error_count` 2, the harness transient twice (**Z**); `admin` not parked; no mod not found.

How to read it. As session 1. The driver's subclass marks the lib's budget and error events under other key names, so F-T5-2 cannot skip R, D and Z here; its docstring names the departure from the oracle: a one-afternoon warm-up (two `TKX.Mixed667`, Wm1_13 and Wm1_18 at 13:00 and 18:00 on day −1, 1333.33 kcal) against the oracle's three warm days. Day 0 is the live six-meal arm: one `TKX.Mixed333` at each of S0_0 to S0_5, 08:00, 10:30, 13:00, 15:30, 18:00 and 20:30 (landing on ring rows 1319, 1471, 1620, 1769, 1921 and 2073), 2000 kcal (`readings.live_kcal_by_day`). The three-`TKX.Mixed667` arm and the 24 h means are read from the grade's `rows.json` `row8`.
- **REPLAY** (`verdicts.REPLAY.observed`, `replay.diff`): from the start record (gen 1, `satiety.t` 4.069) at offset 7, ok over 2712 graded rows: HUNGER max 3.73e-4, `body.energyState` 1.19e-3, `satiety.L` 0; classes offline 5, between 8; no auto-drink found.
- **STOPS**: all 8 done, every eat landed. **The ring**: 5 pages, 2776 rows from age 3.250 to 49.501, past the window's end at 49.0; errors and overwritten 0.
- **F** and **Z**: the flush landed on the first poll; no mod error line; `admin` not parked. The two `server_errors` lines are the harness transient of `x261-20261010-120313` (`java.io.FileNotFoundException` on `testing/runs/x276-20261010-143855/server/Lua/pzt-cmd.txt`); not a mod error.

**Do not cite from this file:**

| Key | Value in the file | Why not |
|---|---|---|
| everything measured here, as a population | — | `n = 1` run, one fixture, one character, one host. |
| `session`, `predictions`, `meta.phase_note`, `meta.staged_at`, `verdicts.STOPS.predicted`; `deviations`, `world_changes` | the driver's tables and text | Written by the driver, not readings. |
| `profile`, `doctor`, `timeline`; `steps[*].epoch_ms_before`, `steps[*].epoch_ms_after` | settings, pre-run checks, walls | Settings and pre-run state, not readings; `steps[*].epoch_ms_*` are wall-clock stamps, never cited; a wildcard, checked at review under § 4.9. |
| `phases.S.nutrition` and `steps[3].ack` `calories`, `carbs`, `lipids`, `proteins`, `weight`, `incWeight`, `incWeightLot`, `decWeight`; `steps[i].ack.before` of the 8 `eat.action` steps; `replay.inputs.player.macros`, `.weight`; `player.json` `macros`, `weight` | −10.97, −300, −70, −400; 80 | The vanilla Nutrition block under Nutrition false, not the mod's body. |
| `phases.W.lastWrite_before`, `phases.W.lastWrite`; `replay.seconds`; `phases.S.autodrink.after`, `steps[5].ack.after` | epoch ms; 0.77; false | Not game state; the setter's read-back (#2941). |
| `readings.requests.<label>`, all 8; `readings.hourly[i].es_replay`, `readings.meal_es[i].es_replay_next` | per-eat minutes; the run-time replay | Not row readings; the driver's replay copies (read the grade's `x276.json`). |
| `chain.prev_run`, `chain.prev_prefix` | null | Not a chained session. |
| `readings.fast_es`, `readings.ladder`, `readings.fast_last_eat_age` | 1.0501 at 49.0; {} | Not a fast: the lib's fast-hour reads fall on the six-meal day. |
