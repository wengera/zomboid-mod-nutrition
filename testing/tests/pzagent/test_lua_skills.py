"""PZAgent_Skills.lua (Plan 22 Task 3): the skill runner PZA.skills (K.start, K.tick, typed act lines through
PZA.emit) and the three movement skills walkTo, steer and stop, each one bounded engine action with a typed result;
the Motor's latches wanted at a skill's start and cleared at every end. Task 4: the skills attack, interact, equip,
consume and drop (ported from Plan 21's PZAgent_Act.lua goals), the runner's guard on a skill's raise (S-12), and every
reason and result key in the schema."""
import json
import math
import os
import re

import pytest

from agent.base import pza1
from .conftest import ROOT, FakeFS, J, lua_file, make_cell, make_lua, make_player, make_weapon, make_zombie

LIVE = "pzagent/admin/state.log"
R2 = 1 / math.sqrt(2)


def load(lua):
    for f in ("shared/PZAgent_World.lua", "client/PZAgent_Link.lua", "client/PZAgent_Motor.lua",
              "client/PZAgent_Skills.lua", "client/PZAgent_SkillsWorld.lua"):
        lua.execute(open(lua_file(f), encoding="utf-8").read())
    lua.globals().PZA.tick = 0
    lua.execute("PZA.link.init('admin')")


def acts(lua, fs):
    """Every act line written so far, read back from the file and decoded through pza1."""
    lua.execute("PZA.link.flush()")
    out = []
    for l in fs.files.get(LIVE, "").split("\n"):
        if not l.strip():
            continue
        obj = json.loads(l)
        if isinstance(obj, dict) and obj.get("kind") == "act":
            out.append(pza1.decode(obj))
    return out


def start(lua, p, typ, aid="a1", **args):
    cmd = lua.table_from({"seq": 1, "aid": aid, "type": typ, "args": args}, recursive=True)
    lua.eval("PZA.skills.start")(cmd, p)


def tick(lua, p, n=1):
    for _ in range(n):
        lua.eval("PZA.skills.tick")(p)


def mover(p, x, y):
    """p's position read from a dict the test moves."""
    pos = {"x": x, "y": y}
    p.getX, p.getY = (lambda s: pos["x"]), (lambda s: pos["y"])
    return pos


def walk_world(lua, x=12, y=20):
    lua.globals()._cell = make_cell(squares={(x, y, 0): "target"})


def states(lines):
    return [(a["aid"], a["state"], a["reason"]) for a in lines]


# ---- the runner ------------------------------------------------------------------------------------------------------

def test_an_unknown_type_is_rejected(lua, fs):
    load(lua)
    start(lua, make_player(), "fly")
    a = acts(lua, fs)
    assert states(a) == [("a1", "rejected", "unknown type")]
    assert a[0]["result"] == {} and a[0]["snapshot"]["me"]["x"] == 10.0
    assert lua.eval("PZA.skills.cur") is None


def test_an_empty_aid_is_rejected_bad_args(lua, fs):
    load(lua)
    start(lua, make_player(), "stop", aid="")
    assert states(acts(lua, fs)) == [("", "rejected", "bad args")]


@pytest.mark.parametrize("args", [{"y": 3}, {"x": "a", "y": 3}, {"x": 1, "y": 2, "gait": "crawl"}])
def test_walk_to_with_bad_args_is_rejected(lua, fs, args):
    load(lua)
    start(lua, make_player(), "walkTo", **args)
    assert states(acts(lua, fs)) == [("a1", "rejected", "bad args")]


def test_a_dead_player_is_rejected_dead_for_walk_to_but_stop_is_accepted(lua, fs):
    load(lua)
    p = make_player(health=0.0)
    walk_world(lua)
    start(lua, p, "walkTo", aid="w", x=12, y=20)
    start(lua, p, "stop", aid="s")
    tick(lua, p)
    assert states(acts(lua, fs)) == [("w", "rejected", "dead"), ("s", "accepted", ""), ("s", "done", "")]


def test_accepted_and_progress_carry_an_empty_result_and_no_snapshot(lua, fs):
    load(lua)
    p = make_player()
    walk_world(lua, 30, 20)
    start(lua, p, "walkTo", x=30, y=20)
    tick(lua, p)
    lua.globals()._clock["ms"] += 1000
    tick(lua, p)
    a = acts(lua, fs)
    assert [x["state"] for x in a] == ["accepted", "progress"]
    for x in a:
        assert x["result"] == {} and "snapshot" not in x and x["reason"] == "" and x["type"] == "walkTo"


def test_progress_is_emitted_at_most_once_a_second(lua, fs):
    load(lua)
    p = make_player()
    walk_world(lua, 30, 20)
    start(lua, p, "walkTo", x=30, y=20)
    tick(lua, p, 10)
    assert [x["state"] for x in acts(lua, fs)] == ["accepted"]
    lua.globals()._clock["ms"] += 999
    tick(lua, p)
    assert [x["state"] for x in acts(lua, fs)] == ["accepted"]
    lua.globals()._clock["ms"] += 1
    tick(lua, p, 5)
    assert [x["state"] for x in acts(lua, fs)] == ["accepted", "progress"]
    lua.globals()._clock["ms"] += 1000
    tick(lua, p)
    assert [x["state"] for x in acts(lua, fs)] == ["accepted", "progress", "progress"]


def test_a_second_command_supersedes_the_first(lua, fs):
    load(lua)
    p = make_player()
    walk_world(lua, 30, 20)
    start(lua, p, "walkTo", aid="w1", x=30, y=20, gait="run")
    tick(lua, p)
    cleared = lua.globals()._queue.cleared
    start(lua, p, "walkTo", aid="w2", x=30, y=20)
    a = acts(lua, fs)
    assert states(a) == [("w1", "accepted", ""), ("w1", "failed", "superseded"), ("w2", "accepted", "")]
    assert a[1]["snapshot"]["me"]["health"] == 100.0
    assert lua.globals()._queue.cleared == cleared + 1 and lua.eval("PZA.motor.wantRun") is False
    assert lua.eval("PZA.skills.cur.aid") == "w2"


def test_a_rejected_command_leaves_the_running_skill_alone(lua, fs):
    load(lua)
    p = make_player()
    walk_world(lua, 30, 20)
    start(lua, p, "walkTo", aid="w1", x=30, y=20)
    start(lua, p, "fly", aid="f")
    assert states(acts(lua, fs)) == [("w1", "accepted", ""), ("f", "rejected", "unknown type")]
    assert lua.eval("PZA.skills.cur.aid") == "w1"


def test_status_names_the_running_skill_and_nil_when_idle(lua, fs):
    load(lua)
    p = make_player()
    assert lua.eval("PZA.skills.status()") is None
    walk_world(lua, 30, 20)
    start(lua, p, "walkTo", aid="w1", x=30, y=20)
    s = lua.eval("PZA.skills.status()")
    assert s.aid == "w1" and s.state == "accepted"
    lua.globals()._clock["ms"] += 1000
    tick(lua, p)
    assert lua.eval("PZA.skills.status()").state == "progress"
    start(lua, p, "stop", aid="s")
    tick(lua, p)
    assert lua.eval("PZA.skills.status()") is None


def test_the_done_snapshot_carries_health_and_no_nearest_without_sense(lua, fs):
    load(lua)
    p = make_player(health=73.5)
    start(lua, p, "stop")
    tick(lua, p)
    done = acts(lua, fs)[-1]
    assert done["state"] == "done" and done["result"] == {}
    assert done["snapshot"]["me"] == {"x": 10.0, "y": 20.0, "z": 0, "health": 73.5}
    assert done["snapshot"].get("nearest") is None


def test_the_snapshot_reads_the_nearest_zombie_through_sense_when_loaded(lua, fs):
    load(lua)
    lua.execute("PZA.sense = { nearestZombie = function(p) return { id = 7, dist = 2.5 } end }")
    p = make_player()
    start(lua, p, "stop")
    tick(lua, p)
    assert acts(lua, fs)[-1]["snapshot"]["nearest"] == {"id": 7, "dist": 2.5}


# ---- walkTo ----------------------------------------------------------------------------------------------------------

def test_walk_to_with_no_square_fails_no_square(lua, fs):
    load(lua)
    p = make_player()
    start(lua, p, "walkTo", x=99, y=99)
    tick(lua, p)
    assert states(acts(lua, fs)) == [("a1", "accepted", ""), ("a1", "failed", "no square")]
    assert lua.globals()._queue.cleared >= 1 and lua.eval("PZA.skills.cur") is None


def test_walk_to_with_no_vanilla_walk_class_fails_no_path_without_a_raise(lua, fs):
    load(lua)
    walk_world(lua)
    lua.globals().ISWalkToTimedAction = None
    p = make_player()
    start(lua, p, "walkTo", x=12, y=20)
    tick(lua, p)
    assert states(acts(lua, fs))[-1] == ("a1", "failed", "no path")


def test_walk_to_is_done_within_a_tile_with_d_and_the_queue_cleared(lua, fs):
    load(lua)
    walk_world(lua)
    p = make_player()
    pos = mover(p, 10.0, 20.0)
    start(lua, p, "walkTo", x=12, y=20)
    tick(lua, p)
    q = lua.globals()._queue
    assert len(q.adds) == 1 and q.adds[0].sq == "target"
    pos["x"] = 11.5
    tick(lua, p)
    a = acts(lua, fs)
    assert states(a)[-1] == ("a1", "done", "") and a[-1]["result"] == {"d": 0.5}
    assert q.queue == [] and q.cleared >= 1 and a[-1]["type"] == "walkTo"


def test_walk_to_stuck_replans_three_times_then_fails_stuck(lua, fs):
    load(lua)
    walk_world(lua, 30, 20)
    p = make_player()
    q = lua.globals()._queue
    start(lua, p, "walkTo", x=30, y=20)
    tick(lua, p, 1 + 90 * 4 - 1)
    assert lua.eval("PZA.skills.cur") is not None and len(q.adds) == 4
    tick(lua, p)
    assert states(acts(lua, fs))[-1] == ("a1", "failed", "stuck")
    assert len(q.adds) == 4 and q.queue == []


def test_a_moving_player_is_never_stuck(lua, fs):
    load(lua)
    walk_world(lua, 300, 20)
    p = make_player()
    pos = mover(p, 10.0, 20.0)
    start(lua, p, "walkTo", x=300, y=20)
    for _ in range(200):
        pos["x"] += 0.05
        tick(lua, p)
    assert lua.eval("PZA.skills.cur") is not None and len(lua.globals()._queue.adds) == 1


@pytest.mark.parametrize("end", ["done", "no square", "superseded", "stop"])
def test_walk_to_run_wants_the_run_at_its_start_and_is_off_at_every_end(lua, fs, end):
    load(lua)
    walk_world(lua)
    p = make_player()
    pos = mover(p, 10.0, 20.0)
    tx = 99 if end == "no square" else 12
    start(lua, p, "walkTo", x=tx, y=20, gait="run")
    if end != "no square":
        tick(lua, p)
        assert lua.eval("PZA.motor.wantRun") is True and lua.eval("PZA.motor.wantSprint") is False
    del p.sets[:]
    if end == "done":
        pos["x"] = 12.0
        tick(lua, p)
    elif end == "no square":
        tick(lua, p)
    elif end == "superseded":
        start(lua, p, "walkTo", aid="a2", x=12, y=20)
    else:
        start(lua, p, "stop", aid="s")
        tick(lua, p)
    assert lua.eval("PZA.motor.wantRun") is False
    assert ("setForceRun", False) in p.sets and ("setForceSprint", False) in p.sets
    assert ("setAutoWalk", False) in p.sets


def test_walk_to_sprint_wants_both(lua, fs):
    load(lua)
    walk_world(lua, 30, 20)
    p = make_player()
    start(lua, p, "walkTo", x=30, y=20, gait="sprint")
    tick(lua, p)
    assert lua.eval("PZA.motor.wantRun") is True and lua.eval("PZA.motor.wantSprint") is True


# ---- steer -----------------------------------------------------------------------------------------------------------

def direction(p):
    return [v for n, v in p.sets if n == "setAutoWalkDirection"]


@pytest.mark.parametrize("vx,vy,ix,iy", [(1, 0, R2, R2), (0, 1, -R2, R2), (2, 0, 2 * R2, 2 * R2)])
def test_steer_rotates_the_world_vector_into_input_space(lua, fs, vx, vy, ix, iy):
    load(lua)
    p = make_player()
    start(lua, p, "steer", vx=vx, vy=vy, seconds=3)
    tick(lua, p)
    assert [n for n, v in p.sets].count("setAutoWalk") == 1 and ("setAutoWalk", True) in p.sets
    d = direction(p)
    assert len(d) == 1 and d[0]._cls == "Vector2"
    assert round(d[0].x, 6) == round(ix, 6) and round(d[0].y, 6) == round(iy, 6)


def test_input_vector_of_zero_is_zero(lua):
    load(lua)
    assert tuple(lua.eval("{PZA.skills.inputVector(0, 0)}").values()) == (0, 0)


def test_steer_is_done_after_its_seconds_with_d_and_auto_walk_off(lua, fs):
    load(lua)
    p = make_player()
    pos = mover(p, 10.0, 20.0)
    start(lua, p, "steer", vx=1, vy=0, seconds=3, gait="run")
    tick(lua, p)
    assert lua.eval("PZA.motor.wantRun") is True
    pos["x"], pos["y"] = 13.0, 24.0
    lua.globals()._clock["ms"] += 2999
    tick(lua, p)
    assert lua.eval("PZA.skills.cur") is not None
    lua.globals()._clock["ms"] += 1
    tick(lua, p)
    a = acts(lua, fs)
    assert states(a)[-1] == ("a1", "done", "") and a[-1]["result"] == {"d": 5}
    assert p.sets[-1] == ("setAutoWalk", False) and lua.eval("PZA.motor.wantRun") is False


def test_steer_without_vector2_fails_not_loaded(lua, fs):
    load(lua)
    lua.globals().Vector2 = None
    p = make_player()
    start(lua, p, "steer", vx=1, vy=0, seconds=3)
    tick(lua, p)
    assert states(acts(lua, fs))[-1] == ("a1", "failed", "not loaded")
    assert ("setAutoWalk", True) not in p.sets


@pytest.mark.parametrize("args", [{"vx": 1, "vy": 0}, {"vx": 1, "vy": 0, "seconds": 0}, {"vy": 0, "seconds": 2}])
def test_steer_with_bad_args_is_rejected(lua, fs, args):
    load(lua)
    start(lua, make_player(), "steer", **args)
    assert states(acts(lua, fs)) == [("a1", "rejected", "bad args")]


# ---- stop ------------------------------------------------------------------------------------------------------------

def test_stop_clears_the_queue_and_the_motor_and_is_done_empty(lua, fs):
    load(lua)
    p = make_player()
    q = lua.globals()._queue
    q.queue.append("vanilla")
    lua.execute("PZA.motor.want('sprint')")
    start(lua, p, "stop")
    tick(lua, p)
    a = acts(lua, fs)
    assert states(a) == [("a1", "accepted", ""), ("a1", "done", "")] and a[-1]["result"] == {}
    assert q.queue == [] and lua.eval("PZA.motor.wantSprint") is False and lua.eval("PZA.skills.cur") is None


# ---- every line in the schema's enums; the banned setters ------------------------------------------------------------

def test_every_emitted_reason_and_type_is_in_the_schema(lua, fs):
    load(lua)
    walk_world(lua)
    p = make_player()
    start(lua, p, "walkTo", aid="", x=1, y=1)
    start(lua, p, "walkTo", x=1)
    start(lua, p, "walkTo", x=99, y=99)
    tick(lua, p)
    start(lua, p, "walkTo", aid="w", x=12, y=20)
    tick(lua, p)
    lua.globals()._clock["ms"] += 1000
    tick(lua, p)
    start(lua, p, "steer", aid="s", vx=1, vy=1, seconds=1)
    tick(lua, p)
    lua.globals()._clock["ms"] += 1000
    tick(lua, p)
    start(lua, p, "stop", aid="t")
    tick(lua, p)
    p2 = make_player(health=0.0)
    start(lua, p2, "steer", aid="d", vx=1, vy=0, seconds=1)
    a = acts(lua, fs)
    assert len(a) >= 12
    reasons, actions = lua.eval("PZA.schema.reasons"), lua.eval("PZA.schema.actions")
    st = lua.eval("PZA.schema.states")
    for x in a:
        assert x["reason"] == "" or reasons[x["reason"]] is True, x
        assert actions[x["type"]] is not None and st[x["state"]] is True, x
        assert (x["reason"] != "") == (x["state"] in ("rejected", "failed")), x
        assert x["result"] == {} or x["state"] == "done", x
        assert ("snapshot" in x) == (x["state"] in ("rejected", "failed", "done")), x


def test_no_client_file_names_the_banned_setters():
    client = lua_file("client")
    files = sorted(f for f in os.listdir(client) if f.endswith(".lua"))
    assert "PZAgent_Motor.lua" in files and "PZAgent_Skills.lua" in files and "PZAgent_Act.lua" not in files
    for f in files:
        src = open(os.path.join(client, f), encoding="utf-8").read()
        for name in ("setRunning", "setSprinting", "setPathfindRunning", "setToggleToRun"):
            assert re.search(name, src) is None, (f, name)


# ==== Plan 22 Task 4: attack, interact, equip, consume, drop; the runner's raise guard (S-12) ===========================

SCHEMA = os.path.join(ROOT, "testing", "agent", "base", "schema", "pza1.json")
OFF = [("setForceRun", False), ("setForceSprint", False), ("setAutoWalk", False)]


def sense(lua, zombies=()):
    """PZA.sense stubbed with zombieById (by online id) and nearestZombie (always nil) until Task 5 provides them."""
    byid = {z.getOnlineID(z): z for z in zombies}
    lua.globals()._zbyid = lambda i: byid.get(int(i))
    lua.execute("PZA.sense = { zombieById = function(p, id) return _zbyid(id) end,"
                " nearestZombie = function(p) return nil end }")


def jlist(items):
    return J(size=lambda s: len(items), get=lambda s, i: items[i])


def osq(x, y, objects=(), solid=False, solid_trans=False):
    objs = list(objects)
    return J(getX=lambda s: x, getY=lambda s: y, getZ=lambda s: 0, isSolid=lambda s: solid,
             isSolidTrans=lambda s: solid_trans, getObjects=lambda s: jlist(objs))


def make_door(opened=False, cls="IsoDoor", barricaded=False):
    st = {"open": opened}
    d = J(_cls=cls, IsOpen=lambda s: st["open"], isBarricaded=lambda s: barricaded)
    d.st = st
    return d


def citem(ft, cls=None):
    return J(_cls=cls, getFullType=lambda s: ft, getFluidContainer=lambda s: None)


def make_box(items, loaded=True):
    c = J(getType=lambda s: "crate")
    if loaded:
        c.getItems = lambda s: jlist(items)
    return c


def box_world(lua, contents, loaded=True):
    box = make_box(contents, loaded)
    obj = J(_cls="IsoObject", getContainerCount=lambda s: 1, getContainerByIndex=lambda s, i: box)
    lua.globals()._cell = make_cell(squares={(11, 20, 0): osq(11, 20, [obj])})
    return box


def ended(lua):
    return lua.eval("PZA.skills.cur") is None


# ---- attack ----------------------------------------------------------------------------------------------------------

def attack_world(lua, zx=11.0, zy=20.0, weapon=True):
    z = make_zombie(7, zx, zy)
    sense(lua, [z])
    lua.globals()._cell = make_cell(zombies=[z], squares={(int(zx), int(zy), 0): "zsq"})
    p = make_player(weapon=make_weapon() if weapon else None)
    return z, p


def test_attack_on_an_unknown_id_is_rejected_no_target(lua, fs):
    load(lua)
    attack_world(lua)
    start(lua, make_player(weapon=make_weapon()), "attack", targetId=99)
    assert states(acts(lua, fs)) == [("a1", "rejected", "no target")]


def test_attack_on_a_dead_or_far_zombie_is_rejected_no_target(lua, fs):
    load(lua)
    dead, far = make_zombie(1, 11.0, 20.0, dead=True), make_zombie(2, 16.5, 20.0)
    sense(lua, [dead, far])
    p = make_player(weapon=make_weapon())
    start(lua, p, "attack", aid="d", targetId=1)
    start(lua, p, "attack", aid="f", targetId=2)
    assert states(acts(lua, fs)) == [("d", "rejected", "no target"), ("f", "rejected", "no target")]


def test_attack_without_sense_is_rejected_no_target_without_a_raise(lua, fs):
    load(lua)
    start(lua, make_player(weapon=make_weapon()), "attack", targetId=7)
    assert states(acts(lua, fs)) == [("a1", "rejected", "no target")] and lua.eval("PZA.skills.errors") == 0


def test_attack_without_a_weapon_is_rejected_no_weapon(lua, fs):
    load(lua)
    _, p = attack_world(lua, weapon=False)
    start(lua, p, "attack", targetId=7)
    assert states(acts(lua, fs)) == [("a1", "rejected", "no weapon")]


def test_attack_with_bad_args_is_rejected(lua, fs):
    load(lua)
    _, p = attack_world(lua)
    start(lua, p, "attack", targetId="7")
    assert states(acts(lua, fs)) == [("a1", "rejected", "bad args")]


def test_reach_is_the_weapons_max_range_times_range_mod_times_the_margin(lua):
    load(lua)
    p = make_player()
    reach = lambda w: lua.eval("PZA.skills.reachOf")(p, w)
    assert reach(make_weapon(1.25, 1.0)) == pytest.approx(1.125)
    assert reach(make_weapon(1.25, 1.2)) == pytest.approx(1.35)
    assert reach(make_weapon(1.25, None)) == pytest.approx(1.125)    # getRangeMod absent: the fallback 1.25
    assert reach(make_weapon(None, 1.2)) == pytest.approx(1.125)     # getMaxRange absent: the fallback
    assert reach(make_weapon(2.0, None)) == pytest.approx(1.125)


def test_attack_beyond_reach_queues_one_approach_walk_at_a_run_and_swings_once_inside(lua, fs):
    load(lua)
    z, p = attack_world(lua, zx=13.0)
    pos = mover(p, 10.0, 20.0)
    q = lua.globals()._queue
    start(lua, p, "attack", targetId=7)
    tick(lua, p)
    assert [a.Type for a in q.adds] == ["ISWalkToTimedAction"] and q.adds[0].sq == "zsq"
    assert lua.eval("PZA.motor.wantRun") is True and list(p.attacks) == []
    tick(lua, p, 3)
    assert len(q.adds) == 1 and list(p.attacks) == []               # one walk, never re-queued
    pos["x"] = 12.0                                                 # 1.0 tiles off: inside the reach 1.125
    tick(lua, p)
    assert list(p.attacks) == [0] and list(p.faced) == [z] and len(q.adds) == 1
    assert q.queue == [] and lua.eval("PZA.motor.wantRun") is False
    tick(lua, p, 5)
    assert list(p.attacks) == [0]                                   # one swing only


def test_attack_out_of_reach_after_the_approach_budget(lua, fs):
    load(lua)
    _, p = attack_world(lua, zx=13.0)
    start(lua, p, "attack", targetId=7)
    tick(lua, p)
    lua.globals()._clock["ms"] += 3999
    tick(lua, p)
    assert not ended(lua)
    lua.globals()._clock["ms"] += 1
    tick(lua, p)
    assert states(acts(lua, fs))[-1] == ("a1", "failed", "out of reach")
    assert list(p.attacks) == [] and lua.globals()._queue.queue == []


def test_attack_whose_approach_walk_cannot_queue_fails_on_that_tick_with_the_walks_reason(lua, fs):
    """Fix wave M5: a sub-walk failing on its first tick ends the attack at once, never burning APPROACH_MS."""
    load(lua)
    _, p = attack_world(lua, zx=13.0)
    lua.globals().ISWalkToTimedAction = None
    start(lua, p, "attack", targetId=7)
    tick(lua, p)
    assert states(acts(lua, fs))[-1] == ("a1", "failed", "no path") and ended(lua)
    assert list(p.attacks) == [] and lua.globals()._queue.queue == []


def test_attack_whose_approach_square_is_absent_fails_on_that_tick_with_no_square(lua, fs):
    load(lua)
    z = make_zombie(7, 13.0, 20.0)
    sense(lua, [z])
    lua.globals()._cell = make_cell(zombies=[z])
    p = make_player(weapon=make_weapon())
    start(lua, p, "attack", targetId=7)
    tick(lua, p)
    assert states(acts(lua, fs))[-1] == ("a1", "failed", "no square") and ended(lua)


def test_attack_started_true_then_false_is_done_with_the_largest_melee_delay(lua, fs):
    load(lua)
    _, p = attack_world(lua)
    start(lua, p, "attack", targetId=7)
    tick(lua, p)
    assert list(p.attacks) == [0]
    for started, delay in ((True, 0.4), (True, 0.6), (True, 0.5)):
        p.attack["started"], p.attack["delay"] = started, delay
        tick(lua, p)
        assert not ended(lua)
    p.attack["started"], p.attack["delay"] = False, 0.2
    tick(lua, p)
    a = acts(lua, fs)
    assert states(a)[-1] == ("a1", "done", "")
    assert a[-1]["result"] == {"swings": 1, "attackStarted": True, "meleeDelay": 0.6, "targetDead": False}


def test_attack_that_never_starts_is_done_after_the_swing_window(lua, fs):
    load(lua)
    _, p = attack_world(lua)
    start(lua, p, "attack", targetId=7)
    tick(lua, p)
    lua.globals()._clock["ms"] += 1499
    tick(lua, p)
    assert not ended(lua)
    lua.globals()._clock["ms"] += 1
    tick(lua, p)
    a = acts(lua, fs)
    assert states(a)[-1] == ("a1", "done", "")
    assert a[-1]["result"] == {"swings": 1, "attackStarted": False, "meleeDelay": 0, "targetDead": False}


def test_a_target_that_dies_ends_the_attack_done_with_target_dead(lua, fs):
    load(lua)
    z, p = attack_world(lua)
    start(lua, p, "attack", targetId=7)
    tick(lua, p)
    z.isDead = lambda s: True
    tick(lua, p)
    a = acts(lua, fs)
    assert states(a)[-1] == ("a1", "done", "") and a[-1]["result"]["targetDead"] is True
    assert a[-1]["result"]["swings"] == 1


def test_a_target_that_dies_during_the_approach_is_done_with_no_swings(lua, fs):
    load(lua)
    z, p = attack_world(lua, zx=13.0)
    start(lua, p, "attack", targetId=7)
    tick(lua, p)
    z.isDead = lambda s: True
    tick(lua, p)
    a = acts(lua, fs)
    assert states(a)[-1] == ("a1", "done", "")
    assert a[-1]["result"]["swings"] == 0 and a[-1]["result"]["targetDead"] is True and list(p.attacks) == []


def test_attack_with_do_attack_absent_never_calls_it_and_the_swing_reads_still_land(lua, fs):
    load(lua)
    _, p = attack_world(lua)
    p.DoAttack = None
    start(lua, p, "attack", targetId=7)
    tick(lua, p)
    p.attack["started"], p.attack["delay"] = True, 0.3
    tick(lua, p)
    p.attack["started"] = False
    tick(lua, p)
    a = acts(lua, fs)
    assert states(a)[-1] == ("a1", "done", "") and lua.eval("PZA.skills.errors") == 0
    assert a[-1]["result"] == {"swings": 0, "attackStarted": True, "meleeDelay": 0.3, "targetDead": False}


def test_attack_fails_no_weapon_when_the_weapon_leaves_the_hand_before_the_swing(lua, fs):
    load(lua)
    _, p = attack_world(lua, zx=13.0)
    start(lua, p, "attack", targetId=7)
    tick(lua, p)
    p.getPrimaryHandItem = lambda s: None
    tick(lua, p)
    assert states(acts(lua, fs))[-1] == ("a1", "failed", "no weapon")


# ---- interact --------------------------------------------------------------------------------------------------------

def test_interact_open_walks_adjacent_first_then_queues_the_door_open(lua, fs):
    load(lua)
    g = lua.globals()
    door = make_door()
    g._cell = make_cell(squares={(13, 20, 0): osq(13, 20, [door]), (12, 20, 0): osq(12, 20),
                                 (12, 19, 0): osq(12, 19, solid=True), (12, 21, 0): osq(12, 21, solid_trans=True)})
    p = make_player()
    pos = mover(p, 10.0, 20.0)
    start(lua, p, "interact", x=13, y=20, kind="open")
    tick(lua, p)
    assert [a.Type for a in g._queue.adds] == ["ISWalkToTimedAction"]
    assert g._queue.adds[0].sq.getX(g._queue.adds[0].sq) == 12 and g._queue.adds[0].sq.getY(g._queue.adds[0].sq) == 20
    assert lua.eval("PZA.motor.wantRun") is False                   # interact's sub-walk is a walk
    pos["x"] = 12.2
    tick(lua, p)
    assert [a.Type for a in g._queue.adds] == ["ISWalkToTimedAction", "ISOpenCloseDoor"]
    assert g._queue.adds[1].item is door and g._queue.adds[1].character is p and not ended(lua)
    door.st["open"] = True
    tick(lua, p)
    a = acts(lua, fs)
    assert states(a)[-1] == ("a1", "done", "") and a[-1]["result"] == {"open": True}


def test_interact_open_of_a_door_that_stays_shut_fails_locked_after_five_seconds(lua, fs):
    load(lua)
    g = lua.globals()
    g._cell = make_cell(squares={(11, 20, 0): osq(11, 20, [make_door()])})
    p = make_player()
    start(lua, p, "interact", x=11, y=20, kind="open")
    tick(lua, p)
    assert [a.Type for a in g._queue.adds] == ["ISOpenCloseDoor"]
    g._clock["ms"] += 5000
    tick(lua, p)
    assert not ended(lua)
    g._clock["ms"] += 1
    tick(lua, p)
    assert states(acts(lua, fs))[-1] == ("a1", "failed", "locked")


def test_interact_open_of_an_open_door_is_done_at_once(lua, fs):
    load(lua)
    g = lua.globals()
    g._cell = make_cell(squares={(13, 20, 0): osq(13, 20, [make_door(opened=True)])})
    p = make_player()
    start(lua, p, "interact", x=13, y=20, kind="open")
    tick(lua, p)
    a = acts(lua, fs)
    assert states(a)[-1] == ("a1", "done", "") and a[-1]["result"] == {"open": True} and g._queue.adds == []


def test_interact_close_queues_the_toggle_and_is_done_once_shut(lua, fs):
    load(lua)
    g = lua.globals()
    door = make_door(opened=True)
    g._cell = make_cell(squares={(11, 20, 0): osq(11, 20, [door])})
    p = make_player()
    start(lua, p, "interact", x=11, y=20, kind="close")
    tick(lua, p)
    assert [a.Type for a in g._queue.adds] == ["ISOpenCloseDoor"]
    door.st["open"] = False
    tick(lua, p)
    a = acts(lua, fs)
    assert states(a)[-1] == ("a1", "done", "") and a[-1]["result"] == {"open": False}


def test_interact_open_failures(lua, fs):
    load(lua)
    g = lua.globals()
    p = make_player()
    start(lua, p, "interact", aid="b1", x=13, y=20, kind="smash")
    start(lua, p, "interact", aid="b2", x="13", y=20, kind="open")
    g._cell = make_cell(squares={})
    start(lua, p, "interact", aid="sq", x=13, y=20, kind="open")
    tick(lua, p)
    g._cell = make_cell(squares={(13, 20, 0): osq(13, 20, [J(_cls="IsoObject")])})
    start(lua, p, "interact", aid="nd", x=13, y=20, kind="open")
    tick(lua, p)
    g._cell = make_cell(squares={(13, 20, 0): osq(13, 20, [make_door(barricaded=True)]), (12, 20, 0): osq(12, 20)})
    start(lua, p, "interact", aid="bar", x=13, y=20, kind="open")
    tick(lua, p)
    g._cell = make_cell(squares={(13, 20, 0): osq(13, 20, [make_door()]), (12, 20, 0): osq(12, 20, solid=True)})
    start(lua, p, "interact", aid="adj", x=13, y=20, kind="open")
    tick(lua, p)
    g._cell = make_cell(squares={(11, 20, 0): osq(11, 20, [make_door()])})
    g.ISOpenCloseDoor = J()
    start(lua, p, "interact", aid="nl", x=11, y=20, kind="open")
    tick(lua, p)
    assert [s for s in states(acts(lua, fs)) if s[1] != "accepted"] == [
        ("b1", "rejected", "bad args"), ("b2", "rejected", "bad args"), ("sq", "failed", "no square"),
        ("nd", "failed", "no door"), ("bar", "failed", "locked"), ("adj", "failed", "not adjacent"),
        ("nl", "failed", "not loaded")]


def test_interact_open_of_a_window_queues_iso_open_close_window_and_a_door_wins(lua, fs):
    load(lua)
    g = lua.globals()
    win, door = J(_cls="IsoWindow", IsOpen=lambda s: False), make_door()
    g._cell = make_cell(squares={(11, 20, 0): osq(11, 20, [win])})
    p = make_player()
    start(lua, p, "interact", aid="w", x=11, y=20, kind="open")
    tick(lua, p)
    assert g._queue.adds[-1].Type == "ISOpenCloseWindow" and g._queue.adds[-1].object is win
    g._cell = make_cell(squares={(11, 20, 0): osq(11, 20, [win, door])})
    start(lua, p, "interact", aid="d", x=11, y=20, kind="open")
    tick(lua, p)
    assert g._queue.adds[-1].Type == "ISOpenCloseDoor" and g._queue.adds[-1].item is door


def test_interact_loot_food_moves_the_matching_items_and_reports_moved(lua, fs):
    load(lua)
    g = lua.globals()
    bread, axe = citem("Base.Bread", "Food"), citem("Base.Axe", "HandWeapon")
    box = box_world(lua, [bread, axe])
    p = make_player()
    start(lua, p, "interact", x=11, y=20, kind="loot", filter="food")
    tick(lua, p)
    adds = g._queue.adds
    assert [a.Type for a in adds] == ["ISInventoryTransferAction"]
    assert adds[0].item is bread and adds[0].src is box and adds[0].character is p and not ended(lua)
    p.held.append(bread)
    tick(lua, p)
    a = acts(lua, fs)
    assert states(a)[-1] == ("a1", "done", "") and a[-1]["result"] == {"moved": 1, "skipped": 0}


def test_interact_loot_filters(lua, fs):
    load(lua)
    stuff = [citem("Base.Bread", "Food"), citem("Base.Axe", "HandWeapon"),
             J(getFullType=lambda s: "Base.WaterBottle", getFluidContainer=lambda s: J()),
             citem("Base.Bandage"), citem("Base.RippedSheets"), citem("Base.RagDirty")]
    expect = {"food": 1, "weapon": 1, "water": 1, "bandage": 2, "all": 6, None: 6}
    g = lua.globals()
    for filt, n in expect.items():
        box_world(lua, stuff)
        before = len(g._queue.adds)
        args = {"x": 11, "y": 20, "kind": "loot"}
        if filt is not None:
            args["filter"] = filt
        p = make_player()
        start(lua, p, "interact", aid=str(filt), **args)
        tick(lua, p)
        assert len(g._queue.adds) - before == n, filt
    start(lua, make_player(), "interact", aid="shoes", x=11, y=20, kind="loot", filter="shoes")
    assert states(acts(lua, fs))[-1] == ("shoes", "rejected", "bad args")


def test_interact_loot_failures(lua, fs):
    load(lua)
    g = lua.globals()
    p = make_player()
    box_world(lua, [citem("Base.Axe", "HandWeapon")])
    start(lua, p, "interact", aid="nm", x=11, y=20, kind="loot", filter="food")
    tick(lua, p)
    box_world(lua, [])
    start(lua, p, "interact", aid="em", x=11, y=20, kind="loot")
    tick(lua, p)
    box_world(lua, [citem("Base.Axe")], loaded=False)
    start(lua, p, "interact", aid="ul", x=11, y=20, kind="loot")
    tick(lua, p)
    g._cell = make_cell(squares={(11, 20, 0): osq(11, 20, [J(_cls="IsoObject")])})
    start(lua, p, "interact", aid="nc", x=11, y=20, kind="loot")
    tick(lua, p)
    box = make_box([citem("Base.Axe")])
    obj = J(_cls="IsoObject", getContainer=lambda s: box)
    g._cell = make_cell(squares={(13, 20, 0): osq(13, 20, [obj]), (12, 20, 0): osq(12, 20, solid_trans=True)})
    start(lua, p, "interact", aid="na", x=13, y=20, kind="loot")
    tick(lua, p)
    box_world(lua, [citem("Base.Axe")])
    g.ISInventoryTransferAction = None
    start(lua, p, "interact", aid="nt", x=11, y=20, kind="loot")
    tick(lua, p)
    assert [s for s in states(acts(lua, fs)) if s[1] != "accepted"] == [
        ("nm", "failed", "no match"), ("em", "failed", "empty"), ("ul", "failed", "not loaded"),
        ("nc", "failed", "no container"), ("na", "failed", "not adjacent"), ("nt", "failed", "not loaded")]
    assert g._queue.adds == []


def test_interact_loot_interrupted_at_its_budget_with_nothing_moved_else_moved(lua, fs):
    load(lua)
    g = lua.globals()
    box_world(lua, [citem("Base.Axe"), citem("Base.Saw")])
    p = make_player()
    start(lua, p, "interact", aid="i", x=11, y=20, kind="loot")
    tick(lua, p)
    g._clock["ms"] += 10000 + 3000 * 2 + 1
    tick(lua, p)
    box_world(lua, [citem("Base.Axe"), citem("Base.Saw")])
    start(lua, p, "interact", aid="m", x=11, y=20, kind="loot")
    tick(lua, p)
    p.held.append(citem("Base.Axe"))
    g._clock["ms"] += 10000 + 3000 * 2 + 1
    tick(lua, p)
    a = acts(lua, fs)
    assert [s for s in states(a) if s[1] != "accepted"] == [("i", "failed", "interrupted"), ("m", "done", "")]
    assert a[-1]["result"] == {"moved": 1, "skipped": 0}


# ---- equip -----------------------------------------------------------------------------------------------------------

def test_equip_queues_the_harness_form_and_is_done_once_the_primary_hand_reads_it(lua, fs):
    load(lua)
    g = lua.globals()
    p = make_player(items=("Base.Bread", "Base.Axe"))
    start(lua, p, "equip", itemId=1001)
    tick(lua, p)
    axe = p.held[1]
    assert len(g._equips) == 1
    who, item, t, primary, two = g._equips[0]
    assert who is p and item is axe and (t, primary, two) == (50, True, False)
    assert [a.Type for a in g._queue.adds] == ["ISEquipWeaponAction"] and not ended(lua)
    tick(lua, p)
    assert not ended(lua)
    p.getPrimaryHandItem = lambda s: axe
    tick(lua, p)
    a = acts(lua, fs)
    assert states(a)[-1] == ("a1", "done", "") and a[-1]["result"] == {"itemId": 1001}


def test_equip_passes_a_two_hand_weapons_flag(lua, fs):
    load(lua)
    g = lua.globals()
    p = make_player(items=("Base.Axe",))
    p.held[0].isTwoHandWeapon = lambda s: True
    start(lua, p, "equip", itemId=1000)
    tick(lua, p)
    assert g._equips[0][4] is True


def test_equip_of_an_unknown_id_is_none_held_and_a_slow_equip_is_interrupted(lua, fs):
    load(lua)
    g = lua.globals()
    p = make_player(items=("Base.Axe",))
    start(lua, p, "equip", aid="u", itemId=5)
    start(lua, p, "equip", aid="s", itemId=1000)
    tick(lua, p)
    g._clock["ms"] += 5001
    tick(lua, p)
    g.ISEquipWeaponAction = J()
    start(lua, p, "equip", aid="nl", itemId=1000)
    tick(lua, p)
    assert [s for s in states(acts(lua, fs)) if s[1] != "accepted"] == [
        ("u", "rejected", "none held"), ("s", "failed", "interrupted"), ("nl", "failed", "not loaded")]


def test_item_by_id_falls_back_to_a_walk_of_the_items(lua):
    load(lua)
    p = make_player(items=("Base.Bread", "Base.Axe"))
    p.getInventory(p).getItemById = None
    by_id = lua.eval("PZA.skills.itemById")
    assert by_id(p, 1001) is p.held[1] and by_id(p, 1000) is p.held[0] and by_id(p, 7) is None


# ---- consume ---------------------------------------------------------------------------------------------------------

def test_consume_of_a_food_queues_the_eat_with_the_whole_item_and_is_done_when_it_is_gone(lua, fs):
    load(lua)
    g = lua.globals()
    p = make_player(items=("Base.Bread",))
    bread = p.held[0]
    start(lua, p, "consume", itemId=1000)
    tick(lua, p)
    act = g._queue.adds[0]
    assert act.Type == "ISEatFoodAction" and act.character is p and act.item is bread and act.pct == 1
    tick(lua, p)
    assert not ended(lua)
    p.held.remove(bread)
    tick(lua, p)
    a = acts(lua, fs)
    assert states(a)[-1] == ("a1", "done", "") and a[-1]["result"] == {"itemId": 1000}


def test_consume_of_a_food_is_done_when_its_hunger_change_moves(lua, fs):
    load(lua)
    p = make_player(items=("Base.Bread",))
    hc = {"v": -0.4}
    p.held[0].getHungerChange = lambda s: hc["v"]
    start(lua, p, "consume", itemId=1000)
    tick(lua, p)
    hc["v"] = -0.2
    tick(lua, p)
    assert states(acts(lua, fs))[-1] == ("a1", "done", "")


def test_consume_of_a_water_bottle_queues_the_drink_and_is_done_when_its_amount_falls(lua, fs):
    load(lua)
    g = lua.globals()
    p = make_player(items=("Base.WaterBottle",))
    bottle = p.held[0]
    start(lua, p, "consume", itemId=1000)
    tick(lua, p)
    act = g._queue.adds[0]
    assert act.Type == "ISDrinkFluidAction" and act.item is bottle and act.pct == 1
    bottle.getFluidContainer(bottle).st["amount"] = 0.2
    tick(lua, p)
    a = acts(lua, fs)
    assert states(a)[-1] == ("a1", "done", "") and a[-1]["result"] == {"itemId": 1000}


def test_consume_of_a_hammer_or_bleach_is_not_valid_and_queues_nothing(lua, fs):
    load(lua)
    g = lua.globals()
    p = make_player(items=("Base.Hammer", "Base.Bleach"))
    start(lua, p, "consume", aid="h", itemId=1000)
    tick(lua, p)
    start(lua, p, "consume", aid="b", itemId=1001)
    tick(lua, p)
    assert [s for s in states(acts(lua, fs)) if s[1] != "accepted"] == [
        ("h", "failed", "not valid"), ("b", "failed", "not valid")]
    assert g._queue.adds == []


def test_consume_of_petrol_in_a_clean_reading_container_is_still_not_valid(lua, fs):
    load(lua)
    p = make_player(items=("Base.PetrolBottle",))
    start(lua, p, "consume", itemId=1000)
    tick(lua, p)
    assert states(acts(lua, fs))[-1] == ("a1", "failed", "not valid")


def test_consume_failures(lua, fs):
    load(lua)
    g = lua.globals()
    p = make_player(items=("Base.Bread",))
    start(lua, p, "consume", aid="u", itemId=3)
    g._valid["start"] = False
    start(lua, p, "consume", aid="v", itemId=1000)
    tick(lua, p)
    g._valid["start"] = True
    start(lua, p, "consume", aid="i", itemId=1000)
    tick(lua, p)
    g._clock["ms"] += 20001
    tick(lua, p)
    g.ISEatFoodAction = J()
    start(lua, p, "consume", aid="nl", itemId=1000)
    tick(lua, p)
    assert [s for s in states(acts(lua, fs)) if s[1] != "accepted"] == [
        ("u", "rejected", "none held"), ("v", "failed", "not valid"), ("i", "failed", "interrupted"),
        ("nl", "failed", "not loaded")]


# ---- drop ------------------------------------------------------------------------------------------------------------

def test_drop_queues_one_floor_drop_and_is_done_moved_one_once_the_inventory_shrinks(lua, fs):
    load(lua)
    g = lua.globals()
    p = make_player(items=("Base.Plank", "Base.Axe"))
    axe = p.held[1]
    start(lua, p, "drop", itemId=1001)
    tick(lua, p)
    adds = g._queue.adds
    assert [a.Type for a in adds] == ["ISDropWorldItemAction"] and adds[0].item is axe and adds[0].character is p
    assert tuple(adds[0].args) == ("sq", 0, 0, 0, 0, False)
    tick(lua, p)
    assert not ended(lua)
    p.held.remove(axe)
    tick(lua, p)
    a = acts(lua, fs)
    assert states(a)[-1] == ("a1", "done", "") and a[-1]["result"] == {"moved": 1}


def test_drop_failures(lua, fs):
    load(lua)
    g = lua.globals()
    p = make_player(items=("Base.Plank",))
    start(lua, p, "drop", aid="u", itemId=4)
    start(lua, p, "drop", aid="i", itemId=1000)
    tick(lua, p)
    g._clock["ms"] += 13001
    tick(lua, p)
    g.ISDropWorldItemAction = None
    start(lua, p, "drop", aid="nl", itemId=1000)
    tick(lua, p)
    assert [s for s in states(acts(lua, fs)) if s[1] != "accepted"] == [
        ("u", "rejected", "none held"), ("i", "failed", "interrupted"), ("nl", "failed", "not loaded")]


# ---- every skill's end; every line in the schema ---------------------------------------------------------------------

def run_walk_to(lua):
    walk_world(lua)
    p = make_player()
    pos = mover(p, 10.0, 20.0)
    start(lua, p, "walkTo", aid="walkTo", x=12, y=20, gait="run")
    tick(lua, p)
    pos["x"] = 11.5
    tick(lua, p)
    return p


def run_steer(lua):
    p = make_player()
    start(lua, p, "steer", aid="steer", vx=1, vy=0, seconds=1, gait="sprint")
    tick(lua, p)
    lua.globals()._clock["ms"] += 1000
    tick(lua, p)
    return p


def run_stop(lua):
    p = make_player()
    start(lua, p, "stop", aid="stop")
    tick(lua, p)
    return p


def run_attack(lua):
    z, p = attack_world(lua, zx=13.0)
    pos = mover(p, 10.0, 20.0)
    start(lua, p, "attack", aid="attack", targetId=7)
    tick(lua, p)
    pos["x"] = 12.0
    tick(lua, p)
    lua.globals()._clock["ms"] += 1500
    tick(lua, p)
    return p


def run_interact(lua):
    door = make_door()
    lua.globals()._cell = make_cell(squares={(11, 20, 0): osq(11, 20, [door])})
    p = make_player()
    start(lua, p, "interact", aid="interact", x=11, y=20, kind="open")
    tick(lua, p)
    door.st["open"] = True
    tick(lua, p)
    return p


def run_loot(lua):
    box_world(lua, [citem("Base.Bread", "Food")])
    p = make_player()
    start(lua, p, "interact", aid="loot", x=11, y=20, kind="loot", filter="food")
    tick(lua, p)
    p.held.append(citem("Base.Bread", "Food"))
    tick(lua, p)
    return p


def run_equip(lua):
    p = make_player(items=("Base.Axe",))
    start(lua, p, "equip", aid="equip", itemId=1000)
    tick(lua, p)
    p.getPrimaryHandItem = lambda s: p.held[0]
    tick(lua, p)
    return p


def run_consume(lua):
    p = make_player(items=("Base.Bread",))
    start(lua, p, "consume", aid="consume", itemId=1000)
    tick(lua, p)
    p.held.pop()
    tick(lua, p)
    return p


def run_drop(lua):
    p = make_player(items=("Base.Plank",))
    start(lua, p, "drop", aid="drop", itemId=1000)
    tick(lua, p)
    p.held.pop()
    tick(lua, p)
    return p


def run_failed_attack(lua):
    _, p = attack_world(lua, zx=13.0)
    start(lua, p, "attack", aid="attackF", targetId=7)
    tick(lua, p)
    lua.globals()._clock["ms"] += 4000
    tick(lua, p)
    return p


def run_failed_consume(lua):
    p = make_player(items=("Base.Hammer",))
    start(lua, p, "consume", aid="consumeF", itemId=1000)
    tick(lua, p)
    return p


RUNS = [run_walk_to, run_steer, run_stop, run_attack, run_interact, run_loot, run_equip, run_consume, run_drop,
        run_failed_attack, run_failed_consume]


@pytest.mark.parametrize("run", RUNS, ids=[r.__name__ for r in RUNS])
def test_every_skills_end_turns_the_motor_off(lua, fs, run):
    load(lua)
    sense(lua)
    p = run(lua)
    a = acts(lua, fs)
    assert ended(lua) and a[-1]["state"] in ("done", "failed"), states(a)
    assert list(p.sets[-3:]) == OFF and lua.eval("PZA.motor.wantRun") is False


def test_every_emitted_reason_and_result_key_is_in_the_schema(lua, fs):
    with open(SCHEMA, encoding="utf-8") as fh:
        defs = json.load(fh)["$defs"]
    reasons = set(defs["reason"]["enum"])
    load(lua)
    sense(lua)
    for run in RUNS:
        run(lua)
    a = acts(lua, fs)
    for scenario in (test_interact_open_failures, test_interact_loot_failures, test_consume_failures, test_drop_failures,
                     test_equip_of_an_unknown_id_is_none_held_and_a_slow_equip_is_interrupted,
                     test_attack_with_bad_args_is_rejected, test_attack_on_a_dead_or_far_zombie_is_rejected_no_target,
                     test_attack_without_a_weapon_is_rejected_no_weapon):
        fs2 = FakeFS()                                  # each failure scenario on a fresh host, its lines kept
        lua2 = make_lua(fs2)
        scenario(lua2, fs2)
        a += acts(lua2, fs2)
    seen_types = {x["type"] for x in a if x["state"] == "done"}
    assert {"walkTo", "steer", "stop", "attack", "interact", "equip", "consume", "drop"} <= seen_types
    for x in a:
        assert x["reason"] == "" or x["reason"] in reasons, x
        props = defs["result_" + x["type"]]["properties"]
        assert set(x["result"]) <= set(props), x


def test_every_reason_literal_in_the_skills_file_is_in_the_schema():
    with open(SCHEMA, encoding="utf-8") as fh:
        reasons = set(json.load(fh)["$defs"]["reason"]["enum"])
    src = "".join(open(lua_file(f), encoding="utf-8").read()
                  for f in ("client/PZAgent_Skills.lua", "client/PZAgent_SkillsWorld.lua"))
    found = set(re.findall(r'"(?:failed|rejected)",\s*"([^"]+)"', src))
    found |= set(re.findall(r'return false,\s*"([^"]+)"', src))
    body = src[src.index("local function queueConsume"):]
    body = body[:body.index("\nend\n")]
    found |= set(re.findall(r'return "([^"]+)"', body))                     # queueConsume's returned reasons
    assert len(found) >= 15 and found <= reasons, found - reasons


def test_a_failed_tick_with_no_reason_is_reported_interrupted(lua, fs):
    load(lua)
    lua.execute("PZA.skills.types.blank = { check = function(args, p) return true, '', {} end,"
                " tick = function(p, st) return 'failed' end }")
    start(lua, make_player(), "blank")
    tick(lua, make_player())
    assert states(acts(lua, fs)) == [("a1", "accepted", ""), ("a1", "failed", "interrupted")]


# ---- S-12: the runner guards a skill's raise -------------------------------------------------------------------------

def test_a_raising_tick_ends_the_skill_failed_interrupted_and_is_counted(lua, fs):
    load(lua)
    lua.execute("PZA.skills.types.boom = { check = function(args, p) return true, '', {} end,"
                " tick = function(p, st) error('tick blew up') end }")
    p = make_player()
    q = lua.globals()._queue
    q.queue.append("vanilla")
    lua.execute("PZA.motor.want('run')")
    start(lua, p, "boom")
    tick(lua, p)
    a = acts(lua, fs)
    assert states(a) == [("a1", "accepted", ""), ("a1", "failed", "interrupted")] and "snapshot" in a[-1]
    assert ended(lua) and q.queue == [] and list(p.sets[-3:]) == OFF and lua.eval("PZA.motor.wantRun") is False
    assert lua.eval("PZA.skills.errors") == 1 and "tick blew up" in lua.eval("PZA.skills.lastError")


def test_a_raising_check_is_rejected_bad_args_and_leaves_the_running_skill(lua, fs):
    load(lua)
    walk_world(lua, 30, 20)
    lua.execute("PZA.skills.types.boom = { check = function(args, p) error('check blew up') end,"
                " tick = function(p, st) return 'done', {} end }")
    p = make_player()
    start(lua, p, "walkTo", aid="w", x=30, y=20)
    start(lua, p, "boom", aid="b")
    assert states(acts(lua, fs)) == [("w", "accepted", ""), ("b", "rejected", "bad args")]
    assert lua.eval("PZA.skills.cur.aid") == "w" and lua.eval("PZA.skills.errors") == 1
    assert "check blew up" in lua.eval("PZA.skills.lastError")


def test_item_by_id_asks_get_item_by_id_first(lua):
    load(lua)
    p = make_player(items=("Base.Bread",))
    bagged = J(getFullType=lambda s: "Base.Apple", getID=lambda s: 77)
    p.getInventory(p).getItemById = lambda s, i: bagged if i == 77 else None
    assert lua.eval("PZA.skills.itemById")(p, 77) is bagged


def test_drop_is_done_when_the_inventory_shrinks_though_the_id_still_answers(lua, fs):
    load(lua)
    p = make_player(items=("Base.Plank", "Base.Axe"))
    axe = p.held[1]
    p.getInventory(p).getItemById = lambda s, i: axe
    start(lua, p, "drop", itemId=1001)
    tick(lua, p)
    tick(lua, p)
    assert not ended(lua)
    p.held.pop()
    tick(lua, p)
    a = acts(lua, fs)
    assert states(a)[-1] == ("a1", "done", "") and a[-1]["result"] == {"moved": 1}


# ---- Task 4 fix 1: the reset's re-cover gaps; the mid-skill death; the run dropped at the swing ----------------------

def test_interact_open_opens_a_thumpable_door(lua, fs):
    load(lua)
    g = lua.globals()
    door = make_door(cls="IsoThumpable")
    door.isDoor = lambda s: True
    g._cell = make_cell(squares={(11, 20, 0): osq(11, 20, [J(_cls="IsoThumpable", isDoor=lambda s: False), door])})
    p = make_player()
    start(lua, p, "interact", x=11, y=20, kind="open")
    tick(lua, p)
    assert [a.Type for a in g._queue.adds] == ["ISOpenCloseDoor"] and g._queue.adds[0].item is door


def test_consume_of_a_container_without_is_poisonous_is_not_valid(lua, fs):
    load(lua)
    p = make_player(items=("Base.WaterBottle",))
    fc = p.held[0].getFluidContainer(p.held[0])
    fc.isPoisonous = None
    start(lua, p, "consume", itemId=1000)
    tick(lua, p)
    assert states(acts(lua, fs))[-1] == ("a1", "failed", "not valid") and lua.globals()._queue.adds == []


@pytest.mark.parametrize("item,cls", [("Base.Bread", "ISEatFoodAction"), ("Base.WaterBottle", "ISDrinkFluidAction")])
def test_a_consume_action_without_is_valid_start_is_not_valid_and_never_queued(lua, fs, item, cls):
    load(lua)
    g = lua.globals()
    setattr(g, cls, J(new=lambda c, p, it, pct: J(Type=cls)))
    # every pcall that catches a raise is counted: the absent isValidStart is index-checked, never called to find out
    lua.execute("pcallFails = 0; local raw = pcall; pcall = function(...) local r = { raw(...) };"
                " if not r[1] then pcallFails = pcallFails + 1 end; return unpack(r) end")
    p = make_player(items=(item,))
    start(lua, p, "consume", itemId=1000)
    tick(lua, p)
    assert states(acts(lua, fs))[-1] == ("a1", "failed", "not valid") and g._queue.adds == []
    assert lua.eval("PZA.skills.errors") == 0 and lua.eval("pcallFails") == 0


def test_interact_loot_whose_sub_walk_fails_is_not_adjacent_with_the_queue_cleared(lua, fs):
    load(lua)
    g = lua.globals()
    box = make_box([citem("Base.Axe")])
    obj = J(_cls="IsoObject", getContainerCount=lambda s: 1, getContainerByIndex=lambda s, i: box)
    g._cell = make_cell(squares={(13, 20, 0): osq(13, 20, [obj]), (12, 20, 0): osq(12, 20)})
    g.ISWalkToTimedAction = None
    p = make_player()
    start(lua, p, "interact", x=13, y=20, kind="loot")
    tick(lua, p)
    assert states(acts(lua, fs))[-1] == ("a1", "failed", "not adjacent")
    assert g._queue.cleared >= 2 and g._queue.queue == [] and g._queue.adds == []   # tickSub's clear, then the runner's


QUEUELESS = [
    ("walkTo", {"x": 12, "y": 20}, "no path"),
    ("interact", {"x": 11, "y": 20, "kind": "open"}, "not loaded"),
    ("interact", {"x": 11, "y": 20, "kind": "loot"}, "not loaded"),
    ("equip", {"itemId": 1000}, "not loaded"),
    ("consume", {"itemId": 1000}, "not loaded"),
    ("consume", {"itemId": 1001}, "not loaded"),
    ("drop", {"itemId": 1000}, "not loaded"),
    ("attack", {"targetId": 7}, "no path"),
]


@pytest.mark.parametrize("typ,args,reason", QUEUELESS, ids=[q[0] + "-" + q[2] + "-" + str(i) for i, q in enumerate(QUEUELESS)])
def test_every_skill_without_the_vanilla_queue_fails_its_reason_and_raises_nothing(lua, fs, typ, args, reason):
    load(lua)
    g = lua.globals()
    z = make_zombie(7, 13.0, 20.0)
    sense(lua, [z])
    squares = {(12, 20, 0): "target", (13, 20, 0): "zsq"}
    if typ == "interact" and args["kind"] == "open":
        squares[(11, 20, 0)] = osq(11, 20, [make_door()])
    elif typ == "interact":
        box = make_box([citem("Base.Axe")])
        squares[(11, 20, 0)] = osq(11, 20, [J(_cls="IsoObject", getContainerCount=lambda s: 1,
                                               getContainerByIndex=lambda s, i: box)])
    g._cell = make_cell(zombies=[z], squares=squares)
    g.ISTimedActionQueue = None
    p = make_player(items=("Base.Bread", "Base.WaterBottle"), weapon=make_weapon())
    start(lua, p, typ, **args)
    tick(lua, p)
    assert states(acts(lua, fs))[-1] == ("a1", "failed", reason)
    assert lua.eval("PZA.skills.errors") == 0 and list(p.sets[-3:]) == OFF


@pytest.mark.parametrize("typ", ["steer", "stop"])
def test_the_queueless_skills_run_without_the_vanilla_queue(lua, fs, typ):
    load(lua)
    lua.globals().ISTimedActionQueue = None
    p = make_player()
    args = {"vx": 1, "vy": 0, "seconds": 1} if typ == "steer" else {}
    start(lua, p, typ, **args)
    tick(lua, p)
    lua.globals()._clock["ms"] += 1000
    tick(lua, p)
    assert states(acts(lua, fs))[-1] == ("a1", "done", "") and lua.eval("PZA.skills.errors") == 0


def setup_running(lua, typ):
    """a running skill of typ after one tick: its player and the args used"""
    g = lua.globals()
    if typ == "attack":
        _, p = attack_world(lua, zx=13.0)
        start(lua, p, "attack", targetId=7)
    elif typ == "interact":
        box_world(lua, [citem("Base.Axe")])
        p = make_player()
        start(lua, p, "interact", x=11, y=20, kind="loot")
    else:
        p = make_player(items=("Base.Bread",))
        start(lua, p, typ, itemId=1000)
    tick(lua, p)
    assert not ended(lua) and len(g._queue.adds) >= 1, typ
    return p


@pytest.mark.parametrize("typ", ["attack", "interact", "equip", "consume", "drop"])
def test_a_player_dying_mid_skill_fails_it_dead_with_the_motor_off(lua, fs, typ):
    load(lua)
    sense(lua)
    p = setup_running(lua, typ)
    p.getBodyDamage = lambda s: J(getOverallBodyHealth=lambda s2: 0.0)
    tick(lua, p)
    assert states(acts(lua, fs))[-1] == ("a1", "failed", "dead") and ended(lua)
    assert list(p.sets[-3:]) == OFF and lua.globals()._queue.queue == []


def test_the_swing_writes_both_latches_false_before_do_attack(lua, fs):
    load(lua)
    _, p = attack_world(lua, zx=13.0)
    pos = mover(p, 10.0, 20.0)
    seen = []
    p.DoAttack = lambda s, f: seen.append(list(p.sets)) or False
    start(lua, p, "attack", targetId=7)
    tick(lua, p)
    pos["x"] = 12.0
    tick(lua, p)
    assert len(seen) == 1
    assert seen[0][-2:] == [("setForceRun", False), ("setForceSprint", False)]


# ---- a raising Java member in the runner's own reads (ruling S-15) ---------------------------------------------------

def boom(*a):
    raise RuntimeError("java raised")


@pytest.mark.parametrize("member", ["setAutoWalk", "setAutoWalkDirection"])
def test_steer_without_the_auto_walk_fails_not_loaded(lua, fs, member):
    load(lua)
    p = make_player()
    setattr(p, member, None)
    start(lua, p, "steer", vx=1, vy=0, seconds=3)
    tick(lua, p)
    assert states(acts(lua, fs))[-1] == ("a1", "failed", "not loaded") and ended(lua)
    assert ("setAutoWalk", True) not in p.sets and lua.eval("PZA.skills.errors") == 0


def test_a_raising_dead_check_rejects_interrupted_and_is_counted(lua, fs):
    load(lua)
    p = make_player()
    p.getBodyDamage = boom
    start(lua, p, "walkTo", x=12, y=20)
    a = acts(lua, fs)
    assert states(a) == [("a1", "rejected", "interrupted")] and ended(lua)
    assert a[0]["snapshot"]["me"]["x"] == 10.0 and a[0]["snapshot"]["me"].get("health") is None
    assert lua.eval("PZA.skills.errors") == 2 and "java raised" in lua.eval("PZA.skills.lastError")


def test_stop_reads_no_dead_check_so_a_raising_body_still_stops(lua, fs):
    load(lua)
    p = make_player()
    p.getBodyDamage = boom
    start(lua, p, "stop")
    tick(lua, p)
    assert [s[1:] for s in states(acts(lua, fs))] == [("accepted", ""), ("done", "")] and ended(lua)


def test_a_raising_snapshot_read_leaves_its_field_absent_and_the_end_still_lands(lua, fs):
    load(lua)
    p = make_player()
    start(lua, p, "stop")
    p.getX, p.getZ = boom, boom
    tick(lua, p)
    a = acts(lua, fs)
    assert states(a)[-1] == ("a1", "done", "") and ended(lua)
    me = a[-1]["snapshot"]["me"]
    assert me.get("x") is None and me.get("y") is None and me.get("z") is None and me["health"] == 100.0
    assert lua.eval("PZA.skills.errors") == 2
    assert list(p.sets[-3:]) == OFF


def test_a_raising_nearest_zombie_leaves_nearest_absent(lua, fs):
    load(lua)
    lua.globals()._boom = boom
    lua.execute("PZA.sense = { nearestZombie = function(p) return _boom() end }")
    p = make_player()
    start(lua, p, "fly")
    a = acts(lua, fs)
    assert states(a) == [("a1", "rejected", "unknown type")] and a[0]["snapshot"].get("nearest") is None
    assert a[0]["snapshot"]["me"]["x"] == 10.0 and lua.eval("PZA.skills.errors") == 1


def test_a_raising_motor_setter_is_counted_and_the_others_still_run(lua, fs):
    load(lua)
    p = make_player()
    start(lua, p, "steer", vx=1, vy=0, seconds=1, gait="run")
    tick(lua, p)
    p.setForceRun = boom
    lua.globals()._clock["ms"] += 1000
    tick(lua, p)
    assert states(acts(lua, fs))[-1] == ("a1", "done", "") and ended(lua)
    assert list(p.sets[-2:]) == [("setForceSprint", False), ("setAutoWalk", False)]
    assert lua.eval("PZA.motor.wantRun") is False and lua.eval("PZA.skills.errors") == 1


def test_a_raise_at_a_superseded_end_still_starts_the_new_skill(lua, fs):
    load(lua)
    p = make_player()
    start(lua, p, "steer", vx=1, vy=0, seconds=5)
    tick(lua, p)
    p.setAutoWalk = boom
    start(lua, p, "stop", aid="a2")
    assert states(acts(lua, fs))[-2:] == [("a1", "failed", "superseded"), ("a2", "accepted", "")]
    assert lua.eval("PZA.skills.cur.aid") == "a2" and lua.eval("PZA.skills.errors") == 1


def test_the_runner_ends_through_mo_off_and_keeps_no_setter_list_of_its_own(lua):
    """Fix wave M1: MO.off owns the per-setter guard; the runner's offSafely and K.OFF_SETTERS are gone."""
    load(lua)
    src = open(lua_file("client/PZAgent_Skills.lua"), encoding="utf-8").read()
    assert "offSafely" not in src and "OFF_SETTERS" not in src and "MO.off(p)" in src
    assert lua.eval("PZA.skills.OFF_SETTERS") is None


# ---- X4 fix pass 2.7 (fix-wave review Minor 4, ruling S-30): the latches off before the end line -------------------

def test_an_end_line_whose_emit_raises_still_clears_the_latches_and_the_runner(lua, fs):
    load(lua)
    g = lua.globals()
    g._cell = make_cell(squares={(12, 20, 0): J(getX=lambda s: 12, getY=lambda s: 20, getZ=lambda s: 0)})
    p = make_player()
    start(lua, p, "walkTo", x=12, y=20, gait="run")
    tick(lua, p)                                                # the walk's first tick wants the run
    assert lua.eval("PZA.motor.wantRun") is True and lua.eval("PZA.skills.cur") is not None
    n0 = len(p.sets)
    lua.execute("PZA.emit = function(kind, body) error('emit raised') end")
    g._p = p
    g._cmd = lua.table_from({"seq": 2, "aid": "s", "type": "stop", "args": {}}, recursive=True)
    ok = lua.eval("pcall(PZA.skills.start, _cmd, _p)")          # the walk's superseded line raises in its emit
    assert ok is False or (isinstance(ok, tuple) and ok[0] is False)
    assert lua.eval("PZA.motor.wantRun") is False and lua.eval("PZA.motor.wantSprint") is False
    assert list(p.sets[n0:n0 + 3]) == OFF and lua.eval("PZA.skills.cur") is None


def witem(ft, w=1.0):
    return J(_cls=None, getFullType=lambda s: ft, getFluidContainer=lambda s: None, getWeight=lambda s: w)


def test_interact_loot_stops_before_the_weight_cap_and_reports_skipped(lua, fs):
    load(lua)
    g = lua.globals()
    items = [witem("Base.A"), witem("Base.B"), witem("Base.C")]
    box_world(lua, items)
    p = make_player(weight=7.0)
    start(lua, p, "interact", x=11, y=20, kind="loot", maxWeight=8.5)
    tick(lua, p)
    assert len(g._queue.adds) == 1
    p.held.append(items[0])
    tick(lua, p)
    a = acts(lua, fs)
    assert states(a)[-1] == ("a1", "done", "") and a[-1]["result"] == {"moved": 1, "skipped": 2}


def test_a_max_weight_of_zero_loots_everything(lua, fs):
    load(lua)
    g = lua.globals()
    box_world(lua, [witem("Base.A"), witem("Base.B"), witem("Base.C")])
    p = make_player(weight=70.0)
    start(lua, p, "interact", x=11, y=20, kind="loot", maxWeight=0)
    tick(lua, p)
    assert len(g._queue.adds) == 3


def test_a_negative_max_weight_is_bad_args(lua, fs):
    load(lua)
    box_world(lua, [witem("Base.A")])
    start(lua, make_player(), "interact", aid="neg", x=11, y=20, kind="loot", maxWeight=-1)
    assert states(acts(lua, fs))[-1] == ("neg", "rejected", "bad args")
