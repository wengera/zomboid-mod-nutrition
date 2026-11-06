"""The five weights of the situation utility (Plan 31 Task 11 U; the proposal's § 5 stage 2), a dial registry: each
weight's value, its feasible interval from the linear program over the verdict set (`tools/utility_fit.py`, its
compact artifact `data/fits/utility-weights.json`: `intervals` and `chosen`), its unit and its source. H, the cost of
one hit, is the unit every weight is read in (1, never a dial).

A weight moves only inside its interval (the proposal's § 5 stage 3: a session's wound analysis names the line, the
act, the runner-up and the margin, and tunes a weight as a dial within it); `test_utility_fit.py` pins every value to
the artifact's chosen point and inside its interval, and the chosen point to the tool's `--check`.

- K, the kill's worth in hits (memory `hits-per-kill-metric`: at K = 1 a fight is taken only when its expected kills
  exceed its expected hits).
- B, a bleeding part-minute's cost in hits (memory `stand-and-fight-dress-first`: the dressing first).
- C, the chase credit: a fight at a standing chaser while armed (the same memory: one zombie is never fled).
- G, the regress: a retreat's ten tiles off the way, in hits.
- V, the goal's progress over the travel's horizon, in hits (memory `clear-then-loot-strategy`).
"""
import dataclasses

H = 1.0   # the cost of one hit: the unit


@dataclasses.dataclass(frozen=True)
class Dial:
    value: float
    lo: float
    hi: float
    unit: str
    source: str


# The values are the linear program's chosen point; the intervals its feasible ones (`data/fits/utility-weights.json`).
FIT = "data/fits/utility-weights.json, lp"
WEIGHTS = {
    "K": Dial(0.503151335, 0.0, 4.903087796, "hits per kill",
              FIT + " (at its lower bound 0; no direction sets it: the artifact's `unset`)"),
    "B": Dial(1.228502656, 0.28640423, 3.236459563, "hits per bleeding part-minute", FIT),
    "C": Dial(3.473035325, 0.0, 4.992137631, "hits per fight at a chaser", FIT + " (at its lower bound 0)"),
    "G": Dial(1.320235198, 0.0, 3.450900685, "hits per ten tiles run off", FIT + " (at its lower bound 0)"),
    "V": Dial(0.503151335, 0.0, 1.899793811, "hits per goal horizon",
              FIT + " (at its lower bound 0; no direction sets it: the artifact's `unset`)"),
}
# The fit's caps on K and C follow the drag-down's first-guess price `select.DRAG_HITS` (the artifact's
# `lp.drag_probe`: K's upper end 1.66, 3.56, 4.90, 8.16 and C's 2.99, 3.99, 4.99, 7.99 at 1, 2, 3, 6 hits).
NAMES = tuple(WEIGHTS)


def values(overrides=None):
    """{name: value} with H, `overrides` laid over (a test's or the fit's point)."""
    out = {k: d.value for k, d in WEIGHTS.items()}
    out["H"] = H
    if overrides:
        out.update(overrides)
    return out
