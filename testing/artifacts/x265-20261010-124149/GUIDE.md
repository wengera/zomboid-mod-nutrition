# `x265-20261010-124149` reading guide

**`x265-20261010-124149/liquid.json`**, **`MANIFEST.json`**, the ring pages **`minute-ring-admin-1.json`** and **`minute-ring-admin-468.json`**, the replay's inputs **`start.json`**, **`start-stats.json`**, **`player.json`** and **`events.json`**, **`replay.json`**, and **`slot-p_00610064006d0069006e_a.json`** and **`_b.json`** — produced by `testing/experiments/x265_liquid.py` on `x26_meals_lib.py`, written at `77fcca7` and edited at `c235fad` before the run (the pre-run edit: the milk drunk first, while THIRST sat under the auto-drink gate), unedited since; on HEAD `c235fad` (`TKX_StudyFoods` `77fcca7`, which adds `TKX.MilkSolid`: 0.5 L of the fluid table's CowMilk as a food; the same harness and `replay_live` commits; `mod/` not booted)
(208.1 s wall; `liquid.json` 125222 bytes, sha256 `f407b3d3…87aabbea`, byte-for-byte identical to the run copy; `MANIFEST.json` the same staged manifest, sha256 `5207b717…f246434c`). **Plan 11f Task 4, session 5**: the same build, fixture, client, staged copy and settings; free memory 16.77 GB before the boot; every verify row ok; `server_error_count` 0; `admin` not parked; no mod not found.

How to read it. As session 1. The milk is 0.5 L of `CowMilk` in a WaterBottle drunk by `drink.action` (`drinks[0]`: 28 sips over ring rows 61–62, from 11:12); `TKX.MilkSolid` landed at ring row 289 (15:00). The session never reaches the window close and no auto-drink is found, so the run's replay and the regrade agree.
- **R4REQ** (`verdicts.R4REQ.observed`): the request 223.14 min after the milk's first sip row and 173.33 min after the solid's landing, live = replay for both.
- **R4LIQ** (`verdicts.R4LIQ.observed`): the liquid lane rose 325.14 and 123.09 g on the milk's two sip rows and −0.03 g on the solid's row; live within 0.11 g of the replay on 415 rows.
- **Swap arms** (`readings.swap_arms`): the solid at the milk's slot 224.10 min and the milk at the solid's slot 154.82, so liquid over solid is 0.996 at slot 1 and 0.893 at slot 2. No study band applies (ruling 11f-4).
- **REPLAY** (`verdicts.REPLAY.observed`): ok, HUNGER max 8.36e-5 over 415 rows; `body.energyState` 3.07e-4 in the regrade.
- **The ring**: 2 pages, 476 rows from age 3.201 to 11.117; errors and overwritten 0.
- **F** and **Z**: the flush landed on the first poll; no mod error line, `server_errors` empty, `admin` not parked.

**Do not cite from this file:**

| Key | Value in the file | Why not |
|---|---|---|
| everything measured here, as a population | — | `n = 1` run, one fixture, one character, one host. |
| `session`, `predictions`, `deviations`, `world_changes`, `meta.phase_note`, `meta.staged_at`, `verdicts.*.predicted` | the driver's tables and text | Written before the run; not readings. |
| `profile`, `doctor`, `timeline`, `steps[*].epoch_ms_before`, `steps[*].epoch_ms_after` | settings, pre-run checks, walls | Not readings. |
| `phases.S.nutrition` calories, carbs, lipids, proteins, weight; `steps[*].ack` the same keys; `steps[*].ack.before`; `replay.inputs.player.macros`, `.weight`; `player.json` `macros`, `weight` | −8.04, −300, −70, −400; 80 | The vanilla Nutrition block under Nutrition false, not the mod's body. |
| `phases.W.lastWrite_before`, `phases.W.lastWrite` | epoch ms | Wall-clock stamps. |
| `phases.S.autodrink.after` | false | The setter's read-back; the flag does not hold (#2941). |
