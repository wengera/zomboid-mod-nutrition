"""The melee maneuver (Plan 28 Task 7b, survival iteration 22; the architecture review `arch-review-cerebellum.md`
§ 3.5, cut 1 of the maneuver layer): `Melee`, the planner's face of Task 7a's reflex skill `melee` (PZA/1.8,
`PZAgent_StanceMelee.lua`), which owns one zombie from the combat stance to the kill at the client's tick rate (the
hit-reaction hold, the strike's end read, the floor swing or the stomp at a fallen target, the knock wait, the shove,
the swing a tick after its face, the back leg after a miss, the close, the stand). The Fight (`fight.Fight.m`) starts
one where its ladder would send an in-reach command at its pin and sets its `inputs` before each `step`.

- `step()`: `pza1.Melee` at `target` from `inputs` (`MeleeInputs`: the Fight's mode, reach, `back` heading and
  floor swing, read afresh at each send) and the policies table (`keepR` KEEP_R, `shoveR` SHOVE_R, `releaseR`
  MELEE_RELEASE_R, `seconds` MELEE_S); None while the running melee is not yet due its re-send. The re-send
  (`resend`): "early" once MELEE_S - MELEE_RESEND_MARGIN_S have passed since the running melee's accept (its
  `acked_wall`, else its `sent_wall`), so the Lua supersedes a melee of the same target and keeps the stance (Task
  7a's report, item 10: a `done` releases it), but never while the last progress line's step is a strike's
  (STRIKE_STEPS: fix 1, review-t7c M1, a re-send would supersede the swing or shove in flight and lose its end), going
  on the first tick after it; "time" after a `done time` (the stance taken again).
- The ends (`ended`): a `done` whose result reads `kill` true names its target in the kills its owner takes
  (`take_kills`), whichever of its sends it was (an early re-send's predecessor too); the current send's `done`
  ends the maneuver `dead` when its `end` reads dead, else (`time`, or a replay's result-less done) it goes on, its
  span (`take_span`: the strikes, the swings, floor swings and stomps, and whether the target's health fell from
  `hp0` to `hp1`, None when either is unreadable) read by the owner's no-progress streak; any other end of the current
  send ends it with its reason (`out of range`, `crowd` with its result kept in `crowd`, `stood`, `out of reach`,
  `superseded`, `not loaded`, `interrupted`, a rejection's `too far`, `no target`, `no weapon`), or its state
  (`timeout`).
- The walk to a fallen target (fix 1, review-t7b m1): the Lua's `stomp_walk` fails `out of reach` after
  K.STOMP_APPROACH_MS, but its `seconds` end it first and every send restarts that walk's clock, so the maneuver keeps
  its own: from the first progress line reading `stomp_walk` (`_walk_since`, reset by any other step), a `done` whose
  last step is still the walk once MELEE_WALK_S have passed ends the maneuver `out of reach`, as the Lua would.
- `why` (logged by the Fight as `maneuver`): target, mode, sends, and the last progress line's step and distance,
  with its counts once one carries them.
"""
import dataclasses
import time

from agent.base import pza1
from agent.base.planner.maneuvers.base import Maneuver
from agent.base.planner.policies import (KEEP_R, MELEE_RELEASE_R, MELEE_RESEND_MARGIN_S, MELEE_S, MELEE_WALK_S,
                                         SHOVE_R)

STRIKE_KEYS = ("swings", "floors", "stomps")   # a span's strikes the no-progress streak counts: the ladder's attack
                                               # (the swing and the floor swing) and its stomp (`Fight.observe`)
COUNT_KEYS = ("swings", "shoves", "stomps", "floors", "knockdowns", "hits")   # the progress line's counts, logged
STRIKE_STEPS = ("face", "swing", "shove", "stomp", "floor")   # the Lua's strike steps (PZAgent_StanceMelee.lua's
                                                              # header: each from its face to its result), in which no
                                                              # early re-send goes (fix 1, review-t7c M1)


@dataclasses.dataclass(frozen=True)
class MeleeInputs:
    """What the Fight reads for one send (`fight.Fight._melee_inputs`)."""
    mode: str           # strike, shove or finish
    reach: float        # the swing's distance at a standing target, 0 for the Lua's own (`K.reachOf`)
    back: tuple         # the back leg's world heading (vx, vy); (0, 0) stands
    floor_swing: bool   # the weapon's floor swing at a fallen target allowed


def _number(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


class Melee(Maneuver):
    """The melee maneuver (the module docstring)."""

    name = "melee"

    def __init__(self, world, actions, clock=time.time, target=None):
        super().__init__(world, actions, clock)
        self.target = target    # the zombie id every send goes at
        self.inputs = None      # MeleeInputs, set by the owner before each `step`
        self.mode = None        # the mode of the last send
        self.resend = None      # the last step's re-send: "early", "time", or None for the first send
        self.crowd = None       # the `crowd` end's result {id, d}
        self.d = None           # the last progress line's distance to the target
        self._progress = {}     # the last progress line's result
        self._kills = []        # the target ids a `done` {kill} read, not yet taken
        self._span = None       # the current send's `done` span, not yet taken
        self._walk_since = None   # the wall of the first progress line of the running walk to a fallen target

    def resend_due(self):
        """The running melee has run MELEE_S - MELEE_RESEND_MARGIN_S since its accept (else its send), and its last
        progress line's step is no strike's (STRIKE_STEPS: the strike's end is read first)."""
        a = self.action
        if a is None or not self.running() or self._progress.get("step") in STRIKE_STEPS:
            return False
        t0 = a.acked_wall if a.acked_wall is not None else a.sent_wall
        return self.clock() - t0 >= MELEE_S - MELEE_RESEND_MARGIN_S

    def step(self):
        """The next `pza1.Melee` (the module docstring), else None."""
        if self._end is not None or self.inputs is None:
            return None
        live = self.running()
        if self.action is not None and not live and not self.actions.done(self.action):
            self._end = "superseded"   # another sender's action is current (`observe` not yet called this tick)
            return None
        if live and not self.resend_due():
            return None
        self.resend = None if self.action is None else ("early" if live else "time")
        i = self.inputs
        self.mode = i.mode
        cmd = pza1.Melee(targetId=self.target, mode=i.mode, reach=float(i.reach), keepR=KEEP_R, shoveR=SHOVE_R,
                         releaseR=MELEE_RELEASE_R, backVx=float(i.back[0]), backVy=float(i.back[1]),
                         seconds=MELEE_S, floorSwing=bool(i.floor_swing))
        self._log(sends=self.n + 1)
        return cmd

    def sent(self, cmd, action):
        super().sent(cmd, action)
        self._log()

    def ended(self, a, current):
        res = a.result if isinstance(a.result, dict) else {}
        if a.state == "done" and res.get("kill") is True:
            self._kills.append(a.args.get("targetId"))
        if not current:
            return
        if a.state == "done":
            strikes = sum(res.get(k) for k in STRIKE_KEYS if _number(res.get(k)))
            hp0, hp1 = res.get("hp0"), res.get("hp1")
            self._span = (strikes, hp1 < hp0 if _number(hp0) and _number(hp1) else None)
            if res.get("end") == "dead":
                self._end = "dead"
            elif (self._progress.get("step") == "stomp_walk" and self._walk_since is not None
                  and self.clock() - self._walk_since >= MELEE_WALK_S):
                self._end = "out of reach"   # fix 1, m1: the Lua's own bound, summed across the sends
            return
        if a.reason == "crowd":
            self.crowd = res
        self._end = a.reason or a.state

    def progressed(self, line):
        res = line.get("result")
        if isinstance(res, dict):
            self._progress = res
            self.d = res.get("d")
            if res.get("step") != "stomp_walk":
                self._walk_since = None
            elif self._walk_since is None:
                self._walk_since = self.clock()
            self._log()

    def take_kills(self):
        """The target ids read killed since the last take."""
        out, self._kills = self._kills, []
        return out

    def take_span(self):
        """(strikes, health fell or None) of the current send's last `done`, once; else None."""
        out, self._span = self._span, None
        return out

    def _log(self, sends=None):
        self.why = {"target": self.target, "mode": self.mode, "sends": self.n if sends is None else sends,
                    "step": self._progress.get("step"), "d": self.d}
        self.why.update({k: self._progress[k] for k in COUNT_KEYS if k in self._progress})
