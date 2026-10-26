# `a_pipe_3-20261026-130558` reading guide

**`a_pipe_3-20261026-130558/a_pipe_3.json`** (with `state.log` and `a_grade.txt`) — produced by `testing/agent/drivers/a_pipe_3.py` at `driver_commit` `a4df25c6` (Plan 21 Stage A pass 3 fix 1), unedited since, which imports the frozen `testing/agent/drivers/a_pipe.py` and `a_pipe_2.py` and `testing/experiments/xlib.py` (`xlib_commit` `45c49217`); on HEAD `a4df25c6` at the boot (`preboot.commit`; harness Lua `ee23b53c`, clean; harness Python `52a7de93`); the agent mod `testing/PZAgent/PZAgent` loaded by path from the tree (`preboot.agent_commit` `a4df25c6` is the last commit under `testing/agent` or `testing/PZAgent`; `preboot.driver_checks.agent_lua_dirty` false), and the last commit under `testing/PZAgent` is `f00c9674` (Plan 21 Stage A pass 3 Lua: stuck is no movement; a failed goal clears its walk), so the Lua under test is `PZAgent_Act.lua`, `PZAgent_Main.lua`, `PZAgent_Sense.lua`, `PZAgent_Link.lua` and `shared/PZAgent_Core.lua` at `f00c9674` (the parts emit from `a30a2adf`). Fixture `agent0` (provisioned `prov-20261026-102802`), build `42.21.0` (`hello.build` `42.21`); profile `testing/profiles/agent-nozombies.toml` (PZTestKit + PZAgent, `[sandbox]` `Zombies = 6`, user `admin`). **Plan 21 Stage A, pass 3**, the last of spec § 4.1's three (pass 1: `a_pipe-20261026-101003`; pass 2: `a_pipe_2-20261026-115846`). `doctor_clean` true; `lint_errors` empty; `server_error_count` 0; `admin_lua_error` false; `client_lua_errors` 0; `lua_errors` 0; `phase_errors` empty; `finished` true; `voided_legs` 0; `bus_dead` null; one note, the motion phase's budget stop (`budget_stop`: `wall 560.032 s past the budget 560.0 s`). Free memory 15.76 GB at the preboot read and the memory wait, 2.66 GB at ready, 16.11 GB after teardown (`memory`, `memory_wait`). 573.4 s wall (`wall_seconds`; client quit rc 0, server stopped rc 0 with 0 errors, `timeline`).

Files, byte-identical to the run copy under `testing/runs/a_pipe_3-20261026-130558/`:

| File | Source | Bytes | sha256 |
|---|---|---|---|
| `a_pipe_3.json` | the driver's auto-copy of `testing/runs/a_pipe_3-20261026-130558/a_pipe_3.json` (`cmp` equal) | 125037 | `6a74a0f607a99af114541f4f199217bbef4990f7b8931364808fcf6e32b44daf` |
| `state.log` | `testing/runs/a_pipe_3-20261026-130558/clients/admin/Lua/pzagent/admin/state.log`, copied by the write-up (`cmp` equal; LF endings, 6020 lines: 1 `hello`, 5819 `frame`, 140 `scanPart`, 40 `ack`, 20 `event`; the driver read 5984 of them, `lines_read`, the rest being the 20th leg and the frames after its last read) | 5258948 | `a28fb5432e82ee3909ea1b92b95a02959e952f3d9af74c63c6ea29af24d9cdc5` |
| `a_grade.txt` | the exact stdout of `python testing/agent/drivers/a_grade.py testing/artifacts/a_pipe_3-20261026-130558/a_pipe_3.json` (exit 1), redirected by Git Bash, LF endings; run at HEAD `a4df25c6`, the driver's own commit | 512 | `4590f5785fb83e8f9f20f8dd3ce31b21b8d634e9def66664e1dcedc2b3df15be` |

`state.log` is the only evidence of the legs' paths, of the scan parts' squares and of the 20th leg below; the hashes are of the working-tree bytes as written (a checkout under `core.autocrlf=true` may rewrite line endings, so re-hash the blob, `git show <commit>:<path> | sha256sum`). The client console `testing/runs/a_pipe_3-20261026-130558/clients/admin/console.txt` (269749 bytes; 0 hits of the driver's `CLIENT_ERR_RX`), `server-stdout.log` and the server logs under `testing/runs/a_pipe_3-20261026-130558/server/` are per-machine and untracked, and nothing below rests on them.

## How to read it

The schedule is `a_pipe_3.py`'s docstring and spec § 4.1: sit still; `rate 2`, `rate 5`, `rate 10` for 60 s each; **new:** `rate 60` for 30 s (a frame every tick), then `rate 10` back; `scan 5`, `scan 10`, `scan 15` five times each, the scan now emitted in parts, one `scanPart` line per tick of at most 60 squares (`PZAgent_Sense.lua` line 214 `S.SCAN_SQUARES_PER_TICK = 60`); `goto` +10 tiles in x and back, ten round trips; three server `stats.all` calls; teardown (`phase_walls`: rates 55.106–235.592 s, rate60 to 265.865, scans to 269.378, motion to the budget stop at 560.032, server to 563.066). Scans and motion run at rate 10, a frame every 6 ticks (about 100 ms), as in pass 2.

- **Rates:** `readings.rates.<2|5|10>`: `frames` (120, 300, 601 against `expected` 120, 300, 600), and per frame the client's `cost` leaves `pollMs`, `actMs`, `scanStepMs`, `senseMs`, `linkMs` and their sum `tickMs` (`COST_KEYS`), each an integer read off a 1 ms clock (`PZA.now`, `getTimestampMs`); `dropped_max` 0 at every rate. `linkMs` is the previous frame's flush (`PZAgent_Main.lua` lines 7–8, 99). Every Lua line cited in this guide is at `f00c9674` (`git show f00c9674:<path>`, under `testing/PZAgent/PZAgent/42/media/lua/`), unchanged at `a4df25c6`.
- **Rate 60:** `readings.rate60`: `frames` 1803 (`expected` 1800 for `window_s` 30), `tickMs` (each frame's sum of the five leaves), `tick_sum` 869, `wall_ms` 30031, `tick_mean_ms_at60` = `tick_sum / frames`; `back_ack` the `rate 10` restore.
- **Scans:** `readings.scans.<5|10|15>[*]`: `scanId`, `parts`, `partNumbers`, `partStepMs` (each part's walk), `partEmitMs` (each part line's `emitMs`, which is the **previous** part's emit and flush, part 1's 0: `PZAgent_Main.lua` lines 72–84 serialise a part before its own emit is timed), `partBytes`, `partSquares`, `squares`, `bytes`, `missing`, the done part's `scanMs`, `scanTicks`, `scanMsPerTick`, `scanStepMaxMs`, and from the next frame `scanEmitMs` (the last part's own emit). The tick that walked part *i* also emitted it, so tick *i* cost `partStepMs[i] + partEmitMs[i+1]`, with `scanEmitMs` standing for the last tick's emit (`testing/agent/grades.py` `part_emits`, `scan_part_tick_ms`); `scan15_ms_max` is the largest such tick over the five r=15 scans, and `scan15_latency_ms_max` (`scan_latency_ms`, ungraded) the walk's sum plus every emit.
- **Motion:** `readings.motion[*]` (19 legs, `trip` 0–9 with `dx` ±10; the 20th, trip 9 −x, cmdSeq 40, was acked and walked but fell after the budget stop): `settled`/`settleMs`, `x0`/`y0`, `args`, `cmdSeq`, `ack`, `goal`, the void inputs, `first_motion` (the first frame past `MOTION_EPS` 0.2 tiles **in the commanded direction**: `x − x0` beyond +0.2 for a +x leg, below −0.2 for a −x leg), `cmd_motion_host_ms` (host write to that frame, two clocks, informational). The graded figure is `grades.cmd_motion_ms`: first-motion frame `wallMs` minus ack `wallMs`, both the client's clock.
- **Server:** `readings.server[*]`: `rttMs` and the `stats.all` ack.
- **Pipe health:** `hello` (`mode` `append`, `rate` 5), `missing` `[]`, `gaps` `[]`, `bad` 0, `lines_read` 5984, `events` `goal_done` 19 (the log holds 20, the 20th after the last read), no `goal_failed`.

## Verdicts

`a_grade.txt`: **NO-GO** (`pass.hello`, `pass.gaps`, `pass.lua_errors` true; `pass.scan15`, `pass.tick_p99_at5`, `pass.cmd_motion_p90` false).

1. **15-tile scan** (`scan15_ms_max` 7 against `< 5`, false; `scan15_latency_ms_max` 75, ungraded). The parts did what they were for: no tick carries the whole line, and the worst tick fell from pass 2's 45 ms to 7. What remains is a 60-square part's walk plus its own ~6 KB emit on one tick, 3–7 ms (section 1).
2. **Per-tick cost at 5 Hz** (`tick_p99_ms_at5` 2 against `< 2`, false). 300 of 300 frames; `tickMs` read 0 on 161, 1 on 116, 2 on 23 (p50 0, p99 2, max 2, mean 0.540). The rate-60 window's mean, 0.482 ms over 1803 consecutive ticks, is the sub-ms reading of the same cost the gate cannot resolve (section 2).
3. **Command to motion** (`cmd_motion_p90_ms` 8130 against `< 500`, false; `cmd_motion_n` 19, `cmd_motion_paired` 19, `cmd_motion_voided` 0). Every leg finished `done`; every walk started moving 77–180 ms after its ack. The 8130 is not a latency: every +x leg's path leaves the house westward by its south door and turns east 6.2–6.7 s after the ack, so the first frame 0.2 tiles **east** of the start comes 7.5–8.5 s in, while every −x leg's identical-length detour happens to open with a −x step (section 3).

### 1. Scan cost: parts, one a tick

Per scan (`readings.scans`; `tick` = `partStepMs[i]` + the emit tick *i* performed; bytes are the driver's re-serialised part lines):

| r | scanId | parts | `partStepMs` | emit per tick (`partEmitMs[1:]` + `scanEmitMs`) | max tick | `scanMs` | latency | bytes |
|---|---|---|---|---|---|---|---|---|
| 5 | 1 | 3 | [3,1,0] | [3,4,1] | 6 | 4 | 12 | 17111 |
| 5 | 2 | 3 | [2,1,0] | [3,4,1] | 5 | 3 | 11 | 17109 |
| 5 | 3 | 3 | [2,2,0] | [5,5,0] | 7 | 4 | 14 | 17110 |
| 5 | 4 | 3 | [0,0,0] | [4,5,0] | 5 | 0 | 9 | 17110 |
| 5 | 5 | 3 | [1,1,0] | [3,3,1] | 4 | 2 | 9 | 17110 |
| 10 | 6 | 8 | [2,2,1,1,1,1,1,1] | [4,3,3,4,3,3,3,1] | 6 | 10 | 34 | 49835 |
| 10 | 7 | 8 | [1,0,2,1,1,1,1,1] | [2,3,3,3,4,3,3,1] | 5 | 8 | 30 | 49833 |
| 10 | 8 | 8 | [1,1,1,1,2,1,1,0] | [3,3,3,3,3,3,3,2] | 5 | 8 | 31 | 49834 |
| 10 | 9 | 8 | [1,3,1,1,1,1,1,0] | [3,2,7,3,6,3,3,1] | 8 | 9 | 37 | 49834 |
| 10 | 10 | 8 | [3,1,1,2,1,2,2,1] | [4,3,3,4,3,4,4,1] | 7 | 13 | 39 | 49843 |
| 15 | 11 | 17 | [2,1,1,1,3,1,1,3,1,1,1,1,2,2,1,1,0] | [4,2,3,3,2,3,4,3,3,3,3,3,4,3,4,4,1] | 6 | 23 | 75 | 101954 |
| 15 | 12 | 17 | [2,1,0,1,1,1,1,1,1,1,1,0,0,1,1,1,0] | [4,3,3,3,3,3,4,3,3,4,4,4,5,3,3,2,1] | 6 | 14 | 69 | 101954 |
| 15 | 13 | 17 | [1,0,1,1,3,0,1,3,1,1,1,1,2,1,1,1,0] | [3,3,3,3,4,3,3,4,4,4,4,3,3,4,3,3,1] | 7 | 19 | 74 | 101954 |
| 15 | 14 | 17 | [2,1,1,1,1,1,1,1,0,1,3,0,1,1,1,1,0] | [3,3,4,3,3,2,3,3,3,3,4,3,3,2,3,4,1] | 7 | 17 | 67 | 101954 |
| 15 | 15 | 17 | [0,1,0,0,1,1,2,1,1,1,1,1,1,1,1,1,0] | [3,3,3,3,3,3,3,3,3,3,3,3,3,3,2,3,0] | 5 | 14 | 61 | 101954 |

**Bytes per part.** At r=15 every scan's parts read [5982, 5982, 5982, 5982, 5981, 5982, 7234, 7119, 6968, 7003, 6719, 6376, 6282, 5983, 5983, 5983, 413] bytes (60 squares each, the last 1): 99.7 B per square on open ground, up to 120.6 B on the parts crossing the house, 106.1 B per square over the scan. At r=10 [5980, 5979, 7232, 7547, 7378, 6892, 6496, 2331] (the last part 21 squares); at r=5 [8190, 8542, ~378] (141 B per square, almost all inside the house). Every scan's union is complete (`missing` `[]`, `squares` 121, 441, 961, `partNumbers` 1..`parts`), and replaying `state.log` through `agent/world.py`'s `World` drops no scan (`dropped_scans` 0) and leaves the 961-square map; the five r=15 scans agree square for square, and every r=5 and r=10 scan agrees with them on its overlap.

**The worst tick.** At r=15 the walk of a full 60-square part reads 1 ms on most ticks (0 on 10, 1 on 58, 2 on 7, 3 on 5 of 80; mean 1.09 ms, 0.018 ms per square, as pass 2's 0.017) and its emit 3 ms on most (2 on 6, 3 on 54, 4 on 19, 5 on 1 of 80; mean 3.19 ms), so a part's tick reads 3–7 ms (mean 4.3). The five r=15 maxima 6, 6, 7, 7, 5 fall where a 2–3 ms walk step meets a 3–4 ms emit on the same tick (7 = 3 + 4 in scanIds 13 and 14). `scanEmitMs`, the last 1-square part's own emit, reads 0–1. The r=10 scans hold the run's largest tick, 8 (scanId 9: a 1 ms step beside a 7 ms emit of its 7.2 KB third part, and 7 two ticks later from a 6 ms emit of the 7.4 KB fifth), outside the gate; r=5's parts are 8.2–8.5 KB and read 4–7.

**Emit per KB.** Over all 140 part lines (0.38–8.54 KB) a least-squares line is `emit ≈ 0.51 + 0.418 × KB` ms, and through the origin **0.495 ms per KB**; over the 130 parts above 1 KB the summed emit over the summed bytes is 0.496 ms per KB. Pass 2's whole lines (16.7–99.3 KB) read 0.445 ms per KB through the origin (`−1.10 + 0.460 × KB`). The slope is within 10 % of pass 2's; what the parts add is a fixed cost of about half a millisecond per line (the positive intercept), so the total emit of an r=15 scan is 47–55 ms over 17 lines (latency minus `scanMs`) against pass 2's 44–45 ms in one: parts cost about 15 % more emit in all and spread it.

**A part size under 5 ms (a projection, not a reading).** The gate reads `< 5` on integer leaves, so every tick must read 4 or less. At 60 squares the r=15 ticks average 4.3 ms and peak at 7: the peak sits about 2.7 ms above the mean, most of it the two leaves' rounding (each integer leaf can read up to 1 ms above its span) plus jitter. Scaling the walk (0.018 ms per square) and the emit (the fit, at 106 B per square) to smaller parts: **30 squares** (about 3.2 KB) projects to a mean tick of about 2.4 ms (0.54 walk + 1.84 emit; 2.1 ms through the origin fit), and with the same 2.7 ms margin to a peak of about 4.8–5.1 ms — at the gate, not safely under it; **20 squares** (about 2.1 KB) projects to a mean of about 1.4–1.8 ms and a peak of about 4.1–4.5 ms, under it. The run's only small full-walk parts agree: the five r=10 last parts (21 squares, 2.33 KB) read ticks of 2, 2, 2, 1, 2. The margin is taken from 80 ticks; a 20-square part makes 49 ticks a scan, 245 over five, and a longer tail may reach further. This projection extrapolates the fit and the margin; only a run at that size reads it.

### 2. The tick cost

Per key by window (frames, 1 ms clock; nearest-rank percentiles; counts are ms: frames):

| Window | Key | p50 | p99 | max | mean | counts |
|---|---|---|---|---|---|---|
| 2 Hz (120 of 120) | `tickMs` | 1 | 2 | 3 | 0.792 | 0:44 1:58 2:17 3:1 |
| 5 Hz (300 of 300) | `pollMs` | 0 | 1 | 1 | 0.163 | 0:251 1:49 |
| 5 Hz | `actMs` | 0 | 0 | 0 | 0 | 0:300 |
| 5 Hz | `scanStepMs` | 0 | 0 | 1 | 0.003 | 0:299 1:1 |
| 5 Hz | `senseMs` | 0 | 1 | 2 | 0.147 | 0:257 1:42 2:1 |
| 5 Hz | `linkMs` | 0 | 1 | 1 | 0.227 | 0:232 1:68 |
| 5 Hz | `tickMs` | 0 | 2 | 2 | 0.540 | 0:161 1:116 2:23 |
| 10 Hz (601 of 600) | `tickMs` | 0 | 2 | 2 | 0.552 | 0:309 1:252 2:40 |
| 60 Hz (1803, 30 s) | `pollMs` | 0 | — | 2 | 0.159 | 0:1521 1:278 2:4 |
| 60 Hz | `actMs` | 0 | — | 1 | 0.002 | 0:1799 1:4 |
| 60 Hz | `scanStepMs` | 0 | — | 1 | 0.002 | 0:1800 1:3 |
| 60 Hz | `senseMs` | 0 | — | 2 | 0.106 | 0:1617 1:180 2:6 |
| 60 Hz | `linkMs` | 0 | — | 4 | 0.213 | 0:1427 1:370 2:5 4:1 |
| 60 Hz | `tickMs` | 0 | 2 | 4 | **0.482** | 0:1094 1:554 2:151 3:3 4:1 |

The 60 Hz per-leaf rows are read off `state.log` (the 1803 frames between `frame_wallMs_first` and `frame_wallMs_last`, whose per-frame sums equal `readings.rate60.tickMs` element for element); the artifact carries only the sum.

**The 5 Hz gate.** 23 of 300 frames read 2, so the p99 is 2 and the gate (`< 2`) fails as in passes 1 and 2; no single leaf reads 2 more than once in 300 frames, and a `tickMs` of 2 is a sum of five integer leaves each rounded on the same 1 ms clock. Bytes written per minute: 88372 at 2 Hz, 220794 at 5 Hz, 442252 at 10 Hz (`state_bytes_end` − `state_bytes_start`; pass 2 88410, 220779, 442331).

**The rate-60 window.** 1803 frames in 30.031 s of client wall clock (60.04 a second; every consecutive pair is one tick apart, so every tick built a frame), `sum(tickMs)` 869 ms, mean **0.482 ms** per frame tick (population SD 0.659, standard error of the mean 0.016 ms). What the mean resolves: each leaf is the difference of two integer `getTimestampMs` stamps, so a span of true length *t* reads ⌊*t*⌋ or ⌈*t*⌉ depending on where the millisecond boundary falls; when that phase is unrelated to the work, each reading is an unbiased estimate of *t*, and the mean over 1803 frames resolves the average measured cost of a frame tick to a few hundredths of a millisecond. It does **not** resolve any single tick or the tail (0.48 ms every tick and 4.8 ms one tick in ten read alike), it counts only the five measured spans (poll, act, scan step, sense, the previous frame's flush; not the OnTick dispatch around them), and it is the cost of a tick that builds a frame, so an upper reading for the average tick at 5 Hz, where five ticks in six build none. By leaf, the frame tick's 0.48 ms is 0.21 flush, 0.16 poll, 0.11 sense and 0.00 act and scan step. The 2, 5 and 10 Hz means (0.792, 0.540, 0.552) read the same cost on fewer frames (pass 2: 0.717, 0.623, 0.592).

### 3. The motion legs

Per leg (`readings.motion`; `ack→fm` is `grades.cmd_motion_ms`, client clock; `first change` is the first frame after the ack whose position differs from the start, any direction; `east turn` the first frame of the eastward stretch, x rising by more than 0.1 a frame; `done` the goal's `wallMs` minus the ack's; `path` the summed frame-to-frame distance; all but the first three columns read off `state.log`):

| cmdSeq | trip, dx | x0, y0 | ack→fm ms | first change (ticks, ms) | east turn ms | done ms | path tiles | goal |
|---|---|---|---|---|---|---|---|---|
| 21 | 0, +10 | 10997.50, 9699.50 | 8545 | 9, 145 | 6650 | 14445 | 26.2 | done d=0.983 |
| 22 | 0, −10 | 11007.07, 9699.03 | 395 | 6, 96 | — | 14695 | 25.3 | done d=0.980 |
| 23 | 1, +10 | 10996.97, 9699.76 | 8130 | 8, 131 | 6431 | 14230 | 25.6 | done d=0.991 |
| 24 | 1, −10 | 11006.43, 9699.34 | 496 | 6, 94 | — | 14395 | 24.5 | done d=0.992 |
| 25 | 2, +10 | 10996.10, 9699.90 | 7463 | 10, 163 | 6263 | 13962 | 24.7 | done d=0.969 |
| 26 | 2, −10 | 11006.41, 9699.27 | 481 | 5, 80 | — | 14380 | 24.5 | done d=0.999 |
| 27 | 3, +10 | 10996.12, 9699.88 | 7462 | 10, 163 | 6262 | 13963 | 24.7 | done d=0.970 |
| 28 | 3, −10 | 11006.39, 9699.24 | 462 | 10, 162 | — | 14363 | 24.4 | done d=0.987 |
| 29 | 4, +10 | 10996.15, 9699.85 | 7563 | 10, 162 | 6262 | 13962 | 24.7 | done d=0.975 |
| 30 | 4, −10 | 11006.38, 9699.20 | 496 | 6, 96 | — | 14296 | 24.3 | done d=0.977 |
| 31 | 5, +10 | 10996.17, 9699.83 | 7578 | 11, 178 | 6278 | 13978 | 24.8 | done d=0.980 |
| 32 | 5, −10 | 11006.37, 9699.17 | 477 | 5, 77 | — | 14277 | 24.2 | done d=0.968 |
| 33 | 6, +10 | 10996.20, 9699.80 | 7546 | 9, 145 | 6245 | 13946 | 24.7 | done d=0.987 |
| 34 | 6, −10 | 11006.35, 9699.13 | 478 | 5, 78 | — | 14278 | 24.3 | done d=0.992 |
| 35 | 7, +10 | 10996.20, 9699.80 | 7564 | 10, 163 | 6265 | 13963 | 24.7 | done d=0.987 |
| 36 | 7, −10 | 11006.35, 9699.13 | 479 | 5, 79 | — | 14279 | 24.3 | done d=0.992 |
| 37 | 8, +10 | 10996.20, 9699.80 | 7580 | 11, 179 | 6282 | 13981 | 24.7 | done d=0.987 |
| 38 | 8, −10 | 11006.35, 9699.13 | 494 | 6, 95 | — | 14294 | 24.4 | done d=0.992 |
| 39 | 9, +10 | 10996.20, 9699.80 | 7580 | 11, 180 | 6281 | 13981 | 24.7 | done d=0.987 |
| (40) | 9, −10 | 11006.35, 9699.13 | (496) | — | — | (14295) | — | done d=0.992 (log only) |

Every leg settled (`settled` true, `settleMs` 0–430), every goal ended `done` within 1 tile, health read 100, `nZombies` 0 and every moodle 0 in all 5819 frames, and the only events are 20 `goal_done`: `min_health` 100 and `max_nZombies` 0 on every leg, `voided_legs` 0. The 20th leg (cmdSeq 40, ack `state.log` seq 5859) is read off the log alone: it is not in the artifact or the grade, since the driver's budget stop at 560.032 s came while it walked.

**The map between x0 and x0 + 10.** The r=15 scans (centred on the spawn (10997.5, 9699.5), x 10982–11012, y 9684–9714), reassembled by `scanId` as `World` does, around the legs (`,` open ground, `.` a building-8 square, `t` `solidTrans`, `#` `solid`, `W` a window, `D` a door; lower case and `*`/`+` the squares leg cmdSeq 23 walked; `S` its start square, `T` its target square; columns x 10990–11009, rows y 9692–9705):

```
     01234567890123456789
9692 ,,,,,,#,,,,,,,,,,,,,
9693 ,,,,,,,,,,,,,,,,,,,,
9694 ,,,,,,,,,,,,,,,,,,,,
9695 ,,,*********,,,,,,,,
9696 ,,,*Wtt#tWt,*,,,#,,,
9697 ,,,*W...t.t,,***,,,,
9698 ,,,*Wtt.t.t,,,,**,,,
9699 ,,,*W.S....W,,,,T,,,
9700 ,,,*W++....,,,,,,,,,
9701 ,,,*wdW...t,,,,,,,,,
9702 ,,,,,,,W.D.W,,,,,,,,
9703 ,,,,,,,#.tt,,,,,,,,,
9704 ,,,,,,t.D##,,,,,,,,,
9705 ,,,,,,tW...,,,,,,,,,
```

The start squares (x 10996–10997, y 9699) are in building 8's living room (x 10994–11000). The straight line east crosses the room's floor (10997–11000, all passable) and then the east wall, whose only opening on that line is the closed window at (11001, 9699) (`locked` false, `open` false); beyond it, x 11002–11007 on rows 9698–9700 hold no `solid` or `solidTrans` square. The scan reads no wall edges, only the squares and their door and window objects, so the walls are read off where `building` squares meet open ones and where the windows sit. The walk's exit is the door at (10995, 9701) on the room's south side (the scan reads it `locked` true, `open` false; every leg crossed it without a stationary frame, and how the engine passed it is not read here).

**What a +x leg did in its first 7.5 s (cmdSeq 23, ack seq 3345, frames 3346–3489, one every 100 ms).** It started moving at 131 ms (the first position change, 8 ticks after the ack) and walked **away from the target**: south-west across the living room to (10995.5, 9700.5), the square north of the door, by about 1.0 s; south through the door to (10995.5, 9701.4) by 1.4 s; west along y 9701.5 to x 10993.21 by 2.8 s (stationary, `moving` true, for 2 frame intervals at x 10994.26 and 6 at x 10993.21); north along x 10993.2–10993.5 to y 9695.5 by 6.3 s; then east along y 9695.5, outside the house's north wall, crossing x0 + 0.2 = 10997.17 at 8.13 s (frame 3427, x 10997.37, 4.3 tiles north of the start). It went on east to x 11001.5, south-east to (11003.5, 9697.5), east along y 9697.5 (stationary for 2 frame intervals at x 11004.70 and 6 at x 11005.71), and south to (11006.35, 9699.12), `done` at 14.23 s, d=0.991, over 25.6 tiles. So the walk executed correctly and started promptly; **what read 7.5–8.5 s is the measurement**: `first_motion` waits for the character to stand 0.2 tiles east of where it started, and on this route that happens only once the detour has come back past the start on the far side of the house. Every +x leg follows the same route (path 24.7–26.2 tiles, the same four pauses, the east turn at 6.2–6.7 s, `done` at 13.9–14.4 s); cmdSeq 21 started at the spawn, x 10997.5, 0.5–1.3 tiles east of the later +x starts, so its walk west was longer and its reading the largest, 8545.

**What a −x leg did (cmdSeq 24, ack seq 3494).** The reverse of the same route: north-west from (11006.43, 9699.34) toward (11005.5, 9697.5), passing x0 − 0.2 at 496 ms (frame 3500, x 11006.18, still 1.5 tiles from that corner); west along y 9697.5 (stationary for 6 frame intervals at x 11005.46–11005.47, `moving` false on 3 of them, and 6 at x 11004.75); north-west to (11001.5, 9695.5); west along y 9695.5 to x 10993.5 — 12.9 tiles west of x0, past the target's x — south along x 10993.5 to y 9701.5, east to the door (stationary at x 10993.58 and 10994.37), north through it and north-east to (10995.98, 9700.02), `done` at 14.40 s over 24.5 tiles. Its directional reading is short only because the route's first segment has a −x component; it times the walk's start (first change 94 ms, then the ramp past 0.2 tiles), as pass 2's legs did, by the geometry's coincidence. The −x legs' 395–496 ms (mean 473) match pass 2's 412–498 on direct paths.

**Against pass 2.** Pass 2 ran the same fixture and spawn; its first leg failed `stuck` on this same detour (pass 2's progress rule) and its failed goal's walk carried the character out to the north side, so its 18 clean legs shuttled along y 9695.5 between x 10988.09 and 10997.47, open ground with a direct path, `done` in about 4.6 s, ack→fm 412–498 ms. Pass 3's Lua (`f00c9674`: stuck is no movement, `PZAgent_Act.lua` lines 8–10, 25–26; a failed goto clears its walk) let the first leg complete the detour, so every later leg shuttled between the living room and the east yard: about 24.5 tiles and 14 s a leg against 10 tiles and 4.6 s. The new stuck rule held: the longest stationary run on any leg is 7 frame intervals (about 42 ticks, cmdSeq 26 and 28 at x 11005.47), under `STUCK_TICKS` 90; `action.n` reads 1 with the goal `running` on every frame of every leg (2830 frames), so no walk was re-queued and none failed. The first position change after the ack, 5–11 ticks (77–180 ms) on every leg, matches pass 2's 6–11 ticks (96–179 ms): the pipe's ack-to-walk is unchanged.

**The grade and the budget.** Sorted, the 19 client-clock values are 395, 462, 477, 478, 479, 481, 494, 496, 496, 7462, 7463, 7546, 7563, 7564, 7578, 7580, 7580, 8130, 8545; the nearest-rank p90 is the 18th, 8130. The −x population alone (9 legs; 10 with the log-only 20th) reads 395–496. The ~14 s legs (three times pass 2's) are why the motion phase ran out of `BUDGET_S` 560 after 19 legs.

**Server.** `readings.server[*].rttMs` 1008.2, 759.4, 1262.6 (n = 3); `stats.all` acks complete.

## Stage A conclusion

Three passes (`a_pipe-20261026-101003`, `a_pipe_2-20261026-115846`, this run) read the pipe, and its plumbing holds: append mode, 0 gaps, 0 bad lines, 0 missing members in every scan's union, 0 Lua errors, and a measured cost of about half a millisecond a frame tick (0.482 ms mean over 1803 consecutive frame ticks at 60 Hz; 0.54–0.79 ms means at 2–10 Hz on the same 1 ms clock). The scan's per-tick cost is governed by its part size, not the walk: a 60-square walk step is about 1 ms, the emit about 0.5 ms per KB plus about 0.5 ms a line, so a 60-square part (about 6 KB) read 3–7 ms a tick and failed the 5 ms gate at 7, against pass 2's 45 ms one-tick emit of the whole line; a 30-square part projects to a peak near 5 ms (at the gate) and a 20-square part to about 4.1–4.5 ms, projections this run did not read. The walk's ack-to-motion is about 0.45–0.5 s on a direct path (pass 2's 18 clean legs, 412–498 ms; this run's −x legs, 395–496 ms) and the walk starts moving 77–180 ms after the ack in every leg of both passes; the directional measurement cannot time a detour, so this run's +x legs' 7.5–8.5 s and the p90 of 8130 they set are a reading of the route out of the agent0 house, not of the pipe. The tick gate (`p99 < 2 ms` at 5 Hz) sits at the clock's resolution: every cost is an integer difference of `getTimestampMs` stamps, a 2 is any tick between about 1 and 2 ms (or a sum of five sub-ms leaves), and the gate read 2 in all three passes while the means read 0.5–0.8 ms.

## Do not cite from this file

| Key | Value in the file | Why not |
|---|---|---|
| everything measured here, as a population | — | `n = 1` boot, one fixture, one character. |
| every wall-clock leaf, by one wildcard sentence: `*PyMs`, `*wallMs`, `wallMs`, `firstWallMs`, `wall`, `wall_*`, `*_wall`, `wall_ms`, `epoch_ms_*`, `took`, `settleMs`, `phase_walls.*`, `budget_stop.wall`, `notes[*].wall`, `timeline`, `wall_seconds`, `server_launch_wall`, `server_started_wall`, `session_ready_wall`, `hello_wait_ms`, `client_seen[*].*`, `memory[*].wall`, `memory_wait[*].wall`, `steps[*].*wall*`, `frame_wallMs_*`, in `a_pipe_3.json` and every line of `state.log` (wildcard) | host epoch ms and seconds | This host's timing, cited only as a difference within this run, never as a reading. |
| `readings.rates.*.tickMs`, `readings.rate60.tickMs` and every `cost.*Ms` (`pollMs`, `actMs`, `scanStepMs`, `senseMs`, `linkMs`, `scanEmitMs`), `tick_p99_ms_at5` 2, `partStepMs`, `partEmitMs`, `emitMs`, `stepMs`, `scanMsPerTick`, `scanStepMaxMs`, `scanMs`, `scan15_ms_max` 7, `scan15_latency_ms_max` 75 | integers 0–75 | Quantised to a 1 ms clock: a 2 is 1–2 ms; cite a small value as a bound, never as a value, and a mean over many frames (`tick_mean_ms_at60` 0.482) only as this clock's mean of the measured spans, never as one tick's cost or the tail. |
| `readings.motion[*].first_motion` and `grades`' `cmd_motion_p90_ms` 8130 for the +x legs (cmdSeq 21, 23, 25, …, 39; 7462–8545) | 7462–8545 | A measurement-definition reading, not a latency: the route leaves the house westward and the first frame 0.2 tiles east of the start comes after the detour returns; cite only as the reason a directional threshold cannot time a detour. |
| `cmd_motion_n` 19 and the motion leg count | 19 | Budget-stopped: the 20th leg (cmdSeq 40) was acked and walked after the stop and is read off `state.log` only. |
| `readings.motion[*].cmd_motion_host_ms` | 413.2–8554.8 | Two clocks (the host's write time against the client's frame stamp) and frame-quantised; informational, never the graded figure. |
| the projected part sizes (30 squares near 5 ms, 20 squares 4.1–4.5 ms) | — | A projection from this run's fit and peak margin, not a reading. |
| `readings.server[*].rttMs` | 1008.2, 759.4, 1262.6 | `n = 3`. |
| `readings.server[*].ack.mult` | 4.7957… | getMultiplier, not the true multiplier (#3762). |
| `constants`, `preboot`, `profile`, `fixture`, `argv`, `memory`, `memory_wait`, `world_changes` | the driver's tables and checks | Written before or around the run; not readings. |
