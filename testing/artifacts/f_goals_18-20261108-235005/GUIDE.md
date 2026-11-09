# `f_goals_18-20261108-235005` reading guide

**`f_goals_18-20261108-235005/f_goals_18.json`** (with `state.log`, `decision.log`, `goals.log`, `f_grade.txt`, `shots/shots.jsonl` and `client-console.txt`) — produced by `testing/agent/drivers/f_goals_18.py` at `driver_commit` `a5747171` (`f_goals_17.py` copied under its own key, Plan 32 Task 7a), on the driver library `testing/agent/driverlib/` at `1cc4c36f` (`preboot.driverlib_commit`), which imports `testing/experiments/xlib.py` (`47dd2d27`) and the agent base under `testing/agent/base/` within HEAD `a5747171` (`preboot.commit`; the planner `testing/agent/base/planner` at `d31ca7d0`: **Plan 32's proven composition, the controller's ruling of 2026-11-08 under P32-R**: the FACING snap in the meet reflex and the ladder's aim leg with `K.PRESS_FACING` `unaimed_snap` (Task 4, `f9dfdbd3`, `d848bba0`), the four coward rules `POINT_BLANK_FIGHT`, `PAIR_NEAREST`, `CARE_COMMIT` and `STRAIN_BOUND` on by default (Task 5, `c739815d`, `de965a55`, `26c76166`, `ac20d55c`, the flip `d31ca7d0`), the window glass gate (Task 6, `80c69f70`, `ab73cc44`, `60b79f16`), the Dress on by default since Plan 31; the `claude` CLI 2.1.319 with model `sonnet`, the live probe `ok` exit 0 (`preboot.claude_answers`); `agent.base.grades.x2` at `2003d67d` carrying `grade_x2`, `grade_x1` under its `base`), with `pzt` at `2f2b1fff` and the harness Lua `PZTestKit` at `edcaf2e6` (`preboot.harness_lua_commit`). The agent mod `testing/PZAgent/PZAgent` loaded by path from the tree at `a5747171`, its Lua last changed at `ab73cc44` (PZA/1.11: the facing ring `fwdAngle`, `twist` and `aimAngle` in `me`, the `probe` act, the FACING table, the Map's `windowPortal` record and the window act's `clear`), its hello reading `mod` `1.11`. Fixture `agent` (build `42.21.0`); profile `testing/profiles/agent.toml` (PZTestKit + PZAgent, user `admin` on a `-debug` client, the 90-minute day); launched with no argument (`argv` `[]`: session 1 on the fixture `agent` with no previous artifact). Graded by `grade_x2` inside the artifact and through `testing/agent/drivers/f_grade_14.py` (`2003d67d`) beside the logs; the session is a report with no gate.

**Plan 32's F18, the facing composition's evidence LLM session** (the plan `docs/superpowers/plans/2026-11-08-plan-32-the-facing.md`, Task 7; the spec `docs/superpowers/specs/2026-11-08-plan-32-the-facing-design.md`, § 2 its success criteria), the first evidence session of the snap, the coward rules and the glass gate. The planner is `Survive(source=LLMSource(ScriptedSource()))`. **By the two metrics (rulings P24-Q and P28-M) the session killed three zombies, all by the meet reflex, and took four runs of hit reactions, the reflex's three hit-step runs each falling on one of them, so four attacks landed by the union, 1.3333333333333333 a kill; the scorecard's split of the same runs reads 16 segments; the character died by a drag-down at game minute 617, 58.048553466796875 game minutes after its first frame** (§ 1). **The character stood in one place from game minute 603 to its death: a finish at a fallen zombie held its `head` step 14.553 s with no press while three zombies walked in from 11.641470859185226 to 11.997415462958367 tiles; the planner's pin then switched among four zombies on twelve melees, eleven superseded and none killing; the zombie it had left at 0.2690059542655945 health rose as a crawler under the character, was never targeted again and bit twice; the drag-down guard's `many` flee sent five run steers on which no frame read the character moving** (§ 3). **The snap held the body on the target at every press: the press leaf's own body offset read under 1.617660401322909e-05 degrees on all 60; through the stance the body read beyond 30 degrees of the target only while a melee's stomp or `head` step stood over its fallen target at 0.0027621358640099515 to 0.005694288959809864 tiles** (§ 4). **The coward rules cut the fleeing to 25 lines and 3.133220672607422 of 54.74802017211914 game minutes, with no `strain` flee** (§ 5).

## 0. The run

- **Wall.** 283.6 s (`wall_seconds`). The `timeline` clock reads the server started at 16.5 s (pid 530112, `server_pid`), the client launched at 16.6 s and ready at 52.3 s, the bat added by rcon at 58.0 s and the client quit at 275.8 s.
- **Hello.** `readings.hello`: `ok` true, `proto` `PZA/1`, `mode` `append`, `build` `42.21`; the hello line (`state.log` seq 1): `mod` `1.11`, `rate` 10, 25 capabilities, `melee`, `probe` and `sneak` among them.
- **The kit.** `readings.kit.spawn.after.id` 1079815874, a `Base.BaseballBat`; equipped by a1 (`state.log` seq 285); every frame reading a weapon (2074 of the 2223) reads it at `reach` 1.125, `cond` 15 on 1520 and 14 on 554.
- **Pipe health.** `frames.gaps` 0, `frames.bad` 0, `frames.lua_errors` 0, `frames.parks` 0, `admin_lua_error` false, `server_error_count` 0.
- **The stop.** `stop.reason` `death`, `stop.wallS` 207.45237350463867 of loop wall time, `stop.gameMin` 617; the death event at `state.log` seq 3669 (game minute 617, `health` 0, `via` `hook`, `zombiesKilled` 3, at 10740.236328125, 10651.1279296875); `survived` false and `game_minutes_alive` 58.048553466796875 (`f_grade.txt`), from the first frame to the death event.
- **Frames.** One file, `state.log`, no rotation: decoded with `pza1.py` (`decode`, `merge_delta`) through `agent.base.replay_decisions.read_record` (`agent.base.transport.files.FileTransport`) on a copy: 3727 lines, line *n* seq *n*, 2223 frames, seq 10–3727, every consecutive pair six ticks apart; the driver read 2192 (`frames.n`). The grade's clip at the loop's stop (`clip`) cut 57 state lines and 32 frames past 207.45237350463867 s; the frames after the death event (seq 3670–3727) read `body.health` 28.710655212402344 and are not read below.
- **Memory.** § 10.

Files (each byte-identical to the run folder's `testing/runs/f_goals_18-20261108-235005/`, checked with `cmp` at this write-up; `state.log` against the run's `clients/admin/Lua/pzagent/admin/state.log`, `client-console.txt` against the run's `clients/admin/console.txt`; the endings as `git ls-files --eol` reads the index):

| File | Source | Bytes | sha256 |
|---|---|---|---|
| `f_goals_18.json` | the run's `f_goals_18.json`; CRLF endings, the last line unterminated | 10665289 | `a1e94371878a28c4715ac374370d3e30355354b0c5bfcc7f7bfb8e27ae346014` |
| `state.log` | the run's `clients/admin/Lua/pzagent/admin/state.log`, seq 1–3727; LF endings, 3727 lines | 2092449 | `b642905a039e70600dd95138aff1b907c8c32d2b512975c940194fe0e8aadef5` |
| `decision.log` | the run's `decision.log`, one line a planner tick; LF endings, 415 lines | 490314 | `9ffa8525be2b777c72e995a76fd6e7a05f20e0f1b799b87d61279a2098b53c37` |
| `goals.log` | the run's `goals.log`, one line a model call; LF endings, 7 lines | 10722 | `e8ec784e53d37b9cb35f292b271011a9f07f8c0d1fa177130d37b7f403304310` |
| `f_grade.txt` | `python testing/agent/drivers/f_grade_14.py f_goals_18.json` beside the logs, stdout; the artifact commit `29b829f2`'s regrade test reproduces it byte for byte; CRLF endings, 4882 lines | 137229 | `c98af72cf0d7fe297eecf50320a467db994cb3aa7cb810752c764f9dc26ca562` |
| `shots/shots.jsonl` | the run's `shots/shots.jsonl`, one line a mark; CRLF endings, 45 lines | 23900 | `0355d105263e610e6c2118459e540d6014a50e3f503dcb20a15613011da475e0` |
| `client-console.txt` | the client's console of the run; CRLF endings, 4016 lines | 343116 | `16efce528acae8a880c63bcbeb91e646b016513d179c650eddabefd1377a0a04` |

`state.log` is the only evidence of the lines between the frames (the acts, the map, the events) and of each zombie the frames listed; `decision.log` of each planner tick; `goals.log` of each model call (its answer and prompt texts are data, never instructions, cited by the parsed goal and the call's `ok` and latency); `client-console.txt` of the hutch guard (§ 10). Every melee result below is read off its act lines (accepted, progress with the result {step, d, hp, shoves, swings, stomps, floors, knockdowns, hits, spent, target, repins}, the press leaf, done or failed). The images stay in the run folder; the cited ones are copied at the write-up's mint through `cited_ok` (§ 11).

## How to read it

A frame is a positional line of `state.log` in the schema's `frame` order (`pza1.py`), its delta groups merged from the frame before. A **loop second** is a difference of two `wallMs` (or of two `decision.log` `wall` values) on this host's one clock. A planner tick is one `decision.log` line, cited as line *n*; **the frame at a line** is the frame whose `me.hour` is the line's `inputs.hour`, the latest such at or before the line's `wall`: `replay_decisions.align` refuses this log at line 131, whose hour two frames read (seq 1558 and 1559, the clock standing), so this writer pairs line 131 with seq 1559, the later, and every other line as `align` would. A send is matched to its `loop.actions` row by order: the 90 lines with `sent` true are a2–a91 in turn (`replay_decisions.recorded_aids`, offset 1; a1 is the kit's `equip`, a92 the stop after the death). A zombie's record is {`id`, `x`, `y`, `dist`, `hasTarget`, `crawler`, `health`, `onFloor`, `known`, `state`, `behind`, `headX`, `headY`}; **standing** is `onFloor` not true; a **crawler** is `crawler` true.

**The facing.** `me.bodyAngle` (`getAnimAngleRadians()`), `me.lookAngle` and, from PZA/1.11, `me.fwdAngle` (the forward direction the code writes) and `me.aimAngle` (the aim vector while aiming) are radians on the world axes; a zombie's **offset** below is the absolute angle between `bodyAngle` and `atan2(dy, dx)` of the line from the character to the zombie on the same frame (`grade_x2`'s own convention). The press leaf (PZA/1.10, PZA/1.11) carries the Lua's own reading at the press: `look_off` and, from PZA/1.11, `body_off` in degrees, and `facing` the snap mode (`unaimed_snap` on all 60 here).

**A press** is a meet press: a `press` leaf on a melee act line, one per press, 60 in all; its kind (`swing`, `shove`, `stomp`) the step it came from and its outcome `grade_x1`'s off the leaf (`killed` hp1 0, `knocked` `knock` true, `lowered` hp1 below hp0, `cut` a `cut_by`, else `nothing`). A **hit** (ruling P28-M) is a run of frames reading `me.hitReaction` non-empty; the **union** joins those runs with the reflex's own `hit` step runs (`landed_hits.steps`); a **wound** a rise of `body.scratched`, `body.bitten` or `body.bleeding` on a frame. A **kill** is a `zombie_dead` event. Part *i* is `body.parts[*].i`.

**The composition** (code at `d31ca7d0`, not readings). `POINT_BLANK_FIGHT` fights the nearest standing zombie within `KEEP_R` 2.5 whatever flee the plan would take (`threat.py` `_point_blank`; it skips a zombie `onFloor`, and the drag-down guard, the doorway stand and the sheltered flee keep their own rows ahead of it); `PAIR_NEAREST` pins the Fight on the nearest standing zombie when two or more are within `KEEP_R` and one stands (`fight.py` `_pair_pin`); `CARE_COMMIT` takes one walk away and then yields the threat branch to a wanted care action (`care_yield.py` `_care_commit`; it reads standing zombies only); `STRAIN_BOUND` lets the `strain` flee go only at `stats.endurance` at or under `STRAIN_ENDURANCE` and never with exactly one standing zombie within `DANGER_R` 6 (`threat.py` `_strain_flees`). The drag-down guard (`_drag`, ruling P24-A (h)) flees `many` with the group steer once `me.attackers` reads `DRAG_DOWN_N` − 1 (2) or more, ahead of every row but the doorway's.

## 1. The kills and the hits, the two metrics

**Three kills.** Three `zombie_dead` events, at game minutes 583 (13617), 589 (13618) and 600 (13652) (`state.log` seq 1855, 2226, 2880); `grade_x2.kills` reads `planner` 3, `events` 3, `agree` true, `melee` [13617, 13618, 13652] and `ladder` []; `kills_matched.planner` 3 with `unmatched` []. Each was a meet stomp: a38's in finish mode at 0.007109482313750506 tiles, a48's in strike mode at 0.005524271728019903 and a66's in finish mode at 0.009003461384075085 (`meet_presses.rows`). The first two came within `DOOR_KILL_S` after the `stance_open` logged at the door 10747,10642 (`door_held`, [inference] in its report line; § 7).

**The hits.** Four runs of frames read `me.hitReaction` non-empty (`grade_x2.hits`: `runs` 4, `kinds` {`Bite` 1, `CrawlerBiteLEFT` 2, `CrawlerBiteRIGHT` 1}, by each run's first frame): seq 1592–1620 `Bite`; 3385–3425 `CrawlerBiteLEFT`, then `BiteDefended` and `CrawlerBite`; 3515–3536 `CrawlerBiteRIGHT`; and 3546–3666 `CrawlerBiteLEFT`, then `Bite`, `CrawlerBiteLEFT`, `Bite`, `CrawlerBiteLEFT`, `BiteLEFT`, `Bite`, `BiteLEFT`, `Bite`, `CrawlerBiteLEFT` and `EndDeath` from seq 3625 to the run's end. The reflex's own `hit` steps came in three runs (`landed_hits.steps` 3; ten progress lines): a81's from seq 3383, a83's from 3514 and a86's from 3545, each one or two lines before the first frame of the run it fell on, so the union counts the four runs (the grade's join is restricted as a frame reading; the count here is read off the runs and the act lines). Hits per kill 1.3333333333333333 (`hits.per_kill`); 12 wounds on 11 frames (`hits.wounds`, `hits.wound_frames`); `hits_in_melee` `inside` 3, `outside` 1.

**The scorecard's 16.** `landed_hits.runs` reads 16: `grade_x1.reaction_segments` splits a run wherever the reaction type changes between two frames, up to an `EndDeath`, whose segment runs to the run's end (`x1.py`, code): 1 for the first run, 3 for the second, 1 for the third and 11 for the fourth (ten types, then `EndDeath`). So the frames' four runs and the scorecard's 16 segments read the same frames: a run is one stretch of reaction, a segment one reaction type within it; the two differ by the 12 type changes inside the second and fourth runs, the last run's 11 segments landing on a character held among four zombies (§ 3).

**Against the earlier sessions.** F17: ten kills with four attacks landed by the union, alive at the 840 s cap (#4692); F15: no kill with eight (#4669).

## 2. The wounds, each traced

**12 wounds on 11 frames** (this writer's reading of the rises agrees):

| seq, game minute | the rise, the part | what preceded it (the line, the gait, the distance, the facing) | the zombie |
|---|---|---|---|
| 1592, 579 | scratched 0→1, part 2; `Bite` | the threat branch's route walk a34 (line 122, `walkTo` at a walk to 10747.5,10643.5 through the door at 10747,10642, `route` and `blocked_edge` in the line, target 13617 at 9.06660426366125 tiles), held on lines 123–135 with nothing else sent; line 128 logged `door_held` `stance_open` (`n_behind` 1) and sent nothing; 13617, reading `thump`, closed from 1.4434934974473739 tiles (seq 1540) to the bite, the body 48.41843443021992 degrees off it, the character walking; the door event at seq 1618 read the door open | 13617 at 0.24118721416740158, `thump` |
| 3385, 611 | bleeding 0→1, part 13; `CrawlerBiteLEFT` | the shove-mode melee a81 at 13653 (line 370), its `hit` step from seq 3383; the body on 13653 (0.0 degrees) | the crawler 13649 at 0.8600106402781315, `attack`, 118.56587444790785 degrees off the body |
| 3515, 613 | scratched 0→1, part 13; `CrawlerBiteRIGHT` | the shove-mode melee a83 at 13651 (line 388), its shove knocked 13651 down (seq 3510), `hit` step from 3514 | 13649 at 0.4325411279781128, 81.23417941122557 degrees off |
| 3561, 614 | scratched 1→2, part 6; `Bite` | the shove-mode melee a86 at 13653 (line 395, sent with 13653 at 2.246871680839538 tiles, `lunge`), in its `hit` steps from seq 3545 with no press; the body on 13653 | 13653 at 0.4932607423798741, `lunge` |
| 3576, 615 | scratched 2→3, part 3; `Bite` | a86's `hit` steps | 13653 at 0.5086990833343952, `attack` |
| 3592, 615 | bleeding 1→2, part 9; `BiteLEFT` | the drag-down guard's `many` flee: the steer a87 at a run (line 402), accepted, the character not moving | 13648 at 0.5033779479878988, `lunge`, 117.82052758727343 degrees off the body |
| 3594, 615 | bitten 0→1; `Bite` | the same | 13648, 13651 (0.5341404093191937) and 13653 (1.5493775748492686) |
| 3625, 616 | bleeding 2→3, part 8; `EndDeath` | the steer a89 at a run (line 408); `me.dragDown` true from this frame, `me.attackers` 3 | 13653, 13651, 13648 at 0.5042969128219389 to 0.5234712048966562 and the crawler at 0.4325411279781128 |
| 3626, 616 | bitten 1→2 and bleeding 3→4, part 1; `EndDeath` | the same | the same |
| 3660, 617 | bleeding 4→5, part 0; `EndDeath` | the steer a91 at a run (line 413) | 13651 at 0.45299238697922156, 13648 at 0.4861771069489894, 13653 at 0.6534655399591186, the crawler at 0.3906372068405211 |
| 3663, 617 | bleeding 5→6, part 4; `EndDeath` | the same | the same, the crawler at 0.3893497249427413 |

**The first wound** came on a route walk at a walk through a door while the zombie it was routed toward thumped at that door: the walk went on 13 lines, the `door_held` decision on line 128 sent nothing, and the bite landed with the zombie at 0.24118721416740158 tiles and the body 48.41843443021992 degrees off it. It was the one run outside a melee span (`hits_in_melee` `outside` 1), dressed by the `bandage` on line 141 (§ 5), 1.9548225402832031 game minutes after the rise (`wounds_dressed.rows`).

**The group's wounds** came from game minute 611 on, all within a tile of where the character had stood since game minute 603 (§ 3): two from the crawler 13649 while the meet pressed at a standing zombie with the body on that one and the crawler 81.23417941122557 to 118.56587444790785 degrees off it; two from 13653 inside a86's `hit` steps; and seven under the drag-down guard's steers, the nearest standing zombie at 0.4469296722046687 to 0.5042969128219389 tiles and the crawler at 0.3893497249427413 to 0.4325411279781128.

## 3. The group and the death

**How the character came to stand among four.** After the third kill (13652, seq 2880, game minute 600) one zombie, 13649, was within 6 tiles. The shove-mode melee a70 knocked it down at seq 2985 and the finish a71 (line 309, game minute 603) walked to it, stomped once at seq 3010 (`hp` 2.8508737087249756 to 2.477198362350464), and from seq 3020 held its `head` step: 15 progress lines to seq 3175, each reading `d` 0.005 and `hp` 2.477198362350464, the planner holding a71 on every line from 310 to 341, 14.553 s by the act lines' `wallMs` (seq 3020 to the failed line at 3181) over game minutes 603 to 607. Over those lines 13648 closed from 11.641470859185226 to 5.825272667523897 tiles, 13651 was listed again at 11.812920134000956 (seq 3085) and closed to 2.247304785612863, and 13653 was listed again at 11.997415462958367 (seq 3110) and closed to 7.937345548313524. From seq 3014 to the death the character stayed within 2.8575755643156535 tiles of where it then stood.

**Twelve melees, none a kill.** From line 342 (game minute 607) to line 395 the threat branch sent 12 melees and one ladder stomp; 11 ended `failed` `superseded` and one (a81) `done` on a `standing` handback. a75's finish at 13649 (which its stomps had taken from 1.6049094200134277 to 0.2690059542655945, the last press cut `superseded`) gave way to a shove at 13651 (line 357); a77's finish at 13651, sent on line 362, to a shove at 13648 on line 363; then the melees went at 13653 (line 366), 13648 (368), 13653 (370), 13648 (385) and 13651 (388), each superseding the last: the lines from 342 to 401 read `pair_nearest` with `n` 2 to 4 and `standing` 1 to 3, its `target` the nearest standing zombie as their distances crossed, and `point_blank_fight` over `many` on lines 351, 357–361, 400 and 401 and over `pair` on 372–392 and 395–399. No line after 356 names 13649.

**The crawler.** 13649 read `crawler` true from seq 3292, at `health` 0.2690059542655945, `onFloor` true; it read `attack` from seq 3377; the two wounds of seq 3385 (0.8600106402781315 tiles) and 3515 (0.4325411279781128) came under `CrawlerBite` reactions with it the one crawler listed, seven of the 16 segments read a `CrawlerBite` type (seq 3385, 3408, 3515, 3546, 3569, 3588 and 3617), and it lay at 0.4325411279781128 to 0.3893497249427413 tiles from seq 3515 to the death. No press, stomp or melee was sent at it after line 354. That the coward rules' readers skip it is the code's (`onFloor`; § How to read it; an inference).

**The drag-down.** On line 402 (game minute 615, frame seq 3582, `me.attackers` 2) the drag-down guard's `many` flee (`flee` `many`, `group` `drag`) took the branch, and every line to the last, 415, read it (14 lines), sending five `steer`s at a run (a87–a91, lines 402, 405, 408, 410 and 413), each accepted and ended `superseded` by the next or, a91, `dead`. On those lines the nearest standing zombie read 0.4469296722046687 to 0.5154335360077998 tiles and the crawler 0.3893497249427413 to 0.4325411279781128, the health 90.02196502685547 to 29.319053649902344. **No frame from seq 3512 to 3655 read the character moving**: 116 frames, 11.498 s by `wallMs`, `me.moving` and `me.running` false on all, the position 10740.3720703125, 10651.1689453125 on every one, 110 of them reading a hit reaction and all 60 from seq 3582, the guard's first line's frame; it moved 0.14180346597113125 tiles from seq 3655 to 3666 under the zombies. `me.attackers` read 3 on frames 3585, 3600-3601 and 3622-3631 and on every frame from 3637; `me.dragDown` read true from seq 3625 with the `EndDeath` reaction. The health read 77.36312103271484 at seq 3600, 53.48555374145508 at 3640, 29.319053649902344 at 3660 and 28.710655212402344 at 3663; the death event at seq 3669 read 0 (#4291: the drag-down's `Kill` sets it to 0 in one call). By #4290 the drag-down counts zombies attacking from under 0.9 tiles at 3 or more, standing unless crawlers are allowed: three standing zombies stood within 0.6655149843519473 tiles on the last frames.

**What POINT_BLANK_FIGHT did there.** On lines 372–392 and 395–399 it held the fight against the `pair` flee and on 400 and 401 against the `many` flee, its target the pair rule's (13653, 13648 or 13651); on lines 402–415 it logged nothing: the drag-down guard's row runs ahead of it (code; an inference). The planner sent no press at the crawler, and from line 395 none at all but the steers.

## 4. The facing, the plan's own measure

**At the presses.** The press leaf's `body_off` read under 1.617660401322909e-05 degrees and `look_off` at most 14.999995681950551 on all 60 presses (the act lines). `grade_x2.facing_body.presses` reads the body against the target on the frame at or before each press step's first act line: n 60, median 3.8042065072358355e-06 degrees, p90 6.340178080200362, hold30 0.9333333333333333, the look the same at the p90; by kind the shoves n 34, median 4.406962833000734e-06, p90 101.18173331307055, hold30 0.8823529411764706; the stomps p90 6.340178080200362; the swings p90 9.73275474665206e-06.

**The shoves' 101.** Four of the 34 rows read over 30 degrees: a35's at seq 1632 (101.18173331307055, the first shove after the first bite, 13617 at 0.5345616065010838 tiles), and three at the shove step that followed a re-pin across the character: a63's at seq 2790 (162.7351402598776; the act line at 2789 re-pinned from 13652 to 13649), a64's at 2813 (168.92537816628192; re-pinned to 13649 at 2812) and at 2824 (168.97089070180937; back to 13652 at 2823). The press leaves of those presses read `body_off` 2.8995193113376064e-06, 1.2286685399437869e-06, 3.7504996227179862e-06 and 6.058456239714418e-06: the grade reads the body when the step begins, the snap then turns it, and the press lands on the target. So the shoves' p90 is the reflex's re-pin between two zombies on opposite sides, read before the snap, not a press off the target.

**Through the stance.** `facing_body.stance`: 1080 stance frames (an aim's or a melee's act accepted or in progress), median 4.928538407548256e-06, p90 170.19391247446308, hold30 0.85; the aims n 154, p90 8.021020494042605e-06, hold30 1.0; the melees n 926, p90 170.19391247446308, hold30 0.8250539956803455. **The 162 frames over 30 degrees** (this writer's count with `grade_x2`'s own readers) are a71's (151: 146 in its `head` step, 5 in its `stomp`) and a59's (11), each with its target `onFloor` 0.0027621358640099515 to 0.005694288959809864 tiles from the character's position, where the bearing names a point under the feet; the other 918 read at most 7.815290137029617 degrees.

**The facing ring** (`facing_ring`, its shares restricted as frame readings): 1080 stance frames with `fwdAngle`, 157 of them aimed and 448 moving.

**Close standing zombies** (this writer's count, F17's table form, #4697): on the 373 frames to the death with a standing zombie within 1.0 tile, the body's offset from the nearest such zombie, by the frame's act:

| the frame's act | frames | within 22.5° | 22.5° to 90° | beyond 90° |
|---|---|---|---|---|
| `melee` (the meet) | 274 | 262 | 5 | 7 |
| `steer` (the drag-down guard's flee) | 68 | 38 | 0 | 30 |
| `walkTo` | 22 | 4 | 18 | 0 |
| `aim` | 3 | 3 | 0 | 0 |
| `stomp` (the ladder) | 3 | 3 | 0 | 0 |
| none | 3 | 1 | 1 | 1 |

From seq 3561 to the death the body held within 0.9736594792633468 degrees of 13653 while 13648 read 102.68175922917726 to 118.49405438763779 degrees off it and 13651 116.06868991503836 to 161.2283424620374 (§ 2).

**The plan's criterion** (the spec's § 2 (1): the body under 15 degrees at the median and 30 at the 90th percentile at every press, and under 30 at the 90th percentile through a held stance): met at the presses (median 3.8042065072358355e-06, p90 6.340178080200362); through the stance the grade's p90 reads 170.19391247446308, so as written it is not met, every frame beyond 30 degrees a melee's stomp or `head` step over a fallen target 0.0027621358640099515 to 0.005694288959809864 tiles off.

**The eye** (`visual-review-f18.md` in the plan's workspace; never evidence for a row): it read the body squared on the target at shots 18, 19, 38 and 39 and turned away from the nearest zombie at shots 31, 33, 35 and 36. On the index frames of those four shots the body read within 0.5 degrees of the act's target (13649, 13651, 13648 and 13651), the nearest standing zombie being that target on 31, 33 and 35; the shot's index `seq` is the latest frame at the mark, not the frame at the grab (§ 11).

## 5. The coward rules and the fleeing

**The fleeing** (`grade_x2.fleeing`): 25 lines over 3.133220672607422 of 54.74802017211914 game minutes (11.923142671585083 s), by reason `many` 14, `held` 9, `flip` 2; the legs `back` 45 lines (5.990123748779297 minutes) and `pull` 11 (1.4517974853515625). The `held` lines are lines 180–184 and 229–232, the frame reading one standing zombie within 6 tiles at 3.6134619095461242 to 5.2492305555067515 on five and none on four; the `flip` lines 233–234; the `many` lines 402–415, the drag-down guard's (§ 3). `engage`: 6 fights, 0 flee turns to fight. Against F17's 389 lines over 51.7921257019043 of 222.08765029907227 game minutes, 158 of them `strain` (#4698).

**What each rule did.**

- `POINT_BLANK_FIGHT`: logged on 38 lines (174 to 401), `over` `pair` 26, `many` 11, `held` 1; six of them sent a melee (lines 214, 351, 357, 385, 388, 395). It held the fight in the group to line 401 and logged nothing under the drag-down guard (§ 3).
- `PAIR_NEAREST`: logged on 78 lines (176 to 401); from line 357 its target followed the nearest standing zombie as the distances crossed, and every melee it sent from 363 to 368 was superseded by the next at another zombie (§ 3).
- `CARE_COMMIT`: 9 lines, all `yield`: lines 140–146 for the first wound (key `wound`, part 2, no zombie near), the `bandage` sent on line 141 and done (`care.bandage` sent 1, done 1); and lines 393–394 for part 13's bleeding (key `bleed`, `near` 3.1174818009959604 and 2.862076780524874), the care's `stop` and the `unwear` a85, superseded on line 395 by the melee at 13653 with the crawler at 0.4325411279781128 and 13651 down at 0.8127347166982364. No walk leg was sent. The Dresses (`dresses`): 2, `done` 1 on part 2 (22.52253246307373 s), `open` 1 on part 13 at the death.
- `STRAIN_BOUND`: 4 lines (291–293 and 309), each withholding the `strain` flee at endurance 0.7032302021980286 to 0.704704225063324 with no standing zombie within 6 tiles (`strain_bound.standing` 0); no `strain` flee line.

## 6. The meet's presses and the melees

**The sends and ends** (`grade_x2.melee`): 28 sent, `by_mode` {`strike` 7, `finish` 6, `shove` 15}, 28 accepted, ends `failed superseded` 22, `done kill` 3, `done handback` 3 (a41, a60 and a81, `why` `standing`: 13649 at 1.6730570793151855 and 1.3476665019989014, 13648 at 1.9979994297027588; `meet_handbacks`). **The 22 superseded** (the next sent line after each): 16 by the planner's next melee, 5 at the same zombie (a finish after a knock-down) and 11 at another; 3 by a flee's steer (a43 and a50 the `held` flee's, a86 the drag-down guard's); 2 by the care's `stop` (a35, a83); 1 by the ladder's stomp (a72). `melees_superseded.superseded_before` 2 (a65, a86).

**The 60 presses** (`grade_x2.meet_presses`): `by_kind` {`shove` 34, `swing` 13, `stomp` 13}; `by_outcome` {`knocked` 27, `nothing` 16, `lowered` 10, `cut` 4, `killed` 3}; `refused` 0. By kind and outcome off the leaves:

| kind | n | killed | knocked | lowered | nothing | cut | `d_press` |
|---|---|---|---|---|---|---|---|
| swing | 13 | 0 | 1 | 10 | 1 | 1 (a79's, superseded) | lowered at 0.9570795786585637–1.2436196570412492; nothing at 0.9567786058426184 |
| shove | 34 | 0 | 16 | 0 | 15 | 3 (a63's and a78's superseded, a81's by the hit) | knocked at 0.6278089344916485–0.8947124714086312; nothing at 0.3586152379863628–0.8962104062920668 |
| stomp | 13 | 3 | 10 | 0 | 0 | 0 | 0.005524271728019903–0.2904399323596568 |

**The 34 shoves knocked 16 down against a `knock_p` sum of 14.3** (`meet_presses.shoves`; #4373). Against F17's 82 presses: 7 killed, 38 knocked, 1 lowered, 3 cut, 33 nothing, the 28 shoves knocking 7 against 12.13 (#4695). Every swing pressed at 0.9567786058426184 tiles or more; none at F17's 0.6224220515093261 to 0.673270970972315.

## 7. The intent: the goal's target, the walks, the door, the sneak

**Toward the goal** (`toward_target`, the grade's inference off the lines): 52 lines and 7.096195220947266 game minutes toward a named target of the 79 lines and 10.549049377441406 minutes on which one was named, of 54.74802017211914; `destinations` 13 walks, `building` 9 and `cluster` 4 (the farthest and `other` restricted). **The walk on a model wait** (`goal_wait`): 47 continued-walk lines, 9 sent; `unmoved_near_s` 0.0. **Standing** (`standing`): 6 stretches of `STAND_LINES` or more lines unmoved near a zombie, 168 lines, 83.8205258846283 s, 23 game minutes, all in the threat branch: lines 160–181, 267–286, 289–309, 311–362, 363–382 and 383–415, each a fight at one to four zombies; the last three run unbroken from the a71 stall to the death (§ 3).

**The door** (`door_held`): 1 decision, `stance_open` at the door 10747,10642 (line 128, nothing sent on it; § 2); 2 kills within `DOOR_KILL_S` after it (13617, 13618). No window was climbed (`pza16.window` sent 0).

**The sneak** (`sneak`): postures `on` 3 and `off` 3; 84 frames sneaking over 5 game minutes; the sneak walk 1.2965047451797167 tiles a second over 2 legs; of the zombies within `SNEAK_R`, 2 passed and 1 noticed (13617).

## 8. The calls and the goals

**The calls** (`goals.log`, 7 lines, each `model` `sonnet`): every one `ok` (`llm.ok` 7, `fallbacks` 0), latency p50 3.6378109455108643 s and p99 4.776790618896484 s (`llm`); goals `LootBuilding` 3 (calls 1–3, building 5), `ExploreToward` 4 (calls 4–7); ends `done` 3, `superseded` 4. The first goal, a loot of building 5, ended `done` (`looted`) on line 65; no call came after the seventh, its `wall` 92.04862856864929 s after `loop.startPyMs` (a span) of the loop's 207.45237350463867.

## 9. `grade_x2` on the facing composition

`f_grade.txt` re-runs `grade_x2` beside `state.log`, `decision.log`, `goals.log` and `shots/shots.jsonl` (`frames_files` [`state.log`], `frames_n` 2223).

- **The header lines.** The report's first line reads "kills 3 (engine 3, planner 0)" and its second "disagree": the legacy act-line read (`kills.legacy_planner`, restricted), which misses a melee's kill; the kills are `kills.planner` 3 (§ 1).
- **The death line.** "death (signal event) explained by the frames: first wound seq 1592" names the first wound of the window the reader scans, not the death's cause; the death is the drag-down of § 3.
- **The facing.** `facing_body.presses` reads the body when the press step begins, before the snap; the leaf's `body_off` is the press's own (§ 4). Its two breaks (restricted as a count) are a71's and a59's frames over a fallen target.
- **The union.** `landed_hits.steps` and `hits_union.steps` both read 3, each step run falling on a reaction run; the frames' runs are 4 and the scorecard's segments 16 (§ 1); the grade's joined counts and unions are restricted as frame readings.

## 10. The end and the machine

**The end.** The death event (§ 0); `client_end` reads the stop `death`; `admin_lua_error` false, `server_error_count` 0.

**The hutch guard** (P28-G): `client-console.txt` line 3295 "found the hen hutch at 10723,10598" and line 3299 "found the turkey hutch at 10779,10637"; no clear line and no `IsoHutch.removeFromWorld` exception in the console.

**The memory** (`memory`; each row's `free_gb` the host's available memory, `java_gb` the `java.exe` working sets, the server's pid 530112): 15.62 GB before the boot (`memory_wait` 15.62, no floor applied); at ready 2.08 with the two sets at 13.67 GB, the server's 3.63 and the client's 10.05; 15.87 GB after the teardown. No in-play row (`loop.memory` [], no `memory_reads` key: the session ended before the first 300 s read).

## 11. The shots and the visual pass

The shot taker wrote 45 index lines and 45 images (`shots/shots.jsonl`: `method` `screen` on all 45, `skipped` none; the `trigger` field `goal` 13, `cadence` 12, `threat` 12, `health` 6, `death` 1, `stop` 1). The index's `seq` and `gameMin` are the latest frame the loop had read at the mark, not the frame at the grab.

| n | file | decision line | method | sha256 | shows (the visual pass; the frame) |
|---|---|---|---|---|---|
| 19 | `shot-0019-1891.jpg` | 167 | screen | `5018d757ce64e66a2f8628835e7315d73a4685f96dd86a19d3f0e3d9bad41294` | after the first kill: the stance held, the bat up, two zombies along the fence line 3 to 5 tiles off; the index frame reads 13652 at 2.84 tiles |
| 33 | `shot-0033-3212.jpg` | 347 | screen | `ee8a0347c89e92d93e04706f51372b2d27039f986a93d0b88f8a45ecd2840547` | the clearing after the a71 stall: a zombie overlapping the character from the north; the index frame reads the body on 13651 at 0.75 tiles, 13649 down at 0.60 |
| 34 | `shot-0034-3351.jpg` | 367 | screen | `220445481734cab7e29c42b47208a0d540b25dd2ba290e14fae1998cf103e373` | the character among the zombies over the corpse; the index frame reads 13651 down at 0.16, 13653 at 0.69, 13648 at 1.41 and the crawler at 1.42 |
| 35 | `shot-0035-3485.jpg` | 387 | screen | `c703701e9c2d854a53b6d2ef89cddd047b1df1a5a6a8cf7cab87ba2c25cabde0` | the pile: standing zombies on two sides, the crawler below; the index frame reads the body on 13648 at 0.96, 13651 at 1.24 75 degrees off |
| 37 | `shot-0037-3582.jpg` | 402 | screen | `01779f172e200c746f651ebc1790f8783ba99a6f12970736757c0b8e155e7da1` | the drag-down guard's first steer: the character encircled under a `Bite`, `me.attackers` 2 |
| 41 | `shot-0041-3631.jpg` | 410 | screen | `c3a9bc1174a0c101991c310ae8e4d8328d3b73aea5e149b6407d0730aa9fecaf` | the heap at health 53.48555374145508 under `EndDeath`, the character unmoved |
| 44 | `shot-0044-3666.jpg` | 415 | screen | `5856ff4138809eeae7717fa51531301bd7711485f707ad8bd4925fc54ab4f83d` | the death's mark: the character down under the standing zombies |

**The visual pass** (`visual-review-f18.md` in the plan's workspace, a sonnet reviewer's reading of 20 of the 45 images; ruling P27-8: its candidates rank beside the write-up's and are never evidence for a row): the facing table (§ 4); the death reconstructed as a crawler under the character from game minute 608 with no press at it, three standing zombies closing by 613 and the `many` flee's run steers heading into a zombie at the side; its candidates: stomp a crawler within 0.5 tiles when a standing zombie is within 3, no run steer whose heading has a zombie within a tile, a shove at the one in front instead of a run at under 0.5 tiles, a leave at the first count of two standing in open ground, the body kept on the nearest between presses, the sheet naming the crawler apart from the standing count.

## 12. What the frames cannot say, the host

- **Why a71's `head` step held.** Fifteen progress lines read `head` with the same `hp` and `d` 0.005; the reflex's reason for not pressing is not on the line (the Lua at `ab73cc44`; no reading).
- **Why the steers did not move the character.** Each was accepted and the frames read no movement under a continuous hit reaction from seq 3546; whether the engine blocks a move during a hit reaction or a grapple is not read here (no register row; the next jar read).
- **What counted the drag-down.** `me.attackers` read 3 with three standing zombies within 0.6655149843519473 tiles and the crawler under 0.44; whether the crawler counted is #4290's sandbox switch, unread on this fixture.
- **The crawler's rise.** The frames read 13649 `crawler` true from seq 3292 at the health a75's stomps left; the engine's rule that turns a fallen zombie into a crawler is not read.

**The host.** One Windows host; § 10. Every millisecond above is this host's.

**The epoch-ms leaves** (wildcard): `*wallMs`, `*Wall`, `*_wall`, `wall_*`, `*.wall`, `epoch_ms_*`, `*PyMs`, `*pyMs` and `*_ms` anywhere in `f_goals_18.json`, and the loop's seconds keys (`loop.startPyMs`, `loop.t_loop0_ms`, `loop.wallS`, `stop.wallS`, `loop.stopped.*`, `loop.fights[*].startS`, `loop.fights[*].startWall`, `loop.fights[*].end.endS`, `loop.actions[*].sentS`, `loop.actions[*].endedS`, `loop.goals[*].startS`, `loop.goals[*].endS`, `readings.kit.spawn.before.wall`, `readings.kit.spawn.after.wall`, `server_launch_wall`, `server_started_wall`, `session_ready_wall`, `teardown_started_wall`, `wall_seconds` and the like), the `wallMs` of every line of `state.log`, every `decision.log` `wall`, every `goals.log` `wall`, the `wallMs`, `pyMs` and `grab_ms` of every line of `shots/shots.jsonl`, `clip.start_ms` and `clip.stop_ms`, and `timeline`, `phase_walls`, `client_seen`, `memory[*].wall` and `memory_wait[*].wall` are this host's clocks, cited only as a difference within this run (a span, a duration, a pairing), never as a reading.

## 13. The next work

The readings behind it are §§ 3, 4 and 5; the candidates, ranked with their costs, are on `docs/reference/research-notes.md#agent-link`.

## Do not cite from this file

The run's 26 rows in `docs/reference/do-not-cite.csv` (25 committed with the artifact at `29b829f2`, the death reader's added at `96d2e89e`): the frames' cost group as a per-tick cost (P28-I); every free-text reason, detail and error string, `stop.detail` and the model's answer and prompt texts among them; the driver's tables; `loop.lineage`; `loop.last_decisions`; the shots' `grab_ms` and `pyMs`; the standing fights' stagger; `engage.fights_sought`, `sought_lines` and `seek_lines` as the planner's count; `wounds.real` and `listed`; the inherited `[inference]` leaves; the record's own `grade_x2` groups reading `read` false; `open_views.all_looted` and `objects.taken_after_skip`; grade_e16's inference leaves; `kills.per_fight` indices counted from 1; `game_minutes_log_end` as minutes to the death; `kills.legacy_planner`; `goal_wait.near_runs`, `near_lines` and `near_s`; `swing_close.back.*` and `bites_in_back`; `hits_union.joined` and `union`; `destinations.farthest`, `off_building` and `by_kind.other`; `landed_hits.joined`, `union` and `per_kill_union`; `fleeing.away.minutes` and `refuge_skipped`; `shots.by_method.screen`; `facing_body.breaks` and its rows' `sent`; `facing_ring`'s shares; `death.check.explained`, `explained_by` and `wound` as the death's cause.

## Corrections

**To the record written before this guide** (the stub, the artifacts row at `docs/reference/artifacts.md` line 340, the brief, the do-not-cite rows):

1. **"45 window-grab images"** (the row): every one of the 45 is a screen grab (`shots.jsonl` `method` `screen` on all 45); none was taken through the window path (corrected at `96d2e89e`).
2. **"the farthest 23.0 tiles from a known building"** (the stub and the row): `destinations.farthest` is restricted by the run's own do-not-cite row; the walks are 13, `building` 9 and `cluster` 4 (corrected at `96d2e89e`).
3. **"the stomps p90 6.3, the swings on target", "the shoves p90 101.2"** (the stub and the brief): the grade reads the body when the press step begins; the press leaf's `body_off` read under 1.617660401322909e-05 degrees at all 60 presses, the shoves' four large rows included (§ 4).
4. **"the reflex's 3 `hit` steps"** (the stub): three runs of `hit` steps, ten progress lines (§ 1).
5. **"the last six decision lines all `flee:many`"** (the stub): the last fourteen, 402–415 (§ 3).
6. **"three standing zombies 13648, 13651, 13653 at 0.45 to 0.86"** (the stub): on the frames of the `many` lines the nearest standing read 0.4469296722046687 to 0.5154335360077998 and the three 0.4469296722046687 to 1.5934064906309267 (§ 3).
7. **The do-not-cite row on `shots.by_method.screen`** (`do-not-cite.csv` 23582): its why carries F17's counts (138 screen, 117 window, 256 lines, 255 images); this run's index reads 45 lines, all screen, 45 images (corrected at `96d2e89e`).
8. **The stub's head** names F18 "the seventeenth"; it is the session the plan names F18.
9. **Not in the record before this guide**: the a71 `head` step stall over which three zombies arrived (§ 3); the character unmoved under all five of the drag-down guard's steers (§ 3); no press at the crawler after line 354 (§ 3).
10. **The row's other figures stand** (the kills by every read, the reaction runs, the 16 segments, the wounds, the fleeing by reason, the melee and press counts, the handbacks, the Dresses, the care, the door, the sneak, the standing, the model's calls, the memory, the hutch lines).
