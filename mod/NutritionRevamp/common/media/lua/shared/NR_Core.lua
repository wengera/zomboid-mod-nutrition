-- NR_Core.lua -- the mod's one global, the side test and the index-first guard; loads first in shared/ by name.
-- Plain assignment on every load resets the sub-tables, so no wrap sentinel may live here (#0943).
NutritionRevamp = {
    version = "1.0.0",
    build = "42.21",
    kernel = {},   -- pure functions, tables in and tables out, no Java (NR_Kernel*.lua)
    server = {},   -- server adapters (server/NR_Server_*.lua), gated by NutritionRevamp.isServer()
    client = {},   -- the read-only mirror (client/NR_Client_*.lua)
    log = { level = 2 },
}
local NR = NutritionRevamp

-- Evaluated per call, never cached: a state can load this before the side is decided, and server/ runs on clients (#0855).
function NR.isServer()
    if isServer == nil then return false end
    local ok, v = pcall(isServer)
    return ok and v == true
end

-- true unless SleepAllowed and SleepNeeded are not both true; true before the first options poll.
function NR.sleepOn()
    local o = NR.server ~= nil and NR.server.options or nil
    return o == nil or o.sleepOn ~= false
end

function NR.isClient()
    if isClient == nil then return false end
    local ok, v = pcall(isClient)
    return ok and v == true
end

-- Index first, then call (#0934): a caught nil call names nothing. Never inside a @fastpath region.
function NR.call(obj, name, ...)
    if obj == nil then return false, nil end
    local m = obj[name]
    if m == nil then return false, nil end
    return true, m(obj, ...)
end

-- level 1 quiet, 2 normal, 3 verbose; set from the sandbox option (NR_Server_Options).
function NR.log.say(level, msg)
    if level <= NR.log.level then print("[NutritionRevamp] " .. tostring(msg)) end
end

-- The item-pass sentinel: Item declares no calorie getter (#2679), so a fresh instance is read through instanceItem.
-- A regenerated pass file that moves the sentinel moves this number too (test_mod_shipped_docs holds them equal).
NR.itemPassSentinel = { fullType = "Base.Acorn", calories = 109.71 }
function NR.itemPassActive()
    if instanceItem == nil then return "unread" end
    local ok, item = pcall(instanceItem, NR.itemPassSentinel.fullType)
    if not ok or item == nil then return "unread" end
    local okC, present, v = pcall(NR.call, item, "getCalories")
    if not okC or not present or type(v) ~= "number" then return "unread" end
    return tostring(math.abs(v - NR.itemPassSentinel.calories) < 0.01)
end

-- worldAge is nil when the clock is unreadable, never 0: a minute without it is skipped.
function NR.worldAge()
    if getGameTime == nil then return nil end
    local ok, gt = pcall(getGameTime)
    if not ok or gt == nil then return nil end
    local okA, present, age = pcall(NR.call, gt, "getWorldAgeHours")
    if okA and present and NR.finite(age) then return age end
    return nil
end

-- x - x is 0 for every finite number and NaN for NaN and either infinity.
function NR.finite(x)
    return type(x) == "number" and x - x == 0
end

-- A raising member is logged once per name per Lua state, never a line a minute.
NR.raised = {}
function NR.noteRaise(name, err)
    if NR.raised[name] ~= nil then return end
    NR.raised[name] = true
    NR.log.say(2, "call: " .. tostring(name) .. " raised: " .. tostring(err))
end

function NR.num(o, name, dflt, ...)
    local ok, present, v = pcall(NR.call, o, name, ...)
    if not ok then NR.noteRaise(name, present) end
    if ok and present and NR.finite(v) then return v end
    return dflt
end

function NR.obj(o, name, ...)
    local ok, present, v = pcall(NR.call, o, name, ...)
    if not ok then NR.noteRaise(name, present) end
    if ok and present then return v end
    return nil
end

function NR.flag(o, name, ...)
    local ok, present, v = pcall(NR.call, o, name, ...)
    if not ok then NR.noteRaise(name, present) end
    return ok and present and v == true
end

-- Fetched once per Lua state; retried on the next call while the global is absent or raises.
function NR.sandbox()
    if NR.so == nil and getSandboxOptions ~= nil then
        local ok, so = pcall(getSandboxOptions)
        if ok then NR.so = so end
    end
    return NR.so
end

function NR.nowMs()
    if getTimestampMs == nil then return nil end
    local ok, v = pcall(getTimestampMs)
    if ok and type(v) == "number" then return v end
    return nil
end

-- dflt when ZombRandFloat is absent, raises or answers a non-finite number.
function NR.roll(dflt)
    if ZombRandFloat == nil then return dflt end
    local ok, v = pcall(ZombRandFloat, 0, 1)
    if ok and NR.finite(v) then return v end
    return dflt
end

-- The #2833 heal: a non-finite field takes ref's value, ageH for an age field, or 0 when zero is set (a nil clears it,
-- so its kernel lays it again); each healed name is comma-appended to bad, which is returned.
function NR.healTable(t, ref, bad, prefix, key, ageH, ageFields, zero)
    for k, v in pairs(t) do
        if type(v) == "number" and not NR.finite(v) then
            local nv = ref[k]
            if ageFields ~= nil and ageFields[k] then nv = ageH end
            if zero and type(nv) ~= "number" then nv = 0 end
            t[k] = nv
            local p = prefix
            if key ~= nil then p = prefix .. key .. "." end
            if bad == nil then bad = p .. tostring(k) else bad = bad .. "," .. p .. tostring(k) end
        end
    end
    return bad
end

-- Idempotent across reloads (S is a persistent global): when ours is outermost or still below a later wrap, nothing
-- changes, so the wrapper is never saved as its own original. absentOk wraps a method the class lacks (S.orig nil).
function NR.installWrap(S, cls, method, make, kind, label, absentOk)
    if cls == nil then return false end
    local cur = cls[method]
    if cur == nil and not absentOk then return false end
    if (cur ~= nil and cur == S.wrapper) or (S.wrapper ~= nil and S.class == cls) then return true end
    S.orig = cur
    S.wrapper = S.wrapper or make(S, kind)
    S.class = cls
    cls[method] = S.wrapper
    NR.log.say(2, label .. " wrapped")
    return true
end

-- The client surfaces' helpers. try: (true, result) when the member is present and answered, else (false, nil).
function NR.try(o, name, ...)
    local ok, present, v = pcall(NR.call, o, name, ...)
    return ok and present, v
end

function NR.fail(surface, label, err)
    surface.stats.errors = surface.stats.errors + 1
    surface.lastError = err
    NR.log.say(2, label .. ": " .. tostring(err))
end

function NR.text(key, fallback)
    local f = NutritionRevamp.client.text
    if f ~= nil then return f(key, fallback) end
    if fallback ~= nil then return fallback end
    return key
end

-- The player-minute's engine reads (Rule 6): one player's minute runs in one tick, so each member is read once and kept
-- on the pipeline's ctx; a nil answer is kept as NONE. A nil ctx reads afresh. The hour falls back to the world age's,
-- (ageH + 7) mod 24, because getWorldAgeHours counts from 07:00 of day one.
NR.read = {}
local RD = NR.read
local NONE = {}

local function memo(ctx, key, read, a, b, c)
    if ctx == nil then return read(a, b, c) end
    local v = ctx[key]
    if v == nil then
        v = read(a, b, c)
        if v == nil then ctx[key] = NONE else ctx[key] = v end
        return v
    end
    if v == NONE then return nil end
    return v
end

local function readHour(ageH)
    local hour = 7
    if ageH ~= nil then hour = (ageH + 7) - math.floor((ageH + 7) / 24) * 24 end
    if getGameTime ~= nil then
        local ok, gt = pcall(getGameTime)
        hour = NR.num(ok and gt or nil, "getTimeOfDay", hour)
    end
    return hour
end
local function readAsleep(p) return NR.flag(p, "isAsleep") end
local function readTraits(p) return NR.obj(p, "getCharacterTraits") end
local function readBodyDamage(p) return NR.obj(p, "getBodyDamage") end
local function readThermo(ctx, p, bd)
    if bd == nil then bd = RD.bodyDamage(ctx, p) end
    return NR.obj(bd, "getThermoregulator")
end
local function readNutrition(p) return NR.obj(p, "getNutrition") end
local function readDayMin() return NR.num(NR.sandbox(), "getDayLengthMinutes", nil) end

function RD.ageH(ctx) return memo(ctx, "eAge", NR.worldAge) end
function RD.hour(ctx, ageH) return memo(ctx, "eHour", readHour, ageH) end
-- Read once at the players' minute (P.minute) for every player's pipeline (Rule 6); nil until the first read.
RD.minuteHour = nil
RD.minuteDayMin = nil
function RD.hoist(ageH)
    RD.minuteHour = readHour(ageH)
    RD.minuteDayMin = readDayMin()
    return RD.minuteHour
end
function RD.asleep(ctx, p) return memo(ctx, "eAsleep", readAsleep, p) end
function RD.traits(ctx, p) return memo(ctx, "eTraits", readTraits, p) end
function RD.bodyDamage(ctx, p) return memo(ctx, "eBd", readBodyDamage, p) end
function RD.thermo(ctx, p, bd) return memo(ctx, "eThermo", readThermo, ctx, p, bd) end
function RD.nutrition(ctx, p) return memo(ctx, "eNut", readNutrition, p) end
-- The minute's hoisted read (eDayMin), else one read a player-minute; dflt when unreadable.
function RD.dayMin(ctx, dflt)
    local v = memo(ctx, "eDayMin", readDayMin)
    if v == nil then return dflt end
    return v
end

-- 0 when the object, the type or the read is absent.
function RD.moodleLevel(moodles, t)
    if moodles == nil or t == nil then return 0 end
    return NR.kernel.clamp(math.floor(NR.num(moodles, "getMoodleLevel", 0, t)), 0, 4)
end

-- The first get of trait t a minute is kept in ctx.eFlags (the reused RD.FLAGS). Only for traits no step changes inside
-- the minute: the band, night-vision and short-sight traits are read off the collection.
RD.FLAGS = {}
function RD.trait(ctx, p, t, coll)
    if t == nil then return false end
    if ctx == nil then return NR.flag(coll or readTraits(p), "get", t) end
    local f = ctx.eFlags
    if f == nil then
        f = RD.FLAGS
        for k in pairs(f) do f[k] = nil end
        ctx.eFlags = f
    end
    local v = f[t]
    if v == nil then
        if coll ~= nil and ctx.eTraits == nil then ctx.eTraits = coll end
        v = NR.flag(RD.traits(ctx, p), "get", t)
        f[t] = v
    end
    return v
end

-- Dropped at the end of each player's minute (MIN.run), so the context holds no Java objects between drains.
RD.KEYS = { "eAge", "eHour", "eAsleep", "eTraits", "eBd", "eThermo", "eNut", "eFlags", "eDayMin" }

-- The trait-block push (#2099), a Java global called with a dot (#2815), under one pcall so a raise skips nothing after.
function NR.pushTraits(player, stats)
    local f = sendSyncPlayerFields
    local ok = f ~= nil and pcall(f, player, 2)
    if ok then
        stats.pushes = stats.pushes + 1
    else
        stats.pushMissing = stats.pushMissing + 1
    end
    return ok
end

-- The writer's mode, fixed at OnGameBoot: an NR.Mode changed mid-run is read but not run.
function NR.runningMode()
    local W = NR.server.writer
    if W ~= nil and W.mode ~= nil then return W.mode end
    local O = NR.server.options
    if O ~= nil and O.mode ~= nil then return O.mode end
    return 1
end

-- K.strength.DEFAULTS while no options table is laid; nil without the strength kernel, read as DEFAULTS.
function NR.strengthP()
    local O = NR.server.options
    if O ~= nil and O.strength ~= nil then return O.strength end
    local S = NR.kernel.strength
    return S ~= nil and S.DEFAULTS or nil
end

function NR.sexSpecific()
    local O = NR.server.options
    return O ~= nil and O.sexSpecific == true
end
