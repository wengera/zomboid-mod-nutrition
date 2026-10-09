"""NR_Server_Nutrients, driven end to end through table-of-functions Java stand-ins (Plan 4 Task 11).

The file is a server/ file the kernel host does not load, so it is loaded on top of the session host with
the adapters it runs after (NR_Server_Kinetics, NR_Server_Metabolism), the record table it steps
(NR_Data_Records, a shared non-kernel file) and the options reader (NR_Server_Options), the way
test_metabolism_shape.py loads Metabolism. NR.call indexes obj[name] and calls it with obj first, so a Lua
table of function fields stands in for a Java object. Every world age, rate, flag and option is stubbed by
hand; the kernel math is the real kernel. A stub proves the wiring, the order and the guards, not the
engine's real getters, which the live acceptance runs read.
"""
import math
import os

import lupa.lua51 as lua51
import pytest

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
SERVER = os.path.join(REPO, "mod", "NutritionRevamp", "common", "media", "lua", "server")
SHARED = os.path.join(REPO, "mod", "NutritionRevamp", "common", "media", "lua", "shared")
CORE = os.path.join(SHARED, "NR_Core.lua")
TOL = 1e-9

SETUP = r"""
function(age)
    local names = { "getGameTime", "CharacterTrait", "Perks", "MoodleType", "BodyPartType",
                    "SwipeStatePlayer", "ZombRandFloat", "ClimbOverFenceState", "ClimbThroughWindowState",
                    "getServerOptions", "SandboxVars" }
    local saved = { age = NR_TEST_AGE, tod = NR_TEST_TOD, rand = NR_TEST_RAND, names = names, vals = {},
                    options = NutritionRevamp.server.options }
    for i = 1, #names do saved.vals[i] = _G[names[i]] end
    NR_TEST_AGE = age
    NR_TEST_TOD = nil
    NR_TEST_RAND = 0.5
    getGameTime = function()
        return {
            getWorldAgeHours = function(self) return NR_TEST_AGE end,
            getTimeOfDay = function(self)
                if NR_TEST_TOD ~= nil then return NR_TEST_TOD end
                return math.fmod(NR_TEST_AGE, 24)
            end,
        }
    end
    CharacterTrait = { ATHLETIC = "ATHLETIC", FIT = "FIT", OUT_OF_SHAPE = "OUT_OF_SHAPE", UNFIT = "UNFIT",
                       STRONG = "STRONG", STOUT = "STOUT", NEEDS_MORE_SLEEP = "NEEDS_MORE_SLEEP",
                       NEEDS_LESS_SLEEP = "NEEDS_LESS_SLEEP" }
    Perks = { Strength = "Strength" }
    MoodleType = { HEAVY_LOAD = "HEAVY_LOAD", HYPERTHERMIA = "HYPERTHERMIA" }
    BodyPartType = { UpperLeg_L = "UpperLeg_L", UpperLeg_R = "UpperLeg_R", LowerLeg_L = "LowerLeg_L",
                     LowerLeg_R = "LowerLeg_R" }
    SwipeStatePlayer = { instance = function() return "SWIPE" end }
    ClimbOverFenceState = { instance = function() return "FENCE" end }
    ClimbThroughWindowState = { instance = function() return "WINDOW" end }
    ZombRandFloat = function(a, b) return NR_TEST_RAND end
    NR_TEST_SLEEP = { SleepAllowed = true, SleepNeeded = true }
    getServerOptions = function()
        return { getBoolean = function(self, name) return NR_TEST_SLEEP[name] end }
    end
    SandboxVars = { NR = {} }
    return saved
end
"""

TEARDOWN = r"""
function(saved)
    NR_TEST_AGE, NR_TEST_TOD, NR_TEST_RAND = saved.age, saved.tod, saved.rand
    for i = 1, #saved.names do _G[saved.names[i]] = saved.vals[i] end
    NutritionRevamp.server.options = saved.options
end
"""

PLAYER = r"""
function(cfg)
    local p = { cfg = cfg }
    p.getUsername = function(self) return "admin" end
    p.getNutrition = function(self)
        return { getWeight = function(s) return self.cfg.weight end }
    end
    p.isFemale = function(self) return self.cfg.female == true end
    p.getCharacterTraits = function(self)
        return { get = function(s, t) return self.cfg.traits[t] == true end }
    end
    p.getPerkLevel = function(self, perk) return 5 end
    p.getMaxWeightDelta = function(self) return 1.0 end
    p.getBodyDamage = function(self)
        local thermo = {
            getMetabolicRate = function(t) return self.cfg.rate end,
            getEnergyMultiplier = function(t) return 1.0 end,
            getFluidsMultiplier = function(t) return self.cfg.fluids end,
        }
        return {
            getThermoregulator = function(s) return thermo end,
            getBodyPart = function(s, part)
                return { getFractureTime = function(b) return 0 end, isSplint = function(b) return false end }
            end,
        }
    end
    p.getInventoryWeight = function(self) return 0 end
    p.getMaxWeight = function(self) return 20 end
    p.isPlayerMoving = function(self) return false end
    p.isAsleep = function(self) return self.cfg.asleep == true end
    p.getMoodles = function(self)
        return { getMoodleLevel = function(s, m) return 0 end }
    end
    p.getFitness = function(self)
        return { getCurrentExe = function(s) return nil end }
    end
    p.isCurrentState = function(self, st) return false end
    return p
end
"""

# One slow-clock minute in the game's order: the stomach, the body, then this file, on one context.
CHAIN = r"""
function(player, record, age)
    NR_TEST_AGE = age
    local S = NutritionRevamp.server
    local pipe = {}
    S.kinetics.minute("admin", player, record, pipe)
    S.metabolism.minute("admin", player, record, pipe)
    S.nutrients.minute("admin", player, record, pipe)
    return record
end
"""

# This file's minute alone (the handoff set by hand on a context, or none).
ALONE = r"""
function(player, record, age, pipe)
    NR_TEST_AGE = age
    NutritionRevamp.server.nutrients.minute("admin", player, record, pipe)
    return record
end
"""

RAISING = r"""
function(player, record, age)
    local K = NutritionRevamp.kernel
    local orig = K.nutrients.minute
    K.nutrients.minute = function() error("boom") end
    NR_TEST_AGE = age
    local ok, err = pcall(NutritionRevamp.server.nutrients.minute, "admin", player, record)
    K.nutrients.minute = orig
    return ok, err
end
"""

NONFINITE = r"""
function(record)
    local bad = {}
    local function walk(t, path)
        for k, v in pairs(t) do
            if type(v) == "number" then
                if v ~= v or v == math.huge or v == -math.huge then bad[#bad + 1] = path .. "." .. tostring(k) end
            elseif type(v) == "table" then
                walk(v, path .. "." .. tostring(k))
            end
        end
    end
    walk(record.nutrients, "nutrients")
    walk(record.fluids, "fluids")
    walk(record.acute, "acute")
    return table.concat(bad, ",")
end
"""

READ = r"""
function(nr)
    SandboxVars = { NR = nr }
    return NutritionRevamp.server.readOptions("test")
end
"""

NAN = float("nan")


def _load(host, path, name):
    with open(path, encoding="utf-8") as fh:
        src = fh.read()
    host.rt.eval("function(src, name) return assert(loadstring(src, name)) end")(src, name)()


@pytest.fixture(scope="module")
def nut_host(host):
    if host.G.NutritionRevamp.server.intake is None:
        _load(host, os.path.join(SERVER, "NR_Server_Intake.lua"), "@NR_Server_Intake.lua")
    saved = host.rt.eval(SETUP)(100.0)
    _load(host, os.path.join(SERVER, "NR_Server_Kinetics.lua"), "@NR_Server_Kinetics.lua")
    _load(host, os.path.join(SERVER, "NR_Server_Metabolism.lua"), "@NR_Server_Metabolism.lua")
    _load(host, os.path.join(SHARED, "NR_Data_Records.lua"), "@NR_Data_Records.lua")
    _load(host, os.path.join(SERVER, "NR_Server_Options.lua"), "@NR_Server_Options.lua")
    _load(host, os.path.join(SERVER, "NR_Server_Nutrients.lua"), "@NR_Server_Nutrients.lua")
    host.G.NutritionRevamp.server.readOptions("test")
    # the gut lane's pending sums start empty here: an earlier module's landings never reach these records
    host.G.NutritionRevamp.server.intake.pendingAlc = host.rt.table()
    host.G.NutritionRevamp.server.intake.pendingCaf = host.rt.table()
    try:
        yield host
    finally:
        host.G.NutritionRevamp.server.intake.lastIngested = None
        host.rt.eval(TEARDOWN)(saved)


def NUT(h):
    return h.G.NutritionRevamp.server.nutrients


def KIN(h):
    return h.G.NutritionRevamp.server.kinetics


def player(h, **kw):
    base = dict(weight=80.0, female=False, traits={}, rate=1.5, fluids=1.0, asleep=False)
    base.update(kw)
    return h.rt.eval(PLAYER)(h.table(base))


def chain(h, p, record, age):
    return h.rt.eval(CHAIN)(p, record, age)


def alone(h, p, record, age, pipe=None):
    return h.rt.eval(ALONE)(p, record, age, pipe)


def handed(h, absorbed, mealCa=None):
    # the pipeline's context (Plan 10 R2) carrying Kinetics' handoffs, set by hand
    pipe = h.rt.table()
    pipe.absorbed = absorbed
    pipe.mealCa = mealCa
    return pipe


def fresh(h, p, age=100.0):
    record = h.rt.table()
    chain(h, p, record, age)
    return record


def nonfinite(h, record):
    return h.rt.eval(NONFINITE)(record)


def order(h):
    return list(h.G.NutritionRevamp.data.records.ORDER.values())


def vec(h, **kw):
    v = h.K.vector.new()
    for k, x in kw.items():
        v[k] = x
    return v


def expected_thirst(dehyd, lm, water, na=0.0):
    # K.fluids.thirstTarget recomputed in doubles: the volume knots and the osmotic term (Edelman, k = 0)
    knots = [(0, 0), (1, 0.12), (2, 0.25), (4, 0.70), (6, 0.84), (8, 1.0)]
    d = min(max(dehyd, 0), 8)
    tvol = 1.0
    for (x0, y0), (x1, y1) in zip(knots, knots[1:]):
        if d <= x1:
            tvol = y0 + (y1 - y0) * (d - x0) / (x1 - x0)
            break
    t0 = 0.73 * lm
    p0 = 140 * t0
    c = (p0 + na) / p0 * t0 / max(t0 + water / 1000, 0.1 * t0)
    tosm = 0.25 * min(max((c - 1) / 0.03, 0), 4)
    return 1 - (1 - tvol) * (1 - min(tosm, 1)), c


# --- creation and the guards --------------------------------------------------------------------------

def test_fresh_record_gains_the_three_sub_tables(nut_host):
    h = nut_host
    record = fresh(h, player(h))
    n, f, a = record["nutrients"], record["fluids"], record["acute"]
    assert n is not None and f is not None and a is not None
    for key in order(h):
        assert n[key]["p"] == 1, key
        assert n[key]["g"] == 1, key
    assert "nv" not in n and n["epoch"] == 0
    assert abs(n["lastAgeH"] - 100.0) < TOL
    assert n["lastDayIndex"] == record["body"]["dayIndex"] == 4
    assert "fv" not in f and f["water"] == 0 and f["viewPct"] == 0
    assert abs(f["sweatK"] - 1.0) < TOL                     # 0.5 + 1.0 x the stub roll 0.5
    assert abs(f["naSweat"] - 30.0) < TOL                   # 10 + 80 x 0.5^2
    assert "av" not in a and a["slowMet"] is False          # roll 0.5 is not < 0.5
    assert abs(a["lastFedAgeH"] - 100.0) < TOL and a["alc7"] == 0 and a["alcDayG"] == 0
    assert nonfinite(h, record) == ""


def test_draws_fall_back_without_zombrandfloat(nut_host):
    h = nut_host
    saved = h.G.ZombRandFloat
    h.G.ZombRandFloat = None
    try:
        record = fresh(h, player(h))
    finally:
        h.G.ZombRandFloat = saved
    assert abs(record["fluids"]["sweatK"] - 1.0) < TOL
    assert abs(record["fluids"]["naSweat"] - 37.0) < 1e-9   # the fallback roll lands on 37 exactly
    assert record["acute"]["slowMet"] is False              # fallback roll 0.75


def test_zero_dt_returns_and_lands_nothing_of_the_handoff(nut_host):
    h = nut_host
    p = player(h)
    record = fresh(h, p)
    played = NUT(h).stats.players
    alone(h, p, record, 100.0, handed(h, vec(h, water=500)))  # same age: dtM 0
    assert NUT(h).stats.players == played
    assert record["fluids"]["water"] == 0
    assert KIN(h).lastAbsorbed is None                      # the handoff rides the context (Plan 10 R2)


def test_unreadable_age_and_missing_body_are_counted(nut_host):
    h = nut_host
    p = player(h)
    bad = NUT(h).stats.badAge
    record = h.rt.table()
    alone(h, p, record, NAN)
    assert NUT(h).stats.badAge == bad + 1
    assert record["nutrients"] is None
    nobody = NUT(h).stats.noBody
    alone(h, p, record, 100.0)
    assert NUT(h).stats.noBody == nobody + 1
    assert record["nutrients"] is None
    NUT(h).minute("admin", p, None)                         # a nil record is a no-op


def test_a_raising_minute_is_caught_and_counted(nut_host):
    h = nut_host
    p = player(h)
    record = fresh(h, p)
    errors = NUT(h).stats.errors
    ok, err = h.rt.eval(RAISING)(p, record, 100.0 + 1 / 60)
    assert ok is True
    assert NUT(h).stats.errors == errors + 1
    assert "boom" in str(NUT(h).lastError)


# --- the records ----------------------------------------------------------------------------------------

def test_forty_days_of_zero_intake_reach_clinical_scurvy(nut_host):
    h = nut_host
    p = player(h)
    record = fresh(h, p)
    for i in range(1, 40 * 24 + 1):
        chain(h, p, record, 100.0 + i)
    n = record["nutrients"]
    assert n["vitC"]["g"] == 4
    assert n["epoch"] > 0
    assert n["allReplete"] is False
    a = record["acute"]
    assert a["refeedRisk"] == 2                             # more than 10 starved days (S0115)
    assert a["starvedDays"] > 10
    assert nonfinite(h, record) == ""


def test_the_interaction_factors_and_the_vitamin_a_fold(nut_host):
    h = nut_host
    p = player(h)
    record = fresh(h, p)
    lm = record["body"]["lm"]
    ab = vec(h, iron=1.0, calcium=150.0, magnesium=10.0, zinc=2.0, caffeine=100.0, ethanol=1.0,
             retinol=100.0, carotene=50.0)
    alone(h, p, record, 100.0 + 1 / 60, handed(h, ab))
    assert abs(ab["iron"] - 0.75) < TOL                     # 1 - 0.5 x 150/300
    cafLoss = 0.02 * 100 * 60 / lm
    assert abs(ab["magnesium"] - (10.0 - cafLoss - 2.0)) < 1e-9
    assert abs(ab["calcium"] - (150.0 - cafLoss)) < 1e-9
    assert abs(ab["zinc"] - 2.0) < TOL                      # the phytate factors live in the stomach kernel
    assert abs(ab["vitA"] - 100.0) < TOL                    # liver p = 1: carotene conversion off (S0202)
    record["nutrients"]["vitA"]["p"] = 0.5
    ab2 = vec(h, retinol=100.0, carotene=50.0, magnesium=1.0, caffeine=1000.0)
    alone(h, p, record, 100.0 + 2 / 60, handed(h, ab2))
    assert abs(ab2["vitA"] - 125.0) < TOL                   # 100 + 0.5 x 50 (the 2:1 equivalence)
    record["nutrients"]["vitA"]["p"] = 0.5
    ab3 = vec(h, carotene=1000.0)
    alone(h, p, record, 100.0 + 3 / 60, handed(h, ab3))
    assert abs(ab3["vitA"] - 500.0) < TOL                   # 1000 ug carotene at p 0.5 adds 500
    record["nutrients"]["vitA"]["p"] = 1.0
    ab4 = vec(h, carotene=1000.0)
    alone(h, p, record, 100.0 + 4 / 60, handed(h, ab4))
    assert abs(ab4["vitA"]) < TOL                           # at p 1.0 adds 0
    assert ab2["magnesium"] == 0                            # floored at 0


def test_ingested_is_consumed_and_vitamin_a_reads_preformed_retinol(nut_host):
    h = nut_host
    p = player(h)
    record = fresh(h, p)
    IN = h.G.NutritionRevamp.server.intake
    ing = h.table({"retinol": 3500.0, "carotene": 9000.0, "ethanol": 14.0})
    IN.lastIngested = h.table({"admin": ing})
    try:
        alone(h, p, record, 100.0 + 1 / 60)
        assert IN.lastIngested["admin"] is None
        assert ing["vitA"] == 3500.0
        assert record["nutrients"]["vitA"]["x"] == 1        # e24 3500 >= the 3000 UL (S0136)
        assert abs(record["body"]["alcDay"] - 14.0) < TOL
        assert abs(record["acute"]["alcDayG"] - 14.0) < TOL
    finally:
        IN.lastIngested = None


def test_excess_off_forces_every_rung_to_zero(nut_host):
    h = nut_host
    p = player(h)
    record = fresh(h, p)
    IN = h.G.NutritionRevamp.server.intake
    h.rt.eval(READ)(h.table({"ExcessEffectsOn": False}))
    IN.lastIngested = h.table({"admin": h.table({"retinol": 3500.0})})
    try:
        alone(h, p, record, 100.0 + 1 / 60)
        assert record["nutrients"]["vitA"]["x"] == 0
        assert record["nutrients"]["vitA"]["e24"] > 3000    # the state still integrates
    finally:
        IN.lastIngested = None
        h.rt.eval(READ)(h.table({}))


def test_the_day_close_reads_the_closed_day_and_the_alcohol_mean(nut_host):
    h = nut_host
    p = player(h)
    record = fresh(h, p, 119.0)                             # day 4, closing at 120
    IN = h.G.NutritionRevamp.server.intake
    IN.lastIngested = h.table({"admin": h.table({"ethanol": 28.0})})
    try:
        alone(h, p, record, 119.5, handed(h, vec(h, calories=400.0)))
    finally:
        IN.lastIngested = None
    assert abs(record["body"]["alcDay"] - 28.0) < TOL
    record["body"]["inDay"] = 800.0                         # the day's absorbed kcal as Metabolism banks it
    days = NUT(h).stats.days
    chain(h, p, record, 120.5)
    body, a, n = record["body"], record["acute"], record["nutrients"]
    assert body["dayIndex"] == 5 and n["lastDayIndex"] == 5
    assert NUT(h).stats.days == days + 1
    assert body["alcDay"] == 0                              # Metabolism's partition close zeroed it
    assert abs(body["inDayClosed"] - 800.0) < 1e-6          # Metabolism's one new stamp
    w = body["fm"] + body["lm"]
    assert abs(a["alc7"] - 28.0 / w / 7) < 1e-9
    assert a["alcDayG"] == 0
    assert a["lowDay"] is False                             # 800/80 = 10 kcal/kg is not below 5 (S1116)
    assert a["mass90max"] > 0 and a["bmi"] > 0
    assert a["refeedRisk"] in (0, 1, 2)


def test_a_multi_day_jump_closes_one_refeeding_day(nut_host):
    h = nut_host
    p = player(h)
    record = fresh(h, p)
    skipped = NUT(h).stats.skippedDays
    chain(h, p, record, 100.0 + 72.0)
    assert record["nutrients"]["lastDayIndex"] == record["body"]["dayIndex"]
    assert NUT(h).stats.skippedDays == skipped + 2


# --- the fluids ---------------------------------------------------------------------------------------

def test_one_litre_of_water_lands_then_clears(nut_host):
    h = nut_host
    p = player(h)
    record = fresh(h, p)
    alone(h, p, record, 100.0 + 1 / 60, handed(h, vec(h, water=1000.0)))
    assert KIN(h).lastAbsorbed is None                      # the handoff rides the context (Plan 10 R2)
    f = record["fluids"]
    w1 = 1000.0 - 3700 / 1440 - 320 / 60                    # landed, the basal minute, the clearance minute
    assert abs(f["water"] - w1) < 1e-6
    for i in range(2, 62):
        alone(h, p, record, 100.0 + i / 60)
    assert f["water"] < w1 - 300                            # an hour's clearance at 320 g/h
    assert f["dehydPct"] == 0 and f["viewPct"] == 0


def test_ten_hours_at_rest(nut_host):
    h = nut_host
    p = player(h)
    record = fresh(h, p)
    for i in range(1, 11):
        chain(h, p, record, 100.0 + i)
    f, body = record["fluids"], record["body"]
    w = body["fm"] + body["lm"]
    assert abs(w - 80.0) < 1e-6
    assert abs(f["water"] + 3700 * 600 / 1440) < 1e-6
    assert abs(f["dehydPct"] - 1.9270833333333133) < 1e-6
    # the basal sodium: -1541.67 g x 0.65 x 140 / 1000 = -140.29 mmol (T11-3)
    assert abs(f["na"] + 3700 * 600 / 1440 / 1000 * 0.65 * 140) < 1e-6
    want, c = expected_thirst(f["dehydPct"], body["lm"], f["water"], f["na"])
    assert abs(f["c"] - c) < 1e-9
    assert abs(f["naPlasma"] - 140 * c) < 1e-6
    assert abs(f["thirstTarget"] - want) < 1e-9
    # the volume term alone is the plan's 0.24; the osmotic term of a solute-free basal loss adds to it
    assert f["thirstTarget"] > 0.2405
    assert f["sweatActive"] is False


def test_the_thirst_view_reads_the_stomach_pending_water(nut_host):
    h = nut_host
    p = player(h)
    record = fresh(h, p)
    for i in range(1, 11):
        chain(h, p, record, 100.0 + i)
    before = record["fluids"]["thirstTarget"]
    record["stomach"]["buffer"]["water"] = 1000.0
    alone(h, p, record, 110.0 + 1 / 60)
    f = record["fluids"]
    assert f["viewPct"] < f["dehydPct"]                     # ruling T1-1: the view counts the pending litre
    assert abs(f["dehydPct"] - f["viewPct"] - 100 * 1.0 / 80.0) < 1e-6
    assert f["thirstTarget"] < before


def test_the_thirst_view_reads_the_liquid_lanes_water_too(nut_host):
    h = nut_host
    p = player(h)
    record = fresh(h, p)
    for i in range(1, 11):
        chain(h, p, record, 100.0 + i)
    before = record["fluids"]["thirstTarget"]
    record["stomach"]["liquid"] = 1000.0
    alone(h, p, record, 110.0 + 1 / 60)
    f = record["fluids"]
    assert abs(f["dehydPct"] - f["viewPct"] - 100 * 1.0 / 80.0) < 1e-6   # ruling T1-1, both lanes' water
    assert f["thirstTarget"] < before


def test_the_kill_cap_and_its_dial(nut_host):
    h = nut_host
    p = player(h)
    record = fresh(h, p)
    f = record["fluids"]
    f["water"] = -0.08 * 80.0 * 1000                        # an 8 % deficit
    h.rt.eval(READ)(h.table({"DeficienciesCanKill": False}))
    try:
        alone(h, p, record, 100.0 + 1 / 60)
        assert f["dehydPct"] > 8
        assert abs(f["thirstTarget"] - 0.83) < TOL          # ruling 8: under vanilla's lethal level
    finally:
        h.rt.eval(READ)(h.table({}))
    alone(h, p, record, 100.0 + 2 / 60)
    assert abs(f["thirstTarget"] - 1.0) < TOL


def test_an_auto_drink_drop_lands_in_the_liquid_lane(nut_host):
    h = nut_host
    p = player(h)
    record = fresh(h, p)
    liquid0 = record["stomach"]["liquid"] or 0
    water0 = record["stomach"]["buffer"]["water"]
    record["fluids"]["autoDrop"] = 0.2
    alone(h, p, record, 100.0 + 1 / 60)
    assert abs(record["stomach"]["liquid"] - liquid0 - 400.0) < 1e-9   # 2 L per THIRST x 0.2
    assert record["stomach"]["buffer"]["water"] == water0
    assert record["fluids"]["autoDrop"] == 0
    # a record with no stomach yet gets an empty one (ruling 11c-15)
    record["stomach"] = None
    record["fluids"]["autoDrop"] = 0.1
    alone(h, p, record, 100.0 + 2 / 60)
    assert abs(record["stomach"]["liquid"] - 200.0) < 1e-9
    assert record["stomach"]["buffer"]["water"] == 0


def test_sweat_reads_the_thermoregulator_fluids_multiplier(nut_host):
    h = nut_host
    p = player(h, fluids=2.0)
    record = fresh(h, p)
    record["body"]["met"] = 8.0                             # Task 13's stamp, set by hand
    alone(h, p, record, 100.0 + 1 / 60)
    f = record["fluids"]
    assert abs(f["sweatLmin"] - 1.0 * 1.0 * 2.0 * 1.0 / 60) < 1e-12   # 1 L/h x 1 x 2 x sweatK 1, one minute
    assert abs(f["na"] - (-(2.0 / 60) * 30.0 - 3700 / 1440 / 1000 * 0.65 * 140)) < 1e-9   # sweat sodium 30 plus the basal
    record["body"]["met"] = None
    p2 = player(h, fluids=NAN)                              # a non-finite read is 1
    record2 = fresh(h, p2)
    record2["body"]["met"] = 8.0
    alone(h, p2, record2, 100.0 + 1 / 60)
    assert abs(record2["fluids"]["sweatLmin"] - 1.0 / 60) < 1e-12
    record3 = fresh(h, player(h))
    record3["body"]["met"] = NAN                            # a NaN stamped upstream: the losses run at met 1
    record3["body"]["coldMult"] = NAN
    alone(h, p, record3, 100.0 + 1 / 60)
    assert record3["fluids"]["sweatLmin"] == 0
    assert nonfinite(h, record3) == ""


# --- the acute states --------------------------------------------------------------------------------

def test_beer_raises_then_clears_blood_alcohol(nut_host):
    h = nut_host
    p = player(h)
    record = fresh(h, p)
    alone(h, p, record, 100.0 + 1 / 60, handed(h, vec(h, ethanol=14.0)))
    a = record["acute"]
    peak = a["bac"]
    assert abs(peak - (14.0 - 0.015 * 0.68 * 80 * 10 / 60) / (10 * 0.68 * 80)) < 1e-9
    alone(h, p, record, 100.0 + 2 / 60)
    assert a["bac"] < peak
    for i in range(1, 6):
        alone(h, p, record, 100.0 + 2 / 60 + i)
    assert a["bac"] == 0
    assert a["alcPeak"] == 0                                # a sub-0.05 % peak leaves no hangover


def test_caffeine_glycogen_and_glucose_step(nut_host):
    h = nut_host
    p = player(h)
    record = fresh(h, p)
    alone(h, p, record, 100.0 + 1 / 60, handed(h, vec(h, caffeine=100.0, carbs=30.0)))
    a = record["acute"]
    assert abs(a["caf"] - 100.0) < TOL
    assert a["bg"] == 5.0
    assert 0 < a["g"] <= 1
    assert a["iu"] >= 0


def test_sleep_disabled_freezes_and_enabled_runs(nut_host):
    h = nut_host
    p = player(h)
    h.G.NR_TEST_SLEEP.SleepNeeded = False
    try:
        assert NUT(h).readSleepOptions() is True
        record = fresh(h, p)
        alone(h, p, record, 100.0 + 1)
        assert record["acute"]["frozen"] is True
        assert record["acute"]["awakeH"] == 0
    finally:
        h.G.NR_TEST_SLEEP.SleepNeeded = True
    assert NUT(h).readSleepOptions() is False
    alone(h, p, record, 100.0 + 2)
    assert record["acute"]["frozen"] is False
    assert abs(record["acute"]["awakeH"] - 1.0) < TOL
    saved = h.G.getServerOptions
    h.G.getServerOptions = None
    try:
        assert NUT(h).readSleepOptions() is False             # unreadable: not disabled
    finally:
        h.G.getServerOptions = saved


@pytest.mark.parametrize("traits, need", [({}, 7.5), ({"NEEDS_MORE_SLEEP": True}, 7.5 * 1.3),
                                          ({"NEEDS_LESS_SLEEP": True}, 7.5 * 0.7)])
def test_the_sleep_need_takes_the_trait_factor(nut_host, traits, need):
    h = nut_host
    NUT(h).sleepDisabled = False
    p = player(h, traits=traits)
    record = fresh(h, p)
    for i in range(1, 25):
        alone(h, p, record, 100.0 + i)                      # 24 h awake: the window books no sleep
    assert abs(record["acute"]["debtH"] - need) < 1e-9


def test_asleep_accrues_sleep(nut_host):
    h = nut_host
    NUT(h).sleepDisabled = False
    p = player(h, asleep=True)
    record = fresh(h, p)
    alone(h, p, record, 100.0 + 1)
    assert abs(record["acute"]["sleptH"] - 1.0) < TOL


# --- the x151r fix wave: the meal calcium and the gut lane (rulings T17-1, T17-2) -------------------------

def test_calcium_iron_reads_the_meal_calcium_handoff(nut_host):
    h = nut_host
    p = player(h)
    record = fresh(h, p)
    ab = vec(h, iron=1.0, calcium=10.0)
    pipe = handed(h, ab, 150.0)                             # the buffer's calcium before the emptying
    alone(h, p, record, 100.0 + 1 / 60, pipe)
    assert abs(ab["iron"] - 0.75) < TOL                     # 1 - 0.5 x 150/300, not 1 - 0.5 x 10/300
    assert KIN(h).lastMealCa is None                        # the handoff rides the context (Plan 10 R2)


def test_the_chain_hands_the_bread_calcium_to_the_iron_factor(nut_host):
    # a loaf in the stomach: the pool takes the stomach factor 0.18 x exp(-0.0034 x 400) per mg emptied,
    # the record engine's absorbed iron that times 1 - 0.5 x 95/300 (0.0388841 per mg, the first minute)
    h = nut_host
    p = player(h)
    record = fresh(h, p)
    st = record["stomach"]
    for k in h.K.vector.KEYS.values():
        st["buffer"][k] = 0
    st["buffer"]["iron"] = 6.5
    st["buffer"]["phytate"] = 400.0
    st["buffer"]["calcium"] = 95.0
    st["buffer"]["calories"] = 532.0
    seen = {}
    h.rt.execute("NR_TEST_SEEN = nil")
    saved = h.K.nutrients.minute
    spy = h.rt.eval("""function(orig) return function(n, recs, absorbed, ingested, ctx, dtM)
        NR_TEST_SEEN = absorbed.iron
        return orig(n, recs, absorbed, ingested, ctx, dtM) end end""")(saved)
    h.K.nutrients.minute = spy
    try:
        chain(h, p, record, 100.0 + 1 / 60)
    finally:
        h.K.nutrients.minute = saved
    emptied = 6.5 - st["buffer"]["iron"]
    assert abs(h.G.NR_TEST_SEEN / emptied - 0.18 * math.exp(-0.0034 * 400) * (1 - 0.5 * 95 / 300)) < 1e-12
    assert abs(h.G.NR_TEST_SEEN / emptied - 0.03888410770846372) < 1e-12


def test_the_gut_lane_drains_and_releases(nut_host):
    h = nut_host
    p = player(h)
    record = fresh(h, p)
    IN = h.G.NutritionRevamp.server.intake
    IN.pendingAlc["admin"] = 11.85
    IN.pendingCaf["admin"] = 107.0
    alone(h, p, record, 100.0 + 1 / 60)
    a = record["acute"]
    f = 1 - math.exp(-math.log(2) * (1 / 60) / 0.5)
    assert IN.pendingAlc["admin"] is None and IN.pendingCaf["admin"] is None
    assert abs(a["gutAlc"] - 11.85 * (1 - f)) < 1e-12
    assert abs(a["gutCaf"] - 107.0 * (1 - f)) < 1e-12
    assert abs(a["caf"] - 107.0 * f) < 1e-12
    assert abs(a["alc"] - (11.85 * f - 0.015 * 0.68 * 80 * 10 / 60)) < 1e-12   # male 80 kg
    w0 = a["gutAlc"]
    for i in range(2, 32):
        alone(h, p, record, 100.0 + i / 60)
    assert abs(a["gutAlc"] - w0 * (1 - f) ** 30) < 1e-9      # half again in the next 30 minutes
    assert a["bac"] > 0


def test_a_skipped_minute_keeps_the_pending_dose(nut_host):
    h = nut_host
    p = player(h)
    record = fresh(h, p)
    IN = h.G.NutritionRevamp.server.intake
    IN.pendingAlc["admin"] = 5.0
    IN.pendingCaf["admin"] = None
    alone(h, p, record, NAN)                                # an unreadable age: skipped before the drain
    assert IN.pendingAlc["admin"] == 5.0
    alone(h, p, record, 100.0)                              # dtM 0: drained onto the record, nothing released
    assert IN.pendingAlc["admin"] is None
    assert record["acute"]["gutAlc"] == 5.0 and record["acute"]["gutCaf"] == 0


def test_a_landed_drink_reaches_the_blood_through_the_gut(nut_host):
    # the full path: IN.land diverts, the next minutes drain and release; the stomach never holds either key
    h = nut_host
    p = player(h)
    record = fresh(h, p)
    IN = h.G.NutritionRevamp.server.intake
    v = vec(h, ethanol=10.0, caffeine=50.0, water=300.0)
    IN.lastIngested = h.rt.table()
    try:
        IN.land(record, "admin", v)
        assert record["stomach"]["buffer"]["ethanol"] == 0 and record["stomach"]["buffer"]["caffeine"] == 0
        bacMax = 0
        for i in range(1, 61):
            chain(h, p, record, 100.0 + i / 60)
            bacMax = max(bacMax, record["acute"]["bac"])
    finally:
        IN.lastIngested = None
    a = record["acute"]
    assert abs(a["gutAlc"] - 5.0 * 0.5) < 1e-9               # two half-times: a quarter left
    assert abs(a["gutCaf"] - 12.5) < 1e-9
    assert a["caf"] > 30 and bacMax > 0                     # the stomach lane never raised it (x151r #2983)
    assert abs(record["acute"]["alcDayG"] - 10.0) < TOL      # the day total reads the ingested amount


# --- Plan 5 Task 5: the band baselines and their feeds -----------------------------------------------------


def test_the_minute_band_is_read_off_the_accumulators_growth(nut_host):
    h = nut_host
    p = player(h)
    record = fresh(h, p)
    body, a = record["body"], record["acute"]
    assert a["exEma"] == 0
    body["band1Day"] = body["band1Day"] + 1.0               # band 1: Metabolism's sample added one minute
    alone(h, p, record, 100.0 + 1 / 60)
    assert abs(a["exEma"] - 1.0) < TOL                      # 0 * exp(-1/360) + 60 * (1/60)
    assert a["lastVigAgeH"] == -1e9
    body["band1Day"] = body["band1Day"] + 1.0               # band 2 grows both accumulators
    body["band2Day"] = body["band2Day"] + 1.0
    alone(h, p, record, 100.0 + 2 / 60)
    assert abs(a["exEma"] - (math.exp(-1 / 360) + 1.0)) < TOL
    assert abs(a["lastVigAgeH"] - (100.0 + 2 / 60)) < TOL
    alone(h, p, record, 100.0 + 3 / 60)                     # no growth: band 0, the memory decays
    assert abs(a["exEma"] - (math.exp(-1 / 360) + 1.0) * math.exp(-1 / 360)) < TOL
    assert (a["lastB1"], a["lastB2"]) == (body["band1Day"], body["band2Day"])


def test_the_minute_band_across_a_day_close(nut_host):
    h = nut_host
    p = player(h)
    record = fresh(h, p)
    body, a = record["body"], record["acute"]
    body["band1Day"] = 30.0
    body["band2Day"] = 10.0
    alone(h, p, record, 100.0 + 1 / 60)                     # baselines 30 / 10 (a band-2 minute)
    vig = a["lastVigAgeH"]
    # Metabolism sampled a band-2 minute, then closed the day: slot 7 holds 31 / 11, the accumulators 0
    body["dayIndex"] = body["dayIndex"] + 1
    body["bandWeek"][7][1] = 31.0
    body["bandWeek"][7][2] = 11.0
    body["band1Day"] = 0.0
    body["band2Day"] = 0.0
    alone(h, p, record, 100.0 + 2 / 60)
    assert abs(a["lastVigAgeH"] - (100.0 + 2 / 60)) < TOL and a["lastVigAgeH"] != vig
    assert (a["lastB1"], a["lastB2"]) == (0.0, 0.0)
    # a close with no exercise in the closing minute reads band 0
    body["dayIndex"] = body["dayIndex"] + 1
    body["bandWeek"][7][1] = 0.0
    body["bandWeek"][7][2] = 0.0
    e = a["exEma"]
    alone(h, p, record, 100.0 + 3 / 60)
    assert abs(a["exEma"] - e * math.exp(-1 / 360)) < TOL
    # a two-day jump reads the new day's growth alone; a missing ring reads it too
    body["dayIndex"] = body["dayIndex"] + 2
    body["band1Day"] = 1.0
    alone(h, p, record, 100.0 + 4 / 60)
    assert abs(a["exEma"] - (e * math.exp(-2 / 360) + 1.0)) < TOL
    body["dayIndex"] = body["dayIndex"] + 1
    body["bandWeek"] = None
    body["band1Day"] = 0.0
    alone(h, p, record, 100.0 + 5 / 60)
    assert abs(a["exEma"] - (e * math.exp(-2 / 360) + 1.0) * math.exp(-1 / 360)) < TOL
    assert abs(a["lastVigAgeH"] - (100.0 + 2 / 60)) < TOL
    lims = list(NUT(h).limitations.values())
    assert "the minute's training band is read off the growth of Metabolism's day accumulators band1Day/band2Day (no per-minute band is stamped); a minute whose day close skipped days reads the new day's growth alone" in lims


def test_a_vigorous_minute_latches_the_next_bout(nut_host):
    h = nut_host
    NUT(h).sleepDisabled = False
    p = player(h)
    record = fresh(h, p)
    body, a = record["body"], record["acute"]
    body["band1Day"] = body["band1Day"] + 1.0
    body["band2Day"] = body["band2Day"] + 1.0
    alone(h, p, record, 100.0 + 1 / 60)
    assert a["boutVig"] is False
    sleeper = player(h, asleep=True)
    alone(h, sleeper, record, 100.0 + 31 / 60)              # asleep 0.5 h after the band-2 minute
    assert a["boutVig"] is True


def test_cold_retinol_and_the_sleep_term_are_fed(nut_host):
    h = nut_host
    p = player(h)
    record = fresh(h, p)
    a = record["acute"]
    record["body"]["coldMult"] = 1.5
    IN = h.G.NutritionRevamp.server.intake
    IN.lastIngested = h.table({"admin": h.table({"retinol": 900.0})})
    try:
        alone(h, p, record, 100.0 + 1 / 60)
    finally:
        IN.lastIngested = None
    assert abs(a["coldH"] - 1 / 60) < TOL
    # 900 ug in one minute: 900 * 1440 * (1 - exp(-(1/1440)/14)) = 64.28411992435912
    assert abs(a["retEma"] - 64.28411992435912) < 1e-9
    assert a["iuSleep"] == h.K.acute.iuSleep(a)


def test_limitations_name_the_fix_wave(nut_host):
    lims = list(NUT(nut_host).limitations.values())
    assert "caffeine and ethanol absorb on a 0.5 h gut lane that a full stomach does not slow (ruling T17-2; S1102 open): a drink with a meal peaks as early as one on an empty stomach" in lims
    assert "the interaction factors read the stomach buffer's phytate, vitC and calcium before each minute's emptying (ruling T17-1): two meals in the buffer act as one meal, and the inhibition eases as the buffer empties" in lims
    assert "a sleep bout tolerates awake gaps under 10 game minutes (ruling T17-4, S1112 open): a real wake of under 10 minutes inside a night counts as sleep for hours awake" in lims


def test_limitations_name_the_close_fix_wave(nut_host):
    lims = list(NUT(nut_host).limitations.values())
    # the vitamin D sun term ships 0: clinical at zero intake in ln(1/0.17)/(ln2/60) = 153.4 d, /30 = 5.1 d
    k = math.log(2) / 60
    assert abs(math.log(1 / 0.17) / k - 153.4) < 0.05 and abs(math.log(1 / 0.17) / k / 30 - 5.1) < 0.05
    assert "vitamin D has no cutaneous term (kSun 0, S1064 open): every character trends to its dietary steady state (clinical in ~153 d at zero intake; ~5 d at OnsetSpeed 30)" in lims
    assert "SleepAllowed/SleepNeeded are read once at OnServerStarted; a runtime change of the server options is not followed" in lims
    assert "the first Nutrients minute on a new record integrates no time (its absorbed vector is dropped; Metabolism already credited it) and also drops that minute's absorbed water" in lims
    assert "the fat factor reads the stomach buffer's lipids before each minute's emptying (ruling T19-1): it eases as the meal empties, so a 30 g-fat meal absorbs 90 % of its retinol and vitK and three 10 g-fat meals a day 81 %" in lims
    assert not any("the ingested vector is empty" in x for x in lims)   # the stale Task 12 string is gone


def test_niacin_takes_the_tryptophan_credit(nut_host):
    # ruling T19-2 (S0270): 80 g protein x 1000 x 0.011 / 60 = 14.6667 mg NE
    h = nut_host
    p = player(h)
    record = fresh(h, p)
    ab = vec(h, proteins=80.0, niacin=2.0)
    alone(h, p, record, 100.0 + 1 / 60, handed(h, ab))
    assert abs(80 * 1000 * 0.011 / 60 - 14.666666666666666) < 1e-12
    assert abs(ab["niacin"] - (2.0 + 80 * 1000 * 0.011 / 60)) < TOL


def test_choline_takes_the_female_rate(nut_host):
    # ruling T19-3: kMul.choline = kFemale (0.57) on a female body, 1 on a male; thiamine's term unchanged
    h = nut_host
    thia = h.K.interact.thiamineAlcoholK(1, 0)
    fem = player(h, female=True)
    record = fresh(h, fem)
    assert record["body"]["sex"] == 2
    alone(h, fem, record, 100.0 + 1 / 60)
    assert NUT(h).kMul.choline == 0.57
    assert NUT(h).kMul.thiamine == thia
    male = player(h)
    record = fresh(h, male)
    alone(h, male, record, 100.0 + 1 / 60)
    assert NUT(h).kMul.choline == 1
    assert NUT(h).kMul.thiamine == thia


# --- the heal --------------------------------------------------------------------------------------------

def test_non_finite_stamps_are_healed_and_counted(nut_host):
    h = nut_host
    p = player(h)
    record = fresh(h, p)
    alone(h, p, record, 100.0 + 1 / 60)
    n, f, a = record["nutrients"], record["fluids"], record["acute"]
    assert n["iron"]["S"] is not None
    healed = NUT(h).stats.healed
    f["water"] = NAN
    a["bac"] = NAN
    a["winStartH"] = NAN
    n["vitC"]["p"] = NAN
    n["iron"]["S"] = NAN
    n["epoch"] = NAN
    alone(h, p, record, 100.0 + 2 / 60)
    assert nonfinite(h, record) == ""
    assert NUT(h).stats.healed == healed + 1
    names = str(NUT(h).lastHealed)
    for name in ("fluids.water", "acute.bac", "acute.winStartH", "nutrients.vitC.p", "nutrients.iron.S",
                 "nutrients.epoch"):
        assert name in names, name
    assert abs(a["winStartH"] - (100.0 + 2 / 60)) < TOL     # an age field heals to the world age
    assert n["iron"]["S"] is not None                       # cleared, then re-laid by K.interact.two
    n["lastAgeH"] = NAN                                     # a healed clock skips that minute (dtM 0)
    played = NUT(h).stats.players
    alone(h, p, record, 100.0 + 3 / 60)
    assert NUT(h).stats.players == played


def test_missing_added_fields_are_backfilled(nut_host):
    h = nut_host
    p = player(h)
    record = fresh(h, p)
    record["nutrients"]["lastDayIndex"] = None
    record["fluids"]["viewPct"] = None
    record["acute"]["alc7"] = None
    record["acute"]["alcDayG"] = None
    record["acute"]["lastFedAgeH"] = None
    record["acute"]["lastB1"] = None
    record["acute"]["lastB2"] = None
    record["body"]["band1Day"] = 12.0                       # a day already exercised before the first minute
    record["body"]["band2Day"] = 4.0
    alone(h, p, record, 100.0 + 1 / 60)
    assert record["nutrients"]["lastDayIndex"] == 4
    assert record["acute"]["alc7"] == 0
    assert (record["acute"]["lastB1"], record["acute"]["lastB2"]) == (12.0, 4.0)   # the baselines start at the accumulators
    assert nonfinite(h, record) == ""


# --- the options -----------------------------------------------------------------------------------------

@pytest.mark.parametrize("v, want", [(7.5, 7.5), (45.0, 30.0), (0.1, 0.5), (NAN, 1.0), ("x", 1.0),
                                     (None, 1.0), (1.0, 1.0)])
def test_onset_speed_is_read_and_clamped(nut_host, v, want):
    h = nut_host
    nr = {} if v is None else {"OnsetSpeed": v}
    O = h.rt.eval(READ)(h.table(nr))
    try:
        assert O.onsetSpeed == want
    finally:
        h.rt.eval(READ)(h.table({}))


@pytest.mark.parametrize("key, field", [("DeficienciesCanKill", "deficienciesCanKill"),
                                        ("ExcessEffectsOn", "excessEffectsOn"), ("BalanceBonus", "balanceBonus")])
def test_the_boolean_dials(nut_host, key, field):
    h = nut_host
    try:
        assert h.rt.eval(READ)(h.table({}))[field] is True
        assert h.rt.eval(READ)(h.table({key: False}))[field] is False
        assert h.rt.eval(READ)(h.table({key: "false"}))[field] is True   # a non-boolean reads the default
    finally:
        h.rt.eval(READ)(h.table({}))


def test_a_dial_change_fires_the_changed_hooks(nut_host):
    h = nut_host
    O = h.G.NutritionRevamp.server.options
    h.rt.execute("NR_TEST_CHANGED = nil")
    hook = h.rt.eval("function(old, new) NR_TEST_CHANGED = old.onsetSpeed end")
    O.changed[len(O.changed) + 1] = hook
    try:
        h.rt.eval(READ)(h.table({"OnsetSpeed": 3.0}))
        assert h.G.NR_TEST_CHANGED == 1.0
    finally:
        O.changed[len(O.changed)] = None
        h.rt.eval(READ)(h.table({}))


def test_the_dial_reaches_the_slow_records(nut_host):
    h = nut_host
    p = player(h)
    slow = fresh(h, p)
    fast = fresh(h, p)
    alone(h, p, slow, 100.0 + 1)
    h.rt.eval(READ)(h.table({"OnsetSpeed": 30.0}))
    try:
        alone(h, p, fast, 100.0 + 1)
    finally:
        h.rt.eval(READ)(h.table({}))
    assert fast["nutrients"]["vitB12"]["p"] < slow["nutrients"]["vitB12"]["p"]   # dialled (ruling 5)
    assert fast["nutrients"]["vitC"]["p"] == slow["nutrients"]["vitC"]["p"]      # never dialled


def test_the_option_file_and_translations_declare_the_four_dials():
    import json
    path = os.path.join(REPO, "mod", "NutritionRevamp", "42.20.4", "media", "sandbox-options.txt")
    with open(path, encoding="utf-8") as fh:
        src = fh.read()
    assert "option NR.OnsetSpeed\n{\n    type = double, min = 0.5, max = 30.0, default = 1.0," in src
    for name in ("DeficienciesCanKill", "ExcessEffectsOn", "BalanceBonus"):
        assert "option NR.%s\n{\n    type = boolean, default = true,\n    page = NutritionRevamp, translation = NR_%s,\n}" % (name, name) in src
    with open(os.path.join(SHARED, "Translate", "EN", "Sandbox.json"), encoding="utf-8") as fh:
        tr = json.load(fh)
    for name in ("OnsetSpeed", "DeficienciesCanKill", "ExcessEffectsOn", "BalanceBonus"):
        assert tr["Sandbox_NR_" + name]
        assert tr["Sandbox_NR_" + name + "_tooltip"]


def test_the_option_file_and_translations_declare_severity():
    # Plan 5 ruling 23: NR.Severity, a double 0-3, default 1 (read and clamped: test_effects_shape.py)
    import json
    path = os.path.join(REPO, "mod", "NutritionRevamp", "42.20.4", "media", "sandbox-options.txt")
    with open(path, encoding="utf-8") as fh:
        src = fh.read()
    assert ("option NR.Severity\n{\n    type = double, min = 0.0, max = 3.0, default = 1.0,\n"
            "    page = NutritionRevamp, translation = NR_Severity,\n}") in src
    with open(os.path.join(SHARED, "Translate", "EN", "Sandbox.json"), encoding="utf-8") as fh:
        tr = json.load(fh)
    assert tr["Sandbox_NR_Severity"] and tr["Sandbox_NR_Severity_tooltip"]


# --- the effects hand-off (Plan 5 ruling 22, made explicit by the pipeline in Plan 10 R2) ------------------
# The Effects step itself, its guard and its effectsErrors counter: test_minute_pipeline.py.

def test_the_minute_ends_by_stamping_the_effects_inputs_on_the_context(nut_host):
    h = nut_host
    p = player(h)
    record = fresh(h, p)
    played = NUT(h).stats.players
    pipe = h.rt.table()
    alone(h, p, record, 100.0 + 2 / 60, pipe)
    same = h.rt.eval("rawequal")
    assert same(pipe.body, record["body"])
    assert abs(pipe.dtM - 2.0) < 1e-9 and abs(pipe.ageH - (100.0 + 2 / 60)) < TOL
    assert NUT(h).stats.players == played + 1
    pipe = h.rt.table()
    alone(h, p, record, 100.0 + 2 / 60, pipe)                     # dtM 0: no minute, no stamp, no effects step
    assert pipe.body is None and pipe.dtM is None and pipe.ageH is None


def test_a_minute_with_no_context_stamps_every_record_table(nut_host):
    h = nut_host
    p = player(h)
    record = fresh(h, p)
    errors = NUT(h).stats.errors
    alone(h, p, record, 100.0 + 1 / 60)
    assert NUT(h).stats.errors == errors
    assert abs(record["nutrients"]["lastAgeH"] - (100.0 + 1 / 60)) < TOL


SLEEP_SPY = r"""
function()
    local K = NutritionRevamp.kernel
    local orig = K.acute.sleepMinute
    NR_TEST_SLEEP_ARGS = nil
    K.acute.sleepMinute = function(a, asleep, hod, nf, ageH, dtH, sd, mAcc, rRec)
        NR_TEST_SLEEP_ARGS = { mAcc = mAcc, rRec = rRec }
        return orig(a, asleep, hod, nf, ageH, dtH, sd, mAcc, rRec)
    end
    return orig
end
"""


@pytest.mark.parametrize("m, r, want_m, want_r", [(1.4, 0.8, 1.4, 0.8), (NAN, 0.0, None, None),
                                                  (None, None, None, None)])
def test_the_sleep_step_reads_last_minutes_multipliers(nut_host, m, r, want_m, want_r):
    h = nut_host
    p = player(h)
    record = fresh(h, p)
    if m is not None:
        record["effects"] = h.table({"mAcc": m, "rRec": r})
    orig = h.rt.eval(SLEEP_SPY)()
    try:
        alone(h, p, record, 100.0 + 1 / 60)
        args = h.G.NR_TEST_SLEEP_ARGS
        assert args["mAcc"] == want_m and args["rRec"] == want_r
    finally:
        h.K.acute.sleepMinute = orig


# --- the wiring order ---------------------------------------------------------------------------------

def test_nutrients_runs_after_metabolism_and_before_strength():
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
    names = sorted(["NR_Server_Weight.lua", "NR_Server_Training.lua", "NR_Server_Strength.lua",
                    "NR_Server_Metabolism.lua", "NR_Server_Kinetics.lua", "NR_Server_Nutrients.lua",
                    "NR_Server_Minute.lua"])
    assert names == ["NR_Server_Kinetics.lua", "NR_Server_Metabolism.lua", "NR_Server_Minute.lua",
                     "NR_Server_Nutrients.lua", "NR_Server_Strength.lua", "NR_Server_Training.lua",
                     "NR_Server_Weight.lua"]
    for n in names:
        with open(os.path.join(SERVER, n), encoding="utf-8") as fh:
            load(fh.read(), "@" + n)()
    rt.execute("for i = 1, #NR_STARTED do NR_STARTED[i]() end")
    rt.execute("for i = 1, #NR_STARTED do NR_STARTED[i]() end")   # a second start wires nothing twice
    G = rt.globals()
    S = G.NutritionRevamp.server
    same = rt.eval("rawequal")
    for name in ("kinetics", "metabolism", "nutrients", "strength", "weight"):
        assert same(S.minute.steps[name], S[name].minute), name
    order = [S.minute.ORDER[i] for i in range(1, len(S.minute.ORDER) + 1)]
    assert [n for n in order if n in ("kinetics", "metabolism", "nutrients", "strength", "weight")] ==         ["kinetics", "metabolism", "nutrients", "strength", "weight"]
    assert S.nutrients.wired is True
    assert S.nutrients.sleepDisabled is False               # no getServerOptions: not disabled


def test_the_file_loads_with_no_engine_and_names_no_stat_write():
    with open(os.path.join(SERVER, "NR_Server_Nutrients.lua"), encoding="utf-8") as fh:
        src = fh.read()
    for name in ("CharacterStat", ":set(", '"set"', "setHealth", "ReduceGeneralHealth", "getMoodles"):
        assert name not in src, name
