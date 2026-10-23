-- NR_Server_Metabolism.lua: the body model's slow-clock adapter. Once per player per game minute, after the stomach
-- step, it creates record.body at first sight, bills the minute's expenditure off the server's metabolic rate, banks
-- the intake Kinetics handed off, samples the training signal, closes the record day after 24 online game hours, and
-- stamps the coefficients and the energy state (K.deficit.activityState) the writer reads.
-- Pitfalls: the thermoregulator TARGET reads -1 at every tick server-side, so only the RATE is read, which lags
-- activity and already carries the engine's load factor (divided out before bucketing); the current timed action is
-- unreadable server-side (getCharacterActions is empty), so the calorie modifier is always 1.
-- Two MET tables, never mixed: expenditure bills the Compendium MET; the training sample banks the engine's own value.
-- The minute runs under one pcall per player; record.body holds numbers, booleans, strings and tables of numbers
-- (#1495). Java globals are named only inside functions behind a nil check. Slow-clock code.
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
        "nothing changes offline: the resume at a return moves every world-age stamp past the absence, so no time away is integrated and a record day closes after 24 online game hours, drifting from the world's day boundary by every absence; a server stall with the player online is integrated in sub-steps of at most 60 game minutes, at most four a queue slot and the rest carried to the player's next minutes, so a player who leaves mid-carry has the part not yet integrated frozen as absence; after a stall over 4 h an eat during the carry lands at the current world age while the integration catches up over a few minutes, so that meal is digested across the carried hours and its monotony count reads high until the carry ends",
        "the disuse arm needs a leg fracture or splint",
        "the nutrient scalars (glycogen, dehydration, iron, caffeine, sleep debt, alcohol, the balance dial) read the previous minute's record sub-tables (a one-minute lag; the pipeline's ORDER runs the nutrients step after this one)",
        "the drain coefficient is stamped and mirrored and drives no stat write",
        "a climb is credited when the minute sample lands inside the climb state; short climbs are missed",
        "the MET-minute bank is mirrored for the panel and feeds no coefficient; the aerobic dose is the band minutes",
        "the engine's inventory weight is read as kilograms",
        "an exhausted idle character's metabolic rate sits at the tired floor (up to the DefaultExercise class), so exhaustion bills as activity",
        "rmod scales the asleep regeneration arm only; under the harness's partial sleep hold it measured 0.904 for a predicted 0.848 (#2899)",
        "a day closes at 07:00 on the default fixture (#2890) until the player's first absence moves the record day off the world's boundary; the 24 h blends count hours since the last close",
        "an unreadable world age skips the minute; a first sight with an unreadable age sends its mirror without the body, which the next readable minute builds",
        "rmod's alcohol arm reads body.alcDay, the day-so-far ethanol the partition close zeroes: the arm resets at the day close, not on a rolling 24 h",
        "a field the step's own arithmetic leaves non-finite and no later step reads in the same minute stays so until the next minute's pre-step heal",
        "every Fitness exercise bills its type's Compendium MET (K.energy.EXERCISE_MET, the general or moderate code, a game choice) while the server's exercise flag is set, from the type NR_Server_Fitness recorded at the set's start; a set with no recorded or no known type bills the flat Fitness class (6.0), counted in stats.exeFallbacks; walking, chopping and fighting keep the metabolic rate's rise lag",
        "a minute whose raw metabolic rate is falling with no exercise and no movement bills the idle class, so a step down to a lighter activity while standing bills idle until the rate settles; the previous rate is held in memory, so the first minute after a boot reads no fall; the fall is read on the raw rate, so a still player at a sustained class above idle who drops weight (an eat, a sip) may bill one idle minute; body.met, which sweat and fluids (NR_Server_Nutrients), the glycogen draw and Effects' exertion heat (NR_Server_Effects) also read, so reads the set's billed MET on every set minute and 1.3 on every standing fall",
        "the after-burn follows the exercise flag's minutes only, at a fixed share of their exercise kcal released on a fixed game-time constant, whatever the intensity or the day length",
        "a fresh record's 24 h window holds no meals: it reads like an even eater, its energy state rising from first sight at its expenditure rate (a new character or a respawn reaches energy level 1 after several unfed hours, inside the model's range for a skipped meal)",
        "a fresh record laid over a character the mod has already changed (a store file lost or corrupt while the character holds no valid backup of the record, as when another mod's client transmitModData wiped the copy inside the save gap before the engine's player save the character came back from, a record that raises at its load, or a deferral that gives up) infers its muscle pick from the native Strength level net of the profession's and the other held traits' Strength boosts (vanilla's boost table; the held band trait at a clamped level 0 or 10 or an unmapped offset) and restarts at that pick's start level plus the profession's boost, so a native level the mod or training moved reads as another pick: a Stout pick under +1 whose native level fell from 8 to 6 is read as no pick; and a Night Vision or Short Sighted trait the lost record owned stays, since the effects own only the traits they added",
        "an immobilised day runs the disuse arm in place of growth, regain and detraining: the grace counter and the neural factor still step, the remembered peak does not decay that day",
    },
}
local MET = NR.server.metabolism

MET.LEG_PARTS = { "UpperLeg_L", "UpperLeg_R", "LowerLeg_L", "LowerLeg_R" }

-- The post-step guard: the body fields something reads before the next minute's
-- heal are re-stamped from a pre-step copy when the step leaves them non-finite. A ring takes this minute's values only
-- in slot 7, and the trailing window only in its age and current hour's slot, so those are guarded.
MET.GUARD = { "fm", "lm", "energyState", "rmod", "met", "coldMult", "eeDay", "inDay", "alcDay", "pPrevKg",
              "inDayClosed", "dayIndex", "band1Day", "band2Day", "exKcalDay", "carbDay", "pDay",
              "lipDay", "ebDay", "tDisuse", "tac", "lastAgeH", "epoc", "lx", "Pk", "T" }
MET.GUARD_RINGS = { "eb7", "p7", "mass7" }
MET.GUARD_TRAIL = { "at" }
MET.TRAIL_SLOT = { 1 } -- an index list: the trailing window's current hour slot, rewritten at each snap: no row needed
MET.snapTrail = {}
MET.snapTrailRings = {}
-- Stepped here, healed by the writer and saved by the store.
MET.GUARD_SATIETY = { "L" }
MET.snapSatiety = {}
MET.SLOT7 = { 7 } -- an index list: slot 7 of each read ring: no row needed
MET.BAND_SLOT = { 1, 2 } -- an index list: the two band slots of bandWeek's latest day: no row needed
MET.snap = {}
MET.snapRings = { eb7 = {}, p7 = {}, mass7 = {} }
MET.snapBand = {}
MET.guarded = 0 -- the count of fields the post-step guard re-stamped: no row needed
MET.BALANCE_BONUS = K.dials.get("met.BALANCE_BONUS")

local finite = NR.finite

-- nil when unread: the minute is then skipped and counted, never stamped 0.
local worldAge = NR.worldAge

local num = NR.num

-- true only when the member is present and answers true.
local flag = NR.flag

local obj = NR.obj

-- Off the sub-tables NR_Server_Nutrients writes, which runs after this step: the PREVIOUS minute's stamps (a one-minute
-- lag). An absent, non-finite or out-of-range field reads its neutral.
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

-- First sight: the creation body over the muscle pick (CRE.musclePick, read off the native level net of the boosts: the
-- held band alone would misread a boosted profession's band as a pick) and the held weight band trait, never the weight
-- or carry delta. An existing record.body is never re-read.
function MET.ensureBody(username, player, record, ageH)
    if record.body ~= nil then return record.body end
    local CRE = NR.server.creation                      -- its readers, read at call time (Creation loads first)
    local traits = obj(player, "getCharacterTraits")
    local pdef = CRE.professionDef(player)
    local muscle = CRE.musclePick(player, traits, pdef)
    local weight = CRE.heldTrait(traits, K.traits.WEIGHT_TRAITS)
    local body = CRE.newBody(player, muscle, weight, ageH, CRE.strengthBoost(pdef))
    body.levelDue = true
    record.body = body
    MET.stats.creates = MET.stats.creates + 1
    NR.log.say(3, "metabolism: first sight of " .. tostring(username) .. " sex=" .. body.sex .. " muscle="
        .. tostring(muscle) .. " weight=" .. tostring(weight))
    return body
end

-- ctx (optional) is the pipeline's, whose shared engine reads it takes and keeps. climbClass is a per-minute state
-- sample, so a climb shorter than the gap between samples is missed.
function MET.readActivity(player, ctx)
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
    return className, moving, 1, loadKg, heavyLevel, coldMult, exercising, swiping, immobilised,
        maxW, climbClass, okR and finite(rate) and rate or nil
end

-- One day close. Each reader runs after the writer of what it reads, or it lags one close: the disuse count before the
-- masses move; the training ring shifts the day in BEFORE TAC reads the week; TAC reads inDay and exKcalDay before
-- the partition ring zeroes them; the AT step reads deficitWeek AFTER it, so the week includes today. fmRef is re-based
-- upward (AT reads depletion from the highest fat reached).

-- Exercise billed by the activity (K.energy.billClass). The previous minute's RAW rate and exercise flag are held per
-- user in memory only, so the first minute after a boot reads no fall. The fall is decided raw against raw: an eat drops
-- the inventory load at once while the raw rate still carries it, so dividing by the new factor would hide the fall.
-- The minute the flag clears counts as falling too: a drain a tick after the clear can still read the rate's last rise.
MET.prevRate = {}
MET.prevExe = {}

function MET.readBilled(username, player, ctx)
    local className, moving, modifier, loadKg, heavyLevel, coldMult, exercising, swiping, immobilised,
        maxW, climbClass, rate = MET.readActivity(player, ctx)
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
        maxW, climbClass, className, exMet
end

-- NR_Server_Fitness.lua's recorded type (C-2); a Lua lookup, no Java (Rule 6). Called only on a set minute, so a clear
-- flag never reads a stale type; nil bills the flat Fitness class (exeFallbacks).
function MET.exeTypeOf(username, exercising)
    if not exercising then return nil end
    local F = NR.server.fitness
    if F == nil or F.typeOf == nil then return nil end
    return F.typeOf(username)
end

-- The pool's release is expenditure, never exercise kcal: the lag L stepped on exKcalDay's rise does not see it.
function MET.spend(username, body, met, resting, coldMult, dtM, exercising)
    local ex0 = body.exKcalDay
    K.energy.minute(body, met, resting, coldMult, dtM)
    local _, healed = K.energy.epoc(body, exercising, body.exKcalDay - ex0, dtM)
    if healed then
        MET.guarded = MET.guarded + 1
        NR.log.say(2, "metabolism: non-finite or negative body.epoc for " .. tostring(username) .. "; stamped 0")
    end
end

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
    local P = NR.strengthP()
    local S = K.strength.signalClose(body) / P.xpPerSet
    local pPerKg = body.pDay / w
    local tdee = K.max(body.eeDay, K.energy.ree(body.lm))
    if immobilised then
        K.strength.disuseDay(body, S, P, P.ts)           -- the disuse arm in place of growth and detraining
    else
        K.strength.day(body, S, pPerKg, body.ebDay, tdee, body.alcDay / w, P, P.ts)
    end
    body.fmRef = K.max(body.fmRef, body.fm)
    local band = K.traits.axes(body, K.body.effSex(body.sex, NR.sexSpecific()))
    if band ~= body.band then
        body.band = band
        body.traitsDirty = true
    end
    body.S = S
    body.levelDue = true                                 -- the Strength minute writes the day's level
    K.training.closeDay(body)
    local m1, hard = K.training.weekMinutes(body)
    K.aerobic.tacDay(body, m1, hard, K.aerobic.G_IRON[ironGrade], K.aerobic.gProt(pPerKg), K.aerobic.gEnergy(body.inDay, body.exKcalDay, body.lm), K.aerobic.gSleep(debtH), 1, immobilised)
    body.pPrevKg = pPerKg
    K.drain.closeDay(body)                               -- the closing day's absorbed kcal into inDayClosed, for NR_Server_Nutrients' refeeding close, and the two before it down one (the drain's recent intake)
    K.partition.closeDay(body)
    body.at = K.energy.atStep(body.at, K.energy.atTarget(body.fm, body.fmRef), K.partition.deficitWeek(body), 1)
    MET.stats.days = MET.stats.days + 1
end
if NR_BENCH then MET._closeDay = closeDay end   -- the day-close bench seam (tools/bench_day_close.py)

-- The self-heal (the #2833 pattern), run once, before the minute's arithmetic: K.heal.body stamps every non-finite
-- scalar or ring slot its neutral; a pass that healed anything counts one failure and names every field. The kernel's
-- tables are read at call time, so the file loads in a runtime that holds NR_Core alone (the wiring tests).

-- The Nutrients step's last day count, else the Effects step's, else nil (the kernel reads the world day).
function MET.dayFloor(record)
    local n, e = record.nutrients, record.effects
    if type(n) == "table" and finite(n.lastDayIndex) then return n.lastDayIndex end
    if type(e) == "table" and finite(e.lastDay) then return e.lastDay end
    return nil
end

local function heal(username, record, body, ageH)
    local floor = nil
    if not finite(body.dayIndex) then floor = MET.dayFloor(record) end   -- read only when the heal needs it
    local bad = K.heal.body(body, ageH, NR.sexSpecific(), NR.strengthP(), floor)
    if bad ~= nil then
        MET.stats.failures = MET.stats.failures + 1
        MET.lastError = "metabolism: non-finite " .. bad .. " for " .. tostring(username) .. "; stamped neutral"
        NR.log.say(2, MET.lastError)
    end
end

-- exerciseLag passes a negative L through, so it is healed here; M is the writer's to seed.
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

-- Floored at the resting expenditure, so a window younger than a day reads at least a resting day.
function MET.ee24(body)
    return K.max(K.body.trail24(body.trail, "ee"), K.energy.ree(body.lm))
end

-- Taken after the heal and the window's move.
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
    local dtM = K.max((ageH - body.lastAgeH) * 60, 0)    -- the pipeline's step (offline time never reaches it: the resume)
    K.body.trailTo(body.trail, K.body.trailClock(body, ageH))   -- the window to this minute on its online clock, before its intake and expenditure land
    snapAll(body, sat)
    local w = body.fm + body.lm + body.lx                 -- the body mass
    -- read, never cleared: NR_Server_Nutrients consumes the handoff and the context lives one player's minute
    local handoff = ctx and ctx.absorbed
    if handoff ~= nil then
        K.energy.intake(body, handoff, dtM)
    end
    local className, moving, modifier, loadKg, heavyLevel, coldMult, exercising, swiping, immobilised,
        maxW, climbClass, rateClass, exMet = MET.readBilled(username, player, ctx)
    local met = K.energy.activityMet(className, moving, modifier, loadKg, exMet)
    -- always finite (1 when the read is not)
    if finite(met) then body.met = met else body.met = 1 end
    if ctx ~= nil then                                   -- the minute's class and exercise flag, for NR_Server_Writer's activity kind
        ctx.activityClass = className
        ctx.exercising = exercising
    end
    if finite(coldMult) then body.coldMult = coldMult else body.coldMult = 1 end
    local ex0 = body.exKcalDay
    MET.spend(username, body, met, not moving, coldMult, dtM, exercising)   -- the minute's bill and the after-burn pool
    sat.L = K.deficit.exerciseLag(sat.L, body.exKcalDay - ex0, dtM / 60)   -- the minute's exercise kcal
    K.training.sample(body, K.energy.CLASS_MET[rateClass], heavyLevel, w, exercising, swiping, dtM)
    if climbClass ~= nil and dtM > 0 then K.training.climbCredit(body, climbClass, w) end
    local ironGrade, allReplete, dehydPct, g, debtH = nutrientInputs(record)
    if K.body.calendar(body, ageH) == 1 then             -- 24 online hours since the record day's start
        closeDay(body, w, immobilised, ageH, ironGrade, debtH)
    end
    w = body.fm + body.lm + body.lx
    local fatDep = 0
    if body.fmRef > 0 then fatDep = K.clamp((body.fmRef - body.fm) / body.fmRef, 0, 1) end
    -- the balance dial (NR.BalanceBonus, an absent options table reads on) while every pool record is replete
    local opts = NR.server.options
    local balanceBonus = 1
    if allReplete and (opts == nil or opts.balanceBonus ~= false) then
        balanceBonus = MET.BALANCE_BONUS                   -- game choice (met.BALANCE_BONUS)
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

-- One pcall around the body: a failure is kept and logged, never raised into the players walk.
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

-- The body is made before the first mirror goes out, so that mirror carries the body_* keys; this is the one
-- first-sight mirror (Players sends none, and its OnNewGame reset fires this hook too). An unreadable world age defers
-- the body to the next readable minute.
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

-- The design precondition: with SandboxVars.Nutrition anything but false, vanilla's updateWeight rewrites the weight
-- flags every tick and its drain empties the mirror stores. Read once at boot and warned; the option is the operator's,
-- never changed by the mod.
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

-- This file sorts before NR_Server_Options.lua, so its handler sets the flag before the boot self-report.
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
