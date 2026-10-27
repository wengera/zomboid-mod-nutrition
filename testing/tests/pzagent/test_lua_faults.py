"""The Lua fault-injection test (Plan 22 Task 9b, on the lupa host): every skill of PZAgent_Skills.lua, started with valid
args, against (a) a bare player exposing no member but getX/getY/getZ, (b) a player whose every member raises, and (d) a
full player with every vanilla class it may reach set to nil; (c) S.frame on (a) and (b); Main's tick once on each.

What each case asserts:
- (a) and (d): the skill's last act line is rejected or failed with a reason in the schema's enum (stop, whose interface
  is done, is done; attack in reach needs no vanilla class and swings), nothing raised, the runner idle, and no caught
  raise anywhere: a pcall-counting wrapper (test_lua_motor.py's) counts every pcall that returns false, which must stay
  0, since a caught raise still parks the -debug client (#0957) and the skills' paths are index-first.
- (b): a raise inside the Java stub is expected; the assertion is only that it never propagates out of K.start or K.tick,
  that the runner counts it (K.errors) and that the skill ends rejected or failed with a reason in the enum.
- (c): S.frame returns every group present, the unreadable fields nil, and S.missing non-empty; the frame encodes
  through the Link and decodes through pza1.
- Main: one OnTick after an init with a full player, the player then swapped for the fault player, each command type of
  PZA.schema.actions in cmd.txt: nothing propagates out of the handler and at most one lua_error event lands.

The cases marked xfail(strict=True) are the Lua's findings at 420d91c2, each named in its reason: when the Lua is fixed the
strict xfail turns into a failure and the marker comes off.
"""
import json

import pytest

from agent.base import pza1
from .conftest import FakeFS, J, lua_file, make_cell, make_lua, make_player, make_weapon, make_zombie

LIVE = "pzagent/admin/state.log"
CMD = "pzagent/admin/cmd.txt"
SKILL_FILES = ("client/PZAgent_Link.lua", "client/PZAgent_Motor.lua", "client/PZAgent_Sense.lua",
               "client/PZAgent_Skills.lua")
MAIN_FILES = ("client/PZAgent_Link.lua", "client/PZAgent_Main.lua", "client/PZAgent_Map.lua",
              "client/PZAgent_Motor.lua", "client/PZAgent_Sense.lua", "client/PZAgent_Skills.lua")
VANILLA = ("ISTimedActionQueue", "ISWalkToTimedAction", "ISOpenCloseDoor", "ISOpenCloseWindow",
           "ISInventoryTransferAction", "ISEatFoodAction", "ISDrinkFluidAction", "ISDropWorldItemAction",
           "ISEquipWeaponAction", "Vector2")
MAIN_TYPES = ("scan", "rate")          # answered by Main, never the runner (ruling P22-5)

# valid args for every action type of the schema; a case name maps to its type (interact and consume take two)
VALID = {
    "walkTo": ("walkTo", {"x": 12, "y": 20, "gait": "walk"}),
    "steer": ("steer", {"vx": 1.0, "vy": 0.0, "seconds": 1.0, "gait": "run"}),
    "attack": ("attack", {"targetId": 5}),
    "open": ("interact", {"x": 11, "y": 20, "kind": "open", "filter": "all"}),
    "loot": ("interact", {"x": 11, "y": 20, "kind": "loot", "filter": "all"}),
    "equip": ("equip", {"itemId": 1001}),
    "eat": ("consume", {"itemId": 1000}),
    "drink": ("consume", {"itemId": 1002}),
    "drop": ("drop", {"itemId": 1000}),
    "stop": ("stop", {}),
    "scan": ("scan", {"r": 3}),
    "rate": ("rate", {"hz": 5}),
}
SKILL_CASES = [c for c, (t, _) in VALID.items() if t not in MAIN_TYPES]
PCALL_COUNTER = ("pcallFails = 0; local raw = pcall; pcall = function(...) local r = { raw(...) };"
                 " if not r[1] then pcallFails = pcallFails + 1 end; return unpack(r) end")


class Raising:
    """A Java-like object whose every member raises when called (a Java exception reaches Kahlua as a Lua error)."""
    def __getattr__(self, name):
        if name.startswith("__"):
            raise AttributeError(name)

        def raises(*a):
            raise RuntimeError("java raised: " + name)
        return raises


def bare_player():
    return J(getX=lambda s: 10.0, getY=lambda s: 20.0, getZ=lambda s: 0)


def full_player():
    """A player holding Bread (1000, food), Hammer (1001) and WaterBottle (1002, clean water), a bat in hand."""
    return make_player(items=("Base.Bread", "Base.Hammer", "Base.WaterBottle"), weapon=make_weapon())


def world(g, zombie_x=11.0):
    """A cell of open squares round (10, 20), each holding a shut door and a container of one apple, zombie 5 at
    (zombie_x, 20)."""
    door = J(_cls="IsoDoor", IsOpen=lambda s: False, isBarricaded=lambda s: False)
    box = J(getItems=lambda s: J(size=lambda s2: 1, get=lambda s2, i: J(getFullType=lambda s3: "Base.Apple")))
    objs = [door, J(getContainer=lambda s: box)]
    sq = J(getObjects=lambda s: J(size=lambda s2: len(objs), get=lambda s2, i: objs[i]),
           isSolid=lambda s: False, isSolidTrans=lambda s: False, getX=lambda s: 0, getY=lambda s: 0,
           getZ=lambda s: 0)
    g._cell = make_cell([make_zombie(5, zombie_x, 20.0)], {(x, y, 0): sq for x in range(6, 16) for y in range(15, 26)})


def skills_host(zombie_x=11.0):
    fs = FakeFS()
    lua = make_lua(fs)
    for f in SKILL_FILES:
        lua.execute(open(lua_file(f), encoding="utf-8").read())
    g = lua.globals()
    g.PZA.tick = 0
    lua.execute("PZA.link.init('admin')")
    world(g, zombie_x)
    return lua, fs, g


def act_lines(lua, fs):
    lua.execute("PZA.link.flush()")
    out = []
    for l in fs.files.get(LIVE, "").split("\n"):
        if l.strip():
            line = pza1.decode(json.loads(l))
            if line["kind"] == "act":
                out.append(line)
    return out


def drive(lua, g, p, case, ticks=400, jump_at=5):
    """Start the case's command and tick the runner; the clock jumps 30 s at tick `jump_at` so every wall budget
    (OPEN_MS, CONSUME_MS, APPROACH_MS, steer's seconds) runs out. Returns the act lines."""
    typ, args = VALID[case]
    cmd = lua.table_from({"seq": 1, "aid": "a1", "type": typ, "args": args}, recursive=True)
    lua.eval("PZA.skills.start")(cmd, p)
    for i in range(ticks):
        if lua.eval("PZA.skills.cur") is None:
            break
        if i == jump_at:
            g._clock["ms"] += 30000
        lua.eval("PZA.skills.tick")(p)


def ended(lines):
    """The terminal act line (rejected, failed or done) of aid a1, asserting there is exactly one."""
    ends = [l for l in lines if l["aid"] == "a1" and l["state"] in ("rejected", "failed", "done")]
    assert len(ends) == 1, [(l["state"], l["reason"]) for l in lines]
    return ends[0]


def assert_failed_in_enum(end):
    assert end["state"] in ("rejected", "failed"), (end["state"], end["reason"])
    assert end["reason"] in pza1.REASONS, end["reason"]


def test_the_cases_cover_every_action_type_of_the_schema():
    lua = make_lua(FakeFS())
    for f in SKILL_FILES:
        lua.execute(open(lua_file(f), encoding="utf-8").read())
    schema = set(lua.eval("PZA.schema.actions").keys())
    skills = set(lua.eval("PZA.skills.types").keys())
    assert schema == set(pza1.ACTION_TYPES) == {t for t, _ in VALID.values()}
    assert skills | set(MAIN_TYPES) == schema and not skills & set(MAIN_TYPES)


def test_the_pcall_counter_counts_a_caught_raise():
    lua = make_lua(FakeFS())
    lua.execute(PCALL_COUNTER)
    lua.execute("pcall(error, 'x'); pcall(tostring, 1)")
    assert lua.globals().pcallFails == 1


# ---- (a) a bare player ---------------------------------------------------------------------------------------------

STEER_BARE = pytest.mark.xfail(strict=True, raises=AssertionError, reason=(
    "Lua finding: steer on a player without setAutoWalk/setAutoWalkDirection reports done (PZA.call answers false "
    "silently and the skill never checks it), so a skill that never steered reads as a success"))


@pytest.mark.parametrize("case", [pytest.param(c, marks=STEER_BARE) if c == "steer" else c for c in SKILL_CASES])
def test_a_bare_player_ends_rejected_or_failed_with_no_raise(case):
    lua, fs, g = skills_host()
    lua.execute(PCALL_COUNTER)
    p = bare_player()
    drive(lua, g, p, case)
    end = ended(act_lines(lua, fs))
    if case == "stop":
        assert end["state"] == "done"                     # stop's interface: it clears what is there and is done
    else:
        assert_failed_in_enum(end)
    assert lua.eval("PZA.skills.cur") is None
    assert lua.eval("PZA.skills.errors") == 0 and g.pcallFails == 0


# ---- (b) a player whose every member raises -------------------------------------------------------------------------

RAISE_FINDING = pytest.mark.xfail(strict=True, raises=RuntimeError, reason=(
    "Lua finding: K.start reads isDead(p) and K.snapshot(p) outside the S-12 pcall, and K.tick's finish emits its "
    "snapshot outside it too (leaving K.cur set), so a raising player's error propagates out of the runner"))


@RAISE_FINDING
@pytest.mark.parametrize("case", SKILL_CASES)
def test_a_raising_player_never_propagates_and_the_runner_counts_it(case):
    lua, fs, g = skills_host()
    p = Raising()
    drive(lua, g, p, case, ticks=5)
    end = ended(act_lines(lua, fs))
    assert_failed_in_enum(end)
    assert lua.eval("PZA.skills.cur") is None and lua.eval("PZA.skills.errors") >= 1


# ---- (c) S.frame ----------------------------------------------------------------------------------------------------

def test_s_frame_on_a_bare_player_has_every_group_with_nil_fields_and_names_the_missing():
    lua, fs, g = skills_host()
    lua.execute(PCALL_COUNTER)
    f = lua.eval("PZA.sense.frame")(bare_player())
    for grp in ("me", "stats", "body", "load"):
        assert f[grp] is not None, grp
    assert (f.me.x, f.me.y, f.me.z) == (10.0, 20.0, 0) and f.me.dir is None and f.me.moving is None
    assert f.stats.hunger is None and f.body.health is None and f.load.weight is None and f.load.max is None
    assert f.weapon is None and f.act is None
    missing = set(lua.eval("PZA.sense.missing").values())
    assert {"getStats", "getBodyDamage", "getInventory", "getPrimaryHandItem", "getDir"} <= missing
    lua.eval("PZA.emitFrame")(f)                              # encodes through the Link, decodes through pza1
    lua.execute("PZA.link.flush()")
    frames = [pza1.decode(json.loads(l)) for l in fs.files[LIVE].split("\n") if l.startswith('["frame"')]
    assert len(frames) == 1 and frames[0]["stats"]["hunger"] is None and frames[0]["me"]["x"] == 10
    assert g.pcallFails == 0


@pytest.mark.xfail(strict=True, raises=RuntimeError, reason=(
    "Lua finding: S.frame reads every member through PZA.call with no guard, so a raising player's error propagates "
    "out of S.frame (Main's pcall catches it; the frame is lost)"))
def test_s_frame_on_a_raising_player_returns_a_frame_and_names_the_missing():
    lua, fs, g = skills_host()
    f = lua.eval("PZA.sense.frame")(Raising())
    for grp in ("me", "stats", "body", "load"):
        assert f[grp] is not None, grp
    assert len(list(lua.eval("PZA.sense.missing").values())) > 0


# ---- (d) every vanilla class absent ---------------------------------------------------------------------------------

# the reason each skill's interface gives with its vanilla class absent; attack needs none in reach (it swings), and out
# of reach its approach walk cannot queue, so it runs out its approach budget
ABSENT = {"walkTo": ("failed", "no path"), "steer": ("failed", "not loaded"), "open": ("failed", "not loaded"),
          "loot": ("failed", "not loaded"), "equip": ("failed", "not loaded"), "eat": ("failed", "not loaded"),
          "drink": ("failed", "not loaded"), "drop": ("failed", "not loaded"), "stop": ("done", "")}


@pytest.mark.parametrize("case", SKILL_CASES)
def test_every_vanilla_class_absent_fails_as_the_interface_says_with_no_raise(case):
    lua, fs, g = skills_host()
    p = full_player()
    for name in VANILLA:
        g[name] = None
    lua.execute(PCALL_COUNTER)
    drive(lua, g, p, case)
    end = ended(act_lines(lua, fs))
    want = ("done", "") if case == "attack" else ABSENT[case]
    assert (end["state"], end["reason"]) == want
    assert lua.eval("PZA.skills.cur") is None
    assert lua.eval("PZA.skills.errors") == 0 and g.pcallFails == 0


def test_attack_out_of_reach_with_the_walk_absent_runs_out_its_approach():
    lua, fs, g = skills_host(zombie_x=14.0)
    p = full_player()
    for name in VANILLA:
        g[name] = None
    lua.execute(PCALL_COUNTER)
    drive(lua, g, p, "attack")
    end = ended(act_lines(lua, fs))
    assert (end["state"], end["reason"]) == ("failed", "out of reach")
    assert lua.eval("PZA.skills.errors") == 0 and g.pcallFails == 0


# ---- Main's tick on each fault ---------------------------------------------------------------------------------------

def main_host(fault):
    """Main loaded in the game's order, the init tick run with a full player, then the player swapped for the fault:
    `bare`, `raise`, or `absent` (the full player with every vanilla class nil)."""
    fs = FakeFS()
    lua = make_lua(fs)
    for f in MAIN_FILES:
        lua.execute(open(lua_file(f), encoding="utf-8").read())
    g = lua.globals()
    world(g)
    cur = {"p": full_player()}
    g.getPlayer = lambda: cur["p"]
    g._handlers[0]()                                          # the init tick
    assert lua.eval("PZA.main.ready") is True
    if fault == "bare":
        cur["p"] = bare_player()
    elif fault == "raise":
        cur["p"] = Raising()
    else:
        for name in VANILLA:
            g[name] = None
    return lua, fs, g


@pytest.mark.parametrize("case", list(VALID))
@pytest.mark.parametrize("fault", ["bare", "raise", "absent"])
def test_main_tick_on_each_fault_never_propagates_and_reports_at_most_one_lua_error(fault, case):
    lua, fs, g = main_host(fault)
    if fault != "raise":
        lua.execute(PCALL_COUNTER)
    typ, args = VALID[case]
    fs.files[CMD] = json.dumps({"seq": 1, "aid": "a1", "type": typ, "args": args}) + "\n"
    g._handlers[0]()                                          # a raise out of the handler fails the test here
    lua.execute("PZA.link.flush()")
    lines = [pza1.decode(json.loads(l)) for l in fs.files.get(LIVE, "").split("\n") if l.strip()]
    errors = [l for l in lines if l["kind"] == "event" and l["event"] == "lua_error"]
    assert len(errors) <= 1
    if fault != "raise":
        assert errors == [] and lua.eval("PZA.errors") == 0 and g.pcallFails == 0
        assert [l["state"] for l in lines if l["kind"] == "act" and l["aid"] == "a1"][:1] != []
