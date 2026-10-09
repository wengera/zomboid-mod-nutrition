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
    cfg.log = { adds = {}, removes = {}, regen = {}, reduce = {}, parts = {}, cold = {}, gets = 0 }
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
        ReduceGeneralHealth = function(s, v) cfg.log.reduce[#cfg.log.reduce + 1] = v end,
    }
    local function setter(name)
        bd[name] = function(s, v) cfg.log.regen[#cfg.log.regen + 1] = { name = name, v = v } end
    end
    setter("setStandardHealthAddition")
    setter("setReducedHealthAddition")
    setter("setSeverlyReducedHealthAddition")
    setter("setSleepingHealthAddition")
    p.getBodyDamage = function(self) return bd end
    return p
end
"""

# A fresh record from the real constructors: an 80 kg male body born at world age 100 (day 4), replete.
RECORD = r"""
function(ageH)
    local K = NutritionRevamp.kernel
    local r = {}
    r.body = K.body.new(80, 1, {}, 5, 1, 1, ageH)
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


def player(h, rec, have=None, parts=None, cold=0.0, setPoint=None, asleep=False):
    cfg = h.table(dict(asleep=asleep, cold=cold))
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
    assert E["epoch"] == 4 and E["key"]["dials"] == 2000 * 1000000 + 100 + 10 + 1
    assert E["dirty"] is True


def test_the_flags_outside_the_key_fold_into_the_dials(eff_host):
    h = eff_host
    rec = record(h)
    p, _ = player(h, rec, asleep=True)
    minute(h, p, rec)
    E = rec["effects"]
    assert E["key"]["dials"] == 1000000000 + 111
    rec["acute"]["boutVig"] = True                                # read while asleep
    minute(h, p, rec, ageH=100.0 + 1 / 60)
    assert E["key"]["dials"] == 1000000000 + 100111 and E["epoch"] == 2
    awake, _ = player(h, rec)
    minute(h, awake, rec, ageH=100.0 + 2 / 60)                    # a latched boutVig awake reads false
    assert E["key"]["dials"] == 1000000000 + 111 and E["epoch"] == 3


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
    assert len(lst(cfg["log"]["regen"])) == n + 4


def test_the_drain_runs_only_with_the_dial_and_zeroes_regeneration(eff_host):
    h = eff_host
    rec = record(h)
    rec["nutrients"]["iron"]["x"] = 3                            # the iron lethal rung: 100 health in 24 h
    p, cfg = player(h, rec)
    setopts(h, DeficienciesCanKill=False)
    minute(h, p, rec, dtM=1.0)
    assert lst(cfg["log"]["reduce"]) == [] and rec["effects"]["drain"] == 0
    assert _regen(cfg)["setStandardHealthAddition"] == 0.002
    setopts(h, DeficienciesCanKill=True)
    minute(h, p, rec, dtM=2.0, ageH=100.0 + 2 / 60)
    rate = 100 / (24 * 60)
    assert abs(rec["effects"]["drain"] - rate) < TOL and rec["effects"]["lethal"] == 7
    assert len(lst(cfg["log"]["reduce"])) == 1 and abs(lst(cfg["log"]["reduce"])[0] - rate * 2) < TOL
    got = lst(cfg["log"]["regen"])[-4:]
    assert all(r["v"] == 0 for r in got)                         # x0 while a drain is active (ruling 13)
    rec["nutrients"]["iron"]["x"] = 0                            # the drain stops: re-asserted at healMul
    minute(h, p, rec, ageH=100.0 + 3 / 60)
    assert lst(cfg["log"]["regen"])[-4]["v"] == 0.002


def test_a_dead_record_is_stepped_with_no_body_write(eff_host):
    h = eff_host
    rec = record(h)
    rec["nutrients"]["iron"]["x"] = 3
    rec["dead"] = True
    p, cfg = player(h, rec)
    minute(h, p, rec)
    assert lst(cfg["log"]["reduce"]) == [] and lst(cfg["log"]["regen"]) == []
    assert rec["effects"]["drain"] > 0


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
    rec["acute"]["starvedDays"] = 11.0                           # pe 4: infectMul 2.30 (S0954)
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


def test_the_dial_key_separates_a_fractional_severity_from_the_kill_dial(eff_host):
    h = eff_host
    rec = record(h)
    p, _ = player(h, rec)
    minute(h, p, rec)
    e0 = rec["effects"]["epoch"]
    setopts(h, Severity=0.1, DeficienciesCanKill=False)
    minute(h, p, rec, ageH=100.0 + 1 / 60)
    e1 = rec["effects"]["epoch"]
    setopts(h, Severity=0.0, DeficienciesCanKill=True)
    minute(h, p, rec, ageH=100.0 + 2 / 60)
    assert rec["effects"]["epoch"] > e1 > e0


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
                   "FOOD_SICKNESS", "capped under moodle level 4", "dmod", "stale until relog", "X81",
                   "not saved (#3020)", "natively held", "Cat Eyes"):
        assert needle in joined, needle
    # ruling T16-1: the sleep-onset latency terms ship unapplied
    assert ("the sleep-onset latency terms (solAddH, solMul) are stamped and unapplied: under the hybrid vanilla sets "
            "the sleep delay (Plan 11)") in lims
    assert any("the cold fold" in s and "X105" in s and "0.1 gate" in s for s in lims)
    assert any("melee swings would drain scaled by dmod" in s and "shipped, they are unscaled" in s for s in lims)
    assert any("X81" in s and "0.45 °C under the set point (x161b)" in s for s in lims)


def test_the_file_names_no_stat_write_and_no_poison():
    with open(EFFECTS, encoding="utf-8") as fh:
        src = fh.read()
    for name in ("CharacterStat", ":set(", "setHealth", "AddGeneralHealth", "setInfectionGrowthRate",
                 "POISON ="):
        assert name not in src, name
