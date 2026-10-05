-- NR_Kernel_Strength.lua -- the body model's Strength (Plan 3): the functional factor (a neural term
-- with a held-peak memory floor, a cumulative-deficit term and a disuse residual), the ceiling it and
-- the lean ratio set on the Java perk level, the XP-implied level, the write policy that moves the shown
-- level toward min(XP-implied, ceiling), the band remap, and the acute carry factor.
-- The level is a clamp, never a grant: the shown level never exceeds the XP-implied level (#2701).
-- Pure: numbers and Lua tables in, numbers, booleans, strings and Lua tables out, no Java. Slow-clock
-- code with no fast region, so math.exp, math.log, math.floor and the bounded numeric `for` over the
-- kernel's own tables are allowed. This file sorts after NR_Kernel.lua, and every K.clamp / K.min /
-- K.max reference is at call time.
local K = NutritionRevamp.kernel
K.strength = {}

-- The neural term's target per unit strength dose.
K.strength.N_TARGET_K = 0.18 -- S0585

-- The neural term's time constants, days: rising, falling, falling while immobilised.
K.strength.TAU_RISE = 14 -- S0086
K.strength.TAU_FALL = 60 -- S0655 design-phase-v1; calibrated to S0610/S0618
K.strength.TAU_IMMOB = 10 -- S0070/S0612

-- The memory floor: the held peak retains MEM_RETAIN, decaying on MEM_TAU days; a peak counts once
-- held MEM_HOLD_DAYS consecutive days (the nHist ring's length).
K.strength.MEM_RETAIN = 0.80 -- S0655 design-phase-v1; S0618/S0080
K.strength.MEM_TAU = 300 -- S0655 design-phase-v1; S0618/S0080
K.strength.MEM_HOLD_DAYS = 14 -- S0655 design-phase-v1: the held-peak window

-- The cumulative deficit: a 10-day exponential of deficit kcal; full scale CUMDEF_FULL costs E_ENERGY_MAX.
K.strength.CUMDEF_TAU = 10 -- S0601
K.strength.CUMDEF_FULL = 50000 -- S0602
K.strength.E_ENERGY_MAX = -0.10 -- S0602

-- The disuse residual DISUSE_K * ln(1 + tDisuse / DISUSE_T).
K.strength.DISUSE_K = -0.325 -- fitted to S0070 beside K.partition's mass term
K.strength.DISUSE_T = 22 -- fitted to S0070 beside K.partition's mass term

-- The functional factor's clamp.
K.strength.F_MIN = 0.55 -- game choice § 7 item 30
K.strength.F_MAX = 1.25 -- game choice § 7 item 30

-- The ceiling's levels per doubling of lean ratio times functional factor.
K.strength.LEVELS_PER_DOUBLING = 10 -- game choice: read off WEAK 0.75 -> STRONG 1.5

-- The Java perk cap: getTotalXpForLevel(11) == getTotalXpForLevel(10) (#2859); BeyondTen's mastery
-- levels 11-15 live in its own modData, outside the model.
K.strength.L_MAX = 10 -- #2118; ruling 9

-- The write policy: a rise after the ceiling stands >= shown + 1 for RISE_HOLD_H game hours; a fall at
-- most once per FALL_MIN_H game hours.
K.strength.RISE_HOLD_H = 6 -- ruling 10
K.strength.FALL_MIN_H = 1 -- ruling 10

-- The acute carry terms. Dehydration in two steps (percent body mass), scaled by DEHYD_SWEAT_K when
-- the deficit arose from sweat or heat.
K.strength.DEHYD_PCT1 = 2 -- S0623
K.strength.DEHYD_STEP1 = -0.03 -- S0623
K.strength.DEHYD_PCT2 = 4 -- S0624
K.strength.DEHYD_STEP2 = -0.06 -- S0624
K.strength.DEHYD_SWEAT_K = 1.5 -- S0624: active (exercise or heat) dehydration an extra −5.4 % vs passive; the ×1.5 is a game choice

-- Hours awake past the knee cost SLEEP_PER_H per hour, capped; halved from dawn to noon.
K.strength.SLEEP_KNEE_H = 18 -- S0763, S0762; ruling 11 (conflict C7)
K.strength.SLEEP_PER_H = -0.004 -- S0763, S0762
K.strength.SLEEP_CAP = -0.08 -- S0763, S0762
K.strength.SLEEP_AM_FACTOR = 0.5 -- S0765; 06-12 game choice
K.strength.AM_FROM_H = 6 -- S0765; 06-12 game choice (ruling 11)
K.strength.AM_TO_H = 12 -- S0765; 06-12 game choice (ruling 11)

-- Caffeine, clinical vitamin D deficiency and body fat above the knee (per 10 points of fat fraction).
K.strength.CAFFEINE_BONUS = 0.02 -- S0626 SMD->% game choice
K.strength.VITD_PENALTY = -0.03 -- S0633; S0634 disagrees
K.strength.FAT_PER_10PT = -0.03 -- S0651
K.strength.FAT_KNEE = 0.30 -- S0651
K.strength.FAT_PER_PTS = 0.10 -- S0651: FAT_PER_10PT's unit, 10 points of fat fraction

-- The acute factor's clamp.
K.strength.E_ACUTE_MIN = -0.20 -- game choice § 7 item 30
K.strength.E_ACUTE_MAX = 0.03 -- game choice § 7 item 30

-- Vanilla's band remap as {highest level, trait}: the first row whose level is >= the shown level.
-- Level 5 carries no band trait (its row's trait is nil).
K.strength.BANDS = { { 1, "WEAK" }, { 4, "FEEBLE" }, { 5, nil }, { 8, "STOUT" }, { 10, "STRONG" } } -- #2157: WEAK 0-1, FEEBLE 2-4, none 5, STOUT 6-8, STRONG >= 9

-- One step of the neural term over dtD days toward N_TARGET_K * dStr: rising on TAU_RISE; falling held
-- while the dose is maintained, else on TAU_IMMOB when immobilised, else on TAU_FALL. Returns the body.
function K.strength.neuralStep(body, dStr, maintained, immobilised, dtD)
    local S = K.strength
    local target = S.N_TARGET_K * dStr
    local tau = S.TAU_RISE
    if target < body.n then
        if maintained then
            return body
        end
        tau = S.TAU_FALL
        if immobilised then
            tau = S.TAU_IMMOB
        end
    end
    body.n = body.n + (target - body.n) * (1 - math.exp(-dtD / tau))
    return body
end

-- Close the day: shift nHist one slot (slot 1 the oldest) and write n into slot MEM_HOLD_DAYS; the
-- ring's minimum is the level held every one of those days, and a held level above nPeak becomes the
-- new peak stamped today. The cumulative deficit decays one day and adds the day's deficit only.
-- Call before K.partition.closeDay, which zeroes ebDay. Returns the body.
function K.strength.closeDay(body, today)
    local S = K.strength
    local hist = body.nHist
    local last = S.MEM_HOLD_DAYS
    for i = 1, last - 1 do
        hist[i] = hist[i + 1]
    end
    hist[last] = body.n
    local heldMin = hist[1]
    for i = 2, last do
        heldMin = K.min(heldMin, hist[i])
    end
    if heldMin > body.nPeak then
        body.nPeak = heldMin
        body.tPeakD = today
    end
    body.cumDef = body.cumDef * math.exp(-1 / S.CUMDEF_TAU) + K.max(0, -body.ebDay)
    return body
end

-- The memory floor on the functional factor: 1 + nPeak * MEM_RETAIN * exp(-(today - tPeakD) / MEM_TAU).
function K.strength.floorF(body, today)
    local S = K.strength
    return 1 + body.nPeak * S.MEM_RETAIN * math.exp(-(today - body.tPeakD) / S.MEM_TAU)
end

-- The slow functional factor: max(1 + n, the memory floor) plus the cumulative-deficit term and the
-- disuse residual, clamped to [F_MIN, F_MAX].
function K.strength.fSlow(body, today)
    local S = K.strength
    local neural = K.max(1 + body.n, S.floorF(body, today))
    local eEnergy = S.E_ENERGY_MAX * K.clamp(body.cumDef / S.CUMDEF_FULL, 0, 1)
    local eDisuse = S.DISUSE_K * math.log(1 + body.tDisuse / S.DISUSE_T)
    return K.clamp(neural + eEnergy + eDisuse, S.F_MIN, S.F_MAX)
end

-- The ceiling level: the creation level l0 moved LEVELS_PER_DOUBLING levels per doubling of
-- (lm / lm0) * fSlow, rounded half up and clamped to [0, L_MAX].
function K.strength.ceiling(l0, lm, lm0, fSlow)
    local S = K.strength
    local moved = l0 + S.LEVELS_PER_DOUBLING * math.log(lm / lm0 * fSlow) / math.log(2) + 0.5
    return K.clamp(math.floor(moved), 0, S.L_MAX)
end

-- The XP-implied level: the largest L in 0..L_MAX with xp >= totals[L], where totals is the adapter's
-- table of getTotalXpForLevel(L) for L = 1..L_MAX (level 0 needs 0). On 42.20.4 the ladder reads
-- {1500, 4500, 10500, 19500, 37500, 67500, 127500, 217500, 337500, 487500} (#2102: 37500 is level 5's
-- total, 67500 level 6's); the adapter reads it at runtime and never hard-codes it.
function K.strength.xpLevel(xp, totals)
    local level = 0
    for L = 1, K.strength.L_MAX do
        if xp >= totals[L] then
            level = L
        end
    end
    return level
end

-- The write policy, once per slow tick: target = min(lvanilla, lceil); the rise hold accrues while the
-- ceiling stands >= shown + 1 and resets otherwise; a fall of one level at most once per FALL_MIN_H; a
-- rise of one level once the hold reaches RISE_HOLD_H; never above lvanilla (a rust or XP loss follows
-- down at once). Writes shownL, riseHeldH and lastFallAge; returns the desired level.
function K.strength.policy(body, lvanilla, lceil, ageH, dtH)
    local S = K.strength
    local target = K.min(lvanilla, lceil)
    local shown = body.shownL
    if lceil >= shown + 1 then
        body.riseHeldH = body.riseHeldH + dtH
    else
        body.riseHeldH = 0
    end
    local desired = shown
    if target < shown and ageH - body.lastFallAge >= S.FALL_MIN_H then
        desired = shown - 1
        body.lastFallAge = ageH
    end
    if target > shown and body.riseHeldH >= S.RISE_HOLD_H then
        desired = K.min(target, shown + 1)
        body.riseHeldH = 0
    end
    desired = K.min(desired, lvanilla)
    body.shownL = desired
    return desired
end

-- The band trait vanilla's remap gives a level (nil at 5); a level above the table reads the last row.
function K.strength.bandOf(level)
    local bands = K.strength.BANDS
    for i = 1, #bands do
        if level <= bands[i][1] then
            return bands[i][2]
        end
    end
    return bands[#bands][2]
end

-- The acute carry factor: dehydration in two steps (x DEHYD_SWEAT_K from sweat or heat), hours awake
-- past the knee (halved from AM_FROM_H to AM_TO_H, capped), caffeine, clinical vitamin D deficiency and
-- body fat above FAT_KNEE, the sum clamped to [E_ACUTE_MIN, E_ACUTE_MAX].
function K.strength.eAcute(dehydPct, sweatActive, hoursAwake, hourOfDay, caffeineActive, vitDClinical, bf)
    local S = K.strength
    local sweatK = 1
    if sweatActive then
        sweatK = S.DEHYD_SWEAT_K
    end
    local e = 0
    if dehydPct >= S.DEHYD_PCT2 then
        e = S.DEHYD_STEP2 * sweatK
    elseif dehydPct >= S.DEHYD_PCT1 then
        e = S.DEHYD_STEP1 * sweatK
    end
    local eSleep = K.max(S.SLEEP_CAP, S.SLEEP_PER_H * K.max(0, hoursAwake - S.SLEEP_KNEE_H))
    if hourOfDay >= S.AM_FROM_H and hourOfDay < S.AM_TO_H then
        eSleep = eSleep * S.SLEEP_AM_FACTOR
    end
    e = e + eSleep
    if caffeineActive then
        e = e + S.CAFFEINE_BONUS
    end
    if vitDClinical then
        e = e + S.VITD_PENALTY
    end
    if bf > S.FAT_KNEE then
        e = e + S.FAT_PER_10PT * (bf - S.FAT_KNEE) / S.FAT_PER_PTS
    end
    return K.clamp(e, S.E_ACUTE_MIN, S.E_ACUTE_MAX)
end

-- The carry delta written through setMaxWeightDelta: the creation-trait factor times (1 + eAcute).
function K.strength.carryDelta(traitCarry, eAcute)
    return traitCarry * (1 + eAcute) -- ruling 11
end
