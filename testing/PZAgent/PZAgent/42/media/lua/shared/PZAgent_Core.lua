-- PZAgent_Core.lua — the PZA table. Loads first (shared/). No PZTestKit anywhere in this mod.
-- Every Java member is reached through PZA.call / PZA.field: an unguarded nil call on a -debug client
-- parks the process in the Lua debugger (platform/lua-platform.md#debug-break), and pcall names nothing.
PZA = PZA or {}
PZA.VERSION = "0.1"

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

local function jsonString(s)
    s = tostring(s)
    s = s:gsub('\\', '\\\\'):gsub('"', '\\"'):gsub('\n', '\\n'):gsub('\r', '\\r'):gsub('\t', '\\t')
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

function PZA.readKV(name)
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
