"""Plan 21's closed sets of goal details, frozen with the Plan 21 grades and drivers that import them.

The Plan 21 Lua goal machines that emitted these details were removed in Plan 22 (the multi-step policies moved to
`agent/base/planner/policies.py`), so nothing emits them now: the sets stay as the frozen `grades.gate_b`
(`agent/grades.py`), `agent/grade_c.py` and `drivers/b_actions.py` read them, to regrade the Plan 21 artifacts.
The Plan 22 base's failure reasons are `pza1.REASONS` (`agent/base/pza1.py`, generated from the PZA/1 schema).

REASONS: the failed details, plus the ack refusals "bad args" (a goal's start) and "dead" (Stage A pass 2: both an ack
refusal of any goal and a running goto's failed detail). gate_b grades on REASONS alone.
DONE: the done details. "d=" (goto, then its distance) and "moved=" (loot, then a count) are prefixes; stop's done
detail is empty and is not listed.

Ruling S-27 (Plan 22's fix wave, the whole-pass review's M12): a docstring-only edit of a frozen file is allowed when it
names code that no longer exists; the code below is unchanged.
"""

REASONS = frozenset({
    "bad args", "no square", "no path", "stuck", "superseded", "no door", "locked", "not adjacent", "no container",
    "not loaded", "empty", "no match", "none held", "interrupted", "not valid",
    "no weapon", "weapon broke", "low health", "cornered", "not allowed", "dead",
})

DONE = frozenset({"d=", "moved=", "open", "consumed", "clear", "at", "awake"})
