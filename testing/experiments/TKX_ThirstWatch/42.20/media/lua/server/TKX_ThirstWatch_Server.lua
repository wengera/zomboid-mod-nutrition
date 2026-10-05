-- TKX_ThirstWatch server (Plan 4 water gate): what the server sees of a connected player's
-- thirst and the thermoregulator state that feeds it. The driver arms a window through
-- `globalmoddata.set TKX_ThirstWatch arm <seconds>` (global modData table "TKX_ThirstWatch", key
-- `arm`, 0 < seconds <= 300). The first online player is sampled EVERY server tick until the
-- wall-clock window ends (per-tick samples are the measurement, so this is an OnTick handler;
-- #1071 prices OnTick as the expensive tier, so the first statement is the nil-cheap
-- `state.armed` test and, while unarmed, the modData key is read only every 30th tick). Per
-- sample, each hop index-first and under pcall (#0935, the raising-probe rule):
--   thirst       Stats:get(CharacterStat.THIRST)
--   fluidsMult   getBodyDamage():getThermoregulator():getFluidsMultiplier()
--   core         ...:getCoreTemperature()
--   extAir       ...:getExternalAirTemperature()
--   bodyFluids   getBodyFluids() on the BodyDamage, else on the Thermoregulator
--   wetness      Stats:get(CharacterStat.WETNESS)
-- A getter the build does not answer is written once as absent_<field> = "absent", never raised.
-- At the window end the global modData table gets FLAT scalar keys only (#2848):
--   status ("armed" | "done"), samples, windowMs,
--   hist_<field>_<value>   a count per value (fixed decimals, "." written "_", at most 40 keys per field, the rest in hist_<field>_other),
--   first_/last_/min_/max_/n_<field>   full-precision scalars per numeric field,
--   raw_1 .. raw_50        the first 50 samples as "t=<ms> field=value ...".
-- Install-once (#2845): the sentinel TKX_ThirstWatch_Installed is a global of its own; the
-- handler registers at file scope behind the nil-checked isServer() test, once, never at a boot event.
local function tkxServer()
    if isServer == nil then return false end
    local ok, s = pcall(isServer)
    return ok and s == true
end

local TABLE = "TKX_ThirstWatch"
local MAX_KEYS = 40
local state = { armed = false, idle = 0 }

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

local function thermo(p) return hop(hop(p, "getBodyDamage"), "getThermoregulator") end

local function bodyFluids(p)
    local v = hop(hop(p, "getBodyDamage"), "getBodyFluids")
    if v == nil then v = hop(thermo(p), "getBodyFluids") end
    return v
end

local function fmt(v, dec)
    if type(v) ~= "number" then return tostring(v) end
    return string.format("%." .. dec .. "f", v)
end

local function bumpHist(field, key)
    local h = state.hist
    local k = "hist_" .. field .. "_" .. string.gsub(key, "[%.]", "_")
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
    for i = 1, #state.raw do t["raw_" .. i] = state.raw[i] end
    t["samples"] = state.count
    t["windowMs"] = state.windowMs
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
    state.hist, state.scal, state.keys, state.absent, state.raw = {}, {}, {}, {}, {}
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
    elseif type(v) == "boolean" then
        parts[#parts + 1] = field .. "=" .. tostring(v)
        bumpHist(field, tostring(v))
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
        local th = thermo(p)
        record(parts, "thirst", stat(p, "THIRST"), 5)
        record(parts, "fluidsMult", hop(th, "getFluidsMultiplier"), 4)
        record(parts, "core", hop(th, "getCoreTemperature"), 3)
        record(parts, "extAir", hop(th, "getExternalAirTemperature"), 2)
        record(parts, "bodyFluids", bodyFluids(p), 4)
        record(parts, "wetness", stat(p, "WETNESS"), 3)
        if state.count <= 50 then state.raw[state.count] = table.concat(parts, " ") end
    end
    if now >= state.deadline then
        finish(ModData.getOrCreate(TABLE))
    end
end

if tkxServer() and TKX_ThirstWatch_Installed == nil then
    TKX_ThirstWatch_Installed = true
    if Events ~= nil and Events.OnTick ~= nil then
        Events.OnTick.Add(onTick)
    end
end
