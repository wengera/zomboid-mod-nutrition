-- NR_Server_Options.lua -- the mod's sandbox options, read at event time (sandbox-options rule
-- #2460): every mod Lua file runs before the operator's values reach SandboxVars, so a read at
-- file scope sees the declared default. No change event exists (#2466), so the options are
-- re-read every slow tick and a change fires NR.server.options.changed.
local NR = NutritionRevamp
-- nutritionOn: true when SandboxVars.Nutrition read anything but false at boot (NR_Server_Metabolism's
-- precondition check sets it; the option is the operator's and is never changed by the mod).
-- The Plan 4 dials (ruling 16): onsetSpeed multiplies the rate of every slow deficiency record (ruling 5);
-- the HUNGER and THIRST views are capped under level 4 whatever the dial (Plan 5 ruling 14); deficienciesCanKill gates the mod's own drains; excessEffectsOn off
-- forces every excess rung to 0 at the output; balanceBonus is Plan 3's 1.05 while allReplete (spec
-- ruling 16, a game choice). Read at every slow tick like the three above, never at file scope.
-- The Plan 5 dial (ruling 23): severity, a double 0-3 (default 1), scales every penalty row of the effects table
-- after the fold (NR_Server_Effects); the double branch clamps it.
-- The Plan 7 option (ruling 3): visibilityMode, an enum 1 Symptoms, 2 Bands, 3 Numbers (default 2, T13-1), the level of
-- detail every player's interface shows; the client reads its own SandboxVars copy (Task 5) and this server read is
-- the diagnostic copy. It changes no simulation, so it fires no changed hook.
-- The Plan 11 option (Decision 3, ruling 8): recordKeepDays, an integer 0-3650 (default 30), the REAL days an offline
-- player's record is kept (NR_Server_Store's prune reads it at call time, so it fires no changed hook); 0 keeps all.
NR.server.options = { mode = 1, logLevel = 2, legacyMirror = true, readAt = "default", changed = {},
                      nutritionOn = false, onsetSpeed = 1.0, deficienciesCanKill = true,
                      excessEffectsOn = true, balanceBonus = true, severity = 1.0, visibilityMode = 2,
                      recordKeepDays = 30 }
local O = NR.server.options

local MODE_NAMES = { "takeover", "overlay" }

-- A number leaf in [lo, hi], or a boolean leaf when the default is a boolean; any other value reads
-- the default. A non-number or NaN reads the default; an out-of-range number reads the default, or with
-- clampIt (the double branch: a double option's value is continuous, so its nearest bound is the
-- operator's intent) is clamped to [lo, hi].
local function readLeaf(tbl, key, default, lo, hi, clampIt)
    if tbl == nil then return default end
    local v = tbl[key]
    if type(default) == "boolean" then
        if type(v) == "boolean" then return v end
        return default
    end
    if type(v) ~= "number" or v ~= v then return default end
    if clampIt then return math.max(lo, math.min(hi, v)) end
    if v < lo or v > hi then return default end
    return v
end

function NR.server.readOptions(where)
    local sv = SandboxVars and SandboxVars.NR or nil
    local oldMode, oldLog, oldMirror = O.mode, O.logLevel, O.legacyMirror
    local oldOnset, oldKill, oldExcess, oldBonus = O.onsetSpeed, O.deficienciesCanKill, O.excessEffectsOn, O.balanceBonus
    local oldSeverity = O.severity
    O.mode = readLeaf(sv, "Mode", 1, 1, 2)
    O.logLevel = readLeaf(sv, "LogLevel", 2, 1, 3)
    O.legacyMirror = readLeaf(sv, "LegacyMirror", true)
    O.onsetSpeed = readLeaf(sv, "OnsetSpeed", 1.0, 0.5, 30, true)
    O.deficienciesCanKill = readLeaf(sv, "DeficienciesCanKill", true)
    O.excessEffectsOn = readLeaf(sv, "ExcessEffectsOn", true)
    O.balanceBonus = readLeaf(sv, "BalanceBonus", true)
    O.severity = readLeaf(sv, "Severity", 1.0, 0, 3, true)
    O.visibilityMode = readLeaf(sv, "VisibilityMode", 2, 1, 3)
    O.recordKeepDays = readLeaf(sv, "RecordKeepDays", 30, 0, 3650)
    O.readAt = where or "poll"
    NR.log.level = O.logLevel
    if oldMode ~= O.mode or oldLog ~= O.logLevel or oldMirror ~= O.legacyMirror or oldOnset ~= O.onsetSpeed
        or oldKill ~= O.deficienciesCanKill or oldExcess ~= O.excessEffectsOn or oldBonus ~= O.balanceBonus
        or oldSeverity ~= O.severity then
        for i = 1, #O.changed do
            local ok, err = pcall(O.changed[i], { mode = oldMode, logLevel = oldLog, legacyMirror = oldMirror,
                                                  onsetSpeed = oldOnset, deficienciesCanKill = oldKill,
                                                  excessEffectsOn = oldExcess, balanceBonus = oldBonus,
                                                  severity = oldSeverity }, O)
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
        .. " mode=" .. NR.modeName(O.mode) .. " itemPass=" .. tostring(NR.itemPassActive ~= nil and NR.itemPassActive() or "unread") .. " legacyMirror=" .. (O.legacyMirror and "on" or "off") .. " frameworks=n/a" .. " hook=" .. tostring(NR.server.fast ~= nil and NR.server.fast.registered) .. " limitations=" .. tostring(NR.server.fast and #NR.server.fast.limitations or 0) .. " nutritionOn=" .. tostring(O.nutritionOn == true) .. " log=" .. tostring(O.logLevel)
end

if Events ~= nil and Events.OnServerStarted ~= nil then
    Events.OnServerStarted.Add(function()
        if not NR.isServer() then return end
        NR.server.readOptions("OnServerStarted")
        NR.log.say(1, NR.selfReport("server"))
    end)
end

-- The poll rides EveryOneMinute directly, server-gated at event time (no change event exists, #2466).
local function pollDirect()
    if not NR.isServer() then return end
    NR.server.readOptions("poll")
end

if Events ~= nil and Events.EveryOneMinute ~= nil then Events.EveryOneMinute.Add(pollDirect) end
