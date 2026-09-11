-- TKX_EatHook -- interception point 1: the script `OnEat` callback.
--  * TKX_OnEatProbe is a GLOBAL function, not a local and not a table member, because
--    `IsoGameCharacter.Eat` resolves the script's `OnEat = <name>` through
--    `LuaManager.getFunctionObject(food.getOnEat())` (@762-@802 L5811-L5814) -- a lookup by
--    name in the global table. A local would simply never be found.
--  * This file is shared/ ON PURPOSE, so BOTH Lua states define the probe. Which side
--    actually runs it is the reading, and `lastSide` plus the per-side character-modData key
--    is how the run tells them apart.
--  * TKX_EatHook is a global for the same reason TKX_Nutrient is: `lua.global` reads it.
--
-- Own six-line guard; the harness's TK is never referenced.
local function tkxCall(obj, name, ...)
    if obj == nil then return false, nil end
    local m = obj[name]
    if m == nil then return false, nil end
    return pcall(m, obj, ...)
end

TKX_EatHook = { version = 1, calls = 0, completes = 0, order = "", lastSide = "?", lastFraction = -1, lastCalories = -1 }

-- isServer/isClient are globals, not Java members, so they take a plain pcall rather than the
-- member guard -- behind the `== nil` pre-check the sibling files use (TKX_Nutrient_Client.lua
-- on getPlayer, TKX_Nutrient_Server.lua on getOnlinePlayers): in Kahlua a call on a nil is
-- uncatchable and escapes the pcall (docs/modding/patterns.md:173), so the pcall alone is not a
-- guard. Same shape as the harness's TK.side, resolved per call because a Lua state can load
-- this file before the side is decided.
local function tkxSide()
    if isServer ~= nil then
        local okS, s = pcall(isServer)
        if okS and s then return "server" end
    end
    if isClient ~= nil then
        local okC, c = pcall(isClient)
        if okC and c then return "client" end
    end
    return "sp"
end

-- Signature is the engine's: (item, character, fraction). `fraction` is what the eat consumed
-- on this call; recording it is how the run learns whether OnEat fires once or per portion.
function TKX_OnEatProbe(item, character, fraction)
    if TKX_EatHook == nil then return end
    local side = tkxSide()
    TKX_EatHook.calls = TKX_EatHook.calls + 1
    TKX_EatHook.order = TKX_EatHook.order .. "onEat "
    TKX_EatHook.lastSide = side
    TKX_EatHook.lastFraction = fraction
    local okNut, nut = tkxCall(character, "getNutrition")
    if okNut and nut ~= nil then
        local okCal, cal = tkxCall(nut, "getCalories")
        if okCal and cal ~= nil then TKX_EatHook.lastCalories = cal end
    end
    -- The KEY's presence is the reading (which side ran the probe); the value is this side's
    -- call count so a census also shows how many times. Never transmitted from here.
    local okMd, md = tkxCall(character, "getModData")
    if okMd and md ~= nil then
        md["TKX_eat_onEat_" .. side] = TKX_EatHook.calls
    end
end
