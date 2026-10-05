"""NR_Server_Metabolism, driven end to end through table-of-functions Java stand-ins.

The file is a server/ file the kernel host does not load, so it is loaded on top of the session host
the way test_kinetics.py loads NR_Server_Kinetics.lua. NR.call indexes obj[name] and calls it with obj
first, so a Lua table of function fields stands in for a Java object (test_intake_shape.py:612). Every
world age, rate and flag is stubbed by hand; the kernel math is the real kernel. A stub proves the
wiring, the order and the guards, not the engine's real getters, which the live acceptance runs read.
"""
import math
import os

import lupa.lua51 as lua51
import pytest

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
SERVER = os.path.join(REPO, "mod", "NutritionRevamp", "common", "media", "lua", "server")
SHARED = os.path.join(REPO, "mod", "NutritionRevamp", "common", "media", "lua", "shared")
METABOLISM = os.path.join(SERVER, "NR_Server_Metabolism.lua")
KINETICS = os.path.join(SERVER, "NR_Server_Kinetics.lua")
INTAKE = os.path.join(SERVER, "NR_Server_Intake.lua")
FAST = os.path.join(SERVER, "NR_Server_Fast.lua")
CORE = os.path.join(SHARED, "NR_Core.lua")
TOL = 1e-9

# The Java globals the adapter names, stubbed; the previous values are returned so the teardown puts
# them back and nothing leaks into a later module.
SETUP = r"""
function(age)
    local names = { "getGameTime", "CharacterTrait", "Perks", "MoodleType", "BodyPartType",
                    "SwipeStatePlayer", "ZombRandFloat" }
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
    p.isCurrentState = function(self, st) return self.cfg.swiping == true and st == "SWIPE" end
    return p
end
"""

MINUTE = r"""
function(player, record, age)
    NR_TEST_AGE = age
    NutritionRevamp.server.metabolism.minute("admin", player, record)
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
                exe=None, swiping=False, noBodyDamage=False)
    base.update(kw)
    return h.table(base)


def player(h, **kw):
    return h.rt.eval(PLAYER)(cfg(h, **kw))


def minute(h, p, record, age):
    return h.rt.eval(MINUTE)(p, record, age)


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


def test_lastabsorbed_is_consumed_once(met_host):
    h = met_host
    p = player(h)
    record = fresh(h, p)
    vec = h.K.vector.new()
    vec.calories = 500
    vec.proteins = 20
    KIN(h).lastAbsorbed["admin"] = vec
    minute(h, p, record, 100.0 + 1 / 60)
    assert abs(record["body"]["inDay"] - 500) < TOL
    assert abs(record["body"]["pDay"] - 20) < TOL
    assert KIN(h).lastAbsorbed["admin"] is None
    minute(h, p, record, 100.0 + 2 / 60)
    assert abs(record["body"]["inDay"] - 500) < TOL


def test_kinetics_hands_off_the_absorbed_vector(met_host):
    h = met_host
    K = h.K
    record = h.rt.table()
    record.stomach = K.stomach.new()
    K.stomach.seedFull(record.stomach)
    record.stomach.buffer.calories = 400
    record.pool = K.vector.new()
    h.G.NR_TEST_AGE = 100.0
    KIN(h).minute("admin", None, record)       # first step: dtH 0
    assert KIN(h).lastAbsorbed["admin"] is None
    h.G.NR_TEST_AGE = 101.0
    KIN(h).minute("admin", None, record)
    handed = KIN(h).lastAbsorbed["admin"]
    assert handed is not None and handed["calories"] > 0
    assert abs(handed["calories"] - record["pool"]["calories"]) < TOL
    KIN(h).minute("admin", None, record)       # same age: dtH 0 clears it
    assert KIN(h).lastAbsorbed["admin"] is None


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
    h.G.NR_TEST_TOD = 0.0
    try:
        minute(h, p, record, 100.0 + 1 / 60)
    finally:
        h.G.NR_TEST_TOD = None
    eb = h.K.energy.eb24h(body, 0.0)
    expected = h.K.energy.state(eb, 0.5)
    assert abs(body["energyState"] - expected) < TOL
    assert abs(body["energyState"] - 1.75) < TOL  # the balance term saturates: 1 + 0.5 + 0.5 x 0.5


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
    assert "offline time is not integrated" in lim
    assert "the disuse arm needs a leg fracture or splint" in lim
    assert ("glycogen, dehydration, iron, caffeine, alcohol, sleep debt and the balance dial are Plan 4/5 "
            "inputs held neutral") in lim
    assert "the drain coefficient is stamped and unapplied until Plan 5" in lim


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
    names = sorted(["NR_Server_Metabolism.lua", "NR_Server_Kinetics.lua"])
    assert names == ["NR_Server_Kinetics.lua", "NR_Server_Metabolism.lua"]
    for n in names:
        with open(os.path.join(SERVER, n), encoding="utf-8") as fh:
            load(fh.read(), "@" + n)()
    rt.execute("for i = 1, #NR_STARTED do NR_STARTED[i]() end")
    rt.execute("for i = 1, #NR_STARTED do NR_STARTED[i]() end")   # a second start wires nothing twice
    G = rt.globals()
    on = G.NutritionRevamp.server.players.onMinute
    assert len(on) == 2
    same = rt.eval("rawequal")
    assert same(on[1], G.NutritionRevamp.server.kinetics.minute)
    assert same(on[2], G.NutritionRevamp.server.metabolism.minute)
    assert G.NutritionRevamp.server.metabolism.wired is True


# --- the fast adapter's two scalars (the file names Java at hoist, so it is read, not loaded) ----------

def test_fast_adapter_reads_the_two_body_scalars():
    with open(FAST, encoding="utf-8") as fh:
        src = fh.read()
    region = src[src.index("-- @fastpath"):src.index("-- @endfastpath")]
    assert "inp.energyState = 1 " not in region
    assert "local body = h.record.body" in region
    assert "es = body.energyState" in region and "inp.energyState = es" in region
    assert "rm = body.rmod" in region and "inp.rmod = rm" in region
    assert "if es == nil or es ~= es then" in region
    assert "if rm == nil or rm ~= rm then" in region
