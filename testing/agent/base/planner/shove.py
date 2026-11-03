"""The shove at the swing and the corner after a missed shove: the mixin `FightShove` (`fight.Fight`'s: rulings P24-AG
and P24-AH's shove, P25-A's corner, P25-I's logged third branch, P25-L's break after repeated misses, P26-L1's
divided swing after them under the `wounded` reason, `_wounded_swing`, and P27-E's full swing after them in the low
fight, `_low_swing`). Moved out of
`fight.py` at Plan 25 Task 8 (`_shove`, `_shove_missed` and `_corner` whole, their rules unchanged; the constants in
`policies.py`'s table); the state is the `Fight`'s own, and `fight.py`'s module docstring stays the record.
"""
import math

from agent.base.planner.policies import (DANGER_R, FIGHT_REACH, FLEE_GAIT, FLEE_S, INSIDE_CROWD_N, KEEP_R,
                                         POINT_BLANK_R, SHOVE_BREAK_N, SHOVE_FAIL_N, SHOVE_R, SHOVE_REPEAT_S,
                                         STAND_MIN_R, STRAIN_SOFT, arm_pain, arms_hurt, blocked, on_floor,
                                         target_id_ok, zdist)
from agent.base.pza1 import Attack, Shove, Steer
from agent.base.world import me_xy


class FightShove:
    """The shove and the corner (the module docstring): `Fight`'s mixin."""

    def _shove(self, zid, z, d):
        """The shove sent instead of the next swing at the standing target `zid` (`d` tiles off, within reach), else
        None (the build must announce `shove`; never with another standing zombie within STAND_MIN_R of the player
        than the one shoved):
        - ruling P24-AG: `arm_pain` at or above STRAIN_SOFT (the swing's damage divided by armPain / 10, #4370), or
          any hold (`spent`, ruling R2), and the target at point blank (POINT_BLANK_R): the shove, which strains the
          arms about a third less than a bat's swing and knocks down 35 + 2 x Strength in 100 (#4373), every time
          (logged `shove` "strain", or "spent" for a hold with the pain under STRAIN_SOFT); rulings P25-P and P25-S:
          a shove-and-stomp Fight (`shove_only`), the same shove at point blank whatever the pain, logged `shove`
          "unarmed" or "low"; ruling P26-L1: at point blank under the `wounded` reason after SHOVE_FAIL_N misses at a
          lone target, the swing in the shove's place (`_wounded_swing`), before the corner's reads;
        - ruling P24-AH: in a standing fight (`standing`), a second standing zombie inside KEEP_R: the nearer of the
          two is shoved (within the Lua's SHOVE_R) before the next swing, once a swing (`_shoved`)."""
        low = self._low_swing(zid)   # P27-E: the low fight's full swing after the failed shoves, within FIGHT_REACH
        if low is not None:
            return low
        if not self.world.can("shove"):
            return None
        pain = arm_pain(self.world)
        sore = pain is not None and pain >= STRAIN_SOFT
        blank = (sore or self.spent or self.shove_only) and d <= POINT_BLANK_R
        swing = self._wounded_swing(zid, z) if blank else None   # P26-L1: the divided swing after the failed shoves
        if swing is not None:
            return swing
        if blank and "corner_break" in self.rules and self._shove_missed(zid):
            corner = self._corner(zid, z, sore)   # P25-A: the break or the undivided swing, else the shove again
            if corner is not None:
                return corner
        elif blank and "shove_break_run" in self.rules and self._miss_run.get(zid):
            brk = self._run_break(zid, z, sore)   # P25-T: a miss on record at any spacing consults the breaks
            if brk is not None:
                return brk
        if blank and self._swing_ok("shove", zid) and self._standing_near(STAND_MIN_R, (zid,)) is None:
            self.why.update({"shove": self.shove_only or ("strain" if sore else "spent"), "strain": pain})
            return Shove(zid)
        if not self.standing() or self._shoved:
            return None
        second = self._standing_near(KEEP_R, (zid,))
        if second is None:
            return None
        sid, _, sd = min(((zid, z, d), second), key=lambda p: (p[2], repr(p[0])))
        if (not target_id_ok(sid) or sd > SHOVE_R or not self._swing_ok("shove", sid)
                or self._standing_near(STAND_MIN_R, (sid,)) is not None):
            return None
        self.why.update({"shove": "second", "shoveTarget": sid, "shoveDist": sd, "second": second[0]})
        return Shove(sid)

    def _wounded_swing(self, zid, z):
        """Ruling P26-L1 (F8, `f_goals_9-20261102-181937`: its last fight's one standing zombie, 28762, health
        1.1920000314712524 on every frame listing it, took six shoves, each done with its swing started and `knockdown`
        false, two lone breaks between, and no swing, the arms' pain 58.1 to 119.1 from the first wound) amends P25-I
        (`_corner`'s divided swing not taken, logged `corner` {kind shove}: review-t3 finding 1, the swing at 1/3.8 to
        1/27 of its damage, #4370, the shove's knock-down a crit roll pain does not touch, #4373, the stomp outside the
        divider, #4374) and P24-AP's no swing at STRAIN_HARD (`no_swing`) for one case: a lone standing zombie that
        resisted SHOVE_FAIL_N shoves takes the divided swing. With the `wounded_swing` rule on (`WOUNDED_SWING`), a
        Fight under the `wounded` reason alone (`arms_hurt`; no hold, `spent`, and no shove-and-stomp Fight,
        `shove_only`, whose fights take no swing by their own rulings) swings at its standing target `zid` (`z`) at
        point blank, in the shove's place, once SHOVE_FAIL_N or more missed shoves at it are on record (`_missed_n`,
        P25-T's count: a swing clears none, so it keeps swinging while the target stands) and no other zombie is listed
        within DANGER_R (`_alone`: a fallen one in reach is the finish's stomp, `_finish`, which goes first); read
        before the corner (P25-A, P25-I) and the breaks (P25-L, P25-T), so P25-L's lone break after the same count is
        not taken while the swing is, and a second zombie within DANGER_R gives the shove and the corner's reading back.
        Logged `wounded_swing` (the misses). Beyond point blank the backpedal holds as P24-AP's (`_wounded_leg`). Cost
        if wrong: a divided swing (a third to a twenty-seventh of its damage under heavy arm pain, #4370) spent where a
        shove might have knocked down. None otherwise."""
        if ("wounded_swing" not in self.rules or not arms_hurt(self.world) or self.spent
                or self.shove_only is not None or on_floor(z)):
            return None
        k = self._missed_n(zid)
        if k < SHOVE_FAIL_N or not self._alone(zid):
            return None
        self.why["wounded_swing"] = k
        self._held_before = False
        return Attack(zid)

    def _low_swing_due(self, zid=None):
        """Ruling P27-E (`LOW_SWING`; F8, `f_goals_9-20261102-181937`: its last fight shoved its lone 28762, health
        1.1920000314712524, six times, each done `knockdown` false, and never swung; the guides' notes § 2: one swing,
        then back off, then shove again): the low fight's full swing is due at `zid` (the pinned target by default): the
        `low_swing` rule on, the Fight's `shove_only` "low" (P25-S: not the unarmed nor the hold fight, which keep no
        swing), no hold read (`spent`) nor the arms' pain at STRAIN_HARD (`arms_hurt`: the swing is the full one), the
        target standing within FIGHT_REACH with SHOVE_FAIL_N or more missed shoves at it on record (`_missed_n`, P25-T's
        count) and no other zombie within DANGER_R (`_alone`). `no_swing` reads it (the swing's exception, so the
        wounded backpedal gives way to it within reach), and so does `_ride_waits` (a riding bandage still holds it)."""
        zid = self.target if zid is None else zid
        z = self.world.zombies.get(zid) if zid is not None else None
        if ("low_swing" not in self.rules or self.shove_only != "low" or self.spent or arms_hurt(self.world)
                or z is None or z.get("x") is None or z.get("y") is None or on_floor(z)):
            return False
        return zdist(self.world, z) <= FIGHT_REACH and self._missed_n(zid) >= SHOVE_FAIL_N and self._alone(zid)

    def _low_swing(self, zid):
        """Ruling P27-E's send (`_low_swing_due`): one `Attack` at `zid` from where the player stands, logged
        `low_swing` {target, missed}, the misses at it reset (`_misses`, `_miss_run`), so the next shove-and-stomp sends
        at it are the backpedal and the shove again until SHOVE_FAIL_N more miss; else None."""
        if not self._low_swing_due(zid):
            return None
        self.why["low_swing"] = {"target": zid, "missed": self._missed_n(zid)}
        self._misses = None
        self._miss_run.pop(zid, None)
        self._held_before = False
        return Attack(zid)

    def _alone(self, zid):
        """No zombie but `zid` listed with a position within DANGER_R of the player, one read dead aside (P26-L1)."""
        dead = blocked(self.dead, self.clock())
        return not any(oid != zid and oid not in dead and o.get("x") is not None and o.get("y") is not None
                       and zdist(self.world, o) <= DANGER_R for oid, o in self.world.zombies.items())

    def _crowd_shove(self, zid, d):
        """Ruling P26-C (E16, `e_day_16-20261102-125450`: from the doorway stand's `inside` end the corner sent five
        attacks, a105 to a109, at zombies within 1.0472329509892702 tiles, four of which swung and one lowered its
        target, while two zombies stood on the door's inside square): an `inside` corner's Fight whose `crowd`
        (Survive's count at point blank) reads INSIDE_CROWD_N or more sends the shove at its target `zid` in place of
        the swing, every time: its knock-down's chance (#4373), read as every shove's result is (`knocked`, then the
        finish's stomp); the stomp of a fallen zombie in reach has gone first (`_finish`). Logged `shove` "crowd". None
        with no crowd, with `zid` not a wire id or beyond SHOVE_R (`d` tiles off: the Lua refuses a shove `too far`,
        ruling P26-7a; the crowd may be `me.attackers` alone, the target up to FIGHT_REACH), or with the shove at `zid`
        refused within SWING_SKIP_S (`_swing_ok`): the swing then stands."""
        if (self.crowd is None or self.crowd < INSIDE_CROWD_N or not target_id_ok(zid) or d > SHOVE_R
                or not self._swing_ok("shove", zid)):
            return None
        self.why["shove"] = "crowd"
        return Shove(zid)

    def _shove_missed(self, zid):
        """Ruling P25-A: the last shove at `zid`, sent within SHOVE_REPEAT_S, ended done with its swing started and
        `knockdown` false (E11's six such shoves at its two cornered zombies, #4406)."""
        a = self._shove_a.get(zid)
        if a is None or self.clock() - a.sent_wall >= SHOVE_REPEAT_S or not self.actions.done(a) or a.state != "done":
            return False
        res = a.result if isinstance(a.result, dict) else {}
        return res.get("knockdown") is False and res.get("attackStarted") is not False

    def _note_shove_end(self, a, res):
        """Ruling P25-L's count, at a shove's end read done with its swing started (`_observe_swing`): `knockdown` false
        appends its send wall to the run of misses at its target (`_misses`: a run at another target starts anew),
        `knockdown` true ends the run. Ruling P25-T's count beside it: `knockdown` false adds one to its target's
        misses over the Fight's life (`_miss_run`, whatever the spacing and whatever other target was shoved between),
        `knockdown` true at that target clears them."""
        zid = a.args.get("targetId")
        if res.get("knockdown") is True:
            self._misses = None
            self._miss_run.pop(zid, None)
            return
        if res.get("knockdown") is not False:
            return
        run = self._misses if self._misses is not None and self._misses[0] == zid else (zid, [])
        self._misses = (zid, run[1] + [a.sent_wall])
        self._miss_run[zid] = self._miss_run.get(zid, 0) + 1

    def _missed_n(self, zid):
        """P25-L: the missed shoves in a row at `zid` sent within SHOVE_BREAK_N x SHOVE_REPEAT_S of now; with the
        `shove_break_run` rule on (ruling P25-T, E13's fight 18: eight shoves at one zombie over 28.5 s, the backpedal
        spacing them past SHOVE_REPEAT_S, so neither the window nor the corner ever read a run), its misses over the
        Fight's life since the last knock-down at it (`_miss_run`)."""
        if "shove_break_run" in self.rules:
            return self._miss_run.get(zid, 0)
        if self._misses is None or self._misses[0] != zid:
            return 0
        now = self.clock()
        return sum(1 for w in self._misses[1] if now - w < SHOVE_BREAK_N * SHOVE_REPEAT_S)

    def _away(self, z):
        """The unit heading from zombie `z` to the player, else None (on its square)."""
        mx, my = me_xy(self.world)
        dx, dy = mx - z["x"], my - z["y"]
        dd = math.hypot(dx, dy)
        return None if dd <= 0.0 else (dx / dd, dy / dd)

    def _pair_break(self, zid, z, n):
        """Ruling P25-A's two-zombie break (`_corner`): with `n` (two or more) standing zombies within FIGHT_REACH, the
        steer at a run through the gap the shove opened (the heading away from `zid`, turned to the first heading
        `clear_heading` passes), logged `corner` {kind "break", shoved, n}; else None."""
        u = self._away(z) if n >= 2 else None
        v = self._clear_turn(u) if u is not None else None
        if v is None:
            return None
        self.why["corner"] = {"kind": "break", "shoved": zid, "n": n}
        return Steer(v[0], v[1], FLEE_S, FLEE_GAIT)

    def _run_break(self, zid, z, sore):
        """Ruling P25-T (E13's fight 18: eight shoves at one zombie over 28.5 s, the backpedal between the shoves of a
        Fight that sends no swing spacing every one past SHOVE_REPEAT_S, so `_shove_missed` never read the last miss
        and the corner was never consulted): a shove at `zid` with a miss on record outside the window consults the
        breaks the same spacing defeated, the two-zombie break (`_pair_break`, the `corner_break` rule on) and, where
        the swing is divided or not taken (`_divided`), the lone break on the misses over the Fight's life
        (`_lone_break`); never the corner's swing (it keeps the window). None when neither breaks: the shove goes,
        with no `corner` why."""
        n = len(self._standing(FIGHT_REACH))
        brk = self._pair_break(zid, z, n) if "corner_break" in self.rules else None
        if brk is None and self._divided(sore):
            brk = self._lone_break(zid, z, n)
        return brk

    def _divided(self, sore):
        """The swing is divided (`sore`: the arms' pain at STRAIN_SOFT or above; the endurance or the tired hold) or
        not taken at all (`shove_only`, P25-P and P25-S): the lone target would be shoved again (`_corner`)."""
        return bool(sore or self.shove_only or "endurance" in self.spent or "tired" in self.spent)

    def _lone_break(self, zid, z, n):
        """Ruling P25-L's break (`_corner`), and P25-T's on a shove at a target with a miss on record outside the
        window: with the `shove_break` rule on, no doorway stand, fewer than two standing zombies within FIGHT_REACH
        (`n`) and SHOVE_BREAK_N or more misses at `zid` (`_missed_n`), the steer at a run away from it turned to the
        first heading `clear_heading` passes, logged `corner` {kind "break", shoved, n, misses}, its counts reset; else
        None."""
        if "shove_break" not in self.rules or self.doorway is not None or n >= 2:
            return None
        k = self._missed_n(zid)
        u = self._away(z) if k >= SHOVE_BREAK_N else None
        v = self._clear_turn(u) if u is not None else None
        if v is None:
            return None
        self._misses = None
        self._miss_run.pop(zid, None)
        self.why["corner"] = {"kind": "break", "shoved": zid, "n": n, "misses": k}
        return Steer(v[0], v[1], FLEE_S, FLEE_GAIT)

    def _corner(self, zid, z, sore):
        """Ruling P25-A, the corner under any hold (E11: seven shoves at two zombies at point blank, none knocking
        down, no swing, #4406): after a missed shove at `zid` (`_shove_missed`), with two or more standing zombies
        within FIGHT_REACH the steer at a run through the gap the shove opened (the heading away from `zid`'s bearing,
        turned by STEER_TURNS to the first heading `clear_heading` passes); otherwise the swing at it only while the
        swing is undivided (`sore` false, the arms' pain under STRAIN_SOFT, and no endurance or tired hold: the arms'
        hold alone leaves it whole), logged `corner` {kind: break | swing, shoved, n}; a divided swing is not taken:
        None, logged `corner` {kind: shove, shoved, n, sore} (ruling P25-I, E12: the branch left no trace), and the
        lone or boxed-in target is shoved again (review-t3 finding 1; ruling: the swing at E11's armPain 38 to
        270 lands at 1/3.8 to 1/27 of its damage, #4370, and x0.5 again under the endurance hold, #4371, while the
        shove's knock-down is a crit roll pain does not touch, #4373, and the stomp after it is outside the divider,
        #4374: #4404 read five or six full swings before a zombie fell, two stomps finishing a fallen one; cost if
        wrong: a seventh shove at a zombie that keeps standing, a bat's swing at a divider of 2 or less left unswung).
        Ruling P25-L (E12: 29 `strain` shoves, 6 knock-downs in 39 done shoves, no swing for 108 game minutes, #4434,
        #4436): where the lone target would be shoved again, after SHOVE_BREAK_N missed shoves in a row at it within
        SHOVE_BREAK_N x SHOVE_REPEAT_S (`_missed_n`), the Fight breaks away as the two-zombie break does, logged
        `corner` {kind "break", shoved, n, misses}, its run of misses reset; never a Doorway's (its stand ends on its
        own wound, P25-K), and only with the `shove_break` rule on (`SHOVE_BREAK`); with `shove_break_run` on
        (ruling P25-T) the misses count over the Fight's life (`_missed_n`), and a shove at a target with a miss on
        record outside SHOVE_REPEAT_S consults both breaks (`_run_break`; the swing keeps the window). Rulings P25-P
        and P25-S: a shove-and-stomp Fight (`shove_only`) takes no swing, so its lone target is shoved again (or broken
        from) as under a divided one."""
        n = len(self._standing(FIGHT_REACH))
        brk = self._pair_break(zid, z, n)
        if brk is not None:
            return brk
        if self._divided(sore):
            brk = self._lone_break(zid, z, n)
            if brk is not None:
                return brk
            self.why["corner"] = {"kind": "shove", "shoved": zid, "n": n, "sore": sore}
            return None
        self.why["corner"] = {"kind": "swing", "shoved": zid, "n": n}
        self._held_before = False
        return Attack(zid)
