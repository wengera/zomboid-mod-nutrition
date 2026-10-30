"""The pull of a lone chaser and the listing's edge (rulings P24-AN and P24-AU): `pull_from` (moved from
`policies.py`, which re-exports it), the mixins `ThreatPull` (`threat.Threat`'s: the pull read for a Fight not yet
made) and `FightPull` (`fight.Fight`'s: the pull's centroid, its pin, its wait and its legs, and the edge hold).
Moved at Plan 25 Task 2 (a pure move: every rule and constant unchanged); `survive.py`'s and `fight.py`'s module
docstrings stay the record.
"""
from agent.base.planner.policies import (AIM_R, DANGER_R, DISENGAGE_R, ENGAGE_R, LISTED_R, PULL_R, blocked, chasing,
                                         target_id_ok, zdist)


def pull_from(world, t, skip=(), reach=ENGAGE_R, edge=None):
    """Ruling P24-AN, the pull (the guides notes § 9 change 8: draw one from a group by walking away, then fight it
    alone; E9 dropped six fights for a chaser 10.74 to 11.90 tiles behind the target, the look behind's `held`): the
    centroid (x, y) of the other zombies listed within LISTED_R when target `t` (id, zombie, dist) chases the player
    (`hasTarget`) within `reach` (ENGAGE_R; a chaser already pulled is kept to DISENGAGE_R: `Fight.seeking`), no other
    zombie chases within ENGAGE_R (one chaser), every other listed zombie stands beyond DANGER_R and at least one is
    listed; else None. The ids in `skip` (read dead) are no zombies. Ruling P24-AU: `edge` ({id: its record at its last
    listed square}, `Fight.edge`) are zombies that left the listing within EDGE_HOLD_TICKS: each counts as listed, read
    at that square, whatever the World holds of it now."""
    zid, z, d = t
    if not chasing(z) or d > reach:
        return None
    edge = edge or {}
    xs, ys = [], []
    for oid, o in list(world.zombies.items()) + [(i, rec) for i, rec in edge.items() if i not in world.zombies]:
        o = edge.get(oid, o)
        if oid == zid or oid in skip or o.get("x") is None or o.get("y") is None:
            continue
        od = zdist(world, o)
        if od > LISTED_R and oid not in edge:
            continue
        if od <= DANGER_R or (od <= ENGAGE_R and chasing(o)):
            return None
        xs.append(o["x"])
        ys.append(o["y"])
    return (sum(xs) / len(xs), sum(ys) / len(ys)) if xs else None


class ThreatPull:
    """The pull read for a Fight not yet made (the module docstring): `Threat`'s mixin."""

    def _pulls(self, t):
        """Ruling P24-AN for a Fight not yet made: `PULL` and the seek on, target `t` within AIM_R (the stance's) and a
        lone chaser with the rest of the listing beyond DANGER_R (`policies.pull_from`, the zombies read dead out)."""
        return (self.PULL and self._seeks() and t[2] <= AIM_R
                and pull_from(self.world, t, blocked(self.dead, self.clock())) is not None)


class FightPull:
    """The pull and the edge hold (the module docstring): `Fight`'s mixin."""

    def pull_centroid(self, t, reach=ENGAGE_R):
        """Ruling P24-AN: the centroid of the group a lone chaser `t` is pulled from (`pull_from` within `reach`, the
        zombies read dead left out), while `pull` is set and the stance applies to it; else None."""
        if not self.pull or t is None or not self.stance_at(t[2]):
            return None
        return pull_from(self.world, t, blocked(self.dead, self.clock()), reach,
                         {zid: rec for zid, (_, rec) in self.edge.items()})

    def _pull_pin(self):
        """Ruling P24-AN: with nothing pinned, the one zombie chasing within ENGAGE_R is pinned when the pull applies to
        it (`pull_centroid`), before the nearest: the chaser is the fight, a nearer idle one part of the group."""
        if not self.pull or self.target is not None:
            return
        skip = self.blocked()
        chasers = [(zid, z) for zid, z in self.world.zombies.items() if target_id_ok(zid) and zid not in skip
                   and chasing(z) and z.get("x") is not None and z.get("y") is not None
                   and zdist(self.world, z) <= ENGAGE_R]
        if len(chasers) == 1:
            zid, z = chasers[0]
            if self.pull_centroid((zid, z, zdist(self.world, z))) is not None:
                self.target, self.repositioned = zid, False

    def _pull_waits(self, t):
        """Ruling P24-AN (F1 with the PZA/1.5 caps replayed: its line 164 pulled 15911 at 8.93 tiles, which read 9.34 at
        the next tick, past ENGAGE_R, so the seek walked back toward it past the group): a chaser the pull was sent at
        (`_pulled`) that has fallen beyond ENGAGE_R while still a lone chaser within DISENGAGE_R is not sought: the
        stance stands facing it and lets it come (`stand`)."""
        return (t[0] == self._pulled and t[2] > ENGAGE_R
                and self.pull_centroid(t, DISENGAGE_R) is not None)

    def pulling(self, t):
        """Ruling P24-AN, the pull: the Fight seeks target `t` (`seeking`), a lone chaser beyond PULL_R with the rest of
        the listing beyond DANGER_R (`pull_centroid`): its stance legs walk away from the group (`pull`), never toward
        the chaser, until it comes within PULL_R; the look behind reads no walk then (`Survive._behind_walk`)."""
        return t is not None and t[2] > PULL_R and self.seeking(t) and self.pull_centroid(t) is not None

    def _observe_edge(self):
        """Ruling P24-AU, the listing-edge flip (E10's run 4, lines 234-245: two idle zombies 11.51 to 11.86 tiles off
        listed on every `pull` line and not on every `seek` line between, so the leg flipped each tick and seven aims
        were superseded): a zombie listed within LISTED_R at the last observe and beyond it (or gone from the World)
        now is held in `edge` at its last listed record for `edge_ticks` observes (EDGE_HOLD_TICKS, one a planner
        tick), the pull's group reading it there (`pull_centroid`); back within LISTED_R, or past the ticks, it is
        read as the World holds it. The target itself is never lost at the edge (its pin drops at DISENGAGE_R, the
        World keeps a zombie ZOMBIE_TTL_S after its last frame), so the edge is read on the group the leg is decided
        by."""
        now = {zid: z for zid, z in self.world.zombies.items() if z.get("x") is not None and z.get("y") is not None
               and zdist(self.world, z) <= LISTED_R}
        for zid in list(self.edge):
            self.edge[zid][0] += 1
            if zid in now or self.edge[zid][0] > self.edge_ticks:
                del self.edge[zid]
        for zid, rec in self._listed.items():
            if zid not in now and zid not in self.edge and self.edge_ticks > 0:
                self.edge[zid] = [1, rec]
        self._listed = {zid: dict(z) for zid, z in now.items()}
