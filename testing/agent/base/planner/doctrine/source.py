"""The doctrine's goal source (Plan 31 Task 11, the variant D): `Resume`, laid over the session's own source (the
scripted one or the model's `LLMSource`) on the doctrine's first tick, so the goal runner (`goal_runner.GoalRunner`,
unedited) runs the standing order with two rules more:

- The resume: a goal the runner closed `superseded` (an intent above the order sent over it, or the order's own need
  step; F15: 16 of its 20 model goals ended so) is queued (`note`, the newest only: one deep, as the arbiter's slot),
  and the runner's next ask gets it back, built again from its row (`goal_runner.validate`), before the inner source is
  asked: a Loot resumes after a Strike. One goal (its type and args) is resumed at most RESUME_MAX times; a Rest is
  never resumed (it is the order's idle, not a place).
- The prefetch (`prefetch`, called by the Order while a LootBuilding runs): the model's next order is asked while the
  loot runs, at most once every PREFETCH_S, so its latency (F15: p50 4.51 s) is spent looting; an answer is held and
  handed to the runner's next ask. Only for a source named `llm` (the scripted one answers at once). The held answer was
  checked against the view of its own ask (the LLMSource's rule), not the view of the tick it is used on.

Every other attribute is the inner source's (`__getattr__`), so a driver reading `totals()`, `calls` or `join` reads the
model's own, and `NAME` is the inner source's own at each read (review-t11-doctrine M4: `LLMSource` names a stand-in's
goal "scripted" on its instance, so the runner's history, its line and P30-B's hop read the real source). A held
prefetch is checked again against the asking view before it is handed over (`llm.place_error`, M3: a building looted
meanwhile, F7's "looted already"), and dropped on a refusal."""
from agent.base.planner.doctrine.constants import PREFETCH_S, RESUME_MAX
from agent.base.planner.goal_runner import validate
from agent.base.planner.goals import goal_key
from agent.base.planner.llm import place_error

NEVER = ("Rest",)   # goal types never resumed


class Resume:
    """The resume and the prefetch over the session's source (the module docstring)."""

    def __init__(self, inner):
        self.inner = inner
        self.queued = None      # the row of the last goal closed superseded, until the next ask
        self.held = None        # a prefetched goal, until the next ask
        self.resumed = {}       # goal key -> times resumed
        self.last_resume = None   # the key of the goal the last ask resumed, else None
        self._asked = None      # wall of the last prefetch ask
        self.dropped = None     # the last held prefetch's refusal against the view at hand, else None

    def __getattr__(self, name):
        if name == "inner":
            raise AttributeError(name)
        return getattr(self.inner, name)

    def note(self, row):
        """A row of the runner's history: queued when it ended `superseded` and may be resumed."""
        if row.get("state") != "superseded" or row.get("type") in NEVER:
            return
        if self.resumed.get(goal_key(row.get("type"), row.get("args")), 0) >= RESUME_MAX:
            return
        self.queued = row

    def propose(self, view):
        """The queued goal built again, else the held prefetch, else the inner source's answer."""
        self.last_resume = None
        row, self.queued = self.queued, None
        if row is not None:
            try:
                g = validate(dict(row.get("args") or {}, type=row.get("type")))
            except ValueError:
                g = None
            if g is not None:
                key = goal_key(g.TYPE, g.args())
                self.resumed[key] = self.resumed.get(key, 0) + 1
                self.last_resume = key
                return g
        if self.held is not None:
            g, self.held = self.held, None
            v = view if isinstance(view, dict) else {}
            if place_error(g, v, v.get("pos")) is None:
                return g
            self.dropped = place_error(g, v, v.get("pos"))   # refused against the view at hand: asked again
        return self.inner.propose(view)

    def prefetch(self, view_fn, now):
        """Ask the model for the next order while a loot runs (the module docstring); None."""
        if getattr(type(self.inner), "NAME", None) != "llm" or self.held is not None or self.queued is not None:
            return
        if self._asked is not None and now - self._asked < PREFETCH_S:
            return
        self._asked = now
        g = self.inner.propose(view_fn())
        if g is not None:
            self.held = g
