"""NR_Server_Strength, driven through table-of-functions Java stand-ins.

The file is a server/ file the kernel host does not load, so it is loaded on top of the session host
the way test_metabolism_shape.py loads NR_Server_Metabolism.lua. NR.call indexes obj[name] and calls it
with obj first, so a Lua table of function fields stands in for a Java object. The body is built with
the real K.body.new over K.body.create and every level, trait and carry read is stubbed by hand; the kernel math is
the real kernel. A stub proves the wiring, the order and the guards, not the engine's real getters,
which the live acceptance runs read. Since Plan 13 Task 14 the minute writes the body's shown level when one is due
(the day close's stamp, first sight, or a native level off the written one): the native level stepped through
LevelPerk and LoseLevel (ruling 13-8), the XP pinned (ruling 13-9), parked at the level-9 total at 10 or written into
BeyondTen's stored XP (ruling 13-42); the carry's trait factor reads the written level's band (ruling 13-7); and the
level-10 guard wraps xpUpdate.checkForLosingLevel (ruling 13-10). The stand-in's addXp global fires the listener as
the engine's AddXP does (#2125).
"""
import os
import re

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
    local names = { "getGameTime", "CharacterTrait", "Perks", "sendSyncPlayerFields", "BeyondTen", "addXp",
                    "xpUpdate", "NR_StrengthGuardInstalled", "SandboxVars" }
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
    xpUpdate = nil
    SandboxVars = nil
    -- the engine's Lua addXp (LuaManager$GlobalObject.addXp): the grant lands times the stand-in's chain and fires
    -- the AddXP event after it, as XP.AddXP does (#2125)
    addXp = function(p, perk, amount)
        local c = p.cfg
        c.grants[#c.grants + 1] = amount
        local landed = amount * (c.chain or 1)
        c.xp = c.xp + landed
        NutritionRevamp.server.strength.onXp(p, perk, landed)
    end
    return saved
end
"""

TEARDOWN = r"""
function(saved)
    NR_TEST_AGE, NR_TEST_TOD = saved.age, saved.tod
    for i = 1, #saved.names do _G[saved.names[i]] = saved.vals[i] end
end
"""

# A player stand-in reading its every answer from cfg; the setters record into cfg, and every Java member counts its
# call in cfg.calls. LevelPerk and LoseLevel move the level one step (capped [0, 10], IsoGameCharacter.LevelPerk
# @106-@120, LoseLevel @20-@29) and record +1 or -1 in cfg.steps; setXPToLevel writes the level's starting total.
PLAYER = r"""
function(cfg)
    local p = { cfg = cfg }
    local c = cfg
    c.levelWrites = {}
    c.deltaWrites = {}
    c.steps = {}
    c.xpSets = {}
    c.grants = {}
    c.calls = {}
    local function hit(name) c.calls[name] = (c.calls[name] or 0) + 1 end
    local ladder = { [0] = 0, 1500, 4500, 10500, 19500, 37500, 67500, 127500, 217500, 337500, 487500 }
    p.getUsername = function(self) hit("getUsername"); return c.name end
    p.getPerkLevel = function(self, perk) hit("getPerkLevel"); return c.level end
    p.setPerkLevelDebug = function(self, perk, n)
        c.levelWrites[#c.levelWrites + 1] = n
        c.level = n
    end
    p.LevelPerk = function(self, perk)
        hit("LevelPerk")
        c.steps[#c.steps + 1] = 1
        c.level = math.min(10, c.level + 1)
    end
    p.LoseLevel = function(self, perk)
        hit("LoseLevel")
        c.steps[#c.steps + 1] = -1
        c.level = math.max(0, c.level - 1)
    end
    local xp = {
        getXP = function(s, perk) hit("getXP"); return c.xp end,
        setXPToLevel = function(s, perk, L)
            hit("setXPToLevel")
            c.xpSets[#c.xpSets + 1] = L
            c.xp = ladder[L]
        end,
        getMultiplier = function(s, perk) hit("getMultiplier"); return c.book end,
    }
    p.getXp = function(self) hit("getXp"); return xp end
    p.getNutrition = function(self)
        hit("getNutrition")
        return { getProteins = function(s) hit("getProteins"); return c.proteins end }
    end
    p.getCharacterTraits = function(self)
        hit("getCharacterTraits")
        return {
            get = function(s, t) return c.traits[t] == true end,
            add = function(s, t) c.traits[t] = true end,
            remove = function(s, t) c.traits[t] = nil end,
        }
    end
    p.getMaxWeightDelta = function(self) hit("getMaxWeightDelta"); return c.delta end
    p.setMaxWeightDelta = function(self, d)
        hit("setMaxWeightDelta")
        c.deltaWrites[#c.deltaWrites + 1] = d
        c.delta = d
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
    local orig = K.strength.eAcute
    K.strength.eAcute = function() error("boom") end
    NR_TEST_AGE = age
    local ok, err = pcall(NutritionRevamp.server.strength.minute, "admin", player, record)
    K.strength.eAcute = orig
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
    h.G.xpUpdate = None
    h.G.SandboxVars = None
    yield


def STR(h):
    return h.G.NutritionRevamp.server.strength


def player(h, level=5, xp=40000, traits=None, delta=1.0, name="admin", proteins=0.0, book=1.0, chain=1.0):
    cfg = h.rt.table()
    cfg.level = level
    cfg.xp = xp
    cfg.traits = h.table({t: True for t in (traits or [])})
    cfg.delta = delta
    cfg.name = name
    cfg.proteins = proteins
    cfg.book = book
    cfg.chain = chain
    return h.rt.eval(PLAYER)(cfg)


def record_for(h, ageH=99.0):
    record = h.rt.table()
    record.body = h.K.body["new"](h.K.body.create(None, None, h.K.strength.DEFAULTS, 1), 1, ageH)
    return record


def minute(h, p, record, age):
    return h.rt.eval(MINUTE)(p, record, age)


def writes(p):
    return list(p.cfg.levelWrites.values())


def deltas(p):
    return list(p.cfg.deltaWrites.values())


def traits(p):
    return sorted(k for k, v in p.cfg.traits.items() if v)


def lst(t):
    return list(t.values())


def body_at(h, L, record=None):
    """A record whose body's shown level is L: lm set through K.strength.fOfLevel at its own N0 and T."""
    record = record or record_for(h)
    body = record["body"]
    body.lm = h.K.strength.fOfLevel(L, body.N0, body.T, h.K.strength.DEFAULTS)
    return record


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


# --- the level write --------------------------------------------------------------------------------

def test_first_sight_writes_the_level_and_pins_the_xp(str_host):
    # Plan 13 Task 14: the no-trait body reads level 5.0 exactly; native 5 at 40000 XP: no step, a pure lowering
    h = str_host
    p = player(h, level=5, xp=40000)
    record = record_for(h)
    record["body"].levelDue = True
    minute(h, p, record, 100.0)
    body = record["body"]
    assert lst(p.cfg.steps) == [] and lst(p.cfg.xpSets) == [5] and lst(p.cfg.grants) == []
    assert p.cfg.xp == 37500
    assert body.wroteL == 5 and body.levelDue is False
    assert writes(p) == []                                      # never the debug setter (ruling 13-8)


def test_a_level_drop_steps_down_and_pins_the_fraction(str_host):
    # 7 to 5: two LoseLevel steps, then setXPToLevel(5) and one addXp of the fraction (ruling 13-9)
    h = str_host
    p = player(h, level=7, xp=130000)
    record = body_at(h, 5.25)
    body = record["body"]
    body.wroteL = 7
    body.levelDue = True
    pushes = h.G.NR_TEST_PUSHES
    minute(h, p, record, 100.0)
    assert lst(p.cfg.steps) == [-1, -1] and p.cfg.level == 5
    assert lst(p.cfg.xpSets) == [5]
    assert len(lst(p.cfg.grants)) == 1
    assert p.cfg.xp == pytest.approx(37500 + 0.25 * 30000, abs=1e-6)
    assert body.wroteL == 5 and body.levelDue is False
    assert h.G.NR_TEST_PUSHES == pushes + 1                   # STOUT to none: the server-side swap pushed


def test_the_grant_is_divided_by_the_chain_it_lands_through(str_host):
    # protein 60 (x1.5) under Global 2 lands the raw grant x3: the pin grants 7500 / 3 and lands 7500
    h = str_host
    h.G.SandboxVars = h.table({"MultiplierConfig": {"Global": 2.0, "GlobalToggle": True, "Strength": 4.0}})
    p = player(h, level=5, xp=0, proteins=60.0, chain=3.0)
    record = body_at(h, 5.25)
    minute(h, p, record, 100.0)
    assert lst(p.cfg.grants) == [pytest.approx(2500, abs=1e-6)]
    assert p.cfg.xp == pytest.approx(45000, abs=1e-6)


def test_a_book_above_1_is_divided_out_of_the_grant(str_host):
    h = str_host
    p = player(h, level=5, xp=0, book=4.0, chain=4.0)
    minute(h, p, body_at(h, 5.5), 100.0)
    assert lst(p.cfg.grants) == [pytest.approx(15000 / 4, abs=1e-6)]
    assert p.cfg.xp == pytest.approx(52500, abs=1e-6)


def test_a_raise_grants_through_add_xp_even_with_no_fraction(str_host):
    # amendment 5: a pin that raises XP re-seeds the anti-cheat through addXp (an amount of 0 when no fraction)
    h = str_host
    p = player(h, level=5, xp=260)
    minute(h, p, record_for(h), 100.0)                         # level 5.0: no fraction, a raise from 260
    assert lst(p.cfg.xpSets) == [5] and lst(p.cfg.grants) == [0]
    assert p.cfg.xp == 37500


def test_a_pure_lowering_uses_set_xp_to_level_only(str_host):
    h = str_host
    p = player(h, level=5, xp=60000)
    minute(h, p, record_for(h), 100.0)
    assert lst(p.cfg.xpSets) == [5] and lst(p.cfg.grants) == []
    assert p.cfg.xp == 37500


def test_an_unreadable_xp_grants_to_reseed(str_host):
    h = str_host
    p = player(h, level=5, xp=None)
    minute(h, p, record_for(h), 100.0)
    assert lst(p.cfg.grants) == [0]


def test_the_pin_grant_is_not_captured_as_training(str_host):
    # the stand-in's addXp fires the AddXP listener; STR.pinning keeps the pin out of body.sigDay
    h = str_host
    records = h.rt.table()
    saved = h.G.NutritionRevamp.server.store
    h.G.NutritionRevamp.server.store = h.table({})
    h.G.NutritionRevamp.server.store.records = records
    try:
        p = player(h, level=5, xp=0)
        records.admin = body_at(h, 5.5)
        caps, ign = STR(h).xpStats.captures, STR(h).xpStats.ignored
        minute(h, p, records.admin, 100.0)
    finally:
        h.G.NutritionRevamp.server.store = saved
    assert lst(p.cfg.grants) == [pytest.approx(15000, abs=1e-6)]
    assert records.admin.body.sigDay == 0
    assert (STR(h).xpStats.captures, STR(h).xpStats.ignored) == (caps, ign)
    assert STR(h).pinning is False


@pytest.mark.parametrize("muscle, n", [("STOUT", 7), ("WEAK", 1), ("FEEBLE", 3), ("STRONG", 9), (None, 5)])
def test_a_new_characters_start_writes_its_band_level(str_host, muscle, n):
    # amendment 4: Stout's start reads 6.999999999999997 and Weak's 0.9999999999999982; shown's 1e-9 floors them up
    h = str_host
    record = h.rt.table()
    record.body = h.K.body["new"](h.K.body.create(muscle, None, h.K.strength.DEFAULTS, 1), 1, 99.0)
    record.body.levelDue = True
    p = player(h, level=5, xp=37500)
    minute(h, p, record, 100.0)
    assert p.cfg.level == n and record.body.wroteL == n
    assert p.cfg.xp == h.K.strength.pinXp(n, 0, STR(h).ladder())


def test_a_sleeping_character_defers_the_write(str_host):
    h = str_host
    p = player(h, level=5, xp=40000)
    h.rt.eval("function(p) p.isAsleep = function(s) return p.cfg.asleep end end")(p)
    p.cfg.asleep = True
    record = body_at(h, 6.5)
    record["body"].levelDue = True
    minute(h, p, record, 100.0)
    assert lst(p.cfg.steps) == [] and lst(p.cfg.xpSets) == [] and record["body"].levelDue is True
    p.cfg.asleep = False
    minute(h, p, record, 100.0 + 1 / 60)
    assert p.cfg.level == 6 and record["body"].levelDue is False
    assert p.cfg.xp == pytest.approx(67500 + 0.5 * 60000, abs=1e-6)


def test_a_step_inside_a_band_pushes_nothing(str_host):
    h = str_host
    p = player(h, level=7, xp=130000)
    record = body_at(h, 6.5)
    record["body"].levelDue = True
    pushes = h.G.NR_TEST_PUSHES
    minute(h, p, record, 100.0)
    assert p.cfg.level == 6 and lst(p.cfg.steps) == [-1]
    assert h.G.NR_TEST_PUSHES == pushes


def test_the_minute_rewrites_after_an_admin_set(str_host):
    # the #2740 re-assertion: an admin's setPerkLevelDebug leaves native off body.wroteL; the next minute steps back
    h = str_host
    p = player(h, level=5, xp=40000)
    record = record_for(h)
    minute(h, p, record, 100.0)
    assert record["body"].wroteL == 5 and record["body"].levelDue is False
    p.setPerkLevelDebug(p, h.G.Perks.Strength, 8)
    minute(h, p, record, 100.0 + 1 / 60)
    assert p.cfg.level == 5 and lst(p.cfg.steps) == [-1, -1, -1]
    assert lst(p.cfg.xpSets) == [5, 5]


def test_no_write_without_the_stamp_or_a_moved_level(str_host):
    h = str_host
    p = player(h, level=5, xp=40000)
    record = record_for(h)
    minute(h, p, record, 100.0)
    lw = STR(h).stats.levelWrites
    minute(h, p, record, 100.0 + 1 / 60)
    minute(h, p, record, 100.0 + 2 / 60)
    assert STR(h).stats.levelWrites == lw and lst(p.cfg.xpSets) == [5]
    record["body"].levelDue = True                             # the day close's stamp
    minute(h, p, record, 100.0 + 3 / 60)
    assert STR(h).stats.levelWrites == lw + 1 and lst(p.cfg.xpSets) == [5, 5]


def test_the_minute_adds_no_java_call_without_a_due_write(str_host):
    # Rule 6 (amendment 6): with no write due the minute reads the level once and the carry's delta, as at HEAD
    h = str_host
    p = player(h, level=5, xp=40000, delta=1.0)
    record = record_for(h)
    record["body"].wroteL = 5
    record["body"].levelDue = False
    minute(h, p, record, 100.0)
    assert dict(p.cfg.calls.items()) == {"getPerkLevel": 1, "getMaxWeightDelta": 1}


def test_a_failed_step_leaves_the_stamp_for_the_next_minute(str_host):
    h = str_host
    p = player(h, level=5, xp=40000)
    p.LevelPerk = None
    record = body_at(h, 7.5)
    record["body"].levelDue = True
    fails = STR(h).stats.stepFailures
    minute(h, p, record, 100.0)
    assert record["body"].levelDue is True and record["body"].wroteL is None
    assert lst(p.cfg.xpSets) == [] and STR(h).stats.stepFailures == fails + 1
    assert deltas(p) == []                                     # nothing written yet: no carry


def test_a_raising_write_clears_pinning_and_is_counted(str_host):
    h = str_host
    p = player(h, level=5, xp=40000)
    p.LevelPerk = h.rt.eval("function() error('step boom') end")
    record = body_at(h, 7.5)
    failures = STR(h).stats.failures
    minute(h, p, record, 100.0)
    assert STR(h).pinning is False
    assert STR(h).stats.failures == failures + 1 and "step boom" in str(STR(h).lastError)


def test_a_non_finite_body_writes_nothing(str_host):
    h = str_host
    p = player(h, level=5, xp=40000)
    record = record_for(h)
    record["body"].T = float("nan")
    bad = STR(h).stats.badReads
    minute(h, p, record, 100.0)
    assert lst(p.cfg.xpSets) == [] and record["body"].wroteL is None
    assert STR(h).stats.badReads == bad + 1


def test_write_level_reads_its_own_level(str_host):
    h = str_host
    p = player(h, level=3, xp=0)
    record = body_at(h, 6.5)
    STR(h).writeLevel(p, record["body"])
    assert p.cfg.level == 6 and record["body"].wroteL == 6
    assert p.cfg.xp == pytest.approx(67500 + 0.5 * 60000, abs=1e-6)
    p2 = player(h, level=None)
    STR(h).writeLevel(p2, record["body"], None)
    assert lst(p2.cfg.xpSets) == []


# --- level 10: the park, BeyondTen (spec section 7; rulings 13-9, 13-24, 13-42) ------------------------

def test_at_10_without_beyond_ten_the_xp_parks_at_the_level_9_total(str_host):
    h = str_host
    p = player(h, level=8, xp=200000)
    record = body_at(h, 11.3)
    minute(h, p, record, 100.0)
    assert p.cfg.level == 10 and lst(p.cfg.steps) == [1, 1]
    assert lst(p.cfg.xpSets) == [9] and p.cfg.xp == 337500
    assert lst(p.cfg.grants) == [0]                            # a raise from 200000: re-seeded
    assert record["body"].wroteL == 10


def test_a_parked_10_lowered_by_a_grant_pins_with_set_xp_only(str_host):
    h = str_host
    p = player(h, level=10, xp=400000)
    record = body_at(h, 10.5)
    minute(h, p, record, 100.0)
    assert lst(p.cfg.xpSets) == [9] and lst(p.cfg.grants) == [] and p.cfg.xp == 337500


BT_STUB = r"""
function()
    local bt = { API_VERSION = 1, sets = {}, costCalls = 0 }
    local c = { [10] = 0, [11] = 1000, [12] = 2100, [13] = 3300, [14] = 4600, [15] = 6000 }
    bt.GetTotalMasteryCost = function(perk, target)
        bt.costCalls = bt.costCalls + 1
        if perk ~= Perks.Strength then error("another perk") end
        if target <= 10 then return 0 end
        if target > 15 then target = 15 end
        return c[target]
    end
    bt.SetStoredXP = function(character, perk, value)
        if perk ~= Perks.Strength then error("another perk") end
        bt.sets[#bt.sets + 1] = value
        return value, 0, 0
    end
    return bt
end
"""


def beyond_ten(h, version=1):
    bt = h.rt.eval(BT_STUB)()
    bt.API_VERSION = version
    h.G.BeyondTen = bt
    return bt


@pytest.mark.parametrize("L, stored", [(12.0, 2100), (10.4, 400), (16.2, 6000), (13.5, 3950)])
def test_with_beyond_ten_the_stored_xp_is_written_and_native_xp_never(str_host, L, stored):
    # 16.2 lies above every default cap: the clamp at 15 binds only on a tuned server (ruling 13-42)
    h = str_host
    bt = beyond_ten(h)
    p = player(h, level=9, xp=400000)
    record = body_at(h, L)
    minute(h, p, record, 100.0)
    assert p.cfg.level == 10 and record["body"].wroteL == 10
    assert lst(p.cfg.xpSets) == [] and lst(p.cfg.grants) == [] and p.cfg.xp == 400000
    assert [round(v, 6) for v in lst(bt.sets)] == [stored]


def test_beyond_ten_is_set_on_every_write(str_host):
    h = str_host
    bt = beyond_ten(h)
    p = player(h, level=10, xp=337500)
    record = body_at(h, 12.0)
    minute(h, p, record, 100.0)
    record["body"].levelDue = True
    minute(h, p, record, 100.0 + 1 / 60)
    assert len(lst(bt.sets)) == 2 and lst(p.cfg.steps) == []


def test_leaving_10_under_beyond_ten_zeroes_its_stored_xp_then_pins(str_host):
    h = str_host
    bt = beyond_ten(h)
    p = player(h, level=10, xp=337500)
    record = body_at(h, 9.5)
    minute(h, p, record, 100.0)
    assert lst(bt.sets) == [0]
    assert p.cfg.level == 9 and lst(p.cfg.xpSets) == [9]
    assert p.cfg.xp == pytest.approx(337500 + 0.5 * 150000, abs=1e-6)


def test_leaving_a_written_10_already_demoted_to_9_zeroes_the_stored_xp(str_host):
    # native fell to 9 before the write (a rust pass the guard missed); the record wrote 10
    h = str_host
    bt = beyond_ten(h)
    p = player(h, level=9, xp=337500)
    record = body_at(h, 9.5)
    record["body"].wroteL = 10
    record["body"].levelDue = True
    minute(h, p, record, 100.0)
    assert lst(bt.sets) == [0] and lst(p.cfg.xpSets) == [9]


SERVER_SYNC = r"""
function()
    local srv = { syncs = {} }
    srv.SendPerkSync = function(player, perk, old, new)
        srv.syncs[#srv.syncs + 1] = { perk = perk, old = old, new = new }
    end
    BeyondTenServer = srv
    return srv
end
"""


def test_a_mastery_write_sends_beyond_tens_client_sync(str_host):
    h = str_host
    saved = h.G.BeyondTenServer
    try:
        bt = beyond_ten(h)
        bt.SetStoredXP = h.rt.eval(
            "function(bt) return function(c, perk, v) bt.sets[#bt.sets + 1] = v; return v, 10, 12 end end")(bt)
        srv = h.rt.eval(SERVER_SYNC)()
        p = player(h, level=10, xp=337500)
        minute(h, p, body_at(h, 12.0), 100.0)
        assert lst(bt.sets) == [2100] and len(lst(srv.syncs)) == 1
        s = srv.syncs[1]
        assert h.rt.eval("rawequal")(s.perk, h.G.Perks.Strength) and (s.old, s.new) == (10, 12)
    finally:
        h.G.BeyondTenServer = saved


def test_a_mastery_write_without_beyond_ten_server_raises_nothing(str_host):
    h = str_host
    saved = h.G.BeyondTenServer
    h.G.BeyondTenServer = None
    try:
        bt = beyond_ten(h)
        p = player(h, level=10, xp=337500)
        record = body_at(h, 12.0)
        failures = STR(h).stats.failures
        minute(h, p, record, 100.0)
        assert lst(bt.sets) == [2100] and record["body"].wroteL == 10
        assert STR(h).stats.failures == failures
        h.G.BeyondTenServer = h.rt.eval("function() return { SendPerkSync = function() error('sync boom') end } end")()
        record["body"].levelDue = True
        minute(h, p, record, 100.0 + 1 / 60)
        assert len(lst(bt.sets)) == 2 and STR(h).stats.failures == failures
    finally:
        h.G.BeyondTenServer = saved


def test_below_10_beyond_ten_is_left_alone(str_host):
    h = str_host
    bt = beyond_ten(h)
    p = player(h, level=5, xp=40000)
    minute(h, p, body_at(h, 7.5), 100.0)
    assert lst(bt.sets) == [] and lst(p.cfg.xpSets) == [7]


def test_another_beyond_ten_api_version_parks_as_without_it(str_host):
    h = str_host
    bt = beyond_ten(h, version=2)
    p = player(h, level=10, xp=400000)
    minute(h, p, body_at(h, 12.0), 100.0)
    assert lst(bt.sets) == [] and lst(p.cfg.xpSets) == [9]


def test_missing_push_global_is_counted(str_host):
    h = str_host
    saved = h.G.sendSyncPlayerFields
    h.G.sendSyncPlayerFields = None
    try:
        p = player(h, level=0, xp=0, traits=[])
        miss = STR(h).stats.pushMissing
        assert STR(h).remap(p, 0) is True
    finally:
        h.G.sendSyncPlayerFields = saved
    assert traits(p) == ["WEAK"]
    assert STR(h).stats.pushMissing == miss + 1


def test_an_unreadable_world_age_skips_the_step(str_host):
    h = str_host
    saved = h.G.getGameTime
    h.G.getGameTime = lambda: h.table({})      # no getWorldAgeHours
    p = player(h, level=5, xp=0, delta=0.5)
    record = record_for(h)
    bad = STR(h).stats.badReads
    try:
        minute(h, p, record, 100.0)
    finally:
        h.G.getGameTime = saved
    assert STR(h).stats.badReads == bad + 1
    assert writes(p) == [] and deltas(p) == []


def test_an_unreadable_level_before_any_write_writes_no_carry(str_host):
    # no native level and no written one: no write, no carry, counted
    h = str_host
    p = player(h, level=None, delta=0.5)
    bad = STR(h).stats.badReads
    minute(h, p, record_for(h), 100.0)
    assert deltas(p) == [] and STR(h).stats.badReads == bad + 1
    saved = h.G.Perks
    h.G.Perks = None
    try:
        p = player(h, level=9, delta=0.5)
        minute(h, p, record_for(h), 100.0)
    finally:
        h.G.Perks = saved
    assert deltas(p) == [] and STR(h).stats.badReads == bad + 2


FAILING_TRAITS = r"""
function(p)
    -- the trait collection answers get, but its add and remove members are absent
    p.getCharacterTraits = function(self)
        return { get = function(s, t) return self.cfg.traits[t] == true end }
    end
    return p
end
"""


def test_a_failing_add_or_remove_counts_no_repair_and_pushes_nothing(str_host):
    # re-review: a remap whose add or remove fails changed nothing, so it must not count a repair and
    # push every minute
    h = str_host
    p = h.rt.eval(FAILING_TRAITS)(player(h, level=3, xp=10500, traits=["STRONG"]))
    pushes = h.G.NR_TEST_PUSHES
    assert STR(h).remap(p, 3) is False
    assert STR(h).remap(p, 3) is False
    assert traits(p) == ["STRONG"]             # nothing could change
    assert h.G.NR_TEST_PUSHES == pushes


def _code():
    with open(STRENGTH, encoding="utf-8") as fh:
        return "\n".join(l.split("--")[0] for l in fh.read().splitlines())


def _calls(code, name):
    # a method or global call, or an NR.call by name; prose in a limitation string is not a call
    return re.findall(r"[:.]%s\b|\"%s\"|\b%s\s*\(" % (name, name, name), code)


def test_never_calls_the_debug_setter_the_xp_method_or_the_carry_base():
    # ruling 13-8's primary branch steps the level; the debug setter is the fallback this build does not take
    code = _code().replace("Events.AddXP", "")                # the capture listens to the event (Task 13)
    for name in ("setPerkLevelDebug", "AddXP", "setMaxWeightBase"):
        assert _calls(code, name) == [], name


def test_the_level_route_lives_in_step_level_alone():
    # amendment 1: a Task 0 finding swaps STR.stepLevel only
    code = _code()
    body = code[code.index("function STR.stepLevel"):code.index("function STR.pin")]
    for name in ("LevelPerk", "LoseLevel"):
        assert len(_calls(code, name)) == 1 and len(_calls(body, name)) == 1, name
    pin = code[code.index("function STR.pin"):code.index("local function mastery")]
    assert len(_calls(code, "setXPToLevel")) == 1 and len(_calls(pin, "setXPToLevel")) == 1


# --- the carry delta --------------------------------------------------------------------------------

def test_carry_delta_from_body_fat(str_host):
    h = str_host
    p = player(h, level=5, xp=40000, delta=1.0)
    record = record_for(h)
    body = record["body"]
    body.fm = 33.0
    body.lm = 66.0
    body.lx = 1.0                              # the body mass fm + lm + lx: 100 kg at 33 % fat (ruling 13-20)
    body.wroteL = 5                            # written already: the carry alone
    body.levelDue = False
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


@pytest.mark.parametrize("level, factor", [(0, 0.75), (2, 0.9), (5, 1.0), (7, 1.25), (9, 1.5), (10, 1.5)])
def test_carry_delta_scales_the_written_bands_trait_factor(str_host, level, factor):
    # ruling 13-7: the trait factor is K.strength.traitCarry of the written level's band (#2144), from native 5
    h = str_host
    p = player(h, level=5, xp=40000, delta=0.5)
    record = body_at(h, level + 0.5)
    minute(h, p, record, 100.0)
    assert record["body"].wroteL == level
    assert deltas(p) == [pytest.approx(factor, abs=1e-12)]    # eAcute 0 at a lean enough body


def test_the_carry_reads_the_written_level_not_the_native(str_host):
    # an unreadable native level writes nothing; the carry keeps the written band
    h = str_host
    p = player(h, level=None, delta=0.5)
    record = record_for(h)
    record["body"].wroteL = 7
    minute(h, p, record, 100.0)
    assert deltas(p) == [1.25]


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


def test_limitations(str_host):
    h = str_host
    lim = list(STR(h).limitations.values())
    assert ("the carry delta's acute inputs (dehydration, sweat, hours awake, caffeine, clinical vitamin D) "
            "read the current minute's fluids, acute and nutrients sub-tables") in lim
    assert ("an unreadable native level writes no level that minute; the carry then reads the last written level's "
            "band, and nothing before the first write") in lim
    assert ("the engine's XP grant does not reach a sleeping character, and the bar's fraction lands through it, so "
            "a level write due while the character sleeps waits until it wakes") in lim
    assert not any("ceiling" in x or "six-hour" in x for x in lim)
    # shipped text names register rows, never plan tasks or rulings
    assert not any("Task " in x or "ruling" in x for x in lim)


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
        NutritionRevamp.server.players = {}
    """)
    names = sorted(["NR_Server_Strength.lua", "NR_Server_Metabolism.lua", "NR_Server_Kinetics.lua",
                    "NR_Server_Minute.lua"])
    assert names == ["NR_Server_Kinetics.lua", "NR_Server_Metabolism.lua", "NR_Server_Minute.lua",
                     "NR_Server_Strength.lua"]
    for n in names:
        with open(os.path.join(SERVER, n), encoding="utf-8") as fh:
            load(fh.read(), "@" + n)()
    rt.execute("for i = 1, #NR_STARTED do NR_STARTED[i]() end")
    rt.execute("for i = 1, #NR_STARTED do NR_STARTED[i]() end")   # a second start wires nothing twice
    G = rt.globals()
    S = G.NutritionRevamp.server
    same = rt.eval("rawequal")
    assert same(S.minute.steps["metabolism"], S.metabolism.minute)
    assert same(S.minute.steps["strength"], S.strength.minute)
    order = [S.minute.ORDER[i] for i in range(1, len(S.minute.ORDER) + 1)]
    assert order.index("metabolism") < order.index("strength")
    assert S.strength.wired is True


# --- the Plan 4 acute inputs: the current minute's fluids, acute and nutrients sub-tables ---------------

def _acute_delta(h, nutrients=None, fluids=None, acute=None, tod=14.0, sleep_on=True):
    # tod is the body clock's hour (record.acute.bodyHour, which the carry's morning band reads since Plan 16 Task 4)
    p = player(h, level=5, xp=40000, delta=1.0)
    record = record_for(h)
    if nutrients is not None:
        record.nutrients = h.table(nutrients)
    if fluids is not None:
        record.fluids = h.table(fluids)
    if acute is not None:
        a = h.K.acute["new"](99.0)
        for k, v in acute.items():
            a[k] = v
        a.bodyOn = True
        a.bodyHour = tod
        record.acute = a
    h.G.NR_TEST_TOD = tod
    S = h.G.NutritionRevamp.server
    saved = S.options
    S.options = h.table(dict(sleepOn=sleep_on))                # the options poll's sleep setting, NR.sleepOn()
    try:
        minute(h, p, record, 100.0)
    finally:
        S.options = saved
    return record["body"]["delta"]


def test_a_pre_plan4_record_reads_eacute_zero(str_host):
    assert _acute_delta(str_host) == 1.0


def test_dehydration_five_percent_is_minus_six(str_host):
    h = str_host
    assert h.K.strength.eAcute(5, False, 0, 14.0, False, False, 0) == pytest.approx(-0.06, abs=1e-12)
    assert _acute_delta(h, fluids=dict(dehydPct=5)) == pytest.approx(1 - 0.06, abs=1e-12)


def test_sweat_active_dehydration_scales_the_step(str_host):
    h = str_host
    want = 1 + h.K.strength.eAcute(5, True, 0, 14.0, False, False, 0)
    assert _acute_delta(h, fluids=dict(dehydPct=5, sweatActive=True)) == pytest.approx(want, abs=1e-12)
    assert want == pytest.approx(1 - 0.09, abs=1e-12)


def test_twenty_eight_hours_awake_is_minus_four(str_host):
    h = str_host
    assert _acute_delta(h, acute=dict(awakeH=28.0)) == pytest.approx(1 - 0.04, abs=1e-12)
    assert _acute_delta(h, acute=dict(awakeH=28.0), tod=8.0) == pytest.approx(1 - 0.02, abs=1e-12)
    # Plan 16 Task 4: with sleep off there is no body clock, so no morning halving (and the hour of the world is not read)
    assert _acute_delta(h, acute=dict(awakeH=28.0), tod=8.0, sleep_on=False) == pytest.approx(1 - 0.04, abs=1e-12)


def test_caffeine_active_is_plus_two(str_host):
    h = str_host
    base = h.K.body.create(None, None, h.K.strength.DEFAULTS, 1)
    w = base.fm + base.lm                      # the no-trait body's mass, lx 0 (the dose is per kg of it)
    assert _acute_delta(h, acute=dict(caf=3 * w)) == pytest.approx(1.02, abs=1e-12)
    assert _acute_delta(h, acute=dict(caf=3 * w - 1)) == 1.0     # below 3 mg/kg: inactive


def test_vitamin_d_clinical_is_minus_three(str_host):
    assert _acute_delta(str_host, nutrients=dict(vitDClinical=True)) == pytest.approx(0.97, abs=1e-12)


def test_unreadable_sub_table_values_read_neutral_in_the_carry(str_host):
    h = str_host
    failures = STR(h).stats.failures
    d = _acute_delta(h, nutrients=dict(vitDClinical="yes"), fluids=dict(dehydPct=float("nan"), sweatActive=1),
                     acute=dict(awakeH=float("inf"), caf=float("nan")))
    assert d == 1.0
    assert STR(h).stats.failures == failures


def test_a_raising_push_global_is_counted_and_the_carry_still_written(str_host):
    # Plan 12 (S B6): the push is guarded as Effects' is; a raise skipped carry() for the minute.
    h = str_host
    saved = h.G.sendSyncPlayerFields
    h.G.sendSyncPlayerFields = h.rt.eval("function(p, n) error('the push raised') end")
    try:
        p = player(h, level=5, xp=0, traits=[], delta=1.0)
        record = record_for(h)
        body = record["body"]
        body.fm = 33.0
        body.lm = 67.0
        body.wroteL = 5
        body.levelDue = False
        h.G.NR_TEST_TOD = 14.0
        miss, cw, fails = STR(h).stats.pushMissing, STR(h).stats.carryWrites, STR(h).stats.failures
        assert STR(h).remap(p, 0) is True       # the remap's push raised: counted, the change stands
        minute(h, p, record, 100.0)
    finally:
        h.G.sendSyncPlayerFields = saved
    assert traits(p) == ["WEAK"]
    assert STR(h).stats.pushMissing == miss + 1
    assert STR(h).stats.carryWrites == cw + 1
    assert STR(h).stats.failures == fails


# --- the AddXP capture (Plan 13 Task 13; spec section 4, rulings 13-11, 13-12, 13-29) ------------------

# A player stand-in for the AddXP listener: every Java member it answers counts its call in cfg.calls.
XP_PLAYER = r"""
function(cfg)
    cfg.calls = {}
    local function hit(name) cfg.calls[name] = (cfg.calls[name] or 0) + 1 end
    local p = { cfg = cfg }
    p.getUsername = function(self) hit("getUsername"); return self.cfg.name end
    p.getNutrition = function(self)
        hit("getNutrition")
        return { getProteins = function(s) hit("getProteins"); return self.cfg.proteins end }
    end
    p.getXp = function(self)
        hit("getXp")
        return { getMultiplier = function(s, perk)
            hit("getMultiplier")
            if perk ~= Perks.Strength then error("the book read another perk") end
            return self.cfg.book
        end }
    end
    p.getPerkLevel = function(self, perk) hit("getPerkLevel"); return self.cfg.level end
    return p
end
"""

XP_SETUP = r"""
function(records, exe)
    local NR = NutritionRevamp
    local saved = { store = NR.server.store, fitness = NR.server.fitness, sv = SandboxVars, fit = Perks.Fitness, wood = Perks.Woodwork,
                    pinning = NR.server.strength.pinning, options = NR.server.options }
    NR.server.store = { records = records }
    NR.server.fitness = { typeOf = function(name) if name == nil then return nil end return exe[name] end }
    SandboxVars = { MultiplierConfig = { Global = 2.0, GlobalToggle = true, Strength = 4.0 } }
    Perks.Fitness = { name = "Fitness" }
    Perks.Woodwork = { name = "Woodwork" }
    return saved
end
"""

XP_TEARDOWN = r"""
function(saved)
    local NR = NutritionRevamp
    NR.server.store = saved.store
    NR.server.fitness = saved.fitness
    SandboxVars = saved.sv
    Perks.Fitness = saved.fit
    Perks.Woodwork = saved.wood
    NR.server.strength.pinning = saved.pinning
    NR.server.options = saved.options
end
"""


@pytest.fixture
def xp(str_host):
    h = str_host
    records = h.rt.table()
    exe = h.rt.table()
    saved = h.rt.eval(XP_SETUP)(records, exe)
    try:
        yield h, records, exe
    finally:
        h.rt.eval(XP_TEARDOWN)(saved)


def xp_player(h, name="admin", proteins=60.0, book=1.0, level=5):
    cfg = h.rt.table()
    cfg.name = name
    cfg.proteins = proteins
    cfg.book = book
    cfg.level = level
    return h.rt.eval(XP_PLAYER)(cfg)


def calls(p):
    return {k: v for k, v in p.cfg.calls.items()}


def xp_stats(h):
    return dict(STR(h).xpStats.items())


def grant(h, p, amount, perk="Strength"):
    STR(h).onXp(p, h.G.Perks[perk], amount)


def xp_record(h):
    """A record whose level 5 is written already (body.wroteL 5), so a grant at native 5 re-pins nothing."""
    record = record_for(h)
    record["body"].wroteL = 5
    record["body"].levelDue = False
    return record


def test_a_fitness_grant_adds_nothing_and_reads_no_java(xp):
    h, records, exe = xp
    records.admin = xp_record(h)
    exe.admin = "pushups"
    p = xp_player(h)
    before = xp_stats(h)
    grant(h, p, 9.0, "Fitness")
    assert records.admin.body.sigDay == 0
    assert calls(p) == {}
    assert xp_stats(h) == before


def test_another_perk_adds_nothing_and_reads_no_java(xp):
    h, records, exe = xp
    records.admin = xp_record(h)
    exe.admin = "pushups"
    p = xp_player(h)
    before = xp_stats(h)
    grant(h, p, 9.0, "Woodwork")
    assert records.admin.body.sigDay == 0
    assert calls(p) == {}
    assert xp_stats(h) == before


def test_a_missing_global_toggle_reads_on(xp):
    # the Java option's default is true, so a missing toggle applies Global
    h, records, exe = xp
    records.admin = xp_record(h)
    exe.admin = "squats"
    h.G.SandboxVars = h.table({"MultiplierConfig": {"Global": 2.0, "Strength": 4.0}})
    grant(h, xp_player(h, proteins=0.0), 8.0)
    assert abs(records.admin.body.sigDay - 4.0) < 1e-12


def test_a_zero_grant_is_ignored_and_reads_no_chain(xp):
    h, records, exe = xp
    records.admin = xp_record(h)
    p = xp_player(h)
    ign, caps = STR(h).xpStats.ignored, STR(h).xpStats.captures
    grant(h, p, 0.0)
    assert records.admin.body.sigDay == 0
    assert STR(h).xpStats.ignored == ign + 1 and STR(h).xpStats.captures == caps
    assert calls(p) == {"getUsername": 1, "getPerkLevel": 1}


def test_a_strength_grant_in_a_recorded_set_adds_the_full_share(xp):
    # 9 XP landed at proteins 60 (x1.5) under Global 2 (GlobalToggle): 9 / 1.5 / 2 = 3 (ruling 13-11)
    h, records, exe = xp
    records.admin = xp_record(h)
    exe.admin = "pushups"
    caps = STR(h).xpStats.captures
    grant(h, xp_player(h), 9.0)
    assert abs(records.admin.body.sigDay - 3.0) < 1e-12
    grant(h, xp_player(h), 9.0)
    assert abs(records.admin.body.sigDay - 6.0) < 1e-12        # accumulates into the day's slot (ruling 13-12)
    assert STR(h).xpStats.captures == caps + 2


def test_a_strength_grant_outside_a_set_adds_the_incidental_share(xp):
    h, records, exe = xp
    records.admin = xp_record(h)
    exe.bob = "pushups"                                          # another player's set
    grant(h, xp_player(h), 9.0)
    assert abs(records.admin.body.sigDay - 3.0 * h.K.strength.DEFAULTS.incidental) < 1e-12


def test_the_incidental_weight_is_the_servers_option(xp):
    h, records, exe = xp
    records.admin = xp_record(h)
    h.G.NutritionRevamp.server.options = h.table({"strength": {"incidental": 0.5}})
    grant(h, xp_player(h), 9.0)
    assert abs(records.admin.body.sigDay - 1.5) < 1e-12


def test_an_absent_fitness_adapter_reads_incidental(xp):
    h, records, exe = xp
    records.admin = xp_record(h)
    exe.admin = "pushups"
    h.G.NutritionRevamp.server.fitness = None
    grant(h, xp_player(h), 9.0)
    assert abs(records.admin.body.sigDay - 3.0 * h.K.strength.DEFAULTS.incidental) < 1e-12


def test_the_per_perk_multiplier_reads_without_the_global_toggle(xp):
    h, records, exe = xp
    records.admin = xp_record(h)
    exe.admin = "squats"
    h.G.SandboxVars.MultiplierConfig.GlobalToggle = False
    grant(h, xp_player(h, proteins=0.0), 8.0)
    assert abs(records.admin.body.sigDay - 2.0) < 1e-12        # 8 / 1 / Strength 4


def test_an_absent_or_bad_sandbox_multiplier_reads_1(xp):
    h, records, exe = xp
    records.admin = xp_record(h)
    exe.admin = "squats"
    h.G.SandboxVars = None
    grant(h, xp_player(h, proteins=0.0), 8.0)
    assert abs(records.admin.body.sigDay - 8.0) < 1e-12
    h.G.SandboxVars = h.table({"MultiplierConfig": {"Global": float("nan"), "GlobalToggle": True}})
    grant(h, xp_player(h, proteins=0.0), 8.0)
    assert abs(records.admin.body.sigDay - 16.0) < 1e-12
    h.G.SandboxVars = h.table({})
    grant(h, xp_player(h, proteins=0.0), 8.0)
    assert abs(records.admin.body.sigDay - 24.0) < 1e-12


def test_the_book_multiplier_divides_above_1_only(xp):
    h, records, exe = xp
    records.admin = xp_record(h)
    exe.admin = "squats"
    h.G.SandboxVars = None
    grant(h, xp_player(h, proteins=0.0, book=4.0), 8.0)
    assert abs(records.admin.body.sigDay - 2.0) < 1e-12
    grant(h, xp_player(h, proteins=0.0, book=0.5), 8.0)
    assert abs(records.admin.body.sigDay - 10.0) < 1e-12
    grant(h, xp_player(h, proteins=0.0, book=None), 8.0)      # unreadable: 1
    assert abs(records.admin.body.sigDay - 18.0) < 1e-12


def test_pinning_blocks_the_capture(xp):
    h, records, exe = xp
    records.admin = xp_record(h)
    exe.admin = "pushups"
    p = xp_player(h, level=9)
    before = xp_stats(h)
    STR(h).pinning = True
    grant(h, p, 9.0)
    assert records.admin.body.sigDay == 0
    assert records.admin.body.levelDue is False and records.admin.body.wroteL == 5
    assert calls(p) == {}
    assert xp_stats(h) == before


def test_a_player_with_no_record_gets_none(xp):
    h, records, exe = xp
    exe.admin = "pushups"
    ign = STR(h).xpStats.ignored
    grant(h, xp_player(h), 9.0)
    assert records.admin is None
    assert STR(h).xpStats.ignored == ign + 1
    records.admin = h.rt.table()                                 # a record with no body yet
    grant(h, xp_player(h), 9.0)
    assert records.admin.body is None
    assert STR(h).xpStats.ignored == ign + 2


def test_an_absent_store_creates_nothing(xp):
    h, records, exe = xp
    h.G.NutritionRevamp.server.store = None
    ign = STR(h).xpStats.ignored
    grant(h, xp_player(h), 9.0)
    assert h.G.NutritionRevamp.server.store is None
    assert STR(h).xpStats.ignored == ign + 1


def test_the_store_is_attached_when_its_records_are_absent(xp):
    # bodyOf reads S.attach() when S.records is nil (Training's helper, moved here)
    h, records, exe = xp
    records.admin = xp_record(h)
    exe.admin = "pushups"
    store = h.G.NutritionRevamp.server.store
    store.records = None
    store.attach = h.rt.eval("function(recs) return function() return recs end end")(records)
    grant(h, xp_player(h), 9.0)
    assert abs(records.admin.body.sigDay - 3.0) < 1e-12


def test_a_grant_that_crosses_a_level_repins_at_once(xp):
    # ruling 13-29: the listener writes the level back, reading no clock
    h, records, exe = xp
    records.admin = xp_record(h)
    body = records.admin.body
    p = player(h, level=5, xp=37500)
    grant(h, p, 9.0)
    assert lst(p.cfg.xpSets) == []                               # same level: nothing
    p.cfg.level = 6
    p.cfg.xp = 67600
    lw = STR(h).stats.levelWrites
    grant(h, p, 30100.0)
    assert lst(p.cfg.steps) == [-1] and p.cfg.level == 5
    assert lst(p.cfg.xpSets) == [5] and p.cfg.xp == 37500
    assert body.wroteL == 5 and body.levelDue is False
    assert STR(h).stats.levelWrites == lw + 1
    assert body.sigDay > 0                                       # the grant still trains


def test_a_rust_grant_captures_nothing_reads_no_chain_and_still_repins(xp):
    h, records, exe = xp
    records.admin = xp_record(h)
    body = records.admin.body
    p = player(h, level=4, xp=37000)
    ign = STR(h).xpStats.ignored
    grant(h, p, -30.0)
    assert body.sigDay == 0
    assert lst(p.cfg.steps) == [1] and p.cfg.level == 5 and lst(p.cfg.grants) == [0]
    assert STR(h).xpStats.ignored == ign + 1
    for name in ("getNutrition", "getProteins", "getMultiplier"):
        assert name not in calls(p), name                         # the capture's chain unread; the pin needs none


def test_an_unreadable_level_repins_nothing(xp):
    h, records, exe = xp
    records.admin = xp_record(h)
    lw = STR(h).stats.levelWrites
    grant(h, xp_player(h, level=None), 9.0)
    assert STR(h).stats.levelWrites == lw
    assert records.admin.body.sigDay > 0


def test_a_grant_on_a_parked_10_reparks_it(xp):
    # spec section 7: the park keeps AddXP's event firing; a grant raises the XP and the listener re-parks it
    h, records, exe = xp
    records.admin = body_at(h, 11.0)
    p = player(h, level=8, xp=200000)
    minute(h, p, records.admin, 100.0)
    assert p.cfg.level == 10 and p.cfg.xp == 337500
    p.cfg.xp = p.cfg.xp + 100                                   # the engine lands a granted 100
    grant(h, p, 100.0)
    assert p.cfg.xp == 337500 and lst(p.cfg.xpSets) == [9, 9]
    assert lst(p.cfg.grants) == [0]                             # the re-park lowers: setXPToLevel only
    assert records.admin.body.sigDay > 0


def test_a_grant_at_10_under_beyond_ten_resets_its_stored_xp(xp):
    # the body is the only source of the level (ruling 13-42): a grant BeyondTen would bank is set back
    h, records, exe = xp
    bt = beyond_ten(h)
    records.admin = body_at(h, 12.0)
    records.admin.body.wroteL = 10
    records.admin.body.levelDue = False
    p = player(h, level=10, xp=337500)
    grant(h, p, 100.0)
    assert lst(bt.sets) == [2100] and lst(p.cfg.xpSets) == []


def test_a_strength_grant_makes_six_java_reads(xp):
    # Rule 6: the name, the protein store, the book multiplier and the level; the sandbox and the set are Lua
    h, records, exe = xp
    records.admin = xp_record(h)
    p = xp_player(h)
    grant(h, p, 9.0)
    assert calls(p) == {"getUsername": 1, "getNutrition": 1, "getProteins": 1, "getXp": 1, "getMultiplier": 1,
                        "getPerkLevel": 1}


def test_an_unreadable_protein_store_reads_0(xp):
    h, records, exe = xp
    records.admin = xp_record(h)
    exe.admin = "squats"
    h.G.SandboxVars = None
    grant(h, xp_player(h, proteins=None), 8.0)
    assert abs(records.admin.body.sigDay - 8.0) < 1e-12


def test_a_raising_capture_is_counted_never_raised(xp):
    h, records, exe = xp
    records.admin = xp_record(h)
    orig = h.K.strength.capture
    h.K.strength.capture = h.rt.eval("function() error('boom') end")
    fails = STR(h).xpStats.failures
    try:
        grant(h, xp_player(h), 9.0)
    finally:
        h.K.strength.capture = orig
    assert STR(h).xpStats.failures == fails + 1
    assert "boom" in str(STR(h).xpError)
    assert records.admin.body.sigDay == 0


def test_the_capture_counters_stay_out_of_the_minutes_stats(str_host):
    # the golden trace walks STR.stats (golden_trace.STATS_NAMES); the capture counts beside it in STR.xpStats
    st = dict(STR(str_host).stats.items())
    for name in ("captures", "ignored"):
        assert name not in st


# --- the level-10 guard (ruling 13-10) ------------------------------------------------------------------

XP_UPDATE = r"""
function()
    local xu = { origCalls = {} }
    xu.checkForLosingLevel = function(playerObj, perk)
        xu.origCalls[#xu.origCalls + 1] = perk
        return "orig"
    end
    NR_StrengthGuardInstalled = {}
    xpUpdate = xu
    return xu
end
"""


@pytest.fixture
def guard(xp):
    h, records, exe = xp
    xu = h.rt.eval(XP_UPDATE)()
    yield h, records, xu


def test_the_guard_returns_for_a_parked_strength(guard):
    h, records, xu = guard
    assert STR(h).installLevelGuard() is True
    records.admin = xp_record(h)
    records.admin.body.wroteL = 10
    p = player(h, level=10, xp=337500)
    g = STR(h).stats.guarded
    assert xu.checkForLosingLevel(p, h.G.Perks.Strength) is None
    assert lst(xu.origCalls) == [] and STR(h).stats.guarded == g + 1
    assert p.cfg.level == 10


def test_the_guard_calls_the_original_for_fitness(guard):
    h, records, xu = guard
    STR(h).installLevelGuard()
    records.admin = xp_record(h)
    records.admin.body.wroteL = 10
    p = player(h, level=10, xp=337500)
    assert xu.checkForLosingLevel(p, h.G.Perks.Fitness) == "orig"
    assert len(lst(xu.origCalls)) == 1 and h.rt.eval("rawequal")(xu.origCalls[1], h.G.Perks.Fitness)


@pytest.mark.parametrize("native, wrote", [(10, 9), (9, 10), (None, 10), (10, None)])
def test_the_guard_calls_the_original_unless_native_and_written_are_10(guard, native, wrote):
    h, records, xu = guard
    STR(h).installLevelGuard()
    records.admin = xp_record(h)
    records.admin.body.wroteL = wrote
    p = player(h, level=native, xp=337500)
    assert xu.checkForLosingLevel(p, h.G.Perks.Strength) == "orig"
    assert len(lst(xu.origCalls)) == 1


def test_the_guard_calls_the_original_for_a_player_with_no_record(guard):
    h, records, xu = guard
    STR(h).installLevelGuard()
    p = player(h, level=10, xp=337500, name="stranger")
    assert xu.checkForLosingLevel(p, h.G.Perks.Strength) == "orig"


def test_the_guard_wraps_once_and_names_its_sentinel(guard):
    h, records, xu = guard
    STR(h).installLevelGuard()
    first = xu.checkForLosingLevel
    assert STR(h).installLevelGuard() is True
    assert h.rt.eval("rawequal")(xu.checkForLosingLevel, first)
    S = h.G.NR_StrengthGuardInstalled
    assert h.rt.eval("rawequal")(S.wrapper, first) and h.rt.eval("rawequal")(S["class"], xu)


def test_no_xp_update_installs_nothing(str_host):
    h = str_host
    h.G.xpUpdate = None
    assert STR(h).installLevelGuard() is False


def test_the_guard_is_installed_at_server_start():
    rt = _wiring_host(True)
    rt.execute("""
        NR_GUARD_ORIG = function(p, perk) return "orig" end
        xpUpdate = { checkForLosingLevel = NR_GUARD_ORIG }
    """)
    G = rt.globals()
    assert rt.eval("rawequal")(G.xpUpdate.checkForLosingLevel, G.NR_GUARD_ORIG)   # nothing at load
    rt.execute("for i = 1, #NR_STARTED do NR_STARTED[i]() end")
    assert not rt.eval("rawequal")(G.xpUpdate.checkForLosingLevel, G.NR_GUARD_ORIG)
    assert rt.eval("rawequal")(G.NR_StrengthGuardInstalled.orig, G.NR_GUARD_ORIG)


def _wiring_host(server):
    rt = lua51.LuaRuntime(unpack_returned_tuples=True)
    load = rt.eval("function(src, name) return assert(loadstring(src, name)) end")
    with open(CORE, encoding="utf-8") as fh:
        load(fh.read(), "@NR_Core.lua")()
    rt.execute(r"""
        NR_STARTED = {}
        NR_XP = {}
        Events = { OnServerStarted = { Add = function(fn) NR_STARTED[#NR_STARTED + 1] = fn end },
                   AddXP = { Add = function(fn) NR_XP[#NR_XP + 1] = fn end } }
        NutritionRevamp.server.players = {}
    """)
    rt.globals().isServer = rt.eval("function() return %s end" % ("true" if server else "false"))
    for n in ("NR_Server_Minute.lua", "NR_Server_Strength.lua"):
        with open(os.path.join(SERVER, n), encoding="utf-8") as fh:
            load(fh.read(), "@" + n)()
    return rt


def test_the_addxp_listener_is_wired_once_at_server_start():
    rt = _wiring_host(True)
    G = rt.globals()
    assert len(G.NR_XP) == 0                                     # nothing at load
    rt.execute("for i = 1, #NR_STARTED do NR_STARTED[i]() end")
    rt.execute("for i = 1, #NR_STARTED do NR_STARTED[i]() end")  # a second start wires nothing twice
    assert len(G.NR_XP) == 1
    assert rt.eval("rawequal")(G.NR_XP[1], G.NutritionRevamp.server.strength.onXp)


def test_the_addxp_listener_is_not_wired_on_a_client():
    rt = _wiring_host(False)
    rt.execute("for i = 1, #NR_STARTED do NR_STARTED[i]() end")
    assert len(rt.globals().NR_XP) == 0



# --- Plan 13 Task 10c: the level-drop hysteresis on the write (Angus, 2026-10-15: "Drop only 0.25 below") ---------

def test_an_untrained_start_at_five_holds_five_after_an_underfed_day(str_host):
    # ledger concern 4: a fresh untrained character at exactly 5.0 floored to native 4 (Feeble's band) after one
    # underfed day; the drop now waits until the level is 0.25 below 5
    h = str_host
    p = player(h, level=5, xp=37500)
    record = body_at(h, 5.0)
    body = record["body"]
    body.levelDue = True
    minute(h, p, record, 100.0)
    assert body.wroteL == 5 and p.cfg.level == 5
    body.lm = h.K.strength.fOfLevel(4.97, body.N0, body.T, h.K.strength.DEFAULTS)    # one underfed day
    body.levelDue = True
    minute(h, p, record, 100.0 + 1 / 60)
    assert p.cfg.level == 5 and body.wroteL == 5 and lst(p.cfg.steps) == []
    assert traits(p) == []                                     # no Feeble band
    assert p.cfg.xp == 37500                                   # held: level 5's starting total, an empty bar
    body.lm = h.K.strength.fOfLevel(4.7, body.N0, body.T, h.K.strength.DEFAULTS)
    body.levelDue = True
    minute(h, p, record, 100.0 + 2 / 60)
    assert p.cfg.level == 4 and body.wroteL == 4               # 0.3 below: dropped to floor(4.7 + 0.25)


def test_a_rise_lands_at_the_whole_number(str_host):
    h = str_host
    p = player(h, level=5, xp=37500)
    record = body_at(h, 6.0)
    record["body"].wroteL = 5
    record["body"].levelDue = True
    minute(h, p, record, 100.0)
    assert p.cfg.level == 6 and record["body"].wroteL == 6


def test_a_native_ten_at_9_8_holds_ten_parked(str_host):
    h = str_host
    p = player(h, level=10, xp=337500)
    record = body_at(h, 9.8)
    record["body"].wroteL = 10
    record["body"].levelDue = True
    minute(h, p, record, 100.0)
    assert p.cfg.level == 10 and lst(p.cfg.steps) == [] and record["body"].wroteL == 10
    assert p.cfg.xp == 337500                                  # the park at the level-9 total
    record["body"].lm = h.K.strength.fOfLevel(9.7, record["body"].N0, record["body"].T, h.K.strength.DEFAULTS)
    record["body"].levelDue = True
    minute(h, p, record, 100.0 + 1 / 60)
    assert p.cfg.level == 9 and record["body"].wroteL == 9
    assert p.cfg.xp == pytest.approx(337500 + 0.7 * 150000, abs=1e-6)


def test_under_beyond_ten_a_ten_at_9_8_holds_ten_and_its_stored_xp_reads_ten(str_host):
    h = str_host
    bt = beyond_ten(h)
    p = player(h, level=10, xp=337500)
    record = body_at(h, 9.8)
    record["body"].wroteL = 10
    record["body"].levelDue = True
    minute(h, p, record, 100.0)
    assert p.cfg.level == 10 and record["body"].wroteL == 10
    assert lst(p.cfg.xpSets) == [] and lst(p.cfg.grants) == []    # never native XP at native 10
    assert lst(bt.sets) == [0]                                     # level 10's mastery start


def test_a_drop_due_while_asleep_waits_then_follows_the_hysteresis(str_host):
    h = str_host
    p = player(h, level=7, xp=130000)
    h.rt.eval("function(p) p.isAsleep = function(s) return p.cfg.asleep end end")(p)
    p.cfg.asleep = True
    record = body_at(h, 6.5)
    record["body"].wroteL = 7
    record["body"].levelDue = True
    minute(h, p, record, 100.0)
    assert lst(p.cfg.steps) == [] and record["body"].levelDue is True and record["body"].wroteL == 7
    p.cfg.asleep = False
    minute(h, p, record, 100.0 + 1 / 60)
    assert p.cfg.level == 6 and record["body"].wroteL == 6 and record["body"].levelDue is False
    assert p.cfg.xp == pytest.approx(67500 + 0.5 * 60000, abs=1e-6)
