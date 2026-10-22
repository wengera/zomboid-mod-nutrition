-- NR_Kernel_Strength.lua -- the body model's Strength (Plan 13, the lean-mass model): the constants table and its
-- sandbox options, the bio scale and the strength level, the growth law, detraining, regain and the remembered peak,
-- the neural factor T, the signal ring's day close and one closed day of the body (K.strength.day); beside them the
-- vanilla band of a level, the carry's trait factor and the acute carry factor. The level is written at the day close
-- by the server's Strength adapter (Plan 13 Task 14), never here.
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
-- functions they read; every other value is a registry row (NR_Data_Dials.lua, the strength block).
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
    startLevel = { STRONG = 9, STOUT = 7, none = 5, FEEBLE = 3, WEAK = 1 }, -- VANILLA: vanilla's start levels but Weak's (vanilla 0, the mod's floor 1)
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

-- The growth law's coordinate: the lean F at bio level L (FFMI ffmi5 at 5, ffmiPerLevel a level, at K.HEIGHT_M).
function K.strength.fOfBio(L, P)
    return (P.ffmi5 + (L - 5) * P.ffmiPerLevel) * (K.HEIGHT_M * K.HEIGHT_M)
end

-- The bio level of a lean F, the inverse of fOfBio.
-- The untrained average's lean Favg, fOfBio(5) of DEFAULTS (52.02 kg at 1.70 m), read at call time so it follows
-- K.HEIGHT_M: the reference the lean-scaled fat cuts and the fat starts divide by (Task 10b).
function K.strength.averageLean()
    return K.strength.fOfBio(5, K.strength.DEFAULTS)
end

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

-- The shown level's drop margin (Plan 13 Task 10c): the written level falls only once the continuous level is this
-- far below it, so a day's small loss never drops a level the next day's regain would restore.
K.strength.DROP_MARGIN = K.dials.get("strength.DROP_MARGIN")

-- The written perk level n and the bar's fraction for continuous level L under the level last written Lw (nil, or not
-- a finite number, when none was written): n rises to floor(L) (shown's floor) when that is above Lw; drops to
-- floor(L + DROP_MARGIN), with shown's epsilon, only when L < Lw - DROP_MARGIN; else holds at Lw, clamped to
-- [0, L_MAX]. frac is L - n where L is above n and below L_MAX, else 0 (a held level shows an empty bar).
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

-- The day's two lean-gain arms in kg, the biology clock ts applied to each (spec section 5); K.strength.day
-- composes them as their max. The growth arm: k a week times the room to the cap Fc, the signal, the two
-- gates and the alcohol gate, an Euler step times ts, never negative. The regain arm, while lm sits below the
-- held peak Pk (else 0): half-life regain_hl_wk at the signal capped at 1 and the same three gates (a drinking
-- day blunts the same synthesis, controller ruling), integrated exactly over the day, so the gap Pk - lm
-- closes by 1 - exp(-lr * min(1, G) * gates * ts / 7) and never past Pk at any clock (Task 11c, Task 11
-- review I-2: the Euler form's fraction ln2 * ts / (7 * regain_hl_wk) exceeds 1 inside the option ranges).
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

-- The signal ring's day close (ruling 13-12): sig7 shifts one slot (slot 1 the oldest), the day's sigDay lands in
-- slot 7 and is zeroed. Returns the ring's sum, the closed week's Strength XP (the caller divides by xpPerSet).
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

-- One closed day of the body (spec sections 5, 5.1 and 6), the oracle's exact Body.day: the larger of
-- growth's two arms (each with the biology clock ts applied), detraining at the day's opening status, the
-- partition arm by the sign of E (each charges growth's energy at grow / ts, ruling 13-3), the floors
-- (lm >= fMinShare * F0, lx >= 0, fm >= fmMin), then the peak and the neural factor (which reads S only). A tdee at or
-- below 0, or NaN, reads the energy gate at balance: the gate's surplus share divides by it. Writes lm, lx, fm, Pk,
-- grace, T and Tgrace; returns the day's dF, dX, dM before the floors.
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

-- An immobilised day of the body (rulings 13-13 and 13-35), in place of K.strength.day: the disuse arm
-- (K.partition.disuse; the adapter stamps its day count tDisuse and anchor lm0dis) applied under the same floors
-- (lm >= fMinShare * F0, fm >= fmMin) with lx untouched; detraining runs at the day's opening status for its grace
-- counter alone, its kg discarded (the disuse curve already carries the immobilised loss); the neural factor steps and
-- the peak does not. Writes lm, fm, grace, T and Tgrace; returns the disuse arm's dFM, dLM before the floors.
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
-- The strength sandbox options (Plan 13 Task 11; spec section 10; Plan 19 Task 3f): the registry's strength rows that
-- carry an option (opt) read into a server's P table (param), built at load by K.dials.paramOptions (NR_Kernel_Dials.lua),
-- one entry a row sorted by id: { id, key, opt, value, min, max, int, written }. A DEFAULTS row's option sets its P key;
-- RATE's multiplies k and PROTEIN_FULL's scales the protein knots' x. A double clamps to its range, an integer reads
-- the default out of range (K.readLeaf), and a read at the option file's three-place default reads the row's exact
-- value (K.dials.readParam: StrengthMaintainShare's 0.333 is m's third). tools/sandbox_options.py writes the option
-- file from the same rows, so a row is the option's one declaration.
K.strength.OPTIONS = K.dials.paramOptions("strength")

-- The protein x at which the gate reaches 1, the last protein knot's (DEFAULTS.fp_knots[4][1] is this dial);
-- StrengthProteinFull moves it by scaling every knot's x.
K.strength.PROTEIN_FULL = K.dials.get("strength.PROTEIN_FULL")

-- The multiplier StrengthRate puts on the fitted growth rate k: 1, k itself.
K.strength.RATE = K.dials.get("strength.RATE")

-- R's cache, one entry: the year value it was run for and its result; params re-runs K.strength.R only when the
-- option's year value differs from the last one (R is 365 steps a year, Rule 6).
local rYears = K.strength.DEFAULTS.yearsTo10
local rValue = K.strength.DEFAULTS.R

-- The strength parameters P of a sandbox table sv (SandboxVars.NR, or nil): a new table from DEFAULTS with every
-- option read through K.dials.readParam, k scaled by StrengthRate and the protein knots' x by StrengthProteinFull / K.strength.PROTEIN_FULL,
-- R for the year option and M5 from DEFAULTS (ruling 13-45). The load guard: at bio level 15's status in the
-- effective cap's room (capLevel held at the natural limit) the growth threshold must sit under the set cap, else
-- beta, Sg0 and Smax1 revert to DEFAULTS; returns P and whether it fell back.
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
    if capBio > 15 then
        local s15 = (15 - 5) / (capBio - 5)
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

-- The Java perk cap: getTotalXpForLevel(11) == getTotalXpForLevel(10) (#2859); BeyondTen's mastery
-- levels 11-15 live in its own modData, outside the model.
K.strength.L_MAX = K.dials.get("strength.L_MAX")

-- The acute carry terms. Dehydration in two steps (percent body mass), scaled by DEHYD_SWEAT_K when
-- the deficit arose from sweat or heat.
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

-- The acute factor's clamp.
K.strength.E_ACUTE_MIN = K.dials.get("strength.E_ACUTE_MIN")
K.strength.E_ACUTE_MAX = K.dials.get("strength.E_ACUTE_MAX")

-- Vanilla's band remap as {highest level, trait}: the first row whose level is >= the shown level.
-- Level 5 carries no band trait (its row's trait is nil).
K.strength.BANDS = { { 1, "WEAK" }, { 4, "FEEBLE" }, { 5, nil }, { 8, "STOUT" }, { 10, "STRONG" } } -- #2157: WEAK 0-1, FEEBLE 2-4, none 5, STOUT 6-8, STRONG >= 9
-- The four muscle-band trait names (CharacterTrait registry fields), the one list every server reader walks:
-- vanilla's remap removes them before it adds one back (#2157), and vanilla never lets a character hold two, so the
-- order is moot.
K.strength.MUSCLE_TRAITS = { "WEAK", "FEEBLE", "STOUT", "STRONG" }

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
-- past the knee (halved from AM_FROM_H to AM_TO_H of the body clock's hourOfDay, K.circadian.hour; nil, with sleep
-- off, halves nothing: a game choice, Plan 16 spec section 6), capped, caffeine, clinical vitamin D deficiency and
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

-- The carry's trait factor by muscle band: the constructor's own values for the band trait a level implies (#2144;
-- ruling 13-7); the level-5 band, none, reads 1.
K.strength.TRAIT_CARRY = { WEAK = 0.75, FEEBLE = 0.9, STOUT = 1.25, STRONG = 1.5 } -- #2144 VANILLA

-- The carry's trait factor at Strength level n: TRAIT_CARRY of the band bandOf(n), 1 with no band (ruling 13-7).
function K.strength.traitCarry(n)
    return K.strength.TRAIT_CARRY[K.strength.bandOf(n)] or 1
end

-- The carry delta written through setMaxWeightDelta: the trait factor (traitCarry) times (1 + eAcute).
function K.strength.carryDelta(traitCarry, eAcute)
    return traitCarry * (1 + eAcute) -- ruling 11
end

-- ============================================================ the AddXP capture (spec section 4, ruling 13-11)
-- The protein factor vanilla's XP.AddXP applies off the server's protein store (#2112; the 42.21 jar's AddXP
-- @107-@190): x1.5 strictly between 50 and 300, x0.7 strictly below -300, else 1.
K.strength.PROTEIN_LO = 50 -- #2112 VANILLA
K.strength.PROTEIN_HI = 300 -- #2112 VANILLA
K.strength.PROTEIN_HI_FACTOR = 1.5 -- #2112 VANILLA
K.strength.PROTEIN_NEG = -300 -- #2112 VANILLA
K.strength.PROTEIN_NEG_FACTOR = 0.7 -- #2112 VANILLA

-- The protein factor of a store (a NaN store compares false everywhere and reads 1).
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

-- One Strength grant's training signal, in Strength XP before vanilla's multipliers: 0 for a non-finite or
-- non-positive amount; else the amount divided by the protein factor of store, the sandbox multiplier (one that is
-- not a positive finite number reads 1) and the book multiplier when above 1 (a non-finite one reads 1; #2113), times
-- 1 for a grant inside a recorded Fitness set (fitness true) or P.incidental for any other (S1951, S1961, S1962).
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

-- The Strength XP before vanilla's multiplier chain that lands as xp after it: xp divided by the protein factor of
-- store, the sandbox multiplier (one that is not a positive finite number reads 1) and the book multiplier when above
-- 1 (a non-finite one reads 1). The capture's division (a landed grant back to its raw size) and the pin's (the raw
-- grant that lands as the bar's fraction, ruling 13-9).
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

-- ============================================================ the level write (spec section 7, Plan 13 Task 14)
-- The native XP pinned for shown level n and bar fraction frac over the cumulative ladder totals (totals[0] = 0):
-- level n's starting total plus frac of the way to the next, at most 1 XP below it (ruling 13-9; a float frac near 1
-- never lands on the next level's total); at L_MAX the level-9 total, the park, so
-- the engine's AddXP keeps firing its event (it returns before the event at the level-10 total, #2109).
function K.strength.pinXp(n, frac, totals)
    if n >= K.strength.L_MAX then
        return totals[K.strength.L_MAX - 1]
    end
    local gap = totals[n + 1] - totals[n]
    return totals[n] + K.min(frac * gap, gap - 1)
end

-- BeyondTen's mastery levels end at 15 (its BT.MAX_LEVEL, Shared.lua:10-12).
K.strength.MASTERY_MAX = K.dials.get("strength.MASTERY_MAX")

-- BeyondTen's stored mastery XP for shown level L (ruling 13-42): cost(f) + (L - f) (cost(f + 1) - cost(f)) with f the
-- floor of L + 1e-9 (shown's epsilon), clamped to [L_MAX, MASTERY_MAX]; cost(MASTERY_MAX) at or above it. cost(level)
-- is BeyondTen's cumulative mastery cost from level 10 (GetTotalMasteryCost for the Strength perk), 0 at 10.
function K.strength.masteryXp(L, cost)
    local f = K.clamp(math.floor(L + 1e-9), K.strength.L_MAX, K.strength.MASTERY_MAX)
    local base = cost(f)
    if f >= K.strength.MASTERY_MAX then
        return base
    end
    local frac = K.clamp(L - f, 0, 1)
    return base + frac * (cost(f + 1) - base)
end
