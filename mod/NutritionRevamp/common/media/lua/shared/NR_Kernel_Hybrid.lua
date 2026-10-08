-- NR_Kernel_Hybrid.lua -- the once-a-minute stat writer's arithmetic (Plan 11 Task 13; Decision 1 (c), the hybrid).
-- With vanilla's hunger, thirst and fatigue rise rates zeroed at the server's OnGameBoot (#3364-#3368), the writer
-- sets HUNGER, THIRST and FATIGUE, the STRESS, UNHAPPINESS and FOOD_SICKNESS floors, PANIC, TEMPERATURE and
-- INTOXICATION once a player-minute, stepping by elapsed world age (#3371), after the minute's eats (#3383), with
-- each auto-drink sip folded into the THIRST target (#3382). Mode 2 (Overlay) writes everything but the first three.
-- Pure: inp, out and c are tables the adapter owns and reuses; an out field left nil means "no write".
local K = NutritionRevamp.kernel
K.hybrid = {}

function K.hybrid.defaults()
    return {
        hungerCap = 0.69,                -- under HUNGRY level 4 at 0.70, #0508 (Plan 5 ruling 14)
        thirstCap = 0.83,                -- under THIRSTY level 4 at 0.84, #0509 (Plan 5 ruling 14)
        moodRiseUnhappy = 22 / 3600,     -- per game-second: one UNHAPPINESS band a game hour (#2369; open S1146)
        moodRiseSick = 25 / 3600,        -- per game-second: one SICK level a game hour on FOOD_SICKNESS (T1-1)
        moodRiseStress = 5.0e-5,         -- per game-second: VANILLA #2231 reused (open S1146)
        maxStepS = 3600,                 -- a step longer than 60 game minutes integrates 60 (the pipeline's clamp)
    }
end

function K.hybrid.input()
    return {
        dtS = 0, mode = 1, asleep = false, hunger = 0, hungerTarget = 0, thirst = 0, thirstTarget = nil,
        lastThirst = nil, sipOK = true, fOwned = false, fFrozen = false, fS = 0, fCirc = 0, fOff = 0,
        stress = 0, stressTarget = 0, unhappy = 0, unhappyTarget = 0, lastUnhappyTarget = 0, foodSick = 0,
        foodSickTarget = 0, panic = 0, panicTarget = 0, temp = 0, tempTarget = 0, tempAdj = 0, intoxTarget = nil,
        endurance = 1, lastEndurance = nil, rmod = 1,
    }
end

function K.hybrid.output()
    return { sip = 0, unhappyTarget = 0 }
end

-- The hunger target from a fill-like scalar x (0 empty .. 1 full: the stomach fill, then the satiety scalar S) and
-- the energy state (Plan 3 ruling 14, moved from the takeover's K.fast.hungerTarget): (1 - x) x energyState, plus a
-- deficit floor 0.15 x (energyState - 1), clamped to [0, 1].
function K.hybrid.hungerTarget(x, energyState)
    return K.clamp((1 - x) * energyState + 0.15 * K.max(0, energyState - 1), 0, 1)
end

-- The auto-drink sip since the last write: THIRST's fall below the value written, when no intake landed this
-- minute (Plan 11 ruling 7) and a value was written.
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
        out.hunger = K.clamp(inp.hungerTarget, 0, c.hungerCap)
        out.sip = K.hybrid.sip(inp.thirst, inp.lastThirst, inp.sipOK)
        local t = inp.thirstTarget
        if t ~= nil and t == t then
            out.thirst = K.clamp(t - out.sip, 0, c.thirstCap)
        end
        if inp.fOwned and not inp.fFrozen then
            out.fatigue = K.clamp(inp.fS + inp.fCirc + inp.fOff, 0, 1)
        end
    end
    out.stress = nil
    if inp.stress < inp.stressTarget then
        out.stress = K.min(inp.stressTarget, inp.stress + c.moodRiseStress * s)
    end
    out.unhappy = nil
    local ut = inp.unhappyTarget
    if ut ~= ut then
        ut = 0
    end
    local last = inp.lastUnhappyTarget
    if ut < last or ut > 0 then
        local v = inp.unhappy
        if ut < last then
            v = K.max(0, v - (last - ut))
        end
        if v < ut then
            v = K.min(ut, v + c.moodRiseUnhappy * s)
        end
        if v ~= inp.unhappy then
            out.unhappy = v
        end
    end
    out.unhappyTarget = ut
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
