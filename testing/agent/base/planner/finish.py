"""The finish of the fallen and the stomp: the mixins `ThreatFinish` (`threat.Threat`'s: ruling P24-AQ, the
`many` flee's finishing stomp, its end and its chaser, P24-AV) and `FightFinish` (`fight.Fight`'s: ruling P24-AL's
finish, the downed read and P24-AV's stomp wait on a shove's knock-down). Moved out of `threat.py` and `fight.py`
at Plan 25 Task 2 (a pure move: every rule and constant unchanged; the constants in `policies.py`'s table); the
state is `Survive`'s and the `Fight`'s own, and `survive.py`'s and `fight.py`'s module docstrings stay the record.
"""
import math

from agent.base.planner.policies import (DANGER_R, FIGHT_REACH, FINISH_R, KEEP_R, POINT_BLANK_R, PREEMPTED, SHOVE_R,
                                         STAND_MIN_R, UNREACHABLE_S, arms_hurt, blocked, chasing, hit_reaction, line_to,
                                         on_floor, running, standing, target_id_ok, zdist)
from agent.base.pza1 import Attack, Shove, Stomp


def finish_chaser(world, zid, dead):
    """The deferred minor 5 of review-t32-fix1: (id, tiles) of the nearest standing (not `on_floor`) zombie chasing
    (`hasTarget`) within KEEP_R of the fallen target `zid`, the ids in `dead` and the target left out, else None: the
    stomp's walk to the target would end at it (the flee's finish, P24-AV, and the Fight's stomp first, P25-B)."""
    t = world.zombies[zid]
    best = None
    for oid, o in world.zombies.items():
        if oid == zid or oid in dead or on_floor(o) or not chasing(o) or o.get("x") is None or o.get("y") is None:
            continue
        d = math.hypot(o["x"] - t["x"], o["y"] - t["y"])
        if d <= KEEP_R and (best is None or (d, repr(oid)) < (best[1], repr(best[0]))):
            best = (oid, d)
    return best


class ThreatFinish:
    """The `many` flee's finish (the module docstring): `Threat`'s mixin."""

    def _flee_finish(self, reason):
        """Ruling P24-AQ, the fallen target under `many` (E9: the two targets its swings struck, 7488 and 7474, read
        fallen while the `many` flee ran the character away from them, neither stomped): in a flee episode whose reason
        was `many`, a zombie the planner struck (an attack or a shove sent at it within UNREACHABLE_S, `struck`) that
        reads downed (`onFloor`: ruling P24-AV, the first frame reading it fallen, never a shove's knock-down alone)
        within FINISH_R (the stomp's own walk in; fix 1, the review's major 5) on a line not read blocked, with no
        standing zombie within DANGER_R (the next standing one beyond it), takes one `Stomp` before the flee resumes, or
        the weapon's floor strike (an `Attack` of it, only within FIGHT_REACH) when the stomp is not announced, would
        be refused (a standing zombie within STAND_MIN_R) or ended refused; never the floor strike at `body.armPain`
        STRAIN_HARD nor under any hold (P24-AP and R2: a swing). Sent as the Flee's own action (its leg superseded, the
        steer resumed on the next tick, as `_flee_drop`); one stomp and at most one floor strike a zombie
        (`finishing`); none in a hit reaction. With a standing zombie within DANGER_R the flee runs as today. Its end is
        read by `_finish_end` (a `targetDead` is a kill). Logged `finish`.
        Ruling P24-AV: a stomp that failed `stood` (the target rose) reads the target again on the next tick: standing
        within DANGER_R the flee runs (no finish); fallen again, one more stomp (`kind` "stomp2"), and that one failed
        `stood` or refused, the floor strike. The deferred minor 5 of review-t32-fix1 (E9's line 334: the 4.62-tile
        stomp walk toward 7474 headed at 7479, standing and chasing 2.16 tiles from it): a chasing standing zombie
        within KEEP_R of the target refuses the finish (`_finish_chaser`, logged `finish_block`)."""
        self.finish_block = None
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
        chaser = self._finish_chaser(zid, dead)
        if chaser is not None:
            self.finish_block = {"target": zid, "chaser": chaser[0], "dist": chaser[1]}
            return None
        done, end = self.finishing.get(zid), self._finish_end_read(zid)
        again = done == "stomp" and end == "stood"   # P24-AV: fallen again after a `stood`: one more stomp
        if ((done is None or again) and self.world.can("stomp")
                and not standing(self.world, STAND_MIN_R, dead | {zid})):
            cmd, kind = Stomp(zid), ("stomp" if done is None else "stomp2")
        elif done in ("stomp", "stomp2") and end is None:
            return None   # the stomp went (or runs) and was not refused: the one finish is spent
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

    def _finish_chaser(self, zid, dead):
        """`finish_chaser` over the World (the flee's finish, P24-AV)."""
        return finish_chaser(self.world, zid, dead)

    def _finish_end_read(self, zid):
        """The end of the flee's last finishing stomp at `zid`: "stood" when it failed `stood` (P24-AV: the target
        rose), "refused" when it ended refused (rejected, timed out, failed for any reason but `superseded` or `stood`,
        or done with `attackStarted` false: P24-AL's rule, the floor strike follows), else None (none, another
        target's, running, superseded or done)."""
        a = self._finish_a
        if a is None or a.type != "stomp" or a.args.get("targetId") != zid or not self.actions.done(a):
            return None
        res = a.result if isinstance(a.result, dict) else {}
        if a.state == "done":
            return "refused" if res.get("attackStarted") is False else None
        if a.state == "failed" and a.reason == "stood":
            return "stood"
        return None if a.state == "failed" and a.reason == PREEMPTED else "refused"

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


class FightFinish:
    """The Fight's finish of the fallen and its stomp wait (the module docstring): `Fight`'s mixin."""

    def _downed(self, knocked=False):
        """(id, zombie, dist) of each downed zombie (`on_floor`) the Fight may target within FIGHT_REACH whose line is
        not read blocked, nearest first (ruling P24-AL: finished before the Fight turns to a standing one). Ruling
        P24-AV (E10's a59: the stomp sent on a shove's `knockdown` before any frame read the target fallen was rejected
        `not valid`): only the frame's `onFloor` makes a zombie downed; with `knocked` the zombies a shove read knocked
        down within KNOCK_READ_S that no frame reads on the floor yet are listed instead (the finish waits for them)."""
        skip, now = self.blocked(), self.clock()
        out = []
        for zid, z in self.world.zombies.items():
            down = (not on_floor(z) and self.knocked.get(zid, -math.inf) > now) if knocked else on_floor(z)
            if (not target_id_ok(zid) or zid in skip or not down or z.get("x") is None or z.get("y") is None
                    or (self.only is not None and zid not in self.only)):
                continue
            d = zdist(self.world, z)
            if d <= FIGHT_REACH and line_to(self.world, z) is not False:
                out.append((d, repr(zid), zid, z))
        return [(zid, z, d) for d, _, zid, z in sorted(out, key=lambda e: e[:2])]

    def _finish(self):
        """Ruling P24-AL (finish the fallen; #4372-#4374), with P24-AH's stomp: the nearest downed zombie within
        FIGHT_REACH takes, in order, the shove of a standing zombie at point blank first (POINT_BLANK_R, within the
        Lua's SHOVE_R: the engine would shove it anyway), else the `stomp` (the Lua walks to under 0.5 tiles; never
        with another standing zombie within STAND_MIN_R, the stomp's refusal), else the weapon's floor strike (an
        `attack` of the downed zombie, its damage times 5 or more: #4374) when the stomp is refused or not announced;
        `(command,)`, the command None in a hit reaction (the engine starts no swing: #4292); None with no downed
        zombie."""
        downed = self._downed()
        if not downed:
            return self._knock_wait()
        zid, z, d = downed[0]
        self.why = {"target": self.target, "pinned": self.target is not None, "dist": d, "downed": zid}
        hit = hit_reaction(self.world)
        if hit is not None:
            self.why["hitReaction"] = hit
            return (None,)
        s = self._standing_near(POINT_BLANK_R, (zid,))
        if (s is not None and not self._shoved and target_id_ok(s[0]) and s[2] <= SHOVE_R
                and self._swing_ok("shove", s[0])):
            self.why.update({"shove": "first", "shoveTarget": s[0], "shoveDist": s[2]})
            return (Shove(s[0]),)
        if self._swing_ok("stomp", zid) and self._standing_near(STAND_MIN_R, (zid,)) is None:
            self.why["stomp"] = True
            return (Stomp(zid),)
        if self.no_swing():   # P24-AP, R2: the floor strike is a swing, divided by the arms' pain: the backpedal
            return (self._wounded_leg(zid, z, d),)
        self.why["floor"] = True   # the stomp refused (or not announced): the weapon's floor strike
        self._held_before = False
        return (Attack(zid),)

    def _knock_wait(self):
        """Ruling P24-AV: a zombie a shove knocked down within KNOCK_READ_S (its `knockdown` read at the hit), within
        FIGHT_REACH on a line not read blocked, that no frame reads `onFloor` yet: the Fight sends nothing (`(None,)`,
        logged `knocked`) until the first frame reads it fallen (the stomp then) or KNOCK_READ_S passes (read standing
        again), unless another standing zombie is within KEEP_R (the Fight answers it as before the wait: Task 36
        fix 1, minor 1); else None."""
        k = self._downed(knocked=True)
        if not k:
            return None
        if self._standing_near(KEEP_R, [e[0] for e in k]) is not None:
            return None   # Task 36 fix 1, minor 1: a standing zombie at point blank is the Fight's to answer, not waited past
        zid, _, d = k[0]
        self.why = {"target": self.target, "pinned": self.target is not None, "dist": d, "knocked": zid}
        return (None,)
