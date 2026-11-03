"""The window records' one filter and one failure leg (ruling P26-7c), shared by the goal layer's window try
(`goals.window_pick`, `goal_policies`' `_window_ended`), the night's ways out (`night.window_exits`) and the Flee's
window way out (`flee.Flee._window_ended`): moved out of `goals.py` at Plan 26's close (ruling P26-R, a pure move:
the rules and their constants unchanged, their tests importing them here), so that `night`, `flee`, `goals` and
`goal_policies` import it at the top, never at a call (goals imports night, which the Flee's module serves). It
imports no planner module.

- `usable_windows(world, building, z)`: the building's windows on floor `z` a window try may take, each with its
  `locked` read.
- `note_window_end(world, sq, action)`: the reason a window action's failed end is noted under in the World.
"""

__all__ = ["WINDOW_DEAD", "WINDOW_REPEAT", "usable_windows", "note_window_end"]

WINDOW_DEAD = ("not a window", "not valid", "fell", "failed", "no square", "stalled")   # a window action's ends that
                      # leave the window out for DOOR_RETRY_MIN game minutes (World.note_window_fail); `locked` is read
                      # apart; `stalled` (the Flee's climb dropped for its hold, ruling P26-J2) is a mark, not an end
WINDOW_REPEAT = ("no path", "not adjacent", "interrupted")   # a window action's ends that are tried once more; the
                      # second within DOOR_RETRY_MIN leaves the window out like a WINDOW_DEAD end (review-t24 major 2)


def usable_windows(world, building, z):
    """`[(sq, locked)]`, the building's windows on floor `z` a window try may take (ruling P26-7c, one filter for
    `goals.window_pick` and `night.window_exits`): not barricaded and not left out by a failed end (`WINDOW_DEAD`),
    `locked` True for a record read locked or a try that ended `locked`; the order of `World.windows`."""
    out = []
    for sq in world.windows(building):
        rec = (world.map.get(sq) or {}).get("window") or {}
        fail = world.window_fail(sq)
        if sq[2] != z or rec.get("barricaded") is True or fail in WINDOW_DEAD:
            continue
        out.append((sq, rec.get("locked") is True or fail == "locked"))
    return out


def note_window_end(world, sq, action):
    """The reason a window action's failed end `action` at square `sq` is noted under (`World.note_window_fail`) and
    returned (ruling P26-7c, one failure leg for the goal layer's `_window_ended` and the Flee's): the end's reason,
    else its state; review-t24 major 2: a smash try refused `locked` (a barricade or a frame a smash cannot cure), a
    second `locked`, or a second `WINDOW_REPEAT` end within DOOR_RETRY_MIN leaves the window out for good (`failed`).
    A `locked` end of an unsmashed try is noted `locked` (so the next try smashes)."""
    reason = action.reason or action.state
    prior = world.window_fail(sq)
    if reason == "locked" and (action.args.get("smash") is True or prior == "locked"):
        reason = "failed"
    elif reason in WINDOW_REPEAT and prior == reason:
        reason = "failed"
    world.note_window_fail(sq, reason)
    return reason
