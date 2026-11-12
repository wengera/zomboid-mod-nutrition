"""The action clock (Plan 36 Task 4; the spec `2026-11-11-plan-36-the-engagement-design.md` § 3.4; Angus's direction,
memory `finish-actions-gain-distance`: an action needed near zombies is done by gaining distance once and finishing it,
never half-done then fled repeatedly). The reading behind it: F21 (`f_goals_21-20261111-150552`, decision lines 427 to
494) started seven rips with the nearest standing 3.4 to 5.7 tiles off, each superseded 1 to 4 s later by the threat
branch's next steer, and sent no bandage while three parts bled from 68 to 13 health; a Plan 35 trial took a bite at a
door interaction with two zombies thumping at 0.3 tiles (P31-T, not evidence).

- The time to contact (`time_to_contact`): per listed zombie not read dead, its distance less CONTACT_R over its clock
  speed (`ActionClock.speed`), 0 inside CONTACT_R; the speed the larger of its own recent speed (its displacement over
  the last CLOCK_SPEED_S of the frames the clock observed, `ActionClock.observe`, read only over CLOCK_SPEED_MIN_S or
  more) and its state's floor (`speed_floor`): LUNGE_TPS lunging or attacking, CRAWL_TPS a crawler, FLOOR_TPS fallen,
  WALK_TPS walking, pathing, turning, staggering or rising, or chasing (`hasTarget`) in any other state; an idle
  zombie with no target has no floor (its own speed alone: one standing still never closes). The smallest of them is
  the clock's `ttc`, None with nobody listed.
- A timed action (`action_kind`: `rip`, `unwear`, a standing `bandage`, the `loot` interact, the door's `open` or
  `close` interact, a `scan`; a riding bandage, `keepMoving`, stands nowhere and is none) starts only when the clock
  allows it (`ActionClock.allows`): `ttc` None or above its duration (ACTION_S) plus ACTION_MARGIN_S.
- The gate (`ClockGate`, the mixin `care_yield.CareYield` derives from, so `threat.Threat` and `survive.Survive`
  too; `ACTION_CLOCK`, on by default): `_clock_gate` asks the clock for every non-threat branch's timed command
  (`Survive._assess_ladder`: the care's Dress steps and its old bleeding step, the care's rag stock, the goals' loot,
  door and scan, the night's door; the Dress's `stop` asked with the step the Dress would take after it, `care.Care.next_kind`) and the threat branch's own
  (`Threat._threat`: the flee's and the doorway's door interact). Allowed, the command goes, logged `clock {action, ttc,
  need, waited}`. Refused: the gain-distance leg (`_clock_refuse`): one episode per action (`ClockLeg`, keyed by the
  branch and the command), steer legs of CLOCK_LEG_S at a run along the room ring's most open heading within
  ROOM_OPEN_DEG of straight away from the nearest listed zombie (`policies.room_open_heading`; no ring, the first
  clear turn of STEER_TURNS, else straight away), re-aimed while the clock refuses, at most CLOCK_EPISODE_S; logged `clock
  {action, ttc, need, waited, refused true, leg}`. Fix 2 (PZA/1.15: the Tend side slot admits a `rip` with
  keepMoving, #4735): a refused care rip rides that leg once it runs (`Dress.ride_rip`: the rip sent with keepMoving
  beside the steer, in place of the stop), logged `clock {action rip, ride true, ..}`; the running riding rip is held
  and cut by the clock as any timed action; an unwear and a bandage still wait for the stop. Then the action goes at the first tick the clock allows; past
  CLOCK_EPISODE_S the action waits (`spent`) and the threat branch decides. A threat command refused with a standing
  zombie within KEEP_R, or once its episode is spent, is the melee instead (`clock_fight`: the Fight at that zombie,
  `Threat._threat_plan`'s first row).
- A running timed action (`_clock_hold`, the threat branch's first read once it holds a threat) is cut only by the
  clock: while `ttc` reads ACTION_MARGIN_S or more the threat branch holds it (no steer, no flee leg, no other row
  supersedes it; logged `clock {action, ttc, need, running}`); under the margin the cut (`clock_cut`, logged `clock
  {.., cut true}`) is the Fight at the zombie of the smallest time to contact, whose melee the dispatch sends
  (`dispatch.FightDispatch`, Plan 35's `_contact_rule` reads the same contact), never a steer.
- The care chain (`care_yield.CareYield._care_commit` under the clock): the threat branch yields to a care action
  wanted or running whenever no standing zombie is within KEEP_R (the Fight's, rule (a)) and no cut or spent episode
  stands, and the clock decides each step at the care branch; Plan 34's column bar (LEAVE_CARE) and the yields'
  distance rules (CARE_R, CARE_HOLD_R, the closing read) are the clock's now, the ride (P24-U's keepMoving bandage) the
  one yield kept beside it. The rip rides the walk (fix 2: `RipClothing` carries `CanBeDoneWhileWalking`, #4735, and
  PZA/1.15's side slot, `PZAgent_Tend.lua` K.RIDE_TYPES, admits it with keepMoving); the unwear (a shirt stops on a
  walk) and the bandage go at the stop the clock allows.
"""
import math

from agent.base.planner.policies import (ACTION_MARGIN_S, ACTION_S, CLOCK_EPISODE_S, CLOCK_LEG_S, CLOCK_SPEED_MIN_S,
                                         CLOCK_SPEED_S, CONTACT_R, CRAWL_TPS, FLEE_GAIT, FLOOR_TPS, KEEP_R, LUNGE_TPS,
                                         STEER_TURNS, WALK_TPS, Policy, _rotate, away_vector, blocked, chasing,
                                         clear_heading, on_floor, room_open_heading, standing, target_id_ok, zdist)
from agent.base.pza1 import Steer

LUNGE_STATES = ("lunge", "lunge-network", "attack", "attack-network")   # PZA/1.9's `state` names at LUNGE_TPS
WALK_STATES = ("walktoward", "walktoward-network", "pathfind", "turnalerted", "staggerback", "hitreaction",
               "getup")   # ... at WALK_TPS (a zombie moving, or about to)
TIMED = ("rip", "unwear", "bandage", "loot", "door", "scan")   # the clock's action kinds (ACTION_S's keys)


def _num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def action_kind(type_, args):
    """The clock's kind of a command or an Action by its type and args (the module docstring), else None."""
    if type_ in ("rip", "unwear", "scan"):
        return type_
    if type_ == "bandage":
        return None if args.get("keepMoving") is True else "bandage"
    if type_ == "interact":
        k = args.get("kind")
        return "loot" if k == "loot" else ("door" if k in ("open", "close") else None)
    return None


def cmd_kind(cmd):
    """`action_kind` of a command dataclass."""
    return action_kind(cmd.TYPE, cmd.args())


def speed_floor(z):
    """Zombie record `z`'s state floor in tiles a second (the module docstring)."""
    if on_floor(z):
        return CRAWL_TPS if z.get("crawler") is True else FLOOR_TPS
    st = z.get("state")
    if st in LUNGE_STATES:
        return LUNGE_TPS
    if chasing(z) or st in WALK_STATES:
        return WALK_TPS
    return 0.0


def time_to_contact(world, tracks=None, skip=()):
    """`({id: seconds}, smallest or None)` over the listed zombies with a position not in `skip` (the module
    docstring); `tracks` an `ActionClock`'s recent positions (None: the floors alone)."""
    per = {}
    for zid, z in world.zombies.items():
        if zid in skip or not _num(z.get("x")) or not _num(z.get("y")):
            continue
        s = speed_floor(z)
        own = _own_speed((tracks or {}).get(zid))
        if own is not None and own > s:
            s = own
        gap = max(0.0, zdist(world, z) - CONTACT_R)
        per[zid] = 0.0 if gap <= 0.0 else (gap / s if s > 0.0 else math.inf)
    return per, (min(per.values()) if per else None)


def _own_speed(track):
    """A track's displacement over its span, tiles a second, None under CLOCK_SPEED_MIN_S of it."""
    if not track or len(track) < 2:
        return None
    (t0, x0, y0), (t1, x1, y1) = track[0], track[-1]
    if t1 - t0 < CLOCK_SPEED_MIN_S:
        return None
    return math.hypot(x1 - x0, y1 - y0) / (t1 - t0)


class ActionClock:
    """The clock (the module docstring): `observe(world, skip)` once a planner tick, then `ttc`, `allows`, `need`."""

    def __init__(self):
        self.tracks = {}     # zombie id -> [(wall s, x, y)] of the frames observed over the last CLOCK_SPEED_S
        self.per = {}        # this tick: zombie id -> its time to contact, seconds
        self.ttc = None      # this tick: the smallest, None with nobody listed
        self.nearest = None  # this tick: the id of the smallest (ties by repr), None with nobody listed

    def observe(self, world, skip=()):
        """The tracks fed with this frame's positions (the frame's `wallMs`; none without one), aged to CLOCK_SPEED_S,
        a zombie no longer listed dropped; then this tick's times to contact."""
        wall = world.frame_wall_ms
        listed = set(world.zombies)
        self.tracks = {zid: tr for zid, tr in self.tracks.items() if zid in listed}
        if _num(wall):
            t = wall / 1000.0
            for zid, z in world.zombies.items():
                x, y = z.get("x"), z.get("y")
                if not (_num(x) and _num(y)):
                    continue
                tr = self.tracks.setdefault(zid, [])
                if tr and tr[-1][0] >= t:
                    continue
                tr.append((t, x, y))
                while tr and t - tr[0][0] > CLOCK_SPEED_S:
                    tr.pop(0)
        self.per, self.ttc = time_to_contact(world, self.tracks, skip)
        self.nearest = min(self.per, key=lambda zid: (self.per[zid], repr(zid))) if self.per else None

    def speed(self, zid, z):
        """Zombie `zid`'s clock speed (record `z`), tiles a second."""
        own = _own_speed(self.tracks.get(zid))
        s = speed_floor(z)
        return own if own is not None and own > s else s

    @staticmethod
    def need(kind, duration_s=None):
        """The seconds a `kind` action needs on the clock: its duration (ACTION_S, or `duration_s`) plus the margin."""
        return (ACTION_S[kind] if duration_s is None else duration_s) + ACTION_MARGIN_S

    def allows(self, kind, duration_s=None):
        """The smallest time to contact exceeds the action's duration plus ACTION_MARGIN_S (nobody listed: True)."""
        return self.ttc is None or self.ttc > self.need(kind, duration_s)

    def under_margin(self):
        """A running timed action is cut: the smallest time to contact under ACTION_MARGIN_S."""
        return self.ttc is not None and self.ttc < ACTION_MARGIN_S


class ClockLeg(Policy):
    """One refused action's gain-distance episode (the module docstring): `key` the action it gains distance for,
    `since` the wall of its first refusal, its steer legs its own sends."""

    def __init__(self, world, actions, clock, key):
        super().__init__(world, actions, clock)
        self.key = key
        self.since = clock()
        self.legs = 0

    def choose(self):
        return None

    def sent(self, cmd, action):
        self.legs += 1

    def spent(self):
        return self.clock() - self.since >= CLOCK_EPISODE_S


def _ttc(v):
    """A time to contact for the log: None for none listed, None for one that never closes (JSON has no infinity)."""
    return None if v is None or math.isinf(v) else round(v, 3)


class ClockGate:
    """The gate (the module docstring): `care_yield.CareYield`'s mixin, its state `Survive`'s (`_init_clock`)."""

    ACTION_CLOCK = True   # Plan 36 Task 4 (in survive.T21_SWITCHES): the action clock; off, the yields and the
                          # supersedes before it (CARE_COMMIT's leg, LEAVE_CARE's bar, the threat's steer over a care)

    def _init_clock(self):
        self.action_clock = ActionClock()
        self.clock_leg = None    # the running refused action's episode (`ClockLeg`), else None
        self.clock_cut = None    # this tick: {action, ttc, target} when the clock cut a running timed action
        self.clock_fight = None  # this tick: {action, ttc, target} when a refused threat command sends the melee
        self.clock_now = None    # this tick: the threat branch's `clock` why, else None

    def _clock_on(self):
        """The rule runs: ACTION_CLOCK on, the clock made (`_init_clock`), and the ladder deciding (a variant's
        `assess`, `Survive(control=...)`, keeps its own rules and goldens)."""
        return (self.ACTION_CLOCK and getattr(self, "action_clock", None) is not None
                and getattr(self, "_control_assess", None) is None)

    def _clock_read(self):
        """The tick's read (`Survive._read`): the clock observed over the World, the ids read dead left out."""
        self.clock_cut, self.clock_fight, self.clock_now = None, None, None
        if self._clock_on():
            self.action_clock.observe(self.world, blocked(self.dead, self.clock()))

    def _clock_why(self, kind, **extra):
        ck = self.action_clock
        why = {"action": kind, "ttc": _ttc(ck.ttc), "need": round(ck.need(kind), 3) if kind in ACTION_S else None}
        why.update(extra)
        return why

    def _clock_waited(self, key):
        leg = self.clock_leg
        return round(self.clock() - leg.since, 3) if leg is not None and leg.key == key else 0.0

    def _clock_target(self):
        """The zombie the clock's melee goes at: the smallest time to contact among the standing ones a Fight may
        target, else among any it may target; None with none."""
        ck = self.action_clock
        ids = [zid for zid in ck.per if target_id_ok(zid)]
        standing_ids = [zid for zid in ids if not on_floor(self.world.zombies[zid])]
        pool = standing_ids or ids
        return min(pool, key=lambda zid: (ck.per[zid], repr(zid))) if pool else None

    def _clock_running(self):
        """`(action, kind)` of the running timed action (`Actions.current`, `action_kind`), else None."""
        a = self.actions.current
        if a is None:
            return None
        f = getattr(self, "fight", None)
        if a.args.get("keepMoving") is True and f is not None and f._engaged():
            return None   # Plan 37 Task 3 fix 3: a rip riding the engaged melee, whose leg the melee is
        kind = action_kind(a.type, a.args)
        return None if kind is None else (a, kind)

    def _clock_hold(self):
        """The threat branch's first read (the module docstring): `(None, None)` holding a running timed action the
        clock lets run, logged `clock {.., running}`; None otherwise, `clock_cut` set when the clock cut it."""
        run = self._clock_running()
        if run is None:
            return None
        a, kind = run
        ck = self.action_clock
        if ck.under_margin():
            target = self._clock_target()
            self.clock_cut = {"action": kind, "ttc": _ttc(ck.ttc), "target": target, "aid": a.aid}
            self.clock_now = self._clock_why(kind, cut=True, running=a.aid, target=target)
            return None
        self.clock_now = self._clock_why(kind, running=a.aid)
        return None, None

    def _clock_kind(self, owner, cmd):
        """The clock's kind of `cmd` sent by `owner`: the care's Dress `stop` asked with the step after it
        (`care.Care.next_kind`), else `cmd_kind`."""
        if cmd is None:
            return None
        if cmd.TYPE == "stop" and owner is getattr(self, "care", None) and self.care.owns(cmd):
            return self.care.next_kind()
        return cmd_kind(cmd)

    def _clock_gate(self, branch, owner, cmd):
        """`(owner, command, why)` for a branch's answer (the module docstring): unchanged with no timed kind (why
        None); allowed, unchanged with its `clock` why (the episode for it ended); refused, the gain-distance leg's
        (`_clock_refuse`)."""
        kind = self._clock_kind(owner, cmd)
        if kind is None or not self._clock_on():
            return owner, cmd, None
        key = (branch, cmd.TYPE) + tuple(sorted((k, v) for k, v in cmd.args().items() if k != "keepMoving"))
        if owner is getattr(self, "care", None):
            key = ("care", self.care.commit_key())   # one episode per care commitment, its steps included
        if self.action_clock.allows(kind):
            why = self._clock_why(kind, waited=self._clock_waited(key))
            self.clock_leg = None
            return owner, cmd, why
        fought = getattr(self, "_fight_disposed", None)
        if fought is not None and fought():   # Plan 37 Task 3 fix 6: the string is the gain-distance leg
            return owner, None, self._clock_why(kind, refused=True, held="disposition")
        out = self._clock_refuse(kind, key, ride=kind == "rip" and owner is getattr(self, "care", None))
        if kind == "rip" and owner is getattr(self, "care", None) and out[0] is self.clock_leg and out[1] is None:
            ride = self._clock_ride_rip()
            if ride is not None:   # fix 2: the refused rip rides the running leg (the Tend side slot, PZA/1.15)
                return owner, ride, dict(out[2], ride=True, dress=self.care.dressing().log())
        return out

    def _clock_ride_rip(self):
        """Plan 36 Task 4 fix 2 (the module docstring): the care's running Dress's riding rip (`Dress.ride_rip`)
        while the clock's gain-distance leg runs, else None (no Dress, its pick no rip, or its own command running)."""
        d = self.care.dressing() if self.clock_leg is not None and self.clock_leg.busy() else None
        return None if d is None else d.ride_rip()

    def _clock_refuse(self, kind, key, ride=False):
        """The refused action's episode (the module docstring): `(leg, Steer)` re-aiming, `(leg, None)` while its leg
        runs, `(None, None)` once spent (the action waits); each with its `clock` why. Fix 2b: a leg the action will
        ride (`ride`: the care's rip, `_clock_ride_rip`) runs for that action's duration plus ACTION_MARGIN_S
        (`ActionClock.need`), so the riding rip never outlasts it and finishes standing; any other leg CLOCK_LEG_S."""
        leg = self.clock_leg
        if leg is None or leg.key != key:
            leg = self.clock_leg = ClockLeg(self.world, self.actions, self.clock, key)
        leg.world, leg.actions = self.world, self.actions
        waited = round(self.clock() - leg.since, 3)
        if leg.spent():
            return None, None, self._clock_why(kind, waited=waited, refused=True, spent=True)
        if leg.busy():
            return leg, None, self._clock_why(kind, waited=waited, refused=True, leg=leg.last.aid)
        heading = self._clock_heading()
        if heading is None:
            return None, None, self._clock_why(kind, waited=waited, refused=True, leg=None)
        (vx, vy), opened = heading
        seconds = round(self.action_clock.need(kind), 3) if ride else CLOCK_LEG_S
        why = self._clock_why(kind, waited=waited, refused=True, leg="sent", heading=[vx, vy], seconds=seconds)
        if opened is not None:
            why["room_open"] = opened
        return leg, Steer(vx, vy, seconds, FLEE_GAIT), why

    def _clock_threat(self, held, breach, ans):
        """The threat branch's own timed command (`ans` from `Threat._decide`: the flee's or the doorway's door
        interact) asked the clock (the module docstring): allowed, unchanged; refused with nobody standing within
        KEEP_R, the gain-distance leg; refused in contact, or with its episode spent, the melee: `clock_fight` set
        and the decision taken again (`Threat._threat_plan`'s first row: the Fight at the clock's zombie)."""
        if not self._clock_on() or ans is None or ans[1] is None or self.clock_cut is not None:
            return ans
        cmd = ans[1]
        kind = cmd_kind(cmd)
        if kind is None:
            return ans
        key = ("threat", cmd.TYPE) + tuple(sorted(cmd.args().items()))
        ck = self.action_clock
        if ck.allows(kind):
            self.clock_now = self._clock_why(kind, waited=self._clock_waited(key))
            self.clock_leg = None
            return ans
        if not self._clock_contact():
            owner, out, why = self._clock_refuse(kind, key)
            if not why.get("spent"):
                self.clock_now = why
                return owner, out
        target = self._clock_target()
        self.clock_fight = {"action": kind, "ttc": _ttc(ck.ttc), "target": target}
        why = self._clock_why(kind, waited=self._clock_waited(key), refused=True, fight=target)
        ans = self._decide(held, breach)
        self.clock_now = why
        return ans

    def _clock_spent(self, key):
        """The care commitment `key`'s episode is spent (its action waits, the threat branch decides)."""
        leg = self.clock_leg
        return leg is not None and leg.key == ("care", key) and leg.spent()

    def _clock_heading(self):
        """`((vx, vy), degrees or None)`: the gain-distance heading, away from the nearest listed zombie (one read
        dead aside) along the room ring's most open heading (`room_open_heading`), else the first clear turn of
        STEER_TURNS, else straight away; None with nobody listed."""
        skip = blocked(self.dead, self.clock())
        zs = [z for zid, z in self.world.zombies.items() if zid not in skip and _num(z.get("x")) and _num(z.get("y"))]
        if not zs:
            return None
        z = min(zs, key=lambda q: zdist(self.world, q))
        v = away_vector(self.world, [(z["x"], z["y"])])
        if v is None:
            return None
        h, opened = room_open_heading(self.world, v)
        if opened is not None:
            return (round(h[0], 6), round(h[1], 6)), opened
        for deg in STEER_TURNS:
            w = _rotate(v, deg)
            if clear_heading(self.world, w, trans=self.TRANS):
                return (round(w[0], 6), round(w[1], 6)), None
        return (round(v[0], 6), round(v[1], 6)), None

    def _clock_contact(self):
        """A standing zombie (one read dead or unreachable aside) within KEEP_R: the Fight's, rule (a)."""
        return bool(standing(self.world, KEEP_R, self._skipped()))
