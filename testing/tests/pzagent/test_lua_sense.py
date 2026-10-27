"""PZAgent_Sense.lua (Plan 22 Task 5): the frame as the PZA/1 schema's groups (a measured pace, the run latch read from
the Motor's post-assert fields, load, body parts, weapon reach), the typed events, the inventory's first sight and the
zombie lookups; the scan job's tests below the frame's stay as they were until Task 6 moves the job to the map."""
import json
import os
import re

from .conftest import ROOT, lua_file, make_player, make_weapon, make_zombie, make_cell, J

SCHEMA = os.path.join(ROOT, "testing", "agent", "base", "schema", "pza1.json")
ENVELOPE = ("kind", "seq", "tick", "wallMs")
GROUPS = ("me", "stats", "body", "load", "weapon", "action", "act", "cost")


def load(lua):
    for f in ("client/PZAgent_Link.lua", "client/PZAgent_Motor.lua", "client/PZAgent_Skills.lua",
              "client/PZAgent_Sense.lua"):
        lua.execute(open(lua_file(f), encoding="utf-8").read())


def defs():
    with open(SCHEMA, encoding="utf-8") as f:
        return json.load(f)["$defs"]


def frame(lua, p):
    return lua.eval("PZA.sense.frame(...)", p)


def events(lua, p, prev):
    ev, cur = lua.eval("PZA.sense.events(...)", p, prev)
    return [dict(e) for e in ev.values()], cur


def missing(lua):
    return list(lua.eval("PZA.sense.missing").values())


def moving_player(**kw):
    """A player whose position is pos["x"], pos["y"] (p.pos)."""
    pos = {"x": kw.pop("x", 10.0), "y": kw.pop("y", 20.0)}
    p = make_player(**kw)
    p.getX, p.getY = lambda s: pos["x"], lambda s: pos["y"]
    p.pos = pos
    return p


def live_zombie(zid, x, y):
    """A zombie whose isDead reads z.st["dead"]."""
    st = {"dead": False}
    z = make_zombie(zid, x, y)
    z.isDead = lambda s: st["dead"]
    z.st = st
    return z


# ---- the frame's groups -------------------------------------------------------------------------------------------

def test_the_frames_groups_have_exactly_the_schemas_keys(lua):
    load(lua)
    d = defs()
    g = lua.globals()
    w = make_weapon(max_range=1.5, range_mod=1.2, cond=7)
    w.getCurrentAmmoCount = lambda s: 0
    healths = [100.0] * 17
    healths[4] = 50.0
    p = make_player(weapon=w, part_health=healths)
    g._cell = make_cell(zombies=[make_zombie(1, 12.0, 20.0)])
    lua.execute("ISTimedActionQueue = {getTimedActionQueue = function(p) return {queue = {{Type = 'ISEatFoodAction'}}} end}")
    lua.execute("PZA.skills.cur = {aid = 'a1', state = 'accepted'}")
    g._updHandlers[0](p)                                         # the Motor's post-assert reads are filled
    frame(lua, p)
    g._clock["ms"] += 100
    f = frame(lua, p)                                            # the second frame carries a pace
    top = [k for k in d["frame"]["x-order"] if k not in ENVELOPE and k != "cost"]
    assert sorted(f.keys()) == sorted(top)
    for grp in GROUPS:
        if grp == "cost":
            continue
        ref = "act_now" if grp == "act" else grp
        assert sorted(f[grp].keys()) == sorted(d[ref]["x-order"]), grp
    assert sorted(f["body"]["parts"][1].keys()) == sorted(d["part"]["x-order"])
    assert sorted(f["zombies"][1].keys()) == sorted(d["zombie"]["x-order"])
    assert lua.eval("PZA.sense.RATE") == 10 and lua.eval("PZA.sense.ZOMBIE_RADIUS") == 12


def test_the_frames_groups_match_the_generated_schema_table(lua):
    load(lua)
    groups = lua.eval("PZA.schema.groups")
    d = defs()
    for grp in GROUPS:
        ref = "act_now" if grp == "act" else grp
        assert list(groups[grp].values()) == d[ref]["x-order"]


def test_clock_stats_and_body(lua):
    load(lua)
    healths = [100.0] * 17
    healths[3], healths[11] = 62.5, 99.0
    f = frame(lua, make_player(part_health=healths, wounds=(1, 2, 0), health=88.0))
    assert f["gameMin"] == 450 and f["worldAge"] == 31.5
    s = f["stats"]
    assert (s["hunger"], s["thirst"], s["sickness"], s["wetness"], s["temperature"]) == (0.3, 0.2, 0.0, 5.0, 37.0)
    b = f["body"]
    assert (b["health"], b["bleeding"], b["scratched"], b["bitten"]) == (88.0, 1, 2, 0)
    assert [(e["i"], e["h"]) for e in b["parts"].values()] == [(3, 62.5), (11, 99.0)]
    assert lua.eval("PZA.enc.body(...)", b) == "[88,1,2,0,[[3,62.5],[11,99]]]"
    unhurt = frame(lua, make_player())["body"]
    assert lua.eval("PZA.enc.body(...)", unhurt) == "[100,0,0,0,[]]"


def test_me_reads_position_dir_moving_and_auto_walk(lua):
    load(lua)
    p = make_player(x=3.5, y=4.25, z=1)
    p.motor["autoWalk"] = True
    me = frame(lua, p)["me"]
    assert (me["x"], me["y"], me["z"], me["dir"], me["moving"], me["autoWalk"]) == (3.5, 4.25, 1, "N", False, True)


def test_pace_is_nil_on_the_first_frame_and_hypot_over_dt_after(lua):
    load(lua)
    g = lua.globals()
    p = moving_player()
    assert frame(lua, p)["me"]["pace"] is None
    g._clock["ms"] += 2000
    p.pos["x"], p.pos["y"] = 13.0, 24.0                          # 5 tiles in 2 s
    assert abs(frame(lua, p)["me"]["pace"] - 2.5) < 1e-9
    p.pos["x"] = 14.0                                            # no wall time passed: no pace
    assert frame(lua, p)["me"]["pace"] is None
    g._clock["ms"] += 500
    p.pos["x"] = 15.0                                            # 1 tile in 0.5 s from the zero-dt frame's position
    assert abs(frame(lua, p)["me"]["pace"] - 2.0) < 1e-9


def test_the_latch_is_the_motors_post_frame_read_never_the_players_flag(lua):
    load(lua)
    p = make_player()
    p.motor["forceRun"], p.motor["forceSprint"] = True, True     # isForceRun and isForceSprint answer true now
    p.IsRunning, p.isSprinting = lambda s: True, lambda s: True
    lua.execute("PZA.motor.updForceRun = false; PZA.motor.updForceSprint = false;"
                " PZA.motor.updRunning = false; PZA.motor.updSprinting = false")
    me = frame(lua, p)["me"]
    assert (me["forceRun"], me["forceSprint"], me["running"], me["sprinting"]) == (False, False, False, False)
    lua.execute("PZA.motor.updForceRun = true; PZA.motor.updForceSprint = nil; PZA.motor.updRunning = true")
    me = frame(lua, p)["me"]
    assert me["forceRun"] is True and me["forceSprint"] is None and me["running"] is True


def test_sense_names_none_of_the_players_latch_readers():
    src = open(lua_file("client/PZAgent_Sense.lua"), encoding="utf-8").read()
    for name in ("isForceRun", "isForceSprint", "IsRunning", "isSprinting"):
        assert not re.search(r'"%s"' % name, src), name


def test_load_reads_weight_max_the_heavy_load_level_and_the_item_count(lua):
    load(lua)
    f = frame(lua, make_player(moodle_levels={"HEAVY_LOAD": 2, "HUNGRY": 3}, weight=11.25, max_weight=8,
                               items=("Base.Apple", "Base.Plank")))
    assert dict(f["load"]) == {"weight": 11.25, "max": 8, "level": 2, "n": 2}


def test_weapon_reach_is_max_range_times_range_mod_times_the_margin(lua):
    load(lua)
    w = make_weapon(max_range=1.5, range_mod=1.2, cond=7)
    w.getCurrentAmmoCount = lambda s: 3
    wp = frame(lua, make_player(weapon=w))["weapon"]
    assert wp["type"] == "Base.BaseballBat" and wp["cond"] == 7 and wp["ammo"] == 3
    assert abs(wp["reach"] - 1.5 * 1.2 * 0.9) < 1e-9
    assert frame(lua, make_player())["weapon"] is None


def test_zombies_in_radius_nearest_first_with_health_and_the_dead_left_out(lua):
    load(lua)
    lua.globals()._cell = make_cell(zombies=[make_zombie(1, 15.0, 20.0, health=0.5), make_zombie(2, 40.0, 40.0),
                                             make_zombie(3, 11.0, 20.0, dead=True), make_zombie(4, 12.0, 20.0)])
    zs = [dict(z) for z in frame(lua, make_player())["zombies"].values()]
    assert [z["id"] for z in zs] == [4, 1] and abs(zs[0]["dist"] - 2.0) < 1e-9
    assert zs[1]["health"] == 0.5 and zs[0]["hasTarget"] is False and zs[0]["crawler"] is False
    lua.globals()._cell = make_cell()
    assert len(frame(lua, make_player())["zombies"]) == 0       # none in range: an empty array, never nil


def test_action_from_the_queue(lua):
    load(lua)
    lua.execute("ISTimedActionQueue = {getTimedActionQueue = function(p) return {queue = {{Type = 'ISEatFoodAction'}, {Type = 'X'}}} end}")
    a = frame(lua, make_player())["action"]
    assert a["class"] == "ISEatFoodAction" and a["n"] == 2


def test_act_is_the_runners_status_and_nil_when_idle(lua):
    load(lua)
    assert frame(lua, make_player())["act"] is None
    lua.execute("PZA.skills.cur = {aid = 'w7', state = 'progress'}")
    assert dict(frame(lua, make_player())["act"]) == {"aid": "w7", "state": "progress"}


def test_a_missing_member_leaves_its_field_nil_and_its_name_in_missing(lua):
    load(lua)
    p = make_player(weapon=make_weapon())
    del p.getStats
    del p.getMaxWeight
    lua.globals()._cell = make_cell(zombies=[J(getX=lambda s: 11.0, getY=lambda s: 20.0, isDead=lambda s: False)])
    f = frame(lua, p)
    assert f["stats"]["hunger"] is None and f["load"]["max"] is None and f["load"]["weight"] == 4.5
    assert f["weapon"]["ammo"] is None and f["zombies"][1]["id"] is None
    m = missing(lua)
    for name in ("getStats", "getMaxWeight", "getCurrentAmmoCount", "getOnlineID"):
        assert name in m, name
    lua.execute("CharacterStat = {HUNGER = 'HUNGER'}; MoodleType = {}")
    f = frame(lua, make_player())
    assert f["stats"]["hunger"] == 0.3 and f["stats"]["thirst"] is None and f["load"]["level"] is None
    assert "CharacterStat.THIRST" in missing(lua) and "MoodleType.HEAVY_LOAD" in missing(lua)


def test_a_missing_get_body_parts_is_reported_not_raised(lua):
    load(lua)
    p = make_player()
    bd = p.getBodyDamage(p)
    del bd.getBodyParts
    f = frame(lua, p)
    assert len(f["body"]["parts"]) == 0 and "getBodyParts" in missing(lua)


def test_a_frame_without_the_vanilla_queue_carries_no_action_and_raises_nothing(lua):
    load(lua)
    lua.execute("pcallFails = 0\n"
                "local rawPcall = pcall\n"
                "pcall = function(...)\n"
                "    local r = { rawPcall(...) }\n"
                "    if not r[1] then pcallFails = pcallFails + 1 end\n"
                "    return unpack(r)\n"
                "end")
    g = lua.globals()
    g.ISTimedActionQueue = None
    f = frame(lua, make_player())
    assert f["action"] is None and f["me"]["x"] == 10.0 and g.pcallFails == 0
    lua.execute("ISTimedActionQueue = {}")                       # the class without getTimedActionQueue
    assert frame(lua, make_player())["action"] is None and g.pcallFails == 0
    lua.execute("ISTimedActionQueue = {getTimedActionQueue = function(p) return nil end}")
    assert frame(lua, make_player())["action"] is None and g.pcallFails == 0
    lua.execute("ISTimedActionQueue = {getTimedActionQueue = function(p) return {queue = 'x'} end}")
    assert frame(lua, make_player())["action"] is None and g.pcallFails == 0
    g.ISTimedActionQueue = J(getTimedActionQueue=lambda p: J(queue=[1, 2]))   # a Java-like object, a Python list
    assert frame(lua, make_player())["action"] is None


# ---- the events -----------------------------------------------------------------------------------------------------

def test_damage_records_become_client_damage_events_once(lua):
    load(lua)
    g = lua.globals()
    p = make_player()
    g.getPlayer = lambda: p
    assert len(g._damageHandlers) == 1
    prev = frame(lua, p)
    g._damageHandlers[0](p, "FALLDOWN", 4.5)
    g._damageHandlers[0](make_player(), "ZOMBIE", 1.25)
    ev, cur = events(lua, p, prev)
    dmg = [e for e in ev if e["event"] == "damage"]
    assert [(e["tag"], e["amount"], e["side"], e["gameMin"]) for e in dmg] == [("FALLDOWN", 4.5, "client", 450),
                                                                              ("ZOMBIE", 1.25, "client", 450)]
    assert all(sorted(e.keys()) == ["amount", "event", "gameMin", "side", "tag"] for e in dmg)
    ev, _ = events(lua, p, cur)
    assert [e for e in ev if e["event"] == "damage"] == []


def test_the_damage_hook_is_added_once_and_a_raise_inside_it_is_counted(lua):
    load(lua)
    lua.execute(open(lua_file("client/PZAgent_Sense.lua"), encoding="utf-8").read())
    g = lua.globals()
    assert len(g._damageHandlers) == 1
    g.getPlayer = lambda: (_ for _ in ()).throw(RuntimeError("boom"))
    g._damageHandlers[0](make_player(), "FALLDOWN", 1.0)        # a raise out of the hook would fail the test here
    assert lua.eval("PZA.sense.damageErrors") == 1 and lua.eval("#PZA.sense.damage") == 0


def test_the_damage_list_is_capped_and_counts_the_dropped(lua):
    load(lua)
    g = lua.globals()
    p = make_player()
    g.getPlayer = lambda: p
    prev = frame(lua, p)
    for _ in range(201):
        g._damageHandlers[0](p, "FALLDOWN", 1.0)
    assert lua.eval("PZA.sense.DAMAGE_MAX") == 200
    assert lua.eval("#PZA.sense.damage") == 200 and lua.eval("PZA.sense.damageDropped") == 1
    ev, _ = events(lua, p, prev)
    assert sum(1 for e in ev if e["event"] == "damage") == 200


def test_an_attack_started_flip_is_one_swing(lua):
    load(lua)
    p = make_player()
    prev = frame(lua, p)
    ev, prev = events(lua, p, prev)
    assert [e for e in ev if e["event"] == "swing"] == []
    p.attack["started"], p.attack["delay"] = True, 0.75
    ev, prev = events(lua, p, prev)
    sw = [e for e in ev if e["event"] == "swing"]
    assert [(e["attackStarted"], e["meleeDelay"]) for e in sw] == [(True, 0.75)]
    ev, prev = events(lua, p, prev)                              # still started: no second swing
    assert [e for e in ev if e["event"] == "swing"] == []
    p.attack["started"] = False
    ev, prev = events(lua, p, prev)
    p.attack["started"] = True
    ev, prev = events(lua, p, prev)
    assert len([e for e in ev if e["event"] == "swing"]) == 1


def test_a_zombie_seen_last_frame_reading_dead_is_zombie_dead_once(lua):
    load(lua)
    z1, z2 = live_zombie(1, 12.0, 20.0), live_zombie(2, 14.0, 20.0)
    lua.globals()._cell = make_cell(zombies=[z1, z2])
    p = make_player()
    prev = frame(lua, p)
    z2.st["dead"] = True
    ev, cur = events(lua, p, prev)
    assert [(e["event"], e["id"]) for e in ev if e["event"] == "zombie_dead"] == [("zombie_dead", 2)]
    assert [z["id"] for z in cur["zombies"].values()] == [1]
    ev, _ = events(lua, p, cur)
    assert [e for e in ev if e["event"] == "zombie_dead"] == []
    assert not any(e["event"] in ("zombie_enter", "zombie_leave", "hit") for e in ev)


def test_an_item_added_and_removed_by_id(lua):
    load(lua)
    p = make_player(items=("Base.Apple",))
    lua.eval("PZA.sense.firstSight(...)", p)
    prev = frame(lua, p)
    from .conftest import make_item
    p.held.append(make_item("Base.Plank", 1077))
    ev, prev = events(lua, p, prev)
    add = [e for e in ev if e["event"] == "item_added"]
    assert [(e["itemId"], e["fullType"], e["weight"]) for e in add] == [(1077, "Base.Plank", 1.0)]
    del p.held[0]
    ev, prev = events(lua, p, prev)
    rem = [e for e in ev if e["event"] == "item_removed"]
    assert [(e["itemId"], e["fullType"]) for e in rem] == [(1000, "Base.Apple")]
    assert sorted(rem[0].keys()) == ["event", "fullType", "gameMin", "itemId"]
    ev, _ = events(lua, p, prev)
    assert [e for e in ev if e["event"] in ("item_added", "item_removed")] == []


def door_square(st, cls="IsoDoor"):
    door = J(_cls=cls, IsOpen=lambda s: st["open"])
    return J(getObjects=lambda s: J(size=lambda s2: 1, get=lambda s2, i: door))


def test_a_door_toggled_within_four_tiles_is_a_door_event(lua):
    load(lua)
    near, far, win = {"open": False}, {"open": False}, {"open": True}
    lua.globals()._cell = make_cell(squares={(13, 22, 0): door_square(near), (15, 20, 0): door_square(far),
                                             (6, 16, 0): door_square(win, "IsoWindow")})
    p = make_player()
    prev = frame(lua, p)
    ev, prev = events(lua, p, prev)                              # first sight of each door records it, no event
    assert [e for e in ev if e["event"] == "door"] == []
    near["open"], far["open"], win["open"] = True, True, False
    ev, prev = events(lua, p, prev)
    doors = sorted((e["x"], e["y"], e["z"], e["open"]) for e in ev if e["event"] == "door")
    assert doors == [(6, 16, 0, False), (13, 22, 0, True)]
    assert lua.eval("PZA.sense.DOOR_R") == 4
    ev, _ = events(lua, p, prev)
    assert [e for e in ev if e["event"] == "door"] == []


def test_first_sight_is_one_item_added_per_held_item(lua):
    load(lua)
    p = make_player(items=("Base.Apple", "Base.Plank", "Base.WaterBottle"))
    ev = [dict(e) for e in lua.eval("PZA.sense.firstSight(...)", p).values()]
    assert [(e["event"], e["itemId"], e["fullType"], e["weight"]) for e in ev] == [
        ("item_added", 1000, "Base.Apple", 1.0), ("item_added", 1001, "Base.Plank", 1.0),
        ("item_added", 1002, "Base.WaterBottle", 1.0)]
    assert all(e["gameMin"] == 450 for e in ev)
    prev = frame(lua, p)
    ev, _ = events(lua, p, prev)                                 # first sight seeded the diff
    assert [e for e in ev if e["event"] == "item_added"] == []


def test_event_kinds_and_fields_are_the_schemas(lua):
    load(lua)
    kinds = lua.eval("PZA.schema.events")
    g = lua.globals()
    p = make_player(items=("Base.Apple",))
    g.getPlayer = lambda: p
    z = live_zombie(5, 12.0, 20.0)
    st = {"open": False}
    g._cell = make_cell(zombies=[z], squares={(11, 20, 0): door_square(st)})
    lua.eval("PZA.sense.firstSight(...)", p)
    prev = frame(lua, p)
    _, prev = events(lua, p, prev)
    from .conftest import make_item
    g._damageHandlers[0](p, "FALLDOWN", 1.0)
    p.attack["started"] = True
    z.st["dead"] = True
    st["open"] = True
    p.held.append(make_item("Base.Plank", 1500))
    del p.held[0]
    ev, _ = events(lua, p, prev)
    assert sorted(e["event"] for e in ev) == ["damage", "door", "item_added", "item_removed", "swing", "zombie_dead"]
    for e in ev:
        assert "kind" not in e
        assert sorted(e.keys()) == sorted(["event", "gameMin"] + list(kinds[e["event"]].values())), e["event"]


# ---- the zombie lookups ---------------------------------------------------------------------------------------------

def test_zombie_by_id_is_the_live_zombie_object_and_nil_for_a_dead_or_unknown_id(lua):
    load(lua)
    a, b = make_zombie(7, 30.0, 20.0), make_zombie(8, 11.0, 20.0, dead=True)
    lua.globals()._cell = make_cell(zombies=[a, b])
    p = make_player()
    assert lua.eval("PZA.sense.zombieById(...)", p, 7) is a     # beyond the frame's radius too
    assert lua.eval("PZA.sense.zombieById(...)", p, 8) is None
    assert lua.eval("PZA.sense.zombieById(...)", p, 99) is None


def test_nearest_zombie_is_the_closest_live_one_or_nil(lua):
    load(lua)
    g = lua.globals()
    g._cell = make_cell(zombies=[make_zombie(7, 15.0, 20.0), make_zombie(8, 11.0, 20.0, dead=True),
                                 make_zombie(9, 10.0, 23.0)])
    n = lua.eval("PZA.sense.nearestZombie(...)", make_player())
    assert n["id"] == 9 and abs(n["dist"] - 3.0) < 1e-9
    g._cell = make_cell()
    assert lua.eval("PZA.sense.nearestZombie(...)", make_player()) is None


# ---- the scan job (Task 6 moves it to PZAgent_Map.lua) ---------------------------------------------------------------

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


def step_parts(lua, p, limit=80):
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


def test_scan_job_r15_yields_49_contiguous_parts_of_its_walk(lua):
    load(lua)
    assert lua.eval("PZA.sense.SCAN_SQUARES_PER_TICK") == 20
    calls = clocked_cell(lua, 10, 20, 15)
    pos = {"x": 10.0}
    p = make_player(); p.getX = lambda s: pos["x"]
    lua.eval("PZA.sense.scanStart(...)", p, 15)
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
    assert len(parts) == 49 and [q["part"] for q in parts] == list(range(1, 50))
    assert whole["r"] == 15 and whole["scanTicks"] == 49 and whole["scanMs"] == 961 and whole["scanStepMaxMs"] == 20
    assert [whole["scanMsPerTick"][i] for i in range(1, 50)] == [20] * 48 + [1]
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
    assert [(q["part"], q["parts"], q["r"], len(q["squares"]), q["done"]) for q in second] == [(1, 2, 2, 20, None),
                                                                                                  (2, 2, 2, 5, True)]
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
    assert len(s["scanMsPerTick"]) == s["scanTicks"] == 49
    assert steps == [20] * 48 + [1] and s["scanStepMaxMs"] == 20 and sum(steps) == s["scanMs"]
    s = lua.eval("PZA.sense.scan(...)", make_player(), 0)        # one square, one step
    assert s["scanTicks"] == 1 and s["scanStepMaxMs"] == 1 and s["scanMsPerTick"][1] == 1
