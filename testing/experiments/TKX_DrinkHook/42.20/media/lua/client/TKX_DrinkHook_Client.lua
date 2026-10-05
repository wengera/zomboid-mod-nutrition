-- TKX_DrinkHook client twin (X13): wraps ISDrinkFluidAction.updateEat and .complete in this
-- Lua state and, when isClient() is true, bumps TKX_DrinkHook.<method> and the global-modData
-- counter TKX_Drink.<method>_client. The sentinel TKX_DrinkHook_Installed is held OUTSIDE the
-- re-created TKX_DrinkHook table (the TKX_EatHook shape), so a reload never wraps a wrapper.
-- The saved original is always called.
local function tkxArm()
    if isClient == nil then return false end
    local ok, s = pcall(isClient)
    return ok and s == true
end

local function bump(method)
    if not tkxArm() then return end
    if TKX_DrinkHook ~= nil then TKX_DrinkHook[method] = TKX_DrinkHook[method] + 1 end
    if ModData == nil or ModData.getOrCreate == nil then return end
    local okM, md = pcall(ModData.getOrCreate, "TKX_Drink")
    if okM and md ~= nil then
        local key = method .. "_client"
        md[key] = (md[key] or 0) + 1
    end
end

TKX_DrinkHook_Installed = TKX_DrinkHook_Installed or {}

local function wrapMethod(method)
    local saved = TKX_DrinkHook_Installed
    if ISDrinkFluidAction == nil then return end
    if ISDrinkFluidAction[method] == nil then return end
    if saved[method] ~= nil and ISDrinkFluidAction[method] == saved[method].wrapper then return end
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
