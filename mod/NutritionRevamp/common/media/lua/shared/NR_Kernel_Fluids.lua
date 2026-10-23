-- NR_Kernel_Fluids.lua: the fast pools (body water, the sodium and potassium balances), their loss terms and clearance,
-- the derived scalars (dehydration %, the plasma-sodium index, Edelman form, open S1092) and the THIRST view. Water is
-- read against weu, the water na + k carries isotonically. Metabolic water, caffeine diuresis (S0528) and respiratory
-- loss beyond basal are omitted. Vanilla sizes every sip from THIRST, so the thirst VIEW counts the stomach's pending
-- water (extraG) and THIRST falls at the drink; f.dehydPct and f.c are pool-only. No term reads the sex.
-- Pure, no Java; slow-clock code. Sorts after NR_Kernel.lua; K.clamp, K.min and K.max resolve at call time.
local K = NutritionRevamp.kernel
K.fluids = {}

K.fluids.TBW_PER_LM = K.dials.get("fluids.TBW_PER_LM")

K.fluids.OSM_REF = K.dials.get("fluids.OSM_REF")

-- Net of the metabolic water the model omits; BASAL_G at the reference lean K.strength.averageLean()
-- (52.02 kg, the no-trait body). Sex-neutral: S2218's fat-free-mass form has no sex term.
K.fluids.BASAL_G = K.dials.get("fluids.BASAL_G")
K.fluids.BASAL_G_PER_LM = K.dials.get("fluids.BASAL_G_PER_LM")

-- On the basal loss alone, never on sweat (#0486).
K.fluids.HIGH_THIRST = K.dials.get("fluids.HIGH_THIRST")
K.fluids.LOW_THIRST = K.dials.get("fluids.LOW_THIRST")

K.fluids.SWEAT_LH = K.dials.get("fluids.SWEAT_LH")
K.fluids.SWEAT_MET_LO = K.dials.get("fluids.SWEAT_MET_LO")
K.fluids.SWEAT_MET_HI = K.dials.get("fluids.SWEAT_MET_HI")
K.fluids.SWEAT_CAP = K.dials.get("fluids.SWEAT_CAP")

-- The adapter draws the multiplier once.
K.fluids.SWEATK_RANGE = {
    K.dials.get("fluids.SWEATK_RANGE.1"),
    K.dials.get("fluids.SWEATK_RANGE.2"),
}

-- naSweatEff adapts the drawn baseline to a deficit.
K.fluids.NA_SWEAT_MEAN = K.dials.get("fluids.NA_SWEAT_MEAN")
K.fluids.NA_SWEAT_RANGE = {
    K.dials.get("fluids.NA_SWEAT_RANGE.1"),
    K.dials.get("fluids.NA_SWEAT_RANGE.2"),
}

K.fluids.K_SWEAT = K.dials.get("fluids.K_SWEAT")

K.fluids.COLD_DIURESIS_LH = K.dials.get("fluids.COLD_DIURESIS_LH")

K.fluids.ALC_DIURESIS_G_PER_G = K.dials.get("fluids.ALC_DIURESIS_G_PER_G")
K.fluids.ALC_HYPO_K = K.dials.get("fluids.ALC_HYPO_K")
K.fluids.ALC_KNEE_PCT = K.dials.get("fluids.ALC_KNEE_PCT")

K.fluids.CLEAR_GH = K.dials.get("fluids.CLEAR_GH")

-- A deficit is conserved.
K.fluids.NA_TAU_H = K.dials.get("fluids.NA_TAU_H")
K.fluids.K_TAU_H = K.dials.get("fluids.K_TAU_H")

K.fluids.NA_MG_PER_MMOL = 23 -- molar mass, no row needed
K.fluids.K_MG_PER_MMOL = 39.1 -- molar mass, no row needed

-- One knot per vanilla moodle level (#0509); vanilla's thresholds are strict (#0507), so a level shows just past it.
-- Parched sits on the 4 % onset (K.drain.DEHYD_ONSET): about 32 h without water at rest. The 3 % knot is set so the
-- combined thirst crosses level 3's 0.70 at 3 % at rest: about 24 h without water.
K.fluids.THIRST_KNOTS = {
    { 0, 0 }, -- euhydrated: no thirst
    { K.dials.get("fluids.THIRST_KNOTS.2.1"), K.dials.get("fluids.THIRST_KNOTS.2.2") },
    { K.dials.get("fluids.THIRST_KNOTS.3.1"), K.dials.get("fluids.THIRST_KNOTS.3.2") },
    { K.dials.get("fluids.THIRST_KNOTS.4.1"), K.dials.get("fluids.THIRST_KNOTS.4.2") },
    { K.dials.get("fluids.THIRST_KNOTS.5.1"), K.dials.get("fluids.THIRST_KNOTS.5.2") },
    { K.dials.get("fluids.THIRST_KNOTS.6.1"), 1.0 }, -- full thirst, the THIRST top: no row needed
}

-- OSM_GAIN per OSM_SLOPE of index rise, clamped at OSM_MAX steps.
K.fluids.OSM_SLOPE = K.dials.get("fluids.OSM_SLOPE")
K.fluids.OSM_GAIN = K.dials.get("fluids.OSM_GAIN")
K.fluids.OSM_MAX = K.dials.get("fluids.OSM_MAX")

-- Below HYPO_NA thirst stays under HYPO_CAP (#2770), relaxed past the defence onset.
K.fluids.HYPO_NA = K.dials.get("fluids.HYPO_NA")
K.fluids.HYPO_CAP = K.dials.get("fluids.HYPO_CAP")

-- Grade 1 below [1], 2 below [2], 3 below [3].
K.fluids.HYPONAT = {
    K.dials.get("fluids.HYPONAT.1"),
    K.dials.get("fluids.HYPONAT.2"),
    K.dials.get("fluids.HYPONAT.3"),
}

-- The sweat share of the 6 h water loss above which a deficit counts as sweat-caused.
K.fluids.SWEAT_ACTIVE_SHARE = K.dials.get("fluids.SWEAT_ACTIVE_SHARE")

-- Urine, skin and faeces, whatever the intake.
K.fluids.BASAL_NA = K.dials.get("fluids.BASAL_NA")

-- lo + (hi - lo) r^2, a mean of 36.7 at the shipped range (S0518).
function K.fluids.naSweatOf(r)
    local nr = K.fluids.NA_SWEAT_RANGE
    return nr[1] + (nr[2] - nr[1]) * r * r
end

K.fluids.EMA_MIN = K.dials.get("fluids.EMA_MIN")

-- lm is accepted for the call shape and not stored (tbw0 is recomputed from body.lm).
function K.fluids.new(lm, sweatK, naSweat)
    return {
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

function K.fluids.tbw0(lm)
    return K.fluids.TBW_PER_LM * lm
end

function K.fluids.osmPool0(lm)
    return K.fluids.OSM_REF * K.fluids.tbw0(lm)
end

-- Absorption 1.0.
function K.fluids.intake(f, absorbed)
    f.water = f.water + (absorbed.water or 0)
    f.na = f.na + (absorbed.sodium or 0) / K.fluids.NA_MG_PER_MMOL
    f.k = f.k + (absorbed.potassium or 0) / K.fluids.K_MG_PER_MMOL
end

function K.fluids.sweatLh(met, thermoFluids, sweatK)
    local F = K.fluids
    local x = K.clamp((met - F.SWEAT_MET_LO) / (F.SWEAT_MET_HI - F.SWEAT_MET_LO), 0, F.SWEAT_CAP)
    return F.SWEAT_LH * x * thermoFluids * sweatK
end

-- traitScale includes the sandbox multiplier; floored at 0, so no lean mass or scale makes it a gain.
function K.fluids.basalG(lm, traitScale)
    local F = K.fluids
    local g = F.BASAL_G + F.BASAL_G_PER_LM * (lm - K.strength.averageLean())
    return K.max(g * traitScale, 0)
end

-- High Thirst wins (a game choice: vanilla's two tests give 1.0 with both, #2767; creation never grants both).
function K.fluids.thirstTrait(high, low)
    if high then
        return K.fluids.HIGH_THIRST
    end
    if low then
        return K.fluids.LOW_THIRST
    end
    return 1
end

-- ctx = { lm, basalScale (nil reads 1), met, thermoFluids, coldMult, ethanolAbsG, dehydPct (pool-only) }.
function K.fluids.losses(f, ctx, dtM)
    local F = K.fluids
    local basalG = F.basalG(ctx.lm, ctx.basalScale or 1) / 1440 * dtM
    local sweatL = F.sweatLh(ctx.met, ctx.thermoFluids, f.sweatK) * dtM / 60
    local sweatG = sweatL * 1000
    local coldG = F.COLD_DIURESIS_LH * K.clamp(ctx.coldMult - 1, 0, 1) * 1000 / 60 * dtM
    local blunt = 1 - F.ALC_HYPO_K * K.clamp(ctx.dehydPct / F.ALC_KNEE_PCT, 0, 1)
    local alcG = F.ALC_DIURESIS_G_PER_G * ctx.ethanolAbsG * blunt
    local lossG = basalG + sweatG + coldG + alcG
    f.water = f.water - lossG
    f.na = f.na - F.BASAL_NA / 1440 * dtM
    f.na = f.na - sweatL * F.naSweatEff(f)
    f.k = f.k - sweatL * F.K_SWEAT
    local a = K.min(dtM / F.EMA_MIN, 1)
    f.sweat6h = f.sweat6h + a * (sweatG / dtM - f.sweat6h)
    f.loss6h = f.loss6h + a * (lossG / dtM - f.loss6h)
    f.sweatLmin = sweatL
    return sweatL
end

-- Surpluses first-order, then the water above weu zero-order.
function K.fluids.clearance(f, dtM, w)
    local F = K.fluids
    f.na = f.na - K.max(f.na, 0) * (dtM / 60) / F.NA_TAU_H
    f.k = f.k - K.max(f.k, 0) * (dtM / 60) / F.K_TAU_H
    f.water = f.water - K.min(K.max(f.water - F.weu(f, w), 0), F.CLEAR_GH / 60 * dtM)
end

-- extraG (nil reads 0) counts as if in the pool: the view's pending stomach water.
function K.fluids.dehydPct(f, w, extraG)
    return 100 * K.max(0, (K.fluids.weu(f, w) - f.water - (extraG or 0)) / 1000) / w
end

-- extraG as in dehydPct; the water term is floored at 0.1 tbw0.
function K.fluids.conc(f, lm, extraG)
    local F = K.fluids
    local t0 = F.tbw0(lm)
    local p0 = F.osmPool0(lm)
    local tbw = K.max(t0 + (f.water + (extraG or 0)) / 1000, 0.1 * t0)
    return (p0 + f.na + f.k) / p0 * t0 / tbw
end

function K.fluids.naPlasma(c)
    return K.fluids.OSM_REF * c
end

function K.fluids.tVol(dehydPct)
    return K.interp(K.fluids.THIRST_KNOTS, dehydPct)
end

-- defence (nil reads 0) relaxes the hypotonic cap toward the uncapped thirst, so a salt-depleted body keeps replacing
-- volume while its plasma falls (S1729). Riding the set point's ramp is a game choice.
function K.fluids.thirstTarget(dehydPct, c, naPlasma, defence)
    local F = K.fluids
    local tVol = F.tVol(dehydPct)
    local tOsm = F.OSM_GAIN * K.clamp((c - 1) / F.OSM_SLOPE, 0, F.OSM_MAX)
    local t = 1 - (1 - tVol) * (1 - K.min(tOsm, 1))
    if naPlasma < F.HYPO_NA then
        local capped = K.min(t, F.HYPO_CAP)
        t = capped + (defence or 0) * (t - capped)
    end
    return t
end

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

function K.fluids.sweatActive(f)
    return f.loss6h > 0 and f.sweat6h / f.loss6h > K.fluids.SWEAT_ACTIVE_SHARE
end

-- Water follows sodium. LIMITATION: isotonic retention holds to about 200 mmol/d (S1678); above it sodium is also stored
-- without water (S1677), not modelled, so the set point overstates the water retained.
K.fluids.WATER_PER_MMOL = 1000 / K.fluids.OSM_REF -- derived: 1000 g a litre over the plasma's OSM_REF mmol/L (S1683)

-- The volume defence: a sodium deficit contracts the set point isotonically only so far.
K.fluids.ECF_PER_KG = K.dials.get("fluids.ECF_PER_KG")
K.fluids.DEFEND_ONSET = K.dials.get("fluids.DEFEND_ONSET")
K.fluids.DEFEND_FULL = K.dials.get("fluids.DEFEND_FULL")

-- Potassium's share is a game choice: conc counts na + k, so water at weu reads c = 1 exactly. Past DEFEND_ONSET of ECF
-- the contraction is bounded, so a further sodium loss leaves the water in place; the same ramp relaxes the thirst
-- cap, so water lost with it is drunk back and dilutes the pool (S1729). A surplus is never bounded.
function K.fluids.weu(f, w)
    local F = K.fluids
    local iso = F.WATER_PER_MMOL * (f.na + f.k)
    local ecf = F.ECF_PER_KG * w * 1000
    local a = F.DEFEND_ONSET * ecf
    if iso >= -a then
        return iso
    end
    local b = F.DEFEND_FULL * ecf
    return (b - a) * math.exp((iso + a) / (b - a)) - b
end

-- weu's ramp, 0 up to DEFEND_ONSET of ECF and toward 1 at DEFEND_FULL.
function K.fluids.defence(f, w)
    local F = K.fluids
    local ecf = F.ECF_PER_KG * w * 1000
    local a = F.DEFEND_ONSET * ecf
    local b = F.DEFEND_FULL * ecf
    return K.clamp((-F.weu(f, w) - a) / (b - a), 0, 1)
end

-- Sweat sodium adapts to a sodium deficit (C-14; docs/superpowers/research/2026-10-10-live-study-replays/
-- 08-sweat-sodium.md@program-record-v19 section 7): "the presence of a salt deficit is required" (S1747). The deficit's
-- own build-up is the gland lag. A replete, acclimatising worker under-adapts here (S1755).
K.fluids.NA_SWEAT_MIN_FRAC = K.dials.get("fluids.NA_SWEAT_MIN_FRAC")
-- The deficit at the floor ratio; the zero anchor and the straight line are game choices (open S1770).
K.fluids.NA_SWEAT_DEF_FULL = K.dials.get("fluids.NA_SWEAT_DEF_FULL")
-- A game choice (S1758): keeps a low draw from falling to 3.
K.fluids.NA_SWEAT_ABS_MIN = K.dials.get("fluids.NA_SWEAT_ABS_MIN")

-- f.naSweat is never rewritten; a surplus reads the baseline, and recovery follows the same line (open S1771).
function K.fluids.naSweatEff(f)
    local F = K.fluids
    local deficit = K.max(-f.na, 0)
    local r = K.clamp(deficit / F.NA_SWEAT_DEF_FULL, 0, 1)
    local eff = f.naSweat * (1 - (1 - F.NA_SWEAT_MIN_FRAC) * r)
    return K.max(eff, F.NA_SWEAT_ABS_MIN)
end
