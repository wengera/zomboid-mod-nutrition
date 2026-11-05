"""Known blocked edges (ruling P25-X, Plan 25 Task 14's amendment, survival iteration 16; E15,
`e_day_15-20261102-091322`: from game minute 627 to the cap at 785, 158 game minutes with no kill, twelve cycles of
stance, walk, blocked line, reposition `stuck` and a 20 s mark against one chasing zombie (8064) behind a locked
chain-link gate at (10756, 10642), while the goal layer's water loots and the need's fills, aimed beyond that fence,
kept walking the character back to it; an unlocked door record sat 9 tiles west at (10747, 10642)).

The seek's fence test (`World.fence_on_line`) and the fence wait (P25-F) read hoppable edges only. Here an outdoor
edge (between two mapped squares neither of which is a room square: a fence, a garden wall, a gate) that the map reads
blocked and not hoppable (`World.blocked`, also with `climb`) is a known blocked edge; a door record on it (the square
keeping that edge carries `door` with the edge's flag, `policies.door_edge`) is a way through when it reads neither
`locked` nor `barricaded`, else part of the wall. A building's walls are not read here: the Lua's path follower and
the shelter and loot routes own them, and the engage leaves a zombie inside a building alone (`Engage._side`).

- `edge_read(world, a, b, reach)`: the first known blocked edge the straight line from `a` to `b` crosses (Bresenham's
  on the floored ends, as `World.line_clear`), with the unlocked door record that passes it: the crossed edge's own,
  else the nearest way to the player along the same run of blocked edges within `reach` tiles of the crossing when it
  is a door (`via`, the square on `b`'s side of it, the route's walk target: the path follower opens a closed door on
  its path); a run whose nearest way is its end (walked round, or a hoppable stretch) reads None, iteration 15's walk
  round a wall and reposition standing; a run with no way known within `reach` is a wall.
- `first_edge(world, a, b)` (ruling P27-F, survival iteration 20): the edge the line from `a` toward `b` leaves `a`'s
  square by, the goal runner's stuck mark of a walk that ended `stuck` unmoved (`goal_runner.GoalRunner`).
- `FightEdge` (the Fight's mixin; rule `blocked_edge`): a target whose line crosses such an edge is routed through the
  door (`WalkTo` of `via`) or, with none within DISENGAGE_R, refused: marked unreachable until a frame reads it on the
  player's side of the edge or the player crosses to its side (`edge_marks`; never the UNREACHABLE_S mark), so no seek
  nor reposition is tried across it again. A route walk that fails marks it the same way.
- `ThreatEdge` (the threat branch's mixin): the marks' release, every tick. A marked zombie read on the far side of its
  edge is out of the hold (`EDGE_OUT_OF_HOLD`, Task 14 fix 1; `Survive._edge_out`, read by `_within`): the threat
  branch neither flees `unreachable` from it nor holds for it while it stays across, and it counts again the tick it
  reads on the player's side. The mark is only for a blocked, non-hoppable edge, so it cannot hop it.
- `GoalEdge` (the goal legs' mixin): a goal's target beyond such an edge is routed through the door (a leg to `via`,
  then the target) or the goal ends `failed "blocked edge"` (cooled: `cool`, as a leg's final failure).
Logged `blocked_edge` {edge: [x, y, side], door: [x, y] | None, action: refuse | route | drop} on the line (the
Fight's why, the goal's, the need's `fill`).

Ruling P29-A (`ROUTE_CROSS`, survival iteration 23; F13, `f_goals_14-20261105-021722`: 131.48134231567383 game minutes
at the closed, unlocked fence gate (10747, 10642), every route walk to its far square's centre (10747.5, 10642.5),
0.8629818220113737 tiles from where the character stood, inside the Lua walk's done radius, so it ended `done` on its
first tick unmoved and was read as "next", #4633), the goal's route (`GoalEdge`) and the Fight's (`FightEdge`, the
`route_cross` rule): the walk targets the square one step beyond the door's far square (`beyond_square`: the far
square plus the edge's unit normal, the shared `policies._beyond` read of an exit), the far square's centre only when
the map does not hold that square open; the Fight's route goes at a walk, never a run. A route leg's end is read by
whether it crossed (`same_side` of the leg's start and the frame's position), never by `done`: one ended `done` on its
start's side is the door's failure (`World.note_door_fail(door, "not crossed", "out")`, P24-Z's store: the second
within DOOR_RETRY_MIN marks the door), and `edge_read` with `marked` (the marked doors) reads a marked door as wall,
so the next route takes the run's next way, else the goal ends `failed "blocked edge"`, cooled, the Fight refuses its
target and the need's fill passes the source over (`water.Water`, fix 1's M2: the fill's route walk read the same
way). Logged `route` {door, target, beyond, start_side} on the route's send and `route_end` {door, crossed,
noted, next: the way the route reads now or None, dropped: no way left} on the line that reads the leg's end.
Fix 1 (review-t1 m1): every end of a route walk but a supersede is read by its side, so one that ended `failed` on its
start's side notes the door too; its goal is still decided by the leg's own logic (`_Legs._leg_ended`: no hop,
`_leg_failed` cools it and marks its far target) and the Fight still marks its target across the edge, and a goal walk
that ended `failed "stuck"` unmoved is also the runner's P27-F stuck mark (`goal_runner.GoalRunner._read_walks`): the
two reads fire on one walk in separate stores, the door's failure count (`World.door_fails`, `door_marks`) and the
square's mark (`stuck_marks`). A route record is read only against its own walk (the target the record names) and is
dropped at the next route read (review-t1 m2), so a later leg's end is never read against a superseded route's start.
The goal reads a route leg's end on the first tick its branch runs after it (review-t1 m3: only a hold that sends
nothing delays it, under GOAL_HOLD_SUPERSEDE_TICKS, the character barely moving meanwhile).
"""
import math

from agent.base.planner.policies import DISENGAGE_R, PREEMPTED, _beyond, centre
from agent.base.pza1 import WalkTo
from agent.base.world import me_xy

__all__ = ["edge_read", "edge_why", "same_side", "crossed", "first_edge", "beyond_square", "side_of", "route_target",
           "route_record", "route_why", "read_route_end", "FightEdge", "ThreatEdge", "GoalEdge"]


def _edge_of(p, q):
    """(the square keeping the edge between orthogonal neighbours `p` and `q`, "N" or "W")."""
    if q[1] == p[1] - 1:
        return p, "N"
    if q[1] == p[1] + 1:
        return q, "N"
    if q[0] == p[0] - 1:
        return p, "W"
    return q, "W"


def _wall(world, p, q):
    """The orthogonal step p -> q crosses a known blocked outdoor edge: both squares mapped and no room square,
    blocked, and blocked with `climb` too (not hoppable)."""
    sp, sq = world.map.get(p), world.map.get(q)
    if sp is None or sq is None or sp.get("room") is not None or sq.get("room") is not None:
        return False
    return world.blocked(p, q) and world.blocked(p, q, climb=True)


def _crossed(world, a, b):
    """The first known blocked outdoor edge (holder, side) on the straight line from position `a` to `b`, else None:
    the first of `World.edge_steps` (a diagonal step through its corner squares' legs) that is a wall (`_wall`). A
    diagonal with a wall on a leg reads blocked (`World.blocked`'s diagonal reads both legs of each corner), so the
    diagonal's own blocked read is not needed. Public as `crossed` (Plan 26, ruling CF-1 of Plan 25's close): the
    frozen grades read `_crossed` through `gates_e` (`grade_e13`, which `grade_e14` and `grade_e15` call), which keeps
    its name for them; the public name waits for the next grade module, which imports `crossed`."""
    for u, v in world.edge_steps(a, b):
        if _wall(world, u, v):
            return _edge_of(u, v)
    return None


crossed = _crossed   # the public name (Plan 26, ruling CF-1): no importer yet; the next grade module takes it


def first_edge(world, a, b):
    """Ruling P27-F: the edge (holder, side) the straight line from position `a` toward `b` leaves `a`'s square by (the
    first of `World.edge_steps`, a diagonal's first corner leg), else None (the line stays on the square, or its first
    step is on unmapped ground): the route a goal walk that ended `stuck` unmoved could not take."""
    start = (int(math.floor(a[0])), int(math.floor(a[1])))
    step = next(iter(world.edge_steps(a, b)), None)
    if step is None or step[0][:2] != start:
        return None
    return _edge_of(*step)


def _door_on(world, holder, side):
    """The door record on the edge `side` of square `holder`, else None."""
    s = world.map.get(holder) or {}
    if s.get("door") is None or not s.get("edge" + side):
        return None
    return s["door"]


def _passable(world, sq, side, marked=frozenset()):
    """The door record on the edge `side` of square `sq` is a way through: neither `locked` nor `barricaded`, and the
    door not in `marked` (ruling P29-A: a door marked within DOOR_RETRY_MIN, `World.marked_doors`, is wall)."""
    rec = _door_on(world, sq, side)
    return rec is not None and not rec.get("locked") and not rec.get("barricaded") and sq not in marked


def _across(sq, side):
    """The square across the edge `side` of `sq` (north of it for "N", west of it for "W")."""
    return (sq[0], sq[1] - 1, sq[2]) if side == "N" else (sq[0] - 1, sq[1], sq[2])


def _run_ways(world, holder, side, reach, marked=frozenset()):
    """The ways past the run of blocked `side` edges through `holder` (along x for a north edge, along y for a west
    one), out to `reach` tiles each way: `("door", sq)` for each square keeping an unlocked door record on it, and
    `("end", sq)` for the first square each way whose edge is crossable (not blocked, or hoppable: the run's end, walked
    round or climbed). A square, or the one across its edge, the map does not hold ends the read that way unread (an
    unscanned stretch is no way known). A door in `marked` is wall (P29-A)."""
    dx, dy = (1, 0) if side == "N" else (0, 1)
    out = []
    for sign, k0 in ((1, 0), (-1, 1)):
        k = k0
        while k <= reach:
            sq = (holder[0] + sign * k * dx, holder[1] + sign * k * dy, holder[2])
            other = _across(sq, side)
            if sq not in world.map or other not in world.map:
                break
            door = _passable(world, sq, side, marked)
            if door:
                out.append(("door", sq))
            if not world.blocked(other, sq, climb=True):
                if not door:
                    out.append(("end", sq))
                break
            k += 1
    return out


def _via(holder, side, b):
    """The square on position `b`'s side of the edge `side` of `holder`: the one the route walks to."""
    if side == "N":
        return holder if b[1] >= holder[1] else (holder[0], holder[1] - 1, holder[2])
    return holder if b[0] >= holder[0] else (holder[0] - 1, holder[1], holder[2])


def edge_read(world, a, b, reach, marked=frozenset()):
    """Ruling P25-X: None when the straight line from position `a` to `b` crosses no known blocked outdoor edge, or
    crosses one whose run is walked round (its nearest way, `_run_ways` within `reach` of the crossing, is the run's
    end: iteration 15's walk round a wall and its reposition stand); else `{edge: (holder, side), door: the square
    keeping the unlocked door record that passes it, else None, via: the square on `b`'s side of that door, else
    None}`: the crossed edge's own door when it reads unlocked, else the nearest way to the player when it is a door;
    with no way within `reach` the edge is a wall (door None: refused or dropped). A locked or barricaded door record is
    wall, and so is a door square in `marked` (ruling P29-A: the route's callers pass `World.marked_doors()`)."""
    edge = _crossed(world, a, b)
    if edge is None:
        return None
    holder, side = edge
    if _passable(world, holder, side, marked):
        door = holder
    else:
        mx, my = me_xy(world)
        ways = _run_ways(world, holder, side, reach, marked)
        way = min(ways, key=lambda w: (math.hypot(w[1][0] + 0.5 - mx, w[1][1] + 0.5 - my), w)) if ways else None
        if way is not None and way[0] == "end":
            return None
        door = None if way is None else way[1]
    return {"edge": edge, "door": door, "via": None if door is None else _via(door, side, b)}


def edge_why(read, action):
    """The `blocked_edge` why of `read` (`edge_read`'s) under `action` (refuse, route or drop)."""
    (x, y, _), side = read["edge"]
    door = read["door"]
    return {"edge": [x, y, side], "door": None if door is None else [door[0], door[1]], "action": action}


def same_side(edge, p, q):
    """Positions `p` and `q` lie on one side of the line the edge `(holder, side)` runs along (a north edge's y, a west
    edge's x)."""
    return side_of(edge, p) == side_of(edge, q)


def side_of(edge, p):
    """The side of the edge `(holder, side)`'s line position `p` lies on: "N" or "S" of a north edge, "W" or "E" of a
    west edge (ruling P29-A: a route leg's start side, logged)."""
    (x, y, _), side = edge
    if side == "N":
        return "N" if p[1] < y else "S"
    return "W" if p[0] < x else "E"


def beyond_square(world, far, edge):
    """Ruling P29-A: the square one step beyond the route's far square `far` across the door's edge `(door, side)`, the
    far square plus the edge's unit normal, when the map holds it open (`policies._beyond`, the exit's read: mapped,
    not solid nor `solidTrans`, no room, the step from `far` not blocked), else None. The shared helper, not a copy."""
    door, side = edge
    near = _across(door, side) if far == door else door
    return _beyond(world, near, far)


def route_target(world, read):
    """Ruling P29-A: `(the route walk's target (x, y), beyond)` of an `edge_read` read with a way (`via`): the centre of
    `beyond_square` when the map holds it open (beyond True), else the far square's centre (beyond False)."""
    sq = beyond_square(world, read["via"], (read["door"], read["edge"][1]))
    return (centre(sq), True) if sq is not None else (centre(read["via"]), False)


def route_record(world, read, start):
    """P29-A's route record of an `edge_read` read with a way, the leg starting at `start`: `{edge: the door's (door,
    side), door, start, target, beyond}` (the goal's, the Fight's and the need's fill's route walks)."""
    target, beyond = route_target(world, read)
    return {"edge": (read["door"], read["edge"][1]), "door": read["door"], "start": start, "target": target,
            "beyond": beyond}


def route_why(route):
    """The `route` why of a route record (`route_record`): {door: [x, y], target: [x, y], beyond, start_side}."""
    door, target = route["door"], route["target"]
    return {"door": [door[0], door[1]], "target": [target[0], target[1]], "beyond": route["beyond"],
            "start_side": side_of(route["edge"], route["start"])}


def read_route_end(world, route, toward, reach):
    """Ruling P29-A: the end of a route leg (`route_record`'s record) that ended `done`, read by whether it crossed (the
    frame's position on the other side of the door's edge from the leg's start): one on the start's side notes the
    door's failure (`World.note_door_fail(door, "not crossed", "out")`). Returns the `route_end` why {door, crossed,
    noted, next, dropped}: `next` the door the route reads now toward `toward` within `reach` (the marked doors wall),
    else None, `dropped` True when that read finds the edge with no way left."""
    me = me_xy(world)
    crossed = not same_side(route["edge"], route["start"], me)
    if not crossed:
        world.note_door_fail(route["door"], "not crossed", "out")
    read = edge_read(world, me, toward, reach, marked=world.marked_doors())
    door = None if read is None else read["door"]
    return {"door": [route["door"][0], route["door"][1]], "crossed": crossed, "noted": not crossed,
            "next": None if door is None else [door[0], door[1]], "dropped": read is not None and door is None}


class FightEdge:
    """The Fight's side of ruling P25-X (the module docstring): `edge_marks` (zombie id -> the edge it was refused
    across) Survive shares across its Fights, as `unreachable`."""

    def _edge_answer(self, t):
        """With the `blocked_edge` rule on, on an open-ground Fight (no corner, no door fight): target `t`'s line
        crossing a known blocked edge is routed (`("route", WalkTo)` of the door's far square at a run) when an unlocked
        door record passes it within DISENGAGE_R of the crossing (but for a chaser the pull draws, P24-AN: it walks
        away and the chaser comes round by the door), else refused (`("refuse", None)`: the target marked,
        `_mark_edge`); None with no such edge, or one walked round (`edge_read`). Sets `blocked_edge` for the why.
        With the `route_cross` rule on (ruling P29-A, the module docstring): a marked door is wall, the walk goes at a
        walk to `route_target`'s square (the step beyond the far square when open), logged `route`."""
        self._edge_send, self.blocked_edge = None, None
        if "blocked_edge" not in self.rules or self.point_blank or self.only is not None:
            return None
        zid, z, d = t
        cross = "route_cross" in self.rules
        me = me_xy(self.world)
        read = edge_read(self.world, me, (z["x"], z["y"]), DISENGAGE_R,
                         marked=self.world.marked_doors() if cross else frozenset())
        if read is None:
            return None
        if read["via"] is None:
            self.blocked_edge = edge_why(read, "refuse")
            self._mark_edge(zid, read["edge"])
            return "refuse", None
        if self.pull_centroid(t) is not None:
            return None   # P24-AN's pull walks away from the group: the chaser comes round by the door itself
        self.blocked_edge = edge_why(read, "route")
        self.why = {"target": zid, "pinned": True, "dist": d, "blocked_edge": self.blocked_edge}
        if not cross:
            self._edge_send = (zid, read["edge"], None)
            return "route", WalkTo(*centre(read["via"]), "run")
        route = route_record(self.world, read, me)
        self._edge_send = (zid, read["edge"], route)
        self.why["route"] = route_why(route)
        return "route", WalkTo(route["target"][0], route["target"][1], "walk")   # P29-A: never a run

    def _mark_edge(self, zid, edge):
        """The target refused across `edge`: unreachable until `ThreatEdge._release_edges` reads it on the player's
        side, or the player on its (`edge_marks`; an infinite `unreachable` wall)."""
        self._marked_now.add(zid)
        self.unreachable[zid] = math.inf
        self.edge_marks[zid] = edge
        self._drop_pin_read()   # the tick's `_pin_free` leaves the refused zombie out (fix 3, minor 4)
        if zid == self.target:
            self._unpin()

    def _observe_edge_route(self):
        """A route walk (`_edge_walk`) that ended any way but done or superseded marks its target across its edge. One
        sent under `route_cross` (P29-A) that ended any way but superseded is read by whether it crossed
        (`read_route_end` toward its target, kept in `_route_end` for the next choose's why): an uncrossed one notes
        the door, a failed one marks its target as well (fix 1, m1)."""
        w = self._edge_walk
        if w is None or not self.actions.done(w[0]):
            return
        self._edge_walk = None
        a, zid, edge, route = w
        preempted = a.state == "failed" and a.reason == PREEMPTED
        if route is not None and not preempted:
            z = self.world.zombies.get(zid) or {}
            toward = (z["x"], z["y"]) if z.get("x") is not None and z.get("y") is not None else route["target"]
            self._route_end = read_route_end(self.world, route, toward, DISENGAGE_R)
        if a.state != "done" and not preempted:
            self._mark_edge(zid, edge)


class ThreatEdge:
    """The threat branch's side of ruling P25-X: `edge_marks` released."""

    def _release_edges(self):
        """Each edge mark (`FightEdge._mark_edge`) released once its zombie is gone from the World or read on the
        player's side of its edge (it came round, or the player crossed): its infinite `unreachable` wall dropped."""
        if not self.edge_marks:
            return
        me = me_xy(self.world)
        for zid, edge in list(self.edge_marks.items()):
            z = self.world.zombies.get(zid)
            if z is not None and z.get("x") is not None and z.get("y") is not None and not same_side(
                    edge, me, (z["x"], z["y"])):
                continue
            del self.edge_marks[zid]
            if self.unreachable.get(zid) == math.inf:
                del self.unreachable[zid]


class GoalEdge:
    """The goal legs' side of ruling P25-X (`goal_policies._Legs`): `_edge_cmd`; and of ruling P29-A: `edge_route`,
    the running route leg's record (`route_record`'s, with the goal's `toward` and the `reach`), read at its end by
    `_route_ended`."""

    def _edge_cmd(self, world, x, y, reach):
        """With the kit's `blocked_edge` on: the goal's target (x, y) beyond a known blocked edge is routed through
        the unlocked door record that passes it within `reach` (the goal's leg length) of the crossing, a leg (`leg`, so
        its end reads as one) at a walk to the door's far square, returned; with none the goal ends `failed "blocked
        edge"`, cooled, and None is returned (the caller reads `running`). None with no such edge. The read is of the
        whole straight line to the goal's target, not the leg (`edge_read` walks Bresenham's to (x, y), 150 tiles off
        if need be): a blocked edge anywhere on it routes or drops the goal now, a far crossing dropping it early
        (judged acceptable in Task 14's review, minor 5: the goal would meet the same wall on its way; a crossing read
        within the leg only would route round it later, at the cost of the retries a `via` beyond the loaded grid
        takes down to LEG_MIN)."""
        if not self.kit.blocked_edge:
            return None
        self.edge_route = None   # fix 1, m2: a superseded route's record is never read against a later leg
        cross = self.kit.route_cross
        me = me_xy(world)
        read = edge_read(world, me, (x, y), reach, marked=world.marked_doors() if cross else frozenset())
        if read is None:
            return None
        if read["via"] is None:
            self.why = dict(self.why, blocked_edge=edge_why(read, "drop"))
            self.cool = True
            self.end("failed", "blocked edge")
            return None
        if not cross:
            self.leg = centre(read["via"])
            self.why = dict(self.why, blocked_edge=edge_why(read, "route"), leg=[self.leg[0], self.leg[1]])
            return WalkTo(self.leg[0], self.leg[1], "walk")
        route = route_record(world, read, me)   # P29-A: the step beyond the far square when open
        self.edge_route = dict(route, toward=(x, y), reach=reach)
        self.leg = route["target"]
        self.why = dict(self.why, blocked_edge=edge_why(read, "route"), leg=[self.leg[0], self.leg[1]],
                        route=route_why(route))
        return WalkTo(self.leg[0], self.leg[1], "walk")

    def _route_ended(self, world, action):
        """Ruling P29-A: the running route leg's (`edge_route`) end, `action` its walk. None when no route leg ran,
        `action` is not its walk (its target not the record's) or was superseded; else its end read by whether it
        crossed (`read_route_end`, kept in `route_end` for the runner's why: an uncrossed one notes the door, fix 1's m1
        a `failed` one too), then None for a walk that ended other than done (the caller reads the leg as before: the
        module docstring's stuck-mark interplay), else "next" (the next choose routes by the way it reads now, or walks
        on once crossed), the goal first ended `failed "blocked edge"`, cooled, when the read finds no way left."""
        route, self.edge_route = self.edge_route, None
        if route is None or (action.args.get("x"), action.args.get("y")) != tuple(route["target"]):
            return None
        if action.state == "failed" and action.reason == PREEMPTED:
            return None
        end = read_route_end(world, route, route["toward"], route["reach"])
        self.route_end = end
        if action.state != "done":
            return None
        if end["dropped"]:
            self.why = dict(self.why, route_end=end)
            self.cool = True
            self.end("failed", "blocked edge")
        return "next"
