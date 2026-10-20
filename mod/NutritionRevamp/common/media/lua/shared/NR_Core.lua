-- NR_Core.lua -- the mod's one global, its version, the side test and the index-first guard.
-- Loads first in shared/ by name; every other NR_ file assumes NutritionRevamp exists.
-- Plain assignment on every load: a reload of this file resets the sub-tables, so no sentinel
-- for a wrapped vanilla function may live here (lua-platform rule #0943).
NutritionRevamp = {
    version = "1.0.0",
    build = "42.21",
    kernel = {},   -- pure functions, tables in and tables out, no Java (NR_Kernel*.lua)
    server = {},   -- server adapters (server/NR_Server_*.lua), gated by NutritionRevamp.isServer()
    client = {},   -- the read-only mirror (client/NR_Client_*.lua)
    log = { level = 2 },
}
local NR = NutritionRevamp

-- The side test, nil-checked before the protected call that reads it (#0937), evaluated per
-- call and never cached at file scope: a Lua state can load this file before the side is
-- decided, and a mod's server/ files run in the client's state too (#0855).
function NR.isServer()
    if isServer == nil then return false end
    local ok, v = pcall(isServer)
    return ok and v == true
end

-- The polled sleep setting (NR_Server_Options' sleepOn, read each server minute): true unless the server's
-- SleepAllowed and SleepNeeded are not both true; true before the first poll and with no options table. No Java.
function NR.sleepOn()
    local o = NR.server ~= nil and NR.server.options or nil
    return o == nil or o.sleepOn ~= false
end

function NR.isClient()
    if isClient == nil then return false end
    local ok, v = pcall(isClient)
    return ok and v == true
end

-- The index-first guard (#0934, #0935): index the member, then call it. Returns
-- (present, result...). A caught nil call names nothing, so the guard is what makes an absent
-- member visible. Never used inside a @fastpath region, which hoists its handles instead.
function NR.call(obj, name, ...)
    if obj == nil then return false, nil end
    local m = obj[name]
    if m == nil then return false, nil end
    return true, m(obj, ...)
end

-- Console lines on whichever side runs this. level 1 quiet (the boot self-report only),
-- 2 normal, 3 verbose. The level is set from the sandbox option at event time (NR_Server_Options).
function NR.log.say(level, msg)
    if level <= NR.log.level then print("[NutritionRevamp] " .. tostring(msg)) end
end

-- The item-pass sentinel, read by both sides' self-reports: the generated pass file's first item,
-- Base.Acorn, is re-based to 109.71 kcal (vanilla's script says 55.0). zombie.scripting.objects.Item keeps its macro
-- fields private and declares no calorie getter (#2679), so the read is a fresh instance through the instanceItem
-- global (LuaManager$GlobalObject.instanceItem(String), #2680) and its zombie.inventory.types.Food.getCalories().
-- Returns "true" or "false", or "unread" when the global, the item or the getter is absent or a call raises.
-- Called once per boot per side, never on a hot path. A regenerated pass file that moves the sentinel moves this
-- number too (testing/tests/test_mod_shipped_docs.py holds the two equal).
NR.itemPassSentinel = { fullType = "Base.Acorn", calories = 109.71 }
function NR.itemPassActive()
    if instanceItem == nil then return "unread" end
    local ok, item = pcall(instanceItem, NR.itemPassSentinel.fullType)
    if not ok or item == nil then return "unread" end
    local okC, present, v = pcall(NR.call, item, "getCalories")
    if not okC or not present or type(v) ~= "number" then return "unread" end
    return tostring(math.abs(v - NR.itemPassSentinel.calories) < 0.01)
end

-- The shared adapter helpers (Plan 10 Task R1): one copy, one failure meaning. worldAge is nil when the
-- clock cannot be read, and no adapter stamps 0 in its place: a minute without it is skipped.
function NR.worldAge()
    if getGameTime == nil then return nil end
    local ok, gt = pcall(getGameTime)
    if not ok or gt == nil then return nil end
    local okA, present, age = pcall(NR.call, gt, "getWorldAgeHours")
    if okA and present and NR.finite(age) then return age end
    return nil
end

-- A finite number: x - x is 0 for every finite number and NaN for NaN and either infinity.
function NR.finite(x)
    return type(x) == "number" and x - x == 0
end

-- The raise log (the bug review's should-fix): a member that raises inside NR.num, NR.obj or
-- NR.flag is logged once per member name per Lua state, so a broken getter is visible without a line a minute.
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

-- The sandbox options object (getSandboxOptions), fetched once per Lua state and kept in NR.so; nil while the global
-- is absent or raises, and fetched again on the next call (one helper for Kinetics and the writer,
-- which each kept their own copy).
function NR.sandbox()
    if NR.so == nil and getSandboxOptions ~= nil then
        local ok, so = pcall(getSandboxOptions)
        if ok then NR.so = so end
    end
    return NR.so
end

-- The real clock in milliseconds (getTimestampMs), or nil when the global is absent, raises or answers a non-number.
function NR.nowMs()
    if getTimestampMs == nil then return nil end
    local ok, v = pcall(getTimestampMs)
    if ok and type(v) == "number" then return v end
    return nil
end

-- A uniform roll in [0, 1) from ZombRandFloat, or dflt when the global is absent, raises or answers a non-finite
-- number.
function NR.roll(dflt)
    if ZombRandFloat == nil then return dflt end
    local ok, v = pcall(ZombRandFloat, 0, 1)
    if ok and NR.finite(v) then return v end
    return dflt
end

-- A record sub-table's heal (the #2833 pattern): every numeric field of t that is not finite takes ref's value for its
-- key, the world age ageH for a key in ageFields, or 0 when zero is true and ref holds no number (a nil clears the
-- field, so its kernel lays it again). Each healed name, prefix .. field, or prefix .. key .. "." .. field for a
-- nutrient's sub-table (joined only when a bad field is found), is appended to bad, comma-joined. Returns bad.
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

-- The sentinel install of a vanilla method wrap (Intake and Fitness): S is a persistent global table keeping orig,
-- wrapper and class across reloads. Idempotent: when ours is the outermost, or still in the chain below a later wrap,
-- nothing changes, so the wrapper is never saved as its own original. make(S, kind) builds the wrapper once, kept in
-- S; it names nothing from its file's load. label names the method in the log line. absentOk installs over a method
-- the class does not define (ISEatFoodAction's serverStart): S.orig is then nil, and the wrapper must skip it. Returns
-- whether the wrap is in place.
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

-- The client surfaces' helper set (the panel, the moodles, the view and the tooltip): one guard, one failure count and
-- one translation lookup. try: a method of o, index-first inside a pcall; (true, result) when the member is present
-- and answered, else (false, nil), a raise included.
function NR.try(o, name, ...)
    local ok, present, v = pcall(NR.call, o, name, ...)
    return ok and present, v
end

-- A surface's failure: counted in surface.stats.errors, kept as surface.lastError and logged under label.
function NR.fail(surface, label, err)
    surface.stats.errors = surface.stats.errors + 1
    surface.lastError = err
    NR.log.say(2, label .. ": " .. tostring(err))
end

-- A translation through NR.client.text (NR_Client_ModOptions.lua, looked up per call), else the fallback or the key.
function NR.text(key, fallback)
    local f = NutritionRevamp.client.text
    if f ~= nil then return f(key, fallback) end
    if fallback ~= nil then return fallback end
    return key
end

-- The player-minute's engine reads (Rule 6): the steps of one player's minute run in one call, inside
-- one server tick, so a member several steps read answers the same; each is read once and kept on the pipeline's
-- context (NR_Server_Minute's ctx, cleared per player), and the steps after the first share that read. A nil ctx (a
-- step called outside the pipeline) reads afresh. A read that answers nil is kept as NONE, so it is not read again.
-- The world age is the pipeline's own read (P.work's, seeded by NR_Server_Minute.run); the hour of day is the clock's
-- getTimeOfDay, else the world age's hour, (ageH + 7) mod 24 (GameTime.getWorldAgeHours counts from 07:00 of day one:
-- nightsSurvived x 24 + timeOfDay - 7; 7 with no age). The hour is read once a server minute (RD.hoist, from the
-- players' minute, Plan 16 Task 4) and shared by every player's minute through the context (NR_Server_Minute.run seeds
-- eHour from RD.minuteHour); only the body clock's seed reads it (K.circadian.step). The failure meaning is NR.flag's and
-- NR.obj's: a raise reads false or nil.
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
-- The server minute's hour of day and day length, read once at the players' minute (P.minute) for every player's
-- pipeline (Rule 6: the day length's read moved here from each player-minute in Plan 17 Task 3, NR_Server_Minute seeds
-- it as eDayMin); nil until the first read, and the day length nil while the sandbox is unreadable.
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
-- bd (optional) is the body damage the caller holds, so a call with no ctx reads it once.
function RD.thermo(ctx, p, bd) return memo(ctx, "eThermo", readThermo, ctx, p, bd) end
function RD.nutrition(ctx, p) return memo(ctx, "eNut", readNutrition, p) end
-- The day length in real minutes (the sandbox's getDayLengthMinutes), dflt when unreadable: the minute's hoisted read
-- (eDayMin, seeded by NR_Server_Minute), else one read a player-minute, shared by Effects' heal toward its target and
-- the writer's re-applied severe terms (Plan 15 Task 6, Task 5's review L4).
function RD.dayMin(ctx, dflt)
    local v = memo(ctx, "eDayMin", readDayMin)
    if v == nil then return dflt end
    return v
end

-- A moodle's level 0..4 off a moodles object (getMoodles), 0 when the object, the type or the read is absent: one copy for
-- Effects and the writer (Plan 15 Task 6, Task 5's review I5).
function RD.moodleLevel(moodles, t)
    if moodles == nil or t == nil then return 0 end
    return NR.kernel.clamp(math.floor(NR.num(moodles, "getMoodleLevel", 0, t)), 0, 4)
end

-- One trait flag a player-minute (Plan 15 Task 3 fix 1): the first get of trait t is kept in the minute's flag table
-- (ctx.eFlags, the one reused table RD.FLAGS, emptied when a minute first reads a flag), so Nutrients' sleep and thirst
-- traits and the writer's sleep traits share one get each. Only for traits no step changes inside the minute: the
-- band, night-vision and short-sight traits Effects, Strength and Weight toggle are read off the collection. coll
-- (optional) is the collection the caller holds (the writer's hoisted h.traits), taken as the minute's when none is
-- read yet; with no ctx every call reads. A raise or a non-boolean answer reads false (NR.flag).
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

-- The context keys the reads above keep: the pipeline drops them at the end of each player's minute (MIN.run), so the
-- shared context holds no player's Java objects between drains.
RD.KEYS = { "eAge", "eHour", "eAsleep", "eTraits", "eBd", "eThermo", "eNut", "eFlags", "eDayMin" }

-- The trait-block push (#2099): sendSyncPlayerFields(player, 2), a Java global called with a dot (#2815), under one
-- pcall, so a raise never skips the work after it in the caller's minute. Counted in stats.pushes, or in
-- stats.pushMissing when the global is absent or raises. Returns whether it ran. One copy for Effects, Strength
-- and Weight.
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

-- The mode the server runs: the writer's (NR_Server_Writer), fixed at OnGameBoot, not the option NR_Server_Options
-- polls every minute (an NR.Mode changed mid-run is read but not run); the option, then 1, before the writer has
-- decided. Read by the mirror's meta and the self-report.
function NR.runningMode()
    local W = NR.server.writer
    if W ~= nil and W.mode ~= nil then return W.mode end
    local O = NR.server.options
    if O ~= nil and O.mode ~= nil then return O.mode end
    return 1
end

-- The server's strength table (NR_Server_Options builds it from the sandbox), else K.strength.DEFAULTS while no
-- options table is laid (a runtime without NR_Server_Options); nil in a runtime without the strength kernel, which every
-- kernel reader takes as DEFAULTS. Every server adapter reads it here, at the call.
function NR.strengthP()
    local O = NR.server.options
    if O ~= nil and O.strength ~= nil then return O.strength end
    local S = NR.kernel.strength
    return S ~= nil and S.DEFAULTS or nil
end

-- NR.SexSpecific: true only when the options table reads it true (an absent table reads off).
function NR.sexSpecific()
    local O = NR.server.options
    return O ~= nil and O.sexSpecific == true
end
