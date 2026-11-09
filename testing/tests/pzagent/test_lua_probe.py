"""PZAgent_FacingProbe.lua (PZA/1.11, Plan 32 Task 1; the spec `2026-11-08-plan-32-the-facing-design.md` section 4.1 and
the facing jar read's six experiments): the act probe {mode, targetId, x, y, ticks, k, vx, vy}, which for `ticks`
client ticks reads the facing ring before any write, applies its mode's write toward the target and emits one progress
line a tick (result_probe_step), then ends done on the tick after the last with the summary (result_probe); every flag a
mode sets is restored on done, on a stop, on a supersede and on a raise mid-tick. Run on the lupa host: the runner and its
skills loaded in the game's order (the probe's file first: client files load by name, "f" before "h", so it registers
without K's helpers at load), over conftest.make_player (a fixed body, look and forward direction a test sets) and
make_mover (the body turning toward the written facing; a snap sets it at once)."""
import json
import math
import os

import pytest

from agent.base import pza1
from .conftest import ROOT, TICK_MS, J, lua_file, make_mover, make_player, step_world
from .test_lua_skills import acts, sense, start, states, tick

SCHEMA = os.path.join(ROOT, "testing", "agent", "base", "schema", "pza1.json")
FILES = ("shared/PZAgent_World.lua", "client/PZAgent_FacingProbe.lua", "client/PZAgent_Link.lua",
         "client/PZAgent_Motor.lua", "client/PZAgent_Skills.lua", "client/PZAgent_SkillsWorld.lua",
         "client/PZAgent_Stance.lua", "client/PZAgent_StanceMelee.lua", "client/PZAgent_Tend.lua")
STEP_KEYS = {"step", "tick", "b", "fwd", "body", "look", "twist", "aim", "aiming", "forceAim", "autoWalk", "err_body",
             "err_look"}
MODES = ("read", "snap_aimed", "unaimed_face", "unaimed_snap", "block_aim", "ignore_aim", "turn_k")


def load(lua, zombies=()):
    for f in FILES:
        lua.execute(open(lua_file(f), encoding="utf-8").read())
    lua.globals().PZA.tick = 0
    lua.execute("PZA.link.init('admin')")
    sense(lua, zombies)


def go(lua, p, aid="p1", **args):
    start(lua, p, "probe", aid=aid, **args)


def run(lua, p, n=1, w=None, between=None):
    """n client ticks: the fake engine's update (make_mover's, when w), the clock and PZA.tick, then the runner's tick;
    between(i) runs before the i-th tick's runner (1-based)."""
    for i in range(1, n + 1):
        if w is not None:
            step_world(w, p)
        lua.globals()._clock["ms"] += TICK_MS
        lua.execute("PZA.tick = PZA.tick + 1")
        if between is not None:
            between(i)
        tick(lua, p)


def lines(lua, fs, aid="p1"):
    return [a for a in acts(lua, fs) if a["aid"] == aid]


def progress(lua, fs, aid="p1"):
    return [a["result"] for a in lines(lua, fs, aid) if a["state"] == "progress"]


def done(lua, fs, aid="p1"):
    ends = [a for a in lines(lua, fs, aid) if a["state"] in ("done", "failed", "rejected")]
    assert len(ends) == 1, [(a["state"], a["reason"]) for a in lines(lua, fs, aid)]
    return ends[0]


def calls(p, name=None):
    return [c for c in p.aim["calls"] if name is None or c[0] == name]


def deg(r):
    return r * 180 / math.pi


# ---- the checks ----------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("args, reason", [({"mode": "kick", "x": 11.0, "y": 20.0}, "bad args"),
                                          ({"mode": 3, "x": 11.0, "y": 20.0}, "bad args"),
                                          ({"x": 11.0, "y": 20.0}, "bad args"),
                                          ({"mode": "read", "x": 11.0, "y": 20.0, "ticks": "x"}, "bad args"),
                                          ({"mode": "read", "x": 11.0, "y": 20.0, "ticks": 0}, "bad args"),
                                          ({"mode": "read", "x": 11.0, "y": 20.0, "ticks": 2.5}, "bad args"),
                                          ({"mode": "read", "x": "a", "y": 20.0}, "bad args"),
                                          ({"mode": "turn_k", "x": 11.0, "y": 20.0}, "bad args"),
                                          ({"mode": "turn_k", "x": 11.0, "y": 20.0, "k": 0}, "bad args"),
                                          ({"mode": "read"}, "no target"),
                                          ({"mode": "read", "x": 11.0}, "no target"),
                                          ({"mode": "read", "targetId": 99}, "no target")])
def test_a_bad_mode_a_missing_target_or_bad_ticks_is_rejected(lua, fs, args, reason):
    load(lua)
    go(lua, make_player(), **args)
    assert states(lines(lua, fs)) == [("p1", "rejected", reason)]


def test_the_probe_registers_before_the_runner_loads_and_its_modes_are_the_schemas(lua):
    """The file sorts first among the client files ("facingprobe" before "hutch"): it registers into PZA.skills.types
    with no K helper at load, and the runner's file keeps it."""
    lua.execute(open(lua_file("shared/PZAgent_World.lua"), encoding="utf-8").read())
    lua.execute(open(lua_file("client/PZAgent_FacingProbe.lua"), encoding="utf-8").read())
    assert lua.eval("PZA.skills.types.probe") is not None
    load(lua)
    assert lua.eval("PZA.skills.types.probe.check") is not None
    assert sorted(lua.eval("PZA.schema.probeModes").keys()) == sorted(MODES)
    names = sorted(n.lower() for n in os.listdir(os.path.dirname(lua_file("client/PZAgent_Link.lua"))))
    assert names.index("pzagent_facingprobe.lua") < names.index("pzagent_motor.lua") < names.index("pzagent_skills.lua")


# ---- the ring and the read mode ------------------------------------------------------------------------------------

def test_read_for_3_ticks_emits_3_progress_lines_then_done_with_the_wrapped_error(lua, fs):
    """A fixed body angle against a point due south (bearing +90 degrees): err_body is body - b wrapped to (-180, 180]
    in degrees; every step carries the ring's keys; done comes on the 4th tick with the summary."""
    load(lua)
    p = make_player()
    p.angles.update(body=math.radians(-150), look=math.radians(170), fwd=0.25, twist=7.5)
    p.aim["vec"] = (0.0, -3.0)
    go(lua, p, mode="read", x=10.0, y=25.0, ticks=3)
    run(lua, p, 3)
    steps = progress(lua, fs)
    assert [s["step"] for s in steps] == [1, 2, 3] and [s["tick"] for s in steps] == [1, 2, 3]
    s = steps[0]
    assert set(s) == STEP_KEYS
    assert s["b"] == pytest.approx(math.pi / 2) and s["fwd"] == 0.25 and s["twist"] == 7.5
    assert s["aim"] == pytest.approx(-math.pi / 2) and s["autoWalk"] is False
    assert s["err_body"] == pytest.approx(120.0) and s["err_look"] == pytest.approx(80.0)   # -240 wraps to 120
    assert lua.eval("PZA.skills.cur") is not None
    run(lua, p, 1)
    end = done(lua, fs)
    assert (end["state"], end["result"]["ticks"], end["result"]["mode"]) == ("done", 3, "read")
    assert end["result"]["err_body_med"] == pytest.approx(120.0) and end["result"]["hold30"] == 0
    assert end["result"]["pressed"] is False and "press" not in end["result"]


def test_read_holds_the_stance_through_the_motor_and_faces_every_tick_then_releases(lua, fs):
    load(lua)
    p = make_player()
    go(lua, p, mode="read", x=12.0, y=20.0, ticks=2)
    run(lua, p, 1)
    assert lua.eval("PZA.motor.wantAim") is True and lua.eval("PZA.skills.stance.held") is True
    assert calls(p, "setForceAim") == [("setForceAim", True)]
    run(lua, p, 2)
    assert p.faced == [(12.0, 20.0), (12.0, 20.0)]                         # faceLocationF at the point, each ring tick
    assert lua.eval("PZA.motor.wantAim") is False and lua.eval("PZA.skills.stance.held") is False
    assert calls(p)[-1] == ("nullifyAiming", None) and done(lua, fs)["state"] == "done"


def test_the_readings_come_before_the_write(lua, fs):
    """snap_aimed snaps the fake's body onto b at once: the first step still reads the body before the snap (-90 off)
    and the second reads it on b."""
    load(lua)
    p = make_player()
    go(lua, p, mode="snap_aimed", x=10.0, y=25.0, ticks=2)
    run(lua, p, 2)
    errs = [s["err_body"] for s in progress(lua, fs)]
    assert errs[0] == pytest.approx(-90.0) and errs[1] == pytest.approx(0.0)


def test_snap_aimed_snaps_onto_the_bearing_every_tick(lua, fs):
    load(lua)
    p = make_player()
    go(lua, p, mode="snap_aimed", x=13.0, y=24.0, ticks=3)
    run(lua, p, 4)
    snaps = [c[1] for c in calls(p, "setTargetAndCurrentDirection")]
    b = math.atan2(4.0, 3.0)
    assert len(snaps) == 3 and all(s == pytest.approx((math.cos(b), math.sin(b))) for s in snaps)
    assert calls(p, "setForceAim") == [("setForceAim", True)] and p.faced == []
    assert lua.eval("PZA.motor.wantAim") is False


def test_a_zombie_target_is_faced_by_face_this_object_and_its_bearing_read_live(lua, fs):
    p, z, w = make_mover(zx=12.0, zy=20.0, look=math.pi / 2)
    load(lua, [z])
    go(lua, p, mode="unaimed_face", targetId=7, ticks=3)
    run(lua, p, 3, w=w)
    steps = progress(lua, fs)
    assert p.faced == [z, z, z] and all(s["b"] == pytest.approx(0.0) for s in steps)
    assert steps[0]["err_body"] == pytest.approx(90.0) and steps[2]["err_body"] < steps[1]["err_body"] < 90.0


# ---- the unaimed modes ---------------------------------------------------------------------------------------------

def test_unaimed_face_releases_the_stance_and_faces(lua, fs):
    load(lua)
    p = make_player()
    lua.execute("PZA.motor.wantAim = true; PZA.skills.stance.held = true")
    go(lua, p, mode="unaimed_face", x=12.0, y=20.0, ticks=2)
    run(lua, p, 1)
    assert lua.eval("PZA.motor.wantAim") is False and lua.eval("PZA.skills.stance.held") is False
    assert ("setForceAim", False) in calls(p) and p.faced == [(12.0, 20.0)]
    run(lua, p, 2)
    assert calls(p, "setTargetAndCurrentDirection") == [] and done(lua, fs)["state"] == "done"


def test_unaimed_snap_with_a_zombie_presses_on_the_last_tick_only_after_the_snap(lua, fs):
    p, z, w = make_mover(zx=11.0, zy=20.0, look=math.pi)
    hp = []

    def on_attack(world, shove):
        hp.append(world["zhp"])
        world["zhp"] = 0.75
    w["on_attack"] = on_attack
    load(lua, [z])
    order = []
    snap0, attack0 = p.setTargetAndCurrentDirection, p.DoAttack
    p.setTargetAndCurrentDirection = lambda s, x, y: order.append("snap") or snap0(s, x, y)
    p.DoAttack = lambda s, f: order.append("attack") or attack0(s, f)
    go(lua, p, mode="unaimed_snap", targetId=7, ticks=3)
    run(lua, p, 3, w=w)
    assert order == ["snap", "snap", "snap", "attack"] and len(w["presses"]) == 1
    run(lua, p, 1, w=w)
    end = done(lua, fs)["result"]
    assert end["pressed"] is True and end["press"]["hp0"] == 1.0 and end["press"]["hp1"] == 0.75
    assert end["press"]["cut_by"] == "" and end["press"]["d_press"] == pytest.approx(1.0)
    assert end["press"]["look_off"] == pytest.approx(0.0)                 # the snapped look read on tick 3


def test_unaimed_snap_at_a_point_never_presses(lua, fs):
    load(lua)
    p = make_player()
    go(lua, p, mode="unaimed_snap", x=12.0, y=20.0, ticks=2)
    run(lua, p, 3)
    assert p.attacks == [] and done(lua, fs)["result"]["pressed"] is False


def test_a_refused_press_reads_cut_by_refused(lua, fs):
    p, z, w = make_mover(zx=11.0, zy=20.0)
    w["attack_ticks"] = 0                                                   # isAttackStarted never reads true
    load(lua, [z])
    go(lua, p, mode="snap_aimed", targetId=7, ticks=1)
    run(lua, p, 2, w=w)
    assert done(lua, fs)["result"]["press"]["cut_by"] == "refused"


# ---- block_aim, ignore_aim and turn_k: each flag restored on every end ---------------------------------------------

def test_block_aim_sets_the_posture_and_releases_it_on_done(lua, fs):
    load(lua)
    p = make_player()
    go(lua, p, mode="block_aim", x=12.0, y=20.0, ticks=2)
    run(lua, p, 1)
    assert [c for c in calls(p) if c[0] != "setForceAim"] == [("setBlockMovement", True), ("setIsAiming", True)]
    assert ("setForceAim", False) in calls(p) and lua.eval("PZA.motor.wantAim") is False
    assert p.faced == [(12.0, 20.0)]
    run(lua, p, 2)
    assert calls(p)[-2:] == [("setBlockMovement", False), ("nullifyAiming", None)] and done(lua, fs)["state"] == "done"


def test_block_aim_releases_the_posture_on_a_stop(lua, fs):
    load(lua)
    p = make_player()
    go(lua, p, mode="block_aim", x=12.0, y=20.0, ticks=10)
    run(lua, p, 2)
    start(lua, p, "stop", aid="s1")
    assert done(lua, fs)["reason"] == "superseded"
    assert ("setBlockMovement", False) in calls(p) and calls(p)[-1] == ("nullifyAiming", None)


def test_ignore_aim_holds_the_stance_with_the_input_ignored_and_restores_it(lua, fs):
    load(lua)
    p = make_player()
    go(lua, p, mode="ignore_aim", x=12.0, y=20.0, ticks=2)
    run(lua, p, 1)
    assert ("setIgnoreAimingInput", True) in calls(p) and lua.eval("PZA.motor.wantAim") is True
    run(lua, p, 2)
    assert calls(p, "setIgnoreAimingInput") == [("setIgnoreAimingInput", True), ("setIgnoreAimingInput", False)]
    assert lua.eval("PZA.motor.wantAim") is False


def test_turn_k_writes_k_and_restores_the_read_delta_on_done(lua, fs):
    load(lua)
    p = make_player()
    p.aim["turn"] = 0.8
    go(lua, p, mode="turn_k", x=12.0, y=20.0, ticks=2, k=3.0)
    run(lua, p, 1)
    assert p.aim["turn"] == 3.0 and p.faced == [(12.0, 20.0)] and lua.eval("PZA.motor.wantAim") is False
    run(lua, p, 2)
    assert calls(p, "setTurnDelta") == [("setTurnDelta", 3.0), ("setTurnDelta", 0.8)] and p.aim["turn"] == 0.8
    assert done(lua, fs)["state"] == "done"


def test_turn_k_restores_the_read_delta_on_a_raise_mid_tick(lua, fs):
    """The face write raises on tick 2: the act ends failed interrupted, counted in K.errors, with the delta restored."""
    load(lua)
    p = make_player()
    p.aim["turn"] = 0.8
    face0 = p.faceLocationF
    n = {"i": 0}

    def face(s, x, y):
        n["i"] += 1
        if n["i"] == 2:
            raise RuntimeError("java raised")
        return face0(s, x, y)
    p.faceLocationF = face
    go(lua, p, mode="turn_k", x=12.0, y=20.0, ticks=5, k=3.0)
    run(lua, p, 2)
    end = done(lua, fs)
    assert (end["state"], end["reason"]) == ("failed", "interrupted") and lua.eval("PZA.skills.errors") == 1
    assert calls(p, "setTurnDelta") == [("setTurnDelta", 3.0), ("setTurnDelta", 0.8)]
    assert end["result"]["ticks"] == 2 and lua.eval("PZA.skills.cur") is None


def test_a_supersede_releases_the_stance_of_an_aimed_mode(lua, fs):
    load(lua)
    p = make_player()
    go(lua, p, mode="read", x=12.0, y=20.0, ticks=10)
    run(lua, p, 2)
    go(lua, p, aid="p2", mode="unaimed_face", x=12.0, y=20.0, ticks=10)
    assert done(lua, fs)["reason"] == "superseded" and lua.eval("PZA.motor.wantAim") is False
    assert ("nullifyAiming", None) in calls(p)


# ---- the back-pedal ------------------------------------------------------------------------------------------------

def test_a_back_pedal_walks_the_vector_in_input_space_and_clears_it(lua, fs):
    load(lua)
    p = make_player()
    go(lua, p, mode="read", x=12.0, y=20.0, ticks=2, vx=-1.0, vy=0.0)
    run(lua, p, 1)
    dirs = [v for n, v in p.sets if n == "setAutoWalkDirection"]
    assert ("setAutoWalk", True) in p.sets and len(dirs) == 1
    r2 = 1 / math.sqrt(2)
    assert (dirs[0].x, dirs[0].y) == pytest.approx((-r2, -r2))              # K.inputVector(-1, 0)
    run(lua, p, 2)
    assert ("setAutoWalk", False) in p.sets[p.sets.index(("setAutoWalk", True)) + 1:] and p.motor["autoWalk"] is False


# ---- the index check and the target on the player's square ---------------------------------------------------------

@pytest.mark.parametrize("mode, member", [("read", "getTwist"), ("snap_aimed", "setTargetAndCurrentDirection"),
                                          ("block_aim", "setBlockMovement"), ("ignore_aim", "setIgnoreAimingInput"),
                                          ("turn_k", "getTurnDelta"), ("unaimed_face", "faceLocationF")])
def test_an_absent_member_fails_not_loaded_naming_it_with_nothing_written(lua, fs, mode, member):
    load(lua)
    p = make_player()
    setattr(p, member, None)
    go(lua, p, mode=mode, x=12.0, y=20.0, ticks=2, k=2.0)
    run(lua, p, 1)
    end = done(lua, fs)
    assert (end["state"], end["reason"], end["result"]["missing"]) == ("failed", "not loaded", member)
    assert calls(p) == [] and p.faced == [] and lua.eval("PZA.motor.wantAim") is False


def test_without_vector2_the_probe_fails_not_loaded(lua, fs):
    load(lua)
    lua.globals().Vector2 = None
    p = make_player()
    go(lua, p, mode="read", x=12.0, y=20.0, ticks=2)
    run(lua, p, 1)
    assert done(lua, fs)["result"]["missing"] == "Vector2.new"


def test_a_target_on_the_player_holds_the_last_bearing_and_writes_no_face(lua, fs):
    load(lua)
    p = make_player()
    pos = {"x": 10.0}
    p.getX = lambda s: pos["x"]
    go(lua, p, mode="unaimed_face", x=12.0, y=20.0, ticks=3)
    run(lua, p, 1)
    pos["x"] = 12.0                                                         # the player now stands on the point
    run(lua, p, 2)
    steps = progress(lua, fs)
    assert p.faced == [(12.0, 20.0)] and [s["b"] for s in steps] == [0.0, 0.0, 0.0]


# ---- the summary ---------------------------------------------------------------------------------------------------

def test_the_summary_medians_and_p90s_over_a_known_series(lua, fs):
    """Ten ticks whose body errors are 6, 11, ..., 51 degrees (nearest rank: the median the 5th, 26; p90 the 9th, 46),
    the look errors their negatives (absolute values ranked), hold30 the five under 30, aiming on the even ticks."""
    load(lua)
    p = make_player()
    errs = [5.0 * i + 1 for i in range(1, 11)]

    def between(i):
        p.angles.update(body=math.radians(errs[i - 1]), look=-math.radians(errs[i - 1]))
        p.aim["aiming"] = i % 2 == 0
    go(lua, p, mode="unaimed_face", x=12.0, y=20.0, ticks=10)
    run(lua, p, 11, between=lambda i: between(min(i, 10)))
    r = done(lua, fs)["result"]
    assert r["ticks"] == 10
    assert r["err_body_med"] == pytest.approx(26.0) and r["err_body_p90"] == pytest.approx(46.0)
    assert r["err_look_med"] == pytest.approx(26.0) and r["err_look_p90"] == pytest.approx(46.0)
    assert r["hold30"] == pytest.approx(0.5) and r["aiming_share"] == pytest.approx(0.5)


def test_the_act_lines_decode_and_carry_only_the_schemas_keys(lua, fs):
    with open(SCHEMA, encoding="utf-8") as fh:
        d = json.load(fh)["$defs"]
    p, z, w = make_mover(zx=11.0, zy=20.0)
    load(lua, [z])
    go(lua, p, mode="snap_aimed", targetId=7, ticks=2)
    run(lua, p, 3, w=w)
    ls = lines(lua, fs)
    assert [a["state"] for a in ls] == ["accepted", "progress", "progress", "done"]
    for a in ls[1:3]:
        assert set(a["result"]) <= set(d["result_probe_step"]["properties"])
    assert set(ls[-1]["result"]) <= set(d["result_probe"]["properties"])
    assert set(ls[-1]["result"]["press"]) <= set(d["result_probe"]["properties"]["press"]["properties"])
    assert pza1.Probe(mode="snap_aimed", targetId=7, ticks=2).args()["ticks"] == 2


def test_the_probe_file_keeps_the_kahlua_rules():
    with open(lua_file("client/PZAgent_FacingProbe.lua"), encoding="utf-8") as fh:
        code = "\n".join(line.split("--", 1)[0] for line in fh.read().splitlines())   # the code, comments dropped
    assert "goto" not in code and "%d" not in code and "%g" not in code.lower() and "string.format" not in code
