"""The plays' executors (Plan 31 Task 11, variant T; the proposal § 2's table "each executor is a machine that exists
today"): one object per running play, owning its commands (each is its own commands' owner: `send` sends through the
Actions and tells its maneuver), stepping once a tick and checking its bound every tick.

The contract (`Exec`): `bound()` -> None while the play holds, else its end (one of the play's bounds in `plays.json`,
or `lost`, `failed`); `step()` -> (branch, owner, command or None, why): the command to send through `owner` (None holds
the running action, or waits; the owner is the executor itself but for `GoalExec`, whose owner is the ladder step's
policy or goal runner); `send(cmd)` the owner's send `Survive._apply` calls; `target_xy()` the square the play heads to (the decision
line's play target), else None; `aids` the action ids it sent; `age()` wall seconds since it began.

- `FightExec` (`fight`): the shared `Melee` maneuver (`maneuvers.melee`, the reflex `PZAgent_StanceMelee.lua`) within
  `policies.MELEE_RELEASE_R` of the target, its call in one function (`melee_step`: Task 2's PZA/1.10 meet or today's
  PZA/1.9 melee, told apart by `MeleeInputs`' fields, `MELEE_API`);
  beyond it the stance (`Aim` facing the target) standing for a chasing target (let it come: memory
  `combat-approach-not-flee`, the stance at the edge of reach) or walking toward an idle one, and a walk to the
  zombie's square when the line reads blocked (a door between: the path opens it, the zombie met in the stance; never
  a wait at the door: memory `intent-doors-sneak` 1). No back step after a press (the spec's § 4 item 1, J4: PZA/1.10
  has none; on PZA/1.9 the back leg is (0, 0)). Ends: `dead` (unlisted, read dead, or the Melee's `dead`/`kill`),
  `second_standing` (another standing zombie nearer than the target within KEEP_R, or the meet's `handback`: the
  nearest is fought), `lost` (beyond DISENGAGE_R, or the meet's `lost` for no progress or out of reach). Never on
  health (memory `stand-and-fight-dress-first` 1).
- `KiteExec` (`kite`): the stance facing the target (`Aim` with a move vector: the backpedal), the vector toward the
  refuge's square while that runs away from the standing zombies within DANGER_R (`policies.away_vector`), else the
  away vector, turned by `policies.STEER_TURNS` to a clear heading (`policies.clear_heading`: never across a fence),
  else standing; `toward` "stance" backpedals along the away vector. Ends: `alone` (armed and one standing within
  DANGER_R: fight it), `reached` (within REACHED_R of the refuge), `time` (KITE_S).
- `ShelterExec` (`avoid`, `shelter`): `night.shelter_plan` kept to the door (`avoid` toward D<n>) or the building's own
  doors (`avoid` toward B<id>, `shelter`), its steps `night.shelter_step` (approach, open, enter, close), each end read
  by `night.shelter_ended`; the approach at a run while a standing zombie within DANGER_R targets the player, else at a
  walk (the planner's sneak gait, `sneak.SneakGait`, takes a walk near zombies with no target). Ends: `reached` /
  `inside` (the plan done), `shun` (no door left), `contact` (a standing zombie within KEEP_R), `clear` (avoid only:
  outside, none targeting the player within LISTED_R).
- `DressExec` (`dress`): the shared `Dress` maneuver (`maneuvers.dress`: stop, tear, bandage), no ride. Ends:
  `dressed` (its `done`), `nothing` (`failed`), `contact` (`superseded`: a standing zombie within KEEP_R).
- `GoalExec` (`loot`, `travel`, `shelter` answered by the model with a building, and the doctrine's strategic rules):
  Survive's own lower steps in the ladder's order (`_care`, `_need`, `_load`, `_night`, the rag stock, `_goal`), the
  strategic goal layer (`goals.py`, `goal_runner.py`, the LLM source when the session has one) choosing where; a
  model's play pins its building through `PlaySource` (one goal proposed for it). Ends: the pinned goal's end
  (`looted`/`arrived`/`inside`, `stuck` for a failed one), `contact` (a standing zombie within KEEP_R)."""
import dataclasses
import math

from agent.base import pza1
from agent.base.planner import night as N
from agent.base.planner.dispatch import MANEUVERS
from agent.base.planner.goal_policies import ExploreToward, LootBuilding, Shelter
from agent.base.planner.maneuvers.melee import MeleeInputs
from agent.base.planner.policies import (AIM_LEG_S, ATTACK_MARGIN, DANGER_R, DISENGAGE_R, KEEP_R, LISTED_R,
                                         MELEE_RELEASE_R, STEER_TURNS, UNREACHABLE_S, _rotate, away_vector, blocked,
                                         chasing, clear_heading, line_to, on_floor, running, standing, zdist)
from agent.base.planner.tactician.trigger import _inside
from agent.base.world import me_floor, me_xy

KITE_S = 8.0          # wall seconds a kite runs before it ends `time` (a first guess for the trials: two stance legs of
                      # AIM_LEG_S with the re-aims between)
REACHED_R = 1.5       # tiles from a refuge's square at which a kite reached it (the goal layer's ARRIVE_R)
WALK_R = 10.0         # tiles: a fight's target beyond this is walked to, not approached in the stance (inside AIM_R 12:
                      # a first guess for the trials)
STRATEGIC_STEPS = ("care", "need", "load", "night", "stock", "goal")   # Survive's lower steps in the ladder's order
                      # (survive.STEPS without `threat`)
SWING_GUARD_R = 1.0   # tiles: a standing zombie this near starts the melee in any play (the proposal's guard, at P30-A's
                      # SWING_CLOSE_R 1.0, `policies` before Plan 31 Task 2 removed it: the swing close's radius); and
                      # the `closeR` today's PZA/1.9 melee takes
MELEE_KILL_ENDS = ("dead", "kill")   # a Melee's end that is its target's death: PZA/1.9's `dead`, PZA/1.10's `kill`
MELEE_API = "1.10" if "back" not in {f.name for f in dataclasses.fields(MeleeInputs)} else "1.9"   # Task 2's meet
                      # (PZA/1.10: MeleeInputs(mode, reach, floor_swing), no back leg, no closeR, no time end) or
                      # today's (PZA/1.9: MeleeInputs(mode, reach, back, floor_swing, close_r))


def _num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _unit(dx, dy):
    n = math.hypot(dx, dy)
    return None if n == 0.0 else (dx / n, dy / n)


def melee_step(m, mode, world):
    """The Melee's next command at its target (the one call Task 2's API changes): the inputs read afresh (the frame's
    weapon reach plus ATTACK_MARGIN, 0 for the Lua's own; the floor swing allowed), then `Melee.step`. On Task 2's
    PZA/1.10 meet (`MELEE_API` "1.10") that is all its inputs; on today's PZA/1.9 melee the back leg is (0, 0), no back
    step after a press (the spec's section 4 item 1, J4), and the swing close is SWING_GUARD_R (ruling P30-A)."""
    r = (world.weapon or {}).get("reach")
    reach = r + ATTACK_MARGIN if _num(r) and r > 0.0 else 0.0
    if MELEE_API == "1.10":
        m.inputs = MeleeInputs(mode, reach, True)
    else:
        m.inputs = MeleeInputs(mode, reach, (0.0, 0.0), True, SWING_GUARD_R)
    return m.step()


class Exec:
    """One running play (the module docstring's contract)."""

    def __init__(self, sv, play, started):
        self.sv = sv
        self.play = play            # the validated `plays.Play`
        self.started = started      # wall of its start
        self.last = None            # the last Action it sent
        self.aids = []
        self.why = {}

    @property
    def world(self):
        return self.sv.world

    @property
    def actions(self):
        return self.sv.actions

    def age(self):
        return self.sv.clock() - self.started

    def send(self, cmd):
        a = self.actions.send(cmd)
        self.last = a
        self.aids.append(a.aid)
        self.sent(cmd, a)
        return a

    def sent(self, cmd, action):
        """Hook: `cmd` went out as `action`."""

    def busy(self):
        return running(self.actions, self.last)

    def bound(self):
        raise NotImplementedError

    def step(self):
        raise NotImplementedError

    def target_xy(self):
        return None

    def drop(self):
        """The play is replaced or ended: nothing of its own runs on (the maneuvers' late ends are no longer read)."""


def _zid(view, label):
    return next((z["id"] for z in view.get("zombies") or () if z.get("label") == label), None)


def door_square(view, world, label):
    """The door square a view's door label names (`tview.door_rows`' order), else None."""
    from agent.base.planner.tactician.tview import door_rows
    if not isinstance(label, str) or not label.startswith("D"):
        return None
    k = int(label[1:]) - 1
    rows = door_rows(world)
    return rows[k][1] if 0 <= k < len(rows) else None


def building_id(label):
    return int(label[1:]) if isinstance(label, str) and label.startswith("B") else None


class FightExec(Exec):
    """`fight` (the module docstring)."""

    def __init__(self, sv, play, started, view):
        super().__init__(sv, play, started)
        self.zid = _zid(view, play.args["target"])
        self.m = None               # the running Melee
        self.leg = None             # the running stance leg's kind: "stand", "toward" or "walk"
        self.melee_end = None       # the last Melee's end
        self.handback = None        # PZA/1.10: a `handback` end's other zombie {id, d}
        self.lost_why = None        # PZA/1.10: a `lost` end's why (out of range, out of reach, no progress)

    def target(self):
        return self.world.zombies.get(self.zid)

    def target_xy(self):
        z = self.target()
        return None if z is None or z.get("x") is None else [z["x"], z["y"]]

    def sent(self, cmd, action):
        if cmd.TYPE == "melee" and self.m is not None:
            self.m.sent(cmd, action)

    def _observe(self):
        m = self.m
        if m is None:
            return
        m.observe()
        for zid in m.take_kills():
            self.world.note_kill(zid)
            self.sv.dead[zid] = self.sv.clock() + UNREACHABLE_S   # read dead: skipped as the ladder skips one
        m.take_span()
        end = m.over()
        if end is not None:
            self.melee_end = "dead" if end in MELEE_KILL_ENDS else end
            self.handback = getattr(m, "handback", None) if end == "handback" else None
            self.lost_why = getattr(m, "end_why", None) if end == "lost" else None
            self.m = None

    def bound(self):
        self._observe()
        z = self.target()
        if z is None or z.get("x") is None or self.zid in blocked(self.sv.dead, self.sv.clock()):
            return "dead"
        if self.melee_end == "dead":
            return "dead"
        if self.melee_end == "handback":
            return "second_standing"   # PZA/1.10: another standing zombie the press would take, or one by the finish
        if self.melee_end == "lost" and self.lost_why in ("no progress", "out of reach"):
            return "lost"              # PZA/1.10: presses that lowered nothing, or a fallen target the walk never met
        d = zdist(self.world, z)
        if d > DISENGAGE_R:
            return "lost"
        nearer = [o for o in standing(self.world, min(d, KEEP_R), skip=(self.zid,)) if zdist(self.world, o) < d]
        if nearer and not on_floor(z):
            return "second_standing"
        return None

    def step(self):
        z = self.target()
        d = zdist(self.world, z)
        armed = self.world.weapon is not None
        if d <= MELEE_RELEASE_R and self.world.can("melee"):
            mode = "finish" if on_floor(z) else ("strike" if armed else "shove")
            if self.m is None or self.m.target != self.zid:
                self.m = MANEUVERS["melee"](self.world, self.actions, self.sv.clock, self.zid)
            cmd = melee_step(self.m, mode, self.world)
            self.why = {"step": "melee", "mode": mode, "d": round(d, 2), "maneuver": self.m.log() if self.m else None}
            if cmd is not None or (self.m is not None and self.m.running()):
                self.leg = None
                return "threat", self, cmd, self.why
            self.m = None   # ended or superseded at its own step: the stance below this tick
        leg, cmd = self._approach(z, d)
        self.why = {"step": leg, "d": round(d, 2), "melee_end": self.melee_end}
        if leg == self.leg and self.busy():
            return "threat", self, None, self.why
        self.leg = leg
        return "threat", self, cmd, self.why

    def _approach(self, z, d):
        """(leg kind, command) beyond the melee's reach: a walk to the zombie's square far off or behind a blocked line,
        else the stance facing it, standing for a chaser, walking toward an idle one."""
        mx, my = me_xy(self.world)
        if d > WALK_R or line_to(self.world, z) is False or not self.world.can("aim"):
            return "walk", pza1.WalkTo(math.floor(z["x"]) + 0.5, math.floor(z["y"]) + 0.5, "walk")
        if chasing(z) and not on_floor(z):
            return "stand", pza1.Aim(0.0, 0.0, AIM_LEG_S, targetId=self.zid)
        v = _unit(z["x"] - mx, z["y"] - my) or (0.0, 0.0)
        return "toward", pza1.Aim(v[0], v[1], AIM_LEG_S, targetId=self.zid)

    def drop(self):
        self.m = None


class KiteExec(Exec):
    """`kite` (the module docstring)."""

    def __init__(self, sv, play, started, view):
        super().__init__(sv, play, started)
        self.zid = _zid(view, play.args["target"])
        self.refuge = refuge_xy(view, sv.world, play.args["toward"])

    def target_xy(self):
        return list(self.refuge) if self.refuge is not None else None

    def bound(self):
        if self.world.weapon is not None and len(standing(self.world, DANGER_R)) == 1:
            return "alone"
        if self.refuge is not None and math.hypot(self.refuge[0] - me_xy(self.world)[0],
                                                   self.refuge[1] - me_xy(self.world)[1]) <= REACHED_R:
            return "reached"
        z = self.world.zombies.get(self.zid)
        if self.age() >= KITE_S or z is None or z.get("x") is None:
            return "time"
        return None

    def _vector(self):
        mx, my = me_xy(self.world)
        pts = [(z["x"], z["y"]) for z in standing(self.world, DANGER_R)]
        away = away_vector(self.world, pts) if pts else None
        v = None
        if self.refuge is not None:
            r = _unit(self.refuge[0] - mx, self.refuge[1] - my)
            if r is not None and (away is None or r[0] * away[0] + r[1] * away[1] > 0.0):
                v = r
        v = v or away
        if v is None:
            return (0.0, 0.0)
        for turn in STEER_TURNS:
            t = _rotate(v, turn)
            if clear_heading(self.world, t):
                return t
        return (0.0, 0.0)

    def step(self):
        v = self._vector()
        self.why = {"step": "back", "v": [round(v[0], 3), round(v[1], 3)]}
        if self.busy():
            return "threat", self, None, self.why
        return "threat", self, pza1.Aim(v[0], v[1], AIM_LEG_S, targetId=self.zid), self.why


def refuge_xy(view, world, label):
    """The square centre a refuge label names: a door's approach square (outside), else the door square; a building's
    first exterior door's approach square, else its nearest room square; None for "stance" or an unknown label."""
    sq = door_square(view, world, label)
    if sq is None:
        b = building_id(label)
        if b is None:
            return None
        doors = N.exterior_doors(world, b, me_floor(world))
        if doors:
            sq = doors[0]
        else:
            rooms = world.interiors().get(b) or ()
            if not rooms:
                return None
            mx, my = me_xy(world)
            r = min(rooms, key=lambda q: (math.hypot(q[0] + 0.5 - mx, q[1] + 0.5 - my), q))
            return (r[0] + 0.5, r[1] + 0.5)
    out = N.approach_square(world, sq) or sq
    return (out[0] + 0.5, out[1] + 0.5)


class ShelterExec(Exec):
    """`avoid` and `shelter` (the module docstring)."""

    def __init__(self, sv, play, started, view):
        super().__init__(sv, play, started)
        label = play.args.get("toward") or play.args.get("building")
        door = door_square(view, sv.world, label)
        b = building_id(label)
        if door is not None:
            b = sv.world.door_building(door)
        self.building, self.door = b, door
        self.plan = None
        if b is not None:   # the named door's plan, else the building's own doors (a door marked stuck from outside)
            self.plan = N.shelter_plan(sv.world, b, door=door) if door is not None else None
            self.plan = self.plan or N.shelter_plan(sv.world, b)
        self.ended = None           # the last step's end read (`night.shelter_ended`)
        self._read = None           # the last Action whose end was read

    def target_xy(self):
        if self.plan is None:
            return None
        d = self.plan["doors"][self.plan["door_i"]]
        return [d[0] + 0.5, d[1] + 0.5]

    def bound(self):
        if self.plan is None:
            return "failed"
        a = self.last
        if a is not None and self.actions.done(a) and self._read is not a:
            self._read = a
            self.ended = N.shelter_ended(self.plan, a)
            if self.ended == "shun":
                return "shun"
        if self.plan["step"] == "done":
            return "reached" if self.play.play == "avoid" else "inside"
        if standing(self.world, KEEP_R):
            return "contact"
        if self.play.play == "avoid" and not _inside(self.world) and not any(
                chasing(z) for z in standing(self.world, LISTED_R)):
            return "clear"
        return None

    def step(self):
        if self.busy():
            self.why = {"step": self.plan["step"], "holding": self.last.aid}
            return "threat", self, None, self.why
        cmd, step = N.shelter_step(self.world, self.plan)
        if cmd is not None and cmd.TYPE == "walkTo" and any(chasing(z) for z in standing(self.world, DANGER_R)):
            cmd = pza1.WalkTo(cmd.x, cmd.y, "run")   # a chaser near: at a run (never a sprint, ruling P24-O)
        self.why = {"step": step, "building": self.building, "ended": self.ended}
        return "threat", self, cmd, self.why


class DressExec(Exec):
    """`dress` (the module docstring)."""

    def __init__(self, sv, play, started, view):
        super().__init__(sv, play, started)
        self.part = int(play.args["part"][1:])
        self.m = MANEUVERS["dress"](sv.world, sv.actions, sv.clock, part=self.part, ride=False)

    def sent(self, cmd, action):
        self.m.sent(cmd, action)

    def busy(self):
        return self.m.running()

    def bound(self):
        self.m.observe()
        end = self.m.over()
        return {"done": "dressed", "failed": "nothing", "superseded": "contact"}.get(end) if end else None

    def step(self):
        cmd = self.m.step()
        self.why = dict(self.m.log())
        return "care", self, cmd, self.why


class PlaySource:
    """The goal source a model's strategic play pins (the module docstring's `GoalExec`): `pin` one goal, proposed
    once (`LootBuilding`, `ExploreToward` to the place's door or square, `Shelter`), else the session's own source
    (scripted, or the LLM's), whose NAME it reports."""

    def __init__(self, inner):
        self.inner = inner
        self.pin = None             # the goal to propose once, else None
        self.pinned = None          # the goal the runner took from the pin
        self.NAME = getattr(inner, "NAME", None)

    def propose(self, view):
        if self.pin is not None:
            g, self.pin = self.pin, None
            self.pinned, self.NAME = g, "tactician"
            return g
        out = self.inner.propose(view)
        self.NAME = getattr(self.inner, "NAME", None)
        return out

    def __getattr__(self, name):   # the runner and the drivers read the inner source's own fields (calls, totals)
        return getattr(self.inner, name)


def pin_goal(play, view, world):
    """The goal a model's strategic play names, else None (`travel` to `explore`: the source's own)."""
    a = play.args
    if play.play == "loot":
        b = building_id(a["building"])
        return None if b is None else LootBuilding(b)
    if play.play == "shelter":
        b = building_id(a["building"])
        return None if b is None else Shelter(b)
    if play.play == "travel":
        xy = refuge_xy(view, world, a["to"])
        return None if xy is None else ExploreToward(int(math.floor(xy[0])), int(math.floor(xy[1])))
    return None


class GoalExec(Exec):
    """The strategic plays (the module docstring)."""

    def __init__(self, sv, play, started, view, pin=None):
        super().__init__(sv, play, started)
        self.pin = pin              # the goal pinned for it (a model's answer), else None
        self.branch = None
        self.done_end = None

    def target_xy(self):
        g = getattr(self.sv.goals, "current", None)
        args = g.args() if g is not None else {}
        if _num(args.get("x")) and _num(args.get("y")):
            return [args["x"] + 0.5, args["y"] + 0.5]
        b = args.get("building")
        if isinstance(b, int) and not isinstance(b, bool):
            box = self.world.building_boxes().get(b)
            if box is not None:
                return [(box[0] + box[2] + 1) / 2.0, (box[1] + box[3] + 1) / 2.0]
        return None

    def bound(self):
        if standing(self.world, KEEP_R):
            return "contact"
        src = self.sv.goals.source
        if (self.pin is not None and self.pin.state == "running" and getattr(src, "pin", None) is None
                and self.sv.goals.current is not self.pin):
            return "stuck"   # the runner refused the pinned goal (cooled): it never ran
        if self.pin is not None and self.pin.state != "running":
            return {"done": {"loot": "looted", "travel": "arrived", "shelter": "inside"}.get(self.play.play, "arrived")
                    }.get(self.pin.state, "stuck")
        return None

    def step(self):
        """Survive's lower steps in STRATEGIC_STEPS order, the first that answers (a cooled command passed over, as the
        ladder's `_assess_ladder` passes it; the care's own retries never are)."""
        sv = self.sv
        tried = {}
        for name in STRATEGIC_STEPS:
            sv.why = {}
            ans = sv._care_stock() if name == "stock" else getattr(sv, "_" + name)()
            tried[name if name != "stock" else "care"] = dict(sv.why)
            if ans is None:
                continue
            owner, cmd = ans
            if cmd is not None and sv._cooling(cmd) and not sv.care.owns(cmd):
                continue
            self.branch = "care" if name == "stock" else name
            self.why = {"step": name, "tried": tried}
            return self.branch, owner, cmd, self.why
        self.branch = None
        self.why = {"step": None, "tried": tried}
        return None, None, None, self.why


EXECS = {"fight": FightExec, "kite": KiteExec, "avoid": ShelterExec, "shelter": ShelterExec, "dress": DressExec}
