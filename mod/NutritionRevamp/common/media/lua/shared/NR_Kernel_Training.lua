-- NR_Kernel_Training.lua -- the body model's training signal: the aerobic side banks the
-- ENGINE's own MET value above its resting floor as MET-minutes (spec § 7 item 35; the second of the
-- two MET tables, never mixed with expenditure's Compendium METs) and sorts each minute into the two
-- intensity bands, with a one-off credit per climb. The day accumulators close into the seven-day band
-- ring. (The resistance side went in Plan 13 Task 12, ruling 13-18: the Strength signal is the AddXP
-- capture's, K.strength.signalClose.)
-- Pure: numbers and Lua tables in, numbers, booleans and Lua tables out, no Java. Slow-clock code with
-- no fast region, so math.floor and the bounded numeric `for` over the kernel's own tables
-- are allowed. This file sorts after NR_Kernel.lua, and every K.clamp / K.max reference is at call time.
local K = NutritionRevamp.kernel
K.training = {}

-- The engine's resting MET floor; MET-minutes bank only what the engine reads above it.
K.training.MET_FLOOR = 1.5 -- Metabolics.Default; spec § 7 item 35

-- Vanilla's heavy-load multipliers indexed by HEAVY_LOAD level 0-4 (index level + 1).
K.training.LOAD_MULT = { 1, 1.5, 1.9, 2.3, 2.8 } -- #2255 by HEAVY_LOAD level 0-4

-- The mass reference the MET-minutes scale by (weight / 80).
K.training.MASS_REF = 80 -- #0453 weight/80

-- The intensity bands' engine-MET thresholds.
K.training.BAND1_MET = 6.0 -- game choice § 7 item 31
K.training.BAND2_MET = 9.0 -- game choice § 7 item 31

-- The engine MET credited once per climb, by the climb state's Metabolics class.
K.training.CLIMB_MET = { JumpFence = 4.0, ClimbRope = 8.0 } -- #2632

-- The band-2 minutes that make a day a hard day.
K.training.HARD_DAY_MIN = 10 -- HARD_DAY_MIN 10, endurance report

-- MET-minutes over dtM minutes: the engine MET above the floor, times the heavy-load multiplier
-- (level clamped 0-4), times weight over the mass reference.
function K.training.metMinutes(engineMet, heavyLoadLevel, w, dtM)
    local level = math.floor(K.clamp(heavyLoadLevel, 0, 4))
    local above = K.max(engineMet - K.training.MET_FLOOR, 0)
    return above * K.training.LOAD_MULT[level + 1] * (w / K.training.MASS_REF) * dtM
end

-- The intensity band: 2 at or above BAND2_MET or while exercising or swiping, 1 at or above BAND1_MET,
-- else 0.
function K.training.band(engineMet, exercising, swiping)
    if engineMet >= K.training.BAND2_MET or exercising or swiping then
        return 2
    end
    if engineMet >= K.training.BAND1_MET then
        return 1
    end
    return 0
end

-- One sample: bank the MET-minutes into metMinDay; band >= 1 adds dtM to band1Day, band 2 adds dtM
-- to band2Day too. Returns the band.
function K.training.sample(body, engineMet, heavyLoadLevel, w, exercising, swiping, dtM)
    body.metMinDay = body.metMinDay + K.training.metMinutes(engineMet, heavyLoadLevel, w, dtM)
    local b = K.training.band(engineMet, exercising, swiping)
    if b >= 1 then
        body.band1Day = body.band1Day + dtM
    end
    if b == 2 then
        body.band2Day = body.band2Day + dtM
    end
    return b
end

-- A climb's one-off credit: (CLIMB_MET[className] - MET_FLOOR) * w / MASS_REF into metMinDay; a nil or
-- unknown class credits 0. Returns the credit.
function K.training.climbCredit(body, className, w)
    local met = nil
    if className ~= nil then
        met = K.training.CLIMB_MET[className]
    end
    if met == nil then
        return 0
    end
    local credit = (met - K.training.MET_FLOOR) * (w / K.training.MASS_REF)
    body.metMinDay = body.metMinDay + credit
    return credit
end

-- Close the day: shift the seven-day band ring one slot (bandWeek[1] the oldest), write the day's
-- {band1Day, band2Day} into slot 7, and zero the day accumulators. Values are copied slot to slot, so
-- every slot stays its own table. Returns the body.
function K.training.closeDay(body)
    local ring = body.bandWeek
    local n = K.body.WEEK_N
    for i = 1, n - 1 do
        ring[i][1] = ring[i + 1][1]
        ring[i][2] = ring[i + 1][2]
    end
    ring[n][1] = body.band1Day
    ring[n][2] = body.band2Day
    body.metMinDay = 0
    body.band1Day = 0
    body.band2Day = 0
    return body
end

-- The week: m1 = the band-1 minutes summed over the ring, hardDays = the days with band-2 minutes
-- >= HARD_DAY_MIN.
function K.training.weekMinutes(body)
    local ring = body.bandWeek
    local m1 = 0
    local hardDays = 0
    for i = 1, K.body.WEEK_N do
        m1 = m1 + ring[i][1]
        if ring[i][2] >= K.training.HARD_DAY_MIN then
            hardDays = hardDays + 1
        end
    end
    return m1, hardDays
end
