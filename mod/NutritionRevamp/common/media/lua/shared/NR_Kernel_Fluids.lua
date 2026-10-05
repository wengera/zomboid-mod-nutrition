-- NR_Kernel_Fluids.lua -- the fast pools (Plan 4): body water and the sodium and potassium balances, the
-- per-minute loss terms that charge them, the surplus clearance, the derived scalars (dehydration per cent
-- of body mass, the plasma-sodium index) and the THIRST view the fast clock writes (rulings 7, 8, T1-1).
-- The model (formulas briefing B1-B6): water is a gram balance against euhydration (< 0 a deficit, > 0 a
-- surplus); na and k are mmol balances against baseline; total body water is TBW_PER_LM x lean mass; the
-- plasma-sodium index follows the Edelman form, plasma Na proportional to (exchangeable Na + K) over total
-- body water (open row S1092), with 1.0 = OSM_REF mmol/L. Metabolic water is omitted (stated). Caffeine
-- diuresis is 0 for a habitual drinker (S0528/S0529) and respiratory loss is 0 beyond basal (open S1052);
-- neither has code. The sweat EMAs take each step's per-minute sample, so a step of dtM minutes moves them
-- as one sample with alpha = dtM/360 (capped at 1); dtM is always > 0. Sex is indexed 1 male, 2 female
-- (Plan 3's K.body convention). Ruling T1-1: vanilla's autoDrink and ISTakeWaterAction size every sip from
-- THIRST, so the thirst VIEW reads the pool plus the stomach's still-unabsorbed water (dehydPct's extraG,
-- which the adapter passes) and THIRST falls at the drink; the performance scalar f.dehydPct is the
-- pool-only call (extraG 0). thirstTarget is a pure function of the dehydPct it is given.
-- Pure: numbers and Lua tables in, numbers and Lua tables out, no Java. Slow-clock code with no fast
-- region. This file sorts after NR_Kernel.lua, and every K.clamp / K.min / K.max reference is at call time.
local K = NutritionRevamp.kernel
K.fluids = {}

-- The record.fluids schema version.
K.fluids.FV = 1 -- schema version, no row needed

-- Total body water per kg of lean mass, litres.
K.fluids.TBW_PER_LM = 0.73 -- design-phase-v1 game choice (open row S1091: total body water as a fraction of lean mass)

-- The osmotic reference, mmol/L: the plasma-sodium index 1.0.
K.fluids.OSM_REF = 140 -- midpoint of S1045's 135-145 normal range

-- The basal water turnover (urine plus insensible loss at rest), g/day, indexed by sex.
K.fluids.AI = {
    3700, -- male: the total-water AI, S0088; as turnover a design-phase-v1 game choice (open row S1093)
    2700, -- female: the total-water AI, S0088; as turnover a design-phase-v1 game choice (open row S1093)
}

-- Sweat: SWEAT_LH L/h at SWEAT_MET_HI, from zero at SWEAT_MET_LO, capped at SWEAT_CAP x the scale.
K.fluids.SWEAT_LH = 1.0 -- S0090 (1.28-1.51 L/h hard work), S0091 modulators; design-phase-v1 (open row S1094)
K.fluids.SWEAT_MET_LO = 3 -- design-phase-v1 game choice (open row S1094: sweat rate as a function of MET)
K.fluids.SWEAT_MET_HI = 8 -- design-phase-v1 game choice (open row S1094: sweat rate as a function of MET)
K.fluids.SWEAT_CAP = 1.5 -- design-phase-v1 game choice (open row S1094: sweat rate as a function of MET)

-- The per-character sweat multiplier's draw range (the adapter draws it once).
K.fluids.SWEATK_RANGE = {
    0.5, -- S0090 SD about half the mean; design-phase-v1 game choice (open row S1094: the between-person spread)
    1.5, -- S0090 SD about half the mean; design-phase-v1 game choice (open row S1094: the between-person spread)
}

-- Sweat sodium, mmol/L: the mean and the per-character draw range.
K.fluids.NA_SWEAT_MEAN = 37 -- 55.9 mmol/h / 1.51 L/h, S0394 / S0090
K.fluids.NA_SWEAT_RANGE = {
    10, -- S0518
    90, -- S0518
}

-- Sweat potassium, mmol/L.
K.fluids.K_SWEAT = 5 -- S0518 (2-8 mmol/L)

-- Cold diuresis at full cold strain, L/h.
K.fluids.COLD_DIURESIS_LH = 0.1 -- design-phase-v1 game choice (open row S1053: cold-induced diuresis)

-- Alcohol diuresis: g urine per g ethanol absorbed, blunted by ALC_HYPO_K at ALC_KNEE_PCT per cent deficit.
K.fluids.ALC_DIURESIS_G_PER_G = 4 -- S0521 (1279 - 1121 = 158 mL per ~40 g)
K.fluids.ALC_HYPO_K = 0.45 -- S0522/S0523 (87 vs 158 mL: x0.55)
K.fluids.ALC_KNEE_PCT = 2 -- design-phase-v1 game choice (open row S1095: the deficit at which alcohol diuresis is blunted)

-- Surplus water clearance, zero-order, g/h.
K.fluids.CLEAR_GH = 320 -- S0521 (1279 mL in 4 h after 1 L, about 0.32 L/h)

-- The renal time constants of a sodium and a potassium surplus, hours; a deficit is conserved.
K.fluids.NA_TAU_H = 24 -- design-phase-v1 game choice (open row S1096: the renal tau of a sodium surplus)
K.fluids.K_TAU_H = 24 -- design-phase-v1 game choice (open row S1097: the renal tau of a potassium surplus)

-- mg per mmol.
K.fluids.NA_MG_PER_MMOL = 23 -- molar mass, no row needed
K.fluids.K_MG_PER_MMOL = 39.1 -- molar mass, no row needed

-- The thirst knots {dehydPct, THIRST}: the vanilla moodle levels #0509 at 1/2/4/6 per cent deficit.
K.fluids.THIRST_KNOTS = {
    { 0, 0 }, -- euhydrated: no thirst
    { 1, 0.12 }, -- moodle level 1 (#0509) at 1 %: design-phase-v1 game choice (open row S1098)
    { 2, 0.25 }, -- moodle level 2 (#0509) on the 2 % threshold, S0092
    { 4, 0.70 }, -- moodle level 3 (#0509) on the 4 % strain point, S0709
    { 6, 0.84 }, -- moodle level 4 (#0509) at 6 %: design-phase-v1 game choice (open row S1098)
    { 8, 1.0 }, -- full thirst at 8 %: design-phase-v1 game choice (open row S1098)
}

-- Osmotic thirst: OSM_GAIN per OSM_SLOPE of index rise, the clamp's top OSM_MAX steps.
K.fluids.OSM_SLOPE = 0.03 -- design-phase-v1 game choice (open row S1099: the osmotic thirst slope)
K.fluids.OSM_GAIN = 0.25 -- design-phase-v1 game choice (open row S1099: the osmotic thirst slope)
K.fluids.OSM_MAX = 4 -- design-phase-v1 game choice (open row S1099: the osmotic thirst slope)

-- Hypotonic suppression: below HYPO_NA mmol/L thirst stays under HYPO_CAP (drink to thirst protects).
K.fluids.HYPO_NA = 135 -- S0102
K.fluids.HYPO_CAP = 0.11 -- S0102 direction; design-phase-v1 game choice (open row S1099: the suppression below normal Na)

-- The view's cap while NR.DeficienciesCanKill is off: under vanilla's level-4 drain (#0518/#0519).
K.fluids.KILL_CAP = 0.83 -- game choice, ruling 8

-- The hyponatraemia ladder, mmol/L: grade 1 below [1], 2 below [2], 3 below [3].
K.fluids.HYPONAT = {
    135, -- S0102 / S1047
    120, -- S1047
    112, -- the midpoint of S1047's 110-115 band
}

-- sweatActive: the sweat share of the last 6 h's water loss above which a deficit counts as sweat-caused.
K.fluids.SWEAT_ACTIVE_SHARE = 0.5 -- design-phase-v1 game choice (open row S1100)

-- The sweat EMAs' window, minutes.
K.fluids.EMA_MIN = 360 -- game choice: the 6 h window

-- The deficit (per cent of body mass) Plan 5's severe-dehydration drain starts at.
K.fluids.SEVERE_DEHYD_PCT = 10 -- design-phase-v1 game choice (open row S1101; S0103 open)

-- A fresh record.fluids: euhydrated, at baseline sodium and potassium. lm is the caller's lean mass,
-- accepted for the call shape and not stored (tbw0 is recomputed from body.lm); a nil draw takes the
-- multiplier 1 and the mean sweat sodium.
function K.fluids.new(lm, sweatK, naSweat)
    return {
        fv = K.fluids.FV,
        water = 0,
        na = 0,
        k = 0,
        sweatK = sweatK or 1,
        naSweat = naSweat or K.fluids.NA_SWEAT_MEAN,
        sweat6h = 0,
        loss6h = 0,
        dehydPct = 0,
        c = 1,
        naPlasma = K.fluids.OSM_REF,
        thirstTarget = 0,
        autoDrop = 0,
        sweatLmin = 0,
    }
end

-- Total body water at euhydration, litres.
function K.fluids.tbw0(lm)
    return K.fluids.TBW_PER_LM * lm
end

-- The osmotic pool at euhydration, mmol (the Edelman form's numerator, open row S1092).
function K.fluids.osmPool0(lm)
    return K.fluids.OSM_REF * K.fluids.tbw0(lm)
end

-- Land this minute's absorbed vector: water g, sodium and potassium mg to mmol (absorption 1.0).
function K.fluids.intake(f, absorbed)
    f.water = f.water + (absorbed.water or 0)
    f.na = f.na + (absorbed.sodium or 0) / K.fluids.NA_MG_PER_MMOL
    f.k = f.k + (absorbed.potassium or 0) / K.fluids.K_MG_PER_MMOL
end

-- The sweat rate, L/h.
function K.fluids.sweatLh(met, thermoFluids, sweatK)
    local F = K.fluids
    local x = K.clamp((met - F.SWEAT_MET_LO) / (F.SWEAT_MET_HI - F.SWEAT_MET_LO), 0, F.SWEAT_CAP)
    return F.SWEAT_LH * x * thermoFluids * sweatK
end

-- The step's losses: basal, sweat (with its sodium and potassium), cold and alcohol diuresis; caffeine
-- diuresis 0 (S0528/S0529: habitual intake loses no fluid beyond the volume drunk); respiratory 0 beyond
-- basal (open row S1052). ctx = { sex, met, thermoFluids, coldMult, ethanolAbsG (this step's absorbed
-- ethanol g), dehydPct (the pool-only deficit) }. Updates the 6 h sweat and loss EMAs and returns the
-- step's sweat litres (also stored as f.sweatLmin).
function K.fluids.losses(f, ctx, dtM)
    local F = K.fluids
    local basalG = F.AI[ctx.sex] / 1440 * dtM
    local sweatL = F.sweatLh(ctx.met, ctx.thermoFluids, f.sweatK) * dtM / 60
    local sweatG = sweatL * 1000
    local coldG = F.COLD_DIURESIS_LH * K.clamp(ctx.coldMult - 1, 0, 1) * 1000 / 60 * dtM
    local blunt = 1 - F.ALC_HYPO_K * K.clamp(ctx.dehydPct / F.ALC_KNEE_PCT, 0, 1)
    local alcG = F.ALC_DIURESIS_G_PER_G * ctx.ethanolAbsG * blunt
    local lossG = basalG + sweatG + coldG + alcG
    f.water = f.water - lossG
    f.na = f.na - sweatL * f.naSweat
    f.k = f.k - sweatL * F.K_SWEAT
    local a = K.min(dtM / F.EMA_MIN, 1)
    f.sweat6h = f.sweat6h + a * (sweatG / dtM - f.sweat6h)
    f.loss6h = f.loss6h + a * (lossG / dtM - f.loss6h)
    f.sweatLmin = sweatL
    return sweatL
end

-- The renal clearance of a surplus: water zero-order at CLEAR_GH, sodium and potassium first-order.
function K.fluids.clearance(f, dtM)
    local F = K.fluids
    f.water = f.water - K.min(K.max(f.water, 0), F.CLEAR_GH / 60 * dtM)
    f.na = f.na - K.max(f.na, 0) * (dtM / 60) / F.NA_TAU_H
    f.k = f.k - K.max(f.k, 0) * (dtM / 60) / F.K_TAU_H
end

-- The water deficit in per cent of body mass w kg; extraG (nil = 0) is water counted as if in the pool:
-- the thirst view passes the stomach's pending water grams (ruling T1-1), the performance scalar 0.
function K.fluids.dehydPct(f, w, extraG)
    return 100 * K.max(0, -(f.water + (extraG or 0)) / 1000) / w
end

-- The plasma-sodium index (1.0 = OSM_REF): the osmotic pool over its baseline, diluted by total body water
-- (the Edelman form, open row S1092). The water term is floored at a tenth of tbw0.
function K.fluids.conc(f, lm)
    local F = K.fluids
    local t0 = F.tbw0(lm)
    local p0 = F.osmPool0(lm)
    local tbw = K.max(t0 + f.water / 1000, 0.1 * t0)
    return (p0 + f.na + f.k) / p0 * t0 / tbw
end

-- Plasma sodium, mmol/L, from the index.
function K.fluids.naPlasma(c)
    return K.fluids.OSM_REF * c
end

-- The volume thirst: piecewise-linear over THIRST_KNOTS, flat outside the first and last knot.
function K.fluids.tVol(dehydPct)
    local kn = K.fluids.THIRST_KNOTS
    local n = #kn -- THIRST_KNOTS is a Lua table this file built, so # is defined on it (as the vector kernel's KEYS)
    local d = K.clamp(dehydPct, kn[1][1], kn[n][1])
    local seg = n
    for i = n, 2, -1 do
        if d <= kn[i][1] then
            seg = i
        end
    end
    local x0 = kn[seg - 1][1]
    local y0 = kn[seg - 1][2]
    return y0 + (kn[seg][2] - y0) * (d - x0) / (kn[seg][1] - x0)
end

-- The THIRST target: the volume and osmotic drives combined, then the hypotonic and the kill caps.
function K.fluids.thirstTarget(dehydPct, c, naPlasma, canKill)
    local F = K.fluids
    local tVol = F.tVol(dehydPct)
    local tOsm = F.OSM_GAIN * K.clamp((c - 1) / F.OSM_SLOPE, 0, F.OSM_MAX)
    local t = 1 - (1 - tVol) * (1 - K.min(tOsm, 1))
    if naPlasma < F.HYPO_NA then
        t = K.min(t, F.HYPO_CAP)
    end
    if not canKill then
        t = K.min(t, F.KILL_CAP)
    end
    return t
end

-- The hyponatraemia grade, 0 (none) to 3 (the lethal band).
function K.fluids.hyponatGrade(naPlasma)
    local H = K.fluids.HYPONAT
    if naPlasma >= H[1] then
        return 0
    end
    if naPlasma >= H[2] then
        return 1
    end
    if naPlasma >= H[3] then
        return 2
    end
    return 3
end

-- Whether the last 6 h's water loss was mostly sweat.
function K.fluids.sweatActive(f)
    return f.loss6h > 0 and f.sweat6h / f.loss6h > K.fluids.SWEAT_ACTIVE_SHARE
end
