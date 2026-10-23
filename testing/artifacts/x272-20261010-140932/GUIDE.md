# `x272-20261010-140932` reading guide

**`x272-20261010-140932/energy-2.json`**, **`MANIFEST.json`**, the ring pages **`minute-ring-admin-1.json`**, **`minute-ring-admin-721.json`**, **`minute-ring-admin-1441.json`**, **`minute-ring-admin-2161.json`** and **`minute-ring-admin-2504.json`**, the replay's inputs **`start.json`**, **`start-stats.json`**, **`player.json`** and **`events.json`**, **`replay.json`**, and **`slot-p_00610064006d0069006e_a.json`** and **`_b.json`** — produced by `testing/experiments/x272_fast.py` on `x27_energy_lib.py`, both written before the boot and committed at `1240988`, unedited since; on HEAD `1240988` (the same harness, `TKX_StudyFoods` and `replay_live` commits as session 1; `mod/` not booted)
(680.2 s wall; `energy-2.json` 587922 bytes, sha256 `ab2a50be…bf934a08`, byte-for-byte identical to the run copy; `MANIFEST.json` the same staged manifest, sha256 `5207b717…f246434c`). **Plan 11f Task 5, session 2 of the chain**: one boot of `x27-energy` on a copy of `x271-20261010-135751`'s whole `server/` folder (`chain.prev_run_id`, booted with reuse; `world_changes.restored`), the `admin` client a fresh restore of fixture `default`; the same build, staged copy and settings; free memory 17.04 GB before the boot; every verify row ok; `server_error_count` 0; `admin` not parked; no mod not found.

How to read it. As session 1. The store's record survived the restart: this session's replay starts from its own start record (`start.json`, gen 27, `satiety.t` 51.234), read after the boot, not from session 1's last slot line (gen 26, 49.201), so the offline gap between the two is not replayed. THIRST reads 0.11 on the ring's first row, the hypotonic cap of F-T5-1.
- **The fast** (`readings.fast_es.24`, `.36`): at 24 h (age 61.0, ring row s 635) the energy state reads 1.2585 live; at 36 h (age 73.0, s 1355) 1.3761. The replay values beside them are the run-time copy; read the grade's `row6_7.fast_log`.
- **The ladder** (`readings.ladder.<level>.live`): the energy state first reaches 1.1 (level 1) at age 52.256, 15.256 h after 20:00 on day 0, and 1.25 (level 2) at 59.892, 22.892 h after; 1.4 and 1.55 are not reached within the fast (they have no entry). The replay's 1.25 crossing is 59.945; the grade's fast arm reads 15.286 and 22.969 h.
- **Request-level day 2** (`stops[3]`, `stops[5]`, `stops[7]`): D2_08 reads es 1.3766 at age 73.067 and its request 836.78 kcal, eats 800 (`TKX.Mixed650` and three `TKX.Unit50`); D2_13 es 1.2750, request 828.75, eats 866.67; D2_20 es 1.1173, request 794.53, eats 800; day 2's intake 2466.67 kcal (`readings.live_kcal_by_day.2`), the carry out −24.41.
- **REPLAY** (`verdicts.REPLAY.observed`, `replay.diff`): from the start record at offset 7, ok over 2433 graded rows: HUNGER max 6.18e-4, `body.energyState` 2.11e-3, `satiety.L` 0; classes offline 5, between 22; no auto-drink found.
- **STOPS**: all 9 done, none missed or late, every eat landed. **The ring**: 5 pages, 2511 rows from age 50.418 to 92.251; errors and overwritten 0.
- **F** and **Z**: the flush landed on the first poll (slot gen 51 and 52, `satiety.t` 89.168 and 92.168); no mod error line, `server_errors` empty, `admin` not parked.

**Do not cite from this file:**

| Key | Value in the file | Why not |
|---|---|---|
| everything measured here, as a population | — | `n = 1` run, one fixture, one character, one host. |
| `session`, `predictions`, `meta.phase_note`, `meta.staged_at`, `verdicts.STOPS.predicted`; `deviations`, `world_changes` | the driver's tables and text | Written by the driver, not readings. |
| `profile`, `doctor`, `timeline`; `steps[*].epoch_ms_before`, `steps[*].epoch_ms_after` | settings, pre-run checks, walls | Settings and pre-run state, not readings; `steps[*].epoch_ms_*` are wall-clock stamps, never cited; a wildcard, checked at review under § 4.9. |
| `phases.S.nutrition` and `steps[3].ack` `calories`, `carbs`, `lipids`, `proteins`, `weight`, `incWeight`, `incWeightLot`, `decWeight`; `steps[i].ack.before` of the 22 `eat.action` steps; `replay.inputs.player.macros`, `.weight`; `player.json` `macros`, `weight` | −342.98, −57.07, 5.58, 20.99; 79.92 | The vanilla Nutrition block under Nutrition false, not the mod's body. |
| `phases.W.lastWrite_before`, `phases.W.lastWrite`; `replay.seconds` | epoch ms; 0.73 | Not game state. |
| `phases.S.autodrink.after`, `steps[5].ack.after` | false | The setter's read-back (#2941). |
| `readings.requests.<label>`, all 22 labels; `readings.hourly[i].es_replay`, `readings.meal_es[i].es_replay_next` | per-eat minutes; the run-time replay | Per-portion minutes, not row readings; the driver's replay copies (read the grade). |
| `chain.carry_in`, `chain.maint_kcal_in`, `chain.prev_*` (each key enumerated); `readings.maint_kcal`, `readings.maint_body` | −17.80; 2089.32; session 1's | Carried in from session 1's artifact, not read here. |
| `readings.live_kcal_by_day.1`, `.3` | 0.0; 0.0 | Partial chain days: day 1 began in x271, day 3 runs on in x273. Read the grade's `row6_7.intake_by_day.live`. |
