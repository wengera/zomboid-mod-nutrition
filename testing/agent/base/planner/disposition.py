"""The disposition (Plan 37 Task 3; the spec `docs/superpowers/specs/2026-11-12-plan-37-the-disposition-design.md`
§§ 3.1, 3.2, 3.4 and 3.5): the threat branch picks which table of primitives the melee reflex runs in contact, on
events, with a dwell and a hysteresis, and hands it to the running reflex by a re-send; it never decides a step.

`Threat`'s mixin `Disposer`, its state `Survive`'s own (`_init_disposition`, called beside `ThreatGroup`'s), its
constants `policies.py`'s, its switch `DISPOSITION` (`survive.T22_SWITCHES`, on by default; off, the Plan 36 branch:
the leave row, the engagement picker's pull, no `disposition` on the wire).

- The gate (`_disposing`): DISPOSITION on, the melee can go (MELEE, the build announcing `melee`), the character armed
  and not sheltered. Where it reads False the selector holds no disposition and the rows decide as before.
- The read (`_disposition_read`, each tick in `Threat._threat_read` after the held list): the facts (the standing count
  within GROUP_ENTRY_R, `group_n`, and within GROUP_ENTRY_R + RETREAT_HOLD_R; the leave's entry, GROUP_LEAVE_N or more
  standing closing within GROUP_ENTRY_R or on the character with the nearest within KEEP_R; the health; the room ring;
  the engaged melee's last work leaf, `pinned`; the leader, the nearest standing, its own recent speed off the action
  clock's tracks, `clock.ActionClock`), the condition clocks, the release's hand-back, then `select`.
- The table (`select`, `_want`; every threshold a `policies.py` constant):
  from none: STRING_N or more standing `string`; the leave's entry with a leave door `break` (`leave`); the entry
  `hold`; else `hunt`.
  `hunt`: STRING_N `string`; the entry with a leave door `break` `leave`; the entry `hold`.
  `hold`: STRING_N `string`; the leaf `pinned` for STRING_PIN_S with the count not falling `string` (`pinned`); the
  ring reading the withdraw heading and both its neighbours under PULL_ROOM_NEED `string` (`walled`); the leave's entry
  with a leave door `break` `leave`; under GROUP_LEAVE_N standing within GROUP_ENTRY_R + RETREAT_HOLD_R for
  DISPOSITION_DWELL_S `hunt`.
  `string`: no open heading (the ring closed round the string heading, or its open line under PULL_ROOM_NEED) for
  BREAK_CORNERED_S `break` (`cornered`); the leader above STRING_RUN_V with its gap shrinking on SPRINT_READS reads in a
  row `break` (`sprinter`); at most GROUP_LEAVE_N standing within GROUP_ENTRY_R for DISPOSITION_DWELL_S `hold`.
  `break`: at most GROUP_LEAVE_N standing with the health above FLEE_HEALTH for DISPOSITION_DWELL_S, `hold` at
  GROUP_LEAVE_N, else `hunt`.
  Any: the health at or under FLEE_HEALTH (the reflex's `floor`) `break` (`health`), the one change the dwell never
  holds. Every other change waits until the running disposition has held DISPOSITION_DWELL_S. A change is logged
  `disposition` {from, to, why, dwell} on the threat why of its line only.
  Fix 2 (the string probe `x_trial-ladder-20261112-055128`: the string entered after the dwell, inside the clump, and
  the character dragged down 21 s in): the string's count entry also reads the standing zombies closing within
  STRING_ENTRY_R (`coming`, the group read coming), and either count's jump to STRING_N takes no dwell; no string is
  entered with the nearest standing inside STRING_MIN_GAP (five there go to `hold`, why `clump`); a running string
  whose nearest stays inside STRING_MIN_GAP, or whose leaf reads `pinned`, for STRING_PIN_S goes to `hold` (`clump`);
  its exit to `hold` on the count reads the coming group too (at most GROUP_LEAVE_N within GROUP_ENTRY_R and under
  STRING_N coming, for DISPOSITION_DWELL_S);
  the sprinter's break reads SPRINTER_V (STRING_RUN_V, now 1.0, is the walk's run latch); under `string` the melee is
  sent at a pin within STRING_RELEASE_R (`dispatch.FightDispatch._release_r`, `_contact_r`) and the row answers with
  nobody yet within GROUP_ENTRY_R, the heading read off the standing within STRING_ENTRY_R.
  Fix 3 (the horde8 trial `x_trial-ladder-20261112-061307`: six game minutes of `hold` inside a clump of four to
  seven, the string barred by STRING_MIN_GAP; two `many` steers in contact; a scratch bled 98 to 42 undressed under
  the engaged melee): `hold` with STRING_N within GROUP_ENTRY_R for STRING_PIN_S (`crowd`), or the leaf `pinned` for
  STRING_PIN_S (`pinned`), enters `string` whatever the gap (STRING_MIN_GAP bars only the entries at range), and such
  a string takes no clump exit; the contract (`_contract`, `Threat._threat_plan`): under `hunt`, `hold` or `string`
  off a room square no `flee` plan goes with a standing zombie within KEEP_R, the Fight at the nearest such in its
  place (`engage_dispatch` {from, target}), and a melee that ended `lost` or `too far` in contact re-pins the nearest
  (`dispatch.FightDispatch._pin_nearest`); the ride (`_engaged_ride`, ENGAGED_RIDE): a bleeding part under `hold` or
  `string` with the melee engaged sends the rip of a held unworn cotton garment with keepMoving over the melee (the
  side slot, `policies.rides_on` reading the melee as its leg, no melee re-send and no clock hold while it rides), or
  under GROUP_LEAVE_N the riding bandage of a part above the legs, logged `care_ride` {under, cmd[, why]} (why `worn`,
  `nothing`, `stop` or `count` when nothing goes). Fix 4 (Task 2 Lua fix 2: while a rip rides the melee the reflex
  presses nothing, `SwipeStatePlayer.enter` stopping the action queue, and the string's run is suppressed): the
  riding rip asks the action clock as a start, with no ride exemption: it goes only when the smallest time to contact
  exceeds the rip's duration plus ACTION_MARGIN_S (`ActionClock.allows`), logged `clock` {action rip, ride "melee"[,
  refused true]}, else `care_ride` {why "clock"}.
- The row (`_disposition_plan`, `Threat._threat_plan`'s open-ground row in contact: off a room square, a standing
  zombie within GROUP_ENTRY_R): `hunt`, `hold`, `string` are the Fight (`("fight", None)`), whatever the flee reasons
  read; `break` keeps the Fight while the release it asked is pending, then the Flee (`cornered` and `sprinter` reason
  `many`, `leave` reason `leave`), or the rows below for `health` (the health flee, the low fight).
- The inputs (`_disposition_inputs`, `Threat._decide`'s Fight where the engagement picker reads, `Threat._pull_ok`):
  the Fight's `disposition` (the wire's name; a pending `break` sends the one it left), its `withdraw` (`hold` the
  picker's pull, `ThreatGroup._pull` with `hold`; `string` the string heading; `hunt`, fix 1 (the controller's
  ruling), the picker's spread and cone pulls as Plan 36 sent them, never the retreat: the Lua's hunt retreats along
  a given withdraw, Plan 36's pair behaviour) and its `release` (a pending `break`).
- The string heading (`_string_heading`): of the headings every STRING_STEP_DEG within STRING_TURN_DEG either side of
  the way away from the standing centroid, the longest open line over STRING_LOOK_R (`World.open_line`), ties to the
  nearest straight away, then clamped to the room ring as the pull is (`ThreatGroup._pull_room`); logged
  `string_heading` {deg, open, room}.
- The release (`_release_read`): the `break` transition with the melee engaged asks the release (the re-send's
  `release` true); the Fight is kept until the melee ends (its `released` or `floor` hand-back, or any other end), or
  RELEASE_WAIT_S passes; the hand-over logged `release` {asked, waited, end} on the line the Flee takes it.
"""
import math

from agent.base.planner import care as C
from agent.base.planner.clock import _own_speed
from agent.base.planner.crawler import is_crawler
from agent.base.planner.policies import (BREAK_CORNERED_S, DISPOSITION_DWELL_S, FLEE_HEALTH, GROUP_ENTRY_R,
                                         GROUP_LEAVE_N, KEEP_R, PULL_ROOM_NEED, RELEASE_WAIT_S, RETREAT_HOLD_R,
                                         SPRINT_READS, SPRINTER_V, STRING_ENTRY_R, STRING_LOOK_R, STRING_MIN_GAP,
                                         STRING_N, STRING_PIN_S, STRING_STEP_DEG, STRING_TURN_DEG, target_id_ok)
from agent.base.pza1 import Rip
from agent.base.world import ROOM_HEADINGS, ROOM_STEP_DEG, me_xy

__all__ = ["Disposer", "DISPOSITIONS", "WIRE", "BREAK_FLEE"]

DISPOSITIONS = ("hunt", "hold", "string", "break")   # the selector's names (`break` is the Flee's, never on the wire)
WIRE = ("hunt", "hold", "string")                     # the melee's `disposition` enum (pza1.MELEE_DISPOSITIONS)
CLUMP_ENTRIES = ("crowd", "pinned")   # fix 3: the string's entries inside the clump, which take no clump exit
BREAK_FLEE = {"cornered": "many", "sprinter": "many", "leave": "leave"}   # a break's reason -> the Flee's reason
                                                                          # (`health` decided by the rows below)


def _heading(deg):
    r = math.radians(deg)
    return (math.cos(r), math.sin(r))


class Disposer:
    """The disposition selector (the module docstring): `Threat`'s mixin."""

    DISPOSITION = True   # Plan 37 Task 3 (survive.T22_SWITCHES): the selector; off, the Plan 36 branch
    ENGAGED_RIDE = True  # fix 3 (survive.T22_SWITCHES): a bleeding part under `hold` or `string` rides the engaged
                         # melee (`_engaged_ride`); off, the care waits for the clock's stop as before. Needs the
                         # Lua's side slot to admit the melee as its leg (PZAgent_Tend.lua's K.RIDES)

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
        self._pin_n = None               # the standing count when the leaf first read `pinned`, else None
        self._sprint = (None, None, 0)   # (the leader's id, its tiles on the last read, the shrinking reads in a row)
        self._hold_heading = None        # the hold's last withdraw heading, degrees, else None
        self._string_from = None         # fix 3: the running string's entry why (CLUMP_ENTRIES keep no clump exit)
        self.care_ride = None            # fix 3: this tick's ride over the engaged melee {under, cmd}, else None

    # ---------------------------------------------------------------------------------------------------- the gate
    def _disposing(self):
        """The selector runs: DISPOSITION on, the melee can go (MELEE on, the build announcing `melee`), armed, not
        sheltered."""
        return (self.DISPOSITION and self.MELEE and self.world.can("melee") and self._armed()
                and not self.sheltered)

    def _disposition_end(self):
        """The threat ended (no held zombie) or the gate closed: no disposition, its clocks cleared."""
        self.disposition, self.disposition_since, self.break_reason, self.release_pending = None, None, None, None
        self._disp_since, self._pin_n, self._sprint, self._hold_heading = {}, None, (None, None, 0), None

    # ---------------------------------------------------------------------------------------------------- the read
    def _disposition_read(self, held):
        """The tick's facts, the condition clocks and the release's hand-back, then `select` (the module docstring);
        no disposition where the gate reads False or nothing is held."""
        self.disposition_why, self.release_why, self.string_why, self._string_read = None, None, None, None
        self._disp_facts = None
        if not held or not self._disposing():
            self._disposition_end()
            return
        self._disp_facts = self._facts()
        self._release_read()
        self.select(held)

    def _facts(self):
        standing = [(zid, z, d) for zid, z, d in self._group_standing(GROUP_ENTRY_R + RETREAT_HOLD_R)
                    if not is_crawler(z)]
        n = self.group_n
        near = [e for e in standing if e[2] <= GROUP_ENTRY_R]
        closing = [e for e in self._group_closing if not is_crawler(e[1])]
        coming = sum(1 for e in self._string_closing if not is_crawler(e[1]))   # fix 2: within STRING_ENTRY_R
        nearest = min((d for _, z, d in self._group_standing(STRING_ENTRY_R) if not is_crawler(z)), default=None)
        entry = (len(closing) >= GROUP_LEAVE_N
                 or (len(near) >= GROUP_LEAVE_N and near[0][2] <= KEEP_R))
        f = self.fight
        m = f.m if f is not None and f._engaged() else None
        leaf = (m._progress.get("work") if m is not None else None) or {}
        leader = near[0] if near else None
        speed = None
        clock = getattr(self, "action_clock", None)
        if leader is not None and clock is not None:
            speed = _own_speed(clock.tracks.get(leader[0]))
        return {"n": n, "n_hold": len(standing), "entry": entry, "health": self._health(), "ring": self.world.room(),
                "pinned": leaf.get("pinned") is True, "leader": leader, "speed": speed, "coming": coming,
                "nearest": nearest, "clump": nearest is not None and nearest < STRING_MIN_GAP}

    def _for(self, key, cond):
        """Seconds condition `key` has read true without a break (0.0 when false, the clock cleared)."""
        if not cond:
            self._disp_since.pop(key, None)
            return 0.0
        return self.clock() - self._disp_since.setdefault(key, self.clock())

    def _clocks(self, f):
        """The condition clocks, read every tick whatever the disposition (so a condition's time is its own)."""
        if f["pinned"]:
            self._pin_n = f["n"] if self._pin_n is None else self._pin_n
        else:
            self._pin_n = None
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
        return {"pinned": self._for("pinned", self._pin_n is not None and f["n"] >= self._pin_n),
                "hold_low": self._for("hold_low", f["n_hold"] < GROUP_LEAVE_N),
                "string_low": self._for("string_low", f["n"] <= GROUP_LEAVE_N and f["coming"] < STRING_N),
                "cornered": self._for("cornered", cornered),
                "clump": self._for("clump", self.disposition == "string" and f["clump"]),
                "crowd": self._for("crowd", f["n"] >= STRING_N),
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
        jump = want == "string" and why in ("coming", "count")   # fix 2: the count's jump to STRING_N, no dwell
        if dwell is not None and why != "health" and not jump and dwell < DISPOSITION_DWELL_S:
            return cur
        self._change(cur, want, why, dwell, now)
        return want

    def _want(self, cur, f, t):
        """`(disposition, why)` the table reads this tick, else `(None, None)` (no change wanted)."""
        if f["health"] <= FLEE_HEALTH:
            return (None, None) if cur == "break" else ("break", "health")
        n = f["n"]
        if cur == "break":
            if t["calm"] >= DISPOSITION_DWELL_S:
                return ("hold" if n >= GROUP_LEAVE_N else "hunt"), "calm"
            return None, None
        if cur == "string":
            if t["cornered"] >= BREAK_CORNERED_S:
                return "break", "cornered"
            if self._sprint[2] >= SPRINT_READS:
                return "break", "sprinter"
            if self._string_from not in CLUMP_ENTRIES and (t["clump"] >= STRING_PIN_S or t["pinned"] >= STRING_PIN_S):
                return "hold", "clump"   # fix 2: a string entered at range whose nearest stays inside STRING_MIN_GAP
            if t["string_low"] >= DISPOSITION_DWELL_S:
                return "hold", "count"
            return None, None
        if cur == "hold" and t["crowd"] >= STRING_PIN_S:
            return "string", "crowd"   # fix 3: STRING_N within GROUP_ENTRY_R held STRING_PIN_S, whatever the gap
        if cur == "hold" and t["pinned"] >= STRING_PIN_S:
            return "string", "pinned"   # fix 3: whatever the gap (the pinned leaf is the clump itself)
        if not f["clump"]:   # fix 2: no string entered at range inside the clump (the answer there is `hold`, below)
            if f["coming"] >= STRING_N:
                return "string", "coming"   # fix 2: the group read coming, no dwell (`select`)
            if n >= STRING_N:
                return "string", "count"
            if cur == "hold" and self._walled(f["ring"]):
                return "string", "walled"
        if f["entry"] and self._leave_door_open():
            return "break", "leave"
        if cur == "hold":
            return ("hunt", "count") if t["hold_low"] >= DISPOSITION_DWELL_S else (None, None)
        if f["entry"] or (f["clump"] and n >= STRING_N):
            return "hold", "entry" if f["entry"] else "clump"
        return (None, None) if cur == "hunt" else ("hunt", "count")

    def _walled(self, ring):
        """The ring reads the hold's withdraw heading and both its neighbours under PULL_ROOM_NEED tiles clear."""
        if ring is None or self._hold_heading is None:
            return False
        h = ring.get("h") or ()
        if len(h) != ROOM_HEADINGS:
            return False
        i = int(math.floor((self._hold_heading % 360.0 + ROOM_STEP_DEG / 2.0) / ROOM_STEP_DEG)) % ROOM_HEADINGS
        return all(isinstance(c, (int, float)) and not isinstance(c, bool) and c < PULL_ROOM_NEED
                   for c in (h[(i - 1) % ROOM_HEADINGS], h[i], h[(i + 1) % ROOM_HEADINGS]))

    def _leave_door_open(self):
        """The leave's door reads (`ThreatGroup._leave_door`: a known door within LEAVE_DOOR_R the Flee reads `ok`, the
        race and the one-exit refusals applied)."""
        door, _ = self._leave_door(self.flee, [z for _, z, _ in self._group_standing(GROUP_ENTRY_R)])
        return door is not None

    def _change(self, cur, want, why, dwell, now):
        self.disposition_why = {"from": cur, "to": want, "why": why,
                                "dwell": None if dwell is None else round(dwell, 3)}
        self.disposition, self.disposition_since = want, now
        self._string_from = why if want == "string" else None
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
        """The Fight's `disposition`, `withdraw` and `release` this tick (the module docstring); where the selector
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
        policy.disposition = d
        if d == "hold":
            policy.withdraw = self._pull(policy, "hold")
            self._hold_heading = (None if policy.withdraw is None
                                  else math.degrees(math.atan2(policy.withdraw[1], policy.withdraw[0])) % 360.0)
        elif d == "string":
            vec, why = self._string_read if self._string_read is not None else self._string_heading()
            self.string_why, policy.withdraw = why, vec
        else:
            policy.withdraw = self._pull(policy, "hunt")   # fix 1: Plan 36's spread and cone pulls, no retreat

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
        """Fix 3 (the same trial: a scratch at game minute 601 bled the character from 98 to 42 under the engaged
        melee, every line's care refused by the clock's contact read with no why, until the care chain at 605):
        `(care, command)` when a part bleeds under `hold` or `string` with the melee engaged: with no dressing held the
        rip of a held cotton garment riding the melee (`Rip` with keepMoving, PZA/1.15's side slot), with one held and
        under GROUP_LEAVE_N standing within GROUP_ENTRY_R the riding bandage of the worst part above the legs; logged
        `care_ride` {under, cmd}; else None (a ride already running, nothing to send: the clock's stop dresses it)."""
        self.care_ride = None
        if not (self.ENGAGED_RIDE and self.disposition in ("hold", "string") and self._disposing()):
            return None
        f, care = self.fight, self.care
        if f is None or not f._engaged() or care.bleeding_n() <= 0 or self.night.inside():
            return None
        if self.actions.current is not f.m.action:
            return None   # a ride already rides it
        items = care._items()
        cmd, why = None, None
        if C.dressing_pick(items, 0.0, dirty_ok=True) is None:
            iid = C.rip_pick(self.world, care.held_out) if self.world.can("rip") else None
            cmd = Rip(iid, keepMoving=True) if iid is not None else None
            if cmd is not None and self._clock_on():   # fix 4: the riding rip asks the clock as a start (no ride
                ck = self.action_clock                   # exemption: the reflex presses nothing while it rides)
                allowed = ck.allows("rip")
                self.clock_now = self._clock_why("rip", ride="melee", **({} if allowed else {"refused": True}))
                if not allowed:
                    cmd, why = None, "clock"
            elif cmd is None:   # nothing unworn to tear: an unwear stops on a walk, so it waits for the clock's stop
                worn = any(it.get("rip") == "cotton" and it.get("worn") is True for it in self.world.inventory.values())
                why = "worn" if worn else "nothing"
        elif self.group_n < GROUP_LEAVE_N and self.world.can("bandage"):
            cmd = care._wound(items, care._bleeding(), ride=True)[0]
            cmd = cmd if cmd is not None and cmd.TYPE == "bandage" and cmd.keepMoving else None
            why = None if cmd is not None else "stop"   # a leg part: the bandage at the clock's stop
        else:
            why = "count"   # a dressing held under GROUP_LEAVE_N or more: the bandage waits for the count or the stop
        self.care_ride = {"under": self.disposition, "cmd": None if cmd is None else cmd.TYPE}
        if why is not None:
            self.care_ride["why"] = why
        return None if cmd is None else (care, cmd)

    # ---------------------------------------------------------------------------------------------------- the string
    def _string_heading(self):
        """`(unit vector or None, why)`: the string heading (the module docstring), why {deg, open, room} (`room` the
        ring's clamped degrees, None with no ring, "closed" with no open ring heading: then no vector); `(None, None)`
        with no standing zombie within GROUP_ENTRY_R."""
        p = me_xy(self.world)
        group = [z for _, z, _ in self._group_standing(STRING_ENTRY_R) if not is_crawler(z)]   # fix 2: the group coming
        if not group:
            return None, None
        cx = sum(z["x"] for z in group) / len(group)
        cy = sum(z["y"] for z in group) / len(group)
        dx, dy = p[0] - cx, p[1] - cy
        base = 0.0 if dx == 0.0 and dy == 0.0 else math.degrees(math.atan2(dy, dx))
        k_max = int(round(STRING_TURN_DEG / STRING_STEP_DEG))
        best = None
        for k in range(-k_max, k_max + 1):
            deg = (base + k * STRING_STEP_DEG) % 360.0
            rank = (-self.world.open_line(deg, STRING_LOOK_R), abs(k), k, deg)
            if best is None or rank < best:
                best = rank
        open_, deg = -best[0], best[3]
        room = self._pull_room(deg)
        why = {"deg": deg, "open": open_, "room": room}
        if room == "closed":
            return None, why
        return _heading(deg if room is None else room), why
