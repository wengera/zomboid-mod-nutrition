# `a_pipe-20261026-101003` reading guide

**`a_pipe-20261026-101003/a_pipe.json`** (with `state.log` and `a_grade.txt`) — produced by `testing/agent/drivers/a_pipe.py` at `driver_commit` `3e550f1f` (Plan 21 Task 8 fix 1), unedited since, which imports `testing/experiments/xlib.py` (`xlib_commit` `45c49217`); on HEAD `7c1a07be` at the boot (`preboot.commit`; harness Lua `ee23b53c`, clean; harness Python `52a7de93`); the agent mod `testing/PZAgent/PZAgent` loaded by path from the tree, whose last commit at that HEAD is `a184da0c` (Plan 21 Task 9 fix 1; `preboot.driver_checks.agent_lua_dirty` false), so the Lua under test is `PZAgent_Act.lua`, `PZAgent_Main.lua`, `PZAgent_Sense.lua`, `PZAgent_Link.lua` and `shared/PZAgent_Core.lua` at `a184da0c`. Fixture `agent` (provisioned `prov-20261026-092028`), build `42.21.0`; profile `testing/profiles/agent-nozombies.toml` (PZTestKit + PZAgent, `[sandbox]` `Zombies = 6`, user `admin`). **Plan 21 Stage A, pass 1.** `doctor_clean` true; `lint_errors` empty; `server_error_count` 0; `admin_lua_error` false; `client_lua_errors` empty; `lua_errors` 0; no phase error; `finished` true. Free memory 15.43 GB at the preboot read and the memory wait, 2.31 GB at ready, 16.09 GB after teardown (`memory`, `memory_wait`). 435.9 s wall (`wall_seconds`; server stopped rc 0, client quit rc 0, `timeline`).

Files, byte-identical to the run copy under `testing/runs/a_pipe-20261026-101003/`:

| File | Source | Bytes | sha256 |
|---|---|---|---|
| `a_pipe.json` | the driver's auto-copy of `testing/runs/a_pipe-20261026-101003/a_pipe.json` | 81680 | `6a23048f1a95b801df3016303695677ddd9d6460dc71283d1d2e76286edf2ead` |
| `state.log` | `testing/runs/a_pipe-20261026-101003/clients/admin/Lua/pzagent/admin/state.log`, copied by the write-up (`cmp` equal; LF endings, 3082 lines: 1 `hello`, 2922 `frame`, 38 `ack`, 106 `event`, 15 `scan`) | 3572263 | `da58ad84b1fb5c5a9205638c93368bc7e2fffc8624c6ac8f4cbd42b6d5a207a4` |
| `a_grade.txt` | the exact stdout of `python testing/agent/drivers/a_grade.py testing/artifacts/a_pipe-20261026-101003/a_pipe.json` (exit 1), written by the Windows console with CRLF endings | 382 | `46aa07415d09df6b7cbb42cc20893f925d54fc67f17ed31fc29a704dca8524a8` |

`state.log` is the only evidence of the motion defect below; the hashes are of the working-tree bytes as written (a checkout under `core.autocrlf=true` may rewrite line endings, so re-hash the blob, `git show <commit>:<path> | sha256sum`). The client console `testing/runs/a_pipe-20261026-101003/clients/admin/console.txt` (282717 bytes) and the server logs under `testing/runs/a_pipe-20261026-101003/server/Logs/` are per-machine and untracked; they are cited below by path and line as corroboration only.

## How to read it

The schedule is `a_pipe.py`'s docstring and spec § 4.1: sit still; `rate 2`, `rate 5`, `rate 10` for 60 s each; `scan 5`, `scan 10`, `scan 15` five times each; `goto` +10 tiles in x and back, ten round trips; three server `stats.all` calls; teardown (`phase_walls`: rates 56.14–236.719 s, scans to 238.606, motion to 420.313, server to 425.602).

- **Rates:** `readings.rates.<2|5|10>`: `frames` (121, 301, 600 against `expected` 120, 300, 600), and per frame the client's `cost` leaves `pollMs`, `actMs`, `senseMs`, `linkMs` and their sum `tickMs`, each an integer read off a 1 ms clock; `dropped_max` 0 at every rate.
- **Scans:** `readings.scans.<5|10|15>[*]`: `scanMs`, `squares`, `bytes`, `missing` per scan.
- **Motion:** `readings.motion[*]` (20 legs, `trip` 0–9 with `dx` ±10): `args`, `cmdSeq`, `ack`, `goal` (the goal's end state), `first_motion` (the first frame moved at least `MOTION_EPS` 0.2 tiles in the commanded direction after the settle), `cmd_motion_host_ms`. In `state.log` each frame's `goal.seq` is the `cmdSeq` of the goal it reports; `action.class`/`action.n` is the timed-action queue; `health`, `moodles` and `zombies[*].{id,dist,hasTarget}` are the player's state; `event` lines carry `hit`, `zombie_enter`/`zombie_leave`, `goal_done`/`goal_failed`.
- **Server:** `readings.server[*]`: `rttMs` and the `stats.all` ack.
- **Pipe health:** `hello`, `mode` `append`, `missing` `[]`, `gaps` 0, `bad` 0, `lines_read` 3025.

## Verdicts

`a_grade.txt`: **NO-GO** (`pass.hello`, `pass.gaps`, `pass.lua_errors` true; three gates false).

1. **Per-tick cost at 5 Hz** (`tick_p99_ms_at5` 2 against `< 2`, false). Over the 301 frames of `readings.rates.5`, `tickMs` read 0 on 118 frames, 1 on 152, 2 on 30 and 3 on 1 (p50 1, p99 2, max 3, mean 0.714). The clock is 1 ms resolution, so a p99 of 2 says the 99th-percentile tick lies between 1 and 2 ms (or a little above, since `tickMs` sums four rounded leaves); the gate `< 2` sits at the clock's resolution and cannot pass with an integer clock unless 99 % of ticks read 0 or 1. That is a finding about the gate and the clock, not an excuse for the cost.
2. **15-tile scan** (`scan15_ms_max` 21 against `< 5`, false). The five r=15 scans read 17, 14, 21, 14, 18 ms.
3. **Command to motion** (`cmd_motion_p90_ms` `Infinity`, `cmd_motion_paired` 11 of `cmd_motion_n` 20, false). `Infinity` is the grade's p90 with 9 legs unpaired (no `first_motion`), not a latency. The 9 unpaired legs and one of the paired ones are the defect below, a dead character, not the pipe.

### Per-key cost by rate (frames, 1 ms clock)

| Rate | Key | p50 | p99 | max | mean | counts (ms: frames) |
|---|---|---|---|---|---|---|
| 2 Hz (121) | `tickMs` | 1 | 2 | 3 | 0.736 | 0:48 1:58 2:14 3:1 |
| 5 Hz (301) | `pollMs` | 0 | 1 | 1 | 0.193 | 0:243 1:58 |
| 5 Hz | `actMs` | 0 | 0 | 1 | 0.003 | 0:300 1:1 |
| 5 Hz | `senseMs` | 0 | 1 | 1 | 0.292 | 0:213 1:88 |
| 5 Hz | `linkMs` | 0 | 1 | 2 | 0.226 | 0:235 1:64 2:2 |
| 5 Hz | `tickMs` | 1 | 2 | 3 | 0.714 | 0:118 1:152 2:30 3:1 |
| 10 Hz (600) | `tickMs` | 1 | 2 | 3 | 0.698 | 0:257 1:272 2:66 3:5 |

Percentiles are nearest-rank. No single key reaches 2 ms more than 2 times in 301 frames at 5 Hz; the 2s and 3s in `tickMs` are sums of 1 ms leaves. The cost per frame does not rise with the rate (mean 0.736, 0.714, 0.698 ms at 2, 5, 10 Hz).

### Scan cost by radius

| r | squares | bytes | `scanMs` ×5 | mean | ms per square |
|---|---|---|---|---|---|
| 5 | 121 | 16603–16604 | 4, 3, 3, 4, 3 | 3.4 | 0.028 |
| 10 | 441 | 49328–49330 | 8, 8, 7, 7, 6 | 7.2 | 0.016 |
| 15 | 961 | 100596–100597 | 17, 14, 21, 14, 18 | 16.8 | 0.017 |

A least-squares line over the 15 readings is `scanMs ≈ 0.91 + 0.0162 × squares` (predicting 2.9, 8.1, 16.5 ms): the per-square cost is constant at about 16–17 µs once a fixed cost of about 0.9 ms is taken out, which is why r=5 reads high per square. Bytes run 137, 112, 105 per square. The r=15 spread (14–21 ms) is wider than the r=10 one; with five readings a cause cannot be named. At this rate a 2 ms tick holds about 60–70 squares beside the fixed cost, so r=15 needs about 15 ticks.

## The motion defect: the character was killed by zombies during the motion phase

**Finding.** Trips 0–4 out and back (cmdSeq 19–27) and trip 4's return up to the death ran normally; the character was then killed by two zombies at 10:15:30 (host time) at (10730, 10629, 0), and every later leg (cmdSeq 29–38) commanded a dead character. The walk machine behaved as written throughout: it reported `stuck` after its three replans on a body that could not walk, and it ran to the driver's 30 s timeout on cmdSeq 35 because the dead player's position kept drifting, which reset its stuck counter every tick.

Evidence, all from `state.log` unless named:

- **Zombies were present despite `Zombies = 6`.** The first frame (seq 2) already lists zombie 12564 at dist 7 (`nZombies` 1). During the rates phase zombies entered and left at the sense radius (`zombie_enter` dist 11.4–12.0). Zombie 12557 first appears with `hasTarget` true at frame seq 1230 (tick 11784, dist 9.8), during the first motion leg.
- **The hits and the death.** The first `hit` event is seq 1373 (tick 12600, health 98.77), during cmdSeq 22; 58 `hit` events in all; health falls to 61.0 by the end of cmdSeq 26 and to 13.9 by the end of 27, with moodles BLEEDING, INJURED, PAIN and PANIC at 4. Health first reads 0 at frame seq 2070 (tick 16356), during cmdSeq 28. Corroboration: the server log `testing/runs/a_pipe-20261026-101003/server/Logs/2026-10-26_10-10_user.txt` line 7, `user admin died at (10730,10629,0) (non pvp).` at 10:15:30.828, and `..._PerkLog.txt` line 3 `[Died]`; the client console `testing/runs/a_pipe-20261026-101003/clients/admin/console.txt` lines 3358–3370 carry eleven `Combat: "admin" hit "admin" "zombie"` messages from 10:14:27.644 to 10:15:27.994, and lines 3371–3379 `SendEatBody`/`ReceiveEatBody` for zombies 12557 and 12555; the server's `stats.all` after the motion phase reads `ZombieInfection` 0.5189 and `Pain` 99.44 (`readings.server[0].ack.stats`).
- **Every failed leg is a dead leg.** Per goto goal, ticks from the ack to the first position change: cmdSeq 19–28 (alive at the start) 6, 6, 11, 10, 7, 11, 9, 7, 10, 11 ticks (95–181 ms at the measured 59.9 ticks/s); cmdSeq 29–38 (`health` 0 at every frame) none, except 29 (239 ticks, a 0.25-tile jump of the body) and 35 (191 ticks, the drift below). No live leg failed to start.
- **cmdSeq 28 (`failed stuck`) moved and was then killed.** It walked from x 10731.05 to 10730.01 (frames 2016–2037), was held in place by the attack from tick 16194 (frame 2037) with the queue empty (`action.n` 0 from frame 2035), was re-queued at tick 16284 (frame 2056, `action.n` 0 → 1: exactly `STUCK_TICKS` 90 later, the first replan), moved 0.9 tiles, died at tick 16356, and its body snapped to (10730.12, 10629.44) at frame 2076; the remaining replans ran out and it failed at tick 16662 (`goal_failed` seq 2122).
- **The replans happened, and are observable.** On a live character: during cmdSeq 22 the hit at tick 12600 emptied the queue (`action.n` 0 at frame 1374) and froze the position from tick 12606; the walk was re-queued at tick 12702 (frame 1391) and the leg finished `done`: the replan recovered a walk interrupted by a hit. On the dead character: each failed leg runs 360–365 ticks from ack to `goal_failed` (cmdSeq 30–34, 36–38), against 1 + 4 × 90 = 361 for three replans and a fourth stuck window; `action.n` reads 2 at each new goal's first frames (the previous goal's walk, never cleared because the goal had already ended `failed`, plus the new one) and 1 after.
- **cmdSeq 35's "12 tiles in y" is the body, not a walk.** From tick 19206 (frame 2561) the frame position moves from (10730.23, 10629.22) to (10732.52, 10641.54) by frame 2834, at about 0.47 tiles/s (0.375 tiles per 48 ticks), `moving` false and `health` 0 throughout; a zombie id 12663 appeared at dist 0 four seconds after the death (`zombie_enter` seq 2111, tick 16602) and stays at dist 0 in every later frame; the sandbox has `Reanimate = 3` (console line 3209). Each position change reset `still`, so the goal neither stuck nor reached its target (the target was +10 in x, the drift was +12 in y) and ran to the driver's `GOAL_TIMEOUT_S` 30; cmdSeq 36 then superseded it (`goal_failed` `superseded`, seq 2836). The server's own record of the player stayed at the death square (`..._user.txt` line 10, `disconnected player (10730,10629,0)`).

**The candidate hypotheses against this data.** (a) An asynchronous pathfinder outrun by `STUCK_TICKS`: excluded for this run, since every live leg moved within 11 ticks and the one replan on a live leg recovered the walk. (b) The target square: excluded, since square 10721 (cmdSeq 24, 26, 27's return targets 10721.03–10721.05) succeeded alive and failed only dead (cmdSeq 28); the +10 target squares 10740 were never commanded alive, and the r=15 scans (x 10706–10736, y 10615–10645) do not reach them, so their reachability is not read here (rows 10629–10630 of the scan hold no solid square). (c) State left by `ISTimedActionQueue.clear` at `done`: excluded, since the clear at `done` preceded nine successful legs. (d) A save or chunk load: nothing in the server debug log between 10:13:14 and 10:15:34 (`2026-10-26_10-10_DebugLog-server.txt` lines 2109–2110); excluded as the cause.

**What this run cannot settle.** Why zombies were present under `Zombies = 6` (the fixture's saved world already held them at the first frame; whether the setting stops spawning only is not read here); which object the client frame read after the death (the dead `IsoPlayer`, whose position followed the reanimated body, or another), since the frame does not name it; and whether a live character would have reached the 10740 targets.

**The command-to-motion latency on live legs**, for the report and never cited as a gate pass: `cmd_motion_host_ms` on the ten live legs (cmdSeq 19–28) reads 315, 516, 491, 575, 428, 488, 453, 330, 471, 493 (nearest-rank p90 516, over the 500 ms gate), but the first position change comes 95–181 ms after the ack; the rest is the walk's ramp to `MOTION_EPS` 0.2 tiles (ack to that frame 293–563 ms) and the frame period. Several of these legs ran while a zombie was attacking.

## Pass 2

1. **The world, before the Lua:** the motion legs need a living, unattacked character. Either the `agent` fixture is re-provisioned with no zombies within the walk's reach, or the driver kills or removes the zombies before the motion phase; and the driver checks `health` > 0 and no `hasTarget` zombie at each leg's start and marks a leg on a dead or attacked character as void, not as a motion failure (cmdSeq 29–38 here).
2. **The walk:** no change to `STUCK_TICKS` or the replan is called for by this run (every live leg moved within 11 ticks; the replan recovered a hit-interrupted walk at exactly 90 ticks). Two small fixes the log shows: `goto` should fail at once with a new reason (`dead`) when `health` is 0, instead of 361 ticks of replans; and the stuck test should read progress toward the target, not any position change, so a drifting body or a pushed character cannot hold a goal open past its budget (cmdSeq 35). A new goal should clear the queue even when the old goal has ended, so a stale walk is never left beside the new one (`action.n` 2).
3. **The scan:** chunked, N squares per tick with the `scan` line written when the last chunk completes, so no tick carries more than about 1 ms of scan: at 0.0162 ms per square, 60 squares per tick, r=15 in 17 ticks (under 0.3 s at 60 ticks/s). The gate then reads the per-tick chunk cost, and the whole-scan wall is reported beside it.
4. **The tick-cost gate** needs a finer clock (`PZA.now` is `getTimestampMs`, `PZAgent_Core.lua` line 8, a 1 ms clock; a sub-millisecond source if one is reachable from Lua, not read here, or a cost summed over many ticks and divided) before `p99 < 2 ms` can separate 1.2 ms from 1.9 ms; with the present clock the reading is "between 1 and 2 ms".
5. **The motion gate** reads the first position change after the ack (here 95–181 ms) as well as the 0.2-tile crossing, so the ramp of the walk animation is not graded as pipe latency.

## Do not cite from this file

| Key | Value in the file | Why not |
|---|---|---|
| everything measured here, as a population | — | `n = 1` boot, one fixture, one character. |
| every wall-clock leaf, by wildcard: `*PyMs`, `*wallMs`, `wallMs`, `wall`, `wall_*`, `*_wall`, `epoch_ms_*`, `took`, `phase_walls.*`, `timeline`, `wall_seconds`, `server_launch_wall`, `server_started_wall`, `session_ready_wall`, `hello_wait_ms`, `memory[*].wall`, `memory_wait[*].wall`, `steps[*].*wall*`, in `a_pipe.json` and every line of `state.log` | host epoch ms and seconds | This host's timing, cited only as a difference within this run, never as a reading. |
| `readings.rates.5.tickMs` p99 (`tick_p99_ms_at5` 2) and every `cost.*Ms` | integers 0–3 | Quantised to a 1 ms clock: a 2 is 1–2 ms; cite as a bound, never as a value. |
| `readings.motion[*]` for cmdSeq 28–38 (trips 4 return to 9), `cmd_motion_p90_ms`, `cmd_motion_paired` | `failed stuck`, a timeout, `Infinity`, 11 | A defect reading: the character was dead (cmdSeq 29–38) or dying (28). Cite the failure and its cause, never a latency; cmdSeq 35's `cmd_motion_host_ms` 22784.9 is a reanimated body's drift. |
| `readings.motion[*].cmd_motion_host_ms` for cmdSeq 19–27 | 315–575 | Host-side, frame- and poll-quantised (10 Hz frames, 0.1 s poll), with a zombie attacking during several legs; cite only as this run's live-leg reading beside the tick count to the first position change. |
| `readings.server[*].rttMs` | 1509.0, 2011.8, 1762.9 | `n = 3`, taken with the character dead. |
| `readings.server[*].ack.mult` | 4.799… | getMultiplier, not the true multiplier (#3762). |
| `constants`, `preboot`, `profile`, `fixture`, `argv` | the driver's tables and checks | Written before the run; not readings. |
