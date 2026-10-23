-- NR_Kernel_Aerobic.lua -- trained aerobic capacity TAC, stepped once a game day, and the regeneration coefficient
-- rmod, which applies to the asleep regeneration arm only: awake endurance stays vanilla's.
-- Slow-clock code, so math.exp and math.log are allowed; K.clamp / K.min / K.max are read at call time.
local K = NutritionRevamp.kernel
K.aerobic = {}

-- Every dial's meaning and source is its row in NR_Data_Dials.lua.
K.aerobic.TAC_MIN = K.dials.get("aerobic.TAC_MIN")
K.aerobic.TAC_MAX = K.dials.get("aerobic.TAC_MAX")

K.aerobic.TAU_GAIN = K.dials.get("aerobic.TAU_GAIN")
K.aerobic.TAU_LOSS = K.dials.get("aerobic.TAU_LOSS")

K.aerobic.TAC_DEADBAND = K.dials.get("aerobic.TAC_DEADBAND")

K.aerobic.VOL_WEEK_FULL = K.dials.get("aerobic.VOL_WEEK_FULL")
K.aerobic.HARD_DAYS_KEEP = K.dials.get("aerobic.HARD_DAYS_KEEP")

K.aerobic.G_PROT_LOW = K.dials.get("aerobic.G_PROT_LOW")
K.aerobic.P_LOW = K.dials.get("aerobic.P_LOW")
K.aerobic.EA_THRESHOLD = K.dials.get("aerobic.EA_THRESHOLD")
K.aerobic.G_ENERGY_LOW = K.dials.get("aerobic.G_ENERGY_LOW")
K.aerobic.G_IRON = { K.dials.get("aerobic.G_IRON.1"), K.dials.get("aerobic.G_IRON.2"), K.dials.get("aerobic.G_IRON.3"), K.dials.get("aerobic.G_IRON.4") }
K.aerobic.G_SLEEP_SEVERE = K.dials.get("aerobic.G_SLEEP_SEVERE")
K.aerobic.SLEEP_DEBT_FROM = K.dials.get("aerobic.SLEEP_DEBT_FROM")
K.aerobic.SLEEP_DEBT_SPAN = K.dials.get("aerobic.SLEEP_DEBT_SPAN")

K.aerobic.EXP_R = K.dials.get("aerobic.EXP_R")
K.aerobic.R_FLOOR = K.dials.get("aerobic.R_FLOOR")

K.aerobic.GLYC_R = K.dials.get("aerobic.GLYC_R")

K.aerobic.HYDR_T1 = K.dials.get("aerobic.HYDR_T1")

K.aerobic.IRON_R = { K.dials.get("aerobic.IRON_R.1"), K.dials.get("aerobic.IRON_R.2"), K.dials.get("aerobic.IRON_R.3"), K.dials.get("aerobic.IRON_R.4") }

K.aerobic.HYDR_R_K = K.dials.get("aerobic.HYDR_R_K")
K.aerobic.HYDR_R_FLOOR = K.dials.get("aerobic.HYDR_R_FLOOR")
K.aerobic.DEBT_R_K = K.dials.get("aerobic.DEBT_R_K")
K.aerobic.DEBT_R_FLOOR = K.dials.get("aerobic.DEBT_R_FLOOR")
K.aerobic.ALC_K = K.dials.get("aerobic.ALC_K")
K.aerobic.ALC_T = K.dials.get("aerobic.ALC_T")

-- Also the regeneration coefficient's protFactor.
function K.aerobic.gProt(pPerKg)
    if pPerKg < K.aerobic.P_LOW then
        return K.aerobic.G_PROT_LOW
    end
    return 1
end

-- EA = (inDay - exKcalDay) / lm kcal per kg lean; exKcalDay is the MET above the idle class (S0691).
function K.aerobic.gEnergy(inDay, exKcalDay, lm)
    local ea = (inDay - exKcalDay) / lm
    if ea >= K.aerobic.EA_THRESHOLD then
        return 1
    end
    return K.aerobic.G_ENERGY_LOW
end

function K.aerobic.gSleep(debtH)
    local A = K.aerobic
    return 1 - (1 - A.G_SLEEP_SEVERE) * K.clamp((debtH - A.SLEEP_DEBT_FROM) / A.SLEEP_DEBT_SPAN, 0, 1)
end

-- Immobilised is tested first: an immobilised week's target is parity, so the gain step would hold it there.
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
