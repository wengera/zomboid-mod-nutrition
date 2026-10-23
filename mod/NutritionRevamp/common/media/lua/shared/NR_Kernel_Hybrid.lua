-- NR_Kernel_Hybrid.lua -- the once-a-minute stat writer's arithmetic. With vanilla's hunger, thirst and fatigue rates
-- zeroed at OnGameBoot (#3364), it steps by elapsed world age (#3371), after the minute's eats (#3383), folding each
-- auto-drink sip into the THIRST target (#3382). Mode 2 (Overlay) writes everything but HUNGER, THIRST and FATIGUE.
-- inp, out and c are tables the adapter owns and reuses; an out field left nil means "no write".
local K = NutritionRevamp.kernel
K.hybrid = {}

-- K.hybrid.defaults reads these at call time.
K.hybrid.CAP_MARGIN = K.dials.get("hybrid.CAP_MARGIN")
K.hybrid.MOOD_RISE_UNHAPPY = K.dials.get("hybrid.MOOD_RISE_UNHAPPY")
K.hybrid.MOOD_RISE_SICK = K.dials.get("hybrid.MOOD_RISE_SICK")
K.hybrid.MOOD_RISE_STRESS = K.dials.get("hybrid.MOOD_RISE_STRESS")
K.hybrid.MOOD_RISE_BORED = K.dials.get("hybrid.MOOD_RISE_BORED")

function K.hybrid.defaults()
    return {
        hungerCap = K.hybrid.HUNGRY_4 - K.hybrid.CAP_MARGIN, -- under HUNGRY level 4 (#0508); lifted while starving
        thirstCap = K.hybrid.THIRST_4 - K.hybrid.CAP_MARGIN, -- under THIRSTY level 4 (#0509); lifted while dehydrated
        moodRiseUnhappy = K.hybrid.MOOD_RISE_UNHAPPY, -- per game-second: one UNHAPPINESS band a game hour (#2369)
        moodRiseSick = K.hybrid.MOOD_RISE_SICK, -- per game-second
        moodRiseStress = K.hybrid.MOOD_RISE_STRESS, moodRiseBored = K.hybrid.MOOD_RISE_BORED, -- per game-second (#2369)
        maxStepS = K.resume.STEP_M * 60, -- a guard: the pipeline sub-steps a stall
        liftedCap = 1,                   -- the stat's own top (#0021): no row needed
        starvingMin = K.hybrid.HUNGRY_4 + K.hybrid.CAP_MARGIN, -- over HUNGRY level 4's strict threshold (#0507), so Starving shows under the acute onset
    }
end

function K.hybrid.input()
    return {
        dtS = 0, mode = 1, asleep = false, starving = false, starveAcute = false, dehydrated = false, hunger = 0,
        hungerTarget = 0, fed = true, circ = 1, thirst = 0, thirstTarget = nil,
        lastThirst = nil, sipOK = true, fOwned = false, fFrozen = false, fS = 0, fCirc = 0, fOff = 0,
        stress = 0, stressTarget = 0, unhappy = 0, unhappyTarget = 0, lastUnhappyTarget = 0, foodSick = 0,
        foodSickTarget = 0, foodSickStep = 0, panic = 0, panicTarget = 0, temp = 0, tempTarget = 0, tempAdj = 0, intoxTarget = nil,
        endurance = 1, lastEndurance = nil, rmod = 1, endCap = 1, bored = 0, boredTarget = 0, lastBoredTarget = 0,
    }
end

function K.hybrid.output()
    return { sip = 0, unhappyTarget = 0, boredTarget = 0 }
end

-- THIRST's fall below the value written, when no intake landed this minute.
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
            out.hunger = K.clamp(K.hungerCurve.write(h, inp, hCap), hMin, hCap)
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
    -- a FOOD_SICKNESS level is raised at once, not at the floor's pace (the Overfull 4 nausea)
    if inp.foodSickStep > 0 and (out.foodSick or inp.foodSick) < inp.foodSickStep then
        out.foodSick = inp.foodSickStep
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
    out.endurance = K.hybrid.endCap(out.endurance, inp.endurance, inp.endCap)
end

-- The ENDURANCE ceiling: the effects' enduranceCap holds ENDURANCE at or under it; a cap of 1 or more, or NaN, holds
-- nothing, and a minute already under it writes nothing more.
-- VANILLA #3926: the Endurance moodle's level edges, descending; the last is the stat's floor.
K.hybrid.END_EDGES = { 0.75, 0.5, 0.25, 0.10, 0 }
K.hybrid.END_BAND_EPS = K.dials.get("hybrid.END_BAND_EPS")
K.hybrid.END_REGEN_UNIT = 0.0000930 / 3 * 1.8 * 1.6 -- VANILLA #2258 at Very Fast regeneration and Fitness 10, the worst case

-- Room under the band's upper edge for one game minute of the worst standing regeneration (#2922: a cap 0.002 under
-- the edge flipped), never at or under the lower edge plus END_BAND_EPS nor above cap; a level-0 cap returns as it is.
function K.hybrid.capAt(cap, dayMin)
    local E = K.hybrid.END_EDGES
    if not (cap <= E[1]) then
        return cap
    end
    local margin = K.hybrid.END_REGEN_UNIT * K.drain.UNITS_PER_MIN * dayMin
    for i = 1, 4 do
        local lo = E[i + 1]
        if cap > lo then
            return K.min(cap, K.max(lo + K.hybrid.END_BAND_EPS, E[i] - margin))
        end
    end
    return cap
end

function K.hybrid.endCap(e, e1, cap)
    if not (cap < 1) then
        return e
    end
    local v = e or e1
    if v > cap then
        return cap
    end
    return e
end

-- A floor target that is nil or not a number reads 0.
function K.hybrid.target(t)
    if t == nil or t ~= t then
        return 0
    end
    return t
end

K.hybrid.FLOOR_EPS = K.dials.get("hybrid.FLOOR_EPS")

-- A mood floor (#3119): a fallen target is subtracted once, never below 0; a stat under the target rises by rise. A fall
-- under FLOOR_EPS to a target above 0 is held (last stays), so the next write subtracts the whole fall: no drift.
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

-- Rule 6: vanilla resets BOREDOM every tick while PANIC > 5 (#3015), so a rise then only costs a Stats.set. The target is
-- still remembered, so the floor resumes once panic drops.
function K.hybrid.boredRise(inp, c, s)
    if inp.panic > 5 then
        return 0
    end
    return c.moodRiseBored * s
end

-- The caps lift at the crises, so vanilla's own Starving and Parched moodles show. Under the chronic BMI onset alone
-- HUNGER follows the curve: the Starving moodle is appetite, the drain is the body.
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

-- Each a strict greater-than (#0507).
K.hybrid.HUNGRY_4 = K.dials.get("hybrid.HUNGRY_4")
K.hybrid.THIRST_4 = K.dials.get("hybrid.THIRST_4")

-- Vanilla's severe-moodle drain runs there (#0516), so the writer sets the shared constant to 0 while this holds.
function K.hybrid.severe(hunger, thirst)
    return hunger > K.hybrid.HUNGRY_4 or thirst > K.hybrid.THIRST_4
end

-- Vanilla's other severe-moodle terms ride the same constant (#2356), so while the writer holds it at 0 it re-applies
-- them. The heavy-load roll is 1/10 a tick whatever the frame rate, so in expectation the constant over (5 - level).
K.hybrid.SEVERE_SICK = 1 -- VANILLA #2356 (SICK 4, either arm: the whole constant)
K.hybrid.SEVERE_BLEED = 1 -- VANILLA #2356 (BLEEDING 4: the whole constant)
K.hybrid.HEAVY_ROLL = 0.1 -- VANILLA #2356's one-in-ten roll (an inference, read on 42.21)
K.hybrid.HEAVY_STRAIN = 0.5 -- VANILLA #2356 (half the heavy-load term goes to back-muscle strain)

-- sickArm: a SICK arm holds; heavyOK: the HEAVY_LOAD term's other conditions hold. Levels are 0-4.
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
