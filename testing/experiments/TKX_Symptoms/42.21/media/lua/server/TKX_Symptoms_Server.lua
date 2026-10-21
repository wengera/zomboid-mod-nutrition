-- TKX_Symptoms server side (Plan 18 Task 1, the live probe of the levers). TEST-ONLY: installed by the x49 profiles
-- only, never shipped. This file also runs in a client's Lua state, so its event listeners are added only when
-- isServer() answers true (the TKX_TraitLevers shape).
--
-- What it does, all on the dedicated server, for one watched player (TKX_Symptoms.watch(user)):
--   1. HOLDS, re-applied once a game minute on EveryOneMinute, the cadence the mod's own minute writer keeps:
--        pain    <part> <value>  BodyPart:setAdditionalPain(value) on BodyPartType.FromIndex(part), set every minute
--                                whatever it reads (the design's re-set, spec section 2.1);
--        endcap  <cap>           ENDURANCE set to cap when it reads above it (a ceiling, the Overfull row's op);
--        stress  <floor>         STRESS set to floor when it reads below it;
--        unhappy <floor>         UNHAPPINESS set to floor when it reads below it;
--        boredcap <cap>          BOREDOM set to cap when it reads above it (keeps boredom out of the unhappy arms).
--      TKX_Symptoms.hold(user, kind, a, b) arms one (and applies it at once, logged as an "arm" row);
--      TKX_Symptoms.release(kind, a) drops one ("all" drops every hold); TKX_Symptoms.setPain(user, part, value) is
--      a one-shot set with no hold (the relog and restart arms).
--   2. THE MINUTE LOG (TKX_Symptoms.mlog.rows): one row per hold per minute event and per arm: the hold, the value
--      read before the write, the value after, whether it wrote, the world age, the wall ms, and the server ticks and
--      the summed GameTime:getMultiplier() seen by OnTick since the previous minute event (acc), so a row's fall
--      between writes can be set against 0.005 x the multiplier sum (BodyPart.DamageUpdate @2323-@2339 L501).
--   3. THE SNAPSHOT (TKX_Symptoms.s), rewritten every server tick for the watched player: PAIN, the tracked part's
--      added pain, ENDURANCE, STRESS, NICOTINE_WITHDRAWAL, UNHAPPINESS, BOREDOM and the PAIN, ENDURANCE, STRESS and
--      UNHAPPY moodle levels, the multiplier and the tick count; lua.read reads it in one tick. TKX_Symptoms.trk holds
--      each level's minimum and maximum since TKX_Symptoms.trkReset(), so a dip between two driver reads is seen.
--   4. THE TICK RING (TKX_Symptoms.ring), while TKX_Symptoms.ringOn(true): one compact row per tick up to RING_CAP,
--      later ticks counted in ring.dropped.
--   5. TKX_Symptoms.dump(tag) writes {minutes, ticks, counts, holds} through the harness's TK.result as
--      pzt-results/tkxs-<tag>.json (PZTestKit loads first); TKX_Symptoms.reset() empties the log, the ring and the
--      trackers.
-- Every Java member is reached under pcall, so a missing member is a nil reading, never a raise in a handler.
-- Kahlua: no goto, no # on a Java list, no string.format.
TKX_Symptoms = TKX_Symptoms or {}
local T = TKX_Symptoms

T.version = "1"
T.MINUTE_CAP = 2000
T.RING_CAP = 6000

local function onServer()
    if isServer == nil then return false end
    local ok, s = pcall(isServer)
    return ok and s == true
end

local function try(fn)
    local ok, v = pcall(fn)
    if ok then return v end
    return nil
end

local function nowMs()
    if getTimestampMs == nil then return nil end
    return try(function() return getTimestampMs() end)
end

local function worldAge()
    return try(function() return getGameTime():getWorldAgeHours() end)
end

local function multiplier()
    return try(function() return getGameTime():getMultiplier() end)
end

function T.findPlayer(user)
    if user == nil or getOnlinePlayers == nil then return nil end
    local list = try(function() return getOnlinePlayers() end)
    if list == nil then return nil end
    local n = try(function() return list:size() end)
    if type(n) ~= "number" then return nil end
    for i = 0, n - 1 do
        local p = try(function() return list:get(i) end)
        if p ~= nil and try(function() return p:getUsername() end) == user then return p end
    end
    return nil
end

function T.stat(p, name)
    local e = CharacterStat ~= nil and CharacterStat[name] or nil
    if p == nil or e == nil then return nil end
    return try(function() return p:getStats():get(e) end)
end

function T.setStat(p, name, v)
    local e = CharacterStat ~= nil and CharacterStat[name] or nil
    if p == nil or e == nil then return false end
    local ok = pcall(function() p:getStats():set(e, v) end)
    return ok
end

function T.part(p, i)
    if p == nil or BodyPartType == nil or BodyPartType.FromIndex == nil then return nil end
    local t = try(function() return BodyPartType.FromIndex(i) end)
    if t == nil then return nil end
    return try(function() return p:getBodyDamage():getBodyPart(t) end)
end

function T.partPain(p, i)
    local bp = T.part(p, i)
    if bp == nil then return nil end
    return try(function() return bp:getAdditionalPain() end)
end

function T.level(p, name)
    local mt = MoodleType ~= nil and MoodleType[name] or nil
    if p == nil or mt == nil then return nil end
    return try(function() return p:getMoodles():getMoodleLevel(mt) end)
end

-- ---- state
T.user = T.user
T.holds = T.holds or {}
T.trackPart = T.trackPart or 7
T.acc = { ticks = 0, mult = 0 }
T.ticks = T.ticks or 0
T.s = T.s or {}

function T.reset()
    T.mlog = { n = 0, rows = {}, dropped = 0 }
    T.ring = { n = 0, rows = {}, dropped = 0, on = false }
    T.trkReset()
    return true
end

function T.trkReset()
    T.trk = { n = 0, ms = nowMs() }
    return true
end

if T.mlog == nil then T.reset() end

function T.watch(user)
    T.user = user
    return T.findPlayer(user) ~= nil
end

function T.ringOn(on)
    T.ring.on = (on == true)
    return T.ring.on
end

-- ---- the holds
local SET_KINDS = { endcap = true, stress = true, unhappy = true, boredcap = true }
local STAT_OF = { endcap = "ENDURANCE", stress = "STRESS", unhappy = "UNHAPPINESS", boredcap = "BOREDOM" }
local CEILING = { endcap = true, boredcap = true }

function T.holdKey(kind, a)
    if kind == "pain" then return "pain:" .. tostring(a) end
    return kind
end

-- Apply one hold to p: returns before, after, wrote.
function T.apply(p, h)
    if h.kind == "pain" then
        local bp = T.part(p, h.part)
        if bp == nil then return nil, nil, false end
        local before = try(function() return bp:getAdditionalPain() end)
        local ok = pcall(function() bp:setAdditionalPain(h.value) end)
        local after = try(function() return bp:getAdditionalPain() end)
        return before, after, ok
    end
    local name = STAT_OF[h.kind]
    local before = T.stat(p, name)
    if type(before) ~= "number" then return before, before, false end
    local need = false
    if CEILING[h.kind] then need = before > h.value else need = before < h.value end
    if not need then return before, before, false end
    local ok = T.setStat(p, name, h.value)
    return before, T.stat(p, name), ok
end

function T.log(ev, key, h, before, after, wrote)
    local L = T.mlog
    if L.n >= T.MINUTE_CAP then
        L.dropped = L.dropped + 1
        return
    end
    L.n = L.n + 1
    L.rows[L.n] = { ev = ev, key = key, kind = h.kind, part = h.part, value = h.value, before = before,
                    after = after, wrote = wrote, age = worldAge(), ms = nowMs(), ticks = T.acc.ticks,
                    mult = T.acc.mult, tick = T.ticks }
end

function T.hold(user, kind, a, b)
    local p = T.findPlayer(user)
    if p == nil then return false, "no online player" end
    local h
    if kind == "pain" then
        if type(a) ~= "number" or type(b) ~= "number" then return false, "usage: hold <user> pain <part> <value>" end
        h = { kind = "pain", part = a, value = b }
        T.trackPart = a
    elseif SET_KINDS[kind] then
        if type(a) ~= "number" then return false, "usage: hold <user> " .. tostring(kind) .. " <value>" end
        h = { kind = kind, value = a }
    else
        return false, "unknown kind " .. tostring(kind)
    end
    T.user = user
    local key = T.holdKey(kind, a)
    T.holds[key] = h
    local before, after, wrote = T.apply(p, h)
    T.log("arm", key, h, before, after, wrote)
    return true, before, after
end

function T.release(kind, a)
    if kind == "all" then
        local n = 0
        for k in pairs(T.holds) do
            T.holds[k] = nil
            n = n + 1
        end
        return true, n
    end
    local key = T.holdKey(kind, a)
    local had = T.holds[key] ~= nil
    T.holds[key] = nil
    return had
end

function T.setPain(user, part, value)
    local p = T.findPlayer(user)
    if p == nil then return false, "no online player" end
    local bp = T.part(p, part)
    if bp == nil then return false, "no body part" end
    local before = try(function() return bp:getAdditionalPain() end)
    local ok = pcall(function() bp:setAdditionalPain(value) end)
    T.trackPart = part
    T.user = user
    return ok, before, try(function() return bp:getAdditionalPain() end)
end

function T.sortedKeys()
    local keys = {}
    for k in pairs(T.holds) do keys[#keys + 1] = k end
    table.sort(keys)
    return keys
end

function T.onMinute()
    local keys = T.sortedKeys()
    if keys[1] ~= nil then
        local p = T.findPlayer(T.user)
        if p ~= nil then
            for i = 1, #keys do
                local h = T.holds[keys[i]]
                local before, after, wrote = T.apply(p, h)
                T.log("minute", keys[i], h, before, after, wrote)
            end
        end
    end
    T.acc = { ticks = 0, mult = 0 }
end

-- ---- the per-tick snapshot, trackers and ring
local LEVELS = { lvPain = "PAIN", lvEnd = "ENDURANCE", lvStress = "STRESS", lvUnhappy = "UNHAPPY" }

function T.track(key, v)
    if type(v) ~= "number" then return end
    local lo, hi = key .. "Min", key .. "Max"
    if T.trk[lo] == nil or v < T.trk[lo] then T.trk[lo] = v end
    if T.trk[hi] == nil or v > T.trk[hi] then T.trk[hi] = v end
end

function T.onTick()
    T.ticks = T.ticks + 1
    local m = multiplier()
    T.acc.ticks = T.acc.ticks + 1
    if type(m) == "number" then T.acc.mult = T.acc.mult + m end
    if T.user == nil then return end
    local p = T.findPlayer(T.user)
    if p == nil then
        T.s = { online = false, n = T.ticks, ms = nowMs() }
        return
    end
    local s = { online = true, n = T.ticks, ms = nowMs(), age = worldAge(), mult = m, trackPart = T.trackPart,
                pain = T.stat(p, "PAIN"), part = T.partPain(p, T.trackPart), endurance = T.stat(p, "ENDURANCE"),
                stress = T.stat(p, "STRESS"), nicotine = T.stat(p, "NICOTINE_WITHDRAWAL"),
                unhappy = T.stat(p, "UNHAPPINESS"), boredom = T.stat(p, "BOREDOM"),
                fatigue = T.stat(p, "FATIGUE") }
    for key, name in pairs(LEVELS) do
        s[key] = T.level(p, name)
        T.track(key, s[key])
    end
    T.trk.n = T.trk.n + 1
    T.s = s
    local R = T.ring
    if R.on then
        if R.n >= T.RING_CAP then
            R.dropped = R.dropped + 1
        else
            R.n = R.n + 1
            R.rows[R.n] = { n = s.n, ms = s.ms, mult = m, pain = s.pain, part = s.part, endurance = s.endurance,
                            stress = s.stress, unhappy = s.unhappy, lvPain = s.lvPain, lvEnd = s.lvEnd,
                            lvStress = s.lvStress, lvUnhappy = s.lvUnhappy }
        end
    end
end

function T.dump(tag)
    if TK == nil or TK.result == nil then return false, "no TK.result" end
    local holds = {}
    for k, h in pairs(T.holds) do holds[k] = { kind = h.kind, part = h.part, value = h.value } end
    local ok = TK.result("tkxs-" .. tostring(tag), { minutes = T.mlog.rows, mN = T.mlog.n,
                         mDropped = T.mlog.dropped, ticks = T.ring.rows, tN = T.ring.n, tDropped = T.ring.dropped,
                         holds = holds, user = T.user, trackPart = T.trackPart, serverTicks = T.ticks })
    return ok, T.mlog.n, T.ring.n
end

-- The listeners, once per Lua state (a reloadlua re-runs this file; the sentinel keeps one copy of each).
if onServer() and Events ~= nil and not T.installed then
    T.installed = true
    if Events.EveryOneMinute ~= nil then
        Events.EveryOneMinute.Add(function()
            local ok, err = pcall(T.onMinute)
            if not ok then T.lastError = tostring(err) end
        end)
    end
    if Events.OnTick ~= nil then
        Events.OnTick.Add(function()
            local ok, err = pcall(T.onTick)
            if not ok then T.lastError = tostring(err) end
        end)
    end
end
