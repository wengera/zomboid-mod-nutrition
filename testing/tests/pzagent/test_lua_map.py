"""PZAgent_Map.lua (Plan 22 Task 6): the scan job moved out of Sense, each part queued through the Link as a positional
`map` line in mode "full" with the schema's square records, and the dirty-set watch: WATCH_PER_TICK squares a tick of
the (2 WATCH_R + 1)^2 ring round the player, each encoded and queued as a one-square `delta` line when its encoding
differs from the last one emitted (MP.seen), at most once every DELTA_MIN_TICKS ticks a square."""
import json
import os
import re

from agent.base import pza1
from .conftest import ROOT, lua_file, make_player, J

SCHEMA = os.path.join(ROOT, "testing", "agent", "base", "schema", "pza1.json")
LIVE = "pzagent/admin/state.log"


def load(lua, init=False):
    for f in ("client/PZAgent_Link.lua", "client/PZAgent_Motor.lua", "client/PZAgent_Skills.lua",
              "client/PZAgent_Sense.lua", "client/PZAgent_Map.lua"):
        lua.execute(open(lua_file(f), encoding="utf-8").read())
    lua.globals().PZA.tick = 0
    if init:
        lua.execute("PZA.link.init('admin')")


def map_lines(fs):
    out = []
    for l in fs.files.get(LIVE, "").split("\n"):
        if l.strip().startswith('["map"'):
            out.append(pza1.decode(json.loads(l)))
    return out


def backlog(lua):
    return [lua.eval("PZA.link.backlog")[i] for i in range(1, lua.eval("#PZA.link.backlog") + 1)]


# ---- the scan job (moved from test_lua_sense.py, re-targeted at PZA.map) -----------------------------------------------

def test_scan_reports_door_container_and_room(lua):
    load(lua)
    door = J(IsOpen=lambda s: False, isLocked=lambda s: True, isBarricaded=lambda s: False)
    cont = J(getType=lambda s: "fridge", getItems=lambda s: J(size=lambda s2: 1, get=lambda s2, i: J(getFullType=lambda s3: "Base.Milk")))
    objs = [J(getContainer=lambda s: cont), J(_cls="IsoDoor", getContainer=lambda s: None, IsOpen=door.IsOpen, isLocked=door.isLocked, isBarricaded=door.isBarricaded)]
    sq = J(getX=lambda s: 11, getY=lambda s: 20, getZ=lambda s: 0, isSolid=lambda s: False, isSolidTrans=lambda s: False,
           getRoom=lambda s: J(getName=lambda s2: "kitchen"), getBuilding=lambda s: J(getID=lambda s2: 77),
           getLightLevel=lambda s, i: 0.6, getObjects=lambda s: J(size=lambda s2: 2, get=lambda s2, i: objs[i]),
           getWorldObjects=lambda s: J(size=lambda s2: 0, get=lambda s2, i: None))
    lua.globals()._cell = make_cell_of({(11, 20, 0): sq})
    s = lua.eval("PZA.map.scan(...)", make_player(), 1)
    one = [q for q in s["squares"].values() if q["x"] == 11][0]
    assert one["room"] == "kitchen" and one["door"]["locked"] is True
    assert one["containers"][1]["type"] == "fridge" and one["containers"][1]["items"][1] == "Base.Milk"
    assert s["r"] == 1 and len(s["squares"]) == 1


def make_cell_of(squares):
    return J(getGridSquare=lambda s, x, y, z: squares.get((int(x), int(y), int(z))))


def _sq_with(objs):
    return J(getX=lambda s: 11, getY=lambda s: 20, getZ=lambda s: 0, isSolid=lambda s: False, isSolidTrans=lambda s: False,
             getObjects=lambda s: J(size=lambda s2: len(objs), get=lambda s2, i: objs[i]),
             getWorldObjects=lambda s: J(size=lambda s2: 0, get=lambda s2, i: None))


def _scan_one(lua, objs):
    lua.globals()._cell = make_cell_of({(11, 20, 0): _sq_with(objs)})
    s = lua.eval("PZA.map.scan(...)", make_player(), 1)
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
    lua.execute("PZA.map.missing = {'stale'}")
    one, s = _scan_one(lua, [both])
    assert [c["type"] for c in one["containers"].values()] == ["fridge", "freezer"]
    assert "stale" not in list(s["missing"].values())


# ---- the chunked scan, queued in parts ---------------------------------------------------------------------------

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


def step_parts(lua, p, limit=80):
    """scanStep until a part carries done (or limit steps): the parts in order, each a dict with its squares a list."""
    parts = []
    while len(parts) < limit:
        part = lua.eval("PZA.map.scanStep(...)", p)
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


def test_scan_job_r15_yields_49_contiguous_parts_of_its_walk(lua):
    load(lua)
    assert lua.eval("PZA.map.SCAN_SQUARES_PER_TICK") == 20
    calls = clocked_cell(lua, 10, 20, 15)
    pos = {"x": 10.0}
    p = make_player(); p.getX = lambda s: pos["x"]
    lua.eval("PZA.map.scanStart(...)", p, 15)
    parts, per = [], []
    while len(parts) < 80:
        n0 = len(calls)
        got = step_parts(lua, p, limit=1)
        if not got:
            break
        parts += got
        per.append(len(calls) - n0)
        pos["x"] = 30.0                                          # the grid is the one at start
        if got[0]["done"]:
            break
    # ceil(961 / 20) = 49 parts: 48 of 20 squares and the last of 1
    assert [q["part"] for q in parts] == list(range(1, 50)) and {q["parts"] for q in parts} == {49}
    assert per == [20] * 48 + [1] and [len(q["squares"]) for q in parts] == [20] * 48 + [1]
    assert [q["stepMs"] for q in parts] == [20] * 48 + [1] and {q["scanId"] for q in parts} == {parts[0]["scanId"]}
    assert [q["done"] for q in parts] == [None] * 48 + [True]
    last = parts[-1]
    assert last["scanTicks"] == 49 and last["scanMs"] == 961 and last["scanStepMaxMs"] == 20
    assert last["scanMsPerTick"] == [20] * 48 + [1] and all(q["scanMs"] is None for q in parts[:-1])
    assert min(c[0] for c in calls) == -5 and max(c[0] for c in calls) == 25
    assert lua.eval("PZA.map.scanStep(...)", p) is None        # no job: nothing


def test_the_parts_union_is_the_synchronous_scan(lua):
    load(lua)
    clocked_cell(lua, 10, 20, 15)
    p = make_player()
    lua.eval("PZA.map.scanStart(...)", p, 15)
    parts = step_parts(lua, p)
    whole = lua.eval("PZA.map.scan(...)", p, 15)
    key = lambda q: (q["x"], q["y"], q["z"])
    union = [key(q) for part in parts for q in part["squares"]]
    assert len(union) == len(set(union)) == 961
    assert sorted(union) == sorted(key(q) for q in whole["squares"].values())
    assert len(parts) == 49 and [q["part"] for q in parts] == list(range(1, 50))
    assert whole["r"] == 15 and whole["scanTicks"] == 49 and whole["scanMs"] == 961 and whole["scanStepMaxMs"] == 20
    assert [whole["scanMsPerTick"][i] for i in range(1, 50)] == [20] * 48 + [1]
    for k in ("hour", "missing"):
        assert whole[k] is not None


def test_each_scan_start_takes_a_new_id_and_replaces_the_running_job(lua):
    load(lua)
    clocked_cell(lua, 10, 20, 15)
    p = make_player()
    lua.eval("PZA.map.scanStart(...)", p, 15)
    first = step_parts(lua, p, limit=3)
    assert [q["part"] for q in first] == [1, 2, 3] and not any(q["done"] for q in first)
    lua.eval("PZA.map.scanStart(...)", p, 2)
    second = step_parts(lua, p)
    assert second[0]["scanId"] == first[0]["scanId"] + 1
    assert [(q["part"], q["parts"], q["r"], len(q["squares"]), q["done"]) for q in second] == [(1, 2, 2, 20, None),
                                                                                                  (2, 2, 2, 5, True)]
    assert lua.eval("PZA.map.scanStep(...)", p) is None        # the replaced job's parts stop
    s = lua.eval("PZA.map.scan(...)", p, 15)                    # the sync helper takes no id and leaves none running
    assert len(s["squares"]) == 961 and lua.eval("PZA.map.job") is None
    lua.eval("PZA.map.scanStart(...)", p, 0)
    assert step_parts(lua, p)[0]["scanId"] == first[0]["scanId"] + 2


def test_a_parts_missing_lists_what_its_own_squares_lacked_and_the_whole_unions_them(lua):
    load(lua)
    plain = lambda x, y: J(getX=lambda s: x, getY=lambda s: y, getZ=lambda s: 0, isSolid=lambda s: False,
                           isSolidTrans=lambda s: False, getLightLevel=lambda s, i: 0.5,
                           getObjects=lambda s: J(size=lambda s2: 0), getWorldObjects=lambda s: J(size=lambda s2: 0))
    bare = lambda x, y: J(getX=lambda s: x, getY=lambda s: y, getZ=lambda s: 0)
    squares = {(x, y, 0): (bare(x, y) if (x, y) == (10, 20) else plain(x, y)) for x in range(9, 12) for y in range(19, 22)}
    lua.globals()._cell = J(getGridSquare=lambda s, x, y, z: squares.get((int(x), int(y), int(z))))
    lua.execute("PZA.map.SCAN_SQUARES_PER_TICK = 4")             # 9 squares: parts of 4, 4, 1; (10, 20) is the 5th
    p = make_player()
    lua.eval("PZA.map.scanStart(...)", p, 1)
    parts = step_parts(lua, p)
    assert [q["parts"] for q in parts] == [3, 3, 3] and [len(q["squares"]) for q in parts] == [4, 4, 1]
    assert parts[0]["missing"] == [] and "isSolid" in parts[1]["missing"] and parts[2]["missing"] == []
    whole = lua.eval("PZA.map.scan(...)", p, 1)
    assert sorted(whole["missing"].values()) == sorted(parts[1]["missing"])


def test_scan_records_each_steps_ms_and_their_maximum(lua):
    load(lua)
    clocked_cell(lua, 10, 20, 15)                                # 1 ms per square
    s = lua.eval("PZA.map.scan(...)", make_player(), 15)
    steps = [s["scanMsPerTick"][i] for i in range(1, s["scanTicks"] + 1)]
    assert len(s["scanMsPerTick"]) == s["scanTicks"] == 49
    assert steps == [20] * 48 + [1] and s["scanStepMaxMs"] == 20 and sum(steps) == s["scanMs"]
    s = lua.eval("PZA.map.scan(...)", make_player(), 0)        # one square, one step
    assert s["scanTicks"] == 1 and s["scanStepMaxMs"] == 1 and s["scanMsPerTick"][1] == 1


# ---- the parts as map lines --------------------------------------------------------------------------------------

def test_each_part_is_queued_as_a_positional_full_map_line(lua, fs):
    load(lua, init=True)
    clocked_cell(lua, 10, 20, 15)
    p = make_player()
    lua.eval("PZA.map.scanStart(...)", p, 15)
    parts = step_parts(lua, p)
    assert len(parts) == 49
    queued = backlog(lua)
    assert len(queued) == 49                                     # one map body a part, unstamped (ruling S-11)
    assert all(b["seq"] is None and b["mode"] == "full" for b in queued)
    for _ in range(60):
        lua.execute("PZA.link.flush()")
    lines = map_lines(fs)
    assert len(lines) == 49 and {m["mode"] for m in lines} == {"full"}
    assert [m["part"] for m in lines] == list(range(1, 50)) and {m["parts"] for m in lines} == {49}
    assert {m["scanId"] for m in lines} == {parts[0]["scanId"]} and sum(len(m["squares"]) for m in lines) == 961
    keys = set(json.load(open(SCHEMA, encoding="utf-8"))["$defs"]["square"]["x-order"])
    assert all(set(q) == keys for m in lines for q in m["squares"])
    assert [m["seq"] for m in lines] == list(range(1, 50))


def test_a_scan_part_line_decodes_to_the_squares_it_walked(lua, fs):
    load(lua, init=True)
    lua.globals()._cell = make_cell_of({(11, 20, 0): full_square(11, 20, door=True)})
    p = make_player()
    lua.eval("PZA.map.scanStart(...)", p, 1)
    step_parts(lua, p)
    lua.execute("PZA.link.flush()")
    (m,) = map_lines(fs)
    assert (m["mode"], m["part"], m["parts"], m["missing"]) == ("full", 1, 1, [])
    assert m["squares"] == [{"x": 11, "y": 20, "z": 0, "solid": False, "solidTrans": False, "light": 0.5,
                             "room": "kitchen", "building": 7, "door": {"open": False, "locked": False,
                                                                        "barricaded": False},
                             "window": None, "containers": [], "floor": []}]
    assert lua.eval("PZA.map.seen['11,20,0']") == lua.eval("PZA.enc.square(PZA.map.square(...))", full_square(11, 20, door=True), lua.table())


def test_map_square_has_exactly_the_schemas_square_keys(lua):
    load(lua)
    t = lua.eval("PZA.map.square(...)", full_square(3, 4, door=True, window=True, box=True, floor=True), lua.table())
    keys = json.load(open(SCHEMA, encoding="utf-8"))["$defs"]["square"]["x-order"]
    assert sorted(t.keys()) == sorted(keys)
    assert sorted(lua.eval("PZA.schema.records.square").values()) == sorted(keys)
    assert sorted(t["door"].keys()) == ["barricaded", "locked", "open"]
    assert sorted(t["containers"][1].keys()) == ["items", "n", "type"]
    assert list(t["containers"][1]["items"].values()) == ["Base.Milk"] and list(t["floor"].values()) == ["Base.Plank"]
    assert lua.eval("PZA.map.key(3, 4, 0)") == "3,4,0"


def test_map_reads_every_java_member_through_pza_call():
    src = open(lua_file("client/PZAgent_Map.lua"), encoding="utf-8").read()
    code = "\n".join(re.sub(r'"[^"]*"', '""', l.split("--")[0]) for l in src.splitlines())
    assert re.findall(r"[\w\])]:\w+\s*\(", code) == []


# ---- the watch ---------------------------------------------------------------------------------------------------

def full_square(x, y, door=False, window=False, box=False, floor=False, state=None):
    """A square with every member; with door, an IsoDoor whose IsOpen reads state["open"]."""
    st = state if state is not None else {"open": False}
    objs = []
    if door:
        objs.append(J(_cls="IsoDoor", IsOpen=lambda s: st["open"], isLocked=lambda s: False,
                      isBarricaded=lambda s: False))
    if window:
        objs.append(J(_cls="IsoWindow", IsOpen=lambda s: False, isLocked=lambda s: False, isBarricaded=lambda s: False))
    if box:
        cont = J(getType=lambda s: "fridge",
                 getItems=lambda s: J(size=lambda s2: 1, get=lambda s2, i: J(getFullType=lambda s3: "Base.Milk")))
        objs.append(J(getContainer=lambda s: cont))
    wos = [J(getItem=lambda s: J(getFullType=lambda s2: "Base.Plank"))] if floor else []
    return J(getX=lambda s: x, getY=lambda s: y, getZ=lambda s: 0, isSolid=lambda s: False,
             isSolidTrans=lambda s: False, getLightLevel=lambda s, i: 0.5,
             getRoom=lambda s: J(getName=lambda s2: "kitchen"), getBuilding=lambda s: J(getID=lambda s2: 7),
             getObjects=lambda s: J(size=lambda s2: len(objs), get=lambda s2, i: objs[i]),
             getWorldObjects=lambda s: J(size=lambda s2: len(wos), get=lambda s2, i: wos[i]))


def watch_world(lua, door_at=(12, 21)):
    """Squares over x 0..45, y 10..30 (floor 0), one holding a door whose IsOpen reads st["open"]; every getGridSquare
    call is recorded."""
    st = {"open": False}
    squares = {}
    for x in range(0, 46):
        for y in range(10, 31):
            squares[(x, y, 0)] = J(getX=lambda s, x=x: x, getY=lambda s, y=y: y, getZ=lambda s: 0,
                                   isSolid=lambda s: False, isSolidTrans=lambda s: False,
                                   getLightLevel=lambda s, i: 0.5,
                                   getObjects=lambda s: J(size=lambda s2: 0),
                                   getWorldObjects=lambda s: J(size=lambda s2: 0))
    squares[(door_at[0], door_at[1], 0)] = full_square(door_at[0], door_at[1], door=True, state=st)
    calls = []

    def grid(s, x, y, z):
        calls.append((int(x), int(y)))
        return squares.get((int(x), int(y), int(z)))
    lua.globals()._cell = J(getGridSquare=grid)
    return st, calls


def seed_ring(lua, p):
    """A full scan of the watch's ring (r = WATCH_R), every part stepped and the backlog emptied: MP.seen holds them."""
    lua.eval("PZA.map.scanStart(...)", p, lua.eval("PZA.map.WATCH_R"))
    step_parts(lua, p)
    lua.execute("PZA.link.backlog = {}")


def watch(lua, p, tick):
    lua.globals().PZA.tick = tick
    return lua.eval("PZA.map.watchStep(...)", p)


def test_the_watch_constants(lua):
    load(lua)
    assert (lua.eval("PZA.map.WATCH_R"), lua.eval("PZA.map.WATCH_PER_TICK"), lua.eval("PZA.map.DELTA_MIN_TICKS")) == (6, 8, 30)


def test_a_watch_step_reads_8_squares_and_queues_nothing_while_nothing_changed(lua):
    load(lua)
    st, calls = watch_world(lua)
    p = make_player()
    seed_ring(lua, p)
    for t in range(1, 23):                                      # 169 squares at 8 a tick: one whole cycle and more
        n0 = len(calls)
        watch(lua, p, t)
        assert len(calls) - n0 == 8
    assert backlog(lua) == []
    # the cycle is the ring's (2*6+1)^2 squares by index: the 22 ticks read 176 = 169 + 7 squares
    assert len(set(calls[-176:])) == 169 and set(calls[-176:]) == {(x, y) for x in range(4, 17) for y in range(14, 27)}


def test_a_door_toggled_on_a_seen_square_queues_one_delta_and_seen_updates(lua, fs):
    load(lua, init=True)
    st, calls = watch_world(lua)
    p = make_player()
    seed_ring(lua, p)
    before = lua.eval("PZA.map.seen['12,21,0']")
    assert before is not None
    st["open"] = True
    for t in range(1, 23):
        watch(lua, p, 100 + t)
    queued = backlog(lua)
    assert len(queued) == 1
    d = queued[0]
    assert (d["mode"], d["scanId"], d["part"], d["parts"], len(d["squares"])) == ("delta", 0, 1, 1, 1)
    assert d["squares"][1]["x"] == 12 and d["squares"][1]["door"]["open"] is True
    after = lua.eval("PZA.map.seen['12,21,0']")
    assert after != before and after == lua.eval("PZA.enc.square(...)", d["squares"][1])
    lua.execute("PZA.link.flush()")
    (m,) = map_lines(fs)
    assert m["mode"] == "delta" and m["squares"][0]["door"] == {"open": True, "locked": False, "barricaded": False}


def test_a_square_changed_again_within_30_ticks_is_not_requeued_and_after_30_it_is(lua):
    load(lua)
    st, calls = watch_world(lua)
    p = make_player()
    seed_ring(lua, p)
    st["open"] = True
    tick, first = 0, None
    while first is None:                                         # the first delta lands on the tick the watch reads it
        tick += 1
        watch(lua, p, tick)
        if backlog(lua):
            first = tick
    st["open"] = False
    lua.execute("PZA.link.backlog = {}")
    while tick < first + 29:                                     # re-read 22 ticks later: within 30, held
        tick += 1
        watch(lua, p, tick)
    assert backlog(lua) == []
    assert lua.eval("PZA.map.lastDelta['12,21,0']") == first
    while not backlog(lua) and tick < first + 80:              # the next read at or past 30 ticks queues it
        tick += 1
        watch(lua, p, tick)
    queued = backlog(lua)
    assert len(queued) == 1 and queued[0]["squares"][1]["door"]["open"] is False
    assert tick - first >= 30 and lua.eval("PZA.map.lastDelta['12,21,0']") == tick


def test_a_square_never_seen_is_queued_as_a_delta(lua):
    load(lua)
    watch_world(lua)
    pos = {"x": 10.0}
    p = make_player(); p.getX = lambda s: pos["x"]
    seed_ring(lua, p)
    pos["x"] = 30.0                                             # moved: the ring's first row is (24..31, 14), unseen
    watch(lua, p, 1)
    queued = backlog(lua)
    assert [(b["mode"], b["squares"][1]["x"], b["squares"][1]["y"]) for b in queued] == [
        ("delta", x, 14) for x in range(24, 32)]
    assert all(lua.eval("PZA.map.seen['%d,14,0']" % x) is not None for x in range(24, 32))


def test_a_missing_square_is_skipped_and_the_watch_index_still_advances(lua):
    load(lua)
    lua.globals()._cell = make_cell_of({})                       # no square anywhere: nothing read, nothing queued
    p = make_player()
    assert watch(lua, p, 1) == 0 and backlog(lua) == []
    assert lua.eval("PZA.map.watchIdx") == 8
