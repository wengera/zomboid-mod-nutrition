# `a_pipe_4-20261026-181848` reading guide

**`a_pipe_4-20261026-181848/a_pipe_4.json`** (with `state.log` and `a_grade_4.txt`) — produced by `testing/agent/drivers/a_pipe_4.py` at `driver_commit` `4b025035` (Plan 21b Task 1: gate_a4 …, a_pipe_4 and a_grade_4), unedited since, which imports the frozen `testing/agent/drivers/a_pipe.py`, `a_pipe_2.py`, `a_pipe_3.py` and `testing/experiments/xlib.py` (`preboot.xlib_commit` `45c49217`); on HEAD `4b025035` at the boot (`preboot.commit`; `preboot.harness_lua_commit` `ee23b53c`, `preboot.harness_lua_dirty` false; `preboot.harness_py_commit` `52a7de93`); the agent mod `testing/PZAgent/PZAgent` loaded by path from the tree (`profile.sources.PZAgent`; `preboot.agent_commit` `4b025035` is the last commit under `testing/agent` or `testing/PZAgent`; `preboot.driver_checks.agent_lua_dirty` false), and the last commit under `testing/PZAgent` is `942859f2` (Plan 21b Task 1 Lua: 20-square scan parts; vanilla classes index-checked before every action build), so the Lua under test is `PZAgent_Act.lua`, `PZAgent_Main.lua`, `PZAgent_Sense.lua`, `PZAgent_Link.lua` and `shared/PZAgent_Core.lua` at `942859f2`. Fixture `agent0` (`fixture.provision_run` `prov-20261026-102802`, `fixture.build` `42.21.0`; `hello.build` `42.21`); profile `testing/profiles/agent-nozombies.toml` (`profile.name` `agent-nozombies`; PZTestKit + PZAgent, `profile.sandbox.Zombies` 6, user `admin`).

**Plan 21b Stage A, pass 4 — the one pass beyond the stage's three-pass budget** (spec § 4.1's three: `a_pipe-20261026-101003`, `a_pipe_2-20261026-115846`, `a_pipe_3-20261026-130558`, `pass3_run`). Angus ordered it on 2026-10-26 after the agent harness report (`docs/superpowers/specs/2026-10-26-agent-harness-report.md` § 6, "run the go-with-changes boot"; ruling P21b-0 in `docs/superpowers/plans/2026-10-26-plan-21b-agent-harness-go-with-changes.md`). It is graded by `testing/agent/grades.py` `gate_a4`, never `gate_a`: the report's § 6 changes 1 and 3 redefine two of `gate_a`'s gates (the tick on the 60 Hz mean; motion as ack to the first position change), and `gate_a`'s output is carried by three committed files (`testing/artifacts/a_pipe-20261026-101003/a_grade.txt`, `a_pipe_2-20261026-115846/a_grade.txt`, `a_pipe_3-20261026-130558/a_grade.txt`), so it is frozen and never edited; `gate_a4` runs `gate_a` and replaces those two gates, keeping `scan15`, `gaps`, `lua_errors` and `hello` as `gate_a` reads them.

`preboot.doctor_clean` true; `preboot.lint_errors` empty; `server_error_count` 0; `admin_lua_error` false; `client_lua_errors` 0; `lua_errors` 0; `phase_errors` empty; `finished` true; `voided_legs` 0; `bus_dead` null; `notes` empty (no budget stop). Free memory 15.41 GB at the preboot read and the memory wait, 3.02 GB at ready, 16.63 GB after teardown (`memory`, `memory_wait`). 610.8 s wall (`wall_seconds`, against `constants.BUDGET_S` 800, ruling P21b-1; client quit rc 0, server stopped rc 0 with 0 errors, `timeline`).

Files, byte-identical to the run copy under `testing/runs/a_pipe_4-20261026-181848/`:

| File | Source | Bytes | sha256 |
|---|---|---|---|
| `a_pipe_4.json` | the driver's auto-copy of `testing/runs/a_pipe_4-20261026-181848/a_pipe_4.json` (`cmp` equal) | 146187 | `54d788b6732b64c43eb4b0c564c85b80410adb83ad06759f13a3b164e1817321` |
| `state.log` | `testing/runs/a_pipe_4-20261026-181848/clients/admin/Lua/pzagent/admin/state.log`, copied by the write-up (`cmp` equal; LF endings, 6351 lines, seq 1–6351 without a gap: 1 `hello`, 5895 `frame`, 395 `scanPart`, 40 `ack`, 20 `event`; the driver read 6308 of them, `lines_read`, the other 43 being frames after its last read) | 5358560 | `72a16a2f4fdf13570057a8c845e684929d1641c34703aa646e2a923d730770a5` |
| `a_grade_4.txt` | the controller's stdout of `python testing/agent/drivers/a_grade_4.py` over this run's `a_pipe_4.json` (the script exits 1 on NO-GO), copied from the run dir by the write-up (`cmp` equal); LF endings, a JSON object | 607 | `c25bc6c5635ac1c684a7e96a8c56253111b31633116c07621e7f88105906507d` |

`state.log` is the only evidence of the per-leaf costs in the rate-60 window, of each leg's path and of the first-change frames below; the hashes are of the working-tree bytes as written (re-hash a checkout's blob with `git show <commit>:<path> | sha256sum`). The client console `testing/runs/a_pipe_4-20261026-181848/clients/admin/console.txt` (269749 bytes; 0 hits of the driver's `constants.CLIENT_ERR_RX`), `server-stdout.log` (285038 bytes) and the logs under `server/` and `clients/` are per-machine and untracked, and nothing below rests on them.

## How to read it

The schedule is pass 3's (`a_pipe_3.py`'s docstring, unchanged by `a_pipe_4.py` but for the motion row's `first_move`): sit still; `rate 2`, `rate 5`, `rate 10` for 60 s each; `rate 60` for 30 s, then `rate 10` back; `scan 5`, `scan 10`, `scan 15` five times each, emitted in parts, one `scanPart` line per tick of at most **20** squares (`PZAgent_Sense.lua` line 225 `S.SCAN_SQUARES_PER_TICK = 20` at `942859f2`, against pass 3's 60); `goto` +10 tiles in x and back, ten round trips; three server `stats.all` calls; teardown (`phase_walls`: rates 85.469–265.931 s, rate60 to 296.169, scans to 304.173, motion to 596.893, server to 600.927). Scans and motion run at rate 10, a frame every 6 ticks: every one of the 2925 consecutive frame pairs inside the motion phase in `state.log` is 6 ticks apart, 91–107 ms (mean 100.0 ms) of client clock.

- **Rates:** `readings.rates.<2|5|10>`: `frames` (120, 300, 601 against `expected` 120, 300, 600), and per frame the client's `cost` leaves `pollMs`, `actMs`, `scanStepMs`, `senseMs`, `linkMs` and their sum `tickMs` (`constants.inherited_from_a_pipe_3.COST_KEYS`), each an integer read off a 1 ms clock (`getTimestampMs`); `dropped_max` 0 at every rate. Bytes written per minute (`state_bytes_end` − `state_bytes_start`): 88350 at 2 Hz, 220784 at 5 Hz, 442210 at 10 Hz (pass 3: 88372, 220794, 442252).
- **Rate 60:** `readings.rate60`: `frames` 1800 (`expected` 1800.0 for `window_s` 30.0), `tickMs` (each frame's sum of the five leaves), `tick_none` 0, `tick_sum` 1429, `wall_ms` 29976, `tick_mean_ms_at60` = `tick_sum / frames`; `back_ack` the `rate 10` restore.
- **Scans:** `readings.scans.<5|10|15>[*]` as in pass 3's guide: `scanId`, `parts`, `partNumbers`, `partStepMs` (each part's walk), `partEmitMs` (each part line's `emitMs`, which is the **previous** part's emit and flush, part 1's 0), `partBytes`, `partSquares`, `squares`, `bytes`, `missing`, `scanMs`, `scanTicks`, `scanMsPerTick`, `scanStepMaxMs`, and `scanEmitMs` (the last part's own emit, from the next frame). Tick *i* cost `partStepMs[i]` plus the emit it performed, `partEmitMs[i+1]`, with `scanEmitMs` for the last tick (`grades.part_emits`, `scan_part_tick_ms`); `scan15_ms_max` is the largest such tick over the five r=15 scans, and `scan15_latency_ms_max` (`scan_latency_ms`, ungraded) the walk's sum plus every emit.
- **Motion:** `readings.motion[*]` (20 legs, `trip` 0–9 with `dx` ±10, `cmdSeq` 21–40): `settled`/`settleMs`, `x0`/`y0`, `args`, `cmdSeq`, `ack`, `goal`, the void inputs (`at_send`, `at_end`, `min_health`, `max_nZombies`), **new:** `first_move` (`{seq, wallMs, x, y, readPyMs}`: the first frame with `seq` > `ack.seq` whose `hypot(x − x0, y − y0)` exceeds `constants.MOVE_EPS_TILES` 0.01 tiles, any direction), and beside it pass 3's `first_motion` (the first frame past `MOTION_EPS` 0.2 tiles in the commanded direction) and `cmd_motion_host_ms`. The graded figure is `grades.cmd_move_ms`: `first_move.wallMs` − `ack.wallMs`, both the client's clock; `grades.cmd_motion_ms` (`first_motion.wallMs` − `ack.wallMs`) is reported ungraded.
- **Server:** `readings.server[*]`: `rttMs` and the `stats.all` ack.
- **Pipe health:** `hello` (`mode` `append`, `rate` 5, `build` `42.21`), `missing` `[]`, `gaps` `[]`, `bad` 0, `lines_read` 6308, `events` `goal_done` 20 (the log's 20 `event` lines, all `goal_done`), no `goal_failed`.

## Verdicts

`a_grade_4.txt`, key by key: `verdict` **NO-GO**; `pass.tick_mean_at60` true, `pass.scan15` **false**, `pass.cmd_move_p90` true, `pass.gaps` true, `pass.lua_errors` true, `pass.hello` true. Readings: `tick_mean_ms_at60` 0.7938888888888889 on `tick60_frames` 1800; `scan15_ms_max` 7, `scan15_latency_ms_max` 117; `cmd_move_p90_ms` 195 on `cmd_move_n` 20, `cmd_move_paired` 20; `gaps` 0; `lua_errors` 0; `mode` `append`. Ungraded: `tick_p99_ms_at5` 2 on `tick_frames_at5` 300; `cmd_motion_p90_ms` 7629 on `cmd_motion_n` 20, `cmd_motion_paired` 20, `cmd_motion_voided` 0 (`cmd_motion_voided_reasons` `[]`).

**The NO-GO is `scan15` alone: `scan15_ms_max` 7 against `< 5` (`grades.SCAN15_MS`).** The five other gates passed. The budget held: `wall_seconds` 610.8 against `BUDGET_S` 800, the motion phase completed all 20 legs (`readings.motion` 20 rows, `cmd_move_n` 20; `notes` empty, so no `budget_stop`), and no leg was voided (`voided_legs` 0; every row `min_health` 100, `max_nZombies` 0).

1. **15-tile scan** (`scan15_ms_max` 7 against `< 5`, false; `scan15_latency_ms_max` 117, ungraded). The 20-square parts halved the mean tick against pass 3's 60-square parts and left the worst tick where it was, 7 ms: pass 3's projection (a 4.1–4.5 ms peak) did not hold (section 1).
2. **Tick cost on the 60 Hz mean** (`tick_mean_ms_at60` 0.794 against `< 1`, true; 1800 of 1800 frames). The 5 Hz p99 reads 2 as in passes 1–3 (ungraded). Every window's mean reads higher than pass 3's on the same Lua path (section 2).
3. **Command to first move** (`cmd_move_p90_ms` 195 against `< 500`, true; 20 of 20 paired). Every leg's first move came 110–220 ms after its ack; the directional reading, 7629, is the same detour pass 3 met (section 3).
4. **Plumbing** (`hello`, `gaps`, `lua_errors` true): section 4.

### 1. Scan cost: 20-square parts

Per r=15 scan (`readings.scans.15`; `max tick` the largest `partStepMs[i]` + the emit tick *i* performed; `emit sum` the emits over all ticks, which is `latency` − `scanMs`):

| scanId | parts | `scanMs` | emit sum | latency | max tick | the max tick (part: step + emit, its `partBytes`) | `bytes` |
|---|---|---|---|---|---|---|---|
| 11 | 49 | 31 | 86 | 117 | 7 | part 28: 2 + 5, 2726 B | 107234 |
| 12 | 49 | 23 | 81 | 104 | 6 | part 37: 2 + 4, 2402 B | 107233 |
| 13 | 49 | 23 | 80 | 103 | 6 | part 25: 2 + 4, 2361 B | 107233 |
| 14 | 49 | 27 | 86 | 113 | 5 | parts 30, 36: 1 + 4, 2103 and 2190 B | 107233 |
| 15 | 49 | 33 | 82 | 115 | 6 | part 15: 2 + 4, 2103 B | 107234 |

Every r=15 scan reads `parts` 49, `partNumbers` 1..49, `partSquares` 20 × 48 then 1, `squares` 961, `missing` `[]`; its full parts are 2102–3037 bytes (mean 2224, 111 B per square; the driver's re-serialised part lines) and its last 476–477. The r=5 scans (`scanId` 1–5: 7 parts, `squares` 121) read max ticks 7, 6, 4, 5, 6 and latencies 27, 34, 15, 20, 20; the r=10 scans (6–10: 23 parts, `squares` 441) max ticks 6, 5, 6, 4, 6 and latencies 56, 66, 61, 57, 61; every `missing` is `[]`.

**The ticks.** Over the 245 r=15 ticks (5 × 49) the per-tick cost reads 0 on 2, 1 on 41, 2 on 140, 3 on 36, 4 on 12, 5 on 10, 6 on 3, 7 on 1 (mean 2.25 ms); 14 ticks read 5 or more, and every scan holds at least one. Over the 240 full 20-square parts the walk reads 0 on 110, 1 on 124, 2 on 6 (mean 0.567 ms, 0.028 ms per square; pass 3: 1.09 ms a 60-square part, 0.018 per square) and the emit 1 on 114, 2 on 93, 3 on 21, 4 on 10, 5 on 2 (mean 1.72 ms; pass 3: 3.19 ms a ~6 KB part), so a part's tick averages 2.29 ms (pass 3: 4.3). The worst tick is a 2 ms walk beside a 5 ms emit of a 2.7 KB part (scanId 11, part 28); 4 ms emits occur on parts of 2.1–2.2 KB as well (scanId 14, parts 30 and 36). The peak sits about 4.7 ms above the mean tick (7 − 2.29), against the 2.7 ms margin pass 3's projection assumed (`a_pipe_3-20261026-130558/GUIDE.md` § 1), so pass 3's projected 4.1–4.5 ms peak for a 20-square part did not hold: the mean fell, the tail did not. The scan's total emit grew: 80–86 ms over 49 lines an r=15 scan, against pass 3's 47–55 ms over 17 (latency 103–117 against 61–75).

**Emit per KB, re-derived from this run's parts.** Over every part of every scan (395 parts: 35 at r=5, 115 at r=10, 245 at r=15), each part's bytes (`partBytes[i]`) against the emit its own tick performed (`partEmitMs[i+1]`, or `scanEmitMs` for the last part), both a least-squares fit and a table:

- the fit: `emit ≈ 0.18 + 0.751 × KB` ms; through the origin **0.829 ms per KB**; over the 380 parts above 1 KB the summed emit over the summed bytes is 0.826 ms per KB. Per radius, summed emit over summed KB: r=5 1.014, r=10 0.891, r=15 0.774. The parts span only 0.39–3.35 KB and 225 of 395 sit within 1.75–2.25 KB, so the fit's slope and intercept are weakly separated, and the table is the reading;
- the table (parts binned by KB, mean emit ms): 0.25–0.75 KB, 15 parts (the 1-square last parts), 0.73; 1.75–2.25 KB, 225 parts, 1.73; 2.25–2.75 KB, 114 parts, 2.05; 2.75–3.25 KB, 36 parts, 2.44; 3.25–3.75 KB, 5 parts, 3.20. Over the r=15 full parts alone: 2102–2103 B, 160 parts, 1.67 ms (max 4); 2104–2499 B, 50 parts, 1.76 (max 4); 2500 B and over, 30 parts, 1.93 (max 5).

Against pass 3's 0.495 ms per KB through the origin (`0.51 + 0.418 × KB` over 0.38–8.54 KB parts): a 2.1 KB part's emit reads 1.67 ms here, where pass 3's line predicts about 1.39; a third of a 60-square part's bytes costs about half its emit. The per-KB figure through the origin is higher at small parts because a per-line cost does not shrink with the part, and every window of this run also reads its frame cost higher than pass 3's (section 2), which this run cannot separate from the emit.

### 2. The tick cost

Per key by window (frames, 1 ms clock; nearest-rank percentiles, `grades.pct`; counts are ms: frames):

| Window | Key | p50 | p99 | max | mean | counts | pass 3 mean |
|---|---|---|---|---|---|---|---|
| 2 Hz (120 of 120) | `tickMs` | 1 | 3 | 4 | 1.017 | 0:29 1:64 2:24 3:2 4:1 | 0.792 |
| 5 Hz (300 of 300) | `pollMs` | 0 | 1 | 1 | 0.247 | 0:226 1:74 | 0.163 |
| 5 Hz | `actMs` | 0 | 0 | 1 | 0.003 | 0:299 1:1 | 0 |
| 5 Hz | `scanStepMs` | 0 | 0 | 0 | 0 | 0:300 | 0.003 |
| 5 Hz | `senseMs` | 0 | 1 | 1 | 0.170 | 0:249 1:51 | 0.147 |
| 5 Hz | `linkMs` | 0 | 1 | 2 | 0.357 | 0:194 1:105 2:1 | 0.227 |
| 5 Hz | `tickMs` | 1 | 2 | 3 | 0.777 | 0:108 1:152 2:39 3:1 | 0.540 |
| 10 Hz (601 of 600) | `tickMs` | 1 | 2 | 5 | 0.705 | 0:265 1:255 2:76 3:4 5:1 | 0.552 |
| 60 Hz (1800, 30 s) | `pollMs` | 0 | 1 | 6 | 0.281 | 0:1303 1:492 2:4 6:1 | 0.159 |
| 60 Hz | `actMs` | 0 | 0 | 1 | 0.003 | 0:1794 1:6 | 0.002 |
| 60 Hz | `scanStepMs` | 0 | 0 | 2 | 0.004 | 0:1794 1:5 2:1 | 0.002 |
| 60 Hz | `senseMs` | 0 | 1 | 2 | 0.167 | 0:1505 1:290 2:5 | 0.106 |
| 60 Hz | `linkMs` | 0 | 1 | 2 | 0.339 | 0:1198 1:594 2:8 | 0.213 |
| 60 Hz | `tickMs` | 1 | 2 | 7 | **0.794** | 0:686 1:811 2:295 3:7 7:1 | 0.482 |

The 2, 5 and 10 Hz rows are read off `readings.rates.<r>.<key>`; the 60 Hz per-leaf rows are read off `state.log` (the 1800 frames between `readings.rate60.frame_wallMs_first` and `frame_wallMs_last`, whose per-frame sums equal `readings.rate60.tickMs` element for element); the artifact carries only the sum. The pass 3 column is `a_pipe_3-20261026-130558/GUIDE.md` § 2.

**The gate.** `gate_a4`'s `tick_mean_at60` grades `readings.rate60.tick_mean_ms_at60` < 1 ms (`grades.TICK_MEAN_MS_AT60`) on at least 0.9 of `expected` frames: `tick_sum` 1429 over `frames` 1800 is **0.794 ms**, in `wall_ms` 29976 of client clock (60.05 frames a second; all 1799 consecutive pairs one tick apart, so every tick built a frame); population SD 0.734, standard error of the mean 0.017 ms. It passes. As pass 3's guide § 2 sets out, the mean resolves the average of the five measured spans on a frame-building tick to a few hundredths of a millisecond, and resolves no single tick and no tail; the rate-60 window's one 7 ms frame is a 6 ms `pollMs` beside a 1 ms `linkMs`.

**The 5 Hz p99, ungraded.** 39 of 300 frames read 2 and one reads 3, so the p99 is 2 (`tick_p99_ms_at5` 2), which `gate_a`'s `< 2` would fail as in passes 1–3.

**Against pass 3.** Every window's mean reads 0.15–0.31 ms higher (2 Hz 1.017 against 0.792; 5 Hz 0.777 against 0.540; 10 Hz 0.705 against 0.552; 60 Hz 0.794 against 0.482), and at 60 Hz the rise is spread over `pollMs` (+0.12), `linkMs` (+0.13) and `senseMs` (+0.06). Between pass 3's Lua (`f00c9674`) and this run's (`942859f2`) only `PZAgent_Act.lua` and `PZAgent_Sense.lua` changed (`git diff --stat`): the sense frame's timed-action queue read is index-checked (`S.frame`), and the scan constant; `PZAgent_Main.lua` and `PZAgent_Link.lua`, which hold the poll and the flush, did not change. This run does not separate a Lua cost from the host's state; it reads the same pipe about 0.3 ms a frame tick slower than pass 3 did, and still under the 1 ms gate.

### 3. The motion legs

Per leg (`readings.motion[*]`; `first change` the first frame after the ack whose position differs from (`x0`, `y0`) at all, read off `state.log`, as frame `tick` − `ack.tick`, frame `wallMs` − `ack.wallMs`, and its displacement; `first_move` the graded frame, `first_move.wallMs` − `ack.wallMs` (`grades.cmd_move_ms`) and its displacement; `first_motion` the directional reading, `first_motion.wallMs` − `ack.wallMs`; `done` `goal.wallMs` − `ack.wallMs`; `d` from `goal.detail`):

| cmdSeq | trip, dx | x0, y0 | first change (ticks, ms, tiles) | `first_move` (ms, tiles) | `first_motion` ms | done ms | goal |
|---|---|---|---|---|---|---|---|
| 21 | 0, +10 | 10997.50, 9699.50 | 5, 83, 0.001 | 179, 0.046 | 8578 | 14478 | done d=0.983 |
| 22 | 0, −10 | 11007.07, 9699.03 | 5, 79, 0.001 | 179, 0.103 | 379 | 14677 | done d=0.980 |
| 23 | 1, +10 | 10996.97, 9699.76 | 10, 163, 0.080 | 163, 0.080 | 8062 | 14262 | done d=0.991 |
| 24 | 1, −10 | 11006.43, 9699.34 | 7, 113, 0.017 | 113, 0.017 | 513 | 14313 | done d=0.992 |
| 25 | 2, +10 | 10996.10, 9699.90 | 7, 116, 0.0097 | 220, 0.081 | 7515 | 14015 | done d=0.970 |
| 26 | 2, −10 | 11006.41, 9699.27 | 9, 143, 0.057 | 143, 0.057 | 443 | 14343 | done d=0.999 |
| 27 | 3, +10 | 10996.12, 9699.88 | 10, 157, 0.044 | 157, 0.044 | 7457 | 13957 | done d=0.971 |
| 28 | 3, −10 | 11006.39, 9699.24 | 8, 131, 0.035 | 131, 0.035 | 430 | 14330 | done d=0.987 |
| 29 | 4, +10 | 10996.15, 9699.85 | 6, 96, 0.003 | 195, 0.069 | 7497 | 13996 | done d=0.975 |
| 30 | 4, −10 | 11006.38, 9699.20 | 7, 110, 0.017 | 110, 0.017 | 511 | 14311 | done d=0.977 |
| 31 | 5, +10 | 10996.17, 9699.83 | 11, 179, 0.057 | 179, 0.057 | 7578 | 13978 | done d=0.980 |
| 32 | 5, −10 | 11006.37, 9699.17 | 7, 111, 0.017 | 111, 0.017 | 512 | 14314 | done d=0.968 |
| 33 | 6, +10 | 10996.20, 9699.80 | 7, 109, 0.0097 | 209, 0.081 | 7609 | 14010 | done d=0.988 |
| 34 | 6, −10 | 11006.36, 9699.13 | 8, 127, 0.035 | 127, 0.035 | 428 | 14328 | done d=0.994 |
| 35 | 7, +10 | 10996.20, 9699.80 | 8, 129, 0.019 | 129, 0.019 | 7629 | 13929 | done d=0.987 |
| 36 | 7, −10 | 11006.35, 9699.13 | 9, 146, 0.057 | 146, 0.057 | 446 | 14345 | done d=0.992 |
| 37 | 8, +10 | 10996.20, 9699.80 | 11, 178, 0.057 | 178, 0.057 | 7578 | 13978 | done d=0.987 |
| 38 | 8, −10 | 11006.35, 9699.13 | 5, 80, 0.001 | 180, 0.103 | 480 | 14281 | done d=0.992 |
| 39 | 9, +10 | 10996.20, 9699.80 | 8, 131, 0.019 | 131, 0.019 | 7629 | 13929 | done d=0.987 |
| 40 | 9, −10 | 11006.35, 9699.13 | 8, 129, 0.035 | 129, 0.035 | 429 | 14330 | done d=0.992 |

Every leg settled (`settled` true, `settleMs` 0–429), every goal ended `done` within 1 tile, health read 100, `nZombies` 0 and every moodle 0 in all 5895 frames of `state.log`, and `action.n` reads 1 with the goal `running` on every frame of every leg but its last. The route is pass 3's: every +x leg reaches x 10993.21 (west of its start) and every −x leg x 10993.50, every leg y 9695.5, over 24.3–26.3 tiles of summed frame-to-frame distance, `done` at 13.9–14.7 s (pass 3: 24.2–26.2 tiles, 13.9–14.7 s; the house and the detour are drawn in `a_pipe_3-20261026-130558/GUIDE.md` § 3).

**The graded figure.** Sorted, the 20 `cmd_move_ms` values are 110, 111, 113, 127, 129, 129, 131, 131, 143, 146, 157, 163, 178, 179, 179, 179, 180, 195, 209, 220; the nearest-rank p90 is the 18th, **195** (`cmd_move_p90_ms`), under 500.

**The directional figure, ungraded.** Sorted, the 20 `cmd_motion_ms` values are 379, 428, 429, 430, 443, 446, 480, 511, 512, 513, 7457, 7497, 7515, 7578, 7578, 7609, 7629, 7629, 8062, 8578; the nearest-rank p90 is the 18th, 7629 (`cmd_motion_p90_ms`). The ten +x legs read 7457–8578 and the ten −x legs 379–513, as pass 3's 7462–8545 and 395–496: the directional threshold times the detour, not the pipe (pass 3's guide § 3).

**The two resolutions.** Pass 3's guide § 3 reported "5–11 ticks (77–180 ms)" as the first position change after the ack. Replayed here over pass 3's committed `state.log`, those figures are reproduced leg for leg as the first frame after the ack whose position differs from (`x0`, `y0`) by any amount (0.001 tiles counts), its ticks the frame's `tick` minus the ack's `tick` and its ms the two `wallMs` stamps' difference. `first_move` is the same kind of reading with a threshold, `> 0.01` tiles. Both are read off frames, and at rate 10 a frame exists only every 6 ticks (about 100 ms), so neither resolves the walk's start finer than the frame period: the ack is stamped on the tick the command is polled, the next frame falls 0–5 ticks after it (1–83 ms here), and every reading is that phase plus whole frame periods. The tick count is no finer than the ms: it counts ticks to a frame that exists every sixth tick.

- **Pass 3's measure on this run:** first change 5–11 ticks, 79–179 ms on all 20 legs, against pass 3's 5–11 ticks, 77–180 ms: it agrees.
- **This run's measure:** `first_move` is the first frame after the ack on no leg, the second on 17, the third on 3 (cmdSeq 25, 29, 33). On 14 legs it is the first changed frame; on 6 (cmdSeq 21, 22, 25, 29, 33, 38) the first changed frame moved 0.001–0.0097 tiles, under `MOVE_EPS_TILES`, so `first_move` is the next frame, about 100 ms later (83 → 179, 79 → 179, 116 → 220, 96 → 195, 109 → 209, 80 → 180). That is why the graded range, 110–220 ms, sits about one frame above the any-change range on those legs.
- **Against the reviewer's replay** (`.superpowers/sdd/2026-10-26-plan-21b-agent-harness-go-with-changes/review-t1.md`: `first_move` over pass 3's 19 rows read 131–196 ms, displacements 0.02–0.11 tiles, p90 196): this run's 110–220 ms (displacements 0.017–0.103 tiles, p90 195) agrees within the frame period, the range wider by one frame's phase at each end. The pipe's ack-to-walk is unchanged across passes 3 and 4.

**Server.** `readings.server[*]`: three `stats.all` acks, complete (`missing` `{}`); `rttMs` is listed under Do not cite.

### 4. The plumbing

`mode` `append` and `hello.mode` `append` (`hello.rate` 5, `hello.build` `42.21`, `hello.modVersion` `0.1`; `hello_build` `42.21`; `build` `42.21.0`); `gaps` `[]`; `bad` 0; `missing` `[]`; `lua_errors` 0 (`lua_error_lines` `[]`); `client_lua_errors` 0 (`logs.clients.admin` `[]`); `server_error_count` 0; `phase_errors` `{}`; `verify` both `ping` rows ok. `state.log`'s seq runs 1–6351 without a gap.

## Stage A conclusion

Four passes (`a_pipe-20261026-101003`, `a_pipe_2-20261026-115846`, `a_pipe_3-20261026-130558`, this run) read the pipe. The plumbing holds in all four: append mode, 0 gaps, 0 bad lines, 0 missing members in every scan's union, 0 Lua errors. Of the report's § 6 changes, two closed their gates: the tick gate restated on the 60 Hz mean passes at 0.794 ms (`tick_mean_ms_at60`, 1800 consecutive frame ticks; the run reads every window 0.15–0.31 ms above pass 3, which it cannot attribute), and the motion gate graded as ack to first position change passes at a p90 of 195 ms (20 of 20 legs, 110–220 ms, resolved to the 100 ms frame period). The third did not: 20-square parts halved the mean scan tick (2.29 ms a full part against pass 3's 4.3) but not the worst one, `scan15_ms_max` 7 as in pass 3, because a part's emit carries a per-line cost that does not shrink with the part (1.67 ms for 2.1 KB, 0.83 ms per KB through the origin, against pass 3's 0.495) and its tail still reaches 4–5 ms on single ticks. Stage A's verdict on `gate_a4` is **NO-GO on `scan15` alone**. The report's § 6 left the spec's JVM-agent fallback "unwarranted unless the 20-square pass also fails its scan gate"; this pass failed its scan gate.

## Do not cite from this file

| Key | Value in the file | Why not |
|---|---|---|
| everything measured here, as a population | — | `n = 1` boot, one fixture, one character. |
| every wall-clock leaf, by one wildcard sentence: `*PyMs`, `*wallMs`, `wallMs`, `firstWallMs`, `wall`, `wall_*`, `*_wall`, `wall_ms`, `epoch_ms_*`, `took`, `settleMs`, `phase_walls.*`, `timeline`, `wall_seconds`, `server_launch_wall`, `server_started_wall`, `session_ready_wall`, `hello_wait_ms`, `client_seen[*].*`, `memory[*].wall`, `memory_wait[*].wall`, `steps[*].*wall*`, `frame_wallMs_first`, `frame_wallMs_last`, `first_move.wallMs`, `first_move.readPyMs`, `first_motion.wallMs`, `first_motion.readPyMs`, in `a_pipe_4.json` and every line of `state.log` (wildcard) | host epoch ms and seconds | This host's timing, cited only as a difference within this run, never as a reading. |
| `readings.rates.*.tickMs`, `readings.rate60.tickMs` and every `cost.*Ms` (`pollMs`, `actMs`, `scanStepMs`, `senseMs`, `linkMs`, `scanEmitMs`, `dropped`), `tick_p99_ms_at5` 2, `partStepMs`, `partEmitMs`, `emitMs`, `stepMs`, `scanMsPerTick`, `scanStepMaxMs`, `scanMs`, `next_frame_senseMs`, `next_frame_scanStepMs`, `scan15_ms_max` 7, `scan15_latency_ms_max` 117 | integers 0–117 | Quantised to a 1 ms clock: a 2 is 1–2 ms; cite a small value as a bound, never as a value, and a mean over many frames (`tick_mean_ms_at60` 0.794) only as this clock's mean of the measured spans, never as one tick's cost or the tail. |
| `readings.motion[*].first_motion` and `cmd_motion_p90_ms` 7629 | 379–8578 | A measurement-definition reading, not a latency: the +x legs' route leaves the house westward and the first frame 0.2 tiles east of the start comes after the detour returns; cite only as the reason a directional threshold cannot time a detour. |
| `readings.motion[*].first_move` and `cmd_move_p90_ms` 195 as a latency finer than a frame | 110–220 | Frame-quantised: frames are 6 ticks (about 100 ms) apart at rate 10, so a reading is the ack's phase before the next frame plus whole frame periods; cite as "within one to two frame periods of the ack", never as the walk's start time. |
| `readings.motion[*].cmd_motion_host_ms` | — | Two clocks (the host's write time against the client's frame stamp) and frame-quantised; informational, never a graded figure. |
| `readings.server[*].rttMs` | 256.2, 1761.7, 2011.8 | `n = 3`. |
| `readings.server[*].ack.mult` | 4.79… | getMultiplier, not the true multiplier (#3762). |
| the emit-per-KB fit (`0.18 + 0.751 × KB`) | — | Fitted over parts of 0.39–3.35 KB, most within 1.75–2.25 KB: slope and intercept weakly separated; cite the binned table. |
| `constants`, `preboot`, `profile`, `fixture`, `argv`, `memory`, `memory_wait`, `world_changes` | the driver's tables and checks | Written before or around the run; not readings. |
