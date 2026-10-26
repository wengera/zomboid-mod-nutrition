from .conftest import lua_file, make_player, make_cell, J


def load(lua):
    for f in ("client/PZAgent_Link.lua", "client/PZAgent_Sense.lua", "client/PZAgent_Act.lua", "client/PZAgent_Main.lua"):
        lua.execute(open(lua_file(f), encoding="utf-8").read())


def sq(x, y):
    return J(getX=lambda s: x, getY=lambda s: y, getZ=lambda s: 0)


def test_goto_queues_walk_and_reports_done_within_one_tile(lua):
    load(lua)
    g = lua.globals(); g._cell = make_cell(squares={(13, 20, 0): sq(13, 20)})
    pos = {"x": 10.0}
    p = make_player(); p.getX = lambda s: pos["x"]
    ok, reason, _ = lua.eval("PZA.act.start({seq=1, goal='goto', args='3 0'}, ...)", p)
    assert ok is True
    lua.eval("PZA.act.tick(...)", p)
    assert len(g._queue.queue) == 1 and lua.eval("PZA.act.status().state") == "running"
    pos["x"] = 12.6; g._queue.queue[:] = []
    lua.eval("PZA.act.tick(...)", p)
    st = lua.eval("PZA.act.status()")
    assert st["state"] == "done" and st["seq"] == 1
    lua.eval("PZA.act.tick(...)", p)
    assert lua.eval("PZA.act.status().name") == "idle"


def test_goto_no_square_fails_and_stuck_replans_then_fails(lua):
    load(lua)
    g = lua.globals(); g._cell = make_cell(squares={})
    ok, reason, _ = lua.eval("PZA.act.start({seq=2, goal='goto', args='3 0'})")
    lua.eval("PZA.act.tick(...)", make_player())
    assert lua.eval("PZA.act.status()")["detail"] == "no square"
    g._cell = make_cell(squares={(13, 20, 0): sq(13, 20)})
    lua.eval("PZA.act.start({seq=3, goal='goto', args='3 0'})")
    p = make_player()
    for _ in range(4 * 90 + 5):
        lua.eval("PZA.act.tick(...)", p)
    st = lua.eval("PZA.act.status()")
    assert st["state"] == "failed" and st["detail"] == "stuck"
    assert len(g._queue.adds) == 4           # the first add plus REPLAN_MAX re-adds


def test_unknown_goal_and_stop(lua):
    load(lua)
    assert lua.eval("PZA.act.start({seq=4, goal='dance', args=''})") == (False, "unknown goal")
    g = lua.globals(); g._cell = make_cell(squares={(13, 20, 0): sq(13, 20)})
    lua.eval("PZA.act.start({seq=5, goal='goto', args='3 0'}, ...)", make_player()); lua.eval("PZA.act.tick(...)", make_player())
    lua.eval("PZA.act.start({seq=6, goal='stop', args=''}, ...)", make_player()); lua.eval("PZA.act.tick(...)", make_player())
    assert g._queue.cleared == 2 and lua.eval("PZA.act.status()")["state"] == "done"  # supersede clear + stop's own


def test_main_tick_emits_hello_frames_at_rate_and_acks_config(lua, fs):
    load(lua)
    g = lua.globals(); g.getPlayer = lambda: make_player()
    assert len(g._handlers) == 1
    lua.execute("PZA.main.init('admin')")
    lua.execute("PZA.main.ready = true")
    fs.files["pzagent/admin/cmd.txt"] = "seq=1\ngoal=rate\nargs=10\n"
    for _ in range(60):
        g._handlers[0]()
    log = fs.files["pzagent/admin/state.log"]
    kinds = [l.split('"kind":"')[1].split('"')[0] for l in log.splitlines()]
    assert kinds[0] == "hello" and kinds.count("ack") == 1
    assert kinds.count("frame") == 10 and lua.eval("PZA.sense.RATE") == 10


def test_main_tick_catches_a_raise_and_emits_lua_error_once(lua, fs):
    load(lua)
    g = lua.globals(); g.getPlayer = lambda: (_ for _ in ()).throw(RuntimeError("boom"))
    lua.execute("PZA.main.init('admin')")
    lua.execute("PZA.main.ready = true")
    for _ in range(30):
        g._handlers[0]()
    assert lua.eval("PZA.errors") == 30
    assert fs.files["pzagent/admin/state.log"].count('"event":"lua_error"') == 1


def test_new_goal_clears_running_walk_and_reports_superseded(lua):
    load(lua)
    g = lua.globals(); g._cell = make_cell(squares={(13, 20, 0): sq(13, 20)})
    p = make_player()
    lua.eval("PZA.act.start({seq=1, goal='goto', args='3 0'}, ...)", p)
    lua.eval("PZA.act.tick(...)", p)
    assert len(g._queue.adds) == 1
    ok, reason, old = lua.eval("PZA.act.start({seq=2, goal='goto', args='3 0'}, ...)", p)
    assert ok is True and old["state"] == "failed" and old["detail"] == "superseded" and old["seq"] == 1
    lua.eval("PZA.act.tick(...)", p)
    assert g._queue.cleared == 1 and len(g._queue.adds) == 2


def test_main_reports_superseded_event_and_scan_lands_with_its_ack(lua, fs):
    load(lua)
    g = lua.globals(); g.getPlayer = lambda: make_player()
    g._cell = make_cell(squares={(13, 20, 0): sq(13, 20)})
    lua.execute("PZA.main.init('admin')"); lua.execute("PZA.main.ready = true")
    fs.files["pzagent/admin/cmd.txt"] = "seq=1\ngoal=goto\nargs=3 0\n"
    g._handlers[0]()
    fs.files["pzagent/admin/cmd.txt"] = "seq=2\ngoal=goto\nargs=3 0\n"
    g._handlers[0]()
    log = fs.files["pzagent/admin/state.log"]
    assert '"reason":"superseded"' in log
    fs.files["pzagent/admin/cmd.txt"] = "seq=3\ngoal=scan\nargs=1\n"
    g._handlers[0]()
    log = fs.files["pzagent/admin/state.log"]
    assert '"kind":"scan"' in log and log.count('"kind":"ack"') == 3 and '"scanMs":' in log
