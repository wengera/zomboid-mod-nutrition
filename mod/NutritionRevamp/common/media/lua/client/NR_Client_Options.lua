-- NR_Client_Options.lua -- the client reads the same options after the join sync has landed
-- (OnGameStart, #2446) for its log level, and prints the self-report once.
-- It MERGES into NR.client.options: NR_Client_ModOptions.lua (earlier in path order) has already attached its
-- accessors there, and a replacement would drop them until OnGameStart.
-- frameworks= names MoodleFramework when the moodle route NR_Client_Moodles.lua's OnGameBoot type test set (#2547) is
-- "framework", else none (read per call, never re-tested here); itemPass= is NR.itemPassActive()'s sentinel read.
local NR = NutritionRevamp
NR.client.options = NR.client.options or {}
NR.client.options.mode = 1
NR.client.options.logLevel = 2

-- The detected framework for the self-report, read per call; "none" when the moodles file or its route is absent.
local function moodleRoute()
    local m = NutritionRevamp.client.moodles
    return (m ~= nil and m.route == "framework") and "MoodleFramework" or "none"
end

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
              .. " side=client mode=" .. (NR.modeName and NR.modeName(NR.client.options.mode) or tostring(NR.client.options.mode))
              .. " itemPass=" .. tostring(NR.itemPassActive ~= nil and NR.itemPassActive() or "unread") .. " frameworks=" .. tostring(moodleRoute()) .. " log=" .. tostring(NR.client.options.logLevel))
    end)
end
