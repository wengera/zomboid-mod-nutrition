-- TKX_DrinkHook server twin (X13): wraps ISDrinkFluidAction.updateEat and .complete in this
-- Lua state and, when isServer() is true, bumps TKX_DrinkHook.<method> and the global-modData
-- counter TKX_Drink.<method>_server. The sentinel TKX_DrinkHook_Installed is held OUTSIDE the
-- re-created TKX_DrinkHook table (the TKX_EatHook shape), so a reload never wraps a wrapper.
-- Install-once rule (#2835): wrapMethod returns at once when the sentinel already holds that
-- method's entry, so the probe never re-wraps at a boot event and never overwrites its saved
-- original (a re-wrap below a later-loaded wrapper forms a call cycle). A mod uses its own
-- class-table guard instead; a probe needs no reload resilience.
-- The saved original is always called.
local function tkxArm()
    if isServer == nil then return false end
    local ok, s = pcall(isServer)
    return ok and s == true
end

local function bump(method)
    if not tkxArm() then return end
    if TKX_DrinkHook ~= nil then TKX_DrinkHook[method] = TKX_DrinkHook[method] + 1 end
    if ModData == nil or ModData.getOrCreate == nil then return end
    local okM, md = pcall(ModData.getOrCreate, "TKX_Drink")
    if okM and md ~= nil then
        local key = method .. "_server"
        md[key] = (md[key] or 0) + 1
    end
end

TKX_DrinkHook_Installed = TKX_DrinkHook_Installed or {}

local function wrapMethod(method)
    local saved = TKX_DrinkHook_Installed
    if saved[method] ~= nil then return end
    if ISDrinkFluidAction == nil then return end
    if ISDrinkFluidAction[method] == nil then return end
    local entry = { orig = ISDrinkFluidAction[method] }
    entry.wrapper = function(self, ...)
        bump(method)
        return entry.orig(self, ...)
    end
    saved[method] = entry
    ISDrinkFluidAction[method] = entry.wrapper
end

local function install()
    wrapMethod("updateEat")
    wrapMethod("complete")
end

install()

if Events ~= nil and Events.OnGameBoot ~= nil then
    Events.OnGameBoot.Add(install)
end
if Events ~= nil and Events.OnServerStarted ~= nil then
    Events.OnServerStarted.Add(install)
end
