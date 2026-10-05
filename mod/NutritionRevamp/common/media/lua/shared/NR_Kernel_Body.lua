-- NR_Kernel_Body.lua -- the body model's pure pieces (Plan 3): the band-anchored split of a starting
-- weight into fat and lean mass, the record.body table the adapter creates at first sight, the
-- vanilla weight band, the three direction flags off the 7-day trend, and the legacy macro-mirror maps
-- that turn the mod's trailing-24 h figures into the vanilla Nutrition stores other mods read.
-- Pure: numbers and Lua tables in, numbers, strings and Lua tables out, no Java. Slow-clock code with
-- no fast region, so math.floor and the bounded numeric `for` over the kernel's own tables are allowed.
-- This file sorts after NR_Kernel.lua, and every K.clamp / K.min reference is at call time.
local K = NutritionRevamp.kernel
K.body = {}

-- The band-anchored fat-fraction table: body weight anchors (kg) and the fat fraction at each, by sex
-- (index 1 male, 2 female); piecewise-linear between anchors, flat beyond the first and last.
K.body.ANCHORS_W = { 50, 60, 70, 80, 95, 105 } -- S1051 design-phase-v1: the band-anchored split; a game choice until the row settles
K.body.BF_MALE = { 0.06, 0.09, 0.13, 0.18, 0.27, 0.33 } -- S1051 design-phase-v1: the band-anchored split; a game choice until the row settles
K.body.BF_FEMALE = { 0.15, 0.19, 0.23, 0.28, 0.35, 0.40 } -- S1051 design-phase-v1: the band-anchored split; a game choice until the row settles

-- The fat-fraction floor by sex (index 1 male, 2 female) and the common ceiling.
K.body.BF_MIN = { 0.04, 0.12 } -- S1051 design-phase-v1: the band-anchored split; a game choice until the row settles
K.body.BF_MAX = 0.55 -- S1051 design-phase-v1: the band-anchored split; a game choice until the row settles

-- The creation-build offsets on the fat fraction, added for each build flag that is true.
K.body.BUILD_OFFSET = {}
K.body.BUILD_OFFSET.athletic = -0.04 -- S1051 design-phase-v1: the band-anchored split; a game choice until the row settles
K.body.BUILD_OFFSET.fit = -0.02 -- S1051 design-phase-v1: the band-anchored split; a game choice until the row settles
K.body.BUILD_OFFSET.outOfShape = 0.02 -- S1051 design-phase-v1: the band-anchored split; a game choice until the row settles
K.body.BUILD_OFFSET.unfit = 0.04 -- S1051 design-phase-v1: the band-anchored split; a game choice until the row settles
K.body.BUILD_OFFSET.strong = -0.02 -- S1051 design-phase-v1: the band-anchored split; a game choice until the row settles
K.body.BUILD_OFFSET.stout = -0.01 -- S1051 design-phase-v1: the band-anchored split; a game choice until the row settles

-- The build flag names, walked in order by split (a numeric `for` over the kernel's own list).
K.body.BUILD_KEYS = { "athletic", "fit", "outOfShape", "unfit", "strong", "stout" }

-- The weight clamp split applies before it reads the table (kg).
K.body.W_MIN = 35 -- design-phase-v1 game choice: a sanity clamp on the read weight, no row
K.body.W_MAX = 200 -- design-phase-v1 game choice: a sanity clamp on the read weight, no row

-- The piecewise-linear fat fraction at weight w for sex (1 male, 2 female), flat beyond the end
-- anchors. Each segment whose lower anchor w exceeds overwrites the result with its own reading at
-- min(w, upper anchor), so the last such segment wins and w past the top anchor reads the top value.
function K.body.interp(w, sex)
    local xs = K.body.ANCHORS_W
    local ys = K.body.BF_MALE
    if sex == 2 then
        ys = K.body.BF_FEMALE
    end
    local bf = ys[1]
    for i = 2, #xs do
        if w > xs[i - 1] then
            bf = ys[i - 1] + (ys[i] - ys[i - 1]) * (K.min(w, xs[i]) - xs[i - 1]) / (xs[i] - xs[i - 1])
        end
    end
    return bf
end

-- Split weight w into fat mass, lean mass and the fat fraction: w clamped to [W_MIN, W_MAX]; the
-- fraction is interp plus the offsets of every true build flag, clamped to [BF_MIN[sex], BF_MAX].
-- build is a table of booleans keyed by BUILD_KEYS (a missing key is false).
function K.body.split(w, sex, build)
    local wc = K.clamp(w, K.body.W_MIN, K.body.W_MAX)
    local off = 0
    local keys = K.body.BUILD_KEYS
    for i = 1, #keys do
        local k = keys[i]
        if build[k] then
            off = off + K.body.BUILD_OFFSET[k]
        end
    end
    local bf = K.clamp(K.body.interp(wc, sex) + off, K.body.BF_MIN[sex], K.body.BF_MAX)
    local fm = wc * bf
    local lm = wc - fm
    return fm, lm, bf
end

-- The vanilla weight band of weight w (kg): its trait thresholds (#0531, #0155). Normal is the open
-- interval 75 < w < 85.
function K.body.band(w)
    if w >= 100 then
        return "obese" -- #0531, #0155
    end
    if w >= 85 then
        return "overweight" -- #0531, #0155
    end
    if w > 75 then
        return "normal" -- #0531, #0155
    end
    if w > 65 then
        return "underweight" -- #0531, #0155
    end
    if w > 50 then
        return "veryUnderweight" -- #0531, #0155
    end
    return "emaciated" -- #0531, #0155
end

-- The three direction flags off the 7-day trend in kg per day: weight increasing, increasing a lot,
-- decreasing. Strict inequalities, so a trend exactly on a threshold raises nothing.
function K.body.flags(trendKgPerDay)
    return trendKgPerDay > 0.02, trendKgPerDay > 0.10, trendKgPerDay < -0.02 -- game choice, ruling 17
end

-- The 7-day trend (kg/day): today's weight minus the oldest ring slot, over 7. The adapter rotates
-- the ring at day close; a fresh ring holds the creation weight, so the trend starts at 0.
function K.body.trend(mass7, w)
    return (w - mass7[1]) / 7
end

-- The trailing-24 h blend: today's figure plus yesterday's (the most recent closed day) weighted by
-- the share of the 24 h since the last close still to run, clamped to [0, 1] (a game choice). Both
-- K.energy.eb24h and the legacy mirror's protein, carbohydrate and lipid blends read it.
function K.body.blend24(today, yesterday, hoursSinceClose)
    return today + yesterday * K.clamp(1 - hoursSinceClose / 24, 0, 1)
end

-- The legacy calorie store: the trailing-24 h energy balance clamped to the vanilla store's range.
function K.body.mapCalories(eb24h)
    return K.clamp(eb24h, -2200, 3700) -- #0022
end

-- The legacy protein store from the trailing-24 h protein intake per kg body weight (g/kg/d):
-- P <= 0.5 reads -400; 0.5 < P < 0.8 runs linearly -300 .. 0; 0.8 <= P <= 1.6 runs linearly 0 .. 150;
-- P > 1.6 reads 200; clamped to the store's [-500, 1000].
-- ruling 13: the x1.5 arm (50 < p < 300, #2112) opens at P ~ 1.07.
function K.body.mapProteins(pPerKgDay)
    local m = 200 -- game choice, ruling 13
    if pPerKgDay <= 0.5 then
        m = -400 -- game choice, ruling 13
    elseif pPerKgDay < 0.8 then
        m = -300 + 300 * (pPerKgDay - 0.5) / 0.3 -- game choice, ruling 13
    elseif pPerKgDay <= 1.6 then
        m = 150 * (pPerKgDay - 0.8) / 0.8 -- game choice, ruling 13
    end
    return K.clamp(m, -500, 1000) -- #0023
end

-- The legacy carbohydrate store: the trailing-24 h carbohydrate intake (g) minus a 300 g reference.
function K.body.mapCarbs(gIn24h)
    return K.clamp(gIn24h - 300, -500, 1000) -- game choice, ruling 13
end

-- The legacy lipid store: the trailing-24 h lipid intake (g) minus a 70 g reference.
function K.body.mapLipids(gIn24h)
    return K.clamp(gIn24h - 70, -500, 1000) -- game choice, ruling 13
end

-- A fresh record.body at first sight: weight w (kg), sex (1 male, 2 female), the build flags, the
-- Strength level l0, the creation-trait carry factor, the responder constant r and the world age in
-- hours. Numbers, one string (band) and tables of numbers only (#1495: global modData refuses
-- functions and userdata). The rings are built with numeric `for`; every bandWeek slot is its own
-- table. p7, carb7 and lip7 hold each closed day's protein, carbohydrate and lipid grams (slot 7 is
-- yesterday), the legacy mirror's trailing-24 h blend. The rings and the band read the clamped weight
-- split reads (fm + lm), not the raw w. lastCloseAgeH is the world age of the last day close (the
-- creation age until the first close); pPrevKg is the closed day's protein per kg, neutral at birth.
function K.body.new(w, sex, build, l0, traitCarry, r, ageH)
    local fm, lm = K.body.split(w, sex, build)
    local wc = K.clamp(w, K.body.W_MIN, K.body.W_MAX)
    local day = math.floor(ageH / 24)
    local body = {}
    body.bv = 1
    body.fm = fm
    body.lm = lm
    body.fm0 = fm
    body.lm0 = lm
    body.lm0dis = lm
    body.fmRef = fm
    body.l0 = l0
    body.sex = sex
    body.r = r
    body.traitCarry = traitCarry
    body.bornAge = ageH
    body.lastAgeH = ageH
    body.lastCloseAgeH = ageH
    body.strAgeH = ageH
    body.at = 0
    body.dayIndex = day
    body.inDay = 0
    body.eeDay = 0
    body.ebDay = 0
    body.actKcalDay = 0
    body.pDay = 0
    body.carbDay = 0
    body.lipDay = 0
    body.alcDay = 0
    body.eb7 = {}
    body.mass7 = {}
    body.bandWeek = {}
    body.p7 = {}
    body.carb7 = {}
    body.lip7 = {}
    for i = 1, 7 do
        body.eb7[i] = 0
        body.mass7[i] = wc
        body.bandWeek[i] = { 0, 0 }
        body.p7[i] = 0
        body.carb7[i] = 0
        body.lip7[i] = 0
    end
    body.eb24h = 0
    body.vStr = 0
    body.vHyp = 0
    body.vStrHigh = 0
    body.metMinDay = 0
    body.band1Day = 0
    body.band2Day = 0
    body.n = 0
    body.nPeak = 0
    body.tPeakD = day
    body.nHist = {}
    for i = 1, 14 do
        body.nHist[i] = 0
    end
    body.cumDef = 0
    body.tDisuse = 0
    body.shownL = l0
    body.riseHeldH = 0
    body.lastFallAge = ageH
    body.delta = traitCarry
    body.band = K.body.band(wc)
    body.tac = 1.0
    body.dmod = 1
    body.rmod = 1
    body.pPrevKg = 0.8 -- = K.aerobic.P_LOW; neutral
    body.energyState = 1
    body.mirrorLast = { 0, 0, 0, 0 }
    return body
end
