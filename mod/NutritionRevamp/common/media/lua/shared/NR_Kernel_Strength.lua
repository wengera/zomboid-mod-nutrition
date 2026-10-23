-- NR_Kernel_Strength.lua: the lean-mass Strength model (constants and options, the bio scale and level, growth,
-- detraining, regain, the peak, the neural factor T, one closed day), the band and carry factors, and the AddXP
-- capture. The level is written at the day close by NR_Server_Strength, never here. Pure, no Java; slow-clock code.
-- Sorts after NR_Kernel.lua; DEFAULTS.R is computed at this file's load, so K.clamp, K.min, K.max and K.HEIGHT_M
-- must already be defined there.
local K = NutritionRevamp.kernel
K.strength = {}

-- ============================================================ the lean-mass strength model
-- The fitted constants are point T (data/fits/strength-refit-T/compact_T.json "chosen", the oracle's key names).
-- K.strength.params merges a server's options over a copy, taken as P below; M5, R and ffmiNaturalRaw are derived
-- at file load, after the functions they read.
K.strength.DEFAULTS = {
    -- point T (the growth law, the energy gate, the lean partition)
    k = K.dials.get("strength.DEFAULTS.k"),
    beta = K.dials.get("strength.DEFAULTS.beta"),
    Sg0 = K.dials.get("strength.DEFAULTS.Sg0"),
    Sref = K.dials.get("strength.DEFAULTS.Sref"),
    Smax = K.dials.get("strength.DEFAULTS.Smax"),
    Smax1 = K.dials.get("strength.DEFAULTS.Smax1"),
    fp_knots = { { K.dials.get("strength.DEFAULTS.fp_knots.1.1"), 0 }, { K.dials.get("strength.DEFAULTS.fp_knots.2.1"), K.dials.get("strength.DEFAULTS.fp_knots.2.2") }, { K.dials.get("strength.DEFAULTS.fp_knots.3.1"), K.dials.get("strength.DEFAULTS.fp_knots.3.2") }, { K.dials.get("strength.DEFAULTS.fp_knots.4.1"), 1.0 } }, -- the gate's 0 and 1 are its ends: no row needed
    E0 = K.dials.get("strength.DEFAULTS.E0"),
    E0_drop = K.dials.get("strength.DEFAULTS.E0_drop"),
    fbal0 = K.dials.get("strength.DEFAULTS.fbal0"),
    fbal_drop = K.dials.get("strength.DEFAULTS.fbal_drop"),
    surplus_full = K.dials.get("strength.DEFAULTS.surplus_full"),
    full_drop = K.dials.get("strength.DEFAULTS.full_drop"),
    a_nov = K.dials.get("strength.DEFAULTS.a_nov"),
    trained_need = K.dials.get("strength.DEFAULTS.trained_need"),
    forbes_c = K.dials.get("strength.DEFAULTS.forbes_c"),
    wT = K.dials.get("strength.DEFAULTS.wT"),
    S_def = K.dials.get("strength.DEFAULTS.S_def"),
    wP = K.dials.get("strength.DEFAULTS.wP"),
    pdef_lo = K.dials.get("strength.DEFAULTS.pdef_lo"),
    pdef_hi = K.dials.get("strength.DEFAULTS.pdef_hi"),
    prot_floor = K.dials.get("strength.DEFAULTS.prot_floor"),
    x_max_frac = K.dials.get("strength.DEFAULTS.x_max_frac"),
    x_tau_d = K.dials.get("strength.DEFAULTS.x_tau_d"),
    m = K.dials.get("strength.DEFAULTS.m"),
    grace_d = K.dials.get("strength.DEFAULTS.grace_d"),
    detrain_hl_wk = K.dials.get("strength.DEFAULTS.detrain_hl_wk"),
    detrain_status = K.dials.get("strength.DEFAULTS.detrain_status"),
    regain_hl_wk = K.dials.get("strength.DEFAULTS.regain_hl_wk"),
    peak_hl_yr = K.dials.get("strength.DEFAULTS.peak_hl_yr"),
    -- the game constants
    ffmi5 = K.dials.get("strength.DEFAULTS.ffmi5"),
    ffmiPerLevel = K.dials.get("strength.DEFAULTS.ffmiPerLevel"),
    capLevel = K.dials.get("strength.DEFAULTS.capLevel"),
    ts = K.dials.get("strength.DEFAULTS.ts"),
    xpPerSet = K.dials.get("strength.DEFAULTS.xpPerSet"),
    incidental = K.dials.get("strength.DEFAULTS.incidental"),
    fMinShare = K.dials.get("strength.DEFAULTS.fMinShare"),
    fmMin = K.dials.get("strength.DEFAULTS.fmMin"),
    nov_p0 = K.dials.get("strength.DEFAULTS.nov_p0"),
    nov_pspan = K.dials.get("strength.DEFAULTS.nov_pspan"),
    xs_p0 = K.dials.get("strength.DEFAULTS.xs_p0"),
    xs_pspan = K.dials.get("strength.DEFAULTS.xs_pspan"),
    -- the strength-model block (ruling 13-45)
    b = K.dials.get("strength.DEFAULTS.b"),
    Fnm = K.dials.get("strength.DEFAULTS.Fnm"),
    N0 = { STRONG = K.dials.get("strength.DEFAULTS.N0.STRONG"), STOUT = K.dials.get("strength.DEFAULTS.N0.STOUT"), none = 1.0, FEEBLE = K.dials.get("strength.DEFAULTS.N0.FEEBLE"), WEAK = K.dials.get("strength.DEFAULTS.N0.WEAK") }, -- none is the untrained average, 1 by definition: no row needed
    startLevel = { STRONG = 9, STOUT = 7, none = 5, FEEBLE = 3, WEAK = 1 }, -- VANILLA #3879: vanilla's start levels, but WEAK 1 is the mod's level floor (vanilla 0): no row needed
    traitShare = K.dials.get("strength.DEFAULTS.traitShare"),
    ffmiNatural = K.dials.get("strength.DEFAULTS.ffmiNatural"),
    kouriCoef = K.dials.get("strength.DEFAULTS.kouriCoef"),
    Tmax = K.dials.get("strength.DEFAULTS.Tmax"),
    tauUpWk = K.dials.get("strength.DEFAULTS.tauUpWk"),
    tauDownWk = K.dials.get("strength.DEFAULTS.tauDownWk"),
    Tgrace_d = K.dials.get("strength.DEFAULTS.Tgrace_d"),
    Wsat = K.dials.get("strength.DEFAULTS.Wsat"),
    yearsTo10 = K.dials.get("strength.DEFAULTS.yearsTo10"),
    perfectS = K.dials.get("strength.DEFAULTS.perfectS"),
    perfectP = K.dials.get("strength.DEFAULTS.perfectP"),
    perfectE = K.dials.get("strength.DEFAULTS.perfectE"),
}

-- FFMI ffmi5 at 5, ffmiPerLevel a level, at K.HEIGHT_M.
function K.strength.fOfBio(L, P)
    return (P.ffmi5 + (L - 5) * P.ffmiPerLevel) * (K.HEIGHT_M * K.HEIGHT_M)
end

-- The untrained average's lean, read at call time so it follows K.HEIGHT_M: the fat cuts and fat starts divide by it.
function K.strength.averageLean()
    return K.strength.fOfBio(5, K.strength.DEFAULTS)
end

function K.strength.bioLevel(F, P)
    return 5 + (F / (K.HEIGHT_M * K.HEIGHT_M) - P.ffmi5) / P.ffmiPerLevel
end

-- 0 at or below Fnm.
function K.strength.strengthOf(F, N0, T, P)
    if F <= P.Fnm then
        return 0
    end
    return ((F - P.Fnm) / P.M5) ^ P.b * N0 * T
end

-- Linear in S: 5 at the untrained average (S = 1), 10 at S = R.
function K.strength.level(F, N0, T, P)
    return 5 + 5 * (K.strength.strengthOf(F, N0, T, P) - 1) / (P.R - 1)
end

-- Fnm where that level needs S <= 0.
function K.strength.fOfLevel(L, N0, T, P)
    local S = 1 + (L - 5) * (P.R - 1) / 5
    if S <= 0 then
        return P.Fnm
    end
    return P.Fnm + P.M5 * (S / (N0 * T)) ^ (1 / P.b)
end

function K.strength.threshold(s, P)
    return P.Sg0 * math.exp(P.beta * s)
end

function K.strength.setCap(s, P)
    return P.Smax + (P.Smax1 - P.Smax) * s
end

-- 1 at Sref for a novice.
function K.strength.signal(S, s, P)
    local root = math.sqrt(K.min(S, K.strength.setCap(s, P))) - math.sqrt(K.strength.threshold(s, P))
    return K.max(0, root) / (math.sqrt(P.Sref) - math.sqrt(P.Sg0))
end

-- The S of the untrained average after `years` of perfect training. Reads DEFAULTS only; about 365 steps a year, so it
-- runs at file load and at a yearsTo10 change only (Rule 6).
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

-- n floors L + 1e-9, so a start built exactly on its level never floors one low; frac is 0 below 0 and at the cap.
function K.strength.shown(L)
    local n = K.clamp(math.floor(L + 1e-9), 0, K.strength.L_MAX)
    local frac = 0
    if L >= 0 and n < K.strength.L_MAX then
        frac = K.max(0, L - n)
    end
    return n, frac
end

-- The written level falls only this far below, so a day's small loss never drops a level the next day restores.
K.strength.DROP_MARGIN = K.dials.get("strength.DROP_MARGIN")

-- Rises to floor(L) above Lw; drops only when L < Lw - DROP_MARGIN; else holds Lw (nil or non-finite Lw: none
-- written). A held level shows an empty bar.
function K.strength.heldLevel(L, Lw)
    local n, frac = K.strength.shown(L)
    if not K.finite(Lw) or n > Lw then
        return n, frac
    end
    if L < Lw - K.strength.DROP_MARGIN then
        n = K.clamp(math.floor(L + K.strength.DROP_MARGIN + 1e-9), 0, K.strength.L_MAX)
    else
        n = K.clamp(Lw, 0, K.strength.L_MAX)
    end
    frac = 0
    if L > n and n < K.strength.L_MAX then
        frac = L - n
    end
    return n, frac
end

-- Lean above the set point as a share of the cap's room; 0 when the cap sits at or below the set point.
function K.strength.status(body)
    if body.Fc <= body.F0 then
        return 0
    end
    return K.clamp((body.lm - body.F0) / (body.Fc - body.F0), 0, 1)
end

function K.strength.fp(p, P)
    return K.interp(P.fp_knots, p)
end

-- Zero at the status zero point E0s (deepened for a high-protein novice) and below; bal times the way from E0s in a
-- deficit; toward 1 across a surplus saturating at surplus_full of tdee.
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

-- The growth arm, an Euler step; the regain arm toward the held peak Pk, integrated exactly so it never passes Pk at
-- any clock (the Euler fraction exceeds 1 inside the option ranges). A drinking day blunts both.
function K.strength.growth(body, S, p, E, tdee, alcGkg, P, ts)
    local s = K.strength.status(body)
    local G = K.strength.signal(S, s, P)
    local gates = K.strength.fp(p, P) * K.strength.fe(E, s, p, tdee, P) * K.partition.gAlc(alcGkg)
    local grow = K.max(0, P.k * (body.Fc - body.lm) * G * gates / 7) * ts
    local regain = 0
    if body.lm < body.Pk then
        local lr = math.log(2) / P.regain_hl_wk
        regain = (body.Pk - body.lm) * (1 - math.exp(-lr * K.min(1, G) * gates * ts / 7))
    end
    return grow, regain
end

function K.strength.maintainSets(s, P)
    return P.m * K.strength.threshold(s, P)
end

-- Past grace_d / ts days below S_m, and only above F0, lm - F0 decays, integrated exactly so no clock overshoots F0.
-- At ts > grace_d a day below S_m detrains at grace 1, as the oracle does.
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

-- Pk holds the highest lm, then decays toward lm (peak_hl_yr), the biology clock scaling the day.
function K.strength.peakStep(body, P, ts)
    local Pk = K.max(body.Pk, body.lm)
    body.Pk = body.lm + (Pk - body.lm) * math.exp(-math.log(2) / (P.peak_hl_yr * 365) * ts)
end

-- Past Tgrace_d / ts days below m * Wsat, T decays toward 1; else it rises toward Tmax, both exact over the day.
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

-- Slot 1 the oldest; returns the ring's sum, the closed week's Strength XP (the caller divides by xpPerSet).
function K.strength.signalClose(body)
    local ring = body.sig7
    local n = K.body.WEEK_N
    for i = 1, n - 1 do
        ring[i] = ring[i + 1]
    end
    ring[n] = body.sigDay
    body.sigDay = 0
    local sum = 0
    for i = 1, n do
        sum = sum + ring[i]
    end
    return sum
end

-- The oracle's exact Body.day. Partition by the sign of E charges growth's energy at grow / ts. A tdee at or below 0,
-- or NaN, reads the energy gate at balance, since the gate divides by it. Returns dF, dX, dM before the floors.
function K.strength.day(body, S, p, E, tdee, alcGkg, P, ts)
    local s = K.strength.status(body)
    local Egate = E
    local tdeeGate = tdee
    if not (tdee > 0) then
        Egate = K.min(E, 0)
        tdeeGate = 1
    end
    local grow, regain = K.strength.growth(body, S, p, Egate, tdeeGate, alcGkg, P, ts)
    grow = K.max(grow, regain)
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

-- In place of K.strength.day: the disuse arm under the same floors, lx untouched; detraining runs for its grace counter
-- alone, its kg discarded (the disuse curve already carries the loss); T steps, the peak does not.
function K.strength.disuseDay(body, S, P, ts)
    local s = K.strength.status(body)
    local dFM, dLM = K.partition.disuse(body)
    body.fm = K.max(body.fm + dFM, P.fmMin)
    body.lm = K.max(body.lm + dLM, P.fMinShare * body.F0)
    K.strength.detrain(body, S, s, P, ts)
    K.strength.neural(body, S, P, ts)
    return dFM, dLM
end

K.strength.DEFAULTS.M5 = K.strength.fOfBio(5, K.strength.DEFAULTS) - K.strength.DEFAULTS.Fnm -- F5 - Fnm, so S = 1 at the average
K.strength.DEFAULTS.R = K.strength.R(K.strength.DEFAULTS.yearsTo10) -- the S of level 10 (ruling 13-45)
K.strength.DEFAULTS.ffmiNaturalRaw = K.strength.DEFAULTS.ffmiNatural - K.strength.DEFAULTS.kouriCoef * (1.8 - K.HEIGHT_M) -- the raw FFMI limit at K.HEIGHT_M, 24.37 at 1.70 m (ruling 13-47); 1.8 m is ffmiNatural's normalisation height (its row): no row needed
-- The strength sandbox options: the registry rows that carry an option. RATE multiplies k and PROTEIN_FULL scales the
-- protein knots' x; a read at the option file's three-place default reads the row's exact value (K.dials.readParam).
-- tools/sandbox_options.py writes the option file from the same rows, so a row is the option's one declaration.
K.strength.OPTIONS = K.dials.paramOptions("strength")

-- fp_knots[4][1] is this dial; StrengthProteinFull moves it by scaling every knot's x.
K.strength.PROTEIN_FULL = K.dials.get("strength.PROTEIN_FULL")

K.strength.RATE = K.dials.get("strength.RATE")

-- R's one-entry cache: R is 365 steps a year (Rule 6), so it re-runs only for a new year value.
local rYears = K.strength.DEFAULTS.yearsTo10
local rValue = K.strength.DEFAULTS.R

-- The load guard: at bio level 15's status, if the growth threshold reaches the set cap, beta, Sg0 and Smax1 revert to
-- DEFAULTS; returns P and whether it fell back.
function K.strength.params(sv)
    local S = K.strength
    local D = S.DEFAULTS
    local P = {}
    for key, value in pairs(D) do
        P[key] = value
    end
    local rows = S.OPTIONS
    local kMul = S.RATE
    local pFull = S.PROTEIN_FULL
    for i = 1, #rows do
        local row = rows[i]
        local live = D[row.key]
        if row.key == "RATE" then
            live = S.RATE
        elseif row.key == "PROTEIN_FULL" then
            live = S.PROTEIN_FULL
        end
        local v = K.dials.readParam(sv, row, live)
        if row.key == "RATE" then
            kMul = v
        elseif row.key == "PROTEIN_FULL" then
            pFull = v
        else
            P[row.key] = v
        end
    end
    P.k = D.k * kMul
    local scale = pFull / S.PROTEIN_FULL
    local knots = {}
    for i = 1, #D.fp_knots do
        knots[i] = { D.fp_knots[i][1] * scale, D.fp_knots[i][2] }
    end
    P.fp_knots = knots
    if P.yearsTo10 ~= rYears then
        rValue = S.R(P.yearsTo10)
        rYears = P.yearsTo10
    end
    P.R = rValue
    P.M5 = D.M5
    local fellBack = false
    local capBio = K.min(P.capLevel, 5 + (P.ffmiNaturalRaw - P.ffmi5) / P.ffmiPerLevel) -- K.body.create holds Fc at the natural limit
    if capBio > K.strength.MASTERY_MAX then
        local s15 = (K.strength.MASTERY_MAX - 5) / (capBio - 5)
        if S.threshold(s15, P) >= S.setCap(s15, P) then
            P.beta = D.beta
            P.Sg0 = D.Sg0
            P.Smax1 = D.Smax1
            fellBack = true
        end
    end
    return P, fellBack
end

-- ============================================================ the level band and the carry

-- getTotalXpForLevel(11) == getTotalXpForLevel(10) (#2859); BeyondTen's levels 11-15 live in its own modData.
K.strength.L_MAX = K.dials.get("strength.L_MAX")

-- Dehydration in two steps (% body mass), scaled by DEHYD_SWEAT_K when sweat or heat caused it.
K.strength.DEHYD_PCT1 = K.dials.get("strength.DEHYD_PCT1")
K.strength.DEHYD_STEP1 = K.dials.get("strength.DEHYD_STEP1")
K.strength.DEHYD_PCT2 = K.dials.get("strength.DEHYD_PCT2")
K.strength.DEHYD_STEP2 = K.dials.get("strength.DEHYD_STEP2")
K.strength.DEHYD_SWEAT_K = K.dials.get("strength.DEHYD_SWEAT_K")

-- Hours awake past the knee cost SLEEP_PER_H per hour, capped; halved from dawn to noon.
K.strength.SLEEP_KNEE_H = K.dials.get("strength.SLEEP_KNEE_H")
K.strength.SLEEP_PER_H = K.dials.get("strength.SLEEP_PER_H")
K.strength.SLEEP_CAP = K.dials.get("strength.SLEEP_CAP")
K.strength.SLEEP_AM_FACTOR = K.dials.get("strength.SLEEP_AM_FACTOR")
K.strength.AM_FROM_H = K.dials.get("strength.AM_FROM_H")
K.strength.AM_TO_H = K.dials.get("strength.AM_TO_H")

-- Caffeine, clinical vitamin D deficiency and body fat above the knee (per 10 points of fat fraction).
K.strength.CAFFEINE_BONUS = K.dials.get("strength.CAFFEINE_BONUS")
K.strength.VITD_PENALTY = K.dials.get("strength.VITD_PENALTY")
K.strength.FAT_PER_10PT = K.dials.get("strength.FAT_PER_10PT")
K.strength.FAT_KNEE = K.dials.get("strength.FAT_KNEE")
K.strength.FAT_PER_PTS = K.dials.get("strength.FAT_PER_PTS")

K.strength.E_ACUTE_MIN = K.dials.get("strength.E_ACUTE_MIN")
K.strength.E_ACUTE_MAX = K.dials.get("strength.E_ACUTE_MAX")

-- {highest level, trait}: the first row at or above the shown level; level 5 carries no trait.
K.strength.BANDS = { { 1, "WEAK" }, { 4, "FEEBLE" }, { 5, nil }, { 8, "STOUT" }, { 10, "STRONG" } } -- #2157: WEAK 0-1, FEEBLE 2-4, none 5, STOUT 6-8, STRONG >= 9
-- Vanilla's remap removes all four before it adds one back (#2157) and never lets a character hold two.
K.strength.MUSCLE_TRAITS = { "WEAK", "FEEBLE", "STOUT", "STRONG" }

function K.strength.bandOf(level)
    local bands = K.strength.BANDS
    for i = 1, #bands do
        if level <= bands[i][1] then
            return bands[i][2]
        end
    end
    return bands[#bands][2]
end

-- The sum clamped to [E_ACUTE_MIN, E_ACUTE_MAX]. The morning halving reads the body clock (K.circadian.hour); nil, with
-- sleep off, halves nothing (a game choice).
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
    if hourOfDay ~= nil and hourOfDay >= S.AM_FROM_H and hourOfDay < S.AM_TO_H then
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

-- The constructor's own values (#2144).
K.strength.TRAIT_CARRY = { WEAK = 0.75, FEEBLE = 0.9, STOUT = 1.25, STRONG = 1.5 } -- VANILLA #2144

function K.strength.traitCarry(n)
    return K.strength.TRAIT_CARRY[K.strength.bandOf(n)] or 1
end

function K.strength.carryDelta(traitCarry, eAcute)
    return traitCarry * (1 + eAcute) -- ruling 11
end

-- ============================================================ the AddXP capture
-- Vanilla's XP.AddXP protein factor off the server's store (#2112): x1.5 strictly between 50 and 300, x0.7 below -300.
K.strength.PROTEIN_LO = 50 -- VANILLA #2112
K.strength.PROTEIN_HI = 300 -- VANILLA #2112
K.strength.PROTEIN_HI_FACTOR = 1.5 -- VANILLA #2112
K.strength.PROTEIN_NEG = -300 -- VANILLA #2112
K.strength.PROTEIN_NEG_FACTOR = 0.7 -- VANILLA #2112

-- A NaN store compares false everywhere and reads 1.
function K.strength.proteinFactor(store)
    local S = K.strength
    if store > S.PROTEIN_LO and store < S.PROTEIN_HI then
        return S.PROTEIN_HI_FACTOR
    end
    if store < S.PROTEIN_NEG then
        return S.PROTEIN_NEG_FACTOR
    end
    return 1
end

-- 0 for a non-finite or non-positive amount; a grant outside a recorded Fitness set counts P.incidental (S1951).
function K.strength.capture(amount, store, sandboxMult, bookMult, fitness, P)
    if not K.finite(amount) or not (amount > 0) then
        return 0
    end
    local xp = K.strength.rawXp(amount, store, sandboxMult, bookMult)
    if fitness then
        return xp
    end
    return xp * P.incidental
end

-- Divides out the protein factor, the sandbox multiplier and a book multiplier above 1 (non-finite ones read 1, #2113):
-- the capture's division and the pin's (the raw grant that lands as the bar's fraction).
function K.strength.rawXp(xp, store, sandboxMult, bookMult)
    local sm = sandboxMult
    if not K.finite(sm) or not (sm > 0) then
        sm = 1
    end
    local bm = bookMult
    if not K.finite(bm) then
        bm = 1
    end
    return xp / K.strength.proteinFactor(store) / sm / K.max(1, bm)
end

-- ============================================================ the level write
-- Level n's starting total plus frac of the way, at most 1 XP below the next (a float frac near 1 never lands on it);
-- at L_MAX the level-9 total, so the engine's AddXP keeps firing its event (#2109).
function K.strength.pinXp(n, frac, totals)
    if n >= K.strength.L_MAX then
        return totals[K.strength.L_MAX - 1]
    end
    local gap = totals[n + 1] - totals[n]
    return totals[n] + K.min(frac * gap, gap - 1)
end

-- BeyondTen's BT.MAX_LEVEL (Shared.lua:10-12).
K.strength.MASTERY_MAX = K.dials.get("strength.MASTERY_MAX")

-- cost(level) is BeyondTen's cumulative mastery cost from level 10 (GetTotalMasteryCost), 0 at 10; f floors L + 1e-9.
function K.strength.masteryXp(L, cost)
    local f = K.clamp(math.floor(L + 1e-9), K.strength.L_MAX, K.strength.MASTERY_MAX)
    local base = cost(f)
    if f >= K.strength.MASTERY_MAX then
        return base
    end
    local frac = K.clamp(L - f, 0, 1)
    return base + frac * (cost(f + 1) - base)
end
