"""The group rules (Plan 33 Task 3, the spec `2026-11-08` § 3.3, F18's death under three standing in open ground; Plan
36 Task 3's engagement picker; Plan 37 Task 3 the disposition's leave, `planner/disposition.py`): a group is met by the
reflex's engagement, never by running into it (Angus's memories `combat-approach-not-flee`, `fighting-retreat`).

`Threat`'s mixin, its state `Survive`'s own (`Survive.__init__`), its constants `policies.py`'s, its switches
`Threat`'s (`survive.T19_SWITCHES`); `_group_read` is the tick's bookkeeping, read at `Threat._threat_read`'s start:
the standing count within GROUP_ENTRY_R (`group_n`, one read dead or across a blocked edge left out), the closing read
(`_group_closing`: each nearer than on the line before) and the pull's hysteresis (`_pull_prev`).

- The leave (`_group_leave`, `_leave_entry`, `_leave_leg`, `_leave_door`): the row where the disposition selector does
  not run (`Disposer._disposing` False: DISPOSITION off, a build announcing no `melee`, unarmed). GROUP_LEAVE_N standing
  zombies closing within GROUP_ENTRY_R, or (LEAVE_ENTRY) GROUP_LEAVE_N standing with the nearest within KEEP_R, the
  character in the open (not on a room square, not sheltered) and above FLEE_HEALTH_FLOOR; the back read logged beside
  the entry (`back_cover`, a wall at the back stops no drag-down, #4290; with LEAVE_ENTRY off the cover withholds and
  the closing read alone enters). Its legs, logged `group_leave` {closing | on, leg} and `group_retreat` {leg, closing,
  centroid_away}: `door`, the Flee's walk (reason `leave`) to the nearest known door whose approach square is within
  LEAVE_DOOR_R and whose verdict reads `ok` (`Flee.door_verdicts`), the doorway stand resumed there (P24-AO); under
  LEAVE_DOOR_RACE no new door with the nearest standing within DOOR_RACE_R or a building with no second way out
  (`door_refused`), a running door plan before its close dropped with a standing zombie within DOOR_ABORT_R
  (`door_dropped`); else `retreat`, the Fight on the nearest standing zombie, `retreat` the unit heading away from the
  standing centroid (the Fight's pin read), the melee's withdraw the picker's. With the melee engaged the door reads as
  the retreat (`group_leave` {over}). The leave holds while GROUP_LEAVE_N stand within GROUP_ENTRY_R (on the door's
  walk within DANGER_R) and ends at the doorway, when fewer stand (`group_leave` {end "strung"}) or under the floor.
  Where the selector runs, its `hold` is the retreat and its `break` (`leave`) the door, taken through the release.
- `LEAVE_CARE` (Plan 34, the spec's § 3.1): with `group_n` at GROUP_LEAVE_N or more the care's commitment and yield are
  barred but the ride (`care_yield.py`, logged `care_withheld`).
- The engagement picker (`_pull`, Plan 36 Task 3, the spec `2026-11-11-plan-36-the-engagement-design.md` § 3.3; F21's
  two bites from 76 to 116 degrees off the body): the withdraw vector the Fight's running melee carries, read on the
  Fight's lines the picker reads (`Threat._pull_ok`): the spread (`_pull_spread`), two or more standing zombies closing
  within GROUP_ENTRY_R whose bearings spread more than PULL_SPREAD_DEG, the vector into the widest gap of their
  bearings until the spread falls under PULL_STOP_DEG or the nearest stands within the reach; the cone (`_pull_cone`),
  a standing zombie closing within CONE_TRIGGER_R more than CONE_OFF_DEG off the pinned target's bearing, the vector
  away from the bisector until it stands inside the cone (CONE_HALF_DEG) or within the reach; the retreat
  (`_pull_retreat`, Angus's fighting retreat), the vector away from the standing centroid: under the `hold`
  disposition whenever the spread and the cone read none (the standing within GROUP_ENTRY_R + RETREAT_HOLD_R, closing or
  not: the hold's dwell is the selector's), never under `hunt` (its pulls the spread's and the cone's alone, Task 3 fix
  1), and with the selector not running at GROUP_LEAVE_N or more closing, read after the spread and before the cone. Every heading is clamped to the room ring's open headings within PULL_ROOM_TURN_DEG reading PULL_ROOM_NEED
  tiles (`_pull_room`, logged {room {from}}), the vector dropped with none ({room "closed"}); logged `engage_pull` {why
  "spread" | "retreat" | "cone", spread, n, heading[, flank]} on the threat why.

Deleted: Plan 35 Task 8 the rules that pressed or stepped in contact beside the reflex (the leave's first-line shove,
DRAG_GUARD_FIGHT, SIDE_CLEAR, STRUNG_HOLD, DRAG_DEFER); Plan 37 Task 3 the leave's `run` leg above RETREAT_MAX_N with
the constant, SPENT_LEAVE's spent run and RUN_HOLD (the string owns the many and the spent), the GROUP_LEAVE switch (the
entry is the selector's where it runs) and the retreat pull's own hysteresis (the hold's dwell is the selector's).
"""
import math

from agent.base.planner.crawler import is_crawler
from agent.base.planner.policies import (ATTACK_MARGIN, CONE_HALF_DEG, CONE_OFF_DEG, CONE_TRIGGER_R, DANGER_R,
                                         DISENGAGE_R, DOOR_ABORT_R, DOOR_RACE_R, FIGHT_REACH, FLEE_HEALTH_FLOOR,
                                         GROUP_ENTRY_R, GROUP_LEAVE_N, KEEP_R, LEAVE_DOOR_R, PULL_ROOM_NEED,
                                         PULL_ROOM_TURN_DEG, PULL_SPREAD_DEG, PULL_STOP_DEG, RETREAT_HOLD_R,
                                         STRING_ENTRY_R, WALL_R, blocked, on_floor, zdist)
from agent.base.world import ROOM_STEP_DEG, me_floor, me_xy

__all__ = ["ThreatGroup", "LEAVE_PLAN", "back_cover", "spread_gap"]

LEAVE_PLAN = {"door": ("flee", "leave"), "retreat": ("fight", None)}   # the threat plan of each leave leg
                                                                      # (`Threat._threat_plan`)


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
    """The leave's back read: `{kind, at}` of the first known feature within WALL_R of the player on its back side (its
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


def _bearing(p, z):
    """Degrees [0, 360) from point `p` to zombie `z`, 0 the world's +x, 90 its +y."""
    return math.degrees(math.atan2(z["y"] - p[1], z["x"] - p[0])) % 360.0


def _off(a, b):
    """Degrees [0, 180] between bearings `a` and `b`."""
    return abs((a - b + 180.0) % 360.0 - 180.0)


def _heading(deg):
    r = math.radians(deg)
    return (math.cos(r), math.sin(r))


def spread_gap(bearings):
    """`(spread, gap)` of two or more bearings (degrees): `spread` the narrowest arc holding them all (360 less their
    widest gap), `gap` the bearing at that gap's middle (the arc's bisector turned about: the way away from the group's
    centroid while the arc is under 180 degrees, and the open side while it is over); the first widest gap in bearing
    order on a tie."""
    bs = sorted(b % 360.0 for b in bearings)
    gaps = [(bs[i + 1] - bs[i], bs[i]) for i in range(len(bs) - 1)] + [(bs[0] + 360.0 - bs[-1], bs[-1])]
    widest, start = max(gaps, key=lambda g: g[0])
    return 360.0 - widest, (start + widest / 2.0) % 360.0


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
        """The tick's group bookkeeping, before the decision (`Threat._threat_read`): this tick's whys cleared, the
        leave's outputs too (`_clear_leave`, fix 4: a line the drag guard answers before the leave's row logs no stale
        `group_retreat`); the closing read (`_group_closing`: the standing zombies within GROUP_ENTRY_R each nearer than
        on the line before, `_group_prev` their distances within DISENGAGE_R, kept for the next line); `group_n`, the
        standing zombies within GROUP_ENTRY_R (LEAVE_CARE's count and the disposition selector's, read every tick);
        the pull's outputs cleared, its last read kept as `_pull_prev` (Plan 36 Task 3: the hysteresis of `_pull`, a
        tick that fought no open-ground Fight leaving none)."""
        self.group_leave = None
        self._clear_leave()
        self._pull_prev, self._pull_on, self.pull, self.engage_pull = self._pull_on, None, None, None
        near = self._group_standing(DISENGAGE_R)
        self.group_n = sum(1 for _, _, d in near if d <= GROUP_ENTRY_R)
        prev = self._group_prev
        self._group_closing = [(zid, z, d) for zid, z, d in near
                               if d <= GROUP_ENTRY_R and zid in prev and d < prev[zid]]
        self._string_closing = [(zid, z, d) for zid, z, d in near   # Plan 37 Task 3 fix 2: the string's count entry
                                if d <= STRING_ENTRY_R and zid in prev and d < prev[zid]]   # (within DISENGAGE_R)
        self._group_prev = {zid: d for zid, _, d in near}

    # ------------------------------------------------------------------------------------------------ the leave
    def _clear_leave(self):
        """The leave's outputs for this tick, cleared: `leave_leg` (door | retreat), `retreat` (the unit heading the
        Fight's pin reads, else None) and the `group_retreat` why."""
        self.retreat, self.group_retreat, self.leave_leg = None, None, None

    def _group_leave(self, inside):
        """The leave's row (the module docstring): True when the tick takes the leave (a new one, or the running one
        held), else False, `leave` cleared when its end is read; `group_leave` the why either way, `leave_leg` the leg
        (door | retreat) and, on the retreat, `retreat` the unit heading away from the standing group's centroid."""
        self._clear_leave()
        if not self.GROUP_LEAVE or inside or self.sheltered or self._health() < FLEE_HEALTH_FLOOR:
            self.leave = None
            return False
        if self.leave is not None:
            door_leg = self.flee is not None and self.flee.plan is not None
            n = len(self._group_standing(DANGER_R if door_leg else GROUP_ENTRY_R))
            if n < GROUP_LEAVE_N:
                self.leave = None
                self.group_leave = {"end": "strung", "n": n}
                return False
            self.group_leave = {"n": n}
            self._leave_leg()
            return True
        entry = self._leave_entry()
        if entry is None:
            return False
        self.leave = dict(entry, since=self.clock())
        self.group_leave = entry
        self._leave_leg()
        return True

    def _leave_entry(self):
        """A new leave's entry read: its why (`group_leave`'s first keys, kept in the leave's record) when the tick
        enters, else None (`group_leave` {withheld "cover", closing, cover} logged when a wall at the back withholds it):
        - closing: GROUP_LEAVE_N or more standing zombies within GROUP_ENTRY_R each nearer than on the line before
          (`_group_closing`), `{closing: [ids]}`; the back read (`back_cover`, away from the closing ones' centroid)
          withholds it, except under LEAVE_ENTRY, where it is logged beside the entry (`{closing, cover}`) and the
          leave enters;
        - on (LEAVE_ENTRY): GROUP_LEAVE_N or more standing within GROUP_ENTRY_R with the nearest within KEEP_R, closing
          or not (already on the character, they jitter rather than close), `{on: [ids], near: tiles}`."""
        closing = self._group_closing
        if len(closing) >= GROUP_LEAVE_N:
            ids = [zid for zid, _, _ in closing]
            mx, my = me_xy(self.world)
            cx = sum(z["x"] for _, z, _ in closing) / len(closing)
            cy = sum(z["y"] for _, z, _ in closing) / len(closing)
            cover = back_cover(self.world, _unit(mx - cx, my - cy))
            if cover is None:
                return {"closing": ids}
            if self.LEAVE_ENTRY:   # Plan 34 Task 3b: a wall at the back stops no drag-down
                return {"closing": ids, "cover": cover}
            self.group_leave = {"withheld": "cover", "closing": ids, "cover": cover}
            return None
        if not self.LEAVE_ENTRY:
            return None
        group = self._group_standing(GROUP_ENTRY_R)
        if len(group) < GROUP_LEAVE_N or group[0][2] > KEEP_R:
            return None
        return {"on": [zid for zid, _, _ in group], "near": group[0][2]}

    def _leave_leg(self):
        """The leave's leg this tick, the first that applies:
        - `door` while a known door within LEAVE_DOOR_R is held or reads `ok` (a long walk turns the back on the
          group); Plan 34 Task 2 (LEAVE_DOOR_RACE): a running door plan before its close is dropped with a standing
          zombie within DOOR_ABORT_R (`flee.abort_door`, logged `door_dropped` "abort" and `near`, the tiles) and this
          line's leg re-read; no new door is picked against the race or a building with one way out (`_leave_door`,
          logged `door_refused`);
        - else `retreat`, the Fight on the nearest standing zombie (`retreat`, the heading away from the centroid of
          the standing zombies within GROUP_ENTRY_R, re-read every line, is the Fight's pin read, `_retreat_read`),
          logged `group_retreat` {leg, closing, centroid_away}; the melee's withdraw is the pull's (`_pull`).
        Plan 36 Task 3: with the Fight's melee engaged (`Threat._engage_on`) the door reads as the retreat, logged
        `group_leave` {leg "retreat", over: the door's keys}: never a leg over the melee."""
        flee = self.flee
        held_door = flee is not None and flee.plan is not None
        if held_door and self.LEAVE_DOOR_RACE and flee.plan["step"] in ("approach", "open", "enter"):
            close = self._group_standing(DOOR_ABORT_R)
            if close:   # Plan 34 Task 2 (LEAVE_DOOR_RACE): the door given up before its close, the leg re-read
                flee.abort_door()
                self.group_leave = dict(self.group_leave or {}, door_dropped="abort", near=close[0][2])
        group = self._group_standing(GROUP_ENTRY_R)
        door, refused = self._leave_door(flee, [z for _, z, _ in group])
        if refused is not None:
            self.group_leave = dict(self.group_leave or {}, **refused)
        mx, my = me_xy(self.world)
        cx = sum(z["x"] for _, z, _ in group) / len(group)
        cy = sum(z["y"] for _, z, _ in group) / len(group)
        away = _unit(mx - cx, my - cy)
        ids = [zid for zid, _, _ in group]
        if door is None:
            leg, out = "retreat", {"leg": "retreat"}
        elif self._engage_on():
            leg, out = "retreat", {"leg": "retreat", "over": {"leg": "door", "door": list(door)}}
        else:
            leg, out = "door", {"leg": "door", "door": list(door)}
        self.leave_leg = leg
        self.group_leave = dict(self.group_leave or {}, **out)
        if leg == "retreat":
            self.retreat = away
        self.group_retreat = {"leg": leg, "closing": ids, "centroid_away": [away[0], away[1]]}

    # ------------------------------------------------------------------------------------------------ the pull
    def _pull(self, fight, disposition=None):
        """Plan 36 Task 3 (the module docstring's engagement picker): the withdraw vector `fight`'s melee carries this
        tick (`pull`, a unit vector), else None; `engage_pull` {why, spread, n, heading[, flank]} its why, `heading`
        the vector's degrees; read on the Fight's lines the picker reads (`Threat._decide`), the spread's and the cone's
        hysteresis the last such line's read (`_pull_prev`). By the selector's `disposition` (Plan 37 Task 3 and its fix
        1): `hunt` the spread's pull (`_pull_spread`), else the cone's (`_pull_cone`), never the retreat (Plan 36's
        pair behaviour; the retreat is `hold`'s alone); `hold` the spread's, else the cone's, else the retreat's, which
        always reads there (`_pull_retreat` with `hold`); None (the selector not running) Plan 36's order, the spread's,
        then the retreat's at GROUP_LEAVE_N closing, then the cone's."""
        p = me_xy(self.world)
        standing = [(zid, z, d) for zid, z, d in self._group_standing(GROUP_ENTRY_R) if not is_crawler(z)]
        reach = self._pull_reach(fight)
        if disposition == "hunt":
            read = self._pull_spread(p, standing, reach) or self._pull_cone(p, standing, reach, fight)
        elif disposition == "hold":
            read = (self._pull_spread(p, standing, reach) or self._pull_cone(p, standing, reach, fight)
                    or self._pull_retreat(p, standing, hold=True))
        else:
            read = (self._pull_spread(p, standing, reach) or self._pull_retreat(p, standing)
                    or self._pull_cone(p, standing, reach, fight))
        if read is None:
            self._pull_on, self.pull, self.engage_pull = None, None, None
            return None
        heading, why = read
        self._pull_on = why
        room = self._pull_room(heading)
        if room == "closed":   # fix 3: no open heading within PULL_ROOM_TURN_DEG: the vector dropped, the reflex stands
            self.pull, self.engage_pull = None, dict(why, heading=heading, room="closed")
            return None
        self.engage_pull = dict(why, heading=heading)
        if room is not None and room != heading:
            self.engage_pull.update(heading=room, room={"from": heading})
        self.pull = _heading(heading if room is None else room)
        return self.pull

    def _pull_room(self, heading):
        """Plan 36 Task 3 fix 3: the pull's `heading` clamped to the room ring (`World.room`, Plan 36 Task 1: heading i
        at ROOM_STEP_DEG * i degrees from the world's +x): of the ring headings within PULL_ROOM_TURN_DEG of it reading
        at least PULL_ROOM_NEED tiles clear, the nearest to it (a tie to the clearer, then the first), its degrees;
        "closed" with none; None with no ring (an old frame: the heading unclamped)."""
        ring = self.world.room()
        if ring is None:
            return None
        picks = []
        for i, clear in enumerate(ring["h"]):
            at = ROOM_STEP_DEG * i
            off = _off(at, heading)
            if (isinstance(clear, (int, float)) and not isinstance(clear, bool) and clear >= PULL_ROOM_NEED
                    and off <= PULL_ROOM_TURN_DEG + 1e-9):
                picks.append((off, -clear, i, at))
        return "closed" if not picks else min(picks)[3]

    def _pull_reach(self, fight):
        """The tiles within which the nearest standing zombie ends the spread's pull (the reflex stands and presses):
        the Fight's attack reach (`reach_r`: the frame's `weapon.reach` plus ATTACK_MARGIN), else the frame's weapon
        reach plus ATTACK_MARGIN, else FIGHT_REACH."""
        r = fight.reach_r() if fight is not None else None
        if r is None:
            w = (self.world.weapon or {}).get("reach")
            ok = isinstance(w, (int, float)) and not isinstance(w, bool) and w > 0.0
            r = w + ATTACK_MARGIN if ok else FIGHT_REACH
        return r

    def _pull_spread(self, p, standing, reach):
        """The spread's pull: `(heading, why)` with two or more standing zombies (no crawler) closing within
        GROUP_ENTRY_R (`_group_closing`) whose bearings spread more than PULL_SPREAD_DEG, the heading the middle of
        their widest gap (`spread_gap`: along the bisector, away from their centroid); once running (`_pull_prev`), or
        while a leave holds (`leave`: the leave is this pull), every standing zombie within GROUP_ENTRY_R counts,
        closing or not (the pull itself opens their distances), the pull holding while their spread reads
        PULL_STOP_DEG or more; None with the nearest standing within `reach` (the reflex stands) or the spread
        closed."""
        if not standing or standing[0][2] <= reach:
            return None
        prev = self._pull_prev
        running = prev is not None and prev["why"] == "spread"
        if running or self.leave is not None:
            group = standing
        else:
            closing = {zid for zid, _, _ in self._group_closing}
            group = [e for e in standing if e[0] in closing]
        if len(group) < 2:
            return None
        spread, gap = spread_gap([_bearing(p, z) for _, z, _ in group])
        if spread < PULL_STOP_DEG if running else spread <= PULL_SPREAD_DEG:
            return None
        return gap, {"why": "spread", "spread": spread, "n": len(group)}

    def _pull_retreat(self, p, standing, hold=False):
        """Plan 36 Task 3 fix 1 (Angus's fighting retreat, memory `fighting-retreat`: with three on you, back-pedal in
        the stance while swinging): `(heading, why)`, the heading away from the group's centroid whatever its spread
        (a column included) and whatever the reach, logged {why "retreat", spread, n}: under the `hold` disposition
        (`hold`, Plan 37 Task 3) the standing zombies (no crawler) within GROUP_ENTRY_R + RETREAT_HOLD_R, closing or not
        (the hold's dwell and exit are the selector's); else GROUP_LEAVE_N or more of `standing` closing
        (`_group_closing`); None with none such."""
        if hold:
            group = [z for _, z, _ in self._group_standing(GROUP_ENTRY_R + RETREAT_HOLD_R) if not is_crawler(z)]
            if not group:
                return None
        else:
            closing = {zid for zid, _, _ in self._group_closing}
            group = [z for zid, z, _ in standing if zid in closing]
            if len(group) < GROUP_LEAVE_N:
                return None
        cx = sum(z["x"] for z in group) / len(group)
        cy = sum(z["y"] for z in group) / len(group)
        away = _unit(p[0] - cx, p[1] - cy)
        spread, _ = spread_gap([_bearing(p, z) for z in group])
        heading = math.degrees(math.atan2(away[1], away[0])) % 360.0
        return heading, {"why": "retreat", "spread": spread, "n": len(group)}

    def _pull_cone(self, p, standing, reach, fight):
        """The cone's pull: `(heading, why)` with a standing zombie (no crawler, not the pin) closing within
        CONE_TRIGGER_R and beyond `reach` more than CONE_OFF_DEG off the bearing of `fight`'s pinned target (standing,
        listed): the heading away from the bisector of the two bearings (the withdraw that brings it toward the
        engagement cone, the pin's bearing CONE_HALF_DEG either side), `flank` its id, `spread` the degrees between
        them, `n` 2; once running the same flanker holds it while it stands within CONE_TRIGGER_R beyond `reach`
        more than CONE_HALF_DEG off the pin, closing or not; the nearest such flanker else."""
        t = self.world.zombies.get(fight.target) if fight is not None and fight.target is not None else None
        if t is None or t.get("x") is None or t.get("y") is None or on_floor(t) or is_crawler(t):
            return None
        bt = _bearing(p, t)
        prev = self._pull_prev
        held = prev["flank"] if prev is not None and prev["why"] == "cone" else None
        closing = {zid for zid, _, _ in self._group_closing}
        picks = []
        for zid, z, d in standing:
            if zid == fight.target or d > CONE_TRIGGER_R or d <= reach:
                continue
            bf = _bearing(p, z)
            off = _off(bf, bt)
            if off > CONE_HALF_DEG if zid == held else (zid in closing and off > CONE_OFF_DEG):
                picks.append((zid != held, d, repr(zid), zid, bf, off))
        if not picks:
            return None
        _, _, _, zid, bf, off = min(picks)
        signed = (bf - bt + 180.0) % 360.0 - 180.0
        return (bt + signed / 2.0 + 180.0) % 360.0, {"why": "cone", "spread": off, "n": 2, "flank": zid}

    def _leave_door(self, flee, ts):
        """`(door, refused)`: the door the leave walks to, the Flee's running plan's, else the nearest door a Flee reads
        `ok` whose approach square is within LEAVE_DOOR_R while the Flee has not picked yet (the running Flee, else a
        fresh one for the read, `ts` the group's zombies); else None. Plan 34 Task 2 (LEAVE_DOOR_RACE; F19's line 1595
        took the door with the nearest standing at 0.37 tiles, its building one room with one door): the verdicts
        read with `second_exit` True (a building with no other way out on the door's floor is `one_exit`), and no new
        door with the nearest standing zombie within DOOR_RACE_R; `refused` then {door_refused "race", near} when an
        `ok` door was there to take, else {door_refused "one_exit"} when only that verdict refused one within
        LEAVE_DOOR_R; None otherwise."""
        if flee is not None and flee.plan is not None:
            return flee.door(), None
        if flee is not None and flee.picked:
            return None, None
        if flee is None:
            from agent.base.planner.flee import Flee   # at call: threat.py imports this module
            flee = Flee(self.world, self.actions, self.clock, shunned=self.night.shunned)
        race = self.LEAVE_DOOR_RACE
        near = [(rank, verdict) for rank, _, _, verdict in flee.door_verdicts(ts, True if race else None)
                if rank[0] <= LEAVE_DOOR_R]
        ok = [rank for rank, verdict in near if verdict == "ok"]
        if ok and race:
            standing = self._group_standing(DANGER_R)
            if standing and standing[0][2] <= DOOR_RACE_R:
                return None, {"door_refused": "race", "near": standing[0][2]}
        if ok:
            return min(ok)[2], None
        if race and any(verdict == "one_exit" for _, verdict in near):
            return None, {"door_refused": "one_exit"}
        return None, None
