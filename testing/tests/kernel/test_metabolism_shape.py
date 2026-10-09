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
                       STRONG = "STRONG", STOUT = "STOUT" }
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
    # Kinetics' self-heal reads NR.server.intake.isFinite (Intake loads before it in the game), and the
    # handoff table lives on NR.server.kinetics: both load here when this module runs alone.
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


# --- first sight --------------------------------------------------------------------------------------

def test_first_sight_splits_the_body(met_host):
    h = met_host
    splits = MET(h).stats.splits
    record = fresh(h, player(h))
    body = record["body"]
    assert body is not None
    assert abs(body["fm"] - 14.4) < 1e-6
    assert abs(body["lm"] - 65.6) < 1e-6
    assert body["l0"] == 5
    assert body["traitCarry"] == 1.0
    assert 0.5 <= body["r"] <= 1.8
    assert abs(body["r"] - 1.0) < TOL          # twelve draws of 0.5: z = 0, r = exp(0) = 1
    assert body["sex"] == 1
    assert abs(body["lastAgeH"] - 100.0) < TOL
    assert body["dayIndex"] == 4
    assert MET(h).stats.splits == splits + 1
    assert body["eeDay"] == 0                  # dtM is 0 on the first minute
    assert nonfinite(h, record) == ""


def test_first_sight_reads_sex_build_and_the_responder_clamp(met_host):
    h = met_host
    h.G.NR_TEST_RAND = 1.0                     # z = 12 - 6 = 6: exp(1.8) clamps to 1.8
    try:
        p = player(h, female=True, traits={"ATHLETIC": True}, weight=62.0, strength=3, delta=0.9)
        body = fresh(h, p)["body"]
    finally:
        h.G.NR_TEST_RAND = 0.5
    assert body["sex"] == 2
    assert abs(body["r"] - 1.8) < TOL
    assert body["l0"] == 3
    assert abs(body["traitCarry"] - 0.9) < TOL
    fm, lm, _ = h.K.body.split(62.0, 2, h.table({"athletic": True}))
    assert abs(body["fm"] - fm) < TOL and abs(body["lm"] - lm) < TOL
    h.G.NR_TEST_RAND = 0.0                     # z = -6: exp(-1.8) clamps to 0.5
    try:
        body = fresh(h, player(h))["body"]
    finally:
        h.G.NR_TEST_RAND = 0.5
    assert abs(body["r"] - 0.5) < TOL


def test_first_sight_defaults_when_every_getter_is_absent(met_host):
    h = met_host
    saved = h.G.ZombRandFloat
    h.G.ZombRandFloat = None
    try:
        record = fresh(h, h.rt.table())        # a player with no members at all
    finally:
        h.G.ZombRandFloat = saved
    body = record["body"]
    assert abs(body["fm"] + body["lm"] - 80.0) < 1e-6
    assert body["sex"] == 1 and body["l0"] == 0 and body["traitCarry"] == 1.0 and body["r"] == 1
    assert nonfinite(h, record) == ""


def test_trait_carry_is_read_once(met_host):
    h = met_host
    p = player(h, delta=1.0)
    record = fresh(h, p)
    p.cfg.delta = 0.5                          # the mod's own later write: never re-read
    minute(h, p, record, 100.0 + 1 / 60)
    assert record["body"]["traitCarry"] == 1.0


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
    minute(h, p, record, 100.0 + 5.0)          # five hours later: billed as 60 minutes
    body = record["body"]
    ree = h.K.energy.ree(body["lm"])
    act = max(h.K.energy.activityMet("Default", False, 1, 0) - 1.0, 0) * 80.0
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
    KIN(h).minute("admin", None, record, pipe)
    handed = pipe.absorbed
    assert handed is not None and handed["calories"] > 0
    assert abs(handed["calories"] - record["pool"]["calories"]) < TOL
    KIN(h).minute("admin", None, record, pipe)       # same age: dtH 0 clears it
    assert pipe.absorbed is None


# --- the activity read (ruling T5-2) ----------------------------------------------------------------

def _activity(h, p):
    r = MET(h).readActivity(p)
    return dict(className=r[0], moving=r[1], modifier=r[2], loadKg=r[3], heavyLevel=r[4], coldMult=r[5],
                exercising=r[6], swiping=r[7], immobilised=r[8], hourOfDay=r[9], maxW=r[10], heatLevel=r[11])


def test_read_activity_classifies_the_rate(met_host):
    h = met_host
    a = _activity(h, player(h))
    assert a["className"] == "Walking5kmh"
    assert a["moving"] is True and a["modifier"] == 1
    assert a["loadKg"] == 0 and a["maxW"] == 20
    assert a["heavyLevel"] == 0 and a["heatLevel"] == 0 and a["coldMult"] == 1
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
    assert a["heatLevel"] == 2
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


def test_loaded_minute_banks_a_resistance_event_only_with_a_max_weight(met_host):
    h = met_host
    p = player(h, carried=17.0, maxW=20, rate=3.1 * (1 + 0.35 * 0.85 * 0.85))
    record = fresh(h, p)
    minute(h, p, record, 100.0 + 1 / 60)
    assert record["body"]["vStrHigh"] > 0      # 0.85 of max: a high load minute
    p0 = player(h, carried=17.0, maxW=0)
    record0 = fresh(h, p0)
    minute(h, p0, record0, 100.0 + 1 / 60)
    assert record0["body"]["vStr"] == 0        # maxW 0: loadMinute is not called
    assert nonfinite(h, record0) == ""


# --- the day close -------------------------------------------------------------------------------------

def test_a_24h_jump_closes_one_day(met_host):
    h = met_host
    p = player(h)
    record = fresh(h, p, 100.0)                # dayIndex 4
    days = MET(h).stats.days
    minute(h, p, record, 124.0)
    body = record["body"]
    assert body["dayIndex"] == 5
    assert MET(h).stats.days == days + 1
    assert body["eeDay"] == 0 and body["inDay"] == 0  # the day accumulators closed
    assert body["eb7"][7] < 0                  # the closed day's balance: an hour of expenditure
    assert nonfinite(h, record) == ""


def test_a_72h_jump_closes_three_days(met_host):
    h = met_host
    p = player(h)
    record = fresh(h, p, 100.0)
    days = MET(h).stats.days
    minute(h, p, record, 172.0)
    assert record["body"]["dayIndex"] == 7
    assert MET(h).stats.days == days + 3


def test_catch_up_is_capped_at_seven_days(met_host):
    h = met_host
    p = player(h)
    record = fresh(h, p, 100.0)
    days = MET(h).stats.days
    skipped = MET(h).stats.skippedDays
    minute(h, p, record, 100.0 + 240.0)        # ten days: seven closed, three skipped
    assert MET(h).stats.days == days + 7
    assert MET(h).stats.skippedDays == skipped + 3
    assert record["body"]["dayIndex"] == math.floor(340.0 / 24)


def test_day_close_runs_the_partition_strength_and_tac(met_host):
    h = met_host
    p = player(h)
    record = fresh(h, p, 100.0)
    body = record["body"]
    fm0 = body["fm"]
    body.vStr = 2.0
    body.vStrHigh = 2.0
    body.n = 0.0
    for i in range(1, 8):
        body.bandWeek[i][1] = 60               # a full week of band-1 minutes: TAC rises
    minute(h, p, record, 124.0)
    assert body["fm"] < fm0                    # an hour's deficit paid by fat
    assert body["n"] > 0 and body["nHist"][14] == body["n"]
    assert body["cumDef"] > 0
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
    minute(h, p, record, 124.0)
    assert body["bandWeek"][7][1] == 300.0
    assert body["band1Day"] == 0
    assert body["tac"] > 1.0                   # the same close saw the training


def test_close_order_training_ring_before_tac_and_at_after_the_ring():
    with open(METABOLISM, encoding="utf-8") as fh:
        src = fh.read()
    region = src[src.index("local function closeDay("):src.index("MET.stats.days = MET.stats.days + 1")]
    order = ["body.tDisuse = body.tDisuse + 1", "K.training.doses(body)", "K.partition.day(",
             "K.strength.closeDay(", "K.training.closeDay(body)", "K.training.weekMinutes(body)",
             "K.aerobic.tacDay(", "K.partition.closeDay(body, ageH)", "K.energy.atStep(",
             "K.partition.deficitWeek(body)"]
    at = [region.index(s) for s in order]
    assert at == sorted(at)
    assert "K.aerobic.gEnergy(body.inDay, body.exKcalDay, body.lm)" in region   # ruling W-1
    assert "actKcalDay" not in region
    assert re.search(r"K\.aerobic\.tacDay\(.*, immobilised\)", region)   # ruling W-2


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
    minute(h, p, record, 124.0)
    assert body["tDisuse"] == 1
    assert abs(body["lm0dis"] - lm) < TOL
    assert body["lm"] < lm
    lm1 = body["lm"]
    minute(h, p, record, 148.0)
    assert body["tDisuse"] == 2
    assert abs(body["lm0dis"] - lm) < TOL      # stamped once
    assert body["lm"] < lm1
    p.cfg.fracture = h.table({})
    minute(h, p, record, 172.0)
    assert body["tDisuse"] == 0


# --- the stamps -----------------------------------------------------------------------------------------

def test_coefficients_stamped_neutral_on_a_fresh_body(met_host):
    h = met_host
    p = player(h)
    record = fresh(h, p)
    minute(h, p, record, 100.0 + 1 / 60)
    body = record["body"]
    assert abs(body["dmod"] - 1.0) < TOL       # tac 1, no excess fat, heat 0
    assert abs(body["rmod"] - 1.0) < TOL       # tac 1, protein gate neutral before the first close


def test_heat_raises_the_drain_coefficient(met_host):
    h = met_host
    p = player(h, moodles={"HYPERTHERMIA": 2})
    record = fresh(h, p)
    minute(h, p, record, 100.0 + 1 / 60)
    assert abs(record["body"]["dmod"] - h.K.aerobic.HEAT[3]) < TOL


def test_energy_state_reads_the_trailing_balance_and_fat_depletion(met_host):
    h = met_host
    p = player(h, moving=False, rate=1.5)
    record = fresh(h, p)
    body = record["body"]
    body.eb7[7] = -3000.0
    body.fm = body["fmRef"] / 2
    minute(h, p, record, 100.0 + 1 / 60)
    eb = h.K.energy.eb24h(body, 1 / 60)        # the hours since the last close (first sight at 100)
    expected = h.K.energy.state(eb, 0.5)
    assert abs(body["energyState"] - expected) < TOL
    assert abs(body["energyState"] - 1.75) < TOL  # the balance term saturates: 1 + 0.5 + 0.5 x 0.5


def test_energy_state_blends_on_hours_since_the_close_not_the_clock(met_host):
    # run x141b: the day closes at floor(age / 24), which is not midnight on the clock; the blend reads
    # the hours since the last close, so the clock hour never enters it
    h = met_host
    p = player(h, moving=False, rate=1.5)
    record = fresh(h, p, 100.0)
    body = record["body"]
    body.lastCloseAgeH = 100.0 - 12.0          # half of yesterday still in the window
    body.eb7[7] = -1000.0
    h.G.NR_TEST_TOD = 0.0                      # a clock reading the old code would have used
    try:
        minute(h, p, record, 100.0)
    finally:
        h.G.NR_TEST_TOD = None
    expected = h.K.energy.state(body["ebDay"] + -1000.0 * 0.5, 0)
    assert abs(body["energyState"] - expected) < TOL
    assert abs(body["energyState"] - (1 + 0.5 * 500 / 1500)) < 1e-6


def test_day_close_stamps_last_close_age(met_host):
    h = met_host
    p = player(h)
    record = fresh(h, p, 100.0)
    assert record["body"]["lastCloseAgeH"] == 100.0  # K.body.new stamps creation
    minute(h, p, record, 124.25)
    assert abs(record["body"]["lastCloseAgeH"] - 124.25) < TOL


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
    assert abs(body["fm"] - body["fm0"]) < TOL
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
    body.lastCloseAgeH = float("inf")
    body.fm0 = NAN
    body.lm0 = NAN
    failures = MET(h).stats.failures
    days = MET(h).stats.days
    minute(h, p, record, 130.0)
    assert body["dayIndex"] == 5               # floor(130 / 24); a NaN never stops the closes
    assert MET(h).stats.days == days           # healed to today: no spurious close
    assert body["lastAgeH"] == 130.0
    assert body["lastCloseAgeH"] == 130.0
    assert abs(body["fm0"] - body["fm"]) < 1e-6 and abs(body["lm0"] - body["lm"]) < 1e-6
    assert MET(h).stats.failures == failures + 1
    for k in ("dayIndex", "lastAgeH", "lastCloseAgeH", "fm0", "lm0"):
        assert k in MET(h).lastError
    assert nonfinite(h, record) == ""
    minute(h, p, record, 154.0)
    assert body["dayIndex"] == 6               # the closes run again


def test_heal_creation_masses_fall_back_to_the_split(met_host):
    h = met_host
    p = player(h)
    record = fresh(h, p, 100.0)
    body = record["body"]
    body.fm = NAN
    body.fm0 = NAN
    body.lm = NAN
    body.lm0 = NAN
    minute(h, p, record, 100.0 + 1 / 60)
    fm, lm, _ = h.K.body.split(80, 1, h.table({}))
    assert abs(body["fm0"] - fm) < TOL and abs(body["lm0"] - lm) < TOL
    assert nonfinite(h, record) == ""


def test_heal_rebuilds_absent_rings_and_backfills_without_counting(met_host):
    # a record.body made before the p7/carb7/lip7 rings, pPrevKg or lastCloseAgeH existed
    h = met_host
    p = player(h)
    record = fresh(h, p, 100.0)
    body = record["body"]
    body.p7 = None
    body.carb7 = None
    body.lip7 = None
    body.pPrevKg = None
    body.lastCloseAgeH = None
    body.exKcalDay = None                      # a record saved before Part A-2's accumulator
    body.nHist = None
    body.bandWeek = None
    failures = MET(h).stats.failures
    minute(h, p, record, 100.5)
    for k in ("p7", "carb7", "lip7"):
        assert list(body[k].values()) == [0] * 7, k
    assert body["pPrevKg"] == h.K.aerobic.P_LOW
    assert body["lastCloseAgeH"] == 100.5
    assert body["exKcalDay"] > 0             # backfilled 0, then the walking half hour banked
    assert list(body["nHist"].values()) == [0] * 14
    assert [list(body["bandWeek"][i].values()) for i in range(1, 8)] == [[0, 0]] * 7
    assert MET(h).stats.failures == failures   # a backfill, not a corruption
    minute(h, p, record, 124.0)                # the partition ring reads the rebuilt rings
    assert body["dayIndex"] == 5
    assert nonfinite(h, record) == ""


def test_heal_stamps_non_finite_ring_slots(met_host):
    h = met_host
    p = player(h)
    record = fresh(h, p, 100.0)
    body = record["body"]
    body.p7[2] = NAN
    body.carb7[7] = float("inf")
    body.lip7[4] = NAN
    body.mass7[1] = NAN
    failures = MET(h).stats.failures
    minute(h, p, record, 100.0 + 1 / 60)
    assert body["p7"][2] == 0 and body["carb7"][7] == 0 and body["lip7"][4] == 0
    assert abs(body["mass7"][1] - (body["fm"] + body["lm"])) < 1e-6
    assert MET(h).stats.failures == failures + 1
    for k in ("p7", "carb7", "lip7", "mass7"):
        assert k in MET(h).lastError
    assert nonfinite(h, record) == ""


def test_heal_covers_the_creation_scalars_and_the_strength_and_band_rings(met_host):
    # whole-pass issue 11: every field a kernel reads at a close heals to its neutral, counted
    h = met_host
    p = player(h, strength=7)
    record = fresh(h, p, 100.0)
    body = record["body"]
    body.r = NAN
    body.traitCarry = float("inf")
    body.l0 = NAN
    body.tDisuse = NAN
    body.lm0dis = NAN
    body.nPeak = NAN
    body.tPeakD = NAN
    body.exKcalDay = NAN
    body.nHist[3] = NAN
    body.bandWeek[2][1] = NAN
    body.bandWeek[5][2] = float("-inf")
    failures = MET(h).stats.failures
    minute(h, p, record, 100.0 + 1 / 60)
    assert body["r"] == 1 and body["traitCarry"] == 1
    assert body["l0"] == 7                     # the Strength level read now
    assert body["tDisuse"] == 0 and body["nPeak"] == 0
    assert abs(body["lm0dis"] - body["lm"]) < TOL
    assert body["tPeakD"] == body["dayIndex"]
    assert body["exKcalDay"] == body["exKcalDay"]
    assert body["nHist"][3] == 0
    assert body["bandWeek"][2][1] == 0 and body["bandWeek"][5][2] == 0
    assert MET(h).stats.failures == failures + 1
    named = MET(h).lastError.split("non-finite ")[1].split(" for ")[0].split(",")
    for k in ("r", "traitCarry", "l0", "tDisuse", "lm0dis", "nPeak", "tPeakD", "exKcalDay", "nHist",
              "bandWeek"):
        assert k in named, k
    assert nonfinite(h, record) == ""
    minute(h, p, record, 124.0)                # the closes run on the healed record
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
    assert body["lastAgeH"] == 100.0 and body["lastCloseAgeH"] == 100.0   # never stamped 0
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
    assert MET(h).readActivity(player(h, climb="FENCE"), 100.0)[12] == "JumpFence"
    assert MET(h).readActivity(player(h, climb="WINDOW"), 100.0)[12] == "ClimbRope"
    assert MET(h).readActivity(player(h), 100.0)[12] is None


def test_absent_climb_state_globals_read_no_climb(met_host):
    h = met_host
    G = h.G
    saved = (G.ClimbOverFenceState, G.ClimbThroughWindowState)
    G.ClimbOverFenceState = None
    G.ClimbThroughWindowState = h.table({})    # a class global without instance
    try:
        assert MET(h).readActivity(player(h, climb="FENCE"), 100.0)[12] is None
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
            "Running classes are unreachable; the metabolic rate lags activity by tens of seconds; the current "
            "timed action is unreadable server-side, so the calorie-modifier bands are unused and timed actions "
            "bill at the class rate") in lim
    assert ("an 8.0 rate classifies as ClimbRope, never ForestryAxe (chopping bills 8.0 not 6.5); a 6.0 as "
            "HeavyWork, never Fitness") in lim
    assert ("offline time is not integrated; a multi-day catch-up runs days 2..n with pDay 0 (pPrevKg 0 until "
            "the next normal close) and reuses today's immobilised reading; the catch-up stamps every close "
            "with the catch-up minute's age, so the first blend after an offline gap counts yesterday in "
            "full") in lim
    assert "the disuse arm needs a leg fracture or splint" in lim
    assert ("rmod" + chr(39) + "s alcohol arm reads body.alcDay, the day-so-far ethanol the partition close zeroes: "
            "the arm resets at the day close, not on a rolling 24 h") in lim
    assert ("the nutrient scalars (glycogen, dehydration, iron, caffeine, sleep debt, alcohol, the balance "
            "dial) read the previous minute" + chr(39) + "s record sub-tables (a one-minute lag; the pipeline" + chr(39) + "s "
            "ORDER runs the nutrients step after this one)") in lim
    assert not any("held neutral" in x for x in lim)
    assert "the drain coefficient is stamped and unapplied until Plan 5" in lim
    assert ("a climb is credited when the minute sample lands inside the climb state; short climbs are "
            "missed") in lim
    assert ("the MET-minute bank is mirrored for the panel and feeds no coefficient; the aerobic dose is the "
            "band minutes") in lim
    assert "the engine's inventory weight is read as kilograms" in lim
    assert ("an exhausted idle character's metabolic rate sits at the tired floor (up to the DefaultExercise "
            "class), so exhaustion bills as activity until Plan 5 owns endurance") in lim
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
        NutritionRevamp.server.players = { onMinute = {} }
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
    assert len(S.players.onMinute) == 0                     # the pipeline's named steps (Plan 10 R2)
    same = rt.eval("rawequal")
    assert same(S.minute.steps["kinetics"], S.kinetics.minute)
    assert same(S.minute.steps["metabolism"], S.metabolism.minute)
    order = [S.minute.ORDER[i] for i in range(1, len(S.minute.ORDER) + 1)]
    assert order.index("kinetics") < order.index("metabolism")
    assert S.metabolism.wired is True


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
    rt.execute(r"""
        NR_STARTED = {}
        NR_PRINTED = {}
        print = function(s) NR_PRINTED[#NR_PRINTED + 1] = s end
        Events = { OnServerStarted = { Add = function(fn) NR_STARTED[#NR_STARTED + 1] = fn end } }
        isServer = function() return true end
        SandboxVars = { Nutrition = true }
        NutritionRevamp.server.players = { onMinute = {}, onFirstSight = {} }
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
    assert len(fs) == 1
    assert rt.eval("rawequal")(fs[1], G.NutritionRevamp.server.metabolism.onFirstSight)


def test_self_report_reads_nutrition_off_by_default():
    rt = lua51.LuaRuntime(unpack_returned_tuples=True)
    load = rt.eval("function(src, name) return assert(loadstring(src, name)) end")
    with open(CORE, encoding="utf-8") as fh:
        load(fh.read(), "@NR_Core.lua")()
    with open(os.path.join(SERVER, "NR_Server_Options.lua"), encoding="utf-8") as fh:
        load(fh.read(), "@NR_Server_Options.lua")()
    G = rt.globals()
    assert G.NutritionRevamp.server.options.nutritionOn is False
    assert "nutritionOn=false" in G.NutritionRevamp.selfReport("server")


# --- the Plan 4 scalars: the record's nutrients, fluids and acute sub-tables feed dmod, rmod, TAC and E --

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


def _activity_es(h, record, hsince, fatDep=0, g=1, ee24=True):
    """The energy state Metabolism stamps since Plan 11c Task 6 (spec s5c; amendment 4), rebuilt from the record:
    K.energy.activityState(eb24h, ex24h, L, fatDep, g, ee24h), ex24h the trailing-24 h exercise kcal (today's
    exKcalDay blended with the closed day's exKcalPrev, as K.energy.eb24h blends the balance) and ee24h the
    trailing-24 h expenditure the Nutrients adapter builds (today's eeDay blended with the closed day's, floored at
    the resting expenditure)."""
    E, B = h.K.energy, h.K.body
    body = record["body"]
    ex24 = B.blend24(body["exKcalDay"], body["exKcalPrev"] or 0, hsince)
    ee_yest = E.ree(body["lm"])
    if body["inDayClosed"] is not None:
        ee_yest = body["inDayClosed"] - body["eb7"][7]
    ee24h = max(B.blend24(body["eeDay"], ee_yest, hsince), E.ree(body["lm"]))
    L = record["satiety"]["L"]
    return E.activityState(E.eb24h(body, hsince), ex24, L, fatDep, g, ee24h if ee24 else None)


def _excess(h, body):
    w = body["fm"] + body["lm"]
    return h.K.aerobic.excessPct(body["fm"], h.K.aerobic.FM_NORMAL_80[body["sex"]], w)


def _rmod(h, body, g=1, iron=1, dehyd=0, debt=0, alc=0, bonus=1):
    return h.K.aerobic.rmod(body["tac"], g, h.K.aerobic.gProt(body["pPrevKg"]), iron, dehyd, debt, alc, bonus)


def _dmod(h, body, g=1, dehyd=0, heat=0, iron=1, awake=0, caf=0, tol=0):
    return h.K.aerobic.dmod(body["tac"], g, dehyd, heat, _excess(h, body), iron, awake, caf, tol)


def test_a_pre_plan4_record_reads_the_plan3_values(met_host, opts):
    h = met_host
    record = _plan4(h)
    body = record["body"]
    assert record["nutrients"] is None and record["fluids"] is None and record["acute"] is None
    assert body["dmod"] == _dmod(h, body)
    assert body["rmod"] == _rmod(h, body)
    assert abs(body["dmod"] - 1.0) < TOL and abs(body["rmod"] - 1.0) < TOL
    assert body["energyState"] == _activity_es(h, record, 1 / 60)   # Plan 11c Task 6: the walker's exercise lagged


def test_iron_grade_four_reaches_dmod_and_rmod(met_host, opts):
    h = met_host
    record = _plan4(h, nutrients=dict(ironGrade=4))
    body = record["body"]
    assert body["dmod"] == _dmod(h, body, iron=4)
    assert abs(body["dmod"] - 1.20) < TOL          # IRON_D[4] on a neutral body
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
    assert body["dmod"] == _dmod(h, body, dehyd=5)


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


def test_the_acute_scalars_reach_dmod_rmod_and_the_energy_state(met_host, opts):
    h = met_host
    record = _plan4(h, acute=dict(g=0.5, awakeH=22.0, debtH=12.0, caf=120.0, cafTol=0.25))
    body = record["body"]
    w = body["fm"] + body["lm"]
    caf = h.K.acute.cafEffect(record["acute"], w)
    assert 0 < caf < 1
    assert body["dmod"] == _dmod(h, body, g=0.5, awake=22.0, caf=caf, tol=0.25)
    assert body["rmod"] == _rmod(h, body, g=0.5, debt=12.0)
    assert body["energyState"] == _activity_es(h, record, 1 / 60, g=0.5)
    assert abs(body["energyState"] - (_activity_es(h, record, 1 / 60) + 0.15)) < TOL


def test_the_day_alcohol_reaches_rmod_per_kg(met_host, opts):
    h = met_host
    record = _plan4(h, alcDay=80.0)
    body = record["body"]
    w = body["fm"] + body["lm"]
    assert body["rmod"] == _rmod(h, body, alc=80.0 / w)
    assert body["rmod"] < 1.0


def test_unreadable_sub_table_values_read_neutral(met_host, opts):
    h = met_host
    failures = MET(h).stats.failures
    record = _plan4(h, nutrients=dict(ironGrade=7, allReplete="yes", vitDClinical=1),
                    fluids=dict(dehydPct=NAN, sweatActive="no"),
                    acute=dict(g=NAN, awakeH=float("inf"), caf=NAN, cafTol=-float("inf")))
    record.acute.debtH = None
    minute(h, player(h), record, 100.0 + 2 / 60)
    body = record["body"]
    assert body["dmod"] == _dmod(h, body)
    assert body["rmod"] == _rmod(h, body)
    assert nonfinite(h, record) == ""
    for grade in (0, 2.5, NAN, "4"):
        rec = _plan4(h, nutrients=dict(ironGrade=grade))
        assert rec["body"]["dmod"] == _dmod(h, rec["body"])
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
    # exercise into exKcalDay, and L relaxes toward that rate by K.energy.exerciseLag over the minute
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
    assert record["satiety"]["L"] == pytest.approx(h.K.energy.exerciseLag(0, ex, 1 / 60), rel=1e-12)
    assert record["satiety"]["L"] > 0
    assert body["energyState"] == _activity_es(h, record, 1 / 60)


def test_the_minute_stamps_the_class_and_the_exercise_flag_on_the_context_for_the_writer(met_host):
    # Ruling T6-2: the writer names the activity kind from the minute's class (S1301); FitnessHeavy is the one
    # resistance class classOf reaches (9.0 exactly), and Fitness.getCurrentExe is the flag for a 6.0 exercise
    h = met_host
    for kw, cls, ex in ((dict(rate=9.0), "FitnessHeavy", False), (dict(rate=3.1), "Walking5kmh", False),
                        (dict(rate=6.0, exe="squats"), "HeavyWork", True)):
        p = player(h, **kw)
        record = fresh(h, p)
        pipe = h.rt.table()
        minute(h, p, record, 100.0 + 1 / 60, pipe)
        assert pipe["activityClass"] == cls
        assert pipe["exercising"] == ex


def test_an_activity_surplus_never_lowers_es_below_the_no_activity_value(met_host):
    # S1330-S1332: with yesterday in surplus, balanced and in deficit, the walker's es is never below the state the
    # same intake reads with no activity, K.energy.state(eb24h + ex24h): the exercise kcal added back to the balance
    h = met_host
    for eb7 in (1200.0, 0.0, -800.0):
        p = player(h)
        record = fresh(h, p)
        body = record["body"]
        body.eb7[7] = eb7
        body.exKcalPrev = 600.0
        minute(h, p, record, 100.0 + 1 / 60)
        ex24 = h.K.body.blend24(body["exKcalDay"], body["exKcalPrev"], 1 / 60)
        plain = h.K.energy.state(h.K.energy.eb24h(body, 1 / 60) + ex24, 0, 1)
        assert ex24 > 590 and body["energyState"] >= plain, eb7
        assert body["energyState"] == _activity_es(h, record, 1 / 60)


def test_the_bypass_ramp_fires_through_the_adapter_only_with_the_24h_expenditure(met_host):
    # yesterday: 1500 kcal eaten against 3000 spent (inDayClosed 1500, eb7[7] -1500: eeYest 3000), 800 kcal of it
    # exercise; the 24 h total deficit d = -eb24h / ee24h is about 0.5 > EX_BYPASS_HI 0.45, so the lag is bypassed
    # whole and es reads the balance as if the exercise were food restriction (S1325); the same record without the
    # 24 h expenditure bypasses nothing (the kernel's ee24h nil), so the adapter is what passes it
    h = met_host
    p = player(h, moving=False, rate=1.5)                  # idle: no exercise this minute, ex24h from yesterday
    record = fresh(h, p)
    body = record["body"]
    body.eb7[7] = -1500.0
    body.inDayClosed = 1500.0
    body.exKcalPrev = 800.0
    minute(h, p, record, 100.0 + 1 / 60)
    es = body["energyState"]
    with_ee = _activity_es(h, record, 1 / 60)
    without = _activity_es(h, record, 1 / 60, ee24=False)
    eb = h.K.energy.eb24h(body, 1 / 60)
    assert es == with_ee
    assert es > without + 0.2                              # the bypass moves es by about 0.5 x 800 / 1500
    assert abs(es - h.K.energy.state(eb, 0, 1)) < 1e-9     # whole: the exercise share enters at once


def test_the_close_banks_the_days_exercise_kcal_for_the_24h_blend(met_host):
    # Plan 11c Task 6: the partition close zeroes exKcalDay, so the closing day's exercise is banked in
    # body.exKcalPrev first; an idle minute adds none, so the bank is the day's 300 kcal exactly
    h = met_host
    p = player(h, moving=False, rate=1.5)
    record = fresh(h, p, 100.0)
    body = record["body"]
    body.exKcalDay = 300.0
    minute(h, p, record, 124.25)
    assert body["exKcalPrev"] == 300.0 and body["exKcalDay"] == 0


def test_a_non_finite_lag_or_bank_heals_and_counts(met_host):
    # amendment 4: L and exKcalPrev heal to 0 when non-finite, and L when negative (the Task 4b re-review's residual);
    # each heal counts in the adapter's guard count
    h = met_host
    p = player(h, moving=False, rate=1.5)
    for L, bank in ((float("nan"), 0.0), (-5.0, 0.0), (0.0, float("nan"))):
        record = fresh(h, p)
        record.satiety = h.table({"L": L})
        record["body"].exKcalPrev = bank
        g0 = MET(h).guarded
        minute(h, p, record, 100.0 + 1 / 60)
        assert record["satiety"]["L"] == 0 and record["body"]["exKcalPrev"] == 0
        assert MET(h).guarded == g0 + 1
        assert nonfinite(h, record) == ""


def test_a_record_without_satiety_gets_a_lag_and_no_pool(met_host):
    # Metabolism lays record.satiety for its L; P and its mark are the writer's to seed from HUNGER
    h = met_host
    p = player(h)
    record = fresh(h, p)
    assert record["satiety"]["L"] == 0 and record["satiety"]["P"] is None and record["satiety"]["v"] is None
