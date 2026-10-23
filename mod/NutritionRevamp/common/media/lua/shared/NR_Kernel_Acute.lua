-- NR_Kernel_Acute.lua -- the acute states: caffeine (body load, the 7-day mean,
-- tolerance, withdrawal), alcohol (the Widmark load and blood alcohol, the hangover), muscle glycogen and
-- blood glucose, the sleep state (hours awake, the 24 h window's debt, the homeostatic S, the circadian
-- term, the freeze when the server disables sleep), the impairment unit and the refeeding risk state.
-- The model is the formulas briefing's sections C, D, E, F and G as the Task 9 amendments fix them.
-- Time: every dtH and ageH is GAME hours (ageH the world age, Plan 3's clock). Ruling T5-1 (run x151s):
-- a held sleep with sleep allowed runs the world clock about 20x, so a fast-forwarded sleep arrives as
-- many game minutes asleep and is simply a long sleep. Sex is indexed 1 male, 2 female (Plan 3's K.body
-- convention). The first-order relaxations (the caffeine tolerance, glycogen repletion, blood glucose and
-- the homeostatic S) use the exact exponential step x = target + (x - target) * exp(-dtH / tau), a
-- refinement of the briefing's Euler forms on Task 6's zero-order-hold precedent: the result is the same
-- at any step length, so a one-minute step and a long catch-up step agree (per-minute Euler differs from
-- it by under 2e-5 over a week). Pure: numbers and Lua tables in, numbers and Lua tables out, no Java.
-- Slow-clock code with no fast region. This file sorts after NR_Kernel.lua, and every K.clamp / K.min /
-- K.max reference is at call time.
-- The x151r fix wave (rulings T17-2..T17-4): caffeine and ethanol absorb from a gut lane (gutAlc, gutCaf;
-- absorbGut) the intake landing feeds directly, bypassing the stomach's two-lane drain (K.stomach.drain)
-- (one beer built no blood alcohol through the stomach, #2983); the shiver draw starts above a dead band
-- and glycogen refills whenever met < 3 (the thermoregulator's idle 1.007-1.010 indoors blocked every
-- refill, #2984); a sleep bout (boutH, gapH) tolerates awake gaps under BOUT_GAP_H (the harness hold's
-- isAsleep misses, #2840, never let a run reach the nap threshold, #2986).
-- sleepMinute takes the accrual and recovery multipliers
-- mAcc and rRec (nil reads 1, the Plan 4 behaviour) on chi_w and chi_s; three exponential memories join the
-- state -- exEma (exercise minutes, exerciseMinute), coldH (cold hours, coldMinute), retEma (ingested
-- retinol ug/day, retinolMinute) -- with lastVigAgeH (the last band-2 minute) and boutVig (latched at a
-- bout's first asleep minute); iu stores its sleep term on iuSleep; the glucose knee moves to 3.0-2.6 mmol/L.
local K = NutritionRevamp.kernel
K.acute = {}

-- Caffeine.
-- Absorption fraction of the gut lane, applied once in K.acute.absorbGut; alcohol and
-- caffeine take the dose absorbGut releases, so nothing re-applies it.
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

-- The gut lane caffeine and ethanol absorb from: first order on this half-time, game hours.
K.acute.GUT_T_HALF = K.dials.get("acute.GUT_T_HALF")

-- Alcohol.
-- The Widmark distribution factor, indexed by sex.
K.acute.WIDMARK_R = {
    K.dials.get("acute.WIDMARK_R.1"),
    K.dials.get("acute.WIDMARK_R.2"),
}
K.acute.BETA = K.dials.get("acute.BETA")
K.acute.HANG_PEAK = K.dials.get("acute.HANG_PEAK")

-- The stimulant sizes (Plan 15 Task 10, spec section 5): NR.StimulantRealism (1 Game, the default; 2 Realistic)
-- selects the active set K.acute.C once, when the server's options read sees the value change
-- (K.acute.useStimulants), never per call; K.effects.fOff, K.effects.intoxTarget and K.acute.alcohol read C. Realistic
-- is the pharmacological strengths the mod shipped through Plan 14. Game overrides sizes only -- a cup's fatigue
-- offset, the intoxication per drink and the hangover's tail -- so every timing stays the science of both sets:
-- caffeine absorption, clearance, tolerance and withdrawal; alcohol absorption, the Widmark clearance and the
-- hangover's start at clearance. The hangover's effect sizes are the effects table's two hang rows, tagged stim 1 and
-- 2 (NR_Data_Effects.lua).
K.acute.STIM_REALISTIC = {
    MODE = 2, -- no row needed: the option's value
    CAF_OFF_MAX = K.dials.get("acute.STIM_REALISTIC.CAF_OFF_MAX"),
    INTOX_FULL_BAC = K.dials.get("acute.STIM_REALISTIC.INTOX_FULL_BAC"),
    HANG_H = K.dials.get("acute.STIM_REALISTIC.HANG_H"),
}
-- The Game overrides, keyed by constant name; a key left out reads the realistic value.
K.acute.STIM_GAME_OVERRIDES = {
    MODE = 1, -- no row needed: the option's value
    CAF_OFF_MAX = K.dials.get("acute.STIM_GAME_OVERRIDES.CAF_OFF_MAX"),
    INTOX_FULL_BAC = K.dials.get("acute.STIM_GAME_OVERRIDES.INTOX_FULL_BAC"),
    HANG_H = K.dials.get("acute.STIM_GAME_OVERRIDES.HANG_H"),
}
-- The two sets by option value: Game is the realistic set with the overrides laid over it.
K.acute.STIM = { {}, K.acute.STIM_REALISTIC }
for name, v in pairs(K.acute.STIM_REALISTIC) do
    K.acute.STIM[1][name] = v
end
for name, v in pairs(K.acute.STIM_GAME_OVERRIDES) do
    K.acute.STIM[1][name] = v
end
K.acute.C = K.acute.STIM[1]

-- Select the active stimulant set for the option value mode (1 Game, 2 Realistic; anything else reads Game, the
-- default). Returns the set.
function K.acute.useStimulants(mode)
    local set = K.acute.STIM[mode]
    if set == nil then
        set = K.acute.STIM[1]
    end
    K.acute.C = set
    return set
end

-- The alcohol impairment knots {BAC %, IU}: the unit at the third knot's BAC (0.05 %, S0893), the driving bands (S0905).
K.acute.IU_ALC_KNOTS = {
    { 0, 0 }, -- sober
    { K.dials.get("acute.IU_ALC_KNOTS.2.1"), K.dials.get("acute.IU_ALC_KNOTS.2.2") },
    { K.dials.get("acute.IU_ALC_KNOTS.3.1"), 1.00 }, -- the impairment unit itself, 1 by definition: no row needed
    { K.dials.get("acute.IU_ALC_KNOTS.4.1"), K.dials.get("acute.IU_ALC_KNOTS.4.2") },
}
K.acute.IU_ALC_CAP = K.dials.get("acute.IU_ALC_CAP")

-- Glycogen, mmol glucosyl per kg dry muscle.
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

-- Blood glucose, mmol/L.
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

-- Sleep, game hours.
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
-- Sign: +CIRC_AMP (0.12) at CIRC_PEAK_H (04:00) = the sleep-propensity peak (the alertness trough); Plan 5's FATIGUE term ADDS circ.
K.acute.IU_SLEEP_ZERO_H = K.dials.get("acute.IU_SLEEP_ZERO_H")
K.acute.IU_SLEEP_SPAN_H = K.dials.get("acute.IU_SLEEP_SPAN_H")
K.acute.IU_SLEEP_DEBT_H = K.dials.get("acute.IU_SLEEP_DEBT_H")
K.acute.IU_SLEEP_MAX = K.dials.get("acute.IU_SLEEP_MAX")
K.acute.VIG_WINDOW_H = K.dials.get("acute.VIG_WINDOW_H")

-- The Plan 5 memories: exponential sums decaying on their time constant.
K.acute.EX_TAU_H = K.dials.get("acute.EX_TAU_H")
K.acute.COLD_ON = K.dials.get("acute.COLD_ON")
K.acute.COLD_TAU_H = K.dials.get("acute.COLD_TAU_H")
K.acute.RET_TAU_D = K.dials.get("acute.RET_TAU_D")

-- The impairment unit.
K.acute.IU_DEHYD_FROM = K.dials.get("acute.IU_DEHYD_FROM")
K.acute.IU_DEHYD_KNEE = K.dials.get("acute.IU_DEHYD_KNEE")
K.acute.IU_DEHYD_SLOPE1 = K.dials.get("acute.IU_DEHYD_SLOPE1")
K.acute.IU_DEHYD_SLOPE2 = K.dials.get("acute.IU_DEHYD_SLOPE2")
K.acute.IU_DEHYD_MAX = K.dials.get("acute.IU_DEHYD_MAX")
-- The iron term by grade 1..4.
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

-- Refeeding.
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

-- A fresh record.acute at world age ageH: no caffeine or alcohol on board or in the gut, the reference
-- glycogen and normal glucose, rested, no debt or sleep bout, no refeeding risk. bmi 0 until the first
-- refeedDay close. The Plan 5 fields: no exercise, cold or retinol memory, no band-2 minute on record
-- (lastVigAgeH far in the past), no vigorous latch, no sleep term.
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

-- The slow-metaboliser draw: the adapter passes a uniform roll in [0, 1) once per character.
function K.acute.drawSlowMet(roll)
    return roll < K.acute.CAF_SLOW_SHARE
end

-- One gut-lane step over dtH hours: the fraction 1 - exp(-ln2 x dtH / GUT_T_HALF) of the
-- ethanol (g) and caffeine (mg) awaiting absorption moves out. Returns the ethanol and the caffeine
-- absorbed this step (the caffeine at CAF_ABSORB), the doses alcohol and caffeine then take. The intake
-- landing adds to gutAlc and gutCaf; neither key enters the stomach.
function K.acute.absorbGut(a, dtH)
    local f = 1 - math.exp(-0.6931471805599453 * dtH / K.acute.GUT_T_HALF)
    local alc = a.gutAlc * f
    local caf = a.gutCaf * f
    a.gutAlc = a.gutAlc - alc
    a.gutCaf = a.gutCaf - caf
    return alc, caf * K.acute.CAF_ABSORB
end

-- One caffeine step: the body load decays first-order and takes this step's absorbed dose (mg); the
-- daily-rate EMA takes the step's sample (dose x 24 / dtH mg/day) with alpha = dtH / CAF_MEAN_H (168 h), written without
-- the division so a dose-only step (dtH 0) adds dose / 7; tolerance relaxes toward clamp(mean / CAF_TOL_REF, 0, 1)
-- on CAF_TOL_TAU_H (7 d) both ways; withdrawal hours accrue while tolerant and the load is under CAF_WD_LOW_MG (10.7 mg). wd is the
-- withdrawal intensity 0..1 (0 outside the episode). w is accepted for the call shape.
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

-- Whether CAF_EFFECT_MGKG (3 mg/kg) is on board (S0626).
function K.acute.caffeineActive(a, w)
    return a.caf >= K.acute.CAF_EFFECT_MGKG * w
end

-- One alcohol step: the absorbed ethanol g lands, the Widmark zero-order elimination beta x r x w x 10
-- g/h drains it, BAC = load / (10 r w) per cent. The peak is tracked while BAC > 0; when BAC returns to 0
-- after a peak of at least HANG_PEAK (0.05 %) the hangover starts for C.HANG_H x peak/HANG_PEAK hours (the active stimulant set) and counts down; a
-- sub-threshold peak clears. Drinking again during a hangover ends it and starts a fresh episode at the
-- new BAC (game choice).
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

-- The alcohol term of the impairment unit: piecewise-linear over IU_ALC_KNOTS, the last segment extended
-- above the last knot (0.08 %) and capped at IU_ALC_CAP.
function K.acute.iuAlcohol(bac)
    if bac <= 0 then
        return 0
    end
    return K.min(K.interp(K.acute.IU_ALC_KNOTS, bac, true), K.acute.IU_ALC_CAP)
end

-- The glycogen target for a 24 h carbohydrate intake cho24 g/kg/day (S0680 anchors).
function K.acute.glycTarget(cho24)
    local A = K.acute
    local hi = K.clamp((cho24 - A.GLYC_PIVOT) / A.GLYC_SPAN, 0, 1)
    local lo = K.clamp((A.GLYC_PIVOT - cho24) / A.GLYC_SPAN, 0, 1)
    return A.GLYC_REF + A.GLYC_HIGH * hi - A.GLYC_LOW * lo
end

-- One glycogen step: the work draw (above USE_MET_LO, MET 3) and the shivering draw (above the coldMult dead band,
-- full at SHIVER_FULL, 3.5), mmol/kg/h; at rest (met < USE_MET_LO, the S0683 work floor) the store also relaxes toward the
-- carbohydrate target on GLYC_TAU_H (24 h), the refill and any shiver draw coexisting (a working
-- step never refills, a cold resting one refills less). Clamped to [0, GLYC_MAX]; g = clamp(G / GLYC_REF, 0, 1).
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

-- The glycogen state g read off the store: glyc over GLYC_REF clamped to [0, 1] (the glycogen step's own
-- write, and the load's recompute of it from the stored glyc).
function K.acute.glycG(a)
    return K.clamp(a.glyc / K.acute.GLYC_REF, 0, 1)
end

-- One blood-glucose step: carbohydrate absorbed this step (choAbsG > 0) restores toward BG_NORMAL (5.0) on BG_TAU_CHO_H (15 min);
-- otherwise the target is BG_EXERTION (2.5) under exertion with g < BG_EX_G (0.2; a.g, the glycogen step's), BG_ALC_FAST (3.0) with alcohol on
-- board after more than BG_ALC_FAST_H (12 h) of empty stomach, else BG_NORMAL (no fall from fasting alone, S0896), on BG_TAU_H (1 h).
-- Clamped to [BG_MIN, BG_MAX].
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

-- The glucose term of the impairment unit: 0 at or above IU_BG_HI (3.0 mmol/L), linear to IU_BG_MAX (0.90) at IU_BG_LO (2.6), held below
-- (the Plan 4 knee was 3.5-3.0).
function K.acute.iuGlucose(bg)
    local A = K.acute
    local x = K.clamp((A.IU_BG_HI - bg) / (A.IU_BG_HI - A.IU_BG_LO), 0, 1)
    return A.IU_BG_MAX * x
end

-- The effective build-up time constant, game hours: chi_w / (mAcc x (1 + CHI_W_DEBT x min(debtH, CHI_W_DEBT_MAX))),
-- mAcc 1 when nil.
function K.acute.chiW(debtH, mAcc)
    local m = mAcc or 1
    return K.acute.CHI_W / (m * (1 + K.acute.CHI_W_DEBT * K.min(debtH, K.acute.CHI_W_DEBT_MAX)))
end

-- The effective recovery time constant, game hours: chi_s / rRec, rRec 1 when nil.
function K.acute.chiS(rRec)
    local r = rRec or 1
    return K.acute.CHI_S / r
end

-- The body clock (Plan 16 spec section 2, Angus's design): record.acute.bodyHour, the character's own phase in hours of
-- the day (0-24), the hour the three daily-rhythm consumers read in place of the world clock's (the hunger factor,
-- K.satiety.circadian; the fatigue term circ, K.acute.circ; the carry morning halving, K.strength.eAcute). It runs
-- only while sleep is on (NR.sleepOn: SleepAllowed and SleepNeeded both true on a server): with sleep off there is
-- no rhythm (K.circadian.hour reads nil, so the hunger factor is 1, circ 0 and no halving; a game choice, spec
-- section 6). With sleep on it advances by each step's integrated online hours, so it freezes offline (the resume
-- leaves it, K.resume.KEPT); it is seeded at the world hour on a record that has none and on the first sleep-on step
-- after a sleep-off one (bodyOn, the setting the clock last ran under); a sleep-off step keeps the phase unused; and
-- the close of a main sleep (a bout of at least MAIN_SLEEP_H booked hours, K.acute.sleepMinute) sets it to WAKE_H
-- at the waking, plus the gap since (a game choice, spec section 6). Pure: no Java.
K.circadian = {}
K.circadian.WAKE_H = K.dials.get("circadian.WAKE_H")
K.circadian.MAIN_SLEEP_H = K.dials.get("circadian.MAIN_SLEEP_H")
K.circadian.SUM_TOL_H = K.dials.get("circadian.SUM_TOL_H")

-- An hour wrapped into [0, 24).
function K.circadian.wrap(h)
    return h - math.floor(h / 24) * 24
end

-- One body-clock step of dtH online game hours (a.bodyHour, a.bodyOn). sleepOn false marks the clock off and keeps
-- its phase; sleepOn true advances it by dtH, or seeds it at worldHour (the hour of the world clock this minute)
-- when it has no finite phase or last ran under sleep off. A worldHour that is not finite seeds nothing: the clock
-- stays off and the next step seeds it.
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

-- The close of a main sleep: the body woke at WAKE_H, sinceH game hours ago (the bout's awake gap at its close).
function K.circadian.wake(a, sinceH)
    a.bodyHour = K.circadian.wrap(K.circadian.WAKE_H + sinceH)
    return a
end

-- The hour the daily-rhythm consumers read: record.acute.bodyHour when sleepOn and the clock runs (bodyOn) on a
-- finite phase, else nil (no rhythm).
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

-- The circadian term of fatigue at body hour hourOfDay: CIRC_AMP x cos(2 pi (hourOfDay - CIRC_PEAK_H) / 24); 0 when
-- hourOfDay is nil (no rhythm).
function K.acute.circ(hourOfDay)
    if hourOfDay == nil then
        return 0
    end
    return K.acute.CIRC_AMP * math.cos(2 * math.pi * (hourOfDay - K.acute.CIRC_PEAK_H) / 24)
end

-- One sleep step over dtH game hours at world age ageH; hourOfDay is the body clock's hour (K.circadian.hour), nil
-- with no rhythm. sleepDisabled (the server's SleepAllowed and
-- SleepNeeded not both true, the reset ahead of the hook, run x151s) freezes the state at rested: hours
-- awake, debt, the sleep run and the window's sleep are 0, S is S_RESTED and the window restarts at ageH,
-- so a later re-enable opens a fresh window; frozen is set and circ is K.acute.circ(hourOfDay). Otherwise: asleep, the
-- run (sleptH), the bout (boutH) and the window's sleep accrue, the bout's gap clears, hours awake reset to 0
-- once the bout reaches NAP_MIN_H (at that minute) and otherwise hold, and S decays on chi_s to
-- a debt floor capped at S_FLOOR_MAX; awake, the run clears, a bout in progress counts its gap (gapH) and ends
-- when the gap reaches BOUT_GAP_H -- a bout that had reset hours awake then credits the whole gap to them, the
-- waking having begun at its start -- hours awake accrue unless a bout of at least NAP_MIN_H is in progress,
-- and S rises toward 1 on chi_w shortened by the debt. A gap under BOUT_GAP_H inside a bout is so tolerated
-- (the harness hold's isAsleep misses, #2840). sleptH, the unbroken run, is the record's one
-- asleep-this-minute signal (above 0 after an asleep step, 0 after an awake one), which the live experiments'
-- rings read (x30_sleep_lib); the reset reads the bout. The 24 h window closes when ageH has run WINDOW_H past
-- its start: the shortfall against need (7.5 h x needFactor, the trait multiplier) adds to the debt, the
-- excess repays REPAY of itself, clamped [0, DEBT_MAX].
-- mAcc divides chi_w (the accrual multiplier) and rRec divides chi_s (the recovery
-- multiplier), each 1 when nil; their clamps are the caller's. At a bout's first asleep minute (boutH 0
-- before this step) boutVig latches whether a band-2 minute ended within VIG_WINDOW_H before ageH; it holds
-- until the next bout starts. A bout that closes with at least K.circadian.MAIN_SLEEP_H booked (boutH, asleep hours
-- only) is a main sleep: the body clock wakes at WAKE_H (K.circadian.wake) and this step's circ reads the reset hour;
-- a nap or an accelerated-sleep mod's few-minute bout leaves it.
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

-- The sleep term of the impairment unit: 0 at IU_SLEEP_ZERO_H (16 h) awake, 1 IU_SLEEP_SPAN_H later (24 h, S0892), plus debt / IU_SLEEP_DEBT_H (10.5), cap IU_SLEEP_MAX (1.5).
function K.acute.iuSleep(a)
    local A = K.acute
    local awake = K.clamp((a.awakeH - A.IU_SLEEP_ZERO_H) / A.IU_SLEEP_SPAN_H, 0, A.IU_SLEEP_MAX)
    return K.min(A.IU_SLEEP_MAX, awake + a.debtH / A.IU_SLEEP_DEBT_H)
end

-- The dehydration term: 0 below IU_DEHYD_FROM (1 %), IU_DEHYD_SLOPE1 (0.45) per per cent to IU_DEHYD_KNEE (2 %), IU_DEHYD_SLOPE2 (0.22) per per cent above, cap IU_DEHYD_MAX (0.89).
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

-- The impairment unit (1 IU = 24 h awake = BAC 0.05 %): the sleep, alcohol, dehydration, glucose and iron
-- terms summed, less the caffeine credit min(IU_sleep, CREDIT_BASE x min(1, caf / CREDIT_BASE_MG) + CREDIT_GAIN x min(1, caf / CREDIT_MG)), clamped [0, IU_MAX].
-- Additive. Writes a.iu and a.iuSleep (the sleep term, for the Plan 5 readers) and returns a.iu.
function K.acute.iu(a, dehydPct, ironGrade)
    local A = K.acute
    local sleep = A.iuSleep(a)
    a.iuSleep = sleep
    local credit = K.min(sleep, A.CREDIT_BASE * K.min(1, a.caf / A.CREDIT_BASE_MG) + A.CREDIT_GAIN * K.min(1, a.caf / A.CREDIT_MG))
    local sum = sleep + A.iuAlcohol(a.bac) + A.iuDehyd(dehydPct) + A.iuGlucose(a.bg) + A.IU_IRON[ironGrade]
    a.iu = K.clamp(sum - credit, 0, A.IU_MAX)
    return a.iu
end

-- One exercise step: exEma, the moderate-or-harder minutes of about the last EX_TAU_H (6 h), decays on
-- EX_TAU_H and takes this step's minutes (dtH x 60) when the training band is 1 or 2; a band-2 step stamps
-- lastVigAgeH = ageH, the world age sleepMinute's vigorous latch reads. band is 0, 1 or 2.
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

-- One cold step: coldH, the cold hours of about the last COLD_TAU_H (6 h), decays on it and takes dtH when the
-- thermoregulator's coldMult is above COLD_ON.
function K.acute.coldMinute(a, coldMult, dtH)
    local A = K.acute
    local add = 0
    if coldMult > A.COLD_ON then
        add = dtH
    end
    a.coldH = a.coldH * math.exp(-dtH / A.COLD_TAU_H) + add
    return a
end

-- One retinol step: retEma, the RET_TAU_D-day (14) EMA of the ingested preformed retinol in ug/day,
-- relaxes toward this step's rate ingestedUg / dtD by the fraction 1 - exp(-dtD / RET_TAU_D), the exact
-- step for a rate held over the step (a constant 900 ug/day reaches 900 x (1 - e^-1) in RET_TAU_D days at any
-- step length). A step of dtD <= 0 changes nothing.
function K.acute.retinolMinute(a, ingestedUg, dtD)
    if dtD <= 0 then
        return a
    end
    local perDay = ingestedUg / dtD
    a.retEma = a.retEma + (perDay - a.retEma) * (1 - math.exp(-dtD / K.acute.RET_TAU_D))
    return a
end

-- One refeeding day close: kcalPerKg the day's absorbed kcal per kg, w the mass kg at the close, ageH the
-- world age. Order: the refeeding window opens on a normal day that follows a low day while the previous
-- close left the risk high (refeedDayN 0; the low-day predecessor is a game choice so that a thin but
-- fed character does not cycle windows); the starvation count, the 90-day mass maximum, BMI (stored on
-- a.bmi for refeedEvent) and the 90-day loss update; the risk recomputes outside a window (S0115): high
-- (2) on any high criterion, 2 on two moderate ones, 1 on one, else 0. partial: the closed day is the character's
-- first, partial day (under 24 h since its birth), which is never a low day, so a new character does not start one
-- starved day in (Plan 15 close; the drain's unfed clock caps by age the same way). starvedDays counts record days
-- of little or no intake, S0115's criterion as written ("little or no intake for more than 5 / 10 days"), not the
-- drain's unfed hours (K.drain.unfedH), which a nibble resets: the two clocks answer different questions and can
-- disagree by up to a day at a fast's start (Plan 15 close, L4).
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

-- The refeeding event, called after refeedDay at the same close with a uniform roll in [0, 1): inside the
-- first REFEED_DAYS refeeding days the day counts and an intake above the restart limit (RESTART_KCAL_KG, 10 kcal/kg;
-- RESTART_LOW_KCAL_KG, 5, at RESTART_LOW_BMI, BMI 14, or below; S0116) rolls the event at REFEED_P; the close after day REFEED_DAYS ends the window (refeedDayN
-- -1) and the risk recomputes at the next close. Writes a.refeedEvent and returns it.
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
