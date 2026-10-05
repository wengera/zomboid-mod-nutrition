-- TKX_SleepWatch server (Plan 4 sleep gate): what the server sees of a connected player's
-- fatigue across sleep, and the reset signature. The driver arms a window through
-- `globalmoddata.set TKX_SleepWatch arm <seconds>` (global modData table "TKX_SleepWatch", key
-- `arm`, 0 < seconds <= 300). The first online player is sampled EVERY server tick until the
-- wall-clock window ends (an OnTick handler whose first statement is the nil-cheap `state.armed`
-- test; while unarmed the modData key is read only every 30th tick, #1071). Per sample, each hop
-- index-first and under pcall:
--   fat        Stats:get(CharacterStat.FATIGUE) read at the tick (the "before" read)
--   fatUpd     the same stat read by an OnPlayerUpdate handler (the "after" read of one update),
--              the last value that handler saw before this tick; absent when it has not fired
--   dUpd       fatUpd - fat of the previous tick: the change one player update made
--   asleep     isAsleep()
--   resets     a count of ticks whose fat fell by more than 0.1 from the tick before (the reset signature)
-- At the window end the global modData table gets FLAT scalar keys only (#2848): status, samples,
-- windowMs, resets, hist_<field>_<value> (fixed decimals, "." written "_", at most 40 keys per
-- field), first_/last_/min_/max_/n_<field>, absent_<field>, raw_1 .. raw_50.
-- Install-once (#2845): the sentinel TKX_SleepWatch_Installed is a global of its own; the handlers
-- register at file scope behind the nil-checked isServer() test, once, never at a boot event.
local function tkxServer()
    if isServer == nil then return false end
    local ok, s = pcall(isServer)
    return ok and s == true
end

local TABLE = "TKX_SleepWatch"
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

local lastUpd = nil
local prevFat = nil

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
    state.resets = 0
    prevFat = nil
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

local function onPlayerUpdate(p)
    if not state.armed then return end
    local f = stat(p, "FATIGUE")
    if f ~= nil then lastUpd = f end
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
        local fat = stat(p, "FATIGUE")
        record(parts, "fat", fat, 5)
        record(parts, "fatUpd", lastUpd, 5)
        if prevFat ~= nil and type(lastUpd) == "number" then
            record(parts, "dUpd", lastUpd - prevFat, 5)
        end
        if prevFat ~= nil and type(fat) == "number" and prevFat - fat > 0.1 then
            state.resets = state.resets + 1
            parts[#parts + 1] = "RESET"
        end
        record(parts, "asleep", hop(p, "isAsleep"), 0)
        prevFat = fat
        if state.count <= 50 then state.raw[state.count] = table.concat(parts, " ") end
    end
    if now >= state.deadline then
        local t = ModData.getOrCreate(TABLE)
        t["resets"] = state.resets
        finish(t)
    end
end

if tkxServer() and TKX_SleepWatch_Installed == nil then
    TKX_SleepWatch_Installed = true
    if Events ~= nil and Events.OnTick ~= nil then
        Events.OnTick.Add(onTick)
    end
    if Events ~= nil and Events.OnPlayerUpdate ~= nil then
        Events.OnPlayerUpdate.Add(onPlayerUpdate)
    end
end
