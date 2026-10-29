-- PZAgent_Core.lua — the PZA table. Loads first (shared/). No PZTestKit anywhere in this mod.
-- Every Java member is reached through PZA.call / PZA.field: an unguarded nil call on a -debug client
-- parks the process in the Lua debugger (platform/lua-platform.md#debug-break), and pcall names nothing.
PZA = PZA or {}
PZA.VERSION = "1.5"         -- 1.5: PZA/1.5, the actions aim and climb, me.aiming, water any drinkable beverage (P24-G); 1.4.1: the use table reads only drinkable water and edible food, the use container (P24-F); 1.4: PZA/1.4, me's attackers, hitReaction and dragDown, the square's hopN and hopW, attack busy (P24-C); 1.3: PZA/1.3, the death event (P23-AO); 1.2: me.hour, the square's edges, sleep and interact's maxWeight (pza1.json x-prior)

function PZA.log(msg) print("[PZAgent] " .. tostring(msg)) end
function PZA.now() return getTimestampMs and getTimestampMs() or 0 end

function PZA.call(obj, name, ...)
    if obj == nil then return false, nil end
    local m = obj[name]
    if m == nil then return false, nil end
    return true, m(obj, ...)
end

function PZA.field(obj, name)
    if obj == nil then return false, nil end
    local v = obj[name]
    if v == nil then return false, nil end
    return true, v
end

function PZA.missing(list, name)
    for i = 1, #list do if list[i] == name then return end end
    list[#list + 1] = name
end

-- every other control character as \u00XX, so a line carrying one (a lua_error's msg) stays valid JSON; the hex by
-- table, since an integer format of a Lua number raises on Kahlua (kahlua_lint format-d)
local HEX = "0123456789abcdef"
local function controlEscape(c)
    local b = string.byte(c)
    local hi, lo = math.floor(b / 16) + 1, b % 16 + 1
    return "\\u00" .. string.sub(HEX, hi, hi) .. string.sub(HEX, lo, lo)
end

local function jsonString(s)
    s = tostring(s)
    s = s:gsub('\\', '\\\\'):gsub('"', '\\"'):gsub('\n', '\\n'):gsub('\r', '\\r'):gsub('\t', '\\t')
    s = s:gsub('%c', controlEscape)
    return '"' .. s .. '"'
end

-- Encode-only JSON. An empty table is {} (the harness-wide convention); integers below 1e15 print
-- through %.0f, every other number through tostring, so nothing is rounded; NaN and ±Inf are null.
function PZA.json(v, depth)
    depth = depth or 0
    if depth > 8 then return '"<too deep>"' end
    local t = type(v)
    if t == "nil" then return "null" end
    if t == "boolean" then return v and "true" or "false" end
    if t == "number" then
        if v ~= v or v == math.huge or v == -math.huge then return "null" end
        if v == math.floor(v) and math.abs(v) < 1e15 then return string.format("%.0f", v) end
        return tostring(v)
    end
    if t == "string" then return jsonString(v) end
    if t == "table" then
        local n = 0
        for _ in pairs(v) do n = n + 1 end
        local isArray = n > 0
        for i = 1, n do if v[i] == nil then isArray = false; break end end
        local parts = {}
        if isArray then
            for i = 1, n do parts[i] = PZA.json(v[i], depth + 1) end
            return "[" .. table.concat(parts, ",") .. "]"
        end
        for k, val in pairs(v) do parts[#parts + 1] = jsonString(k) .. ":" .. PZA.json(val, depth + 1) end
        table.sort(parts)
        return "{" .. table.concat(parts, ",") .. "}"
    end
    return jsonString(tostring(v))
end

-- PZA.decode(s): one JSON value (the command file cmd.txt, ack.txt) as Lua, or nil on anything malformed. A
-- recursive descent over string.byte/sub/find with its depth capped at 32; every failure leaves through fail() (no
-- error, the text never compiled as Lua, so a bad file never raises on the -debug client). null is nil, so an object key holding null
-- is absent. \uXXXX is written as its UTF-8 bytes; Kahlua strings are Java strings, so a non-ASCII escape in a
-- command is best avoided (a surrogate pair is not combined).
local byte, sub, find, char, concat, floor = string.byte, string.sub, string.find, string.char, table.concat, math.floor
local DECODE_DEPTH = 32
local ESC = { ['"'] = '"', ["\\"] = "\\", ["/"] = "/", b = "\b", f = "\f", n = "\n", r = "\r", t = "\t" }

local function fail() return nil, nil end

local function at(s, p)
    if p > #s then return nil end
    return byte(s, p)
end

local function skip(s, p)
    return find(s, "[^ \t\r\n]", p) or (#s + 1)
end

local function utf8(c)
    if c < 128 then return char(c) end
    if c < 2048 then return char(192 + floor(c / 64), 128 + c % 64) end
    return char(224 + floor(c / 4096), 128 + floor(c / 64) % 64, 128 + c % 64)
end

local decodeValue

-- p at the opening quote; answers the string and the position after its closing quote
local function decodeString(s, p)
    local parts, n, i = {}, 0, p + 1
    while true do
        local q = find(s, '["\\]', i)
        if q == nil then return fail() end
        if q > i then
            n = n + 1
            parts[n] = sub(s, i, q - 1)
        end
        if byte(s, q) == 34 then return concat(parts), q + 1 end
        local e = sub(s, q + 1, q + 1)
        local r = ESC[e]
        if r ~= nil then
            n = n + 1
            parts[n] = r
            i = q + 2
        elseif e == "u" then
            local h = sub(s, q + 2, q + 5)
            if find(h, "^%x%x%x%x$") == nil then return fail() end
            n = n + 1
            parts[n] = utf8(tonumber(h, 16))
            i = q + 6
        else
            return fail()
        end
    end
end

local function decodeNumber(s, p)
    local a, b = find(s, "^-?%d+%.?%d*[eE]?[-+]?%d*", p)
    if a == nil then return fail() end
    local v = tonumber(sub(s, a, b))
    if v == nil then return fail() end
    return v, b + 1
end

local function decodeObject(s, p, depth)
    local t = {}
    p = skip(s, p + 1)
    if at(s, p) == 125 then return t, p + 1 end
    while true do
        if at(s, p) ~= 34 then return fail() end
        local k, v
        k, p = decodeString(s, p)
        if p == nil then return fail() end
        p = skip(s, p)
        if at(s, p) ~= 58 then return fail() end
        v, p = decodeValue(s, skip(s, p + 1), depth)
        if p == nil then return fail() end
        t[k] = v
        p = skip(s, p)
        local c = at(s, p)
        if c == 125 then return t, p + 1 end
        if c ~= 44 then return fail() end
        p = skip(s, p + 1)
    end
end

-- a null element leaves a hole (# stops there); command args never carry one
local function decodeArray(s, p, depth)
    local t, n = {}, 0
    p = skip(s, p + 1)
    if at(s, p) == 93 then return t, p + 1 end
    while true do
        local v
        v, p = decodeValue(s, p, depth)
        if p == nil then return fail() end
        n = n + 1
        t[n] = v
        p = skip(s, p)
        local c = at(s, p)
        if c == 93 then return t, p + 1 end
        if c ~= 44 then return fail() end
        p = skip(s, p + 1)
    end
end

-- answers the value and the position after it, or nil, nil (a null answers nil and a position)
decodeValue = function(s, p, depth)
    local c = at(s, p)
    if c == nil then return fail() end
    if c == 123 or c == 91 then
        if depth >= DECODE_DEPTH then return fail() end
        if c == 123 then return decodeObject(s, p, depth + 1) end
        return decodeArray(s, p, depth + 1)
    end
    if c == 34 then return decodeString(s, p) end
    if c == 45 or (c >= 48 and c <= 57) then return decodeNumber(s, p) end
    if sub(s, p, p + 3) == "true" then return true, p + 4 end
    if sub(s, p, p + 4) == "false" then return false, p + 5 end
    if sub(s, p, p + 3) == "null" then return nil, p + 4 end
    return fail()
end

function PZA.decode(s)
    if type(s) ~= "string" then return nil end
    local v, p = decodeValue(s, skip(s, 1), 0)
    if p == nil then return nil end
    if skip(s, p) <= #s then return nil end
    return v
end
