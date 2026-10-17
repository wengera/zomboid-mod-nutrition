-- NR_Server_Options.lua -- the mod's sandbox options, read at event time (sandbox-options rule
-- #2460): every mod Lua file runs before the operator's values reach SandboxVars, so a read at
-- file scope sees the declared default. No change event exists (#2466), so the options are
-- re-read every slow tick and a change fires NR.server.options.changed.
local NR = NutritionRevamp
local K = NR.kernel
-- nutritionOn: true when SandboxVars.Nutrition read anything but false at boot (NR_Server_Metabolism's
-- precondition check sets it; the option is the operator's and is never changed by the mod).
-- The Plan 4 dials: onsetSpeed multiplies the rate of every slow deficiency record;
-- the HUNGER and THIRST views are capped under level 4 outside the starvation and dehydration states (K.hybrid.caps) whatever the dial; excessEffectsOn off
-- forces every excess rung to 0 at the output; balanceBonus is Plan 3's 1.05 while allReplete (spec
-- ruling 16, a game choice). Read at every slow tick like the three above, never at file scope. No option gates the
-- health drains: every lethal state drains to its floor and kills at its death point (Plan 15 Task 4, spec section 1.3).
-- The Plan 4 kill dial is removed (the mod is unreleased, so no save reads it).
-- The Plan 5 dial: severity, a double 0-3 (default 1), scales every penalty row of the effects table
-- after the fold (NR_Server_Effects); the double branch clamps it.
-- The Plan 7 option: visibilityMode, an enum 1 Symptoms, 2 Bands, 3 Numbers (default 2, T13-1), the level of
-- detail every player's interface shows; the client reads its own SandboxVars copy and this server read is
-- the diagnostic copy. It changes no simulation, so it fires no changed hook.
-- The Plan 11 option: recordKeepDays, an integer 0-3650 (default 30), the REAL days an offline
-- player's record is kept (NR_Server_Store's prune reads it at call time, so it fires no changed hook); 0 keeps all.
-- The Plan 13 strength options: O.strength is K.strength.params of the NR.Strength* and NR.LeanLoss* leaves
-- (params(nil) until one differs from the default), rebuilt only when a leaf changed since the last read, by one
-- comparison loop over the raw leaves (Rule 6: the table is not rebuilt per minute); a load-guard fallback logs once at
-- level 1 with the three values read. It fires no changed hook: the steps read O.strength each time.
-- The Plan 13 option: sexSpecific, a boolean (default false): off, every character reads the male values wherever the mod
-- indexes by sex (K.body.effSex); the steps read it each minute through the options table, so it fires no changed hook.
-- The Plan 15 option: stimulantRealism, an enum 1 Game (the default), 2 Realistic: the stimulant sizes (spec section 5).
-- A read that finds the kernel's active set on another value selects it once (K.acute.useStimulants), so the next step reads
-- it and no step branches on the option; the effects rebuild key carries the set (NR_Server_Effects), so the hangover
-- rows follow at the next minute; a hangover already counting down keeps the length its set gave it. It fires no changed hook.
NR.server.options = { mode = 1, logLevel = 2, legacyMirror = true, readAt = "default", changed = {},
                      nutritionOn = false, onsetSpeed = 1.0,
                      excessEffectsOn = true, balanceBonus = true, severity = 1.0, visibilityMode = 2,
                      recordKeepDays = 30, sexSpecific = false, stimulantRealism = 1, strength = K.strength.params(nil) }
local O = NR.server.options
O.strengthRaw = {} -- the raw strength leaves of the last rebuild, by K.strength.OPTIONS row

local MODE_NAMES = { "managed", "overlay" }

local readLeaf = K.readLeaf -- the one clamp rule (ruling 13-32)

function NR.server.readOptions(where)
    local sv = SandboxVars and SandboxVars.NR or nil
    local oldMode, oldLog, oldMirror = O.mode, O.logLevel, O.legacyMirror
    local oldOnset, oldExcess, oldBonus = O.onsetSpeed, O.excessEffectsOn, O.balanceBonus
    local oldSeverity = O.severity
    O.mode = readLeaf(sv, "Mode", 1, 1, 2)
    O.logLevel = readLeaf(sv, "LogLevel", 2, 1, 3)
    O.legacyMirror = readLeaf(sv, "LegacyMirror", true)
    O.onsetSpeed = readLeaf(sv, "OnsetSpeed", 1.0, 0.5, 30, true)
    O.excessEffectsOn = readLeaf(sv, "ExcessEffectsOn", true)
    O.balanceBonus = readLeaf(sv, "BalanceBonus", true)
    O.severity = readLeaf(sv, "Severity", 1.0, 0, 3, true)
    O.visibilityMode = readLeaf(sv, "VisibilityMode", 2, 1, 3)
    O.recordKeepDays = readLeaf(sv, "RecordKeepDays", 30, 0, 3650)
    O.sexSpecific = readLeaf(sv, "SexSpecific", false)
    O.stimulantRealism = readLeaf(sv, "StimulantRealism", 1, 1, 2)
    if O.stimulantRealism ~= K.acute.C.MODE then
        K.acute.useStimulants(O.stimulantRealism)
    end
    if sv ~= nil then
        local rows = K.strength.OPTIONS
        local raw = O.strengthRaw
        local moved = false
        for i = 1, #rows do
            local v = sv[rows[i][1]]
            if raw[i] ~= v and not (v ~= v and raw[i] ~= raw[i]) then
                raw[i] = v
                moved = true
            end
        end
        if moved then
            local P, fellBack = K.strength.params(sv)
            O.strength = P
            if fellBack then
                NR.log.say(1, "options: the strength threshold exceeds the set cap at bio level 15 (StrengthThreshold "
                    .. tostring(sv.StrengthThreshold) .. ", StrengthThresholdRise " .. tostring(sv.StrengthThresholdRise)
                    .. ", StrengthTrainedSetCap " .. tostring(sv.StrengthTrainedSetCap) .. "): the three revert to their defaults")
            end
        end
    end
    O.readAt = where or "poll"
    NR.log.level = O.logLevel
    if oldMode ~= O.mode or oldLog ~= O.logLevel or oldMirror ~= O.legacyMirror or oldOnset ~= O.onsetSpeed
        or oldExcess ~= O.excessEffectsOn or oldBonus ~= O.balanceBonus
        or oldSeverity ~= O.severity then
        for i = 1, #O.changed do
            local ok, err = pcall(O.changed[i], { mode = oldMode, logLevel = oldLog, legacyMirror = oldMirror,
                                                  onsetSpeed = oldOnset,
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
        .. " mode=" .. NR.modeName(NR.runningMode()) .. " itemPass=" .. tostring(NR.itemPassActive ~= nil and NR.itemPassActive() or "unread") .. " legacyMirror=" .. (O.legacyMirror and "on" or "off") .. " frameworks=n/a" .. " rates=" .. ((NR.server.writer ~= nil and NR.server.writer.zeroed) and "zeroed" or "vanilla") .. " limitations=" .. tostring(NR.server.writer and #NR.server.writer.limitations or 0) .. " nutritionOn=" .. tostring(O.nutritionOn == true) .. " log=" .. tostring(O.logLevel)
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
