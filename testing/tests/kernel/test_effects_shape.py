"""NR_Server_Effects, driven through table-of-functions Java stand-ins (Plan 5 Task 8).

The file is a server/ file the kernel host does not load, so it is loaded on top of the session host with the
tables it reads (NR_Data_Nutrients, NR_Data_Records, NR_Data_Effects) and the options reader, the way
test_nutrients_shape.py loads Nutrients. NR.call indexes obj[name] and calls it with obj first, so a Lua table of
function fields stands in for a Java object: a fake player with a trait collection (get/add/remove), a body
damage (the four regeneration setters, getBodyParts as a Java-list stand-in walked by size()/get(i), the
catchACold pair, ReduceGeneralHealth, the thermoregulator's getSetPoint) and the globals sendSyncPlayerFields,
syncBodyPart and ZombRandFloat. The record is built by hand from the real kernels' constructors; the coefficient
set is the real composer's. A stub proves the wiring, the order and the guards, not the engine's getters, which
the live acceptance reads. The fixture restores NR.server.effects afterwards so the later adapter modules on the
shared host run their Nutrients minute without an effects step.
"""
import os
import re

import lupa.lua51 as lua51
import pytest

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
SERVER = os.path.join(REPO, "mod", "NutritionRevamp", "common", "media", "lua", "server")
SHARED = os.path.join(REPO, "mod", "NutritionRevamp", "common", "media", "lua", "shared")
CORE = os.path.join(SHARED, "NR_Core.lua")
EFFECTS = os.path.join(SERVER, "NR_Server_Effects.lua")
TOL = 1e-12

SETUP = r"""
function()
    local names = { "CharacterTrait", "ZombRandFloat", "sendSyncPlayerFields", "syncBodyPart", "SandboxVars" }
    local saved = { names = names, vals = {}, options = NutritionRevamp.server.options,
                    effects = NutritionRevamp.server.effects, writer = NutritionRevamp.server.writer,
                    bus = NutritionRevamp.server.bus }
    for i = 1, #names do saved.vals[i] = _G[names[i]] end
    CharacterTrait = { NIGHT_VISION = "NIGHT_VISION", SHORT_SIGHTED = "SHORT_SIGHTED" }
    NR_TEST_ROLLS = {}
    ZombRandFloat = function(a, b)
        local r = table.remove(NR_TEST_ROLLS, 1)
        if r == nil then return 0.99 end
        return r
    end
    NR_TEST_PUSHES = 0
    sendSyncPlayerFields = function(p, mask)
        if mask == 2 then NR_TEST_PUSHES = NR_TEST_PUSHES + 1 end
    end
    NR_TEST_SYNCS = {}
    syncBodyPart = function(part, mask) NR_TEST_SYNCS[#NR_TEST_SYNCS + 1] = { part = part.idx, mask = mask } end
    SandboxVars = { NR = {} }
    NutritionRevamp.server.writer = nil
    NutritionRevamp.server.bus = nil
    return saved
end
"""

TEARDOWN = r"""
function(saved)
    for i = 1, #saved.names do _G[saved.names[i]] = saved.vals[i] end
    NutritionRevamp.server.options = saved.options
    NutritionRevamp.server.effects = saved.effects
    NutritionRevamp.server.writer = saved.writer
    NutritionRevamp.server.bus = saved.bus
end
"""

# A fake player: cfg.have is the trait set; cfg.log the writes; cfg.parts the body parts (Lua tables with
# their fields), cfg.cold the catchACold, cfg.setPoint the thermoregulator's set point (nil: no getter).
PLAYER = r"""
function(cfg, record)
    local p = { cfg = cfg }
    cfg.log = { adds = {}, removes = {}, regen = {}, reduce = {}, add = {}, parts = {}, cold = {}, gets = 0 }
    local coll = {
        get = function(s, t) return cfg.have[t] == true end,
        add = function(s, t)
            local E = record.effects
            cfg.log.adds[#cfg.log.adds + 1] = { t = t, ownNv = E.own.nv, ownSs = E.own.ss }
            cfg.have[t] = true
        end,
        remove = function(s, t)
            cfg.log.removes[#cfg.log.removes + 1] = t
            cfg.have[t] = nil
        end,
    }
    p.getUsername = function(self) return "admin" end
    p.isAsleep = function(self) return cfg.asleep == true end
    p.getCharacterTraits = function(self) return coll end
    local function part(i)
        local b = { idx = i, f = cfg.parts[i + 1] }
        local function pair(field, getter, setter)
            b[getter] = function(s)
                cfg.log.gets = cfg.log.gets + 1
                return s.f[field]
            end
            b[setter] = function(s, v)
                cfg.log.parts[#cfg.log.parts + 1] = { part = i, field = field, v = v }
                s.f[field] = v
            end
        end
        pair("bleedingTime", "getBleedingTime", "setBleedingTime")
        pair("scratchTime", "getScratchTime", "setScratchTime")
        pair("cutTime", "getCutTime", "setCutTime")
        pair("deepWoundTime", "getDeepWoundTime", "setDeepWoundTime")
        pair("biteTime", "getBiteTime", "setBiteTime")
        pair("burnTime", "getBurnTime", "setBurnTime")
        pair("fractureTime", "getFractureTime", "setFractureTime")
        pair("woundInfectionLevel", "getWoundInfectionLevel", "setWoundInfectionLevel")
        b.setBleeding = function(s, v)
            cfg.log.parts[#cfg.log.parts + 1] = { part = i, field = "bleeding", v = v }
            s.f.bleeding = v
        end
        return b
    end
    local parts = {}
    for i = 1, #cfg.parts do parts[i] = part(i - 1) end
    local list = {
        size = function(s) return #parts end,
        get = function(s, i) return parts[i + 1] end,
    }
    local thermo = {}
    if cfg.setPoint ~= nil then thermo.getSetPoint = function(t) return cfg.setPoint end end
    local bd = {
        getThermoregulator = function(s) return thermo end,
        getBodyParts = function(s) return list end,
        getCatchACold = function(s)
            cfg.log.gets = cfg.log.gets + 1
            return cfg.cold
        end,
        setCatchACold = function(s, v)
            cfg.log.cold[#cfg.log.cold + 1] = v
            cfg.cold = v
        end,
        ReduceGeneralHealth = function(s, v)
            cfg.log.reduce[#cfg.log.reduce + 1] = v
            if cfg.health ~= nil then cfg.health = cfg.health - v end
        end,
        AddGeneralHealth = function(s, v)
            cfg.log.add[#cfg.log.add + 1] = v
            if cfg.health ~= nil then cfg.health = cfg.health + v * 5.05 / 17 end   -- every part below 100 (#3898)
        end,
    }
    if cfg.health ~= nil then bd.getOverallBodyHealth = function(s) return cfg.health end end
    local function setter(name)
        bd[name] = function(s, v) cfg.log.regen[#cfg.log.regen + 1] = { name = name, v = v } end
    end
    setter("setStandardHealthAddition")
    setter("setReducedHealthAddition")
    setter("setSeverlyReducedHealthAddition")
    setter("setSleepingHealthAddition")
    setter("setHealthFromFood")
    p.getBodyDamage = function(self) return bd end
    return p
end
"""

# A fresh record from the real constructors: an 80 kg male body born at world age 100 (day 4), replete. Since Plan 13
# Task 12 the body is the no-trait creation body with the Plan 3 80 kg male split laid over it (fat 0.18 of 80 kg), so
# every effect below reads the masses it was written against.
RECORD = r"""
function(ageH)
    local K = NutritionRevamp.kernel
    local r = {}
    r.body = K.body.new(K.body.create(nil, nil, K.strength.DEFAULTS, 1), 1, ageH)
    r.body.fm = 80 * 0.18
    r.body.lm = 80 - r.body.fm
    r.body.fmRef = r.body.fm
    r.body.lm0dis = r.body.lm
    for i = 1, 7 do r.body.mass7[i] = 80 end
    r.nutrients = K.nutrients.newState(NutritionRevamp.data.records)
    r.nutrients.lastAgeH = ageH
    r.fluids = K.fluids.new(r.body.lm, 1, 37)
    r.acute = K.acute.new(ageH)
    return r
end
"""

MINUTE = r"""
function(p, record, dtM, ageH)
    NutritionRevamp.server.effects.minute("admin", p, record, record.body, dtM, ageH)
    return record
end
"""

READ = r"""
function(nr)
    SandboxVars = { NR = nr }
    return NutritionRevamp.server.readOptions("test")
end
"""


def _load(host, path):
    with open(path, encoding="utf-8") as fh:
        src = fh.read()
    host.rt.eval("function(src, name) return assert(loadstring(src, name)) end")(src, "@" + os.path.basename(path))()


@pytest.fixture(scope="module")
def eff_host(host):
    saved = host.rt.eval(SETUP)()
    for name in ("NR_Data_Nutrients.lua", "NR_Data_Records.lua", "NR_Data_Effects.lua"):
        _load(host, os.path.join(SHARED, name))
    _load(host, os.path.join(SERVER, "NR_Server_Options.lua"))
    _load(host, EFFECTS)
    host.G.NutritionRevamp.server.readOptions("test")
    try:
        yield host
    finally:
        host.rt.eval(TEARDOWN)(saved)


def EFF(h):
    return h.G.NutritionRevamp.server.effects


def record(h, ageH=100.0):
    return h.rt.eval(RECORD)(ageH)


def player(h, rec, have=None, parts=None, cold=0.0, setPoint=None, asleep=False, health=None):
    cfg = h.table(dict(asleep=asleep, cold=cold))
    if health is not None:
        cfg["health"] = health
    cfg["have"] = h.table(have or {})
    plist = h.rt.table()
    for i, f in enumerate(parts or []):
        plist[i + 1] = h.table(f)
    cfg["parts"] = plist
    if setPoint is not None:
        cfg["setPoint"] = setPoint
    return h.rt.eval(PLAYER)(cfg, rec), cfg


def minute(h, p, rec, dtM=1.0, ageH=100.0):
    return h.rt.eval(MINUTE)(p, rec, dtM, ageH)


def setopts(h, **kw):
    return h.rt.eval(READ)(h.table(kw))


def lst(t):
    return [t[i] for i in range(1, len(t) + 1)]


@pytest.fixture(autouse=True)
def _reset(eff_host):
    h = eff_host
    h.G.NR_TEST_PUSHES = 0
    h.G.NR_TEST_SYNCS = h.rt.table()
    h.G.NR_TEST_ROLLS = h.rt.table()
    E = EFF(h)
    E.last = h.rt.table()
    setopts(h)
    yield
    setopts(h)


# --- the file and the rebuild ---------------------------------------------------------------------------

def test_the_file_loads_with_no_engine():
    rt = lua51.LuaRuntime(unpack_returned_tuples=True)
    load = rt.eval("function(src, name) return assert(loadstring(src, name)) end")
    for path in (CORE, EFFECTS):
        with open(path, encoding="utf-8") as fh:
            load(fh.read(), "@" + os.path.basename(path))()
    E = rt.globals().NutritionRevamp.server.effects
    assert E is not None and E.wired is False
    E.minute("u", None, None)                               # a nil record returns
    assert E.stats.minutes == 0


def test_a_fresh_record_composes_once_and_rebuilds_only_on_a_moved_key(eff_host):
    h = eff_host
    rec = record(h)
    p, cfg = player(h, rec)
    n0 = EFF(h).stats.rebuilds
    minute(h, p, rec)
    E = rec["effects"]
    assert E is not None and E["epoch"] == 1
    assert EFF(h).stats.rebuilds == n0 + 1
    assert E["key"]["day"] == rec["body"]["dayIndex"] == 4
    minute(h, p, rec, ageH=100.0 + 1 / 60)
    minute(h, p, rec, ageH=100.0 + 2 / 60)
    assert E["epoch"] == 1 and EFF(h).stats.rebuilds == n0 + 1   # nothing moved
    rec["acute"]["caf"] = 200.0                                  # caffeine band 0 -> 4
    minute(h, p, rec, ageH=100.0 + 3 / 60)
    assert E["epoch"] == 2 and E["key"]["b"][1] == 4
    rec["nutrients"]["epoch"] = rec["nutrients"]["epoch"] + 1    # a nutrient grade moved
    minute(h, p, rec, ageH=100.0 + 4 / 60)
    assert E["epoch"] == 3
    setopts(h, Severity=2.0)                                     # the dial snapshot moved
    minute(h, p, rec, ageH=100.0 + 5 / 60)
    assert E["epoch"] == 4 and E["key"]["dials"] == 2000 * 10000000 + 10 + 1     # no kill dial (Plan 15 Task 4); the Severity term x 10^7 since Task 8
    assert E["dirty"] is True


def test_the_flags_outside_the_key_fold_into_the_dials(eff_host):
    h = eff_host
    rec = record(h)
    p, _ = player(h, rec, asleep=True)
    minute(h, p, rec)
    E = rec["effects"]
    assert E["key"]["dials"] == 10000000000 + 11
    rec["acute"]["boutVig"] = True                                # read while asleep
    minute(h, p, rec, ageH=100.0 + 1 / 60)
    assert E["key"]["dials"] == 10000000000 + 100011 and E["epoch"] == 2
    awake, _ = player(h, rec)
    minute(h, awake, rec, ageH=100.0 + 2 / 60)                    # a latched boutVig awake reads false
    assert E["key"]["dials"] == 10000000000 + 11 and E["epoch"] == 3


def test_a_non_finite_field_is_healed_and_counted(eff_host):
    h = eff_host
    rec = record(h)
    p, _ = player(h, rec)
    minute(h, p, rec)
    E = rec["effects"]
    healed = EFF(h).stats.healed
    E["fOffNut"] = float("nan")
    E["key"]["dials"] = float("inf")
    minute(h, p, rec, ageH=100.0 + 1 / 60)
    assert EFF(h).stats.healed == healed + 1
    assert "effects.fOffNut" in str(EFF(h).lastHealed) and "effects.key.dials" in str(EFF(h).lastHealed)
    assert E["fOffNut"] == 0 and E["epoch"] == 2                  # the healed key forced a rebuild


def test_a_raise_inside_the_step_is_kept_and_counted(eff_host):
    h = eff_host
    rec = record(h)
    p, _ = player(h, rec)
    orig = h.K.effects.bands
    h.K.effects.bands = h.rt.eval("function() error('boom') end")
    try:
        errors = EFF(h).stats.errors
        minute(h, p, rec)
        assert EFF(h).stats.errors == errors + 1 and "boom" in str(EFF(h).lastError)
    finally:
        h.K.effects.bands = orig


# --- the per-minute scalars -----------------------------------------------------------------------------

def test_the_minute_scalars_are_stamped(eff_host):
    h = eff_host
    setopts(h, StimulantRealism=2)                               # Realistic: the Plan 14 sizes
    rec = record(h)
    a = rec["acute"]
    a["caf"] = 107.0
    a["cafTol"] = 0.5
    a["debtH"] = 10.0
    a["bac"] = 0.05
    p, _ = player(h, rec)
    minute(h, p, rec)
    E = rec["effects"]
    caf_off = 0.35 * 107 / (107 + 150) * (1 - 0.6 * 0.5)
    assert abs(E["fOff"] - (0.05 - caf_off + E["fOffNut"])) < TOL
    assert abs(E["solAddH"] - 0.15) < TOL                        # satC(107) = 1
    assert E["solMul"] == 1
    assert abs(E["intoxTarget"] - 25.0) < TOL                    # 100 x 0.05 / 0.20
    assert E["mAcc"] == h.K.clamp(E["mNut"], 0.2, 5.0)            # no writer reads: the engine part reads 1
    assert E["rRec"] == h.K.clamp(E["rNut"], 0.25, 2.0)
    assert E["tempTarget"] == 0                                  # no set point and no offset


def _stim_minute(h, rec, p):
    minute(h, p, rec)
    E = rec["effects"]
    return E["fOff"] - E["fOffNut"], E["intoxTarget"], E["mNut"], E["stressTarget"], E["unhappyTarget"]


def test_switching_the_stimulant_option_takes_effect_on_the_next_read(eff_host):
    # one record in a hangover with caffeine and alcohol on board, read under Game, then Realistic, then Game again:
    # each options read selects the set, and the next minute's scalars and hangover rows follow it (the set is in the
    # rebuild key, so the hangover rows rebuild with no band change)
    h = eff_host
    rec = record(h)
    a = rec["acute"]
    a["caf"] = 107.0
    a["bac"] = 0.05
    a["hang"] = 1
    p, _ = player(h, rec)
    assert h.K.acute.C.MODE == 1 and h.G.NutritionRevamp.server.options.stimulantRealism == 1   # the default, Game
    caf_g, intox_g, m_g, s_g, u_g = _stim_minute(h, rec, p)
    assert u_g == 21                                             # the Game hangover's unhappiness floor (fix 1)
    assert caf_g == pytest.approx(-0.12 * 107 / 257, abs=TOL) and intox_g == pytest.approx(100 * 0.05 / 0.31, abs=TOL)
    assert (m_g, s_g) == (pytest.approx(1.075, abs=TOL), pytest.approx(0.05, abs=TOL))
    rebuilds = EFF(h).stats.rebuilds
    setopts(h, StimulantRealism=2)
    assert h.K.acute.C.MODE == 2 and h.G.NutritionRevamp.server.options.stimulantRealism == 2
    caf_r, intox_r, m_r, s_r, u_r = _stim_minute(h, rec, p)
    assert u_r == 42
    assert EFF(h).stats.rebuilds == rebuilds + 1                 # the set moved the key
    assert caf_r == pytest.approx(-0.35 * 107 / 257, abs=TOL) and intox_r == pytest.approx(25.0, abs=TOL)
    assert (m_r, s_r) == (pytest.approx(1.15, abs=TOL), pytest.approx(0.10, abs=TOL))
    setopts(h, StimulantRealism=7)                               # out of range: the default, Game
    assert h.K.acute.C.MODE == 1
    assert _stim_minute(h, rec, p)[:2] == (pytest.approx(caf_g, abs=TOL), pytest.approx(intox_g, abs=TOL))
    rec["acute"]["hang"] = 0
    assert _stim_minute(h, rec, p)[4] == 0                       # the hangover over: the floor goes with the band


def test_the_vigorous_and_alcohol_sleep_onset_terms(eff_host):
    h = eff_host
    rec = record(h)
    a = rec["acute"]
    a["lastVigAgeH"] = 99.5                                      # vigorous 0.5 h ago
    a["alcPeak"] = 0.13                                           # the alcohol band 2
    p, _ = player(h, rec)
    minute(h, p, rec)
    E = rec["effects"]
    assert abs(E["solAddH"] - 0.15) < TOL and E["solMul"] == 0.6
    a["lastVigAgeH"] = 98.0                                       # 2 h ago: outside the window
    minute(h, p, rec, ageH=100.0 + 1 / 60)
    assert E["solAddH"] == 0


def test_the_engine_factors_come_from_the_writers_engine_reads(eff_host):
    h = eff_host
    rec = record(h)
    p, _ = player(h, rec)
    inp = h.table(dict(endurance=0.5, sitting=True, resting=False, thermoFatigue=1.2, sd=1.0, needsMore=True,
                       needsLess=False, insomniac=True, nightOwl=False, bedFactor=1.1))
    h.G.NutritionRevamp.server.writer = h.table({"inp": {}})
    h.G.NutritionRevamp.server.writer.inp["admin"] = inp
    try:
        minute(h, p, rec)
    finally:
        h.G.NutritionRevamp.server.writer = None
    E = rec["effects"]
    m_eng = 0.5 / 0.3 / 1.5 * 1.2 * 1.3                          # B3: endDef, rest, thermo, NEEDS_MORE 1.3
    r_eng = 1.1 * (0.5 / 1.18)                                   # B4: bed x ff / t
    assert abs(E["mAcc"] - min(max(E["mNut"] * m_eng, 0.2), 5.0)) < 1e-12
    assert abs(E["rRec"] - min(max(E["rNut"] * r_eng, 0.25), 2.0)) < 1e-12


def test_the_temperature_target_is_absolute_and_zero_without_a_set_point(eff_host):
    h = eff_host
    rec = record(h)
    rec["nutrients"]["iron"]["g"] = 4                            # S1016: -0.2 degrees C at iron clinical
    p, _ = player(h, rec, setPoint=37.0)
    minute(h, p, rec)
    E = rec["effects"]
    assert abs(E["tempOffset"] + 0.2) < TOL
    assert abs(E["tempTarget"] - 36.8) < 1e-9 and abs(E["tempAdj"] + 0.2) < TOL
    q, _ = player(h, rec)                                        # no getSetPoint: no write
    minute(h, q, rec, ageH=100.0 + 1 / 60)
    assert E["tempTarget"] == 0


# --- the traits ------------------------------------------------------------------------------------------

def _nv_ready(rec):
    rec["acute"]["retEma"] = 1000.0                              # at or above R 900 (male)
    return rec


def test_the_night_vision_add_sets_ownership_first_and_pushes_once(eff_host):
    h = eff_host
    rec = _nv_ready(record(h))
    p, cfg = player(h, rec)
    minute(h, p, rec)
    E = rec["effects"]
    E["nvDays"] = 14.0
    minute(h, p, rec, ageH=100.0 + 1 / 60)
    adds = lst(cfg["log"]["adds"])
    assert len(adds) == 1 and adds[0]["t"] == "NIGHT_VISION" and adds[0]["ownNv"] is True
    assert E["own"]["nv"] is True and cfg["have"]["NIGHT_VISION"] is True
    assert h.G.NR_TEST_PUSHES == 1
    minute(h, p, rec, ageH=100.0 + 2 / 60)                        # held and owned: nothing to do
    assert len(lst(cfg["log"]["adds"])) == 1 and h.G.NR_TEST_PUSHES == 1


def test_an_owned_trait_removed_elsewhere_is_reasserted(eff_host):
    h = eff_host
    rec = _nv_ready(record(h))
    p, cfg = player(h, rec)
    minute(h, p, rec)
    rec["effects"]["nvDays"] = 14.0
    minute(h, p, rec, ageH=100.0 + 1 / 60)
    cfg["have"]["NIGHT_VISION"] = None                           # an admin SyncXp erased it (#3051-#3069)
    re0 = EFF(h).stats.reasserts
    minute(h, p, rec, ageH=100.0 + 2 / 60)
    assert cfg["have"]["NIGHT_VISION"] is True and EFF(h).stats.reasserts == re0 + 1
    assert h.G.NR_TEST_PUSHES == 2


def test_the_withdrawal_removes_only_an_owned_trait(eff_host):
    h = eff_host
    rec = _nv_ready(record(h))
    p, cfg = player(h, rec)
    minute(h, p, rec)
    rec["effects"]["nvDays"] = 14.0
    minute(h, p, rec, ageH=100.0 + 1 / 60)
    rec["nutrients"]["vitA"]["g"] = 2                            # vitA leaves replete: withdrawn at once
    minute(h, p, rec, ageH=100.0 + 2 / 60)
    assert lst(cfg["log"]["removes"]) == ["NIGHT_VISION"]
    assert rec["effects"]["own"]["nv"] is False and cfg["have"]["NIGHT_VISION"] is None
    assert h.G.NR_TEST_PUSHES == 2


def test_a_natively_held_trait_is_never_removed(eff_host):
    h = eff_host
    rec = record(h)
    p, cfg = player(h, rec, have={"NIGHT_VISION": True, "SHORT_SIGHTED": True})
    for i in range(3):
        minute(h, p, rec, ageH=100.0 + i / 60)                    # neither wanted, neither owned
    assert lst(cfg["log"]["removes"]) == [] and lst(cfg["log"]["adds"]) == []
    assert cfg["have"]["NIGHT_VISION"] is True and cfg["have"]["SHORT_SIGHTED"] is True
    assert rec["effects"]["own"]["nv"] is False and h.G.NR_TEST_PUSHES == 0
    rec["nutrients"]["vitA"]["g"] = 4                            # wanted while natively held: not owned
    minute(h, p, rec, ageH=100.0 + 4 / 60)
    assert rec["effects"]["own"]["ss"] is False and h.G.NR_TEST_PUSHES == 0


def test_short_sighted_at_clinical_vitamin_a_only_at_severity_one(eff_host):
    h = eff_host
    rec = record(h)
    rec["nutrients"]["vitA"]["g"] = 4
    p, cfg = player(h, rec)
    setopts(h, Severity=0.5)
    minute(h, p, rec)
    assert lst(cfg["log"]["adds"]) == []
    setopts(h, Severity=1.0)
    minute(h, p, rec, ageH=100.0 + 1 / 60)
    adds = lst(cfg["log"]["adds"])
    assert len(adds) == 1 and adds[0]["t"] == "SHORT_SIGHTED" and adds[0]["ownSs"] is True
    assert h.G.NR_TEST_PUSHES == 1


def test_two_trait_changes_in_one_minute_push_once(eff_host):
    h = eff_host
    rec = _nv_ready(record(h))
    p, cfg = player(h, rec)
    minute(h, p, rec)
    rec["effects"]["nvDays"] = 14.0
    minute(h, p, rec, ageH=100.0 + 1 / 60)
    assert h.G.NR_TEST_PUSHES == 1
    rec["nutrients"]["vitA"]["g"] = 4                            # NV withdrawn and Short Sighted added
    minute(h, p, rec, ageH=100.0 + 2 / 60)
    assert lst(cfg["log"]["removes"]) == ["NIGHT_VISION"]
    assert [a["t"] for a in lst(cfg["log"]["adds"])] == ["NIGHT_VISION", "SHORT_SIGHTED"]
    assert h.G.NR_TEST_PUSHES == 2


def test_a_missing_push_global_is_counted(eff_host):
    h = eff_host
    rec = record(h)
    rec["nutrients"]["vitA"]["g"] = 4
    p, _ = player(h, rec)
    keep = h.G.sendSyncPlayerFields
    h.G.sendSyncPlayerFields = None
    try:
        missing = EFF(h).stats.pushMissing
        minute(h, p, rec)
        assert EFF(h).stats.pushMissing == missing + 1
    finally:
        h.G.sendSyncPlayerFields = keep


# --- the regeneration setters and the drains ------------------------------------------------------------

def _regen(cfg):
    return {r["name"]: r["v"] for r in lst(cfg["log"]["regen"])}


def test_the_regeneration_setters_take_heal_mul_at_first_sight_and_on_a_rebuild(eff_host):
    h = eff_host
    rec = record(h)
    rec["nutrients"]["zinc"]["g"] = 3                            # healMul 0.92 (S1151)
    p, cfg = player(h, rec)
    minute(h, p, rec)
    E = rec["effects"]
    assert abs(E["healMul"] - 0.92) < TOL
    got = _regen(cfg)
    assert abs(got["setStandardHealthAddition"] - 0.002 * 0.92) < TOL
    assert abs(got["setReducedHealthAddition"] - 0.0013 * 0.92) < TOL
    assert abs(got["setSeverlyReducedHealthAddition"] - 0.0008 * 0.92) < TOL
    assert abs(got["setSleepingHealthAddition"] - 0.02 * 0.92) < TOL
    n = len(lst(cfg["log"]["regen"]))
    minute(h, p, rec, ageH=100.0 + 1 / 60)                        # no rebuild, same multiplier: no write
    assert len(lst(cfg["log"]["regen"])) == n
    EFF(h).forget("admin")                                       # a first sight: re-asserted (#3020)
    minute(h, p, rec, ageH=100.0 + 2 / 60)
    assert len(lst(cfg["log"]["regen"])) == n + 5                 # the four tiers and the food heal (#3897)


def _health(cfg):
    return cfg["health"]


def test_the_drain_takes_the_rate_toward_the_target_and_zeroes_regeneration_and_the_food_heal(eff_host):
    # Plan 15 Task 4: the iron lethal rung drains 100 health a game day (100 over 24 h); Plan 17 Task 2: on a line from
    # the onset
    h = eff_host
    rec = record(h)
    rec["nutrients"]["iron"]["x"] = 3
    p, cfg = player(h, rec, health=100.0)
    minute(h, p, rec, dtM=2.0)
    D = rec["drain"]
    rate = 100 * 24 / 24                                          # health a game day
    assert D["active"] is True and D["state"] == 7 and D["rate"] == rate
    assert lst(cfg["log"]["reduce"]) == [pytest.approx(rate * 2 / 1440, abs=TOL)]
    got = lst(cfg["log"]["regen"])[-5:]
    assert all(r["v"] == 0 for r in got)                         # x0 while a drain state is active (ruling 13)
    assert got[-1]["name"] == "setHealthFromFood"                # the food heal too (jar-checks Check 2)
    rec["nutrients"]["iron"]["x"] = 0                            # the state ends: re-asserted at healMul, food heal back
    minute(h, p, rec, ageH=100.0 + 3 / 60)
    got = {r["name"]: r["v"] for r in lst(cfg["log"]["regen"])[-5:]}
    assert got["setStandardHealthAddition"] == 0.002 and got["setHealthFromFood"] == 0.0087  # #2354; the gentle heal (Plan 15 Task 8)
    assert rec["drain"]["active"] is False and rec["drain"]["target"] == 100


def test_the_drain_never_takes_health_past_the_target_and_holds_with_no_sawtooth(eff_host):
    h = eff_host
    rec = record(h)
    rec["fluids"]["dehydPct"] = 6.75                             # Realistic dehydration a quarter of the way to 15 %
    target = 100 * h.K.drain.dehydFraction(6.75)                 # Plan 17 Task 2: 0.1 + 0.9 x the curve, about 37.7
    p, cfg = player(h, rec, health=target + 0.02)
    minute(h, p, rec, dtM=1.0)
    assert rec["drain"]["state"] == 6 and rec["drain"]["target"] == pytest.approx(target, abs=1e-12)
    assert lst(cfg["log"]["reduce"]) == [pytest.approx(0.02, abs=1e-9)]   # min(rate x dt, health - target)
    assert 0.02 < 17.82 * 24 / 1440                              # under the minute's rate: the target bound it
    n_regen = len(lst(cfg["log"]["regen"]))
    cfg["health"] = rec["drain"]["target"]                       # at the target: holding
    minute(h, p, rec, ageH=100.0 + 1 / 60)
    assert len(lst(cfg["log"]["reduce"])) == 1                   # nothing taken at the target
    assert len(lst(cfg["log"]["regen"])) == n_regen              # regeneration stays zero: no re-write, no sawtooth
    assert rec["drain"]["active"] is True


def test_no_overall_health_read_takes_nothing(eff_host):
    h = eff_host
    rec = record(h)
    rec["nutrients"]["iron"]["x"] = 3
    p, cfg = player(h, rec)                                      # the stand-in answers no getOverallBodyHealth
    minute(h, p, rec)
    assert rec["drain"]["active"] is True and lst(cfg["log"]["reduce"]) == []


def test_a_drain_state_change_marks_the_mirror_dirty(eff_host):
    # fix 1 (review L1): the winner changes with no rebuild, so only the drain-state clause can mark the mirror
    h = eff_host
    rec = record(h)
    rec["fluids"]["dehydPct"] = 5.5                              # Plan 17 Task 2: dehydration's fraction about 0.493
    rec["nutrients"]["vitC"]["g"] = 4
    rec["nutrients"]["vitC"]["ah"] = 1000.0                      # scurvy's 1 - 1000 / 2160, about 0.537
    p, cfg = player(h, rec, health=44.0)
    minute(h, p, rec)
    assert rec["drain"]["state"] == 6
    rec["effects"]["dirty"] = False
    rebuilds = EFF(h).stats.rebuilds
    rec["nutrients"]["vitC"]["ah"] = 1200.0                      # scurvy's about 0.444: under dehydration's
    minute(h, p, rec, ageH=100.0 + 1 / 60)
    assert rec["drain"]["state"] == 2 and rec["effects"]["dirty"] is True
    assert EFF(h).stats.rebuilds == rebuilds                     # no rebuild marked it


def test_a_dead_record_is_stepped_with_no_body_write(eff_host):
    h = eff_host
    rec = record(h)
    rec["nutrients"]["iron"]["x"] = 3
    rec["dead"] = True
    p, cfg = player(h, rec, health=100.0)
    minute(h, p, rec)
    assert lst(cfg["log"]["reduce"]) == [] and lst(cfg["log"]["regen"]) == []
    assert rec["drain"]["active"] is True


# --- the per-part folds ----------------------------------------------------------------------------------

def _part(**kw):
    base = dict(bleedingTime=0.0, scratchTime=0.0, cutTime=0.0, deepWoundTime=0.0, biteTime=0.0, burnTime=0.0,
                fractureTime=0.0, woundInfectionLevel=0.0)
    base.update(kw)
    return base


def test_the_folds_make_no_java_call_at_identity(eff_host):
    h = eff_host
    rec = record(h)
    p, cfg = player(h, rec, parts=[_part(bleedingTime=1.0, scratchTime=5.0)], cold=10.0)
    minute(h, p, rec)
    cfg["parts"][1]["bleedingTime"] = 0.9
    minute(h, p, rec, ageH=100.0 + 1 / 60)
    assert cfg["log"]["gets"] == 0 and lst(cfg["log"]["parts"]) == [] and lst(cfg["log"]["cold"]) == []


def test_the_bleeding_fold_divides_the_fall_by_bleed_mul(eff_host):
    h = eff_host
    rec = record(h)
    rec["nutrients"]["vitC"]["g"] = 3                            # bleedMul 1.10, healMul 0.85
    p, cfg = player(h, rec, parts=[_part(bleedingTime=1.0, scratchTime=5.0)])
    minute(h, p, rec)                                            # seeds the last values
    assert lst(cfg["log"]["parts"]) == []
    cfg["parts"][1]["bleedingTime"] = 0.9
    cfg["parts"][1]["scratchTime"] = 4.0
    minute(h, p, rec, ageH=100.0 + 1 / 60)
    writes = {w["field"]: w["v"] for w in lst(cfg["log"]["parts"])}
    assert abs(writes["bleedingTime"] - (1.0 - (1.0 - 0.9) / 1.10)) < TOL
    assert abs(writes["scratchTime"] - (5.0 - 1.0 * 0.85)) < TOL
    assert h.G.NR_TEST_SYNCS is not None and len(lst(h.G.NR_TEST_SYNCS)) == 0   # no sync on these (gate 1)
    cfg["parts"][1]["scratchTime"] = 0.0                          # healed by the engine: passed through
    n = len(lst(cfg["log"]["parts"]))
    minute(h, p, rec, ageH=100.0 + 2 / 60)
    assert all(w["field"] != "scratchTime" for w in lst(cfg["log"]["parts"])[n:])


def test_the_infection_fold_scales_the_rise_and_syncs(eff_host):
    h = eff_host
    rec = record(h)
    rec["acute"]["starvedDays"] = 14.0                           # pe 4: infectMul 2.30 (S0954); Plan 15 Task 4: from day 14
    p, cfg = player(h, rec, parts=[_part(), _part(woundInfectionLevel=1.0)])
    minute(h, p, rec)
    assert rec["effects"]["pe"] == 4 and abs(rec["effects"]["infectMul"] - 2.3) < TOL
    cfg["parts"][2]["woundInfectionLevel"] = 1.1
    minute(h, p, rec, ageH=100.0 + 1 / 60)
    w = [x for x in lst(cfg["log"]["parts"]) if x["field"] == "woundInfectionLevel"]
    assert len(w) == 1 and w[0]["part"] == 1 and abs(w[0]["v"] - (1.0 + 0.1 * 2.3)) < 1e-9
    syncs = lst(h.G.NR_TEST_SYNCS)
    assert len(syncs) == 1 and syncs[0]["part"] == 1 and syncs[0]["mask"] == 32768
    cfg["parts"][2]["woundInfectionLevel"] = 0.5                  # a treated fall passes through
    minute(h, p, rec, ageH=100.0 + 2 / 60)
    assert len([x for x in lst(cfg["log"]["parts"]) if x["field"] == "woundInfectionLevel"]) == 1


def test_the_cold_fold_scales_a_rise_and_passes_a_fall(eff_host):
    h = eff_host
    rec = record(h)
    rec["nutrients"]["vitC"]["g"] = 4                            # coldMul 1.15 (S1155)
    p, cfg = player(h, rec, cold=10.0)
    minute(h, p, rec)
    assert abs(rec["effects"]["coldMul"] - 1.15) < TOL
    cfg["cold"] = 12.0
    minute(h, p, rec, ageH=100.0 + 1 / 60)
    assert abs(lst(cfg["log"]["cold"])[0] - (10.0 + 2.0 * 1.15)) < 1e-9
    cfg["cold"] = 5.0                                            # the unscaled fall passes (T1-3)
    minute(h, p, rec, ageH=100.0 + 2 / 60)
    assert len(lst(cfg["log"]["cold"])) == 1
    cfg["cold"] = 6.0
    minute(h, p, rec, ageH=100.0 + 3 / 60)
    assert abs(lst(cfg["log"]["cold"])[1] - (5.0 + 1.0 * 1.15)) < 1e-9


# --- the bruise -------------------------------------------------------------------------------------------

def test_the_bruise_rolls_at_clinical_vitamin_c_only(eff_host):
    h = eff_host
    rec = record(h)
    rec["nutrients"]["vitC"]["g"] = 3
    p, cfg = player(h, rec, parts=[_part(), _part()])
    h.G.NR_TEST_ROLLS = h.table({1: 0.0, 2: 0.0})
    minute(h, p, rec)
    assert all(w["field"] != "bleeding" for w in lst(cfg["log"]["parts"]))
    rec["nutrients"]["vitC"]["g"] = 4
    rec["nutrients"]["epoch"] = rec["nutrients"]["epoch"] + 1    # the engine moves the epoch with a grade
    h.G.NR_TEST_ROLLS = h.table({1: 0.0, 2: 0.6})                 # fires; part floor(0.6 x 2) = 1
    minute(h, p, rec, ageH=100.0 + 1 / 60)
    assert abs(rec["effects"]["bruise"] - 1 / 2880) < TOL
    w = [x for x in lst(cfg["log"]["parts"]) if x["field"] in ("bleeding", "bleedingTime")]
    assert [(x["part"], x["field"], x["v"]) for x in w] == [(1, "bleedingTime", 0.05)]        # no setBleeding: a bandage holds
    syncs = lst(h.G.NR_TEST_SYNCS)
    assert syncs[-1]["part"] == 1 and syncs[-1]["mask"] == 8 + 131072
    n = len(lst(cfg["log"]["parts"]))
    h.G.NR_TEST_ROLLS = h.table({1: 0.5})                         # a roll above p: nothing
    minute(h, p, rec, ageH=100.0 + 2 / 60)
    assert all(x["field"] != "bleeding" for x in lst(cfg["log"]["parts"])[n:])


def test_iron_or_riboflavin_depletion_halves_the_night_vision_clock(eff_host):
    # the review of 781eaa0: iron and riboflavin were swapped at the nvMinute call; the kernel reads them
    # symmetrically today, so each is pinned on its own here
    for nutrient in ("iron", "riboflavin"):
        h = eff_host
        rec = _nv_ready(record(h))
        p, _ = player(h, rec)
        minute(h, p, rec)
        E = rec["effects"]
        d0 = E["nvDays"]
        rec["nutrients"][nutrient]["g"] = 3
        minute(h, p, rec, ageH=100.0 + 1 / 60)
        assert abs((E["nvDays"] - d0) - 0.5 * (1 / 60) / 24) < 1e-12, nutrient
        rec["nutrients"][nutrient]["g"] = 1
        d1 = E["nvDays"]
        minute(h, p, rec, ageH=100.0 + 2 / 60)
        assert abs((E["nvDays"] - d1) - (1 / 60) / 24) < 1e-12, nutrient


def test_the_dial_key_separates_a_fractional_severity_from_the_flag_terms(eff_host):
    h = eff_host
    rec = record(h)
    p, _ = player(h, rec)
    minute(h, p, rec)
    e0 = rec["effects"]["epoch"]
    setopts(h, Severity=0.1)
    minute(h, p, rec, ageH=100.0 + 1 / 60)
    e1 = rec["effects"]["epoch"]
    setopts(h, Severity=0.0)
    minute(h, p, rec, ageH=100.0 + 2 / 60)
    assert rec["effects"]["epoch"] > e1 > e0
    assert rec["effects"]["key"]["dials"] == 11                    # bonus and excess on; no kill dial (Plan 15 Task 4)


# --- the closed-day composites ---------------------------------------------------------------------------

def test_the_protein_side_waits_for_seven_closed_days(eff_host):
    h = eff_host
    rec = record(h)                                              # p7 all zero: a new character
    p, _ = player(h, rec)
    minute(h, p, rec)
    assert rec["effects"]["pe"] == 1
    body = rec["body"]
    body["dayIndex"] = 11                                        # seven days after the birth day 4
    body["inDayClosed"] = 2000.0
    rec["effects"]["exSeen"] = 0
    minute(h, p, rec, ageH=100.0 + 1 / 60)
    assert rec["effects"]["pe"] == 4                             # a zero protein mean read at last
    assert abs(rec["effects"]["ea"] - 2000.0 / body["lm"]) < 1e-9
    assert rec["effects"]["lastDay"] == 11


def _female_starved(h):
    rec = record(h)
    p, cfg = player(h, rec)
    minute(h, p, rec)                                            # the first minute builds the effects table
    body = rec["body"]
    body["sex"] = 2                                              # the engine's value; the option decides what is read
    body["fm"] = 5.0                                             # 5 / 80 = 0.0625: above the male floor 0.04, below the female 0.10
    body["lm"] = 75.0
    body["dayIndex"] = 11
    body["inDayClosed"] = 2000.0
    rec["effects"]["exSeen"] = 0
    rec["acute"]["retEma"] = 800.0                               # below the male R 900, above the female R 700
    return rec, p


def _starving(h, unfedH, fm=14.4, lm=65.6, ageH=100.0):
    """A record whose meal pool was last fed unfedH game hours before the next minute (ageH + 1 / 60): the pool empty
    and drain.fedAgeH stamped there (Plan 15 Task 6 fix 1: the acute onset counts unfed hours)."""
    rec = record(h)
    p, cfg = player(h, rec, health=100.0)
    minute(h, p, rec, ageH=ageH)
    body = rec["body"]
    body["fm"] = fm
    body["lm"] = lm
    if rec["satiety"] is None:                                   # this host runs no writer: the pool laid here
        rec["satiety"] = h.rt.table()
    rec["satiety"]["M"] = 0.0
    rec["drain"]["fedAgeH"] = ageH + 1 / 60 - unfedH
    return rec, p, cfg


def test_starvation_starts_at_30_unfed_hours_and_sets_the_phase_flags(eff_host):
    # Plan 15 Task 6 fix 1: 28 unfed hours (no state, the early hold from 24); 30 h, the onset
    h = eff_host
    rec, p, cfg = _starving(h, 28)
    minute(h, p, rec, ageH=100.0 + 1 / 60)
    D, E = rec["drain"], rec["effects"]
    assert D["active"] is False and abs(D["starvedH"] - 28) < 1e-9
    assert E["key"]["dials"] == 10000000000 + 1000 + 11             # starveEarly: 24 unfed hours or more
    rec["satiety"]["M"] = 0.0
    minute(h, p, rec, ageH=102.0 + 1 / 60)
    assert D["active"] is True and D["state"] == 1 and D["target"] == 100      # Plan 17 Task 2: the curve opens at 1
    est = 80 / 1.7 ** 2 - h.K.drain.STARVE_DBMI * (102.0 + 1 / 60 - rec["body"]["dayStartH"])
    assert abs(D["bmi0"] - est) < 1e-9                             # Plan 17 T2-1: the BMI estimate at the onset
    assert E["key"]["dials"] == 10000000000 + 1000 + 100 + 11       # phase 1, weakness: mNut 1.25
    assert E["mNut"] == pytest.approx(1.25, abs=TOL)
    rec["satiety"]["M"] = 0.0
    rec["drain"]["fedAgeH"] = 102.0 + 2 / 60 - 336                 # 14 days unfed
    minute(h, p, rec, ageH=102.0 + 2 / 60)
    assert E["key"]["dials"] == 10000000000 + 300 + 11 and E["unhappyTarget"] == 21   # phase 3: mood, the pe rows back


def test_eating_ends_the_starvation(eff_host):
    h = eff_host
    rec, p, cfg = _starving(h, 40)
    minute(h, p, rec, ageH=100.0 + 1 / 60)
    assert rec["drain"]["active"] is True and rec["drain"]["bmi0"] > 0
    rec["satiety"]["M"] = 400.0                                   # a meal: a meal spell (no 72 h window seen yet; H1)
    minute(h, p, rec, ageH=100.0 + 2 / 60)
    assert rec["drain"]["active"] is False and rec["drain"]["starvedH"] == 0
    assert rec["drain"]["bmi0"] == 0


def test_overlay_runs_no_starvation_or_dehydration_drain(eff_host):
    # Plan 15 close, ruling M2: in Mode 2 vanilla owns HUNGER and THIRST and its own level-4 drains, so the mod's
    # starvation and dehydration states do not run (the starvation clock and the deficiency states still do)
    h = eff_host
    NR = h.rt.eval("NutritionRevamp")
    saved = NR.server.writer
    NR.server.writer = h.rt.eval("{ mode = 2 }")
    try:
        rec, p, cfg = _starving(h, 40)
        rec["fluids"]["dehydPct"] = 8.0
        minute(h, p, rec, ageH=100.0 + 1 / 60)
        D = rec["drain"]
        assert D["active"] is False and D["starving"] is False and D["dehydrated"] is False
        assert D["starveAcute"] is True and D["starvedH"] >= 40                  # the clock and its phases run on
        NR.server.writer.mode = 1
        rec["satiety"]["M"] = 0.0
        minute(h, p, rec, ageH=100.0 + 2 / 60)
        assert rec["drain"]["active"] is True and rec["drain"]["starving"] is True
    finally:
        NR.server.writer = saved


def test_the_starvation_target_falls_with_bmi_from_its_onset(eff_host):
    # Plan 17 Task 2: Realistic starvation on the curve over the BMI progress, read at each record-day close
    h = eff_host
    rec, p, cfg = _starving(h, 48)
    minute(h, p, rec, ageH=100.0 + 1 / 60)
    D = rec["drain"]
    bmi0 = D["bmi0"]
    body = rec["body"]
    body["fm"] = 12.0 * 1.7 ** 2 + (bmi0 - 12.0) / 2 * 1.7 ** 2 - body["lm"]   # halfway to BMI 12, at a close
    body["dayStartH"] = 100.0 + 2 / 60
    minute(h, p, rec, ageH=100.0 + 2 / 60)
    assert D["pS"] == pytest.approx(0.5, abs=1e-9)
    assert D["target"] == pytest.approx(100 * h.K.drain.curve(0.5, 1, h.K.drain.A_STARVE), abs=1e-9)
    body["fm"] = 12.0 * 1.7 ** 2 - body["lm"]                      # BMI 12, the death point, at the next close: 0
    body["dayStartH"] = 100.0 + 3 / 60
    minute(h, p, rec, ageH=100.0 + 3 / 60)
    assert D["target"] == pytest.approx(0, abs=1e-9)


def test_the_protein_grade_reads_the_mean_per_kg_of_the_body_mass(eff_host):
    # ruling 13-20: the seven closed days' protein per kg of fm + lm + lx at the close
    h = eff_host
    seen = []
    for lx in (0.0, 20.0):
        rec = record(h)
        p, _ = player(h, rec)
        minute(h, p, rec)
        body = rec["body"]
        body["lx"] = lx
        for i in range(1, 8):
            body["p7"][i] = 64.0                                 # 0.8 g/kg/d at 80 kg, 0.64 at 100 kg
        body["dayIndex"] = 11
        body["inDayClosed"] = 2000.0
        rec["effects"]["exSeen"] = 0
        minute(h, p, rec, ageH=100.0 + 1 / 60)
        seen.append(rec["effects"]["pe"])
    assert seen[0] != seen[1], seen


def test_the_retinol_requirement_reads_the_effective_sex_and_the_drain_none(eff_host):
    # Plan 13 Task 3: rec.R[sex] indexes the effective sex, male unless NR.SexSpecific; Plan 15 Task 4: no drain
    # input reads the sex (the old fat floor by sex is gone)
    h = eff_host
    rec, p = _female_starved(h)
    minute(h, p, rec, ageH=100.0 + 1 / 60)
    E = rec["effects"]
    nv_off = E["nvDays"]
    floor_male = rec["drain"]["target"]
    setopts(h, SexSpecific=True)
    minute(h, p, rec, ageH=100.0 + 2 / 60)
    assert rec["drain"]["target"] == floor_male
    setopts(h)
    rec2, p2 = _female_starved(h)
    setopts(h, SexSpecific=True)
    minute(h, p2, rec2, ageH=100.0 + 1 / 60)
    assert rec2["effects"]["nvDays"] > nv_off                       # retEma 800 >= the female R 700: retinol replete


def test_the_closed_day_energy_availability_takes_the_exercise_seen(eff_host):
    h = eff_host
    rec = record(h)
    p, _ = player(h, rec)
    minute(h, p, rec)
    body = rec["body"]
    body["exKcalDay"] = 500.0
    minute(h, p, rec, ageH=100.0 + 1 / 60)
    body["dayIndex"] = 5
    body["exKcalDay"] = 0.0                                      # Metabolism's close zeroed it
    body["inDayClosed"] = 2500.0
    minute(h, p, rec, ageH=100.0 + 2 / 60)
    assert abs(rec["effects"]["ea"] - (2500.0 - 500.0) / body["lm"]) < 1e-9


def test_the_refeeding_flag_holds_for_its_day(eff_host):
    h = eff_host
    rec = record(h)
    p, _ = player(h, rec)
    rec["acute"]["refeedEvent"] = True
    rec["body"]["dayIndex"] = 5                                  # set at a close
    minute(h, p, rec)
    assert rec["effects"]["foodSickTarget"] == 55
    minute(h, p, rec, ageH=100.0 + 1 / 60)
    assert rec["effects"]["foodSickTarget"] == 55


# --- the options and the wiring ---------------------------------------------------------------------------

@pytest.mark.parametrize("v, want", [(2.5, 2.5), (5.0, 3.0), (-1.0, 0.0), (float("nan"), 1.0), ("x", 1.0),
                                     (None, 1.0), (0.0, 0.0)])
def test_severity_is_read_and_clamped(eff_host, v, want):
    h = eff_host
    O = setopts(h) if v is None else setopts(h, Severity=v)
    assert O.severity == want


def test_a_severity_change_fires_the_changed_hooks(eff_host):
    h = eff_host
    O = h.G.NutritionRevamp.server.options
    h.rt.execute("NR_TEST_CHANGED = nil")
    O.changed[len(O.changed) + 1] = h.rt.eval("function(old, new) NR_TEST_CHANGED = old.severity end")
    try:
        setopts(h, Severity=2.0)
        assert h.G.NR_TEST_CHANGED == 1.0
    finally:
        O.changed[len(O.changed)] = None


def test_the_forget_hooks_are_wired_once_at_server_start():
    rt = lua51.LuaRuntime(unpack_returned_tuples=True)
    load = rt.eval("function(src, name) return assert(loadstring(src, name)) end")
    with open(CORE, encoding="utf-8") as fh:
        load(fh.read(), "@NR_Core.lua")()
    rt.execute(r"""
        NR_STARTED = {}
        Events = { OnServerStarted = { Add = function(fn) NR_STARTED[#NR_STARTED + 1] = fn end } }
        isServer = function() return true end
        NutritionRevamp.server.players = { onFirstSight = {}, onDeparture = {} }
    """)
    with open(EFFECTS, encoding="utf-8") as fh:
        load(fh.read(), "@NR_Server_Effects.lua")()
    with open(os.path.join(SERVER, "NR_Server_Minute.lua"), encoding="utf-8") as fh:
        load(fh.read(), "@NR_Server_Minute.lua")()
    rt.execute("for i = 1, #NR_STARTED do NR_STARTED[i]() end")
    rt.execute("for i = 1, #NR_STARTED do NR_STARTED[i]() end")
    S = rt.globals().NutritionRevamp.server
    same = rt.eval("rawequal")
    assert same(S.minute.steps["effects"], S.effects.step)       # after nutrients in ORDER (ruling 22)
    assert len(S.players.onFirstSight) == 1 and same(S.players.onFirstSight[1], S.effects.forget)
    assert len(S.players.onDeparture) == 1 and same(S.players.onDeparture[1], S.effects.forget)


def test_the_limitations_name_the_plan_rulings(eff_host):
    lims = list(EFF(eff_host).limitations.values())
    joined = " | ".join(lims)
    for needle in ("one-minute lag", "VITD_EFFECTS false", "omega-3", "X47", "X86", "POISON ships 0",
                   "FOOD_SICKNESS", "capped under moodle level 4 until the starvation", "stale until relog", "X81",
                   "not saved (#3020)", "natively held", "Cat Eyes"):
        assert needle in joined, needle
    # ruling T16-1: the sleep-onset latency terms ship unapplied
    assert ("the sleep-onset latency terms (solAddH, solMul) are stamped and unapplied: under the hybrid vanilla sets "
            "the sleep delay") in lims
    assert any("the cold fold" in s and "X105" in s and "0.1 gate" in s for s in lims)
    assert not any("dmod" in s or "endurance fold" in s for s in lims)   # no drain coefficient and no fold remain
    assert any("X81" in s and "0.45 °C under the set point (x161b)" in s for s in lims)


def test_the_file_names_no_stat_write_and_no_poison():
    with open(EFFECTS, encoding="utf-8") as fh:
        src = fh.read()
    # fix 1 (ruling L2): AddGeneralHealth is named once, the heal toward the floor
    assert src.count('"AddGeneralHealth"') == 1
    for name in ("CharacterStat", ":set(", "setInfectionGrowthRate", "POISON ="):
        assert name not in src, name
    # Plan 15 Task 4: the food heal setHealthFromFood is the one setHealth* the file names (jar-checks Check 2)
    assert re.findall(r"setHealth\w*", src) == ["setHealthFromFood"]

# --- fix 1: the low-BMI hold (M4) and healing toward the floor (L2) ------------------------------------------------

def test_a_fast_keeps_the_penalties_of_a_body_already_under_normal_bmi(eff_host):
    # review M4: the starveEarly hold lifts the pe and ea rows for a body of normal BMI only (S0115)
    h = eff_host
    for bmi, heal, infect in ((15.0, 0.74, 2.30), (22.0, 1.0, 1.0)):
        rec, p, cfg = _starving(h, 28)
        rec["acute"]["bmi"] = bmi
        rec["body"]["dayIndex"] = 5                              # a day close: the pe grade reads the BMI
        minute(h, p, rec, ageH=100.0 + 1 / 60)                   # 28 unfed hours: the early hold
        E = rec["effects"]
        if bmi < 18.5:
            assert E["pe"] == 4 and E["key"]["dials"] % 10000 < 1000, bmi   # no starveEarly
        else:
            assert E["key"]["dials"] % 10000 >= 1000, bmi                     # starveEarly holds the rows off
        assert E["healMul"] == pytest.approx(heal, abs=TOL) and E["infectMul"] == pytest.approx(infect, abs=TOL), bmi


def test_health_under_the_target_heals_toward_it_at_vanillas_pace_and_never_above(eff_host):
    # ruling L2: a wound left health at 20 under clinical scurvy's target (Plan 17 Task 2: about 100 at the onset); vanilla's standard addition 0.002 a
    # multiplier unit x 2 units a game minute per day-length minute (90, the fallback with no sandbox read) = 0.36 a game minute, scaled by
    # scurvy's healMul 0.5 (S0958), through AddGeneralHealth, until the target; never above it, and no drain under it
    h = eff_host
    rec = record(h)
    rec["nutrients"]["vitC"]["g"] = 4
    p, cfg = player(h, rec, health=20.0)
    minute(h, p, rec)
    assert rec["effects"]["healMul"] == 0.5
    assert lst(cfg["log"]["add"]) == [pytest.approx(0.002 * 0.5 * 2 * 90, abs=TOL)]
    assert lst(cfg["log"]["reduce"]) == []
    for m in range(1, 2000):
        minute(h, p, rec, ageH=100.0 + m / 60)
        assert cfg["health"] <= rec["drain"]["target"] + 1e-9
    assert cfg["health"] == pytest.approx(rec["drain"]["target"], abs=0.011)
    n = len(lst(cfg["log"]["add"]))
    assert 1000 < n < 2000 and EFF(h).stats.healMinutes >= n   # about 80 health at 0.18 x 5.05 / 17 a minute: about 1490
    regen = {r["name"]: r["v"] for r in lst(cfg["log"]["regen"])}
    assert regen["setStandardHealthAddition"] == 0 and regen["setHealthFromFood"] == 0   # vanilla's own stays off


def test_the_heal_reads_the_day_length_and_sleep(eff_host):
    h = eff_host
    h.rt.execute("NR_SAVED_SO = getSandboxOptions; getSandboxOptions = function() return "
                 "{ getDayLengthMinutes = function(s) return 90 end } end; NutritionRevamp.so = nil")
    try:
        rec = record(h)
        rec["nutrients"]["vitC"]["g"] = 4
        p, cfg = player(h, rec, health=20.0, asleep=True)
        minute(h, p, rec)
        assert lst(cfg["log"]["add"]) == [pytest.approx(0.02 * 0.5 * 2 * 90, abs=TOL)]   # the sleeping addition, #2354
    finally:
        h.rt.execute("getSandboxOptions = NR_SAVED_SO; NR_SAVED_SO = nil; NutritionRevamp.so = nil")


# --- the food heal and the Overfull rows (Plan 15 Task 8; spec sections 2.3 and 2.4) ----------------------------------

def _food(cfg):
    return [r["v"] for r in lst(cfg["log"]["regen"]) if r["name"] == "setHealthFromFood"]


def test_the_food_heal_is_the_gentle_game_choice_and_0_under_a_drain(eff_host):
    # 0.0087 health per multiplier unit while the bridge holds the timer above 0: a 667 kcal meal's 0.50 h Well Fed spell
    # is 0.0087 x 180 x 30 = 47.0 health at the 90-minute day, a raw can's 0.015 x 3120 = 46.8 in vanilla (#0054)
    h = eff_host
    assert EFF(h).REGEN_FOOD == 0.0087
    assert abs(0.0087 * 180 * 30 - 0.015 * 3120) < 0.5
    rec = record(h)
    p, cfg = player(h, rec, health=100.0)
    minute(h, p, rec)
    assert _food(cfg) == [0.0087]                                 # first sight: written (not saved, #3897)
    rec["nutrients"]["iron"]["x"] = 3                             # a drain state starts: the heal goes to 0
    minute(h, p, rec, ageH=100.0 + 1 / 60)
    assert _food(cfg) == [0.0087, 0]
    minute(h, p, rec, ageH=100.0 + 2 / 60)
    assert _food(cfg) == [0.0087, 0]                              # held: no write while the state holds


def test_the_food_heal_is_written_again_at_first_sight_after_a_load(eff_host):
    # a reload returns the constructor's 0.015 (#3897, jar-checks J1.5): Players' onFirstSight forgets the memory, so the
    # next minute writes the heal again, 0 when the reloaded record's drain is active
    h = eff_host
    rec = record(h)
    p, cfg = player(h, rec, health=100.0)
    minute(h, p, rec)
    minute(h, p, rec, ageH=100.0 + 1 / 60)
    assert _food(cfg) == [0.0087]
    EFF(h).forget("admin")
    minute(h, p, rec, ageH=100.0 + 2 / 60)
    assert _food(cfg) == [0.0087, 0.0087]
    rec["nutrients"]["iron"]["x"] = 3
    minute(h, p, rec, ageH=100.0 + 3 / 60)
    EFF(h).forget("admin")
    minute(h, p, rec, ageH=100.0 + 4 / 60)
    assert _food(cfg) == [0.0087, 0.0087, 0, 0]


def _stomach(h, rec, grams):
    st = h.K.stomach.new()
    st["buffer"]["water"] = grams
    rec["stomach"] = st


def test_overfull_3_holds_the_endurance_ceiling_and_4_adds_nausea(eff_host):
    h = eff_host
    rec = record(h)
    p, cfg = player(h, rec)
    minute(h, p, rec)
    E = rec["effects"]
    assert E["enduranceCap"] == 1 and E["foodSickStep"] == 0 and E["key"]["dials"] % 10000000 < 1000000
    _stomach(h, rec, 900)                                         # Overfull 2 carries no row: no rebuild (fix 1, review L4)
    e0 = E["epoch"]
    minute(h, p, rec, ageH=100.0 + 1 / 60)
    assert E["epoch"] == e0 and (E["key"]["dials"] // 1000000) % 10 == 0
    _stomach(h, rec, 1000)                                        # Overfull 3 (from about 977 g): a rebuild on the level
    minute(h, p, rec, ageH=100.0 + 2 / 60)
    assert E["epoch"] == e0 + 1 and E["enduranceCap"] == 0.73 and E["foodSickStep"] == 0
    assert (E["key"]["dials"] // 1000000) % 10 == 3
    _stomach(h, rec, 1100)                                        # Overfull 4, the hard capacity: nausea at once too
    minute(h, p, rec, ageH=100.0 + 3 / 60)
    assert E["enduranceCap"] == 0.73 and E["foodSickStep"] == 30 and E["foodSickTarget"] == 0
    _stomach(h, rec, 900)                                         # back to Overfull 2: neither
    minute(h, p, rec, ageH=100.0 + 4 / 60)
    assert E["enduranceCap"] == 1 and E["foodSickStep"] == 0


@pytest.mark.parametrize("sev,cap,step", [(0.4, 1, 12), (0.5, 0.73, 15), (1.0, 0.73, 30), (2.0, 0.73, 60)])
def test_the_overfull_slowing_is_on_or_off_by_severity_and_the_nausea_scales(eff_host, sev, cap, step):
    # fix 1 (review L3): the min surface with a sevMin is v at Severity 0.5 or more and 1 below, never partial
    h = eff_host
    setopts(h, Severity=sev)
    rec = record(h)
    _stomach(h, rec, 1100)
    p, _ = player(h, rec)
    minute(h, p, rec)
    E = rec["effects"]
    assert abs(E["enduranceCap"] - cap) < TOL and abs(E["foodSickStep"] - step) < TOL


def test_the_refusal_never_heals_and_leaving_it_restores_the_heal(eff_host):
    # fix 1 (review M1): Overfull 4 with no meal (a litre of water) holds the timer above 0; the food heal is 0 there
    h = eff_host
    rec = record(h)
    p, cfg = player(h, rec, health=100.0)
    minute(h, p, rec)
    assert _food(cfg) == [0.0087]
    _stomach(h, rec, 1150)
    minute(h, p, rec, ageH=100.0 + 1 / 60)
    assert _food(cfg) == [0.0087, 0]
    _stomach(h, rec, 1000)
    minute(h, p, rec, ageH=100.0 + 2 / 60)
    assert _food(cfg) == [0.0087, 0, 0.0087]


@pytest.mark.parametrize("day,food", [(15, 0.0522), (90, 0.0087), (1440, 0.000544)])
def test_the_food_heal_scales_by_90_over_the_day_length(eff_host, day, food):
    # fix 1 (review I2): per multiplier unit, so a Well Fed spell heals the same health at every day length
    h = eff_host
    h.rt.execute("NR_SAVED_SO = getSandboxOptions; getSandboxOptions = function() return "
                 "{ getDayLengthMinutes = function(s) return %d end } end; NutritionRevamp.so = nil" % day)
    try:
        rec = record(h)
        p, cfg = player(h, rec, health=100.0)
        minute(h, p, rec)
        assert _food(cfg) == [pytest.approx(food, rel=1e-3)]
        assert _food(cfg)[0] * 2 * day * 30 == pytest.approx(0.0087 * 180 * 30)   # 47.0 health per 0.50 h spell
    finally:
        h.rt.execute("getSandboxOptions = NR_SAVED_SO; NR_SAVED_SO = nil; NutritionRevamp.so = nil")
