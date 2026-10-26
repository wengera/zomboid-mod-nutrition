# `a_pipe_2-20261026-115846` reading guide

**`a_pipe_2-20261026-115846/a_pipe_2.json`** (with `state.log` and `a_grade.txt`) — produced by `testing/agent/drivers/a_pipe_2.py` at `driver_commit` `fb87c875` (Plan 21 Stage A pass 2 fix 1), unedited since, which imports the frozen `testing/agent/drivers/a_pipe.py` and `testing/experiments/xlib.py` (`xlib_commit` `45c49217`); on HEAD `fb87c875` at the boot (`preboot.commit`; harness Lua `ee23b53c`, clean; harness Python `52a7de93`); the agent mod `testing/PZAgent/PZAgent` loaded by path from the tree, whose last commit at that HEAD is `fb87c875` (`preboot.agent_commit`; `preboot.driver_checks.agent_lua_dirty` false), so the Lua under test is `PZAgent_Act.lua`, `PZAgent_Main.lua`, `PZAgent_Sense.lua`, `PZAgent_Link.lua` and `shared/PZAgent_Core.lua` at `fb87c875`. Fixture `agent0` (provisioned `prov-20261026-102802`), build `42.21.0` (`hello.build` `42.21`); profile `testing/profiles/agent-nozombies.toml` (PZTestKit + PZAgent, `[sandbox]` `Zombies = 6`, `[server]` `SleepAllowed` and `SleepNeeded` true, user `admin`). **Plan 21 Stage A, pass 2** (pass 1: `a_pipe-20261026-101003`). `doctor_clean` true; `lint_errors` empty; `server_error_count` 0; `admin_lua_error` false; `client_lua_errors` 0; `lua_errors` 0; `phase_errors` empty; `finished` true; `voided_legs` 0; `notes` empty. Free memory 15.67 GB at the preboot read and the memory wait, 2.65 GB at ready, 16.15 GB after teardown (`memory`, `memory_wait`). 364.5 s wall (`wall_seconds`; client quit rc 0, server stopped rc 0 with 0 errors, `timeline`).

Files, byte-identical to the run copy under `testing/runs/a_pipe_2-20261026-115846/`:

| File | Source | Bytes | sha256 |
|---|---|---|---|
| `a_pipe_2.json` | the driver's auto-copy of `testing/runs/a_pipe_2-20261026-115846/a_pipe_2.json` (`cmp` equal) | 99395 | `e70ea8a2e0126fed9230a29bf2174d0f1ff6db66649aa4f5d344d9a4290b52d0` |
| `state.log` | `testing/runs/a_pipe_2-20261026-115846/clients/admin/Lua/pzagent/admin/state.log`, copied by the write-up (`cmp` equal; LF endings, 2261 lines: 1 `hello`, 2187 `frame`, 38 `ack`, 20 `event`, 15 `scan`; the driver read 2224 of them, `lines_read`, the rest being the frames after its last read) | 2481563 | `27d5e372c4c92d2b20a6d0b8667ac1d27d23dc8da73e3341e936f12498d25a8d` |
| `a_grade.txt` | the exact stdout of `python testing/agent/drivers/a_grade.py testing/artifacts/a_pipe_2-20261026-115846/a_pipe_2.json` (exit 1), redirected by Git Bash, CRLF endings; run at HEAD `a30a2adf`, where `testing/agent/` (`grades.py`, `a_grade.py`) is identical to `fb87c875` | 468 | `fa6bc846d76759554915b1f4fcc2c0efd495d9cd0eca721a578a32927e838229` |

`state.log` is the only evidence of the first leg's path and of the per-frame scan emit below; the hashes are of the working-tree bytes as written (a checkout under `core.autocrlf=true` may rewrite line endings, so re-hash the blob, `git show <commit>:<path> | sha256sum`). The client console `testing/runs/a_pipe_2-20261026-115846/clients/admin/console.txt` (269750 bytes; 0 hits of the driver's `CLIENT_ERR_RX`) and the server logs under `testing/runs/a_pipe_2-20261026-115846/server/Logs/` are per-machine and untracked, and nothing below rests on them.

## How to read it

The schedule is `a_pipe_2.py`'s docstring and spec § 4.1: sit still; `rate 2`, `rate 5`, `rate 10` for 60 s each; `scan 5`, `scan 10`, `scan 15` five times each, now a chunked job of 60 squares a tick (`PZAgent_Sense.lua` line 210 `S.SCAN_SQUARES_PER_TICK = 60`); `goto` +10 tiles in x and back, ten round trips; three server `stats.all` calls; teardown (`phase_walls`: rates 59.338–239.767 s, scans to 243.468, motion to 351.159, server to 354.692). The rate is left at 10 after the rates phase, so the scan and motion frames come every 6 ticks (60.0 ticks/s over the motion phase).

- **Rates:** `readings.rates.<2|5|10>`: `frames` (120, 300, 601 against `expected` 120, 300, 600), and per frame the client's `cost` leaves `pollMs`, `actMs`, `scanStepMs`, `senseMs`, `linkMs` and their sum `tickMs` (`COST_KEYS`), each an integer read off a 1 ms clock (`PZA.now`, `getTimestampMs`); `dropped_max` 0 at every rate. `linkMs` is the previous frame's flush (`PZAgent_Main.lua` lines 7–8 at `fb87c875`). Every Lua line cited in this guide is at `fb87c875` (`git show fb87c875:<path>`); the tree has moved on since (`a30a2adf`, pass 3's Lua).
- **Scans:** `readings.scans.<5|10|15>[*]`: `scanMs` (the sum of the job's steps, the whole-scan latency, ungraded), `scanTicks`, `scanMsPerTick` (each step's ms), `scanStepMaxMs`, `squares`, `bytes`, and from the first frame after the line `scanEmitMs` (the completing tick's `PZA.emit("scan", …)` plus `PZA.link.flush()`, `PZAgent_Main.lua` lines 77–79 at `fb87c875`), `next_frame_scanStepMs` and `next_frame_senseMs`. A frame that falls on the completing tick carries the emit in its `scanStepMs` too (step + emit), which is why a few rows read a non-zero `next_frame_scanStepMs` equal to their emit.
- **Motion:** `readings.motion[*]` (20 legs, `trip` 0–9 with `dx` ±10): `settled`/`settleMs` (the driver's wait for a still character, `SETTLE_S` 3), `args`, `cmdSeq`, `ack`, `goal`, `at_send`/`at_end`/`min_health`/`max_nZombies` (the void inputs), `first_motion` (the first frame past `MOTION_EPS` 0.2 tiles in the commanded direction), `cmd_motion_host_ms` (host write to that frame, two clocks, informational). The graded figure is `grades.cmd_motion_ms`: first-motion frame `wallMs` minus ack `wallMs`, both the client's clock.
- **Server:** `readings.server[*]`: `rttMs` and the `stats.all` ack.
- **Pipe health:** `hello` (`mode` `append`, `rate` 5), `missing` `[]`, `gaps` `[]`, `bad` 0, `lines_read` 2224, `events` `goal_done` 19, `goal_failed` 1.

## Verdicts

`a_grade.txt`: **NO-GO** (`pass.hello`, `pass.gaps`, `pass.lua_errors`, `pass.cmd_motion_p90` true; `pass.scan15`, `pass.tick_p99_at5` false).

1. **15-tile scan** (`scan15_ms_max` 45 against `< 5`, false). The walk chunking worked: no r=15 step exceeded 3 ms. The 45 is the completing tick's emit and flush of the 99.3 KB scan line, one tick carrying the whole line's serialisation and append (section 1). `scan15_latency_ms_max` 19 is the summed walk, ungraded.
2. **Per-tick cost at 5 Hz** (`tick_p99_ms_at5` 2 against `< 2`, false). 300 of 300 frames; `tickMs` read 0 on 146, 1 on 121, 2 on 33 (p50 1, p99 2, max 2, mean 0.623). As in pass 1 the gate sits at the clock's resolution: a 2 is a tick between 1 and 2 ms (or a little above, since `tickMs` sums five rounded leaves), and the gate cannot pass unless 99 % of frames read 0 or 1 (section 2).
3. **Command to motion** (`cmd_motion_p90_ms` 498 against `< 500`, true; `cmd_motion_n` 20, `cmd_motion_paired` 19, `cmd_motion_voided` 0). The pass is narrow and the population carries two defect legs (section 3): the first leg failed `stuck` on a detour out of a house, and the second's 3661 ms is the first leg's walk left queued. Over the 18 clean legs (cmdSeq 21–38) the client-clock p90 is 496.

### 1. Scan cost: the walk and the emit

Per radius, five scans each (`readings.scans`; bytes as the driver counts them, the line is one byte longer with its newline):

| r | squares | bytes | `scanTicks` | `scanMsPerTick` (5 scans) | `scanStepMaxMs` | `scanMs` | `scanEmitMs` |
|---|---|---|---|---|---|---|---|
| 5 | 121 | 16725 | 3 | [2,1,0] [2,1,0] [2,2,0] [3,1,0] [4,1,0] | 2, 2, 2, 3, 4 | 3, 3, 4, 4, 5 | 7, 7, 7, 7, 7 |
| 10 | 441 | 48645–48646 | 8 | [1,1,3,1,1,1,1,1] [1,1,2,1,1,1,1,0] [1,1,1,1,1,1,1,1] [0,1,1,1,1,0,1,1] [1,1,1,1,1,1,1,0] | 3, 2, 1, 1, 1 | 10, 8, 8, 6, 7 | 19, 20, 20, 22, 22 |
| 15 | 961 | 99283–99284 | 17 | [1,1,1,1,1,1,1,1,1,3,2,1,1,1,1,1,0] [1,1,1,1,1,1,1,1,1,1,1,0,2,0,1,1,0] [1,0,1,1,1,1,1,1,1,2,1,1,1,0,1,1,0] [2,0,0,1,1,1,2,1,1,1,1,1,1,1,1,1,0] [1,0,1,0,1,1,1,0,1,2,1,1,1,1,1,1,0] | 3, 2, 2, 2, 2 | 19, 15, 15, 16, 14 | 45, 45, 44, 45, 45 |

**The walk.** A 60-square step reads 1 ms in most ticks at r=10 and r=15 (full-chunk means 1.03 and 0.99 ms, so about 0.017 ms per square; the r=15 steps read 0 on 14, 1 on 64, 2 on 6, 3 on 1 of 85), and the last step of r=5 and r=15 walks a single square at 0 ms. Over all fifteen scans the summed `scanMs` is 0.018 ms per square (r=5 0.031, r=10 0.018, r=15 0.016); the r=5 steps read higher (full-chunk mean 1.9 ms) on the squares inside the starting house, whose rooms and containers make each square heavier (138 bytes per square at r=5 against 110 and 103 at r=10 and r=15). The per-square walk cost matches pass 1's 0.0162 ms per square. The chunking did what it was for: the largest walk step at r=15 is 3 ms, against pass 1's 14–21 ms in one tick.

**The emit.** `scanEmitMs` is flat within a radius and scales with the line: a least-squares line over the fifteen rows is `scanEmitMs ≈ −1.10 + 0.460 × KB` (predicting 6.6, 21.3, 44.5 ms at 16.7, 48.6, 99.3 KB; largest residual 2.3 ms), and through the origin 0.445 ms per KB, so **about 0.45 ms per KB** of line. The same rate holds for the frames: a 5 Hz frame is 736 bytes on average (727–738) and `linkMs`, its flush, averages 0.313 ms at 5 Hz, 0.43 ms per KB. **The spike is the completing tick:** on it `stepJob` returns the whole scan table, and `PZAgent_Main.lua` (lines 77–79) serialises it and appends it to `state.log` in that one tick (`PZA.emit("scan", s)` then `PZA.link.flush()`), 44–45 ms for r=15. The grade's per-tick term is `max(scanStepMaxMs, last step + scanEmitMs)` = 45, 45, 44, 45, 45 for the five r=15 scans (`grades.scan_step_ms`); the walk never sets it. The emit is a cost the scan carried in pass 1 too, inside its one-tick 14–21 ms reading or beside it; pass 1 did not split it out.

### 2. The tick cost

Per key by rate (frames, 1 ms clock; nearest-rank percentiles; counts are ms: frames):

| Rate | Key | p50 | p99 | max | mean | counts |
|---|---|---|---|---|---|---|
| 2 Hz (120 of 120) | `tickMs` | 1 | 2 | 3 | 0.717 | 0:48 1:59 2:12 3:1 |
| 5 Hz (300 of 300) | `pollMs` | 0 | 1 | 1 | 0.150 | 0:255 1:45 |
| 5 Hz | `actMs` | 0 | 0 | 1 | 0.003 | 0:299 1:1 |
| 5 Hz | `scanStepMs` | 0 | 0 | 0 | 0 | 0:300 |
| 5 Hz | `senseMs` | 0 | 1 | 2 | 0.157 | 0:255 1:43 2:2 |
| 5 Hz | `linkMs` | 0 | 1 | 2 | 0.313 | 0:207 1:92 2:1 |
| 5 Hz | `tickMs` | 1 | 2 | 2 | 0.623 | 0:146 1:121 2:33 |
| 10 Hz (601 of 600) | `tickMs` | 1 | 2 | 2 | 0.592 | 0:290 1:266 2:45 |

At 5 Hz no single key reads 2 ms more than twice in 300 frames; the 33 frames at 2 are sums of 1 ms leaves (`tickMs` adds five integers, each rounded on the same 1 ms clock, so a sum of 2 can stand for well under 2 ms of work). The cost per frame does not rise with the rate (mean 0.717, 0.623, 0.592 ms at 2, 5, 10 Hz; pass 1 0.736, 0.714, 0.698). Bytes written per minute: 88410 at 2 Hz, 220779 at 5 Hz, 442331 at 10 Hz (`state_bytes_end` − `state_bytes_start`). **The clock:** `PZA.now` is `getTimestampMs`, integer milliseconds, so each leaf is the difference of two integer stamps and reads 0 or 1 for any work under 1 ms depending on where the millisecond boundary falls; a p99 of 2 says only that the 99th-percentile tick lies at or below about 2 ms, and the `< 2` gate cannot separate 1.2 ms from 1.9 ms. The means are the better reading of this clock, since the boundary's phase is uncorrelated with the work: about 0.6 ms a frame tick.

### 3. The motion legs

Per leg (`readings.motion`; `ack→fm` is `grades.cmd_motion_ms`, client clock; `first change` is the first frame after the ack whose position differs from the frame before it, read off `state.log`):

| cmdSeq | trip, dx | settled, settleMs | goal | ack→fm ms | `cmd_motion_host_ms` | first change (ticks, ms) |
|---|---|---|---|---|---|---|
| 19 | 0, +10 | true, 0 | failed `stuck` | — (unpaired, +inf) | — | 9, 147 (westward) |
| 20 | 0, −10 | **false, 3098** | done d=0.996 | 3661 | 3677.6 | 4, 62 (the stale walk) |
| 21 | 1, +10 | true, 427 | done | 442 | 459.1 | 9, 144 |
| 22 | 1, −10 | true, 318 | done | 424 | 443.8 | 8, 124 |
| 23 | 2, +10 | true, 427 | done | 498 | 512.0 | 6, 97 |
| 24 | 2, −10 | true, 427 | done | 478 | 494.5 | 11, 177 |
| 25 | 3, +10 | true, 323 | done | 463 | 480.8 | 10, 163 |
| 26 | 3, −10 | true, 422 | done | 446 | 464.6 | 9, 146 |
| 27 | 4, +10 | true, 318 | done | 429 | 447.1 | 8, 129 |
| 28 | 4, −10 | true, 428 | done | 412 | 428.3 | 7, 112 |
| 29 | 5, +10 | true, 425 | done | 496 | 507.7 | 6, 96 |
| 30 | 5, −10 | true, 424 | done | 477 | 494.4 | 11, 178 |
| 31 | 6, +10 | true, 319 | done | 475 | 485.3 | 11, 175 |
| 32 | 6, −10 | true, 321 | done | 463 | 483.5 | 10, 164 |
| 33 | 7, +10 | true, 323 | done | 477 | 483.7 | 11, 178 |
| 34 | 7, −10 | true, 318 | done | 479 | 496.1 | 11, 179 |
| 35 | 8, +10 | true, 324 | done | 445 | 465.6 | 9, 144 |
| 36 | 8, −10 | true, 318 | done | 446 | 458.8 | 9, 147 |
| 37 | 9, +10 | true, 317 | done | 446 | 454.6 | 9, 146 |
| 38 | 9, −10 | true, 318 | done | 446 | 457.2 | 9, 145 |

**The grade.** Sorted, the 20 client-clock values are 412 … 496, 498, 3661, +inf; the nearest-rank p90 is the 18th, 498, under 500. The two defect legs hold the top two ranks, so the gate read the 18th clean value: over the 18 clean legs alone the p90 is 496 (min 412, max 498, mean 457.9). Against pass 1: pass 1's live legs read 516 at nearest-rank p90 on the host figure `cmd_motion_host_ms` (n = 10, a zombie attacking during several); this run's host figure over the 18 clean legs reads 507.7 at p90, and its client-clock figure 496. The latency is dominated by the walk's ramp to `MOTION_EPS` 0.2 tiles, not the pipe: the first position change comes 6–11 ticks (96–179 ms) after the ack on every clean leg, as in pass 1 (95–181 ms), and the rest is the walk's acceleration and the 6-tick frame period.

**Why the first leg failed: a detour out of a house, read as no progress — a defect, not a one-off.** The `agent0` character starts at (10997.5, 9699.5) inside building 8 (the r=15 scan, `state.log` seq 1105: `room` `livingroom`, the room spanning about x 10994–11000, y 9696–9701, a closed window at (11001, 9699) on the straight line east, and a door at (10995, 9701) on its south-west corner). The target (11007.5, 9699.5) is outside to the east. `ISWalkToTimedAction`'s path leaves by the south-west door and walks around the house: frames seq 1109–1123 go south-west to the door square (10995.5, 9701.2), 1129–1144 west to x 10993.0, 1151–1182 north along x 10993 to y 9695.5, and only then east (frames 1183 on). The whole first stretch leads away from the target: its Euclidean distance grows from 10.0 to about 14.6 at the north-west corner and falls below its starting value only about 5 tiles into the eastward stretch. Pass 2's stuck rule (`PZAgent_Act.lua` lines 8–9, 24–25 and 102–135) counts the ticks since the best distance last shrank by `PROGRESS_EPS` 0.05 tiles; on this path it never shrank, so the goal cleared and re-queued the walk at `STUCK_TICKS` 90 three times (the pauses at frames 1124–1128, tick 11310; 1138–1150, tick 11394; 1154–1155, tick 11490) and failed `stuck` at tick 11580, 363 ticks after the ack (`goal_failed` seq 1169), with the character healthy, walking and on a valid path. The start square is the fixture's, so every boot of `agent0` reproduces it; and any goto whose path must first lead away from the target for more than 90 ticks (about 3 tiles at the measured 2.17 tiles/s) fails the same way. It is not an edge (`no square`) failure; the target square was found and the path walked.

**Why the second leg read 3661 ms: the failed goal's walk was left queued.** A goal that fails `stuck` returns without clearing the queue (`PZAgent_Act.lua` line 130), and `A.start` clears only a *running* old goal (lines 65–66), so the fourth walk carried on after the failure (`action.n` 1 with the goal `idle`, frames 1171–1201), walking east along y 9695.5. The driver's settle wait timed out (`settled` false, 3098 ms) and it sent cmdSeq 20 from the moving character's position (x0 10997.44, y0 9695.5); the new walk queued behind the stale one (`action.n` 2, frames 1203–1217), which carried the character east to x 11001.05 before the new walk took over (`action.n` 1 from frame 1218) and turned west. The −x crossing of 0.2 tiles came at frame 1239, 3661 ms after the ack. Pass 1's recommendation 2 (a new goal clears the queue even when the old goal has ended) is not in this Lua.

**The void machinery did not fire, as it should not.** Health reads 100 in every one of the 2187 frames, `nZombies` 0 and `zombies` empty in every frame, every moodle 0, and no `hit`, `zombie_enter` or `lua_error` event: `min_health` 100 and `max_nZombies` 0 on every leg, `voided_legs` 0. The fixture change to `agent0` removed the pass-1 confound; the `dead` paths (`goto` failing `dead`, `A.start` refusing a dead player) were not exercised.

**Server.** `readings.server[*].rttMs` 1010.6, 506.0, 2013.0 (n = 3); `stats.all` acks complete (`missing` `{}`).

## Pass 3

Pass 3 is the last of spec § 4.1's three. What this run says it needs:

1. **The scan emitted in parts, one per tick.** Each chunk's squares go out as their own line (`scan_part`, with the job's id, the part index and count) on the tick that walks them, and a closing line carries `scanMs`, `scanTicks` and the step list. At 60 squares about 6 KB (103 bytes per square at r=15), so about 2.8 ms of emit at 0.45 ms per KB (1.7 ms on the fit's intercept; both extrapolate below the smallest line measured here, 16.7 KB) beside about 1 ms of walk: a part's tick near 3–4 ms, under the 5 ms gate but not by much. A 30-square part (about 3 KB, near 1.5 ms of emit) would leave margin; the per-part tick is then what `scan_step_ms` grades, with the part's emit measured on its own tick. The driver reassembles the parts and checks `missing` and the square count.
2. **A rate-60 window for the tick cost.** At 60 Hz every tick is a frame tick, so a 60 s window gives 3600 integer readings whose mean resolves the per-tick cost below a millisecond (the boundary phase averages out, as the means above show); the gate's `p99 < 2 ms` still reads the 1 ms clock and needs either that mean beside it or a finer clock, if one is reachable from Lua (not read here). Pass 1's recommendation 4 stands.
3. **The goto stuck rule and the stale walk** (section 3): progress read as distance-to-target fails a detour, so the stuck count should reset on movement (a position change of at least `PROGRESS_EPS` within the window) now that a dead body fails `dead` at once and no longer needs the progress test to stop its drift; and every terminal goto state (`done`, `failed`, `superseded`) clears the queue, and `A.start` clears it whatever the old goal's state. The motion phase should also start from a square outside the house, or the driver should log the first leg's start square, so the 20 legs measure the pipe and not the floor plan.

## Do not cite from this file

| Key | Value in the file | Why not |
|---|---|---|
| everything measured here, as a population | — | `n = 1` boot, one fixture, one character. |
| every wall-clock leaf, by one wildcard sentence: `*PyMs`, `*wallMs`, `wallMs`, `wall`, `wall_*`, `*_wall`, `epoch_ms_*`, `took`, `settleMs`, `phase_walls.*`, `timeline`, `wall_seconds`, `server_launch_wall`, `server_started_wall`, `session_ready_wall`, `hello_wait_ms`, `memory[*].wall`, `memory_wait[*].wall`, `steps[*].*wall*`, `frame_wallMs_*`, in `a_pipe_2.json` and every line of `state.log` (wildcard) | host epoch ms and seconds | This host's timing, cited only as a difference within this run, never as a reading. |
| `readings.rates.*.tickMs` and every `cost.*Ms` (`pollMs`, `actMs`, `scanStepMs`, `senseMs`, `linkMs`, `scanEmitMs`), `tick_p99_ms_at5` 2, `scanMsPerTick`, `scanStepMaxMs`, `scanMs` | integers 0–45 | Quantised to a 1 ms clock: a 2 is 1–2 ms; cite a small value as a bound, never as a value, and a mean over many frames only as this clock's mean. |
| `scan15_ms_max` 45 and `readings.scans.*[*].scanEmitMs` | 7, 19–22, 44–45 | The pass-2 emit shape (the whole line serialised and appended in one tick), superseded by pass 3's parts; cite only as the reason for them, with the 0.45 ms per KB fit. |
| `readings.motion[0]` and `readings.motion[1]` (cmdSeq 19 and 20), and `cmd_motion_p90_ms` 498 as a latency | `failed stuck`, +inf; `settled` false, 3661, 3677.6 | Defect legs: a detour read as no progress, then the failed goal's walk left queued; the p90 rests on them at its top two ranks. Cite the clean-leg figures with their legs named. |
| `readings.motion[*].cmd_motion_host_ms` | 428.3–3677.6 | Two clocks (the host's write time against the client's frame stamp) and frame-quantised; informational, never the graded figure. |
| `readings.server[*].rttMs` | 1010.6, 506.0, 2013.0 | `n = 3`. |
| `readings.server[*].ack.mult` | 4.790… | getMultiplier, not the true multiplier (#3762). |
| `constants`, `preboot`, `profile`, `fixture`, `argv`, `memory`, `memory_wait` | the driver's tables and checks | Written before or around the run; not readings. |
