# `e_day_7-20261029-140813` reading guide

**`e_day_7-20261029-140813/e_day_7.json`** (with `state.log`, `state.1.log`, `decision.log`, `e_grade.txt` and `shots/shots.jsonl`) — produced by `testing/agent/drivers/e_day_7.py` at `driver_commit` `68c18eee` (Plan 24 e_day_7: the seventh chain's driver; `gate_e4` and `grade_e4`, kills the headline), unedited since (its last commit at HEAD is `68c18eee`), on the driver library `testing/agent/driverlib/` at `preboot.driverlib_commit` `68c18eee` (`shots.py` at `425fc6dc`: the guarded shot taker, Task 15 fix 1; `session.py` at `a7fb6ff9`; `day.py` at `68c18eee`), which imports `testing/experiments/xlib.py` (`preboot.xlib_commit` `45c49217`) and the agent base under `testing/agent/base/` at `preboot.agent_commit` `0f7881a1` (`planner/survive.py` and `planner/care.py` at `24987f2a`, `planner/policies.py` and `world.py` at `f774248d`, `planner/goals.py` at `6159dbc4`: survival iteration 7, Task 12 and its fix rounds 1 and 2; `pza1.py` at `c211e196`; `gates_e.py` at `68c18eee`, carrying `grade_e4`); on HEAD `0f7881a1` at the boot (`preboot.commit`; `preboot.harness_lua_commit` `edcaf2e6`, `preboot.harness_lua_dirty` false; `preboot.harness_py_commit` `3c5a6e3b`; `preboot.driver_checks`: `agent_lua_dirty`, `agent_base_dirty`, `driverlib_dirty` and `driver_dirty` false). The agent mod `testing/PZAgent/PZAgent` loaded by path from the tree, its last commit `a945ae4d`: PZAgent 1.5.6 (`readings.hello.hello.mod` `1.5.6`, `proto` `PZA/1`, seventeen `caps`), the stance held from `OnPlayerUpdate` every frame, proven live by the probe `p_stance-20261029-135919` before this boot. Fixture `agent` (`fixture.provision_run` `prov-20261026-092028`, `fixture.build` `42.21.0`, Zombies 5, `fixture.parent` null); profile `testing/profiles/agent.toml` (`preboot.profile` `agent`; PZTestKit + PZAgent, user `admin` on a `-debug` client, the 90-minute day); `argv` `--session 1 --fixture agent`, no `--prev`. Graded by `grade_e4` (`testing/agent/base/gates_e.py` at `68c18eee`) inside the artifact and through `testing/agent/drivers/e_grade_4.py` (`68c18eee`); the session is a report with no gate.

**Plan 24's E7, the seventh chain's first session** (spec `docs/superpowers/specs/2026-10-29-plan-24-the-group-design.md` § 6 items 14–17). The planner is `Survive(source=ScriptedSource())` at survival iteration 7, its branches `threat`, `care`, `need`, `load`, `night`, `goal` in that order at `PLANNER_HZ` 2. **By the iteration metric of ruling P24-Q, the session killed nothing: no attack was sent, no swing or `zombie_dead` event came, and `grade_e4.kills` reads planner 0 (engine null: no death event).** **The character ran to the driver's day cap at game minute 786 with its health at 100 on every one of the 8534 frames, no wound read**, 226.77154541015625 game minutes from the first frame to the last frame the driver read. All three fights ended in the `many` flee (four or more zombies listed within 12 tiles); the goal branch then walked on with zombies listed about 8 to 10 tiles off (7.9855142217366994 to 9.918560285382432); the character stood 55.6 s at a locked back door while eight loots failed `not adjacent`; and from game minute 628 it walked 158.0072021484375 game minutes through woods with no building the map had ever read within 40 tiles, ending 737.5171649765088 tiles from where it began. The stance read live in a planner session for the first time, on every frame of its four legs but the first. Under P24-Q a session with no kill is a failure whatever its length.

## 0. The run

- **Wall.** 923.5 s (`wall_seconds`, counted from the memory gate). Server started at 23.3 s (`timeline`), the client in game 34.9 s and ready 37.4 s after its launch (`client_seen[0]`), the session ready at 61.1 s, both `verify` pings ok, the RCON `additem` at 67.2 s, client quit rc 0 at 915.8 s, server stopped rc 0 with 0 errors at 923.6 s. Phases (`phase_walls`): `hello` 63.558–63.57, `damage_hook` 63.571–65.078, `kit` 65.08–72.061, `loop` 72.062–913.135.
- **Hello.** `readings.hello`: `ok` true, `proto` `PZA/1`, `mode` `append`, `build` `42.21`; the hello line (`state.log` seq 1): `mod` `1.5.6`, `user` `admin`, `rate` 10, seventeen `caps` (`aim` to `wash`); `first_frame.seq` 10.
- **The damage hook** (`readings.damage_hook`): `ok` true, `hooked` true, `n` 0.
- **The kit** (`readings.kit`, `ok` true, `armed` true): the bat's `item_added` at seq 250 (`use` `weapon`), the `equip` a1 `done`, the first frame wielding it seq 302 (`readings.kit.weapon_frame`); the weapon group read `Base.BaseballBat`, `reach` 1.125, `cond` 15 on 8415 frames and null on the 119 before the equip.
- **Pipe health.** `frames.gaps` 0, `frames.bad` 0, `frames.lua_errors` 0, `frames.parks` 0, `logs.clients.admin` `[]`, `admin_lua_error` false, `server_error_count` 0, `bus_dead` null, `phase_errors` `{}`, `missing` `[]`. The poll thread: `loop.server_polls` 14, `loop.server_fails` 0, `loop.damage.polls` 168, `fails` 0, `merged` 0; `loop.polls_joined` and `loop.shots_joined` true. The shot taker: `loop.shots` `n` 81, `skipped` 21, `failures` 0 (§ 9).
- **The stop.** `stop.reason` `day_cap` (`stop.detail`: the loop's 840 s of wall time), `stop.gameMin` 786; the loop then stopped the character (`loop.stopped`: `aid` a395, `state` `done`, `ack_seq` 18451).
- **Frames, in two files.** The Lua rotated its log during the session: `state.log` holds seq 1–15639 (its last frame seq 15635, game minute 752) and `state.1.log`, the rotation, seq 15640–18466. Read as one stream (the two files concatenated in that order and decoded with `testing/agent/base/pza1.py` through `FileTransport` from a `git archive 0f7881a1` copy) they hold 18466 lines, line *n* seq *n*, 0 bad, 0 gaps: 1 `hello`, 8534 `frame` (seq 10–18466, every consecutive pair six ticks apart: 10 Hz), 8705 `map` (2875 `full`, 5830 `delta`), 1211 `act` and 15 `event` (13 `item_added`, 2 `door`). The driver read 8521 frames (`frames.n`), the last seq 18453; the 13 after it came after its last read. `state.1.log` was not in the artifact committed at `cd7e2b15`; this write-up copies it byte-identical from the run folder (Corrections 1).
- **Memory.** Free 14.41 GB at the preboot read (against `MIN_FREE_GB` 12.0), 1.55 GB at ready, 15.3 GB after teardown (`memory`).

Files (the controller's copy at `cd7e2b15` and, for `state.1.log`, this write-up's; each byte-identical to the run folder's):

| File | Source | Bytes | sha256 |
|---|---|---|---|
| `e_day_7.json` | the run's `e_day_7.json`; CRLF endings, no final newline | 3622850 | `d378e7dcb83255c32583efb14c984dc10fc5c7cc6030d3980b6255dacdb2bd04` |
| `state.log` | the run's `clients/admin/Lua/pzagent/admin/state.log`, seq 1–15639; CRLF endings, 15639 lines | 8387092 | `41549a038278b304d76d5c8a7aa5d3ce52ade3de7c59addb762c901b4105113e` |
| `state.1.log` | the run's `clients/admin/Lua/pzagent/admin/state.1.log`, the rotation, seq 15640–18466; CRLF endings, 2827 lines | 1400798 | `d0945783bba89de0f7767670b843a5c22decedf4d6bd68049f61478217689a58` |
| `decision.log` | the driver's copy of the run's `decision.log`, one line a planner tick; CRLF endings, 1680 lines | 1652937 | `4663abe0edd409713267dc2e7d2104522db8e5a814762a5185f0b196e498fb7b` |
| `e_grade.txt` | `python testing/agent/drivers/e_grade_4.py` on this folder's `e_day_7.json`, stdout; the write-up's re-run from a `git archive 0f7881a1` copy is byte-identical; CRLF endings, 235 lines | 6351 | `3919377a99087349dea244db55b8f116c1e94ee0b750286382945e4005fcd218` |
| `shots/shots.jsonl` | the run's `shots/shots.jsonl`, one line a shot or a skipped shot; CRLF endings, 102 lines | 44381 | `4b38870b61a3fd2d3c652168b0bdee8cb95bbdc5e2b289267180b83910428ce8` |
| `shots/shot-NNNN-<seq>.jpg` | the images this guide cites (n 6, 26, 30, 36, 38, 60 and 99), copied byte-identical from the run folder's `shots/` at the mint; each one's bytes and sha256 are its index line's | — | — |

`state.log` and `state.1.log` are the only evidence of the lines between the frames (the acts, the map, the events) and of each zombie the frames listed; `decision.log` of each planner tick; the shots of the scene. The hashes are of the working-tree bytes. The 74 shots this guide does not cite, the driver's stdout, the client console, `server-stdout.log` and the logs under `server/` are per-machine and untracked, and nothing below rests on them.

## How to read it

A frame is a positional line of the two logs read as one stream in the schema's `frame` order (`pza1.py`), its delta groups merged from the frame before; a seq up to 15639 is in `state.log`, from 15640 in `state.1.log`. The kept map is `World.apply` (`world.py` at `f774248d`) over every line up to the seq named; a **building square** is a square record whose `building` is not null (282 in the session, of buildings 2, 3, 5 and 6, the last first read at seq 4108), and a distance to a building is to the nearest such square's centre. A **loop second** is a difference of two `wallMs` (or a `decision.log` `wall` against a `wallMs`) on this host's one clock. A planner tick is one `decision.log` line, cited as line *n*; `inputs.threats` counts the zombies within `DANGER_R` 6, `inputs.held` within the hold radius (`DISENGAGE_R` 10 while a threat policy runs, else 6, by the code), `inputs.nearest` the nearest held. A tick's frame is the latest frame whose `wallMs` is at or before the line's `wall`. An act's frames are those between its `accepted` line and its end line. `loop.fights[k]` is fight *k*; `loop.goals` holds the goal runner's 262 rows.

**Survival iteration 7** (`planner/survive.py` at `24987f2a`, its docstring's "Survival 6" rows as Task 12 rewrote them, rulings P24-N, P24-O, P24-P, P24-U; code, not readings). (1) A fight opens in the stance and keeps it: every leg an `aim` of `policies.AIM_LEG_S` facing the target, backpedalling inside `policies.KEEP_R` 2.5, swinging from the stance within reach; the `many` reason (four or more listed within `policies.LISTED_R` 12, ruling P24-A) and the other flee reasons are read first, as before. (2) No leg sprints (P24-O): every steer and run walk at a run. (3) The care branch yields the threat branch with the nearest beyond `care.CARE_R` 4 and no `many`, with hysteresis; under a flee leg with the nearest beyond `care.RIDE_R` 6 a part above the legs is bandaged riding (P24-U). (4) The goal branch, below them, runs the scripted source (`planner/goals.py` at `6159dbc4`): `LootBuilding` the nearest building with a known container not looted, else `ExploreToward` the kept map's unexplored edge, a scan of the place first while it is unscanned, then the walk.

## 1. The kills, the iteration's metric

**No kill.** No `attack` was sent in the session (`loop.actions`, 393 rows: `walkTo` 233, `scan` 125, `steer` 19, `interact` 12, `aim` 4), the 15 events hold no `swing`, no `zombie_dead` and no `death`, and `grade_e4.kills` reads `planner` 0, `planner_ids` `[]`, `per_fight` [0, 0, 0], `engine` null (the engine's count is the death event's `zombiesKilled`, and the character did not die). Against the earlier sessions' death events: E6 1 (#4321), F2 2 (#4319), F1 3 (#4281), the fifth chain 0 (#4267).

**The length.** The first frame (seq 10) read game minute 559, `worldAge` 2.326962471008301 (`loop.first_world_age`); the last frame the driver read, seq 18453, `worldAge` 6.106488227844238, game minute 786: **226.77154541015625 game minutes** (`grade_e4.game_minutes`), the stop's own frame, seq 18450, 226.74476623535156. The planner ran from line 1 (its frame seq 302, game minute 562) to line 1680 (seq 18420): 223.28641891479492 game minutes, 1680 ticks. **The health read 100 on all 8534 frames, and `bleeding`, `scratched` and `bitten` 0 on every one**; `attackers` read 1 on 10 frames and 2 on 2, `hitReaction` empty on all, `dragDown` false on all. The earlier chain and LLM first sessions each ended in a death, at game minutes 592 to 754 (#4240, #4305), F2's the longest at 195.1186180114746 game minutes (#4305).

## 2. The session

**Where it went.** Over the frames to seq 18453 the position moved 1323.62748476208 tiles of frame-to-frame path. It began in building 2's living room at (10721.5, 10630.5), looted building 2, walked east toward the fence row and met fight 0 there, walked south and east along y 10666 to 10668, fled fight 1 north, looted building 5 from its back deck and stood at its locked door (§ 6), fled fight 2 by building 6 at x 10776 to 10783, and from game minute 622 walked east and south through the woods to (11246.4833984375, 11148.5), **737.5171649765088 tiles from the start and 699.1491929664311 from the nearest building square**, at the cap (§ 7).

**What the planner did** (`decision.log`, 1680 ticks, 393 sends; branch `goal` on 1531 lines, `threat` on 143, none on 6: lines 15, 346, 696, 959, 960 and 961):

| `decision.log` lines | game minutes | what ran | sends |
|---|---|---|---|
| 1–15 | 562–564 | the goal branch: `LootBuilding` 2 (loop.goals[0]) | 3 |
| 16–64 | 564–571 | the goal branch: walks east toward the fence row, scans between | 11 |
| 65–108 | 571–577 | fight 0: two stance legs, the `many` flee, its shelter walk to building 2 stalled at the fence row's locked gate (§ 3) | 5 |
| 109–201 | 577–589 | the goal branch: walks south, then east along y 10666 to 10668 | 26 |
| 202–210 | 589–590 | fight 1: the `many` flee north | 2 |
| 211–235 | 590–593 | the goal branch: walks north to building 5 | 5 |
| 236–346 | 594–608 | the goal branch: `LootBuilding` 5 (loop.goals[30]), the stand at its locked back door (§ 6) | 9 |
| 347–356 | 608–610 | the goal branch: `ExploreToward` (10764, 10633) | 2 |
| 357–446 | 610–622 | fight 2: the `many` flee from the door, the run legs against a blocked edge, two stance legs (§§ 3, 4) | 17 |
| 447–1680 | 622–786 | the goal branch: `ExploreToward` walks east and south into the woods to the cap (§ 7) | 313 |

The actions by type and end (`loop.actions`, 393 rows, a2–a394): `walkTo` 233 (232 the goal branch's, 1 the threat branch's run walk a19), done 226, failed 4 `stuck` (a19, a350, a372, a373) and 3 `superseded`; `scan` 125, done; `steer` 19, every one the threat branch's at `gait` `run`, done 13, failed 6 `superseded`; `interact` 12, every one a loot, done 3, failed 8 `not adjacent` and 1 `no match`; `aim` 4, done 1, failed 3 `superseded`. No `attack`, `consume`, `fill`, `bandage`, `rip`, `wash`, `climb`, `drop` or `sleep` was sent (the `equip` a1 is the kit's, the `stop` a395 the loop's).

**The loot.** Building 2's three loots (a2 `food` moved 2, a3 `no match`, a4 `bandage` moved 1) added `Base.PorkChop` and `Base.MuttonChop` (seq 335 and 347) and `Base.Bandage` (seq 477); building 5's first loot (a54, `food`, moved 1) added `Base.Bacon` (seq 2751); its eight others failed (§ 6). `loop.goals[0]` and `loop.goals[30]` ended `done` `looted`. The two `door` events opened building 2's door at (10721, 10638) (seq 574) and the fence row's gate at (10747, 10642) (seq 1101). The load read level 0 on every frame.

**The goals** (`loop.goals`, 262 rows, every one `source` `scripted`): 2 `LootBuilding` (buildings 2 and 5) and 260 `ExploreToward`, of which 253 ended `done` `arrived`, 3 `failed` `stuck`, 3 `superseded` (two by a steer, one by an aim) and 1 ran at the cap. Buildings 3 and 6 held container squares in the kept map (19 from seq 601, 5 from seq 3413) and no goal named either; why the source passed them is not read here.

## 3. The fights, all fled

`loop.fights` holds three runs of the threat branch (`e_grade.txt`: fights 3, ended 3, fled 3, stand-offs 0; `flee` counts the ticks logging each reason):

| fight | lines | game minutes | ticks, fight ticks, sends | `held` max, `threats_max` | `flee` | first send | end |
|---|---|---|---|---|---|---|---|
| 0 | 65–108 | 571–577 | 44, 7, 5 | 3, 2 | many 22, steps 8, held 5, flip 2 | `aim` a16 on zombie 564 at 5.19389096652908 | 577, health 100, `goal` |
| 1 | 202–210 | 589–590 | 9, 0, 2 | 4, 2 | many 8, flip 1 | `steer` a47 (`many`, `listed` 4) at 5.781076129670065 | 590, health 100, `goal` |
| 2 | 357–446 | 610–622 | 90, 7, 17 | 7, 5 | many 82, flip 1 | `steer` a65 (`many`, `listed` 7) at 5.888598996750521 | 622, health 100, `goal` |

**Every fight ended in the `many` flee and none sent an attack.** Fight 0 opened in the stance on zombie 564 (a16, line 65), which gave way after three ticks to the `many` steer a17 (line 68, `listed` 4, the nearest 3.063008324612107); a second stance leg on zombie 534 at 8.075609593957962 tiles (a18, line 75) gave way at line 79 to the `many` flee's shelter walk to building 2 (a19, `shelter` 2, `step` `approach`, at a run). Fight 1 never stood: its first tick was the `many` flee (line 202). Fight 2 began on the deck of building 5 (line 357, `listed` 7) and ran 13 run steers before its two stance legs on zombie 587 (a78 at line 432, 6.6892615877004005 tiles; a79 at line 437, 6.521449132083193), the second giving way at line 439 to the `many` flee (`listed` 4).

**Within the bat's reach.** A listed zombie stood within the bat's `reach` 1.125 on 27 frames: 7 at game minute 574 (seq 1132–1139) during fight 0's shelter walk, zombie 533 passing at 0.34301262577052216 tiles at seq 1134 while the walk's ticks logged `yield` `many` (lines 87 and 88), and 20 at game minutes 617–618 (seq 3922–3962) in fight 2's run steers a75 and a76, the nearest 0.5441688064759007 at seq 3926, seven of the ticks over them logging `group` `hold` (lines 413–416 and 418–420). The 12 frames reading `attackers` above 0 are among them (seq 1132; 3923–3931, 3958–3960). On none of those ticks did the branch fight: each was a `many` flee by its `why`.

**The shelter walk at the locked gate** (fight 0). The run walk a19 to (10721.5, 10638.5) went east through the open gate at (10747, 10642), back west along the fence row's south side past zombie 533, and **stood 6.0 s (seq 1188–1262) at (10732.310546875, 10642.35546875), the fence row's gate square, which the kept map had read locked from seq 515**, while 533 closed from 9.316552682041696 to 5.860172878618631 tiles; it ended `failed` `stuck` at seq 1263 and line 105 ended the shelter `shun` for a `many` steer. E6's held flee stood on the same square (#4325), and F2's first fights met a zombie on it (#4316).

**The run legs against a blocked edge** (fight 2). **The four run steers a71–a74 (lines 384–405, vectors south-southeast) moved 0.0615234375, 0.08984375, 0.01171875 and 0 tiles over 31, 30, 31 and 30 frames, `running` and `moving` read on 30 or 31 of each, at (10782.7744140625–10782.8828125, 10645.55078125–10645.6123046875), against the north edge of (10782, 10646), which the kept map had read blocked and not hoppable from seq 2516**, while the nearest zombie closed from 7.7744770524274305 tiles (a71's first frame) to 2.2745868098040294 (a74's last) and the held count read 5 or 6 (6 on lines 384 and 389–411, 5 on 385–388); the flee's `why` logged `stuck` true from line 391. The next leg, a75 (line 412), moved 2.599301200272167 tiles west and a76 9.654448060231992 tiles north. Shot 36 (index seq 3955, line 419) shows the character beside a chain-link fence among zombies, one at its side, `x: 10779 , y: 10645`. By inference the flee's leg chooser read no known edge, as in Plan 23's first chain session (research-notes "The flee into a known edge").

**After each flee: the goal walked on with the zombies behind it.** By the code the hold radius falls from 10 to 6 when the threat policy ends, and the goal branch runs on a tick with no threat held. **After fight 0, the goal walk south began at line 109 with zombie 533 listed 10.63050618829875 tiles off, and on 14 of the 38 goal lines 109–146 it read within 10 tiles, 7.9855142217366994 to 9.918560285382432; after fight 2 (line 447, zombie 587 at 10.4062621428731), zombies 580 and 581 read within 10 tiles on 13 of the 54 goal lines 447–500, 8.354633448268789 to 9.656540159538674; after fight 1 none did.** Over the session 188 goal lines' frames listed a zombie within 10 tiles and none within 6. Angus's "forgets zombies are nearby when he jogs away": the frames have the zombies listed and the goal branch's ticks reading `held` 0 at about 8 to 10 tiles (7.9855142217366994 to 9.918560285382432).

## 4. The stance's second live reading

| aim | fight, line | target, distance at the send | end | frames: `aiming`, `forceAim` | target first → last | `dir` |
|---|---|---|---|---|---|---|
| a16 | 0, 65 | 564, 5.19389096652908 | `superseded` by the steer a17 | 16: 15, 16 | 5.013922761971179 → 3.063008324612107 | NE |
| a18 | 0, 75 | 534, 8.075609593957962 | `superseded` by the run walk a19 | 19: 19, 19 | 8.242828257454159 → 8.301541842451623 | E |
| a78 | 2, 432 | 587, 6.6892615877004005 | `done`, `held` true, `heldFrames` 121, `ticks` 121, `d` 0.13515427428107968 | 20: 20, 20 | 6.760020200823334 → 6.750925777668631 | W |
| a79 | 2, 437 | 587, 6.521449132083193 | `superseded` by the steer a80 | 10: 10, 10 | 6.406555466231017 → 5.338551362811952 | W |

**On the four legs' 65 frames `forceAim` read true on all 65 and `aiming` on 64, the one false the first frame of a16 (seq 960)**, as on the probe's legs; a78's result read `heldFrames` equal to `ticks`, 121 of 121. `aiming` read true on 64 frames of the session and `forceAim` on 65, all of them these; no other frame read either. Every leg had a zero vector (the target beyond `KEEP_R` 2.5 at every send), so none backpedalled, and none stood within reach. Shot 6 (index seq 988, line 67, during a16) shows the character with the bat raised, facing a zombie beyond a wooden fence, `x: 10754 , y: 10639`; shot 38 (index seq 4059, line 433, during a78) the character with the bat raised beside a house's wall, `x: 10778 , y: 10626`. `grade_e4.stance_held` (`frames_aiming` 0, `frames_force_aim` 0 of `frames` 3000) reads the driver's kept frames, `loop.last_frames`, seq 11649–18453, which hold none of the legs (Do not cite as the session's).

## 5. The steers: no sprint, and the short glides

**No sprint.** All 19 steers were sent at `gait` `run` (fight 0: a17, a20; fight 1: a47, a48; fight 2: a65–a77, a80, a81) and the run walk a19 at a run; **`sprinting` and `forceSprint` read false on all 8534 frames**, `running` true on 589 and `forceRun` on 595. The endurance read at least 0.8585305213928223. Ruling P24-O read live: against E6, where 13 steers were sent at `sprint` and `sprinting` read true on 22 frames (#4326).

**The glides** (an inference, as in E6). `grade_e4.glides` reads 0 runs over the kept frames (seq 11649–18453, no fight). Over all 8534 frames, a run of consecutive frames reading `moving` false while the position stepped more than 0.1 tiles came 239 times, 194 of 2 frames, 37 of 1, and the longest 6 frames (seq 1046, 1.9372264935455727 tiles), each run of 4 to 6 frames at the end or the turn of a run steer (seq 1046, 2377, 3567, 3720, 3960, 4254); no run of ten frames came, against E6's six (#4326), and no wound rose. Whether any was a stumble the frames do not say.

## 6. The doors

**Building 5's back door.** The `LootBuilding` 5 goal's first loot (a54, line 236) walked the character to the deck behind building 5 and moved one item. **From seq 2824 to seq 3490, 557 frames over 55.6 s (game minutes 595–610), the position read (10770.4521484375, 10633.451171875) on every frame: the square (10770, 10633), outside the building, whose record the kept map had read from seq 2716 with a closed, locked door and its north and west edges blocked, the kitchen square (10769, 10633) of building 5 to its west.** On the 112 decision lines whose frames read that position (lines 246–357), the goal branch sent the loots a56–a62 (a55, sent at line 241, failed there too), a scan and the walk a64: **each of the eight loots a55–a62 ended `failed` `not adjacent`** (a55 7.895 s after its accept line, the others 5.993 to 5.996 s), its frames reading `ISWalkToTimedAction` on 0 to 22 and `moving` on 0 to 18 (the Lua's loot walks to a free square beside the container before it queues the transfer, and fails `not adjacent` when that walk fails; code), and the walk a64 toward (10764, 10633) moved 0 tiles before fight 2's steer superseded it. The `LootBuilding` goal then ended `done` `looted` (none answered after a loot). The `me.dir` read `W`, toward the door, on the frames. Shot 26 (index seq 2906, line 256) and shot 30 (index seq 3351, line 336) show the character on a wooden deck facing the building's door, the kitchen beyond it, `x: 10770 , y: 10633`, the same scene in grabs 40.17172338867187 s apart (their `pyMs`, a span). No `door` event came at that square and no `interact` `open` was sent; by inference the loot walks' path ran through the locked door. Fight 2's `many` flee began from that square (line 357, `listed` 7), five zombies having been listed within 10 tiles on the goal lines 340–356 while `held` read 0.

**The fence row's locked gate** (§ 3): 6.0 s on fight 0's shelter walk.

Angus's "stuck trying to open doors": the frames read the stand at building 5's locked door, 55.6 s, and the gate's 6.0 s; what the screen showed in the stand (an open attempt's animation) the frames do not carry, and the two shots show the character standing.

## 7. The woods

**The last frame within 40 tiles of a building square was seq 4790 (game minute 628, 39.85456129411476 tiles); from it to the driver's last read, seq 18453, the character walked 988.240818359983 tiles of path over 158.0072021484375 game minutes with no building square within 40 tiles**, no building square being first read after seq 4108. The goals from `loop.goals[41]` on, 221 rows, every one an `ExploreToward`, named squares 42.50294107470682 to 701.2777623737973 tiles from the nearest building square; 217 arrived, 3 failed `stuck` (a350 at game minute 758, a372 and a373 from one square at 772 and 774) and 1 ran at the cap. **No zombie was listed on any frame after seq 4459 (game minute 624), and the frames' `zombiesSeen` read 0 after seq 11998 (game minute 710)**, so the threat branch never ran after line 446. Shot 60 (index seq 8959, line 848) shows the character walking among broad-leafed trees with the bat, `x: 11021 , y: 10729`; shot 99 (index seq 17870, line 1630) the character in dense woods among pines and rocks, `x: 11225 , y: 11131`.

Angus, at the screen: once out of its building's surroundings the character wandered aimlessly in the woods with nothing to interact with. The goal layer's source picks the kept map's unexplored edge when no building with a known unlooted container answers (code); here the walks to it took the character 699.1491929664311 tiles from any building it had read.

## 8. The care, the need, the night

- **Care.** No `care` line: no part bled on any frame; the care `why` read `bleeding` `[]` and the held `bandage` 1 on all 1523 lines from line 15 that were not threat lines.
- **The need.** **Thirst first read over `THIRST_T` 0.12 at seq 17272 (game minute 771) and on 114 decision lines (1567–1680), each reading the need branch's `why` `{"fill": {"want": "container"}, "item": null, "mark": "water"}`**: no water item and no container held, so the branch answered nothing and the goal walked on. The maxima over the frames to seq 18453: thirst 0.1280551701784134, hunger 0.1201966404914856 (against `HUNGER_T` 0.15), fatigue 0.1568318009376526.
- **The night.** The hour read 9.3269624710083 at the first frame and 13.106488227844238 at seq 18453; `loop.night.wants` 0.

## 9. The shots

**What was taken.** The shot taker (`shots.py` at `425fc6dc`, the guard's first live session) wrote 102 index lines: 81 grabs (`loop.shots.n`) and 21 skipped. **Of the 21, 9 read `skipped` `not foreground`** with the window found and another window in front, **its class named in `other_class`: `Chrome_WidgetWin_1` on 8 (shots 31–35 and 77–79) and `WinUIDesktopWin32WindowClass` on 1 (shot 29); 12 read `skipped` `no window`** with `window.found` false (shots 82–90, game minutes 734–755, and 100–102, 782–786). Nothing was grabbed on those 21. The 81 grabs read `window.found` true, `rect_source` `dwm` and one rectangle, hold 81 distinct sha256, and came 35.324951171875 to 588.284912109375 ms after their index frame. So no shot shows fight 2's run legs against the edge (shots 34 and 35 skipped) or the last four game minutes. Against E6, where eleven grabs held another application's window (#4331): a skipped mark has no image, and only grabs with `window.found` true were opened at this write-up.

**The cited shots** (the index's `seq` and `decision_line`):

- Shot 6 (seq 988, line 67, during the stance leg a16): the character with the bat raised, facing a zombie beyond a wooden fence by a house, `x: 10754 , y: 10639`.
- Shot 26 (seq 2906, line 256, the door stand): the character on a wooden deck at the building's back door, the kitchen beyond, `x: 10770 , y: 10633`.
- Shot 30 (seq 3351, line 336, the door stand): the same scene and pose, `x: 10770 , y: 10633`.
- Shot 36 (seq 3955, line 419, after the run legs against the edge): the character beside a chain-link fence among zombies, one at its side, `x: 10779 , y: 10645`.
- Shot 38 (seq 4059, line 433, during the stance leg a78): the character with the bat raised beside a house's wall, `x: 10778 , y: 10626`.
- Shot 60 (seq 8959, line 848): the character with the bat among broad-leafed trees, `x: 11021 , y: 10729`.
- Shot 99 (seq 17870, line 1630): the character among pines and rocks in dense woods, one moodle icon at the screen's right edge, `x: 11225 , y: 11131`.

A shot's `seq` is the latest frame the loop had read when it marked the shot, not the frame on the screen (Do not cite as the frame shown).

## 10. The cost, what the frames cannot say, the host

**The per-tick cost** (`loop.cost`; `e_grade.txt`): p50 0, p99 2, max 6 ms, `over5` 473 (restricted: the run's do-not-cite rows).

**What the frames cannot say.**

- **What the screen showed at the door**: the frames read the stand and the failed loots, not an open attempt.
- **Why the scripted source passed buildings 3 and 6**: the view's fields are not logged.
- **Whether a short glide was a stumble.**
- **The hand-over from the stance to a swing**: no attack was sent.

**The host.** One Windows host; free memory 14.41 GB at the gate, 1.55 GB at ready, 15.3 GB after teardown. Every millisecond above is this host's.

**The epoch-ms leaves** (wildcard): `*wallMs`, `*Wall`, `*_wall`, `wall_*`, `*.wall`, `epoch_ms_*`, `*PyMs`, `*pyMs`, `*_ms` and the loop's `*S` keys anywhere in `e_day_7.json` (`loop.startPyMs`, `loop.t_loop0_ms`, `loop.wallS`, `stop.wallS`, `loop.stopped.wallS`, `loop.stopped.settleS`, `loop.last_frames[*].wallMs`, `loop.fights[*].startS`, `loop.fights[*].startWall`, `loop.fights[*].end.endS`, `loop.actions[*].sentS`, `loop.actions[*].endedS`, `loop.goals[*].startS`, `loop.goals[*].endS`, `loop.needs_pairs[*].frameWallMs`, `loop.last_decisions[*].wall`, `readings.hello.hello.wallMs`, `readings.kit.weapon_frame.wallMs`, `server_launch_wall`, `server_started_wall`, `session_ready_wall`, `teardown_started_wall`, `wall_seconds` and the like), the `wallMs` of every line of `state.log` and `state.1.log`, every `decision.log` `wall`, the `wallMs`, `pyMs` and `grab_ms` of every line of `shots/shots.jsonl`, and `timeline`, `phase_walls`, `client_seen`, `memory[*].wall` and `memory_wait[*].wall` are this host's clocks, cited only as a difference within this run (a span, a duration, a pairing), never as a reading.

## Do not cite from this file

The first eight rows are the run's rows in `docs/reference/do-not-cite.csv` (committed with the artifact); the rows after them are this guide's.

| Key | Value in the file | Why not |
|---|---|---|
| `loop.cost.*` and the frames' cost group as a per-tick cost at 10 Hz | per tick | The 1 ms clock; a 10 Hz frame's `tickMs` samples the tick before the frame tick (ruling P22-4); cite the X4 sessions for the base's cost. |
| every free-text reason, detail and error string (`stop.detail`, `actions[*].reason`, a string-valued `why` field of the decision log) | — | The driver's, the planner's or the Lua's message, not a reading; the decision log's numeric, id and boolean `why` fields and the planner's fixed-value `why` fields are readings. |
| `constants`, `preboot`, `profile`, `fixture`, `argv`, `memory`, `memory_wait`, `world_changes`, `steps`, `verify`, `chain` | the driver tables | Written before or around the run, or the bus's raw steps; not readings. |
| `loop.lineage` | null | Session 1 of a chain on the fixture agent has no previous artifact. |
| `loop.last_decisions` | ten `decision.log` lines | A log excerpt, not a reading; cite `decision.log` by line. |
| `shots/shots.jsonl` `grab_ms` and `pyMs` as the capture's cost or clock | per shot | The host's clock and the grab's own duration under the GIL. |
| `grade_e4.kills.engine` as the session's kills | null | The engine's count is the death event's `zombiesKilled` and the session did not die; the planner's count (distinct `targetDead` ids, 0) is a lower bound. |
| `grade_e4.glides` as trips | per run leg | A glide is a second of `moving` false inside a run leg, an inference; the frames carry no fall field (the E6 guide). |
| `grade_e4.stance_held.frames`, `frames_aiming` and `frames_force_aim`, `grade_e4.care.stance.frames` and `frames_aiming`, `grade_e4.wounds.*` and `grade_e4.glides.*` as the session's frames | 3000; 0 | Read over `loop.last_frames`, the driver's last 3000 frames (seq 11649–18453, game minutes 706–786), which hold no fight and no aim leg; the four aim legs read `aiming` on 64 of 65 frames (§ 4). |
| `grade_e4.care.stance.moved` as a backpedal | 0.13515427428107968 | The one `done` aim leg's `d`, a standing leg's drift; no leg backpedalled (§ 4). |
| `grade_e4.load.max_ratio` as the session's | 0.23791664838790894 | Over the kept frames only; the load read level 0 on every frame (§ 2). |
| `state.log` alone as the session | seq 1–15639 | It ends at game minute 752; seq 15640–18466 are in `state.1.log` (§ 0). |
| `loop.shots.n` as the index's lines | 81 | The grabs; the index holds 102 lines, 21 skipped (§ 9). |
| `decision.log` `inputs.held` and `inputs.nearest` as the zombies near the character | per tick | Counted within the hold radius, 6 outside a threat policy; goal lines reading `held` 0 listed zombies about 8 to 10 tiles off (7.9855142217366994 to 9.918560285382432) on the frames (§ 3). |
| `shots/shots.jsonl` `seq` and the index's `gameMin`, `health`, `branch`, `flee`, `fight` and `goal` as the frame a shot shows | per shot | The latest frame the loop had read at the mark; the grab follows on the worker (§ 9). |

## Corrections

**To the record written before this guide** (the stub, the artifacts row, the commit subject `cd7e2b15` and the brief's trace; each checked against this folder's files):

1. The artifact as committed lacks `state.1.log`, the log's rotation: `state.log` ends at seq 15639 (game minute 752), so the session's last 34 game minutes and the stop are not in it. This write-up copies the run folder's `state.1.log` byte-identical into the folder (staged, for the controller's commit) and names it in the files table; the artifacts row's Files column should name it.
2. They read "102 shots, of which 21 were skipped by the guard (`skipped: "not foreground"`: another window was in front of the client)": 81 were grabbed (`loop.shots.n`); of the 21 skipped, 9 read `not foreground` and 12 `no window` (`window.found` false, no window in front named) (§ 9).
3. They read "19 `steer` legs (all at a run: no sprint)": correct as sent; the frames confirm it, `sprinting` false on all 8534 (§ 5). The row's "3 fights fled" is right; that none sent an attack and every one ended in the `many` flee is the reading (§ 3).
4. The brief's trace asks for the door interactions among the 12 `interact`: every one was a loot, none an `open`; the door reading is the 55.6 s stand at building 5's locked back door with eight loots failing `not adjacent`, and the 6.0 s at the fence row's gate (§§ 3, 6).
5. The commit subject's "227 game minutes" rounds `grade_e4.game_minutes` 226.77154541015625, which runs to seq 18453, the last frame the driver read (§ 1).
6. The artifacts row names the library at `425fc6dc`: that is `shots.py`'s commit; `preboot.driverlib_commit` reads `68c18eee`, and the planner's files are at `24987f2a` and `f774248d` within the base's tree `0f7881a1` (the header).
7. `grade_e4`'s frame readings (`stance_held`, `wounds`, `glides`, `care.stance.frames_aiming`) cover only the driver's last 3000 frames, game minutes 706–786, after every fight; its report line "0 of 3000 kept frames aiming" is not the session's (§ 4).
