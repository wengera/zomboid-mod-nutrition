-- NR_Server_Options.lua -- the mod's sandbox options, read at event time (sandbox-options rule
-- #2460): every mod Lua file runs before the operator's values reach SandboxVars, so a read at
-- file scope sees the declared default. No change event exists (#2466), so the options are
-- re-read every slow tick and a change fires NR.server.options.changed.
local NR = NutritionRevamp
NR.server.options = { mode = 1, logLevel = 2, readAt = "default", changed = {} }
local O = NR.server.options

local MODE_NAMES = { "takeover", "overlay" }

local function readLeaf(tbl, key, default, lo, hi)
    if tbl == nil then return default end
    local v = tbl[key]
    if type(v) ~= "number" then return default end
    if v < lo or v > hi then return default end
    return v
end

function NR.server.readOptions(where)
    local sv = SandboxVars and SandboxVars.NR or nil
    local oldMode, oldLog = O.mode, O.logLevel
    O.mode = readLeaf(sv, "Mode", 1, 1, 2)
    O.logLevel = readLeaf(sv, "LogLevel", 2, 1, 3)
    O.readAt = where or "poll"
    NR.log.level = O.logLevel
    if oldMode ~= O.mode or oldLog ~= O.logLevel then
        for i = 1, #O.changed do
            local ok, err = pcall(O.changed[i], { mode = oldMode, logLevel = oldLog }, O)
            if not ok then NR.log.say(2, "options: changed hook failed: " .. tostring(err)) end
        end
    end
    return O
end

function NR.modeName(mode)
    return MODE_NAMES[mode] or ("mode" .. tostring(mode))
end

function NR.selfReport(side)
    return "NutritionRevamp v" .. NR.version .. " build " .. NR.build .. " side=" .. tostring(side)
        .. " mode=" .. NR.modeName(O.mode) .. " log=" .. tostring(O.logLevel) .. " frameworks=none"
end

if Events ~= nil and Events.OnServerStarted ~= nil then
    Events.OnServerStarted.Add(function()
        if not NR.isServer() then return end
        NR.server.readOptions("OnServerStarted")
        NR.log.say(1, NR.selfReport("server"))
    end)
end

-- The poll rides the slow clock. When the players adapter has loaded its onMinute list, the
-- poll is appended to it and keyed off the first queued player of each minute by comparing the
-- minute counter. When that list is absent at load (this file loads before NR_Server_Players
-- by name), the poll registers on EveryOneMinute directly, server-gated at event time.
local lastMinute = -1
local function pollFromPlayers()
    local p = NR.server.players
    if p ~= nil and p.minutes ~= lastMinute then
        lastMinute = p.minutes
        NR.server.readOptions("poll")
    end
end

local function pollDirect()
    if not NR.isServer() then return end
    NR.server.readOptions("poll")
end

if NR.server.players ~= nil and NR.server.players.onMinute ~= nil then
    NR.server.players.onMinute[#NR.server.players.onMinute + 1] = pollFromPlayers
elseif Events ~= nil and Events.EveryOneMinute ~= nil then
    Events.EveryOneMinute.Add(pollDirect)
end
