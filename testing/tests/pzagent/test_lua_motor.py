"""PZAgent_Motor.lua (Plan 22 probe X1, Task 3): the OnPlayerUpdate handler re-asserts the run latches a skill's gait
wants (MO.want), every call, on the player it is given, reads back what the frame ended with, and MO.off clears them."""
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
