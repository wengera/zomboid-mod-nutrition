-- TKX_EatHook -- interception point 2: ISEatFoodAction.complete, wrapped on the SERVER.
--  * In MP a client never runs complete(); the server does, inside NetTimedAction.perform
--    (docs/vanilla/eating-pipeline.md, MP behaviour). So a mod that wants the food item BEFORE
--    IsoGameCharacter.Eat consumes it has to sit here, not in the client's action.
--  * KEEP 4 shape: sentinel-guarded, save-and-call. The sentinel is the wrapper itself, so a
--    `reloadlua` re-running this file does NOT wrap the wrapper, and the saved `_orig` keeps
--    the chain intact when another mod wrapped it first.
--  * The install is retried on the boot events because ISEatFoodAction is a vanilla client/
--    file: whether it is even DEFINED in the server VM, and when, is one of the readings.
--    `wrapped` / `wrapAt` are set at runtime rather than declared in the shared literal.
--
-- Own six-line guard; the harness's TK is never referenced.
local function tkxCall(obj, name, ...)
    if obj == nil then return false, nil end
    local m = obj[name]
    if m == nil then return false, nil end
    return pcall(m, obj, ...)
end

local function install(where)
    if TKX_EatHook == nil then return false end
    if ISEatFoodAction and ISEatFoodAction.complete ~= TKX_EatHook._wrapper then
        TKX_EatHook._orig = ISEatFoodAction.complete
        TKX_EatHook._wrapper = function(self, ...)
            TKX_EatHook.completes = TKX_EatHook.completes + 1
            TKX_EatHook.order = TKX_EatHook.order .. "complete "
            -- The whole point of sitting here: the item is still intact at this
            -- point, before IsoGameCharacter.Eat consumes it.
            if self ~= nil then
                local okType, full = tkxCall(self.item, "getFullType")
                if okType and full ~= nil then TKX_EatHook.lastComplete = full end
            end
            if TKX_EatHook._orig == nil then return end
            return TKX_EatHook._orig(self, ...)
        end
        ISEatFoodAction.complete = TKX_EatHook._wrapper
        TKX_EatHook.wrapped = true
        TKX_EatHook.wrapAt = where
    end
    return TKX_EatHook.wrapped == true
end

local function installAtBoot() install("boot") end

install("file")

if Events ~= nil and Events.OnServerStarted ~= nil then
    Events.OnServerStarted.Add(installAtBoot)
end
if Events ~= nil and Events.OnGameBoot ~= nil then
    Events.OnGameBoot.Add(installAtBoot)
end
