"""The scripted survivor (Plan 22 Task 10, spec § 3): a priority list over the World, ticked by its driver.

`Survive(world, actions, log_path, clock, source=None).tick(world, actions)` tries the branches in order (threat,
care, need, load, night, goal; Plan 23 Task 12 added `load` and `night`, Task 13 replaced `forage` and `explore` with
the goal, Plan 24 Task 10 `care`), takes the first that answers, and returns the `Action` it sent or None. A branch
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
      whatever the DANGER_R or hold count (`_many`, logged `listed` when it alone made `many`); the World keeps a
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
  3. The water chain (`_need`, `_fill_plan`, `_check_fills`): thirst over THIRST_T drinks a held `water` item, a
     clean one first (`World.tainted_ids` only with none clean); with none, a held `container` is filled (`fill`) at
     the nearest known clean source (`World.water_sources`; ruling P24-L, Task 10 fix 1: never a tainted one, which
     the Lua's consume refuses, `W.drinkable`, so a tainted fill lost the vessel for the session), its done marking
     the vessel `filled` or `tainted` (`World.mark`; `by_use` then reads it water, so the next tick drinks it). A
     source refused for its water, or whose walk failed (`not adjacent`, a STUCK_REASONS reason, or the fill timed
     out: SOURCE_FAILS), is left out for `world.SOURCE_RETRY_MIN` (`World.mark_dry`, the store the wash shares; Task
     10 fix 1, minor 4) and the vessel goes to the next source; a vessel whose fill failed any other way (never
     superseded) is left out FILL_RETRY_MIN game minutes from the minute its end was read. `world.by_use()` is read
     once a tick (`_by_use`, minor 14). The wants (`need_marks`, the view's `needs_wanted`): `water` whenever nothing is drunk or filled;
     `container` beside it only with no vessel held at all; `water_source` beside it with a vessel held and no clean
     source known (P24-L: the vessel is kept, and the goal layer may seek a building). A tainted drink refused `not
     valid` is marked `undrinkable` (`_refused`). The World applies PZA/1.5.1's `item_changed` (the engine's own
     re-read of a vessel's use and fluid). The no-effect mark (P24-F) is unchanged.
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

from agent.base.items import days_fresh
from agent.base.planner.care import CARE_HOLD_R, CARE_R, CARE_STILL_TICKS, DRY_REASONS, RIDE_FREE, RIDE_R, Care
from agent.base.planner.goals import GoalRunner, ScriptedSource
from agent.base.planner.night import Night
from agent.base.planner.policies import (AIM_R, CORNERED_R, DANGER_R, DISENGAGE_R, DROP_AT, ENGAGE_R, FIGHT_MAX_S,
                                         FIGHT_REACH, LISTED_R, POINT_BLANK_R, PREEMPTED, STUCK_REASONS,
                                         UNREACHABLE_S, Fight, Flee, adoptable, blocked, chasing, exit_plan,
                                         in_building, in_reach, item_id_ok, line_to, others_behind, seek_allowed,
                                         spare, target_id_ok, zdist)
from agent.base.planner.view import view
from agent.base.pza1 import Consume, Drop, Fill
from agent.base.world import me_floor, me_xy

THIRST_T = 0.12          # the first THIRST moodle fires above 0.12 [#0509]
HUNGER_T = 0.15          # the first HUNGRY moodle fires above 0.15 [#0508]
FLEE_HEALTH = 40.0        # under it a threat is fled, never fought
FLEE_HEALTH_PAIR = 60.0   # two or more threats are fled under this health
REFIGHT_MARGIN = 20.0     # a running flee turns to fight only at health >= FLEE_HEALTH + this, one threat
MAX_FIGHT = 2             # more threats than this are fled
HOLD_BREAK_R = 3.0        # tiles: a held threat this near breaks every hold whatever its line reads (P23-AJ 1)
CLOSING_TICKS = 3         # ticks in a row the nearest held threat reads nearer within DANGER_R that break every hold
                          # (P23-AJ 1, a judgment: E2's hold stood while a zombie closed from 5.78 to 3.05 tiles;
                          # three readings in a row rule out one knock-back's or one frame's jitter)
CORNER_FREE_R = DISENGAGE_R / 2   # tiles: a stuck leg's corner ends once the nearest held threat is beyond this
                          # (P23-AJ 2 fix round 1, a judgment: half the hold radius, room for the next leg to move;
                          # the other corners end beyond CORNERED_R)
MANY_LISTED_N = 4         # zombies listed within LISTED_R that make `many` whatever the DANGER_R count (P24-A (a):
                          # E5's group of five to seven was listed at 12 tiles while the branch counted within 6, #4268)
DRAG_DOWN_N = 3           # attackers the drag-down kills at (#4290, #4291: the fixture's sandbox Strength 2; two at
                          # Strength 1): at DRAG_DOWN_N - 1 the branch leaves any fight for the group's flee (P24-A (h))
FLIP_MIN_S = 5.0          # wall seconds a flee walk runs before a fight's walk may supersede it (P23-AM 1)
GROUP_R_N = 3             # zombies within GROUP_NEAR_R that make a group: steered from, not cornered (P23-AM 4, AP 2)
GROUP_NEAR_R = 3.0        # tiles: ... (P23-AP 2: a third zombie this near; P23-AM 4 read 1.5, CORNERED_R)
GROUP_HOLD_N = 4          # held threats (within the hold radius) that make a group too (P23-AP 2)
STUCK_RETRY_S = 2.0       # wall seconds after a stuck read before a stuck corner against a group tries a leg (P23-AP 2)
STUCK_RETRY_GROUP_S = 1.0  # ... with GROUP_R_N within CORNERED_R or GROUP_HOLD_N held, whatever the nearest reads
                          # (P24-A fix 1 (1), a ruling: F1's corner read stuck at 537 held on against four)
BRANCHES = ("threat", "care", "need", "load", "night", "goal")
FAILED_COOLDOWN_TICKS = 10   # planner ticks a failed command is not chosen again with the same type and args
FAILED = ("failed", "timeout", "rejected")
REFUSED = "not valid"    # the reason the Lua's consume fails an item it cannot eat or drink (an empty bottle)
NEED_STATS = {"water": "thirst", "food": "hunger"}   # the stat a consume of each use must lower (P24-F)
CONSUME_CHECK_MIN = 1.0  # game minutes after a consume's done is first read before its stat is checked (P24-F, fix 1)
STAT_FALL_MIN = 0.01     # the least fall of that stat since the send that counts as an effect (P24-F, a judgment:
                         # a drink or a meal moves its stat by tenths, F2's thirst rose 0.013 in 14 minutes)
CONSUME_RETRY_MIN = 5.0  # game minutes a consume that ended done leaves its item out of the pick (P24-F)
FILL_SETTLE_S = 2.0      # wall seconds a done fill waits for its vessel's item_changed before it is read as filled (9 fix 2)
FILL_RETRY_MIN = 2.0     # game minutes from its end a vessel whose fill failed is left out (as care.CARE_RETRY_MIN)
FILL_WANTS = ("container", "water_source")   # the water chain's wants beside `water` (P24-G 3, P24-L)
DOOR_FAILS = ("locked", "interrupted", "not adjacent") + STUCK_REASONS   # a door interact failed so is a door's
                         # failure, two of which mark it (ruling P24-Z); a loot's `not adjacent` counts on the door the
                         # player stands against (DOOR_NEAR_R)
DOOR_NEAR_R = 1.5        # tiles: a loot failed `not adjacent` counts on a door square this near the player (P24-Z)
SOURCE_FAILS = DRY_REASONS + ("not adjacent",) + STUCK_REASONS   # a fill failed so leaves its source out (Task 10
                         # fix 1, minor 5: a walk to it that failed, as one refused for its water), as a timeout does

__all__ = ["Survive", "BRANCHES", "DANGER_R", "DISENGAGE_R", "THIRST_T", "HUNGER_T", "FLEE_HEALTH",
           "FLEE_HEALTH_PAIR", "REFIGHT_MARGIN", "MAX_FIGHT", "FIGHT_MAX_S", "FIGHT_REACH", "FAILED_COOLDOWN_TICKS",
           "HOLD_BREAK_R", "CLOSING_TICKS", "CORNERED_R", "CORNER_FREE_R", "FLIP_MIN_S", "GROUP_R_N", "GROUP_NEAR_R",
           "GROUP_HOLD_N", "STUCK_RETRY_S", "STUCK_RETRY_GROUP_S", "MANY_LISTED_N", "DRAG_DOWN_N", "NEED_STATS",
           "CONSUME_CHECK_MIN", "STAT_FALL_MIN", "CONSUME_RETRY_MIN", "FILL_RETRY_MIN", "FILL_SETTLE_S", "FILL_WANTS",
           "SOURCE_FAILS", "DOOR_FAILS", "DOOR_NEAR_R"]


def _key(typ, args):
    return typ, json.dumps(args, sort_keys=True)


class Survive:
    ENGAGE = True   # ruling P24-X: one or two within ENGAGE_R are sought, a flee turns to fight at the fight's line
    SEEK = True     # ruling P24-X: every fight it engages (the door fight aside) is sought to KEEP_R; both switches
                    # are the replay tests' seams onto the rules before P24-X (`test_replay_decisions.pre_x`). Not
                    # behind them: Task 18's WIDE_TURNS and STEP_PROBE (the flee's wide tiers), which PRE_X proves move
                    # no golden (Task 18 fix 1, the review's minor 13)

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
        self.care_yield = None    # this tick: the nearest zombie's tiles when the threat yielded to the care (P24-P)
        self._nearest_seen = []   # (id, tiles) of the nearest listed zombie on the last threat ticks, newest last: the
                                  # care yield's closing read (Task 12 fix 1), CARE_STILL_TICKS + 1 of them
        self._observed = []       # the policies observed this tick (each once: P24-A (g))
        self.unreachable = {}     # zombie id -> wall until it is skipped (policies.Fight), kept across Fights
        self.unsought = {}        # zombie id -> wall until no engage re-reads its reach (`_engageable`, Task 18 fix 1)
        self.avoid = set()        # this tick: the ids within the hold no engage reaches (`_engageable`), else empty
        self._flood = None        # (map version, player square, squares): the engage's bounded flood (`_reach`)
        self.dead = {}            # zombie id -> wall until it is skipped, read dead (policies.Fight, Task 12 fix 1)
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
        self.fills = {}           # vessel id -> {action, read, at, base, done_wall}: the need's fills (P24-G 3)
        self.fill_why = None      # this tick: the water chain's fill or want, logged in the need's why
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

    def _hold_r(self):
        """The hold radius: DISENGAGE_R while a threat policy runs, ENGAGE_R on a tick the sought fight entered the
        branch (P24-X), else DANGER_R."""
        if self.mode is not None:
            return DISENGAGE_R
        return ENGAGE_R if self.engaging else DANGER_R

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
        tick resets it after the ends are read (`_note_failures`, `_check_fills` mark items)."""
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

    def _check_fills(self):
        """Each fill's end, once: done marks its vessel `filled` (or `tainted`, the act's result or its fluid saying
        so), so `by_use` reads it water and the next tick drinks it; a failure for its source (SOURCE_FAILS, or a
        timeout: the walk there) leaves the source out (`World.mark_dry`, `world.SOURCE_RETRY_MIN`) and
        frees the vessel for the next source; any other end but a supersede leaves the vessel out of the fill for
        FILL_RETRY_MIN game minutes from the minute its end was read (`_fill_plan`; Task 10 fix 1, minor 5: never from
        the send, a 30 s walk then coming back at once)."""
        now = self.world.world_minutes()
        for iid, f in list(self.fills.items()):
            a = f["action"]
            if f["read"]:
                if now - f["at"] >= FILL_RETRY_MIN:
                    del self.fills[iid]
                continue
            if not self.actions.done(a):
                continue
            if a.state == "done" and iid in self.world.inventory:
                # 9 fix 2: the engine's own read (item_changed) follows the fill by a moment; wait for it, or for
                # FILL_SETTLE_S of wall time, before the vessel is read as filled
                f.setdefault("done_wall", a.ended_wall if a.ended_wall is not None else self.clock())
                res = a.result if isinstance(a.result, dict) else {}
                it = self.world.inventory[iid]
                event = self.world.changes.get(iid, 0) > f["base"]
                if not event and self.clock() - f["done_wall"] < FILL_SETTLE_S:
                    continue
                tainted = res.get("tainted") is True or it.get("fluid") == "TaintedWater"
                if tainted:
                    self.world.tainted_sources.add((a.args.get("x"), a.args.get("y"), me_floor(self.world)))
                if not event:
                    self.world.mark(iid, "tainted" if tainted else "filled")
                del self.fills[iid]
                continue
            if a.state == "done" or (a.state == "failed" and a.reason == PREEMPTED):
                del self.fills[iid]
                continue
            if a.state == "timeout" or a.reason in SOURCE_FAILS:
                self.world.mark_dry((a.args.get("x"), a.args.get("y"), me_floor(self.world)))
                del self.fills[iid]
                continue
            f["read"], f["at"] = True, now

    def _fill_plan(self):
        """The water chain's second step (ruling P24-G 3, as P24-L narrowed it): a held `container` (`by_use`, the
        least id; one whose fill is running, settling or failed within FILL_RETRY_MIN left out) and the nearest known
        clean water source on the player's floor (`World.water_sources`, the dry and the tainted ones left out):
        `Fill(vessel, x, y)`, the Lua walking next to it. None without the `fill` skill, a free vessel or a clean
        source; `fill_why` says which: `want` "container" with no vessel held at all (the third step), `held_out`
        with every held vessel left out, `want` "water_source" with a vessel and no clean source known (P24-L)."""
        if not self.world.can("fill"):
            return None
        held = [i for i in self._by_use()["container"] if item_id_ok(i)]
        if not held:
            self.fill_why = {"want": "container"}
            return None
        vessels = [i for i in held if i not in self.fills]
        if not vessels:
            self.fill_why = {"held_out": held}
            return None
        clean = [s for s in self.world.water_sources() if s[2].get("tainted") is not True]
        if not clean:
            self.fill_why = {"vessel": min(vessels), "source": None, "want": "water_source"}
            return None
        d, sq, _ = clean[0]
        self.fill_why = {"vessel": min(vessels), "source": [sq[0], sq[1]], "dist": d}
        return Fill(min(vessels), sq[0], sq[1])

    def _sent_fill(self, action):
        """Remember the need's fill: its action, and the vessel's `item_changed` count at the send (the settle's)."""
        self.fills[action.args.get("itemId")] = {"action": action, "read": False, "at": None,
                                                 "base": self.world.changes.get(action.args.get("itemId"), 0)}

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

    def _held_inside(self, held):
        """Every held threat line-blocked (`line_to` False) and the character inside (M-6)."""
        return bool(held) and self.night.inside() and all(line_to(self.world, z) is False for z in held)

    def _skipped(self):
        """The ids no Fight targets now: marked unreachable, or read dead (`dead`, Task 12 fix 1)."""
        now = self.clock()
        return blocked(self.unreachable, now) | blocked(self.dead, now)

    def _reachable_held(self):
        """(id, zombie) of each held threat a Fight can target and neither marked unreachable nor read dead (a nil-id
        zombie is a danger, never a target)."""
        skip = self._skipped()
        r = self._hold_r()
        return [(zid, z) for zid, z in self.world.zombies.items() if target_id_ok(zid) and zid not in skip
                and z.get("x") is not None and z.get("y") is not None and zdist(self.world, z) <= r]

    def _many_read(self, held, n):
        """`(many, listed)`, read without side effects: the `many` rule, the hold radius's count over MAX_FIGHT while
        a fight runs (P23-AG ruling 2), the DANGER_R count `n` over it while none does; and while a flee episode whose
        reason was `many` runs (P23-AM 1: E3's flee under a group ended the tick its count fell back to DANGER_R's,
        four times in 8 s), the hold radius's count over MAX_FIGHT or the nearest held threat within DANGER_R.
        Whatever those read, MANY_LISTED_N or more listed within LISTED_R (ruling P24-A (a)) is `many`, `listed` that
        count when it alone made it (else None); since P24-X only when more than MAX_FIGHT of them press
        (`_pressing`: within DISENGAGE_R or chasing), so one or two fought while the rest stand off is no group."""
        if self.mode == "flee" and self.flee_many:
            near = len(held) > MAX_FIGHT or min(zdist(self.world, z) for z in held) <= DANGER_R
        else:
            near = (len(held) if self.mode == "fight" else n) > MAX_FIGHT
        if near:
            return True, None
        listed = self._within(LISTED_R)
        if len(listed) < MANY_LISTED_N or (self.ENGAGE and self._pressing(listed) <= MAX_FIGHT):
            return False, None
        return True, len(listed)

    def _pressing(self, zs):
        """Of `zs`, the zombies within DISENGAGE_R (10: ENGAGE_R's value at P24-X, kept when Task 18 fix 1's minor 8
        drew the engage in to 9) or chasing (`hasTarget`): P24-X's reading of the listing (the E7
        write-up, Task 18: each of E7's fights fled four or more listed within LISTED_R, two of them standing off at
        11.6 and 11.8 tiles, not chasing, while the pair the fight was on came; E5's horde at line 220 had three of
        five pressing, 4.9 tiles off and two chasing at 10.4 and 11.3)."""
        return sum(1 for z in zs if zdist(self.world, z) <= DISENGAGE_R or z.get("hasTarget") is True)

    def _many(self, held, n):
        """`_many_read`'s `many`, its `listed` kept for the decision's why (logged `listed`)."""
        many, listed = self._many_read(held, n)
        if listed is not None:
            self.listed = listed
        return many

    def _flee_reason(self, held, n):
        """Why the threat branch flees, by the hysteresis in the module docstring (`_hysteresis`); None when it fights.
        A fight that would walk toward its target with another zombie listed behind it (`_behind_walk`, ruling P24-A
        (b)) flees `held` instead (`many` having been read first)."""
        reason = self._hysteresis(held, n)
        if reason is None and self._behind_walk():
            return "held"
        return reason

    def _seeks(self):
        """A new Fight is sought (P24-X): both switches on."""
        return self.ENGAGE and self.SEEK

    def _fight_line(self, k):
        """The least health at which `k` held threats are fought: FLEE_HEALTH_PAIR for two, else FLEE_HEALTH."""
        return FLEE_HEALTH_PAIR if k == 2 else FLEE_HEALTH

    def _takes_on(self, k):
        """Ruling P24-X's one predicate (the engage and a flee's turn to fight read it): armed, one or two held
        (`MAX_FIGHT`), health at or above `_fight_line`, and a pair only with no wound (Plan 23 Task 10)."""
        return (self._armed() and 1 <= k <= MAX_FIGHT and self._health() >= self._fight_line(k)
                and not (k >= 2 and self._wounds() > 0))

    def _sought(self):
        """Ruling P24-X (E7: zero kills, the goal running on 160 of its 1420 replayed lines with one or two zombies
        listed within 10 tiles): the zombies listed within ENGAGE_R when, with no threat policy running, the fight is
        sought: one or two of them (`_takes_on`), no `many` reason (`_many_read`: the DANGER_R count, MANY_LISTED_N
        listed within LISTED_R), one of them a target (neither marked unreachable nor read dead), and no night's Sleep
        current (a sleeper is woken only within DANGER_R, as before); else None. The branch then holds all of them
        (`engaging`: the hold radius ENGAGE_R this tick), so the second of a pair within ENGAGE_R is the fight's, not a
        group behind it."""
        if self.mode is not None or self._sleeping() is not None:
            return None
        near = self._within(ENGAGE_R)
        if not near or not self._takes_on(len(near)) or self._many_read(near, len(self._within(DANGER_R)))[0]:
            return None
        if self._chokepoint() and not self._stance_ok(near, self.night.inside()):
            return None   # Task 18 fix 1, ruling 2: held ground with no stance (a PZA/1.4 build, trapped) never walks
        skip = self._skipped()
        held = [(zid, z) for zid, z in self.world.zombies.items() if target_id_ok(zid) and zid not in skip
                and any(z is h for h in near)]
        self.avoid = {zid for zid, z in held if not self._engageable(zid, z)}
        if all(zid in self.avoid for zid, _ in held):
            return None
        return near

    def _side(self, z):
        """The building whose room square position-record `z` ((x, y) keys) stands on, else None (outside, a door
        square or unmapped)."""
        s = self.world.map.get((int(math.floor(z["x"])), int(math.floor(z["y"])), me_floor(self.world))) or {}
        return s.get("building") if s.get("room") is not None else None

    def _chokepoint(self):
        """The character holds ground (Task 18 fix 1, the review's ruling 2): it stands on a room square or a door
        square, where the stance stands and lets a zombie come (no seek: `policies.seek_allowed`)."""
        mx, my = me_xy(self.world)
        sq = self.world.map.get((int(math.floor(mx)), int(math.floor(my)), me_floor(self.world))) or {}
        return sq.get("room") is not None or sq.get("door") is not None

    def _reach(self):
        """The squares the player's bounded flood reaches (`World.flood` within ENGAGE_R + 2 tiles: the open steps, a
        closed or locked door shut, a hoppable fence open), read once per map version and player square."""
        mx, my = me_xy(self.world)
        sq = (int(math.floor(mx)), int(math.floor(my)), me_floor(self.world))
        key = (self.world.map_version, sq)
        if self._flood is None or self._flood[0] != key:
            r = ENGAGE_R + 2.0
            self._flood = (key, self.world.flood(sq, limit=int(4 * (r + 1) ** 2), r=r))
        return self._flood[1]

    def _engageable(self, zid, z):
        """Task 18 fix 1 (the review's major 2 and ruling 2; E4's gate zombie 19001 sought every UNREACHABLE_S behind a
        locked gate, 152 `stalled` lines): zombie `z` (id `zid`) may be engaged within ENGAGE_R: on the character's
        side of a building's walls (`_side`: neither inside a building the character is outside of, a locked or
        unentered one, nor outside one the character shelters in, at night or not), and chasing, or with its line
        clear (`line_to` True), or a square beside it (or its own) in the player's bounded flood (`_reach`). One that
        is not is marked in `unsought` for UNREACHABLE_S (no flood re-read meanwhile; a chase or a clear line still
        engages it at once), so the goal it would supersede runs on."""
        mx, my = me_xy(self.world)
        if self._side(z) != self._side({"x": mx, "y": my}):
            return False
        if chasing(z) or line_to(self.world, z) is True:
            return True
        now = self.clock()
        if self.unsought.get(zid, 0.0) > now:
            return False
        floor = me_floor(self.world)
        own = (int(math.floor(z["x"])), int(math.floor(z["y"])), floor)
        reach = self._reach()
        if own in reach or any(sq in reach for sq in self.world.reachable_adjacent((z["x"], z["y"]), floor)):
            return True
        self.unsought[zid] = now + UNREACHABLE_S
        return False

    def _stance_ok(self, held, inside):
        """Ruling P24-G 1, the standing fight: the build announces `aim` (`World.can`), a weapon in hand, one held
        threat with health at or above FLEE_HEALTH or two with it at or above FLEE_HEALTH_PAIR, and the character
        not trapped on a room square (`_trapped`: the corner rules stay for a stuck or trapped character)."""
        if not (self.world.can("aim") and self._armed() and 1 <= len(held) <= MAX_FIGHT):
            return False
        if self._health() < self._fight_line(len(held)):
            return False
        return not self._trapped(held, inside)

    def _behind_walk(self):
        """Ruling P24-A (b): the ids listed behind the target the Fight would walk toward (`policies.others_behind`),
        kept in `behind`, else []: the running fight's target (its pin, else the nearest reachable), or with none
        running the nearest zombie not marked (a new Fight's first pin); the Fight walks when the target is beyond
        FIGHT_REACH, when its approach is due beyond POINT_BLANK_R (P24-A (e)), or when the line to it reads blocked
        (the reposition)."""
        f = self.fight if self.mode == "fight" else None
        if f is not None:
            t = f._target(pin=False)
            seek = f.seeking(t)
            stand = f.standing() and not f.advance   # P24-N: the advance closes on the target, a walk toward it
        else:
            nz = self.world.nearest_zombie(exclude=self._skipped())
            t = None if nz is None else (nz[0], nz[1], zdist(self.world, nz[1]))
            seek = self._seeks() and t is not None and seek_allowed(self.world, t, self._chokepoint())   # P24-X
            stand = self._stance_ok(self._within(self._hold_r()), self.night.inside())
        if t is None:
            return []
        zid, z, d = t
        stand = stand and d <= AIM_R and not seek   # Task 10 fix 2: beyond the aim's range the Fight walks toward
                                                    # it; P24-X: the seek closes on it, a walk toward it
        walk = not (stand and d > FIGHT_REACH) and (   # P24-G 1: a standing fight never walks beyond reach
            d > FIGHT_REACH or (f is not None and f.approach and d > POINT_BLANK_R) or line_to(self.world, z) is False)
        ids = others_behind(self.world, zid, z) if walk else []
        if seek:   # P24-X: the one or two the fight was sought against are the fight, not a group behind it, and
            held = self._within(self._hold_r())   # one standing off beyond them (not chasing) is no group either
            ids = [i for i in ids if not any(self.world.zombies.get(i) is h for h in held)
                   and self.world.zombies.get(i, {}).get("hasTarget") is True]
        if ids:
            self.behind = ids
        return ids

    def _hysteresis(self, held, n):
        """Plan 21b's hysteresis (the module docstring): the flee reason, else None. `n` is the DANGER_R count (the
        `pair` rule's); `many` is `_many`."""
        health = self._health()
        if not self._armed():
            return "unarmed"
        if self._many(held, n):
            return "many"
        if health < FLEE_HEALTH:
            return "health"
        if n >= 2 and (health < FLEE_HEALTH_PAIR or self._wounds() > 0):
            return "pair"
        if not self._reachable_held():
            return "unreachable"
        near = min(zdist(self.world, z) for z in held)
        if self.mode == "flee":
            if self.stall_flee and near > FIGHT_REACH:
                return "stalled"
            if not self.ENGAGE:   # before P24-X: one held, at the refight margin
                return "held" if len(held) > 1 or health < FLEE_HEALTH + REFIGHT_MARGIN else None
            if not self._takes_on(len(held)):   # P24-X: the flee turns to fight one or two at the fight's line
                return "held"
            if self.flee_health and health < FLEE_HEALTH + REFIGHT_MARGIN:   # the health flee stays, its margin kept
                return "held"
            return None
        if self.mode == "fight" and self.fight.stalled and (self.fight.target_dist() or 0.0) > FIGHT_REACH:
            return "stalled"   # the pinned target's distance: the one the stall clock follows (M3)
        return None

    # ---------------------------------------------------------------- the branches, in order
    # Each returns None (pass) or (policy or None, command or None): a None command holds the branch's running action.
    def _observe(self, policy):
        """`policy.observe()` once a tick (ruling P24-A (g), the close review's M1: a re-planned tick re-entered it)."""
        if not any(p is policy for p in self._observed):
            self._observed.append(policy)
            policy.observe()

    def _answer(self, policy):
        self._observe(policy)
        if policy.busy():
            self.why = dict(policy.why, holding=policy.last.aid)
            return policy, None
        cmd = policy.choose()
        self.why = dict(policy.why)
        return None if cmd is None else (policy, cmd)

    def _breach(self, held):
        """Why a hold breaks this tick (ruling P23-AJ 1), else None: `near` with a held threat within HOLD_BREAK_R
        whatever its line reads, `closing` once the nearest held threat has read nearer than at the tick before on
        CLOSING_TICKS consecutive ticks within DANGER_R (the first such reading counts one: 5.5, 5.0, 4.5 breaks at
        the third), a threat coming through an opening the map does not show. The count is kept every threat tick."""
        d = min(zdist(self.world, z) for z in held)
        n, last = self.closing
        n = (n + 1 if last is not None and d < last else 1) if d <= DANGER_R else 0
        self.closing = (n, d)
        if d <= HOLD_BREAK_R:
            return "near"
        return "closing" if n >= CLOSING_TICKS else None

    def _exit_known(self, held):
        """A way out of the building the character stands in (`policies.exit_plan`, P23-AJ 3): the flee's running
        one, or one not refused this episode."""
        f = self.flee
        if f is not None and f.exit is not None:
            return True
        return exit_plan(self.world, held, f.refused if f is not None else ()) is not None

    def _cornered(self, held, inside):
        """The zombie id a cornered Fight runs on (ruling P23-AJ 2, its fix rounds, and the coordinator's amendment 6
        to P23-AM), else None. Armed, with the nearest held threat within CORNERED_R, it corners (`corner_kind`):
        - `stuck`: the flee's last steer leg ended stuck (`Flee.stuck`: moved under STUCK_MOVE), or `inside`: the
          character stands on a room square (fix round 1: at melee range the branch fights before any walk out);
          on the nearest zombie `in_reach` (fix round 2, G4: within POINT_BLANK_R, or within CORNERED_R with its line
          not read blocked; its unreachable mark aside, I3);
        - `walk` (amendment 6, E3: lines 260-275 passed with a zombie within 1.5 tiles while the enter walk ran): on
          any other threat tick whatever runs (a shelter or exit walk, a steer leg, a goal walk the threat superseded),
          except while a fight runs (it keeps its own pin, Task 10), on the nearest zombie within CORNERED_R whose
          line is not read blocked and that is not marked unreachable (run 1's 103 swings at a zombie behind a locked
          door: these corners respect the marks, their Fight's `mark_free_r` 0).
        Rule 4 (P23-AM 4, as amendment 6 widens the corner, and survival 4's ruling P23-AP 2: E4's `walk` corner on
        one or two zombies held 35 ticks while the group formed outside 1.5 tiles, the held count rising from three to
        six): with a group (`_group`: GROUP_HOLD_N held, or GROUP_R_N within GROUP_NEAR_R) and the last leg not stuck,
        no corner, and a running corner not taken `stuck` ends (fix round 1, G1: E3's group came one at a time onto a
        `walk` corner): `group_steer`, the flee steers (runs, P24-O) while a leg can move, until one ends stuck. A
        `stuck` corner keeps swinging against the group, re-tested every tick: with the nearest beyond POINT_BLANK_R
        and its stuck read STUCK_RETRY_S old, it ends for one steer leg (`group_steer` "retry"; that leg read stuck in
        turn is a new `stuck` corner). Fix round 1: on a room square with no way out (`_trapped`, R3) no group is read:
        no leg can move there, so the corner stands at once; and the corner follows its Fight's re-pin to the nearest
        zombie within POINT_BLANK_R (R4, `policies.Fight`), while any other retarget of its Fight (a mark's recursion
        to a zombie farther off) ends the corner and the tick is planned again (fix round 2, N1). It stays
        cornered on that id until the zombie is dead, gone, or marked unreachable and out of reach (a `walk` corner:
        marked at all), or the nearest held threat is beyond `corner_free`: CORNER_FREE_R for a stuck leg's corner,
        CORNERED_R for the others (a way out is never known at melee range, every exit's line starting within
        EXIT_CLEAR_R). The cornered Fight swings at a target within POINT_BLANK_R whatever its line reads
        (`Fight.point_blank`). A new corner makes a new Fight, superseding whatever ran; the next flee's Flee is a new
        one too, whose first leg is not stuck."""
        nearest = min(zdist(self.world, z) for z in held)
        if not self._armed():
            self.cornered = None
            return None
        skip = self._skipped()
        dead = blocked(self.dead, self.clock())   # Task 12 fix 1: never cornered on, marks aside or not
        group = self._group(held)
        if group and self._trapped(held, inside):
            group = None   # fix round 1, R3: on a room square with no way out no leg can move: the corner stands
        if self.cornered is not None:
            if group and self.corner_kind != "stuck":   # fix round 1, G1: a group gathering on a corner is steered from
                self.cornered, self._corner_fight, self.group_steer = None, None, group
                return None
            if group and self.stuck_wall is not None and (   # P23-AP 2: a moved leg's chance; P24-A fix 1 (1)
                    (nearest > POINT_BLANK_R and self.clock() - self.stuck_wall >= STUCK_RETRY_S)
                    or (self._melee_group(held) and self.clock() - self.stuck_wall >= STUCK_RETRY_GROUP_S)):
                self.cornered, self._corner_fight, self.group_steer = None, None, "retry"
                return None
            if (self.corner_kind == "stuck" and self.stuck_wall is not None and self._stuck_health(held)
                    and not self._trapped(held, inside)
                    and self.clock() - self.stuck_wall >= STUCK_RETRY_GROUP_S):   # P24-A fix 2, G3 (ruling P24-E)
                self.cornered, self._corner_fight, self.group_steer = None, None, "retry"
                self.corner_yield = "health"
                return None
            if self.corner_kind == "walk" and self._walk_yields():   # P24-A (c): a leg can move, the flee reads first
                self.cornered, self._corner_fight, self.corner_yield = None, None, self._walk_yields()
                return None
            z = self.world.zombies.get(self.cornered)
            if (z is not None and z.get("x") is not None and z.get("y") is not None and nearest <= self.corner_free
                    and self.cornered not in dead and (self.cornered not in skip
                         or (self.corner_kind != "walk" and in_reach(self.world, z, CORNERED_R)))):
                return self.cornered
            self.cornered, self._corner_fight = None, None
            return None
        stuck = self.mode == "flee" and self.flee is not None and self.flee.stuck()
        if stuck or inside:   # I3, G4: marks aside, within 1.0 or a line not blocked
            reach = [(zid, z) for zid, z in self.world.zombies.items() if target_id_ok(zid) and zid not in dead
                     and in_reach(self.world, z, CORNERED_R)]
        elif self.mode == "fight":
            return None   # a running fight keeps its own pin (Task 10): the corner pre-empts walks, not swings
        else:   # amendment 6, on any walk: a line not read blocked and no mark (run 1's 103 swings at a locked door)
            reach = [(zid, z) for zid, z in self.world.zombies.items() if target_id_ok(zid) and zid not in skip
                     and z.get("x") is not None and z.get("y") is not None and zdist(self.world, z) <= CORNERED_R
                     and line_to(self.world, z) is not False]
        if nearest > CORNERED_R or not reach:
            return None
        if group and not stuck:
            self.group_steer = group   # P23-AM 4: against a group the branch steers (runs) until a leg ends stuck
            return None
        if not (stuck or inside) and self._walk_yields():   # P24-A (c): no `walk` corner under the health or many flee
            self.corner_yield = self._walk_yields()
            return None
        self.corner_kind = "stuck" if stuck else ("inside" if inside else "walk")
        self.corner_free = CORNER_FREE_R if stuck else CORNERED_R
        self.stuck_wall = self.clock() if stuck else None
        if stuck:
            self.stuck_heading = self.flee.leg_heading()   # P24-A fix 2, G2: the next Flee's first leg skips it
        self.cornered = min(reach, key=lambda p: (zdist(self.world, p[1]), repr(p[0])))[0]
        return self.cornered

    def _stuck_health(self, held):
        """Ruling P24-E (fix 2, G3): a `stuck` corner is a blocked heading, not a pinned player: under FLEE_HEALTH, or
        under FLEE_HEALTH_PAIR with two or more held, it tries a leg every STUCK_RETRY_GROUP_S as under a group."""
        h = self._health()
        return h < FLEE_HEALTH or (len(held) >= 2 and h < FLEE_HEALTH_PAIR)

    def _melee_group(self, held):
        """P24-A fix 1 (1): GROUP_R_N or more held within CORNERED_R, or GROUP_HOLD_N held: a `stuck` corner then tries
        a leg every STUCK_RETRY_GROUP_S, whatever the nearest reads."""
        return (len(held) >= GROUP_HOLD_N
                or sum(1 for z in held if zdist(self.world, z) <= CORNERED_R) >= GROUP_R_N)

    def _walk_yields(self):
        """Ruling P24-A (c) (the close review's I1: F1's `walk` corner on 15921, taken off a `many` shelter walk at
        0.65 tiles, held from health 99.4 to 0.9, the corner tested before the flee reasons and never reading health):
        why a `walk` corner yields, else None: `health` under FLEE_HEALTH, `many` while a flee episode whose reason was
        `many` runs (the corner is then not taken; a running corner ended that episode). `unarmed` never corners
        (`_cornered`); the `stuck` and `inside` corners keep the override, no leg moving there."""
        if self._health() < FLEE_HEALTH:
            return "health"
        return "many" if self.mode == "flee" and self.flee_many else None

    def _drag(self, held, inside):
        """Ruling P24-A (h) (#4290, #4291: DRAG_DOWN_N zombies attacking from within 0.9 tiles turn the next hit into
        the drag-down, health to 0 in one call): the frame's `me.attackers` (PZA/1.4; absent on an older frame, never
        read) at DRAG_DOWN_N - 1 or more, any corner (a `stuck` one too) left for the leg at once; except on a room
        square with no way out and nothing to adopt (`_trapped`): the guard has no leg or exit to take there, so the
        corner keeps swinging (P24-A fix 1 (4), confirmed)."""
        n = (self.world.me or {}).get("attackers")
        if not isinstance(n, int) or isinstance(n, bool) or n < DRAG_DOWN_N - 1:
            return False
        return not self._trapped(held, inside)

    def _group(self, held):
        """Why the held threats are a group the branch steers from rather than corners (P23-AM 4, ruling P23-AP 2),
        else None: `hold` with GROUP_HOLD_N or more held (the hold radius's list), `near` with GROUP_R_N or more within
        GROUP_NEAR_R (a third zombie that near; iteration 3 read three within CORNERED_R, which this takes in)."""
        if len(held) >= GROUP_HOLD_N:
            return "hold"
        return "near" if sum(1 for z in held if zdist(self.world, z) <= GROUP_NEAR_R) >= GROUP_R_N else None

    def _threat_plan(self, held, breach):
        """The threat branch's one decision (ruling P23-AJ), `(kind, reason)`, the machines only executing it:
        - The drag-down guard (ruling P24-A (h), `_drag`): `flee` with the group steer (`group` "drag"), ahead of
          every other row; the Flee steers at a run, or inside walks the exit (P24-A (f), P24-O).
        - `door`: sheltered (a chosen shelter's plan done, the character inside) with a reachable held threat in its
          doorway or inside it: the door fight (I3). It goes first, before the corner and before the inside hold
          (a decision-order change from 21e3716b, which held first; ruled at fix round 1, the review's M1: a threat
          that opened the door or stands inside is the nearest danger, and its line may read blocked from another
          room).
        - `cornered`: `_cornered` names a zombie: a Fight on it whatever the held count or the flee reason (rule 2).
        - `hold`: the character inside, every held threat line-blocked (M-6, `held_inside`), no shelter or exit step
          running, and no breach (rule 1).
        - A broken hold (a breach while the inside hold, or the sheltered Flee's, would hold): `flee` when a way out is
          known (the Flee walks it: rule 3), else `fight` with one or two held and one reachable, else `flee`;
          `reason` the flee reason, else `broken`.
        - Sheltered with nobody in the doorway: `flee` (the sheltered Flee holds, re-closes or drops), reason
          `sheltered` when no other holds.
        - Otherwise Plan 21b's hysteresis (`_flee_reason`): `fight` when it reads None, else `flee`.
        - Fix round 1: a broken hold at a chosen shelter fights only in its doorway or inside (`door`, the review's
          I4); a `flee` on a room square with no way out and no adoption left is the Fight when armed
          (`_trapped_fight`, G3).
        Not a pure function: it sets `sheltered`, `door`, `broken`, `cornered`, `corner_yield`, `behind` and `listed`
        (`_breach` before it set `closing`),
        and a corner inside a chosen shelter drops the sheltered Flee, so the next flee walks out rather than
        re-closing."""
        inside = self.night.inside()
        self.sheltered = self.flee is not None and self.flee.sheltered and inside
        self.broken, self.group_steer, self.corner_yield, self.behind, self.listed = None, None, None, None, None
        if self._drag(held, inside):   # P24-A (h): first, whatever the fight or the corner
            self.cornered, self._corner_fight, self.group_steer, self.door = None, None, "drag", None
            return "flee", self._flee_reason(held, len(self._within(DANGER_R))) or "many"
        self.door = self._door_targets() if self.sheltered else None
        if self.door:
            return "door", None
        if self._cornered(held, inside) is not None:
            return "cornered", None
        if self.group_steer:
            return "flee", self._flee_reason(held, len(self._within(DANGER_R))) or "many"
        steps = self.mode == "flee" and self.flee is not None and (self.flee.running_shelter()
                                                                   or self.flee.running_exit())
        held_inside = not steps and self._held_inside(held)
        if held_inside and breach is None:
            return "hold", "held_inside"
        reason = self._flee_reason(held, len(self._within(DANGER_R)))
        if breach is not None and (held_inside or (self.sheltered and self.flee.shelter_holds(held))):
            self.broken = breach
            if self._exit_known(held):
                return "flee", reason or "broken"
            if self._armed() and len(held) <= MAX_FIGHT and self._reachable_held():
                return ("door", None) if self.sheltered else ("fight", None)   # I4: a shelter's fight stays inside
            return self._trapped_fight(held, inside) or ("flee", reason or "broken")
        if self.sheltered:
            return "flee", reason or "sheltered"
        if reason is None:
            reason = self._kept_flee()
            if reason is None:
                return "fight", None
        return self._trapped_fight(held, inside) or ("flee", reason)

    def _kept_flee(self):
        """Why a running flee the hysteresis would end is kept (ruling P23-AM 1), else None: `steps` while a `many`
        episode's shelter plan or way out runs (its end, sheltered inside or walked out, is the flee's end), and
        `flip` while the Flee's own walk or steer leg sent under FLIP_MIN_S ago runs and the Fight would walk (the
        nearest reachable held threat beyond FIGHT_REACH): a fight's walk never supersedes it sooner. The other way
        the flee wins: a flee is never held back for a fight's walk (it is the retreat)."""
        f = self.flee
        if self.mode != "flee" or f is None:
            return None
        if self.flee_many and (f.running_shelter() or f.running_exit()):
            return "steps"
        a = f.last
        if a is None or a.type not in ("walkTo", "steer") or not f.busy() or self.clock() - a.sent_wall >= FLIP_MIN_S:
            return None
        reach = self._reachable_held()
        return "flip" if reach and min(zdist(self.world, z) for _, z in reach) > FIGHT_REACH else None

    def _trapped(self, held, inside):
        """On a room square with no way out (`_exit_known`) and no adoption left (`policies.adoptable`: no exterior
        door on this floor, or this episode's adoption already dropped)."""
        if not inside or self._exit_known(held):
            return False
        f = self.flee
        return not (adoptable(self.world) and (f is None or not f.adopted or f.plan is not None))

    def _trapped_fight(self, held, inside):
        """Fix round 1, the review's G3: a flee trapped on a room square (`_trapped`) never steers: armed with a
        reachable held threat, `("fight", None)`; else None (the Flee's trapped hold: M4, an unarmed character inside
        with no way out stands)."""
        if not (self._armed() and self._reachable_held() and self._trapped(held, inside)):
            return None
        return "fight", None

    def _end_flee_episode(self):
        """A flee episode's own flags cleared: its stall origin, its one load drop, its `many` (P23-AM 1) and its
        `health` (P24-X)."""
        self.stall_flee, self.flee_dropped, self.flee_many, self.flee_health = False, False, False, False

    def _nearest_listed(self):
        """(id, tiles) of the nearest listed zombie with a position (ties by the listing's order), one read dead left
        out, else None."""
        best, dead = None, blocked(self.dead, self.clock())
        for zid, z in self.world.zombies.items():
            if zid in dead or z.get("x") is None or z.get("y") is None:
                continue
            d = zdist(self.world, z)
            if best is None or d < best[1]:
                best = (zid, d)
        return best

    def _closing(self):
        """The nearest listed zombie may be closing (Task 12 fix 1): fewer than CARE_STILL_TICKS earlier reads of the
        same zombie as the nearest in a row, or its distance now under its read CARE_STILL_TICKS ticks ago."""
        h = self._nearest_seen
        if len(h) <= CARE_STILL_TICKS or any(e[0] != h[-1][0] for e in h):
            return True
        return h[-1][1] < h[0][1]

    def _flee_leg(self):
        """The running flee's own walk or steer leg (`Flee.busy`), else None."""
        f = self.flee if self.mode == "flee" else None
        if f is None or not f.busy() or f.last.type not in ("steer", "walkTo"):
            return None
        return f.last

    def _ride_leg(self):
        """The running flee leg a bandage may ride (P24-U, PZA/1.5.3's obligation: the ride has no pathing): a steer,
        or a walk whose straight line to its target reads clear on the map; else None."""
        leg = self._flee_leg()
        if leg is None or leg.type == "steer":
            return leg
        a = leg.args
        return leg if self.world.line_clear(me_xy(self.world), (a.get("x"), a.get("y"))) else None

    def _care_yields(self, held):
        """Ruling P24-P (Plan 24 Task 12; E6's health fell from 100 to 17.6 under a held zombie before its one
        bandage), with Task 12 fix 1's hysteresis (the review's major 2: with one start and supersede line at CARE_R a
        chaser hovering at it alternated the bandage and the steer every tick, four bandages started and none
        finished): the nearest listed zombie's tiles when the threat branch yields this tick to the care branch's
        bleeding step, else None. No `many` reason may be live (a group: the running `many` episode or the `many`
        count; every other reason, the health flee's included, is about one or two held, whose distance this reads),
        and `Care.tends_wound` must answer (its part reads bleeding while the bandage runs; once no part bleeds the
        yield ends, and the threat's send supersedes the bandage). A bandage starts only with the nearest beyond
        CARE_R, not closing (`_closing`), and no flee episode (`mode` flee, fix 2: the gap between two legs is the same flight) from a chaser (a held zombie whose
        `hasTarget` is set: a run holds the distance while the zombie chases, so the closing read cannot see it, and
        a standing bandage would stop the run the health flee exists to make). A running one (the care's own
        bandage, current) holds the yield while the nearest stays beyond CARE_HOLD_R. The ride (ruling P24-U) comes
        first: under a flee leg it may ride (`_ride_leg`) with the nearest beyond RIDE_R or no chaser, a part above the
        legs bleeding (`Care.rides_wound`), the care's `ride_now` set; a ride running yields nothing (the threat
        answers, the Flee's leg held by the ride: `policies.running`)."""
        if not self.world.can("bandage") or not self._nearest_seen or self.care.riding() is not None:
            return None
        near = self._nearest_seen[-1][1]
        chased = any(z.get("hasTarget") is True for z in held)
        if (near > RIDE_R or not chased) and not (self.flee_many and chased) and self._ride_leg() is not None:
            self._observe(self.care)
            if self.care.rides_wound():
                self.care.ride_now = True
                return near
        if self.flee_many:
            return None
        running = self.care.busy() and self.care.last.type == "bandage"
        if near <= (CARE_HOLD_R if running else CARE_R):
            return None
        if not running and (self._closing() or (self.mode == "flee" and chased)):
            return None
        if self._many_read(held, len(self._within(DANGER_R)))[0]:
            return None
        self._observe(self.care)
        return near if self.care.tends_wound() else None

    def _threat(self):
        """The tick's bookkeeping, once (ruling P24-A (g)): the held list, the Flee's observe and the breach's closing
        count; then the yield to the care (`_care_yields`, P24-P), else the decision (`_decide`), which a corner's
        retarget may re-plan without them."""
        self.care_yield, self.care.ride_now, self.engaging, self.avoid = None, False, False, set()
        held = self._within(self._hold_r())
        sought = self._sought() if self.ENGAGE else None
        if sought:   # P24-X: one or two within ENGAGE_R, the fight sought
            held, self.engaging = sought, True
        elif held and self._released(held):   # Task 18 fix 1, major 2: nothing left the fight may reach
            held = []
        if not held:
            self.mode, self.fight, self.flee = None, None, None
            self._end_flee_episode()
            self.sheltered, self.cornered, self.closing = False, None, (0, None)
            self.stuck_heading, self._nearest_seen = None, []
            if self.avoid:   # Task 18 fix 1: the zombies within ENGAGE_R no engage reaches, logged as the goal runs
                self.why = {"unsought": sorted(self.avoid, key=repr)}
            return None
        self._nearest_seen = (self._nearest_seen + [self._nearest_listed()])[-(CARE_STILL_TICKS + 1):]
        if self.flee is not None:   # a shelter or exit step's end read before the hold (the close may have ended),
            self.flee.threats = held   # over this tick's held records (the stall's and the stuck leg's DANGER_R and
            self._observe(self.flee)   # STUCK_NEAR_R reads: before P24-A (g) the first read saw the last tick's)
        breach = self._breach(held)
        self.care_yield = self._care_yields(held)
        if self.care_yield is not None:
            self.why = {"care": True, "nearest": self.care_yield, "held": len(held)}
            if self.care.ride_now:
                self.why["ride"] = True
            return None
        return self._decide(held, breach)

    def _decide(self, held, breach, replanned=False):
        """`_threat_plan`'s decision executed by the Fight or the Flee, logged in `why`."""
        kind, reason = self._threat_plan(held, breach)
        if kind == "hold":
            self.why = {"flee": "held_inside", "held": len(held)}
            return None, None
        door = self.door if kind == "door" else None
        want = "flee" if kind == "flee" else "fight"
        if kind == "cornered":
            if self.fight is None or self.fight is not self._corner_fight:
                self.fight = self._corner_fight = Fight(self.world, self.actions, self.clock,
                                                        unreachable=self.unreachable, target=self.cornered,
                                                        dead=self.dead)
                self.fight.point_blank = True
                self.fight.mark_free_r = 0.0 if self.corner_kind == "walk" else CORNERED_R
                self.flee = None
                self._end_flee_episode()
            self.mode = "fight"
        elif want != self.mode:
            if want == "fight":
                self.fight = Fight(self.world, self.actions, self.clock, unreachable=self.unreachable, dead=self.dead)
                self.fight.seek = self._seeks() and door is None   # P24-X: every fight but the door's is sought
                if door is None:
                    self.flee = None   # a door fight keeps the sheltered Flee for the re-close
                self._end_flee_episode()
            else:
                if self.flee is None or not self.sheltered:   # only a sheltered Flee outlives a door fight
                    self.flee = Flee(self.world, self.actions, self.clock, shunned=self.night.shunned)
                    self.flee.skip_heading, self.stuck_heading = self.stuck_heading, None   # fix 2, G2
                self.fight = None
                self.stall_flee = reason == "stalled"
            self.mode = want
        if want == "fight" and door is None:
            self.flee = None   # a door fight that left the room: the stale shelter plan goes (the next flee re-picks)
        policy = self.fight if want == "fight" else self.flee
        if want == "flee":
            self.flee_many = self.flee_many or reason == "many"
            self.flee_health = self.flee_health or reason == "health"
            policy.threats = held
            policy.hold_ok = breach is None
            policy.steer_now = self.group_steer is not None
            if self.group_steer:
                policy.give_way()   # amendment 6: the group pre-empts a running walk, as the corner does
            if self.group_steer == "drag":
                policy.drop_stuck_leg()   # P24-A fix 2, I1: never a stalled leg held its FLEE_S under the guard
            ans = self._flee_drop() or self._answer(policy)
        else:
            policy.only = None if door is None else {zid for zid, _ in door}
            policy.stance = self._stance_ok(held, self.night.inside())   # P24-G 1 (no corner or door Fight stands)
            policy.hold_ground = self._chokepoint()   # Task 18 fix 1, ruling 2: no seek from a room or door square
            policy.avoid = self.avoid                 # ... nor at a zombie no engage reaches (major 2)
            policy.ride = self.care.riding()   # P24-U: the stance legs held off while a bandage rides
            policy.threats = held
            ans = self._answer(policy)
        self.why.update({"fight": True} if reason is None else {"flee": reason})
        if self.sheltered:
            self.why["sheltered"] = True
        if kind == "cornered" and self.fight.target not in (None, self.cornered):
            t = self.world.zombies.get(self.fight.target)
            if t is not None and in_reach(self.world, t, CORNERED_R):
                self.cornered = self.fight.target   # R4, P24-A fix 2 I2a: the corner follows its Fight's re-pin in reach
            elif not replanned:   # fix round 2, N1: any other retarget (a mark's recursion) ends the corner, re-planned
                self.cornered, self._corner_fight = None, None
                return self._decide(held, breach, replanned=True)
        if kind == "cornered" and self.fight.why.get("out_of_reach") and not replanned:
            self.cornered, self._corner_fight = None, None   # P24-A fix 2, I2a: no corner walks to a drifted pin
            return self._decide(held, breach, replanned=True)
        if kind == "cornered":
            self.why["cornered"], self.why["corner_kind"] = self.cornered, self.corner_kind   # P24-A (g), M2
        if self.group_steer is not None:
            self.why["group"] = self.group_steer
        if self.avoid and want == "fight":
            self.why["unsought"] = sorted(self.avoid, key=repr)
        for key, v in (("yield", self.corner_yield), ("behind", self.behind), ("listed", self.listed)):
            if v is not None:
                self.why[key] = v
        if self.broken is not None:
            self.why["breach"] = self.broken
        ride = self.care.riding()
        if ride is not None:
            self.why["ride"] = ride.aid   # P24-U: a bandage rides the leg this answer holds or re-aims
        return ans if ans is not None else (policy, None)

    def _released(self, held):
        """Task 18 fix 1 (the review's major 2: E4's fight on gate zombie 19001 held the goal off behind a locked
        gate): a running fight (neither a corner's nor a door fight) with no held threat within DANGER_R and none of
        the held ones it may engage (`_engageable`; one marked unreachable or read dead counted out) ends, and the goal
        runs: the release of P24-X's engage, as it was entered. Sets `avoid`, the held ids beyond DANGER_R no engage
        reaches (the Fight never pins one anew: `Fight.avoid`). Only with `ENGAGE` on."""
        f = self.fight
        if not self.ENGAGE or self.mode != "fight" or f is None or f.point_blank or f.only is not None:
            return False
        ids = {id(z): zid for zid, z in self.world.zombies.items()}
        pairs = [(ids.get(id(z)), z) for z in held]
        self.avoid = {zid for zid, z in pairs if target_id_ok(zid) and zdist(self.world, z) > DANGER_R
                      and not self._engageable(zid, z)}
        if any(zdist(self.world, z) <= DANGER_R for z in held):
            return False
        skip = self._skipped() | self.avoid
        return all(not target_id_ok(zid) or zid in skip for zid, _ in pairs)

    def _door_targets(self):
        """(id, zombie) of each reachable held threat standing in the sheltered building's doorway or inside it
        (`policies.in_building`), when the character is armed; else [] (I3: the door fight never walks out)."""
        if not self._armed():
            return []
        b = self.flee.plan["building"]
        return [(zid, z) for zid, z in self._reachable_held() if in_building(self.world, z, b)]

    def _flee_drop(self):
        """At load level DROP_AT or above, a flee episode's first answer is one `Drop` of `LootHouse.spare()`, sent
        as the Flee's own action so the steer waits on it (the drop skill is quick); None otherwise."""
        if self.flee_dropped or self.flee.busy() or ((self.world.load or {}).get("level") or 0) < DROP_AT:
            return None
        iid = spare(self.world)
        if iid is None:
            return None
        self.flee_dropped = True
        self.why = {"flee_drop": iid}
        return self.flee, Drop(iid)

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
        return None if cmd is None else (c, cmd)

    def _need(self):
        if self.need_last is not None and self.actions.current is self.need_last:
            self.why = {"holding": self.need_last.aid}   # hold first: a frame past the drink must not supersede it
            return None, None
        sleep = self._sleeping()
        if sleep is not None:
            self.why = {"holding_sleep": sleep.aid}       # P23-AB: answered at the wake; the night holds the tick
            return None
        settling = sorted((i for i, f in self.fills.items() if "done_wall" in f), key=str)
        if settling:
            self.why = {"settling": settling[0]}          # 9 fix 2: a done fill waits for its item_changed
            return None, None
        st = self.world.stats or {}
        pick, fill = None, None
        inside = set()     # the held ids of a wanted use that its retry window leaves out (logged as `retry`)
        self.fill_why = None
        for use, stat, t in (("water", "thirst", THIRST_T), ("food", "hunger", HUNGER_T)):
            if pick is not None or fill is not None or (st.get(stat) or 0.0) <= t:
                continue
            inside |= self._retrying() & set(self._by_use()[use])
            pick = self._held_use(use)
            if pick is None and use == "water":
                fill = self._fill_plan()   # P24-G 3: no water held, a vessel filled at a known source
            if use == "water" and pick is None:
                want = (self.fill_why or {}).get("want")
                for u in FILL_WANTS:          # the goal layer's wants: no vessel held, or no clean source (P24-L)
                    if u == want:
                        self.need_marks[u] = self.clock()
                    else:
                        self.need_marks.pop(u, None)
            if pick is None and fill is None:
                self.need_mark = self.need_mark or use
                self.need_marks[use] = self.clock()
            elif pick is not None:
                self.need_marks.pop(use, None)
                if use == "water":
                    for u in FILL_WANTS:
                        self.need_marks.pop(u, None)
                self.need_use = use
        self.why = {"item": pick, "mark": self.need_mark}
        if self.fill_why is not None:
            self.why["fill"] = self.fill_why
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
        running goal or a pending source (P23-AC) holds the branch, and otherwise the branch passes."""
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
        self.world, self.actions = world, actions
        for p in self._policies():
            p.world, p.actions = world, actions
        self.ticks += 1
        self._observed = []
        self._note_failures()
        for zid in [i for i in self.dead if i not in world.zombies]:
            del self.dead[zid]   # Task 12 fix 2: the World no longer lists it, so a later listing is a new zombie
        self._check_consumes()
        self._check_fills()
        self._uses = None
        self.goals.observe(world, actions)
        self.engaging = False   # P24-X: set again by this tick's threat branch
        inputs = self._inputs()
        kill = None
        if self.fight is not None:
            self._observe(self.fight)
            kill = self.fight.kill   # P24-Q: read before any branch may replace the Fight (a lower bound: world.py)
        self.need_mark = None
        branch, owner, cmd, cooled, tried = None, None, None, None, {}
        for name in BRANCHES:
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
        action = None
        if cmd is not None:
            action = owner.send(cmd) if owner is not None else self.actions.send(cmd)
            if owner is None and branch == "need":
                self.need_last = action
                (self._sent_consume if cmd.TYPE == "consume" else self._sent_fill)(action)
            elif owner is None and branch == "load":
                self.load_last = action
            self._watch.append(action)
        self.goals.held(branch not in (None, "goal") and cmd is None)
        self.last_branch = branch
        line = {"wall": self.clock(), "gameMin": self.world.game_min, "branch": branch, "inputs": inputs,
                "action": {"type": cmd.TYPE, "args": cmd.args()} if cmd is not None else None,
                "sent": action is not None, "goal": self.goals.line()}
        if self.no_effect is not None:
            line["marks"] = {"itemId": self.no_effect["itemId"], "reason": "no_effect"}
        with open(self.log_path, "a", encoding="utf-8", newline="\n") as f:
            f.write(json.dumps(line, sort_keys=True) + "\n")
        return action
