-- NR_Kernel_Drain.lua -- the remaining-fraction drain (Plan 17 Task 2 and revision R1; spec docs/superpowers/specs/
-- 2026-10-19-health-combine-design.md, sections 1, 2 and 9): every lethal state keeps a remaining fraction f, 1 at its
-- onset and 0 at its death point (S2231-S2262), on a straight line on its own clock (revision R1: equitable total
-- punishment; the mod's other starvation effects carry the misery). The minute's target health folds every active
-- fraction by the combine rule (worst only, multiply or add, K.drain.OPT.combine), and health falls toward it by at
-- most the sum of the active states' rates (health per game day: each line's slope through its clock's current rate).
-- The target is a ceiling, and it rises only as the body recovers (revision R2, spec section 10): a state whose cause
-- has lapsed keeps its fraction while its clock is above its onset (recovering), every hour clock counts back down 1:1
-- in online game minutes while its cause is absent, and Realistic starvation keeps its onset BMI while its smoothed
-- progress, now free to fall as the body regains weight, is above 0; so a snack or a one-minute exit no longer
-- resets the ceiling to full. With no state active or recovering there is no target (vanilla regeneration and the
-- food heal resume; NR_Server_Effects).
-- The codes (the panel and the mirror read them): 1 starvation, 2 scurvy, 3 wet beriberi, 4 pellagra, 5 severe
-- hyponatraemia, 6 dehydration, 7 the iron lethal rung.
-- While a ceiling applies and health sits under it (a wound, vanilla's own terms, a ceiling that rose as the body
-- recovered), K.drain.heal returns vanilla's own regeneration toward it, never above it (Plan 15 Task 4 fix 1, the
-- controller's ruling L2), so wounds still mend during a long deficiency; vanilla's addition is 0 while HUNGRY or
-- THIRST shows level 4, so under starvation or dehydration a wound does not mend.
-- The pace (K.drain.OPT.pace, spec sections 2.2, 9 and 10): Vanilla runs starvation and dehydration on a line at
-- vanilla's level-4 rate on the hours in the state (#0516, #0518, #2922), Shortened on a line over SHORT_STARVE_H and SHORT_DEHYD_H (336, 48) such
-- hours, each clock counting back down while the cause is absent; Realistic starvation on a line over the BMI progress
-- to BMI_DEATH (12; smoothed within the record day, spec section 1.2a, both ways) and Realistic dehydration on a line over the
-- deficit from DEHYD_ONSET to DEHYD_DEATH (4 % to 17 %). The deficiencies and the rungs are the same at every pace.
-- record.drain holds the inputs a save keeps (bmi0, starvation's clocks fedAgeH and acuteH, the hour clocks of
-- K.drain.CLOCK, the smoothed BMI clock bClose, bRate, pAt and pS, and the last minute's deficit dPrev;
-- K.store.INPUTS) and the minute's derived outputs (active, state, mask, recovering, target, frac, rate,
-- drainThisMinute, starvedH (the starvation clock: the unfed hours, or the onset plus the hours in the acute state),
-- recentKcal, and the starving, starveAcute and dehydrated flags the writer's caps read, K.hybrid.caps, Plan 15 Tasks 5
-- and 6). Pure: Lua tables in and out, no Java. Slow-clock code with no fast region; every K.acute / K.fluids /
-- K.HEIGHT_M / K.body reference is at call time.
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

-- The day length in real minutes an adapter assumes when the sandbox is unreadable: vanilla's 90-minute default day.
K.drain.DAY_MINUTES = 90 -- VANILLA #2922: the fallback for an unreadable sandbox

-- The options (spec section 2): the pace and the combine rule, read once a server minute by the adapter, which
-- overwrites this table's fields in place (no allocation); dayMin is the server's day length in real minutes.
K.drain.PACE_VANILLA = 1 -- no row needed: an option value
K.drain.PACE_SHORT = 2 -- no row needed: an option value
K.drain.PACE_REAL = 3 -- no row needed: an option value
K.drain.COMBINE_WORST = 1 -- no row needed: an option value
K.drain.COMBINE_MULTIPLY = 2 -- no row needed: an option value
K.drain.COMBINE_ADD = 3 -- no row needed: an option value
K.drain.OPT = { pace = K.drain.PACE_REAL, combine = K.drain.COMBINE_MULTIPLY, dayMin = K.drain.DAY_MINUTES } -- the defaults Realistic and Multiply: game choices (spec section 7), the option file's NR.DeathPace and NR.HealthCombine defaults; vanilla's 90-minute day (#2922)

K.drain.SLEEP_FLOOR = 10 -- VANILLA #3900: health at or below which vanilla wakes a sleeper every tick, the last tenth of each line (spec section 9)
K.drain.NONE = 100 -- health: the target read with no state active (full health), no row needed

-- The paces (spec sections 2.2 and 9): vanilla's level-4 rates in health per game hour per real minute of day length,
-- the shortened death points, and the smoothed BMI clock's opening rate, read off the calibration's default creation
-- body fasting with water at the 90-minute day (testing/artifacts/calibrate-drain-20261019/calibration.json).
K.drain.R_HUNGER = 0.0396 -- VANILLA #0516 #0518 #2922: health per game hour per real minute of day length, 3.3e-4 x 120
K.drain.R_THIRST = 0.198 -- VANILLA #0516 #0518 #2922: health per game hour per real minute of day length, 1.65e-3 x 120
K.drain.SHORT_STARVE_H = K.dials.get("drain.SHORT_STARVE_H")
K.drain.SHORT_DEHYD_H = K.dials.get("drain.SHORT_DEHYD_H")
K.drain.STARVE_DPDT = K.dials.get("drain.STARVE_DPDT")
K.drain.CAL_BMI0 = K.dials.get("drain.CAL_BMI0")

-- Starvation: the acute onset (Plan 15 Task 6 fixes 1 and 2) at STARVE_ONSET_H unfed hours (K.drain.unfedH: the hours
-- since the meal pool last held K.hungerCurve.FED_M, counted continuously across days, sleep and restarts, never
-- offline), or, while the pool is under FED_M, the recent intake at RECENT_MIN_KCAL or less (K.drain.recentKcal: today
-- and the three closed record days with what is still in the stomach, a starvation diet of snacks); or the
-- chronic onset at a BMI under BMI_CHRONIC (13) whatever the intake (chronic semi-starvation, Plan 15 Task 4 fix 1, ruling M3); the
-- death at BMI_DEATH (12).
K.drain.STARVE_ONSET_H = K.dials.get("drain.STARVE_ONSET_H")
K.drain.RECENT_TOL = 1e-6 -- kcal: the comparison's tolerance, no row needed (Plan 15 Task 6 fix 3: three absorbed 200 kcal snacks integrate a few 1e-9 kcal over 600)
K.drain.RECENT_DAYS = 3 -- record-day closes the window needs seen, no row needed
K.drain.RECENT_MIN_KCAL = K.dials.get("drain.RECENT_MIN_KCAL")
K.drain.BMI_DEATH = K.dials.get("drain.BMI_DEATH")
K.drain.STARVE_DBMI = K.drain.STARVE_DPDT * (K.drain.CAL_BMI0 - K.drain.BMI_DEATH) -- BMI per game hour before the state's first close: the calibration body's opening rate in BMI, so a heavier body opens no faster in kg
K.drain.BMI_CHRONIC = K.dials.get("drain.BMI_CHRONIC")
K.drain.SUSPEND_M = K.dials.get("drain.SUSPEND_M")
-- The starvation effect phases (spec section 3.3), on the starvation clock (starvedH: the unfed hours, then the onset
-- plus the hours in the acute state): weakness from onset, cold intolerance and slower healing from about day 3,
-- infection and mood from about day 14; a game-pacing choice (spec section 3.3; the day of onset of each is open, S2247;
-- glycogen gone by day 2-3, S2241).
K.drain.STARVE_PHASE_H = {
    K.dials.get("drain.STARVE_PHASE_H.1"),
    K.dials.get("drain.STARVE_PHASE_H.2"),
    K.dials.get("drain.STARVE_PHASE_H.3"),
}

-- Dehydration: onset at 4 %, where weariness and apathy begin; a line to the death point 17 % (Plan 15 Task 4 fix 1,
-- ruling M1: on the water base's 3 % a day at rest, 4 % comes at about 32 h; revision R1: no knee, no final stage).
K.drain.DEHYD_ONSET = K.dials.get("drain.DEHYD_ONSET")
K.drain.DEHYD_DEATH = K.dials.get("drain.DEHYD_DEATH")

-- The deficiencies: onset at the clinical grade (4); a line on the hours at that grade from 1 to 0 at the death time.
K.drain.CLINICAL = 4 -- the clinical grade, no row needed: a grade index
K.drain.BERIBERI_DEATH_H = K.dials.get("drain.BERIBERI_DEATH_H")
K.drain.SCURVY_DEATH_H = K.dials.get("drain.SCURVY_DEATH_H")
K.drain.PELLAGRA_DEATH_H = K.dials.get("drain.PELLAGRA_DEATH_H")

-- The sodium and iron lethal rungs: their onsets kept (hyponatraemia grade 3, the iron rung 3), a line on the hours in
-- the state from 1 to 0 at their Plan 5 drain times (100 health over 6 h and 24 h).
K.drain.HYPONAT_GRADE = 3 -- the lethal hyponatraemia grade (K.fluids.hyponatGrade), no row needed: a grade index
K.drain.IRON_RUNG = 3 -- the iron lethal rung (S1033), no row needed: a rung index
K.drain.NA_DEATH_H = K.dials.get("drain.NA_DEATH_H")
K.drain.FE_DEATH_H = K.dials.get("drain.FE_DEATH_H")

-- Per state, by code: its name, its onset (starved hours, deficit per cent, the clinical grade or the rung), its death
-- point (BMI, deficit per cent or hours since onset) and, for the two paced states, its Shortened death time in hours.
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

-- Each state's hour clock on record.drain, by code (revision R2): the hours in the state, counted up while its cause is
-- present and back down 1:1 while it is absent, never under 0 (K.drain.hours). A deficiency's is the drain's own,
-- beside the nutrient model's hours at the grade (ah), which restart at 0 when the grade leaves clinical.
K.drain.CLOCK = { "stH", "scH", "bbH", "plH", "naH", "dhH", "feH" }

-- A fresh record.drain: no state, no onset BMI, no hours in any state.
function K.drain.new()
    return {
        bmi0 = 0,
        stH = 0,
        scH = 0,
        bbH = 0,
        plH = 0,
        naH = 0,
        dhH = 0,
        feH = 0,
        bClose = 0,
        bRate = 0,
        pS = 0,
        active = false,
        state = 0,
        mask = 0,
        recovering = 0,
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
K.drain.HEAL0 = { "bmi0", "stH", "scH", "bbH", "plH", "naH", "dhH", "feH", "bClose", "bRate", "pS" }
-- The hour clocks among them (K.drain.CLOCK), which also heal to 0 when negative (a corrupt negative clock would
-- lengthen a line).
K.drain.CLOCKS0 = K.drain.CLOCK

-- record.drain, laid when absent; a stored input that is not a finite number, or an hour clock under 0, heals to 0 (the
-- anchor pAt, the stamp fedAgeH and the last deficit dPrev to absent: first sight), and the fraction table is laid
-- once.
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
    local C = K.drain.CLOCKS0
    -- CLOCKS0 is a kernel-built Lua array (no Java list), so # is its length
    for i = 1, #C do
        if D[C[i]] < 0 then
            D[C[i]] = 0
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
    if D.dPrev ~= nil and not K.finite(D.dPrev) then
        D.dPrev = nil
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

-- The line (spec section 9): the remaining fraction at tau on a clock whose death point is T, 1 - tau / T, with tau
-- clamped to [0, T]; 0 with no span.
function K.drain.line(tau, T)
    if not (T > 0) then
        return 0
    end
    return 1 - K.clamp(tau, 0, T) / T
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

-- Starvation's BMI progress from the onset BMI bmi0 to the death BMI BMI_DEATH, clamped to [0, 1]; 1 when the onset is at or
-- under the death BMI.
function K.drain.progress(bmi0, bmi)
    local span = bmi0 - K.drain.BMI_DEATH
    if not (span > 0) then
        return 1
    end
    return K.clamp((bmi0 - bmi) / span, 0, 1)
end

-- The smoothed BMI clock (spec section 1.2a, rulings T1-4 and T2-1): the body moves BMI only at a record-day close, so
-- the line reads the estimate bmiEst = bClose - bRate x (ageH - pAt), anchored at the open record day's start pAt
-- (body.dayStartH, a resume stamp like pAt, K.resume.STAMPS). bClose is the BMI at the anchor; bRate is
-- STARVE_DBMI until the state's first close, then the last closed span's BMI change per hour, a loss positive and a
-- regain negative (revision R2: the clock runs both ways). The onset BMI bmi0 is the estimate at the onset, so the
-- progress opens at 0, and a close moves the estimate by the day-on-day change of the loss only. While the state is
-- active (active true) pS keeps the largest progress, so it never falls within the state. Once its cause has lapsed
-- the estimate extrapolates only toward recovery (ruling R2-2: a ceiling never falls between closes while its cause is absent): pS
-- keeps the smallest progress between closes, and a close (or a re-anchor) sets it to the true BMI's progress either
-- way, so a regained weight lowers it and a weight still lost raises it, the fall then ramping at the cap. Returns
-- pS and whether this minute closed (or re-anchored) the clock.
function K.drain.smooth(D, body, ageH, active)
    local bmi = K.drain.bmi(body.lm, body.fm)
    local day = body.dayStartH
    if not K.finite(day) then
        day = ageH
    end
    local closed = false
    if not K.finite(D.pAt) then
        D.bClose = bmi
        D.bRate = K.drain.STARVE_DBMI
        D.pAt = day
        closed = true
        if not (D.pS > 0) then
            D.bmi0 = K.drain.bmiEst(D, ageH)
        end
    elseif day > D.pAt then
        D.bRate = (D.bClose - bmi) / (day - D.pAt)
        D.bClose = bmi
        D.pAt = day
        closed = true
    end
    local s = K.drain.progress(D.bmi0, K.drain.bmiEst(D, ageH))
    if not K.finite(s) then
        s = D.pS                                           -- an estimate that is not a number leaves the progress as it was
    end
    if active then
        D.pS = K.max(D.pS, s)
    elseif closed then
        D.pS = s
    else
        D.pS = K.min(D.pS, s)
    end
    return D.pS, closed
end

-- The smoothed BMI at world age ageH: the anchor's BMI less its rate since.
function K.drain.bmiEst(D, ageH)
    return D.bClose - D.bRate * K.max(0, ageH - D.pAt)
end

-- The smoothed BMI clock's current rate in progress per game hour: bRate over the span bmi0 - BMI_DEATH (STARVE_DPDT for the
-- calibration body before its first close), or the progress dp the minute of dtM game minutes moved it when that is
-- more (a close's correction: the estimate steps by the day-on-day change of the loss, so health keeps up with the
-- line instead of trailing each step for the rest of the state). With no span (an onset at or under BMI_DEATH, already
-- dead on the line) the rate that runs the line at vanilla's own pace at the day length, so the cap still reaches 0.
function K.drain.pRate(D, dayMin, dp, dtM)
    local span = D.bmi0 - K.drain.BMI_DEATH
    if not (span > 0) then
        return K.drain.rVanilla(K.drain.STARVATION, dayMin) / K.drain.NONE
    end
    local r = D.bRate / span
    if dtM > 0 then
        r = K.max(r, dp * 60 / dtM)
    end
    return r
end

-- State code's remaining fraction and its rate in health per game day (spec sections 1.1, 2.2 and 9), at tH hours on
-- the state's time clock and inp the severity clocks (pStarve, the smoothed BMI progress, and pRate, its rate a game
-- hour; dehydPct, the deficit, and dRise, its rise a game hour), under opt (pace, dayMin). Every state is a line from 1
-- to 0 on its clock, and its rate is the line's slope through the clock's current rate, 100 x 24 x (clock units a game
-- hour) / T: a time clock runs an hour an hour (a deficiency or rung over its death time at every pace; Vanilla over
-- vanilla's 100 / r hours at the day length; Shortened over SHORT_STARVE_H and SHORT_DEHYD_H); Realistic starvation runs on the BMI
-- progress to 1, Realistic dehydration on the deficit from DEHYD_ONSET to DEHYD_DEATH. A fraction or rate that is not a finite number
-- returns nil: the state is left out for the minute.
function K.drain.fraction(code, tH, inp, opt)
    local S = K.drain.states[code]
    local T = S.death
    local clock = tH
    local perH = 1
    if S.short ~= nil then
        if opt.pace == K.drain.PACE_VANILLA then
            T = K.drain.NONE / K.drain.rVanilla(code, opt.dayMin)
        elseif opt.pace == K.drain.PACE_SHORT then
            T = S.short
        elseif code == K.drain.STARVATION then
            T = 1
            clock = inp.pStarve
            perH = inp.pRate
        else
            T = K.drain.DEHYD_DEATH - K.drain.DEHYD_ONSET
            clock = inp.dehydPct - K.drain.DEHYD_ONSET
            perH = inp.dRise
        end
    end
    local f = K.drain.line(clock, T)
    local rate = K.drain.NONE * 24 * perH / T
    if not (K.finite(f) and K.finite(rate)) then
        return nil
    end
    return f, rate
end

-- One state's candidacy: when its fraction is a finite number, it joins frac and its ceiling applies (active); the
-- code's bit, 2^(code - 1), joins the mask of active states, or, for a state whose cause has lapsed (rec true), the
-- recovering mask (the panel's drain lines, Plan 15 Task 9; each code is considered at most once a step); the smallest
-- fraction wins the state (a tie keeps the earlier code). Its rate joins the sum while its fraction can fall: an
-- active state always, a recovering one only while its ceiling can still fall (rec with falling: a recovering hour
-- clock only counts down, so only Realistic starvation's, whose next close can book a weight still lost). A
-- paced state's rate is at least vanilla's level-4 rate at the day length, so health above a line, after a pace
-- switch, closes on it as a ramp.
function K.drain.consider(D, code, tH, inp, opt, rec, falling)
    local f, rate = K.drain.fraction(code, tH, inp, opt)
    if f == nil then
        return
    end
    D.frac[code] = f
    if rec then
        D.recovering = D.recovering + 2 ^ (code - 1)
    else
        D.mask = D.mask + 2 ^ (code - 1)
    end
    if not D.active or f < D.frac[D.state] then
        D.state = code
    end
    D.active = true
    if rec and not falling then
        return
    end
    local rv = K.drain.rVanilla(code, opt.dayMin)
    if rv ~= nil then
        rate = K.max(rate, rv * 24)                -- a paced state's cap is at least vanilla's level-4 rate: a gap above the line closes (review F1)
    end
    D.rate = D.rate + rate
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

-- The minute's target (spec sections 1.3 and 10): 100 x the active and recovering fractions folded by opt.combine,
-- floored at 0; 100 with no ceiling applied. Writes and returns D.target.
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

-- An hour clock h after dtM game minutes with its cause absent: back down 1:1, never under 0 (revision R2).
function K.drain.down(h, dtM)
    return K.max(0, h - dtM / 60)
end

-- An hour-clock state's minute (the sodium and iron rungs; starvation and dehydration at the Vanilla and Shortened
-- paces read the same clocks): with its cause present its clock counts up and the state is active; absent, the clock
-- counts back down and the state recovers while it is above 0, its ceiling rising as the clock falls.
function K.drain.hours(D, code, present, inp, opt, dtM)
    local k = K.drain.CLOCK[code]
    if present then
        D[k] = D[k] + dtM / 60
        K.drain.consider(D, code, D[k], inp, opt, false, true)
        return
    end
    D[k] = K.drain.down(D[k], dtM)
    if D[k] > 0 then
        K.drain.consider(D, code, D[k], inp, opt, true, false)
    end
end

-- The deficiency state code's minute off its nutrient's clinical grade: at clinical the state is active on the drain's
-- own clock, never behind the nutrient's hours at the grade (ah: a record seeded or first seen at clinical), which then
-- counts the minute; under clinical the clock counts back down and the state recovers while it is above 0 (K.drain.hours).
function K.drain.deficiency(D, code, nut, inp, opt, dtM)
    local s = nut[K.drain.NUTRIENT[code]]
    local k = K.drain.CLOCK[code]
    if s ~= nil and s.g == K.drain.CLINICAL then
        local ah = s.ah
        if not K.finite(ah) then
            ah = 0
        end
        local h = K.max(D[k], ah)
        K.drain.consider(D, code, h, inp, opt, false, true)
        D[k] = h + dtM / 60
        return
    end
    K.drain.hours(D, code, false, inp, opt, dtM)
end

-- Starvation's smoothed BMI clock released (revision R2: only once its progress is back at 0, or under Overlay): the
-- onset BMI and the clock's anchor, rate and progress.
function K.drain.release(D)
    D.bmi0 = 0
    D.bClose = 0
    D.bRate = 0
    D.pS = 0
    D.pAt = nil
end

-- Starvation's minute (spec sections 1.2a, 9 and 10). on: the acute or chronic onset holds (never under Overlay, where
-- vanilla owns starvation and the clocks are released). Active, the onset BMI is stamped once, the hours count up and
-- the progress never falls. Lapsed, the hours count back down and, while an onset BMI is held, the progress only
-- falls between closes and takes the true BMI's at each (ruling R2-2), the onset BMI released at a close that books it
-- back at 0 (a lapse at the onset's own progress of 0 keeps it to the close, so a fed spell reads one span),
-- and a close's rise ramps at vanilla's level-4 rate (the R1-5 floor); the state recovers while its own
-- clock is above its onset: the progress at Realistic pace, the hours at Vanilla and Shortened. Writes inp.pStarve and
-- inp.pRate.
function K.drain.starvation(D, body, ageH, dtM, on, overlay, inp, opt)
    inp.pStarve = 0
    inp.pRate = 0
    if overlay then
        K.drain.release(D)
        D.stH = 0
        return
    end
    if on then
        if not (D.bmi0 > 0) then
            D.bmi0 = K.drain.bmi(body.lm, body.fm)
            D.pAt = nil
        end
        D.stH = D.stH + dtM / 60
    else
        D.stH = K.drain.down(D.stH, dtM)
    end
    local p0 = D.pS
    local closed = false
    if D.bmi0 > 0 then
        inp.pStarve, closed = K.drain.smooth(D, body, ageH, on)
        inp.pRate = K.drain.pRate(D, opt.dayMin, inp.pStarve - p0, dtM)
    end
    if not on then
        inp.pRate = 0                                      -- lapsed: a close's fall ramps at the vanilla floor (ruling R2-2)
    end
    if on then
        K.drain.consider(D, K.drain.STARVATION, D.stH, inp, opt, false, true)
        D.starving = true
        return
    end
    if closed and not (D.pS > 0) then
        K.drain.release(D)                                 -- a close booked the progress back at 0
    end
    if opt.pace == K.drain.PACE_REAL then
        if D.pS > 0 then
            K.drain.consider(D, K.drain.STARVATION, D.stH, inp, opt, true, true)
        end
    elseif D.stH > 0 then
        K.drain.consider(D, K.drain.STARVATION, D.stH, inp, opt, true, false)
    end
end

-- Dehydration's minute (spec sections 9 and 10): active at the onset deficit (never under Overlay, where vanilla owns
-- it and the hours clear); under it the hours count back down, and at the Vanilla and Shortened paces the state
-- recovers while they are above 0. At Realistic pace the line follows the deficit both ways, so under the onset its
-- fraction is 1 and nothing recovers.
function K.drain.dehydration(D, d, overlay, inp, opt, dtM)
    if overlay then
        D.dhH = 0
        return
    end
    local present = d >= K.drain.DEHYD_ONSET
    if present then
        D.dehydrated = true
    elseif opt.pace == K.drain.PACE_REAL then
        D.dhH = K.drain.down(D.dhH, dtM)
        return
    end
    K.drain.hours(D, K.drain.DEHYD, present, inp, opt, dtM)
end

-- The deficit's rise in per cent a game hour since the last minute's read (record.drain.dPrev), floored at 0; with no
-- last read (a fresh or healed record) it counts from the onset DEHYD_ONSET, so a record first seen in the state lands
-- on its line in its first minute (ruling R1-3; K.drain.take never passes the target); 0 with no time passed. Stores
-- the minute's deficit (absent when it is not a number) for the next.
function K.drain.rise(D, d, dtM)
    local r = 0
    if K.finite(d) and dtM > 0 then
        local prev = D.dPrev
        if not K.finite(prev) then
            prev = K.min(d, K.drain.DEHYD_ONSET)
        end
        r = K.max(0, d - prev) * 60 / dtM
    end
    D.dPrev = nil
    if K.finite(d) then
        D.dPrev = d
    end
    return r
end

-- The input table the fractions read, laid once and overwritten each step (no allocation per minute).
K.drain.IN = { pStarve = 0, pRate = 0, dehydPct = 0, dRise = 0 }

-- One minute of dtM game minutes at world age ageH (nil reads record.nutrients.lastAgeH) under opt (nil reads
-- K.drain.OPT): every state's onset test, the clocks the record keeps (the onset BMI, the smoothed BMI clock, the last
-- minute's deficit, the hour clocks K.drain.CLOCK) and the outputs on record.drain: active (a ceiling applies: a state
-- is active or recovering, revision R2; the adapter then owns health through K.drain.take and K.drain.heal), state
-- (the code with the smallest fraction among them), mask (every active code's bit, 2^(code - 1)), recovering (every
-- recovering code's bit: its cause has lapsed and its ceiling still applies), frac (each applied code's fraction, nil
-- otherwise), target (K.drain.combine; 100 with none), rate (the sum of the rates of the states whose fraction can
-- fall this minute, health per game day), drainThisMinute (rate x dtM / 1440, the most the minute may take; the
-- adapter takes no more than health - target), starvedH (the starvation clock: the unfed hours, K.drain.unfedH; while
-- the acute state holds, at least the onset plus its hours, acuteH), recentKcal (K.drain.recentKcal), and starving and
-- dehydrated: whether the starvation and the dehydration states are active, whichever fraction wins (the writer lifts
-- its HUNGER and THIRST caps on them, K.hybrid.caps; a recovering state lifts nothing); starveAcute: whether starvation
-- came by the acute onset (STARVE_ONSET_H unfed hours, or, while the pool is unfed, the recent intake at or under
-- RECENT_MIN_KCAL; the clock acuteH is held through a fed spell while the recent intake stays that low, so a snack
-- does not reset the effect phases, Plan 15 Task 6 fix 2), whose HUNGER minimum the chronic BMI onset does not take
-- (Plan 15 Task 6, ruling I2). overlay (Mode 2, Overlay: vanilla owns HUNGER and THIRST and its own level-4 drains and
-- deaths) leaves the starvation and dehydration states out, starving and dehydrated false, while the starvation clock
-- (starvedH, starveAcute, the effect phases) and the deficiency, sodium and iron states still run (Plan 15 close,
-- ruling M2). Returns record.drain.
function K.drain.step(record, dtM, ageH, overlay, opt)
    if opt == nil then
        opt = K.drain.OPT
    end
    local D = K.drain.ensure(record)
    local body, nut, fl, a = record.body, record.nutrients, record.fluids, record.acute
    D.active = false
    D.state = 0
    D.mask = 0
    D.recovering = 0
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
    inp.dRise = K.drain.rise(D, fl.dehydPct, dtM)
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
    if D.starveAcute then
        D.starvedH = K.max(unfed, K.drain.STARVE_ONSET_H + D.acuteH)
        D.acuteH = D.acuteH + K.clamp(dtM, 0, 60) / 60
    else
        D.starvedH = unfed
        if not (low and D.acuteH > 0) then
            D.acuteH = 0                                   -- a snack's fed spell while the intake stays low holds the phases' clock
        end
    end
    local starve = D.starveAcute or K.drain.bmi(body.lm, body.fm) < K.drain.BMI_CHRONIC
    K.drain.starvation(D, body, ageH, dtM, starve and not overlay, overlay, inp, opt)
    K.drain.deficiency(D, K.drain.SCURVY, nut, inp, opt, dtM)
    K.drain.deficiency(D, K.drain.BERIBERI, nut, inp, opt, dtM)
    K.drain.deficiency(D, K.drain.PELLAGRA, nut, inp, opt, dtM)
    K.drain.hours(D, K.drain.HYPONAT, K.fluids.hyponatGrade(fl.naPlasma) == K.drain.HYPONAT_GRADE, inp, opt, dtM)
    K.drain.dehydration(D, fl.dehydPct, overlay, inp, opt, dtM)
    local iron = nut.iron
    K.drain.hours(D, K.drain.IRON, iron ~= nil and iron.x == K.drain.IRON_RUNG, inp, opt, dtM)
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
    0.002, -- VANILLA #2354: tier 0, the standard addition
    0.0013, -- VANILLA #2354: tier 1, the reduced addition (a HUNGRY, SICK or THIRST level 2)
    0.0008, -- VANILLA #2354: tier 2, the severely reduced addition (a level 3, or SICK 4)
    0, -- VANILLA #2721 #2353: tier 3, HUNGRY or THIRST at level 4
}
K.drain.REGEN_SLEEPING = 0.02 -- VANILLA #2354
-- Multiplier units a game minute per real minute of day length: a game hour sums 120 x the day length's minutes (#2922).
K.drain.UNITS_PER_MIN = 2 -- VANILLA #2922: 120 / 60
-- AddGeneralHealth(y) with all 17 parts below 100 raises overall health by y x 5.05 / 17 (#3898).
K.drain.PART_SPREAD = 17 / 5.05 -- VANILLA #3898
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

-- The copies laid at load from the dials (Plan 19 Task 3g): STARVE_DBMI and each state's onset, death and short read
-- their fields once, as this file loads. K.drain.derive lays them again from the fields, so a dial written after load
-- (K.dials.apply's derive on an option change, replay_live.set_constants) reaches every output that reads a copy; it
-- computes exactly what the load-time lines above computed.
function K.drain.derive()
    K.drain.STARVE_DBMI = K.drain.STARVE_DPDT * (K.drain.CAL_BMI0 - K.drain.BMI_DEATH)
    local S = K.drain.states
    S[K.drain.STARVATION].onset = K.drain.STARVE_ONSET_H
    S[K.drain.STARVATION].death = K.drain.BMI_DEATH
    S[K.drain.STARVATION].short = K.drain.SHORT_STARVE_H
    S[K.drain.SCURVY].death = K.drain.SCURVY_DEATH_H
    S[K.drain.BERIBERI].death = K.drain.BERIBERI_DEATH_H
    S[K.drain.PELLAGRA].death = K.drain.PELLAGRA_DEATH_H
    S[K.drain.HYPONAT].death = K.drain.NA_DEATH_H
    S[K.drain.DEHYD].onset = K.drain.DEHYD_ONSET
    S[K.drain.DEHYD].death = K.drain.DEHYD_DEATH
    S[K.drain.DEHYD].short = K.drain.SHORT_DEHYD_H
    S[K.drain.IRON].death = K.drain.FE_DEATH_H
end
