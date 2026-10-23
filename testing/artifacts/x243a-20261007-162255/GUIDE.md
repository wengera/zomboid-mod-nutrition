# `x243a-20261007-162255` reading guide

**`x243a-20261007-162255/shootout.json`**, **`x243a-20261007-162255/MANIFEST.json`** and **`x243a-20261007-162255/gc.log`** — produced by `testing/experiments/x243b_shootout.py`, written before the boot and committed at `da3fdcb` with the profile `testing/profiles/x24-shootout-b.toml` before the run, unedited since, on HEAD `da3fdcb` (harness Lua `6af6595`, clean; harness Python `ed4ac93`; `mod/` not booted)
(960.2 s wall; `shootout.json` 1347732 bytes, sha256 `089ab702…7f481c4d`, `gc.log` 339256 bytes, sha256 `9fd867bc…ec66b936`, both byte-for-byte identical to the run copies, copied by the driver; `MANIFEST.json` sha256 `c86e295a…2415b389`). **Plan 10c Task H3 session b.** The driver was made as a copy of `x243a_shootout.py` and kept its `PREFIX = "x243a"` and `PROFILE = "x24-shootout-a"`: the run id carries `x243a`, and the boot used `x24-shootout-a.toml`, whose content equals `x24-shootout-b.toml` but for its header comment and `description` (fixture `two`, the same staged copy, Nutrition false, `DayLength` 1, gclog on); `x24-shootout-b.toml` was committed and never booted. The arms, predictions and grading are session b's (`session`, `phases`, `verdicts`). Every verify row ok; `server_error_count` 0; `admin` not parked; free memory fell to 0.83 GB. Phase order S0, I, `burst20`, `drainTicks20`, `budget10_20`, `budget10_40`, `burst40`, `drainTicks40`, `shipped60`, Z.

How to read it. As `x243a-20261007-160539`'s guide (the same arm procedure, the same kept populations and `adds` against this session's own `summaries.I`), with N per arm in its name (18 and 38 ghost records at N = 20 and 40) and `shipped60` 70 s long (ruling 3: starvation only; its ring is kept but graded only for its minute events). The mod's 07:00 day close fell in `drainTicks40`, about 860 s into the session.

| arm | busy p50 / p99 / max | minute busy p50 / p99 / max | period p99 / max | longest window | adds: period p99, longest window | total a game minute over idle | starved / minute events | ghost ms a run |
|---|---|---|---|---|---|---|---|---|
| I | 1 / 8 / 15 | 3 / 14 / 15 | 107 / 114 | 115 | — | (11.8 absolute) | — | — |
| burst20 | 1 / 26 / 36 | 18 / 35 / 36 | 125 / 135 | 135 | 18, 20 | 14.3 | 0 / 165 | 0.897 |
| drainTicks20 | 4 / 10 / 15 | 5 / 14 / 15 | 108 / 115 | 115 | 1, 0 | 14.9 | 0 / 167 | 0.967 |
| budget10_20 | 1 / 16 / 21 | 12 / 20 / 21 | 116 / 123 | 123 | 9, 8 | 10.8 | 0 / 166 | 0.799 |
| budget10_40 | 8 / 15 / 40 | 11 / 22 / 40 | 115 / 139 | 139 | 8, 24 | 29.2 | 0 / 167 | 0.850 |
| burst40 | 1 / 41 / 51 | 32 / 48 / 51 | 141 / 151 | 151 | 34, 36 | 25.8 | 0 / 161 | 0.800 |
| drainTicks40 | 6 / 13 / 23 | 7 / 21 / 23 | 111 / 120 | 120 | 4, 5 | 27.9 | 88 / 166 | 0.859 |
| shipped60 | 2 / 7 / 16 | 3 / 11 / 16 | 107 / 117 | 117 | 0, 2 | 1.9 | 6180 / 116 | 1.427 (one ghost a batch: whole-ms truncation dominates) |

- **shipped60**: 4.26 ghost runs a minute event (494 over 116), 232 ticks yielded to the mod's own drain, 6180 queued ghost-minutes dropped, 53 of the 58 ghosts never ran, the longest 115.7 game minutes stale (`summaries.shipped60.ghost`).
- **The GC log**: 174 pauses, the largest 0.179 ms, at most 0.042 ms inside an arm; 36 allocation stalls, the longest 127.306 ms, at 34.2 to 34.6 s of JVM uptime (`gc.events.26.up_ms` to `gc.events.65.up_ms`), during boot, before any arm (`summaries.<arm>.gc`).
- **Verdicts**: I, F, B20, B40, LIN (1.78), SHIP, S, G and Z as predicted; Q falsified (drainTicks40's 88 starved ghost-minutes).

**Do not cite from this file:**

| Key | Value in the file | Why not |
|---|---|---|
| everything measured here, as a population | — | `n = 1` run, one fixture, two characters, one host; ghost records are cost, not behaviour. |
| `session`, `predictions`, `constants`, `deviations`, `world_changes`, `meta.calibration_note`, `meta.cost_note`, `meta.timer_note`, `meta.staging`, `verdicts.*.predicted` | the driver's tables and text | Written before the run; not readings. |
| `profile.name`, `profile.description` | `x24-shootout-a`, x243a's description | The profile booted by the driver's defect; this run is session b. |
| `summaries.*.n_eq_band`, `summaries.*.ghost_over_fed_calibration` | bands; ratios | Arithmetic on x242b's calibration, computed by the driver. |
| `phases.*.perf_read.avg`, `phases.*.perf_doc.avg`, `phases.*.perf_doc.samples_list.avg` | 3 to 8 | The engine's `avg-update-period` is no mean. |
| `phases.<arm>.ring_read` and `phases.<arm>.perf_read` (the bus replies, whole); the copies in `phases.<arm>.ring_doc` (`busy`, `period`, `endPeriod`, `over110`, `minuteFrames`, `minuteBusyMax`) and `phases.<arm>.perf_doc` (`max`, `samples`) where they differ from the summaries; `phases.<arm>.reset.before` and `phases.<arm>.stop.stats` (each listed in `do-not-cite.csv`) | the replies' summaries; the `ghost.stats` replies | The harness's own summaries over every sample or frame, the first window (begun before the arm) and the frames that overlapped a bus step included; `reset.before` is the load's first minute event, before the arm's window, and `stop.stats` counts past the arm's reads; read `summaries.<arm>` and `summaries.<arm>.ghost` (the frames themselves stay citable in `phases.<arm>.ring_doc.frames_list`, the windows in `phases.<arm>.perf_doc.samples_list`). |
