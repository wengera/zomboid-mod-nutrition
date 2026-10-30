"""The engage of the threat branch: the mixin `Engage` that `threat.Threat` derives from (ruling P24-X and Task 18
fix 1: the sought fight, the reach of an engage, the held ground, the standing fight's stance, the release).
Moved out of `threat.py` at Plan 25 Task 2 (a pure move: every rule, switch and constant unchanged; the constants
in `policies.py`'s table); its state is `Survive`'s own, set in `Survive.__init__`, and `survive.py`'s module docstring
stays the record of every rule here.
"""
import math

from agent.base.planner.policies import (DANGER_R, ENGAGE_R, FLEE_HEALTH, FLEE_HEALTH_PAIR, MAX_FIGHT, UNREACHABLE_S,
                                         chasing, line_to, on_floor, target_id_ok, zdist)
from agent.base.world import me_floor, me_xy


class Engage:
    """The engage (the module docstring): `Threat`'s mixin."""

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
