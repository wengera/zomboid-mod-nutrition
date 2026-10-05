-- NR_Server_Metabolism.lua -- the body model's slow-clock adapter (Plan 3, spec § 4.3): once per player
-- per game minute, on the players' OnTick stagger and after the stomach step, it creates record.body at
-- first sight, bills the minute's expenditure off the server's metabolic rate, banks the absorbed intake
-- Kinetics handed off, samples the training signal, steps the neural term, closes each elapsed game day
-- (the partition, the strength bookkeeping, adaptive thermogenesis, TAC, the rings), and stamps the
-- drain and regeneration coefficients and the energy state the fast clock reads.
--
-- The activity read (ruling T5-2, run x141a-20261005-111005): the server's thermoregulator TARGET reads
-- -1 at every tick, so it is never read; the RATE classifies but lags activity by tens of seconds and
-- already carries the engine's load factor, which is divided out (ruling 6) before the bucketing.
-- isAsleep wins over the rate. A missing or non-finite rate reads the Default class and counts a bad
-- read. The current timed action is unreadable server-side (getCharacterActions is empty there, X38),
-- so the calorie modifier is always 1 and getCharacterActions is never called.
--
-- Two MET tables, never mixed: expenditure bills the Compendium MET of the class (K.energy.activityMet);
-- the training sample banks the ENGINE's own value of the same class (K.energy.CLASS_MET).
--
-- Every Java read goes through NR.call (index-first) with a default; every Java global is named only
-- inside a function behind a nil check, so the file loads with no engine
-- (testing/tests/kernel/test_metabolism_shape.py). The whole minute runs under one pcall per player and
-- never raises into the players walk. Every field written on record.body is a number, a boolean, a
-- string or a table of numbers (#1495). Slow-clock code: no @fastpath region in this file.
local NR = NutritionRevamp
local K = NR.kernel
NR.server.metabolism = {
    stats = { minutes = 0, days = 0, failures = 0, splits = 0, badReads = 0, skippedDays = 0,
              firstSightMirrors = 0, preconditionWarnings = 0 },
    lastError = nil,
    wired = false,
    limitations = {
        "the run and sprint flags never reach the server (x141a), so a runner bills as a walker and the Running classes are unreachable; the metabolic rate lags activity by tens of seconds; the current timed action is unreadable server-side, so the calorie-modifier bands are unused and timed actions bill at the class rate",
        "an 8.0 rate classifies as ClimbRope, never ForestryAxe (chopping bills 8.0 not 6.5); a 6.0 as HeavyWork, never Fitness",
        "offline time is not integrated; a multi-day catch-up runs days 2..n with pDay 0 (pPrevKg 0 until the next normal close) and reuses today's immobilised reading; the catch-up stamps every close with the catch-up minute's age, so the first blend after an offline gap counts yesterday in full",
        "the disuse arm needs a leg fracture or splint",
        "glycogen, dehydration, iron, caffeine, alcohol, sleep debt and the balance dial are Plan 4/5 inputs held neutral",
        "the drain coefficient is stamped and unapplied until Plan 5",
        "a climb is credited when the minute sample lands inside the climb state; short climbs are missed",
        "the MET-minute bank is mirrored for the panel and feeds no coefficient; the aerobic dose is the band minutes",
        "the engine's inventory weight is read as kilograms",
        "an exhausted idle character's metabolic rate sits at the tired floor (up to the DefaultExercise class), so exhaustion bills as activity until Plan 5 owns endurance",
        "rmod scales the asleep regeneration arm only; under the harness's partial sleep hold it measured 0.904 for a predicted 0.848 (#2899)",
        "a day closes at 07:00 on the default fixture (#2890); the 24 h blends count hours since the last close",
        "an unreadable world age skips the minute; a first sight with an unreadable age sends its mirror without the body, which the next readable minute builds",
    },
}
local MET = NR.server.metabolism

-- The catch-up guard: at most this many day closes per minute; the rest are skipped and counted.
MET.MAX_CLOSES = 7
-- The leg parts whose fracture or splint immobilises (ruling 8).
MET.LEG_PARTS = { "UpperLeg_L", "UpperLeg_R", "LowerLeg_L", "LowerLeg_R" }
-- The build flags read at first sight: the CharacterTrait registry field and the K.body build key.
MET.BUILD_TRAITS = {
    { "ATHLETIC", "athletic" }, { "FIT", "fit" }, { "OUT_OF_SHAPE", "outOfShape" },
    { "UNFIT", "unfit" }, { "STRONG", "strong" }, { "STOUT", "stout" },
}

local function finite(x)
    return type(x) == "number" and x == x and x ~= math.huge and x ~= -math.huge
end

-- The world age, or nil when it cannot be read (the minute is then skipped and counted, never stamped 0).
local function worldAge()
    if getGameTime == nil then return nil end
    local ok, gt = pcall(getGameTime)
    local okA, age = NR.call(ok and gt or nil, "getWorldAgeHours")
    if okA and finite(age) then return age end
    return nil
end

-- A number read off obj:name(...), or dflt when the member is absent or the answer is not finite.
local function num(obj, name, dflt, ...)
    local ok, v = NR.call(obj, name, ...)
    if ok and finite(v) then return v end
    return dflt
end

-- A boolean read off obj:name(...): true only when the member is present and answers true.
local function flag(obj, name, ...)
    local ok, v = NR.call(obj, name, ...)
    return ok and v == true
end

-- An object read off obj:name(...), or nil.
local function obj(o, name, ...)
    local ok, v = NR.call(o, name, ...)
    if ok then return v end
    return nil
end

-- The responder constant R = exp(0.3 z), z the sum of twelve uniform draws minus 6 (an approximate unit
-- normal), clamped [0.5, 1.8] (ruling 16, a game choice): drawn here once, the kernel never draws.
-- ZombRandFloat absent reads R = 1.
local function responder()
    if ZombRandFloat == nil then return 1 end
    local z = -6
    for i = 1, 12 do
        local u = ZombRandFloat(0, 1)
        if not finite(u) then return 1 end
        z = z + u
    end
    return K.clamp(math.exp(0.3 * z), 0.5, 1.8)          -- ruling 16
end

-- First sight: record.body from the character's then-current weight, sex, build traits, Strength level
-- and creation carry factor. getMaxWeightDelta is read ONLY here, before the mod ever writes the delta;
-- an existing record.body is never re-read.
function MET.ensureBody(username, player, record, ageH)
    if record.body ~= nil then return record.body end
    local w = num(obj(player, "getNutrition"), "getWeight", 80)
    local sex = 1
    if flag(player, "isFemale") then sex = 2 end
    local build = {}
    local traits = obj(player, "getCharacterTraits")
    for i = 1, #MET.BUILD_TRAITS do
        local row = MET.BUILD_TRAITS[i]
        local t = CharacterTrait ~= nil and CharacterTrait[row[1]] or nil
        build[row[2]] = t ~= nil and flag(traits, "get", t)
    end
    local l0 = 0
    local perk = Perks ~= nil and Perks.Strength or nil
    if perk ~= nil then l0 = num(player, "getPerkLevel", 0, perk) end
    local traitCarry = num(player, "getMaxWeightDelta", 1.0)
    local r = responder()
    record.body = K.body.new(w, sex, build, l0, traitCarry, r, ageH)
    MET.stats.splits = MET.stats.splits + 1
    NR.log.say(3, "metabolism: first sight of " .. tostring(username) .. " w=" .. tostring(w) .. " sex=" .. sex
        .. " l0=" .. tostring(l0) .. " traitCarry=" .. tostring(traitCarry) .. " r=" .. tostring(r))
    return record.body
end

-- The minute's activity: className, moving, modifier, loadKg, heavyLevel, coldMult, exercising,
-- swiping, immobilised, hourOfDay, maxW, heatLevel, climbClass. ageH (optional) is the minute's world
-- age. climbClass is the K.training.CLIMB_MET class of the climb state the character is in at the
-- sample (a fence vault JumpFence, a window climb ClimbRope), or nil: a per-minute state sample, so a
-- climb shorter than the gap between samples is missed (ruling W-4).
function MET.readActivity(player, ageH)
    local bd = obj(player, "getBodyDamage")
    local thermo = obj(bd, "getThermoregulator")
    local loadKg = num(player, "getInventoryWeight", 0)
    local maxW = num(player, "getMaxWeight", 0)
    local className = "Default"
    local okR, rate = NR.call(thermo, "getMetabolicRate")
    if okR and finite(rate) then
        className = K.energy.classOf(K.energy.stripLoad(rate, loadKg, maxW))
    else
        MET.stats.badReads = MET.stats.badReads + 1
    end
    if flag(player, "isAsleep") then className = "Sleeping" end
    local moving = flag(player, "isPlayerMoving")
    local moodles = obj(player, "getMoodles")
    local heavyLevel = 0
    local heatLevel = 0
    if MoodleType ~= nil then
        if MoodleType.HEAVY_LOAD ~= nil then
            heavyLevel = K.clamp(math.floor(num(moodles, "getMoodleLevel", 0, MoodleType.HEAVY_LOAD)), 0, 4)
        end
        if MoodleType.HYPERTHERMIA ~= nil then
            heatLevel = K.clamp(math.floor(num(moodles, "getMoodleLevel", 0, MoodleType.HYPERTHERMIA)), 0, 4)
        end
    end
    local coldMult = num(thermo, "getEnergyMultiplier", 1)
    local exercising = obj(obj(player, "getFitness"), "getCurrentExe") ~= nil
    local swiping = false
    if SwipeStatePlayer ~= nil and SwipeStatePlayer.instance ~= nil then
        swiping = flag(player, "isCurrentState", SwipeStatePlayer.instance())
    end
    local climbClass = nil
    if ClimbOverFenceState ~= nil and ClimbOverFenceState.instance ~= nil then
        local okI, inst = pcall(ClimbOverFenceState.instance)
        if okI and inst ~= nil and flag(player, "isCurrentState", inst) then climbClass = "JumpFence" end
    end
    if climbClass == nil and ClimbThroughWindowState ~= nil and ClimbThroughWindowState.instance ~= nil then
        local okI, inst = pcall(ClimbThroughWindowState.instance)
        if okI and inst ~= nil and flag(player, "isCurrentState", inst) then climbClass = "ClimbRope" end
    end
    local immobilised = false
    if BodyPartType ~= nil then
        for i = 1, #MET.LEG_PARTS do
            local t = BodyPartType[MET.LEG_PARTS[i]]
            local part = nil
            if t ~= nil then part = obj(bd, "getBodyPart", t) end
            if part ~= nil and (num(part, "getFractureTime", 0) > 0 or flag(part, "isSplint")) then
                immobilised = true
            end
        end
    end
    local age = ageH or worldAge() or 0
    local hourOfDay = age - math.floor(age / 24) * 24
    if getGameTime ~= nil then
        local ok, gt = pcall(getGameTime)
        hourOfDay = num(ok and gt or nil, "getTimeOfDay", hourOfDay)
    end
    return className, moving, 1, loadKg, heavyLevel, coldMult, exercising, swiping, immobilised, hourOfDay,
        maxW, heatLevel, climbClass
end

-- One day close: the disuse day count (before the partition, so the first immobilised day runs with
-- t = 1 off the lean mass it began on), the partition, the strength bookkeeping (reads ebDay), the
-- training ring, TAC, the partition ring (pushes today's balance into eb7, zeroes the day accumulators,
-- advances dayIndex, stamps lastCloseAgeH), then adaptive thermogenesis. Each reader runs after the
-- writer of what it reads (the x141c one-close lag): the training ring shifts the closing day in BEFORE
-- TAC reads the week (run x141c-20261005-132133); TAC's energy gate reads the closing day's inDay and
-- exKcalDay (ruling W-1) and its immobilised flag (ruling W-2) before the partition ring zeroes them;
-- the AT step reads deficitWeek AFTER the partition ring, so the week it reads includes today.
local function closeDay(body, w, immobilised, ageH)
    if immobilised then
        if body.tDisuse == 0 then body.lm0dis = body.lm end
        body.tDisuse = body.tDisuse + 1
    else
        body.tDisuse = 0
    end
    local dStr, dHyp, maintained = K.training.doses(body)
    local pPerKg = body.pDay / w
    K.partition.day(body, dHyp, dStr, pPerKg, immobilised)
    K.strength.closeDay(body, body.dayIndex)
    K.training.closeDay(body)
    local m1, hard = K.training.weekMinutes(body)
    K.aerobic.tacDay(body, m1, hard, 1, K.aerobic.gProt(pPerKg), K.aerobic.gEnergy(body.inDay, body.exKcalDay, body.lm), 1, 1, immobilised)
    body.pPrevKg = pPerKg
    body.inDayClosed = body.inDay                        -- the closing day's absorbed kcal, for NR_Server_Nutrients' refeeding close
    K.partition.closeDay(body, ageH)
    body.at = K.energy.atStep(body.at, K.energy.atTarget(body.fm, body.fmRef), K.partition.deficitWeek(body), 1)
    MET.stats.days = MET.stats.days + 1
end

-- The self-heal (the #2833 pattern), run before the minute's arithmetic and again after its stamps: a
-- non-finite scalar or ring slot is stamped its neutral and the pass counts one failure. Masses heal to
-- their creation values (a non-finite creation value to the current mass, else the 80 kg split); rmod's
-- protein input to the neutral P_LOW; dayIndex to the day of the world age (a NaN would stop every day
-- close); lastAgeH and lastCloseAgeH to the world age; a ring slot to 0 (mass7's to the current mass).
-- The backfill, uncounted: a field or ring a record made before it existed lacks (pPrevKg,
-- lastCloseAgeH, exKcalDay; the p7, carb7 and lip7 rings of a pre-Task-15 body; an absent nHist or
-- bandWeek) is created at its neutral. The creation scalars heal too: r and traitCarry to 1, l0 to the
-- Strength level read now, tDisuse to 0, lm0dis to the current lean mass, nPeak to 0 and tPeakD to
-- dayIndex; every nHist and bandWeek slot to 0. Every healed field is named in the pass's counted
-- failure. This file owns the rings: the Weight mirror and the partition ring read them and rebuild
-- nothing.
MET.NEUTRAL = { energyState = 1, dmod = 1, rmod = 1, tac = 1, at = 0, n = 0, vStr = 0, vHyp = 0,
                vStrHigh = 0, inDay = 0, eeDay = 0, ebDay = 0, actKcalDay = 0, exKcalDay = 0, pDay = 0,
                carbDay = 0, lipDay = 0, alcDay = 0, metMinDay = 0, band1Day = 0, band2Day = 0, cumDef = 0,
                r = 1, traitCarry = 1, tDisuse = 0, nPeak = 0 }
MET.NEUTRAL_KEYS = { "energyState", "dmod", "rmod", "tac", "at", "n", "vStr", "vHyp", "vStrHigh", "inDay",
                     "eeDay", "ebDay", "actKcalDay", "exKcalDay", "pDay", "carbDay", "lipDay", "alcDay",
                     "metMinDay", "band1Day", "band2Day", "cumDef", "r", "traitCarry", "tDisuse", "nPeak" }
-- The rings whose slots heal to 0 (slot 7 is yesterday); mass7 heals to the current mass.
MET.ZERO_RINGS = { "eb7", "p7", "carb7", "lip7" }

local function heal(username, body, ageH, player)
    local bad = nil
    local function mark(name)
        if bad == nil then bad = name else bad = bad .. "," .. name end
    end
    if body.pPrevKg == nil then body.pPrevKg = K.aerobic.P_LOW end
    if body.lastCloseAgeH == nil then body.lastCloseAgeH = ageH end
    if body.exKcalDay == nil then body.exKcalDay = 0 end
    for r = 1, #MET.ZERO_RINGS do
        local key = MET.ZERO_RINGS[r]
        if type(body[key]) ~= "table" then
            local ring = {}
            for j = 1, 7 do ring[j] = 0 end
            body[key] = ring
        end
    end
    if type(body.mass7) ~= "table" then body.mass7 = {} end
    if type(body.nHist) ~= "table" then
        local hist = {}
        for j = 1, K.strength.MEM_HOLD_DAYS do hist[j] = 0 end
        body.nHist = hist
    end
    if type(body.bandWeek) ~= "table" then body.bandWeek = {} end
    for i = 1, 7 do
        if type(body.bandWeek[i]) ~= "table" then body.bandWeek[i] = { 0, 0 } end
    end
    if not finite(body.fm0) or not finite(body.lm0) then
        local fmS, lmS = K.body.split(80, body.sex == 2 and 2 or 1, {})
        if not finite(body.fm0) then
            if finite(body.fm) then body.fm0 = body.fm else body.fm0 = fmS end
            mark("fm0")
        end
        if not finite(body.lm0) then
            if finite(body.lm) then body.lm0 = body.lm else body.lm0 = lmS end
            mark("lm0")
        end
    end
    if not finite(body.fm) then body.fm = body.fm0; mark("fm") end
    if not finite(body.lm) then body.lm = body.lm0; mark("lm") end
    if not finite(body.fmRef) then body.fmRef = body.fm; mark("fmRef") end
    if not finite(body.pPrevKg) then body.pPrevKg = K.aerobic.P_LOW; mark("pPrevKg") end
    if not finite(body.dayIndex) then body.dayIndex = math.floor(ageH / 24); mark("dayIndex") end
    if not finite(body.lastAgeH) then body.lastAgeH = ageH; mark("lastAgeH") end
    if not finite(body.lastCloseAgeH) then body.lastCloseAgeH = ageH; mark("lastCloseAgeH") end
    local keys = MET.NEUTRAL_KEYS
    for i = 1, #keys do
        local k = keys[i]
        if not finite(body[k]) then body[k] = MET.NEUTRAL[k]; mark(k) end
    end
    if not finite(body.l0) then
        local l0 = 0
        local perk = Perks ~= nil and Perks.Strength or nil
        if perk ~= nil then l0 = num(player, "getPerkLevel", 0, perk) end
        body.l0 = l0
        mark("l0")
    end
    if not finite(body.lm0dis) then body.lm0dis = body.lm; mark("lm0dis") end
    if not finite(body.tPeakD) then body.tPeakD = body.dayIndex; mark("tPeakD") end
    for i = 1, K.strength.MEM_HOLD_DAYS do
        if not finite(body.nHist[i]) then body.nHist[i] = 0; mark("nHist") end
    end
    for i = 1, 7 do
        local slot = body.bandWeek[i]
        if not finite(slot[1]) then slot[1] = 0; mark("bandWeek") end
        if not finite(slot[2]) then slot[2] = 0; mark("bandWeek") end
    end
    for i = 1, 7 do
        if not finite(body.mass7[i]) then body.mass7[i] = body.fm + body.lm; mark("mass7") end
    end
    for r = 1, #MET.ZERO_RINGS do
        local key = MET.ZERO_RINGS[r]
        local ring = body[key]
        for i = 1, 7 do
            if not finite(ring[i]) then ring[i] = 0; mark(key) end
        end
    end
    if bad ~= nil then
        MET.stats.failures = MET.stats.failures + 1
        MET.lastError = "metabolism: non-finite " .. bad .. " for " .. tostring(username) .. "; stamped neutral"
        NR.log.say(2, MET.lastError)
    end
end

local function step(username, player, record)
    local ageH = worldAge()
    if ageH == nil then
        MET.stats.badReads = MET.stats.badReads + 1   -- skipped: no stamp of a 0 age
        return
    end
    local body = MET.ensureBody(username, player, record, ageH)
    heal(username, body, ageH, player)
    local dtM = K.clamp((ageH - body.lastAgeH) * 60, 0, 60)  -- offline time is not integrated
    local w = body.fm + body.lm
    -- read, never cleared here: NR_Server_Nutrients (after this file) consumes and clears the handoff
    -- (Plan 4 ruling 17), and Kinetics rewrites it every minute, so this read sees each vector once
    local handoff = NR.server.kinetics and NR.server.kinetics.lastAbsorbed
    if handoff ~= nil and handoff[username] ~= nil then
        K.energy.intake(body, handoff[username], dtM)
    end
    local className, moving, modifier, loadKg, heavyLevel, coldMult, exercising, swiping, immobilised,
        hourOfDay, maxW, heatLevel, climbClass = MET.readActivity(player, ageH)
    local met = K.energy.activityMet(className, moving, modifier, loadKg)
    K.energy.minute(body, met, not moving, coldMult, dtM)
    K.training.sample(body, K.energy.CLASS_MET[className], heavyLevel, w, exercising, swiping, dtM)
    if climbClass ~= nil and dtM > 0 then K.training.climbCredit(body, climbClass, w) end
    if maxW > 0 then K.training.loadMinute(body, loadKg, maxW, dtM) end
    K.training.actionMinute(body, modifier, moving, dtM)
    K.training.decay(body, dtM)
    local dStr, _, maintained = K.training.doses(body)
    K.strength.neuralStep(body, dStr, maintained, immobilised, dtM / 1440)
    local today = math.floor(ageH / 24)
    local closes = 0
    while today > body.dayIndex and closes < MET.MAX_CLOSES do
        closeDay(body, w, immobilised, ageH)
        closes = closes + 1
    end
    if today > body.dayIndex then
        MET.stats.skippedDays = MET.stats.skippedDays + (today - body.dayIndex)
        body.dayIndex = today
    end
    w = body.fm + body.lm
    local fatDep = 0
    if body.fmRef > 0 then fatDep = K.clamp((body.fmRef - body.fm) / body.fmRef, 0, 1) end
    body.dmod = K.aerobic.dmod(body.tac, 1, 0, heatLevel, K.aerobic.excessPct(body.fm, K.aerobic.FM_NORMAL_80[body.sex], w), 1, 0, 0, 0)
    body.rmod = K.aerobic.rmod(body.tac, 1, K.aerobic.gProt(body.pPrevKg), 1, 0, 0, 0, 1)
    body.energyState = K.energy.state(K.energy.eb24h(body, ageH - body.lastCloseAgeH), fatDep)
    body.lastAgeH = ageH
    heal(username, body, ageH, player)
end

-- One player's minute: the (username, player, record) callback NR_Server_Players fires from P.work.
-- One pcall around the body: a failure is kept and logged on the slow clock, never raised into the
-- players walk.
function MET.minute(username, player, record)
    if record == nil then return end
    MET.stats.minutes = MET.stats.minutes + 1
    local ok, err = pcall(step, username, player, record)
    if not ok then
        MET.stats.failures = MET.stats.failures + 1
        MET.lastError = err
        NR.log.say(2, "metabolism: " .. tostring(username) .. " failed: " .. tostring(err))
    end
end

-- First sight (the players' onFirstSight hook): the body is made before the first mirror goes out, so
-- that mirror carries the body_* keys (run x141b-20261005-122603: sent before the body existed, the
-- client read them 0 until a re-request). This is the one first-sight mirror: NR_Server_Players sends
-- none of its own, and its OnNewGame reset fires this hook too, so the post-respawn mirror carries the
-- new body. An unreadable world age defers the body to the next readable minute (counted in badReads)
-- and the mirror goes out without it.
function MET.onFirstSight(username, player, record)
    if record == nil then return end
    local ageH = worldAge()
    if ageH == nil then
        MET.stats.badReads = MET.stats.badReads + 1
    else
        MET.ensureBody(username, player, record, ageH)
    end
    if NR.server.bus ~= nil and NR.server.bus.sendMirror(player, record) then
        MET.stats.firstSightMirrors = MET.stats.firstSightMirrors + 1
    end
end

-- The design precondition (spec ruling 5, ruling T18-1): vanilla's nutrition update off. With
-- SandboxVars.Nutrition anything but false, vanilla's updateWeight rewrites the weight flags every tick
-- and its drain empties the mirror stores (run x141b-20261005-122603). Read once at boot; warned at log
-- level 1 and flagged on NR.server.options.nutritionOn for the self-report. The option is the
-- operator's: the mod never changes it. Returns whether the precondition is broken.
function MET.checkPrecondition()
    local sv = SandboxVars
    local v = nil
    if sv ~= nil then v = sv.Nutrition end
    if v == false then return false end
    MET.stats.preconditionWarnings = MET.stats.preconditionWarnings + 1
    NR.log.say(1, "NutritionRevamp expects SandboxVars.Nutrition = false: vanilla's nutrition update is ON and will fight the weight flags and drain the mirror stores")
    if NR.server.options ~= nil then NR.server.options.nutritionOn = true end
    return true
end

-- Wiring: appended to the players' onMinute list at OnServerStarted. This file sorts after
-- NR_Server_Kinetics.lua, whose handler registers first, so the stomach step runs before this one. It
-- sorts before NR_Server_Options.lua, so the precondition flag is set before the boot self-report.
if Events ~= nil and Events.OnServerStarted ~= nil then
    Events.OnServerStarted.Add(function()
        if not NR.isServer() then return end
        if MET.wired then return end
        MET.wired = true
        MET.checkPrecondition()
        local P = NR.server.players
        P.onMinute[#P.onMinute + 1] = MET.minute
        if P.onFirstSight ~= nil then P.onFirstSight[#P.onFirstSight + 1] = MET.onFirstSight end
    end)
end
