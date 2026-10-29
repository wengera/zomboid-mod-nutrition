# Plan 23: the survivor — report

Plan 23 asked whether the Plan 22 base could drive one character through a game day and its night: fighting what it must, fleeing what it cannot fight, eating, drinking and sleeping when the game says to, on sessions that chain on one world, so that a goal layer, scripted first and an LLM next, has a living character to steer (spec `docs/superpowers/specs/2026-10-28-plan-23-survivor-design.md` § 1). GO was a chain that lived 24 game hours with a drink, an eat and a sleep each landed `done`.

It did not come near GO. The plan booted eight of its nine sessions (a ledger count; the ninth unspent by ruling P23-AR). Five chains each ended in their first session with a death, so no chain reached a second session and `pzt snapshot` never ran on a live run. The longest chain session lived 68.31436157226562 game minutes [#4255]. The LLM goals session lived 84.42392349243164 [#4280], the plan's longest. No session reached a need's first moodle or the night, so no `consume` and no `sleep` was ever sent [#4233] [#4240] [#4246] [#4255] [#4266] [#4280].

What the plan did deliver:
- **The deaths are now read.** Each one is explained frame by frame from its first wound. Each of the first four answered a bounded survival iteration (P23-AG, P23-AJ, P23-AM, P23-AP), and every iteration changed how the next death came.
- **The death is now seen.** The `death` event of PZA/1.3 stopped the loop with no planner tick reading the dead character in both sessions that carried it [#4267] [#4281].
- **The shots show what the frames do not.** The shot taker made the client's screen part of the record [#4254] [#4265] [#4275] [#4287].
- **The goal seam took an LLM.** The `claude` CLI answered 13 valid goals of 14 calls in its first session [#4276].

Paths below are relative to `testing/artifacts/` unless they begin with `docs/`, `testing/` or `tools/`. A row `#NNNN` is `docs/reference/claims.tsv` at `fa09b657` (Plan 23 E5 write-up fix 1). "Ledger L<n>" is a line of `.superpowers/sdd/2026-10-28-plan-23-survivor/progress.md` (gitignored), and the workspace is that folder. Line counts are by `wc -l` at `fa09b657`. When this report was written, the F1 write-up's review (ledger L285) had not returned. Its rows #4276–#4287 are cited as minted, and a correction it lands supersedes the wording here.

| Session | Folder | Graded by | End |
|---|---|---|---|
| X4-3, the link's cost | `x4_link_3-20261028-101928` | `gate_x4` (`x4_grade.txt`) | NO-GO on `tick_mean_at60` and `worst_tick` (the artifact's grade; #4217, #4215) |
| X5-2, the pinned fight | `x5_combat_2-20261028-105844` | `measure_x5` | a measurement, no gate (#4227–#4232) |
| E1, chain 1 session 1 | `e_day-20261028-110422` | `grade_e1` | death (#4233) |
| E2, chain 2 session 1 | `e_day_2-20261028-124249` | `grade_e1` | death (#4240) |
| E3, chain 3 session 1 | `e_day_3-20261028-153631` | `grade_e1` | death (#4246) |
| E4, chain 4 session 1 | `e_day_4-20261028-173649` | `grade_e1` | death, unseen by the driver; the loop ran to its cap (#4256) |
| E5, chain 5 session 1 | `e_day_5-20261028-201255` | `grade_e2` (`e_grade_2.py`) | death, read through the `death` event (#4267) |
| F1, the LLM goals session | `f_goals-20261028-202437` | `grade_f2` (`f_grade.py`) | death, read through the `death` event (#4281) |

## 1. What the base is now

**The protocol: PZA/1.3.**
- **PZA/1.2** (Task 4, `0470b1d4`; the goldens re-recorded under that named change, ruling P23-N) appended four edge fields to the square record (ruling P23-K). `blockN` and `blockW` are the engine's movement edge, `isBlockedTo`; `edgeN` and `edgeW` mark any wall, door or window on the edge, `isSomethingTo` [#4222]. It also added `me.hour`, the game's float hour [#4221] [#4223], and the `sleep` action (Task 8, ruling P23-E). The loot `interact` gained `maxWeight`, with `result_interact.skipped` in its result (Task 7). `item_added` gained `use`, the item's use as the Lua's engine-backed rule classifies it (Task 9b, ruling P23-O).
- **PZA/1.3** (`caf84b53`, `6952a5b2`, ruling P23-AO) added the `death` event. It fires once per local player, with `via` `hook` when the client's `OnPlayerDeath` named the player and `isDead` when that read came first. The driver library stops the loop on it (`a7fb6ff9`, `182cd10a`).
- `testing/agent/base/schema/pza1.json` is 796 lines, `tools.json` 242, and the hand-written `goals.json` 59 (ruling P23-B).

**The paced poll** (Task 5, `ed519ef5`, spec P23-4). `cmd.txt` is now read every third tick (`L.POLL_EVERY = 3`). At 60 Hz a poll cost what it had cost before, so its share of the tick fell [#4218], and the tick mean read 1.0121816168327795 ms [#4217], still over `gate_x4`'s 1 ms.

**The map's edges in the scan and the watch** (Task 6, `3240565b`). The watch's fingerprint carries the edges. Its steady step rose to 0.2585034013605442 ms against 0.19798657718120805 [#4219]. Ruling P23-P left the choice of a cheaper fingerprint to that reading, and it is still open.

**The driver library** `testing/agent/driverlib/` (Task 2, then the fix wave's Lane D and the later rounds; 2179 lines):

| Module | Lines | Job |
|---|---|---|
| `session.py` | 956 | the memory gate, preboot, boot, hello, the kit, the loop, the stops (the frame's health, the `players` reply, from E5 the `death` event) |
| `reads.py` | 223 | `ServerReads`, the server reads on the poll thread (P23-13: no server read stalls the planner) |
| `polls.py` | 99 | the poll thread and its cadence |
| `record.py` | 81 | the loop record (`loop.first_world_age`, `loop.goals`, `loop.shots`, the death) |
| `chain.py` | 76 | the snapshot step and the lineage diff, with ruling P23-Y's tolerances (its clock band one-sided on `worldAge`) |
| `day.py` | 368 | the day session's flags, the chain record and checks, `boot_and_run`, `grade_day` with `GRADE_KEY` `grade_e2` |
| `shots.py` | 356 | the shot taker (ruling P23-AL) |

Every driver after the X4 and X5 copies imports the library and copies nothing. These are `e_day.py` through `e_day_5.py` (each 132–134 lines) and `f_goals.py` (175). `x4_link_3.py` and `x5_combat_2.py` are copies of their predecessors with their constants swapped (ruling P23-C).

**The planner** (`testing/agent/base/planner/`, 3628 lines):

| Module | Lines | What it holds |
|---|---|---|
| `survive.py` | 783 | `Survive`: the five branches `threat`, `need`, `load`, `night`, `goal` in that order; `_threat_plan` |
| `policies.py` | 1230 | the `Fight` and the `Flee` |
| `night.py` | 435 | the night's shelter and sleep |
| `goals.py` | 648 | the five goal types (`ExploreToward`, `LootBuilding`, `Shelter`, `Stock`, `Rest`), `GoalRunner` and `ScriptedSource` |
| `llm.py` | 361 | `LLMSource` |
| `view.py` | 153 | the view the sources read |

`LLMSource` runs `claude -p` on a worker thread, stripped to no tools, no settings and one turn by the CLI's own flags (ruling P23-V). It validates the answer against the goal schema and the collecting tick's view, and falls back to the scripted source (ruling P23-AC).

The threat plan is where the plan's iterations went. One survival iteration followed each of the first four chains' deaths, each on its own ruling, each with a whole-iteration review and fix rounds (ledger L189–L273):

| Iteration | After | Ruling | What it changed | Commits |
|---|---|---|---|---|
| 1 | E1 | **P23-AG** | The flee runs to a known shelter when its door is not through the threats, and `many` counts the hold radius during a fight. Every steer leg is weighted away and probes the map 3 tiles ahead, turning to the first clear heading. A leg that moved under half a tile is re-aimed. The shelter pick is retried at each leg's end and refuses a heading through a held group; the building a flee starts in is adopted. Fix 3 guarded the open door, preferred a 9-tile probe and skipped a stuck heading by angle. | `170cee79`; fixes `24e14bec`, `9ecef6da`, `42e7f49b`, `21e3716b` |
| 2 | E2 | **P23-AJ**, refined by **P23-AK** | `World.openings`. The inside hold breaks on approach (within 3 tiles, or closing on three ticks running). Cornered, the branch fights the nearest whatever the count. Inside a building the flee walks out through the nearest acceptable opening and never steers on a room square. The reposition floor is 1.2 tiles. Window edges are no openings. The cornered fight skips the line check within 1.0 tile. | `e165ca24`, `aa130e9d`; fixes `607dca06`, `e42a7efb`, `145868e2` |
| 3 | E3 | **P23-AM** | A flee started under a group stays a flee. Every shelter step stalls like the exit, dropping after 1 s unmoved with a threat near. A group is fled at a sprint early, and the corner against three or more steers. Exterior doors are judged by the door's own edge, the corner applies on every walk, and a running corner re-checks the group. A south or east wall door is filed under its room's building. | `c18e247f`, `c41f9880`; fix `259a58bc` |
| 4 | E4 | **P23-AP** | The goal source leaves a stuck area: no walk across a known blocking edge, and at most `STUCK_WALK_CAP` 3 unmoved walks. A walk or inside corner ends for a closing group. A running steer leg is cut when a newly held threat enters the cone ahead. The corner re-pins to the nearest within point blank. | `e07a52cb`; fixes `4a86c05c`, `c77f69e3` |

E5 and F1 ran on iteration 4. No iteration 5 was ruled (P23-AR, § 7).

**`pzt snapshot --from-run`** (Task 1, `bd4cf485`, `e9225ac1`) takes a fixture from a finished run with its lineage. No chain session ended alive, so it never ran on a live run (the chain table, ledger L182–L276).

**The UI tidy** (ruling P23-AN, `7d96a68c`, `3c5a6e3b`). At every client prepare `pzt` closes the character-info window in the per-run `layout.ini`, starts a `-debug` client's debug console hidden, and moves the chat window to the bottom-left. The fixture itself is untouched. It read live in E4 [#4265]. CLAUDE.md § 5's clients clause ("the info window and debug console stay as the fixture saved them") is rewritten at the close (ledger L286).

**The grades.**
- `gates_e.grade_e1` through `e_grade.py` graded E1–E4. It is frozen by ruling P23-AQ, restored byte for byte after the death-event change, and still reproduces all four artifacts' `e_grade.txt` (ledger L265, L270).
- `grade_e2` through `e_grade_2.py` names the death's signal, and graded E5.
- `gates_f.grade_f2` through `f_grade.py` is `grade_e2` plus the LLM calls' and goals' counts, and graded F1 (`d2641e2a`).
- `gate_x4` and `measure_x5` ran unchanged.

**The tests.** The full suite at the close reads `10298 passed, 28 skipped (2026-10-29, `close-full-pytest-1.txt` in the workspace, at 2f7664b4 with the F1 pages uncommitted: docs only)`.

## 2. The chains

Five chains, each one session, each a death. The minutes are by `worldAge` from the session's first frame.

| Chain | Run | Death (game minute) | Game minutes alive | Cause, in one clause | Rows |
|---|---|---|---|---|---|
| 1 | `e_day-20261028-110422` | 606 [#4233] | 45.22184371948242 [#4233] | a `many` flee pinned 17.102 s in a fence corner the map held, the wounds landing there, then a bleed-out with no zombie near [#4237] [#4238] | #4233–#4239 |
| 2 | `e_day_2-20261028-124249` | 592 [#4240] | 33.274497985839844 [#4240] | a flee into a bathroom it never left, one zombie through the doorway [#4243] [#4244] [#4245] | #4240–#4245 |
| 3 | `e_day_3-20261028-153631` | 600 [#4246] | 40.209617614746094 [#4246] | a shelter `enter` walk stuck 14.429 s outside a wall while a group closed, then a fall to 0 in one frame step [#4251] [#4252] | #4246–#4254 |
| 4 | `e_day_4-20261028-173649` | 627 [#4255] | 68.31436157226562, to the last frame that read the bat [#4255] | a stuck corner under a group that rose to six, unseen by the driver [#4262] [#4263] [#4256] | #4255–#4265 |
| 5 | `e_day_5-20261028-201255` | 595 [#4266] | 35.2580451965332, to the `death` event [#4266] | a group of seven held within 2.554 s of a one-zombie fight, the flee's legs carried into it, then a fall to 0 in one frame step [#4268] [#4270] [#4272] | #4266–#4275 |
| F1 (not a chain) | `f_goals-20261028-202437` | 644 [#4280] | 84.42392349243164, to the `death` event [#4280] | a corner on a pair held 55 ticks through health under 40, a bleed under two zombies [#4285] | #4276–#4287 |

**What each death taught, and what answered it.**
- **E1: the flee ran into edges the map already held.** The first fight's flee went into the corner of two building walls, where five legs moved 0 tiles. The second fight's flee went into the inside corner of two fence edges, where four sprint legs moved at most 0.0215 tiles while up to four zombies stood within 1.5 [#4237]. Every wound came there [#4238]. The bleed-out then ran with no zombie nearer than 1.6173505470531806 tiles [#4238], while a looted bandage stayed held (no skill applies one; the research thread "A held bandage"). Iteration 1 answered with the probing, edge-aware steer and the shelter run. In E2 the shelter pick answered once, with a run of 11.5136 tiles toward building 2 [#4242].
- **E2: the hold and the flee inside a room.** The first leg the new steer turned ran into building 3's bathroom. There the inside hold stood 15 ticks while a zombie walked round to the doorway, its line read blocked through a wall [#4243]. The flee then never left four bathroom squares [#4244]. Iteration 2 answered with a hold that breaks on approach, the cornered fight and the walk out through an opening. In E3 the hold stood once, five ticks, against a true shut-out, and its breach conditions were never met [#4249]. No flee began on a room square, so the walk-out is unread live.
- **E3: the fight-flee flap and the stalled shelter step.** The branch changed between a fight and a flee seven times in 7.035 s [#4250]. The shelter plan's `enter` walk then ran back and forth outside the building's north wall while the group closed to 0.4817185932051521 tiles [#4251]. Iteration 3 answered with the kept flee, the stall drop, the early group sprint and the door by its own edge. In E4 no fight and flee flapped: the second fight's flee read `many` on all ten ticks with no fight tick [#4260], and the third ran 35 ticks with none [#4261]. E4 made no shelter plan, so the stall drop is unread live.
- **E4: the corner under a growing group, and a death the driver could not see.** A `walk` corner stood 35 ticks while the held count rose from 3 to 6 [#4262]. The fatal corner was a stuck one with four within 1.5 tiles [#4263]. The goal source had also spent 21.84917449951172 game minutes on twelve walks that moved 0 tiles north of a locked gate [#4257]. The frames' health never read 0, and the planner sent 175 steers on a dead character [#4256].
  - Iteration 4 answered the corner and the stuck area, and ruling P23-AO answered the unseen death.
  - In E5 the source failed no walk [#4274], against fourteen failed in E4 [#4257].
  - In F1 the threat branch's later rules each answered live: a leg was cut, a corner ended at four held, and the steer that followed ran 11.916 tiles in 3.011 s [#4284].
- **E5: a horde within seconds.** Nothing answered it in this plan (P23-AR). Seven zombies came into the 12-tile listing one by one, 11.748361392103797 to 11.992784556085855 tiles off. The fight took on the one within 6 tiles and ran toward it, and 2.554 s later all seven were held [#4268].
- **F1** died the way iteration 4 did not reach. The last fight's corner, on a pair, stood 55 ticks to the death, never more than three held, so no group rule fired [#4285]. The research thread notes that the corner overrides every flee, health included.

**The trend.** The chain sessions lived 45.22184371948242 [#4233], 33.274497985839844 [#4240], 40.209617614746094 [#4246], 68.31436157226562 [#4255] and 35.2580451965332 [#4266] game minutes. F1, on the same instincts with the LLM choosing goals, lived 84.42392349243164 [#4280]. That is no monotone rise. Each iteration removed the failure that killed the session before it, and the next session died of a different one. Each reading is n = 1 on one fixture (`agent`, Zombies 5), and each session's goals took the character to different ground. F1's longer life is one session, not a reading of the LLM's worth (§ 5).

## 3. The instincts' readings

**The fence stand-off.** Every chain's first fight, and F1's, met a zombie across one fence row. In E5 and F1 it stood on that row's locked gate square [#4235] [#4242] [#4248] [#4258] [#4273] [#4282].
- **The line check worked live in every session.** In X5-2 four spawns behind a closed door were read blocked, repositioned once and marked unreachable, with no swing sent [#4229]. In the chains the line read blocked on all 480 frames listing the zombie in E1 [#4235], on 163 of 165 in E2 [#4242], and on all 57 fight ticks in E3 [#4248]. No session swung at a barrier as Plan 22's run 1 had.
- **The reposition was the weak step.**
  - In X5-2 every reposition walk named a square's corner inside the walk's 1.0-tile end radius and ended `done` without moving [#4230]. E1 repeated this, and E2 repeated it with the square's centre at 0.8585783994376733 tiles [#4230] [#4242].
  - Iteration 2's 1.2-tile floor made the walk run, but then it ran 12.3743 to 14.4982 tiles of path and failed `stuck` within 1.4619 tiles of where it began, in E3 [#4248], E4 [#4258], E5 [#4273] and F1, where one ended `done` having moved 0.1434 tiles [#4282].
  - The fence's far side is reached only round the fence's end. In F1 a loot's walk took the character round the west end, met the gate zombie from the south with the line clear, and killed it in eight attacks [#4282].

**The flee.**
- *The edge pin* (E1): legs into corners the map held [#4237]. Iteration 1's probe answered it.
- *The room pin* (E2): legs that never left a bathroom [#4244]. Iteration 2's walk-out answered it, unread live.
- *The shelter step* (E3): an `enter` walk stuck 14.429 s while the group closed [#4251]. Iteration 3's stall drop answered it, unread live.
- *The sprint.* Iteration 3's group sprint ran, its first leg ending 10.45860308923644 tiles from its start [#4260]. A later leg crossed into and out of a fenced pen across lines the map read blocked [#4261]. In E5 the two sprint legs, aimed west with their probes clear, carried the character north-north-east along the line of the superseded run walk, into the group, with `moving` read true on 1 of 50 frames [#4270]. Plan 22's auto-walk legs had gone within 1.52 degrees of their headings [#4199]. Whether a pathed walk keeps steering after a steer supersedes it is a Lua read the E5 writer named as owed.

**The fight.**
- **The kills.** The first kill of any chain came in E4: four attacks, each starting a swing, at health 100 throughout [#4259]. F1 killed three, each the fight's own target, after three, five and eight started swings [#4283].
- **The swings that never start.**
  - In X5-2, 2 of 7 attacks never started, ending at the 1500 ms timeout [#4210].
  - E4's first corner started 5 of 10 swings [#4262].
  - E5's corner started none [#4271].
  - F1's last corner started 11 of 18, with 6 never starting [#4285].
  - The survival-4 implementer read in E4 a wound rise inside each never-started window and inferred that a hit interrupts the swing (ledger L266). The reviewer held that inference to a jar read before any Lua change (ledger L267).
- **The corner kinds** (`walk`, `stuck`, point blank) are read off the code, since the log carries no corner kind (E4 and E5 guides, by inference).

**The hold.** The inside hold stood while a threat walked round to the doorway in E2 [#4243]. Iteration 2's breach on approach never fired live: the one hold in E3 was a true shut-out [#4249].

**The horde** (E5). Seven zombies entered the 12-tile listing one by one, each at its edge [#4268]. The threat branch counts 6 tiles, or the 10-tile hold radius under a fight, so it fought the one zombie it saw and ran toward the six behind [#4268]. The listing's reach, not the counting rule, is the first limit (§ 7).

**The one-step deaths** (E3, E5). In E3 the health read 63.73676300048828 at the last wound rise and 0 one frame step, 0.099 s, later, with no wound count rising [#4252]. In E5 it read 73.07925415039062 and then 0 on the death event's frame, 0.103 s later. The server's damage watch returned three bleeding records summing 0.022167793475091457 [#4272]. What rule takes a character from that health to 0 in one step under five zombies is unread: no row and no jar read. "A pull-down" is a candidate name only. F1's death was not one: it bled to 0.8721389770507812 over 22.898 s [#4285].

## 4. The night, the needs, the load

Unread live in every session. No session reached a need or the night:

| Session | Hunger, thirst and fatigue at most |
|---|---|
| E1 | 0.024253008887171745, 0.03244566544890404, 0.035688985139131546 [#4233] |
| E2 | 0.01835831254720688, 0.017498159781098366, 0.021833082661032677 [#4240] |
| E3 | 0.021474506705999374, 0.02325577475130558, 0.027864642441272736 [#4246] |
| E4 | 0.038264308124780655, 0.038901470601558685, 0.05044184625148773 [#4255] |
| E5 | 0.01938604936003685, 0.019721217453479767, 0.023930059745907784 [#4266] |
| F1 | 0.04537864029407501, 0.05349582061171532, 0.06224467605352402 [#4280] |

The need branch fires at the first moodles, thirst above 0.12 and hunger above 0.15 (spec § 7; [#0509], [#0508]). No `consume`, no `Stock` goal and no `sleep` was sent in any session [#4233] [#4280]. In F1 no view carried a wanted need, so the model was never asked to stock [#4280].
- **The night** rests on the jar alone. The server fast-forwards when `SleepAllowed` and every living connected player reads asleep, at 120 on the 90-minute day [#4224]. The wake rules are [#4225], and the floor bed and the zombie counts the sleep checks are [#4226]. The `sleep` skill has not run live. X4-3 sent none, and the chains never wanted it (`docs/platform/harness.md`, the agent section, a reading of the code).
- **The load** stayed at level 0 in every session but E1's last 14.0 s. There the level-1 reading came from the maximum falling 12 to 8 with the health, the carried weight unchanged [#4239]. Every other session died at load level 0 [#4240] [#4246] [#4255] [#4266] [#4280], under the loot's weight cap (Task 7). No row reads the drop guard firing.

## 5. The goal layer and F1

**The scripted source's sessions:**

| Session | Goals proposed | Done, superseded, failed | Note |
|---|---|---|---|
| E1 | 6 | 3, 3, 0 | Its last loot came at health 14.101974487304688 with five bleeding wounds [#4234]. The view carries no wound. |
| E2 | 7 | 4, 2, 1 | The failure a walk standing 5.901 s and ending `stuck` [#4241]. |
| E3 | 11 | 7, 3, 1 | [#4247] |
| E4 | 24 | 7, 3, 14 | Fourteen walks failed `stuck`, twelve of them in a row from one position north of the locked gate, each moving 0 tiles, over 21.84917449951172 game minutes: the stuck area [#4257]. |
| E5 | 9 | 3, 6, 0 | After iteration 4's stuck-area rule. Four in a row named one square south of the fence, so goal and flee took turns for 20.041 s [#4274]. |

Every superseded goal was superseded by the threat branch's first send [#4234] [#4274]. No `Stock`, `Shelter` or `Rest` came in any session, no need or night wanting one.

**The LLM source's first session (F1).**
- **The calls.** The model was called 14 times, each time a goal was wanted. 13 answered a valid goal and 1 did not [#4276].
- **The latency.** The round trip read 2.6069090366363525 to 5.608803033828735 s, 4.065327167510986 at the median. That is this session's reading on this host, never the model's: the do-not-cite rows restrict it as a reading of the model. Each call was collected 6 to 12 planner ticks after it started, and the goal branch was pending on 122 of its 280 ticks. The planner's ticks ran no slower during a call [#4276].
- **The fallback.** The one invalid answer was collected 4.143779277801514 s after its call started. By then the character's position lay 2.1 tiles west of the one its view had sent, and the scripted source's walk stood in and ended `done` [#4277]. The answer named a square past the source's 60-tile bound from the collecting tick's position. That bound is a code constant (ledger L139), and the answer text is do-not-cite. So the validator's check against the collecting view (ruling P23-AC) caught a goal the call's own view would have passed.
- **The goals' ends.** Of the 14 goals that ran, 13 were the model's: 7 building loots and 6 walks. 3 ended `done`, 3 failed and 8 were superseded. The 3 failures were loots of one building proposed on views listing every one of its containers as looted, each failing on the tick it was proposed. No goal walk ended `stuck` [#4278].
- **What the model chose.** Its first two goals were the scripted source's own for those views. Its six later walks each named a square at least as far east as the last, 21.822423497517242 to 58.143080862738934 tiles off, while the views placed no zombie [#4279].
- **The kills.** Three zombies died, one of them the gate zombie, met from the fence's south side after a loot's walk had taken the character round [#4282] [#4283].

**What F1 showed about the view and the validator.**
- **The view says too little.** It tells the model a building's containers are looted but not what a failed loot means, so the model named the empty building again once its cooling lapsed [#4278] [#4279]. It gives zombie counts, not positions, so the model walked east along the fence toward the gate zombie it could not see placed [#4279].
- **The validator works.** It refused the one goal that had gone stale while the call ran, and the fallback kept the goal branch moving [#4277].
- **The wait has a cost.** The 6–12 tick wait per goal is a real cost to the goal branch, though not to the instincts, which ran on every tick [#4276].
- **The money cost is unread.** The CLI envelope's cost was not recorded.

## 6. The instrument

**The shots** (ruling P23-AL; `971b58ac`, `28baca9d`, `713faae3`). At Angus's request (ledger L226) the library grabs the client window at a 10 s cadence and on triggers (a new fight, a flee rule's change, a goal's change, a health fall, the death, the stop). It indexes each shot in `shots/shots.jsonl`, and a write-up copies the images it cites.
- Every session that carried it found the window on every grab with no failure [#4254] [#4265] [#4275] [#4287].
- **The UI cover.** E3's shots showed the fixture's saved character-info window over the screen's centre, hiding the character until the death [#4254], which led to ruling P23-AN. E4's showed the scene clear, the character under its name tag [#4265].
- **The death screen the driver did not see.** E4's shots show the game's death screen while the frames still read a living health [#4265] [#4256], which led to ruling P23-AO.
- **The fence climb.** In E5 a shot caught the character in a climbing pose at a chain-link fence whose edge the map read blocked [#4269].
- A shot's `seq` is the latest frame read at the mark, and the grab follows on the worker (the E4 guide). That caveat sits beside every shot cited.

**The death event** (ruling P23-AO). In E5 it came through the hook in the client tick that removed the bat, and the loop stopped with no planner tick reading the dead character [#4267]. In F1 it came through the `isDead` read, the hook not having named the player by then, in the frame tick after the running attack ended `failed` `dead` [#4281]. Both arms caught their death within its first frame tick. Which arm answers which death is open (the research thread "Which death signal fires when"). A death the client never reports would still need a server read: the `players` reply listed the dead user in E4 [#4256].

**The grades' freezing** (ruling P23-AQ). The death signal first landed inside `grade_e1`, which four artifacts carry. The death-event review then found `e_grade.py`, a frozen grade script, edited, and both were restored byte for byte. The signal moved to `grade_e2` and `e_grade_2.py`, and the bare `e_grade.py` reproduces E1–E4's `e_grade.txt` (ledger L264–L270). The harness page's sentence naming `e_grade_2.py` as a new session's grade command is a close-pass item.

**The brief-trace lesson.** In every chain write-up, E1 through E5 and F1, the controller's own trace of the live log was wrong on details: in the writer's brief, and in the artifacts row the controller wrote at the artifact commit. Each time the writer or the reviewer caught it (ledger L187, L199, L218, L244, L247, L258–L259, L283, L285):
- E1's brief said "open-ground flee at load level 1".
- E2's brief had the hold stand while the zombie closed to half a tile.
- E3's row placed five zombies within half a tile at the death, which the review corrected.
- In E4 the row had the line-447 corner fight two zombies for three game minutes with little health lost; the writer read it a `walk` corner held 35 ticks while the health fell to 64.94363403320312 [#4262].

Each artifacts row was rewritten from the writer's reading. The rule this plan hands `docs/process/lessons.md` at the close: **a controller's trace of a live log in a write-up brief is a hypothesis the writer verifies; a brief says what to read, never what it reads.**

## 7. What is open, and what Plan 24 should take first

**Open** (the research threads on `docs/reference/research-notes.md#agent-link`):
- **The horde's listing reach.** The frames list zombies to 12 tiles, and the client's cell count rose by at most 2 while seven came [#4268]. A threat read counting the whole listing, or a fight that does not walk toward a zombie with others listed beyond it, is the candidate.
- **The one-step death, the "pull-down".** Read twice and unexplained [#4252] [#4272]. It wants a server read of the death's cause.
- **The fence climb against the map's edges.** The game's walks crossed edges the map reads blocked: the pen in E4 [#4261] and the chain-link fence in E5 [#4269]. The line check and the steer probe trust those edges. A jar read of the pathfinder's edge rules against `isBlockedTo` is owed.
- **The walk keeping its steer.** E5's sprint legs followed the superseded walk's line [#4270].
- **The melee's swings.** Never-started swings in X5-2, E4, E5 and F1 [#4210] [#4262] [#4271] [#4285]. The hit-interrupts-swing inference waits on a jar read.
- **The threat memory.** No goal avoids ground where zombies were met. Six of F1's eight superseded goals were superseded by its answer to the one gate zombie [#4278].
- **The LLM's cost and prompt.** The cost is unrecorded, the latency is one session's [#4276], and the view lacks positions and failure meanings [#4279].
- **The night and the needs.** Unread live in all six survival sessions (§ 4). The fast-forward rate [#4224] and the `sleep` skill have never run.
- **Smaller threads.** The bandage and the bleed-out [#4238]. The frame's lost `me` elision with the hour (the X4-3 guide; a row the X4-3 review asked for, still unminted). The watch's fingerprint cost [#4219]. The edge fields' unread cases [#4220].

**What Plan 24 should take first.** Recommendation: make the threat instinct see the group before it fights, then read why groups kill in one step, before another goal-layer or LLM round.
- **Why the group first.** Four of the six survival deaths came with a group gathering on the character while a fight or a corner held it in place: E3's six [#4251], E4's six [#4262], E5's seven [#4268], and E1's four in the fence corner [#4237]. Two of those ended in a fall to 0 in one frame step that no row explains [#4252] [#4272]. E5 shows the first limit is perception. The group was listed at the 12-tile edge while the branch counted 6 [#4268].
- **The work, in order:**
  1. A threat read over the full listing, with a short memory of where zombies were met.
  2. A fight that refuses to approach a zombie with others listed behind it.
  3. A server-side read of the death's cause, so the pull-down is read rather than named.
  4. The jar read of the pathfinder's edges, since the steer and the line both trust edges the game's own walks cross [#4261] [#4269].
- **What follows.** A chain that lives past one session is the gate for everything else the plan built and never exercised: the snapshot, the needs, the night. No session has yet lived a tenth of the 24 game hours GO asks for [#4280].
- **The weak spot.** The scripted iterations so far each fixed the last death and met a new one, all at n = 1 on one fixture. A fifth iteration may do the same. F1's 84 game minutes [#4280] hint that goal choice moves survival as much as instincts do, though it is one session whose goals took it elsewhere. The alternative is to spend Plan 24 on the LLM's view (positions, failure meanings, the threat memory as a view line) and let goal choice keep the character away from groups. That alternative's downside: no goal can save a character that fights toward a listed group or dies in one step, and the instincts run under every goal.

## 8. The process record

**The rulings** (the ledger, gitignored, so they are recorded here; one line each; the spec's own P23-1 to P23-14 are in the spec):

| Ruling | What it ruled |
|---|---|
| P23-A | Angus's 2026-10-28 direction is the standing approval for every boot the plan names, under CLAUDE.md § 5. |
| P23-B | `goals.json` is a hand-written schema tested against the dataclasses, not a generator target. |
| P23-C | `x4_link_3.py` and `x5_combat_2.py` are constant-swapped copies; `e_day.py` and `f_goals.py` are the library's first drivers. |
| P23-D | A water container's emptiness is learnt from a `consume` failing `not valid` (`World.empty_ids`). |
| P23-E | The `sleep` skill copies vanilla's `onSleepWalkToComplete` through `PZA.call`. |
| P23-F | `Survive`'s forage and explore tests are rewritten into goal tests in place, so the count never drops. |
| P23-G | Task 2 ports `d_survive.py`'s shared code into the library while the frozen driver keeps its copy. |
| P23-H | No worktree and no feature branch: pathspec commits on main. |
| P23-I | Parallel implementers only on disjoint files. |
| P23-J | The checker findings from Task 5's in-flight edit are re-anchored when it lands. |
| P23-K | The edge fields are `blockN`/`blockW` (movement) and `edgeN`/`edgeW` (any edge), and `line_clear` reads the blocked edges. |
| P23-L | The chain plans on the jar's sleep fast-forward. |
| P23-M | Task 2's minors go into fix round 1 with its Important. |
| P23-N | The goldens are re-recorded under PZA/1.2. |
| P23-O | `item_added` gains `use` from the engine (`W.useOf`), the dataset the fallback. |
| P23-P | The cheaper watch fingerprint is decided after X4-3's reading. |
| P23-Q | `REPOSITION_R` is 2.5 tiles. |
| P23-R | The reposition keeps the radius alone; the base has no path search. |
| P23-S | A swing pairs with the first server read sent after its end frame and finished within 2.0 s, else it is voided (refined after Task 16b's review). |
| P23-T | Offline base edits may resume once a detached driver's preboot has passed. |
| P23-U | A sleep refused `not allowed` ends the night's want; one refused `not valid` holds 60 s. |
| P23-V | The LLM call is stripped by the CLI's own flags, verified by one probe. |
| P23-W | A `Rest` is budgeted at max(`GOAL_MAX_S`, its seconds). |
| P23-X | `grade_e1` reads `loop.lineage`. |
| P23-Y | The lineage tolerances; amended to a one-sided `worldAge` clock band. |
| P23-Z | A wrong `--session` refuses the boot. |
| P23-AA | The whole-pass review runs over the offline code before the first boot. |
| P23-AB | A sleep holds the need and load branches, the threat pre-empts, and the Lua wakes the character at any sleep end but `done`. |
| P23-AC | `propose` may return pending; the LLM's goal applies on the current view, the fallback only at the timeout. |
| P23-AD | A consume refusal lasts 120 world minutes. |
| P23-AE | The loop's final `Stop` wakes a sleeper by design. |
| P23-AF | A residual fix round lands before the first boot. |
| P23-AG | E1's death is the first chain's reading; survival iteration 1 and a second chain follow. |
| P23-AH | `e_day_2.py`'s copy review is folded into the chain write-up's. |
| P23-AI | The second chain boots with survival 1's fix-2 findings F1 and F2 parked. |
| P23-AJ | Survival iteration 2: the hold breaks on approach, cornered fights, the flee walks out of a building. |
| P23-AK | The exit is the nearest acceptable opening; cornered pre-empts any walk-out; the adoption is the fallback inside. |
| P23-AL | The driver library gains the shot taker. |
| P23-AM | Survival iteration 3: the kept flee, the shelter-step stall, the early group sprint, the corner against three steers. |
| P23-AN | `pzt` closes the character-info window and the debug console at every client prepare. |
| P23-AO | The Lua emits a `death` event (PZA/1.3) and the driver stops on it. |
| P23-AP | Survival iteration 4: the stuck area, the corner ended for a closing group, the leg cut on a new threat ahead. |
| P23-AQ | `grade_e1` is frozen; the death signal lands in `grade_e2`. |
| P23-AR | The ninth session stays unspent and the plan closes after the E5 and F1 write-ups. Iteration 5 (the horde) is the next plan's design question. |

**The sessions** (ledger counts): eight of nine used: X4-3, X5-2, E1–E5 and F1. X4-3's first two launches were refused at the 12 GB memory gate with no boot, so they are not runs (ledger L133, L152).

**The reviews** (a count of the workspace's `review-*.md` files when this report was written): 63.
- 36 were first reviews: one per offline task (Tasks 1–15, 9b and 16a–d), the whole-pass review, four survival iterations, the shots, the UI tidy, the death event, `grade_f2`, and the seven write-ups (X4-3, X5-2, E1–E5).
- 27 were scoped re-reviews, the fix wave's and the residual round's among them.
- **The first reviews that did not pass on the first round:**
  - Task 2 and the death event on quality;
  - Task 8 on a Critical;
  - Task 13 on the spec;
  - the whole-pass review on principles 5 and 9;
  - survival 1;
  - survival 2, and its first re-review;
  - survival 3 and survival 4;
  - the write-ups of X5-2 and E1–E5.
- The F1 write-up's review and the E5 fix's re-review were in flight (ledger L284–L286).

**The test count** (ledger, each from a saved output file):

| Point | Passed | Source |
|---|---|---|
| The Plan 22 close | 9481 | CLAUDE.md § 3 |
| Task 2 | 9520 | |
| Task 4 | 9535 | |
| The fix wave's HEAD `278ee76d` | 10020 | `full-pytest-wave.txt` |
| The death event `a7fb6ff9` | 10233 | |
| The close | `10298 passed, 28 skipped (2026-10-29, `close-full-pytest-1.txt` in the workspace, at 2f7664b4 with the F1 pages uncommitted: docs only)` | |

One test was deleted by name: `test_base_world.py::test_the_widened_patterns`, with the removed regexes, Task 9 (ledger L76).

**The deferred items the close pass carries** (`close-pass-items-raw.txt` in the workspace, with the ledger's later lines):
- **The per-task minors left deferred:**
  - Task 1: `fixture.py`'s local import; test 1's assertions.
  - Task 2 N4: `last_frames` persisted each save.
  - Task 3: two offset labels.
  - Task 4: the tests' local square builders.
  - Task 5: the fault hosts' tick poke; `live_writes` order.
  - Task 6: the fingerprint's re-calls; the door-closing test.
  - Task 7: the exact-fit result.
  - Task 9: Bresenham's docstring, `_me_xy`, long lines.
  - Task 9b: `use` on every first-sight event; `by_use`'s `KeyError`.
  - Task 10: N1–N5.
  - Task 11: a re-scan does not free a capped square.
  - Task 12: M1, the south/east door outdoors; the done-plan `Sleep()` without `inside()`.
  - Task 13: cooled entries never pruned; building lines trimmed first.
  - Task 14: a stuck abandoned worker unrecorded; the place check's list; nits.
  - Task 15: `gate_e1`'s lineage sources.
  - Task 16d: the duplicated day constants.
  - Task 18: N1–N4.
  - The residual round's #8: three long lines.
  - The fix wave's D-1 to D-8.
  - The X4-3 review's Minor 2 (a row for the `me` group's lost elision) and Nits 3–6.
- **The close-pass items:**
  - the brief-trace rule for `docs/process/lessons.md` (§ 6);
  - the edge-crossing research thread (E2's walk over `blockW` edges);
  - `Base.Disinfectant` read as water by `W.useOf` (E1, E2);
  - the CLAUDE.md § 5 clients clause and the harness page sentence for P23-AN;
  - the harness page sentence and `day.py:41` naming `e_grade_2.py` as a new session's grade command.
- **The writers' open concerns:**
  - E4: a shot's `seq` lag; `grade_e1` misreading a `day_cap` session.
  - E5: `grade_e2`'s minutes running 0.054 past the death; the corner kind inferred.
  - F1: the corner overriding every flee; `decision.log` naming the stand-in source; the health-0 inference's counterexample.
- **The parked survival notes:**
  - iteration 4's four-held block on a closed room;
  - no cap on successive line-clear walks;
  - a retarget-to-nearest-in-reach rule.

Model: claude-opus-5-5

## 9. The close review

The close review (`review-close.md` in the plan's workspace, opus, over the live phase's code as one body) said CLOSE with nothing to land first, and left Plan 24 four Important planner findings from F1's decision log, all behaviours the live deaths exposed rather than defects in what the plan claims: a `walk` corner overrides the `health` flee (the corner is tested before the flee reasons and never reads health; F1's last fight held a walk corner from health 99 to 0.9: the proposed ruling is that a walk corner yields to `health`, `unarmed` and a running `many` episode when the last leg is not stuck, while `stuck` and trapped corners keep the override); the point-blank re-pin alternates between two zombies (about eight swaps in F1, against § 7's "never swaps": re-pin only when the pin itself is beyond point blank); an approach walk is sent at point blank (F1 walked at 0.49 tiles); the group steer runs on a room square with a way out, against P23-AK's "never steer inside". Two minors: a re-planned tick runs the breach test twice, and the corner's kind is not logged. The constants are each defined once; `EXIT_STALL_S` and `STEP_STALL_S` are one quantity under two names, `CORNERED_R` carries two, and `CORNER_FREE_R`, `CLOSING_TICKS` and `SPRINT_MAX_S` lack a provenance tag. The driver copies differ only in their keys and grade lines; the Lua, `pzt`, the tests (the pzagent folder 1906 passed at the close) and the lessons rules pass. The spec's § 14 carries the five amendment lines its item 7 named. The three refactors it recommends for Plan 24, after a `Survive` decision golden is recorded (none exists): (A) a `Corner` state object and a pure, ordered, named-rule `assess()` logged by rule name, removing the re-plan recursion; (B) `Flee` split into a shelter run, an exit run and a steer leg over one walk-progress tracker and one stall constant; (C) one immutable per-tick threat snapshot (the held list, distances, lines, the radii counts) shared by the decision and the policies.

