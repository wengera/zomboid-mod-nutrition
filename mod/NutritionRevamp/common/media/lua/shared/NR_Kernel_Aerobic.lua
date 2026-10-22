-- NR_Kernel_Aerobic.lua -- the body model's trained aerobic capacity: TAC, stepped once per game
-- day toward a target set by the week's aerobic volume and gated by protein, energy availability, iron
-- and sleep; and the regeneration coefficient rmod it and the body's state set, computed on the slow clock
-- and handed down as a scalar, which applies to the asleep regeneration arm only: awake endurance
-- stays vanilla's, so no drain coefficient is computed. Iron, glycogen, dehydration, alcohol, sleep debt and the
-- balance dial are read from the record's Plan 4 sub-tables by the adapter.
-- Pure: numbers and Lua tables in, numbers and Lua tables out, no Java. Slow-clock code with no fast
-- region, so math.exp and math.log are allowed. This file sorts before NR_Kernel_Body.lua, so every
-- K.clamp / K.min / K.max reference is at call time.
local K = NutritionRevamp.kernel
K.aerobic = {}

-- TAC's clamp: parity 1.00, the trained ceiling +25 %.
K.aerobic.TAC_MIN = K.dials.get("aerobic.TAC_MIN")
K.aerobic.TAC_MAX = K.dials.get("aerobic.TAC_MAX")

-- The gain and loss time constants, days.
K.aerobic.TAU_GAIN = K.dials.get("aerobic.TAU_GAIN")
K.aerobic.TAU_LOSS = K.dials.get("aerobic.TAU_LOSS")

-- The dead band around the target and parity: no step closer than this.
K.aerobic.TAC_DEADBAND = K.dials.get("aerobic.TAC_DEADBAND")

-- The weekly band-1 minutes that reach the full target (40 min x 6 d), and the hard days that hold it.
K.aerobic.VOL_WEEK_FULL = K.dials.get("aerobic.VOL_WEEK_FULL")
K.aerobic.HARD_DAYS_KEEP = K.dials.get("aerobic.HARD_DAYS_KEEP")

-- The gain gates: protein below P_LOW g/kg/d, energy availability below EA_THRESHOLD kcal per kg lean,
-- the iron grades (replete, marginal, depleted, clinical) and severe sleep debt.
K.aerobic.G_PROT_LOW = K.dials.get("aerobic.G_PROT_LOW")
K.aerobic.P_LOW = K.dials.get("aerobic.P_LOW")
K.aerobic.EA_THRESHOLD = K.dials.get("aerobic.EA_THRESHOLD")
K.aerobic.G_ENERGY_LOW = K.dials.get("aerobic.G_ENERGY_LOW")
K.aerobic.G_IRON = { K.dials.get("aerobic.G_IRON.1"), K.dials.get("aerobic.G_IRON.2"), K.dials.get("aerobic.G_IRON.3"), K.dials.get("aerobic.G_IRON.4") }
K.aerobic.G_SLEEP_SEVERE = K.dials.get("aerobic.G_SLEEP_SEVERE")
K.aerobic.SLEEP_DEBT_FROM = K.dials.get("aerobic.SLEEP_DEBT_FROM")
K.aerobic.SLEEP_DEBT_SPAN = K.dials.get("aerobic.SLEEP_DEBT_SPAN")

-- The coefficient's exponent on TAC and its floor.
K.aerobic.EXP_R = K.dials.get("aerobic.EXP_R")
K.aerobic.R_FLOOR = K.dials.get("aerobic.R_FLOOR")

-- Glycogen: regeneration runs at GLYC_R + (1 - GLYC_R) x g.
K.aerobic.GLYC_R = K.dials.get("aerobic.GLYC_R")

-- Dehydration in percent body mass above which regeneration falls.
K.aerobic.HYDR_T1 = K.dials.get("aerobic.HYDR_T1")

-- Iron grades 1-4 on regeneration.
K.aerobic.IRON_R = { K.dials.get("aerobic.IRON_R.1"), K.dials.get("aerobic.IRON_R.2"), K.dials.get("aerobic.IRON_R.3"), K.dials.get("aerobic.IRON_R.4") }

-- Regeneration: dehydration above HYDR_T1 and sleep debt, each floored; alcohol above ALC_T g/kg, full
-- at 2 x ALC_T.
K.aerobic.HYDR_R_K = K.dials.get("aerobic.HYDR_R_K")
K.aerobic.HYDR_R_FLOOR = K.dials.get("aerobic.HYDR_R_FLOOR")
K.aerobic.DEBT_R_K = K.dials.get("aerobic.DEBT_R_K")
K.aerobic.DEBT_R_FLOOR = K.dials.get("aerobic.DEBT_R_FLOOR")
K.aerobic.ALC_K = K.dials.get("aerobic.ALC_K")
K.aerobic.ALC_T = K.dials.get("aerobic.ALC_T")

-- The protein gate: 1 at or above P_LOW g/kg/d, G_PROT_LOW below. It is also the regeneration
-- coefficient's protFactor.
function K.aerobic.gProt(pPerKg)
    if pPerKg < K.aerobic.P_LOW then
        return K.aerobic.G_PROT_LOW
    end
    return 1
end

-- The energy gate: energy availability EA = (inDay - exKcalDay) / lm kcal per kg lean, exKcalDay the
-- day's exercise kcal (the MET above the idle class, K.energy.minute; S0691); 1 at or above
-- EA_THRESHOLD, G_ENERGY_LOW below.
function K.aerobic.gEnergy(inDay, exKcalDay, lm)
    local ea = (inDay - exKcalDay) / lm
    if ea >= K.aerobic.EA_THRESHOLD then
        return 1
    end
    return K.aerobic.G_ENERGY_LOW
end

-- The sleep gate: 1 up to SLEEP_DEBT_FROM hours of debt, linear to G_SLEEP_SEVERE at FROM + SPAN.
function K.aerobic.gSleep(debtH)
    local A = K.aerobic
    return 1 - (1 - A.G_SLEEP_SEVERE) * K.clamp((debtH - A.SLEEP_DEBT_FROM) / A.SLEEP_DEBT_SPAN, 0, 1)
end

-- One TAC step over dtD days: immobilised, falling toward TAC_MIN on TAU_LOSS days (first,
-- since an immobilised week's target is parity and the gain step would hold it there); else below the
-- target by more than TAC_DEADBAND, toward 1 + (TAC_MAX - 1) x the week's volume fraction on TAU_GAIN
-- days, scaled by gIron x gProt x min(gEnergy, gSleep); else a trained capacity above parity not held
-- by HARD_DAYS_KEEP hard days falls toward parity 1.0 on TAU_LOSS days; else no step.
-- Clamped; writes body.tac and returns the body.
function K.aerobic.tacDay(body, weekMin1, hardDays, gIron, gProt, gEnergy, gSleep, dtD, immobilised)
    local A = K.aerobic
    local svol = K.clamp(weekMin1 / A.VOL_WEEK_FULL, 0, 1)
    local target = 1 + (A.TAC_MAX - 1) * svol
    local gnut = gIron * gProt * K.min(gEnergy, gSleep)
    local tac = body.tac
    local maintained = hardDays >= A.HARD_DAYS_KEEP
    if immobilised then
        tac = tac - (tac - A.TAC_MIN) / A.TAU_LOSS * dtD
    elseif target > tac + A.TAC_DEADBAND then
        tac = tac + (target - tac) / A.TAU_GAIN * gnut * dtD
    elseif tac > 1 + A.TAC_DEADBAND and not maintained then
        tac = tac - (tac - 1) / A.TAU_LOSS * dtD
    end
    body.tac = K.clamp(tac, A.TAC_MIN, A.TAC_MAX)
    return body
end

-- The regeneration coefficient: TAC^EXP_R x glycogen x protFactor x iron x dehydration x sleep debt x
-- alcohol x the balance bonus, floored at R_FLOOR. ironGrade 1-4.
function K.aerobic.rmod(tac, g, protFactor, ironGrade, dehydPct, debtH, alcGPerKg, balanceBonus)
    local A = K.aerobic
    local v = math.exp(A.EXP_R * math.log(tac))
    v = v * (A.GLYC_R + (1 - A.GLYC_R) * g)
    v = v * protFactor
    v = v * A.IRON_R[ironGrade]
    v = v * K.max(A.HYDR_R_FLOOR, 1 - A.HYDR_R_K * K.max(0, dehydPct - A.HYDR_T1))
    v = v * K.max(A.DEBT_R_FLOOR, 1 - A.DEBT_R_K * debtH)
    v = v * (1 - A.ALC_K * K.clamp((alcGPerKg - A.ALC_T) / A.ALC_T, 0, 1))
    v = v * balanceBonus
    return K.max(A.R_FLOOR, v)
end
