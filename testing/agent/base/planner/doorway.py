"""The doorway stand (ruling P24-AO, Plan 24 Task 32, survival iteration 11; the guides notes § 9 change 3: fight
through a doorframe, where zombies queue, never on an open lawn; #4290: the drag-down needs three standing zombies
attacking from under 0.9 tiles, which a doorway's one-tile front does not let stand round the player).

E9 (`e_day_9-20261030-052429`) fled `many` on 143 threat lines and killed nothing; its shelter flee twice entered and
closed building 1's door and left it again on the next `many` steer, and it died in the open with up to ten listed.
The rule changes the end of a `many` flee's shelter steps (`policies.Flee`, ruling P23-AG):

- **Taking the door.** A `many` flee whose standing zombies (not `onFloor`) within DANGER_R number at most
  DOOR_STAND_N, armed and on a build that announces the stance (`aim`) (`stand_ready`; Survive sets the Flee's
  `stand_ok` each tick), picks its shelter as before (a known building's exterior door whose approach square lies
  within SHELTER_FLEE_R, no zombie in its corridor or inside) and marks the plan a stand (`stand`, the door's
  `World.door_way` kept as `way`, and `post`: `policies.stand_post`, the room square one on from the threshold square
  away from the outside one; a door with none is closed as today). Its approach and open steps run as today; its
  enter walks to the post's centre (Task 32 fix 1, the review's blocker: the Lua's walk ends `done` within DONE_R 1.0
  of its target, so E9's enter to the threshold square's own centre ended on the outdoor door square of building 1,
  (10712, 10596), 0.84 tiles short, open on three sides; from the square beyond it ends at least half a tile inside
  the threshold). Where the close would go, the plan reads `stand` (`stood`) only once the player stands on a room
  square of the building (`policies.on_post`); else the enter is walked again (`ended` "outside", a retry, the stand
  given up for the close once STEP_RETRIES are spent), and Survive's threat branch runs the `Doorway` fight below.
  DOOR_STAND_N is read at the pick only, never again on arrival (the review's minor 10): the stand's own ends govern
  from there.
- **The stand** (`Doorway`, a `policies.Fight` that never walks the open-ground stance machine): on the square inside
  the threshold the enter left it on (a room square of the building), the stance held facing out (an `aim` of (0, 0)
  facing the nearest listed zombie within AIM_R, else the bearing to the door's outside square); whatever comes within
  FIGHT_REACH on a line not read blocked is swung at from the stance, a standing zombie at point blank shoved first
  (once a swing: the shove's knock-down chance, #4373, then the swing), a fallen one in reach stomped (P24-AL's
  `_finish`, the floor strike after a refused stomp); at `body.armPain` STRAIN_HARD (ruling P24-AP) never the swing:
  the shove at point blank every time, the stomp, else the stance held facing it. Pushed off the building's room
  squares (a stomp's walk), it walks back to the post at a walk; that walk, like the stance leg, gives way to a
  standing zombie within FIGHT_REACH on a line not read blocked or a downed one in reach (`busy`; Task 32 fix 1, the
  review's major 2: E9's replayed walk back held 23 s with the nearest at 0.50 tiles, health 97.5 to 41.6, unswung).
- **Leaving it** (`Survive._doorway`): only once no zombie has been within DANGER_R for DOOR_HOLD_S wall seconds
  (`quiet`), or the health falls under FLEE_HEALTH (`health`, the existing health flee line), or the frame's
  `me.attackers` reads DRAG_DOWN_N (`drag`: ruling R1 of review-t32-brief, three attackers mean the one-tile front
  has failed; at two the stand holds), or the weapon is gone (`unarmed`: the stand swings a weapon). The plan then
  goes back to its `close` step, sent from inside as today's shelter close (the Lua's `interact`: a close that fails
  reads `passed`, and the sheltered hold, the door fight, the re-close guard and the way out follow,
  `night.shelter_ended`). Off the building's room squares and more than DOOR_OFF_R from the threshold square
  (`off`: Task 32 fix 1, the review's major 2, E9's replayed stand held at 13 tiles off its post) the plan is
  dropped, no close walked to a door left behind, and the flee steers (logged `doorway_left` "off"). With nothing
  held at all (every zombie dead or gone beyond DISENGAGE_R) the threat branch ends as it always has, the door left
  as it stands.
"""
import math

from agent.base.planner.fight import Fight
from agent.base.planner.policies import (AIM_LEG_S, AIM_R, DANGER_R, FIGHT_REACH, POINT_BLANK_R, STAND_MIN_R, Policy,
                                         arm_pain, blocked, centre, hit_reaction, line_to, on_floor, on_post,
                                         target_id_ok, zdist)
from agent.base.pza1 import Aim, Attack, Shove, WalkTo
from agent.base.world import me_xy

DOOR_STAND_N = 3      # standing zombies within DANGER_R at most for a `many` flee's shelter to be a doorway stand
                      # (ruling P24-AO: "at most three"; #4290's drag-down counts three standing attackers)
DOOR_HOLD_S = 10.0    # wall seconds with no zombie within DANGER_R before the stand ends and the door is closed (a
                      # judgment: a shambler of the queue standing off at DANGER_R walks in within a few seconds; ten
                      # planner seconds is twenty ticks, longer than a 3 s flee leg and the stomp's 4 s walk)
DOOR_OFF_R = 2.0      # tiles from the threshold square's centre beyond which a player off the building's room squares
                      # has left the stand (Task 32 fix 1, the review's major 2: "about 2 tiles"; a stomp's walk out of
                      # the doorway reaches the outside square and the one beyond it)

__all__ = ["Doorway", "DOOR_STAND_N", "DOOR_HOLD_S", "DOOR_OFF_R", "standing", "stand_ready", "off_post"]


def standing(world, r, skip=()):
    """The listed zombies within `r` tiles of the player not lying on the floor (`on_floor`), the ids in `skip` (read
    dead) left out."""
    return [z for zid, z in world.zombies.items() if zid not in skip and z.get("x") is not None
            and z.get("y") is not None and not on_floor(z) and zdist(world, z) <= r]


def stand_ready(world, skip=()):
    """Ruling P24-AO's condition on the flee: armed, the build announces the stance (`aim`), and DOOR_STAND_N or fewer
    standing zombies within DANGER_R (`skip`: the ids read dead)."""
    return (world.weapon is not None and world.can("aim")
            and len(standing(world, DANGER_R, skip)) <= DOOR_STAND_N)


def off_post(world, plan):
    """The player has left the stand plan `plan`'s post (`left` "off", Survive's `_doorway`): off the building's room
    squares (`on_post`) and more than DOOR_OFF_R from the centre of the threshold square inside (`way`'s room
    square)."""
    if on_post(world, plan["building"]):
        return False
    mx, my = me_xy(world)
    c = centre(plan["way"][0])
    return math.hypot(c[0] - mx, c[1] - my) > DOOR_OFF_R


class Doorway(Fight):
    """The doorway stand (the module docstring): a Fight over the Flee's stand `plan` (its `building`, its kept door
    and `way`, its `inside` square), made by Survive once the plan reads `stand` and kept while it does."""

    def __init__(self, world, actions, clock, plan, unreachable=None, dead=None):
        super().__init__(world, actions, clock, unreachable=unreachable, dead=dead)
        self.plan = plan
        self.doorway = plan["building"]
        self.door = plan["doors"][plan["door_i"]]

    def standing(self):
        """Never the open-ground stance machine (the seek, the backpedal, the advance): the post is the threshold."""
        return False

    def _base(self):
        return {"doorway": self.doorway, "door": [self.door[0], self.door[1]]}

    def _on_post(self):
        """The player stands on a room square of the stand's building (`policies.on_post`: the square inside the
        threshold the enter left it on, or one beside it)."""
        return on_post(self.world, self.doorway)

    def _in_reach(self):
        """(id, zombie, dist) of the nearest standing zombie the Fight may target within FIGHT_REACH on a line not read
        blocked (the doorway's front: a wall beside the door blocks the diagonals), else None."""
        skip, best = self.blocked(), None
        for zid, z in self.world.zombies.items():
            if (not target_id_ok(zid) or zid in skip or z.get("x") is None or z.get("y") is None or on_floor(z)
                    or self.knocked.get(zid, -math.inf) > self.clock()):
                continue
            d = zdist(self.world, z)
            if d <= FIGHT_REACH and line_to(self.world, z) is not False and (best is None or (d, repr(zid)) < (
                    best[2], repr(best[0]))):
                best = (zid, z, d)
        return best

    def _face(self, zid):
        """The stance held on the post facing zombie `zid` (an `aim` of (0, 0))."""
        self.why.update({"stance": True, "leg": "stand"})
        return Aim(0.0, 0.0, AIM_LEG_S, targetId=zid)

    def _wounded_leg(self, zid, z, d):
        """P24-AP (and R2: any hold, `no_swing`) on the post: never the swing, and no backpedal off the threshold: the
        stance held facing it."""
        self.why["wounded"] = arm_pain(self.world)
        if self.spent:
            self.why["spent"] = list(self.spent)
        return self._face(zid)

    def _outward(self):
        """The bearing in degrees (0 east, 90 south) from the player to the door's outside square's centre (`way`), else
        to the door square's centre."""
        way = self.plan.get("way")
        sq = way[1] if way else self.door
        mx, my = me_xy(self.world)
        return math.degrees(math.atan2(sq[1] + 0.5 - my, sq[0] + 0.5 - mx)) % 360.0

    def busy(self):
        """The Policy's rule; a running stance leg gives way once the player is off the post (the walk back), a zombie
        lies downed in reach (the stomp), or a standing one comes within FIGHT_REACH (the swing; at STRAIN_HARD, where
        the leg faces it, only at point blank, the shove). The walk back gives way to the same two (Task 32 fix 1, the
        review's major 2): a zombie in reach is fought from where the player stands."""
        if not Policy.busy(self):
            return False
        if self.last.type == "walkTo":
            return self._in_reach() is None and not self._downed()
        if self.last.type != "aim":
            return True
        if not self._on_post() or self._downed():
            return False
        t = self._in_reach()
        return t is None or (self.no_swing() and t[2] > POINT_BLANK_R and self.last.args.get("targetId") == t[0])

    def _choose(self):
        """The stand's next command (the module docstring): nothing in a hit reaction; a downed zombie in reach finished
        (`_finish`); the nearest standing zombie in reach shoved at point blank (once a swing; every time at
        STRAIN_HARD), else swung at (never at STRAIN_HARD: faced); off the post, the walk back; else the stance held
        facing out."""
        self._seek_send, self._walk_kind = False, None
        hit = hit_reaction(self.world)
        if hit is not None:
            self.why = dict(self._base(), hitReaction=hit)
            return None
        fin = self._finish()
        if fin is not None:
            self.why.update(self._base())
            return fin[0]
        t = self._in_reach()
        if t is not None:
            zid, z, d = t
            self.target = zid
            self.why = dict(self._base(), target=zid, dist=d)
            if (d <= POINT_BLANK_R and (not self._shoved or self.no_swing()) and self._swing_ok("shove", zid)
                    and self._standing_near(STAND_MIN_R, (zid,)) is None):
                self.why["shove"] = "doorway"
                return Shove(zid)
            if self.no_swing():
                return self._wounded_leg(zid, z, d)
            self._held_before = self.in_stance()
            self.why["stance"] = self._held_before
            return Attack(zid)
        if not self._on_post():
            self.why = dict(self._base(), step="return")
            return WalkTo(*centre(self.plan["post"]), "walk")
        dead = blocked(self.dead, self.clock())
        near = [(zdist(self.world, z), repr(zid), zid) for zid, z in self.world.zombies.items()
                if target_id_ok(zid) and zid not in dead and z.get("x") is not None and z.get("y") is not None]
        near = [e for e in near if e[0] <= AIM_R]
        self.why = self._base()
        if near:
            zid = min(near)[2]
            self.why["target"] = zid
            return self._face(zid)
        self.why.update({"stance": True, "leg": "stand", "bearing": self._outward()})
        return Aim(0.0, 0.0, AIM_LEG_S, bearing=self._outward())
