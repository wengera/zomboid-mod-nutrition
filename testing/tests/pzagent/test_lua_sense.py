"""PZAgent_Sense.lua (Plan 22 Task 5): the frame as the PZA/1 schema's groups (a measured pace, the run latch read from
the Motor's post-assert fields, load, body parts, weapon reach), the typed events, the inventory's first sight and the
zombie lookups. The scan job's tests moved to test_lua_map.py with the job (Task 6)."""
import json
import os
import re

from .conftest import ROOT, lua_file, make_player, make_weapon, make_zombie, make_cell, J

SCHEMA = os.path.join(ROOT, "testing", "agent", "base", "schema", "pza1.json")
ENVELOPE = ("kind", "seq", "tick", "wallMs")
GROUPS = ("me", "stats", "body", "load", "weapon", "action", "act", "cost")


def load(lua):
    for f in ("shared/PZAgent_World.lua", "client/PZAgent_Link.lua", "client/PZAgent_Motor.lua",
              "client/PZAgent_Skills.lua", "client/PZAgent_SkillsWorld.lua",
              "client/PZAgent_Stance.lua", "client/PZAgent_Tend.lua", "client/PZAgent_Sense.lua"):
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
    lua.execute("PZA.link.frames = 1")                           # a delta next: loadedWidth not carried again
    f = frame(lua, p)                                            # the second frame carries a pace
    top = [k for k in d["frame"]["x-order"] if k not in ENVELOPE and k != "cost"]
    assert sorted(f.keys()) == sorted(top)
    for grp in GROUPS:
        if grp == "cost":
            continue
        ref = "act_now" if grp == "act" else grp
        want = list(d[ref]["x-order"])
        if grp == "me":
            want.remove("worn")                                  # PZA/1.6: elided on a frame whose list is unchanged
            want.remove("loadedWidth")                           # PZA/1.7: carried once read and changed, the fake cell has no chunk map
        assert sorted(f[grp].keys()) == sorted(want), grp
    unbandaged = {"bandageLife", "bandageDirty"}                 # PZA/1.5: nil on an unbandaged part
    assert sorted(f["body"]["parts"][1].keys()) == sorted(set(d["part"]["x-order"]) - unbandaged)
    assert sorted(f["zombies"][1].keys()) == sorted(set(d["zombie"]["x-order"]) - {"onFloor"})   # PZA/1.7: nil while standing
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
    assert lua.eval("PZA.enc.body(...)", b) == ("[88,1,2,0,[[3,62.5,false,0,false,null,null,false,false],"
                                                "[11,99,false,0,false,null,null,false,false]],0,[0,0]]")   # PZA/1.5's fields, PZA/1.7's
    unhurt = frame(lua, make_player())["body"]
    assert lua.eval("PZA.enc.body(...)", unhurt) == "[100,0,0,0,[],0,[0,0]]"


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
        assert not re.search(r':%s\s*\(' % name, src), name      # the method-call form too


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
    assert [(e["tag"], e["amount"], e["side"], e["gameMin"]) for e in dmg] == [("FALLDOWN", 4.5, "client", 450)]
    assert lua.eval("PZA.sense.damageRemote") == 1               # the second player's record is no event of ours
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


def door_square(st, x, y, cls="IsoDoor"):
    """A square at (x, y, 0) holding one portal of class cls whose IsOpen reads st["open"]."""
    door = J(_cls=cls, IsOpen=lambda s: st["open"], isLocked=lambda s: False, isBarricaded=lambda s: False)
    return J(getX=lambda s: x, getY=lambda s: y, getZ=lambda s: 0,
             getObjects=lambda s: J(size=lambda s2: 1, get=lambda s2, i: door))


def load_map(lua):
    """Map beside Sense: the door events come from its records (X4 fix pass 2.3)."""
    lua.execute(open(lua_file("client/PZAgent_Map.lua"), encoding="utf-8").read())


def watch_cycle(lua, p):
    """One whole watch cycle (22 steps of 8 squares cover the 169-square ring), the tick advancing 6 a step."""
    g = lua.globals()
    for _ in range(22):
        g.PZA.tick = (g.PZA.tick or 0) + 6
        lua.eval("PZA.map.watchStep(...)", p)


def test_a_door_or_window_toggled_on_the_watchs_ring_is_a_door_event(lua):
    load(lua)
    load_map(lua)
    near, far, win = {"open": False}, {"open": False}, {"open": True}
    lua.globals()._cell = make_cell(squares={(13, 22, 0): door_square(near, 13, 22),
                                             (17, 20, 0): door_square(far, 17, 20),
                                             (6, 16, 0): door_square(win, 6, 16, "IsoWindow")})
    p = make_player()
    prev = frame(lua, p)
    watch_cycle(lua, p)
    ev, prev = events(lua, p, prev)                              # first sight of each square records it, no event
    assert [e for e in ev if e["event"] == "door"] == []
    near["open"], far["open"], win["open"] = True, True, False
    watch_cycle(lua, p)
    ev, prev = events(lua, p, prev)
    doors = sorted((e["x"], e["y"], e["z"], e["open"]) for e in ev if e["event"] == "door")
    assert doors == [(6, 16, 0, False), (13, 22, 0, True)]      # (17, 20) is 7 tiles out: off the ring
    assert lua.eval("PZA.sense.DOOR_R") is None
    ev, _ = events(lua, p, prev)
    assert [e for e in ev if e["event"] == "door"] == []


def test_the_door_events_z_is_the_squares_on_a_stair(lua):
    load(lua)
    load_map(lua)
    st = {"open": False}
    lua.globals()._cell = make_cell(squares={(12, 20, 0): door_square(st, 12, 20)})
    p = make_player(z=0.5)
    prev = frame(lua, p)
    watch_cycle(lua, p)
    _, prev = events(lua, p, prev)
    st["open"] = True
    watch_cycle(lua, p)
    ev, _ = events(lua, p, prev)
    doors = [e for e in ev if e["event"] == "door"]
    assert [(e["x"], e["y"], e["z"], e["open"]) for e in doors] == [(12, 20, 0, True)]
    assert lua.eval("PZA.enc.v(...)", doors[0]["z"]) == "0"


def test_an_object_inserted_before_two_portals_never_shifts_their_states(lua):
    load(lua)
    load_map(lua)
    a, b = {"open": False}, {"open": True}
    da = J(_cls="IsoDoor", IsOpen=lambda s: a["open"], isLocked=lambda s: False, isBarricaded=lambda s: False)
    wb = J(_cls="IsoWindow", IsOpen=lambda s: b["open"], isLocked=lambda s: False, isBarricaded=lambda s: False)
    objs = [da, wb]
    sq = J(getX=lambda s: 11, getY=lambda s: 20, getZ=lambda s: 0,
           getObjects=lambda s: J(size=lambda s2: len(objs), get=lambda s2, i: objs[i]))
    lua.globals()._cell = make_cell(squares={(11, 20, 0): sq})
    p = make_player()
    prev = frame(lua, p)
    watch_cycle(lua, p)
    _, prev = events(lua, p, prev)
    objs.insert(0, J(_cls="IsoWorldInventoryObject"))             # a dropped item lands before both portals
    watch_cycle(lua, p)
    ev, prev = events(lua, p, prev)
    assert [e for e in ev if e["event"] == "door"] == []
    a["open"] = True
    watch_cycle(lua, p)
    ev, prev = events(lua, p, prev)
    assert [(e["x"], e["y"], e["open"]) for e in ev if e["event"] == "door"] == [(11, 20, True)]
    ev, _ = events(lua, p, prev)
    assert [e for e in ev if e["event"] == "door"] == []


def test_sense_reads_no_square_for_its_door_events(lua):
    """X4 fix pass 2.3: Sense's per-frame door walk is gone; an events call reads no grid square."""
    load(lua)
    load_map(lua)
    calls = []
    lua.globals()._cell = J(getZombieList=lambda s: J(size=lambda s2: 0),
                            getGridSquare=lambda s, x, y, z: calls.append((x, y)))
    p = make_player()
    prev = frame(lua, p)
    for _ in range(3):
        _, prev = events(lua, p, prev)
    assert calls == []


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


def test_every_first_sight_item_added_carries_a_use_of_the_five(lua):
    load(lua)
    p = make_player(items=("Base.Apple", "Base.WaterBottle", "Base.Axe", "Base.RippedSheets", "Base.Plank"))
    ev = [dict(e) for e in lua.eval("PZA.sense.firstSight(...)", p).values() if e["event"] == "item_added"]
    assert len(ev) == 5
    assert all(e["use"] in ("food", "water", "weapon", "bandage", "other", "container") for e in ev)


def test_event_kinds_and_fields_are_the_schemas(lua):
    load(lua)
    kinds = lua.eval("PZA.schema.events")
    g = lua.globals()
    p = make_player(items=("Base.Apple",))
    g.getPlayer = lambda: p
    z = live_zombie(5, 12.0, 20.0)
    st = {"open": False}
    g._cell = make_cell(zombies=[z], squares={(11, 20, 0): door_square(st, 11, 20)})
    load_map(lua)
    lua.eval("PZA.sense.firstSight(...)", p)
    prev = frame(lua, p)
    watch_cycle(lua, p)
    _, prev = events(lua, p, prev)
    from .conftest import make_item
    g._damageHandlers[0](p, "FALLDOWN", 1.0)
    p.attack["started"] = True
    z.st["dead"] = True
    st["open"] = True
    watch_cycle(lua, p)
    shirt = make_item("Base.Tshirt_DefaultTEXTURE", 1500)      # PZA/1.5.2: worn and cotton, so worn and rip are sent
    shirt.isWorn = lambda s: True
    shirt._cls, shirt.getBodyLocation = "Clothing", lambda s: "base:tshirt"   # PZA/1.6: a Clothing, its record sent
    p.held.append(shirt)
    del p.held[0]
    ev, _ = events(lua, p, prev)
    assert sorted(e["event"] for e in ev) == ["damage", "door", "item_added", "item_removed", "swing", "zombie_dead"]
    for e in ev:
        assert "kind" not in e
        assert sorted(e.keys()) == sorted(["event", "gameMin"] + list(kinds[e["event"]].values())), e["event"]


# ---- PZA/1.3: the death event (ruling P23-AO) -------------------------------------------------------------------------

def death_events(ev):
    return [e for e in ev if e["event"] == "death"]


def test_the_death_hook_naming_the_local_player_is_one_death_event_with_its_frames_reads(lua):
    load(lua)
    g = lua.globals()
    p = make_player(x=10770.67, y=10640.48, health=19.506973266601562)
    p.getZombieKills = lambda s: 1
    p.isDead = lambda s: False                                   # the client's copy never reads dead or 0
    g.getPlayer = lambda: p
    assert len(g._deathHandlers) == 1
    prev = frame(lua, p)
    ev, prev = events(lua, p, prev)
    assert death_events(ev) == []
    g._deathHandlers[0](make_player())                           # another character's death
    ev, prev = events(lua, p, prev)
    assert death_events(ev) == [] and lua.eval("PZA.sense.deathRemote") == 1
    g._deathHandlers[0](p)
    ev, prev = events(lua, p, prev)
    d = death_events(ev)
    assert d == [{"event": "death", "gameMin": 450, "worldAge": 31.5, "x": 10770.67, "y": 10640.48, "z": 0,
                  "health": 19.506973266601562, "zombiesKilled": 1, "via": "hook"}]
    kinds = lua.eval("PZA.schema.events")
    assert sorted(d[0].keys()) == sorted(["event", "gameMin"] + list(kinds["death"].values()))
    for _ in range(3):                                           # once: the frames go on, no second event
        ev, prev = events(lua, p, prev)
        assert death_events(ev) == [] and prev is not None


def test_is_dead_reading_true_without_the_hook_is_one_death_event_via_is_dead(lua):
    load(lua)
    g = lua.globals()
    st = {"dead": False}
    p = make_player(health=0.0)
    p.isDead = lambda s: st["dead"]
    p.getZombieKills = lambda s: 3
    g.getPlayer = lambda: p
    prev = frame(lua, p)
    ev, prev = events(lua, p, prev)
    assert death_events(ev) == []                                # health 0 alone is no event: the hook or isDead
    st["dead"] = True
    ev, prev = events(lua, p, prev)
    assert [(e["via"], e["zombiesKilled"], e["health"]) for e in death_events(ev)] == [("isDead", 3, 0.0)]
    g._deathHandlers[0](p)                                       # a late hook for the same player: still once
    ev, _ = events(lua, p, prev)
    assert death_events(ev) == []


def test_a_new_player_object_can_die_again_and_a_raise_in_the_hook_is_counted(lua):
    load(lua)
    g = lua.globals()
    p1, p2 = make_player(), make_player()
    for q in (p1, p2):
        q.isDead, q.getZombieKills = (lambda s: False), (lambda s: 0)
    g.getPlayer = lambda: p1
    prev = frame(lua, p1)
    g._deathHandlers[0](p1)
    ev, prev = events(lua, p1, prev)
    assert len(death_events(ev)) == 1
    g.getPlayer = lambda: p2
    g._deathHandlers[0](p2)
    ev, prev = events(lua, p2, prev)
    assert len(death_events(ev)) == 1
    g.getPlayer = lambda: (_ for _ in ()).throw(RuntimeError("boom"))
    g._deathHandlers[0](p2)                                      # a raise out of the hook would fail the test here
    assert lua.eval("PZA.sense.deathErrors") == 1


def test_the_death_block_sits_at_the_end_of_sense():
    """CLAUDE.md section 5 (review M1): a harness Lua edit appends its new sites at the end of its file."""
    with open(lua_file("client/PZAgent_Sense.lua"), encoding="utf-8") as f:
        src = f.read()
    assert src.index("Events.OnPlayerDeath.Add") > src.index("function S.nearestZombie")
    assert src.index("function S.playerDeathEvents") > src.index("function S.nearestZombie")


def test_an_absent_kill_count_leaves_zombies_killed_nil_and_names_it_missing(lua):
    load(lua)
    g = lua.globals()
    p = make_player()
    p.isDead = lambda s: True
    g.getPlayer = lambda: p
    prev = frame(lua, p)
    ev, _ = events(lua, p, prev)
    d = death_events(ev)
    assert len(d) == 1 and "zombiesKilled" not in d[0] and "getZombieKills" in missing(lua)


# ---- the zombie lookups ---------------------------------------------------------------------------------------------

def test_zombie_by_id_is_the_live_zombie_object_and_nil_for_a_dead_or_unknown_id(lua):
    load(lua)
    a, b = make_zombie(7, 30.0, 20.0), make_zombie(8, 11.0, 20.0, dead=True)
    lua.globals()._cell = make_cell(zombies=[a, b])
    p = make_player()
    assert lua.eval("PZA.sense.zombieById(...)", p, 7) is a     # beyond the frame's radius too
    assert lua.eval("PZA.sense.zombieById(...)", p, 8) is None
    assert lua.eval("PZA.sense.zombieById(...)", p, 99) is None


def test_zombie_by_id_takes_the_last_frames_object_before_walking_the_cell(lua):
    load(lua)
    g = lua.globals()
    z = live_zombie(7, 12.0, 20.0)
    zl = J(size=lambda s: 1, get=lambda s, i: z)
    calls = {"n": 0}

    def zombie_list(s):
        calls["n"] += 1
        return zl
    g._cell = J(getZombieList=zombie_list, getGridSquare=lambda s, x, y, zz: None)
    p = make_player()
    frame(lua, p)                                                # the frame saw zombie 7
    n0 = calls["n"]
    assert lua.eval("PZA.sense.zombieById(...)", p, 7) is z and calls["n"] == n0
    z.st["dead"] = True
    assert lua.eval("PZA.sense.zombieById(...)", p, 7) is None and calls["n"] == n0
    assert lua.eval("PZA.sense.zombieById(...)", p, 8) is None and calls["n"] == n0 + 1   # unknown: the walk


def test_an_item_whose_id_cannot_be_read_is_reported_missing(lua):
    load(lua)
    p = make_player(items=("Base.Apple",))
    del p.held[0].getID
    lua.eval("PZA.sense.firstSight(...)", p)
    assert "getID" in missing(lua)


def test_nearest_zombie_is_the_last_frames_closest_live_one_or_nil(lua):
    """Fix wave M9: the snapshot's nearest is the last frame's first zombie (the frame sorts them nearest first)."""
    load(lua)
    g = lua.globals()
    assert lua.eval("PZA.sense.nearestZombie(...)", make_player()) is None      # no frame yet
    g._cell = make_cell(zombies=[make_zombie(7, 15.0, 20.0), make_zombie(8, 11.0, 20.0, dead=True),
                                 make_zombie(9, 10.0, 23.0)])
    frame(lua, make_player())
    n = lua.eval("PZA.sense.nearestZombie(...)", make_player())
    assert dict(n) == {"id": 9, "dist": 3.0}
    g._cell = make_cell()
    frame(lua, make_player())
    assert lua.eval("PZA.sense.nearestZombie(...)", make_player()) is None


def test_nearest_zombie_reads_no_cell_list(lua):
    """Fix wave M9: with 50 zombies in the cell list, the snapshot's nearest calls the cell's list reader not once."""
    load(lua)
    g = lua.globals()
    zs = [make_zombie(100 + i, 10.0 + 0.1 * (i + 1), 20.0) for i in range(50)]
    calls = {"list": 0, "get": 0}

    def get(s, i):
        calls["get"] += 1
        return zs[i]
    zl = J(size=lambda s: len(zs), get=get)

    def zombie_list(s):
        calls["list"] += 1
        return zl
    g._cell = J(getZombieList=zombie_list, getGridSquare=lambda s, x, y, z: None)
    frame(lua, make_player())
    seen = dict(calls)
    assert seen["list"] >= 1 and seen["get"] >= 50
    n = lua.eval("PZA.sense.nearestZombie(...)", make_player())
    assert n["id"] == 100 and abs(n["dist"] - 0.1) < 1e-9
    snap = lua.eval("PZA.skills.snapshot(...)", make_player())
    assert snap["nearest"]["id"] == 100
    assert calls == seen


# ---- a raising Java member (ruling S-15) -----------------------------------------------------------------------------

def boom(*a):
    raise RuntimeError("java raised")


def test_a_raising_group_reader_costs_only_its_group_and_the_frame_still_encodes(lua):
    load(lua)
    p = make_player(weapon=make_weapon())
    p.getStats = boom
    f = frame(lua, p)
    assert f["stats"] is not None and f["stats"]["hunger"] is None
    assert f["me"]["x"] == 10.0 and f["body"]["health"] == 100.0 and f["load"]["max"] == 8
    assert f["weapon"]["type"] is not None
    assert "raise:stats" in missing(lua) and lua.eval("PZA.sense.frameErrors") == 1
    assert "java raised" in lua.eval("PZA.sense.lastFrameError")
    assert lua.eval("PZA.enc.stats(...)", f["stats"]) == "[" + ",".join(["null"] * 9) + "]"


def test_a_raising_required_body_keeps_its_parts_array_and_a_nullable_group_is_nil(lua):
    load(lua)
    p = make_player(weapon=make_weapon())
    p.getBodyDamage, p.getPrimaryHandItem = boom, boom
    f = frame(lua, p)
    assert lua.eval("PZA.enc.body(...)", f["body"]) == "[null,null,null,null,[],null,null]"
    assert f["weapon"] is None
    # PZA/1.7: the arms' read raises on the same getBodyDamage, a third caught raise (raise:body:arms)
    assert {"raise:body", "raise:weapon", "raise:body:arms"} <= set(missing(lua))
    assert lua.eval("PZA.sense.frameErrors") == 3


def test_a_raising_position_leaves_me_empty_and_the_zombies_an_empty_array(lua):
    load(lua)
    lua.globals()._cell = make_cell(zombies=[live_zombie(1, 12.0, 20.0)])
    p = make_player()
    p.getX = boom
    f = frame(lua, p)
    assert f["me"]["x"] is None and f["me"]["y"] is None and list(f["zombies"].values()) == []
    assert "raise:me" in missing(lua)


def test_a_raising_event_kind_costs_only_its_events(lua):
    load(lua)
    p = make_player(items=("Base.Apple",))
    lua.eval("PZA.sense.firstSight(...)", p)
    prev = frame(lua, p)
    from .conftest import make_item
    p.held.append(make_item("Base.Plank", 1077))
    p.isAttackStarted = boom
    ev, cur = events(lua, p, prev)
    assert [(e["event"], e["itemId"]) for e in ev if e["event"] == "item_added"] == [("item_added", 1077)]
    assert cur["me"]["x"] == 10.0
    assert "raise:event:swing" in missing(lua) and lua.eval("PZA.sense.frameErrors") == 1


def test_an_event_kind_raising_midway_adds_none_of_its_events_and_keeps_its_last_state(lua):
    load(lua)
    p = make_player(items=("Base.Apple",))
    lua.eval("PZA.sense.firstSight(...)", p)
    prev = frame(lua, p)
    from .conftest import make_item
    p.held.append(make_item("Base.Plank", 1077))
    bad = make_item("Base.Nail", 1078)
    bad.getFullType = boom
    p.held.append(bad)
    ev, prev = events(lua, p, prev)
    assert [e for e in ev if e["event"] == "item_added"] == []
    assert "raise:event:item" in missing(lua)
    p.held.remove(bad)
    ev, _ = events(lua, p, prev)
    assert [e["itemId"] for e in ev if e["event"] == "item_added"] == [1077]


# ---- X4 fix pass 1: the cell list's size against the zombies listed (M15) ----------------------------------------------

def test_me_carries_the_cell_lists_size_and_the_zombies_listed(lua):
    load(lua)
    zs = [make_zombie(1, 12.0, 20.0), make_zombie(2, 11.0, 20.0, dead=True), make_zombie(3, 40.0, 20.0),
          make_zombie(4, 10.0, 25.0)]
    lua.globals()._cell = make_cell(zombies=zs)
    f = frame(lua, make_player())
    assert (f["me"]["zombiesSeen"], f["me"]["zombiesListed"]) == (4, 2)
    lua.globals()._cell = make_cell()
    f = frame(lua, make_player())
    assert (f["me"]["zombiesSeen"], f["me"]["zombiesListed"]) == (0, 0)


# ---- X4 fix pass 2.4: one cell walk a frame, shared with zombie_dead (review I7) ---------------------------------------

def test_an_events_call_walks_the_cell_list_once_and_zombie_dead_reuses_the_walk(lua):
    load(lua)
    g = lua.globals()
    zs = [live_zombie(100 + i, 10.0 + 0.2 * (i + 1), 20.0) for i in range(50)]
    calls = {"list": 0, "size": 0, "get": 0, "dead": 0}
    for z in zs:
        def dead(s, z=z):
            calls["dead"] += 1
            return z.st["dead"]
        z.isDead = dead

    def get(s, i):
        calls["get"] += 1
        return zs[i]

    def size(s):
        calls["size"] += 1
        return len(zs)
    zl = J(size=size, get=get)

    def zombie_list(s):
        calls["list"] += 1
        return zl
    g._cell = J(getZombieList=zombie_list, getGridSquare=lambda s, x, y, z: None)
    p = make_player()
    prev = frame(lua, p)
    zs[3].st["dead"] = True
    for k in calls:
        calls[k] = 0
    ev, cur = events(lua, p, prev)
    # the walk asks each of the 50 once; zombie_dead asks only the last frame's zombies this frame did not list alive
    # (103), never the 49 the walk just found alive
    assert calls == {"list": 1, "size": 1, "get": 50, "dead": 51}
    assert [e["id"] for e in ev if e["event"] == "zombie_dead"] == [103]
    assert (cur["me"]["zombiesSeen"], cur["me"]["zombiesListed"]) == (50, 49)


# ---- X4 fix pass 2.5: the act line's snapshot off the last frame (review I8) -------------------------------------------

def test_a_snapshot_after_a_frame_reads_the_frames_health_and_nearest_and_only_the_players_position(lua):
    load(lua)
    g = lua.globals()
    g._cell = make_cell(zombies=[make_zombie(7, 12.0, 20.0)])
    p = make_player(health=80.0)
    frame(lua, p)
    reads = []
    for name in ("getBodyDamage", "getStats", "getInventory", "getPrimaryHandItem", "getMoodles"):
        real = getattr(p, name)
        setattr(p, name, lambda s, real=real, name=name: reads.append(name) or real(s))
    g._cell = J(getZombieList=lambda s: reads.append("getZombieList"), getGridSquare=lambda s, x, y, z: None)
    snap = lua.eval("PZA.skills.snapshot(...)", p)
    assert dict(snap["me"]) == {"x": 10.0, "y": 20.0, "z": 0, "health": 80.0}
    assert dict(snap["nearest"]) == {"id": 7, "dist": 2.0}
    assert reads == []


def test_a_snapshot_before_any_frame_reads_the_players_health(lua):
    load(lua)
    p = make_player(health=64.0)
    assert lua.eval("PZA.skills.snapshot(...)", p)["me"]["health"] == 64.0


def test_the_frame_carries_the_hour(lua):
    load(lua)
    assert frame(lua, make_player())["me"]["hour"] == 8.0


def test_first_sight_carries_the_engines_use_of_each_item(lua):
    load(lua)
    from .conftest import make_item, make_fluid
    apple = make_item("Base.Apple", 1)
    apple._cls = "Food"
    bat = make_item("Base.BaseballBat", 2)
    bat._cls = "HandWeapon"
    bottle = make_item("Base.WaterBottle", 3)
    pan = make_item("Base.Saucepan", 4)
    pan._cls = "HandWeapon"
    pan.getFluidContainer = lambda s: make_fluid()
    rag = make_item("Base.RippedSheets", 5)
    rag2 = make_item("Base.RagDirty", 6)
    plank = make_item("Base.Plank", 7)
    bleach = make_item("Base.Bleach", 8)
    p = make_player()
    p.held.extend([apple, bat, bottle, pan, rag, rag2, plank, bleach])
    ev = [dict(e) for e in lua.eval("PZA.sense.firstSight(...)", p).values()]
    got = {e["itemId"]: e["use"] for e in ev if e["itemId"] >= 1 and e["itemId"] <= 8}
    # PZA/1.5.1 (Task 9 review minor 5): bandage is isCanBandage(), so the rip's RippedSheets reads bandage and a
    # RagDirty (no CanBandage in its script) other
    assert got == {1: "food", 2: "weapon", 3: "water", 4: "weapon", 5: "bandage", 6: "other", 7: "other", 8: "other"}


# ---- PZA/1.4.1 (ruling P24-F): the use table reads only drinkable water and edible food ---------------------------------

def _uses(lua, *items):
    p = make_player()
    p.held.extend(items)
    ev = [dict(e) for e in lua.eval("PZA.sense.firstSight(...)", p).values()]
    return {e["itemId"]: e["use"] for e in ev if 1 <= e["itemId"] <= len(items)}


def test_a_disinfectant_reads_other_a_water_bottle_water_and_a_bleach_bottle_other(lua):
    """F2's Disinfectant (RubbingAlcohol: a fluid container, not poisonous, not water) read `water` and was drunk 68
    times with no thirst fall; isWaterSource is the jar's water test (FluidContainer.isWaterSource @0 L875)."""
    load(lua)
    from .conftest import make_item, make_fluid
    disinfectant = make_item("Base.Disinfectant", 1)
    disinfectant.getFluidContainer = lambda s, fc=make_fluid(water=False): fc
    bottle = make_item("Base.WaterBottle", 2)
    bleach = make_item("Base.Bleach", 3)
    assert _uses(lua, disinfectant, bottle, bleach) == {1: "other", 2: "water", 3: "other"}


def test_an_empty_drinkable_container_reads_container_and_never_water(lua):
    load(lua)
    from .conftest import make_item, make_fluid
    empty = make_item("Base.WaterBottle", 1)
    empty.getFluidContainer = lambda s, fc=make_fluid(amount=0.0): fc
    mug = make_item("Base.Mugl", 2)
    mug.getFluidContainer = lambda s, fc=make_fluid(amount=0.0, capacity=0.2): fc
    locked = make_item("Base.PopEmpty", 3)                      # canAddFluid(Water) false: never a container
    locked.getFluidContainer = lambda s, fc=make_fluid(amount=0.0, can_add=False): fc
    bucket = make_item("Base.BucketEmpty", 4)                   # over the drink menu's 3 litres: not drinkable from
    bucket.getFluidContainer = lambda s, fc=make_fluid(amount=0.0, capacity=10.0): fc
    unread = make_item("Base.Bowl", 5)                          # canAddFluid absent: fails closed
    unread.getFluidContainer = lambda s, fc=make_fluid(amount=0.0, can_add=None): fc
    bleach = make_item("Base.Bleach", 6)                        # an empty bleach bottle is never a water container
    bleach.getFluidContainer = lambda s, fc=make_fluid(amount=0.0, water=False): fc
    assert _uses(lua, empty, mug, locked, bucket, unread, bleach) == {
        1: "container", 2: "container", 3: "other", 4: "other", 5: "other", 6: "other"}


def test_water_needs_every_drinkability_read(lua):
    """Tainted, poisonous, over 3 litres or with a read absent (isWaterSource, isTainted, getCapacity), a container
    holding water reads `other`; a half-full water bottle is still `water`."""
    load(lua)
    from .conftest import make_item, make_fluid
    cases = [make_fluid(amount=0.25), make_fluid(tainted=True), make_fluid(poison=True),
             make_fluid(capacity=10.0), make_fluid(water=None), make_fluid(tainted=None), make_fluid(capacity=None)]
    items = []
    for i, fc in enumerate(cases, 1):
        it = make_item("Base.WaterBottle", i)
        it.getFluidContainer = lambda s, fc=fc: fc
        items.append(it)
    assert _uses(lua, *items) == {1: "water", 2: "other", 3: "other", 4: "other", 5: "other", 6: "other", 7: "other"}


def test_food_needs_a_hunger_change_below_zero(lua):
    load(lua)
    from .conftest import make_item
    apple = make_item("Base.Apple", 1)
    apple._cls = "Food"
    salt = make_item("Base.Salt", 2)
    salt._cls = "Food"                                          # IsFood, hunger change 0: not food
    unread = make_item("Base.Apple", 3)
    unread._cls = "Food"
    unread.getHungerChange = None                               # absent: fails closed
    assert _uses(lua, apple, salt, unread) == {1: "food", 2: "other", 3: "other"}


# ---- PZA/1.4 (ruling P24-C): me's attackers, hitReaction and dragDown --------------------------------------------------

def test_the_frames_me_carries_the_attackers_the_hit_reaction_and_the_drag_down(lua):
    load(lua)
    lua.globals()._cell = make_cell(zombies=[make_zombie(1, 11.0, 20.0)])   # one tile off: the count is asked
    p = make_player()
    f = frame(lua, p)
    assert (f["me"]["attackers"], f["me"]["hitReaction"], f["me"]["dragDown"]) == (0, "", False)
    p.combat.update(attackers=2, hitReaction="HitReactionFront", dragDown=True)
    f = frame(lua, p)
    assert (f["me"]["attackers"], f["me"]["hitReaction"], f["me"]["dragDown"]) == (2, "HitReactionFront", True)
    assert f["me"]["x"] == 10.0 and f["me"]["hour"] == 8.0 and missing(lua) == []
    assert lua.eval("PZA.sense.last.me.attackers") == 2          # the frame S.last keeps is the one carrying them
    order = lua.eval("PZA.schema.groups.me")
    assert [order[i] for i in range(15, 18)] == ["attackers", "hitReaction", "dragDown"]
    enc = json.loads(lua.eval("PZA.enc.me(...)", f["me"]))
    assert enc[14:17] == [2, "HitReactionFront", True]


def test_a_nil_hit_reaction_reads_empty_and_an_absent_member_is_nil_and_named_missing(lua):
    load(lua)
    p = make_player()
    p.combat["hitReaction"] = None
    assert frame(lua, p)["me"]["hitReaction"] == ""
    lua.globals()._cell = make_cell(zombies=[make_zombie(1, 11.0, 20.0)])
    q = make_player()
    q.getSurroundingAttackingZombies, q.getHitReaction, q.isDeathDragDown = None, None, None
    f = frame(lua, q)
    assert (f["me"]["attackers"], f["me"]["hitReaction"], f["me"]["dragDown"]) == (None, None, None)
    assert {"getSurroundingAttackingZombies", "getHitReaction", "isDeathDragDown"} <= set(missing(lua))
    assert f["me"]["x"] == 10.0


def test_a_raising_combat_read_costs_only_the_three_fields(lua):
    load(lua)
    p = make_player()
    p.getHitReaction = boom
    f = frame(lua, p)
    assert f["me"]["attackers"] == 0 and f["me"]["hitReaction"] is None and f["me"]["dragDown"] is None
    assert f["me"]["x"] == 10.0 and "raise:me:combat" in missing(lua) and lua.eval("PZA.sense.frameErrors") == 1
    ev, cur = events(lua, p, f)                                  # the events path reads the same frame
    assert cur["me"]["x"] == 10.0 and lua.eval("PZA.sense.frameErrors") == 2


def test_the_combat_block_sits_at_the_end_of_sense():
    """CLAUDE.md section 5: the 1.4 reads are appended after the death block, so no repo: pointer into Sense moves."""
    with open(lua_file("client/PZAgent_Sense.lua"), encoding="utf-8") as f:
        src = f.read()
    assert src.index("getSurroundingAttackingZombies") > src.index("function S.playerDeathEvents")
    assert src.index("isDeathDragDown") > src.index("function S.playerDeathEvents")


def test_the_attackers_read_runs_only_with_a_listed_zombie_within_2_tiles(lua):
    """Fix 1 (review M1): the frame runs every tick at rate 60, so getSurroundingAttackingZombies (whose count is of
    zombies within 0.9 tiles) is called only when the frame's nearest listed zombie is under NEAR_R (2) tiles or the
    zombie walk could not be read; otherwise attackers reads 0 without the call."""
    load(lua)
    g = lua.globals()
    calls = []
    p = make_player()
    p.getSurroundingAttackingZombies = lambda s: calls.append(1) or 3
    assert lua.eval("PZA.sense.NEAR_R") == 2
    assert frame(lua, p)["me"]["attackers"] == 0 and calls == []          # nobody listed
    g._cell = make_cell(zombies=[make_zombie(1, 12.5, 20.0)])            # 2.5 tiles off
    assert frame(lua, p)["me"]["attackers"] == 0 and calls == []
    g._cell = make_cell(zombies=[make_zombie(1, 12.5, 20.0), make_zombie(2, 11.5, 20.0)])   # 1.5 tiles off
    assert frame(lua, p)["me"]["attackers"] == 3 and calls == [1]
    g._cell = J(getZombieList=lambda s: None)                            # the walk unread: the call is made
    f = frame(lua, p)
    assert f["me"]["zombiesSeen"] is None and f["me"]["attackers"] == 3 and calls == [1, 1]


# ---- PZA/1.5 (ruling P24-G): me.aiming; water is any quenching beverage (the Task 9 amendment) ------------------------

def test_the_frames_me_carries_aiming_from_is_aiming(lua):
    load(lua)
    p = make_player()
    assert frame(lua, p)["me"]["aiming"] is False
    p.aim["force"] = True
    f = frame(lua, p)
    assert f["me"]["aiming"] is True
    order = lua.eval("PZA.schema.groups.me")
    assert order[18] == "aiming" and json.loads(lua.eval("PZA.enc.me(...)", f["me"]))[17] is True
    q = make_player()
    q.isAiming = None
    assert frame(lua, q)["me"]["aiming"] is None and "isAiming" in missing(lua)


def test_a_pop_a_juice_and_a_milk_read_water_and_a_bleach_a_beer_and_a_sealed_category_read_other(lua):
    """The amendment: water is any drinkable fluid that lowers thirst and harms nothing; a pop (Cola: Beverage, thirst
    -30 in scripts/generated/fluids.txt) reads water as a water bottle does, a bleach (Hazardous, poisonous) or a beer
    (Alcoholic) never, and a container whose isCategory or getProperties is absent fails closed."""
    load(lua)
    from .conftest import make_item, make_fluid
    specs = [
        ("Base.Pop2", make_fluid(water=False, cats={"Beverage"}, thirst=-0.3, fluid="Cola")),
        ("Base.JuiceBox", make_fluid(water=False, cats={"Beverage"}, thirst=-0.3, fluid="JuiceGrape")),
        ("Base.Milk", make_fluid(water=False, cats={"Beverage"}, thirst=-0.5, fluid="CowMilk")),
        ("Base.Bleach", make_fluid(water=False, poison=True, cats={"Hazardous"}, thirst=-0.2, fluid="Bleach")),
        ("Base.BeerCan", make_fluid(water=False, cats={"Beverage", "Alcoholic"}, thirst=-0.2, fluid="Beer")),
        ("Base.Pop3", make_fluid(water=False, cats=None, thirst=-0.3)),
        ("Base.Pop", make_fluid(water=False, cats={"Beverage"}, thirst=None)),
        ("Base.AnimalBlood", make_fluid(water=False, cats={"Beverage"}, thirst=0.0)),
        ("Base.Disinfectant", make_fluid(water=False, cats={"Medical", "Alcoholic"}, thirst=0.0)),
    ]
    items = []
    for i, (ft, fc) in enumerate(specs, 1):
        it = make_item(ft, i)
        it.getFluidContainer = lambda s, fc=fc: fc
        items.append(it)
    assert _uses(lua, *items) == {1: "water", 2: "water", 3: "water", 4: "other", 5: "other", 6: "other",
                                  7: "other", 8: "other", 9: "other"}


def test_without_fluid_category_only_a_water_source_reads_water(lua):
    load(lua)
    from .conftest import make_item, make_fluid
    lua.globals().FluidCategory = None
    pop = make_item("Base.Pop2", 1)
    pop.getFluidContainer = lambda s, fc=make_fluid(water=False, cats={"Beverage"}, thirst=-0.3): fc
    bottle = make_item("Base.WaterBottle", 2)
    assert _uses(lua, pop, bottle) == {1: "other", 2: "water"}


# ---- PZA/1.5 (ruling P24-G): body.parts' bleeding, bleedingTime, bandaged, bandageLife, bandageDirty, deep, infected --

def _part(h=100.0, bleeding=False, time=0.0, bandaged=False, life=0.0, deep=False, infected=False, calls=None):
    def rec(name, v):
        def f(s):
            if calls is not None:
                calls.append(name)
            return v
        return f
    return J(getHealth=rec("getHealth", h), bleeding=rec("bleeding", bleeding), getBleedingTime=rec("time", time),
             bandaged=rec("bandaged", bandaged), getBandageLife=rec("life", life),
             isBandageDirty=rec("dirty", life <= 0), deepWounded=rec("deep", deep),
             isInfectedWound=rec("infected", infected))


def _with_parts(p, parts, bleeding):
    bd = p.getBodyDamage(p)
    bd.getBodyParts = lambda s: J(size=lambda s2: len(parts), get=lambda s2, i: parts[i])
    bd.getNumPartsBleeding = lambda s: bleeding


def test_a_part_is_listed_hurt_bandaged_or_bleeding_with_its_care_fields(lua):
    load(lua)
    p = make_player()
    _with_parts(p, [_part(), _part(h=60.0, deep=True, infected=True), _part(bandaged=True, life=0.0, time=4.5),
                    _part(bleeding=True, time=9.0), _part(h=80.0, bandaged=True, life=3.25, time=1.0)], bleeding=1)
    parts = [dict(x) for x in frame(lua, p)["body"]["parts"].values()]
    assert parts == [
        {"i": 1, "h": 60.0, "bleeding": False, "bleedingTime": 0.0, "bandaged": False, "deep": True, "infected": True},
        {"i": 2, "h": 100.0, "bleeding": False, "bleedingTime": 4.5, "bandaged": True, "bandageLife": 0.0,
         "bandageDirty": True, "deep": False, "infected": False},
        {"i": 3, "h": 100.0, "bleeding": True, "bleedingTime": 9.0, "bandaged": False, "deep": False, "infected": False},
        {"i": 4, "h": 80.0, "bleeding": False, "bleedingTime": 1.0, "bandaged": True, "bandageLife": 3.25,
         "bandageDirty": False, "deep": False, "infected": False}]
    assert missing(lua) == []


def test_no_part_reads_bleeding_while_the_body_counts_none_bleeding(lua):
    load(lua)
    calls = []
    p = make_player()
    _with_parts(p, [_part(calls=calls), _part(h=50.0, calls=calls)], bleeding=0)
    f = frame(lua, p)
    assert "bleeding" not in calls and calls.count("bandaged") == 2
    assert [dict(x)["bleeding"] for x in f["body"]["parts"].values()] == [False]
    enc = json.loads(lua.eval("PZA.enc.body(...)", f["body"]))
    assert enc[4] == [[1, 50, False, 0, False, None, None, False, False]]


def test_an_absent_part_member_leaves_its_field_nil_and_is_named(lua):
    load(lua)
    p = make_player()
    part = _part(h=40.0)
    part.bandaged, part.isInfectedWound = None, None
    _with_parts(p, [part], bleeding=1)
    r = dict(frame(lua, p)["body"]["parts"][1])
    assert r["i"] == 0 and "bandaged" not in r and "infected" not in r and r["deep"] is False
    assert {"bandaged", "isInfectedWound"} <= set(missing(lua))


# ---- PZA/1.5.1 (Task 9 fix 1): a sealed can, the bandage use, the absent bleeding() named ------------------------------

def test_a_sealed_pop_can_reads_other_and_its_opened_twin_water(lua):
    """Review minor 2: vanilla's drink menu refuses a container whose canPlayerEmpty() is false (a pop can spawned
    sealed, tagged base:sealedbeveragecan); an absent canPlayerEmpty reads sealed (fails closed)."""
    load(lua)
    from .conftest import make_item, make_fluid
    cola = dict(water=False, cats={"Beverage"}, thirst=-30.0, fluid="Cola", capacity=0.3)
    sealed = make_item("Base.Pop2", 1)
    sealed.getFluidContainer = lambda s, fc=make_fluid(sealed=True, **cola): fc
    opened = make_item("Base.Pop2", 2)
    opened.getFluidContainer = lambda s, fc=make_fluid(**cola): fc
    unread = make_item("Base.WaterBottle", 3)
    unread.getFluidContainer = lambda s, fc=make_fluid(sealed=None): fc
    assert _uses(lua, sealed, opened, unread) == {1: "other", 2: "water", 3: "other"}
    assert lua.eval("PZA.world.drinkable(...)", sealed, sealed.getFluidContainer(sealed)) is False


def test_the_bandage_use_is_is_can_bandage_and_never_the_name(lua):
    """Review minor 5: the rags rip makes and wash cleans (RippedSheets, RippedSheetsDirty) read bandage by the script's
    CanBandage; a Rag (no CanBandage) and an item without the member read other."""
    load(lua)
    from .conftest import J
    def it(ft, iid, can):
        o = J(getFullType=lambda s: ft, getID=lambda s: iid, getWeight=lambda s: 0.1, getFluidContainer=lambda s: None)
        if can is not None:
            o.isCanBandage = lambda s: can
        return o
    assert _uses(lua, it("Base.RippedSheetsDirty", 1, True), it("Base.Rag", 2, False),
                 it("Base.Bandage", 3, None), it("Base.DenimStrips", 4, True)) == {
        1: "bandage", 2: "other", 3: "other", 4: "bandage"}


def test_an_absent_bleeding_member_is_named_in_missing(lua):
    """Review minor 6: a part without bleeding() leaves its field nil and is named, as its docstring says."""
    load(lua)
    p = make_player()
    part = _part(h=40.0)
    part.bleeding = None
    _with_parts(p, [part], bleeding=1)
    r = dict(frame(lua, p)["body"]["parts"][1])
    assert "bleeding" not in r and "bleeding" in missing(lua)


# ---- PZA/1.5.4 (Plan 24 Task 9 fix 6, ruling P24-T): me.forceAim beside aiming -----------------------------------------

def test_the_frames_me_carries_force_aim_from_is_force_aim_appended_after_aiming(lua):
    load(lua)
    p = make_player()
    p.aim["aiming"] = True                                            # the swing's own aiming, no force-aim
    f = frame(lua, p)
    assert f["me"]["forceAim"] is False and f["me"]["aiming"] is True
    p.aim["force"], p.aim["aiming"] = True, None
    f = frame(lua, p)
    assert f["me"]["forceAim"] is True and f["me"]["aiming"] is True
    order = lua.eval("PZA.schema.groups.me")
    assert order[18] == "aiming" and order[19] == "forceAim"
    assert json.loads(lua.eval("PZA.enc.me(...)", f["me"]))[18] is True
    q = make_player()
    q.isForceAim = None
    f = frame(lua, q)
    assert f["me"]["forceAim"] is None and f["me"]["aiming"] is False and "isForceAim" in missing(lua)
