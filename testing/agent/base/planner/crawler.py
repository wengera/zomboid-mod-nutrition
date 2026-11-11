"""The crawler first (Plan 33 Task 2; the spec `docs/superpowers/specs/2026-11-09-plan-33-the-group-design.md` § 3.2):
the mixin `FightCrawler` (`fight.Fight`'s), the Fight's `crawler_first` rule, Survive's CRAWLER_FIRST
(`survive.T17_SWITCHES`). Its state is the Fight's own (`_init_crawler`), and `fight.py`'s module docstring is the
record.

F18 (`f_goals_18-20261108-235005`, its GUIDE § 3): the crawler 13649 (`crawler` true, `onFloor` true) lay within 0.4
tiles of the character from game minute 608 to the death at 617 and was the target of no decision line after 356; the
pair rule (`pair_nearest`) pinned the nearest standing zombie, the finish (`finish_rule`) is silent with one standing
within KEEP_R and the Fight's target choice takes a standing one, so the character stood over the crawler, pressed
nothing at it, and its bites (`CrawlerBiteLEFT` 2, `CrawlerBiteRIGHT` 1 of the four reaction runs) came from under its
feet.

- The read (`_crawler_read`, no side effects; `busy` reads it): with the rule on, neither a door fight (`only`) nor a
  doorway stand, the build announcing `stomp`: the zombie reading `crawler` true or `onFloor` true (a crawler, or one
  knocked down) within CRAWLER_R on a line not read blocked, the Fight may target it (its skips, `target_id_ok`), its
  stomp not refused (`_swing_ok`) and fewer than CRAWLER_TRIES finishes at it ended without a kill, the pin kept first
  while it reads so, else the nearest; while the nearest standing zombie (`_standing`: not on the floor, not read dead,
  not in a shove's knock window; a `crawler` never standing) stands within DANGER_R and beyond STAND_MIN_R (within it
  the engine's call takes that one, #4372: the meet and the shove rule stand). Else None.
- The send (`_crawler_first`, in `_ladder` after the pin's rules, ahead of the finish and every send at the standing
  one): the crawler pinned and a `Stomp` at it (the melee in mode `finish` where the build announces `melee`:
  `dispatch.FightDispatch._melee_mode`), logged `crawler_first` {target, dist, standing, standing_dist, tries}; the
  pair rule's read cleared for that choose. A riding bandage's wait (P25-D) goes first.
- The return (`_crawler_return`): the pinned crawler no longer read (dead, `dead`; gone; beyond CRAWLER_R, `beyond`;
  CRAWLER_TRIES finishes ended without a kill, `tries`; no standing zombie within DANGER_R or one within STAND_MIN_R,
  `standing`): the pin goes to the nearest standing zombie within DANGER_R, logged `crawler_first` {returned, crawler,
  why} by the choose; with no standing zombie the Fight's own target rules (the finish of a crawler alone in reach
  stands as P24-AL has it).
- The tries (`_observe_crawler`, every observe after the kill reads): each finish sent under the rule (a ladder stomp's
  action, or the melee maneuver carrying it) that ends with its crawler not read dead counts one at that id
  (`crawler_tries`, which Survive shares across its Fights, as it shares `dead`); an end `superseded` (a newer send
  replaced it: the Fight's own re-pin, a flee's hand-over) or rejected `busy` is no try (`UNTRIED_ENDS`).
- `busy` (`_crawler_busy`): while the read names a zombie, a running send at another gives way at once; a running send
  at it holds (a melee until its inputs change, `Melee.resend_due`), the hold logged `crawler_first`.

Cost if wrong: a stomp's seconds over a crawler while a standing zombie closes from beyond STAND_MIN_R (the melee's
own handback within HANDBACK_R stands), bounded by CRAWLER_TRIES. Plan 34's crawler clear (the backpedal from a
field of crawlers, CRAWLER_CLEAR) went at Plan 35 Task 8: the reflex's footwork steps off the crawlers (`work`'s
`crawlerR`).
"""
from agent.base.planner.policies import (CRAWLER_R, DANGER_R, PREEMPTED, STAND_MIN_R, blocked, line_to, on_floor,
                                         target_id_ok, zdist)
from agent.base.pza1 import Stomp

CRAWLER_TRIES = 2   # finishes at one crawler ended without a kill after which it is left for the standing fight
NOT_TRIED = ("failed", "rejected")    # an action state whose reason names its end (`_observe_crawler`)
UNTRIED_ENDS = (PREEMPTED, "busy")    # ends that are no try: superseded by a newer send (the Fight's own re-pin, a
                                      # flee's hand-over), or rejected `busy` (P28-D: mid-swing, nothing tried)


def is_crawler(z):
    """Zombie record `z` reads `crawler` true (the frame's; it is never the standing one, whatever `onFloor` reads)."""
    return z.get("crawler") is True


class FightCrawler:
    """The crawler first (the module docstring): `Fight`'s mixin."""

    def _init_crawler(self):
        self.crawler_tries = {}      # zombie id -> finishes at it ended without a kill (Survive shares its own)
        self._crawler_pin = None     # the crawler the rule pinned, until the pin returns
        self._crawler_runs = []      # (the finish's maneuver or action, crawler id), until its end is read
        self._crawler_note = None    # the return's why, logged by the next choose

    def _crawler_standing(self):
        """(id, zombie, dist) of the nearest standing zombie within DANGER_R, crawlers left out, else None."""
        return next((s for s in self._standing(DANGER_R) if not is_crawler(s[1])), None)

    def _crawler_read(self):
        """(id, zombie, dist, (standing id, zombie, dist)) of the crawler the rule takes, else None (the module
        docstring); no side effects."""
        if ("crawler_first" not in self.rules or self.only is not None or self.doorway is not None
                or not self.world.can("stomp")):
            return None
        stand = self._crawler_standing()
        if stand is None or stand[2] <= STAND_MIN_R:
            return None
        skip = self.blocked()
        best = None
        for zid, z in self.world.zombies.items():
            if (not target_id_ok(zid) or zid in skip or z.get("x") is None or z.get("y") is None
                    or not (is_crawler(z) or on_floor(z)) or self.crawler_tries.get(zid, 0) >= CRAWLER_TRIES
                    or not self._swing_ok("stomp", zid)):
                continue
            d = zdist(self.world, z)
            if d > CRAWLER_R or line_to(self.world, z) is False:
                continue
            key = (zid != self._crawler_pin, d, repr(zid))   # the rule's pin kept first while it reads so
            if best is None or key < best[0]:
                best = (key, zid, z, d)
        return None if best is None else (best[1], best[2], best[3], stand)

    def _crawler_why(self, read):
        zid, _, d, stand = read
        return {"target": zid, "dist": d, "standing": stand[0], "standing_dist": stand[2],
                "tries": self.crawler_tries.get(zid, 0)}

    def _crawler_first(self):
        """The rule's `Stomp` at the crawler (the module docstring), else None (the pin returned where it was the
        rule's)."""
        read = self._crawler_read()
        if read is None:
            self._crawler_return()
            return None
        if self._ride_waits():   # P25-D: the riding bandage lands before a held Fight's next send
            return None
        zid, _, d, _ = read
        if self.target != zid:
            self.target, self.repositioned = zid, False
        self._crawler_pin, self.pair = zid, None
        self.why = {"target": zid, "pinned": True, "dist": d, "crawler_first": self._crawler_why(read)}
        return Stomp(zid)

    def _crawler_return(self):
        """The pin back on the nearest standing zombie within DANGER_R once the crawler the rule pinned is no longer
        read (the module docstring), noted for the choose's log."""
        cid, self._crawler_pin = self._crawler_pin, None
        if cid is None:
            return
        z = self.world.zombies.get(cid)
        if cid in blocked(self.dead, self.clock()):
            why = "dead"
        elif z is None or z.get("x") is None or z.get("y") is None:
            why = "gone"
        elif self.crawler_tries.get(cid, 0) >= CRAWLER_TRIES:
            why = "tries"
        elif zdist(self.world, z) > CRAWLER_R:
            why = "beyond"
        else:
            why = "standing"
        stand = self._crawler_standing()
        if self.target in (cid, None) and stand is not None:   # an earlier rule (the pair's) may have re-pinned it
            self.target, self.repositioned = stand[0], False
        self._crawler_note = {"returned": None if self.target == cid else self.target, "crawler": cid, "why": why}

    def _observe_crawler(self):
        """The tries (the module docstring): every finish sent under the rule whose end is read counts one at its
        crawler unless the crawler reads dead."""
        dead, keep = blocked(self.dead, self.clock()), []
        for run, zid in self._crawler_runs:
            if hasattr(run, "over"):   # the melee maneuver: its end, `superseded` or a failed action's reason
                end = run.over()
            else:                      # a ladder stomp: its state, or a failed or rejected one's reason
                end = None if not self.actions.done(run) else (run.reason if run.state in NOT_TRIED else run.state)
            if end is None:
                keep.append((run, zid))
            elif end not in UNTRIED_ENDS and zid not in dead:
                self.crawler_tries[zid] = self.crawler_tries.get(zid, 0) + 1
        self._crawler_runs = keep

    def _crawler_sent(self, cmd, action):
        """A send under the rule (its why `crawler_first`): its finish (the melee maneuver, else the action) kept until
        its end is read."""
        if "crawler_first" not in self.why or "returned" in self.why["crawler_first"]:
            return
        run = self.m if cmd.TYPE == "melee" else action
        if run is not None and not any(r is run for r, _ in self._crawler_runs):
            self._crawler_runs.append((run, cmd.targetId))

    def _crawler_busy(self):
        """`busy`'s give-way (the module docstring): None when the rule reads no crawler, else whether the running
        send holds."""
        read = self._crawler_read()
        if read is None:
            return None
        if self.last.args.get("targetId") != read[0]:
            return False
        if self.last.type == "melee":
            m = self.m
            if m is None or m.action is not self.last:
                return False
            z = self.world.zombies.get(m.target)
            if z is not None:
                m.inputs = self._melee_inputs(self._melee_mode_at(z), z)
            if m.resend_due():
                return False
        self.why = dict(self.why, crawler_first=self._crawler_why(read))
        return True
