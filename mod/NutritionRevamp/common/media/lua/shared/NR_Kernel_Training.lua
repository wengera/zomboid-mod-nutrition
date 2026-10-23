-- NR_Kernel_Training.lua -- the aerobic training signal: the ENGINE's own MET above its resting floor banked as
-- MET-minutes (never mixed with expenditure's Compendium METs), sorted into two intensity bands with a one-off credit
-- per climb, closed daily into the seven-day band ring. The Strength signal is the AddXP capture's, not this file's.
local K = NutritionRevamp.kernel
K.training = {}

-- Every dial's meaning and source is its row in NR_Data_Dials.lua.
K.training.MET_FLOOR = K.dials.get("training.MET_FLOOR")

K.training.LOAD_MULT = { 1, 1.5, 1.9, 2.3, 2.8 } -- VANILLA #2255 by HEAVY_LOAD level 0-4

K.training.MASS_REF = 80 -- VANILLA #0453 weight/80

K.training.BAND1_MET = K.dials.get("training.BAND1_MET")
K.training.BAND2_MET = K.dials.get("training.BAND2_MET")

K.training.CLIMB_MET = { JumpFence = K.dials.get("training.CLIMB_MET.JumpFence"), ClimbRope = K.dials.get("training.CLIMB_MET.ClimbRope") }

K.training.HARD_DAY_MIN = K.dials.get("training.HARD_DAY_MIN")

function K.training.metMinutes(engineMet, heavyLoadLevel, w, dtM)
    local level = math.floor(K.clamp(heavyLoadLevel, 0, 4))
    local above = K.max(engineMet - K.training.MET_FLOOR, 0)
    return above * K.training.LOAD_MULT[level + 1] * (w / K.training.MASS_REF) * dtM
end

-- 2 also while exercising or swiping.
function K.training.band(engineMet, exercising, swiping)
    if engineMet >= K.training.BAND2_MET or exercising or swiping then
        return 2
    end
    if engineMet >= K.training.BAND1_MET then
        return 1
    end
    return 0
end

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

-- A nil or unknown class credits 0.
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

-- Values are copied slot to slot, so every slot stays its own table.
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
