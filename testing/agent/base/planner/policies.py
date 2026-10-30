"""The multi-step policies (Plan 22 Task 10, spec § 3): fight, flee, explore and loot-house, each a Python machine over
the Lua's one-step skills, sending typed commands through `Actions` and reading the `World`.

One action at a time. A policy's `step()` returns the `Action` it sent, or None: it sends nothing while its own last
action is `actions.current` (sent, accepted or in progress), and decides again once that action reads a terminal
state (`done`, `failed`, `rejected`, `timeout`) or another sender's action replaced it. `step()` is `observe()` (the
policy's bookkeeping from the World and its last action's end), then `choose()` (the next command, or None) and
`send(cmd)`; `survive.Survive` calls the three apart so its cooldown can pass a choice over before it is sent. A
walk or steer leg stays running under a bandage sent with `keepMoving` after it (PZA/1.5.3, ruling P24-R: the Lua
keeps the leg and rides the bandage beside it; ruling P24-U, Task 12 fix 1): `running` reads it so, and `busy` and the
Flee's leg reads go through it. Every
command is validated by `Actions.send` against the schema's `ACTION_ARGS` (a TypeError is a policy bug). A policy
never reads `cmd.txt` or the state lines: its driver pumps the transport's lines into the World and Actions first.
`why` is the policy's own inputs to its last choice, logged by Survive.

Distances are tiles from the frame's `me` to a zombie's `x, y` (the World's last sighting), so a zombie kept within
`ZOMBIE_TTL_S` but missing from the latest frame is measured from where the player is now.

- `Fight`: one pinned target (Plan 23 Task 10): the zombie id given as `target=`, else the nearest by
  `world.nearest_zombie()` at the first `choose`, kept until it is dead or gone from the World, unreachable, or beyond
  `DISENGAGE_R` (10 tiles), and never swapped for a nearer one otherwise; dropped, the next `choose` pins again. With
  `only` set (a set of ids: Survive's door fight, P23-AG fix round 1 I3) it neither pins nor keeps a zombie outside it.
  Beyond `FIGHT_REACH` a `WalkTo` of its square's centre (`centre`, as every walk to a square) at a run (the Lua's
  `walkTo` paths there, around walls), within it an `Attack` of its id once the line holds. The line check (ruling
  P23-K) answers run 1 swinging 103 attacks at a zombie behind a locked door: within reach the Fight reads
  `world.line_clear` from the player to the target over the map's blocked edges (a closed door or an intact window
  blocks, an open doorway does not); false, it walks once at a run to the centre of the square of
  `world.reachable_adjacent(target)` nearest the player, within REPOSITION_R (2.5 tiles) of the player by its centre
  and no nearer than REPOSITION_MIN (1.2: ruling P23-AJ 5, a centre inside the Lua walk's DONE_R 1.0 ends the walk
  `done` unmoved), from whose centre the line is clear (`repositioned`), and a second blocked read, or no such square,
  marks the target
  unreachable and the next is tried. `reachable_adjacent` lists the squares open to the target, not to the player, and
  the radius is crow-fly, so it bounds the detour without excluding it: a square within 2.5 tiles may still lie across
  the wall the line crosses (`test_policies.walled_south`'s case at 2.5 tiles walks round a solid block). Ruling P23-R
  keeps the radius alone this plan: the base has no path search, and a walk that cannot reach the square fails or ends
  short, and the next choose's blocked read (the second, as `repositioned` holds) marks the target; cost if wrong, a
  short detour walked before the target is dropped. The line is read only when the map holds both end squares on the
  player's floor; over an unscanned end it is None and the swing goes ahead, left to the no-progress stall below. `why`
  logs `target`, `pinned`, `dist`, `approach`, `line` and `reposition` (the square chosen, else None), and `marked` when
  this choose marked a target. Two `attack` results in a row whose `attackStarted` is False force one approach walk
  before the next attack (a result that is not a dict, as a failed attack's null, neither counts nor resets). The stall
  clock is Plan 21's `out_of_reach_since`: started when the Fight is made and restarted by every `observe()` that reads
  no target or the target within `FIGHT_REACH`; `stalled` reads true once the target has been beyond `FIGHT_REACH` for
  more than `FIGHT_MAX_S` unbroken wall seconds (a knock-back for one tick restarts nothing old; the clock counts the
  unbroken time out of reach only). Within reach that clock is not the stall: run 1 (the whole-pass review's I2) swung
  103 attacks, every one `done` with `attackStarted` true, at zombie 32404 behind a locked door, its health 1.167 on all
  1530 frames listing it, and the out-of-reach clock restarted on every tick. The no-progress stall: `STALL_SWINGS`
  consecutive `done` attacks on one target with `attackStarted` true, read off `Actions`' ended records, whose target's
  health (the frame's `zombies[*].health` for its id) did not fall below the health at the streak's start, make that
  target unreachable for `UNREACHABLE_S` wall seconds: `nearest_zombie` skips it, so the Fight takes another target or,
  with none, sends nothing (Survive then flees, reason `unreachable`). A swing not started neither counts nor resets the
  streak; a fall, a new target or a target no frame lists restarts it. `unreachable` (id -> wall until) is passed in so
  a later Fight of the same planner keeps it. An attack ending `failed` for a walk reason (`STUCK_REASONS`) marks its
  target the same way. A target read dead (Task 12 fix 1, the controller's ruling on concern 6: F1's line 254 swung
  at 15911 on the tick its kill was read, the zombie still listed) is unpinned and skipped for UNREACHABLE_S in `dead`
  (id -> wall until, passed in as `unreachable` is), logged `dead`, never `unreachable`: a time-bounded skip, so a
  recycled id (unverified) is not skipped for the session as the permanent `World.killed` would.
  The standing fight (rulings P24-G 1 and P24-N, survive.py's docstring; P24-N supersedes P24-M's backpedal band
  after E6, `e_day_6-20261029-102942`: 8 of its 11 stance legs stood, the fights went to the approach and swing):
  with `stance` set (Survive's `_stance_ok`), neither `point_blank` nor `only`, and the target within AIM_R
  (`stance_at`), every leg is `Aim(vx, vy, AIM_LEG_S, targetId)` facing the target (`_stance_leg`), the fight's first
  action included: within FIGHT_REACH with the stance not held (`in_stance`: the last send was this Fight's running
  aim, or its attack from the stance running or ended within AIM_HOLD_S, Task 9's hand-over) an `enter` leg (0, 0),
  the swing following from it; inside KEEP_R the backpedal (`away_vector` of `threats` turned by STEER_TURNS to the
  first heading `clear_heading` passes, never into a wall or over a hoppable fence, else (0, 0)); beyond it standing
  (0, 0), the target faced while it comes. A running leg gives way (`busy`) once the target is within reach,
  re-pinned, or the stand ends, and (Task 12 fix 1) once the leg its distance calls for (`stance_leg_kind`) is
  another: a standing leg inside KEEP_R or in the advance, a backpedal past KEEP_R + KEEP_MARGIN, an `enter` leg
  whose target was knocked out of reach; the advance's `toward` leg holds until reach, or gives way and re-pins for
  `_advance_switch` (Task 18 fix 2: another zombie inside KEEP_R or SEEK_SWITCH_R nearer than the target). The stand
  clock (`_stand`) restarts on a new target or a fall of its health, ending any advance; at STAND_MAX_S the Fight
  closes in the stance (`advance`: `toward` legs, the unit vector to the target, or with its line blocked over
  STEER_PROBE the approach walk at a walk round the wall, never a run: Task 12 fix 1, the review's minor 3), the
  out-of-reach stall clock (which a stand keeps at zero)
  starting then. A stance leg that ends failed, timed out or rejected (never superseded, nor refused `no target`:
  Task 10 fix 2, the zombie is gone) sets `standoff` at once (Task 10 fix 1, minor 11: a build that cannot hold the
  stance never re-sends it), and the approach and swing above run for the rest of the Fight; `standoff_why` names
  the leg's state and reason. The seek (ruling P24-X, Plan 24 Task 18; survive.py's docstring): a Fight with `seek`
  set (Survive's engaged fights) closes on a target not yet `sought`: beyond KEEP_R its stance leg is `seek`, the
  `toward` leg's vector (the walk at a walk round a blocked STEER_PROBE line), giving way the tick the target comes
  within KEEP_R, which marks it `sought` (iteration 7's stance from then on, never a second seek of it); beyond AIM_R
  the seek walks at a walk; a seek walk that fails for a STUCK_REASONS reason marks its target unreachable for
  SEEK_SKIP_S (`_observe_seek`). Task 18 fix 1: a sought target inside KEEP_R that reads no target of its own
  (`chasing` false) is advanced on at once (`advance`, the review's minor 10: the back and stand legs dithered until
  STAND_MAX_S in front of an idle zombie); no seek on a room or door square (`hold_ground`) nor at a chasing
  target across a known fence (`seek_allowed`); the seek re-pins to a zombie SEEK_SWITCH_R nearer than its target
  (`_seek_switch`), its leg giving way for it; the stance's own walk (a seek's or the advance's round a wall, a
  seek's beyond AIM_R) gives way as a leg does (`_walk_gives_way`, the review's blocker); a zombie in `avoid` (no
  engage reaches it) is never pinned anew beyond DANGER_R.
  Survival 11 (survival iteration 10; Plan 24 Task 27; PZA/1.7's `shove` and `stomp`, `zombies[].onFloor`, `body.armPain`; #4370-#4374),
  each sent only to a build that announces it: P24-AL, finish the fallen (`_finish`, ahead of every other step once
  the target is resolved): the nearest downed zombie (`onFloor`, or a shove's `knockdown` within KNOCK_READ_S) within
  FIGHT_REACH on a line not read blocked takes the shove of a standing zombie at point blank first, else the `stomp`,
  else the weapon's floor strike (an `attack` of it) when the stomp was refused (`swing_refused`, SWING_SKIP_S) or a
  standing zombie stands within STAND_MIN_R (the engine's call would take that one); a running stance leg gives way
  to it (`busy`). At the swing (`_shove`): P24-AG, with `body.armPain` at STRAIN_SOFT or above a standing target at
  point blank is shoved, never swung at; P24-AH, in a standing fight a second standing zombie inside KEEP_R makes the
  nearer of the two (within SHOVE_R) shoved before the next swing, once a swing (`_shoved`); neither with another
  standing zombie within STAND_MIN_R. A shove's or stomp's `targetDead` is a kill (SWING_TYPES), a started stomp
  counts in the no-progress streak.
  Survival 12 (survival iteration 11; Plan 24 Task 32; survive.py's docstring the record): P24-AN, the pull: with
  `pull` set (Survive's sought fights), a lone chaser (`pull_from`: it alone chases within ENGAGE_R, the rest of the
  listing beyond DANGER_R) is pinned first (`_pull_pin`) and, beyond PULL_R (FIGHT_REACH + KEEP_R), its stance legs
  walk away from the rest's centroid facing it (`pull`, `pulling`), the seek's switch to a nearer zombie off; within
  PULL_R it is `sought` (the stance stands for it, never a seek toward it past the group), and once pulled it is kept
  to DISENGAGE_R (`_pull_waits`: past ENGAGE_R it is stood for, never sought back). P24-AP, the wounded fight: at
  `body.armPain` STRAIN_HARD (`arms_hurt`) the Fight never swings, the floor strike included: the shove at point
  blank (P24-AG's), the stomp of a fallen one, else the backpedal facing the target (`_wounded_leg`, held by `busy`
  until point blank; with no stance announced nothing). P24-AS (amendment 1): every heading read (`clear_heading`:
  the steer's turns, the backpedal, the pull, the seek's and the advance's lines) and the way out's end (`_beyond`)
  refuse a `solidTrans` square (the policy's `trans`, Survive's TRANS switch); the fight's line of sight does not.
  The doorway stand's Fight is `planner/doorway.py`'s `Doorway`; the Flee keeps its stand plan (`stand_ok`, the
  pick's `stand`, the enter's end read `stand`, `standing_door`, `closing_stand`).
- `Flee` (one per flee episode): a `Steer` of `FLEE_S` seconds away from the threats (the `threats` list its caller
  passes, else every zombie the World holds), at a run (ruling P24-O, Task 12: the planner never sprints; E6 sprinted
  13 steers and Angus saw the character trip, and a fence climb begun at a sprint rolls a trip, #4296); re-aimed on
  every end of its steer. Every leg runs along the sum of the unit vectors from each threat to the player, each weighted
  by 1/distance (ruling P23-AG 3, amended at fix round 1 to every leg: away from the centroid and from the nearest, so a
  group spread round the player is not fled into); a zero sum steers along +x. The steer reads the map (fix round 1, I4:
  the chain's E1 died sprinting 15 s into a fence the World already held as `blockW`, the group biting): the away vector
  turns by STEER_TURNS (30, 60, 90 degrees either way, nearest first) to the first heading whose `world.line_clear` over
  AHEAD_R (9 tiles, about a leg's run: fix round 3, F3) and over STEER_PROBE is true (survival 2, the fix-3 review's
  (a): the two rasterised lines cross different squares, so a 9-tile clear alone may graze a wall the 3-tile line
  meets), else over STEER_PROBE (3) tiles, an unknown square read
  open (`unknown_open`, its unknown diagonal corner open too: F5) (fix round 2, concern 1: unscanned ground is no wall,
  so the flee does not bend along the scanned area's edge), and along which no held threat beyond NEAR_R lies within
  AHEAD_R (9 tiles, a 3 s leg at E1's 3 tiles/s) inside AHEAD_CONE (20 degrees) or in the CORRIDOR_R tube (fix round 2,
  T2: E1's first leg, set by a melee zombie at 0.18 tiles, ran at the far pair); with none such, the first clear on the
  map, else the away vector kept. A leg that ended having moved under STUCK_MOVE (0.5) tiles is stuck, and the next
  leg's turn skips the away vector's own 0 and every heading within STUCK_SKIP_DEG (15 degrees) of the stuck leg's (F4).
  The way out (ruling P23-AJ 3, as amended: E2 died steering into its own room's walls in a building whose doors were
  all broken): on a room square, with no shelter plan running or held, each choose (the episode's start and every
  re-aim) takes `exit_plan`, of the building's `night.exits` (its openings, `world.openings`, and its closed,
  unbarricaded exterior doors at their approach squares) the one whose outside square is no nearer any held threat
  than the player is to it and lies farthest from their centroid, and runs it: a closed door opened first (`Interact`
  open), then a `WalkTo` at FLEE_GAIT of the centre of the square one on beyond the outside square (`_beyond`, when
  the map holds it open: a walk ends `done` within the Lua's DONE_R, so the outside square's own centre may end it on
  the room square); a superseded step is sent again, any other failed end, or a walk that ended done with the frame
  still inside, refuses that exit for the episode (`refused`) and the next choose takes the next. Fix round 1: no
  window's edge is an opening (`world.openings`, the review's G1); an exit with no open square beyond is skipped
  (I1); the walk goes first even at a closed door, the open only after it fails there (I2); a walk that leaves the
  player within STUCK_MOVE for WALK_STALL_S is dropped and read as failed (G2); the
  exit is the nearest acceptable one, its straight line passing no held threat within EXIT_CLEAR_R; with none, the
  building is adopted once an episode (`_adopt`, iteration 1's fix round 2 brought back as the fallback: the
  sheltered hold, the re-close guard, the door fight), and with that dropped or no exterior door the Flee holds with
  no command (`trapped`): on a room square it never steers (Survive's corner fights at melee range); the frame
  reading
  outside ends the exit, the building is `left` (never the episode's shelter) and the steer follows.
  The shelter (ruling P23-AG 1): at each re-aim until a plan is chosen (fix round 2, T1: a melee zombie's corridor
  refusal is retried once it has moved), the episode picks, never from a room square: of the buildings not shunned
  (`night.shunned_now` over `shunned`, Night's store) nor left this episode with
  no known zombie on one of their room or door squares, the exterior door the map reads neither locked nor barricaded
  whose `night.approach_square` lies within SHELTER_FLEE_R (25 tiles) of the player, is no nearer any held threat than
  the player is to it, and has no known zombie ahead within CORRIDOR_R (2 tiles) of the straight line to it
  (`in_corridor`), the nearest such square first; the plan (`night.shelter_plan(..., door=)`) is kept to that door, and
  its steps (`night.shelter_step`: approach, open, enter, close) go out with their walks at FLEE_GAIT, a run (never a
  sprint: P24-O). A step's end is read by `night.shelter_ended`: `advance`, `resend`
  and `passed` keep the plan; any other end drops it for the steer (the episode never picks again), shunning the
  building only for a reason in `night.SHUN_REASONS`. Once the close ended with the player inside (`sheltered`), choose
  holds with no command while every threat reads line-blocked (`line_to` False), or while the door reads closed and no
  threat's line reads clear (an unknown line holds: concern 2), and while `hold_ok` (Survive clears it on a breach,
  ruling P23-AJ 1); else it re-sends the close when the door reads open (again after each close that ended done, never
  after one that did not), unless a known zombie stands within DOOR_CLEAR_R (1.5 tiles) of the door (concern 4) or the
  player's square is no nearer the door square than every known zombie's (F2: the Lua's close walks the player to the
  door); else drops the plan, and the way out or the steer follows. A plan done with the player outside is dropped for
  the steer. `night` imports this module at its top, so the Flee imports `night` at the call (`_night()`).
  Survival 3 (ruling P23-AM, the chain's E3): a shelter step's walk (approach, enter, or an open's or close's walk
  while the player stands more than one square from the door, the Lua interact's own approach) that leaves the
  player within STUCK_MOVE for WALK_STALL_S (1.0) wall seconds while a held threat is within DANGER_R is dropped
  (`ended` `stalled`, `_dropped` as the exit's walk) with its plan for the episode (never shunned in the night's
  store), and the steer follows at once; with no held threat within DANGER_R the step waits the Lua's stuck time.
  P23-AM 3's group sprint (a `many` flee sprinting while the endurance allowed) is gone with every other sprint
  (ruling P24-O). With `steer_now` (Survive's group at melee range, its last leg not stuck), the choose steers first.
  Survival 4 (ruling P23-AP 3, E4's line 440: a leg aimed west before two zombies there were listed ran 8.92 tiles
  into them): on every threat tick the running steer leg's heading is re-read against the held threats (`_cut_leg`:
  `_ahead`, AHEAD_R, AHEAD_CONE and the CORRIDOR_R tube, beyond NEAR_R); a threat ahead that was not ahead when the
  leg was aimed cuts it, and the next choose re-aims by the turn rules (its why's `cut` the ids), the new leg
  superseding it. Fix round 1: the cut reads the World's current records by id (G1), and a cornered Fight
  (`point_blank`) re-pins at each choose to the nearest zombie within POINT_BLANK_R (R4).
  Survival 5 (ruling P24-A; survive.py's docstring is the record): the re-pin only while the pin stands beyond
  POINT_BLANK_R (d); no approach walk at point blank (e); no attack while the frame's `me.hitReaction` names one
  (`hit_reaction`, i); `others_behind` (b), Survive's look past a fight's walk target; the episode's first leg
  repulsed from `World.met_window`'s centre too (a); on a room square `steer_now` never steers: the exit (at a run
  since P24-O), else the adoption or the trapped hold, and `give_way` keeps a running exit (f).
- `Explore`: it scans per 10-tile place, spec § 6's "once at a new building or on request" read as the place
  grid: a `Scan(SCAN_R)` once per place (the player's square rounded half up to a `SCAN_R`-tile grid, kept in
  `scanned` from its send and dropped again when the scan ends other than `done`, so a pre-empted, timed-out or
  rejected scan is retried, and dropped when the World names the last scan's aid in `scans_dropped`, a job the Lua
  dropped after its `done` line (ruling S-32), so that place is scanned again), then a `WalkTo` at a walk to
  `world.unexplored_edge()`; no edge, no
  command. A walk that ends `failed` with a reason in `STUCK_REASONS` has its target marked in the World
  (`world.mark_stuck`), and
  `unexplored_edge` leaves it out for `STUCK_TTL_MIN` (60) game minutes, so it is never re-sent inside them (the
  whole-pass review's I4: run 1 re-sent a walk that failed `stuck` to the same edge 20 times). Survival 4 (ruling
  P23-AP 1, E4's twelve walks from one square north of a locked gate): a walk failed `stuck` with the player moved
  under STUCK_MOVE is a stuck pair from its start square (`world.mark_stuck_pair`), a walk that moved or arrived ends
  the run (`clear_stuck_run`); at the STUCK_AREA_N-th pair in a row the player's place is dropped from `scanned` (the
  scan the goal source falls back to), and `unexplored_edge` then answers only a square in the open.
- `LootHouse` (Plan 23 Task 11, P23-7, P23-8): at load level `LOOT_MAX_LEVEL` (1) or below an
  `Interact(x, y, "loot", want, maxWeight=cap)` at `world.nearest_unlooted(want)`, `want` one of `LOOT_WANTS`
  (`food`, `water`, `weapon`, `bandage`), set by the caller (the `Stock` and `LootBuilding` goals), and never `all`:
  Plan 22's loot of
  `all` took whole containers, one interact at level 2 lifting runs 1 and 2 to level 3 and 4. Any other want (None
  included) loots nothing. `cap` is the frame's `load.max` times `LOAD_RATIO_MAX` (1.0), the Lua's loot stopping
  before the carried weight would pass it; 0.0 (no cap) when `load.max` reads no positive number; logged as
  `why["cap"]`. The looted mark is per use (Task 11 fix 1): when the interact ends done, or failed `no match`
  (`LOOT_MARKS`: nothing of the use there), every container on its square holding an item of the loot's filter is
  marked looted for that use only (`world.mark_looted(key, use)`), so a counter looted for water is still looted for
  food later; any other end (failed, rejected, timed out: Task 18 fix 1, the review's major 3, E7's eight loots failed
  `not adjacent` from outside a locked door) counts one failure on each such container (`fails`), the
  LOOT_FAILS_TO_PASS-th (2) marking it, so a container that really cannot be reached is tried twice; except a `failed
  "superseded"`, which a newer send replaced before it ran (Plan 21 lost such a square for the session:
  `docs/reference/research-notes.md`, "A pre-empted loot's square is marked looted"), and a loot whose result carries
  `skipped > 0` (the cap left items), which marks nothing: its square waits in `capped` for that use until the
  frame's `load.weight` falls below its reading at that loot's end (a drop or a meal), so the bot never re-sends a
  loot that cannot fit, and `target(want)` (the container a loot would go to, which the goal layer's view reads too)
  leaves it out meanwhile; an unreadable weight keeps it waiting. `within` (Plan 23 Task 13), a set of container
  keys or None, keeps `target` to those keys: the `LootBuilding` goal sets it to its building's. The level
  guard stays the backstop, spec § 9 (1), "a policy stops looting before level 3": above LOOT_MAX_LEVEL it sends
  nothing (`why["hold"]`), and no loot is sent again until the level is back under 2. It never drops (Plan 23 Task 12):
  the drop is Survive's `load` branch, which at `DROP_AT` (3) or above sends `Drop` of `spare(world)`, the heaviest
  held item that is neither the wielded weapon's type, nor of use `weapon`, `food` or `water` by `world.by_use()` (a
  bottle the planner marked empty reads `other`, so it is dropped), one a decision, until the frame's level reads
  `DROP_TO` (2); Survive's flee sends one `spare()` drop of its own at `DROP_AT` (`survive.py`).

HEURISTIC: an item's use is `agent.base.items.use_of`: food and water off `data/food-items.json` (the dataset's food and
fluid containers), a weapon by `items.WEAPON_RX`'s fullType names, which is no game data (the dataset names no weapon).
"""
import math
import time

from agent.base.items import holds_use, use_of
from agent.base.pza1 import Aim, Attack, Interact, Scan, Shove, Steer, Stomp, Stop, WalkTo
from agent.base.world import STUCK_AREA_N, STUCK_WALK_CAP, me_floor, me_xy

DANGER_R = 6.0        # tiles: a zombie this close is a threat (Survive's threat branch; the night sends nothing)
FIGHT_REACH = 2.0     # tiles: a nearest zombie beyond this is walked to, within it attacked
FIGHT_MAX_S = 20.0    # wall seconds the target may stay beyond FIGHT_REACH before the fight reads stalled
DISENGAGE_R = 10.0    # tiles: a pinned target beyond this is dropped (and Survive's hold radius while a threat runs)
ENGAGE_R = 9.0        # tiles: one or two zombies listed this near are sought (ruling P24-X, Plan 24 Task 18: E7 killed
                      # nothing in 227 game minutes, its goal walking on with a lone zombie listed at 7 to 10 tiles);
                      # Task 18 fix 1, the review's minor 8: a tile inside DISENGAGE_R, the band in which a fight holds
                      # but none is engaged, so a zombie idling at 10 tiles does not flap goal, fight, goal
REPOSITION_R = 2.5    # tiles: a reposition square farther than this from the player is never walked to (P23-Q)
REPOSITION_MIN = 1.2  # tiles: ... nor one whose centre is nearer than this, inside the Lua walk's DONE_R 1.0 (P23-AJ 5)
MISSES_TO_APPROACH = 2   # attack results in a row with attackStarted false before one approach walk
STALL_SWINGS = 3      # started swings in a row on one target that took no health before it reads unreachable
UNREACHABLE_S = 20.0  # wall seconds a no-progress target is skipped
SEEK_SWITCH_R = 0.5   # tiles: a seek re-pins to another zombie at least this much nearer than its target (Task 18 fix
                      # 1, the review's blocker: E7's 564 closed to 2.84 tiles while the seek was on 534 at 5.3; a
                      # judgment, the margin keeping two zombies at about one distance from flapping the pin)
SEEK_SKIP_S = 60.0    # wall seconds a target whose seek walk failed for a walk reason is skipped (Task 18 fix 1, the
                      # review's major 2, a judgment: three UNREACHABLE_S, so a zombie behind a gate is not walked at
                      # again every 20 s while the goal loots)
FLEE_S = 3.0          # seconds a flee's steer runs before it is re-aimed
NEAR_R = 2.0          # tiles: a held threat this near is never `ahead` of a heading (the cone and tube reads look
                      # beyond it: fix 2, T2); named SPRINT_R while the steer sprinted within it (P24-O renamed it)
SHELTER_FLEE_R = 25.0  # tiles: a flee runs to a known door whose approach square is this near (ruling P23-AG)
FLEE_GAIT = "run"     # every flee leg and walk's gait (P23-AG; ruling P24-O: the planner never sprints, #4296)
CORRIDOR_R = 2.0      # tiles: a zombie this near the line to a door's approach square, ahead, refuses it (fix 1, I1)
STEER_PROBE = 3.0     # tiles: a steer heading is clear when the map's line this far along it is (fix 1, I4)
STEER_TURNS = (0, 30, -30, 60, -60, 90, -90)   # degrees a blocked heading turns, nearest first
WIDE_TURNS = (120, -120, 150, -150, 180)         # ... then, with none of those clear, the rest of the circle (Task 18,
                                                 # the E7 write-up's T19.5: four legs ran into a known fence corner)
STEP_PROBE = 1.0      # tiles: the last resort's probe, a heading whose first tile crosses no known blocked edge
STUCK_MOVE = 0.5      # tiles: a steer leg that moved less is stuck, and the next turns off the away vector
AHEAD_R = 9.0         # tiles: a 3 s leg at about 3 tiles/s (E1's flee): a held threat this far ahead refuses a heading
AHEAD_CONE = 20.0     # degrees: ... within this cone of it (or in its CORRIDOR_R tube), beyond NEAR_R (fix 2, T2)
DOOR_CLEAR_R = 1.5    # tiles: no re-close is tried with a known zombie this near the door square's centre (fix 2)
EXIT_CLEAR_R = 1.5    # tiles: no exit is walked with a held threat this near its outside square or ahead on its
                      # straight line (the tube, `_in_tube`): P23-AJ fix 1, narrowed at P24-A fix 1 (3), never one at
                      # the player's back
WALK_STALL_S = 1.0    # wall seconds a flee walk may leave the player within STUCK_MOVE before it is dropped: the exit
                      # walk (P23-AJ fix 1, G2), a shelter step's walk while a held threat is within DANGER_R (P23-AM 2)
                      # and a running steer leg's stuck read (P23-AM fix 1, R1); one quantity (P24-A (g), the close
                      # review's M3: the old EXIT_STALL_S and STEP_STALL_S merged)
CORNERED_R = 1.5      # tiles: Survive's corner's trigger radius (P23-AJ 2)
STUCK_NEAR_R = 1.5    # tiles: a running leg unmoved WALK_STALL_S with a held threat this near is stuck (P23-AM fix 1,
                      # R1; split from CORNERED_R, P24-A (g), the close review's M4)
LISTED_R = 12.0       # tiles: the listing's edge, the frame's zombie list (#4268: E5's horde listed at 12 tiles):
                      # the `many` count (Survive) and a fight's look behind its target (P24-A (a), (b))
POINT_BLANK_R = 1.0   # tiles: a cornered Fight's target this near is swung at whatever its line reads (P23-AJ fix 1)
REPIN_MARGIN = 0.3    # tiles: the point-blank re-pin goes when the new zombie is at least this much nearer than the pin
                      # (or the pin beyond CORNERED_R): P24-A fix 1 (2), a ruling (F1's pin alternated at 0.18 apart)
BEHIND_MARGIN = 0.5   # tiles: a zombie is behind a fight's target only this much farther or more (P24-A fix 1 (5), a
                      # ruling: one beside the target, 0.16 tiles farther, is not behind it)
AIM_LEG_S = 2.0       # seconds one stance leg (`aim`) holds before the stance fight re-aims (ruling P24-G 1)
STAND_MAX_S = 20.0    # wall seconds a standing fight may go without its target's health falling (or a new target
                      # after a kill) before it closes on the target in the stance (`advance`; ruling P24-N: no
                      # stand-off, and no run)
KEEP_R = 2.5          # tiles: a target inside this and beyond FIGHT_REACH is backpedalled from; farther, the stance
                      # stands facing it and lets it come (ruling P24-N, superseding P24-M's band of FIGHT_REACH + 1)
KEEP_MARGIN = 0.25    # tiles: a running backpedal holds until its target is this far past KEEP_R, so the back and
                      # stand legs do not flap at the line (Task 12 fix 1, the review's major 1)
AIM_HOLD_S = 2.0      # seconds the Lua keeps a stance an attack swung from once nothing runs (K.AIM_HOLD_MS 2000,
                      # PZAgent_Stance.lua): an attack ended longer ago left the character out of the stance
STUCK_SKIP_DEG = 15.0  # degrees: after a stuck leg, no heading this near its heading is chosen again (fix 3, F4)
SCAN_R = 10           # tiles: the scan radius, and the grid a place is rounded to
LOOT_MAX_LEVEL = 1    # spec § 9 (1) "stops looting before level 3": a loot is sent only at load level 0-1
CLOTHING_HELD_N = 3   # unworn garments held at which `clothing` is no longer wanted (Task 24: the wear rule judges each
                      # garment once held; a judgment bounding the surplus the loot carries)
CLOTHING_LOOT_KG = 1.5   # kg a clothing loot may take per garment still wanted (review-t24 major 3; a judgment: a
                      # coat or boilersuit weighs about that), so a full wardrobe leaves the cap to the food
LOAD_RATIO_MAX = 1.0  # a loot fills to this times the frame's load.max (level 1 holds up to 1.25 of it, #3926)
LOOT_FAILS_TO_PASS = 2   # failed loots of one container for one use before it is passed (Task 18 fix 1, the review's
                         # major 3: as a door's DOOR_FAILS_TO_MARK; a failure is not an empty container)
LOOT_MARKS = ("no match",)   # the failed loot's reasons that mark at once: nothing of the use there
LOOT_WANTS = ("food", "water", "weapon", "bandage", "container", "clothing")   # a loot's want and filter: one use,
                      # never `all` (P23-8); `container` (an empty vessel, the Lua's filter since PZA/1.5.1) by P24-Y;
                      # `clothing` (the Lua's filter since PZA/1.6, Plan 24 Task 24; a build without `wear` never loots it)
DROP_AT = 3           # at this load level or above Survive's load branch drops (the heavy-load drain falls at 3) ...
DROP_TO = 2           # ... down to this level, and between the two neither drops nor loots
KEPT_USES = ("weapon", "food", "water")   # the uses a drop never takes
AIM_R = 12.0   # tiles: the Lua's K.AIM_R (PZAgent_Stance.lua), the farthest target an aim takes: beyond it the aim is refused `no target`
NO_TARGET = "no target"   # the Lua's refusal of an aim whose target is gone (Task 10 fix 2: not a stand-off)
PREEMPTED = "superseded"   # the reason the Lua fails an action a newer send replaced
RIDE_TYPES = ("walkTo", "steer")   # the legs a keepMoving bandage rides (PZA/1.5.3, ruling P24-R)
STUCK_REASONS = ("stuck", "no path", "no square")   # a walkTo failed for one of these: its target is remembered
SWING_TYPES = ("attack", "aim", "shove", "stomp")   # the Fight's sends whose result's `targetDead` is a kill (P24-Q)
STRAIN_SOFT = 10.0    # the frame's body.armPain at which a swing's damage starts to fall (divided by armPain / 10,
                      # #4370): the Fight prefers the stomp and the point-blank shove (ruling P24-AG); under it again
                      # the strain hold ends
STRAIN_HARD = 20.0    # ... at which the damage is halved: the threat branch disengages and starts no new fight until
                      # armPain falls under STRAIN_SOFT (ruling P24-AG)
ENDURANCE_T = 0.75    # the frame's stats.endurance at or under which the ENDURANCE moodle reads level 1 (#3926, #4076),
                      # whose first level halves every swing (#4371): the disengage of P24-AG
ENDURANCE_RELEASE = 0.80   # ... and above which that hold ends (review-t27: rest gives back 0.003-0.005 a game minute,
                           # a fight takes far more, so the edge alone flickered flee / one swing / flee)
TIRED_FIGHT_T = 0.6   # stats.fatigue at or above which no fight is sought or stood (ruling P24-AK; the first TIRED
                      # moodle, night.TIRED_T, halves every swing at its first level too, #4371)
SHOVE_R = 1.5         # tiles: the Lua's shove refuses a target beyond this (`too far`, PZAgent_Stance.lua K.SHOVE_R)
STAND_MIN_R = 0.61    # tiles: a standing zombie this near the player makes the engine's call shove it (the weapon's
                      # MinRange, #4372: the bat's 0.61, the bare hand's 0.6), so no shove or stomp of another is sent
                      # (ruling P24-AH; the frame carries no MinRange, the bat's the widest read)
SWING_SKIP_S = UNREACHABLE_S   # wall seconds a target whose shove or stomp the Lua refused or failed is not sent that
                               # skill again (the stomp's floor strike follows instead: ruling P24-AL)
KNOCK_READ_S = 2.0    # wall seconds a shove's `knockdown` true reads its target downed before the frame's `onFloor`
                      # does (PZA/1.7.1, 9 fix 12: the result is read off the knocked-down state at the hit, onFloor
                      # follows about a second later; a judgment, two of those), so the stomp follows the shove at once
PULL_R = FIGHT_REACH + KEEP_R   # tiles: the pull of a lone chaser ends, the stance taken, once it is this near (ruling
                      # P24-AN: "until the chaser alone is within FIGHT_REACH + KEEP_R"; 4.5)


def place_of(world):
    """The player's square on a uniform SCAN_R grid (half up, never Python's half-even round): Explore's place."""
    mx, my = me_xy(world)
    return int(math.floor(mx / SCAN_R + 0.5)) * SCAN_R, int(math.floor(my / SCAN_R + 0.5)) * SCAN_R


def centre(sq):
    """The centre `(x + 0.5, y + 0.5)` of the square holding (x, y): every walk the planner sends to a square targets
    it. The Lua's walk ends `done` within its DONE_R (1.0 tiles) of the target, so a square's integer corner, which
    lies within 1.0 of the character on any square touching its own, ended every X5-2 reposition walk on its accept
    tick without a step (T18.4)."""
    return math.floor(sq[0]) + 0.5, math.floor(sq[1]) + 0.5


def item_id_ok(iid):
    """An inventory key usable as a command's itemId: an int, not a bool."""
    return isinstance(iid, int) and not isinstance(iid, bool)


def target_id_ok(zid):
    """A zombie id a Fight can target: an int, not a bool (a nil read keys the zombie None); the one rule
    `world.nearest_zombie` and Survive's reachable-threat set share."""
    return isinstance(zid, int) and not isinstance(zid, bool)


def zdist(world, z):
    """Tiles from the player to a zombie's last seen square."""
    mx, my = me_xy(world)
    return math.hypot(z["x"] - mx, z["y"] - my)


class Policy:
    """One action at a time: see the module docstring."""

    trans = True   # ruling P24-AS: a heading read (`clear_heading`) refuses a `solidTrans` square; Survive sets it each
                   # tick from its TRANS switch (the replay tests' seam onto the rules before it)

    def __init__(self, world, actions, clock=time.time):
        self.world = world
        self.actions = actions
        self.clock = clock
        self.last = None      # the last Action this policy sent
        self.why = {}

    def busy(self):
        """True while this policy's last action runs (`running`: the current one and not yet terminal, or a leg a
        riding bandage left running)."""
        return running(self.actions, self.last)

    def observe(self):
        """Bookkeeping from the World and the last action's end; called every tick, idempotent."""

    def choose(self):
        """The next command, or None; called only when not busy."""
        raise NotImplementedError

    def sent(self, cmd, action):
        """Bookkeeping once `cmd` went out as `action`."""

    def send(self, cmd):
        action = self.actions.send(cmd)
        self.last = action
        self.sent(cmd, action)
        return action

    def step(self):
        self.observe()
        if self.busy():
            return None
        cmd = self.choose()
        return None if cmd is None else self.send(cmd)


def spare(world):
    """The id of the heaviest held item that is neither the wielded weapon's type nor of use weapon, food or water by
    `world.by_use()` (so a bottle marked empty is `other`, and spare) nor a worn garment (use `clothing`, PZA/1.6),
    ties by the least id; else None. Survive's load
    branch and its flee drop it."""
    wielded = (world.weapon or {}).get("type")
    by_use = world.by_use()
    kept = {iid for use in KEPT_USES for iid in by_use[use]}
    best = None
    for iid, it in world.inventory.items():
        if not item_id_ok(iid) or iid in kept or (it.get("fullType") or "") == wielded:
            continue
        if it.get("use") == "clothing" and it.get("worn") is True:
            continue   # Task 24: the garment on the back is never the spare (dropping it would undo the wear)
        rank = (-(it.get("weight") or 0.0), iid)
        if best is None or rank < best:
            best = rank
    return best[1] if best else None


def line_to(world, z):
    """The line from the player to zombie record `z` (`world.line_clear`), None when the frame has no position or the
    map lacks either end square on the player's floor: an unscanned end is never read as a wall. The Fight's line
    check and Survive's inside hold (fix wave P, M-6) share it."""
    me = world.me or {}
    a, b = (me.get("x"), me.get("y")), (z.get("x"), z.get("y"))
    if a[0] is None or a[1] is None or b[0] is None or b[1] is None:
        return None
    floor = me_floor(world)
    if any((int(math.floor(q[0])), int(math.floor(q[1])), floor) not in world.map for q in (a, b)):
        return None
    return world.line_clear(a, b)


def in_reach(world, z, r):
    """Zombie `z` is in a cornered Fight's reach (fix round 2, G4): within POINT_BLANK_R, or within `r` with its line
    not read blocked (`line_to` True or None). A zombie at 1.0-1.5 tiles behind a blocked line is no corner's target:
    it is hitting the wall from outside."""
    if z.get("x") is None or z.get("y") is None:
        return False
    d = zdist(world, z)
    return d <= POINT_BLANK_R or (d <= r and line_to(world, z) is not False)


def others_behind(world, zid, z):
    """Ruling P24-A (b) (E5 line 219: the fight walked at 19275, 5.99 tiles off, with 19278 and 19249 listed 11 tiles
    out within 13 degrees of its bearing; the group arrived round it): the ids, sorted, of the other zombies listed
    within LISTED_R of the player that lie BEHIND_MARGIN or more beyond the target `z` (id `zid`; P24-A fix 1 (5))
    and within AHEAD_CONE of its bearing. A
    zombie with no position, or the target at the player's own position, is none."""
    mx, my = me_xy(world)
    tx, ty = z["x"] - mx, z["y"] - my
    td = math.hypot(tx, ty)
    if td == 0.0:
        return []
    cos_cone = math.cos(math.radians(AHEAD_CONE))
    out = []
    for oid, o in world.zombies.items():
        if oid == zid or o.get("x") is None or o.get("y") is None:
            continue
        dx, dy = o["x"] - mx, o["y"] - my
        d = math.hypot(dx, dy)
        if td + BEHIND_MARGIN <= d <= LISTED_R and (dx * tx + dy * ty) >= d * td * cos_cone:
            out.append(oid)
    return sorted(out, key=repr)


def hit_reaction(world):
    """The frame's `me.hitReaction` when it names one (PZA/1.4, a non-empty string), else None (absent on a PZA/1.3
    frame): no swing starts while it is set (#4292, #4293)."""
    h = (world.me or {}).get("hitReaction")
    return h if isinstance(h, str) and h else None


def arm_pain(world):
    """The frame's `body.armPain` (PZA/1.7: the summed pain of the six arm parts, #4370) when a number, else None (a
    frame written before PZA/1.7 carries none: no strain rule reads it)."""
    v = (world.body or {}).get("armPain")
    return v if isinstance(v, (int, float)) and not isinstance(v, bool) else None


def arms_hurt(world):
    """Ruling P24-AP (#4370: a swing that is not a stomp divides its damage by the summed arm pain over 10, whatever
    the pain's source, a bite's included): the frame's `body.armPain` at STRAIN_HARD or above, where a swing does half
    its damage or less, so the Fight never swings (the shove ignores damage, #4373; the stomp's damage is set after
    the divider, #4374)."""
    pain = arm_pain(world)
    return pain is not None and pain >= STRAIN_HARD


def on_floor(z):
    """Zombie record `z` lies on the floor (PZA/1.7's `onFloor`: knocked down, or crawling); absent is standing."""
    return z.get("onFloor") is True


def pull_from(world, t, skip=(), reach=ENGAGE_R):
    """Ruling P24-AN, the pull (the guides notes § 9 change 8: draw one from a group by walking away, then fight it
    alone; E9 dropped six fights for a chaser 10.74 to 11.90 tiles behind the target, the look behind's `held`): the
    centroid (x, y) of the other zombies listed within LISTED_R when target `t` (id, zombie, dist) chases the player
    (`hasTarget`) within `reach` (ENGAGE_R; a chaser already pulled is kept to DISENGAGE_R: `Fight.seeking`), no other
    zombie chases within ENGAGE_R (one chaser), every other listed zombie stands beyond DANGER_R and at least one is
    listed; else None. The ids in `skip` (read dead) are no zombies."""
    zid, z, d = t
    if not chasing(z) or d > reach:
        return None
    xs, ys = [], []
    for oid, o in world.zombies.items():
        if oid == zid or oid in skip or o.get("x") is None or o.get("y") is None:
            continue
        od = zdist(world, o)
        if od > LISTED_R:
            continue
        if od <= DANGER_R or (od <= ENGAGE_R and chasing(o)):
            return None
        xs.append(o["x"])
        ys.append(o["y"])
    return (sum(xs) / len(xs), sum(ys) / len(ys)) if xs else None


def away_vector(world, points):
    """The unit vector along the sum of the unit vectors from each of `points` ((x, y)) to the player, each weighted
    by 1/distance (ruling P23-AG 3: away from the centroid and from the nearest, so a group spread round the player is
    not fled into), else None when the sum is zero. The flee's legs and the stance fight's backpedal (P24-G 1) share
    it."""
    mx, my = me_xy(world)
    vx = vy = 0.0
    for px, py in points:
        dx, dy = mx - px, my - py
        d2 = dx * dx + dy * dy
        if d2 > 0.0:
            vx, vy = vx + dx / d2, vy + dy / d2   # (unit vector) / distance
    n = math.hypot(vx, vy)
    return None if n == 0.0 else (vx / n, vy / n)


def clear_heading(world, v, reach=STEER_PROBE, trans=True):
    """The map's line `reach` tiles along `v` from the player, an unknown square open (fix round 2, concern 1). A
    hoppable fence's edge reads blocked (`line_clear` never climbs: a steer or a backpedal never vaults, ruling P24-G
    4). `trans` (ruling P24-AS; a policy's `trans`, Survive's TRANS): a `solidTrans` square (a fence, a window or a
    counter the engine blocks but sees through: E9 held its y 16.511 s against such a row while every steer pointed
    into it) refuses the heading as a solid one does; off, `solid` alone, the rule before it."""
    mx, my = me_xy(world)
    return world.line_clear((mx, my), (mx + reach * v[0], my + reach * v[1]), unknown_open=True, trans=trans)


def stance_leg_kind(d, advance, seek=False, pull=False):
    """The stance leg a standing fight's target `d` tiles off calls for (rulings P24-G 1, P24-N, P24-X and P24-AN):
    `enter` within FIGHT_REACH, `toward` in the advance, `pull` while the fight pulls a lone chaser away from the group
    (`pull`: the caller's `Fight.pulling`, beyond PULL_R), `seek` while the fight seeks it (`seek`: the caller's
    `Fight.seeking`, whose `seek_allowed` holds the one KEEP_R guard: Task 18 fix 1, the review's minor 13; the caller
    has already excluded a target inside KEEP_R, so `seek` here means d > KEEP_R: fix 2, minor 4), `back`
    inside KEEP_R, else `stand`. `Fight._stance_leg` sends it and `Fight.busy` gives a running leg way when it changes
    (Task 12 fix 1)."""
    if d <= FIGHT_REACH:
        return "enter"
    if advance:
        return "toward"
    if pull:
        return "pull"
    if seek:
        return "seek"
    return "back" if d <= KEEP_R else "stand"


def chasing(z):
    """Zombie record `z` reads a target (`hasTarget` true): it is coming."""
    return z.get("hasTarget") is True


def seek_allowed(world, t, hold_ground):
    """Ruling P24-X as Task 18 fix 1 narrows it (the review's ruling 2): target `t` (id, zombie, dist) may be sought:
    beyond KEEP_R, the character not holding ground (`hold_ground`: on a room or door square, Survive's
    `_chokepoint`: inside a building, the broken hold's and the trapped fight's included, or in a doorway, the stance
    stands and lets it come), and not a chasing target whose straight line to the character crosses a known fence
    (`World.fence_on_line`: the fence is the chokepoint)."""
    if t[2] <= KEEP_R or hold_ground:
        return False
    if not chasing(t[1]):
        return True
    mx, my = me_xy(world)
    return not world.fence_on_line((mx, my), (t[1]["x"], t[1]["y"]))


def rides_on(actions, a):
    """Leg `a` (a walkTo or a steer, not yet terminal) is kept running by the Lua under the bandages sent after it,
    every one of them with `keepMoving` (PZA/1.5.3, ruling P24-R: a riding bandage leaves the leg its slot; a new leg
    takes the ride along, any other send ends both): Task 12 fix 1, P24-U."""
    if a.type not in RIDE_TYPES or actions.done(a):
        return False
    for b in reversed(actions.history):
        if b is a:
            return True
        if b.type != "bandage" or b.args.get("keepMoving") is not True:
            return False
    return False


def running(actions, a):
    """Action `a` runs: the current action, or a leg a riding bandage sent since has left running (`rides_on`)."""
    return a is not None and (actions.current is a or rides_on(actions, a))


def blocked(unreachable, now):
    """The ids of `unreachable` (id -> wall until) still skipped at `now`."""
    return {zid for zid, until in unreachable.items() if until > now}


class Fight(Policy):
    def __init__(self, world, actions, clock=time.time, unreachable=None, target=None, dead=None):
        super().__init__(world, actions, clock)
        self.dead = {} if dead is None else dead   # zombie id -> wall until it is skipped: read dead (Task 12 fix 1)
        self.out_of_reach_since = clock()   # the stall clock: since when the target has been out of reach
        self.misses = 0                     # attack results in a row with attackStarted false
        self.approach = False               # the next command is an approach walk
        self.unreachable = {} if unreachable is None else unreachable   # target id -> wall until it is skipped
        self.target = target                # the pinned zombie id, None until the first choose pins one
        self.only = None                    # a set of zombie ids the Fight may target (Survive's door fight), or None
        self.point_blank = False            # a cornered Fight: a target within POINT_BLANK_R skips the line check
        self.mark_free_r = 0.0              # a cornered Fight: no zombie `in_reach` this near is skipped for its mark
        self._marked_now = set()            # the ids marked during the running choose (G4), skipped by the recursion
        self.repositioned = False           # the one reposition walk on the pinned target was sent
        self.no_progress = 0                # started swings in a row on `_streak_id` that took no health
        self._streak_id = None
        self._streak_h = None               # the target's health at the streak's start
        self._counted = None                # the last attack whose result was counted
        self.stance = False                 # Survive sets it each tick: the standing fight applies (P24-G 1)
        self.threats = None                 # Survive sets it: the held threats the backpedal steps away from
        self.standoff = False               # the stand went STAND_MAX_S without progress: approach and swing
        self.standoff_why = None            # why it fell back: "<state> <reason>" of a stance leg that failed
        self.advance = False                # the stand went STAND_MAX_S without progress: close in the stance (P24-N)
        self._leg_read = None               # the last stance leg whose end observe() has read
        self._stand = None                  # (target id, wall of the stand clock's start, its health then)
        self._leg = None                    # the kind of the last stance leg sent: enter, stand, back or toward
        self._attack_held = False           # the last attack was sent from the held stance (Task 9's hand-over)
        self._held_before = False           # the stance read held at the choose that chose the attack
        self.kill = None                    # this observe's kill: the target id its attack or aim read dead (P24-Q)
        self.ride = None                    # Survive sets it each tick: the riding bandage while one runs (P24-U)
        self._kill_read = None              # the last attack or aim whose result the kill read has seen
        self.seek = False                   # Survive sets it on a Fight it engages (ruling P24-X): sought to KEEP_R
        self._seek_walk = None              # (walk, target id) of the last seek walk sent, until its end is read
        self._seek_send = False             # the walk the running choose returns is a seek's (P24-X)
        self.sought = set()                 # the target ids whose seek reached KEEP_R (then iteration 7's stance)
        self.hold_ground = False            # Survive sets it each tick: on a room or door square, no seek (fix 1)
        self.avoid = set()                  # Survive sets it each tick: ids never pinned anew beyond DANGER_R (fix 1,
                                            # major 2: a zombie no engage reaches)
        self._walk_kind = None              # the stance walk the running choose returns: "round" or "far" (fix 1)
        self._stance_walk = None            # (walk, target id, kind) of the stance's running walk (the blocker)
        self.swing_refused = {}             # (shove or stomp, zombie id) -> wall until that skill is not sent at it
                                            # (SWING_SKIP_S: the Lua refused or failed it; P24-AL's floor strike then)
        self._shoved = False                # the last swing-like send was a shove: the next is the swing (P24-AH)
        self.knocked = {}                   # zombie id -> wall until a shove's knockdown reads it downed (KNOCK_READ_S)
        self.pull = False                   # Survive sets it on a Fight it seeks (ruling P24-AN): a lone chaser pulled
        self._pulled = None                 # the zombie id the last pull leg was sent at (P24-AN)
        self.doorway = None                 # the building a doorway stand holds (`planner.doorway.Doorway`), else None

    def marked(self):
        """The unreachable ids skipped now: the marked ones, less, for a cornered Fight (`mark_free_r`, fix round 1
        I3), a marked zombie `in_reach` within that radius (fix round 2, G4: within POINT_BLANK_R, or with a line not
        read blocked; one behind a blocked line at 1.0-1.5 stays marked); and always every id marked during this
        choose (G4: the mark's recursion never re-pins the id it just marked)."""
        out = blocked(self.unreachable, self.clock())
        if self.mark_free_r > 0.0:
            zs = self.world.zombies
            out = {zid for zid in out if not (zid in zs and in_reach(self.world, zs[zid], self.mark_free_r))}
        return out | self._marked_now

    def blocked(self):
        """The ids skipped now: the `marked` ones and those read dead within UNREACHABLE_S (`dead`, whatever the
        corner's reach: a dead zombie is never swung at)."""
        return self.marked() | blocked(self.dead, self.clock())

    def _target_health(self, zid):
        z = self.world.zombies.get(zid)
        return None if z is None else z.get("health")

    def _mark_unreachable(self, zid, seconds=UNREACHABLE_S):
        self._marked_now.add(zid)
        self.unreachable[zid] = self.clock() + seconds
        if zid == self.target:
            self._unpin()

    def _unpin(self):
        self.target, self.repositioned = None, False

    def _swing_landed_nothing(self, zid):
        """Count one started swing on `zid` against its health at the streak's start; mark the target unreachable
        after STALL_SWINGS that took none."""
        h = self._target_health(zid)
        if zid != self._streak_id or h is None:
            self._streak_id, self._streak_h, self.no_progress = None, None, 0
            return
        if self._streak_h is None or h < self._streak_h:
            self._streak_h, self.no_progress = h, 0
            return
        self.no_progress += 1
        if self.no_progress >= STALL_SWINGS:
            self._mark_unreachable(zid)
            self._streak_id, self._streak_h, self.no_progress = None, None, 0

    def _pinned(self):
        """(id, zombie, dist) of the pinned target while it holds: it is dropped once dead or gone from the World,
        positionless, unreachable, or beyond DISENGAGE_R."""
        if self.target is None:
            return None
        z = self.world.zombies.get(self.target)
        if (z is None or z.get("x") is None or z.get("y") is None or self.target in self.blocked()
                or (self.only is not None and self.target not in self.only)):
            self._unpin()
            return None
        d = zdist(self.world, z)
        if d > DISENGAGE_R:
            self._unpin()
            return None
        return self.target, z, d

    def _nearest(self):
        skip = self.blocked()
        if self.only is not None:
            skip = skip | {zid for zid in self.world.zombies if zid not in self.only}
        if self.avoid:   # fix 1, major 2: never pinned anew beyond DANGER_R (within it the old rules: the line check)
            zs = self.world.zombies
            skip = skip | {zid for zid in self.avoid if zid in zs and zs[zid].get("x") is not None
                           and zs[zid].get("y") is not None and zdist(self.world, zs[zid]) > DANGER_R}
        nz = self.world.nearest_zombie(exclude=skip)
        if nz is None or nz[1].get("x") is None or nz[1].get("y") is None:
            return None
        zid, z = nz
        return zid, z, zdist(self.world, z)

    def _target(self, pin):
        """The Fight's target: the pinned one while it holds, else the nearest reachable zombie, pinned when `pin`."""
        t = self._pinned() or self._nearest()
        if pin and t is not None and self.target != t[0]:
            self.target, self.repositioned = t[0], False
        return t

    def _line(self, z):
        """`line_to` the target: None over an unscanned end, the swing then left to the no-progress stall."""
        return line_to(self.world, z)

    def _reposition(self, z):
        """The square to reposition to: of `world.reachable_adjacent` of the target's square (nearest the player
        first), the first within REPOSITION_R of the player and at least REPOSITION_MIN from it (by its centre) from
        whose centre the line to the target is clear; None when none is. `reachable_adjacent` reads the squares open
        to the target, not to the player: the radius keeps a detour round a building out of the reflex (ruling
        P23-Q); the floor (ruling P23-AJ 5: E2's centre walk 0.86 tiles off ended `done` on its accept tick without a
        step, inside the Lua walk's DONE_R 1.0) keeps a walk that cannot move out of it."""
        floor = me_floor(self.world)
        mx, my = me_xy(self.world)
        for sq in self.world.reachable_adjacent((z["x"], z["y"]), floor):
            c = (sq[0] + 0.5, sq[1] + 0.5)
            d = math.hypot(c[0] - mx, c[1] - my)
            if d > REPOSITION_R:
                break   # nearest the player first: every later square is as far or farther
            if d < REPOSITION_MIN:
                continue   # P23-AJ 5: within the walk's DONE_R the walk ends done on its accept tick, unmoved
            if self.world.line_clear(c, (z["x"], z["y"])):
                return sq
        return None

    def standing(self):
        """The stance fight applies (ruling P24-G 1): Survive's `stance`, no stand-off fallback yet, and neither a
        cornered Fight (`point_blank`, the corner rules) nor a door fight (`only`)."""
        return self.stance and not self.standoff and not self.point_blank and self.only is None

    def stance_at(self, d):
        """The stance applies to a target `d` tiles off: `standing` and within AIM_R (Task 10 fix 2: farther, the Lua
        refuses the aim `no target`, so the Fight walks toward it as the approach and swing does and takes the stance
        once inside)."""
        return self.standing() and d <= AIM_R

    def _observe_stand(self, t):
        """The stand clock (ruling P24-G 1, as P24-N rules its end): restarted by a new target (a kill or a re-pin)
        and by a fall of the target's health, each restart ending an advance; once it reads STAND_MAX_S the Fight
        closes on the target in the stance (`advance`: `aim` legs toward it), its out-of-reach stall clock starting
        then (so a target it cannot reach still ends in the stalled flee, FIGHT_MAX_S later)."""
        if not self.standing() or t is None or t[2] > AIM_R:   # beyond AIM_R the walk toward it: no stand to time
            self._stand, self.advance = None, False
            return
        now = self.clock()
        h = self._target_health(t[0])
        if (self._stand is None or self._stand[0] != t[0]
                or (h is not None and self._stand[2] is not None and h < self._stand[2])):
            self._stand, self.advance = (t[0], now, h), False
        elif not self.advance and now - self._stand[1] >= STAND_MAX_S:
            self.advance = True
            self.out_of_reach_since = now

    def _fall_back(self, why):
        """The stance cannot be held (a stance leg that failed): the approach and swing for the rest of the Fight
        (`standoff`), its stall clock starting now."""
        self.standoff, self.standoff_why, self._stand, self.advance = True, why, None, False
        self.out_of_reach_since = self.clock()

    def _observe_leg(self):
        """Minor 11 (Task 10 fix 1): the first stance leg that ends failed, timed out or rejected (a superseded one is
        this planner's own next send) ends the stand."""
        a = self.last
        if a is None or a.type != "aim" or not self.actions.done(a) or a is self._leg_read:
            return
        self._leg_read = a
        if (a.state in ("failed", "timeout", "rejected") and not (a.state == "failed" and a.reason == PREEMPTED)
                and a.reason != NO_TARGET):   # Task 10 fix 2: the target is gone, not a build that cannot hold the stance
            if not self.standoff:
                self._fall_back(("%s %s" % (a.state, a.reason)).strip())

    def seeking(self, t):
        """Ruling P24-X: the Fight is sought (`seek`) and target `t` (id, zombie, dist) has not yet come within KEEP_R
        (`sought`) and may be sought (`seek_allowed`: Task 18 fix 1's ruling 2, never from a room or door square, nor
        across a known fence at a chasing target): its legs close on it (`seek`), a walk at a walk beyond AIM_R."""
        return (self.seek and t is not None and t[0] not in self.sought
                and seek_allowed(self.world, t, self.hold_ground) and not self._pull_waits(t))

    def pull_centroid(self, t, reach=ENGAGE_R):
        """Ruling P24-AN: the centroid of the group a lone chaser `t` is pulled from (`pull_from` within `reach`, the
        zombies read dead left out), while `pull` is set and the stance applies to it; else None."""
        if not self.pull or t is None or not self.stance_at(t[2]):
            return None
        return pull_from(self.world, t, blocked(self.dead, self.clock()), reach)

    def _pull_pin(self):
        """Ruling P24-AN: with nothing pinned, the one zombie chasing within ENGAGE_R is pinned when the pull applies to
        it (`pull_centroid`), before the nearest: the chaser is the fight, a nearer idle one part of the group."""
        if not self.pull or self.target is not None:
            return
        skip = self.blocked()
        chasers = [(zid, z) for zid, z in self.world.zombies.items() if target_id_ok(zid) and zid not in skip
                   and chasing(z) and z.get("x") is not None and z.get("y") is not None
                   and zdist(self.world, z) <= ENGAGE_R]
        if len(chasers) == 1:
            zid, z = chasers[0]
            if self.pull_centroid((zid, z, zdist(self.world, z))) is not None:
                self.target, self.repositioned = zid, False

    def _pull_waits(self, t):
        """Ruling P24-AN (F1 with the PZA/1.5 caps replayed: its line 164 pulled 15911 at 8.93 tiles, which read 9.34 at
        the next tick, past ENGAGE_R, so the seek walked back toward it past the group): a chaser the pull was sent at
        (`_pulled`) that has fallen beyond ENGAGE_R while still a lone chaser within DISENGAGE_R is not sought: the
        stance stands facing it and lets it come (`stand`)."""
        return (t[0] == self._pulled and t[2] > ENGAGE_R
                and self.pull_centroid(t, DISENGAGE_R) is not None)

    def pulling(self, t):
        """Ruling P24-AN, the pull: the Fight seeks target `t` (`seeking`), a lone chaser beyond PULL_R with the rest of
        the listing beyond DANGER_R (`pull_centroid`): its stance legs walk away from the group (`pull`), never toward
        the chaser, until it comes within PULL_R; the look behind reads no walk then (`Survive._behind_walk`)."""
        return t is not None and t[2] > PULL_R and self.seeking(t) and self.pull_centroid(t) is not None

    def _observe_seek(self, t):
        """A sought target within KEEP_R has been sought: the stance fight of iteration 7 from then on (P24-X); so has
        a lone chaser within PULL_R with the rest of the listing beyond DANGER_R (ruling P24-AN: the pull's end, or a
        chaser met there, takes the stance, standing while it comes, never a seek toward it past the group); a seek
        walk (round a wall, or beyond AIM_R) that failed for a walk reason marks the target unreachable for SEEK_SKIP_S
        (Task 18 fix 1, the review's major 2: longer than a swing's mark, so the goal is not superseded every
        UNREACHABLE_S by a zombie behind a gate)."""
        if self.seek and t is not None and (t[2] <= KEEP_R or (
                t[2] <= PULL_R and t[0] not in self.sought and self.pull_centroid(t) is not None)):
            self.sought.add(t[0])
            if not chasing(t[1]) and self.standing() and not self.advance:   # fix 1, minor 10: no stand-off at an
                self.advance, self.out_of_reach_since = True, self.clock()   # idle one; the advance's stall clock
        if self._seek_walk is None or not self.actions.done(self._seek_walk[0]):
            return
        a, zid = self._seek_walk
        self._seek_walk = None
        if a.state == "failed" and a.reason in STUCK_REASONS:
            self._mark_unreachable(zid, SEEK_SKIP_S)

    def _seek_switch(self, t):
        """The zombie (id, zombie, dist) a seek re-pins to (Task 18 fix 1, the review's blocker), else None: while
        target `t` is being sought (`seeking`), the nearest zombie the Fight may pin (`_nearest`: not marked, not dead,
        not avoided beyond DANGER_R) when it is another and SEEK_SWITCH_R or more nearer. The seek closes on the
        nearest; once a target is `sought` the pin holds as iteration 7's stance rules, except in the advance, whose
        walk and `toward` leg give way and re-pin for `_advance_switch` (a zombie inside KEEP_R or SEEK_SWITCH_R
        nearer: Task 18 fix 2). Ruling P24-AN: never while the pull runs (`pulling`: the one chaser is the fight, a
        nearer idle zombie part of the group it is drawn from)."""
        if not self.seeking(t) or self.pulling(t):
            return None
        n = self._nearest()
        return n if n is not None and n[0] != t[0] and n[2] <= t[2] - SEEK_SWITCH_R else None

    def _advance_switch(self, t):
        """The zombie (id, zombie, dist) the advance re-pins to (Task 18 fix 2, the re-review's blocker 1: the advance's
        walk round a wall held while a chasing zombie closed to 1.2 tiles), else None: while the Fight advances on
        target `t`, the nearest zombie the Fight may pin (`_nearest`) when it is another and inside KEEP_R, or
        SEEK_SWITCH_R or more nearer than `t`. The advance ends with the re-pin."""
        if not self.advance or t is None:
            return None
        n = self._nearest()
        if n is None or n[0] == t[0]:
            return None
        return n if n[2] <= KEEP_R or n[2] <= t[2] - SEEK_SWITCH_R else None

    def _walk_gives_way(self):
        """The blocker of Task 18's review (E7 replayed: the seek walk a12 round a wall, sent at line 52 on 533 at 8.17
        tiles, held through line 73 while 533 receded past DISENGAGE_R and 564 and 534 closed to 2.84 and 3.10 tiles
        out of the stance): the stance's running walk (`_stance_walk`: a seek's or the advance's walk round a wall,
        `seek` or `advance`, or a seek's walk beyond AIM_R, `far`) gives way, so the stance leg resumes, once
        - its target is no longer the Fight's (dead, re-pinned, unpinned), or (a walk sent within AIM_R) beyond
          DISENGAGE_R;
        - a seek's walk: another zombie is SEEK_SWITCH_R nearer than its target (`_seek_switch`: the next choose
          re-pins to it, so a zombie closing inside KEEP_R is the stance's target); the advance's walk: another zombie
          inside KEEP_R or SEEK_SWITCH_R nearer (`_advance_switch`, Task 18 fix 2: the next choose re-pins to it and
          ends the advance);
        - the walk beyond AIM_R: the target is within AIM_R (the stance takes it from there);
        - the walk round a wall: the leg the target's distance calls for (`stance_leg_kind`) is no walk's (inside
          KEEP_R, in reach, or no longer sought: a standing leg), or the straight line toward the target now passes
          over STEER_PROBE (the aim)."""
        a, zid, kind = self._stance_walk
        t = self._target(pin=False)
        if t is None or t[0] != zid:
            return True
        if (self._advance_switch(t) if kind == "advance" else self._seek_switch(t)) is not None:
            return True   # fix 2: the advance's walk gives way to a closing zombie as the seek's does
        if kind == "far":
            return t[2] <= AIM_R
        if t[2] > DISENGAGE_R or not self.stance_at(t[2]) or stance_leg_kind(t[2], self.advance, self.seeking(t)) not in ("toward", "seek"):
            return True
        mx, my = me_xy(self.world)
        u = ((t[1]["x"] - mx) / t[2], (t[1]["y"] - my) / t[2])
        return clear_heading(self.world, u, min(STEER_PROBE, t[2]), self.trans)

    def stand_s(self):
        """Wall seconds the running stand has gone without progress, else None."""
        return None if self._stand is None else self.clock() - self._stand[1]

    def busy(self):
        """The Policy's rule, except that a running stance leg gives way at once (P24-G 1) when the target is within
        FIGHT_REACH (the swing from the stance), another target is pinned, or the stand no longer applies; and (Task 12
        fix 1, the review's major 1: a backpedal held its whole AIM_LEG_S while its target fell back past KEEP_R,
        opening the gap the swing needs closed) once the leg the target's distance calls for (`stance_leg_kind`)
        differs from the running one: a standing leg inside KEEP_R or in the advance, a backpedal past KEEP_R +
        KEEP_MARGIN (the margin keeps the two from flapping at the line) or in the advance, an `enter` leg whose
        target was knocked out of reach. A `toward` leg (the advance) holds until reach, or until `_advance_switch`
        names another zombie (inside KEEP_R or SEEK_SWITCH_R nearer: Task 18 fix 2), re-pinned. The stance's own walk (a seek's
        or the advance's) gives way as a leg does (`_walk_gives_way`, Task 18 fix 1, the review's blocker); any other
        walk (the approach and swing's, a reposition) holds until it ends."""
        if not super().busy():
            return False
        if self.last.type == "walkTo" and self._stance_walk is not None and self._stance_walk[0] is self.last:
            return not self._walk_gives_way()
        if self.last.type != "aim":
            return True
        if self._downed():
            return False   # P24-AL: a downed zombie within reach is finished before the stance goes on
        t = self._target(pin=False)
        if t is None or t[0] != self.last.args.get("targetId") or t[2] <= FIGHT_REACH or not self.stance_at(t[2]):
            return False
        if self._leg == "toward":
            return self._advance_switch(t) is None   # fix 2: it holds until reach, or a zombie closing on the character
        want = stance_leg_kind(t[2], self.advance, self.seeking(t), self.pulling(t))
        if want == "seek" and self._leg == "seek" and self._seek_switch(t) is not None:
            return False   # Task 18 fix 1, the blocker: a nearer zombie; the next choose re-pins to it
        if self._leg == "back" and want == "stand":
            return t[2] <= KEEP_R + KEEP_MARGIN
        return want == self._leg

    def in_stance(self):
        """The Lua holds the stance now (Task 9's hand-over, PZAgent_Stance.lua): the last action sent by anyone is
        this Fight's aim still running, or its attack sent from the held stance and running or ended within
        AIM_HOLD_S. Any other send (a walk, a steer, a care skill) released it."""
        a = self.last
        if a is None or not self.actions.history or self.actions.history[-1] is not a:
            return False
        if a.type == "aim":
            return not self.actions.done(a)
        if a.type != "attack" or not self._attack_held:
            return False
        return not self.actions.done(a) or (a.ended_wall is not None and self.clock() - a.ended_wall < AIM_HOLD_S)

    def _observe_kill(self):
        """Ruling P24-Q (zombies killed, the iteration's metric): the Fight's last attack or aim that ended with
        `targetDead` true in its result is a kill, read once: `kill` names its target for this observe (Survive logs
        it as the decision line's `kill`) and the World counts it (`World.note_kill`, `kills`)."""
        self.kill = None
        a = self.last
        if a is None or a.type not in SWING_TYPES or not self.actions.done(a) or a is self._kill_read:
            return
        self._kill_read = a
        if isinstance(a.result, dict) and a.result.get("targetDead") is True:
            zid = a.args.get("targetId")
            if self.world.note_kill(zid):
                self.kill = zid
            self.dead[zid] = self.clock() + UNREACHABLE_S   # the controller's ruling on concern 6 (Task 12 fix 1)
            if zid == self.target:
                self._unpin()

    def observe(self):
        self._observe_kill()
        self._observe_leg()
        t = self._target(pin=False)
        self._observe_stand(t)
        self._observe_seek(t)
        if t is None or t[2] <= FIGHT_REACH or (self.stance_at(t[2]) and not self.advance):
            self.out_of_reach_since = self.clock()   # P24-G 1: a stand's own clock is STAND_MAX_S
        a = self.last
        if a is None or a.type not in ("attack", "shove", "stomp") or not self.actions.done(a) or a is self._counted:
            return
        self._counted = a
        if a.type != "attack":
            self._observe_swing(a)
            return
        if a.state == "failed" and a.reason in STUCK_REASONS:   # the approach walk could not queue (Minor 3)
            self._mark_unreachable(a.args.get("targetId"))
            return
        if not isinstance(a.result, dict):
            return
        if a.result.get("attackStarted") is False:
            self.misses += 1
            if self.misses >= MISSES_TO_APPROACH:
                self.approach = True
                self.misses = 0
        else:
            self.misses = 0
            if a.state == "done" and a.result.get("attackStarted") is True:
                self._swing_landed_nothing(a.args.get("targetId"))

    def _observe_swing(self, a):
        """A shove's or a stomp's end (rulings P24-AH, P24-AL): one the Lua refused, failed (never `superseded`, this
        planner's own next send), timed out, or ended done with `attackStarted` false (the engine dropped it) leaves its
        target out of that skill for SWING_SKIP_S (a refused stomp's target takes the weapon's floor strike); a stomp
        that started counts in the no-progress streak as a swing does (`_swing_landed_nothing`)."""
        zid = a.args.get("targetId")
        res = a.result if isinstance(a.result, dict) else {}
        if a.state != "done" or res.get("attackStarted") is False:
            if not (a.state == "failed" and (a.reason == PREEMPTED or (a.type == "stomp" and a.reason == "stood"))):
                self.swing_refused[(a.type, zid)] = self.clock() + SWING_SKIP_S
            return
        if a.type == "stomp" and res.get("attackStarted") is True:
            self._swing_landed_nothing(zid)
        if a.type == "shove" and res.get("knockdown") is True:
            self.knocked[zid] = self.clock() + KNOCK_READ_S   # PZA/1.7.1: downed before the frame's onFloor reads it

    def _swing_ok(self, kind, zid):
        """The build announces `kind` (shove or stomp) and its last end at `zid` left it out no longer."""
        return self.world.can(kind) and self.swing_refused.get((kind, zid), -math.inf) <= self.clock()

    def _standing_near(self, r, exclude=()):
        """(id, zombie, dist) of the nearest standing zombie (not `on_floor`, not read dead) listed within `r` tiles of
        the player, its id not in `exclude`, else None: the engine's call takes a standing zombie within the weapon's
        MinRange for its target (#4372), so no shove or stomp of another goes then (P24-AH)."""
        dead, now = blocked(self.dead, self.clock()), self.clock()
        best = None
        for zid, z in self.world.zombies.items():
            if (zid in exclude or zid in dead or on_floor(z) or self.knocked.get(zid, -math.inf) > now
                    or z.get("x") is None or z.get("y") is None):
                continue
            d = zdist(self.world, z)
            if d <= r and (best is None or (d, repr(zid)) < (best[2], repr(best[0]))):
                best = (zid, z, d)
        return best

    def _downed(self):
        """(id, zombie, dist) of each downed zombie (`on_floor`) the Fight may target within FIGHT_REACH whose line is
        not read blocked, nearest first (ruling P24-AL: finished before the Fight turns to a standing one); a zombie a
        shove read knocked down within KNOCK_READ_S counts as downed (`knocked`)."""
        skip, now = self.blocked(), self.clock()
        out = []
        for zid, z in self.world.zombies.items():
            down = on_floor(z) or self.knocked.get(zid, -math.inf) > now
            if (not target_id_ok(zid) or zid in skip or not down or z.get("x") is None or z.get("y") is None
                    or (self.only is not None and zid not in self.only)):
                continue
            d = zdist(self.world, z)
            if d <= FIGHT_REACH and line_to(self.world, z) is not False:
                out.append((d, repr(zid), zid, z))
        return [(zid, z, d) for d, _, zid, z in sorted(out, key=lambda e: e[:2])]

    def _finish(self):
        """Ruling P24-AL (finish the fallen; #4372-#4374), with P24-AH's stomp: the nearest downed zombie within
        FIGHT_REACH takes, in order, the shove of a standing zombie at point blank first (POINT_BLANK_R, within the
        Lua's SHOVE_R: the engine would shove it anyway), else the `stomp` (the Lua walks to under 0.5 tiles; never
        with another standing zombie within STAND_MIN_R, the stomp's refusal), else the weapon's floor strike (an
        `attack` of the downed zombie, its damage times 5 or more: #4374) when the stomp is refused or not announced;
        `(command,)`, the command None in a hit reaction (the engine starts no swing: #4292); None with no downed
        zombie."""
        downed = self._downed()
        if not downed:
            return None
        zid, z, d = downed[0]
        self.why = {"target": self.target, "pinned": self.target is not None, "dist": d, "downed": zid}
        hit = hit_reaction(self.world)
        if hit is not None:
            self.why["hitReaction"] = hit
            return (None,)
        s = self._standing_near(POINT_BLANK_R, (zid,))
        if (s is not None and not self._shoved and target_id_ok(s[0]) and s[2] <= SHOVE_R
                and self._swing_ok("shove", s[0])):
            self.why.update({"shove": "first", "shoveTarget": s[0], "shoveDist": s[2]})
            return (Shove(s[0]),)
        if self._swing_ok("stomp", zid) and self._standing_near(STAND_MIN_R, (zid,)) is None:
            self.why["stomp"] = True
            return (Stomp(zid),)
        self.why["floor"] = True   # the stomp refused (or not announced): the weapon's floor strike
        self._held_before = False
        return (Attack(zid),)

    def _shove(self, zid, z, d):
        """The shove sent instead of the next swing at the standing target `zid` (`d` tiles off, within reach), else
        None (the build must announce `shove`; never with another standing zombie within STAND_MIN_R of the player
        than the one shoved):
        - ruling P24-AG: `arm_pain` at or above STRAIN_SOFT (the swing's damage divided by armPain / 10, #4370) and
          the target at point blank (POINT_BLANK_R): the shove, which strains the arms about a third less than a bat's
          swing and knocks down 35 + 2 x Strength in 100 (#4373), every time;
        - ruling P24-AH: in a standing fight (`standing`), a second standing zombie inside KEEP_R: the nearer of the
          two is shoved (within the Lua's SHOVE_R) before the next swing, once a swing (`_shoved`)."""
        if not self.world.can("shove"):
            return None
        pain = arm_pain(self.world)
        if (pain is not None and pain >= STRAIN_SOFT and d <= POINT_BLANK_R and self._swing_ok("shove", zid)
                and self._standing_near(STAND_MIN_R, (zid,)) is None):
            self.why.update({"shove": "strain", "strain": pain})
            return Shove(zid)
        if not self.standing() or self._shoved:
            return None
        second = self._standing_near(KEEP_R, (zid,))
        if second is None:
            return None
        sid, _, sd = min(((zid, z, d), second), key=lambda p: (p[2], repr(p[0])))
        if (not target_id_ok(sid) or sd > SHOVE_R or not self._swing_ok("shove", sid)
                or self._standing_near(STAND_MIN_R, (sid,)) is not None):
            return None
        self.why.update({"shove": "second", "shoveTarget": sid, "shoveDist": sd, "second": second[0]})
        return Shove(sid)

    def fight_s(self):
        """Seconds the target has been out of reach (the stall clock)."""
        return self.clock() - self.out_of_reach_since

    def target_dist(self):
        """Tiles to the target the stall clock follows (the pinned one while it holds, else the nearest reachable),
        None with no target: Survive's stall guard reads the same zombie as the clock."""
        t = self._target(pin=False)
        return None if t is None else t[2]

    @property
    def stalled(self):
        return self.fight_s() > FIGHT_MAX_S

    def choose(self):
        self._marked_now = set()
        cmd = self._choose()
        self._marked_now = set()
        for key, ids in (("unreachable", self.marked()), ("dead", blocked(self.dead, self.clock()))):
            if ids:
                self.why[key] = sorted(ids, key=str)
        return cmd

    def _repin_point_blank(self):
        """Survival 4 fix round 1, R4 (E4: the corner's pin stayed on 19032 while 19035 at 0.48 tiles dealt the first
        wound and was never swung at): a cornered Fight (`point_blank`) re-pins, at each choose, to the nearest zombie
        within POINT_BLANK_R that it may target, when that is not its pin. Its hysteresis (ruling P24-A (d), the close
        review's I2: F1's pin alternated 15921, 15917, 15921 about eight times between gameMin 637 and 644, both at
        0.49 to 1.03 tiles, each new id restarting the no-progress streak), as margined at fix 1 (2) (every one of
        F1's re-pins came with the pin at 1.03 to 1.30 tiles): only when the pin reads no position, stands beyond
        CORNERED_R, or stands at least REPIN_MARGIN farther than the new zombie. Fix 2, I2a (F1's 578: the held pin
        drifted to 2.73 tiles and the Fight walked at it while 15921 hit from 1.19): a pin beyond CORNERED_R (or with
        no position) gives way to the nearest zombie `in_reach` within CORNERED_R; with none, `_choose` sends no walk
        (`out_of_reach`, and Survive ends the corner)."""
        if not self.point_blank:
            return
        skip = self.blocked()
        if self.only is not None:
            skip = skip | {zid for zid in self.world.zombies if zid not in self.only}
        pin = self.world.zombies.get(self.target) if self.target is not None else None
        if pin is None or pin.get("x") is None or pin.get("y") is None or zdist(self.world, pin) > CORNERED_R:
            reach = [(zid, z) for zid, z in self.world.zombies.items() if target_id_ok(zid) and zid not in skip
                     and zid != self.target and in_reach(self.world, z, CORNERED_R)]
            if reach:   # P24-A fix 2, I2a: a drifted pin gives way to the nearest in reach
                self.target = min(reach, key=lambda p: (zdist(self.world, p[1]), p[0]))[0]
                self.repositioned = False
            return
        nz = self.world.nearest_zombie(exclude=skip)
        if nz is None or nz[0] == self.target:
            return
        d = zdist(self.world, nz[1])
        if d > POINT_BLANK_R:
            return
        if d > zdist(self.world, pin) - REPIN_MARGIN:   # the pin within CORNERED_R: re-pinned only past the margin
            return
        self.target, self.repositioned = nz[0], False

    def _choose(self):
        self._seek_send, self._walk_kind = False, None
        self._repin_point_blank()
        self._pull_pin()
        switch = self._seek_switch(self._pinned()) if self.seek and self.target is not None else None
        if switch is None and self.advance and self.target is not None:
            switch = self._advance_switch(self._pinned())   # Task 18 fix 2: the advance gives way to a closing zombie
            if switch is not None:
                self.advance = False
        if switch is not None:   # Task 18 fix 1, the blocker: the seek closes on the nearest
            self.target, self.repositioned = switch[0], False
        t = self._target(pin=True)
        if t is None:
            self.why = {"target": None, "pinned": False}
            return None
        zid, z, d = t
        if self.point_blank and d > CORNERED_R:   # P24-A fix 2, I2a: a cornered Fight never walks to a drifted pin
            self.why = {"target": zid, "pinned": True, "dist": d, "out_of_reach": True}
            return None
        fin = self._finish()   # P24-AL: a downed zombie within reach first
        if fin is not None:
            return fin[0]
        if d <= POINT_BLANK_R:
            self.approach = False   # P24-A (e), the close review's I3 (F1's walkTo at 0.49 tiles): never at point blank
        blank = self.point_blank and d <= POINT_BLANK_R   # P23-AJ fix 1: in reach whatever the map's line says
        line = self._line(z) if d <= FIGHT_REACH and not blank else None
        self.why = {"target": zid, "pinned": True, "dist": d, "approach": self.approach, "line": line,
                    "reposition": None}
        if switch is not None and zid == switch[0]:
            self.why["seek_switch"] = True
        if line is False:
            sq = None if self.repositioned else self._reposition(z)
            if sq is None:   # a second blocked read, or no clear square: the target is unreachable, the next tried
                self._mark_unreachable(zid)
                read = self.why
                cmd = self._choose()
                self.why = dict(read if self.why["target"] is None else self.why, marked=zid)
                return cmd
            self.repositioned = True
            self.why["reposition"] = list(sq)
            return WalkTo(*centre(sq), "run")
        if self.stance_at(d) and (d > FIGHT_REACH or not self.in_stance()) and not (self.approach and d <= FIGHT_REACH):
            if self.ride is not None and d > FIGHT_REACH:   # P24-U: an aim would end the riding bandage; held off
                self.why["ride"] = self.ride.aid           # until it ends, a target within reach excepted
                return None
            return self._stance_leg(zid, z, d)   # P24-N: every leg of a standing fight is an aim, the first one too
        if self.approach or d > FIGHT_REACH:
            self._seek_send = self.seeking(t) and not self.approach   # P24-X: its failure marks the target
            if self._seek_send and d > AIM_R:           # beyond the aim's range the seek walks, never runs
                self.why.update({"seek": True, "leg": "walk"})
                self._walk_kind = "far" if self.standing() else None   # fix 1: it gives way within AIM_R
                return WalkTo(*centre((z["x"], z["y"])), "walk")
            return WalkTo(*centre((z["x"], z["y"])), "run")
        hit = hit_reaction(self.world)
        if hit is not None:   # P24-A (i): the engine starts no swing in a hit reaction (#4292, #4293): sent on its end
            self.why["hitReaction"] = hit
            return None
        shove = self._shove(zid, z, d)   # P24-AG, P24-AH: the shove before (or for) the swing
        if shove is not None:
            return shove
        self._held_before = self.stance_at(d) and self.in_stance()
        if self.stance_at(d):
            self.why["stance"] = True   # the swing from the stance (Task 9's hand-over keeps it)
        return Attack(zid)   # nearest_zombie yields int ids only (M7)

    def _stance_leg(self, zid, z, d, kind=None):
        """One stance leg (rulings P24-G 1 and P24-N): `aim` facing the target for AIM_LEG_S, walking (the stance
        never runs) one of
        - `enter` (0, 0): the target within FIGHT_REACH with the stance not held (`in_stance`): the stance is taken
          before the swing, which the next choose sends from it;
        - `toward`: the advance (`advance`, after STAND_MAX_S without progress), the unit vector to the target while
          its STEER_PROBE line (to the target at most) is clear; with that line blocked the approach walk closes on
          it instead (the path follower walks round the wall), the one walk of a standing fight, at a walk (Task 12
          fix 1, the review's minor 3: ruling P24-N 1 closes "in the stance ... not to a run");
        - `back`: the target inside KEEP_R: `away_vector` of the held threats (`threats`, else the target) turned
          by STEER_TURNS to the first heading `clear_heading` passes (never into a wall or over a fence), else
          standing: a wall behind is never stepped into;
        - `pull` (ruling P24-AN): a lone chaser beyond PULL_R pulled from the group (`pulling`): the unit vector from
          the group's centroid (`pull_centroid`) to the player, turned by STEER_TURNS to the first heading
          `clear_heading` passes, else standing; the chaser faced while it follows, the group left behind;
        - `stand` (0, 0): the target beyond KEEP_R, faced while it comes.
        `kind` names the leg instead of the target's distance (P24-AP's wounded backpedal within reach)."""
        t = (zid, z, d)
        v, kind = None, kind or stance_leg_kind(d, self.advance, self.seeking(t), self.pulling(t))
        if kind in ("toward", "seek"):
            mx, my = me_xy(self.world)
            u = ((z["x"] - mx) / d, (z["y"] - my) / d)
            if not clear_heading(self.world, u, min(STEER_PROBE, d), self.trans):
                self.why.update({"stance": True, "leg": "walk", "stand_s": self.stand_s()})
                self.why["advance" if kind == "toward" else "seek"] = True
                self._seek_send, self._walk_kind = kind == "seek", "seek" if kind == "seek" else "advance"   # fix 1
                return WalkTo(*centre((z["x"], z["y"])), "walk")
            v = u
        elif kind == "back":
            ts = [q for q in (self.threats or [z]) if q.get("x") is not None and q.get("y") is not None]
            v = self._clear_turn(away_vector(self.world, [(q["x"], q["y"]) for q in ts]))
        elif kind == "pull":
            c = self.pull_centroid(t)
            v = self._clear_turn(away_vector(self.world, [c]))
            self.why["pull"] = [c[0], c[1]]
        vx, vy = v if v is not None else (0.0, 0.0)
        self.why.update({"stance": True, "leg": kind, "back": [vx, vy] if kind == "back" and v is not None else None,
                         "stand_s": self.stand_s()})
        if self.advance:
            self.why["advance"] = True
        if kind == "seek":
            self.why["seek"] = True
        return Aim(vx, vy, AIM_LEG_S, targetId=zid)

    def _clear_turn(self, a):
        """Heading `a` (a unit vector, or None) turned by STEER_TURNS to the first heading `clear_heading` passes
        (never into a wall or over a fence), else None: the backpedal's and the pull's step."""
        if a is None:
            return None
        return next((_rotate(a, t) for t in STEER_TURNS if clear_heading(self.world, _rotate(a, t), STEER_PROBE,
                                                                         self.trans)), None)

    def sent(self, cmd, action):
        if cmd.TYPE == "aim":
            self._leg = self.why.get("leg")
            if self._leg == "pull":
                self._pulled = cmd.targetId   # P24-AN: kept to DISENGAGE_R from here (`_pull_waits`)
        elif cmd.TYPE == "walkTo":
            self.approach = False
            self._seek_walk = (action, self.target) if self._seek_send else None
            self._stance_walk = (action, self.target, self._walk_kind) if self._walk_kind else None
        elif cmd.TYPE == "shove":
            self._shoved = True
        elif cmd.TYPE in ("attack", "stomp"):
            self._shoved = False
            self._attack_held = self._held_before if cmd.TYPE == "attack" else False
            if cmd.targetId != self._streak_id:   # a new target: its streak starts here
                self._streak_id, self._streak_h, self.no_progress = cmd.targetId, self._target_health(cmd.targetId), 0


def _night():
    """`planner.night`, imported at the call: night imports this module at its top, so a top-level import here would
    be circular. The flee's shelter runs night's own steps (`shelter_plan`, `shelter_step`, `shelter_ended`)."""
    from agent.base.planner import night
    return night


def _rotate(v, deg):
    c, s = math.cos(math.radians(deg)), math.sin(math.radians(deg))
    return v[0] * c - v[1] * s, v[0] * s + v[1] * c


def _square_of(world, z):
    """The map record of zombie `z`'s floored square on the player's floor, else None."""
    return world.map.get((int(math.floor(z["x"])), int(math.floor(z["y"])), me_floor(world)))


def in_building(world, z, building):
    """Zombie `z` stands on a square of `building` (a room square or its door square, a door kept on an outdoor
    square read by `World.door_building`: survival 3 fix round 1, R2): Survive's door fight reads it."""
    s = _square_of(world, z)
    if s is None or building is None:
        return False
    if s.get("room") is not None:
        return s.get("building") == building
    sq = (int(math.floor(z["x"])), int(math.floor(z["y"])), me_floor(world))
    return s.get("door") is not None and world.door_building(sq) == building


def in_corridor(me, end, z):
    """Zombie `z` lies ahead of the player within CORRIDOR_R of the straight segment from `me` to `end` (past `end`,
    within CORRIDOR_R of it): the flee would run through it (P23-AG fix round 1, I1)."""
    ux, uy = end[0] - me[0], end[1] - me[1]
    length = math.hypot(ux, uy)
    zx, zy = z["x"] - me[0], z["y"] - me[1]
    if length == 0.0:
        return math.hypot(zx, zy) < CORRIDOR_R
    ux, uy = ux / length, uy / length
    t = zx * ux + zy * uy
    if t <= 0.0:
        return False
    if t > length:
        return math.hypot(z["x"] - end[0], z["y"] - end[1]) < CORRIDOR_R
    return abs(zx * uy - zy * ux) < CORRIDOR_R


def on_room(world):
    """The player's square is a room square (the night's `inside()` read off the World alone)."""
    return (world.map.get(_night().player_square(world)) or {}).get("room") is not None


def exit_plan(world, threats, refused=(), trans=True):
    """The way out of the building the player stands in (ruling P23-AJ 3 as amended, and its fix round 1), else
    None: standing on a room square of a building, of its `night.exits` on the player's floor (an opening, or a
    closed exterior door to open first) whose outside square is not in `refused`, whose outside square's centre is no
    nearer any threat than the player is to it (the shelter pick's rule), and whose straight line from the player to
    that centre passes no threat within EXIT_CLEAR_R (fix round 1: E2's offline check at gameMin 585 chose an opening
    across the building past the zombie at 0.48 tiles), and whose square beyond is open (`_beyond`; the review's I1:
    a walk to the outside square itself ends `done` on the room square and is refused), the nearest to the player,
    ties by that square; `{building, inner, outer, door, target, step, opened}`, `target` the square the walk goes to,
    `step` "walk" (the review's I2: the jar's path follower opens a closed door on a player's path,
    `PathFindBehavior2.checkDoorHoppableWindow`, a review reading; the open is the fallback), `opened` False. `trans`:
    `_beyond`'s (ruling P24-AS)."""
    N = _night()
    s = world.map.get(N.player_square(world)) or {}
    b = s.get("building")
    if s.get("room") is None or b is None:
        return None
    ts = [z for z in threats if z.get("x") is not None and z.get("y") is not None]
    me = me_xy(world)
    marked = world.marked_doors()   # Task 18 fix 1, major 4: a marked door stays a way out, ranked after the others
    best = None
    for e in N.exits(world, b, me_floor(world)):
        if e["outer"] in refused:
            continue
        c = centre(e["outer"])
        if any(math.hypot(z["x"] - c[0], z["y"] - c[1]) < zdist(world, z)
               or _in_tube(me, c, (z["x"], z["y"]), EXIT_CLEAR_R) for z in ts):
            continue
        if _beyond(world, e["inner"], e["outer"], trans) is None:
            continue
        rank = (e["door"] in marked, math.hypot(c[0] - me[0], c[1] - me[1]), e["outer"], e["inner"])
        if best is None or rank < best[0]:
            best = (rank, e)
    if best is None:
        return None
    e = best[1]
    return dict(e, building=b, target=_beyond(world, e["inner"], e["outer"], trans), step="walk", opened=False)


def _in_tube(a, b, p, r):
    """Point `p` lies within `r` of the end `b`, or ahead of `a` (its projection on the segment from `a` to `b` past
    `a`) within `r` of the segment: the exit's own square and its straight line, never the player's back (P24-A fix 1
    (3), the tube of P23-AP 3's cut)."""
    if math.hypot(p[0] - b[0], p[1] - b[1]) < r:
        return True
    ux, uy = b[0] - a[0], b[1] - a[1]
    if (p[0] - a[0]) * ux + (p[1] - a[1]) * uy <= 0.0:
        return False
    return _seg_dist(a, b, p) < r


def _seg_dist(a, b, p):
    """Tiles from point `p` to the segment from `a` to `b`."""
    ux, uy = b[0] - a[0], b[1] - a[1]
    n2 = ux * ux + uy * uy
    t = 0.0 if n2 == 0.0 else max(0.0, min(1.0, ((p[0] - a[0]) * ux + (p[1] - a[1]) * uy) / n2))
    return math.hypot(p[0] - a[0] - t * ux, p[1] - a[1] - t * uy)


def _beyond(world, inner, outer, trans=True):
    """The square the exit walks to: one more square on from `outer` away from `inner` when the map holds it open (not
    solid, no room, the step to it not blocked), else None (the exit is skipped: fix round 1, the review's I1). A walk
    ends `done` within the Lua's DONE_R (1.0) of its target, so a walk to the outside square's own centre may end on
    the room square beside it (rule 5's lesson); from the square beyond it ends at least a tile from the room
    square's centre. With `trans` (ruling P24-AS) a `solidTrans` square beyond is no walk's end either."""
    sq = (2 * outer[0] - inner[0], 2 * outer[1] - inner[1], outer[2])
    s = world.map.get(sq)
    if (s is None or s.get("solid") or (trans and s.get("solidTrans")) or s.get("room") is not None
            or world.blocked(outer, sq)):
        return None
    return sq


def adoptable(world):
    """The building the player stands in has an exterior door on the player's floor (`Flee._adopt` can adopt it), a
    marked one included (read from inside: Task 18 fix 1, the review's major 4)."""
    N = _night()
    s = world.map.get(N.player_square(world)) or {}
    b = s.get("building")
    return (s.get("room") is not None and b is not None
            and bool(N.exterior_doors(world, b, me_floor(world), marked=True)))


class Flee(Policy):
    def __init__(self, world, actions, clock=time.time, threats=None, shunned=None):
        super().__init__(world, actions, clock)
        self.threats = threats   # the zombies to flee; None: every zombie the World holds
        self.shunned = {} if shunned is None else shunned   # building -> world minutes shunned at (Night's store)
        self.plan = None         # the shelter plan this episode runs (night.shelter_plan kept to one door), else None
        self.picked = False      # a shelter plan was chosen this episode (once dropped, the episode only steers)
        self.ended = None        # the outcome of the last shelter step end read (night.shelter_ended)
        self.exit = None         # the way out this episode runs (`exit_plan`, P23-AJ 3), else None
        self.refused = set()     # the outside squares of exits that failed this episode
        self.left = set()        # the buildings this episode walked out of (never its shelter)
        self.hold_ok = True      # Survive clears it while a held threat breaks the hold (P23-AJ 1)
        self.adopted = False     # the building stood in was adopted this episode (fix round 1: once)
        self.steer_now = False   # Survive sets it: a group at melee range, the last leg not stuck (P23-AM 4)
        self._chosen = None      # "step", "close" or "exit": what the last choose returned, until it is sent
        self._step = None        # the last shelter step's Action
        self._step_anchor = None  # (wall, (x, y)) of the shelter step's send or its walk's last STUCK_MOVE (P23-AM 2)
        self._read = None        # the last shelter step whose end observe() read
        self._close = None       # the last re-sent close's Action (the sheltered re-close)
        self._exit_a = None      # the last exit step's Action
        self._exit_read = None   # the last exit step whose end observe() read
        self._exit_anchor = None  # (wall, (x, y)) of the exit step's send or its walk's last STUCK_MOVE (G2)
        self._dropped = None     # an exit or shelter walk dropped while still current (G2, P23-AM 2): not waited on
        self._leg = None         # (Action, (x, y) at its send, heading, ids ahead at its aim) of the last steer leg
        self._aimed = frozenset()  # the held ids `_ahead` of the heading the last `_steer` chose (P23-AP 3)
        self._cut = None         # the ids newly ahead that cut the running leg (P23-AP 3), till a steer logs them
        self._leg_anchor = None  # (wall, (x, y)) of the running leg's send or its last STUCK_MOVE (fix round 1, R1)
        self._leg_still = 0.0    # wall seconds the running leg has left the player within STUCK_MOVE of that anchor
        self.skip_heading = None  # Survive sets it: a stuck heading from before this Flee (a `stuck` corner's leg),
                                  # skipped by the first leg's turn as F4 skips a stuck leg's (P24-A fix 2, G2)
        self.stand_ok = False    # Survive sets it each tick: a shelter picked now is a doorway stand (ruling P24-AO,
                                 # `planner.doorway`)

    @property
    def sheltered(self):
        """The episode's shelter plan read done (its close ended) and is kept."""
        return self.plan is not None and self.plan["step"] == "done"

    def running_shelter(self):
        """A shelter plan is running and its close has not ended (Survive's inside hold waits for it)."""
        return self.plan is not None and self.plan["step"] != "done"

    def standing_door(self):
        """The doorway stand runs (ruling P24-AO): the plan's enter ended where its close would go (`stand`)."""
        return self.plan is not None and self.plan["step"] == "stand"

    def closing_stand(self):
        """A doorway stand left (Survive's `_doorway`) and its close not yet ended: the stand's own shelter step."""
        return self.plan is not None and bool(self.plan.get("stood")) and self.plan["step"] == "close"

    def running_exit(self):
        """A way out is running (Survive's inside hold waits for it, as for the shelter steps)."""
        return self.exit is not None

    def door(self):
        """The plan's one door square, else None."""
        return self.plan["doors"][0] if self.plan is not None else None

    def _threats(self):
        ts = self.threats if self.threats is not None else list(self.world.zombies.values())
        return [z for z in ts if z.get("x") is not None and z.get("y") is not None]

    def _known(self):
        return [z for z in self.world.zombies.values() if z.get("x") is not None and z.get("y") is not None]

    def _drop(self, shun):
        """Drop the plan: the steer for the rest of the episode; the building shunned only for a shun reason (M1)."""
        if shun:
            self.shunned[self.plan["building"]] = self.world.world_minutes()
        self.plan = None

    def observe(self):
        self._observe_exit()
        if self._leg is not None and running(self.actions, self._leg[0]):
            self._leg_anchor, self._leg_still = self._still_for(self._leg_anchor)
            self._cut_leg()
        a = self._step
        if a is None or a is self._read or self.plan is None:
            return
        if not self.actions.done(a):
            if self._step_stalled(a):
                self._dropped, self._read, self.ended = a, a, "stalled"
                self._drop(False)   # this episode only (`picked` stays): the steer follows at once
            return
        self._read = a
        self.ended = _night().shelter_ended(self.plan, a)
        if self.ended not in ("advance", "resend", "passed"):
            self._drop(a.state == "failed" and a.reason in _night().SHUN_REASONS)
        elif self.plan.get("stand") and self.plan["step"] == "close":   # P24-AO: the enter ended, the close is the
            self.plan.update(step="stand", stood=True, quiet=self.clock())   # stand's (`planner.doorway`)

    def _ids(self, zs):
        """The World's ids of the zombie records `zs` (this tick's dicts), sorted."""
        ids = {id(z): zid for zid, z in self.world.zombies.items()}
        return sorted((ids.get(id(z)) for z in zs), key=repr)

    def _cut_leg(self):
        """Ruling P23-AP 3 (E4's line 440: a leg aimed west before 19032 and 19035 were listed ran 8.92 tiles into
        them): the running steer leg's heading re-read against this tick's held threats beyond NEAR_R (`_ahead`: the
        cone and the tube the aim refuses); one ahead that was not ahead at its aim cuts it (`_dropped`, so the next
        choose re-aims by the turn rules and the new leg supersedes it), logged as the next steer's `cut`. Fix round 1
        (the review's G1): the World's current records by id, the held ones (within DISENGAGE_R) beyond NEAR_R, never
        the caller's list, which may be the last tick's records, every one replaced since by its frame (an id read None
        is never new: e07a52cb cut a fallback leg on every tick, so R1's stuck read never came)."""
        leg = self._leg
        if leg[0] is self._dropped:
            return
        far = [(zid, z) for zid, z in self.world.zombies.items() if target_id_ok(zid) and z.get("x") is not None
               and z.get("y") is not None and NEAR_R < zdist(self.world, z) <= DISENGAGE_R]
        ahead = {id(z) for z in self._ahead(leg[2], [z for _, z in far])}
        new = sorted((zid for zid, z in far if id(z) in ahead and zid not in leg[3]), key=repr)
        if new:
            self._dropped, self._cut = leg[0], new

    def _still_for(self, anchor):
        """`(anchor, seconds)`: the anchor `(wall, (x, y))` moved on to now when the player has moved STUCK_MOVE or
        more from it, and the wall seconds the player has stood within STUCK_MOVE of it (G2, P23-AM 2)."""
        now, pos = self.clock(), me_xy(self.world)
        if math.hypot(pos[0] - anchor[1][0], pos[1] - anchor[1][1]) >= STUCK_MOVE:
            return (now, pos), 0.0
        return anchor, now - anchor[0]

    def _step_stalled(self, a):
        """Ruling P23-AM 2 (E3: the enter walk stood 14.5 s while the group closed from 7.9 tiles to 0.48): a shelter
        step still current whose walk has left the player within STUCK_MOVE for WALK_STALL_S wall seconds while a
        held threat is within DANGER_R. An `open` or `close` walks only while the player stands more than one square
        (Chebyshev) from the door (the Lua's interact `approach`); at the door its anchor follows the player, the
        door's own action being no walk. With no held threat within DANGER_R the step waits the Lua's stuck time."""
        if not running(self.actions, a):
            return False
        if a.type == "interact":
            sq, door = _night().player_square(self.world), self.door()
            if sq is None or max(abs(sq[0] - door[0]), abs(sq[1] - door[1])) <= 1:
                self._step_anchor = (self.clock(), me_xy(self.world))
                return False
        self._step_anchor, still = self._still_for(self._step_anchor)
        return still >= WALK_STALL_S and any(zdist(self.world, z) <= DANGER_R for z in self._threats())

    def busy(self):
        """As `Policy.busy`, except for an exit or shelter walk dropped while still current (G2, P23-AM 2): the next
        choose answers."""
        return super().busy() and self.last is not self._dropped

    def give_way(self):
        """P23-AM 4 with the coordinator's amendment 6 (E3: the enter walk ran on with three zombies at half a tile):
        Survive's group steer drops a running shelter or exit step (`_dropped`; the plan for the episode, `ended`
        `pre-empted`; the exit refused), so the steer goes at once; a running steer leg, or anything else, is kept. On
        a room square a running exit step is kept (ruling P24-A (f): inside, the group's answer is the exit; its walk
        is no longer re-sent at a sprint, P24-O)."""
        if not self.busy() or self.last.type not in ("walkTo", "interact"):
            return
        if self.last is self._exit_a and self.exit is not None and on_room(self.world):
            return
        self._dropped = self.last
        if self.last is self._step and self.plan is not None:
            self._read, self.ended = self._step, "pre-empted"
            self._drop(False)
        elif self.last is self._exit_a and self.exit is not None:
            self._exit_read = self._exit_a
            self._refuse_exit()

    def _observe_exit(self):
        """An exit step's end, and a running walk's progress (fix round 1, the review's G2): a walk that has left the
        player within STUCK_MOVE of where it last moved for WALK_STALL_S wall seconds is dropped while still current
        (`_dropped`) and read as failed. An open `done` goes back to the walk (`opened`); a superseded step is sent
        again; a walk `done` with the frame reading outside waits for the choose to read it out (`_exit_step`); a
        walk that failed, stalled or ended `done` with the frame still inside goes to the open when its way out is a
        closed door not yet opened (I2), else refuses that exit for the episode, as does a failed open (P23-AJ 3: the
        next choose takes the next way out, else the adoption or the trapped hold)."""
        a = self._exit_a
        if a is None or a is self._exit_read or self.exit is None:
            return
        if not self.actions.done(a):
            if self.exit["step"] != "walk" or not running(self.actions, a):
                return
            self._exit_anchor, still = self._still_for(self._exit_anchor)
            if still < WALK_STALL_S:
                return
            self._dropped = a
        self._exit_read = a
        if a.state == "failed" and a.reason == PREEMPTED:
            return
        e = self.exit
        if e["step"] == "open":
            if a.state == "done":
                e["step"], e["opened"] = "walk", True
            else:
                self._refuse_exit()
        elif a is self._dropped or a.state != "done" or on_room(self.world):
            if e["door"] is not None and not e["opened"]:
                e["step"] = "open"
            else:
                self._refuse_exit()

    def _refuse_exit(self):
        self.refused.add(self.exit["outer"])
        self.exit = None

    def _pick(self, ts):
        """The shelter plan to run (ruling P23-AG and its fix rounds), else None: never from a room square (P23-AJ
        3: inside, the flee walks out first, `exit_plan`); else of the buildings not shunned (`night.shunned_now`)
        and not walked out of this episode (`left`) with no known zombie on one of their squares (M4), each exterior
        door the map reads neither locked nor barricaded whose `night.approach_square` lies within SHELTER_FLEE_R of
        the player, no nearer any held threat than the player is to it, with no known zombie in its corridor
        (`in_corridor`, I1 and M3); the nearest such square first, ties by the building, then the door; the plan
        `night.shelter_plan(..., door=)` kept to that door."""
        N = _night()
        if on_room(self.world):
            return None
        mx, my = me_xy(self.world)
        known = self._known()
        skip = N.shunned_now(self.shunned, self.world.world_minutes()) | self.left
        best = None
        for b in self.world.interiors():
            if b is None or b in skip or any(in_building(self.world, z, b) for z in known):
                continue
            plan = N.shelter_plan(self.world, b)
            for door in plan["doors"] if plan is not None else ():
                rec = self.world.map[door].get("door") or {}
                sq = None if rec.get("locked") or rec.get("barricaded") else N.approach_square(self.world, door)
                if sq is None:
                    continue
                c = (sq[0] + 0.5, sq[1] + 0.5)
                d = math.hypot(c[0] - mx, c[1] - my)
                if d > SHELTER_FLEE_R or any(in_corridor((mx, my), c, z) for z in known):
                    continue
                if any(math.hypot(z["x"] - c[0], z["y"] - c[1]) < zdist(self.world, z) for z in ts):
                    continue
                rank = (d, repr(b), door)
                if best is None or rank < best[0]:
                    best = (rank, b, door)
        return None if best is None else N.shelter_plan(self.world, best[1], door=best[2])

    def _shelter(self, ts):
        """The plan's next step (its walks at FLEE_GAIT); once done inside, a hold while every threat reads
        line-blocked, or while the door reads closed and no threat's line reads clear (an unknown line holds: fix
        round 2, concern 2); else one re-sent close of a door that reads open (again after each close that ended
        done), unless a known zombie stands within DOOR_CLEAR_R of the door (concern 4) or the player's square is no
        nearer the door square than every known zombie (fix round 3, F2: the Lua's close walks the player to the door,
        so never toward a zombie nearer it); else the plan dropped (I2). None with the plan dropped: the steer
        follows."""
        N = _night()
        b = self.plan["building"]
        if self.plan["step"] == "stand":   # P24-AO: the stand is Survive's Doorway fight; the Flee holds its plan
            self.why = {"shelter": b, "step": "stand"}
            return None
        cmd, step = N.shelter_step(self.world, self.plan)
        if step == "shun":
            self._drop(True)
            return None
        if step != "done":
            self._chosen = "step"
            self.why = {"shelter": b, "step": step, "ended": self.ended}
            return cmd if cmd.TYPE != "walkTo" else WalkTo(cmd.x, cmd.y, FLEE_GAIT)
        if not on_room(self.world):
            self._drop(False)   # pushed out after the close: no shelter this episode
            return None
        door = self.door()
        rec = (self.world.map.get(door) or {}).get("door")
        if self.hold_ok and self.shelter_holds(ts):
            self.why = {"shelter": b, "step": "done"}
            return None
        failed = self._close is not None and self.actions.done(self._close) and self._close.state != "done"
        sq = N.player_square(self.world)
        mine = math.hypot(sq[0] - door[0], sq[1] - door[1])   # square to square, as each zombie's below
        guarded = any(math.hypot(z["x"] - door[0] - 0.5, z["y"] - door[1] - 0.5) < DOOR_CLEAR_R
                      or math.hypot(math.floor(z["x"]) - door[0], math.floor(z["y"]) - door[1]) <= mine
                      for z in self._known())
        if rec is not None and rec.get("open") and not failed and not guarded:
            self._chosen = "close"
            self.why = {"shelter": b, "step": "reclose"}
            return Interact(door[0], door[1], "close")
        self._drop(False)
        return None

    def shelter_holds(self, ts):
        """The sheltered hold's reading of the lines: every threat line-blocked (`line_to` False), or the plan's door
        read closed and no threat's line read clear (an unknown line holds: fix round 2, concern 2)."""
        rec = (self.world.map.get(self.door()) or {}).get("door")
        lines = [line_to(self.world, z) for z in ts]
        closed = rec is not None and not rec.get("open")
        return all(ln is False for ln in lines) or (closed and all(ln is not True for ln in lines))

    def _exit_step(self):
        """The running exit's next command (P23-AJ 3), else None with the exit ended: outside (the frame reads no
        room square) the building is left and the steer follows; else the walk to the centre of the exit's `target`
        (`_beyond`) at FLEE_GAIT, or, after that walk failed at a closed door, its open (`Interact`, fix round 1 I2)."""
        e = self.exit
        if not on_room(self.world):
            self.left.add(e["building"])
            self.exit = None
            return None
        if e["step"] == "open" and ((self.world.map.get(e["door"]) or {}).get("door") or {}).get("open"):
            e["step"], e["opened"] = "walk", True
        self._chosen = "exit"
        self.why = {"exit": e["building"], "outer": list(e["outer"]), "door": list(e["door"]) if e["door"] else None,
                    "step": e["step"], "shelter": None, "refused": sorted(map(list, self.refused))}
        if e["step"] == "open":
            return Interact(e["door"][0], e["door"][1], "open")
        return WalkTo(*centre(e["target"]), FLEE_GAIT)   # P24-A (f)'s group exit, at a run since P24-O

    def _adopt(self, ts):
        """Fix round 1 (concern 1): the building stood in, every way out refused, adopted as sheltered: its plan kept
        to its open exterior door nearest the threats, else its exterior door nearest them (iteration 1's F1), read
        done, so the sheltered hold, the re-close guard and Survive's door fight apply; None with no exterior door on
        this floor (E2's building 3: its doors all broken)."""
        N = _night()
        b = (self.world.map.get(N.player_square(self.world)) or {}).get("building")
        doors = N.exterior_doors(self.world, b, me_floor(self.world), marked=True) if b is not None else []
        if not doors:
            return None
        marked = self.world.marked_doors()   # Task 18 fix 1, major 4: kept from inside, ranked after the others

        def rank(d):
            is_open = bool(((self.world.map.get(d) or {}).get("door") or {}).get("open"))
            return d in marked, not is_open, min(math.hypot(z["x"] - d[0] - 0.5, z["y"] - d[1] - 0.5) for z in ts), d
        return N.shelter_plan(self.world, b, door=min(doors, key=rank), step="done", marked=True)

    def choose(self):
        """The running exit; else the shelter (picked at each re-aim until one is chosen: fix round 2, T1, and never
        from a room square); else, on a room square, a new exit (`exit_plan`, P23-AJ 3), else, once an episode, the
        building adopted (`_adopt`, fix round 1), else the trapped hold (no command, `why.trapped`: on a room square
        the flee never steers, fix round 1: steering inside killed E2); else the steer. With `steer_now` (P23-AM 4 and
        AP 2: Survive's group, `_group`, the last leg not stuck) the steer goes first off a room square (the next leg
        that ends stuck is Survive's corner); on a room square (ruling P24-A (f), the close review's I4: the group
        steer ran inside a room with a way out, E2's death mode) the steer is never sent: the running exit, else a new
        one, walked at a run (P24-O), else the adoption, else the trapped hold."""
        self._chosen = None
        ts = self._threats()
        if not ts:
            self.why = {"centroid": None, "shelter": None}
            return None
        if self.steer_now and not on_room(self.world):
            return self._steer(ts)
        if self.exit is not None:
            cmd = self._exit_step()
            if cmd is not None:
                return cmd
        if not self.picked:
            self.plan = self._pick(ts)
            self.picked = self.plan is not None
            if self.plan is not None and self.stand_ok:   # P24-AO: the door taken for the doorway stand
                self.plan.update(stand=True, way=self.world.door_way(self.door()))
        if self.plan is not None:
            cmd = self._shelter(ts)
            if cmd is not None or self.plan is not None:
                return cmd
        if on_room(self.world):
            self.exit = exit_plan(self.world, ts, self.refused, self.trans)
            if self.exit is not None:
                return self._exit_step()
            if not self.adopted:
                self.adopted = True
                self.plan = self._adopt(ts)
                if self.plan is not None:
                    cmd = self._shelter(ts)
                    if cmd is not None or self.plan is not None:
                        return cmd
            self.why = {"trapped": (self.world.map.get(_night().player_square(self.world)) or {}).get("building"),
                        "shelter": None, "refused": sorted(map(list, self.refused))}
            if self._dropped is not None and self.actions.current is self._dropped:
                return Stop()   # the dropped walk is still running: stand (G2)
            return None
        return self._steer(ts)

    def _leg_moved(self):
        """Tiles the player stands from the last steer leg's start once that leg ended, else None."""
        if self._leg is None or not self.actions.done(self._leg[0]):
            return None
        mx, my = me_xy(self.world)
        return math.hypot(mx - self._leg[1][0], my - self._leg[1][1])

    def stuck(self):
        """The last steer leg ended and moved the player under STUCK_MOVE tiles; or (survival 3 fix round 1, R1: E3's
        a40 stood 3 s, five zombies within 1.555 tiles, health 93.7 to 68.3) it still runs, has left the player
        within STUCK_MOVE for WALK_STALL_S (`observe`), and a held threat is within STUCK_NEAR_R."""
        d = self._leg_moved()
        if d is not None:
            return d < STUCK_MOVE
        if self._leg is None or not running(self.actions, self._leg[0]) or self._leg_still < WALK_STALL_S:
            return False
        return any(zdist(self.world, z) <= STUCK_NEAR_R for z in self._threats())

    def leg_heading(self):
        """The last steer leg's heading (vx, vy), else None."""
        return None if self._leg is None else self._leg[2]

    def drop_stuck_leg(self):
        """P24-A fix 2, I1: a running steer leg that reads stuck (`stuck`) is dropped (`_dropped`), so the choose
        re-aims at once with F4's skip; anything else is kept."""
        if self.busy() and self._leg is not None and self.last is self._leg[0] and self.stuck():
            self._dropped = self.last
            return True
        return False

    def _clear(self, v, reach=STEER_PROBE):
        return clear_heading(self.world, v, reach, self.trans)

    def _ahead(self, v, far):
        """The threats of `far` a leg along `v` would run at: within AHEAD_R and AHEAD_CONE of it, or in the
        CORRIDOR_R tube to AHEAD_R along it (fix round 2, T2)."""
        mx, my = me_xy(self.world)
        end = (mx + AHEAD_R * v[0], my + AHEAD_R * v[1])
        out = []
        for z in far:
            dx, dy = z["x"] - mx, z["y"] - my
            d = math.hypot(dx, dy)
            cone = d <= AHEAD_R and (dx * v[0] + dy * v[1]) >= d * math.cos(math.radians(AHEAD_CONE))
            if cone or in_corridor((mx, my), end, z):
                out.append(z)
        return out

    def _steer(self, ts):
        """A leg along the sum of the unit vectors from each threat to the player, each weighted by 1/distance (ruling
        P23-AG 3, amended at fix round 1: every leg), and on the episode's first leg the unit vector from the densest
        met window's centre (`World.met_window`, ruling P24-A (a)) weighted so too, logged `met` [cx, cy, n]; +x when
        the sum is zero (the away vector); turned by STEER_TURNS,
        nearest first, to the first heading clear of the map over AHEAD_R (fix round 3, F3: the leg runs about that
        far) and along which no held threat beyond NEAR_R lies ahead (`_ahead`, T2); else the first such heading
        clear over STEER_PROBE (I4; an unknown square open throughout); else the first clear over STEER_PROBE; else
        (Task 18, the E7 write-up's T19.5: four legs a71-a74 ran into a known fence corner, every turn within 90
        degrees blocked) the first of the rest of the circle (WIDE_TURNS) clear over AHEAD_R and STEER_PROBE with no
        held threat ahead (Task 18 fix 1, the review's minor 9: a 150 or 180 degree turn into the fled group is read
        first), else the first of them clear over STEER_PROBE, else the first of all whose first STEP_PROBE tile
        crosses no known blocked edge; else the away vector kept. After a leg that moved under STUCK_MOVE the turn skips the away vector's own 0 and every
        heading within STUCK_SKIP_DEG of the stuck leg's (F4), turning +30 when nothing is left."""
        mx, my = me_xy(self.world)
        cx = sum(z["x"] for z in ts) / len(ts)
        cy = sum(z["y"] for z in ts) / len(ts)
        met = self.world.met_window() if self._leg is None else None   # P24-A (a): the episode's first leg only
        v = away_vector(self.world, [(z["x"], z["y"]) for z in ts] + ([met[:2]] if met is not None else []))
        v = (1.0, 0.0) if v is None else v
        stuck = self.stuck()
        h0 = self._leg[2] if stuck else (self.skip_heading if self._leg is None else None)
        turns = STEER_TURNS[1:] if h0 is not None else STEER_TURNS
        if h0 is not None:
            cos_skip = math.cos(math.radians(STUCK_SKIP_DEG))
            turns = tuple(t for t in turns if _rotate(v, t)[0] * h0[0] + _rotate(v, t)[1] * h0[1] < cos_skip)
        far = [z for z in ts if zdist(self.world, z) > NEAR_R]
        wide = tuple(t for t in WIDE_TURNS if h0 is None or _rotate(v, t)[0] * h0[0] + _rotate(v, t)[1] * h0[1]
                     < math.cos(math.radians(STUCK_SKIP_DEG)))
        turn, probe = None, None
        for reaches, group, among in (((AHEAD_R, STEER_PROBE), True, turns), ((STEER_PROBE,), True, turns),
                                      ((STEER_PROBE,), False, turns), ((AHEAD_R, STEER_PROBE), True, wide),
                                      ((STEER_PROBE,), False, wide), ((STEP_PROBE,), False, turns + wide)):
            turn = next((t for t in among if all(self._clear(_rotate(v, t), reach) for reach in reaches)
                         and not (group and self._ahead(_rotate(v, t), far))), None)
            if turn is not None:
                probe = reaches[0]
                break
        heading = _rotate(v, turn) if turn is not None else (_rotate(v, STEER_TURNS[1]) if h0 is not None else v)
        near = min(zdist(self.world, z) for z in ts)
        self._aimed = frozenset(self._ids(self._ahead(heading, far)))
        self.why = {"centroid": [cx, cy], "nearest": near, "turn": turn, "probe": probe, "stuck": stuck,
                    "ahead": self._ids(self._ahead(v, far)), "shelter": None, "ended": self.ended}
        if met is not None:
            self.why["met"] = [met[0], met[1], met[2]]
        if h0 is not None and not stuck:
            self.why["skip"] = [h0[0], h0[1]]   # fix 2, G2: the carried stuck heading
        if self._cut is not None:
            self.why["cut"], self._cut = self._cut, None
        return Steer(heading[0], heading[1], FLEE_S, FLEE_GAIT)   # P24-O: a run, never a sprint

    def sent(self, cmd, action):
        if self._chosen == "step":
            self._step, self._step_anchor = action, (self.clock(), me_xy(self.world))
        elif self._chosen == "close":
            self._close = action
        elif self._chosen == "exit":
            self._exit_a, self._exit_anchor = action, (self.clock(), me_xy(self.world))
        elif cmd.TYPE == "steer":
            mx, my = me_xy(self.world)
            self._leg = (action, (mx, my), (cmd.vx, cmd.vy), self._aimed)
            self._leg_anchor, self._leg_still = (self.clock(), (mx, my)), 0.0
        self._chosen = None


class Explore(Policy):
    def __init__(self, world, actions, clock=time.time):
        super().__init__(world, actions, clock)
        self.scanned = set()   # the places scanned from, or with a scan still running
        self._scan = None      # (place, Action) of the last scan sent, until it ends
        self._walk = None      # ((x, y), Action) of the last walk sent, until it ends
        self._last = None      # (aid, place) of the last scan sent: its job may still be dropped after its done line

    def place(self):
        return place_of(self.world)

    def observe(self):
        if self._walk is not None and self.actions.done(self._walk[1]):
            self._walk_ended(*self._walk)
            self._walk = None
        if self._last is not None and self._last[0] in self.world.scans_dropped:
            self.scanned.discard(self._last[1])   # S-32: the job stopped short of its parts, the scan stays done
            self._last = None
        if self._scan is None or not self.actions.done(self._scan[1]):
            return
        place, a = self._scan
        self._scan = None
        if a.state != "done":
            self.scanned.discard(place)

    def choose(self):
        place = self.place()
        if place not in self.scanned:
            self.why = {"scanAt": list(place)}
            return Scan(SCAN_R)
        edge = self.world.unexplored_edge()
        self.why = {"edge": list(edge) if edge else None}
        if edge is None:
            return None
        return WalkTo(*centre(edge), "walk")

    def sent(self, cmd, action, leg=False):
        """`leg`: the walk is a goal's leg toward a farther point (ruling P24-AC, `goals._Legs`): its `no square` marks
        nothing."""
        if cmd.TYPE == "scan":
            self.scanned.add(self.place())
            self._scan = (self.place(), action)
            self._last = (action.aid, self.place())
        elif cmd.TYPE == "walkTo":   # the target square, for mark_stuck; the player's position, for the stuck pair
            self._walk = ((int(math.floor(cmd.x)), int(math.floor(cmd.y))), action, me_xy(self.world), leg)

    def _walk_ended(self, to, a, start, leg=False):
        """A walk's end: a target failed for a STUCK_REASONS reason is marked stuck (a leg's `no square` never: the
        client's unloaded ground is no stuck square, P24-AC); one failed `stuck` with the
        player moved under STUCK_MOVE from its start is a stuck pair from the start's square (P23-AP 1), and the
        rescan of the player's place once STUCK_AREA_N stand in a row there (the goal source's scan, never a third
        walk); a walk that moved the player or ended done ends the run."""
        moved = math.hypot(me_xy(self.world)[0] - start[0], me_xy(self.world)[1] - start[1])
        if a.state == "failed" and a.reason in STUCK_REASONS and not (leg and a.reason == "no square"):
            self.world.mark_stuck(*to)
        if a.state == "failed" and a.reason == "stuck" and moved < STUCK_MOVE:
            self.world.mark_stuck_pair((int(math.floor(start[0])), int(math.floor(start[1]))), to)
            if len(self.world.stuck_run["to"]) in (STUCK_AREA_N, STUCK_AREA_N + STUCK_WALK_CAP):
                self.scanned.discard(self.place())   # the scan the source falls back to (fix round 1, R2: at the cap)
        elif a.state == "done" or moved >= STUCK_MOVE:
            self.world.clear_stuck_run()


class LootHouse(Policy):
    def __init__(self, world, actions, clock=time.time, want=None):
        super().__init__(world, actions, clock)
        self.want = want        # one of LOOT_WANTS, set by the caller: the container's want and the loot's filter
        self.pending = []       # (x, y, z, Action) of each loot sent and not yet seen ended
        self.capped = {}        # (x, y, z, use) -> the carried weight when a loot there skipped items for the cap
        self.within = None      # a set of container keys a target is kept to (a LootBuilding goal's), None for any
        self._key = None        # the container the last choose picked
        self.fails = {}         # (container key, use) -> failed loots there (Task 18 fix 1, major 3)

    def level(self):
        return (self.world.load or {}).get("level") or 0

    def cap(self):
        """The loot's maxWeight: the frame's load.max times LOAD_RATIO_MAX, 0.0 (no cap) when it reads no positive
        number. A `clothing` loot takes at most CLOTHING_LOOT_KG per garment still wanted on top of the carried weight
        (CLOTHING_HELD_N less the unworn garments held), never past that cap (review-t24 major 3)."""
        m = (self.world.load or {}).get("max")
        ok = isinstance(m, (int, float)) and not isinstance(m, bool) and m > 0
        cap = float(m) * LOAD_RATIO_MAX if ok else 0.0
        w = self.weight()
        if self.want == "clothing" and ok and w is not None:
            spare = sum(1 for i in self.world.by_use().get("clothing", ()) if self.world.inventory[i].get("worn") is not True)
            cap = min(cap, w + max(CLOTHING_HELD_N - spare, 0) * CLOTHING_LOOT_KG)
        return cap

    def weight(self):
        w = (self.world.load or {}).get("weight")
        return w if isinstance(w, (int, float)) and not isinstance(w, bool) else None

    def observe(self):
        still = []
        for x, y, z, a in self.pending:
            if not self.actions.done(a):
                still.append((x, y, z, a))
                continue
            if a.state == "failed" and a.reason == PREEMPTED:
                continue
            use = a.args.get("filter")
            skipped = a.result.get("skipped") if isinstance(a.result, dict) else None
            if isinstance(skipped, (int, float)) and not isinstance(skipped, bool) and skipped > 0:
                self.capped[(x, y, z, use)] = self.weight()   # the items left may fit once the load falls
                continue
            self.capped.pop((x, y, z, use), None)
            mark = a.state == "done" or (a.state == "failed" and a.reason in LOOT_MARKS)
            for key, c in self.world.containers.items():
                if key[:3] != (x, y, z) or not any(holds_use(i, use) for i in c["items"]):
                    continue
                n = 0 if mark else self.fails.get((key, use), 0) + 1
                if mark or n >= LOOT_FAILS_TO_PASS:
                    self.fails.pop((key, use), None)
                    self.world.mark_looted(key, use)
                else:
                    self.fails[(key, use)] = n
        self.pending = still

    def waiting(self, want):
        """The container keys on a square whose loot for `want` skipped items for the cap, while the carried weight
        has not fallen below its reading at that loot's end (an unreadable weight on either side keeps waiting)."""
        now = self.weight()
        squares = {k[:3] for k, w in self.capped.items() if k[3] == want and (now is None or w is None or now >= w)}
        return {k for k in self.world.containers if k[:3] in squares}

    def target(self, want):
        """The container a loot for `want` would go to: `world.nearest_unlooted(want)` less the squares waiting on
        the cap, and kept to `within` when it is set; None for a want outside LOOT_WANTS."""
        if want not in LOOT_WANTS:
            return None
        exclude = self.waiting(want)
        if self.within is not None:
            exclude = exclude | {k for k in self.world.containers if k not in self.within}
        return self.world.nearest_unlooted(want, exclude=exclude)

    def choose(self):
        level = self.level()
        if level > LOOT_MAX_LEVEL:
            self.why = {"level": level, "hold": True}
            return None
        key = self.target(self.want)
        cap = self.cap()
        self._key = key
        self.why = {"level": level, "want": self.want, "container": list(key) if key else None, "cap": cap}
        if key is None:
            return None
        return Interact(int(key[0]), int(key[1]), "loot", self.want, maxWeight=cap)

    def sent(self, cmd, action):
        if cmd.TYPE == "interact":
            self.pending.append((self._key[0], self._key[1], self._key[2], action))
