-- NR_Kernel_Body.lua: record.body and its creation (K.body.create, K.body.new), the trend flags, the legacy
-- macro-mirror maps (the vanilla Nutrition stores other mods read), the trailing-24 h window and the record calendar.
-- Pure, no Java; slow-clock code with no fast region. Sorts after NR_Kernel.lua; K.clamp and K.min resolve at call time.
local K = NutritionRevamp.kernel
K.body = {}

-- The length of the seven-day rings (eb7, mass7, p7, sig7, bandWeek; slot 1 the oldest, the last yesterday).
K.body.WEEK_N = 7

-- Index 1 male, 2 female: female only with NR.SexSpecific on; record.body.sex keeps the engine's value.
function K.body.effSex(sex, specific)
    if specific == true and sex == 2 then
        return 2
    end
    return 1
end

-- Strict inequalities, so a trend exactly on a threshold raises nothing.
K.body.TREND_KG_D = K.dials.get("body.TREND_KG_D")
K.body.TREND_LOT_KG_D = K.dials.get("body.TREND_LOT_KG_D")
function K.body.flags(trendKgPerDay)
    return trendKgPerDay > K.body.TREND_KG_D, trendKgPerDay > K.body.TREND_LOT_KG_D, trendKgPerDay < -K.body.TREND_KG_D -- ruling 17
end

-- A fresh ring holds the creation weight, so the trend starts at 0; the adapter rotates it at day close.
function K.body.trend(mass7, w)
    return (w - mass7[1]) / 7
end

-- Every trailing-24 h figure (K.energy.eb24h, ex24h, ee24h, the nutrients', the legacy mirror's) is K.body.trail24 over
-- record.body.trail; the closed-day rings eb7, p7 and mass7 serve the 7-day readers.

-- The legacy mirror maps: each trailing-24 h figure clamped to its vanilla store's range.
function K.body.mapCalories(eb24h)
    return K.clamp(eb24h, -2200, 3700) -- #0022
end

-- g/kg/d through the body.PROT_* ramp; the x1.5 arm (50 < p < 300, #2112) opens at P ~ 1.07 at the shipped dials.
K.body.PROT_OK = K.dials.get("body.PROT_OK")
K.body.PROT_RAMP_SPAN = K.dials.get("body.PROT_RAMP_SPAN")
K.body.PROT_FLOOR_AT = K.body.PROT_OK - K.body.PROT_RAMP_SPAN -- derived, so the ramp ends at PROT_OK whatever P_LOW reads
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

K.body.CARB_REF_G = K.dials.get("body.CARB_REF_G")
function K.body.mapCarbs(gIn24h)
    return K.clamp(gIn24h - K.body.CARB_REF_G, -500, 1000) -- the reference a dial (ruling 13); the store's range
end

K.body.LIP_REF_G = K.dials.get("body.LIP_REF_G")
function K.body.mapLipids(gIn24h)
    return K.clamp(gIn24h - K.body.LIP_REF_G, -500, 1000) -- the reference a dial (ruling 13); the store's range
end

-- The trailing-24 h window: one hourly ring of TRAIL_N slots a quantity, hour h in slot h % TRAIL_N + 1. The window
-- (trail24) is the current hour so far, the 23 closed hours and the oldest hour weighted by the share of it still inside
-- the 24 h, off by at most the oldest hour's own content for a lump inside it. Intake (kcal and
-- the protein, carbohydrate and lipid grams), expenditure and exercise come in meals and bouts, so each takes a ring.
-- The closed sums c are rebuilt whenever ch is not the current hour (a fresh window, a load, a heal). A game choice.
K.body.TRAIL_N = 25 -- the current hour and the 24 before it
K.body.TRAIL_KEYS = { "kcal", "ee", "ex", "p", "carb", "lip" }

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

function K.body.trailSlot(h)
    return h % K.body.TRAIL_N + 1
end

-- Zero the slot of every hour passed since the last write (the whole ring at most); an age not past t.at leaves it.
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

-- The window runs on online hours, its age moved by the step's length, so the resume (K.resume.shift) books no hour of
-- an offline gap and rolls no slot off.
function K.body.trailClock(body, ageH)
    return body.trail.at + (ageH - body.lastAgeH)
end

function K.body.trailAdd(t, key, x)
    local ring = t[key]
    local s = K.body.trailSlot(math.floor(t.at))
    ring[s] = ring[s] + x
end

-- A non-finite slot is zeroed on the way; the count lets the heal name the ring (K.heal.trail).
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

-- Rebuilt when built for another hour; returns t.c and the count of non-finite slots zeroed.
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

-- Less the share f of the oldest hour already outside the window.
function K.body.trail24(t, key)
    local c = K.body.trailClosed(t)
    local h = math.floor(t.at)
    local ring = t[key]
    return c[key] - (t.at - h) * ring[K.body.trailSlot(h + 1)] + ring[K.body.trailSlot(h)]
end

function K.body.trailIntake(t, absorbed)
    K.body.trailAdd(t, "kcal", absorbed.calories)
    K.body.trailAdd(t, "p", absorbed.proteins)
    K.body.trailAdd(t, "carb", absorbed.carbs)
    K.body.trailAdd(t, "lip", absorbed.lipids)
end

-- The record calendar: a record day closes after DAY_H online game hours (the resume moves dayStartH past an offline
-- gap). At most one close a minute: a start still a day behind after it (a stall) jumps to the last whole day, closing
-- nothing more. The caller's K.partition.closeDay advances dayIndex.
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

-- ============================================================ the creation body
-- The muscle pick sets the start lean; the weight pick sets the fat alone, so every weight pick goes with every muscle pick.

-- Creation fat as FMI at the average lean, the middle of Kelly 2009's bands (the _F table for effective sex 2); create
-- scales it by the start lean, so each start sits at its band's body-fat share.
K.body.FAT_FMI = { none = K.dials.get("body.FAT_FMI.none"), OVERWEIGHT = K.dials.get("body.FAT_FMI.OVERWEIGHT"), OBESE = K.dials.get("body.FAT_FMI.OBESE") }
K.body.FAT_FMI_F = { none = K.dials.get("body.FAT_FMI_F.none"), OVERWEIGHT = K.dials.get("body.FAT_FMI_F.OVERWEIGHT"), OBESE = K.dials.get("body.FAT_FMI_F.OBESE") }

-- A thin pick's start body-fat share (male); female adds K.traits.THIN_F_OFFSET. The fat is bf x lm / (1 - bf).
K.body.THIN = { UNDERWEIGHT = K.dials.get("body.THIN.UNDERWEIGHT"), VERY_UNDERWEIGHT = K.dials.get("body.THIN.VERY_UNDERWEIGHT") }

-- Emaciated reads as Very Underweight (rung 2).
K.body.FAT_RUNG = { OVERWEIGHT = 1, OBESE = 2 } -- ruling 13-30
K.body.THIN_RUNG = { UNDERWEIGHT = 1, VERY_UNDERWEIGHT = 2 } -- ruling 13-30
K.body.WEIGHT_ALIAS = { EMACIATED = "VERY_UNDERWEIGHT" } -- ruling 13-30

-- A thin pick: its body-fat share on F; any other pick: its FMI times H2, scaled by F over the average lean.
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

-- The start lean F solves level(F, N0, 1) = the pick's start level; F0 and Fc move by traitShare of F - F5, Fc clamped
-- at the natural FFMI limit. fmRef, the fat the depletion reads, is the no-pick fat, so a thin start is underfed from
-- its first minute. profBoost (nil reads 0) raises the start level like a trait but adds no innate factor.
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

-- Numbers and tables of numbers only (#1495). Every body is built here: first sight, the store's default body and the
-- heal's no-trait values (K.body.create(nil, nil, P)).
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
