"""The threat branch of `survive.Survive` (Plan 22 Task 10's priority list, its first branch): the held list, the
flee reasons and their hysteresis, the sought fight, the corner, the doorway stand, the finish of the fallen, the care
yield and the decision the Fight and the Flee execute (`_threat`, `_decide`). Moved out of `survive.py` at Plan 24
Task 36 (a pure move: every rule, switch and constant unchanged), as the mixin `Threat` that `Survive` derives from;
its state is `Survive`'s own, set in `Survive.__init__`, and `survive.py`'s module docstring stays the record of every
rule here (the rulings by iteration, P23-AG to P24-AS).
"""
import math

from agent.base.planner.care import (CARE_HOLD_R, CARE_R, CARE_STILL_TICKS, FLEE_CARE_N, FLEE_CARE_S, RIDE_MANY_R,
                                     RIDE_R)
from agent.base.planner.doorway import DOOR_HOLD_S, Doorway, off_post, standing, stand_ready
from agent.base.planner.fight import Fight
from agent.base.planner.flee import Flee
from agent.base.planner.policies import (AIM_R, CORNERED_R, DANGER_R, DISENGAGE_R, DROP_AT, EDGE_HOLD_TICKS,
                                         ENDURANCE_RELEASE, ENDURANCE_T, ENGAGE_R, FIGHT_REACH, KEEP_R, LISTED_R,
                                         POINT_BLANK_R, PREEMPTED, STAND_MIN_R, STIFF_HARD, STIFF_SOFT, STRAIN_HARD,
                                         TIRED_FIGHT_T, UNREACHABLE_S, adoptable, arm_pain, arm_stiffness, arms_hurt,
                                         blocked, chasing, exit_plan, in_building, in_reach, line_to, on_floor,
                                         others_behind, pull_from, running, seek_allowed, spare, target_id_ok, zdist)
from agent.base.pza1 import Attack, Drop, Stomp
from agent.base.world import me_floor, me_xy

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

__all__ = ["Threat", "FLEE_HEALTH", "FLEE_HEALTH_PAIR", "REFIGHT_MARGIN", "MAX_FIGHT", "HOLD_BREAK_R", "CLOSING_TICKS",
           "CORNERED_R", "CORNER_FREE_R", "MANY_LISTED_N", "FINISH_R", "DRAG_DOWN_N", "FLIP_MIN_S", "GROUP_R_N",
           "GROUP_NEAR_R", "GROUP_HOLD_N", "STUCK_RETRY_S", "STUCK_RETRY_GROUP_S", "LISTED_R"]


def _num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


class Threat:
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
    EDGE = True     # ruling P24-AU: a zombie that left the listing is held in the Fight's pull reads EDGE_HOLD_TICKS
                    # ticks (`policies.Fight.edge_ticks`); off, 0 (the replay tests' seam onto the rule before it)

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

    def _read_spent(self):
        """Rulings P24-AG and P24-AK (#4370, #4371), with P24-AT's hold on the stiffness, read once a tick (`_threat`;
        `self.spent` is what the tick's `_sought`, `_hysteresis`, `_walk_yields` and the why read, review-t27 minor 3):
        why the character is spent for a fight this tick, else None (always with `STRAIN` off):
        - `arms` while the strain hold runs: ruling P24-AT (E10: the hold, set at game minute 605 by a bite's pain,
          fled on 308 of 580 threat lines and never released, the pain never under 21 again while the stiffness read 0
          on both arms) reads the arms' stiffness (`policies.arm_stiffness`, the frame's `body.strain`, #4369): it
          starts at STIFF_HARD on either arm (the health panel's line past minor stiffness) and ends once both read
          under STIFF_SOFT (the panel's first naming of it), or with no `strain` on the frame (an older Lua); a rest
          lowers it by about 5.76 a real minute on the server (#4369). Before it the pain set it (STRAIN_HARD, released
          under STRAIN_SOFT), which a wound holds up whatever the rest: the pain is now its own reason, `wounded`
          (`self.wound`, below);
        - `endurance` while the endurance hold runs: it starts at the frame's `stats.endurance` ENDURANCE_T or under
          (the ENDURANCE moodle's first level, which halves every swing) and ends only above ENDURANCE_RELEASE (a
          fight drains far faster than rest restores, so with no release line the edge flickered: flee, one swing,
          flee; review-t27 blocker 1, F1 gm 635-637);
        - `tired` at `stats.fatigue` TIRED_FIGHT_T or above (the TIRED moodle's, which halves it again).
        Spent, the threat branch disengages (the flee `strain`, its legs as today), engages and seeks nothing, and a
        `walk` corner yields; the `stuck`, `inside`, trapped and door fights, which no leg can leave, stay and fight
        (`policy.spent` is set on every Fight, so on a shove build under HOLD_WIDE none of them swings under any hold:
        they shove at point blank and stomp, `policies.Fight._shove`). Ruling P24-AP (`_wounded_fight`), as
        ruling R2 widens it (Task 32 fix 1): under any hold a zombie within KEEP_R is fought, never fled, and the Fight
        sends no swing (`_fight_spent`). The why's `strain` carries the pain and the frame's `body.strain` (each
        arm's stiffness, #4369) when it reads one.
        Ruling P24-AT's `wounded` (`self.wound`, logged `pain` {kind "wounded", armPain, strain} on the tick's threat
        why): the frame's `body.armPain` at STRAIN_HARD (#4370: every swing's damage halved or worse, whatever the
        pain's source) with `STRAIN` on. It is no hold: the Fight sends no swing (`policies.Fight.no_swing` reads the
        pain itself, `arms_hurt`: the shove at point blank, the stomp of a fallen one, the backpedal between), no
        `strain` flee is read for it, and a lone target is still sought (`_lone`); a group is fled as today."""
        pain = arm_pain(self.world)
        stiff = arm_stiffness(self.world)
        if stiff is None or stiff < STIFF_SOFT:
            self.strain_hold = False
        elif stiff >= STIFF_HARD:
            self.strain_hold = True
        st = self.world.stats or {}
        e, f = st.get("endurance"), st.get("fatigue")
        if not _num(e) or e > ENDURANCE_RELEASE:
            self.endurance_hold = False
        elif e <= ENDURANCE_T:
            self.endurance_hold = True
        kinds = () if not self.STRAIN else tuple(k for k, on in (
            ("arms", self.strain_hold), ("endurance", self.endurance_hold), ("tired", _num(f) and f >= TIRED_FIGHT_T))
            if on)
        self.spent_kinds = kinds
        self.spent = None if not kinds else {"kind": kinds[0], "armPain": pain, "endurance": e, "fatigue": f}
        strain = (self.world.body or {}).get("strain")
        if self.spent is not None and strain is not None:   # P24-AP: the stiffness (#4369) beside the pain, logged
            self.spent["strain"] = strain                    # (a PZA/1.7 frame carries it)
        hurt = self.STRAIN and pain is not None and pain >= STRAIN_HARD
        self.wound = {"kind": "wounded", "armPain": pain, "strain": strain} if hurt else None   # P24-AT

    def _wounded_fight(self):
        """Ruling P24-AP, the wounded fight (E9: a bite on part 5 read `body.armPain` 37.6 with `body.strain` 0 on both
        arms and held the strain hold to the death), as ruling R2 widens it (Task 32 fix 1, the review's major 4: E9's
        endurance hold stood from game minute 617, and a flee from a zombie at 0.5 tiles never works; the shove loses
        only 5 points of crit chance per endurance level, #4373): any hold this tick (`spent_kinds`: arms, endurance
        or tired) and a zombie within KEEP_R: it is fought whatever the hold (the Fight's shove at point blank, the
        stomp of a fallen one, the backpedal between, never the swing: `policies.Fight.no_swing`, which Survive feeds
        the hold, `_fight_spent`); the holds' release lines govern the seeking of fights only (`_sought`). With
        `HOLD_WIDE` off, the arms' hold alone (P24-AP as Task 32 landed it)."""
        if not self.HOLD_WIDE:
            return self.spent_kinds == ("arms",) and bool(self._within(KEEP_R))
        return bool(self.spent_kinds) and bool(self._within(KEEP_R))

    def _fight_spent(self):
        """The holds the Fight reads to send no swing (`policies.Fight.spent`, ruling R2): this tick's `spent_kinds`
        with `HOLD_WIDE` on and a build that announces `shove` (the point-blank answer R2 puts in the swing's place;
        on a build without it a held Fight would send nothing at 0.5 tiles, so the swing stays, as on E4's and F1's
        PZA/1.4 records), else () (the Fight reads `body.armPain` itself, `arms_hurt`)."""
        return self.spent_kinds if self.HOLD_WIDE and self.world.can("shove") else ()

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
        if self.mode is not None or self._sleeping() is not None or self.spent is not None:
            return None   # P24-AG, P24-AK: a spent character starts no fight
        near = self._within(ENGAGE_R)
        if self.wound is not None:   # P24-AT: wounded, a lone target only
            near = self._lone(near)
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

    def _lone(self, near):
        """Ruling P24-AT, the wounded seek: of `near` (the zombies listed within ENGAGE_R), `[t]` when `t` is a lone
        target: the one standing zombie (not `on_floor`) within ENGAGE_R, no other zombie within DANGER_R, and no other
        listed within LISTED_R chasing (`hasTarget`: a group coming, which the wounded character flees as today);
        else []. The fight then goes as any sought fight's, the Fight sending no swing (`arms_hurt`)."""
        standing = [z for z in near if not on_floor(z)]
        if len(standing) != 1:
            return []
        t = standing[0]
        if any(z is not t and zdist(self.world, z) <= DANGER_R for z in near):
            return []
        if any(z is not t and chasing(z) for z in self._within(LISTED_R)):
            return []
        return [t]

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
        engages it at once), so the goal it would supersede runs on. Fix 2: while `_chokepoint` holds (a room or door
        square) a zombie that is not chasing and stands beyond DANGER_R is not engaged: the goal runs, and a chase or
        DANGER_R still engages it."""
        mx, my = me_xy(self.world)
        if self._side(z) != self._side({"x": mx, "y": my}):
            return False
        if chasing(z):
            return True
        if self._chokepoint() and zdist(self.world, z) > DANGER_R:
            return False   # Task 18 fix 2, the re-review's blocker 2 (E7 286-332): held ground lets an idle one lie
        if line_to(self.world, z) is True:
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
        threat with health at or above FLEE_HEALTH or two with it at or above FLEE_HEALTH_PAIR (counted by
        `_stance_count`), and the character not trapped on a room square (`_trapped`: the corner rules stay for a stuck
        or trapped character)."""
        k = self._stance_count(held)
        if not (self.world.can("aim") and self._armed() and held and k <= MAX_FIGHT):
            return False
        if self._health() < self._fight_line(max(k, 1)):
            return False
        return not self._trapped(held, inside)

    def _stance_count(self, held):
        """The held zombies the stance counts (Task 32 fix 1, the review's major 6: E9's replayed line 342 lost the
        pull's stance to held 3 within DISENGAGE_R, one fallen at 7.43 and an idle one at 9.17, and ran at the
        chaser toward the group): those standing (not `on_floor`) and within DANGER_R or chasing (`_counts_listed`,
        the listing's own reading); with `STANCE_LISTED` off, every held one."""
        if not self.STANCE_LISTED:
            return len(held)
        return sum(1 for z in held if not on_floor(z) and self._counts_listed(z))

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

    def _pulls(self, t):
        """Ruling P24-AN for a Fight not yet made: `PULL` and the seek on, target `t` within AIM_R (the stance's) and a
        lone chaser with the rest of the listing beyond DANGER_R (`policies.pull_from`, the zombies read dead out)."""
        return (self.PULL and self._seeks() and t[2] <= AIM_R
                and pull_from(self.world, t, blocked(self.dead, self.clock())) is not None)

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
            if not self._takes_on(len(held)):   # P24-X: the flee turns to fight one or two at the fight's line
                return "held"
            if self.flee_health and health < FLEE_HEALTH + REFIGHT_MARGIN:   # the health flee stays, its margin kept
                return "held"
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
        one, or one not refused this episode."""
        f = self.flee
        if f is not None and f.exit is not None:
            return True
        return exit_plan(self.world, held, f.refused if f is not None else (), self.TRANS) is not None

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
        corner keeps swinging (P24-A fix 1 (4), confirmed)."""
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
          `flee` (reason `doorway`) while the stand's close runs, ahead of every other row (the stand's premise is the
          one-tile front the drag-down guard flees: the stand reads its own `drag` end at DRAG_DOWN_N, ruling R1).
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
          (`_trapped_fight`, G3).
        Not a pure function: it sets `sheltered`, `door`, `broken`, `cornered`, `corner_yield`, `behind` and `listed`
        (`_breach` before it set `closing`),
        and a corner inside a chosen shelter drops the sheltered Flee, so the next flee walks out rather than
        re-closing."""
        inside = self.night.inside()
        self.sheltered = self.flee is not None and self.flee.sheltered and inside
        self.broken, self.group_steer, self.corner_yield, self.behind, self.listed = None, None, None, None, None
        self.stand_left, self.stand_end = None, None
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
        if self.sheltered:
            return "flee", reason or "sheltered"
        if reason is None:
            reason = self._kept_flee()
            if reason is None:
                return "fight", None
        return self._trapped_fight(held, inside) or ("flee", reason)

    def _doorway(self):
        """Ruling P24-AO (`planner/doorway.py`'s docstring the record): `("doorway", None)` while the Flee's stand plan
        reads `stand` and none of its ends holds; the end (`plan["left"]`: `health` under FLEE_HEALTH, `drag` with the
        frame's `me.attackers` at DRAG_DOWN_N (ruling R1, Task 32 fix 1: the front has failed), `unarmed`, or `quiet`
        once no zombie has been within DANGER_R for DOOR_HOLD_S wall seconds, `plan["quiet"]` the last wall one was)
        puts the plan back on its `close` step, and while that close runs `("flee", "doorway")`: the Flee sends it from
        inside and its end is the shelter's as today. `off` (`doorway.off_post`: off the building's room squares and
        beyond DOOR_OFF_R of the threshold, fix 1's major 2) drops the plan instead, no close walked back to the door,
        logged `doorway_left` (`stand_end`, set for every end; `stand_left` is `off` alone, the Flee's keep) on the tick. Else None (no stand)."""
        f = self.flee
        plan = None if f is None else f.plan
        if plan is None or not plan.get("stood"):
            return None
        if plan["step"] == "stand":
            now = self.clock()
            if self._within(DANGER_R):
                plan["quiet"] = now
            left = ("health" if self._health() < FLEE_HEALTH else "drag" if self._attackers() >= DRAG_DOWN_N
                    else "unarmed" if not self._armed() else "off" if off_post(self.world, plan)
                    else "quiet" if now - plan["quiet"] >= DOOR_HOLD_S else None)
            if left is None:
                return "doorway", None
            plan.update(step="close", left=left)
            self.stand_end = left   # Task 32 fix 2: logged `doorway_left` for every end; `stand_left` (the Flee's keep) is `off` alone
            if left == "off":
                self.stand_left = left
                f._drop(False)   # the episode only steers from here (`picked` kept)
                return None
        return ("flee", "doorway") if f.closing_stand() else None

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
        or a walk whose straight line to its target reads clear on the map, a `solidTrans` square on it read as solid
        with `TRANS` on (ruling P24-AS; Task 32 fix 1, the review's minor 8: the walk paths round it, the ride does
        not); else None."""
        leg = self._flee_leg()
        if leg is None or leg.type == "steer":
            return leg
        a = leg.args
        return leg if self.world.line_clear(me_xy(self.world), (a.get("x"), a.get("y")), trans=self.TRANS) else None

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
        answers, the Flee's leg held by the ride: `policies.running`). Ruling P24-AR (`_rides_many`): under a `many`
        flee with a zombie chasing the ride goes with the nearest beyond RIDE_MANY_R, or, whatever the distance, once
        FLEE_CARE_S have passed since the first `many` (`many_since`) with FLEE_CARE_N or more parts bleeding."""
        if not self.world.can("bandage") or not self._nearest_seen or self.care.riding() is not None:
            return None
        near = self._nearest_seen[-1][1]
        chased = any(z.get("hasTarget") is True for z in held)
        free = self._rides_many(near) if (self.flee_many and chased) else (near > RIDE_R or not chased)
        if free and self._ride_leg() is not None:
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

    def _rides_many(self, near):
        """Ruling P24-AR, the care tick inside a long flee (E9: four bites bled the health from 96.39065551757812 to 0
        in 13.111 s while the `many` flee ran, five rags held): a `many` flee from a chaser lets the bandage ride its
        leg with the nearest zombie `near` beyond RIDE_MANY_R (a part bleeding with a dressing held, `rides_wound`), or
        whatever the distance once FLEE_CARE_S wall seconds have passed since the first `many` read (`many_since`)
        with FLEE_CARE_N or more parts bleeding, except under the drag-down guard (`me.attackers` at DRAG_DOWN_N - 1,
        `_drag`'s own line: Task 32 fix 1, the review's minor 9, E8's replayed ride at line 389 two ticks after the
        `drag` steer at 387, the nearest at 0.51: the ride holds the leg to a walk, P24-U). Before it no ride went under
        a `many` flee with a chaser held (the re-review's minor 4 of Task 12). The doorway stand has no care tick (its
        bleeding is the next iteration's, the review's minor 9)."""
        if near > RIDE_MANY_R:
            return True
        return (self.many_since is not None and self.clock() - self.many_since >= FLEE_CARE_S
                and self.care.bleeding_n() >= FLEE_CARE_N and self._attackers() < DRAG_DOWN_N - 1)

    def _threat(self):
        """The tick's bookkeeping, once (ruling P24-A (g)): the held list, the Flee's observe and the breach's closing
        count; then the yield to the care (`_care_yields`, P24-P), else the decision (`_decide`), which a corner's
        retarget may re-plan without them."""
        self.care_yield, self.care.ride_now, self.engaging, self.avoid = None, False, False, set()
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
        if kind == "doorway":
            return self._stand(held)
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
                self.fight.pull = self.fight.seek and self.PULL    # P24-AN: a lone chaser pulled from the group
                if door is None:
                    self.flee = None   # a door fight keeps the sheltered Flee for the re-close
                self._end_flee_episode()
            else:
                if self.flee is None or not (self.sheltered or self.flee.closing_stand()
                                             or self.stand_left is not None):   # a sheltered Flee outlives a door
                    # fight, and a stand's Flee its Doorway (P24-AO; one whose stand was left `off` only steers)
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
            if reason == "many" and self.many_since is None:
                self.many_since = self.clock()   # P24-AR: the long flee's clock, kept across its corners
            policy.threats = held
            policy.hold_ok = breach is None
            policy.steer_now = self.group_steer is not None
            policy.stand_ok = self.DOORWAY and self.flee_many and stand_ready(self.world, blocked(self.dead,
                                                                                               self.clock()))
            if self.group_steer:
                policy.give_way()   # amendment 6: the group pre-empts a running walk, as the corner does
            if self.group_steer == "drag":
                policy.drop_stuck_leg()   # P24-A fix 2, I1: never a stalled leg held its FLEE_S under the guard
            ans = self._flee_drop() or self._flee_finish(reason) or self._answer(policy)
        else:
            policy.only = None if door is None else {zid for zid, _ in door}
            policy.stance = self._stance_ok(held, self.night.inside())   # P24-G 1 (no corner or door Fight stands)
            policy.spent = self._fight_spent()   # R2: no swing under any hold
            policy.hold_ground = self._chokepoint()   # Task 18 fix 1, ruling 2: no seek from a room or door square
            policy.avoid = self.avoid                 # ... nor at a zombie no engage reaches (major 2)
            policy.ride = self.care.riding()   # P24-U: the stance legs held off while a bandage rides
            policy.threats = held
            policy.edge_ticks = EDGE_HOLD_TICKS if self.EDGE else 0   # P24-AU, read at the policy's observe
            ans = self._answer(policy)
        self.why.update({"fight": True} if reason is None else {"flee": reason})
        if reason == "strain" or self.corner_yield == "strain":
            self.why["strain"] = self.spent   # P24-AG: the why names the strain
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
        for key, v in (("yield", self.corner_yield), ("behind", self.behind), ("listed", self.listed),
                       ("doorway_left", self.stand_end), ("pain", self.wound)):
            if v is not None:
                self.why[key] = v
        if self.broken is not None:
            self.why["breach"] = self.broken
        ride = self.care.riding()
        if ride is not None:
            self.why["ride"] = ride.aid   # P24-U: a bandage rides the leg this answer holds or re-aims
        return ans if ans is not None else (policy, None)

    def _stand(self, held):
        """Ruling P24-AO: the doorway stand's answer: its `Doorway` fight over the Flee's stand plan (made once, kept
        while the plan stands; the Flee kept for the close), the mode `fight`, the flee episode's flags kept (the
        stand is the `many` flee's end), logged `doorway` (the building) beside the fight's why."""
        f = self.fight
        if f is None or f.doorway is None or f.plan is not self.flee.plan:
            self.fight = Doorway(self.world, self.actions, self.clock, self.flee.plan, unreachable=self.unreachable,
                                 dead=self.dead)
            self.cornered, self._corner_fight = None, None
        self.mode = "fight"
        policy = self.fight
        policy.threats = held
        policy.spent = self._fight_spent()   # R2: no swing under any hold
        policy.ride = self.care.riding()
        ans = self._answer(policy)
        self.why.update({"fight": True, "doorway": policy.doorway})
        return ans if ans is not None else (policy, None)

    def _released(self, held):
        """Task 18 fix 1 (the review's major 2: E4's fight on gate zombie 19001 held the goal off behind a locked
        gate): a running fight (neither a corner's nor a door fight) with no held threat within DANGER_R and none of
        the held ones it may engage (`_engageable`; one marked unreachable or read dead counted out) ends, and the goal
        runs: the release of P24-X's engage, as it was entered. Sets `avoid`, the held ids beyond DANGER_R no engage
        reaches (the Fight never pins one anew: `Fight.avoid`). Only with `ENGAGE` on."""
        f = self.fight
        if (not self.ENGAGE or self.mode != "fight" or f is None or f.point_blank or f.only is not None
                or f.doorway is not None):   # P24-AO: the doorway stand is left only by its own ends
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

    def _flee_finish(self, reason):
        """Ruling P24-AQ, the fallen target under `many` (E9: the two targets its swings struck, 7488 and 7474, read
        fallen while the `many` flee ran the character away from them, neither stomped): in a flee episode whose reason
        was `many`, a zombie the planner struck (an attack or a shove sent at it within UNREACHABLE_S, `struck`) that
        reads downed (`onFloor`) within FINISH_R (the stomp's own walk in; fix 1, the review's major 5) on a line not
        read blocked, with no standing zombie within DANGER_R (the next standing one beyond it), takes one `Stomp`
        before the flee resumes, or the weapon's floor strike (an `Attack` of it, only within FIGHT_REACH) when the
        stomp is not announced, would be refused (a standing zombie within STAND_MIN_R) or ended refused; never the
        floor strike at `body.armPain` STRAIN_HARD nor under any hold (P24-AP and R2: a swing). Sent as
        the Flee's own action (its leg superseded, the steer resumed on the next tick, as `_flee_drop`); one stomp and
        at most one floor strike a zombie (`finishing`); none in a hit reaction. With a standing zombie within DANGER_R
        the flee runs as today. Its end is read by `_finish_end` (a `targetDead` is a kill). Logged `finish`."""
        if not (self.flee_many or reason == "many") or (self._finish_a is not None and running(self.actions,
                                                                                               self._finish_a)):
            return None
        now = self.clock()
        dead = blocked(self.dead, now)
        if standing(self.world, DANGER_R, dead) or (self.world.me or {}).get("hitReaction"):
            return None
        best = None
        for zid, at in self.struck.items():
            z = self.world.zombies.get(zid)
            if (now - at > UNREACHABLE_S or zid in dead or z is None or z.get("x") is None or z.get("y") is None
                    or not on_floor(z) or self.finishing.get(zid) == "floor"):
                continue
            d = zdist(self.world, z)
            if d <= FINISH_R and line_to(self.world, z) is not False and (best is None or (d, repr(zid)) < best[0]):
                best = ((d, repr(zid)), zid)
        if best is None:
            return None
        zid = best[1]
        done = self.finishing.get(zid)
        stomp_ok = (self.world.can("stomp") and done is None
                    and not standing(self.world, STAND_MIN_R, dead | {zid}))
        if stomp_ok:
            cmd, kind = Stomp(zid), "stomp"
        elif done == "stomp" and not self._finish_refused(zid):
            return None   # the stomp went and was not refused: the one finish is spent
        elif arms_hurt(self.world) or self._fight_spent():
            self.finishing[zid] = "floor"   # P24-AP, R2: no floor strike (a swing) at STRAIN_HARD or under a hold
            return None
        elif best[0][0] > FIGHT_REACH:
            return None   # the floor strike swings from where the player stands: only within FIGHT_REACH
        else:
            cmd, kind = Attack(zid), "floor"
        self.finishing[zid] = kind
        self.why = {"finish": zid, "kind": kind, "dist": best[0][0]}
        return self.flee, cmd

    def _finish_refused(self, zid):
        """The flee's last finishing stomp ended refused (rejected, timed out, failed for any reason but `superseded`
        or `stood`, or done with `attackStarted` false): P24-AL's rule, the floor strike follows."""
        a = self._finish_a
        if a is None or a.type != "stomp" or a.args.get("targetId") != zid or not self.actions.done(a):
            return False
        res = a.result if isinstance(a.result, dict) else {}
        if a.state == "done":
            return res.get("attackStarted") is False
        return not (a.state == "failed" and a.reason in (PREEMPTED, "stood"))

    def _finish_end(self):
        """P24-AQ: the zombie id the flee's finishing stomp or floor strike read dead (`targetDead`, read once), the
        World's kill counted and the id skipped as dead; else None."""
        a = self._finish_a
        if a is None or a is self._finish_read or not self.actions.done(a):
            return None
        self._finish_read = a
        if not (isinstance(a.result, dict) and a.result.get("targetDead") is True):
            return None
        zid = a.args.get("targetId")
        self.dead[zid] = self.clock() + UNREACHABLE_S
        return zid if self.world.note_kill(zid) else None
