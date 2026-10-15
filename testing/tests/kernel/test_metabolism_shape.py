"""NR_Server_Metabolism, driven end to end through table-of-functions Java stand-ins.

The file is a server/ file the kernel host does not load, so it is loaded on top of the session host
the way test_kinetics.py loads NR_Server_Kinetics.lua. NR.call indexes obj[name] and calls it with obj
first, so a Lua table of function fields stands in for a Java object (test_intake_shape.py:612). Every
world age, rate and flag is stubbed by hand; the kernel math is the real kernel. A stub proves the
wiring, the order and the guards, not the engine's real getters, which the live acceptance runs read.
"""
import glob
import math
import os
import re

import lupa.lua51 as lua51
import pytest

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
SERVER = os.path.join(REPO, "mod", "NutritionRevamp", "common", "media", "lua", "server")
SHARED = os.path.join(REPO, "mod", "NutritionRevamp", "common", "media", "lua", "shared")
METABOLISM = os.path.join(SERVER, "NR_Server_Metabolism.lua")
KINETICS = os.path.join(SERVER, "NR_Server_Kinetics.lua")
INTAKE = os.path.join(SERVER, "NR_Server_Intake.lua")
CORE = os.path.join(SHARED, "NR_Core.lua")
TOL = 1e-9

# The Java globals the adapter names, stubbed; the previous values are returned so the teardown puts
# them back and nothing leaks into a later module.
SETUP = r"""
function(age)
    local names = { "getGameTime", "CharacterTrait", "Perks", "MoodleType", "BodyPartType",
                    "SwipeStatePlayer", "ZombRandFloat", "ClimbOverFenceState", "ClimbThroughWindowState" }
    local saved = { age = NR_TEST_AGE, tod = NR_TEST_TOD, rand = NR_TEST_RAND, names = names, vals = {} }
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
                       STRONG = "STRONG", STOUT = "STOUT", FEEBLE = "FEEBLE", WEAK = "WEAK", OBESE = "OBESE",
                       OVERWEIGHT = "OVERWEIGHT", UNDERWEIGHT = "UNDERWEIGHT", VERY_UNDERWEIGHT = "VERY_UNDERWEIGHT",
                       EMACIATED = "EMACIATED" }
    Perks = { Strength = "Strength" }
    MoodleType = { HEAVY_LOAD = "HEAVY_LOAD", HYPERTHERMIA = "HYPERTHERMIA" }
    BodyPartType = { UpperLeg_L = "UpperLeg_L", UpperLeg_R = "UpperLeg_R", LowerLeg_L = "LowerLeg_L",
                     LowerLeg_R = "LowerLeg_R" }
    SwipeStatePlayer = { instance = function() return "SWIPE" end }
    ClimbOverFenceState = { instance = function() return "FENCE" end }
    ClimbThroughWindowState = { instance = function() return "WINDOW" end }
    ZombRandFloat = function(a, b) return NR_TEST_RAND end
    return saved
end
"""

TEARDOWN = r"""
function(saved)
    NR_TEST_AGE, NR_TEST_TOD, NR_TEST_RAND = saved.age, saved.tod, saved.rand
    for i = 1, #saved.names do _G[saved.names[i]] = saved.vals[i] end
end
"""

# A player stand-in reading its every answer from cfg, which a case mutates between minutes.
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
    p.getPerkLevel = function(self, perk) return self.cfg.strength end
    p.getMaxWeightDelta = function(self) return self.cfg.delta end
    p.getBodyDamage = function(self)
        if self.cfg.noBodyDamage then return nil end
        local thermo = {
            getMetabolicRate = function(t) return self.cfg.rate end,
            getEnergyMultiplier = function(t) return self.cfg.cold end,
        }
        return {
            getThermoregulator = function(s) return thermo end,
            getBodyPart = function(s, part)
                return {
                    getFractureTime = function(b) return self.cfg.fracture[part] or 0 end,
                    isSplint = function(b) return self.cfg.splint[part] == true end,
                }
            end,
        }
    end
    p.getInventoryWeight = function(self) return self.cfg.carried end
    p.getMaxWeight = function(self) return self.cfg.maxW end
    p.isPlayerMoving = function(self) return self.cfg.moving == true end
    p.isAsleep = function(self) return self.cfg.asleep == true end
    p.getMoodles = function(self)
        return { getMoodleLevel = function(s, m) return self.cfg.moodles[m] or 0 end }
    end
    p.getFitness = function(self)
        return { getCurrentExe = function(s) return self.cfg.exe end }
    end
    p.isCurrentState = function(self, st)
        return (self.cfg.swiping == true and st == "SWIPE") or (self.cfg.climb ~= nil and st == self.cfg.climb)
    end
    return p
end
"""

MINUTE = r"""
function(player, record, age, pipe)
    NR_TEST_AGE = age
    NutritionRevamp.server.metabolism.minute("admin", player, record, pipe)
    return record
end
"""

RAISING = r"""
function(player, record, age)
    local K = NutritionRevamp.kernel
    local orig = K.energy.minute
    K.energy.minute = function() error("boom") end
    NR_TEST_AGE = age
    local ok, err = pcall(NutritionRevamp.server.metabolism.minute, "admin", player, record)
    K.energy.minute = orig
    return ok, err
end
"""

NONFINITE = r"""
function(record)
    -- every number on the body, rings included, is finite
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
    walk(record.body, "body")
    return table.concat(bad, ",")
end
"""

NAN = float("nan")


def _load(host, path, name):
    with open(path, encoding="utf-8") as fh:
        src = fh.read()
    host.rt.eval("function(src, name) return assert(loadstring(src, name)) end")(src, name)()


@pytest.fixture(scope="module")
def met_host(host):
    # the intake loads before Kinetics in the game, and the handoff table lives on NR.server.kinetics: both load
    # here when this module runs alone.
    if host.G.NutritionRevamp.server.intake is None:
        _load(host, INTAKE, "@NR_Server_Intake.lua")
    if host.G.NutritionRevamp.server.kinetics is None:
        _load(host, KINETICS, "@NR_Server_Kinetics.lua")
    _load(host, METABOLISM, "@NR_Server_Metabolism.lua")
    saved = host.rt.eval(SETUP)(100.0)
    try:
        yield host
    finally:
        host.rt.eval(TEARDOWN)(saved)


def MET(h):
    return h.G.NutritionRevamp.server.metabolism


def KIN(h):
    return h.G.NutritionRevamp.server.kinetics


def cfg(h, **kw):
    base = dict(weight=80.0, female=False, traits={}, strength=5, delta=1.0, rate=3.1, cold=1.0,
                fracture={}, splint={}, carried=0.0, maxW=20, moving=True, asleep=False, moodles={},
                exe=None, swiping=False, noBodyDamage=False, climb=None)
    base.update(kw)
    return h.table(base)


def player(h, **kw):
    return h.rt.eval(PLAYER)(cfg(h, **kw))


def minute(h, p, record, age, pipe=None):
    return h.rt.eval(MINUTE)(p, record, age, pipe)


def nonfinite(h, record):
    return h.rt.eval(NONFINITE)(record)


def fresh(h, p, age=100.0):
    record = h.rt.table()
    minute(h, p, record, age)
    return record


def seed(h, body, hour=99, **amounts):
    """Plan 11d Task 9c: lays amounts (kcal, ee, ex, p, carb, lip) in game hour `hour` of the trailing-24 h window (99:
    the closed hour before a fresh record's hour 100, inside the window whole) and marks the closed sums for a rebuild."""
    t = body["trail"]
    s = h.K.body.trailSlot(hour)
    for k, v in amounts.items():
        t[k][s] = v
    t.ch = -1


# --- first sight --------------------------------------------------------------------------------------

def D(h):
    return h.K.strength.DEFAULTS


def spec(h, muscle=None, weight=None, sex_idx=1):
    return h.py(h.K.body.create(muscle, weight, D(h), sex_idx))


def test_first_sight_builds_the_no_trait_body(met_host):
    # Plan 13 Task 12 (ruling 13-6): a character holding no band trait is the no-trait creation body, whatever its
    # native weight; body.levelDue asks the Strength minute to write the level once
    h = met_host
    creates = MET(h).stats.creates
    record = fresh(h, player(h, weight=95.0))
    body = record["body"]
    want = spec(h)
    for k in ("lm", "F0", "Fc", "Pk", "N0", "fm", "fatT", "thinT"):
        assert body[k] == want[k], k
    assert body["levelDue"] is True and body["S"] == 0 and body["lx"] == 0
    assert body["band"] == "normal"
    assert body["sex"] == 1 and abs(body["lastAgeH"] - 100.0) < TOL and body["dayIndex"] == 4
    assert MET(h).stats.creates == creates + 1 and MET(h).stats.splits is None
    assert body["eeDay"] == 0                  # dtM is 0 on the first minute
    for k in ("fm0", "lm0", "l0", "r", "traitCarry", "strAgeH", "shownL", "n", "vStr", "delta"):
        assert body[k] is None, k
    assert nonfinite(h, record) == ""


def test_first_sight_with_strong_and_obese_builds_strongs_f0_and_obeses_fat(met_host):
    # the brief: the held muscle and weight band traits are the creation picks (ruling 13-6)
    h = met_host
    body = fresh(h, player(h, traits={"STRONG": True, "OBESE": True}))["body"]
    want = spec(h, "STRONG", "OBESE")
    assert body["F0"] == want["F0"] and body["fm"] == want["fm"]
    assert body["F0"] != spec(h)["F0"] and body["fm"] != spec(h)["fm"]
    assert body["N0"] == D(h).N0["STRONG"] and body["fatT"] == 2 and body["band"] == "obese"


@pytest.mark.parametrize("traits, muscle, weight", [
    ({"FEEBLE": True}, "FEEBLE", None),
    ({"WEAK": True, "OVERWEIGHT": True}, "WEAK", "OVERWEIGHT"),
    ({"STOUT": True, "UNDERWEIGHT": True}, "STOUT", "UNDERWEIGHT"),
    ({"EMACIATED": True}, None, "VERY_UNDERWEIGHT"),                # Emaciated reads as Very Underweight
    ({"ATHLETIC": True, "FIT": True}, None, None),                  # a fitness trait is no band pick
])
def test_first_sight_reads_the_held_band_traits_never_the_native_level(met_host, traits, muscle, weight):
    h = met_host
    for strength in (0, 5, 10):                # the native level never moves the body
        body = fresh(h, player(h, traits=traits, strength=strength, weight=60.0 + 10 * strength))["body"]
        want = spec(h, muscle, weight)
        for k in ("lm", "F0", "Fc", "Pk", "N0", "fm", "fatT", "thinT"):
            assert body[k] == want[k], (traits, strength, k)


GUARDED_PLAYER = r"""
function(p, C)
    p.getPerkLevel = function(self) C.perk = C.perk + 1; return 9 end
    p.getMaxWeightDelta = function(self) C.delta = C.delta + 1; return 1.5 end
    local nut = p.getNutrition
    p.getNutrition = function(self) C.nutrition = C.nutrition + 1; return nut(self) end
    return p
end
"""


def test_ensure_body_reads_no_carry_delta_no_perk_level_and_no_weight(met_host):
    # the brief: ensureBody no longer reads getMaxWeightDelta or getPerkLevel (ruling 13-7: the carry is the band's);
    # the weight read went with the split
    h = met_host
    C = h.rt.eval("{ perk = 0, delta = 0, nutrition = 0 }")
    p = h.rt.eval(GUARDED_PLAYER)(player(h, traits={"STOUT": True}), C)
    record = h.rt.table()
    MET(h).ensureBody("admin", p, record, 100.0)
    assert record["body"]["N0"] == D(h).N0["STOUT"]
    assert (C.perk, C.delta, C.nutrition) == (0, 0, 0)
    record2 = fresh(h, p)
    minute(h, p, record2, 100.0 + 1 / 60)
    assert (C.perk, C.delta) == (0, 0)         # nor does the minute or its heal


def test_a_female_first_sight_builds_the_male_body_unless_sex_specific_is_on(met_host):
    # Plan 13 Task 3 fix 1: the creation body reads the effective sex; body.sex keeps the engine's value
    h = met_host
    traits = {"OVERWEIGHT": True}
    nr = h.G.NutritionRevamp.server
    made = nr.options is None
    if made:
        nr.options = h.rt.table()
    opts = nr.options
    saved = opts.sexSpecific
    try:
        opts.sexSpecific = False
        off = fresh(h, player(h, female=True, traits=traits, weight=62.0))["body"]
        male = fresh(h, player(h, traits=traits, weight=62.0))["body"]
        assert off["sex"] == 2 and male["sex"] == 1
        assert off["fm"] == male["fm"] and off["lm"] == male["lm"]
        opts.sexSpecific = True
        on = fresh(h, player(h, female=True, traits=traits, weight=62.0))["body"]
    finally:
        opts.sexSpecific = saved
        if made:
            nr.options = None
    want = spec(h, None, "OVERWEIGHT", 2)
    assert on["sex"] == 2 and on["fm"] == want["fm"] and on["lm"] == want["lm"]
    assert on["fm"] != off["fm"] and off["fm"] == spec(h, None, "OVERWEIGHT", 1)["fm"]


def test_first_sight_defaults_when_every_getter_is_absent(met_host):
    h = met_host
    record = fresh(h, h.rt.table())            # a player with no members at all: male, no band trait held
    body = record["body"]
    want = spec(h)
    assert body["fm"] == want["fm"] and body["lm"] == want["lm"] and body["sex"] == 1
    assert nonfinite(h, record) == ""


# --- the minute -----------------------------------------------------------------------------------------

def test_second_minute_bills_expenditure_and_banks_met_minutes(met_host):
    h = met_host
    p = player(h)
    record = fresh(h, p)
    minute(h, p, record, 100.0 + 1 / 60)
    body = record["body"]
    assert body["eeDay"] > 0
    assert body["actKcalDay"] > 0
    assert body["metMinDay"] > 0               # engine 3.1 (Walking5kmh) above the 1.5 floor
    assert body["ebDay"] < 0
    es = body["energyState"]
    assert es == es and 0.5 <= es <= 2.0
    assert abs(body["lastAgeH"] - (100.0 + 1 / 60)) < TOL
    assert body["band1Day"] == 0               # 3.1 is under the 6.0 band
    assert nonfinite(h, record) == ""


def test_minute_dt_is_clamped_to_an_hour(met_host):
    h = met_host
    p = player(h, moving=False, rate=1.5)      # idle Default, billed at its Compendium MET
    record = fresh(h, p)
    body = record["body"]
    body.lx = 1.25                             # the body mass the bill reads is fm + lm + lx (ruling 13-20)
    mass = body["fm"] + body["lm"] + 1.25
    minute(h, p, record, 100.0 + 5.0)          # five hours later: billed as 60 minutes
    ree = h.K.energy.ree(body["lm"])
    act = max(h.K.energy.activityMet("Default", False, 1, 0) - 1.0, 0) * mass
    assert abs(body["actKcalDay"] - act) < 1e-6
    assert abs(body["eeDay"] - (ree / 1440 * 60 + act)) < 1e-6


def test_lastabsorbed_is_read_not_cleared(met_host):
    # Plan 4 ruling 17: Metabolism reads the handoff's macros and leaves it for NR_Server_Nutrients, which
    # runs after it on the same minute (test_nutrients_shape.py); the handoff rides the pipeline's context
    # (Plan 10 R2), cleared at the start of each player's run, so a fresh context stands in for that here
    h = met_host
    p = player(h)
    record = fresh(h, p)
    vec = h.K.vector.new()
    vec.calories = 500
    vec.proteins = 20
    pipe = h.rt.table()
    pipe.absorbed = vec
    minute(h, p, record, 100.0 + 1 / 60, pipe)
    assert abs(record["body"]["inDay"] - 500) < TOL
    assert abs(record["body"]["pDay"] - 20) < TOL
    assert pipe.absorbed is not None
    minute(h, p, record, 100.0 + 2 / 60, h.rt.table())
    assert abs(record["body"]["inDay"] - 500) < TOL


def test_kinetics_hands_off_the_absorbed_vector(met_host):
    h = met_host
    K = h.K
    record = h.rt.table()
    record.stomach = K.stomach.new()
    record.stomach.buffer.calories = 400
    record.pool = K.vector.new()
    pipe = h.rt.table()                        # the pipeline's context (Plan 10 R2)
    h.G.NR_TEST_AGE = 100.0
    KIN(h).minute("admin", None, record, pipe)       # first step: dtH 0
    assert pipe.absorbed is None
    h.G.NR_TEST_AGE = 101.0
    pipe.eAge = None                                 # NR_Server_Minute.run clears the context per minute (NR.read's age)
    KIN(h).minute("admin", None, record, pipe)
    handed = pipe.absorbed
    assert handed is not None and handed["calories"] > 0
    assert abs(handed["calories"] - record["pool"]["calories"]) < TOL
    KIN(h).minute("admin", None, record, pipe)       # same age (the context unchanged): dtH 0 clears it
    assert pipe.absorbed is None


# --- the activity read (ruling T5-2) ----------------------------------------------------------------

def _activity(h, p):
    r = MET(h).readActivity(p)
    return dict(className=r[0], moving=r[1], modifier=r[2], loadKg=r[3], heavyLevel=r[4], coldMult=r[5],
                exercising=r[6], swiping=r[7], immobilised=r[8], hourOfDay=r[9], maxW=r[10], climbClass=r[11])


def test_read_activity_classifies_the_rate(met_host):
    h = met_host
    a = _activity(h, player(h))
    assert a["className"] == "Walking5kmh"
    assert a["moving"] is True and a["modifier"] == 1
    assert a["loadKg"] == 0 and a["maxW"] == 20
    assert a["heavyLevel"] == 0 and a["coldMult"] == 1
    assert a["exercising"] is False and a["swiping"] is False and a["immobilised"] is False


def test_read_activity_strips_the_engine_load_factor(met_host):
    h = met_host
    loaded = 3.1 * (1 + 0.35 * 0.5 * 0.5)      # half the max carried: the engine's factor on Walking5kmh
    a = _activity(h, player(h, rate=loaded, carried=10.0, maxW=20))
    assert a["className"] == "Walking5kmh"
    assert a["loadKg"] == 10.0


def test_read_activity_sleeping_wins(met_host):
    h = met_host
    assert _activity(h, player(h, asleep=True, rate=3.1))["className"] == "Sleeping"


@pytest.mark.parametrize("rate", [NAN, None, float("inf")])
def test_bad_rate_reads_default_and_counts(met_host, rate):
    h = met_host
    before = MET(h).stats.badReads
    a = _activity(h, player(h, rate=rate))
    assert a["className"] == "Default"
    assert MET(h).stats.badReads == before + 1


def test_absent_body_damage_reads_default_and_counts(met_host):
    h = met_host
    before = MET(h).stats.badReads
    a = _activity(h, player(h, noBodyDamage=True))
    assert a["className"] == "Default"
    assert a["immobilised"] is False and a["coldMult"] == 1
    assert MET(h).stats.badReads == before + 1


def test_nan_rate_minute_leaves_no_nan_on_the_record(met_host):
    h = met_host
    p = player(h, rate=NAN)
    record = fresh(h, p)
    minute(h, p, record, 100.0 + 1 / 60)
    assert nonfinite(h, record) == ""
    assert record["body"]["eeDay"] > 0


def test_read_activity_flags_and_moodles(met_host):
    h = met_host
    a = _activity(h, player(h, exe="squats", swiping=True, moodles={"HEAVY_LOAD": 7, "HYPERTHERMIA": 2},
                            cold=2.5, fracture={"LowerLeg_R": 30.0}))
    assert a["exercising"] is True and a["swiping"] is True
    assert a["heavyLevel"] == 4                # clamped 0-4
    assert "heatLevel" not in a                # the hyperthermia level fed only the drain coefficient, now gone
    assert a["coldMult"] == 2.5
    assert a["immobilised"] is True
    assert _activity(h, player(h, splint={"UpperLeg_L": True}))["immobilised"] is True


def test_read_activity_hour_of_day(met_host):
    h = met_host
    h.G.NR_TEST_TOD = 7.5
    try:
        assert _activity(h, player(h))["hourOfDay"] == 7.5
    finally:
        h.G.NR_TEST_TOD = None


# --- the day close -------------------------------------------------------------------------------------

def online(h, p, record, age):
    """The minute at world age `age` after an hour online: body.lastAgeH set one hour back, so the step is 60 game
    minutes, at the gap threshold and not over it (ruling 13-5: a step over 60 minutes is a return after a gap)."""
    record["body"].lastAgeH = age - 1.0
    return minute(h, p, record, age)


def test_an_online_world_day_boundary_closes_one_day(met_host):
    h = met_host
    p = player(h)
    record = fresh(h, p, 100.0)                # dayIndex 4, wday 4
    days = MET(h).stats.days
    online(h, p, record, 124.0)
    body = record["body"]
    assert body["dayIndex"] == 5 and body["wday"] == 5
    assert MET(h).stats.days == days + 1
    assert body["eeDay"] == 0 and body["inDay"] == 0  # the day accumulators closed
    assert body["eb7"][7] < 0                  # the closed day's balance: an hour of expenditure
    assert nonfinite(h, record) == ""


def test_a_day_close_stamps_the_level_write(met_host):
    # Plan 13 Task 14: every close asks the Strength minute to write the day's level (spec section 7)
    h = met_host
    p = player(h)
    record = fresh(h, p, 100.0)
    record["body"].levelDue = False
    minute(h, p, record, 100.0 + 1 / 60)
    assert record["body"]["levelDue"] is False             # no close: no stamp
    online(h, p, record, 124.0)
    assert record["body"]["levelDue"] is True


def test_an_online_minute_closes_at_most_one_day(met_host):
    h = met_host
    p = player(h)
    record = fresh(h, p, 100.0)
    days = MET(h).stats.days
    online(h, p, record, 172.0)                # three world days on, inside an hour's step
    assert record["body"]["dayIndex"] == 5 and record["body"]["wday"] == 7
    assert MET(h).stats.days == days + 1
    minute(h, p, record, 172.0 + 1 / 60)
    assert record["body"]["dayIndex"] == 5 and MET(h).stats.days == days + 1


def test_the_catch_up_guard_and_its_counter_are_gone(met_host):
    h = met_host
    assert MET(h).MAX_CLOSES is None
    assert MET(h).stats.skippedDays is None
    with open(METABOLISM, encoding="utf-8") as fh:
        src = fh.read()
    assert "MAX_CLOSES" not in src and "skippedDays" not in src


def _ring(t):
    out = []
    for i in range(1, 8):
        v = t[i]
        out.append((v[1], v[2]) if not isinstance(v, (int, float)) else v)
    return out


def test_a_step_just_over_an_hour_across_midnight_is_a_gap(met_host):
    # the threshold pinned from above: 61 game minutes is a return after a gap, so it closes nothing (ruling 13-5)
    h = met_host
    p = player(h)
    record = fresh(h, p, 100.0)
    days = MET(h).stats.days
    record["body"].lastAgeH = 120.0 + 1 / 60 - 61 / 60
    minute(h, p, record, 120.0 + 1 / 60)
    body = record["body"]
    assert body["dayIndex"] == 4 and body["wday"] == 5
    assert MET(h).stats.days == days


def test_a_step_of_exactly_an_hour_across_midnight_closes_once(met_host):
    # and from below: 60 game minutes is online, so the world-day boundary closes the record day
    h = met_host
    p = player(h)
    record = fresh(h, p, 100.0)
    days = MET(h).stats.days
    record["body"].lastAgeH = 119.5
    minute(h, p, record, 120.5)
    body = record["body"]
    assert body["dayIndex"] == 5 and body["wday"] == 5
    assert MET(h).stats.days == days + 1


def test_a_return_after_three_days_changes_nothing_and_resumes_the_calendar(met_host):
    # ruling 13-5: the record calendar advances on online days only; a return re-stamps wday and closes nothing
    h = met_host
    p = player(h)
    record = fresh(h, p, 100.0)
    body = record["body"]
    online(h, p, record, 124.0)                # one online close, so the rings hold a closed day
    minute(h, p, record, 124.0 + 1 / 60)
    days = MET(h).stats.days
    keep = {"dayIndex": body["dayIndex"], "fm": body["fm"], "lm": body["lm"]}
    rings = {k: _ring(body[k]) for k in ("eb7", "p7", "mass7", "bandWeek")}
    minute(h, p, record, 124.0 + 1 / 60 + 72.0)   # away three game days: the return minute
    for k, v in keep.items():
        assert body[k] == v, k
    for k, v in rings.items():
        assert _ring(body[k]) == v, k
    assert MET(h).stats.days == days
    assert body["wday"] == 8                   # floor(196.0167 / 24): re-stamped to today's world day
    minute(h, p, record, 196.5)                # online through the rest of world day 8: nothing closes
    online(h, p, record, 199.0)
    assert body["dayIndex"] == keep["dayIndex"] and MET(h).stats.days == days
    online(h, p, record, 216.0 + 1 / 60)       # the next world-day boundary closes exactly one day
    assert body["dayIndex"] == keep["dayIndex"] + 1 and body["wday"] == 9
    assert MET(h).stats.days == days + 1
    assert nonfinite(h, record) == ""


def test_day_close_runs_the_partition_strength_and_tac(met_host):
    h = met_host
    p = player(h)
    record = fresh(h, p, 100.0)
    body = record["body"]
    fm0 = body["fm"]
    body.sigDay = 6 * D(h).xpPerSet            # today's six sets of Strength XP (ruling 13-12)
    for i in range(1, 8):
        body.bandWeek[i][1] = 60               # a full week of band-1 minutes: TAC rises
    online(h, p, record, 124.0)
    assert body["fm"] < fm0                    # an hour's deficit paid by fat
    assert body["S"] == 6.0 and body["sig7"][7] == 6 * D(h).xpPerSet and body["sigDay"] == 0
    assert body["T"] > 1.0                     # the neural factor rose on the week's sets
    assert body["tac"] > 1.0
    assert body["pPrevKg"] == 0                # no protein eaten on the closed day


def test_training_reaches_tac_at_the_same_close(met_host):
    # run x141c: the week was read before the training ring shifted the closing day in, so a day's
    # training reached TAC one close late; the training ring now closes first
    h = met_host
    p = player(h)
    record = fresh(h, p, 100.0)
    body = record["body"]
    body.band1Day = 300.0                      # the closing day's band-1 minutes; the ring is empty
    online(h, p, record, 124.0)
    assert body["bandWeek"][7][1] == 300.0
    assert body["band1Day"] == 0
    assert body["tac"] > 1.0                   # the same close saw the training


def test_close_order_training_ring_before_tac_and_at_after_the_ring():
    with open(METABOLISM, encoding="utf-8") as fh:
        src = fh.read()
    region = src[src.index("local function closeDay("):src.index("MET.stats.days = MET.stats.days + 1")]
    order = ["body.tDisuse = body.tDisuse + 1", "K.strength.signalClose(body)", "K.strength.disuseDay(",
             "K.strength.day(", "body.fmRef = K.max(body.fmRef, body.fm)",
             "K.traits.axes(", "body.S = S", "K.training.closeDay(body)", "K.training.weekMinutes(body)",
             "K.aerobic.tacDay(", "K.partition.closeDay(body)", "K.energy.atStep(",
             "K.partition.deficitWeek(body)"]
    at = [region.index(s) for s in order]
    assert at == sorted(at)
    assert "K.aerobic.gEnergy(body.inDay, body.exKcalDay, body.lm)" in region   # ruling W-1
    assert "actKcalDay" not in region
    assert re.search(r"K\.aerobic\.tacDay\(.*, immobilised\)", region)   # ruling W-2
    for gone in ("K.training.doses", "K.partition.day(", "K.strength.closeDay("):
        assert gone not in region, gone


SPY = r"""
function(player, record, age)
    local K = NutritionRevamp.kernel
    local origD, origG, origT = K.partition.deficitWeek, K.aerobic.gEnergy, K.aerobic.tacDay
    local seen = {}
    K.partition.deficitWeek = function(body)
        seen.ebDayAtAT = body.ebDay
        seen.eb7AtAT = body.eb7[7]
        return origD(body)
    end
    K.aerobic.gEnergy = function(inDay, ex, lm)
        seen.gInDay, seen.gEx = inDay, ex
        return origG(inDay, ex, lm)
    end
    K.aerobic.tacDay = function(...)
        seen.immobilised = select(9, ...)
        return origT(...)
    end
    record.body.lastAgeH = age - 1                 -- an hour online: the step closes the day (ruling 13-5)
    NR_TEST_AGE = age
    local ok, err = pcall(NutritionRevamp.server.metabolism.minute, "admin", player, record)
    K.partition.deficitWeek, K.aerobic.gEnergy, K.aerobic.tacDay = origD, origG, origT
    seen.ok = ok
    return seen
end
"""


def test_at_reads_a_week_that_includes_today(met_host):
    # whole-pass issue 8: deficitWeek was read before the partition ring pushed today, a one-close lag
    h = met_host
    p = player(h)
    record = fresh(h, p, 100.0)
    seen = h.rt.eval(SPY)(p, record, 124.0)
    assert seen.ok is True
    assert seen.ebDayAtAT == 0                 # the ring has closed the day
    assert seen.eb7AtAT < 0                    # and today's deficit is in the week AT reads
    assert record["body"]["at"] > 0            # one deficit day adapts at the first close


def test_tac_reads_exercise_kcal_and_the_immobilised_flag(met_host):
    h = met_host
    p = player(h, moving=False, rate=1.5)      # an idle minute: activity kcal but no exercise kcal
    record = fresh(h, p, 100.0)
    body = record["body"]
    body.inDay = 2000.0
    body.actKcalDay = 900.0
    body.exKcalDay = 120.0
    seen = h.rt.eval(SPY)(p, record, 124.0)
    assert seen.gInDay == 2000.0 and seen.gEx == 120.0  # not actKcalDay (ruling W-1)
    assert seen.immobilised is False
    assert body["exKcalDay"] == 0              # the partition ring zeroes it
    q = player(h, fracture={"LowerLeg_R": 30.0})
    record2 = fresh(h, q, 100.0)
    seen2 = h.rt.eval(SPY)(q, record2, 124.0)
    assert seen2.immobilised is True
    assert record2["body"]["tac"] < 1.0        # immobilisation detrains below parity (ruling W-2)


def test_immobilised_days_run_disuse(met_host):
    h = met_host
    p = player(h, fracture={"UpperLeg_L": 40.0})
    record = fresh(h, p, 100.0)
    body = record["body"]
    lm = body["lm"]
    body.lm0dis = 1.0                          # proves the 0 -> 1 stamp overwrites it
    online(h, p, record, 124.0)
    assert body["tDisuse"] == 1
    assert abs(body["lm0dis"] - lm) < TOL
    assert body["lm"] < lm
    lm1 = body["lm"]
    online(h, p, record, 148.0)
    assert body["tDisuse"] == 2
    assert abs(body["lm0dis"] - lm) < TOL      # stamped once
    assert body["lm"] < lm1
    p.cfg.fracture = h.table({})
    online(h, p, record, 172.0)
    assert body["tDisuse"] == 0


# --- the lean-mass day close (Plan 13 Task 12) ------------------------------------------------------------------------
# A spy wraps the kernel functions the close calls, counts each call and keeps the arguments and returns it names; the
# minute runs an hour online across a world-day boundary, so the step closes one day (ruling 13-5).
CLOSE_COUNT = r"""
function(player, record, age)
    local K = NutritionRevamp.kernel
    local names = { { K.strength, "signalClose" }, { K.strength, "day" }, { K.strength, "growth" },
                    { K.strength, "detrain" }, { K.strength, "neural" }, { K.strength, "peakStep" },
                    { K.traits, "axes" }, { K.partition, "disuse" } }
    local seen = { n = {}, ret = {}, args = {} }
    local saved = {}
    for i = 1, #names do
        local t, k = names[i][1], names[i][2]
        local f = t[k]
        saved[i] = f
        seen.n[k] = 0
        t[k] = function(...)
            seen.n[k] = seen.n[k] + 1
            seen.args[k] = { ... }
            local r = { f(...) }
            seen.ret[k] = r
            return unpack(r)
        end
    end
    record.body.lastAgeH = age - 1
    NR_TEST_AGE = age
    local ok, err = pcall(NutritionRevamp.server.metabolism.minute, "admin", player, record)
    for i = 1, #names do names[i][1][names[i][2]] = saved[i] end
    seen.ok = ok
    seen.err = err
    return seen
end
"""


def test_one_close_runs_signal_close_day_and_axes_once_and_writes_the_sets(met_host):
    h = met_host
    p = player(h)
    record = fresh(h, p, 100.0)
    body = record["body"]
    for i in range(1, 8):
        body.sig7[i] = 100.0 * i               # slot 1 (100) leaves at the shift; slots 2-7 are the six kept days
    body.sigDay = 800.0
    failures = MET(h).stats.failures
    seen = h.rt.eval(CLOSE_COUNT)(p, record, 124.0)
    assert seen.ok is True and MET(h).stats.failures == failures
    for k, n in (("signalClose", 1), ("day", 1), ("axes", 1), ("disuse", 0)):
        assert seen.n[k] == n, k
    want = (200 + 300 + 400 + 500 + 600 + 700 + 800.0) / D(h).xpPerSet    # today's slot in, the oldest out
    assert body["S"] == want and seen.args["day"][2] == want
    assert seen.args["day"][8] == D(h).ts      # the biology clock rides on P
    assert body["sigDay"] == 0 and body["sig7"][7] == 800.0


def test_the_close_reads_the_servers_strength_table(met_host, opts):
    # the brief: P is NR.server.options.strength, falling back to DEFAULTS when absent
    h = met_host
    P, _ = h.K.strength.params(h.table({"StrengthXPPerSet": 100}))
    opts.strength = P
    p = player(h)
    record = fresh(h, p, 100.0)
    record["body"].sigDay = 300.0
    seen = h.rt.eval(CLOSE_COUNT)(p, record, 124.0)
    assert seen.ok is True
    assert record["body"]["S"] == 3.0 and h.G.rawequal(seen.args["day"][7], P)


def test_the_close_weighs_the_day_per_kg_of_the_body_mass(met_host):
    # ruling 13-20: w = fm + lm + lx; the protein the close hands on is per kg of it, and so is the alcohol
    h = met_host
    p = player(h)
    record = fresh(h, p, 100.0)
    body = record["body"]
    body.lx = 2.5
    body.pDay = 100.0
    body.alcDay = 30.0
    w = body["fm"] + body["lm"] + 2.5
    seen = h.rt.eval(CLOSE_COUNT)(p, record, 124.0)
    assert seen.ok is True
    assert seen.args["day"][3] == 100.0 / w and seen.args["day"][6] == 30.0 / w
    assert body["pPrevKg"] == 100.0 / w


def test_an_immobilised_close_runs_disuse_and_no_growth(met_host):
    # ruling 13-13 and the Task 8 review (amendment 3): the disuse arm in place of growth, regain and detraining;
    # detraining is called for its grace counter and its kg discarded; lx untouched; the neural factor still steps
    h = met_host
    p = player(h, fracture={"LowerLeg_L": 30.0}, traits={"STRONG": True})
    record = fresh(h, p, 100.0)
    body = record["body"]
    body.lm = body["F0"] + 3.0                 # above the set point: detraining would take kg on this day
    body.grace = 100                           # past the grace days, no sets: a detraining day
    body.lx = 0.5
    lm, fm = body["lm"], body["fm"]
    seen = h.rt.eval(CLOSE_COUNT)(p, record, 124.0)
    assert seen.ok is True
    assert seen.n["disuse"] == 1 and seen.n["day"] == 0 and seen.n["growth"] == 0 and seen.n["peakStep"] == 0
    assert seen.n["detrain"] == 1 and seen.n["neural"] == 1 and seen.n["axes"] == 1
    dfm, dlm = seen.ret["disuse"][1], seen.ret["disuse"][2]
    assert dlm < 0 and seen.ret["detrain"][1] > 0   # detraining's kg is real, and discarded
    assert body["lm"] == lm + dlm               # the disuse arm alone moved the lean
    assert body["fm"] == fm + dfm
    assert body["lx"] == 0.5 and body["grace"] == 101 and body["tDisuse"] == 1 and body["Tgrace"] == 1
    # a trained, fed day while immobilised grows nothing: the signal resets the grace counter and steps T only
    body.sigDay = 50 * D(h).xpPerSet
    body.pDay = 200.0
    lm, T = body["lm"], body["T"]
    seen = h.rt.eval(CLOSE_COUNT)(p, record, 148.0)
    assert seen.ok is True and seen.n["growth"] == 0 and seen.n["day"] == 0
    assert body["lm"] == lm + seen.ret["disuse"][2] and body["grace"] == 0 and body["T"] > T
    assert body["S"] == 50.0


def test_an_immobilised_close_keeps_the_floors(met_host):
    # ruling 13-35: the disuse arm's change is applied under fmMin and fMinShare * F0
    h = met_host
    p = player(h, fracture={"UpperLeg_R": 30.0})
    record = fresh(h, p, 100.0)
    body = record["body"]
    body.lm = D(h).fMinShare * body["F0"] + 1e-6
    body.fm = D(h).fmMin + 1e-6
    body.ebDay = -5000.0
    online(h, p, record, 124.0)
    assert body["lm"] == D(h).fMinShare * body["F0"] and body["fm"] == D(h).fmMin


def test_the_close_writes_the_band_and_marks_the_traits_dirty_only_when_it_changes(met_host):
    h = met_host
    p = player(h)
    record = fresh(h, p, 100.0)
    body = record["body"]
    online(h, p, record, 124.0)
    assert body["band"] == "normal" and body["traitsDirty"] is None
    body.fm = 12.5 * 1.7 * 1.7                 # past the obese cut by more than the margin
    online(h, p, record, 148.0)
    assert body["band"] == "obese" and body["traitsDirty"] is True and body["fatT"] == 2
    assert body["fmRef"] >= body["fm"]         # the re-base runs before the axes read the day's fat


# --- the stamps -----------------------------------------------------------------------------------------

def test_coefficients_stamped_neutral_on_a_fresh_body(met_host):
    h = met_host
    p = player(h)
    record = fresh(h, p)
    minute(h, p, record, 100.0 + 1 / 60)
    body = record["body"]
    assert body["dmod"] is None                # no drain coefficient: awake endurance stays vanilla's
    assert abs(body["rmod"] - 1.0) < TOL       # tac 1, protein gate neutral before the first close


def test_energy_state_reads_the_trailing_balance_and_fat_depletion(met_host):
    h = met_host
    p = player(h, moving=False, rate=1.5)
    record = fresh(h, p)
    body = record["body"]
    seed(h, body, ee=8000.0)                   # 8000 kcal spent in the hour before, nothing eaten (past the span)
    body.fm = body["fmRef"] / 2
    minute(h, p, record, 100.0 + 1 / 60)
    eb = h.K.energy.eb24h(body)                # the trailing-24 h window (Plan 11d Task 9c)
    expected = h.K.deficit.state(eb, 0.5)
    assert abs(body["energyState"] - expected) < TOL
    # the balance term saturates and the fat term reads the low-fat ramp (Plan 13 Task 10c): 1 + 0.5 + FAT_GAIN x
    # (0.5 - FAT_DEP_LO) / (FAT_DEP_HI - FAT_DEP_LO)
    D = h.K.deficit
    assert abs(body["energyState"] - (1.5 + D.FAT_GAIN * (0.5 - D.FAT_DEP_LO) / (D.FAT_DEP_HI - D.FAT_DEP_LO))) < TOL
    assert body["energyState"] > 1.5


def test_energy_state_reads_the_window_across_a_day_close_and_never_the_clock(met_host):
    # Plan 11d Task 9c: the window runs on the world age, so a day close (run x141b: floor(age / 24), not midnight on
    # the clock) moves nothing in it, and the clock hour never enters it
    h = met_host
    p = player(h, moving=False, rate=1.5)
    record = fresh(h, p, 119.5)
    body = record["body"]
    seed(h, body, hour=110, ee=1000.0)         # 1000 kcal spent nine hours before the close
    h.G.NR_TEST_TOD = 0.0                      # a clock reading would read midnight
    try:
        minute(h, p, record, 119.75)
        before = h.K.energy.eb24h(body)
        ee0 = h.K.body.trail24(body["trail"], "ee")
        minute(h, p, record, 120.25)           # the day closes: eb7 takes the day, the window keeps it
    finally:
        h.G.NR_TEST_TOD = None
    assert body["dayIndex"] == 5 and body["ebDay"] != before
    spent = h.K.body.trail24(body["trail"], "ee") - ee0
    assert spent > 0 and abs(h.K.energy.eb24h(body) - (before - spent)) < 1e-9
    fat_dep = (body["fmRef"] - body["fm"]) / body["fmRef"]   # the close's partition paid some fat
    assert abs(body["energyState"] - h.K.deficit.state(h.K.energy.eb24h(body), fat_dep)) < TOL
    assert body["energyState"] > 1 + 0.5 * 1000 / h.K.deficit.BALANCE_SPAN_KCAL


def test_the_window_moves_with_the_world_age(met_host):
    # Plan 11d Task 9c: each minute moves the window to its age, and no close stamp is kept; a jump past the hour the
    # step integrates skips the rest (Plan 12 A1: offline time is not simulated), so the window carries its contents
    # to the start of the integrated hour and zeroes only the hours that hour passes
    h = met_host
    p = player(h)
    record = fresh(h, p, 100.0)
    t = record["body"]["trail"]
    assert t["at"] == 100.0 and "lastCloseAgeH" not in h.py(record["body"])
    minute(h, p, record, 100.5)
    assert t["at"] == 100.5 and t.ee[h.K.body.trailSlot(100)] > 0
    ee100 = t.ee[h.K.body.trailSlot(100)]
    minute(h, p, record, 124.25)
    assert t["at"] == 124.25
    assert t.ee[h.K.body.trailSlot(110)] == 0 and t.ee[h.K.body.trailSlot(124)] > 0
    assert t.ee[h.K.body.trailSlot(123)] == ee100              # hour 100's slot carried to the integrated hour's start


def test_a_non_finite_stamp_heals_and_counts(met_host):
    h = met_host
    p = player(h)
    record = fresh(h, p)
    body = record["body"]
    body.fm = NAN
    body.tac = NAN
    body.eb7[3] = NAN
    failures = MET(h).stats.failures
    minute(h, p, record, 100.0 + 1 / 60)
    assert nonfinite(h, record) == ""
    assert body["fm"] == spec(h)["fm"]           # the no-trait body's fat (Plan 13 Task 12)
    assert body["tac"] == 1.0
    assert body["energyState"] == body["energyState"]
    assert MET(h).stats.failures == failures + 1
    assert "non-finite" in MET(h).lastError


def test_heal_covers_day_index_ages_and_creation_masses(met_host):
    h = met_host
    p = player(h)
    record = fresh(h, p, 100.0)
    body = record["body"]
    body.dayIndex = NAN
    body.lastAgeH = NAN
    body.trail.at = float("inf")
    body.F0 = NAN
    body.Pk = NAN
    failures = MET(h).stats.failures
    days = MET(h).stats.days
    minute(h, p, record, 110.0)
    assert body["dayIndex"] == 4               # floor(110 / 24), no record day to read; a NaN never stops the closes
    assert MET(h).stats.days == days           # healed to today: no spurious close
    assert body["lastAgeH"] == 110.0
    assert body["trail"]["at"] == 110.0
    assert body["F0"] == spec(h)["F0"] and body["Pk"] == spec(h)["Pk"]
    assert MET(h).stats.failures == failures + 1
    for k in ("dayIndex", "lastAgeH", "trail.at", "F0", "Pk"):
        assert k in MET(h).lastError
    assert nonfinite(h, record) == ""
    online(h, p, record, 120.0)
    assert body["dayIndex"] == 5               # the closes run again


def test_heal_day_index_reads_the_records_own_day(met_host):
    # Task 12 amendment 5: the record-day lower bound is the Nutrients step's last seen day, else the Effects day
    h = met_host
    p = player(h)
    for subs, want in (({"nutrients": {"lastDayIndex": 2}, "effects": {"lastDay": 1}}, 2),
                       ({"nutrients": {"lastDayIndex": NAN}, "effects": {"lastDay": 1}}, 1),
                       ({"effects": {"lastDay": 3}}, 3),
                       ({}, 4)):
        record = fresh(h, p, 100.0)
        for k, v in subs.items():
            record[k] = h.table(v)
        record["body"].dayIndex = NAN
        assert MET(h).dayFloor(record) == (want if want != 4 else None)
        minute(h, p, record, 100.0 + 1 / 60)
        assert record["body"]["dayIndex"] == want, subs


def test_heal_stamps_non_finite_ring_slots(met_host):
    h = met_host
    p = player(h)
    record = fresh(h, p, 100.0)
    body = record["body"]
    body.p7[2] = NAN
    body.eb7[7] = float("inf")
    body.trail.carb[h.K.body.trailSlot(100)] = NAN   # the window's current hour (Plan 11d Task 9c)
    body.mass7[1] = NAN
    failures = MET(h).stats.failures
    minute(h, p, record, 100.0 + 1 / 60)
    assert body["p7"][2] == 0 and body["eb7"][7] == 0 and body["trail"]["carb"][h.K.body.trailSlot(100)] == 0
    assert abs(body["mass7"][1] - (body["fm"] + body["lm"] + body["lx"])) < 1e-6
    assert MET(h).stats.failures == failures + 1
    for k in ("p7", "eb7", "trail.carb", "mass7"):
        assert k in MET(h).lastError
    assert nonfinite(h, record) == ""


def test_heal_covers_the_creation_scalars_and_the_strength_and_band_rings(met_host):
    # whole-pass issue 11: every field a kernel reads at a close heals to its neutral, counted
    h = met_host
    p = player(h, strength=7)
    record = fresh(h, p, 100.0)
    body = record["body"]
    body.N0 = NAN
    body.T = float("inf")
    body.grace = NAN
    body.tDisuse = NAN
    body.lm0dis = NAN
    body.fatT = 7
    body.exKcalDay = NAN
    body.sig7[3] = NAN
    body.bandWeek[2][1] = NAN
    body.bandWeek[5][2] = float("-inf")
    failures = MET(h).stats.failures
    minute(h, p, record, 100.0 + 1 / 60)
    assert body["N0"] == 1 and body["T"] == 1 and body["grace"] == 0
    assert body["tDisuse"] == 0 and body["fatT"] == 0
    assert abs(body["lm0dis"] - body["lm"]) < TOL
    assert body["exKcalDay"] == body["exKcalDay"]
    assert body["sig7"][3] == 0
    assert body["bandWeek"][2][1] == 0 and body["bandWeek"][5][2] == 0
    assert MET(h).stats.failures == failures + 1
    named = MET(h).lastError.split("non-finite ")[1].split(" for ")[0].split(",")
    for k in ("N0", "T", "grace", "tDisuse", "lm0dis", "fatT", "exKcalDay", "sig7", "bandWeek"):
        assert k in named, k
    assert nonfinite(h, record) == ""
    online(h, p, record, 124.0)                # the closes run on the healed record
    assert body["dayIndex"] == 5
    assert nonfinite(h, record) == ""


# --- the unreadable world age (Part B re-review) --------------------------------------------------------

def test_an_unreadable_world_age_skips_the_minute(met_host):
    h = met_host
    p = player(h)
    record = fresh(h, p, 100.0)
    body = record["body"]
    bad = MET(h).stats.badReads
    ee = body["eeDay"]
    minute(h, p, record, NAN)                  # getWorldAgeHours answers NaN
    assert MET(h).stats.badReads == bad + 1
    assert body["lastAgeH"] == 100.0 and body["trail"]["at"] == 100.0   # never stamped 0
    assert body["eeDay"] == ee
    record2 = h.rt.table()
    minute(h, p, record2, NAN)                 # no body is built off an unreadable age
    assert record2["body"] is None
    minute(h, p, record2, 100.0)
    assert record2["body"]["lastAgeH"] == 100.0


# --- the climb sample (ruling W-4) ----------------------------------------------------------------------

def _climb_credit(h, state):
    p0 = player(h)
    p1 = player(h, climb=state)
    r0 = fresh(h, p0, 100.0)
    r1 = fresh(h, p1, 100.0)
    minute(h, p0, r0, 100.0 + 1 / 60)
    minute(h, p1, r1, 100.0 + 1 / 60)
    return r1["body"]["metMinDay"] - r0["body"]["metMinDay"], r1["body"]["fm"] + r1["body"]["lm"]


@pytest.mark.parametrize("state, cls", [("FENCE", "JumpFence"), ("WINDOW", "ClimbRope")])
def test_a_climb_state_minute_credits_its_class_once(met_host, state, cls):
    h = met_host
    got, w = _climb_credit(h, state)
    T = h.K.training
    want = (T.CLIMB_MET[cls] - T.MET_FLOOR) * (w / T.MASS_REF)
    assert want > 0 and abs(got - want) < 1e-6


def test_read_activity_reads_the_climb_state(met_host):
    h = met_host
    assert MET(h).readActivity(player(h, climb="FENCE"), 100.0)[11] == "JumpFence"
    assert MET(h).readActivity(player(h, climb="WINDOW"), 100.0)[11] == "ClimbRope"
    assert MET(h).readActivity(player(h), 100.0)[11] is None


def test_absent_climb_state_globals_read_no_climb(met_host):
    h = met_host
    G = h.G
    saved = (G.ClimbOverFenceState, G.ClimbThroughWindowState)
    G.ClimbOverFenceState = None
    G.ClimbThroughWindowState = h.table({})    # a class global without instance
    try:
        assert MET(h).readActivity(player(h, climb="FENCE"), 100.0)[11] is None
        got, _ = _climb_credit(h, "FENCE")
        assert got == 0
    finally:
        G.ClimbOverFenceState, G.ClimbThroughWindowState = saved


def test_a_repeated_minute_credits_no_climb(met_host):
    h = met_host
    p = player(h, climb="FENCE")
    record = fresh(h, p, 100.0)                # first sight: dt 0
    assert record["body"]["metMinDay"] == 0
    minute(h, p, record, 100.0)                # the same minute again: dt 0
    assert record["body"]["metMinDay"] == 0


def test_a_raising_kernel_never_raises_into_the_walk(met_host):
    h = met_host
    p = player(h)
    record = fresh(h, p)
    failures = MET(h).stats.failures
    ok, err = h.rt.eval(RAISING)(p, record, 100.0 + 1 / 60)
    assert ok is True
    assert MET(h).stats.failures == failures + 1
    assert "boom" in str(MET(h).lastError)


def test_nil_record_is_a_no_op(met_host):
    h = met_host
    minutes = MET(h).stats.minutes
    MET(h).minute("admin", player(h), None)
    assert MET(h).stats.minutes == minutes


def test_limitations_name_the_branch_and_the_neutral_inputs(met_host):
    h = met_host
    lim = list(MET(h).limitations.values())
    assert ("the run and sprint flags never reach the server (x141a), so a runner bills as a walker and the "
            "Running classes are unreachable; the metabolic rate lags activity (a first-order lag fixed in real "
            "seconds, so its game-time length scales with the day length), and only a Fitness exercise bills its "
            "class from the first minute, from the server" + chr(39) + "s exercise flag; the current "
            "timed action is unreadable server-side, so the calorie-modifier bands are unused and timed actions "
            "bill at the class rate") in lim
    assert ("an 8.0 rate classifies as ClimbRope, never ForestryAxe (chopping bills 8.0 not 6.5); a 6.0 as "
            "HeavyWork, and Fitness only from the exercise flag") in lim
    assert ("offline time is not integrated and the record calendar does not advance offline: a "
            "return after a step over 60 game minutes closes no day and continues the day open at departure as "
            "today's record day, so record days count online days only; a server stall over 60 game minutes "
            "with the player online reads as a gap and folds those world days into one record day") in lim
    assert "the disuse arm needs a leg fracture or splint" in lim
    assert ("rmod" + chr(39) + "s alcohol arm reads body.alcDay, the day-so-far ethanol the partition close zeroes: "
            "the arm resets at the day close, not on a rolling 24 h") in lim
    assert ("the nutrient scalars (glycogen, dehydration, iron, caffeine, sleep debt, alcohol, the balance "
            "dial) read the previous minute" + chr(39) + "s record sub-tables (a one-minute lag; the pipeline" + chr(39) + "s "
            "ORDER runs the nutrients step after this one)") in lim
    assert not any("held neutral" in x for x in lim)
    assert "the drain coefficient is stamped and mirrored and drives no stat write" in lim
    assert ("a climb is credited when the minute sample lands inside the climb state; short climbs are "
            "missed") in lim
    assert ("the MET-minute bank is mirrored for the panel and feeds no coefficient; the aerobic dose is the "
            "band minutes") in lim
    assert "the engine's inventory weight is read as kilograms" in lim
    assert ("an exhausted idle character's metabolic rate sits at the tired floor (up to the DefaultExercise "
            "class), so exhaustion bills as activity") in lim
    assert ("rmod scales the asleep regeneration arm only; under the harness's partial sleep hold it measured "
            "0.904 for a predicted 0.848 (#2899)") in lim
    assert ("a day closes at 07:00 on the default fixture (#2890); the 24 h blends count hours since the last "
            "close") in lim
    assert ("an unreadable world age skips the minute; a first sight with an unreadable age sends its mirror "
            "without the body, which the next readable minute builds") in lim
    assert not any("Task " in x or "ruling" in x for x in lim)


# --- the wiring order -----------------------------------------------------------------------------------

def test_metabolism_runs_after_kinetics_in_the_players_list():
    # A bare runtime: NR_Core, a Players stand-in, an Events stub that records the OnServerStarted
    # handlers in registration order; the two files load in the game's alphabetical order.
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
    names = sorted(["NR_Server_Metabolism.lua", "NR_Server_Kinetics.lua", "NR_Server_Minute.lua"])
    assert names == ["NR_Server_Kinetics.lua", "NR_Server_Metabolism.lua", "NR_Server_Minute.lua"]
    for n in names:
        with open(os.path.join(SERVER, n), encoding="utf-8") as fh:
            load(fh.read(), "@" + n)()
    rt.execute("for i = 1, #NR_STARTED do NR_STARTED[i]() end")
    rt.execute("for i = 1, #NR_STARTED do NR_STARTED[i]() end")   # a second start wires nothing twice
    G = rt.globals()
    S = G.NutritionRevamp.server
    same = rt.eval("rawequal")
    assert same(S.minute.steps["kinetics"], S.kinetics.minute)
    assert same(S.minute.steps["metabolism"], S.metabolism.minute)
    order = [S.minute.ORDER[i] for i in range(1, len(S.minute.ORDER) + 1)]
    assert order.index("kinetics") < order.index("metabolism")
    assert S.metabolism.wired is True


def test_the_start_handler_registers_forget_though_the_minute_wiring_raises():
    # The handler's player hooks come first: a raise in the precondition or the minute registration (here
    # no NR.server.minute exists) leaves forget registered on both lists.
    rt = lua51.LuaRuntime(unpack_returned_tuples=True)
    load = rt.eval("function(src, name) return assert(loadstring(src, name)) end")
    with open(CORE, encoding="utf-8") as fh:
        load(fh.read(), "@NR_Core.lua")()
    rt.execute(r"""
        NR_STARTED = {}
        Events = { OnServerStarted = { Add = function(fn) NR_STARTED[#NR_STARTED + 1] = fn end } }
        isServer = function() return true end
        NutritionRevamp.server.players = { onFirstSight = {}, onDeparture = {} }
        NutritionRevamp.server.minute = nil
    """)
    with open(os.path.join(SERVER, "NR_Server_Metabolism.lua"), encoding="utf-8") as fh:
        load(fh.read(), "@NR_Server_Metabolism.lua")()
    ok = rt.eval("function() return pcall(NR_STARTED[1]) end")()
    assert ok is False or ok[0] is False
    same = rt.eval("rawequal")
    S = rt.globals().NutritionRevamp.server
    assert same(S.players.onDeparture[1], S.metabolism.forget)
    assert same(S.players.onFirstSight[2], S.metabolism.forget)


# --- first sight's mirror and the precondition (ruling T18-1) ----------------------------------------

FIRSTSIGHT = r"""
function(player, record, age)
    local NR = NutritionRevamp
    local savedBus = NR.server.bus
    NR_TEST_SENT = {}
    NR.server.bus = { sendMirror = function(p, r)
        NR_TEST_SENT[#NR_TEST_SENT + 1] = r.body ~= nil
        return true
    end }
    NR_TEST_AGE = age
    NR.server.metabolism.onFirstSight("admin", player, record)
    NR.server.bus = savedBus
    return NR_TEST_SENT
end
"""


def test_first_sight_hook_makes_the_body_before_the_mirror(met_host):
    h = met_host
    record = h.rt.table()
    n0 = MET(h).stats.firstSightMirrors
    sent = h.rt.eval(FIRSTSIGHT)(player(h), record, 100.0)
    assert list(sent.values()) == [True]       # the one mirror carried the body
    assert record["body"] is not None and record["body"]["lastAgeH"] == 100.0
    assert MET(h).stats.firstSightMirrors == n0 + 1
    MET(h).onFirstSight("admin", player(h), None)  # no record: nothing
    assert MET(h).stats.firstSightMirrors == n0 + 1


def test_first_sight_with_an_unreadable_age_defers_the_body(met_host):
    h = met_host
    record = h.rt.table()
    bad = MET(h).stats.badReads
    sent = h.rt.eval(FIRSTSIGHT)(player(h), record, NAN)
    assert list(sent.values()) == [False]      # the one mirror, without a body
    assert record["body"] is None
    assert MET(h).stats.badReads == bad + 1
    minute(h, player(h), record, 100.0)        # the next readable minute builds it
    assert record["body"]["lastAgeH"] == 100.0


# --- the players first sight and respawn: one mirror each, carrying the body ---------------------------

PLAYERS = os.path.join(SERVER, "NR_Server_Players.lua")


def _players_runtime():
    rt = lua51.LuaRuntime(unpack_returned_tuples=True)
    load = rt.eval("function(src, name) return assert(loadstring(src, name)) end")
    for path in [CORE] + sorted(glob.glob(os.path.join(SHARED, "NR_Kernel*.lua"))):
        with open(path, encoding="utf-8") as fh:
            load(fh.read(), "@" + os.path.basename(path))()
    rt.execute(r"""
        NR_HANDLERS = {}
        local function ev(name)
            return { Add = function(fn)
                NR_HANDLERS[name] = NR_HANDLERS[name] or {}
                table.insert(NR_HANDLERS[name], fn)
            end }
        end
        Events = { OnServerStarted = ev("OnServerStarted"), EveryOneMinute = ev("EveryOneMinute"),
                   OnTick = ev("OnTick"), OnNewGame = ev("OnNewGame") }
        isServer = function() return true end
        NR_AGE = 100.0
        getGameTime = function() return { getWorldAgeHours = function(s) return NR_AGE end } end
        NR_PLAYER = { getUsername = function(s) return "admin" end }
        getOnlinePlayers = function()
            return { size = function(s) return 1 end, get = function(s, i) return NR_PLAYER end }
        end
        NR_RECORDS = {}
        NR_SENT = {}
        NutritionRevamp.log.level = 0
        NutritionRevamp.server.store = {
            get = function(u, age) NR_RECORDS[u] = NR_RECORDS[u] or { username = u }; return NR_RECORDS[u] end,
            reset = function(u, age) NR_RECORDS[u] = { username = u, resets = 1 }; return NR_RECORDS[u] end,
        }
        NutritionRevamp.server.bus = { sendMirror = function(p, r)
            NR_SENT[#NR_SENT + 1] = r.body ~= nil
            return true
        end }
    """)
    for n in ["NR_Server_Metabolism.lua", "NR_Server_Minute.lua", "NR_Server_Players.lua"]:
        with open(os.path.join(SERVER, n), encoding="utf-8") as fh:
            load(fh.read(), "@" + n)()
    rt.execute("for i = 1, #NR_HANDLERS.OnServerStarted do NR_HANDLERS.OnServerStarted[i]() end")
    return rt


def test_first_sight_sends_one_mirror_with_the_body():
    rt = _players_runtime()
    G = rt.globals()
    rt.execute("NR_HANDLERS.EveryOneMinute[1]()")
    assert list(G.NR_SENT.values()) == []      # Plan 11 Task 9: the minute marks the sight; the drain runs it
    rt.execute("NR_HANDLERS.OnTick[1]()")
    assert list(G.NR_SENT.values()) == [True]  # one send, carrying the body
    assert G.NR_RECORDS.admin.body is not None
    assert G.NutritionRevamp.server.metabolism.stats.firstSightMirrors == 1
    rt.execute("NR_HANDLERS.EveryOneMinute[1]()")   # seen: no second first sight
    rt.execute("NR_HANDLERS.OnTick[1]()")
    assert list(G.NR_SENT.values()) == [True]


def test_a_respawn_reset_fires_first_sight_and_sends_one_mirror_with_the_new_body():
    rt = _players_runtime()
    G = rt.globals()
    rt.execute("NR_HANDLERS.EveryOneMinute[1](); NR_HANDLERS.OnTick[1]()")
    old = G.NR_RECORDS.admin.body
    rt.execute("NR_AGE = 130.0; NR_HANDLERS.OnNewGame[1](NR_PLAYER, nil)")
    assert list(G.NR_SENT.values()) == [True]         # Plan 11 Task 9: OnNewGame resets and evicts (#3358)
    rt.execute("NR_HANDLERS.EveryOneMinute[1](); NR_HANDLERS.OnTick[1]()")
    assert list(G.NR_SENT.values()) == [True, True]   # one send per reset, with the body, at the next minute
    body = G.NR_RECORDS.admin.body
    assert body is not None and body != old and body.lastAgeH == 130.0
    assert G.NutritionRevamp.server.metabolism.stats.firstSightMirrors == 2


def test_players_sends_no_mirror_of_its_own():
    with open(PLAYERS, encoding="utf-8") as fh:
        code = "\n".join(l.split("--")[0] for l in fh.read().splitlines())
    assert "sendMirror" not in code


PRECONDITION = r"""
function(v)
    local NR = NutritionRevamp
    local saved, savedOpts, savedLevel = SandboxVars, NR.server.options, NR.log.level
    NR.log.level = 0
    if v == "absent" then SandboxVars = nil
    elseif v == "missing" then SandboxVars = {}
    else SandboxVars = { Nutrition = v } end
    NR.server.options = { nutritionOn = false }
    local broken = NR.server.metabolism.checkPrecondition()
    local flagged = NR.server.options.nutritionOn
    SandboxVars, NR.server.options, NR.log.level = saved, savedOpts, savedLevel
    return broken, flagged
end
"""


@pytest.mark.parametrize("v, broken", [(False, False), (True, True), ("missing", True), ("absent", True),
                                       ("false", True)])
def test_precondition_warns_unless_nutrition_is_false(met_host, v, broken):
    h = met_host
    w0 = MET(h).stats.preconditionWarnings
    got, flagged = h.rt.eval(PRECONDITION)(v)
    assert got is broken
    assert flagged is broken
    assert MET(h).stats.preconditionWarnings == w0 + (1 if broken else 0)


def test_precondition_message_and_no_write():
    with open(METABOLISM, encoding="utf-8") as fh:
        src = fh.read()
    assert ('NR.log.say(1, "NutritionRevamp expects SandboxVars.Nutrition = false: vanilla\'s nutrition update '
            'is ON and will fight the weight flags and drain the mirror stores")') in src
    code = "\n".join(l.split("--")[0] for l in src.splitlines())
    assert re.search(r"^\s*(SandboxVars|sv)\.Nutrition\s*=[^=]", code, re.M) is None   # never changed


def test_wiring_checks_the_precondition_once_and_hooks_first_sight():
    rt = lua51.LuaRuntime(unpack_returned_tuples=True)
    load = rt.eval("function(src, name) return assert(loadstring(src, name)) end")
    with open(CORE, encoding="utf-8") as fh:
        load(fh.read(), "@NR_Core.lua")()
    for n in sorted(os.listdir(SHARED)):   # NR_Server_Options reads K.readLeaf and K.strength at file scope
        if n.startswith("NR_Kernel"):
            with open(os.path.join(SHARED, n), encoding="utf-8") as fh:
                load(fh.read(), "@" + n)()
    rt.execute(r"""
        NR_STARTED = {}
        NR_PRINTED = {}
        print = function(s) NR_PRINTED[#NR_PRINTED + 1] = s end
        Events = { OnServerStarted = { Add = function(fn) NR_STARTED[#NR_STARTED + 1] = fn end } }
        isServer = function() return true end
        SandboxVars = { Nutrition = true }
        NutritionRevamp.server.players = { onFirstSight = {}, onDeparture = {} }
    """)
    for n in sorted(["NR_Server_Metabolism.lua", "NR_Server_Kinetics.lua", "NR_Server_Minute.lua",
                     "NR_Server_Options.lua"]):
        with open(os.path.join(SERVER, n), encoding="utf-8") as fh:
            load(fh.read(), "@" + n)()
    rt.execute("for i = 1, #NR_STARTED do NR_STARTED[i]() end")
    rt.execute("for i = 1, #NR_STARTED do NR_STARTED[i]() end")
    G = rt.globals()
    printed = list(G.NR_PRINTED.values())
    warn = [s for s in printed if "expects SandboxVars.Nutrition = false" in s]
    assert len(warn) == 1                      # once, at level 1
    assert G.NutritionRevamp.server.options.nutritionOn is True
    report = [s for s in printed if "NutritionRevamp v" in s]
    assert report and "nutritionOn=true" in report[0]   # set before the boot self-report
    fs = G.NutritionRevamp.server.players.onFirstSight
    assert len(fs) == 2                        # onFirstSight, then the held-rate forget (Plan 11f C-17 fix 1)
    assert rt.eval("rawequal")(fs[1], G.NutritionRevamp.server.metabolism.onFirstSight)
    assert rt.eval("rawequal")(fs[2], G.NutritionRevamp.server.metabolism.forget)
    ds = G.NutritionRevamp.server.players.onDeparture
    assert len(ds) == 2 and rt.eval("rawequal")(ds[1], G.NutritionRevamp.server.kinetics.forget)   # the traits cache's drop (ruling T10-1), Kinetics loading first
    assert rt.eval("rawequal")(ds[2], G.NutritionRevamp.server.metabolism.forget)


def test_self_report_reads_nutrition_off_by_default():
    rt = lua51.LuaRuntime(unpack_returned_tuples=True)
    load = rt.eval("function(src, name) return assert(loadstring(src, name)) end")
    with open(CORE, encoding="utf-8") as fh:
        load(fh.read(), "@NR_Core.lua")()
    for n in sorted(os.listdir(SHARED)):   # NR_Server_Options reads K.readLeaf and K.strength at file scope
        if n.startswith("NR_Kernel"):
            with open(os.path.join(SHARED, n), encoding="utf-8") as fh:
                load(fh.read(), "@" + n)()
    with open(os.path.join(SERVER, "NR_Server_Options.lua"), encoding="utf-8") as fh:
        load(fh.read(), "@NR_Server_Options.lua")()
    G = rt.globals()
    assert G.NutritionRevamp.server.options.nutritionOn is False
    assert "nutritionOn=false" in G.NutritionRevamp.selfReport("server")


# --- the Plan 4 scalars: the record's nutrients, fluids and acute sub-tables feed rmod, TAC and E ---------

@pytest.fixture
def opts(met_host):
    # NR_Server_Options may or may not have loaded in this session: a stand-in with the dial on, put back
    h = met_host
    NR = h.G.NutritionRevamp
    saved = NR.server.options
    NR.server.options = h.table(dict(balanceBonus=True))
    try:
        yield NR.server.options
    finally:
        NR.server.options = saved


def _plan4(h, nutrients=None, fluids=None, acute=None, alcDay=None, **pkw):
    # a body made on a bare (pre-Plan-4) minute, then the sub-tables laid and one more minute run
    p = player(h, **pkw)
    record = fresh(h, p)
    if nutrients is not None:
        record.nutrients = h.table(nutrients)
    if fluids is not None:
        record.fluids = h.table(fluids)
    if acute is not None:
        a = h.K.acute["new"](100.0)
        for k, v in acute.items():
            a[k] = v
        record.acute = a
    if alcDay is not None:
        record["body"].alcDay = alcDay
    minute(h, p, record, 100.0 + 1 / 60)
    return record


def _activity_es(h, record, fatDep=0, ee24=True):
    """The energy state Metabolism stamps since Plan 11c Task 6 (spec s5c; amendment 4), rebuilt from the record:
    K.deficit.activityState(eb24h, ex24h, L, fatDep, ee24h), each 24 h figure off the trailing-24 h window (Plan 11d
    Task 9c): ex24h its exercise kcal and ee24h its expenditure floored at the resting expenditure (MET.ee24, as the
    Nutrients adapter reads it)."""
    E, B, D = h.K.energy, h.K.body, h.K.deficit
    body = record["body"]
    t = body["trail"]
    ex24 = B.trail24(t, "ex")
    ee24h = max(B.trail24(t, "ee"), E.ree(body["lm"]))
    L = record["satiety"]["L"]
    return D.activityState(E.eb24h(body), ex24, L, fatDep, ee24h if ee24 else None)


def _rmod(h, body, g=1, iron=1, dehyd=0, debt=0, alc=0, bonus=1):
    return h.K.aerobic.rmod(body["tac"], g, h.K.aerobic.gProt(body["pPrevKg"]), iron, dehyd, debt, alc, bonus)


def test_a_pre_plan4_record_reads_the_plan3_values(met_host, opts):
    h = met_host
    record = _plan4(h)
    body = record["body"]
    assert record["nutrients"] is None and record["fluids"] is None and record["acute"] is None
    assert body["rmod"] == _rmod(h, body)
    assert abs(body["rmod"] - 1.0) < TOL
    assert body["energyState"] == _activity_es(h, record)   # Plan 11c Task 6: the walker's exercise lagged


def test_iron_grade_four_reaches_rmod(met_host, opts):
    h = met_host
    record = _plan4(h, nutrients=dict(ironGrade=4))
    body = record["body"]
    assert body["rmod"] == _rmod(h, body, iron=4)
    assert abs(body["rmod"] - 0.75) < TOL          # IRON_R[4]


def test_dehydration_lowers_rmod_by_the_kernel_factor(met_host, opts):
    h = met_host
    base = _plan4(h)["body"]["rmod"]
    record = _plan4(h, fluids=dict(dehydPct=5))
    body = record["body"]
    assert body["rmod"] == _rmod(h, body, dehyd=5)
    A = h.K.aerobic
    factor = max(A.HYDR_R_FLOOR, 1 - A.HYDR_R_K * max(0, 5 - A.HYDR_T1))
    assert abs(body["rmod"] - base * factor) < TOL
    assert body["rmod"] < base


def test_the_balance_bonus_follows_all_replete_and_the_dial(met_host, opts):
    h = met_host
    base = _plan4(h)["body"]["rmod"]
    on = _plan4(h, nutrients=dict(allReplete=True))["body"]
    assert abs(on["rmod"] - base * 1.05) < TOL
    assert on["rmod"] == _rmod(h, on, bonus=1.05)
    opts.balanceBonus = False
    off = _plan4(h, nutrients=dict(allReplete=True))["body"]
    assert off["rmod"] == base
    opts.balanceBonus = True
    not_replete = _plan4(h, nutrients=dict(allReplete=False))["body"]
    assert not_replete["rmod"] == base


def test_absent_options_read_the_dial_default_on(met_host):
    h = met_host
    NR = h.G.NutritionRevamp
    saved = NR.server.options
    NR.server.options = None
    try:
        base = _plan4(h)["body"]["rmod"]
        body = _plan4(h, nutrients=dict(allReplete=True))["body"]
    finally:
        NR.server.options = saved
    assert abs(body["rmod"] - base * 1.05) < TOL


def test_the_acute_scalars_reach_rmod_and_the_energy_state(met_host, opts):
    h = met_host
    record = _plan4(h, acute=dict(g=0.5, awakeH=22.0, debtH=12.0, caf=120.0, cafTol=0.25))
    body = record["body"]
    assert body["rmod"] == _rmod(h, body, g=0.5, debt=12.0)
    assert body["energyState"] == _activity_es(h, record)    # g does not enter the state (ruling T4-1)


def test_the_day_alcohol_reaches_rmod_per_kg(met_host, opts):
    h = met_host
    record = _plan4(h, alcDay=80.0)
    body = record["body"]
    w = body["fm"] + body["lm"]
    assert body["rmod"] == _rmod(h, body, alc=80.0 / w)
    assert body["rmod"] < 1.0


def test_the_day_alcohol_reads_the_body_mass_with_the_labile_lean(met_host, opts):
    # ruling 13-20: the minute's mass after the close check is fm + lm + lx
    h = met_host
    p = player(h)
    record = fresh(h, p)
    body = record["body"]
    body.lx = 3.0
    body.alcDay = 50.0
    minute(h, p, record, 100.0 + 1 / 60)
    w = body["fm"] + body["lm"] + 3.0
    assert body["rmod"] == _rmod(h, body, alc=50.0 / w)
    assert body["rmod"] != _rmod(h, body, alc=50.0 / (w - 3.0))   # inside the arm's 0.5-1 g/kg ramp: the mass moves it


def test_unreadable_sub_table_values_read_neutral(met_host, opts):
    h = met_host
    failures = MET(h).stats.failures
    record = _plan4(h, nutrients=dict(ironGrade=7, allReplete="yes", vitDClinical=1),
                    fluids=dict(dehydPct=NAN, sweatActive="no"),
                    acute=dict(g=NAN, awakeH=float("inf"), caf=NAN, cafTol=-float("inf")))
    record.acute.debtH = None
    minute(h, player(h), record, 100.0 + 2 / 60)
    body = record["body"]
    assert body["rmod"] == _rmod(h, body)
    assert nonfinite(h, record) == ""
    for grade in (0, 2.5, NAN, "4"):
        rec = _plan4(h, nutrients=dict(ironGrade=grade))
        assert rec["body"]["rmod"] == _rmod(h, rec["body"])
    assert MET(h).stats.failures == failures       # no raise, no heal: the reads never stamp a bad value


CLOSE_SPY = r"""
function(player, record, age)
    local K = NutritionRevamp.kernel
    local origT = K.aerobic.tacDay
    local seen = {}
    K.aerobic.tacDay = function(...)
        seen.gIron = select(4, ...)
        seen.gSleep = select(7, ...)
        return origT(...)
    end
    record.body.lastAgeH = age - 1                 -- an hour online: the step closes the day (ruling 13-5)
    NR_TEST_AGE = age
    local ok, err = pcall(NutritionRevamp.server.metabolism.minute, "admin", player, record)
    K.aerobic.tacDay = origT
    seen.ok = ok
    return seen
end
"""


def test_the_close_reads_the_iron_and_sleep_gates(met_host, opts):
    h = met_host
    p = player(h)
    record = fresh(h, p, 100.0)
    failures = MET(h).stats.failures
    seen = h.rt.eval(CLOSE_SPY)(p, record, 124.0)
    assert seen["ok"] is True
    assert seen["gIron"] == 1 and seen["gSleep"] == 1          # a pre-Plan-4 record: the neutral gates
    record.nutrients = h.table(dict(ironGrade=3))
    a = h.K.acute["new"](100.0)
    a.debtH = 20.0
    record.acute = a
    record["body"].alcDay = 30.0
    seen = h.rt.eval(CLOSE_SPY)(p, record, 148.0)
    assert seen["ok"] is True
    assert MET(h).stats.failures == failures
    assert seen["gIron"] == h.K.aerobic.G_IRON[3]
    assert seen["gSleep"] == h.K.aerobic.gSleep(20.0)
    assert abs(seen["gSleep"] - 0.775) < TOL                   # 1 - (1 - 0.70) x (20 - 8)/16
    assert record["body"]["alcDay"] == 0                       # the partition close zeroes the day's ethanol


def test_met_and_cold_mult_are_stamped_finite(met_host, opts):
    h = met_host
    p = player(h, rate=3.1, moving=True, cold=1.4)
    record = fresh(h, p)
    body = record["body"]
    class_name = h.K.energy.classOf(h.K.energy.stripLoad(3.1, 0.0, 20))
    assert body["met"] == h.K.energy.activityMet(class_name, True, 1, 0.0)
    assert body["coldMult"] == 1.4
    p.cfg.cold = NAN
    p.cfg.rate = NAN
    minute(h, p, record, 100.0 + 1 / 60)
    assert body["coldMult"] == 1
    assert body["met"] == h.K.energy.activityMet("Default", True, 1, 0.0)
    assert nonfinite(h, record) == ""


def test_met_stamp_falls_back_to_one_when_the_kernel_returns_a_non_finite(met_host, opts):
    h = met_host
    E = h.K.energy
    orig = E.activityMet
    E.activityMet = h.rt.eval("function() return 0/0 end")
    try:
        record = fresh(h, player(h))
    finally:
        E.activityMet = orig
    assert record["body"]["met"] == 1


# --- Plan 11c Task 6 (spec s5c; rulings 11c-29, 11c-32 amended; amendment 4): the exercise lag and es -----------

def test_the_exercise_lag_steps_on_the_minutes_exercise_kcal(met_host):
    # a walker (engine 3.1, Walking5kmh, billed at Compendium 3.8): the minute banks (3.8 - 1.3) x w / 60 kcal of
    # exercise into exKcalDay, and L relaxes toward that rate by K.deficit.exerciseLag over the minute
    h = met_host
    p = player(h)
    record = fresh(h, p)
    body = record["body"]
    body["exKcalDay"] = 300.0           # a banked day, so a lag fed the cumulative day (not the minute's delta) is seen
    ex0 = body["exKcalDay"]
    w = body["fm"] + body["lm"]
    minute(h, p, record, 100.0 + 1 / 60)
    ex = body["exKcalDay"] - ex0
    assert abs(ex - (3.8 - 1.3) * w / 60) < 1e-9
    assert record["satiety"]["L"] == pytest.approx(h.K.deficit.exerciseLag(0, ex, 1 / 60), rel=1e-12)
    assert record["satiety"]["L"] > 0
    assert body["energyState"] == _activity_es(h, record)


def test_the_minute_stamps_the_class_and_the_exercise_flag_on_the_context_for_the_writer(met_host):
    # Ruling T6-2: the writer names the activity kind from the minute's class (S1301); FitnessHeavy is the one
    # resistance class classOf reaches (9.0 exactly), and Fitness.getCurrentExe is the flag for a 6.0 exercise, which
    # the minute bills at the Fitness class since Plan 11f C-17 (it read HeavyWork, the rate's class, before)
    h = met_host
    for kw, cls, ex in ((dict(rate=9.0), "FitnessHeavy", False), (dict(rate=3.1), "Walking5kmh", False),
                        (dict(rate=6.0, exe="squats"), "Fitness", True)):
        p = player(h, **kw)
        record = fresh(h, p)
        pipe = h.rt.table()
        minute(h, p, record, 100.0 + 1 / 60, pipe)
        assert pipe["activityClass"] == cls
        assert pipe["exercising"] == ex


def test_an_activity_surplus_never_lowers_es_below_the_no_activity_value(met_host):
    # S1330-S1332: with yesterday in surplus, balanced and in deficit, the walker's es is never below the state the
    # same intake reads with no activity, K.deficit.state(eb24h + ex24h): the exercise kcal added back to the balance
    h = met_host
    for eb in (1200.0, 0.0, -800.0):
        p = player(h)
        record = fresh(h, p)
        body = record["body"]
        seed(h, body, kcal=2000.0 + eb, ee=2000.0, ex=600.0)   # the hour before: the balance eb, 600 kcal of it exercise
        minute(h, p, record, 100.0 + 1 / 60)
        ex24 = h.K.body.trail24(body["trail"], "ex")
        plain = h.K.deficit.state(h.K.energy.eb24h(body) + ex24, 0)
        assert ex24 > 590 and body["energyState"] >= plain, eb
        assert body["energyState"] == _activity_es(h, record)


def test_the_bypass_ramp_fires_through_the_adapter_only_with_the_24h_expenditure(met_host):
    # the window: 1200 kcal eaten against 3000 spent, 800 kcal of it exercise; the 24 h total deficit d = -eb24h / ee24h is about 0.6 > EX_BYPASS_HI 0.405 (Plan 11g Task 7 fix 1; 0.44 in Task 7, 0.575 in Plan 11f Task 2c fix 1, 1500 kcal and 0.45 before), so the lag is bypassed
    # whole and es reads the balance as if the exercise were food restriction (S1325); the same record without the
    # 24 h expenditure bypasses nothing (the kernel's ee24h nil), so the adapter is what passes it
    h = met_host
    p = player(h, moving=False, rate=1.5)                  # idle: no exercise this minute, ex24h from the hour before
    record = fresh(h, p)
    body = record["body"]
    seed(h, body, kcal=1200.0, ee=3000.0, ex=800.0)
    minute(h, p, record, 100.0 + 1 / 60)
    es = body["energyState"]
    with_ee = _activity_es(h, record)
    without = _activity_es(h, record, ee24=False)
    eb = h.K.energy.eb24h(body)
    assert es == with_ee
    assert es > without + 0.05                             # the bypass is whole here (w = 1: d = 0.6 >= 0.575, L = 0) and moves es by 0.5 x 800 / 3100 = 0.129
    assert abs(es - h.K.deficit.state(eb, 0)) < 1e-9     # whole: the exercise share enters at once


def test_the_window_keeps_the_exercise_a_day_close_zeroes(met_host):
    # Plan 11d Task 9c: the partition close zeroes exKcalDay; the window, not a closed-day bank (Plan 11c's exKcalPrev,
    # retired), carries the bout: at 124.25 the bout's hour (100) is the oldest, three quarters inside; idle adds none.
    # The day is stepped in integrated hours: a single 24 h jump is an offline gap the window skips (Plan 12 A1)
    h = met_host
    p = player(h, moving=False, rate=1.5)
    record = fresh(h, p, 100.0)
    body = record["body"]
    body.exKcalDay = 300.0
    seed(h, body, hour=100, ex=300.0)
    for hour in range(101, 125):
        minute(h, p, record, float(hour))
    minute(h, p, record, 124.25)
    assert body["exKcalDay"] == 0 and "exKcalPrev" not in h.py(body)
    assert abs(h.K.body.trail24(body["trail"], "ex") - 0.75 * 300.0) < 1e-9


def test_a_non_finite_or_negative_lag_heals_and_counts(met_host):
    # amendment 4: L heals to 0 when non-finite or negative (the Task 4b re-review's residual); each heal counts in the
    # adapter's guard count (the closed-day exercise bank it healed beside L went with the 24 h blend, Plan 11d Task 9c)
    h = met_host
    p = player(h, moving=False, rate=1.5)
    for L in (float("nan"), -5.0, float("inf")):
        record = fresh(h, p)
        record.satiety = h.table({"L": L})
        g0 = MET(h).guarded
        minute(h, p, record, 100.0 + 1 / 60)
        assert record["satiety"]["L"] == 0
        assert MET(h).guarded == g0 + 1
        assert nonfinite(h, record) == ""


def test_a_record_without_satiety_gets_a_lag_and_no_pool(met_host):
    # Metabolism lays record.satiety for its L; G is the writer's to seed from HUNGER
    h = met_host
    p = player(h)
    record = fresh(h, p)
    assert record["satiety"]["L"] == 0 and record["satiety"]["M"] is None


# --- the window's minors (Plan 11d Task 9d; the Task 9c review's weak oracles for M3b and M8) ---------------------

def test_ee24_keeps_yesterdays_bout_whole_across_a_day_close(met_host):
    # MET.ee24 reads the window's expenditure, so a bout at 19:00 of day 4 (hour 115) counts whole at 06:15 of day 5,
    # after the day close at hour 120; the retired blend weighted the closed day by 1 - 6.25 / 24 and would read about
    # three quarters of it. Two records walked hour by hour, one with the bout: their ee24 differ by the bout's kcal
    h = met_host
    out = []
    for rate in (1.5, 10.3):
        p = player(h, moving=False, rate=1.5)
        record = fresh(h, p, 100.0)
        body = record["body"]
        bout = 0.0
        for hour in range(101, 127):
            if hour == 115:
                p.cfg.rate = rate                       # a 60 min minute at the run's rate, then idle again
                ee0 = body["eeDay"]
                minute(h, p, record, float(hour))
                bout = body["eeDay"] - ee0
                p.cfg.rate = 1.5
            else:
                minute(h, p, record, float(hour))
        minute(h, p, record, 126.25)
        assert body["dayIndex"] == 5
        assert MET(h).ee24(body) == max(h.K.body.trail24(body["trail"], "ee"), h.K.energy.ree(body["lm"]))
        out.append((MET(h).ee24(body), bout))
    (idle, b0), (run, b1) = out
    assert b1 - b0 > 500
    # within 1 %: the run arm's close pays a little more mass, so its later resting minutes spend about 4 kcal less
    assert abs((run - idle) - (b1 - b0)) < 0.01 * (b1 - b0), (run - idle, b1 - b0)


def test_an_intake_at_an_hour_turn_lands_in_the_new_hours_slot(met_host):
    # the window moves to the minute's age before the minute's intake lands (Metabolism's step), so a vector handed
    # off at the first minute of hour 101 is booked in hour 101's slot, and hour 100's holds no intake
    h = met_host
    p = player(h, moving=False, rate=1.5)
    record = fresh(h, p, 100.0)
    minute(h, p, record, 100.5)
    vec = h.K.vector.new()
    vec.calories = 600
    vec.proteins = 30
    pipe = h.rt.table()
    pipe.absorbed = vec
    minute(h, p, record, 101.0, pipe)
    t = record["body"]["trail"]
    s0, s1 = h.K.body.trailSlot(100), h.K.body.trailSlot(101)
    assert t.kcal[s1] == 600 and t.p[s1] == 30
    assert t.kcal[s0] == 0 and t.p[s0] == 0
    assert t.ee[s0] > 0 and t.ee[s1] > 0


def test_the_fresh_record_over_a_changed_character_is_a_stated_limitation(met_host):
    # Plan 12 (S B2, ruling P12-4: documented, not fixed until a durable marker is designed)
    lim = list(MET(met_host).limitations.values())
    assert any(x.startswith("a fresh record laid over a character the mod has already changed") for x in lim)


# --- Rule 6: the Java calls of a Metabolism minute (Plan 13 Task 4, the Plan 11g close rule) ------------------------
# The record calendar (K.body.calendar, ruling 13-5) replaced the catch-up loop with a pure-Lua read of body.wday: it
# adds no engine call. Every method of the player stand-in and of every table one of them returns, and the clock's
# getGameTime and its methods, are counted over a steady minute, an online day-close minute and a return after a gap.
# The counts were read at the build before the change (9b92ee9b) and pinned: a minute here makes no more.
JAVA_COUNT = r"""
function(p, C)
    local seen = {}
    local function wrap(t)
        if type(t) ~= "table" or seen[t] then return t end
        seen[t] = true
        local names = {}
        for k, v in pairs(t) do
            if type(v) == "function" then names[#names + 1] = k end
        end
        for i = 1, #names do
            local k = names[i]
            local f = t[k]
            t[k] = function(...)
                C.n = C.n + 1
                return wrap(f(...))
            end
        end
        return t
    end
    wrap(p)
    local gt = getGameTime
    C.restore = gt
    getGameTime = function()
        C.n = C.n + 1
        return wrap(gt())
    end
end
"""

HEAD_JAVA_CALLS = {"steady": 31, "close": 31, "return": 31}   # read at 9b92ee9b


def test_a_metabolism_minute_makes_no_more_java_calls_than_before_the_calendar(met_host):
    h = met_host
    p = player(h)
    record = fresh(h, p, 100.0)
    minute(h, p, record, 100.0 + 1 / 60)
    C = h.rt.eval("{ n = 0 }")
    h.rt.eval(JAVA_COUNT)(p, C)
    try:
        got = {}
        n0 = C.n
        minute(h, p, record, 100.0 + 2 / 60)
        got["steady"] = C.n - n0
        n0 = C.n
        online(h, p, record, 120.0)
        assert record["body"]["dayIndex"] == 5     # the minute closed a day
        got["close"] = C.n - n0
        n0 = C.n
        minute(h, p, record, 120.0 + 72.0)
        got["return"] = C.n - n0
    finally:
        h.G.getGameTime = C.restore
    for k, v in HEAD_JAVA_CALLS.items():
        assert got[k] <= v, (k, got)


# Plan 13 Task 12: first sight reads the held band traits (4 muscle and 5 weight gets at most) where the Plan 3 body
# read the weight, the six build traits, the Strength level and the carry delta. The first-sight minute's count was
# read at the day-close seam commit 6fa69ca7 (43 for a player holding no trait and for one holding Strong) and pinned:
# it makes no more. The steady, close and return minutes keep HEAD_JAVA_CALLS above.
HEAD_FIRST_SIGHT_CALLS = 43   # read at 6fa69ca7


@pytest.mark.parametrize("traits", [{}, {"STRONG": True}, {"STOUT": True, "EMACIATED": True}])
def test_a_first_sight_minute_makes_no_more_java_calls_than_the_plan_3_body(met_host, traits):
    h = met_host
    p = player(h, traits=traits)
    C = h.rt.eval("{ n = 0 }")
    h.rt.eval(JAVA_COUNT)(p, C)
    try:
        record = h.rt.table()
        minute(h, p, record, 100.0)
    finally:
        h.G.getGameTime = C.restore
    assert record["body"] is not None
    assert C.n <= HEAD_FIRST_SIGHT_CALLS, C.n


def test_the_close_and_first_sight_ride_the_servers_tuned_table(met_host, opts):
    # review T12: a tuned biology clock reaches every strength step of the close, the immobilised arm's included,
    # and first sight builds the creation body off the server's table, never DEFAULTS
    h = met_host
    P, _ = h.K.strength.params(h.table({"StrengthTimeScale": 3.0, "StrengthCapLevel": 18, "StrengthTraitShare": 0.2}))
    opts.strength = P
    p = player(h, traits={"STRONG": True})
    record = fresh(h, p, 100.0)
    want = h.py(h.K.body.create("STRONG", None, P, 1))
    assert want["F0"] != spec(h, "STRONG")["F0"]
    for k in ("lm", "F0", "Fc", "Pk", "N0", "fm"):
        assert record["body"][k] == want[k], k
    seen = h.rt.eval(CLOSE_COUNT)(p, record, 124.0)
    assert seen.ok is True and seen.args["day"][8] == 3.0
    q = player(h, fracture={"LowerLeg_L": 30.0})
    rec2 = fresh(h, q, 100.0)
    seen = h.rt.eval(CLOSE_COUNT)(q, rec2, 124.0)
    assert seen.ok is True and seen.n["day"] == 0
    assert seen.args["detrain"][5] == 3.0 and seen.args["neural"][4] == 3.0


def test_the_close_reads_the_axes_at_the_effective_sex(met_host, opts):
    # review T12: a female character reads the male cuts at the close unless NR.SexSpecific is on
    h = met_host
    p = player(h, female=True)
    for specific, want in ((False, 1), (True, 2)):
        opts.sexSpecific = specific
        record = fresh(h, p, 100.0)
        seen = h.rt.eval(CLOSE_COUNT)(p, record, 124.0)
        assert seen.ok is True and seen.args["axes"][2] == want, specific


def test_the_close_floors_tdee_at_the_resting_expenditure(met_host):
    # review T12: a short first day's eeDay reads the resting expenditure as tdee; a full day's its own
    h = met_host
    p = player(h)
    record = fresh(h, p, 100.0)
    body = record["body"]
    body.eeDay = 10.0
    lm = body["lm"]
    seen = h.rt.eval(CLOSE_COUNT)(p, record, 124.0)
    assert seen.ok is True and seen.args["day"][5] == h.K.energy.ree(lm)
    body.eeDay = 9000.0
    seen = h.rt.eval(CLOSE_COUNT)(p, record, 148.0)
    assert seen.ok is True and seen.args["day"][5] > 9000.0
