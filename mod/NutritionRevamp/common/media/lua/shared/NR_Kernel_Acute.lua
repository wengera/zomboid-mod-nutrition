-- NR_Kernel_Acute.lua -- the acute states (Plan 4, rulings 10-15): caffeine (body load, the 7-day mean,
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
-- absorbGut) the intake landing feeds directly, bypassing the stomach's composition-scaled half-time
-- (one beer built no blood alcohol through the stomach, #2983); the shiver draw starts above a dead band
-- and glycogen refills whenever met < 3 (the thermoregulator's idle 1.007-1.010 indoors blocked every
-- refill, #2984); a sleep bout (boutH, gapH) tolerates awake gaps under BOUT_GAP_H (the harness hold's
-- isAsleep misses, #2840, never let a run reach the nap threshold, #2986).
local K = NutritionRevamp.kernel
K.acute = {}

-- The record.acute schema version.
K.acute.AV = 1 -- schema version, no row needed

-- Caffeine.
-- Absorption fraction of the gut lane, applied once in K.acute.absorbGut (ruling T17-2); alcohol and
-- caffeine take the dose absorbGut releases, so nothing re-applies it.
K.acute.CAF_ABSORB = 1.0 -- design-phase-v1 game choice (open row S1102: caffeine absorption fraction)
K.acute.CAF_THALF_H = 5.0 -- S0793 (5.0 h in men)
K.acute.CAF_THALF_SLOW_H = 9.7 -- S0793's 9.7 h arm borrowed for the slow-metaboliser trait; S0794 (CYP1A2 polymorphism)
K.acute.CAF_SLOW_SHARE = 0.5 -- design-phase-v1 game choice (open row S1103: the share of slow metabolisers)
K.acute.CAF_MEAN_H = 168 -- game choice: the 7-day window of the daily-rate EMA
K.acute.CAF_TOL_REF = 400 -- S0807 (400 mg/day for at least 14 days: tolerance)
K.acute.CAF_TOL_TAU_H = 168 -- tau_up 7 d, S0807-derived (86 % by day 14); tau_down the same, open row S0848
K.acute.CAF_WD_TOL = 0.25 -- S0806 (100 mg/day = 0.25 of the 400 reference)
K.acute.CAF_WD_LOW_MG = 10.7 -- 0.1 x the 107 mg cup of S0797: game choice
K.acute.CAF_WD_ONSET_H = 12 -- S0805 (onset 12-24 h)
K.acute.CAF_WD_PEAK_H = 36 -- S0805 (peak 20-51 h); the midpoint a game choice
K.acute.CAF_WD_END_H = 120 -- S0805 (2-9 days); the point a game choice
K.acute.CAF_EFFECT_MGKG = 3 -- S0531 (3-6 mg/kg band: full at 3); S0626 (caffeineActive at 3 mg/kg)

-- The gut lane caffeine and ethanol absorb from (ruling T17-2): first order on this half-time, game hours.
K.acute.GUT_T_HALF = 0.5 -- design-phase-v1 game choice; open S1102 (caffeine time to peak); the S0524 beer cross-check: 1 L of 4 % beer peaks ~1 h

-- Alcohol.
-- The Widmark distribution factor, indexed by sex.
K.acute.WIDMARK_R = {
    0.68, -- male: design-phase-v1 game choice (open row S1104: the Widmark distribution factor r)
    0.55, -- female: design-phase-v1 game choice (open row S1104: the Widmark distribution factor r)
}
K.acute.BETA = 0.015 -- per cent BAC per hour: design-phase-v1 game choice (open row S1105: the elimination rate beta)
K.acute.HANG_PEAK = 0.05 -- per cent BAC: game choice, the S0893 0.05 % unit point (hangover direction S0854 open)
K.acute.HANG_H = 6 -- hours at a 0.05 % peak, scaled by peak/0.05: design-phase-v1 game choice (open row S0854: hangover duration)

-- The alcohol impairment knots {BAC %, IU}: the unit at 0.05 % (S0893), the driving bands (S0905).
K.acute.IU_ALC_KNOTS = {
    { 0, 0 }, -- sober
    { 0.03, 0.30 }, -- S0905 (0.03 %: mean speed impaired); the 0.30 interpolation a game choice
    { 0.05, 1.00 }, -- S0893 (24 h awake = 0.05 %: the unit)
    { 0.08, 1.60 }, -- S0893 (0.08 % the upper bound), S0905 (all measures at 0.08 %)
}
K.acute.IU_ALC_CAP = 2.0 -- game choice: the last segment extended to this cap

-- Glycogen, mmol glucosyl per kg dry muscle.
K.acute.GLYC_REF = 462 -- S0679
K.acute.GLYC_HIGH = 102 -- S0680 (high carbohydrate availability +102)
K.acute.GLYC_LOW = 253 -- S0680 (depletion plus low carbohydrate -253)
K.acute.GLYC_PIVOT = 3 -- g/kg/day: design-phase-v1 game choice (open row S1108: the intake that holds the store)
K.acute.GLYC_SPAN = 3 -- g/kg/day to the full swing (6 = S0680's high threshold); the low side a game choice
K.acute.GLYC_TAU_H = 24 -- design-phase-v1 game choice (open row S1108: the resynthesis time constant)
K.acute.GLYC_MAX = 600 -- game choice: the store's ceiling (564 the high-carbohydrate target)
K.acute.USE_WORK = 51.5 -- mmol/kg/h at MET 7.5, S0683 (71 % VO2max)
K.acute.USE_MET_LO = 3 -- game choice: no glycogen draw at or below MET 3
K.acute.USE_MET_SPAN = 4.5 -- MET 7.5 = 71 % VO2max: design-phase-v1 game choice (open row S1107: MET to per cent VO2max)
K.acute.USE_MAX = 1.6 -- game choice: the draw's cap in units of the MET 7.5 rate
K.acute.USE_SHIVER = 52 -- mmol/kg/h at coldMult 3.5, derived from S0049 (410 -> 332 in 90 min)
K.acute.SHIVER_FULL = 3.5 -- S0049 (3.5 x resting metabolic rate): the full draw
K.acute.SHIVER_DEADBAND = 1.05 -- game choice (ruling T17-3): the thermoregulator's idle multiplier sits at 1.007-1.010 indoors (x151r #2984); no shiver draw at or below it

-- Blood glucose, mmol/L.
K.acute.BG_NORMAL = 5.0 -- S0684 (fed range 4.2-5.2); no fall from fasting alone, S0896
K.acute.BG_EXERTION = 2.5 -- S0684 (2.5 mM at fatigue)
K.acute.BG_EX_G = 0.2 -- design-phase-v1 game choice (open row S1109: the glycogen level of exertional hypoglycaemia)
K.acute.BG_EX_MET = 6 -- design-phase-v1 game choice (open row S1109: the exercise intensity of exertional hypoglycaemia)
K.acute.BG_ALC_FAST = 3.0 -- S1015 direction; design-phase-v1 game choice (open row S1110: alcohol-fasting glucose)
K.acute.BG_ALC_FAST_H = 12 -- hours of empty stomach, S1015 direction; design-phase-v1 game choice (open row S1110)
K.acute.BG_TAU_CHO_H = 0.25 -- design-phase-v1 game choice (open row S1111: the glucose recovery time course)
K.acute.BG_TAU_H = 1 -- design-phase-v1 game choice (open row S1111: the glucose recovery time course)
K.acute.BG_MIN = 2.0 -- game choice: the clamp's floor
K.acute.BG_MAX = 8.0 -- game choice: the clamp's ceiling
K.acute.IU_BG_HI = 3.5 -- S0897 (impairment 2.6-3.0; the 3.5 upper bound the report's choice)
K.acute.IU_BG_LO = 3.0 -- S0897, S0898 (-0.7 SD at 3.0)
K.acute.IU_BG_MAX = 0.90 -- S0898 (-0.7 SD at 3.0, scaled to the unit)

-- Sleep, game hours.
K.acute.SLEEP_NEED_H = 7.5 -- S0740 (7-9 h, the midpoint)
K.acute.CHI_W = 18.2 -- S0733
K.acute.CHI_S = 4.2 -- S0734
K.acute.CHI_W_DEBT = 0.02 -- per debt hour: design-phase-v1 game choice (open row S1114: debt on build-up rate)
K.acute.CHI_W_DEBT_MAX = 20 -- debt hours: design-phase-v1 game choice (open row S1114: debt on build-up rate)
K.acute.S_FLOOR_DEBT = 0.01 -- per debt hour: design-phase-v1 game choice (open row S1114: debt on the floor)
K.acute.S_FLOOR_MAX = 0.25 -- design-phase-v1 game choice (open row S1114: debt on the floor)
K.acute.S_RESTED = 0.17 -- game choice: S on waking from a full night (the briefing's rested value)
K.acute.NAP_MIN_H = 1 -- design-phase-v1 game choice (open row S1112: the sleep that resets hours awake)
K.acute.BOUT_GAP_H = 10 / 60 -- design-phase-v1 game choice; open S1112 (the nap rule): an awake gap this long ends a sleep bout (ruling T17-4)
K.acute.WINDOW_H = 24 -- game choice: the accounting window
K.acute.DEBT_MAX = 40 -- S0742 (cumulative); the cap a game choice
K.acute.REPAY = 0.5 -- S0743 (deficits persist); design-phase-v1 game choice (open row S1113: the repaid fraction)
K.acute.CIRC_AMP = 0.12 -- S0736
K.acute.CIRC_PEAK_H = 4 -- design-phase-v1 game choice (open row S0861: the 04:00 trough)
-- Sign: +0.12 at 04:00 = the sleep-propensity peak (the alertness trough); Plan 5's FATIGUE term ADDS circ.
K.acute.IU_SLEEP_ZERO_H = 16 -- design-phase-v1 game choice (open row S1115: the hours awake of the first decline)
K.acute.IU_SLEEP_SPAN_H = 8 -- S0892 (24 h awake = 1 IU)
K.acute.IU_SLEEP_DEBT_H = 10.5 -- derived from S0742 (about 21 h owed = 2 nights' deprivation = 2 IU)
K.acute.IU_SLEEP_MAX = 1.5 -- game choice: the sleep term's cap

-- The impairment unit.
K.acute.IU_DEHYD_FROM = 1 -- per cent: S0894 (1-6 % body-mass loss)
K.acute.IU_DEHYD_KNEE = 2 -- per cent: S0895 (the 2 % subgroup split)
K.acute.IU_DEHYD_SLOPE1 = 0.45 -- S0894/S0895 scaled to the unit (the report's arithmetic)
K.acute.IU_DEHYD_SLOPE2 = 0.22 -- S0894/S0895 scaled to the unit (the report's arithmetic)
K.acute.IU_DEHYD_MAX = 0.89 -- S0894 (attention ES -0.52 scaled to the unit)
-- The iron term by grade 1..4.
K.acute.IU_IRON = {
    0, -- replete
    0, -- marginal
    0.38, -- depleted: half of S0906's 0.776, game choice
    0.76, -- clinical: S0906 (SMD 0.59 / 0.776)
}
K.acute.CREDIT_BASE = 0.50 -- S0899 (g 0.28 rested); the formula a game choice
K.acute.CREDIT_GAIN = 0.60 -- S0900 (g 1.11 after sleep loss); the formula a game choice
K.acute.CREDIT_MG = 200 -- S0899 (doses of 200 mg and more did more)
K.acute.CREDIT_BASE_MG = 100 -- game choice (ruling T9-2: the rested credit is full at 100 mg; S0899 direction)
K.acute.IU_MAX = 2.5 -- game choice: additive sum capped (super-additive gamma rejected pending open row S0855)

-- Refeeding.
K.acute.LOW_KCAL_KG = 5 -- kcal/kg/day: design-phase-v1 game choice (open row S1116: the little-or-no-intake day)
K.acute.HEIGHT_M = 1.75 -- design-phase-v1 game choice (open row S1117: the reference stature)
K.acute.MASS_WINDOW_H = 2160 -- 90 days in hours, S0115 (weight loss within 3-6 months)
K.acute.RISK_BMI_HIGH = 16 -- S0115
K.acute.RISK_LOSS_HIGH = 0.15 -- S0115
K.acute.RISK_DAYS_HIGH = 10 -- S0115
K.acute.RISK_BMI_MOD = 18.5 -- S0115
K.acute.RISK_LOSS_MOD = 0.10 -- S0115
K.acute.RISK_DAYS_MOD = 5 -- S0115
K.acute.REFEED_DAYS = 7 -- S0116 (4-7 days)
K.acute.RESTART_KCAL_KG = 10 -- S0116
K.acute.RESTART_LOW_KCAL_KG = 5 -- S0116 (BMI 14 or below)
K.acute.RESTART_LOW_BMI = 14 -- S0116
K.acute.REFEED_P = 0.23 -- S0117 (23 %); S0118's 35 % noted, both critically-ill populations: game choice

-- A fresh record.acute at world age ageH: no caffeine or alcohol on board or in the gut, the reference
-- glycogen and normal glucose, rested, no debt or sleep bout, no refeeding risk. bmi 0 until the first
-- refeedDay close.
function K.acute.new(ageH)
    return {
        av = K.acute.AV,
        gutAlc = 0,
        gutCaf = 0,
        caf = 0,
        cafMean = 0,
        cafTol = 0,
        cafLowH = 0,
        wdH = -1,
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
    }
end

-- The slow-metaboliser draw: the adapter passes a uniform roll in [0, 1) once per character.
function K.acute.drawSlowMet(roll)
    return roll < K.acute.CAF_SLOW_SHARE
end

-- One gut-lane step over dtH hours (ruling T17-2): the fraction 1 - exp(-ln2 x dtH / GUT_T_HALF) of the
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
-- daily-rate EMA takes the step's sample (dose x 24 / dtH mg/day) with alpha = dtH / 168, written without
-- the division so a dose-only step (dtH 0) adds dose / 7; tolerance relaxes toward clamp(mean/400, 0, 1)
-- with tau 7 d both ways; withdrawal hours accrue while tolerant and the load is under 10.7 mg. wd is the
-- withdrawal intensity 0..1 and wdH the hours since its onset (-1 outside the episode). w is accepted for
-- the call shape (the effect scalars take it).
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
        a.wdH = -1
    elseif h <= A.CAF_WD_PEAK_H then
        a.wd = (h - A.CAF_WD_ONSET_H) / (A.CAF_WD_PEAK_H - A.CAF_WD_ONSET_H)
        a.wdH = h - A.CAF_WD_ONSET_H
    else
        a.wd = (A.CAF_WD_END_H - h) / (A.CAF_WD_END_H - A.CAF_WD_PEAK_H)
        a.wdH = h - A.CAF_WD_ONSET_H
    end
    return a
end

-- The caffeine performance scalar: full at 3 mg/kg on board (S0531).
function K.acute.cafEffect(a, w)
    return K.clamp(a.caf / (K.acute.CAF_EFFECT_MGKG * w), 0, 1)
end

-- Whether 3 mg/kg is on board (S0626).
function K.acute.caffeineActive(a, w)
    return a.caf >= K.acute.CAF_EFFECT_MGKG * w
end

-- One alcohol step: the absorbed ethanol g lands, the Widmark zero-order elimination beta x r x w x 10
-- g/h drains it, BAC = load / (10 r w) per cent. The peak is tracked while BAC > 0; when BAC returns to 0
-- after a peak of at least 0.05 % the hangover starts for HANG_H x peak/0.05 hours and counts down; a
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
        a.hangH = A.HANG_H * a.alcPeak / A.HANG_PEAK
    else
        a.alcPeak = 0
    end
    return a
end

-- The alcohol term of the impairment unit: piecewise-linear over IU_ALC_KNOTS, the last segment extended
-- above 0.08 % and capped at IU_ALC_CAP.
function K.acute.iuAlcohol(bac)
    local kn = K.acute.IU_ALC_KNOTS
    local n = #kn -- IU_ALC_KNOTS is a Lua table this file built, so # is defined on it
    if bac <= 0 then
        return 0
    end
    local seg = n
    for i = n, 2, -1 do
        if bac <= kn[i][1] then
            seg = i
        end
    end
    local x0 = kn[seg - 1][1]
    local y0 = kn[seg - 1][2]
    local y = y0 + (kn[seg][2] - y0) * (bac - x0) / (kn[seg][1] - x0)
    return K.min(y, K.acute.IU_ALC_CAP)
end

-- The glycogen target for a 24 h carbohydrate intake cho24 g/kg/day (S0680 anchors).
function K.acute.glycTarget(cho24)
    local A = K.acute
    local hi = K.clamp((cho24 - A.GLYC_PIVOT) / A.GLYC_SPAN, 0, 1)
    local lo = K.clamp((A.GLYC_PIVOT - cho24) / A.GLYC_SPAN, 0, 1)
    return A.GLYC_REF + A.GLYC_HIGH * hi - A.GLYC_LOW * lo
end

-- One glycogen step: the work draw (above MET 3) and the shivering draw (above the coldMult dead band,
-- full at 3.5), mmol/kg/h; at rest (met < 3, the S0683 work floor) the store also relaxes toward the
-- carbohydrate target on tau 24 h, the refill and any shiver draw coexisting (ruling T17-3: a working
-- step never refills, a cold resting one refills less). Clamped to [0, GLYC_MAX]; g = clamp(G / 462, 0, 1).
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
    a.g = K.clamp(a.glyc / A.GLYC_REF, 0, 1)
    return a
end

-- One blood-glucose step: carbohydrate absorbed this step (choAbsG > 0) restores toward 5.0 on tau 15 min;
-- otherwise the target is 2.5 under exertion with g < 0.2 (a.g, the glycogen step's), 3.0 with alcohol on
-- board after more than 12 h of empty stomach, else 5.0 (no fall from fasting alone, S0896), on tau 1 h.
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

-- The glucose term of the impairment unit: 0 at or above 3.5 mmol/L, linear to 0.90 at 3.0, held below.
function K.acute.iuGlucose(bg)
    local A = K.acute
    local x = K.clamp((A.IU_BG_HI - bg) / (A.IU_BG_HI - A.IU_BG_LO), 0, 1)
    return A.IU_BG_MAX * x
end

-- One sleep step over dtH game hours at world age ageH. sleepDisabled (the server's SleepAllowed and
-- SleepNeeded not both true, the reset ahead of the hook, run x151s) freezes the state at rested: hours
-- awake, debt, the sleep run and the window's sleep are 0, S is S_RESTED and the window restarts at ageH,
-- so a later re-enable opens a fresh window; frozen is set and circ still computed. Otherwise: asleep,
-- the run (sleptH), the bout (boutH) and the window's sleep accrue, the bout's gap clears, hours awake
-- reset to 0 once the bout reaches NAP_MIN_H (at that minute, ruling T17-4) and otherwise hold, and S
-- decays on chi_s to a debt floor capped at S_FLOOR_MAX; awake, the run clears, a bout in progress counts
-- its gap (gapH) and ends when the gap reaches BOUT_GAP_H -- a bout that had reset hours awake then
-- credits the whole gap to them, the waking having begun at its start -- hours awake accrue unless a
-- bout of at least NAP_MIN_H is in progress, and S rises toward 1 on chi_w shortened by the debt. A gap
-- under BOUT_GAP_H inside a bout is so tolerated (the harness hold's isAsleep misses, #2840). sleptH is
-- the unbroken run, kept for the readers; the reset reads the bout. The 24 h window closes
-- when ageH has run WINDOW_H past its start: the shortfall against need (7.5 h x needFactor, the trait
-- multiplier) adds to the debt, the excess repays REPAY of itself, clamped [0, DEBT_MAX].
function K.acute.sleepMinute(a, asleep, hourOfDay, needFactor, ageH, dtH, sleepDisabled)
    local A = K.acute
    a.circ = A.CIRC_AMP * math.cos(2 * math.pi * (hourOfDay - A.CIRC_PEAK_H) / 24)
    if sleepDisabled then
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
        a.sleptH = a.sleptH + dtH
        a.boutH = a.boutH + dtH
        a.gapH = 0
        a.winSleptH = a.winSleptH + dtH
        if a.boutH >= A.NAP_MIN_H then
            a.awakeH = 0
        end
        local floor = K.min(A.S_FLOOR_DEBT * a.debtH, A.S_FLOOR_MAX)
        a.S = K.max(a.S * math.exp(-dtH / A.CHI_S), floor)
    else
        a.sleptH = 0
        if a.boutH > 0 then
            a.gapH = a.gapH + dtH
            if a.gapH >= A.BOUT_GAP_H then
                if a.boutH >= A.NAP_MIN_H then
                    a.awakeH = a.gapH - dtH -- the gap before this step; this step accrues below
                end
                a.boutH = 0
                a.gapH = 0
            end
        end
        if a.boutH < A.NAP_MIN_H then
            a.awakeH = a.awakeH + dtH
        end
        local chiW = A.CHI_W / (1 + A.CHI_W_DEBT * K.min(a.debtH, A.CHI_W_DEBT_MAX))
        a.S = 1 - (1 - a.S) * math.exp(-dtH / chiW)
    end
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

-- The sleep term of the impairment unit: 0 at 16 h awake, 1 at 24 h (S0892), plus debt / 10.5, cap 1.5.
function K.acute.iuSleep(a)
    local A = K.acute
    local awake = K.clamp((a.awakeH - A.IU_SLEEP_ZERO_H) / A.IU_SLEEP_SPAN_H, 0, A.IU_SLEEP_MAX)
    return K.min(A.IU_SLEEP_MAX, awake + a.debtH / A.IU_SLEEP_DEBT_H)
end

-- The dehydration term: 0 below 1 %, 0.45 per per cent to 2 %, 0.22 per per cent above, cap 0.89.
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
-- terms summed, less the caffeine credit min(IU_sleep, 0.5 x min(1, caf / 100) + 0.6 x min(1, caf / 200)), clamped [0, 2.5].
-- Additive (ruling 14). Writes a.iu and returns it.
function K.acute.iu(a, dehydPct, ironGrade)
    local A = K.acute
    local sleep = A.iuSleep(a)
    local credit = K.min(sleep, A.CREDIT_BASE * K.min(1, a.caf / A.CREDIT_BASE_MG) + A.CREDIT_GAIN * K.min(1, a.caf / A.CREDIT_MG))
    local sum = sleep + A.iuAlcohol(a.bac) + A.iuDehyd(dehydPct) + A.iuGlucose(a.bg) + A.IU_IRON[ironGrade]
    a.iu = K.clamp(sum - credit, 0, A.IU_MAX)
    return a.iu
end

-- One refeeding day close: kcalPerKg the day's absorbed kcal per kg, w the mass kg at the close, ageH the
-- world age. Order: the refeeding window opens on a normal day that follows a low day while the previous
-- close left the risk high (refeedDayN 0; the low-day predecessor is a game choice so that a thin but
-- fed character does not cycle windows); the starvation count, the 90-day mass maximum, BMI (stored on
-- a.bmi for refeedEvent) and the 90-day loss update; the risk recomputes outside a window (S0115): high
-- (2) on any high criterion, 2 on two moderate ones, 1 on one, else 0.
function K.acute.refeedDay(a, kcalPerKg, w, ageH, kDepleted, mgDepleted, alcoholHistory)
    local A = K.acute
    local low = kcalPerKg < A.LOW_KCAL_KG
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
    a.bmi = w / (A.HEIGHT_M * A.HEIGHT_M)
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
-- first REFEED_DAYS refeeding days the day counts and an intake above the restart limit (10 kcal/kg, 5 at
-- BMI 14 or below, S0116) rolls the event at REFEED_P; the close after day 7 ends the window (refeedDayN
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
