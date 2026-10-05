-- NR_Server_Fast.lua -- the fast clock: the Hook.CalculateStats takeover handler (spec § 4.1).
-- Registration is itself the takeover (#2238): the hook answers true for any registrant, the
-- handler's return is discarded, and a raise leaves the seven stats frozen for that update -- so
-- the body runs inside one rim guard (Plan 1 ruling 4) and, after three consecutive failures for
-- a player, the handler removes itself and vanilla resumes (ruling 9, logged at level 1).
-- Every Java member is hoisted once per player (#0935); the per-tick body re-indexes nothing.
-- Plan 4 (ruling 8): THIRST is the water pool's view -- the region reads h.record.fluids.thirstTarget,
-- which NR_Server_Nutrients stamps on the slow clock, and writes it. A record with no fluids table yet
-- (a pre-Plan-4 record on first sight) hands the stat through, so vanilla's thirst is frozen at its
-- last value until the slow clock stamps a target. autoDrink is bracketed (ruling 9): see the body.
-- server/ files load alphabetically, so this file runs before NR_Server_Options and
-- NR_Server_Players: every append to their lists happens in the OnServerStarted handler below.
local NR = NutritionRevamp
local K = NR.kernel
-- The limitations list is the handler's self-report. The mod ships no test hook: no sentinel arm
-- (player modData is client-writable), so X35's running arm reads one from a probe mod's own handler.
NR.server.fast = { h = {}, byChar = {}, mode = 2, closure = nil, registered = false, wired = false,
                   stats = { calls = 0, failures = 0, disabledAt = nil, byCharHits = 0, perPlayer = {} },
                   limitations = { "idle-square timer mirrored (engine field frozen under takeover; boredom reads it)",
                                   "sleep delay mirrored with sleepDelayFraction (vanilla draws it at random)",
                                   "tripping angle dropped (nothing reads it)",
                                   "after a respawn the fast clock may read the dead character's stomachFill for at most one slow-clock minute until onMinute refreshes h.record; the adopt-before-OnNewGame order is unverified (a Plan 8 reading)" } }
local FAST = NR.server.fast
local C = K.fast.defaults()

-- The ZomboidGlobals Lua table is what the Java constants are loaded from (defines.lua); a server
-- that edits it is followed. Read once at install, never per tick.
local GLOBAL_KEYS = { thirstIncrease = "ThirstIncrease", thirstSleepingIncrease = "ThirstSleepingIncrease",
    hungerIncrease = "HungerIncrease", hungerIncreaseWhenWellFed = "HungerIncreaseWhenWellFed",
    hungerIncreaseWhileAsleep = "HungerIncreaseWhileAsleep", hungerIncreaseWhenExercise = "HungerIncreaseWhenExercise",
    fatigueIncrease = "FatigueIncrease", stressDecrease = "StressDecrease",
    stressFromSoundsMultiplier = "StressFromSoundsMultiplier", stressFromBiteOrScratch = "StressFromBiteOrScratch",
    stressFromHemophobic = "StressFromHemophobic", angerDecrease = "AngerDecrease",
    idleIncrease = "IdleIncrease", idleDecrease = "IdleDecrease", imobileEnduranceIncrease = "ImobileEnduranceIncrease" }

local function readConstants()
    local zg = ZomboidGlobals
    if type(zg) ~= "table" then return end
    for field, key in pairs(GLOBAL_KEYS) do
        if type(zg[key]) == "number" then C[field] = zg[key] end
    end
end

-- Fatigue restoration's bed factor (IsoPlayer.updateStats_Sleeping @109-@244, #2276) and the
-- fall-asleep delay's (SleepingEvent.doDelayToSleep @70-@215, jar § 3): two different ladders.
local BED = { badBed = 0.9, badBedPillow = 0.95, averageBedPillow = 1.05, goodBed = 1.1, goodBedPillow = 1.15,
              floor = 0.6, floorPillow = 0.75 }
local DELAY_BED = { badBed = 1.3, badBedPillow = 1.25, goodBed = 0.8, goodBedPillow = 0.6, floor = 1.6,
                    floorPillow = 1.45, averageBedPillow = 1.0 }

-- The world age in hours, for a record the store creates at hoist time (its firstSeen stamp).
local function worldAge()
    if getGameTime == nil then return 0 end
    local ok, gt = pcall(getGameTime)
    local okA, age = NR.call(ok and gt or nil, "getWorldAgeHours")
    if okA and type(age) == "number" then return age end
    return 0
end

-- Hoist: one table of handles per player, filled at first sight. A member that is nil here is
-- recorded in h.missing; an optional term's member (thermoregulator, sounds, wounds, blood, the
-- all-asleep test, the tablet) disables that term, and a core member's absence raises in the body,
-- which the rim guard turns into the three-strike failover to vanilla.
local function hoist(username, p)
    local h = { username = username, p = p, inp = K.fast.input(), out = K.fast.output(), missing = {},
                wasAsleep = false, calls = 0, fails = 0 }
    local function want(obj, name)
        if obj == nil then
            h.missing[#h.missing + 1] = name
            return nil
        end
        local m = obj[name]
        if m == nil then h.missing[#h.missing + 1] = name end
        return m
    end
    h.stats = p:getStats()
    h.get, h.set = want(h.stats, "get"), want(h.stats, "set")
    h.setLastEndurance = want(h.stats, "setLastEndurance")
    h.getNumVeryClose, h.getNumChasing = want(h.stats, "getNumVeryCloseZombies"), want(h.stats, "getNumChasingZombies")
    h.traits = p:getCharacterTraits()
    h.traitGet = want(h.traits, "get")
    h.moodles = p:getMoodles()
    h.moodleLevel = want(h.moodles, "getMoodleLevel")
    h.bd = p:getBodyDamage()
    h.thermo = h.bd and h.bd:getThermoregulator() or nil
    h.getFatigueMult, h.getFluidsMult = want(h.thermo, "getFatigueMultiplier"), want(h.thermo, "getFluidsMultiplier")
    h.partsBitten, h.partsScratched = want(h.bd, "getNumPartsBitten"), want(h.bd, "getNumPartsScratched")
    h.isInfected, h.isFakeInfected = want(h.bd, "IsInfected"), want(h.bd, "IsFakeInfected")
    h.isAsleep, h.isGhost = want(p, "isAsleep"), want(p, "isGhostMode")
    h.isSitGround, h.isSitFurniture, h.isResting = want(p, "isSitOnGround"), want(p, "isSittingOnFurniture"), want(p, "isResting")
    h.IsRunning, h.isPlayerMoving, h.isCurrentState = want(p, "IsRunning"), want(p, "isPlayerMoving"), want(p, "isCurrentState")
    h.isCurrentlyIdle, h.getCurrentSquare, h.getLastSquare = want(p, "isCurrentlyIdle"), want(p, "getCurrentSquare"), want(p, "getLastSquare")
    h.getTotalBlood, h.getBedType, h.getPerkLevel = want(p, "getTotalBlood"), want(p, "getBedType"), want(p, "getPerkLevel")
    h.isUnlimited, h.autoDrink, h.setTimeOfSleep = want(p, "isUnlimitedEndurance"), want(p, "autoDrink"), want(p, "setTimeOfSleep")
    h.getRecoveryMod, h.getX, h.getY, h.getZ = want(p, "getRecoveryMod"), want(p, "getX"), want(p, "getY"), want(p, "getZ")
    h.getTabletEffect = want(p, "getSleepingTabletEffect")
    -- the player's store record (a Lua table on global modData, not a Java member): the region reads
    -- its stomachFill field, which the slow clock (NR_Server_Kinetics) stamps; an empty stand-in
    -- when the store is not attached reads full, and the slow clock's onMinute refreshes the handle
    h.record = (NR.server.store and NR.server.store.get(username, worldAge())) or {}
    local getIdle = want(p, "getIdleSquareTime")
    h.out.idleTimer = getIdle and getIdle(p) or 0         -- seed the mirror where the engine timer stands
    h.gt = getGameTime and getGameTime() or nil
    h.getMult, h.getDMPD, h.getMPD, h.getTOD = want(h.gt, "getMultiplier"), want(h.gt, "getDeltaMinutesPerDay"), want(h.gt, "getMinutesPerDay"), want(h.gt, "getTimeOfDay")
    h.so = getSandboxOptions and getSandboxOptions() or nil
    h.getSD, h.getEndRegen = want(h.so, "getStatsDecreaseMultiplier"), want(h.so, "getEnduranceRegenMultiplier")
    h.wsm = getWorldSoundManager and getWorldSoundManager() or nil
    h.getStressFromSounds = want(h.wsm, "getStressFromSounds")
    -- getStressFromSounds takes three ints (PZMath.fastfloor of the position, jar dump updateStress
    -- @29-@46): the floor is hoisted as a plain function value so the region never names math.
    h.floor = math.floor
    h.swipe = SwipeStatePlayer and SwipeStatePlayer.instance and SwipeStatePlayer.instance() or nil
    h.allPlayersAsleep = want(IsoPlayer, "allPlayersAsleep")
    h.fitnessPerk = Perks and Perks.Fitness or nil
    if h.fitnessPerk == nil then h.missing[#h.missing + 1] = "Perks.Fitness" end
    -- the enum handles (CharacterStat, MoodleType, CharacterTrait are exposed, #2248)
    h.HUNGER, h.THIRST, h.FATIGUE, h.ENDURANCE = CharacterStat.HUNGER, CharacterStat.THIRST, CharacterStat.FATIGUE, CharacterStat.ENDURANCE
    h.STRESS, h.ANGER, h.IDLENESS, h.MORALE = CharacterStat.STRESS, CharacterStat.ANGER, CharacterStat.IDLENESS, CharacterStat.MORALE
    h.NICOTINE, h.FITNESS = CharacterStat.NICOTINE_WITHDRAWAL, CharacterStat.FITNESS
    h.FOOD_EATEN, h.PAIN, h.STRESSM = MoodleType.FOOD_EATEN, MoodleType.PAIN, MoodleType.STRESS
    h.T = { highThirst = CharacterTrait.HIGH_THIRST, lowThirst = CharacterTrait.LOW_THIRST,
            heartyAppetite = CharacterTrait.HEARTY_APPETITE, lightEater = CharacterTrait.LIGHT_EATER,
            needsLess = CharacterTrait.NEEDS_LESS_SLEEP, needsMore = CharacterTrait.NEEDS_MORE_SLEEP,
            hemophobic = CharacterTrait.HEMOPHOBIC, deaf = CharacterTrait.DEAF,
            insomniac = CharacterTrait.INSOMNIAC, nightOwl = CharacterTrait.NIGHT_OWL }
    if #h.missing > 0 then
        NR.log.say(1, "fast: " .. username .. " missing members: " .. table.concat(h.missing, ", ") .. " -- an optional term is disabled; a core member raises and the rim guard fails over to vanilla")
    end
    FAST.stats.perPlayer[username] = { calls = 0, failures = 0 }
    return h
end

-- @hoisted h, inp, out, stats, traitGet, moodleLevel, K, sq
-- @fastpath
local function body(h)
    local p, inp, out, stats = h.p, h.inp, h.out, h.stats
    local get = h.get
    inp.M = h.getMult(h.gt)
    inp.D = h.getDMPD(h.gt)
    inp.minutesPerDay = h.getMPD(h.gt)
    inp.timeOfDay = h.getTOD(h.gt)
    inp.sd = h.getSD(h.so)
    inp.endRegen = h.getEndRegen(h.so)
    inp.hunger = get(stats, h.HUNGER)
    inp.thirst = get(stats, h.THIRST)
    local fl = h.record.fluids                            -- Plan 4: the pool's view; nil passes the stat through
    inp.thirstTarget = fl and fl.thirstTarget or inp.thirst
    inp.fatigue = get(stats, h.FATIGUE)
    inp.endurance = get(stats, h.ENDURANCE)
    inp.stress = get(stats, h.STRESS)
    inp.anger = get(stats, h.ANGER)
    inp.idleness = get(stats, h.IDLENESS)
    inp.morale = get(stats, h.MORALE)
    inp.nicotine = get(stats, h.NICOTINE)
    local asleep = h.isAsleep(p)
    inp.sleepTransition = asleep and not h.wasAsleep
    h.wasAsleep = asleep
    inp.asleep = asleep
    inp.ghost = h.isGhost(p)
    local T, tg = h.T, h.traitGet
    inp.highThirst = tg(h.traits, T.highThirst)
    inp.lowThirst = tg(h.traits, T.lowThirst)
    inp.heartyAppetite = tg(h.traits, T.heartyAppetite)
    inp.lightEater = tg(h.traits, T.lightEater)
    inp.needsLess = tg(h.traits, T.needsLess)
    inp.needsMore = tg(h.traits, T.needsMore)
    inp.hemophobic = tg(h.traits, T.hemophobic)
    inp.deaf = tg(h.traits, T.deaf)
    inp.insomniac = tg(h.traits, T.insomniac)
    inp.nightOwl = tg(h.traits, T.nightOwl)
    inp.sitting = h.isSitGround(p) or h.isSitFurniture(p)
    inp.resting = h.isResting(p)
    inp.foodEaten = h.moodleLevel(h.moodles, h.FOOD_EATEN)
    inp.painLevel = h.moodleLevel(h.moodles, h.PAIN)
    inp.stressMoodle = h.moodleLevel(h.moodles, h.STRESSM)
    inp.exercising = (h.IsRunning(p) and h.isPlayerMoving(p)) or (h.swipe ~= nil and h.isCurrentState(p, h.swipe))
    inp.running = false                                   -- the local-instance test is false on a dedicated server (jar § 1)
    inp.thermoFatigue = h.getFatigueMult and h.getFatigueMult(h.thermo) or 1
    inp.thermoFluids = h.getFluidsMult and h.getFluidsMult(h.thermo) or 1
    inp.soundStress = h.getStressFromSounds and h.getStressFromSounds(h.wsm, h.floor(h.getX(p)), h.floor(h.getY(p)), h.floor(h.getZ(p))) or 0
    inp.partsBitten = h.partsBitten and h.partsBitten(h.bd) or 0
    inp.partsScratched = h.partsScratched and h.partsScratched(h.bd) or 0
    inp.infected = h.isInfected and h.isInfected(h.bd) or false
    inp.fakeInfected = h.isFakeInfected and h.isFakeInfected(h.bd) or false
    inp.totalBlood = h.getTotalBlood and h.getTotalBlood(p) or 0
    inp.veryClose = h.getNumVeryClose(stats)
    inp.chasing = h.getNumChasing(stats)
    inp.currentlyIdle = h.isCurrentlyIdle(p)
    local sq = h.getCurrentSquare(p)
    inp.hasSquare = sq ~= nil
    inp.sameSquare = sq == h.getLastSquare(p)             -- nil == nil is true, as in Java
    inp.inRoom = sq ~= nil and sq:isInARoom()
    inp.idleTimer = out.idleTimer
    inp.timeOfSleep = out.timeOfSleep
    inp.delayToSleep = out.delayToSleep
    local bed = h.getBedType(p)
    if inp.sleepTransition then
        -- the transition tick seeds the delay mirror from doDelayToSleep's ladder; fatigue cannot be
        -- restored on this tick (timeOfSleep is reset to now, below the delay), so its ladder is unused
        inp.bedFactor = DELAY_BED[bed] or 1
        inp.sleepingTablet = h.getTabletEffect ~= nil and h.getTabletEffect(p) > 1000
    else
        inp.bedFactor = BED[bed] or 1
    end
    inp.recoveryMod = h.getRecoveryMod(p)
    inp.allAsleep = h.allPlayersAsleep ~= nil and h.allPlayersAsleep()
    inp.fitnessLevel = h.getPerkLevel(p, h.fitnessPerk)
    inp.unlimitedEndurance = h.isUnlimited(p)
    local fill = h.record.stomachFill                     -- Plan 2: hunger derives from it; nil reads full (the seed)
    if fill == nil or fill ~= fill then fill = 1 end      -- NaN reads full too (#2833): K.clamp passes NaN through
    inp.stomachFill = fill
    local rec_body = h.record.body                        -- Plan 3: the slow clock stamps the two scalars here
    local es = 1
    local rm = 1
    if rec_body ~= nil then
        es = rec_body.energyState
        rm = rec_body.rmod
    end
    if es == nil or es ~= es then es = 1 end              -- nil or NaN reads neutral, as the fill does
    if rm == nil or rm ~= rm then rm = 1 end
    inp.energyState = es
    inp.rmod = rm

    K.fast.step(inp, out, C)

    h.setLastEndurance(stats, out.lastEndurance)
    local set = h.set
    set(stats, h.THIRST, out.thirst)
    set(stats, h.STRESS, out.stress)
    set(stats, h.ANGER, out.anger)
    set(stats, h.HUNGER, out.hunger)
    set(stats, h.FATIGUE, out.fatigue)
    set(stats, h.IDLENESS, out.idleness)
    set(stats, h.MORALE, out.morale)
    set(stats, h.FITNESS, out.fitness)
    if asleep then
        set(stats, h.ENDURANCE, out.endurance)            -- the sleep regeneration arm the hook skips (jar § 3)
        h.setTimeOfSleep(p, out.timeOfSleep)
    elseif inp.unlimitedEndurance then
        set(stats, h.ENDURANCE, 1)
    end
    -- #2250: vanilla calls autoDrink on every pass. Ruling 9's bracket: the THIRST drop across the call is
    -- the sip (litres = 2 x the drop, x151w #2939-#2941), held in fl.autoDrop for the slow clock to land as
    -- water; while a drop is pending the call is SKIPPED (the only off switch: setAutoDrink reverts), so at
    -- most one sip lands per slow minute and the view falls at the next slow tick (ruling T1-1)
    if fl == nil then
        h.autoDrink(p)
    else
        local pending = fl.autoDrop or 0                  -- nil (a table the slow clock has not filled) reads 0
        if not (pending > 0) then
            local t0 = get(stats, h.THIRST)
            h.autoDrink(p)
            local t1 = get(stats, h.THIRST)
            if t1 < t0 then
                fl.autoDrop = pending + (t0 - t1)
            end
        end
    end
end
-- @endfastpath

-- The hook hands the character and nothing else (jar § 8). The steady-state tick finds its handles
-- by the character object itself (FAST.byChar, a plain Kahlua table index: the engine hands the same
-- IsoPlayer instance every update); only a miss -- first sight or a respawn -- reads the username,
-- a Java member on an object this file did not hoist, behind this guard outside the region.
local function keyOf(character)
    local ok, username = pcall(character.getUsername, character)
    if ok then return username end
    return nil
end

-- A character whose handles are absent or stale (first update before the slow clock's first
-- sight, or a respawn: a new IsoPlayer under the same username, which the slow clock does not
-- report again) is hoisted here, once, outside the region. A hoist that raises disables the
-- takeover, so vanilla resumes rather than a player's stats freezing.
function FAST.adopt(username, character)
    local old = FAST.h[username]
    if old ~= nil and old.p ~= character then FAST.byChar[old.p] = nil end
    local ok, h = pcall(hoist, username, character)
    if ok then
        FAST.h[username] = h
        FAST.byChar[character] = h
        return h
    end
    FAST.lastError = h
    NR.log.say(1, "fast: hoist failed for " .. tostring(username) .. ": " .. tostring(h))
    FAST.disable(username, "hoist failed")
    return nil
end

-- @fastpath
local function handler(character)
    local h = FAST.byChar[character]
    if h == nil then
        -- first sight or a respawn (rare): the guarded username read, then the hoist if stale
        local username = keyOf(character)
        if username == nil then return end
        h = FAST.h[username]
        if h == nil or h.p ~= character then
            h = FAST.adopt(username, character)
            if h == nil then return end
        end
        FAST.byChar[character] = h
    else
        FAST.stats.byCharHits = FAST.stats.byCharHits + 1
    end
    h.calls = h.calls + 1
    FAST.stats.calls = FAST.stats.calls + 1
    local ok, err = pcall(body, h)                        -- @rimguard
    if ok then
        h.fails = 0
        return
    end
    h.fails = h.fails + 1
    FAST.stats.failures = FAST.stats.failures + 1
    FAST.stats.perPlayer[h.username].failures = h.fails
    FAST.lastError = err
    if h.fails >= 3 then FAST.disable(h.username, "three consecutive failures") end
end
-- @endfastpath
FAST.handler = handler

-- Outside the region: the failure is logged with its message (string concatenation) on the slow
-- clock, which reads FAST.lastError and the per-player failure counts once a minute.
function FAST.install()
    if FAST.registered then return true end
    if Hook == nil or Hook.CalculateStats == nil or Hook.CalculateStats.Add == nil then
        NR.log.say(1, "fast: Hook.CalculateStats is absent; takeover unavailable")
        return false
    end
    readConstants()
    FAST.closure = FAST.closure or function(character) handler(character) end
    Hook.CalculateStats.Add(FAST.closure)                 -- a dot, never a colon (jar § 11)
    FAST.registered, FAST.mode = true, 1
    NR.log.say(1, "fast: takeover handler registered")
    return true
end

function FAST.uninstall()
    if not FAST.registered then return end
    if Hook ~= nil and Hook.CalculateStats ~= nil and Hook.CalculateStats.Remove ~= nil then
        Hook.CalculateStats.Remove(FAST.closure)          -- the same closure object (jar § 11)
    end
    FAST.registered, FAST.mode = false, 2
    NR.log.say(1, "fast: takeover handler removed")
end

function FAST.disable(username, reason)
    FAST.stats.disabledAt = tostring(reason) .. " for " .. tostring(username)
    FAST.uninstall()
    NR.log.say(1, "fast: DISABLED (" .. FAST.stats.disabledAt .. "); vanilla stat update resumed")
end

-- Mode: 1 takeover registers; 2 overlay registers nothing (and in this plan writes nothing).
-- In overlay mode the handler is not registered, so hunger stays vanilla's drain and is NOT derived
-- from the stomach -- an intake consequence of the mode choice (the stomach still fills and empties on
-- the slow clock; nothing reads its fill into HUNGER).
local function applyMode(opts)
    if FAST.stats.disabledAt ~= nil then return end
    if opts.mode == 1 then FAST.install() else FAST.uninstall() end
end

local function onFirstSight(username, player)
    if player == nil then return end
    local h = FAST.h[username]
    if h == nil or h.p ~= player then
        if h ~= nil then FAST.byChar[h.p] = nil end
        h = hoist(username, player)
        FAST.h[username] = h
        FAST.byChar[player] = h
    end
end

local function onDeparture(username)
    local h = FAST.h[username]
    if h ~= nil then FAST.byChar[h.p] = nil end
    FAST.h[username] = nil
end

-- The per-player call and failure counts are read on the slow clock, never per tick. The record
-- handle is refreshed here: a respawn replaces the record (NR_Server_Store reset), and the region
-- must read the table the slow clock stamps.
local function onMinute(username, player, record)
    local h = FAST.h[username]
    if h == nil then return end
    if record ~= nil then h.record = record end
    FAST.stats.perPlayer[username].calls = h.calls
    if FAST.lastError ~= nil then
        NR.log.say(2, "fast: handler failed (" .. tostring(FAST.stats.failures) .. " so far): " .. tostring(FAST.lastError))
        FAST.lastError = nil
    end
end

-- Every file has loaded by OnServerStarted: read the options here (the order of the two
-- OnServerStarted handlers is then irrelevant), wire the lists, hoist anyone already seen, apply.
if Events ~= nil and Events.OnServerStarted ~= nil then
    Events.OnServerStarted.Add(function()
        if not NR.isServer() then return end
        NR.server.readOptions("OnServerStarted")
        if not FAST.wired then
            FAST.wired = true
            local P = NR.server.players
            P.onFirstSight[#P.onFirstSight + 1] = onFirstSight
            P.onDeparture[#P.onDeparture + 1] = onDeparture
            P.onMinute[#P.onMinute + 1] = onMinute
            NR.server.options.changed[#NR.server.options.changed + 1] = function(old, new) applyMode(new) end
            for username, player in pairs(P.online) do
                local h = hoist(username, player)
                FAST.h[username] = h
                FAST.byChar[player] = h
            end
        end
        applyMode(NR.server.options)
    end)
end
