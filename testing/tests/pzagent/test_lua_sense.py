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
    objs = [J(getContainer=lambda s: cont), J(_cls="IsoDoor", getContainer=lambda s: None, IsOpen=door.IsOpen, isLocked=door.isLocked, isBarricaded=door.isBarricaded)]
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


def _sq_with(objs):
    return J(getX=lambda s: 11, getY=lambda s: 20, getZ=lambda s: 0, isSolid=lambda s: False, isSolidTrans=lambda s: False,
             getObjects=lambda s: J(size=lambda s2: len(objs), get=lambda s2, i: objs[i]),
             getWorldObjects=lambda s: J(size=lambda s2: 0, get=lambda s2, i: None))


def _scan_one(lua, objs):
    lua.globals()._cell = make_cell(squares={(11, 20, 0): _sq_with(objs)})
    s = lua.eval("PZA.sense.scan(...)", make_player(), 1)
    return [q for q in s["squares"].values() if q["x"] == 11][0], s


def test_window_is_not_a_door(lua):
    load(lua)
    win = J(_cls="IsoWindow", IsOpen=lambda s: True, isLocked=lambda s: False, isBarricaded=lambda s: True)
    one, _ = _scan_one(lua, [win])
    assert one["door"] is None and one["window"]["open"] is True and one["window"]["barricaded"] is True


def test_thumpable_wall_is_neither_and_thumpable_door_is_a_door(lua):
    load(lua)
    wall = J(_cls="IsoThumpable", isDoor=lambda s: False, isWindow=lambda s: False,
             IsOpen=lambda s: False, isLocked=lambda s: False, isBarricaded=lambda s: False)
    tdoor = J(_cls="IsoThumpable", isDoor=lambda s: True, isWindow=lambda s: False,
              IsOpen=lambda s: False, isLocked=lambda s: True, isBarricaded=lambda s: False)
    one, _ = _scan_one(lua, [wall])
    assert one["door"] is None and one["window"] is None
    one, _ = _scan_one(lua, [tdoor])
    assert one["door"]["locked"] is True and one["window"] is None


def test_two_containers_on_one_object_and_per_scan_missing(lua):
    load(lua)
    def box(t, ft):
        return J(getType=lambda s: t, getItems=lambda s: J(size=lambda s2: 1, get=lambda s2, i: J(getFullType=lambda s3: ft)))
    boxes = [box("fridge", "Base.Milk"), box("freezer", "Base.Ice")]
    both = J(getContainerCount=lambda s: 2, getContainerByIndex=lambda s, i: boxes[i])
    lua.execute("PZA.sense.missing = {'stale'}")
    one, s = _scan_one(lua, [both])
    assert [c["type"] for c in one["containers"].values()] == ["fridge", "freezer"]
    assert "stale" not in list(s["missing"].values())


def test_moodles_upper_case_and_missing_constant_reported(lua):
    load(lua)
    f = lua.eval("PZA.sense.frame(...)", make_player(moodle_levels={"HUNGRY": 2}))
    assert f["moodles"]["HUNGRY"] == 2
    lua.execute("MoodleType = {HUNGRY = 'HUNGRY'}")
    f = lua.eval("PZA.sense.frame(...)", make_player(moodle_levels={"HUNGRY": 2}))
    assert f["moodles"]["HUNGRY"] == 2 and f["moodles"]["TIRED"] is None
    assert "MoodleType.TIRED" in list(lua.eval("PZA.sense.missing").values())


def test_stats_via_characterstat_and_missing_constant(lua):
    load(lua)
    f = lua.eval("PZA.sense.frame(...)", make_player())
    assert f["sickness"] == 0.0 and f["wetness"] == 5.0 and f["temperature"] == 37.0 and f["thirst"] == 0.2
    lua.execute("CharacterStat = {HUNGER = 'HUNGER'}")
    f = lua.eval("PZA.sense.frame(...)", make_player())
    assert f["hunger"] == 0.3 and f["thirst"] is None
    assert "CharacterStat.THIRST" in list(lua.eval("PZA.sense.missing").values())


def test_action_from_queue_and_zombie_id_fallback(lua):
    load(lua)
    lua.execute("ISTimedActionQueue = {getTimedActionQueue = function(p) return {queue = {{Type = 'ISEatFoodAction'}, {Type = 'X'}}} end}")
    lua.globals()._cell = make_cell(zombies=[J(getX=lambda s: 11.0, getY=lambda s: 20.0, isDead=lambda s: False)])
    f = lua.eval("PZA.sense.frame(...)", make_player())
    assert f["action"]["class"] == "ISEatFoodAction" and f["action"]["n"] == 2
    assert f["zombies"][1]["id"] == "i0"
