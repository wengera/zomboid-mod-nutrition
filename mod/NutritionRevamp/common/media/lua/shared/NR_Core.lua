-- NR_Core.lua -- the mod's one global, its version, the side test and the index-first guard.
-- Loads first in shared/ by name; every other NR_ file assumes NutritionRevamp exists.
-- Plain assignment on every load: a reload of this file resets the sub-tables, so no sentinel
-- for a wrapped vanilla function may live here (lua-platform rule #0943).
NutritionRevamp = {
    version = "1.0.0",
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

-- The item-pass sentinel (Plan 9 ruling 5), read by both sides' self-reports: the generated pass file's first item,
-- Base.Acorn, is re-based to 109.71 kcal (vanilla's script says 55.0). zombie.scripting.objects.Item keeps its macro
-- fields private and declares no calorie getter (#2679), so the read is a fresh instance through the instanceItem
-- global (LuaManager$GlobalObject.instanceItem(String), #2680) and its zombie.inventory.types.Food.getCalories().
-- Returns "true" or "false", or "unread" when the global, the item or the getter is absent or a call raises.
-- Called once per boot per side, never on a hot path. A regenerated pass file that moves the sentinel moves this
-- number too (testing/tests/test_mod_shipped_docs.py holds the two equal).
NR.itemPassSentinel = { fullType = "Base.Acorn", calories = 109.71 }
function NR.itemPassActive()
    if instanceItem == nil then return "unread" end
    local ok, item = pcall(instanceItem, NR.itemPassSentinel.fullType)
    if not ok or item == nil then return "unread" end
    local okC, present, v = pcall(NR.call, item, "getCalories")
    if not okC or not present or type(v) ~= "number" then return "unread" end
    return tostring(math.abs(v - NR.itemPassSentinel.calories) < 0.01)
end

-- The shared adapter helpers (Plan 10 Task R1): one copy, one failure meaning. worldAge is nil when the
-- clock cannot be read; an adapter whose old copy answered 0 keeps a local wrapper that says so.
function NR.worldAge()
    if getGameTime == nil then return nil end
    local ok, gt = pcall(getGameTime)
    if not ok or gt == nil then return nil end
    local okA, present, age = pcall(NR.call, gt, "getWorldAgeHours")
    if okA and present and NR.finite(age) then return age end
    return nil
end

function NR.finite(x)
    return type(x) == "number" and x == x and x ~= math.huge and x ~= -math.huge
end

function NR.num(o, name, dflt, ...)
    local ok, present, v = pcall(NR.call, o, name, ...)
    if ok and present and NR.finite(v) then return v end
    return dflt
end

function NR.obj(o, name, ...)
    local ok, present, v = pcall(NR.call, o, name, ...)
    if ok and present then return v end
    return nil
end

function NR.flag(o, name, ...)
    local ok, present, v = pcall(NR.call, o, name, ...)
    return ok and present and v == true
end
