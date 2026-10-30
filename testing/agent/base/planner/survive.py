"""The scripted survivor (Plan 22 Task 10, spec § 3): a priority list over the World, ticked by its driver.

`Survive(world, actions, log_path, clock, source=None).tick(world, actions)` tries the branches in order (threat,
care, need, load, night, goal; Plan 23 Task 12 added `load` and `night`, Task 13 replaced `forage` and `explore` with
the goal, Plan 24 Task 10 `care`), takes the first that answers, and returns the `Action` it sent or None. Refactor A
(Plan 24 Task 21, the reviews of Tasks 12 and 18): a tick is `_read` (the actions' ends and the marks they make, the
logged inputs), `assess(inputs) -> Decision` (the ordered branches, nothing sent or written) and `_apply` (the send,
its bookkeeping, the goal runner's hold report and the decision line). A branch
answers with a command to send or, while its own action is still current, with none (it holds: nothing is sent and
no lower branch runs). A branch whose answer differs from the current action's sender sends at once, so a higher
branch pre-empts a lower one's action (the Lua fails the old one `superseded`). The branches run the policies of
`policies.py`; `need` is one `Consume`. Every tick appends one JSON line to `log_path` (decision.log): `{wall,
gameMin, branch, inputs, action, sent, goal}`, sorted keys, `wall` from the injected clock, `action` the command's
`type` and `args` or null, `goal` the goal runner's `{type, args, state, source}` (the running goal, or the one that
ended this tick; null when none), so a replayed session reproduces its decisions byte for byte.

The thresholds and the threat hysteresis are Plan 21b's (`testing/agent/policy.py`'s docstring, frozen; ported):
- A zombie is a threat within DANGER_R; while a threat policy runs (the "mode", `fight` or `flee`, kept while the
  threat branch answers), the branch holds every zombie within DISENGAGE_R: a threat engaged at 6 tiles holds the
  branch until it is beyond 10 or dead, so the bot never turns its back to loot. DISENGAGE_R is also the radius at
  which the Fight drops its pinned target (`policies.Fight`, Plan 23 Task 10), so it lives in `policies.py`.
- The hold-radius fix (`docs/reference/research-notes.md`, "The hold radius widens the 'too many' count"; the Plan
  21b ledger's ruling): `pair` counts the zombies within DANGER_R only; `held`, which keeps a flee running, reads the
  held list, being the hold itself. `many` (ruling P23-AG 2, the chain's E1: a fight engaged with one zombie fled only
  once four were within 6, and died) counts the held list while a fight runs and the DANGER_R count otherwise, so a
  fight engaged at 5 tiles with two more zombies closing from 8 and 9 turns to a flee before they are within 6.
- Fight or flee: flee when unarmed (`world.weapon` is None), when the `many` count > MAX_FIGHT, when health <
  FLEE_HEALTH, or when that count >= 2 and either health < FLEE_HEALTH_PAIR or the body carries a wound (the frame's
  `body.bleeding + scratched + bitten` > 0, a missing count read 0; Plan 23 Task 10: a wounded player does not take
  on a pair at any health), the reason `pair`. A running flee turns back to fight only with
  one held threat and health >= FLEE_HEALTH + REFIGHT_MARGIN, and a flee sent because a fight stalled is held while
  the nearest stays beyond FIGHT_REACH; a running fight turns to flee only on the flee conditions or its stall
  (`Fight.stalled`: its target beyond FIGHT_REACH for more than FIGHT_MAX_S unbroken seconds), never because a
  threat count dropped; the stall guard reads the distance to the Fight's target (`Fight.target_dist()`, the pinned
  one), the zombie its stall clock follows, never the nearest held one (Task 10's review M3). The flee steers from
  the held threats (`policies.Flee`: every leg away from each by 1/distance, turned off a known edge and off a
  held group ahead).
- The flee to shelter (ruling P23-AG 1, fix round 1): each flee episode's `Flee` takes the night's shun store and, at
  its first choose, a known building's exterior door within `policies.SHELTER_FLEE_R` with no zombie in its corridor
  and none inside the building; it then runs the night's shelter steps at a run, a failed step falling back to the
  steer (`policies.Flee`). While those steps run (the close not yet ended) the inside hold below waits, since the
  character stands inside with the door still open. Once the close ended inside (`sheltered`: the Flee's plan done
  and the character inside) the inside hold applies; when it does not (a line clears), an armed character fights only
  the reachable held threats standing in the building's doorway or inside it (`policies.in_building`; the Fight's
  `only`), whatever the flee reason (`many` and `health` included: a doorway kill beats running out into the group),
  and with none there the Flee answers (reason `sheltered` when no other holds): it holds while every threat reads
  line-blocked, re-closes an open door, else falls back to the steer. The sheltered Flee is kept across the door
  fight, so after the doorway kill it re-sends the close; both log `sheltered`.
- The flee's load drop (Plan 23 Task 10): run 2's last flee was pinned at load level 4. While the mode is `flee` and
  the frame's load level is at or above `policies.DROP_AT` (3), the flee episode's first free answer is one `Drop` of
  `LootHouse.spare()` (logged `flee_drop`, the item's id), sent as the Flee's own action so its steer waits on the
  drop (the drop skill is quick) and follows on the next tick; at most one drop per episode (`flee_dropped`, reset when
  the mode leaves `flee`), none when nothing is spare.
- Unreachable (the whole-pass review's I2): a target whose STALL_SWINGS started swings took no health, or whose line
  stays blocked after the Fight's one reposition (or has no clear square to reposition to), is skipped for
  UNREACHABLE_S (`policies.Fight`); Survive keeps that memory in `unreachable` across its Fights, and when every held
  threat is skipped the branch flees (reason `unreachable`), never attacking it again until its time runs out.
- Held inside (fix wave P, M-6): when the character is `inside()` (the night's read: a room square) and every held
  threat's line reads blocked (`policies.line_to` False: both end squares mapped, a wall, closed door or intact window
  between), the branch holds with no command (logged `flee: held_inside`) instead of fighting or fleeing out of its
  shelter; the hold ends when a threat's line clears or reads unknown, or the character is not inside.
- Survival 2 (ruling P23-AJ, the chain's E2: it died at game minute 592 inside building 3, the hold standing while a
  zombie closed from 5.78 to 3.05 tiles behind a wall the map read, then nine sprint steers pinned against its own
  room's walls, the bat never swung). `_threat_plan` makes the branch's one decision from the inputs (cornered, hold,
  door fight, broken hold, sheltered, Plan 21b's hysteresis; its docstring is the order), the Fight and the Flee only
  executing it:
  1. Every hold breaks (`_breach`, logged `breach`) with a held threat within HOLD_BREAK_R (3.0) whatever its line
     reads (`near`), or once the nearest held threat has read nearer than the tick before on CLOSING_TICKS (3)
     consecutive ticks within DANGER_R (`closing`: a threat coming through an opening the map does not show). That is
     the M-6 hold and the sheltered Flee's (its `hold_ok`). A broken hold flees when a way out of the building is
     known (`policies.exit_plan`: the Flee walks out, rule 3), else fights with one or two held and one reachable,
     else flees.
  2. Cornered (`_cornered`, logged `cornered`: the zombie id): armed, the nearest held threat within CORNERED_R (1.5)
     and either the flee's last steer leg ended stuck or the character on a room square (fix round 1: at melee range
     inside, the fight comes before any walk out), the Fight runs on the nearest reachable held threat whatever the
     count (MAX_FIGHT aside) or the flee reason, keeping its pin and stall and its line check beyond POINT_BLANK_R
     (1.0; within it the swing goes whatever the map's line says); it ends when that zombie is dead, gone or marked
     unreachable, or the nearest held threat is beyond CORNERED_R (a corner taken on a room square) or CORNER_FREE_R
     (5.0, a stuck leg's), and the next flee is a fresh Flee whose first leg is not stuck.
  3. Inside a building the flee walks out (`policies.Flee`'s way out, `night.exits`: the building's openings and its
     closed exterior doors; fix round 1: the nearest whose straight line passes no held threat within 1.5 tiles);
     with none it adopts the building (the sheltered hold, the re-close, the door fight), else, armed, fights the
     nearest (`_trapped_fight`), else holds (an unarmed character inside with no way out stands: the review's M4):
     on a room square it never steers. No window's edge is a way out; a walk out that stops moving for 1 s is
     dropped, and the corner pre-empts a running walk at melee range. While a walk out runs the inside hold waits,
     as for the shelter steps. The door fight stays for a sheltered building, ahead of the corner.
- Survival 3 (ruling P23-AM, the chain's E3: it died at game minute 600 after a fight and a `many` shelter flee
  superseded each other four times in 8 s, then the shelter's enter walk stood while a group of six closed):
  1. A flee started under a group stays a flee (`flee_many`, the episode's reason once `many`; `_many`): while it
     runs, `many` reads the hold radius's count over MAX_FIGHT or the nearest held threat within DANGER_R, so the
     fight resumes only with at most MAX_FIGHT held, the nearest beyond DANGER_R, and the `held` and refight rules
     above passed. A flee the hysteresis would end is kept (`_kept_flee`) while a `many` episode's shelter steps or
     way out run (`steps`: their end is the flee's), and while the Flee's own walk or steer leg sent under FLIP_MIN_S
     (5 s) ago runs and the Fight would walk (`flip`); a flee is never held back for a fight's walk (the retreat wins
     the tie).
  2. A shelter step's walk that stands WALK_STALL_S with a held threat within DANGER_R is dropped (`policies.Flee`,
     `ended` `stalled`): the plan for the episode, the steer at once.
  3. (A `many` flee sprinted while the endurance allowed; ruling P24-O removed it with every sprint: the flee runs.)
  4. GROUP_R_N (3) or more held within CORNERED_R after a steer leg that moved are steered from, not cornered
     (`group_steer`, `Flee.steer_now`, on a room square too); after a stuck leg, or against one or two, the corner
     stands.
  The coordinator's amendments (E3's write-up): 5, an exterior door is one whose own edge joins a room square to an
  outside square (`World.door_way`, `night.exterior_doors`), the approach square that outside square; 6, the corner
  is judged on every threat tick whatever runs (`_cornered`'s `walk` corner: a line not read blocked, no mark; a
  running fight keeps its pin), so a shelter or exit walk at melee range is superseded by the corner's attack, or,
  with a group (`_group`) and no stuck leg, by rule 4's steer (`Flee.give_way` drops the walk); rule 4
  then reads "not stuck" for "a leg that moved", a walk having no leg.
- Survival 4 (ruling P23-AP, the chain's E4: it died at game minute 627 after a `walk` corner on one or two zombies
  held 35 ticks while the group formed outside 1.5 tiles, and a steer leg aimed before two zombies ahead were listed
  ran into them; twelve walks from one stuck square cost 21.85 game minutes before):
  1. The goal source leaves a stuck area (`world.unexplored_edge` after two unmoved stuck walks from the player's
     square: only a square in the open, else a loot or the scan; `goals.py`'s docstring).
  2. A corner ends for a closing group (`_group`): GROUP_HOLD_N (4) held, or GROUP_R_N (3) within GROUP_NEAR_R (3.0
     tiles), whichever first, ends a `walk` or `inside` corner and blocks a new one while the last leg is not stuck
     (the group steer, logged `group`); a `stuck` corner keeps swinging, but with the nearest beyond POINT_BLANK_R
     and its stuck read STUCK_RETRY_S (2 s) old one steer leg is tried (`group` "retry").
  3. A running steer leg is cut and re-aimed when a held threat comes ahead of it (`policies.Flee._cut_leg`).
- Survival 5 (ruling P24-A, Plan 23's close: four of six deaths came with a group gathering while a fight or a
  corner held the character, #4237, #4251, #4262, #4268; the close review's I1-I4 and M1-M2), the rows of the decision
  each named in `why`:
  (a) The `many` reason also fires on MANY_LISTED_N (4) or more zombies listed within `policies.LISTED_R` (12 tiles),
      whatever the DANGER_R or hold count (`_many`, logged `listed` when it alone made `many`; since ruling P24-AD,
      Plan 24 Task 21, an idle zombie, `hasTarget` false, counts in both only within DANGER_R); the World keeps a
      memory of met ground (`World.met`, MET_TTL_MIN game minutes) whose densest window repulses the flee's first leg
      (`policies.Flee._steer`, logged `met`). The branch is still entered by a held threat only.
  (b) A fight that would walk toward its target (beyond FIGHT_REACH, an approach due beyond POINT_BLANK_R, or the
      reposition of a blocked line) with another zombie listed within LISTED_R beyond it and within AHEAD_CONE of its
      bearing (`policies.others_behind`) flees `held` instead (`_behind_walk`, logged `behind`), `many` read first.
  (c) A `walk` corner yields (`_walk_yields`, logged `yield`) to the `health` reason and to a running `many` flee
      episode: a running one ends, a new one is not taken; `unarmed` never corners; the `stuck` and `inside`
      corners keep the override.
  (d) The cornered Fight's point-blank re-pin goes only while its pin stands beyond POINT_BLANK_R
      (`Fight._repin_point_blank`).
  (e) No approach walk at point blank: within POINT_BLANK_R the Fight clears the flag and attacks.
  (f) On a room square the group's flee never steers: the running exit, else a new one, else the adoption, else
      the trapped hold, the next tick's corner (`Flee.choose`, `Flee.give_way`); P24-O runs the exit, never sprints.
  (g) `corner_kind` is logged beside `cornered`; each policy's `observe` runs once a tick (`_observe`), the Flee's
      over this tick's held records, and the breach once (`_threat` is the bookkeeping, `_decide` the decision a
      corner's retarget re-plans); WALK_STALL_S and STUCK_NEAR_R (`policies`) name the merged and the split constants.
  (h) The drag-down guard (#4290, #4291; `_drag`): with the frame's `me.attackers` at DRAG_DOWN_N - 1 (2) or more,
      first of every row, the fight or corner of any kind ends for the group's flee (`group` "drag"; inside, the exit
      by (f)), except on a room square with no way out and nothing to adopt, where no leg exists and the corner swings.
  (i) No attack in a hit reaction (#4292, #4293): while the frame's `me.hitReaction` names one the Fight sends
      nothing (logged `hitReaction`) and attacks on the first frame after it clears; a running attack holds anyway.
  A PZA/1.3 frame carries neither `attackers` nor `hitReaction`: (h) and (i) read them absent and change nothing.
- Survival 6 (ruling P24-G, Angus's direction of 2026-10-29 after F2's shots; the jar reads #4294-#4304), each sent
  only to a build whose hello's caps carry the skill (`World.can`; the five live artifacts' hellos announce none, so
  their goldens do not move; the sixth golden, `f1-caps15`, replays F1's frames with them announced: Task 10 fix 1):
  1. The standing fight (`_stance_ok`, `policies.Fight.standing`): a `fight` from the hysteresis (or a broken hold's)
     with one held at health >= FLEE_HEALTH or two at >= FLEE_HEALTH_PAIR, armed, not trapped on a room square,
     opens in the stance and keeps it (ruling P24-N, superseding P24-M after E6): every leg an `aim` facing the
     target for `policies.AIM_LEG_S` (`policies.Fight._stance_leg`), the first one too, backpedalling along
     `policies.away_vector` of the held threats while the target is inside `policies.KEEP_R`, standing facing it
     farther off; it swings from the stance within reach (the stance leg gives way at once: `Fight.busy`), and after
     `policies.STAND_MAX_S` with no fall of its target's health (a kill restarts it on the next) closes on it in the
     stance (`Fight.advance`, an aim toward it; the approach walk only round a wall), its stall clock starting then;
     at the first stance leg that ends failed, timed out or rejected (Task 10 fix 1, minor 11) it falls back to the
     approach and swing (`Fight.standoff`); the flee rules, the corner (`point_blank`) and the door fight (`only`) are
     as before, and the look past a fight's walk target (P24-A (b)) reads no walk while the Fight stands, and reads
     the advance as one.
  2. The care branch (`_care`, `planner/care.py`'s docstring the record), between `threat` and `need`: with no
     threat held (or, ruling P24-P, Task 12, with one held while the nearest listed zombie is beyond `care.CARE_R`
     and no `many` reason live: the threat branch yields, `_care_yields`, logged `care`, only when the bleeding step
     would send or runs; Task 12 fix 1's hysteresis: it starts only with the nearest not closing over
     `care.CARE_STILL_TICKS` ticks and no flee leg running from a chaser, a held zombie whose `hasTarget` is set,
     and a running bandage is superseded only once the nearest is inside `care.CARE_HOLD_R`, or no part bleeds any
     more; the ride, ruling P24-U: under a running flee leg, a steer or a walk on an open line, with the nearest
     beyond `care.RIDE_R` or no zombie chasing, a part above the legs is bandaged with keepMoving, the leg kept
     running at a walk, whatever the `many` reason; the Flee's re-aims during it are new legs that keep it, any other
     send ends it, so no ride starts in a fight and the Fight's stance legs are held off while one runs, logged
     `ride`), the worst bleeding part bandaged with the best held item (a bandage, a clean rag, a dirty rag only
     past `care.DIRTY_RAG_MIN`), with no rag of any kind held a cotton garment ripped for it (never one of the
     inventory's first sight; never with no wound: Task 10 fix 1, the review's major 2), a spent bandage replaced
     with a clean one, a dirty rag washed at a known water source within `care.WASH_R` with no zombie within
     DISENGAGE_R; its own action holds the branch, the Sleep passes it, and a refused item waits
     `care.CARE_RETRY_MIN` game minutes.
  3. The water chain (`_need`, then `planner/water.py`'s `Water`, its docstring the record since refactor A): thirst
     over THIRST_T drinks a held `water` item, a clean one first (`World.tainted_ids` only with none clean); with
     none, a held `container` is filled (`fill`) at the nearest known clean source (`Water.plan`), its done marking the
     vessel `filled` or `tainted` (`Water.check`; `by_use` then reads it water, so the next tick drinks it); a source
     that failed is left out, a vessel that failed otherwise waits FILL_RETRY_MIN. `world.by_use()` is read once a
     tick (`_by_use`, minor 14). The wants (`need_marks`, the view's `needs_wanted`): `water` whenever nothing is
     drunk or filled; `container` beside it only with no vessel held at all; `water_source` beside it with a vessel
     held and no clean source known (`Water.wants`, P24-L). A tainted drink refused `not valid` is marked
     `undrinkable` (`_refused`). The World applies PZA/1.5.1's `item_changed` (the engine's own re-read of a vessel's
     use and fluid). The no-effect mark (P24-F) is unchanged.
  4. The climb in routes is the goals' (`goals.Kit.hop_after`, `World.hop_ahead`, in `ExploreToward` and, since Task
     10 fix 1, minor 9, the `Shelter` goal's walks): a walk failed `stuck` at a hoppable edge on its line's first
     step climbs it (`climb`) and walks on; the flood and the path follower's own
     climbs need nothing; no steer or backpedal ever crosses a hoppable edge (`policies.clear_heading`), so nothing
     vaults. 5: no look-around (jar reads 2 § 6: the frames list every zombie whatever the facing).
- Survival 8, the fight sought (ruling P24-X, Plan 24 Task 18; E7, `e_day_7-20261029-140813`, killed nothing in 227
  game minutes: its three fights fled a group listed within 12 tiles, and of the 1420 lines the replay aligns the
  goal ran on 160 with one or two zombies listed within 10 tiles and none within 6, on 47 of them one chasing;
  Angus: "he completely forgets zombies are nearby"): with no threat policy running, one or two zombies listed
  within `policies.ENGAGE_R` (10; 9 since Task 18 fix 1's minor 8), a weapon in hand, health at or above `_fight_line` (FLEE_HEALTH for one, FLEE_HEALTH_PAIR for two, a pair only
  unwounded: `_takes_on`), no `many` reason (`_many_read`) and one of them a target (`_sought`; never while the
  night's Sleep is current), the threat branch holds them all (`engaging`, the hold radius ENGAGE_R that tick) and
  fights: every Fight it makes but the door fight's is sought (`Fight.seek`: a `seek` stance leg toward the target
  until it comes within KEEP_R, then iteration 7's stance; a walk at a walk beyond AIM_R), and the look behind
  (P24-A (b)) reads the seek as a walk but never the one or two it was sought against. A flee turns to fight one or
  two held at the fight's line (`_hysteresis`'s `held` rule is `_takes_on`; before, any second held zombie, or one
  under FLEE_HEALTH + REFIGHT_MARGIN, kept it), once its own running leg ends (`flip`); a `health` episode
  (`flee_health`) keeps the refight margin, and a `many` episode stays `many` while its nearest is within DANGER_R
  (P23-AM 1, read as P24-X's "no `many` live"). The goal branch never runs while such a fight is to be sought.
  `ENGAGE` and `SEEK` are class switches, the replay tests' seams onto the rules before P24-X.
  Task 18 fix 1 (the review's blocker, major 2 and ruling 2): only a zombie the engage reaches is engaged
  (`_engageable`: on the character's side of a building's walls, and chasing, or its line clear, or a square beside
  it in the player's bounded flood, `_reach`; one that is not is marked `unsought` for UNREACHABLE_S and logged, and
  the goal runs: E4's gate zombie, the spawn's idle zombie on unscanned ground); a running fight with nothing left
  within DANGER_R that it may engage ends (`_released`), and never pins anew beyond DANGER_R a zombie no engage
  reaches (`avoid`); a character holding ground (`_chokepoint`: on a room or door square) never seeks, the stance
  standing there, and with no stance (a PZA/1.4 build, trapped) engages nothing; a chasing target across a known
  fence is not sought (`policies.seek_allowed`). The Fight's seek closes on the nearest zombie and its walks give way
  as its legs do (`policies.Fight._walk_gives_way`, `_seek_switch`).
- Survival 9 (Plan 24 Task 21, spec § 6 item 19; E8, `e_day_8-20261029-174023`: four kills, then a bite bled 73 game
  minutes to the death with no dressing held, every goal walk from game minute 618 failed `no square`, and fight 1
  fled `many` from one chaser and two idle zombies): P24-AB, the rag stock (`care.Care.stock`, `_care_stock`: on an
  idle tick, behind the need, the load and the night, an unworn cotton garment ripped while fewer than
  `care.RAG_STOCK` clean dressings are held; a bleeding part with nothing to dress it marks the want `bandage`,
  `_dressing_want`, the goal layer's loot taking it first); P24-AC, legged far walks (`goals._Legs`); P24-AD, an idle
  zombie (`hasTarget` false) counts toward `many` only within DANGER_R (`_counts_many`, the `IDLE` switch).
- Survival 10 (Plan 24 Task 24; PZA/1.6.1): the stock also wears (`care.Care._wear`, the better garment by the rule of
  review-t9-fix9; `World.worn` is `me.worn` kept across null frames), the goals loot clothing (`goals.wanted_uses`) and
  route a stuck-door building through a window (`goals.window_pick`), and the view carries `worn`.
- Survival 11 (survival iteration 10, the commit label; Plan 24 Task 27, spec § 6 item 20 and amendment 6's guides' rulings; PZA/1.7; the jar reads #4368-#4377;
  the eighth chain killed four in three standing fights and bled out standing): P24-AG, strain-aware fighting: a
  spent character (`_read_spent`: the arms' strain hold, from `body.armPain` STRAIN_HARD 20 until it reads
  under STRAIN_SOFT 10; the ENDURANCE moodle's first level, `stats.endurance` ENDURANCE_T 0.75 or under, held until it reads above ENDURANCE_RELEASE 0.80; and P24-AK's
  tired gate, `stats.fatigue` TIRED_FIGHT_T 0.6 or above) flees `strain` (`_hysteresis`, after `pair`; the why's
  `strain` names the kind and the reads), engages and seeks nothing (`_sought`), and a `walk` corner yields `strain`
  after `health` and a running `many` episode (`_walk_yields`); the `stuck`, `inside`, trapped and door fights still
  swing, no leg leaving them. Under STRAIN_SOFT's line the Fight's own preference, the shove and the stomp (P24-AH,
  P24-AL) are `policies.Fight`'s; the loaded-window legs (P24-AI) `goals.leg_max`; the unwear then rip (P24-AJ)
  `care.Care._unwear`. `STRAIN` is the replay tests' seam onto the rules before it (`test_replay_decisions.pre_ag`).
- Survival 12 (survival iteration 11, the commit label; Plan 24 Task 32, spec § 6 item 23; E9,
  `e_day_9-20261030-052429`: no kill, every fight from game minute 580 with a group listed, six fights dropped by the
  look behind for a chaser 10.74 to 11.90 tiles behind the target, the strain hold set by a bite's pain and never
  released, two struck targets left fallen under the `many` flee, five rags held to the death, the y held 16.511 s
  against a `solidTrans` row; the guides notes § 9 changes 8, 3 and 2; rows #4290, #4369, #4370, #4373, #4374):
  P24-AN, the pull (`policies.Fight.pulling`, `pull_from`: one zombie chasing within ENGAGE_R, the rest of the
  listing beyond DANGER_R: the stance walks away from their centroid until the chaser is within PULL_R, then stands;
  the look behind reads no walk then, `_pulls`; the `many` listing counts a zombie only within DANGER_R or chasing,
  `_counts_listed`); P24-AO, the doorway stand (`planner/doorway.py`'s docstring the record; `_doorway`, `_stand`);
  P24-AP, the wounded fight (`_wounded_fight`: the arms' hold alone flees `strain` only with no zombie within
  KEEP_R; the Fight never swings at STRAIN_HARD, `policies.Fight._wounded_leg`); P24-AQ, the fallen target under
  `many` (`_flee_finish`: a struck target downed in reach, nobody standing within DANGER_R: one stomp, or the floor
  strike, as the Flee's own action, its kill read by `_finish_end`); P24-AR, the care tick inside a long flee
  (`_rides_many`: RIDE_MANY_R, FLEE_CARE_S from `many_since`, FLEE_CARE_N); P24-AS (amendment 1), the transparent
  solid (each policy's `trans`: a heading read and the way out's end refuse a `solidTrans` square). `PULL`, `DOORWAY`
  and `TRANS` are the replay tests' seam onto the rules before it (`test_replay_decisions.pre_an`); P24-AP to P24-AR
  read what no record carries.
  Task 32 fix 1 (review-t32, its rulings R1 to R3): the doorway stand's post (`policies.stand_post`: the enter walks
  to the room square one on from the threshold, since the Lua's walk ends `done` within DONE_R 1.0 and E9's enter to
  the threshold's own centre ended on the outdoor door square; the stand starts only on a room square of the building,
  `policies.on_post`, else the enter is walked again), its walk back giving way to a zombie in reach
  (`doorway.Doorway.busy`), and its `drag` (`me.attackers` at DRAG_DOWN_N, R1) and `off` (`doorway.off_post`) ends
  (`_doorway`); ruling R2 (`HOLD_WIDE`): every hold kind fights a zombie within KEEP_R, the Fight sending no swing
  under any (`_wounded_fight`, `_fight_spent`, `policies.Fight.no_swing`); the finish's reach FINISH_R (R3 as the
  review corrects it, `_flee_finish`); the stance's count (`STANCE_LISTED`, `_stance_count`: the standing held within
  DANGER_R or chasing, so a group idling 6 to 10 tiles off no longer turns the pull's stance off). `HOLD_WIDE` and
  `STANCE_LISTED` join the replay tests' seam (`test_replay_decisions.fix1_off`). And the minors: the ride's walk line
  and the reposition's squares read a `solidTrans` square as solid (`_ride_leg`, `World.reachable_adjacent`, under
  `TRANS`); the care tick's rule (b) never rides under the drag-down guard (`_rides_many`); the finishing stomp's end
  is read in `_read`, out of `assess` (`_finish_end`, `_finish_kill`).
- `need` (Plan 23 Task 11, P23-7): Plan 22's character never ate or drank, its thresholds 0.5, which vanilla reaches
  in 17 to 20 game hours; the needs now fire at the game's first moodle, THIRST_T 0.12 (#0509) and HUNGER_T 0.15
  (#0508). While its own `Consume` is current the branch holds, before any threshold is read (a frame that already
  reads the drink's effect must not let a lower branch supersede it); while the night's `Sleep` is current (sent,
  accepted or in progress) the branch sends nothing and passes, logged `holding_sleep` (ruling P23-AB: the night's own
  hold then answers the tick, and the needs are answered at the wake; the threat above still pre-empts the sleep);
  else thirst > THIRST_T consumes the held item of least id whose use is `water` (`world.by_use()`: the dataset's
  drinkable, non-poisonous fluid containers, an id marked empty left out), else marks `water`; then hunger >
  HUNGER_T consumes the held `food` item of least `items.days_fresh` (the most perishable first, the spec's "smallest
  spoil risk"; a food with none last; ties by least id: fix wave P, I-4), a sealed can (`cant_eat`) never being food
  and a refused id left out, else marks `food`; nothing held, the branch passes (to the goal). Each mark is also kept in
  `need_marks` {use: wall of its last mark} (both uses, where `need_mark` logs the first), which the view reads as
  `needs_wanted` for `view.NEED_MEMORY_S`; a held item of the use found clears its mark.
- The empties (P23-D): a `Consume` whose action ended `failed "not valid"` on an id `by_use()` reads `water` marks it
  empty (`world.mark_empty`), so the next tick takes the next bottle and `spare()` may drop it; on an id it reads
  `food` marks it refused (`world.mark_refused`, fix wave P I-4, P23-AD: `by_use` then reads it `other` for
  `world.REFUSED_TTL_MIN` world minutes, so the need does not retry it meanwhile and takes the next food), logged as
  inputs.consume_refused on the tick that read the end (else None), as is any other id refused so (one no longer
  held when the end was read), which is never marked.
- The no-effect mark (ruling P24-F; F2 drank a `Base.Disinfectant` its Lua read `water` 68 times in 14 game
  minutes, every consume `done`, thirst 0.12 to 0.133, the character parked on one square): each `Consume` the need
  sends is remembered with its use, its stat (`NEED_STATS`: thirst for water, hunger for food), the stat at the send
  and the world minute (`world.world_minutes()`). Once it has ended `done` and CONSUME_CHECK_MIN (1) game minute has
  passed since the minute its done was first read (never since the send: the Lua reports done at the first fall of
  the fluid), the stat is checked once: fallen by less than STAT_FALL_MIN (0.01), the item still held is
  marked no-effect for the session (`world.mark_no_effect`: `by_use` reads it `other`), so the branch moves to the
  next item of the use, or marks the want and passes to the goal's loot when none is left. An item whose consume
  ended, done or failed (never one superseded, forgotten), is not consumed again within CONSUME_RETRY_MIN (5) game
  minutes of that send (left out of the pick). The decision line carries `marks` {itemId, reason "no_effect"} on
  whatever branch's line the tick that marked writes; the need's `why` carries `no_effect` {itemId, use, stat, fell}
  on that tick when the need ran, and `retry` (the ids left out by the window) only when a need was wanted and
  its held item is inside the window, each only then, beside `item` and `mark`. The branch never consumes a `container`
  (PZA/1.4.1, an empty vessel): Task 10's water chain fills it (survival 6, 3); with no `water` held and nothing to
  fill it marks the want.
- `goal` (Plan 23 Task 13, P23-10; ruling P23-F): `goals.GoalRunner` over the goal source (`source`, default
  `goals.ScriptedSource()`; Task 14's LLM source shares the seam), whose module docstring is the design record: one
  goal at a time, proposed from `view.view(world, self)` (built only on a tick that proposes) when none runs,
  `superseded` when an instinct sent since its own last action, failed at `goals.GOAL_MAX_S`. The old `forage`
  (P23-8: a loot for one use, never `all`, with `maxWeight` = the frame's `load.max` times
  `policies.LOAD_RATIO_MAX`, the level guard the backstop, spec § 9 (1)) and `explore` (scan each new place, walk to
  the unexplored edge) are now the `Stock`, `LootBuilding` and `ExploreToward` goals' steps over the same
  `LootHouse` and `Explore` (`policies.py`). A running goal holds the branch (no command while its action runs, or
  while it rests); with no goal running it passes. Its `why` is the goal's own plus `goal`, `args`, `state`,
  `reason`, `proposed` (the type proposed this tick, else None) and `ended` (the record row of a goal that ended
  before the proposal, else None).
- A command whose action ended `failed` (any reason but `superseded`, which this planner's own next send caused),
  `timeout` or `rejected` is not chosen again with the same type and args for FAILED_COOLDOWN_TICKS planner ticks:
  its branch is passed over and the next one tried (logged as inputs.cooled); the threat branch is never passed
  over. Every branch tried logs its own inputs under inputs.branches[<branch>].
- `load` (Plan 23 Task 12, split out of `LootHouse`): at load level `policies.DROP_AT` (3) or above it sends one
  `Drop` of `policies.spare(world)` a decision (logged `level`, `drop`), holding while that drop is current, until the
  frame's level reads `DROP_TO` (2); with nothing spare, or under DROP_AT, it passes. It runs before `night`, so a
  heavy load is dropped before the sleep; while the night's `Sleep` is current it passes as the need does (P23-AB).
- `night` (Plan 23 Task 12, P23-9): `night.Night` (its docstring is the design record). Its own running action holds
  first, before the want is read (a sleep is never superseded by its fatigue falling under the want); not wanting, it
  passes (logged `{"wants": false}`); wanting (counted in `night.wants_n`), it shelters in a known interior and
  sleeps, holds NOT_SAFE_S after a sleep refused `not safe` and NOT_VALID_S after `not valid`, stops wanting for the
  session after `not allowed` (ruling P23-U), and with no shelter known sets `night.want_shelter` and passes. Its
  `why` carries `step`, `building`, `shunned` and the sent action's `aid`.
- `last_branch` (Plan 23 Task 16c) is the branch of the last decision line (None when no branch answered), so a
  driver's action rows name the branch that sent each action without re-reading the log.
- Each tick ends by telling the goal runner whether a branch other than the goal answered without sending
  (`GoalRunner.held`), so a goal an instinct holds without a send is superseded `hold` (fix wave P, M-7).
- The log's inputs carry `mode` (the running threat policy at the tick's start, else None), `threats` (the DANGER_R
  count), `held` (the count within the hold radius), `fight_s` (the running fight's stall clock read before this
  tick restarts it, else None), and the frame's `fatigue` and `hour` (the night's inputs).
"""
import json
import math
import time
from dataclasses import dataclass
from typing import Optional

from agent.base.items import days_fresh
from agent.base.planner.care import RIDE_FREE, Care
from agent.base.planner.goals import GoalRunner, ScriptedSource
from agent.base.planner.night import Night
from agent.base.planner.policies import (DANGER_R, DISENGAGE_R, DROP_AT, FIGHT_MAX_S, FIGHT_REACH, PREEMPTED,
                                         STUCK_REASONS, blocked, item_id_ok, spare, zdist)
from agent.base.planner.threat import (CLOSING_TICKS, CORNER_FREE_R, CORNERED_R, DRAG_DOWN_N, FINISH_R, FLEE_HEALTH,
                                       FLEE_HEALTH_PAIR, FLIP_MIN_S, GROUP_HOLD_N, GROUP_NEAR_R, GROUP_R_N,
                                       HOLD_BREAK_R, LISTED_R, MANY_LISTED_N, MAX_FIGHT, REFIGHT_MARGIN,
                                       STUCK_RETRY_GROUP_S, STUCK_RETRY_S, Threat)
from agent.base.planner.view import NEED_MEMORY_S, view
from agent.base.planner.water import FILL_RETRY_MIN, FILL_SETTLE_S, FILL_WANTS, SOURCE_FAILS, Water
from agent.base.pza1 import Consume, Drop
from agent.base.world import me_floor, me_xy

THIRST_T = 0.12          # the first THIRST moodle fires above 0.12 [#0509]
HUNGER_T = 0.15          # the first HUNGRY moodle fires above 0.15 [#0508]
BRANCHES = ("threat", "care", "need", "load", "night", "goal")
STEPS = ("threat", "care", "need", "load", "night", "stock", "goal")   # assess() tries these in order: BRANCHES with the
                         # care's rag stock (P24-AB) before the goal (it logs under `care`, why `stock`)
KIT_WANTS = ("bandage",)   # the need marks the goals' loot takes first (`goals.Kit.wants`; ruling P24-AB)
FAILED_COOLDOWN_TICKS = 10   # planner ticks a failed command is not chosen again with the same type and args
FAILED = ("failed", "timeout", "rejected")
REFUSED = "not valid"    # the reason the Lua's consume fails an item it cannot eat or drink (an empty bottle)
NEED_STATS = {"water": "thirst", "food": "hunger"}   # the stat a consume of each use must lower (P24-F)
CONSUME_CHECK_MIN = 1.0  # game minutes after a consume's done is first read before its stat is checked (P24-F, fix 1)
STAT_FALL_MIN = 0.01     # the least fall of that stat since the send that counts as an effect (P24-F, a judgment:
                         # a drink or a meal moves its stat by tenths, F2's thirst rose 0.013 in 14 minutes)
CONSUME_RETRY_MIN = 5.0  # game minutes a consume that ended done leaves its item out of the pick (P24-F)
DOOR_FAILS = ("locked", "interrupted", "not adjacent") + STUCK_REASONS   # a door interact failed so is a door's
                         # failure, two of which mark it (ruling P24-Z); a loot's `not adjacent` counts on the door the
                         # player stands against (DOOR_NEAR_R)
DOOR_NEAR_R = 1.5        # tiles: a loot failed `not adjacent` counts on a door square this near the player (P24-Z)

__all__ = ["Survive", "Decision", "BRANCHES", "STEPS", "DANGER_R", "DISENGAGE_R", "THIRST_T", "HUNGER_T", "FLEE_HEALTH",
           "FLEE_HEALTH_PAIR", "REFIGHT_MARGIN", "MAX_FIGHT", "FIGHT_MAX_S", "FIGHT_REACH", "FAILED_COOLDOWN_TICKS",
           "HOLD_BREAK_R", "CLOSING_TICKS", "CORNERED_R", "CORNER_FREE_R", "FLIP_MIN_S", "GROUP_R_N", "GROUP_NEAR_R",
           "GROUP_HOLD_N", "STUCK_RETRY_S", "STUCK_RETRY_GROUP_S", "MANY_LISTED_N", "DRAG_DOWN_N", "FINISH_R",
           "NEED_STATS", "CONSUME_CHECK_MIN", "STAT_FALL_MIN", "CONSUME_RETRY_MIN", "FILL_RETRY_MIN", "FILL_SETTLE_S", "FILL_WANTS",
           "SOURCE_FAILS", "DOOR_FAILS", "DOOR_NEAR_R", "KIT_WANTS", "LISTED_R"]


@dataclass
class Decision:
    """`Survive.assess`'s answer (refactor A): the branch that answered (None when none did), the owner its command
    goes through (a policy or the goal runner; None for the need's and the load's own sends), the command (None: the
    branch holds its running action, or nothing answered), and the decision line's completed `inputs`."""
    branch: Optional[str]
    owner: object
    cmd: object
    inputs: dict


def _key(typ, args):
    return typ, json.dumps(args, sort_keys=True)


class Survive(Threat):
    def __init__(self, world, actions, log_path, clock=time.time, source=None):
        self.world = world
        self.actions = actions
        self.log_path = log_path
        self.clock = clock
        self.mode = None          # the running threat policy: "fight", "flee" or None
        self.fight = None
        self.flee = None
        self.stall_flee = False   # the running flee was chosen because a fight stalled
        self.flee_dropped = False  # the running flee episode sent its one load drop
        self.flee_many = False    # the running flee episode's reason was `many` (P23-AM 1: it stays a flee)
        self.flee_health = False  # the running flee episode's reason was `health` (P24-X: the health flee stays)
        self.engaging = False     # this tick: the threat branch was entered by the sought fight (P24-X), no zombie
                                  # within DANGER_R
        self.group_steer = None   # this tick: why a group at melee range is steered from, not cornered (`_group`:
                                  # "near" or "hold", P23-AM 4 and AP 2; "retry", a stuck corner's leg), else None
        self.sheltered = False    # a flee's shelter plan ended inside: a threat whose line clears is fought (P23-AG)
        self.door = None          # the door fight's targets this tick (`_door_targets`) while sheltered, else None
        self.broken = None        # the breach that broke a due hold this tick (P23-AJ 1), else None
        self.closing = (0, None)  # (ticks the nearest held threat has closed within DANGER_R, its last distance)
        self.cornered = None      # the zombie id a cornered Fight runs on (P23-AJ 2), else None
        self.corner_free = CORNER_FREE_R   # tiles: the nearest beyond this ends the corner (fix round 1)
        self.corner_kind = None   # "stuck", "inside" or "walk" (amendment 6: taken on any walk), the running corner's
        self.stuck_wall = None    # wall of the stuck read a `stuck` corner was taken on (P23-AP 2: STUCK_RETRY_S)
        self.stuck_heading = None  # the stuck leg's heading a `stuck` corner was taken on, handed to the next Flee's
                                   # first leg (P24-A fix 2, G2: its turn skips it, as F4's after a stuck leg)
        self._corner_fight = None   # the Fight made for the corner
        self.corner_yield = None  # this tick: why a `walk` corner yielded, "health" or "many" (P24-A (c)), else None
        self.behind = None        # this tick: the ids listed behind the fight's walk target (P24-A (b)), else None
        self.listed = None        # this tick: the listed count when it alone made `many` (P24-A (a)), else None
        self.stand_left = None    # this tick: `off` when the doorway stand was left off its post (P24-AO fix 1)
        self.stand_end = None     # this tick: any end the doorway stand took (health, drag, unarmed, quiet, off): the why only
        self.care_yield = None    # this tick: the nearest zombie's tiles when the threat yielded to the care (P24-P)
        self._nearest_seen = []   # (id, tiles) of the nearest listed zombie on the last threat ticks, newest last: the
                                  # care yield's closing read (Task 12 fix 1), CARE_STILL_TICKS + 1 of them
        self._observed = []       # the policies observed this tick (each once: P24-A (g))
        self.unreachable = {}     # zombie id -> wall until it is skipped (policies.Fight), kept across Fights
        self.unsought = {}        # zombie id -> wall until no engage re-reads its reach (`_engageable`, Task 18 fix 1)
        self.avoid = set()        # this tick: the ids within the hold no engage reaches (`_engageable`), else empty
        self._flood = None        # (map version, player square, squares): the engage's bounded flood (`_reach`)
        self.dead = {}            # zombie id -> wall until it is skipped, read dead (policies.Fight, Task 12 fix 1)
        self.strain_hold = False  # the arms' strain hold (P24-AG): set at armPain STRAIN_HARD, cleared under STRAIN_SOFT
        self.endurance_hold = False  # the endurance hold (P24-AG): set at ENDURANCE_T or under, cleared above ENDURANCE_RELEASE
        self.spent = None         # this tick's `_read_spent` (None: fit to fight)
        self.spent_kinds = ()     # every hold `_read_spent` read this tick, in its order (P24-AP reads them all)
        self.many_since = None    # wall of the first `many` reason since the threat branch last held nothing (P24-AR)
        self.struck = {}          # zombie id -> wall of the last attack or shove sent at it (P24-AQ)
        self.finishing = {}       # zombie id -> the `many` flee's finishing sends at it, "stomp" then "floor" (P24-AQ)
        self._finish_a = None     # the flee's last finishing action (P24-AQ), its end read once (`_finish_read`)
        self._finish_read = None
        self._finish_kill = None  # the zombie id the finishing stomp read dead this tick (`_read`), else None
        self.night = Night(world, actions, clock)
        # one shun store: the goals' Shelter shuns into the night's (Task 13 fix 1, M6), so neither re-tries the other's
        self.goals = GoalRunner(ScriptedSource() if source is None else source, clock, shunned=self.night.shunned)
        self.goals.kit.bind(world, actions)
        self.care = Care(world, actions, clock)   # the care branch's policy (P24-G 2)
        self.need_last = None     # the last Consume sent
        self.load_last = None     # the last load Drop sent
        self.need_mark = None     # "water" or "food" when need found nothing held this tick (logged)
        self.need_marks = {}      # use -> wall of its last mark: the view's needs_wanted
        self.consume_refused = None   # a non-water id whose consume ended failed "not valid" this tick (logged)
        self.consumes = {}        # item id -> {action, use, stat, before, at, checked}: the need's sends (P24-F)
        self.water = Water(world, actions, clock)   # the water chain (`planner/water.py`, P24-G 3; refactor A)
        self.need_use = None      # the use of the item the need picked this tick
        self.no_effect = None     # this tick: {itemId, use, stat, fell} of an item marked no-effect, else None
        self.ticks = 0
        self.last_failed = None   # (type, args json, tick first seen failed) of the last command that failed
        self._watch = []          # actions sent and not yet seen terminal
        self.why = {}
        self.last_branch = None   # the branch of the last decision line (a driver's action rows read it at the send)
        self._uses = None         # this tick's `world.by_use()` (`_by_use`)

    # ---------------------------------------------------------------- reading the world
    def _policies(self):
        return [p for p in (self.night, self.care, self.fight, self.flee) if p is not None]

    def _within(self, r, raw=False):
        """The listed zombies within `r` tiles, less those read dead within UNREACHABLE_S (`dead`, Task 12 fix 1: a
        zombie still listed on its kill tick is no threat; F1's line 333 fled 15937's corpse, `unreachable`); `raw`
        keeps them (the decision line's `threats` and `held`, the record's own readings of the frame)."""
        dead = () if raw else blocked(self.dead, self.clock())
        return [z for zid, z in self.world.zombies.items() if zid not in dead
                and z.get("x") is not None and z.get("y") is not None and zdist(self.world, z) <= r]

    def _health(self):
        h = (self.world.body or {}).get("health")
        return 100.0 if h is None else h

    def _wounds(self):
        """The body's bleeding, scratched and bitten counts summed (a missing count reads 0)."""
        body = self.world.body or {}
        return sum(body.get(k) or 0 for k in ("bleeding", "scratched", "bitten"))

    def _armed(self):
        return self.world.weapon is not None

    def _held_use(self, use):
        """The id to consume among the held items of `use` (`_by_use()`), else None: a food the least
        `days_fresh` first (None last); water a clean one (not in `world.tainted_ids()`) first, the least id, a
        tainted one only with no clean one held (ruling P24-G 3); an id inside its retry window left out."""
        recent = self._retrying()
        ids = self._by_use()[use]
        tainted = self.world.tainted_ids() if use == "water" else set()
        ids = [i for i in set(ids) | (tainted & set(self.world.inventory)) if item_id_ok(i) and i not in recent]
        if not ids:
            return None
        if use == "water":
            return min(ids, key=lambda i: (i in tainted, i))
        if use != "food":
            return min(ids)

        def spoil(i):
            d = days_fresh((self.world.inventory.get(i) or {}).get("fullType"))
            return (math.inf if d is None else d), i
        return min(ids, key=spoil)

    def _by_use(self):
        """`world.by_use()`, read once a tick (Task 10 fix 1, minor 14: the need, its pick and the fill read it); the
        tick resets it after the ends are read (`_note_failures`, `Water.check` mark items)."""
        if self._uses is None:
            self._uses = self.world.by_use()
        return self._uses

    def _retrying(self):
        """The ids a consume that ended (done or failed, never one superseded) was sent on within CONSUME_RETRY_MIN
        game minutes (P24-F; fix 1: a consume that always ends failed is not re-sent every few seconds)."""
        now = self.world.world_minutes()
        return {i for i, c in self.consumes.items()
                if self.actions.done(c["action"]) and c["action"].reason != "superseded"
                and now - c["at"] < CONSUME_RETRY_MIN}

    def _check_consumes(self):
        """Each remembered consume: one superseded forgotten; one that ended done checked once CONSUME_CHECK_MIN game
        minutes after the minute its done was first read (never from the send: the Lua reports done at the first fall
        of the fluid, which can come a minute after the send), its item marked no-effect when its stat fell by less
        than STAT_FALL_MIN and it is still held; a failed one is never checked; an ended one is forgotten once its
        retry window has passed (P24-F)."""
        self.no_effect = None
        now = self.world.world_minutes()
        st = self.world.stats or {}
        for iid, c in list(self.consumes.items()):
            a = c["action"]
            if self.actions.done(a) and a.reason == "superseded" and a.state != "done":
                del self.consumes[iid]
                continue
            if self.actions.done(a) and a.state != "done":
                c["checked"] = True                       # failed: no check, the retry window answers it
            if a.state == "done" and c["ended"] is None:
                c["ended"] = now
            if c["checked"]:
                if now - c["at"] >= CONSUME_RETRY_MIN:
                    del self.consumes[iid]
                continue
            if c["ended"] is None or now - c["ended"] < CONSUME_CHECK_MIN:
                continue
            c["checked"] = True
            cur, before = st.get(c["stat"]), c["before"]
            if cur is None or before is None or iid not in self.world.inventory:
                continue
            fell = before - cur
            if fell < STAT_FALL_MIN:
                self.world.mark_no_effect(iid)
                self.no_effect = {"itemId": iid, "use": c["use"], "stat": c["stat"], "fell": round(fell, 6)}

    @property
    def fills(self):
        """The water chain's fills (`Water.fills`)."""
        return self.water.fills

    def _sent_consume(self, action):
        """Remember the need's consume (P24-F): its use, its stat, the stat now and the world minute."""
        stat = NEED_STATS[self.need_use]
        self.consumes[action.args.get("itemId")] = {
            "action": action, "use": self.need_use, "stat": stat, "before": (self.world.stats or {}).get(stat),
            "at": self.world.world_minutes(), "ended": None, "checked": False}

    def _sleeping(self):
        """The night's Sleep while it is the current action (sent, accepted or in progress), else None (P23-AB)."""
        a = self.night.last
        return a if a is not None and a.type == "sleep" and self.actions.current is a else None

    # ---------------------------------------------------------------- the branches, in order
    # Each returns None (pass) or (policy or None, command or None): a None command holds the branch's running action.
    def _observe(self, policy):
        """`policy.observe()` once a tick (ruling P24-A (g), the close review's M1: a re-planned tick re-entered it)."""
        if not any(p is policy for p in self._observed):
            self._observed.append(policy)
            policy.trans = self.TRANS   # P24-AS: the policy's heading reads, before its observe, busy and choose
            policy.observe()

    def _answer(self, policy):
        self._observe(policy)
        if policy.busy():
            self.why = dict(policy.why, holding=policy.last.aid)
            return policy, None
        cmd = policy.choose()
        self.why = dict(policy.why)
        return None if cmd is None else (policy, cmd)

    def _care(self):
        """The care branch (`planner/care.py`, ruling P24-G 2): its own running action holds first; while the night's
        Sleep is current it passes as the need does (P23-AB); else `Care.choose`, `quiet` with no zombie within
        DISENGAGE_R (the wash's condition)."""
        c = self.care
        self._observe(c)
        if c.busy():
            self.why = dict(c.why, holding=c.last.aid)
            return c, None
        sleep = self._sleeping()
        if sleep is not None:
            self.why = {"holding_sleep": sleep.aid}
            return None
        c.quiet = not self._within(DISENGAGE_R)
        cmd = c.choose()
        self.why = dict(c.why)
        self._dressing_want(cmd is None and c.wants_dressing())
        return None if cmd is None else (c, cmd)

    def _dressing_want(self, want):
        """Ruling P24-AB: a bleeding part with nothing to dress it and no garment to rip marks the want `bandage`
        (`need_marks`, the view's `needs_wanted`; logged `want` on the care's why), which the goal layer's loot takes
        first (`goals.Kit.wants`); a tick of the care branch with no such want drops it."""
        if want:
            self.need_marks["bandage"] = self.clock()
            self.why["want"] = "bandage"
        else:
            self.need_marks.pop("bandage", None)

    def _care_stock(self):
        """Ruling P24-AB, the rag stock (`Care.stock`), tried behind the need, the load and the night and before the
        goal: only on an idle tick, no threat policy running and no action running (a drink, a fill, a goal's walk or
        loot is never superseded: Task 10's objection), no zombie within DISENGAGE_R; its line is the care branch's,
        the stock's why under the care's `stock`. Else None."""
        cur = self.actions.current
        if self.mode is not None or cur is not None:
            return None
        c = self.care
        c.quiet = not self._within(DISENGAGE_R)
        cmd, why = c.stock()
        if cmd is None:
            return None
        self.why = why
        return c, cmd

    def _need(self):
        if self.need_last is not None and self.actions.current is self.need_last:
            self.why = {"holding": self.need_last.aid}   # hold first: a frame past the drink must not supersede it
            return None, None
        sleep = self._sleeping()
        if sleep is not None:
            self.why = {"holding_sleep": sleep.aid}       # P23-AB: answered at the wake; the night holds the tick
            return None
        settling = self.water.settling()
        if settling:
            self.why = {"settling": settling[0]}          # 9 fix 2: a done fill waits for its item_changed
            return None, None
        st = self.world.stats or {}
        pick, fill = None, None
        inside = set()     # the held ids of a wanted use that its retry window leaves out (logged as `retry`)
        self.water.why = None
        for use, stat, t in (("water", "thirst", THIRST_T), ("food", "hunger", HUNGER_T)):
            if pick is not None or fill is not None or (st.get(stat) or 0.0) <= t:
                continue
            inside |= self._retrying() & set(self._by_use()[use])
            pick = self._held_use(use)
            if pick is None and use == "water":
                fill = self.water.plan(self._by_use())   # P24-G 3: no water held, a vessel filled at a known source
                self.water.wants(self.need_marks, self.clock())   # no vessel held, or no clean source (P24-L)
            if pick is None and fill is None:
                self.need_mark = self.need_mark or use
                self.need_marks[use] = self.clock()
            elif pick is not None:
                self.need_marks.pop(use, None)
                if use == "water":
                    Water.clear(self.need_marks)
                self.need_use = use
        self.why = {"item": pick, "mark": self.need_mark}
        if self.water.why is not None:
            self.why["fill"] = self.water.why
        if fill is not None:
            return None, fill
        if self.no_effect is not None:
            self.why["no_effect"] = self.no_effect
        if inside:
            self.why["retry"] = sorted(inside, key=str)
        if pick is None:
            return None
        return None, Consume(pick)

    def _load(self):
        """At load level DROP_AT or above, one `Drop` of `spare(world)` a decision, holding while it is current; with
        nothing spare, or under DROP_AT, it passes."""
        if self.load_last is not None and self.actions.current is self.load_last:
            self.why = {"holding": self.load_last.aid}
            return None, None
        sleep = self._sleeping()
        if sleep is not None:
            self.why = {"holding_sleep": sleep.aid}       # P23-AB, as the need
            return None
        level = (self.world.load or {}).get("level") or 0
        if level < DROP_AT:
            self.why = {"level": level}
            return None
        iid = spare(self.world)
        self.why = {"level": level, "drop": iid}
        return None if iid is None else (None, Drop(iid))

    def _night(self):
        """`night.Night`: its own running action holds first (a sleep is never superseded by a fatigue falling under
        the want); not wanting, it passes; a refused sleep's hold answers with no command. Each tick it wants counts in
        `night.wants_n`; `self.why` is the night's own `why`, so the `aid` its `sent` adds reaches the log."""
        n = self.night
        n.observe()
        if n.busy():
            self.why = dict(n.why, holding=n.last.aid)
            return n, None
        if not n.wants():
            n.idle()
            self.why = dict(n.why)
            return None
        n.wants_n += 1
        cmd = n.choose()
        self.why = n.why
        if cmd is None:
            return (n, None) if n.why.get("hold") else None
        return n, cmd

    def _goal(self):
        """The goal runner's command (owner: the runner, which hands the sent Action to its goal); with none, a
        running goal or a pending source (P23-AC) holds the branch, and otherwise the branch passes. The care's want
        (`bandage`, P24-AB) within NEED_MEMORY_S is handed to the goals' kit first (`Kit.wants`: the loot's order)."""
        now = self.clock()
        self.goals.kit.wants = tuple(u for u in KIT_WANTS if now - self.need_marks.get(u, -math.inf) <= NEED_MEMORY_S)
        cmd = self.goals.tick(self.world, self.actions, lambda: view(self.world, self))
        self.why = dict(self.goals.why)
        if cmd is not None:
            return self.goals, cmd
        return (self.goals, None) if self.goals.current is not None or self.goals.pending else None

    # ---------------------------------------------------------------- the tick
    def _note_failures(self):
        still = []
        self.consume_refused = None
        for a in self._watch:
            if not self.actions.done(a):
                still.append(a)
            elif a.state in FAILED and not (a.state == "failed" and a.reason == PREEMPTED):
                if a.type == "bandage" and a.state == "failed" and a.reason in RIDE_FREE and a.args.get("keepMoving") is True:
                    continue   # Task 12 fix 2: the engine's stop of a ride is no failure to cool (Care waits RIDE_RETRY_S)
                self.last_failed = _key(a.type, a.args) + (self.ticks,)
                if a.type == "consume" and a.state == "failed" and a.reason == REFUSED:
                    self._refused(a.args.get("itemId"))
                self._door_failed(a)
        self._watch = still

    def _door_failed(self, a):
        """Ruling P24-Z (Plan 24 Task 18; E7: eight loots failed `not adjacent` while the character stood 55.6 s at
        building 5's locked back door, and 6.0 s at a locked gate; Angus: "stuck trying to open doors"): a door's
        failure noted in the World (`World.note_door_fail`, the second marking it): an `interact` open or close that
        failed for a DOOR_FAILS reason, on its own square; a loot that failed `not adjacent` (its route stood against a
        door), on the door square nearest the player within DOOR_NEAR_R, if any. Whichever branch sent it: the night's
        shelter, the Shelter and LootBuilding goals, the flee's shelter and way out. The side it failed from (the
        character on a room square, `Night.inside`, "in", else "out": Task 18 fix 1, the review's major 4) is kept, so a
        door marked from outside stays a way out from inside."""
        if a.type != "interact" or a.state != "failed":
            return
        floor = me_floor(self.world)
        kind = a.args.get("kind")
        side = "in" if self.night.inside() else "out"   # Task 18 fix 1, major 4: the mark is one-sided
        if kind in ("open", "close") and a.reason in DOOR_FAILS:
            self.world.note_door_fail((a.args.get("x"), a.args.get("y"), floor), a.reason, side)
        elif kind == "loot" and a.reason == "not adjacent":
            door = self.world.door_near(me_xy(self.world), floor, DOOR_NEAR_R)
            if door is not None:
                self.world.note_door_fail(door, a.reason, side)

    def _refused(self, iid):
        """A consume refused `not valid`: a tainted one (`World.tainted_ids`: the Lua's `W.drinkable` refuses tainted
        water; the fill never takes a tainted source, P24-L, so this is a looted one or a fill from a source the map
        read clean) is marked `undrinkable`; an id `by_use()` reads `water` is empty (P23-D), one it reads `food` is
        refused (I-4), each marked so it reads `other`; a food and any other id (no longer held) are logged."""
        if iid in self.world.tainted_ids():
            self.world.mark(iid, "undrinkable")
            return
        uses = self.world.by_use()
        if iid in uses["water"]:
            self.world.mark_empty(iid)
            return
        if iid in uses["food"]:
            self.world.mark_refused(iid)
        self.consume_refused = iid

    def _cooling(self, cmd):
        f = self.last_failed
        return f is not None and _key(cmd.TYPE, cmd.args()) == f[:2] and self.ticks - f[2] < FAILED_COOLDOWN_TICKS

    def _inputs(self):
        me = self.world.me or {}
        st = self.world.stats or {}
        held = self._within(self._hold_r(), raw=True)
        cur = self.actions.current
        return {"x": me.get("x"), "y": me.get("y"), "health": self._health(), "hunger": st.get("hunger"),
                "thirst": st.get("thirst"), "fatigue": st.get("fatigue"), "hour": me.get("hour"),
                "armed": self._armed(), "load": (self.world.load or {}).get("level"),
                "threats": len(self._within(DANGER_R, raw=True)), "held": len(held),
                "nearest": min((zdist(self.world, z) for z in held), default=None),
                "running": cur.type if cur is not None else None, "mode": self.mode,
                "fight_s": self.fight.fight_s() if self.mode == "fight" else None}

    def tick(self, world, actions):
        """One planner tick (refactor A, Plan 24 Task 21): `_read` (the ends of the actions, the world's marks they
        make, the logged inputs), `assess` (the ordered branches' Decision, nothing sent or written), `_apply` (the
        send, its bookkeeping and the decision line). Returns the Action sent, else None."""
        return self._apply(self.assess(self._read(world, actions)))

    def _read(self, world, actions):
        """The tick's reads before any branch: the World and the Actions re-bound, the ends of the actions the tick
        itself owns read (the failures cooled, a refused consume or a door's failure marked, the consumes checked,
        the fills' ends; the flee's finishing stomp's, `_finish_end`, which marks the zombie dead and counts the World's
        kill: Task 32 fix 1, the review's minor 11, out of `assess`), the goal runner's observe, and the logged inputs (read before any branch runs: `mode` is
        the tick's start). Not every end: the branches' own observes (Care's, Night's, the Fight's and the Flee's)
        read theirs inside `assess`, see there."""
        self.world, self.actions = world, actions
        for p in self._policies():
            p.world, p.actions = world, actions
        self.water.world, self.water.actions = world, actions
        self.ticks += 1
        self._observed = []
        self._note_failures()
        for zid in [i for i in self.dead if i not in world.zombies]:
            del self.dead[zid]   # Task 12 fix 2: the World no longer lists it, so a later listing is a new zombie
        self._check_consumes()
        self.water.check()
        self._uses = None
        self.goals.observe(world, actions)
        self.engaging = False   # P24-X: set again by this tick's threat branch
        self._finish_kill = self._finish_end()   # P24-AQ: the flee's finishing stomp's end (fix 1, the review's minor 11)
        return self._inputs()

    def assess(self, inputs):
        """The tick's one decision (refactor A): the branches tried in BRANCHES order, the first that answers taken
        (a branch's command cooled, `_cooling`, passes it over; the threat branch never is), `inputs` completed with
        `need`, `consume_refused`, `cooled` and `branches` (each branch tried, its own why; a kill the running Fight
        read this tick on the threat's). Nothing is sent, logged or reported to the goal runner here: `_apply` does
        that from the Decision. The branches' policies keep their own memory as they choose (a policy is its state
        machine), so assess runs once a tick.

        Side effects refactor A left inside assess (a documented debt, review-t21 minor 2): `Care.observe` (from
        `_care` and `_care_yields`), `Night.observe` (from `_night`) and the Fight's and the Flee's observes (from
        `_threat`) read action ends there and mark the World (`unrippable`, `in_bag`, `mark_dry`, the Fight's
        `unreachable`); moving them to `_read` changes the tick a bandage's end is read, a golden re-record under a
        named change."""
        kill = None
        if self.fight is not None:
            self._observe(self.fight)
            kill = self.fight.kill   # P24-Q: read before any branch may replace the Fight (a lower bound: world.py)
        kill = self._finish_kill if kill is None else kill   # P24-AQ: the flee's finishing stomp's, read in `_read`
        self.need_mark = None
        branch, owner, cmd, cooled, tried = None, None, None, None, {}
        for name in STEPS:
            if name == "stock":   # P24-AB: the care's rag stock on an idle tick, behind the need, before the goal
                self.why = {}
                ans = self._care_stock()
                if ans is not None and not self._cooling(ans[1]):
                    tried["care"] = dict(tried.get("care") or {}, stock=self.why)
                    branch, (owner, cmd) = "care", ans
                    break
                continue
            self.why = {}
            ans = getattr(self, "_" + name)()
            tried[name] = self.why
            if ans is None:
                continue
            if name != "threat" and ans[1] is not None and self._cooling(ans[1]):   # a threat is never waited out
                cooled = {"type": ans[1].TYPE, "args": ans[1].args()}
                continue
            branch, (owner, cmd) = name, ans
            break
        inputs["need"] = self.need_mark
        inputs["consume_refused"] = self.consume_refused
        inputs["cooled"] = cooled
        if kill is not None:   # P24-Q: the kill read this tick, on the threat branch's why whatever answered
            tried["threat"] = dict(tried.get("threat") or {}, kill=kill)
        inputs["branches"] = tried
        return Decision(branch, owner, cmd, inputs)

    def _apply(self, d):
        """The Decision's effects: its command sent (through its owner, a policy or the goal runner, else directly:
        the need's consume or fill and the load's drop, each remembered) and watched for its end; the goal runner told
        whether another branch held without sending (`GoalRunner.held`); `last_branch`; the decision line appended."""
        action = None
        if d.cmd is not None:
            action = d.owner.send(d.cmd) if d.owner is not None else self.actions.send(d.cmd)
            if d.branch == "threat" and d.cmd.TYPE in ("attack", "shove", "stomp"):
                if d.owner is self.flee and ((d.inputs.get("branches") or {}).get("threat") or {}).get("finish") is not None:
                    self._finish_a = action   # P24-AQ: the flee's finish, its end read by `_finish_end`
                elif d.cmd.TYPE != "stomp":
                    self.struck[d.cmd.targetId] = self.clock()   # P24-AQ: a struck target
            if d.owner is None and d.branch == "need":
                self.need_last = action
                (self._sent_consume if d.cmd.TYPE == "consume" else self.water.sent)(action)
            elif d.owner is None and d.branch == "load":
                self.load_last = action
            self._watch.append(action)
        self.goals.held(d.branch not in (None, "goal") and d.cmd is None)
        self.last_branch = d.branch
        line = {"wall": self.clock(), "gameMin": self.world.game_min, "branch": d.branch, "inputs": d.inputs,
                "action": {"type": d.cmd.TYPE, "args": d.cmd.args()} if d.cmd is not None else None,
                "sent": action is not None, "goal": self.goals.line()}
        if self.no_effect is not None:
            line["marks"] = {"itemId": self.no_effect["itemId"], "reason": "no_effect"}
        with open(self.log_path, "a", encoding="utf-8", newline="\n") as f:
            f.write(json.dumps(line, sort_keys=True) + "\n")
        return action
