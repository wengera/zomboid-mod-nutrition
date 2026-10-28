# `x4_link_3-20261028-101928` reading guide

**`x4_link_3-20261028-101928/x4_link_3.json`** (with `state.log` and `x4_grade.txt`) — produced by `testing/agent/drivers/x4_link_3.py` at `driver_commit` `468da796` (Plan 23 Task 16a), unedited since (its last commit at HEAD is `468da796`), which imports `testing/agent/drivers/_dlib.py` and `testing/experiments/xlib.py` (`preboot.xlib_commit` `45c49217`); on HEAD `278ee76d` at the boot (`preboot.commit`; `preboot.harness_lua_commit` `edcaf2e6`, `preboot.harness_lua_dirty` false; `preboot.harness_py_commit` `6f834a38`); the agent mod `testing/PZAgent/PZAgent` loaded by path from the tree (`profile.sources.PZAgent`; `preboot.agent_commit` `278ee76d`, the last commit under `testing/agent` or `testing/PZAgent`; `preboot.driver_checks.agent_lua_dirty`, `agent_base_dirty` and `driver_dirty` false), so the Lua under test is `testing/PZAgent` at `e3e68793` (Plan 23 fix wave L, its last commit; `git diff --stat e3e68793 278ee76d -- testing/PZAgent` is empty), PZAgent 1.2 (`readings.hello.hello.mod` `1.2`, `proto` `PZA/1`, `caps` now eleven with `sleep`). Fixture `agent0` (`fixture.provision_run` `prov-20261026-102802`, `fixture.build` `42.21.0`; `hello.build` `42.21`; `build` `42.21.0`); profile `testing/profiles/agent-nozombies.toml` (`profile.name` `agent-nozombies`; PZTestKit + PZAgent, `profile.sandbox.Zombies` 6, user `admin` on a `-debug` client, a 90-minute day). Graded by `testing/agent/base/gates.py` `gate_x4` through `testing/agent/drivers/x4_grade.py`, both unchanged since the first X4 session's boot at `95596a91` (`git diff --stat 95596a91 HEAD` on the two files is empty).

**Plan 23's X4 session, "the link" a third time**: the third X4 session (spec § 10's X4-3, ruling P23-C), on the same schedule as the first two (`testing/artifacts/x4_link-20261027-171916/GUIDE.md` and `testing/artifacts/x4_link_2-20261027-210612/GUIDE.md`) and graded by the same frozen `gate_x4`. The agent stood still at 60 Hz for 30 s, scanned r = 15, walked twenty 6-tile `walkTo` legs, scanned again and stood until the frames' cost rows spanned 600 s. The driver's docstring restates every phase, reading and key.

**What changed since the fix pass's session.** The Lua under test differs from the fix pass's `5d9debb5` by Plan 23's commits (`git log 5d9debb5..e3e68793 -- testing/PZAgent`): `ed519ef5` the poll paced to every third tick (`L.POLL_EVERY = 3`, P23-4); `0470b1d4` PZA/1.2 (the square record's `blockN`, `blockW`, `edgeN`, `edgeW`, `me.hour`, the `sleep` action, `interact`'s `maxWeight`); `3240565b` the square's four edges read in the scan and in the watch's fingerprint (P23-K); `a7544ddc` the loot's weight cap and `me.hour` from `getTimeOfDay`; `e5f5409b` and `baad765a` the `sleep` skill; `08a4e103` `item_added`'s `use`; `a8a83676` a loot fix; `e3e68793` a sleep's wake on any end and the fingerprint taking the watch's coordinates. The X4 session sends no `sleep`, `interact` or loot, so of these the paced poll, the edges, `me.hour` and `item_added`'s `use` are what its frames can read. The driver `x4_link_3.py` is `x4_link_2.py` with only its docstring head and `KEY`, `DRIVER` and `ARTIFACT` changed (`diff testing/agent/drivers/x4_link_2.py testing/agent/drivers/x4_link_3.py`).

## 0. The run

- **Wall.** 685.3 s (`wall_seconds`; against `constants.BUDGET_S` 840, counted from the memory gate, the boot included). The memory gate waited 28 reads, from 11.97 GB to the 12.23 GB that passed it (`memory_wait`, 30 min of polling at the 12 GB floor); server started at 37.3 s (`server_started_wall` 37.335), the session ready at 74.7 s (`session_ready_wall` 74.673; `client_seen[0].ready` 36.9 s after the client's launch), both `verify` pings ok, client quit rc 0 and server stopped rc 0 with 0 errors (`timeline`). Phases (`phase_walls`, seconds from the gate): `hello` 75.188–75.196, `rate60` 75.199–105.368, `scan` 105.391–106.222, `walk` 106.254–336.424, `final_scan` 336.479–337.766, `worst_window` 337.816–673.735, `server` 673.835–675.101.
- **Hello.** `readings.hello`: `ok` true, `proto` `PZA/1`; the hello line (`state.log` seq 1, tick 1): `mod` `1.2`, `build` `42.21`, `user` `admin`, `rate` 10, `mode` `append`, `caps` the eleven skill types `attack`, `consume`, `drop`, `equip`, `interact`, `rate`, `scan`, `sleep`, `steer`, `stop`, `walkTo`; `first_frame.seq` 11.
- **Pipe health.** `frames.gaps` 0 (`gap_list` `[]`), `frames.bad` 0, `frames.lua_errors` 0 (`lua_error_msgs` `[]`), `frames.parks` 0, `logs.clients.admin` `[]`, `admin_lua_error` false, `server_error_count` 0 (`server_errors` `[]`), `bus_dead` null; every frame's `cost.dropped` reads 0 (`frames.cost`, 7506 rows).
- **Stops.** `finished` true; `phase_errors` `{}`; `notes` `[]`; `verdicts` `{}`; the artifact carries no `abort`, `error` or `budget_stop` key; `readings.worst_window.stopped` `span` (`span_s` 600.089, `frames` 7506).
- **Frames.** `state.log` holds 8051 lines and line *n* is seq *n* on every line (checked line by line, each line decoded by `testing/agent/base/pza1.py`): 1 `hello`, 7524 `frame`, 268 `map` (98 `full`, 49 for each of the two scans; 170 `delta`), 248 `act` (2 `rate` done, 2 `scan` done, 20 `walkTo` accepted, 204 `walkTo` progress, 20 `walkTo` done) and 10 `event` (9 `item_added` at seq 2–10, the inventory's first sight, 8 stamped tick 1 and seq 10 tick 2; and 1 `door` at seq 2079). The nine `item_added` lines' new `use` field reads `other` on all nine (an ID card, a key ring, a belt and six garments: `Base.IDcard`, `Base.Vest_DefaultTEXTURE_TINT`, `Base.KeyRing`, `Base.Skirt_Mini`, `Base.Socks_Ankle`, `Base.Shoes_Random`, `Base.Hat_BaseballCap`, `Base.Tshirt_PoloStripedTINT`, `Base.Belt2`), so the session reads no food, water, weapon or bandage use. No `scan_dropped`, `overflow` or `lua_error` event. The driver read 7506 frames (`frames.n`, seq 11–8033), each `cost` row equal to its line's once each delta frame is merged with `merge_delta` over the frame before (534 delta frames elide an unchanged `cost` as `true`); the 18 frames seq 8034–8051 came after its last read. Of the 7505 consecutive frame pairs the driver read, 1806 are one tick apart (the 60 Hz window's 1805 and seq 2001 → 2003, tick 1901 → 1902, the `rate` 10 command's own frame tick) and 5699 six ticks apart; no pair is three or five apart, the `rate` commands having both been taken on 10 Hz frame ticks (§ 1).
- **Zombies.** `me.zombiesSeen` and `me.zombiesListed` read 0 and 0 on all 7524 frames: fixture `agent0` holds none.
- **Memory.** Free 12.23 GB at the preboot read (the gate's last `memory_wait` read), 2.18 GB at ready, 16.2 GB after teardown (`memory`).
- **The server reading.** `readings.server.stats` (`stats.all admin` at 673.835 s) and `readings.server.players` (`["admin"]`); nothing below rests on them.

Files, byte-identical (amendment 1 of the write-up; the controller's copy of the run folder's files, its `x4_grade.txt` re-made below):

| File | Source | Bytes | sha256 |
|---|---|---|---|
| `x4_link_3.json` | the run's `x4_link_3.json`; CRLF endings, 175836 line breaks, no final newline | 3242830 | `95d837277614f999d1add45e0f35ba6aac6ce5e9039ad9bdfdc6ad3ae83cfce7` |
| `state.log` | the run's `clients/admin/Lua/pzagent/admin/state.log`; LF endings, 8051 lines | 1979231 | `e2b10a4b05a44ef2354f499cafc9f9c2fc418985a6790ae25e5b6c68634f73bb` |
| `x4_grade.txt` | `python testing/agent/drivers/x4_grade.py` on this folder's `x4_link_3.json`, stdout (exit 1); the write-up's re-run is byte-identical (`cmp` equal); CRLF endings, 74 lines | 1399 | `f41c1d15460477e78888f9eb585ad083eeb599e8d31a3b0ec0fd34bd0eedc914` |

`state.log` is the only evidence of the lines between the frames (the acts, the map parts and deltas, the events) and of each frame's position; the hashes are of the working-tree bytes as written (re-hash a checkout's blob with `git show <commit>:<path> | sha256sum`). The driver's stdout, the client console, `server-stdout.log` and the logs under `server/` and `clients/` are per-machine and untracked, and nothing below rests on them.

## How to read it

**The cost group** (`frames.cost[*].cost`, and the frame line's last array, 16 fields) is written by `PZAgent_Main.lua` (its header L14–L22 and `body` L180–L227 at `e3e68793`) on the 1 ms clock (`PZA.now`, `getTimestampMs`, ruling P22-4), with the fix pass's semantics unchanged: for a frame on tick T1 whose frame before was on tick T0, `pollMs`, `startMs`, `actMs`, `senseMs`, `mapMs` are **this** tick T1's spans; `tickMs` and `linkMs` the **previous** tick T1 − 1's whole body and flush; `tickMaxMs` and `over5` the worst body and the bodies of 5 ms or more over ticks T0 … T1 − 1; `maxPollMs`, `maxStartMs`, `maxActMs`, `maxSenseMs`, `maxMapMs` each phase's worst over ticks T0 + 1 … T1, and `maxLinkMs` the worst flush over ticks T0 … T1 − 1; `dropped` the Link's dropped lines (`testing/artifacts/x4_link_2-20261027-210612/GUIDE.md`, How to read it).

**The paced poll** (`PZAgent_Link.lua` L253–L276 at `e3e68793`): `L.poll(tick)` returns at once, opening nothing, unless `tick % L.POLL_EVERY == 0` (`POLL_EVERY` 3, L255–L257); on a polling tick it opens `cmd.txt`, reads its first non-empty line, closes it and decodes the line, and on a new seq writes `ack.txt` (L272), all inside `pollMs` (Main's stamps `tp` and `t0` around it, `PZAgent_Main.lua` L190–L192). So a command is taken only on a tick divisible by 3. The 10 Hz frame ticks (`tick % 6 == 0`) and the watch's ticks (`MP.watchDue`, the same `tick % 6 == 0`, `PZAgent_Map.lua` L345) are all polling ticks; at 10 Hz each frame window T0 … T1 holds two polling ticks, T0 + 3 and the frame tick T1 itself, so a window's `maxPollMs` is the larger of the two, and the frame tick's is the frame's own `pollMs`. That is why every command's accept tick's poll is read in this session (§ 1), where in the fix pass's a window's six polls hid the accept tick's unless it was the frame tick.

**The edges** (`PZAgent_Map.lua` L16–L22 and L85–L131 at `e3e68793`): a square record's `blockN` and `blockW` are its `isBlockedTo` its north (x, y − 1) and west (x − 1, y) neighbour, `edgeN` and `edgeW` its `isSomethingTo` the same neighbours, each through `PZA.call`; an unloaded neighbour leaves its side's two nil and names `neighbourN` or `neighbourW` in the part's `missing` list. The fingerprint (`edgeMark`, L151–L163) reads the same four calls, so every watched square now costs two neighbour lookups and four member calls a step beyond the fix pass's fingerprint. What the engine reads behind the two calls is the jar note `docs/superpowers/specs/2026-10-28-plan-23-jar-reads.md` § 1 (Task 3's rows).

**`me.hour`** (`PZAgent_Sense.lua` L106): `getGameTime():getTimeOfDay()` read on the frame's sense read, through `PZA.call`.

**Quantisation.** As in the fix pass's guide: a span read as the difference of two integer-millisecond stamps reads 1 when a millisecond boundary falls inside it; a mean over many spans estimates the span, one reading is a bound (*r* − 1 to *r* + 1 ms), and the mean over the readings above 0 is at least 1 by construction.

**The leg latency** (`gate_x4`'s `cmd_move_p90`, `gates.leg_move_ms`): a leg's `first_move.wallMs` minus its `accepted_wallMs`, both the client's clock: the accept act line's stamp to the first frame after it whose position moved more than `MOVE_EPS_TILES` 0.01 tiles; nearest-rank percentiles (`gates.pct`). The paced poll's wait before the accept (up to two ticks after the driver's write) is not in it.

## 1. The tick

**The 60 Hz window** (`readings.rate60`): `frames` 1806, `first_seq` 147 (tick 96) to `last_seq` 2001 (tick 1901), every consecutive pair one tick apart, `span_s` 30.074 (`seconds` 30.046). `tickMs` (each frame's `cost.tickMs`, the bodies of ticks 95–1900; `readings.rate60.tickMs` equal to `frames.cost`'s, element by element) reads mean **1.0121816168327795 ms** (1828 / 1806, `tick_mean_ms`); nearest-rank p50 1, p90 2, p99 2, max 9; counts (ms: frames) 0:248 1:1308 2:236 3:13 9:1.

Per field over the same 1806 frames (`frames.cost`, seq 147–2001; the 1 ms clock's means of the measured spans):

| field | sum (ms) | mean (ms) | max | counts |
|---|---|---|---|---|
| `pollMs` | 259 | 0.1434108527131783 | 5 | 0:1556 1:244 2:5 5:1 |
| `linkMs` | 836 | 0.4629014396456257 | 2 | 0:995 1:786 2:25 |
| `senseMs` | 424 | 0.23477297895902546 | 2 | 0:1388 1:412 2:6 |
| `mapMs` | 91 | 0.050387596899224806 | 2 | 0:1719 1:83 2:4 |
| `actMs` | 2 | 0.0011074197120708748 | 1 | 0:1804 1:2 |
| `startMs` | 3 | 0.0016611295681063123 | 1 | 0:1803 1:3 |
| `tickMs` | 1828 | 1.0121816168327795 | 9 | 0:248 1:1308 2:236 3:13 9:1 |

The six named fields' means sum to 0.8942414174972314 of the 1.0121816168327795 mean. Tick by tick, over the 1805 ticks 96–1900 whose body (the next frame's `tickMs`), flush (the next frame's `linkMs`) and named spans (this frame's `pollMs`, `startMs`, `actMs`, `senseMs`, `mapMs`) are all read, the body less the six reads 0 on 1598 ticks, 1 on 200 and 2 on 7, mean **0.1185595567867036 ms**: the frame's positional encode, the overflow check and the timers' own calls, which no field names. The poll and the flush together, tick by tick over the same 1805 ticks, read 0:865 1:792 2:144 3:3 6:1, mean **0.6066481994459834 ms** (the 6 is tick 96, the `rate` 60 command's: poll 5, flush 1).

**The paced poll.** Split by the tick's residue mod 3 (`frames.cost`, seq 147–2001), `pollMs` reads 254 ms over the 602 polling ticks (`tick % 3 == 0`), a mean of **0.4219269102990033 ms** a poll (0:357 1:239 2:5 5:1), and 2 and 3 ms over the 602 and 602 ticks at residues 1 and 2, which open nothing (a millisecond boundary inside an empty span, as the fix pass read for the map phase). In the fix pass's session every tick polled, at **0.42437673130193904 ms** a tick (its guide § 1, the `pollMs` row); its own ticks split the same way read 0.44019933554817275, 0.3903654485049834 and 0.4425956738768719 (602, 602 and 601 ticks; `x4_link_2.json` `frames.cost`, seq 183–2004, this write-up's split). So a poll costs what it did, within the clock, and the pacing cut the poll's share of the tick from 0.42437673130193904 to 0.1434108527131783 ms, a third plus the empty spans. The tick's body (the next frame's `tickMs`) reads 1.308970099667774 ms on the 602 polling ticks and 0.8645054031587698 on the 1203 others (the window's last tick, 1901, has no next frame in the window), a difference of 0.4444646965090042, about one poll.

**The watch with the edges at 60 Hz.** `mapMs` read 91 ms over the 1806 frames: 82 of it on the 301 watch ticks (`tick % 6 == 0`; 0:222 1:76 2:3, mean 0.2724252491694352 a step), 9 on the other 1505 ticks, where the map phase does nothing. The window's watch ticks 96–132 (seven steps) were the watch's first-sight cycle; over the 294 watch steps after tick 132 the watch read 76 ms, **0.2585034013605442 ms a step**, against **0.19798657718120805** (59 ms over 298 steps after tick 132) in the fix pass's window (`x4_link_2.json` `frames.cost`, seq 183–2004, the same split, this write-up's). Over the 22 first-sight steps of each session (watch ticks 6–132, each a frame tick's own `mapMs`; `frames.cost`), this session read 24 ms (mean 1.0909090909090908) against the fix pass's 17 (0.7727272727272727). So with the four edge calls and two neighbour lookups per fingerprinted square the steady watch step rose by 0.06051682417933618 ms (0.2585034013605442 − 0.19798657718120805), one step in six ticks, and the window's `mapMs` mean by 0.016038566428310676 (0.050387596899224806 against the fix pass's 0.03434903047091413, this window holding seven first-sight steps to the fix pass's three): ruling P23-P's input; the steps are 8 squares each (`MP.WATCH_PER_FRAME`), and the rise is not split between the fingerprint's reads and the whole reads of changed squares, of which the steady cycle had one (§ 2).

**The flush and the frame's size.** The flush read 0.4629014396456257 ms a tick against the fix pass's 0.4326869806094183 and the first session's 0.2691029900332226. The frames are longer: over the 60 Hz window the frame lines (`state.log` seq 147–2001) average 216.2846068660022 bytes against 144.204432132964 in the fix pass's window (seq 183–2004), because `me` is written whole on every frame (its elided `true` on 0 of the 1806 frames, against 1623 of 1805): `me.hour` changes every frame (§ 3), so a standing frame's `me` group never matches the frame before. The frame is encoded at its emit, inside the unattributed remainder (0.1185595567867036 against 0.09257206208425721), and the flush writes it; that the longer frame raised both is the reading the numbers fit, and the host differs too (§ 0's memory), which one session does not separate.

**The `rate` 60 command's tick.** Tick 96, a 10 Hz frame tick and a polling tick, took the command (act seq 146) and wrote frame seq 147, the window's first: its `pollMs` 5, `startMs` 1, `mapMs` 2 (a first-sight watch step), `actMs` and `senseMs` 0 (seq 147), its body 9 and its flush 1 (seq 156's `tickMs` and `linkMs`); so its named spans hold all 9 of its body, as the fix pass's rate-60 tick's held its 4.

**The worst tick** (`frames.cost`, all 7506 frames, their `wallMs` spanning 600.089 s; `gate_x4.gates.worst_tick`): the largest `tickMaxMs` is **21**, at seq 11, and `over5` sums to **25** over 25 frames, each reading 1. `tickMaxMs` counts over the session: 0:313 1:6040 2:1081 3:43 4:4 5:6 6:14 7:1 8:1 9:2 21:1. The session's per-phase maxima: `maxPollMs` 0:4557 1:2866 2:60 4:3 5:14 6:4 7:1 8:1; `maxStartMs` 0:7481 1:25; `maxActMs` 0:7109 1:389 2:8; `maxSenseMs` 0:5752 1:1722 2:32; `maxMapMs` 0:6019 1:1463 2:23 3:1; `maxLinkMs` 0:5163 1:2280 2:62 9:1. The 25 frame windows holding a tick of 5 ms or more, by what `state.log` holds between each and the frame before:

| what the window holds | frames (seq: `tickMaxMs`) | ticks of `tickMaxMs` |
|---|---|---|
| the init: the hello and 8 first-sight `item_added` (seq 1–9, tick 1) and the ninth (seq 10, tick 2) | 11: **21** (`maxLinkMs` 9, `maxMapMs` 2, `maxPollMs` 1, `maxSenseMs`, `maxStartMs`, `maxActMs` 0) | 1–5 |
| first-sight watch deltas, 8 a window | 38: 5, 47: 5, 65: 6 (`maxMapMs` 1, `maxLinkMs` 1, 1, 2, `maxPollMs` at most 1) | 18–23, 24–29, 36–41 |
| the `rate` 60 command's tick (act seq 146, tick 96), read at 60 Hz | 156: 9 (its `tickMs`) | 96 |
| a command accepted on a 10 Hz frame tick, whose body falls in the next window (the first scan, legs 2, 6, 8, 10, 18, the final scan) | 2012: 6, 2204: 6, 2726: 6, 2978: 6, 3230: 6, 4238: 9, 4623: 6 | the accept tick and the five after |
| a `walkTo` accepted mid-window (tick T0 + 3: legs 1, 4, 5, 7, 9, 11–17, 19) | 2064: 8, 2469: 5, 2599: 5, 2852: 6, 3104: 7, 3356: 6, 3481: 6, 3608: 5, 3733: 6, 3860: 6, 3985: 5, 4112: 6, 4364: 6 | the six before each frame |

So 21 of the session's 24 commands put their accept tick's body in a window whose worst tick read 5–9 ms (legs 3 and 20 read 4, the `rate` 10 command's window 2), the init window read 21, and three first-sight watch windows read 5–6; no other window reached 5 ms.

**The command windows.** Every command was accepted on a polling tick (`tick % 3 == 0`): the `rate` 60 (tick 96), the `rate` 10 (tick 1902), both scans (ticks 1908 and 15798) and legs 2, 6, 8, 10 and 18 on 10 Hz frame ticks (`tick % 6 == 0`), the other 15 legs on ticks T0 + 3 (`state.log` act lines; `readings.walk.legs[*].accepted_seq`). So the accept tick's own poll is read on all 24: the frame tick's `pollMs` where it is the frame tick, else the window's `maxPollMs`, the window's only other poll being the frame tick's, which read 0 or 1 (`pollMs`) on all 15:

| command (act seq, tick) | accept tick's poll | window of its body: `tickMaxMs` |
|---|---|---|
| `rate` 60 (146, 96) | 5 (seq 147 `pollMs`) | 156: 9 |
| `rate` 10 (2002, 1902) | 1 (seq 2003 `pollMs`) | 2005: 2 |
| `scan` (2004, 1908) | 5 (seq 2005 `pollMs`) | 2012: 6 |
| leg 1 (2063, 1959) | 5 (seq 2064 `maxPollMs`) | 2064: 8 |
| leg 2 (2202, 2706) | 5 (seq 2203 `pollMs`) | 2204: 6 |
| leg 3 (2338, 3441) | 4 (seq 2339) | 2339: 4 |
| leg 4 (2468, 4143) | 5 (seq 2469) | 2469: 5 |
| leg 5 (2598, 4845) | 5 (seq 2599) | 2599: 5 |
| leg 6 (2724, 5532) | 5 (seq 2725 `pollMs`) | 2726: 6 |
| leg 7 (2851, 6219) | 6 (seq 2852) | 2852: 6 |
| leg 8 (2976, 6900) | 5 (seq 2977 `pollMs`) | 2978: 6 |
| leg 9 (3103, 7587) | 7 (seq 3104) | 3104: 7 |
| leg 10 (3228, 8268) | 5 (seq 3229 `pollMs`) | 3230: 6 |
| leg 11 (3355, 8955) | 6 (seq 3356) | 3356: 6 |
| leg 12 (3480, 9633) | 5 (seq 3481) | 3481: 6 |
| leg 13 (3607, 10323) | 5 (seq 3608) | 3608: 5 |
| leg 14 (3732, 11001) | 5 (seq 3733) | 3733: 6 |
| leg 15 (3859, 11691) | 6 (seq 3860) | 3860: 6 |
| leg 16 (3984, 12369) | 4 (seq 3985) | 3985: 5 |
| leg 17 (4111, 13059) | 6 (seq 4112) | 4112: 6 |
| leg 18 (4236, 13740) | 8 (seq 4237 `pollMs`) | 4238: 9 |
| leg 19 (4363, 14427) | 5 (seq 4364) | 4364: 6 |
| leg 20 (4488, 15105) | 4 (seq 4489) | 4489: 4 |
| `scan` (4615, 15798) | 5 (seq 4616 `pollMs`) | 4623: 6 |

23 of the 24 accept polls read 4–8 ms (4 on three, 5 on fourteen, 6 on four, 7 on one, 8 on one: exactly the session's `maxPollMs` readings of 4 or more), the `rate` 10's read 1; every window holding no command line reads `maxPollMs` 0–2 (0:4557 1:2865 2:60), so no poll but a command's accept read above 2 ms. The window of the accept tick's body less the accept poll reads 0 or 1 on 22 commands (the `rate` 10's 1 among them), 3 on leg 1 (whose window also read `maxActMs` 2) and 4 on the `rate` 60 (its start 1, map step 2 and flush 1, all named). `maxStartMs` reads 1 on 25 frames and 0 on the rest, 22 of the 25 in windows holding no command. The command-tick burst is the poll's, as the fix pass read, now with the accept tick's own poll read every time; what in the poll costs 4–8 ms on an accepting tick (the read of a `cmd.txt` the driver has just replaced, the decode, the `ack.txt` write) is still one span. Consecutive legs' accepts lie 11298–12447 ms apart on the client's clock (`readings.walk.legs[*].accepted_wallMs`).

**The 21 ms tick.** Seq 11's window covers ticks 1–5. Tick 1 is the init (`M.init`, `PZAgent_Main.lua` L92–L104: the Link's init with its probe file's two writes, the hello, the inventory's first sight queued, one flush). The nine `item_added` lines now carry `use` and encode to 1576 bytes (the lines of seq 2–10, newlines excluded; 1450 in the fix pass's session), over the flush's `BUDGET_BYTES` 1536 (`PZAgent_Link.lua` L16, L220), so tick 1's flush carried the hello and eight (1397 bytes) and tick 2's the ninth: seq 10 is stamped tick 2. `maxLinkMs` 9 is one of those two flushes (ticks 3–5 had nothing to flush); the eight lines of tick 1's flush are stamped 861477 to 861483 and the hello 861473 (the last six digits of their `wallMs`; tick 2's line 861785), so at least 10 ms of tick 1 lie between the hello's emit and the flush's last stamp, 6 of them inside its flush, which by inference is the 9. Ticks 2–5 polled once (tick 3; the window's `maxPollMs` 1 covers it and tick 6's) and stepped neither the watch nor the sense read (both first on tick 6: `maxMapMs` 2 and `maxSenseMs` 0 are tick 6's). The frames point at tick 1 for the 21 ms, against the fix pass's 15 and the first session's 19, and do not show it: the init's work before its flush is inside no timer, and its flush read 9 against the fix pass's 4.

**The first-sight watch windows.** The three 5–6 ms windows (seq 38, 47 and 65) each hold eight first-sight deltas; their `maxMapMs` reads 1 and `maxLinkMs` 1–2. Their first tick (18, 24 and 36) is the frame tick of the window before, a watch tick whose own `mapMs` reads 3, 1 and 2 (seq 29, 38 and 56) and whose flush carried those deltas, so the body is by inference that watch tick's: its map step, the frame's encode and the flush of eight full square records, now with their four edge fields. The fix pass's first-sight windows read 2 to 4.

**Standing at 10 Hz** after the final scan (the 3360 frames from seq 4674), the windows read `tickMaxMs` 0:53 1:2951 2:346 3:10, all at or under 3, and the samples of the tick before each frame (`tickMs`, a tick at residue 5 mod 6, which neither polls nor senses nor steps the watch) mean 0.021726190476190475 ms, against the fix pass's 0.256021409455843 on ticks that all polled. Through the walk, of the 2286 frame windows from seq 2065 to 4614 holding no command line, five hold a frame-tick accept's body (above) and the other 2281 read `tickMaxMs` 0:13 1:1774 2:481 3:13. The 15 standing 10 Hz frames before the `rate` 60 command (seq 11–137) read 2 to 6 but seq 11's 21, during the watch's first-sight cycle.

**The emit against the sidecar trigger.** Spec § 8 (6) of Plan 22: "K2's transport spike runs only if X4 reads the emit above 1 ms mean or 3 ms worst per tick at the budget"; `gates.sidecar` reads it as the mean and max of `cost.linkMs` over the frames whose `linkMs` is above 0:

- **The gate's reading** (`gate_x4.emit_mean_ms`, `emit_worst_ms`, `emit_frames`; ungraded): over the whole session's 837 frames reading `linkMs` above 0, 812 × 1 + 25 × 2 = 862 ms, a mean of **1.0298685782556751 ms**, worst **2**; `sidecar_trigger` "fired". 811 of the 837 are 60 Hz frames (786 × 1 + 25 × 2 = 836 ms); the other 26 are 10 Hz frames reading 1. On the 1 ms clock a mean over the readings above 0 is at least 1 by construction, so this reading is the clock's, not the flush's.
- **The 60 Hz window's reading** (`frames.cost` seq 147–2001): every one of the 1806 `linkMs` is a flushing tick's flush: mean **0.4629014396456257 ms**, worst **2**, under both the 1 ms and the 3 ms.
- **The flush with the frame's encode, bounded.** The flush plus the tick's unattributed remainder, over the 1805 ticks 96–1900: 0:792 1:976 2:37, mean 0.5817174515235457 ms, worst 2; not above either threshold.
- **The link's two operations with the poll.** The poll plus the flush, tick by tick, mean 0.6066481994459834 ms, worst 6 on the `rate` 60 command's tick and 3 on three others.

Ruling S-18 reads the trigger as **not fired**: by the gate "fired" (1.0298685782556751 over 837 frames, worst 2), on every honest population not fired (the flush 0.4629014396456257 ms mean and 2 worst; the flush with the encode bounded at 0.5817174515235457 and 2).

**Scan parts.** Each scan's 49 parts went out one a tick (first scan seq 2006–2062, ticks 1908–1956; final scan seq 4617–4673, ticks 15798–15846); the frames over each scan read `maxMapMs` and `maxLinkMs` at most 2 a window (`maxMapMs` 2 on seq 2033 and 2054 of the first and 4637 of the final, `maxLinkMs` 2 on seq 2040 and 2061 of the first), so a scan part's step, now with its squares' four edge calls, and its flush each read at most 2 ms on the 1 ms clock, as in the fix pass's session.

**The three sessions** (the first: `testing/artifacts/x4_link-20261027-171916/GUIDE.md`, rows #4203–#4207, Lua `c8493a0e`; the fix pass: `testing/artifacts/x4_link_2-20261027-210612/GUIDE.md`, rows #4214–#4216, Lua `5d9debb5`; this: Lua `e3e68793`; each number at its own guide's section):

| reading | first session | fix pass | this session |
|---|---|---|---|
| 60 Hz window | 1806 frames, seq 211–2016, ticks 182–1987 | 1805 frames, seq 183–2004, ticks 117–1921 | 1806 frames, seq 147–2001, ticks 96–1901 |
| tick mean at 60 Hz | 1.672203765227021 ms (p50 2, p90 2, p99 3, max 9) | 1.2614958448753462 ms (p50 1, p90 2, p99 3, max 4) | 1.0121816168327795 ms (p50 1, p90 2, p99 2, max 9) |
| poll (`pollMs`) | not timed | 0.42437673130193904 a tick, every tick polling, worst 2 | 0.1434108527131783 a tick; 0.4219269102990033 a poll on the 602 polling ticks; worst 5 |
| flush (`linkMs`) | 0.2691029900332226, worst 2 | 0.4326869806094183, worst 2 | 0.4629014396456257, worst 2 |
| sense read (`senseMs`) | 0.7115171650055371 | 0.2692520775623269 | 0.23477297895902546 |
| map watch (`mapMs`) | 0.3449612403100775 | 0.03434903047091413 (0.19798657718120805 a steady step) | 0.050387596899224806 (0.2585034013605442 a steady step) |
| skill tick (`actMs`) | 0.0005537098560354374 | 0.004986149584487534 | 0.0011074197120708748 |
| start (`startMs`) | not timed | 0.002770083102493075 | 0.0016611295681063123 |
| unattributed remainder | 0.3462603878116344 (the poll, the encode, the timers) | 0.09257206208425721 | 0.1185595567867036 |
| poll + flush, tick by tick | — | 0.8575388026607539 | 0.6066481994459834 |
| the emit with its encode, bounded | 0.6155124653739612, worst 3 but tick 182's 8 | 0.5254988913525499, worst 3 | 0.5817174515235457, worst 2 |
| the gate's emit reading | 1.0576131687242798 over 486, worst 3, "fired" | 1.019280205655527 over 778, worst 2, "fired" | 1.0298685782556751 over 837, worst 2, "fired" |
| frame line at 60 Hz | — | 144.204432132964 bytes mean | 216.2846068660022 bytes mean (`me` never elided) |
| the `rate` 60 command's tick | 9 ms, 7 unattributed (tick 182) | 4 ms, all named (tick 117) | 9 ms, all named: poll 5, start 1, map 2, flush 1 (tick 96) |
| worst tick | 19 (seq 43, ticks 1–4) | 15 (seq 11, ticks 1–5) | 21 (seq 11, ticks 1–5; its flush 9) |
| `over5` over the session | 31 in 30 windows over 600.066 s | 25 in 25 windows over 600.013 s | 25 in 25 windows over 600.089 s |
| command windows | all 24 at 5–9 ms, cause unattributed | 23 of 24 at 5–7 ms, the poll's worst 4–7; 8 in the window after leg 1's accept | the accept poll read on all 24: 23 at 4–8, the `rate` 10's 1; 21 bodies' windows at 5–9 |
| other windows of 5 ms or more | 6 (two first-sight watch windows, four lone) | none | 3, first-sight watch windows |
| standing at 10 Hz after the final scan | `tickMaxMs` 1:1471 2:1727 3:138 4:13 5:1 (one 0), `tickMs` mean 0.588779468815279 | `tickMaxMs` 0:76 1:3057 2:225 3:5, `tickMs` mean 0.256021409455843 | `tickMaxMs` 0:53 1:2951 2:346 3:10, `tickMs` mean 0.021726190476190475 |
| legs (ack → first move) | 128–181 ms, p50 146, p90 165 | 126–195 ms, p50 147, p90 178 | 144–196 ms, p50 147, p90 196 |
| kept map | 6 walls, 3 doors, 13 windows, 21 containers, ratio 1.0 each | the same | the same, the four edge fields included |
| final scan's window | shifted; 870 shared squares, 91 outside the kept map | the same | the same |
| door events | 1 (tick 2124, before the agent entered at tick 2136) | 1 (tick 2148, after the agent entered at tick 2070) | 1 (tick 2040, before the agent entered at tick 2052) |
| first-sight watch | 169 deltas on ticks 2–23 | 169 deltas on ticks 6–132, every sixth | 169 deltas on ticks 6–132, every sixth |
| wall; memory at the gate, ready, after | 702.2 s; 13.51, 2.31, 15.85 GB | 688.2 s; 12.63, 2.67, 16.66 GB | 685.3 s; 12.23, 2.18, 16.2 GB |

Against the fix pass, the pacing cut the poll's share of the tick by 0.28096587858876076 ms (0.42437673130193904 − 0.1434108527131783), a poll costing what it did, and the mean fell 0.24931422804256664 ms (1.2614958448753462 − 1.0121816168327795): the flush rose 0.030214459036207397, the watch 0.016038566428310676 and the remainder 0.025987494702446393, and the sense read fell 0.03447909860330142 (each the difference of the two windows' means). The mean stands 0.0121816168327795 ms over `gate_x4`'s 1.0.

## 2. The map

**The first scan** (`readings.scan`): `scanId` 1, `parts` 49, `got` 49, `complete` true, `squares` 961, in 0.83 s (`seconds`); `mapMs` on its 9 frames 1, 1, 0, 1, 0, 1, 0, 1, 1. From the settled start (10997.5, 9699.5) (`readings.walk.start`) its squares span x 10982–11012, y 9684–9714 (`state.log` seq 2006–2062), the earlier sessions' window. No part carries a `missing` name (every part's `missing` list empty, both scans), so every square's four edge fields were read.

**The watch before the walk.** The watch sent its 13 × 13 ring as 169 first-sight `delta` lines on the 22 watch ticks 6–132 (seq 12–232, 8 a step and 1 on the last; x 10991–11003, y 9693–9705), each square inside the first scan's window.

**The watch during the walk** (`readings.walk.map_deltas` **1**, on leg 1; the other 19 legs' `map_deltas` 0). The walk's one delta, seq 2078 (tick 2034, a watch tick), carried square (10995, 9701, 0) with its door `[true, false, false]` (`open`, `locked`, `barricaded`) and its edges `blockN` false, `blockW` false, `edgeN` true, `edgeW` false, against the door `[false, true, false]` and `blockN` true, `edgeN` true in the first-sight delta (seq 133) and the first scan (seq 2037); the `door` event at seq 2079 (tick 2040, the next frame tick's events) read the door at (10995, 9701, 0) `open` true. Leg 1's frames entered that square at seq 2082 (tick 2052, y 9701.1875), so this time the delta came 18 ticks and the event 12 ticks (200 ms of the client's clock between the event's and the entering frame's `wallMs`) before the agent stood in the doorway, where the fix pass's came 72 and 78 ticks after; the door's change and its edge's together changed the square's fingerprint, so which of the two the watch caught first is not separated.

**The walk's ground.** As in both earlier sessions, each leg was sent to its own start's x ± 6 at y 9699.5 (`readings.walk.legs[*].target`), and every leg's frames (positions merged across delta frames) reach y 9695.5 and y 9701.5 and x 10993.5 or less, all within x 10993.2099609375–11003.0478515625: the pathfinder's loop through the door at (10995, 9701).

**The final scan and the kept map** (`readings.final_scan`): settled (`settled` true) at (10995.5, 9700.154296875), the kept map snapshotted before the scan (`kept_squares` 961, the kept map's size), then `scanId` 2, 49 of 49 parts, 961 squares in 0.903 s (`mapMs` 1, 0, 1, 2, 1, 1, 1, 0, 1). Its window, x 10980–11010 and y 9685–9715 (seq 4617–4673), is shifted from the first scan's exactly as in both earlier sessions: the two share 870 squares, and the 91 final squares at x 10980–10981 and y 9715 lie outside the kept map. None of the 91 carries a wall, a door, a window or a container, so each kind's `absent` reads 0; and the 870 shared squares read identical in the kept map (the first-sight deltas, the first scan and the door delta, the last line for a square winning) and the final scan in every field but `light`, the four edge fields included (`state.log`, compared square by square). The four kinds (`readings.final_scan.kept`):

| kind | kept | total | absent | seen | ratio |
|---|---|---|---|---|---|
| walls (`solid` true) | 6 | 6 | 0 | 6 | 1.0 |
| doors | 3 | 3 | 0 | 3 | 1.0 |
| windows | 13 | 13 | 0 | 13 | 1.0 |
| containers (by square and type) | 21 | 21 | 0 | 21 | 1.0 |

So the kept map held every one of the final scan's 43 walls, doors, windows and containers, the door's opening included, the earlier sessions' reading a third time; `absent` is coverage by kind, and the square coverage was 870 of 961.

**The edge fields' first live reading** (the final scan's 961 squares, `state.log` seq 4617–4673): `blockN` true on 89, `blockW` on 76, `edgeN` on 90, `edgeW` on 76; 160 squares carry at least one true (83 north only, both fields; 70 west only, both fields; 6 all four; 1 `edgeN` alone). Every blocked edge is also an edge (`blockN` without `edgeN` 0, `blockW` without `edgeW` 0), and the one edge that is not blocked is the opened door's: (10995, 9701, 0), door `[true, false, false]`, reads `edgeN` true and `blockN` false, where the same door closed and locked read `blockN` true and `edgeN` true (the first scan, seq 2037, and the first-sight delta, seq 133). The two doors the session never opened, both closed and locked, read blocked on their edge: (10998, 9704, 0) `blockN` and `edgeN` true, (10999, 9702, 0) `blockW` and `edgeW` true. All 13 windows, closed (11 locked, 2 not), read blocked on their square's north or west edge or both (`blockN` and `edgeN` on 4, `blockW` and `edgeW` on 11, both pairs on 2 of them); none was open or smashed, so the unblocked open window is not read. Of the 6 `solid` squares, 4 read an edge blocked and 2 none. So a door reads blocked on its edge while closed and not while open, and the edge stays an edge either way: the jar's `isBlockedTo` and `isSomethingTo` rules (Task 3's rows), read live once, on one door's two states and two closed doors; which edge of a door's square the door sits on is read off the fields, the jar's note not reading which sprites carry the collide flags.

## 3. The hour and the legs

**`me.hour`** is on all 7524 frames (`state.log`), from 9.316320419311523 at seq 11 to 11.990715980529785 at seq 8051, and on every frame equals `worldAge` + 7.0 exactly and its whole minutes equal `gameMin` (floor(`hour` × 60) = `gameMin`, 558 to 719). It stepped back twice, by 0.000270843505859375 h at seq 1036 (tick 936) and 0.0001468658447265625 h at seq 1642 (tick 1542), 10.099 s apart on the client's clock (the two frames' `wallMs`), `worldAge` stepping back with it; Task 3's jar read has the client's clock set from the server's at each clock sync, sent every 10 s of wall time, which is the reading these two steps fit, not one the frames show.

**The legs.** Each leg's `accepted_seq` is its `walkTo` accepted act line, its first move the first frame after it whose position moved more than 0.01 tiles, its latency `first_move.wallMs` − `accepted_wallMs` on the client's clock (`readings.walk.legs[*]`); every leg was `settled` true before its send, its `at_accept` equal to its start:

| leg | start x | target x | `accepted_seq` | `first_move.seq` | latency (ms) | end | `result.d` |
|---|---|---|---|---|---|---|---|
| 1 | 10997.5 | 11003.5 | 2063 | 2065 | 145 | done | 0.9833203675875426 |
| 2 | 11003.0478515625 | 10997.0478515625 | 2202 | 2205 | 196 | done | 0.9830104513301557 |
| 3 | 10996.58203125 | 11002.58203125 | 2338 | 2340 | 147 | done | 0.9934674515098483 |
| 4 | 11002.3505859375 | 10996.3505859375 | 2468 | 2470 | 144 | done | 0.9910396634660937 |
| 5 | 10995.943359375 | 11001.943359375 | 2598 | 2600 | 146 | done | 0.9966259301407455 |
| 6 | 11001.5 | 10995.5 | 2724 | 2727 | 196 | done | 1 |
| 7 | 10995.5 | 11001.5 | 2851 | 2853 | 147 | done | 0.96484375 |
| 8 | 11001.5 | 10995.5 | 2976 | 2979 | 196 | done | 1 |
| 9 | 10995.5 | 11001.5 | 3103 | 3105 | 144 | done | 0.96484375 |
| 10 | 11001.5 | 10995.5 | 3228 | 3231 | 196 | done | 1 |
| 11 | 10995.5 | 11001.5 | 3355 | 3357 | 147 | done | 0.96484375 |
| 12 | 11001.5 | 10995.5 | 3480 | 3482 | 145 | done | 1 |
| 13 | 10995.5 | 11001.5 | 3607 | 3609 | 146 | done | 0.96484375 |
| 14 | 11001.5 | 10995.5 | 3732 | 3734 | 147 | done | 1 |
| 15 | 10995.5 | 11001.5 | 3859 | 3861 | 145 | done | 0.96484375 |
| 16 | 11001.5 | 10995.5 | 3984 | 3986 | 147 | done | 1 |
| 17 | 10995.5 | 11001.5 | 4111 | 4113 | 145 | done | 0.96484375 |
| 18 | 11001.5 | 10995.5 | 4236 | 4239 | 193 | done | 1 |
| 19 | 10995.5 | 11001.5 | 4363 | 4365 | 146 | done | 0.96484375 |
| 20 | 11001.5 | 10995.5 | 4488 | 4490 | 147 | done | 1 |

All 20 legs moved and ended `done` with an empty `reason`; none lacks a first move. Over the 20 latencies, 144–196 ms: nearest-rank p50 **147**, p90 **196** (`gate_x4.gates.cmd_move_p90.value`), max **196**; mean 158.25. The first move is the second frame after the accept on the 15 legs accepted mid-window (`first_move.seq` = `accepted_seq` + 2, 144–147 ms) and the third on the five accepted on a 10 Hz frame tick (legs 2, 6, 8, 10 and 18: + 3, 193–196 ms), where the accept's act line precedes that tick's own frame; with the poll on every third tick, half the polling ticks are frame ticks, where the fix pass's every-tick poll put one leg of 20 there. Against the earlier sessions (128–181, p90 165; 126–195, p90 178): the same within the frame period of about 100 ms. The paced poll's own wait, up to two ticks from the driver's write of `cmd.txt` to the accepting tick, falls before the accept line and is not in this measure.

## 4. What the frames cannot say, the host, the controller's readings

**What the frames cannot say.**

- **What in the poll costs 4–8 ms on an accepting tick.** The open, the read of a `cmd.txt` the driver has just replaced, the decode and the `ack.txt` write are one span; a polling tick that takes nothing reads 0.4219269102990033 ms a poll, an accepting one 4–8 (the `rate` 10's 1 the exception), and the frames do not split the two.
- **The 21 ms tick's owner.** One of ticks 1–5, the frames pointing at tick 1 (the init, its flush by inference the 9) without showing it; why the init's flush read 9 against the fix pass's 4 (eight keyed lines each with `use`, against nine without; another host state) is not separated.
- **Why the flush rose again.** 0.4629014396456257 ms against 0.4326869806094183 with frames 72 bytes longer and another host state (§ 0); one session does not separate the two.
- **The watch's rise, split.** The steady step's 0.06 ms rise is the fingerprint's four member calls and two neighbour lookups a square and the whole reads of the changed squares together; one changed square in the steady cycle (the door) leaves the fingerprint's share as the reading's bulk by inference, not measured apart.
- **The open window and the stairs.** No window was open or smashed and no stair in the scans, so `blockN`/`blockW` false on an open or smashed window and a stair top's block are unread live; nor is the collide flag beside a door frame.
- **Sub-millisecond spans.** Every `cost` field is an integer on the 1 ms clock: a single reading is a bound, a mean over many is the clock's mean of the measured spans, and the gate's mean over the readings above 0 is at least 1 by construction.
- **The emit with its encode.** `linkMs` is the flush alone; the frame's encode is inside the unattributed remainder with the overflow check and the timers, so the emit is bounded (§ 1), not measured.
- **The two clocks.** A line's `wallMs` is the client's clock in epoch milliseconds; the driver's `*_wall` keys are this process's clock in seconds; nothing here sets one against the other, and every latency and span above is a difference within one clock.
- **The kept map's square coverage, and the door's opening.** The ratios are fidelity over the 43 features on the 870 squares both scans covered; the door delta and event are read, the opening itself is not.
- **The hour's steps.** That the two backward steps are clock syncs is the jar's mechanism set against their 10.099 s spacing, not a reading of a sync.

**The host.** One Windows host; free memory 12.23 GB at the gate after a 30-minute wait at the 12 GB floor, 2.18 GB at ready with the server and the `-debug` client up, 16.2 GB after teardown (`memory`, `memory_wait`). Every millisecond above is this host's.

**The epoch-ms leaves** (wildcard): `*wallMs`, `*_wall`, `wall_*` and `epoch_ms_*` anywhere in `x4_link_3.json` (`frames.cost[*].wallMs`, `readings.hello.first_frame.wallMs`, `readings.walk.legs[*].accepted_wallMs`, `accepted_wall`, `first_move.wallMs`, `end.ended_wall`, `readings.*.act.ended_wall`, `rate_on.ended_wall`, `rate_off.ended_wall`, `server_launch_wall`, `server_started_wall`, `session_ready_wall`, `wall_seconds`, `steps[*].wall_before`, `epoch_ms_before` and the like), the `wallMs` of every line of `state.log`, and `took`, `timeline`, `phase_walls`, `client_seen`, `memory[*].wall` and `memory_wait[*].wall` are this host's clocks, cited only as a difference within this run (a latency, a span), never as a reading.

**The controller's readings** (`.superpowers/sdd/2026-10-28-plan-23-survivor/progress.md`, the Task 17 lines, and the write-up's dispatch): the 60 Hz window's 1806 frames and their means (tick 1.012182, poll 0.143411, flush 0.462901, sense 0.234773, map 0.050388, act 0.001107, start 0.001661), the worst `tickMaxMs` 21 at seq 11, `gates.sidecar`'s ("fired", 1.0298685782556751, 2, 837), the verdict (NO-GO on `tick_mean_at60` and `worst_tick`, GO on the five others) and the memory 12.23 / 2.18 / 16.2 GB are confirmed as read. The committed do-not-cite row for `maxPollMs` names the range 0–5 and the accept tick's poll as read only where it is the frame tick; the session reads `maxPollMs` 0–8, and with the paced poll the accept tick's poll is read on all 24 commands (§ 1): the write-up corrects that row.

## 5. The grade

`gate_x4` (`x4_grade.txt`, verbatim values; the same object is `gate_x4` in `x4_link_3.json`):

| gate | ok | value | threshold | n |
|---|---|---|---|---|
| `tick_mean_at60` | **false** | 1.0121816168327795 | mean < 1.0 ms over >= 1620 frames | 1806 |
| `worst_tick` | **false** | `tickMaxMs` 21, `over5` 25, `span_s` 600.089 | max tickMaxMs <= 3.0 ms and 0 over5, over >= 600.0 s | 7506 |
| `gaps` | true | 0 | == 0 | 1 |
| `lua_errors` | true | 0 | == 0 | 1 |
| `parks` | true | 0 | == 0 | 1 |
| `cmd_move_p90` | true | 196 | p90 < 500.0 ms over >= 20 legs | 20 |
| `map_kept` | true | walls 1.0, doors 1.0, windows 1.0, containers 1.0 | each of walls/doors/windows/containers ratio >= 0.99 | 43 |

**Verdict: NO-GO** (`verdict`), on `tick_mean_at60` and `worst_tick`, as in both earlier sessions. Beside it, ungraded: `sidecar_trigger` "fired", `emit_mean_ms` 1.0298685782556751, `emit_worst_ms` 2, `emit_frames` 837, `sidecar_thresholds` `{mean_ms 1.0, worst_ms 3.0}`. Re-running `x4_grade.py` on this folder's `x4_link_3.json` reproduces `x4_grade.txt` byte for byte (`cmp` equal).

**The sidecar trigger, both ways (ruling S-18).** By the gate, "fired" (the mean over the 837 frames reading above 0, at least 1 on the 1 ms clock by construction). By ruling S-18's reading, **not fired**: over the 60 Hz window the flush reads 0.4629014396456257 ms mean and 2 ms worst, the flush with the encode bounded at 0.5817174515235457 and 2, under the 1 ms mean and not above the 3 ms worst; so the spike does not run on the trigger, and `gate_x4` stays frozen.

**What the reading says.** The paced poll did what spec § 5's P23-4 asked: a poll costs what it did (0.4219269102990033 ms against 0.42437673130193904), a third as often, and the mean fell from 1.2614958448753462 to 1.0121816168327795 ms; the mean stays 0.0121816168327795 ms over the gate, with the flush now the largest named span (0.4629014396456257) and the edges adding about 0.016 ms a tick to the watch at 60 Hz. The failed `worst_tick` is the init tick (21 ms), the commands' accepting polls (4–8 ms, bodies to 9) and the watch's first-sight windows (5–6 ms), while standing and walking windows holding no command read at most 3 ms. The plan runs this session once with no fix pass (spec § 10); what follows from it is the controller's.

## Do not cite from this file

| Key | Value in the file | Why not |
|---|---|---|
| everything measured here, as a population | — | One boot, one fixture, one character, one host; with the two earlier sessions, `n = 3` on the legs, the kept map and the flush. |
| `gate_x4.sidecar_trigger` | "fired" | A mean over the 1 ms clock's readings above 0, at least 1 by construction; ruling S-18 reads the trigger as not fired (§ 1, § 5). |
| `gate_x4.emit_mean_ms` as the emit per flushing tick | 1.0298685782556751 | The subset reading above 0; the flush per flushing tick is the 60 Hz window's 0.4629014396456257 mean over 1806 flushes. |
| `frames.cost[*].cost.linkMs` and `cost.tickMs` at 10 Hz as a frame tick's cost | 0–2 | They sample the tick before each frame tick, which now neither polls nor senses nor steps the watch. |
| any single `cost.*Ms` reading | integers 0–21 | The 1 ms clock: a reading is a bound, never a value. |
| `frames.cost[*].cost.maxPollMs` as one tick's poll | 0–8 | A window's worst over its two polling ticks; the accept tick's own poll is the window's `maxPollMs` only where the frame tick's `pollMs` is lower (§ 1). |
| `readings.final_scan.kept_squares` and `final_squares` as square coverage | 961 | The kept map's size and the final scan's; 91 of the final squares were outside the kept map (870 shared). |
| `readings.final_scan.kept.*.absent` as square coverage | 0 | Per kind: 91 of the 961 final squares were not in the kept map. |
| `readings.walk.legs[*].target` as the path walked | x0 ± 6 at y 9699.5 | Every leg looped, reaching y 9695.5 and 9701.5 within x 10993.2099609375–11003.0478515625 (§ 2). |
| `readings.walk.legs[*]` latency finer than a frame | 144–196 | Frame-quantised at about 100 ms (the second frame after the accept, the third on an accept at a frame tick). |
| `readings.scan.mapMs`, `readings.final_scan.scan.mapMs` as the scan's cost | 0–2 | A frame tick's own step, one tick in six. |
| `readings.server.stats.ack.mult` | 4.794972896575928 | getMultiplier, not the true multiplier (#3762). |
| every `reason` and error text | empty | Empty in this run; a text is the driver's or the Lua's message, not a reading. |
| `constants`, `preboot`, `profile`, `fixture`, `argv`, `memory`, `memory_wait`, `world_changes`, `steps`, `verify` | the driver's tables | Written before or around the run, or the server reading's raw steps; not readings. |

## Corrections

None yet; a later fix to this guide is dated and named here, the text above left as written.
