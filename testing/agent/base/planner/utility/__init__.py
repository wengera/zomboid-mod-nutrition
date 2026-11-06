"""The situation utility (Plan 31 Task 11, the variant U; the proposal `rebuild-proposal-situation-utility.md`, the
spec's § 3): a selector about once a second plus five interrupts, scoring six to ten candidate acts by the expected
kill value, the expected hits, the bleed over the act's span and the goal's progress, the held act replaced only by a
margin after a minimum span. `Survive(control="utility")` calls `assess(survive, inputs)` each tick in place of the
ladder (`planner/control.py`); the README is the design in one page.

Modules: `features` (the frame's readings), `models` (the hit hazard and the kill chance, fitted), `weights` (K, B,
C, G, V, the dial registry with each feasible interval), `acts` (the candidates), `select` (the terms, the scores,
the commitment), `execute` (the executors over the shared plays), `core` (the tick), `replay` (the offline replay and
the goldens).
"""
from agent.base.planner.utility.core import STATE_KEY, Utility


def assess(survive, inputs):
    """The fork's `assess`: the Utility kept on `survive.control_state[STATE_KEY]`, made on the first tick."""
    u = survive.control_state.get(STATE_KEY)
    if u is None:
        u = survive.control_state[STATE_KEY] = Utility(survive)
    return u.assess(inputs)
