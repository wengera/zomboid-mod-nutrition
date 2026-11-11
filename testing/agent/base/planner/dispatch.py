"""The Fight's dispatch to its maneuver (Plan 28 Task 7b, survival iteration 22; the architecture review
`arch-review-cerebellum.md` § 3.5, cut 1 of the maneuver layer): the mixin `FightDispatch` (`fight.Fight`'s), which
starts or continues the Fight's `Melee` (`maneuvers.melee`, the planner's face of the reflex skill `melee`: PZA/1.8,
Task 7a; the meet of PZA/1.10, Plan 31 Task 2) where the Fight's decision ladder (`Fight._ladder`, every rule before this one) would send an in-reach
command at its pin. Its state is the Fight's own (`_init_dispatch`), and `fight.py`'s module docstring is the record.

- The dispatch point (`_melee_mode`): with the `melee` rule on (Survive's MELEE), the build announcing `melee`
  (`World.can`, so no golden's record, whose hello announces none, moves) and no `melee_off`, a ladder command at the
  pin (its `targetId` the Fight's `target`), the pin listed within MELEE_RELEASE_R: an `aim` leg `enter`, `back` or
  `stand` within KEEP_R at a standing pin (the fence wait's leg excepted), an `attack` (the swing, or at a fallen pin
  the floor swing), a `shove` or a `stomp`. Mode `finish` at a fallen pin or for a stomp, else `shove` under a hold
  or in a shove-and-stomp Fight (`_hold_bars`: `spent`, R2; `shove_only`, but the low fight's full swing when due),
  else `strike`; in mode `shove` with a weapon held the reflex swings after a shove that knocked nothing down (Plan 31
  Task 15a, the controller's ruling on review-t15a M1, Angus's stand and fight: a hold or a low fight with a weapon
  presses on, the spent meet's shove-swing alternation governing; unarmed it cannot swing and shoves again), so the
  mode bars the ladder's own swing sends only (`no_swing`). Task 7e (ruling P28-H 3, E22: 27 of its 38 melees ran in `shove` mode once the first scratch put
  `body.armPain` past STRAIN_HARD, and 12 of its 13 bites inside a span came 0.746 to 0.932 s after a shove that
  knocked nothing down): the arms' pain alone (`arms_hurt`, P24-AP's bar, which `no_swing` keeps for the ladder) no
  longer selects `shove`, since the melee's swing goes at the reach, where T86 read every swing at a standing zombie
  lowering it, never at point blank, where P27-L's divided swings lowered nothing. The approach-and-swing Fight (a
  non-stance one: more than MAX_FIGHT held, the health under the fight line, a trapped character) is dispatched too:
  its `attack` at the pin is "an attack" (review-t7b's ruling (b): a PZA/1.8 build announcing `melee` announces
  `aim`, and the Lua takes its own force-aim). The crowd gate (fix 1, review-t7b M1, at the Lua's crowd end of the
  time, two; Plan 31 Task 15a fix 1, review-t15a I1, at its end since Task 15a): no melee while MELEE_CROWD_N standing
  zombies, a standing pin counted, are listed within MELEE_CROWD_R of the player (the Lua would end it handback crowd
  with no press, #4290), the ladder's rules owning that tick; with fewer the melee goes, the Lua re-pinning to the
  nearer of two and pressing it (#4688: the press is the defence); nor at a target in its backoff (below); nor in the
  crawler clear's backpedal's place (Plan 34, ruling P34-A fix B: `crawler_clear` on the why,
  `crawler.FightCrawler._crawler_clear`).
  Everything above the point stays the ladder's (the pin and its re-pins, P27-N's pin-first, the finish's choice of a
  fallen zombie other than the pin, the fence wait, the edge route, the reposition, the seek, the pull, the advance's
  `toward` legs and walks, the approach); the corner Fight (`point_blank`), the door fight (`only`) and the doorway
  stand (`doorway`) keep the ladder whole in cut 1, and the flee's finish is the threat branch's own.
- The inputs (`_melee_inputs`, read at every send and on every `busy`): `reach` the Fight's `reach_r` (the frame's
  `weapon.reach` plus ATTACK_MARGIN), 0 where it reads none (the Lua's `K.reachOf`); `floorSwing` with the
  `floor_finish` rule on (P27-G, the floor swing ahead of the stomp) and the floor swing not barred
  (`floor_swing_barred`, P28-C). PZA/1.10 (Plan 31 Task 2) dropped the back leg's heading, the time span and P30-A's
  `closeR` (the `swing_close` rule reads nothing since): the Lua's meet presses at the predicted collision and again
  after a swing that did nothing, with no back step and no time end.
- `busy` (`_melee_holds`): a running melee holds until its inputs change its behaviour (`Melee.resend_due`: the spent
  mode, the floor swing, the reach, read afresh on the tick), its target is no longer the pin, P27-N's pin-first would take a marked zombie (`_pin_marked`, the target not among `_pin_free`: fix
  1, review-t7b M2, so a marked attacker at point blank is pinned on its own tick as on the ladder, whose stance leg
  gives way within FIGHT_REACH on every tick), or the finish would take another fallen zombie (`_finishable`); its
  own pin fallen, it holds (the Lua's floor reflexes).
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
- Plan 35 Task 2 (the footwork, PZA/1.13; the spec's §§ 3.2 and 3.3): with the Fight's `footwork` rule (Survive's
  FOOTWORK) and the build announcing mod WORK_MOD or later (`World.mod_at_least`: every golden's hello announces 1.11
  or earlier, so none moves), every melee carries `work` (`_work_inputs`: WORK_R, WORK_CRAWLER_R, WORK_BAND_LO, the
  floor FLEE_HEALTH, `pile` true; with the `withdraw` rule (WITHDRAW) the fighting retreat's heading, `retreat`, while
  GROUP_LEAVE_N or more stand within GROUP_ENTRY_R, `group_n`, else none). With the `engage_hold` rule too
  (ENGAGE_HOLD) the crowd gate and the crawler clear's exemption are off at the dispatch point (the reflex meets the
  pile and the crawlers), and the running melee with `work` is the engagement (`_engaged`): `_melee_holds` holds it
  whatever its pin, the pin-first and the finish read, until a re-send is due, and the choose that follows re-sends it
  and nothing else (`_engage_resend`: no ladder leg supersedes it); the Fight's own give-ways (`fight.Fight.busy`) and
  the threat branch's flees (`threat.Threat._engage_holds`) answer the hold, logged `engage_hold` {rule}. Its ends:
  `handback` why `floor` (the body's health at FLEE_HEALTH) gives the next choose to the ladder (the threat branch's
  health flee reads the health on its own), `clear` (no zombie left to meet) as `lost` out of range (the ladder's, no
  mark).
"""
from agent.base.planner.crawler import is_crawler
from agent.base.planner.maneuvers import Melee
from agent.base.planner.maneuvers.melee import MeleeInputs, WorkInputs
from agent.base.planner.policies import (FLEE_HEALTH, GROUP_LEAVE_N, KEEP_R, MELEE_BACKOFF_TICKS, MELEE_CROWD_N,
                                         POINT_BLANK_R,
                                         MELEE_CROWD_R, MELEE_RELEASE_R, SEEK_SKIP_S, STALL_SWINGS, UNREACHABLE_S,
                                         WORK_BAND_LO, WORK_CRAWLER_R, WORK_R, arm_pain, line_to, on_floor,
                                         target_id_ok, zdist)
from agent.base.pza1 import Attack

MELEE_LEGS = ("enter", "back", "stand")   # the ladder's stance legs within KEEP_R a melee replaces
MELEE_SENDS = ("attack", "shove", "stomp")   # the ladder's sends at its pin a melee replaces (an attack at a fallen
                                             # pin is the floor swing)
LADDER_ENDS = ("too far", "no weapon")   # a melee's ends that give the next choose to the ladder (and `lost`)
LOST_UNREACHABLE = {"out of reach": SEEK_SKIP_S, "no progress": UNREACHABLE_S}   # a `lost` end's why -> the seconds
                                         # its target is left unreachable (the ladder's own marks)
OFF_ENDS = ("not loaded", "bad args", "unknown type")    # ... that end the melee for the rest of the Fight
BACKOFF_ENDS = ("interrupted", "timeout", "no target")   # ... that leave its target to the ladder for
                                                         # MELEE_BACKOFF_TICKS (fix 1, review-t7b m2)
WORK_ENDS = ("floor", "clear")   # Plan 35: a `handback`'s whys under `work` that give the next choose to the ladder,
                                 # no re-pin (the body at the floor; nothing left to meet, as `lost` out of range)
WORK_MOD = "1.13"   # Plan 35 (PZA/1.13): the hello's least mod version whose melee takes the `work` arguments

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
        self._m_lost = False                # Plan 35 fix 8: the next choose follows a `lost` end the engagement keeps
        self.group_n = 0                    # Survive sets it each tick (Plan 35, WITHDRAW): the standing zombies within
                                            # GROUP_ENTRY_R (`group.ThreatGroup._group_read`)

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
        if end in LADDER_ENDS:
            self._m_ladder = True
        elif end == "lost":
            self._lost_end(m)
        elif end == "handback":
            if m.end_why in WORK_ENDS or not self._melee_crowd(m):
                self._m_ladder = True   # fix 1, M1: no fresh melee on the same geometry; the ladder's press (Plan 35:
                                        # `floor` the ladder's, the health flee next; `clear` as `lost` out of range)
        elif end in OFF_ENDS:
            self.melee_off = end
        elif end in BACKOFF_ENDS:
            self._m_backoff[m.target] = MELEE_BACKOFF_TICKS
            self._m_end["backoff"] = MELEE_BACKOFF_TICKS

    def _lost_end(self, m):
        """A `lost` end (the module docstring): its target left unreachable by its why (out of reach for SEEK_SKIP_S,
        no progress for UNREACHABLE_S, out of range never), the next choose the ladder's. Plan 35 fix 8 (the
        controller's ruling; the proof round's death, `x_trial-ladder-20261111-112648`, decision lines 365 to 370:
        a112, sent at 25246 fallen 2.85 tiles off, re-pinned in the reflex to 25245 lunging at 0.50 and ended `lost`
        `no progress`;
        25246 was marked, and the ladder's choose (`_m_ladder`) sent RETREAT_REGAIN's back leg in its attack's place,
        25201 climbing the fence at 0.49 bit under it 0.8 s later): under the engagement's dispatch (`_pile_met`) the
        mark goes on the zombie the reflex stalled on (its last `target`, `span_id`), lifted (never written) while it
        stands within POINT_BLANK_R on a line not read blocked (a stall at point blank is the reflex's miss count; a
        fence read on the map keeps it); and with a standing zombie (not a crawler) within KEEP_R the next choose is
        no ladder's: it sends the melee with `work` at the Fight's pin (`_m_lost`, `fight.Fight._choose`), logged
        `engage_dispatch` {from "lost"}."""
        pile = self._pile_met()
        zid = (getattr(m, "span_id", None) or m.target) if pile else m.target
        if m.end_why in LOST_UNREACHABLE and not (pile and self._point_blank_clear(zid)):
            self._mark_unreachable(zid, LOST_UNREACHABLE[m.end_why])   # fix 1, m1: as the ladder's stomp walk or stall
        if pile and m.end_why in LOST_UNREACHABLE and any(not is_crawler(z) for _, z, _ in self._standing(KEEP_R)):
            self._m_lost = True   # Plan 35 fix 8: the engagement kept, no ladder choose
            return
        self._m_ladder = True

    def _point_blank_clear(self, zid):
        """Plan 35 fix 8: zombie `zid` stands (not `onFloor`) within POINT_BLANK_R on a line not read blocked."""
        z = self.world.zombies.get(zid)
        if z is None or z.get("x") is None or z.get("y") is None or on_floor(z):
            return False
        return zdist(self.world, z) <= POINT_BLANK_R and line_to(self.world, z) is not False

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

    def _work_on(self):
        """Plan 35 FOOTWORK: the melee carries `work` (the rule on, the build announcing mod WORK_MOD or later)."""
        return "footwork" in self.rules and self.world.mod_at_least(WORK_MOD)

    def _pile_met(self):
        """Plan 35 ENGAGE_HOLD at the dispatch point: the melee carries `work` with `pile` and the hold is on, so the
        crowd gate and the crawler clear's exemption are off (the reflex meets the pile and the crawlers)."""
        return "engage_hold" in self.rules and self._work_on()

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
        16 s, to its `done`, while 3648 and 3651 stood at 0.3 to 0.8 tiles and bit six times: a walk the Fight sent
        that is not the stance's own holds until it ends, `fight.Fight.busy`'s tail, before this plan as after):
        under the engagement's dispatch (`_pile_met`) the pin stands (not `onFloor`) within KEEP_R on a line not read
        blocked, so a running walk gives way and the dispatch sends the melee at the pin in the walk's place."""
        if not self._pile_met() or not target_id_ok(self.target):
            return False
        z = self.world.zombies.get(self.target)
        if z is None or z.get("x") is None or z.get("y") is None or on_floor(z):
            return False
        return zdist(self.world, z) <= KEEP_R and line_to(self.world, z) is not False

    def _engaged(self):
        """Plan 35 ENGAGE_HOLD: the engagement, the rule on and this Fight's running `Melee` (its action the Fight's
        last and not ended) whose last send carried `work` (`Melee.work`); no Python leg supersedes it (the module
        docstring)."""
        m = self.m
        return ("engage_hold" in self.rules and m is not None and self.last is not None and m.action is self.last
                and m.work is not None and m.running())

    def _engage_note(self, rule):
        """Plan 35 ENGAGE_HOLD: the Fight's rule `rule` held off the engagement this tick, logged `engage_hold` {rule}
        (the first one read on the tick)."""
        self.why.setdefault("engage_hold", {"rule": rule})

    def _engage_hold(self, rule):
        """`busy`'s answer where rule `rule` would cut the engagement: logged (`_engage_note`), the melee's own hold
        (`_melee_holds`: held until a re-send is due)."""
        self._engage_note(rule)
        return self._melee_holds()

    def _melee_holds(self):
        """`busy` for the running melee (the module docstring); Plan 35: held while engaged (`_engaged`) whatever the
        pin, until a re-send is due."""
        m = self.m
        if m is None or m.action is not self.last:
            return False
        z = self.world.zombies.get(m.target)
        if z is not None:
            m.inputs = self._melee_inputs(self._melee_mode_at(z), z)   # the inputs read afresh on the tick
        if self._outside_only(m):
            self._retire_maneuver()   # Plan 35 fix 7: the door fight's melee re-pinned outside `only`: a new send
            return False
        if m.resend_due():
            return False
        if self._engaged():
            return True   # Plan 35 ENGAGE_HOLD: the reflex re-pins, finishes and steps; no pin read cuts it
        t = self._target(pin=False)
        if t is None or t[0] != m.target:
            return False
        if self._pin_marked() and m.target not in self._pin_free():
            return False   # fix 1, M2: P27-N's pin-first takes a marked attacker on its own tick, as on the ladder
        fin = self._finishable()
        return not fin or fin[0][0] == m.target

    def _melee_mode(self, cmd):
        """The melee's mode where the ladder's `cmd` is at the dispatch point (the module docstring), else None. Plan 35
        fix 5 (the controller's ruling; the street-1 trial `x_trial-ladder-20261110-095321`, decision lines 152 to 234:
        the corner's Fight sent raw attacks and shoves, then, kept by the threat branch after its corner ended, its
        `point_blank` still set, every back leg, circle and shove back went as an aim, four bites with no melee): under
        the engagement's dispatch (`_pile_met`) a cornered Fight (`point_blank`) dispatches the melee with `work` too
        (logged `engage_dispatch` {from "corner"}), and an aim leg of any kind at a standing pin within KEEP_R is a
        dispatch point (the fence wait's aside), logged {from "point_blank_leg"} when the leg is a corner Fight's or
        one MELEE_LEGS lacks. Fix 7 (the trial `x_trial-ladder-20261110-104053`, decision lines 315 to 415: the
        sheltered door fight sent raw attacks, strain shoves and wounded aim legs at 22774 and 22776 at 0.42 to 0.76
        tiles, every bite on its lines): under `_pile_met` the door fight (`only`: its pin among `only`, never a melee at
        another) and the doorway stand (`doorway`: `doorway.Doorway`'s own dispatch) dispatch it too, logged
        {from "door" | "doorway"}."""
        self._m_from = None
        pile = self._pile_met()   # Plan 35 ENGAGE_HOLD: the reflex meets the pile and the crawlers
        if (cmd is None or "melee" not in self.rules or self.melee_off is not None or not self.world.can("melee")
                or (not pile and (self.point_blank or self.only is not None or self.doorway is not None))):
            return None
        if "crawler_clear" in self.why and not pile:
            return None   # Plan 34 fix B: the backpedal from the crawlers is the leg, never a melee in its place
        zid = getattr(cmd, "targetId", None)
        z = self.world.zombies.get(zid) if target_id_ok(zid) and zid == self.target else None
        if z is None or z.get("x") is None or z.get("y") is None or (self.only is not None and zid not in self.only):
            return None
        d = zdist(self.world, z)
        if d > MELEE_RELEASE_R or self._m_backoff.get(zid):
            return None
        if not pile and self._crowded(zid, z):
            return None   # the crowd gate (the module docstring): the Lua would end it handback crowd
        if cmd.TYPE == "aim":
            leg_ok = pile or self.why.get("leg") in MELEE_LEGS   # Plan 35 fix 5: any leg under the engagement
            if "fence_wait" in self.why or not leg_ok or d > KEEP_R or on_floor(z):
                return None
            if pile and (self.point_blank or self.why.get("leg") not in MELEE_LEGS):
                self._m_from = "point_blank_leg"
        elif cmd.TYPE not in MELEE_SENDS:
            return None
        elif self.point_blank:
            self._m_from = "corner"   # Plan 35 fix 5 (only under `pile`: the guard above)
        if self.doorway is not None or self.only is not None:   # Plan 35 fix 7 (only under `pile`: the guard above)
            self._m_from = "doorway" if self.doorway is not None else "door"
        if cmd.TYPE == "stomp":
            return "finish"
        return self._melee_mode_at(z)

    def _crowded(self, zid, z):
        """The crowd gate (Plan 31 Task 15a fix 1, review-t15a I1): MELEE_CROWD_N standing zombies within
        MELEE_CROWD_R of the player, pin `zid` (zombie `z`) counted while it stands, the Lua's crowd end mirrored
        (`PZAgent_StanceMelee.lua`'s `crowdOf`; review-t7b M1's gate at the Lua's old end of two)."""
        n = len(self._standing(MELEE_CROWD_R, (zid,))) + (0 if on_floor(z) else 1)
        return n >= MELEE_CROWD_N

    def _melee_mode_at(self, z):
        """The melee's mode at pin `z`: finish at a fallen pin, else shove under a hold or in a shove-and-stomp Fight
        (`_hold_bars`) or for RETREAT_REGAIN's shove-form press (Plan 34 Task 3c, `fight.Fight._regain_shove`: two or
        more standing within FIGHT_REACH, the knockback opening room), else strike (P28-H 3: the arms' pain alone
        strikes; the Lua's own spent read takes the shove and the stomp once the arms or the moodles are spent)."""
        if on_floor(z):
            return "finish"
        return "shove" if self._hold_bars() or self._regain_shove() else "strike"

    def _melee_inputs(self, mode, z):
        """The send's `MeleeInputs` at pin `z` (the module docstring), read afresh."""
        return MeleeInputs(mode, self.reach_r() or 0.0, "floor_finish" in self.rules and not self.floor_swing_barred(),
                           self._work_inputs())

    def _work_inputs(self):
        """Plan 35 FOOTWORK: the send's `WorkInputs` (the module docstring), else None (the rule off, an older
        build)."""
        if not self._work_on():
            return None
        withdraw = None
        if "withdraw" in self.rules and self.retreat is not None and self.group_n >= GROUP_LEAVE_N:
            withdraw = (float(self.retreat[0]), float(self.retreat[1]))   # WITHDRAW: the fighting retreat's heading
        return WorkInputs(WORK_R, WORK_CRAWLER_R, WORK_BAND_LO, withdraw, FLEE_HEALTH, True)

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
        """Plan 35 ENGAGE_HOLD: the choose under the engagement (`busy` gave way only for a re-send, `_melee_holds`):
        the engaged melee's re-send on its inputs read afresh, else None; nothing else is sent."""
        m = self.m
        out = m.step()
        self.why = dict(self.why, maneuver=m.log())
        self._melee_why(m, out)
        return out
