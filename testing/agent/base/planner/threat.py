"""The threat branch of `survive.Survive` (Plan 22 Task 10's priority list, its first branch): the held list, the
flee reasons and their hysteresis, the sought fight, the corner, the doorway stand, the finish of the fallen, the care
yield and the decision the Fight and the Flee execute (`_threat`, `_decide`). Moved out of `survive.py` at Plan 24
Task 36 (a pure move: every rule, switch and constant unchanged), as the mixin `Threat` that `Survive` derives from;
its state is `Survive`'s own, set in `Survive.__init__`, and `survive.py`'s module docstring stays the record of every
rule here (the rulings by iteration, P23-AG to P24-AS). Plan 25 Task 2 moved parts of it into mixins `Threat` derives
from (a pure move): the hold and spent reads (`hold.Hold`), the engage (`engage.Engage`), the pull read
(`pull.ThreatPull`), the care yield (`care_yield.CareYield`), the doorway stand's side (`doorway.DoorwayStand`) and the
`many` flee's finish (`finish.ThreatFinish`); the constants are `policies.py`'s, imported here. Plan 37 Task 3: the
disposition selector (`disposition.Disposer`) owns the open-ground rows in contact (`_threat_plan`'s row before the
leave's) and the Fight's work inputs (`_decide`), `planner/disposition.py`'s docstring the record.
"""
from agent.base.planner.care import CARE_STILL_TICKS
from agent.base.planner.care_yield import CareYield
from agent.base.planner.crawler import is_crawler
from agent.base.planner.disposition import Disposer
from agent.base.planner.door_held import ThreatDoorHeld
from agent.base.planner.doorway import DoorwayStand, stand_ready
from agent.base.planner.edges import ThreatEdge, crossed
from agent.base.planner.engage import Engage
from agent.base.planner.fight import Fight
from agent.base.planner.finish import ThreatFinish
from agent.base.planner.flee import Flee
from agent.base.planner.group import LEAVE_PLAN, ThreatGroup
from agent.base.planner.hold import Hold
from agent.base.planner.policies import (AIM_R, BLEED_FAST, CLOSING_TICKS, CORNERED_R, CORNER_FREE_R, DANGER_R,
                                         DISENGAGE_R, DRAG_DOWN_N, DROP_AT, EDGE_HOLD_TICKS, ENGAGE_R, FIGHT_REACH,
                                         FINISH_R, FLEE_GAIT, FLEE_HEALTH, FLEE_HEALTH_FLOOR, FLEE_HEALTH_PAIR,
                                         FLIP_MIN_S, GROUP_HOLD_N, GROUP_NEAR_R, GROUP_R_N, HOLD_BREAK_R, KEEP_R,
                                         LISTED_R, MANY_LISTED_N, MANY_TAIL_TICKS, MAX_FIGHT, POINT_BLANK_R,
                                         REFIGHT_MARGIN, STUCK_RETRY_GROUP_S, STUCK_RETRY_S, adoptable, blocked,
                                         chasing, exit_plan, in_building, in_reach, line_to, on_floor, others_behind,
                                         seek_allowed, spare, target_id_ok, zdist, STRAIN_ENDURANCE,
                                         POINT_BLANK_OVER_R)
from agent.base.planner.pull import ThreatPull
from agent.base.planner.still import ThreatStill
from agent.base.pza1 import Drop
from agent.base.world import me_xy

SHOVE_ONLY_WHY = {"unarmed": "unarmed_fight", "low": "low_fight", "hold": "hold_fight"}   # the why of each
                         # shove-and-stomp Fight (`Fight.shove_only`: P25-P, P25-S, P27-C)

__all__ = ["Threat", "FLEE_HEALTH", "FLEE_HEALTH_PAIR", "REFIGHT_MARGIN", "MAX_FIGHT", "HOLD_BREAK_R", "CLOSING_TICKS",
           "CORNERED_R", "CORNER_FREE_R", "MANY_LISTED_N", "FINISH_R", "DRAG_DOWN_N", "FLIP_MIN_S", "GROUP_R_N",
           "GROUP_NEAR_R", "GROUP_HOLD_N", "STUCK_RETRY_S", "STUCK_RETRY_GROUP_S", "LISTED_R"]


class Threat(Hold, Engage, ThreatPull, CareYield, DoorwayStand, ThreatFinish, ThreatEdge, ThreatDoorHeld,
             ThreatStill, ThreatGroup, Disposer):
    """The threat branch (the module docstring): `Survive`'s mixin, its switches the replay tests' seams."""

    ENGAGE = True   # ruling P24-X: one or two within ENGAGE_R are sought, a flee turns to fight at the fight's line
    SEEK = True     # ruling P24-X: every fight it engages (the door fight aside) is sought to KEEP_R; both switches
                    # are the replay tests' seams onto the rules before P24-X (`test_replay_decisions.pre_x`). Not
                    # behind them: Task 18's WIDE_TURNS and STEP_PROBE (the flee's wide tiers), which PRE_X proves move
                    # no golden (Task 18 fix 1, the review's minor 13)
    IDLE = True     # ruling P24-AD: an idle zombie counts toward `many` only within DANGER_R; off, every zombie counts
                    # (the replay tests' seam onto the rules before it, `test_replay_decisions.pre_x` with the above)
    STRAIN = True   # rulings P24-AG and P24-AK: a spent character (the arms' strain hold, the endurance moodle, the
                    # tired line) flees `strain` and engages nothing; off, neither is read (the replay tests' seam onto
                    # the rules before Task 27, `test_replay_decisions.pre_ag`)
    PULL = True     # ruling P24-AN: a lone chaser is pulled from the group, never dropped for one behind it
    TRANS = True    # ruling P24-AS: a heading read refuses a `solidTrans` square (each policy's `trans`)
    DOORWAY = True  # ruling P24-AO: a `many` flee against DOOR_STAND_N or fewer standing fights in the doorway; both
                    # switches and TRANS off are the replay tests' seam onto the rules before Task 32
                    # (`test_replay_decisions.pre_an`; P24-AP to P24-AR read what no record carries: `armPain`,
                    # `onFloor`, a part's `bleeding`)
    HOLD_WIDE = True    # ruling R2 (Task 32 fix 1, the review's major 4): every hold kind (arms, endurance, tired)
                        # fights a zombie within KEEP_R as the shove then the stomp, never the swing; off, the arms'
                        # hold alone (P24-AP as Task 32 landed it)
    STANCE_LISTED = True  # Task 32 fix 1, the review's major 6: the stance counts the held zombies standing and
                          # within DANGER_R or chasing (`_stance_count`); off, every held one. Both switches are in
                          # the replay tests' seam onto the rules before Task 32 (`pre_an`)
    PICK_WHY = True  # ruling P24-AX: every `many` line logs `doorway_pick`; off, no such why (the replay tests' seam: a
                     # why on every golden `many` line, no decision moved)
    EDGE = True     # ruling P24-AU: a zombie that left the listing is held in the Fight's pull reads EDGE_HOLD_TICKS
                    # ticks (`policies.Fight.edge_ticks`); off, 0 (the replay tests' seam onto the rule before it)
    OBSERVES_IN_READ = True   # Plan 25 Task 2 (Plan 24's close review, minor 8): every observe of a policy held at the
                              # tick's read (the Night, the Care, the Fight, the Flee) and the threat's bookkeeping run
                              # in `Survive._read`; off, inside `assess` as before (the replay tests' seam, `pre_t2`)
    # survival iteration 13 (Plan 25 Task 3; survive.py's docstring, Survival 14): each switch off is the rule before
    # it, and all of them off (`survive.T3_SWITCHES`) the replay tests' seam onto the goldens before Task 3 (`pre_t3`)
    CORNER_BREAK = True   # ruling P25-A: after a missed shove the swing (one in reach) or the break (two), never a
                          # second shove within SHOVE_REPEAT_S (`policies.Fight._corner`)
    FINISH_FIRST = True   # ruling P25-B: a fallen zombie within FINISH_R stomped before an attack's walk
                          # (`Fight._finish_first`)
    HOLD_RUN = True       # ruling P25-C: the endurance hold's `strain` flee walks with no zombie within DANGER_R, and
                          # the hold releases after HOLD_SPAN_MIN quiet (`hold.Hold._read_endurance`, `_hold_walk`)
    RIDE_WAIT = True      # ruling P25-D: a riding bandage holds a no-swing Fight's sends (`Fight._ride_waits`)
    DOOR_WALK = True      # ruling P25-E: a doorway stand's stalled walk re-routes once, then drops the plan
                          # (`flee.Flee._door_stall`)
    FENCE_WAIT = True     # ruling P25-F: a chaser across a known fence waited for in the stance (`Fight._fence_wait`)
    # survival iteration 14's second half (Plan 25 Task 8; survive.py's docstring, Survival 16): each switch off is the
    # rule before it, all of them in `survive.T4_SWITCHES` (the replay tests' `pre_t4`)
    FINISH_FAR = True     # ruling P25-J: the fallen finished out to FINISH_R with no standing zombie within KEEP_R
                          # (`finish.finish_rule`, `Doorway._finish_post`), and the `pair` flee yields to that finish
                          # (`_pair_finish`)
    STAND_WOUND = True    # ruling P25-K: the doorway stand leaves on a part bleeding since it began (`_stand_wound`)
    SHOVE_BREAK = True    # ruling P25-L: after SHOVE_BREAK_N missed shoves at a lone target the Fight breaks away
                          # (`shove.FightShove._corner`)
    # survival iteration 15 (Plan 25 Task 10; survive.py's docstring, Survival 17): each switch off is the rule before
    # it, all of them in `survive.T5_SWITCHES` (the replay tests' `pre_t5`)
    UNARMED_FIGHT = True  # ruling P25-P: unarmed, one zombie within DANGER_R is fought by the shove and the stomp,
                          # never the swing (`_unarmed_fight`, `Fight.shove_only`); off, every unarmed tick flees
                          # `unarmed`
    LOW_FIGHT = True      # ruling P25-S: under FLEE_HEALTH, at or above FLEE_HEALTH_FLOOR, one zombie within DANGER_R
                          # is fought by the shove and the stomp (`_low_fight`); off, every such tick flees `health`
    SHOVE_BREAK_RUN = True  # ruling P25-T: the break's misses count over the Fight's life, any spacing
                            # (`shove.FightShove._missed_n`, `_lone_break`); off, P25-L's window
    # survival iteration 16 (Plan 25 Task 14; survive.py's docstring, Survival 18): each switch off is the rule before
    # it, all of them in `survive.T6_SWITCHES` (the replay tests' `pre_t6`)
    STAND_DRAG_EARLY = True   # ruling P25-U: the doorway stand's `drag` end at DRAG_DOWN_N - 1 attackers
                              # (`DoorwayStand._stand_drag_n`); off, at DRAG_DOWN_N
    STAND_INSIDE = True   # ruling P25-V: a standing zombie on the stand's room squares, off its door square and not its
                          # target, ends the stand `inside` (`DoorwayStand._stand_inside`); off, no such end
    STAND_EXIT = True     # ruling P25-W: a stand ended `wound`, `drag` or `inside` walks out of the building by its way
                          # out (`flee.Flee.walk_out`), never the close; off, every end but `off` closes the door
    BLOCKED_EDGE = True   # ruling P25-X: a known blocked outdoor edge on the line to a Fight's target, a goal's or a
                          # fill's is routed through its unlocked door or refused (`planner/edges.py`: the Fight's
                          # `blocked_edge` rule, the goals' kit, the water chain); off, iteration 15's seek and walks
    EDGE_OUT_OF_HOLD = True   # ruling P25-X, amended (Task 14 fix 1): a zombie marked for a blocked edge (`edge_marks`)
                              # and read across it is out of the hold (`Survive._within`: the held set, `_released`, the
                              # DANGER_R count the `unreachable` flee reads); off, it counts as before
    # survival iteration 17 (Plan 26 Task 2; survive.py's docstring, Survival 19): each switch off is the rule before
    # it, all of them in `survive.T7_SWITCHES` (the replay tests' `pre_t7`)
    WINDOW_EXIT = True    # ruling P26-A: a building's windows are ways out after its doors and openings
                          # (`night.window_exits`, `policies.exit_plan`, `flee.Flee._window_step`); off, no way out
                          # crosses a window
    STAND_SECOND_EXIT = True   # ruling P26-B: the doorway stand's pick refuses a free door whose building has no other
                               # way out on its floor (`flee.Flee.door_verdicts` "one_exit"); off, any free door stands
    INSIDE_SHOVE = True   # ruling P26-C: an `inside` corner with INSIDE_CROWD_N or more at point blank shoves, never
                          # swings (`_inside_crowd`, `fight.Fight._crowd_shove`); off, the corner's swing as before
    THREAT_BLEED = True   # ruling P26-D: the bleed's yield under the threat branch (`care_yield.CareYield._bleed_free`,
                          # `_bleed_leg`); off, the yield's reads of P24-P, P24-U and P24-AR alone
    # survival iteration 18 (Plan 26 Task 7; survive.py's docstring, Survival 20): each switch off is the rule before
    # it, all of them in `survive.T8_SWITCHES` (the replay tests' `pre_t8`)
    WINDOW_INNER = True   # ruling P26-I: a window way out needs an inside square that is neither `solid` nor
                          # `solidTrans` (`night.window_exits`' `walkable`); off, P26-A's windows whatever stands inside
    WINDOW_STALL = True   # ruling P26-J: a window way out's act holding the player within STUCK_MOVE for WINDOW_STALL_S
                          # is dropped and refused `stalled`, a first `interrupted` end sent again
                          # (`flee.Flee._stall_limit`, `_window_ended`), a stalled mark a WINDOW_DEAD end for
                          # DOOR_RETRY_MIN (P26-J2); off, the act runs to its end, a failure refuses
    STAND_CROWD = True    # ruling P26-K: the doorway stand ends `crowd` at STAND_CROWD_N standing held within DANGER_R,
                          # read after `wound` and before `inside` (`DoorwayStand._stand_crowd`); it takes the close
                          # with nobody inside, else walks out (P26-K2, `_stand_occupied`); off, no such end
    WOUNDED_SWING = False  # ruling P26-L1: under the `wounded` reason a lone standing target at point blank with
                           # SHOVE_FAIL_N missed shoves on record is swung at in the shove's place, ahead of the corner
                           # and the breaks (`shove.FightShove._wounded_swing`); off, the shove, the corner, the breaks.
                           # Ruling P27-L (Plan 27 Task 5): withdrawn, off by default (F10's six divided swings after
                           # three failed shoves landed five times and lowered the target's listed health not at all,
                           # 1.0190000534057617 before and after each, the arms' pain at 118.6 to 120.8 dividing them,
                           # #4370; with E18's three, nine lowered no target; F8's one case was its only support)
    BLEED_HOLD = True     # ruling P26-L2: the dressing P26-D's yield sent is held while the zombie within FIGHT_REACH
                          # is not closing (`care_yield.CareYield._bleed_holds`), the hold applying only with one zombie
                          # within FIGHT_REACH (P26-L2a; `care_yield.py`); off, any zombie there supersedes it
    # survival iteration 19 (Plan 27 Task 1; survive.py's docstring, Survival 21): each switch off is the rule before
    # it, all of them in `survive.T9_SWITCHES` (the replay tests' `pre_t9`)
    FLEE_FINISH = True    # ruling P27-A: the flee's finish under the `strain`, `pair` and `many` flees on any fallen
                          # zombie, cleared to FINISH_CLEAR_R (`finish.ThreatFinish._flee_finish`, `_fallen_wide`); off,
                          # P24-AQ's struck target under `many` and P25-J (3)'s `pair` finish
    MANY_TAIL = True      # ruling P27-B: a `many` flee episode ends after MANY_TAIL_TICKS ticks with at most one
                          # standing zombie within DANGER_R and at most one of the listed pressing (`_many_tail_read`);
                          # off, it ends only when no held threat is within DANGER_R (P23-AM 1)
    HOLD_LONE = True      # ruling P27-C: under the endurance hold one zombie standing within DANGER_R and no other
                          # chaser listed is fought by the shove and the stomp (`hold.Hold._hold_lone`,
                          # `Fight.shove_only` "hold"); off, every such tick flees `strain`
    HOLD_REST = True      # ruling P27-C2: the endurance hold's walk with no chaser listed within LISTED_R is the rest,
                          # no leg sent (`hold.Hold._hold_rest`, `_rest`); off, P25-C's walk
    LOW_SWING = True      # ruling P27-E: the low fight's full swing after SHOVE_FAIL_N missed shoves at its lone target
                          # (`shove.FightShove._low_swing`); off, the low fight never swings (P25-S)
    # survival iteration 20 (Plan 27 Task 5; survive.py's docstring, Survival 22): each switch off is the rule before
    # it, all of them in `survive.T10_SWITCHES` (the replay tests' `pre_t10`)
    FLOOR_FINISH = True   # ruling P27-G: with a weapon held and the swing allowed, the Fight's and the flee's finish
                          # swing at a fallen zombie within FIGHT_REACH ahead of the stomp, and no stomp goes while a
                          # strike at it runs (`finish.FightFinish._floor_finish`, `ThreatFinish._flee_finish`); off,
                          # the stomp first (P24-AL, P24-AQ)
    FALLEN_SEEK = True    # ruling P27-H: a standing fight whose target reads fallen beyond FINISH_R on
                          # FALLEN_SEEK_TICKS ticks walks to it, or with a standing zombie within DANGER_R or its line
                          # blocked leaves it (`finish.FightFinish._fallen_seek`); off, the stance stands at it
    LISTING_FALLEN = True  # ruling P27-I: the `many` counts (the listing's and the held one's) leave out a zombie read
                           # fallen and one across a known blocked edge out of the hold radius (`_left_out`), as do the
                           # stance count and P27-B's tail read, which share `_counts_listed`; off, they count as
                           # P24-AD and P24-AN read them
    SHOVE_CLOSE = True    # ruling P27-J: the hold's lone fight only at a chasing zombie, an idle one leaving the rest
                          # (`hold.Hold._hold_idle`), and a shove-only Fight's lone chaser holding beyond point blank
                          # for SHOVE_CLOSE_TICKS walked to, or left for a blocked line
                          # (`shove.FightShove._shove_close`); off, the stance stands at it (P25-P, P25-S, P27-C)
    LOW_EXIT = True       # ruling P27-K2: the low fight leaves its lone target after SHOVE_FAIL_N missed shoves for the
                          # `health` flee (`shove.FightShove._low_exit`, `_low_left`), and the inside corner yields to
                          # that flee's way out under FLEE_HEALTH_FLOOR (`_corner_exit`); off, the shoves go on
    # survival iteration 20, fix 2 (Plan 27 Task 5 fix 2; survive.py's docstring, Survival 22): in T10_SWITCHES too
    ATTACK_REACH = True   # ruling P27-M: the standing fight's attack at a standing zombie only within the frame's
                          # `weapon.reach` plus ATTACK_MARGIN, the stance standing beyond it and the advance a walk to
                          # it (`fight.Fight._attack_hold`, `_reach_walk`); off, the attack within FIGHT_REACH
    POINT_BLANK_PIN = True   # ruling P27-N: a zombie within POINT_BLANK_R, or the nearest listed while the frame reads
                             # it attacking, is never left out of the Fight's targets by a mark, pinned and shoved,
                             # then swung at (`fight.Fight._pin_free`, `_pin_send`); off, the marks leave it out
    HEALTH_RIDE = True    # ruling P27-O: the `health` flee's leg is ridden by the bandage as the `many` flee's is,
                          # whatever the distance once FLEE_CARE_S have passed since that flee began with a part
                          # bleeding (`care_yield.CareYield._rides_health`); off, P24-U's RIDE_R alone
    # survival iteration 21 (Plan 28 Task 3; survive.py's docstring, Survival 23): each switch off is the rule before
    # it, all of them in `survive.T11_SWITCHES` (the replay tests' `pre_t11`)
    SHOVE_BACK = True     # ruling P28-B2: after a point-blank shove that knocked nothing down (within SHOVE_REPEAT_S)
                          # the stance's `back` leg in the second shove's place (`shove.FightShove._shove`); off, the
                          # shove again (P25-I's corner {kind shove})
    DRIFT_STAND = True    # ruling P28-B3: a cornered Fight's pin standing beyond CORNERED_R, chasing within DANGER_R
                          # on a line not read blocked, takes the stance's standing leg (`fight.Fight._drift_stands`);
                          # off, nothing sent (`out_of_reach`, P24-A fix 2, I2a)
    CIRCLE = True         # ruling P28-E: the stance's `back` leg from one standing zombie within KEEP_R turns
                          # CIRCLE_TURN off the straight away heading, the last side kept while clear
                          # (`fight.Fight._circle_turn`); off, the straight backpedal
    FLOOR_PAIN = True     # ruling P28-C: the swing at a fallen zombie within FIGHT_REACH is barred by a hold or a
                          # shove-only Fight, never by the arms' pain alone (`fight.Fight.floor_swing_barred`,
                          # `finish.ThreatFinish._flee_finish`); off, P24-AP's bar
    APPROACH_WALK = True  # the spec's 1 (b) (ruling P27-9, landed in P28-C's commit, its own switch since fix 1): a
                          # Fight not in the stance walks at a walk, never a run, to a zombie beyond FIGHT_REACH and on
                          # the approach after MISSES_TO_APPROACH unstarted swings (`fight.Fight._choose`); off, the run
    BUSY_RETRY = True     # ruling P28-D: a shove or a stomp rejected `busy` records no refusal at its target, so the
                          # next tick sends it again (`fight.Fight._observe_swing`); off, SWING_SKIP_S's refusal
    # survival iteration 22 (Plan 28 Task 7b; survive.py's docstring, Survival 24): in `survive.T12_SWITCHES` (the
    # replay tests' `pre_t12`)
    # survival iteration 24 (Plan 30 Task 3; survive.py's docstring, Survival 26): in `survive.T14_SWITCHES` (the
    # replay tests' `pre_t14`)
    SWING_CLOSE = True    # ruling P30-A: the melee's `closeR` is SWING_CLOSE_R, so the Lua swings at a chaser only
                          # inside it and presses a swing that did nothing again with no back leg (the Fight's
                          # `swing_close` rule, `dispatch.FightDispatch._melee_inputs`); off, `closeR` 0: the swing at
                          # the reach and the back leg after every miss, as before. PZA/1.10 (Plan 31 Task 2) retired
                          # `closeR` and the back leg (the meet's press at the predicted collision): the rule reads
                          # nothing since, kept as iteration 24's record in T14_SWITCHES
    CHASER_STANCE = True  # Plan 31 Task 15a (the ladder's street defect (a), in `survive.T15_SWITCHES`): a Fight not in
                          # the stance meets a chasing pin within DANGER_R in the stance's standing leg, never a walk
                          # toward it (`fight.Fight._chaser_stands`; the Fight's `chaser_stance` rule); off, the
                          # approach walk (APPROACH_WALK) as before
    MELEE = True          # cut 1 of the maneuver layer: where the Fight's ladder would send an in-reach stance leg,
                          # an attack, a shove, a stomp or a floor swing at its pin, the melee maneuver to a build
                          # announcing `melee` (`dispatch.FightDispatch`); off, the ladder's command
    # survival iteration 23 (Plan 29 Task 1; survive.py's docstring, Survival 25): in `survive.T13_SWITCHES` (the
    # replay tests' `pre_t13`)
    ROUTE_CROSS = True    # ruling P29-A: a route through a door (BLOCKED_EDGE's) walks to the square one step beyond
                          # its far square when the map holds it open, the Fight's at a walk, and reads its end by
                          # whether it crossed, an uncrossed `done` the door's failure and a marked door wall
                          # (`planner/edges.py`: the Fight's `route_cross` rule, the goals' kit); off, P25-X's route
    # survival iteration 23's hit rules (Plan 29 Task 2; survive.py's docstring, Survival 25): in `survive.T13_SWITCHES`
    HEALTH_NEAR = True    # ruling P29-E: the `health` flee only from a zombie within DANGER_R; with none there the low
                          # fight's stance at a held zombie in view, else the threat branch passes to the care
                          # (`_health_far`, `_near_view`); off, the `health` flee from any held zombie (P25-S)
    DRESS_FINISH = True   # ruling P29-D: a running dressing is not superseded by the flee's command while no zombie is
                          # within DANGER_R, the flee waiting on its end (`_dress_waits`); off, the flee's next command
                          # supersedes it
    MANY_NEAR = True      # ruling P29-G: the `many` flee's count is the standing zombies within DANGER_R
                          # (`_many_near`), over MAX_FIGHT to begin and at MAX_FIGHT to hold an episode; off, P24-A's
                          # hold radius, DANGER_R and listing counts (P27-I's `_counts_many`)
    FINISH_LONE = True    # ruling P29-F: the running Fight's finish of a fallen (or knocked) pin, the only zombie
                          # within DANGER_R, is kept over the `health` and `many` flees (`_finish_lone`); off, the flee
    CLOSE_IDLE = True     # ruling P29-C: P27-J's walk to close goes at an idle target only, a chaser met by the
                          # stance (`shove.FightShove._shove_close`, the Fight's `close_idle` rule); off, at a chaser
    DRESS_RIDE = True     # ruling P30-F (Plan 30 Task 3; survive.py's docstring, Survival 26; `survive.T14_SWITCHES`):
                          # a running dressing on a part falling faster than BLEED_FAST a game minute is waited on by
                          # the flee while no zombie is within KEEP_R (`_dress_waits`, `care_yield.CareYield
                          # ._bleed_rate`), logged `dress_ride` {part, rate}; off, P29-D's wait with nobody within
                          # DANGER_R alone
    # Plan 32 Task 5 (the coward fix; survive.py's docstring): in `survive.T16_SWITCHES`
    PAIR_NEAREST = True    # (b): with two or more within KEEP_R and one standing, the nearest standing one is the
                           # Fight's pin, faced and shoved first, switched only PAIR_SWITCH_R nearer (the Fight's
                           # `pair_nearest` rule, `fight.Fight._pair_pin`); off, the finish and the pin as before
    CARE_COMMIT = True     # (c): a care action wanted with the nearest within CARE_HOLD_R takes one walk away (to
                           # CARE_HOLD_R + CARE_MARGIN, at most CARE_LEG_S), then the threat branch yields to it until
                           # it ends, unless a standing zombie is within KEEP_R (`care_yield.CareYield._care_commit`);
                           # off, the yields before it
    STRAIN_BOUND = True    # (d): the `strain` flee only at stats.endurance STRAIN_ENDURANCE or under (the ENDURANCE
                           # moodle's second level) and never with exactly one standing within DANGER_R
                           # (`_strain_flees`); off, every hold's `strain` flee as before
    POINT_BLANK_FIGHT = True   # (a): a standing zombie within KEEP_R is fought whatever flee reason the plan would take
                               # (`_point_blank`), the health under FLEE_HEALTH_FLOOR and a running retreat to a named
                               # structure excepted (Plan 34 Task 3c fix 1: within POINT_BLANK_OVER_R alone under
                               # a `many` or `health` reason); off, the flee reasons as before
    POINT_BLANK_OVER_R = POINT_BLANK_OVER_R   # Plan 34 Task 3c fix 1: (a)'s radius under a `many` or `health` reason,
                                              # the rule's own constant read here, so a seam onto the rules before it
                                              # (a replay's) sets KEEP_R; no switch
    GROUP_LEAVE = True        # Plan 33 Task 3 (`group.ThreatGroup._group_leave`): the leave's row where the disposition
                              # selector does not run; off, no such row. No switch since Plan 37 Task 3 (out of
                              # survive.T18_SWITCHES: the selector owns the entry where it runs): the replay tests'
                              # seam onto the rules before Plan 33 (`test_replay_decisions.pre_t17`,
                              # `test_survive.make`)
    FLEE_HELD_STANCE = True   # ruling P29-H': a flee walk whose observed heading runs at a held zombie is dropped with
                              # its plan, its door marked `walled`, and the fight meets it in the stance
                              # (`flee.Flee._held_ahead`, the Flee's `flee_held_stance` rule); off, the walk runs on
    # Plan 34 (the column; the spec's § 3): in survive.T19_SWITCHES
    LEAVE_CARE = True        # the care barred under a column of GROUP_LEAVE_N standing within GROUP_ENTRY_R, the ride
                             # alone kept (`care_yield.CareYield._care_commit`, `_care_yields`), logged `care_withheld`;
                             # off, the care's yields as before
    DOOR_INSIDE = True       # the shelter plan's enter read inside (a room square of its building) and its close sent
                             # from inside (Task 2); off, the enter's `done` and the close as before
    LEAVE_DOOR_RACE = True   # the leave's door only with the nearest standing beyond DOOR_RACE_R and a second exit,
                             # dropped at DOOR_ABORT_R (Task 2); off, any `ok` door within LEAVE_DOOR_R
    LEAVE_ENTRY = True       # Task 3b (ruling P34-G): the leave's entry with no cover exemption (the back read logged
                             # beside it) and with GROUP_LEAVE_N standing within GROUP_ENTRY_R, the nearest within
                             # KEEP_R, closing or not (`group.ThreatGroup._leave_entry`); off, the cover withholds and
                             # the closing read alone enters
    # Plan 36 Task 2a addendum (the press on the back step; the spec's § 3.2): in survive.T21_SWITCHES
    BACKSWING = True         # every melee sent with work carries backswing true (the Fight's `backswing`, set each
                             # tick, `dispatch.FightDispatch._work_inputs`): a press launched while the reflex's step
                             # walks keeps the walk held through it (PZAgent_StanceMelee.lua's K.meleePressWalk);
                             # off, the walk stopped on the press's tick as before

    def _hold_r(self):
        """The hold radius: DISENGAGE_R while a threat policy runs, ENGAGE_R on a tick the sought fight entered the
        branch (P24-X), else DANGER_R."""
        if self.mode is not None:
            return DISENGAGE_R
        return ENGAGE_R if self.engaging else DANGER_R

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
        (`_pressing`: within DISENGAGE_R or chasing), so one or two fought while the rest stand off is no group.
        Ruling P24-AD (Plan 24 Task 21; E8's fight 1, line 170: `many` fired on three held, one chasing at 7.50 tiles
        and two reading `hasTarget` false at 9.45 and 9.95 on every frame of the fight): a zombie reading `hasTarget`
        false counts toward `many` only within DANGER_R (`_counts_many`), in the held count and the listing alike; a
        chasing one, or one whose frame carries no `hasTarget`, counts as before. The read is per tick, so an idle
        zombie that wakes counts on the next. Ruling P24-AN (P24-AD extended from the flee's count to the listing's):
        the listing counts a zombie only within DANGER_R or chasing (`_counts_listed`: `hasTarget` true; one whose
        frame carries no `hasTarget` no longer counts beyond DANGER_R), so no idle or unread zombie past DANGER_R ever
        makes `many` by MANY_LISTED_N. Ruling P27-B (`MANY_TAIL`): the episode's tail, read once a tick in
        `_threat_read` (`_many_tail_read`), clears `flee_many`, so this clause no longer holds the flee after it.
        Ruling P27-I (`LISTING_FALLEN`): neither count takes a zombie `_left_out` names (fallen, or across a known
        blocked edge out of the hold radius). Ruling P29-G (`MANY_NEAR`): the read is `_many_near`'s alone."""
        if self.MANY_NEAR:   # P29-G
            hold = 1 if self.mode == "flee" and self.flee_many else 0
            return self._many_near() > MAX_FIGHT - hold, None
        return self._many_read_p27(held, n)

    def _many_read_p27(self, held, n):
        """`_many_read` before ruling P29-G: the hold radius's, the DANGER_R count's and the listing's reads."""
        counted = [z for z in held if self._counts_many(z)]
        if self.mode == "flee" and self.flee_many:
            near = len(counted) > MAX_FIGHT or min(zdist(self.world, z) for z in held) <= DANGER_R
        else:
            near = (len(counted) if self.mode == "fight" else n) > MAX_FIGHT
        if near:
            return True, None
        listed = [z for z in self._within(LISTED_R) if self._counts_listed(z)]
        if len(listed) < MANY_LISTED_N or (self.ENGAGE and self._pressing(listed) <= MAX_FIGHT):
            return False, None
        return True, len(listed)

    def _many_near(self):
        """Ruling P29-G (`MANY_NEAR`; E22, `e_day_22-20261105-004919`: on 145 of the `many` flee's 198 lines at most one
        standing zombie stood within 6 tiles, #4628; line 1341's `many` read three within DANGER_R, two of them lying
        fallen; E21's and F12's fifth readings): the count the `many` rule reads, the zombies standing (not `onFloor`)
        within DANGER_R that `_counts_many` takes (one `_left_out` names aside). `many` is more than MAX_FIGHT of them,
        and while a `many` episode runs MAX_FIGHT hold it (a flip at the line kept off, as P23-AM 1's), so the episode
        ends at one standing or none; the hold radius's count and the listing's (P24-A (a), P24-X) are not read. Cost
        if wrong: a group arriving from beyond DANGER_R, met in the stance until three stand within it."""
        return sum(1 for z in self._danger_near() if not on_floor(z) and self._counts_many(z))

    def _counts_many(self, z):
        """Ruling P24-AD: zombie `z` counts toward `many`: within DANGER_R, or not idle (`hasTarget` not read false: a
        chaser, or a frame that does not carry the field); with `IDLE` off every zombie counts. Ruling P27-I: never one
        `_left_out` names."""
        return self._counts_many_p24(z) and self._left_out(z) is None

    def _counts_many_p24(self, z):
        return not self.IDLE or z.get("hasTarget") is not False or zdist(self.world, z) <= DANGER_R

    def _counts_listed(self, z):
        """Ruling P24-AN: zombie `z` counts toward `many` by the listing: within DANGER_R or chasing (`hasTarget`
        true); with `IDLE` off every zombie counts (the rules before P24-AD). Ruling P27-I: never one `_left_out`
        names."""
        return self._counts_listed_p24(z) and self._left_out(z) is None

    def _counts_listed_p24(self, z):
        return not self.IDLE or chasing(z) or zdist(self.world, z) <= DANGER_R

    def _left_out(self, z):
        """Ruling P27-I (`LISTING_FALLEN`; E19, `e_day_19-20261103-072904`: on line 386's frame three of the five listed
        read fallen, one was the gate zombie across the fence row and one stood chasing 10.538954093041877 tiles off,
        and the listing's count of four began a new `many` episode, #4555): why zombie `z` is left out of the `many`
        counts, else None: "fallen" when the frame reads it `onFloor`; "across" when it stands beyond the hold radius
        (`_hold_r`) and the straight line to it crosses a known blocked edge (`edges.crossed`, P25-X's read: a blocked,
        unhoppable outdoor edge). None with `LISTING_FALLEN` off. `_counts_listed` reads it, so the clauses reach every
        read of the listing: the `many` counts, the stance count (`engage._stance_count`) and P27-B's tail read
        (`_many_tail_read`). Cost if wrong: a group that rises together (the fallen counted again the tick they
        stand)."""
        if not self.LISTING_FALLEN:
            return None
        if on_floor(z):
            return "fallen"
        if zdist(self.world, z) > self._hold_r() and crossed(self.world, me_xy(self.world), (z["x"], z["y"])):
            return "across"
        return None

    def _listing_out(self):
        """P27-I's why: {fallen, across} of the listed zombies within LISTED_R the counts before it took (P24-AD's or
        P24-AN's reading) and `_left_out` leaves out, when any is, else None."""
        out = {"fallen": 0, "across": 0}
        for z in self._within(LISTED_R):
            if self._counts_listed_p24(z) or self._counts_many_p24(z):
                kind = self._left_out(z)
                if kind is not None:
                    out[kind] += 1
        return out if out["fallen"] or out["across"] else None

    def _pressing(self, zs):
        """Of `zs`, the zombies within DISENGAGE_R (10: ENGAGE_R's value at P24-X, kept when Task 18 fix 1's minor 8
        drew the engage in to 9) or chasing (`hasTarget`): P24-X's reading of the listing (the E7
        write-up, Task 18: each of E7's fights fled four or more listed within LISTED_R, two of them standing off at
        11.6 and 11.8 tiles, not chasing, while the pair the fight was on came; E5's horde at line 220 had three of
        five pressing, 4.9 tiles off and two chasing at 10.4 and 11.3)."""
        return sum(1 for z in zs if zdist(self.world, z) <= DISENGAGE_R or z.get("hasTarget") is True)

    def _many(self, held, n):
        """`_many_read`'s `many`, its `listed` kept for the decision's why (logged `listed`); ruling P29-G: a tick
        whose `many` the reads before it made and `_many_near` does not, logged `many_near` {n}. Plan 35: a
        `many` read while the Fight's melee is engaged (`_engage_holds`) answers the hold (False), logged `engage_hold`
        {rule "many"}."""
        many, listed = self._many_read(held, n)
        if listed is not None:
            self.listed = listed
        if self.MANY_NEAR and not many and self._many_read_p27(held, n)[0]:
            self.many_near = {"n": self._many_near()}   # P29-G: the standing count that withheld it
        out = self._listing_out() if self.LISTING_FALLEN else None
        if out is not None:
            self.listing = out   # P27-I: the zombies the counts left out, on the decision's why
        return many and not self._engage_holds("many")

    def _engage_holds(self, rule):
        """Plan 35 (the spec's § 3.2): True when the threat row `rule` would supersede the Fight's engaged
        melee (`dispatch.FightDispatch._engaged`: the running melee with `work`, this branch fighting) and the health
        reads above FLEE_HEALTH (the reflex's floor, `floorHealth`: at or under it the reflex hands back `floor` and the
        rows run as before), the hold logged `engage_hold` {rule} (the first row held on the tick); else False (no
        engagement). Every row is held in contact, whatever the count (Plan 37 Task 3 deleted Plan 35 fixes 3 and 4's
        lapse above RETREAT_MAX_N: the many and the crowd are the disposition's, `disposition.Disposer`, and its `break`
        hands over through the reflex's release); `engage_yield` is the bleed's care alone (`care_yield.py`)."""
        if not self._engage_on():
            return False
        if self.engage_hold is None:
            self.engage_hold = {"rule": rule}
        return True

    def _contact_lift(self):
        """Plan 35 fix 8b (the controller's ruling; the street-1 trial `x_trial-ladder-20261111-114439`, decision lines
        306 to 313: the one standing zombie left, 27900, marked unreachable and lunging from 1.11 to 0.49 tiles, the
        threat plan fled `unreachable` to a shelter and the bite landed under the walk 0.75 s later): where the melee
        can go (MELEE on, the build announcing `melee`) no `unreachable` flee is taken with a standing zombie (not a
        crawler) within KEEP_R: the nearest's mark is lifted, so the Fight pins it and its
        dispatch sends the melee with `work`, logged `engage_dispatch` {from "unreachable", target} on the threat why
        (the reflex's stall and re-pin own the unreachable case from inside the engagement). True when it lifted one."""
        if not (self.MELEE and self.world.can("melee")):
            return False
        near = next(((zid, d) for zid, z, d in self._group_standing(KEEP_R)
                     if target_id_ok(zid) and not is_crawler(z)), None)
        if near is None:
            return False
        self.unreachable.pop(near[0], None)
        self.engage_dispatch = {"from": "unreachable", "target": near[0]}
        return bool(self._reachable_held())

    def _engage_on(self):
        """`_engage_holds`'s read, with no log: this branch fighting, its Fight engaged, the health above FLEE_HEALTH."""
        f = self.fight
        return (self.mode == "fight" and f is not None and f._engaged()
                and self._health() > FLEE_HEALTH)

    def _pull_ok(self, kind, door):
        """Plan 36 Task 3: the engagement picker reads this Fight's line: never the door fight (`door`) or a sheltered
        one (a doorway is a chosen chokepoint; the doorway stand has its own row); the open-ground Fight (kind
        `fight` off a room square); fix 3 (the trial `x_trial-ladder-20261111-190803`: 79 `engage_hold` {rule
        "cornered"} lines with four or five held and no pull, the three bites under that hold) the corner Fight (kind
        `cornered`, or a `fight` on a room square, the held corner's) where the frame carries the room ring
        (`World.room`), its withdraw clamped to the ring's open headings (`group.ThreatGroup._pull_room`); with no
        ring the corner Fight sends none, as before the ring."""
        if door is not None or self.sheltered or kind not in ("fight", "cornered"):
            return False
        if kind == "fight" and not self.night.inside():
            return True
        return self.world.room() is not None

    def _flee_reason(self, held, n):
        """Why the threat branch flees, by the hysteresis in the module docstring (`_hysteresis`); None when it fights.
        A fight that would walk toward its target with another zombie listed behind it (`_behind_walk`, ruling P24-A
        (b)) flees `held` instead (`many` having been read first)."""
        reason = self._hysteresis(held, n)
        if reason is None and self.health_near is not None and not self._low_fight(n):
            if self._held_in_view(held):
                return "health"   # P29-E fix 1 (review-t2 M1): one in view and no stance to hold, P25-S's flee
            self.health_pass = True   # P29-E: none in view, the threat branch passes (`_threat_plan`)
            return None
        if reason is None and self._behind_walk():
            return "held"
        return reason

    def _finish_lone(self, reason):
        """Ruling P29-F (`FINISH_LONE`; E22, `e_day_22-20261105-004919`: 11526's melee read its shove's knock-down,
        `knock_wait` at seq 13233, and line 1471's `many` flee steered away from it, 2.083 tiles off with no other
        zombie within DANGER_R, its stomp landing later from 2.896 without a kill; 11784's far-finish stomp a227 was
        superseded by line 1064's `health` steer, #4625): `{target}` when this tick's reason is `health` or `many`, a
        Fight runs (`mode` fight) whose pin's finish is under way (`Fight.finishing`: read fallen, in a shove's knock
        window, or the melee at it on a finish step) within FINISH_R, and that pin is the only zombie within DANGER_R:
        the flee is not taken, the Fight keeps its stomp walk or its melee, logged `finish_lone` {target}; a second
        zombie within DANGER_R, standing or not, gives the flee as before. Else None. Cost if wrong: a walk to a
        zombie that rises, the stance meeting it."""
        f = self.fight
        if not self.FINISH_LONE or reason not in ("health", "many") or self.mode != "fight" or f is None:
            return None
        zid = f.target
        z = self.world.zombies.get(zid) if zid is not None else None
        if z is None or z.get("x") is None or z.get("y") is None or zdist(self.world, z) > FINISH_R:
            return None
        near = self._danger_near()
        if len(near) != 1 or near[0] is not z or not f.finishing(zid):
            return None
        return {"target": zid}

    def _behind_walk(self):
        """Ruling P24-A (b): the ids listed behind the target the Fight would walk toward (`policies.others_behind`),
        kept in `behind`, else []: the running fight's target (its pin, else the nearest reachable), or with none
        running the nearest zombie not marked (a new Fight's first pin); the Fight walks when the target is beyond
        FIGHT_REACH, when its approach is due beyond POINT_BLANK_R (P24-A (e)), or when the line to it reads blocked
        (the reposition). Ruling P24-AN: a lone chaser the Fight pulls (or would pull, or stand for within PULL_R:
        `_pulls`) is walked away from, never toward: no look behind it (E9's six fights dropped for a chaser 10.74 to
        11.90 tiles behind the target)."""
        f = self.fight if self.mode == "fight" else None
        if f is not None:
            t = f._target(pin=False)
            seek = f.seeking(t)
            stand = f.standing() and not f.advance   # P24-N: the advance closes on the target, a walk toward it
            if seek and f.pull_centroid(t) is not None:
                return []   # P24-AN: the pull, or the stance once the chaser is within PULL_R
        else:
            nz = self.world.nearest_zombie(exclude=self._skipped())
            t = None if nz is None else (nz[0], nz[1], zdist(self.world, nz[1]))
            seek = self._seeks() and t is not None and seek_allowed(self.world, t, self._chokepoint())   # P24-X
            stand = self._stance_ok(self._within(self._hold_r()), self.night.inside())
            if seek and stand and self._pulls(t):
                return []   # P24-AN: the new Fight's first leg pulls (or stands within PULL_R)
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
        `pair` rule's); `many` is `_many`. Ruling P29-E (`HEALTH_NEAR`): under FLEE_HEALTH with no zombie within
        DANGER_R (`_health_far`) no `health` reason, nor a `held` one the health keeps (`_unpaired`), logged
        `health_near` {near: n}: the low fight's stance at a held zombie in view (`_low_fight`, `_near_view`), else the
        branch passes (`_flee_reason`'s `health_pass`)."""
        health = self._health()
        self.health_near = {"near": n} if health < FLEE_HEALTH and self._health_far(n) else None
        if not self._armed() and (not self._unarmed_fight(n) or self._many(held, n)):
            return "unarmed"
        if self._many(held, n):
            return "many"
        if (health < FLEE_HEALTH and not self._low_fight(n) and self.health_near is None
                and not self._engage_holds("health")):   # Plan 35: held only above the floor (the reflex's)
            return "health"
        if n >= 2 and (health < FLEE_HEALTH_PAIR or self._wounds() > 0):
            fallen = self._pair_finish()   # P25-J (3): the finish of a fallen (or knocked) one goes before the flee
            if fallen is None:
                if not self._engage_holds("pair"):   # Plan 35 fix 1: no pair flee over the engaged melee
                    return "pair"
                return self._unpaired(held, health, n)
            reason = self._unpaired(held, health, n)
            if reason is None:
                self.pair_yield = fallen   # kept only where the fight answers: never on a `strain` (or any flee) line
            return reason
        return self._unpaired(held, health, n)

    def _unarmed_fight(self, n):
        """Ruling P25-P (F5, `f_goals_6-20261030-192251`: 27 fights, every one fled `unarmed`, no kill; the Lua's shove
        takes a standing zombie within K.STAND_R with no weapon, and the stomp has been every session's kill since
        E11): with no weapon held, the Fight is allowed (`UNARMED_FIGHT` on): the build announces `shove`, one zombie
        within DANGER_R (`n` 1: two or more flee `unarmed` as before) and the health at or above FLEE_HEALTH_PAIR. The
        Fight it makes sends no swing (`Fight.shove_only`, `no_swing`): the stance, the shove at point blank, the stomp
        of the fallen; it is never sought (`Fight.seeking`), the corner and the doorway stand stay armed-only."""
        return (self.UNARMED_FIGHT and not self._armed() and self.world.can("shove") and n == 1
                and self._health() >= FLEE_HEALTH_PAIR)

    def _low_fight(self, n):
        """Ruling P25-S (E13, `e_day_13-20261030-213219`: the health held between 30.32921600341797 and
        32.70201110839844 from game minute 712 to the cap, the last 15 fights all fled `health` and nothing was killed
        for 96 game minutes, a bat, dressings and water held): under FLEE_HEALTH the line is no lock: the Fight is
        allowed (`LOW_FIGHT` on) with the build announcing `shove`, one zombie within DANGER_R (`n` 1: two or more flee
        `health` as before) and the health at or above FLEE_HEALTH_FLOOR. Its Fight is P25-P's shove-and-stomp fight
        (`Fight.shove_only` "low": the stance, the shove at point blank, the stomp of the fallen, no swing, no seek),
        logged `low_fight`; the doorway stand's own `health` end is unchanged. Ruling P29-E (`HEALTH_NEAR`): with none
        within DANGER_R (`n` 0) too, where the stance may hold at a held zombie in view (`_near_view`)."""
        health = self._health()
        return (self.LOW_FIGHT and health < FLEE_HEALTH and self.world.can("shove") and (n == 1 or self._near_view(n))
                and health >= FLEE_HEALTH_FLOOR and not self._low_left())

    def _health_far(self, n):
        """Ruling P29-E (`HEALTH_NEAR`; E22, `e_day_22-20261105-004919`: 138 of the `health` flee's 181 lines read no
        zombie within DANGER_R and its 32 sends all went at a run, while the low fight's runs under the same health held
        the third and fourth kills, #4628): no zombie within DANGER_R (`n` 0), so no `health` flee. Cost if wrong: a
        chaser reaching the stance at health 30."""
        return self.HEALTH_NEAR and n == 0

    def _near_view(self, n):
        """Ruling P29-E: with no zombie within DANGER_R (`_health_far`), the stance announced (`aim`: the low fight
        never walks to a zombie from afar), at most MAX_FIGHT held zombies in its count (`_stance_count`) and a held
        zombie the Fight may target whose straight line is not read blocked (`line_to`: an unscanned end reads None,
        in view): the low fight's stance holds at it (E22's line 749: 11515 chasing 8.197687115943333 tiles off, the
        `health` flee's steer sent at a run), the zombie met where the low fight meets it once it comes within
        DANGER_R. With none of these (under FLEE_HEALTH_FLOOR, more than MAX_FIGHT in the stance count, no `aim` or
        `shove` announced) and one in view, the `health` flee runs as before; with none in view the branch passes
        (`_flee_reason`; fix 1, review-t2 M1)."""
        if not (self._health_far(n) and self.world.can("aim")
                and self._stance_count(self._within(self._hold_r())) <= MAX_FIGHT):
            return False
        return self._held_in_view([z for _, z in self._reachable_held()])

    def _held_in_view(self, zs):
        """P29-E: a zombie of `zs` whose straight line is not read blocked (`line_to`: an unscanned end reads None, in
        view)."""
        return any(line_to(self.world, z) is not False for z in zs)

    def _low_left(self):
        """Ruling P27-K2 (`LOW_EXIT`): every zombie within DANGER_R is one the low fight left this threat episode
        (`low_left`, `shove.FightShove._low_exit`): the low fight is not allowed, so the `health` flee runs."""
        if not (self.LOW_EXIT and self.low_left):
            return False
        near = self._danger_near()
        ids = [zid for zid, z in self.world.zombies.items() if any(z is w for w in near)]
        return bool(ids) and all(zid in self.low_left for zid in ids)

    def _danger_near(self):
        """The zombies within DANGER_R (`_within`), read once a tick for the rules that count them (the threat plan's
        `n`, P27-K2's `_low_left`, P29-D's `_dress_waits`, P29-F's `_finish_lone`, P29-G's `_many_near`; fix 1,
        review-t2 m4): read again when the tick, the frame, a kill mark (`dead`) or an edge mark (`edge_marks`, which
        `_within` leaves out across) has moved since."""
        key = (self.ticks, self.world.frame_n, len(self.dead), len(self.edge_marks))
        if self._near_cache is None or self._near_cache[0] != key:
            self._near_cache = (key, self._within(DANGER_R))
        return self._near_cache[1]

    def _corner_exit(self, held, inside):
        """Ruling P27-K2 (`LOW_EXIT`; F10, `f_goals_11-20261103-075140`: on line 1442, health 11.3414306640625, the
        `health` flee chose the bedroom's window and sent its walk, superseded on the next line by the inside corner's
        shove at point blank, with three zombies within DANGER_R): on a room square (`inside`) under FLEE_HEALTH_FLOOR
        with a way out known (`_exit_known`), the inside corner yields to the `health` flee's way out (logged `corner`
        {yield "health"} on the flee's line). Cost if wrong: turning from a zombie at point blank."""
        return self.LOW_EXIT and inside and self._health() < FLEE_HEALTH_FLOOR and self._exit_known(held)

    def _unpaired(self, held, health, n):
        """The hysteresis past the `pair` rule (`_hysteresis`; `n` the DANGER_R count): `strain`, `unreachable`,
        `stalled`, `held`, else None."""
        if (self.spent is not None and not self._wounded_fight() and not self._hold_lone()   # P24-AG, P24-AK: the
                and self._strain_flees() and not self._engage_holds("strain")):   # arms, the endurance or the
            # tiredness halve every swing; P24-AP within KEEP_R; P27-C; Plan 32 Task 5 (d): only under a real
            # exhaustion; Plan 35 fix 1: not over the engaged melee (the reflex's spent meet)
            return "strain"
        if not self._reachable_held() and not self._contact_lift():
            return "unreachable"
        near = min(zdist(self.world, z) for z in held)
        if self.mode == "flee":
            if self.stall_flee and near > FIGHT_REACH:
                return "stalled"
            if not self.ENGAGE:   # before P24-X: one held, at the refight margin
                return "held" if len(held) > 1 or health < FLEE_HEALTH + REFIGHT_MARGIN else None
            kept = None if self.health_near is not None else "held"   # P29-E: no health keeps a flee from afar
            if not (self._takes_on(len(held)) or self._unarmed_fight(n) or self._low_fight(n)
                    or self._hold_lone()):   # P24-X: the flee turns to fight one or two at the fight's line; P25-P
                return kept   # unarmed, P25-S under FLEE_HEALTH, P27-C the hold's lone zombie
            if self.flee_health and health < FLEE_HEALTH + REFIGHT_MARGIN and not self._low_fight(n):
                return None if self._health_far(n) else "held"   # the health flee stays, its margin kept (P25-S: but
            return None                                           # for the low fight; P29-E: but from afar)
        if self.mode == "fight" and self.fight.stalled and (self.fight.target_dist() or 0.0) > FIGHT_REACH:
            return "stalled"   # the pinned target's distance: the one the stall clock follows (M3)
        return None

    def _strain_flees(self):
        """Plan 32 Task 5 (d) (`STRAIN_BOUND`; Angus watching F17, `f_goals_17-20261108-172833`: the `strain` flee took
        158 of its 389 flee lines from line 1173 to the end, every one the endurance hold alone at stats.endurance
        0.6427835822105408 to 0.7410425543785095, the ENDURANCE moodle's first level, 51 of them with one zombie within
        DANGER_R): the spent character's `strain` flee may go: always with the rule off; else only under a real
        exhaustion, the frame's stats.endurance at or under STRAIN_ENDURANCE (the moodle's second level, #3926), and
        never while exactly one standing zombie (not `onFloor`) is within DANGER_R (it is fought, the Fight's no-swing
        rules under the hold, R2, or met). A withheld flee is logged `strain_bound` {endurance, standing} and the plan
        goes on past it (`_unpaired`); the pain-divided and the moodle-halved swing are the meet's business (the Lua's
        spent meet at the moodle's second level). The hold itself, its seek bar (`_sought`) and its rest are unchanged.
        Cost if wrong: a fight at endurance level 1, every swing halved (#4371)."""
        if not self.STRAIN_BOUND:
            return True
        e = (self.world.stats or {}).get("endurance")
        stand = sum(1 for z in self._danger_near() if not on_floor(z))
        if isinstance(e, (int, float)) and not isinstance(e, bool) and e <= STRAIN_ENDURANCE and stand != 1:
            return True
        self.strain_bound = {"endurance": e, "standing": stand}
        return False

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
        one, or one not refused this episode; the window rules read from the Flee's rules (`_flee_rules`, P26-R: the
        frozenset `_decide` hands the Flee, read here before this tick's Flee may exist)."""
        f = self.flee
        if f is not None and f.exit is not None:
            return True
        rules = self._flee_rules()
        return exit_plan(self.world, held, f.refused if f is not None else (), self.TRANS,
                         "window_exit" in rules, "window_inner" in rules) is not None

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
            if self.corner_kind == "inside" and self._corner_exit(held, inside):   # P27-K2: the health flee's way out
                self.cornered, self._corner_fight, self.corner_exit = None, None, {"yield": "health"}
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
        if inside and not stuck and self._corner_exit(held, inside):   # P27-K2: no inside corner over the way out
            self.corner_exit = {"yield": "health"}
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
        if self.mode == "flee" and self.flee_many:
            return "many"
        if self.spent is None or self._wounded_fight() or not self._strain_flees():   # P24-AP, R2: a hold fights
            return None                                                              # within KEEP_R; Plan 32 Task 5 (d)
        return "strain"   # P24-AG: spent, it disengages as the health flee does

    def _drag(self, held, inside):
        """Ruling P24-A (h) (#4290, #4291: DRAG_DOWN_N zombies attacking from within 0.9 tiles turn the next hit into
        the drag-down, health to 0 in one call): the frame's `me.attackers` (PZA/1.4; absent on an older frame, never
        read) at DRAG_DOWN_N - 1 or more, any corner (a `stuck` one too) left for the leg at once; except on a room
        square with no way out and nothing to adopt (`_trapped`): the guard has no leg or exit to take there, so the
        corner keeps swinging (P24-A fix 1 (4), confirmed). Never read while a doorway stand stands: its own `drag` end
        reads first at the same count (P25-U, `DoorwayStand._stand_drag_n`)."""
        if self._attackers() < DRAG_DOWN_N - 1:
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
        """The threat branch's decision (`_threat_rows`), then the contract under a fight disposition (Plan 37 Task 3
        fix 3, `disposition.Disposer._contract`: no flee in contact under `hunt`, `hold` or `string`)."""
        return self._contract(self._threat_rows(held, breach), self.night.inside())

    def _threat_rows(self, held, breach):
        """The threat branch's one decision (ruling P23-AJ), `(kind, reason)`, the machines only executing it:
        - The doorway stand (ruling P24-AO, `_doorway`): `doorway` while the Flee's stand plan reads `stand`, then
          `flee` (reason `doorway`) while the stand's close, or its way out after an end under a group (P25-W), runs,
          ahead of every other row (the stand's premise is the
          one-tile front the drag-down guard flees: the stand reads its own `drag` end, at DRAG_DOWN_N - 1 since
          P25-U, the guard's own count, `_stand_drag_n`).
        - The drag-down guard (ruling P24-A (h), `_drag`): `flee` with the group steer (`group` "drag"), ahead of
          every other row but the doorway's; the Flee steers at a run, or inside walks the exit (P24-A (f), P24-O);
          not over the engaged melee (Plan 35, `_engage_holds`).
        - The disposition (Plan 37 Task 3, `disposition.Disposer._disposition_plan`), where the selector runs: under
          `break` the Fight while its release is pending, then `flee` with the break's reason (`health` the rows
          below), ahead of the corner; after the corner, off a room square with a standing zombie within
          GROUP_ENTRY_R, `fight` under `hunt`, `hold` and `string`, ahead of every flee reason. Where the selector
          does not run, the leave before the corner (`group.ThreatGroup._group_leave`: its door's `flee` reason
          `leave`, its retreat's `fight`).
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
        - Otherwise Plan 21b's hysteresis (`_flee_reason`): `fight` when it reads None, else `flee`; ruling P29-E:
          `pass` when it withheld the `health` flee with no stance to hold (`health_pass`), the branch passing.
        - Fix round 1: a broken hold at a chosen shelter fights only in its doorway or inside (`door`, the review's
          I4); a `flee` on a room square with no way out and no adoption left is the Fight when armed
          (`_trapped_fight`, G3), or unarmed (ruling P25-P) with one zombie within DANGER_R and a reachable one within
          FIGHT_REACH, the sheltered row's flee included (the unarmed character has no door fight).
        Not a pure function: it sets `sheltered`, `door`, `broken`, `cornered`, `corner_yield`, `behind` and `listed`
        (`_breach` before it set `closing`),
        and a corner inside a chosen shelter drops the sheltered Flee, so the next flee walks out rather than
        re-closing."""
        inside = self.night.inside()
        self.sheltered = self.flee is not None and self.flee.sheltered and inside
        self.broken, self.group_steer, self.corner_yield, self.behind, self.listed = None, None, None, None, None
        self.stand_left, self.stand_end, self.stand_wound, self.pair_yield = None, None, None, None
        self.stand_drag, self.stand_inside, self.stand_exit, self.stand_crowd = None, None, None, None
        self.one_exit_refused, self.listing, self.corner_exit = None, None, None
        self.health_near, self.health_pass, self.many_near = None, False, None   # P29-E, P29-G: this tick's
        self.finish_lone = None   # P29-F: this tick's
        self.point_blank_fight = None   # Plan 32 Task 5 (a): this tick's
        self.strain_bound = None   # Plan 32 Task 5 (d): this tick's
        pin = (self.clock_cut or self.clock_fight) if self._clock_on() else None
        if pin is not None and pin.get("target") in self.world.zombies:   # Plan 36 Task 4: the clock's melee first
            z = self.world.zombies[pin["target"]]
            self.cornered, self._corner_fight = None, None
            self.point_blank_fight = {"target": pin["target"], "dist": zdist(self.world, z), "over": "clock"}
            return "fight", None
        door = self._doorway()
        if door is not None:   # P24-AO: the doorway stand and its close go first, the drag guard's leg included
            self.leave = None   # Plan 33 Task 3: a leave ends at the doorway
            return door
        if self._drag(held, inside) and not self._engage_holds("drag"):   # P24-A (h): first, whatever the fight or
            # the corner; Plan 35: not over the engaged melee (the reflex meets the pile)
            self.cornered, self._corner_fight, self.group_steer, self.door = None, None, "drag", None
            return "flee", self._flee_reason(held, len(self._danger_near())) or "many"
        self.door = self._door_targets() if self.sheltered else None
        if self.door:
            return "door", None
        disposing = self._disposing()   # Plan 37 Task 3: the selector owns the entry where it runs
        if disposing and self.disposition == "break":   # the release, then the Flee: ahead of the corner
            plan = self._disposition_plan(inside)
            if plan is not None:
                return plan
        elif not disposing and self._group_leave(inside):   # Plan 33 Task 3: a closing trio left in the open (the
            self.cornered, self._corner_fight = None, None   # door or the retreat)
            return LEAVE_PLAN[self.leave_leg]
        if self._cornered(held, inside) is not None:
            if not self._engage_holds("cornered"):
                return "cornered", None
            self.cornered, self._corner_fight = None, None   # Plan 35: no corner Fight over the
            # engaged melee (the reflex meets the zombie at point blank)
            return "fight", None
        plan = self._disposition_plan(inside) if disposing else None   # Plan 37 Task 3: hunt, hold, string fight
        if plan is not None:
            return plan
        if self.group_steer:
            reason = self._flee_reason(held, len(self._danger_near())) or "many"
            if self._point_blank(reason) is not None:   # Plan 32 Task 5 (a): the group steer at point blank
                return "fight", None
            return "flee", reason
        steps = self.mode == "flee" and self.flee is not None and (self.flee.running_shelter()
                                                                   or self.flee.running_exit())
        held_inside = not steps and self._held_inside(held) and self.door_open is None   # P30-C: the open first
        if held_inside and breach is None:
            return "hold", "held_inside"
        reason = self._flee_reason(held, len(self._danger_near()))
        lone = self._finish_lone(reason)
        if lone is not None:   # P29-F: the lone fallen pin's finish kept over the `health` or `many` flee
            self.finish_lone, reason = lone, None
        if breach is not None and (held_inside or (self.sheltered and self.flee.shelter_holds(held))):
            self.broken = breach
            if self._exit_known(held):
                return "flee", reason or "broken"
            if self._armed() and len(held) <= MAX_FIGHT and self._reachable_held():
                return ("door", None) if self.sheltered else ("fight", None)   # I4: a shelter's fight stays inside
            return self._trapped_fight(held, inside) or ("flee", reason or "broken")
        if self.sheltered:   # P25-P: unarmed, a lone zombie in reach of a shelter with no way out is shoved
            fight = None if self._armed() else self._trapped_fight(held, inside)
            return fight or ("flee", reason or "sheltered")
        if reason is None and self.health_pass:
            return "pass", None   # P29-E: under FLEE_HEALTH, nobody within DANGER_R and no held zombie in view
        if reason is None:
            reason = self._kept_flee()
            if reason is None:
                return "fight", None
        if self._point_blank(reason) is not None:   # Plan 32 Task 5 (a): no flee at point blank
            return "fight", None
        return self._trapped_fight(held, inside) or ("flee", reason)

    def _point_blank(self, reason):
        """Plan 32 Task 5 (a) (`POINT_BLANK_FIGHT`; Angus watching F17, `f_goals_17-20261108-172833`: its first wound,
        seq 1613-1621, followed line 144's `attack` at 16101 and line 145's group steer fleeing `many` at
        0.1848981257193573 tiles from it, one zombie standing within DANGER_R; a flee from a zombie at point blank turns
        the back on it): `{target, dist, over}` when the plan would flee for `reason` while a standing zombie (not
        `onFloor`, one read dead or held out across a blocked edge aside: `_within`) a Fight may target stands within
        KEEP_R on a line not read blocked (`line_to`): the nearest such is fought instead, `over` the reason withheld,
        logged `point_blank_fight` and pinned by the Fight a new one makes (`_decide`). None with the rule off, under
        FLEE_HEALTH_FLOOR, for `steps` (a running shelter plan or way out: the retreat to a named structure, Plan 31's
        refuge ruling) or with no such zombie. The doorway stand, the drag-down guard and the sheltered Flee keep their
        own rows. Plan 34 Task 3c fix 1 (the trials `x_trial-ladder-20261109-142418` lines 343 and 358, a zombie
        pinned at 2.455 and 2.18 tiles over the `health` flee and walked in on, and `x_trial-ladder-20261109-141434`
        line 392, 2.24 over `many`): under a `many` or `health` reason the radius is POINT_BLANK_OVER_R (the zombie
        already on the character, which no flee outruns), beyond it the flee stands; KEEP_R under the others. Cost if
        wrong: a fight held against a second zombie arriving within KEEP_R."""
        self.point_blank_fight = None
        if not self.POINT_BLANK_FIGHT or reason == "steps" or self._health() < FLEE_HEALTH_FLOOR:
            return None
        near = self._within(self.POINT_BLANK_OVER_R if reason in ("many", "health") else KEEP_R)
        skip = self._skipped()
        best = None
        for zid, z in self.world.zombies.items():
            if (not target_id_ok(zid) or zid in skip or on_floor(z) or not any(z is w for w in near)
                    or line_to(self.world, z) is False):
                continue
            d = zdist(self.world, z)
            if best is None or (d, repr(zid)) < (best[1], repr(best[0])):
                best = (zid, d)
        if best is None:
            return None
        self.point_blank_fight = {"target": best[0], "dist": best[1], "over": reason}
        return self.point_blank_fight

    def _attackers(self):
        """The frame's `me.attackers` (PZA/1.4, an int; absent or not an int on an older frame: 0)."""
        n = (self.world.me or {}).get("attackers")
        return n if isinstance(n, int) and not isinstance(n, bool) else 0

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
        with no way out stands). Ruling P25-P (F5: the trapped stand's 110 s, one zombie biting through the window):
        unarmed, the same Fight where the unarmed fight is allowed (`_unarmed_fight`) and a reachable held threat
        stands within FIGHT_REACH (the shove's side of the room: farther, in the flee rows the hold stands and P25-Q's
        care runs). Called from the flee rows only: the hysteresis-None row makes the Fight at any distance, which
        takes the stance (`_stance_ok`, shove-only trapped too) and never an approach walk."""
        reach = self._reachable_held()
        if not (reach and self._trapped(held, inside)):
            return None
        if self._armed():
            return "fight", None
        near = min(zdist(self.world, z) for _, z in reach)
        return ("fight", None) if near <= FIGHT_REACH and self._unarmed_fight(len(self._danger_near())) else None

    def _end_flee_episode(self):
        """A flee episode's own flags cleared: its stall origin, its one load drop, its `many` (P23-AM 1), its `health`
        (P24-X) and its clock (P27-O) and its last reason (P26-D)."""
        self.stall_flee, self.flee_dropped, self.flee_many, self.flee_health = False, False, False, False
        self.flee_reason, self.health_since = None, None

    def _threat_read(self):
        """The tick's threat bookkeeping, once (ruling P24-A (g)): the held list (`_held`), the Flee's observe and the
        breach's closing count (`_breach_now`). Read in `_read` (Plan 25 Task 2, `OBSERVES_IN_READ`), else at the
        threat branch's start in `assess` (the rules before it)."""
        self.care_yield, self.care.ride_now, self.engaging, self.avoid = None, False, False, set()
        self._group_read()   # Plan 33 Task 3: the closing read, the unmoving count, this tick's group whys
        self.ride_flee = None   # P27-O: this tick's ride the health flee's clock admitted
        self.bleed_yield = None   # P26-D: this tick's yield the bleed's rule made
        self.scratch_yield = None   # Plan 31 Task 15a: this tick's yield to a scratch's Dress
        self.bleed_held = False   # P26-L2: this tick's yield the dressing's hold made
        self.finish_block = None   # Task 36 fix 1: this tick's refusal only (`_finish_chaser` sets it)
        self.held_cut = None       # P29-H': this tick's cut flee walk (`flee.Flee.take_held_cut`)
        self.care_withheld = None  # Plan 34 (LEAVE_CARE): this tick's care barred under a column
        self.engage_hold = None    # Plan 35: this tick's threat row held off the engaged melee
        self.engage_yield = None   # Plan 35 fix 2: this tick's care the engagement yielded to (a bleed, nobody in KEEP_R)
        self.engage_dispatch = None   # Plan 35 fix 8b: this tick's `unreachable` flee withheld in contact
        self._read_bleed()         # P30-F: each part's health sampled, its bleed's rate read by `_dress_waits`
        self._release_edges()   # P25-X: a zombie refused across a blocked edge, read on the player's side, is free
        self._door_held_read()   # P30-C: a zombie behind a door within DOOR_HELD_R, decided before the hold counts
        self._held, self._breach_now = [], None
        self._read_spent()
        self._many_tail_read()
        held = self._within(self._hold_r())
        sought = self._sought() if self.ENGAGE else None
        if sought:   # P24-X: one or two within ENGAGE_R, the fight sought
            held, self.engaging = sought, True
        elif held and self._released(held):   # Task 18 fix 1, major 2: nothing left the fight may reach
            held = []
        if not held:
            self.mode, self.fight, self.flee = None, None, None
            self.many_since = None   # P24-AR: the long flee's clock ends with the threat
            self.rest_from = None    # P27-C2: and the hold's rest
            self.low_left = set()    # P27-K2: and the low fight's exits
            self._end_flee_episode()
            self.sheltered, self.cornered, self.closing = False, None, (0, None)
            self.stuck_heading, self._nearest_seen = None, []
            self._still_rec = None   # P30-E: the still read starts again with the next threat
            self.leave = None   # Plan 33 Task 3: the leave ends with it
            self._disposition_read(held)   # Plan 37 Task 3: and the disposition
            return
        self._nearest_seen = (self._nearest_seen + [self._nearest_listed()])[-(CARE_STILL_TICKS + 1):]
        if self.flee is not None:   # a shelter or exit step's end read before the hold (the close may have ended),
            self.flee.threats = held   # over this tick's held records (the stall's and the stuck leg's DANGER_R and
            self._observe(self.flee)   # STUCK_NEAR_R reads: before P24-A (g) the first read saw the last tick's)
            self.held_cut = self.flee.take_held_cut()   # P29-H': its walk cut for a held zombie ahead
        self._held, self._breach_now = held, self._breach(held)
        self._disposition_read(held)   # Plan 37 Task 3: the selector's facts, the release's end, the disposition

    def _many_tail_read(self):
        """Ruling P27-B (E18, `e_day_18-20261102-224036`: on 168 of its 302 `many` lines one zombie or none stood within
        DANGER_R, F9's 105 of 169; the guides' notes § 4: draw a group out and turn on the lead one once it strings
        out), the `many` episode's tail, read once a tick before the decision: while a flee episode whose reason was
        `many` runs (`mode` "flee", `flee_many`) with `MANY_TAIL` on, a tick with at most one standing zombie (not
        `onFloor`) within DANGER_R and at most one of the listed pressing (`_pressing` of the zombies the listing
        counts, `_counts_listed`) adds one to `many_tail_n`, and any other tick resets it (two or more standing within
        DANGER_R never end the episode, so P23-AM 1's flips do not return); at MANY_TAIL_TICKS the episode ends
        (`flee_many` cleared, the count reset, logged `many_tail` {ticks, standing, pressing} on that tick's threat why)
        and the tick decides by the ordinary rules, the lone one fought where they allow it (the hold's if spent); a
        `many` read after it starts a new episode as today. Else the count is 0."""
        self.many_tail = None
        if not (self.MANY_TAIL and self.mode == "flee" and self.flee_many):
            self.many_tail_n = 0
            return
        stand = sum(1 for z in self._within(DANGER_R) if not on_floor(z))
        pressing = self._pressing([z for z in self._within(LISTED_R) if self._counts_listed(z)])
        self.many_tail_n = self.many_tail_n + 1 if stand <= 1 and pressing <= 1 else 0
        if self.many_tail_n >= MANY_TAIL_TICKS:
            self.many_tail = {"ticks": self.many_tail_n, "standing": stand, "pressing": pressing}
            self.flee_many, self.many_tail_n = False, 0

    def _threat(self):
        """The threat branch: the tick's bookkeeping (`_threat_read`, read in `_read` with `OBSERVES_IN_READ` on); then
        the care's commitment (`_care_commit`, Plan 32 Task 5 (c)) and the yield to the care (`_care_yields`, P24-P),
        both barred but the ride under a column (Plan 34's LEAVE_CARE, logged `care_withheld` on the line's why), else
        the decision (`_decide`), which a corner's retarget may re-plan without them. Plan 36 Task 4 (ACTION_CLOCK,
        `clock.py`): first, a running timed action the clock lets run is held (`_clock_hold`, no row supersedes it)
        and one under the margin is cut into the melee (`clock_cut`, `_threat_plan`'s first row); the decision's own
        timed command asks the clock (`_clock_threat`); logged `clock` on the why."""
        self.trapped_pass = False
        if not self.OBSERVES_IN_READ:
            self._threat_read()
        held, breach = self._held, self._breach_now
        if not held:
            if self.avoid:   # Task 18 fix 1: the zombies within ENGAGE_R no engage reaches, logged as the goal runs
                self.why = {"unsought": sorted(self.avoid, key=repr)}
            return None
        ride = self._engaged_ride()   # Plan 37 Task 3 fix 3: the rip riding the engaged melee, first
        if ride is not None:
            self.care_yield = None
            self.why = {"care_ride": self.care_ride, "fight": True, "held": len(held)}
            if self.clock_now is not None:
                self.why["clock"] = self.clock_now   # fix 4: the start the clock allowed
            self._disposition_whys()
            return ride
        if self._clock_on():   # Plan 36 Task 4: a running timed action is cut by the clock only (`clock.py`)
            hold = self._clock_hold()
            if hold is not None:
                self.care_yield = None
                self.why = {"clock": self.clock_now, "held": len(held)}
                self._disposition_whys()
                return hold
        self.care.no_stop = False
        if self._fight_disposed():   # Plan 37 Task 3 fix 6: no care supersedes the engaged melee, no care leg
            if self._care_gate():
                self.care_yield = self._yield_near()
                self.why = {"care": True, "care_start": self.care_start, "held": len(held)}
                self._disposition_whys()
                return None
            self.care_yield = None
            ans = self._clock_threat(held, breach, self._decide(held, breach))
            if self.clock_now is not None:
                self.why = dict(self.why or {}, clock=self.clock_now)
            if self.care_hold is not None:
                self.why = dict(self.why or {}, care_hold=self.care_hold)
            self._disposition_whys()
            return ans
        commit = self._care_commit(held)   # Plan 32 Task 5 (c): one leg, then the care's action finished
        if commit is not None and commit[0] == "leg":
            self.care_yield = None
            self.why = {"care_commit": self.care_commit, "held": len(held)}
            if self.engage_yield is not None:   # Plan 35 fix 2: the bleed's leg over the engaged melee
                self.why["engage_yield"] = self.engage_yield
            return commit[1]
        self.care_yield = commit[1] if commit is not None else self._care_yields(held)
        if self.care_yield is not None and not self.care.ride_now and self._care_engage_holds():
            self.care_yield, self.bleed_yield, self.scratch_yield = None, None, None   # Plan 35: no care over the
                                                                                       # engaged melee
        if self.care_yield is not None:
            self.why = {"care": True, "nearest": self.care_yield, "held": len(held)}
            if commit is not None:
                self.why["care_commit"] = self.care_commit
            if self.care.ride_now:
                self.why["ride"] = {"flee": self.ride_flee} if self.ride_flee else True   # P27-O: the health ride
            if self.scratch_yield is not None:
                self.why["care_yield"] = {"why": "scratch", "near": self.scratch_yield}   # Plan 31 Task 15a
            if self.bleed_yield is not None:
                self.why["care_yield"] = {"why": "bleed", "near": self.bleed_yield}   # P26-D
                if self.bleed_held:
                    self.why["care_yield"]["held"] = True   # P26-L2: held only by the dressing's hold
            ans = None
        else:
            ans = self._clock_threat(held, breach, self._decide(held, breach))   # Plan 36 Task 4: its own timed
                                                                                 # command asks the clock
        if self.clock_now is not None:
            self.why = dict(self.why or {}, clock=self.clock_now)   # Plan 36 Task 4
        if commit is None and (self.care_commit or {}).get("phase") == "spent":
            self.why = dict(self.why or {}, care_commit=self.care_commit)   # Plan 36 Task 4: the care's episode spent
        if self.many_tail is not None:
            self.why["many_tail"] = self.many_tail   # P27-B: the tick the `many` episode's tail ended it
        if self.care_withheld is not None:   # Plan 34 (LEAVE_CARE): the care barred under a column
            self.why = dict(self.why or {}, care_withheld=self.care_withheld)
        if self.engage_yield is not None:   # Plan 35 fix 2: the engagement yielded to the bleed's care
            self.why = dict(self.why or {}, engage_yield=self.engage_yield)
        self._disposition_whys()
        return ans

    def _disposition_whys(self):
        """Plan 37 Task 3: this tick's `disposition` change, `release` hand-over and `string_heading` on the threat
        why, whichever row answered."""
        for key, v in (("disposition", self.disposition_why), ("release", self.release_why),
                       ("string_heading", self.string_why), ("care_ride", self.care_ride),
                       ("care_start", self.care_start)):
            if v is not None:
                self.why = dict(self.why or {}, **{key: v})

    def _decide(self, held, breach, replanned=False):
        """`_threat_plan`'s decision executed by the Fight or the Flee, logged in `why`."""
        kind, reason = self._threat_plan(held, breach)
        if kind == "pass":   # P29-E: the threat episode ends, the care branch (and every branch after it) answers
            self.mode, self.fight, self.flee = None, None, None
            self._end_flee_episode()
            self.why = {"health_near": self.health_near, "held": len(held)}
            return None
        if kind in ("hold", "doorway"):
            self.rest_from = None   # P27-C2 (Task 1 fix 1): held inside or standing a doorway is not the hold's rest
        if kind == "hold":
            self.why = {"flee": "held_inside", "held": len(held)}
            return None, None
        if kind == "doorway":
            return self._stand(held)
        door = self.door if kind == "door" else None
        want = "flee" if kind == "flee" else "fight"
        walk = False
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
                if self.point_blank_fight is not None:   # Plan 32 Task 5 (a): the fight at the point-blank zombie
                    self.fight.target = self.point_blank_fight["target"]
                self.fight.pull = self.fight.seek and self.PULL    # P24-AN: a lone chaser pulled from the group
                if door is None:
                    self.flee = None   # a door fight keeps the sheltered Flee for the re-close
                self._end_flee_episode()
            else:
                if self.flee is None or not (self.sheltered or self.flee.closing_stand()
                                             or self.stand_left is not None):   # a sheltered Flee outlives a door
                    # fight, and a stand's Flee its Doorway (P24-AO; one whose stand was left `off` only steers, one
                    # left under a group walks out, P25-W)
                    self.flee = Flee(self.world, self.actions, self.clock, shunned=self.night.shunned)
                    self.flee.skip_heading, self.stuck_heading = self.stuck_heading, None   # fix 2, G2
                if self.fight is not None:   # P25-J (3), 8 fix 1: the pair flee's finish reads the Fight's refusals
                    self.fight_refused = self.fight.swing_refused
                self.fight = None
                self.stall_flee = reason == "stalled"
            self.mode = want
        if want == "fight" and door is None:
            self.flee = None   # a door fight that left the room: the stale shelter plan goes (the next flee re-picks)
        policy = self.fight if want == "fight" else self.flee
        self.flee_reason = reason if want == "flee" else None   # P26-D: the leg's reason, read by the next yield
        if want == "flee":
            self.flee_many = self.flee_many or reason == "many"
            self.flee_health = self.flee_health or reason == "health"
            if reason == "health" and self.health_since is None:
                self.health_since = self.clock()   # P27-O: the health flee's clock, kept for its episode
            if reason == "many" and self.many_since is None:
                self.many_since = self.clock()   # P24-AR: the long flee's clock, kept across its corners
            policy.threats = held
            policy.hold_ok = breach is None
            policy.steer_now = self.group_steer is not None
            # Plan 37 Task 3: the `break` steer off a room square reads the map's open line and the ring's open half
            policy.open_run = self.disposition == "break" and self._disposing() and not self.night.inside()
            policy.rules = self._flee_rules()   # P25-E, P26-A, P26-B, P26-I, P26-J, Plan 34 Task 2 (DOOR_INSIDE)
            # Plan 34 Task 2 (LEAVE_DOOR_RACE): the leave's pick refuses a one-exit building as its leg read did
            policy.second_exit = True if reason == "leave" and self.LEAVE_DOOR_RACE else None
            walk = self._hold_walk(reason)   # P25-C: the endurance hold's flee walks with nobody within DANGER_R
            policy.gait = "walk" if walk else FLEE_GAIT
            policy.keep_gait()
            policy.stand_ok = self.DOORWAY and (self.flee_many or reason == "leave") and stand_ready(
                self.world, blocked(self.dead, self.clock()))   # Plan 33 Task 3: the leave's door is a stand
            if self.group_steer:
                policy.give_way()   # amendment 6: the group pre-empts a running walk, as the corner does
            if self.group_steer == "drag":
                policy.drop_stuck_leg()   # P24-A fix 2, I1: never a stalled leg held its FLEE_S under the guard
            self.pair_yield = None   # P25-J (3): a flee's yield is the `pair` flee's own finish (`_pair_flee_finish`)
            ans = self._flee_drop() or self._flee_finish(reason)
            idle = None if walk or reason != "strain" else self._hold_idle()   # P27-J (a): an idle zombie in reach
            # P27-C2: the hold's walk with no chaser is the rest
            rest = ans is None and (walk or idle is not None) and self._hold_rest()
            if ans is None:   # P29-D: a running dressing waited on with nobody within DANGER_R
                ans = self._rest(policy, idle) if rest else (self._dress_waits(policy) or self._answer(policy))
            if not rest:
                self.rest_from = None
            pick = self._doorway_pick(policy) if reason == "many" and self.PICK_WHY else None   # P24-AX, after the pick
        else:
            policy.only = None if door is None else {zid for zid, _ in door}
            policy.stance = self._stance_ok(held, self.night.inside())   # P24-G 1 (no corner or door Fight stands)
            policy.spent = self._fight_spent()   # R2: no swing under any hold
            policy.hold_ground = self._chokepoint()   # Task 18 fix 1, ruling 2: no seek from a room or door square
            policy.avoid = self.avoid                 # ... nor at a zombie no engage reaches (major 2)
            policy.ride = self.care.riding()   # P24-U: the stance legs held off while a bandage rides
            policy.threats = held
            policy.retreat = self.retreat   # Plan 33 Task 3 fix 3: GROUP_LEAVE's fighting retreat heading, else None
            # Plan 36 Task 3: the engagement picker's withdraw (`_pull_ok`) whose melee can go (`_melee_on`: no
            # golden's hello announces `melee`); Plan 37 Task 3: the disposition, its withdraw and the release
            self._disposition_inputs(policy, kind, door)
            policy.backswing = self.BACKSWING   # Plan 36 Task 2a addendum (T21_SWITCHES): the work's backswing
            policy.edge_ticks = EDGE_HOLD_TICKS if self.EDGE else 0   # P24-AU, read at the policy's observe
            policy.rules = self._fight_rules()   # P25-A, P25-B, P25-D, P25-F
            policy.edge_marks = self.edge_marks   # P25-X: the refusals across a blocked edge, shared as `unreachable`
            policy.close_left = self.close_left   # P27-J: the shove-only close's refusals across a blocked line
            policy.shove_only = self._shove_only(kind)   # P25-P, P25-S: no swing, no seek
            policy.door_open = self.door_open   # P30-C: the stance_open plan's steps, this tick's
            policy.crowd = self._inside_crowd() if kind == "cornered" else None   # P26-C
            still = (None if replanned or kind != "fight" or door is not None or policy._engaged()   # Plan 35: never
                     else self._still_read(held, policy))   # over the engaged melee (its approach nor its pass)
            if still is not None and still[0] == "goal":   # P30-E: the zombie left, the branch passes
                self.mode, self.fight, self.flee = None, None, None
                self._end_flee_episode()
                self.why = {"still": self.still_now, "held": len(held)}
                return None
            if still is not None:   # P30-E: the stance's approach at the still zombie
                self._observe(policy)
                cmd = policy._stance_leg(still[1], still[2], still[3], kind="toward")
                self.why = dict(policy.why, still=self.still_now)
                ans = (policy, cmd)
            else:
                ans = self._answer(policy)
            self.rest_from = None
            if self.why.get("low_exit") is not None:   # P27-K2: the low fight left its lone target, the flee next
                self.low_left.add(self.why["low_exit"]["target"])
            if self.pair_yield is not None and not self._finishes(self.pair_yield):
                self.pair_yield = None   # P25-J (3): logged only where the Fight's finish answers it
        self.why.update({"fight": True} if reason is None else {"flee": reason})
        if want == "fight" and policy.shove_only is not None:   # P25-P, P25-S, P27-C: the Fight's shove and stomp
            self.why[SHOVE_ONLY_WHY[policy.shove_only]] = True
        if reason == "strain" or self.corner_yield == "strain":
            self.why["strain"] = self.spent   # P24-AG: the why names the strain
        if want == "flee" and walk and self._walking(policy, ans):
            self.why["hold_walk"] = True   # P25-C: the flee's leg sent or running at a walk
        if want == "flee" and self.stand_exit is not None:   # P25-W: the stand's end walks out; the way the Flee took
            self.why["doorway_exit"] = self._stand_exit_why(policy)
        if want == "flee" and policy.door_walk is not None:   # P25-E: the stand's stalled walk, read at its observe
            self.why["door_walk"] = policy.door_walk
            if policy.door_walk["end"] == "drop":
                self.stand_end = "stall"   # logged `doorway_left` below
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
        if want == "flee" and pick is not None:
            self.why["doorway_pick"] = pick
            if self.one_exit_refused is not None:
                self.why["doorway_one_exit"] = self.one_exit_refused   # P26-B: the building the pick refused
        for key, v in (("yield", self.corner_yield), ("behind", self.behind), ("listed", self.listed),
                       ("doorway_left", self.stand_end), ("pain", self.wound), ("finish_block", self.finish_block),
                       ("doorway_wound", self.stand_wound), ("doorway_crowd", self.stand_crowd),
                       ("doorway_drag", self.stand_drag),
                       ("doorway_inside", self.stand_inside),
                       ("pair_yield", self.pair_yield), ("listing", self.listing), ("corner", self.corner_exit),
                       ("health_near", self.health_near), ("many_near", self.many_near),
                       ("finish_lone", self.finish_lone), ("flee_held_stance", self.held_cut),
                       ("point_blank_fight", self.point_blank_fight), ("strain_bound", self.strain_bound),
                       ("group_leave", self.group_leave), ("group_retreat", self.group_retreat),
                       ("engage_hold", self.engage_hold), ("engage_pull", self.engage_pull),
                       ("engage_dispatch", self.engage_dispatch)):
            if v is not None:
                self.why[key] = v
        if self.broken is not None:
            self.why["breach"] = self.broken
        ride = self.care.riding()
        if ride is not None:
            self.why["ride"] = ride.aid   # P24-U: a bandage rides the leg this answer holds or re-aims
        self.trapped_pass = want == "flee" and ans is None and "trapped" in self.why   # P25-Q: read by `assess`
        return ans if ans is not None else (policy, None)

    def _dress_waits(self, flee):
        """Ruling P29-D (`DRESS_FINISH`; E22, `e_day_22-20261105-004919`: twelve dressings superseded by the flees'
        steers at a run, four of them on lines reading no zombie within 6 tiles, lines 463, 470, 536 and 542, while the
        four parts bled undressed 9.315 to 19.103 game minutes, #4627): `(flee, None)` when the Flee would choose (no
        leg of its own running, `busy`) while the care's dressing runs (a `bandage` accepted and not ended: the ride
        whose leg ended, `Care.riding`, or a standing one, `Care.busy`) with no zombie within DANGER_R: the flee waits
        on the dressing's end as a running leg holds it, logged `dress_finish` {action, near 0}; a zombie within
        DANGER_R supersedes it as before. Else None. Cost if wrong: a dressing's seconds with a chaser coming from
        beyond DANGER_R. Ruling P30-F (`DRESS_RIDE`; E23, `e_day_23-20261105-095110`: the neck bite took the health from
        98.90239715576172 to 49.206119537353516 over 3.7356948852539062 game minutes, #4648, its two riding dressings
        superseded by the flee's next legs, decision lines 245 and 252, before the third landed): the dressing on a
        part whose health falls faster than BLEED_FAST a game minute (`_bleed_rate`) is waited on with a zombie within
        DANGER_R too, superseded only by one within KEEP_R, logged `dress_ride` {part, rate}. Cost if wrong: a
        dressing's seconds with a chaser at 3 tiles."""
        if flee.busy():
            return None
        c = self.care
        a = c.riding()
        if a is None and c.busy() and c.last is not None and c.last.type == "bandage":
            a = c.last
        if a is None or a.type != "bandage":
            return None
        if self.DRESS_FINISH and not self._danger_near():
            self.why = {"dress_finish": {"action": a.aid, "near": 0}}
            return flee, None
        part = a.args.get("part")
        rate = self._bleed_rate(part) if self.DRESS_RIDE else None
        if rate is None or rate <= BLEED_FAST or self._within(KEEP_R):
            return None
        self.why = {"dress_ride": {"part": part, "rate": rate}}
        return flee, None

    def _shove_only(self, kind):
        """Why this tick's Fight is the shove and the stomp alone (`Fight.shove_only`), else None: "unarmed" with no
        weapon held (`_unarmed`, P25-P); for the open-ground Fight (`kind` "fight": no corner nor door fight) "hold"
        for the endurance hold's lone zombie (`_hold_lone`, P27-C) and "low" under FLEE_HEALTH the low fight admits
        (`_low_fight`, P25-S)."""
        if self._unarmed():
            return "unarmed"
        if kind != "fight":
            return None
        if self._hold_lone():
            return "hold"
        return "low" if self._low_fight(len(self._danger_near())) else None

    def _inside_crowd(self):
        """Ruling P26-C: the running corner's count at point blank when it is an `inside` corner (`corner_kind`) with
        `INSIDE_SHOVE` on and the build announcing `shove`: the zombies within POINT_BLANK_R (`_within`: one read dead
        left out), or the frame's `me.attackers` if more; else None (no crowd read, nothing logged)."""
        if not (self.INSIDE_SHOVE and self.corner_kind == "inside" and self.world.can("shove")):
            return None
        return max(len(self._within(POINT_BLANK_R)), self._attackers())

    def _unarmed(self):
        """Ruling P25-P: no weapon held and `UNARMED_FIGHT` on (the Fight's `unarmed`; the `many` flee's finish sends
        no floor strike, a swing)."""
        return self.UNARMED_FIGHT and not self._armed()

    def _finishes(self, zid):
        """The Fight's answer this tick (its `why`) is the finish of `zid`: its stomp (sent or running) or the knock
        wait on it (P24-AV), the `pair` yield's two answers (P25-J (3))."""
        return self.why.get("knocked") == zid or (self.why.get("downed") == zid and self.why.get("stomp") is True)

    @staticmethod
    def _walking(flee, ans):
        """The Flee's command this tick (`ans`), else its running leg, goes at a walk (P25-C's `hold_walk`)."""
        cmd = ans[1] if ans is not None and ans[0] is flee else None
        if cmd is not None:
            return getattr(cmd, "gait", None) == "walk"
        return flee.busy() and flee.last.args.get("gait") == "walk"

    def _fight_rules(self):
        """The iterations 13 to 23 Fight rules (`fight.FIGHT_RULES`, iteration 20's fix 2 included) whose switch is on:
        the Fight's `rules`."""
        return frozenset(rule for rule, on in (("corner_break", self.CORNER_BREAK), ("finish_first", self.FINISH_FIRST),
                                               ("ride_wait", self.RIDE_WAIT), ("fence_wait", self.FENCE_WAIT),
                                               ("finish_far", self.FINISH_FAR), ("shove_break", self.SHOVE_BREAK),
                                               ("shove_break_run", self.SHOVE_BREAK_RUN),
                                               ("blocked_edge", self.BLOCKED_EDGE),
                                               ("wounded_swing", self.WOUNDED_SWING),
                                               ("low_swing", self.LOW_SWING), ("floor_finish", self.FLOOR_FINISH),
                                               ("fallen_seek", self.FALLEN_SEEK), ("shove_close", self.SHOVE_CLOSE),
                                               ("low_exit", self.LOW_EXIT), ("attack_reach", self.ATTACK_REACH),
                                               ("point_blank_pin", self.POINT_BLANK_PIN),
                                               ("busy_retry", self.BUSY_RETRY), ("floor_pain", self.FLOOR_PAIN),
                                               ("shove_back", self.SHOVE_BACK), ("drift_stand", self.DRIFT_STAND),
                                               ("circle", self.CIRCLE), ("approach_walk", self.APPROACH_WALK),
                                               ("melee", self.MELEE), ("route_cross", self.ROUTE_CROSS),
                                               ("close_idle", self.CLOSE_IDLE),
                                               ("swing_close", self.SWING_CLOSE),
                                               ("chaser_stance", self.CHASER_STANCE),
                                               ("pair_nearest", self.PAIR_NEAREST))
                         if on)

    def _flee_rules(self):
        """The iterations 13, 17, 18 and 23 Flee rules (`flee.FLEE_RULES`) whose switch is on: the Flee's `rules`."""
        return frozenset(rule for rule, on in (("door_walk", self.DOOR_WALK), ("window_exit", self.WINDOW_EXIT),
                                               ("stand_second_exit", self.STAND_SECOND_EXIT),
                                               ("window_inner", self.WINDOW_INNER),
                                               ("window_stall", self.WINDOW_STALL),
                                               ("flee_held_stance", self.FLEE_HELD_STANCE),
                                               ("door_inside", self.DOOR_INSIDE))   # Plan 34 Task 2
                         if on)

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
