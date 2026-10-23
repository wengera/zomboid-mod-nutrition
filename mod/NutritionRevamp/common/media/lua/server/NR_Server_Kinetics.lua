-- NR_Server_Kinetics.lua: the slow-clock drive of the stomach. Once per player per game minute both lanes empty over
-- the minutes since the last run (K.stomach.drain), the emptied vector is absorbed into the pool, and the physical fill
-- is stamped as record.stomachFill (the writer's fallback and the mirror; the writer's F is W.satietyF). A longer gap
-- drains in one-minute substeps, since the solid rate rises with the load and the oracle's replays step a minute; the
-- resume keeps offline time out. The meal pool M is cleared on every substep (K.satiety.drain).
-- The absorption factor reads the meal in the stomach before the emptying, not the share emptied (#2981).
-- Record fields are numbers or tables of numbers (#1495); the registration is behind the side test at
-- OnServerStarted, so the file loads with no engine.
local NR = NutritionRevamp
local K = NR.kernel
-- The hand-offs ride the pipeline's per-player context, cleared at the start of each player's run: ctx.absorbed (never
-- on the record; Metabolism reads it, Nutrients consumes it) and ctx.mealCa. KIN.badAge sits outside stats, which the
-- golden trace walks.
NR.server.kinetics = { stats = { minutes = 0, players = 0, failures = 0 }, lastError = nil, wired = false,
                       ctx = {} }
local KIN = NR.server.kinetics

-- An infinite gram key clamps the fill to 1, which is finite, so the fill alone does not catch it and that key never
-- drains; a non-finite one resets the stomach empty. EVERY buffer key is read at call time. About 2.3 us a player-minute.
KIN.GUARD = { "liquid", "volX", "liqKcal" } -- volX: the satiety mass's volume excess; liqKcal: the drink-borne energy

local function nonFinite(stomach)
    for i = 1, #KIN.GUARD do
        local v = stomach[KIN.GUARD[i]]
        if not NR.finite(v) then return true end
    end
    local keys = K.vector.KEYS
    local b = stomach.buffer
    for i = 1, #keys do
        if not NR.finite(b[keys[i]]) then return true end
    end
    return false
end

-- In the kernel, so the replays' stand-ins split a step as the server does. No cap: the pipeline bounds the step.
function KIN.drain(stomach, dtM, pool)
    return K.satiety.drain(stomach, dtM, pool)
end

-- K.stomach.drain raises on a buffer key that is nil or a string, so a malformed stomach would never reach the heal:
-- it is reset empty on the minute it is found, the pool kept. A NaN or infinite number stays with the heal below.
function KIN.malformed(stomach, username)
    local bad = type(stomach) ~= "table" or type(stomach.buffer) ~= "table"
    if not bad then
        local keys = K.vector.KEYS
        local b = stomach.buffer
        for i = 1, #keys do
            if type(b[keys[i]]) ~= "number" then
                bad = true
                break
            end
        end
        if type(stomach.liquid) ~= "number" or type(stomach.volX) ~= "number" or type(stomach.liqKcal) ~= "number" then
            bad = true
        end
    end
    if not bad then
        return false
    end
    KIN.stats.failures = KIN.stats.failures + 1
    KIN.lastError = "kinetics: malformed stomach for " .. tostring(username) .. "; stomach reset empty"
    NR.log.say(2, KIN.lastError)
    return true
end

-- As KIN.malformed: K.stomach.toPool raises on a nil or string key, so the pool resets to zero, the stomach kept.
function KIN.malformedPool(pool, username)
    local bad = type(pool) ~= "table"
    if not bad then
        local keys = K.vector.KEYS
        for i = 1, #keys do
            if type(pool[keys[i]]) ~= "number" then
                bad = true
                break
            end
        end
    end
    if not bad then
        return false
    end
    KIN.stats.failures = KIN.stats.failures + 1
    KIN.lastError = "kinetics: malformed pool for " .. tostring(username) .. "; pool reset to zero"
    NR.log.say(2, KIN.lastError)
    return true
end

-- KIN.meal: the one pool state, overwritten every step. nil for a record whose satiety is not a table or whose M is
-- absent or non-finite: that M is left for the writer's seed.
KIN.mealState = { M = 0, trait = 1 }
function KIN.meal(record, player, username, ctx)
    local s = record.satiety
    if type(s) ~= "table" or not NR.finite(s.M) then
        return nil
    end
    local pool = KIN.mealState
    pool.M = s.M
    pool.trait = KIN.mealTrait(player, username, ctx)
    return pool
end

-- K.satiety.trait times getStatsDecreaseMultiplier (1 when unreadable). Rule 6: the multiplier is read once a
-- player-minute and handed to the writer on ctx.sd, so the clearance adds no Java call to its minute.
function KIN.mealTrait(player, username, ctx)
    local T = CharacterTrait
    local hearty = false
    local light = false
    if T ~= nil then
        local traits = KIN.traits(username, player)
        hearty = T.HEARTY_APPETITE ~= nil and NR.flag(traits, "get", T.HEARTY_APPETITE)
        light = T.LIGHT_EATER ~= nil and NR.flag(traits, "get", T.LIGHT_EATER)
    end
    local sd = NR.num(NR.sandbox(), "getStatsDecreaseMultiplier", 1)
    if ctx ~= nil then ctx.sd = sd end
    return K.satiety.trait(hearty, light) * sd
end

-- An overflowing clearance keeps the previous M and counts a failure.
function KIN.landMeal(record, pool, username)
    if pool == nil then
        return
    end
    if NR.finite(pool.M) then
        record.satiety.M = pool.M
        return
    end
    KIN.stats.failures = KIN.stats.failures + 1
    KIN.lastError = "kinetics: non-finite meal pool clearance for " .. tostring(username) .. "; M kept"
    NR.log.say(2, KIN.lastError)
end

-- Once per player object (a respawn or a reconnect is a new object, #3360), dropped at departure.
KIN.h = {}
function KIN.traits(username, player)
    if username == nil then
        return NR.obj(player, "getCharacterTraits")
    end
    local c = KIN.h[username]
    if c == nil or c.p ~= player then
        c = { p = player, traits = NR.obj(player, "getCharacterTraits") }
        KIN.h[username] = c
    end
    return c.traits
end

function KIN.forget(username)
    KIN.h[username] = nil
end

local function step(username, player, record, ctx)
    local age = NR.read.ageH(ctx)
    if age == nil then
        if ctx ~= nil then
            ctx.absorbed = nil
            ctx.mealCa = nil
        end
        KIN.badAge = (KIN.badAge or 0) + 1        -- a minute with no clock read is skipped, never stamped 0
        return
    end
    if record.stomach == nil or KIN.malformed(record.stomach, username) then
        record.stomach = K.stomach.new()              -- an empty stomach; a malformed one heals
    end
    if record.pool == nil or KIN.malformedPool(record.pool, username) then
        record.pool = K.vector.new()                  -- a fresh pool; a malformed one heals
    end
    local last = record.kineticsAge
    local dtH = 0
    if last ~= nil then
        dtH = K.max(age - last, 0)
    end
    record.kineticsAge = age
    if dtH > 0 then
        local meal = K.stomach.context(record.stomach, KIN.ctx)   -- the meal, before this minute's emptying
        local pool = KIN.meal(record, player, username, ctx)       -- nil for an M the writer has yet to seed
        if pool ~= nil then
            -- the meal spell reads the pool before this minute's clearance takes it: read after, a 200 kcal snack opened no spell
            K.drain.spellStep(K.drain.ensure(record), pool.M)
        end
        local emptied = KIN.drain(record.stomach, dtH * 60, pool)
        KIN.landMeal(record, pool, username)
        local absorbed = K.stomach.absorb(emptied, meal)
        K.stomach.toPool(record.pool, absorbed)
        if ctx ~= nil then ctx.absorbed = absorbed end            -- the handoff to Metabolism, then Nutrients
        if ctx ~= nil then ctx.mealCa = meal.calcium end
    elseif ctx ~= nil then
        ctx.absorbed = nil
        ctx.mealCa = nil
    end
    local fill = K.stomach.fill(record.stomach)
    -- #2833: K.clamp passes NaN through, so a non-finite fill or KIN.GUARD field resets the stomach empty instead of writing
    -- NaN into the satiety read. The pool is reset only when one of its own keys is non-finite.
    if not NR.finite(fill) or nonFinite(record.stomach) then
        record.stomach = K.stomach.new()
        if ctx ~= nil then
            ctx.absorbed = nil                       -- this minute's absorbed vector came from the bad buffer
            ctx.mealCa = nil
        end
        local keys = K.vector.KEYS
        for i = 1, #keys do
            if not NR.finite(record.pool[keys[i]]) then
                record.pool = K.vector.new()
                break
            end
        end
        fill = 0
        KIN.stats.failures = KIN.stats.failures + 1
        KIN.lastError = "kinetics: non-finite stomach fill for " .. tostring(username) .. "; stomach reset empty"
        NR.log.say(2, KIN.lastError)
    end
    record.stomachFill = fill
    KIN.stats.players = KIN.stats.players + 1
end

-- One pcall around the body: a failure is kept and logged, never raised into the players walk.
function KIN.minute(username, player, record, ctx)
    if record == nil then return end
    KIN.stats.minutes = KIN.stats.minutes + 1
    local ok, err = pcall(step, username, player, record, ctx)
    if not ok then
        KIN.stats.failures = KIN.stats.failures + 1
        KIN.lastError = err
        NR.log.say(2, "kinetics: " .. tostring(username) .. " failed: " .. tostring(err))
    end
end

if Events ~= nil and Events.OnServerStarted ~= nil then
    Events.OnServerStarted.Add(function()
        if not NR.isServer() then return end
        if KIN.wired then return end
        KIN.wired = true
        local MIN = NR.server.minute
        MIN.register("kinetics", KIN.minute)
        local P = NR.server.players
        if P ~= nil and P.onDeparture ~= nil then P.onDeparture[#P.onDeparture + 1] = KIN.forget end
    end)
end
