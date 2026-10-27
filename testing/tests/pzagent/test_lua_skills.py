"""PZAgent_Skills.lua (Plan 22 Task 3): the skill runner PZA.skills (K.start, K.tick, typed act lines through
PZA.emit) and the three movement skills walkTo, steer and stop, each one bounded engine action with a typed result;
the Motor's latches wanted at a skill's start and cleared at every end."""
import json
import math
import re

import pytest

from agent.base import pza1
from .conftest import lua_file, make_player, make_cell

LIVE = "pzagent/admin/state.log"
R2 = 1 / math.sqrt(2)


def load(lua):
    for f in ("client/PZAgent_Link.lua", "client/PZAgent_Motor.lua", "client/PZAgent_Skills.lua"):
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


def test_the_motor_and_skills_never_name_the_banned_setters():
    for f in ("client/PZAgent_Motor.lua", "client/PZAgent_Skills.lua"):
        src = open(lua_file(f), encoding="utf-8").read()
        for name in ("setRunning", "setSprinting", "setPathfindRunning", "setToggleToRun"):
            assert re.search(name, src) is None, (f, name)
