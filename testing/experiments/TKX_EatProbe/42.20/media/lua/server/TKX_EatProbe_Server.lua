-- TKX_EatProbe server (X45b): wraps ISEatFoodAction.complete on the server, bumping enter
-- before and exit after the saved original, and records ONCE on an OnTick whether the probe's
-- wrapper is still the outermost. The sentinel TKX_EatProbe_Installed is held outside the
-- re-created TKX_EatProbe table (the TKX_EatHook shape).
-- Install-once rule (#2835): install() returns at once when the sentinel's wrapper exists, so the
-- probe never re-wraps at a boot event and never overwrites the global holding its saved original;
-- a re-wrap below a later-loaded wrapper (QualityCooking) forms a call cycle (every eat overflowed
-- in X13). A mod uses its own class-table guard instead; a probe needs no reload resilience.
local function tkxServer()
    if isServer == nil then return false end
    local ok, s = pcall(isServer)
    return ok and s == true
end

TKX_EatProbe_Installed = TKX_EatProbe_Installed or {}

local function install()
    if TKX_EatProbe_Installed.wrapper ~= nil then return end
    if not tkxServer() then return end
    if ISEatFoodAction == nil then return end
    if ISEatFoodAction.complete == nil then return end
    TKX_EatProbe_Installed.orig = ISEatFoodAction.complete
    TKX_EatProbe_Installed.wrapper = function(self, ...)
        if TKX_EatProbe ~= nil then TKX_EatProbe.enter = TKX_EatProbe.enter + 1 end
        local r = TKX_EatProbe_Installed.orig(self, ...)
        if TKX_EatProbe ~= nil then TKX_EatProbe.exit = TKX_EatProbe.exit + 1 end
        return r
    end
    ISEatFoodAction.complete = TKX_EatProbe_Installed.wrapper
end

install()

if Events ~= nil and Events.OnGameBoot ~= nil then
    Events.OnGameBoot.Add(install)
end
if Events ~= nil and Events.OnServerStarted ~= nil then
    Events.OnServerStarted.Add(install)
end

local recorded = false
local function recordOnce()
    if recorded then return end
    if not tkxServer() then return end
    if TKX_EatProbe == nil or ISEatFoodAction == nil then return end
    recorded = true
    TKX_EatProbe.outermost = (ISEatFoodAction.complete == TKX_EatProbe_Installed.wrapper)
end

if Events ~= nil and Events.OnTick ~= nil then
    Events.OnTick.Add(recordOnce)
end
