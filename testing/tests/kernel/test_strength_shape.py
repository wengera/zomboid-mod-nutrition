"""NR_Server_Strength, driven through table-of-functions Java stand-ins.

The file is a server/ file the kernel host does not load, so it is loaded on top of the session host
the way test_metabolism_shape.py loads NR_Server_Metabolism.lua. NR.call indexes obj[name] and calls it
with obj first, so a Lua table of function fields stands in for a Java object. The body is built with
the real K.body.new and every level, XP, trait and carry read is stubbed by hand; the kernel math is
the real kernel. A stub proves the wiring, the order and the guards, not the engine's real getters,
which the live acceptance runs read.
"""
import os

import lupa.lua51 as lua51
import pytest

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
SERVER = os.path.join(REPO, "mod", "NutritionRevamp", "common", "media", "lua", "server")
SHARED = os.path.join(REPO, "mod", "NutritionRevamp", "common", "media", "lua", "shared")
STRENGTH = os.path.join(SERVER, "NR_Server_Strength.lua")
CORE = os.path.join(SHARED, "NR_Core.lua")
TOL = 1e-9
LADDER = [1500, 4500, 10500, 19500, 37500, 67500, 127500, 217500, 337500, 487500]

# The Java globals the adapter names, stubbed; the previous values are returned so the teardown puts
# them back and nothing leaks into a later module.
SETUP = r"""
function(age)
    local names = { "getGameTime", "CharacterTrait", "Perks", "sendSyncPlayerFields", "BeyondTen" }
    local saved = { age = NR_TEST_AGE, tod = NR_TEST_TOD, names = names, vals = {} }
    for i = 1, #names do saved.vals[i] = _G[names[i]] end
    NR_TEST_AGE = age
    NR_TEST_TOD = nil
    NR_TEST_NOLADDER = false
    NR_TEST_PUSHES = 0
    NR_TEST_LADDER_READS = 0
    local ladder = { 1500, 4500, 10500, 19500, 37500, 67500, 127500, 217500, 337500, 487500 }
    getGameTime = function()
        return {
            getWorldAgeHours = function(self) return NR_TEST_AGE end,
            getTimeOfDay = function(self)
                if NR_TEST_TOD ~= nil then return NR_TEST_TOD end
                return math.fmod(NR_TEST_AGE, 24)
            end,
        }
    end
    CharacterTrait = { WEAK = "WEAK", FEEBLE = "FEEBLE", STOUT = "STOUT", STRONG = "STRONG" }
    Perks = { Strength = {
        getTotalXpForLevel = function(self, L)
            NR_TEST_LADDER_READS = NR_TEST_LADDER_READS + 1
            if NR_TEST_NOLADDER then return nil end
            return ladder[L]
        end,
    } }
    sendSyncPlayerFields = function(p, n)
        if n == 2 then NR_TEST_PUSHES = NR_TEST_PUSHES + 1 end
    end
    BeyondTen = nil
    return saved
end
"""

TEARDOWN = r"""
function(saved)
    NR_TEST_AGE, NR_TEST_TOD = saved.age, saved.tod
    for i = 1, #saved.names do _G[saved.names[i]] = saved.vals[i] end
end
"""

# A player stand-in reading its every answer from cfg; the setters record into cfg.
PLAYER = r"""
function(cfg)
    local p = { cfg = cfg }
    cfg.levelWrites = {}
    cfg.deltaWrites = {}
    p.getPerkLevel = function(self, perk) return self.cfg.level end
    p.setPerkLevelDebug = function(self, perk, n)
        self.cfg.levelWrites[#self.cfg.levelWrites + 1] = n
        self.cfg.level = n
    end
    p.getXp = function(self)
        return { getXP = function(s, perk) return self.cfg.xp end }
    end
    p.getCharacterTraits = function(self)
        return {
            get = function(s, t) return self.cfg.traits[t] == true end,
            add = function(s, t) self.cfg.traits[t] = true end,
            remove = function(s, t) self.cfg.traits[t] = nil end,
        }
    end
    p.getMaxWeightDelta = function(self) return self.cfg.delta end
    p.setMaxWeightDelta = function(self, d)
        self.cfg.deltaWrites[#self.cfg.deltaWrites + 1] = d
        self.cfg.delta = d
    end
    return p
end
"""

MINUTE = r"""
function(player, record, age)
    NR_TEST_AGE = age
    NutritionRevamp.server.strength.minute("admin", player, record)
    return record
end
"""

RAISING = r"""
function(player, record, age)
    local K = NutritionRevamp.kernel
    local orig = K.strength.policy
    K.strength.policy = function() error("boom") end
    NR_TEST_AGE = age
    local ok, err = pcall(NutritionRevamp.server.strength.minute, "admin", player, record)
    K.strength.policy = orig
    return ok, err
end
"""


def _load(host, path, name):
    with open(path, encoding="utf-8") as fh:
        src = fh.read()
    host.rt.eval("function(src, name) return assert(loadstring(src, name)) end")(src, name)()


@pytest.fixture(scope="module")
def str_host(host):
    _load(host, STRENGTH, "@NR_Server_Strength.lua")
    saved = host.rt.eval(SETUP)(100.0)
    try:
        yield host
    finally:
        host.rt.eval(TEARDOWN)(saved)


@pytest.fixture(autouse=True)
def _reset(str_host):
    h = str_host
    STR(h).totals = None                       # every case reads the ladder afresh
    h.G.NR_TEST_NOLADDER = False
    h.G.NR_TEST_TOD = None
    h.G.BeyondTen = None
    yield


def STR(h):
    return h.G.NutritionRevamp.server.strength


def player(h, level=5, xp=40000, traits=None, delta=1.0):
    cfg = h.rt.table()
    cfg.level = level
    cfg.xp = xp
    cfg.traits = h.table({t: True for t in (traits or [])})
    cfg.delta = delta
    return h.rt.eval(PLAYER)(cfg)


def record_for(h, l0=5, ageH=99.0, traitCarry=1.0):
    record = h.rt.table()
    record.body = h.K.body["new"](80, 1, h.table({}), l0, traitCarry, 1.0, ageH)
    return record


def minute(h, p, record, age):
    return h.rt.eval(MINUTE)(p, record, age)


def writes(p):
    return list(p.cfg.levelWrites.values())


def deltas(p):
    return list(p.cfg.deltaWrites.values())


def traits(p):
    return sorted(k for k, v in p.cfg.traits.items() if v)


# --- the ladder -------------------------------------------------------------------------------------

def test_ladder_read_once_and_cached(str_host):
    h = str_host
    reads = h.G.NR_TEST_LADDER_READS
    t = STR(h).ladder()
    assert [t[L] for L in range(1, 11)] == LADDER
    assert t[0] == 0
    assert h.G.NR_TEST_LADDER_READS == reads + 10
    STR(h).ladder()
    assert h.G.NR_TEST_LADDER_READS == reads + 10   # cached once per server


def test_ladder_nil_falls_back_to_the_literal_ladder(str_host):
    h = str_host
    h.G.NR_TEST_NOLADDER = True
    fb = STR(h).stats.ladderFallbacks
    t = STR(h).ladder()
    assert [t[L] for L in range(1, 11)] == LADDER
    assert t[0] == 0
    assert STR(h).stats.ladderFallbacks == fb + 1
    STR(h).ladder()
    assert STR(h).stats.ladderFallbacks == fb + 1   # logged once


def test_ladder_falls_back_without_perks(str_host):
    h = str_host
    saved = h.G.Perks
    h.G.Perks = None
    try:
        t = STR(h).ladder()
    finally:
        h.G.Perks = saved
    assert [t[L] for L in range(1, 11)] == LADDER


# --- the vanilla level and BeyondTen (ruling T1-1) ------------------------------------------------

def test_vanilla_level_reads_the_xp(str_host):
    h = str_host
    lv, cur = STR(h).vanillaLevel(player(h, level=5, xp=40000), h.G.Perks.Strength)
    assert lv == 5 and cur == 5
    lv, _ = STR(h).vanillaLevel(player(h, level=5, xp=20000), h.G.Perks.Strength)
    assert lv == 4                             # 19500 is level 4's total, 37500 level 5's (#2102)


def test_beyondten_parked_xp_reads_ten(str_host):
    h = str_host
    h.G.BeyondTen = h.table({"NATIVE_MAX_LEVEL": 10})
    lv, cur = STR(h).vanillaLevel(player(h, level=10, xp=337500), h.G.Perks.Strength)
    assert lv == 10 and cur == 10
    p = player(h, level=10, xp=337500, traits=["STRONG"])
    record = record_for(h, l0=10)
    minute(h, p, record, 100.0)
    assert writes(p) == []                     # no clamp to 9


def test_beyondten_absent_parked_xp_reads_nine(str_host):
    h = str_host
    lv, _ = STR(h).vanillaLevel(player(h, level=10, xp=337500), h.G.Perks.Strength)
    assert lv == 9
    # Without BeyondTen the level follows the XP down (vanilla's rust pass would too, #2124); 9 keeps
    # STRONG, so no push.
    p = player(h, level=10, xp=337500, traits=["STRONG"])
    record = record_for(h, l0=10)
    pushes = h.G.NR_TEST_PUSHES
    minute(h, p, record, 100.0)
    assert writes(p) == [9]
    assert traits(p) == ["STRONG"]
    assert h.G.NR_TEST_PUSHES == pushes


def test_beyondten_without_native_max_is_ignored(str_host):
    h = str_host
    h.G.BeyondTen = h.table({})
    lv, _ = STR(h).vanillaLevel(player(h, level=10, xp=337500), h.G.Perks.Strength)
    assert lv == 9


def test_beyondten_does_not_lift_a_level_nine(str_host):
    h = str_host
    h.G.BeyondTen = h.table({"NATIVE_MAX_LEVEL": 10})
    lv, _ = STR(h).vanillaLevel(player(h, level=9, xp=337500), h.G.Perks.Strength)
    assert lv == 9


# --- the level write --------------------------------------------------------------------------------

def test_no_write_when_ceiling_meets_the_shown_level(str_host):
    h = str_host
    p = player(h, level=5, xp=40000)
    record = record_for(h)
    w0 = STR(h).stats.writes
    minute(h, p, record, 100.0)
    assert writes(p) == []
    assert STR(h).stats.writes == w0
    assert record["body"]["shownL"] == 5


def test_lean_loss_clamps_one_level_an_hour_with_remap_and_push(str_host):
    h = str_host
    p = player(h, level=5, xp=40000, traits=["STOUT"])
    record = record_for(h)
    body = record["body"]
    body.lm = 0.9 * body["lm0"]
    assert h.K.strength.ceiling(5, body["lm"], body["lm0"], 1.0) == 3
    pushes = h.G.NR_TEST_PUSHES
    w0 = STR(h).stats.writes
    minute(h, p, record, 100.0)
    assert writes(p) == [4]
    assert traits(p) == ["FEEBLE"]             # STOUT removed, FEEBLE added
    assert h.G.NR_TEST_PUSHES == pushes + 1
    assert STR(h).stats.writes == w0 + 1
    # The sync rebuilt the level to 5: re-asserted at 4, the trait set unchanged, no second push.
    p.cfg.level = 5
    minute(h, p, record, 100.0 + 1 / 60)
    assert writes(p) == [4, 4]
    assert h.G.NR_TEST_PUSHES == pushes + 1
    # Within the hour: nothing more.
    minute(h, p, record, 100.5)
    assert writes(p) == [4, 4]
    # An hour on: the next fall to 3 (FEEBLE again, no push).
    minute(h, p, record, 101.0)
    assert writes(p) == [4, 4, 3]
    assert traits(p) == ["FEEBLE"]
    assert h.G.NR_TEST_PUSHES == pushes + 1


def test_xp_loss_follows_down_at_once(str_host):
    # K.strength.policy caps desired at lvanilla: an XP loss follows down at once (Task 10's kernel);
    # the one-per-hour fall paces the ceiling only.
    h = str_host
    p = player(h, level=5, xp=0)
    record = record_for(h)
    minute(h, p, record, 100.0)
    assert writes(p) == [0]
    assert traits(p) == ["WEAK"]
    assert record["body"]["shownL"] == 0


def test_rise_after_six_held_hours(str_host):
    h = str_host
    p = player(h, level=3, xp=40000, traits=["FEEBLE"])
    record = record_for(h, l0=3)
    body = record["body"]
    body.shownL = 3
    body.lm = body["lm0"] * 2 ** 0.2           # ceiling 5
    minute(h, p, record, 99.0)
    for k in range(1, 6):
        minute(h, p, record, 99.0 + k)
    assert writes(p) == []                     # five held hours
    minute(h, p, record, 105.0)
    assert writes(p) == [4]
    assert traits(p) == ["FEEBLE"]


def test_dt_is_clamped_to_an_hour(str_host):
    h = str_host
    p = player(h, level=3, xp=40000)
    record = record_for(h, l0=3)
    body = record["body"]
    body.lm = body["lm0"] * 2 ** 0.2
    minute(h, p, record, 99.0 + 10.0)          # a ten-hour gap counts one hour
    assert abs(body["riseHeldH"] - 1.0) < TOL
    assert writes(p) == []
    assert abs(body["strAgeH"] - 109.0) < TOL


def test_band_traits_absent_are_added(str_host):
    h = str_host
    p = player(h, level=8, xp=40000, traits=[])
    record = record_for(h)
    pushes = h.G.NR_TEST_PUSHES
    minute(h, p, record, 100.0)
    assert writes(p) == [5]                    # 8 above the XP-implied 5
    assert traits(p) == []                     # level 5 has no band trait
    assert h.G.NR_TEST_PUSHES == pushes
    p.cfg.level = 9
    p.cfg.traits = h.table({"STRONG": True, "WEAK": True})
    minute(h, p, record, 100.0 + 1 / 60)
    assert traits(p) == []
    assert h.G.NR_TEST_PUSHES == pushes + 1


def test_missing_push_global_is_counted(str_host):
    h = str_host
    saved = h.G.sendSyncPlayerFields
    h.G.sendSyncPlayerFields = None
    try:
        p = player(h, level=5, xp=0, traits=[])
        miss = STR(h).stats.pushMissing
        minute(h, p, record_for(h), 100.0)
    finally:
        h.G.sendSyncPlayerFields = saved
    assert traits(p) == ["WEAK"]
    assert STR(h).stats.pushMissing == miss + 1


def test_unreadable_xp_skips_the_level_arm(str_host):
    h = str_host
    p = player(h, level=5, xp=None)
    record = record_for(h)
    bad = STR(h).stats.badReads
    minute(h, p, record, 100.0)
    assert writes(p) == []
    assert STR(h).stats.badReads == bad + 1


def test_never_calls_a_granting_or_leveling_member():
    with open(STRENGTH, encoding="utf-8") as fh:
        code = "\n".join(l.split("--")[0] for l in fh.read().splitlines())
    for name in ("LevelPerk", "LoseLevel", "setXPToLevel", "addXp", "AddXP", "setMaxWeightBase"):
        assert name not in code


# --- the carry delta --------------------------------------------------------------------------------

def test_carry_delta_from_body_fat(str_host):
    h = str_host
    p = player(h, level=5, xp=40000, delta=1.0)
    record = record_for(h)
    body = record["body"]
    body.fm = 33.0
    body.lm = 67.0
    body.lm0 = 67.0
    h.G.NR_TEST_TOD = 14.0
    cw = STR(h).stats.carryWrites
    minute(h, p, record, 100.0)
    assert deltas(p) == [pytest.approx(0.991, abs=1e-9)]
    assert abs(body["delta"] - 0.991) < 1e-9
    assert STR(h).stats.carryWrites == cw + 1
    minute(h, p, record, 100.0 + 1 / 60)
    assert len(deltas(p)) == 1                 # unchanged: written once
    p.cfg.delta = 1.0                          # another writer drifted it
    minute(h, p, record, 100.0 + 2 / 60)
    assert len(deltas(p)) == 2 and abs(deltas(p)[1] - 0.991) < 1e-9
    assert STR(h).stats.carryWrites == cw + 2


def test_carry_delta_scales_the_trait_factor(str_host):
    h = str_host
    p = player(h, level=5, xp=40000, delta=1.0)
    record = record_for(h, traitCarry=1.25)
    minute(h, p, record, 100.0)
    assert deltas(p) == [1.25]                 # lean body: eAcute 0


def test_no_carry_write_within_tolerance(str_host):
    h = str_host
    p = player(h, level=5, xp=40000, delta=1.0005)
    minute(h, p, record_for(h), 100.0)
    assert deltas(p) == []


# --- the guards -------------------------------------------------------------------------------------

def test_no_body_is_a_no_op(str_host):
    h = str_host
    p = player(h)
    record = h.rt.table()
    minutes = STR(h).stats.minutes
    minute(h, p, record, 100.0)
    assert writes(p) == [] and deltas(p) == []
    assert STR(h).stats.minutes == minutes + 1


def test_nil_record_is_a_no_op(str_host):
    h = str_host
    minutes = STR(h).stats.minutes
    STR(h).minute("admin", player(h), None)
    assert STR(h).stats.minutes == minutes


def test_a_raising_kernel_never_raises_into_the_walk(str_host):
    h = str_host
    p = player(h)
    record = record_for(h)
    failures = STR(h).stats.failures
    ok, err = h.rt.eval(RAISING)(p, record, 100.0)
    assert ok is True
    assert STR(h).stats.failures == failures + 1
    assert "boom" in str(STR(h).lastError)


def test_a_non_finite_stamp_is_healed(str_host):
    h = str_host
    p = player(h)
    record = record_for(h)
    body = record["body"]
    body.strAgeH = float("nan")
    body.riseHeldH = float("nan")
    minute(h, p, record, 100.0)
    assert abs(body["strAgeH"] - 100.0) < TOL
    assert body["riseHeldH"] == body["riseHeldH"]


def test_limitations(str_host):
    h = str_host
    lim = list(STR(h).limitations.values())
    assert ("the ceiling clamps the Java level 0-10; BeyondTen mastery levels are outside the model "
            "(#2118, Task 1)") in lim
    assert "a rise is one level per six-hour window" in lim
    assert "the carry delta's acute inputs are Plan 4/5's" in lim
    assert any("BeyondTen" in s and "level-9 total" in s for s in lim)


# --- the wiring order -------------------------------------------------------------------------------

def test_strength_runs_after_metabolism_in_the_players_list():
    rt = lua51.LuaRuntime(unpack_returned_tuples=True)
    load = rt.eval("function(src, name) return assert(loadstring(src, name)) end")
    with open(CORE, encoding="utf-8") as fh:
        load(fh.read(), "@NR_Core.lua")()
    rt.execute(r"""
        NR_STARTED = {}
        Events = { OnServerStarted = { Add = function(fn) NR_STARTED[#NR_STARTED + 1] = fn end } }
        isServer = function() return true end
        NutritionRevamp.server.players = { onMinute = {} }
    """)
    names = sorted(["NR_Server_Strength.lua", "NR_Server_Metabolism.lua", "NR_Server_Kinetics.lua"])
    assert names == ["NR_Server_Kinetics.lua", "NR_Server_Metabolism.lua", "NR_Server_Strength.lua"]
    for n in names:
        with open(os.path.join(SERVER, n), encoding="utf-8") as fh:
            load(fh.read(), "@" + n)()
    rt.execute("for i = 1, #NR_STARTED do NR_STARTED[i]() end")
    rt.execute("for i = 1, #NR_STARTED do NR_STARTED[i]() end")   # a second start wires nothing twice
    G = rt.globals()
    on = G.NutritionRevamp.server.players.onMinute
    assert len(on) == 3
    same = rt.eval("rawequal")
    assert same(on[2], G.NutritionRevamp.server.metabolism.minute)
    assert same(on[3], G.NutritionRevamp.server.strength.minute)
    assert G.NutritionRevamp.server.strength.wired is True
