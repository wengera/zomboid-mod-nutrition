"""mix_2's tick (Plan 31 Task 13): `assess(survive, inputs)`, the fork's call (`planner/control.py`), over one `Mix2`
kept on `survive.control_state["mix_2"]`.

`Mix2` is the doctrine's `Doctrine` (`doctrine/assess.py`: its bookkeeping, the kills, the skips and the back-offs, the
retired maneuvers, the bandage want, the Avoid's gait, `source.Resume` laid over the goal runner's source with its
resume and prefetch, the ladder's P30-C door read off on this Survive) with three things of its own:
- the wants are mix_2's (`situation.read`), the lone-idle seek's reachability read through its own `seek.Reach`;
- the intents are mix_2's (`intents.INTENTS`: its Fight and Dress, D's Avoid, Door and Order);
- the decision line carries `inputs.mix_2` (D's `inputs.doctrine` keys: `intent`, `p`, `why`, `state`, `target`,
  `n`, `preempted_by`, `resumed`, `ended`, `slot`, `wants`, with an order's `step` and `resumed_goal`; and `piece`, the
  rule that started the running intent, `pieces`, the pieces of this tick's wants, and a Fight's `repin` {id, by} on its
  `done repin`), never `inputs.doctrine`, so a trial's lines are told apart by key; `inputs.intent` {kind, target} is
  the scorecard's label as D's (`tools/trial_score.py`).

No tactical model is asked: the model stays strategic through the doctrine's Order (the goal runner's source)."""
from agent.base.planner.doctrine.assess import MAX_STEPS, Doctrine
from agent.base.planner.mix_2 import situation
from agent.base.planner.mix_2.intents import INTENTS, piece_of
from agent.base.planner.mix_2.seek import Reach

STATE_KEY = "mix_2"
LINE_KEY = "mix_2"


class Mix2(Doctrine):
    """The doctrine's arbiter over mix_2's wants and intents (the module docstring)."""

    def __init__(self, sv):
        super().__init__(sv)
        self.reach = Reach(sv.world, sv.clock)

    def _make(self, want, prev):
        return INTENTS[want.kind](self, want, prev)

    def _seek(self):
        """The lone-idle seek's reachability, None while the night's Sleep runs (the ladder's `_sought`: a sleeper is
        woken only by what comes near)."""
        if self.sv._sleeping() is not None:
            return None
        self.reach.world = self.world
        return self.reach.engageable

    def read(self):
        return situation.read(self.world, self.mem, self.now(), self._seek())

    def tick(self, inputs):
        """D's tick (`Doctrine.tick`) over mix_2's read."""
        sv = self.sv
        sv.need_mark = None
        sv.mode = None
        self.ticks += 1
        self._bookkeeping()
        events = []
        for _ in range(MAX_STEPS):
            wants = self.read()
            events.append(self.arbiter.step(wants, self._make))
            act = self.arbiter.current.act()
            if self.arbiter.current.end is None:
                break
        self._bandage_want()
        self._gait()
        return self._decision(inputs, wants, events, act)

    def _decision(self, inputs, wants, events, act):
        decision = super()._decision(inputs, wants, events, act)
        line = inputs.pop("doctrine")
        line["piece"] = piece_of(self.arbiter.current)
        line["pieces"] = [situation.piece_of(w) for w in wants]
        inputs[LINE_KEY] = line
        return decision


def line_switches(rows):
    """The equal-priority switches mix_2's lines read (D's `doctrine.assess.line_switches` over `inputs.mix_2`):
    consecutive lines whose serial `n` differs at the same `p` with no `ended` on the later line."""
    out, last = 0, None
    for r in rows:
        d = ((r or {}).get("inputs") or {}).get(LINE_KEY)
        if not isinstance(d, dict):
            continue
        if last is not None and d.get("n") != last.get("n") and d.get("p") == last.get("p") and not d.get("ended"):
            out += 1
        last = d
    return out


def prepare(survive):
    """The variant's construction hook (the fork's `prepare_of`): D's (`doctrine.assess.prepare`), the ladder's P30-C
    door read off at once, the Mix2 made once the Survive carries its goal runner."""
    survive.DOOR_HELD = False
    if getattr(survive, "goals", None) is None or getattr(survive, "control_state", None) is None:
        return None
    return mix_of(survive)


def mix_of(survive):
    """The Survive's Mix2, made on its first tick."""
    m = survive.control_state.get(STATE_KEY)
    if m is None:
        m = survive.control_state[STATE_KEY] = Mix2(survive)
    return m


def assess(survive, inputs):
    """The fork's call (`planner/control.py`): mix_2's Decision for this tick."""
    return mix_of(survive).tick(inputs)


__all__ = ["assess", "prepare", "Mix2", "mix_of", "line_switches", "STATE_KEY", "LINE_KEY"]
