"""The melee maneuver (Plan 28 Task 7b, survival iteration 22, cut 1 of the maneuver layer; the meet of PZA/1.10, Plan 31
Task 2): `Melee`, the planner's face of the reflex skill `melee` (`PZAgent_StanceMelee.lua`), which owns one zombie to
the kill at the client's tick rate: the stance beyond FACE_R, the facing every tick inside it, the press when the look is
on the target and its distance at the swing's collision is predicted inside the reach, the press again at once after a
swing that left it standing (no back step, no pause), the knock wait, the finish at a fallen target's head, the spent
meet's shove and stomp, the press leaf on each result. It ends on the kill, a hand-back or a lost target, never on time.
The Fight (`fight.Fight.m`) starts one where its ladder would send an in-reach command at its pin and sets its `inputs`
before each `step`; a decider variant may start one wherever it fights.

- `step()`: `pza1.Melee` at `target` from `inputs` (`MeleeInputs`: the mode, the reach and the floor swing, read afresh
  at each step) and the policies table (`shoveR` SHOVE_SEND_R, `releaseR` MELEE_RELEASE_R, `faceR` FACE_R,
  `pressAngle` PRESS_ANGLE, `pressLo` PRESS_LO, `floorR` FLOOR_R, `handbackR` HANDBACK_R, `stall` STALL_SWINGS,
  `headAim` HEAD_AIM, off until calibrated: fix 1, review-t2 F4); None
  while the running melee runs on inputs that are still its own. One send a target: the melee has no time end, so the
  only re-send (`resend` "inputs") is for inputs that changed the reflex's behaviour (`resend_due`: the spent mode
  shove against the meet's strike or finish, which the Lua runs alike by the target's posture, the floor swing, the
  reach), never while the last progress line's step is a press in flight (STRIKE_STEPS: its result is read first).
- The ends (`ended`): a `done` whose result reads `kill` true names its target in the kills its owner takes
  (`take_kills`), whichever of its sends it was (a re-send's predecessor too); the current send's `done` ends the
  maneuver with its `end` (`kill`; `handback`, its other zombie {id, d} kept in `handback`, with a crowd's count `n`
  and distances `ds`, Plan 31 Task 15a: three standing within 0.6 tiles, two pressed; `lost`), its `why` in
  `end_why` (out of range, out of reach, no progress; crowd, standing) and its span (`take_span`: the strikes, the
  swings, floor swings and stomps, and whether the target's health fell from `hp0` to `hp1`, None when either is
  unreadable) read by the owner's no-progress streak, `span_id` the zombie it read; a reflex that re-pinned to the
  nearer of two standing (Task 15a, the line's `target`) names that one in the kill and in `span_id`; any other end
  of the current send ends it with its reason
  (`superseded`, `not loaded`, `no weapon`, `interrupted`, `dead`, a rejection's `too far`, `no target`, `bad args`),
  or its state (`timeout`).
- `press`: the last press leaf a line carried (`{d_press, d_collide_pred, d_min, look_off, hp0, hp1, knock, cut_by,
  knock_p}`, a shove's knock_p its knock-down chance, Task 15a), kept
  for its owner's log.
- `why` (logged by the Fight as `maneuver`): target, mode, sends, and the last progress line's step and distance, with
  its counts and `spent` once one carries them, and the last press leaf.
"""
import dataclasses
import time

from agent.base import pza1
from agent.base.planner.maneuvers.base import Maneuver
from agent.base.planner.policies import (FACE_R, FLOOR_R, HANDBACK_R, HEAD_AIM, MELEE_RELEASE_R, PRESS_ANGLE,
                                         PRESS_LO, SHOVE_SEND_R, STALL_SWINGS)

STRIKE_KEYS = ("swings", "floors", "stomps")   # a span's strikes the no-progress streak counts: the ladder's attack
                                               # (the swing and the floor swing) and its stomp (`Fight.observe`)
COUNT_KEYS = ("swings", "shoves", "stomps", "floors", "knockdowns", "hits", "spent", "target", "repins")   # the
                                       # progress line's, logged (Task 15a: a re-pin's target and repins)
STRIKE_STEPS = ("swing", "shove", "stomp", "floor")   # the Lua's presses in flight (PZAgent_StanceMelee.lua's header:
                                                      # each from its press to its result), in which no re-send goes
PRESS_KEYS = ("d_press", "d_collide_pred", "d_min", "look_off", "hp0", "hp1", "knock", "cut_by", "knock_p")   # the
                                       # leaf's keys (Task 15a: a shove's knock_p)
PRESS_OPTIONAL = ("knock_p",)   # ... kept only where the leaf carries it (a shove's)


@dataclasses.dataclass(frozen=True)
class MeleeInputs:
    """What the owner reads for one send (`fight.Fight._melee_inputs`)."""
    mode: str           # strike, shove (the spent meet) or finish (sent at a fallen target)
    reach: float        # the swing's distance at the collision, 0 for the Lua's own (`K.reachOf`)
    floor_swing: bool   # the weapon's floor swing at a fallen target allowed

    def behaviour(self):
        """The inputs as the reflex runs them: strike and finish are one meet (the target's posture picks the finish),
        shove the spent meet."""
        return ("shove" if self.mode == "shove" else "meet", float(self.reach), bool(self.floor_swing))


def _number(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _zid(v):
    """An online id as the act lines carry it: an integer, never a bool."""
    return isinstance(v, int) and not isinstance(v, bool)


class Melee(Maneuver):
    """The melee maneuver (the module docstring)."""

    name = "melee"

    def __init__(self, world, actions, clock=time.time, target=None):
        super().__init__(world, actions, clock)
        self.target = target    # the zombie id every send goes at
        self.inputs = None      # MeleeInputs, set by the owner before each `step`
        self.mode = None        # the mode of the last send
        self.resend = None      # the last step's re-send: "inputs", or None for the first send
        self.handback = None    # a `handback` end's other zombie {id, d}
        self.end_why = None     # a `done` end's why (out of range, out of reach, no progress; crowd, standing)
        self.press = None       # the last press leaf a line carried
        self.d = None           # the last progress line's distance to the target
        self._sent = None       # the running send's inputs (`MeleeInputs.behaviour`)
        self._progress = {}     # the last progress line's result
        self._kills = []        # the target ids a `done` {kill} read, not yet taken
        self._span = None       # the current send's `done` span, not yet taken
        self.span_id = None     # the zombie that span read (the target, or a re-pin's `target`: Task 15a)

    def resend_due(self):
        """The running melee runs on inputs the current ones change (`MeleeInputs.behaviour`), and its last progress
        line's step is no press in flight (STRIKE_STEPS: its result is read first)."""
        if self.action is None or not self.running() or self.inputs is None:
            return False
        return self.inputs.behaviour() != self._sent and self._progress.get("step") not in STRIKE_STEPS

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
        if self.action is not None and not live:
            return None   # its end is read by `observe`, which ends the maneuver
        self.resend = None if self.action is None else "inputs"
        i = self.inputs
        self.mode = i.mode
        self._sent = i.behaviour()
        cmd = pza1.Melee(targetId=self.target, mode=i.mode, reach=float(i.reach), shoveR=SHOVE_SEND_R,
                         releaseR=MELEE_RELEASE_R, faceR=FACE_R, pressAngle=PRESS_ANGLE, pressLo=PRESS_LO,
                         floorR=FLOOR_R, handbackR=HANDBACK_R, stall=STALL_SWINGS, floorSwing=bool(i.floor_swing),
                         headAim=HEAD_AIM)
        self._log(sends=self.n + 1)
        return cmd

    def sent(self, cmd, action):
        super().sent(cmd, action)
        self._log()

    def ended(self, a, current):
        res = a.result if isinstance(a.result, dict) else {}
        if a.state == "done" and res.get("kill") is True:   # Task 15a: a re-pinned target's kill names it (`target`)
            self._kills.append(res["target"] if _zid(res.get("target")) else a.args.get("targetId"))
        self._keep_press(res)
        if not current:
            return
        if a.state == "done":
            strikes = sum(res.get(k) for k in STRIKE_KEYS if _number(res.get(k)))
            hp0, hp1 = res.get("hp0"), res.get("hp1")
            self._span = (strikes, hp1 < hp0 if _number(hp0) and _number(hp1) else None)
            self.span_id = res["target"] if _zid(res.get("target")) else self.target   # Task 15a: the re-pinned one
            self.end_why = res.get("why")
            if res.get("end") == "handback":   # Task 15a: a crowd's count and distances beside the nearest other
                self.handback = {"id": res.get("id"), "d": res.get("d")}
                self.handback.update({k: res[k] for k in ("n", "ds") if k in res})
            self._end = res.get("end") or "done"   # a replay's result-less done ends it as done
            return
        self._end = a.reason or a.state

    def progressed(self, line):
        res = line.get("result")
        if isinstance(res, dict):
            self._progress = res
            self.d = res.get("d")
            self._keep_press(res)
            self._log()

    def _keep_press(self, res):
        leaf = res.get("press")
        if isinstance(leaf, dict):
            self.press = {k: leaf.get(k) for k in PRESS_KEYS if k not in PRESS_OPTIONAL or k in leaf}

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
        if self.press is not None:
            self.why["press"] = dict(self.press)
