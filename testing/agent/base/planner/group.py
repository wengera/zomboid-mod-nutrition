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

- `GROUP_LEAVE` (`_group_leave`, `_leave_leg`, `_leave_door`, `_leave_answer`): GROUP_LEAVE_N (3, fix 3: a pair is
  fought under PAIR_NEAREST) standing zombies within GROUP_ENTRY_R, each nearer than on the decision line before
  (closing), with nothing at the character's back within WALL_R (`back_cover`: a known wall or fence edge, a door
  record, a solid square) and the character out in the open (not on a room square, not sheltered), whatever stands in
  reach (the FIGHT_REACH exception is dropped: round two, trial 2, a group of four closed on a character fighting one at
  0.4 to 0.7 tiles and the exception withheld every line) but under FLEE_HEALTH_FLOOR (the health flee's). Its legs,
  logged `group_leave` {closing | n, leg} and `group_retreat` {leg, closing, centroid_away}:
  `shove` once, on the first line, at the nearest standing zombie within STAND_MIN_R (the engine's shove distance; the
  Flee's shove), then
  `door`: the Flee's walk (reason `leave`) to the nearest known building door whose approach square is within
  LEAVE_DOOR_R (6.0: a long walk turns the back on the group) and whose verdict reads `ok` (`Flee.door_verdicts`), the
  doorway stand resumed there (the Flee's `stand_ok`, P24-AO); with none,
  `retreat` (Angus's fighting retreat, memory `fighting-retreat`): the Fight, never a run, keeps its stance on the
  nearest standing zombie, every stance leg a backpedal (`Fight.retreat`) whose heading is away from the centroid of the
  standing zombies within GROUP_ENTRY_R, re-read every line, the meet pressing whoever enters reach as it does; fix 4
  (round three, trial 3, `x_trial-ladder-20261109-042558`: the standing count rose to eight under the retreat and the
  character died): the retreat for GROUP_LEAVE_N to RETREAT_MAX_N standing within GROUP_ENTRY_R; above it
  `run`: the threat plan's `many` flee (Plan 32's composition: the drag guard, SIDE_CLEAR's least-bad heading and the
  run), logged `group_leave` {leg "run", n}, the retreat resumed on the line the count falls back to RETREAT_MAX_N.
  The Fight's side of the retreat (its pin on the nearest standing zombie, the back leg always sent) is `fight.py`'s.
  The leave holds while GROUP_LEAVE_N stand within GROUP_ENTRY_R (the retreat, the run) or, on the door's walk, within
  DANGER_R; it ends at the doorway (the stand's row, `Threat._doorway`, answers first), when fewer stand (`group_leave`
  {end "strung"}) or under the floor. Withheld, logged `group_leave` {withheld: cover}, when a wall is at the back
  (with LEAVE_ENTRY off: Task 3b below).
  Plan 34 Task 2 (`LEAVE_DOOR_RACE`; F19, `f_goals_19-20261109-060929`, its GUIDE § 3: the leg turned `door` on line
  1595 with the nearest standing at 0.37 tiles, the door of a one-room building with one door, and the close shut it
  from outside three seconds later, 12431 at 0.60 tiles): `_leave_door` picks no new door with the nearest standing
  zombie within DOOR_RACE_R (`group_leave` {door_refused "race", near}) and reads the verdicts with `second_exit` True
  (a building with no other way out refused, `door_refused` "one_exit"); `_leave_leg` drops a running door plan whose
  step is not yet the close with a standing zombie within DOOR_ABORT_R (`Flee.abort_door`, `group_leave` {door_dropped
  "abort", near}) and re-reads the leg on the same line (the retreat or the run). Its partner, `DOOR_INSIDE`, is the
  Flee's (`flee.py`: the enter read inside, the close sent from inside).
  Plan 34 STRUNG_HOLD (F19, `f_goals_19-20261109-060929`, GUIDE.md § 4: episode one's 15 retreat lines alternated with
  11 `strung` ends at decision lines 274 to 299 as the count within 6 tiles flicked between three and fewer, the stance
  leg turning from the back heading to a seek toward 12340 and back, the character moving back and forth under a tile
  for 13 s): the `strung` end comes only once the count has read under GROUP_LEAVE_N on STRUNG_LINES consecutive lines
  (`strung_n` counting them, `_strung_holds`; reset on a line at or above the count, at the leave's start and its end);
  the lines before it hold the leave and its leg, logged `group_leave` {n, strung_n} (the key on those lines alone); a
  line reading none standing ends it at once. With the switch off, the end on the first such line.
  Plan 34 Task 3b LEAVE_ENTRY (ruling P34-G; the trial `x_trial-ladder-20261109-123231`, the fix arm on the `agent`
  fixture, P31-T, not evidence: at decision line 12 a closing trio, 8932, 8933 and 8927, was withheld `cover`, a wall
  edge at the back, and fought there; from line 25 to 60 three standing at 0.4 to 0.9 tiles, jittering rather than
  closing, made no leave line; the drag-down at game minute 578), `_leave_entry`: no cover exemption, the back read
  logged beside the entry (`group_leave` {closing, cover}), since a wall at the back stops no drag-down (#4290) and the
  retreat's heading turns off it (`fight.Fight._retreat_heading`); and the leave entered, besides the closing read,
  with GROUP_LEAVE_N or more standing within GROUP_ENTRY_R and the nearest within KEEP_R, closing or not (`group_leave`
  {on: [ids], near}). With the switch off, the cover withholds and the closing read alone enters.
  The Fight's side of the retreat at the stance's band (Plan 34 RETREAT_GAP and RETREAT_MELEE) is `fight.py`'s.
- `DRAG_GUARD_FIGHT` (`_drag_fight`, `_drag_shove`): the drag-down guard's flee, when the frame reads a hit reaction
  (`me.hitReaction` non-empty) or STUCK_FRAMES frames of `me.moving` false while a steer or a walk is the running
  action (`_drag_stuck`), shoves the nearest standing zombie within SHOVE_R in front of the character (within 90 degrees
  of `me.lookAngle`; else the nearest within SHOVE_R) in the run's place, the shove being the one press the engine takes
  at the reaction's end (#4372). Fix 2 (round one, trial 3, `x_trial-ladder-20261109-022952`: in a pile of three the
  character was hit every tick, so the latch never released and the guard shoved tick after tick, the targets
  alternating, until the death; Plan 32's plain run left such a pile and lived): the shove opens a stuck episode
  (`drag_episode` {at, shoves}, at the character's place) and is sent at most DRAG_SHOVES_PER_EPISODE times in it; from
  the next guard line the guard's run is sent as it always was, whatever the reaction reads (a shove still running
  dropped for it: the engine moves the character the moment the reaction ends, and the run's steer stands meanwhile),
  until the character has moved STUCK_FREE_R from the episode's start (`_group_read`), which ends the episode (the
  threat's end too); a new one may shove once again. Logged `drag_fight` {target, dist, why hit | stuck} on the shove,
  {spent, why} on the runs after it. Plan 34 fix C (ruling P34-A, `SHOVE_CLEAR`): the Lua's shove waits for the
  reaction's end, so a shove still running on a spent line is held, logged `drag_fight` {spent, holding, why
  "shove_wait"}, and the run goes once it has ended (done, or `failed busy` at the wait's cap).
  Plan 34 Task 3c `DRAG_DEFER` (ruling P34-I; the trial `x_trial-ladder-20261109-132439`, P31-T, not evidence:
  decision lines 408 to 446, the guard's `many` run sent six times under the leave's retreat, each superseding the
  band's melee, the character moving nowhere until the drag-down): one owner under the retreat. While the leave
  holds with its leg the retreat, the guard's row sends its one shove as before (and holds it while it runs, fix C),
  then sends no run: the line takes the leave's plan, the Fight's retreat, whose regain (`fight.py`'s
  RETREAT_REGAIN) takes the guard's shove as its press and sends the back leg (`_drag_defers`), logged `drag_fight`
  {.., deferred "retreat"}. Under the leave's `run` (above the bound, or the spent meet's) the guard's run as before.
- `SPENT_LEAVE` (Plan 34 Task 3c, the same trial: every band melee in mode `shove` after 11 kills, the arms spent):
  with the meet spent (`_spent_meet`: the melee would go in mode `shove`) the retreat's upper bound is one under
  GROUP_LEAVE_N, so GROUP_LEAVE_N standing within GROUP_ENTRY_R take the `run` (`_leave_leg`), logged `group_leave`
  {leg "run", n, spent true}; unspent, RETREAT_MAX_N as before.
- `RUN_HOLD` (Plan 34 Task 3c amendment 1; the trial `x_trial-ladder-20261109-134527`, P31-T, not evidence: decision
  lines 412 to 449, the leg flicked between {leg "run", n 5} and {leg "retreat", n 4} as the count crossed
  RETREAT_MAX_N, so the character never ran clear; the drag-down at game minute 621): once a leave's leg has read
  `run` (above RETREAT_MAX_N, or SPENT_LEAVE's bound) it stays `run` while that leave holds, whatever the count reads,
  until the leave ends (`strung`, the doorway, the floor), logged `group_leave` {leg "run", n, held true} on the lines
  the count alone would read the retreat (`_leave_leg`, the leave's record `run`); off, the leg by the count each line.
- `SIDE_CLEAR` (`_side_clear`): no run steer the threat branch answers passes within SIDE_R of a standing zombie over
  its first SIDE_LOOK tiles (`side_hits`: ahead of the player, within SIDE_R of the leg's segment); the heading is turned
  by 30-degree steps both ways, nearest first, to the first heading clear of them and of the map (then clear of them
  alone). With no clear heading (fix 2: the shove sent there in a pile was the trial's second shover) the least-bad run
  (`_least_bad`): of the wanted heading and its SIDE_TURNS turns (those the map reads clear over STEER_PROBE, else all),
  the one whose nearest passed standing zombie lies farthest along the leg (`side_dist`), the nearest turn on a tie;
  never a shove, so DRAG_GUARD_FIGHT's one shove is the only one these rules send. Logged `side_clear` {turn, near} and,
  on the least-bad run, `least_bad` that distance.
- `LEAVE_CARE` (Plan 34, the spec's § 3.1; F19, `f_goals_19-20261109-060929`: above RETREAT_MAX_N the leave's `run`
  alternated with the care, 21 of 55 lines from game minute 770 to 777 the care's, 5 rips none done): `_group_read`
  keeps the tick's standing count within GROUP_ENTRY_R (`group_n`, `_group_standing`'s read, one read dead or across a
  blocked edge left out); with it at GROUP_LEAVE_N or more the care's commitment and yield are barred but the ride.
  The rule's home is `care_yield.py` (`CareYield._care_commit`, `_care_yields`), logged `care_withheld` there.
"""
import math

from agent.base.planner.policies import (DANGER_R, DISENGAGE_R, DOOR_ABORT_R, DOOR_RACE_R, DRAG_SHOVES_PER_EPISODE,
                                         FLEE_GAIT,
                                         FLEE_HEALTH_FLOOR, GROUP_ENTRY_R, GROUP_LEAVE_N, KEEP_R,
                                         LEAVE_DOOR_R, RETREAT_MAX_N, SHOVE_R, STAND_MIN_R, SIDE_LOOK, SIDE_R,
                                         STEER_PROBE, STRAIN_SOFT, STRUNG_LINES, STUCK_FRAMES, STUCK_FREE_R, WALL_R,
                                         _rotate, arm_pain, blocked, clear_heading, hit_reaction, on_floor,
                                         target_id_ok, zdist)
from agent.base.pza1 import Shove, Steer
from agent.base.world import me_floor, me_xy

__all__ = ["ThreatGroup", "LEAVE_PLAN", "SIDE_TURNS", "side_hits", "side_dist", "back_cover"]

SIDE_TURNS = (30, -30, 60, -60, 90, -90, 120, -120, 150, -150, 180)   # degrees a heading turns, nearest first
ROAMING = ("steer", "walkTo")   # the running actions under which an unmoving frame counts toward STUCK_FRAMES
LEAVE_PLAN = {"shove": ("flee", "leave"), "door": ("flee", "leave"), "retreat": ("fight", None),
              "run": ("flee", "many")}   # the threat plan of each leave leg (`Threat._threat_plan`)


def _side_passes(world, v, zs):
    """(id, projection) of each of `zs` ((id, zombie) pairs) a leg from the player along unit `v` passes within SIDE_R
    of over its first SIDE_LOOK tiles: ahead of the player (the projection on `v` above 0: one abeam or behind is left by
    the leg) and within SIDE_R of the leg's segment."""
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
            out.append((zid, t))
    return out


def side_hits(world, v, zs):
    """The ids of `zs` a leg along unit `v` passes (`_side_passes`)."""
    return [zid for zid, _ in _side_passes(world, v, zs)]


def side_dist(world, v, zs):
    """Tiles along a leg on unit `v` to the nearest of `zs` it passes (its projection, `_side_passes`), SIDE_LOOK +
    SIDE_R when it passes none: SIDE_CLEAR's least-bad measure (fix 2)."""
    return min((t for _, t in _side_passes(world, v, zs)), default=SIDE_LOOK + SIDE_R)


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
        reset by any other) and the stuck episode's end once the character stands STUCK_FREE_R from its start (fix 2).
        Fix 4: the leave's outputs too (`_clear_leave`), so a line the drag guard answers before the leave's row logs no
        stale `group_retreat`. Plan 34: `group_n`, the standing zombies within GROUP_ENTRY_R (LEAVE_CARE's count, read
        every tick)."""
        self.group_leave, self.drag_fight, self.side_clear = None, None, None
        self.drag_press = False   # Plan 34 Task 3c (DRAG_DEFER): this tick's hand-off of the guard's shove
        self._clear_leave()
        ep = self.drag_episode
        if ep is not None and math.hypot(*(a - b for a, b in zip(me_xy(self.world), ep["at"]))) >= STUCK_FREE_R:
            self.drag_episode = None
        near = self._group_standing(DISENGAGE_R)
        self.group_n = sum(1 for _, _, d in near if d <= GROUP_ENTRY_R)   # Plan 34: LEAVE_CARE's count
        prev = self._group_prev
        self._group_closing = [(zid, z, d) for zid, z, d in near
                               if d <= GROUP_ENTRY_R and zid in prev and d < prev[zid]]
        self._group_prev = {zid: d for zid, _, d in near}
        if (self.world.me or {}).get("moving") is True:
            self._still_n0 = None
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
        the shove in the run's place, the stuck episode opened (or counted) by it; `{spent, why}` when the episode has
        sent its DRAG_SHOVES_PER_EPISODE shoves (fix 2: the run); else None (the rule off, no hit reaction nor unmoving
        count, or no standing zombie within SHOVE_R: the guard's run as before)."""
        if not self.DRAG_GUARD_FIGHT:
            return None
        hit = hit_reaction(self.world) is not None
        if not (hit or self._drag_stuck()):
            return None
        why = "hit" if hit else "stuck"
        ep = self.drag_episode
        if ep is not None and ep["shoves"] >= DRAG_SHOVES_PER_EPISODE:
            self.drag_fight = {"spent": ep["shoves"], "why": why}
            return self.drag_fight
        t = self._front_shove_target()
        if t is None:
            return None
        if ep is None:
            ep = self.drag_episode = {"at": me_xy(self.world), "shoves": 0}
        ep["shoves"] += 1
        self.drag_fight = {"target": t[0], "dist": t[2], "why": why}
        return self.drag_fight

    def _drag_shove(self, flee):
        """The Flee's answer under DRAG_GUARD_FIGHT: on a spent episode's line (fix 2) None, the guard's run, a shove
        of the Flee's still running dropped for it, except under SHOVE_CLEAR (Plan 34 fix C, ruling P34-A: the smoke
        trial `x_trial-ladder-20261109-105452`'s a26, accepted and waiting under the Lua's wait, was superseded one line
        later by the run, so the wait never pressed), where it is held (`drag_fight` {spent, holding, why
        "shove_wait"}) and the run goes once it has ended; else its own shove still running held, else the shove at the
        read's target (superseding a running run); None with no read this tick."""
        if self.drag_fight is None:
            return None
        if "spent" in self.drag_fight:
            if flee.busy() and flee.last.type == "shove":
                if self.SHOVE_CLEAR:   # Plan 34 fix C (ruling P34-A): the Lua's wait presses it at the reaction's end
                    self.drag_fight = {"spent": self.drag_fight["spent"], "holding": flee.last.aid,
                                       "why": "shove_wait"}
                    self.why = {"holding": flee.last.aid}
                    return flee, None
                flee._dropped = flee.last   # the run in its place, whatever the reaction reads
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

    def _least_bad(self, v, zs):
        """Fix 2: (turn, tiles) of the heading off unit `v` (0 or a SIDE_TURNS turn, those the map reads clear over
        STEER_PROBE, else all) whose nearest passed zombie of `zs` lies farthest along the leg (`side_dist`), the nearest
        turn on a tie."""
        turns = (0,) + SIDE_TURNS
        open_ = [t for t in turns if clear_heading(self.world, _rotate(v, t), STEER_PROBE, self.TRANS)] or turns
        best = None
        for t in open_:
            d = side_dist(self.world, _rotate(v, t), zs)
            if best is None or d > best[1]:
                best = (t, d)
        return best

    def _side_clear(self, ans):
        """SIDE_CLEAR (the module docstring) over the threat branch's answer `ans`: a run steer whose leg passes a
        standing zombie turned to the nearest clear heading, else to the least-bad one (fix 2), never a shove; any other
        answer as it is."""
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
        turn, d = self._least_bad(v, zs)
        h = _rotate(v, turn)
        self.side_clear = {"turn": turn, "near": hits, "least_bad": d}
        return policy, Steer(h[0], h[1], cmd.seconds, cmd.gait)

    # ------------------------------------------------------------------------------------------------ GROUP_LEAVE
    def _clear_leave(self):
        """The leave's outputs for this tick, cleared: `leave_leg` (shove | door | retreat | run), `retreat` (the unit
        heading the Fight backpedals on, else None) and the `group_retreat` why."""
        self.retreat, self.group_retreat, self.leave_leg = None, None, None

    def _group_leave(self, inside):
        """GROUP_LEAVE's row (the module docstring): True when the tick takes the leave (a new one, or the running one
        held), else False, `leave` cleared when its end is read; `group_leave` the why either way, `leave_leg` the leg
        (shove | door | retreat | run) and, on the retreat, `retreat` the unit heading away from the standing group's
        centroid."""
        self._clear_leave()
        if not self.GROUP_LEAVE or inside or self.sheltered or self._health() < FLEE_HEALTH_FLOOR:
            self.leave, self.strung_n = None, 0
            return False
        if self.leave is not None:
            door_leg = self.flee is not None and self.flee.plan is not None
            n = len(self._group_standing(DANGER_R if door_leg else GROUP_ENTRY_R))
            if n >= GROUP_LEAVE_N:
                self.strung_n = 0
                self.group_leave = {"n": n}
            elif self._strung_holds(n):
                self.group_leave = {"n": n, "strung_n": self.strung_n}
            else:
                self.leave, self.strung_n = None, 0
                self.group_leave = {"end": "strung", "n": n}
                return False
            self._leave_leg()
            return True
        entry = self._leave_entry()
        if entry is None:
            return False
        self.leave, self.strung_n = dict(entry, since=self.clock()), 0
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
            if self.LEAVE_ENTRY:   # Plan 34 Task 3b: a wall at the back stops no drag-down, the retreat turns off it
                return {"closing": ids, "cover": cover}
            self.group_leave = {"withheld": "cover", "closing": ids, "cover": cover}
            return None
        if not self.LEAVE_ENTRY:
            return None
        group = self._group_standing(GROUP_ENTRY_R)
        if len(group) < GROUP_LEAVE_N or group[0][2] > KEEP_R:
            return None
        return {"on": [zid for zid, _, _ in group], "near": group[0][2]}

    def _strung_holds(self, n):
        """STRUNG_HOLD (Plan 34; the module docstring): a running leave's line reading `n` (fewer than GROUP_LEAVE_N,
        one or more) standing counts one more line under the count (`strung_n`); True while fewer than STRUNG_LINES
        such lines ran in a row (the leave held), False once the end is due. With the rule off, or with none standing
        (nothing to retreat from), the end at once. Plan 35 ENGAGE_HOLD: held while the Fight's melee is engaged
        (`threat.Threat._engage_holds`, logged `engage_hold` {rule "strung"}), the count not run: the leave and its
        heading stay with the reflex's fight."""
        if not self.STRUNG_HOLD or n == 0:
            return False
        if self._engage_holds("strung"):
            return True
        self.strung_n += 1
        return self.strung_n < STRUNG_LINES

    def _leave_leg(self):
        """The leave's leg this tick, the first that applies:
        - `shove` once a leave, at the nearest standing zombie within STAND_MIN_R (round two, trial 2: the engine's own
          shove distance), whatever leg follows;
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
        - else `retreat`, the Fight's stance on the nearest standing zombie with its back heading away from the
          centroid of the standing zombies within GROUP_ENTRY_R, re-read every line (`retreat`, logged `group_retreat`
          {leg, closing, centroid_away})."""
        flee = self.flee
        held_door = flee is not None and flee.plan is not None
        if held_door and self.LEAVE_DOOR_RACE and flee.plan["step"] in ("approach", "open", "enter"):
            close = self._group_standing(DOOR_ABORT_R)
            if close:   # Plan 34 Task 2 (LEAVE_DOOR_RACE): the door given up before its close, the leg re-read
                flee.abort_door()
                held_door = False
                self.group_leave = dict(self.group_leave or {}, door_dropped="abort", near=close[0][2])
        near = self._group_standing(STAND_MIN_R)
        if near and not self.leave.get("shoved") and not held_door:
            self.leave["shoved"] = True
            self.leave_leg = "shove"
            self.group_leave = dict(self.group_leave or {}, leg="shove", target=near[0][0])
            return
        group = self._group_standing(GROUP_ENTRY_R)
        door, refused = self._leave_door(flee, [z for _, z, _ in group])
        if refused is not None:
            self.group_leave = dict(self.group_leave or {}, **refused)
        mx, my = me_xy(self.world)
        cx = sum(z["x"] for _, z, _ in group) / len(group)
        cy = sum(z["y"] for _, z, _ in group) / len(group)
        away = _unit(mx - cx, my - cy)
        ids = [zid for zid, _, _ in group]
        if door is not None:
            self.leave_leg = "door"
            self.group_leave = dict(self.group_leave or {}, leg="door", door=list(door))
            self.group_retreat = {"leg": "door", "closing": ids, "centroid_away": [away[0], away[1]]}
            return
        spent = self.SPENT_LEAVE and self._spent_meet()   # Plan 34 Task 3c: a spent meet leaves three by the run
        if len(group) > (GROUP_LEAVE_N - 1 if spent else RETREAT_MAX_N):   # fix 4: the `many` run as Plan 32's ran
            self.leave_leg = "run"
            self.group_leave = dict(self.group_leave or {}, leg="run", n=len(group))
            if spent:
                self.group_leave["spent"] = True
            self.leave["run"] = True   # Plan 34 Task 3c amendment 1 (RUN_HOLD): the run holds for this leave
            return
        if self.RUN_HOLD and self.leave.get("run"):   # RUN_HOLD: no retreat resumes inside a leave that ran
            self.leave_leg = "run"
            self.group_leave = dict(self.group_leave or {}, leg="run", n=len(group), held=True)
            return
        self.leave_leg = "retreat"
        self.retreat = away
        self.group_leave = dict(self.group_leave or {}, leg="retreat")
        self.group_retreat = {"leg": "retreat", "closing": ids, "centroid_away": [away[0], away[1]]}

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

    def _drag_defers(self, inside):
        """DRAG_DEFER (Plan 34 Task 3c, ruling P34-I; the trial `x_trial-ladder-20261109-132439`, lines 408 to 446: the
        drag guard at `me.attackers` 2 sent its `many` run six times under the leave's retreat, each superseding the
        band's melee, which the next line sent again, and the character moved nowhere) on a drag guard line, after
        `_drag_fight`: True when the leave holds (`leave`) and its leg this line is the retreat, so the guard's row
        sends no run of its own and the line takes the leave's plan; `drag_fight` then carries {deferred "retreat"}
        (beside its {spent, why}, or alone with no shove read), and the episode's one shove, the first line it defers,
        is handed to the Fight as its regain's press (`drag_press`: `fight.Fight._regain_back`). False, the guard's
        row as before, with the switch off, no leave, the guard's shove going this line (`drag_fight` {target}), the
        Flee's shove still running (held under SHOVE_CLEAR, fix C, or dropped for the run), the leave's own first shove
        due (a standing zombie within STAND_MIN_R before it shoved: the guard's run, the leave's shove kept for its
        own line), or the leave's leg this line anything but the retreat (the run above the bound, the door; the leave
        read, so its why is logged), or the leave ended on it."""
        if not self.DRAG_DEFER or self.leave is None:
            return False
        df, flee = self.drag_fight, self.flee
        if df is not None and "spent" not in df:
            return False
        if flee is not None and flee.last is not None and flee.last.type == "shove" and flee.busy():
            return False
        held_door = flee is not None and flee.plan is not None
        if not held_door and not self.leave.get("shoved") and self._group_standing(STAND_MIN_R):
            return False
        if not self._group_leave(inside) or self.leave_leg != "retreat":
            return False
        self.drag_fight = dict(df or {}, deferred="retreat")
        ep = self.drag_episode
        if ep is not None and ep["shoves"] and not ep.get("handed"):
            ep["handed"] = self.drag_press = True
        return True

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

    def _leave_answer(self, flee, held):
        """The Flee's answer on a leave tick that is not the retreat: the one shove at a standing zombie within
        STAND_MIN_R on the leave's first line, else None (a running door walk held by `Survive._answer`, the door's walk
        picked by the Flee's choose, its stand ready)."""
        if self.leave_leg == "shove":
            self.why = {"shove": "leave", "target": self.group_leave["target"]}
            return flee, Shove(self.group_leave["target"])
        return None
