# `p22_probe-20261027-032502` reading guide

**`p22_probe-20261027-032502/p22_probe.json`** (with `state.log`) — produced by `testing/agent/drivers/p22_probe.py` at `driver_commit` `1261079a` (Plan 22 probe driver residual), unedited since, which imports the frozen `testing/agent/drivers/a_pipe.py`, `a_pipe_2.py` and `a_pipe_4.py`, `testing/agent/drivers/_dlib.py` and `testing/experiments/xlib.py` (`preboot.xlib_commit` `45c49217`); on HEAD `1261079a` at the boot (`preboot.commit`; `preboot.harness_lua_commit` `ee23b53c`, `preboot.harness_lua_dirty` false; `preboot.harness_py_commit` `52a7de93`); the agent mod `testing/PZAgent/PZAgent` loaded by path from the tree (`profile.sources.PZAgent`; `preboot.agent_commit` `1261079a` is the last commit under `testing/agent` or `testing/PZAgent`; `preboot.driver_checks.agent_lua_dirty` false, `driver_dirty` false), and the last commit under `testing/PZAgent` is `83a1e0ba` (Plan 22 probe Lua fix 1), so the Lua under test is PZAgent 0.2 (`hello.modVersion` `0.2`): `PZAgent_Act.lua`, `PZAgent_Main.lua`, `PZAgent_Sense.lua`, `PZAgent_Link.lua`, `PZAgent_Motor.lua`, `PZAgent_Bench.lua` and `shared/PZAgent_Core.lua` at `83a1e0ba`. Fixture `agent0` (`fixture.provision_run` `prov-20261026-102802`, `fixture.build` `42.21.0`; `hello.build` `42.21`; `build` `42.21.0`); profile `testing/profiles/agent-nozombies.toml` (`profile.name` `agent-nozombies`; PZTestKit + PZAgent, `profile.sandbox.Zombies` 6, user `admin` on a `-debug` client, a 90-minute day).

**Plan 22's agent-base probe**, the one live session Angus approved on 2026-10-27 ("K1, approved for the probe session, no JDK for now") before the agent's base is designed: the three experiments X1–X3 of `.superpowers/sdd/2026-10-27-plan-22-agent-base-design/plan-22-options.md` § 4, on the Lua ↔ Python interface `probe-interface.md` beside it (both gitignored workspace files; the driver's docstring restates every phase, reading and prediction and is the committed source). The driver has no GO/NO-GO: every verdict is a prediction recorded with its falsifier.

## 0. The run

- **Wall.** 296.4 s (`wall_seconds`; against `constants.BUDGET_S` 720, counted from the memory gate, the boot included). Server started at 47.4 s, the client ready at 83.7 s (`timeline`; `client_seen[0].ready` 35.9 s after its launch), client quit rc 0 at 288.8 s, server stopped rc 0 with 0 errors at 296.4 s. Phases (`phase_walls`, seconds from the gate): `hello_and_map` 84.964–85.847, `x2_bench` 85.848–105.969, `x1_motor` 105.971–216.123, `x3_load` 216.126–285.193, `server` 285.2–286.709.
- **Hello and bench line.** `hello`: `mode` `append`, `rate` 5, `modVersion` `0.2`, `build` `42.21` (`hello_wait_ms` is a wall leaf). The `bench` line (`state.log` seq 2; `bench_info`): `json21Bytes` 2740, `noSortBytes` 2740, `compactBytes` 1244, `squares` 20.
- **Pipe health.** `gaps` `[]`, `bad` 0, `missing` `[]`, `lua_errors` 0 (`lua_error_lines` `[]`), `client_lua_errors` 0 (`logs.clients.admin` `[]`), `admin_lua_error` false, `server_error_count` 0, `bus_dead` null; `verify` both `ping` rows ok. Every frame's `motor.updErrors` reads 0 and none carries `damageDropped` (`state.log`, all 1531 frames).
- **Stops.** `finished` true; `phase_errors` `{}`; `notes` `[]`; the artifact carries no `abort`, `error` or `budget_stop` key. **The X1 deadline cut nothing**: `readings.motor.deadline_skipped` 0, X1 ending at 216.123 s against `constants.X1_DEADLINE_S` 450.
- **Arms not run.** The `toggle` arm was skipped by rule (`readings.motor.toggle_skipped`: `forcerun` 3.707733093237295 ≥ `TOGGLE_IF_BELOW` 1.3 × `walk` 2.051212391013422), so `readings.motor.toggle` is `[]` and `readings.motor.paces.toggle` null; the client's "toggle to run" option was never written.
- **Frames.** The driver read 1675 lines (`lines_read`), 1523 of them frames (`frames_n`); `state.log` holds 1683 lines, seq 1–1683 without a gap (line *n* is seq *n*): 1 `hello`, 1 `bench`, 1531 `frame`, 49 `scanPart`, 43 `ack` (every one `ok`), 58 `event` (40 `goal_done`, 6 `item_added`, 12 `hit`; `events`), the 8 lines after the driver's last read being frames. X1 ran at `rate 10` (`readings.motor.rate_on`, ack seq 175): every consecutive frame pair from seq 176 to 1292 is 6 ticks apart; X3 at `rate 5` (`readings.motor.rate_back`, ack seq 1293): every pair from 1294 to 1683 is 12 ticks apart. `nZombies` reads 0 on every frame.
- **Memory.** Free 15.62 GB at the preboot read and the memory wait, 2.88 GB at ready, 16.63 GB after teardown (`memory`, `memory_wait`).

Files, byte-identical to the run copy under `testing/runs/p22_probe-20261027-032502/`:

| File | Source | Bytes | sha256 |
|---|---|---|---|
| `p22_probe.json` | the driver's auto-copy of `testing/runs/p22_probe-20261027-032502/p22_probe.json` (`cmp` equal); LF endings, 8952 lines | 191181 | `033d5688f2e4f33dc18d1f736f32fbe441d08e37b6d73f0277efa5f8468f3292` |
| `state.log` | `testing/runs/p22_probe-20261027-032502/clients/admin/Lua/pzagent/admin/state.log`, copied by the write-up (`cmp` equal); LF endings, 1683 lines | 1886865 | `079e0b4719dbce1cde142c408b4571c4759abcad90f4eb249925985bd94790f1` |

`state.log` is the only evidence of the game-time stamps (`gameMin`, `worldAge` in game hours), the per-part body health, the `motor` block of each frame and the frames between the driver's leg rows; the hashes are of the working-tree bytes as written (re-hash a checkout's blob with `git show <commit>:<path> | sha256sum`). The bench file `Lua/pzagent/admin/bench.log` (8250000 bytes, the bench arms' own writes), the client console, `options.ini` and the server's logs are per-machine and untracked; nothing below rests on them but the one `options.ini` line named in § 1.

## How to read it

The schedule is the driver's docstring: `hello_and_map` (the hello, the bench line, a `scan 15`, the line choice), `x2_bench` standing, `x1_motor`, `x3_load`, `server` (`stats.all admin`). The readings, verbatim from its docstring:

- **pace** (tiles/s) of a leg: over the leg's frames with `moving` true, consecutive pairs' `hypot(dx, dy)` summed over the `wallMs` span between the first and last moving frame (the Stage C guide's measure); null under 2 moving frames. A leg's frames are those with seq above its ack's up to its goal's end frame. Each arm's pace (`readings.motor.paces.<arm>`) is the median over its legs.
- **endurance slope**: (last − first endurance) over the leg's frames, per second of the client's clock.
- **flags**: counts of the leg's frames reading `running`, `sprinting`, `motor.forceRun`, `motor.updRunning`, `motor.updForceRun` and `motor.autoWalk` true, beside `frames`. `running`, `sprinting` and `motor.forceRun` are read in `OnTick` by the sense frame (`isRunning`, `isSprinting`, `isForceRun`); `motor.updRunning` and `motor.updForceRun` are read inside the `OnPlayerUpdate` handler after its own asserts (`PZAgent_Motor.lua`), that is, inside the player update before `UpdateInputState`.
- **heading error** (autowalk legs): the angle between the commanded world vector and the displacement from the first to the last frame of the leg; `heading_signed_deg` keeps its sign.
- **first_move** and **cmd_move_ms**: the first frame after the ack whose position moved more than `MOVE_EPS_TILES` 0.01 tiles, and its `wallMs` minus the ack's (the client's clock), frame-quantised at about 100 ms (§ 4).

## 1. X1 motor

**The line.** Chosen live, no fallback (`readings.line` carries no `fallback` key): the `scan 15` (`readings.line.scan`: 49 parts of 49 declared, `map_squares` 961) gave 1302 candidate squares (`candidates`) and the nearest clear 12-square run lies along −x (`dir` `-x`, `dist` 4.0 from the settled position (10997.5, 9699.5), `me`), A = (10993, 9699) and B = (10982, 9699) (`ax`, `ay`, `bx`, `by`; walk targets A (10993.5, 9699.5), B (10982.5, 9699.5), midpoint M (10988.0, 9699.5), `targets`), checked as 36 squares (`strip_squares`: the line and a row either side), every one outdoors and clear. A straight line, so every pace below is a straight walk with no turn.

**The pathed arms** (`readings.motor.legs[*]`; the approach `goto A walk` read 1.5356354678243147 tiles/s over 22 frames and is ungraded, `readings.motor.approach`). Flags are running / sprinting / forceRun / updRunning / updForceRun of `frames`; every goal ended `done` with `d` 0.93–0.99 (`goal.detail`), every leg `settled` true, none voided:

| arm | leg | to | pace | endurance slope (/s) | frames | flags r / s / fR / uR / uFR | first_move seq | cmd_move_ms |
|---|---|---|---|---|---|---|---|---|
| `walk` | 0 | B | 2.051212391013422 | 0.0 | 52 | 0 / 0 / 0 / 0 / 0 | 182 | 180 |
| `walk` | 1 | A | 2.0794270833333335 | 0.0 | 47 | 0 / 0 / 0 / 0 / 0 | 240 | 162 |
| `walk` | 2 | B | 2.0371577574967406 | 0.0 | 48 | 0 / 0 / 0 / 0 / 0 | 292 | 129 |
| `setrun` | 0 | A | 2.003014605978261 | 0.0 | 48 | 47 / 47 / 0 / 47 / 0 | 346 | 146 |
| `setrun` | 1 | B | 2.0257302989130435 | 0.0 | 49 | 48 / 48 / 0 / 47 / 0 | 401 | 195 |
| `setrun` | 2 | A | 2.0038858607003047 | 0.0 | 48 | 47 / 47 / 0 / 47 / 0 | 455 | 148 |
| `forcerun` | 0 | B | 3.707733093237295 | −0.0012665489018295407 | 28 | 26 / 0 / 26 / 26 / 26 | 510 | 193 |
| `forcerun` | 1 | A | 3.73046875 | −0.001031041145324707 | 31 | 30 / 0 / 30 / 30 / 30 | 547 | 162 |
| `forcerun` | 2 | B | 3.702905011115228 | −0.001503314290727888 | 29 | 28 / 0 / 27 / 28 / 28 | 582 | 45 |
| `forcerun_tick` | 0 | A | 2.0506153873372335 | 0.0005386742678555576 | 56 | 0 / 0 / 55 / 0 / 0 | 622 | 213 |
| `forcerun_tick` | 1 | B | 2.032311480978261 | 0.0006242593129475912 | 49 | 0 / 0 / 48 / 0 / 0 | 683 | 213 |
| `forcerun_tick` | 2 | A | 2.0189511306805827 | 0.00045901538209982136 | 48 | 0 / 0 / 47 / 0 / 0 | 736 | 179 |
| `forcesprint` | 0 | B | 4.594582447473736 | −0.0072935933158511206 | 22 | 1 / 20 / 20 / 1 / 21 | 790 | 147 |
| `forcesprint` | 1 | A | 4.684016827968682 | −0.0047830988383762195 | 31 | 7 / 23 / 23 / 7 / 30 | 825 | 776 |
| `forcesprint` | 2 | B | 5.163445723684211 | −0.01172884635295553 | 21 | 1 / 19 / 19 / 1 / 20 | 854 | 42 |

**The medians** (`readings.motor.paces`): `walk` 2.051212391013422, `setrun` 2.0038858607003047, `forcerun` 3.707733093237295, `forcerun_tick` 2.032311480978261, `forcesprint` 4.684016827968682, `toggle` null. Against `walk`: `forcerun` 1.8075812672940474 (`verdicts.x1_forcerun_runs.observed.ratio`), `setrun` 0.9769275329456569 (`verdicts.x1_setrun_walks.observed.ratio`), `forcerun_tick` 0.9907854934389204 (`verdicts.x1_forcerun_tick.observed.ratio`); `forcesprint` reads 2.2835 × `walk` and 1.2633 × `forcerun` (the medians' quotients). The walk and `setrun` legs' endurance slope reads 0.0 because endurance stood at its full 1 on every frame from seq 176 to 502; `forcerun_tick`'s positive slopes are recovery after the force-run legs.

**The autowalk legs** (`readings.motor.autowalk[*]`, after the calibration leg `readings.motor.autowalk_calibration`). Each `(dx, dy)` is the wanted world vector along the line's axis (dx toward B), turned into the world vector `(vx, vy)` (−x line: `vx` = −dx) and sent as the input vector `(ix, iy)` (the inverse of `IsoPlayer.updateMovementFromInput` L3025–L3026); each leg follows its own `goto M` (`readings.motor.centre[*]`, all `done` within 1 tile):

| leg | arm | world `(dx, dy)` | sent `(ix, iy)` | s | pace | heading error° (signed) | displacement | frames / autoWalk | updForceRun on autoWalk frames | running | cmd_move_ms | voided |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| calibration | `walk` | (1, 0) | (−0.707107, −0.707107) | 1.5 | 1.9028946168042857 | 1.9891844975987512 (−1.989184497598842) | 2.8415560800582 | 16 / 15 | 0 | 0 | 113 | no (0 off-strip frames) |
| 0 | `walk` | (1, 0) | (−0.707107, −0.707107) | 3.0 | 1.942729086686262 | 0.3350032460755668 (−0.33500324607624066) | 5.845803048056987 | 31 / 30 | 0 | 0 | 147 | **left the strip** (3 off-strip frames, the first seq 995 at x 10981.9384765625, past B) |
| 1 | `forcerun` | (−1, 0) | (0.707107, 0.707107) | 1.5 | 3.7132606887328485 | 0.7835862126686675 (−0.7835862126683821) | 5.569856814970204 | 16 / 15 | 15 | 15 | 112 | no |
| 2 | `forcerun` | (2, 0) | (−1.414214, −1.414214) | 1.5 | 3.82360470868279 | 0.7751365999513493 (−0.7751365999515656) | 5.77494253485026 | 16 / 15 | 15 | 15 | 157 | no |
| 3 | `once` | (−1.95, 0) | (1.378858, 1.378858) | 1.5 | 2.0508320643081634 | 1.3794796624639436 (−1.3794796624637797) | 3.0829247556221877 | 16 / 15 | **0** | 0 | 178 | no |
| 4 | `forcerun` | (1, 0) | (−0.707107, −0.707107) | 1.5 | 3.7761755644013926 | 0.7841533227853373 (−0.7841533227848743) | 5.708542432459098 | 16 / 15 | 15 | 15 | 145 | no |
| 5 | `walk` | (−1, 0) | (0.707107, 0.707107) | 3.0 | 2.111850526837193 | 1.5172931177699753 (−1.5172931177701514) | 6.122263783780947 | 31 / 30 | 0 | 0 | 179 | no |

The calibration's signed error, −1.989184497598842°, is inside `CALIBRATE_TOL_DEG` 15, so no correction was applied (`readings.motor.autowalk_correction_deg` 0.0; every leg's `correction_deg` 0.0): the input-space rotation the driver applied was right as sent. Every goal ended `done` after its seconds (`goal.detail` `d=` 2.84–6.13 tiles); the `forcerun` legs' `forceRun` flag reads 14, 15 and 15 of 16 frames and `updForceRun` 16, 15 and 15. The median pace of the three unvoided `forcerun` legs is 3.7761755644013926, 1.8409481051037015 × `walk` (`verdicts.x1_autowalk_runs.observed`); the largest heading error over the six legs is 1.5172931177699753° (`verdicts.x1_autowalk_heads.observed.max`; `unread_legs` 0, `voided_legs` 1). Every signed error over the seven legs reads negative, −0.335 to −1.989°, on legs heading both ways along the line.

**Verdicts** (`verdicts.*`): `x1_forcerun_runs` as_predicted; `x1_setrun_walks` as_predicted; `x1_autowalk_runs` as_predicted; `x1_autowalk_heads` as_predicted; `x1_forcerun_tick` recorded; `x1_once_holds` **falsified** (`updForceRun` 0 of 15 autoWalk frames, `fraction` 0.0); `x1_endurance` as_predicted (`forcerun` −0.0012665489018295407 against `walk` 0.0).

**The reading in words.**

- **A force-run re-asserted from `OnPlayerUpdate` makes a pathed walk run.** With no client option changed, the `forcerun` legs ran at 3.70–3.73 tiles/s against 2.04–2.08 for the walk, `running` and `updRunning` true on all but the first one or two frames of each leg, and endurance fell (−0.00103 to −0.00150 a second) where the walk's held at 1. This is the jar research's door 2 (`jar-research-movement.md` line 148), and it passes the options' X1 line for arm (b): 1.81 × walk against 1.3, endurance falling faster.
- **The `OnTick`-only form does not.** `forcerun_tick` walked (2.02–2.05 tiles/s), though the sense frame, read in `OnTick` after the goal's own `setForceRun(true)`, saw `forceRun` true on all but the first frame of each leg (55 of 56, 48 of 49, 47 of 48): inside the next `OnPlayerUpdate` the flag read false on every frame (`updForceRun` 0). Something clears a force-run written from `OnTick` before the next frame's player update reads it. That is what the options' [synth read] predicted (`plan-22-options.md` § 2.1, "The clear runs first in the frame"): `CharacterInputComponent.updateToggleToRun` clearing `forceRun` from `frameStep` while the toggle is muted, before `updateInternal2`'s `OnPlayerUpdate`. The frames confirm the order (a clear between `OnTick` and the next `OnPlayerUpdate`); which call clears it stays the jar reading, its `frameStep` dispatch an inference the options name as unread. It refutes the jar research's "(or `OnTick`, one frame late)" in its door 2. The client's `options.ini` in the run dir reads `toggleToRun=false` (line 127; per-machine, untracked), the default the reading assumes.
- **The toggle question.** The A/B reading (force-run survives only with "toggle to run" on) is refuted for the `OnPlayerUpdate` write: the run held with the toggle off. The toggle-on arm did not run (skipped by rule), so whether a once-set or `OnTick` latch holds with the toggle on is unread.
- **`setRunning`/`setSprinting` from `OnTick` is a dead flag, as Stage C read it.** `setrun` walked (2.00–2.03 tiles/s, 0.98 × walk) with `running` and `sprinting` true on 47–48 frames of each leg, and `updRunning` true on 47: the flag set in `OnTick` is still true when the next `OnPlayerUpdate` reads it, and the gait is a walk (`jar-research-movement.md` line 63, the reset at `updateInternal2` L2549 after the handler). A frame's `running` is therefore no gait reading.
- **The sprint arm sprints.** `forcesprint` read 4.59–5.16 tiles/s (median 1.26 × `forcerun`), `sprinting` true on 20 of 22, 23 of 31 and 19 of 21 frames (62 of 74) and `running` on 1, 7 and 1, endurance falling 4 to 9 times faster than the force-run's. The jar research's "likely result" that L2566's clear and L2572 turn a pathed sprint into a run (`jar-research-movement.md` line 68) did not happen on these legs. Leg 1's first move came 776 ms after its ack, against 42–213 ms on the other 14 legs; its 7 `running` frames are seq 818–824, six of them before it moved.
- **Auto-walk steers.** All six legs went within 1.52° of the commanded world heading at world vector lengths 1, 1.95 and 2 (input lengths 1, 1.95 and 2 as sent; the input space maps an input length *L* along a diagonal to a world length √2 × *L*), and the calibration within 1.99°, with no correction needed. With the force-run re-asserted from `OnPlayerUpdate` it ran: 3.71–3.82 tiles/s, about the pathed force-run's pace, at length 1 as at length 2, so the vector's length did not set the gait here; without it (`walk`, `once`) it walked, 1.94–2.11. The first walk leg ran 5.85 tiles in 3 s from a start 0.65 tiles past M toward B (x 10987.3544921875) and left the strip past B; its heading (0.34°) is kept and its pace is out of every grade.
- **The once-set latch does not hold.** `once` set `setForceRun(true)` on the goal's second tick, with the auto-walk vector non-zero, and no frame of the leg read it, in `OnTick` (`forceRun` 0) or in `OnPlayerUpdate` (`updForceRun` 0 of 15); the leg walked (2.05). Under the default option the latch is cleared every frame whatever the input vector, so the jar research's door 3 ("`setForceRun(true)` set once … gives a steerable run that the engine itself holds", line 149) does not hold as written; the options' [synth read] said so ("The auto-walk door changes too"). Auto-walk runs only with the force-run re-asserted every frame.
- **One `OnPlayerUpdate` a tick.** The last frame reads `motor.upd` 12024 at `tick` 12024 (`state.log` seq 1683): on this client, with one local player, the handler ran once per `OnTick`.

## 2. X2 bench

Standing, before any walk. Each row is one `bench.global PZA.bench.<arm> <n>` on the client: `ms` the harness's integer-millisecond bracket around `n` calls, `usPerCall` = `ms` × 1000 / `n` (`readings.bench.rows[*]`, `steps[*].ack`), so a 500-call row resolves 2 µs. Bytes from `bench_info`; µs per KB = `usPerCall` / (bytes / 1024) (`readings.bench.summary.<arm>.us_per_kb`):

| arm | body | rep 0 | rep 1 | rep 2 | median µs | bytes | µs per KB | share of 1.67 ms |
|---|---|---|---|---|---|---|---|---|
| `json` | `PZA.json(PART)` | 1102 | 1250 | 1274 | **1250** | 2740 | 467.15328467153284 | 74.85 % |
| `jsonNoSort` | the encoder without `table.sort` | 928 | 926 | 1038 | 928 | 2740 | 346.814598540146 | 55.57 % |
| `compact` | a positional encoder, no sort | 146 | 148 | 166 | 148 | 1244 | 121.82636655948554 | 8.86 % |
| `concat` | `table.concat({S21}, "\n")`, the floor | 2 | 0 | 0 | 0 | 2740 | — | 0 |
| `openWrite` | open + write 2740 B + close | 138 | 168 | 136 | 138 | 2740 | 51.573722627737226 | 8.26 % |
| `openWrite20` | open + write 20 B + close | 108 | 118 | 120 | 118 | 20 | — | 7.07 % |
| `openOnly` | open + close | 62 | 60 | 76 | 62 | — | — | 3.71 % |
| `poll` | the real poll's `readKV` of `cmd.txt` | 54 | 54 | 54 | 54 | — | — | 3.23 % |
| `heldOpen` (n 1) | open a held writer | 0 | 0 | 0 | 0 | — | — | — |
| `heldWrite` | `write(S21)` on the held writer | 4 | 4 | 4 | 4 | 2740 | 1.494890510948905 | 0.24 % |
| `heldClose` (n 1) | close it | 0 | 0 | 0 | 0 | — | — | — |

The share column is the median over 1670 µs, pass 4's mean emit of a 2.1 KB part (`testing/artifacts/a_pipe_4-20261026-181848/GUIDE.md` line 60: "2102–2103 B, 160 parts, 1.67 ms"). Every row's `error` is null.

**Decomposition** (differences of medians):

- **The encoder holds the emit.** `json` costs 1250 µs for the 2740-byte part, 74.85 % of 1.67 ms; `concat` reads 0 (the noise floor, 0–2 µs). Scaled per byte to pass 4's 2102-byte part it would be 1250 × 2102 / 2740 = 958.94 µs, 57.42 %; the encoder walks keys and values rather than bytes, so the per-byte scaling is an assumption, and the bench part is 638 bytes larger than pass 4's typical part. No other arm comes near either way.
- **The sort** is `json` − `jsonNoSort` = 322 µs, a quarter of the encoder (25.76 %).
- **The positional encoder** costs 148 µs for 1244 bytes, about an eighth of `json` (1250 / 148 = 8.45), its output 45.40 % of the JSON's bytes.
- **The file.** Open + close 62 µs; open + 20 B write + close 118 µs; open + 2740 B write + close 138 µs. So a line's file cost is about 118 µs whatever its size (the 56 µs between `openOnly` and `openWrite20` being, by inference, the write and its flush at close), plus about 7 µs per KB (20 µs for 2720 more bytes). The held writer's `write` costs 4 µs for 2740 bytes, but its bytes land only at close or when its buffer fills (§ 2.3 of the options); this run reads no delivery latency.
- **The poll** costs 54 µs on every rep.
- **What the arms do not sum to.** `json` + `openWrite` at 2740 bytes is 1388 µs, under pass 4's 1.67 ms for 2.1 KB parts; the live emit runs once a tick on a frame-building tick inside a different session, the bench 500 times in a warm loop, and the remainder is not attributed.

**The pass line** (`plan-22-options.md` § 4, X2: "Names the arm holding ≥ 60 % of the 1.67 ms"): the encoder, at 74.85 % at the bench's size (57.42 % on a per-byte scaling to 2.1 KB); open and close are under 9 % together with the write. By the line's own mapping this is "Encoder ≥ 60 %: compact encoding".

**For K1's Link.** Compact positional encoding is the fix (8.45 × cheaper than `PZA.json` here, sort included); dropping the sort alone saves a quarter. One flush a tick (merging the scan part's, the ack tick's and the frame's) saves about 118 µs per merged line and costs no latency, worth taking but second-order. A held writer saves the open and close (about 118 µs a line) and buys latency the run does not read. **For the sidecar trigger:** every arm here is a Lua-side cost the Lua can cut; nothing names a cost only a JVM transport would reach.

## 3. X3 load

**The load** (`readings.load`). Before: `weight` 1.5550000667572021, `maxWeight` 12, `HEAVY_LOAD` 0, health 100 (`before`, seq 1294). Six RCON `additem "admin" "Base.Plank" 1` (`adds[*]`, `planks_added` 6; the second reply blank, the rest "Item Base.Plank Added in admin's inventory."), each awaited by a frame whose weight rose by 3.0 (`PLANK_W`; `Base.Plank` `Weight = 3.0`, the 42.21 install's `media/scripts/generated/items/weapon.txt` L8859, read by the controller):

| add | frame weight | ratio (weight / 12) | `HEAVY_LOAD` | frame seq |
|---|---|---|---|---|
| 1 | 4.555000305175781 | 0.37958335876464844 | 0 | 1303 |
| 2 | 7.555000305175781 | 0.6295833587646484 | 0 | 1306 |
| 3 | 10.555000305175781 | 0.8795833587646484 | 0 | 1308 |
| 4 | 13.555000305175781 | 1.1295833587646484 | 1 | 1310 |
| 5 | 16.55500030517578 | 1.3795833587646484 | 2 | 1312 |
| 6 | 19.55500030517578 | **1.6295833587646484** | **3** | 1314 |

Level 3 came at the sixth add, `level3_at_ratio` 1.6295833587646484 (`level3_at_add` 6; `load_stalled_at` null): every transition sits where #3926's thresholds put it (level 1 above 1.0, 2 from 1.25, 3 from 1.5), and 3.0-kg steps on a 12-kg maximum resolve each threshold only to a 0.25 band (level 3's edge lies in 1.3796–1.6296). After `drop Base.Plank 1` (`readings.load.drop`: `k` 1 by the level-2 band rule, `goal.detail` `moved=1`) the frame read 16.55500030517578 and level 2 (`drop.after`, seq 1571). `maxWeight` reads 8 on the first frame (seq 3) and 12 from seq 4 on.

**The health trace** (`readings.load.trace`, 345 frames; `drops` the 34 consecutive-frame falls over `DROP_EPS` 0.05, each with the level and `moving` of the frame before it):

| window (seq range, `windows`) | what ran | drops | quanta | health at its start → end | game minutes (`worldAge`) | net fall per game minute |
|---|---|---|---|---|---|---|
| `walk_loaded` [1314, 1490] | five `goto` legs A↔B at level 3 | 27 (24 with `moving` true) | 41 | 100 (seq 1314) → 84.65166473388672 (seq 1490) | 8.259944915771484 | 1.858164360976218 |
| `still` [1490, 1566] | 15 s standing at level 3 | 6 (all `moving` false) | 7 | 84.65166473388672 → 82.30940246582031 (seq 1566) | 3.990955352783203 | 0.586892626206145 |
| `drop` [1566, 1571] | the drop goal, standing | 1 (seq 1568, level 3) | 1 | → 81.92774963378906 (seq 1568, the session's minimum) | — | — |
| `walk_level2` [1571, 1663] | three `goto` legs at level 2 | **0** | 0 | 81.94200897216797 (seq 1571) → 82.42669677734375 (seq 1663) | 4.580211639404297 | −0.1058221417119537 (a rise) |

Over the whole level-3 span, seq 1314 to 1569, health fell 18.072250366210938 in 12.358016967773438 game minutes (`worldAge` 2.9168128967285156 → 3.1227798461914062 h), a net 1.4623908037461646 a game minute, in 46.399 s of the client's clock (3.75 s a game minute on the 90-minute day). Each window's game minutes and fall are differences of `state.log` frames at the named seqs.

- **The quantum.** Every drop is a whole multiple of about 0.381: 22 single falls of 0.3808746337890625–0.3909912109375 (the 0.391 the first, from 100 before any regeneration), 9 double falls of 0.7756576538085938–0.7781982421875 and 3 triple falls of 1.1724090576171875–1.1734619140625 (`drops[*].fall`), 49 quanta in all. Between drops health rose in steps of 0.014251708984375–0.01425933837890625 (60 rises over the level-3 span). The 12 falls over 0.5 are the 12 `hit` events (`PZAgent_Sense.lua` line 200's rule, a fall over 0.5 between event ticks), not hits.
- **Level and posture.** Every drop came at level 3 (`verdicts.x3_drops_at_level3_only.observed`: `below_level3` 0, `unread_level` 0, `levels` `["3"]`); none in the 86 level-2 frames (`verdicts.x3_level2_no_drop.observed.level2_frames`). Ten of the 34 came with the frame before reading `moving` false: three between the loaded legs, the six of the still window and the drop window's one. **The drain runs standing still**, at about a third of the walking rate in this run (0.587 against 1.858 a game minute net; 7 quanta in 15.0 s against 41 in 31.0 s of client clock); the windows ran once each, in that order, so the run does not separate standing from the time since the load.
- **The body.** From seq 1316 every frame lists all 17 body parts below 100 (`body.nParts` 17), the first drop spread over all of them (seq 1316: parts at 99.76889038085938–99.96746826171875); `bleeding`, `scratched`, `bitten` 0 and `injured` false throughout, and the `PAIN` and `INJURED` moodles 0 on every frame, while the server's `stats.all` read `Pain` 3.1785154342651367 at the end (`readings.server[0].ack.stats.Pain`).
- **Endurance and pace under the load.** The loaded walk legs read 1.677–1.728 tiles/s (median 1.6834353005186145, `walk_loaded[*].pace`) with endurance falling 0.00164–0.00195 a second, the level-2 legs 1.799–1.873 (median 1.839453125, `walk_level2[*].pace`) with endurance slope 0.0, against 2.05 and 0.0 unloaded: walking drains endurance at level 3 and not at level 2, as #2256 reads the jar ("only above heavy-load level 2").

**Who hears it** (`readings.load.server_arm`/`server_read`, `client_arm`/`client_read`, `damage_events`). The server's `fall.probe admin` listener, armed at 216.126 s with `counts` `{}`, read `counts` `{"HEAVYLOAD": 49}` at 282.704 s, and no other tag: 49 events, the same number as the frames' quanta. The client's `event.watch OnPlayerGetDamage`, armed in the same second, read `count` 0, and PZAgent's own client `OnPlayerGetDamage` hook emitted 0 `damage` events (`damage_events` `[]`, `damage_events_n` 0); both hooks read `hooked` true. **The server hears every HEAVYLOAD event and the client hears none**, which is #2597's consequence (`BodyDamage.Update` returns at once on the client for the local player, so the whole body-damage tick is the server's); the client sees the drain only as its health falling.

**Verdicts** (`verdicts.*`): `x3_drops_at_level3_only` as_predicted (34 drops); `x3_floor_75` **unmeasured** (`min_health` 81.92774963378906, `frames_at_or_below_floor` 0); `x3_drops_while_still` recorded (6 drops, `fall` 2.6843948364257812); `x3_level2_no_drop` as_predicted; `x3_server_hears_heavyload` as_predicted; `x3_client_hears_heavyload` as_predicted (0); `x3_level3_at_ratio` as_predicted.

**The reading in words, against the pass line** ("Drops only at level ≥ 3 while health > 75, none at ≤ 2 or seated, and the fall stops at the first frame ≤ 75"; the probe ruling reads "seated" as standing still):

- **Drops only at level ≥ 3: held.** All 34 at level 3; none in 4.58 game minutes of walking at level 2, where health rose instead.
- **None standing still: did not hold.** Standing at level 3 drained at about a third of the walking rate; the jar's exemptions (#2356, its conditions as #3907 lists them: a vehicle, sleep, a seat and the seated-resting class) do not include standing, so a sit was not read and remains the case the line named.
- **The 75 floor: unmeasured.** Health never came within 6.9 of 75. At this run's rates the floor lies about 3.7 game minutes of loaded walking past the session's minimum ((81.92774963378906 − 75) / 1.858164360976218 = 3.73), about 11.8 standing (/ 0.586892626206145 = 11.80), or about 13.5 game minutes of loaded walking from 100 (25 / 1.858164360976218 = 13.45); a projection, not a reading.
- **Which side hears HEAVYLOAD: the server only**, as above.
- **Against the Stage C falls.** `testing/artifacts/c_survive_2-20261026-195516/GUIDE.md` line 175 read two looting falls that began at the 37th inventory item, fell in whole multiples of about 0.39 (single falls 0.381–0.382), standing or walking, with no zombie near, and stopped at 74.56 and 74.55, with no weight or level on the frames. This run's drain falls in the same quantum, 0.3808746337890625–0.3909912109375 a single fall, standing or walking, at level 3 only, server-side only. That matches the Stage C falls in every field their frames carried, which reads them as the heavy-load drain: an inference, since those frames carried no weight, level or body part and the onset at item 37 is where the carried weight would have crossed 1.5 × the maximum, which they cannot show. Their stop just under 75 (76.13 → 74.56 on the last frame's 1.566 fall) fits the jar's floor of the term (#2356's "health > 75" condition), which this run did not reach. This run read level 3 only; Stage C's falls were mostly double quanta (22 of 31 at 0.776–0.789), which a higher level (the term scales as 1 / (5 − level), #2356) or a faster event rate would give; their level is not read.

## 4. What the frames cannot say, the host, corrections

**What the frames cannot say.**

- **The run flags' call sites.** The frames read `isForceRun` in `OnTick` and inside `OnPlayerUpdate`, and the pace; they do not read `UpdateInputState`, `frameStep` or the animator, so every engine call named in § 1 is the jar reading the frames are consistent with, not a reading.
- **Timing finer than a frame.** `cmd_move_ms` is the ack's phase before the next frame plus whole frame periods (6 ticks, about 100 ms at rate 10); the 42–776 ms here say only that each leg moved within one to eight frames of its ack.
- **Pace at a leg's ends.** The 1.5 s legs carry the start and stop ramps in about 15 moving frames; the pathed legs' 21–56 frames dilute them. The autowalk walk legs' 1.94 and 2.11 bracket the pathed walk's 2.05.
- **The toggle on.** Not run.
- **Why standing drains slower.** Not read: one walking window then one standing window, n = 1.
- **The drain's event rate.** 49 events in 12.358 game minutes (about 1.06 a second of client clock); the jar's one-in-ten roll a tick (#3924) is not tested against it, since the server's tick rate is not read.
- **The floor**, unmeasured.
- **The bench's live share.** The bench runs each arm 500 times in a warm loop on a standing character; the live emit runs once a tick among the frame's other work, so the shares are of the 1.67 ms by arm, not a decomposition of a live tick.

**The host.** One Windows host; free memory 15.62 GB at the gate, 2.88 GB at ready with the server and the `-debug` client up, 16.63 GB after teardown; the `bench.log` of 8250000 bytes is the bench arms' own appends. The bench and the pace readings are this host's.

**Corrections to the controller's ledger** (`.superpowers/sdd/2026-10-27-plan-22-agent-base-design/progress.md`, the probe-session line):

1. "34 drops all at level 3 (quanta ~0.38/0.78/1.17)": the 34 are frame-to-frame falls carrying 49 quanta (22 single, 9 double, 3 triple), and the server's listener counted 49 HEAVYLOAD events, so the server's count and the frames agree at 49, not 34.
2. The same line does not say that the drain ran standing: 6 of the 34 drops (7 quanta) came in the still window and one in the drop window, at about a third of the walking rate, so the pass line's "none … seated", as the ruling reads it, did not hold.
3. "health min 81.9 so the 75 floor is unmeasured" holds; the task brief's "not reached in the 30 s walk (health min about 81.9)" places the minimum in the walk: the walk ended at 84.65166473388672 (seq 1490), and the minimum 81.92774963378906 came at seq 1568, in the drop window after the 15 s stand.
4. "X2 json 1250 us … (the encoder holds the emit, not the open)" holds at the bench's 2740 bytes (74.85 %); scaled per byte to pass 4's 2.1 KB part it is 57.42 %, under the 60 % line, and the encoder is still the largest arm by far.
5. "1523 frames" is the driver's `frames_n`; `state.log` holds 1531 frames, the last 8 after the driver's last read.

## Do not cite from this file

| Key | Value in the file | Why not |
|---|---|---|
| everything measured here, as a population | — | `n = 1` boot, one fixture, one character, one line on open ground. |
| every wall-clock leaf, by one wildcard sentence: `*PyMs`, `*wallMs`, `wallMs`, `wall`, `wall_*`, `*_wall`, `wall_ms`, `epoch_ms_*`, `took`, `phase_walls.*`, `timeline`, `wall_seconds`, `server_launch_wall`, `server_started_wall`, `session_ready_wall`, `hello_wait_ms`, `client_seen[*].*`, `memory[*].wall`, `memory_wait[*].wall`, `steps[*].*wall*`, `first_move.wallMs`, `first_move.readPyMs`, in `p22_probe.json` and every line of `state.log` (wildcard) | host epoch ms and seconds | This host's timing, cited only as a difference within this run (a pace, a window's span), never as a reading. |
| `readings.motor.*.cmd_move_ms` as a latency finer than a frame | 42–776 | Frame-quantised at about 100 ms; cite as "within one to eight frame periods of the ack". |
| `readings.motor.legs[*].flags.running`, `flags.sprinting`, `flags.updRunning` as gait | 47–48 of 48–49 on `setrun` | The flag set from `OnTick` is still true when read and the gait is a walk; read the pace. |
| `readings.motor.autowalk[0].pace` and the leg as a graded run or walk | 1.942729086686262 | Voided: the leg left the checked strip; its heading is kept. |
| `voided_legs` (top level) | 0 | The inherited pass-2 counter (health and zombies on `goto` legs), not the strip voids; read `readings.motor.autowalk[*].voided`. |
| `readings.bench.rows[*]` of `heldOpen`, `heldClose` and `concat`, and `readings.bench.summary.concat.median_usPerCall` | 0–2 | Integer milliseconds over 1 or 500 calls: under the bracket's resolution; a bound, never a cost. |
| `readings.bench.summary.heldWrite.median_usPerCall` as a write cost | 4 | The bytes stay in the writer's buffer; no delivery is read. |
| `readings.bench.summary.json.us_per_kb` scaled to another part size | 467.15328467153284 | The encoder's cost follows the part's keys and values, not its bytes; one part was benched. |
| `readings.load.drops` as an event count | 34 | Frame falls merge quanta; the events are 49. |
| `readings.load.drops[*].moving` of a drop on a leg's first frame | `false` on seq 1316 | The rule reads the frame before; seq 1316's own frame reads `moving` true. |
| `events.hit` as hits | 12 | A fall over 0.5 between event ticks, here the multi-quantum heavy-load falls. |
| `verdicts.x3_floor_75` | unmeasured | Health never fell below 81.92774963378906. |
| the walking-against-standing drain rate as a cause | 1.858 / 0.587 a game minute | One window each, in order; standing and the time since the load are not separated. |
| the Stage C looting fall's cause read from this run | — | An inference: the quantum, posture and server-only hearing match, but those frames carry no weight or level. |
| `readings.server[*].rttMs`, `readings.server[*].ack.mult` | 1509.53759765625 / 4.795048236846924 | `n = 1`; getMultiplier, not the true multiplier (#3762). |
| `constants`, `preboot`, `profile`, `fixture`, `argv`, `memory`, `memory_wait`, `world_changes`, `predictions`, `readings.load.adds[*].rcon` | the driver's tables, checks and the harness's writes | Written before or around the run, or the harness's RCON writes; not readings. |
