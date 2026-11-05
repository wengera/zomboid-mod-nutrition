"""The Fight (Plan 22 Task 10, spec § 3; Plan 23 Task 10's pinned target), one of the multi-step policies whose
common rules (`Policy`, one action at a time, distances, the shared reads) are `policies.py`'s; moved out of it whole
at Plan 24 Task 36 (a pure move: its rules, constants and record unchanged; the constants stay in `policies.py`, the
one table the gates and the other policies import).

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
  aim; the Lua releases the stance on an attack's first tick and keeps none after it) an `enter` leg (0, 0),
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
  to it (`busy`). At the swing (`_shove`, `shove.py`'s mixin since Plan 25 Task 8, with `_corner` and P25-L's break):
  P24-AG, with `body.armPain` at STRAIN_SOFT or above a standing target at point blank is shoved, never swung at;
  P24-AH, in a standing fight a second standing zombie inside KEEP_R makes the nearer of the two (within SHOVE_R)
  shoved before the next swing, once a swing (`_shoved`); neither with another standing zombie within STAND_MIN_R.
  A shove's or stomp's `targetDead` is a kill (SWING_TYPES), a started stomp counts in the no-progress streak.
  Survival 12 (survival iteration 11; Plan 24 Task 32; survive.py's docstring the record): P24-AN, the pull: with
  `pull` set (Survive's sought fights), a lone chaser (`pull_from`: it alone chases within ENGAGE_R, the rest of the
  listing beyond DANGER_R) is pinned first (`_pull_pin`) and, beyond PULL_R (FIGHT_REACH + KEEP_R), its stance legs
  walk away from the rest's centroid facing it (`pull`, `pulling`), the seek's switch to a nearer zombie off; within
  PULL_R it is `sought` (the stance stands for it, never a seek toward it past the group), and once pulled it is kept
  to DISENGAGE_R (`_pull_waits`: past ENGAGE_R it is stood for, never sought back). P24-AP, the wounded fight: at
  `body.armPain` STRAIN_HARD (`arms_hurt`), or under any hold Survive reads (`spent`, ruling R2 of Task 32 fix 1:
  the arms', the endurance or the tired hold; `no_swing`), the Fight never swings, the floor strike included: the
  shove at point blank (P24-AG's, every time), the stomp of a fallen one, else the backpedal facing the target
  (`_wounded_leg`, held by `busy` until point blank; with no stance announced nothing). P24-AS (amendment 1): every heading read (`clear_heading`:
  the steer's turns, the backpedal, the pull, the seek's and the advance's lines) and the way out's end (`_beyond`)
  refuse a `solidTrans` square (the policy's `trans`, Survive's TRANS switch); the fight's line of sight does not.
  The doorway stand's Fight is `planner/doorway.py`'s `Doorway`; the Flee keeps its stand plan (`stand_ok`, the
  pick's `stand`, the enter's end read `stand`, `standing_door`, `closing_stand`).
  Survival 13 (survival iteration 12; Plan 24 Task 36; survive.py's docstring the record): P24-AU, the listing-edge
  hold (`_observe_edge`): a zombie that leaves the listing (beyond LISTED_R) is kept in `edge` at its last listed
  record for `edge_ticks` observes (EDGE_HOLD_TICKS; Survive's EDGE switch), and the pull's group reads it there
  (`pull_centroid`, `policies.pull_from`'s `edge`), so the leg does not flip between `pull` and `seek` each tick.
  P24-AV: the finish (`_finish`) stomps only a zombie the frame reads `onFloor`; one a shove read knocked down within
  KNOCK_READ_S and no frame reads fallen yet is waited on (`_knock_wait`, logged `knocked`, nothing sent); a stomp
  failed `stood` reads the target again (standing, the shove or the swing; fallen, one more stomp), the STOOD_STOMPS-th
  `stood` taking the floor strike (`stood`, `_observe_swing`).
  Survival 19 (survival iteration 17; Plan 26 Task 2; survive.py's docstring the record): P26-C, the inside corner's
  shove: an `inside` corner's Fight (`crowd`, Survive's count of the zombies within POINT_BLANK_R, `me.attackers` if
  more; None for any other Fight) at INSIDE_CROWD_N or more shoves its target at the swing (`_crowd_shove`), the stomp
  of a fallen one in reach going first as ever (`_finish`); with one at point blank the swing stands. Every shove,
  stomp or attack such a Fight sends is logged `corner` {kind "inside", send, near_n} (`choose`).
  Survival 20 (survival iteration 18; Plan 26 Task 7d; survive.py's docstring the record): P26-L1, the divided swing
  after failed shoves: under the `wounded` reason alone, at a lone standing target at point blank with SHOVE_FAIL_N
  missed shoves on record, the swing in the shove's place (`shove.FightShove._wounded_swing`), ahead of the corner and
  the breaks; a second zombie within DANGER_R gives them back.
  Survival 22 (survival iteration 20; Plan 27 Task 5; survive.py's docstring the record): P27-G, the floor swing as the
  finish: with a weapon held and the swing allowed, a fallen zombie within FIGHT_REACH takes the attack ahead of the
  stomp, and a running attack at a zombie it knocked down is held to its end (`finish.FightFinish._floor_finish`,
  `_finish_gives_way`); P27-H, the stance at a fallen target beyond FINISH_R for FALLEN_SEEK_TICKS walks to it, or with
  a standing zombie within DANGER_R or its line blocked leaves it (`finish.FightFinish._fallen_seek`); P27-J, a
  shove-and-stomp Fight whose lone chaser holds beyond point blank for SHOVE_CLOSE_TICKS walks to it, or with its line
  blocked leaves it (`shove.FightShove._shove_close`); P27-K2, the low fight leaves its lone target after SHOVE_FAIL_N
  missed shoves where its full swing is barred or has gone (`shove.FightShove._low_exit`).
  Its fix 2 (Plan 27 Task 5 fix 2; E20): P27-M, the attack within reach: the standing fight's attack at a standing
  zombie goes only within the frame's `weapon.reach` plus ATTACK_MARGIN (`reach_r`, logged `attack` {dist, reach};
  `reach.FightReach`); beyond it within FIGHT_REACH the stance stands facing it and lets it come (`_attack_hold`,
  logged `attack_held` {target, dist, reach}), and the advance walks at a walk to the reach (`_reach_walk`, the stance
  walk `reach`, logged `reach_walk`) where the `toward` legs went; the finish of a fallen zombie keeps FIGHT_REACH.
  P27-N, a zombie at point blank is never dropped: one within POINT_BLANK_R, or the nearest listed on a frame reading
  it attacking (kept while within FIGHT_REACH), is left out by no mark (`_pin_free`, `blocked`; `pin.FightPin`); a
  marked one takes the pin (`_pin_first`) and is shoved, then swung at, on every tick that may send (`_pin_send`,
  logged `pin` {why}, apart from the target flag `pinned`).
  Survival 23 (survival iteration 21; Plan 28 Task 3; F11, `f_goals_12-20261103-144240`; survive.py's docstring the
  record): P28-D, a `busy` rejection is no refusal: a shove or a stomp `rejected` `busy` (the player mid-swing or in a
  hit reaction, the Lua's check) leaves its target in that skill (no `swing_refused` record), latched in `_busy_retry`
  until the next send of that kind at that id, logged `busy_retry` {target, kind} (`_observe_swing`, `choose`).
  P28-C, the floor swing under the arms' pain: the swing at a fallen zombie within FIGHT_REACH (the finish's
  `_floor_finish`, the floor strike after a refused stomp) is barred by a hold or a shove-only Fight, never by
  `arms_hurt` alone (`floor_swing_barred`), logged `floor_finish` {.., pain}. The approach walk (the spec's 1 (b),
  ruling P27-9: E20's a190 ran 1.762922801715824 tiles into 3189, #4571; Survive's APPROACH_WALK since fix 1): a
  Fight not in the stance walks at a walk, never a run, to a zombie beyond FIGHT_REACH and on the approach after
  MISSES_TO_APPROACH unstarted swings, logged `leg` "walk".
  P28-B (the strike before the zombie's attack; F11's #4580; P28-B1's early shove withdrawn by the jar read, the
  engine's shove reach 1.1 the point-blank band itself, #4592, so SHOVE_R reads 1.1): B2, after a missed point-blank
  shove the stance's `back` leg in the second shove's place (`shove.FightShove._shove`, logged `shove_back`); B3, a
  cornered Fight's pin standing beyond CORNERED_R, chasing within DANGER_R on a line not read blocked, takes the
  stance's standing leg (`_drift_stands`, logged `out_of_reach` with `stance`), held while it comes beyond CORNERED_R
  (`busy`), where it sent nothing before.
  P28-E, the circle: the stance's `back` leg with exactly one standing zombie within KEEP_R (its target) turns
  CIRCLE_TURN off the straight away heading, the side last used first while `clear_heading` passes it, else the other,
  else straight away and STEER_TURNS as before (`_circle_turn`, logged `circle` {turn}); two or more standing within
  KEEP_R keep the straight backpedal.
Survival 24 (survival iteration 22; Plan 28 Task 7b, cut 1 of the maneuver layer; the architecture review
`arch-review-cerebellum.md` § 3.5; survive.py's docstring the record): the melee maneuver (`dispatch.FightDispatch`,
its module docstring the rule): with the `melee` rule on (Survive's MELEE) and the build announcing PZA/1.8's `melee`,
where the ladder (`_ladder`, every rule above) would send an in-reach `aim` leg (`enter`, `back`, `stand` within
KEEP_R), an `attack`, a `shove`, a `stomp` or a floor swing at its pin within MELEE_RELEASE_R, the Fight starts or
continues its `Melee` (`m`, `maneuvers.melee`) instead, which Task 7a's Lua skill runs at the client's tick rate:
mode strike, shove (`_hold_bars`: P28-H dropped the arms' pain from the mode) or finish (a fallen pin), its `back`
heading P28-E's, re-sent with a fresh one before MELEE_S runs out (`melee` {mode, pain} on every send, `resend` on one);
`busy` holds it as it holds a leg, a flee's hand-over supersedes it, its kill is
read once (`_read_dead`) and a span of strikes with no health fall counts in the no-progress streak. Everything above
the dispatch point is unchanged, and the corner Fight (`point_blank`), the door fight (`only`), the doorway stand and
the flee's finish keep the ladder in cut 1; nothing of the ladder is deleted (cut 2 deletes once cut 1 reads no
worse).
"""
import math
import time

from agent.base.planner.dispatch import FightDispatch
from agent.base.planner.edges import FightEdge
from agent.base.planner.finish import FightFinish
from agent.base.planner.policies import (AIM_LEG_S, AIM_R, CIRCLE_TURN, CORNERED_R, DANGER_R,
                                         DISENGAGE_R, DRAG_DOWN_N, EDGE_HOLD_TICKS, FENCE_BACK_R, FIGHT_MAX_S,
                                         FIGHT_REACH, FINISH_R, KEEP_MARGIN, KEEP_R, KNOCK_READ_S, MISSES_TO_APPROACH,
                                         NO_TARGET, POINT_BLANK_R, PREEMPTED, PULL_R, Policy, REPIN_MARGIN,
                                         REPOSITION_MIN, REPOSITION_R, SEEK_SKIP_S, SEEK_SWITCH_R,
                                         STALL_SWINGS, STAND_MAX_S, STEER_PROBE, STEER_TURNS,
                                         STOOD_STOMPS, STUCK_REASONS,
                                         SWING_SKIP_S, SWING_TYPES, UNREACHABLE_S, _rotate, arm_pain,
                                         arms_hurt, away_vector, blocked, centre, chasing, clear_heading, hit_reaction,
                                         in_reach, line_to, on_floor, seek_allowed, stance_leg_kind, target_id_ok,
                                         zdist)
from agent.base.planner.pin import FightPin
from agent.base.planner.pull import FightPull
from agent.base.planner.reach import FightReach
from agent.base.planner.shove import FightShove
from agent.base.pza1 import Aim, Attack, WalkTo
from agent.base.world import me_floor, me_xy

__all__ = ["Fight", "FIGHT_RULES"]

FIGHT_RULES = ("corner_break", "finish_first", "ride_wait", "fence_wait", "finish_far", "shove_break",
               "shove_break_run", "blocked_edge", "wounded_swing", "low_swing",
               "floor_finish", "fallen_seek", "shove_close", "low_exit", "attack_reach",
               "point_blank_pin", "busy_retry", "floor_pain", "shove_back",
               "drift_stand", "circle", "approach_walk", "melee")   # survival iterations 13 to 22's Fight
                     # rules (P25-A, P25-B, P25-D, P25-F; P25-J, P25-L; P25-T; P25-X; P26-L1; P27-E; P27-G, P27-H,
                     # P27-J, P27-K2; fix 2's P27-M and P27-N; P28-D, P28-C, P28-B2, P28-B3, P28-E, the approach walk;
                     # the melee, cut 1 of the maneuver layer), each on in `rules` unless Survive's switch for it is
                     # off


class Fight(FightPull, FightFinish, FightShove, FightEdge, FightPin, FightReach, FightDispatch, Policy):
    """The Fight (the module docstring), with its rules in mixins, the state the Fight's own:
    - `FightPull` (`pull.py`): the pull of a lone chaser and the listing's edge hold (P24-AN, P24-AU);
    - `FightFinish` (`finish.py`): the finish of the fallen and the stomp (P24-AL, P24-AV, P25-B, P25-J, P27-G, P27-H);
    - `FightShove` (`shove.py`): the shove at the swing and the corner after a missed shove (P24-AG to P25-L, P26-L1,
      P27-E, P27-J);
    - `FightEdge` (`edges.py`): the route round a blocked edge (P25-X);
    - `FightPin` (`pin.py`): the point-blank pin, a zombie at point blank or attacking never dropped (P27-N, fix 3);
    - `FightReach` (`reach.py`): the attack within the weapon's reach and the walk to it (P27-M);
    - `FightDispatch` (`dispatch.py`): the melee maneuver in the ladder's in-reach sends' place (survival iteration
      22, cut 1 of the maneuver layer)."""

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
        self.knocked = {}                   # zombie id -> wall until a shove's knockdown is waited on (KNOCK_READ_S)
        self.stood = {}                     # zombie id -> its stomps failed `stood` (P24-AV, STOOD_STOMPS)
        self.pull = False                   # Survive sets it on a Fight it seeks (ruling P24-AN): a lone chaser pulled
        self._pulled = None                 # the zombie id the last pull leg was sent at (P24-AN)
        self.doorway = None                 # the building a doorway stand holds (`planner.doorway.Doorway`), else None
        self.spent = ()                     # Survive sets it each tick: the holds read (ruling R2), no swing under any
        self.edge_ticks = EDGE_HOLD_TICKS   # Survive sets it each tick (its EDGE switch; 0 the rule before P24-AU)
        self.edge = {}                      # zombie id -> [ticks unlisted, its record at its last listed square]
        self._listed = {}                   # zombie id -> its record, of the zombies within LISTED_R at the last observe
        self.rules = frozenset(FIGHT_RULES)  # Survive sets it each tick: the iteration-13 rules its switches leave on
        self._shove_a = {}                  # zombie id -> the last shove sent at it (P25-A: its end and its wall)
        self._fence_leg = None              # the fence wait's leg kind the last aim was sent for (P25-F), else None
        self._misses = None                 # (zombie id, [send walls]) of the missed shoves in a row at it (P25-L)
        self._miss_run = {}                 # zombie id -> its missed shoves since its last knock-down (P25-T)
        self.edge_marks = {}                # Survive shares its own: zombie id -> the blocked edge it was refused
                                            # across (P25-X, `edges.FightEdge`), released by the threat branch
        self._edge_send = None              # (target id, edge) of the route walk the running choose returns (P25-X)
        self._edge_walk = None              # (walk, target id, edge) of the last route walk sent, until its end is read
        self.blocked_edge = None            # this choose's `blocked_edge` why (P25-X), else None
        self.shove_only = None              # Survive sets it each tick: why the Fight is the shove and the stomp
                                            # alone, "unarmed" (P25-P), "low" (P25-S) or "hold" (P27-C), else None:
                                            # no swing, no seek
        self.crowd = None                   # Survive sets it each tick: an `inside` corner's count at point blank
                                            # (P26-C, `_crowd_shove`), else None
        self._fallen = None                 # (target id, consecutive observes it read fallen beyond FINISH_R) (P27-H)
        self._close = None                  # (target id, consecutive observes it held beyond point blank) (P27-J)
        self._low_swung = set()             # the ids the low fight's full swing went at (P27-E), its exit's (P27-K2)
        self.close_left = {}                # Survive shares its own: zombie id -> wall until a close refused for its
                                            # blocked line leaves it out of the hold's reads (P27-J)
        self._init_pin()   # P27-N: the attacker latch and the tick's pin read (`pin.FightPin`)
        self._busy_retry = None             # (shove or stomp, zombie id) of the last send rejected `busy`, until the
                                            # next send of that kind at that id or another end at it (P28-D)
        self._circle_side = 1               # the side the last circling `back` leg turned (+1 first, -1), kept (P28-E)
        self._backed = {}                   # zombie id -> the missed shove a `shove_back` leg answered (P28-B2: one leg
                                            # a miss)
        self._back_leg = None               # (aim action, zombie id) of the last `shove_back` leg (P28-B2), else None
        self._back_left = False             # that leg's target was read beyond POINT_BLANK_R since it was sent
        self._init_dispatch()   # survival iteration 22: the running maneuver, `m` (`dispatch.FightDispatch`)

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
        corner's reach: a dead zombie is never swung at). Ruling P27-N: a mark made before this choose leaves no
        `_pin_free` zombie out (this choose's own marks, `_marked_now`, still do: the recursion never re-pins them)."""
        out = self.marked()
        free = self._pin_free()
        if free:
            out = (out - set(free)) | self._marked_now
        return out | blocked(self.dead, self.clock())

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
        for sq in self.world.reachable_adjacent((z["x"], z["y"]), floor, self.trans):   # P24-AS (fix 1, minor 8)
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

    def _observe_back(self, t):
        """Ruling P28-B2 (fix 1, M1): while the last `shove_back` leg runs, a read of its target beyond POINT_BLANK_R
        marks it left (`_back_left`), so its return within POINT_BLANK_R gives the leg way to the shove (`busy`)."""
        if (self._back_leg is not None and self.last is self._back_leg[0] and not self.actions.done(self.last)
                and t is not None and t[0] == self._back_leg[1] and t[2] > POINT_BLANK_R):
            self._back_left = True

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
        return (self.seek and self.shove_only is None and t is not None and t[0] not in self.sought
                and seek_allowed(self.world, t, self.hold_ground) and not self._pull_waits(t))

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
        if (self._advance_switch(t) if kind in ("advance", "reach") else self._seek_switch(t)) is not None:
            return True   # fix 2: the advance's walk gives way to a closing zombie as the seek's does
        if kind == "reach":   # P27-M: the advance's walk ends within the reach and its margin, or as the target comes
            r = self.reach_r()
            return (r is None or t[2] <= r or not self.advance or not self.stance_at(t[2])
                    or (t[2] <= FIGHT_REACH and chasing(t[1])))
        if kind == "far":
            return t[2] <= AIM_R
        if kind == "fallen":   # P27-H: the walk to a fallen target ends within FINISH_R (the finish's) or as it stands
            return t[2] <= FINISH_R or not on_floor(t[1])
        if kind == "close":    # P27-J: the walk to point blank ends there (the shove's) or as it falls
            return t[2] <= POINT_BLANK_R or on_floor(t[1])
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
        if self.last.type == "melee":
            return self._melee_holds()   # survival iteration 22: the running melee (`dispatch.FightDispatch`)
        if self.last.type in ("attack", "walkTo") and self._finish_gives_way():
            return False   # P25-B: a fallen zombie within FINISH_R is stomped before the attack's walk goes on
        if self.last.type == "walkTo" and self._stance_walk is not None and self._stance_walk[0] is self.last:
            return not self._walk_gives_way()
        if self.last.type != "aim":
            return True
        if self._finishable():
            return False   # P24-AL: a downed zombie within reach (P25-J: `finish.finish_rule`) is finished first
        t = self._target(pin=False)
        if t is None or t[0] != self.last.args.get("targetId"):
            return False
        if self._fallen_due(t) or self._close_due(t):
            return False   # P27-H, P27-J: the stance gives way to the walk to a fallen target or to point blank
        if self._fence_leg is not None:   # P25-F: the fence wait's leg holds while the wait calls for it
            read = self._fence_read(t)
            return read is not None and read[0] == self._fence_leg
        if self.point_blank and self._leg == "stand":   # P28-B3: the drifted pin's stand holds while it comes
            return t[2] > CORNERED_R and self._drift_stands(t[1], t[2])
        if self._back_leg is not None and self.last is self._back_leg[0]:   # P28-B2 (fix 1, M1): the leg after a miss
            if t[2] <= POINT_BLANK_R:   # held at point blank until the target left it, then the shove on its return
                return not self._back_left
            return t[2] <= KEEP_R + KEEP_MARGIN   # held whatever `no_swing` reads (the sore band too)
        if self._leg == "back" and self.no_swing():   # P24-AP, R2: the wounded backpedal holds until point blank
            return POINT_BLANK_R < t[2] <= KEEP_R + KEEP_MARGIN
        if t[2] <= FIGHT_REACH or not self.stance_at(t[2]):
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
        """The Lua holds the stance now: the last action sent by anyone is this Fight's aim, still running. P28-F's
        planner side (Plan 28 Task 3 fix 1, review-t1b R2; Task 1b `e75bf474`, `e9241a94`): the Lua releases the
        stance on an attack's first tick and keeps none after the swing, so an attack, running or ended, reads no
        stance held (before it, an attack from the held stance read held while it ran and AIM_HOLD_S after its end).
        Any other send (a walk, a steer, a care skill) released it."""
        a = self.last
        if a is None or not self.actions.history or self.actions.history[-1] is not a:
            return False
        return a.type == "aim" and not self.actions.done(a)

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
            self._read_dead(a.args.get("targetId"))

    def _read_dead(self, zid):
        """Zombie `zid` read killed by the Fight's own send (an attack's or a leg's `targetDead`, a melee's `kill`):
        `kill` names it on this observe where the World counts it new, it is skipped as dead for UNREACHABLE_S and
        unpinned."""
        if self.world.note_kill(zid):
            self.kill = zid
        self.dead[zid] = self.clock() + UNREACHABLE_S   # the controller's ruling on concern 6 (Task 12 fix 1)
        if zid == self.target:
            self._unpin()

    def observe(self):
        self._drop_pin_read()
        self._observe_attackers()   # P27-N
        self._observe_edge()
        self._observe_edge_route()
        self._observe_kill()
        self._observe_maneuver()   # survival iteration 22: the melee's ends, a kill among them (`dispatch.py`)
        self._take_pin_read()   # once a tick: `blocked` and the pin read it on every call (fix 3, minor 4)
        self._observe_leg()
        t = self._target(pin=False)
        self._observe_back(t)   # P28-B2 (fix 1, M1)
        self._observe_stand(t)
        self._observe_seek(t)
        self._observe_fallen(t)   # P27-H
        self._observe_close(t)    # P27-J
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
        that started counts in the no-progress streak as a swing does (`_swing_landed_nothing`). Ruling P24-AV: a stomp
        failed `stood` (the target rose before it landed) is read again on the next frame (standing, the Fight's own
        path; fallen again, one more stomp): the STOOD_STOMPS-th `stood` at one target leaves it out of the stomp as a
        refusal does, so the floor strike follows. Ruling P28-D (`busy_retry`, Survive's BUSY_RETRY; F11,
        `f_goals_12-20261103-144240`: the stomp a145 at 14725, sent while a144 ran at 14630, was rejected `busy`, the
        refusal kept 14725 out of the finish rule beyond FIGHT_REACH for SWING_SKIP_S, and it lay 2.5172987398919933 to
        2.5942970526263225 tiles off with nothing within 6 tiles while the Fight logged `out_of_reach`, #4583): a shove
        or a stomp `rejected` `busy` (the player mid-swing or in a hit reaction, the Lua's `K.attackBusy`) says
        nothing about the target: no refusal is recorded, the send latched in `_busy_retry` (logged on the next send
        of its kind at its id, `choose`); any other end at that id clears the latch. Cost if wrong: a send rejected
        `busy` every tick through a long swing (the Lua's check, no engine call)."""
        zid = a.args.get("targetId")
        res = a.result if isinstance(a.result, dict) else {}
        if "busy_retry" in self.rules and a.state == "rejected" and a.reason == "busy":
            self._busy_retry = (a.type, zid)
            return
        if self._busy_retry is not None and self._busy_retry[1] == zid:
            self._busy_retry = None   # P28-D: another end at that id ends the latch
        if a.state != "done" or res.get("attackStarted") is False:
            if a.type == "stomp" and a.state == "failed" and a.reason == "stood":
                self.stood[zid] = self.stood.get(zid, 0) + 1
                if self.stood[zid] >= STOOD_STOMPS:
                    self.swing_refused[(a.type, zid)] = self.clock() + SWING_SKIP_S
                return
            if not (a.state == "failed" and a.reason == PREEMPTED):
                self.swing_refused[(a.type, zid)] = self.clock() + SWING_SKIP_S
            return
        if a.type == "stomp" and res.get("attackStarted") is True:
            self._swing_landed_nothing(zid)
        if a.type == "shove" and res.get("knockdown") is True:
            self.knocked[zid] = self.clock() + KNOCK_READ_S   # PZA/1.7.1: downed before the frame's onFloor reads it
        if a.type == "shove":
            self._note_shove_end(a, res)   # P25-L: the run of missed shoves at one target

    def _swing_ok(self, kind, zid):
        """The build announces `kind` (shove or stomp) and its last end at `zid` left it out no longer."""
        return self.world.can(kind) and self.swing_refused.get((kind, zid), -math.inf) <= self.clock()

    def _standing(self, r, exclude=()):
        """(id, zombie, dist) of each standing zombie (not `on_floor`, not read dead, not knocked down by a shove within
        KNOCK_READ_S) listed within `r` tiles of the player, its id not in `exclude`, nearest first (ties by id)."""
        dead, now = blocked(self.dead, self.clock()), self.clock()
        out = []
        for zid, z in self.world.zombies.items():
            if (zid in exclude or zid in dead or on_floor(z) or self.knocked.get(zid, -math.inf) > now
                    or z.get("x") is None or z.get("y") is None):
                continue
            d = zdist(self.world, z)
            if d <= r:
                out.append((d, repr(zid), zid, z))
        return [(zid, z, d) for d, _, zid, z in sorted(out, key=lambda e: e[:2])]

    def _standing_near(self, r, exclude=()):
        """(id, zombie, dist) of the nearest standing zombie (`_standing`) within `r` tiles of the player, its id not in
        `exclude`, else None: the engine's call takes a standing zombie within the weapon's MinRange for its target
        (#4372), so no shove or stomp of another goes then (P24-AH)."""
        near = self._standing(r, exclude)
        return near[0] if near else None

    def no_swing(self):
        """The Fight sends no swing, the floor strike included (rulings P24-AP and R2): `body.armPain` at STRAIN_HARD
        (`arms_hurt`), any hold Survive read this tick (`spent`: the arms', the endurance or the tired hold, each
        halving a swing, #4370, #4371), or a shove-and-stomp Fight (`shove_only`: "unarmed", ruling P25-P, the
        shove and the stomp need no weapon, the Lua's K.STAND_R; "low", ruling P25-S, under FLEE_HEALTH the kill with
        the least exposure; "hold", ruling P27-C, the endurance hold's lone zombie), but for the low fight's full swing
        when it is due (ruling P27-E, `_low_swing_due`)."""
        return arms_hurt(self.world) or self._hold_bars()

    def _hold_bars(self):
        """The swing's bar beside the arms' pain (fix 1, review-t3 minor 5: `no_swing` and `floor_swing_barred` read
        it): any hold read this tick (`spent`, R2) or a shove-and-stomp Fight (`shove_only`) but for the low fight's
        full swing when due (P27-E, `_low_swing_due`)."""
        return bool(self.spent) or (self.shove_only is not None and not self._low_swing_due())

    def floor_swing_barred(self):
        """Ruling P28-C (`floor_pain`, Survive's FLOOR_PAIN; F11, `f_goals_12-20261103-144240`: from the first bite
        `body.armPain` read 25.6 to 115.5 and no attack went again, the kills after the first by stomps alone, five to
        seven landed stomps a kill at 0.0756 to 0.5496 health each, where E19's floor swings killed in one from health
        up to 2.0870866775512695, #4583, #4553): the swing at a fallen zombie (the finish's floor swing, P27-G, and the
        floor strike after a refused stomp, P24-AL) is barred by a hold (`spent`, R2) or a shove-and-stomp Fight
        (`shove_only`, but for the low fight's full swing when due, P27-E), never by the arms' pain alone: a divided
        swing at a fallen zombie still lands its floor multiplier (#4374). The swing at a standing zombie keeps P24-AP's
        bar (`no_swing`). With the rule off, `no_swing`. Cost if wrong: a swing's strain and seconds where a stomp
        would do, bounded to a fallen target in reach."""
        if "floor_pain" not in self.rules:
            return self.no_swing()
        return self._hold_bars()

    def _drift_stands(self, z, d):
        """Ruling P28-B3 (`drift_stand`, Survive's DRIFT_STAND; F11, `f_goals_12-20261103-144240`: on lines 696 to 705
        the Fight sent nothing, each line `out_of_reach`, while 14725 closed chasing from 7.712846482962758 tiles after
        the corner's break, and it bit, #4580): a cornered Fight's (`point_blank`) pin `z`, `d` tiles off beyond
        CORNERED_R, stands (not `on_floor`: a fallen pin is the drifted finish's), chases (`hasTarget`), within
        DANGER_R, on a line not read blocked, with the build announcing `aim` and no riding bandage (P24-U: an aim ends
        it): the stance's standing leg aimed at it (`_choose`, held by `busy` while it comes beyond CORNERED_R), the
        shove or the swing taking it within reach. The drifted finish (P25-J) goes first. Cost if wrong: a leg standing
        for a pin that turns away (it ends at AIM_LEG_S, or as the pin stops chasing)."""
        return ("drift_stand" in self.rules and not on_floor(z) and chasing(z) and d <= DANGER_R and self.ride is None
                and line_to(self.world, z) is not False and self.world.can("aim"))

    def _wounded_leg(self, zid, z, d):
        """Ruling P24-AP, the wounded fight (#4370: at `body.armPain` STRAIN_HARD a swing does half its damage or less,
        whatever the pain's source), and ruling R2 under any hold (`no_swing`): where the Fight would swing, the
        stance's backpedal from the held threats facing `zid` instead (`_stance_leg`'s `back`, a heading
        `clear_heading` passes, else standing), held until the target comes to point blank (`busy`), where the shove
        goes, or lies down, where the stomp goes; with no `aim` announced nothing is sent (the Fight holds, logged
        `hold`). Logged `wounded` (the pain) and, under a hold, `spent` (its kinds)."""
        self.why["wounded"] = arm_pain(self.world)
        if self.spent:
            self.why["spent"] = list(self.spent)
        if not self.world.can("aim"):
            self.why["hold"] = True
            return None
        return self._stance_leg(zid, z, d, kind="back")

    def _ride_waits(self):
        """Ruling P25-D (E11: two riding bandages superseded by the corner's own shoves, #4408): a riding bandage in
        flight (`ride`, until its end) holds a Fight that sends no swing (`no_swing`: a hold, or the arms' pain) off
        every send, its shoves, stomps and legs, unless the frame reads `me.attackers` at DRAG_DOWN_N - 1 (the
        drag-down guard's line, `Survive._drag`, which flees first there)."""
        if "ride_wait" not in self.rules or self.ride is None or not (self.no_swing() or self._low_swing_due()):
            return False
        n = (self.world.me or {}).get("attackers")
        return not (isinstance(n, int) and not isinstance(n, bool) and n >= DRAG_DOWN_N - 1)

    def _fence_read(self, t):
        """Ruling P25-F, the fence wait (the guides notes § 9 change 4: the fence trick; the chain's fence-row fights
        each ended unreachable after a reposition walk, #4235 to #4316): `(leg, fence, tiles)` while target `t` chases
        (`hasTarget`) from across a known hoppable edge on its straight line (`World.fence_crossing`, the edge's
        midpoint `fence`, `tiles` from the player), the stance standing for it (`stance_at`, the build announcing the
        aim) and not yet advancing (STAND_MAX_S on the stand clock leaves it as today); `leg` `back` nearer the fence
        than FENCE_BACK_R's first value, `toward` farther than its second, else `stand`; None otherwise (neither a
        corner nor a door fight waits)."""
        if ("fence_wait" not in self.rules or self.point_blank or self.only is not None or not self.world.can("aim")
                or self.advance):
            return None
        zid, z, d = t
        if not chasing(z) or not self.stance_at(d):
            return None
        mx, my = me_xy(self.world)
        c = self.world.fence_crossing((mx, my), (z["x"], z["y"]))
        if c is None:
            return None
        df = math.hypot(c[0] - mx, c[1] - my)
        lo, hi = FENCE_BACK_R
        return ("back" if df < lo else "toward" if df > hi else "stand"), c, df

    def _fence_wait(self, t):
        """Ruling P25-F: the fence wait's leg (`_fence_read`), an `aim` facing the target: `back` away from the fence
        (turned by STEER_TURNS to a clear heading, else standing), `toward` the fence while the line to FENCE_BACK_R's
        first value reads clear (else standing), `stand` (0, 0); the target is neither repositioned for nor marked
        unreachable meanwhile (its line reads blocked by the fence). Logged `fence_wait` {target, fence, dist, leg}.
        Once it crosses (the fence off the line) the Fight's own rules swing at it or, fallen, stomp it."""
        read = self._fence_read(t)
        if read is None:
            return None
        kind, c, df = read
        zid, z, d = t
        mx, my = me_xy(self.world)
        v = None
        if kind == "back" and df > 0.0:
            v = self._clear_turn(((mx - c[0]) / df, (my - c[1]) / df))
        elif kind == "toward":
            u = ((c[0] - mx) / df, (c[1] - my) / df)
            v = u if clear_heading(self.world, u, min(STEER_PROBE, df - FENCE_BACK_R[0]), self.trans) else None
        vx, vy = v if v is not None else (0.0, 0.0)
        self.why = {"target": zid, "pinned": True, "dist": d, "stance": True, "leg": kind, "stand_s": self.stand_s(),
                    "fence_wait": {"target": zid, "fence": [c[0], c[1]], "dist": df, "leg": kind}}
        return Aim(vx, vy, AIM_LEG_S, targetId=zid)

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
        if (self.crowd is not None and cmd is not None and cmd.TYPE in ("shove", "stomp", "attack")
                and "corner" not in self.why):   # P26-C: an `inside` corner's send, logged
            self.why["corner"] = {"kind": "inside", "send": cmd.TYPE, "near_n": self.crowd}
        retry = self._busy_retry
        if retry is not None and cmd is not None and (cmd.TYPE, getattr(cmd, "targetId", None)) == retry:
            self.why["busy_retry"] = {"target": retry[1], "kind": retry[0]}   # P28-D: the send rejected `busy`, again
            self._busy_retry = None
        if self._m_end is not None:   # survival iteration 22: the maneuver that ended since the last choose
            self.why["melee_end"], self._m_end = self._m_end, None
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
        """The decision ladder's command (`_ladder`), or at its in-reach sends at the pin the melee maneuver's in its
        place (`dispatch.FightDispatch._melee_dispatch`, survival iteration 22), but on the choose after an end that
        gives it back to the ladder (`_m_ladder`)."""
        cmd = self._ladder()
        ladder, self._m_ladder = self._m_ladder, False
        return cmd if ladder else self._melee_dispatch(cmd)

    def _ladder(self):
        self._seek_send, self._walk_kind, self._edge_send = False, None, None
        self._repin_point_blank()
        self._pull_pin()
        switch = self._seek_switch(self._pinned()) if self.seek and self.target is not None else None
        if switch is None and self.advance and self.target is not None:
            switch = self._advance_switch(self._pinned())   # Task 18 fix 2: the advance gives way to a closing zombie
            if switch is not None:
                self.advance = False
        if switch is not None:   # Task 18 fix 1, the blocker: the seek closes on the nearest
            self.target, self.repositioned = switch[0], False
        self._pin_first()   # P27-N: a zombie at point blank or read attacking takes the pin
        t = self._target(pin=True)
        if t is None:
            self.why = {"target": None, "pinned": False}
            return None
        zid, z, d = t
        if self.point_blank and d > CORNERED_R:   # P24-A fix 2, I2a: a cornered Fight never walks to a drifted pin
            fin = self._drifted_finish()   # P25-J (3), 8 fix 1: the finish of the fallen first
            if fin is not None:
                return fin[0]
            self.why = {"target": zid, "pinned": True, "dist": d, "out_of_reach": True}
            if self._drift_stands(z, d):   # P28-B3: the stance aimed at the pin while it comes, not nothing
                self.why["stance"] = True
                return self._stance_leg(zid, z, d, kind="stand")
            return None
        if self._ride_waits():   # P25-D: the riding bandage lands before a held Fight's next send
            self.why = {"target": zid, "pinned": True, "dist": d, "ride_wait": self.ride.aid}
            return None
        fin = self._finish()   # P24-AL: a downed zombie within reach first
        if fin is not None:
            return fin[0]
        first = self._finish_first(d)   # P25-B: one within FINISH_R before any walk toward a standing one
        if first is not None:
            return first
        pin = self._pin_send(zid, z, d)   # P27-N: the pinned zombie at point blank or attacking, shoved then swung at
        if pin is not None:
            return pin[0]
        seek = self._fallen_seek(t)   # P27-H: a target lying fallen beyond FINISH_R walked to, or left
        if seek is not None:
            return seek[0]
        fence = self._fence_wait(t)   # P25-F: a chaser across a fence waited for, never walked round to nor marked
        if fence is not None:
            if switch is not None and zid == switch[0]:
                self.why["seek_switch"] = True
            return fence
        edge = self._edge_answer(t)   # P25-X: a known blocked edge on the line, routed through its door or refused
        if edge is not None:
            if edge[0] == "route":
                return edge[1]
            read = self.blocked_edge
            cmd = self._ladder()
            self.why = dict(self.why, marked=zid)
            if "blocked_edge" not in self.why:   # the re-run's own (the routed or the refused second zombie's) stands
                self.why["blocked_edge"] = read
            return cmd
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
                cmd = self._ladder()
                self.why = dict(read if self.why["target"] is None else self.why, marked=zid)
                return cmd
            self.repositioned = True
            self.why["reposition"] = list(sq)
            return WalkTo(*centre(sq), "run")
        close = self._shove_close(t)   # P27-J: a shove-only Fight's chaser holding off is walked to, or left
        if close is not None:
            return close[0]
        if (self.stance_at(d) and (d > FIGHT_REACH or not (self.in_stance() or self.no_swing()
                                                           or self.shove_only is not None))
                and not (self.approach and d <= FIGHT_REACH)):   # P24-AP: wounded, in reach the backpedal is the leg;
            # P27-E: a shove-and-stomp Fight takes no enter leg in reach, its low swing going from where it stands
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
            if "approach_walk" in self.rules:   # the spec's 1 (b): beyond FIGHT_REACH or on the approach, a walk
                self.why["leg"] = "walk"
                return WalkTo(*centre((z["x"], z["y"])), "walk")
            return WalkTo(*centre((z["x"], z["y"])), "run")
        hit = hit_reaction(self.world)
        if hit is not None:   # P24-A (i): the engine starts no swing in a hit reaction (#4292, #4293): sent on its end
            self.why["hitReaction"] = hit
            return None
        if self._low_exit(zid):   # P27-K2: the low fight leaves a lone target its shoves cannot knock down
            return None
        crowd = self._crowd_shove(zid, d)   # P26-C: an `inside` corner under a crowd at point blank shoves
        if crowd is not None:
            return crowd
        shove = self._shove(zid, z, d)   # P24-AG, P24-AH: the shove before (or for) the swing
        if shove is not None:
            return shove
        if self.no_swing():   # P24-AP, R2: never the swing at STRAIN_HARD or under a hold; the backpedal between
            return self._wounded_leg(zid, z, d)
        held = self._attack_hold(zid, z, d)   # P27-M: no attack beyond the weapon's reach and ATTACK_MARGIN
        if held is not None:
            return held[0]
        if self.stance_at(d):
            self.why["stance"] = True   # the swing from the stance (the Lua releases it on the attack's first tick)
            if self.reach_r() is not None:
                self.why["attack"] = {"dist": d, "reach": self.world.weapon["reach"]}   # P27-M
        return Attack(zid)   # nearest_zombie yields int ids only (M7)

    def _stance_leg(self, zid, z, d, kind=None):
        """One stance leg (rulings P24-G 1 and P24-N): `aim` at the target for AIM_LEG_S (its `targetId`: the frames'
        `dir` reads the target's bearing, #4588-#4591), walking (the stance never runs) one of
        - `enter` (0, 0): the target within FIGHT_REACH with the stance not held (`in_stance`): the stance is taken
          before the swing, which the next choose sends from it;
        - `toward`: the advance (`advance`, after STAND_MAX_S without progress), the unit vector to the target while
          its STEER_PROBE line (to the target at most) is clear; with that line blocked the approach walk closes on
          it instead (the path follower walks round the wall), the one walk of a standing fight, at a walk (Task 12
          fix 1, the review's minor 3: ruling P24-N 1 closes "in the stance ... not to a run");
        - `back`: the target inside KEEP_R: `away_vector` of the held threats (`threats`, else the target) turned
          by STEER_TURNS to the first heading `clear_heading` passes (never into a wall or over a fence), else
          standing: a wall behind is never stepped into; with one standing zombie within KEEP_R and the `circle` rule
          on, turned CIRCLE_TURN first (`_circle_turn`, ruling P28-E);
        - `pull` (ruling P24-AN): a lone chaser beyond PULL_R pulled from the group (`pulling`): the unit vector from
          the group's centroid (`pull_centroid`) to the player, turned by STEER_TURNS to the first heading
          `clear_heading` passes, else standing; the chaser faced while it follows, the group left behind;
        - `stand` (0, 0): the target beyond KEEP_R, faced while it comes.
        `kind` names the leg instead of the target's distance (P24-AP's wounded backpedal within reach)."""
        t, named = (zid, z, d), kind is not None
        v, kind = None, kind or stance_leg_kind(d, self.advance, self.seeking(t), self.pulling(t))
        if kind in ("toward", "seek"):
            mx, my = me_xy(self.world)
            u = ((z["x"] - mx) / d, (z["y"] - my) / d)
            if not clear_heading(self.world, u, min(STEER_PROBE, d), self.trans):
                self.why.update({"stance": True, "leg": "walk", "stand_s": self.stand_s()})
                self.why["advance" if kind == "toward" else "seek"] = True
                self._seek_send, self._walk_kind = kind == "seek", "seek" if kind == "seek" else "advance"   # fix 1
                return WalkTo(*centre((z["x"], z["y"])), "walk")
            if kind == "toward" and self._reach_walk_due(z, d):
                return self._reach_walk(zid, z, d)   # P27-M: the advance walks to the reach, never `toward` legs
            v = u
        elif kind == "enter" and not named and self._reach_walk_due(z, d):
            return self._reach_walk(zid, z, d)   # P27-M: the advance on an idle target within FIGHT_REACH
        elif kind == "back":
            v = self._back_heading(z)
        elif kind == "pull":
            c = self.pull_centroid(t)
            v = self._clear_turn(away_vector(self.world, [c]))
            self.why["pull"] = [c[0], c[1]]
            if self.edge:
                self.why["edge"] = sorted(self.edge, key=repr)   # P24-AU: the group read held at the listing's edge
        vx, vy = v if v is not None else (0.0, 0.0)
        self.why.update({"stance": True, "leg": kind, "back": [vx, vy] if kind == "back" and v is not None else None,
                         "stand_s": self.stand_s()})
        if self.advance:
            self.why["advance"] = True
        if kind == "seek":
            self.why["seek"] = True
        return Aim(vx, vy, AIM_LEG_S, targetId=zid)

    def _back_heading(self, z):
        """The `back` leg's heading from target `z` (`_stance_leg`): `away_vector` of the held threats (else `z`),
        turned by CIRCLE_TURN from a lone standing zombie within KEEP_R (P28-E, `_circle_turn`), else by STEER_TURNS
        (`_clear_turn`); None when no heading is clear (the leg then stands)."""
        ts = [q for q in (self.threats or [z]) if q.get("x") is not None and q.get("y") is not None]
        away = away_vector(self.world, [(q["x"], q["y"]) for q in ts])
        lone = "circle" in self.rules and away is not None and len(self._standing(KEEP_R)) == 1
        return self._circle_turn(away) if lone else self._clear_turn(away)   # P28-E: the arc from a lone zombie

    def _circle_turn(self, a):
        """Ruling P28-E (`circle`, Survive's CIRCLE; E20, `e_day_20-20261103-121340`'s candidate, #4576: the stance's
        legs walked straight toward or away from the target): the `back` leg's heading `a` (the unit away heading)
        turned CIRCLE_TURN degrees to the side last used (`_circle_side`, +1 first, so the arc goes one way while it
        stays clear), else to the other side, the first whose heading `clear_heading` passes, the side kept, logged
        `circle` {turn}; with neither clear, `_clear_turn(a)` (straight away, then STEER_TURNS, as before). The aim
        keeps its target (the frames' `dir` reads its bearing). Cost if wrong: a slower retreat from a lone zombie, a
        leg toward an edge `clear_heading` reads open."""
        for side in (self._circle_side, -self._circle_side):
            h = _rotate(a, side * CIRCLE_TURN)
            if clear_heading(self.world, h, STEER_PROBE, self.trans):
                self._circle_side = side
                self.why["circle"] = {"turn": side * CIRCLE_TURN}
                return h
        return self._clear_turn(a)

    def _clear_turn(self, a):
        """Heading `a` (a unit vector, or None) turned by STEER_TURNS to the first heading `clear_heading` passes
        (never into a wall or over a fence), else None: the backpedal's and the pull's step."""
        if a is None:
            return None
        return next((_rotate(a, t) for t in STEER_TURNS if clear_heading(self.world, _rotate(a, t), STEER_PROBE,
                                                                         self.trans)), None)

    def sent(self, cmd, action):
        if cmd.TYPE == "melee":
            self.m.sent(cmd, action)   # survival iteration 22: the maneuver's own send
        else:
            self._retire_maneuver()   # the ladder's command in its place: the Lua supersedes the melee
        if cmd.TYPE == "aim":
            self._leg = self.why.get("leg")
            if "shove_back" in self.why:   # P28-B2 (fix 1, M1): the one leg for this miss, held by `busy`
                self._backed[cmd.targetId] = self._shove_a.get(cmd.targetId)
                self._back_leg, self._back_left = (action, cmd.targetId), False
            self._fence_leg = self.why["fence_wait"]["leg"] if "fence_wait" in self.why else None   # P25-F
            if self._leg == "pull":
                self._pulled = cmd.targetId   # P24-AN: kept to DISENGAGE_R from here (`_pull_waits`)
        elif cmd.TYPE == "walkTo":
            self.approach = False
            self._seek_walk = (action, self.target) if self._seek_send else None
            self._edge_walk = (action,) + self._edge_send if self._edge_send else None   # P25-X: its end read
            self._stance_walk = (action, self.target, self._walk_kind) if self._walk_kind else None
        elif cmd.TYPE == "shove":
            self._shoved = True
            self._shove_a[cmd.targetId] = action   # P25-A: its end read by `_shove_missed`
        elif cmd.TYPE in ("attack", "stomp", "melee"):
            self._shoved = False
            if cmd.targetId != self._streak_id:   # a new target: its streak starts here
                self._streak_id, self._streak_h, self.no_progress = cmd.targetId, self._target_health(cmd.targetId), 0
