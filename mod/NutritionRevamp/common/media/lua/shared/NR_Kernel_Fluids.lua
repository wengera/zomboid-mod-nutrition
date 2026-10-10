-- NR_Kernel_Fluids.lua -- the fast pools (Plan 4): body water and the sodium and potassium balances, the
-- per-minute loss terms that charge them, the surplus clearance, the derived scalars (dehydration per cent
-- of body mass, the plasma-sodium index) and the THIRST view the writer writes (rulings 7, 8, T1-1).
-- The model (formulas briefing B1-B6): water, na and k are gram and mmol balances against baseline, and the
-- water is read against weu, the water na + k carries isotonically (Plan 11f Task 5b); TBW is TBW_PER_LM x lm; the
-- plasma-sodium index follows the Edelman form, plasma Na proportional to (exchangeable Na + K) over total
-- body water (open row S1092), with 1.0 = OSM_REF mmol/L. Metabolic water is omitted (stated). Caffeine
-- diuresis is 0 for a habitual drinker (S0528/S0529) and respiratory loss is 0 beyond basal (open S1052);
-- neither has code. The sweat EMAs take each step's per-minute sample, so a step of dtM minutes moves them
-- as one sample with alpha = dtM/360 (capped at 1); dtM is always > 0. Sex is indexed 1 male, 2 female
-- (Plan 3's K.body convention). Ruling T1-1: vanilla's autoDrink and ISTakeWaterAction size every sip from
-- THIRST, so the thirst VIEW reads the pool plus the stomach's still-unabsorbed water (the extraG of dehydPct
-- and, Plan 11f Task 5b fix 1, of conc, which the adapter passes) and THIRST falls at the drink; f.dehydPct and
-- f.c are the pool-only calls (extraG 0). thirstTarget is a pure function of the scalars it is given.
-- Pure: numbers and Lua tables in, numbers and Lua tables out, no Java. Slow-clock code with no fast
-- region. This file sorts after NR_Kernel.lua, and every K.clamp / K.min / K.max reference is at call time.
local K = NutritionRevamp.kernel
K.fluids = {}

-- Total body water per kg of lean mass, litres.
K.fluids.TBW_PER_LM = 0.73 -- S1706: 72.7 +/- 3.2 % of lean body mass (Peronnet 2012), rounded to two places

-- The osmotic reference, mmol/L: the plasma-sodium index 1.0.
K.fluids.OSM_REF = 140 -- midpoint of S1045's 135-145 normal range

-- The basal water turnover (urine plus insensible loss at rest), g/day, indexed by sex.
K.fluids.AI = {
    3700, -- male: the total-water AI, S0088, as basal turnover: a game choice above S1688's minimum losses
    2700, -- female: the total-water AI, S0088, as basal turnover: a game choice above S1688's minimum losses
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

-- Sweat sodium, mmol/L: the mean and the per-character draw range (the baseline naSweatEff adapts to a deficit).
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

-- The clearance of water above the set point weu, zero-order, g/h.
K.fluids.CLEAR_GH = 672 -- S1685: the maximal free-water clearance, 11.2 mL/min x 60 (derived)

-- The renal time constants of a sodium and a potassium surplus, hours; a deficit is conserved.
K.fluids.NA_TAU_H = 33.8 -- S1670: the 30-59 y half-time 23.4 h / ln 2 (derived; the mod has no age); S1672 agrees
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

-- Hypotonic suppression: below HYPO_NA thirst stays under HYPO_CAP (#2770), relaxed past the defence onset (defence).
K.fluids.HYPO_NA = 135 -- S0102
K.fluids.HYPO_CAP = 0.09 -- game choice under #2770's 0.1 autoDrink trigger, so suppression stops drinking (open S1695)

-- The view's cap while NR.DeficienciesCanKill is off: under vanilla's level-4 drain (#0518/#0519).
K.fluids.KILL_CAP = 0.83 -- game choice, ruling 8

-- The hyponatraemia ladder, mmol/L: grade 1 below [1], 2 below [2], 3 below [3].
K.fluids.HYPONAT = {
    135, -- S0102 / S1047
    120, -- S1047
    112, -- inside S1047's 110-115 band (its midpoint 112.5, rounded down: game choice)
}

-- sweatActive: the sweat share of the last 6 h's water loss above which a deficit counts as sweat-caused.
K.fluids.SWEAT_ACTIVE_SHARE = 0.5 -- design-phase-v1 game choice (open row S1100)

-- The obligatory sodium loss without sweating (urine, skin and faeces), mmol/day, whatever the intake.
K.fluids.BASAL_NA = 8 -- S1665: the IOM's total obligatory loss, up to 8 mmol/d (Table 6-1, 1.7-8.0)

-- The sweat sodium draw from a uniform roll r: 10 + 80 r^2 has mean 36.7 and range 10-90 (S0518; ruling T11-4).
function K.fluids.naSweatOf(r)
    local nr = K.fluids.NA_SWEAT_RANGE
    return nr[1] + (nr[2] - nr[1]) * r * r
end

-- The sweat EMAs' window, minutes.
K.fluids.EMA_MIN = 360 -- game choice: the 6 h window

-- The deficit (per cent of body mass) Plan 5's severe-dehydration drain starts at.
K.fluids.SEVERE_DEHYD_PCT = 10 -- design-phase-v1 game choice (open row S1101; S0103 open)

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
-- pool: the thirst view passes the stomach's pending water grams (ruling T1-1), the performance scalar 0.
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

-- The THIRST target: the volume and osmotic drives combined, then the hypotonic and the kill caps. defence (nil
-- reads 0) is the volume-defence weight K.fluids.defence: past the onset a volume-thirst term relaxes the hypotonic cap
-- toward the uncapped thirst by that weight (Plan 11f Task 5b fix 2), so a salt-depleted body keeps replacing its
-- volume and its plasma falls (S1729: volume held at the expense of the osmotic pressure; S1731: the subjects drank
-- freely; S1724: volume depletion raises thirst); the weight riding the set point's ramp is a game choice, and the
-- human cut-off of hypotonic thirst is open (S1695, S1736). Below the onset the weight is 0 and the cap holds.
function K.fluids.thirstTarget(dehydPct, c, naPlasma, canKill, defence)
    local F = K.fluids
    local tVol = F.tVol(dehydPct)
    local tOsm = F.OSM_GAIN * K.clamp((c - 1) / F.OSM_SLOPE, 0, F.OSM_MAX)
    local t = 1 - (1 - tVol) * (1 - K.min(tOsm, 1))
    if naPlasma < F.HYPO_NA then
        local capped = K.min(t, F.HYPO_CAP)
        t = capped + (defence or 0) * (t - capped)
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

-- Water follows sodium (Plan 11f Task 5b, option B): the grams of water one retained mmol carries, the plasma's
-- 140 mmol/L. LIMITATION: isotonic retention holds in the low-to-normal band (S1673's low-to-normal step, S1678's
-- 50-200 mmol/d); at high sustained intakes sodium is also stored without water (S1673's normal-to-high step, S1677),
-- which is not modelled, so above about 200 mmol/d the set point overstates the water retained.
K.fluids.WATER_PER_MMOL = 1000 / 140 -- S1683: plasma sodium 140 mmol/L, so 7.14 g per mmol (derived)

-- The volume defence (Plan 11f Task 5b fix 1): a sodium deficit contracts the set point isotonically only so far.
-- The body's ECF at euhydration, L per kg of body mass.
K.fluids.ECF_PER_KG = 0.20 -- S1714: 14 L of ECF in the 70 kg man (derived 14 / 70); McCance also took 20 % (S1730)
-- The contraction, as a share of ECF, at which vasopressin starts to defend volume over osmolality.
K.fluids.DEFEND_ONSET = 0.08 -- 8-10 % blood (rat, S1717) / plasma (review, S1722) volume fall; human dose-response open (S1736); applied to ECF, a game choice
-- The contraction, as a share of ECF, at which the volume is fully defended.
K.fluids.DEFEND_FULL = 0.20 -- S1729: McCance's weight levels at a 2-3 kg loss, about 15-23 % of ECF (Fig. 1 read by eye)

-- The euhydration set point weu, g against baseline, at body mass w kg: the water the sodium and potassium balances
-- carry isotonically. Potassium's share is a game choice (no row prices it): conc counts na + k, so weu counts both,
-- and water at weu reads c = 1 exactly. A deficit contracts it fully up to DEFEND_ONSET of ECF (a); past that the
-- weight with which water follows sodium falls linearly with the contraction to 0 at DEFEND_FULL (b), so a requested
-- contraction x gives b - (b - a) exp(-(x - a) / (b - a)), bounded by b: past the onset a further sodium loss leaves
-- the water in place. The same ramp relaxes the hypotonic thirst cap (K.fluids.defence, Plan 11f Task 5b fix 2), so
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
-- reached x = -weu, so 0 up to DEFEND_ONSET of ECF and toward 1 at DEFEND_FULL (Plan 11f Task 5b fix 2). thirstTarget
-- relaxes the hypotonic cap by it; riding the set point's ramp is a game choice resting on S1729, S1731 and S1724.
function K.fluids.defence(f, w)
    local F = K.fluids
    local ecf = F.ECF_PER_KG * w * 1000
    local a = F.DEFEND_ONSET * ecf
    local b = F.DEFEND_FULL * ecf
    return K.clamp((-F.weu(f, w) - a) / (b - a), 0, 1)
end

-- Sweat sodium adapts to a sodium deficit (Plan 11f Task 5b fix 3, candidate C-14; 08-sweat-sodium.md section 7). The
-- driver is the deficit max(-na, 0), not the diet or heat exposure: "the presence of a salt deficit is required"
-- (S1747); McCance 1938's deficiency arm fell 72 -> 33 mM Na while his generous arm rose 62 -> 70 (S1749); Armstrong
-- 1985's low-sodium arm fell 45 -> 26 while the high arm rose 41 -> 56 (S1750). Allsopp 1998 saw a fall without a
-- deficit (S1755), so a replete, acclimatising worker under-adapts here (an exposure field is a later candidate).
-- No gland lag is stored (S1748: 1-4 days; S1773: about 12 h): the deficit's own build-up is the delay.
-- The floor ratio: the median of the 5-13 day deficit arms, Weiner 13/40 = 0.325 (S1751), between Komives 15/50 = 0.30
-- (S1769) and McCance 1938's 33/72 = 0.46 (S1749) (derived); two of the three are chloride ratios read as sodium
-- (S0518: chloride tracks sodium), the arms are n = 1, 4 and 2, and none measured its deficit.
K.fluids.NA_SWEAT_MIN_FRAC = 0.325 -- derived: the median of S1769, S1751, S1749
-- The deficit, mmol, at which the floor ratio is reached: a line from (0, 1) through the mean of Robinson 1956 (169 mmol
-- Cl depleted, 28 -> 17 mM Cl, S1752, a chloride proxy) and Armstrong 1985 (-230.4 mmol body sodium, 45 -> 26 mM Na,
-- S1750, S1753), that is (199.7, 0.5925), reaches 0.325 at 330.8 mmol (derived). The zero anchor and the straight line
-- are game choices, not a fitted dose-response (open S1770).
K.fluids.NA_SWEAT_DEF_FULL = 331 -- derived from S1752, S1750, S1753; the line a game choice (S1770 open)
-- The absolute floor, mmol/L: a game choice resting on the low end of S0518's 10-90 and of Allan and Wilson's 10-58
-- (S1758); not a measured floor. It keeps a low draw from falling to 3.
K.fluids.NA_SWEAT_ABS_MIN = 10 -- game choice: S0518, S1758

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
