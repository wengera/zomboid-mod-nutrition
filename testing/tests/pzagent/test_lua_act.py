import pytest
from .conftest import lua_file, make_player, make_cell, make_zombie, J


def load(lua):
    for f in ("client/PZAgent_Link.lua", "client/PZAgent_Sense.lua", "client/PZAgent_Act.lua", "client/PZAgent_Main.lua",
              "client/PZAgent_Motor.lua", "client/PZAgent_Bench.lua"):
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
    assert '"kind":"scanPart"' in log and log.count('"kind":"ack"') == 3 and '"done":true' in log and '"scanMs":' in log


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
    used = set(re.findall(r'(?:"failed",\s*|failWalk\(p, g, )"([^"]+)"', src))
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
    assert kinds[:3] == ["hello", "bench", "ack"] and lua.eval("PZA.errors") == 0


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
    z = make_zombie(7, 11.0, 20.0)                      # 1 tile east: inside REACH_R
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
    g._cell = make_cell(zombies=[make_zombie(1, 11.0, 20.0)])
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
    assert st["state"] == "running" and runs == [True, True] and (walk.sq.getX(walk.sq), walk.sq.getY(walk.sq)) == (18, 20)
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
    used = set(re.findall(r'(?:"failed",\s*|failWalk\(p, g, )"([^"]+)"', src))
    for x in ("no weapon", "weapon broke", "low health", "cornered", "not allowed", "interrupted"):
        assert x in used and x in closed
    done = set([l for l in src.splitlines() if l.startswith("-- done: ")][0][len("-- done: "):].strip().split("|"))
    for x in ("clear", "at", "awake"):
        assert x in done and x not in closed and re.search(r'"done",\s*"%s"' % x, src)


# ---- Stage A pass 2 and 3: goto fails dead; the chunked scan, emitted in parts --------------------

ALL_GOALS = (("goto", "13 20"), ("open", "13 20"), ("loot", "13 20"), ("eat", "Base.Apple"), ("drink", ""),
             ("fight", ""), ("flee", "13 20"), ("sleep", ""))          # stop is exempt (fix 1)


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


# ---- Stage A pass 3: stuck is no movement; a failed goto clears its walk -----------------------------------------

def run_goto(lua, p, n):
    states = []
    for _ in range(n):
        st = tick(lua, p)
        states.append((st["state"], st["detail"]))
        p.t["n"] += 1
        if st["state"] != "running":
            break
    return states


def timed_player(**axes):
    """make_player whose getX/getY are functions of p.t['n'], the tick count run_goto advances."""
    p = make_player()
    p.t = {"n": 0}
    for k, f in axes.items():
        setattr(p, k, (lambda f: lambda s: f(p.t["n"]))(f))
    return p


def test_goto_moving_without_approaching_is_never_stuck(lua):
    load(lua)
    g = lua.globals(); g._cell = make_cell(squares={(13, 20, 0): sq(13, 20)})
    p = timed_player(getX=lambda n: 10.0 if n % 2 == 0 else 10.5)    # moves every tick, never nearer than 2.5
    lua.eval("PZA.act.start({seq=1, goal='goto', args='13 20'}, ...)", p)
    states = run_goto(lua, p, 4 * 90 + 10)
    assert set(states) == {("running", "")} and len(g._queue.adds) == 1   # never a replan


def test_goto_whose_path_grows_the_distance_is_never_stuck(lua):
    load(lua)
    g = lua.globals(); g._cell = make_cell(squares={(13, 20, 0): sq(13, 20)})
    # out of the house by its far door (the distance grows from 3 to 9 over 300 ticks), then round to the target
    p = timed_player(getX=lambda n: 10.0 - 0.02 * n if n < 300 else 4.0 + 0.05 * (n - 300))
    lua.eval("PZA.act.start({seq=1, goal='goto', args='13 20'}, ...)", p)
    states = run_goto(lua, p, 600)
    assert states[-1][0] == "done" and ("failed", "stuck") not in states and len(g._queue.adds) == 1


def test_an_unmoving_player_replans_then_fails_stuck_and_the_failure_clears_the_walk(lua):
    load(lua)
    g = lua.globals(); g._cell = make_cell(squares={(13, 20, 0): sq(13, 20)})
    p = timed_player(getX=lambda n: 10.0 + 0.004 * (n % 2))             # a jitter under STILL_EPS is no movement
    lua.eval("PZA.act.start({seq=1, goal='goto', args='13 20'}, ...)", p)
    states = run_goto(lua, p, 4 * 90 + 10)
    assert states[-1] == ("failed", "stuck") and len(states) == 1 + 4 * 90
    assert len(g._queue.adds) == 4                                     # the first add plus REPLAN_MAX re-adds
    assert g._queue.cleared == 4 and g._queue.queue == []              # three replans, then the failure's own clear


def test_every_failed_goto_exit_clears_its_walk(lua):
    load(lua)
    g = lua.globals(); g._cell = make_cell(squares={})
    lua.eval("PZA.act.start({seq=1, goal='goto', args='13 20'}, ...)", make_player())
    assert tick(lua, make_player())["detail"] == "no square" and g._queue.cleared == 1
    g._cell = make_cell(squares={(13, 20, 0): sq(13, 20)})
    hp = {"v": 100.0}
    p = health_player(hp)
    lua.eval("PZA.act.start({seq=2, goal='goto', args='13 20'}, ...)", p)
    assert tick(lua, p)["state"] == "running" and len(g._queue.queue) == 1
    hp["v"] = 0.0
    assert tick(lua, p)["detail"] == "dead" and g._queue.cleared == 2 and g._queue.queue == []
    g.ISWalkToTimedAction = J(new=lambda cls, p, sq: (_ for _ in ()).throw(RuntimeError("no path")))
    lua.eval("PZA.act.start({seq=3, goal='goto', args='13 20'}, ...)", make_player())
    assert tick(lua, make_player())["detail"] == "no path" and g._queue.cleared == 3


def test_a_failed_sub_walk_clears_once_for_open(lua):
    load(lua)
    g = lua.globals()
    door = J(_cls="IsoDoor", IsOpen=lambda s: False, isLocked=lambda s: False, isBarricaded=lambda s: False)
    squares = open_squares(10, 20)
    squares[(16, 20, 0)] = osq(16, 20, objects=[door])
    g._cell = make_cell(squares=squares)
    p = make_player()                                                  # never moves: the approach walk is stuck
    lua.eval("PZA.act.start({seq=1, goal='open', args='16 20'}, ...)", p)
    st = tick(lua, p, 4 * 90 + 5)
    assert st["state"] == "failed" and st["detail"] == "not adjacent"
    assert g._queue.cleared == 4 and g._queue.queue == []


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


def log_lines(fs):
    import json
    return [json.loads(l) for l in fs.files["pzagent/admin/state.log"].splitlines()]


def test_main_scan_is_queued_and_emitted_one_part_per_tick(lua, fs):
    load(lua)
    g = lua.globals(); g.getPlayer = lambda: make_player()
    scan_world(lua, 10, 20, 15)
    lua.execute("PZA.main.init('admin')"); lua.execute("PZA.main.ready = true")
    fs.files["pzagent/admin/cmd.txt"] = "seq=1\ngoal=scan\nargs=15\n"
    per_tick = []
    for i in range(1, 62):
        n0 = len(log_lines(fs))
        g._handlers[0]()
        lines = log_lines(fs)
        if i == 1:
            acks = [l for l in lines if l["kind"] == "ack"]
            assert len(acks) == 1 and acks[0]["ok"] is True and acks[0]["reason"] == "queued"
        per_tick.append([l["part"] for l in lines[n0:] if l["kind"] == "scanPart"])
    assert per_tick == [[k] for k in range(1, 50)] + [[]] * 12      # ceil(961 / 20) parts, one a tick, each flushed
    lines = log_lines(fs)
    assert not any(l["kind"] == "scan" for l in lines)
    parts = [l for l in lines if l["kind"] == "scanPart"]
    assert {p["scanId"] for p in parts} == {1} and {p["parts"] for p in parts} == {49} and {p["r"] for p in parts} == {15}
    assert [p.get("done") for p in parts] == [None] * 48 + [True] and sum(len(p["squares"]) for p in parts) == 961
    last = parts[-1]
    assert last["scanTicks"] == 49 and last["scanMs"] == 961 and last["scanStepMaxMs"] == 20
    for k in ("hour", "missing", "gameMin", "worldAge"):
        assert k in last
    assert "gameMin" not in parts[0]
    frames = [l for l in lines if l["kind"] == "frame"]
    assert frames[0]["cost"]["scanStepMs"] == 20                 # tick 12: one chunk of 20 squares (its emit costs 0 here)
    assert frames[0]["cost"]["senseMs"] == 0                     # the chunk is not the frame's sense cost
    assert [f["cost"]["scanStepMs"] for f in frames[1:4]] == [20] * 3   # ticks 24, 36, 48: the job still walks
    assert frames[4]["cost"]["scanStepMs"] == 0                  # tick 60: the job is done (its last part on tick 49)


def test_main_second_scan_replaces_a_running_one_and_its_parts_stop(lua, fs):
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
    parts = [l for l in log_lines(fs) if l["kind"] == "scanPart"]
    assert [(p["scanId"], p["part"], p.get("done")) for p in parts] == [(1, 1, None), (1, 2, None), (1, 3, None),
                                                                        (2, 1, True)]
    assert parts[-1]["r"] == 1 and len(parts[-1]["squares"]) == 9 and parts[-1]["scanTicks"] == 1
    assert parts[-1]["emitMs"] == 0                              # a new scan's first part carries no emit


def floor_cost_writes(lua, fs):
    """Every file write costs 1 ms of the fixture clock per square it carries (its '"floor"' keys), so a part's emit
    and flush reads its own square count."""
    clock = lua.globals()._clock

    def writer(name, create, append):
        w = fs.writer(name, create, append)
        if w is None:
            return None

        class CW:
            def write(self, s):
                clock["ms"] += s.count('"floor"')
                w.write(s)

            def close(self):
                w.close()
        return CW()
    lua.globals().getFileWriter = writer


def test_each_part_carries_the_previous_parts_emit_and_the_next_frame_the_last_ones(lua, fs):
    load(lua)
    g = lua.globals(); g.getPlayer = lambda: make_player()
    scan_world(lua, 10, 20, 15)
    lua.execute("PZA.main.init('admin')"); lua.execute("PZA.main.ready = true")
    for _ in range(4):                                           # the r=15 job starts on tick 5: parts on ticks 5-53
        g._handlers[0]()
    floor_cost_writes(lua, fs)
    fs.files["pzagent/admin/cmd.txt"] = "seq=1\ngoal=scan\nargs=15\n"
    for _ in range(72):
        g._handlers[0]()
    lines = log_lines(fs)
    parts = [l for l in lines if l["kind"] == "scanPart"]
    frames = [l for l in lines if l["kind"] == "frame"]
    assert [p["emitMs"] for p in parts] == [0] + [20] * 48      # part i carries part i-1's emit (20 squares, 20 ms)
    assert [p["stepMs"] for p in parts] == [20] * 48 + [1]
    last = parts[-1]
    after = [f for f in frames if f["seq"] > last["seq"]]
    assert after[0]["cost"]["scanEmitMs"] == 1                   # the last part's own emit: one square, 1 ms
    assert after[1]["cost"]["scanEmitMs"] == 0                   # reported once
    assert all(f["cost"]["scanEmitMs"] == 0 for f in frames if f["seq"] < last["seq"])   # a mid-scan frame carries none
    mid = [f for f in frames if parts[0]["seq"] < f["seq"] < last["seq"]]
    assert mid and all(f["cost"]["scanStepMs"] == 40 for f in mid)   # the tick's 20 ms walk plus its 20 ms part emit


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
    tick(lua, p)                                        # the walk fails stuck and clears itself; the fight drops it
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
    assert tick(lua, p)["detail"] == "at" and runs == [True, True, False]
    g._cell = make_cell(squares={})
    runs[:] = []
    lua.eval("PZA.act.start({seq=2, goal='flee', args='18 20'})")
    assert tick(lua, p)["detail"] == "cornered" and runs == [False]


# ---- Stage A pass 2 fix 1: stop allowed when dead; the completing scan emit carried on the next frame ----------

def test_a_dead_player_may_still_stop_a_running_goal(lua):
    load(lua)
    g = lua.globals(); g._cell = make_cell(squares={(13, 20, 0): sq(13, 20)})
    hp = {"v": 100.0}
    p = health_player(hp)
    assert lua.eval("PZA.act.start({seq=1, goal='sleep', args=''}, ...)", p)[0] is True
    hp["v"] = 0.0
    assert lua.eval("PZA.act.start({seq=2, goal='goto', args='13 20'}, ...)", p) == (False, "dead")
    ok, reason, old = lua.eval("PZA.act.start({seq=3, goal='stop', args=''}, ...)", p)
    assert ok is True and old["seq"] == 1 and old["detail"] == "superseded"
    st = tick(lua, p)
    assert st["name"] == "stop" and st["state"] == "done"


def test_the_frame_after_a_completed_scan_carries_its_emit_cost_once(lua, fs):
    import json
    load(lua)
    g = lua.globals(); g.getPlayer = lambda: make_player()
    scan_world(lua, 10, 20, 1)                                   # 9 squares: one chunk, done on its first tick
    lua.execute("PZA.main.init('admin')"); lua.execute("PZA.main.ready = true")
    for _ in range(10):                                          # to tick 10, before the tick-12 frame
        g._handlers[0]()
    fs.write_cost_ms = 4                                         # every file write costs 4 ms from here
    fs.files["pzagent/admin/cmd.txt"] = "seq=1\ngoal=scan\nargs=1\n"
    g._handlers[0]()                                             # tick 11: the ack flush (4), then the scan line's
    for _ in range(13):
        g._handlers[0]()
    lines = [json.loads(l) for l in fs.files["pzagent/admin/state.log"].splitlines()]
    scan = [l for l in lines if l["kind"] == "scanPart"][0]
    assert scan["done"] is True and scan["part"] == scan["parts"] == 1 and scan["emitMs"] == 0
    frames = [l for l in lines if l["kind"] == "frame"]
    assert scan["scanTicks"] == 1 and scan["scanStepMaxMs"] == 9
    after = [f for f in frames if f["seq"] > scan["seq"]]
    assert after[0]["cost"]["scanEmitMs"] == 4                   # the scan line's own emit and flush
    assert after[1]["cost"]["scanEmitMs"] == 0                   # reported once
    assert all(f["cost"]["scanEmitMs"] == 0 for f in frames if f["seq"] < scan["seq"])


# ---- Plan 21b Task 1: the vanilla classes index-checked before every action build ------------------------------

def count_failed_pcalls(lua):
    """Wraps the global pcall so every caught raise is counted in _G.pcallFails: a guard that index-checks before the
    call leaves it at 0 (a caught raise still parks a -debug client)."""
    lua.execute("pcallFails = 0\n"
                "local rawPcall = pcall\n"
                "pcall = function(...)\n"
                "    local r = { rawPcall(...) }\n"
                "    if not r[1] then pcallFails = pcallFails + 1 end\n"
                "    return unpack(r)\n"
                "end")


def test_a_goto_without_the_vanilla_walk_class_fails_no_path_and_raises_nothing(lua):
    load(lua)
    count_failed_pcalls(lua)
    g = lua.globals(); g._cell = make_cell(squares={(13, 20, 0): sq(13, 20)})
    g.ISWalkToTimedAction = None
    p = make_player()
    lua.eval("PZA.act.start({seq=1, goal='goto', args='13 20'}, ...)", p)
    st = tick(lua, p)
    assert st["state"] == "failed" and st["detail"] == "no path" and g._queue.adds == []
    assert g.pcallFails == 0 and g._queue.cleared == 1          # failWalk still clears through the loaded queue
    g.ISWalkToTimedAction = J()                                 # the class without its new
    lua.eval("PZA.act.start({seq=2, goal='goto', args='13 20'}, ...)", p)
    assert tick(lua, p)["detail"] == "no path" and g.pcallFails == 0 and g._queue.adds == []


def test_a_goto_without_the_vanilla_queue_fails_no_path_and_raises_nothing(lua):
    load(lua)
    count_failed_pcalls(lua)
    g = lua.globals(); g._cell = make_cell(squares={(13, 20, 0): sq(13, 20)})
    g.ISTimedActionQueue = None
    p = make_player()
    lua.eval("PZA.act.start({seq=1, goal='goto', args='13 20'}, ...)", p)
    st = tick(lua, p)
    assert st["state"] == "failed" and st["detail"] == "no path" and g.pcallFails == 0
    lua.eval("PZA.act.start({seq=2, goal='stop', args=''}, ...)", p)   # stop clears nothing it cannot index
    assert tick(lua, p)["state"] == "done" and g.pcallFails == 0


def test_a_loot_without_the_vanilla_transfer_class_fails_not_loaded(lua):
    load(lua)
    count_failed_pcalls(lua)
    lua.globals().ISInventoryTransferAction = None
    g, box, held, p = loot_world(lua, [item("Base.Bread", "Food")], filt="food")
    st = tick(lua, p)
    assert st["state"] == "failed" and st["detail"] == "not loaded"     # the class not loaded, not "no match"
    assert g._queue.adds == [] and g.pcallFails == 0
    g.ISInventoryTransferAction = J()                                   # the class without its new
    g, box, held, p = loot_world(lua, [item("Base.Bread", "Food")], filt="food")
    assert tick(lua, p)["detail"] == "not loaded" and g._queue.adds == [] and g.pcallFails == 0


def test_an_eat_whose_constructor_lacks_new_is_refused_before_any_call(lua):
    load(lua)
    count_failed_pcalls(lua)
    g = lua.globals()
    g.ISEatFoodAction = J()                                     # the class without its new: queueConsume returns false
    p = inv_player([item("Base.Bread", "Food")])
    lua.eval("PZA.act.start({seq=1, goal='eat', args='Base.Bread'})")
    st = tick(lua, p)
    assert st["state"] == "failed" and st["detail"] == "not valid" and g._queue.adds == [] and g.pcallFails == 0


def test_an_action_without_is_valid_start_or_a_missing_queue_is_refused_before_any_call(lua):
    load(lua)
    count_failed_pcalls(lua)
    g = lua.globals()
    g.ISEatFoodAction = J(new=lambda cls, p, it, pct: J(Type="ISEatFoodAction"))   # no isValidStart
    p = inv_player([item("Base.Bread", "Food")])
    lua.eval("PZA.act.start({seq=1, goal='eat', args='Base.Bread'})")
    assert tick(lua, p)["detail"] == "not valid" and g._queue.adds == [] and g.pcallFails == 0
    q = g._queue
    g.ISTimedActionQueue = J(clear=lambda p: q.clear(p))       # the queue without its add
    fc = J(isEmpty=lambda s: False, isPoisonous=lambda s: False, isFilledWithCleanWater=lambda s: True,
           getAmount=lambda s: 1.0)
    p = inv_player([item("Base.WaterBottle", fluid=fc)])
    lua.eval("PZA.act.start({seq=2, goal='drink', args=''})")
    assert tick(lua, p)["detail"] == "not valid" and q.adds == [] and g.pcallFails == 0


def test_an_open_whose_constructor_lacks_new_or_whose_queue_lacks_add_fails_no_door(lua):
    load(lua)
    count_failed_pcalls(lua)
    g = lua.globals()
    g._cell = make_cell(squares={(11, 20, 0): osq(11, 20, [make_door()])})
    p = make_player()
    g.ISOpenCloseDoor = J()
    lua.eval("PZA.act.start({seq=1, goal='open', args='11 20'})")
    assert tick(lua, p)["detail"] == "no door" and g._queue.adds == [] and g.pcallFails == 0
    g.ISOpenCloseDoor = J(new=lambda cls, p, item: J(Type="ISOpenCloseDoor"))
    q = g._queue
    g.ISTimedActionQueue = J(clear=lambda p: q.clear(p))
    lua.eval("PZA.act.start({seq=2, goal='open', args='11 20'})")
    assert tick(lua, p)["detail"] == "no door" and q.adds == [] and g.pcallFails == 0


# ---- Plan 21b Stage B pass 2: approach skips solidTrans squares ---------------------------------

def test_loot_approach_skips_a_solidtrans_neighbour_and_walks_to_the_next_free_one(lua):
    """Pass 1's rep 5 (b_actions-20261026-183143): the nearest neighbour of the container was a stove square
    (isSolid false, isSolidTrans true), the walk stuck and the loot failed `not adjacent`."""
    load(lua)
    g = lua.globals()
    box = make_container([item("Base.Bread", "Food")])
    obj = J(_cls="IsoObject", getContainerCount=lambda s: 1, getContainerByIndex=lambda s, i: box)
    stove = osq(12, 20)
    stove.isSolidTrans = lambda s: True
    plain = osq(12, 21)                                    # no isSolidTrans member: counts as not solidTrans
    g._cell = make_cell(squares={(13, 20, 0): osq(13, 20, [obj]), (12, 20, 0): stove, (12, 21, 0): plain})
    p = inv_player([], x=10.0, y=20.0)
    lua.eval("PZA.act.start({seq=1, goal='loot', args='13 20 food'})")
    st = tick(lua, p)
    adds = g._queue.adds
    assert st["state"] == "running" and [a.Type for a in adds] == ["ISWalkToTimedAction"]
    assert (adds[0].sq.getX(adds[0].sq), adds[0].sq.getY(adds[0].sq)) == (12, 21)
    g._cell = make_cell(squares={(13, 20, 0): osq(13, 20, [obj]), (12, 20, 0): stove})
    lua.eval("PZA.act.start({seq=2, goal='loot', args='13 20 food'})")
    assert tick(lua, p)["detail"] == "not adjacent"        # the stove alone: no free neighbour


# ---- Stage C pass 2 Lua: the fight closes to its reach before swinging; a run-flagged walk asks to run every tick ----

def test_fight_steps_toward_a_zombie_out_of_reach_and_never_swings_there(lua):
    load(lua)
    g = lua.globals()
    zpos = {"x": 12.5, "y": 20.0}                       # 2.5 tiles east of the player at (10, 20): inside FIGHT_R, out of reach
    z = J(getOnlineID=lambda s: 7, getX=lambda s: zpos["x"], getY=lambda s: zpos["y"], isDead=lambda s: False,
          getTarget=lambda s: None, isCrawling=lambda s: False)
    g._cell = make_cell(zombies=[z], squares=open_squares(10, 20))
    p = make_player(weapon=weapon())
    lua.eval("PZA.act.start({seq=1, goal='fight', args=''})")
    st = tick(lua, p)
    walk = g._queue.adds[-1]
    assert st["state"] == "running" and p.attacks == [] and p.faced == []
    assert walk.Type == "ISWalkToTimedAction" and (walk.sq.getX(walk.sq), walk.sq.getY(walk.sq)) == (12, 20)
    tick(lua, p, 5)
    assert len(g._queue.adds) == 1 and p.attacks == []  # the step runs; it is not re-queued each tick
    zpos["y"] = 21.2                                    # the zombie moves to another square: the step is re-aimed
    tick(lua, p)
    walk = g._queue.adds[-1]
    assert len(g._queue.adds) == 2 and g._queue.cleared == 1 and p.attacks == []
    assert (walk.sq.getX(walk.sq), walk.sq.getY(walk.sq)) == (12, 21)  # the zombie's own square
    zpos["x"], zpos["y"] = 11.0, 20.0                   # within reach (1.125): the step is dropped and the swing runs
    tick(lua, p)
    assert g._queue.cleared == 2 and g._queue.queue == [] and p.attacks == [0] and p.faced == [z]
    assert len(g._queue.adds) == 2


def test_fight_swings_inside_reach_and_queues_no_step(lua):
    load(lua)
    g = lua.globals()
    z = make_zombie(7, 11.1, 20.0)                      # 1.1 tiles: inside the fallback reach 1.25 x 0.9 = 1.125
    g._cell = make_cell(zombies=[z], squares=open_squares(10, 20))
    p = make_player(weapon=weapon())
    lua.eval("PZA.act.start({seq=1, goal='fight', args=''})")
    tick(lua, p, 3)
    assert p.attacks == [0] and g._queue.adds == []     # one swing (the cooldown holds the rest), no walk


def test_flee_asks_to_run_and_sprint_every_tick_and_clears_both_once_at_the_end(lua):
    load(lua)
    g = lua.globals()
    g._cell = make_cell(squares=open_squares(10, 20))
    pos = {"x": 10.0}
    p = make_player(); p.getX = lambda s: pos["x"]
    runs, sprints = [], []
    p.setRunning = lambda s, v: runs.append(v)
    p.setSprinting = lambda s, v: sprints.append(v)
    lua.eval("PZA.act.start({seq=1, goal='flee', args='18 20'})")
    tick(lua, p)                                        # the walk's own start sets the run once, then the tick's ask
    assert runs == [True, True] and sprints == [True]
    for i in range(4):
        pos["x"] += 1.0
        tick(lua, p)
    assert runs == [True] * 6 and sprints == [True] * 5
    pos["x"] = 18.2
    assert tick(lua, p)["detail"] == "at"
    assert runs == [True] * 6 + [False] and sprints == [True] * 5 + [False]
    tick(lua, p, 3)                                     # the finished flee asks nothing more
    assert runs[-1] is False and runs.count(False) == 1 and sprints.count(False) == 1


def test_a_walking_step_never_asks_to_run(lua):
    load(lua)
    g = lua.globals()
    g._cell = make_cell(zombies=[make_zombie(7, 12.5, 20.0)], squares=open_squares(10, 20))
    p = make_player(weapon=weapon())
    runs, sprints = [], []
    p.setRunning = lambda s, v: runs.append(v)
    p.setSprinting = lambda s, v: sprints.append(v)
    lua.eval("PZA.act.start({seq=1, goal='fight', args=''})")
    tick(lua, p, 4)
    assert g._queue.adds[-1].Type == "ISWalkToTimedAction" and runs == [] and sprints == []


# ---- Task 7c fix 1: the closing step reaches the zombie; the reach is the weapon's; a superseded run is cleared ----

def ranged_weapon(max_range=None, range_mod=None):
    """a weapon stub whose getMaxRange(chr) and getRangeMod(chr) answer the given values (None: the member is absent)"""
    w = weapon()
    if max_range is not None:
        w.getMaxRange = lambda s, chr: max_range
    if range_mod is not None:
        w.getRangeMod = lambda s, chr: range_mod
    return w


def test_reach_is_the_weapons_max_range_times_range_mod_times_the_margin(lua):
    load(lua)
    p = make_player()
    reach = lambda w: lua.eval("PZA.act.reachOf(...)", p, w)
    assert reach(ranged_weapon(1.25, 1.0)) == pytest.approx(1.125)
    assert reach(ranged_weapon(1.25, 1.2)) == pytest.approx(1.35)
    assert reach(ranged_weapon(1.25, None)) == pytest.approx(1.125)    # getRangeMod absent: the fallback 1.25
    assert reach(ranged_weapon(None, 1.2)) == pytest.approx(1.125)     # getMaxRange absent: the fallback
    assert reach(ranged_weapon(2.0, None)) == pytest.approx(1.125)


def walking_fight(lua, zx, w, ticks=200, speed=0.05):
    """a fight against a zombie standing at (zx, 20) from a player at (10, 20) who walks `speed` tiles a tick toward
    the queued walk's square centre while a walk is queued (the review's probe); returns the player's distance to
    the zombie at each DoAttack, the walk adds, and the player"""
    g = lua.globals()
    z = make_zombie(7, zx, 20.0)
    g._cell = make_cell(zombies=[z], squares=open_squares(10, 20))
    pos = {"x": 10.0, "y": 20.0}
    p = make_player(weapon=w)
    p.getX, p.getY = (lambda s: pos["x"]), (lambda s: pos["y"])
    swings_at = []
    p.DoAttack = lambda s, f: swings_at.append(((zx - pos["x"]) ** 2 + (20.0 - pos["y"]) ** 2) ** 0.5) or True
    lua.eval("PZA.act.start({seq=1, goal='fight', args=''})")
    for _ in range(ticks):
        tick(lua, p)
        g._clock["ms"] += 100                          # 10 ticks a second: the 1200 ms swing cadence comes round
        if g._queue.queue:
            sq = g._queue.queue[-1].sq
            tx, ty = sq.getX(sq) + 0.5, sq.getY(sq) + 0.5
            ex, ey = tx - pos["x"], ty - pos["y"]
            n = (ex * ex + ey * ey) ** 0.5
            if n > 0:
                step = min(speed, n)
                pos["x"] += ex / n * step
                pos["y"] += ey / n * step
    return swings_at, len(g._queue.adds), lua.eval("PZA.act.status().state")


@pytest.mark.parametrize("zx", [12.74, 12.0])
@pytest.mark.parametrize("w,reach", [(None, 1.125), ((1.25, 1.0), 1.125), ((1.25, 1.2), 1.35)])
def test_a_walking_player_closes_on_a_standing_zombie_and_swings_inside_the_weapons_reach(lua, zx, w, reach):
    load(lua)
    wep = weapon() if w is None else ranged_weapon(*w)
    swings_at, adds, state = walking_fight(lua, zx, wep)
    assert state == "running" and len(swings_at) >= 2           # it reached the zombie and kept swinging
    assert all(d <= reach + 1e-9 for d in swings_at)            # never a swing outside the reach
    assert adds <= 2                                            # one closing walk (review probe: 188-198 adds before)


def test_a_closing_walk_that_ends_short_of_reach_swings_from_there_and_never_re_queues(lua):
    load(lua)
    g = lua.globals()
    z = make_zombie(7, 12.95, 20.95)                    # the far corner of square (12, 20): its centre is 0.64 tiles off
    g._cell = make_cell(zombies=[z], squares=open_squares(10, 20))
    pos = {"x": 11.0, "y": 19.0}                        # 2.76 tiles off, approaching along the diagonal
    p = make_player(weapon=ranged_weapon(1.2, 1.0))     # reach 1.08: the walk ends done 0.5 from the centre, 1.14 off
    p.getX, p.getY = (lambda s: pos["x"]), (lambda s: pos["y"])
    lua.eval("PZA.act.start({seq=1, goal='fight', args=''})")
    for _ in range(120):
        tick(lua, p)
        g._clock["ms"] += 100
        if g._queue.queue:
            sq = g._queue.queue[-1].sq
            ex, ey = sq.getX(sq) + 0.5 - pos["x"], sq.getY(sq) + 0.5 - pos["y"]
            n = (ex * ex + ey * ey) ** 0.5
            pos["x"] += ex / n * min(0.05, n)
            pos["y"] += ey / n * min(0.05, n)
    assert len(g._queue.adds) == 1 and len(p.attacks) >= 2  # one walk; the fight swings from where it ended


def test_a_superseded_flee_and_a_stop_clear_the_run_and_sprint_flags(lua):
    load(lua)
    g = lua.globals()
    g._cell = make_cell(zombies=[make_zombie(7, 11.0, 20.0)], squares=open_squares(10, 20))
    p = make_player(weapon=weapon())
    runs, sprints = [], []
    p.setRunning = lambda s, v: runs.append(v)
    p.setSprinting = lambda s, v: sprints.append(v)
    lua.eval("PZA.act.start({seq=1, goal='flee', args='18 20'}, ...)", p)
    tick(lua, p)
    assert runs[-1] is True and sprints[-1] is True
    ok, _, old = lua.eval("PZA.act.start({seq=2, goal='fight', args=''}, ...)", p)
    assert ok is True and old["detail"] == "superseded"
    assert runs[-1] is False and sprints[-1] is False
    runs[:], sprints[:] = [], []
    lua.eval("PZA.act.start({seq=3, goal='stop', args=''}, ...)", p)
    assert runs == [False] and sprints == [False]               # the superseded fight; stop's own tick follows
    tick(lua, p)
    assert runs == [False, False] and sprints == [False, False]


# ---- Plan 22 probe X1-X3: the goto motor arms, A.motorOff, autowalk, drop ---------------------------------------------

OFF = [("setRunning", False), ("setSprinting", False), ("setForceRun", False), ("setForceSprint", False),
       ("setAutoWalk", False)]


def arm_goto(lua, arm, seq=1):
    """a goto to (13, 20) with the given arm and a player at x = pos['x'] (10.0: running until pos['x'] >= 12)"""
    g = lua.globals(); g._cell = make_cell(squares={(13, 20, 0): sq(13, 20)})
    pos = {"x": 10.0}
    p = make_player(); p.getX = lambda s: pos["x"]
    args = "13 20" if arm is None else "13 20 " + arm
    ok, reason, _ = lua.eval("PZA.act.start({seq=%d, goal='goto', args='%s'}, ...)" % (seq, args), p)
    assert ok is True, reason
    return g, p, pos


def tick_sets(lua, p):
    """one tick; the motor sets it made"""
    n = len(p.sets)
    st = tick(lua, p)
    return st, p.sets[n:]


def motor(lua, key):
    return lua.eval("PZA.motor.%s" % key)


@pytest.mark.parametrize("arm", [None, "walk"])
def test_a_walk_arm_asks_nothing_and_its_done_turns_every_motor_ask_off(lua, arm):
    load(lua)
    g, p, pos = arm_goto(lua, arm)
    for _ in range(3):
        st, made = tick_sets(lua, p)
        assert st["state"] == "running" and made == []
    pos["x"] = 12.6
    st, made = tick_sets(lua, p)
    assert st["state"] == "done" and made == OFF
    assert motor(lua, "forceRun") is False and motor(lua, "forceSprint") is False


@pytest.mark.parametrize("arm", ["setrun", "run"])
def test_a_setrun_arm_asks_run_and_sprint_every_tick_from_the_tick(lua, arm):
    load(lua)
    g, p, pos = arm_goto(lua, arm)
    for _ in range(4):
        st, made = tick_sets(lua, p)
        assert st["state"] == "running"
        assert ("setRunning", True) in made and made.count(("setSprinting", True)) == 1
        assert not any(n in ("setForceRun", "setForceSprint") for n, _ in made)
    assert motor(lua, "forceRun") is False
    pos["x"] = 12.6
    st, made = tick_sets(lua, p)
    assert st["state"] == "done" and made == OFF


def test_a_forcerun_arm_sets_the_motor_flag_and_never_calls_set_force_run_from_the_tick(lua):
    load(lua)
    g, p, pos = arm_goto(lua, "forcerun")
    for _ in range(3):
        st, made = tick_sets(lua, p)
        assert st["state"] == "running" and made == [] and motor(lua, "forceRun") is True
    assert motor(lua, "forceSprint") is False
    pos["x"] = 12.6
    st, made = tick_sets(lua, p)
    assert st["state"] == "done" and made == OFF and motor(lua, "forceRun") is False


def test_the_forcerun_arm_reaches_the_player_through_the_on_player_update_handler(lua):
    load(lua)
    g, p, pos = arm_goto(lua, "forcerun")
    tick(lua, p)
    g._updHandlers[0](p)
    g._updHandlers[0](p)
    assert p.sets == [("setForceRun", True)] * 2
    pos["x"] = 12.6
    tick(lua, p)
    g._updHandlers[0](p)
    assert p.sets[-len(OFF):] == OFF                    # the handler asks nothing once the goal is over


def test_a_forcerun_tick_arm_asks_set_force_run_every_tick_and_leaves_the_motor_flag_clear(lua):
    load(lua)
    g, p, pos = arm_goto(lua, "forcerun_tick")
    for _ in range(4):
        st, made = tick_sets(lua, p)
        assert st["state"] == "running" and made == [("setForceRun", True)] and motor(lua, "forceRun") is False
    pos["x"] = 12.6
    st, made = tick_sets(lua, p)
    assert st["state"] == "done" and made == OFF


def test_a_forcesprint_arm_sets_both_motor_flags(lua):
    load(lua)
    g, p, pos = arm_goto(lua, "forcesprint")
    st, made = tick_sets(lua, p)
    assert made == [] and motor(lua, "forceRun") is True and motor(lua, "forceSprint") is True
    g._updHandlers[0](p)
    assert p.sets == [("setForceRun", True), ("setForceSprint", True)]
    pos["x"] = 12.6
    tick(lua, p)
    assert motor(lua, "forceRun") is False and motor(lua, "forceSprint") is False


@pytest.mark.parametrize("was", [False, True])
def test_a_toggle_arm_sets_toggle_to_run_once_and_restores_the_value_read_before(lua, was):
    load(lua)
    g, p, pos = arm_goto(lua, "toggle")
    g._core.toggle = was
    tick(lua, p, 3)
    assert list(g._core.toggles) == [True] and motor(lua, "toggleWas") is was and motor(lua, "forceRun") is True
    pos["x"] = 12.6
    assert tick(lua, p)["state"] == "done"
    assert list(g._core.toggles) == [True, was] and g._core.toggle is was and motor(lua, "toggleWas") is None
    assert motor(lua, "forceRun") is False


def test_an_unknown_arm_is_bad_args(lua):
    load(lua)
    assert lua.eval("PZA.act.start({seq=1, goal='goto', args='13 20 sprint'})") == (False, "bad args")
    assert lua.eval("PZA.act.start({seq=2, goal='goto', args='13 20 once'})") == (False, "bad args")


def test_a_stuck_failure_turns_the_motor_off(lua):
    load(lua)
    g, p, pos = arm_goto(lua, "forcesprint")
    st = tick(lua, p, 4 * 90 + 5)
    assert st["state"] == "failed" and st["detail"] == "stuck"
    assert p.sets[-len(OFF):] == OFF and motor(lua, "forceRun") is False and motor(lua, "forceSprint") is False


def test_a_no_square_failure_turns_the_motor_off(lua):
    load(lua)
    g, p, pos = arm_goto(lua, "forcerun")
    g._cell = make_cell(squares={})
    st, made = tick_sets(lua, p)
    assert st["detail"] == "no square" and made == OFF and motor(lua, "forceRun") is False


def test_a_superseded_goto_and_a_stop_turn_the_motor_off(lua):
    load(lua)
    g, p, pos = arm_goto(lua, "toggle")
    tick(lua, p)
    assert motor(lua, "forceRun") is True and list(g._core.toggles) == [True]
    n = len(p.sets)
    ok, _, old = lua.eval("PZA.act.start({seq=2, goal='goto', args='13 20 forcerun'}, ...)", p)
    assert ok is True and old["detail"] == "superseded"
    assert p.sets[n:] == OFF and motor(lua, "forceRun") is False and list(g._core.toggles) == [True, False]
    tick(lua, p)
    assert motor(lua, "forceRun") is True
    n = len(p.sets)
    lua.eval("PZA.act.start({seq=3, goal='stop', args=''}, ...)", p)
    assert p.sets[n:] == OFF and motor(lua, "forceRun") is False
    tick(lua, p)
    assert p.sets[n:] == OFF + OFF and lua.eval("PZA.act.status()")["state"] == "done"


def test_a_flee_sub_walk_takes_no_motor_off_at_its_end(lua):
    load(lua)
    g = lua.globals(); g._cell = make_cell(squares=open_squares(10, 20))
    pos = {"x": 10.0}
    p = make_player(); p.getX = lambda s: pos["x"]
    lua.eval("PZA.act.start({seq=1, goal='flee', args='18 20'})")
    tick(lua, p)
    pos["x"] = 18.2
    assert tick(lua, p)["detail"] == "at"
    assert not any(n in ("setForceRun", "setAutoWalk") for n, _ in p.sets)


# autowalk ----------------------------------------------------------------------------------------------------------

def autowalk(lua, args, p=None, seq=1):
    g = lua.globals()
    pos = {"x": 10.0}
    if p is None:
        p = make_player()
    p.getX = lambda s: pos["x"]
    ok, reason, _ = lua.eval("PZA.act.start({seq=%d, goal='autowalk', args='%s'}, ...)" % (seq, args), p)
    assert ok is True, reason
    return g, p, pos


def test_autowalk_sets_auto_walk_and_its_direction_once_and_is_done_at_its_deadline(lua):
    load(lua)
    g, p, pos = autowalk(lua, "1.95 0 2")
    g._queue.queue.append("old walk")
    st, made = tick_sets(lua, p)
    assert st["state"] == "running" and g._queue.cleared == 1 and g._queue.queue == []
    assert [m[0] for m in made] == ["setAutoWalk", "setAutoWalkDirection"] and made[0][1] is True
    v = made[1][1]
    assert v._cls == "Vector2" and (v.x, v.y) == (1.95, 0)
    g._clock["ms"] += 1999
    pos["x"] = 12.0
    st, made = tick_sets(lua, p)
    assert st["state"] == "running" and made == []
    g._clock["ms"] += 1
    pos["x"] = 13.0
    st, made = tick_sets(lua, p)
    assert st["state"] == "done" and st["detail"].startswith("d=") and float(st["detail"][2:]) == 3.0
    assert made == OFF


def test_autowalk_once_asks_set_force_run_exactly_once(lua):
    load(lua)
    g, p, pos = autowalk(lua, "2 0 2 once")
    tick(lua, p, 5)
    g._clock["ms"] += 2000
    tick(lua, p)
    assert p.sets.count(("setForceRun", True)) == 1 and lua.eval("PZA.motor.forceRun") is False
    assert lua.eval("PZA.act.status()")["state"] == "done"


def test_autowalk_forcerun_sets_the_motor_flag_until_its_end(lua):
    load(lua)
    g, p, pos = autowalk(lua, "1 0 2 forcerun")
    tick(lua, p, 3)
    assert motor(lua, "forceRun") is True and ("setForceRun", True) not in p.sets
    g._clock["ms"] += 2000
    assert tick(lua, p)["state"] == "done" and motor(lua, "forceRun") is False


def test_autowalk_bad_args(lua):
    load(lua)
    for args in ("", "1", "1 0", "1 0 0", "1 0 -2", "x 0 2", "1 0 2 sprint", "1 0 2 setrun"):
        assert lua.eval("PZA.act.start({seq=1, goal='autowalk', args='%s'})" % args) == (False, "bad args"), args


def test_autowalk_without_vector2_fails_not_loaded(lua):
    load(lua)
    count_failed_pcalls(lua)
    for v in (None, J()):
        lua.globals().Vector2 = v
        g, p, pos = autowalk(lua, "1 0 2")
        st, made = tick_sets(lua, p)
        assert st["state"] == "failed" and st["detail"] == "not loaded" and ("setAutoWalk", True) not in made
        assert g.pcallFails == 0


def test_autowalk_fails_dead_when_health_reads_zero(lua):
    load(lua)
    hp = {"v": 100.0}
    g, p, pos = autowalk(lua, "1 0 5", p=health_player(hp))
    tick(lua, p)
    hp["v"] = 0.0
    st, made = tick_sets(lua, p)
    assert st["state"] == "failed" and st["detail"] == "dead" and made == OFF


# drop --------------------------------------------------------------------------------------------------------------

def drop(lua, held, args, seq=1):
    p = inv_player(held)
    ok, reason, _ = lua.eval("PZA.act.start({seq=%d, goal='drop', args='%s'}, ...)" % (seq, args), p)
    assert ok is True, reason
    return lua.globals(), p


def test_drop_queues_one_floor_drop_per_matching_item_up_to_n_and_reports_moved(lua):
    load(lua)
    planks = [item("Base.Plank") for _ in range(3)]
    axe = item("Base.Axe", "HandWeapon")
    held = [axe, planks[0], planks[1], planks[2]]
    g, p = drop(lua, held, "Base.Plank 2")
    st = tick(lua, p)
    adds = g._queue.adds
    assert st["state"] == "running" and [a.Type for a in adds] == ["ISDropWorldItemAction"] * 2
    assert adds[0].item is planks[0] and adds[1].item is planks[1] and adds[0].character is p
    assert all(tuple(a.args) == ("sq", 0, 0, 0, 0, False) for a in adds)
    held.remove(planks[0])
    assert tick(lua, p)["state"] == "running"
    held.remove(planks[1])
    st = tick(lua, p)
    assert st["state"] == "done" and st["detail"] == "moved=2"


def test_drop_none_held_and_bad_args(lua):
    load(lua)
    g, p = drop(lua, [item("Base.Axe")], "Base.Plank 1")
    assert tick(lua, p)["detail"] == "none held" and g._queue.adds == []
    for args in ("", "Base.Plank", "Base.Plank x", "Base.Plank 0"):
        assert lua.eval("PZA.act.start({seq=2, goal='drop', args='%s'})" % args) == (False, "bad args"), args


def test_drop_without_the_vanilla_class_or_a_square_fails_not_loaded(lua):
    load(lua)
    count_failed_pcalls(lua)
    g = lua.globals()
    for cls in (None, J()):
        g.ISDropWorldItemAction = cls
        g2, p = drop(lua, [item("Base.Plank")], "Base.Plank 1")
        assert tick(lua, p)["detail"] == "not loaded" and g._queue.adds == []
    g.ISDropWorldItemAction = J(new=lambda cls, *a: J(Type="ISDropWorldItemAction"))
    g2, p = drop(lua, [item("Base.Plank")], "Base.Plank 1")
    del p.getCurrentSquare
    assert tick(lua, p)["detail"] == "not loaded" and g._queue.adds == []
    assert g.pcallFails == 0


def test_drop_interrupted_at_the_budget_with_none_gone_else_moved(lua):
    load(lua)
    planks = [item("Base.Plank") for _ in range(2)]
    held = list(planks)
    g, p = drop(lua, held, "Base.Plank 5")
    tick(lua, p)
    assert len(g._queue.adds) == 2
    g._clock["ms"] += 10000 + 3000 * 2 + 1
    st = tick(lua, p)
    assert st["state"] == "failed" and st["detail"] == "interrupted"
    held2 = [item("Base.Plank") for _ in range(2)]
    g, p = drop(lua, held2, "Base.Plank 2", seq=2)
    tick(lua, p)
    held2.pop()
    g._clock["ms"] += 10000 + 3000 * 2 + 1
    st = tick(lua, p)
    assert st["state"] == "done" and st["detail"] == "moved=1"


# ---- Plan 22 probe fix 1: the autowalk once arm asserts on its second tick ------------------------------------------

def test_autowalk_once_asks_set_force_run_on_its_second_tick_only(lua):
    load(lua)
    g, p, pos = autowalk(lua, "2 0 5 once")
    st, made = tick_sets(lua, p)
    assert st["state"] == "running" and not any(n == "setForceRun" for n, _ in made)
    st, made = tick_sets(lua, p)
    assert made == [("setForceRun", True)]
    for _ in range(4):
        st, made = tick_sets(lua, p)
        assert st["state"] == "running" and made == []
