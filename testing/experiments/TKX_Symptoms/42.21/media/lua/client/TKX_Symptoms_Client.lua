-- TKX_Symptoms client side (Plan 18 Task 1). TEST-ONLY: installed by the x49 profiles only, never shipped.
-- Every client tick it rewrites TKX_Symptoms.c for the local player, the client half of the driver's pairs: PAIN,
-- the tracked part's added pain as the client's own BodyPart copy holds it (TKX_Symptoms.cpart, default 7, the lower
-- torso), ENDURANCE, STRESS, NICOTINE_WITHDRAWAL, UNHAPPINESS, BOREDOM, and the PAIN, ENDURANCE, STRESS and UNHAPPY
-- moodle levels the client's own Moodles hold, with the wall ms and a tick count; lua.read reads it in one tick.
-- TKX_Symptoms.ctrk holds each level's minimum and maximum since TKX_Symptoms.creset() (lua.call on the client), so
-- a level dip between two driver reads is seen. TKX_Symptoms.cpartSet(i) moves the tracked part.
-- Every Java member is reached under pcall. Kahlua: no goto, no # on a Java list, no string.format.
TKX_Symptoms = TKX_Symptoms or {}
local T = TKX_Symptoms

T.version = "1"
T.cpart = T.cpart or 7
T.cticks = T.cticks or 0
T.c = T.c or {}

local function onClient()
    if isClient == nil then return false end
    local ok, c = pcall(isClient)
    return ok and c == true
end

local function try(fn)
    local ok, v = pcall(fn)
    if ok then return v end
    return nil
end

local function stat(p, name)
    local e = CharacterStat ~= nil and CharacterStat[name] or nil
    if e == nil then return nil end
    return try(function() return p:getStats():get(e) end)
end

local function level(p, name)
    local mt = MoodleType ~= nil and MoodleType[name] or nil
    if mt == nil then return nil end
    return try(function() return p:getMoodles():getMoodleLevel(mt) end)
end

local function partPain(p, i)
    if BodyPartType == nil or BodyPartType.FromIndex == nil then return nil end
    local t = try(function() return BodyPartType.FromIndex(i) end)
    if t == nil then return nil end
    return try(function() return p:getBodyDamage():getBodyPart(t):getAdditionalPain() end)
end

function T.creset()
    T.ctrk = { n = 0, ms = try(function() return getTimestampMs() end) }
    return true
end

function T.cpartSet(i)
    if type(i) ~= "number" then return false end
    T.cpart = i
    return true
end

if T.ctrk == nil then T.creset() end

local CLEVELS = { lvPain = "PAIN", lvEnd = "ENDURANCE", lvStress = "STRESS", lvUnhappy = "UNHAPPY" }

function T.ctrack(key, v)
    if type(v) ~= "number" then return end
    local lo, hi = key .. "Min", key .. "Max"
    if T.ctrk[lo] == nil or v < T.ctrk[lo] then T.ctrk[lo] = v end
    if T.ctrk[hi] == nil or v > T.ctrk[hi] then T.ctrk[hi] = v end
end

function T.cTick()
    T.cticks = T.cticks + 1
    local p = getPlayer and getPlayer() or nil
    if p == nil then return end
    local c = { n = T.cticks, ms = try(function() return getTimestampMs() end), cpart = T.cpart,
                pain = stat(p, "PAIN"), part = partPain(p, T.cpart), endurance = stat(p, "ENDURANCE"),
                stress = stat(p, "STRESS"), nicotine = stat(p, "NICOTINE_WITHDRAWAL"),
                unhappy = stat(p, "UNHAPPINESS"), boredom = stat(p, "BOREDOM") }
    for key, name in pairs(CLEVELS) do
        c[key] = level(p, name)
        T.ctrack(key, c[key])
    end
    T.ctrk.n = T.ctrk.n + 1
    T.c = c
end

if onClient() and Events ~= nil and Events.OnTick ~= nil and not T.cinstalled then
    T.cinstalled = true
    Events.OnTick.Add(function()
        local ok, err = pcall(T.cTick)
        if not ok then T.cLastError = tostring(err) end
    end)
end
