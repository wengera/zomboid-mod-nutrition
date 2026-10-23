-- NR_Server_Options.lua -- the mod's sandbox options, read at event time (#2460): every mod Lua file
-- runs before the operator's values reach SandboxVars, so a read at file scope sees the declared default. No change event exists (#2466), so the options are
-- re-read every slow tick and a change fires NR.server.options.changed.
local NR = NutritionRevamp
local K = NR.kernel
-- nutritionOn: true when SandboxVars.Nutrition read anything but false at boot (NR_Server_Metabolism's
-- precondition check sets it; the option is the operator's and is never changed by the mod).
-- onsetSpeed multiplies the rate of every slow deficiency record;
-- the HUNGER and THIRST views are capped under level 4 outside the starvation and dehydration states (K.hybrid.caps) whatever the dial; excessEffectsOn off
-- forces every excess rung to 0 at the output; balanceBonus is a game choice while allReplete.
-- Read at every slow tick, never at file scope. No option gates the
-- health drains: every lethal state drains toward its target and kills at its death point.
-- severity (options.SEVERITY) scales every penalty row of the effects table
-- after the fold (NR_Server_Effects); the double branch clamps it.
-- visibilityMode, an enum 1 Symptoms, 2 Bands, 3 Numbers, is the level of
-- detail every player's interface shows; the client reads its own SandboxVars copy and this server read is
-- the diagnostic copy. It changes no simulation, so it fires no changed hook.
-- The strength options: O.strength is K.strength.params of the NR.Strength* and NR.LeanLoss* leaves
-- (params(nil) until one differs from the default), rebuilt only when a leaf changed since the last read, by one
-- comparison loop over the raw leaves (Rule 6: the table is not rebuilt per minute); a load-guard fallback logs once at
-- level 1 with the three values read. It fires no changed hook: the steps read O.strength each time.
-- sexSpecific, a boolean: off, every character reads the male values wherever the mod
-- indexes by sex (K.body.effSex); the steps read it each minute through the options table, so it fires no changed hook.
-- stimulantRealism, an enum 1 Game, 2 Realistic: the stimulant sizes.
-- A read that finds the kernel's active set on another value selects it once (K.acute.useStimulants), so the next step reads
-- it and no step branches on the option; the effects rebuild key carries the set (NR_Server_Effects), so the hangover
-- rows follow at the next minute; a hangover already counting down keeps the length its set gave it. It fires no changed hook.
-- The sleep poll: sleepOn, the server's SleepAllowed and SleepNeeded both true, read
-- by NR.server.readSleep in every poll (two getBoolean calls and one getServerOptions a server minute, never per
-- player), so an admin's live change takes effect at the next minute (no Lua event fires on a server-option change);
-- the engine resets an out-of-handler FATIGUE write unless both are true (#2947), so with sleep off the sleep
-- state freezes at rested (K.acute.sleepMinute) and the body clock does not run (K.circadian). The test copies the
-- engine's own (IsoGameCharacter.calculateStats gates the reset on GameServer.server): sleep is off only on a server,
-- isServer() and not (allowed and needed), so single player reads on. An unreadable option reads true. A change is
-- logged; it fires no changed hook (the steps read NR.sleepOn() each minute).
-- deathPace, an enum 1 Vanilla, 2 Shortened, 3 Realistic, and
-- healthCombine, an enum 1 Worst only, 2 Multiply, 3 Add; read in every poll like stimulantRealism (an out-of-
-- range value reads the default) and logged on a change. The players' minute writes them into K.drain.OPT with the day
-- length once a server minute (NR_Server_Effects' EFF.writeDrainOptions), so a change takes effect within a game minute
-- (the poll's listener runs first: this file sorts before NR_Server_Players in the execution list, #0850; the reverse
-- would cost one minute); it fires no changed hook.
NR.server.options = { mode = 1, logLevel = 2, legacyMirror = true, readAt = "default", changed = {},
                      nutritionOn = false,
                      onsetSpeed = K.dials.get("options.ONSET_SPEED"),
                      sleepOn = true, excessEffectsOn = true, balanceBonus = true,
                      severity = K.dials.get("options.SEVERITY"),
                      visibilityMode = 2,
                      sexSpecific = false, stimulantRealism = 1, deathPace = K.drain.PACE_REAL,
                      healthCombine = K.drain.COMBINE_MULTIPLY, strength = K.strength.params(nil), dialSeen = {} }
local O = NR.server.options
O.strengthRaw = {} -- the raw strength leaves of the last rebuild, by K.strength.OPTIONS row
O.ONSET_SPEED = K.dials.row("options.ONSET_SPEED") -- OnsetSpeed's row (param): its option, default and range, one source with the option file
O.SEVERITY = K.dials.row("options.SEVERITY") -- Severity's row (param): its option, default and range, one source with the option file

local MODE_NAMES = { "managed", "overlay" }

local readLeaf = K.readLeaf -- the one clamp rule

-- The server's sleep setting (the header): true unless this is a server whose SleepAllowed and SleepNeeded are not
-- both true. Reads the options afresh; the steps read the polled copy through NR.sleepOn().
function NR.server.readSleep()
    if not NR.isServer() then return true end
    local allowed, needed = true, true
    if getServerOptions ~= nil then
        local ok, so = pcall(getServerOptions)
        local okA, a = NR.call(ok and so or nil, "getBoolean", "SleepAllowed")
        if okA and type(a) == "boolean" then allowed = a end
        local okN, n = NR.call(ok and so or nil, "getBoolean", "SleepNeeded")
        if okN and type(n) == "boolean" then needed = n end
    end
    return allowed and needed
end

function NR.server.readOptions(where)
    local sv = SandboxVars and SandboxVars.NR or nil
    local oldMode, oldLog, oldMirror = O.mode, O.logLevel, O.legacyMirror
    local oldOnset, oldExcess, oldBonus = O.onsetSpeed, O.excessEffectsOn, O.balanceBonus
    local oldSeverity = O.severity
    O.mode = readLeaf(sv, "Mode", 1, 1, 2)
    O.logLevel = readLeaf(sv, "LogLevel", 2, 1, 3)
    O.legacyMirror = readLeaf(sv, "LegacyMirror", true)
    O.onsetSpeed = K.dials.readParam(sv, O.ONSET_SPEED, O.ONSET_SPEED.value)
    O.excessEffectsOn = readLeaf(sv, "ExcessEffectsOn", true)
    O.balanceBonus = readLeaf(sv, "BalanceBonus", true)
    O.severity = K.dials.readParam(sv, O.SEVERITY, O.SEVERITY.value)
    O.visibilityMode = readLeaf(sv, "VisibilityMode", 2, 1, 3)
    O.sexSpecific = readLeaf(sv, "SexSpecific", false)
    local oldSleep = O.sleepOn
    O.sleepOn = NR.server.readSleep()
    if O.sleepOn ~= oldSleep or where == "OnServerStarted" then
        NR.log.say(2, "options: sleep " .. (O.sleepOn and "on" or "off")
            .. (O.sleepOn and "" or ": the sleep state freezes at rested and the body clock stops"))
    end
    O.stimulantRealism = readLeaf(sv, "StimulantRealism", 1, 1, 2)
    if O.stimulantRealism ~= K.acute.C.MODE then
        K.acute.useStimulants(O.stimulantRealism)
    end
    local oldPace, oldCombine = O.deathPace, O.healthCombine
    O.deathPace = readLeaf(sv, "DeathPace", K.drain.PACE_REAL, K.drain.PACE_VANILLA, K.drain.PACE_REAL)
    O.healthCombine = readLeaf(sv, "HealthCombine", K.drain.COMBINE_MULTIPLY, K.drain.COMBINE_WORST, K.drain.COMBINE_ADD)
    if O.deathPace ~= oldPace or O.healthCombine ~= oldCombine or where == "OnServerStarted" then
        NR.log.say(2, "options: death pace " .. tostring(O.deathPace) .. ", health combining " .. tostring(O.healthCombine))
    end
    -- Every sandbox-backed tuning dial re-resolves into its kernel field, written only when its
    -- option's read changed against O.dialSeen (K.dials.apply); no hook fires: the steps read the fields.
    K.dials.apply(sv, O.dialSeen)
    if sv ~= nil then
        local rows = K.strength.OPTIONS
        local raw = O.strengthRaw
        local moved = false
        for i = 1, #rows do
            local v = sv[rows[i].opt]
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
