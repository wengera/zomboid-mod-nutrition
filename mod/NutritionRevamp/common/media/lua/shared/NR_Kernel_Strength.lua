-- NR_Kernel_Strength.lua -- the body model's Strength: the functional factor (a neural term
-- with a held-peak memory floor, a cumulative-deficit term and a disuse residual), the ceiling it and
-- the lean ratio set on the Java perk level, the XP-implied level, the write policy that moves the shown
-- level toward min(XP-implied, ceiling), the band remap, and the acute carry factor.
-- The level is a clamp, never a grant: the shown level never exceeds the XP-implied level (#2701).
-- Pure: numbers and Lua tables in, numbers, booleans, strings and Lua tables out, no Java. Slow-clock
-- code with no fast region, so math.exp, math.log, math.floor and the bounded numeric `for` over the
-- kernel's own tables are allowed. This file sorts after NR_Kernel.lua, and every K.clamp / K.min /
-- K.max reference is at call time; DEFAULTS.R is computed at this file's load, so those helpers and
-- K.HEIGHT_M must be defined in NR_Kernel.lua.
local K = NutritionRevamp.kernel
K.strength = {}

-- ============================================================ the lean-mass strength model (Plan 13)
-- The constants table (ruling 13-1): every constant of the growth law, the energy gate and the lean
-- partition (point T, compact_T.json "chosen", under the oracle's key names), the game constants beside
-- them, and the strength-model block (ruling 13-45). K.strength.params merges a server's options over a
-- copy; every function below takes that table as P. M5, R and ffmiNaturalRaw are derived at file load, after the
-- functions they read.
K.strength.DEFAULTS = {
    -- point T (the growth law, the energy gate, the lean partition)
    k = 0.009906127265972144, -- per week; fit point T, the anchor
    beta = 3.0, -- fit point T; S1976, S1977, S1967, S1974 (against S1955, S1975)
    Sg0 = 0.5, -- sets/wk; fit point T (bound reported); S1951, S1958
    Sref = 12.0, -- sets/wk; S1951
    Smax = 30.0, -- sets/wk; S1951 (data thin above 25-30)
    Smax1 = 12.0, -- sets/wk; fit point T (bound reported); S1953, S1955, S1956
    fp_knots = { { 0.4, 0 }, { 0.8, 0.5 }, { 1.3, 0.92 }, { 1.6, 1.0 } }, -- g/kg/d; S0591, S0592, S1990, S0509
    E0 = -650.0, -- kcal/d at s = 0; fit point T; S1942, S0064, S2029, S2018
    E0_drop = 0.5, -- Angus's gate; flat in the fit; S2018
    fbal0 = 1.0, -- fit point T, at its physical bound; S1943, S2033
    fbal_drop = 0.5, -- Angus's gate; fit point T; S2018, S2019, S1925, S0606
    surplus_full = 0.10, -- of TDEE; Angus's gate; flat in the fit; S1943, S2033, S1944, S2037, S1946
    full_drop = 0.5, -- fit point T, flat; S2069, S2068, S1946, S2062, S2064
    a_nov = 6.0, -- fit point T; S0064
    trained_need = 0.0, -- evidence default (1 = Angus's premise)
    forbes_c = 10.4, -- kg; S0054, S0055 (S1056 open)
    wT = 0.35, -- fit point T; S0072, S1997, S0609
    S_def = 10.0, -- sets/wk; fit point T (H.47)
    wP = 0.6, -- fit point T; S0599
    pdef_lo = 0.8, -- g/kg/d; fit point T (the protection ramp's start)
    pdef_hi = 1.6, -- g/kg/d; fit point T, at its grid bound; S0599, S0064
    prot_floor = 0.1, -- fit point T
    x_max_frac = 0.05, -- of F; S0605 (game choice, S2016)
    x_tau_d = 28.0, -- days; S0605 (game choice, S2016)
    m = 0.3333333333333333, -- S1963, S0616 (unidentified; S2014 open)
    grace_d = 14, -- days; S1932, S1940, S1966
    detrain_hl_wk = 6.0, -- weeks; S2001
    detrain_status = 2.0, -- S1938 (game choice; S2014, S2017)
    regain_hl_wk = 6.0, -- weeks; S2002, S2003 (unidentified)
    peak_hl_yr = 2.0, -- years; S2004, S2010, S0620, S2007
    -- the game constants
    ffmi5 = 18.0, -- kg/m2, bio level 5's FFMI; game choice (spec section 2.4)
    ffmiPerLevel = 0.5, -- kg/m2 per bio level; game choice (spec section 2.4)
    capLevel = 16.5, -- the untrained natural cap in bio levels; ruling; S1915
    ts = 1.0, -- the biology clock; ruling 13-2
    xpPerSet = 346, -- provisional until Task 1's calibration run (plan constants block)
    incidental = 0.35, -- S1951 fractional, S1961, S1962; game choice
    fMinShare = 0.35, -- F's floor as a share of F0; game choice (the oracle's 0.35 * F0)
    fmMin = 0.5, -- kg, the fat floor; game choice (K.partition.FM_MIN)
    nov_p0 = 1.6, -- g/kg/d; the oracle's literal (the novice deficit deepening's ramp); game choice
    nov_pspan = 0.8, -- g/kg/d; the oracle's literal; game choice
    xs_p0 = 0.8, -- g/kg/d; the oracle's literal (the surplus share's protein ramp); game choice
    xs_pspan = 0.8, -- g/kg/d; the oracle's literal; game choice
    -- the strength-model block (ruling 13-45)
    b = 0.8, -- S2121 (derived 0.79), S0085
    Fnm = 27.0, -- kg; S2133; game choice
    N0 = { STRONG = 1.14, STOUT = 1.07, none = 1.0, FEEBLE = 0.915, WEAK = 0.82 }, -- S2142, S2143, S2145, S2162, S2166; game choice (S2170 open)
    startLevel = { STRONG = 9, STOUT = 7, none = 5, FEEBLE = 3, WEAK = 1 }, -- the vanilla start levels (Weak's 1 the floor)
    traitShare = 0.5, -- Angus
    ffmiNatural = 25.0, -- kg/m2 normalised to 1.80 m; S1915 (ruling 13-47)
    kouriCoef = 6.3, -- kg/m2 per m below 1.80 m; S1915 (Kouri 1995's height normalisation, its range cell; ruling 13-47)
    Tmax = 1.10, -- S2120, S2121, S2122; game choice
    tauUpWk = 3.0, -- weeks; S2112, S2113, S0086, S2118; game choice
    tauDownWk = 12.0, -- weeks; S1937, S2138, S2139; game choice (S2140 open)
    Tgrace_d = 21, -- days; S1939, S1931, S2138; game choice
    Wsat = 5.0, -- sets/wk; S1952, S2096; game choice
    yearsTo10 = 4.0, -- Angus; S2120, S2121 (S2141 open)
    perfectS = 20.0, -- sets/wk; perfect training (spec section 2.4); game choice
    perfectP = 2.0, -- g/kg/d; perfect training (spec section 2.4); game choice
    perfectE = 0.10, -- of TDEE; perfect training (spec section 2.4); game choice
}

-- The growth law's coordinate: the lean F at bio level L (FFMI ffmi5 at 5, ffmiPerLevel a level, at K.HEIGHT_M).
function K.strength.fOfBio(L, P)
    return (P.ffmi5 + (L - 5) * P.ffmiPerLevel) * (K.HEIGHT_M * K.HEIGHT_M)
end

-- The bio level of a lean F, the inverse of fOfBio.
function K.strength.bioLevel(F, P)
    return 5 + (F / (K.HEIGHT_M * K.HEIGHT_M) - P.ffmi5) / P.ffmiPerLevel
end

-- General strength S = ((F - Fnm) / M5)^b * N0 * T (spec section 2.1); 0 at or below Fnm.
function K.strength.strengthOf(F, N0, T, P)
    if F <= P.Fnm then
        return 0
    end
    return ((F - P.Fnm) / P.M5) ^ P.b * N0 * T
end

-- The shown level, linear in S: 5 at the untrained average (S = 1), 10 at S = R (ruling 13-45).
function K.strength.level(F, N0, T, P)
    return 5 + 5 * (K.strength.strengthOf(F, N0, T, P) - 1) / (P.R - 1)
end

-- The lean F at which level(F, N0, T, P) is L; Fnm where that level needs S <= 0 (below 5 - 5 / (R - 1)).
function K.strength.fOfLevel(L, N0, T, P)
    local S = 1 + (L - 5) * (P.R - 1) / 5
    if S <= 0 then
        return P.Fnm
    end
    return P.Fnm + P.M5 * (S / (N0 * T)) ^ (1 / P.b)
end

-- The growth threshold in sets a week at status s (spec section 5).
function K.strength.threshold(s, P)
    return P.Sg0 * math.exp(P.beta * s)
end

-- The effective set cap at status s (spec section 5).
function K.strength.setCap(s, P)
    return P.Smax + (P.Smax1 - P.Smax) * s
end

-- The training signal G of S weekly hard sets at status s, 1 at Sref for a novice (spec section 5).
function K.strength.signal(S, s, P)
    local root = math.sqrt(K.min(S, K.strength.setCap(s, P))) - math.sqrt(K.strength.threshold(s, P))
    return K.max(0, root) / (math.sqrt(P.Sref) - math.sqrt(P.Sg0))
end

-- R: the S of the untrained average after `years` of perfect training at Tmax, the growth law's
-- full-gate daily step from the average's creation body (spec section 2.4). It reads DEFAULTS only, never
-- a server's options; about 365 steps a year, run at file load and at a yearsTo10 change only (Rule 6).
function K.strength.R(years)
    local D = K.strength.DEFAULTS
    local F = K.strength.fOfBio(5, D)
    local F0 = F
    local Fc = K.strength.fOfBio(D.capLevel, D)
    local days = math.floor(years * 365 + 0.5)
    for _ = 1, days do
        local s = K.clamp((F - F0) / (Fc - F0), 0, 1)
        F = F + D.k * (Fc - F) * K.strength.signal(D.perfectS, s, D) / 7
    end
    return K.strength.strengthOf(F, 1, D.Tmax, D)
end

-- The shown perk level n and the progress bar's fraction of the next level: n floors L + 1e-9 (a start
-- built exactly on its level never floors one low) into [0, L_MAX]; frac is 0 below 0 and at the cap.
function K.strength.shown(L)
    local n = K.clamp(math.floor(L + 1e-9), 0, K.strength.L_MAX)
    local frac = 0
    if L >= 0 and n < K.strength.L_MAX then
        frac = K.max(0, L - n)
    end
    return n, frac
end

-- The growth status s in [0, 1]: lean above the set point as a share of the cap's room (bio units by
-- construction); 0 when the cap sits at or below the set point.
function K.strength.status(body)
    if body.Fc <= body.F0 then
        return 0
    end
    return K.clamp((body.lm - body.F0) / (body.Fc - body.F0), 0, 1)
end

-- The protein gate f_p at p g/kg/d: the fp_knots read flat past their ends (spec section 5).
function K.strength.fp(p, P)
    return K.interp(P.fp_knots, p)
end

-- The energy gate f_e at balance E kcal/d, status s, protein p g/kg/d and expenditure tdee (spec section 5):
-- zero at the status zero point E0s (deepened for a high-protein novice) and below; the balance gate bal
-- times the share of the way from E0s to balance in a deficit; from bal toward 1 across a surplus that
-- saturates at surplus_full of tdee, less full_drop with status.
function K.strength.fe(E, s, p, tdee, P)
    local ramp = K.clamp((p - P.nov_p0) / P.nov_pspan, 0, 1)
    local E0s = P.E0 * (1 - P.E0_drop * s) * (1 + P.a_nov * (1 - s) ^ 2 * ramp)
    local bal = P.fbal0 * (1 - P.fbal_drop * s) * (1 - P.trained_need * s)
    if E <= E0s then
        return 0
    end
    if E < 0 then
        return bal * (1 - E / E0s)
    end
    local full = P.surplus_full * (1 - P.full_drop * s) * tdee
    return bal + (1 - bal) * K.min(1, E / full)
end

-- The day's lean gain in kg before the biology clock ts (spec section 5): k a week times the room to the
-- cap Fc, the signal, the two gates and the alcohol gate; while lm sits below the held peak Pk, the regain
-- term (half-life regain_hl_wk, the signal capped at 1, the same three gates: a drinking day blunts the same
-- synthesis, controller ruling) wins if larger. Never negative.
function K.strength.growth(body, S, p, E, tdee, alcGkg, P)
    local s = K.strength.status(body)
    local G = K.strength.signal(S, s, P)
    local gates = K.strength.fp(p, P) * K.strength.fe(E, s, p, tdee, P) * K.partition.gAlc(alcGkg)
    local grow = P.k * (body.Fc - body.lm) * G * gates / 7
    if body.lm < body.Pk then
        local lr = math.log(2) / P.regain_hl_wk
        local regain = lr * (body.Pk - body.lm) * K.min(1, G) * gates / 7
        grow = K.max(grow, regain)
    end
    return K.max(0, grow)
end

-- The maintenance threshold S_m(s) in sets a week: the share m of the growth threshold (spec section 6).
function K.strength.maintainSets(s, P)
    return P.m * K.strength.threshold(s, P)
end

-- Detraining, in kg of lean lost today (spec section 6; ruling 13-2's exact form). Advances the grace
-- counter (a day below S_m adds one, any other day resets it); past grace_d / ts such days, and only while
-- lm is above the set point F0, lm - F0 falls by exp(-lam * ts * (1 - S / S_m) / 7), integrated exactly
-- over the day so no clock overshoots F0, lam's half-life lengthened by the status term. At ts > grace_d a
-- day below S_m detrains at grace 1, as the oracle does.
function K.strength.detrain(body, S, s, P, ts)
    local Sm = K.strength.maintainSets(s, P)
    if S < Sm then
        body.grace = body.grace + 1
    else
        body.grace = 0
    end
    if body.grace <= P.grace_d / ts or body.lm <= body.F0 then
        return 0
    end
    local lam = math.log(2) / (P.detrain_hl_wk * (1 + P.detrain_status * s))
    return (body.lm - body.F0) * (1 - math.exp(-lam * ts * (1 - S / Sm) / 7))
end

-- The remembered peak (spec section 6): Pk holds the highest lm, then decays toward lm with a half-life of
-- peak_hl_yr years, the biology clock scaling the day.
function K.strength.peakStep(body, P, ts)
    local Pk = K.max(body.Pk, body.lm)
    body.Pk = body.lm + (Pk - body.lm) * math.exp(-math.log(2) / (P.peak_hl_yr * 365) * ts)
end

-- The neural factor T (spec sections 4 and 6; ruling 13-45). Tgrace counts the days below m * Wsat and any
-- other day resets it; past Tgrace_d / ts such days T decays toward 1 on tauDownWk, else it rises toward
-- Tmax on tauUpWk at the signal's share of Wsat (capped at 1), both integrated exactly over the day.
function K.strength.neural(body, S, P, ts)
    if S < P.m * P.Wsat then
        body.Tgrace = body.Tgrace + 1
    else
        body.Tgrace = 0
    end
    if body.Tgrace > P.Tgrace_d / ts then
        body.T = 1 + (body.T - 1) * math.exp(-ts / (7 * P.tauDownWk))
    else
        body.T = P.Tmax - (P.Tmax - body.T) * math.exp(-K.min(1, S / P.Wsat) * ts / (7 * P.tauUpWk))
    end
end

-- One closed day of the body (spec sections 5, 5.1 and 6), the oracle's exact Body.day: growth (regain
-- inside it) scaled by the biology clock ts, detraining at the day's opening status, the partition arm by
-- the sign of E (each charges growth's energy at grow / ts, ruling 13-3), the floors (lm >= fMinShare * F0,
-- lx >= 0, fm >= fmMin), then the peak and the neural factor (which reads S only). A tdee at or below 0, or
-- NaN, reads the energy gate at balance: the gate's surplus share divides by it. Writes lm, lx, fm, Pk,
-- grace, T and Tgrace; returns the day's dF, dX, dM before the floors.
function K.strength.day(body, S, p, E, tdee, alcGkg, P, ts)
    local s = K.strength.status(body)
    local Egate = E
    local tdeeGate = tdee
    if not (tdee > 0) then
        Egate = K.min(E, 0)
        tdeeGate = 1
    end
    local grow = K.strength.growth(body, S, p, Egate, tdeeGate, alcGkg, P) * ts
    local dF = grow - K.strength.detrain(body, S, s, P, ts)
    local dX = 0
    local dM = 0
    if E >= 0 then
        dX, dM = K.partition.surplusLean(body, grow, S, p, E, P, ts)
    else
        local dFp = 0
        dFp, dX, dM = K.partition.deficitLean(body, grow, S, p, E, P, ts)
        dF = dF + dFp
    end
    body.lm = K.max(body.lm + dF, P.fMinShare * body.F0)
    body.lx = K.max(body.lx + dX, 0)
    body.fm = K.max(body.fm + dM, P.fmMin)
    K.strength.peakStep(body, P, ts)
    K.strength.neural(body, S, P, ts)
    return dF, dX, dM
end

K.strength.DEFAULTS.M5 = K.strength.fOfBio(5, K.strength.DEFAULTS) - K.strength.DEFAULTS.Fnm -- F5 - Fnm, so S = 1 at the average
K.strength.DEFAULTS.R = K.strength.R(K.strength.DEFAULTS.yearsTo10) -- the S of level 10 (ruling 13-45)
K.strength.DEFAULTS.ffmiNaturalRaw = K.strength.DEFAULTS.ffmiNatural - K.strength.DEFAULTS.kouriCoef * (1.8 - K.HEIGHT_M) -- the raw FFMI limit at K.HEIGHT_M, 24.37 at 1.70 m (ruling 13-47)
-- ============================================================ the Plan 3 model (removed in Plan 13 Task 12)

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
K.strength.DEHYD_STEP1 = -0.03 -- S0623 (~−2 %): −0.03 a game choice
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
K.strength.VITD_PENALTY = -0.03 -- S0633 SMD 0.17 → −0.03: an SMD→% game choice (S0634 disagrees)
K.strength.FAT_PER_10PT = -0.03 -- S0651 (≥ 6 % weaker per FFM in obesity): −0.03 per 10 points over 30 % a game mapping
K.strength.FAT_KNEE = 0.30 -- S0651 (≥ 6 % weaker per FFM in obesity): −0.03 per 10 points over 30 % a game mapping
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
