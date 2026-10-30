"""The threat branch's yield to the care branch: the mixin `CareYield` that `threat.Threat` derives from (rulings
P24-P, P24-U and P24-AR: the bandage under a held threat, the ride on a flee leg, the care tick in a long flee).
Moved out of `threat.py` at Plan 25 Task 2 (a pure move: every rule, switch and constant unchanged; the constants
in `policies.py`'s table); its state is `Survive`'s own, set in `Survive.__init__`, and `survive.py`'s module docstring
stays the record of every rule here.
"""
from agent.base.planner.care import CARE_HOLD_R, CARE_R, CARE_STILL_TICKS, FLEE_CARE_N, FLEE_CARE_S, RIDE_MANY_R, RIDE_R
from agent.base.planner.policies import DANGER_R, DRAG_DOWN_N, blocked, zdist
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
