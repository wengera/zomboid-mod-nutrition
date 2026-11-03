"""The threat branch's yield to the care branch: the mixin `CareYield` that `threat.Threat` derives from (rulings
P24-P, P24-U and P24-AR: the bandage under a held threat, the ride on a flee leg, the care tick in a long flee; P26-D's
bleed under the threat branch and P26-L2's hold of its dressing; P27-O's ride on the `health` flee's leg).
Moved out of `threat.py` at Plan 25 Task 2 (a pure move: every rule, switch and constant unchanged; the constants
in `policies.py`'s table); its state is `Survive`'s own, set in `Survive.__init__`, and `survive.py`'s module docstring
stays the record of every rule here.
"""
from agent.base.planner.care import CARE_HOLD_R, CARE_R, CARE_STILL_TICKS, FLEE_CARE_N, FLEE_CARE_S, RIDE_MANY_R, RIDE_R
from agent.base.planner.policies import DANGER_R, DRAG_DOWN_N, FIGHT_REACH, POINT_BLANK_R, blocked, zdist
from agent.base.world import me_xy


class CareYield:
    """The care yield (the module docstring): `Threat`'s mixin."""

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
        "health"} (`ride_flee`)."""
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
