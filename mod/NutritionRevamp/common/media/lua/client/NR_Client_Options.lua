-- NR_Client_Options.lua -- the client reads the same options after the join sync has landed
-- (OnGameStart, #2446) for its log level, and prints the self-report once.
local NR = NutritionRevamp
NR.client.options = { mode = 1, logLevel = 2 }

if Events ~= nil and Events.OnGameStart ~= nil then
    Events.OnGameStart.Add(function()
        if not NR.isClient() then return end
        local sv = SandboxVars and SandboxVars.NR or nil
        if sv ~= nil then
            if type(sv.Mode) == "number" then NR.client.options.mode = sv.Mode end
            if type(sv.LogLevel) == "number" then NR.client.options.logLevel = sv.LogLevel end
        end
        NR.log.level = NR.client.options.logLevel
        print("[NutritionRevamp] NutritionRevamp v" .. NR.version .. " build " .. NR.build
              .. " side=client mode=" .. tostring(NR.client.options.mode)
              .. " log=" .. tostring(NR.client.options.logLevel) .. " frameworks=none")
    end)
end
