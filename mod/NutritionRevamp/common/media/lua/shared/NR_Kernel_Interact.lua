-- NR_Kernel_Interact.lua -- the nutrient interactions, two layers: the factor functions the adapter applies to the
-- absorbed vector before K.nutrients.minute (and the intake wrapper per eat), and K.interact.two, the step the engine
-- calls for every pool2, counter, derived and excessOnly record (ctx.two). The caffeine and alcohol loss magnitudes
-- are placeholders: their rows (S1087, S1086) carry direction only. Biotin, selenium and unknown records are not
-- stepped. State fields are added lazily (numbers only, #1495). K.clamp / K.nutrients are read at call time.
local K = NutritionRevamp.kernel
K.interact = {}

-- Every dial's meaning and source is its row in NR_Data_Dials.lua.
K.interact.CA_FE_REF = K.dials.get("interact.CA_FE_REF")
K.interact.CA_FE_MAX = K.dials.get("interact.CA_FE_MAX")

K.interact.PHY_SLOPE = K.dials.get("interact.PHY_SLOPE")

K.interact.B12_ACTIVE_FRAC = K.dials.get("interact.B12_ACTIVE_FRAC")
K.interact.B12_ACTIVE_MAX = K.dials.get("interact.B12_ACTIVE_MAX")
K.interact.B12_PASSIVE = K.dials.get("interact.B12_PASSIVE")
K.interact.B12_PASSIVE_FROM = K.interact.B12_ACTIVE_MAX / K.interact.B12_ACTIVE_FRAC -- ug: the dose that saturates the active route, derived (S0357)

K.interact.CAROTENE_RAE = K.dials.get("interact.CAROTENE_RAE")
K.interact.CAROTENE_OFF = K.dials.get("interact.CAROTENE_OFF")

K.interact.RIBO_FE_GRADE = K.dials.get("interact.RIBO_FE_GRADE")
K.interact.RIBO_FE_XFER = K.dials.get("interact.RIBO_FE_XFER")

K.interact.LAMBDA_ALC = K.dials.get("interact.LAMBDA_ALC")

K.interact.CAF_MG_LOSS = K.dials.get("interact.CAF_MG_LOSS")
K.interact.CAF_LM_REF = K.dials.get("interact.CAF_LM_REF")

K.interact.ALC_MG_LOSS = K.dials.get("interact.ALC_MG_LOSS")


function K.interact.calciumIron(caMealMg)
    return 1 - K.interact.CA_FE_MAX * K.clamp(caMealMg / K.interact.CA_FE_REF, 0, 1)
end

function K.interact.phytateMg(phytateMg)
    return math.exp(-K.interact.PHY_SLOPE * phytateMg)
end

-- The magnesium slope reused (open S1084).
function K.interact.phytateZn(phytateMg)
    return K.interact.phytateMg(phytateMg)
end

-- Applied per eat by the intake wrapper, before the stomach.
function K.interact.b12Ceiling(aUg)
    local active = K.min(K.interact.B12_ACTIVE_FRAC * aUg, K.interact.B12_ACTIVE_MAX)
    return active + K.interact.B12_PASSIVE * K.max(0, aUg - K.interact.B12_PASSIVE_FROM)
end

function K.interact.caroteneOn(liverP, off)
    local thr = off or K.interact.CAROTENE_OFF
    if liverP >= thr then
        return 0
    end
    return 1
end

function K.interact.riboIronXfer(riboGrade)
    if riboGrade >= K.interact.RIBO_FE_GRADE then
        return K.interact.RIBO_FE_XFER
    end
    return 1
end

function K.interact.thiamineAlcoholK(k, alcGkg)
    return k * (1 + K.interact.LAMBDA_ALC * alcGkg)
end

-- Two returns: magnesium and calcium, mg.
function K.interact.caffeineLossMg(doseMg, lm)
    local mg = K.interact.CAF_MG_LOSS * doseMg * K.interact.CAF_LM_REF / lm
    return mg, mg
end

function K.interact.alcoholLossMg(ethanolG)
    return K.interact.ALC_MG_LOSS * ethanolG
end

function K.interact.zincCopperLoss(e24Zn, dtD, kcu, ulZn)
    return kcu * K.max(0, e24Zn - ulZn) / ulZn * dtD
end

-- Iron: absolute mg, initialised to S0 and H0 on the first step; the store refills H at most xMax a day.
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

-- Vitamin A: the liver p has no cap (the record has no pCap).
function K.interact.vitATwo(s, rec, aAbs, R, kEff, dtD)
    K.nutrients.stepPool(s, rec, aAbs, R, kEff, dtD)
    s.p2 = K.min(1, s.p / rec.two.plasmaKnee)
end

-- B12: dmg accrues the hours with p2 below 1 and is never cleared (S0363).
function K.interact.b12Two(s, rec, aAbs, R, kEff, dtD, dtH)
    K.nutrients.stepPool(s, rec, aAbs, R, kEff, dtD)
    s.p2 = K.min(1, s.p / rec.two.fThreshold)
    if s.p2 < 1 then
        s.dmg = s.dmg + dtH
    end
end

-- Calcium: aAbs is already absorbed (K.stomach.BIOAVAIL.calcium), so no absorption is applied again.
function K.interact.calciumTwo(s, rec, aAbs, sex, dtD)
    local c = rec.counter
    local full = c.skeleton[sex] * 1000
    local bone = (s.bone or full) + aAbs - c.lossPerDay * dtD
    s.bone = K.clamp(bone, 0, full)
    s.p = s.bone / full
end

-- Fibre: a 7-day EMA, exact at constant intake.
function K.interact.fibreTwo(s, rec, aAbs, R, dtD)
    local rate = aAbs / dtD
    s.p = s.p + (rate / R - s.p) * (1 - math.exp(-rec.counter.kEma * dtD))
end

function K.interact.copperTwo(s, rec, e24Zn, dtD)
    local d = rec.derived
    local p = s.p - K.interact.zincCopperLoss(e24Zn, dtD, d.kcu, d.ulZn) + d.kcu * (1 - s.p) * dtD
    s.p = K.clamp(p, 0, 1)
end

-- A zero step, selenium and an unknown kind or key are not stepped.
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
        elseif key == "fibre" then
            K.interact.fibreTwo(s, rec, aAbs, K.nutrients.requirement(rec, ctx), dtD)
        end
    elseif kind == "derived" then
        if key == "copper" then
            K.interact.copperTwo(s, rec, ctx.e24Zn or 0, dtD)
        end
    end
end
