-- NR_Kernel_Energy.lua -- the body model's expenditure and energy state: resting energy
-- expenditure off lean mass, adaptive thermogenesis, the two MET tables (the engine's Metabolics values,
-- read to classify the thermoregulator's target, and the Compendium METs expenditure bills), the
-- timed-action band METs, the Compendium METs per Fitness exercise, the Compendium load-walking floors, the engine
-- load factor divided out, the per-minute expenditure and intake accumulators on record.body and the trailing-24 h
-- balance the deficit drive reads (NR_Kernel_Deficit.lua: the energy state, the exercise lag and the hunger target,
-- since Plan 11g Task 7).
-- Pure: numbers and Lua tables in, numbers, strings and Lua tables out, no Java. Slow-clock code with
-- no fast region, so math.exp, math.abs and the bounded numeric `for` over the kernel's own tables are
-- allowed. This file sorts after NR_Kernel.lua, and every K.clamp / K.max reference is at call time.
local K = NutritionRevamp.kernel
K.energy = {}

-- Resting energy expenditure off lean mass: REE (kcal/d) = REE_A * LM + REE_B.
K.energy.REE_A = K.dials.get("energy.REE_A")
K.energy.REE_B = K.dials.get("energy.REE_B")

-- Adaptive thermogenesis: at most AT_MAX of REE, full at AT_FULL_DEP of the reference fat store gone,
-- approached with time constant AT_TAU_ON days under a deficit week, decaying with AT_TAU_OFF otherwise.
K.energy.AT_MAX = K.dials.get("energy.AT_MAX")
K.energy.AT_FULL_DEP = K.dials.get("energy.AT_FULL_DEP")
K.energy.AT_TAU_ON = K.dials.get("energy.AT_TAU_ON")
K.energy.AT_TAU_OFF = K.dials.get("energy.AT_TAU_OFF")

-- The cap on the resting cold multiplier (peak shivering, x resting metabolic rate).
K.energy.COLD_MAX = K.dials.get("energy.COLD_MAX")

-- The resting MET expenditure counts activity above.
K.energy.MET_REST = K.dials.get("energy.MET_REST")

-- ---------------------------------------------------------------------------------------------------------------------
-- The activity data, one section (spec § 6): the engine's class values and their bucketing order, the
-- Compendium bill per class, the timed-action band METs, the Compendium bill per Fitness exercise type and the
-- load-walking floors. Two MET tables, never mixed: CLASS_MET classifies the engine's rate and feeds the training
-- sample; COMPENDIUM, BAND_MET, EXERCISE_MET and LOAD_FLOOR are what expenditure bills.

-- The engine's Metabolics values by class name (Metabolics.<clinit>).
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

-- The same names in ascending engine value, for classOf's bucketing loop. Equal values keep the
-- plan's order (HeavyWork before Fitness, ClimbRope before ForestryAxe), and the first wins a tie.
-- The cost of the tie rule: an 8.0 rate classifies as ClimbRope, so COMPENDIUM.ForestryAxe is
-- unreachable through classOf and chopping bills COMPENDIUM.ClimbRope; a 6.0 as HeavyWork, so Fitness's 6.0 is reached
-- only by the exercise flag.
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

-- The 2024 Compendium MET expenditure bills for each engine class (ruling: two MET tables, never
-- mixed). A class with no Compendium row keeps its engine value.
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

-- The timed-action band METs keyed by the action's caloriesModifier; 1 has no entry.
-- #2720/#2638 the bands; 3 is the Fitness class value.
K.energy.BAND_MET = {}
K.energy.BAND_MET[0.5] = K.dials.get("energy.BAND_MET.0_5")
K.energy.BAND_MET[2] = K.dials.get("energy.BAND_MET.2")
K.energy.BAND_MET[3] = K.dials.get("energy.BAND_MET.3")
K.energy.BAND_MET[4] = K.dials.get("energy.BAND_MET.4")
K.energy.BAND_MET[5] = K.dials.get("energy.BAND_MET.5")
K.energy.BAND_MET[8] = K.dials.get("energy.BAND_MET.8")

-- The Compendium bill per vanilla Fitness exercise (C-2; spec § 3), keyed by ISFitnessAction's exeDataType
-- (the install's media/lua/shared/Definitions/FitnessExercises.lua), which NR_Server_Fitness.lua records server-side at
-- the set's start. Each type takes the general or moderate code of its pair, a game choice (Angus 2026-10-13), but burpees
-- the one code naming them; each line names the code not chosen. A set minute with no recorded or no known type bills COMPENDIUM.Fitness
-- (K.energy.exerciseMet), and NR_Server_Metabolism counts it.
K.energy.EXERCISE_MET = {}
K.energy.EXERCISE_MET.squats = K.dials.get("energy.EXERCISE_MET.squats")
K.energy.EXERCISE_MET.pushups = K.dials.get("energy.EXERCISE_MET.pushups")
K.energy.EXERCISE_MET.situp = K.dials.get("energy.EXERCISE_MET.situp")
K.energy.EXERCISE_MET.burpees = K.dials.get("energy.EXERCISE_MET.burpees")
K.energy.EXERCISE_MET.barbellcurl = K.dials.get("energy.EXERCISE_MET.barbellcurl")
K.energy.EXERCISE_MET.dumbbellpress = K.dials.get("energy.EXERCISE_MET.dumbbellpress")
K.energy.EXERCISE_MET.bicepscurl = K.dials.get("energy.EXERCISE_MET.bicepscurl")

-- The Compendium load-walking floors: {load threshold kg, MET}, ascending.
-- 5 lb = 2.3 kg, 15 lb = 6.8 kg, 50 lb = 22.7 kg.
-- the engine's inventory weight unit is read as kilograms (a game choice; no row); the thresholds are S0035's lb bands in kg
K.energy.LOAD_FLOOR = {
    { K.dials.get("energy.LOAD_FLOOR.1.1"), K.dials.get("energy.LOAD_FLOOR.1.2") },
    { K.dials.get("energy.LOAD_FLOOR.2.1"), K.dials.get("energy.LOAD_FLOOR.2.2") },
    { K.dials.get("energy.LOAD_FLOOR.3.1"), K.dials.get("energy.LOAD_FLOOR.3.2") },
}

-- The billing constants: the falling gate's threshold (K.energy.rateFalling) and the after-burn pool's
-- fraction, release constant and floor (K.energy.epoc).
K.energy.FALL_EPS = K.dials.get("energy.FALL_EPS")
K.energy.EPOC_F = K.dials.get("energy.EPOC_F")
K.energy.EPOC_TAU_H = K.dials.get("energy.EPOC_TAU_H")
K.energy.EPOC_FLOOR_KCAL = K.dials.get("energy.EPOC_FLOOR_KCAL")

-- The end of the activity data.
-- ---------------------------------------------------------------------------------------------------------------------

-- The band MET for a timed action's caloriesModifier, or nil for 1 and any unknown modifier.
function K.energy.bandMet(modifier)
    return K.energy.BAND_MET[modifier]
end

-- The largest load-walking floor whose threshold the load reaches, else 0 (thresholds ascend). loadKg
-- is the engine's inventory weight, read as kilograms (a game choice; no row).
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

-- The engine's load factor 1 + 0.35 * clamp01(carried / maxW)^2 divided out of a metabolic target
-- (#2649), so load is charged once. A non-positive maxW reads unloaded.
function K.energy.stripLoad(target, carried, maxW)
    if maxW <= 0 then
        return target
    end
    local f = K.clamp(carried / maxW, 0, 1)
    return target / (1 + K.energy.LOAD_FACTOR * f * f) -- #2649
end

-- The CLASS_LIST name whose engine value is nearest metValue; a tie goes to the earlier (lower) name.
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

-- The MET expenditure bills: the class's Compendium value (unknown reads COMPENDIUM.Default, standing quietly);
-- not moving, raised to the timed-action band (#0462: vanilla bills the modifier only when not
-- moving); walking, raised to the load-walking floor. exMet (optional) is a set minute's exercise MET
-- (K.energy.exerciseMet), billed as it stands: no band or load floor lifts it.
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

-- Resting energy expenditure (kcal/d) off lean mass lm (kg).
function K.energy.ree(lm)
    return K.energy.REE_A * lm + K.energy.REE_B
end

-- The adaptive-thermogenesis target: AT_MAX scaled by the fraction of the reference fat store gone,
-- full at AT_FULL_DEP; a non-positive reference reads 0.
function K.energy.atTarget(fm, fmRef)
    if fmRef <= 0 then
        return 0
    end
    return K.energy.AT_MAX * K.clamp(((fmRef - fm) / fmRef) / K.energy.AT_FULL_DEP, 0, 1)
end

-- One adaptive-thermogenesis step over dtD days: toward target with AT_TAU_ON under a deficit week,
-- else decaying toward 0 with AT_TAU_OFF.
function K.energy.atStep(at, target, deficitWeek, dtD)
    if deficitWeek then
        return at + (target - at) * (1 - math.exp(-dtD / K.energy.AT_TAU_ON))
    end
    return at * math.exp(-dtD / K.energy.AT_TAU_OFF)
end

-- One expenditure step of dtM game minutes (the pipeline bounds dtM at K.resume.STEP_M, the players' sub-steps;
-- offline time never reaches it, the store's resume). REE per minute, reduced by adaptive thermogenesis, times the cold multiplier at rest
-- (clamped to [1, COLD_MAX]); activity above MET_REST times the total mass fm + lm + lx per hour. Mutates body's day
-- accumulators, balance and trailing-24 h window (ee and ex, body.trail's current hour); returns the energy spent
-- and the activity part. Beside actKcalDay (net activity above 1 MET) it banks exKcalDay, the MET above the idle
-- class (COMPENDIUM.Default) times total mass per hour: the exercise energy availability subtracts.
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

-- One intake step: the absorbed vector (Plan 2's per-minute output) into the day accumulators and the window.
function K.energy.intake(body, absorbed, dtM)
    body.inDay = body.inDay + absorbed.calories
    body.pDay = body.pDay + absorbed.proteins
    body.carbDay = body.carbDay + absorbed.carbs
    body.lipDay = body.lipDay + absorbed.lipids
    body.ebDay = body.inDay - body.eeDay
    K.body.trailIntake(body.trail, absorbed)
end

-- The trailing-24 h balance: the window's absorbed kcal less its expenditure (K.body.trail24 over body.trail, Plan
-- 11d Task 9c). The caller moves the window to the minute's age (K.body.trailTo) before the minute's
-- intake and expenditure land in it. A game choice (the window; the 24 h span is ruling 14's).
function K.energy.eb24h(body)
    return K.body.trail24(body.trail, "kcal") - K.body.trail24(body.trail, "ee")
end

-- Whether the raw engine rate fell from prev to rate by more than FALL_EPS; a nil or non-finite reading is no fall.
function K.energy.rateFalling(prev, rate)
    if prev == nil or rate == nil then
        return false
    end
    if not K.finite(prev) or not K.finite(rate) then
        return false
    end
    return rate < prev - K.energy.FALL_EPS
end

-- The MET a set minute bills for the recorded exercise type exeType, and whether the type was known: EXERCISE_MET's
-- value for a vanilla type, else (no record, a modded exercise, a non-string) the flat COMPENDIUM.Fitness and false.
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

-- The class a minute bills. Exercise is billed by the activity, not by the
-- engine's lagged metabolic rate: the engine moves its rate toward the activity's target as an asymmetric first-order
-- lag (0.001 of the gap per update rising, 0.0004 falling, times GameTime's multiplier:
-- Thermoregulator.updateMetabolicRate), so a rate read alone under-bills a bout's rise and bills its slow fall as
-- exercise: about 450 kcal after a 1 h Fitness set at DayLength 1, where the after-burn is tens of kcal (S1775, S1777,
-- S1779). rateClass is the rate's classOf, exercising the server's exercise flag, moving the player's moving flag and
-- falling rateFalling's answer (raw against raw). Sleeping wins; otherwise the minute bills,
-- while the server's exercise flag is set (getFitness():getCurrentExe(), #2901) the Fitness class, from the first
-- exercise minute; while the rate falls with no exercise and no movement, the idle class (Default, COMPENDIUM.Default) for
-- any class billing above it; while it falls on the move, at most Walking5kmh; otherwise the rate's own class. Every
-- other activity keeps the engine's lag, so a walk, a chop or a fight still under-bills its rise. The function names
-- the class only: getCurrentExe cannot say which exercise (#2180, #2901), so the adapter bills a set minute at the MET
-- of the type NR_Server_Fitness.lua recorded at the set's start (K.energy.exerciseMet over EXERCISE_MET), or the flat
-- Fitness class (COMPENDIUM.Fitness) when no known type is recorded; the writer reads every set minute as resistance-vigorous from
-- the flag, whatever its MET (W.vigorous).
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
    -- a game choice resting on #2875 and #2877: a moving player's server rate settles near 3.1 even when asked to
    -- run, so a moving fall above Walking5kmh is all tail and bills Walking5kmh (it keeps activityMet's load floor)
    if falling and moving then
        if bill > K.energy.COMPENDIUM.Walking5kmh then
            return "Walking5kmh"
        end
    end
    return rateClass
end

-- The after-burn pool (EPOC, excess post-exercise oxygen consumption): body.epoc, kcal, created lazily by the first
-- exercise minute (a character who never exercises never carries it). Each minute with the exercise flag set adds
-- EPOC_F of its exercise kcal (the MET above the idle class times mass, exKcalDay's quantity); the pool releases with
-- the game-time constant EPOC_TAU_H, and the release is billed as expenditure (eeDay, ebDay and the window's ee), never
-- as exercise kcal: it does not enter exKcalDay, the window's ex or the exercise lag L. The decision, a game choice:
-- S1318's deficit is DLW total expenditure, which includes any after-burn, so the rows do not separate it from the
-- exercise (inference); the pool therefore enters the energy state at once, as resting expenditure does. Only the flag's
-- minutes feed it: the other activities keep the engine's lagged rate, whose own fall bills their tail.
-- One pool step of dtM game minutes: the minute's exercise kcal exKcal (a negative or non-finite one reads none) feeds
-- the pool when exercising; an existing pool then releases (1 - exp(-dtM / (60 EPOC_TAU_H))) of itself into the body's
-- expenditure. A pool that is not a number, non-finite or negative is stamped 0 first. Returns the kcal released and whether the pool
-- was healed; with no pool and no exercise it returns 0, false and lays nothing.
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
    -- A pool left under EPOC_FLOOR_KCAL is released whole (the remainder is billed, not dropped) and leaves the record,
    -- so a decayed pool stops costing an exp and a trail add every minute; the next exercise minute lays it again.
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

-- The engine's load factor K.energy.stripLoad divides out (Plan 19 Task 3g: its inline 0.35 named, a fixed row, #2649),
-- appended so no earlier line moves.
K.energy.LOAD_FACTOR = K.dials.get("energy.LOAD_FACTOR")
