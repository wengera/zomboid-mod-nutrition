"""The cached table (Plan 31 Task 11, variant T; the proposal § 5 "The cached table"): the doctrine plus the model's
offline labels on discretised situations, read at zero latency.

- The situation (`key(view) -> str`): the standing count within DANGER_R by band (0, 1, 2, 3+), a standing zombie
  within KEEP_R, a group (`fallback.is_group`), armed, a health band (`lo` under 40, `mid` under 70, `hi`), a bleed
  that can be dressed (`rubric.dress_due`'s bleed with something held), a door between (the nearest standing zombie's
  `line` reads `door`), inside or outside: the proposal's bands, with the reach and the group added because the
  doctrine's rules turn on them (fallback.RULES `reach`, `group`).
- Where Angus's rules bind (`rubric.fight_due`: one standing zombie within DANGER_R, armed; `rubric.dress_due`: a bleed
  with nothing standing within KEEP_R and something to dress with) the doctrine answers, whatever a cell holds: the
  model's labels fill the ambiguous middle only (the proposal's weakest point: "the model earns its place only in the
  ambiguous middle"), so the table never breaks a rule the doctrine keeps.
- Elsewhere a cell holds a play type. `Table.answer(view)` reads the view's cell: a labelled cell's play with the
  fallback's own target for it (`fallback.target_for`), else (an empty cell, or a play the view admits no target for)
  the doctrine's answer (`fallback.doctrine`); `(source, rule_or_key, answer)`, `source` "table" or "doctrine".
- The labels come from the bench (`tools/tactician_bench.py`): each cell the majority play type of the model's valid
  answers on the bench's views in it where no rule binds (ties to the doctrine's play, then by name). `table.json` beside this module is
  the committed table, `{key: play}`; `Table.load()` reads it (an absent file is the doctrine alone)."""
import json
import os

from agent.base.planner.policies import DANGER_R, KEEP_R, LISTED_R
from agent.base.planner.tactician import fallback as F
from agent.base.planner.tactician import rubric as R

HERE = os.path.dirname(os.path.abspath(__file__))
TABLE_PATH = os.path.join(HERE, "table.json")
HEALTH_BANDS = ((40.0, "lo"), (70.0, "mid"))   # health under 40 / under 70 / else hi (policies.FLEE_HEALTH 40 and
                                               # FLEE_HEALTH_PAIR 60 rounded up: the ladder's two health lines)


def _band(n):
    return str(n) if n < 3 else "3+"


def _health(view):
    h = (view.get("me") or {}).get("health")
    h = 100.0 if h is None else h
    return next((name for t, name in HEALTH_BANDS if h < t), "hi")


def key(view):
    """The situation's cell (the module docstring), as a stable string."""
    s6 = F._standing(view, DANGER_R)
    keep = bool(F._standing(view, KEEP_R))
    near = F._standing(view, LISTED_R)
    door = bool(near) and near[0].get("line") == "door"
    parts = ("s" + _band(len(s6)), "k%d" % keep, "g%d" % F.is_group(view), "a%d" % F.armed(view),
             "h" + _health(view), "b%d" % R.dress_due(view), "d%d" % door,
             "i%d" % bool((view.get("me") or {}).get("inside")))
    return "|".join(parts)


def bound(view):
    """One of Angus's rules binds the view (the module docstring): the doctrine answers it."""
    return R.fight_due(view) or R.dress_due(view)


class Table:
    """The cached table (the module docstring)."""

    def __init__(self, cells=None):
        self.cells = dict(cells or {})

    @classmethod
    def load(cls, path=TABLE_PATH):
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, ValueError):
            return cls()
        return cls(data.get("cells") if isinstance(data, dict) else None)

    @classmethod
    def fit(cls, rows):
        """A table from `rows` of (view, model answer or None): each cell the majority play of its valid answers,
        ties to the doctrine's play, then by name."""
        votes = {}
        for view, ans in rows:
            if ans is None or bound(view):
                continue
            k = key(view)
            votes.setdefault(k, {"doctrine": (F.doctrine(view)[1] or {}).get("play"), "n": {}})
            n = votes[k]["n"]
            n[ans["play"]] = n.get(ans["play"], 0) + 1
        cells = {}
        for k, v in votes.items():
            top = max(v["n"].values())
            best = sorted(p for p, c in v["n"].items() if c == top)
            cells[k] = v["doctrine"] if v["doctrine"] in best else best[0]
        return cls(cells)

    def answer(self, view):
        """(source, rule or key, flat answer or None) for `view` (the module docstring)."""
        k = key(view)
        play = None if bound(view) else self.cells.get(k)
        if play is not None:
            ans = F.target_for(play, view)
            if ans is not None:
                return "table", k, ans
        rule, ans = F.doctrine(view)
        return "doctrine", rule, ans

    def save(self, path=TABLE_PATH, meta=None):
        data = dict(meta or {}, cells={k: self.cells[k] for k in sorted(self.cells)})
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            json.dump(data, f, indent=1, sort_keys=True)
            f.write("\n")
