# `p_stance-20261029-135919` reading guide

**`p_stance-20261029-135919/p_stance.json`** (with `state.log`, `decision.log`, `shots/shots.jsonl` and the write-up's `p_grade_2.txt`) — produced by `testing/agent/drivers/p_stance.py` at `driver_commit` `f7201f76` (Plan 24 Task 16 and its fix round 1, ruling P24-T: a scripted probe, no planner; `grade_p1` in the same file), unedited since (its last commit at HEAD is `f7201f76`), on the driver library `testing/agent/driverlib/` at `preboot.driverlib_commit` `68c18eee` (`shots.py` at `425fc6dc`: the guarded shot taker, Task 15 fix 1; `session.py` at `a7fb6ff9`), which imports `testing/experiments/xlib.py` (`preboot.xlib_commit` `45c49217`) and the agent base under `testing/agent/base/` at `preboot.agent_commit` `0f7881a1` (`pza1.py` at `c211e196`); on HEAD `0f7881a1` at the boot (`preboot.commit`; `preboot.harness_lua_commit` `edcaf2e6`, `preboot.harness_lua_dirty` false; `preboot.harness_py_commit` `3c5a6e3b`; `preboot.driver_checks`: `agent_lua_dirty`, `agent_base_dirty`, `driverlib_dirty` and `driver_dirty` false). The agent mod `testing/PZAgent/PZAgent` loaded by path from the tree, its last commit `a945ae4d`: PZAgent 1.5.6 (`readings.hello.hello.mod` `1.5.6`, `proto` `PZA/1`, seventeen `caps`), whose stance is held from `OnPlayerUpdate` every frame (`d631b084`, Task 9 fix 6) with fix rounds 7 and 8 (`c211e196`, `a945ae4d`) over it. Fixture `agent` (`fixture.provision_run` `prov-20261026-092028`, `fixture.build` `42.21.0`, Zombies 5); profile `testing/profiles/agent.toml` (`preboot.profile` `agent`; PZTestKit + PZAgent, user `admin` on a `-debug` client, the 90-minute day); `argv` `--session 1 --fixture agent`. Graded by `grade_p1` inside the artifact; regraded by `testing/agent/drivers/p_grade_2.py` (the write-up's, § 2) into `p_grade_2.txt`.

**Plan 24's stance probe** (ruling P24-T: the stance proven live before the seventh chain boots on it). A fixed script of eight steps went through the session loop at `PLANNER_HZ` 10: 5 s idle, a standing leg (`aim {bearing 0, vx 0, vy 0, seconds 5}`, a2), a backpedal leg (`aim {bearing 0, vx -1, vy 0, seconds 5}`, a3: face east, move west), the three target steps (skipped: no zombie within the bat's reach), a walk 3 tiles east (`walkTo`, a4) and 1.5 s idle. **The stance held live: `forceAim` read true on every frame of both legs and `aiming` on every frame from each leg's ack to its end, 50 of 50 on each, where the sixth chain's 11 aim legs had read `aiming` on none of 185** (#4323). **The backpedal moved, then stood against a wall**: the character went 1.01171875 tiles west in its first 1.195 s, facing east, and stood 3.801 s at the living room's west wall with `moving` true; `grade_p1`'s 0.09375 tiles is its window's defect (§ 2). The walk then released the stance.

## 0. The run

- **Wall.** 122.8 s (`wall_seconds`, counted from the memory gate). Phases (`phase_walls`, seconds from the gate): `hello` 84.794–84.807, `damage_hook` 84.809–86.57, `kit` 86.572–93.666, `loop` 93.667–112.518. The loop's eight steps ran in 18.187174558639526 s of loop wall time (`stop.wallS`) and stopped `script_done`. The record's `timeline` reads its server start at 282.7 s, past the run's 122.8 s, so it counts from another origin and nothing here rests on it.
- **Hello.** `readings.hello`: `ok` true, `proto` `PZA/1`, `mode` `append`, `build` `42.21`; the hello line (`state.log` seq 1): `mod` `1.5.6`, `user` `admin`, `rate` 10, the seventeen `caps` of PZA/1.5.2 (`aim` to `wash`); `first_frame.seq` 10.
- **The kit.** The bat's `item_added` at seq 236 (`use` `weapon`), the `equip` a1 accepted at seq 274 and `done` at seq 288 (`readings.kit.weapon_frame.seq` 289); the weapon group read `Base.BaseballBat`, `reach` 1.125, `cond` 15 on the 192 frames from it and null on the 106 before.
- **Pipe health.** `frames.gaps` 0, `frames.bad` 0, `frames.lua_errors` 0, `frames.parks` 0, `logs.clients.admin` `[]`, `admin_lua_error` false, `server_error_count` 0, `bus_dead` null; `missing` `[]`. The shot taker: `loop.shots` `n` 6, `skipped` 0, `failures` 0.
- **Frames.** `state.log` holds 523 lines and line *n* is seq *n* (decoded with `testing/agent/base/pza1.py` through `FileTransport` from a `git archive 0f7881a1` copy; 0 bad, 0 gaps): 1 `hello`, 298 `frame` (seq 10–523, every consecutive pair six ticks apart), 195 `map` (all `delta`), 20 `act` (5 `accepted`, 10 `progress`, 5 `done`) and 9 `event` (the first sight's eight `item_added` and the bat's). The driver read 290 frames (`frames.n`; `probe.frames` holds them compact, seq 10–513). The health read 100 on every frame; `attackers` read 0 and `hitReaction` empty on all 298.
- **The zombie.** One zombie, 5965, was listed on the frames throughout, 7 tiles off at the legs' start and 4.943792365624464 at the stop's act line (seq 512): never within the bat's 1.125.
- **Memory.** Free 12.23 GB at the preboot read (against `MIN_FREE_GB` 12.0), 1.11 GB at ready, 15.04 GB after teardown (`memory`).

Files, as committed in `cd7e2b15` (the controller's copy of the run folder's files, each byte-identical to it) and, for `p_grade_2.txt`, this write-up:

| File | Source | Bytes | sha256 |
|---|---|---|---|
| `p_stance.json` | the run's `p_stance.json`; CRLF endings, no final newline | 455029 | `a584e1f7a7e91998fa5543138cdfbb67257af8d0a15c3c474cefe3aad2c7e0f7` |
| `state.log` | the run's `clients/admin/Lua/pzagent/admin/state.log`; CRLF endings, 523 lines | 132050 | `9a5662ce3e66446e258b24db05be2119d40d0e7be76bcd4f9d0ba315bb6cb26d` |
| `decision.log` | the run's `decision.log`, one line a script step; CRLF endings, 8 lines | 1556 | `d322140f51bcef110d05ca42b8ebe1260b6632c2abd4fe143b2ebd0f83fbe742` |
| `shots/shots.jsonl` | the run's `shots/shots.jsonl`; CRLF endings, 6 lines | 2682 | `c7eea7d2c3d3f169c6f5435fd5e1ce97a60339c916e09386cd498aa6628b4d99` |
| `p_grade_2.txt` | `python testing/agent/drivers/p_grade_2.py` on this folder's `p_stance.json`, stdout (§ 2); CRLF endings, 94 lines | 2086 | `7feadb2fd0740f77fbcacf846979aa872e1ed822a31bdb8f6399580b611318ae` |
| `shots/shot-NNNN-<seq>.jpg` | the images this guide cites (n 3 and 4), copied byte-identical from the run folder's `shots/` at the mint; each one's bytes and sha256 are its index line's | — | — |

The hashes are of the working-tree bytes. The other four shots, the driver's stdout, the client console and `server-stdout.log` are per-machine and untracked, and nothing below rests on them.

## How to read it

A frame is `state.log`'s positional line in the schema's `frame` order (`testing/agent/base/pza1.py`), its delta groups merged from the frame before. `me.aiming` is `isAiming()` and `me.forceAim` is `isForceAim()`, read after the frame's update (`PZAgent_Sense.lua` at `a945ae4d`; code). A leg's frames are counted three ways, each named where used: **(a)** the `state.log` frames between the leg's `accepted` act line and its `done` act line (51 a leg: seq 342–396 and 399–466); **(b)** the `probe.frames` whose `wallMs` lies from the step's `ackedMs` (the driver's clock at the ack) to its `endMs` (50 a leg: seq 343–396 and 400–466; `p_grade_2.txt`); **(c)** `grade_p1`'s window, from `ackedMs` + `LEG_SETTLE_MS` 1000 to `endMs` (40 a leg). A **span** is a difference of two frames' `wallMs` on this host's one clock.

**The stance on PZA/1.5.6** (`PZAgent_Stance.lua` and `PZAgent_Motor.lua` at `a945ae4d`; code, not readings). An `aim` leg clears the vanilla queue, writes the run latches false, calls `setForceAim(true)`, faces its bearing every tick and, with a non-zero vector, drives the auto-walk along it; while the stance is held the Motor's `OnPlayerUpdate` handler re-asserts `setForceAim(true)` every frame, since the force-aim set once lives one frame on 42.21 (#4333). The leg ends `done` at its seconds with `{d (tiles from its start), held (isForceAim at the end), targetDead, heldFrames (the ticks after the first whose isAiming read true), ticks}` and releases the stance through `nullifyAiming()`; any other skill started releases it too. The jar reads have an aiming character strafe with its facing held (#4332) at a move rate multiplied by 0.7 while aiming (#4295).

## 1. The stance held

| leg | act | frames (a): `aiming`, `forceAim` | frames (b): `aiming`, `forceAim` | `grade_p1` (c) | result |
|---|---|---|---|---|---|
| `aim_stand` | a2, accepted seq 341, `done` seq 397 | 51: 50, 51 | 50: 50, 50 | `n` 40, `held_frac` 1.0, `force_frac` 1.0 | `held` true, `heldFrames` 301, `ticks` 301, `d` 0 |
| `aim_strafe` | a3, accepted seq 398, `done` seq 467 | 51: 50, 51 | 50: 50, 50 | `n` 40, `held_frac` 1.0, `force_frac` 1.0 | `held` true, `heldFrames` 301, `ticks` 301, `d` 1.01171875 |

**`forceAim` read true on all 51 frames of each leg, and `aiming` on all but the leg's first frame (seq 342 and seq 399, each the frame of the accepted line's own tick, before the driver's ack), so on all 50 from the ack to the end**; each result read `held` true with `heldFrames` equal to `ticks`, 301 of 301. The 52 idle frames before (seq 289–340) read both false, as did all 38 frames from the walk's accept to the log's end (§ 3). Every frame of both legs read `me.dir` `E`, the bearing 0 the script sent, and `running` and `sprinting` false. Against the sixth chain's first session, where all 185 frames of 11 aim legs read `aiming` false and every `done` leg `held` false (#4323): the same skill, after Task 9 fix 6's per-frame re-assertion, held the stance on every frame a leg was running. The standing leg did not move (x 10721.5, y 10630.5 on all 51 frames, `moving` false).

Shot 3 (index seq 396, line 3, the last frame of the standing leg) shows the character in the living room with the bat raised high in both hands, `x: 10721 , y: 10630`.

## 2. The backpedal, and the grade's window

**What the frames read** (`p_grade_2.txt`, from `probe.frames`; the `state.log` frames agree). From seq 399 (x 10721.5, the frame before the ack) the position fell along x in 12 frame steps to **10720.48828125 at seq 415: 1.01171875 tiles in 1.195 s, 0.8466265690376569 tiles a second**, the modal step 0.09375 tiles a frame (9 of the 12), `pace` 0.07120768229166667 on the first moving frame, 0.6640625 on the second and 0.9191176470588236 to 0.9568339646464646 on the other ten. **Then it stood 3.801 s, 38 frames (seq 417–466), at (10720.48828125, 10630.5), every one reading `moving` true and `pace` 0.** y held 10630.5, and `me.dir` read `E` on every frame: the character moved west facing east. The leg's own result `d` reads 1.01171875, the same distance. The `steps` list in `p_grade_2.txt` is rounded to 9 places (0.006835938 for the frames' 0.0068359375, 0.094726562 for 0.0947265625) and no row cites it; the figures above are the unrounded ones.

**Why it stopped.** The kept map (`World.apply`, `testing/agent/base/world.py` from the `0f7881a1` archive) reads the square it stopped on, (10720, 10630), as building 2's living room with its west edge blocked (`blockW` true) and a closed, locked window (`window.open` false, `locked` true): the room's west wall, 0.48828125 tiles behind the character. Shot 4 (index seq 466, line 7, the leg's last frame) shows the character with the bat raised high beside the room's window wall, `x: 10720 , y: 10630`. So the leg ran out its 5 s against the wall; how fast a backpedal in the open keeps going over a whole leg the probe does not read.

**Against the walk.** The walk a4 after it, at a walk with the stance released, stepped 0.216796875 tiles a frame on 7 of its 12 steps (seq 469–483), against the backpedal's 0.09375: by inference the aiming walk's slower rate (#4295 reads a 0.7 multiplier on the move rate while aiming, which alone does not give the ratio; the strafe animation's rate is not read).

**The grade's defect.** `grade_p1` reads a leg from `LEG_SETTLE_MS` 1000 after the ack (`p_stance.leg_frames`), so its backpedal window opened at seq 414, after 11 of the 12 movement steps, and read 0.09375 tiles (the last step, seq 414 to 415) and `strafe_ok` false against `STRAFE_MIN_TILES` 1.0. `p_grade_2.py` (`testing/agent/drivers/p_grade_2.py`, written after the run and before its output was staged, never an edit of `grade_p1`) reads the same record with no settle and reproduces the grade's window as a check: its `grade_window` reads 40 frames from seq 414 and 0.09375 tiles, equal to `grade_p1.strafe_tiles`, and its `opens_after_run` true. Its offline tests (`testing/tests/pzagent/test_p_grade_2.py`) fail a leg that never moves, a leg that moves to its end and a grade window that does not reproduce the committed value.

## 3. The release, the skipped legs, the walk

- **The target legs** (`aim_target`, `attack`, `post_attack`) were skipped when a3 ended (`decision.log` lines 4–6), each row reading `skipped` true: zombie 5965 stood 5.666618664856098 tiles off (the a3 `done` snapshot), beyond the bat's `reach` 1.125. So the hand-over (a swing from the stance) is unread here: `grade_p1.handover_ok` null.
- **The release.** The walk a4 (`walkTo` to (10723.48828125, 10630.5), `gait` `walk`) was accepted at seq 468 and `done` at seq 485 with `d` 0.9892582945149369 (its distance to the target at the end); `aiming` and `forceAim` read false on all 38 frames from seq 469 to the log's end, seq 523 (`grade_p1.release_ok` true). The character moved on to (10722.8447265625, 10630.5009765625) by seq 490 with `moving` false, and the loop's `stop` a5 came at seq 511–512.
- **`mod_ok` false** is the grade's stale pin: `p_stance.MOD_VERSION` is `1.5.4` and the hello read `1.5.6` (fix rounds 7 and 8 bumped the version after the driver was written); the verdict's `mod != 1.5.4` qualifier says the same. Nothing about the stance rests on it.

## 4. The shots

The shot taker (`testing/agent/driverlib/shots.py` at `425fc6dc`, the guard's code) took 6 shots and skipped none (`loop.shots`); every index line reads `window.found` true and the same rectangle; one shot per script step's start (`goal`) and the cadence and stop shots. The cited shots (the index's `seq` and `decision_line`):

- Shot 3 (seq 396, line 3, the standing leg's last frame): the character in the living room, the bat raised high in both hands, `x: 10721 , y: 10630`.
- Shot 4 (seq 466, line 7, the backpedal leg's last frame): the character, the bat raised, beside the room's window wall, `x: 10720 , y: 10630`.

A shot's `seq` is the latest frame the loop had read at the mark; the grab followed 52.1767578125 to 134.2705078125 ms after that frame (`pyMs` less its `wallMs`).

## 5. What the probe cannot say, the host, the clocks

- **The hand-over** from the stance to a swing: the target legs were skipped.
- **A backpedal over a full leg in the open**: the leg met the wall after 1.195 s.
- **The strafe animation**: the frames read the position, the facing and `pace`, not the animation; the shots show the bat raised.
- **`moving` against the wall**: it read true on 38 frames with the position unchanged; what the flag answers there (the input, the auto-walk) is not read.

**The host.** One Windows host; free memory 12.23 GB at the gate, 1.11 GB at ready, 15.04 GB after teardown.

**The epoch-ms leaves** (wildcard): `*wallMs`, `*Ms`, `*pyMs`, `*_ms`, `*.wall`, `*_wall`, `wall_*`, `epoch_ms_*` and the loop's `*S` keys anywhere in `p_stance.json` (`probe.steps[*].startMs`, `probe.steps[*].endMs`, `probe.steps[*].ackedMs`, `probe.frames[*].wallMs`, `loop.startPyMs`, `loop.wallS`, `stop.wallS`, `loop.stopped.wallS`, `readings.hello.hello.wallMs`, `server_launch_wall`, `server_started_wall`, `session_ready_wall`, `teardown_started_wall`, `wall_seconds` and the like), the `wallMs` of every line of `state.log`, every `decision.log` `wall`, the `wallMs`, `pyMs` and `grab_ms` of every line of `shots/shots.jsonl`, and `timeline`, `phase_walls`, `client_seen` and `memory[*].wall` are this host's clocks, cited only as a difference within this run (a span, a duration, a speed), never as a reading; `p_grade_2.txt`'s `span_s`, `leg_s` and `tiles_per_s` are such differences.

## Do not cite from this file

The first five rows are the run's rows in `docs/reference/do-not-cite.csv` (committed with the artifact); the rows after them are this guide's.

| Key | Value in the file | Why not |
|---|---|---|
| `grade_p1.strafe_tiles`, `grade_p1.strafe_tiles_per_s` and `grade_p1.strafe_ok` as the backpedal leg's movement | 0.09375, 0.02403846153846154, false | The grade's window opened 1 s after the ack, after 11 of the 12 movement steps (§ 2); `p_grade_2.txt` reads the leg. |
| `grade_p1.mod_ok` and the verdict's `mod != 1.5.4` qualifier | false | The grade pins 1.5.4; the hello read 1.5.6 (§ 3). |
| `loop.cost.*` and the frames' cost group as a per-tick cost | per tick | The 1 ms clock; cite the X4 sessions for the base's cost. |
| every free-text reason, detail and note string (`stop.detail`, `notes[*].note`, `decision.log` `inputs.note`) | — | The driver's or the Lua's message, not a reading. |
| `constants`, `preboot`, `profile`, `fixture`, `argv`, `memory`, `memory_wait`, `world_changes`, `steps`, `verify`, `chain`, `timeline` | the driver tables | Written before or around the run, or the bus's raw steps; not readings. |
| `grade_p1.legs.aim_stand.n` and `grade_p1.legs.aim_strafe.n` as the legs' frames | 40 | The grade's window (c), from the ack plus 1 s; from the ack 50 a leg, from the accepted line 51 (§ 1). |
| `grade_p1.strafe.moving_frac` as the backpedal moving | 1.0 | `moving` read true on the 38 frames the character stood against the wall (§ 2). |
| `shots/shots.jsonl` `seq` and the index's `gameMin`, `health`, `branch` and `goal` as the frame a shot shows | per shot | The latest frame the loop had read at the mark; the grab follows on the worker (§ 4). |

## Corrections

**To the record written before this guide** (the stub, the artifacts row and the commit subject `cd7e2b15`; each checked against this folder's files):

1. They read the backpedal as "about one tile west in 4.9 s … the backpedal moves, slowly": the 1.01171875 tiles came in the leg's first 1.195 s (0.8466265690376569 tiles a second, 0.09375 a frame), and the character then stood 3.801 s against the living room's west wall with `moving` true (§ 2). It was stopped, not slow.
2. They read `pace` 0.07 to 0.96 on the backpedal: that is the 12 moving frames; `pace` read 0 on the other 38 (§ 2).
3. They read `aiming` and `forceAim` true "on all 50 of their frames (`held_frac` 1.0 …)": `held_frac` is over `grade_p1`'s 40 frames (c); over the 50 from the ack (b) both read true on all, and over the 51 from the accepted line (a) `forceAim` on all and `aiming` on all but the first (§ 1).
4. They name the grade's window as the defect without saying how: it opened at seq 414, 1 s after the ack, after 11 of the 12 movement steps (§ 2).
5. The artifacts row names the library at `425fc6dc`: that is `shots.py`'s commit; `preboot.driverlib_commit` reads `68c18eee`, the library's tree at the boot (the header).
