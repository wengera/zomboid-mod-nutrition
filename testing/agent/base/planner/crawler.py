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
own handback within HANDBACK_R stands), bounded by CRAWLER_TRIES.

The crawler clear (Plan 34, ruling P34-A fix B; the Fight's `crawler_clear` rule, Survive's CRAWLER_CLEAR in
`survive.T19_SWITCHES`). The smoke trial `x_trial-ladder-20261109-105452` (P31-T, not evidence; its row in
`testing/trials/trials.md`): at game minute 632 the Fight's approach to the standing 9128 (2.43 tiles) stopped the
character at seq 1832 with the crawlers 9174 at 0.85 tiles and 9175 at 1.1; the melee's swing knocked 9128 down at
0.69, and from the first `CrawlerBite` at seq 1868 the character, never moving again, took 13 wounds in 20 s from the
crawlers and from 9173, which walked in and bit from 0.48 tiles; the death at game minute 638 after five kills. One
crawler is stomped (the crawler first above); a field of them is left:

- The read (`_crawler_clear_read`, no side effects; `busy` reads it): with the rule on, neither a door fight (`only`)
  nor a doorway stand, the build announcing `aim`, no stand-off fallback (an aim failed) and no riding bandage (P24-U:
  an aim ends it), a standing zombie (`_crawler_standing`, crawlers left out) within DANGER_R, and among the zombies
  reading `crawler` or `onFloor` true (one read dead left out) those within CRAWLER_AVOID_R (`near`): one other than the
  Fight's finish target (`_clear_finish_target`: the pin where it lies fallen, else, with no standing pin taken by the
  pair's or the retreat's read, the zombie the finish takes), or two or more whatever the target; a lone one the
  crawler first takes (`_crawler_read` names it: within CRAWLER_R, the standing one beyond STAND_MIN_R) is left to its
  stomp. So a lone fallen zombie is finished as before unless two or more standing hold the pin (the smoke trial's
  9128 and 9173 within KEEP_R: the pair's pin, no finish).
  Its heading (`away`) is the unit vector from the centroid of every fallen or crawling zombie within KEEP_R (the
  stance's band: the smoke trial's 9175 lay at 1.29 tiles on frame 1835, beyond CRAWLER_AVOID_R, and the heading away
  from 9174 alone led toward it and toward 9173) to the character.
- The send (`_crawler_clear`, in `_ladder` after the pin's rules, ahead of the crawler first, the finish and every send
  at the standing one): the stance's `back` leg, an `aim` facing the pin where it stands (else the nearest standing
  zombie, pinned), on `away` turned to the first clear heading (`_clear_turn`), standing (0, 0) with none; under the
  retreat (`retreat`) its heading where it lies within 90 degrees of the crawler heading, else the crawler heading.
  Logged `crawler_clear` {fallen: the heading's ids, away: the heading sent, n: the count within CRAWLER_AVOID_R}; the
  melee's dispatch takes no such leg (`dispatch.FightDispatch._melee_mode`).
- `busy` (`_crawler_clear_busy`): while the read holds, the clear leg holds while its heading lies within
  RETREAT_RESEND_DEG of the heading the read sends now; a running melee holds only through a press in flight
  (`Melee.pressing`, STRIKE_STEPS), as a ladder's attack, shove or stomp does (each a press), whatever the later rules
  of `busy` read (the finish's give-way to a fallen one in reach among them: the clear owns the tick); any other
  running send (an aim, a walk) gives way; once the read ends, the clear leg gives way to the ladder.

Cost if wrong: a stand-off at a standing zombie over two crawlers, the kill deferred until the backpedal clears them;
the crawler first's stomp of a lone crawler stands.
"""
import math

from agent.base.planner.policies import (AIM_LEG_S, CRAWLER_AVOID_R, CRAWLER_R, DANGER_R, KEEP_R, PREEMPTED,
                                         RETREAT_RESEND_DEG, STAND_MIN_R, blocked, line_to, on_floor, target_id_ok,
                                         zdist)
from agent.base.pza1 import Aim, Stomp
from agent.base.world import me_xy

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
        self._clear_leg = None       # the last crawler clear leg sent (Plan 34 fix B), held by `busy` while it reads

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

    # ------------------------------------------------------------------ the crawler clear (Plan 34, P34-A fix B)
    def _crawler_clear_read(self):
        """{near, fallen, away, stand} of the crawler clear (the module docstring), else None; no side effects."""
        if ("crawler_clear" not in self.rules or self.only is not None or self.doorway is not None
                or not self.world.can("aim") or self.standoff or self.ride is not None):
            return None
        stand = self._crawler_standing()
        if stand is None:
            return None
        dead = blocked(self.dead, self.clock())
        fallen = []
        for zid, z in self.world.zombies.items():
            if (zid in dead or z.get("x") is None or z.get("y") is None
                    or not (is_crawler(z) or on_floor(z))):
                continue
            d = zdist(self.world, z)
            if d <= KEEP_R:
                fallen.append((d, repr(zid), zid, z))
        fallen.sort(key=lambda e: e[:2])
        near = [e[2] for e in fallen if e[0] <= CRAWLER_AVOID_R]
        if not near:
            return None
        if len(near) == 1:
            if near[0] == self._clear_finish_target():
                return None   # the finish target alone: its finish
            lone = self._crawler_read()
            if lone is not None and lone[0] == near[0]:
                return None   # one crawler is stomped (the crawler first)
        mx, my = me_xy(self.world)
        cx = sum(e[3]["x"] for e in fallen) / len(fallen)
        cy = sum(e[3]["y"] for e in fallen) / len(fallen)
        n = math.hypot(mx - cx, my - cy)
        away = None if n == 0.0 else ((mx - cx) / n, (my - cy) / n)
        return {"near": near, "fallen": [e[2] for e in fallen], "away": away, "stand": stand}

    def _clear_finish_target(self):
        """The Fight's finish target for the crawler clear: its pin where the pin lies fallen, else, with no standing
        pin taken by the pair's or the retreat's read (`_near_read`: those Fights meet the standing one first and finish
        none), the zombie the finish takes (`_finishable`'s nearest); else None. No side effects."""
        pin = self.world.zombies.get(self.target) if self.target is not None else None
        if pin is not None and (on_floor(pin) or is_crawler(pin)):
            return self.target
        if self._near_read() is not None:
            return None
        fin = self._finishable()
        return fin[0][0] if fin else None

    def _crawler_clear_heading(self, read):
        """The clear leg's heading: the read's `away` turned to the first clear heading (`_clear_turn`), else None (the
        leg stands); under the retreat its heading where it lies within 90 degrees of the crawler heading."""
        away = read["away"]
        h = self._clear_turn(away)
        if self.retreat is not None:
            c = h or away
            r = self._retreat_heading()[0]
            if c is None or r[0] * c[0] + r[1] * c[1] > 0.0:
                return r
        return h

    def _crawler_clear(self):
        """The crawler clear's `back` leg (the module docstring), else None."""
        read = self._crawler_clear_read()
        if read is None:
            return None
        pin = self.world.zombies.get(self.target) if self.target is not None else None
        if (pin is not None and pin.get("x") is not None and pin.get("y") is not None and not on_floor(pin)
                and not is_crawler(pin) and zdist(self.world, pin) <= DANGER_R):
            zid, d = self.target, zdist(self.world, pin)
        else:
            zid, _, d = read["stand"]
            self.target, self.repositioned = zid, False
        v = self._crawler_clear_heading(read)
        vx, vy = v if v is not None else (0.0, 0.0)
        self.pair = None
        self.why = {"target": zid, "pinned": True, "dist": d, "stance": True, "leg": "back",
                    "back": [vx, vy] if v is not None else None, "stand_s": self.stand_s(),
                    "crawler_clear": {"fallen": read["fallen"], "away": [vx, vy] if v is not None else None,
                                      "n": len(read["near"])}}
        return Aim(vx, vy, AIM_LEG_S, targetId=zid)

    def _crawler_clear_busy(self):
        """`busy`'s give-way to the crawler clear (the module docstring): None when neither the read nor its running
        leg is at stake (the other rules decide), else whether the running send holds."""
        mine = self._clear_leg is not None and self.last is self._clear_leg
        read = self._crawler_clear_read()
        if read is None:
            return False if mine else None
        if mine:
            v = self._crawler_clear_heading(read)
            vx, vy = self.last.args.get("vx") or 0.0, self.last.args.get("vy") or 0.0
            n = math.hypot(vx, vy)
            if v is None or n == 0.0:
                return v is None and n == 0.0
            return (vx * v[0] + vy * v[1]) / n >= math.cos(math.radians(RETREAT_RESEND_DEG))
        if self.last.type == "melee":
            m = self.m
            return m is not None and m.action is self.last and m.pressing()
        return self.last.type in ("attack", "shove", "stomp")   # a press in flight: its end is read first
