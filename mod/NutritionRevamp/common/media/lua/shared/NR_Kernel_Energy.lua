-- NR_Kernel_Energy.lua -- the body model's expenditure and energy state (Plan 3): resting energy
-- expenditure off lean mass, adaptive thermogenesis, the two MET tables (the engine's Metabolics values,
-- read to classify the thermoregulator's target, and the Compendium METs expenditure bills), the
-- timed-action band METs, the Compendium load-walking floors, the engine load factor divided out, the
-- per-minute expenditure and intake accumulators on record.body, the trailing-24 h balance and the
-- energy state the writer's hunger term reads.
-- Pure: numbers and Lua tables in, numbers, strings and Lua tables out, no Java. Slow-clock code with
-- no fast region, so math.exp, math.abs and the bounded numeric `for` over the kernel's own tables are
-- allowed. This file sorts after NR_Kernel.lua, and every K.clamp / K.max reference is at call time.
local K = NutritionRevamp.kernel
K.energy = {}

-- Resting energy expenditure off lean mass: REE (kcal/d) = REE_A * LM + REE_B (ruling 5).
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
K.energy.COMPENDIUM.Fitness = 6.0 -- engine value #2632, no Compendium row (no resistance-exercise row)
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

-- The Compendium load-walking floors: {load threshold kg, MET}, ascending.
-- 5 lb = 2.3 kg, 15 lb = 6.8 kg, 50 lb = 22.7 kg.
-- the engine's inventory weight unit is read as kilograms (a game choice; no row); the thresholds are S0035's lb bands in kg
K.energy.LOAD_FLOOR = {
    { 2.3, 4.0 }, -- S0035: carrying 5-14 lb, moderate pace
    { 6.8, 4.5 }, -- S0035: carrying 15-155 lb, slow pace
    { 22.7, 6.5 }, -- S0035: carrying 50-150 lb, moderate pace
}

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
-- (#2649), so load is charged once (ruling 6). A non-positive maxW reads unloaded.
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
-- moving); walking, raised to the load-walking floor (ruling 6).
function K.energy.activityMet(className, moving, modifier, loadKg)
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
-- accumulators and balance; returns the energy spent and the activity part. Beside actKcalDay (net
-- activity above 1 MET, the expenditure quantity) it banks exKcalDay, the MET above the idle class
-- (COMPENDIUM.Default, 1.3) times total mass per hour: the exercise energy availability subtracts.
function K.energy.minute(body, met, resting, coldMult, dtM)
    local coldK = 1
    if resting then
        coldK = K.clamp(coldMult, 1, K.energy.COLD_MAX)
    end
    local reeMin = K.energy.ree(body.lm) / 1440 * (1 - body.at) * coldK
    local actMin = K.max(met - K.energy.MET_REST, 0) * (body.fm + body.lm) / 60
    local ee = (reeMin + actMin) * dtM
    local act = actMin * dtM
    local exMin = K.max(met - K.energy.COMPENDIUM.Default, 0) * (body.fm + body.lm) / 60
    body.eeDay = body.eeDay + ee
    body.actKcalDay = body.actKcalDay + act
    body.exKcalDay = body.exKcalDay + exMin * dtM -- S0691: EA is intake minus EXERCISE expenditure per kg FFM; the idle class is not exercise
    body.ebDay = body.inDay - body.eeDay
    return ee, act
end

-- One intake step: the absorbed vector (Plan 2's per-minute output) into the day accumulators.
function K.energy.intake(body, absorbed, dtM)
    body.inDay = body.inDay + absorbed.calories
    body.pDay = body.pDay + absorbed.proteins
    body.carbDay = body.carbDay + absorbed.carbs
    body.lipDay = body.lipDay + absorbed.lipids
    body.ebDay = body.inDay - body.eeDay
end

-- The trailing-24 h balance: today's balance plus yesterday's (eb7[7], the most recent closed day)
-- weighted by the share of the 24 h since the last close still to run (K.body.blend24; the caller
-- passes ageH - body.lastCloseAgeH, so the window follows the day close, not the clock). A game choice.
function K.energy.eb24h(body, hoursSinceClose)
    return K.body.blend24(body.ebDay, body.eb7[7], hoursSinceClose)
end

-- The energy state the hunger term reads: 1 neutral, up under deficit, fat depletion and glycogen
-- depletion, down under surplus, clamped to [0.5, 2.0] (ruling 14, a game choice). g is the muscle
-- glycogen fraction (0-1, record.acute.g); omitted it reads 1, the neutral every Plan 3 caller passed.
K.energy.GLYC_STATE_K = 0.3 -- game choice, Plan 4 Task 13 ruling; no row (S1109 is the exertional trigger, not this coupling)

function K.energy.state(eb24h, fatDep, g)
    if g == nil then
        g = 1
    end
    return K.clamp(1 + 0.5 * K.clamp(-eb24h / 1500, -1, 1) + 0.5 * fatDep + K.energy.GLYC_STATE_K * (1 - g), 0.5, 2.0) -- ruling 14
end

-- Plan 11c Task 4b (spec § 5c, ruling 11c-29): no same-day compensation for exercise. A deficit made by exercise
-- does not raise appetite the same day, while an equal one made by food restriction does (S1312; S1310, S1311,
-- S1313); intake makes up about 30 % of an exercise deficit over days 3-16 (S1318) and more over months (S1320,
-- S1321, S1322). L is the exercise expenditure rate in kcal per day that appetite has caught up with: a first-order
-- lag of the exercise kcal (exKcalDay's quantity, the MET above the idle class). The split of a deficit into an
-- exercise share and a food share is a game choice no row defines. Appended so no line above moves.
K.energy.EX_LAG_TAU_D = 24 -- game choice, fitted in Task 4b (Plan 11c) (S1335 open): the lag's time constant in days, fitted to S1318 (Whybrow 2008: about 30 % of the exercise deficit compensated over days 3-16) and about 0 the same day (S1312)

-- One lag step of dtH game hours with exKcal exercise kcal spent in it: L relaxes toward the step's rate (exKcal x 24
-- / dtH kcal per day). Nothing for no time; a non-finite L reads 0 and a negative or non-finite exKcal reads none.
function K.energy.exerciseLag(L, exKcal, dtH)
    if L - L ~= 0 then
        L = 0
    end
    if not (dtH > 0) then
        return L
    end
    if exKcal - exKcal ~= 0 or exKcal < 0 then
        exKcal = 0
    end
    local k = math.exp(-dtH / (K.energy.EX_LAG_TAU_D * 24))
    return L * k + exKcal * 24 / dtH * (1 - k)
end

-- The exercise deficit, kcal per day, that enters the energy state: L, non-negative and finite.
function K.energy.lagged(L)
    if L - L ~= 0 or L < 0 then
        return 0
    end
    return L
end

-- The energy state the writer hands to hungerTarget: the food balance (eb24h with the window's exercise kcal ex24h
-- added back) enters at once, the exercise share only through the lag. lagged(L) >= 0 and state falls with the
-- balance, so the activity never pushes the state below that of the same intake without it (S1330, S1331, S1332).
-- A negative or non-finite ex24h reads none. A 24-h total deficit bypasses the lag on a linear ramp: with ee24h the
-- 24-h expenditure and d = -eb24h / ee24h, the weight w = clamp((d - EX_BYPASS_LO) / (EX_BYPASS_HI - EX_BYPASS_LO), 0, 1)
-- moves the lag w of the way to ex24h (heavy work in a deficit raises hunger within days, S1325; ordinary exercise
-- stays compensated over weeks, S1312, S1318); it only ever raises the lag, so the never-below property holds. An
-- ee24h that is nil, non-finite or not positive bypasses nothing.
K.energy.EX_BYPASS_LO = 0.30 -- game choice, ruling 11c-32 as amended (Plan 11c): the 24-h total-deficit share of the 24-h expenditure at which the exercise lag starts to be bypassed; S1325 (Karl 2021) gives the direction, S1312 (King 2011, steady state) and S1318 (Whybrow 2008, 26-28 % arms compensate ~30 %) bound it from below
K.energy.EX_BYPASS_HI = 0.45 -- game choice, ruling 11c-32 as amended: the share at which the bypass is whole
function K.energy.activityState(eb24h, ex24h, L, fatDep, g, ee24h)
    local ex = 0
    if ex24h - ex24h == 0 and ex24h > 0 then
        ex = ex24h
    end
    local lag = K.energy.lagged(L)
    if ee24h ~= nil and ee24h - ee24h == 0 and ee24h > 0 and eb24h - eb24h == 0 and lag < ex then
        local d = -eb24h / ee24h
        local w = K.clamp((d - K.energy.EX_BYPASS_LO) / (K.energy.EX_BYPASS_HI - K.energy.EX_BYPASS_LO), 0, 1)
        lag = lag + w * (ex - lag)
    end
    return K.energy.state(eb24h + ex - lag, fatDep, g)
end
