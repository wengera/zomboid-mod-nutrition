"""PZA/1.6's window {x, y, smash} (Plan 24 Task 9 fix 9, ruling P24-Z: the route takes a window when the doors are
stuck) on the lupa host: a walk to the window's near side, then vanilla's ISOpenCloseWindow or, with smash true,
ISSmashWindow, then ISClimbThroughWindow; done {smashed, opened, cut, wounds} across the edge. The jar reads are
docs/superpowers/specs/2026-10-29-plan-24-jar-reads-2.md section 10. The fake vanilla queue never runs an action: a
test empties it (the action left the queue) and moves the player as the engine would."""
from .conftest import J, make_cell, make_player
from .test_lua_sense import load
from .test_lua_skills import acts, start, states, tick


def window(open_=False, smashed=False, locked=False, perma=False, barricaded=False, north=True, far_ok=True,
           cls="IsoWindow"):
    """A window whose state is .st: canClimbThrough(p) holds while it is open or smashed and its far side stands."""
    st = {"open": open_, "smashed": smashed, "locked": locked, "perma": perma}
    w = J(_cls=cls, getNorth=lambda s: north, IsOpen=lambda s: st["open"], isSmashed=lambda s: st["smashed"],
          isLocked=lambda s: st["locked"], isPermaLocked=lambda s: st["perma"], isBarricaded=lambda s: barricaded,
          canClimbThrough=lambda s, p: far_ok and (st["open"] or st["smashed"]))
    w.st = st
    return w


def win_world(lua, w, x=11, y=20):
    """The window on square (x, y) and open squares round it."""
    squares = {}
    for dx in (-2, -1, 0, 1, 2):
        for dy in (-2, -1, 0, 1, 2):
            objs = [w] if (dx, dy) == (0, 0) and w is not None else []
            squares[(x + dx, y + dy, 0)] = J(getObjects=lambda s, o=objs: J(size=lambda s2: len(o),
                                                                            get=lambda s2, i: o[i]),
                                              isSolid=lambda s: False, isSolidTrans=lambda s: False)
    lua.globals()._cell = make_cell(squares=squares)


def mover(p, x, y):
    pos = {"x": x, "y": y}
    p.getX, p.getY = (lambda s: pos["x"]), (lambda s: pos["y"])
    return pos


def wounds(p):
    """The body damage's scratched count as a mutable cell (the climb's cut reads its rise)."""
    n = {"v": 0}
    bd = p.getBodyDamage(p)
    bd.getNumPartsScratched = lambda s: n["v"]
    return n


def host(lua, w, x=11.5, y=18.5):
    load(lua)
    lua.execute("PZA.link.init('admin')")
    win_world(lua, w)
    p = make_player()
    pos = mover(p, x, y)
    return p, pos, lua.globals()


def leave(g):
    """The queued actions left the vanilla queue (the walk and the action ran)."""
    g._queue.queue[:] = []


def types(g):
    return [a.Type for a in g._queue.adds]


def test_the_open_path_walks_to_the_near_side_opens_climbs_and_is_done(lua, fs):
    w = window()
    p, pos, g = host(lua, w)
    start(lua, p, "window", x=11, y=20)
    tick(lua, p)
    assert types(g) == ["ISWalkToTimedAction", "ISOpenCloseWindow"]
    assert g._queue.adds[0].sq is not None and g._queue.adds[1].object is w
    tick(lua, p)
    assert states(acts(lua, fs))[-1] == ("a1", "accepted", "")
    pos["y"] = 19.5                                              # at the near square (11, 19)
    leave(g)
    w.st["open"] = True
    tick(lua, p)
    assert types(g)[-1] == "ISClimbThroughWindow" and g._windows[-1] == ("climb", p, w, 0)
    tick(lua, p)
    assert states(acts(lua, fs))[-1] == ("a1", "accepted", "")
    pos["y"] = 20.5                                              # through: the far square (11, 20)
    tick(lua, p)
    a = acts(lua, fs)
    assert states(a)[-1] == ("a1", "done", "")
    assert a[-1]["result"] == {"smashed": False, "opened": True, "cut": False, "wounds": 0}


def test_an_open_window_is_climbed_at_once(lua, fs):
    w = window(open_=True)
    p, pos, g = host(lua, w, y=19.5)
    start(lua, p, "window", x=11, y=20)
    tick(lua, p)
    assert types(g) == ["ISClimbThroughWindow"]
    pos["y"] = 20.5
    tick(lua, p)
    assert acts(lua, fs)[-1]["result"] == {"smashed": False, "opened": False, "cut": False, "wounds": 0}


def test_the_smash_path_with_smash_true_smashes_climbs_and_reports_the_cut(lua, fs):
    w = window(locked=True, perma=True)
    p, pos, g = host(lua, w, y=19.5)
    n = wounds(p)
    start(lua, p, "window", x=11, y=20, smash=True)
    tick(lua, p)
    assert types(g) == ["ISSmashWindow"] and g._windows[-1] == ("smash", p, w)
    leave(g)
    w.st["smashed"] = True
    tick(lua, p)
    assert types(g)[-1] == "ISClimbThroughWindow"
    n["v"] = 1                                                   # the glass cut a hand on the way through
    pos["y"] = 20.5
    tick(lua, p)
    a = acts(lua, fs)
    assert states(a)[-1] == ("a1", "done", "")
    assert a[-1]["result"] == {"smashed": True, "opened": False, "cut": True, "wounds": 1}


def test_a_scratch_before_the_climb_is_queued_is_not_the_climbs_cut(lua, fs):
    w = window(locked=True, perma=True)
    p, pos, g = host(lua, w, y=19.5)
    n = wounds(p)
    start(lua, p, "window", x=11, y=20, smash=True)
    tick(lua, p)
    n["v"] = 1                                                   # the weaponless smash scratches the smasher (ISSmashWindow:55)
    leave(g)
    w.st["smashed"] = True
    tick(lua, p)
    assert types(g)[-1] == "ISClimbThroughWindow"
    pos["y"] = 20.5
    tick(lua, p)
    a = acts(lua, fs)
    assert a[-1]["result"] == {"smashed": True, "opened": False, "cut": False, "wounds": 0}


def test_a_perma_locked_window_without_smash_is_refused_locked(lua, fs):
    p, _, g = host(lua, window(locked=True, perma=True))
    start(lua, p, "window", x=11, y=20)
    assert states(acts(lua, fs)) == [("a1", "rejected", "locked")] and g._queue.adds == []


def test_an_open_that_locks_for_good_fails_locked_or_smashes_with_smash(lua, fs):
    w = window(locked=True)
    p, pos, g = host(lua, w, y=19.5)
    start(lua, p, "window", aid="o", x=11, y=20)
    tick(lua, p)
    assert types(g) == ["ISOpenCloseWindow"]
    leave(g)
    w.st["perma"] = True                                         # the struggle broke the lock
    tick(lua, p)
    assert states(acts(lua, fs))[-1] == ("o", "failed", "locked")
    w.st["perma"] = False
    start(lua, p, "window", aid="s", x=11, y=20, smash=True)
    tick(lua, p)
    leave(g)
    w.st["perma"] = True
    cleared = g._queue.cleared
    tick(lua, p)
    assert types(g)[-1] == "ISSmashWindow" and g._queue.cleared == cleared + 1
    assert states(acts(lua, fs))[-1] == ("s", "accepted", "")


def test_an_open_still_shut_past_its_budget_fails_locked(lua, fs):
    w = window(locked=True)
    p, _, g = host(lua, w, y=19.5)
    start(lua, p, "window", x=11, y=20)
    tick(lua, p)
    leave(g)
    tick(lua, p)
    g._clock["ms"] += lua.eval("PZA.skills.WINDOW_OPEN_MS")
    tick(lua, p)
    assert states(acts(lua, fs))[-1] == ("a1", "failed", "locked")


def test_a_smash_that_never_breaks_the_glass_is_interrupted(lua, fs):
    w = window(perma=True)
    p, _, g = host(lua, w, y=19.5)
    start(lua, p, "window", x=11, y=20, smash=True)
    tick(lua, p)
    leave(g)
    tick(lua, p)
    g._clock["ms"] += lua.eval("PZA.skills.WINDOW_SMASH_MS")
    tick(lua, p)
    assert states(acts(lua, fs))[-1] == ("a1", "failed", "interrupted")


def test_a_fall_through_the_window_fails_fell(lua, fs):
    w = window(open_=True)
    p, pos, g = host(lua, w, y=19.5)
    start(lua, p, "window", x=11, y=20)
    tick(lua, p)
    p.variables["ClimbWindowOutcome"] = "fallfront"
    tick(lua, p)
    pos["y"] = 20.5
    tick(lua, p)
    assert states(acts(lua, fs))[-1] == ("a1", "failed", "fell")


def test_a_climb_gone_from_the_queue_with_the_player_on_the_near_side_fails(lua, fs):
    w = window(open_=True)
    p, _, g = host(lua, w, y=19.5)
    start(lua, p, "window", x=11, y=20)
    tick(lua, p)
    leave(g)
    tick(lua, p)
    g._clock["ms"] += lua.eval("PZA.skills.WINDOW_SETTLE_MS")
    tick(lua, p)
    assert states(acts(lua, fs))[-1] == ("a1", "failed", "failed")


def test_an_open_left_with_the_player_away_from_the_window_fails_not_adjacent(lua, fs):
    w = window()
    p, pos, g = host(lua, w, y=14.5)
    start(lua, p, "window", x=11, y=20)
    tick(lua, p)
    leave(g)                                                     # the walk gave up where it stood
    tick(lua, p)
    assert states(acts(lua, fs))[-1] == ("a1", "failed", "not adjacent")


def test_the_whole_budget_interrupts(lua, fs):
    w = window()
    p, _, g = host(lua, w, y=19.5)
    start(lua, p, "window", x=11, y=20)
    tick(lua, p)
    g._clock["ms"] += lua.eval("PZA.skills.WINDOW_MS")
    tick(lua, p)
    assert states(acts(lua, fs))[-1] == ("a1", "failed", "interrupted")


def test_the_west_edge_window_takes_the_west_near_square(lua, fs):
    w = window(north=False)
    p, pos, g = host(lua, w, x=8.5, y=20.5)
    start(lua, p, "window", x=11, y=20)
    tick(lua, p)
    walk = g._queue.adds[0]
    assert walk.Type == "ISWalkToTimedAction"
    assert lua.eval("PZA.skills.cur.st.nx") == 10 and lua.eval("PZA.skills.cur.st.ny") == 20


def test_window_refusals(lua, fs):
    p, _, g = host(lua, window())
    start(lua, p, "window", aid="ba", x="x", y=20)
    start(lua, p, "window", aid="bs", x=11, y=20, smash="yes")
    start(lua, p, "window", aid="ns", x=50, y=50)
    start(lua, p, "window", aid="nw", x=10, y=20)
    win_world(lua, window(barricaded=True))
    start(lua, p, "window", aid="br", x=11, y=20)
    win_world(lua, window(open_=True, far_ok=False))
    start(lua, p, "window", aid="nv", x=11, y=20)
    frame_ = J(_cls="IsoWindowFrame", getNorth=lambda s: True, canClimbThrough=lambda s, q: False)
    win_world(lua, frame_)
    start(lua, p, "window", aid="fr", x=11, y=20)
    assert states(acts(lua, fs)) == [("ba", "rejected", "bad args"), ("bs", "rejected", "bad args"),
                                     ("ns", "rejected", "no square"), ("nw", "rejected", "not a window"),
                                     ("br", "rejected", "locked"), ("nv", "rejected", "not valid"),
                                     ("fr", "rejected", "locked")]


def test_a_window_frame_that_can_be_climbed_is_climbed(lua, fs):
    fr = J(_cls="IsoWindowFrame", getNorth=lambda s: True, canClimbThrough=lambda s, q: True)
    p, pos, g = host(lua, fr, y=19.5)
    start(lua, p, "window", x=11, y=20)
    tick(lua, p)
    assert types(g) == ["ISClimbThroughWindow"] and g._windows[-1][2] is fr


def test_the_climb_class_absent_fails_not_loaded(lua, fs):
    p, _, g = host(lua, window(open_=True), y=19.5)
    g.ISClimbThroughWindow = None
    start(lua, p, "window", x=11, y=20)
    tick(lua, p)
    assert states(acts(lua, fs))[-1] == ("a1", "failed", "not loaded")


def test_window_is_an_action_of_the_schema_and_a_held_stance_is_released(lua, fs):
    from agent.base import pza1
    p, _, g = host(lua, window(open_=True), y=19.5)
    assert "window" in pza1.ACTION_TYPES and pza1.ACTION_ARGS["window"] == {"x": "int", "y": "int", "smash": "bool"}
    assert pza1.Window(x=1, y=2).args() == {"x": 1, "y": 2} and pza1.Window(x=1, y=2, smash=True).args()["smash"] is True
    assert "not a window" in pza1.REASONS
    lua.execute("PZA.skills.stance.held = true")
    start(lua, p, "window", x=11, y=20)
    assert lua.eval("PZA.skills.stance.held") is False
