-- PZAgent_Bench.lua — the emit arms the harness times on the client (Plan 22 probe X2, interface § 5): each
-- PZA.bench.<name> is a plain function of no arguments that `bench.global PZA.bench.<name> <n>` calls n times. PART is
-- a synthetic scan part built once at load from literals (no game object), 20 squares in the shape PZAgent_Sense.lua's
-- square() writes: 2 squares with one container of 3 items, 1 with a door table, the rest bare. S21 is its PZA.json,
-- prebuilt; S20 a 20-byte string. The bench file is the link's dir's bench.log (pzagent/<user>/bench.log), resolved at
-- call time, pzagent/bench.log before the link is initialised; every write appends. Every function tolerates a nil
-- writer (it returns without raising), and every writer member is reached through PZA.call.
PZA.bench = PZA.bench or {}
local B = PZA.bench
B.w = nil

local function bare(x, y, light, room, building)
    return { x = x, y = y, z = 0, solid = false, solidTrans = false, light = light, room = room, building = building,
             containers = {}, floor = {} }
end

local function buildPart()
    local sq = {}
    for i = 0, 19 do
        local x, y = 10640 + i % 5, 9810 + math.floor(i / 5)
        if i < 10 then
            sq[#sq + 1] = bare(x, y, 0.6328125 + i / 1000, "kitchen", 4127)
        else
            sq[#sq + 1] = bare(x, y, 0.8046875 - i / 1000, nil, nil)
        end
    end
    sq[3].containers = { { type = "fridge", n = 3, items = { "Base.Milk", "Base.Cheese", "Base.Apple" } } }
    sq[7].containers = { { type = "counter", n = 3, items = { "Base.TinnedBeans", "Base.WaterBottle", "Base.Bandage" } } }
    sq[11].door = { open = false, locked = true, barricaded = false }
    sq[11].floor = { "Base.Plank" }
    return { scanId = 1, r = 15, hour = 7, part = 1, parts = 49, squares = sq, missing = {}, stepMs = 1 }
end

local PART = buildPart()
local S21 = PZA.json(PART)
local S20 = "0123456789abcdefghi\n"

-- PZA.json with its table.sort removed (the order pairs gives)
local function jsonString(s)
    s = tostring(s)
    s = s:gsub('\\', '\\\\'):gsub('"', '\\"'):gsub('\n', '\\n'):gsub('\r', '\\r'):gsub('\t', '\\t')
    return '"' .. s .. '"'
end

local function jsonNoSort(v, depth)
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
            for i = 1, n do parts[i] = jsonNoSort(v[i], depth + 1) end
            return "[" .. table.concat(parts, ",") .. "]"
        end
        for k, val in pairs(v) do parts[#parts + 1] = jsonString(k) .. ":" .. jsonNoSort(val, depth + 1) end
        return "{" .. table.concat(parts, ",") .. "}"
    end
    return jsonString(tostring(v))
end

-- a positional value: nil is null, a string quoted, anything else tostring
local function cval(v)
    if v == nil then return "null" end
    if type(v) == "string" then return jsonString(v) end
    return tostring(v)
end

local function clist(list)
    local s = ""
    for i = 1, #list do
        if i > 1 then s = s .. "," end
        s = s .. cval(list[i])
    end
    return "[" .. s .. "]"
end

-- the positional encoder: each square as [x,y,z,solid,solidTrans,light,room,building,[containers...],[floor...]], a
-- container as [type,n,[items...]], built by string concatenation with no sort (the door table is not carried)
local function compact(part)
    local s = ""
    for i = 1, #part.squares do
        local q = part.squares[i]
        local cs = ""
        for j = 1, #q.containers do
            local c = q.containers[j]
            if j > 1 then cs = cs .. "," end
            cs = cs .. "[" .. cval(c.type) .. "," .. cval(c.n) .. "," .. clist(c.items) .. "]"
        end
        if i > 1 then s = s .. "," end
        s = s .. "[" .. cval(q.x) .. "," .. cval(q.y) .. "," .. cval(q.z) .. "," .. cval(q.solid) .. "," ..
            cval(q.solidTrans) .. "," .. cval(q.light) .. "," .. cval(q.room) .. "," .. cval(q.building) .. ",[" ..
            cs .. "]," .. clist(q.floor) .. "]"
    end
    return "[" .. s .. "]"
end

-- the bench file, resolved at call time
local function benchFile()
    local L = PZA.link
    if L ~= nil and L.dir ~= nil then return L.dir .. "bench.log" end
    return "pzagent/bench.log"
end

local function open()
    if getFileWriter == nil then return nil end
    return getFileWriter(benchFile(), true, true)
end

function B.json() return PZA.json(PART) end
function B.jsonNoSort() return jsonNoSort(PART) end
function B.compact() return compact(PART) end

function B.openWrite()
    local w = open()
    if w == nil then return end
    PZA.call(w, "write", S21)
    PZA.call(w, "close")
end

function B.openWrite20()
    local w = open()
    if w == nil then return end
    PZA.call(w, "write", S20)
    PZA.call(w, "close")
end

function B.openOnly()
    local w = open()
    if w == nil then return end
    PZA.call(w, "close")
end

function B.heldOpen() B.w = open() end
function B.heldWrite() PZA.call(B.w, "write", S21) end

function B.heldClose()
    PZA.call(B.w, "close")
    B.w = nil
end

function B.poll()
    if getFileReader == nil then return nil end
    local L = PZA.link
    local dir = (L ~= nil and L.dir ~= nil) and L.dir or "pzagent/"
    return PZA.readKV(dir .. "cmd.txt")
end

function B.concat() return table.concat({ S21 }, "\n") end

-- the sizes Main's init emits as its bench line: a fresh table each call (PZA.emit stamps its body)
function B.sizes()
    local c, ns = compact(PART), jsonNoSort(PART)
    return { json21Bytes = #S21, compactBytes = #c, noSortBytes = #ns, squares = #PART.squares }
end
