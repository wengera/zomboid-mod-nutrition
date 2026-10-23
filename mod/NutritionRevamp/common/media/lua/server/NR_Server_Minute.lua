-- NR_Server_Minute.lua: the slow minute's pipeline: one declared order, one context table, each step guarded so a raise
-- is logged and the steps after it still run. Adapters register by name at OnServerStarted; P.work calls run.
-- The context (ctx) is reused and cleared at the start of each player's run, so nothing in it outlives one player's
-- minute: the hand-offs (absorbed, mealCa, sd, activityClass, exercising, and body, dtM and ageH, without which Effects
-- does not run) and the shared engine reads under NR.read's e-prefixed keys. An adapter's own pcall keeps its own
-- counters; this guard is the outer net.
-- Registering a name again REPLACES that step's function; a name not in ORDER never runs.
local NR = NutritionRevamp
NR.server.minute = {
    ORDER = { "bus", "reconcile", "kinetics", "metabolism", "nutrients", "effects", "strength", "weight", "writer", "store" },
    steps = {},
    ctx = {},
    stats = { runs = 0, failures = 0, deadRuns = 0 },
}
local MIN = NR.server.minute

function MIN.register(name, fn)
    MIN.steps[name] = fn
end

-- Seeds ctx with the minute's world age, hour and day length and, in a stall's sub-steps, its asleep latch (nil leaves
-- the first step to read each); the shared engine reads are dropped at the end, so no Java handle outlives the minute.
function MIN.run(username, player, record, ageH, asleep)
    local ctx = MIN.ctx
    for k in pairs(ctx) do ctx[k] = nil end
    ctx.eAge = ageH
    ctx.eHour = NR.read.minuteHour
    ctx.eDayMin = NR.read.minuteDayMin
    ctx.eAsleep = asleep
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
    local keys = NR.read.KEYS
    for i = 1, #keys do
        ctx[keys[i]] = nil
    end
end

-- Only DEAD_ORDER's steps (the store's save), so the record and its dead flag persist until OnNewGame's reset.
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
