"""The sneak gait (ruling P30-D, `SNEAK`, survival iteration 24; Plan 30 Task 3, the spec
`2026-11-05-plan-30-the-intent-design.md` § 1 reading 4 and § 2 item 3): the mixin `SneakGait` that `survive.Survive`
derives from, its state Survive's own (`_init_sneak`), read at the tick's send (`Survive._apply`).

PZA/1.9's `sneak {on}` writes the player's stored sneak flag once (`setSneaking`, #4654: nothing clears it on an
attack, a shove, a run, an aim or a hit), and under it the Lua's `walk` plays the crouched sneak walk and `run` the
sneak run (#4656); at Sneak 0 or 1 sneaking spots worse than upright beyond about 4.5 tiles and about 2.6 times better
inside it, and footsteps carry 4 tiles against 7 (#4657, #4661). The rule:

- The want (`_sneak_want`), read only with the switch on and a build announcing `sneak` (`World.can`): upright (False)
  while any zombie within SNEAK_R chases (`hasTarget`, the stance then), while a flee runs or its command is the
  tick's, and when the tick's command is a press at a zombie (a melee, an attack, a shove, a stomp: the fight runs
  upright); else sneaking (True) while a zombie is listed within SNEAK_R, upright with none. Else None: nothing is sent
  and nothing logged (a build without `sneak` sends nothing).
- The send (`_sneak_posture`): the frame's `me.sneaking` (observed, never the planner's own last send) against the
  want. Agreeing, nothing; a sneaking walk the tick sends at a run that is no flee's goes at a walk (the sneak gait is
  the Lua's `walk` under the flag; the flee keeps its run). Disagreeing: one `Sneak(want)`, the tick's one command
  (cmd.txt carries one command a write, so a posture beside another command would be lost): `Sneak(True)` only on a
  tick that sends nothing else (a goal's or a fight's walk already running goes on crouched), `Sneak(False)` in place
  of the tick's command (deferred: the branch answers it again on the next tick, upright), and a posture of the same
  value already sent is never sent again until the frame reads it, its act line fails, or SNEAK_CONFIRM_S have passed
  since its `done` with the frame still reading the other value (`_sneak_a`, one-shot; fix 1, review-t3 m9: a done
  posture the frame never confirms, a player packet clearing the flag, never blocks that value for the session: the
  frame's value rules and the posture goes once more).
- Logged `sneak` {on: the want, near: the zombies within SNEAK_R}, with `sent` true and `deferred` (the tick's own
  command type, or None) on the tick the posture goes, on the decision line's inputs.

Cost if wrong: a slower walk where no zombie would have noticed; a command a tick late when the character stands up.
"""
from agent.base.planner.policies import SNEAK_R, chasing
from agent.base.pza1 import Sneak, WalkTo

PRESSES = ("melee", "attack", "shove", "stomp")   # a tick's command that strikes at a zombie: the fight runs upright
POSTURE_FAILS = ("failed", "rejected", "timeout")   # a posture's ends after which its value may be sent again
SNEAK_CONFIRM_S = 2.0   # wall seconds after a posture's `done` the frame may take to read its value before the value
                        # may be sent again (fix 1, review-t3 m9): four planner ticks at PLANNER_HZ 2, twenty frames at
                        # the Lua's 10 Hz, past any frame lag; a judgment


class SneakGait:
    """The sneak gait (the module docstring): `Survive`'s mixin."""

    SNEAK = True   # ruling P30-D (Plan 30 Task 3): the module docstring; off, upright and no posture sent. In
                   # `survive.T14_SWITCHES`

    def _init_sneak(self):
        self._sneak_a = None     # the last posture Action sent, until the frame reads its value or it fails
        self.sneak_now = None    # this tick's `sneak` why {on, near[, sent, deferred]}, else None

    def _sneak_want(self, d):
        """(want, near): the want (True, False, or None unread) and the zombies within SNEAK_R (the module
        docstring), for the Decision `d`."""
        if not self.SNEAK or not self.world.can("sneak"):
            return None, 0
        near = self._within(SNEAK_R)
        flee = self.mode == "flee" or (self.flee is not None and d.owner is self.flee)
        if flee or any(chasing(z) for z in near) or (d.cmd is not None and d.cmd.TYPE in PRESSES):
            return False, len(near)
        return bool(near), len(near)

    def _sneak_posture(self, d):
        """(the posture to send this tick in place of `d.cmd`, or None; the command to send otherwise, `d.cmd` or its
        walk at the sneak gait). Sets `sneak_now` (the module docstring)."""
        want, near = self._sneak_want(d)
        self.sneak_now = None
        if want is None:
            return None, d.cmd
        self.sneak_now = {"on": want, "near": near}
        on = (self.world.me or {}).get("sneaking") is True
        a = self._sneak_a
        if a is not None and (a.args.get("on", False) == on or (
                a.state == "done" and a.ended_wall is not None and self.clock() - a.ended_wall >= SNEAK_CONFIRM_S)):
            self._sneak_a = a = None   # the frame reads what it set, or never did within SNEAK_CONFIRM_S (m9)
        if want == on:
            cmd = d.cmd
            if on and cmd is not None and cmd.TYPE == "walkTo" and cmd.gait == "run":
                cmd = WalkTo(cmd.x, cmd.y, "walk")   # the sneak gait: the Lua's walk under the flag
            return None, cmd
        if a is not None and a.args.get("on", False) == want and a.state not in POSTURE_FAILS:
            return None, d.cmd   # one-shot: the same posture already sent, its frame not yet read
        if want and d.cmd is not None:
            return None, d.cmd   # Sneak(True) waits for a tick that sends nothing else
        self.sneak_now.update(sent=True, deferred=None if d.cmd is None else d.cmd.TYPE)
        return Sneak(want), None
