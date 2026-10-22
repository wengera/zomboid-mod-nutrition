-- NR_Kernel_Deficit.lua -- the deficit drive (spec § 5a): how an energy deficit raises hunger, as one
-- mechanism. The trailing-24 h balance (K.energy.eb24h, the expenditure model's window) enters the energy state through
-- the balance term (BALANCE_SPAN_KCAL, state); exercise kcal enter it only through a first-order lag that plateaus
-- below the whole share (EX_LAG_TAU_D, EX_LAG_GAIN, exerciseLag, lagged), bypassed on a ramp when the day's total
-- deficit is large (EX_BYPASS_LO, EX_BYPASS_HI, activityState); and the hunger target meets the satiety read with the
-- energy state (hungerTarget, and its inverse unsated, which the meal pool's seed reads; the deficit floor, fitted at
-- its bound 0, was removed in Plan 11g Task 7 fix 1). Until Plan 11g Task 7 the pieces sat in
-- NR_Kernel_Energy (the balance, the lag, the bypass) and NR_Kernel_Hybrid (the hunger target). Pure: numbers in,
-- numbers out, no Java; one statement a line for the coverage gate. This file sorts before NR_Kernel_Energy.lua, and
-- every K.clamp reference is at call time.
local K = NutritionRevamp.kernel
K.deficit = {}

-- --- the balance term ---------------------------------------------------------------------------------------------
-- The balance term's span, the trailing-24 h deficit (kcal) at which K.deficit.state's
-- balance term reaches its 0.5 cap (a surplus of the span reaches -0.5). Fitted jointly with the bypass ramp's ends
-- (and, until Plan 11g Task 7 fix 1, the deficit floor) on the server-path replays (Plan 11f Task 2c and its fix round 1, Karl 2021's two arms
-- scored; Plan 11g Task 7 on the deficit studies alone, the well-fed arm held as a constraint now that satiety
-- carries it: tools/fit_deficit_drive.py over testing/tests/kernel/deficit_oracles.py).
K.deficit.BALANCE_SPAN_KCAL = K.dials.get("deficit.BALANCE_SPAN_KCAL")

-- --- the fat term: the low-fat hunger ramp (Plan 13 Task 10c) ---------------------------------------------------
-- The fat store's drive enters on its depletion from the body's own reference (fatDep = (fmRef - fm) / fmRef), never
-- on its level: a stable lean body reads none (S2189-S2193, constitutional thinness; S2184-S2186: the level of fat
-- does not predict intake), a body that lost fat reads it, more per kg the leaner it started (S2181). The term is a
-- ramp with a soft threshold, FAT_GAIN x clamp((fatDep - FAT_DEP_LO) / (FAT_DEP_HI - FAT_DEP_LO), 0, 1): near nothing
-- at modest loss, full at Minnesota's depletion (S2180), in place of ruling 14's linear 0.5 x fatDep (S2196 open:
-- no row gives hunger against fat lost in lean people as a dose-response).
K.deficit.FAT_DEP_LO = K.dials.get("deficit.FAT_DEP_LO")
K.deficit.FAT_DEP_HI = K.dials.get("deficit.FAT_DEP_HI")
K.deficit.FAT_GAIN = K.dials.get("deficit.FAT_GAIN")

-- The fat term of the energy state at depletion fatDep (0 none .. 1 all of the reference lost): 0 at or below
-- FAT_DEP_LO, the common case, before any arithmetic (the per-minute path, Rule 6).
function K.deficit.fatTerm(fatDep)
    local D = K.deficit
    if not (fatDep > D.FAT_DEP_LO) then
        return 0
    end
    return D.FAT_GAIN * K.clamp((fatDep - D.FAT_DEP_LO) / (D.FAT_DEP_HI - D.FAT_DEP_LO), 0, 1)
end

-- The energy state the hunger term reads: 1 neutral, up under deficit and fat depletion (the fat term above), down
-- under surplus, clamped to [0.5, 2.0] (a game choice). Muscle glycogen does not enter it (ruling T4-1:
-- no science row backs a coupling, and ketosis blunts the deficit's rise in appetite, S1451, S1452, S1259).
function K.deficit.state(eb24h, fatDep)
    return K.clamp(1 + K.deficit.BALANCE_CAP * K.clamp(-eb24h / K.deficit.BALANCE_SPAN_KCAL, -1, 1) + K.deficit.fatTerm(fatDep), K.deficit.STATE_MIN, K.deficit.STATE_MAX) -- ruling 14; the span BALANCE_SPAN_KCAL, ruling 9c-1; the fat term, Plan 13 Task 10c
end

-- --- the exercise lag ---------------------------------------------------------------------------------------------
-- Spec § 5c: no same-day compensation for exercise. A deficit made by exercise
-- does not raise appetite the same day, while an equal one made by food restriction does (S1312; S1310, S1311,
-- S1313); intake makes up about 30 % of an exercise deficit over days 3-16 (S1318) and more over months (S1320,
-- S1321, S1322). L is the exercise expenditure rate in kcal per day that appetite has caught up with: a first-order
-- lag of the exercise kcal (exKcalDay's quantity, the MET above the idle class). The split of a deficit into an
-- exercise share and a food share is a game choice no row defines.
K.deficit.EX_LAG_TAU_D = K.dials.get("deficit.EX_LAG_TAU_D")

-- One lag step of dtH game hours with exKcal exercise kcal spent in it: L relaxes toward the step's rate (exKcal x 24
-- / dtH kcal per day). Nothing for no time; a non-finite L reads 0 and a negative or non-finite exKcal reads none.
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

-- The exercise deficit, kcal per day, that enters the energy state: EX_LAG_GAIN x L, non-negative and finite.
function K.deficit.lagged(L)
    if not K.finite(L) or L < 0 then
        return 0
    end
    return K.deficit.EX_LAG_GAIN * L
end

-- Spec § 5d: the lag plateaus below the whole exercise share. lagged(L) is the gain
-- times L, so a steady exercise rate is compensated at EX_LAG_GAIN of it once the lag has caught up; the bypass ramp
-- in activityState still moves the lag toward the whole ex24h, unscaled by the gain.
K.deficit.EX_LAG_GAIN = K.dials.get("deficit.EX_LAG_GAIN")

-- --- the bypass: a large total deficit raises hunger through the lag ------------------------------------------------
-- The energy state the writer hands to hungerTarget: the food balance (eb24h with the window's exercise kcal ex24h
-- added back) enters at once, the exercise share only through the lag. lagged(L) >= 0 and state falls with the
-- balance, so the activity never pushes the state below that of the same intake without it (S1330, S1331, S1332).
-- A negative or non-finite ex24h reads none. A 24-h total deficit bypasses the lag on a linear ramp: with ee24h the
-- 24-h expenditure and d = -eb24h / ee24h, the weight w = clamp((d - EX_BYPASS_LO) / (EX_BYPASS_HI - EX_BYPASS_LO), 0, 1)
-- moves the lag w of the way to ex24h (heavy work in a deficit raises hunger within days, S1325; ordinary exercise
-- stays compensated over weeks, S1312, S1318); it only ever raises the lag, so the never-below property holds. An
-- ee24h that is nil, non-finite or not positive bypasses nothing. The ramp, not a step, rests on King 2011 alone
--: since Plan 11g Task 7's refit a 25 % step passes Karl's band too.
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
-- The hunger target from a fill-like scalar x (0 empty .. 1 sated: since Plan 11c the satiety read Z) and the energy
-- state (moved from the takeover's K.fast.hungerTarget): (1 - x) x energyState, clamped to [0, 1].
-- The deficit's hunger comes through the energy state alone (S1254 sets its direction): the deficit floor, a
-- coefficient x max(0, energyState - 1) added whatever the satiety read (0.02 from Plan 11f Task 2c fix 1, 1.0 in Plan
-- 11d, 0.15 in Plan 3; S1271 open), fitted at its bound 0 in Plan 11g Task 7 (fit-11g-deficit-20261012:
-- every floor above 0 scored lower) and was removed in its fix round 1.
function K.deficit.hungerTarget(x, energyState)
    return K.clamp((1 - x) * energyState, 0, 1)
end

-- The inverse of hungerTarget inside its clamp: the unsated share (1 - x) a hunger reads at energyState. The caller
-- guards a non-positive or non-finite energyState (K.satiety.seedMeal).
function K.deficit.unsated(hunger, energyState)
    return hunger / energyState
end

-- The energy state's cap and clamp (K.deficit.state; Plan 19 Task 3b), resolved at load: appended here so no line
-- above moved.
K.deficit.BALANCE_CAP = K.dials.get("deficit.BALANCE_CAP")
K.deficit.STATE_MIN = K.dials.get("deficit.STATE_MIN")
K.deficit.STATE_MAX = K.dials.get("deficit.STATE_MAX")
