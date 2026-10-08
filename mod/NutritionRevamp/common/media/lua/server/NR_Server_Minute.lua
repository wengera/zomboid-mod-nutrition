-- NR_Server_Minute.lua -- the slow minute's pipeline (Plan 10 Task R2): one declared order, one context table,
-- each step guarded so a raise is logged and the steps after it still run. Adapters register by name at
-- OnServerStarted; NR_Server_Players' P.work calls run. The order is the order 1.0.0 ran in (the Reconcile splice
-- and the Nutrients hand call of Effects made explicit); the golden trace holds it byte for byte.
--
-- The context (ctx): one table reused per call and cleared at the start of each player's run, so nothing in it
-- outlives one player's minute. Its fields: absorbed and mealCa (Kinetics writes them; Metabolism and Nutrients
-- read them), and body, dtM and ageH (Nutrients stamps them where its minute reaches its end; the Effects step
-- runs only when they are stamped). An adapter that wraps its own body in a pcall keeps it, with its own
-- counters and log lines; this guard is the outer net, so a step that raises inside its own pcall never reaches
-- stats.failures here.
--
-- Registering a name again REPLACES that step's function. A name not in ORDER is never run. Slow-clock code,
-- with no fast-path region in this file; nothing runs at file scope but table setup, so the file loads with no
-- engine.
local NR = NutritionRevamp
NR.server.minute = {
    ORDER = { "bus", "fast", "reconcile", "kinetics", "metabolism", "nutrients", "effects", "strength", "weight", "store" },
    steps = {},
    ctx = {},
    stats = { runs = 0, failures = 0 },
}
local MIN = NR.server.minute

-- A step's function: fn(username, player, record, ctx). Registering a name again replaces its function.
function MIN.register(name, fn)
    MIN.steps[name] = fn
end

-- One player's minute: clear the context, then every registered step in ORDER, each under its own pcall.
function MIN.run(username, player, record)
    local ctx = MIN.ctx
    for k in pairs(ctx) do ctx[k] = nil end
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
