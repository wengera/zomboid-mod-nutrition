import pytest
from .conftest import lua_file, make_player, make_cell, make_zombie, J


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
    import json
    ev = [json.loads(l) for l in log.splitlines() if '"reason":"superseded"' in l][0]
    assert ev["goalSeq"] == 1 and ev["seq"] != 1         # the goal's seq survives emit's own line seq
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


def make_door(opened=False, locked=False, cls="IsoDoor", barricaded=False):
    st = {"open": opened}
    d = J(_cls=cls, IsOpen=lambda s: st["open"], isLocked=lambda s: locked, isBarricaded=lambda s: barricaded)
    d.st = st
    return d


def item(ft, cls=None, fluid=None):
    return J(_cls=cls, getFullType=lambda s: ft, getFluidContainer=lambda s: fluid)


def make_container(items, loaded=True):
    c = J(getType=lambda s: "crate")
    if loaded:
        c.getItems = lambda s: jlist(items)
    return c


def inv_player(items, x=10.0, y=20.0, bagged=()):
    """A player whose inventory is a mutable list; getFirstType/getCountType read it (the top level), and
    the *Recurse forms also see `bagged` (items inside a bag)."""
    p = make_player(x=x, y=y)
    deep = lambda: list(items) + list(bagged)
    inv = J(getItems=lambda s: jlist(items),
            getFirstType=lambda s, t: next((i for i in items if i.getFullType(i) == t), None),
            getCountType=lambda s, t: sum(1 for i in items if i.getFullType(i) == t),
            getFirstTypeRecurse=lambda s, t: next((i for i in deep() if i.getFullType(i) == t), None),
            getCountTypeRecurse=lambda s, t: sum(1 for i in deep() if i.getFullType(i) == t))
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
    g._cell = make_cell(squares={(13, 20, 0): osq(13, 20, [make_door(barricaded=True)]), (12, 20, 0): osq(12, 20)})
    lua.eval("PZA.act.start({seq=4, goal='open', args='13 20'})")
    st = tick(lua, p)
    assert st["state"] == "failed" and st["detail"] == "locked"     # a barricade fails up front
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


def test_open_a_locked_door_is_toggled_and_locked_is_read_after(lua):
    load(lua)
    g = lua.globals()
    door = make_door(locked=True)
    g._cell = make_cell(squares={(11, 20, 0): osq(11, 20, [door])})
    p = make_player()
    lua.eval("PZA.act.start({seq=1, goal='open', args='11 20'})")
    assert tick(lua, p)["state"] == "running"              # queued: from inside, the toggle unlocks it
    assert [a.Type for a in g._queue.adds] == ["ISOpenCloseDoor"]
    door.st["open"] = True
    assert tick(lua, p)["detail"] == "open"
    shut = make_door(locked=True)
    g._cell = make_cell(squares={(11, 20, 0): osq(11, 20, [shut])})
    lua.eval("PZA.act.start({seq=2, goal='open', args='11 20'})")
    tick(lua, p)
    g._clock["ms"] += 5001
    st = tick(lua, p)
    assert st["state"] == "failed" and st["detail"] == "locked"


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


def test_eat_refuses_a_non_food_before_the_constructor_and_ignores_bags(lua):
    load(lua)
    g = lua.globals()
    made = []
    g.ISEatFoodAction = J(new=lambda cls, p, it, pct: made.append(it) or J(Type="ISEatFoodAction", isValidStart=lambda s: True))
    p = inv_player([item("Base.Pills")], bagged=[item("Base.Bread", "Food")])
    lua.eval("PZA.act.start({seq=1, goal='eat', args='Base.Pills'})")
    assert tick(lua, p)["detail"] == "not valid"
    assert made == [] and g._queue.adds == []               # ISEatFoodAction:new never ran on a non-Food
    lua.eval("PZA.act.start({seq=2, goal='eat', args='Base.Bread'})")
    assert tick(lua, p)["detail"] == "none held"            # a bag-only item is not held at the top level


def test_drink_skips_poison_and_prefers_clean_water(lua):
    load(lua)
    g = lua.globals()

    def fluid(clean=False, poison=False):
        return J(getAmount=lambda s: 0.5, isEmpty=lambda s: False,
                 isPoisonous=lambda s: poison, isFilledWithCleanWater=lambda s: clean)
    bleach = item("Base.Bleach", fluid=fluid(poison=True))
    juice = item("Base.JuiceBox", fluid=fluid())
    water = item("Base.WaterBottle", fluid=fluid(clean=True))
    p = inv_player([bleach, juice, water])
    lua.eval("PZA.act.start({seq=1, goal='drink', args=''})")
    tick(lua, p)
    assert g._queue.adds[-1].item is water
    p = inv_player([bleach, juice])
    lua.eval("PZA.act.start({seq=2, goal='drink', args=''})")
    tick(lua, p)
    assert g._queue.adds[-1].item is juice
    p = inv_player([bleach])
    lua.eval("PZA.act.start({seq=3, goal='drink', args=''})")
    assert tick(lua, p)["detail"] == "none held"


def test_drink_consumed_and_failures(lua):
    load(lua)
    g = lua.globals()
    amount = {"v": 0.5}
    fc = J(getAmount=lambda s: amount["v"], isEmpty=lambda s: amount["v"] <= 0, isPoisonous=lambda s: False)
    empty = J(getAmount=lambda s: 0.0, isEmpty=lambda s: True, isPoisonous=lambda s: False)
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
    n = len(g._queue.adds)
    assert tick(lua, p)["detail"] == "no door"              # openWindow takes an IsoWindow only
    assert len(g._queue.adds) == n
    g._cell = make_cell(squares={(11, 20, 0): osq(11, 20, [make_door(cls="IsoWindow", barricaded=True)])})
    lua.eval("PZA.act.start({seq=3, goal='open', args='11 20'})")
    assert tick(lua, p)["detail"] == "locked"
    g._cell = make_cell(squares={(11, 20, 0): osq(11, 20, [make_door(cls="IsoWindow")])})
    g.ISOpenCloseWindow = None
    lua.eval("PZA.act.start({seq=4, goal='open', args='11 20'})")
    assert tick(lua, p)["detail"] == "no door"


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


# ---- Task 5c: no poll or flush before init; goto clears its walk at done ---------------------

def test_tick_without_a_player_before_init_polls_and_writes_nothing(lua, fs):
    load(lua)
    g = lua.globals(); g.getPlayer = lambda: None
    fs.files["pzagent/admin/cmd.txt"] = "seq=1\ngoal=stop\nargs=\n"
    for _ in range(30):
        g._handlers[0]()
    assert lua.eval("PZA.errors") == 0 and fs.opens == 0
    assert list(fs.files) == ["pzagent/admin/cmd.txt"] and not lua.eval("PZA.main.ready")


def test_raise_before_init_counts_and_never_re_raises(lua, fs):
    load(lua)
    g = lua.globals(); g.getPlayer = lambda: (_ for _ in ()).throw(RuntimeError("boom"))
    for _ in range(30):
        g._handlers[0]()                    # a raise out of the handler would fail the test here
    assert lua.eval("PZA.errors") == 30 and fs.files == {} and fs.opens == 0


def test_tick_inits_the_link_before_its_first_poll(lua, fs):
    load(lua)
    g = lua.globals(); g.getPlayer = lambda: make_player()
    g._cell = make_cell(squares={(13, 20, 0): sq(13, 20)})
    fs.files["pzagent/admin/cmd.txt"] = "seq=1\ngoal=goto\nargs=13 20\n"
    g._handlers[0]()
    log = fs.files["pzagent/admin/state.log"]
    kinds = [l.split('"kind":"')[1].split('"')[0] for l in log.splitlines()]
    assert kinds[:2] == ["hello", "ack"] and lua.eval("PZA.errors") == 0


def test_goto_done_clears_its_walk(lua):
    load(lua)
    g = lua.globals(); g._cell = make_cell(squares={(13, 20, 0): sq(13, 20)})
    pos = {"x": 10.0}
    p = make_player(); p.getX = lambda s: pos["x"]
    lua.eval("PZA.act.start({seq=1, goal='goto', args='13 20'}, ...)", p)
    tick(lua, p)
    assert len(g._queue.queue) == 1 and g._queue.cleared == 0
    pos["x"] = 12.6
    assert tick(lua, p)["state"] == "done"
    assert g._queue.cleared == 1 and g._queue.queue == []


def test_open_sub_walk_is_cleared_before_the_open_is_queued(lua):
    load(lua)
    g = lua.globals()
    door = make_door()
    g._cell = make_cell(squares={(13, 20, 0): osq(13, 20, [door]), (12, 20, 0): osq(12, 20)})
    pos = {"x": 10.0}
    p = make_player(); p.getX = lambda s: pos["x"]
    lua.eval("PZA.act.start({seq=1, goal='open', args='13 20'})")
    tick(lua, p)
    pos["x"] = 12.2
    tick(lua, p)
    assert g._queue.cleared == 1 and [a.Type for a in g._queue.queue] == ["ISOpenCloseDoor"]


# ---- Task 11a: drink's poison check fails closed ---------------------------------------------

def test_drink_with_is_poisonous_absent_is_none_held(lua):
    load(lua)
    g = lua.globals()
    unknown = item("Base.WaterBottle", fluid=J(getAmount=lambda s: 0.5, isEmpty=lambda s: False,
                                               isFilledWithCleanWater=lambda s: True))
    p = inv_player([unknown])
    lua.eval("PZA.act.start({seq=1, goal='drink', args=''})")
    assert tick(lua, p)["detail"] == "none held"
    assert g._queue.adds == []


# ---- Task 11: fight, flee, sleep -------------------------------------------------------------

def weapon(cond=10):
    c = {"v": cond}
    w = J(_cls="HandWeapon", getFullType=lambda s: "Base.BaseballBat", getCondition=lambda s: c["v"])
    w.cond = c
    return w


def health_player(hp, **k):
    """a make_player whose overall body health reads hp["v"]"""
    p = make_player(**k)
    bd = J(getOverallBodyHealth=lambda s: hp["v"])
    p.getBodyDamage = lambda s: bd
    return p


def open_squares(cx, cy, r=12):
    return {(x, y, 0): osq(x, y) for x in range(cx - r, cx + r + 1) for y in range(cy - r, cy + r + 1)}


def test_fight_faces_and_swings_on_the_1200_ms_cooldown(lua):
    load(lua)
    g = lua.globals()
    z = make_zombie(7, 12.0, 20.0)
    g._cell = make_cell(zombies=[z])
    p = make_player(weapon=weapon())
    assert lua.eval("PZA.act.start({seq=1, goal='fight', args=''})")[0] is True
    st = tick(lua, p)
    assert st["state"] == "running" and p.faced == [z] and p.attacks == [0]     # DoAttack(0), the harness's call
    g._clock["ms"] += 1199
    tick(lua, p)
    assert p.attacks == [0]
    g._clock["ms"] += 1
    tick(lua, p)
    assert p.attacks == [0, 0] and len(p.faced) == 3


def test_fight_waits_beyond_fight_r_and_ignores_the_dead(lua):
    load(lua)
    g = lua.globals()
    g._cell = make_cell(zombies=[make_zombie(1, 14.0, 20.0), make_zombie(2, 11.0, 20.0, dead=True)])
    p = make_player(weapon=weapon())
    lua.eval("PZA.act.start({seq=1, goal='fight', args=''})")
    assert tick(lua, p)["state"] == "running"
    assert p.attacks == [] and p.faced == []          # 4 tiles is outside FIGHT_R = 3; the dead one is no threat


def test_fight_steps_back_two_tiles_inside_the_grab_window(lua):
    load(lua)
    g = lua.globals()
    z = make_zombie(7, 10.5, 20.0)                      # 0.5 east of the player at (10, 20)
    g._cell = make_cell(zombies=[z], squares=open_squares(10, 20))
    p = make_player(weapon=weapon())
    lua.eval("PZA.act.start({seq=1, goal='fight', args=''})")
    tick(lua, p)
    assert p.attacks == [0] and g._queue.adds == []     # the swing is due first
    st = tick(lua, p)                                   # no swing due, dist < 1: a walk 2 tiles west
    walk = g._queue.adds[-1]
    assert walk.Type == "ISWalkToTimedAction" and (walk.sq.getX(walk.sq), walk.sq.getY(walk.sq)) == (8, 20)
    assert st["state"] == "running" and p.attacks == [0]
    tick(lua, p)
    assert len(g._queue.adds) == 1                      # the step back runs; it is not re-queued each tick


def test_fight_done_clear_after_60_quiet_ticks(lua):
    load(lua)
    g = lua.globals()
    g._cell = make_cell(zombies=[make_zombie(1, 12.0, 20.0)])
    p = make_player(weapon=weapon())
    lua.eval("PZA.act.start({seq=1, goal='fight', args=''})")
    tick(lua, p)
    g._cell = make_cell(zombies=[make_zombie(1, 12.0, 20.0, dead=True)])
    assert tick(lua, p, 59)["state"] == "running"
    st = tick(lua, p)
    assert st["state"] == "done" and st["detail"] == "clear"


def test_fight_failures(lua):
    load(lua)
    g = lua.globals()
    g._cell = make_cell(zombies=[make_zombie(1, 12.0, 20.0)])
    lua.eval("PZA.act.start({seq=1, goal='fight', args=''})")
    assert tick(lua, make_player())["detail"] == "no weapon"
    lua.eval("PZA.act.start({seq=2, goal='fight', args=''})")
    assert tick(lua, make_player(weapon=weapon(cond=0)))["detail"] == "weapon broke"
    hp = {"v": 80.0}
    p = health_player(hp, weapon=weapon())
    lua.eval("PZA.act.start({seq=3, goal='fight', args=''})")
    assert tick(lua, p)["state"] == "running"
    hp["v"] = 39.9
    st = tick(lua, p)
    assert st["state"] == "failed" and st["detail"] == "low health"


def test_fight_never_calls_an_absent_do_attack(lua):
    load(lua)
    g = lua.globals()
    g._cell = make_cell(zombies=[make_zombie(1, 12.0, 20.0)])
    p = make_player(weapon=weapon())
    p.DoAttack = None
    lua.eval("PZA.act.start({seq=1, goal='fight', args=''})")
    assert tick(lua, p)["state"] == "running" and lua.eval("PZA.errors") == 0


def test_flee_runs_to_its_target_and_is_done_at(lua):
    load(lua)
    g = lua.globals()
    g._cell = make_cell(squares=open_squares(10, 20))
    pos = {"x": 10.0}
    p = make_player(); p.getX = lambda s: pos["x"]
    runs = []
    p.setRunning = lambda s, v: runs.append(v)
    assert lua.eval("PZA.act.start({seq=1, goal='flee', args='18 20'})")[0] is True
    st = tick(lua, p)
    walk = g._queue.adds[-1]
    assert st["state"] == "running" and runs == [True] and (walk.sq.getX(walk.sq), walk.sq.getY(walk.sq)) == (18, 20)
    pos["x"] = 18.2
    st = tick(lua, p)
    assert st["state"] == "done" and st["detail"] == "at"
    assert lua.eval("PZA.act.start({seq=2, goal='flee', args='18'})") == (False, "bad args")


def test_flee_replans_every_30_ticks_away_from_the_zombie_centroid(lua):
    load(lua)
    g = lua.globals()
    g._cell = make_cell(zombies=[make_zombie(1, 10.0, 18.0), make_zombie(2, 10.0, 16.0)],
                        squares=open_squares(10, 20, r=10))
    p = make_player()                                   # at (10, 20); the centroid is (10, 17), north
    lua.eval("PZA.act.start({seq=1, goal='flee', args='14 20'})")
    tick(lua, p, 29)
    assert len(g._queue.adds) == 1
    tick(lua, p)                                        # tick 30: 8 tiles south of the player
    walk = g._queue.adds[-1]
    assert len(g._queue.adds) == 2 and (walk.sq.getX(walk.sq), walk.sq.getY(walk.sq)) == (10, 28)
    assert g._queue.cleared >= 1 and lua.eval("PZA.act.status().state") == "running"


def test_flee_replan_keeps_its_walk_when_the_away_square_is_unknown(lua):
    load(lua)
    g = lua.globals()
    g._cell = make_cell(zombies=[make_zombie(1, 10.0, 17.0)], squares={(14, 20, 0): osq(14, 20)})
    p = make_player()
    lua.eval("PZA.act.start({seq=1, goal='flee', args='14 20'})")
    st = tick(lua, p, 30)
    assert len(g._queue.adds) == 1 and st["state"] == "running"


def test_flee_cornered_on_no_square_or_stuck(lua):
    load(lua)
    g = lua.globals()
    g._cell = make_cell(squares={})
    lua.eval("PZA.act.start({seq=1, goal='flee', args='18 20'})")
    st = tick(lua, make_player())
    assert st["state"] == "failed" and st["detail"] == "cornered"
    g._cell = make_cell(squares={(18, 20, 0): osq(18, 20)})
    lua.eval("PZA.act.start({seq=2, goal='flee', args='18 20'})")
    st = tick(lua, make_player(), 4 * 90 + 5)            # the player never moves: the walk is stuck
    assert st["state"] == "failed" and st["detail"] == "cornered"


def test_sleep_calls_the_vanilla_ground_sleep_and_is_done_awake(lua):
    load(lua)
    g = lua.globals()
    p = make_player()
    assert lua.eval("PZA.act.start({seq=1, goal='sleep', args=''})")[0] is True
    st = tick(lua, p)
    assert list(g._sleeps) == [("YES", 0, None)] and st["state"] == "running"   # the ground: bed nil
    p.asleep["v"] = True
    g._clock["ms"] += 60000                             # asleep past the 10 s wait is still running
    assert tick(lua, p, 3)["state"] == "running"
    p.asleep["v"] = False
    st = tick(lua, p)
    assert st["state"] == "done" and st["detail"] == "awake"


def test_sleep_not_allowed_when_the_call_raises_or_sleep_never_comes(lua):
    load(lua)
    g = lua.globals()
    p = make_player()
    g._sleep["raise"] = True
    lua.eval("PZA.act.start({seq=1, goal='sleep', args=''})")
    assert tick(lua, p)["detail"] == "not allowed"
    g._sleep["raise"] = False
    lua.eval("PZA.act.start({seq=2, goal='sleep', args=''})")
    tick(lua, p)
    g._clock["ms"] += 10000
    assert tick(lua, p)["state"] == "running"
    g._clock["ms"] += 1
    st = tick(lua, p)
    assert st["state"] == "failed" and st["detail"] == "not allowed"
    g.ISWorldObjectContextMenu = None                   # the entry absent: refused, never nil-called
    lua.eval("PZA.act.start({seq=3, goal='sleep', args=''})")
    assert tick(lua, p)["detail"] == "not allowed"
    p.isAsleep = None                                   # isAsleep absent: fails closed
    g.ISWorldObjectContextMenu = lua.eval("{onConfirmSleep = function() end}")
    lua.eval("PZA.act.start({seq=4, goal='sleep', args=''})")
    tick(lua, p)
    assert tick(lua, p)["detail"] == "not allowed"


def test_sleep_interrupted_when_woken_by_a_hit_or_a_zombie(lua):
    load(lua)
    g = lua.globals()
    hp = {"v": 90.0}
    p = health_player(hp)
    lua.eval("PZA.act.start({seq=1, goal='sleep', args=''})")
    tick(lua, p)
    p.asleep["v"] = True
    tick(lua, p)
    hp["v"] = 70.0
    p.asleep["v"] = False
    st = tick(lua, p)
    assert st["state"] == "failed" and st["detail"] == "interrupted"
    hp["v"] = 90.0
    lua.eval("PZA.act.start({seq=2, goal='sleep', args=''})")
    tick(lua, p)
    p.asleep["v"] = True
    tick(lua, p)
    g._cell = make_cell(zombies=[make_zombie(1, 15.0, 20.0)])
    p.asleep["v"] = False
    assert tick(lua, p)["detail"] == "interrupted"


def test_task11_details_are_in_the_header_reasons_and_done_lines():
    import re
    src = open(lua_file("client/PZAgent_Act.lua"), encoding="utf-8").read()
    header = [l for l in src.splitlines() if l.startswith("-- reasons: ")][0]
    closed = set(header[len("-- reasons: "):].strip().split("|"))
    used = set(re.findall(r'"failed",\s*"([^"]+)"', src))
    for x in ("no weapon", "weapon broke", "low health", "cornered", "not allowed", "interrupted"):
        assert x in used and x in closed
    done = set([l for l in src.splitlines() if l.startswith("-- done: ")][0][len("-- done: "):].strip().split("|"))
    for x in ("clear", "at", "awake"):
        assert x in done and x not in closed and re.search(r'"done",\s*"%s"' % x, src)


# ---- Stage A pass 2: goto fails dead; stuck by progress; the chunked scan --------------------

ALL_GOALS = (("goto", "13 20"), ("open", "13 20"), ("loot", "13 20"), ("eat", "Base.Apple"), ("drink", ""),
             ("fight", ""), ("flee", "13 20"), ("sleep", ""), ("stop", ""))


def test_goto_fails_dead_at_once_when_health_reads_zero(lua):
    load(lua)
    g = lua.globals(); g._cell = make_cell(squares={(13, 20, 0): sq(13, 20)})
    hp = {"v": 100.0}
    p = health_player(hp)
    assert lua.eval("PZA.act.start({seq=1, goal='goto', args='13 20'}, ...)", p)[0] is True
    assert tick(lua, p)["state"] == "running"
    hp["v"] = 0.0
    st = tick(lua, p)
    assert st["state"] == "failed" and st["detail"] == "dead"


def test_a_dead_player_refuses_every_goal_and_an_absent_health_is_not_dead(lua):
    load(lua)
    g = lua.globals(); g._cell = make_cell(squares={(13, 20, 0): sq(13, 20)})
    dead = health_player({"v": 0.0})
    for i, (goal, args) in enumerate(ALL_GOALS):
        assert lua.eval("PZA.act.start({seq=%d, goal='%s', args='%s'}, ...)" % (i + 1, goal, args), dead) == (False, "dead")
    assert lua.eval("PZA.act.status().name") == "idle"
    nobody = make_player(); nobody.getBodyDamage = None           # no reading: not dead
    assert lua.eval("PZA.act.start({seq=20, goal='goto', args='13 20'}, ...)", nobody)[0] is True
    assert tick(lua, nobody)["state"] == "running"
    blank = health_player({"v": None})                           # getOverallBodyHealth answers nil: not dead
    assert lua.eval("PZA.act.start({seq=21, goal='goto', args='13 20'}, ...)", blank)[0] is True
    assert tick(lua, blank)["state"] == "running"


def test_main_acks_a_dead_players_goal_with_reason_dead(lua, fs):
    import json
    load(lua)
    g = lua.globals(); g.getPlayer = lambda: health_player({"v": 0.0})
    g._cell = make_cell(squares={(13, 20, 0): sq(13, 20)})
    lua.execute("PZA.main.init('admin')"); lua.execute("PZA.main.ready = true")
    fs.files["pzagent/admin/cmd.txt"] = "seq=1\ngoal=goto\nargs=13 20\n"
    g._handlers[0]()
    acks = [json.loads(l) for l in fs.files["pzagent/admin/state.log"].splitlines() if '"kind":"ack"' in l]
    assert len(acks) == 1 and acks[0]["ok"] is False and acks[0]["reason"] == "dead"


def test_goto_oscillating_without_approaching_is_stuck(lua):
    load(lua)
    g = lua.globals(); g._cell = make_cell(squares={(13, 20, 0): sq(13, 20)})
    t = {"n": 0}
    p = make_player(); p.getX = lambda s: 10.0 if t["n"] % 2 == 0 else 10.5    # moves every tick, never nearer than 2.5
    lua.eval("PZA.act.start({seq=1, goal='goto', args='13 20'}, ...)", p)
    st = None
    for _ in range(4 * 90 + 10):
        st = tick(lua, p); t["n"] += 1
        if st["state"] != "running":
            break
    assert st["state"] == "failed" and st["detail"] == "stuck"
    assert len(g._queue.adds) == 4                                # the first add plus REPLAN_MAX re-adds


def test_goto_drifting_away_is_stuck(lua):
    load(lua)
    g = lua.globals(); g._cell = make_cell(squares={(23, 20, 0): sq(23, 20)})
    t = {"n": 0}
    p = make_player(); p.getY = lambda s: 20.0 + 0.01 * t["n"]   # the dead body's drift, across the target line
    lua.eval("PZA.act.start({seq=1, goal='goto', args='23 20'}, ...)", p)
    st = None
    for _ in range(4 * 90 + 10):
        st = tick(lua, p); t["n"] += 1
        if st["state"] != "running":
            break
    assert st["state"] == "failed" and st["detail"] == "stuck"


def test_goto_approaching_slowly_is_never_stuck(lua):
    load(lua)
    g = lua.globals(); g._cell = make_cell(squares={(13, 20, 0): sq(13, 20)})
    t = {"n": 0}
    p = make_player(); p.getX = lambda s: 10.0 + 0.1 * (t["n"] // 30)    # 0.1 tile per 30 ticks
    lua.eval("PZA.act.start({seq=1, goal='goto', args='13 20'}, ...)", p)
    states = []
    for _ in range(20 * 30 + 5):
        st = tick(lua, p); t["n"] += 1
        states.append((st["state"], st["detail"]))
        if st["state"] != "running":
            break
    assert states[-1][0] == "done" and ("failed", "stuck") not in states
    assert len(g._queue.adds) == 1                                # never a replan


def scan_world(lua, cx, cy, r):
    """A cell whose every square in the (2r+1)^2 grid around (cx, cy) exists; each getGridSquare call costs 1 ms of
    the fixture's clock, so a scan's ms counts its squares."""
    g = lua.globals()
    clock = g._clock
    squares = {(x, y, 0): sq(x, y) for x in range(cx - r, cx + r + 1) for y in range(cy - r, cy + r + 1)}
    calls = []

    def grid(s, x, y, z):
        clock["ms"] += 1
        calls.append((int(x), int(y)))
        return squares.get((int(x), int(y), int(z)))
    g._cell = J(getZombieList=lambda s: J(size=lambda s2: 0, get=lambda s2, i: None), getGridSquare=grid)
    return calls


def test_main_scan_is_queued_chunked_and_lands_when_its_last_square_is_done(lua, fs):
    import json
    load(lua)
    g = lua.globals(); g.getPlayer = lambda: make_player()
    scan_world(lua, 10, 20, 15)
    lua.execute("PZA.main.init('admin')"); lua.execute("PZA.main.ready = true")
    fs.files["pzagent/admin/cmd.txt"] = "seq=1\ngoal=scan\nargs=15\n"
    landed = None
    for i in range(1, 30):
        g._handlers[0]()
        lines = [json.loads(l) for l in fs.files["pzagent/admin/state.log"].splitlines()]
        if i == 1:
            acks = [l for l in lines if l["kind"] == "ack"]
            assert len(acks) == 1 and acks[0]["ok"] is True and acks[0]["reason"] == "queued"
        if landed is None and any(l["kind"] == "scan" for l in lines):
            landed = i
    lines = [json.loads(l) for l in fs.files["pzagent/admin/state.log"].splitlines()]
    scans = [l for l in lines if l["kind"] == "scan"]
    assert landed == 17 and len(scans) == 1                      # ceil(961 / 60) ticks
    s = scans[0]
    assert s["r"] == 15 and len(s["squares"]) == 961 and s["scanTicks"] == 17 and s["scanMs"] == 961
    for k in ("hour", "missing", "gameMin", "worldAge"):
        assert k in s
    frames = [l for l in lines if l["kind"] == "frame"]
    assert frames[0]["cost"]["scanStepMs"] == 60                 # tick 12: one chunk of 60 squares
    assert frames[0]["cost"]["senseMs"] == 0                     # the chunk is not the frame's sense cost
    assert frames[1]["cost"]["scanStepMs"] == 0                  # tick 24: the job is done


def test_main_second_scan_replaces_a_running_one(lua, fs):
    import json
    load(lua)
    g = lua.globals(); g.getPlayer = lambda: make_player()
    scan_world(lua, 10, 20, 15)
    lua.execute("PZA.main.init('admin')"); lua.execute("PZA.main.ready = true")
    fs.files["pzagent/admin/cmd.txt"] = "seq=1\ngoal=scan\nargs=15\n"
    for _ in range(3):
        g._handlers[0]()
    fs.files["pzagent/admin/cmd.txt"] = "seq=2\ngoal=scan\nargs=1\n"
    for _ in range(30):
        g._handlers[0]()
    scans = [json.loads(l) for l in fs.files["pzagent/admin/state.log"].splitlines() if '"kind":"scan"' in l]
    assert [s["r"] for s in scans] == [1] and scans[0]["scanTicks"] == 1 and len(scans[0]["squares"]) == 9


# ---- Task 11 fix 1: the sleep gates; fight drops its step-back; flee resets running ------------

def server_options(lua, allowed=True, needed=True):
    """isClient() true and getServerOptions():getBoolean(name) answering from the dict (an absent key is nil)"""
    g = lua.globals()
    opts = {}
    if allowed is not None:
        opts["SleepAllowed"] = allowed
    if needed is not None:
        opts["SleepNeeded"] = needed
    g.isClient = lambda: True
    so = J(getBoolean=lambda s, k: opts.get(k))
    g.getServerOptions = lambda: so


def sleep_tick(lua, p, seq):
    lua.eval("PZA.act.start({seq=%d, goal='sleep', args=''})" % seq)
    return tick(lua, p)


def test_sleep_on_a_client_honours_sleep_allowed(lua):
    load(lua)
    g = lua.globals()
    p = make_player()
    server_options(lua, allowed=False)
    st = sleep_tick(lua, p, 1)
    assert st["state"] == "failed" and st["detail"] == "not allowed" and list(g._sleeps) == []
    server_options(lua, allowed=None)                   # an unreadable option fails closed
    assert sleep_tick(lua, p, 2)["detail"] == "not allowed" and list(g._sleeps) == []
    server_options(lua, allowed=True, needed=False)
    assert sleep_tick(lua, p, 3)["state"] == "running" and len(g._sleeps) == 1


def test_sleep_needed_refuses_within_an_hour_of_the_last_sleep(lua):
    load(lua)
    g = lua.globals()
    hours = {"v": 30.5}
    p = make_player()
    p.getHoursSurvived = lambda s: hours["v"]
    p.getLastHourSleeped = lambda s: 30
    server_options(lua, allowed=True, needed=True)
    assert sleep_tick(lua, p, 1)["detail"] == "not allowed" and list(g._sleeps) == []
    server_options(lua, allowed=True, needed=False)     # SleepNeeded off: no too-early gate
    assert sleep_tick(lua, p, 2)["state"] == "running" and len(g._sleeps) == 1
    server_options(lua, allowed=True, needed=True)
    hours["v"] = 31.5
    assert sleep_tick(lua, p, 3)["state"] == "running" and len(g._sleeps) == 2
    g.isClient = lambda: False                          # not a client: sleep is needed, the gate applies
    hours["v"] = 31.0
    assert sleep_tick(lua, p, 4)["detail"] == "not allowed" and len(g._sleeps) == 2


def test_fight_clears_a_step_back_dropped_when_the_zombies_leave(lua):
    load(lua)
    g = lua.globals()
    g._cell = make_cell(zombies=[make_zombie(7, 10.5, 20.0)], squares=open_squares(10, 20))
    p = make_player(weapon=weapon())
    lua.eval("PZA.act.start({seq=1, goal='fight', args=''})")
    tick(lua, p, 2)                                      # the swing, then the step back queued
    assert g._queue.adds[-1].Type == "ISWalkToTimedAction" and g._queue.cleared == 0
    g._cell = make_cell(squares=open_squares(10, 20))
    tick(lua, p)
    assert g._queue.cleared == 1 and g._queue.queue == []
    assert tick(lua, p, 58)["state"] == "running" and g._queue.cleared == 1
    st = tick(lua, p)
    assert st["detail"] == "clear" and g._queue.cleared == 2


def test_fight_clears_a_step_back_that_failed(lua):
    load(lua)
    g = lua.globals()
    squares = open_squares(10, 20)
    g._cell = make_cell(zombies=[make_zombie(7, 10.5, 20.0)], squares=squares)
    p = make_player(weapon=weapon())
    lua.eval("PZA.act.start({seq=1, goal='fight', args=''})")
    tick(lua, p, 2)
    tick(lua, p, 4 * 90 - 1)                            # the player never moves: three re-plans, each a clear
    assert g._queue.cleared == 3
    tick(lua, p)                                        # the walk fails stuck: the fight drops and clears it
    assert g._queue.cleared == 4 and lua.eval("PZA.act.status().state") == "running"


def test_flee_resets_running_when_it_ends(lua):
    load(lua)
    g = lua.globals()
    g._cell = make_cell(squares=open_squares(10, 20))
    pos = {"x": 10.0}
    p = make_player(); p.getX = lambda s: pos["x"]
    runs = []
    p.setRunning = lambda s, v: runs.append(v)
    lua.eval("PZA.act.start({seq=1, goal='flee', args='18 20'})")
    tick(lua, p)
    pos["x"] = 18.2
    assert tick(lua, p)["detail"] == "at" and runs == [True, False]
    g._cell = make_cell(squares={})
    runs[:] = []
    lua.eval("PZA.act.start({seq=2, goal='flee', args='18 20'})")
    assert tick(lua, p)["detail"] == "cornered" and runs == [False]
