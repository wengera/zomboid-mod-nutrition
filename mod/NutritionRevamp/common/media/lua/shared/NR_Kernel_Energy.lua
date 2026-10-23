-- NR_Kernel_Energy.lua: expenditure and the energy accumulators: resting expenditure off lean mass, adaptive
-- thermogenesis, the MET tables, the per-minute expenditure and intake on record.body, the trailing-24 h balance and
-- the after-burn pool. Pure, no Java; slow-clock code with no fast region. Sorts after NR_Kernel.lua; K.clamp and
-- K.max resolve at call time.
local K = NutritionRevamp.kernel
K.energy = {}

K.energy.REE_A = K.dials.get("energy.REE_A")
K.energy.REE_B = K.dials.get("energy.REE_B")

K.energy.AT_MAX = K.dials.get("energy.AT_MAX")
K.energy.AT_FULL_DEP = K.dials.get("energy.AT_FULL_DEP")
K.energy.AT_TAU_ON = K.dials.get("energy.AT_TAU_ON")
K.energy.AT_TAU_OFF = K.dials.get("energy.AT_TAU_OFF")

K.energy.COLD_MAX = K.dials.get("energy.COLD_MAX")

K.energy.MET_REST = K.dials.get("energy.MET_REST")

-- ---------------------------------------------------------------------------------------------------------------------
-- The activity data. Two MET tables, never mixed: CLASS_MET classifies the engine's rate and feeds the training
-- sample; COMPENDIUM, BAND_MET, EXERCISE_MET and LOAD_FLOOR are what expenditure bills.

-- The engine's Metabolics values (Metabolics.<clinit>).
K.energy.CLASS_MET = {}
K.energy.CLASS_MET.Sleeping = K.dials.get("energy.CLASS_MET.Sleeping")
K.energy.CLASS_MET.SeatedResting = K.dials.get("energy.CLASS_MET.SeatedResting")
K.energy.CLASS_MET.StandingAtRest = K.dials.get("energy.CLASS_MET.StandingAtRest")
K.energy.CLASS_MET.SedentaryActivity = K.dials.get("energy.CLASS_MET.SedentaryActivity")
K.energy.CLASS_MET.DrivingCar = K.dials.get("energy.CLASS_MET.DrivingCar")
K.energy.CLASS_MET.Default = K.dials.get("energy.CLASS_MET.Default")
K.energy.CLASS_MET.LightDomestic = K.dials.get("energy.CLASS_MET.LightDomestic")
K.energy.CLASS_MET.Walking2kmh = K.dials.get("energy.CLASS_MET.Walking2kmh")
K.energy.CLASS_MET.HeavyDomestic = K.dials.get("energy.CLASS_MET.HeavyDomestic")
K.energy.CLASS_MET.UsingTools = K.dials.get("energy.CLASS_MET.UsingTools")
K.energy.CLASS_MET.DefaultExercise = K.dials.get("energy.CLASS_MET.DefaultExercise")
K.energy.CLASS_MET.Walking5kmh = K.dials.get("energy.CLASS_MET.Walking5kmh")
K.energy.CLASS_MET.LightWork = K.dials.get("energy.CLASS_MET.LightWork")
K.energy.CLASS_MET.MediumWork = K.dials.get("energy.CLASS_MET.MediumWork")
K.energy.CLASS_MET.JumpFence = K.dials.get("energy.CLASS_MET.JumpFence")
K.energy.CLASS_MET.DiggingSpade = K.dials.get("energy.CLASS_MET.DiggingSpade")
K.energy.CLASS_MET.HeavyWork = K.dials.get("energy.CLASS_MET.HeavyWork")
K.energy.CLASS_MET.Fitness = K.dials.get("energy.CLASS_MET.Fitness")
K.energy.CLASS_MET.Running10kmh = K.dials.get("energy.CLASS_MET.Running10kmh")
K.energy.CLASS_MET.ClimbRope = K.dials.get("energy.CLASS_MET.ClimbRope")
K.energy.CLASS_MET.ForestryAxe = K.dials.get("energy.CLASS_MET.ForestryAxe")
K.energy.CLASS_MET.FitnessHeavy = K.dials.get("energy.CLASS_MET.FitnessHeavy")
K.energy.CLASS_MET.Running15kmh = K.dials.get("energy.CLASS_MET.Running15kmh")
K.energy.CLASS_MET.MAX = K.dials.get("energy.CLASS_MET.MAX")

-- Ascending engine value; the first wins a tie, so an 8.0 rate is ClimbRope (chopping never bills ForestryAxe) and a
-- 6.0 is HeavyWork (Fitness is reached only by the exercise flag).
K.energy.CLASS_LIST = {
    "Sleeping",
    "SeatedResting",
    "StandingAtRest",
    "SedentaryActivity",
    "DrivingCar",
    "Default",
    "LightDomestic",
    "Walking2kmh",
    "HeavyDomestic",
    "UsingTools",
    "DefaultExercise",
    "Walking5kmh",
    "LightWork",
    "MediumWork",
    "JumpFence",
    "DiggingSpade",
    "HeavyWork",
    "Fitness",
    "Running10kmh",
    "ClimbRope",
    "ForestryAxe",
    "FitnessHeavy",
    "Running15kmh",
    "MAX",
}

-- A class with no Compendium row keeps its engine value.
K.energy.COMPENDIUM = {}
K.energy.COMPENDIUM.Sleeping = K.dials.get("energy.COMPENDIUM.Sleeping")
K.energy.COMPENDIUM.SeatedResting = K.dials.get("energy.COMPENDIUM.SeatedResting")
K.energy.COMPENDIUM.StandingAtRest = K.dials.get("energy.COMPENDIUM.StandingAtRest")
K.energy.COMPENDIUM.SedentaryActivity = K.dials.get("energy.COMPENDIUM.SedentaryActivity")
K.energy.COMPENDIUM.DrivingCar = K.dials.get("energy.COMPENDIUM.DrivingCar")
K.energy.COMPENDIUM.Default = K.dials.get("energy.COMPENDIUM.Default")
K.energy.COMPENDIUM.LightDomestic = K.dials.get("energy.COMPENDIUM.LightDomestic")
K.energy.COMPENDIUM.HeavyDomestic = K.dials.get("energy.COMPENDIUM.HeavyDomestic")
K.energy.COMPENDIUM.UsingTools = K.dials.get("energy.COMPENDIUM.UsingTools")
K.energy.COMPENDIUM.DefaultExercise = K.dials.get("energy.COMPENDIUM.DefaultExercise")
K.energy.COMPENDIUM.Walking2kmh = K.dials.get("energy.COMPENDIUM.Walking2kmh")
K.energy.COMPENDIUM.Walking5kmh = K.dials.get("energy.COMPENDIUM.Walking5kmh")
K.energy.COMPENDIUM.LightWork = K.dials.get("energy.COMPENDIUM.LightWork")
K.energy.COMPENDIUM.MediumWork = K.dials.get("energy.COMPENDIUM.MediumWork")
K.energy.COMPENDIUM.HeavyWork = K.dials.get("energy.COMPENDIUM.HeavyWork")
K.energy.COMPENDIUM.JumpFence = K.dials.get("energy.COMPENDIUM.JumpFence")
K.energy.COMPENDIUM.DiggingSpade = K.dials.get("energy.COMPENDIUM.DiggingSpade")
K.energy.COMPENDIUM.Fitness = K.dials.get("energy.COMPENDIUM.Fitness")
K.energy.COMPENDIUM.FitnessHeavy = K.dials.get("energy.COMPENDIUM.FitnessHeavy")
K.energy.COMPENDIUM.Running10kmh = K.dials.get("energy.COMPENDIUM.Running10kmh")
K.energy.COMPENDIUM.ClimbRope = K.dials.get("energy.COMPENDIUM.ClimbRope")
K.energy.COMPENDIUM.ForestryAxe = K.dials.get("energy.COMPENDIUM.ForestryAxe")
K.energy.COMPENDIUM.Running15kmh = K.dials.get("energy.COMPENDIUM.Running15kmh")
K.energy.COMPENDIUM.MAX = K.dials.get("energy.COMPENDIUM.MAX")

-- Keyed by the timed action's caloriesModifier (#2720); 1 has no entry.
K.energy.BAND_MET = {}
K.energy.BAND_MET[0.5] = K.dials.get("energy.BAND_MET.0_5")
K.energy.BAND_MET[2] = K.dials.get("energy.BAND_MET.2")
K.energy.BAND_MET[3] = K.dials.get("energy.BAND_MET.3")
K.energy.BAND_MET[4] = K.dials.get("energy.BAND_MET.4")
K.energy.BAND_MET[5] = K.dials.get("energy.BAND_MET.5")
K.energy.BAND_MET[8] = K.dials.get("energy.BAND_MET.8")

-- Keyed by ISFitnessAction's exeDataType, which NR_Server_Fitness.lua records at the set's start (C-2). An unknown type
-- bills COMPENDIUM.Fitness (K.energy.exerciseMet).
K.energy.EXERCISE_MET = {}
K.energy.EXERCISE_MET.squats = K.dials.get("energy.EXERCISE_MET.squats")
K.energy.EXERCISE_MET.pushups = K.dials.get("energy.EXERCISE_MET.pushups")
K.energy.EXERCISE_MET.situp = K.dials.get("energy.EXERCISE_MET.situp")
K.energy.EXERCISE_MET.burpees = K.dials.get("energy.EXERCISE_MET.burpees")
K.energy.EXERCISE_MET.barbellcurl = K.dials.get("energy.EXERCISE_MET.barbellcurl")
K.energy.EXERCISE_MET.dumbbellpress = K.dials.get("energy.EXERCISE_MET.dumbbellpress")
K.energy.EXERCISE_MET.bicepscurl = K.dials.get("energy.EXERCISE_MET.bicepscurl")

-- {threshold kg, MET}, ascending: S0035's lb bands in kg, the inventory weight read as kilograms (a game choice).
K.energy.LOAD_FLOOR = {
    { K.dials.get("energy.LOAD_FLOOR.1.1"), K.dials.get("energy.LOAD_FLOOR.1.2") },
    { K.dials.get("energy.LOAD_FLOOR.2.1"), K.dials.get("energy.LOAD_FLOOR.2.2") },
    { K.dials.get("energy.LOAD_FLOOR.3.1"), K.dials.get("energy.LOAD_FLOOR.3.2") },
}

K.energy.FALL_EPS = K.dials.get("energy.FALL_EPS")
K.energy.EPOC_F = K.dials.get("energy.EPOC_F")
K.energy.EPOC_TAU_H = K.dials.get("energy.EPOC_TAU_H")
K.energy.EPOC_FLOOR_KCAL = K.dials.get("energy.EPOC_FLOOR_KCAL")

-- ---------------------------------------------------------------------------------------------------------------------

function K.energy.bandMet(modifier)
    return K.energy.BAND_MET[modifier]
end

-- Thresholds ascend, so the last reached wins.
function K.energy.loadFloor(loadKg)
    local floors = K.energy.LOAD_FLOOR
    local met = 0
    for i = 1, #floors do
        if loadKg >= floors[i][1] then
            met = floors[i][2]
        end
    end
    return met
end

-- The engine's load factor divided out of a metabolic target (#2649), so load is charged once.
K.energy.LOAD_FACTOR = K.dials.get("energy.LOAD_FACTOR")
function K.energy.stripLoad(target, carried, maxW)
    if maxW <= 0 then
        return target
    end
    local f = K.clamp(carried / maxW, 0, 1)
    return target / (1 + K.energy.LOAD_FACTOR * f * f) -- #2649
end

function K.energy.classOf(metValue)
    local list = K.energy.CLASS_LIST
    local best = list[1]
    local bestD = math.abs(metValue - K.energy.CLASS_MET[best])
    for i = 2, #list do
        local d = math.abs(metValue - K.energy.CLASS_MET[list[i]])
        if d < bestD then
            best = list[i]
            bestD = d
        end
    end
    return best
end

-- Not moving, raised to the timed-action band (#0462: vanilla bills the modifier only when not moving); walking,
-- raised to the load-walking floor. exMet, a set minute's exercise MET, is billed as it stands.
function K.energy.activityMet(className, moving, modifier, loadKg, exMet)
    if exMet ~= nil then
        return exMet
    end
    local met = K.energy.COMPENDIUM[className] or K.energy.COMPENDIUM.Default -- S0020
    local band = K.energy.bandMet(modifier)
    if not moving and band then
        met = K.max(met, band)
    end
    if moving and (className == "Walking2kmh" or className == "Walking5kmh") then
        met = K.max(met, K.energy.loadFloor(loadKg))
    end
    return met
end

function K.energy.ree(lm)
    return K.energy.REE_A * lm + K.energy.REE_B
end

-- A non-positive reference reads 0.
function K.energy.atTarget(fm, fmRef)
    if fmRef <= 0 then
        return 0
    end
    return K.energy.AT_MAX * K.clamp(((fmRef - fm) / fmRef) / K.energy.AT_FULL_DEP, 0, 1)
end

function K.energy.atStep(at, target, deficitWeek, dtD)
    if deficitWeek then
        return at + (target - at) * (1 - math.exp(-dtD / K.energy.AT_TAU_ON))
    end
    return at * math.exp(-dtD / K.energy.AT_TAU_OFF)
end

-- dtM is bounded at K.resume.STEP_M and never carries offline time. exKcalDay banks the MET above the idle class, what
-- energy availability subtracts (S0691).
function K.energy.minute(body, met, resting, coldMult, dtM)
    local coldK = 1
    if resting then
        coldK = K.clamp(coldMult, 1, K.energy.COLD_MAX)
    end
    local reeMin = K.energy.ree(body.lm) / 1440 * (1 - body.at) * coldK
    local actMin = K.max(met - K.energy.MET_REST, 0) * (body.fm + body.lm + body.lx) / 60
    local ee = (reeMin + actMin) * dtM
    local act = actMin * dtM
    local ex = K.max(met - K.energy.COMPENDIUM.Default, 0) * (body.fm + body.lm + body.lx) / 60 * dtM
    body.eeDay = body.eeDay + ee
    body.actKcalDay = body.actKcalDay + act
    body.exKcalDay = body.exKcalDay + ex -- S0691: EA is intake minus EXERCISE expenditure per kg FFM; the idle class is not exercise
    body.ebDay = body.inDay - body.eeDay
    K.body.trailAdd(body.trail, "ee", ee)
    K.body.trailAdd(body.trail, "ex", ex)
    return ee, act
end

function K.energy.intake(body, absorbed, dtM)
    body.inDay = body.inDay + absorbed.calories
    body.pDay = body.pDay + absorbed.proteins
    body.carbDay = body.carbDay + absorbed.carbs
    body.lipDay = body.lipDay + absorbed.lipids
    body.ebDay = body.inDay - body.eeDay
    K.body.trailIntake(body.trail, absorbed)
end

-- The caller moves the window to the minute's age (K.body.trailTo) before the minute's intake and expenditure land.
function K.energy.eb24h(body)
    return K.body.trail24(body.trail, "kcal") - K.body.trail24(body.trail, "ee")
end

-- A nil or non-finite reading is no fall.
function K.energy.rateFalling(prev, rate)
    if prev == nil or rate == nil then
        return false
    end
    if not K.finite(prev) or not K.finite(rate) then
        return false
    end
    return rate < prev - K.energy.FALL_EPS
end

-- A modded, missing or non-string type bills the flat COMPENDIUM.Fitness and returns false.
function K.energy.exerciseMet(exeType)
    local met = nil
    if type(exeType) == "string" then
        met = K.energy.EXERCISE_MET[exeType]
    end
    if met == nil then
        return K.energy.COMPENDIUM.Fitness, false
    end
    return met, true
end

-- Exercise is billed by the activity, not by the engine's lagged rate (Thermoregulator.updateMetabolicRate), which
-- under-bills a bout's rise and bills its slow fall as exercise (S1775). Sleeping wins; otherwise the minute bills,
-- while the server's exercise flag is set (getFitness():getCurrentExe(), #2901) the Fitness class; while the rate
-- falls with no movement, at most the idle class; on the move, at most Walking5kmh. Other activities keep the lag.
function K.energy.billClass(rateClass, exercising, moving, falling)
    if rateClass == "Sleeping" then
        return rateClass
    end
    if exercising then
        return "Fitness"
    end
    local bill = K.energy.COMPENDIUM[rateClass] or K.energy.COMPENDIUM.Default
    if falling and not moving then
        if bill > K.energy.COMPENDIUM.Default then
            return "Default"
        end
    end
    -- a game choice (#2875): a moving player's server rate settles near 3.1 even when asked to run, so a moving fall
    -- above Walking5kmh is all tail
    if falling and moving then
        if bill > K.energy.COMPENDIUM.Walking5kmh then
            return "Walking5kmh"
        end
    end
    return rateClass
end

-- The after-burn pool body.epoc, laid lazily by the first exercise minute: EPOC_F of each flagged minute's exercise
-- kcal, released with EPOC_TAU_H and billed as expenditure, never as exercise kcal (a game choice: S1318's DLW total
-- includes any after-burn). A corrupt pool is stamped 0; returns the kcal released and whether it was healed.
function K.energy.epoc(body, exercising, exKcal, dtM)
    local pool = body.epoc
    local healed = false
    if pool ~= nil and (not K.finite(pool) or pool < 0) then
        pool = 0
        healed = true
    end
    if not K.finite(exKcal) or exKcal < 0 then
        exKcal = 0
    end
    if exercising and exKcal > 0 then
        if pool == nil then
            pool = 0
        end
        pool = pool + K.energy.EPOC_F * exKcal
    end
    if pool == nil then
        return 0, healed
    end
    local rel = 0
    if dtM > 0 then
        rel = pool * (1 - math.exp(-dtM / (60 * K.energy.EPOC_TAU_H)))
    end
    -- Released whole under EPOC_FLOOR_KCAL and dropped, so a decayed pool stops costing an exp every minute.
    if pool - rel < K.energy.EPOC_FLOOR_KCAL then
        rel = pool
        body.epoc = nil
    else
        body.epoc = pool - rel
    end
    body.eeDay = body.eeDay + rel
    body.ebDay = body.inDay - body.eeDay
    K.body.trailAdd(body.trail, "ee", rel)
    return rel, healed
end
