-- NR_Kernel_Drain.lua: the remaining-fraction drain (docs/superpowers/specs/2026-10-19-health-combine-design.md@
-- program-record-v19). Every lethal state keeps a fraction f, 1 at onset and 0 at its death point, on a straight line
-- on its own clock (S2231); the target health folds the active fractions by the combine rule, and health falls toward
-- it by at most the active states' summed rates. The target is a ceiling that rises only as the body recovers: a
-- lapsed cause keeps its fraction while its clock counts back down, so a snack or a one-minute exit never resets it.
-- With no state active or recovering there is no target and vanilla's regeneration resumes (NR_Server_Effects);
-- K.drain.heal lets vanilla's own regeneration mend wounds up to the ceiling, never past it.
-- Codes: 1 starvation, 2 scurvy, 3 wet beriberi, 4 pellagra, 5 severe hyponatraemia, 6 dehydration, 7 the iron rung.
-- Paces: Vanilla on the hours in the state at vanilla's level-4 rate (#0516), Shortened on SHORT_* hours, Realistic
-- starvation on the smoothed BMI progress and dehydration on the deficit; the deficiencies and rungs match at every pace.
-- record.drain's saved inputs are in K.store.INPUTS. Pure, no Java; slow-clock code; every `#` is on a kernel-built
-- Lua array. K.acute, K.fluids, K.HEIGHT_M and K.body resolve at call time.
local K = NutritionRevamp.kernel
K.drain = {}

K.drain.STARVATION = 1 -- no row needed: a code
K.drain.SCURVY = 2 -- no row needed: a code
K.drain.BERIBERI = 3 -- no row needed: a code
K.drain.PELLAGRA = 4 -- no row needed: a code
K.drain.HYPONAT = 5 -- no row needed: a code
K.drain.DEHYD = 6 -- no row needed: a code
K.drain.IRON = 7 -- no row needed: a code
K.drain.N = 7 -- the state count, no row needed

-- An unreadable sandbox reads vanilla's 90-minute default day.
K.drain.DAY_MINUTES = 90 -- VANILLA #2922: the fallback for an unreadable sandbox

-- Read once a server minute by the adapter, which overwrites this table's fields in place (no allocation).
K.drain.PACE_VANILLA = 1 -- no row needed: an option value
K.drain.PACE_SHORT = 2 -- no row needed: an option value
K.drain.PACE_REAL = 3 -- no row needed: an option value
K.drain.COMBINE_WORST = 1 -- no row needed: an option value
K.drain.COMBINE_MULTIPLY = 2 -- no row needed: an option value
K.drain.COMBINE_ADD = 3 -- no row needed: an option value
K.drain.OPT = { pace = K.drain.PACE_REAL, combine = K.drain.COMBINE_MULTIPLY, dayMin = K.drain.DAY_MINUTES } -- the defaults Realistic and Multiply: game choices (spec section 7), the option file's NR.DeathPace and NR.HealthCombine defaults; vanilla's 90-minute day (#2922)

K.drain.SLEEP_FLOOR = 10 -- VANILLA #3900: health at or below which vanilla wakes a sleeper every tick, the last tenth of each line (spec section 9)
K.drain.NONE = 100 -- health: the target read with no state active (full health), no row needed

-- The paces' rates and the BMI clock's opening rate, read off the calibration's default body fasting with water at
-- the 90-minute day (testing/artifacts/calibrate-drain-20261019/calibration.json).
K.drain.R_HUNGER = 0.0396 -- VANILLA #0516 #0518 #2922: health per game hour per real minute of day length, 3.3e-4 x 120
K.drain.R_THIRST = 0.198 -- VANILLA #0516 #0518 #2922: health per game hour per real minute of day length, 1.65e-3 x 120
K.drain.SHORT_STARVE_H = K.dials.get("drain.SHORT_STARVE_H")
K.drain.SHORT_DEHYD_H = K.dials.get("drain.SHORT_DEHYD_H")
K.drain.STARVE_DPDT = K.dials.get("drain.STARVE_DPDT")
K.drain.CAL_BMI0 = K.dials.get("drain.CAL_BMI0")

-- Starvation's acute onset: STARVE_ONSET_H unfed hours (counted continuously across days, sleep and restarts, never
-- offline), or, while the pool is unfed, recent intake at RECENT_MIN_KCAL or less (a starvation diet of snacks); the
-- chronic onset is a BMI under BMI_CHRONIC whatever the intake.
K.drain.STARVE_ONSET_H = K.dials.get("drain.STARVE_ONSET_H")
K.drain.RECENT_TOL = 1e-6 -- kcal: the comparison's tolerance, no row needed (three 200 kcal snacks integrate a few 1e-9 kcal over 600)
K.drain.RECENT_DAYS = 3 -- record-day closes the window needs seen, no row needed
K.drain.RECENT_MIN_KCAL = K.dials.get("drain.RECENT_MIN_KCAL")
K.drain.BMI_DEATH = K.dials.get("drain.BMI_DEATH")
K.drain.BMI_CHRONIC = K.dials.get("drain.BMI_CHRONIC")
K.drain.SUSPEND_M = K.dials.get("drain.SUSPEND_M")
-- A game-pacing choice on the starvation clock (the day of onset of each phase is open, S2247).
K.drain.STARVE_PHASE_H = {
    K.dials.get("drain.STARVE_PHASE_H.1"),
    K.dials.get("drain.STARVE_PHASE_H.2"),
    K.dials.get("drain.STARVE_PHASE_H.3"),
}

-- On the water base's 3 % a day at rest, 4 % comes at about 32 h; no knee, no final stage.
K.drain.DEHYD_ONSET = K.dials.get("drain.DEHYD_ONSET")
K.drain.DEHYD_DEATH = K.dials.get("drain.DEHYD_DEATH")

-- Onset at the clinical grade; a line on the hours at it to the death time.
K.drain.CLINICAL = 4 -- the clinical grade, no row needed: a grade index
K.drain.BERIBERI_DEATH_H = K.dials.get("drain.BERIBERI_DEATH_H")
K.drain.SCURVY_DEATH_H = K.dials.get("drain.SCURVY_DEATH_H")
K.drain.PELLAGRA_DEATH_H = K.dials.get("drain.PELLAGRA_DEATH_H")

-- Their onsets kept; a line on the hours in the state to NA_DEATH_H and FE_DEATH_H.
K.drain.HYPONAT_GRADE = 3 -- the lethal hyponatraemia grade (K.fluids.hyponatGrade), no row needed: a grade index
K.drain.IRON_RUNG = 3 -- the iron lethal rung (S1033), no row needed: a rung index
K.drain.NA_DEATH_H = K.dials.get("drain.NA_DEATH_H")
K.drain.FE_DEATH_H = K.dials.get("drain.FE_DEATH_H")

-- Per state: its name and structural onset; every value read off a dial is laid by K.drain.derive. A state with no
-- short is a line on its hours at every pace.
K.drain.states = {
    { name = "starvation" },
    { name = "scurvy", onset = K.drain.CLINICAL },
    { name = "beriberi", onset = K.drain.CLINICAL },
    { name = "pellagra", onset = K.drain.CLINICAL },
    { name = "hyponatraemia", onset = K.drain.HYPONAT_GRADE },
    { name = "dehydration" },
    { name = "iron", onset = K.drain.IRON_RUNG },
}

-- The dial copies, laid once at load and again whenever a dial is written after load (K.dials.apply, the replays'
-- set_constants), so every output that reads a copy follows.
function K.drain.derive()
    K.drain.STARVE_DBMI = K.drain.STARVE_DPDT * (K.drain.CAL_BMI0 - K.drain.BMI_DEATH) -- BMI per game hour before the state's first close: the calibration body's opening rate in BMI, so a heavier body opens no faster in kg
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
K.drain.derive()

K.drain.NUTRIENT = {
    [2] = "vitC", -- scurvy, no row needed
    [3] = "thiamine", -- wet beriberi, no row needed
    [4] = "niacin", -- pellagra, no row needed
}

-- Each state's hour clock: up while its cause is present, back down 1:1 while absent, never under 0. A deficiency's is
-- the drain's own, beside the nutrient model's ah, which restarts at 0 when the grade leaves clinical.
K.drain.CLOCK = { "stH", "scH", "bbH", "plH", "naH", "dhH", "feH" }

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

K.drain.HEAL0 = { "bmi0", "stH", "scH", "bbH", "plH", "naH", "dhH", "feH", "bClose", "bRate", "pS" }
-- Also heal when negative: a corrupt negative clock would lengthen a line.
K.drain.CLOCKS0 = K.drain.CLOCK

-- pAt, fedAgeH and dPrev heal to absent (first sight); the fraction table is laid once.
function K.drain.ensure(record)
    local D = record.drain
    if type(D) ~= "table" then
        D = K.drain.new()
        record.drain = D
    end
    local H = K.drain.HEAL0
    for i = 1, #H do
        if not K.finite(D[H[i]]) then
            D[H[i]] = 0
        end
    end
    local C = K.drain.CLOCKS0
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

function K.drain.bmi(lm, fm)
    return (lm + fm) / (K.HEIGHT_M * K.HEIGHT_M)
end

-- The meal spell (a stored input): open while M is at SUSPEND_M or more and held until M falls under FED_M, so a snack's
-- pool opens a fed spell as long as the curve's own, and a floret's never opens one.
function K.drain.spellStep(D, M)
    if not K.finite(M) or M < K.hungerCurve.FED_M then
        D.spell = false
    elseif M >= K.drain.SUSPEND_M then
        D.spell = true
    end
end

function K.drain.mealFed(D, M)
    return K.finite(M) and M >= K.hungerCurve.FED_M and D.spell == true
end

-- Inside the acute state only a meal spell is fed. fedAgeH is a resume stamp; a fed minute, a first sight, an unseeded
-- pool or a stamp ahead of the minute stamps the world age and reads 0.
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

-- Today, the three closed record days and what is still in the stomach, so a meal counts in full from its eat; the
-- record calendar keeps the window, so an offline gap neither counts nor shifts it. nil until RECENT_DAYS closes are
-- seen (a loaded body's defaulted closed day never counts).
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

-- NR_Server_Metabolism's and the replays': the closed days move down one.
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

function K.drain.starvePhase(h)
    local P = K.drain.STARVE_PHASE_H
    local n = 0
    for i = 1, #P do
        if h >= P[i] then
            n = i
        end
    end
    return n
end

-- 1 - tau / T with tau clamped to [0, T]; 0 with no span.
function K.drain.line(tau, T)
    if not (T > 0) then
        return 0
    end
    return 1 - K.clamp(tau, 0, T) / T
end

-- nil for every state but starvation and dehydration; a non-positive day length reads 90 minutes.
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

-- 1 when the onset is at or under the death BMI.
function K.drain.progress(bmi0, bmi)
    local span = bmi0 - K.drain.BMI_DEATH
    if not (span > 0) then
        return 1
    end
    return K.clamp((bmi0 - bmi) / span, 0, 1)
end

-- The body moves BMI only at a record-day close, so the line reads an estimate anchored at the open day's start pAt (a
-- resume stamp) and running at bRate, which turns negative on a regain. Active, pS keeps the largest progress; lapsed,
-- it only falls between closes (ruling R2-2: a ceiling never falls while its cause is absent), and a close sets it to
-- the true BMI's progress either way. Returns pS and whether this minute closed or re-anchored the clock.
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

function K.drain.bmiEst(D, ageH)
    return D.bClose - D.bRate * K.max(0, ageH - D.pAt)
end

-- The progress the minute moved wins when more (a close's correction, so health keeps up with the line instead of
-- trailing it). With no span, vanilla's own pace at the day length, so the cap still reaches 0.
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

-- Every state is a line from 1 to 0 on its clock, its rate the line's slope through the clock's current rate. A
-- fraction or rate that is not finite returns nil: the state is left out for the minute.
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

-- The smallest fraction wins the state (a tie keeps the earlier code). A recovering state's rate joins only while its
-- ceiling can still fall: only Realistic starvation's, whose next close can book a weight still lost.
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

-- Multiply is the default and any unknown value.
function K.drain.fold(acc, f, c)
    if c == K.drain.COMBINE_WORST then
        return K.min(acc, f)
    end
    if c == K.drain.COMBINE_ADD then
        return acc - (1 - f)
    end
    return acc * f
end

-- Floored at 0; 100 with no ceiling applied.
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

function K.drain.down(h, dtM)
    return K.max(0, h - dtM / 60)
end

-- Absent, the clock counts back down and the state recovers while it is above 0, its ceiling rising as it falls.
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

-- Never behind the nutrient's hours at the grade (ah: a record seeded or first seen at clinical).
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

-- Released only once its progress is back at 0, or under Overlay.
function K.drain.release(D)
    D.bmi0 = 0
    D.bClose = 0
    D.bRate = 0
    D.pS = 0
    D.pAt = nil
end

-- on is never true under Overlay, where vanilla owns starvation. A lapse at the onset's own progress of 0 keeps the
-- onset BMI to the close, so a fed spell reads one span; a close's rise ramps at vanilla's level-4 rate.
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

-- At Realistic pace the line follows the deficit both ways, so under the onset nothing recovers.
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

-- With no last read the rise counts from DEHYD_ONSET, so a record first seen in the state lands on its line in its
-- first minute (ruling R1-3).
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

-- Laid once and overwritten each step: no allocation per minute.
K.drain.IN = { pStarve = 0, pRate = 0, dehydPct = 0, dRise = 0 }

-- One minute: every onset test, the kept clocks and the outputs on record.drain. active means a ceiling applies (the
-- adapter then owns health through K.drain.take and K.drain.heal); starving and dehydrated lift the writer's caps
-- (K.hybrid.caps), a recovering state lifts nothing; starveAcute's clock acuteH holds through a snack's fed spell while
-- intake stays low. Overlay leaves starvation and dehydration out while the starvation clock and the other states
-- still run. Returns record.drain.
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

-- Never past the target; 0 at or under it or unknown.
function K.drain.take(D, health)
    if not D.active or not K.finite(health) then
        return 0
    end
    return K.clamp(health - D.target, 0, D.drainThisMinute)
end

-- Vanilla's regeneration tiers (#2721) and additions per multiplier unit (#2354).
K.drain.REGEN = {
    0.002, -- VANILLA #2354: tier 0, the standard addition
    0.0013, -- VANILLA #2354: tier 1, the reduced addition (a HUNGRY, SICK or THIRST level 2)
    0.0008, -- VANILLA #2354: tier 2, the severely reduced addition (a level 3, or SICK 4)
    0, -- VANILLA #2721 #2353: tier 3, HUNGRY or THIRST at level 4
}
K.drain.REGEN_SLEEPING = 0.02 -- VANILLA #2354
-- A game hour sums 120 x the day length's minutes (#2922).
K.drain.UNITS_PER_MIN = 2 -- VANILLA #2922: 120 / 60
-- With all 17 parts below 100 (#3898).
K.drain.PART_SPREAD = 17 / 5.05 -- VANILLA #3898
K.drain.HEAL_EPS = 0.01 -- health: under the target by less than this is at it, no row needed

-- Asleep the sleeping addition, 0 at HUNGRY or THIRST 4 (#0515); awake by the worst moodle level.
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

-- 0 with no state, an unknown health or health within HEAL_EPS of the target.
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
