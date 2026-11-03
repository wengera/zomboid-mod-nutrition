"""The threat branch of `survive.Survive` (Plan 22 Task 10's priority list, its first branch): the held list, the
flee reasons and their hysteresis, the sought fight, the corner, the doorway stand, the finish of the fallen, the care
yield and the decision the Fight and the Flee execute (`_threat`, `_decide`). Moved out of `survive.py` at Plan 24
Task 36 (a pure move: every rule, switch and constant unchanged), as the mixin `Threat` that `Survive` derives from;
its state is `Survive`'s own, set in `Survive.__init__`, and `survive.py`'s module docstring stays the record of every
rule here (the rulings by iteration, P23-AG to P24-AS). Plan 25 Task 2 moved parts of it into mixins `Threat` derives
from (a pure move): the hold and spent reads (`hold.Hold`), the engage (`engage.Engage`), the pull read
(`pull.ThreatPull`), the care yield (`care_yield.CareYield`), the doorway stand's side (`doorway.DoorwayStand`) and the
`many` flee's finish (`finish.ThreatFinish`); the constants are `policies.py`'s, imported here.
"""
from agent.base.planner.care import CARE_STILL_TICKS
from agent.base.planner.care_yield import CareYield
from agent.base.planner.doorway import DoorwayStand, stand_ready
from agent.base.planner.edges import ThreatEdge
from agent.base.planner.engage import Engage
from agent.base.planner.fight import Fight
from agent.base.planner.finish import ThreatFinish
from agent.base.planner.flee import Flee
from agent.base.planner.hold import Hold
from agent.base.planner.policies import (AIM_R, CLOSING_TICKS, CORNERED_R, CORNER_FREE_R, DANGER_R, DISENGAGE_R,
                                         DRAG_DOWN_N, DROP_AT, EDGE_HOLD_TICKS, ENGAGE_R, FIGHT_REACH, FINISH_R,
                                         FLEE_GAIT, FLEE_HEALTH, FLEE_HEALTH_FLOOR, FLEE_HEALTH_PAIR, FLIP_MIN_S,
                                         GROUP_HOLD_N, GROUP_NEAR_R, GROUP_R_N, HOLD_BREAK_R, LISTED_R, MANY_LISTED_N,
                                         MAX_FIGHT,
                                         POINT_BLANK_R, REFIGHT_MARGIN, STUCK_RETRY_GROUP_S, STUCK_RETRY_S, adoptable,
                                         blocked, chasing, exit_plan, in_building, in_reach, line_to, others_behind,
                                         seek_allowed, spare, target_id_ok, zdist)
from agent.base.planner.pull import ThreatPull
from agent.base.pza1 import Drop

__all__ = ["Threat", "FLEE_HEALTH", "FLEE_HEALTH_PAIR", "REFIGHT_MARGIN", "MAX_FIGHT", "HOLD_BREAK_R", "CLOSING_TICKS",
           "CORNERED_R", "CORNER_FREE_R", "MANY_LISTED_N", "FINISH_R", "DRAG_DOWN_N", "FLIP_MIN_S", "GROUP_R_N",
           "GROUP_NEAR_R", "GROUP_HOLD_N", "STUCK_RETRY_S", "STUCK_RETRY_GROUP_S", "LISTED_R"]


class Threat(Hold, Engage, ThreatPull, CareYield, DoorwayStand, ThreatFinish, ThreatEdge):
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
    WOUNDED_SWING = True  # ruling P26-L1: under the `wounded` reason a lone standing target at point blank with
                          # SHOVE_FAIL_N missed shoves on record is swung at in the shove's place, ahead of the corner
                          # and the breaks (`shove.FightShove._wounded_swing`); off, the shove, the corner, the breaks
    BLEED_HOLD = True     # ruling P26-L2: the dressing P26-D's yield sent is held while the zombie within FIGHT_REACH
                          # is not closing (`care_yield.CareYield._bleed_holds`), the hold applying only with one zombie
                          # within FIGHT_REACH (P26-L2a; `care_yield.py`); off, any zombie there supersedes it
    # survival iteration 19 (Plan 27 Task 1; survive.py's docstring, Survival 21): each switch off is the rule before
    # it, all of them in `survive.T9_SWITCHES` (the replay tests' `pre_t9`)
    FLEE_FINISH = True    # ruling P27-A: the flee's finish under the `strain`, `pair` and `many` flees on any fallen
                          # zombie, cleared to FINISH_CLEAR_R (`finish.ThreatFinish._flee_finish`, `_fallen_wide`); off,
                          # P24-AQ's struck target under `many` and P25-J (3)'s `pair` finish

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
        makes `many` by MANY_LISTED_N."""
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

    def _counts_many(self, z):
        """Ruling P24-AD: zombie `z` counts toward `many`: within DANGER_R, or not idle (`hasTarget` not read false: a
        chaser, or a frame that does not carry the field); with `IDLE` off every zombie counts."""
        return not self.IDLE or z.get("hasTarget") is not False or zdist(self.world, z) <= DANGER_R

    def _counts_listed(self, z):
        """Ruling P24-AN: zombie `z` counts toward `many` by the listing: within DANGER_R or chasing (`hasTarget`
        true); with `IDLE` off every zombie counts (the rules before P24-AD)."""
        return not self.IDLE or chasing(z) or zdist(self.world, z) <= DANGER_R

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
        `pair` rule's); `many` is `_many`."""
        health = self._health()
        if not self._armed() and (not self._unarmed_fight(n) or self._many(held, n)):
            return "unarmed"
        if self._many(held, n):
            return "many"
        if health < FLEE_HEALTH and not self._low_fight(n):
            return "health"
        if n >= 2 and (health < FLEE_HEALTH_PAIR or self._wounds() > 0):
            fallen = self._pair_finish()   # P25-J (3): the finish of a fallen (or knocked) one goes before the flee
            if fallen is None:
                return "pair"
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
        logged `low_fight`; the doorway stand's own `health` end is unchanged."""
        health = self._health()
        return (self.LOW_FIGHT and health < FLEE_HEALTH and self.world.can("shove") and n == 1
                and health >= FLEE_HEALTH_FLOOR)

    def _unpaired(self, held, health, n):
        """The hysteresis past the `pair` rule (`_hysteresis`; `n` the DANGER_R count): `strain`, `unreachable`,
        `stalled`, `held`, else None."""
        if self.spent is not None and not self._wounded_fight():   # P24-AG, P24-AK: the arms, the endurance or the
            return "strain"                                        # tiredness halve every swing; P24-AP within KEEP_R
        if not self._reachable_held():
            return "unreachable"
        near = min(zdist(self.world, z) for z in held)
        if self.mode == "flee":
            if self.stall_flee and near > FIGHT_REACH:
                return "stalled"
            if not self.ENGAGE:   # before P24-X: one held, at the refight margin
                return "held" if len(held) > 1 or health < FLEE_HEALTH + REFIGHT_MARGIN else None
            if not (self._takes_on(len(held)) or self._unarmed_fight(n) or self._low_fight(n)):   # P24-X: the flee
                return "held"   # turns to fight one or two at the fight's line; P25-P unarmed, P25-S under FLEE_HEALTH
            if self.flee_health and health < FLEE_HEALTH + REFIGHT_MARGIN and not self._low_fight(n):
                return "held"   # the health flee stays, its margin kept (P25-S: but for the low fight)
            return None
        if self.mode == "fight" and self.fight.stalled and (self.fight.target_dist() or 0.0) > FIGHT_REACH:
            return "stalled"   # the pinned target's distance: the one the stall clock follows (M3)
        return None

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
        if self.mode == "flee" and self.flee_many:
            return "many"
        if self.spent is None or self._wounded_fight():   # P24-AP, R2: a hold fights within KEEP_R
            return None
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
        """The threat branch's one decision (ruling P23-AJ), `(kind, reason)`, the machines only executing it:
        - The doorway stand (ruling P24-AO, `_doorway`): `doorway` while the Flee's stand plan reads `stand`, then
          `flee` (reason `doorway`) while the stand's close, or its way out after an end under a group (P25-W), runs,
          ahead of every other row (the stand's premise is the
          one-tile front the drag-down guard flees: the stand reads its own `drag` end, at DRAG_DOWN_N - 1 since
          P25-U, the guard's own count, `_stand_drag_n`).
        - The drag-down guard (ruling P24-A (h), `_drag`): `flee` with the group steer (`group` "drag"), ahead of
          every other row but the doorway's; the Flee steers at a run, or inside walks the exit (P24-A (f), P24-O).
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
        self.one_exit_refused = None
        door = self._doorway()
        if door is not None:   # P24-AO: the doorway stand and its close go first, the drag guard's leg included
            return door
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
        if self.sheltered:   # P25-P: unarmed, a lone zombie in reach of a shelter with no way out is shoved
            fight = None if self._armed() else self._trapped_fight(held, inside)
            return fight or ("flee", reason or "sheltered")
        if reason is None:
            reason = self._kept_flee()
            if reason is None:
                return "fight", None
        return self._trapped_fight(held, inside) or ("flee", reason)

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
        return ("fight", None) if near <= FIGHT_REACH and self._unarmed_fight(len(self._within(DANGER_R))) else None

    def _end_flee_episode(self):
        """A flee episode's own flags cleared: its stall origin, its one load drop, its `many` (P23-AM 1), its `health`
        (P24-X) and its last reason (P26-D)."""
        self.stall_flee, self.flee_dropped, self.flee_many, self.flee_health = False, False, False, False
        self.flee_reason = None

    def _threat_read(self):
        """The tick's threat bookkeeping, once (ruling P24-A (g)): the held list (`_held`), the Flee's observe and the
        breach's closing count (`_breach_now`). Read in `_read` (Plan 25 Task 2, `OBSERVES_IN_READ`), else at the
        threat branch's start in `assess` (the rules before it)."""
        self.care_yield, self.care.ride_now, self.engaging, self.avoid = None, False, False, set()
        self.bleed_yield = None   # P26-D: this tick's yield the bleed's rule made
        self.bleed_held = False   # P26-L2: this tick's yield the dressing's hold made
        self.finish_block = None   # Task 36 fix 1: this tick's refusal only (`_finish_chaser` sets it)
        self._release_edges()   # P25-X: a zombie refused across a blocked edge, read on the player's side, is free
        self._held, self._breach_now = [], None
        self._read_spent()
        held = self._within(self._hold_r())
        sought = self._sought() if self.ENGAGE else None
        if sought:   # P24-X: one or two within ENGAGE_R, the fight sought
            held, self.engaging = sought, True
        elif held and self._released(held):   # Task 18 fix 1, major 2: nothing left the fight may reach
            held = []
        if not held:
            self.mode, self.fight, self.flee = None, None, None
            self.many_since = None   # P24-AR: the long flee's clock ends with the threat
            self._end_flee_episode()
            self.sheltered, self.cornered, self.closing = False, None, (0, None)
            self.stuck_heading, self._nearest_seen = None, []
            return
        self._nearest_seen = (self._nearest_seen + [self._nearest_listed()])[-(CARE_STILL_TICKS + 1):]
        if self.flee is not None:   # a shelter or exit step's end read before the hold (the close may have ended),
            self.flee.threats = held   # over this tick's held records (the stall's and the stuck leg's DANGER_R and
            self._observe(self.flee)   # STUCK_NEAR_R reads: before P24-A (g) the first read saw the last tick's)
        self._held, self._breach_now = held, self._breach(held)

    def _threat(self):
        """The threat branch: the tick's bookkeeping (`_threat_read`, read in `_read` with `OBSERVES_IN_READ` on); then
        the yield to the care (`_care_yields`, P24-P), else the decision (`_decide`), which a corner's retarget may
        re-plan without them."""
        self.trapped_pass = False
        if not self.OBSERVES_IN_READ:
            self._threat_read()
        held, breach = self._held, self._breach_now
        if not held:
            if self.avoid:   # Task 18 fix 1: the zombies within ENGAGE_R no engage reaches, logged as the goal runs
                self.why = {"unsought": sorted(self.avoid, key=repr)}
            return None
        self.care_yield = self._care_yields(held)
        if self.care_yield is not None:
            self.why = {"care": True, "nearest": self.care_yield, "held": len(held)}
            if self.care.ride_now:
                self.why["ride"] = True
            if self.bleed_yield is not None:
                self.why["care_yield"] = {"why": "bleed", "near": self.bleed_yield}   # P26-D
                if self.bleed_held:
                    self.why["care_yield"]["held"] = True   # P26-L2: held only by the dressing's hold
            return None
        return self._decide(held, breach)

    def _decide(self, held, breach, replanned=False):
        """`_threat_plan`'s decision executed by the Fight or the Flee, logged in `why`."""
        kind, reason = self._threat_plan(held, breach)
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
            if reason == "many" and self.many_since is None:
                self.many_since = self.clock()   # P24-AR: the long flee's clock, kept across its corners
            policy.threats = held
            policy.hold_ok = breach is None
            policy.steer_now = self.group_steer is not None
            policy.rules = self._flee_rules()   # P25-E, P26-A, P26-B, P26-I, P26-J
            walk = self._hold_walk(reason)   # P25-C: the endurance hold's flee walks with nobody within DANGER_R
            policy.gait = "walk" if walk else FLEE_GAIT
            policy.keep_gait()
            policy.stand_ok = self.DOORWAY and self.flee_many and stand_ready(self.world, blocked(self.dead,
                                                                                               self.clock()))
            if self.group_steer:
                policy.give_way()   # amendment 6: the group pre-empts a running walk, as the corner does
            if self.group_steer == "drag":
                policy.drop_stuck_leg()   # P24-A fix 2, I1: never a stalled leg held its FLEE_S under the guard
            self.pair_yield = None   # P25-J (3): a flee's yield is the `pair` flee's own finish (`_pair_flee_finish`)
            ans = self._flee_drop() or self._flee_finish(reason) or self._answer(policy)
            pick = self._doorway_pick(policy) if reason == "many" and self.PICK_WHY else None   # P24-AX, after the pick
        else:
            policy.only = None if door is None else {zid for zid, _ in door}
            policy.stance = self._stance_ok(held, self.night.inside())   # P24-G 1 (no corner or door Fight stands)
            policy.spent = self._fight_spent()   # R2: no swing under any hold
            policy.hold_ground = self._chokepoint()   # Task 18 fix 1, ruling 2: no seek from a room or door square
            policy.avoid = self.avoid                 # ... nor at a zombie no engage reaches (major 2)
            policy.ride = self.care.riding()   # P24-U: the stance legs held off while a bandage rides
            policy.threats = held
            policy.edge_ticks = EDGE_HOLD_TICKS if self.EDGE else 0   # P24-AU, read at the policy's observe
            policy.rules = self._fight_rules()   # P25-A, P25-B, P25-D, P25-F
            policy.edge_marks = self.edge_marks   # P25-X: the refusals across a blocked edge, shared as `unreachable`
            policy.shove_only = self._shove_only(kind)   # P25-P, P25-S: no swing, no seek
            policy.crowd = self._inside_crowd() if kind == "cornered" else None   # P26-C
            ans = self._answer(policy)
            if self.pair_yield is not None and not self._finishes(self.pair_yield):
                self.pair_yield = None   # P25-J (3): logged only where the Fight's finish answers it
        self.why.update({"fight": True} if reason is None else {"flee": reason})
        if want == "fight" and policy.shove_only is not None:   # P25-P, P25-S: the Fight's shove and stomp
            self.why["unarmed_fight" if policy.shove_only == "unarmed" else "low_fight"] = True
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
                       ("pair_yield", self.pair_yield)):
            if v is not None:
                self.why[key] = v
        if self.broken is not None:
            self.why["breach"] = self.broken
        ride = self.care.riding()
        if ride is not None:
            self.why["ride"] = ride.aid   # P24-U: a bandage rides the leg this answer holds or re-aims
        self.trapped_pass = want == "flee" and ans is None and "trapped" in self.why   # P25-Q: read by `assess`
        return ans if ans is not None else (policy, None)

    def _shove_only(self, kind):
        """Why this tick's Fight is the shove and the stomp alone (`Fight.shove_only`), else None: "unarmed" with no
        weapon held (`_unarmed`, P25-P), "low" for the open-ground Fight (`kind` "fight": no corner nor door fight)
        under FLEE_HEALTH the low fight admits (`_low_fight`, P25-S)."""
        if self._unarmed():
            return "unarmed"
        return "low" if kind == "fight" and self._low_fight(len(self._within(DANGER_R))) else None

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
        """The iterations 13 to 18 Fight rules (`fight.FIGHT_RULES`) whose switch is on: the Fight's `rules`."""
        return frozenset(rule for rule, on in (("corner_break", self.CORNER_BREAK), ("finish_first", self.FINISH_FIRST),
                                               ("ride_wait", self.RIDE_WAIT), ("fence_wait", self.FENCE_WAIT),
                                               ("finish_far", self.FINISH_FAR), ("shove_break", self.SHOVE_BREAK),
                                               ("shove_break_run", self.SHOVE_BREAK_RUN),
                                               ("blocked_edge", self.BLOCKED_EDGE),
                                               ("wounded_swing", self.WOUNDED_SWING))
                         if on)

    def _flee_rules(self):
        """The iterations 13, 17 and 18 Flee rules (`flee.FLEE_RULES`) whose switch is on: the Flee's `rules`."""
        return frozenset(rule for rule, on in (("door_walk", self.DOOR_WALK), ("window_exit", self.WINDOW_EXIT),
                                               ("stand_second_exit", self.STAND_SECOND_EXIT),
                                               ("window_inner", self.WINDOW_INNER),
                                               ("window_stall", self.WINDOW_STALL))
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
