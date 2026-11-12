"""The Fight's dispatch to its maneuver (Plan 28 Task 7b, survival iteration 22; the architecture review
`arch-review-cerebellum.md` § 3.5, cut 1 of the maneuver layer): the mixin `FightDispatch` (`fight.Fight`'s), which
starts or continues the Fight's `Melee` (`maneuvers.melee`, the planner's face of the reflex skill `melee`: PZA/1.8,
Task 7a; the meet of PZA/1.10, Plan 31 Task 2) where the Fight's decision ladder (`Fight._ladder`, every rule before this one) would send an in-reach
command at its pin. Its state is the Fight's own (`_init_dispatch`), and `fight.py`'s module docstring is the record.

- The dispatch point (`_melee_mode`): with the `melee` rule on (Survive's MELEE), the build announcing `melee`
  (`World.can`, so no golden's record, whose hello announces none, moves) and no `melee_off`, a ladder command at the
  pin (its `targetId` the Fight's `target`; a door fight's pin among `only`), the pin listed within MELEE_RELEASE_R:
  an `aim` leg of any kind within KEEP_R at a standing pin (the fence wait's leg excepted), an `attack` (the swing, or
  at a fallen pin the floor swing), a `shove` or a `stomp`; the corner Fight's (`point_blank`), the door fight's
  (`only`) and the doorway stand's (`doorway`) commands included (Plan 35 fixes 5 and 7). Mode `finish` at a fallen
  pin or for a stomp, else `shove` under a hold or in a shove-and-stomp Fight (`_hold_bars`: `spent`, R2;
  `shove_only`, but the low fight's full swing when due), else `strike`; in mode `shove` with a weapon held the reflex
  swings after a shove that knocked nothing down (Plan 31 Task 15a), so the mode bars the ladder's own swing sends
  only (`no_swing`). P28-H 3: the arms' pain alone (`arms_hurt`, which `no_swing` keeps for the ladder) selects no
  `shove`. The approach-and-swing Fight (a non-stance one) is dispatched too. No melee at a target in its backoff
  (below). Everything above the point stays the ladder's (the pin and its re-pins, P27-N's pin-first, the finish's
  choice of a fallen zombie other than the pin, the fence wait, the edge route, the reposition, the seek, the pull,
  the advance's `toward` legs and walks, the approach), and the flee's finish is the threat branch's own. A running
  walk the Fight sent gives way while the pin stands within KEEP_R on a line not read blocked, the melee sent in its
  place, and so does the nothing a hit reaction answers (`_walk_melee`, Plan 35 fix 6), logged `engage_dispatch`
  {from "walk" | "hit_reaction"}; the first send from a corner, a point-blank leg, the door fight or the doorway stand
  is logged {from "corner" | "point_blank_leg" | "door" | "doorway"}.
- The inputs (`_melee_inputs`, read at every send and on every `busy`): `reach` the Fight's `reach_r` (the frame's
  `weapon.reach` plus ATTACK_MARGIN), 0 where it reads none (the Lua's `K.reachOf`); `floorSwing` with the
  `floor_finish` rule on (P27-G, the floor swing ahead of the stomp) and the floor swing not barred
  (`floor_swing_barred`, P28-C). PZA/1.10 (Plan 31 Task 2) dropped the back leg's heading, the time span and P30-A's
  `closeR` (the `swing_close` rule reads nothing since): the Lua's meet presses at the predicted collision and again
  after a swing that did nothing, with no back step and no time end.
- `busy` (`_melee_holds`): a running melee holds until its inputs change its behaviour (`Melee.resend_due`: the spent
  mode, the floor swing, the reach, the work's withdraw sector, read afresh on the tick), whatever the pin, P27-N's
  pin-first and the finish read (the reflex re-pins, presses a marked attacker and finishes; Plan 35 Task 8 deleted
  those give-ways).
- The ends (`_observe_maneuver`, every observe, after the kill read): a kill on any send of the maneuver, or of one
  it retired (`_spent_m`), is the Fight's kill (`_read_dead`), once; a `done` span with strikes and no health fall
  counts them in the no-progress streak STALL_SWINGS reads (`_melee_span`); `kill` retires it; `handback` {id, d}
  (why crowd, a standing zombie the press would take, or standing, one within HANDBACK_R of a finish) re-pins to that
  zombie when it is the nearer (`_melee_crowd`), else gives the next choose to the ladder (fix 1, M1: never a fresh
  melee on the geometry the Lua just refused); `lost` gives the next choose to the ladder, and by its why leaves the
  target unreachable: out of reach (the walk that did not close, the Lua's K.STOMP_APPROACH_MS bound) for SEEK_SKIP_S,
  as the ladder's failed stomp walk is left, no progress (STALL_SWINGS presses that lowered nothing) for the ladder's
  own no-progress mark (UNREACHABLE_S), out of range never; `too far` and `no weapon` give the next choose to the
  ladder whatever it sends (`_m_ladder`); `not loaded`, `bad args` and
  `unknown type` (a build that cannot run it) end the melee for the rest of the Fight (`melee_off`, as a failed
  stance leg ends the stand); `interrupted`, `timeout` and `no target` leave that target to the ladder for
  MELEE_BACKOFF_TICKS planner ticks (`_m_backoff`, fix 1, m2: Survive's FAILED_COOLDOWN_TICKS), logged `backoff`;
  every end is logged `melee_end` {.., end[, why]} by the next choose. A ladder command sent in its place retires the
  maneuver (the Lua supersedes its melee), and so does another sender's (`Maneuver.observe`'s `superseded`), as a leg
  is superseded: the flee's hand-over among them.
- The log: `maneuver` (`Melee.log`: target, mode, sends, step, d, the counts, spent, the last press leaf) on every
  choose that dispatches and every observe while it runs, `ladder` (the ladder's command type it replaced), `melee`
  {mode, pain} on every send (P28-H: the frame's `body.armPain`, so a write-up reads the swings under pain), with
  `resend` "inputs" on a re-send and (Plan 35) `withdraw` [vx, vy] on a send carrying the withdraw bias.
- Plan 35 (the footwork, PZA/1.13; the spec's §§ 3.2 and 3.3; Task 8 removed its switches and the crowd gate): every
  melee carries `work` (`_work_inputs`: WORK_R, WORK_CRAWLER_R, WORK_BAND_LO, the floor FLEE_HEALTH, `pile` true, so
  the reflex meets the pile and the crawlers; the withdraw bias the engagement picker's vector, `withdraw`, Plan 36
  Task 3's `group.ThreatGroup._pull`, else none; backswing the Fight's `backswing`, threat.Threat's BACKSWING, Plan 36
  Task 2a addendum), and the running melee with `work` is the
  engagement (`_engaged`): `_melee_holds` holds it whatever its pin, the pin-first and the finish read, until a re-send
  is due, and the choose that follows re-sends it and nothing else (`_engage_resend`: no ladder leg supersedes it); the
  threat branch's rows answer the hold above FLEE_HEALTH (`threat.Threat._engage_holds`, logged `engage_hold` {rule}).
  Its ends: `handback` why `floor` (the body's health at FLEE_HEALTH) gives the next choose to the ladder (the threat
  branch's health flee reads the health on its own), `clear` (no zombie left to meet) as `lost` out of range (the
  ladder's, no mark); any end but `floor` with a standing zombie (not a crawler) within KEEP_R is followed by the melee
  at the pin, no ladder choose and no backoff (`_contact_rule`, the one rule: fixes 8 and 8b, Task 8 fix 1; a `lost`
  end's zombie marked and left out of P27-N's pin, `_stalled`), logged `engage_dispatch` {from: the end}.
- Plan 37 Task 3 (the disposition, `disposition.Disposer`): the work carries the Fight's `disposition` and `release`
  (Survive sets both each tick, as the withdraw); the hand-back why `released` (PZA/1.16: the release the planner
  asked) gives the next choose to the ladder as `floor` does, in contact too (the Flee takes it next).
"""
from agent.base.planner.crawler import is_crawler
from agent.base.planner.maneuvers import Melee
from agent.base.planner.maneuvers.melee import MeleeInputs, WorkInputs
from agent.base.planner.policies import (FLEE_HEALTH, KEEP_R, MELEE_BACKOFF_TICKS,
                                         MELEE_RELEASE_R, SEEK_SKIP_S, STALL_SWINGS, STRING_RELEASE_R, UNREACHABLE_S,
                                         WORK_BAND_LO, WORK_CRAWLER_R, WORK_R, arm_pain, line_to, on_floor,
                                         target_id_ok, zdist)
from agent.base.pza1 import Attack

MELEE_LEGS = ("enter", "back", "stand")   # the stance legs a melee replaces logged with no `engage_dispatch`
MELEE_SENDS = ("attack", "shove", "stomp")   # the ladder's sends at its pin a melee replaces (an attack at a fallen
                                             # pin is the floor swing)
LADDER_ENDS = ("too far", "no weapon")   # a melee's ends that give the next choose to the ladder (and `lost`)
LOST_UNREACHABLE = {"out of reach": SEEK_SKIP_S, "no progress": UNREACHABLE_S}   # a `lost` end's why -> the seconds
                                         # its target is left unreachable (the ladder's own marks)
OFF_ENDS = ("not loaded", "bad args", "unknown type")    # ... that end the melee for the rest of the Fight
BACKOFF_ENDS = ("interrupted", "timeout", "no target")   # ... that leave its target to the ladder for
                                                         # MELEE_BACKOFF_TICKS (fix 1, review-t7b m2)
WORK_ENDS = ("floor", "clear", "released")   # Plan 35: a `handback`'s whys under `work` that give the next choose to
                                             # the ladder, no re-pin (the body at the floor; nothing left to meet, as
                                             # `lost` out of range; Plan 37 Task 3: the release the planner asked)
HANDED_BACK = ("floor", "released")   # ... and those that do so in contact too (`_contact_rule`): the Flee's next

# The maneuver registry (Plan 31 Task 8): every maneuver by its logged name, the one table a decider (a variant, the
# ladder's care branch) reads to start one; the Fight's dispatch above starts its Melee directly.
from agent.base.planner.maneuvers import Dress   # noqa: E402  (Task 8's registration lines, one block)
MANEUVERS = {m.name: m for m in (Melee, Dress)}


def _number(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


class FightDispatch:
    """The dispatch to the Fight's maneuver (the module docstring): `Fight`'s mixin."""

    def _init_dispatch(self):
        self.m = None                       # the running maneuver (`maneuvers.Melee`), else None
        self._spent_m = []                  # maneuvers retired whose sends' ends are still read (a late kill)
        self._m_end = None                  # the last ended maneuver's log and end, logged by the next choose
        self._m_ladder = False              # the next choose is the ladder's whatever it sends (an `out of range`)
        self.melee_off = None               # the end after which no melee goes for the rest of the Fight, else None
        self._m_backoff = {}                # zombie id -> planner ticks left in which no melee goes at it (fix 1, m2)
        self._m_from = None                 # Plan 35 fix 5: the dispatch point's `engage_dispatch` source this choose
        self._stalled = {}                  # Plan 35 fix 8b: zombie id -> wall until its reflex stall's mark ends (the
                                            # P27-N pin leaves it out while another stands within KEEP_R, `pin.py`)
        self._m_kept = None                 # Plan 35 fixes 8 and 8b: the end (kill, lost, ...) the next choose follows
                                            # with a standing zombie within KEEP_R: the melee, logged `engage_dispatch`
        self.withdraw = None                # Survive sets it each tick (Plan 36 Task 3): the engagement picker's unit
                                            # vector (`group.ThreatGroup._pull`), the melee's withdraw bias, else None
        self.backswing = False              # Survive sets it each tick (Plan 36 Task 2a addendum: threat.Threat's
                                            # BACKSWING, T21_SWITCHES): the work's backswing; a bare Fight sends none
        self.disposition = None             # Survive sets it each tick (Plan 37 Task 3, `disposition.Disposer`): the
                                            # work's disposition (hunt, hold, string), else None (absent)
        self.release = False                # Survive sets it each tick (Plan 37 Task 3): the hand-back asked

    def _retire_maneuver(self):
        """The running maneuver is dropped, its sends' ends still read (`_spent_m`)."""
        if self.m is not None:
            self._spent_m.append(self.m)
            self.m = None

    def _observe_maneuver(self):
        """The maneuvers' ends (the module docstring), every observe after `_observe_kill` (Survive's `_observe`: once a
        tick, so the backoff counts planner ticks)."""
        self._m_backoff = {zid: n - 1 for zid, n in self._m_backoff.items() if n > 1}
        for m in ([self.m] if self.m is not None else []) + self._spent_m:
            m.observe()
            for zid in m.take_kills():
                self._read_dead(zid)
        self._spent_m = [m for m in self._spent_m if not m.drained()]
        m = self.m
        if m is None:
            return
        span = m.take_span()
        if span is not None:   # Task 15a: the span names the zombie it read (a re-pin's `target`)
            sid = getattr(m, "span_id", None)
            self._melee_span(sid if sid is not None else m.target, span)
        end = m.over()
        if end is None:
            if m.running():
                self.why = dict(self.why, maneuver=m.log())
            return
        self._m_end = dict(m.log(), end=end)
        if getattr(m, "end_why", None) is not None:
            self._m_end["why"] = m.end_why   # PZA/1.10: a handback's or a lost end's why
        self._retire_maneuver()
        contact = self._contact()
        ladder = False
        if end in LADDER_ENDS:
            ladder = True
        elif end == "lost":
            self._lost_end(m)
            ladder = True
        elif end == "handback":
            ladder = m.end_why in WORK_ENDS or not self._melee_crowd(m)   # fix 1, M1: no fresh melee on the
            # same geometry; Plan 35: `floor` the ladder's (the health flee next), `clear` as `lost` out of range
        elif end in OFF_ENDS:
            self.melee_off = end
        elif end in BACKOFF_ENDS and not contact:
            self._m_backoff[m.target] = MELEE_BACKOFF_TICKS
            self._m_end["backoff"] = MELEE_BACKOFF_TICKS
        self._contact_rule(end, getattr(m, "end_why", None), contact, ladder)

    def _contact_rule(self, end, why, contact, ladder):
        """The one rule after a melee end (Plan 35 fixes 8 and 8b; Task 8 fix 1, review-t8 A: a `head_stall` handback
        and a `refused` lost at a pin 0.4 tiles off handed the ladder a raw aim leg): with a standing zombie (not a
        crawler) within KEEP_R (`contact`), no end gives the next choose to the ladder but the body at the floor (a
        handback why `floor`: the health flee is the ladder's), the release the planner asked (Plan 37 Task 3: why
        `released`, HANDED_BACK, the Flee next) and `no weapon` (fix 1b: the ladder's bare-hand shove
        and stomp, not a melee re-sent every choose); the next choose dispatches the melee with `work` at the
        Fight's pin (`_m_kept`, `fight.Fight._choose`), logged `engage_dispatch` {from: the end}, the end's own marks
        written as before (a `lost` end's `_lost_end`, a crowd handback's re-pin); an end in contact sets no backoff.
        With nobody standing within KEEP_R (`clear`, an `out of range` with the zombie gone, any end at range) the
        ladder takes the ends it took before (`ladder`)."""
        if contact and not (end == "handback" and why in HANDED_BACK) and end != "no weapon":
            self._m_kept = end
            if end in ("lost", "too far") and self.disposition is not None:   # Plan 37 Task 3 fix 3: under a
                self._pin_nearest()   # fight disposition the re-dispatch goes at the nearest standing
            return
        if ladder:
            self._m_ladder = True

    def _pin_nearest(self):
        """Plan 37 Task 3 fix 3 (the horde8 trial `x_trial-ladder-20261112-061307`, lines 153 and 157: the melee ended
        in contact and the next line fled): the Fight's pin moved to the nearest standing zombie (not a crawler) within
        KEEP_R (STRING_RELEASE_R under `string`, fix 5: `_contact_r`) that the Fight may target and has not marked (a `lost` end's own mark, `_lost_end`, stands); with none such
        the pin stays (the threat branch's contract lifts a mark, `disposition.Disposer._contract`); never one beyond
        KEEP_R."""
        blocked = self.blocked()
        near = [(d, repr(zid), zid) for zid, z, d in self._standing(self._contact_r()) if target_id_ok(zid)
                and not is_crawler(z)
                and (self.only is None or zid in self.only) and zid not in blocked]
        if near:
            self.target, self.repositioned = min(near)[2], False

    def _contact(self):
        """Plan 35 fixes 8 and 8b: a standing zombie (`_standing`, not a crawler) within KEEP_R of the player; Plan 37
        Task 3 fix 5 (the horde8 trial `x_trial-ladder-20261112-065221`, decision line 11: the string's melee ended
        `lost` out of range at 6.6 tiles and the ladder's approach walk went): within STRING_RELEASE_R under `string`
        (`_contact_r`), so no end there gives the next choose to the ladder's walk, aim or seek."""
        return any(not is_crawler(z) for _, z, _ in self._standing(self._contact_r()))

    def _lost_end(self, m):
        """A `lost` end's marks (the module docstring): its target left unreachable by its why (out of reach for
        SEEK_SKIP_S, no progress for UNREACHABLE_S, out of range and refused never). Plan 35 fix 8 (the
        controller's ruling; the proof round's death, `x_trial-ladder-20261111-112648`, decision lines 365 to 370:
        a112, sent at 25246 fallen 2.85 tiles off, re-pinned in the reflex to 25245 lunging at 0.50 and ended `lost`
        `no progress`; 25246 was marked, and the ladder's choose sent a back leg in its attack's place, 25201 climbing
        the fence at 0.49 bit under it 0.8 s later): the mark goes on the zombie the reflex stalled on (its last
        `target`, `span_id`), for its whole span (fix 8b; the reflex's own re-pin at the stall takes another standing
        zombie), the zombie left out of P27-N's pin while another stands in contact (`_stalled`). Who takes the next
        choose is `_contact_rule`'s."""
        zid = getattr(m, "span_id", None) or m.target
        if m.end_why in LOST_UNREACHABLE:
            self._mark_unreachable(zid, LOST_UNREACHABLE[m.end_why])   # fix 1, m1: as the ladder's stomp walk or stall
            self._stalled[zid] = self.clock() + LOST_UNREACHABLE[m.end_why]

    def _melee_span(self, zid, span):
        """A `done` span at `zid` (strikes, health fell or None): strikes with no health fall count in the
        no-progress streak (`no_progress`, STALL_SWINGS marking the target unreachable, as the ladder's started
        swings and stomps do, `Fight._swing_landed_nothing`); a fall, or a health read missing, restarts it; a span
        with no strike neither counts nor restarts it."""
        strikes, fell = span
        if strikes <= 0:
            return
        if zid != self._streak_id:
            self._streak_id, self._streak_h, self.no_progress = zid, None, 0
        if fell is not False:
            self.no_progress = 0
            return
        self.no_progress += strikes
        if self.no_progress >= STALL_SWINGS:
            self._mark_unreachable(zid)
            self._streak_id, self._streak_h, self.no_progress = None, None, 0

    def _melee_crowd(self, m):
        """A `handback` end (`m.handback` {id, d}: another standing zombie within the press's reach, K.STAND_R, or
        within HANDBACK_R of a finish): that zombie is pinned when the Fight may target it and it is nearer than the
        target (the last progress line's distance, else the frame's), so the next melee goes at it; else the pin
        holds. True when it re-pinned."""
        res = m.handback or {}
        zid, d = res.get("id"), res.get("d")
        zs = self.world.zombies
        if (not target_id_ok(zid) or not _number(d) or zid not in zs or zid in self.blocked()
                or (self.only is not None and zid not in self.only)):
            return False
        t = zs.get(m.target)
        near = m.d if _number(m.d) else (zdist(self.world, t) if t is not None and t.get("x") is not None
                                         and t.get("y") is not None else None)
        if near is None or d < near:
            self.target, self.repositioned = zid, False
            return True
        return False

    def _outside_only(self, m):
        """Plan 35 fix 7: the door fight's (`only`) running melee whose reflex re-pinned (its last progress line's
        `target`) to a zombie outside `only`: it is retired, and the next choose sends a melee at the pin among `only`
        (the reflex's state kept by the Lua's same-target re-send rule only where the pin is its old one)."""
        if self.only is None or m is None:
            return False
        t = m._progress.get("target")
        return isinstance(t, int) and not isinstance(t, bool) and t not in self.only

    def _walk_meets_pin(self):
        """Plan 35 fix 6 (the arena lone wave's trial `x_trial-ladder-20261110-100118`, decision lines 25 to 42: the
        Fight, out of the stance at three chasers, sent its approach walk a9 at 3648 7.96 tiles off, and `busy` held it
        16 s, to its `done`, while 3648 and 3651 stood at 0.3 to 0.8 tiles and bit six times): the melee can go
        (`_melee_on`) and the pin stands (not `onFloor`) within KEEP_R on a line not read blocked, so a running walk
        gives way and the dispatch sends the melee at the pin in the walk's place."""
        if not self._melee_on() or not target_id_ok(self.target):
            return False
        z = self.world.zombies.get(self.target)
        if z is None or z.get("x") is None or z.get("y") is None or on_floor(z):
            return False
        return zdist(self.world, z) <= self._contact_r() and line_to(self.world, z) is not False

    def _contact_r(self):
        """Plan 37 Task 3 fix 2: the tiles within which a standing pin takes the melee in a walk's or a stance leg's
        place: STRING_RELEASE_R under the `string` disposition (the walk away is the reflex's, begun before contact),
        else KEEP_R."""
        return STRING_RELEASE_R if self.disposition == "string" else KEEP_R

    def _release_r(self):
        """The tiles within which a pin is sent the melee at all: STRING_RELEASE_R under `string` (fix 2), else
        MELEE_RELEASE_R."""
        return STRING_RELEASE_R if self.disposition == "string" else MELEE_RELEASE_R

    def _melee_on(self):
        """The melee can go at all: the `melee` rule on, no `melee_off` end, the build announcing `melee` (`World.can`:
        a record whose hello announces none, every golden's, keeps the ladder's own sends)."""
        return "melee" in self.rules and self.melee_off is None and self.world.can("melee")

    def _engaged(self):
        """Plan 35: the engagement, this Fight's running `Melee` (its action the Fight's last and not ended) whose last
        send carried `work` (`Melee.work`); no Python leg supersedes it (the module docstring)."""
        m = self.m
        return m is not None and self.last is not None and m.action is self.last and m.work is not None and m.running()

    def _melee_holds(self):
        """`busy` for the running melee (the module docstring): held whatever the pin, the pin-first and the finish read
        (Plan 35: the reflex re-pins, finishes and steps), until a re-send is due (`Melee.resend_due`, its inputs read
        afresh on the tick), or the door fight's melee re-pinned outside `only` (fix 7: retired, a new send at the pin).
        Task 8 deleted the pin read's give-ways (P27-N's pin-first, the finish of another fallen zombie, a re-pinned
        target), which every melee's `work` had left to the reflex."""
        m = self.m
        if m is None or m.action is not self.last:
            return False
        z = self.world.zombies.get(m.target)
        if z is not None:
            m.inputs = self._melee_inputs(self._melee_mode_at(z), z)   # the inputs read afresh on the tick
        if self._outside_only(m):
            self._retire_maneuver()   # Plan 35 fix 7: the door fight's melee re-pinned outside `only`: a new send
            return False
        if self.actions.current is not m.action:
            return True   # Plan 37 Task 3 fix 3: a keepMoving rip or bandage rides it: no re-send ends the ride
        if self._beyond_release(m):
            self._retire_maneuver()   # fix 8: no `hunt` or `hold` melee re-sent at a pin beyond its release radius
            return False
        return not m.resend_due()

    def _beyond_release(self, m):
        """Plan 37 Task 3 fix 8 (the horde8 trial `x_trial-ladder-20261112-072340`, lines 24 and 25: the string's melee
        re-sent as `hold` at a pin 6.6 tiles off, refused `too far`): under `hunt` or `hold` the running melee's target
        (its last progress line's re-pinned `target`, else its own) stands beyond MELEE_RELEASE_R."""
        if self.disposition not in ("hunt", "hold"):
            return False
        t = m._progress.get("target")
        zid = t if isinstance(t, int) and not isinstance(t, bool) else m.target
        z = self.world.zombies.get(zid)
        return z is not None and z.get("x") is not None and zdist(self.world, z) > MELEE_RELEASE_R

    def _melee_mode(self, cmd):
        """The melee's mode where the ladder's `cmd` is at the dispatch point (the module docstring), else None. Plan 35
        fix 5 (the controller's ruling; the street-1 trial `x_trial-ladder-20261110-095321`, decision lines 152 to 234:
        the corner's Fight sent raw attacks and shoves, then every back leg, circle and shove back as an aim, four
        bites with no melee): a cornered Fight (`point_blank`) dispatches the melee with `work` too (logged
        `engage_dispatch` {from "corner"}), and an aim leg of any kind at a standing pin within KEEP_R is a dispatch
        point (the fence wait's aside), logged {from "point_blank_leg"} when the leg is a corner Fight's or one
        MELEE_LEGS lacks. Fix 7 (the trial `x_trial-ladder-20261110-104053`, decision lines 315 to 415: the sheltered
        door fight sent raw attacks, strain shoves and wounded aim legs at 0.42 to 0.76 tiles, every bite on its
        lines): the door fight (`only`: its pin among `only`, never a melee at another) and the doorway stand
        (`doorway`: `doorway.Doorway`'s own dispatch) dispatch it too, logged {from "door" | "doorway"}. Task 8 fix 1
        (review-t8 C): P30-C's walk to the post of a closed door (`door_step` "post", the zombie behind the door) is
        no dispatch point; every other leg is, whatever the map's line reads (a just-opened door keeps its scanned
        edge, a hoppable fence reads blocked: the reflex's own probes and its stall own them)."""
        self._m_from = None
        if cmd is None or not self._melee_on():
            return None
        zid = getattr(cmd, "targetId", None)
        z = self.world.zombies.get(zid) if target_id_ok(zid) and zid == self.target else None
        if z is None or z.get("x") is None or z.get("y") is None or (self.only is not None and zid not in self.only):
            return None
        d = zdist(self.world, z)
        if d > self._release_r() or self._m_backoff.get(zid):
            return None
        if cmd.TYPE == "aim":
            if ("fence_wait" in self.why or self.why.get("door_step") == "post" or d > self._contact_r()
                    or on_floor(z)):
                return None
            if self.point_blank or self.why.get("leg") not in MELEE_LEGS:
                self._m_from = "point_blank_leg"
        elif cmd.TYPE not in MELEE_SENDS:
            return None
        elif self.point_blank:
            self._m_from = "corner"
        if self.doorway is not None or self.only is not None:
            self._m_from = "doorway" if self.doorway is not None else "door"
        if cmd.TYPE == "stomp":
            return "finish"
        return self._melee_mode_at(z)

    def _melee_mode_at(self, z):
        """The melee's mode at pin `z`: finish at a fallen pin, else shove under a hold or in a shove-and-stomp Fight
        (`_hold_bars`), else strike (P28-H 3: the arms' pain alone strikes; the Lua's own spent read takes the shove and
        the stomp once the arms or the moodles are spent)."""
        if on_floor(z):
            return "finish"
        return "shove" if self._hold_bars() else "strike"

    def _melee_inputs(self, mode, z):
        """The send's `MeleeInputs` at pin `z` (the module docstring), read afresh."""
        return MeleeInputs(mode, self.reach_r() or 0.0, "floor_finish" in self.rules and not self.floor_swing_barred(),
                           self._work_inputs())

    def _work_inputs(self):
        """Plan 35: the send's `WorkInputs` (the module docstring): the withdraw bias the engagement picker's vector
        (Plan 36 Task 3, `withdraw`), else none; Plan 36 Task 2a addendum: backswing the Fight's `backswing`; Plan 37
        Task 3: the Fight's `disposition` and `release`."""
        w = self.withdraw
        withdraw = None if w is None else (float(w[0]), float(w[1]))
        return WorkInputs(WORK_R, WORK_CRAWLER_R, WORK_BAND_LO, withdraw, FLEE_HEALTH, True,
                          backswing=bool(self.backswing), disposition=self.disposition, release=bool(self.release))

    def _melee_dispatch(self, cmd):
        """The ladder's `cmd`, or at the dispatch point the running maneuver's next command (a new `Melee` where none
        runs at the pin): its re-send, or None while it runs and none is due (nothing sent; it goes on)."""
        mode = self._melee_mode(cmd)
        if mode is None:
            mode, cmd = self._walk_melee(cmd)
        if mode is None:
            return cmd
        z = self.world.zombies[cmd.targetId]
        out = None
        for _ in range(2):   # a maneuver its own step finds superseded is retired, and a new one starts
            m = self.m
            if m is None or m.target != cmd.targetId or m.over() is not None:
                self._retire_maneuver()
                self.m = m = Melee(self.world, self.actions, self.clock, cmd.targetId)
            m.inputs = self._melee_inputs(mode, z)
            out = m.step()
            if out is not None or m.over() is None:
                break
        self.why = dict(self.why, maneuver=m.log(), ladder=cmd.TYPE)
        self._melee_why(m, out)
        if out is not None and m.resend is None and self._m_from is not None:
            self.why["melee"]["engage_dispatch"] = {"from": self._m_from}   # Plan 35 fix 5: the first send
        return out

    def _walk_melee(self, cmd):
        """Plan 35 fix 6: `(mode, Attack at the pin)` in place of the ladder's walk (or of its nothing under a hit
        reaction, P24-A (i)) while the pin stands within KEEP_R (`_walk_meets_pin`) and the dispatch takes the attack,
        `engage_dispatch` {from "walk" | "hit_reaction"}; else `(None, cmd)`."""
        hit = cmd is None and "hitReaction" in self.why
        if not ((hit or (cmd is not None and cmd.TYPE == "walkTo")) and self._walk_meets_pin()):
            return None, cmd
        alt = Attack(self.target)
        mode = self._melee_mode(alt)
        if mode is None:
            return None, cmd
        self._m_from = "hit_reaction" if hit else "walk"
        return mode, alt

    def _melee_why(self, m, out):
        """A send's `melee` why: {mode, pain} (P28-H: the swings under pain read), `resend` on a re-send, `withdraw`
        [vx, vy] when it carries the withdraw bias (Plan 35)."""
        if out is None:
            return
        self.why["melee"] = {"mode": m.mode, "pain": arm_pain(self.world)}
        if m.resend is not None:
            self.why["melee"]["resend"] = m.resend
        if m.work is not None and m.work.withdraw is not None:
            self.why["melee"]["withdraw"] = list(m.work.withdraw)

    def _engage_resend(self):
        """Plan 35: the choose under the engagement (`busy` gave way only for a re-send, `_melee_holds`): the engaged
        melee's re-send on its inputs read afresh, else None; nothing else is sent."""
        m = self.m
        out = m.step()
        self.why = dict(self.why, maneuver=m.log())
        self._melee_why(m, out)
        return out
