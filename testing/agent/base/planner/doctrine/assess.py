"""The doctrine's tick (Plan 31 Task 11, the variant D): `assess(survive, inputs)`, the fork's call
(`planner/control.py`), over one `Doctrine` kept on `survive.control_state["doctrine"]`.

A tick, after Survive's own `_read` (the ends of the actions, the goal runner's observe, the logged inputs):
1. The bookkeeping: the goal runner's newly closed goals noted for the resume (`source.Resume.note`); the running and
   the suspended intents' maneuvers read (`Intent.observe`: their kills), and the retired ones' late ends; the
   memory's expired entries dropped.
2. The wants (`situation.read`), the arbiter's step (`arbiter.Arbiter.step`), the running intent's act; an intent that
   ends while it acts (a Door's leave, a Dress that found nothing) hands the tick to the next one at once, at most
   MAX_STEPS times, so no tick stands idle for an end.
3. The Decision: the act's branch, owner and command; `inputs` completed as the ladder's (`need`, `consume_refused`,
   `cooled`, `branches`: the act's own, a kill read this tick on the threat's, the goal runner's stuck mark and stall
   on the goal's) and the doctrine's own keys: `inputs.doctrine` {intent, p, why, state, target, preempted_by,
   resumed, ended, slot} and `inputs.intent` {kind, target} (the scorecard's label and target, `tools/trial_score.py`;
   with `play` "string" while a Fight strings a pair).

On its first tick the Doctrine lays `source.Resume` over the goal runner's source and turns the ladder's P30-C door read
off on this Survive only (`DOOR_HELD`, an instance attribute: its leave would mark edges and end goals in `_read`
before the doctrine decides the door itself). That first tick's own `_read` has already run once with the ladder's read
on (the fork makes no call at construction, review-t11-doctrine m3): a caller that builds the Survive calls `prepare`
first to close that tick too.

Survive's sneak gait reads the Avoid's run as a flee (`Survive.mode` "flee") while a zombie of the group within
SNEAK_R is aware of the character (`hasTarget` or `known`), so the run keeps its gait until out of sight
(review-t11-doctrine m5); the mode is None on every other tick (the ladder's own threat bookkeeping never sets it under
the doctrine, which runs no Fight or Flee policy)."""
from agent.base.planner.doctrine import constants as K
from agent.base.planner.doctrine import situation
from agent.base.planner.doctrine.arbiter import Arbiter
from agent.base.planner.doctrine.intents import INTENTS
from agent.base.planner.doctrine.source import Resume
from agent.base.planner.policies import SNEAK_R
from agent.base.planner.survive import Decision

MAX_STEPS = 3   # arbiter steps a tick takes at most (an intent ended while it acted hands the tick on)
STATE_KEY = "doctrine"


class Doctrine:
    """The variant's state and its tick (the module docstring)."""

    def __init__(self, sv):
        self.sv = sv
        self.mem = situation.Memory()
        self.arbiter = Arbiter()
        self.retired = []        # maneuvers dropped whose sends' ends are still read (a late kill)
        self.kill_now = []       # the zombie ids read killed this tick
        self.source = Resume(sv.goals.source)
        sv.goals.source = self.source
        sv.DOOR_HELD = False     # the ladder's door read off on this Survive: the Door intent decides (the docstring)
        self._hist_n = len(sv.goals.history)
        self.ticks = 0

    # -- what the intents read ------------------------------------------------------------------------------------
    @property
    def world(self):
        return self.sv.world

    @property
    def actions(self):
        return self.sv.actions

    @property
    def clock(self):
        return self.sv.clock

    def now(self):
        return self.sv.clock()

    def note_kill(self, zid):
        """A kill read off a maneuver: counted once in the World, kept out of every want for SKIP_S."""
        if zid is None:
            return
        self.world.note_kill(zid)
        self.mem.dead[zid] = self.now() + K.SKIP_S
        if zid not in self.kill_now:
            self.kill_now.append(zid)

    def skip(self, zid):
        """A zombie a Fight failed on: no Fight wants it for SKIP_S."""
        if zid is not None:
            self.mem.skip[zid] = self.now() + K.SKIP_S

    def backoff(self, zid):
        """A melee at `zid` that backed off: none is sent at it for BACKOFF_TICKS ticks (the ladder's back-off)."""
        if zid is not None:
            self.mem.backoff[zid] = K.BACKOFF_TICKS

    def retire(self, m):
        if m is not None and m not in self.retired:
            self.retired.append(m)

    # -- the tick -------------------------------------------------------------------------------------------------
    def _bookkeeping(self):
        sv, now = self.sv, self.now()
        hist = sv.goals.history
        for row in hist[self._hist_n:]:
            self.source.note(row)
        self._hist_n = len(hist)
        self.kill_now = []
        for it in (self.arbiter.current, self.arbiter.slot):
            if it is not None:
                it.observe()
        for m in self.retired:
            m.observe()
            for zid in m.take_kills():
                self.note_kill(zid)
        self.retired = [m for m in self.retired if not m.drained()]
        for store in (self.mem.dead, self.mem.skip):
            for zid in [z for z, until in store.items() if until <= now]:
                del store[zid]
        for edge in [e for e, (_, _, at) in self.mem.doors.items() if now - at >= K.DOOR_DECIDED_S]:
            del self.mem.doors[edge]
        self.mem.backoff = {zid: n - 1 for zid, n in self.mem.backoff.items() if n > 1}

    def _make(self, want, prev):
        return INTENTS[want.kind](self, want, prev)

    def tick(self, inputs):
        sv = self.sv
        sv.need_mark = None
        sv.mode = None
        self.ticks += 1
        self._bookkeeping()
        events = []
        for _ in range(MAX_STEPS):
            wants = situation.read(self.world, self.mem, self.now())
            events.append(self.arbiter.step(wants, self._make))
            act = self.arbiter.current.act()
            if self.arbiter.current.end is None:
                break
        self._bandage_want()
        self._gait()
        return self._decision(inputs, wants, events, act)

    def _gait(self):
        """The Avoid's run read as a flee by Survive's sneak gait while the group sees the character (the module
        docstring)."""
        it = self.arbiter.current
        walking = getattr(it, "walking", None)
        if walking is None or not walking():
            return
        if any(situation.aware(e[2]) for e in situation.listed(self.world, self.mem, self.now()) if e[0] <= SNEAK_R):
            self.sv.mode = "flee"

    def _bandage_want(self):
        """A bleed with nothing to dress it marks the want `bandage` (the goal's loot takes one first, P24-AB)."""
        if self.mem.bandage_want:
            self.sv.need_marks["bandage"] = self.now()
        elif not situation.bleeding_parts(self.world):
            self.sv.need_marks.pop("bandage", None)

    def _decision(self, inputs, wants, events, act):
        sv = self.sv
        branch, owner, cmd, tried, cooled = act
        it = self.arbiter.current
        tried = dict(tried)
        if self.kill_now:
            tried["threat"] = dict(tried.get("threat") or {}, kill=self.kill_now[0])
            if len(self.kill_now) > 1:
                tried["threat"]["kills"] = list(self.kill_now)
        mark = getattr(sv.goals, "stuck_now", None)
        if mark is not None:
            tried["goal"] = dict(tried.get("goal") or {}, stuck_mark=mark)
        stall = getattr(sv.goals, "stall_now", None)
        if stall is not None:
            tried["goal"] = dict(tried.get("goal") or {}, stall=stall)
        inputs["need"] = sv.need_mark
        inputs["consume_refused"] = sv.consume_refused
        inputs["cooled"] = cooled
        inputs["branches"] = tried
        line = it.line()
        pre = next((e["preempted_by"] for e in events if e["preempted_by"] is not None), None)
        ended = [e["ended"] for e in events if e["ended"] is not None]
        line.update(preempted_by=pre, resumed=any(e["resumed"] for e in events),
                    ended=ended[0] if len(ended) == 1 else (ended or None),
                    slot=None if self.arbiter.slot is None else self.arbiter.slot.kind,
                    wants=[w.kind for w in wants])
        resumed_goal = self.source.last_resume
        if resumed_goal is not None:
            line["resumed_goal"] = resumed_goal[0]
        inputs["doctrine"] = line
        inputs["intent"] = it.label()
        play = it.play()
        if play is not None:
            inputs["play"] = play   # M2: where `tools/trial_score.py`'s `_labels` reads a play
        return Decision(branch, owner, cmd, inputs)


def line_switches(rows):
    """The equal-priority switches the decision lines read (review-t11-doctrine m6): consecutive lines whose
    `inputs.doctrine.n` differ at the same `p` with no `ended` on the later line; lines carrying no doctrine are
    skipped. Spec section 8's "must read zero", read off a trial's own log."""
    out, last = 0, None
    for r in rows:
        d = ((r or {}).get("inputs") or {}).get("doctrine")
        if not isinstance(d, dict):
            continue
        if last is not None and d.get("n") != last.get("n") and d.get("p") == last.get("p") and not d.get("ended"):
            out += 1
        last = d
    return out


def prepare(survive):
    """The Doctrine made before the Survive's first tick, so that tick's `_read` runs with the ladder's door read off
    too (review-t11-doctrine m3); returns it. A trial driver calls it after building a `control="doctrine"` Survive."""
    return doctrine_of(survive)


def doctrine_of(survive):
    """The Survive's Doctrine, made on its first tick."""
    d = survive.control_state.get(STATE_KEY)
    if d is None:
        d = survive.control_state[STATE_KEY] = Doctrine(survive)
    return d


def assess(survive, inputs):
    """The fork's call (`planner/control.py`): the doctrine's Decision for this tick."""
    return doctrine_of(survive).tick(inputs)


__all__ = ["assess", "Doctrine", "doctrine_of", "prepare", "line_switches", "MAX_STEPS"]
