# `x4_link_2-20261027-210612` reading guide

**`x4_link_2-20261027-210612/x4_link_2.json`** (with `state.log` and `x4_grade.txt`) — produced by `testing/agent/drivers/x4_link_2.py` at `driver_commit` `fc1d58cf` (Plan 22 X4 fix pass 3), unedited since (its last commit at HEAD is `fc1d58cf`), which imports `testing/agent/drivers/_dlib.py` and `testing/experiments/xlib.py` (`preboot.xlib_commit` `45c49217`); on HEAD `5d9debb5` at the boot (`preboot.commit`; `preboot.harness_lua_commit` `edcaf2e6`, the fix wave's Lane H, `preboot.harness_lua_dirty` false; `preboot.harness_py_commit` `52a7de93`); the agent mod `testing/PZAgent/PZAgent` loaded by path from the tree (`profile.sources.PZAgent`; `preboot.agent_commit` `5d9debb5`, the last commit under `testing/agent` or `testing/PZAgent`; `preboot.driver_checks.agent_lua_dirty`, `agent_base_dirty` and `driver_dirty` false), so the Lua under test is the agent base at `5d9debb5` (Plan 22 X4 fix pass fix 1), PZAgent 1.1 (`readings.hello.hello.mod` `1.1`, `proto` `PZA/1`). Fixture `agent0` (`fixture.provision_run` `prov-20261026-102802`, `fixture.build` `42.21.0`; `hello.build` `42.21`; `build` `42.21.0`); profile `testing/profiles/agent-nozombies.toml` (`profile.name` `agent-nozombies`; PZTestKit + PZAgent, `profile.sandbox.Zombies` 6, user `admin` on a `-debug` client, a 90-minute day). Graded by `testing/agent/base/gates.py` `gate_x4` through `testing/agent/drivers/x4_grade.py`, both unchanged since the first X4 session's boot at `95596a91` (`git diff --stat 95596a91 HEAD` on the two files is empty).

**Plan 22's X4 fix pass, "the link" again**: the second X4 session, the plan's one fix pass (ruling S-19), on the same schedule as the first (`testing/artifacts/x4_link-20261027-171916/GUIDE.md`, the base before the pass) and graded by the same frozen `gate_x4` (ruling S-19's "same gate"; the gate is never edited after the first artifact carried it). The agent stood still at 60 Hz for 30 s, scanned r = 15, walked twenty 6-tile `walkTo` legs, scanned again and stood until the frames' cost rows spanned 600 s. The driver's docstring (L1–L45) restates every phase, reading and key.

**What changed since the first session.** The Lua under test differs from the first session's `c8493a0e` by the fix wave's Lane L commits (`5854203a`, `dccc2146`, `3b2339dd`, `4dbdb6cf`, `e8fe1964`, `88296b4c`, `a1218093`: the map phase under its own pcall, the Skills split, `S.nearestZombie` off the last frame, the cost fields' wording, among others) and the X4 fix pass's (`1d2e2d24` the cost group's `pollMs`, `startMs` and per-phase maxima and `me`'s `zombiesSeen`/`zombiesListed`; `b8630daf` PZA/1.1 and PZAgent 1.1; `daa3ef03` the watch stepped every 6th tick whatever the rate, a square read whole only when its fingerprint changed; `4be64f1f` the inventory's first sight through the Link's backlog; `d9fe59c2` door events from the map's records, Sense's 81-square door walk dropped; `51bebb20` one zombie walk a frame; `013a0abb` the act line's snapshot off the last frame; `bd915b62` the ack write named; `02d99b5c` and `09bb95fe` two error-path fixes; `5d9debb5` the `scan_dropped` event, the fingerprint keyed on `floor(z)`); `git log 95596a91..5d9debb5 -- testing/PZAgent` lists them. The driver `x4_link_2.py` is `x4_link.py` with only its docstring head and `KEY`, `DRIVER` and `ARTIFACT` changed (`diff testing/agent/drivers/x4_link.py testing/agent/drivers/x4_link_2.py`); its docstring names the pass's first ten Lua commits and not `5d9debb5`, which the boot ran. The Python side also moved: the `FileTransport` retries a `cmd.txt` replace that meets a sharing violation (`6925886d`) and seeds its command seq from `ack.txt` (`21afe8f6`).

## 0. The run

- **Wall.** 688.2 s (`wall_seconds`; against `constants.BUDGET_S` 840, counted from the memory gate, the boot included). Server started at 40.7 s (`server_started_wall` 40.683), the client ready at 77.4 s (`timeline`; `client_seen[0].ready` 36.4 s after its launch), both `verify` pings ok (server 78.2 s, client 78.7 s), client quit rc 0 at 680.5 s, server stopped rc 0 with 0 errors at 688.2 s. Phases (`phase_walls`, seconds from the gate): `hello` 78.639–78.646, `rate60` 78.647–108.803, `scan` 108.834–109.666, `walk` 109.693–339.334, `final_scan` 339.391–340.622, `worst_window` 340.678–676.835, `server` 676.939–678.205.
- **Hello.** `readings.hello`: `ok` true, `proto` `PZA/1`; the hello line (`state.log` seq 1, tick 1): `mod` `1.1`, `build` `42.21`, `user` `admin`, `rate` 10, `mode` `append`, `caps` the ten skill types `attack`, `consume`, `drop`, `equip`, `interact`, `rate`, `scan`, `steer`, `stop`, `walkTo`; `first_frame.seq` 11.
- **Pipe health.** `frames.gaps` 0 (`gap_list` `[]`), `frames.bad` 0, `frames.lua_errors` 0 (`lua_error_msgs` `[]`), `frames.parks` 0, `logs.clients.admin` `[]`, `admin_lua_error` false, `server_error_count` 0 (`server_errors` `[]`), `bus_dead` null; every frame's `cost.dropped` reads 0 (`frames.cost`, 7505 rows).
- **Stops.** `finished` true; `phase_errors` `{}`; `notes` `[]`; `verdicts` `{}`; the artifact carries no `abort`, `error` or `budget_stop` key; `readings.worst_window.stopped` `span` (`span_s` 600.013, `frames` 7505).
- **Frames.** `state.log` holds 8050 lines and line *n* is seq *n* on every line (checked line by line, each line decoded by `testing/agent/base/pza1.py`): 1 `hello`, 7522 `frame`, 268 `map` (98 `full`, 49 for each of the two scans; 170 `delta`), 249 `act` (2 `rate` done, 2 `scan` done, 20 `walkTo` accepted, 205 `walkTo` progress, 20 `walkTo` done) and 10 `event` (9 `item_added` at seq 2–10, all stamped tick 1, the inventory's first sight, and 1 `door` at seq 2097). No `scan_dropped`, `overflow` or `lua_error` event. The driver read 7505 frames (`frames.n`, seq 11–8033), each `cost` row equal to its line's wherever the line carries one (430 delta frames elide an unchanged `cost` as `true`, which the driver merges from the frame before); the 17 frames seq 8034–8050 came after its last read. Of the 7504 consecutive frame pairs the driver read, 1804 are one tick apart (the 60 Hz window), 5698 six ticks apart (10 Hz), one three (seq 173 → 183, the switch to 60 Hz) and one five (seq 2004 → 2006, the switch back).
- **Zombies.** `me.zombiesSeen` and `me.zombiesListed` (the pass's new fields) read 0 and 0 on all 7522 frames: fixture `agent0` holds none.
- **Memory.** Free 12.63 GB at the preboot read and the memory wait, 2.67 GB at ready, 16.66 GB after teardown (`memory`, `memory_wait`).
- **The server reading.** `readings.server.stats` (`stats.all admin` at 676.939 s) and `readings.server.players` (`["admin"]`); nothing below rests on them.

Files, byte-identical to the run copy under `testing/runs/x4_link_2-20261027-210612/`:

| File | Source | Bytes | sha256 |
|---|---|---|---|
| `x4_link_2.json` | the driver's auto-copy of `testing/runs/x4_link_2-20261027-210612/x4_link_2.json` (`cmp` equal); CRLF endings, 175703 line breaks, no final newline | 3240666 | `10237d659dd62016fbc4ee55b0c47704fd6ffb822879871fc542a53c0f1a36f5` |
| `state.log` | `testing/runs/x4_link_2-20261027-210612/clients/admin/Lua/pzagent/admin/state.log`, copied by the write-up (`cmp` equal); LF endings, 8050 lines | 1495614 | `331912d11a2cbacdceda17feac6905b4a51ecbbc15ed7d700b1986d92d04df87` |
| `x4_grade.txt` | `python testing/agent/drivers/x4_grade.py` on this folder's `x4_link_2.json`, stdout (exit 1); byte-identical (`cmp` equal) to the controller's print of the run copy; CRLF endings, 74 lines | 1398 | `05ac1b8188d38e87f9c5410b77a650755c7b52af550082cfd4072a02b74448eb` |

`state.log` is the only evidence of the lines between the frames (the acts, the map parts and deltas, the events) and of each frame's position; the hashes are of the working-tree bytes as written (re-hash a checkout's blob with `git show <commit>:<path> | sha256sum`). The driver's stdout `testing/runs/x4_link_2.out`, the client console, `server-stdout.log` and the logs under `server/` and `clients/` are per-machine and untracked, and nothing below rests on them.

## How to read it

**The cost group** (`frames.cost[*].cost`, and the frame line's last array, 16 fields) is written by `PZAgent_Main.lua` (its header L14–L22 and `body` L180–L227 at `5d9debb5`) on the 1 ms clock (`PZA.now`, `getTimestampMs`, ruling P22-4); every field is a single tick's span or a maximum, never a mean. For a frame on tick T1 whose frame before was on tick T0:

- `pollMs`, `startMs`, `actMs`, `senseMs`, `mapMs`: **this** tick T1's `L.poll` (its `ack.txt` write included), command start (Main's `scan` or `rate` answer, else `K.start`), skill tick, events-and-frame read and scan or watch step.
- `tickMs` and `linkMs`: the **previous** tick T1 − 1's whole body and its `L.flush` (a frame is encoded at its emit, before its own flush).
- `tickMaxMs` and `over5`: the worst body and the bodies of 5 ms or more over ticks T0 … T1 − 1 (the frame tick's own body falls in the next frame's window).
- `maxPollMs`, `maxStartMs`, `maxActMs`, `maxSenseMs`, `maxMapMs` (new in the pass): each phase's worst over ticks T0 + 1 … T1, this tick included; `maxLinkMs`: the worst flush over ticks T0 … T1 − 1. So a tick's poll and its body can fall in two neighbouring frames when the tick is a frame tick.
- `dropped` the Link's dropped lines.

At 60 Hz every tick reads and writes a frame, so every field resolves every tick (the body and the flush one frame late). At 10 Hz a frame is written every sixth tick (`tick % 6 == 0`): `tickMs` and `linkMs` sample the tick before the frame tick, the maxima and `tickMaxMs` cover every tick of the window once.

**What each phase does** (`PZAgent_Link.lua` at `5d9debb5`): `L.poll` (L253–L272) opens `cmd.txt`, reads its first non-empty line, closes it and decodes the line with `PZA.decode` on **every** tick once the driver has written a command (the file keeps the last command; an old seq returns nil after the decode), and on a tick whose line carries a new seq it also opens, writes and closes `ack.txt` (`writeAll`, L44); that write is inside `pollMs` (the timers `tp` and `t0` around `L.poll`, `PZAgent_Main.lua` L190–L192), never in `linkMs`. `L.flush` (L205–L244) stamps and encodes the backlog's lines under `BUDGET_BYTES` 1536 and makes one open-write-close of `state.log`. The frame's positional encode (`PZA.emitFrame`, L133–L149) and the overflow check run inside no timed span. The watch steps on `MP.watchDue(tick)`, `tick % 6 == 0`, whatever the rate (`PZAgent_Map.lua` L283–L285).

**Quantisation.** A span read as the difference of two integer-millisecond stamps reads 1 when a millisecond boundary falls inside it and 0 otherwise; a span of *d* < 1 ms reads 1 with probability *d* when its phase against the clock is uniform, so the mean over many spans estimates the span, while one reading is only a bound (a reading *r* is a span between *r* − 1 and *r* + 1 ms), and the mean over the readings above 0 is at least 1 by construction.

**The leg latency** (`gate_x4`'s `cmd_move_p90`, `gates.leg_move_ms`): a leg's `first_move.wallMs` minus its `accepted_wallMs`, both the client's clock: the accept act line's stamp to the first frame after it whose position moved more than `MOVE_EPS_TILES` 0.01 tiles from the position at accept; nearest-rank percentiles (`gates.pct`).

## 1. The tick

**The 60 Hz window** (`readings.rate60`): `frames` 1805, `first_seq` 183 (tick 117) to `last_seq` 2004 (tick 1921), every consecutive pair one tick apart, `span_s` 30.062 (`seconds` 30.03). `tickMs` (each frame's `cost.tickMs`, the bodies of ticks 116–1920) reads mean **1.2614958448753462 ms** (2277 / 1805, `tick_mean_ms`); nearest-rank p50 1, p90 2, p99 3, max 4; counts (ms: frames) 0:99 1:1191 2:465 3:44 4:6.

Per field over the same 1805 frames (`frames.cost`, seq 183–2004; the 1 ms clock's means of the measured spans):

| field | sum (ms) | mean (ms) | max | counts |
|---|---|---|---|---|
| `pollMs` | 766 | 0.42437673130193904 | 2 | 0:1059 1:726 2:20 |
| `linkMs` | 781 | 0.4326869806094183 | 2 | 0:1039 1:751 2:15 |
| `senseMs` | 486 | 0.2692520775623269 | 2 | 0:1329 1:466 2:10 |
| `mapMs` | 62 | 0.03434903047091413 | 1 | 0:1743 1:62 |
| `actMs` | 9 | 0.004986149584487534 | 1 | 0:1796 1:9 |
| `startMs` | 5 | 0.002770083102493075 | 1 | 0:1800 1:5 |
| `tickMs` | 2277 | 1.2614958448753462 | 4 | 0:99 1:1191 2:465 3:44 4:6 |

The six named fields sum to 1.168421052631579 of the 1.2614958448753462 mean. Tick by tick, over the 1804 ticks 117–1920 whose body (the next frame's `tickMs`), flush (the next frame's `linkMs`) and named spans (this frame's `pollMs`, `startMs`, `actMs`, `senseMs`, `mapMs`) are all read, the body less the six reads 0 on 1640 ticks, 1 on 161 and 2 on 3, mean 0.09257206208425721 ms: the frame's positional encode, the overflow check and the timers' own calls, which no field names. The poll and the flush together, tick by tick over the same 1804 ticks, read 0:675 1:724 2:392 3:13, mean **0.8575388026607539 ms**: the link's two file operations a tick, the poll's decode of the command line included. Mean less poll less flush is 0.4044321329639888 ms: the sense read, the watch, the skill tick and the start (0.3113573407202216 named) and the unattributed remainder.

**The watch at 60 Hz.** `mapMs` read 1 on 62 of the 1805 frames: 60 of them on watch ticks (`tick % 6 == 0`; 301 of the window's ticks) and 2 on ticks 1 and 2 past one, where the map phase does nothing and a millisecond boundary fell inside the empty span. So the watch stepped every sixth tick at 60 Hz, reading 1 on 60 of its 301 steps (by the quantisation, about a fifth of a millisecond a step). The window's first 17 map lines (seq 187–215) are the watch's last three first-sight steps (ticks 120, 126 and 132; 8, 8 and 1 squares); after tick 132 the watch cycled its ring by fingerprint and sent no delta until the door changed (§ 2).

**The `rate` 60 command's tick.** Tick 117 took the command (act seq 182) and wrote the forced full frame seq 183: its `pollMs` 2, `startMs` 1, `actMs`, `senseMs` and `mapMs` 0 (seq 183), its body 4 and its flush 1 (seq 184's `tickMs` and `linkMs`), so its named spans hold all 4 of its body.

**The worst tick** (`frames.cost`, all 7505 frames, their `wallMs` spanning 600.013 s; `gate_x4.gates.worst_tick`): the largest `tickMaxMs` is **15**, at seq 11, and `over5` sums to **25** over 25 frames, each reading 1. `tickMaxMs` counts over the session: 0:188 1:6237 2:987 3:58 4:10 5:12 6:8 7:3 8:1 15:1. The 25 frame windows holding a tick of 5 ms or more, by what `state.log` holds between each and the frame before it, with the window's phase maxima:

| what the window holds | frames (seq: `tickMaxMs` / `maxPollMs`) | ticks of `tickMaxMs` |
|---|---|---|
| the first five ticks: the hello and the 9 first-sight `item_added` events (seq 1–10, tick 1); no map line | 11: **15** / 1 (`maxLinkMs` 4, `maxSenseMs` 1, `maxMapMs` 1, `maxStartMs` and `maxActMs` 0) | 1–5 |
| the `rate` 10 command (act seq 2005, tick 1922) | 2006: 6 / 6 | 1921–1925 |
| the first `scan` command (act seq 2007, tick 1928) and its first four parts (seq 2008–2011) | 2012: 5 / 4 | 1926–1931 |
| leg 1's `walkTo` accept (act seq 2065, tick 1980, itself a frame tick) and the first scan's last three parts | 2066: 7 / 7 (`pollMs` 6: tick 1980's own poll) | 1974–1979 |
| no line: the window after leg 1's accept | 2067: 8 / 1 | 1980–1985 |
| a `walkTo` accept, legs 2–20 (each leg's `accepted_seq` + 1) | 2205: 5 / 5, 2341: 6 / 5, 2471: 5 / 5, 2600: 5 / 5, 2726: 6 / 5, 2854: 7 / 6, 2979: 5 / 5, 3105: 6 / 5, 3230: 6 / 5, 3356: 6 / 6, 3481: 5 / 4, 3607: 5 / 4, 3732: 7 / 7, 3859: 5 / 5, 3984: 5 / 4, 4110: 5 / 5, 4235: 5 / 5, 4362: 6 / 6, 4487: 5 / 4 | the six before each frame |
| the final `scan` command (act seq 4613, tick 15784) and its first two parts | 4616: 6 / 5 | 15780–15785 |

So 23 of the session's 24 commands (the `rate` 10, both scans and all 20 `walkTo` accepts) fell in a window whose worst tick read 5–7 ms and whose worst poll read 4–7 ms (4 on five: legs 12, 13, 16 and 20 and the first scan; 5 on twelve; 6 on four; 7 on two), the window's worst tick less its worst poll reading 0 or 1 on all 23; the `rate` 60 command's window (seq 183) read `tickMaxMs` 2 and `maxPollMs` 2. Across those 23 windows `maxStartMs` reads 0 but on the first scan's (1) and `maxActMs` at most 1; over the whole session `maxStartMs` reads 0 on 7470 frames and 1 on 35 (33 of them in windows holding no command: a boundary inside an empty span), never more, and `maxPollMs` reads 3 or more in no window that holds no command (session counts 0:2067 1:5258 2:157 4:5 5:12 6:4 7:2). The command-tick burst is the poll's: in each such window the poll's worst is within the clock of the window's worst tick, and the start, including the `walkTo`'s act line and its encode, never read above 1 ms. Consecutive legs' accepts lie 11266–12349 ms apart on the client's clock (`readings.walk.legs[*].accepted_wallMs`), the leg period, which is the 5–7 ms recurrence through the walk.

Leg 1 is the one window where two polls show: its accept tick 1980 was a frame tick, so seq 2066 reads that tick's own poll at 6 (`pollMs`) while its `maxPollMs` 7 is a poll of one of ticks 1975–1979, which accepted nothing (seq 2066's `tickMs` 7 is tick 1979's body); seq 2067's 8 is a body of ticks 1980–1985 whose polls (ticks 1981–1986) read at most 1, which points at tick 1980, the accept, but does not show it.

**The 15 ms tick.** Seq 11's window covers ticks 1–5. Tick 1 is the init (`M.init`, `PZAgent_Main.lua` L92–L104: the Link's init with its probe file's two writes, one read and the existence checks, `PZAgent_Link.lua` L90–L113; the hello; the inventory's first sight queued; one flush); its flush carried the hello and all 9 `item_added` lines (stamped tick 1, 1450 encoded bytes, under the 1536-byte budget, so the backlog did not spread them) and is `maxLinkMs` 4, the only flush of the window with anything to write. Ticks 2–5 polled no command (the first was taken at tick 117) and stepped neither the watch nor the sense read (both first on tick 6): their named spans read at most 1 (`maxPollMs` 1, `maxStartMs` and `maxActMs` 0). The hello is stamped 649375 and the nine `item_added` lines 649379–649382 (the last six digits of their `wallMs`), so at least 7 ms of tick 1 lie between the hello's emit and the flush's last stamp. The frames point at tick 1 for the 15 ms but do not show it: the init's work before its flush is inside no timer.

**Standing at 10 Hz** after the final scan (the 3363 frames from seq 4671), the windows read `tickMaxMs` 0:76 1:3057 2:225 3:5, all at or under 3, and the samples of the tick before each frame (`tickMs`) mean 0.256021409455843 ms. Through the walk the 2280 frame windows from seq 2068 to 4612 holding no command read `tickMaxMs` 0:13 1:1986 2:276 3:5. The 18 standing 10 Hz frames before the `rate` 60 command (seq 20–173) read 2 to 4, during the watch's first-sight cycle.

**The emit against the sidecar trigger.** Spec § 8 (6): "K2's transport spike runs only if X4 reads the emit above 1 ms mean or 3 ms worst per tick at the budget"; `gates.sidecar` reads it as the mean and max of `cost.linkMs` over the frames whose `linkMs` is above 0. The readings, with their populations:

- **The gate's reading** (`gate_x4.emit_mean_ms`, `emit_worst_ms`, `emit_frames`; ungraded): over the whole session's 778 frames reading `linkMs` above 0, 763 × 1 + 15 × 2 = 793 ms, a mean of **1.019280205655527 ms**, worst **2**; `sidecar_trigger` "fired". 766 of the 778 are 60 Hz frames (751 × 1 + 15 × 2 = 781 ms); the other 12 are 10 Hz frames reading 1. On the 1 ms clock a mean over the readings above 0 is at least 1 by construction, so this reading is the clock's, not the flush's.
- **The 60 Hz window's reading** (`frames.cost` seq 183–2004): every tick wrote a frame, so every one of the 1805 `linkMs` is a flushing tick's flush: mean **0.4326869806094183 ms**, worst **2**, under both the 1 ms and the 3 ms.
- **The flush with the frame's encode, bounded.** The flush plus the tick's unattributed remainder (which holds the frame's encode and no longer the poll), over the 1804 ticks 117–1920: 0:889 1:883 2:31 3:1, mean 0.5254988913525499 ms, worst 3 on one tick (tick 1449); not above either threshold.
- **The link's two operations with the poll.** The poll plus the flush, tick by tick, mean 0.8575388026607539 ms, worst 3 on 13 ticks: also under the 1 ms mean and not above the 3 ms worst, though the spec's trigger names the emit, not the poll.

The controller's **ruling S-18** (the first session) reads the trigger as **not fired**: the gate's "fired" is the quantisation artifact above. This session reads the same: by the gate "fired" (1.019280205655527 over 778 frames, worst 2), on every honest population not fired (the flush 0.4326869806094183 ms mean and 2 worst; the flush with the encode bounded at 0.5254988913525499 and 3; the poll and the flush together 0.8575388026607539 and 3).

**Scan parts.** Each scan's 49 parts went out one a tick (first scan seq 2008–2064, ticks 1928–1976; final scan seq 4614–4670, ticks 15784–15832); the frames over each scan read `maxMapMs` 1 or 2 a window (2 on two windows of the first scan, seq 2040 and 2061) and `maxLinkMs` 0 or 1, so a scan part's step and its flush each read at most 2 ms on the 1 ms clock.

**The two sessions** (the first: `testing/artifacts/x4_link-20261027-171916/GUIDE.md` and its rows #4203–#4207, Lua `c8493a0e`; this: Lua `5d9debb5`; each number at its own guide's section):

| reading | first session (`x4_link-20261027-171916`) | this session |
|---|---|---|
| 60 Hz window | 1806 frames, seq 211–2016, ticks 182–1987 | 1805 frames, seq 183–2004, ticks 117–1921 |
| tick mean at 60 Hz | 1.672203765227021 ms (p50 2, p90 2, p99 3, max 9) | 1.2614958448753462 ms (p50 1, p90 2, p99 3, max 4) |
| sense read (`senseMs`) | 0.7115171650055371 | 0.2692520775623269 |
| map watch (`mapMs`) | 0.3449612403100775 | 0.03434903047091413 |
| flush (`linkMs`) | 0.2691029900332226, worst 2 | 0.4326869806094183, worst 2 |
| skill tick (`actMs`) | 0.0005537098560354374 | 0.004986149584487534 |
| poll (`pollMs`) | not timed (inside the remainder) | 0.42437673130193904, worst 2 |
| start (`startMs`) | not timed | 0.002770083102493075 |
| unattributed remainder | 0.3462603878116344 (the poll, the encode, the timers) | 0.09257206208425721 (the encode, the timers) |
| the emit with its encode, bounded | 0.6155124653739612, worst 3 but tick 182's 8 | 0.5254988913525499, worst 3 |
| the gate's emit reading | 1.0576131687242798 over 486, worst 3, "fired" | 1.019280205655527 over 778, worst 2, "fired" |
| the `rate` 60 command's tick | 9 ms, 7 unattributed (tick 182) | 4 ms, all named: poll 2, start 1, flush 1 (tick 117) |
| worst tick | 19 (seq 43, one of ticks 1–4) | 15 (seq 11, ticks 1–5) |
| the first window's lines | hello, 9 `item_added`, 32 watch deltas | hello, 9 `item_added` |
| `over5` over the session | 31 in 30 windows over 600.066 s | 25 in 25 windows over 600.013 s |
| command windows | all 24 at 5–9 ms, cause unattributed | 23 of 24 at 5–7 ms (the `rate` 60's at 2), the poll's worst 4–7; 8 in the window after leg 1's accept |
| other windows of 5 ms or more | 6 (two first-sight watch windows, four lone) | none |
| standing at 10 Hz after the final scan | `tickMaxMs` 1:1471 2:1727 3:138 4:13 5:1 (one 0), `tickMs` mean 0.588779468815279 | `tickMaxMs` 0:76 1:3057 2:225 3:5, `tickMs` mean 0.256021409455843 |
| legs (ack → first move) | 128–181 ms, p50 146, p90 165 | 126–195 ms, p50 147, p90 178 |
| kept map | 6 walls, 3 doors, 13 windows, 21 containers, ratio 1.0 each | the same |
| final scan's window | shifted; 870 shared squares, 91 outside the kept map | the same windows; 870 and 91 |
| door events | 1 (tick 2124, before the agent entered the door square at tick 2136) | 1 (tick 2148, after the agent entered at tick 2070) |
| first-sight watch | 169 deltas on ticks 2–23 | 169 deltas on ticks 6–132, every sixth |
| wall; memory at the gate, ready, after | 702.2 s; 13.51, 2.31, 15.85 GB | 688.2 s; 12.63, 2.67, 16.66 GB |

The pass cut the sense read by 0.4422650874432102 ms a tick and the watch by 0.3106122098391634, the per-tick work the first session's ruling S-19 named; the flush rose by 0.16358399057619571 on an `L.flush` whose code changed only by a kind lookup per backlog line (`4be64f1f`), with eight more cost fields and two more `me` fields in each frame, and the frames do not say whether the host or the frame's size moved it; the poll, untimed in the first session, is now the largest named span with the flush.

## 2. The map

**The first scan** (`readings.scan`): `scanId` 1, `parts` 49, `got` 49, `complete` true, `squares` 961, in 0.833 s (`seconds`); `mapMs` on its 9 frames 0, 1, 1, 1, 0, 0, 0, 0, 0 (a frame tick's own scan step, one tick in six; the other steps show in `maxMapMs`). From the settled start (10997.5, 9699.5) (`readings.walk.start`) its squares span x 10982–11012, y 9684–9714 (`state.log` seq 2008–2064), the first session's window.

**The watch before the walk.** The watch sent its 13 × 13 ring as 169 first-sight `delta` lines on the 22 watch ticks 6–132 (seq 12–215, 8 a step and 1 on the last; x 10991–11003, y 9693–9705), each square inside the first scan's window.

**The watch during the walk** (`readings.walk.map_deltas` **1**, on leg 1; the other 19 legs' `map_deltas` 0). The walk's one delta, seq 2096 (tick 2142, a watch tick), carried square (10995, 9701, 0) with its door `[true, false, false]` (`open`, `locked`, `barricaded`), against `[false, true, false]` in the first-sight delta (seq 133) and the first scan (seq 2039); the `door` event at seq 2097 (tick 2148, the next frame tick's events) read the door at (10995, 9701, 0) `open` true. Leg 1's frames entered that square at seq 2082 (tick 2070, y 9701.078125), so the delta came 72 ticks and the event 78 ticks (1301 ms of the client's clock, `wallMs` 1793149684153 to 1793149685454) after the agent stood in the doorway, where the first session's event (Sense's 81-square door walk) came at tick 2124, 12 ticks before its frames entered the square at tick 2136. When the door opened is not read; the event is now the watch's, within its cycle of 132 ticks plus the drain. One delta and no more: the legs' squares lay inside the first scan's window, and the watch reads a square whole only when its fingerprint changes (`PZAgent_Map.lua` L1–L15), so only the door's change was new.

**The walk's ground.** As in the first session, each leg was sent to its own start's x ± 6 at y 9699.5 (`readings.walk.legs[*].target`), and every leg's frames (positions merged across delta frames) reach y 9695.5 and y 9701.5 and x 10993.5 or less, all within x 10993.208984375–11003.0478515625: the pathfinder's loop through the door at (10995, 9701), the first session's route.

**The final scan and the kept map** (`readings.final_scan`): settled (`settled` true) at (10995.5, 9700.154296875), the kept map snapshotted before the scan (`kept_squares` 961, the kept map's size), then `scanId` 2, 49 of 49 parts, 961 squares in 0.851 s (`mapMs` 1, 1, 1, 0, 1, 1, 1, 0, 0). Its window, x 10980–11010 and y 9685–9715 (seq 4614–4670), is shifted from the first scan's exactly as in the first session: the two share 870 squares, and the 91 final squares at x 10980–10981 and y 9715 lie outside the kept map (no line of the session sent them before the final scan). None of the 91 carries a wall, a door, a window or a container, so each kind's `absent` reads 0; and the 870 shared squares read identical in the kept map (the first-sight deltas, the first scan and the door delta, the last line for a square winning) and the final scan in every field but `light` (`state.log`, compared square by square). The four kinds (`readings.final_scan.kept`):

| kind | kept | total | absent | seen | ratio |
|---|---|---|---|---|---|
| walls (`solid` true) | 6 | 6 | 0 | 6 | 1.0 |
| doors | 3 | 3 | 0 | 3 | 1.0 |
| windows | 13 | 13 | 0 | 13 | 1.0 |
| containers (by square and type) | 21 | 21 | 0 | 21 | 1.0 |

So the kept map held every one of the final scan's 43 walls, doors, windows and containers, the door's opening included, the first session's reading again; `absent` is coverage by kind, and the square coverage was 870 of 961.

## 3. The legs

Each leg's `accepted_seq` is its `walkTo` accepted act line, its first move the first frame after it whose position moved more than 0.01 tiles, its latency `first_move.wallMs` − `accepted_wallMs` on the client's clock (`readings.walk.legs[*]`); every leg was `settled` true before its send, its `at_accept` equal to its start:

| leg | start x | target x | `accepted_seq` | `first_move.seq` | latency (ms) | end | `result.d` |
|---|---|---|---|---|---|---|---|
| 1 | 10997.5 | 11003.5 | 2065 | 2068 | 195 | done | 0.9833203675875426 |
| 2 | 11003.0478515625 | 10997.0478515625 | 2204 | 2206 | 147 | done | 0.9836122494413012 |
| 3 | 10996.58203125 | 11002.58203125 | 2340 | 2342 | 146 | done | 0.9934674515098483 |
| 4 | 11002.3505859375 | 10996.3505859375 | 2470 | 2472 | 178 | done | 0.9910396634660937 |
| 5 | 10995.943359375 | 11001.943359375 | 2599 | 2601 | 146 | done | 0.9966259301407455 |
| 6 | 11001.5 | 10995.5 | 2725 | 2727 | 162 | done | 1 |
| 7 | 10995.5 | 11001.5 | 2853 | 2855 | 129 | done | 0.96484375 |
| 8 | 11001.5 | 10995.5 | 2978 | 2980 | 162 | done | 1 |
| 9 | 10995.5 | 11001.5 | 3104 | 3106 | 163 | done | 0.96484375 |
| 10 | 11001.5 | 10995.5 | 3229 | 3231 | 162 | done | 1 |
| 11 | 10995.5 | 11001.5 | 3355 | 3357 | 147 | done | 0.96484375 |
| 12 | 11001.5 | 10995.5 | 3480 | 3482 | 178 | done | 1 |
| 13 | 10995.5 | 11001.5 | 3606 | 3608 | 160 | done | 0.96484375 |
| 14 | 11001.5 | 10995.5 | 3731 | 3733 | 126 | done | 1 |
| 15 | 10995.5 | 11001.5 | 3858 | 3860 | 131 | done | 0.96484375 |
| 16 | 11001.5 | 10995.5 | 3983 | 3985 | 163 | done | 1 |
| 17 | 10995.5 | 11001.5 | 4109 | 4111 | 144 | done | 0.96484375 |
| 18 | 11001.5 | 10995.5 | 4234 | 4236 | 146 | done | 1 |
| 19 | 10995.5 | 11001.5 | 4361 | 4363 | 145 | done | 0.96484375 |
| 20 | 11001.5 | 10995.5 | 4486 | 4488 | 130 | done | 1 |

All 20 legs moved and ended `done` with an empty `reason`; none lacks a first move, so no leg counts +inf in the gate. Over the 20 latencies, 126–195 ms: nearest-rank p50 **147**, p90 **178** (`gate_x4.gates.cmd_move_p90.value`), max **195**; mean 153. On legs 2–20 the first move is the second frame after the accept (`first_move.seq` = `accepted_seq` + 2); on leg 1, whose accept tick 1980 was itself a frame tick (the frame seq 2066 written after the act line on the same tick), it is the third (seq 2068), the reason its 195 ms is the session's longest. Against the first session (128–181, p50 146, p90 165, every first move the second frame): the same within the frame period of about 100 ms.

## 4. What the frames cannot say, the host, corrections

**What the frames cannot say.**

- **Which tick of a 10 Hz window was slow, and what a slow poll met.** The new maxima name the phase, not the tick: a window's worst poll is one of its six ticks, and only where the accept tick was the frame tick (leg 1) is the accept's own poll read (6 ms). The poll's open, read, close, decode and, on a command's tick, the `ack.txt` write are one span; which of them costs 4–7 ms on a command's window, and what leg 1's earlier 7 ms poll met (it accepted nothing: the driver's replace of `cmd.txt` landing during the read is one reading, the frames do not show it), is not read.
- **The 15 ms tick's owner.** One of ticks 1–5; the named spans of ticks 2–5 read at most 1 ms and tick 1's work before its flush is untimed, so the frames point at the init without showing it.
- **Why the flush rose.** 0.4326869806094183 ms against 0.2691029900332226 on an `L.flush` changed only by that lookup (`git diff c8493a0e 5d9debb5` on `PZAgent_Link.lua`; `L.poll` unchanged), with longer frames and a different host state (§ 0's memory); two sessions do not separate the two.
- **The poll's cost against the probe's bench.** The probe's warm-loop bench read open + close at 62 µs and open + write + close at 138 µs (`testing/artifacts/p22_probe-20261027-032502/GUIDE.md` § 2); the live loop reads the poll at 0.42437673130193904 ms and the flush at 0.4326869806094183 a tick, one call each inside the game's frame; the gap is not attributed.
- **Sub-millisecond spans.** Every `cost` field is an integer on the 1 ms clock: a single reading is a bound, a mean over many is the clock's mean of the measured spans, and the gate's mean over the readings above 0 is at least 1 by construction.
- **The emit with its encode.** `linkMs` is the flush alone; the frame's encode is inside the unattributed remainder with the overflow check and the timers, so the emit is bounded (§ 1), not measured.
- **The two clocks.** A line's `wallMs` is the client's clock in epoch milliseconds; the driver's `*_wall` keys are this process's clock in seconds; nothing here sets one against the other, and every latency and span above is a difference within one clock.
- **The kept map's square coverage, and the door's opening.** The ratios are fidelity over the 43 features on the 870 squares both scans covered; the 91 squares only the final scan sent hold none. The door delta and event are read, the opening itself is not, so the event's lag behind the opening is bounded only by the agent's entering the square.

**The host.** One Windows host; free memory 12.63 GB at the gate, 2.67 GB at ready with the server and the `-debug` client up, 16.66 GB after teardown (`memory`); the controller's pre-boot read was 12.95 GB at 21:05:36 (ledger). Every millisecond above is this host's.

**The epoch-ms leaves** (wildcard): `*wallMs`, `*_wall`, `wall_*` and `epoch_ms_*` anywhere in `x4_link_2.json` (`frames.cost[*].wallMs`, `readings.hello.first_frame.wallMs`, `readings.walk.legs[*].accepted_wallMs`, `accepted_wall`, `first_move.wallMs`, `end.ended_wall`, `readings.*.act.ended_wall`, `rate_on.ended_wall`, `rate_off.ended_wall`, `server_launch_wall`, `server_started_wall`, `session_ready_wall`, `wall_seconds`, `steps[*].wall_before`, `epoch_ms_before` and the like), the `wallMs` of every line of `state.log`, and `took`, `timeline`, `phase_walls`, `client_seen`, `memory[*].wall` and `memory_wait[*].wall` are this host's clocks, cited only as a difference within this run (a latency, a span), never as a reading.

**Corrections to the controller's readings** (`.superpowers/sdd/2026-10-27-plan-22-agent-base/progress.md`, the line "X4 fix pass run x4_link_2-20261027-210612" and ruling S-34; `x4fix-writeup-amendments.md` and its dispatch note):

1. The amendments' "launched by the controller at 2026-10-27 17:19:14 (pid 357548), detached, HEAD `95596a91`" is the first session's; this boot ran on HEAD `5d9debb5` (`preboot.commit`), its memory wait at 21:06:12.940 local (`memory_wait[0].wall`), and the ledger's launch line names 21:06:11 and pid 364148, which the artifact does not carry (`server_pid` 368584 is the server's).
2. The amendments' expected `hello.modVersion` `1.0`: it is `readings.hello.hello.mod`, and it reads `1.1` (PZAgent 1.1 since `b8630daf`); `proto` `PZA/1` as expected.
3. "the pass's commits 1d2e2d24..5d9debb5 on the fix wave's d22503e6": against the first session the Lua also carries the fix wave's Lane L commits (`git log 95596a91..5d9debb5 -- testing/PZAgent`), `4dbdb6cf`'s nearest zombie off the last frame among them, so the comparison is of `c8493a0e` against `5d9debb5`, not of the pass alone; and the driver's docstring names ten of the pass's Lua commits, not `5d9debb5`, which the boot ran.
4. "maxStartMs 0 everywhere": it reads 0 on 7470 frames and 1 on 35 (seq 183, the `rate` 60 command's, and seq 2012, the first scan's, among them; 33 in windows holding no command), never more.
5. "the 5–8 ms ticks at the commands' accepts now read as maxPollMs 5–7 on the accept tick (seqs 2066/2067, 2854, 3732, 4616, …)": a command window's `maxPollMs` is its worst poll over its six ticks, which is the accept tick's own only where the accept tick is the frame tick (leg 1: seq 2066's `pollMs` 6); the 23 command windows read 4–7 (4 on five), the `rate` 60 command's 2; seq 2067 reads `maxPollMs` 1, its `tickMaxMs` 8 being a body of ticks 1980–1985 (the accept tick's, by inference, its poll falling in seq 2066's window); and leg 1's window holds a second slow poll, 7 ms on one of ticks 1975–1979, before the accept.
6. "the burst is the poll of a non-empty `cmd.txt` and its decode": every tick from tick 117 on polls a non-empty `cmd.txt` and decodes its line (the file keeps the last command; `L.poll` returns nil for an old seq only after the decode), and that poll reads 0.42437673130193904 ms a tick at 60 Hz; what a command's tick adds is a `cmd.txt` the driver has just replaced and the `ack.txt` write, both inside `pollMs`; the frames do not split the read, the decode and the write.
7. "the ack write (M10, bd915b62) is in linkMs or pollMs": in `pollMs` (`L.poll` L253–L272 calls `writeAll` for `ack.txt`; Main times `L.poll` between `tp` and `t0`, L190–L192).
8. "The worst tick 15 ms is seq 11 (the init window: maxLinkMs 4, maxSenseMs 1, maxMapMs 1)": the window is ticks 1–5, its lines the hello and 9 `item_added` (no map delta); `maxLinkMs` 4 is tick 1's init flush (ticks 2–5 had nothing to flush), `maxSenseMs` 1 and `maxMapMs` 1 are tick 6's first frame read and first watch step, and `maxPollMs` reads 1; the 15 ms is not attributed by any field.
9. The dispatch note's "the first session's 32 + 8 lines": its first window held the hello, 9 `item_added` (seq 2–10) and 32 watch deltas (seq 11–42); this session's holds the hello and the same 9 `item_added`, and the watch's first deltas came after the first frame.
10. "the two file operations a tick (the poll and the flush) about 0.86 ms: the file transport's floor at 60 Hz, the rest of the base about 0.3 ms": the poll and the flush read 0.8575388026607539 ms a tick (tick by tick), the poll's decode of the command line included, so it is the link's two operations, not file work alone; the rest is 0.4044321329639888 ms, 0.3113573407202216 of it named (sense, watch, skill tick, start) and 0.09257206208425721 unattributed.
11. The ledger's "map_kept 1.0 on all four kinds (6/3/13/21, absent 0, 961 of 961)": 961 is `kept_squares`, the kept map's size, and `final_squares`; the final scan's window is shifted as in the first session and 91 of its squares were outside the kept map, so the square coverage is 870 of 961 and the ratios are fidelity over the 43 features.
12. Ruling S-34's "the remaining 0.26 over the gate is the file transport's two operations a tick, which no Lua edit removes": the mean exceeds the gate by 0.2614958448753462 ms, and the poll alone reads 0.42437673130193904 a tick, so a poll made less often (one of the ruling's own Plan 23 options, a Lua edit) reaches the excess by the frames' arithmetic; what the frames read is that the excess lies within the link's two operations, not that no Lua edit removes it.
13. Confirmed as the controller read them: the 60 Hz window's means and histograms (sense, map, link, poll, act, start, `tickMs`), the sum 1.168421052631579, the watch every sixth tick (60 of the 62 `mapMs` ones on watch ticks), one `door` event and one walk delta with the legs looping through the door, `zombiesSeen` and `zombiesListed` 0 throughout, the legs' 126–195 ms with p90 178, all done, and the memory 12.63 / 2.67 / 16.66 GB.
14. The amendments' "each a mean since the last frame" for the cost group is the first session's schema wording; the Lua writes single-tick spans and maxima (How to read it), as the fix wave's `88296b4c` now says.

## 5. The grade

`gate_x4` (`x4_grade.txt`, verbatim values; the same object is `gate_x4` in `x4_link_2.json`):

| gate | ok | value | threshold | n |
|---|---|---|---|---|
| `tick_mean_at60` | **false** | 1.2614958448753462 | mean < 1.0 ms over >= 1620 frames | 1805 |
| `worst_tick` | **false** | `tickMaxMs` 15, `over5` 25, `span_s` 600.013 | max tickMaxMs <= 3.0 ms and 0 over5, over >= 600.0 s | 7505 |
| `gaps` | true | 0 | == 0 | 1 |
| `lua_errors` | true | 0 | == 0 | 1 |
| `parks` | true | 0 | == 0 | 1 |
| `cmd_move_p90` | true | 178 | p90 < 500.0 ms over >= 20 legs | 20 |
| `map_kept` | true | walls 1.0, doors 1.0, windows 1.0, containers 1.0 | each of walls/doors/windows/containers ratio >= 0.99 | 43 |

**Verdict: NO-GO** (`verdict`), on `tick_mean_at60` and `worst_tick`, as in the first session. Beside it, ungraded: `sidecar_trigger` "fired", `emit_mean_ms` 1.019280205655527, `emit_worst_ms` 2, `emit_frames` 778, `sidecar_thresholds` `{mean_ms 1.0, worst_ms 3.0}`. Re-running `x4_grade.py` on this folder's `x4_link_2.json` reproduces `x4_grade.txt` byte for byte against the controller's print of the run copy (`.superpowers/sdd/2026-10-27-plan-22-agent-base/x4fix-grade.txt`, `cmp` equal).

**The sidecar trigger, both ways (ruling S-18).** By the gate, "fired" (the mean over the 778 frames reading above 0, at least 1 on the 1 ms clock by construction), which by § 8 (6) would run K2's transport spike. By ruling S-18's reading, **not fired**: over the 60 Hz window the flush reads 0.4326869806094183 ms mean and 2 ms worst, the flush with the encode bounded at 0.5254988913525499 and 3, under § 8 (6)'s 1 ms mean and not above its 3 ms worst; so the spike does not run on the spec's own trigger, and `gate_x4` stays frozen.

**What follows.** The controller's **ruling S-34**: this pass's verdict stands as the plan's last X4 reading (the plan allows one fix pass, ruling S-19); the mean fell 0.4107079203516748 ms from the first session's, and the choice between a cheaper poll (made every other tick or on a cheaper check) and the sidecar's byte channel is Plan 23's. This guide's reading: the failed `tick_mean_at60` lies within the link's two operations a tick (the poll 0.42437673130193904 and the flush 0.4326869806094183 of the 1.2614958448753462 mean), the base's own per-tick work being 0.4044321329639888; the failed `worst_tick` is the init tick (15 ms) and the commands' polls (5–7 ms windows, 8 once), while standing and walking windows holding no command read at most 3 ms.

## Do not cite from this file

| Key | Value in the file | Why not |
|---|---|---|
| everything measured here, as a population | — | One boot, one fixture, one character, one host; with the first session, `n = 2` on the legs and the kept map. |
| `gate_x4.sidecar_trigger` | "fired" | A mean over the 1 ms clock's readings above 0, at least 1 by construction; ruling S-18 reads the trigger as not fired (§ 1, § 5). |
| `gate_x4.emit_mean_ms` as the emit per flushing tick | 1.019280205655527 | The subset reading above 0; the flush per flushing tick is the 60 Hz window's 0.4326869806094183 mean over 1805 flushes. |
| `frames.cost[*].cost.linkMs` and `cost.tickMs` at 10 Hz as a frame tick's cost | 0–2 | They sample the tick before each frame tick, which reads and writes no frame. |
| any single `cost.*Ms` reading | integers 0–15 | The 1 ms clock: a reading is a bound, never a value; a mean over many is cited, or a worst, max or nearest-rank percentile, or a count at a threshold, each as a ±1 ms bound. |
| `frames.cost[*].cost.maxPollMs` as the accept tick's poll | 4–7 | A window's worst over its six ticks; the accept tick's own poll is read only where it is the frame tick (leg 1, seq 2066's `pollMs` 6). |
| `readings.final_scan.kept_squares` and `final_squares` as square coverage | 961 | The kept map's size and the final scan's; 91 of the final squares were outside the kept map (870 shared). |
| `readings.final_scan.kept.*.absent` as square coverage | 0 | Per kind: 91 of the 961 final squares were not in the kept map. |
| `readings.walk.legs[*].target` as the path walked | x0 ± 6 at y 9699.5 | Every leg looped, reaching y 9695.5 and 9701.5 within x 10993.208984375–11003.0478515625 (§ 2). |
| `readings.walk.legs[*]` latency finer than a frame | 126–195 | Frame-quantised at about 100 ms (the first move is the second frame after the accept, the third on leg 1). |
| `readings.scan.mapMs`, `readings.final_scan.scan.mapMs` as the scan's cost | 0–1 | A frame tick's own step, one tick in six. |
| `readings.server.stats.ack.mult` | 4.805104732513428 | getMultiplier, not the true multiplier (#3762). |
| every `reason` and error text | empty | Empty in this run; a text is the driver's or the Lua's message, not a reading. |
| `constants`, `preboot`, `profile`, `fixture`, `argv`, `memory`, `memory_wait`, `world_changes`, `steps`, `verify` | the driver's tables | Written before or around the run, or the server reading's raw steps; not readings. |

## Corrections

- 2026-10-27, the controller after the write-up's review (review-x4fix-writeup.md Minor 1): the "rest of the base" 0.4044321329639888 ms (§ 1 and § 4) is the 1805-frame mean minus the poll's and flush's 1805-frame means, two populations: the named parts 0.3113573407202216 plus the unattributed 0.09257206208425721 sum to 0.4039, and the tick-by-tick poll + flush 0.8575388026607539 plus 0.4044 gives 1.2620, not the 1.2614958448753462 mean; read the rest as about 0.40 ms. No register row carries the number.
