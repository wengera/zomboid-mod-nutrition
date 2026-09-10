-- PZTestKit core. Loads on the dedicated server and on every client (shared/).
--  * TK is a global on purpose: `reloadlua` re-runs this file and state must survive (S7).
--  * Command bus: the orchestrator writes <cachedir>/Lua/pzt-cmd.txt {seq, cmd, args};
--    each seq is executed once (last seq recovered from pzt-ack.txt after a Lua reset)
--    and answered in pzt-ack.txt {seq, cmd, result}. Same protocol on both sides.
--  * Results: TK.result(name, table) writes <cachedir>/Lua/pzt-results/<name>.json as one
--    complete JSON object; a parseable file IS the ready marker (S4).
TK = TK or {}
TK.version = 1
TK.commands = TK.commands or {}
TK.lastSeq = TK.lastSeq or 0
TK.ticks = TK.ticks or 0
TK.side = isServer() and "server" or (isClient() and "client" or "sp")

function TK.log(msg) print("PZTK: " .. tostring(msg)) end

function TK.now() return getTimestampMs and getTimestampMs() or 0 end

function TK.readKV(name)
    local reader = getFileReader(name, false)
    if not reader then return nil end
    local t = {}
    while true do
        local line = reader:readLine()
        if line == nil then break end
        local k, v = string.match(line, "^%s*([%w_%.]+)%s*=%s*(.-)%s*$")
        if k then t[k] = v end
    end
    reader:close()
    return t
end

function TK.writeKV(name, t)
    local w = getFileWriter(name, true, false)
    if not w then TK.log("cannot write " .. name); return false end
    for k, v in pairs(t) do w:write(k .. "=" .. tostring(v) .. "\n") end
    w:close()
    return true
end

-- ---- JSON (encode only) ----------------------------------------------------
local function jsonString(s)
    s = string.gsub(s, '[%c"\\]', function(c)
        if c == '"' then return '\\"' end
        if c == "\\" then return "\\\\" end
        if c == "\n" then return "\\n" end
        if c == "\t" then return "\\t" end
        if c == "\r" then return "\\r" end
        return string.format("\\u%04x", string.byte(c))
    end)
    return '"' .. s .. '"'
end

function TK.json(v, depth)
    depth = depth or 0
    if depth > 8 then return '"<too deep>"' end
    local t = type(v)
    if t == "nil" then return "null" end
    if t == "boolean" then return v and "true" or "false" end
    if t == "number" then
        if v ~= v then return "null" end
        if v == math.floor(v) and math.abs(v) < 1e15 then return string.format("%.0f", v) end
        return string.format("%.6f", v)
    end
    if t == "string" then return jsonString(v) end
    if t == "table" then
        local n = #v
        local isArray = n > 0
        if isArray then
            for k in pairs(v) do if type(k) ~= "number" then isArray = false; break end end
        end
        local parts = {}
        if isArray then
            for i = 1, n do parts[#parts + 1] = TK.json(v[i], depth + 1) end
            return "[" .. table.concat(parts, ",") .. "]"
        end
        for k, val in pairs(v) do
            parts[#parts + 1] = jsonString(tostring(k)) .. ":" .. TK.json(val, depth + 1)
        end
        return "{" .. table.concat(parts, ",") .. "}"
    end
    return jsonString(tostring(v))   -- Java objects: their toString()
end

function TK.result(name, tbl)
    tbl = tbl or {}
    tbl.name, tbl.side, tbl.t, tbl.complete = name, TK.side, TK.now(), true
    local w = getFileWriter("pzt-results/" .. name .. ".json", true, false)
    if not w then TK.log("cannot write result " .. name); return false end
    w:write(TK.json(tbl))
    w:close()
    TK.log("result " .. name .. " written")
    return true
end

-- ---- probing Java objects safely --------------------------------------------
-- Calling a method a Java object does not have raises Kahlua's "Tried to call nil", and in
-- PZ that is NOT recoverable with pcall: it escapes and kills the calling event handler
-- (measured, run exp01-20260909-235420 - the client stopped answering the bus entirely).
-- So probe by indexing first, exactly like the game's own ISItemEditPanel.lua:442.
-- Returns (present, value).
function TK.call(obj, name, ...)
    if obj == nil then return false, nil end
    local m = obj[name]
    if m == nil then return false, nil end
    return true, m(obj, ...)
end

function TK.field(obj, name)
    if obj == nil then return false, nil end
    local v = obj[name]
    if v == nil or type(v) == "function" then return false, nil end
    return true, v
end

-- ---- nutrition snapshot (both sides: client commands and the server's per-user ones) ----
-- Stats accessors moved with B42: the pre-B42 getHunger()/`.hunger` pair is gone and the
-- game's own Lua reads Stats:get(CharacterStat.HUNGER). Try that first, then the two older
-- forms; `statsApi` in the snapshot records which one answered (decision ledger evidence).
local function statValue(s, enumName, getter, field)
    local enum = CharacterStat and CharacterStat[enumName]
    if enum then
        local ok, v = TK.call(s, "get", enum)
        if ok and v ~= nil then return v, "Stats:get(CharacterStat." .. enumName .. ")" end
    end
    local ok, v = TK.call(s, getter)
    if ok and v ~= nil then return v, "Stats:" .. getter .. "()" end
    ok, v = TK.field(s, field)
    if ok then return v, "Stats." .. field end
    return nil, "none"
end

function TK.nutritionSnapshot(p)
    local n, s = p:getNutrition(), p:getStats()
    local hunger, api = statValue(s, "HUNGER", "getHunger", "hunger")
    local thirst = statValue(s, "THIRST", "getThirst", "thirst")
    return { calories = n:getCalories(), carbs = n:getCarbohydrates(), lipids = n:getLipids(),
             proteins = n:getProteins(), weight = n:getWeight(), hunger = hunger, thirst = thirst,
             statsApi = api }
end

TK.NUTRITION_SETTERS = { calories = "setCalories", carbs = "setCarbohydrates", lipids = "setLipids",
                         proteins = "setProteins", weight = "setWeight" }

-- ---- writing stats (hunger/thirst) ------------------------------------------
-- Needed because CharacterStat.HUNGER/THIRST clamp to [0,1]: on a satiated character every
-- eat's hunger/thirst relief is silently discarded and dHunger/dThirst measure nothing.
-- B42 writes stats through the enum -- the game's own Lua is Stats:set(CharacterStat.HUNGER, v)
-- (ISAnimalContextMenu.lua:739, Tutorial/Steps.lua:548, server/ClientCommands.lua:897), which
-- also pins the arity at two -- so that is the primary route and set<Name>() the fallback.
-- The enum is read BEFORE the call and the route skipped when it is nil: handing a nil enum to
-- a present Java method is an argument mismatch, and Kahlua does not let pcall catch that
-- either. Returns (ok, how): `how` names the route that answered, or why none did.
TK.STAT_FIELDS = { hunger = { "HUNGER", "setHunger" }, thirst = { "THIRST", "setThirst" },
                   fatigue = { "FATIGUE", "setFatigue" }, endurance = { "ENDURANCE", "setEndurance" } }

function TK.setStat(p, field, value)
    local spec = TK.STAT_FIELDS[field]
    if not spec then return false, "unknown stat '" .. tostring(field) .. "'" end
    local s = p:getStats()
    local enum = CharacterStat and CharacterStat[spec[1]]
    if enum and TK.call(s, "set", enum, value) then
        return true, "Stats:set(CharacterStat." .. spec[1] .. ")"
    end
    if TK.call(s, spec[2], value) then return true, "Stats:" .. spec[2] .. "()" end
    return false, "no Stats:set(CharacterStat." .. spec[1] .. ") and no Stats:" .. spec[2] .. "()"
end

-- "<field> <value> [<field> <value> ...]" starting at argv[first]. Reports per field so a
-- half-applied prime is visible in the results rather than silently wrong.
function TK.applyStats(p, argv, first)
    local applied, any = {}, false
    for i = first, #argv - 1, 2 do
        local v = tonumber(argv[i + 1])
        if v == nil then
            applied[tostring(argv[i])] = "not a number: " .. tostring(argv[i + 1])
        else
            local ok, how = TK.setStat(p, argv[i], v)
            applied[tostring(argv[i])] = (ok and how or ("failed: " .. tostring(how)))
            any = any or ok
        end
    end
    return applied, any
end

-- ---- command bus -----------------------------------------------------------
function TK.register(name, fn) TK.commands[name] = fn end

local function splitArgs(s)
    local out = {}
    for w in string.gmatch(s or "", "%S+") do out[#out + 1] = w end
    return out
end

function TK.pollCommands()
    local c = TK.readKV("pzt-cmd.txt")
    if not c or not c.seq then return end
    local seq = tonumber(c.seq) or 0
    if seq <= TK.lastSeq then return end
    TK.lastSeq = seq
    local name = c.cmd or ""
    TK.writeKV("pzt-ack.txt", { seq = seq, cmd = name, result = "running" })
    local fn = TK.commands[name]
    local ok, res
    if fn then ok, res = pcall(fn, splitArgs(c.args), c) else ok, res = false, "unknown command" end
    if type(res) == "table" then res = TK.json(res) end
    TK.log("cmd #" .. seq .. " " .. name .. " -> " .. tostring(res))
    TK.writeKV("pzt-ack.txt", { seq = seq, cmd = name, result = (ok and "ok:" or "err:") .. tostring(res) })
end

-- A Lua reset (client join) reloads this file: don't replay the last executed command.
do
    local ack = TK.readKV("pzt-ack.txt")
    if ack and ack.seq then TK.lastSeq = math.max(TK.lastSeq, tonumber(ack.seq) or 0) end
end

-- ---- commands available on both sides ---------------------------------------
TK.register("ping", function() return "pong" end)
TK.register("version", function() return "v" .. tostring(TK.version) .. " " .. TK.side end)
TK.register("result", function(argv)
    TK.result(argv[1] or "manual", { note = argv[2] })
    return "written"
end)
TK.register("state", function()
    return { ticks = TK.ticks, lastSeq = TK.lastSeq, version = TK.version, side = TK.side }
end)
TK.register("lua.reload", function(argv)
    local r = reloadLuaFile(argv[1])
    return "reloadLuaFile(" .. tostring(argv[1]) .. ") -> " .. tostring(r)
end)
TK.register("time.snapshot", function()
    local gt = getGameTime()
    return { worldAge = gt:getWorldAgeHours(), hour = gt:getHour(), minutes = gt:getMinutes(),
             mult = gt:getMultiplier(), wall = TK.now() }
end)
-- S3 probe: KeenPerception (workshop mod) removes the Keen Hearing <-> Deaf exclusivity.
TK.register("trait.check", function()
    local kh = CharacterTraitDefinition.getCharacterTraitDefinition(CharacterTrait.KEEN_HEARING)
    if not kh then return "no KEEN_HEARING definition" end
    local ex = kh:getMutuallyExclusiveTraits()
    return { keenHearingExcludesDeaf = ex:contains(CharacterTrait.DEAF),
             keenHearingExcludesHardOfHearing = ex:contains(CharacterTrait.HARD_OF_HEARING),
             keenPerceptionLoaded = not ex:contains(CharacterTrait.DEAF) }
end)

TK.log("core loaded (" .. TK.side .. ")")
