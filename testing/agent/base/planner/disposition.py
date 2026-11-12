"""The disposition (Plan 37 Task 3; the spec `docs/superpowers/specs/2026-11-12-plan-37-the-disposition-design.md`
§§ 3.1, 3.2, 3.4 and 3.5): the threat branch picks which table of primitives the melee reflex runs in contact, on
events, with a dwell and a hysteresis, and hands it to the running reflex by a re-send; it never decides a step.

`Threat`'s mixin `Disposer`, its state `Survive`'s own (`_init_disposition`, called beside `ThreatGroup`'s), its
constants `policies.py`'s, its switch `DISPOSITION` (`survive.T22_SWITCHES`, on by default; off, the Plan 36 branch:
the leave row, the engagement picker's pull, no `disposition` on the wire).

- The gate (`_disposing`): DISPOSITION on, the melee can go (MELEE, the build announcing `melee`), the character armed
  and not sheltered. Where it reads False the selector holds no disposition and the rows decide as before.
- The read (`_disposition_read`, each tick in `Threat._threat_read` after the held list): the facts (`n_on`, the
  standing zombies, not crawlers, within HOLD_ENTRY_R; `n_hold`, within HOLD_ENTRY_R + RETREAT_HOLD_R; `n_range`,
  within STRING_ENTRY_R; the hold's entry, GROUP_LEAVE_N closing within HOLD_ENTRY_R or there with the nearest within
  KEEP_R; the health; the leader, the nearest standing within GROUP_ENTRY_R, and its own recent speed off the action
  clock's tracks), the condition clocks, the releases' hand-backs, then `select`.
- The table (`select`, `_want`; every threshold a `policies.py` constant):
  `string` whenever STRING_N or more stand within STRING_ENTRY_R, entered at once from none, `hunt` or `hold` (why
  `count`, no dwell: the count's jump is an event); left only to `hold` (GROUP_LEAVE_N or more within HOLD_ENTRY_R)
  or `hunt` once at most GROUP_LEAVE_N standing zombies have been listed, whatever their distance, for
  DISPOSITION_DWELL_S, with the frame's `zombiesSeen` no more than its `zombiesListed` and no line within
  STRING_RUN_HOLD_S reading the melee leaf's `string_state` run (fix 10: a run carries the group off the list), or to
  `break` on
  the health floor, `cornered` (no open heading, the ring closed round the string heading or its open line under
  PULL_ROOM_NEED, for BREAK_CORNERED_S) or `sprinter` (the leader above SPRINTER_V with its gap shrinking on
  SPRINT_READS reads in a row).
  Below STRING_N: `hold` on the hold's entry (three on you), left to `hunt` under GROUP_LEAVE_N within HOLD_ENTRY_R +
  RETREAT_HOLD_R for the dwell; `hunt` otherwise; the hold's entry with a leave door read `break` (`leave`).
  `break`: at most GROUP_LEAVE_N within GROUP_ENTRY_R with the health above FLEE_HEALTH for the dwell, then `hold` or
  `hunt` by the hold's count. Fix 10: a `hunt` that followed a string's exit seeks no zombie while one stands closing
  beyond KEEP_R within STRING_ENTRY_R (`hold_ground`, the stance waits for the leader), logged `hunt_hold`.
  Any: the health at or under FLEE_HEALTH (the reflex's `floor`) `break` (`health`), no dwell. Every other change
  but the string's entry waits until the running disposition has held DISPOSITION_DWELL_S. A change is logged
  `disposition` {from, to, why, dwell} on the threat why of its line only.
- The contract (`_contract`, `Threat._threat_plan`): under `hunt`, `hold` or `string` off a room square no `flee` plan
  goes with a standing zombie within KEEP_R: the Fight at the nearest such zombie in its place (`engage_dispatch`
  {from, target}); a melee that ended `lost` or `too far` in contact re-pins the nearest standing within the
  disposition's reach (`dispatch.FightDispatch._pin_nearest`); the pin is the nearest standing within KEEP_R
  (STRING_RELEASE_R under `string`) whenever its own stands beyond it (`_pin_in_reach`), and no `hunt` or `hold`
  melee runs at a pin beyond MELEE_RELEASE_R (`dispatch.FightDispatch._beyond_release`): the approach goes.
- The care under a fight disposition (`_fight_disposed`): no care supersedes the engaged melee and no care leg goes
  (the care commitment, its yields and Plan 35 fix 2's bleed exemption are not read; the clock's refused-action
  steer is not sent). The rip the clock allows as a start rides the engaged melee with keepMoving (`_engaged_ride`,
  ENGAGED_RIDE; PZA/1.16's `K.RIDES.melee`), logged `care_ride` {under, cmd[, why]} and `care_start` {under, action
  rip, ride "melee"}; the unwear and the bandage the clock allows start after the melee's release (`_care_gate`,
  `care_pending`), logged `care_start` {under, action, released}; a refused action is held, logged `care_hold`
  {why "clock" | "release" | "ride", action}; the Dress sends no stop (`care.Care.no_stop`).
- The row (`_disposition_plan`, `Threat._threat_plan`'s open-ground row in contact: off a room square, a standing
  zombie within GROUP_ENTRY_R): `hunt`, `hold`, `string` are the Fight (`("fight", None)`), whatever the flee reasons
  read; `break` keeps the Fight while the release it asked is pending, then the Flee (`cornered` and `sprinter` reason
  `many`, `leave` reason `leave`), or the rows below for `health` (the health flee, the low fight).
- The inputs (`_disposition_inputs`, `Threat._decide`'s Fight where the engagement picker reads, `Threat._pull_ok`):
  the Fight's `disposition` (the wire's name; a pending `break` sends the one it left), its `withdraw` (`hold` the
  picker's pull, `ThreatGroup._pull` with `hold`; `string` the string heading; `hunt`, fix 1 (the controller's
  ruling), the picker's spread and cone pulls as Plan 36 sent them, never the retreat: the Lua's hunt retreats along
  a given withdraw, Plan 36's pair behaviour) and its `release` (a pending `break`).
- The string heading (`_string_heading`, fix 11): of the headings every STRING_STEP_DEG over the whole circle, the one
  whose first contact (the nearest listed standing zombie within AHEAD_CONE of it, any distance) is farthest, none
  ahead the best, ties to the longest open line over STRING_LOOK_R (`World.open_line`), then to the nearest to the way
  away from the standing centroid within STRING_ENTRY_R; clamped to the room ring as the pull is
  (`ThreatGroup._pull_room`); held STRING_HEADING_HOLD_S unless a zombie enters its cone within STRING_RUN_R, the ring
  closes it, or a new pick's contact is STRING_HEADING_GAIN farther; logged `string_heading` {deg, contact, open,
  room, held}. No sneak posture goes over the engaged melee under a fight disposition (`sneak.SneakGait`).
- The release (`_release_read`): the `break` transition with the melee engaged asks the release (the re-send's
  `release` true); the Fight is kept until the melee ends (its `released` or `floor` hand-back, or any other end), or
  RELEASE_WAIT_S passes; the hand-over logged `release` {asked, waited, end} on the line the Flee takes it.
"""
import math

from agent.base.planner import care as C
from agent.base.planner.clock import _own_speed
from agent.base.planner.crawler import is_crawler
from agent.base.planner.policies import (BREAK_CORNERED_S, DISPOSITION_DWELL_S, FLEE_HEALTH, GROUP_ENTRY_R,
                                         GROUP_LEAVE_N, HOLD_ENTRY_R, KEEP_R, PULL_ROOM_NEED, RELEASE_WAIT_S,
                                         RETREAT_HOLD_R, SPRINT_READS, SPRINTER_V, STRING_ENTRY_R, STRING_LOOK_R,
                                         STRING_HEADING_GAIN, STRING_HEADING_HOLD_S, STRING_N, STRING_RELEASE_R,
                                         STRING_RUN_HOLD_S, STRING_RUN_R, STRING_STEP_DEG, AHEAD_CONE, blocked,
                                         on_floor, target_id_ok, zdist)
from agent.base.pza1 import Rip
from agent.base.world import me_xy

__all__ = ["Disposer", "DISPOSITIONS", "WIRE", "BREAK_FLEE"]

DISPOSITIONS = ("hunt", "hold", "string", "break")   # the selector's names (`break` is the Flee's, never on the wire)
WIRE = ("hunt", "hold", "string")                     # the melee's `disposition` enum (pza1.MELEE_DISPOSITIONS)
BREAK_FLEE = {"cornered": "many", "sprinter": "many", "leave": "leave"}   # a break's reason -> the Flee's reason
                                                                          # (`health` decided by the rows below)


def _heading(deg):
    r = math.radians(deg)
    return (math.cos(r), math.sin(r))


class Disposer:
    """The disposition selector (the module docstring): `Threat`'s mixin."""

    DISPOSITION = True   # Plan 37 Task 3 (survive.T22_SWITCHES): the selector; off, the Plan 36 branch
    ENGAGED_RIDE = True  # fix 3 (survive.T22_SWITCHES), on again at fix 7 (the controller's ruling): under a fight
                         # disposition the clock-allowed rip rides the engaged melee (`_engaged_ride`, the Lua's
                         # K.RIDES.melee = {rip}); off, the rip starts through the release as the unwear and the
                         # bandage do (`_care_gate`, fix 6)

    def _init_disposition(self):
        self.disposition = None          # the running disposition (DISPOSITIONS), else None
        self.disposition_since = None    # the wall it was entered at
        self.disposition_why = None      # this tick: the change {from, to, why, dwell}, else None
        self.break_reason = None         # the running `break`'s reason (health | cornered | sprinter | leave)
        self.release_pending = None      # the running `break`'s release {asked, from, end, waited}, else None
        self.release_why = None          # this tick: the hand-over {asked, waited, end}, else None
        self.string_why = None           # this tick: the string heading {deg, open, room}, else None
        self._string_read = None         # this tick: `_string_heading`'s (vector or None, why), else None
        self._disp_facts = None          # this tick: the facts `select` read
        self._disp_since = {}            # condition name -> the wall it first read true (the condition clocks)
        self._sprint = (None, None, 0)   # (the leader's id, its tiles on the last read, the shrinking reads in a row)
        self.care_ride = None            # fix 3: this tick's ride over the engaged melee {under, cmd}, else None
        self._held_heading = None        # fix 11: the held string heading {deg, at}, else None
        self._run_at = None              # fix 10: the wall of the last line whose melee leaf read string_state run
        self._after_string = False       # fix 10: the running `hunt` follows a string's exit (the hunt's hold reads it)
        self.hunt_hold = None            # fix 10: this tick's hunt hold {why "coming", target, d}, else None
        self.care_pending = None         # fix 6: the care start's release {asked, kind, end, waited}, else None
        self.care_start = None           # fix 6: this tick's care start {under, action, released}, else None
        self.care_hold = None            # fix 6: this tick's care held under the disposition {why, action}, else None

    # ---------------------------------------------------------------------------------------------------- the gate
    def _disposing(self):
        """The selector runs: DISPOSITION on, the melee can go (MELEE on, the build announcing `melee`), armed, not
        sheltered."""
        return (self.DISPOSITION and self.MELEE and self.world.can("melee") and self._armed()
                and not self.sheltered)

    def _fight_disposed(self):
        """Fix 6: a fight disposition holds (`hunt`, `hold` or `string`, the selector running): no care supersedes the
        engaged melee and no care leg goes (`_care_gate`)."""
        return self.disposition in WIRE and self._disposing()

    def _disposition_end(self):
        """The threat ended (no held zombie) or the gate closed: no disposition, its clocks cleared."""
        self.disposition, self.disposition_since, self.break_reason, self.release_pending = None, None, None, None
        self.care_pending = None
        self._disp_since, self._sprint = {}, (None, None, 0)
        self._run_at, self._after_string, self._held_heading = None, False, None

    # ---------------------------------------------------------------------------------------------------- the read
    def _disposition_read(self, held):
        """The tick's facts, the condition clocks and the release's hand-back, then `select` (the module docstring);
        no disposition where the gate reads False or nothing is held."""
        self.disposition_why, self.release_why, self.string_why, self._string_read = None, None, None, None
        self._disp_facts, self.care_start, self.care_hold = None, None, None
        if not held or not self._disposing():
            self._disposition_end()
            return
        self._disp_facts = self._facts()
        self._release_read()
        self._care_release_read()
        self.select(held)
        if self.disposition not in WIRE:
            self.care_pending = None

    def _facts(self):
        standing = [(zid, z, d) for zid, z, d in self._group_standing(STRING_ENTRY_R) if not is_crawler(z)]
        near = [e for e in standing if e[2] <= GROUP_ENTRY_R]
        on = [e for e in standing if e[2] <= HOLD_ENTRY_R]   # fix 8: the hold's count, "three on you"
        closing = [e for e in self._group_closing if not is_crawler(e[1]) and e[2] <= HOLD_ENTRY_R]
        entry = len(closing) >= GROUP_LEAVE_N or (len(on) >= GROUP_LEAVE_N and on[0][2] <= KEEP_R)
        leader = near[0] if near else None
        speed = None
        clock = getattr(self, "action_clock", None)
        if leader is not None and clock is not None:
            speed = _own_speed(clock.tracks.get(leader[0]))
        f = self.fight
        m = f.m if f is not None and f._engaged() else None
        if m is not None and ((m._progress.get("work") or {}).get("string_state")) == "run":
            self._run_at = self.clock()   # fix 10: the run just opened the gap; the group is coming
        me = self.world.me or {}
        seen, listed = me.get("zombiesSeen"), me.get("zombiesListed")
        beyond = (isinstance(seen, int) and isinstance(listed, int) and not isinstance(seen, bool)
                  and seen > listed)   # fix 10: zombies the frame does not list (beyond its sense radius)
        dead = blocked(self.dead, self.clock())
        n_list = sum(1 for zid, z in self.world.zombies.items()   # fix 10: every listed standing zombie
                     if not on_floor(z) and not is_crawler(z) and z.get("x") is not None and zid not in dead)
        return {"n_list": n_list, "beyond": beyond, "n": self.group_n, "n_on": len(on), "entry": entry, "health": self._health(), "leader": leader,
                "speed": speed, "n_range": len(standing),
                "n_hold": sum(1 for e in standing if e[2] <= HOLD_ENTRY_R + RETREAT_HOLD_R)}

    def _run_recent(self):
        """Fix 10: a line within STRING_RUN_HOLD_S read the engaged melee's leaf `string_state` run."""
        return self._run_at is not None and self.clock() - self._run_at < STRING_RUN_HOLD_S

    def _for(self, key, cond):
        """Seconds condition `key` has read true without a break (0.0 when false, the clock cleared)."""
        if not cond:
            self._disp_since.pop(key, None)
            return 0.0
        return self.clock() - self._disp_since.setdefault(key, self.clock())

    def _clocks(self, f):
        """The condition clocks, read every tick whatever the disposition (so a condition's time is its own)."""
        lead, speed = f["leader"], f["speed"]
        zid, d0, k = self._sprint
        if lead is None:
            self._sprint = (None, None, 0)
        else:
            shrink = lead[0] == zid and d0 is not None and lead[2] < d0 and speed is not None and speed > SPRINTER_V
            self._sprint = (lead[0], lead[2], k + 1 if shrink else 0)
        cornered = False
        if self.disposition == "string":
            self._string_read = self._string_heading()
            why = self._string_read[1]
            cornered = why is None or why.get("room") == "closed" or why.get("open", 0.0) < PULL_ROOM_NEED
        return {"hold_low": self._for("hold_low", f["n_hold"] < GROUP_LEAVE_N),
                "string_low": self._for("string_low", f["n_list"] <= GROUP_LEAVE_N and not f["beyond"]
                                        and not self._run_recent()),   # fix 10: the whole list, never after a run
                "cornered": self._for("cornered", cornered),
                "calm": self._for("calm", f["n"] <= GROUP_LEAVE_N and f["health"] > FLEE_HEALTH)}

    # ---------------------------------------------------------------------------------------------------- the table
    def select(self, held):
        """The disposition for this tick by the table (the module docstring): a change only after the running one has
        held DISPOSITION_DWELL_S, the health floor's excepted, logged `disposition` {from, to, why, dwell}."""
        f = self._disp_facts if self._disp_facts is not None else self._facts()
        t = self._clocks(f)
        cur = self.disposition
        want, why = self._want(cur, f, t)
        if want is None or want == cur:
            return cur
        now = self.clock()
        dwell = None if cur is None else now - self.disposition_since
        jump = want == "string"   # the count's jump to STRING_N within STRING_ENTRY_R: an event, no dwell
        if dwell is not None and why != "health" and not jump and dwell < DISPOSITION_DWELL_S:
            return cur
        self._change(cur, want, why, dwell, now)
        return want

    def _want(self, cur, f, t):
        """`(disposition, why)` the table reads this tick, else `(None, None)` (no change wanted)."""
        if f["health"] <= FLEE_HEALTH:
            return (None, None) if cur == "break" else ("break", "health")
        below = "hold" if f["n_on"] >= GROUP_LEAVE_N else "hunt"   # fix 8: the hold's count below STRING_N
        if cur == "break":
            return (below, "calm") if t["calm"] >= DISPOSITION_DWELL_S else (None, None)
        if cur == "string":
            if t["cornered"] >= BREAK_CORNERED_S:
                return "break", "cornered"
            if self._sprint[2] >= SPRINT_READS:
                return "break", "sprinter"
            return (below, "count") if t["string_low"] >= DISPOSITION_DWELL_S else (None, None)
        if f["n_range"] >= STRING_N:
            return "string", "count"
        if f["entry"] and self._leave_door_open():
            return "break", "leave"
        if cur == "hold":
            return ("hunt", "count") if t["hold_low"] >= DISPOSITION_DWELL_S else (None, None)
        if f["entry"]:
            return "hold", "entry"
        return (None, None) if cur == "hunt" else ("hunt", "count")

    def _leave_door_open(self):
        """The leave's door reads (`ThreatGroup._leave_door`: a known door within LEAVE_DOOR_R the Flee reads `ok`, the
        race and the one-exit refusals applied)."""
        door, _ = self._leave_door(self.flee, [z for _, z, _ in self._group_standing(GROUP_ENTRY_R)])
        return door is not None

    def _change(self, cur, want, why, dwell, now):
        self.disposition_why = {"from": cur, "to": want, "why": why,
                                "dwell": None if dwell is None else round(dwell, 3)}
        self.disposition, self.disposition_since = want, now
        self._after_string = cur == "string" and want == "hunt"   # fix 10: the hunt's hold after a string's exit
        self._held_heading = None   # fix 11: a new disposition reads its heading afresh
        if want != "break":
            self.break_reason, self.release_pending = None, None
            return
        self.break_reason = why
        f = self.fight
        engaged = f is not None and f._engaged()
        self.release_pending = ({"asked": now, "from": cur if cur in WIRE else "hunt", "end": None}
                                if engaged else None)

    # ---------------------------------------------------------------------------------------------------- the release
    def _release_read(self):
        """A pending release's end, read before the table: the melee's end this tick (its `released` or `floor`
        hand-back, or any other end), the melee gone, or RELEASE_WAIT_S since it was asked (`bound`)."""
        rp = self.release_pending
        if rp is None or rp["end"] is not None:
            return
        f = self.fight
        end = f._m_end if f is not None else None
        now = self.clock()
        if end is not None:
            rp["end"] = end.get("why") or end.get("end")
        elif f is None or f.m is None or not f.m.running():
            rp["end"] = "gone"
        elif now - rp["asked"] >= RELEASE_WAIT_S:
            rp["end"] = "bound"
        if rp["end"] is not None:
            rp["waited"] = round(now - rp["asked"], 3)

    def _care_release_read(self):
        """Fix 6: a care start's pending release ends as the break's does (`_release_read`'s reads)."""
        cp = self.care_pending
        if cp is None or cp["end"] is not None:
            return
        f = self.fight
        end = f._m_end if f is not None else None
        now = self.clock()
        if end is not None:
            cp["end"] = end.get("why") or end.get("end")
        elif f is None or f.m is None or not f.m.running():
            cp["end"] = "gone"
        elif now - cp["asked"] >= RELEASE_WAIT_S:
            cp["end"] = "bound"
        if cp["end"] is not None:
            cp["waited"] = round(now - cp["asked"], 3)

    def _care_gate(self):
        """Fix 6 (the horde8 trial `x_trial-ladder-20261112-070655`, decision lines 41 to 63: Plan 35 fix 2's bleed yield
        took the care chain over the string, the clock's gain-distance steer, a stop, an unwear, a rip and four refused
        bandages with seven to ten standing within 6 tiles, the character caught standing): under a fight disposition
        True when the threat branch yields this tick to the care's action, else False. The care's next timed action
        (`care.Care.next_kind`: unwear, rip or bandage) starts only when the clock allows it as a start, no ride
        exemption (`ActionClock.allows`), else held, logged `care_hold` {why "clock", action}; allowed with the melee
        engaged, the melee is released first (`care_pending`: the re-send's `release`, `_disposition_inputs`), the
        yield on the line its end reads (`released`, `floor`, any end, or RELEASE_WAIT_S), logged `care_start` {under,
        action, released}; allowed with no melee running, the yield at once (`released` null). The Dress sends no stop
        (`care.Care.no_stop`)."""
        care = self.care
        if not self.world.can("bandage") or (care.bleeding_n() <= 0 and care.dressing() is None):
            self.care_pending = None
            return False
        kind = care.next_kind()
        if kind is None:
            return False
        f = self.fight
        if kind == "rip" and self.ENGAGED_RIDE and f is not None and f._engaged():
            refused = (self.care_ride or {}).get("why") == "clock"   # fix 7: the rip rides the melee (`_engaged_ride`)
            self.care_hold = {"why": "clock" if refused else "ride", "action": kind}
            return False
        if self._clock_on():
            ck = self.action_clock
            allowed = ck.allows(kind)
            if self.clock_now is None:   # the ride's own read (fix 4) stands on its line
                self.clock_now = self._clock_why(kind, start=True, **({} if allowed else {"refused": True}))
        else:
            allowed = not self._group_standing(KEEP_R)
        if not allowed:
            self.care_pending, self.care_hold = None, {"why": "clock", "action": kind}
            return False
        f = self.fight
        if f is not None and f._engaged():
            if self.care_pending is None:
                self.care_pending = {"asked": self.clock(), "kind": kind, "end": None}
            if self.care_pending["end"] is None:
                self.care_hold = {"why": "release", "action": kind}
                return False
        cp, self.care_pending = self.care_pending, None
        self.care_start = {"under": self.disposition, "action": kind, "released": None if cp is None else cp["end"]}
        care.no_stop = True
        return True

    # ---------------------------------------------------------------------------------------------------- the row
    def _disposition_plan(self, inside):
        """`Threat._threat_plan`'s row in contact (the module docstring): `(kind, reason)`, else None (the rows below
        decide)."""
        d = self.disposition
        if d is None or inside or not self._disposing():
            return None
        if self.group_n < 1 and d not in ("break", "string"):   # fix 2: the string runs before contact
            return None
        if d != "break":
            if not self._reachable_held() and not self._contact_lift():
                return None   # nothing the Fight may reach (Plan 35 fix 8b's lift read first): the rows below
            self.cornered, self._corner_fight, self.leave = None, None, None
            return "fight", None
        self.cornered, self._corner_fight, self.leave = None, None, None
        rp = self.release_pending
        if rp is not None and rp["end"] is None:
            return "fight", None   # the release asked: the reflex hands back at its first safe frame
        if rp is not None and not rp.get("logged"):
            rp["logged"] = True
            self.release_why = {"asked": round(rp["asked"], 3), "waited": rp["waited"], "end": rp["end"]}
        if self.break_reason not in BREAK_FLEE:
            return None   # `health`: the health flee or the low fight, the rows below
        return "flee", BREAK_FLEE[self.break_reason]

    def _disposition_inputs(self, policy, kind, door):
        """The Fight's `disposition`, `withdraw` and `release` this tick (the module docstring; fix 6: the care start's
    release too); where the selector
        holds none, the engagement picker's pull as Plan 36 sent it."""
        policy.disposition, policy.release = None, False
        if not (self._pull_ok(kind, door) and policy._melee_on()):
            policy.withdraw = None
            return
        d = self.disposition if self._disposing() else None
        if d is None:
            policy.withdraw = self._pull(policy)
            return
        if d == "break":
            rp = self.release_pending
            if rp is None or rp["end"] is not None:
                policy.withdraw = None   # the health floor's low fight: no disposition, no release
                return
            policy.release, d = True, rp["from"]
        if self.care_pending is not None and self.care_pending["end"] is None:
            policy.release = True   # fix 6: the care's start asked the hand-back
        policy.disposition = d
        self._pin_in_reach(policy, d)
        if d == "hold":
            policy.withdraw = self._pull(policy, "hold")
        elif d == "string":
            vec, why = self._string_read if self._string_read is not None else self._string_heading()
            self.string_why, policy.withdraw = why, vec
        else:
            policy.withdraw = self._pull(policy, "hunt")   # fix 1: Plan 36's spread and cone pulls, no retreat
            self._hunt_hold(policy)

    # ---------------------------------------------------------------------------------------------------- the contract
    def _contract(self, plan, inside):
        """Fix 3 (the horde8 trial `x_trial-ladder-20261112-061307`, decision lines 153 and 157: the drag guard's `many`
        steer in contact between two melees): under `hunt`, `hold` or `string` off a room square, a `flee` plan with a
        standing zombie (not a crawler) within KEEP_R is the Fight at the nearest such zombie instead (its mark lifted,
        pinned as the point-blank fight is, logged `engage_dispatch` {from: the flee's reason, target}); any other plan
        unchanged. No non-melee command goes in contact under a fight disposition."""
        if (plan is None or plan[0] != "flee" or inside or self.disposition not in WIRE
                or not self._disposing()):
            return plan
        near = [(d, repr(zid), zid) for zid, z, d in self._group_standing(KEEP_R) if not is_crawler(z)
                and target_id_ok(zid)]
        if not near:
            return plan
        d, _, zid = min(near)
        self.unreachable.pop(zid, None)
        self.engage_dispatch = {"from": plan[1] or "flee", "target": zid}
        self.point_blank_fight = {"target": zid, "dist": d, "over": plan[1]}
        self.group_steer, self.cornered, self._corner_fight = None, None, None
        if self.mode == "fight" and self.fight is not None:
            self.fight.target = zid
        return "fight", None

    # ---------------------------------------------------------------------------------------------------- the ride
    def _engaged_ride(self):
        """Fix 3, as fixes 4 and 7 left it (the controller's ruling: the clock-allowed rip rides the melee; Task 2 fix 2's
        `K.RIDES.melee = {rip}`, the walk going on at a walk and the press deferred while the rip is queued):
        `(care, Rip)` when a part bleeds under a fight disposition (`hunt`, `hold` or `string`) with the melee engaged,
        no dressing held and an unworn cotton garment held (`care.rip_pick`): the rip with keepMoving riding the melee,
        once the clock allows it as a start (fix 4: no ride exemption), logged `care_ride` {under, cmd rip}, `care_start`
        {under, action rip, ride "melee"} and `clock` {action rip, ride "melee"}; refused, `care_ride` {why "clock"};
        nothing unworn to tear, `care_ride` {why "worn" | "nothing"}. A dressing held is no ride: the bandage cannot ride
        the melee, so it starts through the release (`_care_gate`, fix 6), as the unwear does. Else None."""
        self.care_ride = None
        if not (self.ENGAGED_RIDE and self.disposition in WIRE and self._disposing()):
            return None
        f, care = self.fight, self.care
        if f is None or not f._engaged() or care.bleeding_n() <= 0 or self.night.inside():
            return None
        if self.actions.current is not f.m.action:
            return None   # a ride already rides it
        if C.dressing_pick(care._items(), 0.0, dirty_ok=True) is not None:
            return None   # the bandage: the release, then the action (`_care_gate`)
        iid = C.rip_pick(self.world, care.held_out) if self.world.can("rip") else None
        cmd, why = (Rip(iid, keepMoving=True) if iid is not None else None), None
        if cmd is not None and self._clock_on():   # fix 4: the riding rip asks the clock as a start
            allowed = self.action_clock.allows("rip")
            self.clock_now = self._clock_why("rip", ride="melee", **({} if allowed else {"refused": True}))
            if not allowed:
                cmd, why = None, "clock"
        elif cmd is None:   # nothing unworn to tear: the unwear stops on a walk, so it starts through the release
            worn = any(it.get("rip") == "cotton" and it.get("worn") is True for it in self.world.inventory.values())
            why = "worn" if worn else "nothing"
        self.care_ride = {"under": self.disposition, "cmd": None if cmd is None else cmd.TYPE}
        if why is not None:
            self.care_ride["why"] = why
        if cmd is None:
            return None
        self.care_start = {"under": self.disposition, "action": "rip", "ride": "melee"}
        return care, cmd

    def _hunt_hold(self, policy):
        """Fix 10 (the horde10 trial `x_trial-ladder-20261112-081859`, decision line 15: after the string's exit `hunt`
        walked back toward the group): under a `hunt` that followed a string's exit, while a standing zombie (not a
        crawler) stands beyond KEEP_R within STRING_ENTRY_R closing (the leader coming), the Fight seeks none
        (`hold_ground`: the stance waits for it, an aim leg, no walk), logged `hunt_hold` {why "coming", target, d}."""
        self.hunt_hold = None
        if not self._after_string:
            return
        coming = [(d, repr(zid), zid) for zid, z, d in self._group_coming
                  if not is_crawler(z) and KEEP_R < d <= STRING_ENTRY_R]
        if not coming:
            return
        d, _, zid = min(coming)
        policy.hold_ground = True
        self.hunt_hold = {"why": "coming", "target": zid, "d": round(d, 3)}

    def _pin_in_reach(self, policy, d):
        """Fix 8 (the same trial, lines 24 and 25: a `hold` melee re-sent at a pin 6.6 tiles off ended `too far` and an
        aim went): the Fight's pin under a fight disposition is the nearest standing zombie (not a crawler, one the Fight
        may target) within the disposition's reach, KEEP_R under `hunt` and `hold`, STRING_RELEASE_R under `string`,
        whenever its pin stands beyond it; with none within it the pin stays and the Fight's approach goes (the
        dispatch sends no `hunt` or `hold` melee beyond MELEE_RELEASE_R: `dispatch.FightDispatch._melee_holds`)."""
        r = STRING_RELEASE_R if d == "string" else KEEP_R
        t = self.world.zombies.get(policy.target) if policy.target is not None else None
        if t is not None and t.get("x") is not None and zdist(self.world, t) <= r:
            return
        blocked = policy.blocked()
        near = [(dd, repr(zid), zid) for zid, z, dd in self._group_standing(r) if not is_crawler(z)
                and target_id_ok(zid) and zid not in blocked]
        if near:
            policy.target, policy.repositioned = min(near)[2], False

    # ---------------------------------------------------------------------------------------------------- the string
    def _contact(self, deg, standing):
        """Fix 11: the tiles to the first contact along heading `deg`: the nearest of `standing` ((zombie, tiles) of every
        listed standing zombie) whose bearing lies within AHEAD_CONE of it, None with none (no contact ahead)."""
        p = me_xy(self.world)
        best = None
        for z, d in standing:
            b = math.degrees(math.atan2(z["y"] - p[1], z["x"] - p[0]))
            if abs((b - deg + 180.0) % 360.0 - 180.0) <= AHEAD_CONE and (best is None or d < best):
                best = d
        return best

    def _string_heading(self):
        """`(unit vector or None, why)`: the string heading, why {deg, contact, open, room, held} (`contact` the first
        contact's tiles, None with none ahead; `room` the ring's clamped degrees, None with no ring, "closed" with no
        open ring heading: then no vector); `(None, None)` with no standing zombie within STRING_ENTRY_R.
        Fix 11 (the town trial `x_trial-ladder-20261112-082228`: the heading flipped eight times in ten seconds and
        pointed into one of three groups; Angus: sprint away to create distance, never into them): the candidates are
        the headings every STRING_STEP_DEG over the whole circle, each scored by its first contact (`_contact`, every
        listed standing zombie, any distance): the farthest wins (none ahead the best), ties to the longest open line
        over STRING_LOOK_R (`World.open_line`), then to the nearest to the way away from the standing centroid within
        STRING_ENTRY_R; then the ring clamp (`ThreatGroup._pull_room`). The pick is held STRING_HEADING_HOLD_S: a new
        read within the hold replaces it only when a standing zombie stands inside the held heading's cone within
        STRING_RUN_R, the ring reads it closed, or the new pick's first contact is STRING_HEADING_GAIN farther."""
        p = me_xy(self.world)
        group = [z for _, z, _ in self._group_standing(STRING_ENTRY_R) if not is_crawler(z)]   # the string's group
        if not group:
            return None, None
        dead = blocked(self.dead, self.clock())
        standing = [(z, zdist(self.world, z)) for zid, z in self.world.zombies.items()
                    if zid not in dead and not on_floor(z) and not is_crawler(z) and z.get("x") is not None]
        cx = sum(z["x"] for z in group) / len(group)
        cy = sum(z["y"] for z in group) / len(group)
        dx, dy = p[0] - cx, p[1] - cy
        away = 0.0 if dx == 0.0 and dy == 0.0 else math.degrees(math.atan2(dy, dx)) % 360.0
        best = None
        for k in range(int(round(360.0 / STRING_STEP_DEG))):
            deg = k * STRING_STEP_DEG
            c = self._contact(deg, standing)
            off = abs((deg - away + 180.0) % 360.0 - 180.0)
            rank = (-(math.inf if c is None else c), -self.world.open_line(deg, STRING_LOOK_R), off, deg)
            if best is None or rank < best:
                best = rank
        deg, contact = best[3], self._contact(best[3], standing)
        held = self._held_heading
        if held is not None and self.clock() - held["at"] < STRING_HEADING_HOLD_S:
            hc = self._contact(held["deg"], standing)
            entered = hc is not None and hc <= STRING_RUN_R
            closed = self._pull_room(held["deg"]) == "closed"
            gain = (math.inf if contact is None else contact) - (math.inf if hc is None else hc)
            if not (entered or closed or gain >= STRING_HEADING_GAIN):
                deg, contact = held["deg"], hc
                held = True
            else:
                held = None
        else:
            held = None
        if held is None:
            self._held_heading = {"deg": deg, "at": self.clock()}
        open_ = self.world.open_line(deg, STRING_LOOK_R)
        room = self._pull_room(deg)
        why = {"deg": deg, "contact": None if contact is None else round(contact, 3), "open": open_, "room": room,
               "held": held is True}
        if room == "closed":
            return None, why
        return _heading(deg if room is None else room), why
