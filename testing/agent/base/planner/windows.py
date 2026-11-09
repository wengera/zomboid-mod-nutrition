"""The window records' one filter and one failure leg (ruling P26-7c), shared by the goal layer's window try
(`goals.window_pick`, `goal_policies`' `_window_ended`), the night's ways out (`night.window_exits`) and the Flee's
window way out (`flee.Flee._window_ended`): moved out of `goals.py` at Plan 26's close (ruling P26-R, a pure move:
the rules and their constants unchanged, their tests importing them here), so that `night`, `flee`, `goals` and
`goal_policies` import it at the top, never at a call (goals imports night, which the Flee's module serves). It
imports no planner module.

- `usable_windows(world, building, z)`: the building's windows on floor `z` a window try may take, each with its
  `locked` read.
- `note_window_end(world, sq, action)`: the reason a window action's failed end is noted under in the World.
- The glass (Plan 32 Task 6, the jar rows T101.1-T101.3 on docs/platform/agent.md; Angus's direction of 2026-11-08,
  memory `window-broken-glass`): a climb through a smashed window whose broken glass is in cuts a hand or a forearm 1
  time in 2 (#4366; T101.2: 10 damage, a deep shard wound 1 time in 7, else a scratch), and vanilla's
  ISRemoveBrokenGlass removes the glass with no glove or held-item test (T101.3). The map's window record carries
  `glass` (PZA/1.11's windowPortal: smashed and not glass-removed; None on an older record or an unread getter, which
  gates nothing). `GLASS_CLEAR` on: a window reading glass stays usable and its command carries `clear` true (the
  Lua's window act removes the glass before the climb); off: `usable_windows` leaves it out. `clear_for(world, sq,
  smash)`: the command's `clear`, true also for a smash (the act's own smash leaves the glass in, and the act fails a
  climb into glass without clear). `window_cmd(world, sq, smash)`: the `Window` command every sender builds (the goal
  layer's window route, the Flee's window way out). A `glass` end (the act's refusal) is a `WINDOW_DEAD` end: the
  window is left for another way.
"""

from agent.base.pza1 import Window

__all__ = ["WINDOW_DEAD", "WINDOW_REPEAT", "GLASS_CLEAR", "usable_windows", "note_window_end", "glass_of", "clear_for",
           "window_cmd"]

WINDOW_DEAD = ("not a window", "not valid", "fell", "failed", "no square", "stalled", "glass")   # a window action's
                      # ends that leave the window out for DOOR_RETRY_MIN game minutes (World.note_window_fail); `locked`
                      # is read apart; `stalled` (the Flee's climb dropped for its hold, ruling P26-J2) is a mark, not an
                      # end; `glass` (Plan 32 Task 6): the act refused or failed a climb into broken glass without clear
GLASS_CLEAR = True   # Plan 32 Task 6 (the module docstring): a window reading glass is climbed with clear true, the
                     # glass removed first; off, it is left out of `usable_windows`
WINDOW_REPEAT = ("no path", "not adjacent", "interrupted")   # a window action's ends that are tried once more; the
                      # second within DOOR_RETRY_MIN leaves the window out like a WINDOW_DEAD end (review-t24 major 2)


def usable_windows(world, building, z):
    """`[(sq, locked)]`, the building's windows on floor `z` a window try may take (ruling P26-7c, one filter for
    `goals.window_pick` and `night.window_exits`): not barricaded and not left out by a failed end (`WINDOW_DEAD`),
    `locked` True for a record read locked or a try that ended `locked`; the order of `World.windows`. Plan 32 Task 6:
    a record reading `glass` true is left out unless `GLASS_CLEAR` (its climb then clears it, `clear_for`)."""
    out = []
    for sq in world.windows(building):
        rec = (world.map.get(sq) or {}).get("window") or {}
        fail = world.window_fail(sq)
        if sq[2] != z or rec.get("barricaded") is True or fail in WINDOW_DEAD:
            continue
        if rec.get("glass") is True and not GLASS_CLEAR:
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


def glass_of(world, sq):
    """The map's window record at square `sq` (x, y, z): its `glass` (PZA/1.11, T101.1: smashed with the broken glass
    in), True or False, None when unread (no record, a record written before PZA/1.11, a getter the Lua could not
    read)."""
    return ((world.map.get(sq) or {}).get("window") or {}).get("glass")


def clear_for(world, sq, smash=False):
    """The window command's `clear` at square `sq` (the module docstring): `GLASS_CLEAR` and the record reading glass
    or the command smashing (the act's own smash leaves the glass in, T101.2)."""
    return GLASS_CLEAR and (glass_of(world, sq) is True or smash is True)


def window_cmd(world, sq, smash=False):
    """The `Window` command at square `sq` (x, y, z) with `smash` and `clear_for`'s `clear` (left off the wire when
    false): the one builder of the goal layer's window route and the Flee's window way out."""
    return Window(sq[0], sq[1], smash=smash, clear=clear_for(world, sq, smash))
