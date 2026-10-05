-- NR_Kernel_Aerobic.lua -- the body model's trained aerobic capacity (Plan 3): TAC, stepped once per game
-- day toward a target set by the week's aerobic volume and gated by protein, energy availability, iron
-- and sleep; and the two endurance coefficients it and the body's state set, the drain coefficient dmod
-- and the regeneration coefficient rmod, computed on the slow clock and handed down as scalars.
-- Plan 3 applies rmod only to the asleep regeneration arm the fast kernel already owns (ruling 2); dmod
-- is stamped for Plan 5's awake takeover. Iron, glycogen, dehydration, caffeine, alcohol, sleep debt,
-- hours awake and the balance dial are Plan 4/5 inputs the adapter passes neutral (ruling 12).
-- Pure: numbers and Lua tables in, numbers and Lua tables out, no Java. Slow-clock code with no fast
-- region, so math.exp and math.log are allowed. This file sorts before NR_Kernel_Body.lua, so every
-- K.clamp / K.min / K.max reference is at call time.
local K = NutritionRevamp.kernel
K.aerobic = {}

-- TAC's clamp: parity 1.00, the trained ceiling +25 %.
K.aerobic.TAC_MIN = 0.80 -- floor game choice
K.aerobic.TAC_MAX = 1.25 -- ceiling S0661/S0662/S0666

-- The gain and loss time constants, days.
K.aerobic.TAU_GAIN = 15 -- S0668
K.aerobic.TAU_LOSS = 84 -- calibrated to S0675; game choice

-- The weekly band-1 minutes that reach the full target (40 min x 6 d), and the hard days that hold it.
K.aerobic.VOL_WEEK_FULL = 240 -- S0668 40x6
K.aerobic.HARD_DAYS_KEEP = 2 -- S0669

-- The gain gates: protein below P_LOW g/kg/d, energy availability below EA_THRESHOLD kcal per kg lean,
-- the iron grades (replete, marginal, depleted, clinical) and severe sleep debt.
K.aerobic.G_PROT_LOW = 0.85 -- S0715
K.aerobic.P_LOW = 0.8 -- S0509
K.aerobic.EA_THRESHOLD = 30 -- S0691/S0692
K.aerobic.G_ENERGY_LOW = 0.5 -- S0691/S0692
K.aerobic.G_IRON = { 1.0, 0.7, 0.4, 0.4 } -- S0701/S0702; rungs inference
K.aerobic.G_SLEEP_SEVERE = 0.70 -- S0721; rungs inference
K.aerobic.SLEEP_DEBT_FROM = 8 -- S0721; game choice: the debt in hours at which the gate starts
K.aerobic.SLEEP_DEBT_SPAN = 16 -- S0721; game choice: severe at 8 + 16 = 24 h

-- The excess-fat reference: the sex's normal-band fat at 80 kg (1 male, 2 female), K.body.BF_MALE[4]
-- and BF_FEMALE[4] times 80 (Ruling T6-1); the adapter passes FM_NORMAL_80[body.sex] to excessPct.
K.aerobic.FM_NORMAL_80 = { 14.4, 22.4 } -- S1051 design-phase-v1, a reading of K.body's anchors

-- The coefficients' exponents on TAC, the drain cap and the regeneration floor.
K.aerobic.EXP_D = -0.8 -- game choices § 7 item 31
K.aerobic.EXP_R = 1.2 -- game choices § 7 item 31
K.aerobic.D_CAP = 2.5 -- game choices § 7 item 31
K.aerobic.R_FLOOR = 0.25 -- game choices § 7 item 31

-- Glycogen: the drain rises GLYC_D x (1 - g)^2; regeneration runs at GLYC_R + (1 - GLYC_R) x g.
K.aerobic.GLYC_D = 0.35 -- S0684
K.aerobic.GLYC_R = 0.5 -- S0684; inference

-- Dehydration in percent body mass: the drain's two slopes above HYDR_T1 and HYDR_T2.
K.aerobic.HYDR_T1 = 2 -- S0706/S0707
K.aerobic.HYDR_K1 = 0.03 -- S0706/S0707
K.aerobic.HYDR_T2 = 4 -- S0706/S0707
K.aerobic.HYDR_K2 = 0.09 -- S0706/S0707

-- The heat ladder by the engine's hyperthermia level 0-4 (indexed level + 1), and the heat-dehydration
-- interaction HEAT_HYDR_K x (d / HEAT_HYDR_PCT) x (level / HEAT_HYDR_LEVEL).
K.aerobic.HEAT = { 1.0, 1.10, 1.25, 1.50, 2.00 } -- S0730 design-phase-v1: open row, a game choice until it settles
K.aerobic.HEAT_HYDR_K = 0.10 -- S1021
K.aerobic.HEAT_HYDR_PCT = 4 -- S1021: the interaction's dehydration unit
K.aerobic.HEAT_HYDR_LEVEL = 2 -- S1021: the interaction's heat-level unit

-- Fat as load: per point of excess fat percentage.
K.aerobic.FAT_LOAD_K = 0.008 -- S0723

-- Iron grades 1-4 on the drain and on regeneration.
K.aerobic.IRON_D = { 1.0, 1.03, 1.08, 1.20 } -- S0696/S0697/S0694
K.aerobic.IRON_R = { 1.0, 0.95, 0.88, 0.75 } -- S0699

-- Hours awake past the knee raise the drain, capped.
K.aerobic.AWAKE_KNEE = 18 -- S0763; knee ruling 11
K.aerobic.AWAKE_K = 0.004 -- S0763
K.aerobic.AWAKE_CAP = 1.20 -- S0763

-- Caffeine lowers the drain by CAF_K x effect x (1 - tolerance).
K.aerobic.CAF_K = 0.03 -- S0531

-- Regeneration: dehydration above HYDR_T1 and sleep debt, each floored; alcohol above ALC_T g/kg, full
-- at 2 x ALC_T.
K.aerobic.HYDR_R_K = 0.05 -- game choice § 7 item 31: no row
K.aerobic.HYDR_R_FLOOR = 0.70 -- game choice § 7 item 31: no row
K.aerobic.DEBT_R_K = 0.01 -- S0762 direction
K.aerobic.DEBT_R_FLOOR = 0.60 -- S0762 direction
K.aerobic.ALC_K = 0.15 -- S0718
K.aerobic.ALC_T = 0.5 -- S0718

-- The protein gate: 1 at or above P_LOW g/kg/d, G_PROT_LOW below. It is also the regeneration
-- coefficient's protFactor (ruling 12).
function K.aerobic.gProt(pPerKg)
    if pPerKg < K.aerobic.P_LOW then
        return K.aerobic.G_PROT_LOW
    end
    return 1
end

-- The energy gate: energy availability EA = (inDay - actKcalDay) / lm kcal per kg lean; 1 at or above
-- EA_THRESHOLD, G_ENERGY_LOW below.
function K.aerobic.gEnergy(inDay, actKcalDay, lm)
    local ea = (inDay - actKcalDay) / lm
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

-- One TAC step over dtD days: toward 1 + (TAC_MAX - 1) x the week's volume fraction on TAU_GAIN days,
-- scaled by gIron x gProt x min(gEnergy, gSleep); at or above the target, held by HARD_DAYS_KEEP hard
-- days, else falling toward TAC_MIN on TAU_LOSS days. Clamped; writes body.tac and returns the body.
function K.aerobic.tacDay(body, weekMin1, hardDays, gIron, gProt, gEnergy, gSleep, dtD)
    local A = K.aerobic
    local svol = K.clamp(weekMin1 / A.VOL_WEEK_FULL, 0, 1)
    local target = 1 + (A.TAC_MAX - 1) * svol
    local gnut = gIron * gProt * K.min(gEnergy, gSleep)
    local tac = body.tac
    if target > tac then
        tac = tac + (target - tac) / A.TAU_GAIN * gnut * dtD
    elseif hardDays < A.HARD_DAYS_KEEP then
        tac = tac - (tac - A.TAC_MIN) / A.TAU_LOSS * dtD
    end
    body.tac = K.clamp(tac, A.TAC_MIN, A.TAC_MAX)
    return body
end

-- Excess fat as a percentage of body mass: 100 x max(0, fm - fmNormal) / w (Ruling T6-1: fmNormal is
-- FM_NORMAL_80 by sex, not body.fmRef).
function K.aerobic.excessPct(fm, fmNormal, w)
    return 100 * K.max(0, fm - fmNormal) / w
end

-- The drain coefficient: TAC^EXP_D x glycogen x dehydration x heat (with its dehydration interaction)
-- x fat load x iron x hours awake x caffeine, capped at D_CAP. heatLevel 0-4, ironGrade 1-4.
function K.aerobic.dmod(tac, g, dehydPct, heatLevel, excessPct, ironGrade, hoursAwake, cafEffect, cafTol)
    local A = K.aerobic
    local v = math.exp(A.EXP_D * math.log(tac))
    v = v * (1 + A.GLYC_D * (1 - g) * (1 - g))
    v = v * (1 + A.HYDR_K1 * K.max(0, dehydPct - A.HYDR_T1) + A.HYDR_K2 * K.max(0, dehydPct - A.HYDR_T2))
    v = v * A.HEAT[heatLevel + 1] * (1 + A.HEAT_HYDR_K * (dehydPct / A.HEAT_HYDR_PCT) * (heatLevel / A.HEAT_HYDR_LEVEL))
    v = v * (1 + A.FAT_LOAD_K * excessPct)
    v = v * A.IRON_D[ironGrade]
    v = v * K.min(A.AWAKE_CAP, 1 + A.AWAKE_K * K.max(0, hoursAwake - A.AWAKE_KNEE))
    v = v * (1 - A.CAF_K * cafEffect * (1 - cafTol))
    return K.min(A.D_CAP, v)
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
