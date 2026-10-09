-- NR_Kernel_Body.lua -- the body model's pure pieces (Plan 3): the band-anchored split of a starting
-- weight into fat and lean mass, the record.body table the adapter creates at first sight, the
-- vanilla weight band, the three direction flags off the 7-day trend, the legacy macro-mirror maps that turn
-- the mod's trailing-24 h figures into the vanilla Nutrition stores other mods read, and the trailing-24 h window.
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

-- The trailing-24 h figures every reader takes (K.energy.eb24h, the exercise lag's ex24h and ee24h, the nutrients'
-- expenditure and carbohydrate, the legacy mirror's protein, carbohydrate and lipid) are K.body.trail24 over
-- record.body.trail (Plan 11d Task 9c, ruling C-8: the evenly-spread blend of today and the closed day read a
-- phantom deficit before breakfast; it is retired). The closed-day rings eb7, p7 and mass7 remain for the 7-day
-- readers: K.partition.deficitWeek, NR_Server_Effects' protein week and K.body.trend.
-- The window's code is at the end of this file.

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
-- table. p7 holds each closed day's protein grams (slot 7 is yesterday; NR_Server_Effects' protein
-- week). The rings and the band read the clamped weight split reads (fm + lm), not the raw w. trail is
-- the trailing-24 h window (K.body.newTrail), empty at birth; pPrevKg is the closed day's protein per
-- kg, neutral at birth.
function K.body.new(w, sex, build, l0, traitCarry, r, ageH)
    local fm, lm = K.body.split(w, sex, build)
    local wc = K.clamp(w, K.body.W_MIN, K.body.W_MAX)
    local day = math.floor(ageH / 24)
    local body = {}
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
    body.strAgeH = ageH
    body.at = 0
    body.dayIndex = day
    body.inDay = 0
    body.eeDay = 0
    body.ebDay = 0
    body.actKcalDay = 0
    body.exKcalDay = 0
    body.pDay = 0
    body.carbDay = 0
    body.lipDay = 0
    body.alcDay = 0
    body.eb7 = {}
    body.mass7 = {}
    body.bandWeek = {}
    body.p7 = {}
    for i = 1, 7 do
        body.eb7[i] = 0
        body.mass7[i] = wc
        body.bandWeek[i] = { 0, 0 }
        body.p7[i] = 0
    end
    body.trail = K.body.newTrail(ageH)
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

-- The trailing-24 h window (Plan 11d Task 9c, ruling C-8): one hourly ring per quantity, TRAIL_N slots, game hour h
-- (the floor of the world age) in slot h % TRAIL_N + 1, so a ring holds the current hour and the 24 before it. The
-- current hour accumulates each minute (trailAdd); as the clock passes an hour its slot is zeroed (trailTo). The window
-- (trail24) is the current hour so far, the 23 closed hours and the oldest hour weighted by the share of it still inside
-- the 24 h, 1 - f with f the elapsed share of the current hour: exact for a quantity spread evenly over its hour, and
-- off by at most the oldest hour's own content for a lump (a meal) inside it, for less than an hour. Intake (kcal and
-- the protein, carbohydrate and lipid grams), expenditure and exercise come in meals and bouts, so each takes a ring.
-- The closed hours' sums c are derived: rebuilt from the slots whenever the hour they were built for (ch) is not the
-- current one, so a fresh window (ch -1), a load or a heal rebuilds them at the next read. A game choice (the window's
-- hourly grain and its interpolation); no row.
K.body.TRAIL_N = 25 -- the current hour and the 24 before it
K.body.TRAIL_KEYS = { "kcal", "ee", "ex", "p", "carb", "lip" }

-- A fresh window at world age ageH: every slot 0, the closed sums 0 and unbuilt.
function K.body.newTrail(ageH)
    local t = {}
    t.at = ageH
    t.ch = -1
    t.c = {}
    local keys = K.body.TRAIL_KEYS
    for k = 1, #keys do
        local ring = {}
        for i = 1, K.body.TRAIL_N do
            ring[i] = 0
        end
        t[keys[k]] = ring
        t.c[keys[k]] = 0
    end
    return t
end

-- The slot of game hour h (an integer-valued number).
function K.body.trailSlot(h)
    return h % K.body.TRAIL_N + 1
end

-- Move window t to world age ageH: zero the slot of every hour after the last one written up to ageH's hour (the
-- whole ring at most), then stamp ageH. An age not past the window's (behind it, equal or not a number) leaves it.
function K.body.trailTo(t, ageH)
    if not (ageH > t.at) then
        return t
    end
    local h0 = math.floor(t.at)
    local h1 = K.min(math.floor(ageH), h0 + K.body.TRAIL_N)
    local keys = K.body.TRAIL_KEYS
    for h = h0 + 1, h1 do
        local s = K.body.trailSlot(h)
        for k = 1, #keys do
            t[keys[k]][s] = 0
        end
    end
    t.at = ageH
    return t
end

-- Add x to ring key's current hour.
function K.body.trailAdd(t, key, x)
    local ring = t[key]
    local s = K.body.trailSlot(math.floor(t.at))
    ring[s] = ring[s] + x
end

-- One ring's closed sum: every slot but slot cur, a non-finite slot zeroed on the way. Returns the sum and the count
-- of slots zeroed (Plan 11d Task 9d: the heal names a ring by it, K.heal.trail).
function K.body.trailRingSum(ring, cur)
    local s = 0
    local z = 0
    for i = 1, K.body.TRAIL_N do
        local x = ring[i]
        if x - x ~= 0 then
            x = 0
            ring[i] = 0
            z = z + 1
        end
        if i ~= cur then
            s = s + x
        end
    end
    return s, z
end

-- The closed hours' sums, rebuilt when they were built for another hour: each ring's sum over every slot but the
-- current hour's (K.body.trailRingSum). The rebuild zeroes a non-finite slot on its way (none is made by the step,
-- whose current-hour writes Metabolism's guard covers; the heal walks the rings first at each hour's turn and names
-- what it zeroes, K.heal.trail). Returns t.c and the count of slots this call zeroed (0 when the sums stood).
function K.body.trailClosed(t)
    local h = math.floor(t.at)
    if t.ch == h then
        return t.c, 0
    end
    local cur = K.body.trailSlot(h)
    local keys = K.body.TRAIL_KEYS
    local n = 0
    for k = 1, #keys do
        local s, z = K.body.trailRingSum(t[keys[k]], cur)
        t.c[keys[k]] = s
        n = n + z
    end
    t.ch = h
    return t.c, n
end

-- The trailing-24 h sum of ring key: the closed hours, less the share f of the oldest hour already outside the window,
-- plus the current hour so far.
function K.body.trail24(t, key)
    local c = K.body.trailClosed(t)
    local h = math.floor(t.at)
    local ring = t[key]
    return c[key] - (t.at - h) * ring[K.body.trailSlot(h + 1)] + ring[K.body.trailSlot(h)]
end

-- One absorbed vector into the window's current hour: its kcal and its protein, carbohydrate and lipid grams.
function K.body.trailIntake(t, absorbed)
    K.body.trailAdd(t, "kcal", absorbed.calories)
    K.body.trailAdd(t, "p", absorbed.proteins)
    K.body.trailAdd(t, "carb", absorbed.carbs)
    K.body.trailAdd(t, "lip", absorbed.lipids)
end
