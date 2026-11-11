"""The point-blank pin (Plan 27 Task 5 fix 2, ruling P27-N; fix 3's cache and its residual R1): the mixin `FightPin`
(`fight.Fight`'s): a zombie at point blank, or read attacking, is left out by no mark. `_observe_attackers` latches
the attacker, `_pin_read` is the {id: why} of the zombies no mark leaves out, `_pin_free` the tick's read of it (taken
once after `observe`'s edge and kill reads, `_free`/`_free_n`, dropped by `_drop_pin_read` when a new edge mark leaves
a zombie out and read afresh on a newer frame: fix 3's residual R1), `_pin_marked` the marked ones among them,
`_pin_first` the pin on the nearest of them and `_pin_send` the shove, then the swing at the pinned one. Moved out of
`fight.py` at the Plan 27 close fix (m8; a pure move, goldens byte-identical); the state is the `Fight`'s own
(`_init_pin` sets the attacker latch and the cache), the Fight's `rules`, `only`, `edge_marks`, `unreachable` and `why`
are read and written here, and `fight.py`'s module docstring stays the record.
"""
from agent.base.planner.policies import (FIGHT_REACH, KEEP_R, POINT_BLANK_R, SHOVE_R, STAND_MIN_R, blocked,
                                         hit_reaction, line_to, on_floor, target_id_ok, zdist)
from agent.base.pza1 import Attack, Shove


class FightPin:
    """The point-blank pin (the module docstring): `Fight`'s mixin."""

    def _init_pin(self):
        self._attackers = set()             # the ids read attacking (`me.attackers` with a hit reaction, the nearest
                                            # listed within FIGHT_REACH), kept while within it: no mark leaves them out
                                            # (P27-N)
        self._free = None                   # the tick's `_pin_free`, read once after `observe`'s edge and kill reads
                                            # (fix 3, minor 4); None: read on each call (no observe yet)
        self._free_n = -1                   # the `world.frame_n` of that read: a newer frame reads afresh (fix 3's
                                            # residual R1: the threat's finish reads `blocked` before this tick's
                                            # observe)

    def _take_pin_read(self):
        """The tick's `_pin_free`: `_pin_read` taken now, on this frame (`observe`, after its edge and kill reads)."""
        self._free = self._pin_read()
        self._free_n = self.world.frame_n

    def _drop_pin_read(self):
        """The tick's `_pin_free` read is dropped (a new edge mark leaves the refused zombie out: fix 3, minor 4):
        the next call reads afresh."""
        self._free = None

    def _observe_attackers(self):
        """Ruling P27-N's attacker read, every observe: with the `point_blank_pin` rule on, the frame reading
        `me.attackers` above 0 with a hit reaction (`hit_reaction`: the bite's or any attack's) adds the nearest listed
        zombie (a wire id, with a position, not read dead) to `_attackers` where it stands within FIGHT_REACH, and each
        one there is kept while it stands within FIGHT_REACH (so the pin outlasts its reaction to the next allowed
        tick); off, none."""
        if "point_blank_pin" not in self.rules:
            self._attackers = set()
            return
        zs, dead = self.world.zombies, blocked(self.dead, self.clock())
        near = [(zdist(self.world, z), repr(zid), zid) for zid, z in zs.items() if target_id_ok(zid)
                and zid not in dead and z.get("x") is not None and z.get("y") is not None]
        self._attackers = {zid for d, _, zid in near if zid in self._attackers and d <= FIGHT_REACH}
        n = (self.world.me or {}).get("attackers")
        if (near and min(near)[0] <= FIGHT_REACH and isinstance(n, int) and not isinstance(n, bool) and n > 0
                and hit_reaction(self.world) is not None):
            self._attackers.add(min(near)[2])

    def _pin_free(self):
        """The tick's `_pin_read` (`observe` takes it once, after its edge and kill reads; a new edge mark drops it),
        else a fresh read; a read taken on an older frame (`_free_n` behind `world.frame_n`: the threat's finish
        rules call `blocked` before the tick's `observe`, fix 3's residual R1) is dropped and read afresh."""
        if self._free is not None and self._free_n == self.world.frame_n:
            return self._free
        return self._pin_read()

    def _pin_read(self):
        """Ruling P27-N (E20, `e_day_20-20261103-121340`: from line 722 to line 747, 26 lines and 12.603 s, the why read
        `target` null and `unreachable` [3189], the no-progress stall's mark, and the Fight sent nothing while 3189 bit
        from 0.507 to 1.576 tiles): {id: why} of the zombies no mark leaves out of the Fight's targets, with the
        `point_blank_pin` rule on: each listed within POINT_BLANK_R ("point_blank"), and each read attacking
        (`_attackers`, "attacker"); never a zombie read dead, one outside `only`, one refused across a known blocked
        edge (`edge_marks`, P25-X: the sixth golden's gate zombie 15885 stood 0.9282266374931059 tiles off across the
        fence row at its line 228) nor one whose line reads blocked (`line_to` False: P23-K's zombie behind a locked
        door, which run 1 swung at 103 times); {} with the rule off."""
        if "point_blank_pin" not in self.rules:
            return {}
        zs, dead = self.world.zombies, blocked(self.dead, self.clock())
        out = {zid: "attacker" for zid in self._attackers if zid in zs}
        for zid, z in zs.items():
            if (target_id_ok(zid) and z.get("x") is not None and z.get("y") is not None
                    and zdist(self.world, z) <= POINT_BLANK_R):
                out[zid] = "point_blank"
        out = {zid: w for zid, w in out.items() if zid not in dead and zid not in self.edge_marks
               and (self.only is None or zid in self.only) and line_to(self.world, zs[zid]) is not False}
        return self._pin_unstalled(out)

    def _pin_unstalled(self, out):
        """Plan 35 fix 8b (the controller's ruling on the fix 8 report, concern 1): a zombie whose reflex stall marked it
        (`dispatch.FightDispatch._stalled`, its span) is left out of the pin while another standing zombie the marks
        leave in stands within KEEP_R (the melee goes at that one, the fence case's climber); with none,
        P27-N's pin takes it as before (the Lua's stall and re-pin own it)."""
        stalled = blocked(getattr(self, "_stalled", {}), self.clock())
        if not stalled or not any(zid in stalled for zid in out):
            return out
        marks = blocked(self.unreachable, self.clock()) | blocked(self.dead, self.clock())
        if not any(zid not in marks for zid, _, _ in self._standing(KEEP_R)):
            return out
        return {zid: w for zid, w in out.items() if zid not in stalled}

    def _pin_marked(self):
        """Ruling P27-N: the `_pin_free` zombies a mark (`unreachable`: the no-progress stall's, a failed walk's, the
        seek's skip) would have left out, {id: why}: the case the rule exists for. An unmarked zombie at point blank
        keeps the Fight's own rules (its shove, its corner, its breaks)."""
        free = self._pin_free()
        if not free:
            return {}
        marks = blocked(self.unreachable, self.clock())
        return {zid: why for zid, why in free.items() if zid in marks}

    def _pin_first(self):
        """Ruling P27-N: with a marked `_pin_free` zombie listed (`_pin_marked`) and the pin on no `_pin_free` one,
        the nearest marked one is pinned."""
        pins = self._pin_marked()
        if not pins or self.target in self._pin_free():
            return
        zs = self.world.zombies
        self.target = min(pins, key=lambda zid: (zdist(self.world, zs[zid]), repr(zid)))
        self.repositioned = False

    def _pin_send(self, zid, z, d):
        """Ruling P27-N's send at the pinned target `zid` (`d` tiles off) when it is `_pin_marked` and standing:
        `(command,)`, logged `pin` {why}: in a hit reaction nothing (the engine starts no swing in one: the next
        allowed tick sends); else the shove (the knock-down's chance, #4373) within SHOVE_R where the last swing-like
        send was no shove, the build announcing it and no other standing zombie within STAND_MIN_R; else the swing
        (`Attack`), where it is allowed (`no_swing` false; within the reach and its margin in the stance, P27-M), or,
        the swing barred, the shove again. None where neither goes: the Fight's own path then (its stance, its
        wounded backpedal), the target still pinned."""
        why = self._pin_marked().get(zid)
        if why is None or on_floor(z):
            return None
        self.why = {"target": zid, "pin": {"why": why}, "dist": d}
        hit = hit_reaction(self.world)
        if hit is not None:
            self.why["hitReaction"] = hit
            return (None,)
        shove = (d <= SHOVE_R and target_id_ok(zid) and self._swing_ok("shove", zid)
                 and self._standing_near(STAND_MIN_R, (zid,)) is None)
        if shove and (not self._shoved or self.no_swing()):
            self.why["shove"] = "pin"
            return (Shove(zid),)
        r = self.reach_r()
        if self.no_swing() or (r is not None and self.stance_at(d) and d > r):
            return None
        if r is not None and self.stance_at(d):
            self.why["attack"] = {"dist": d, "reach": self.world.weapon["reach"]}   # P27-M, as the stance's attack logs
        return (Attack(zid),)
