-- NR_Kernel_Hybrid.lua -- the once-a-minute stat writer's arithmetic (Plan 11 Task 13; Decision 1 (c), the hybrid).
-- With vanilla's hunger, thirst and fatigue rise rates zeroed at the server's OnGameBoot (#3364-#3368), the writer
-- sets HUNGER, THIRST and FATIGUE, the STRESS, UNHAPPINESS, BOREDOM and FOOD_SICKNESS floors, PANIC, TEMPERATURE and
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
        moodRiseStress = 5.0e-5, moodRiseBored = 25 / 3600, -- per game-second: STRESS VANILLA #2231 reused (open S1146); BOREDOM one BORED level a game hour (#2369; game choice, Plan 11f ruling T9-3)
        maxStepS = 3600,                 -- a step longer than 60 game minutes integrates 60 (the pipeline's clamp)
    }
end

function K.hybrid.input()
    return {
        dtS = 0, mode = 1, asleep = false, hunger = 0, hungerTarget = 0, thirst = 0, thirstTarget = nil,
        lastThirst = nil, sipOK = true, fOwned = false, fFrozen = false, fS = 0, fCirc = 0, fOff = 0,
        stress = 0, stressTarget = 0, unhappy = 0, unhappyTarget = 0, lastUnhappyTarget = 0, foodSick = 0,
        foodSickTarget = 0, panic = 0, panicTarget = 0, temp = 0, tempTarget = 0, tempAdj = 0, intoxTarget = nil,
        endurance = 1, lastEndurance = nil, rmod = 1, bored = 0, boredTarget = 0, lastBoredTarget = 0,
    }
end

function K.hybrid.output()
    return { sip = 0, unhappyTarget = 0, boredTarget = 0 }
end

-- The hunger target from a fill-like scalar x (0 empty .. 1 sated: since Plan 11c the satiety read Z) and the energy
-- state (Plan 3 ruling 14, moved from the takeover's K.fast.hungerTarget): (1 - x) x energyState, plus a deficit
-- floor DEFICIT_FLOOR x (energyState - 1), clamped to [0, 1].
function K.hybrid.hungerTarget(x, energyState)
    return K.clamp((1 - x) * energyState + K.hybrid.DEFICIT_FLOOR * K.max(0, energyState - 1), 0, 1)
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

K.hybrid.DEFICIT_FLOOR = 0.02 -- game choice, refit on the shipped pipeline against Karl 2021 as reported (Plan 11f ruling 2b-3, widened search), from Plan 11f Task 2c's 0, Plan 11d's 1.0 (ruling 9c-1) and Plan 3 ruling 14's 0.15 (S1271 open): the deficit floor's coefficient, the hunger a deficit adds whatever the satiety read: fitted and weak (Task 2c's search read 0 and the widened search 0.02, a tie broken toward a floor above 0), and Plan 11d ruling 9c-1's floor role, keeping a deficit's hunger up at a full satiety read, is superseded in substance by the refit (Plan 11f ruling 2c-4); S1254 sets the deficit's direction, which the energy state also carries through (1 - x) x energyState; fitted with K.energy.BALANCE_SPAN_KCAL 3100 and K.energy.EX_BYPASS_LO 0.282 and EX_BYPASS_HI 0.575 on the server-path replays for the best worst-case margin over twin K's alternatives: S1325 (Karl 2021 as the paper ran it, DEF +30.2 % against +26 %), S1613 (the 36 h fast's next day 1.196 against 1.20) and S1614 (day 3 0.969 against 1.0); S1255 (CALERIE 2: < 10 mm over 2 y at a 25 % deficit) reads 6.7 mm under the request-anchored mapping, reproduced

-- Plan 11f Task 9b (rulings T9-1, T9-3): the UNHAPPINESS and BOREDOM floors share one rule, moved here from write().
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

-- Plan 11f Task 9b fix 2 (Rule 6): BOREDOM's rise per this write. Vanilla resets BOREDOM every tick while PANIC > 5
-- (BodyDamage.UpdateBoredom @482-@509, #3015), so a rise written then is wiped and only costs a Stats.set: 0 while
-- the stat reads PANIC above 5. The target is still remembered (floor's second return), so the floor resumes at the
-- rate once panic drops; a fall still lands.
function K.hybrid.boredRise(inp, c, s)
    if inp.panic > 5 then
        return 0
    end
    return c.moodRiseBored * s
end
