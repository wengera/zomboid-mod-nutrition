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
"""
import math

from agent.base.planner.policies import DISENGAGE_R, PREEMPTED, centre, door_edge
from agent.base.pza1 import WalkTo
from agent.base.world import me_floor, me_xy

__all__ = ["edge_read", "edge_why", "same_side", "FightEdge", "ThreatEdge", "GoalEdge"]


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
    """The first known blocked outdoor edge (holder, side) on the straight line from position `a` to `b`, else None.
    A diagonal step that reads blocked is read through its corner squares' legs, the first such edge on either."""
    z = me_floor(world)
    sqs = [(x, y, z) for x, y in world._bresenham(int(math.floor(a[0])), int(math.floor(a[1])),
                                                 int(math.floor(b[0])), int(math.floor(b[1])))]
    for p, q in zip(sqs, sqs[1:]):
        if p not in world.map or q not in world.map:
            continue
        if p[0] == q[0] or p[1] == q[1]:
            if _wall(world, p, q):
                return _edge_of(p, q)
            continue
        if not world.blocked(p, q):
            continue
        for c in ((q[0], p[1], z), (p[0], q[1], z)):
            for u, v in ((p, c), (c, q)):
                if c in world.map and _wall(world, u, v):
                    return _edge_of(u, v)
    return None


def _door_on(world, holder, side):
    """The door record on the edge `side` of square `holder`, else None."""
    s = world.map.get(holder) or {}
    if s.get("door") is None or not s.get("edge" + side):
        return None
    return s["door"]


def _passable(rec):
    return rec is not None and not rec.get("locked") and not rec.get("barricaded")


def _across(sq, side):
    """The square across the edge `side` of `sq` (north of it for "N", west of it for "W")."""
    return (sq[0], sq[1] - 1, sq[2]) if side == "N" else (sq[0] - 1, sq[1], sq[2])


def _run_ways(world, holder, side, reach):
    """The ways past the run of blocked `side` edges through `holder` (along x for a north edge, along y for a west
    one), out to `reach` tiles each way: `("door", sq)` for each square keeping an unlocked door record on it, and
    `("end", sq)` for the first square each way whose edge is crossable (not blocked, or hoppable: the run's end, walked
    round or climbed). A square, or the one across its edge, the map does not hold ends the read that way unread (an
    unscanned stretch is no way known)."""
    dx, dy = (1, 0) if side == "N" else (0, 1)
    out = []
    for sign, k0 in ((1, 0), (-1, 1)):
        k = k0
        while k <= reach:
            sq = (holder[0] + sign * k * dx, holder[1] + sign * k * dy, holder[2])
            other = _across(sq, side)
            if sq not in world.map or other not in world.map:
                break
            door = _passable(_door_on(world, sq, side))
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


def edge_read(world, a, b, reach):
    """Ruling P25-X: None when the straight line from position `a` to `b` crosses no known blocked outdoor edge, or
    crosses one whose run is walked round (its nearest way, `_run_ways` within `reach` of the crossing, is the run's
    end: iteration 15's walk round a wall and its reposition stand); else `{edge: (holder, side), door: the square
    keeping the unlocked door record that passes it, else None, via: the square on `b`'s side of that door, else
    None}`: the crossed edge's own door when it reads unlocked, else the nearest way to the player when it is a door;
    with no way within `reach` the edge is a wall (door None: refused or dropped). A locked or barricaded door record is
    wall."""
    edge = _crossed(world, a, b)
    if edge is None:
        return None
    holder, side = edge
    if _passable(_door_on(world, holder, side)):
        door = holder
    else:
        mx, my = me_xy(world)
        ways = _run_ways(world, holder, side, reach)
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
    (x, y, _), side = edge
    if side == "N":
        return (p[1] < y) == (q[1] < y)
    return (p[0] < x) == (q[0] < x)


class FightEdge:
    """The Fight's side of ruling P25-X (the module docstring): `edge_marks` (zombie id -> the edge it was refused
    across) Survive shares across its Fights, as `unreachable`."""

    def _edge_answer(self, t):
        """With the `blocked_edge` rule on, on an open-ground Fight (no corner, no door fight): target `t`'s line
        crossing a known blocked edge is routed (`("route", WalkTo)` of the door's far square at a run) when an unlocked
        door record passes it within DISENGAGE_R of the crossing (but for a chaser the pull draws, P24-AN: it walks
        away and the chaser comes round by the door), else refused (`("refuse", None)`: the target marked,
        `_mark_edge`); None with no such edge, or one walked round (`edge_read`). Sets `blocked_edge` for the why."""
        self._edge_send, self.blocked_edge = None, None
        if "blocked_edge" not in self.rules or self.point_blank or self.only is not None:
            return None
        zid, z, d = t
        read = edge_read(self.world, me_xy(self.world), (z["x"], z["y"]), DISENGAGE_R)
        if read is None:
            return None
        if read["via"] is None:
            self.blocked_edge = edge_why(read, "refuse")
            self._mark_edge(zid, read["edge"])
            return "refuse", None
        if self.pull_centroid(t) is not None:
            return None   # P24-AN's pull walks away from the group: the chaser comes round by the door itself
        self.blocked_edge = edge_why(read, "route")
        self._edge_send = (zid, read["edge"])
        self.why = {"target": zid, "pinned": True, "dist": d, "blocked_edge": self.blocked_edge}
        return "route", WalkTo(*centre(read["via"]), "run")

    def _mark_edge(self, zid, edge):
        """The target refused across `edge`: unreachable until `ThreatEdge._release_edges` reads it on the player's
        side, or the player on its (`edge_marks`; an infinite `unreachable` wall)."""
        self._marked_now.add(zid)
        self.unreachable[zid] = math.inf
        self.edge_marks[zid] = edge
        if zid == self.target:
            self._unpin()

    def _observe_edge_route(self):
        """A route walk (`_edge_walk`) that ended any way but done or superseded marks its target across its edge."""
        w = self._edge_walk
        if w is None or not self.actions.done(w[0]):
            return
        self._edge_walk = None
        a, zid, edge = w
        if a.state != "done" and not (a.state == "failed" and a.reason == PREEMPTED):
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
    """The goal legs' side of ruling P25-X (`goal_policies._Legs`): `_edge_cmd`."""

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
        read = edge_read(world, me_xy(world), (x, y), reach)
        if read is None:
            return None
        if read["via"] is None:
            self.why = dict(self.why, blocked_edge=edge_why(read, "drop"))
            self.cool = True
            self.end("failed", "blocked edge")
            return None
        self.leg = centre(read["via"])
        self.why = dict(self.why, blocked_edge=edge_why(read, "route"), leg=[self.leg[0], self.leg[1]])
        return WalkTo(self.leg[0], self.leg[1], "walk")
