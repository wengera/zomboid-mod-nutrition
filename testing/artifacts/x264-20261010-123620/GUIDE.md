# `x264-20261010-123620` reading guide

**`x264-20261010-123620/density.json`**, **`MANIFEST.json`**, the ring pages **`minute-ring-admin-1.json`**, **`minute-ring-admin-721.json`** and **`minute-ring-admin-864.json`**, the replay's inputs **`start.json`**, **`start-stats.json`**, **`player.json`** and **`events.json`**, **`replay.json`**, and **`slot-p_00610064006d0069006e_a.json`** and **`_b.json`** — produced by `testing/experiments/x264_density.py` on `x26_meals_lib.py`, written at `b21c392` and edited at `c235fad` before the run (the pre-run edit: the drink arm moved to the start of the scenario while THIRST sat under the auto-drink gate, F-T4-2), unedited since; on HEAD `c235fad` (`TKX_StudyFoods` `77fcca7`; the same harness and `replay_live` commits; `mod/` not booted)
(302.0 s wall; `density.json` 162175 bytes, sha256 `8b739d0d…eed3006f`, byte-for-byte identical to the run copy; `MANIFEST.json` the same staged manifest, sha256 `5207b717…f246434c`). **Plan 11f Task 4, session 4**: the same build, fixture, client, staged copy and settings; free memory 16.76 GB before the boot; every verify row ok; `server_error_count` 1, the harness transient named under **Z**; `admin` not parked; no mod not found.

How to read it. As session 1. The eats landed at 11:15 (MARC, `TKX.Marc`, with 0.300 L of water drunk, `drinks[0]`: 61 sips over ring rows 64–66), 14:47 (MSOUP, `TKX.MarcSoup`), 17:18 (DLO, `TKX.Dense400Lo`) and 20:43 (DHI, `TKX.Dense400Hi`); the Task 4 report's "04:15" for MARC is wrong (the ring row 61 reads 11:15). The session never reaches the window close and the regrade injects no auto-drink, so the run's replay and the regrade agree.
- **R3REQ** (`verdicts.R3REQ.observed`): live = replay for MARC 208.04, MSOUP 147.00 and DLO 200.03 min; DHI 228.44 live against 229.29.
- **R3MEAN** (`verdicts.R3MEAN.observed`): the mean HUNGER over 180 min after the landing, live against the replay, MARC 0.19112 / 0.19111, DLO 0.18029 / 0.18023, DHI 0.19716 / 0.19705. MSOUP's 180 minutes run past DLO's landing (row 424, 151 min after MSOUP's), so its window is read from the regrade's `readings.means.arms.MSOUP`, cut at that landing: 0.18107 live and 0.18234 replayed over 150.99 min.
- **Marciani arms**, the replay with every arm removed and one at MARC's row 61 (`readings.marc_arms`, the regrade's alike): the 180-min mean HUNGER is 0.17398 after the soup and 0.19110 after the solid with 0.300 L of water, soup minus solid −0.01712, and the soup is never higher on any of the 179 rows.
- **Density arms**, at DLO's row 424 (`readings.dense_arms`): the 180-min mean 0.20065 for `TKX.Dense400Lo` and 0.22840 for `TKX.Dense400Hi`; the request 162.08 and 134.14 min.
- **REPLAY** (`verdicts.REPLAY.observed`): ok, HUNGER max 1.63e-4 over 810 rows; the regrade reads the same with `body.energyState` 6.08e-4.
- **The ring**: 3 pages, 873 rows from age 3.252 to 17.785; errors and overwritten 0.
- **Z**: no mod error line; `admin` not parked. The one `server_errors` line is the harness transient of `x261-20261010-120313`: `java.io.FileNotFoundException` on `testing/runs/x264-20261010-123620/server/Lua/pzt-cmd.txt`, being used by another process; not a mod error.

**Do not cite from this file:**

| Key | Value in the file | Why not |
|---|---|---|
| everything measured here, as a population | — | `n = 1` run, one fixture, one character, one host. |
| `session`, `predictions`, `deviations`, `world_changes`, `meta.phase_note`, `meta.staged_at`, `verdicts.*.predicted` | the driver's tables and text | Written before the run; not readings. |
| `profile`, `doctor`, `timeline`, `steps[*].epoch_ms_before`, `steps[*].epoch_ms_after` | settings, pre-run checks, walls | Not readings. |
| `phases.S.nutrition` calories, carbs, lipids, proteins, weight; `steps[*].ack` the same keys; `steps[*].ack.before`; `replay.inputs.player.macros`, `.weight`; `player.json` `macros`, `weight` | −11.27, −300, −70, −400; 80 | The vanilla Nutrition block under Nutrition false, not the mod's body. |
| `phases.W.lastWrite_before`, `phases.W.lastWrite` | epoch ms | Wall-clock stamps. |
| `phases.S.autodrink.after` | false | The setter's read-back; the flag does not hold (#2941). |
| `verdicts.R3MEAN.observed.MSOUP.live`, `.replay`, `.diff` | 0.17268; 0.17373; −1.06e-3 | The 180-min window spans DLO's landing; read the regrade's `readings.means.arms.MSOUP.live` and `.replay`. |
