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

- `Fight` and `Flee`: `planner/fight.py` and `planner/flee.py`, each module's docstring its record (moved out of this
  module at Plan 24 Task 36, a pure move); this module keeps the constants they read, the reads they share (the
  line, the heading, the pull's group, the way out's and the shelter's squares) and the `Policy` base, and names
  both classes for the frozen drivers that import them from here (`__getattr__`).
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
from agent.base.pza1 import Interact, Scan, WalkTo
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
WINDOW_STALL_S = 3.0  # wall seconds a window way out's act may leave the player within STUCK_MOVE before it is dropped
                      # (ruling P26-J, `flee.Flee._stall_limit`): above the one live window climbed `done`, F5's a20
                      # (`f_goals_6-20261030-192251`), whose longest such hold was 2.497 s (frame seq 1617 to 1661, the
                      # open and the climb's start), below E17's a81 (`e_day_17-20261102-180459`), 12.9 s from seq 3482
                      # to its `dead` end; WALK_STALL_S would have dropped F5's at seq 1573
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
CRAWLER_R = 1.0       # tiles: a crawler or a fallen zombie this near is stomped first while one stands within DANGER_R
KEEP_MARGIN = 0.25    # tiles: a running backpedal holds until its target is this far past KEEP_R, so the back and
                      # stand legs do not flap at the line (Task 12 fix 1, the review's major 1)
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
STRAIN_HARD = 20.0    # ... at which the damage is halved: the Fight never swings (`arms_hurt`, P24-AP), and the
                      # threat branch reads the pain as the `wounded` reason, a lone target still sought (ruling P24-AT)
STIFF_HARD = 20.0     # the frame's `body.strain` (an arm's stiffness, #4369) at which the arms' hold starts on either
                      # arm (ruling P24-AT, superseding P24-AG's read of the pain: the health panel calls a part's
                      # stiffness minor under 20, #4369) ...
STIFF_SOFT = 5.0      # ... and under which, on both arms, it ends (the panel names a stiffness from 5, #4369)
ENDURANCE_T = 0.75    # the frame's stats.endurance at or under which the ENDURANCE moodle reads level 1 (#3926, #4076),
                      # whose first level halves every swing (#4371): the disengage of P24-AG
ENDURANCE_RELEASE = 0.80   # ... and above which that hold ends (review-t27: rest gives back 0.003-0.005 a game minute,
                           # a fight takes far more, so the edge alone flickered flee / one swing / flee)
TIRED_FIGHT_T = 0.6   # stats.fatigue at or above which no fight is sought or stood (ruling P24-AK; the first TIRED
                      # moodle, night.TIRED_T, halves every swing at its first level too, #4371)
SHOVE_R = 1.1         # tiles: the engine's shove reach, the bare hands' MaxRange 1.1 to the zombie's position, #4592;
                      # the Lua's K.SHOVE_R 1.5 is a wider bound (ruling P28-B, Plan 28 Task 3, the jar read withdrawing
                      # P28-B1's early shove: the reach is the point-blank band itself; 1.5 before it)
STAND_MIN_R = 0.61    # tiles: a standing zombie this near the player makes the engine's call shove it (the weapon's
                      # MinRange, #4372: the bat's 0.61, the bare hand's 0.6), so no shove or stomp of another is sent
                      # (ruling P24-AH; the frame carries no MinRange, the bat's the widest read)
SWING_SKIP_S = UNREACHABLE_S   # wall seconds a target whose shove or stomp the Lua refused or failed is not sent that
                               # skill again (the stomp's floor strike follows instead: ruling P24-AL)
KNOCK_READ_S = 2.0    # wall seconds a shove's `knockdown` true is waited on for the frame's `onFloor` (PZA/1.7.1, 9 fix
                      # 12: the result is read off the knocked-down state at the hit, onFloor follows about a second
                      # later; a judgment, two of those): the Fight sends nothing meanwhile and stomps on the first
                      # frame reading it fallen (ruling P24-AV: E10's a59, sent on the knockdown alone, was rejected
                      # `not valid`); before P24-AV the knockdown read the target downed and the stomp went at once
STOOD_STOMPS = 2      # stomps at one target failed `stood` (it rose before the stomp landed) after which the floor strike
                      # follows (ruling P24-AV: "fallen again, one more stomp, then the floor strike")
PULL_R = FIGHT_REACH + KEEP_R   # tiles: the pull of a lone chaser ends, the stance taken, once it is this near (ruling
                      # P24-AN: "until the chaser alone is within FIGHT_REACH + KEEP_R"; 4.5)
EDGE_HOLD_TICKS = 6   # planner ticks a zombie that left the listing (beyond LISTED_R, AIM_R's 12) is held in the seek's
                      # and the pull's reads at its last listed square (ruling P24-AU: 3 s at the drivers' PLANNER_HZ 2;
                      # E10's run 4 flipped seek, pull, seek seven aims running as a group at the edge came and went)
# the threat branch's (`threat.Threat` and its mixins; moved from `planner/threat.py` at Plan 25 Task 2)
FLEE_HEALTH = 40.0        # under it a threat is fled, never fought
FLEE_HEALTH_PAIR = 60.0   # two or more threats are fled under this health
FLEE_HEALTH_FLOOR = 20.0  # under FLEE_HEALTH and at or above this, one threat within DANGER_R is fought by the shove
                          # and the stomp (ruling P25-S, Plan 25 Task 10): a judgment; E13 held its health between
                          # 30.32921600341797 and 32.70201110839844 from game minute 712 to the cap and fled its last 15
                          # fights under FLEE_HEALTH; below this the flee stays
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
FINISH_R = 5.0            # tiles: the farthest struck target downed the flee's finishing stomp is sent at (P24-AQ,
                          # Task 32 fix 1, the review's major 5 correcting ruling R3's 4.0): the Lua's stomp takes a
                          # target within K.ATTACK_R 6 (`swingCheck`) and walks in to under STOMP_R 0.5 for at most
                          # STOMP_APPROACH_MS 4000, which at a walk of 2.04 to 2.08 tiles a second (#4197) covers the
                          # whole 6; 5.0 keeps a tile under ATTACK_R. E9's 7474 was first read fallen on a decision tick
                          # at 4.62 tiles (HEAD replay line 334, the nearest standing 6.49), beyond 4.0; its 7488 never
                          # qualifies at any reach (a standing zombie within DANGER_R on every tick it lay, 141 to 150).
                          # The floor strike (a swing from where the player stands) stays at FIGHT_REACH
DRAG_DOWN_N = 3           # attackers the drag-down kills at (#4290, #4291: the fixture's sandbox Strength 2; two at
                          # Strength 1): at DRAG_DOWN_N - 1 the branch leaves any fight for the group's flee (P24-A (h))
FLIP_MIN_S = 5.0          # wall seconds a flee walk runs before a fight's walk may supersede it (P23-AM 1)
GROUP_R_N = 3             # zombies within GROUP_NEAR_R that make a group: steered from, not cornered (P23-AM 4, AP 2)
GROUP_NEAR_R = 3.0        # tiles: ... (P23-AP 2: a third zombie this near; P23-AM 4 read 1.5, CORNERED_R)
GROUP_HOLD_N = 4          # held threats (within the hold radius) that make a group too (P23-AP 2)
STUCK_RETRY_S = 2.0       # wall seconds after a stuck read before a stuck corner against a group tries a leg (P23-AP 2)
STUCK_RETRY_GROUP_S = 1.0  # ... with GROUP_R_N within CORNERED_R or GROUP_HOLD_N held, whatever the nearest reads
                          # (P24-A fix 1 (1), a ruling: F1's corner read stuck at 537 held on against four)
# survival iteration 13 (Plan 25 Task 3, rulings P25-A to P25-F; E11 and F3, rows #4402-#4427)
SHOVE_REPEAT_S = 3.0      # wall seconds after a shove at a target in which no second shove goes at it (P25-A): a shove
                          # read no knock-down is answered by the swing or the break instead. E11's seven shoves at its
                          # two cornered zombies came 2.004 to 4.928 s apart (lines 396-436), six reading `knockdown`
                          # false (#4406); 3.0 takes in the three sent 2.0 to 2.6 s after the one before, a judgment
                          # (the shove's swing and its act line take about a second: the window holds one swing after)
HOLD_SPAN_MIN = 15.0      # game minutes the endurance hold may stand before it releases on a quiet rise under
                          # ENDURANCE_RELEASE (P25-C): F3's hold set at game minute 648 at 0.7267035841941833 and
                          # never read above 0.80 (#4415); rest gives back 0.003-0.005 a game minute
                          # (ENDURANCE_RELEASE's note), so F3's 0.0733 to the release line takes 14.7 to 24.4 quiet
                          # minutes; 15 releases F3's hold by game minute 663 in a quiet replay (`test_survive_t`), its
                          # endurance then 0.7489942908287048 (the runs kept it there), a judgment
HOLD_QUIET_S = 20.0       # wall seconds with no zombie within DANGER_R before that release (P25-C): about 5.4 game
                          # minutes at F3's 3.7 s a game minute; STAND_MAX_S's and UNREACHABLE_S's span, a judgment
DOOR_WALK_S = 20.0        # wall seconds a doorway stand's walk may leave the player within STUCK_MOVE whatever the
                          # zombies before it stalls (P25-E: E11's walk toward building 2's door stood 2.101 s 11.44
                          # tiles from it against a fence, dropped by WALK_STALL_S with a zombie at 5.36, #4409; with
                          # none within DANGER_R the step waited the Lua's own stuck time); STAND_MAX_S's span, a
                          # judgment
FENCE_BACK_R = (1.5, 2.5)  # tiles from a known hoppable edge the fence wait stands (P25-F, the guides notes § 9
                          # change 4: "one to two tiles back from the fence, out of the lunge"): a zombie landing half
                          # a tile past the fence is then 1.0 to 2.0 tiles off, within FIGHT_REACH, and the stand at
                          # most KEEP_R back
# survival iteration 14 (Plan 25 Task 8, rulings P25-J to P25-M; E12, rows #4428-#4439)
SHOVE_BREAK_N = 3         # missed shoves in a row at one lone target after which the Fight breaks away (P25-L): E12's
                          # doorway stand sent twelve shoves from game minute 694, the eleven done each reading
                          # `knockdown` false, while the bites took the bleeding parts from 1 to 7 (#4431); the window
                          # is SHOVE_BREAK_N x SHOVE_REPEAT_S, a judgment (three rolls of the knock-down, #4373)
# survival iteration 17 (Plan 26 Task 2, rulings P26-A to P26-E; E16, F7 and F5)
INSIDE_CROWD_N = 2        # zombies within POINT_BLANK_R (or `me.attackers`, if more) at which an `inside` corner shoves
                          # and never swings (P26-C: from E16's stand's `inside` end the corner sent five attacks with
                          # two zombies on the door's inside square, four of which swung, one lowering its target)
# survival iteration 18 (Plan 26 Task 7d, ruling P26-L; F8)
STAND_CROWD_N = 4         # standing held zombies within DANGER_R at which the stand ends `crowd` (P26-K, P26-K2):
                          # E17's stand held six within DANGER_R from its line 370, none inside, ended `inside` at 380
                          # and the first bite came 2 game minutes later; E16's held five, then six; E14's five came in
                          # through the window square beside its door; the pick takes at most DOOR_STAND_N standing
SHOVE_FAIL_N = 3          # missed shoves at one lone standing target (`shove.FightShove._missed_n`) after which a Fight
                          # under the `wounded` reason swings in the shove's place (P26-L1, which amends P25-I: a lone
                          # standing zombie that resisted SHOVE_FAIL_N shoves takes the divided swing, #4370, #4373,
                          # #4374): F8's last fight (`f_goals_9-20261102-181937`) shoved its lone 28762 six times, each
                          # done `knockdown` false, and never swung; E11's corner shoved its two seven times, six
                          # missing (#4406). P25-L's break after SHOVE_BREAK_N misses is the other reading of the same
                          # count: at most SHOVE_BREAK_N, or the break would take the count first and reset it
# survival iteration 19 (Plan 27 Task 1, rulings P27-A to P27-E; E18 `e_day_18-20261102-224036`, F9, F8)
FINISH_CLEAR_R = 3.0      # tiles: a flee's finish goes with no standing zombie this near the character nor the fallen
                          # one (P27-A, in place of P24-AQ's DANGER_R): E18's line 1649 ran the `strain` flee from
                          # 30744, knocked down 2.5339841792960844 tiles off with no standing zombie within DANGER_R,
                          # and its line 939's `many` flee from 30452, fallen 2.053499872133796 off; HOLD_BREAK_R's and
                          # GROUP_NEAR_R's 3.0, a judgment (the guides put the stomp at 0.3 strain, a second's work)
MANY_TAIL_TICKS = 4       # consecutive ticks with at most one standing zombie within DANGER_R and at most one of the
                          # listed pressing after which a `many` flee episode ends (P27-B): on 168 of E18's 302 `many`
                          # lines and 105 of F9's 169 one zombie or none stood within DANGER_R; four ticks (two seconds
                          # at the drivers' PLANNER_HZ 2) rule out one knock-back's or one frame's dip, a judgment
                          # beside CLOSING_TICKS' three
SPENT_REDRESS_BT = 10.0   # a spent dressing on a part reading `bleeding` false is replaced only at a `bleedingTime` at
                          # or under this (P27-D; the engine's raw wound-time units, DIRTY_RAG_MIN's): E18's neck read
                          # bleeding false under its spent dressing at 15.462026596069336 and 13.89616870880127, and its
                          # two re-dressings each took health (82.34173583984375 to 67.09330749511719 and
                          # 62.200069427490234 to 54.371578216552734)
# Plan 32 Task 5 (the coward rules; Angus watching F17, `f_goals_17-20261108-172833`), set here below the pointed lines
PAIR_SWITCH_R = 0.3   # tiles: with two or more within KEEP_R the Fight's pin moves to another standing zombie only once
                      # it reads this much nearer than the pin ((b), `fight.Fight._pair_pin`; a judgment, REPIN_MARGIN's
                      # 0.3: F17's pair at seq 7493-7499 read 0.97 and 0.99 tiles and traded the target)
STRAIN_ENDURANCE = 0.5   # the frame's stats.endurance at or under which the ENDURANCE moodle reads level 2 (#3926:
                         # level 1 while above 0.5), the real exhaustion the `strain` flee is bounded to ((d),
                         # `threat.Threat._strain_flees`): F17's 158 `strain` lines read the endurance hold alone at
                         # 0.6427835822105408 to 0.7410425543785095, the first level, whose halved swing is the meet's
# survival iteration 20 (Plan 27 Task 5, rulings P27-F to P27-L; E19 `e_day_19-20261103-072904`, F10
# `f_goals_11-20261103-075140`)
STUCK_MARK_MIN = 30.0     # game minutes a square a goal walk ended `stuck` on unmoved stays marked with its route's
                          # first edge (P27-F): E19 stood 141.47037506103516 game minutes on the gate square, its four
                          # walks from it (game minutes 640, 643, 710 and 776) each `stuck` unmoved, the source resting
                          # 17 times between; DOOR_RETRY_MIN's 30, a judgment (the controller's number)
STUCK_LEAVE_R = 10.0      # tiles from a marked square the scripted source's walk away from its edge goes (P27-F, with
                          # no building to walk back to): SCAN_R's place, the next place over, a judgment (the brief
                          # names the walk and no distance)
FALLEN_SEEK_TICKS = 4     # consecutive ticks a standing fight's target reads fallen beyond FINISH_R before it is walked
                          # to or left (P27-H): E19's fight 2 stood eleven stance legs, 20.437649965286255 s, at 20951
                          # lying 8.683652011883524 to 11.861148063389683 tiles off; MANY_TAIL_TICKS' four (two seconds
                          # at the drivers' PLANNER_HZ 2) rule out one frame's fall, the controller's number
SHOVE_CLOSE_TICKS = 6     # consecutive ticks a shove-only Fight's lone chaser holds beyond POINT_BLANK_R within
                          # DANGER_R before it is walked to (P27-J): F10's hold fight at 27031 (lines 656-681) faced it
                          # at 2.815809041061751, then 3.1712611313783534 to 3.393632390072648 tiles for twenty lines
                          # while five aim legs went; three seconds at the drivers' PLANNER_HZ 2, past a stance leg's
                          # AIM_LEG_S, the controller's number
# survival iteration 20, fix 2 (Plan 27 Task 5 fix 2, rulings P27-M to P27-O; E20 `e_day_20-20261103-121340`)
ATTACK_MARGIN = 0.35      # tiles past the frame's `weapon.reach` within which the standing fight's attack goes at a
                          # standing zombie (P27-M): E20's a190 went at 1.8161174585612616 tiles, 0.6911174585612616
                          # beyond the bat's reach 1.125, and the Lua's attack ran the character 1.762922801715824 tiles
                          # into zombie 3189, which bit 1.799 s after the line's frame; the controller's number
WALK_DONE_R = 1.0         # tiles: the Lua's walkTo ends `done` within this of its target (PZAgent_Skills.lua K.DONE_R),
                          # so the advance's walk to the reach (P27-M) targets the point this much nearer the zombie
STALL_R = 1.0             # tiles: a goal ended `goal budget` with the character's displacement since it began under
                          # this is a stall (ruling P29-B, GOAL_STALL: `goal_runner.GoalRunner._stall`): F13's stall
                          # (`f_goals_14-20261105-021722`, #4633, #4634), the four ExploreTowards begun at the gate
                          # (10747, 10642) on decision lines 823 to 1405, each ending `goal budget` 90.00974249839783
                          # to 90.52074551582336 wall seconds on with the character 0.0 tiles from where it began;
                          # WALK_DONE_R, a judgment (the spec's number)
# survival iteration 21 (Plan 28 Task 3, rulings P28-A to P28-E; F11 `f_goals_12-20261103-144240`)
WOUND_RESERVE = 1         # clean dressings (bandages and clean rags) the wound step keeps for a bleed: a part reading
                          # `wound`, not bleeding, is dressed only while more than this are held (P28-A): F11's
                          # scratched parts 4, 6 and 8 never bled and fell to 0, 9.163058280944824 and 51.79861068725586
                          # undressed while 63.577457427978516 of its health fell on frames reading no bleed and no bite
                          # (#4581, #4585); one kept for the next bleed, the stock's rip (RAG_STOCK 2) refilling it, a
                          # judgment
CIRCLE_TURN = 45.0        # degrees the stance's `back` leg from a lone standing zombie within KEEP_R turns off the
                          # straight away heading (P28-E, E20's candidate, #4576: the stance's legs walked straight
                          # toward or away from the target): half of STEER_TURNS' 90, the arc keeping the target within
                          # the swing's reach while it follows, a judgment (the spec's number)
# survival iteration 22 (Plan 28 Task 7b, cut 1 of the maneuver layer: the melee reflex of PZA/1.8, `maneuvers.Melee`)
MELEE_RELEASE_R = KEEP_R + KEEP_MARGIN   # tiles beyond which the melee ends lost, out of range (its `releaseR`): the
                          # running backpedal's own give-way past KEEP_R (`Fight.busy`), the ladder's legs taking the
                          # target there
MELEE_BACKOFF_TICKS = 10  # planner ticks after a melee ended `interrupted`, `timeout` or `no target` in which no melee
                          # goes at that target, the ladder's command going instead (fix 1, review-t7b m2): Survive's
                          # FAILED_COOLDOWN_TICKS, the cooling of a failed command, mirrored (survive.py imports this
                          # module, so it cannot be read from there)
# the meet (PZA/1.10, Plan 31 Task 2: the melee reflex's arguments; the spec `2026-11-05-plan-31-the-rebuild-design.md`
# section 4 items 1, 2 and 2b; the swing jar read's rows #4678-#4691, `docs/platform/agent.md`)
FACE_R = 3.0              # tiles: the melee's `faceR`, inside which the stance is released and the target faced every
                          # tick until the press: the body turns toward a written facing at about 206 degrees a second
                          # walking and an idle turn's clip runs about 0.83 s for 90 degrees (#4689 and the review's
                          # arithmetic), while a chaser closes at about 1.6 tiles a second (the spec's section 1), so 3
                          # tiles leave the turn (3.0 - 1.125) / 1.6 = 1.17 s before the bat's margined reach of 1.125
                          # (fix 1, review-t2 F8); the spec's number
PRESS_ANGLE = 41.40962210927086   # degrees: the melee's `pressAngle`, the most the look may lie off the bearing at a
                          # press: acos(0.75), the bat's MinAngle 0.75 (weapon.txt:6701), the dot band the hit list
                          # holds a target in at the press (#4591: an empty list makes the attack a MISS) and at the
                          # collision (#4681), inside the bite's facing skip's 0.7 (#4688)
PRESS_LO = 0.0            # tiles: the melee's `pressLo`, the least predicted distance at the collision a swing is
                          # pressed at: the collision's rebuild tests the range and MaxRange, never a lower distance,
                          # and never MinRange (#4681, #4682); MinRange binds the press and the swing's entry only, the
                          # Lua's own test
FLOOR_R = 1.0             # tiles: the melee's `floorR`, the floor swing's distance to a fallen target's head: the floor
                          # attack's line reaches WeaponLength + 0.5 (#4679), the bat's WeaponLength 0.5 (weapon.txt:6716)
HEAD_AIM = False          # the melee's `headAim` (fix 1, review-t2 F4, the controller's ruling): the finish aimed at
                          # the fallen zombie's head estimate (the frame's headX and headY; the floor line tests the
                          # head bone first, x3, #4679) only once its lying direction is calibrated, on the first arena
                          # trial's shots of a finish (the frame's headX and headY against the body on the shot, the
                          # trial's --seen lines): no row supports the direction, and a reversed estimate aims the line
                          # at the calves and feet (x0.05, #4679), worse than the zombie's position (the spine, x1)
HANDBACK_R = 2.0          # tiles: the melee's `handbackR`, inside which another standing zombie ends a finish handback
                          # and beyond which none breaks it (F15's two knock-downs were lost to `pair` flees from zombies
                          # beyond it, the spec's section 1); the spec's number
SHOVE_SEND_R = 0.9        # tiles: the melee's `shoveR` (Plan 28 Task 7e, ruling P28-H 1), the shove sent inside its
                          # reach, not at its edge: the engine's reach SHOVE_R 1.1 (to the nearest of head, pelvis and
                          # position, #4592) read as a bound, not a target; E22's eight shoves at 1.068 to 1.100 tiles
                          # (`e_day_22-20261105-004919`, the fight at game minutes 611 to 621) knocked nothing down nine
                          # bites in a row, against F11's and F12's at 0.16 to 0.98 that knocked down 8 of 33 and 8 of
                          # 36; SHOVE_R stays the planner's refusal bound, the controller's number
FLEE_HEAD_R = 0.3         # tiles: a flee walk's observed heading (the character's displacement since its send) is read
                          # once it reaches this (ruling P29-H', Plan 29 Task 2, `flee.Flee._held_ahead`): F13's fight 2
                          # (`f_goals_14-20261105-021722`) moved 0.058 tiles at -117 degrees on its turn-in frame (seq
                          # 3155) and 0.377 at 14.9 degrees by decision line 412 (seq 3159), so under it the turn-in
                          # would read as the heading; FLEE_CLOSE_TICKS (the spec's closing count) is not added
# survival iteration 24 (Plan 30 Task 3, rulings P30-A to P30-F; the spec `2026-11-05-plan-30-the-intent-design.md` § 1)
EXPLORE_HOP_MIN = 12.0    # tiles: an ExploreToward answer nearer than this is extended along its line (ruling P30-B,
                          # `goal_policies.hop_target`): F14's model hops (`f_goals_15-20261105-092752`, decision lines
                          # 196 to 274, the spec's § 1 reading 2) ran 1 to 6 tiles, each ended in a 7 to 14 s wait with
                          # the character standing over calls of median 4.60 s; a walk of 12 tiles outlasts a median
                          # call at the walk's pace, the spec's number
DOOR_HELD_R = 4.0         # tiles: a zombie behind a closed door, a locked gate or a window this near is a decision
                          # (ruling P30-C, `door_held.ThreatDoorHeld`): F14's 32307 chased at 0.91 tiles behind the
                          # locked gate (10732, 10642) on decision lines 146 to 192 and its 32448 stood 0.90 tiles
                          # behind the door (10770, 10633) on line 1081, while the Fight read the line only within
                          # FIGHT_REACH 2.0 (F14's 32308 behind a window at 2.005 tiles, lines 281 to 315); twice that
                          # reach, the spec's number
DOOR_POST_PACE = 2.0      # tiles a second the stance's leg to the door's post is timed at (P30-C): the walk's own pace
                          # (the Lua's walk, the fake mover's WALK_SPEED), so a slower stance walk falls short of the
                          # post and is re-aimed, never carried past it into the door; a judgment
STILL_S = 6.0             # wall seconds a held zombie's steady distance with the character unmoved resolves (ruling
                          # P30-E, `still.ThreatStill`): F14's melee stood at 32308, 2.005 tiles off, on decision lines
                          # 281 to 315 (`f_goals_15-20261105-092752`; the spec's 16.5 s), seven melee sends 2.5 s apart
                          # (lines 281, 286, ... 311); two and a half sends of nothing, the spec's number
STILL_DRIFT_R = 0.3       # tiles the held zombie's distance may drift from the still read's start (P30-E): F14's read
                          # 2.1849812857308732 then 2.0050714015960693 for the whole stand; the spec's number
STILL_MOVE_R = 1.0        # tiles the character may move from the read's start (P30-E): "unmoved under a tile", the
                          # spec's number (F14's character stood at (10743.74, 10638.49) throughout)
BLEED_FAST = 2.0          # part health a game minute: a dressing on a part falling faster rides through a flee from a
                          # zombie beyond KEEP_R (ruling P30-F, `threat.Threat._dress_waits`): E23's neck bite
                          # (`e_day_23-20261105-095110`, game minute 594 on) took the health from 98.90239715576172 to
                          # 49.206119537353516 over 3.7356948852539062 game minutes (#4648), its part 9 falling at the
                          # rule's own clock (`World.world_minutes`) from 98.43199920654297 (state.log seq 2015, minute
                          # 174.045296) to 55.45134353637695 (seq 2241, 177.780991), about 11.5 a game minute, 12.40 at
                          # most over a one-minute window (seq 2080 to 2160; fix 1, review-t3 m7: the integer `gameMin`
                          # read 14), while two riding dressings were superseded by the flee's legs before the third
                          # landed; a slow bleed (a scratch) falls under 1; the spec's number
BLEED_WINDOW_MIN = 1.0    # game minutes of a part's health samples the bleed's rate reads (P30-F, `_bleed_rate`): one
                          # game minute, the rate's own unit, a judgment
BLEED_SPAN_MIN = 0.2      # game minutes the samples must span before a rate is read (P30-F): a planner tick or more
                          # at E23's pace (decision lines 238 to 262 over game minutes 594 to 598, about six a game
                          # minute), a judgment
SNEAK_R = 8.0             # tiles: a zombie listed this near with no target makes the gait the sneak's (ruling P30-D,
                          # `sneak.SneakGait`): the jar read's footsteps (#4661: 7 tiles upright, 4 sneaking) plus one
                          # tile, beyond the 4.5 tiles inside which sneaking spots about 2.6 times better at Sneak 0
                          # or 1 (#4657); no live case yet (the first sneak session is F15), the spec's number


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
    and within AHEAD_CONE of its bearing. A zombie with no position, or the target at the player's own position, is
    none; ruling P24-AY (the deferred minor 7 of review-t32-fix1: E9's line 344 dropped the fight for 7489, read fallen
    11.69 tiles behind the target) a fallen one (`on_floor`) is none either: it is no group arriving."""
    mx, my = me_xy(world)
    tx, ty = z["x"] - mx, z["y"] - my
    td = math.hypot(tx, ty)
    if td == 0.0:
        return []
    cos_cone = math.cos(math.radians(AHEAD_CONE))
    out = []
    for oid, o in world.zombies.items():
        if oid == zid or o.get("x") is None or o.get("y") is None or on_floor(o):
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


def arm_stiffness(world):
    """Ruling P24-AT: the larger of the frame's two arms' stiffness (`body.strain` {l, r}, PZA/1.7: each the largest
    `getStiffness()` of its side's three arm parts, #4369) when both read numbers, else None (a frame before PZA/1.7)."""
    s = (world.body or {}).get("strain")
    if not isinstance(s, dict):
        return None
    v = [s.get(k) for k in ("l", "r")]
    if not all(isinstance(x, (int, float)) and not isinstance(x, bool) for x in v):
        return None
    return max(v)


def on_floor(z):
    """Zombie record `z` lies on the floor (PZA/1.7's `onFloor`: knocked down, or crawling); absent is standing."""
    return z.get("onFloor") is True


def standing(world, r, skip=()):
    """The listed zombies within `r` tiles of the player not lying on the floor (`on_floor`), the ids in `skip` (read
    dead) left out."""
    return [z for zid, z in world.zombies.items() if zid not in skip and z.get("x") is not None
            and z.get("y") is not None and not on_floor(z) and zdist(world, z) <= r]


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


def exit_plan(world, threats, refused=(), trans=True, windows=False, walkable=True):
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
    `_beyond`'s (ruling P24-AS). Ruling P26-A (`windows`, `Threat.WINDOW_EXIT`): the building's windows are ways out too
    (`night.window_exits`), each passing the same checks on its outside square but `_beyond` (its climb lands on the
    outside square: no walk ends short of it, so a window into a closed pocket is taken as a way out, which the next
    flee's steer answers: ruling P26-7b), ranked after every door and opening that passes (the rank
    `(door marked, window, smash, distance, outer, inner)`: a window is the way out only when no door or opening is, and
    an unlocked one goes before a locked one at any distance, ruling P26-7d, as `goals.window_pick` ranks); a
    window's record carries `window` and `smash`, its `target` its inside square (`inner`, the walk's end before the
    climb) and its `step` "window" (`flee.Flee._window_step`), `sent` False. Ruling P26-I (`walkable`,
    `Threat.WINDOW_INNER`): a window whose inside square cannot be stood on is no way out (`night.window_exits`).
    Ruling P29-H' (fix 1, review-t2 M2): an exit whose door, or an opening's outside square, the World marks `walled`
    (`flee.Flee._held_ahead`'s cut walk, `World.mark_door`) is refused while the mark stands, DOOR_RETRY_MIN."""
    N = _night()
    s = world.map.get(N.player_square(world)) or {}
    b = s.get("building")
    if s.get("room") is None or b is None:
        return None
    ts = [z for z in threats if z.get("x") is not None and z.get("y") is not None]
    me = me_xy(world)
    marked = world.marked_doors()   # Task 18 fix 1, major 4: a marked door stays a way out, ranked after the others
    walled = {sq for sq in marked if world.door_marks[sq][1] == "walled"}   # P29-H' fix 1: a cut exit, refused
    best = None
    for e in N.exits(world, b, me_floor(world), windows, walkable):
        if e["outer"] in refused or e["outer"] in walled or e["door"] in walled:
            continue
        c = centre(e["outer"])
        if any(math.hypot(z["x"] - c[0], z["y"] - c[1]) < zdist(world, z)
               or _in_tube(me, c, (z["x"], z["y"]), EXIT_CLEAR_R) for z in ts):
            continue
        window = e.get("window") is not None
        if not window and _beyond(world, e["inner"], e["outer"], trans) is None:
            continue
        rank = (e["door"] in marked, window, e.get("smash", False), math.hypot(c[0] - me[0], c[1] - me[1]), e["outer"],
                e["inner"])
        if best is None or rank < best[0]:
            best = (rank, e)
    if best is None:
        return None
    e = best[1]
    if e.get("window") is not None:   # P26-A: the walk to the window's inside square, then its climb
        return dict(e, building=b, target=e["inner"], step="window", opened=False, sent=False)
    return dict(e, building=b, target=_beyond(world, e["inner"], e["outer"], trans), step="walk", opened=False)


def exit_kind(world, e):
    """What the way out `e` (an `exit_plan` record) crosses (ruling P25-W's `doorway_exit`): "window" for a window's
    (ruling P26-A, `night.window_exits`), "door" for a closed exterior door to open (`door`) or an opening across a
    door's edge (an open door, `door_edge`), else "opening" (a step out with no door on it)."""
    if e.get("window") is not None:
        return "window"
    if e["door"] is not None or door_edge(world, e["inner"], e["outer"]):
        return "door"
    return "opening"


def door_edge(world, a, b):
    """The edge between two orthogonally adjacent squares `a` and `b` holds a door: the square keeping that edge (a
    square keeps its own north and west edges, `World._window_edge`'s read) carries a `door` record and that edge's
    `edgeN`/`edgeW` reads true."""
    if b[1] != a[1]:
        holder, field = (a, "edgeN") if b[1] == a[1] - 1 else (b, "edgeN")
    else:
        holder, field = (a, "edgeW") if b[0] == a[0] - 1 else (b, "edgeW")
    s = world.map.get(holder) or {}
    return s.get("door") is not None and bool(s.get(field))


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


def stand_post(world, way, building, trans=True):
    """The square a doorway stand's walks aim at (ruling P24-AO, Task 32 fix 1, the review's blocker): of the door's
    `way` (`World.door_way`: the room square inside the threshold, the outside square), the square one on from the
    room square away from the outside one, when it is a room square of `building`, not solid (nor `solidTrans` with
    `trans`) and its step from the threshold square not blocked; else None (no stand: the door is closed as today).
    A walk ends `done` within the Lua's DONE_R (1.0) of its target: E9's enter to the threshold square's own centre
    (10711.5, 10596.5) ended 0.84 tiles off it, on the outdoor door square (10712, 10596), open on three sides; to the
    square beyond (10710.5, 10596.5), 1.5 tiles from the door's edge, it ends at least half a tile inside it, as
    `_beyond` reads for an exit."""
    inner, outer = way
    deep = (2 * inner[0] - outer[0], 2 * inner[1] - outer[1], inner[2])
    s = world.map.get(deep)
    if (s is None or s.get("room") is None or s.get("building") != building or s.get("solid")
            or (trans and s.get("solidTrans")) or world.blocked(inner, deep)):
        return None
    return deep


def on_post(world, building):
    """The player stands on a room square of `building` (the doorway stand's post: the threshold square inside or one
    beside it, never the outdoor door square of a door on a south or east wall)."""
    s = world.map.get(_night().player_square(world)) or {}
    return s.get("room") is not None and s.get("building") == building


def adoptable(world):
    """The building the player stands in has an exterior door on the player's floor (`Flee._adopt` can adopt it), a
    marked one included (read from inside: Task 18 fix 1, the review's major 4)."""
    N = _night()
    s = world.map.get(N.player_square(world)) or {}
    b = s.get("building")
    return (s.get("room") is not None and b is not None
            and bool(N.exterior_doors(world, b, me_floor(world), marked=True)))


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


def __getattr__(name):
    """`Fight` and `Flee` by their old module (Plan 24 Task 36 moved them to `planner/fight.py` and `planner/flee.py`):
    the frozen drivers (`x5_combat.py`, `x5_combat_2.py`, never edited after their runs) import `Fight` from here.
    Read at the access, so neither module is imported while this one loads (both import it). `pull_from` likewise
    (Plan 25 Task 2 moved it to `planner/pull.py`, which imports this module)."""
    if name == "pull_from":
        from agent.base.planner.pull import pull_from
        return pull_from
    if name == "Fight":
        from agent.base.planner.fight import Fight
        return Fight
    if name == "Flee":
        from agent.base.planner.flee import Flee
        return Flee
    raise AttributeError("module %r has no attribute %r" % (__name__, name))


# Plan 33 Task 3 (the group's entry and the drag guard; F18, `f_goals_18-20261108-235005`: three standing zombies
# walked in while the finish stalled and the drag-down guard sent five run steers under hit reactions into a zombie at
# the side; `group.ThreatGroup`). At the end of the module so that Task 2's constant after KEEP_R moves none of them.
WALL_R = 1.5          # tiles: a wall, a fence, a door or a solid square this near the player's back keeps the stand
                      # against a closing pair (GROUP_LEAVE: the group cannot close round a back to a wall)
GROUP_ENTRY_R = 6.0   # tiles: GROUP_LEAVE counts the closing standing zombies this near (Plan 33 Task 3 fix 1: DANGER_R's
                      # value, its own constant; GROUP_NEAR_R left a half-tile window outside KEEP_R)
# Plan 33 Task 3 fix 3 (round two, trial 1: the leave at two closing zombies left the pairs Plan 32's composition fought
# and killed under PAIR_NEAREST, 3 kills against 7 to 11; the controller's ruling 2026-11-09 03:11)
GROUP_LEAVE_N = 3     # standing zombies closing within GROUP_ENTRY_R that GROUP_LEAVE leaves (DRAG_DOWN_N's count: a pair
                      # is fought, a trio is left before it closes)
# Plan 33 Task 3 fix 3 addenda (round two, trial 2 and Angus's fighting retreat, memory `fighting-retreat`): the leave is a
# fighting retreat, never a run; a known door is walked to only when this near (a long walk turns the back on the group)
LEAVE_DOOR_R = 6.0    # tiles: GROUP_LEAVE walks to a known door whose approach square is this near, else the retreat
# Plan 33 Task 3 fix 4 (round three, trial 3, `x_trial-ladder-20261109-042558`: on street-1 the retreat's standing
# count within GROUP_ENTRY_R rose to eight and the character died under the drag guard's runs, where Plan 32's `many`
# run before the group closed read 9 to 11 kills; the controller's ruling 2026-11-09 04:45: a backpedal does not outpace
# eight, so the retreat is the leg for GROUP_LEAVE_N to RETREAT_MAX_N standing and the `many` run above it)
RETREAT_MAX_N = 4     # standing zombies within GROUP_ENTRY_R the fighting retreat backpedals from; above it the leave's
                      # leg is the `many` run (GROUP_LEAVE), the retreat resumed when the count falls back to it
# Plan 34 Task 5 (spec section 3.5; F19, `f_goals_19-20261109-060929`: the melee at the first wound was sent off a frame
# 0.970 s old, the line 1.435 s after the one before, the session's median lag 0.057 s, its GUIDE.md section 2)
FRAME_STALE_S = 0.5  # seconds: a decision line whose frame is older than this (its `wall` less the frame's `wallMs`)
                     # carries `frame_age`, so the write-up reads what held the loop; no rule reads it
# Plan 34 Task 2 (LEAVE_DOOR_RACE; F19, `f_goals_19-20261109-060929`, GUIDE.md section 3 "The door": the leave's leg
# turned `door` on decision line 1595 with the nearest standing zombie at 0.37 tiles; the approach, the open, the enter
# and the close took about three seconds, and the close shut the door from outside with 12431 at 0.60 tiles)
DOOR_RACE_R = 3.0     # tiles: the leave picks no new door with the nearest standing zombie within DANGER_R this near
                      # (the walk to the door, the open, the enter and the close take about three seconds)
DOOR_ABORT_R = 1.0    # tiles: a running leave door plan before its close is dropped with a standing zombie this near
# Plan 34 Task 3c fix 1 (the trials `x_trial-ladder-20261109-142418`, lines 343 and 358: POINT_BLANK_FIGHT pinned 8836
# at 2.455 tiles and 8847 at 2.18 over the `health` flee, each walked in on and shoved at, 27 hit runs in the trial; and
# `x_trial-ladder-20261109-141434`, line 392: 13837 pinned at 2.24 over `many`; P31-T, not evidence)
POINT_BLANK_OVER_R = 1.5   # tiles: under a `many` or `health` flee reason POINT_BLANK_FIGHT fights only a standing
                           # zombie this near (already on the character); beyond it the flee stands (KEEP_R otherwise)
# Plan 35 Task 2 (the footwork; the spec's §§ 3.1 to 3.3): the melee's `work` arguments the Fight sends with every
# melee (`dispatch.FightDispatch._melee_inputs`, `maneuvers.melee.WorkInputs`)
WORK_R = 3.5               # tiles: the reflex reads the standing zombies this near for the footwork's heading (`workR`)
WORK_CRAWLER_R = 1.2       # tiles: a crawler this near repels the heading hard and is never stepped onto (`crawlerR`)
WORK_BAND_LO = 0.4         # tiles: the step back goes while the nearest standing is nearer than the reach less this
                           # (`bandLo`)
WITHDRAW_RESEND_DEG = 30.0   # degrees: the withdraw bias re-sends the running melee only once its heading leaves its
                             # WITHDRAW_RESEND_DEG sector (`maneuvers.melee.WorkInputs.behaviour`)
# Plan 36 Task 3 (the engagement picker; the spec `2026-11-11-plan-36-the-engagement-design.md` § 3.3; F21,
# `f_goals_21-20261111-150552`: two bites from 76 to 116 degrees off the body while the leave's hold kept the reflex
# pressing): the pull to a line and the cone trigger (`group.ThreatGroup._pull`), the withdraw the melee carries
PULL_SPREAD_DEG = 60.0     # degrees: two or more standing zombies closing within GROUP_ENTRY_R whose bearings spread more
                           # than this start the pull (the withdraw into the widest gap of their bearings), § 3.3
PULL_STOP_DEG = 45.0       # degrees: the running pull stops once their spread falls under this (or the nearest stands
                           # within the reach): the vector dropped and the reflex standing, § 3.3
CONE_HALF_DEG = 60.0       # degrees: the engagement cone, the pinned target's bearing this far either side; the cone's
                           # pull stops once its flanker is inside it, § 3.3
CONE_OFF_DEG = 90.0        # degrees: a standing zombie closing within CONE_TRIGGER_R more than this off the pinned
                           # target's bearing (30 degrees past the cone's edge) starts the cone's pull, § 3.3
CONE_TRIGGER_R = 4.0       # tiles: the cone's pull reads flankers this near (before contact), § 3.3
RETREAT_HOLD_R = 1.0       # tiles: Task 3 fix 1b, the armed fighting retreat's withdraw holds while three stand within
                           # GROUP_ENTRY_R plus this, closing or not (a column keeping pace reads flat distances)
