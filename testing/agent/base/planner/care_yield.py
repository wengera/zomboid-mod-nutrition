"""The threat branch's yield to the care branch: the mixin `CareYield` that `threat.Threat` derives from (rulings
P24-P, P24-U and P24-AR: the bandage under a held threat, the ride on a flee leg, the care tick in a long flee; P26-D's
bleed under the threat branch and P26-L2's hold of its dressing; P27-O's ride on the `health` flee's leg).
Moved out of `threat.py` at Plan 25 Task 2 (a pure move: every rule, switch and constant unchanged; the constants
in `policies.py`'s table); its state is `Survive`'s own, set in `Survive.__init__`, and `survive.py`'s module docstring
stays the record of every rule here.
"""
from agent.base.planner.care import (CARE_HOLD_R, CARE_LEG_S, CARE_MARGIN, CARE_R, CARE_STILL_TICKS, FLEE_CARE_N,
                                     FLEE_CARE_S, RIDE_MANY_R, RIDE_R)
from agent.base.planner.clock import ClockGate
from agent.base.planner.policies import (BLEED_SPAN_MIN, BLEED_WINDOW_MIN, DANGER_R, DRAG_DOWN_N, FIGHT_REACH,
                                         GROUP_LEAVE_N, KEEP_R, POINT_BLANK_R, STEER_TURNS, Policy, _rotate, away_vector, blocked,
                                         clear_heading, standing, zdist)
from agent.base.pza1 import Steer
from agent.base.world import me_xy


class CareLeg(Policy):
    """Plan 32 Task 5 (c): the care's one distance leg, a walk directly away from the nearest zombie, held by the threat
    branch (`CareYield._care_commit`); `key` the care action it was planned for (`care.Care.commit_key`), `over` once
    it is spent (its distance gained, its CARE_LEG_S passed, or its steer ended)."""

    def __init__(self, world, actions, clock, key):
        super().__init__(world, actions, clock)
        self.key = key
        self.sent_wall = None
        self.over = False

    def choose(self):
        return None

    def sent(self, cmd, action):
        self.sent_wall = self.clock()


def _num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


class CareYield(ClockGate):
    """The care yield (the module docstring): `Threat`'s mixin; Plan 36 Task 4: over the action clock's gate
    (`clock.ClockGate`), whose commitment `_clock_commit` is."""

    def _read_bleed(self):
        """Ruling P30-F (`DRESS_RIDE`): each part's health (`body.parts` `h`) sampled this tick at the World's minutes,
        the samples of the last BLEED_WINDOW_MIN game minutes kept (`_part_h`); a part the frame no longer lists is
        dropped. Read once a threat read, every tick."""
        now = self.world.world_minutes()
        keep = {}
        for p in (self.world.body or {}).get("parts") or ():
            i, h = p.get("i"), p.get("h")
            if not (isinstance(i, int) and _num(h)):
                continue
            old = [s for s in self._part_h.get(i, ()) if now - s[0] <= BLEED_WINDOW_MIN and s[0] < now]
            keep[i] = old + [(now, h)]
        self._part_h = keep

    def _bleed_rate(self, part):
        """Ruling P30-F: part `part`'s health fall a game minute over its kept samples (the oldest to this tick's), None
        with under BLEED_SPAN_MIN game minutes of them."""
        s = self._part_h.get(part) or ()
        if len(s) < 2 or s[-1][0] - s[0][0] < BLEED_SPAN_MIN:
            return None
        return (s[0][1] - s[-1][1]) / (s[-1][0] - s[0][0])

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
        FLEE_CARE_S have passed since the first `many` (`many_since`) with FLEE_CARE_N or more parts bleeding.
        Ruling P26-D (`THREAT_BLEED`; F7, `f_goals_8-20261102-093241`: part 2 bled on all 157 frames from seq 18234 to
        the log's end while every decision line was the threat branch's, the yield refused on each by the nearest within
        CARE_R, the chased flee, the closing read or a bleeding step with nothing to send): a `pair` or `held` flee's
        leg rides the bleed as the `many` leg does (`_bleed_leg`, `_rides_many`); and a fight's tick that the closing
        read or CARE_R would refuse yields all the same when the bleed leaves room (`_bleed_free`: no zombie within
        FIGHT_REACH, the nearest listed beyond POINT_BLANK_R) and the bleeding step's send is a dressing
        (`Care.dresses_wound`, never a rip or an unwear), the running bandage held while the room lasts. A yield only
        this rule made is kept in `bleed_yield` (the threat why's `care_yield` {why "bleed", near}). Ruling P26-L2
        (`BLEED_HOLD`): the dressing that yield sent keeps the room with a zombie within FIGHT_REACH while none closes
        (`_bleed_holds`), a tick so held kept in `bleed_held` (the why's `care_yield` {why "bleed", near, held
        true}). Ruling P27-K1 (`STOCK_EARLY`; F10, `f_goals_11-20261103-075140`: the care's rip of the T-shirt for part
        7, why `no_rag`, went on lines 817, 832, 847 and 862, the first three superseded by the threat branch's flee
        legs): the yield takes the wound's rip (a held cotton garment ripped for a bleeding part with nothing to dress
        it) as it takes a dressing: a running rip holds the yield as a running bandage does (the nearest beyond
        CARE_HOLD_R), and the bleed's room takes the rip as well as a dressing (`Care.dresses_wound`). Ruling P27-O
        (`HEALTH_RIDE`; E20, `e_day_20-20261103-121340`: over the `health` flee's 98 lines from the bite no dressing was
        sent with six held while parts 9 and 7 bled, the chaser 1.283800888761518 to 5.083229199369507 tiles behind,
        inside RIDE_R): the `health` flee's leg is admitted as the `many` flee's (`_rides_health`), the ride's own
        reads (`_ride_leg`, `Care.rides_wound`) unchanged; a ride only its clock admitted is logged `ride` {flee
        "health"} (`ride_flee`). Plan 34 (LEAVE_CARE, `_column_bars`; F19's 21 care lines of 55 under the leave's `run`,
        8 stops, an unwear and 5 rips, each rip superseded 0.5 to 1.5 s later as the column of four or five within 6
        tiles closed back to 1.78-2.47 tiles): with GROUP_LEAVE_N or more standing within GROUP_ENTRY_R the ride above
        (P24-U, P24-AR, P26-D, P27-O: a bandage with keepMoving on a part above the legs, which keeps the leg) is the one
        yield; every one after it (the scratch's, the bleed's standing dressing, the rip) is None, `care_withheld` set.
        Plan 36 Task 4 (ACTION_CLOCK): past the ride every yield here is the clock's commitment's (`_clock_commit`),
        whose care step the clock decides; the distance rules above (CARE_R, CARE_HOLD_R, the closing read, the bleed's
        room, the column) read nothing."""
        if not self.world.can("bandage") or not self._nearest_seen or self.care.riding() is not None:
            return None
        near = self._nearest_seen[-1][1]
        chased = any(z.get("hasTarget") is True for z in held)
        free = self._rides_many(near) if (self.flee_many and chased) else (near > RIDE_R or not chased)
        health = not free and chased and not self.flee_many and self._rides_health()   # P27-O: the health flee's leg
        bleed = not free and not health and chased and self._bleed_leg() and near > RIDE_MANY_R   # P26-D
        if (free or bleed or health) and self._ride_leg() is not None:
            self._observe(self.care)
            if self.care.rides_wound():
                self.care.ride_now = True
                self.bleed_yield = near if bleed else None
                self.ride_flee = "health" if health else None
                return near
        if self._clock_on():
            return None   # Plan 36 Task 4: past the ride the clock's commitment is the one yield (`_clock_commit`)
        if self._column_bars(self.care.commit_key()):
            return None   # Plan 34 (LEAVE_CARE): under a column the ride alone
        scratch = self._wound_yields(held, near)   # Plan 31 Task 15a: a scratch's Dress, no part bleeding
        if scratch is not None:
            return scratch
        if self.flee_many:
            return None
        rip = self.care.stock_early   # P27-K1: the wound's rip is taken as a dressing is
        running = self.care.busy() and (self.care.last.type == "bandage" or (rip and self.care.last.type == "rip"))
        refused = (near <= (CARE_HOLD_R if running else CARE_R)
                   or (not running and (self._closing() or (self.mode == "flee" and chased))))
        if refused and not self._bleed_free():
            return None
        if self._many_read(held, len(self._within(DANGER_R)))[0]:
            return None
        self._observe(self.care)
        if not refused:
            return near if self.care.tends_wound() else None
        if not self.care.dresses_wound(rip=rip):
            return None
        self.bleed_yield = near   # P26-D: the yield the bleed's room made
        self.bleed_held = bool(self._within(FIGHT_REACH))   # P26-L2: the room only the dressing's hold made
        return near

    def _care_commit(self, held):
        """Plan 32 Task 5 (c) (`CARE_COMMIT`; Angus watching F17, `f_goals_17-20261108-172833`, memory
        `finish-actions-gain-distance`: of its 15 rips 14 failed, every one superseded, 13 of them sent after the care's
        stop, each by the threat branch's flee leg or the Dress's own next stop as a chaser closed within CARE_HOLD_R
        between lines 279 and 330, the scratch on part 1 dressed at the 15th): an action the care wants or runs
        (`care.Care.commit_key`) is done by gaining distance once and finishing it. `("leg", (policy, command))` while
        the one leg runs or is sent, `("yield", near)` when the threat branch yields the tick to the care, else None
        (the yields before it, `_care_yields`, decide): None with the rule off, a riding bandage running, nothing
        wanted, or a standing zombie (not `onFloor`, one read dead aside) within KEEP_R (the Fight's, rule (a); the
        Dress's own end). A running action (`commit_running`) is yielded to until it ends. Wanted and not running: with
        the nearest standing zombie (within DANGER_R; a fallen one makes no leg) within CARE_HOLD_R and no leg spent for
        this action, one leg (`CareLeg`): a walk directly away from it (the first clear heading of STEER_TURNS), CARE_LEG_S
        long; it holds the threat branch until the nearest standing reads CARE_HOLD_R + CARE_MARGIN or farther, its
        CARE_LEG_S pass, or it ends; then (or with the nearest beyond CARE_HOLD_R from the start) the yield, so the care
        starts the action, and never a second leg for the same action (`key`; an action interrupted within KEEP_R before
        any leg takes its one leg after). Logged `care_commit` {key, phase "leg" | "hold" | "yield", near}.
        Cost if wrong: a dressing's seconds standing with a zombie closing from CARE_HOLD_R to KEEP_R.
        Plan 34 (LEAVE_CARE, `_column_bars`; F19, `f_goals_19-20261109-060929`: of 55 lines from game minute 770 to 777
        under the leave's `run` 21 were the care's, 8 stops, an unwear and 5 rips (decision.log lines 1559, 1580, 1584,
        1589, 1599), each rip superseded 0.5 to 1.5 s later as four or five standing zombies within 6 tiles closed back
        to 1.78-2.47 tiles, every care line logging `care_commit` {phase "yield", key ["bleed", 7]} with the nearest
        standing 2.9 to 4.2 tiles off: this read only KEEP_R, before the threat plan read the group): with GROUP_LEAVE_N
        or more standing within GROUP_ENTRY_R (`group_n`) None, no leg and no yield, `care_withheld` set; the care
        resumes on the line the count falls under GROUP_LEAVE_N.
        Plan 35: None while the Fight's melee is engaged (`threat.Threat._engage_holds`, logged
        `engage_hold` {rule "care"}) where the commitment would answer: no leg nor yield over the reflex; fix 2: but a
        bleeding part answers as before (`_care_engage_holds`).
        Plan 36 Task 4 (ACTION_CLOCK): the commitment is `_clock_commit`'s, the leg the clock's (`clock.ClockLeg`)."""
        self.care_commit = None
        c = self.care
        if not self.CARE_COMMIT or not self.world.can("bandage") or c.riding() is not None:
            return None
        if self._clock_on():
            return self._clock_commit()   # Plan 36 Task 4: the commitment is the clock's
        key = c.commit_key()   # read before the bars, so a column's bar names what it withheld
        if self._column_bars(key):
            return None   # Plan 34 (LEAVE_CARE): the yields after it, the ride alone, decide
        if standing(self.world, KEEP_R, self._skipped()):
            return None   # the Fight's (rule (a)), the leg kept for its action (no second one)
        if key is None:
            self.care_leg = None
            return None
        if self._care_engage_holds():
            return None   # Plan 35: the engaged melee is not superseded for the care (but a bleed's)
        leg = self.care_leg
        if leg is not None and leg.key != key:
            leg = self.care_leg = None
        ids = {id(z): zid for zid, z in self.world.zombies.items()}
        nz = min(((zdist(self.world, z), repr(ids[id(z)]), ids[id(z)]) for z in standing(self.world, DANGER_R,
                                                                                       self._skipped())), default=None)
        near = None if nz is None else nz[0]   # the nearest standing within DANGER_R: a fallen one makes no leg
        why = {"key": list(key), "near": near}
        if c.commit_running() or (leg is not None and leg.over):
            self.care_commit = dict(why, phase="yield")
            return "yield", self._yield_near()
        if leg is not None:
            if (near is None or near >= CARE_HOLD_R + CARE_MARGIN or self.clock() - leg.sent_wall >= CARE_LEG_S
                    or not leg.busy()):
                leg.over = True
                self.care_commit = dict(why, phase="yield")
                return "yield", self._yield_near()
            self.care_commit = dict(why, phase="hold", aid=leg.last.aid)
            return "leg", (leg, None)
        if near is not None and near <= CARE_HOLD_R:
            v = self._care_leg_heading(nz[2])
            if v is not None:
                self.care_leg = CareLeg(self.world, self.actions, self.clock, key)
                self.care_commit = dict(why, phase="leg")
                return "leg", (self.care_leg, Steer(v[0], v[1], CARE_LEG_S, "walk"))
        self.care_commit = dict(why, phase="yield")
        return "yield", self._yield_near()

    def _clock_commit(self):
        """Plan 36 Task 4 (the action clock, `clock.py`'s docstring; F21, `f_goals_21-20261111-150552`, decision lines
        427 to 494: seven rips started under the commitment's yield with the nearest standing 3.4 to 5.7 tiles off,
        every one superseded by the threat branch's next steer once LEAVE_CARE read the column, and no bandage sent
        while three parts bled from 68 to 13 health): the commitment rewritten to the clock. An action the care wants or
        runs (`care.Care.commit_key`) takes the tick, `("yield", near)` logged `care_commit` {key, near, phase
        "yield"}, so the care branch steps it and the clock decides each step there (`ClockGate._clock_gate`: the
        action, or the gain-distance leg); None (the threat branch decides) with nothing wanted, under the clock's cut
        (`clock_cut`: the melee), with a standing zombie within KEEP_R (the Fight's, rule (a)), while the engaged melee
        holds (Plan 35, `_care_engage_holds`), or while the action's episode is spent and the clock still refuses it
        (phase "spent"). CARE_HOLD_R's leg and LEAVE_CARE's column bar are the clock's now. Cost if wrong: a care step
        refused for a zombie the clock reads closing that never comes (the leg's seconds)."""
        c = self.care
        key = c.commit_key()
        if key is None:
            self.care_leg = None
            return None
        if self.clock_cut is not None or self._clock_contact() or self._care_engage_holds():
            return None
        ids = {id(z): zid for zid, z in self.world.zombies.items()}
        nz = min(((zdist(self.world, z), repr(ids[id(z)])) for z in standing(self.world, DANGER_R, self._skipped())),
                 default=None)
        why = {"key": list(key), "near": None if nz is None else nz[0]}
        if self._clock_spent(key):
            kind = c.next_kind()
            if kind is not None and not self.action_clock.allows(kind):
                self.care_commit = dict(why, phase="spent")
                return None
            self.clock_leg = None   # the clock allows it now: the action goes
        self.care_commit = dict(why, phase="yield")
        return "yield", self._yield_near()

    def _care_engage_holds(self):
        """Plan 35's engagement hold over the care (`_care_commit`, the yields' post-check in `threat.Threat._threat`): True
        (logged `engage_hold` {rule "care"}) while the engagement holds (`threat.Threat._engage_holds`); fix 2 (the
        controller's ruling; Angus's dress first, memory `stand-and-fight-dress-first`): a bleeding unbandaged part
        (`care.Care.bleeding_n`, P24-AR's count) with no standing zombie within KEEP_R (rule (a)'s read, `standing`)
        yields it, False, logged `engage_yield` {rule "bleed"}: the dressing goes over the melee, which the ladder
        re-sends once a zombie stands in reach."""
        if (self._engage_on() and self.care.bleeding_n() > 0
                and not standing(self.world, KEEP_R, self._skipped())):
            self.engage_yield = {"rule": "bleed"}
            return False
        return self._engage_holds("care")

    def _column_bars(self, key):
        """Plan 34 (LEAVE_CARE, the spec's § 3.1): the care is barred this tick, a column of GROUP_LEAVE_N or more
        standing zombies within GROUP_ENTRY_R read (`group_n`, `group.ThreatGroup._group_read`), with the rule on; then
        `care_withheld` is {why "group", n, key} (`key` the care's `commit_key`, a list, else None), logged on the
        threat's why. A rip cannot ride a leg (the handcraft stops on a walk: `PZAgent_Tend.lua`'s note), so under a
        column only the ride (a bandage with keepMoving) dresses."""
        if not (self.LEAVE_CARE and self.group_n >= GROUP_LEAVE_N):
            return False
        self.care_withheld = {"why": "group", "n": self.group_n, "key": list(key) if key is not None else None}
        return True

    def _yield_near(self):
        """The tiles the threat's why logs `nearest` on a commitment's yield: the nearest listed zombie's read this tick
        (`_nearest_seen`, as every yield logs it), never None (a yield with none listed logs 0.0: no threat tick has
        none held)."""
        return self._nearest_seen[-1][1] if self._nearest_seen else 0.0

    def _care_leg_heading(self, zid):
        """Plan 32 Task 5 (c): the unit heading directly away from zombie `zid` (the nearest standing), turned by the
        first of STEER_TURNS whose line reads clear (`policies.clear_heading`), else the straight one."""
        z = self.world.zombies[zid]
        v = away_vector(self.world, [(z["x"], z["y"])])
        if v is None:
            return None
        for deg in STEER_TURNS:
            w = _rotate(v, deg)
            if clear_heading(self.world, w, trans=self.TRANS):
                return round(w[0], 6), round(w[1], 6)
        return round(v[0], 6), round(v[1], 6)

    def _wound_yields(self, held, near):
        """Plan 31 Task 15a (SCRATCH_DRESS; the ladder's street defect (b): round two's trial 12,
        `x_trial-ladder-20261106-031801`, whose two scratches went undressed from health 92.7 to 16.2 while the threat
        branch answered 305 of its 600 lines, among them its flee legs from chasers 8 to 9.6 tiles off over decision
        lines 316 to 328, none within KEEP_R): the nearest listed zombie's tiles `near` when the threat branch yields
        this tick to the care's Dress of a wound not bleeding, else None. No part may bleed (the bleed's own rules,
        P24-P to P27-K1, decide then), no zombie (one read dead aside) stand within KEEP_R (the Dress's own end), and
        no `many` be read this tick (a group, `_many_read`, as the bleed's yield refuses one; a `many` flee episode whose
        group is no longer read so, trial 12's lines 314 to 330 with the nearest 6.0 to 9.6 tiles off, is no bar: the
        bleed's ride has its own rule there, P24-AR, and a scratch cannot ride); a running wound Dress (`Care.dress`)
        holds the yield while that lasts, unless the nearest is closing within CARE_HOLD_R (fix 1, review-t15a M2: as a
        running bleed bandage gives way there, so a scratch, the less urgent wound, never keeps the character still
        nearer an approaching zombie than a bleed would); a new one starts only with the nearest beyond CARE_R or not closing
        (`_closing`, the bleed's hysteresis without its flee clause: a scratch is dressed under a flee's lull, the
        dressing first) and `Care.scratch_wanted`; the standing read is the Care's own (`Care.scratch_room`, its
        `skip` the ids read dead: fix 1, review-t15a M5). Logged `care_yield` {why "scratch", near} on the threat's why.
        Cost if wrong: a stop under a chaser beyond KEEP_R, whose arrival ends the Dress and gives the Fight the tick."""
        c = self.care
        if not c.scratch_dress or c.bleeding_n() or not c.scratch_room():
            return None
        if self._many_read(held, len(self._within(DANGER_R)))[0]:
            return None
        self._observe(c)
        d = c.dress
        running = d is not None and d.wound and d.over() is None
        if running and near <= CARE_HOLD_R and self._closing():
            return None   # fix 1, review-t15a M2: a running scratch's Dress gives way at CARE_HOLD_R, as a bleed's does
        if not running and ((near <= CARE_R and self._closing()) or not c.scratch_wanted()):
            return None
        self.scratch_yield = near
        return near

    def _bleed_leg(self):
        """Ruling P26-D: the running flee is a `pair` or `held` one (`flee_reason`, its last decision's), with
        `THREAT_BLEED` on: its leg rides the bleed on the distance rule of `_rides_many` alone, the nearest beyond
        RIDE_MANY_R (ruling P26-7e; `_rides_many`'s FLEE_CARE_S clause, the long `many` episode with FLEE_CARE_N parts
        bleeding, is the `many` episode's: `many_since` outlives the `many` flee while a threat is held)."""
        return self.THREAT_BLEED and self.mode == "flee" and self.flee_reason in ("pair", "held")

    def _bleed_free(self):
        """Ruling P26-D, the room the bleed takes on a threat tick (`THREAT_BLEED` on): a Fight runs (`mode` fight;
        never the doorway stand's, whose new bleeding part is its `wound` end, nor a flee's, whose bleed rides its leg,
        P24-P's fix 2: a standing bandage stops the run), no zombie within FIGHT_REACH (`_within`: the Fight has no
        target in reach, nor any other zombie there, one read dead or held out across a blocked edge aside) and the
        nearest listed zombie beyond POINT_BLANK_R: the fight line between swings. F7's read (the task's report) asks
        for no radius of its own: its undressed fight lines lay 2.27 to 7.71 tiles from their nearest zombie. With a
        zombie within FIGHT_REACH the room lasts only for the running dressing this yield sent, while that one zombie
        is not closing (`_bleed_holds`, rulings P26-L2 and P26-L2a)."""
        if not self.THREAT_BLEED or self.mode != "fight" or self.fight is None or self.fight.doorway is not None:
            return False
        if self._nearest_seen[-1][1] <= POINT_BLANK_R:
            return False
        return not self._within(FIGHT_REACH) or self._bleed_holds()

    def _bleed_holds(self):
        """Ruling P26-L2 (F8, `f_goals_9-20261102-181937`: P26-D's two dressings in its last fight, a272 and a280,
        were superseded 1.999 and 1.951 s in, against the 2.601, 2.726 and 5.828 s of the three that landed (a23,
        a143, a162), each from its accept, by the threat branch's backpedal and its `health` flee's steer, 28762
        within FIGHT_REACH): with `BLEED_HOLD` on, the dressing the bleed's yield sent (`bleed_dressing`,
        `Survive._apply`), still running as the care's own bandage, is held as P25-D holds a riding one while the
        one zombie within FIGHT_REACH (ruling P26-L2a: F8's lone fight; with two in reach the hold does not apply and
        the threat branch decides, the `pair` flee under wounds) is not closing (`_closing`): the threat branch's
        sends (the Fight's shove, swing or stance leg) wait; a zombie closing inside FIGHT_REACH, or one within
        POINT_BLANK_R (`_bleed_free`), supersedes it as before. Both of F8's read closing (each nearer than two ticks
        before), so neither would have been held. Cost if wrong: a bandage completing while a zombie walks in from
        1.5 tiles (the stance leg lost); the closing read and the Fight's reach bound it."""
        a = self.bleed_dressing
        if not self.BLEED_HOLD or a is None or not self.care.busy() or self.care.last is not a:
            return False
        return len(self._within(FIGHT_REACH)) == 1 and not self._closing()

    def _rides_health(self):
        """Ruling P27-O: the running flee is a `health` one (`flee_reason`, its last decision's) with `HEALTH_RIDE` on,
        FLEE_CARE_S wall seconds have passed since that flee began (`health_since`) and a part bleeds
        (`Care.bleeding_n`), except under the drag-down guard (`me.attackers` at DRAG_DOWN_N - 1), as `_rides_many`'s
        clock clause reads; the nearest beyond RIDE_R rides already by P24-U's own clause."""
        return (self.HEALTH_RIDE and self.mode == "flee" and self.flee_reason == "health"
                and self.health_since is not None and self.clock() - self.health_since >= FLEE_CARE_S
                and self.care.bleeding_n() >= 1 and self._attackers() < DRAG_DOWN_N - 1)

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
