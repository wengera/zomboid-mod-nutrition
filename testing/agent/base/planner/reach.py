"""The attack within reach (Plan 27 Task 5 fix 2, ruling P27-M): the mixin `FightReach` (`fight.Fight`'s): the
standing fight's attack at a standing zombie goes only within the frame's `weapon.reach` plus ATTACK_MARGIN (`reach_r`);
beyond it within FIGHT_REACH the stance stands facing the zombie and lets it come (`_attack_hold`) and the advance
walks to the reach (`_reach_walk_due`, `_reach_walk`). Moved out of `fight.py` at the Plan 27 close fix (m8; a pure
move, goldens byte-identical); the rule keeps no state of its own (so no `_init_reach`: it reads the Fight's `rules`,
`advance`, `why` and `world`), and `fight.py`'s module docstring stays the record.
"""
from agent.base.planner.policies import ATTACK_MARGIN, FIGHT_REACH, WALK_DONE_R, chasing, on_floor
from agent.base.pza1 import WalkTo
from agent.base.world import me_xy


class FightReach:
    """The attack within reach (the module docstring): `Fight`'s mixin."""

    def reach_r(self):
        """Ruling P27-M: the tiles within which the standing fight's attack goes at a standing zombie, the frame's
        `weapon.reach` (the Lua's own `K.reachOf`, inside which its attack swings at once) plus ATTACK_MARGIN, with the
        `attack_reach` rule on and a positive reach read; else None (the attack within FIGHT_REACH, the rule before
        it)."""
        r = (self.world.weapon or {}).get("reach") if "attack_reach" in self.rules else None
        ok = isinstance(r, (int, float)) and not isinstance(r, bool) and r > 0.0
        return r + ATTACK_MARGIN if ok else None

    def _reach_walk_due(self, z, d):
        """Ruling P27-M: the advance (`advance`, P24-N and the seek's fix) closes on its standing target `z`, `d` tiles
        off beyond `reach_r`, by the walk to the reach (`_reach_walk`): beyond FIGHT_REACH whatever it reads, within it
        only while the target reads no target of its own (a chaser within FIGHT_REACH is let come, the stance
        standing)."""
        r = self.reach_r()
        return (r is not None and self.advance and self.stance_at(d) and d > r and not on_floor(z)
                and (d > FIGHT_REACH or not chasing(z)))

    def _reach_walk(self, zid, z, d):
        """Ruling P27-M (E20, `e_day_20-20261103-121340`: the advance's `toward` leg held to FIGHT_REACH at the idle
        3189 and the attack a190 went at 1.8161174585612616 tiles, its own approach running the character 1.76 tiles
        into the zombie, which bit): the advance's walk at a walk to the point on the line to the target WALK_DONE_R
        short of `reach_r` from it (the Lua's walk ends `done` within WALK_DONE_R of its target, so it ends at
        `reach_r`; a walk to the point at `reach_r` would end WALK_DONE_R short and, re-sent from there, end on its
        accept tick unmoved, P23-AJ 5), the stance walk `reach` (`_walk_gives_way`: it gives way within `reach_r`, or
        as the target comes within FIGHT_REACH), the stance's standing leg then, and the attack from it. Logged
        `reach_walk` {target, dist, to}."""
        r = self.reach_r()
        mx, my = me_xy(self.world)
        k = max(r - WALK_DONE_R, 0.0) / d
        self.why.update({"stance": True, "leg": "walk", "advance": True, "stand_s": self.stand_s(),
                         "reach_walk": {"target": zid, "dist": d, "to": r}})
        self._seek_send, self._walk_kind = False, "reach"
        return WalkTo(z["x"] + (mx - z["x"]) * k, z["y"] + (my - z["y"]) * k, "walk")

    def _attack_hold(self, zid, z, d):
        """Ruling P27-M at the swing: the standing fight's target `zid` standing `d` tiles off beyond `reach_r` (within
        FIGHT_REACH: the Lua's attack would approach it at a run, its own skill's walk) takes no attack, logged
        `attack_held` {target, dist, reach}: the advance's walk to the reach where it is due (`_reach_walk_due`), else
        the stance holding its ground facing the target and letting it come, its running standing leg kept (`(None,)`)
        or a new one sent (`enter`, (0, 0)). None where the attack goes (within `reach_r`, the rule off, no reach read,
        no stance)."""
        r = self.reach_r()
        if r is None or not self.stance_at(d) or d <= r or on_floor(z):
            return None
        self.why["attack_held"] = {"target": zid, "dist": d, "reach": self.world.weapon["reach"]}
        if self._reach_walk_due(z, d):
            return (self._reach_walk(zid, z, d),)
        a = self.last
        if (a is not None and a.type == "aim" and not self.actions.done(a) and self.in_stance()
                and a.args.get("targetId") == zid and a.args.get("vx") == 0.0 and a.args.get("vy") == 0.0):
            return (None,)
        return (self._stance_leg(zid, z, d, kind="enter"),)
