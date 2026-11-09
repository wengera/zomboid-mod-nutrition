"""The group's entry and the drag guard (Plan 33 Task 3, the spec's § 3.3; F18, `f_goals_18-20261108-235005`: while the
finish stalled, three standing zombies, 13648, 13651 and 13653, walked in from 11.6 to 12.0 tiles and closed to 0.45 to
0.9 tiles with the character in open ground; the drag-down guard (`Threat._drag`, ruling P24-A (h)) then sent fourteen
`flee:many` lines (402 to 415) with five run steers while no frame read the character moving for 116 frames, seq 3512
to 3655, every one under a hit reaction; the runs' headings pointed into a zombie standing at the character's side, the
visual pass's shots 37 to 41, and the character died in the drag-down at game minute 617). Angus's direction (memories
`combat-approach-not-flee`, `stand-and-fight-dress-first`): one zombie is never a reason to flee; a group is left
before it closes, never by running into it.

`Threat`'s mixin, its state `Survive`'s own (`Survive.__init__`), its constants `policies.py`'s, its switches
`Threat`'s (`survive.T18_SWITCHES`); `_group_read` is the tick's bookkeeping, read at `Threat._threat_read`'s start:

- `GROUP_LEAVE` (`_group_leave`, `_leave_answer`): two or more standing zombies within GROUP_ENTRY_R, each nearer than on
  the decision line before (closing), with nothing at the character's back within WALL_R (`back_cover`: a known wall
  or fence edge, a door record, a solid square) and the character out in the open (not on a room square, not
  sheltered): the threat plan's `flee` row with reason `leave`, the leave leg. Its leg is the Flee's walk to the nearest
  known building door whose approach square is within LEAVE_R and whose verdict reads `ok` (`Flee.door_verdicts`), the
  doorway stand resumed there (the Flee's `stand_ok`, P24-AO); with none, a run away from the closing group's centroid
  for LEAVE_S, turned by 30-degree steps to the first heading the map reads clear over STEER_PROBE. Never with a
  standing zombie within FIGHT_REACH (POINT_BLANK_FIGHT and the meet then stand; one between FIGHT_REACH and
  GROUP_ENTRY_R is outrun) nor under FLEE_HEALTH_FLOOR (the health flee's),
  logged `group_leave` {withheld: keep_r | cover} when two close then. The leave holds while two or more stand within
  GROUP_ENTRY_R (the run's leg) or, on the door's walk, within DANGER_R; it ends at the doorway (the stand's row,
  `Threat._doorway`, answers first), at a standing zombie within FIGHT_REACH, or under the floor. Fix 1 (the
  coordinator's ruling on F18: within GROUP_NEAR_R and outside KEEP_R the entry window was half a tile, and every
  two-closing line of F18 and the goldens read a zombie within KEEP_R): the entry radius GROUP_ENTRY_R, the exception
  at FIGHT_REACH.
  Logged `group_leave` {leg door | steer, closing | n, door}.
- `DRAG_GUARD_FIGHT` (`_drag_fight`, `_drag_shove`): the drag-down guard's flee, when the frame reads a hit reaction
  (`me.hitReaction` non-empty) or STUCK_FRAMES frames of `me.moving` false while a steer or a walk is the running
  action (`_drag_stuck`), shoves the nearest standing zombie within SHOVE_R in front of the character (within 90 degrees
  of `me.lookAngle`; else the nearest within SHOVE_R) in the run's place, the shove being the one press the engine takes
  at the reaction's end (#4372); the read latches (`drag_latch`) until a frame reads the character moving, so a run is
  sent only once it has moved. Logged `drag_fight` {target, dist, why hit | stuck | latched}.
- `SIDE_CLEAR` (`_side_clear`): no run steer the threat branch answers passes within SIDE_R of a standing zombie over
  its first SIDE_LOOK tiles (`side_hits`: ahead of the player, within SIDE_R of the leg's segment); the heading is turned
  by 30-degree steps both ways, nearest first, to the first heading clear of them and of the map (then clear of them
  alone), else the shove of `_front_shove_target` is sent in its place (else the steer is kept). Logged `side_clear`
  {turn, near, shove}.
"""
import math

from agent.base.planner.policies import (DANGER_R, DISENGAGE_R, FIGHT_REACH, FLEE_GAIT, FLEE_HEALTH_FLOOR, GROUP_ENTRY_R,
                                         LEAVE_R, LEAVE_S, SHOVE_R, SIDE_LOOK, SIDE_R, STEER_PROBE, STUCK_FRAMES,
                                         WALL_R, _rotate, blocked, clear_heading, hit_reaction, on_floor, target_id_ok,
                                         zdist)
from agent.base.pza1 import Shove, Steer
from agent.base.world import me_floor, me_xy

__all__ = ["ThreatGroup", "SIDE_TURNS", "side_hits", "back_cover"]

SIDE_TURNS = (30, -30, 60, -60, 90, -90, 120, -120, 150, -150, 180)   # degrees a heading turns, nearest first
ROAMING = ("steer", "walkTo")   # the running actions under which an unmoving frame counts toward STUCK_FRAMES


def side_hits(world, v, zs):
    """The ids of `zs` ((id, zombie) pairs) a leg from the player along unit `v` passes within SIDE_R of over its first
    SIDE_LOOK tiles: ahead of the player (the projection on `v` above 0: one abeam or behind is left by the leg) and
    within SIDE_R of the leg's segment."""
    mx, my = me_xy(world)
    out = []
    for zid, z in zs:
        dx, dy = z["x"] - mx, z["y"] - my
        t = dx * v[0] + dy * v[1]
        if t <= 0.0:
            continue
        perp = abs(dx * v[1] - dy * v[0])
        d = perp if t <= SIDE_LOOK else math.hypot(t - SIDE_LOOK, perp)
        if d < SIDE_R:
            out.append(zid)
    return out


def _seg_dist(p, a, b):
    """Tiles from point `p` to the segment `a`-`b`."""
    ax, ay = b[0] - a[0], b[1] - a[1]
    L2 = ax * ax + ay * ay
    t = 0.0 if L2 == 0.0 else max(0.0, min(1.0, ((p[0] - a[0]) * ax + (p[1] - a[1]) * ay) / L2))
    return math.hypot(p[0] - a[0] - t * ax, p[1] - a[1] - t * ay)


def _box_dist(p, x, y):
    """Tiles from point `p` to the square (x, y)'s box."""
    return math.hypot(max(x - p[0], 0.0, p[0] - x - 1), max(y - p[1], 0.0, p[1] - y - 1))


def back_cover(world, away):
    """GROUP_LEAVE's back read: `{kind, at}` of the first known feature within WALL_R of the player on its back side (its
    centre's offset from the player along unit `away` above 0: away from the closing group), else None. The features:
    a blocked edge (`blockN` or `blockW` True on a mapped square: a wall, a fence, a closed door's edge), `wall`, `at` the
    holder square and its side; a square carrying a `door` record, `door`; a `solid` or `solidTrans` square, `solid`. An
    unmapped square is no cover (the open ground the rule leaves)."""
    p = me_xy(world)
    fz = me_floor(world)
    px, py = int(math.floor(p[0])), int(math.floor(p[1]))
    reach = int(math.ceil(WALL_R)) + 1
    for x in range(px - reach, px + reach + 1):
        for y in range(py - reach, py + reach + 1):
            s = world.map.get((x, y, fz))
            if s is None:
                continue
            feats = []
            if s.get("blockN") is True:
                feats.append(("wall", [x, y, "N"], (x + 0.5, y), _seg_dist(p, (x, y), (x + 1, y))))
            if s.get("blockW") is True:
                feats.append(("wall", [x, y, "W"], (x, y + 0.5), _seg_dist(p, (x, y), (x, y + 1))))
            if s.get("door") is not None:
                feats.append(("door", [x, y], (x + 0.5, y + 0.5), _box_dist(p, x, y)))
            if s.get("solid") or s.get("solidTrans"):
                feats.append(("solid", [x, y], (x + 0.5, y + 0.5), _box_dist(p, x, y)))
            for kind, at, mid, d in feats:
                if d <= WALL_R and (mid[0] - p[0]) * away[0] + (mid[1] - p[1]) * away[1] > 0.0:
                    return {"kind": kind, "at": at}
    return None


def _unit(dx, dy):
    n = math.hypot(dx, dy)
    return (1.0, 0.0) if n == 0.0 else (dx / n, dy / n)


class ThreatGroup:
    """The threat branch's group rules (the module docstring): `Threat`'s mixin."""

    def _group_standing(self, r):
        """(id, zombie, tiles) of each listed zombie standing (not `onFloor`) within `r` tiles, nearest first; one read
        dead or out of the hold across its blocked edge left out (`Survive._within`'s set)."""
        dead = blocked(self.dead, self.clock()) | self._edge_out()
        out = []
        for zid, z in self.world.zombies.items():
            if zid in dead or z.get("x") is None or z.get("y") is None or on_floor(z):
                continue
            d = zdist(self.world, z)
            if d <= r:
                out.append((zid, z, d))
        return sorted(out, key=lambda e: (e[2], repr(e[0])))

    def _group_read(self):
        """The tick's group bookkeeping, before the decision (`Threat._threat_read`): this tick's whys cleared; the
        closing read (`_group_closing`: the standing zombies within GROUP_ENTRY_R each nearer than on the line before,
        `_group_prev` their distances within DISENGAGE_R, kept for the next line); the unmoving count's start
        (`_still_n0`: the World's `frame_n` of the first tick reading `me.moving` false while a steer or a walk runs,
        reset by any other) and the drag latch's release on a frame reading the character moving."""
        self.group_leave, self.drag_fight, self.side_clear = None, None, None
        near = self._group_standing(DISENGAGE_R)
        prev = self._group_prev
        self._group_closing = [(zid, z, d) for zid, z, d in near
                               if d <= GROUP_ENTRY_R and zid in prev and d < prev[zid]]
        self._group_prev = {zid: d for zid, _, d in near}
        if (self.world.me or {}).get("moving") is True:
            self._still_n0, self.drag_latch = None, False
            return
        cur = self.actions.current
        if cur is not None and cur.type in ROAMING:
            if self._still_n0 is None:
                self._still_n0 = self.world.frame_n
        else:
            self._still_n0 = None

    # ------------------------------------------------------------------------------------------ DRAG_GUARD_FIGHT
    def _drag_stuck(self):
        """STUCK_FRAMES frames since the first tick that read the character unmoving under a running steer or walk."""
        return self._still_n0 is not None and self.world.frame_n - self._still_n0 >= STUCK_FRAMES

    def _front_shove_target(self):
        """(id, zombie, tiles) of the nearest standing zombie a Fight may target within SHOVE_R in front of the player
        (its offset within 90 degrees of `me.lookAngle`, read when a number), else of the nearest within SHOVE_R, else
        None."""
        zs = [e for e in self._group_standing(SHOVE_R) if target_id_ok(e[0])]
        if not zs:
            return None
        look = (self.world.me or {}).get("lookAngle")
        if isinstance(look, (int, float)) and not isinstance(look, bool):
            mx, my = me_xy(self.world)
            fx, fy = math.cos(look), math.sin(look)
            front = [e for e in zs if (e[1]["x"] - mx) * fx + (e[1]["y"] - my) * fy >= 0.0]
            if front:
                return front[0]
        return zs[0]

    def _drag_fight(self):
        """DRAG_GUARD_FIGHT's read on a tick the drag-down guard flees (the module docstring): `{target, dist, why}` of
        the shove in the run's place, else None (the rule off, no hit reaction nor unmoving count nor latch, or no
        standing zombie within SHOVE_R: the guard's run as before)."""
        if not self.DRAG_GUARD_FIGHT:
            return None
        hit = hit_reaction(self.world) is not None
        stuck = self._drag_stuck()
        if not (hit or stuck or self.drag_latch):
            return None
        self.drag_latch = True
        t = self._front_shove_target()
        if t is None:
            return None
        self.drag_fight = {"target": t[0], "dist": t[2], "why": "hit" if hit else ("stuck" if stuck else "latched")}
        return self.drag_fight

    def _drag_shove(self, flee):
        """The Flee's answer under DRAG_GUARD_FIGHT: its own shove still running held, else the shove at the read's
        target (superseding a running run); None with no read this tick."""
        if self.drag_fight is None:
            return None
        if flee.busy() and flee.last.type == "shove":
            self.why = {"holding": flee.last.aid}
            return flee, None
        self.why = {"shove": "drag", "target": self.drag_fight["target"]}
        return flee, Shove(self.drag_fight["target"])

    # ------------------------------------------------------------------------------------------------- SIDE_CLEAR
    def _side_zombies(self):
        return [(zid, z) for zid, z, _ in self._group_standing(SIDE_LOOK + SIDE_R)]

    def _side_turn(self, v, zs):
        """The first of SIDE_TURNS whose heading off unit `v` passes no zombie of `zs` (`side_hits`) and reads clear on
        the map over STEER_PROBE, else the first passing none, else None."""
        for need_map in (True, False):
            for turn in SIDE_TURNS:
                h = _rotate(v, turn)
                if side_hits(self.world, h, zs):
                    continue
                if need_map and not clear_heading(self.world, h, STEER_PROBE, self.TRANS):
                    continue
                return turn
        return None

    def _side_clear(self, ans):
        """SIDE_CLEAR (the module docstring) over the threat branch's answer `ans`: a run steer whose leg passes a
        standing zombie turned to the nearest clear heading, else the shove; any other answer as it is."""
        if not self.SIDE_CLEAR or ans is None or ans[1] is None or ans[1].TYPE != "steer" or ans[1].gait != FLEE_GAIT:
            return ans
        policy, cmd = ans
        v = _unit(cmd.vx, cmd.vy)
        zs = self._side_zombies()
        hits = side_hits(self.world, v, zs)
        if not hits:
            return ans
        turn = self._side_turn(v, zs)
        if turn is not None:
            h = _rotate(v, turn)
            self.side_clear = {"turn": turn, "near": hits}
            return policy, Steer(h[0], h[1], cmd.seconds, cmd.gait)
        t = self._front_shove_target()
        self.side_clear = {"turn": None, "near": hits, "shove": None if t is None else t[0]}
        return ans if t is None else (policy, Shove(t[0]))

    # ------------------------------------------------------------------------------------------------ GROUP_LEAVE
    def _group_leave(self, inside):
        """GROUP_LEAVE's row (the module docstring): True when the tick takes the leave (a new one, or the running one
        held), else False, `leave` cleared when its end is read; `group_leave` the why either way."""
        if not self.GROUP_LEAVE or inside or self.sheltered or self._health() < FLEE_HEALTH_FLOOR:
            self.leave = None
            return False
        keep = self._group_standing(FIGHT_REACH)   # fix 1: FIGHT_REACH, KEEP_R before
        if self.leave is not None:
            door_leg = self.flee is not None and self.flee.plan is not None
            n = len(self._group_standing(DANGER_R if door_leg else GROUP_ENTRY_R))
            if keep or n < 2:
                self.leave = None
                self.group_leave = {"end": "fight_reach" if keep else "strung", "n": n}
                return False
            self.group_leave = {"n": n}
            return True
        closing = self._group_closing
        if len(closing) < 2:
            return False
        ids = [zid for zid, _, _ in closing]
        if keep:
            self.group_leave = {"withheld": "fight_reach", "closing": ids, "near": keep[0][2]}
            return False
        mx, my = me_xy(self.world)
        cx = sum(z["x"] for _, z, _ in closing) / len(closing)
        cy = sum(z["y"] for _, z, _ in closing) / len(closing)
        cover = back_cover(self.world, _unit(mx - cx, my - cy))
        if cover is not None:
            self.group_leave = {"withheld": "cover", "closing": ids, "cover": cover}
            return False
        self.leave = {"since": self.clock(), "closing": ids}
        self.group_leave = {"closing": ids}
        return True

    def _leave_door(self, flee, held):
        """The door the leave walks to: the Flee's running plan's, else the nearest door `Flee.door_verdicts` reads `ok`
        whose approach square is within LEAVE_R while the Flee has not picked yet (a Flee that picked and dropped its
        plan runs the leave's own run); else None."""
        if flee.plan is not None:
            return flee.door()
        if flee.picked:
            return None
        ok = [rank for rank, _, _, verdict in flee.door_verdicts(held) if verdict == "ok" and rank[0] <= LEAVE_R]
        return min(ok)[2] if ok else None

    def _leave_answer(self, flee, held):
        """The Flee's answer on a leave tick: its running leg held (None: `Survive._answer` holds it); the door's walk
        (None: the Flee's choose picks that door, its stand ready); else the run from the group's centroid for LEAVE_S,
        turned by SIDE_TURNS to the first heading the map reads clear over STEER_PROBE."""
        door = self._leave_door(flee, held)
        if door is not None:
            self.group_leave = dict(self.group_leave or {}, leg="door", door=list(door))
            return None
        if flee.busy():
            self.group_leave = dict(self.group_leave or {}, leg="steer")
            return None
        group = self._group_standing(GROUP_ENTRY_R)
        mx, my = me_xy(self.world)
        cx = sum(z["x"] for _, z, _ in group) / len(group)
        cy = sum(z["y"] for _, z, _ in group) / len(group)
        v = _unit(mx - cx, my - cy)
        turn = next((t for t in (0,) + SIDE_TURNS if clear_heading(self.world, _rotate(v, t), STEER_PROBE,
                                                                   self.TRANS)), 0)
        h = _rotate(v, turn)
        self.group_leave = dict(self.group_leave or {}, leg="steer", centroid=[cx, cy], turn=turn)
        self.why = {"leave": True}
        return flee, Steer(h[0], h[1], LEAVE_S, FLEE_GAIT)
