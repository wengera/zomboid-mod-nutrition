-- NR_Kernel_Body.lua -- the body model's pure pieces: the record.body table the adapter creates (the creation
-- body of a muscle and a weight pick, K.body.create, laid by K.body.new), the three direction
-- flags off the 7-day trend, the legacy macro-mirror maps that turn the mod's trailing-24 h figures into the vanilla
-- Nutrition stores other mods read, the trailing-24 h window and the record calendar.
-- Pure: numbers and Lua tables in, numbers, strings and Lua tables out, no Java. Slow-clock code with
-- no fast region, so math.floor and the bounded numeric `for` over the kernel's own tables are allowed.
-- This file sorts after NR_Kernel.lua, and every K.clamp / K.min reference is at call time.
local K = NutritionRevamp.kernel
K.body = {}

-- The length of the seven-day rings (eb7, mass7, p7, sig7, bandWeek; slot 1 the oldest, the last yesterday).
K.body.WEEK_N = 7

-- The sex every sex-indexed table is read at (index 1 male, 2 female): the engine's sex only when the mod-wide
-- NR.SexSpecific option is on and the character is female, else male (1). record.body.sex keeps the engine's value.
function K.body.effSex(sex, specific)
    if specific == true and sex == 2 then
        return 2
    end
    return 1
end

-- The three direction flags off the 7-day trend in kg per day: weight increasing, increasing a lot,
-- decreasing. Strict inequalities, so a trend exactly on a threshold raises nothing.
K.body.TREND_KG_D = K.dials.get("body.TREND_KG_D")
K.body.TREND_LOT_KG_D = K.dials.get("body.TREND_LOT_KG_D")
function K.body.flags(trendKgPerDay)
    return trendKgPerDay > K.body.TREND_KG_D, trendKgPerDay > K.body.TREND_LOT_KG_D, trendKgPerDay < -K.body.TREND_KG_D -- ruling 17
end

-- The 7-day trend (kg/day): today's weight minus the oldest ring slot, over 7. The adapter rotates
-- the ring at day close; a fresh ring holds the creation weight, so the trend starts at 0.
function K.body.trend(mass7, w)
    return (w - mass7[1]) / 7
end

-- The trailing-24 h figures every reader takes (K.energy.eb24h, the exercise lag's ex24h and ee24h, the nutrients'
-- expenditure and carbohydrate, the legacy mirror's protein, carbohydrate and lipid) are K.body.trail24 over
-- record.body.trail (the evenly-spread blend of today and the closed day read a
-- phantom deficit before breakfast; it is retired). The closed-day rings eb7, p7 and mass7 remain for the 7-day
-- readers: K.partition.deficitWeek, NR_Server_Effects' protein week and K.body.trend.
-- The window's code is at the end of this file.

-- The legacy calorie store: the trailing-24 h energy balance clamped to the vanilla store's range.
function K.body.mapCalories(eb24h)
    return K.clamp(eb24h, -2200, 3700) -- #0022
end

-- The legacy protein store from the trailing-24 h protein intake per kg body weight (g/kg/d):
-- P <= PROT_FLOOR_AT reads PROT_STORE_FLOOR; below PROT_OK it runs linearly PROT_STORE_RAMP .. 0; to PROT_FULL 0 .. PROT_STORE_FULL;
-- above PROT_FULL PROT_STORE_OVER; clamped to the store's [-500, 1000] (the body.PROT_* dials).
-- The x1.5 arm (50 < p < 300, #2112) opens at P ~ 1.07 at the shipped dials.
K.body.PROT_OK = K.dials.get("body.PROT_OK")
K.body.PROT_RAMP_SPAN = K.dials.get("body.PROT_RAMP_SPAN")
K.body.PROT_FLOOR_AT = K.body.PROT_OK - K.body.PROT_RAMP_SPAN -- derived (bit-identical to the former literal at the shipped dials), so the ramp ends at PROT_OK whatever P_LOW reads
K.body.PROT_FULL = K.dials.get("body.PROT_FULL")
K.body.PROT_STORE_FLOOR = K.dials.get("body.PROT_STORE_FLOOR")
K.body.PROT_STORE_RAMP = K.dials.get("body.PROT_STORE_RAMP")
K.body.PROT_STORE_FULL = K.dials.get("body.PROT_STORE_FULL")
K.body.PROT_STORE_OVER = K.dials.get("body.PROT_STORE_OVER")
function K.body.mapProteins(pPerKgDay)
    local m = K.body.PROT_STORE_OVER -- ruling 13 (the body.PROT_* dials)
    if pPerKgDay <= K.body.PROT_FLOOR_AT then
        m = K.body.PROT_STORE_FLOOR
    elseif pPerKgDay < K.body.PROT_OK then
        m = K.body.PROT_STORE_RAMP - K.body.PROT_STORE_RAMP * (pPerKgDay - K.body.PROT_FLOOR_AT) / K.body.PROT_RAMP_SPAN
    elseif pPerKgDay <= K.body.PROT_FULL then
        m = K.body.PROT_STORE_FULL * (pPerKgDay - K.body.PROT_OK) / (K.body.PROT_FULL - K.body.PROT_OK)
    end
    return K.clamp(m, -500, 1000) -- #0023
end

-- The legacy carbohydrate store: the trailing-24 h carbohydrate intake (g) minus the CARB_REF_G reference.
K.body.CARB_REF_G = K.dials.get("body.CARB_REF_G")
function K.body.mapCarbs(gIn24h)
    return K.clamp(gIn24h - K.body.CARB_REF_G, -500, 1000) -- the reference a dial (ruling 13); the store's range
end

-- The legacy lipid store: the trailing-24 h lipid intake (g) minus the LIP_REF_G reference.
K.body.LIP_REF_G = K.dials.get("body.LIP_REF_G")
function K.body.mapLipids(gIn24h)
    return K.clamp(gIn24h - K.body.LIP_REF_G, -500, 1000) -- the reference a dial (ruling 13); the store's range
end

-- The trailing-24 h window: one hourly ring per quantity, TRAIL_N slots, game hour h
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

-- The window's clock at world age ageH: the window runs on online hours, its own age moved by the step's length
-- (ageH - body.lastAgeH; Plan 16 Task 2), so the resume, which moves body.lastAgeH past an offline gap
-- (K.resume.shift), leaves every slot's hour where the player left it, and no hour of the gap is booked or rolls one
-- off. Equal to ageH for a body never away (the difference of two close ages is exact, so the sum lands on ageH).
function K.body.trailClock(body, ageH)
    return body.trail.at + (ageH - body.lastAgeH)
end

-- Add x to ring key's current hour.
function K.body.trailAdd(t, key, x)
    local ring = t[key]
    local s = K.body.trailSlot(math.floor(t.at))
    ring[s] = ring[s] + x
end

-- One ring's closed sum: every slot but slot cur, a non-finite slot zeroed on the way. Returns the sum and the count
-- of slots zeroed (the heal names a ring by it, K.heal.trail).
function K.body.trailRingSum(ring, cur)
    local s = 0
    local z = 0
    for i = 1, K.body.TRAIL_N do
        local x = ring[i]
        if not K.finite(x) then
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

-- The record calendar (Plan 13 ruling 13-5; Plan 16 Task 2, spec section 1.2): body.dayIndex counts the record's
-- closed days and body.dayStartH is the world age the open record day started at. The day closes after 24 online
-- game hours: a minute at world age ageH closes it when ageH - dayStartH reaches DAY_H, and moves dayStartH on by one
-- day. The resume moves dayStartH past an offline gap (K.resume.STAMPS), so a record day counts online hours only,
-- whatever the world days between; a body never away closes at the world's day boundary, where K.body.new starts
-- its first day. At most one close a minute: a start still a day or more behind after the move (a stall the pipeline
-- did not sub-step) is brought up to the last whole day before ageH, closing nothing more. Returns the closes the
-- caller runs, 0 or 1; dayIndex is never touched here: the caller's K.partition.closeDay advances it by one.
K.body.DAY_H = 24 -- game hours in a record day

function K.body.calendar(body, ageH)
    if ageH - body.dayStartH < K.body.DAY_H then
        return 0
    end
    body.dayStartH = body.dayStartH + K.body.DAY_H
    local behind = ageH - body.dayStartH
    if behind >= K.body.DAY_H then
        body.dayStartH = ageH - math.fmod(behind, K.body.DAY_H)
    end
    return 1
end

-- ============================================================ the creation body (Plan 13 Task 9; spec section 3.2)
-- What each muscle and weight pick sets in the starting body. The muscle pick (nil reads "none") sets the start lean
-- through its innate factor N0 and its start level; the weight pick sets the fat alone (Plan 13 Task 10c, Angus
-- 2026-10-15: a thin pick removes fat, not muscle), so every weight pick may be taken with every muscle pick.

-- The creation fat as a fat mass index (kg/m2) at the average lean by weight pick: male, the middle of Kelly 2009's
-- bands (Obese at class I, 9-12); female, the middle of the female bands, read only for effective sex 2 (NR.SexSpecific
-- on and the character female). create scales it by the start lean over the average's (Task 10b), so each start sits
-- at its band middle's body-fat share: male 20 %, 29.4 % and 36.8 % at every lean.
K.body.FAT_FMI = { none = K.dials.get("body.FAT_FMI.none"), OVERWEIGHT = K.dials.get("body.FAT_FMI.OVERWEIGHT"), OBESE = K.dials.get("body.FAT_FMI.OBESE") }
K.body.FAT_FMI_F = { none = K.dials.get("body.FAT_FMI_F.none"), OVERWEIGHT = K.dials.get("body.FAT_FMI_F.OVERWEIGHT"), OBESE = K.dials.get("body.FAT_FMI_F.OBESE") }

-- A thin pick's start body-fat share (male), mid-band below its entry edge (K.traits.THIN_CUTS 0.12 and 0.08); the
-- female values add K.traits.THIN_F_OFFSET (18 % and 14.5 %). The fat is bf x lm / (1 - bf) on the muscle pick's lean.
K.body.THIN = { UNDERWEIGHT = K.dials.get("body.THIN.UNDERWEIGHT"), VERY_UNDERWEIGHT = K.dials.get("body.THIN.VERY_UNDERWEIGHT") }

-- The rungs of a weight pick (ruling 13-30), and Emaciated read as Very Underweight (rung 2).
K.body.FAT_RUNG = { OVERWEIGHT = 1, OBESE = 2 } -- ruling 13-30
K.body.THIN_RUNG = { UNDERWEIGHT = 1, VERY_UNDERWEIGHT = 2 } -- ruling 13-30
K.body.WEIGHT_ALIAS = { EMACIATED = "VERY_UNDERWEIGHT" } -- rulings 13-6, 13-30

-- The start fat of weight pick pick (nil for none; a thin pick or a fat pick) on start lean F at effective sex sexIdx
-- (2 female, else male): a thin pick's body-fat share (K.body.THIN, plus K.traits.THIN_F_OFFSET for 2) as
-- bf x F / (1 - bf); any other pick's FMI times H2 times F / Favg (K.strength.averageLean; Task 10b), the female table for 2.
function K.body.fatStart(pick, F, sexIdx)
    local bf = K.body.THIN[pick]
    if bf then
        if sexIdx == 2 then
            bf = bf + K.traits.THIN_F_OFFSET
        end
        return bf * F / (1 - bf)
    end
    local fmi = K.body.FAT_FMI
    if sexIdx == 2 then
        fmi = K.body.FAT_FMI_F
    end
    local H2 = K.HEIGHT_M * K.HEIGHT_M
    return fmi[pick or "none"] * H2 * (F / K.strength.averageLean())
end

-- The creation spec of a muscle pick, a weight pick (either nil for none), the strength table P and the effective sex
-- sexIdx (2 female, else male): the start lean F solves level(F, N0, 1) = the pick's start level; the set point F0 and
-- the natural cap Fc move by traitShare of F - F5, Fc clamped at the natural FFMI limit (ruling 13-47); the peak is
-- max(F, F0); the lean is F for every weight pick; the fat is the pick's start fat (K.body.fatStart) on F; and fmRef,
-- the fat reference the depletion reads, is the no-pick fat on F, so a thin start is underfed from its first minute
-- (fatDep = (fmRef - fm) / fmRef > 0: hungry, and partly adapted, until regained; Angus 2026-10-15), every other
-- start at its own fat.
-- profBoost is the profession's Strength boost (Plan 13 Task 17b; a nil or non-finite one reads 0): it raises the
-- start level like a small trait, clamped to [0, 10] so the native perk is reachable, and adds no innate factor; F0, Fc
-- and Pk follow the raised F as for a trait.
-- Returns { lm, F0, Fc, Pk, N0, fm, fmRef, fatT, thinT, sexIdx }.
function K.body.create(muscle, weight, P, sexIdx, profBoost)
    local key = muscle or "none"
    local pick = K.body.WEIGHT_ALIAS[weight] or weight
    local H2 = K.HEIGHT_M * K.HEIGHT_M
    local N0 = P.N0[key]
    local boost = 0
    if K.finite(profBoost) then
        boost = profBoost
    end
    local F = K.strength.fOfLevel(K.clamp(P.startLevel[key] + boost, 0, K.strength.L_MAX), N0, 1, P)
    local F5 = K.strength.fOfBio(5, P)
    local d = P.traitShare * (F - F5)
    local spec = {}
    spec.N0 = N0
    spec.F0 = F5 + d
    spec.Fc = K.min(K.strength.fOfBio(P.capLevel, P) + d, P.ffmiNaturalRaw * H2)
    spec.Pk = K.max(F, spec.F0)
    spec.lm = F
    spec.sexIdx = sexIdx or 1
    spec.fm = K.body.fatStart(pick, F, spec.sexIdx)
    spec.fmRef = K.body.fatStart(nil, F, spec.sexIdx)
    if K.body.THIN[pick] == nil then
        spec.fmRef = spec.fm
    end
    spec.fatT = K.body.FAT_RUNG[pick] or 0
    spec.thinT = K.body.THIN_RUNG[pick] or 0
    return spec
end

-- A fresh record.body from a creation spec (K.body.create), the engine's sex (1 male, 2 female) and the world age in
-- hours: the spec's lean, set point, cap, peak, N0, fat and rungs; the labile lean, the grace counters and the signal
-- ring at 0; T at 1; fmRef the spec's (the no-pick fat for a thin start) and lm0dis at the start; the record day from the
-- world day's start, the day accumulators at 0, the seven-day rings (mass7 at the body mass lm + lx + fm), the trailing-24 h
-- window (K.body.newTrail, empty at birth) and the neutral rmod, tac, pPrevKg and energyState. Numbers and tables of
-- numbers only (#1495).
-- body.band is K.traits.axes over the spec's rungs at its effective sex sexIdx (ruling 13-30). The closed week's
-- sets S start at 0. The adapter builds every body here: first sight (NR_Server_Metabolism.ensureBody over the muscle
-- pick read off the native level, Task 17b), the store's default body and the heal's no-trait values (K.body.create(nil, nil, P)).
function K.body.new(spec, sex, ageH)
    local day = math.floor(ageH / 24)
    local body = {}
    body.lm = spec.lm
    body.F0 = spec.F0
    body.Fc = spec.Fc
    body.Pk = spec.Pk
    body.N0 = spec.N0
    body.fm = spec.fm
    body.fatT = spec.fatT
    body.thinT = spec.thinT
    body.band = K.traits.axes(body, spec.sexIdx)
    body.lx = 0
    body.grace = 0
    body.sigDay = 0
    body.T = 1
    body.Tgrace = 0
    body.S = 0
    body.tDisuse = 0
    body.fmRef = spec.fmRef
    body.lm0dis = spec.lm
    body.sex = sex
    body.bornAge = ageH
    body.lastAgeH = ageH
    body.at = 0
    body.dayIndex = day
    body.dayStartH = day * K.body.DAY_H
    body.inDay = 0
    body.eeDay = 0
    body.ebDay = 0
    body.actKcalDay = 0
    body.exKcalDay = 0
    body.pDay = 0
    body.carbDay = 0
    body.lipDay = 0
    body.alcDay = 0
    body.sig7 = {}
    body.eb7 = {}
    body.mass7 = {}
    body.bandWeek = {}
    body.p7 = {}
    for i = 1, K.body.WEEK_N do
        body.sig7[i] = 0
        body.eb7[i] = 0
        body.mass7[i] = body.lm + body.lx + body.fm
        body.bandWeek[i] = { 0, 0 }
        body.p7[i] = 0
    end
    body.trail = K.body.newTrail(ageH)
    body.metMinDay = 0
    body.band1Day = 0
    body.band2Day = 0
    body.tac = 1.0
    body.rmod = 1
    body.pPrevKg = K.aerobic.P_LOW -- neutral
    body.energyState = 1
    return body
end
