"""The door held (ruling P30-C, `DOOR_HELD`, survival iteration 24; Plan 30 Task 3, the spec
`2026-11-05-plan-30-the-intent-design.md` § 1 reading 3 and § 2 item 3): the threat branch's mixin `ThreatDoorHeld`
and the Fight's `FightDoorHeld`, their state Survive's and the Fight's own.

F14 (`f_goals_15-20261105-092752`): on decision lines 146 to 192 zombie 32307 chased at 0.91 tiles behind the locked
gate (10732, 10642) while the threat why read empty (the zombie edge-marked out of the hold, `Survive._edge_out`) and
the model's goal walks went into the gate, two of them ending `stuck`; on lines 1081 to 1105 the Fight's reposition
rule ran through the closed door (10770, 10633) at 32448, 0.90 tiles off, and the melee killed it there with no hit;
the Fight's line is read only within FIGHT_REACH (lines 281 to 315: 16.5 s standing at 32308 behind a closed window
at 2.005 tiles). E23 (`e_day_23-20261105-095110`), lines 121 to 133: the same gate, 26240 refused and left.

- The read (`portal_between`): the first door or window on the straight line from the player to a zombie
  (`World.edge_steps`, the steps the blocked-edge read walks), a wall or fence with neither met first reading none; a
  door's state is its last `door` event's where one came since the map last read the square (`World.door_seen`: the
  open the stance sent reads open at once, the map's own edge flags waiting for the next scan).
  Its kind: `door` (a closed door record, neither locked nor barricaded nor marked by P24-Z's failures; from a room
  square a locked building door too: `ToggleDoorActual` unlocks a locked door for a player inside,
  `canBeOpenFromInside`, #4367, and F14 opened the door (10770, 10633), recorded locked (fail-closed, PZA/1.6), from
  the kitchen square (10769, 10633), its map line at seq 10905 reading it open and unlocked; #4367's bound: a door
  locked but not by key may refuse from one side, the `Interact`'s `locked` end then, two of which mark it (P24-Z) so
  the read turns it `locked door`), `locked gate` (one that is locked, barricaded or marked, on an outdoor edge: no
  room square either side), `locked door` (on a building's wall), `window`.
- `ThreatDoorHeld._door_held_read`, each threat read before the hold is counted (`Threat._threat_read`): the
  zombies listed within DOOR_HELD_R, none read dead, the edge-marked ones included (they are the gate's), whose line
  meets a portal, grouped by that portal; the nearest group's portal decides, on the tick it is read, never a stand
  (F14's 32448 stood behind its door with the character on a room square, so the read runs inside too; there only
  `stance_open` is taken, and with it the inside hold, `Threat._threat_plan`'s `held_inside`, gives way to it, every
  `leave` inside left to the inside hold's rules, so a sheltered character never walks out on a group at its door):
  - `stance_open`: a `door`, one zombie behind it, the health at FLEE_HEALTH_FLOOR or above, armed, on a build
    announcing `interact` and `aim`: the Fight's plan (`door_open`: the zombie, the door, the post): the stance's leg
    to the post square (the near square's `stand_post` inside, or the square beyond it outside, `policies._beyond`;
    the near square itself when the map holds neither open), then `Interact` open on the door, then (the door read
    open) the stance stands facing the zombie (`meet`) while it is still across the edge, and once it is on the
    player's side the Fight's own ladder and its melee meet it as it comes;
  - `leave` otherwise (a locked gate or door, a window, two or more behind, the health under the floor): each zombie
    behind edge-marked across the portal's edge (`edge_marks`, as `edges.FightEdge._mark_edge` refuses one, so the
    hold leaves it out while it stays across and the Fight never pins it), the running goal whose way goes through
    the portal (`meets_portal`: the straight line from the player to its target, or to its running walk's target,
    meets this portal, or this portal's run of fence, first; fix 1, review-t3 M1: never every goal on the far side
    of the edge's whole line) ended
    `failed "door held"`, cooled, its far target marked (`mark_far`: no walk goes into the gate on the next tick), and
    a `door` left so marked held (`World.mark_door`, the routes reading it wall for DOOR_RETRY_MIN game
    minutes: the route's next way).
  Logged `door_held` {door, kind, n_behind, decision} on the threat why of the tick the decision is first read
  (whatever answered), again only when the door, the decision or the zombies behind change.
- `FightDoorHeld._door_open_cmd`: the plan's steps for the Fight's pin (its why `door_step` the step: `post`,
  `open` or `meet`); a pin that is not the plan's zombie, or no plan this tick, leaves the ladder as it was.

Cost if wrong: a door opened on a second zombie the frames did not list; a goal dropped at a gate that would have
opened.
"""
import math

from agent.base.planner.edges import _across, _door_on, _edge_of, same_side, side_of
from agent.base.planner.policies import (AIM_LEG_S, DOOR_HELD_R, DOOR_POST_PACE, FLEE_HEALTH_FLOOR, WALK_DONE_R,
                                         _beyond, blocked, stand_post, target_id_ok, zdist)
from agent.base.pza1 import Aim, Interact
from agent.base.world import me_xy

DOOR_KINDS = ("door", "locked gate", "locked door", "window")


def portal_between(world, a, b, marked=frozenset(), inside=False):
    """Ruling P30-C's read (the module docstring): `(edge (holder, side), kind)` of the first door or window on the
    straight line from position `a` to `b`, else None (no portal, or a wall or fence met first). A door in `marked`
    (P24-Z's marked doors) reads locked; `inside` (the player on a room square), a locked building door reads `door`
    (#4367: `ToggleDoorActual` unlocks it for a player inside; F14's door (10770, 10633) opened so, map seq 10905; a
    door locked but not by key may still refuse, its `locked` end then marking it after two, P24-Z)."""
    seen = getattr(world, "door_seen", None) or {}
    for u, v in world.edge_steps(a, b):
        holder, side = _edge_of(u, v)
        door = _door_on(world, holder, side)
        if door is not None and holder in seen:
            door = dict(door, **{k: v for k, v in seen[holder].items() if v is not None})
        if door is not None and not door.get("open"):
            rooms = any((world.map.get(q) or {}).get("room") is not None for q in (u, v))
            if door.get("barricaded") or holder in marked or (door.get("locked") and not (inside and rooms)):
                return (holder, side), "locked door" if rooms else "locked gate"
            return (holder, side), "door"
        s = world.map.get(holder) or {}
        if door is None and s.get("window") is not None and s.get("edge" + side):
            return (holder, side), "window"
        if door is None and world.blocked(u, v):
            return None
    return None


def meets_portal(world, a, b, edge):
    """Fix 1 (review-t3 M1): the straight line from position `a` to `b` goes through the portal on `edge` (holder,
    side): it meets that portal first (`portal_between`, P24-Z's marked doors read locked, so a door the leave marked
    still reads there), or the first blocked step it meets lies on the portal's own run (the same row of edges, every
    one between them blocked: `_same_run`), where the path follower takes the portal (F14's goal walk to (10727, 10645)
    met the gate's fence at (10731, 10642) and stood stuck at the gate). A line that clears the run's end, or meets
    another wall, does not."""
    p = portal_between(world, a, b, world.marked_doors())
    if p is not None:
        return p[0] == edge
    for u, v in world.edge_steps(a, b):
        if world.blocked(u, v):
            return _same_run(world, _edge_of(u, v), edge)
    return False


def _same_run(world, hit, edge):
    """The blocked edge `hit` (holder, side) and the portal's `edge` lie on one run: the same side and row, the hit
    within DOOR_HELD_R of the portal along it (review-t3 re-review r1: a far hit on a long fence is no way through this
    portal), and every edge from one to the other mapped on both sides and blocked (a closed door's included; an
    unmapped gap reads no fence)."""
    (h, side), (p, pside) = hit, edge
    if side != pside or h[2] != p[2] or (side == "N" and h[1] != p[1]) or (side == "W" and h[0] != p[0]):
        return False
    k = 0 if side == "N" else 1
    lo, hi = sorted((h[k], p[k]))
    if hi - lo > DOOR_HELD_R:
        return False
    for c in range(lo, hi + 1):
        sq = (c, h[1], h[2]) if side == "N" else (h[0], c, h[2])
        other = _across(sq, side)
        if sq not in world.map or other not in world.map or not world.blocked(sq, other):
            return False
    return True


def door_post(world, edge, me):
    """The square the stance takes before the open: of the door's two squares the one on the player's side (`near`),
    one square on from it away from the door (`stand_post` when `near` is a room square, else `policies._beyond`), else
    `near` itself; `(post, near)`."""
    holder, side = edge
    across = _across(holder, side)
    player_low = side_of(edge, me) in ("N", "W")   # the player north (or west) of the edge: the square across
    near, far = (across, holder) if player_low else (holder, across)
    s = world.map.get(near) or {}
    if s.get("room") is not None:
        post = stand_post(world, (near, far), s.get("building"))
    else:
        post = _beyond(world, far, near)
    return (post if post is not None else near), near


class ThreatDoorHeld:
    """The threat branch's side of ruling P30-C (the module docstring): `Threat`'s mixin."""

    DOOR_HELD = True   # ruling P30-C (Plan 30 Task 3): the module docstring; off, no door read (the Fight's line within
                       # FIGHT_REACH and its reposition, P25-X's refusal, as before). In `survive.T14_SWITCHES`

    def _init_door_held(self):
        self.door_held_now = None   # this tick's `door_held` why {door, kind, n_behind, decision}, logged, else None
        self.door_open = None       # this tick's stance_open plan {zid, edge, door, post, near} for the Fight
        self._door_held_key = None  # the last decision read (door, decision, ids): logged again only when it changes
        self._door_opening = None   # the stance_open plan whose door the stance opened, while its zombie is across

    def _door_held_read(self):
        """The read and its decision (the module docstring), once a threat read, before the hold is counted."""
        self.door_held_now, self.door_open = None, None
        goals = self.goals
        goals.door_left = None
        if not self.DOOR_HELD:
            self._door_held_key, self._door_opening = None, None
            return
        me = me_xy(self.world)
        if self._door_meets(me):
            return
        inside = self.night.inside()
        dead = blocked(self.dead, self.clock())
        marked = self.world.marked_doors()
        groups = {}
        for zid, z in self.world.zombies.items():
            if zid in dead or z.get("x") is None or z.get("y") is None:
                continue
            d = zdist(self.world, z)
            if d > DOOR_HELD_R:
                continue
            p = portal_between(self.world, me, (z["x"], z["y"]), marked, inside)
            if p is not None:
                groups.setdefault(p, []).append((d, zid, z))
        if not groups:
            self._door_held_key = None
            return
        (edge, kind), zs = min(groups.items(), key=lambda kv: (min(e[0] for e in kv[1]), kv[0][0]))
        zs.sort(key=lambda e: (e[0], repr(e[1])))
        opens = (kind == "door" and len(zs) == 1 and self._health() >= FLEE_HEALTH_FLOOR and self._armed()
                 and self.world.can("interact") and self.world.can("aim") and target_id_ok(zs[0][1]))
        decision = "stance_open" if opens else "leave"
        if inside and not opens:
            self._door_held_key = None
            return   # inside, a `leave` is the inside hold's (the module docstring)
        holder = edge[0]
        rec = {"door": [holder[0], holder[1]], "kind": kind, "n_behind": len(zs), "decision": decision}
        key = (edge, decision, tuple(sorted(repr(e[1]) for e in zs)))
        if key != self._door_held_key:
            self.door_held_now = rec
        self._door_held_key = key
        if opens:
            post, near = door_post(self.world, edge, me)
            self.door_open = self._door_opening = {"zid": zs[0][1], "edge": edge, "door": holder, "post": post,
                                                   "near": near, "phase": None}
            return
        self._door_opening = None
        self._door_leave(edge, kind, zs, me)

    def _door_meets(self, me):
        """The opened door's `meet` (the module docstring): True, the plan handed on with phase `meet`, while the
        plan's door reads open (`World.door_seen`) and its zombie, listed, stands across the door's edge; else the plan
        dropped and False."""
        plan = self._door_opening
        if plan is None:
            return False
        z = self.world.zombies.get(plan["zid"])
        open_ = ((getattr(self.world, "door_seen", None) or {}).get(plan["door"]) or {}).get("open") is True
        if not open_ or z is None or z.get("x") is None or z.get("y") is None or same_side(
                plan["edge"], me, (z["x"], z["y"])):
            self._door_opening = None if open_ or z is None else plan
            return False
        self.door_open = dict(plan, phase="meet")
        return True

    def _door_leave(self, edge, kind, zs, me):
        """`leave` (the module docstring): the zombies behind edge-marked, the goal past the edge ended and its target
        marked, a `door` left marked held; the edge handed to the goal runner (`door_left`), whose continued walk
        (P30-B) takes no target past it."""
        self.goals.door_left = edge
        for _, zid, _ in zs:
            if target_id_ok(zid):
                self.edge_marks[zid] = edge
                self.unreachable[zid] = math.inf
        g = getattr(self.goals, "current", None)
        if hasattr(g, "stall_target") and g.running and self._goal_through(g, edge, me):
            g.cool = True
            g.mark_far(self.world)
            g.end("failed", "door held")
        if kind == "door":
            self.world.mark_door(edge[0], "held", "out")


    def _goal_through(self, g, edge, me):
        """Fix 1 (review-t3 M1): goal `g`'s way goes through the portal on `edge` (`meets_portal`) from the player to
        its target's centre (`stall_target`), or to its running walk's target (a leg or a route's step)."""
        points = []
        target = g.stall_target()
        if target is not None:
            points.append((target[0] + 0.5, target[1] + 0.5))
        a = g.last
        if a is not None and a.type == "walkTo" and not self.actions.done(a):
            points.append((a.args.get("x"), a.args.get("y")))
        return any(None not in pt and meets_portal(self.world, me, pt, edge) for pt in points)


class FightDoorHeld:
    """The Fight's side of ruling P30-C (the module docstring): `Fight`'s mixin; `door_open` the threat's plan, set on
    the Fight each tick it decides (None without one)."""

    door_open = None

    def _door_open_cmd(self, t):
        """The plan's step at the pin `t` (id, zombie, dist), else None: beyond WALK_DONE_R of the post square's centre
        the stance's leg toward it, facing the zombie, timed at DOOR_POST_PACE (a slower stance walk falls short and
        is re-aimed, never past the post into the door); at the post `Interact` open on the door; the door open and
        the zombie across, the stance standing facing it (`meet`)."""
        plan = self.door_open
        if plan is None or t[0] != plan["zid"]:
            return None
        zid, z, d = t
        post, door = plan["post"], plan["door"]
        mx, my = me_xy(self.world)
        cx, cy = post[0] + 0.5, post[1] + 0.5
        far = math.hypot(cx - mx, cy - my)
        self.why = {"target": zid, "pinned": True, "dist": d, "door": [door[0], door[1]],
                    "post": [post[0], post[1]]}
        if plan.get("phase") == "meet":
            self.why.update(door_step="meet", stance=True, leg="door_meet")
            return Aim(0.0, 0.0, AIM_LEG_S, targetId=zid)
        if far > WALK_DONE_R:
            self.why.update(door_step="post", stance=True, leg="door_post")
            return Aim((cx - mx) / far, (cy - my) / far, min(AIM_LEG_S, far / DOOR_POST_PACE), targetId=zid)
        self.why["door_step"] = "open"
        return Interact(door[0], door[1], "open")
