-- NR_Server_Minute.lua -- the slow minute's pipeline (Plan 10 Task R2): one declared order, one context table,
-- each step guarded so a raise is logged and the steps after it still run. Adapters register by name at
-- OnServerStarted; NR_Server_Players' P.work calls run. The order is 1.0.0's (the Reconcile splice and the Nutrients
-- hand call of Effects made explicit); the writer (Plan 11) runs after the eats and effects; the takeover's fast step is gone.
--
-- The context (ctx): one table reused per call and cleared at the start of each player's run, so nothing in it
-- outlives one player's minute. Its fields: absorbed and mealCa (Kinetics writes them; Metabolism and Nutrients
-- read them); sd (Kinetics' sandbox read), activityClass and exercising (Metabolism's), which the writer reads; body,
-- dtM and ageH (Nutrients stamps them where its minute reaches its end; the Effects step runs only when they are
-- stamped); and the minute's shared engine reads under NR.read's e-prefixed keys (eAge, the world age P.work read,
-- seeded here; eHour, eAsleep, eTraits, eBd, eThermo and eNut, each kept at its first read). An adapter that wraps
-- its own body in a pcall keeps it, with its own counters and log lines; this guard is the outer net, so a step that
-- raises inside its own pcall never reaches stats.failures here.
--
-- Registering a name again REPLACES that step's function. A name not in ORDER is never run. Slow-clock code,
-- with no fast-path region in this file; nothing runs at file scope but table setup, so the file loads with no
-- engine.
local NR = NutritionRevamp
NR.server.minute = {
    ORDER = { "bus", "reconcile", "kinetics", "metabolism", "nutrients", "effects", "strength", "weight", "writer", "store" },
    steps = {},
    ctx = {},
    stats = { runs = 0, failures = 0, deadRuns = 0 },
}
local MIN = NR.server.minute

-- A step's function: fn(username, player, record, ctx). Registering a name again replaces its function.
function MIN.register(name, fn)
    MIN.steps[name] = fn
end

-- One player's minute: clear the context, seed it with the minute's world age (ageH, P.work's read; nil leaves the
-- first step to read it), then every registered step in ORDER, each under its own pcall.
function MIN.run(username, player, record, ageH)
    local ctx = MIN.ctx
    for k in pairs(ctx) do ctx[k] = nil end
    ctx.eAge = ageH
    MIN.stats.runs = MIN.stats.runs + 1
    for i = 1, #MIN.ORDER do
        local fn = MIN.steps[MIN.ORDER[i]]
        if fn ~= nil then
            local ok, err = pcall(fn, username, player, record, ctx)
            if not ok then
                MIN.stats.failures = MIN.stats.failures + 1
                NR.log.say(2, "minute: " .. MIN.ORDER[i] .. " failed for " .. tostring(username) .. ": " .. tostring(err))
            end
        end
    end
end

-- A dead record's minute (Plan 11f Task 5b): only DEAD_ORDER's steps run, under the same guard -- the store's save,
-- so the record and its dead flag persist until OnNewGame's reset -- and nothing is stepped, written or sent.
MIN.DEAD_ORDER = { "store" }

function MIN.runDead(username, player, record)
    local ctx = MIN.ctx
    for k in pairs(ctx) do ctx[k] = nil end
    MIN.stats.deadRuns = MIN.stats.deadRuns + 1
    for i = 1, #MIN.DEAD_ORDER do
        local fn = MIN.steps[MIN.DEAD_ORDER[i]]
        if fn ~= nil then
            local ok, err = pcall(fn, username, player, record, ctx)
            if not ok then
                MIN.stats.failures = MIN.stats.failures + 1
                NR.log.say(2, "minute: " .. MIN.DEAD_ORDER[i] .. " failed for " .. tostring(username) .. ": " .. tostring(err))
            end
        end
    end
end
