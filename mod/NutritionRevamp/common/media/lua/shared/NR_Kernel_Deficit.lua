-- NR_Kernel_Deficit.lua -- the deficit drive (Plan 11g Task 7, spec § 5a): how an energy deficit raises hunger, as one
-- mechanism. The trailing-24 h balance (K.energy.eb24h, the expenditure model's window) enters the energy state through
-- the balance term (BALANCE_SPAN_KCAL, state); exercise kcal enter it only through a first-order lag that plateaus
-- below the whole share (EX_LAG_TAU_D, EX_LAG_GAIN, exerciseLag, lagged), bypassed on a ramp when the day's total
-- deficit is large (EX_BYPASS_LO, EX_BYPASS_HI, activityState); and the hunger target meets the satiety read with the
-- energy state and a deficit floor (DEFICIT_FLOOR, hungerTarget, and its inverse unsated, which the meal pool's seed
-- reads). Until Plan 11g Task 7 the pieces sat in NR_Kernel_Energy (the balance, the lag, the bypass) and
-- NR_Kernel_Hybrid (the floor and the hunger target). Pure: numbers in, numbers out, no Java; one statement a line for
-- the coverage gate. This file sorts before NR_Kernel_Energy.lua, and every K.energy, K.clamp and K.max reference is at
-- call time.
local K = NutritionRevamp.kernel
K.deficit = {}

-- --- the balance term ---------------------------------------------------------------------------------------------
-- Plan 11d Task 9d (ruling 9c-1): the balance term's span, the trailing-24 h deficit (kcal) at which K.deficit.state's
-- balance term reaches its 0.5 cap (a surplus of the span reaches -0.5). Fitted jointly with K.deficit.DEFICIT_FLOOR
-- on the server-path replays (refit in Plan 11f Task 2c and its fix round 1).
K.deficit.BALANCE_SPAN_KCAL = 3100 -- game choice, refit on the shipped pipeline against Karl 2021 as reported (Plan 11f ruling 2b-3, widened search), from Plan 11f Task 2c's 3300, Plan 11d's 7500 (ruling 9c-1) and Plan 3 ruling 14's 1500 (S1271 open: no row gives a hunger rise per kcal of deficit): fitted with K.deficit.DEFICIT_FLOOR 0.02 and K.deficit.EX_BYPASS_LO 0.282 and EX_BYPASS_HI 0.575 on the server-path replays at the point with the best worst-case smallest margin over twin K's plausible alternatives (0.283 of a half-width at LO 0.282, set from the search's 0.28 for S1318's 0.2814; the search's 0.286 at 0.28 sat within the 0.02 tie that prefers a floor above 0 and then the nearest the shipped constants): Karl 2021 as the paper ran it reads DEF +30.2 % against S1325's +26 % and BAL -45.1 % against -55 % (each within 1.5x), the 36 h fast's next-day intake 1.196 against S1613's 1.20 (Johnstone 2002, within 1.1x) and day 3 0.969 against S1614's 1.0 (Clayton 2016), King 2011 at steady state within 0.92 mm of control (S1312), six meals against three 0.981 (S1608, within 0.9-1.3; the band that binds as built, 0.40), the steady eater at balance; S1255 (CALERIE 2: < 10 mm at a 25 % deficit) reads 6.7 mm, reproduced

-- The energy state the hunger term reads: 1 neutral, up under deficit and fat depletion, down under surplus,
-- clamped to [0.5, 2.0] (ruling 14, a game choice). Muscle glycogen does not enter it (ruling T4-1, Plan 11d Task 4b:
-- no science row backs a coupling, and ketosis blunts the deficit's rise in appetite, S1451, S1452, S1259).
function K.deficit.state(eb24h, fatDep)
    return K.clamp(1 + 0.5 * K.clamp(-eb24h / K.deficit.BALANCE_SPAN_KCAL, -1, 1) + 0.5 * fatDep, 0.5, 2.0) -- ruling 14; the span BALANCE_SPAN_KCAL, ruling 9c-1
end

-- --- the exercise lag ---------------------------------------------------------------------------------------------
-- Plan 11c Task 4b (spec § 5c, ruling 11c-29): no same-day compensation for exercise. A deficit made by exercise
-- does not raise appetite the same day, while an equal one made by food restriction does (S1312; S1310, S1311,
-- S1313); intake makes up about 30 % of an exercise deficit over days 3-16 (S1318) and more over months (S1320,
-- S1321, S1322). L is the exercise expenditure rate in kcal per day that appetite has caught up with: a first-order
-- lag of the exercise kcal (exKcalDay's quantity, the MET above the idle class). The split of a deficit into an
-- exercise share and a food share is a game choice no row defines.
K.deficit.EX_LAG_TAU_D = 16 -- game choice, Plan 11d (ruling 11d-4), refit from Plan 11c Task 4b's 24 (S1335 open): the lag's time constant in days, fitted with EX_LAG_GAIN to both readings, S1318 (Whybrow 2008: about 30 % of the exercise deficit compensated over days 3-16; the replay reads 0.298) and S1320 with S1664 (Martin 2019: 53-89 % at 24 weeks by this plan's arithmetic, the plateau the gain sets), and about 0 the same day (S1312)

-- One lag step of dtH game hours with exKcal exercise kcal spent in it: L relaxes toward the step's rate (exKcal x 24
-- / dtH kcal per day). Nothing for no time; a non-finite L reads 0 and a negative or non-finite exKcal reads none.
function K.deficit.exerciseLag(L, exKcal, dtH)
    if L - L ~= 0 then
        L = 0
    end
    if not (dtH > 0) then
        return L
    end
    if exKcal - exKcal ~= 0 or exKcal < 0 then
        exKcal = 0
    end
    local k = math.exp(-dtH / (K.deficit.EX_LAG_TAU_D * 24))
    return L * k + exKcal * 24 / dtH * (1 - k)
end

-- The exercise deficit, kcal per day, that enters the energy state: EX_LAG_GAIN x L, non-negative and finite.
function K.deficit.lagged(L)
    if L - L ~= 0 or L < 0 then
        return 0
    end
    return K.deficit.EX_LAG_GAIN * L
end

-- Plan 11d Task 2 (spec § 5d, ruling 11d-4): the lag plateaus below the whole exercise share. lagged(L) is the gain
-- times L, so a steady exercise rate is compensated at EX_LAG_GAIN of it once the lag has caught up; the bypass ramp
-- in activityState still moves the lag toward the whole ex24h, unscaled by the gain.
K.deficit.EX_LAG_GAIN = 0.7 -- game choice, Plan 11d (ruling 11d-4): the plateau share, the middle of 53-89 % at 24 weeks (DLW): S1320's intake rise over S1664's achieved exercise EE a day, 90.7 / (17,114 / 168) = 0.89 and 123.6 / (38,956 / 168) = 0.53; the share is this plan's arithmetic on S1320 and S1664, not the paper's; S1516's self-report pool reads about 0 and is weighted lower

-- --- the bypass: a large total deficit raises hunger through the lag ------------------------------------------------
-- The energy state the writer hands to hungerTarget: the food balance (eb24h with the window's exercise kcal ex24h
-- added back) enters at once, the exercise share only through the lag. lagged(L) >= 0 and state falls with the
-- balance, so the activity never pushes the state below that of the same intake without it (S1330, S1331, S1332).
-- A negative or non-finite ex24h reads none. A 24-h total deficit bypasses the lag on a linear ramp: with ee24h the
-- 24-h expenditure and d = -eb24h / ee24h, the weight w = clamp((d - EX_BYPASS_LO) / (EX_BYPASS_HI - EX_BYPASS_LO), 0, 1)
-- moves the lag w of the way to ex24h (heavy work in a deficit raises hunger within days, S1325; ordinary exercise
-- stays compensated over weeks, S1312, S1318); it only ever raises the lag, so the never-below property holds. An
-- ee24h that is nil, non-finite or not positive bypasses nothing.
K.deficit.EX_BYPASS_LO = 0.282 -- game choice, ruling 11c-32 as amended (Plan 11c), refit from 0.30 (0.28 in Task 2c fix 1) on the shipped pipeline against Karl 2021 as reported (Plan 11f ruling 2b-3, widened search): the 24-h total-deficit share of the 24-h expenditure at which the exercise lag starts to be bypassed; S1325 (Karl 2021) gives the direction (its regression: a deficit of >= 25 % to raise appetite), S1312 (King 2011, steady state: within 0.92 mm of control, where a 25 % step reads 6.70 mm) and S1318 (Whybrow 2008: the high-exercise arms' 24-h deficit shares, 0.277 and 0.2814 of expenditure, 4.7 / 16.7 for the men's, compensate ~30 %, so both take a weight of 0) bound it from below (Plan 11f Task 2c fix 2: 0.282, from 0.28, which gave the men's arm 0.005); fitted with EX_BYPASS_HI, K.deficit.BALANCE_SPAN_KCAL and K.deficit.DEFICIT_FLOOR for the best worst-case margin over twin K's walk billings and battery (S1325)
K.deficit.EX_BYPASS_HI = 0.575 -- game choice, ruling 11c-32 as amended, refit from 0.45 on the shipped pipeline against Karl 2021 as reported (Plan 11f ruling 2b-3, widened search): the share at which the bypass is whole; fitted with EX_BYPASS_LO, K.deficit.BALANCE_SPAN_KCAL and K.deficit.DEFICIT_FLOOR: S1325 (Karl 2021 as the paper ran it, a 24-h deficit share of about 0.48, DEF +30.2 % against +26 %, and +20.4 to +35.8 % over the walk billed ClimbRope, Running10kmh or loaded Walking5kmh and no battery), S1312 (King 2011 at steady state, 0.92 mm) and S1318 (Whybrow 2008, unbypassed)
function K.deficit.activityState(eb24h, ex24h, L, fatDep, ee24h)
    local ex = 0
    if ex24h - ex24h == 0 and ex24h > 0 then
        ex = ex24h
    end
    local lag = K.deficit.lagged(L)
    if ee24h ~= nil and ee24h - ee24h == 0 and ee24h > 0 and eb24h - eb24h == 0 and lag < ex then
        local d = -eb24h / ee24h
        local w = K.clamp((d - K.deficit.EX_BYPASS_LO) / (K.deficit.EX_BYPASS_HI - K.deficit.EX_BYPASS_LO), 0, 1)
        lag = lag + w * (ex - lag)
    end
    return K.deficit.state(eb24h + ex - lag, fatDep)
end

-- --- the hunger target ---------------------------------------------------------------------------------------------
-- The hunger target from a fill-like scalar x (0 empty .. 1 sated: since Plan 11c the satiety read Z) and the energy
-- state (Plan 3 ruling 14, moved from the takeover's K.fast.hungerTarget): (1 - x) x energyState, plus a deficit
-- floor DEFICIT_FLOOR x (energyState - 1), clamped to [0, 1].
function K.deficit.hungerTarget(x, energyState)
    return K.clamp((1 - x) * energyState + K.deficit.DEFICIT_FLOOR * K.max(0, energyState - 1), 0, 1)
end

-- The inverse of hungerTarget inside its clamp: the unsated share (1 - x) a hunger reads at energyState, the deficit
-- floor taken off first. The caller guards a non-positive or non-finite energyState (K.satiety.seedMeal).
function K.deficit.unsated(hunger, energyState)
    return (hunger - K.deficit.DEFICIT_FLOOR * K.max(0, energyState - 1)) / energyState
end

K.deficit.DEFICIT_FLOOR = 0.02 -- game choice, refit on the shipped pipeline against Karl 2021 as reported (Plan 11f ruling 2b-3, widened search), from Plan 11f Task 2c's 0, Plan 11d's 1.0 (ruling 9c-1) and Plan 3 ruling 14's 0.15 (S1271 open): the deficit floor's coefficient, the hunger a deficit adds whatever the satiety read: fitted and weak (Task 2c's search read 0 and the widened search 0.02, a tie broken toward a floor above 0), and Plan 11d ruling 9c-1's floor role, keeping a deficit's hunger up at a full satiety read, is superseded in substance by the refit (Plan 11f ruling 2c-4); S1254 sets the deficit's direction, which the energy state also carries through (1 - x) x energyState; fitted with K.deficit.BALANCE_SPAN_KCAL 3100 and K.deficit.EX_BYPASS_LO 0.282 and EX_BYPASS_HI 0.575 on the server-path replays for the best worst-case margin over twin K's alternatives: S1325 (Karl 2021 as the paper ran it, DEF +30.2 % against +26 %), S1613 (the 36 h fast's next day 1.196 against 1.20) and S1614 (day 3 0.969 against 1.0); S1255 (CALERIE 2: < 10 mm over 2 y at a 25 % deficit) reads 6.7 mm under the request-anchored mapping, reproduced
