-- NR_Kernel_Drain.lua -- the drain-and-floor engine (Plan 15 Task 4; spec section 3.2): every lethal state drains
-- overall health at its own rate, health per game day, down to a floor; the floor deepens with the state's severity or
-- its time since onset and reaches 0 at the state's death point (S2231-S2262). A drain signals damage, not lethality:
-- the first floor (50) is vanilla-paced and every floor stays above 10, where vanilla wakes a sleeper on every tick
-- (#3900), until the state's final stage. Several states at once: the lowest floor wins and the fastest rate drains.
-- With no state active there is no floor (vanilla regeneration and the food heal resume; NR_Server_Effects).
-- The codes (the panel and the mirror read them): 1 starvation, 2 scurvy, 3 wet beriberi, 4 pellagra, 5 severe
-- hyponatraemia, 6 dehydration, 7 the iron lethal rung.
-- While a state is active and health sits under its floor (a wound, vanilla's own terms, a floor that rose as a deficit
-- eased), K.drain.heal returns vanilla's own regeneration toward the floor, never above it (Plan 15 Task 4 fix 1, the
-- controller's ruling L2), so wounds still mend during a long deficiency.
-- The clocks: starvation's floor follows BMI (lm + fm over K.HEIGHT_M squared) from its onset BMI, so a heavier
-- body, whose BMI falls more slowly for the same loss, lives longer (S2235's direction); dehydration's follows the
-- body-water deficit; the three deficiencies' follow the hours at the clinical grade (nutrients.<key>.ah); the sodium
-- and iron rungs' follow the record's own hours in the state (record.drain.naH, feH). The rates are per game day and
-- independent of day length.
-- record.drain holds the inputs a save keeps (bmi0, naH, feH, and starvation's clocks fedAgeH and acuteH;
-- K.store.INPUTS) and the minute's derived outputs (active, state, targetFloor, rate, drainThisMinute, starvedH (the
-- starvation clock: the unfed hours, or the onset plus the hours in the acute state), recentKcal, and the starving,
-- starveAcute and dehydrated flags the writer's caps read, K.hybrid.caps, Plan 15 Tasks 5 and 6). Pure: Lua tables in and out, no Java. Slow-clock code
-- with no fast region; every K.acute / K.fluids / K.HEIGHT_M reference is at call time.
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

-- The shared floor shape.
K.drain.FIRST_FLOOR = 50 -- health: the vanilla-paced first floor; game choice (spec section 10: each floor's curve)
K.drain.SLEEP_FLOOR = 10 -- health: at or below it vanilla wakes a sleeper every tick (#3900); the final stage starts here
K.drain.NONE = 100 -- health: the floor read with no state active (full health), no row needed

-- Starvation: the acute onset (Plan 15 Task 6 fixes 1 and 2) at STARVE_ONSET_H unfed hours (K.drain.unfedH: the hours
-- since the meal pool last held K.hungerCurve.FED_M, counted continuously across days, sleep and restarts, never
-- offline), or, while the pool is under FED_M, the recent intake at RECENT_MIN_KCAL or less (K.drain.recentKcal: today
-- and the three closed record days with what is still in the stomach, a starvation diet of snacks); or the
-- chronic onset at a BMI under 13 whatever the intake (chronic semi-starvation, Plan 15 Task 4 fix 1, ruling M3); the
-- floor by BMI, 10 + 40 x clamp((BMI - 12.5) / (BMI0 - 12.5), 0, 1) above 12.5, then linear to 0 at BMI 12.
K.drain.STARVE_ONSET_H = 30 -- unfed hours (the meal pool under K.hungerCurve.FED_M), counted continuously: game choice (spec section 10: each floor's curve), set so the onset coincides with the calibrated curve reaching its 0.69 cap, 29.9-30.3 h after the pool empties for 200-1,300 kcal meals, so Starving shows 33.6-35.1 h after the meal (vanilla 34.55 h)
K.drain.RECENT_TOL = 1e-6 -- kcal: the comparison's tolerance, no row needed (Plan 15 Task 6 fix 3: three absorbed 200 kcal snacks integrate a few 1e-9 kcal over 600)
K.drain.RECENT_DAYS = 3 -- record-day closes the window needs seen, no row needed
K.drain.RECENT_MIN_KCAL = 600 -- kcal absorbed today and over the three closed record days (72-96 h): game choice (spec section 10: each floor's curve; the controller's Task 6 fix 1 and 2 rulings), about 200 kcal a day, at or under which the acute onset holds while the pool is unfed whatever the unfed hours, so a snack now and then does not keep a starving body out of the state (at or under: the window can hold three of a 200 kcal snack every 33 h, exactly 600)
K.drain.BMI_KNEE = 12.5 -- kg/m2, the floor reaches 10 here: game choice inside S2234's 12-13 (spec section 10)
K.drain.BMI_DEATH = 12 -- kg/m2, S2234 (Speakman: at BMI 12 recovery is virtually zero)
K.drain.BMI_CHRONIC = 13 -- kg/m2: starvation is active below it whatever the day's intake; game choice inside S2234's 12-13 (spec section 10: each floor's curve)
K.drain.STARVE_RATE = 25 -- health per game day, 50 in about 2 days from onset: game choice (spec section 10)
-- The starvation effect phases (spec section 3.3), on the starvation clock (starvedH: the unfed hours, then the onset
-- plus the hours in the acute state): weakness from onset, cold intolerance and slower healing from about day 3,
-- infection and mood from about day 14; a game-pacing choice (spec section 3.3; the day of onset of each is open, S2247;
-- glycogen gone by day 2-3, S2241).
K.drain.STARVE_PHASE_H = {
    30, -- phase 1, weakness: the drain's onset (STARVE_ONSET_H), game choice (open S2247)
    72, -- phase 2, cold and healing: day 3, game choice (open S2247; S2241 glycogen gone in 2-3 days)
    336, -- phase 3, infection and mood: day 14, game choice (open S2247)
}

-- Dehydration: onset at 4 %, where weariness and apathy begin, the floor by body-water deficit (per cent of body mass):
-- 50 at 4 %, linear to 10 at 15 %, then to 0 at the death point 17 % (Plan 15 Task 4 fix 1, ruling M1: on the water
-- base's 3 % a day at rest, 4 % comes at about 32 h and the first floor of 50 at about 38 h, near vanilla's pace).
K.drain.DEHYD_KNOTS = {
    { 4, 50 }, -- the onset at about 4 %, weariness and apathy (S2248 4.2 %; the research's drain start): game choice (spec section 10: each floor's curve)
    { 15, 10 }, -- the final stage from 15 %: game choice (spec section 10: each floor's curve); S2248 painful urination at about 14.5 %
    { 17, 0 }, -- the death point 17 %: game choice inside 15-19 % (spec section 10: dehydration's 17 % death point); S2248 anuria at about 19 %
}
K.drain.DEHYD_RATE = 200 -- health per game day, 50 in about 6 h from onset: game choice (spec section 10: each floor's drain rate)

-- The deficiencies: onset at the clinical grade (4); the floor by hours at that grade: 50 for the first 3 days, linear
-- to 10 two days before death, then to 0 at the death point.
K.drain.CLINICAL = 4 -- the clinical grade, no row needed: a grade index
K.drain.DEF_HOLD_H = 72 -- 3 days at the first floor: game choice (spec section 10)
K.drain.DEF_FINAL_H = 48 -- the last 2 days, 10 to 0: game choice (spec section 10); S2255 death within 48 h of admission
K.drain.BERIBERI_DEATH_H = 840 -- 5 weeks after clinical onset: S2255 (an inference: median 33 d to admission + < 48 h)
K.drain.SCURVY_DEATH_H = 2160 -- 90 days: game choice (spec section 10; the time to death is open, S1168)
K.drain.PELLAGRA_DEATH_H = 4320 -- 180 days: game choice (spec section 10; open S1170, the evidence says months to years)
K.drain.DEF_RATE = 50 / 3 -- health per game day, 50 in about 3 days: game choice (spec section 10)

-- The sodium and iron lethal rungs: their onsets kept (hyponatraemia grade 3, the iron rung 3), the death time their
-- Plan 5 drain time (100 health over 6 h and 24 h), the floor 50 at onset, linear to 10 two hours before death.
K.drain.HYPONAT_GRADE = 3 -- the lethal hyponatraemia grade (K.fluids.hyponatGrade), no row needed: a grade index
K.drain.IRON_RUNG = 3 -- the iron lethal rung (S1033), no row needed: a rung index
K.drain.NA_DEATH_H = 6 -- hours: S1047 respiratory failure; game choice (spec section 10; open S1171)
K.drain.FE_DEATH_H = 24 -- hours: S1033; game choice (spec section 10; open S1173)
K.drain.ACUTE_FINAL_H = 2 -- hours from 10 to 0: game choice (spec section 10)

-- The time-clock knots { hours, floor } of a state with death at T: a hold at the first floor, the knee at 10 the final
-- stage before death, 0 at T.
function K.drain.timeKnots(hold, T, final)
    local D = K.drain
    local kn = {}
    kn[1] = { 0, D.FIRST_FLOOR }
    if hold > 0 then
        kn[#kn + 1] = { hold, D.FIRST_FLOOR }
    end
    kn[#kn + 1] = { T - final, D.SLEEP_FLOOR }
    kn[#kn + 1] = { T, 0 }
    return kn
end

-- Per state, by code: its name, its clock ("bmi", "deficit" or "time"), its onset (starved hours, deficit per cent, the
-- clinical grade or the rung), its first floor, its death point (BMI, deficit per cent or hours since onset), its floor
-- curve (knots over the clock; starvation's is K.drain.starveFloor) and its rate (health per game day).
K.drain.states = {
    { name = "starvation", clock = "bmi", onset = K.drain.STARVE_ONSET_H, firstFloor = K.drain.FIRST_FLOOR,
      death = K.drain.BMI_DEATH, rate = K.drain.STARVE_RATE },
    { name = "scurvy", clock = "time", onset = K.drain.CLINICAL, firstFloor = K.drain.FIRST_FLOOR,
      death = K.drain.SCURVY_DEATH_H, rate = K.drain.DEF_RATE,
      knots = K.drain.timeKnots(K.drain.DEF_HOLD_H, K.drain.SCURVY_DEATH_H, K.drain.DEF_FINAL_H) },
    { name = "beriberi", clock = "time", onset = K.drain.CLINICAL, firstFloor = K.drain.FIRST_FLOOR,
      death = K.drain.BERIBERI_DEATH_H, rate = K.drain.DEF_RATE,
      knots = K.drain.timeKnots(K.drain.DEF_HOLD_H, K.drain.BERIBERI_DEATH_H, K.drain.DEF_FINAL_H) },
    { name = "pellagra", clock = "time", onset = K.drain.CLINICAL, firstFloor = K.drain.FIRST_FLOOR,
      death = K.drain.PELLAGRA_DEATH_H, rate = K.drain.DEF_RATE,
      knots = K.drain.timeKnots(K.drain.DEF_HOLD_H, K.drain.PELLAGRA_DEATH_H, K.drain.DEF_FINAL_H) },
    { name = "hyponatraemia", clock = "time", onset = K.drain.HYPONAT_GRADE, firstFloor = K.drain.FIRST_FLOOR,
      death = K.drain.NA_DEATH_H, rate = 100 * 24 / K.drain.NA_DEATH_H,
      knots = K.drain.timeKnots(0, K.drain.NA_DEATH_H, K.drain.ACUTE_FINAL_H) },
    { name = "dehydration", clock = "deficit", onset = K.drain.DEHYD_KNOTS[1][1], firstFloor = K.drain.FIRST_FLOOR,
      death = K.drain.DEHYD_KNOTS[3][1], rate = K.drain.DEHYD_RATE, knots = K.drain.DEHYD_KNOTS },
    { name = "iron", clock = "time", onset = K.drain.IRON_RUNG, firstFloor = K.drain.FIRST_FLOOR,
      death = K.drain.FE_DEATH_H, rate = 100 * 24 / K.drain.FE_DEATH_H,
      knots = K.drain.timeKnots(0, K.drain.FE_DEATH_H, K.drain.ACUTE_FINAL_H) },
}

-- The nutrient key each deficiency state reads.
K.drain.NUTRIENT = {
    [2] = "vitC", -- scurvy, no row needed
    [3] = "thiamine", -- wet beriberi, no row needed
    [4] = "niacin", -- pellagra, no row needed
}

-- A fresh record.drain: no state, no onset BMI, no hours in the sodium or iron state.
function K.drain.new()
    return {
        bmi0 = 0,
        naH = 0,
        feH = 0,
        active = false,
        state = 0,
        targetFloor = K.drain.NONE,
        rate = 0,
        drainThisMinute = 0,
        starvedH = 0,
        acuteH = 0,
        starving = false,
        starveAcute = false,
        dehydrated = false,
    }
end

-- record.drain, laid when absent; a stored input that is not a finite number heals to 0.
function K.drain.ensure(record)
    local D = record.drain
    if type(D) ~= "table" then
        D = K.drain.new()
        record.drain = D
    end
    if not K.finite(D.bmi0) then
        D.bmi0 = 0
    end
    if not K.finite(D.naH) then
        D.naH = 0
    end
    if not K.finite(D.feH) then
        D.feH = 0
    end
    if not K.finite(D.acuteH) or D.acuteH < 0 then
        D.acuteH = 0
    end
    if D.fedAgeH ~= nil and not K.finite(D.fedAgeH) then
        D.fedAgeH = nil
    end
    return D
end

-- The BMI of lm + fm at K.HEIGHT_M.
function K.drain.bmi(lm, fm)
    return (lm + fm) / (K.HEIGHT_M * K.HEIGHT_M)
end

-- The hours since the meal pool was last fed (record.satiety.M at K.hungerCurve.FED_M or more), counted continuously
-- across days, sleep and restarts (record.drain.fedAgeH, a stored input, moved past an offline gap by
-- K.acute.skipRecord): a fed minute, a record seen for the first time (no stamp), a pool not yet seeded or a stamp
-- ahead of the minute stamps the world age and reads 0.
function K.drain.unfedH(D, sat, ageH)
    if not K.finite(ageH) then
        return 0
    end
    local M = nil
    if type(sat) == "table" then
        M = sat.M
    end
    if not K.finite(D.fedAgeH) or D.fedAgeH > ageH or not K.finite(M) or M >= K.hungerCurve.FED_M then
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

-- Starvation's floor at BMI bmi from the onset BMI bmi0: 10 + 40 x clamp((bmi - 12.5) / (bmi0 - 12.5), 0, 1) at or
-- above the knee (the first floor when the onset BMI is not above it), then linear to 0 at the death BMI.
function K.drain.starveFloor(bmi, bmi0)
    local D = K.drain
    if bmi < D.BMI_KNEE then
        return K.max(0, D.SLEEP_FLOOR * (bmi - D.BMI_DEATH) / (D.BMI_KNEE - D.BMI_DEATH))
    end
    local span = bmi0 - D.BMI_KNEE
    if not (span > 0) then
        return D.FIRST_FLOOR
    end
    return D.SLEEP_FLOOR + (D.FIRST_FLOOR - D.SLEEP_FLOOR) * K.clamp((bmi - D.BMI_KNEE) / span, 0, 1)
end

-- The floor health of state code at tSinceOnsetH hours since its onset, body the severity inputs: lm and fm (kg) and
-- bmi0 (the onset BMI) for starvation, dehydPct (per cent of body mass) for dehydration. Falls monotonically along its
-- clock, stays above 10 until the final stage and reaches 0 at the death point.
function K.drain.floor(state, tSinceOnsetH, body)
    local S = K.drain.states[state]
    if S.clock == "bmi" then
        return K.drain.starveFloor(K.drain.bmi(body.lm, body.fm), body.bmi0)
    end
    if S.clock == "deficit" then
        return K.interp(S.knots, body.dehydPct)
    end
    return K.interp(S.knots, tSinceOnsetH)
end

-- The drain rate of state code, health per game day.
function K.drain.rate(state)
    return K.drain.states[state].rate
end

-- One state's candidacy: when active, a floor under the best so far wins the state (a tie keeps the earlier code) and a
-- faster rate wins the rate. A floor that is not a finite number (a clock the record's heal has not reached yet) leaves
-- the state out for the minute.
function K.drain.consider(D, code, tH, inp)
    local f = K.drain.floor(code, tH, inp)
    if not K.finite(f) then
        return
    end
    if not D.active or f < D.targetFloor then
        D.targetFloor = f
        D.state = code
    end
    D.rate = K.max(D.rate, K.drain.rate(code))
    D.active = true
end

-- The deficiency state code's candidacy off its nutrient's clinical grade and its hours there.
function K.drain.deficiency(D, code, nut, inp)
    local s = nut[K.drain.NUTRIENT[code]]
    if s ~= nil and s.g == K.drain.CLINICAL then
        K.drain.consider(D, code, s.ah, inp)
    end
end

-- The input table the floors read, laid once and overwritten each step (no allocation per minute).
K.drain.IN = { lm = 0, fm = 0, bmi0 = 0, dehydPct = 0 }

-- One minute of dtM game minutes at world age ageH (nil reads record.nutrients.lastAgeH): every state's onset test, the
-- clocks the record keeps (the onset BMI, the sodium and iron hours) and the outputs on record.drain: active, state
-- (the code whose floor is lowest), targetFloor (100 with none), rate (the fastest active, health per game day),
-- drainThisMinute (rate x dtM / 1440, the most the minute may take; the adapter takes no more than health - floor),
-- starvedH (the starvation clock: the unfed hours, K.drain.unfedH; while the acute state holds, at least the onset plus
-- its hours, acuteH), recentKcal (K.drain.recentKcal), and starving and
-- dehydrated: whether the starvation and the dehydration states are active, whichever floor wins (the writer lifts its
-- HUNGER and THIRST caps on them, K.hybrid.caps); starveAcute: whether starvation came by the acute onset
-- (STARVE_ONSET_H unfed hours, or, while the pool is unfed, the recent intake at or under RECENT_MIN_KCAL; the clock
-- acuteH and the onset BMI are held through a fed spell while the recent intake stays that low, so a snack does not
-- reset the phases or the floor, Plan 15 Task 6 fix 2), whose HUNGER minimum the chronic BMI
-- onset does not take (Plan 15 Task 6, ruling I2). Returns record.drain.
function K.drain.step(record, dtM, ageH)
    local D = K.drain.ensure(record)
    local body, nut, fl, a = record.body, record.nutrients, record.fluids, record.acute
    D.active = false
    D.state = 0
    D.targetFloor = K.drain.NONE
    D.rate = 0
    D.drainThisMinute = 0
    D.starvedH = 0
    D.starving = false
    D.starveAcute = false
    D.dehydrated = false
    if body == nil or nut == nil or fl == nil or a == nil then
        return D
    end
    if ageH == nil then
        ageH = nut.lastAgeH
    end
    local inp = K.drain.IN
    inp.lm = body.lm
    inp.fm = body.fm
    inp.dehydPct = fl.dehydPct
    local unfed = K.drain.unfedH(D, record.satiety, ageH)
    D.recentKcal = K.drain.recentKcal(body, record.stomach)
    local low = D.recentKcal ~= nil and D.recentKcal <= K.drain.RECENT_MIN_KCAL + K.drain.RECENT_TOL
    local sat = record.satiety
    local fedNow = type(sat) == "table" and K.finite(sat.M) and sat.M >= K.hungerCurve.FED_M
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
    if D.starveAcute or K.drain.bmi(body.lm, body.fm) < K.drain.BMI_CHRONIC then
        if not (D.bmi0 > 0) then
            D.bmi0 = K.drain.bmi(body.lm, body.fm)
        end
        inp.bmi0 = D.bmi0
        K.drain.consider(D, K.drain.STARVATION, 0, inp)
        D.starving = true
    elseif not held then
        D.bmi0 = 0
    end
    K.drain.deficiency(D, K.drain.SCURVY, nut, inp)
    K.drain.deficiency(D, K.drain.BERIBERI, nut, inp)
    K.drain.deficiency(D, K.drain.PELLAGRA, nut, inp)
    if K.fluids.hyponatGrade(fl.naPlasma) == K.drain.HYPONAT_GRADE then
        D.naH = D.naH + dtM / 60
        K.drain.consider(D, K.drain.HYPONAT, D.naH, inp)
    else
        D.naH = 0
    end
    if fl.dehydPct >= K.drain.states[K.drain.DEHYD].onset then
        K.drain.consider(D, K.drain.DEHYD, 0, inp)
        D.dehydrated = true
    end
    local iron = nut.iron
    if iron ~= nil and iron.x == K.drain.IRON_RUNG then
        D.feH = D.feH + dtM / 60
        K.drain.consider(D, K.drain.IRON, D.feH, inp)
    else
        D.feH = 0
    end
    D.drainThisMinute = D.rate * dtM / 1440
    return D
end

-- The health the minute takes: drainThisMinute, never past the floor (0 when health is at or under it or unknown).
function K.drain.take(D, health)
    if not D.active or not K.finite(health) then
        return 0
    end
    return K.clamp(health - D.targetFloor, 0, D.drainThisMinute)
end

-- Healing toward the floor (Plan 15 Task 4 fix 1, ruling L2): vanilla's regeneration tier (#2721, #2353) and its
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
K.drain.HEAL_EPS = 0.01 -- health: under the floor by less than this is at it, no row needed

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

-- The AddGeneralHealth argument that heals health toward the active floor over dtM game minutes at y a game minute
-- (vanilla's addition x the units a game minute), never past the floor: 0 with no state, an unknown health or health at
-- the floor (within HEAL_EPS).
function K.drain.heal(D, health, yPerMin, dtM)
    if not D.active or not K.finite(health) or not K.finite(yPerMin) then
        return 0
    end
    local gap = D.targetFloor - health
    if gap <= K.drain.HEAL_EPS then
        return 0
    end
    return K.clamp(yPerMin * dtM, 0, gap * K.drain.PART_SPREAD)
end
