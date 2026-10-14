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
K.energy.REE_A = 19.7 -- S0004
K.energy.REE_B = 413 -- S0004

-- Adaptive thermogenesis: at most AT_MAX of REE, full at AT_FULL_DEP of the reference fat store gone,
-- approached with time constant AT_TAU_ON days under a deficit week, decaying with AT_TAU_OFF otherwise.
K.energy.AT_MAX = 0.10 -- design-phase-v1 game choice: adaptive-thermogenesis magnitude; S1055 design-phase-v1 (the open row; direction S0013/S0016); direction S0013/S0016
K.energy.AT_FULL_DEP = 0.5 -- design-phase-v1 game choice: adaptive-thermogenesis magnitude; S1055 design-phase-v1 (the open row; direction S0013/S0016); direction S0013/S0016
K.energy.AT_TAU_ON = 7 -- design-phase-v1 game choice: adaptive-thermogenesis magnitude; S1055 design-phase-v1 (the open row; direction S0013/S0016); direction S0013/S0016
K.energy.AT_TAU_OFF = 14 -- design-phase-v1 game choice: adaptive-thermogenesis magnitude; S1055 design-phase-v1 (the open row; direction S0013/S0016); direction S0013/S0016

-- The cap on the resting cold multiplier (peak shivering, x resting metabolic rate).
K.energy.COLD_MAX = 4.9 -- S0048

-- The resting MET expenditure counts activity above.
K.energy.MET_REST = 1.0 -- S0018/S0019

-- ---------------------------------------------------------------------------------------------------------------------
-- The activity data, one section (spec § 6): the engine's class values and their bucketing order, the
-- Compendium bill per class, the timed-action band METs, the Compendium bill per Fitness exercise type and the
-- load-walking floors. Two MET tables, never mixed: CLASS_MET classifies the engine's rate and feeds the training
-- sample; COMPENDIUM, BAND_MET, EXERCISE_MET and LOAD_FLOOR are what expenditure bills.

-- The engine's Metabolics values by class name (Metabolics.<clinit>).
K.energy.CLASS_MET = {}
K.energy.CLASS_MET.Sleeping = 0.8 -- #2632
K.energy.CLASS_MET.SeatedResting = 1.0 -- #2632
K.energy.CLASS_MET.StandingAtRest = 1.1 -- #2632
K.energy.CLASS_MET.SedentaryActivity = 1.2 -- #2632
K.energy.CLASS_MET.DrivingCar = 1.4 -- #2632
K.energy.CLASS_MET.Default = 1.5 -- #2632
K.energy.CLASS_MET.LightDomestic = 1.6 -- #2632
K.energy.CLASS_MET.Walking2kmh = 1.9 -- #2632
K.energy.CLASS_MET.HeavyDomestic = 2.0 -- #2632
K.energy.CLASS_MET.UsingTools = 2.5 -- #2632
K.energy.CLASS_MET.DefaultExercise = 3.0 -- #2632
K.energy.CLASS_MET.Walking5kmh = 3.1 -- #2632
K.energy.CLASS_MET.LightWork = 3.2 -- #2632
K.energy.CLASS_MET.MediumWork = 3.9 -- #2632
K.energy.CLASS_MET.JumpFence = 4.0 -- #2632
K.energy.CLASS_MET.DiggingSpade = 5.5 -- #2632
K.energy.CLASS_MET.HeavyWork = 6.0 -- #2632
K.energy.CLASS_MET.Fitness = 6.0 -- #2632
K.energy.CLASS_MET.Running10kmh = 6.9 -- #2632
K.energy.CLASS_MET.ClimbRope = 8.0 -- #2632
K.energy.CLASS_MET.ForestryAxe = 8.0 -- #2632
K.energy.CLASS_MET.FitnessHeavy = 9.0 -- #2632
K.energy.CLASS_MET.Running15kmh = 9.5 -- #2632
K.energy.CLASS_MET.MAX = 10.3 -- #2632

-- The same names in ascending engine value, for classOf's bucketing loop. Equal values keep the
-- plan's order (HeavyWork before Fitness, ClimbRope before ForestryAxe), and the first wins a tie.
-- The cost of the tie rule: an 8.0 rate classifies as ClimbRope, so COMPENDIUM.ForestryAxe (6.5) is
-- unreachable through classOf and chopping bills 8.0; a 6.0 as HeavyWork, so Fitness's 6.0 is reached
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
K.energy.COMPENDIUM.Sleeping = 1.0 -- S0018
K.energy.COMPENDIUM.SeatedResting = 1.0 -- S0019
K.energy.COMPENDIUM.StandingAtRest = 1.3 -- S0020
K.energy.COMPENDIUM.SedentaryActivity = 1.5 -- S0019 (sitting fidgeting)
K.energy.COMPENDIUM.DrivingCar = 1.4 -- engine value #2632, no Compendium row
K.energy.COMPENDIUM.Default = 1.3 -- S0020 (standing quietly; a ruling)
K.energy.COMPENDIUM.LightDomestic = 1.6 -- engine value #2632, no Compendium row
K.energy.COMPENDIUM.HeavyDomestic = 2.0 -- engine value #2632, no Compendium row
K.energy.COMPENDIUM.UsingTools = 2.5 -- S0040 (carpentry light)
K.energy.COMPENDIUM.DefaultExercise = 3.0 -- engine value #2632, no Compendium row
K.energy.COMPENDIUM.Walking2kmh = 1.9 -- engine value #2632, no Compendium row (none below 3.2 km/h)
K.energy.COMPENDIUM.Walking5kmh = 3.8 -- S0023
K.energy.COMPENDIUM.LightWork = 3.0 -- S0040 (hammering nails)
K.energy.COMPENDIUM.MediumWork = 4.0 -- S0040 (construction outside, remodeling)
K.energy.COMPENDIUM.HeavyWork = 6.0 -- S0040 (home repair vigorous)
K.energy.COMPENDIUM.JumpFence = 4.0 -- engine value #2632, no Compendium row
K.energy.COMPENDIUM.DiggingSpade = 5.0 -- S0041 (digging general)
K.energy.COMPENDIUM.Fitness = 6.0 -- engine value #2632, no Compendium row for the class; a set minute bills its exercise's EXERCISE_MET, and this flat value only when the type is unrecorded or unknown (K.energy.exerciseMet)
K.energy.COMPENDIUM.FitnessHeavy = 9.0 -- engine value #2632, no Compendium row (no resistance-exercise row)
K.energy.COMPENDIUM.Running10kmh = 9.3 -- S0029
K.energy.COMPENDIUM.ClimbRope = 8.0 -- S0043 (rock climbing)
K.energy.COMPENDIUM.ForestryAxe = 6.5 -- S0038 (chopping vigorous)
K.energy.COMPENDIUM.Running15kmh = 14.8 -- S0032's 16.1 km/h row applied to the 15 km/h class (MAX is the sprint class; S0034; spec § 7 item 3)
K.energy.COMPENDIUM.MAX = 14.8 -- S0032, extrapolated to the sprint class (S0034; spec § 7 item 3)

-- The timed-action band METs keyed by the action's caloriesModifier; 1 has no entry.
-- #2720/#2638 the bands; 3 is the Fitness class value.
K.energy.BAND_MET = {}
K.energy.BAND_MET[0.5] = 1.0 -- S0019 (sitting quietly: read, research, rest)
K.energy.BAND_MET[2] = 2.5 -- S0040 (carpentry light)
K.energy.BAND_MET[3] = 6.0 -- engine Fitness class value #2632
K.energy.BAND_MET[4] = 4.3 -- S0040 (carpentry moderate)
K.energy.BAND_MET[5] = 5.5 -- S0041 (shovelling dirt or mud)
K.energy.BAND_MET[8] = 7.0 -- S0040 (carpentry heavy)

-- The Compendium bill per vanilla Fitness exercise (C-2; spec § 3), keyed by ISFitnessAction's exeDataType
-- (the install's media/lua/shared/Definitions/FitnessExercises.lua), which NR_Server_Fitness.lua records server-side at
-- the set's start. Each type takes the general or moderate code of its pair, a game choice (Angus 2026-10-13), but burpees
-- the one code naming them; each line names the code not chosen. A set minute with no recorded or no known type bills COMPENDIUM.Fitness
-- (K.energy.exerciseMet), and NR_Server_Metabolism counts it.
K.energy.EXERCISE_MET = {}
K.energy.EXERCISE_MET.squats = 3.0 -- S1898 (02056, body weight resistance exercises, general); game choice: general over the high-intensity 02057 (6.5, S1899)
K.energy.EXERCISE_MET.pushups = 3.8 -- S1896 (02022, calisthenics, moderate effort); game choice: moderate over the vigorous 02020 (7.5, S1895)
K.energy.EXERCISE_MET.situp = 3.8 -- S1896 (02022, calisthenics, moderate effort); game choice: moderate over the vigorous 02020 (7.5, S1895) and the light 02024 (S1897)
K.energy.EXERCISE_MET.burpees = 7.5 -- S1895 (02020, calisthenics, vigorous effort: the one code that names burpees); game choice: the paced set's code over the interval-protocol HIIT 02214 (11.0, S1903)
K.energy.EXERCISE_MET.barbellcurl = 3.5 -- S1902 (02054, resistance training, multiple exercises, 8-15 reps at varied resistance), an approximate match (no curl code); game choice: over the vigorous body building 02050 (6.0, S1900)
K.energy.EXERCISE_MET.dumbbellpress = 3.5 -- S1902 (02054, resistance training, multiple exercises, 8-15 reps at varied resistance), an approximate match (no press code); game choice: over the vigorous body building 02050 (6.0, S1900)
K.energy.EXERCISE_MET.bicepscurl = 3.5 -- S1902 (02054, resistance training, multiple exercises, 8-15 reps at varied resistance), an approximate match (no curl code); game choice: over the vigorous body building 02050 (6.0, S1900)

-- The Compendium load-walking floors: {load threshold kg, MET}, ascending.
-- 5 lb = 2.3 kg, 15 lb = 6.8 kg, 50 lb = 22.7 kg.
-- the engine's inventory weight unit is read as kilograms (a game choice; no row); the thresholds are S0035's lb bands in kg
K.energy.LOAD_FLOOR = {
    { 2.3, 4.0 }, -- S0035: carrying 5-14 lb, moderate pace
    { 6.8, 4.5 }, -- S0035: carrying 15-155 lb, slow pace
    { 22.7, 6.5 }, -- S0035: carrying 50-150 lb, moderate pace
}

-- The billing constants: the falling gate's threshold (K.energy.rateFalling) and the after-burn pool's
-- fraction, release constant and floor (K.energy.epoc).
K.energy.FALL_EPS = 1e-4 -- game choice (Plan 11f C-17): the drop in the raw engine rate, MET per sample, that counts as falling; below it the gate leaves the rate's class (a tail within 1e-4 of its asymptote already classes as its target)
K.energy.EPOC_F = 0.10 -- game choice (Plan 11f C-17): the fraction f of the minute's net exercise kcal the pool takes. It lies inside S1775's 6-15 %, below S1777's 15.2 %, above S1779's trained mean of 4.8 % and below S1783's vigorous 37 %. The rows' denominators differ (S1779's net total O2 cost includes the EPOC, S1777's total exercise O2 is not called net or gross, and S1783's is net exercise kcal), so the comparison is approximate
K.energy.EPOC_TAU_H = 0.5 -- game choice (Plan 11f C-17): the release time constant, game hours, with no fitted constant behind it (S1798 stays open); it releases about 86 % of a pool within 1 h and about 98 % within 2 h. The rows bound it only loosely: expenditure is at or below baseline by 31-60 min after calisthenics (S1796), and oxygen uptake stays raised for 30-60 min after HIFT (S1797); after resistance work it returns to control in the last 30 min of 2 h (S1790) and is still above control at 105-120 min after heavy sets (S1791); after long or vigorous aerobic work it stays raised for 12-14 h (S1777, S1783). The constant therefore fits the bodyweight rows and front-loads the release after resistance and hard aerobic work
K.energy.EPOC_FLOOR_KCAL = 1e-6 -- game choice (Plan 11f close fix): a pool under this is released whole and removed from the record

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
    return target / (1 + 0.35 * f * f) -- #2649
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

-- The MET expenditure bills: the class's Compendium value (unknown reads 1.3, standing quietly);
-- not moving, raised to the timed-action band (#0462: vanilla bills the modifier only when not
-- moving); walking, raised to the load-walking floor. exMet (optional) is a set minute's exercise MET
-- (K.energy.exerciseMet), billed as it stands: no band or load floor lifts it.
function K.energy.activityMet(className, moving, modifier, loadKg, exMet)
    if exMet ~= nil then
        return exMet
    end
    local met = K.energy.COMPENDIUM[className] or 1.3 -- S0020
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

-- One expenditure step of dtM game minutes (the caller clamps dtM to [0, 60]; offline time is not
-- integrated). REE per minute, reduced by adaptive thermogenesis, times the cold multiplier at rest
-- (clamped to [1, COLD_MAX]); activity above MET_REST times total mass per hour. Mutates body's day
-- accumulators, balance and trailing-24 h window (ee and ex, body.trail's current hour); returns the energy spent
-- and the activity part. Beside actKcalDay (net activity above 1 MET) it banks exKcalDay, the MET above the idle
-- class (COMPENDIUM.Default, 1.3) times total mass per hour: the exercise energy availability subtracts.
function K.energy.minute(body, met, resting, coldMult, dtM)
    local coldK = 1
    if resting then
        coldK = K.clamp(coldMult, 1, K.energy.COLD_MAX)
    end
    local reeMin = K.energy.ree(body.lm) / 1440 * (1 - body.at) * coldK
    local actMin = K.max(met - K.energy.MET_REST, 0) * (body.fm + body.lm) / 60
    local ee = (reeMin + actMin) * dtM
    local act = actMin * dtM
    local ex = K.max(met - K.energy.COMPENDIUM.Default, 0) * (body.fm + body.lm) / 60 * dtM
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
-- exercise minute; while the rate falls with no exercise and no movement, the idle class (Default, COMPENDIUM 1.3) for
-- any class billing above it; while it falls on the move, at most Walking5kmh; otherwise the rate's own class. Every
-- other activity keeps the engine's lag, so a walk, a chop or a fight still under-bills its rise. The function names
-- the class only: getCurrentExe cannot say which exercise (#2180, #2901), so the adapter bills a set minute at the MET
-- of the type NR_Server_Fitness.lua recorded at the set's start (K.energy.exerciseMet over EXERCISE_MET), or the flat
-- Fitness class (6.0) when no known type is recorded; the writer reads every set minute as resistance-vigorous from
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
