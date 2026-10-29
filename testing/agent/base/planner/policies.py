"""The multi-step policies (Plan 22 Task 10, spec § 3): fight, flee, explore and loot-house, each a Python machine over
the Lua's one-step skills, sending typed commands through `Actions` and reading the `World`.

One action at a time. A policy's `step()` returns the `Action` it sent, or None: it sends nothing while its own last
action is `actions.current` (sent, accepted or in progress), and decides again once that action reads a terminal
state (`done`, `failed`, `rejected`, `timeout`) or another sender's action replaced it. `step()` is `observe()` (the
policy's bookkeeping from the World and its last action's end), then `choose()` (the next command, or None) and
`send(cmd)`; `survive.Survive` calls the three apart so its cooldown can pass a choice over before it is sent. Every
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
  target the same way.
  The standing fight (rulings P24-G 1 and P24-N, survive.py's docstring; P24-N supersedes P24-M's backpedal band
  after E6, `e_day_6-20261029-102942`: 8 of its 11 stance legs stood, the fights went to the approach and swing):
  with `stance` set (Survive's `_stance_ok`), neither `point_blank` nor `only`, and the target within AIM_R
  (`stance_at`), every leg is `Aim(vx, vy, AIM_LEG_S, targetId)` facing the target (`_stance_leg`), the fight's first
  action included: within FIGHT_REACH with the stance not held (`in_stance`: the last send was this Fight's running
  aim, or its attack from the stance running or ended within AIM_HOLD_S, Task 9's hand-over) an `enter` leg (0, 0),
  the swing following from it; inside KEEP_R the backpedal (`away_vector` of `threats` turned by STEER_TURNS to the
  first heading `clear_heading` passes, never into a wall or over a hoppable fence, else (0, 0)); beyond it standing
  (0, 0), the target faced while it comes. A running leg gives way (`busy`) once the target is within reach,
  re-pinned, or the stand ends, and a standing one once the target is inside KEEP_R or the advance begins. The stand
  clock (`_stand`) restarts on a new target or a fall of its health, ending any advance; at STAND_MAX_S the Fight
  closes in the stance (`advance`: `toward` legs, the unit vector to the target, or with its line blocked over
  STEER_PROBE the approach walk at a run round the wall), the out-of-reach stall clock (which a stand keeps at zero)
  starting then. A stance leg that ends failed, timed out or rejected (never superseded, nor refused `no target`:
  Task 10 fix 2, the zombie is gone) sets `standoff` at once (Task 10 fix 1, minor 11: a build that cannot hold the
  stance never re-sends it), and the approach and swing above run for the rest of the Fight; `standoff_why` names
  the leg's state and reason.
- `Flee` (one per flee episode): a `Steer` of `FLEE_S` seconds away from the threats (the `threats` list its caller
  passes, else every zombie the World holds), at a sprint when the nearest is within `SPRINT_R`, else a run; re-aimed on
  every end of its steer. Every leg runs along the sum of the unit vectors from each threat to the player, each weighted
  by 1/distance (ruling P23-AG 3, amended at fix round 1 to every leg: away from the centroid and from the nearest, so a
  group spread round the player is not fled into); a zero sum steers along +x. The steer reads the map (fix round 1, I4:
  the chain's E1 died sprinting 15 s into a fence the World already held as `blockW`, the group biting): the away vector
  turns by STEER_TURNS (30, 60, 90 degrees either way, nearest first) to the first heading whose `world.line_clear` over
  AHEAD_R (9 tiles, about a leg's run: fix round 3, F3) and over STEER_PROBE is true (survival 2, the fix-3 review's
  (a): the two rasterised lines cross different squares, so a 9-tile clear alone may graze a wall the 3-tile line
  meets), else over STEER_PROBE (3) tiles, an unknown square read
  open (`unknown_open`, its unknown diagonal corner open too: F5) (fix round 2, concern 1: unscanned ground is no wall,
  so the flee does not bend along the scanned area's edge), and along which no held threat beyond SPRINT_R lies within
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
  sprint: it drains the endurance the night needs). A step's end is read by `night.shelter_ended`: `advance`, `resend`
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
  With `many` (Survive's: the episode's reason was `many`) and the nearest held threat beyond SPRINT_R, the steer
  and the shelter walks go at a sprint (FLEE_GAIT a run otherwise) while the frame's `stats.endurance` reads above
  SPRINT_END (0.5), or, with none read, for SPRINT_MAX_S (20) wall seconds from the episode's first such sprint.
  With `steer_now` (Survive's group at melee range, its last leg not stuck), the choose steers first.
  Survival 4 (ruling P23-AP 3, E4's line 440: a leg aimed west before two zombies there were listed ran 8.92 tiles
  into them): on every threat tick the running steer leg's heading is re-read against the held threats (`_cut_leg`:
  `_ahead`, AHEAD_R, AHEAD_CONE and the CORRIDOR_R tube, beyond SPRINT_R); a threat ahead that was not ahead when the
  leg was aimed cuts it, and the next choose re-aims by the turn rules (its why's `cut` the ids), the new leg
  superseding it. Fix round 1: the cut reads the World's current records by id (G1), and a cornered Fight
  (`point_blank`) re-pins at each choose to the nearest zombie within POINT_BLANK_R (R4).
  Survival 5 (ruling P24-A; survive.py's docstring is the record): the re-pin only while the pin stands beyond
  POINT_BLANK_R (d); no approach walk at point blank (e); no attack while the frame's `me.hitReaction` names one
  (`hit_reaction`, i); `others_behind` (b), Survive's look past a fight's walk target; the episode's first leg
  repulsed from `World.met_window`'s centre too (a); on a room square `steer_now` never steers: the exit at a sprint,
  else the adoption or the trapped hold, and `give_way` keeps a running exit, re-sent at a sprint (f).
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
  `why["cap"]`. The looted mark is per use (Task 11 fix 1): when the interact ends, done, failed, rejected or timed
  out, every container on its square holding an item of the loot's filter is marked looted for that use only
  (`world.mark_looted(key, use)`), so a counter looted for water is still looted for food later; except a `failed
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

from agent.base.items import use_of
from agent.base.pza1 import Aim, Attack, Interact, Scan, Steer, Stop, WalkTo
from agent.base.world import STUCK_AREA_N, STUCK_WALK_CAP, me_floor, me_xy

DANGER_R = 6.0        # tiles: a zombie this close is a threat (Survive's threat branch; the night sends nothing)
FIGHT_REACH = 2.0     # tiles: a nearest zombie beyond this is walked to, within it attacked
FIGHT_MAX_S = 20.0    # wall seconds the target may stay beyond FIGHT_REACH before the fight reads stalled
DISENGAGE_R = 10.0    # tiles: a pinned target beyond this is dropped (and Survive's hold radius while a threat runs)
REPOSITION_R = 2.5    # tiles: a reposition square farther than this from the player is never walked to (P23-Q)
REPOSITION_MIN = 1.2  # tiles: ... nor one whose centre is nearer than this, inside the Lua walk's DONE_R 1.0 (P23-AJ 5)
MISSES_TO_APPROACH = 2   # attack results in a row with attackStarted false before one approach walk
STALL_SWINGS = 3      # started swings in a row on one target that took no health before it reads unreachable
UNREACHABLE_S = 20.0  # wall seconds a no-progress target is skipped
FLEE_S = 3.0          # seconds a flee's steer runs before it is re-aimed
SPRINT_R = 2.0        # tiles: a nearest zombie within this is fled at a sprint
SHELTER_FLEE_R = 25.0  # tiles: a flee runs to a known door whose approach square is this near (ruling P23-AG)
FLEE_GAIT = "run"     # the shelter walks' gait (P23-AG; a sprint drains the endurance the night needs: N1's ruling)
                      # (a `many` flee sprints them while endurance allows: P23-AM 3, `Flee._group_sprint`)
CORRIDOR_R = 2.0      # tiles: a zombie this near the line to a door's approach square, ahead, refuses it (fix 1, I1)
STEER_PROBE = 3.0     # tiles: a steer heading is clear when the map's line this far along it is (fix 1, I4)
STEER_TURNS = (0, 30, -30, 60, -60, 90, -90)   # degrees a blocked heading turns, nearest first
STUCK_MOVE = 0.5      # tiles: a steer leg that moved less is stuck, and the next turns off the away vector
AHEAD_R = 9.0         # tiles: a 3 s leg at about 3 tiles/s (E1's flee): a held threat this far ahead refuses a heading
AHEAD_CONE = 20.0     # degrees: ... within this cone of it (or in its CORRIDOR_R tube), beyond SPRINT_R (fix 2, T2)
DOOR_CLEAR_R = 1.5    # tiles: no re-close is tried with a known zombie this near the door square's centre (fix 2)
EXIT_CLEAR_R = 1.5    # tiles: no exit is walked with a held threat this near its outside square or ahead on its
                      # straight line (the tube, `_in_tube`): P23-AJ fix 1, narrowed at P24-A fix 1 (3), never one at
                      # the player's back
WALK_STALL_S = 1.0    # wall seconds a flee walk may leave the player within STUCK_MOVE before it is dropped: the exit
                      # walk (P23-AJ fix 1, G2), a shelter step's walk while a held threat is within DANGER_R (P23-AM 2)
                      # and a running steer leg's stuck read (P23-AM fix 1, R1); one quantity (P24-A (g), the close
                      # review's M3: the old EXIT_STALL_S and STEP_STALL_S merged)
SPRINT_END = 0.5      # a `many` flee sprints beyond SPRINT_R while the frame's endurance reads above this (P23-AM 3)
SPRINT_MAX_S = 20.0   # wall seconds a `many` flee sprints with no endurance read, an episode (P23-AM 3, a judgment:
                      # about a full endurance bar's sprint; the frames have read endurance since PZA/1.0, so a
                      # backstop for a frame without it)
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
AIM_HOLD_S = 2.0      # seconds the Lua keeps a stance an attack swung from once nothing runs (K.AIM_HOLD_MS 2000,
                      # PZAgent_Stance.lua): an attack ended longer ago left the character out of the stance
STUCK_SKIP_DEG = 15.0  # degrees: after a stuck leg, no heading this near its heading is chosen again (fix 3, F4)
SCAN_R = 10           # tiles: the scan radius, and the grid a place is rounded to
LOOT_MAX_LEVEL = 1    # spec § 9 (1) "stops looting before level 3": a loot is sent only at load level 0-1
LOAD_RATIO_MAX = 1.0  # a loot fills to this times the frame's load.max (level 1 holds up to 1.25 of it, #3926)
LOOT_WANTS = ("food", "water", "weapon", "bandage")   # a loot's want and filter: one use, never `all` (P23-8)
DROP_AT = 3           # at this load level or above Survive's load branch drops (the heavy-load drain falls at 3) ...
DROP_TO = 2           # ... down to this level, and between the two neither drops nor loots
KEPT_USES = ("weapon", "food", "water")   # the uses a drop never takes
AIM_R = 12.0   # tiles: the Lua's K.AIM_R (PZAgent_Stance.lua), the farthest target an aim takes: beyond it the aim is refused `no target`
NO_TARGET = "no target"   # the Lua's refusal of an aim whose target is gone (Task 10 fix 2: not a stand-off)
PREEMPTED = "superseded"   # the reason the Lua fails an action a newer send replaced
STUCK_REASONS = ("stuck", "no path", "no square")   # a walkTo failed for one of these: its target is remembered


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

    def __init__(self, world, actions, clock=time.time):
        self.world = world
        self.actions = actions
        self.clock = clock
        self.last = None      # the last Action this policy sent
        self.why = {}

    def busy(self):
        """True while this policy's last action is the current one and not yet terminal."""
        return self.last is not None and self.actions.current is self.last

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
    `world.by_use()` (so a bottle marked empty is `other`, and spare), ties by the least id; else None. Survive's load
    branch and its flee drop it."""
    wielded = (world.weapon or {}).get("type")
    by_use = world.by_use()
    kept = {iid for use in KEPT_USES for iid in by_use[use]}
    best = None
    for iid, it in world.inventory.items():
        if not item_id_ok(iid) or iid in kept or (it.get("fullType") or "") == wielded:
            continue
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


def clear_heading(world, v, reach=STEER_PROBE):
    """The map's line `reach` tiles along `v` from the player, an unknown square open (fix round 2, concern 1). A
    hoppable fence's edge reads blocked (`line_clear` never climbs: a steer or a backpedal never vaults, ruling P24-G
    4)."""
    mx, my = me_xy(world)
    return world.line_clear((mx, my), (mx + reach * v[0], my + reach * v[1]), unknown_open=True)


def blocked(unreachable, now):
    """The ids of `unreachable` (id -> wall until) still skipped at `now`."""
    return {zid for zid, until in unreachable.items() if until > now}


class Fight(Policy):
    def __init__(self, world, actions, clock=time.time, unreachable=None, target=None):
        super().__init__(world, actions, clock)
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

    def blocked(self):
        """The ids skipped now: the marked ones, less, for a cornered Fight (`mark_free_r`, fix round 1 I3), a marked
        zombie `in_reach` within that radius (fix round 2, G4: within POINT_BLANK_R, or with a line not read blocked;
        one behind a blocked line at 1.0-1.5 stays marked); and always every id marked during this choose (G4: the
        mark's recursion never re-pins the id it just marked)."""
        out = blocked(self.unreachable, self.clock())
        if self.mark_free_r > 0.0:
            zs = self.world.zombies
            out = {zid for zid in out if not (zid in zs and in_reach(self.world, zs[zid], self.mark_free_r))}
        return out | self._marked_now

    def _target_health(self, zid):
        z = self.world.zombies.get(zid)
        return None if z is None else z.get("health")

    def _mark_unreachable(self, zid):
        self._marked_now.add(zid)
        self.unreachable[zid] = self.clock() + UNREACHABLE_S
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

    def stand_s(self):
        """Wall seconds the running stand has gone without progress, else None."""
        return None if self._stand is None else self.clock() - self._stand[1]

    def busy(self):
        """The Policy's rule, except that a running stance leg gives way at once (P24-G 1) when the target is within
        FIGHT_REACH (the swing from the stance), another target is pinned, or the stand no longer applies; and a
        standing leg (P24-N) once the target is inside KEEP_R (the backpedal) or the advance began."""
        if not super().busy():
            return False
        if self.last.type != "aim":
            return True
        t = self._target(pin=False)
        if t is None or t[0] != self.last.args.get("targetId") or t[2] <= FIGHT_REACH or not self.stance_at(t[2]):
            return False
        return not (self._leg == "stand" and (t[2] <= KEEP_R or self.advance))

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

    def observe(self):
        self._observe_leg()
        t = self._target(pin=False)
        self._observe_stand(t)
        if t is None or t[2] <= FIGHT_REACH or (self.stance_at(t[2]) and not self.advance):
            self.out_of_reach_since = self.clock()   # P24-G 1: a stand's own clock is STAND_MAX_S
        a = self.last
        if a is None or a.type != "attack" or not self.actions.done(a) or a is self._counted:
            return
        self._counted = a
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
        skipped = sorted(self.blocked(), key=str)
        if skipped:
            self.why["unreachable"] = skipped
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
        self._repin_point_blank()
        t = self._target(pin=True)
        if t is None:
            self.why = {"target": None, "pinned": False}
            return None
        zid, z, d = t
        if self.point_blank and d > CORNERED_R:   # P24-A fix 2, I2a: a cornered Fight never walks to a drifted pin
            self.why = {"target": zid, "pinned": True, "dist": d, "out_of_reach": True}
            return None
        if d <= POINT_BLANK_R:
            self.approach = False   # P24-A (e), the close review's I3 (F1's walkTo at 0.49 tiles): never at point blank
        blank = self.point_blank and d <= POINT_BLANK_R   # P23-AJ fix 1: in reach whatever the map's line says
        line = self._line(z) if d <= FIGHT_REACH and not blank else None
        self.why = {"target": zid, "pinned": True, "dist": d, "approach": self.approach, "line": line,
                    "reposition": None}
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
            return self._stance_leg(zid, z, d)   # P24-N: every leg of a standing fight is an aim, the first one too
        if self.approach or d > FIGHT_REACH:
            return WalkTo(*centre((z["x"], z["y"])), "run")
        hit = hit_reaction(self.world)
        if hit is not None:   # P24-A (i): the engine starts no swing in a hit reaction (#4292, #4293): sent on its end
            self.why["hitReaction"] = hit
            return None
        self._held_before = self.stance_at(d) and self.in_stance()
        if self.stance_at(d):
            self.why["stance"] = True   # the swing from the stance (Task 9's hand-over keeps it)
        return Attack(zid)   # nearest_zombie yields int ids only (M7)

    def _stance_leg(self, zid, z, d):
        """One stance leg (rulings P24-G 1 and P24-N): `aim` facing the target for AIM_LEG_S, walking (the stance
        never runs) one of
        - `enter` (0, 0): the target within FIGHT_REACH with the stance not held (`in_stance`): the stance is taken
          before the swing, which the next choose sends from it;
        - `toward`: the advance (`advance`, after STAND_MAX_S without progress), the unit vector to the target while
          its STEER_PROBE line (to the target at most) is clear; with that line blocked the approach walk at a run
          closes on it instead (the path follower walks round the wall), the one walk of a standing fight;
        - `back`: the target inside KEEP_R: `away_vector` of the held threats (`threats`, else the target) turned
          by STEER_TURNS to the first heading `clear_heading` passes (never into a wall or over a fence), else
          standing: a wall behind is never stepped into;
        - `stand` (0, 0): the target beyond KEEP_R, faced while it comes."""
        v, kind = None, "stand"
        if d <= FIGHT_REACH:
            kind = "enter"
        elif self.advance:
            mx, my = me_xy(self.world)
            u = ((z["x"] - mx) / d, (z["y"] - my) / d)
            if not clear_heading(self.world, u, min(STEER_PROBE, d)):
                self.why.update({"stance": True, "advance": True, "leg": "walk", "stand_s": self.stand_s()})
                return WalkTo(*centre((z["x"], z["y"])), "run")
            v, kind = u, "toward"
        elif d <= KEEP_R:
            kind = "back"
            ts = [q for q in (self.threats or [z]) if q.get("x") is not None and q.get("y") is not None]
            a = away_vector(self.world, [(q["x"], q["y"]) for q in ts])
            if a is not None:
                v = next((_rotate(a, t) for t in STEER_TURNS if clear_heading(self.world, _rotate(a, t))), None)
        vx, vy = v if v is not None else (0.0, 0.0)
        self.why.update({"stance": True, "leg": kind, "back": [vx, vy] if kind == "back" and v is not None else None,
                         "stand_s": self.stand_s()})
        if self.advance:
            self.why["advance"] = True
        return Aim(vx, vy, AIM_LEG_S, targetId=zid)

    def sent(self, cmd, action):
        if cmd.TYPE == "aim":
            self._leg = self.why.get("leg")
        elif cmd.TYPE == "walkTo":
            self.approach = False
        elif cmd.TYPE == "attack":
            self._attack_held = self._held_before
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


def exit_plan(world, threats, refused=()):
    """The way out of the building the player stands in (ruling P23-AJ 3 as amended, and its fix round 1), else
    None: standing on a room square of a building, of its `night.exits` on the player's floor (an opening, or a
    closed exterior door to open first) whose outside square is not in `refused`, whose outside square's centre is no
    nearer any threat than the player is to it (the shelter pick's rule), and whose straight line from the player to
    that centre passes no threat within EXIT_CLEAR_R (fix round 1: E2's offline check at gameMin 585 chose an opening
    across the building past the zombie at 0.48 tiles), and whose square beyond is open (`_beyond`; the review's I1:
    a walk to the outside square itself ends `done` on the room square and is refused), the nearest to the player,
    ties by that square; `{building, inner, outer, door, target, step, opened}`, `target` the square the walk goes to,
    `step` "walk" (the review's I2: the jar's path follower opens a closed door on a player's path,
    `PathFindBehavior2.checkDoorHoppableWindow`, a review reading; the open is the fallback), `opened` False."""
    N = _night()
    s = world.map.get(N.player_square(world)) or {}
    b = s.get("building")
    if s.get("room") is None or b is None:
        return None
    ts = [z for z in threats if z.get("x") is not None and z.get("y") is not None]
    me = me_xy(world)
    best = None
    for e in N.exits(world, b, me_floor(world)):
        if e["outer"] in refused:
            continue
        c = centre(e["outer"])
        if any(math.hypot(z["x"] - c[0], z["y"] - c[1]) < zdist(world, z)
               or _in_tube(me, c, (z["x"], z["y"]), EXIT_CLEAR_R) for z in ts):
            continue
        if _beyond(world, e["inner"], e["outer"]) is None:
            continue
        rank = (math.hypot(c[0] - me[0], c[1] - me[1]), e["outer"], e["inner"])
        if best is None or rank < best[0]:
            best = (rank, e)
    if best is None:
        return None
    e = best[1]
    return dict(e, building=b, target=_beyond(world, e["inner"], e["outer"]), step="walk", opened=False)


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


def _beyond(world, inner, outer):
    """The square the exit walks to: one more square on from `outer` away from `inner` when the map holds it open (not
    solid, no room, the step to it not blocked), else None (the exit is skipped: fix round 1, the review's I1). A walk
    ends `done` within the Lua's DONE_R (1.0) of its target, so a walk to the outside square's own centre may end on
    the room square beside it (rule 5's lesson); from the square beyond it ends at least a tile from the room
    square's centre."""
    sq = (2 * outer[0] - inner[0], 2 * outer[1] - inner[1], outer[2])
    s = world.map.get(sq)
    if s is None or s.get("solid") or s.get("room") is not None or world.blocked(outer, sq):
        return None
    return sq


def adoptable(world):
    """The building the player stands in has an exterior door on the player's floor (`Flee._adopt` can adopt it)."""
    N = _night()
    s = world.map.get(N.player_square(world)) or {}
    b = s.get("building")
    return s.get("room") is not None and b is not None and bool(N.exterior_doors(world, b, me_floor(world)))


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
        self.many = False        # Survive sets it: the episode's reason is `many` (P23-AM 3: the group sprint)
        self.steer_now = False   # Survive sets it: a group at melee range, the last leg not stuck (P23-AM 4)
        self._sprint_from = None  # wall of the episode's first sprint chosen with no endurance read (SPRINT_MAX_S)
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

    @property
    def sheltered(self):
        """The episode's shelter plan read done (its close ended) and is kept."""
        return self.plan is not None and self.plan["step"] == "done"

    def running_shelter(self):
        """A shelter plan is running and its close has not ended (Survive's inside hold waits for it)."""
        return self.plan is not None and self.plan["step"] != "done"

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
        if self._leg is not None and self.actions.current is self._leg[0]:
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

    def _ids(self, zs):
        """The World's ids of the zombie records `zs` (this tick's dicts), sorted."""
        ids = {id(z): zid for zid, z in self.world.zombies.items()}
        return sorted((ids.get(id(z)) for z in zs), key=repr)

    def _cut_leg(self):
        """Ruling P23-AP 3 (E4's line 440: a leg aimed west before 19032 and 19035 were listed ran 8.92 tiles into
        them): the running steer leg's heading re-read against this tick's held threats beyond SPRINT_R (`_ahead`: the
        cone and the tube the aim refuses); one ahead that was not ahead at its aim cuts it (`_dropped`, so the next
        choose re-aims by the turn rules and the new leg supersedes it), logged as the next steer's `cut`. Fix round 1
        (the review's G1): the World's current records by id, the held ones (within DISENGAGE_R) beyond SPRINT_R, never
        the caller's list, which may be the last tick's records, every one replaced since by its frame (an id read None
        is never new: e07a52cb cut a fallback leg on every tick, so R1's stuck read never came)."""
        leg = self._leg
        if leg[0] is self._dropped:
            return
        far = [(zid, z) for zid, z in self.world.zombies.items() if target_id_ok(zid) and z.get("x") is not None
               and z.get("y") is not None and SPRINT_R < zdist(self.world, z) <= DISENGAGE_R]
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
        if self.actions.current is not a:
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
        a room square a running exit walk is not refused (ruling P24-A (f): inside, the group's answer is the exit):
        one at a sprint is kept, one at another gait dropped unread (its superseded end never refuses it), so the
        choose re-sends it at a sprint."""
        if not self.busy() or self.last.type not in ("walkTo", "interact"):
            return
        if self.last is self._exit_a and self.exit is not None and on_room(self.world):
            if self.last.type == "walkTo" and self.last.args.get("gait") != "sprint":
                self._dropped = self._exit_read = self.last
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
            if self.exit["step"] != "walk" or self.actions.current is not a:
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
        cmd, step = N.shelter_step(self.world, self.plan)
        b = self.plan["building"]
        if step == "shun":
            self._drop(True)
            return None
        if step != "done":
            self._chosen = "step"
            self.why = {"shelter": b, "step": step, "ended": self.ended}
            if cmd.TYPE != "walkTo":
                return cmd
            near = min(zdist(self.world, z) for z in ts)
            return WalkTo(cmd.x, cmd.y, "sprint" if self._group_sprint(near) else FLEE_GAIT)
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
        return WalkTo(*centre(e["target"]), "sprint" if self.steer_now else FLEE_GAIT)   # P24-A (f): a group, a sprint

    def _adopt(self, ts):
        """Fix round 1 (concern 1): the building stood in, every way out refused, adopted as sheltered: its plan kept
        to its open exterior door nearest the threats, else its exterior door nearest them (iteration 1's F1), read
        done, so the sheltered hold, the re-close guard and Survive's door fight apply; None with no exterior door on
        this floor (E2's building 3: its doors all broken)."""
        N = _night()
        b = (self.world.map.get(N.player_square(self.world)) or {}).get("building")
        doors = N.exterior_doors(self.world, b, me_floor(self.world)) if b is not None else []
        if not doors:
            return None

        def rank(d):
            is_open = bool(((self.world.map.get(d) or {}).get("door") or {}).get("open"))
            return not is_open, min(math.hypot(z["x"] - d[0] - 0.5, z["y"] - d[1] - 0.5) for z in ts), d
        return N.shelter_plan(self.world, b, door=min(doors, key=rank), step="done")

    def choose(self):
        """The running exit; else the shelter (picked at each re-aim until one is chosen: fix round 2, T1, and never
        from a room square); else, on a room square, a new exit (`exit_plan`, P23-AJ 3), else, once an episode, the
        building adopted (`_adopt`, fix round 1), else the trapped hold (no command, `why.trapped`: on a room square
        the flee never steers, fix round 1: steering inside killed E2); else the steer. With `steer_now` (P23-AM 4 and
        AP 2: Survive's group, `_group`, the last leg not stuck) the steer goes first off a room square (the next leg
        that ends stuck is Survive's corner); on a room square (ruling P24-A (f), the close review's I4: the group
        steer ran inside a room with a way out, E2's death mode) the steer is never sent: the running exit, else a new
        one, walked at a sprint, else the adoption, else the trapped hold."""
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
        if self.plan is not None:
            cmd = self._shelter(ts)
            if cmd is not None or self.plan is not None:
                return cmd
        if on_room(self.world):
            self.exit = exit_plan(self.world, ts, self.refused)
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
        if self._leg is None or self.actions.current is not self._leg[0] or self._leg_still < WALK_STALL_S:
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

    def _group_sprint(self, near):
        """Ruling P23-AM 3 (a sprint outpaces a walking group): the episode's reason is `many`, the nearest held
        threat beyond SPRINT_R (within it the steer sprints anyway), and the frame's `stats.endurance` above
        SPRINT_END; with no endurance read, for SPRINT_MAX_S wall seconds from the episode's first such sprint."""
        if not self.many or near <= SPRINT_R:
            return False
        e = (self.world.stats or {}).get("endurance")
        if isinstance(e, (int, float)) and not isinstance(e, bool):
            return e > SPRINT_END
        if self._sprint_from is None:
            self._sprint_from = self.clock()
        return self.clock() - self._sprint_from < SPRINT_MAX_S

    def _clear(self, v, reach=STEER_PROBE):
        return clear_heading(self.world, v, reach)

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
        far) and along which no held threat beyond SPRINT_R lies ahead (`_ahead`, T2); else the first such heading
        clear over STEER_PROBE (I4; an unknown square open throughout); else the first clear over STEER_PROBE, else
        the away vector kept. After a leg that moved under STUCK_MOVE the turn skips the away vector's own 0 and every
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
        far = [z for z in ts if zdist(self.world, z) > SPRINT_R]
        turn, probe = None, None
        for reaches, group in (((AHEAD_R, STEER_PROBE), True), ((STEER_PROBE,), True), ((STEER_PROBE,), False)):
            turn = next((t for t in turns if all(self._clear(_rotate(v, t), reach) for reach in reaches)
                         and not (group and self._ahead(_rotate(v, t), far))), None)
            if turn is not None:
                probe = reaches[0]
                break
        heading = _rotate(v, turn) if turn is not None else (_rotate(v, STEER_TURNS[1]) if h0 is not None else v)
        near = min(zdist(self.world, z) for z in ts)
        gait = "sprint" if near <= SPRINT_R or self._group_sprint(near) else "run"
        self._aimed = frozenset(self._ids(self._ahead(heading, far)))
        self.why = {"centroid": [cx, cy], "nearest": near, "turn": turn, "probe": probe, "stuck": stuck,
                    "ahead": self._ids(self._ahead(v, far)), "shelter": None, "ended": self.ended}
        if met is not None:
            self.why["met"] = [met[0], met[1], met[2]]
        if h0 is not None and not stuck:
            self.why["skip"] = [h0[0], h0[1]]   # fix 2, G2: the carried stuck heading
        if self._cut is not None:
            self.why["cut"], self._cut = self._cut, None
        return Steer(heading[0], heading[1], FLEE_S, gait)

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

    def sent(self, cmd, action):
        if cmd.TYPE == "scan":
            self.scanned.add(self.place())
            self._scan = (self.place(), action)
            self._last = (action.aid, self.place())
        elif cmd.TYPE == "walkTo":   # the target square, for mark_stuck; the player's position, for the stuck pair
            self._walk = ((int(math.floor(cmd.x)), int(math.floor(cmd.y))), action, me_xy(self.world))

    def _walk_ended(self, to, a, start):
        """A walk's end: a target failed for a STUCK_REASONS reason is marked stuck; one failed `stuck` with the
        player moved under STUCK_MOVE from its start is a stuck pair from the start's square (P23-AP 1), and the
        rescan of the player's place once STUCK_AREA_N stand in a row there (the goal source's scan, never a third
        walk); a walk that moved the player or ended done ends the run."""
        moved = math.hypot(me_xy(self.world)[0] - start[0], me_xy(self.world)[1] - start[1])
        if a.state == "failed" and a.reason in STUCK_REASONS:
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

    def level(self):
        return (self.world.load or {}).get("level") or 0

    def cap(self):
        """The loot's maxWeight: the frame's load.max times LOAD_RATIO_MAX, 0.0 (no cap) when it reads no positive
        number."""
        m = (self.world.load or {}).get("max")
        ok = isinstance(m, (int, float)) and not isinstance(m, bool) and m > 0
        return float(m) * LOAD_RATIO_MAX if ok else 0.0

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
            for key, c in self.world.containers.items():
                if key[:3] == (x, y, z) and any(use_of(i) == use for i in c["items"]):
                    self.world.mark_looted(key, use)
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
