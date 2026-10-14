-- NR_Server_Kinetics.lua -- the slow-clock drive of the stomach (spec § 4.2, § 4.4): once per player per
-- game minute, inside the budgeted queue, both lanes empty over the game minutes since the last run (K.stomach.drain:
-- the solid lane's energy at a zero-order rate rising with its load, the liquid lane's water first-order), the
-- emptied vector is absorbed and the absorbed vector accumulates into the pool, and the physical fill (the stomach's
-- whole mass, both lanes, over its maximal capacity, K.stomach.fill; the writer's F reads K.stomach.fullnessMass through W.satietyF) is stamped on the record as record.stomachFill for the
-- writer's fallback and the mirror to read (the "fed" gates read the food fill, K.stomach.recordFoodFill). A gap of more than a minute drains in one-minute substeps (the
-- solid rate rises with the load, and the oracle's replays step a minute), and a gap is capped at 60 game minutes:
-- offline time is not integrated, as Metabolism and Nutrients clamp. A record with no stomach starts with an empty one
-- (spec § 4); hunger carries over through the meal pool M (record.satiety.M), which the intake feeds at the eat and this step clears
-- on every substep (K.satiety.drain); the writer seeds M from HUNGER at its first minute and reads it. The energy-state term is NR_Server_Metabolism's per-minute stamp
-- (record.body.energyState; the writer reads nil or NaN as 1).
-- Every field written on the record is a number or a table of numbers (global modData holds no
-- function or Java object, #1495). Nothing runs at file scope but table setup: the registration is
-- in the OnServerStarted handler behind the side test, so the file loads with no engine.
-- Run x151r (#2981): the factor reads the meal in the stomach, not the share emptied this
-- minute -- the buffer's phytate, vitC and calcium (and its lipids: the fat factor) are
-- read into KIN.ctx BEFORE the emptying and absorb takes them; the calcium goes on to
-- NR_Server_Nutrients' calcium x iron factor through the pipeline context's mealCa.
local NR = NutritionRevamp
local K = NR.kernel
-- The hand-offs ride the pipeline's per-player context (NR_Server_Minute; Plan 10 R2): ctx.absorbed is the
-- absorbed vector of this player's step -- transient, never on the record -- that NR_Server_Metabolism reads
-- (the four macros) and NR_Server_Nutrients then consumes on the same minute (the pipeline's ORDER runs both
-- after this step); nil when the step had no elapsed time. ctx.mealCa: the buffer's calcium
-- mg before that step's emptying (the same lifetime), the meal calcium the calcium x iron factor reads. The
-- context is cleared at the start of each player's run. KIN.ctx: the one meal-context table, overwritten every
-- step. KIN.badAge: the minutes skipped for want of a clock read, outside stats (the golden trace walks stats).
NR.server.kinetics = { stats = { minutes = 0, players = 0, failures = 0 }, lastError = nil, wired = false,
                       ctx = {} }
local KIN = NR.server.kinetics

-- The stomach fields a later reader takes that this step's arithmetic can leave non-finite (test_heal_once.py CROSS,
-- Plan 11c Task 8): a non-finite one resets the stomach empty with the fill. The liquid lane is named
-- (the pending water, the mirror's mass, the store) and EVERY vector key of the buffer is read at call time. The main
-- reason: an infinite gram key clamps the fill (the physical fill and the writer's fallback; the writer's F is W.satietyF) to 1, which is finite, so the fill alone
-- does not catch it, and that key never drains. A non-finite micronutrient would also spread into the pool and the
-- nutrients every minute. The cost is about 2.3 us per player-minute, per minute and never per tick.
KIN.GUARD = { "liquid" }

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

-- A gap's drain: dtM game minutes, capped at K.satiety.MAX_GAP_M, in one-minute substeps
-- (K.satiety.drain, the kernel's since Plan 11g Task 6, so the replays' stand-ins split a step as the server does).
-- Returns the emptied vector. pool is nil or KIN.meal's state, whose M each substep clears (K.satiety.mealClear).
-- The cap is the kernel's since the Plan 11g close, so replay_live's stand-in reads the same constant.
function KIN.drain(stomach, dtM, pool)
    return K.satiety.drain(stomach, K.min(dtM, K.satiety.MAX_GAP_M), pool)
end

-- The buffer check the step runs before the meal context and the drain, which raise on a
-- buffer key that is nil or a string (K.stomach.drain multiplies every key), so the heal below the fill never ran and
-- the stomach stayed malformed while the writer's F read failed. A stomach that is not a table, a buffer that is not
-- one, a buffer key (K.vector.KEYS) or a liquid lane that is not a number (an absent lane included) counts a
-- failure, is logged and answers true: the step resets the stomach empty on the minute it is found and keeps the pool.
-- A NaN or infinite number does not raise and stays with the heal below the fill (nonFinite).
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
        if type(stomach.liquid) ~= "number" then
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

-- The close fix wave's residual: the pool check the step runs before the drain, as KIN.malformed
-- runs the stomach's, since K.stomach.toPool raises on a pool key that is nil or a string. A pool that is not a table,
-- or a key of it (K.vector.KEYS) that is not a number, counts a failure, is logged and answers true: the step resets
-- the pool to zero on the minute it is found and keeps the stomach. A NaN or infinite key stays with the heal below
-- the fill.
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

-- Plan 11g Task 4 and its fix 1 (spec § 7): the meal pool M's clearance. The intake feeds M at
-- the eat (IN.feed); KIN.drain clears it on every substep (K.satiety.mealClear), and the writer, later in the minute's
-- ORDER, seeds M at first sight and reads it.
-- KIN.meal: the one pool state, overwritten every step: M as cleared, and the clearance factor, the appetite trait
-- (#0485) times the sandbox's stats-decrease multiplier. Returns nil for a record whose satiety is not
-- a table, or whose M is absent or non-finite: that M is left for the writer's seed.
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

-- The clearance factor: K.satiety.trait of the player's HEARTY_APPETITE and LIGHT_EATER, times the sandbox's
-- getStatsDecreaseMultiplier (1 when the sandbox or a trait is unreadable; a nil player reads no trait), read off the
-- sandbox object NR.sandbox() caches for every adapter. Rule 6: the traits handle is
-- KIN.traits', once per player object, and the multiplier is read once a player-minute and handed to the writer on
-- ctx.sd (W.readEngine), so the clearance adds no Java call to the P-model writer's minute.
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

-- Lands the cleared M on the record. An M the clearance made non-finite (a clearance that overflows) keeps the previous
-- M and counts a failure, as the step's other guards do.
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

-- Rule 6: the traits handle KIN.mealTrait reads, once per player object (as W.hoist: a
-- respawn or a reconnect is a new object, #3360), dropped at departure (KIN.forget). A nil username reads it afresh.
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
        record.stomach = K.stomach.new()              -- an empty stomach (spec § 4, ruling 11c-15); a malformed one heals (C-1)
    end
    if record.pool == nil or KIN.malformedPool(record.pool, username) then
        record.pool = K.vector.new()                  -- a fresh pool; a malformed one heals (Task 9b)
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
    -- the self-heal for #2833: a non-finite fill or KIN.GUARD field (a stomach a NaN intake poisoned before the
    -- landing guard, or a corrupt record) is never stamped -- K.clamp passes NaN through -- so the stomach is reset
    -- empty and the record heals on this minute instead of writing NaN into the satiety read. The POOL is reset only
    -- when one of its own keys is non-finite: a finite pool is absorbed intake the stomach fault did not touch, so it
    -- is kept. NR.finite is the one finiteness test of the fill, the guard and the pool.
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

-- One player's minute: the pipeline's kinetics step (NR_Server_Minute.run, from P.work); ctx is its context.
-- One pcall around the body: a failure is kept and logged on the slow clock, never raised into the
-- players walk.
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
