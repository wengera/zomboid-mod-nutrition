-- NR_Client_Options.lua -- the client reads the same options after the join sync has landed
-- (OnGameStart, #2446) for its log level, and prints the self-report once.
-- It MERGES into NR.client.options: NR_Client_ModOptions.lua (earlier in path order) has already attached its
-- accessors there, and a replacement would drop them until OnGameStart.
-- frameworks= names MoodleFramework when the moodle route NR_Client_Moodles.lua's OnGameBoot type test set (#2547) is
-- "framework", else none (read per call, never re-tested here); itemPass= is NR.itemPassActive()'s sentinel read.
-- Shape (the client-file discipline): the sentinel NR_ClientOptions_Installed is a global of its own holding the
-- OnGameStart closure, so a reload of this file adds no second listener; the closure looks NutritionRevamp up per call.
local NR = NutritionRevamp
NR.client.options = NR.client.options or {}
NR.client.options.mode = 1 -- NR.Mode's default, 1 Managed, until OnGameStart reads the option: an option value, no row needed
NR.client.options.logLevel = 2 -- NR.LogLevel's default until OnGameStart reads the option: an option value, no row needed
NR.client.options.dialSeen = {} -- the last value seen of each sandbox-backed dial (K.dials.apply)

NR_ClientOptions_Installed = NR_ClientOptions_Installed or {}

if NR_ClientOptions_Installed.start == nil and Events ~= nil and Events.OnGameStart ~= nil then
    NR_ClientOptions_Installed.start = function()
        local nr = NutritionRevamp
        if not nr.isClient() then return end
        local o = nr.client.options
        local sv = SandboxVars and SandboxVars.NR or nil
        if sv ~= nil then
            if type(sv.Mode) == "number" then o.mode = sv.Mode end
            if type(sv.LogLevel) == "number" then o.logLevel = sv.LogLevel end
        end
        -- Plan 19: the sandbox-backed dials the client reads follow the option as on the server (ruling T1-1)
        nr.kernel.dials.apply(sv, o.dialSeen)
        nr.log.level = o.logLevel
        local m = nr.client.moodles
        local route = (m ~= nil and m.route == "framework") and "MoodleFramework" or "none"
        print("[NutritionRevamp] NutritionRevamp v" .. nr.version .. " build " .. nr.build
              .. " side=client mode=" .. (nr.modeName and nr.modeName(o.mode) or tostring(o.mode))
              .. " itemPass=" .. tostring(nr.itemPassActive ~= nil and nr.itemPassActive() or "unread")
              .. " frameworks=" .. route .. " log=" .. tostring(o.logLevel))
    end
    Events.OnGameStart.Add(NR_ClientOptions_Installed.start)
end
