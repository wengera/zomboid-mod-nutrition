"""The Fight's dispatch to its maneuver (Plan 28 Task 7b, survival iteration 22; the architecture review
`arch-review-cerebellum.md` § 3.5, cut 1 of the maneuver layer): the mixin `FightDispatch` (`fight.Fight`'s), which
starts or continues the Fight's `Melee` (`maneuvers.melee`, the planner's face of Task 7a's reflex skill `melee`,
PZA/1.8) where the Fight's decision ladder (`Fight._ladder`, every rule before this one) would send an in-reach
command at its pin. Its state is the Fight's own (`_init_dispatch`), and `fight.py`'s module docstring is the record.

- The dispatch point (`_melee_mode`): with the `melee` rule on (Survive's MELEE), the build announcing `melee`
  (`World.can`, so no golden's record, whose hello announces none, moves) and no `melee_off`, a ladder command at the
  pin (its `targetId` the Fight's `target`), the pin listed within MELEE_RELEASE_R: an `aim` leg `enter`, `back` or
  `stand` within KEEP_R at a standing pin (the fence wait's leg excepted), an `attack` (the swing, or at a fallen pin
  the floor swing), a `shove` or a `stomp`. Mode `finish` at a fallen pin or for a stomp, else `shove` under a hold
  or in a shove-and-stomp Fight (`_hold_bars`: `spent`, R2; `shove_only`, but the low fight's full swing when due),
  else `strike`. Task 7e (ruling P28-H 3, E22: 27 of its 38 melees ran in `shove` mode once the first scratch put
  `body.armPain` past STRAIN_HARD, and 12 of its 13 bites inside a span came 0.746 to 0.932 s after a shove that
  knocked nothing down): the arms' pain alone (`arms_hurt`, P24-AP's bar, which `no_swing` keeps for the ladder) no
  longer selects `shove`, since the melee's swing goes at the reach, where T86 read every swing at a standing zombie
  lowering it, never at point blank, where P27-L's divided swings lowered nothing. The approach-and-swing Fight (a
  non-stance one: more than MAX_FIGHT held, the health under the fight line, a trapped character) is dispatched too:
  its `attack` at the pin is "an attack" (review-t7b's ruling (b): a PZA/1.8 build announcing `melee` announces
  `aim`, and the Lua takes its own force-aim). Fix 1 (review-t7b M1): no melee while another standing zombie is
  listed within STAND_MIN_R of the player (the Lua's press would take that one, its `crowd` end), the ladder's P24-AH
  rules owning that tick as before; nor at a target in its backoff (below).
  Everything above the point stays the ladder's (the pin and its re-pins, P27-N's pin-first, the finish's choice of a
  fallen zombie other than the pin, the fence wait, the edge route, the reposition, the seek, the pull, the advance's
  `toward` legs and walks, the approach); the corner Fight (`point_blank`), the door fight (`only`) and the doorway
  stand (`doorway`) keep the ladder whole in cut 1, and the flee's finish is the threat branch's own.
- The inputs (`_melee_inputs`, read at every send): `reach` the Fight's `reach_r` (the frame's `weapon.reach` plus
  ATTACK_MARGIN), 0 where it reads none (the Lua's `K.reachOf`); `back` the stance's `back` heading
  (`Fight._back_heading`: away from the held threats, P28-E's arc from a lone standing zombie within KEEP_R, else
  STEER_TURNS to a clear one), (0, 0) where none is clear; `floorSwing` with the `floor_finish` rule on (P27-G, the
  floor swing ahead of the stomp) and the floor swing not barred (`floor_swing_barred`, P28-C); `closeR` SWING_CLOSE_R
  with the `swing_close` rule on (ruling P30-A, Plan 30 Task 3: the Lua's swing close), else 0 (the rule off).
- `busy` (`_melee_holds`): a running melee holds until its re-send is due (`Melee.resend_due`), its target is no
  longer the pin, P27-N's pin-first would take a marked zombie (`_pin_marked`, the target not among `_pin_free`: fix
  1, review-t7b M2, so a marked attacker at point blank is pinned on its own tick as on the ladder, whose stance leg
  gives way within FIGHT_REACH on every tick), or the finish would take another fallen zombie (`_finishable`); its
  own pin fallen, it holds (the Lua's floor reflexes).
- The ends (`_observe_maneuver`, every observe, after the kill read): a kill on any send of the maneuver, or of one
  it retired (`_spent_m`), is the Fight's kill (`_read_dead`), once; a `done` span with strikes and no health fall
  counts them in the no-progress streak STALL_SWINGS reads (`_melee_span`); `out of range`, `too far` and
  `no weapon` give the next choose to the ladder whatever it sends (`_m_ladder`); `out of reach` (the walk to a
  fallen target that did not close, the Lua's or `Melee`'s own bound across its sends: fix 1, m1) leaves the target
  unreachable for SEEK_SKIP_S, as the ladder's failed stomp walk is left, and gives the next choose to the ladder;
  `crowd` {id, d} re-pins to that zombie when it is the nearer (`_melee_crowd`), else gives the next choose to the
  ladder (fix 1, M1: never a fresh melee on the geometry the Lua just refused); `not loaded`, `bad args` and
  `unknown type` (a build that cannot run it) end the melee for the rest of the Fight (`melee_off`, as a failed
  stance leg ends the stand); `interrupted`, `timeout` and `no target` leave that target to the ladder for
  MELEE_BACKOFF_TICKS planner ticks (`_m_backoff`, fix 1, m2: Survive's FAILED_COOLDOWN_TICKS), logged `backoff`;
  every end is logged `melee_end` {.., end} by the next choose. A ladder command sent in its place retires the
  maneuver (the Lua supersedes its melee), and so does another sender's (`Maneuver.observe`'s `superseded`), as a leg
  is superseded: the flee's hand-over among them.
- The log: `maneuver` (`Melee.log`: target, mode, sends, step, d) on every choose that dispatches and every observe
  while it runs, `ladder` (the ladder's command type it replaced), `melee` {mode, pain} on every send (P28-H: the
  frame's `body.armPain`, so a write-up reads the swings under pain), with `resend` "early" | "time" on a re-send.
"""
from agent.base.planner.maneuvers import Melee
from agent.base.planner.maneuvers.melee import MeleeInputs
from agent.base.planner.policies import (KEEP_R, MELEE_BACKOFF_TICKS, MELEE_RELEASE_R, SEEK_SKIP_S, STALL_SWINGS,
                                         STAND_MIN_R, SWING_CLOSE_R, arm_pain, on_floor, target_id_ok, zdist)

MELEE_LEGS = ("enter", "back", "stand")   # the ladder's stance legs within KEEP_R a melee replaces
MELEE_SENDS = ("attack", "shove", "stomp")   # the ladder's sends at its pin a melee replaces (an attack at a fallen
                                             # pin is the floor swing)
LADDER_ENDS = ("out of range", "too far", "no weapon")   # a melee's ends that give the next choose to the ladder
OFF_ENDS = ("not loaded", "bad args", "unknown type")    # ... that end the melee for the rest of the Fight
BACKOFF_ENDS = ("interrupted", "timeout", "no target")   # ... that leave its target to the ladder for
                                                         # MELEE_BACKOFF_TICKS (fix 1, review-t7b m2)


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
        if span is not None:
            self._melee_span(m.target, span)
        end = m.over()
        if end is None:
            if m.running():
                self.why = dict(self.why, maneuver=m.log())
            return
        self._m_end = dict(m.log(), end=end)
        self._retire_maneuver()
        if end in LADDER_ENDS:
            self._m_ladder = True
        elif end == "out of reach":   # fix 1, m1: as the ladder's failed stomp walk, its target left SEEK_SKIP_S
            self._mark_unreachable(m.target, SEEK_SKIP_S)
            self._m_ladder = True
        elif end == "crowd":
            if not self._melee_crowd(m):
                self._m_ladder = True   # fix 1, M1: no fresh melee on the same geometry; the ladder's press
        elif end in OFF_ENDS:
            self.melee_off = end
        elif end in BACKOFF_ENDS:
            self._m_backoff[m.target] = MELEE_BACKOFF_TICKS
            self._m_end["backoff"] = MELEE_BACKOFF_TICKS

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
        """A `crowd` end (`m.crowd` {id, d}: another standing zombie within the press's reach, K.STAND_R): that zombie
        is pinned when the Fight may target it and it is nearer than the target (the last progress line's distance,
        else the frame's), so the next melee goes at it; else the pin holds. True when it re-pinned."""
        res = m.crowd or {}
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

    def _melee_holds(self):
        """`busy` for the running melee (the module docstring)."""
        m = self.m
        if m is None or m.action is not self.last or m.resend_due():
            return False
        t = self._target(pin=False)
        if t is None or t[0] != m.target:
            return False
        if self._pin_marked() and m.target not in self._pin_free():
            return False   # fix 1, M2: P27-N's pin-first takes a marked attacker on its own tick, as on the ladder
        fin = self._finishable()
        return not fin or fin[0][0] == m.target

    def _melee_mode(self, cmd):
        """The melee's mode where the ladder's `cmd` is at the dispatch point (the module docstring), else None."""
        if (cmd is None or "melee" not in self.rules or self.melee_off is not None or not self.world.can("melee")
                or self.point_blank or self.only is not None or self.doorway is not None):
            return None
        zid = getattr(cmd, "targetId", None)
        z = self.world.zombies.get(zid) if target_id_ok(zid) and zid == self.target else None
        if z is None or z.get("x") is None or z.get("y") is None:
            return None
        d = zdist(self.world, z)
        if d > MELEE_RELEASE_R or self._m_backoff.get(zid):
            return None
        if self._standing_near(STAND_MIN_R, (zid,)) is not None:
            return None   # fix 1, M1: the Lua's press would take that one (its `crowd`): the ladder's P24-AH rules
        if cmd.TYPE == "aim":
            if "fence_wait" in self.why or self.why.get("leg") not in MELEE_LEGS or d > KEEP_R or on_floor(z):
                return None
        elif cmd.TYPE not in MELEE_SENDS:
            return None
        if cmd.TYPE == "stomp" or on_floor(z):
            return "finish"
        return "shove" if self._hold_bars() else "strike"   # P28-H 3: the arms' pain alone strikes

    def _melee_inputs(self, mode, z):
        """The send's `MeleeInputs` at pin `z` (the module docstring), read afresh."""
        back = self._back_heading(z)
        return MeleeInputs(mode, self.reach_r() or 0.0, back if back is not None else (0.0, 0.0),
                           "floor_finish" in self.rules and not self.floor_swing_barred(),
                           SWING_CLOSE_R if "swing_close" in self.rules else 0.0)

    def _melee_dispatch(self, cmd):
        """The ladder's `cmd`, or at the dispatch point the running maneuver's next command (a new `Melee` where none
        runs at the pin): its re-send, or None while it runs and none is due (nothing sent; it goes on)."""
        mode = self._melee_mode(cmd)
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
        if out is not None:
            self.why["melee"] = {"mode": mode, "pain": arm_pain(self.world)}   # P28-H: the swings under pain read
            if m.resend is not None:
                self.why["melee"]["resend"] = m.resend
        return out
