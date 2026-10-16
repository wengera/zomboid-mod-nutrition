-- NR_Kernel_Hybrid.lua -- the once-a-minute stat writer's arithmetic (the hybrid).
-- With vanilla's hunger, thirst and fatigue rise rates zeroed at the server's OnGameBoot (#3364-#3368), the writer
-- sets HUNGER, THIRST and FATIGUE, the STRESS, UNHAPPINESS, BOREDOM and FOOD_SICKNESS floors, PANIC, TEMPERATURE and
-- INTOXICATION once a player-minute, stepping by elapsed world age (#3371), after the minute's eats (#3383), with
-- each auto-drink sip folded into the THIRST target (#3382). Mode 2 (Overlay) writes everything but the first three.
-- HUNGER is the satiety model's h_model through the calibrated curve (K.hungerCurve.write, Plan 15 Task 6), then capped.
-- Pure: inp, out and c are tables the adapter owns and reuses; an out field left nil means "no write".
local K = NutritionRevamp.kernel
K.hybrid = {}

function K.hybrid.defaults()
    return {
        hungerCap = 0.69,                -- under HUNGRY level 4 at 0.70, #0508 (Plan 5 ruling 14); lifted while starving (K.hybrid.caps)
        thirstCap = 0.83,                -- under THIRSTY level 4 at 0.84, #0509 (Plan 5 ruling 14); lifted while dehydrated (K.hybrid.caps)
        moodRiseUnhappy = 22 / 3600,     -- per game-second: one UNHAPPINESS band a game hour (#2369; open S1146)
        moodRiseSick = 25 / 3600,        -- per game-second: one SICK level a game hour on FOOD_SICKNESS (T1-1)
        moodRiseStress = 5.0e-5, moodRiseBored = 25 / 3600, -- per game-second: STRESS VANILLA #2231 reused (open S1146); BOREDOM one BORED level a game hour (#2369; game choice, Plan 11f ruling T9-3)
        maxStepS = 3600,                 -- a step longer than 60 game minutes integrates 60 (the pipeline's clamp)
        liftedCap = 1,                   -- the stat's own top (#0021): a lifted cap, no row needed
        starvingMin = 0.71,              -- HUNGER at least this under starvation's acute onset, over HUNGRY level 4's strict 0.70 (#0508, #0507), so vanilla's Starving moodle shows: game choice (spec section 3.1; the chronic BMI onset follows the curve, Plan 15 Task 6, ruling I2)
    }
end

function K.hybrid.input()
    return {
        dtS = 0, mode = 1, asleep = false, starving = false, starveAcute = false, dehydrated = false, hunger = 0,
        hungerTarget = 0, fed = true, circ = 1, thirst = 0, thirstTarget = nil,
        lastThirst = nil, sipOK = true, fOwned = false, fFrozen = false, fS = 0, fCirc = 0, fOff = 0,
        stress = 0, stressTarget = 0, unhappy = 0, unhappyTarget = 0, lastUnhappyTarget = 0, foodSick = 0,
        foodSickTarget = 0, panic = 0, panicTarget = 0, temp = 0, tempTarget = 0, tempAdj = 0, intoxTarget = nil,
        endurance = 1, lastEndurance = nil, rmod = 1, bored = 0, boredTarget = 0, lastBoredTarget = 0,
    }
end

function K.hybrid.output()
    return { sip = 0, unhappyTarget = 0, boredTarget = 0 }
end

-- The auto-drink sip since the last write: THIRST's fall below the value written, when no intake landed this
-- minute and a value was written.
function K.hybrid.sip(thirst, lastThirst, sipOK)
    if not sipOK or lastThirst == nil then
        return 0
    end
    if thirst < lastThirst then
        return lastThirst - thirst
    end
    return 0
end

function K.hybrid.write(inp, out, c)
    local s = K.clamp(inp.dtS, 0, c.maxStepS)
    out.hunger = nil
    out.thirst = nil
    out.sip = 0
    out.fatigue = nil
    if inp.mode == 1 then
        -- K.clamp passes a NaN through, so each target is tested first: a NaN target writes nothing (t == t)
        local hCap, hMin, tCap = K.hybrid.caps(inp, c)
        local h = inp.hungerTarget
        if h == h then
            out.hunger = K.clamp(K.hungerCurve.write(h, inp), hMin, hCap)
        end
        out.sip = K.hybrid.sip(inp.thirst, inp.lastThirst, inp.sipOK)
        local t = inp.thirstTarget
        if t ~= nil and t == t then
            out.thirst = K.clamp(t - out.sip, 0, tCap)
        end
        if inp.fOwned and not inp.fFrozen then
            local f = inp.fS + inp.fCirc + inp.fOff
            if f == f then
                out.fatigue = K.clamp(f, 0, 1)
            end
        end
    end
    out.stress = nil
    if inp.stress < inp.stressTarget then
        out.stress = K.min(inp.stressTarget, inp.stress + c.moodRiseStress * s)
    end
    local ut = K.hybrid.target(inp.unhappyTarget)
    out.unhappy, out.unhappyTarget = K.hybrid.floor(inp.unhappy, ut, inp.lastUnhappyTarget, c.moodRiseUnhappy * s)
    local bt = K.hybrid.target(inp.boredTarget)
    out.bored, out.boredTarget = K.hybrid.floor(inp.bored, bt, inp.lastBoredTarget, K.hybrid.boredRise(inp, c, s))
    out.foodSick = nil
    if inp.foodSickTarget > 0 and inp.foodSick < inp.foodSickTarget then
        out.foodSick = K.min(inp.foodSickTarget, inp.foodSick + c.moodRiseSick * s)
    end
    out.panic = nil
    if inp.panicTarget > 0 and inp.panic < inp.panicTarget then
        out.panic = inp.panicTarget
    end
    out.temp = nil
    if inp.tempTarget > 0 then
        local adj = inp.tempAdj
        if (adj < 0 and inp.temp > inp.tempTarget) or (adj > 0 and inp.temp < inp.tempTarget) then
            out.temp = inp.tempTarget
        end
    end
    out.intox = nil
    local it = inp.intoxTarget
    if it ~= nil and it == it then
        out.intox = it
    end
    out.endurance = nil
    local e0 = inp.lastEndurance
    if inp.asleep and e0 ~= nil and inp.endurance > e0 and inp.rmod == inp.rmod then
        out.endurance = K.clamp(e0 + (inp.endurance - e0) * inp.rmod, 0, 1)
    end
end

-- The UNHAPPINESS and BOREDOM floors share one rule, moved here from write().
-- A floor target that is nil or not a number reads 0.
function K.hybrid.target(t)
    if t == nil or t ~= t then
        return 0
    end
    return t
end

K.hybrid.FLOOR_EPS = 0.05 -- game choice, Plan 11f Task 9b fix 1 (Rule 6): a mood floor's target fall under 0.05 of the stat (0-100) is held and folded into the next write, so a decaying monotony target sets UNHAPPINESS and BOREDOM about once per 0.05 of fall (every 9 game minutes or more at the steepest release) instead of every minute; a step of 0.05 is far under any moodle threshold's margin

-- A mood floor (#3119): when the target fell since the last write (last), the stat v loses that fall once, never
-- below 0, whatever else raised it; then a stat under the target rises toward it by rise. A fall under FLOOR_EPS to a
-- target above 0 is held: last stays the remembered target, so the next write subtracts the whole fall since it (no
-- drift), and a fall to 0 always lands. Returns the value to write (nil when there is no target and no fall, or the
-- value is unchanged) and the target to remember as the next call's last.
function K.hybrid.floor(v0, ut, last, rise)
    local keep = ut
    local fall = last - ut
    if fall > 0 and fall < K.hybrid.FLOOR_EPS and ut > 0 then
        keep = last
        fall = 0
    end
    if not (fall > 0 or ut > 0) then
        return nil, keep
    end
    local v = v0
    if fall > 0 then
        v = K.max(0, v - fall)
    end
    if v < ut then
        v = K.min(ut, v + rise)
    end
    if v ~= v0 then
        return v, keep
    end
    return nil, keep
end

-- Rule 6: BOREDOM's rise per this write. Vanilla resets BOREDOM every tick while PANIC > 5
-- (BodyDamage.UpdateBoredom @482-@509, #3015), so a rise written then is wiped and only costs a Stats.set: 0 while
-- the stat reads PANIC above 5. The target is still remembered (floor's second return), so the floor resumes at the
-- rate once panic drops; a fall still lands.
function K.hybrid.boredRise(inp, c, s)
    if inp.panic > 5 then
        return 0
    end
    return c.moodRiseBored * s
end

-- Option B (Plan 15 Task 5; spec section 3.1; jar-checks Check 3): the caps lift at the crises, so vanilla's own
-- Starving and Parched moodles show. state is any table with the drain flags (record.drain, or the writer's input,
-- which copies them): starving (K.drain's starvation state active) lifts HUNGER's cap to 1, and under the acute onset
-- (starveAcute, 36 starved hours) holds it at least starvingMin; under the chronic BMI onset alone HUNGER follows the
-- curve (ruling I2: the Starving moodle is appetite, the drain is the body); dehydrated (K.drain's dehydration state active, a body-water deficit of 4 % or more) lifts THIRST's cap
-- to 1, where the thirst knots already read Parched (K.fluids.THIRST_KNOTS). Otherwise HUNGER stays under 0.69 and
-- THIRST under 0.83, below level 4. Returns the HUNGER cap, the HUNGER minimum and the THIRST cap.
function K.hybrid.caps(state, c)
    local hCap, hMin, tCap = c.hungerCap, 0, c.thirstCap
    if state.starving == true then
        hCap = c.liftedCap
        if state.starveAcute == true then
            hMin = c.starvingMin
        end
    end
    if state.dehydrated == true then
        tCap = c.liftedCap
    end
    return hCap, hMin, tCap
end

-- The level-4 thresholds, each a strict greater-than (#0507): HUNGRY above 0.70 (#0508), THIRST above 0.84 (#0509).
K.hybrid.HUNGRY_4 = 0.70 -- VANILLA #0508
K.hybrid.THIRST_4 = 0.84 -- VANILLA #0509, #0577

-- Whether a HUNGER and a THIRST stand at level 4: vanilla's severe-moodle drain runs there (#0516), so the writer
-- sets the shared constant to 0 while this holds.
function K.hybrid.severe(hunger, thirst)
    return hunger > K.hybrid.HUNGRY_4 or thirst > K.hybrid.THIRST_4
end

-- Vanilla's other severe-moodle terms, which the shared constant also carries (#2356, x451): while the writer holds the
-- constant at 0 it re-applies them at vanilla's rates. Each is a multiple of the constant per multiplier unit:
-- SICK level 4 on either arm and BLEEDING level 4 the whole constant (BodyDamage.Update L2365, L2370, L2376); a
-- HEAVY_LOAD above level 2 the constant over (5 - level) / 10 on a one-in-ten roll a tick (Rand.PerThirtiethOfASecond
-- with 10 draws RandAbstract.Next(0, 10 f), a uniform float, under f: probability 1/10 whatever the frame rate, read on
-- 42.21), so in expectation the constant over (5 - level), half of it also going to back-muscle strain (L2391-L2393).
K.hybrid.SEVERE_SICK = 1 -- VANILLA #2356 (SICK 4, either arm: the whole constant)
K.hybrid.SEVERE_BLEED = 1 -- VANILLA #2356 (BLEEDING 4: the whole constant)
K.hybrid.HEAVY_ROLL = 0.1 -- VANILLA #2356's roll (Rand.PerThirtiethOfASecond(10) @0-@28 L41-L42 over RandAbstract.Next(FF) L84, uniform; an inference, read on 42.21)
K.hybrid.HEAVY_STRAIN = 0.5 -- VANILLA #2356 (half the heavy-load term goes to back-muscle strain, L2393)

-- The multiple of the constant per multiplier unit the re-applied terms take at these moodle levels (sickArm: one of
-- the SICK arms holds; heavyOK: the HEAVY_LOAD term's further conditions hold), and its heavy-load share (the strain's
-- base). Levels are 0-4.
function K.hybrid.severeRate(sickLvl, sickArm, bleedLvl, heavyLvl, heavyOK)
    local f = 0
    if sickLvl == 4 and sickArm then
        f = f + K.hybrid.SEVERE_SICK
    end
    if bleedLvl == 4 then
        f = f + K.hybrid.SEVERE_BLEED
    end
    local heavy = 0
    if heavyLvl > 2 and heavyOK then
        heavy = K.hybrid.HEAVY_ROLL / ((5 - heavyLvl) / 10)
    end
    return f + heavy, heavy
end
