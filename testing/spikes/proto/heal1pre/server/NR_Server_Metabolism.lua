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
        "the nutrient scalars (glycogen, dehydration, iron, caffeine, sleep debt, alcohol, the balance dial) read the previous minute's record sub-tables (a one-minute lag; NR_Server_Nutrients sorts after this file)",
        "the drain coefficient is stamped and unapplied until Plan 5",
        "a climb is credited when the minute sample lands inside the climb state; short climbs are missed",
        "the MET-minute bank is mirrored for the panel and feeds no coefficient; the aerobic dose is the band minutes",
        "the engine's inventory weight is read as kilograms",
        "an exhausted idle character's metabolic rate sits at the tired floor (up to the DefaultExercise class), so exhaustion bills as activity until Plan 5 owns endurance",
        "rmod scales the asleep regeneration arm only; under the harness's partial sleep hold it measured 0.904 for a predicted 0.848 (#2899)",
        "a day closes at 07:00 on the default fixture (#2890); the 24 h blends count hours since the last close",
        "an unreadable world age skips the minute; a first sight with an unreadable age sends its mirror without the body, which the next readable minute builds",
        "rmod's alcohol arm reads body.alcDay, the day-so-far ethanol the partition close zeroes: the arm resets at the day close, not on a rolling 24 h",
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

local finite = NR.finite

-- The world age, or nil when it cannot be read (the minute is then skipped and counted, never stamped 0).
local worldAge = NR.worldAge

-- A number read off obj:name(...), or dflt when the member is absent or the answer is not finite.
local num = NR.num

-- A boolean read off obj:name(...): true only when the member is present and answers true.
local flag = NR.flag

-- An object read off obj:name(...), or nil.
local obj = NR.obj

-- The nutrient scalars dmod, rmod and TAC read, off the record's Plan 4 sub-tables (NR_Server_Nutrients
-- writes record.nutrients, record.fluids and record.acute). Its step runs after this one, so these are
-- the PREVIOUS minute's stamps: a one-minute lag. A sub-table that is absent (a record made before Plan 4,
-- or the first minute before NR_Server_Nutrients has run) or a field that is absent, non-finite or out of
-- range reads the neutral the Plan 3 stubs passed: iron grade 1, not all replete, dehydration 0, glycogen
-- 1, hours awake 0, sleep debt 0, caffeine effect 0, tolerance 0. Read: nutrients.ironGrade (1-4),
-- nutrients.allReplete (true), fluids.dehydPct, acute.g, acute.awakeH, acute.debtH, acute.caf (through
-- K.acute.cafEffect) and acute.cafTol. w is the minute's starting mass, kg.
local function nutrientInputs(record, w)
    local nut, fl, ac = record.nutrients, record.fluids, record.acute
    local ironGrade, allReplete = 1, false
    if type(nut) == "table" then
        local grade = nut.ironGrade
        if grade == 1 or grade == 2 or grade == 3 or grade == 4 then ironGrade = grade end
        allReplete = nut.allReplete == true
    end
    local dehydPct = 0
    if type(fl) == "table" and finite(fl.dehydPct) then dehydPct = K.max(0, fl.dehydPct) end
    local g, awakeH, debtH, cafEffect, cafTol = 1, 0, 0, 0, 0
    if type(ac) == "table" then
        if finite(ac.g) then g = K.clamp(ac.g, 0, 1) end
        if finite(ac.awakeH) then awakeH = K.max(0, ac.awakeH) end
        if finite(ac.debtH) then debtH = K.max(0, ac.debtH) end
        if finite(ac.caf) and w > 0 then cafEffect = K.acute.cafEffect(ac, w) end
        if finite(ac.cafTol) then cafTol = K.clamp(ac.cafTol, 0, 1) end
    end
    return ironGrade, allReplete, dehydPct, g, awakeH, debtH, cafEffect, cafTol
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
    -- a body made beside kept nutrients (a load that dropped an unusable stored body, Plan 8 T3 fix concern 2)
    -- closes its first day on the resting expenditure, as K.store.load stamps a loaded body, not on a 0 kcal day
    if record.nutrients ~= nil then record.body.inDayClosed = K.energy.ree(record.body.lm) end
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
-- ironGrade and debtH are the record's iron grade and sleep debt (nutrientInputs): TAC's iron and sleep
-- gates.
local function closeDay(body, w, immobilised, ageH, ironGrade, debtH)
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
    K.aerobic.tacDay(body, m1, hard, K.aerobic.G_IRON[ironGrade], K.aerobic.gProt(pPerKg), K.aerobic.gEnergy(body.inDay, body.exKcalDay, body.lm), K.aerobic.gSleep(debtH), 1, immobilised)
    body.pPrevKg = pPerKg
    body.inDayClosed = body.inDay                        -- the closing day's absorbed kcal, for NR_Server_Nutrients' refeeding close
    K.partition.closeDay(body, ageH)
    body.at = K.energy.atStep(body.at, K.energy.atTarget(body.fm, body.fmRef), K.partition.deficitWeek(body), 1)
    MET.stats.days = MET.stats.days + 1
end

-- The self-heal (the #2833 pattern), run before the minute's arithmetic and again after its stamps: the pure
-- part is the kernel's (NR_Kernel_Heal.lua, K.heal.body, Plan 10 Task R3), which stamps every non-finite scalar
-- or ring slot its neutral, backfills the fields and rings an older record lacks, and returns the healed names.
-- The adapter keeps its one engine read -- the Strength level, read only when body.l0 is not finite, and passed
-- in -- and the count and the log: a pass that healed anything counts one failure and names every field. This
-- file owns the rings: the Weight mirror and the partition ring read them and rebuild nothing. The neutrals,
-- their order and the zero-healed rings are the kernel's tables (K.heal.NEUTRAL, K.heal.NEUTRAL_KEYS,
-- K.heal.ZERO_RINGS), read at call time: nothing here names the kernel at file scope, so the file loads in a
-- runtime that holds NR_Core alone (the wiring tests).


local function heal(username, body, ageH, player)
    local l0 = nil
    if not finite(body.l0) then
        l0 = 0
        local perk = Perks ~= nil and Perks.Strength or nil
        if perk ~= nil then l0 = num(player, "getPerkLevel", 0, perk) end
    end
    local bad = K.heal.body(body, ageH, l0)
    if bad ~= nil then
        MET.stats.failures = MET.stats.failures + 1
        MET.lastError = "metabolism: non-finite " .. bad .. " for " .. tostring(username) .. "; stamped neutral"
        NR.log.say(2, MET.lastError)
    end
end

local function step(username, player, record, pipe)
    local ageH = worldAge()
    if ageH == nil then
        MET.stats.badReads = MET.stats.badReads + 1   -- skipped: no stamp of a 0 age
        return
    end
    local body = MET.ensureBody(username, player, record, ageH)
    heal(username, body, ageH, player)
    local dtM = K.clamp((ageH - body.lastAgeH) * 60, 0, 60)  -- offline time is not integrated
    local w = body.fm + body.lm
    -- read, never cleared here: NR_Server_Nutrients (the next step) consumes the handoff (Plan 4 ruling 17),
    -- and the pipeline's context lives one player's minute, so this read sees each vector once
    local handoff = pipe and pipe.absorbed
    if handoff ~= nil then
        K.energy.intake(body, handoff, dtM)
    end
    local className, moving, modifier, loadKg, heavyLevel, coldMult, exercising, swiping, immobilised,
        hourOfDay, maxW, heatLevel, climbClass = MET.readActivity(player, ageH)
    local met = K.energy.activityMet(className, moving, modifier, loadKg)
    -- the activity stamps NR_Server_Nutrients reads for sweat, cold diuresis and the glycogen draw: always
    -- finite (1 when the read is not)
    if finite(met) then body.met = met else body.met = 1 end
    if finite(coldMult) then body.coldMult = coldMult else body.coldMult = 1 end
    K.energy.minute(body, met, not moving, coldMult, dtM)
    K.training.sample(body, K.energy.CLASS_MET[className], heavyLevel, w, exercising, swiping, dtM)
    if climbClass ~= nil and dtM > 0 then K.training.climbCredit(body, climbClass, w) end
    if maxW > 0 then K.training.loadMinute(body, loadKg, maxW, dtM) end
    K.training.actionMinute(body, modifier, moving, dtM)
    K.training.decay(body, dtM)
    local dStr, _, maintained = K.training.doses(body)
    K.strength.neuralStep(body, dStr, maintained, immobilised, dtM / 1440)
    local ironGrade, allReplete, dehydPct, g, awakeH, debtH, cafEffect, cafTol = nutrientInputs(record, w)
    local today = math.floor(ageH / 24)
    local closes = 0
    while today > body.dayIndex and closes < MET.MAX_CLOSES do
        closeDay(body, w, immobilised, ageH, ironGrade, debtH)
        closes = closes + 1
    end
    if today > body.dayIndex then
        MET.stats.skippedDays = MET.stats.skippedDays + (today - body.dayIndex)
        body.dayIndex = today
    end
    w = body.fm + body.lm
    local fatDep = 0
    if body.fmRef > 0 then fatDep = K.clamp((body.fmRef - body.fm) / body.fmRef, 0, 1) end
    -- the balance dial (NR.BalanceBonus, default on: an absent options table reads on) while every pool
    -- record is replete; body.alcDay is the day-so-far ethanol, zeroed by the partition close
    local opts = NR.server.options
    local balanceBonus = 1
    if allReplete and (opts == nil or opts.balanceBonus ~= false) then
        balanceBonus = 1.05                                -- game choice, spec s4.5
    end
    local alcGkg = body.alcDay / w
    body.dmod = K.aerobic.dmod(body.tac, g, dehydPct, heatLevel, K.aerobic.excessPct(body.fm, K.aerobic.FM_NORMAL_80[body.sex], w), ironGrade, awakeH, cafEffect, cafTol)
    body.rmod = K.aerobic.rmod(body.tac, g, K.aerobic.gProt(body.pPrevKg), ironGrade, dehydPct, debtH, alcGkg, balanceBonus)
    body.energyState = K.energy.state(K.energy.eb24h(body, ageH - body.lastCloseAgeH), fatDep, g)
    body.lastAgeH = ageH
    -- PROTO heal1pre (Plan 10c H1): the post-step heal removed; the one heal is the pre-step pass above
end

-- One player's minute: the pipeline's metabolism step (NR_Server_Minute.run, from P.work); pipe its context.
-- One pcall around the body: a failure is kept and logged on the slow clock, never raised into the
-- players walk.
function MET.minute(username, player, record, pipe)
    if record == nil then return end
    MET.stats.minutes = MET.stats.minutes + 1
    local ok, err = pcall(step, username, player, record, pipe)
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

-- Wiring: registered as the pipeline's metabolism step at OnServerStarted; ORDER runs the stomach
-- (kinetics) step before this one. This file sorts before NR_Server_Options.lua, so its handler sets
-- the precondition flag before the boot self-report.
if Events ~= nil and Events.OnServerStarted ~= nil then
    Events.OnServerStarted.Add(function()
        if not NR.isServer() then return end
        if MET.wired then return end
        MET.wired = true
        MET.checkPrecondition()
        local P = NR.server.players
        NR.server.minute.register("metabolism", MET.minute)
        if P.onFirstSight ~= nil then P.onFirstSight[#P.onFirstSight + 1] = MET.onFirstSight end
    end)
end
