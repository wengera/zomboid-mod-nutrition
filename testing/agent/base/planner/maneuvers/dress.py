"""The dress maneuver (Plan 31 Task 8; the spec `2026-11-05-plan-31-the-rebuild-design.md` § 4 item 3; Angus's direction
of 2026-11-05, memory `stand-and-fight-dress-first`: the dressing first, even by tearing own clothing): `Dress(part)`,
one commitment from the stop to the dressing of one bleeding part, sent one command at a time under the maneuver
contract (`base.Maneuver`: its owner calls `observe` every tick, asks `step` for the next command, sends it and tells
`sent`; the Dress reads its own actions' ends and never sends itself). Every decider uses it: the variants, and the
ladder's care branch behind Survive's `DRESS_MANEUVER`, on by default since Plan 31 Task 15a
(`care.Care._dress_step`).

The reading behind it (F15, `f_goals_16-20261105-164332`, its `f_grade.txt`: "9 unwears sent, 0 done, rejected
{'moving': 9}"; "bandage sent 3 done 1"): both hands bled undressed from game minute 587 to the death at 702, every
unwear of the only cotton garment refused `moving` (the unwear skill's refusal while the character moves) because each
went out while a flee's steer leg ran, and the bandages were superseded by the flee's re-aims.

The sequence (`phase`, logged):
- `stop`: the pick read first (fix 1, review-t8 M1: with nothing held and nothing to tear the Dress ends `failed`
  "nothing" with no send), then a `stop` (`pza1.Stop`: the running skill and every motor flag cleared), then `still`:
  the wait for a frame
  newer than the stop's end reading `me.moving` false. STILL_FRAMES frames still moving send the stop again; past
  DRESS_MOVED such waits (or `moving` refusals) the Dress ends `failed` "moving".
- `pick` (`care.dress_pick`, the care branch's item choice, with this Dress's own refusal memory): a held clean
  bandage, then a clean rag, then an unwashed (dirty) rag, taken while the part bleeds (the care branch's DIRTY_RAG_MIN
  time rule is not the Dress's); else the rip of a held unworn cotton garment, the one this Dress took off first; else
  the unwear of the worn cotton garment covering the least (never shoes or trousers: `care.UNWEAR_NEVER`). Each
  command's end is read before the next is sent.
- After an `unwear` done, `unworn`: the wait for the garment's record to read unworn (the Lua's `item_changed`), at
  most SETTLE_FRAMES frames, then `pick` (its rip). After a `rip` done, `rag`: the wait for a dressing to be held (the
  rags' `item_added`), at most SETTLE_FRAMES frames, then `pick` (the bandage); a rip that made no rag picks at once.
  After a `bandage` done, `settle`: the wait for the part's `bleeding` to read false, at most SETTLE_FRAMES frames,
  then `pick` again.
- A refusal or failure: `moving`, `stopped` or `aiming` (the character's motion or stance, never the item's: the
  bandage's ride is refused `aiming` under an aim leg, fix 1, review-t8 m1) goes back to the stop, the
  item kept (a riding bandage the engine stopped drops the ride); `superseded` (another sender's command took the
  slot) resumes at the stop (`lost`); any other holds the item out of this Dress's picks for `care.CARE_RETRY_MIN`
  game minutes, a rip refused `worn`, `not cotton` or `needs tool` marking it `unrippable` in the World and one refused
  `in bag` marking it `in_bag`, as the care branch's observe does.
- The ride (`ride=True`, the caller's ask; ruling P24-U's rule, memory `combat-stance-and-wound-care`): a part above
  the legs (index under `care.LEG_FIRST`) is bandaged with `keepMoving` and no stop, the caller's walk kept (the
  riding bandage runs until its own end, whatever leg the caller sends meanwhile); a leg or foot part never rides; a
  pick that finds no dressing held drops the ride and stops to tear.

- The wound (`wound=True`, Plan 31 Task 15a: the ladder's street defect (b), two scratches undressed from 92.7 to
  16.2 health): a part reading `wound` and not bleeding (a scratch drains its part where a bandage suppresses it,
  #2364) is dressed the same way, a clean dressing first and the tear for one next, an unwashed rag only when there
  is nothing else (#4299: under a dirty dressing the wound's infection odds about double against none, a judgment
  against #2364's drain, which any bandage suppresses: trial 12's undressed scratches took the health from 92.7 to
  16.2), never riding, and done once its record reads `bandaged` true.

The ends (`over`, ENDS): `done` once the frame's record of the part reads `bleeding` false (or the frame's parts list
no longer lists it); `failed` when the pick finds nothing held and nothing to tear (`why.fail` "nothing"), past
DRESS_MOVED still-waits ("moving") or past DRESS_SENDS commands ("sends"); `superseded` only when a standing zombie
(`policies.standing`, not lying on the floor) reads within KEEP_R. Another sender's command taking the slot is no end
(the base's `superseded`): the Dress resumes at the stop on its next step, so the commitment outlives a branch that sent
over it; an owner that gives the dressing up drops the maneuver.

The stop-flee loop (fix 1, review-t8 § 2): a flee leg sent over each of the Dress's commands is a loss, and each loss
resumes at a stop, which the next flee leg supersedes again. What bounds it: within one Dress, DRESS_SENDS commands
(the end failed "sends"); across Dresses, the care branch's no-restart rule (`care.Care._dress_step`: no new Dress
after a failed one until the inventory changes or `care.DRESS_RETRY_S` pass, and a Dress with nothing to dress sends
nothing at all); on the ladder's ride tick no Dress sends anything but a riding bandage (`_dress_step`'s ride rule,
P24-U's "never stops the leg").

`why` (`log()`: `{maneuver "dress", ...}`): part, phase, sends, item (the last command's), kind (the dressing's), ride,
lost, moved, and `fail` once it failed.
"""
import time

from agent.base import pza1
from agent.base.planner import care as C
from agent.base.planner.maneuvers.base import Maneuver
from agent.base.planner.policies import KEEP_R, PREEMPTED, standing

ENDS = ("done", "failed", "superseded")   # the Dress's ends (`over`)
STILL_FRAMES = 10         # frames after a stop's end the Dress waits for `me.moving` false before it stops again (one
                          # second at the Lua's 10 Hz frames, the hello's `rate`)
DRESS_MOVED = 3           # still-waits and motion refusals at most before the Dress ends failed "moving"
DRESS_SENDS = 16          # commands at most before the Dress ends failed "sends": four of each of the stop, the unwear,
                          # the rip and the bandage, a bound on a loop no rule above ends
SETTLE_FRAMES = C.WEAR_SETTLE_MAX   # frames the Dress waits at most for an end's effect to reach the frame or the
                                    # inventory (the garment unworn, the rag held, the part's bleeding cleared): a
                                    # bound borrowed from the worn cadence (the Lua's `me.worn` every S.WORN_EVERY 10
                                    # frames), never a measurement of these three effects' latency
MOVED = ("moving", "stopped", "aiming")   # the refusals the character's motion or stance made (`aiming`: the ride
                                         # under an aim leg, PZAgent_Tend.lua's bandage): back to the stop, the item
                                         # kept
NEXT = {"unwear": "unworn", "rip": "rag", "bandage": "settle"}   # a command's done -> the wait for its effect


class Dress(Maneuver):
    """The dress maneuver (the module docstring)."""

    name = "dress"

    def __init__(self, world, actions, clock=time.time, part=None, ride=False, wound=False):
        super().__init__(world, actions, clock)
        self.part = part        # the body part index this Dress dresses
        self.wound = bool(wound)   # Plan 31 Task 15a: a wound not bleeding (a scratch), dressed until it reads bandaged
        self.ride = (bool(ride) and not self.wound and isinstance(part, int) and not isinstance(part, bool)
                     and part < C.LEG_FIRST)
        self.phase = "pick" if self.ride else "stop"
        self.cmd = None         # the command the last `step` returned (its owner's `sent` routes by it)
        self.item = None        # the item the last command named
        self.kind = None        # the dressing's kind (`care.care_kind`) of the last bandage
        self.garment = None     # the garment this Dress took off, ripped first
        self.held_out = {}      # item id -> world minute: refused under this Dress (`care.dress_pick`'s memory)
        self.unwear_at = {}     # item id -> world minute its unwear ended done (a refused or lost one is tried again)
        self.lost = 0           # times another sender's command took the slot
        self.moved = 0          # still-waits that timed out and motion refusals (DRESS_MOVED)
        self.fail = None        # why it failed: "nothing", "moving" or "sends"
        self._since = 0         # `World.frame_n` when the current wait began
        self._log()

    # -- the contract ---------------------------------------------------------------------------------------------
    def running(self):
        """Its current action runs: a riding bandage until its own end (the caller's legs sent since take the slot),
        else the base's rule."""
        a = self.action
        if a is not None and a.type == "bandage" and a.args.get("keepMoving") is True:
            return not self.actions.done(a)
        return super().running()

    def observe(self):
        """Its current action's end, once; another sender's command current over its running action is a loss (no
        end: resumed at the stop); then the frame's ends (`_check`). Idempotent within a tick."""
        a = self.action
        for b in [b for b in self._open if self.actions.done(b)]:
            self._open.remove(b)
            if b is a:
                self.ended(b, True)
        if self.action is not None and not self.actions.done(self.action) and not self.running():
            self._lose()
        self._check()
        self._log()

    def ended(self, a, current):
        """Action `a`'s end (the module docstring's refusals); an earlier action's late end reads nothing."""
        if not current:
            return
        self._since = self.world.act_n.get(str(a.aid), self.world.frame_n)   # the frames applied before its end line
        if a.state == "failed" and a.reason == PREEMPTED:
            self._lose()   # another sender's command superseded it in the Lua
            return
        if a.type == "stop":
            self.phase = "still"   # a stop's other ends: the skill and the motor flags are cleared
            return
        if a.state == "done":
            self.phase = NEXT.get(a.type, "pick")
            if a.type == "unwear":
                self.garment = a.args.get("itemId")
                self.unwear_at[self.garment] = self.world.world_minutes()   # not again while it reads worn
            if a.type == "rip" and isinstance(a.result, dict) and a.result.get("rags") == 0:
                self.phase = "pick"
            return
        if a.reason in MOVED:
            self.ride = False   # a ride the engine stopped goes on standing
            self._moved()
            return
        iid = a.args.get("itemId")
        self.held_out[iid] = self.world.world_minutes()
        if iid in self.world.inventory:
            if a.type == "rip" and a.reason in C.RIP_REFUSALS:
                self.world.mark(iid, "unrippable")
            elif a.reason == "in bag":
                self.world.mark(iid, "in_bag")
        self.phase = "pick"

    def sent(self, cmd, action):
        super().sent(cmd, action)
        self.phase = "sent"
        self.item = getattr(cmd, "itemId", None)
        self._log()

    def step(self):
        """The next command (the module docstring's sequence), or None while its command runs, while it waits, or once
        it ended."""
        self.observe()
        self.cmd = None
        if self._end is not None or (self.action is not None and self.running()):
            return None
        while self._end is None:
            ph, frames = self.phase, self.world.frame_n - self._since
            if ph == "stop":
                if self._choice() is None:   # fix 1, M1: nothing to dress and nothing to tear sends nothing
                    return self._failed("nothing")
                return self._out(pza1.Stop())
            if ph == "still":
                if frames > 0 and (self.world.me or {}).get("moving") is False:
                    self.phase = "pick"
                elif frames >= STILL_FRAMES:
                    self._moved()
                else:
                    return None
            elif ph == "unworn":
                if (self.world.inventory.get(self.garment) or {}).get("worn") is not True or frames >= SETTLE_FRAMES:
                    self.phase = "pick"
                else:
                    return None
            elif ph == "rag":
                if any(C.held_dressings(self.world, self.held_out).values()) or frames >= SETTLE_FRAMES:
                    self.phase = "pick"
                else:
                    return None
            elif ph == "settle":
                if frames < SETTLE_FRAMES:
                    return None
                self.phase = "pick"   # the bandage on and the part still bleeding: dressed again
            elif ph == "pick":
                return self._pick()
            else:
                return None   # "sent": its command's end not yet read
        return None

    # -- the steps ------------------------------------------------------------------------------------------------
    def _pick(self):
        """The pick's command (`care.dress_pick`), else the end failed "nothing"; a ride that finds no dressing held
        is dropped and the stop goes first."""
        got = self._choice()
        if got is None:
            return self._failed("nothing")
        if got[0] != "bandage" and self.ride:
            self.ride, self.phase = False, "stop"
            return self._out(pza1.Stop())
        if got[0] == "bandage":
            self.kind = got[2]
            return self._out(pza1.Bandage(got[1], part=self.part, keepMoving=self.ride))
        return self._out(pza1.Rip(got[1]) if got[0] == "rip" else pza1.Unwear(got[1]))

    def _choice(self):
        """`care.dress_pick` over this Dress's refusal memory, an unwashed rag taken (`dirty_ok`)."""
        p = self._record() or {}
        got = C.dress_pick(self.world, p.get("bleedingTime") or 0.0, held_out=self.held_out,
                           unwear_at=self.unwear_at, prefer=self.garment, dirty_ok=not self.wound)
        if got is None and self.wound:   # Task 15a: a scratch takes an unwashed rag only with nothing else to dress
            got = C.dress_pick(self.world, 0.0, held_out=self.held_out, unwear_at=self.unwear_at, dirty_ok=True)
        return got

    def _out(self, cmd):
        """`cmd` as the step's command, unless DRESS_SENDS were sent (the end failed "sends")."""
        if self.n >= DRESS_SENDS:
            return self._failed("sends")
        self.cmd = cmd
        self._log()
        return cmd

    def _moved(self):
        """A still-wait timed out or a motion refusal: the stop again, or past DRESS_MOVED the end failed "moving"."""
        self.moved += 1
        if self.moved > DRESS_MOVED:
            self._failed("moving")
        else:
            self.phase = "stop"

    def _lose(self):
        """Another sender's command took the slot: no end; the current action dropped (its late end reads nothing)
        and the Dress resumes at the stop (at the pick while it rides)."""
        self.lost += 1
        self.action = None
        self.phase = "pick" if self.ride else "stop"

    def _failed(self, why):
        self._end, self.fail = "failed", why
        self._log()
        return None

    def _record(self):
        """The frame's record of the part, else None."""
        parts = (self.world.body or {}).get("parts")
        if not isinstance(parts, list):
            return None
        return next((p for p in parts if isinstance(p, dict) and p.get("i") == self.part), None)

    def _check(self):
        """The frame's ends: `done` once the part reads `bleeding` false (a wound Dress: `bandaged` true), or a parts
        list no longer lists it; else `superseded` with a standing zombie within KEEP_R."""
        if self._end is not None:
            return
        parts = (self.world.body or {}).get("parts")
        rec = self._record()
        dressed = rec is not None and (rec.get("bandaged") is True if self.wound else rec.get("bleeding") is False)
        if isinstance(parts, list) and (rec is None or dressed):
            self._end = "done"
        elif standing(self.world, KEEP_R):
            self._end = "superseded"

    def _log(self):
        self.why = {"part": self.part, "phase": self.phase, "sends": self.n, "item": self.item, "kind": self.kind,
                    "ride": self.ride, "lost": self.lost, "moved": self.moved}
        if self.wound:
            self.why["wound"] = True   # Plan 31 Task 15a: a scratch's Dress
        if self.fail is not None:
            self.why["fail"] = self.fail
