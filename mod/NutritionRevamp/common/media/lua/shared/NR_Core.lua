-- NR_Core.lua -- the mod's one global, its version, the side test and the index-first guard.
-- Loads first in shared/ by name; every other NR_ file assumes NutritionRevamp exists.
-- Plain assignment on every load: a reload of this file resets the sub-tables, so no sentinel
-- for a wrapped vanilla function may live here (lua-platform rule #0943).
NutritionRevamp = {
    version = "0.1.0",
    build = "42.20.4",
    kernel = {},   -- pure functions, tables in and tables out, no Java (NR_Kernel*.lua)
    server = {},   -- server adapters (server/NR_Server_*.lua), gated by NutritionRevamp.isServer()
    client = {},   -- the read-only mirror (client/NR_Client_*.lua)
    log = { level = 2 },
}
local NR = NutritionRevamp

-- The side test, nil-checked before the protected call that reads it (#0937), evaluated per
-- call and never cached at file scope: a Lua state can load this file before the side is
-- decided, and a mod's server/ files run in the client's state too (#0855).
function NR.isServer()
    if isServer == nil then return false end
    local ok, v = pcall(isServer)
    return ok and v == true
end

function NR.isClient()
    if isClient == nil then return false end
    local ok, v = pcall(isClient)
    return ok and v == true
end

-- The index-first guard (#0934, #0935): index the member, then call it. Returns
-- (present, result...). A caught nil call names nothing, so the guard is what makes an absent
-- member visible. Never used inside a @fastpath region, which hoists its handles instead.
function NR.call(obj, name, ...)
    if obj == nil then return false, nil end
    local m = obj[name]
    if m == nil then return false, nil end
    return true, m(obj, ...)
end

-- Console lines on whichever side runs this. level 1 quiet (the boot self-report only),
-- 2 normal, 3 verbose. The level is set from the sandbox option at event time (NR_Server_Options).
function NR.log.say(level, msg)
    if level <= NR.log.level then print("[NutritionRevamp] " .. tostring(msg)) end
end
