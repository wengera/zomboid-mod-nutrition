"""PZAgent_Motor.lua (Plan 22 probe X1, Task 3): the OnPlayerUpdate handler re-asserts the run latches a skill's gait
wants (MO.want), every call, on the player it is given, reads back what the frame ended with, and MO.off clears them."""
import math

import pytest

from .conftest import lua_file, make_player, J


def load(lua):
    for f in ("client/PZAgent_Link.lua", "client/PZAgent_Motor.lua"):
        lua.execute(open(lua_file(f), encoding="utf-8").read())


def fire(lua, p, n=1):
    for _ in range(n):
        lua.globals()._updHandlers[0](p)


def test_the_handler_is_hooked_once_and_counts_its_calls(lua):
    load(lua)
    lua.execute(open(lua_file("client/PZAgent_Motor.lua"), encoding="utf-8").read())   # a reload adds nothing
    g = lua.globals()
    assert len(g._updHandlers) == 1 and lua.eval("PZA.motor.hooked") is True
    assert lua.eval("PZA.motor.wantRun") is False and lua.eval("PZA.motor.wantSprint") is False
    assert lua.eval("PZA.motor.forceRun") is None and lua.eval("PZA.motor.toggleWas") is None
    fire(lua, make_player(), 3)
    assert lua.eval("PZA.motor.upd") == 3 and lua.eval("PZA.motor.updErrors") == 0


def test_want_run_asserts_force_run_every_call_and_never_force_sprint(lua):
    load(lua)
    p = make_player()
    fire(lua, p, 2)
    assert p.sets == []
    lua.execute("PZA.motor.want('run')")
    assert lua.eval("PZA.motor.wantRun") is True and lua.eval("PZA.motor.wantSprint") is False
    fire(lua, p, 4)
    assert p.sets == [("setForceRun", True)] * 4


def test_want_sprint_asserts_both_every_call(lua):
    load(lua)
    p = make_player()
    lua.execute("PZA.motor.want('sprint')")
    fire(lua, p, 2)
    assert p.sets == [("setForceRun", True), ("setForceSprint", True)] * 2


def test_want_walk_asserts_nothing(lua):
    load(lua)
    p = make_player()
    lua.execute("PZA.motor.want('sprint'); PZA.motor.want('walk')")
    assert lua.eval("PZA.motor.wantRun") is False and lua.eval("PZA.motor.wantSprint") is False
    fire(lua, p, 3)
    assert p.sets == []


def test_off_clears_the_latches_once_and_stops_the_asserts(lua):
    load(lua)
    p = make_player()
    lua.execute("PZA.motor.want('sprint')")
    fire(lua, p)
    del p.sets[:]
    lua.eval("PZA.motor.off")(p)
    assert p.sets == [("setForceRun", False), ("setForceSprint", False), ("setAutoWalk", False)]
    assert lua.eval("PZA.motor.wantRun") is False and lua.eval("PZA.motor.wantSprint") is False
    fire(lua, p, 3)
    assert len(p.sets) == 3


def boom(*a):
    raise RuntimeError("java raised")


def test_off_guards_each_setter_so_a_raising_one_leaves_the_others_cleared_and_is_counted(lua):
    """Fix wave M1: MO.off owns the per-setter guard (S-15) the runner's offSafely duplicated."""
    load(lua)
    p = make_player()
    lua.execute("PZA.motor.want('sprint')")
    p.setForceRun = boom
    n, err = lua.eval("PZA.motor.off")(p)
    assert p.sets == [("setForceSprint", False), ("setAutoWalk", False)]
    assert n == 1 and "java raised" in err and lua.eval("PZA.motor.offErrors") == 1
    assert lua.eval("PZA.motor.wantRun") is False and lua.eval("PZA.motor.wantSprint") is False
    p2 = make_player()
    assert lua.eval("PZA.motor.off")(p2)[0] == 0 and lua.eval("PZA.motor.offErrors") == 1


def test_the_reads_land_after_the_asserts_and_an_absent_member_leaves_nil(lua):
    load(lua)
    p = make_player()
    p.IsRunning = lambda s: p.motor["forceRun"]      # the frame runs once the latch is in
    lua.execute("PZA.motor.want('run')")
    fire(lua, p)
    assert lua.eval("PZA.motor.updRunning") is True and lua.eval("PZA.motor.updForceRun") is True
    assert lua.eval("PZA.motor.updSprinting") is False
    del p.isSprinting
    fire(lua, p)
    assert lua.eval("PZA.motor.updSprinting") is None


def test_the_handler_acts_on_its_argument_never_get_player(lua):
    load(lua)
    other = make_player()
    lua.globals().getPlayer = lambda: other
    p = make_player()
    lua.execute("PZA.motor.want('run')")
    fire(lua, p)
    assert p.sets == [("setForceRun", True)] and other.sets == []


def test_a_raising_member_counts_one_error_and_the_handler_keeps_running(lua):
    load(lua)
    p = make_player()
    boom = {"on": True}

    def raising(s, v):
        if boom["on"]:
            raise RuntimeError("setForceRun raised")
        p.sets.append(("setForceRun", v))
    p.setForceRun = raising
    lua.execute("PZA.motor.want('run')")
    fire(lua, p)                                     # a raise out of the handler would fail the test here
    assert lua.eval("PZA.motor.updErrors") == 1 and lua.eval("PZA.motor.upd") == 1
    boom["on"] = False
    fire(lua, p)
    assert lua.eval("PZA.motor.updErrors") == 1 and p.sets == [("setForceRun", True)]


def test_a_player_without_the_latch_members_never_raises(lua):
    load(lua)
    lua.execute("pcallFails = 0\n"
                "local rawPcall = pcall\n"
                "pcall = function(...)\n"
                "    local r = { rawPcall(...) }\n"
                "    if not r[1] then pcallFails = pcallFails + 1 end\n"
                "    return unpack(r)\n"
                "end")
    p = J(getX=lambda s: 1.0)
    lua.execute("PZA.motor.want('sprint')")
    fire(lua, p, 2)
    lua.eval("PZA.motor.off")(p)
    assert lua.eval("PZA.motor.updErrors") == 0 and lua.globals().pcallFails == 0
    assert lua.eval("PZA.motor.updRunning") is None and lua.eval("PZA.motor.updForceRun") is None


def test_update_reads_force_sprint_after_its_asserts(lua):
    """Plan 22 Task 5: the frame's me.forceSprint is MO.updForceSprint, read after the asserts like the other three."""
    load(lua)
    p = make_player()
    lua.execute("PZA.motor.want('sprint')")
    fire(lua, p)
    assert lua.eval("PZA.motor.updForceSprint") is True
    lua.execute("PZA.motor.want('walk')")
    p.motor["forceSprint"] = False
    fire(lua, p)
    assert lua.eval("PZA.motor.updForceSprint") is False
    del p.isForceSprint
    fire(lua, p)
    assert lua.eval("PZA.motor.updForceSprint") is None


# ---- PZA/1.9 (Plan 30 Task 1): the sneak flag, written once per transition -------------------------------------------

def test_the_sneak_want_starts_false_and_writes_nothing_while_the_flag_agrees(lua):
    load(lua)
    p = make_player()
    assert lua.eval("PZA.motor.wantSneak") is False
    fire(lua, p, 3)
    assert p.sneak["sets"] == [] and p.sets == []


def test_a_sneak_want_writes_the_flag_once_on_the_transition_and_never_again_while_it_holds(lua):
    """The flag is a stored field nothing clears (the jar read's #4654): one setSneaking per transition, never per
    frame."""
    load(lua)
    p = make_player()
    lua.execute("PZA.motor.sneak(true)")
    assert lua.eval("PZA.motor.wantSneak") is True and p.sneak["sets"] == []   # no player given: the frame writes it
    fire(lua, p, 5)
    assert p.sneak["sets"] == [True] and p.sneak["on"] is True
    lua.execute("PZA.motor.sneak(true)")                         # the same want again changes nothing
    fire(lua, p, 3)
    assert p.sneak["sets"] == [True]
    lua.execute("PZA.motor.sneak(false)")
    fire(lua, p, 4)
    assert p.sneak["sets"] == [True, False] and p.sneak["on"] is False
    assert p.sets == []                                          # no latch was touched


def test_a_sneak_given_the_player_writes_at_once_and_the_frame_adds_nothing(lua):
    load(lua)
    p = make_player()
    lua.eval("PZA.motor.sneak")(True, p)
    assert p.sneak["sets"] == [True]
    fire(lua, p, 3)
    assert p.sneak["sets"] == [True]
    lua.eval("PZA.motor.sneak")(False, p)
    lua.eval("PZA.motor.sneak")(False, p)
    assert p.sneak["sets"] == [True, False]


def test_off_leaves_the_sneak_want_and_the_flag(lua):
    """A stop or a supersede ends a walk, never the sneak: MO.off clears the latches only."""
    load(lua)
    p = make_player()
    lua.execute("PZA.motor.sneak(true); PZA.motor.want('run')")
    fire(lua, p)
    lua.eval("PZA.motor.off")(p)
    assert lua.eval("PZA.motor.wantSneak") is True and p.sneak["on"] is True
    assert ("setSneaking", False) not in p.sets and p.sneak["sets"] == [True]
    fire(lua, p, 3)
    assert p.sneak["sets"] == [True]


def test_a_flag_flipped_outside_the_motor_is_written_back_once(lua):
    """A crouch-key toggle or a save load writes the field (#4654); the next frame restores the want, once."""
    load(lua)
    p = make_player()
    lua.execute("PZA.motor.sneak(true)")
    fire(lua, p)
    p.sneak["on"] = False
    fire(lua, p, 3)
    assert p.sneak["sets"] == [True, True]


def test_the_sneak_is_written_under_the_stance_too(lua):
    load(lua)
    p = make_player()
    lua.execute("PZA.motor.wantAim = true; PZA.motor.sneak(true)")
    fire(lua, p, 2)
    assert p.sneak["sets"] == [True] and p.aim["calls"] == [("setForceAim", True)] * 2


def test_a_player_without_the_sneak_members_is_never_written_and_nothing_raises(lua):
    load(lua)
    lua.execute(PCALL_COUNTER)
    p = make_player()
    del p.isSneaking                                             # unreadable: no write on a guess
    lua.execute("PZA.motor.sneak(true)")
    fire(lua, p, 3)
    assert p.sneak["sets"] == []
    q = J(getX=lambda s: 1.0)
    fire(lua, q, 2)
    lua.eval("PZA.motor.sneak")(False, q)
    assert lua.eval("PZA.motor.updErrors") == 0 and lua.globals().pcallFails == 0


def test_a_raising_sneak_setter_counts_one_error_and_the_latches_are_still_asserted(lua):
    load(lua)
    p = make_player()
    p.setSneaking = boom
    lua.execute("PZA.motor.want('run'); PZA.motor.sneak(true)")
    fire(lua, p)
    assert p.sets == [("setForceRun", True)] and lua.eval("PZA.motor.updErrors") == 1
    assert lua.eval("PZA.motor.updRunning") is False             # the reads after the latches still landed


PCALL_COUNTER = ("pcallFails = 0; local raw = pcall; pcall = function(...) local r = { raw(...) };"
                 " if not r[1] then pcallFails = pcallFails + 1 end; return unpack(r) end")


def test_a_setter_raising_sneak_raises_times_in_a_row_drops_the_want_to_the_flag(lua):
    """Review-t1 minor 3: after MO.SNEAK_RAISES raises in a row the want drops to the flag as read, so the Motor stops
    trying; every raise stays counted in updErrors."""
    load(lua)
    p = make_player()
    tries = []

    def raising(s, v):
        tries.append(v)
        raise RuntimeError("setSneaking raised")
    p.setSneaking = raising
    assert lua.eval("PZA.motor.SNEAK_RAISES") == 3
    lua.execute("PZA.motor.sneak(true)")
    fire(lua, p, 2)
    assert tries == [True, True] and lua.eval("PZA.motor.wantSneak") is True
    fire(lua, p, 4)
    assert tries == [True] * 3 and lua.eval("PZA.motor.wantSneak") is False
    assert lua.eval("PZA.motor.updErrors") == 3 and lua.eval("PZA.motor.sneakRaises") == 0
    lua.execute("PZA.motor.sneak(true)")                          # a new want tries again
    fire(lua, p)
    assert tries == [True] * 4 and lua.eval("PZA.motor.sneakRaises") == 1


def test_a_write_that_runs_resets_the_raise_count(lua):
    load(lua)
    p = make_player()
    boom = {"on": True}

    def flaky(s, v):
        if boom["on"]:
            raise RuntimeError("setSneaking raised")
        p.sneak["on"] = v
    p.setSneaking = flaky
    lua.execute("PZA.motor.sneak(true)")
    fire(lua, p, 2)
    boom["on"] = False
    fire(lua, p)
    assert p.sneak["on"] is True and lua.eval("PZA.motor.sneakRaises") == 0 and lua.eval("PZA.motor.wantSneak") is True


# ---- the idle snap (Plan 33 Task 1: F18's visual pass, the body turned away from the nearest zombie between presses) --

def idle_world(lua, zx=11.5, zy=20.0, **kw):
    """Every client file loaded (the melee's FACING.idle beside the Motor), a mover with zombie 7 at (zx, zy) and the
    last frame listing it at its distance."""
    from .test_lua_melee import frame_last, world
    p, z, w = world(lua, zx=zx, zy=zy, **kw)
    frame_last(lua, [(7, ((zx - 10.0) ** 2 + (zy - 20.0) ** 2) ** 0.5)], objs={7: z})
    return p, z, w


def frame(lua, p, n=1):
    for _ in range(n):
        lua.eval("PZA.motor.onPlayerUpdate")(p)


def idle_snaps(p):
    return [v for k, v in p.aim["calls"] if k == "setTargetAndCurrentDirection"]


def test_the_idle_snap_turns_the_body_onto_a_standing_zombie_within_the_radius_every_frame(lua):
    """No skill running and a standing zombie at 1.5 tiles: each frame snaps body and facing onto its bearing (the
    aim posture untouched: no setForceAim written with no stance wanted)."""
    p, z, w = idle_world(lua, zx=11.5, zy=21.5)
    frame(lua, p, 3)
    b = (1 / 2 ** 0.5, 1 / 2 ** 0.5)
    assert idle_snaps(p) == [pytest.approx(b)] * 3 and w["look"] == pytest.approx(math.pi / 4)
    assert [c for c in p.aim["calls"] if c[0] == "setForceAim"] == []
    assert lua.eval("PZA.motor.updErrors") == 0


def test_the_idle_snap_keeps_a_held_stance_s_aim(lua):
    """With the stance wanted (MO.wantAim) the Motor asserts the force-aim as before and the snap rides beside it."""
    p, z, w = idle_world(lua)
    lua.execute("PZA.motor.wantAim = true")
    frame(lua, p, 2)
    assert [c[0] for c in p.aim["calls"]] == ["setForceAim", "setTargetAndCurrentDirection"] * 2
    assert p.aim["force"] is True


def test_a_zombie_beyond_the_radius_is_never_snapped_onto(lua):
    p, z, w = idle_world(lua, zx=13.0)
    frame(lua, p, 3)
    assert idle_snaps(p) == []


def test_the_nearest_standing_zombie_is_the_one_snapped_onto(lua):
    """Two standing (7 at 2.0 tiles due +x, 8 at 1.0 due +y) and a fallen one (9 at 0.5 due -x): the snap goes to 8."""
    from .conftest import make_zombie
    from .test_lua_melee import frame_last
    p, z, w = idle_world(lua, zx=12.0)
    o8, o9 = make_zombie(8, 10.0, 21.0), make_zombie(9, 9.5, 20.0)
    o9.isOnFloor = lambda s: True
    frame_last(lua, [(9, 0.5), (8, 1.0), (7, 2.0)], objs={7: z, 8: o8, 9: o9})
    frame(lua, p)
    assert idle_snaps(p) == [pytest.approx((0.0, 1.0))]


def test_a_dead_or_fallen_zombie_alone_is_never_snapped_onto(lua):
    p, z, w = idle_world(lua)
    w["floor"] = True
    frame(lua, p)
    w["floor"], w["zdead"] = False, True
    frame(lua, p)
    assert idle_snaps(p) == []


def test_a_running_steer_or_walk_owns_the_facing_and_the_idle_snap_writes_nothing(lua):
    from .test_lua_skills import start
    p, z, w = idle_world(lua)
    start(lua, p, "steer", aid="s", vx=-1, vy=0, seconds=5)
    frame(lua, p, 3)
    assert idle_snaps(p) == []


def test_a_run_latch_wanted_with_no_skill_writes_no_idle_snap(lua):
    p, z, w = idle_world(lua)
    lua.execute("PZA.motor.want('run')")
    frame(lua, p, 2)
    assert idle_snaps(p) == []


def test_a_running_melee_leaves_the_snap_to_the_melee(lua):
    """A melee running: the Motor's frame writes no snap (the melee's own tick snaps, at its press and through its
    stance)."""
    from .test_lua_melee import go
    p, z, w = idle_world(lua)
    go(lua, p)
    frame(lua, p, 3)
    assert idle_snaps(p) == []


def test_the_idle_snap_is_off_with_its_switch_and_silent_with_no_frame(lua):
    p, z, w = idle_world(lua)
    lua.execute("PZA.skills.IDLE_SNAP = false")
    frame(lua, p, 2)
    assert idle_snaps(p) == []
    lua.execute("PZA.skills.IDLE_SNAP = true; PZA.sense.last = nil")
    frame(lua, p, 2)
    assert idle_snaps(p) == [] and lua.eval("PZA.motor.updErrors") == 0


def test_a_player_without_the_snap_member_is_never_snapped_reads_nothing_and_nothing_raises(lua):
    """The index check: the snap member absent on the first idle frame, no position is read on any frame."""
    from .test_lua_stance import Rec
    p, z, w = idle_world(lua)
    p.setTargetAndCurrentDirection = None
    log = []
    frame(lua, Rec(p, log, "p"), 2)
    assert lua.eval("PZA.motor.updErrors") == 0 and p.aim["calls"] == []
    assert ("p", "getX") not in log


def test_the_idle_snap_s_frame_cost(lua):
    """The bench (Java calls a frame through Rec): the Motor's frame alone reads its five members; idle near a standing
    zombie it adds the two player positions, the zombie's two positions, isDead, isOnFloor and the snap (7); the snap
    member is index-checked on the first frame only, and a record the frame lists beyond the radius and its slack
    (zombie 8 at 5 tiles) is never read."""
    from .conftest import make_zombie
    from .test_lua_melee import frame_last
    from .test_lua_stance import Rec
    p, z, w = idle_world(lua)
    frame(lua, p)                                                     # the index check, once
    log = []
    o8 = Rec(make_zombie(8, 15.0, 20.0), log, "z8")
    frame_last(lua, [(7, 1.5), (8, 5.0)], objs={7: Rec(z, log, "z"), 8: o8})
    frame(lua, Rec(p, log, "p"))
    idle = [("p", "getX"), ("p", "getY"), ("z", "getX"), ("z", "getY"), ("z", "isDead"), ("z", "isOnFloor"),
            ("p", "setTargetAndCurrentDirection")]
    base = [("p", "IsRunning"), ("p", "isForceRun"), ("p", "isSprinting"), ("p", "isForceSprint"), ("p", "isSneaking")]
    assert sorted(log) == sorted(base + idle), log
    del log[:]
    lua.execute("PZA.skills.IDLE_SNAP = false")
    frame(lua, Rec(p, log, "p"))
    assert sorted(log) == sorted(base)
