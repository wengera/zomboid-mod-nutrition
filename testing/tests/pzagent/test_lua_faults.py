"""The Lua fault-injection test (Plan 22 Task 9b, on the lupa host): every skill of PZAgent_Skills.lua, started with valid
args, against (a) a bare player exposing no member but getX/getY/getZ, (b) a player whose every member raises, and (d) a
full player with every vanilla class it may reach set to nil; (c) S.frame on (a) and (b); Main's tick once on each.

What each case asserts:
- (a) and (d): the skill's last act line is the (state, reason) its interface gives on that fault, pinned per case (stop,
  whose interface is done, is done; attack in reach needs no vanilla class and swings), nothing raised, the runner idle,
  and no caught raise anywhere: a pcall-counting wrapper (test_lua_motor.py's) counts every pcall that returns false, which must stay
  0, since a caught raise still parks the -debug client (#0957) and the skills' paths are index-first.
- (b): a raise inside the Java stub is expected (ruling S-15: a supported fault to contain); the assertion is that it
  never propagates out of K.start or K.tick, that the runner counts it (K.errors) and that the skill ends rejected or
  failed with a reason in the enum; stop, whose only player work is the queue clear already under pcall, ends done.
- (c): S.frame returns every group present, the unreadable fields nil, and S.missing non-empty; the frame encodes
  through the Link and decodes through pza1; on the raising player each group's raise is counted in S.frameErrors.
- Main: one OnTick after an init with a full player, the player then swapped for the fault player, each command type of
  PZA.schema.actions in cmd.txt: nothing propagates out of the handler and at most one lua_error event lands.

The test was committed at eef30811 against the Lua at dd79ed27 with 12 strict xfails naming three defects (a raise
escaping the runner, a raise escaping S.frame, steer without the auto-walk reading as done); Task 9 fix 2 (ruling S-15)
fixed the Lua and took every marker off.
"""
import json

import pytest

from agent.base import pza1
from .conftest import FakeFS, J, lua_file, make_cell, make_lua, make_player, make_weapon, make_zombie

LIVE = "pzagent/admin/state.log"
CMD = "pzagent/admin/cmd.txt"
SKILL_FILES = ("shared/PZAgent_World.lua", "client/PZAgent_Link.lua", "client/PZAgent_Motor.lua",
               "client/PZAgent_Sense.lua", "client/PZAgent_Skills.lua", "client/PZAgent_SkillsWorld.lua",
               "client/PZAgent_Stance.lua", "client/PZAgent_Tend.lua")
MAIN_FILES = ("shared/PZAgent_World.lua", "client/PZAgent_Link.lua", "client/PZAgent_Main.lua",
              "client/PZAgent_Map.lua", "client/PZAgent_Motor.lua", "client/PZAgent_Sense.lua",
              "client/PZAgent_Skills.lua", "client/PZAgent_SkillsWorld.lua",
              "client/PZAgent_Stance.lua", "client/PZAgent_Tend.lua")
VANILLA = ("ISTimedActionQueue", "ISWalkToTimedAction", "ISOpenCloseDoor", "ISOpenCloseWindow",
           "ISInventoryTransferAction", "ISEatFoodAction", "ISDrinkFluidAction", "ISDropWorldItemAction",
           "ISEquipWeaponAction", "Vector2", "ISWorldObjectContextMenu", "UIManager", "ISClimbOverFence",
           "ISApplyBandage", "ISWashClothing", "ISInventoryPaneContextMenu", "ISTakeWaterAction", "ISWearClothing",
           "ISClimbThroughWindow", "ISSmashWindow", "ISUnequipAction")
MAIN_TYPES = ("scan", "rate")          # answered by Main, never the runner (ruling P22-5)
PENDING_TYPES = ()                     # sleep, in the schema since PZA/1.2 (Plan 23 Task 4), got its skill in Task 8

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
    "sleep": ("sleep", {}),
    "aim": ("aim", {"vx": 0.0, "vy": -1.0, "seconds": 1.0, "targetId": -1, "bearing": 90.0}),
    "climb": ("climb", {"x": 11, "y": 20}),
    "bandage": ("bandage", {"itemId": 1003, "part": 0}),
    "rip": ("rip", {"itemId": 1004}),
    "wash": ("wash", {"itemId": 1003, "x": 11, "y": 20}),
    "fill": ("fill", {"itemId": 1002, "x": 11, "y": 20}),
    "wear": ("wear", {"itemId": 1005}),                 # PZA/1.6 (Task 9 fix 9)
    "window": ("window", {"x": 11, "y": 20}),            # PZA/1.6: the shut window on the world's west edge
    "unwear": ("unwear", {"itemId": 1005}),              # PZA/1.7 (Task 9 fix 11)
    "shove": ("shove", {"targetId": 5}),
    "stomp": ("stomp", {"targetId": 5}),
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
    """A player holding Bread (1000, food), Hammer (1001), WaterBottle (1002, clean water), RippedSheetsDirty (1003, a
    dirty rag), Tshirt_DefaultTEXTURE (1004, cotton) and Jacket_Padded (1005, PZA/1.6: a Clothing at base:jacket, not
    worn), a bat in hand."""
    p = make_player(items=("Base.Bread", "Base.Hammer", "Base.WaterBottle", "Base.RippedSheetsDirty",
                           "Base.Tshirt_DefaultTEXTURE", "Base.Jacket_Padded"), weapon=make_weapon())
    p.held[5]._cls, p.held[5].getBodyLocation = "Clothing", lambda s: "base:jacket"
    return p


def world(g, zombie_x=11.0):
    """A cell of open squares round (10, 20), each holding a shut door, a container of one apple and a low fence on its
    west edge (PZA/1.5's climb) and a sink (its wash), zombie 5 at (zombie_x, 20)."""
    door = J(_cls="IsoDoor", IsOpen=lambda s: False, isBarricaded=lambda s: False)
    box = J(getItems=lambda s: J(size=lambda s2: 1, get=lambda s2, i: J(getFullType=lambda s3: "Base.Apple")))
    fence = J(isHoppable=lambda s: True, isTallHoppable=lambda s: False)
    sink = J(hasWater=lambda s: True, getFluidAmount=lambda s: 10000.0, isTaintedWater=lambda s: False,
             isWaterInfinite=lambda s: True, hasFluid=lambda s: True)
    window = J(_cls="IsoWindow", getNorth=lambda s: False, IsOpen=lambda s: False, isSmashed=lambda s: False,
               isLocked=lambda s: False, isPermaLocked=lambda s: False, isBarricaded=lambda s: False,
               canClimbThrough=lambda s, p: False)               # PZA/1.6's window: shut, opens unlocked
    objs = [door, J(getContainer=lambda s: box), fence, sink, window]
    sq = J(getObjects=lambda s: J(size=lambda s2: len(objs), get=lambda s2, i: objs[i]),
           isSolid=lambda s: False, isSolidTrans=lambda s: False, getX=lambda s: 0, getY=lambda s: 0,
           getZ=lambda s: 0)
    g._cell = make_cell([make_zombie(5, zombie_x, 20.0)], {(x, y, 0): sq for x in range(6, 16) for y in range(15, 26)})


def load(lua, files):
    """Executes each client file in order (the game's load order)."""
    for f in files:
        lua.execute(open(lua_file(f), encoding="utf-8").read())


def clear_vanilla(g):
    """Sets every vanilla class a skill may reach to nil."""
    for name in VANILLA:
        g[name] = None


def skills_host(zombie_x=11.0):
    fs = FakeFS()
    lua = make_lua(fs)
    load(lua, SKILL_FILES)
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


JUMP_MS = {"sleep": 3600001, "window": 60001}   # sleep's budget is K.SLEEP_MS, an hour of wall; window's WINDOW_MS


def drive(lua, g, p, case, ticks=400, jump_at=5):
    """Start the case's command and tick the runner; the clock jumps 30 s (JUMP_MS for a longer budget) at tick
    `jump_at` so every wall budget (OPEN_MS, CONSUME_MS, APPROACH_MS, steer's seconds, SLEEP_MS) runs out. Returns None; act_lines reads what it emitted."""
    typ, args = VALID[case]
    cmd = lua.table_from({"seq": 1, "aid": "a1", "type": typ, "args": args}, recursive=True)
    lua.eval("PZA.skills.start")(cmd, p)
    for i in range(ticks):
        if lua.eval("PZA.skills.cur") is None:
            break
        if i == jump_at:
            g._clock["ms"] += JUMP_MS.get(case, 30000)
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
    load(lua, SKILL_FILES)
    schema = set(lua.eval("PZA.schema.actions").keys())
    skills = set(lua.eval("PZA.skills.types").keys())
    assert schema == set(pza1.ACTION_TYPES) == {t for t, _ in VALID.values()} | set(PENDING_TYPES)
    assert skills | set(MAIN_TYPES) | set(PENDING_TYPES) == schema and not skills & set(MAIN_TYPES)


def test_the_pcall_counter_counts_a_caught_raise():
    lua = make_lua(FakeFS())
    lua.execute(PCALL_COUNTER)
    lua.execute("pcall(error, 'x'); pcall(tostring, 1)")
    assert lua.globals().pcallFails == 1


# ---- (a) a bare player ---------------------------------------------------------------------------------------------

# the (state, reason) each skill's interface gives on a player with no member but getX/getY/getZ, pinned so a rejected bad
# args from an args drift cannot pass as the fault path: walkTo never moves (stuck); steer has no auto-walk (not
# loaded); attack holds nothing; open reads the shut door as not opening (locked, at OPEN_MS); loot queues its transfers
# but cannot read the inventory grow, so its budget runs out (interrupted); the item skills find no inventory (none
# held); stop's interface is done; sleep finds no setter to put the player to sleep with (not loaded); aim finds no
# setForceAim (not loaded); climb queues its climb from the near square it stands on and never crosses, its action
# still in the fake's queue by vanilla's hasAction (PZA/1.5.1), so its budget runs out (interrupted); the care skills
# find no inventory (none held), wear (PZA/1.6) too; window (PZA/1.6) queues its open, which the fake queue never
# runs, so its WINDOW_MS runs out (interrupted)
# PZA/1.7: unwear finds no inventory item (none held); shove finds no setDoShove (not loaded); stomp's world zombie
# does not lie on the floor (not valid)
BARE = {"walkTo": ("failed", "stuck"), "steer": ("failed", "not loaded"), "attack": ("rejected", "no weapon"),
        "open": ("failed", "locked"), "loot": ("failed", "interrupted"), "equip": ("rejected", "none held"),
        "eat": ("rejected", "none held"), "drink": ("rejected", "none held"), "drop": ("rejected", "none held"),
        "stop": ("done", ""), "sleep": ("failed", "not loaded"), "aim": ("failed", "not loaded"),
        "climb": ("failed", "interrupted"), "bandage": ("rejected", "none held"), "rip": ("rejected", "none held"),
        "wash": ("rejected", "none held"), "fill": ("rejected", "none held"), "wear": ("rejected", "none held"),
        "window": ("failed", "interrupted"), "unwear": ("rejected", "none held"), "shove": ("failed", "not loaded"),
        "stomp": ("rejected", "not valid")}


def test_the_bare_table_covers_every_skill_case():
    assert set(BARE) == set(SKILL_CASES)


@pytest.mark.parametrize("case", SKILL_CASES)
def test_a_bare_player_ends_as_the_interface_says_with_no_raise(case):
    lua, fs, g = skills_host()
    lua.execute(PCALL_COUNTER)
    p = bare_player()
    drive(lua, g, p, case)
    end = ended(act_lines(lua, fs))
    assert (end["state"], end["reason"]) == BARE[case]
    assert lua.eval("PZA.skills.cur") is None
    assert lua.eval("PZA.skills.errors") == 0 and g.pcallFails == 0


# ---- (b) a player whose every member raises -------------------------------------------------------------------------

@pytest.mark.parametrize("case", SKILL_CASES)
def test_a_raising_player_never_propagates_and_the_runner_counts_it(case):
    lua, fs, g = skills_host()
    p = Raising()
    drive(lua, g, p, case, ticks=5)
    end = ended(act_lines(lua, fs))
    if case == "stop":
        assert (end["state"], end["reason"]) == ("done", "")   # its only player work, the queue clear, is under pcall
    else:
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


def test_s_frame_on_a_raising_player_returns_a_frame_and_names_the_missing():
    lua, fs, g = skills_host()
    f = lua.eval("PZA.sense.frame")(Raising())
    for grp in ("me", "stats", "body", "load"):
        assert f[grp] is not None, grp
    assert f.me.x is None and f.me.y is None and f.me.dir is None and f.stats.hunger is None
    assert f.body.health is None and f.load.weight is None and f.weapon is None
    missing = set(lua.eval("PZA.sense.missing").values())
    assert {"raise:me", "raise:stats", "raise:body", "raise:load", "raise:weapon"} <= missing
    assert lua.eval("PZA.sense.frameErrors") >= 5


# ---- (d) every vanilla class absent ---------------------------------------------------------------------------------

# the reason each skill's interface gives with its vanilla class absent; attack needs none in reach (it swings), and out
# of reach its approach walk cannot queue, so it fails at once with the walk's reason (fix wave M5); sleep needs none (the
# floor bed, ZombRand's midpoint, no fade) and the player stays asleep until its hour of wall runs out (interrupted);
# aim walks its vector through the auto-walk, which needs Vector2 (not loaded); climb needs ISClimbOverFence; the care
# skills need ISApplyBandage, OnNewCraft, ISWashClothing and ISTakeWaterAction, and wear ISWearClothing; window's open needs ISOpenCloseWindow (PZA/1.6)
# PZA/1.7: the full player's jacket is not worn, so unwear is refused not worn before it needs ISUnequipAction (test_lua_pza17
# fails it not loaded on a worn one); shove finds no setDoShove, stomp's zombie stands (not valid)
ABSENT = {"walkTo": ("failed", "no path"), "steer": ("failed", "not loaded"), "open": ("failed", "not loaded"),
          "loot": ("failed", "not loaded"), "equip": ("failed", "not loaded"), "eat": ("failed", "not loaded"),
          "drink": ("failed", "not loaded"), "drop": ("failed", "not loaded"), "stop": ("done", ""),
          "sleep": ("failed", "interrupted"), "aim": ("failed", "not loaded"), "climb": ("failed", "not loaded"),
          "bandage": ("failed", "not loaded"), "rip": ("failed", "not loaded"), "wash": ("failed", "not loaded"),
          "fill": ("failed", "not loaded"), "wear": ("failed", "not loaded"), "window": ("failed", "not loaded"),
          "unwear": ("rejected", "not worn"), "shove": ("failed", "not loaded"), "stomp": ("rejected", "not valid")}


@pytest.mark.parametrize("case", SKILL_CASES)
def test_every_vanilla_class_absent_fails_as_the_interface_says_with_no_raise(case):
    lua, fs, g = skills_host()
    p = full_player()
    clear_vanilla(g)
    lua.execute(PCALL_COUNTER)
    drive(lua, g, p, case)
    end = ended(act_lines(lua, fs))
    want = ("done", "") if case == "attack" else ABSENT[case]
    assert (end["state"], end["reason"]) == want
    assert lua.eval("PZA.skills.cur") is None
    assert lua.eval("PZA.skills.errors") == 0 and g.pcallFails == 0


def test_attack_out_of_reach_with_the_walk_absent_fails_no_path_on_its_first_tick():
    lua, fs, g = skills_host(zombie_x=14.0)
    p = full_player()
    clear_vanilla(g)
    lua.execute(PCALL_COUNTER)
    drive(lua, g, p, "attack", ticks=1)
    end = ended(act_lines(lua, fs))
    assert (end["state"], end["reason"]) == ("failed", "no path")
    assert lua.eval("PZA.skills.errors") == 0 and g.pcallFails == 0


# ---- Main's tick on each fault ---------------------------------------------------------------------------------------

def main_host(fault):
    """Main loaded in the game's order, the init tick run with a full player, then the player swapped for the fault:
    `bare`, `raise`, or `absent` (the full player with every vanilla class nil)."""
    fs = FakeFS()
    lua = make_lua(fs)
    load(lua, MAIN_FILES)
    g = lua.globals()
    world(g)
    cur = {"p": full_player()}
    g.getPlayer = lambda: cur["p"]
    g._handlers[0]()                                          # the init tick
    assert lua.eval("PZA.main.ready") is True
    lua.execute("PZA.tick = 2")                               # the next tick is 3, a poll tick (L.POLL_EVERY, P23-4)
    if fault == "bare":
        cur["p"] = bare_player()
    elif fault == "raise":
        cur["p"] = Raising()
    else:
        clear_vanilla(g)
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
        assert any(l["kind"] == "act" and l["aid"] == "a1" for l in lines)


# ---- the map phase under its own pcall (fix wave I9: S-15 extended to Map) -------------------------------------------

def raising_square_host():
    """Main loaded in the game's order, the init tick run with a full player at (10, 20), the rate at 60 (a frame every
    tick) and the watch due every tick; every square round the player answers its position and solidity but raises on getObjects (a modded object)."""
    fs = FakeFS()
    lua = make_lua(fs)
    load(lua, MAIN_FILES)
    g = lua.globals()

    def objects(s):
        raise RuntimeError("java raised: getObjects")
    sqs = {}
    for x in range(0, 21):
        for y in range(10, 31):
            sqs[(x, y, 0)] = J(getObjects=objects, isSolid=lambda s: False, isSolidTrans=lambda s: False,
                               getX=lambda s, x=x: x, getY=lambda s, y=y: y, getZ=lambda s: 0)
    g._cell = make_cell([], sqs)
    p = full_player()
    g.getPlayer = lambda: p
    g._handlers[0]()                                          # the init tick
    lua.execute("PZA.tick = 2")                               # the next tick is 3, a poll tick (L.POLL_EVERY, P23-4)
    lua.execute("PZA.sense.RATE = 60")
    lua.execute("PZA.map.WATCH_EVERY = 1")                    # the watch due every tick (X4 fix pass 2.1 paces it at 6)
    return lua, fs, g


def live_lines(lua, fs):
    lua.execute("PZA.link.flush()")
    return [pza1.decode(json.loads(l)) for l in fs.files.get(LIVE, "").split("\n") if l.strip()]


def test_a_square_raising_on_every_visit_still_emits_every_frame_and_one_lua_error_a_second():
    lua, fs, g = raising_square_host()
    n = 12
    for _ in range(n):
        g._clock["ms"] += 1000                                # a second a tick: reportError's limit lets each one out
        g._handlers[0]()
    out = live_lines(lua, fs)
    frames = [l for l in out if l["kind"] == "frame"]
    errors = [l for l in out if l["kind"] == "event" and l["event"] == "lua_error"]
    assert len(frames) == n                                   # the frame is emitted on every raising tick
    assert len(errors) == n and all("getObjects" in e["msg"] for e in errors)
    assert lua.eval("PZA.errors") == n and lua.eval("PZA.map.errors") == n
    assert "raise:map" in set(lua.eval("PZA.map.missing").values())


def test_the_map_raise_is_rate_limited_to_one_lua_error_a_second_and_never_stalls_the_watch():
    lua, fs, g = raising_square_host()
    idx0 = lua.eval("PZA.map.watchIdx")
    for _ in range(30):                                       # 30 ticks inside one second of the client clock
        g._handlers[0]()
    out = live_lines(lua, fs)
    assert len([l for l in out if l["kind"] == "frame"]) == 30
    assert len([l for l in out if l["kind"] == "event" and l["event"] == "lua_error"]) == 1
    assert lua.eval("PZA.errors") == 30 and lua.eval("PZA.map.watchIdx") != idx0   # the watch moves on


def test_a_raising_scan_step_drops_the_job_and_the_watch_takes_over():
    lua, fs, g = raising_square_host()
    fs.files[CMD] = json.dumps({"seq": 1, "aid": "s1", "type": "scan", "args": {"r": 3}}) + "\n"
    g._handlers[0]()                                          # the scan accepted, its first step raised
    assert lua.eval("PZA.map.job") is None
    g._clock["ms"] += 1000
    g._handlers[0]()
    out = live_lines(lua, fs)
    s1 = [l for l in out if l["kind"] == "act" and l["aid"] == "s1"]
    assert [(l["state"], l["reason"]) for l in s1] == [("done", "")]   # S-32: one act line, never a second terminal one
    (drop,) = [l for l in out if l["kind"] == "event" and l["event"] == "scan_dropped"]
    assert (drop["scanId"], drop["aid"], drop["part"], drop["parts"]) == (1, "s1", 1, 3)
    assert "getObjects" in drop["reason"]
    assert len([l for l in out if l["kind"] == "frame"]) == 2
    assert len([l for l in out if l["kind"] == "map"]) == 0 and lua.eval("PZA.map.errors") == 2


# ---- X4 fix pass 2.8 (fix-wave review Minors 5 and 6, ruling S-30): a scan's raise always ends its act line ---------

def test_a_raising_scan_start_answers_the_scan_failed_interrupted_and_the_tick_goes_on():
    lua, fs, g = raising_square_host()
    p = g.getPlayer()
    real_x = p.getX

    def raising_x(s):
        raise RuntimeError("java raised: getX")
    lua.execute("PZA.map.WATCH_EVERY = 6")                    # keep the watch off the raising squares on this tick
    p.getX = raising_x
    fs.files[CMD] = json.dumps({"seq": 1, "aid": "s1", "type": "scan", "args": {"r": 3}}) + "\n"
    g._handlers[0]()
    p.getX = real_x
    out = live_lines(lua, fs)
    s1 = [l for l in out if l["kind"] == "act" and l["aid"] == "s1"]
    assert [(l["type"], l["state"], l["reason"]) for l in s1] == [("scan", "failed", "interrupted")]
    assert lua.eval("PZA.map.job") is None and lua.eval("PZA.map.errors") == 1
    assert "raise:map" in set(lua.eval("PZA.map.missing").values())
    assert lua.eval("PZA.main.ready") is True


def test_a_job_dropped_by_the_map_phase_names_its_scans_aid_once():
    lua, fs, g = raising_square_host()
    fs.files[CMD] = json.dumps({"seq": 1, "aid": "s1", "type": "scan", "args": {"r": 3}}) + "\n"
    for _ in range(5):
        g._clock["ms"] += 1000
        g._handlers[0]()                                      # the job drops on the first; the watch raises after
    out = live_lines(lua, fs)
    s1 = [l for l in out if l["kind"] == "act" and l["aid"] == "s1"]
    assert [l["state"] for l in s1] == ["done"]               # S-32: the scan's one act line stays its only one
    assert [l for l in out if l["kind"] == "act" and l["aid"] != "s1"] == []
    drops = [l for l in out if l["kind"] == "event" and l["event"] == "scan_dropped"]
    assert [(d["aid"], d["scanId"]) for d in drops] == [("s1", 1)]   # once: the watch's later raises drop no job


# ---- X4 fix pass fix 1 (ruling S-32): a dropped job is one scan_dropped event, never a second act line ---------------

def test_a_scan_dropped_after_its_first_part_names_the_part_it_was_walking():
    lua, fs, g = raising_square_host()
    lua.execute("PZA.map.WATCH_EVERY = 6")                    # the watch off these ticks: only the job's step runs
    lua.execute("PZA.map.square = function(sq, missing) return { x = 0, y = 0, z = 0 } end")
    lua.execute("_steps = 0; local st0 = PZA.map.scanStep; PZA.map.scanStep = function(p) _steps = _steps + 1;"
                " if _steps == 2 then error('java raised: part two') end; return st0(p) end")
    fs.files[CMD] = json.dumps({"seq": 1, "aid": "s2", "type": "scan", "args": {"r": 3}}) + "\n"
    for _ in range(3):
        g._clock["ms"] += 1000
        g._handlers[0]()
    out = live_lines(lua, fs)
    assert [l["state"] for l in out if l["kind"] == "act" and l["aid"] == "s2"] == ["done"]
    (drop,) = [l for l in out if l["kind"] == "event" and l["event"] == "scan_dropped"]
    assert (drop["scanId"], drop["aid"], drop["part"], drop["parts"]) == (1, "s2", 2, 3)
    assert "part two" in drop["reason"] and drop["gameMin"] is not None
    assert lua.eval("PZA.map.job") is None and len([l for l in out if l["kind"] == "map"]) == 1


# ---- PZA/1.5.3 (Task 9 fix 5, ruling P24-R): the ride's new shape, a bandage beside a running leg ---------------------

def ride(lua, g, p, ticks=20):
    """A walkTo started and ticked once, then a bandage with keepMoving on part 0 (a hand, above the legs), ticked."""
    for aid, typ, args in (("w", "walkTo", {"x": 12, "y": 20, "gait": "run"}),
                           ("a1", "bandage", {"itemId": 1003, "part": 0, "keepMoving": True})):
        lua.eval("PZA.skills.start")(lua.table_from({"seq": 1, "aid": aid, "type": typ, "args": args},
                                                    recursive=True), p)
        lua.eval("PZA.skills.tick")(p)
    for i in range(ticks):
        if i == 5:
            g._clock["ms"] += 30000
        lua.eval("PZA.skills.tick")(p)


def test_a_ride_on_a_bare_player_is_rejected_none_held_with_no_raise():
    lua, fs, g = skills_host()
    lua.execute(PCALL_COUNTER)
    ride(lua, g, bare_player())
    assert (ended(act_lines(lua, fs))["state"], ended(act_lines(lua, fs))["reason"]) == ("rejected", "none held")
    assert lua.eval("PZA.skills.side") is None
    assert lua.eval("PZA.skills.errors") == 0 and g.pcallFails == 0


def test_a_ride_on_a_raising_player_never_propagates_and_is_counted():
    lua, fs, g = skills_host()
    ride(lua, g, Raising(), ticks=5)
    assert_failed_in_enum(ended(act_lines(lua, fs)))
    assert lua.eval("PZA.skills.side") is None and lua.eval("PZA.skills.errors") >= 1


def test_a_ride_with_every_vanilla_class_absent_fails_not_loaded_and_its_leg_walks_on_with_no_raise():
    lua, fs, g = skills_host()
    p = full_player()
    lua.execute(PCALL_COUNTER)
    lua.eval("PZA.skills.start")(lua.table_from({"seq": 1, "aid": "w", "type": "walkTo",
                                                 "args": {"x": 12, "y": 20, "gait": "run"}}, recursive=True), p)
    lua.eval("PZA.skills.tick")(p)
    clear_vanilla(g)
    lua.eval("PZA.skills.start")(lua.table_from({"seq": 2, "aid": "a1", "type": "bandage",
                                                 "args": {"itemId": 1003, "part": 0, "keepMoving": True}},
                                                recursive=True), p)
    for _ in range(5):
        lua.eval("PZA.skills.tick")(p)
    lines = act_lines(lua, fs)
    end = ended(lines)
    assert (end["state"], end["reason"]) == ("failed", "not loaded")
    assert all(l["state"] in ("accepted", "progress") for l in lines if l["aid"] == "w")   # the leg walks on
    assert lua.eval("PZA.skills.side") is None and lua.eval("PZA.skills.cur.type") == "walkTo"
    assert lua.eval("PZA.skills.errors") == 0 and g.pcallFails == 0
