# `x243c-20261007-163949` reading guide

**`x243c-20261007-163949/shootout.json`**, **`x243c-20261007-163949/MANIFEST.json`** and **`x243c-20261007-163949/gc.log`** — produced by `testing/experiments/x243c_shootout.py`, written before the boot and committed at `c23586a` with the profile `testing/profiles/x24-shootout-c.toml` before the run, unedited since, on HEAD `c23586a` (harness Lua `6af6595`, clean; harness Python `ed4ac93`; `mod/` not booted)
(918.2 s wall; `shootout.json` 1259797 bytes, sha256 `c93823c7…24e9c025`, `gc.log` 299987 bytes, sha256 `efdd82d9…a47f6f9e`; both byte-for-byte identical to the run copies, copied by the driver; `MANIFEST.json` sha256 `c86e295a…2415b389`). **Plan 10c Task H3 session c, N = 60 at the `DayLength` 4 spacing and under a fast clock.** Fixture `two`, Nutrition false, `DayLength` 1 in the profile; phase M set `time.multiplier 0.1674` live (the reply read the multiplier back as 0.7975, and `TK.H0.tpmSeen` was 37 ticks a game minute, 0.237 world minutes a wall second, `summaries.M`); phase FS set `settimespeed 30` (48.19 world minutes a wall second, `summaries.FS`) for the three fast arms; Z restored `settimespeed 1`. Every verify row ok; `server_error_count` 0; `admin` not parked; free memory fell to 0.55 GB. Phase order S0, M, I, `rr5`, `budget10`, `burst`, `drainTicks`, FS, `fastIdle`, `fastBudget10`, `fastBurst`, Z.

How to read it. As `x243a-20261007-160539`'s guide, with two baselines: the slow arms' `adds` are against `summaries.I`, the fast arms' against `summaries.fastIdle` (61 s each, about 610 frames, every frame a minute frame). At 37 ticks a game minute 1000 frames hold 27 or 28 minute frames, so a slow arm's minute-frame p99 is its max (`do-not-cite.csv`); the totals a game minute divide by those 27 or 28 frames. Deviation: the fast arms hold about 610 frames each (`summaries.fastIdle.frames`, `fastBudget10`, `fastBurst`), under H3's sizing rule of at least 1000 frames an arm. Each fast arm crossed the mod's 07:00 about twice.

| arm | busy p50 / p99 / max | minute busy p50 / max (n) | period p99 / max | longest window | adds: period p99, longest window | total a game minute over idle | starved / minute events | ghost ms a run |
|---|---|---|---|---|---|---|---|---|
| I | 1 / 5 / 18 | 3 / 14 (27) | 105 / 120 | 119 | — | (47.5 absolute) | — | — |
| rr5 | 1 / 14 / 20 | 13 / 20 (27) | 113 / 121 | 121 | 8, 2 | 0.6 | 0 / 28 | 0.896 |
| budget10 | 1 / 13 / 21 | 11 / 21 (28) | 112 / 120 | 121 | 7, 2 | 29.9 | 0 / 29 | 0.831 |
| burst | 1 / 50 / 60 | 48 / 60 (27) | 149 / 161 | 161 | 44, 42 | 24.5 | 0 / 29 | 0.794 |
| drainTicks | 2 / 7 / 11 | 4 / 11 (27) | 107 / 112 | 113 | 2, −6 | 43.2 | 0 / 29 | 1.107 |
| fastIdle | 6 / 16 / 47 | all 610 | 113 / 145 | 145 | — | (6.2 absolute) | — | — |
| fastBudget10 | 14 / 25 / 52 | all 610 | 116 / 138 | 138 | 3, −7 | 8.4 | 29715 / 623 (10.3 runs a run frame; 42.8 game minutes stale) | 0.854 |
| fastBurst | 48 / 67 / 76 | all 609 | 123 / 134 | 134 | 10, −11 | 43.1 | 0 / 623 | 0.767 |

- **The GC log**: 154 pauses, the largest 0.053 ms; 29 allocation stalls, the longest 274.56 ms, at 34.1 to 34.4 s of JVM uptime (`gc.events.25.up_ms` to `gc.events.57.up_ms`), during boot, before any arm (`summaries.<arm>.gc`).
- **Verdicts**: every one as predicted (TPM 37; FAST 610 of 610 minute frames; FB10 29715 starved).

**Do not cite from this file:**

| Key | Value in the file | Why not |
|---|---|---|
| everything measured here, as a population | — | `n = 1` run, one fixture, two characters, one host; ghost records are cost, not behaviour. |
| `session`, `predictions`, `constants`, `deviations`, `world_changes`, `meta.calibration_note`, `meta.cost_note`, `meta.timer_note`, `meta.staging`, `verdicts.*.predicted` | the driver's tables and text | Written before the run; not readings. |
| `summaries.I.busy_minute.p99`, `summaries.rr5.busy_minute.p99`, `summaries.budget10.busy_minute.p99`, `summaries.burst.busy_minute.p99`, `summaries.drainTicks.busy_minute.p99` | 14, 20, 21, 60, 11 | Nearest rank over 27 or 28 minute frames: the p99 is the max; read `.max`. |
| `summaries.*.n_eq_band`, `summaries.*.ghost_over_fed_calibration` | bands; ratios | Arithmetic on x242b's calibration, computed by the driver. |
| `phases.*.perf_read.avg`, `phases.*.perf_doc.avg`, `phases.*.perf_doc.samples_list.avg` | 3 to 8 | The engine's `avg-update-period` is no mean. |
| `phases.<arm>.ring_read` and `phases.<arm>.perf_read` (the bus replies, whole); the copies in `phases.<arm>.ring_doc` (`busy`, `period`, `endPeriod`, `over110`, `minuteFrames`, `minuteBusyMax`) and `phases.<arm>.perf_doc` (`max`, `samples`) where they differ from the summaries; `phases.<arm>.reset.before` and `phases.<arm>.stop.stats` (each listed in `do-not-cite.csv`) | the replies' summaries; the `ghost.stats` replies | The harness's own summaries over every sample or frame, the first window (begun before the arm) and the frames that overlapped a bus step included; `reset.before` is the load's first minute event, before the arm's window, and `stop.stats` counts past the arm's reads; read `summaries.<arm>` and `summaries.<arm>.ghost` (the frames themselves stay citable in `phases.<arm>.ring_doc.frames_list`, the windows in `phases.<arm>.perf_doc.samples_list`). |
