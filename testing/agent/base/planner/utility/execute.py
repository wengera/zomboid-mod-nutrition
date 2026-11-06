"""The executors (Plan 31 Task 11 U): the held act turned into the tick's command through the shared plays (the
maneuvers, the goal runner, the ladder's need steps) and the planner's geometry, never the ladder's decisions. One
executor runs per held act (`core.Utility`); it reads its own actions' ends (`observe`, which sets `ended`) and gives
its next command (`step` -> `Step`, or None when it ended at once). Every send goes through its `Owner` (a
`policies.Policy`), which hands a maneuver its own sends.

- `FightExec` (`fight:<id>`): the door read's plan when the door read opens a door on the target (`door_held`'s
  `FightDoorHeld._door_open_cmd`: the stance to the post, the open, the meet); within MELEE_START_R of a standing
  target (or of a fallen one) the `Melee` maneuver (`melee_step`, THE CALL SITE, its inputs by `melee_inputs` under
  either `MeleeInputs`: Task 2's PZA/1.10 meet, or today's with no back leg and the swing close off), mode `finish` at
  a fallen target, `shove` when spent (`select.spent`), else `strike`; farther, the approach: a route through the door
  of a known blocked edge (`edges.route_record`, at a walk), a walk beyond STANCE_R, else the stance (`Aim`) standing
  facing an aware chaser (it comes: memory `combat-approach-not-flee`) or walking toward an unaware or fallen one. A
  build without `melee` presses `Attack` or `Stomp` itself. Ends: `dead` (a kill read: PZA/1.9's `done dead`,
  PZA/1.10's `done kill`; or the target read dead), `gone` (no longer listed), `far` (beyond DISENGAGE_R), `out of
  reach` (the walk to a fallen target never closed: PZA/1.9's `out of reach`, PZA/1.10's `lost` why `out of reach`; the
  target left unreachable for SEEK_SKIP_S), `no progress` (PZA/1.10's `lost` why `no progress`: UNREACHABLE_S) and
  `crowd` (PZA/1.9's `crowd`, PZA/1.10's `handback`: another standing zombie in the press's way, which the next
  selection fights); any other end (a supersede, PZA/1.10's `lost` out of range) starts a new melee on the next step.
- `DressExec` (`dress:<part>`): one `Dress` maneuver (`dispatch.MANEUVERS["dress"]`: the stop, the tear, the bandage),
  riding the held walk when the candidate rides; ends with the maneuver (`done`, `failed`, `superseded`), a failure
  noted for the context's `dress_cooled`.
- `RetreatExec` (`retreat:door:<x>,<y>`): one run (`WalkTo` at a run) to the filter's post; ends `arrived` (the walk
  done or the player within AT_FILTER_R of the post: `Utility.at_filter` set, so the next selection fights from the
  stance there) or `failed` (the walk failed for anything but a supersede).
- `GoalExec` (`travel`, `loot`, `sneak`): the goal runner (`Survive._goal`); ends `idle` when it holds nothing.
- `NeedsExec` (`needs:<branch>`): the answer the context read this tick (`Utility._needs`); ends when none.
- `RestExec` (`rest`): nothing sent (the stance is not held; the endurance comes back standing).
"""
import dataclasses
import math

from agent.base.planner.dispatch import MANEUVERS
from agent.base.planner.door_held import FightDoorHeld
from agent.base.planner.edges import edge_read, route_record
from agent.base.planner.maneuvers.melee import MeleeInputs
from agent.base.planner.policies import (AIM_LEG_S, ATTACK_MARGIN, DISENGAGE_R, KEEP_R, MELEE_RELEASE_R, PREEMPTED,
                                         SEEK_SKIP_S, UNREACHABLE_S, Policy)
from agent.base.planner.utility import acts as A
from agent.base.planner.utility import select as S
from agent.base.pza1 import Aim, Attack, Stomp, WalkTo

MELEE_START_R = KEEP_R    # tiles: a standing target this near is the melee's (the ladder's dispatch point, its stance
                          # legs within KEEP_R: `dispatch.MELEE_LEGS`)
STANCE_R = 6.0            # tiles: a target farther than this is walked to, nearer the stance walks (DANGER_R's 6)
WALK_RESEND_S = 2.0       # seconds an approach walk runs before it is aimed again at the moving target (a first guess)
OFF_ENDS = ("not loaded", "bad args", "unknown type")   # the melee's ends after which this fight presses itself
                                                        # (`dispatch.OFF_ENDS`)
KILL_ENDS = ("dead", "kill")        # the melee's kill: PZA/1.9's `done dead`, PZA/1.10's `done kill` (Task 2)
HANDBACK_ENDS = ("crowd", "handback")   # another standing zombie in the press's way: PZA/1.9's `crowd`, PZA/1.10's
                                        # `done handback` (why crowd or standing): the next selection fights it


def melee_inputs(mode, reach, floor_swing, cls=MeleeInputs):
    """The `MeleeInputs` of one send under either API, told by the class's fields (the README's Task 2 note): Task 2's
    PZA/1.10 `MeleeInputs(mode, reach, floor_swing)` (the meet: no back step and no swing close by construction);
    today's PZA/1.9 `(mode, reach, back, floor_swing, close_r)` with no back leg ((0, 0): J4, the back step is the
    worst answer) and the swing close off (closeR 0: the swing within the reach, #4596)."""
    if "back" not in {f.name for f in dataclasses.fields(cls)}:
        return cls(mode, reach, floor_swing)
    return cls(mode, reach, (0.0, 0.0), floor_swing, 0.0)


@dataclasses.dataclass
class Step:
    branch: object
    owner: object
    cmd: object
    why: dict


class Owner(Policy):
    """The sender of one executor: its last action (`busy`), and a maneuver's own sends handed back to it."""

    def __init__(self, world, actions, clock):
        super().__init__(world, actions, clock)
        self.m = None
        self._from_m = None

    def choose(self):   # never asked: the executors decide
        return None

    def send(self, cmd):
        action = self.actions.send(cmd)
        self.last = action
        if self.m is not None and cmd is self._from_m:
            self.m.sent(cmd, action)
        self._from_m = None
        return action


class Exec:
    kind = None

    def __init__(self, u, cand):
        self.u = u
        self.key = cand.key
        self.target = cand.target
        self.ended = None
        self.owner = Owner(u.sv.world, u.sv.actions, u.sv.clock)

    def rebind(self):
        sv = self.u.sv
        self.owner.world, self.owner.actions = sv.world, sv.actions

    def observe(self, sit):
        """Its actions' ends (sets `ended`)."""

    def step(self, sit, cand):
        raise NotImplementedError

    def retire(self):
        """It is replaced: what must still be read (a maneuver's late kill) is handed to the Utility."""


class FightExec(Exec):
    kind = "fight"

    def __init__(self, u, cand):
        super().__init__(u, cand)
        self.m = None
        self.end = None           # the last maneuver's end
        self.melee_off = None
        self.walk_wall = None

    def observe(self, sit):
        m = self.m
        if m is not None:
            m.observe()
            for zid in m.take_kills():
                self.u.killed(zid)
            m.take_span()
            end = m.over()
            if end is not None:
                why = getattr(m, "end_why", None)
                self.end = dict(m.log(), end=end, **({"why": why} if why is not None else {}))
                self.m = self.owner.m = None
                if end in KILL_ENDS:
                    self.ended = "dead"
                elif end == "out of reach" or (end == "lost" and why == "out of reach"):
                    self.u.mark_unreachable(self.target, SEEK_SKIP_S)
                    self.ended = "out of reach"
                elif end == "lost" and why == "no progress":
                    self.u.mark_unreachable(self.target, UNREACHABLE_S)
                    self.ended = "no progress"
                elif end in HANDBACK_ENDS:
                    self.ended = "crowd"
                elif end in OFF_ENDS:
                    self.melee_off = end
        if self.ended is None:
            z = sit.zed(self.target)
            if self.target in self.u.dead_now:
                self.ended = "dead"
            elif z is None:
                self.ended = "gone"
            elif z.d > DISENGAGE_R:
                self.ended = "far"

    def retire(self):
        if self.m is not None:
            self.u.retired.append(self.m)
            self.m = self.owner.m = None

    def step(self, sit, cand):
        z = cand.zed
        why = {"target": z.id, "dist": z.d, "fallen": z.fallen}
        if self.end is not None:
            why["melee_end"], self.end = self.end, None
        if cand.door and self.u.sv.door_open is not None:
            h = FightDoorHeld()
            h.world, h.why, h.door_open = self.u.sv.world, {}, self.u.sv.door_open
            cmd = h._door_open_cmd((z.id, self.u.sv.world.zombies.get(z.id) or {}, z.d))
            if cmd is not None:
                if self.owner.busy() and cmd.TYPE == self.owner.last.type:   # its leg or its open still runs
                    return Step("threat", self.owner, None, dict(why, **h.why, holding=self.owner.last.aid))
                return Step("threat", self.owner, cmd, dict(why, **h.why))
        world = self.u.sv.world
        near = z.d <= (MELEE_START_R if z.standing else MELEE_RELEASE_R)
        if near and world.can("melee") and self.melee_off is None:
            return self.melee_step(sit, z, why)
        if near:
            if self.owner.busy():
                return Step("threat", self.owner, None, dict(why, holding=self.owner.last.aid))
            return Step("threat", self.owner, Stomp(z.id) if z.fallen else Attack(z.id), why)
        return self.approach(sit, z, why)

    def melee_step(self, sit, z, why):
        """THE CALL SITE of the melee maneuver (Task 2 switches `Melee`'s arguments here, one edit): a new `Melee` at
        the target where none runs, its inputs read afresh, its next command or None while it runs."""
        world, sv = self.u.sv.world, self.u.sv
        mode = "finish" if z.fallen else ("shove" if S.spent(sit) else "strike")
        reach = (world.weapon or {}).get("reach") if isinstance(world.weapon, dict) else None
        inputs = melee_inputs(mode, reach + ATTACK_MARGIN if isinstance(reach, (int, float)) else 0.0,
                              not S.spent(sit))
        for _ in range(2):
            m = self.m
            if m is None or m.over() is not None:
                self.retire()
                self.m = self.owner.m = m = MANEUVERS["melee"](world, sv.actions, sv.clock, z.id)
            m.inputs = inputs
            out = m.step()
            if out is not None or m.over() is None:
                break
        self.owner._from_m = out
        why = dict(why, maneuver=m.log(), melee={"mode": mode, "pain": sit.arm_pain})
        return Step("threat", self.owner, out, why)

    def approach(self, sit, z, why):
        sv = self.u.sv
        world, now = sv.world, sv.clock()
        last = self.owner.last
        if self.owner.busy() and last is not None and (
                last.type != "walkTo" or now - (self.walk_wall or now) < WALK_RESEND_S):
            return Step("threat", self.owner, None, dict(why, holding=last.aid, leg=last.type))
        me = (sit.x, sit.y)
        read = edge_read(world, me, (z.x, z.y), DISENGAGE_R, marked=world.marked_doors())
        if read is not None and read["via"] is not None:
            route = route_record(world, read, me)
            self.walk_wall = now
            return Step("threat", self.owner, WalkTo(route["target"][0], route["target"][1], "walk"),
                        dict(why, leg="route", door=[read["door"][0], read["door"][1]]))
        if z.d > STANCE_R or not world.can("aim"):
            self.walk_wall = now
            return Step("threat", self.owner, WalkTo(z.x, z.y, "walk"), dict(why, leg="walk"))
        if z.standing and z.aware:
            return Step("threat", self.owner, Aim(0.0, 0.0, AIM_LEG_S, targetId=z.id), dict(why, leg="stand"))
        vx, vy = (z.x - sit.x) / z.d, (z.y - sit.y) / z.d
        return Step("threat", self.owner, Aim(vx, vy, AIM_LEG_S, targetId=z.id), dict(why, leg="toward"))


class DressExec(Exec):
    kind = "dress"

    def __init__(self, u, cand):
        super().__init__(u, cand)
        sv = u.sv
        self.m = self.owner.m = MANEUVERS["dress"](sv.world, sv.actions, sv.clock, cand.target, cand.ride)

    def observe(self, sit):
        self.m.observe()
        end = self.m.over()
        if end is not None:
            self.ended = end
            if end == "failed":
                self.u.dress_failed()

    def step(self, sit, cand):
        cmd = self.m.step()
        self.owner._from_m = cmd
        end = self.m.over()
        if cmd is None and end is not None:
            self.ended = end
            if end == "failed":
                self.u.dress_failed()
            return None
        return Step("care", self.owner, cmd, {"maneuver": self.m.log()})


class RetreatExec(Exec):
    kind = "retreat"

    def __init__(self, u, cand):
        super().__init__(u, cand)
        self.filter = cand.filter

    def observe(self, sit):
        a = self.owner.last
        if A.filter_at(None, sit, self.filter):
            self.ended = "arrived"
        elif a is not None and self.u.sv.actions.done(a):
            if a.state == "done":
                self.ended = "arrived"
            elif not (a.state == "failed" and a.reason == PREEMPTED):
                self.ended = "failed"
        if self.ended == "arrived":
            self.u.at_filter = self.filter

    def step(self, sit, cand):
        f = self.filter
        why = {"flee": "retreat:%s" % f.kind, "filter": [f.target[0], f.target[1]],
               "door": [f.square[0], f.square[1]], "dist": math.hypot(f.target[0] - sit.x, f.target[1] - sit.y)}
        if self.owner.busy():
            return Step("threat", self.owner, None, dict(why, holding=self.owner.last.aid))
        return Step("threat", self.owner, WalkTo(f.target[0], f.target[1], "run"), why)


class GoalExec(Exec):
    kind = "travel"

    def step(self, sit, cand):
        sv = self.u.sv
        sv.why = {}
        ans = sv._goal()
        why = dict(sv.why)
        if ans is None:
            self.ended = "idle"
            return None
        return Step("goal", ans[0], ans[1], why)


class NeedsExec(Exec):
    kind = "needs"

    def step(self, sit, cand):
        ans = self.u.needs_answer
        if ans is None:
            self.ended = "none"
            return None
        branch, owner, cmd, why = ans
        return Step(branch, owner, cmd, why)


class RestExec(Exec):
    kind = "rest"

    def step(self, sit, cand):
        return Step(None, None, None, {"rest": True})


EXECUTORS = {"fight": FightExec, "dress": DressExec, "retreat": RetreatExec, "travel": GoalExec, "loot": GoalExec,
             "sneak": GoalExec, "needs": NeedsExec, "rest": RestExec}
