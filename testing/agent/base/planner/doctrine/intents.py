"""The doctrine's intents (Plan 31 Task 11, the variant D): one class per intent, each with its own `done` and `failed`
tests and the maneuver or the planner call it runs. The arbiter (`arbiter.py`) holds one at a time; `assess.py` asks the
running one to `observe` its maneuver, `check` its end and `act` (the tick's command, through itself as the owner, so
its maneuver hears of each send).

The contract (`Intent`): `kind`, `p`, `branch` (the decision line's); `check()` -> `(done | failed, why)` or None (its
own tests, read before it acts); `act()` -> `(branch, owner, command or None, branches)`; `covers(want)` (the want is
answered by this intent already: no pre-emption); `suspend()` and `resume()` (the slot's); `send(cmd)` (the owner's:
the Actions' send, the maneuver told); `line()` (its keys of `inputs.doctrine`) and `label()` (`inputs.intent`, the
scorecard's label and target).

- `Strike` (P0): one `melee` (the reflex: the stance, the face, the press, the shove, the stomp) at the zombie in
  reach, in the mode `press_mode` reads; `done` on its one press (today's melee closing a span, `Melee.take_span`;
  Task 2's meet reading a new press leaf, `Melee.press`), on its kill or the melee's other ends, or once its target
  leaves the listing or MELEE_RELEASE_R; `failed` when the build cannot run it (OFF_ENDS).
- `Fight` (P3): the one or two zombies of its want (`ids`), its pin the nearest of them standing (a fallen one with
  none standing: the finish): within MELEE_RELEASE_R or fallen, the melee (`melee_command`, the one call site, on
  either melee API: `melee_inputs`, `melee_end`); farther, a pair arriving closer together than STRING_GAP is strung (`string`: the stance backpedalling
  on one heading, chosen once, until the lead is STRING_GAP ahead), a chasing pin is met standing in the stance facing
  it (`stand`: "let it come"), an idle one is closed on (`close`: the stance's walk, a walk beyond CLOSE_WALK_R). `done`
  when none of its zombies is left standing or fallen within DISENGAGE_R (`kill` when it read one killed, else `gone`);
  `failed` after DUD_N strikes in a row that lowered nothing or the meet's own stall (`lost` `no progress`: `dud`),
  or with the pin's distance not falling for
  STALL_S while it stands, closes or strings (`stall`), its pin then left for SKIP_S (`Memory.skip`: the Fight's want
  skips it; the strike at P0 does not). Health is never read.
- `Dress` (P1): the `maneuvers.Dress` of the part (stop, tear, bandage; riding the pre-empted intent's walk for a part
  above the legs while that walk runs). `done` once the part reads not bleeding; `failed` with the Dress's own end (its
  hold then keeps P1 off until a dressing or a garment is added or `care.DRESS_RETRY_S` pass), or `zombie near` when a
  standing zombie came within KEEP_R (no hold: the fight takes it and the Dress comes back).
- `Avoid` (P2): the walk at a run (never a sprint, #4296; memory `no-sprinting`) to the refuge chosen once
  (`situation.refuge`), changed only when its route fails (`stuck`, `no path`, `no square`, a timeout, or its distance
  not falling for STALL_S), then the stance at the refuge facing the nearest (`hold`: the filter at a door or a way
  out, the stance in the open). `done` with no aware standing zombie within GROUP_CLEAR_R (`clear`) or, armed, two or
  fewer (`thinned`: the Fight then); `failed` with no refuge (`no refuge`) or after ROUTE_TRIES route failures
  (`route`), the next Avoid then held off AVOID_RETRY_S (the Fight takes the nearest meanwhile, whatever the count).
  The sneak once out of sight is Survive's gait (`sneak.py`): a walk with no zombie near chasing goes crouched.
- `Door` (P4): decided once (`situation._door`): `stance_open` takes the stance's leg to the door's post
  (`door_held.door_post`), opens it (`Interact` open), then stands facing the zombie (`meet`) while it is across the
  edge; `leave` marks a door held (`World.mark_door`), ends the running goal whose way goes through the portal
  (`door_held.meets_portal`, as P30-C's leave does) and hands the portal to the goal runner (`door_left`) in one tick.
  `done` when the zombie crossed to the player's side or left (the fight takes it), or at once for a leave; `failed`
  when the open failed (the door then left).
- `Order` (P5): the ladder's lower steps in their order, Survive's own (`_need`, `_load`, `_night`, `_care_stock`,
  `_goal`), a cooled command passed over as the ladder passes it; the label the step's (`needs`, `rest`, `stock`, or
  the goal's: `loot`, `travel`); while a LootBuilding runs, the model's next order is prefetched (`source.Resume`).
  Never ends by itself.
"""
import dataclasses
import math

from agent.base import pza1
from agent.base.planner.care import LEG_FIRST
from agent.base.planner.dispatch import MANEUVERS, OFF_ENDS
from agent.base.planner.doctrine import constants as K
from agent.base.planner.doctrine.situation import aware, listed, refuge, strike_r
from agent.base.planner.door_held import meets_portal, portal_between
from agent.base.planner.edges import same_side
from agent.base.planner.maneuvers.melee import MeleeInputs
from agent.base.planner.policies import (AIM_LEG_S, DISENGAGE_R, DOOR_POST_PACE, KEEP_R, MELEE_RELEASE_R, RIDE_TYPES,
                                         SEEK_SWITCH_R, WALK_DONE_R, arm_pain, away_vector, centre,
                                         chasing, clear_heading, on_floor, on_room, running, zdist)
from agent.base.pza1 import Aim, Interact, WalkTo
from agent.base.world import me_xy

CLOSE_WALK_R = 2 * KEEP_R   # 5.0 tiles: an idle pin farther than this is walked to (a walk), nearer the stance's walk;
                            # a first guess for the trials
PROGRESS_R = 0.25           # tiles the distance to a walk's target must fall by to count as progress (the stall read)
ORDER_STEPS = ("need", "load", "night", "stock", "goal")   # Survive's ladder steps below the threat and care, in order
GOAL_KINDS = {"LootBuilding": "loot", "ExploreToward": "travel", "Shelter": "travel", "Stock": "stock",
              "Rest": "rest"}   # the scorecard's labels of the goal types (`tools/trial_score.py` KNOWN_LABELS)
STEP_KINDS = {"need": "needs", "load": "needs", "night": "rest", "care": "stock"}


def _xy(sq):
    return [sq[0], sq[1]]


def spent(world):
    """The arms' pain is past SPENT_PAIN: a swing's damage divided (#4370), the meet becomes shove and stomp."""
    pain = arm_pain(world)
    return pain is not None and pain > K.SPENT_PAIN


def press_mode(world, z):
    """The melee's mode at zombie `z`: `finish` at a fallen one; `shove` unarmed or spent (the spec's section 4 item
    2b); else `strike`."""
    if on_floor(z):
        return "finish"
    if world.weapon is None or spent(world):
        return "shove"
    return "strike"


MELEE_FIELDS = frozenset(f.name for f in dataclasses.fields(MeleeInputs))
MEET = "back" not in MELEE_FIELDS   # Task 2's meet (PZA/1.10, `MeleeInputs(mode, reach, floor_swing)`) on this tree;
                                    # False: today's melee (PZA/1.9, `MeleeInputs(mode, reach, back, floor_swing,
                                    # close_r)`), with its back leg and its time end
KILL_ENDS = ("dead", "kill")        # the melee's end on its target's death: PZA/1.9's, PZA/1.10's
OTHER_ENDS = ("crowd", "handback")  # ... on another standing zombie near: PZA/1.9's `crowd` {id, d}, PZA/1.10's
                                    # `handback` {id, d}
UNREACHED = ("out of reach",)       # a lost target the Fight leaves (PZA/1.9's end, PZA/1.10's `lost` why)
DUD = "no progress"                 # PZA/1.10's `lost` why: the Lua's own stall of presses that lowered nothing


def melee_inputs(mode, reach):
    """The doctrine's `MeleeInputs` on either melee (`MEET`): the strike radius as the reach, the floor swing at a
    fallen zombie (#4374, #4679); on today's melee no back step (0, 0: the combat doctrine's "after the press, no back
    step") and no swing close (`closeR` 0: the swing at the reach, E21's and F13's presses that lowered, #4596), both
    gone from Task 2's meet."""
    if MEET:
        return MeleeInputs(mode, reach, True)
    return MeleeInputs(mode, reach, (0.0, 0.0), True, 0.0)


def melee_end(m):
    """(end, why) of an ended melee read the same way on either API: `kill`, `other` (its zombie {id, d} the why),
    `lost` (out of range, out of reach, no progress), else its own end with no why; None while it runs."""
    over = m.over()
    if over is None:
        return None
    if over in KILL_ENDS:
        return "kill", None
    if over in OTHER_ENDS:
        return "other", getattr(m, "handback", None) or getattr(m, "crowd", None) or {}
    if over == "lost":
        return "lost", getattr(m, "end_why", None)
    if over in ("out of range",) + UNREACHED:
        return "lost", over
    return over, None


def melee_command(intent, zid, mode):
    """THE one call site of the `Melee` maneuver (Task 2's meet changed its arguments; `melee_inputs` reads which API
    this tree carries): the intent's running melee at `zid` stepped, a new one made when none runs at it (the old one
    retired, its late kills still read). Returns the command, or None while it runs."""
    ctx = intent.ctx
    reach = strike_r(ctx.world) if ctx.world.weapon is not None else 0.0
    m = intent.m
    for _ in range(2):   # a melee its own step finds ended is retired, and a fresh one starts at once
        if m is None or m.target != zid or m.over() is not None:
            ctx.retire(m)
            m = intent.m = MANEUVERS["melee"](ctx.world, ctx.actions, ctx.clock, zid)
            intent.press_seen = None
        m.inputs = melee_inputs(mode, reach)
        cmd = m.step()
        if cmd is not None or m.over() is None:
            break
    intent.mcmd = cmd
    return cmd


def fallback_press(intent, zid, mode):
    """A build announcing no `melee`: one `attack`, `shove` or `stomp` at a time (`finish` stomps), held while it
    runs."""
    if running(intent.ctx.actions, intent.last):
        return None
    if mode == "finish":
        return pza1.Stomp(zid)
    return pza1.Shove(zid) if mode == "shove" else pza1.Attack(zid)


class Intent:
    """The contract (the module docstring)."""

    kind = None
    p = None
    branch = "threat"

    def __init__(self, ctx, want, prev=None):
        self.ctx = ctx
        self.want = want
        self.target = want.target
        self.ids = tuple(want.ids)
        self.why = dict(want.why)
        self.state = "start"
        self.end = None
        self.last = None       # the last Action this intent sent
        self.m = None          # its maneuver, else None
        self.mcmd = None       # the maneuver's command this tick (routed to it at the send)
        self.press_seen = None   # the melee's press leaf when this intent took it (the meet's one-press read)
        self.started = ctx.now()
        self.kills = 0
        self._inherit(prev)

    def _inherit(self, prev):
        """A running melee of the intent that ended this tick, at one of this intent's zombies, is kept (the Strike's
        press handed to the Fight that follows it); any other is retired."""
        if prev is None or prev.m is None:
            return
        m = prev.m
        prev.m = None
        if getattr(m, "name", None) == "melee" and m.over() is None and m.target in self.ids:
            self.m = m
            self.press_seen = getattr(m, "press", None)   # its earlier press is the last intent's, not this one's
        else:
            self.ctx.retire(m)

    # -- the contract ---------------------------------------------------------------------------------------------
    def finish(self, end, why):
        if self.end is None:
            self.end = (end, why)

    def check(self):
        return self.end

    def covers(self, want):
        return False

    def suspend(self):
        pass

    def resume(self):
        pass

    def observe(self):
        """The maneuver's read: its kills counted (`ctx.note_kill`)."""
        m = self.m
        if m is None:
            return
        m.observe()
        for zid in m.take_kills():
            self.kills += 1
            self.ctx.note_kill(zid)

    def act(self):
        """`(branch, owner, command or None, branches, cooled)`: this intent the owner of its own command."""
        cmd = self.command()
        return self.branch, self, cmd, {self.branch: self.branch_why()}, None

    def command(self):
        return None

    def branch_why(self):
        why = {"intent": self.kind, "state": self.state}
        if self.m is not None:
            why["maneuver"] = self.m.log()
        return why

    def send(self, cmd):
        a = self.ctx.actions.send(cmd)
        self.last = a
        if self.m is not None and cmd is self.mcmd:
            self.m.sent(cmd, a)
        return a

    def target_label(self):
        return self.target

    def label(self):
        out = {"kind": self.kind}
        t = self.target_label()
        if t is not None:
            out["target"] = t
        return out

    def line(self):
        return {"intent": self.kind, "p": self.p, "why": self.why, "state": self.state,
                "target": self.target_label()}

    # -- shared reads ---------------------------------------------------------------------------------------------
    def zombie(self, zid):
        """(tiles, record) of listed zombie `zid` with a position, not read dead, else None."""
        z = self.ctx.world.zombies.get(zid)
        if z is None or z.get("x") is None or z.get("y") is None or self.ctx.mem.dead.get(zid, -math.inf) > \
                self.ctx.now():
            return None
        return zdist(self.ctx.world, z), z

    def leg(self, state, cmd):
        """A stance leg or walk of kind `state`: sent when the kind changed or the last one ended, else None."""
        if state == self.state and running(self.ctx.actions, self.last):
            return None
        self.state = state
        return cmd


class Strike(Intent):
    kind = "strike"
    p = K.P_STRIKE

    def observe(self):
        """One press: done on its kill, on its first press read (today's melee: a span closed; the meet: a new press
        leaf), or on the melee's other ends; failed on a build that cannot run it."""
        super().observe()
        m = self.m
        if m is None:
            return
        span, end = m.take_span(), melee_end(m)
        leaf = getattr(m, "press", None)
        if end is not None and end[0] == "kill":
            self.finish("done", "kill")
        elif span is not None or (leaf is not None and leaf is not self.press_seen):
            self.finish("done", "press")
        elif end is not None and end[0] in OFF_ENDS:
            self.finish("failed", end[0])
        elif end is not None:
            self.finish("done", end[0] if end[1] is None or not isinstance(end[1], str) else end[1])

    def check(self):
        if self.end is not None:
            return self.end
        if self.m is None and self.last is not None and self.ctx.actions.done(self.last):
            return "done", "press"   # the fallback press ended
        got = self.zombie(self.target)
        if got is None:
            return "done", "gone"
        if got[0] > MELEE_RELEASE_R:
            return "done", "out"
        return None

    def covers(self, want):
        return want.kind == "strike"

    def command(self):
        got = self.zombie(self.target)
        if got is None:
            return None
        mode = press_mode(self.ctx.world, got[1])
        self.state = mode
        if not self.ctx.world.can("melee"):
            return fallback_press(self, self.target, mode)
        cmd = melee_command(self, self.target, mode)
        if self.m.over() in OFF_ENDS:
            self.finish("failed", self.m.over())
        return cmd


class Fight(Intent):
    kind = "fight"
    p = K.P_FIGHT

    def __init__(self, ctx, want, prev=None):
        super().__init__(ctx, want, prev)
        self.ids = self.ids or (want.target,)
        self.pin = want.target
        self.duds = 0
        self.best = None        # (the pin, its least distance) since the stall clock started
        self.best_at = ctx.now()
        self.heading = None     # the string's heading, chosen once
        self.melee_off = False

    def alive(self):
        """(tiles, id, record) of the Fight's zombies listed within DISENGAGE_R, not read dead or skipped, nearest
        first."""
        now = self.ctx.now()
        out = []
        for zid in self.ids:
            got = self.zombie(zid)
            if got is None or got[0] > DISENGAGE_R or self.ctx.mem.skip.get(zid, -math.inf) > now:
                continue
            out.append((got[0], zid, got[1]))
        out.sort(key=lambda e: (e[0], repr(e[1])))
        return out

    def _pick(self, al):
        """The pin: the current one while it stands unless another standing one is SEEK_SWITCH_R nearer; else the
        nearest standing; with none standing, the nearest fallen (the finish)."""
        up = [e for e in al if not on_floor(e[2])]
        pool = up or al
        cur = next((e for e in pool if e[1] == self.pin), None)
        if cur is not None and pool[0][0] >= cur[0] - SEEK_SWITCH_R:
            return cur
        return pool[0]

    def observe(self):
        super().observe()
        m = self.m
        if m is None:
            return
        span = m.take_span()
        if span is not None and span[0] > 0:
            self.duds = 0 if span[1] is not False else self.duds + span[0]
        end = melee_end(m)
        if end is None:
            return
        kind, why = end
        if kind == "other":
            zid = (why or {}).get("id")
            if zid is not None and self.zombie(zid) is not None:
                self.ids = self.ids if zid in self.ids else self.ids + (zid,)
                self.pin = zid
        elif kind == "lost" and why in UNREACHED:
            self.ctx.skip(m.target)
        elif kind == "lost" and why == DUD:
            self.duds = max(self.duds, K.DUD_N)   # the meet's own stall: the Fight's dud
        elif kind in OFF_ENDS:
            self.melee_off = True
        self.ctx.retire(m)
        self.m = None

    def check(self):
        if self.end is not None:
            return self.end
        al = self.alive()
        if not al:
            return "done", "kill" if self.kills else "gone"
        if self.duds >= K.DUD_N:
            self.ctx.skip(self.pin)
            return "failed", "dud"
        if self.state in ("stand", "close", "string"):
            pin = next((e for e in al if e[1] == self.pin), None)
            now = self.ctx.now()
            if pin is not None and (self.best is None or self.best[0] != pin[1] or pin[0] < self.best[1] - PROGRESS_R):
                self.best, self.best_at = (pin[1], pin[0]), now
            elif pin is not None and now - self.best_at >= K.STALL_S:
                self.ctx.skip(self.pin)
                return "failed", "stall"
        return None

    def covers(self, want):
        return want.kind in ("strike", "fight") and want.target in self.ids

    def command(self):
        al = self.alive()
        if not al:
            return None
        d, zid, z = self._pick(al)
        if zid != self.pin:
            self.pin, self.best = zid, None
        w = self.ctx.world
        if on_floor(z) or d <= MELEE_RELEASE_R:
            self.best, self.best_at = None, self.ctx.now()
            mode = press_mode(w, z)
            self.state = "finish" if mode == "finish" else "meet"
            if self.melee_off or not w.can("melee"):
                return fallback_press(self, zid, mode)
            return melee_command(self, zid, mode)
        up = [e for e in al if not on_floor(e[2])]
        if len(up) == 2 and up[1][0] - up[0][0] < K.STRING_GAP:
            v = self._string_heading(up)
            if v is not None:
                return self.leg("string", Aim(v[0], v[1], AIM_LEG_S, targetId=zid))
        if chasing(z):
            return self.leg("stand", Aim(0.0, 0.0, AIM_LEG_S, targetId=zid))
        mx, my = me_xy(w)
        ux, uy = (z["x"] - mx) / d, (z["y"] - my) / d
        if d > CLOSE_WALK_R:
            stop = d - strike_r(w)
            return self.leg("close", WalkTo(mx + ux * stop, my + uy * stop, "walk"))
        return self.leg("close", Aim(ux, uy, min(AIM_LEG_S, (d - strike_r(w)) / DOOR_POST_PACE), targetId=zid))

    def _string_heading(self, up):
        """The string's heading, chosen once: away from the two (`policies.away_vector`) when its line reads clear for
        KEEP_R, else None (no string: the stand)."""
        if self.heading is None:
            v = away_vector(self.ctx.world, [(e[2]["x"], e[2]["y"]) for e in up])
            if v is not None and clear_heading(self.ctx.world, v, KEEP_R):
                self.heading = v
        return self.heading

    def target_label(self):
        return self.pin

    def branch_why(self):
        why = super().branch_why()
        why.update(target=self.pin, ids=list(self.ids), duds=self.duds)
        got = self.zombie(self.pin)
        if got is not None:
            why["d"] = got[0]
        return why

    def label(self):
        out = super().label()
        if self.state == "string":
            out["play"] = "string"
        return out


class Dress(Intent):
    kind = "dress"
    p = K.P_DRESS
    branch = "care"

    def __init__(self, ctx, want, prev=None):
        super().__init__(ctx, want, prev)
        part = want.target
        walk = ctx.actions.current   # the pre-empted intent's walk, its sender the intent or the goal runner
        ride = (isinstance(part, int) and part < LEG_FIRST and ctx.arbiter.slot is not None and walk is not None
                and walk.type in RIDE_TYPES and running(ctx.actions, walk))
        self.m = MANEUVERS["dress"](ctx.world, ctx.actions, ctx.clock, part=part, ride=ride)

    def observe(self):
        self.m.observe()

    def check(self):
        if self.end is not None:
            return self.end
        over = self.m.over()
        if over == "done":
            return "done", "dressed"
        if over == "failed":
            self.ctx.mem.dress_hold = (frozenset(self.ctx.world.inventory), self.ctx.now())
            self.end = ("failed", self.m.fail)
            return self.end
        if over == "superseded":
            return "failed", "zombie near"
        return None

    def command(self):
        cmd = self.m.step()
        self.mcmd = cmd
        self.state = self.m.phase
        if self.m.over() is not None:
            self.end = self.check()
        return cmd

    def branch_why(self):
        return {"reason": "dress", "dress": self.m.log()}

    def label(self):
        return {"kind": "dress"}   # a part is no place: the scorecard's target is a square or a zombie


class Avoid(Intent):
    kind = "avoid"
    p = K.P_AVOID

    def __init__(self, ctx, want, prev=None):
        super().__init__(ctx, want, prev)
        self.refuge = want.target
        self.tries = 0
        self.refused = []
        self.walk = None
        self.best, self.best_at = None, ctx.now()
        if self.refuge is None:
            self._fail("no refuge")
        else:
            self.state = "hold" if self.refuge["kind"] == "inside" else "walk"

    def _fail(self, why):
        self.finish("failed", why)
        self.ctx.mem.avoid_until = self.ctx.now() + K.AVOID_RETRY_S

    def group(self):
        """The aware standing zombies within GROUP_CLEAR_R not behind a door or a window."""
        w = self.ctx.world
        me = me_xy(w)
        marked = w.marked_doors()
        inside = on_room(w)
        out = []
        for d, zid, z in listed(w, self.ctx.mem, self.ctx.now()):
            if d > K.GROUP_CLEAR_R:
                break
            if on_floor(z) or not aware(z):
                continue
            if d <= K.DOOR_R and portal_between(w, me, (z["x"], z["y"]), marked, inside) is not None:
                continue
            out.append((d, zid, z))
        return out

    def check(self):
        if self.end is not None:
            return self.end
        g = self.group()
        if not g:
            return "done", "clear"
        if len(g) < K.GROUP_N and self.ctx.world.weapon is not None:
            return "done", "thinned"
        return None

    def resume(self):
        self.walk, self.best, self.best_at = None, None, self.ctx.now()

    def suspend(self):
        self.walk = None

    def _reroute(self):
        self.tries += 1
        self.refused.append(self.refuge["square"])
        self.walk, self.best = None, None
        if self.tries >= K.ROUTE_TRIES:
            self._fail("route")
            return
        r = refuge(self.ctx.world, [e[2] for e in self.group()], self.refused)
        if r is None:
            self._fail("no refuge")
            return
        self.refuge, self.best_at = r, self.ctx.now()
        self.state = "hold" if r["kind"] == "inside" else "walk"

    def command(self):
        """The walk to the refuge (its end read first: `done` holds, a supersede re-sends it, any other end re-routes;
        the stall re-routes too), then the stance at the refuge."""
        a = self.walk
        if self.state == "walk" and a is not None and self.ctx.actions.done(a):
            self.walk = None
            if a.state == "done":
                self.state = "hold"
            elif not (a.state == "failed" and a.reason == "superseded"):
                self._reroute()
        if self.state == "walk" and self.end is None:
            c = centre(self.refuge["square"])
            mx, my = me_xy(self.ctx.world)
            d = math.hypot(c[0] - mx, c[1] - my)
            now = self.ctx.now()
            if d <= WALK_DONE_R:
                self.state = "hold"
            elif self.best is None or d < self.best - PROGRESS_R:
                self.best, self.best_at = d, now
            elif now - self.best_at >= K.STALL_S:
                self._reroute()
        if self.end is not None:
            return None
        if self.state == "walk":
            if self.walk is not None:
                return None   # the walk runs (a posture beside it leaves it running)
            c = centre(self.refuge["square"])
            return WalkTo(c[0], c[1], "run")
        g = self.group()
        if not g:
            return None
        return self.leg("hold", Aim(0.0, 0.0, AIM_LEG_S, targetId=g[0][1]))

    def send(self, cmd):
        a = super().send(cmd)
        if cmd.TYPE == "walkTo":
            self.walk = a
        return a

    def target_label(self):
        return None if self.refuge is None else _xy(self.refuge["square"])

    def label(self):
        out = super().label()
        if self.refuge is not None:
            out["kind"] = self.refuge["label"] if self.state == "walk" else (
                "filter_door" if self.refuge["kind"] in ("door", "exit", "inside") else "fight_hold")
        return out

    def branch_why(self):
        why = super().branch_why()
        why.update(refuge=self.refuge, tries=self.tries)
        if self.state == "walk":
            why["flee"] = "group"   # the decision line's contract: a retreat's reason on the threat why
        return why


class Door(Intent):
    kind = "door"
    p = K.P_DOOR

    def __init__(self, ctx, want, prev=None):
        super().__init__(ctx, want, prev)
        plan = self.plan = want.target
        self.zid = plan["zid"]
        self.edge = plan["edge"]
        ctx.mem.doors[self.edge] = (plan["decision"], self.ids, ctx.now())
        self.state = "leave" if plan["decision"] == "leave" else "post"
        self.opened = None   # the open's Action

    def check(self):
        if self.end is not None:
            return self.end
        got = self.zombie(self.zid)
        if got is None:
            return "done", "gone"
        z = got[1]
        if self.state != "leave" and same_side(self.edge, me_xy(self.ctx.world), (z["x"], z["y"])):
            return "done", "crossed"
        a = self.opened
        if a is not None and self.ctx.actions.done(a) and a.state != "done" and a.reason != "superseded":
            self.ctx.mem.doors[self.edge] = ("leave", self.ids, self.ctx.now())
            self._leave()
            return "failed", "open " + (a.reason or a.state)
        return None

    def command(self):
        if self.state == "leave":
            self._leave()
            self.finish("done", "leave")
            return None
        w = self.ctx.world
        door = self.plan["door"]
        seen = (getattr(w, "door_seen", None) or {}).get(door) or {}
        if seen.get("open") is True or (self.opened is not None and self.opened.state == "done"):
            return self.leg("meet", Aim(0.0, 0.0, AIM_LEG_S, targetId=self.zid))
        post = self.plan["post"]
        mx, my = me_xy(w)
        cx, cy = post[0] + 0.5, post[1] + 0.5
        far = math.hypot(cx - mx, cy - my)
        if far > WALK_DONE_R and self.state == "post":
            return self.leg("post", Aim((cx - mx) / far, (cy - my) / far, min(AIM_LEG_S, far / DOOR_POST_PACE),
                                        targetId=self.zid))
        if self.opened is not None and not self.ctx.actions.done(self.opened):
            return None
        self.state = "open"
        return Interact(door[0], door[1], "open")

    def send(self, cmd):
        a = super().send(cmd)
        if cmd.TYPE == "interact":
            self.opened = a
        return a

    def _leave(self):
        """P30-C's leave, once: a door marked held; the running goal whose way goes through the portal ended `failed
        "door held"` and cooled, its far target marked; the portal handed to the goal runner (`door_left`)."""
        w, sv = self.ctx.world, self.ctx.sv
        if self.plan["kind"] == "door":
            w.mark_door(self.edge[0], "held", "out")
        sv.goals.door_left = self.edge
        g = getattr(sv.goals, "current", None)
        me = me_xy(w)
        if g is not None and hasattr(g, "stall_target") and g.running:
            pts = []
            t = g.stall_target()
            if t is not None:
                pts.append((t[0] + 0.5, t[1] + 0.5))
            a = g.last
            if a is not None and a.type == "walkTo" and not self.ctx.actions.done(a):
                pts.append((a.args.get("x"), a.args.get("y")))
            if any(None not in pt and meets_portal(w, me, pt, self.edge) for pt in pts):
                g.cool = True
                g.mark_far(w)
                g.end("failed", "door held")

    def target_label(self):
        return _xy(self.plan["door"])

    def label(self):
        out = super().label()
        out["kind"] = "door_leave" if self.plan["decision"] == "leave" else "filter_door"
        return out

    def branch_why(self):
        why = super().branch_why()
        why["door_held"] = {"door": _xy(self.plan["door"]), "kind": self.plan["kind"], "n_behind": len(self.ids),
                            "decision": self.plan["decision"]}
        return why


class Order(Intent):
    kind = "order"
    p = K.P_ORDER
    branch = None

    def __init__(self, ctx, want, prev=None):
        super().__init__(ctx, want, prev)
        self.sub = "rest"
        self.square = None

    def act(self):
        """Survive's lower steps in the ladder's order (the module docstring): `(branch, owner, command, branches,
        cooled)`."""
        sv = self.ctx.sv
        tried, cooled = {}, None
        self.sub, self.square, self.state = "rest", None, "idle"
        for name in ORDER_STEPS:
            sv.why = {}
            ans = sv._care_stock() if name == "stock" else getattr(sv, "_" + name)()
            branch = "care" if name == "stock" else name
            tried[branch] = dict(tried.get(branch) or {}, stock=sv.why) if name == "stock" else sv.why
            if ans is None:
                continue
            if ans[1] is not None and sv._cooling(ans[1]) and not sv.care.owns(ans[1]):
                cooled = {"type": ans[1].TYPE, "args": ans[1].args()}
                continue
            self._label(branch)
            self._prefetch()
            return branch, ans[0], ans[1], tried, cooled
        self._prefetch()
        return None, None, None, tried, cooled

    def _label(self, branch):
        self.state = branch
        if branch != "goal":
            self.sub = STEP_KINDS.get(branch, "needs")
            return
        g = getattr(self.ctx.sv.goals, "current", None)
        if g is None:
            cont = getattr(self.ctx.sv.goals, "continue_now", None)
            self.sub = "travel" if cont else "rest"
            self.square = (cont or {}).get("target")
            return
        self.sub = GOAL_KINDS.get(g.TYPE, "travel")
        t = g.stall_target() if hasattr(g, "stall_target") else None
        self.square = None if t is None else [t[0], t[1]]

    def _prefetch(self):
        g = getattr(self.ctx.sv.goals, "current", None)
        if g is not None and g.TYPE == "LootBuilding" and g.running:
            self.ctx.source.prefetch(self.ctx.sv._view, self.ctx.now())

    def target_label(self):
        return self.square

    def label(self):
        out = {"kind": self.sub}
        if self.square is not None:
            out["target"] = self.square
        return out

    def line(self):
        out = super().line()
        out["intent"] = "order"
        out["step"] = self.sub
        return out


INTENTS = {c.kind: c for c in (Strike, Dress, Avoid, Fight, Door, Order)}
