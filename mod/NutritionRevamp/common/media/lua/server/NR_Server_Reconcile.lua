-- NR_Server_Reconcile.lua: the missed-intake reconciliation. Once per player per slow minute the four vanilla macro
-- stores are compared against the record's baseline, and a calorie rise above K.reconcile.RECONCILE_EPS is an intake the
-- wrapped seats never saw (another mod's eat, an admin write): it lands through IN.land as the four macros only. A fall
-- is never an intake. The baseline is then reset to the stores read this minute.
-- The baseline (derived: K.store.load drops it) is seeded at every first sight, since the player save and the global
-- table are written apart (#2098); reset by NR_Server_Weight to the values it WROTE under NR.LegacyMirror; and credited
-- by the intake with the stores' movement across a wrapped eat, so a landed intake is not landed twice.
-- Runs after the bus's effects flush and before Kinetics, so a reconciled intake empties the same minute.
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

-- nil when the Nutrition object or any store is unreadable or not finite.
function RC.read(character, ctx)
    local nut = NR.read.nutrition(ctx, character)
    if nut == nil then return nil end
    local out = {}
    for k, getter in pairs(GETTERS) do
        local ok, v = NR.call(nut, getter)
        if not ok or type(v) ~= "number" or v ~= v or v == math.huge or v == -math.huge then return nil end
        out[k] = v
    end
    return out
end

-- K.store.load keeps the count, not the baseline.
local function state(record)
    local rc = record.reconcile
    if type(rc) ~= "table" then
        rc = {}
        record.reconcile = rc
    end
    if type(rc.count) ~= "number" then rc.count = 0 end
    return rc
end

local function step(username, player, record, ctx)
    local store = RC.read(player, ctx)
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
        record.stomach = record.stomach or K.stomach.new()  -- an empty stomach, as the intake lays one
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

-- Under one pcall: a failure is counted and logged, never raised into the players walk.
function RC.minute(username, player, record, ctx)
    if record == nil then return end
    RC.stats.minutes = RC.stats.minutes + 1
    local ok, err = pcall(step, username, player, record, ctx)
    if not ok then
        RC.stats.errors = RC.stats.errors + 1
        RC.lastError = err
        NR.log.say(2, "reconcile: " .. tostring(username) .. " failed: " .. tostring(err))
    end
end

-- Left unset for the next readable minute when the stores cannot be read.
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

-- No baseline yet: nothing (the next first sight or minute seeds one).
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
