-- NR_Kernel_Partition.lua -- the body model's daily partition (Plan 3): once per game day the day's
-- energy balance moves fat and lean mass. A deficit is paid by fat up to Alpert's ceiling and the
-- overflow by lean under the training and protein protection, the spared energy paid by fat beyond the
-- ceiling (ruling 7); a surplus follows the lean-gain product and the rest is stored as fat; an
-- immobilised day (a leg fracture or splint, ruling 8) follows the logarithmic disuse curve instead.
-- The day close rotates the seven-day rings and zeroes the day accumulators.
-- Pure: numbers and Lua tables in, numbers, booleans and Lua tables out, no Java. Slow-clock code with
-- no fast region, so math.log and the bounded numeric `for` over the kernel's own tables are allowed.
-- This file sorts after NR_Kernel.lua, and every K.clamp / K.min / K.max reference is at call time.
local K = NutritionRevamp.kernel
K.partition = {}

-- The fat store's maximum energy transfer rate, kcal per kg fat per day.
K.partition.FAT_CEIL_KCAL = 69 -- S0056: 290 ± 25 kJ/kg fat/d

-- The tissue energy densities, kcal per kg.
K.partition.RHO_LEAN = 1816 -- S0126 design-phase-v1: Hall's densities; the row is open
K.partition.RHO_FAT = 9441 -- S0126 design-phase-v1: Hall's densities; the row is open

-- The lean protection in a deficit: the strength-dose and protein-gate weights and the floor.
K.partition.PROT_STR = 0.55 -- S0072, S0601; the floor a game choice
K.partition.PROT_P = 0.15 -- S0072, S0601; the floor a game choice
K.partition.PROT_FLOOR = 0.30 -- S0072, S0601; the floor a game choice

-- The hypertrophy base rate, kg lean per day at full dose and full gates.
K.partition.G0 = 0.050 -- S0125 design-phase-v1; derived from S0064/S0605/S0606/S0590

-- The protein gate's ends, g per kg per day.
K.partition.P_LO = 0.8 -- S0509
K.partition.P_HI = 1.6 -- S0591/S0592

-- The surplus at which the energy gate is full, kcal per day.
K.partition.SURPLUS_RAMP = 500 -- game choice § 7 item 30; shape S0605/S0606

-- The deficit half-rate: lean still accrues at half rate in a deficit at high protein and dose.
K.partition.DEFICIT_HALF_P = 2.0 -- S0064
K.partition.DEFICIT_HALF_DSTR = 0.5 -- S0064
K.partition.DEFICIT_HALF = 0.5 -- S0064

-- The lean cap as a ratio of the creation lean mass.
K.partition.LM_CAP_RATIO = 1.25 -- game choice § 7 item 30

-- The alcohol gate: above ALC_THRESH g per kg per day the lean gain carries G_ALC.
K.partition.ALC_THRESH = 0.5 -- S0718
K.partition.G_ALC = 0.65 -- S0631

-- The disuse curve: the lean fraction lost after t days immobilised is DISUSE_A * ln(1 + t / DISUSE_T).
K.partition.DISUSE_A = 0.171 -- fitted to S0069; log shape S0612
K.partition.DISUSE_T = 22 -- fitted to S0069; log shape S0612

-- The mass guards: fat never below FM_MIN kg, lean never below LM_MIN_RATIO of the creation lean.
K.partition.FM_MIN = 0.5 -- game-choice guards
K.partition.LM_MIN_RATIO = 0.35 -- game-choice guards

-- The protein gate: 0 at or below P_LO g/kg/d, 1 at or above P_HI, linear between.
function K.partition.gProt(pPerKg)
    local P = K.partition
    return K.clamp((pPerKg - P.P_LO) / (P.P_HI - P.P_LO), 0, 1)
end

-- The energy gate: a surplus ramps 0 .. 1 over SURPLUS_RAMP kcal; a deficit reads DEFICIT_HALF at
-- protein >= DEFICIT_HALF_P and strength dose >= DEFICIT_HALF_DSTR, else 0.
function K.partition.gEnergy(ebDay, pPerKg, dStr)
    local P = K.partition
    if ebDay >= 0 then
        return K.clamp(ebDay / P.SURPLUS_RAMP, 0, 1)
    end
    if pPerKg >= P.DEFICIT_HALF_P and dStr >= P.DEFICIT_HALF_DSTR then
        return P.DEFICIT_HALF
    end
    return 0
end

-- The headroom under the lean cap: 1 at or below lm0, 0 at or above LM_CAP_RATIO * lm0, linear between.
function K.partition.headroom(lm, lm0)
    local cap = K.partition.LM_CAP_RATIO * lm0
    return K.clamp((cap - lm) / (cap - lm0), 0, 1)
end

-- The alcohol gate: G_ALC above ALC_THRESH g alcohol per kg body mass per day, else 1.
function K.partition.gAlc(alcGPerKg)
    if alcGPerKg > K.partition.ALC_THRESH then
        return K.partition.G_ALC
    end
    return 1
end

-- The lean gain in kg per day: G0 times the responder constant, the hypertrophy dose and the four
-- gates (protein, energy, headroom, alcohol per kg of fm + lm).
function K.partition.leanGain(body, dHyp, dStr, pPerKg)
    local P = K.partition
    local g = P.G0 * body.r * dHyp * P.gProt(pPerKg)
    g = g * P.gEnergy(body.ebDay, pPerKg, dStr)
    g = g * P.headroom(body.lm, body.lm0)
    return g * P.gAlc(body.alcDay / (body.fm + body.lm))
end

-- The lean protection: the share of the overflow lean still pays, 1 - PROT_STR * dStr - PROT_P * gProt,
-- clamped to [PROT_FLOOR, 1].
function K.partition.protection(dStr, gProt)
    local P = K.partition
    return K.clamp(1 - P.PROT_STR * dStr - P.PROT_P * gProt, P.PROT_FLOOR, 1)
end

-- The deficit arm, returning dFM, dLM (kg): fat pays up to FAT_CEIL_KCAL * fm, the overflow is paid
-- by lean at RHO_LEAN times the protection, and the energy the protection spares is paid by fat beyond
-- the ceiling. Ruling 7: fat pays the spared energy beyond the ceiling so mass balance closes.
function K.partition.deficit(body, dStr, gProt)
    local P = K.partition
    local deficit = -body.ebDay
    local fatCap = P.FAT_CEIL_KCAL * body.fm
    local fromFat = K.min(deficit, fatCap)
    local overflow = deficit - fromFat
    local prot = P.protection(dStr, gProt)
    local leanLoss = overflow / P.RHO_LEAN * prot
    local spared = overflow * (1 - prot)
    local dFM = -(fromFat + spared) / P.RHO_FAT
    local dLM = -leanLoss
    return dFM, dLM
end

-- The surplus arm, returning dFM, dLM (kg): lean gains the lean-gain law's amount, never more than the
-- surplus can pay at RHO_LEAN, and the rest of the surplus is stored as fat.
function K.partition.surplus(body, dHyp, dStr, pPerKg)
    local P = K.partition
    local gain = K.min(P.leanGain(body, dHyp, dStr, pPerKg), body.ebDay / P.RHO_LEAN)
    local dLM = gain
    local dFM = (body.ebDay - gain * P.RHO_LEAN) / P.RHO_FAT
    return dFM, dLM
end

-- The lean fraction lost after tDays immobilised: DISUSE_A * ln(1 + tDays / DISUSE_T).
function K.partition.disuseFraction(tDays)
    local P = K.partition
    return P.DISUSE_A * math.log(1 + tDays / P.DISUSE_T)
end

-- The disuse arm for immobilised day tDisuse (>= 1; the adapter stamps lm0dis, the lean mass on the
-- day disuse began, when tDisuse goes 0 -> 1), returning dFM, dLM (kg): lean loses lm0dis times the
-- curve's step from day tDisuse - 1 to day tDisuse, whatever the balance. Fat takes the deficit arm
-- with the lean overflow set to 0: fat pays up to the ceiling and the energy beyond it is UNPAID under
-- immobilisation (the disuse loss stands in for the lean arm); a surplus reads as a negative deficit
-- under the ceiling and is stored as fat.
function K.partition.disuse(body)
    local P = K.partition
    local t = body.tDisuse
    local dLM = -body.lm0dis * (P.disuseFraction(t) - P.disuseFraction(t - 1))
    local fromFat = K.min(-body.ebDay, P.FAT_CEIL_KCAL * body.fm)
    local dFM = -fromFat / P.RHO_FAT
    return dFM, dLM
end

-- One day's partition: immobilised -> disuse; a deficit -> deficit (its protein gate from pPerKg);
-- else surplus. Applies the masses under the FM_MIN and LM_MIN_RATIO * lm0 guards and re-bases fmRef
-- upward (adaptive thermogenesis reads depletion from the highest fat mass reached). Returns the arm's
-- dFM, dLM before the guards.
function K.partition.day(body, dHyp, dStr, pPerKg, immobilised)
    local P = K.partition
    local dFM = 0
    local dLM = 0
    if immobilised then
        dFM, dLM = P.disuse(body)
    elseif body.ebDay < 0 then
        dFM, dLM = P.deficit(body, dStr, P.gProt(pPerKg))
    else
        dFM, dLM = P.surplus(body, dHyp, dStr, pPerKg)
    end
    body.fm = K.max(body.fm + dFM, P.FM_MIN)
    body.lm = K.max(body.lm + dLM, P.LM_MIN_RATIO * body.lm0)
    body.fmRef = K.max(body.fmRef, body.fm)
    return dFM, dLM
end

-- Close the day: shift eb7, mass7, p7, carb7 and lip7 one slot (slot 1 the oldest), write the day's
-- ebDay, fm + lm, pDay, carbDay and lipDay into slot 7 (the legacy mirror's yesterday), zero the day
-- accumulators and advance dayIndex. Returns the body.
function K.partition.closeDay(body)
    local eb = body.eb7
    local mass = body.mass7
    local p7 = body.p7
    local carb7 = body.carb7
    local lip7 = body.lip7
    for i = 1, 6 do
        eb[i] = eb[i + 1]
        mass[i] = mass[i + 1]
        p7[i] = p7[i + 1]
        carb7[i] = carb7[i + 1]
        lip7[i] = lip7[i + 1]
    end
    eb[7] = body.ebDay
    mass[7] = body.fm + body.lm
    p7[7] = body.pDay
    carb7[7] = body.carbDay
    lip7[7] = body.lipDay
    body.inDay = 0
    body.eeDay = 0
    body.ebDay = 0
    body.actKcalDay = 0
    body.pDay = 0
    body.carbDay = 0
    body.lipDay = 0
    body.alcDay = 0
    body.dayIndex = body.dayIndex + 1
    return body
end

-- Whether the seven closed days sum to a deficit.
function K.partition.deficitWeek(body)
    local sum = 0
    for i = 1, 7 do
        sum = sum + body.eb7[i]
    end
    return sum < 0
end
