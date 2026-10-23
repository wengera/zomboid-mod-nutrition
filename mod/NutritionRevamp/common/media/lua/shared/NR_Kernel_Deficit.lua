-- NR_Kernel_Deficit.lua -- the deficit drive: how an energy deficit raises hunger. The trailing-24 h balance enters the
-- energy state through the balance term; exercise kcal only through a lag that plateaus below the whole share,
-- bypassed on a ramp when the day's total deficit is large; the hunger target meets the satiety read with that state.
-- One statement a line for the coverage gate; K.clamp is read at call time.
local K = NutritionRevamp.kernel
K.deficit = {}

-- --- the balance term ---------------------------------------------------------------------------------------------
-- Fitted jointly with the bypass ramp's ends (tools/fit_deficit_drive.py).
K.deficit.BALANCE_SPAN_KCAL = K.dials.get("deficit.BALANCE_SPAN_KCAL")
K.deficit.BALANCE_CAP = K.dials.get("deficit.BALANCE_CAP")

-- --- the fat term: the low-fat hunger ramp -------------------------------------------------------------------------
-- The drive enters on depletion from the body's own reference, never on the level: a stable lean body reads none
-- (S2189), a body that lost fat reads it. A soft-threshold ramp, since no row gives the dose-response (S2196 open).
K.deficit.FAT_DEP_LO = K.dials.get("deficit.FAT_DEP_LO")
K.deficit.FAT_DEP_HI = K.dials.get("deficit.FAT_DEP_HI")
K.deficit.FAT_GAIN = K.dials.get("deficit.FAT_GAIN")

-- 0 at or below FAT_DEP_LO, the common case, before any arithmetic (the per-minute path, Rule 6).
function K.deficit.fatTerm(fatDep)
    local D = K.deficit
    if not (fatDep > D.FAT_DEP_LO) then
        return 0
    end
    return D.FAT_GAIN * K.clamp((fatDep - D.FAT_DEP_LO) / (D.FAT_DEP_HI - D.FAT_DEP_LO), 0, 1)
end

-- 1 neutral, up under deficit and fat depletion, down under surplus. Muscle glycogen does not enter it: ketosis blunts
-- the deficit's rise in appetite (S1451).
K.deficit.STATE_MIN = K.dials.get("deficit.STATE_MIN")
K.deficit.STATE_MAX = K.dials.get("deficit.STATE_MAX")
function K.deficit.state(eb24h, fatDep)
    return K.clamp(1 + K.deficit.BALANCE_CAP * K.clamp(-eb24h / K.deficit.BALANCE_SPAN_KCAL, -1, 1) + K.deficit.fatTerm(fatDep), K.deficit.STATE_MIN, K.deficit.STATE_MAX)
end

-- --- the exercise lag ---------------------------------------------------------------------------------------------
-- An exercise deficit does not raise appetite the same day, while an equal food-restriction one does (S1312); intake
-- makes up part of it over days to months (S1318). L is the exercise rate (kcal/day) appetite has caught up with.
K.deficit.EX_LAG_TAU_D = K.dials.get("deficit.EX_LAG_TAU_D")

-- Nothing for no time; a non-finite L reads 0 and a negative or non-finite exKcal reads none.
function K.deficit.exerciseLag(L, exKcal, dtH)
    if not K.finite(L) then
        L = 0
    end
    if not (dtH > 0) then
        return L
    end
    if not K.finite(exKcal) or exKcal < 0 then
        exKcal = 0
    end
    local k = math.exp(-dtH / (K.deficit.EX_LAG_TAU_D * 24))
    return L * k + exKcal * 24 / dtH * (1 - k)
end

function K.deficit.lagged(L)
    if not K.finite(L) or L < 0 then
        return 0
    end
    return K.deficit.EX_LAG_GAIN * L
end

-- The lag plateaus below the whole share; the bypass ramp in activityState still moves it toward the unscaled ex24h.
K.deficit.EX_LAG_GAIN = K.dials.get("deficit.EX_LAG_GAIN")

-- --- the bypass: a large total deficit raises hunger through the lag ------------------------------------------------
-- The energy state the writer hands to hungerTarget: the food balance (eb24h with ex24h
-- added back) enters at once, the exercise share only through the lag. lagged(L) >= 0 and state falls with the
-- balance, so the activity never pushes the state below that of the same intake without it (S1330, S1331, S1332).
-- A 24-h total deficit d = -eb24h / ee24h bypasses the lag on a linear ramp (heavy work in a deficit, S1325); it only
-- raises the lag, so the never-below property holds. An ee24h nil, non-finite or not positive bypasses nothing.
K.deficit.EX_BYPASS_LO = K.dials.get("deficit.EX_BYPASS_LO")
K.deficit.EX_BYPASS_HI = K.dials.get("deficit.EX_BYPASS_HI")
function K.deficit.activityState(eb24h, ex24h, L, fatDep, ee24h)
    local ex = 0
    if K.finite(ex24h) and ex24h > 0 then
        ex = ex24h
    end
    local lag = K.deficit.lagged(L)
    if K.finite(ee24h) and ee24h > 0 and K.finite(eb24h) and lag < ex then
        local d = -eb24h / ee24h
        local w = K.clamp((d - K.deficit.EX_BYPASS_LO) / (K.deficit.EX_BYPASS_HI - K.deficit.EX_BYPASS_LO), 0, 1)
        lag = lag + w * (ex - lag)
    end
    return K.deficit.state(eb24h + ex - lag, fatDep)
end

-- --- the hunger target ---------------------------------------------------------------------------------------------
-- x is the satiety read Z (0 empty .. 1 sated). The deficit's hunger comes through the energy state alone (S1254).
function K.deficit.hungerTarget(x, energyState)
    return K.clamp((1 - x) * energyState, 0, 1)
end

-- The caller guards a non-positive or non-finite energyState (K.satiety.seedMeal).
function K.deficit.unsated(hunger, energyState)
    return hunger / energyState
end
