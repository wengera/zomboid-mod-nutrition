-- NR_Kernel_Training.lua -- the body model's training signal (Plan 3): the aerobic side banks the
-- ENGINE's own MET value above its resting floor as MET-minutes (spec § 7 item 35; the second of the
-- two MET tables, never mixed with expenditure's Compendium METs) and sorts each minute into the two
-- intensity bands; the resistance side turns events and loaded minutes into set-equivalents feeding
-- the strength and hypertrophy accumulators, which decay on a weekly time constant and saturate into
-- the two doses. The day accumulators close into the seven-day band ring.
-- Pure: numbers and Lua tables in, numbers, booleans and Lua tables out, no Java. Slow-clock code with
-- no fast region, so math.exp, math.floor and the bounded numeric `for` over the kernel's own tables
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

-- The accumulators' decay time constant, in days (the dose rows state weekly units).
K.training.TAU_V_DAYS = 7 -- S0576/S0577 weekly units

-- The doses' half-saturation constants, in set-equivalents.
K.training.K_STR = 4 -- S0582
K.training.K_HYP = 10 -- S0576

-- The strength weight of a set-equivalent by intensity class (load drives strength, sets hypertrophy).
K.training.W_STR = { low = 0.5, moderate = 0.8, high = 1.0 } -- S0575

-- Set-equivalents per event and per loaded or effortful minute.
K.training.S_REP_ARMS = 0.10 -- game choices § 7 item 30
K.training.S_REP_LEGS = 0.05 -- game choices § 7 item 30
K.training.S_HIT = 0.05 -- game choices § 7 item 30
K.training.S_TREE = 0.07 -- game choices § 7 item 30
K.training.S_LOAD_HIGH_PER_MIN = 0.10 -- game choices § 7 item 30
K.training.S_LOAD_MOD_PER_MIN = 0.05 -- game choices § 7 item 30
K.training.S_ACTION_MOD_PER_MIN = 0.02 -- game choices § 7 item 30
K.training.S_ACTION_HIGH_PER_MIN = 0.04 -- game choices § 7 item 30

-- The high-class accumulator level that maintains strength.
K.training.MAINTAIN_HIGH = 1 -- S0616

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

-- A resistance event of s set-equivalents per hit at intensity class `class` ("low", "moderate",
-- "high"), hits floored at 1: vStr gains the class-weighted amount, vHyp the whole amount, vStrHigh the
-- whole amount when the class is high. Returns the body.
function K.training.event(body, s, class, hits)
    local n = s * K.max(1, hits or 1)
    body.vStr = body.vStr + K.training.W_STR[class] * n
    body.vHyp = body.vHyp + n
    if class == "high" then
        body.vStrHigh = body.vStrHigh + n
    end
    return body
end

-- A loaded minute: carried / maxW >= 0.8 is a high event, >= 0.5 a moderate one, else nothing.
-- Returns the body.
function K.training.loadMinute(body, carried, maxW, dtM)
    local ratio = carried / maxW
    if ratio >= 0.8 then
        return K.training.event(body, K.training.S_LOAD_HIGH_PER_MIN * dtM, "high")
    end
    if ratio >= 0.5 then
        return K.training.event(body, K.training.S_LOAD_MOD_PER_MIN * dtM, "moderate")
    end
    return body
end

-- An effortful timed-action minute, standing still: caloriesModifier >= 8 is a high event, >= 4 a
-- moderate one; a moving character or a lighter modifier banks nothing. Returns the body.
function K.training.actionMinute(body, modifier, moving, dtM)
    if moving then
        return body
    end
    if modifier >= 8 then
        return K.training.event(body, K.training.S_ACTION_HIGH_PER_MIN * dtM, "high")
    end
    if modifier >= 4 then
        return K.training.event(body, K.training.S_ACTION_MOD_PER_MIN * dtM, "moderate")
    end
    return body
end

-- Decay the three accumulators over dtM minutes: x exp(-dtM / (TAU_V_DAYS * 1440)). Returns the body.
function K.training.decay(body, dtM)
    local d = math.exp(-dtM / (K.training.TAU_V_DAYS * 1440))
    body.vStr = body.vStr * d
    body.vHyp = body.vHyp * d
    body.vStrHigh = body.vStrHigh * d
    return body
end

-- The doses: dStr = vStr / (vStr + K_STR), dHyp = vHyp / (vHyp + K_HYP), and whether the high-class
-- accumulator maintains strength (vStrHigh >= MAINTAIN_HIGH).
function K.training.doses(body)
    local dStr = body.vStr / (body.vStr + K.training.K_STR)
    local dHyp = body.vHyp / (body.vHyp + K.training.K_HYP)
    local maintained = body.vStrHigh >= K.training.MAINTAIN_HIGH
    return dStr, dHyp, maintained
end

-- Close the day: shift the seven-day band ring one slot (bandWeek[1] the oldest), write the day's
-- {band1Day, band2Day} into slot 7, and zero the day accumulators. Values are copied slot to slot, so
-- every slot stays its own table. Returns the body.
function K.training.closeDay(body)
    local ring = body.bandWeek
    for i = 1, 6 do
        ring[i][1] = ring[i + 1][1]
        ring[i][2] = ring[i + 1][2]
    end
    ring[7][1] = body.band1Day
    ring[7][2] = body.band2Day
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
    for i = 1, 7 do
        m1 = m1 + ring[i][1]
        if ring[i][2] >= K.training.HARD_DAY_MIN then
            hardDays = hardDays + 1
        end
    end
    return m1, hardDays
end
