"""The closed set of goal-failure details PZAgent_Act.lua emits (spec § 2.3), in one place for the grades.

A static set: testing/tests/pzagent/test_b_actions.py parses the `-- reasons:` header line of PZAgent_Act.lua and
asserts it equals REASONS, and greps every `"failed", "<detail>"` pair in the Act file against it, so the Lua and this
set cannot drift. "bad args" is an ack refusal (a goal's start), the rest are a running goal's failed details, except
"clear", "at" and "awake", the done details of fight, flee and sleep (Task 11), carried in the same closed line.
"""

REASONS = frozenset({
    "bad args", "no square", "no path", "stuck", "superseded", "no door", "locked", "not adjacent", "no container",
    "not loaded", "empty", "no match", "none held", "interrupted", "not valid",
    "clear", "no weapon", "weapon broke", "low health", "at", "cornered", "awake", "not allowed",
})
