"""The closed sets of goal details PZAgent_Act.lua emits (spec § 2.3), in one place for the grades.

Static sets: testing/tests/pzagent/test_b_actions.py parses the `-- reasons:` and `-- done:` header lines of
PZAgent_Act.lua and asserts they equal REASONS and DONE, greps every `"failed", "<detail>"` pair in the Act file against
REASONS and every `"done", "<detail>"` pair against DONE, and asserts the two sets are disjoint, so the Lua and these sets
cannot drift.

REASONS: the failed details, plus the ack refusals "bad args" (a goal's start) and "dead" (Stage A pass 2: both an ack
refusal of any goal and a running goto's failed detail). gate_b grades on REASONS alone.
DONE: the done details. "d=" (goto, then its distance) and "moved=" (loot, then a count) are prefixes; stop's done
detail is empty and is not listed.
"""

REASONS = frozenset({
    "bad args", "no square", "no path", "stuck", "superseded", "no door", "locked", "not adjacent", "no container",
    "not loaded", "empty", "no match", "none held", "interrupted", "not valid",
    "no weapon", "weapon broke", "low health", "cornered", "not allowed", "dead",
})

DONE = frozenset({"d=", "moved=", "open", "consumed", "clear", "at", "awake"})
