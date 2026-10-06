-- TKX_StatWatch server (Plan 5 effect channels): what the server sees of a connected player's
-- effect-channel stats tick by tick. The driver arms a window through
-- `globalmoddata.set TKX_StatWatch arm <seconds>` (global modData table "TKX_StatWatch", key
-- `arm`, 0 < seconds <= 300) and, for the X88 arm, `globalmoddata.set TKX_StatWatch delta <x>`
-- BEFORE the arm (x is a number, 0 or absent for none; read once at arm time). The first online
-- player is sampled EVERY server tick until the wall-clock window ends (an OnTick handler whose
-- first statement is the nil-cheap `state.armed` test; while unarmed the modData key is read
-- only every 30th tick, #1071).
-- Per sample, each index-first and under pcall (an unreadable one is written once as
-- absent_<field>, never raised): the CharacterStat values POISON, FOOD_SICKNESS, SICKNESS,
-- PANIC, UNHAPPINESS, BOREDOM, STRESS, TEMPERATURE, FATIGUE, ENDURANCE, INTOXICATION (field names
-- lower-cased), and the thermoregulator core through getBodyDamage():getThermoregulator():
-- getCoreTemperature() (the regulator answers nil off the server and can be nil on it, #3010,
-- so it is recorded as absent_core once).
-- Tag counter: Events.OnPlayerGetDamage (character, tag, amount) is listened to once, at file
-- scope, and while a window is armed counts the tags POISON, SICK, FALLDOWN, BLEEDING, HUNGRY,
-- THIRST and HEAVYLOAD (any other tag lands in dmg_other): `dmg_<TAG>` is the count and
-- `dmgsum_<TAG>` the summed amount.
-- X88 arm: when the window was armed with a nonzero `delta`, after each sample the probe writes
-- PANIC and UNHAPPINESS back as (value read + delta) through Stats:set -- an OUT-OF-HANDLER
-- write on the OnTick event, which runs outside the player update the CalculateStats hook runs
-- inside; whether the next update's takeover keeps or erases it is the reading. The written
-- value is clamped by the stat itself, so a steady delta saturates and the histogram shows the
-- ceiling.
-- At the window end the global modData table gets FLAT scalar keys only (#2848): status, samples,
-- windowMs, deltaUsed (the arm-time delta, which is then cleared), hist_<field>_<value> (at most 16 per field, the rest in hist_<field>_other),
-- first_/last_/min_/max_/n_<field>, absent_<field>, dmg_/dmgsum_<TAG>, raw_1 .. raw_60.
-- Install-once (#2845): the sentinel TKX_StatWatch_Installed is a global of its own; the
-- handlers register at file scope behind the nil-checked isServer() test, once, never at a boot
-- event.
local function tkxServer()
    if isServer == nil then return false end
    local ok, s = pcall(isServer)
    return ok and s == true
end

local TABLE = "TKX_StatWatch"
local MAX_KEYS = 16
local MAX_RAW = 60
local state = { armed = false, idle = 0 }

local STATS = { "POISON", "FOOD_SICKNESS", "SICKNESS", "PANIC", "UNHAPPINESS", "BOREDOM", "STRESS",
                "TEMPERATURE", "FATIGUE", "ENDURANCE", "INTOXICATION" }
local TAGS = { POISON = true, SICK = true, FALLDOWN = true, BLEEDING = true, HUNGRY = true, THIRST = true,
               HEAVYLOAD = true }

-- index-first hop: absent member -> nil, a raise -> nil (never reaches the debugger)
local function hop(obj, name, ...)
    if obj == nil then return nil end
    local f = obj[name]
    if f == nil then return nil end
    local ok, v = pcall(f, obj, ...)
    if not ok then return nil end
    return v
end

local function stat(p, enumName)
    if CharacterStat == nil then return nil end
    local enum = CharacterStat[enumName]
    if enum == nil then return nil end
    return hop(hop(p, "getStats"), "get", enum)
end

local function writeStat(p, enumName, v)
    if CharacterStat == nil then return end
    local enum = CharacterStat[enumName]
    if enum == nil then return end
    hop(hop(p, "getStats"), "set", enum, v)
end

local function fmt(v, dec)
    if type(v) ~= "number" then return tostring(v) end
    return string.format("%." .. dec .. "f", v)
end

local function bumpHist(field, key)
    local h = state.hist
    local k = "hist_" .. field .. "_" .. string.gsub(key, "[%.%-]", "_")
    if h[k] == nil then
        local n = state.keys[field] or 0
        if n >= MAX_KEYS then k = "hist_" .. field .. "_other" else state.keys[field] = n + 1 end
    end
    h[k] = (h[k] or 0) + 1
end

local function track(field, v)
    local s = state.scal[field]
    if s == nil then
        state.scal[field] = { first = v, last = v, min = v, max = v, n = 1 }
        return
    end
    s.last = v
    s.n = s.n + 1
    if v < s.min then s.min = v end
    if v > s.max then s.max = v end
end

local function finish(t)
    for k, v in pairs(state.hist) do t[k] = v end
    for field, s in pairs(state.scal) do
        t["first_" .. field] = s.first
        t["last_" .. field] = s.last
        t["min_" .. field] = s.min
        t["max_" .. field] = s.max
        t["n_" .. field] = s.n
    end
    for field, why in pairs(state.absent) do t["absent_" .. field] = why end
    for tag, n in pairs(state.dmg) do t["dmg_" .. tag] = n end
    for tag, a in pairs(state.dmgsum) do t["dmgsum_" .. tag] = a end
    for i = 1, #state.raw do t["raw_" .. i] = state.raw[i] end
    t["samples"] = state.count
    t["windowMs"] = state.windowMs
    t["deltaUsed"] = state.delta
    t["status"] = "done"
    t["arm"] = 0
    state.armed = false
end

local function arm()
    if ModData == nil then return end
    local t = ModData.getOrCreate(TABLE)
    local secs = tonumber(t["arm"])
    if secs == nil or secs <= 0 then return end
    if secs > 300 then secs = 300 end
    state.armed = true
    state.start = getTimestampMs()
    state.deadline = state.start + secs * 1000
    state.windowMs = secs * 1000
    state.delta = tonumber(t["delta"]) or 0
    t["delta"] = 0
    state.hist, state.scal, state.keys, state.absent, state.raw = {}, {}, {}, {}, {}
    state.dmg, state.dmgsum = {}, {}
    state.count = 0
    t["arm"] = 0
    t["status"] = "armed"
end

local function firstPlayer()
    local players = nil
    if getOnlinePlayers ~= nil then players = getOnlinePlayers() end
    local n = hop(players, "size")
    if n ~= nil and n > 0 then return hop(players, "get", 0) end
    return nil
end

-- Records one field of one sample: a number goes to the histogram and the scalar tracker, an
-- unreadable getter is written once as absent_<field> and never raised.
local function record(parts, field, v, dec)
    if type(v) == "number" then
        parts[#parts + 1] = field .. "=" .. fmt(v, dec)
        bumpHist(field, fmt(v, dec))
        track(field, v)
    else
        parts[#parts + 1] = field .. "=unreadable"
        state.absent[field] = "absent"
    end
end

local function onTick()
    if not state.armed then
        state.idle = state.idle + 1
        if state.idle < 30 then return end
        state.idle = 0
        arm()
        return
    end
    local now = getTimestampMs()
    local p = firstPlayer()
    if p ~= nil then
        state.count = state.count + 1
        local parts = { "t=" .. tostring(now - state.start) }
        for i = 1, #STATS do
            local name = STATS[i]
            local dec = 3
            if name == "TEMPERATURE" then dec = 2 end
            record(parts, string.lower(name), stat(p, name), dec)
        end
        local th = hop(hop(p, "getBodyDamage"), "getThermoregulator")
        record(parts, "core", hop(th, "getCoreTemperature"), 2)
        if state.count <= MAX_RAW then state.raw[state.count] = table.concat(parts, " ") end
        if state.delta ~= 0 then
            local panic, unh = stat(p, "PANIC"), stat(p, "UNHAPPINESS")
            if panic ~= nil then writeStat(p, "PANIC", panic + state.delta) end
            if unh ~= nil then writeStat(p, "UNHAPPINESS", unh + state.delta) end
        end
    end
    if now >= state.deadline then
        finish(ModData.getOrCreate(TABLE))
    end
end

-- The tag counter. The first statement of the listener is the nil-cheap armed test, so an
-- unarmed server pays one table read per fired tag.
local function onDamage(character, tag, amount)
    if not state.armed then return end
    local t = tostring(tag)
    if not TAGS[t] then t = "other" end
    state.dmg[t] = (state.dmg[t] or 0) + 1
    if type(amount) == "number" then state.dmgsum[t] = (state.dmgsum[t] or 0) + amount end
end

if tkxServer() and TKX_StatWatch_Installed == nil then
    TKX_StatWatch_Installed = true
    if Events ~= nil and Events.OnTick ~= nil then
        Events.OnTick.Add(onTick)
    end
    if Events ~= nil and Events.OnPlayerGetDamage ~= nil then
        Events.OnPlayerGetDamage.Add(onDamage)
    end
end

-- ---- Plan 5 Task 4 (gate 2): the hold arm and the band arm ------------------------------------
-- HOLD (X82, X83): `globalmoddata.set TKX_StatWatch holdFatigue <v>` and/or `... holdIntox <v>`
-- (a negative value or absent = leave that stat alone), `... holdMode handler|tick`, then
-- `... hold <seconds>` (0 < seconds <= 300) arms a hold window, independent of the sampling window.
-- handler: the probe wraps NutritionRevamp.kernel.fast.step -- the call the takeover handler makes
--   inside Hook.CalculateStats every update, after BodyDamage.Update and after the server's fatigue
--   reset -- and after the original returns it sets out.fatigue = holdFatigue (the handler then
--   writes FATIGUE from it) and writes INTOXICATION = holdIntox through Stats:set on the first
--   online player, so both writes sit in the handler path. The wrap is installed once, at the
--   first handler-mode arm, and passes through untouched while no hold is armed; the additions run
--   under pcall so a fault never reaches the handler's rim guard. The original's own raise is not
--   caught (the handler's behaviour unchanged).
-- tick: the same two writes on this file's OnTick, outside the player update (the X88 seat).
-- At the window end the table gets holdStatus=done, holdCalls (handler calls or ticks that wrote),
-- holdWrapped (true when the wrap stands), holdMissing (why a write could not be made), and hold=0.
-- BAND (X4b): `... bandW <kg>` makes the next poll set the first online player's weight with
-- getNutrition():setWeight(kg) and call applyTraitFromWeight() in the SAME tick (the mod's weight
-- minute cannot run between them), then write band_req, band_weight (read back), band_traits
-- (getKnownTraits names, comma-joined), band_wall and band_status=done, and bandW=0.
-- The keys are read every 10th tick while nothing is armed.
local hold = { armed = false, idle = 0, wrapped = false, calls = 0, missing = "" }

local function holdNum(t, key)
    local v = tonumber(t[key])
    if v == nil or v < 0 then return nil end
    return v
end

local function holdWrites(p)
    if hold.fatigueOnTick ~= nil then writeStat(p, "FATIGUE", hold.fatigueOnTick) end
    if hold.intox ~= nil then writeStat(p, "INTOXICATION", hold.intox) end
end

local function holdFinish()
    local t = ModData.getOrCreate(TABLE)
    t["holdStatus"] = "done"
    t["holdCalls"] = hold.calls
    t["holdWrapped"] = hold.wrapped
    t["holdMissing"] = hold.missing
    t["hold"] = 0
    hold.armed = false
end

local function holdInHandler(out)
    if hold.fatigue ~= nil then out.fatigue = hold.fatigue end
    if hold.intox ~= nil then
        local p = firstPlayer()
        if p ~= nil then writeStat(p, "INTOXICATION", hold.intox) end
    end
    hold.calls = hold.calls + 1
end

local function holdWrap()
    if hold.wrapped then return true end
    local NR = NutritionRevamp
    if NR == nil or NR.kernel == nil or NR.kernel.fast == nil or NR.kernel.fast.step == nil then
        hold.missing = "no NutritionRevamp.kernel.fast.step"
        return false
    end
    local fast = NR.kernel.fast
    local orig = fast.step
    fast.step = function(inp, out, c)
        orig(inp, out, c)
        if hold.armed and hold.mode == "handler" then
            pcall(holdInHandler, out)
        end
    end
    hold.wrapped = true
    return true
end

local function holdArm(t)
    local secs = tonumber(t["hold"])
    if secs == nil or secs <= 0 then return end
    if secs > 300 then secs = 300 end
    hold.mode = tostring(t["holdMode"] or "handler")
    hold.fatigue = holdNum(t, "holdFatigue")
    hold.intox = holdNum(t, "holdIntox")
    hold.fatigueOnTick = nil
    if hold.mode == "tick" then hold.fatigueOnTick = hold.fatigue end
    hold.calls = 0
    hold.missing = ""
    t["hold"] = 0
    if hold.mode == "handler" and not holdWrap() then
        t["holdStatus"] = "failed"
        t["holdMissing"] = hold.missing
        return
    end
    hold.deadline = getTimestampMs() + secs * 1000
    hold.armed = true
    t["holdStatus"] = "armed"
    t["holdModeUsed"] = hold.mode
end

local function bandRun(t)
    local w = tonumber(t["bandW"])
    if w == nil or w <= 0 then return end
    t["bandW"] = 0
    t["band_req"] = w
    local p = firstPlayer()
    local nu = hop(p, "getNutrition")
    if nu == nil then
        t["band_status"] = "no player or no getNutrition"
        return
    end
    hop(nu, "setWeight", w)
    hop(nu, "applyTraitFromWeight")
    t["band_weight"] = hop(nu, "getWeight")
    local names = {}
    local known = hop(hop(p, "getCharacterTraits"), "getKnownTraits")
    local n = hop(known, "size")
    local i = 0
    while n ~= nil and i < n do
        local tr = hop(known, "get", i)
        names[#names + 1] = tostring(hop(tr, "getName"))
        i = i + 1
    end
    t["band_traits"] = table.concat(names, ",")
    t["band_wall"] = getTimestampMs()
    t["band_status"] = "done"
end

local function onHoldTick()
    if hold.armed then
        if hold.mode == "tick" then
            local p = firstPlayer()
            if p ~= nil then
                holdWrites(p)
                hold.calls = hold.calls + 1
            end
        end
        if getTimestampMs() >= hold.deadline then holdFinish() end
        return
    end
    hold.idle = hold.idle + 1
    if hold.idle < 10 then return end
    hold.idle = 0
    if ModData == nil then return end
    local t = ModData.getOrCreate(TABLE)
    bandRun(t)
    holdArm(t)
end

if tkxServer() and TKX_StatWatch_HoldInstalled == nil then
    TKX_StatWatch_HoldInstalled = true
    if Events ~= nil and Events.OnTick ~= nil then
        Events.OnTick.Add(onHoldTick)
    end
end
