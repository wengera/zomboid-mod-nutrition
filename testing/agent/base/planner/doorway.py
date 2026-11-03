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
  from there. Ruling P26-B (`STAND_SECOND_EXIT`; E16: the stand held the one door of a shed until the group came
  through it, and the `inside` end found no way out): a door whose building has no other way out on its floor (another
  door, an opening or a window, `night.exits`) is refused `one_exit`, so the stand is only taken where its ends under
  a group can walk out (P25-W). Ruling P26-K (`STAND_CROWD`; E17, E16 and E14 each died with five or six in the room
  after the stand's end): the stand leaves once STAND_CROWD_N held zombies stand within DANGER_R (`crowd`), before
  they reach the front.
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
  `me.attackers` reads DRAG_DOWN_N - 1 (`drag`: ruling P25-U, E14's three attackers read 0.101 s before the
  drag-down, two 3.001 s before; ruling R1 of review-t32-brief read DRAG_DOWN_N, `STAND_DRAG_EARLY` off), or the
  weapon is gone (`unarmed`: the stand swings a weapon), or a standing zombie reads on a square of the stand's room
  off the door square and not its target (`inside`: ruling P25-V, `stand_room`), or a part bleeds that did not when
  the stand began (`wound`: ruling P25-K), or STAND_CROWD_N or more held zombies stand within DANGER_R (`crowd`:
  ruling P26-K). After `wound`, `crowd`, `drag` or `inside` (ruling P25-W: the group is at or through the front, or
  gathered before it) the plan is dropped and the Flee walks out of the building by its way out (`Flee.walk_out`,
  `policies.exit_plan`), else holds trapped; never the close, which in E14 shut the kitchen door with five zombies
  inside. After `health`, `unarmed` or `quiet` the plan goes back to its `close` step, sent from inside as today's
  shelter close (the Lua's `interact`: a close that fails reads `passed`, and the sheltered hold, the door fight, the
  re-close guard and the way out follow, `night.shelter_ended`). Off the building's room squares and more than
  DOOR_OFF_R from the threshold square
  (`off`: Task 32 fix 1, the review's major 2, E9's replayed stand held at 13 tiles off its post) the plan is
  dropped, no close walked to a door left behind, and the flee steers (logged `doorway_left` "off"). With nothing
  held at all (every zombie dead or gone beyond DISENGAGE_R) the threat branch ends as it always has, the door left
  as it stands.
"""
import math

from agent.base.planner.fight import Fight
from agent.base.planner.policies import (AIM_LEG_S, AIM_R, DANGER_R, DRAG_DOWN_N, FIGHT_REACH, FLEE_HEALTH,
                                         POINT_BLANK_R, Policy, STAND_CROWD_N, STAND_MIN_R, arm_pain, blocked, centre,
                                         exit_kind, hit_reaction, line_to, on_floor, on_post, on_room, standing,
                                         target_id_ok, zdist)
from agent.base.pza1 import Aim, Attack, Shove, WalkTo
from agent.base.world import me_floor, me_xy

DOOR_STAND_N = 3      # standing zombies within DANGER_R at most for a `many` flee's shelter to be a doorway stand
                      # (ruling P24-AO: "at most three"; #4290's drag-down counts three standing attackers)
DOOR_HOLD_S = 10.0    # wall seconds with no zombie within DANGER_R before the stand ends and the door is closed (a
                      # judgment: a shambler of the queue standing off at DANGER_R walks in within a few seconds; ten
                      # planner seconds is twenty ticks, longer than a 3 s flee leg and the stomp's 4 s walk)
STAND_EXIT_ENDS = ("wound", "crowd", "drag", "inside")   # the stand's ends under a group that walk out, never the
                                                         # close (ruling P25-W; `crowd`, ruling P26-K)
DOOR_OFF_R = 2.0      # tiles from the threshold square's centre beyond which a player off the building's room squares
                      # has left the stand (Task 32 fix 1, the review's major 2: "about 2 tiles"; a stomp's walk out of
                      # the doorway reaches the outside square and the one beyond it)

__all__ = ["Doorway", "DOOR_STAND_N", "DOOR_HOLD_S", "DOOR_OFF_R", "STAND_EXIT_ENDS", "standing", "stand_ready",
           "off_post", "off_post_at", "stand_room", "bleeding_parts"]


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


def off_post_at(world, plan, x, y):
    """`off_post` read at the point (x, y) on the player's floor (ruling P25-J (2): where the stomp's walk to a fallen
    zombie there would leave the player): off the building's room squares and more than DOOR_OFF_R from the centre of
    the threshold square inside."""
    s = world.map.get((int(math.floor(x)), int(math.floor(y)), me_floor(world))) or {}
    if s.get("room") is not None and s.get("building") == plan["building"]:
        return False
    c = centre(plan["way"][0])
    return math.hypot(c[0] - x, c[1] - y) > DOOR_OFF_R


def stand_room(world, plan):
    """Ruling P25-V's bound, the room the stand's door opens into: the threshold's room square (`way`'s inside square)
    and every square reached from it by orthogonal steps through mapped squares of the same building whose `room`
    reads the same name, a frozenset (memoised per map version). `policies.in_building` reads the whole building (any
    of its room squares, or a door square of it); the scan's `room` is a name, so a room is bounded by its name and
    its squares' contiguity (two rooms of one name that touch read as one)."""
    start = plan["way"][0]

    def flood():
        s0 = world.map.get(start) or {}
        b, name = s0.get("building"), s0.get("room")
        if name is None:
            return frozenset()
        seen, todo = {start}, [start]
        while todo:
            x, y, zf = todo.pop()
            for n in ((x + 1, y, zf), (x - 1, y, zf), (x, y + 1, zf), (x, y - 1, zf)):
                s = world.map.get(n)
                if n not in seen and s is not None and s.get("room") == name and s.get("building") == b:
                    seen.add(n)
                    todo.append(n)
        return frozenset(seen)
    return world.memo(("stand_room", start), flood)


def bleeding_parts(world):
    """The indices of the frame's `body.parts` reading `bleeding` true (ruling P25-K: the stand's wound end), a set."""
    return {p["i"] for p in ((world.body or {}).get("parts") or ())
            if isinstance(p, dict) and isinstance(p.get("i"), int) and p.get("bleeding") is True}


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

    def _finish_post(self, z):
        """Ruling P25-J (2): a fallen zombie beyond FIGHT_REACH is the stand's to stomp only where the stomp's walk to
        it keeps the player on its post's tolerance (`off_post_at`: a room square of the building, or within DOOR_OFF_R
        of the threshold square's centre; the walk back exists), so the stand finishes E12's 10906 at 2.9 tiles and
        leaves one 5 tiles outside."""
        return not off_post_at(self.world, self.plan, z["x"], z["y"])

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
            return self._in_reach() is None and not self._finishable()
        if self.last.type != "aim":
            return True
        if not self._on_post() or self._finishable():
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


class DoorwayStand:
    """The threat branch's side of the doorway stand (ruling P24-AO, P24-AX; moved out of `threat.py` at Plan 25
    Task 2, a pure move): `Threat`'s mixin, `_doorway` its ends, `_doorway_pick` its why, `_stand` its answer."""

    def _doorway(self):
        """Ruling P24-AO (`planner/doorway.py`'s docstring the record): `("doorway", None)` while the Flee's stand plan
        reads `stand` and none of its ends holds (`_stand_end`, in this order):
        - `wound` (ruling P25-K, `STAND_WOUND`; E12, #4431: the stand held the door from game minute 694 while the
          bleeding parts rose from 1 to 7, the first bite far above FLEE_HEALTH): a part reading `bleeding` that was not
          when the stand began (the start's indices kept on the plan, `bleed0`), logged `doorway_wound` (the indices);
        - `crowd` (ruling P26-K, `STAND_CROWD`): STAND_CROWD_N or more held zombies within DANGER_R (`_stand_crowd`),
          logged `doorway_crowd` {n};
        - `inside` (ruling P25-V, `STAND_INSIDE`): a standing zombie on a square of the stand's room, off its door
          square and not its target (`_stand_inside`), logged `doorway_inside` {id, square};
        - `drag` with the frame's `me.attackers` at DRAG_DOWN_N - 1 (ruling P25-U, `STAND_DRAG_EARLY`; off, at
          DRAG_DOWN_N: ruling R1, Task 32 fix 1, the front has failed; `_stand_drag_n`), logged `doorway_drag`; read
          before `health` since Task 14 fix 1 (`STAND_DRAG_EARLY`; off, after it), so a two-attacker tick under
          FLEE_HEALTH leaves by the way out, never the close;
        - `health` under FLEE_HEALTH;
        - `unarmed`;
        - `off` (`off_post`: off the building's room squares and beyond DOOR_OFF_R of the threshold, fix 1's major 2);
        - `quiet` once no zombie has been within DANGER_R for DOOR_HOLD_S wall seconds (`plan["quiet"]` the last wall
          one was).
        Every end is logged `doorway_left` (`stand_end`) and kept as `plan["left"]`; where it goes:
        - `wound`, `crowd`, `drag` and `inside` (STAND_EXIT_ENDS) under ruling P25-W (`STAND_EXIT`; E14: the `wound`
          end's close shut the kitchen door with five zombies inside): the plan is dropped and the Flee walks out of
          the building (`Flee.walk_out`: the way out, else the trapped hold, never the close), `("flee", "doorway")` on
          the tick and while that way out runs (`Flee.stand_exit_running`), ahead of every row as the close ran; logged
          `doorway_exit` on the tick (`_stand_exit_why`);
        - `off` drops the plan, no close walked back to the door; the flee steers from the next row;
        - `health`, `unarmed` and `quiet` (and every end with `STAND_EXIT` off) put the plan back on its `close` step,
          and while that close runs `("flee", "doorway")`: the Flee sends it from inside and its end is the shelter's.
        `stand_left` (the Flee's keep past a dropped plan, `_decide`) is set for `off` and the exit ends. Else None (no
        stand)."""
        f = self.flee
        if f is None:
            return None
        if f.stand_exit_running():
            return "flee", "doorway"
        plan = f.plan
        if plan is None or not plan.get("stood"):
            return None
        if plan["step"] == "stand":
            left = self._stand_end(plan)
            if left is None:
                return "doorway", None
            plan["left"] = left
            self.stand_end = left
            if left == "off":
                self.stand_left = left
                f._drop(False)   # the episode only steers from here (`picked` kept)
                return None
            if self.STAND_EXIT and left in STAND_EXIT_ENDS:
                self.stand_left = self.stand_exit = left
                f.walk_out(left)
                return "flee", "doorway"
            plan["step"] = "close"
        return ("flee", "doorway") if f.closing_stand() else None

    def _stand_exit_why(self, f):
        """Ruling P25-W's `doorway_exit` on the stand's end tick, read after the Flee answered: {end, exit}, `exit` the
        way out the choose took ("door", "opening" or, ruling P26-A, "window": `policies.exit_kind`), "trapped" for
        its trapped hold, "steer" off a room square (an end read within DOOR_OFF_R outside), else "deferred" (the
        flee's own drop or finish took the tick)."""
        if f.exit is not None:
            kind = exit_kind(self.world, f.exit)
        elif "trapped" in self.why:
            kind = "trapped"
        elif not on_room(self.world):
            kind = "steer"
        else:
            kind = "deferred"
        return {"end": self.stand_exit, "exit": kind}

    def _stand_end(self, plan):
        """The stand's end this tick (`_doorway`'s docstring), the first of its table that holds, else None; the quiet
        clock (`plan["quiet"]`) moved on while a zombie is within DANGER_R, and the wound read every tick (its start's
        snapshot is taken on the first). `crowd` reads the held zombies within DANGER_R (`_stand_crowd`) and logs their
        count (`stand_crowd`); `drag` reads the frame's `me.attackers` at `_stand_drag_n` and logs the count
        (`stand_drag`)."""
        now = self.clock()
        if self._within(DANGER_R):
            plan["quiet"] = now
        new = self._stand_wound(plan)
        if new:
            self.stand_wound = new
        attackers = self._attackers()
        crowd = self._stand_crowd()
        inside = self._stand_inside(plan)
        health = ("health", lambda: self._health() < FLEE_HEALTH)
        drag = ("drag", lambda: attackers >= self._stand_drag_n())
        ends = (("wound", lambda: new),
                ("crowd", lambda: crowd is not None),
                ("inside", lambda: inside),
                *((drag, health) if self.STAND_DRAG_EARLY else (health, drag)),
                ("unarmed", lambda: not self._armed()),
                ("off", lambda: off_post(self.world, plan)),
                ("quiet", lambda: now - plan["quiet"] >= DOOR_HOLD_S))
        left = next((end for end, holds in ends if holds()), None)
        if left == "crowd":
            self.stand_crowd = {"n": crowd}
        if left == "drag":
            self.stand_drag = attackers
        if left == "inside":
            self.stand_inside = {"id": inside[0], "square": [inside[1][0], inside[1][1]]}
        return left

    def _stand_crowd(self):
        """Ruling P26-K (E17, `e_day_17-20261102-180459`: the stand held building 2's kitchen door from line 362 with
        six held within DANGER_R from line 370 and none inside, until its `inside` end at line 380; three came in
        through the door and three across the window square beside it, the first bite 2 game minutes later and the
        death at game minute 617; E16 held five, then six; E14's five came in through the window square beside its
        door): with `STAND_CROWD` on, the count of the held zombies within DANGER_R (`_within`: those read dead and
        those out of the hold across their blocked edge left out) when it is STAND_CROWD_N or more, else None. The pick
        is unchanged: its `standing` condition already refuses more than DOOR_STAND_N standing within DANGER_R."""
        if not self.STAND_CROWD:
            return None
        n = len(self._within(DANGER_R))
        return n if n >= STAND_CROWD_N else None

    def _stand_inside(self, plan):
        """Ruling P25-V (E14: the stand faced the door square while five zombies crossed the window square beside the
        door into the kitchen; its `_in_reach` takes a zombie inside only once within FIGHT_REACH): with `STAND_INSIDE`
        on, `(id, square)` of the nearest standing zombie (not `onFloor`, not read dead) on a square of the stand's room
        (`stand_room`: bounded to the room, not `in_building`'s whole building), neither on the door square (the one
        the stand fights through) nor the Doorway's target; else None. A downed one inside is the stand's stomp."""
        if not self.STAND_INSIDE:
            return None
        room = stand_room(self.world, plan)
        door = plan["doors"][plan["door_i"]]
        f = self.fight
        target = f.target if f is not None and f.doorway is not None else None
        dead = blocked(self.dead, self.clock())
        zf, best = me_floor(self.world), None
        for zid, z in self.world.zombies.items():
            if (z.get("x") is None or z.get("y") is None or on_floor(z) or zid in dead
                    or (target is not None and zid == target)):
                continue
            sq = (int(math.floor(z["x"])), int(math.floor(z["y"])), zf)
            if sq == door or sq not in room:
                continue
            key = (zdist(self.world, z), repr(zid))
            if best is None or key < best[0]:
                best = (key, zid, sq)
        return None if best is None else (best[1], best[2])

    def _stand_drag_n(self):
        """Ruling P25-U (E14, `e_day_14-20261030-235607`: three attackers read at seq 3655, `EndDeath` with `dragDown`
        0.101 s later, two read 3.001 s before): the attackers at which the stand's `drag` end fires, DRAG_DOWN_N - 1
        with `STAND_DRAG_EARLY` on (#4290: the drag-down needs DRAG_DOWN_N, so the end at it can never act in time),
        else DRAG_DOWN_N (ruling R1, Task 32 fix 1). The drag-down guard (`_drag`, P24-A (h)) leaves any fight at the
        same DRAG_DOWN_N - 1, but the stand's end reads first on a tick: `_doorway` is `_threat_plan`'s first row (the
        stand's plan holds the Flee and its premise is the one-tile front the guard flees), so while a stand stands the
        guard is never read; its end names the tick (`doorway_left` "drag"), and the guard reads once the stand's close
        (`STAND_EXIT` off) or its way out has ended (both run ahead of every row)."""
        return DRAG_DOWN_N - 1 if self.STAND_DRAG_EARLY else DRAG_DOWN_N

    def _stand_wound(self, plan):
        """Ruling P25-K: with `STAND_WOUND` on, the sorted indices of the parts bleeding now that were not when the
        stand began (`plan["bleed0"]`, taken on the stand's first tick), else []."""
        if not self.STAND_WOUND:
            return []
        now = bleeding_parts(self.world)
        if "bleed0" not in plan:
            plan["bleed0"] = frozenset(now)
            return []
        return sorted(now - plan["bleed0"])

    def _doorway_pick(self, flee):
        """Ruling P24-AX (E10: the doorway stand never ran, the count condition held on 155 of 162 `many` lines and a
        shelter was picked on 6, and no why said which condition failed): on a `many` line, read after the Flee
        answered (its pick made, if it was due), `ok` when the episode's plan is a doorway stand (marked, or standing,
        or stood); else the first condition that failed, in the order the stand reads them (`doorway.stand_ready`, the
        pick, `policies.stand_post`): `unarmed`, `no_stance` (no `aim` announced), `standing` (more than DOOR_STAND_N
        standing within DANGER_R), `inside` (on a room square: the flee walks out, never picks), `no_door` (no known
        exterior door's approach square within SHELTER_FLEE_R, `Flee.door_verdicts`), `locked` (every one locked or
        barricaded), `taken` (every free one refused for a zombie: in its building, its corridor, or nearer its
        approach than the player), `one_exit` (ruling P26-B: no door left free, and one refused only for its
        building's lack of a second way out), `picked` (a door was free, but the episode's one pick was spent: a plan
        without the stand, its post refused, or a plan dropped), `pending` (a door is free and the pick waits on a
        running leg)."""
        plan = flee.plan
        if plan is not None and (plan.get("stand") or plan.get("stood")):
            return "ok"
        if not self._armed():
            return "unarmed"
        if not self.world.can("aim"):
            return "no_stance"
        if len(standing(self.world, DANGER_R, blocked(self.dead, self.clock()))) > DOOR_STAND_N:
            return "standing"
        if on_room(self.world):
            return "inside"
        rows = flee.door_verdicts(flee._threats())
        verdicts = [v[3] for v in rows]
        if not verdicts:
            return "no_door"
        if "ok" not in verdicts:
            if all(v == "locked" for v in verdicts):
                return "locked"
            if "one_exit" in verdicts:
                _, b, door, _ = next(v for v in rows if v[3] == "one_exit")
                self.one_exit_refused = {"building": b, "door": [door[0], door[1]]}   # P26-B: the first refused door
                return "one_exit"
            return "taken"
        return "picked" if flee.picked or plan is not None else "pending"

    def _stand(self, held):
        """Ruling P24-AO: the doorway stand's answer: its `Doorway` fight over the Flee's stand plan (made once, kept
        while the plan stands; the Flee kept for the close), the mode `fight`, the flee episode's flags kept (the
        stand is the `many` flee's end), logged `doorway` (the building) beside the fight's why."""
        f = self.fight
        if f is None or f.doorway is None or f.plan is not self.flee.plan:
            self.fight = Doorway(self.world, self.actions, self.clock, self.flee.plan, unreachable=self.unreachable,
                                 dead=self.dead)
            self.cornered, self._corner_fight = None, None
        self.mode = "fight"
        policy = self.fight
        policy.threats = held
        policy.spent = self._fight_spent()   # R2: no swing under any hold
        policy.ride = self.care.riding()
        policy.rules = self._fight_rules()   # P25's rules: the Doorway reads `finish_far` (`_finish`), no other
        ans = self._answer(policy)
        self.why.update({"fight": True, "doorway": policy.doorway})
        return ans if ans is not None else (policy, None)
