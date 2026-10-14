"""NR_Server_Strength, driven through table-of-functions Java stand-ins.

The file is a server/ file the kernel host does not load, so it is loaded on top of the session host
the way test_metabolism_shape.py loads NR_Server_Metabolism.lua. NR.call indexes obj[name] and calls it
with obj first, so a Lua table of function fields stands in for a Java object. The body is built with
the real K.body.new over K.body.create and every level, trait and carry read is stubbed by hand; the kernel math is
the real kernel. A stub proves the wiring, the order and the guards, not the engine's real getters,
which the live acceptance runs read. Since Plan 13 Task 12 the minute writes no level (the XP-implied level, the
ceiling and the write policy are removed); the carry's trait factor reads the native level's band until Task 14
(ruling 13-28), and STR.ladder and STR.remap stay for the level write.
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

def test_the_minute_writes_no_level_reads_no_xp_and_runs_no_remap(str_host):
    # Plan 13 Task 12: the level is the day close's (written from Task 14); the minute reads the native level once
    h = str_host
    p = player(h, level=8, xp=0, traits=["WEAK"])
    reads = h.rt.eval("{ xp = 0 }")
    h.rt.eval("function(p, C) local g = p.getXp; p.getXp = function(s) C.xp = C.xp + 1; return g(s) end end")(p, reads)
    pushes = h.G.NR_TEST_PUSHES
    record = record_for(h)
    minute(h, p, record, 100.0)
    assert writes(p) == [] and reads.xp == 0
    assert traits(p) == ["WEAK"] and h.G.NR_TEST_PUSHES == pushes
    for gone in ("writes", "bandRepairs"):
        assert STR(h).stats[gone] is None, gone
    for gone in ("vanillaLevel", "MAX_DT_H"):
        assert STR(h)[gone] is None, gone
    assert record["body"]["strAgeH"] is None


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


def test_an_unreadable_level_writes_no_carry(str_host):
    # the carry's trait factor reads the native level (ruling 13-28): no level, no write, counted
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


def test_never_calls_a_granting_or_leveling_member():
    with open(STRENGTH, encoding="utf-8") as fh:
        code = "\n".join(l.split("--")[0] for l in fh.read().splitlines())
    code = code.replace("Events.AddXP", "")                   # the capture listens to the event (Task 13)
    for name in ("LevelPerk", "LoseLevel", "setXPToLevel", "addXp", "AddXP", "setMaxWeightBase"):
        # a method or global call, or an NR.call by name; prose in a limitation string is not a call
        pattern = r"[:.]%s\b|\"%s\"|\b%s\s*\(" % (name, name, name)
        assert re.search(pattern, code) is None, name


# --- the carry delta --------------------------------------------------------------------------------

def test_carry_delta_from_body_fat(str_host):
    h = str_host
    p = player(h, level=5, xp=40000, delta=1.0)
    record = record_for(h)
    body = record["body"]
    body.fm = 33.0
    body.lm = 66.0
    body.lx = 1.0                              # the body mass fm + lm + lx: 100 kg at 33 % fat (ruling 13-20)
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
def test_carry_delta_scales_the_trait_factor(str_host, level, factor):
    # ruling 13-28: until Task 14 the trait factor is K.strength.traitCarry of the native level's band (#2144)
    h = str_host
    p = player(h, level=level, xp=40000, delta=0.5)
    record = record_for(h)
    minute(h, p, record, 100.0)
    assert deltas(p) == [factor]               # lean body: eAcute 0


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
    assert ("no level is written yet and the carry's trait factor reads the native level's band; an unreadable "
            "level writes no carry that minute") in lim
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

def _acute_delta(h, nutrients=None, fluids=None, acute=None, tod=14.0):
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
        record.acute = a
    h.G.NR_TEST_TOD = tod
    minute(h, p, record, 100.0)
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


def test_a_fitness_grant_adds_nothing_and_reads_no_java(xp):
    h, records, exe = xp
    records.admin = record_for(h)
    exe.admin = "pushups"
    p = xp_player(h)
    before = xp_stats(h)
    grant(h, p, 9.0, "Fitness")
    assert records.admin.body.sigDay == 0
    assert calls(p) == {}
    assert xp_stats(h) == before


def test_another_perk_adds_nothing_and_reads_no_java(xp):
    h, records, exe = xp
    records.admin = record_for(h)
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
    records.admin = record_for(h)
    exe.admin = "squats"
    h.G.SandboxVars = h.table({"MultiplierConfig": {"Global": 2.0, "Strength": 4.0}})
    grant(h, xp_player(h, proteins=0.0), 8.0)
    assert abs(records.admin.body.sigDay - 4.0) < 1e-12


def test_a_zero_grant_is_ignored_and_reads_no_chain(xp):
    h, records, exe = xp
    records.admin = record_for(h)
    p = xp_player(h)
    ign, caps = STR(h).xpStats.ignored, STR(h).xpStats.captures
    grant(h, p, 0.0)
    assert records.admin.body.sigDay == 0
    assert STR(h).xpStats.ignored == ign + 1 and STR(h).xpStats.captures == caps
    assert calls(p) == {"getUsername": 1, "getPerkLevel": 1}


def test_a_strength_grant_in_a_recorded_set_adds_the_full_share(xp):
    # 9 XP landed at proteins 60 (x1.5) under Global 2 (GlobalToggle): 9 / 1.5 / 2 = 3 (ruling 13-11)
    h, records, exe = xp
    records.admin = record_for(h)
    exe.admin = "pushups"
    caps = STR(h).xpStats.captures
    grant(h, xp_player(h), 9.0)
    assert abs(records.admin.body.sigDay - 3.0) < 1e-12
    grant(h, xp_player(h), 9.0)
    assert abs(records.admin.body.sigDay - 6.0) < 1e-12        # accumulates into the day's slot (ruling 13-12)
    assert STR(h).xpStats.captures == caps + 2


def test_a_strength_grant_outside_a_set_adds_the_incidental_share(xp):
    h, records, exe = xp
    records.admin = record_for(h)
    exe.bob = "pushups"                                          # another player's set
    grant(h, xp_player(h), 9.0)
    assert abs(records.admin.body.sigDay - 3.0 * h.K.strength.DEFAULTS.incidental) < 1e-12


def test_the_incidental_weight_is_the_servers_option(xp):
    h, records, exe = xp
    records.admin = record_for(h)
    h.G.NutritionRevamp.server.options = h.table({"strength": {"incidental": 0.5}})
    grant(h, xp_player(h), 9.0)
    assert abs(records.admin.body.sigDay - 1.5) < 1e-12


def test_an_absent_fitness_adapter_reads_incidental(xp):
    h, records, exe = xp
    records.admin = record_for(h)
    exe.admin = "pushups"
    h.G.NutritionRevamp.server.fitness = None
    grant(h, xp_player(h), 9.0)
    assert abs(records.admin.body.sigDay - 3.0 * h.K.strength.DEFAULTS.incidental) < 1e-12


def test_the_per_perk_multiplier_reads_without_the_global_toggle(xp):
    h, records, exe = xp
    records.admin = record_for(h)
    exe.admin = "squats"
    h.G.SandboxVars.MultiplierConfig.GlobalToggle = False
    grant(h, xp_player(h, proteins=0.0), 8.0)
    assert abs(records.admin.body.sigDay - 2.0) < 1e-12        # 8 / 1 / Strength 4


def test_an_absent_or_bad_sandbox_multiplier_reads_1(xp):
    h, records, exe = xp
    records.admin = record_for(h)
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
    records.admin = record_for(h)
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
    records.admin = record_for(h)
    exe.admin = "pushups"
    p = xp_player(h, level=9)
    before = xp_stats(h)
    STR(h).pinning = True
    grant(h, p, 9.0)
    assert records.admin.body.sigDay == 0
    assert records.admin.body.levelDue is None
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
    records.admin = record_for(h)
    exe.admin = "pushups"
    store = h.G.NutritionRevamp.server.store
    store.records = None
    store.attach = h.rt.eval("function(recs) return function() return recs end end")(records)
    grant(h, xp_player(h), 9.0)
    assert abs(records.admin.body.sigDay - 3.0) < 1e-12


def test_a_grant_that_moves_the_level_off_wrote_l_stamps_level_due(xp):
    h, records, exe = xp
    records.admin = record_for(h)
    body = records.admin.body
    body.wroteL = 5
    grant(h, xp_player(h, level=5), 9.0)
    assert body.levelDue is None                                 # same level: no stamp
    grant(h, xp_player(h, level=6), 9.0)
    assert body.levelDue is True                                 # ruling 13-29 (Task 14: STR.repin)


def test_a_rust_grant_captures_nothing_reads_no_chain_and_still_checks_the_level(xp):
    h, records, exe = xp
    records.admin = record_for(h)
    body = records.admin.body
    body.wroteL = 5
    p = xp_player(h, level=4)
    ign = STR(h).xpStats.ignored
    grant(h, p, -30.0)
    assert body.sigDay == 0 and body.levelDue is True
    assert calls(p) == {"getUsername": 1, "getPerkLevel": 1}
    assert STR(h).xpStats.ignored == ign + 1


def test_an_unreadable_level_stamps_nothing(xp):
    h, records, exe = xp
    records.admin = record_for(h)
    records.admin.body.wroteL = 5
    grant(h, xp_player(h, level=None), 9.0)
    assert records.admin.body.levelDue is None
    assert records.admin.body.sigDay > 0


def test_a_strength_grant_makes_six_java_reads(xp):
    # Rule 6: the name, the protein store, the book multiplier and the level; the sandbox and the set are Lua
    h, records, exe = xp
    records.admin = record_for(h)
    p = xp_player(h)
    grant(h, p, 9.0)
    assert calls(p) == {"getUsername": 1, "getNutrition": 1, "getProteins": 1, "getXp": 1, "getMultiplier": 1,
                        "getPerkLevel": 1}


def test_an_unreadable_protein_store_reads_0(xp):
    h, records, exe = xp
    records.admin = record_for(h)
    exe.admin = "squats"
    h.G.SandboxVars = None
    grant(h, xp_player(h, proteins=None), 8.0)
    assert abs(records.admin.body.sigDay - 8.0) < 1e-12


def test_a_raising_capture_is_counted_never_raised(xp):
    h, records, exe = xp
    records.admin = record_for(h)
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
