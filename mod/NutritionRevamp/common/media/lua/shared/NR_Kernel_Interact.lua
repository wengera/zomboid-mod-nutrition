-- NR_Kernel_Interact.lua -- the nutrient interactions and the non-pool steps (Plan 4, ruling 20; formulas
-- briefing A3, A4, A6): two layers in one file.
-- 1. The factor functions, pure multipliers and loss terms the adapter (Task 11) applies to the absorbed
--    vector BEFORE K.nutrients.minute, and the intake wrapper (Task 12) applies per eat: calcium x iron,
--    phytate x magnesium and zinc, the B12 intrinsic-factor ceiling, the carotene gate on liver status,
--    raw egg x biotin, riboflavin x iron transfer, alcohol x thiamine rate, the caffeine and alcohol
--    urinary mineral losses, zinc -> copper, and the blood-loss event on haemoglobin iron.
--    The caffeine and alcohol loss magnitudes are PLACEHOLDERS: their rows (S1087, S1086) are open and
--    carry direction only (S0543, S0542), so CAF_MG_LOSS, CAF_LM_REF and ALC_MG_LOSS are game choices.
-- 2. K.interact.two(key, s, rec, aAbs, ctx, dtD, dtH), the step the engine calls for every pool2, counter,
--    derived and excessOnly record (the adapter injects it as ctx.two): iron's store and haemoglobin
--    compartments (A6), vitamin A's liver and plasma, B12's store and functional fraction with its damage
--    counter, the calcium bone counter, the biotin raw-egg counter, the fibre 7-day EMA and copper derived
--    from the zinc excess; selenium (excessOnly) and any unknown record are not stepped.
-- The ctx fields read: sex (1 male, 2 female, Plan 3's K.body convention), w (kg), dial (nil = 1), riboGrade
-- (nil = 1), rawEggDay (true on a raw-egg day), e24Zn (nil = 0), and through K.nutrients.requirement eeMJ,
-- pDay for scaled records. The state fields added lazily (numbers only, #1495): S and H (iron, absolute mg)
-- and bone (calcium, mg); biotin reuses ext (its record has no chronic, so the engine's excess never writes
-- it). Pure: numbers and Lua tables in, numbers and Lua tables out, no Java. Slow-clock code with no fast
-- region, so math.exp is allowed. This file sorts after NR_Kernel.lua and before NR_Kernel_Nutrients.lua, so, and
-- every K.clamp / K.min / K.max / K.nutrients reference is at call time.
local K = NutritionRevamp.kernel
K.interact = {}

-- Calcium x iron: 1 - CA_FE_MAX x clamp(Ca_meal / CA_FE_REF, 0, 1), flat above the reference.
K.interact.CA_FE_REF = 300 -- mg calcium per meal at the full effect, S0418 (40-300 mg dose-related, little further above ~600 mg)
K.interact.CA_FE_MAX = 0.5 -- the 50 % reduction at 300 mg: design-phase-v1 game choice (open S1081; direction S0418)

-- Phytate x magnesium: exp(-PHY_SLOPE x phytate mg); zinc reuses the slope.
K.interact.PHY_SLOPE = 0.00093 -- per mg phytic acid: ln(32.5/13.0)/983 derived from S0536 (1.49 mmol = 983 mg); the zinc reuse is a game choice (open S1084; direction S0454)

-- The B12 intrinsic-factor ceiling per eat: min(B12_ACTIVE_FRAC x a, B12_ACTIVE_MAX) + B12_PASSIVE x max(0, a - B12_PASSIVE_FROM).
K.interact.B12_ACTIVE_FRAC = 0.5 -- ~50 % of a 1 ug dose absorbed, S0358
K.interact.B12_ACTIVE_MAX = 2.0 -- ug per meal via the active route, S0357
K.interact.B12_PASSIVE = 0.012 -- ~1.2 % of a dose absorbed passively, S0358
K.interact.B12_PASSIVE_FROM = 4 -- ug: the dose that saturates the active route, B12_ACTIVE_MAX / B12_ACTIVE_FRAC derived from S0357/S0358

-- Carotene conversion stops at this liver p (the record's two.caroteneOff wins when passed).
K.interact.CAROTENE_OFF = 1.0 -- liver > 0.4 umol/g suppresses bioconversion, S0202

-- Riboflavin x iron: the store-to-haemoglobin transfer at RIBO_FE_XFER once riboflavin is at RIBO_FE_GRADE or worse.
K.interact.RIBO_FE_GRADE = 3 -- the depleted grade, game choice (direction S0261)
K.interact.RIBO_FE_XFER = 0.5 -- halved transfer: design-phase-v1 game choice (open S1082; direction S0261)

-- Alcohol x thiamine: k x (1 + LAMBDA_ALC x alcohol g/kg/day).
K.interact.LAMBDA_ALC = 0.5 -- per g/kg/day: game choice (the contributions are open S0553; direction S0250)

-- The caffeine urinary mineral loss: CAF_MG_LOSS mg per mg caffeine at CAF_LM_REF kg lean, scaled by CAF_LM_REF / lean mass.
K.interact.CAF_MG_LOSS = 0.02 -- mg Mg (and Ca) per mg caffeine: placeholder game choice (open S1087; direction S0543)
K.interact.CAF_LM_REF = 60 -- kg lean mass the placeholder is set at: game choice (S0543: proportional to dose per lean mass)

-- The alcohol urinary magnesium loss.
K.interact.ALC_MG_LOSS = 2 -- mg Mg per g ethanol: placeholder game choice (open S1086; direction S0542)

-- The iron cost of blood loss.
K.interact.BLOOD_FE = 0.5 -- mg iron per mL whole blood: design-phase-v1 game choice (open S0554)

-- The biotin p at cosmeticDays: 1 - BIOTIN_DROP lands at 0.69, grade 2 on the generic 0.70 rung.
K.interact.BIOTIN_DROP = 0.31 -- game choice (the onset is open S1076)

-- Calcium x iron absorption factor for a meal's calcium in mg.
function K.interact.calciumIron(caMealMg)
    return 1 - K.interact.CA_FE_MAX * K.clamp(caMealMg / K.interact.CA_FE_REF, 0, 1)
end

-- Phytate x magnesium absorption factor for a meal's phytic acid in mg.
function K.interact.phytateMg(phytateMg)
    return math.exp(-K.interact.PHY_SLOPE * phytateMg)
end

-- Phytate x zinc: the magnesium slope reused (open S1084).
function K.interact.phytateZn(phytateMg)
    return K.interact.phytateMg(phytateMg)
end

-- The B12 absorbed from one eat of aUg ingested (applied per eat by the intake wrapper, before the stomach).
function K.interact.b12Ceiling(aUg)
    local active = K.min(K.interact.B12_ACTIVE_FRAC * aUg, K.interact.B12_ACTIVE_MAX)
    return active + K.interact.B12_PASSIVE * K.max(0, aUg - K.interact.B12_PASSIVE_FROM)
end

-- The carotene conversion gate: 0 once the liver p reaches off (default CAROTENE_OFF), else 1.
function K.interact.caroteneOn(liverP, off)
    local thr = off or K.interact.CAROTENE_OFF
    if liverP >= thr then
        return 0
    end
    return 1
end

-- The biotin absorption factor: 0 from a raw-egg item, 1 otherwise.
function K.interact.biotinRaw(isRawEgg)
    if isRawEgg then
        return 0
    end
    return 1
end

-- The iron store-to-haemoglobin transfer multiplier for the riboflavin grade.
function K.interact.riboIronXfer(riboGrade)
    if riboGrade >= K.interact.RIBO_FE_GRADE then
        return K.interact.RIBO_FE_XFER
    end
    return 1
end

-- The thiamine rate raised by the day's alcohol in g per kg.
function K.interact.thiamineAlcoholK(k, alcGkg)
    return k * (1 + K.interact.LAMBDA_ALC * alcGkg)
end

-- The extra urinary magnesium and calcium in mg for a caffeine dose in mg at lean mass lm kg (two returns).
function K.interact.caffeineLossMg(doseMg, lm)
    local mg = K.interact.CAF_MG_LOSS * doseMg * K.interact.CAF_LM_REF / lm
    return mg, mg
end

-- The extra urinary magnesium in mg for an ethanol dose in g.
function K.interact.alcoholLossMg(ethanolG)
    return K.interact.ALC_MG_LOSS * ethanolG
end

-- The copper p lost over dtD days under the zinc excess (e24Zn above ulZn, in units of ulZn).
function K.interact.zincCopperLoss(e24Zn, dtD, kcu, ulZn)
    return kcu * K.max(0, e24Zn - ulZn) / ulZn * dtD
end

-- A bleed of mL whole blood off the haemoglobin iron (an event Plan 5 calls); returns the mg lost. A state
-- never stepped has no H yet and loses nothing; p2 is refreshed at the next step.
function K.interact.ironBleed(s, mL)
    if s.H == nil then
        return 0
    end
    local lost = K.min(K.interact.BLOOD_FE * mL, s.H)
    s.H = s.H - lost
    return lost
end

-- Iron (A6): store S and haemoglobin iron H in absolute mg, initialised to S0 and H0 on the first step.
-- S gains the absorbed iron at eta = 1 - etaK x clamp(S/S0, 0, 1); H loses L[sex] per day; the store
-- refills H toward H0 at most xMax per day (times the riboflavin factor). p = S/S0, p2 = H/H0.
function K.interact.ironTwo(s, rec, aAbs, w, sex, dtD, riboGrade)
    local two = rec.two
    local total = two.totalPerKg[sex] * w
    local S0 = two.storeShare * total
    local H0 = two.hbShare * total
    if s.S == nil then
        s.S = S0
        s.H = H0
    end
    local eta = 1 - two.etaK * K.clamp(s.S / S0, 0, 1)
    s.S = s.S + aAbs * eta
    s.H = K.max(s.H - rec.L[sex] * dtD, 0)
    local need = K.max(0, H0 - s.H)
    local xfer = K.min(need, K.min(s.S, two.xMax * dtD * K.interact.riboIronXfer(riboGrade)))
    s.S = s.S - xfer
    s.H = s.H + xfer
    s.p = s.S / S0
    s.p2 = s.H / H0
end

-- Vitamin A: the liver p takes the engine's pool step with no cap (the record has no pCap); the plasma
-- p2 = min(1, p / plasmaKnee).
function K.interact.vitATwo(s, rec, aAbs, R, kEff, dtD)
    K.nutrients.stepPool(s, rec, aAbs, R, kEff, dtD)
    s.p2 = K.min(1, s.p / rec.two.plasmaKnee)
end

-- B12: the store p takes the engine's pool step (capped at the record's pCap); the functional
-- p2 = min(1, p / fThreshold); dmg accrues the hours spent with p2 below 1 and is never cleared (S0363).
function K.interact.b12Two(s, rec, aAbs, R, kEff, dtD, dtH)
    K.nutrients.stepPool(s, rec, aAbs, R, kEff, dtD)
    s.p2 = K.min(1, s.p / rec.two.fThreshold)
    if s.p2 < 1 then
        s.dmg = s.dmg + dtH
    end
end

-- Calcium: the bone counter in mg, bone += absorbed - lossPerDay x dtD, held between 0 and the starting
-- skeleton; aAbs is already the absorbed amount (K.stomach.BIOAVAIL.calcium), so counter.absorb is never
-- applied again. p = bone / skeleton.
function K.interact.calciumTwo(s, rec, aAbs, sex, dtD)
    local c = rec.counter
    local full = c.skeleton[sex] * 1000
    local bone = (s.bone or full) + aAbs - c.lossPerDay * dtD
    s.bone = K.clamp(bone, 0, full)
    s.p = s.bone / full
end

-- Biotin: ext counts raw-egg days (up on a raw-egg day, back down otherwise); p falls BIOTIN_DROP over
-- cosmeticDays.
function K.interact.biotinTwo(s, rec, rawEggDay, dtD)
    if rawEggDay then
        s.ext = s.ext + dtD
    else
        s.ext = K.max(0, s.ext - dtD)
    end
    s.p = 1 - K.clamp(s.ext / rec.counter.cosmeticDays, 0, 1) * K.interact.BIOTIN_DROP
end

-- Fibre: the exponential moving average of intake / R on rate kEma (7-day EMA), exact at constant intake.
function K.interact.fibreTwo(s, rec, aAbs, R, dtD)
    local rate = aAbs / dtD
    s.p = s.p + (rate / R - s.p) * (1 - math.exp(-rec.counter.kEma * dtD))
end

-- Copper: falls under the zinc excess and recovers toward 1 at kcu, held in [0, 1].
function K.interact.copperTwo(s, rec, e24Zn, dtD)
    local d = rec.derived
    local p = s.p - K.interact.zincCopperLoss(e24Zn, dtD, d.kcu, d.ulZn) + d.kcu * (1 - s.p) * dtD
    s.p = K.clamp(p, 0, 1)
end

-- The engine's ctx.two: the step for a pool2, counter, derived or excessOnly record by kind and key. A
-- zero step, selenium (excessOnly) and an unknown kind or key are not stepped.
function K.interact.two(key, s, rec, aAbs, ctx, dtD, dtH)
    if dtD <= 0 then
        return
    end
    local kind = rec.kind
    if kind == "pool2" then
        if key == "iron" then
            K.interact.ironTwo(s, rec, aAbs, ctx.w, ctx.sex, dtD, ctx.riboGrade or 1)
        elseif key == "vitA" then
            K.interact.vitATwo(s, rec, aAbs, K.nutrients.requirement(rec, ctx), K.nutrients.kEff(rec, rec.k, ctx.dial or 1), dtD)
        elseif key == "vitB12" then
            K.interact.b12Two(s, rec, aAbs, K.nutrients.requirement(rec, ctx), K.nutrients.kEff(rec, rec.k, ctx.dial or 1), dtD, dtH)
        end
    elseif kind == "counter" then
        if key == "calcium" then
            K.interact.calciumTwo(s, rec, aAbs, ctx.sex, dtD)
        elseif key == "biotin" then
            K.interact.biotinTwo(s, rec, ctx.rawEggDay == true, dtD)
        elseif key == "fibre" then
            K.interact.fibreTwo(s, rec, aAbs, K.nutrients.requirement(rec, ctx), dtD)
        end
    elseif kind == "derived" then
        if key == "copper" then
            K.interact.copperTwo(s, rec, ctx.e24Zn or 0, dtD)
        end
    end
end
