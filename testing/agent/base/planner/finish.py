"""The finish of the fallen and the stomp: the mixins `ThreatFinish` (`threat.Threat`'s: ruling P24-AQ, the
`many` flee's finishing stomp, its end and its chaser, P24-AV; ruling P27-A's widening to the `strain` and `pair` flees
and to any fallen zombie, `_fallen_wide`) and `FightFinish` (`fight.Fight`'s: ruling P24-AL's
finish, the downed read and P24-AV's stomp wait on a shove's knock-down, P25-B's stomp first and P25-J's reach to
FINISH_R; and `ThreatFinish`'s P25-J yield of the `pair` flee, `_pair_finish`, and since Task 8 fix 1 the `pair`
flee's own finish, `_pair_flee_finish`: one rule, `finish_rule`, which the Fight's finish reads too). Moved out of
`threat.py` and `fight.py` at Plan 25 Task 2 (a pure move: every rule and constant unchanged; the constants in
`policies.py`'s table); the state is `Survive`'s and the `Fight`'s own, and `survive.py`'s and `fight.py`'s module
docstrings stay the record.
"""
import math

from agent.base.planner.policies import (DANGER_R, FIGHT_REACH, FINISH_CLEAR_R, FINISH_R, KEEP_R, POINT_BLANK_R,
                                         PREEMPTED, SHOVE_R, STAND_MIN_R, UNREACHABLE_S, arms_hurt, blocked, chasing,
                                         hit_reaction, line_to, on_floor, running, standing, target_id_ok, zdist)
from agent.base.pza1 import Attack, Shove, Stomp

FLEE_FINISH_REASONS = ("strain", "pair", "many")   # the flee reasons whose episode takes the finish (P27-A)


def finish_chaser(world, zid, dead, radius=KEEP_R):
    """The deferred minor 5 of review-t32-fix1: (id, tiles) of the nearest standing (not `on_floor`) zombie chasing
    (`hasTarget`) within `radius` (KEEP_R; FINISH_CLEAR_R for the flee's finish under P27-A) of the fallen target
    `zid`, the ids in `dead` and the target left out, else None: the stomp's walk to the target would end at it (the
    flee's finish, P24-AV, and the Fight's stomp first, P25-B)."""
    t = world.zombies[zid]
    best = None
    for oid, o in world.zombies.items():
        if oid == zid or oid in dead or on_floor(o) or not chasing(o) or o.get("x") is None or o.get("y") is None:
            continue
        d = math.hypot(o["x"] - t["x"], o["y"] - t["y"])
        if d <= radius and (best is None or (d, repr(oid)) < (best[1], repr(best[0]))):
            best = (oid, d)
    return best


def downed_list(world, skip, knocked, now, reach, knock=False, only=None):
    """(id, zombie, dist) of each downed zombie a Fight may target (`target_id_ok`, not in `skip`, in `only` when it is
    set) within `reach` whose line is not read blocked, nearest first (ruling P24-AL). Ruling P24-AV (E10's a59: the
    stomp sent on a shove's `knockdown` before any frame read the target fallen was rejected `not valid`): only the
    frame's `onFloor` makes a zombie downed; with `knock` the zombies a shove read knocked down (`knocked`: id -> wall
    until KNOCK_READ_S ends) that no frame reads on the floor yet are listed instead (the finish waits for them)."""
    out = []
    for zid, z in world.zombies.items():
        down = (not on_floor(z) and knocked.get(zid, -math.inf) > now) if knock else on_floor(z)
        if (not target_id_ok(zid) or zid in skip or not down or z.get("x") is None or z.get("y") is None
                or (only is not None and zid not in only)):
            continue
        d = zdist(world, z)
        if d <= reach and line_to(world, z) is not False:
            out.append((d, repr(zid), zid, z))
    return [(zid, z, d) for d, _, zid, z in sorted(out, key=lambda e: e[:2])]


def finish_rule(world, skip, dead, knocked, now, swing_ok, knock=False, only=None, post=None, strike_reach=0.0):
    """Ruling P25-J (3) as amended at Task 8 fix 1: the one finish rule, which the Fight's finish (`_finishable`: its
    `_finish`, its knock wait and its legs' give-way) and the threat's (`ThreatFinish._pair_finish` before a `pair` flee
    is chosen, `_pair_flee_finish` inside a running one) both call. With a standing zombie within KEEP_R of the player
    (neither `onFloor`, nor in a knock window of `knocked`, nor read dead) the rule is silent: None. Else the zombies
    downed (`downed_list`: `onFloor`, or with `knock` a shove's knock-down within KNOCK_READ_S no frame reads fallen
    yet) within FINISH_R on a line not read blocked whose stomp goes, nearest first: `swing_ok("stomp", id)` (announced
    and not refused at it, by the caller's own record of refusals), no standing chaser within KEEP_R of it
    (`finish_chaser`, P25-B's guard) and `post(z)` (the doorway stand's post, `Doorway._finish_post`); a zombie within
    `strike_reach` is kept whatever its stomp reads (the Fight's FIGHT_REACH: its floor strike follows a refused stomp;
    the `pair` yield's 0: the stomp alone)."""
    hot = {zid for zid, until in knocked.items() if until > now}
    if standing(world, KEEP_R, dead | hot):
        return None
    out = downed_list(world, skip, knocked, now, FINISH_R, knock, only)
    return [(zid, z, d) for zid, z, d in out if d <= strike_reach or (
        swing_ok("stomp", zid) and finish_chaser(world, zid, dead) is None and (post is None or post(z)))]


class ThreatFinish:
    """The flee's finish (the module docstring): `Threat`'s mixin."""

    def _flee_finish(self, reason):
        """Ruling P24-AQ, the fallen target under `many` (E9: the two targets its swings struck, 7488 and 7474, read
        fallen while the `many` flee ran the character away from them, neither stomped): in a flee episode whose reason
        was `many`, a zombie the planner struck (an attack or a shove sent at it within UNREACHABLE_S, `struck`) that
        reads downed (`onFloor`: ruling P24-AV, the first frame reading it fallen, never a shove's knock-down alone)
        within FINISH_R (the stomp's own walk in; fix 1, the review's major 5) on a line not read blocked, with no
        standing zombie within DANGER_R (the next standing one beyond it), takes one `Stomp` before the flee resumes, or
        the weapon's floor strike (an `Attack` of it, only within FIGHT_REACH) when the stomp is not announced, would
        be refused (a standing zombie within STAND_MIN_R) or ended refused; never the floor strike at `body.armPain`
        STRAIN_HARD, under any hold (P24-AP and R2: a swing) nor unarmed (P25-P, `_unarmed`). Sent as the Flee's own
        action (its leg superseded, the steer resumed on the next tick, as `_flee_drop`); one stomp and at most one
        floor strike a zombie (`finishing`); none in a hit reaction. With a standing zombie within
        DANGER_R the flee runs as today. Its end is read by `_finish_end` (a `targetDead` is a kill). Logged `finish`.
        Ruling P24-AV: a stomp that failed `stood` (the target rose) reads the target again on the next tick: standing
        within DANGER_R the flee runs (no finish); fallen again, one more stomp (`kind` "stomp2"), and that one failed
        `stood` or refused, the floor strike. The deferred minor 5 of review-t32-fix1 (E9's line 334: the 4.62-tile
        stomp walk toward 7474 headed at 7479, standing and chasing 2.16 tiles from it): a chasing standing zombie
        within KEEP_R of the target refuses the finish (`_finish_chaser`, logged `finish_block`). A tick whose reason is
        `pair` outside a `many` episode takes the `pair` flee's own finish instead (`_pair_flee_finish`, P25-J (3) as
        amended at Task 8 fix 1).
        Ruling P27-A (`FLEE_FINISH`; E18, `e_day_18-20261102-224036`: line 1649's `strain` flee ran from 30744, knocked
        down 2.5339841792960844 tiles off with no standing zombie within DANGER_R, and line 939's `many` flee from
        30452, fallen off its window climb 2.053499872133796 off and never struck; neither was stomped): the finish
        runs in a flee episode whose reason is `strain` (any hold kind) or `pair` as well as `many`
        (FLEE_FINISH_REASONS; the `health` flee keeps none: a stomp at FLEE_HEALTH is the fall the guides warn of), on
        any zombie the frame reads `onFloor` (`downed_list`'s read, P24-AV) within FINISH_R on a line not read blocked,
        the struck test dropped (`_fallen_wide`); its clearance is no standing zombie within FINISH_CLEAR_R of the
        character (`_within`, the fallen left out) and no standing chaser within FINISH_CLEAR_R of the fallen one
        (`finish_chaser`), in place of DANGER_R and KEEP_R. The sends, their refusals and ends are P24-AQ's (one stomp a
        zombie, `finishing`; no floor strike under a hold, R2, nor unarmed), a stomp the replaced Fight saw refused
        within SWING_SKIP_S read as refused (as `_flee_stomp_ok` reads it). Logged `flee_finish` {reason, struck (sent
        at within UNREACHABLE_S), clear (the nearest listed standing zombie's tiles, else None)} beside `finish`, and
        `pair_yield` under the `pair` flee (the `pair` flee's own finish's why)."""
        self.finish_block = None
        if self._finish_a is not None and running(self.actions, self._finish_a):
            return None
        wide = self.FLEE_FINISH and (self.flee_many or reason in FLEE_FINISH_REASONS)
        if not wide and reason == "pair" and not self.flee_many:
            return self._pair_flee_finish()
        if not (wide or self.flee_many or reason == "many"):
            return None
        now = self.clock()
        dead = blocked(self.dead, now)
        if (self.world.me or {}).get("hitReaction"):
            return None
        best = self._fallen_wide(dead, now) if wide else self._fallen_struck(dead, now)
        if best is None:
            return None
        zid, d = best
        chaser = self._finish_chaser(zid, dead, FINISH_CLEAR_R if wide else KEEP_R)
        if chaser is not None:
            self.finish_block = {"target": zid, "chaser": chaser[0], "dist": chaser[1]}
            return None
        done, end = self.finishing.get(zid), self._finish_end_read(zid)
        again = done == "stomp" and end == "stood"   # P24-AV: fallen again after a `stood`: one more stomp
        refused = wide and self.fight_refused.get(("stomp", zid), -math.inf) > now
        if ((done is None or again) and self.world.can("stomp") and not refused
                and not standing(self.world, STAND_MIN_R, dead | {zid})):
            cmd, kind = Stomp(zid), ("stomp" if done is None else "stomp2")
        elif done in ("stomp", "stomp2") and end is None:
            return None   # the stomp went (or runs) and was not refused: the one finish is spent
        elif arms_hurt(self.world) or self._fight_spent() or self._unarmed():
            self.finishing[zid] = "floor"   # P24-AP, R2, P25-P: no floor strike (a swing) at STRAIN_HARD, under a hold
                                            # or with no weapon held
            return None
        elif d > FIGHT_REACH:
            return None   # the floor strike swings from where the player stands: only within FIGHT_REACH
        else:
            cmd, kind = Attack(zid), "floor"
        self.finishing[zid] = kind
        self.why = {"finish": zid, "kind": kind, "dist": d}
        if wide:
            self.why["flee_finish"] = {"reason": reason if reason in FLEE_FINISH_REASONS else "many",
                                       "struck": now - self.struck.get(zid, -math.inf) <= UNREACHABLE_S,
                                       "clear": self._nearest_standing(dead)}
            if reason == "pair":
                self.pair_yield = zid
        return self.flee, cmd

    def _fallen_struck(self, dead, now):
        """P24-AQ's candidate: (id, tiles) of the nearest zombie struck within UNREACHABLE_S that reads `onFloor`
        within FINISH_R on a line not read blocked, its floor strike not spent, with no standing zombie within DANGER_R;
        else None."""
        if standing(self.world, DANGER_R, dead):
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
        return None if best is None else (best[1], best[0][0])

    def _fallen_wide(self, dead, now):
        """P27-A's candidate: (id, tiles) of the nearest zombie `downed_list` reads (`onFloor`, within FINISH_R, a line
        not read blocked, one read dead left out) whose floor strike is not spent, with no standing zombie within
        FINISH_CLEAR_R of the character (`_within`, the fallen left out); else None."""
        if any(not on_floor(z) for z in self._within(FINISH_CLEAR_R)):
            return None
        for zid, _, d in downed_list(self.world, dead, {}, now, FINISH_R):
            if self.finishing.get(zid) != "floor":
                return zid, d
        return None

    def _nearest_standing(self, dead):
        """The tiles to the nearest listed standing zombie (not `on_floor`, not read dead), else None (P27-A's
        `clear`)."""
        ds = [zdist(self.world, z) for zid, z in self.world.zombies.items() if zid not in dead and not on_floor(z)
              and z.get("x") is not None and z.get("y") is not None]
        return min(ds) if ds else None

    def _pair_finish(self):
        """Ruling P25-J (3) as amended at Task 8 fix 1, consulted before a `pair` flee is chosen (E12, #4435: the
        knocked-down zombies first read fallen 2.12 to 2.73 tiles off, and the `pair` flee ran the character from three
        of the five knock-downs; a86 and a69 came on the ticks before the first frame read them fallen): with
        `FINISH_FAR` on and no flee episode running (inside one the flee's own finish consults the rule,
        `_pair_flee_finish`), the id of the nearest zombie `finish_rule` lists for a stomp, the fallen first, then those
        in the knock window; read with the running Fight's own state (its skips, `only`, refusals, post and knock
        window), so the Fight's finish answers it (its knock wait, then its stomp on the first frame reading it fallen),
        or with no Fight running the threat's (a new Fight's finish answers it); None when the rule is silent."""
        if not self.FINISH_FAR or self.mode == "flee":
            return None
        now = self.clock()
        dead = blocked(self.dead, now)
        f = self.fight if self.mode == "fight" else None
        if f is not None:
            state, extra = (f.blocked(), dead, f.knocked, now, f._swing_ok), {"only": f.only, "post": f._finish_post}
        else:
            state, extra = (self._skipped(), dead, {}, now, lambda kind, zid: self.world.can(kind)), {}
        for knock in (False, True):
            out = finish_rule(self.world, *state, knock=knock, **extra)
            if out is None:
                return None
            if out:
                return out[0][0]
        return None

    def _pair_flee_finish(self):
        """Ruling P25-J (3) as amended at Task 8 fix 1, inside a running `pair` flee episode (P24-AQ's finish extended
        to `pair`, under the rule's guards): each tick, with `FINISH_FAR` on and no hit reaction, the nearest zombie
        read `onFloor` that `finish_rule` lists for a stomp (the flee keeps no knock window: the stomp goes on the frame
        reading it fallen) takes one `Stomp`, sent as the Flee's own action (its leg superseded, the steer resumed on
        the next tick), and, failed `stood` and fallen again, one more (`stomp2`, P24-AV). The flee's refusals are its
        own (`_flee_stomp_ok`): a stomp at the zombie that went or runs, or ended refused (the Lua's `not valid`,
        STAND_MIN_R), leaves the rule silent at it and the flee runs; no floor strike (the `pair` finish is the stomp
        alone). Logged `finish` {kind, dist} with `pair_yield`; its end read by `_finish_end` (a `targetDead` is a
        kill)."""
        if not self.FINISH_FAR or (self.world.me or {}).get("hitReaction"):
            return None
        now = self.clock()
        out = finish_rule(self.world, self._skipped(), blocked(self.dead, now), {}, now, self._flee_stomp_ok)
        if not out:
            return None
        zid, _, d = out[0]
        kind = "stomp" if self.finishing.get(zid) is None else "stomp2"
        self.finishing[zid] = kind
        self.pair_yield = zid
        self.why = {"finish": zid, "kind": kind, "dist": d}
        return self.flee, Stomp(zid)

    def _flee_stomp_ok(self, kind, zid):
        """The flee's finish may send `kind` (the stomp) at `zid`: the build announces it, the Fight the flee replaced
        did not refuse it there within SWING_SKIP_S (`fight_refused`), and the flee sent none at it yet, or its one
        stomp failed `stood` (P24-AV: fallen again, one more)."""
        if not self.world.can(kind) or self.fight_refused.get((kind, zid), -math.inf) > self.clock():
            return False
        done = self.finishing.get(zid)
        return done is None or (done == "stomp" and self._finish_end_read(zid) == "stood")

    def _finish_chaser(self, zid, dead, radius=KEEP_R):
        """`finish_chaser` over the World within `radius` (the flee's finish, P24-AV; FINISH_CLEAR_R under P27-A)."""
        return finish_chaser(self.world, zid, dead, radius)

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
        """`downed_list` within FIGHT_REACH over the Fight's own skips (`blocked`), knock window and `only`: the downed
        it finishes with a standing zombie within KEEP_R or the `finish_far` rule off (ruling P24-AL: finished before
        the Fight turns to a standing one)."""
        return downed_list(self.world, self.blocked(), self.knocked, self.clock(), FIGHT_REACH, knocked, self.only)

    def _finish_post(self, z):
        """P25-J (2): the stomp's walk to `z` keeps the Fight where it fights (the open-ground Fight: anywhere; the
        doorway stand bounds it by its post, `Doorway._finish_post`)."""
        return True

    def _finishable(self, knocked=False):
        """What the finish, the knock wait and a running leg's give-way read (with `knocked`, the knock window's).
        Ruling P25-J (E12, #4435: every knocked-down zombie first read fallen 2.12 to 2.73 tiles off, beyond
        FIGHT_REACH, and with a standing one in reach nothing stomped it): with the `finish_far` rule on, the one finish
        rule (`finish_rule`, the threat's `pair` yield and the `pair` flee's finish read it too) over the Fight's own
        skips, knock window, `only`, refusals (`_swing_ok`) and post (`_finish_post`), a zombie within FIGHT_REACH kept
        whatever its stomp reads (the floor strike follows a refused stomp): the downed out to FINISH_R (the stomp's own
        walk covers the distance: the Lua walks to under 0.5 tiles), the far one only where its stomp goes; with a
        standing zombie within KEEP_R (the rule silent: it is fought first, at point blank its shove first, as P24-AL)
        or the rule off, `_downed` within FIGHT_REACH."""
        if "finish_far" in self.rules:
            now = self.clock()
            out = finish_rule(self.world, self.blocked(), blocked(self.dead, now), self.knocked, now, self._swing_ok,
                              knocked, self.only, self._finish_post, FIGHT_REACH)
            if out is not None:
                return out
        return self._downed(knocked)

    def _finish(self):
        """Ruling P24-AL (finish the fallen; #4372-#4374), with P24-AH's stomp: the nearest downed zombie within
        FIGHT_REACH takes, in order, the shove of a standing zombie at point blank first (POINT_BLANK_R, within the
        Lua's SHOVE_R: the engine would shove it anyway), else the `stomp` (the Lua walks to under 0.5 tiles; never
        with another standing zombie within STAND_MIN_R, the stomp's refusal), else the weapon's floor strike (an
        `attack` of the downed zombie, its damage times 5 or more: #4374) when the stomp is refused or not announced;
        `(command,)`, the command None in a hit reaction (the engine starts no swing: #4292); None with no downed
        zombie. Ruling P25-J: the downed are read through `_finishable` (`finish_rule`): FINISH_R with no standing
        zombie within KEEP_R, the far one taken only where its stomp goes."""
        downed = self._finishable()
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

    def _drifted_finish(self):
        """Ruling P25-J (3) as amended at Task 8 fix 1 (E12's a86: the walk corner's shove knocked its pin to 1.8
        tiles, beyond CORNERED_R, and no frame read it fallen yet): with the `finish_far` rule on, a cornered Fight
        (`point_blank`) whose pin drifted beyond CORNERED_R still consults the finish before it holds `out_of_reach`
        (its knock wait, then its stomp on the first frame reading the zombie fallen), the ride's wait (P25-D) first as
        before any send; else None."""
        if "finish_far" not in self.rules or self._ride_waits():
            return None
        return self._finish()

    def _knock_wait(self):
        """Ruling P24-AV: a zombie a shove knocked down within KNOCK_READ_S (its `knockdown` read at the hit), within
        FIGHT_REACH on a line not read blocked, that no frame reads `onFloor` yet: the Fight sends nothing (`(None,)`,
        logged `knocked`) until the first frame reads it fallen (the stomp then) or KNOCK_READ_S passes (read standing
        again), unless another standing zombie is within KEEP_R (the Fight answers it as before the wait: Task 36
        fix 1, minor 1); else None."""
        k = self._finishable(knocked=True)
        if not k:
            return None
        if self._standing_near(KEEP_R, [e[0] for e in k]) is not None:
            return None   # Task 36 fix 1, minor 1: a standing zombie at point blank is the Fight's to answer, not waited past
        zid, _, d = k[0]
        self.why = {"target": self.target, "pinned": self.target is not None, "dist": d, "knocked": zid}
        return (None,)

    def _finish_pick(self):
        """Ruling P25-B: (id, dist) of the nearest zombie read `onFloor` within FINISH_R on a line not read blocked that
        the stomp may take (announced, not refused at it, no standing zombie within STAND_MIN_R of the player, no
        standing chaser within KEEP_R of it: `finish.finish_chaser`, the flee finish's guard), else None. With the
        `finish_far` rule on it refuses while a standing zombie is within KEEP_R (P25-J: it is fought first), and with
        none there the finish (`_finishable`) has already listed every zombie it would pick, so its pick answers only
        `_finish_gives_way` (`_finish_first`'s stomp is never reached: its docstring)."""
        if "finish_first" not in self.rules or not self.world.can("stomp") or hit_reaction(self.world) is not None:
            return None
        if "finish_far" in self.rules and self._standing_near(KEEP_R) is not None:
            return None   # P25-J: a standing zombie within KEEP_R is fought first, the downed waits
        skip = self.blocked()
        dead = blocked(self.dead, self.clock())
        best = None
        for zid, z in self.world.zombies.items():
            if (not target_id_ok(zid) or zid in skip or not on_floor(z) or z.get("x") is None or z.get("y") is None
                    or (self.only is not None and zid not in self.only)):
                continue
            d = zdist(self.world, z)
            if (d > FINISH_R or line_to(self.world, z) is False or not self._swing_ok("stomp", zid)
                    or self._standing_near(STAND_MIN_R, (zid,)) is not None
                    or finish_chaser(self.world, zid, dead) is not None):
                continue
            if best is None or (d, repr(zid)) < (best[1], repr(best[0])):
                best = (zid, d)
        return best

    def _finish_gives_way(self):
        """P25-B (E11's third target lay fallen 4.3 s under an attack running to `out of reach`, #4405): a running
        walk, or a running attack whose target reads fallen or beyond FIGHT_REACH, gives way to `_finish_pick`."""
        if self._finish_pick() is None:
            return False
        if self.last.type != "attack":
            return True
        t = self.world.zombies.get(self.last.args.get("targetId"))
        return t is None or t.get("x") is None or on_floor(t) or zdist(self.world, t) > FIGHT_REACH

    def _finish_first(self, d):
        """Ruling P25-B: with the target `d` tiles off beyond FIGHT_REACH (the Fight would walk, step or wait toward a
        standing one), the stomp of `_finish_pick`'s zombie first (its walk in, the Lua's), logged `finish_first`
        {target, dist}; else None. With the `finish_far` rule on (P25-J) its stomp is never reached: a standing zombie
        within KEEP_R makes `_finish_pick` refuse, and with none there the finish's own `downed` step (`_finish`,
        ahead of it in `_choose`) has already taken every zombie `_finish_pick` would name, so the `downed` why
        supersedes `finish_first`. It stays the rule with FINISH_FAR off (`pre_t4`), which is why P25-B's tests pin it
        with that switch off (`test_survive_t`, Task 8's named change)."""
        if d <= FIGHT_REACH:
            return None
        pick = self._finish_pick()
        if pick is None:
            return None
        self.why = {"target": self.target, "pinned": self.target is not None, "dist": d,
                    "finish_first": {"target": pick[0], "dist": pick[1]}}
        return Stomp(pick[0])
