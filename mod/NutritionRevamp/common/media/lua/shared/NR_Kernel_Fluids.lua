-- NR_Kernel_Fluids.lua -- the fast pools: body water and the sodium and potassium balances, the
-- per-minute loss terms that charge them, the surplus clearance, the derived scalars (dehydration per cent
-- of body mass, the plasma-sodium index) and the THIRST view the writer writes.
-- The model (formulas briefing B1-B6): water, na and k are gram and mmol balances against baseline, and the
-- water is read against weu, the water na + k carries isotonically; TBW is TBW_PER_LM x lm; the
-- plasma-sodium index follows the Edelman form, plasma Na proportional to (exchangeable Na + K) over total
-- body water (open row S1092), with 1.0 = OSM_REF mmol/L. Metabolic water is omitted (stated). Caffeine
-- diuresis is 0 for a habitual drinker (S0528/S0529) and respiratory loss is 0 beyond basal (open S1052);
-- neither has code. The sweat EMAs take each step's per-minute sample, so a step of dtM minutes moves them
-- as one sample with alpha = dtM/360 (capped at 1); dtM is always > 0. No term reads the sex (Plan 15 Task 3:
-- the basal loss scales by lean mass). Vanilla's autoDrink and ISTakeWaterAction size every sip from
-- THIRST, so the thirst VIEW reads the pool plus the stomach's still-unabsorbed water (the extraG of dehydPct
-- and, of conc, which the adapter passes) and THIRST falls at the drink; f.dehydPct and
-- f.c are the pool-only calls (extraG 0). thirstTarget is a pure function of the scalars it is given.
-- Pure: numbers and Lua tables in, numbers and Lua tables out, no Java. Slow-clock code with no fast
-- region. This file sorts after NR_Kernel.lua, and every K.clamp / K.min / K.max reference is at call time.
local K = NutritionRevamp.kernel
K.fluids = {}

-- Total body water per kg of lean mass, litres.
K.fluids.TBW_PER_LM = K.dials.get("fluids.TBW_PER_LM")

-- The osmotic reference, mmol/L: the plasma-sodium index 1.0.
K.fluids.OSM_REF = K.dials.get("fluids.OSM_REF")

-- The basal net water loss (urine, skin, breath and faeces, net of the metabolic water the model omits), g/day:
-- BASAL_G at the reference lean mass K.strength.averageLean() (52.02 kg, the no-trait body), BASAL_G_PER_LM a kg
-- of lean mass either side. Sex-neutral: S2218's fat-free-mass form has no sex term (Plan 15 Task 3).
K.fluids.BASAL_G = K.dials.get("fluids.BASAL_G")
K.fluids.BASAL_G_PER_LM = K.dials.get("fluids.BASAL_G_PER_LM")

-- The thirst traits' scale on the basal loss alone, never on sweat (spec section 3.4: vanilla's thirst rate x2 and x0.5, #0486).
K.fluids.HIGH_THIRST = K.dials.get("fluids.HIGH_THIRST")
K.fluids.LOW_THIRST = K.dials.get("fluids.LOW_THIRST")

-- Sweat: SWEAT_LH L/h at SWEAT_MET_HI, from zero at SWEAT_MET_LO, capped at SWEAT_CAP x the scale.
K.fluids.SWEAT_LH = K.dials.get("fluids.SWEAT_LH")
K.fluids.SWEAT_MET_LO = K.dials.get("fluids.SWEAT_MET_LO")
K.fluids.SWEAT_MET_HI = K.dials.get("fluids.SWEAT_MET_HI")
K.fluids.SWEAT_CAP = K.dials.get("fluids.SWEAT_CAP")

-- The per-character sweat multiplier's draw range (the adapter draws it once).
K.fluids.SWEATK_RANGE = {
    K.dials.get("fluids.SWEATK_RANGE.1"),
    K.dials.get("fluids.SWEATK_RANGE.2"),
}

-- Sweat sodium, mmol/L: the mean and the per-character draw range (the baseline naSweatEff adapts to a deficit).
K.fluids.NA_SWEAT_MEAN = K.dials.get("fluids.NA_SWEAT_MEAN")
K.fluids.NA_SWEAT_RANGE = {
    K.dials.get("fluids.NA_SWEAT_RANGE.1"),
    K.dials.get("fluids.NA_SWEAT_RANGE.2"),
}

-- Sweat potassium, mmol/L.
K.fluids.K_SWEAT = K.dials.get("fluids.K_SWEAT")

-- Cold diuresis at full cold strain, L/h.
K.fluids.COLD_DIURESIS_LH = K.dials.get("fluids.COLD_DIURESIS_LH")

-- Alcohol diuresis: g urine per g ethanol absorbed, blunted by ALC_HYPO_K at ALC_KNEE_PCT per cent deficit.
K.fluids.ALC_DIURESIS_G_PER_G = K.dials.get("fluids.ALC_DIURESIS_G_PER_G")
K.fluids.ALC_HYPO_K = K.dials.get("fluids.ALC_HYPO_K")
K.fluids.ALC_KNEE_PCT = K.dials.get("fluids.ALC_KNEE_PCT")

-- The clearance of water above the set point weu, zero-order, g/h.
K.fluids.CLEAR_GH = K.dials.get("fluids.CLEAR_GH")

-- The renal time constants of a sodium and a potassium surplus, hours; a deficit is conserved.
K.fluids.NA_TAU_H = K.dials.get("fluids.NA_TAU_H")
K.fluids.K_TAU_H = K.dials.get("fluids.K_TAU_H")

-- mg per mmol.
K.fluids.NA_MG_PER_MMOL = 23 -- molar mass, no row needed
K.fluids.K_MG_PER_MMOL = 39.1 -- molar mass, no row needed

-- The volume-thirst knots {dehydPct, THIRST}, one per vanilla moodle level (#0509) at 1/2/3/4 per cent deficit. Vanilla
-- tests each threshold with a strict greater-than (#0507), so a level shows just past it. Plan 15 Task 5 (option B):
-- Parched (level 4, 0.84) sits on the 4 % dehydration onset (K.drain.DEHYD_ONSET), where the writer lifts its thirst
-- cap (K.hybrid.caps): about 32 h without water at rest, against vanilla's 29.17 h (#0495). The 3 % knot is set so the
-- combined thirst (thirstTarget: the volume and osmotic drives) crosses level 3's 0.70 at 3 % at rest, where the
-- osmotic drive reads about 0.45: about 24 h without water (vanilla's 0.70 at 24.3 h by #0495's rate); by volume alone
-- level 3 comes at about 3.6 %.
K.fluids.THIRST_KNOTS = {
    { 0, 0 }, -- euhydrated: no thirst
    { K.dials.get("fluids.THIRST_KNOTS.2.1"), K.dials.get("fluids.THIRST_KNOTS.2.2") },
    { K.dials.get("fluids.THIRST_KNOTS.3.1"), K.dials.get("fluids.THIRST_KNOTS.3.2") },
    { K.dials.get("fluids.THIRST_KNOTS.4.1"), K.dials.get("fluids.THIRST_KNOTS.4.2") },
    { K.dials.get("fluids.THIRST_KNOTS.5.1"), K.dials.get("fluids.THIRST_KNOTS.5.2") },
    { K.dials.get("fluids.THIRST_KNOTS.6.1"), 1.0 }, -- full thirst, the THIRST top: no row needed
}

-- Osmotic thirst: OSM_GAIN per OSM_SLOPE of index rise, the clamp's top OSM_MAX steps.
K.fluids.OSM_SLOPE = K.dials.get("fluids.OSM_SLOPE")
K.fluids.OSM_GAIN = K.dials.get("fluids.OSM_GAIN")
K.fluids.OSM_MAX = K.dials.get("fluids.OSM_MAX")

-- Hypotonic suppression: below HYPO_NA thirst stays under HYPO_CAP (#2770), relaxed past the defence onset (defence).
K.fluids.HYPO_NA = K.dials.get("fluids.HYPO_NA")
K.fluids.HYPO_CAP = K.dials.get("fluids.HYPO_CAP")

-- The hyponatraemia ladder, mmol/L: grade 1 below [1], 2 below [2], 3 below [3].
K.fluids.HYPONAT = {
    K.dials.get("fluids.HYPONAT.1"),
    K.dials.get("fluids.HYPONAT.2"),
    K.dials.get("fluids.HYPONAT.3"),
}

-- sweatActive: the sweat share of the last 6 h's water loss above which a deficit counts as sweat-caused.
K.fluids.SWEAT_ACTIVE_SHARE = K.dials.get("fluids.SWEAT_ACTIVE_SHARE")

-- The obligatory sodium loss without sweating (urine, skin and faeces), mmol/day, whatever the intake.
K.fluids.BASAL_NA = K.dials.get("fluids.BASAL_NA")

-- The sweat sodium draw from a uniform roll r: lo + (hi - lo) r^2 over NA_SWEAT_RANGE, at the shipped 10-90 a mean of 36.7 (S0518).
function K.fluids.naSweatOf(r)
    local nr = K.fluids.NA_SWEAT_RANGE
    return nr[1] + (nr[2] - nr[1]) * r * r
end

-- The sweat EMAs' window, minutes.
K.fluids.EMA_MIN = K.dials.get("fluids.EMA_MIN")

-- A fresh record.fluids: euhydrated, at baseline sodium and potassium. lm is the caller's lean mass,
-- accepted for the call shape and not stored (tbw0 is recomputed from body.lm); a nil draw takes the
-- multiplier 1 and the mean sweat sodium.
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

-- The basal net water loss, g/day, at lean mass lm kg, times traitScale (K.fluids.thirstTrait times the sandbox's
-- StatsDecrease multiplier: the caller's), floored at 0, so no lean mass or scale makes it a gain. The anchor reads
-- K.strength.averageLean at call time (game choice, spec section 3.4: the default body loses exactly BASAL_G).
function K.fluids.basalG(lm, traitScale)
    local F = K.fluids
    local g = F.BASAL_G + F.BASAL_G_PER_LM * (lm - K.strength.averageLean())
    return K.max(g * traitScale, 0)
end

-- The thirst traits' scale: High Thirst wins over Low Thirst, 1 with neither (game choice, spec section 3.4: vanilla's two independent tests give 1.0 when both are held, #2767; creation never grants both).
function K.fluids.thirstTrait(high, low)
    if high then
        return K.fluids.HIGH_THIRST
    end
    if low then
        return K.fluids.LOW_THIRST
    end
    return 1
end

-- The step's losses: basal, sweat (with its sodium and potassium), cold and alcohol diuresis; caffeine
-- diuresis 0 (S0528/S0529: habitual intake loses no fluid beyond the volume drunk); respiratory 0 beyond
-- basal (open row S1052). ctx = { lm (lean kg), basalScale (K.fluids.basalG's traitScale; nil reads 1), met,
-- thermoFluids, coldMult, ethanolAbsG (this step's absorbed ethanol g), dehydPct (the pool-only deficit) }. Updates the 6 h sweat and loss EMAs and returns the
-- step's sweat litres (also stored as f.sweatLmin).
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

-- The renal clearance: a sodium and a potassium surplus first-order, then the water above weu (at body mass w) zero-order.
function K.fluids.clearance(f, dtM, w)
    local F = K.fluids
    f.na = f.na - K.max(f.na, 0) * (dtM / 60) / F.NA_TAU_H
    f.k = f.k - K.max(f.k, 0) * (dtM / 60) / F.K_TAU_H
    f.water = f.water - K.min(K.max(f.water - F.weu(f, w), 0), F.CLEAR_GH / 60 * dtM)
end

-- The water deficit against weu in per cent of body mass w kg; extraG (nil = 0) is water counted as if in the
-- pool: the thirst view passes the stomach's pending water grams, the performance scalar 0.
function K.fluids.dehydPct(f, w, extraG)
    return 100 * K.max(0, (K.fluids.weu(f, w) - f.water - (extraG or 0)) / 1000) / w
end

-- The plasma-sodium index (1.0 = OSM_REF): the osmotic pool over its baseline, diluted by total body water plus extraG
-- (nil = 0: the view's swallowed water; the Edelman form, open row S1092). The water term is floored at 0.1 tbw0.
function K.fluids.conc(f, lm, extraG)
    local F = K.fluids
    local t0 = F.tbw0(lm)
    local p0 = F.osmPool0(lm)
    local tbw = K.max(t0 + (f.water + (extraG or 0)) / 1000, 0.1 * t0)
    return (p0 + f.na + f.k) / p0 * t0 / tbw
end

-- Plasma sodium, mmol/L, from the index.
function K.fluids.naPlasma(c)
    return K.fluids.OSM_REF * c
end

-- The volume thirst: piecewise-linear over THIRST_KNOTS, flat outside the first and last knot.
function K.fluids.tVol(dehydPct)
    return K.interp(K.fluids.THIRST_KNOTS, dehydPct)
end

-- The THIRST target: the volume and osmotic drives combined, then the hypotonic cap. defence (nil
-- reads 0) is the volume-defence weight K.fluids.defence: past the onset a volume-thirst term relaxes the hypotonic cap
-- toward the uncapped thirst by that weight, so a salt-depleted body keeps replacing its
-- volume and its plasma falls (S1729: volume held at the expense of the osmotic pressure; S1731: the subjects drank
-- freely; S1724: volume depletion raises thirst); the weight riding the set point's ramp is a game choice, and the
-- human cut-off of hypotonic thirst is open (S1695, S1736). Below the onset the weight is 0 and the cap holds.
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

-- Water follows sodium (option B): the grams of water one retained mmol carries, the plasma's
-- OSM_REF mmol/L. LIMITATION: isotonic retention holds in the low-to-normal band (S1673's low-to-normal step, S1678's
-- 50-200 mmol/d); at high sustained intakes sodium is also stored without water (S1673's normal-to-high step, S1677),
-- which is not modelled, so above about 200 mmol/d the set point overstates the water retained.
K.fluids.WATER_PER_MMOL = 1000 / K.fluids.OSM_REF -- derived: 1000 g a litre over the plasma's OSM_REF mmol/L (S1683: 140 mmol/L, so 7.14 g per mmol at the shipped dials)

-- The volume defence: a sodium deficit contracts the set point isotonically only so far.
-- The body's ECF at euhydration, L per kg of body mass.
K.fluids.ECF_PER_KG = K.dials.get("fluids.ECF_PER_KG")
-- The contraction, as a share of ECF, at which vasopressin starts to defend volume over osmolality.
K.fluids.DEFEND_ONSET = K.dials.get("fluids.DEFEND_ONSET")
-- The contraction, as a share of ECF, at which the volume is fully defended.
K.fluids.DEFEND_FULL = K.dials.get("fluids.DEFEND_FULL")

-- The euhydration set point weu, g against baseline, at body mass w kg: the water the sodium and potassium balances
-- carry isotonically. Potassium's share is a game choice (no row prices it): conc counts na + k, so weu counts both,
-- and water at weu reads c = 1 exactly. A deficit contracts it fully up to DEFEND_ONSET of ECF (a); past that the
-- weight with which water follows sodium falls linearly with the contraction to 0 at DEFEND_FULL (b), so a requested
-- contraction x gives b - (b - a) exp(-(x - a) / (b - a)), bounded by b: past the onset a further sodium loss leaves
-- the water in place. The same ramp relaxes the hypotonic thirst cap (K.fluids.defence), so
-- water lost with it is drunk back and dilutes the pool (S1729's second phase, S1730's falling serum sodium); only water
-- not yet replaced reads as dehydration (dehydPct). A surplus is never bounded.
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

-- The volume-defence weight at body mass w kg, 0 to 1: the set point's own ramp, (x - a) / (b - a) on the contraction
-- reached x = -weu, so 0 up to DEFEND_ONSET of ECF and toward 1 at DEFEND_FULL. thirstTarget
-- relaxes the hypotonic cap by it; riding the set point's ramp is a game choice resting on S1729, S1731 and S1724.
function K.fluids.defence(f, w)
    local F = K.fluids
    local ecf = F.ECF_PER_KG * w * 1000
    local a = F.DEFEND_ONSET * ecf
    local b = F.DEFEND_FULL * ecf
    return K.clamp((-F.weu(f, w) - a) / (b - a), 0, 1)
end

-- Sweat sodium adapts to a sodium deficit (candidate C-14; 08-sweat-sodium.md section 7). The
-- driver is the deficit max(-na, 0), not the diet or heat exposure: "the presence of a salt deficit is required"
-- (S1747); McCance 1938's deficiency arm fell 72 -> 33 mM Na while his generous arm rose 62 -> 70 (S1749); Armstrong
-- 1985's low-sodium arm fell 45 -> 26 while the high arm rose 41 -> 56 (S1750). Allsopp 1998 saw a fall without a
-- deficit (S1755), so a replete, acclimatising worker under-adapts here (an exposure field is a later candidate).
-- No gland lag is stored (S1748: 1-4 days; S1773: about 12 h): the deficit's own build-up is the delay.
-- The floor ratio: the median of the 5-13 day deficit arms, Weiner 13/40 = 0.325 (S1751), between Komives 15/50 = 0.30
-- (S1769) and McCance 1938's 33/72 = 0.46 (S1749) (derived); two of the three are chloride ratios read as sodium
-- (S0518: chloride tracks sodium), the arms are n = 1, 4 and 2, and none measured its deficit.
K.fluids.NA_SWEAT_MIN_FRAC = K.dials.get("fluids.NA_SWEAT_MIN_FRAC")
-- The deficit, mmol, at which the floor ratio is reached: a line from (0, 1) through the mean of Robinson 1956 (169 mmol
-- Cl depleted, 28 -> 17 mM Cl, S1752, a chloride proxy) and Armstrong 1985 (-230.4 mmol body sodium, 45 -> 26 mM Na,
-- S1750, S1753), that is (199.7, 0.5925), reaches 0.325 at 330.8 mmol (derived). The zero anchor and the straight line
-- are game choices, not a fitted dose-response (open S1770).
K.fluids.NA_SWEAT_DEF_FULL = K.dials.get("fluids.NA_SWEAT_DEF_FULL")
-- The absolute floor, mmol/L: a game choice resting on the low end of S0518's 10-90 and of Allan and Wilson's 10-58
-- (S1758); not a measured floor. It keeps a low draw from falling to 3.
K.fluids.NA_SWEAT_ABS_MIN = K.dials.get("fluids.NA_SWEAT_ABS_MIN")

-- The effective sweat sodium, mmol/L: the drawn baseline f.naSweat (never rewritten) less (1 - MIN_FRAC) of itself in
-- proportion to the deficit up to DEF_FULL, floored at ABS_MIN; a surplus reads the baseline. Recovery on repletion
-- follows the same line (open S1771).
function K.fluids.naSweatEff(f)
    local F = K.fluids
    local deficit = K.max(-f.na, 0)
    local r = K.clamp(deficit / F.NA_SWEAT_DEF_FULL, 0, 1)
    local eff = f.naSweat * (1 - (1 - F.NA_SWEAT_MIN_FRAC) * r)
    return K.max(eff, F.NA_SWEAT_ABS_MIN)
end
