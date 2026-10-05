-- NR_Kernel_Fast.lua -- the fast clock's arithmetic: the seven updaters IsoGameCharacter.calculateStats
-- runs when Hook.CalculateStats does not answer true, reproduced from
-- docs/superpowers/research/jar-calculatestats-updaters.md with no nutrition term (Plan 1, vanilla
-- parity). Pure: `inp`, `out` and `c` are tables the adapter owns and reuses; nothing here allocates
-- per call and nothing names a Java global. Constants carry their register id or jar section.
-- Plan 2 ruling (Task 11): HUNGER is no longer the Plan 1 vanilla drain. It is derived from stomach
-- fill and written every tick, so vanilla's eat-time hunger write is overwritten within one push
-- (spec § 4.2): the stomach is the state, hunger the view. The slow clock stamps record.stomachFill
-- (NR_Server_Kinetics.lua); the adapter hands it in as inp.stomachFill. THIRST is untouched in this
-- plan: vanilla's drain stays until Plan 4 derives thirst from the water pool.
-- Every Stats.add / remove / set the jar shows clamps once to [0,1] (#2208, jar § 10), so each
-- vanilla write is one K.clamp here, in vanilla's order: a saturated stat behaves as it does in Java.
-- Kahlua numbers are doubles: the Java float-only chains (the idle timer, the sleep dt and fatigue
-- removal, morale, fitness, the sleep endurance factor) reproduce bit-close, not bit-exact (jar § 9).
local K = NutritionRevamp.kernel
K.fast = {}
local clamp, max = K.clamp, K.max

-- The shipped defines.lua values (jar report "Shared constants" table; media/lua/shared/defines.lua).
-- Outside the fast-path region: called once at install, never per tick.
function K.fast.defaults()
    return {
        thirstIncrease = 8.0e-6,                 -- #0476; defines.lua:9
        thirstSleepingIncrease = 1.0e-6,         -- #0477; :10
        -- the four hunger constants are no longer read by the hunger term (Plan 2: hunger derives from
        -- stomach fill); they stay because the adapter's GLOBAL_KEYS reads them from ZomboidGlobals
        hungerIncrease = 9.6e-6,                 -- #0470; :14
        hungerIncreaseWhenWellFed = 0.0,         -- #0473; :15
        hungerIncreaseWhileAsleep = 1.0e-6,      -- #0472; :17
        hungerIncreaseWhenExercise = 1.92e-5,    -- #0471; :16
        fatigueIncrease = 3.45e-5,               -- #2270; :19
        stressDecrease = 3.0e-5,                 -- jar § 2; :21
        stressFromSoundsMultiplier = 2.0e-5,     -- #2231; :27
        stressFromBiteOrScratch = 5.0e-5,        -- #2231; :28
        stressFromHemophobic = 3.333e-7,         -- #2231; :29
        angerDecrease = 1.0e-4,                  -- #2231; :32
        idleIncrease = 5.0e-4,                   -- jar § 2; :55
        idleDecrease = 6.0e-3,                   -- jar § 2; :56
        imobileEnduranceIncrease = 3.1e-5,       -- #2258; :7
        sleepDelayFraction = 0.5,                -- Plan 1 ruling 7: the mean of Rand.Next(0, d); a game choice
    }
end

-- The input table the adapter fills every tick (one per player, allocated once at hoist time).
-- `sitting` is sitting on the ground or on furniture; `resting` is isResting(): the awake fatigue
-- divisor tests all three, the idleness decrease only the two sitting tests (jar § 2 @94, @598).
-- `sleepingTablet` is getSleepingTabletEffect() > 1000, doDelayToSleep's 0.1 override (jar § 3).
-- `stomachFill` is the slow clock's record.stomachFill (0 empty .. 1 full); `energyState` is the
-- Plan 3 entry point, stubbed at the neutral 1 by the adapter; `rmod` is the slow clock's regeneration
-- coefficient (NR_Kernel_Aerobic.lua), scaling the asleep endurance regeneration. The defaults read full
-- and neutral.
-- `heartyAppetite`, `lightEater` and `foodEaten` are no longer read by the hunger term (Plan 2); they
-- stay filled for Plan 3/4's appetite and energy terms.
function K.fast.input()
    return {
        M = 0, D = 0, sd = 1, asleep = false, ghost = false,
        hunger = 0, thirst = 0, fatigue = 0, endurance = 1, stress = 0, anger = 0, idleness = 0, morale = 1, nicotine = 0,
        highThirst = false, lowThirst = false, heartyAppetite = false, lightEater = false, needsLess = false,
        needsMore = false, hemophobic = false, deaf = false, insomniac = false, nightOwl = false,
        sitting = false, resting = false, foodEaten = 0, exercising = false, running = false,
        thermoFatigue = 1, thermoFluids = 1, soundStress = 0, partsBitten = 0, partsScratched = 0,
        infected = false, fakeInfected = false, totalBlood = 0, veryClose = 0, chasing = 0,
        currentlyIdle = false, hasSquare = false, sameSquare = false, inRoom = false, idleTimer = 0,
        bedFactor = 1, timeOfSleep = 0, delayToSleep = 0, timeOfDay = 0, minutesPerDay = 60,
        endRegen = 1, recoveryMod = 1, allAsleep = false, fitnessLevel = 0, unlimitedEndurance = false,
        painLevel = 0, stressMoodle = 0, sleepingTablet = false, sleepTransition = false,
        stomachFill = 1, energyState = 1, rmod = 1,
    }
end

-- The output table: the seven stats' new values plus the side-effect requests and the mirrors.
function K.fast.output()
    return {
        hunger = 0, thirst = 0, fatigue = 0, endurance = 1, lastEndurance = 1, stress = 0, anger = 0,
        idleness = 0, resetIdleness = false, morale = 1, fitness = 0, autoDrink = true,
        idleTimer = 0, timeOfSleep = 0, delayToSleep = 0,
    }
end

-- The per-tick hunger target from the stomach fill and the energy state. Judgement: an empty stomach
-- reads as hunger 1, a full one as 0, linear between; energyState scales it and, under deficit
-- (energyState > 1), adds a floor 0.15 * (energyState - 1), so a starving character who just ate bulk
-- still feels hungry (Plan 3 ruling 14, a game choice). Clamped to [0, 1]. Called from inside the
-- region: a Lua call, no allocation, no `^` or math.*.
function K.fast.hungerTarget(fill, energyState)
    return K.clamp((1 - fill) * energyState + 0.15 * K.max(0, energyState - 1), 0, 1) -- ruling 14
end

-- @fastpath
-- One update. s = M × D is the game-seconds elapsed (jar § 9).
function K.fast.step(inp, out, c)
    local M, D, sd = inp.M, inp.D, inp.sd
    local s = M * D
    local F03 = 0.30000001192092896                         -- the float 0.3f the jar compares against (§ 9)

    -- 7. the endurance stub: stamp, then the cheat (#2215)
    out.lastEndurance = inp.endurance
    local endurance = inp.endurance
    if inp.unlimitedEndurance then
        endurance = 1
    end

    -- 1. thirst (#0476, #0477, #0486, #0478, #0560)
    local thirst = inp.thirst
    if not inp.ghost then
        local trait = 1
        if inp.highThirst then
            trait = trait * 2
        end
        if inp.lowThirst then
            trait = trait * 0.5
        end
        if inp.asleep then
            thirst = thirst + c.thirstSleepingIncrease * sd * M * D * trait
        else
            local run = 1
            if inp.running then
                run = 1.2
            end
            thirst = thirst + c.thirstIncrease * sd * M * run * D * trait * inp.thermoFluids
        end
    end
    out.thirst = clamp(thirst, 0, 1)
    out.autoDrink = true                                     -- #2250: called on every pass, outside both gates

    -- stress updater (#2220, #2230, #2226, #2231): each term is its own Stats.add, clamped
    local stress = inp.stress
    if not inp.deaf then
        stress = clamp(stress + inp.soundStress * c.stressFromSoundsMultiplier, 0, 1)
    end
    if inp.partsBitten > 0 then
        stress = clamp(stress + c.stressFromBiteOrScratch * s, 0, 1)
    end
    if inp.partsScratched > 0 then
        stress = clamp(stress + c.stressFromBiteOrScratch * s, 0, 1)
    end
    if inp.infected or inp.fakeInfected then
        stress = clamp(stress + c.stressFromBiteOrScratch * s, 0, 1)
    end
    if inp.hemophobic then
        stress = clamp(stress + inp.totalBlood * c.stressFromHemophobic * (M / 0.8) * D, 0, 1)
    end
    out.anger = clamp(inp.anger - c.angerDecrease * s, 0, 1)

    -- wake state
    local fatigue, idleness = inp.fatigue, inp.idleness
    out.resetIdleness = false
    out.idleTimer = inp.idleTimer
    out.timeOfSleep = inp.timeOfSleep
    out.delayToSleep = inp.delayToSleep
    if inp.asleep then
        -- 3. IsoPlayer.updateStats_Sleeping: endurance (#2261), fatigue (#2276, #2277); hunger below (Plan 2)
        local f = 2
        if inp.allAsleep then
            f = 2 * D
        end
        -- Plan 3 ruling 2: the one endurance arm the handler owns, x the regeneration coefficient
        endurance = clamp(endurance + c.imobileEnduranceIncrease * inp.endRegen * inp.recoveryMod * M * f * inp.rmod, 0, 1)
        local dt = 1 / inp.minutesPerDay / 60 * M / 2         -- game-hours this update (jar § 3, § 9)
        if inp.sleepTransition then
            -- Plan 1 ruling 7: the two mirrors, seeded as SleepingEvent.doDelayToSleep builds d (jar § 3)
            local d = 0.3
            if inp.insomniac then
                d = 1.0
            end
            if inp.painLevel > 0 then
                d = d + (1 + 0.2 * inp.painLevel)
            end
            if inp.stressMoodle > 0 then
                d = d * 1.2
            end
            d = d * inp.bedFactor
            if inp.nightOwl then
                d = d * 0.5
            end
            if inp.sleepingTablet then
                d = 0.1
            end
            if d > 2.0 then
                d = 2.0
            end
            out.timeOfSleep = inp.timeOfDay
            out.delayToSleep = inp.timeOfDay + d * c.sleepDelayFraction
        end
        if fatigue > 0 then
            local ff = 1
            if inp.insomniac then
                ff = ff * 0.5
            end
            if inp.nightOwl then
                ff = ff * 1.4
            end
            out.timeOfSleep = out.timeOfSleep + dt
            if out.timeOfSleep > out.delayToSleep then
                local t = 1
                if inp.needsLess then
                    t = t * 0.75
                elseif inp.needsMore then
                    t = t * 1.18
                end
                if fatigue <= F03 then
                    fatigue = fatigue - dt / (7 * t) * 0.3 * ff * inp.bedFactor
                else
                    fatigue = fatigue - dt / (5 * t) * 0.7 * ff * inp.bedFactor
                end
            end
        end
    else
        -- 2. updateStats_Awake: stress decay, fatigue, idleness (jar § 2; #2270, #2271); hunger below (Plan 2)
        stress = clamp(stress - c.stressDecrease * s, 0, 1)
        local endDef = max(F03, 1 - endurance)              -- reads ENDURANCE after the stub's cheat reset
        local sleepTrait = 1
        if inp.needsLess then
            sleepTrait = 0.7
        end
        if inp.needsMore then
            sleepTrait = 1.3
        end
        local rest = 1
        if inp.sitting or inp.resting then
            rest = 1.5
        end
        fatigue = fatigue + c.fatigueIncrease * sd * endDef * s * sleepTrait * inp.thermoFatigue / rest
        -- the idle-square timer mirror (Plan 1 ruling 8), then idleness
        if inp.sameSquare then
            if out.idleTimer <= 3600 then
                out.idleTimer = out.idleTimer + s
            end
        else
            out.idleTimer = 0
        end
        if inp.veryClose > 0 or inp.chasing >= 3 then
            idleness = 0
            out.resetIdleness = true
        elseif inp.currentlyIdle and inp.hasSquare then
            if inp.sameSquare and out.idleTimer >= 1800 then
                idleness = clamp(idleness + c.idleIncrease * s, 0, 1)
            end
            if inp.inRoom then
                idleness = clamp(idleness + c.idleIncrease / 3 * s, 0, 1)
            end
        elseif not inp.sitting then
            idleness = clamp(idleness - c.idleDecrease * s, 0, 1)
        end
    end
    -- hunger (Plan 2 ruling): the stomach's view, written every tick whatever the stat read
    local hunger = K.fast.hungerTarget(inp.stomachFill, inp.energyState)
    out.hunger = clamp(hunger, 0, 1)
    out.fatigue = clamp(fatigue, 0, 1)
    out.stress = clamp(stress, 0, 1)
    out.idleness = clamp(idleness, 0, 1)
    out.endurance = clamp(endurance, 0, 1)

    -- 4. morale (jar § 4): getNicotineStress reads STRESS after the stress and wake-state updaters;
    -- never lowered, pinned at 1 within two updates
    local ns = clamp(out.stress + inp.nicotine, 0, 1)
    local m = (1 - ns - 0.5) * 1e-4
    if m > 0 then
        m = m + 0.5
    end
    out.morale = clamp(inp.morale + clamp(m, 0, 1), 0, 1)

    -- 6. fitness (#2223)
    out.fitness = clamp(inp.fitnessLevel / 5 - 1, -1, 1)
end
-- @endfastpath
