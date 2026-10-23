-- NR_Server_Options.lua: the mod's sandbox options, read at event time (#2460): every mod Lua file runs before the
-- operator's values reach SandboxVars, so a read at file scope sees the declared default. No change event exists
-- (#2466), so the options are re-read every slow tick and a change fires NR.server.options.changed.
local NR = NutritionRevamp
local K = NR.kernel
-- nutritionOn is set by NR_Server_Metabolism's precondition check; the option is the operator's, never changed.
-- No option gates the health drains: every lethal state drains toward its target and kills at its death point.
-- The diagnostic, strength, sexSpecific, stimulantRealism, sleep and drain reads fire no changed hook: the steps read
-- them each time. O.strength is rebuilt only when a leaf changed (Rule 6).
-- stimulantRealism selects the kernel's set once (K.acute.useStimulants), so no step branches on the option; a
-- hangover already counting down keeps the length its set gave it.
-- sleepOn: the engine resets an out-of-handler FATIGUE write unless SleepAllowed and SleepNeeded are both true (#2947),
-- so with sleep off the sleep state freezes at rested and the body clock does not run. The test copies the engine's
-- own: off only on a server, so single player reads on; an unreadable option reads true.
-- deathPace and healthCombine: an out-of-
-- range value reads the default. This file sorts before NR_Server_Players (#0850), so the poll runs before the
-- players' minute writes them into K.drain.OPT; the reverse would cost one minute.
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

-- The steps read the polled copy through NR.sleepOn().
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
    -- written only when its option's read changed (K.dials.apply); no hook fires: the steps read the fields.
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

-- Server-gated at event time (no change event exists, #2466).
local function pollDirect()
    if not NR.isServer() then return end
    NR.server.readOptions("poll")
end

if Events ~= nil and Events.EveryOneMinute ~= nil then Events.EveryOneMinute.Add(pollDirect) end
