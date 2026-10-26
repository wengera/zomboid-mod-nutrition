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


# ---- Stage A pass 2 and 3: the chunked scan, emitted in parts ----------------------------------------------------------

def clocked_cell(lua, cx, cy, r):
    """Every square of the (2r+1)^2 grid around (cx, cy); each getGridSquare call costs 1 ms of the fixture clock
    and is recorded."""
    clock = lua.globals()._clock
    squares = {(x, y, 0): J(getX=lambda s, x=x: x, getY=lambda s, y=y: y, getZ=lambda s: 0)
               for x in range(cx - r, cx + r + 1) for y in range(cy - r, cy + r + 1)}
    calls = []

    def grid(s, x, y, z):
        clock["ms"] += 1
        calls.append((int(x), int(y)))
        return squares.get((int(x), int(y), int(z)))
    lua.globals()._cell = J(getGridSquare=grid)
    return calls


def step_parts(lua, p, limit=40):
    """scanStep until a part carries done (or limit steps): the parts in order, each a dict with its squares a list."""
    parts = []
    while len(parts) < limit:
        part = lua.eval("PZA.sense.scanStep(...)", p)
        if part is None:
            break
        d = {k: part[k] for k in ("scanId", "r", "part", "parts", "stepMs", "done", "scanMs", "scanTicks",
                                  "scanStepMaxMs", "hour")}
        d["squares"] = list((part["squares"] or {}).values())
        d["missing"] = list((part["missing"] or {}).values())
        d["scanMsPerTick"] = list(part["scanMsPerTick"].values()) if part["scanMsPerTick"] is not None else None
        parts.append(d)
        if d["done"]:
            break
    return parts


def test_scan_job_r15_yields_17_contiguous_parts_of_its_walk(lua):
    load(lua)
    assert lua.eval("PZA.sense.SCAN_SQUARES_PER_TICK") == 60
    calls = clocked_cell(lua, 10, 20, 15)
    pos = {"x": 10.0}
    p = make_player(); p.getX = lambda s: pos["x"]
    lua.eval("PZA.sense.scanStart(...)", p, 15)
    parts, per = [], []
    while len(parts) < 40:
        n0 = len(calls)
        got = step_parts(lua, p, limit=1)
        if not got:
            break
        parts += got
        per.append(len(calls) - n0)
        pos["x"] = 30.0                                          # the grid is the one at start
        if got[0]["done"]:
            break
    assert [q["part"] for q in parts] == list(range(1, 18)) and {q["parts"] for q in parts} == {17}
    assert per == [60] * 16 + [1] and [len(q["squares"]) for q in parts] == [60] * 16 + [1]
    assert [q["stepMs"] for q in parts] == [60] * 16 + [1] and {q["scanId"] for q in parts} == {parts[0]["scanId"]}
    assert [q["done"] for q in parts] == [None] * 16 + [True]
    last = parts[-1]
    assert last["scanTicks"] == 17 and last["scanMs"] == 961 and last["scanStepMaxMs"] == 60
    assert last["scanMsPerTick"] == [60] * 16 + [1] and all(q["scanMs"] is None for q in parts[:-1])
    assert min(c[0] for c in calls) == -5 and max(c[0] for c in calls) == 25
    assert lua.eval("PZA.sense.scanStep(...)", p) is None        # no job: nothing


def test_the_parts_union_is_the_synchronous_scan(lua):
    load(lua)
    clocked_cell(lua, 10, 20, 15)
    p = make_player()
    lua.eval("PZA.sense.scanStart(...)", p, 15)
    parts = step_parts(lua, p)
    whole = lua.eval("PZA.sense.scan(...)", p, 15)
    key = lambda q: (q["x"], q["y"], q["z"])
    union = [key(q) for part in parts for q in part["squares"]]
    assert len(union) == len(set(union)) == 961
    assert sorted(union) == sorted(key(q) for q in whole["squares"].values())
    assert whole["r"] == 15 and whole["scanTicks"] == 17 and whole["scanMs"] == 961 and whole["scanStepMaxMs"] == 60
    assert [whole["scanMsPerTick"][i] for i in range(1, 18)] == [60] * 16 + [1]
    for k in ("hour", "missing"):
        assert whole[k] is not None


def test_each_scan_start_takes_a_new_id_and_replaces_the_running_job(lua):
    load(lua)
    clocked_cell(lua, 10, 20, 15)
    p = make_player()
    lua.eval("PZA.sense.scanStart(...)", p, 15)
    first = step_parts(lua, p, limit=3)
    assert [q["part"] for q in first] == [1, 2, 3] and not any(q["done"] for q in first)
    lua.eval("PZA.sense.scanStart(...)", p, 2)
    second = step_parts(lua, p)
    assert second[0]["scanId"] == first[0]["scanId"] + 1
    assert [(q["part"], q["parts"], q["r"], len(q["squares"]), q["done"]) for q in second] == [(1, 1, 2, 25, True)]
    assert lua.eval("PZA.sense.scanStep(...)", p) is None        # the replaced job's parts stop
    s = lua.eval("PZA.sense.scan(...)", p, 15)                    # the sync helper takes no id and leaves none running
    assert len(s["squares"]) == 961 and lua.eval("PZA.sense.job") is None
    lua.eval("PZA.sense.scanStart(...)", p, 0)
    assert step_parts(lua, p)[0]["scanId"] == first[0]["scanId"] + 2


def test_a_parts_missing_lists_what_its_own_squares_lacked_and_the_whole_unions_them(lua):
    load(lua)
    plain = lambda x, y: J(getX=lambda s: x, getY=lambda s: y, getZ=lambda s: 0, isSolid=lambda s: False,
                           isSolidTrans=lambda s: False, getLightLevel=lambda s, i: 0.5,
                           getObjects=lambda s: J(size=lambda s2: 0), getWorldObjects=lambda s: J(size=lambda s2: 0))
    bare = lambda x, y: J(getX=lambda s: x, getY=lambda s: y, getZ=lambda s: 0)
    squares = {(x, y, 0): (bare(x, y) if (x, y) == (10, 20) else plain(x, y)) for x in range(9, 12) for y in range(19, 22)}
    lua.globals()._cell = J(getGridSquare=lambda s, x, y, z: squares.get((int(x), int(y), int(z))))
    lua.execute("PZA.sense.SCAN_SQUARES_PER_TICK = 4")             # 9 squares: parts of 4, 4, 1; (10, 20) is the 5th
    p = make_player()
    lua.eval("PZA.sense.scanStart(...)", p, 1)
    parts = step_parts(lua, p)
    assert [q["parts"] for q in parts] == [3, 3, 3] and [len(q["squares"]) for q in parts] == [4, 4, 1]
    assert parts[0]["missing"] == [] and "isSolid" in parts[1]["missing"] and parts[2]["missing"] == []
    whole = lua.eval("PZA.sense.scan(...)", p, 1)
    assert sorted(whole["missing"].values()) == sorted(parts[1]["missing"])


def test_scan_records_each_steps_ms_and_their_maximum(lua):
    load(lua)
    clocked_cell(lua, 10, 20, 15)                                # 1 ms per square
    s = lua.eval("PZA.sense.scan(...)", make_player(), 15)
    steps = [s["scanMsPerTick"][i] for i in range(1, s["scanTicks"] + 1)]
    assert len(s["scanMsPerTick"]) == s["scanTicks"] == 17
    assert steps == [60] * 16 + [1] and s["scanStepMaxMs"] == 60 and sum(steps) == s["scanMs"]
    s = lua.eval("PZA.sense.scan(...)", make_player(), 0)        # one square, one step
    assert s["scanTicks"] == 1 and s["scanStepMaxMs"] == 1 and s["scanMsPerTick"][1] == 1
