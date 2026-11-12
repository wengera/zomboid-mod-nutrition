"""The group's entry (Plan 33 Task 3, the spec's § 3.3; F18, `f_goals_18-20261108-235005`: while the finish stalled,
three standing zombies, 13648, 13651 and 13653, walked in from 11.6 to 12.0 tiles and closed to 0.45 to 0.9 tiles with
the character in open ground; the drag-down guard (`Threat._drag`, ruling P24-A (h)) then sent fourteen `flee:many`
lines (402 to 415) with five run steers while no frame read the character moving for 116 frames, seq 3512 to 3655,
every one under a hit reaction, and the character died in the drag-down at game minute 617). Angus's direction
(memories `combat-approach-not-flee`, `stand-and-fight-dress-first`): one zombie is never a reason to flee; a group is
left before it closes, never by running into it.

`Threat`'s mixin, its state `Survive`'s own (`Survive.__init__`), its constants `policies.py`'s, its switches
`Threat`'s (`survive.T18_SWITCHES`, `survive.T19_SWITCHES`); `_group_read` is the tick's bookkeeping, read at
`Threat._threat_read`'s start:

- `GROUP_LEAVE` (`_group_leave`, `_leave_leg`, `_leave_door`): GROUP_LEAVE_N (3, fix 3: a pair is fought under
  PAIR_NEAREST) standing zombies within GROUP_ENTRY_R, each nearer than on the decision line before (closing), with
  nothing at the character's back within WALL_R (`back_cover`: a known wall or fence edge, a door record, a solid
  square) and the character out in the open (not on a room square, not sheltered), whatever stands in reach but under
  FLEE_HEALTH_FLOOR (the health flee's). Its legs, logged `group_leave` {closing | n, leg} and `group_retreat` {leg,
  closing, centroid_away}:
  `door`: the Flee's walk (reason `leave`) to the nearest known building door whose approach square is within
  LEAVE_DOOR_R (6.0: a long walk turns the back on the group) and whose verdict reads `ok` (`Flee.door_verdicts`), the
  doorway stand resumed there (the Flee's `stand_ok`, P24-AO); with none,
  `retreat` (Angus's fighting retreat, memory `fighting-retreat`): the Fight, never a run, on the nearest standing
  zombie (`retreat`, the unit heading away from the centroid of the standing zombies within GROUP_ENTRY_R, re-read
  every line, the Fight's pin read), the melee's withdraw the engagement picker's (below, Plan 36); with the melee
  engaged the door and the spent or held run read as the retreat; fix 4 (round three, trial 3,
  `x_trial-ladder-20261109-042558`: the standing count rose to eight under the retreat and the character died): the
  retreat for GROUP_LEAVE_N to RETREAT_MAX_N standing within GROUP_ENTRY_R; above it
  `run`: the threat plan's `many` flee, logged `group_leave` {leg "run", n}, the retreat resumed on the line the count
  falls back to RETREAT_MAX_N (but under RUN_HOLD, below).
  The leave holds while GROUP_LEAVE_N stand within GROUP_ENTRY_R (the retreat, the run) or, on the door's walk, within
  DANGER_R; it ends at the doorway (the stand's row, `Threat._doorway`, answers first), when fewer stand (`group_leave`
  {end "strung"}, on the first such line) or under the floor. Withheld, logged `group_leave` {withheld: cover}, when a
  wall is at the back (with LEAVE_ENTRY off: Task 3b below).
  Plan 34 Task 2 (`LEAVE_DOOR_RACE`; F19, `f_goals_19-20261109-060929`, its GUIDE § 3: the leg turned `door` on line
  1595 with the nearest standing at 0.37 tiles, the door of a one-room building with one door, and the close shut it
  from outside three seconds later, 12431 at 0.60 tiles): `_leave_door` picks no new door with the nearest standing
  zombie within DOOR_RACE_R (`group_leave` {door_refused "race", near}) and reads the verdicts with `second_exit` True
  (a building with no other way out refused, `door_refused` "one_exit"); `_leave_leg` drops a running door plan whose
  step is not yet the close with a standing zombie within DOOR_ABORT_R (`Flee.abort_door`, `group_leave` {door_dropped
  "abort", near}) and re-reads the leg on the same line (the retreat or the run). Its partner, `DOOR_INSIDE`, is the
  Flee's (`flee.py`: the enter read inside, the close sent from inside).
  Plan 34 Task 3b LEAVE_ENTRY (ruling P34-G; the trial `x_trial-ladder-20261109-123231`, the fix arm on the `agent`
  fixture, P31-T, not evidence: at decision line 12 a closing trio, 8932, 8933 and 8927, was withheld `cover`, a wall
  edge at the back, and fought there; from line 25 to 60 three standing at 0.4 to 0.9 tiles, jittering rather than
  closing, made no leave line; the drag-down at game minute 578), `_leave_entry`: no cover exemption, the back read
  logged beside the entry (`group_leave` {closing, cover}), since a wall at the back stops no drag-down (#4290); and the
  leave entered, besides the closing read, with GROUP_LEAVE_N or more standing within GROUP_ENTRY_R and the nearest
  within KEEP_R, closing or not (`group_leave` {on: [ids], near}). With the switch off, the cover withholds and the
  closing read alone enters.
- `SPENT_LEAVE` (Plan 34 Task 3c, the trial `x_trial-ladder-20261109-132439`: every band melee in mode `shove` after 11
  kills, the arms spent): with the meet spent (`_spent_meet`: the melee would go in mode `shove`) the retreat's upper
  bound is one under GROUP_LEAVE_N, so GROUP_LEAVE_N standing within GROUP_ENTRY_R take the `run` (`_leave_leg`), logged
  `group_leave` {leg "run", n, spent true}; unspent, RETREAT_MAX_N as before.
- `RUN_HOLD` (Plan 34 Task 3c amendment 1; the trial `x_trial-ladder-20261109-134527`, P31-T, not evidence: decision
  lines 412 to 449, the leg flicked between {leg "run", n 5} and {leg "retreat", n 4} as the count crossed
  RETREAT_MAX_N, so the character never ran clear; the drag-down at game minute 621): once a leave's leg has read
  `run` (above RETREAT_MAX_N, or SPENT_LEAVE's bound) it stays `run` while that leave holds, whatever the count reads,
  until the leave ends (`strung`, the doorway, the floor), logged `group_leave` {leg "run", n, held true} on the lines
  the count alone would read the retreat (`_leave_leg`, the leave's record `run`); off, the leg by the count each line.
- `LEAVE_CARE` (Plan 34, the spec's § 3.1; F19, `f_goals_19-20261109-060929`: above RETREAT_MAX_N the leave's `run`
  alternated with the care, 21 of 55 lines from game minute 770 to 777 the care's, 5 rips none done): `_group_read`
  keeps the tick's standing count within GROUP_ENTRY_R (`group_n`, `_group_standing`'s read, one read dead or across a
  blocked edge left out); with it at GROUP_LEAVE_N or more the care's commitment and yield are barred but the ride.
  The rule's home is `care_yield.py` (`CareYield._care_commit`, `_care_yields`), logged `care_withheld` there.
- The engagement picker (Plan 36 Task 3, the spec `2026-11-11-plan-36-the-engagement-design.md` § 3.3; F21,
  `f_goals_21-20261111-150552`, decision lines 364 to 412: three and four standing with the meet spent, the leave's
  run held off the engaged melee, `engage_hold` {rule "leave"}, while the reflex pressed at point blank and two bites
  came from 76 to 116 degrees off the body): where the fight happens, decided before contact, by the withdraw vector
  the Fight's running melee carries (`_pull`, `Fight.withdraw`, the reflex's withdraw bias; the melee runs throughout:
  never a flee leg, a steer or a walk), read on every open-ground Fight line (`Threat._decide`):
  the spread (`_pull_spread`): two or more standing zombies closing within GROUP_ENTRY_R whose bearings spread more
  than PULL_SPREAD_DEG pull the fight to a line, the vector into the widest gap of their bearings (along the
  bisector, away from their centroid), until the spread falls under PULL_STOP_DEG or the nearest stands within the
  reach (then the vector is dropped, the melee re-sent without it, and the reflex stands);
  the retreat (`_pull_retreat`, fix 1, Angus's fighting retreat): GROUP_LEAVE_N or more standing zombies closing within
  GROUP_ENTRY_R send the vector away from their centroid whatever their spread (a column included) and whatever the
  reach, where the spread's pull does not answer, and once armed holds (fix 1b, {held true}) while three stand within
  GROUP_ENTRY_R + RETREAT_HOLD_R under the engaged melee, closing or not;
  the cone (`_pull_cone`): a standing zombie closing within CONE_TRIGGER_R more than CONE_OFF_DEG off the pinned
  target's bearing sends the vector away from the bisector of the two bearings, until it stands inside the cone (the
  pin's bearing CONE_HALF_DEG either side) or within the reach;
  fix 3: with the room ring on the frame (`World.room`) every pull's heading is clamped to the nearest ring heading
  within PULL_ROOM_TURN_DEG reading PULL_ROOM_NEED tiles clear (`_pull_room`, logged {room {from}} when it moved),
  the vector dropped with none (logged {room "closed"}); so the pull runs for the corner Fight too (`Threat._pull_ok`);
  logged `engage_pull` {why "spread" | "retreat" | "cone", spread, n, heading[, flank]} on the threat why. The leave at
  GROUP_LEAVE_N is this pull: its retreat's withdraw, and with the melee engaged its door and spent or held run read as
  the retreat (`_leave_leg`, `group_leave` {over}); Plan 35's `engage_hold` {rule "leave"} is deleted. Above
  RETREAT_MAX_N the `many` run stays, its heading the room ring's most open one where the frame carries the ring
  (`flee.Flee.open_run`, `World.room_open`).

Plan 35 Task 8 (the deletion; the reflex owns contact) removed the rules that pressed or stepped in contact beside the
reflex: the leave's first-line shove (its `shove` leg), Plan 33 Task 3's DRAG_GUARD_FIGHT (the guard's shove in its
run's place and the stuck episode) and SIDE_CLEAR (the run steer turned off a standing zombie, the least-bad heading),
and Plan 34's STRUNG_HOLD (the `strung` end held STRUNG_LINES lines) and DRAG_DEFER (the guard's run deferred to the
retreat's regain).
"""
import math

from agent.base.planner.crawler import is_crawler
from agent.base.planner.policies import (ATTACK_MARGIN, CONE_HALF_DEG, CONE_OFF_DEG, CONE_TRIGGER_R, DANGER_R,
                                         DISENGAGE_R, DOOR_ABORT_R, DOOR_RACE_R, FIGHT_REACH, FLEE_HEALTH_FLOOR,
                                         GROUP_ENTRY_R, GROUP_LEAVE_N, KEEP_R, LEAVE_DOOR_R, PULL_ROOM_NEED,
                                         PULL_ROOM_TURN_DEG, PULL_SPREAD_DEG, PULL_STOP_DEG, RETREAT_HOLD_R,
                                         RETREAT_MAX_N, STRAIN_SOFT, WALL_R, arm_pain, blocked, on_floor, zdist)
from agent.base.world import ROOM_STEP_DEG, me_floor, me_xy

__all__ = ["ThreatGroup", "LEAVE_PLAN", "back_cover", "spread_gap"]

LEAVE_PLAN = {"door": ("flee", "leave"), "retreat": ("fight", None),
              "run": ("flee", "many")}   # the threat plan of each leave leg (`Threat._threat_plan`)


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
        standing zombies within GROUP_ENTRY_R (Plan 34: LEAVE_CARE's count and the `many` lapse's, read every tick);
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
        self._group_prev = {zid: d for zid, _, d in near}

    # ------------------------------------------------------------------------------------------------ GROUP_LEAVE
    def _clear_leave(self):
        """The leave's outputs for this tick, cleared: `leave_leg` (door | retreat | run), `retreat` (the unit heading
        the reflex withdraws on, else None) and the `group_retreat` why."""
        self.retreat, self.group_retreat, self.leave_leg = None, None, None

    def _group_leave(self, inside):
        """GROUP_LEAVE's row (the module docstring): True when the tick takes the leave (a new one, or the running one
        held), else False, `leave` cleared when its end is read; `group_leave` the why either way, `leave_leg` the leg
        (door | retreat | run) and, on the retreat, `retreat` the unit heading away from the standing group's
        centroid."""
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
        - `door` while a known door within LEAVE_DOOR_R is held or reads `ok` (Angus's fighting retreat: a long walk
          turns the back on the group); Plan 34 Task 2 (LEAVE_DOOR_RACE): a running door plan before its close is
          dropped with a standing zombie within DOOR_ABORT_R (`flee.abort_door`, logged `door_dropped` "abort" and
          `near`, the tiles) and this line's leg re-read; no new door is picked against the race or a building with
          one way out (`_leave_door`, logged `door_refused`);
        - `run` with more than RETREAT_MAX_N standing within GROUP_ENTRY_R (fix 4: a backpedal does not outpace eight),
          the threat plan's `many` flee, logged `group_leave` {leg "run", n}; Plan 34 Task 3c (SPENT_LEAVE): with the
          meet spent (`_spent_meet`) at GROUP_LEAVE_N or more, logged {leg "run", n, spent true}; amendment 1
          (RUN_HOLD): once a leave's leg read `run` it stays `run` while that leave holds, whatever the count reads,
          logged {leg "run", n, held true} on the lines the count alone would read the retreat;
        - else `retreat`, the Fight on the nearest standing zombie (`retreat`, the heading away from the centroid of
          the standing zombies within GROUP_ENTRY_R, re-read every line, is the Fight's pin read, `_retreat_read`),
          logged `group_retreat` {leg, closing, centroid_away}; the melee's withdraw is the pull's (`_pull`).
        Plan 36 Task 3 (the spec's § 3.3): with the Fight's melee engaged (`Threat._engage_on`) and no more than
        RETREAT_MAX_N standing, the door, the spent run and the held run read as the retreat, logged `group_leave`
        {leg "retreat", over: the leg's own keys}: the leave is the pull, never a leg or a hold over the melee."""
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
        n = len(group)
        if door is not None:
            leg, out = "door", {"leg": "door", "door": list(door)}
        else:
            spent = self.SPENT_LEAVE and self._spent_meet()   # Plan 34 Task 3c: a spent meet leaves three by the run
            if n > (GROUP_LEAVE_N - 1 if spent else RETREAT_MAX_N):   # fix 4: the `many` run as Plan 32's ran
                leg, out = "run", dict({"leg": "run", "n": n}, **({"spent": True} if spent else {}))
            elif self.RUN_HOLD and self.leave.get("run"):   # RUN_HOLD: no retreat resumes inside a leave that ran
                leg, out = "run", {"leg": "run", "n": n, "held": True}
            else:
                leg, out = "retreat", {"leg": "retreat"}
        if leg != "retreat" and n <= RETREAT_MAX_N and self._engage_on():
            leg, out = "retreat", {"leg": "retreat", "over": out}   # Plan 36 Task 3: no leave leg over the engaged
            # melee: the leave's door, spent run or held run is the pull (`_pull`), never a hold against the leave
        self.leave_leg = leg
        self.group_leave = dict(self.group_leave or {}, **out)
        if leg == "run":
            if "held" not in out:
                self.leave["run"] = True   # Plan 34 Task 3c amendment 1 (RUN_HOLD): the run holds for this leave
            return
        if leg == "retreat":
            self.retreat = away
        self.group_retreat = {"leg": leg, "closing": ids, "centroid_away": [away[0], away[1]]}

    def _spent_meet(self):
        """Plan 34 Task 3c (SPENT_LEAVE): the meet is spent this tick: the melee the Fight's dispatch would send goes in
        mode `shove` (`dispatch.FightDispatch._melee_mode_at`, `fight.Fight._hold_bars`): a hold the Fight reads
        (`_fight_spent`, R2) or a shove-and-stomp Fight (`_shove_only` of the open-ground Fight, the retreat's). Read off
        this tick's holds, not the Fight's last ones (the `run` drops the Fight, so a read off it would flap); the low
        fight's full swing (P27-E) needs a lone zombie and never stands beside a group. Fix 1 (the trial
        `x_trial-ladder-20261109-142025`, lines 119 and 120: `strain` 47.2, the stiffness 5.7 so no arms' hold, the
        maneuver's `spent` true, `group_leave` {leg "retreat", n 4}): or the arms' pain alone over STRAIN_SOFT, the
        reflex's own spent read (`PZAgent_StanceMelee.lua`'s `spentOf`: `body.armPain` over K.MELEE_SPENT_PAIN 10,
        where the meet sent in mode strike runs as the spent one); its moodle half the frame does not carry."""
        if self._fight_spent() or self._shove_only("fight") is not None:
            return True
        pain = arm_pain(self.world)
        return pain is not None and pain > STRAIN_SOFT

    # ------------------------------------------------------------------------------------------------ the pull
    def _pull(self, fight):
        """Plan 36 Task 3 (the module docstring's engagement picker): the withdraw vector `fight`'s melee carries this
        tick (`pull`, a unit vector), else None; `engage_pull` {why, spread, n, heading[, flank]} its why, `heading`
        the vector's degrees. The spread's pull first (`_pull_spread`), else the cone's (`_pull_cone`); read on the
        open-ground Fight's lines (`Threat._decide`), its hysteresis the last such line's read (`_pull_prev`)."""
        p = me_xy(self.world)
        standing = [(zid, z, d) for zid, z, d in self._group_standing(GROUP_ENTRY_R) if not is_crawler(z)]
        reach = self._pull_reach(fight)
        read = (self._pull_spread(p, standing, reach) or self._pull_retreat(p, standing, fight)
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

    def _pull_retreat(self, p, standing, fight):
        """Plan 36 Task 3 fix 1 (the controller's ruling; Angus's fighting retreat, memory `fighting-retreat`: with
        three on you, back-pedal in the stance while swinging): `(heading, why)` with GROUP_LEAVE_N or more standing
        zombies (no crawler) closing within GROUP_ENTRY_R whatever their spread (a column included) and whatever the
        reach, the heading away from their centroid, logged {why "retreat", spread, n}; None under GROUP_LEAVE_N
        closing (the spread's pull, read first, answers a wide pair or trio). Fix 1b (the hysteresis: a column keeping
        pace with the backpedal reads flat distances): once armed (`_pull_prev`) and while `fight`'s melee is engaged,
        it holds while GROUP_LEAVE_N or more standing zombies stand within GROUP_ENTRY_R + RETREAT_HOLD_R, closing or
        not, their centroid the heading's, logged {held true}; it drops under that count or at the melee's end."""
        closing = {zid for zid, _, _ in self._group_closing}
        group = [z for zid, z, _ in standing if zid in closing]
        held = False
        if len(group) < GROUP_LEAVE_N:
            prev = self._pull_prev
            if prev is None or prev["why"] != "retreat" or fight is None or not fight._engaged():
                return None
            group = [z for _, z, _ in self._group_standing(GROUP_ENTRY_R + RETREAT_HOLD_R) if not is_crawler(z)]
            if len(group) < GROUP_LEAVE_N:
                return None
            held = True
        cx = sum(z["x"] for z in group) / len(group)
        cy = sum(z["y"] for z in group) / len(group)
        away = _unit(p[0] - cx, p[1] - cy)
        spread, _ = spread_gap([_bearing(p, z) for z in group])
        heading = math.degrees(math.atan2(away[1], away[0])) % 360.0
        why = {"why": "retreat", "spread": spread, "n": len(group)}
        if held:
            why["held"] = True
        return heading, why

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
