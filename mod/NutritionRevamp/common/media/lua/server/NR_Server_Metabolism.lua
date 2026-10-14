-- NR_Server_Metabolism.lua -- the body model's slow-clock adapter (spec § 4.3): once per player
-- per game minute, on the players' OnTick stagger and after the stomach step, it creates record.body at
-- first sight, bills the minute's expenditure off the server's metabolic rate, banks the absorbed intake
-- Kinetics handed off, samples the aerobic training signal, closes the record day at an online world-day boundary
-- (the lean-mass body's day, the body traits, adaptive thermogenesis, TAC, the rings), and stamps the
-- drain and regeneration coefficients and the energy state the writer reads. Since Plan 11c Task 6 (spec § 5c,
-- rulings 11c-29 and 11c-32 amended) the energy state is K.deficit.activityState: the exercise share of the deficit
-- enters through the lag L (record.satiety.L, stepped here on the minute's exercise kcal), bypassed on a ramp when the
-- trailing-24 h total deficit is large against the trailing-24 h expenditure.
--
-- The activity read (run x141a-20261005-111005): the server's thermoregulator TARGET reads
-- -1 at every tick, so it is never read; the RATE classifies but lags activity (a first-order lag) and
-- already carries the engine's load factor, which is divided out before the bucketing; the bill then reads the
-- exercise flag and the rate's fall beside it (MET.readBilled, K.energy.billClass). isAsleep wins. A missing or non-finite rate reads the Default class and counts a bad
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
    stats = { minutes = 0, days = 0, failures = 0, creates = 0, badReads = 0,
              firstSightMirrors = 0, preconditionWarnings = 0, exeFallbacks = 0 },
    lastError = nil,
    wired = false,
    limitations = {
        "the run and sprint flags never reach the server (x141a), so a runner bills as a walker and the Running classes are unreachable; the metabolic rate lags activity (a first-order lag fixed in real seconds, so its game-time length scales with the day length), and only a Fitness exercise bills its class from the first minute, from the server's exercise flag; the current timed action is unreadable server-side, so the calorie-modifier bands are unused and timed actions bill at the class rate",
        "an 8.0 rate classifies as ClimbRope, never ForestryAxe (chopping bills 8.0 not 6.5); a 6.0 as HeavyWork, and Fitness only from the exercise flag",
        "offline time is not integrated and the record calendar does not advance offline: a return after a step over 60 game minutes closes no day and continues the day open at departure as today's record day, so record days count online days only; a server stall over 60 game minutes with the player online reads as a gap and folds those world days into one record day",
        "the disuse arm needs a leg fracture or splint",
        "the nutrient scalars (glycogen, dehydration, iron, caffeine, sleep debt, alcohol, the balance dial) read the previous minute's record sub-tables (a one-minute lag; the pipeline's ORDER runs the nutrients step after this one)",
        "the drain coefficient is stamped and mirrored and drives no stat write",
        "a climb is credited when the minute sample lands inside the climb state; short climbs are missed",
        "the MET-minute bank is mirrored for the panel and feeds no coefficient; the aerobic dose is the band minutes",
        "the engine's inventory weight is read as kilograms",
        "an exhausted idle character's metabolic rate sits at the tired floor (up to the DefaultExercise class), so exhaustion bills as activity",
        "rmod scales the asleep regeneration arm only; under the harness's partial sleep hold it measured 0.904 for a predicted 0.848 (#2899)",
        "a day closes at 07:00 on the default fixture (#2890); the 24 h blends count hours since the last close",
        "an unreadable world age skips the minute; a first sight with an unreadable age sends its mirror without the body, which the next readable minute builds",
        "rmod's alcohol arm reads body.alcDay, the day-so-far ethanol the partition close zeroes: the arm resets at the day close, not on a rolling 24 h",
        "a field the step's own arithmetic leaves non-finite and no later step reads in the same minute stays so until the next minute's pre-step heal",
        "every Fitness exercise bills its type's Compendium MET (K.energy.EXERCISE_MET, the general or moderate code, a game choice) while the server's exercise flag is set, from the type NR_Server_Fitness recorded at the set's start; a set with no recorded or no known type bills the flat Fitness class (6.0), counted in stats.exeFallbacks; walking, chopping and fighting keep the metabolic rate's rise lag",
        "a minute whose raw metabolic rate is falling with no exercise and no movement bills the idle class, so a step down to a lighter activity while standing bills idle until the rate settles; the previous rate is held in memory, so the first minute after a boot reads no fall; the fall is read on the raw rate, so a still player at a sustained class above idle who drops weight (an eat, a sip) may bill one idle minute; body.met, which sweat and fluids (NR_Server_Nutrients), the glycogen draw and Effects' exertion heat (NR_Server_Effects) also read, so reads the set's billed MET on every set minute and 1.3 on every standing fall",
        "the after-burn follows the exercise flag's minutes only, at a fixed share of their exercise kcal released on a fixed game-time constant, whatever the intensity or the day length",
        "a fresh record's 24 h window holds no meals: it reads like an even eater, its energy state rising from first sight at its expenditure rate (a new character or a respawn reaches energy level 1 after several unfed hours, inside the model's range for a skipped meal)",
        "a fresh record laid over a character the mod has already changed (a return after NR.RecordKeepDays prunes the record, a corrupt file healed fresh, or a deferral that gives up) is built from the band traits the character holds, never its native level, so it restarts at its muscle band's start level and may lose up to two native levels, and a Night Vision or Short Sighted trait the lost record owned stays, since the effects own only the traits they added; a fix needs a durable marker on the character",
        "an immobilised day runs the disuse arm in place of growth, regain and detraining: the grace counter and the neural factor still step, the remembered peak does not decay that day",
    },
}
local MET = NR.server.metabolism

-- The leg parts whose fracture or splint immobilises.
MET.LEG_PARTS = { "UpperLeg_L", "UpperLeg_R", "LowerLeg_L", "LowerLeg_R" }
-- The band traits read at first sight (ruling 13-6), as CharacterTrait registry fields: the muscle band and the
-- weight band; Emaciated reads as Very Underweight (K.body.WEIGHT_ALIAS). The first held in each list is the pick.
MET.MUSCLE_TRAITS = { "STRONG", "STOUT", "FEEBLE", "WEAK" }
MET.WEIGHT_TRAITS = { "OBESE", "OVERWEIGHT", "UNDERWEIGHT", "VERY_UNDERWEIGHT", "EMACIATED" }

-- The post-step guard: the body fields something reads before the next minute's
-- pre-step heal -- the later steps of the minute (the writer among them), the bus step (first in ORDER) and
-- the store step -- are copied after the pre-step heal and re-stamped from the copy when the step leaves them
-- non-finite (testing/tests/kernel/test_heal_once.py CROSS names each read). A ring takes this minute's values only
-- in slot 7 (a close shifts slots 1-6), so slot 7 of each read ring and of bandWeek is guarded. The trailing-24 h
-- window takes values this minute only in its age and its current hour's slot, so those are guarded.
MET.GUARD = { "fm", "lm", "energyState", "rmod", "met", "coldMult", "eeDay", "inDay", "alcDay", "pPrevKg",
              "inDayClosed", "dayIndex", "band1Day", "band2Day", "exKcalDay", "carbDay", "pDay",
              "lipDay", "ebDay", "tDisuse", "tac", "lastAgeH", "epoc", "lx", "Pk", "T" }
MET.GUARD_RINGS = { "eb7", "p7", "mass7" }
MET.GUARD_TRAIL = { "at" }
MET.TRAIL_SLOT = { 1 }
MET.snapTrail = {}
MET.snapTrailRings = {}
-- The exercise lag on record.satiety, stepped here, healed by the writer and saved by the store.
MET.GUARD_SATIETY = { "L" }
MET.snapSatiety = {}
MET.SLOT7 = { 7 }
MET.BAND_SLOT = { 1, 2 }
MET.snap = {}
MET.snapRings = { eb7 = {}, p7 = {}, mass7 = {} }
MET.snapBand = {}
MET.guarded = 0

local finite = NR.finite

-- The world age, or nil when it cannot be read (the minute is then skipped and counted, never stamped 0).
local worldAge = NR.worldAge

-- A number read off obj:name(...), or dflt when the member is absent or the answer is not finite.
local num = NR.num

-- A boolean read off obj:name(...): true only when the member is present and answers true.
local flag = NR.flag

-- An object read off obj:name(...), or nil.
local obj = NR.obj

-- The nutrient scalars rmod and TAC read, off the record's Plan 4 sub-tables (NR_Server_Nutrients
-- writes record.nutrients, record.fluids and record.acute). Its step runs after this one, so these are
-- the PREVIOUS minute's stamps: a one-minute lag. A sub-table that is absent (a fresh character's first
-- minute, before NR_Server_Nutrients has run) or a field that is absent, non-finite or out of
-- range reads the neutral: iron grade 1, not all replete, dehydration 0, glycogen 1, sleep debt 0. Read:
-- nutrients.ironGrade (1-4), nutrients.allReplete (true), fluids.dehydPct, acute.g and acute.debtH.
local function nutrientInputs(record)
    local nut, fl, ac = record.nutrients, record.fluids, record.acute
    local ironGrade, allReplete = 1, false
    if type(nut) == "table" then
        local grade = nut.ironGrade
        if grade == 1 or grade == 2 or grade == 3 or grade == 4 then ironGrade = grade end
        allReplete = nut.allReplete == true
    end
    local dehydPct = 0
    if type(fl) == "table" and finite(fl.dehydPct) then dehydPct = K.max(0, fl.dehydPct) end
    local g, debtH = 1, 0
    if type(ac) == "table" then
        if finite(ac.g) then g = K.clamp(ac.g, 0, 1) end
        if finite(ac.debtH) then debtH = K.max(0, ac.debtH) end
    end
    return ironGrade, allReplete, dehydPct, g, debtH
end

-- The strength table the body steps with: the server's (NR_Server_Options builds it from the sandbox), else the
-- kernel's DEFAULTS when no options table is laid (a runtime without NR_Server_Options).
function MET.strengthP()
    local opts = NR.server.options
    if opts ~= nil and opts.strength ~= nil then return opts.strength end
    return K.strength.DEFAULTS
end

-- Whether NR.SexSpecific is on (an absent options table reads off).
local function sexSpecific()
    local opts = NR.server.options
    return opts ~= nil and opts.sexSpecific == true
end

-- The first trait of names the collection holds, or nil (none held, or the registry or the collection unreadable).
function MET.heldTrait(traits, names)
    if CharacterTrait == nil or traits == nil then return nil end
    for i = 1, #names do
        local t = CharacterTrait[names[i]]
        if t ~= nil and flag(traits, "get", t) then return names[i] end
    end
    return nil
end

-- First sight: record.body is the creation body (K.body.create) over the muscle and weight band traits the character
-- holds (ruling 13-6), never its native Strength level, weight or carry delta, at the engine's sex and the world age;
-- body.levelDue asks the Strength minute to write the level once (Plan 13 Task 14). An existing record.body is
-- never re-read.
function MET.ensureBody(username, player, record, ageH)
    if record.body ~= nil then return record.body end
    local sex = 1
    if flag(player, "isFemale") then sex = 2 end
    local traits = obj(player, "getCharacterTraits")
    local muscle = MET.heldTrait(traits, MET.MUSCLE_TRAITS)
    local weight = MET.heldTrait(traits, MET.WEIGHT_TRAITS)
    local spec = K.body.create(muscle, weight, MET.strengthP(), K.body.effSex(sex, sexSpecific()))
    local body = K.body.new(spec, sex, ageH)
    body.levelDue = true
    record.body = body
    MET.stats.creates = MET.stats.creates + 1
    NR.log.say(3, "metabolism: first sight of " .. tostring(username) .. " sex=" .. sex .. " muscle="
        .. tostring(muscle) .. " weight=" .. tostring(weight))
    return body
end

-- The minute's activity: className, moving, modifier, loadKg, heavyLevel, coldMult, exercising,
-- swiping, immobilised, hourOfDay, maxW, climbClass. ageH (optional) is the minute's world
-- age; ctx (optional) the pipeline's context, whose shared engine reads (NR.read) it takes and keeps. climbClass
-- is the K.training.CLIMB_MET class of the climb state the character is in at the sample (a fence vault JumpFence,
-- a window climb ClimbRope), or nil: a per-minute state sample, so a climb shorter than the gap between samples is
-- missed.
function MET.readActivity(player, ageH, ctx)
    local bd = NR.read.bodyDamage(ctx, player)
    local thermo = NR.read.thermo(ctx, player, bd)
    local loadKg = num(player, "getInventoryWeight", 0)
    local maxW = num(player, "getMaxWeight", 0)
    local className = "Default"
    local okR, rate = NR.call(thermo, "getMetabolicRate")
    if okR and finite(rate) then
        className = K.energy.classOf(K.energy.stripLoad(rate, loadKg, maxW))
    else
        MET.stats.badReads = MET.stats.badReads + 1
    end
    if NR.read.asleep(ctx, player) then className = "Sleeping" end
    local moving = flag(player, "isPlayerMoving")
    local moodles = obj(player, "getMoodles")
    local heavyLevel = 0
    if MoodleType ~= nil and MoodleType.HEAVY_LOAD ~= nil then
        heavyLevel = K.clamp(math.floor(num(moodles, "getMoodleLevel", 0, MoodleType.HEAVY_LOAD)), 0, 4)
    end
    local coldMult = num(thermo, "getEnergyMultiplier", 1)
    local exercising = obj(obj(player, "getFitness"), "getCurrentExe") ~= nil
    local swiping = false
    if SwipeStatePlayer ~= nil and SwipeStatePlayer.instance ~= nil then
        local okI, inst = pcall(SwipeStatePlayer.instance)  -- under the guard the writer's hoist and the climbs use
        if okI and inst ~= nil then swiping = flag(player, "isCurrentState", inst) end
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
    local hourOfDay = NR.read.hour(ctx, ageH or NR.read.ageH(ctx))
    return className, moving, 1, loadKg, heavyLevel, coldMult, exercising, swiping, immobilised, hourOfDay,
        maxW, climbClass, okR and finite(rate) and rate or nil
end

-- One day close (Plan 13 Task 12): the disuse day count (before the masses move, so the first immobilised day runs
-- with t = 1 off the lean mass it began on); the signal ring's close, whose sum over xpPerSet is the closed week's
-- sets S; the body's day -- K.strength.day (growth, regain, detraining, the partition, the floors, the peak and the
-- neural factor) or, immobilised, the disuse arm under the floors with lx untouched, detraining's grace counter
-- (its kg discarded) and the neural factor (ruling 13-13); fmRef re-based upward (adaptive thermogenesis reads
-- depletion from the highest fat reached); the trait axes and band word; then the training ring, TAC, the
-- partition ring (pushes today's balance into eb7, zeroes the day accumulators, advances dayIndex) and adaptive
-- thermogenesis. Each reader runs after the writer of what it reads (the x141c one-close lag): the training ring
-- shifts the closing day in BEFORE TAC reads the week (run x141c-20261005-132133); TAC's energy gate reads the
-- closing day's inDay and exKcalDay and its immobilised flag before the partition ring zeroes them;
-- the AT step reads deficitWeek AFTER the partition ring, so the week it reads includes today.
-- w is the body mass fm + lm + lx; ironGrade and debtH are the record's iron grade and sleep debt
-- (nutrientInputs): TAC's iron and sleep gates.

-- Option C, Angus 2026-10-11: exercise billed by the activity.
-- readBilled reads the activity as readActivity does and swaps the rate's class for the class the minute
-- bills (K.energy.billClass): the Fitness class while the exercise flag is set, the idle class while the raw engine
-- rate falls with no exercise and no movement, else the rate's own. The rate's class rides along, for the
-- training sample, which banks the ENGINE's own value of the rate's class (two MET tables, never mixed). The previous
-- minute's RAW rate and exercise flag are held here per user, in memory only: the first minute after a boot reads
-- no fall. The fall is decided raw against raw (F-T6r-3): the engine's rate lags toward base x
-- load factor, so an eat or a sip drops the inventory load at once while the raw rate still carries the old load, and
-- dividing it by the new, smaller factor lifts the stripped rate and hides the fall. The class still comes from the
-- stripped rate. The minute the flag clears counts as falling too: the engine's target drops with the flag, but a drain a
-- tick after the clear can still read the rate's last rise.
MET.prevRate = {}
MET.prevExe = {}

function MET.readBilled(username, player, ageH, ctx)
    local className, moving, modifier, loadKg, heavyLevel, coldMult, exercising, swiping, immobilised,
        hourOfDay, maxW, climbClass, rate = MET.readActivity(player, ageH, ctx)
    local falling = K.energy.rateFalling(MET.prevRate[username], rate)
    if MET.prevExe[username] == true and not exercising then falling = true end
    MET.prevRate[username] = rate
    MET.prevExe[username] = exercising
    local billClass = K.energy.billClass(className, exercising, moving, falling)
    local exMet = nil
    local known = true
    if billClass == "Fitness" and exercising then
        exMet, known = K.energy.exerciseMet(MET.exeTypeOf(username, exercising))
    end
    if not known then MET.stats.exeFallbacks = MET.stats.exeFallbacks + 1 end
    return billClass, moving, modifier, loadKg, heavyLevel, coldMult, exercising, swiping, immobilised,
        hourOfDay, maxW, climbClass, className, exMet
end

-- C-2: the exercise type NR_Server_Fitness.lua recorded at the set's start; a Lua table lookup, no Java
-- (Rule 6). The flag test is a guard: readBilled calls it only on a set minute, and a clear flag never reads a stale
-- type. nil when the module is absent or nothing is recorded: the minute then bills the flat Fitness class (exeFallbacks).
function MET.exeTypeOf(username, exercising)
    if not exercising then return nil end
    local F = NR.server.fitness
    if F == nil or F.typeOf == nil then return nil end
    return F.typeOf(username)
end

-- The minute's expenditure (K.energy.minute) and the after-burn pool (K.energy.epoc), fed by the minute's exercise
-- kcal while the flag is set. The pool's release is expenditure, never exercise kcal: the lag L the caller steps on
-- exKcalDay's rise does not see it. A pool the kernel healed counts in MET.guarded.
function MET.spend(username, body, met, resting, coldMult, dtM, exercising)
    local ex0 = body.exKcalDay
    K.energy.minute(body, met, resting, coldMult, dtM)
    local _, healed = K.energy.epoc(body, exercising, body.exKcalDay - ex0, dtM)
    if healed then
        MET.guarded = MET.guarded + 1
        NR.log.say(2, "metabolism: non-finite or negative body.epoc for " .. tostring(username) .. "; stamped 0")
    end
end

-- Plan 11f C-17 fix 1: the held rate and flag are per user and leave with the player.
function MET.forget(username)
    MET.prevRate[username] = nil
    MET.prevExe[username] = nil
end

local function closeDay(body, w, immobilised, ageH, ironGrade, debtH)
    if immobilised then
        if body.tDisuse == 0 then body.lm0dis = body.lm end
        body.tDisuse = body.tDisuse + 1
    else
        body.tDisuse = 0
    end
    local P = MET.strengthP()
    local S = K.strength.signalClose(body) / P.xpPerSet
    local pPerKg = body.pDay / w
    local tdee = K.max(body.eeDay, K.energy.ree(body.lm))
    if immobilised then
        local s = K.strength.status(body)
        local dFM, dLM = K.partition.disuse(body)
        body.fm = K.max(body.fm + dFM, P.fmMin)
        body.lm = K.max(body.lm + dLM, P.fMinShare * body.F0)
        K.strength.detrain(body, S, s, P, P.ts)          -- the grace counter only: the disuse arm is the day's loss
        K.strength.neural(body, S, P, P.ts)
    else
        K.strength.day(body, S, pPerKg, body.ebDay, tdee, body.alcDay / w, P, P.ts)
    end
    body.fmRef = K.max(body.fmRef, body.fm)
    local band = K.traits.axes(body, K.body.effSex(body.sex, sexSpecific()))
    if band ~= body.band then
        body.band = band
        body.traitsDirty = true
    end
    body.S = S
    K.training.closeDay(body)
    local m1, hard = K.training.weekMinutes(body)
    K.aerobic.tacDay(body, m1, hard, K.aerobic.G_IRON[ironGrade], K.aerobic.gProt(pPerKg), K.aerobic.gEnergy(body.inDay, body.exKcalDay, body.lm), K.aerobic.gSleep(debtH), 1, immobilised)
    body.pPrevKg = pPerKg
    body.inDayClosed = body.inDay                        -- the closing day's absorbed kcal, for NR_Server_Nutrients' refeeding close
    K.partition.closeDay(body)
    body.at = K.energy.atStep(body.at, K.energy.atTarget(body.fm, body.fmRef), K.partition.deficitWeek(body), 1)
    MET.stats.days = MET.stats.days + 1
end
if NR_BENCH then MET._closeDay = closeDay end   -- the day-close bench seam (tools/bench_day_close.py, ruling 13-33)

-- The self-heal (the #2833 pattern), run once, before the minute's arithmetic: the pure
-- part is the kernel's (NR_Kernel_Heal.lua, K.heal.body, Plan 10 Task R3), which stamps every non-finite scalar
-- or ring slot its neutral and returns the healed names; it reads no engine value. The adapter passes the
-- effective-sex option, the strength table the no-trait body is built with and the record-day lower bound a
-- non-finite dayIndex heals to (MET.dayFloor), and keeps the count and the log: a pass that healed anything counts
-- one failure and names every field. This file owns the rings: the Weight mirror and the partition ring read them
-- and rebuild nothing. The neutrals, their order and the zero-healed rings are the kernel's tables (K.heal.NEUTRAL
-- and K.heal.ZERO_RINGS), read at call time: nothing here names the kernel at file scope, so the file loads in a
-- runtime that holds NR_Core alone (the wiring tests).

-- The record-day lower bound a non-finite dayIndex heals to: the Nutrients step's last seen day count
-- (record.nutrients.lastDayIndex, at most one close behind), else the Effects step's (record.effects.lastDay), else
-- nil (the kernel then reads the world day).
function MET.dayFloor(record)
    local n, e = record.nutrients, record.effects
    if type(n) == "table" and finite(n.lastDayIndex) then return n.lastDayIndex end
    if type(e) == "table" and finite(e.lastDay) then return e.lastDay end
    return nil
end

local function heal(username, record, body, ageH)
    local floor = nil
    if not finite(body.dayIndex) then floor = MET.dayFloor(record) end   -- read only when the heal needs it
    local bad = K.heal.body(body, ageH, sexSpecific(), MET.strengthP(), floor)
    if bad ~= nil then
        MET.stats.failures = MET.stats.failures + 1
        MET.lastError = "metabolism: non-finite " .. bad .. " for " .. tostring(username) .. "; stamped neutral"
        NR.log.say(2, MET.lastError)
    end
end

-- The exercise lag, healed before the minute: a lag that is non-finite or negative
-- (the Task 4b re-review's residual: exerciseLag passes a negative L through) is stamped 0, logged and counted in
-- MET.guarded. record.satiety is laid for its L when absent; its M is the writer's to seed (the intake feeds it, Kinetics clears it). (The closed day's
-- exercise bank it healed beside the lag went with the 24 h blend.) Returns the satiety table.
function MET.healActivity(username, record, body)
    local healed = nil
    local s = record.satiety
    if type(s) ~= "table" then
        s = {}
        record.satiety = s
    end
    if s.L == nil then s.L = 0 end
    if not finite(s.L) or s.L < 0 then
        s.L = 0
        healed = K.heal.mark(healed, "satiety.L")
    end
    if healed ~= nil then
        MET.guarded = MET.guarded + 1
        NR.log.say(2, "metabolism: non-finite or negative " .. healed .. " for " .. tostring(username) .. "; stamped 0")
    end
    return s
end

-- The trailing-24 h expenditure (kcal), as NR_Server_Nutrients reads its ee24 for the expenditure-scaled
-- requirements: the window's expenditure (K.body.trail24), floored at the resting expenditure (a
-- window younger than a day, a fresh character's, reads at least a resting day).
function MET.ee24(body)
    return K.max(K.body.trail24(body.trail, "ee"), K.energy.ree(body.lm))
end

-- The guard's copy, taken after the pre-step heal and the window's move: the scalars, slot 7 of each ring, bandWeek's
-- slot 7, the lag, the window's age and its current hour's slot in each ring.
local function snapAll(body, sat)
    K.heal.snap(body, MET.GUARD, MET.snap)
    K.heal.snap(sat, MET.GUARD_SATIETY, MET.snapSatiety)
    local rings = MET.GUARD_RINGS
    for i = 1, #rings do
        K.heal.snap(body[rings[i]], MET.SLOT7, MET.snapRings[rings[i]])
    end
    K.heal.snap(body.bandWeek[K.body.WEEK_N], MET.BAND_SLOT, MET.snapBand)
    local t = body.trail
    MET.TRAIL_SLOT[1] = K.body.trailSlot(math.floor(t.at))
    K.heal.snap(t, MET.GUARD_TRAIL, MET.snapTrail)
    local keys = K.body.TRAIL_KEYS
    for i = 1, #keys do
        local out = MET.snapTrailRings[keys[i]]
        if out == nil then
            out = {}
            MET.snapTrailRings[keys[i]] = out
        end
        K.heal.snap(t[keys[i]], MET.TRAIL_SLOT, out)
    end
end

-- The guard after the step: every guarded field the step left non-finite re-stamped from the copy; the count.
local function guardAll(body, sat)
    local g = K.heal.guard(body, MET.GUARD, MET.snap) + K.heal.guard(sat, MET.GUARD_SATIETY, MET.snapSatiety)
    local rings = MET.GUARD_RINGS
    for i = 1, #rings do
        g = g + K.heal.guard(body[rings[i]], MET.SLOT7, MET.snapRings[rings[i]])
    end
    local t = body.trail
    g = g + K.heal.guard(t, MET.GUARD_TRAIL, MET.snapTrail)
    local keys = K.body.TRAIL_KEYS
    for i = 1, #keys do
        g = g + K.heal.guard(t[keys[i]], MET.TRAIL_SLOT, MET.snapTrailRings[keys[i]])
    end
    return g + K.heal.guard(body.bandWeek[K.body.WEEK_N], MET.BAND_SLOT, MET.snapBand)
end

local function step(username, player, record, ctx)
    local ageH = NR.read.ageH(ctx)
    if ageH == nil then
        MET.stats.badReads = MET.stats.badReads + 1   -- skipped: no stamp of a 0 age
        return
    end
    local body = MET.ensureBody(username, player, record, ageH)
    heal(username, record, body, ageH)
    local sat = MET.healActivity(username, record, body)
    local stepM = (ageH - body.lastAgeH) * 60
    local dtM = K.clamp(stepM, 0, 60)                     -- offline time is not integrated
    if stepM > 60 then K.body.trailShift(body.trail, ageH - dtM / 60) end   -- nor kept in the window: it skips the gap
    K.body.trailTo(body.trail, ageH)                      -- the window to this minute, before its intake and expenditure land
    snapAll(body, sat)
    local w = body.fm + body.lm + body.lx                 -- the body mass (ruling 13-20)
    -- read, never cleared here: NR_Server_Nutrients (the next step) consumes the handoff,
    -- and the pipeline's context lives one player's minute, so this read sees each vector once
    local handoff = ctx and ctx.absorbed
    if handoff ~= nil then
        K.energy.intake(body, handoff, dtM)
    end
    local className, moving, modifier, loadKg, heavyLevel, coldMult, exercising, swiping, immobilised,
        hourOfDay, maxW, climbClass, rateClass, exMet = MET.readBilled(username, player, ageH, ctx)
    local met = K.energy.activityMet(className, moving, modifier, loadKg, exMet)
    -- the activity stamps NR_Server_Nutrients reads for sweat, cold diuresis and the glycogen draw: always
    -- finite (1 when the read is not)
    if finite(met) then body.met = met else body.met = 1 end
    if ctx ~= nil then                                   -- the minute's class and exercise flag, for NR_Server_Writer's activity kind (ruling T6-2)
        ctx.activityClass = className
        ctx.exercising = exercising
    end
    if finite(coldMult) then body.coldMult = coldMult else body.coldMult = 1 end
    local ex0 = body.exKcalDay
    MET.spend(username, body, met, not moving, coldMult, dtM, exercising)   -- the minute's bill and the after-burn pool
    sat.L = K.deficit.exerciseLag(sat.L, body.exKcalDay - ex0, dtM / 60)   -- the minute's exercise kcal (spec § 5c)
    K.training.sample(body, K.energy.CLASS_MET[rateClass], heavyLevel, w, exercising, swiping, dtM)
    if climbClass ~= nil and dtM > 0 then K.training.climbCredit(body, climbClass, w) end
    local ironGrade, allReplete, dehydPct, g, debtH = nutrientInputs(record)
    if K.body.calendar(body, ageH, stepM > 60) == 1 then   -- a return after a gap closes nothing (ruling 13-5)
        closeDay(body, w, immobilised, ageH, ironGrade, debtH)
    end
    w = body.fm + body.lm + body.lx
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
    body.rmod = K.aerobic.rmod(body.tac, g, K.aerobic.gProt(body.pPrevKg), ironGrade, dehydPct, debtH, alcGkg, balanceBonus)
    local ex24 = K.body.trail24(body.trail, "ex")          -- the trailing-24 h exercise kcal
    body.energyState = K.deficit.activityState(K.energy.eb24h(body), ex24, sat.L, fatDep, MET.ee24(body))
    body.lastAgeH = ageH
    local ng = guardAll(body, sat)
    if ng > 0 then
        MET.guarded = MET.guarded + ng
        NR.log.say(2, "metabolism: " .. tostring(ng) .. " field(s) the step made non-finite re-stamped for " .. tostring(username))
    end
end

-- One player's minute: the pipeline's metabolism step (NR_Server_Minute.run, from P.work); ctx is its context.
-- One pcall around the body: a failure is kept and logged on the slow clock, never raised into the
-- players walk.
function MET.minute(username, player, record, ctx)
    if record == nil then return end
    MET.stats.minutes = MET.stats.minutes + 1
    local ok, err = pcall(step, username, player, record, ctx)
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

-- The design precondition (spec ruling 5): vanilla's nutrition update off. With
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
        local P = NR.server.players
        if P.onFirstSight ~= nil then P.onFirstSight[#P.onFirstSight + 1] = MET.onFirstSight end
        if P.onFirstSight ~= nil then P.onFirstSight[#P.onFirstSight + 1] = MET.forget end
        if P.onDeparture ~= nil then P.onDeparture[#P.onDeparture + 1] = MET.forget end
        MET.checkPrecondition()
        NR.server.minute.register("metabolism", MET.minute)
    end)
end
