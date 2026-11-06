"""The doctrine's intents (Plan 31 Task 11, the variant D): one class per intent, each with its own `done` and `failed`
tests and the maneuver or the planner call it runs. The arbiter (`arbiter.py`) holds one at a time; `assess.py` asks the
running one to `observe` its maneuver, `check` its end and `act` (the tick's command, through itself as the owner, so
its maneuver hears of each send).

The contract (`Intent`): `kind`, `p`, `branch` (the decision line's); `check()` -> `(done | failed, why)` or None (its
own tests, read before it acts); `act()` -> `(branch, owner, command or None, branches, cooled)`; `covers(want)` (the
want is answered by this intent already: no pre-emption); `suspend()`, `resume()` and `adopt(prev)` (the slot's);
`play()` (the line's `inputs.play`, else None); `send(cmd)` (the owner's:
the Actions' send, the maneuver told); `line()` (its keys of `inputs.doctrine`) and `label()` (`inputs.intent`, the
scorecard's label and target).

- `Strike` (P0): one `melee` (the reflex: the stance, the face, the press, the shove, the stomp) at the zombie in
  reach, in the mode `press_mode` reads; `done` on its one press (today's melee closing a span, `Melee.take_span`;
  Task 2's meet reading a new press leaf, `Melee.press`), on its kill or the melee's other ends, or once its target
  leaves the listing or MELEE_RELEASE_R; `failed` when the build cannot run it (OFF_ENDS), and on a backed-off end or
  a rejection (`melee_backoff`: the zombie backed off BACKOFF_TICKS, review-t11-doctrine Major 2).
- `Fight` (P3): the one or two zombies of its want (`ids`), its pin the nearest of them standing (a fallen one with
  none standing: the finish): within MELEE_RELEASE_R or fallen, the melee (`melee_command`, the one call site, on
  either melee API: `melee_inputs`, `melee_end`), nothing while the pin's melee backs off (`wait`); farther, a stand
  (a group with no refuge) first walks the stance to its ground (`ground`), a pair arriving closer together than
  STRING_GAP is strung (`string`: the stance backpedalling on one heading, chosen once), a chasing pin is met standing
  in the stance facing it (`stand`: "let it come") until it has not closed for STALL_S, then closed on (`close`, M1),
  an idle one is closed on (the stance's walk, a walk beyond CLOSE_WALK_R). `done` when none of its zombies is left
  standing or fallen within DISENGAGE_R (`kill` when it read one killed, else `gone`); `failed` after DUD_N strikes in a
  row that lowered nothing, backed-off ends included, or the meet's own stall (`lost` `no progress`: `dud`), or with
  the pin's distance not falling for STALL_S while it closes (`stall`; the string keeps its gap by design and never
  stalls), its pin then left for SKIP_S (`Memory.skip`: the Fight's want skips it; the strike at P0 does not). Health is
  never read.
- `Dress` (P1): the `maneuvers.Dress` of the part (stop, tear, bandage; riding the pre-empted intent's walk for a part
  above the legs while that walk runs). `done` once the part reads not bleeding; `failed` with the Dress's own end (its
  hold then keeps P1 off until a dressing or a garment is added or `care.DRESS_RETRY_S` pass), or `zombie near` when a
  standing zombie came within KEEP_R (no hold: the fight takes it and the Dress comes back).
- `Avoid` (P2): the walk at a run (never a sprint, #4296; memory `no-sprinting`) to the named refuge chosen once
  (`situation.refuge`), a window refuge's walk ending in its climb (`Window`), a fence's walk climbing the fence where
  it sticks (`Climb`, `night.hop_after`), changed only when its route fails (`stuck`, `no path`, `no square`, a
  timeout, or its distance not falling for STALL_S), then the stance at the refuge facing the nearest (`hold`, the
  filter). `done` with no aware standing zombie within GROUP_CLEAR_R (`clear`), or, armed, two or fewer (`thinned`: the
  Fight then), or after AVOID_HOLD_S of the hold (`held`, M6: the Fight at the refuge then, P2 held off AVOID_RETRY_S);
  `failed` with no refuge (`no refuge`) or after ROUTE_TRIES route failures (`route`), the next Avoid then held off
  AVOID_RETRY_S (the Fight takes the nearest meanwhile, whatever the count). While it walks with the group aware of the
  character Survive's sneak gait reads it as a flee (`walking`, `assess.Doctrine._gait`); out of sight a walk goes
  crouched.
- `Door` (P4): decided once (`situation._door`): `stance_open` takes the stance's leg to the door's post
  (`door_held.door_post`), opens it (`Interact` open), then stands facing the zombie (`meet`) for DOOR_WAIT_S, then
  fights it through the doorway as long again (`through`: the stance's walk to the threshold, the melee at it) with two
  or fewer across, else re-routes (Major 1: never an indefinite hold); `leave` marks a door held (`World.mark_door`),
  ends the running goal whose way goes through the portal (`door_held.meets_portal`, as P30-C's leave does) and hands
  the portal to the goal runner (`door_left`) in one tick. `done` when the zombie crossed to the player's side or left
  (the fight takes it), at once for a leave, `reroute`, `left` or `stuck` at its bounds (the door then left); `failed`
  when the open failed (the door then left).
- `Order` (P5): the ladder's lower steps in their order, Survive's own: the care's (`_care`) in the lull only (no
  listed zombie within DANGER_R, no part bleeding: the spent dressing's replace, the wound's dressing, the wash,
  Major 3), then `_need`, `_load`, `_night`, `_care_stock`, `_goal`, a cooled command passed over as the ladder passes
  it; the label the step's (`dress` or `stock` for the lull's care, `needs`, `rest`, `stock`, or the goal's: `loot`,
  `travel`); while a LootBuilding runs, the model's next order is prefetched (`source.Resume`). Never ends by itself.
"""
import dataclasses
import math

from agent.base import pza1
from agent.base.planner.care import LEG_FIRST
from agent.base.planner.dispatch import BACKOFF_ENDS, MANEUVERS, OFF_ENDS
from agent.base.planner.doctrine import constants as K
from agent.base.planner.doctrine.situation import aware, bleeding_parts, listed, refuge, strike_r
from agent.base.planner.door_held import meets_portal, portal_between
from agent.base.planner.edges import same_side
from agent.base.planner.night import hop_after
from agent.base.planner.maneuvers.melee import MeleeInputs
from agent.base.planner.policies import (AIM_LEG_S, DANGER_R, DISENGAGE_R, DOOR_POST_PACE, KEEP_R, MELEE_RELEASE_R,
                                         RIDE_TYPES,
                                         SEEK_SWITCH_R, WALK_DONE_R, arm_pain, away_vector, centre,
                                         chasing, clear_heading, on_floor, on_room, running, zdist)
from agent.base.pza1 import Aim, Climb, Interact, WalkTo, Window
from agent.base.world import me_xy

CLOSE_WALK_R = 2 * KEEP_R   # 5.0 tiles: an idle pin farther than this is walked to (a walk), nearer the stance's walk;
                            # a first guess for the trials
PROGRESS_R = 0.25           # tiles the distance to a walk's target must fall by to count as progress (the stall read)
ORDER_STEPS = ("care", "need", "load", "night", "stock", "goal")   # Survive's ladder steps below the threat, in order:
                            # the care's only in the lull (`Order._lull`), its bleeding step P1's
GROUND_DONE_R = 0.6         # tiles from the stand's ground square's centre at which the stand is taken (inside the walk's
                            # own done radius); a first guess
HOLD_KINDS = {"door": "filter_door", "exit": "filter_door", "inside": "filter_door", "window": "filter_window",
              "fence": "filter_fence"}   # the Avoid's hold label by its refuge's kind (refuge words for the scorecard)
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
BACKOFF = tuple(BACKOFF_ENDS) + ("no weapon",)   # the melee's ends that back its zombie off BACKOFF_TICKS (the ladder's
                                    # `dispatch.BACKOFF_ENDS`, and `no weapon`, which a re-send would meet again)


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


def melee_backoff(m):
    """The end of an ended melee that backs its zombie off (BACKOFF, or any rejection but a build's, OFF_ENDS), else
    None (review-t11-doctrine Major 2: the ladder's back-off honoured, `dispatch.FightDispatch._observe_maneuver`)."""
    over = m.over()
    if over is None:
        return None
    a = m.action
    if over in BACKOFF or (a is not None and a.state == "rejected" and over not in OFF_ENDS):
        return over
    return None


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
        self.n = None          # the arbiter's serial of this intent (`Arbiter._set`), on the line as `n`
        self._inherit(prev)

    def adopt(self, prev):
        """The resumed slot's hand-over (review-t11-doctrine m2): the ended intent's running melee kept when this
        intent runs none and the melee's zombie is one of this intent's, else retired (its late kills still read)."""
        if prev is None or prev.m is None or prev is self:
            return
        if self.m is not None:
            self.ctx.retire(prev.m)
            prev.m = None
            return
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

    def play(self):
        """The line's `inputs.play` this tick (a retreat leg's label where the scorecard reads it), else None."""
        return None

    def label(self):
        out = {"kind": self.kind}
        t = self.target_label()
        if t is not None:
            out["target"] = t
        return out

    def line(self):
        return {"intent": self.kind, "p": self.p, "why": self.why, "state": self.state,
                "target": self.target_label(), "n": self.n}

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
        back = melee_backoff(m)
        if end is not None and end[0] == "kill":
            self.finish("done", "kill")
        elif back is not None:
            self.ctx.backoff(m.target)   # a rejection or a backed-off end is no press: failed, never done
            self.finish("failed", back)
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
        self.closing = False    # a stand that stalled closes on its zombie (review-t11-doctrine M1)
        g = want.why.get("ground")
        self.ground = None if g is None else tuple(g)   # the stand's square (no refuge for a group), else None
        self.grounded = self.ground is None

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
        back = melee_backoff(m)
        if back is not None:
            self.ctx.backoff(m.target)
            self.duds += 1   # consecutive backed-off presses count toward the dud
        elif kind == "other":
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
        if self.state in ("stand", "close"):   # the string keeps its gap by design: never a stall
            pin = next((e for e in al if e[1] == self.pin), None)
            now = self.ctx.now()
            if pin is not None and (self.best is None or self.best[0] != pin[1] or pin[0] < self.best[1] - PROGRESS_R):
                self.best, self.best_at = (pin[1], pin[0]), now
            elif pin is not None and now - self.best_at >= K.STALL_S:
                if self.state == "stand":   # M1: a chaser that does not close is closed on, never left standing
                    self.closing, self.best, self.best_at = True, None, now
                    return None
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
        if self.ctx.mem.backoff.get(zid):
            self.state = "wait"   # its melee backed off: nothing sent at it until BACKOFF_TICKS pass
            return None
        if on_floor(z) or d <= MELEE_RELEASE_R:
            self.best, self.best_at = None, self.ctx.now()
            mode = press_mode(w, z)
            self.state = "finish" if mode == "finish" else "meet"
            if self.melee_off or not w.can("melee"):
                return fallback_press(self, zid, mode)
            return melee_command(self, zid, mode)
        leg = self._ground_leg(zid)
        if leg is not None or self.state == "ground":
            return leg
        up = [e for e in al if not on_floor(e[2])]
        if len(up) == 2 and up[1][0] - up[0][0] < K.STRING_GAP:
            v = self._string_heading(up)
            if v is not None:
                return self.leg("string", Aim(v[0], v[1], AIM_LEG_S, targetId=zid))
        if chasing(z) and not self.closing:
            return self.leg("stand", Aim(0.0, 0.0, AIM_LEG_S, targetId=zid))
        mx, my = me_xy(w)
        ux, uy = (z["x"] - mx) / d, (z["y"] - my) / d
        if d > CLOSE_WALK_R:
            stop = d - strike_r(w)
            return self.leg("close", WalkTo(mx + ux * stop, my + uy * stop, "walk"))
        return self.leg("close", Aim(ux, uy, min(AIM_LEG_S, (d - strike_r(w)) / DOOR_POST_PACE), targetId=zid))

    def _ground_leg(self, zid):
        """The stand's leg to its ground (the controller's ruling on M5): the stance's walk to the square with a wall
        or a fence at its back, facing the lead, until within GROUND_DONE_R; then the stand is taken there (None)."""
        if self.grounded:
            return None
        mx, my = me_xy(self.ctx.world)
        cx, cy = self.ground[0] + 0.5, self.ground[1] + 0.5
        far = math.hypot(cx - mx, cy - my)
        if far <= GROUND_DONE_R:
            self.grounded = True
            return None
        return self.leg("ground", Aim((cx - mx) / far, (cy - my) / far, min(AIM_LEG_S, far / DOOR_POST_PACE),
                                      targetId=zid))

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

    def play(self):
        """M2: the string's backpedal on the line's own `inputs.play`, where the scorecard's `_labels` reads a retreat."""
        return {"kind": "string", "target": self.pin} if self.state == "string" else None


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
        self.climb = None       # the climb's Action (a window's, or a fence on the route's stuck end)
        self.climb_cmd = None   # the climb to send (`Window` at a window refuge, `Climb` at a fence on the route)
        self.hold_at = None     # wall of the hold's first tick
        self.best, self.best_at = None, ctx.now()
        if self.refuge is None:
            self._fail("no refuge")
        elif self.refuge["kind"] == "inside":
            self._hold()
        else:
            self.state = "walk"

    def _hold(self):
        self.state = "hold"
        if self.hold_at is None:
            self.hold_at = self.ctx.now()

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
        if self.hold_at is not None and self.ctx.now() - self.hold_at >= K.AVOID_HOLD_S:
            self.ctx.mem.avoid_until = self.ctx.now() + K.AVOID_RETRY_S   # M6: the Fight at the refuge takes it
            return "done", "held"
        return None

    def resume(self):
        self.walk, self.climb, self.best, self.best_at = None, None, None, self.ctx.now()

    def suspend(self):
        self.walk, self.climb = None, None

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
        if r["kind"] == "inside":
            self._hold()
        else:
            self.state = "walk"

    def command(self):
        """The walk to the refuge (its end read first: `done` holds, or climbs a window refuge's window first; a
        supersede re-sends it; a `stuck` end at a hoppable fence on its line climbs it, `night.hop_after`; any other
        end re-routes; the stall re-routes too), then the stance at the refuge (AVOID_HOLD_S at most, `check`)."""
        acts = self.ctx.actions
        c = self.climb
        if self.state == "climb" and c is not None and acts.done(c):
            self.climb = None
            if c.state == "failed" and c.reason == "superseded":
                pass   # another sender took the slot: the climb goes again
            elif c.state != "done":
                self._reroute()
            elif c.type == "window":
                self._hold()
            else:
                self.state, self.best = "walk", None
        a = self.walk
        if self.state == "walk" and a is not None and acts.done(a):
            self.walk = None
            hop = hop_after(self.ctx.world, a)
            if a.state == "done":
                self._arrived()
            elif a.state == "failed" and a.reason == "superseded":
                pass
            elif hop is not None:
                self.state, self.climb_cmd = "climb", Climb(hop[0], hop[1])
                return self.climb_cmd
            else:
                self._reroute()
        if self.state == "walk" and self.end is None:
            c = centre(self.refuge["square"])
            mx, my = me_xy(self.ctx.world)
            d = math.hypot(c[0] - mx, c[1] - my)
            now = self.ctx.now()
            if d <= WALK_DONE_R:
                self._arrived()
            elif self.best is None or d < self.best - PROGRESS_R:
                self.best, self.best_at = d, now
            elif now - self.best_at >= K.STALL_S:
                self._reroute()
        if self.end is not None:
            return None
        if self.state == "climb":
            if self.climb is not None:
                return None
            return self.climb_cmd
        if self.state == "walk":
            if self.walk is not None:
                return None   # the walk runs (a posture beside it leaves it running)
            c = centre(self.refuge["square"])
            return WalkTo(c[0], c[1], "run")
        g = self.group()
        if not g:
            return None
        return self.leg("hold", Aim(0.0, 0.0, AIM_LEG_S, targetId=g[0][1]))

    def _arrived(self):
        """At the refuge's square: a window refuge climbs its window, any other holds."""
        if self.refuge["kind"] == "window":
            w = self.refuge["window"]
            self.state, self.climb_cmd = "climb", Window(w[0], w[1], smash=bool(self.refuge.get("smash")))
        else:
            self._hold()

    def walking(self):
        """The run to the refuge runs (Survive's sneak gait reads it as a flee while the group sees the character)."""
        return self.end is None and self.state in ("walk", "climb")

    def send(self, cmd):
        a = super().send(cmd)
        if cmd.TYPE == "walkTo":
            self.walk = a
        elif cmd.TYPE in ("climb", "window"):
            self.climb = a
        return a

    def target_label(self):
        return None if self.refuge is None else _xy(self.refuge["square"])

    def label(self):
        out = super().label()
        if self.refuge is not None:
            out["kind"] = self.refuge["label"] if self.state in ("walk", "climb") else HOLD_KINDS.get(
                self.refuge["kind"], "filter_door")
        return out

    def branch_why(self):
        why = super().branch_why()
        why.update(refuge=self.refuge, tries=self.tries)
        if self.state in ("walk", "climb"):
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
        self.opened_at = None   # wall the door first read open (the wait's start)
        self.through_at = None  # wall the fight through the doorway began

    def check(self):
        """The Door's ends (review-t11-doctrine Major 1: it never holds the stance indefinitely): `gone`, `crossed`
        (the zombie on the player's side: the Fight meets it), a failed open (the door left); DOOR_WAIT_S after the
        door read open with its zombie still across, two or fewer across turn to the fight through the doorway
        (`through`), more re-route (`reroute`: the door marked, the goal through it ended); DOOR_WAIT_S of that fight
        with no crossing or kill leave it (`left`); an open never reached within three DOOR_WAIT_S leaves it (`stuck`)."""
        if self.end is not None:
            return self.end
        got = self.zombie(self.zid)
        if got is None:
            return "done", "gone"
        z = got[1]
        me = me_xy(self.ctx.world)
        if self.state != "leave" and same_side(self.edge, me, (z["x"], z["y"])):
            return "done", "crossed"
        a = self.opened
        now = self.ctx.now()
        if a is not None and self.ctx.actions.done(a) and a.state != "done" and a.reason != "superseded":
            return self._left("failed", "open " + (a.reason or a.state))
        if self.opened_at is None and self._open_read():
            self.opened_at = now
        if self.opened_at is None:
            return self._left("done", "stuck") if now - self.started >= 3 * K.DOOR_WAIT_S else None
        if self.through_at is None and now - self.opened_at >= K.DOOR_WAIT_S:
            if len(self._across()) > K.DOOR_OPEN_MAX:
                return self._left("done", "reroute")
            self.through_at, self.state = now, "through"
        if self.through_at is not None and now - self.through_at >= K.DOOR_WAIT_S:
            return self._left("done", "left")
        return None

    def _open_read(self):
        seen = (getattr(self.ctx.world, "door_seen", None) or {}).get(self.plan["door"]) or {}
        return seen.get("open") is True or (self.opened is not None and self.opened.state == "done")

    def _across(self):
        """The listed zombies within DOOR_R on the far side of the door's edge from the player."""
        me = me_xy(self.ctx.world)
        return [zid for d, zid, z in listed(self.ctx.world, self.ctx.mem, self.ctx.now())
                if d <= K.DOOR_R and not same_side(self.edge, me, (z["x"], z["y"]))]

    def _left(self, end, why):
        """The Door left: decided `leave` for its zombies (`mem.doors`), the leave's marks (`_leave`), the end."""
        self.ctx.mem.doors[self.edge] = ("leave", self.ids, self.ctx.now())
        self._leave()
        self.end = (end, why)
        return self.end

    def observe(self):
        super().observe()
        m = self.m
        if m is not None and m.over() is not None:
            if melee_backoff(m) is not None:
                self.ctx.backoff(m.target)
            self.ctx.retire(m)
            self.m = None

    def command(self):
        if self.state == "leave":
            self._leave()
            self.finish("done", "leave")
            return None
        w = self.ctx.world
        door = self.plan["door"]
        if self.state == "through":
            return self._through()
        if self._open_read():
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

    def _through(self):
        """The fight through the doorway: the stance's walk toward the zombie to the melee's release radius (the
        threshold), then the melee at it; nothing while its melee backs off."""
        got = self.zombie(self.zid)
        if got is None or self.ctx.mem.backoff.get(self.zid):
            return None
        d, z = got
        w = self.ctx.world
        if d <= MELEE_RELEASE_R:
            mode = press_mode(w, z)
            if not w.can("melee"):
                return fallback_press(self, self.zid, mode)
            return melee_command(self, self.zid, mode)
        mx, my = me_xy(w)
        ux, uy = (z["x"] - mx) / d, (z["y"] - my) / d
        return self.leg("through", Aim(ux, uy, min(AIM_LEG_S, max(d - strike_r(w), 0.25) / DOOR_POST_PACE),
                                       targetId=self.zid))

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
            if name == "care" and not self._lull():
                tried["care"] = {"lull": False}
                continue
            ans = sv._care_stock() if name == "stock" else getattr(sv, "_" + name)()
            branch = "care" if name == "stock" else name
            tried[branch] = dict(tried.get(branch) or {}, stock=sv.why) if name == "stock" else sv.why
            if ans is None:
                continue
            if ans[1] is not None and sv._cooling(ans[1]) and not sv.care.owns(ans[1]):
                cooled = {"type": ans[1].TYPE, "args": ans[1].args()}
                continue
            self._label(branch, ans[1], name)
            self._prefetch()
            return branch, ans[0], ans[1], tried, cooled
        self._prefetch()
        return None, None, None, tried, cooled

    def _lull(self):
        """The lull (review-t11-doctrine Major 3): no listed zombie within DANGER_R and no part bleeding (the bleeding
        step is P1's Dress), so the care's other steps run (`Survive._care`: the spent dressing's replace, P27-D and
        P27-K3; the wound's dressing, P28-A; the rag's wash)."""
        w = self.ctx.world
        if bleeding_parts(w):
            return False
        return not any(d <= DANGER_R for d, _, _ in listed(w, self.ctx.mem, self.ctx.now()))

    def _label(self, branch, cmd=None, step=None):
        self.state = branch
        if step == "care":
            held = self.ctx.sv.care.last if cmd is None else None   # the care holding its running action
            dressing = (cmd is not None and cmd.TYPE == "bandage") or (held is not None and held.type == "bandage")
            self.sub = "dress" if dressing else "stock"
            return
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
