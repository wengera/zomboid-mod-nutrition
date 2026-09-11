-- TKX_EatHook -- interception point 2: ISEatFoodAction.complete, wrapped on the SERVER.
--  * In MP a client never runs complete(); the server does, inside NetTimedAction.perform
--    (docs/vanilla/eating-pipeline.md, MP behaviour). So a mod that wants the food item BEFORE
--    IsoGameCharacter.Eat consumes it has to sit here, not in the client's action.
--  * KEEP 4 shape: sentinel-guarded, save-and-call -- but the sentinel is held OUTSIDE the
--    mod's state table, in the global TKX_EatHook_Installed, because TKX_EatHook.lua ~:19
--    re-creates TKX_EatHook by plain assignment on every load. A sentinel kept inside that
--    table would be wiped by a `reloadlua` of the shared file while ISEatFoodAction.complete
--    still held the old wrapper, and the next install would wrap the wrapper (double
--    `completes`). Held outside, the install is idempotent in BOTH senses: within a boot
--    (file scope, OnServerStarted and OnGameBoot all call install, only the first wraps) AND
--    across a `reloadlua` of either file in either order -- complete() ends up carrying
--    exactly one of our wrappers per VM, ever. `TKX_EatHook_Installed.orig` is saved at that
--    one wrap and keeps the chain intact when another mod wrapped complete() first.
--  * The install is retried on the boot events because ISEatFoodAction is a vanilla
--    shared/TimedActions/ file, present in both VMs; the retry covers load order only -- WHEN
--    this VM has the class, not WHETHER (media/lua/shared/TimedActions/ISEatFoodAction.lua is
--    the install's only copy of it, so the server VM defines it too).
--    `wrapped` / `wrapAt` are set at runtime rather than declared in the shared literal.
--
-- Own six-line guard; the harness's TK is never referenced.
local function tkxCall(obj, name, ...)
    if obj == nil then return false, nil end
    local m = obj[name]
    if m == nil then return false, nil end
    return pcall(m, obj, ...)
end

-- The sentinel table, and nothing else, survives a reload: `or {}` keeps the existing one when
-- THIS file is re-run, and TKX_EatHook.lua's plain-assignment reset never touches it.
TKX_EatHook_Installed = TKX_EatHook_Installed or {}

local function install(where)
    if TKX_EatHook == nil then return false end
    if ISEatFoodAction ~= nil and ISEatFoodAction.complete ~= TKX_EatHook_Installed.wrapper then
        TKX_EatHook_Installed.orig = ISEatFoodAction.complete
        TKX_EatHook_Installed.wrapper = function(self, ...)
            -- The counters live on TKX_EatHook because that is what `lua.global` reads, so a
            -- reload of the shared file resets them under a wrapper that is still installed.
            -- Guard rather than return, so the saved chain below still runs in that window.
            if TKX_EatHook ~= nil then
                TKX_EatHook.completes = TKX_EatHook.completes + 1
                TKX_EatHook.order = TKX_EatHook.order .. "complete "
                -- The whole point of sitting here: the item is still intact at this
                -- point, before IsoGameCharacter.Eat consumes it.
                if self ~= nil then
                    local okType, full = tkxCall(self.item, "getFullType")
                    if okType and full ~= nil then TKX_EatHook.lastComplete = full end
                end
            end
            if TKX_EatHook_Installed.orig == nil then return end
            return TKX_EatHook_Installed.orig(self, ...)
        end
        ISEatFoodAction.complete = TKX_EatHook_Installed.wrapper
        TKX_EatHook_Installed.wrapAt = where
    end
    -- Mirrored on EVERY call, not only the wrapping one: after a reload of the shared file the
    -- counters are fresh but the wrapper is still in place, and `wrapped` has to read true or
    -- the run would score a live hook as "never installed".
    TKX_EatHook.wrapped = TKX_EatHook_Installed.wrapper ~= nil
    TKX_EatHook.wrapAt = TKX_EatHook_Installed.wrapAt
    return TKX_EatHook.wrapped
end

local function installAtBoot() install("boot") end

install("file")

if Events ~= nil and Events.OnServerStarted ~= nil then
    Events.OnServerStarted.Add(installAtBoot)
end
if Events ~= nil and Events.OnGameBoot ~= nil then
    Events.OnGameBoot.Add(installAtBoot)
end
