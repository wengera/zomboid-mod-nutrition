-- NR_Kernel_Drain.lua -- the remaining-fraction drain (Plan 17 Task 2; spec docs/superpowers/specs/2026-10-19-health-
-- combine-design.md, sections 1 and 2): every lethal state keeps a remaining fraction f, 1 at its onset and 0 at its
-- death point (S2231-S2262). Starvation and dehydration follow the curve f = 1 - ln(1 + a t) / ln(1 + a T), which opens
-- at vanilla's own level-4 drain rate (#0516, #0518, #2922) and tapers to the real death; the three deficiencies and
-- the sodium and iron rungs fall on a line to their death times. The minute's target health folds every active
-- fraction by the combine rule (worst only, multiply or add, K.drain.OPT.combine), and health falls toward it by at
-- most the sum of the active states' rates (health per game day). With no state active there is no target (vanilla
-- regeneration and the food heal resume; NR_Server_Effects).
-- The codes (the panel and the mirror read them): 1 starvation, 2 scurvy, 3 wet beriberi, 4 pellagra, 5 severe
-- hyponatraemia, 6 dehydration, 7 the iron lethal rung.
-- While a state is active and health sits under the target (a wound, vanilla's own terms, a target that rose as a
-- state ended), K.drain.heal returns vanilla's own regeneration toward the target, never above it (Plan 15 Task 4 fix
-- 1, the controller's ruling L2), so wounds still mend during a long deficiency.
-- The pace (K.drain.OPT.pace, spec section 2.2): Vanilla runs starvation and dehydration on vanilla's line from the
-- onset; Shortened on the curve over 336 and 48 game hours; Realistic starvation on the curve over the BMI progress
-- to BMI 12 (smoothed within the record day, spec section 1.2a) and Realistic dehydration on the curve over the
-- deficit from 4 % to 15 % (to a fraction of 0.1), then on a line to 0 at 17 %. The deficiencies and the rungs are the
-- same at every pace.
-- record.drain holds the inputs a save keeps (bmi0, naH, feH, starvation's clocks fedAgeH and acuteH, the hours in
-- the starvation and dehydration states stH and dhH, and the smoothed BMI clock pClose, pRate, pAt and pS;
-- K.store.INPUTS) and the minute's derived outputs (active, state, mask, target, frac, rate, drainThisMinute, starvedH
-- (the starvation clock: the unfed hours, or the onset plus the hours in the acute state), recentKcal, and the
-- starving, starveAcute and dehydrated flags the writer's caps read, K.hybrid.caps, Plan 15 Tasks 5 and 6). Pure: Lua
-- tables in and out, no Java. Slow-clock code with no fast region; every K.acute / K.fluids / K.HEIGHT_M / K.body
-- reference is at call time.
local K = NutritionRevamp.kernel
K.drain = {}

-- The state codes.
K.drain.STARVATION = 1 -- no row needed: a code
K.drain.SCURVY = 2 -- no row needed: a code
K.drain.BERIBERI = 3 -- no row needed: a code
K.drain.PELLAGRA = 4 -- no row needed: a code
K.drain.HYPONAT = 5 -- no row needed: a code
K.drain.DEHYD = 6 -- no row needed: a code
K.drain.IRON = 7 -- no row needed: a code
K.drain.N = 7 -- the state count, no row needed

-- The options (spec section 2): the pace and the combine rule, read once a server minute by the adapter, which
-- overwrites this table's fields in place (no allocation); dayMin is the server's day length in real minutes.
K.drain.PACE_VANILLA = 1 -- no row needed: an option value
K.drain.PACE_SHORT = 2 -- no row needed: an option value
K.drain.PACE_REAL = 3 -- no row needed: an option value
K.drain.COMBINE_WORST = 1 -- no row needed: an option value
K.drain.COMBINE_MULTIPLY = 2 -- no row needed: an option value
K.drain.COMBINE_ADD = 3 -- no row needed: an option value
K.drain.OPT = { pace = 3, combine = 2, dayMin = 90 } -- the defaults Realistic and Multiply: game choices (spec section 7); vanilla's 90-minute day (#2922)

K.drain.SLEEP_FLOOR = 10 -- health: at or below it vanilla wakes a sleeper every tick (#3900); the final stage starts here
K.drain.NONE = 100 -- health: the target read with no state active (full health), no row needed

-- The curve (spec section 1.2): vanilla's level-4 rates in health per game hour per real minute of day length, the
-- shortened death points, and the severity clocks' constants, calibrated so the default creation body, fasting with
-- water at the 90-minute day, opens at vanilla's rate (testing/artifacts/calibrate-drain-20261019/calibration.json).
K.drain.A_EPS = 1e-9 -- below it the curve is the line, no row needed
K.drain.R_HUNGER = 0.0396 -- health per game hour per real minute of day length: 3.3e-4 x 120 (#0516, #0518, #2922)
K.drain.R_THIRST = 0.198 -- health per game hour per real minute of day length: 1.65e-3 x 120 (#0516, #0518, #2922)
K.drain.SHORT_STARVE_H = 336 -- Shortened starvation, 14 game days: game choice (spec section 2.2)
K.drain.SHORT_DEHYD_H = 48 -- Shortened dehydration, 2 game days: game choice (spec section 2.2)
K.drain.A_STARVE = 509.81334200481825 -- game choice (spec section 1.2): calibrate-drain-20261019/calibration.json a_starve, the BMI progress clock (T = 1)
K.drain.STARVE_DPDT = 0.0004359462040936248 -- BMI progress per game hour before the state's first record-day close: calibrate-drain-20261019/calibration.json starve_dpdt_per_h, game choice (spec section 1.2a)
K.drain.A_DEHYD = 79.83361067025903 -- game choice (spec section 1.2): solved from calibrate-drain-20261019/calibration.json dehyd_dpdt_per_h for the 0.9 form f = 1 - 0.9 g(p) (ruling T1-1; the artifact's own a_dehyd is the full-span value)
K.drain.DEHYD_FINAL = 0.1 -- the fraction at the 15 % knee, dehydration's final stage (spec section 1.1)
K.drain.A_LO = 1e-9 -- the solver's bracket, no row needed
K.drain.A_HI = 1e9 -- the solver's bracket, no row needed
K.drain.A_ITER = 200 -- the solver's bisection steps on log a, no row needed
K.drain.ACACHE = {} -- solveA's cache by "T:r", a new entry only for a new day length or death time, no row needed
K.drain.AMEMO = {
    [1] = { r = 0, T = 0, a = 0 }, -- starvation's last solve, so a minute builds no cache key, no row needed
    [6] = { r = 0, T = 0, a = 0 }, -- dehydration's last solve, no row needed
}

-- Starvation: the acute onset (Plan 15 Task 6 fixes 1 and 2) at STARVE_ONSET_H unfed hours (K.drain.unfedH: the hours
-- since the meal pool last held K.hungerCurve.FED_M, counted continuously across days, sleep and restarts, never
-- offline), or, while the pool is under FED_M, the recent intake at RECENT_MIN_KCAL or less (K.drain.recentKcal: today
-- and the three closed record days with what is still in the stomach, a starvation diet of snacks); or the
-- chronic onset at a BMI under 13 whatever the intake (chronic semi-starvation, Plan 15 Task 4 fix 1, ruling M3); the
-- death at BMI 12.
K.drain.STARVE_ONSET_H = 30 -- unfed hours (the meal pool under K.hungerCurve.FED_M), counted continuously: game choice (spec section 10: each floor's curve), set so the onset coincides with the calibrated curve reaching its 0.69 cap, 29.9-30.3 h after the pool empties for 200-1,300 kcal meals, so Starving shows 33.6-35.1 h after the meal (vanilla 34.55 h)
K.drain.RECENT_TOL = 1e-6 -- kcal: the comparison's tolerance, no row needed (Plan 15 Task 6 fix 3: three absorbed 200 kcal snacks integrate a few 1e-9 kcal over 600)
K.drain.RECENT_DAYS = 3 -- record-day closes the window needs seen, no row needed
K.drain.RECENT_MIN_KCAL = 600 -- kcal absorbed or still in the stomach today and over the three closed record days (72-96 h): game choice (spec section 10: each floor's curve; the controller's Task 6 fix 1 and 2 rulings), about 200 kcal a day, at or under which the acute onset holds while the pool is unfed whatever the unfed hours, so a snack now and then does not keep a starving body out of the state (at or under: the window can hold three of a 200 kcal snack every 33 h, exactly 600)
K.drain.BMI_DEATH = 12 -- kg/m2, S2234 (Speakman: at BMI 12 recovery is virtually zero)
K.drain.BMI_CHRONIC = 13 -- kg/m2: starvation is active below it whatever the day's intake; game choice inside S2234's 12-13 (spec section 10: each floor's curve)
K.drain.SUSPEND_M = 236.44 -- weighted kcal, the meal pool a 200 kcal mixed snack lands (15/50/35 % of energy, 236.44 under the fitted weights, K.satiety.weigh): game choice (spec section 10: each floor's curve): only a meal spell (the pool reached SUSPEND_M and has not yet fallen under K.hungerCurve.FED_M, K.drain.mealFed) suspends the fallback or, inside the state, resets the unfed clock, so a floret an hour (11 kcal, the pool at FED_M for about 70 min) no longer ends or holds off a starving body's state, while a 200 kcal snack or a refeed meal still does for its whole fed spell (Plan 15 close, H1)
-- The starvation effect phases (spec section 3.3), on the starvation clock (starvedH: the unfed hours, then the onset
-- plus the hours in the acute state): weakness from onset, cold intolerance and slower healing from about day 3,
-- infection and mood from about day 14; a game-pacing choice (spec section 3.3; the day of onset of each is open, S2247;
-- glycogen gone by day 2-3, S2241).
K.drain.STARVE_PHASE_H = {
    30, -- phase 1, weakness: the drain's onset (STARVE_ONSET_H), game choice (open S2247)
    72, -- phase 2, cold and healing: day 3, game choice (open S2247; S2241 glycogen gone in 2-3 days)
    336, -- phase 3, infection and mood: day 14, game choice (open S2247)
}

-- Dehydration: onset at 4 %, where weariness and apathy begin; the curve to the final stage at 15 %, then a line to the
-- death point 17 % (Plan 15 Task 4 fix 1, ruling M1: on the water base's 3 % a day at rest, 4 % comes at about 32 h).
K.drain.DEHYD_ONSET = 4 -- per cent of body mass, weariness and apathy (S2248 4.2 %; the research's drain start): game choice (spec section 10: each floor's curve)
K.drain.DEHYD_KNEE = 15 -- per cent, the final stage from here: game choice (spec section 10: each floor's curve); S2248 painful urination at about 14.5 %
K.drain.DEHYD_DEATH = 17 -- per cent, the death point: game choice inside 15-19 % (spec section 10: dehydration's 17 % death point); S2248 anuria at about 19 %

-- The deficiencies: onset at the clinical grade (4); a line on the hours at that grade from 1 to 0 at the death time.
K.drain.CLINICAL = 4 -- the clinical grade, no row needed: a grade index
K.drain.BERIBERI_DEATH_H = 840 -- 5 weeks after clinical onset: S2255 (an inference: median 33 d to admission + < 48 h)
K.drain.SCURVY_DEATH_H = 2160 -- 90 days: game choice (spec section 10; the time to death is open, S1168)
K.drain.PELLAGRA_DEATH_H = 4320 -- 180 days: game choice (spec section 10; open S1170, the evidence says months to years)

-- The sodium and iron lethal rungs: their onsets kept (hyponatraemia grade 3, the iron rung 3), a line on the hours in
-- the state from 1 to 0 at their Plan 5 drain times (100 health over 6 h and 24 h).
K.drain.HYPONAT_GRADE = 3 -- the lethal hyponatraemia grade (K.fluids.hyponatGrade), no row needed: a grade index
K.drain.IRON_RUNG = 3 -- the iron lethal rung (S1033), no row needed: a rung index
K.drain.NA_DEATH_H = 6 -- hours: S1047 respiratory failure; game choice (spec section 10; open S1171)
K.drain.FE_DEATH_H = 24 -- hours: S1033; game choice (spec section 10; open S1173)

-- Per state, by code: its name, its onset (starved hours, deficit per cent, the clinical grade or the rung), its death
-- point (BMI, deficit per cent or hours since onset) and, for the two curve states, its Shortened death time in hours.
-- A state with no short is a line on its hours to death at every pace.
K.drain.states = {
    { name = "starvation", onset = K.drain.STARVE_ONSET_H, death = K.drain.BMI_DEATH, short = K.drain.SHORT_STARVE_H },
    { name = "scurvy", onset = K.drain.CLINICAL, death = K.drain.SCURVY_DEATH_H },
    { name = "beriberi", onset = K.drain.CLINICAL, death = K.drain.BERIBERI_DEATH_H },
    { name = "pellagra", onset = K.drain.CLINICAL, death = K.drain.PELLAGRA_DEATH_H },
    { name = "hyponatraemia", onset = K.drain.HYPONAT_GRADE, death = K.drain.NA_DEATH_H },
    { name = "dehydration", onset = K.drain.DEHYD_ONSET, death = K.drain.DEHYD_DEATH, short = K.drain.SHORT_DEHYD_H },
    { name = "iron", onset = K.drain.IRON_RUNG, death = K.drain.FE_DEATH_H },
}

-- The nutrient key each deficiency state reads.
K.drain.NUTRIENT = {
    [2] = "vitC", -- scurvy, no row needed
    [3] = "thiamine", -- wet beriberi, no row needed
    [4] = "niacin", -- pellagra, no row needed
}

-- A fresh record.drain: no state, no onset BMI, no hours in any state.
function K.drain.new()
    return {
        bmi0 = 0,
        naH = 0,
        feH = 0,
        stH = 0,
        dhH = 0,
        pClose = 0,
        pRate = 0,
        pS = 0,
        active = false,
        state = 0,
        mask = 0,
        target = K.drain.NONE,
        frac = {},
        rate = 0,
        drainThisMinute = 0,
        starvedH = 0,
        acuteH = 0,
        starving = false,
        starveAcute = false,
        dehydrated = false,
        spell = false,
    }
end

-- The stored numbers that heal to 0 when they are not finite.
K.drain.HEAL0 = { "bmi0", "naH", "feH", "stH", "dhH", "pClose", "pRate", "pS" }

-- record.drain, laid when absent; a stored input that is not a finite number heals to 0 (the anchor pAt and the stamp
-- fedAgeH to absent: first sight), and the fraction table is laid once.
function K.drain.ensure(record)
    local D = record.drain
    if type(D) ~= "table" then
        D = K.drain.new()
        record.drain = D
    end
    local H = K.drain.HEAL0
    -- HEAL0 is a kernel-built Lua array (no Java list), so # is its length
    for i = 1, #H do
        if not K.finite(D[H[i]]) then
            D[H[i]] = 0
        end
    end
    if not K.finite(D.acuteH) or D.acuteH < 0 then
        D.acuteH = 0
    end
    if D.fedAgeH ~= nil and not K.finite(D.fedAgeH) then
        D.fedAgeH = nil
    end
    if D.pAt ~= nil and not K.finite(D.pAt) then
        D.pAt = nil
    end
    if type(D.spell) ~= "boolean" then
        D.spell = false
    end
    if type(D.frac) ~= "table" then
        D.frac = {}
    end
    return D
end

-- The BMI of lm + fm at K.HEIGHT_M.
function K.drain.bmi(lm, fm)
    return (lm + fm) / (K.HEIGHT_M * K.HEIGHT_M)
end

-- The meal spell (Plan 15 close, H1): record.drain.spell, a stored input, set while the pool M is at
-- K.drain.SUSPEND_M or more and held until M falls under K.hungerCurve.FED_M, so a snack-sized pool or more opens a fed
-- spell that lasts as long as the curve's own, and a floret's pool, which never reaches SUSPEND_M, opens none. Updated
-- once a minute by K.drain.spellStep.
function K.drain.spellStep(D, M)
    if not K.finite(M) or M < K.hungerCurve.FED_M then
        D.spell = false
    elseif M >= K.drain.SUSPEND_M then
        D.spell = true
    end
end

-- Whether the pool M is fed by a meal spell: at FED_M or more with the spell open.
function K.drain.mealFed(D, M)
    return K.finite(M) and M >= K.hungerCurve.FED_M and D.spell == true
end

-- The hours since the meal pool was last fed (record.satiety.M at K.hungerCurve.FED_M or more; inside the acute state,
-- acuteH over 0, only a meal spell, K.drain.mealFed), counted continuously across days, sleep and restarts (record.drain.fedAgeH, a stored input, moved past an offline gap by
-- the resume, K.resume.STAMPS): a fed minute, a record seen for the first time (no stamp), a pool not yet seeded or a stamp
-- ahead of the minute stamps the world age and reads 0.
function K.drain.unfedH(D, sat, ageH)
    if not K.finite(ageH) then
        return 0
    end
    local M = nil
    if type(sat) == "table" then
        M = sat.M
    end
    local fed = K.finite(M) and M >= K.hungerCurve.FED_M
    if K.finite(D.acuteH) and D.acuteH > 0 then
        fed = K.drain.mealFed(D, M)                         -- inside the state only a meal spell is fed (H1)
    end
    if not K.finite(D.fedAgeH) or D.fedAgeH > ageH or not K.finite(M) or fed then
        D.fedAgeH = ageH
    end
    return K.max(0, ageH - D.fedAgeH)
end

-- The recent intake (Plan 15 Task 6 fixes 2 and 3): the kcal absorbed today (body.inDay) and over the three closed
-- record days (body.inDayClosed, inDay2 and inDay3, rotated at the day close, K.drain.closeDay), a window of 72-96 h
-- that the record calendar keeps, so an offline gap neither counts nor shifts it, plus the kcal eaten and still in the
-- stomach (stomach.buffer.calories, solid and liquid), so a meal counts in full from its eat and not only as it is
-- absorbed. nil until the body has seen RECENT_DAYS closes (body.recentDays, counted by closeDay; a loaded body's
-- defaulted closed day, K.store.closeDefault, is never counted) or while a day is not a number.
function K.drain.recentKcal(body, stomach)
    local n = body.recentDays
    if not K.finite(n) or n < K.drain.RECENT_DAYS then
        return nil
    end
    local a, b, c, d = body.inDay, body.inDayClosed, body.inDay2, body.inDay3
    if not (K.finite(a) and K.finite(b) and K.finite(c) and K.finite(d)) then
        return nil
    end
    local eaten = 0
    if type(stomach) == "table" and type(stomach.buffer) == "table" and K.finite(stomach.buffer.calories) then
        eaten = K.max(0, stomach.buffer.calories)
    end
    return a + b + c + d + eaten
end

-- The record day's close (NR_Server_Metabolism's, and the replays'): the closed days move down one, the closing day's
-- absorbed kcal into inDayClosed, and the closes seen (body.recentDays) count up to RECENT_DAYS.
function K.drain.closeDay(body)
    body.inDay3 = body.inDay2
    body.inDay2 = body.inDayClosed
    body.inDayClosed = body.inDay
    local n = body.recentDays
    if not K.finite(n) then
        n = 0
    end
    body.recentDays = K.min(K.drain.RECENT_DAYS, n + 1)
end

-- The starvation effect phase 0..3 of starved hours (K.drain.STARVE_PHASE_H).
function K.drain.starvePhase(h)
    local P = K.drain.STARVE_PHASE_H
    local n = 0
    -- STARVE_PHASE_H is a kernel-built Lua array (no Java list), so # is its length
    for i = 1, #P do
        if h >= P[i] then
            n = i
        end
    end
    return n
end

-- The curve (spec section 1.2): the remaining fraction at tau on a clock whose death point is T, 1 at 0 and 0 at T,
-- opening at a / ln(1 + a T) and flattening after; at a at or under A_EPS the line 1 - tau / T. tau clamps to [0, T].
function K.drain.curve(tau, T, a)
    if not (T > 0) then
        return 0
    end
    local t = K.clamp(tau, 0, T)
    if not (a > K.drain.A_EPS) then
        return 1 - t / T
    end
    return 1 - math.log(1 + a * t) / math.log(1 + a * T)
end

-- Vanilla's level-4 drain of state code in health per game hour at a day of dayMin real minutes (spec section 2.1):
-- the hunger term for starvation, the thirst term for dehydration, nil for every other state. A day length that is
-- not a positive number reads vanilla's 90 minutes.
function K.drain.rVanilla(code, dayMin)
    if not K.finite(dayMin) or dayMin <= 0 then
        dayMin = K.drain.DAY_MINUTES
    end
    if code == K.drain.STARVATION then
        return K.drain.R_HUNGER * dayMin
    end
    if code == K.drain.DEHYD then
        return K.drain.R_THIRST * dayMin
    end
    return nil
end

-- The time clock's a: the curve over T hours whose opening slope in health per game hour, 100 a / ln(1 + a T), is r.
-- 0 (the line) when r is at or under the line's own 100 / T. Bisection on log a over [A_LO, A_HI], cached by "T:r".
function K.drain.solveA(r, T)
    if not (r > K.drain.NONE / T) then
        return 0
    end
    local key = T .. ":" .. r
    local cached = K.drain.ACACHE[key]
    if cached ~= nil then
        return cached
    end
    local lo = math.log(K.drain.A_LO)
    local hi = math.log(K.drain.A_HI)
    for i = 1, K.drain.A_ITER do
        local mid = (lo + hi) / 2
        local x = math.exp(mid)
        if K.drain.NONE * x / math.log(1 + x * T) < r then
            lo = mid
        else
            hi = mid
        end
    end
    local a = math.exp((lo + hi) / 2)
    K.drain.ACACHE[key] = a
    return a
end

-- solveA through the state's memo, so a minute with the same rate and death time builds no cache key.
function K.drain.aFor(code, r, T)
    local m = K.drain.AMEMO[code]
    if m.r ~= r or m.T ~= T then
        m.a = K.drain.solveA(r, T)
        m.r = r
        m.T = T
    end
    return m.a
end

-- Starvation's BMI progress from the onset BMI bmi0 to the death BMI 12, clamped to [0, 1]; 1 when the onset is at or
-- under the death BMI.
function K.drain.progress(bmi0, bmi)
    local span = bmi0 - K.drain.BMI_DEATH
    if not (span > 0) then
        return 1
    end
    return K.clamp((bmi0 - bmi) / span, 0, 1)
end

-- The smoothed BMI clock (spec section 1.2a, ruling T1-4): the body moves BMI only at a record-day close, so the curve
-- reads p_s = pClose + pRate x (ageH - pAt). pClose is the true progress at the anchor; pAt is the anchor's world age,
-- the onset at first and then body.dayStartH at each close (a resume stamp, K.resume.STAMPS, as pAt is, so the two
-- move together past an offline gap and the clock counts online hours only); pRate is STARVE_DPDT until the state's
-- first close, then the closed day's progress per hour. A close is seen when body.dayStartH has moved past the anchor.
-- p_s clamps to [0, 1] and never falls within the state (pS keeps its largest), so a close's correction never raises
-- the target. Returns pS.
function K.drain.smooth(D, body, ageH)
    local p = K.drain.progress(D.bmi0, K.drain.bmi(body.lm, body.fm))
    local day = body.dayStartH
    if not K.finite(D.pAt) then
        D.pClose = p
        D.pRate = K.drain.STARVE_DPDT
        D.pAt = ageH
    elseif K.finite(day) and day > D.pAt then
        D.pRate = K.max(0, p - D.pClose) / K.body.DAY_H
        D.pClose = p
        D.pAt = day
    end
    local s = K.clamp(D.pClose + D.pRate * K.max(0, ageH - D.pAt), 0, 1)
    if K.finite(s) and s > D.pS then
        D.pS = s
    end
    return D.pS
end

-- Realistic dehydration's fraction at a deficit of d per cent (spec section 1.1): the curve from 1 at 4 % to 0.1 at
-- 15 %, f = 0.1 + 0.9 x curve, then the final stage, a line from 0.1 to 0 at 17 %.
function K.drain.dehydFraction(d)
    local D = K.drain
    if d >= D.DEHYD_KNEE then
        return D.DEHYD_FINAL * D.curve(d - D.DEHYD_KNEE, D.DEHYD_DEATH - D.DEHYD_KNEE, 0)
    end
    local p = (d - D.DEHYD_ONSET) / (D.DEHYD_KNEE - D.DEHYD_ONSET)
    return D.DEHYD_FINAL + (1 - D.DEHYD_FINAL) * D.curve(p, 1, D.A_DEHYD)
end

-- State code's remaining fraction and its rate in health per game day (spec sections 1.1, 1.4 and 2.2), at tH hours on
-- the state's time clock and inp the severity clocks (pStarve, the smoothed BMI progress; dehydPct, the deficit), under
-- opt (pace, dayMin). A line state falls from 1 to 0 at its death time at 100 x 24 / T a day. A curve state's rate is
-- vanilla's at the day length (the line's own when the Shortened curve degenerates to it). A fraction that is not a
-- finite number returns nil: the state is left out for the minute.
function K.drain.fraction(code, tH, inp, opt)
    local S = K.drain.states[code]
    local f = 0
    local rate = 0
    if S.short == nil then
        f = K.drain.curve(tH, S.death, 0)
        rate = K.drain.NONE * 24 / S.death
    else
        local r = K.drain.rVanilla(code, opt.dayMin)
        rate = r * 24
        if opt.pace == K.drain.PACE_VANILLA then
            f = K.drain.curve(tH, K.drain.NONE / r, 0)
        elseif opt.pace == K.drain.PACE_SHORT then
            f = K.drain.curve(tH, S.short, K.drain.aFor(code, r, S.short))
            rate = K.max(r, K.drain.NONE / S.short) * 24
        elseif code == K.drain.STARVATION then
            f = K.drain.curve(inp.pStarve, 1, K.drain.A_STARVE)
        else
            f = K.drain.dehydFraction(inp.dehydPct)
        end
    end
    if not K.finite(f) then
        return nil
    end
    return f, rate
end

-- One state's candidacy: when its fraction is a finite number, it joins frac, the code's bit, 2^(code - 1), joins the
-- mask of active states (the panel's drain lines, Plan 15 Task 9; each code is considered at most once a step), its
-- rate joins the sum, and the smallest fraction wins the state (a tie keeps the earlier code).
function K.drain.consider(D, code, tH, inp, opt)
    local f, rate = K.drain.fraction(code, tH, inp, opt)
    if f == nil then
        return
    end
    D.frac[code] = f
    D.mask = D.mask + 2 ^ (code - 1)
    if not D.active or f < D.frac[D.state] then
        D.state = code
    end
    D.rate = D.rate + rate
    D.active = true
end

-- One fraction folded into the accumulator by the combine rule c: worst keeps the least, add subtracts the loss,
-- multiply (the default, and any other value) multiplies.
function K.drain.fold(acc, f, c)
    if c == K.drain.COMBINE_WORST then
        return K.min(acc, f)
    end
    if c == K.drain.COMBINE_ADD then
        return acc - (1 - f)
    end
    return acc * f
end

-- The minute's target (spec section 1.3): 100 x the active fractions folded by opt.combine, floored at 0; 100 with no
-- state active. Writes and returns D.target.
function K.drain.combine(D, opt)
    D.target = K.drain.NONE
    if not D.active then
        return D.target
    end
    local acc = 1
    for code = 1, K.drain.N do
        local f = D.frac[code]
        if f ~= nil then
            acc = K.drain.fold(acc, f, opt.combine)
        end
    end
    D.target = K.drain.NONE * K.max(0, acc)
    return D.target
end

-- The deficiency state code's candidacy off its nutrient's clinical grade and its hours there.
function K.drain.deficiency(D, code, nut, inp, opt)
    local s = nut[K.drain.NUTRIENT[code]]
    if s ~= nil and s.g == K.drain.CLINICAL then
        K.drain.consider(D, code, s.ah, inp, opt)
    end
end

-- Starvation's clocks cleared when its state ends: the onset BMI, the hours in the state and the smoothed BMI clock.
function K.drain.release(D)
    D.bmi0 = 0
    D.stH = 0
    D.pClose = 0
    D.pRate = 0
    D.pS = 0
    D.pAt = nil
end

-- The input table the fractions read, laid once and overwritten each step (no allocation per minute).
K.drain.IN = { pStarve = 0, dehydPct = 0 }

-- One minute of dtM game minutes at world age ageH (nil reads record.nutrients.lastAgeH) under opt (nil reads
-- K.drain.OPT): every state's onset test, the clocks the record keeps (the onset BMI, the smoothed BMI clock, the hours
-- in the starvation, dehydration, sodium and iron states) and the outputs on record.drain: active, state (the code with
-- the smallest fraction), mask (every active code's bit, 2^(code - 1)), frac (each active code's fraction, nil when
-- inactive), target (K.drain.combine; 100 with none), rate (the sum of the active rates, health per game day),
-- drainThisMinute (rate x dtM / 1440, the most the minute may take; the adapter takes no more than health - target),
-- starvedH (the starvation clock: the unfed hours, K.drain.unfedH; while the acute state holds, at least the onset plus
-- its hours, acuteH), recentKcal (K.drain.recentKcal), and starving and
-- dehydrated: whether the starvation and the dehydration states are active, whichever fraction wins (the writer lifts its
-- HUNGER and THIRST caps on them, K.hybrid.caps); starveAcute: whether starvation came by the acute onset
-- (STARVE_ONSET_H unfed hours, or, while the pool is unfed, the recent intake at or under RECENT_MIN_KCAL; the clock
-- acuteH, the onset BMI and the starvation clocks are held through a fed spell while the recent intake stays that low,
-- so a snack does not reset the phases or the fraction, Plan 15 Task 6 fix 2), whose HUNGER minimum the chronic BMI
-- onset does not take (Plan 15 Task 6, ruling I2). overlay (Mode 2, Overlay: vanilla owns HUNGER and THIRST and its
-- own level-4 drains and deaths) leaves the starvation and dehydration states out, starving and dehydrated false, while
-- the starvation clock (starvedH, starveAcute, the effect phases) and the deficiency, sodium and iron states still run
-- (Plan 15 close, ruling M2). Returns record.drain.
function K.drain.step(record, dtM, ageH, overlay, opt)
    if opt == nil then
        opt = K.drain.OPT
    end
    local D = K.drain.ensure(record)
    local body, nut, fl, a = record.body, record.nutrients, record.fluids, record.acute
    D.active = false
    D.state = 0
    D.mask = 0
    D.target = K.drain.NONE
    D.rate = 0
    D.drainThisMinute = 0
    D.starvedH = 0
    D.starving = false
    D.starveAcute = false
    D.dehydrated = false
    for code = 1, K.drain.N do
        D.frac[code] = nil
    end
    if body == nil or nut == nil or fl == nil or a == nil then
        return D
    end
    if ageH == nil then
        ageH = nut.lastAgeH
    end
    local inp = K.drain.IN
    inp.dehydPct = fl.dehydPct
    local sat = record.satiety
    local M = nil
    if type(sat) == "table" then
        M = sat.M
    end
    K.drain.spellStep(D, M)
    local unfed = K.drain.unfedH(D, sat, ageH)
    D.recentKcal = K.drain.recentKcal(body, record.stomach)
    local low = D.recentKcal ~= nil and D.recentKcal <= K.drain.RECENT_MIN_KCAL + K.drain.RECENT_TOL
    local fedNow = K.drain.mealFed(D, M)
    D.starveAcute = unfed >= K.drain.STARVE_ONSET_H or (low and not fedNow)
    local held = false
    if D.starveAcute then
        D.starvedH = K.max(unfed, K.drain.STARVE_ONSET_H + D.acuteH)
        D.acuteH = D.acuteH + K.clamp(dtM, 0, 60) / 60
    else
        D.starvedH = unfed
        if low and D.acuteH > 0 then
            held = true                                    -- a snack's fed spell: the clock and the onset BMI wait
        else
            D.acuteH = 0
        end
    end
    local starve = D.starveAcute or K.drain.bmi(body.lm, body.fm) < K.drain.BMI_CHRONIC
    if starve and not overlay then
        if not (D.bmi0 > 0) then
            D.bmi0 = K.drain.bmi(body.lm, body.fm)
            D.pAt = nil
        end
        D.stH = D.stH + dtM / 60
        inp.pStarve = K.drain.smooth(D, body, ageH)
        K.drain.consider(D, K.drain.STARVATION, D.stH, inp, opt)
        D.starving = true
    elseif not held then
        K.drain.release(D)
    end
    K.drain.deficiency(D, K.drain.SCURVY, nut, inp, opt)
    K.drain.deficiency(D, K.drain.BERIBERI, nut, inp, opt)
    K.drain.deficiency(D, K.drain.PELLAGRA, nut, inp, opt)
    if K.fluids.hyponatGrade(fl.naPlasma) == K.drain.HYPONAT_GRADE then
        D.naH = D.naH + dtM / 60
        K.drain.consider(D, K.drain.HYPONAT, D.naH, inp, opt)
    else
        D.naH = 0
    end
    if fl.dehydPct >= K.drain.states[K.drain.DEHYD].onset and not overlay then
        D.dhH = D.dhH + dtM / 60
        K.drain.consider(D, K.drain.DEHYD, D.dhH, inp, opt)
        D.dehydrated = true
    else
        D.dhH = 0
    end
    local iron = nut.iron
    if iron ~= nil and iron.x == K.drain.IRON_RUNG then
        D.feH = D.feH + dtM / 60
        K.drain.consider(D, K.drain.IRON, D.feH, inp, opt)
    else
        D.feH = 0
    end
    K.drain.combine(D, opt)
    D.drainThisMinute = D.rate * dtM / 1440
    return D
end

-- The health the minute takes: drainThisMinute, never past the target (0 when health is at or under it or unknown).
function K.drain.take(D, health)
    if not D.active or not K.finite(health) then
        return 0
    end
    return K.clamp(health - D.target, 0, D.drainThisMinute)
end

-- Healing toward the target (Plan 15 Task 4 fix 1, ruling L2): vanilla's regeneration tier (#2721, #2353) and its
-- additions per multiplier unit (#2354); asleep, the sleeping addition, which HUNGRY or THIRST at level 4 zeroes (#0515).
K.drain.REGEN = {
    0.002, -- tier 0, the standard addition: VANILLA #2354
    0.0013, -- tier 1, the reduced addition (a HUNGRY, SICK or THIRST level 2): VANILLA #2354
    0.0008, -- tier 2, the severely reduced addition (a level 3, or SICK 4): VANILLA #2354
    0, -- tier 3, HUNGRY or THIRST at level 4: VANILLA #2721, #2353
}
K.drain.REGEN_SLEEPING = 0.02 -- VANILLA #2354
-- Multiplier units a game minute per real minute of day length: a game hour sums 120 x the day length's minutes (#2922).
K.drain.UNITS_PER_MIN = 2 -- 120 / 60, #2922
-- The day length in real minutes an adapter assumes when the sandbox is unreadable: vanilla's 90-minute default day.
K.drain.DAY_MINUTES = 90 -- VANILLA #2922, the fallback for an unreadable sandbox
-- AddGeneralHealth(y) with all 17 parts below 100 raises overall health by y x 5.05 / 17 (#3898).
K.drain.PART_SPREAD = 17 / 5.05 -- #3898
K.drain.HEAL_EPS = 0.01 -- health: under the target by less than this is at it, no row needed

-- Vanilla's regeneration addition per multiplier unit for the HUNGRY, THIRST and SICK moodle levels and sleep (#2721,
-- #2353, #0515): asleep the sleeping addition, 0 at HUNGRY or THIRST 4; awake a level 2 drops to the reduced tier, a 3
-- (or SICK 4) to the severely reduced, HUNGRY or THIRST 4 to none.
function K.drain.regenAddition(hungerLvl, thirstLvl, sickLvl, asleep)
    local starving = hungerLvl >= 4 or thirstLvl >= 4
    if asleep then
        if starving then
            return 0
        end
        return K.drain.REGEN_SLEEPING
    end
    local tier = 0
    if K.max(hungerLvl, K.max(thirstLvl, sickLvl)) >= 3 then
        tier = 2
    elseif K.max(hungerLvl, K.max(thirstLvl, sickLvl)) >= 2 then
        tier = 1
    end
    if starving then
        tier = 3
    end
    return K.drain.REGEN[tier + 1]
end

-- The AddGeneralHealth argument that heals health toward the active target over dtM game minutes at y a game minute
-- (vanilla's addition x the units a game minute), never past the target: 0 with no state, an unknown health or health
-- at the target (within HEAL_EPS).
function K.drain.heal(D, health, yPerMin, dtM)
    if not D.active or not K.finite(health) or not K.finite(yPerMin) then
        return 0
    end
    local gap = D.target - health
    if gap <= K.drain.HEAL_EPS then
        return 0
    end
    return K.clamp(yPerMin * dtM, 0, gap * K.drain.PART_SPREAD)
end
