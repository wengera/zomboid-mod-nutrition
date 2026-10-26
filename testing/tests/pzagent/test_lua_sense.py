from .conftest import lua_file, make_player, make_zombie, make_cell, J


def load(lua):
    for f in ("client/PZAgent_Link.lua", "client/PZAgent_Sense.lua"):
        lua.execute(open(lua_file(f), encoding="utf-8").read())


def test_frame_fields_and_zombies_in_radius(lua):
    load(lua)
    lua.globals()._cell = make_cell(zombies=[make_zombie(1, 12.0, 20.0), make_zombie(2, 40.0, 40.0), make_zombie(3, 11.0, 20.0, dead=True)])
    f = lua.eval("PZA.sense.frame(...)", make_player())
    assert f["x"] == 10.0 and f["hunger"] == 0.3 and f["health"] == 100.0 and f["dir"] == "N"
    assert [z["id"] for z in f["zombies"].values()] == [1] and abs(f["zombies"][1]["dist"] - 2.0) < 1e-9
    assert f["nZombies"] == 1 and f["items"] == 0


def test_missing_member_reported_not_raised(lua):
    load(lua)
    p = make_player(); del p.getStats
    f = lua.eval("PZA.sense.frame(...)", p)
    assert "hunger" not in f and "getStats" in list(lua.eval("PZA.sense.missing").values())


def test_events_enter_leave_hit_item(lua):
    load(lua)
    g = lua.globals(); g._cell = make_cell(zombies=[make_zombie(1, 12.0, 20.0)])
    prev = lua.eval("PZA.sense.frame(...)", make_player(health=100.0, items=()))
    g._cell = make_cell(zombies=[make_zombie(2, 15.0, 20.0)])
    ev, _cur = lua.eval("PZA.sense.events(...)", make_player(health=98.0, items=("Base.Apple",)), prev)
    kinds = sorted(e["event"] for e in ev.values())
    assert kinds == ["hit", "item_added", "zombie_enter", "zombie_leave"]


def test_scan_reports_door_container_and_room(lua):
    load(lua)
    door = J(IsOpen=lambda s: False, isLocked=lambda s: True, isBarricaded=lambda s: False)
    cont = J(getType=lambda s: "fridge", getItems=lambda s: J(size=lambda s2: 1, get=lambda s2, i: J(getFullType=lambda s3: "Base.Milk")))
    objs = [J(getContainer=lambda s: cont), J(getContainer=lambda s: None, IsOpen=door.IsOpen, isLocked=door.isLocked, isBarricaded=door.isBarricaded)]
    sq = J(getX=lambda s: 11, getY=lambda s: 20, getZ=lambda s: 0, isSolid=lambda s: False, isSolidTrans=lambda s: False,
           getRoom=lambda s: J(getName=lambda s2: "kitchen"), getBuilding=lambda s: J(getID=lambda s2: 77),
           getLightLevel=lambda s, i: 0.6, getObjects=lambda s: J(size=lambda s2: 2, get=lambda s2, i: objs[i]),
           getWorldObjects=lambda s: J(size=lambda s2: 0, get=lambda s2, i: None))
    lua.globals()._cell = make_cell(squares={(11, 20, 0): sq})
    s = lua.eval("PZA.sense.scan(...)", make_player(), 1)
    one = [q for q in s["squares"].values() if q["x"] == 11][0]
    assert one["room"] == "kitchen" and one["door"]["locked"] is True
    assert one["containers"][1]["type"] == "fridge" and one["containers"][1]["items"][1] == "Base.Milk"
    assert s["r"] == 1 and len(s["squares"]) == 1
