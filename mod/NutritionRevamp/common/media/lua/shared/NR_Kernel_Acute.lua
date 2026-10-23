-- NR_Kernel_Acute.lua: the acute states: caffeine (load, 7-day mean, tolerance, withdrawal), alcohol (Widmark load,
-- BAC, hangover), glycogen and blood glucose, sleep (hours awake, the window's debt, S, circ, the freeze when the
-- server disables sleep), the body clock, the impairment unit, the exercise, cold and retinol memories and refeeding.
-- Every dtH and ageH is GAME hours; a held sleep runs the world clock about 20x, so it arrives as a long sleep
-- (ruling T5-1). The first-order relaxations use the exact exponential step, so a one-minute step and a long catch-up
-- step agree. Caffeine and ethanol absorb from a gut lane the intake feeds directly, never through the stomach's
-- drain (one beer built no blood alcohol through it, #2983). Pure, no Java; slow-clock code. Sorts after
-- NR_Kernel.lua; K.clamp, K.min and K.max resolve at call time.
local K = NutritionRevamp.kernel
K.acute = {}

-- Applied once in K.acute.absorbGut; alcohol and caffeine take the dose it releases, so nothing re-applies it.
K.acute.CAF_ABSORB = K.dials.get("acute.CAF_ABSORB")
K.acute.CAF_THALF_H = K.dials.get("acute.CAF_THALF_H")
K.acute.CAF_THALF_SLOW_H = K.dials.get("acute.CAF_THALF_SLOW_H")
K.acute.CAF_SLOW_SHARE = K.dials.get("acute.CAF_SLOW_SHARE")
K.acute.CAF_MEAN_H = K.dials.get("acute.CAF_MEAN_H")
K.acute.CAF_TOL_REF = K.dials.get("acute.CAF_TOL_REF")
K.acute.CAF_TOL_TAU_H = K.dials.get("acute.CAF_TOL_TAU_H")
K.acute.CAF_WD_TOL = K.dials.get("acute.CAF_WD_TOL")
K.acute.CAF_WD_LOW_MG = K.dials.get("acute.CAF_WD_LOW_MG")
K.acute.CAF_WD_ONSET_H = K.dials.get("acute.CAF_WD_ONSET_H")
K.acute.CAF_WD_PEAK_H = K.dials.get("acute.CAF_WD_PEAK_H")
K.acute.CAF_WD_END_H = K.dials.get("acute.CAF_WD_END_H")
K.acute.CAF_EFFECT_MGKG = K.dials.get("acute.CAF_EFFECT_MGKG")

-- First order on this half-time, game hours.
K.acute.GUT_T_HALF = K.dials.get("acute.GUT_T_HALF")

K.acute.WIDMARK_R = {
    K.dials.get("acute.WIDMARK_R.1"),
    K.dials.get("acute.WIDMARK_R.2"),
}
K.acute.BETA = K.dials.get("acute.BETA")
K.acute.HANG_PEAK = K.dials.get("acute.HANG_PEAK")

-- The stimulant sets: NR.StimulantRealism (1 Game, the default; 2 Realistic) selects K.acute.C once, when the options
-- read sees the value change, never per call. Game overrides sizes only (a cup's fatigue offset, the intoxication per
-- drink, the hangover's tail), so every timing stays the science of both sets.
K.acute.STIM_REALISTIC = {
    MODE = 2, -- no row needed: the option's value
    CAF_OFF_MAX = K.dials.get("acute.STIM_REALISTIC.CAF_OFF_MAX"),
    INTOX_FULL_BAC = K.dials.get("acute.STIM_REALISTIC.INTOX_FULL_BAC"),
    HANG_H = K.dials.get("acute.STIM_REALISTIC.HANG_H"),
}
-- A key left out reads the realistic value.
K.acute.STIM_GAME_OVERRIDES = {
    MODE = 1, -- no row needed: the option's value
    CAF_OFF_MAX = K.dials.get("acute.STIM_GAME_OVERRIDES.CAF_OFF_MAX"),
    INTOX_FULL_BAC = K.dials.get("acute.STIM_GAME_OVERRIDES.INTOX_FULL_BAC"),
    HANG_H = K.dials.get("acute.STIM_GAME_OVERRIDES.HANG_H"),
}
K.acute.STIM = { {}, K.acute.STIM_REALISTIC }
for name, v in pairs(K.acute.STIM_REALISTIC) do
    K.acute.STIM[1][name] = v
end
for name, v in pairs(K.acute.STIM_GAME_OVERRIDES) do
    K.acute.STIM[1][name] = v
end
K.acute.C = K.acute.STIM[1]

-- Anything but 2 reads Game, the default.
function K.acute.useStimulants(mode)
    local set = K.acute.STIM[mode]
    if set == nil then
        set = K.acute.STIM[1]
    end
    K.acute.C = set
    return set
end

-- {BAC %, IU}: the unit at the third knot's BAC (S0893), the driving bands (S0905).
K.acute.IU_ALC_KNOTS = {
    { 0, 0 }, -- sober
    { K.dials.get("acute.IU_ALC_KNOTS.2.1"), K.dials.get("acute.IU_ALC_KNOTS.2.2") },
    { K.dials.get("acute.IU_ALC_KNOTS.3.1"), 1.00 }, -- the impairment unit itself, 1 by definition: no row needed
    { K.dials.get("acute.IU_ALC_KNOTS.4.1"), K.dials.get("acute.IU_ALC_KNOTS.4.2") },
}
K.acute.IU_ALC_CAP = K.dials.get("acute.IU_ALC_CAP")

K.acute.GLYC_REF = K.dials.get("acute.GLYC_REF")
K.acute.GLYC_HIGH = K.dials.get("acute.GLYC_HIGH")
K.acute.GLYC_LOW = K.dials.get("acute.GLYC_LOW")
K.acute.GLYC_PIVOT = K.dials.get("acute.GLYC_PIVOT")
K.acute.GLYC_SPAN = K.dials.get("acute.GLYC_SPAN")
K.acute.GLYC_TAU_H = K.dials.get("acute.GLYC_TAU_H")
K.acute.GLYC_MAX = K.dials.get("acute.GLYC_MAX")
K.acute.USE_WORK = K.dials.get("acute.USE_WORK")
K.acute.USE_MET_LO = K.dials.get("acute.USE_MET_LO")
K.acute.USE_MET_SPAN = K.dials.get("acute.USE_MET_SPAN")
K.acute.USE_MAX = K.dials.get("acute.USE_MAX")
K.acute.USE_SHIVER = K.dials.get("acute.USE_SHIVER")
K.acute.SHIVER_FULL = K.dials.get("acute.SHIVER_FULL")
K.acute.SHIVER_DEADBAND = K.dials.get("acute.SHIVER_DEADBAND")

K.acute.BG_NORMAL = K.dials.get("acute.BG_NORMAL")
K.acute.BG_EXERTION = K.dials.get("acute.BG_EXERTION")
K.acute.BG_EX_G = K.dials.get("acute.BG_EX_G")
K.acute.BG_EX_MET = K.dials.get("acute.BG_EX_MET")
K.acute.BG_ALC_FAST = K.dials.get("acute.BG_ALC_FAST")
K.acute.BG_ALC_FAST_H = K.dials.get("acute.BG_ALC_FAST_H")
K.acute.BG_TAU_CHO_H = K.dials.get("acute.BG_TAU_CHO_H")
K.acute.BG_TAU_H = K.dials.get("acute.BG_TAU_H")
K.acute.BG_MIN = K.dials.get("acute.BG_MIN")
K.acute.BG_MAX = K.dials.get("acute.BG_MAX")
K.acute.IU_BG_HI = K.dials.get("acute.IU_BG_HI")
K.acute.IU_BG_LO = K.dials.get("acute.IU_BG_LO")
K.acute.IU_BG_MAX = K.dials.get("acute.IU_BG_MAX")

K.acute.SLEEP_NEED_H = K.dials.get("acute.SLEEP_NEED_H")
K.acute.CHI_W = K.dials.get("acute.CHI_W")
K.acute.CHI_S = K.dials.get("acute.CHI_S")
K.acute.CHI_W_DEBT = K.dials.get("acute.CHI_W_DEBT")
K.acute.CHI_W_DEBT_MAX = K.dials.get("acute.CHI_W_DEBT_MAX")
K.acute.S_FLOOR_DEBT = K.dials.get("acute.S_FLOOR_DEBT")
K.acute.S_FLOOR_MAX = K.dials.get("acute.S_FLOOR_MAX")
K.acute.S_RESTED = K.dials.get("acute.S_RESTED")
K.acute.NAP_MIN_H = K.dials.get("acute.NAP_MIN_H")
K.acute.BOUT_GAP_H = K.dials.get("acute.BOUT_GAP_H")
K.acute.WINDOW_H = K.dials.get("acute.WINDOW_H")
K.acute.DEBT_MAX = K.dials.get("acute.DEBT_MAX")
K.acute.REPAY = K.dials.get("acute.REPAY")
K.acute.CIRC_AMP = K.dials.get("acute.CIRC_AMP")
K.acute.CIRC_PEAK_H = K.dials.get("acute.CIRC_PEAK_H")
-- +CIRC_AMP at CIRC_PEAK_H, the sleep-propensity peak; the fatigue term ADDS circ.
K.acute.IU_SLEEP_ZERO_H = K.dials.get("acute.IU_SLEEP_ZERO_H")
K.acute.IU_SLEEP_SPAN_H = K.dials.get("acute.IU_SLEEP_SPAN_H")
K.acute.IU_SLEEP_DEBT_H = K.dials.get("acute.IU_SLEEP_DEBT_H")
K.acute.IU_SLEEP_MAX = K.dials.get("acute.IU_SLEEP_MAX")
K.acute.VIG_WINDOW_H = K.dials.get("acute.VIG_WINDOW_H")

-- Exponential sums decaying on their time constant.
K.acute.EX_TAU_H = K.dials.get("acute.EX_TAU_H")
K.acute.COLD_ON = K.dials.get("acute.COLD_ON")
K.acute.COLD_TAU_H = K.dials.get("acute.COLD_TAU_H")
K.acute.RET_TAU_D = K.dials.get("acute.RET_TAU_D")

K.acute.IU_DEHYD_FROM = K.dials.get("acute.IU_DEHYD_FROM")
K.acute.IU_DEHYD_KNEE = K.dials.get("acute.IU_DEHYD_KNEE")
K.acute.IU_DEHYD_SLOPE1 = K.dials.get("acute.IU_DEHYD_SLOPE1")
K.acute.IU_DEHYD_SLOPE2 = K.dials.get("acute.IU_DEHYD_SLOPE2")
K.acute.IU_DEHYD_MAX = K.dials.get("acute.IU_DEHYD_MAX")
K.acute.IU_IRON = {
    0, -- replete
    0, -- marginal
    K.dials.get("acute.IU_IRON.3"),
    K.dials.get("acute.IU_IRON.4"),
}
K.acute.CREDIT_BASE = K.dials.get("acute.CREDIT_BASE")
K.acute.CREDIT_GAIN = K.dials.get("acute.CREDIT_GAIN")
K.acute.CREDIT_MG = K.dials.get("acute.CREDIT_MG")
K.acute.CREDIT_BASE_MG = K.dials.get("acute.CREDIT_BASE_MG")
K.acute.IU_MAX = K.dials.get("acute.IU_MAX")

K.acute.LOW_KCAL_KG = K.dials.get("acute.LOW_KCAL_KG")
K.acute.MASS_WINDOW_H = K.dials.get("acute.MASS_WINDOW_H")
K.acute.RISK_BMI_HIGH = K.dials.get("acute.RISK_BMI_HIGH")
K.acute.RISK_LOSS_HIGH = K.dials.get("acute.RISK_LOSS_HIGH")
K.acute.RISK_DAYS_HIGH = K.dials.get("acute.RISK_DAYS_HIGH")
K.acute.RISK_BMI_MOD = K.dials.get("acute.RISK_BMI_MOD")
K.acute.RISK_LOSS_MOD = K.dials.get("acute.RISK_LOSS_MOD")
K.acute.RISK_DAYS_MOD = K.dials.get("acute.RISK_DAYS_MOD")
K.acute.REFEED_DAYS = K.dials.get("acute.REFEED_DAYS")
K.acute.RESTART_KCAL_KG = K.dials.get("acute.RESTART_KCAL_KG")
K.acute.RESTART_LOW_KCAL_KG = K.dials.get("acute.RESTART_LOW_KCAL_KG")
K.acute.RESTART_LOW_BMI = K.dials.get("acute.RESTART_LOW_BMI")
K.acute.REFEED_P = K.dials.get("acute.REFEED_P")

-- bmi is 0 until the first refeedDay close; lastVigAgeH lies far in the past.
function K.acute.new(ageH)
    return {
        gutAlc = 0,
        gutCaf = 0,
        caf = 0,
        cafMean = 0,
        cafTol = 0,
        cafLowH = 0,
        wd = 0,
        slowMet = false,
        alc = 0,
        bac = 0,
        alcPeak = 0,
        hangH = 0,
        hang = 0,
        glyc = K.acute.GLYC_REF,
        g = 1,
        bg = K.acute.BG_NORMAL,
        awakeH = 0,
        debtH = 0,
        sleptH = 0,
        boutH = 0,
        gapH = 0,
        winStartH = ageH,
        winSleptH = 0,
        S = K.acute.S_RESTED,
        circ = 0,
        frozen = false,
        starvedDays = 0,
        lowDay = false,
        mass90max = 0,
        mass90ageH = ageH,
        bmi = 0,
        refeedRisk = 0,
        refeedDayN = -1,
        refeedEvent = false,
        iu = 0,
        exEma = 0,
        lastVigAgeH = -1e9,
        boutVig = false,
        coldH = 0,
        retEma = 0,
        iuSleep = 0,
    }
end

-- The adapter passes a uniform roll in [0, 1) once per character.
function K.acute.drawSlowMet(roll)
    return roll < K.acute.CAF_SLOW_SHARE
end

-- Returns the ethanol and the caffeine absorbed (the caffeine at CAF_ABSORB); neither key enters the stomach.
function K.acute.absorbGut(a, dtH)
    local f = 1 - math.exp(-0.6931471805599453 * dtH / K.acute.GUT_T_HALF)
    local alc = a.gutAlc * f
    local caf = a.gutCaf * f
    a.gutAlc = a.gutAlc - alc
    a.gutCaf = a.gutCaf - caf
    return alc, caf * K.acute.CAF_ABSORB
end

-- The rate EMA is written without the division, so a dose-only step (dtH 0) adds dose / 7. Withdrawal hours accrue
-- while tolerant and the load is under CAF_WD_LOW_MG; wd is 0 outside the episode. w is accepted for the call shape.
function K.acute.caffeine(a, doseAbsMg, w, dtH)
    local A = K.acute
    local thalf = A.CAF_THALF_H
    if a.slowMet then
        thalf = A.CAF_THALF_SLOW_H
    end
    a.caf = a.caf * math.exp(-math.log(2) * dtH / thalf) + doseAbsMg
    -- floored at 0: a step longer than CAF_MEAN_H would otherwise drive the mean negative
    a.cafMean = K.max(0, a.cafMean + (doseAbsMg * 24 - a.cafMean * dtH) / A.CAF_MEAN_H)
    local tStar = K.clamp(a.cafMean / A.CAF_TOL_REF, 0, 1)
    a.cafTol = tStar + (a.cafTol - tStar) * math.exp(-dtH / A.CAF_TOL_TAU_H)
    if a.cafTol > A.CAF_WD_TOL and a.caf < A.CAF_WD_LOW_MG then
        a.cafLowH = a.cafLowH + dtH
    else
        a.cafLowH = 0
    end
    local h = a.cafLowH
    if h <= A.CAF_WD_ONSET_H or h >= A.CAF_WD_END_H then
        a.wd = 0
    elseif h <= A.CAF_WD_PEAK_H then
        a.wd = (h - A.CAF_WD_ONSET_H) / (A.CAF_WD_PEAK_H - A.CAF_WD_ONSET_H)
    else
        a.wd = (A.CAF_WD_END_H - h) / (A.CAF_WD_END_H - A.CAF_WD_PEAK_H)
    end
    return a
end

-- S0626.
function K.acute.caffeineActive(a, w)
    return a.caf >= K.acute.CAF_EFFECT_MGKG * w
end

-- Widmark zero-order elimination; a peak of at least HANG_PEAK starts the hangover when BAC returns to 0, a smaller
-- one clears. Drinking again during a hangover starts a fresh episode (a game choice).
function K.acute.alcohol(a, ethanolAbsG, w, sex, dtH)
    local A = K.acute
    local r = A.WIDMARK_R[sex]
    a.alc = K.max(0, a.alc + ethanolAbsG - A.BETA * r * w * 10 * dtH)
    a.bac = a.alc / (10 * r * w)
    if a.bac > 0 then
        if a.hang == 1 then
            a.hang = 0
            a.hangH = 0
            a.alcPeak = 0
        end
        a.alcPeak = K.max(a.alcPeak, a.bac)
    elseif a.hang == 1 then
        a.hangH = a.hangH - dtH
        if a.hangH <= 0 then
            a.hang = 0
            a.hangH = 0
            a.alcPeak = 0
        end
    elseif a.alcPeak >= A.HANG_PEAK then
        a.hang = 1
        a.hangH = A.C.HANG_H * a.alcPeak / A.HANG_PEAK
    else
        a.alcPeak = 0
    end
    return a
end

-- The last segment extended above the last knot and capped at IU_ALC_CAP.
function K.acute.iuAlcohol(bac)
    if bac <= 0 then
        return 0
    end
    return K.min(K.interp(K.acute.IU_ALC_KNOTS, bac, true), K.acute.IU_ALC_CAP)
end

-- cho24 in g/kg/day (S0680 anchors).
function K.acute.glycTarget(cho24)
    local A = K.acute
    local hi = K.clamp((cho24 - A.GLYC_PIVOT) / A.GLYC_SPAN, 0, 1)
    local lo = K.clamp((A.GLYC_PIVOT - cho24) / A.GLYC_SPAN, 0, 1)
    return A.GLYC_REF + A.GLYC_HIGH * hi - A.GLYC_LOW * lo
end

-- Work and shivering draw above their floors; at rest (met < USE_MET_LO, S0683) the store also refills toward the
-- carbohydrate target, so a working step never refills and a cold resting one refills less.
-- USE_MET_LO stays above the thermoregulator's idle met (1.007-1.010 indoors), or a resting store never refills (#2984).
function K.acute.glycogen(a, met, coldMult, cho24, dtH)
    local A = K.acute
    local work = A.USE_WORK * K.clamp((met - A.USE_MET_LO) / A.USE_MET_SPAN, 0, A.USE_MAX)
    local shiver = A.USE_SHIVER * K.clamp((coldMult - A.SHIVER_DEADBAND) / (A.SHIVER_FULL - A.SHIVER_DEADBAND), 0, 1)
    local use = work + shiver
    a.glyc = a.glyc - use * dtH
    if met < A.USE_MET_LO then
        local target = A.glycTarget(cho24)
        a.glyc = target + (a.glyc - target) * math.exp(-dtH / A.GLYC_TAU_H)
    end
    a.glyc = K.clamp(a.glyc, 0, A.GLYC_MAX)
    a.g = A.glycG(a)
    return a
end

-- Also the load's recompute of g from the stored glyc.
function K.acute.glycG(a)
    return K.clamp(a.glyc / K.acute.GLYC_REF, 0, 1)
end

-- Absorbed carbohydrate restores toward BG_NORMAL; otherwise BG_EXERTION under exertion with low glycogen, BG_ALC_FAST
-- with alcohol after a long empty stomach, else BG_NORMAL: no fall from fasting alone (S0896).
function K.acute.glucose(a, met, choAbsG, bac, stomachEmptyH, dtH)
    local A = K.acute
    local target = A.BG_NORMAL
    local tau = A.BG_TAU_H
    if choAbsG > 0 then
        tau = A.BG_TAU_CHO_H
    elseif a.g < A.BG_EX_G and met >= A.BG_EX_MET then
        target = A.BG_EXERTION
    elseif bac > 0 and stomachEmptyH > A.BG_ALC_FAST_H then
        target = A.BG_ALC_FAST
    end
    a.bg = target + (a.bg - target) * math.exp(-dtH / tau)
    a.bg = K.clamp(a.bg, A.BG_MIN, A.BG_MAX)
    return a
end

-- 0 at or above IU_BG_HI, linear to IU_BG_MAX at IU_BG_LO, held below.
function K.acute.iuGlucose(bg)
    local A = K.acute
    local x = K.clamp((A.IU_BG_HI - bg) / (A.IU_BG_HI - A.IU_BG_LO), 0, 1)
    return A.IU_BG_MAX * x
end

-- mAcc nil reads 1.
function K.acute.chiW(debtH, mAcc)
    local m = mAcc or 1
    return K.acute.CHI_W / (m * (1 + K.acute.CHI_W_DEBT * K.min(debtH, K.acute.CHI_W_DEBT_MAX)))
end

-- rRec nil reads 1.
function K.acute.chiS(rRec)
    local r = rRec or 1
    return K.acute.CHI_S / r
end

-- The body clock record.acute.bodyHour, read by the hunger factor, circ and the carry's morning halving in place of the
-- world hour. It runs only while sleep is on; with sleep off there is no rhythm (a game choice). It advances by online
-- hours, so it freezes offline (K.resume.KEPT), and a main sleep's close sets it to WAKE_H plus the gap since.
K.circadian = {}
K.circadian.WAKE_H = K.dials.get("circadian.WAKE_H")
K.circadian.MAIN_SLEEP_H = K.dials.get("circadian.MAIN_SLEEP_H")
K.circadian.SUM_TOL_H = K.dials.get("circadian.SUM_TOL_H")

function K.circadian.wrap(h)
    return h - math.floor(h / 24) * 24
end

-- A worldHour that is not finite seeds nothing: the clock stays off and the next step seeds it.
function K.circadian.step(a, sleepOn, worldHour, dtH)
    if not sleepOn then
        a.bodyOn = false
        return a
    end
    local h = a.bodyHour
    if a.bodyOn == true and K.finite(h) then
        a.bodyHour = K.circadian.wrap(h + dtH)
        return a
    end
    if not K.finite(worldHour) then
        a.bodyOn = false
        return a
    end
    a.bodyHour = K.circadian.wrap(worldHour)
    a.bodyOn = true
    return a
end

-- sinceH is the bout's awake gap at its close.
function K.circadian.wake(a, sinceH)
    a.bodyHour = K.circadian.wrap(K.circadian.WAKE_H + sinceH)
    return a
end

-- nil (no rhythm) unless sleepOn and the clock runs on a finite phase.
function K.circadian.hour(record, sleepOn)
    if not sleepOn or type(record) ~= "table" then
        return nil
    end
    local a = record.acute
    if type(a) ~= "table" or a.bodyOn ~= true then
        return nil
    end
    local h = a.bodyHour
    if K.finite(h) then
        return h
    end
    return nil
end

-- 0 when hourOfDay is nil (no rhythm).
function K.acute.circ(hourOfDay)
    if hourOfDay == nil then
        return 0
    end
    return K.acute.CIRC_AMP * math.cos(2 * math.pi * (hourOfDay - K.acute.CIRC_PEAK_H) / 24)
end

-- sleepDisabled (SleepAllowed and SleepNeeded not both true) freezes the state at rested and restarts the window at
-- ageH, so a later re-enable opens a fresh one. A sleep bout tolerates awake gaps under BOUT_GAP_H (the harness hold's
-- isAsleep misses, #2840); a bout that reached NAP_MIN_H credits a closing gap to hours awake. sleptH, the unbroken
-- run, is 0 after any awake step; the reset reads the bout. A closing window books the shortfall against need x
-- needFactor as debt and repays REPAY of any excess. A bout of at least MAIN_SLEEP_H booked hours is a main sleep and
-- wakes the body clock; a nap or an accelerated-sleep mod's few-minute bout leaves it.
function K.acute.sleepMinute(a, asleep, hourOfDay, needFactor, ageH, dtH, sleepDisabled, mAcc, rRec)
    local A = K.acute
    if sleepDisabled then
        a.circ = A.circ(hourOfDay)
        a.frozen = true
        a.awakeH = 0
        a.debtH = 0
        a.sleptH = 0
        a.boutH = 0
        a.gapH = 0
        a.winSleptH = 0
        a.winStartH = ageH
        a.S = A.S_RESTED
        return a
    end
    a.frozen = false
    if asleep then
        if a.boutH == 0 then
            a.boutVig = ageH - a.lastVigAgeH <= A.VIG_WINDOW_H
        end
        a.sleptH = a.sleptH + dtH
        a.boutH = a.boutH + dtH
        a.gapH = 0
        a.winSleptH = a.winSleptH + dtH
        if a.boutH >= A.NAP_MIN_H then
            a.awakeH = 0
        end
        local floor = K.min(A.S_FLOOR_DEBT * a.debtH, A.S_FLOOR_MAX)
        a.S = K.max(a.S * math.exp(-dtH / A.chiS(rRec)), floor)
    else
        a.sleptH = 0
        if a.boutH > 0 then
            a.gapH = a.gapH + dtH
            if a.gapH >= A.BOUT_GAP_H then
                if a.boutH >= A.NAP_MIN_H then
                    a.awakeH = a.gapH - dtH -- the gap before this step; this step accrues below
                end
                if a.boutH + K.circadian.SUM_TOL_H >= K.circadian.MAIN_SLEEP_H then
                    K.circadian.wake(a, a.gapH)
                    if hourOfDay ~= nil then
                        hourOfDay = a.bodyHour
                    end
                end
                a.boutH = 0
                a.gapH = 0
            end
        end
        if a.boutH < A.NAP_MIN_H then
            a.awakeH = a.awakeH + dtH
        end
        a.S = 1 - (1 - a.S) * math.exp(-dtH / A.chiW(a.debtH, mAcc))
    end
    a.circ = A.circ(hourOfDay)
    -- every elapsed window closes (a long step can span several); a window books at most its own WINDOW_H
    while ageH - a.winStartH >= A.WINDOW_H do
        local need = A.SLEEP_NEED_H * needFactor
        local booked = K.min(a.winSleptH, A.WINDOW_H)
        local short = K.max(0, need - booked)
        local extra = K.max(0, booked - need)
        a.debtH = K.clamp(a.debtH + short - A.REPAY * extra, 0, A.DEBT_MAX)
        a.winStartH = a.winStartH + A.WINDOW_H
        a.winSleptH = 0
    end
    return a
end

-- 1 IU_SLEEP_SPAN_H after IU_SLEEP_ZERO_H awake (S0892), plus the debt term, capped.
function K.acute.iuSleep(a)
    local A = K.acute
    local awake = K.clamp((a.awakeH - A.IU_SLEEP_ZERO_H) / A.IU_SLEEP_SPAN_H, 0, A.IU_SLEEP_MAX)
    return K.min(A.IU_SLEEP_MAX, awake + a.debtH / A.IU_SLEEP_DEBT_H)
end

-- Two slopes either side of IU_DEHYD_KNEE, capped at IU_DEHYD_MAX.
function K.acute.iuDehyd(dehydPct)
    local A = K.acute
    if dehydPct < A.IU_DEHYD_FROM then
        return 0
    end
    if dehydPct <= A.IU_DEHYD_KNEE then
        return A.IU_DEHYD_SLOPE1 * (dehydPct - A.IU_DEHYD_FROM)
    end
    local y = A.IU_DEHYD_SLOPE1 * (A.IU_DEHYD_KNEE - A.IU_DEHYD_FROM) + A.IU_DEHYD_SLOPE2 * (dehydPct - A.IU_DEHYD_KNEE)
    return K.min(y, A.IU_DEHYD_MAX)
end

-- 1 IU = 24 h awake = BAC 0.05 %. Additive, less the caffeine credit (never above IU_sleep); writes a.iu and a.iuSleep.
function K.acute.iu(a, dehydPct, ironGrade)
    local A = K.acute
    local sleep = A.iuSleep(a)
    a.iuSleep = sleep
    local credit = K.min(sleep, A.CREDIT_BASE * K.min(1, a.caf / A.CREDIT_BASE_MG) + A.CREDIT_GAIN * K.min(1, a.caf / A.CREDIT_MG))
    local sum = sleep + A.iuAlcohol(a.bac) + A.iuDehyd(dehydPct) + A.iuGlucose(a.bg) + A.IU_IRON[ironGrade]
    a.iu = K.clamp(sum - credit, 0, A.IU_MAX)
    return a.iu
end

-- A band-2 step stamps lastVigAgeH, which sleepMinute's vigorous latch reads.
function K.acute.exerciseMinute(a, band, ageH, dtH)
    local A = K.acute
    local add = 0
    if band >= 1 then
        add = dtH * 60
    end
    a.exEma = a.exEma * math.exp(-dtH / A.EX_TAU_H) + add
    if band == 2 then
        a.lastVigAgeH = ageH
    end
    return a
end

-- Cold is coldMult above COLD_ON.
function K.acute.coldMinute(a, coldMult, dtH)
    local A = K.acute
    local add = 0
    if coldMult > A.COLD_ON then
        add = dtH
    end
    a.coldH = a.coldH * math.exp(-dtH / A.COLD_TAU_H) + add
    return a
end

-- The exact step for a rate held over the step, so any step length agrees; dtD <= 0 changes nothing.
function K.acute.retinolMinute(a, ingestedUg, dtD)
    if dtD <= 0 then
        return a
    end
    local perDay = ingestedUg / dtD
    a.retEma = a.retEma + (perDay - a.retEma) * (1 - math.exp(-dtD / K.acute.RET_TAU_D))
    return a
end

-- The window opens on a normal day after a low day while the risk is high (a game choice, so a thin but fed character
-- does not cycle windows). A first, partial day is never low, so a new character does not start a day starved.
-- starvedDays counts days of little or no intake (S0115 as written), not the drain's unfed hours, which a nibble
-- resets: the two can differ by a day at a fast's start.
function K.acute.refeedDay(a, kcalPerKg, w, ageH, kDepleted, mgDepleted, alcoholHistory, partial)
    local A = K.acute
    local low = kcalPerKg < A.LOW_KCAL_KG and partial ~= true
    if not low and a.lowDay and a.refeedRisk == 2 and a.refeedDayN < 0 then
        a.refeedDayN = 0
    end
    if low then
        a.starvedDays = a.starvedDays + 1
    else
        a.starvedDays = 0
    end
    a.lowDay = low
    if w > a.mass90max or ageH - a.mass90ageH > A.MASS_WINDOW_H then
        a.mass90max = w
        a.mass90ageH = ageH
    end
    local loss90 = (a.mass90max - w) / a.mass90max
    a.bmi = w / (K.HEIGHT_M * K.HEIGHT_M)
    if a.refeedDayN >= 0 then
        return a
    end
    if a.bmi < A.RISK_BMI_HIGH or loss90 > A.RISK_LOSS_HIGH or a.starvedDays > A.RISK_DAYS_HIGH or kDepleted or mgDepleted then
        a.refeedRisk = 2
        return a
    end
    local n = 0
    if a.bmi < A.RISK_BMI_MOD then
        n = n + 1
    end
    if loss90 > A.RISK_LOSS_MOD then
        n = n + 1
    end
    if a.starvedDays > A.RISK_DAYS_MOD then
        n = n + 1
    end
    if alcoholHistory then
        n = n + 1
    end
    a.refeedRisk = K.min(n, 2)
    return a
end

-- Inside the first REFEED_DAYS days an intake above the restart limit (S0116) rolls the event at REFEED_P.
function K.acute.refeedEvent(a, kcalPerKg, roll)
    local A = K.acute
    local event = false
    if a.refeedDayN >= 0 and a.refeedDayN < A.REFEED_DAYS then
        a.refeedDayN = a.refeedDayN + 1
        local limit = A.RESTART_KCAL_KG
        if a.bmi <= A.RESTART_LOW_BMI then
            limit = A.RESTART_LOW_KCAL_KG
        end
        event = kcalPerKg > limit and roll < A.REFEED_P
    elseif a.refeedDayN >= A.REFEED_DAYS then
        a.refeedDayN = -1
    end
    a.refeedEvent = event
    return event
end
