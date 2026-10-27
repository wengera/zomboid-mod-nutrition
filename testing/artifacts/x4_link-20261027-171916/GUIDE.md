# `x4_link-20261027-171916` reading guide

**`x4_link-20261027-171916/x4_link.json`** (with `state.log` and `x4_grade.txt`) — produced by `testing/agent/drivers/x4_link.py` at `driver_commit` `92f4c0d0` (Plan 22 Task 11 fix 1), unedited since (its last commit at HEAD is `92f4c0d0`), which imports `testing/agent/drivers/_dlib.py` and `testing/experiments/xlib.py` (`preboot.xlib_commit` `45c49217`); on HEAD `95596a91` at the boot (`preboot.commit`; `preboot.harness_lua_commit` `e4d5b71b`, `preboot.harness_lua_dirty` false; `preboot.harness_py_commit` `52a7de93`); the agent mod `testing/PZAgent/PZAgent` loaded by path from the tree (`profile.sources.PZAgent`; `preboot.agent_commit` `95596a91` is the last commit under `testing/agent` or `testing/PZAgent`; `preboot.driver_checks.agent_lua_dirty`, `agent_base_dirty` and `driver_dirty` false), and the last commit under `testing/PZAgent` is `c8493a0e` (Plan 22 Task 9 fix 2), so the Lua under test is the agent base, PZAgent 1.0 (`readings.hello.hello.mod` `1.0`, `proto` `PZA/1`): `PZAgent_Main.lua`, `PZAgent_Link.lua`, `PZAgent_Map.lua`, `PZAgent_Motor.lua`, `PZAgent_Sense.lua`, `PZAgent_Skills.lua`, `shared/PZAgent_Core.lua` and `shared/PZAgent_Schema.lua` at `c8493a0e`. Fixture `agent0` (`fixture.provision_run` `prov-20261026-102802`, `fixture.build` `42.21.0`; `hello.build` `42.21`; `build` `42.21.0`); profile `testing/profiles/agent-nozombies.toml` (`profile.name` `agent-nozombies`; PZTestKit + PZAgent, `profile.sandbox.Zombies` 6, user `admin` on a `-debug` client, a 90-minute day). Graded by `testing/agent/base/gates.py` `gate_x4` through `testing/agent/drivers/x4_grade.py` (both last changed before the boot; `gate_x4` is frozen once this artifact carries its output).

**Plan 22's X4, "the link"**: the agent base's first live session (spec `docs/superpowers/specs/2026-10-27-plan-22-agent-base-design.md` § 10, its live gates; § 8 (6), the sidecar trigger). The base is PZA/1 over the file channel: the positional encoder for frames and map parts, one flush a tick, the Skills runner and the Map watch. The agent stood still at 60 Hz for 30 s, scanned r = 15, walked twenty 6-tile `walkTo` legs, scanned again and stood until the frames' cost rows spanned 600 s; the driver graded the base's tick cost, its worst tick, the pipe, the command-to-motion latency and the kept map. The driver's docstring (L1–L45) restates every phase, reading and key and is the committed source of the schedule.

## 0. The run

- **Wall.** 702.2 s (`wall_seconds`; against `constants.BUDGET_S` 840, counted from the memory gate, the boot included). Server started at 52.7 s, the client ready at 90.5 s (`timeline`; `client_seen[0].ready` 37.4 s after its launch), both `verify` pings ok (server 92.3 s, client 92.5 s), client quit rc 0 at 694.4 s, server stopped rc 0 with 0 errors at 702.2 s. Phases (`phase_walls`, seconds from the gate): `hello` 92.497–92.51, `rate60` 92.512–122.674, `scan` 122.69–123.518, `walk` 123.534–353.248, `final_scan` 353.289–354.532, `worst_window` 354.572–689.559, `server` 689.636–692.155.
- **Hello.** `readings.hello`: `ok` true, `proto` `PZA/1`; the hello line (`state.log` seq 1, tick 1): `mod` `1.0`, `build` `42.21`, `user` `admin`, `rate` 10, `mode` `append`, `caps` the ten skill types `attack`, `consume`, `drop`, `equip`, `interact`, `rate`, `scan`, `steer`, `stop`, `walkTo`; `first_frame.seq` 43.
- **Pipe health.** `frames.gaps` 0 (`gap_list` `[]`), `frames.bad` 0, `frames.lua_errors` 0 (`lua_error_msgs` `[]`), `frames.parks` 0, `logs.clients.admin` `[]`, `admin_lua_error` false, `server_error_count` 0 (`server_errors` `[]`), `bus_dead` null; every frame's `cost.dropped` reads 0 (`frames.cost`, 7505 rows).
- **Stops.** `finished` true; `phase_errors` `{}`; `notes` `[]`; `verdicts` `{}`; the artifact carries no `abort`, `error` or `budget_stop` key; `readings.worst_window.stopped` `span` (`span_s` 600.066, `frames` 7505).
- **Frames.** `state.log` holds 8061 lines and line *n* is seq *n* on every line (checked line by line): 1 `hello`, 7533 `frame`, 268 `map` (98 `full`, 49 for each of the two scans; 170 `delta`), 249 `act` (2 `rate` done, 2 `scan` done, 20 `walkTo` accepted, 205 `walkTo` progress, 20 `walkTo` done) and 10 `event` (9 `item_added` at seq 2–10, the inventory's first sight, and 1 `door` at seq 2092). The driver read 7505 frames (`frames.n`, seq 43–8033), each `cost` row equal to its line's wherever the line carries one (675 delta frames elide an unchanged `cost` as `true`, which the driver merges from the frame before); the 28 frames seq 8034–8061 came after its last read. Of the 7504 consecutive frame pairs the driver read, 1805 are one tick apart (the 60 Hz window), 5697 six ticks apart (10 Hz), one two (seq 209 → 211, the switch to 60 Hz) and one five (seq 2016 → 2018, the switch back).
- **Memory.** Free 13.51 GB at the preboot read and the memory wait, 2.31 GB at ready, 15.85 GB after teardown (`memory`, `memory_wait`).
- **The server reading.** `readings.server.stats` (`stats.all admin` at 689.636 s) and `readings.server.players` (`["admin"]`); nothing below rests on them.

Files, byte-identical to the run copy under `testing/runs/x4_link-20261027-171916/`:

| File | Source | Bytes | sha256 |
|---|---|---|---|
| `x4_link.json` | the driver's auto-copy of `testing/runs/x4_link-20261027-171916/x4_link.json` (`cmp` equal); CRLF endings, 115664 line breaks, no final newline | 1957370 | `cc853c11baadb59b82795cc2e759c0762ce91ca2f576b0f9da65ff4816274b26` |
| `state.log` | `testing/runs/x4_link-20261027-171916/clients/admin/Lua/pzagent/admin/state.log`, copied by the write-up (`cmp` equal); LF endings, 8061 lines | 1369779 | `e75db8fb25a9c4a0d6caee7f531790baa73eeedf9bbf69dcba3f4d6ca58127f1` |
| `x4_grade.txt` | `python testing/agent/drivers/x4_grade.py` on this folder's `x4_link.json`, stdout (exit 1); identical (`diff` empty) to the controller's print of the run copy; CRLF endings, 74 lines | 1398 | `ec664dfb7d067819ccfa468922c12f805c7aeca369404ca7c27d503735dfdac3` |

`state.log` is the only evidence of the lines between the frames (the acts, the map parts and deltas, the door event) and of each frame's position; the hashes are of the working-tree bytes as written (re-hash a checkout's blob with `git show <commit>:<path> | sha256sum`). The driver's stdout `testing/runs/x4_link.out`, the client console, `server-stdout.log` and the logs under `server/` and `clients/` are per-machine and untracked, and nothing below rests on them.

## How to read it

**The cost group** (`frames.cost[*].cost`, and the frame line's last array) is written by `PZAgent_Main.lua` (L10–L14 and L143–L144 at `c8493a0e`) on the 1 ms clock (`PZA.now`, `getTimestampMs`, ruling P22-4), and its fields are single ticks, not means since the last frame (the schema's descriptions read "mean"; the Lua writes one tick's span):

- `tickMs` the **previous** tick's whole body; `actMs`, `senseMs` and `mapMs` **this** tick's skill tick, events-and-frame read and scan or watch step; `linkMs` the **previous** tick's `L.flush` (a frame is encoded at its emit, before its own flush); `tickMaxMs` the worst body and `over5` the bodies of 5 ms or more since the last frame (the frame's own tick not yet among them); `dropped` the Link's dropped lines.
- `linkMs` times `L.flush` only (`PZAgent_Link.lua` L195–L233): the map parts' stamp and encode as they leave the backlog, the concat and the file's open, write and close. The frame's own positional encode runs in `PZA.emitFrame` (L130–L146) between the map step and the flush, inside no timed span, as do the poll and an act line's keyed encode.
- At 60 Hz every tick reads and writes a frame, so `tickMs`, `linkMs`, `actMs`, `senseMs` and `mapMs` resolve every tick (the body and the flush one frame late). At 10 Hz a frame is written every sixth tick: `tickMs` and `linkMs` sample the tick before the frame tick, which reads no frame and writes none, and the frame tick's own body is seen only inside the next frame's `tickMaxMs`; `tickMaxMs` and `over5` cover every tick exactly once.
- **Quantisation.** A span read as the difference of two integer-millisecond stamps reads 1 when a millisecond boundary falls inside it and 0 otherwise; a span of *d* < 1 ms reads 1 with probability *d* when its phase against the clock is uniform, so the mean over many spans estimates the span, while one reading is only a bound (a reading *r* is a span between *r* − 1 and *r* + 1 ms), and the mean over the readings above 0 is at least 1 by construction.

**The leg latency** (`gate_x4`'s `cmd_move_p90`, `gates.leg_move_ms`): a leg's `first_move.wallMs` minus its `accepted_wallMs`, both the client's clock: the accept act line's stamp to the first frame after it whose position moved more than `MOVE_EPS_TILES` 0.01 tiles from the position at accept; nearest-rank percentiles (`gates.pct`).

## 1. The tick

**The 60 Hz window** (`readings.rate60`): `frames` 1806, `first_seq` 211 (tick 182) to `last_seq` 2016 (tick 1987), every consecutive pair one tick apart, `span_s` 30.076 (`seconds` 30.031). `tickMs` (each frame's `cost.tickMs`, the bodies of ticks 181–1986) reads mean **1.672203765227021 ms** (3020 / 1806, `tick_mean_ms`); nearest-rank p50 2, p90 2, p99 3, max 9; counts (ms: frames) 0:3 1:696 2:1018 3:74 4:13 5:1 9:1.

Per field over the same 1806 frames (`frames.cost`, seq 211–2016; the 1 ms clock's means of the measured spans):

| field | sum (ms) | mean (ms) | max | counts |
|---|---|---|---|---|
| `senseMs` | 1285 | 0.7115171650055371 | 3 | 0:584 1:1161 2:59 3:2 |
| `mapMs` | 623 | 0.3449612403100775 | 2 | 0:1204 1:581 2:21 |
| `linkMs` | 486 | 0.2691029900332226 | 2 | 0:1345 1:436 2:25 |
| `actMs` | 1 | 0.0005537098560354374 | 1 | 0:1805 1:1 |
| `tickMs` | 3020 | 1.672203765227021 | 9 | 0:3 1:696 2:1018 3:74 4:13 5:1 9:1 |

The four named fields sum to 1.3261351052048729 of the 1.672203765227021 mean. Tick by tick, over the 1805 ticks 182–1986 whose body (the next frame's `tickMs`), flush (the next frame's `linkMs`) and named spans (this frame's `actMs`, `senseMs`, `mapMs`) are all read, the body less the four reads 0 on 1241 ticks, 1 on 508, 2 on 55 and 7 on one (tick 182), mean 0.3462603878116344 ms: the poll, the frame's positional encode, an act line's encode and the timers' own calls, which no field names. The sense read and the map watch, which run on every tick at 60 Hz, hold 1.0564784053156147 ms of the mean.

**The worst tick** (`frames.cost`, all 7505 frames, their `wallMs` spanning 600.066 s; `gate_x4.gates.worst_tick`): the largest `tickMaxMs` is **19**, at seq 43, and `over5` sums to **31** over 30 frames (29 reading 1, seq 43 reading 2). `tickMaxMs` counts over the session: 0:4 1:3105 2:4016 3:311 4:39 5:11 6:10 7:4 8:3 9:1 19:1. The 30 frame windows holding a tick of 5 ms or more, by what `state.log` holds between each and the frame before it:

| what the window holds | frames (seq: `tickMaxMs`) | ticks covered |
|---|---|---|
| the first five ticks: the hello and the 9 first-sight `item_added` events (seq 1–10, tick 1) and 32 first-sight watch `delta` lines (seq 11–42, 8 a tick on ticks 2–5) | 43: **19** (`over5` 2) | 1–5 |
| the next six watch ticks (seq 44–91, 8 `delta` lines a tick) | 92: 5 | 6–11 |
| the `rate` 60 command (act seq 210, tick 182), and the forced full frame seq 211 | 212: 9 (`tickMs` 9: tick 182 itself) | 182 |
| the `rate` 10 command (act seq 2017, tick 1988) | 2018: 6 | 1987–1991 |
| the first `scan` command (act seq 2019, tick 1993) and its first five parts (seq 2020–2024) | 2025: 8 | 1992–1997 |
| a `walkTo` accept, on all 20 legs (each leg's `accepted_seq` + 1) | 2078: 8, 2216: 7, 2352: 5, 2482: 5, 2611: 6, 2736: 7, 2864: 7, 2989: 5, 3115: 6, 3240: 6, 3367: 5, 3492: 6, 3618: 5, 3743: 5, 3870: 6, 3995: 8, 4122: 6, 4247: 7, 4374: 6, 4499: 6 | the six before each |
| the final `scan` command (act seq 4625, tick 15849) and its first three parts | 4629: 6 | 15846–15851 |
| no line: standing at 10 Hz before the switch | 208: 5 | 168–173 |
| no line: a 60 Hz tick (tick 1637: `senseMs` 3 and `mapMs` 1 at seq 1666, `linkMs` 1 and `tickMs` 5 at seq 1667) | 1667: 5 | 1637 |
| no line: leg 12's walk | 3516: 5 | 9822–9827 |
| no line: the worst window, standing | 5811: 5 | 22662–22667 |

So every one of the session's 24 commands (2 `rate`, 2 `scan`, 20 `walkTo`) fell in a window whose worst tick read 5–9 ms, and those are 24 of the 30; consecutive legs' accept windows lie 11299–12349 ms apart on the client's clock, the leg period, which is the 5–8 ms recurrence through the walk. At 10 Hz the frames resolve such a tick only to its six-tick window; at 60 Hz tick 182 is resolved: a 9 ms body of which the named spans hold 2 (`senseMs` 1, `linkMs` 1) and 7 ms is unattributed. The 19 ms tick is one of ticks 1–4: tick 5's body read 5 ms (seq 43's `tickMs`), which is the window's second `over5`. Tick 1 is the init (the hello, the inventory's first sight, one flush) and ticks 2–4 the watch's first ticks, each queueing 8 first-sight deltas; ticks 6–23, queueing the same 8 a tick (169 in all, the watch's 13 × 13 ring), read at most 5 (seq 92), 4 (seq 141) and 4 (seq 183), which points at the init tick but does not show it. Standing at 10 Hz after the final scan (the 3351 frames from seq 4683), the windows read `tickMaxMs` 1:1471 2:1727 3:138 4:13 5:1 (one `0`), and the samples of the tick before each frame (`tickMs`) mean 0.588779468815279 ms.

**The emit against the sidecar trigger.** Spec § 8 (6): "K2's transport spike runs only if X4 reads the emit above 1 ms mean or 3 ms worst per tick at the budget"; `gates.sidecar` reads it as the mean and max of `cost.linkMs` over the frames whose `linkMs` is above 0. Two readings, with their populations:

- **The gate's reading** (`gate_x4.emit_mean_ms`, `emit_worst_ms`, `emit_frames`; ungraded): over the whole session's 486 frames reading `linkMs` above 0, 459 × 1 + 26 × 2 + 1 × 3 = 514 ms, a mean of **1.0576131687242798 ms**, worst **3** (seq 43: the flush of tick 5, which carried 8 first-sight deltas before the first frame); `sidecar_trigger` "fired". 461 of the 486 are 60 Hz frames (436 × 1 + 25 × 2 = 486 ms, mean 1.054229934924078); the other 25 are 10 Hz frames whose `linkMs` is the flush of a tick that wrote no frame (28 ms: seq 43, 3; seq 92, 2; 23 frames of 1). On the 1 ms clock a mean over the readings above 0 is at least 1 by construction, so this reading is the clock's, not the emit's.
- **The 60 Hz window's reading** (`frames.cost` seq 211–2016): every tick wrote a frame, so every one of the 1806 `linkMs` is a flushing tick's flush: mean **0.2691029900332226 ms**, worst **2**, under both the 1 ms and the 3 ms. This is the honest reading of the flush per flushing tick: the mean over every flush of the window, which the clock's quantisation does not bias, where the gate's subset is biased to at least 1.
- **What `linkMs` leaves out.** The frame's positional encode is outside every timed span (How to read it). Taking the flush plus the tick's unattributed remainder as an upper bound on the emit with the encode, over the 1805 ticks 182–1986 it reads 0:841 1:835 2:116 3:12 8:1, mean 0.6155124653739612 ms, under 1; its worst is 3 on twelve ticks and 8 on tick 182 alone, the `rate` 60 command's tick, whose 7 unattributed ms the frames do not split between the command's handling, its act line and the forced full frame's encode.

The controller's **ruling S-18** reads the trigger as **not fired**: the gate's "fired" is the quantisation artifact above, and over the 60 Hz window the flush averages 0.2691029900332226 ms with a worst of 2 ms, both under § 8 (6)'s 1 ms and 3 ms, so K2's transport spike does not run and the frozen `gate_x4` is not edited. This guide reads it the same on the flush; with the encode bounded, the mean is not fired on either reading, and the worst is not fired on every tick but tick 182, where the bound (8) does not separate the encode from the command.

**Scan parts under the positional encoder.** Each scan's 49 parts went out one a tick (98 `full` lines, one per tick), 20 squares a part in 1150–1689 bytes (the last parts 106 and 107). 16 frames read the flush of a tick that wrote one part (1150–1549 bytes): `linkMs` 0 on 8 and 1 on 8. Pass 4 read 1.67 ms (max 4) for a 2102–2103 B JSON part of the same 20 squares (`testing/artifacts/a_pipe_4-20261026-181848/GUIDE.md` line 60); 16 readings on the 1 ms clock bound this run's part flush near half a millisecond and do not measure it.

## 2. The map

**The first scan** (`readings.scan`): `scanId` 1, `parts` 49, `got` 49, `complete` true, `squares` 961, in 0.828 s (`seconds`); `mapMs` on its 9 frames 0, 0, 1, 0, 0, 0, 1, 0, 0 (a frame tick's own scan step, one tick in six; the other steps show only in `tickMaxMs`). From the settled start (10997.5, 9699.5) (`readings.walk.start`) its squares span x 10982–11012, y 9684–9714 (`state.log` seq 2020–2076).

**The watch during the walk** (`readings.walk.map_deltas` **1**, all on leg 1; the other 19 legs' `map_deltas` 0). The watch had sent its 13 × 13 ring as 169 first-sight `delta` lines on ticks 2–23 (seq 11–182, x 10991–11003, y 9693–9705). The walk's one delta, seq 2098 (tick 2152), carried square (10995, 9701, 0) with its door `[true, false, false]` (`open`, `locked`, `barricaded`, the schema's `portal` order), against `[false, true, false]` in the first-sight delta (seq 121) and the first scan (seq 2051); the `door` event at seq 2092 (tick 2124) read the door at (10995, 9701, 0) `open` true, while leg 1's frames walked through that square (seq 2093–2097, y 9700.716796875 to 9701.5). One delta and no more: every square within the ring's 6 tiles of the walk's positions lay inside the first scan's window, and the watch queues a square only when its encoding without light differs from the last one sent (`PZAgent_Map.lua` L1–L15), so only the door's change was new.

**The walk's ground.** Each leg was sent to its own start's x ± 6 at y 9699.5 (`readings.walk.legs[*].target`), but no leg went straight: every leg's frames (those between its accept and the next leg's, positions merged across delta frames) reach y 9695.5 and y 9701.5 and x 10993.5 or less, and all of them lie within x 10993.2–11003.05. Leg 1's path (seq 2080–2212): south-west to the door square (10995, 9701), west to x 10993.2, north to y 9695.5, east along y 9695.5 to x 11001.5, then south and south-east to (11003.0, 9699.0). The pathfinder's route, not the commanded line, is what every leg's frames show.

**The final scan and the kept map** (`readings.final_scan`): settled (`settled` true) at (10995.5, 9700.154296875), the kept map snapshotted before the scan (`kept_squares` 961), then `scanId` 2, 49 of 49 parts, 961 squares in 0.859 s (`mapMs` 0, 0, 0, 0, 1, 1, 0, 0, 0). Its window, x 10980–11010 and y 9685–9715 (seq 4626–4682), is shifted from the first scan's: the two share 870 squares, and the 91 final squares at x 10980–10981 and y 9715 lie outside the kept map (no line of the session sent them before the final scan). None of the 91 carries a wall, a door, a window or a container, so each kind's `absent` reads 0; and the 870 shared squares read identical in the kept map and the final scan in every field but `light` (`state.log`, compared square by square). The four kinds (`readings.final_scan.kept`):

| kind | kept | total | absent | seen | ratio |
|---|---|---|---|---|---|
| walls (`solid` true) | 6 | 6 | 0 | 6 | 1.0 |
| doors | 3 | 3 | 0 | 3 | 1.0 |
| windows | 13 | 13 | 0 | 13 | 1.0 |
| containers (by square and type) | 21 | 21 | 0 | 21 | 1.0 |

So the kept map held every one of the final scan's 43 walls, doors, windows and containers, the door's opening included; `absent` is coverage by kind, and the square coverage was 870 of 961.

## 3. The legs

Each leg's `accepted_seq` is its `walkTo` accepted act line, its first move the first frame after it whose position moved more than 0.01 tiles, its latency `first_move.wallMs` − `accepted_wallMs` on the client's clock (`readings.walk.legs[*]`); every leg was `settled` true before its send, its `at_accept` equal to its start:

| leg | start x | target x | `accepted_seq` | `first_move.seq` | latency (ms) | end | `result.d` |
|---|---|---|---|---|---|---|---|
| 1 | 10997.5 | 11003.5 | 2077 | 2079 | 130 | done | 0.9833203675875426 |
| 2 | 11003.0478515625 | 10997.0478515625 | 2215 | 2217 | 146 | done | 0.9836122494413012 |
| 3 | 10996.58203125 | 11002.58203125 | 2351 | 2353 | 181 | done | 0.9934674515098483 |
| 4 | 11002.3505859375 | 10996.3505859375 | 2481 | 2483 | 162 | done | 0.9910396634660937 |
| 5 | 10995.943359375 | 11001.943359375 | 2610 | 2612 | 178 | done | 0.9966259301407455 |
| 6 | 11001.5 | 10995.5 | 2735 | 2737 | 143 | done | 1 |
| 7 | 10995.5 | 11001.5 | 2863 | 2865 | 163 | done | 0.96484375 |
| 8 | 11001.5 | 10995.5 | 2988 | 2990 | 164 | done | 1 |
| 9 | 10995.5 | 11001.5 | 3114 | 3116 | 146 | done | 0.96484375 |
| 10 | 11001.5 | 10995.5 | 3239 | 3241 | 146 | done | 1 |
| 11 | 10995.5 | 11001.5 | 3366 | 3368 | 165 | done | 0.96484375 |
| 12 | 11001.5 | 10995.5 | 3491 | 3493 | 163 | done | 1 |
| 13 | 10995.5 | 11001.5 | 3617 | 3619 | 164 | done | 0.96484375 |
| 14 | 11001.5 | 10995.5 | 3742 | 3744 | 129 | done | 1 |
| 15 | 10995.5 | 11001.5 | 3869 | 3871 | 161 | done | 0.96484375 |
| 16 | 11001.5 | 10995.5 | 3994 | 3996 | 145 | done | 1 |
| 17 | 10995.5 | 11001.5 | 4121 | 4123 | 146 | done | 0.96484375 |
| 18 | 11001.5 | 10995.5 | 4246 | 4248 | 128 | done | 1 |
| 19 | 10995.5 | 11001.5 | 4373 | 4375 | 146 | done | 0.96484375 |
| 20 | 11001.5 | 10995.5 | 4498 | 4500 | 128 | done | 1 |

All 20 legs moved and ended `done` with an empty `reason`; none lacks a first move, so no leg counts +inf in the gate. Over the 20 latencies, 128–181 ms: nearest-rank p50 **146**, p90 **165** (`gate_x4.gates.cmd_move_p90.value`), max **181**; mean 151.7. On every leg the first move is the second frame after the accept (`first_move.seq` = `accepted_seq` + 2): the frame after the accept, the one carrying that window's 5–8 ms `tickMaxMs` (§ 1), had not yet moved. The rows' y and the targets' y 9699.5 are the commanded line; the legs' paths are § 2's loop.

## 4. What the frames cannot say, the host, corrections

**What the frames cannot say.**

- **A tick finer than its window at 10 Hz.** A 10 Hz frame reads one tick's `tickMs` and `linkMs` (the tick before it) and the worst of six in `tickMaxMs`; which tick of a window was the 5–9 ms one, and so whether it was the command's own tick, is not read (only tick 182, at 60 Hz, is).
- **What a burst tick did.** Every command fell in a burst window, but no field times the poll, a command's start, an act line's encode or a frame's encode, so the 7 unattributed ms of tick 182 and the walk's 5–8 ms windows have no cause in this artifact: whether the vanilla path request, the act line's snapshot and encode, or the file's write is the cost is the fix pass's question.
- **The 19 ms tick's owner.** One of ticks 1–4: the init tick or one of the watch's first three; the frames do not separate them.
- **Sub-millisecond spans.** Every `cost` field is an integer on the 1 ms clock: a single reading is a bound, a mean over many is the clock's mean of the measured spans (§ How to read it), and the gate's mean over the readings above 0 is at least 1 by construction.
- **The emit with its encode.** `linkMs` is the flush alone; the frame's encode is inside the unattributed remainder with the poll and the timers, so the emit is bounded (§ 1), not measured.
- **The two clocks.** A line's `wallMs` is the client's clock in epoch milliseconds; the driver's `*_wall` keys are this process's clock in seconds; nothing here sets one against the other, and every latency and span above is a difference within one clock.
- **The kept map's square coverage.** The ratios are fidelity over the 43 features the final scan found, all on the 870 squares both scans covered; the 91 squares only the final scan sent hold none, so the run does not read the kept map's fidelity on squares the watch alone sent as they changed beyond the door.
- **Why the legs looped.** The frames show the paths, not the obstacle the pathfinder routed around; the door's `locked` reading `true` before it opened is the Map's reading, not explained here.

**The host.** One Windows host; free memory 13.51 GB at the gate, 2.31 GB at ready with the server and the `-debug` client up, 15.85 GB after teardown (`memory`); the controller's own read at its 17:19 dispatch was 13.67 GB. Every millisecond above is this host's.

**The epoch-ms leaves** (wildcard): `*wallMs`, `*_wall`, `wall_*` and `epoch_ms_*` anywhere in `x4_link.json` (`frames.cost[*].wallMs`, `readings.walk.legs[*].accepted_wallMs`, `accepted_wall`, `first_move.wallMs`, `end.ended_wall`, `readings.*.act.ended_wall`, `rate_on.ended_wall`, `server_launch_wall`, `server_started_wall`, `session_ready_wall`, `wall_seconds`, `steps[*].wall_before`, `epoch_ms_before` and the like), the `wallMs` of every line of `state.log`, and `took`, `timeline`, `phase_walls`, `client_seen`, `memory[*].wall` and `memory_wait[*].wall` are this host's clocks, cited only as a difference within this run (a latency, a span), never as a reading.

**Corrections to the controller's ledger** (`.superpowers/sdd/2026-10-27-plan-22-agent-base/progress.md`, the line "Task 12 X4 run x4_link-20261027-171916", the rulings S-18 and S-19, and the Task 13 dispatch note):

1. "the 19 ms tick is seq 43 (the first frame after init, map delta lines 40–46 beside it: the watch's first pass)": seq 43 reads it, but the tick is one of ticks 1–4 (tick 5 read 5 ms), and the window's lines are seq 1–42 (the hello, 9 `item_added` events, 32 first-sight deltas on ticks 2–5); delta lines 44–46 are tick 6's, after it. The frames do not say whether it was the init or the watch.
2. "9 ms at seq 212 (the first 60 Hz frame)": the first 60 Hz frame is seq 211 (`readings.rate60.first_seq`); seq 212's `tickMs` 9 is tick 182's body, the tick that took the `rate` 60 command (act seq 210) and wrote the forced full frame seq 211.
3. "8 ms at 2025/2078 (the scan)": seq 2025's window holds the first scan's command (act seq 2019) and its first five parts; seq 2078's holds leg 1's `walkTo` accept (act seq 2077), after the scan's last part (seq 2076).
4. "a 5–8 ms tick recurs about every 125–130 frames (about 12.5 s) at 10 Hz through the walk and the worst window (seqs 2216, 2352, 2482, … 4629)": each walk instance is the window holding a leg's `walkTo` accept, on all 20 legs (seq 2078 included), consecutive ones 11299–12349 ms apart, the leg period; 4629 holds the final scan's command; the seq gaps count act lines and are not frame counts. The worst window holds one 5 ms window (seq 5811) and no recurrence; the walk's seq 3516 is the other lone one.
5. The dispatch note's "the walk is along y = 9699.5 over x ± 6 of the start": the targets are, but every leg's path looped, reaching y 9695.5, y 9701.5 and x 10993.5 or less within x 10993.2–11003.05, through the door at (10995, 9701); the one walk delta is that door opening, not an unchanged square.
6. The dispatch note's "the final scan's 961 squares against 961 kept (`absent` 0: full coverage, so the 1.0 ratios are fidelity over every square)": the final scan's window is shifted (x 10980–11010, y 9685–9715) and 91 of its 961 squares were never in the kept map; `absent` is per kind and reads 0 because none of the 91 carries a wall, door, window or container. The ratios are fidelity over all 43 features; square coverage is 870 of 961.
7. S-18's cost-if-wrong, "X2's 148 µs encode + 138 µs flush projection matches the 0.27 ms read": `linkMs` is the flush alone; the frame's encode is untimed (`PZA.emitFrame`), so 0.2691029900332226 ms is not encode plus flush; with the encode bounded by the unattributed remainder the emit's mean is at most 0.6155124653739612 ms (§ 1). S-18's reading of the trigger holds on the mean; its worst holds except on tick 182 (§ 1).
8. S-19's "survival at 10 Hz, where the tick reads 0–1 ms": at 10 Hz `tickMs` samples the tick before each frame, which reads no frame; the frame tick shows only in `tickMaxMs`, which reads 1–3 on 3336 of the 3351 standing 10 Hz windows after the final scan (§ 1).
9. The Task 13 amendments' `hello.modVersion` is `readings.hello.hello.mod` here (`1.0`), and their "each a mean since the last frame" for the cost group is the schema's wording; the Lua writes single-tick spans (How to read it).

## 5. The grade

`gate_x4` (`x4_grade.txt`, verbatim values; the same object is `gate_x4` in `x4_link.json`):

| gate | ok | value | threshold | n |
|---|---|---|---|---|
| `tick_mean_at60` | **false** | 1.672203765227021 | mean < 1.0 ms over >= 1620 frames | 1806 |
| `worst_tick` | **false** | `tickMaxMs` 19, `over5` 31, `span_s` 600.066 | max tickMaxMs <= 3.0 ms and 0 over5, over >= 600.0 s | 7505 |
| `gaps` | true | 0 | == 0 | 1 |
| `lua_errors` | true | 0 | == 0 | 1 |
| `parks` | true | 0 | == 0 | 1 |
| `cmd_move_p90` | true | 165 | p90 < 500.0 ms over >= 20 legs | 20 |
| `map_kept` | true | walls 1.0, doors 1.0, windows 1.0, containers 1.0 | each of walls/doors/windows/containers ratio >= 0.99 | 43 |

**Verdict: NO-GO** (`verdict`), on `tick_mean_at60` and `worst_tick`. Beside it, ungraded: `sidecar_trigger` "fired", `emit_mean_ms` 1.0576131687242798, `emit_worst_ms` 3, `emit_frames` 486, `sidecar_thresholds` `{mean_ms 1.0, worst_ms 3.0}`. Re-running `x4_grade.py` on this folder's `x4_link.json` reproduces `x4_grade.txt` byte for byte against the controller's print of the run copy.

**The sidecar trigger.** By the gate, "fired", which by § 8 (6) would run K2's transport spike. The controller's **ruling S-18** reads it as **not fired** (§ 1: the gate's mean over the readings above 0 is at least 1 on the 1 ms clock; over the 60 Hz window the flush reads 0.2691029900332226 ms mean and 2 ms worst), so the spike does not run; `gate_x4` stays frozen, and a `gate_x4_2` reading the window is minted only if a second X4 pass runs. This guide's reading: not fired on the mean on any reading; not fired on the worst on the flush, and on the bound with the encode on every tick but the `rate` 60 command's tick 182 (8), which the frames do not split.

**What follows.** The controller's **ruling S-19**: the plan continues to X5 and the acceptance run on this NO-GO as go-with-findings: the failed gates are the base's own cost at 60 Hz (the sense read and the map watch every tick, 1.0564784053156147 ms of the 1.672203765227021 mean) and the bursts (the 19 ms first ticks and the 5–9 ms command windows), neither of which changes what a 10 Hz session measures; the one fix pass the plan allows (`x4_link_2.py`, graded by the same `gate_x4`) runs after the plan's consolidated fix wave, where the Lua cost edits land, so the re-measure reads the fixed base once.

## Do not cite from this file

| Key | Value in the file | Why not |
|---|---|---|
| everything measured here, as a population | — | `n = 1` boot, one fixture, one character, one host. |
| `gate_x4.sidecar_trigger` | "fired" | A mean over the 1 ms clock's readings above 0, at least 1 by construction; ruling S-18 reads the trigger as not fired (§ 1, § 5). |
| `gate_x4.emit_mean_ms` as the emit per flushing tick | 1.0576131687242798 | The subset reading above 0; the flush per flushing tick is the 60 Hz window's 0.2691029900332226 mean over 1806 flushes. |
| `frames.cost[*].cost.linkMs` and `cost.tickMs` at 10 Hz as a frame tick's cost | 0–3 | They sample the tick before each frame tick, which reads and writes no frame. |
| any single `cost.*Ms` reading | integers 0–19 | The 1 ms clock: a reading is a bound, never a value. |
| `readings.final_scan.kept.*.absent` as square coverage | 0 | Per kind: 91 of the 961 final squares were not in the kept map. |
| `readings.walk.legs[*].target` as the path walked | x0 ± 6 at y 9699.5 | Every leg looped, reaching y 9695.5 and 9701.5 within x 10993.2–11003.05 (§ 2). |
| `readings.walk.legs[*]` latency finer than a frame | 128–181 | Frame-quantised at about 100 ms (the first move is always the second frame after the accept). |
| `readings.scan.mapMs`, `readings.final_scan.scan.mapMs` as the scan's cost | 0–1 | A frame tick's own step, one tick in six. |
| `readings.server.stats.ack.mult` | 4.800405979156494 | getMultiplier, not the true multiplier (#3762). |
| every `reason` and error text | empty | Empty in this run; a text is the driver's or the Lua's message, not a reading. |
| `constants`, `preboot`, `profile`, `fixture`, `argv`, `memory`, `memory_wait`, `world_changes`, `steps`, `verify` | the driver's tables | Written before or around the run, or the server reading's raw steps; not readings. |
