-- NR_Server_Kinetics.lua -- the slow-clock drive of the stomach (spec § 4.2, § 4.4): once per player
-- per game minute, on the players' OnTick stagger, the stomach empties over the game hours since the
-- last run, the emptied vector is absorbed, the absorbed vector accumulates into the pool, and the
-- fill is stamped on the record as record.stomachFill for the fast clock to read
-- (NR_Server_Fast.lua hands it to the kernel as inp.stomachFill).
-- Plan 2 ruling: hunger derives from stomach fill and is written to HUNGER every tick, so vanilla's
-- eat-time hunger write is overwritten within one push -- the stomach is the state, hunger the view.
-- Two companion game choices make that playable: (1) a record with no stomach yet is seeded FULL
-- (K.stomach.seedFull) -- judgement: the character ate before the apocalypse, so a new or respawned
-- character starts at vanilla's hunger 0 and empties on the gastric half-time; (2) the energy-state
-- term, stubbed at 1 in Plan 2, is NR_Server_Metabolism's per-minute stamp (record.body.energyState;
-- the fast adapter reads nil or NaN as 1). Thirst is
-- untouched in this plan: vanilla's drain stays until Plan 4 derives thirst from the water pool.
-- design-phase-v1 game choice, the hunger timescale: the stomach's 2 h half-time (S0130,
-- design-phase-v1) makes hunger run from 0 to 0.5 in 2 game-hours, ~0.875 by 6 h and ~0.94 across an
-- 8 h sleep -- hours, where vanilla's drain takes ~29 game-hours to reach 1 -- and a litre of drink
-- (bulk >= 9 against FULL_BULK 8) sates fully; a balance choice re-read when S0130 settles (Plan 2
-- ruling T11).
-- Every field written on the record is a number or a table of numbers (global modData holds no
-- function or Java object, #1495). Nothing runs at file scope but table setup: the registration is
-- in the OnServerStarted handler behind the side test, so the file loads with no engine.
-- Ruling T17-1 (x151r #2981): the factor reads the meal in the stomach, not the share emptied this
-- minute -- the buffer's phytate, vitC and calcium (and its lipids, ruling T19-1: the fat factor) are
-- read into KIN.ctx BEFORE the emptying and absorb takes them; the calcium goes on to
-- NR_Server_Nutrients' calcium x iron factor through the pipeline context's mealCa.
local NR = NutritionRevamp
local K = NR.kernel
-- The hand-offs ride the pipeline's per-player context (NR_Server_Minute; Plan 10 R2): ctx.absorbed is the
-- absorbed vector of this player's step -- transient, never on the record -- that NR_Server_Metabolism reads
-- (the four macros) and NR_Server_Nutrients then consumes on the same minute (the pipeline's ORDER runs both
-- after this step; Plan 4 ruling 17); nil when the step had no elapsed time. ctx.mealCa: the buffer's calcium
-- mg before that step's emptying (the same lifetime), the meal calcium the calcium x iron factor reads. The
-- context is cleared at the start of each player's run. KIN.ctx: the one meal-context table, overwritten every
-- step. KIN.badAge: the minutes skipped for want of a clock read, outside stats (the golden trace walks stats).
NR.server.kinetics = { stats = { minutes = 0, players = 0, failures = 0 }, lastError = nil, wired = false,
                       ctx = {} }
local KIN = NR.server.kinetics

local function step(username, player, record, ctx)
    local age = NR.worldAge()
    if age == nil then
        if ctx ~= nil then
            ctx.absorbed = nil
            ctx.mealCa = nil
        end
        KIN.badAge = (KIN.badAge or 0) + 1        -- a minute with no clock read is skipped, never stamped 0
        return
    end
    if record.stomach == nil then
        record.stomach = K.stomach.new()
        K.stomach.seedFull(record.stomach)            -- judgement: the character ate before the apocalypse
    end
    if record.pool == nil then
        record.pool = K.vector.new()
    end
    local last = record.kineticsAge
    local dtH = 0
    if last ~= nil then
        dtH = K.max(age - last, 0)
    end
    record.kineticsAge = age
    if dtH > 0 then
        local meal = K.stomach.context(record.stomach, KIN.ctx)   -- the meal, before this minute's emptying
        local emptied = K.stomach.empty(record.stomach, dtH)
        local absorbed = K.stomach.absorb(emptied, meal)
        K.stomach.toPool(record.pool, absorbed)
        if ctx ~= nil then ctx.absorbed = absorbed end            -- the handoff to Metabolism, then Nutrients
        if ctx ~= nil then ctx.mealCa = meal.calcium end
    elseif ctx ~= nil then
        ctx.absorbed = nil
        ctx.mealCa = nil
    end
    local fill = K.stomach.fill(record.stomach)
    -- the self-heal for #2833: a non-finite fill (a stomach a NaN intake poisoned before the landing
    -- guard, or a corrupt record) is never stamped -- K.clamp passes NaN through -- so the stomach is
    -- reset to the full seed and the record heals on this minute instead of writing NaN into HUNGER
    -- for the session. The POOL is reset only when one of its own keys is non-finite: a finite pool
    -- is absorbed intake the stomach fault did not touch, so it is kept. NR.server.intake.isFinite is
    -- the one finiteness test: NR_Server_Intake.lua loads before this file (server/ files load
    -- alphabetically) and the test is read at call time.
    if type(fill) ~= "number" or fill ~= fill or fill == math.huge or fill == -math.huge then
        record.stomach = K.stomach.seedFull(K.stomach.new())
        local isFinite = NR.server.intake.isFinite
        local keys = K.vector.KEYS
        for i = 1, #keys do
            if not isFinite(record.pool[keys[i]]) then
                record.pool = K.vector.new()
                break
            end
        end
        fill = 1
        KIN.stats.failures = KIN.stats.failures + 1
        KIN.lastError = "kinetics: non-finite stomach fill for " .. tostring(username) .. "; stomach reset full"
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
    end)
end
