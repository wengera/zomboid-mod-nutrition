"""The still read (ruling P30-E, `STILL`, survival iteration 24; Plan 30 Task 3, the spec
`2026-11-05-plan-30-the-intent-design.md` § 1 reading 2 and § 2 item 3): the threat branch's mixin `ThreatStill`, its
state Survive's own (`_init_still`), read where the threat branch's Fight would answer (`Threat._decide`).

F14 (`f_goals_15-20261105-092752`), decision lines 281 to 315: the melee stood out of reach at 32308, 2.005 tiles off,
for 16.5 s, the character unmoved and the zombie's distance steady, the melee re-sent every 2.5 s and nothing else
(the zombie stood behind a closed window, which P30-C's door read now leaves; the still read is the rule for any such
stand). The rule: an open-ground Fight (no corner, no door fight, no doorway stand) whose nearest held zombie stands
beyond the swing's reach (the Fight's `reach_r`, else FIGHT_REACH: one within it is the fight's, the swing or the
stance's back leg, never a stand; the replay of F1, `f_goals-20261028-202437`, line 481 read 15910 steady at 1.06 tiles
while the Fight walked at 15885) and has kept its distance within STILL_DRIFT_R of the read's start, the character
within STILL_MOVE_R of its own, read on every planner tick for STILL_S wall seconds, resolves (logged `still`
{target, d, resolved} on the threat why):
- `approach`, the zombie alone within DANGER_R and the health above FLEE_HEALTH_FLOOR: the stance's leg toward it (the
  Fight's `toward` leg, `fight.Fight._stance_leg`: an aim at it along a clear heading, else the walk the path follower
  takes round the wall), in place of the Fight's own answer;
- `goal` otherwise: the zombie left (unreachable for UNREACHABLE_S, so the Fight's release lets the goal run) and the
  threat branch passing this tick, its episode ended.
The read then starts again. Cost if wrong: an approach at a zombie a hold was right to wait on.
"""
import math

from agent.base.planner.policies import (DANGER_R, FIGHT_REACH, FLEE_HEALTH_FLOOR, STILL_DRIFT_R, STILL_MOVE_R,
                                         STILL_S, UNREACHABLE_S, target_id_ok, zdist)
from agent.base.world import me_xy


class ThreatStill:
    """The still read (the module docstring): `Threat`'s mixin."""

    STILL = True   # ruling P30-E (Plan 30 Task 3): the module docstring; off, the Fight stands on. In
                   # `survive.T14_SWITCHES`

    def _init_still(self):
        self._still_rec = None   # [zombie id, wall, its distance, the player's (x, y)] at the read's start, and the
                                 # planner tick it was last read on
        self.still_now = None    # this tick's `still` why {target, d, resolved}, else None

    def _still_read(self, held, fight):
        """`(resolved, zid, z, d)` when the still read resolves this tick (the module docstring), else None."""
        self.still_now = None
        if (not self.STILL or fight is None or fight.point_blank or fight.only is not None
                or fight.doorway is not None):
            self._still_rec = None
            return None
        ids = {id(z): zid for zid, z in self.world.zombies.items()}
        near = sorted(((zdist(self.world, z), repr(ids.get(id(z))), ids.get(id(z)), z) for z in held
                       if target_id_ok(ids.get(id(z)))), key=lambda e: e[:2])
        if not near:
            self._still_rec = None
            return None
        d, _, zid, z = near[0]
        if d <= (fight.reach_r() or FIGHT_REACH):   # a zombie within the swing's reach is the fight's, never a stand
            self._still_rec = None
            return None
        me, now, rec, tick = me_xy(self.world), self.clock(), self._still_rec, getattr(self, "ticks", 0)
        if (rec is None or rec[0] != zid or rec[4] != tick - 1 or abs(d - rec[2]) > STILL_DRIFT_R
                or math.hypot(me[0] - rec[3][0], me[1] - rec[3][1]) >= STILL_MOVE_R):
            self._still_rec = [zid, now, d, me, tick]
            return None
        rec[4] = tick   # read on consecutive ticks only: a tick the read skipped starts it again
        if now - rec[1] < STILL_S:
            return None
        alone = len(self._danger_near()) <= 1   # the once-a-tick DANGER_R count (fix 1, review-t3 m6)
        resolved = "approach" if alone and self._health() > FLEE_HEALTH_FLOOR else "goal"
        self.still_now = {"target": zid, "d": d, "resolved": resolved}
        self._still_rec = None
        if resolved == "goal":
            self.unreachable[zid] = now + UNREACHABLE_S
        return resolved, zid, z, d
