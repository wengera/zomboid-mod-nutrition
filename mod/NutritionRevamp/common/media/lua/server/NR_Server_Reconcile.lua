-- NR_Server_Reconcile.lua -- the missed-intake reconciliation (Plan 8 ruling 6; spec § 4.8, § 7 item 38):
-- once per player per slow minute it reads the four vanilla macro stores, compares them against the
-- record's baseline (K.reconcile.delta), and a calorie rise above K.reconcile.RECONCILE_EPS is an intake the
-- wrapped seats never saw (another mod's eat or drink action, an admin write): it lands through the intake's
-- own landing (NR.server.intake.land) as the four macros only, every other vector key 0, with
-- lastIntake.source = "reconciled", the kernel's note and record.reconcile.count bumped. A fall is never an
-- intake. The baseline is then reset to the stores read this minute, landed or not.
--
-- The baseline (record.reconcile.baseline, derived: K.store.load drops it) is:
--  * seeded from the stores at every first sight (this file's onFirstSight hook; an OnNewGame respawn fires
--    it too), since the player save and the global table are written apart (#2098); a minute that finds no
--    baseline seeds one and lands nothing;
--  * reset to the stores at the end of this minute's step;
--  * reset by NR_Server_Weight to the four values it WROTE when NR.LegacyMirror is on (its write follows this
--    step in the same minute), so the next minute compares against the mod's own last write;
--  * credited by NR_Server_Intake with the stores' own movement across a wrapped eat, drink or world-water
--    step (RC.credit: after minus before, read around the original inside the wrap), so an intake the wrap
--    already landed is not landed twice and a write by another writer earlier in the same minute is not
--    absorbed into the baseline.
--
-- The minute order (the pipeline's declared ORDER, NR_Server_Minute): the reconcile step runs after the bus's
-- effects flush and the fast clock's handle refresh and before the stomach (Kinetics), so a player's minute
-- runs: the bus's effects flush, the fast clock's handle refresh, THIS step, the stomach (Kinetics),
-- Metabolism, Nutrients, Effects, Strength, Weight (the legacy write). The order is the one 1.0.0's splice
-- into P.onMinute produced (before Kinetics' minute); the pipeline names it rather than inserting into a
-- list. A reconciled intake is then
-- emptied by the same minute's Kinetics step.
--
-- Every Java read goes through NR.call (index-first); every Java global is named only inside a function
-- behind a nil check, so the file loads with no engine (testing/tests/kernel/test_server_reconcile_shape.py).
-- The minute runs under one pcall per player and never raises into the players walk.
-- Slow-clock code: no @fastpath region in this file.
local NR = NutritionRevamp
local K = NR.kernel
NR.server.reconcile = {
    stats = { minutes = 0, landed = 0, skipped = 0, noStore = 0, errors = 0, seeded = 0, credits = 0 },
    lastError = nil,
    wired = false,
    limitations = {
        "a rise is reconciled as the four macros only; the nutrient vector of a missed intake is unknown and lands nothing",
        "the baseline is the legacy mirror's last write when NR.LegacyMirror is on, else the last observed store value, plus each wrapped eat's credited store movement",
        "a rise within RECONCILE_EPS kcal is ignored; a fall (vanilla's drain only with Nutrition on, or another writer) is never reconciled",
        "with Nutrition = true the vanilla update only subtracts (its macro drain and calorie burn, #0453), so a missed intake is netted against that fall between two minutes and one smaller than the fall is lost: the mod's precondition is Nutrition = false",
        "a write by another writer inside a wrapped eat's original (a mod wrapping the same seat below this one, or an item's OnEat hook, which runs inside Eat) moves the stores inside the wrap and is credited to the baseline as part of the eat",
    },
}
local RC = NR.server.reconcile

local GETTERS = { calories = "getCalories", carbs = "getCarbohydrates", lipids = "getLipids", proteins = "getProteins" }

-- The four vanilla macro stores of a character, keyed by the vector's macro names, or nil when the
-- Nutrition object or any store is unreadable or not a finite number.
function RC.read(character)
    local okN, nut = NR.call(character, "getNutrition")
    if not okN or nut == nil then return nil end
    local out = {}
    for k, getter in pairs(GETTERS) do
        local ok, v = NR.call(nut, getter)
        if not ok or type(v) ~= "number" or v ~= v or v == math.huge or v == -math.huge then return nil end
        out[k] = v
    end
    return out
end

-- The record's reconciliation table, laid when absent (the count kept by K.store.load, the baseline not).
local function state(record)
    local rc = record.reconcile
    if type(rc) ~= "table" then
        rc = {}
        record.reconcile = rc
    end
    if type(rc.count) ~= "number" then rc.count = 0 end
    return rc
end

-- One player's step: read, compare, land, reset.
local function step(username, player, record)
    local store = RC.read(player)
    if store == nil then
        RC.stats.noStore = RC.stats.noStore + 1
        return
    end
    local rc = state(record)
    if type(rc.baseline) ~= "table" then
        rc.baseline = K.reconcile.baselineAfter(store)
        RC.stats.seeded = RC.stats.seeded + 1
        return
    end
    local delta = K.reconcile.delta(store, rc.baseline)
    local vec, note = K.reconcile.intake(delta, K.reconcile.RECONCILE_EPS)
    if vec ~= nil then
        local IN = NR.server.intake
        if IN == nil or IN.land == nil then error("reconcile: NR.server.intake.land absent") end
        record.stomach = record.stomach or K.stomach.seedFull(K.stomach.new())  -- as the intake seeds an early eat
        record.pool = record.pool or K.vector.new()
        local macros = K.reconcile.baselineAfter(vec)       -- the four landed macros, copied before the landing
        IN.land(record, username, vec)
        record.lastIntake = { source = "reconciled", note = note, calories = macros.calories,
                              carbs = macros.carbs, lipids = macros.lipids, proteins = macros.proteins }
        rc.count = rc.count + 1
        RC.stats.landed = RC.stats.landed + 1
        NR.log.say(3, "reconcile: " .. tostring(username) .. " missed intake " .. tostring(macros.calories)
            .. " kcal landed as macros only (" .. tostring(rc.count) .. ")")
    else
        RC.stats.skipped = RC.stats.skipped + 1
    end
    rc.baseline = K.reconcile.baselineAfter(store)
end

-- One player's minute: the pipeline's reconcile step (NR_Server_Minute.run, called from P.work), under
-- one pcall: a failure is counted and logged on the slow clock, never raised into the players walk.
function RC.minute(username, player, record)
    if record == nil then return end
    RC.stats.minutes = RC.stats.minutes + 1
    local ok, err = pcall(step, username, player, record)
    if not ok then
        RC.stats.errors = RC.stats.errors + 1
        RC.lastError = err
        NR.log.say(2, "reconcile: " .. tostring(username) .. " failed: " .. tostring(err))
    end
end

-- First sight (and an OnNewGame respawn): the baseline re-seeded from the stores read now, or left unset
-- for the next readable minute to seed.
function RC.onFirstSight(username, player, record)
    if record == nil then return end
    local rc = state(record)
    local ok, store = pcall(RC.read, player)
    if ok and store ~= nil then
        rc.baseline = K.reconcile.baselineAfter(store)
        RC.stats.seeded = RC.stats.seeded + 1
    else
        rc.baseline = nil
    end
end

-- The wrapped seat's credit (NR_Server_Intake): the stores' own movement across the original, after minus
-- before, added to the baseline, so the next minute's delta does not count an intake the wrap landed. No
-- baseline yet: nothing (the next first sight or minute seeds one from the stores).
function RC.credit(record, before, after)
    if record == nil or before == nil or after == nil then return false end
    local rc = record.reconcile
    if type(rc) ~= "table" or type(rc.baseline) ~= "table" then return false end
    local d = K.reconcile.delta(after, before)
    for k, v in pairs(d) do
        rc.baseline[k] = (rc.baseline[k] or 0) + v
    end
    RC.stats.credits = RC.stats.credits + 1
    return true
end

if Events ~= nil and Events.OnServerStarted ~= nil then
    Events.OnServerStarted.Add(function()
        if not NR.isServer() then return end
        if RC.wired then return end
        local P = NR.server.players
        if P == nil then return end
        RC.wired = true
        NR.server.minute.register("reconcile", RC.minute)
        P.onFirstSight[#P.onFirstSight + 1] = RC.onFirstSight
    end)
end
