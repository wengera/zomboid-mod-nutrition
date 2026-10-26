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
    ok, reason, _ = lua.eval("PZA.act.start({seq=1, goal='goto', args='13 20'}, ...)", p)
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
    ok, reason, _ = lua.eval("PZA.act.start({seq=2, goal='goto', args='13 20'})")
    lua.eval("PZA.act.tick(...)", make_player())
    assert lua.eval("PZA.act.status()")["detail"] == "no square"
    g._cell = make_cell(squares={(13, 20, 0): sq(13, 20)})
    lua.eval("PZA.act.start({seq=3, goal='goto', args='13 20'})")
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
    lua.eval("PZA.act.start({seq=5, goal='goto', args='13 20'}, ...)", make_player()); lua.eval("PZA.act.tick(...)", make_player())
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
    lua.eval("PZA.act.start({seq=1, goal='goto', args='13 20'}, ...)", p)
    lua.eval("PZA.act.tick(...)", p)
    assert len(g._queue.adds) == 1
    ok, reason, old = lua.eval("PZA.act.start({seq=2, goal='goto', args='13 20'}, ...)", p)
    assert ok is True and old["state"] == "failed" and old["detail"] == "superseded" and old["seq"] == 1
    lua.eval("PZA.act.tick(...)", p)
    assert g._queue.cleared == 1 and len(g._queue.adds) == 2


def test_main_reports_superseded_event_and_scan_lands_with_its_ack(lua, fs):
    load(lua)
    g = lua.globals(); g.getPlayer = lambda: make_player()
    g._cell = make_cell(squares={(13, 20, 0): sq(13, 20)})
    lua.execute("PZA.main.init('admin')"); lua.execute("PZA.main.ready = true")
    fs.files["pzagent/admin/cmd.txt"] = "seq=1\ngoal=goto\nargs=13 20\n"
    g._handlers[0]()
    fs.files["pzagent/admin/cmd.txt"] = "seq=2\ngoal=goto\nargs=13 20\n"
    g._handlers[0]()
    log = fs.files["pzagent/admin/state.log"]
    assert '"reason":"superseded"' in log
    fs.files["pzagent/admin/cmd.txt"] = "seq=3\ngoal=scan\nargs=1\n"
    g._handlers[0]()
    log = fs.files["pzagent/admin/state.log"]
    assert '"kind":"scan"' in log and log.count('"kind":"ack"') == 3 and '"scanMs":' in log


# ---- Task 9: open, loot, eat, drink ----------------------------------------------------------

def jlist(items):
    return J(size=lambda s: len(items), get=lambda s, i: items[i])


def osq(x, y, objects=(), solid=False):
    objs = list(objects)
    return J(getX=lambda s: x, getY=lambda s: y, getZ=lambda s: 0, isSolid=lambda s: solid,
             getObjects=lambda s: jlist(objs))


def make_door(opened=False, locked=False, cls="IsoDoor"):
    st = {"open": opened}
    d = J(_cls=cls, IsOpen=lambda s: st["open"], isLocked=lambda s: locked, isBarricaded=lambda s: False)
    d.st = st
    return d


def item(ft, cls=None, fluid=None):
    return J(_cls=cls, getFullType=lambda s: ft, getFluidContainer=lambda s: fluid)


def make_container(items, loaded=True):
    c = J(getType=lambda s: "crate")
    if loaded:
        c.getItems = lambda s: jlist(items)
    return c


def inv_player(items, x=10.0, y=20.0):
    """A player whose inventory is a mutable list; getFirstTypeRecurse/getCountTypeRecurse read it."""
    p = make_player(x=x, y=y)
    inv = J(getItems=lambda s: jlist(items),
            getFirstTypeRecurse=lambda s, t: next((i for i in items if i.getFullType(i) == t), None),
            getCountTypeRecurse=lambda s, t: sum(1 for i in items if i.getFullType(i) == t))
    p.getInventory = lambda s: inv
    p.inv = inv
    return p


def tick(lua, p, n=1):
    for _ in range(n):
        lua.eval("PZA.act.tick(...)", p)
    return lua.eval("PZA.act.status()")


def test_open_walks_adjacent_first_then_queues_the_open(lua):
    load(lua)
    g = lua.globals()
    door = make_door()
    g._cell = make_cell(squares={(13, 20, 0): osq(13, 20, [door]), (12, 20, 0): osq(12, 20),
                                 (12, 19, 0): osq(12, 19, solid=True)})
    pos = {"x": 10.0}
    p = make_player(); p.getX = lambda s: pos["x"]
    ok, _, _ = lua.eval("PZA.act.start({seq=1, goal='open', args='13 20'}, ...)", p)
    assert ok is True
    st = tick(lua, p)
    assert st["state"] == "running" and [a.Type for a in g._queue.adds] == ["ISWalkToTimedAction"]
    assert g._queue.adds[0].sq.getX(g._queue.adds[0].sq) == 12    # the non-solid neighbour, not (12,19)
    pos["x"] = 12.2
    st = tick(lua, p)
    assert [a.Type for a in g._queue.adds] == ["ISWalkToTimedAction", "ISOpenCloseDoor"]
    assert g._queue.adds[1].item is door and st["state"] == "running"
    door.st["open"] = True
    st = tick(lua, p)
    assert st["state"] == "done" and st["detail"] == "open"


def test_open_adjacent_skips_the_walk_and_thumpable_door_counts(lua):
    load(lua)
    g = lua.globals()
    door = make_door(cls="IsoThumpable"); door.isDoor = lambda s: True
    g._cell = make_cell(squares={(11, 20, 0): osq(11, 20, [door])})
    p = make_player()
    lua.eval("PZA.act.start({seq=1, goal='open', args='11 20'}, ...)", p)
    tick(lua, p)
    assert [a.Type for a in g._queue.adds] == ["ISOpenCloseDoor"]


def test_open_failures(lua):
    load(lua)
    g = lua.globals()
    assert lua.eval("PZA.act.start({seq=1, goal='open', args='x'})") == (False, "bad args")
    p = make_player()
    g._cell = make_cell(squares={})
    lua.eval("PZA.act.start({seq=2, goal='open', args='13 20'})")
    assert tick(lua, p)["detail"] == "no square"
    g._cell = make_cell(squares={(13, 20, 0): osq(13, 20, [J(_cls="IsoObject")])})
    lua.eval("PZA.act.start({seq=3, goal='open', args='13 20'})")
    assert tick(lua, p)["detail"] == "no door"
    g._cell = make_cell(squares={(13, 20, 0): osq(13, 20, [make_door(locked=True)]), (12, 20, 0): osq(12, 20)})
    lua.eval("PZA.act.start({seq=4, goal='open', args='13 20'})")
    st = tick(lua, p)
    assert st["state"] == "failed" and st["detail"] == "locked"
    g._cell = make_cell(squares={(13, 20, 0): osq(13, 20, [make_door()]), (12, 20, 0): osq(12, 20, solid=True)})
    lua.eval("PZA.act.start({seq=5, goal='open', args='13 20'})")
    assert tick(lua, p)["detail"] == "not adjacent"


def test_open_that_never_opens_is_locked_and_an_open_door_is_done_at_once(lua):
    load(lua)
    g = lua.globals()
    g._cell = make_cell(squares={(11, 20, 0): osq(11, 20, [make_door()])})
    p = make_player()
    lua.eval("PZA.act.start({seq=1, goal='open', args='11 20'})")
    assert tick(lua, p)["state"] == "running"
    g._clock["ms"] += 6000
    st = tick(lua, p)
    assert st["state"] == "failed" and st["detail"] == "locked"
    g._cell = make_cell(squares={(13, 20, 0): osq(13, 20, [make_door(opened=True)])})
    lua.eval("PZA.act.start({seq=2, goal='open', args='13 20'})")
    st = tick(lua, p)
    assert st["state"] == "done" and st["detail"] == "open"


def loot_world(lua, contents, loaded=True, filt=""):
    g = lua.globals()
    box = make_container(contents, loaded)
    obj = J(_cls="IsoObject", getContainerCount=lambda s: 1, getContainerByIndex=lambda s, i: box)
    g._cell = make_cell(squares={(11, 20, 0): osq(11, 20, [obj])})
    held = []
    p = inv_player(held)
    lua.eval("PZA.act.start({seq=1, goal='loot', args='11 20 %s'})" % filt)
    return g, box, held, p


def test_loot_food_transfers_matches_and_reports_moved(lua):
    load(lua)
    bread, axe = item("Base.Bread", "Food"), item("Base.Axe", "HandWeapon")
    g, box, held, p = loot_world(lua, [bread, axe], filt="food")
    st = tick(lua, p)
    adds = g._queue.adds
    assert [a.Type for a in adds] == ["ISInventoryTransferAction"]
    assert adds[0].item is bread and adds[0].src is box and adds[0].dest is p.inv and st["state"] == "running"
    held.append(bread)
    st = tick(lua, p)
    assert st["state"] == "done" and st["detail"] == "moved=1"


def test_loot_filters(lua):
    load(lua)
    water = item("Base.WaterBottle", fluid=J())
    stuff = [item("Base.Bread", "Food"), item("Base.Axe", "HandWeapon"), water,
             item("Base.Bandage"), item("Base.RippedSheets"), item("Base.RagDirty")]
    expect = {"food": 1, "weapon": 1, "water": 1, "bandage": 2, "all": 6, "": 6}
    for filt, n in expect.items():
        g, box, held, p = loot_world(lua, stuff, filt=filt)
        before = len(g._queue.adds)
        tick(lua, p)
        assert len(g._queue.adds) - before == n, filt
    assert lua.eval("PZA.act.start({seq=9, goal='loot', args='11 20 shoes'})") == (False, "bad args")


def test_loot_failures(lua):
    load(lua)
    g, _, _, p = loot_world(lua, [item("Base.Axe", "HandWeapon")], filt="food")
    assert tick(lua, p)["detail"] == "no match"
    g, _, _, p = loot_world(lua, [])
    assert tick(lua, p)["detail"] == "empty"
    g, _, _, p = loot_world(lua, [item("Base.Axe")], loaded=False)
    assert tick(lua, p)["detail"] == "not loaded"
    g._cell = make_cell(squares={(11, 20, 0): osq(11, 20, [J(_cls="IsoObject")])})
    lua.eval("PZA.act.start({seq=2, goal='loot', args='11 20'})")
    assert tick(lua, p)["detail"] == "no container"
    g._cell = make_cell(squares={})
    lua.eval("PZA.act.start({seq=3, goal='loot', args='11 20'})")
    assert tick(lua, p)["detail"] == "not loaded"


def test_eat_consumed_and_failures(lua):
    load(lua)
    g = lua.globals()
    bread = item("Base.Bread", "Food")
    held = [bread]
    p = inv_player(held)
    lua.eval("PZA.act.start({seq=1, goal='eat', args='Base.Bread'})")
    st = tick(lua, p)
    act = g._queue.adds[0]
    assert act.Type == "ISEatFoodAction" and act.item is bread and act.character is p and st["state"] == "running"
    held.remove(bread)
    st = tick(lua, p)
    assert st["state"] == "done" and st["detail"] == "consumed"
    assert lua.eval("PZA.act.start({seq=2, goal='eat', args=''})") == (False, "bad args")
    lua.eval("PZA.act.start({seq=3, goal='eat', args='Base.Apple'})")
    assert tick(lua, p)["detail"] == "none held"
    held.append(bread)
    g._valid["start"] = False
    lua.eval("PZA.act.start({seq=4, goal='eat', args='Base.Bread'})")
    assert tick(lua, p)["detail"] == "not valid"
    g._valid["start"] = True
    lua.eval("PZA.act.start({seq=5, goal='eat', args='Base.Bread'})")
    assert tick(lua, p)["state"] == "running"
    g._clock["ms"] += 20001
    st = tick(lua, p)
    assert st["state"] == "failed" and st["detail"] == "interrupted"


def test_drink_consumed_and_failures(lua):
    load(lua)
    g = lua.globals()
    amount = {"v": 0.5}
    fc = J(getAmount=lambda s: amount["v"], isEmpty=lambda s: amount["v"] <= 0)
    empty = J(getAmount=lambda s: 0.0, isEmpty=lambda s: True)
    bottle = item("Base.WaterBottle", fluid=fc)
    held = [item("Base.Bread", "Food"), item("Base.EmptyBottle", fluid=empty), bottle]
    p = inv_player(held)
    lua.eval("PZA.act.start({seq=1, goal='drink', args=''})")
    tick(lua, p)
    act = g._queue.adds[0]
    assert act.Type == "ISDrinkFluidAction" and act.item is bottle
    amount["v"] = 0.2
    st = tick(lua, p)
    assert st["state"] == "done" and st["detail"] == "consumed"
    g._valid["start"] = False
    amount["v"] = 0.5
    lua.eval("PZA.act.start({seq=2, goal='drink', args=''})")
    assert tick(lua, p)["detail"] == "not valid"
    g._valid["start"] = True
    lua.eval("PZA.act.start({seq=3, goal='drink', args=''})")
    tick(lua, p)
    g._clock["ms"] += 20001
    assert tick(lua, p)["detail"] == "interrupted"
    held.remove(bottle)
    lua.eval("PZA.act.start({seq=4, goal='drink', args=''})")
    assert tick(lua, p)["detail"] == "none held"


def test_every_failed_detail_is_in_the_header_reasons_line():
    import re
    src = open(lua_file("client/PZAgent_Act.lua"), encoding="utf-8").read()
    lines = [l for l in src.splitlines() if l.startswith("-- reasons: ")]
    assert len(lines) == 1
    closed = set(lines[0][len("-- reasons: "):].strip().split("|"))
    used = set(re.findall(r'"failed",\s*"([^"]+)"', src))
    assert used and used <= closed, used - closed
    for x in ("no door", "locked", "not adjacent", "no container", "not loaded", "empty", "no match",
              "none held", "interrupted", "not valid"):
        assert x in used


# ---- Task 9 fix 0: world coordinates, windows, loot timeout ----------------------------------

def test_goto_target_is_world_coordinates_not_an_offset(lua):
    load(lua)
    g = lua.globals(); g._cell = make_cell(squares={(13, 20, 0): sq(13, 20), (63, 70, 0): sq(63, 70)})
    p = make_player(x=50.0, y=50.0)
    lua.eval("PZA.act.start({seq=1, goal='goto', args='13 20'}, ...)", p)
    tick(lua, p)
    walk = g._queue.adds[0].sq
    assert (walk.getX(walk), walk.getY(walk)) == (13, 20)


def test_open_window_through_iso_open_close_window(lua):
    load(lua)
    g = lua.globals()
    win = make_door(cls="IsoWindow")
    g._cell = make_cell(squares={(11, 20, 0): osq(11, 20, [win])})
    p = make_player()
    lua.eval("PZA.act.start({seq=1, goal='open', args='11 20'})")
    tick(lua, p)
    assert [a.Type for a in g._queue.adds] == ["ISOpenCloseWindow"] and g._queue.adds[0].object is win
    win.st["open"] = True
    st = tick(lua, p)
    assert st["state"] == "done" and st["detail"] == "open"
    thump = make_door(cls="IsoThumpable"); thump.isWindow = lambda s: True
    g._cell = make_cell(squares={(11, 20, 0): osq(11, 20, [thump])})
    lua.eval("PZA.act.start({seq=2, goal='open', args='11 20'})")
    tick(lua, p)
    assert g._queue.adds[-1].Type == "ISOpenCloseWindow"
    g._cell = make_cell(squares={(11, 20, 0): osq(11, 20, [make_door(cls="IsoWindow", locked=True)])})
    lua.eval("PZA.act.start({seq=3, goal='open', args='11 20'})")
    assert tick(lua, p)["detail"] == "locked"


def test_open_prefers_the_door_when_a_square_holds_both(lua):
    load(lua)
    g = lua.globals()
    door = make_door()
    g._cell = make_cell(squares={(11, 20, 0): osq(11, 20, [make_door(cls="IsoWindow"), door])})
    lua.eval("PZA.act.start({seq=1, goal='open', args='11 20'})")
    tick(lua, make_player())
    assert g._queue.adds[-1].Type == "ISOpenCloseDoor" and g._queue.adds[-1].item is door


def test_loot_timeout_fails_interrupted_when_nothing_moved_else_reports_moved(lua):
    load(lua)
    g, box, held, p = loot_world(lua, [item("Base.Bread", "Food")], filt="food")
    tick(lua, p)
    g._clock["ms"] += 10000 + 3000
    assert tick(lua, p)["state"] == "running"        # the budget is exceeded only past it
    g._clock["ms"] += 1
    st = tick(lua, p)
    assert st["state"] == "failed" and st["detail"] == "interrupted"
    bread, apple = item("Base.Bread", "Food"), item("Base.Apple", "Food")
    g, box, held, p = loot_world(lua, [bread, apple], filt="food")
    tick(lua, p)
    held.append(bread)
    assert tick(lua, p)["state"] == "running"
    g._clock["ms"] += 10000 + 2 * 3000 + 1
    st = tick(lua, p)
    assert st["state"] == "done" and st["detail"] == "moved=1"


# ---- Task 5b: cost.linkMs reports the previous frame's flush --------------------------------

def test_frame_link_ms_is_the_previous_frames_flush(lua, fs):
    import json
    load(lua)
    g = lua.globals(); g.getPlayer = lambda: make_player()
    lua.execute("PZA.main.init('admin')"); lua.execute("PZA.main.ready = true")
    fs.write_cost_ms = 3
    for _ in range(24):                     # RATE 5: a frame every 12 ticks, so two frames
        g._handlers[0]()
    frames = [json.loads(l) for l in fs.files["pzagent/admin/state.log"].splitlines() if '"kind":"frame"' in l]
    assert len(frames) == 2
    assert frames[0]["cost"]["linkMs"] == 0 and frames[1]["cost"]["linkMs"] == 3
