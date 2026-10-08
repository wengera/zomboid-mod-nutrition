-- NR_Kernel_Json.lua -- a JSON codec for the server-local store (Plan 11 Task 10; Decision 3: the mod writes its own
-- serialiser). Pure: Lua values in, a string out, and back. A number is written by the caller's fmt (the adapter
-- passes tostring, which on Kahlua is Double.toString or a long below 1e14: a round trip, J2); a non-finite number
-- writes null. A table with keys exactly 1..#t (#t > 0) is an array, any other an object; an object's number key is
-- written "#<fmt(k)>" and read back as a number; a string key that starts with # gets one more # ("##5" reads "#5").
-- A table is an array only when t[1]..t[#t] are all present and no other key exists. A top-level non-table is unreadable. Decode answers nil and a message on malformed text.
local K = NutritionRevamp.kernel
K.json = {}

K.json.ESC = { ['"'] = '\\"', ['\\'] = '\\\\', ['\n'] = '\\n', ['\r'] = '\\r', ['\t'] = '\\t' }

-- A control byte (< 32) as a \u00XX escape; the digits come from a lookup, because %x on a float raises on Kahlua.
function K.json.ctl(b)
    local hi = math.floor(b / 16) + 1
    local lo = b % 16 + 1
    return "\\u00" .. string.sub("0123456789abcdef", hi, hi) .. string.sub("0123456789abcdef", lo, lo)
end

function K.json.str(s)
    local out = {}
    for i = 1, string.len(s) do
        local c = string.sub(s, i, i)
        local e = K.json.ESC[c]
        if e ~= nil then
            out[#out + 1] = e
        elseif string.byte(c) < 32 then
            out[#out + 1] = K.json.ctl(string.byte(c))
        else
            out[#out + 1] = c
        end
    end
    return '"' .. table.concat(out) .. '"'
end

function K.json.isArray(t)
    local n = #t
    if n == 0 then
        return false
    end
    local count = 0
    for _ in pairs(t) do
        count = count + 1
    end
    return count == n and K.json.dense(t, n)
end

-- True when t[1]..t[n] are all present (no branch inside the loop body, for the line-hook coverage gate).
function K.json.dense(t, n)
    local ok = true
    for i = 1, n do
        ok = ok and t[i] ~= nil
    end
    return ok
end

function K.json.emit(v, fmt, out)
    local tv = type(v)
    if tv == "number" then
        if v ~= v or v == math.huge or v == -math.huge then
            out[#out + 1] = "null"
        else
            out[#out + 1] = fmt(v)
        end
    elseif tv == "boolean" then
        out[#out + 1] = tostring(v)
    elseif tv == "string" then
        out[#out + 1] = K.json.str(v)
    elseif tv == "table" then
        K.json.emitTable(v, fmt, out)
    else
        out[#out + 1] = "null"
    end
end

function K.json.emitTable(t, fmt, out)
    if K.json.isArray(t) then
        out[#out + 1] = "["
        for i = 1, #t do
            if i > 1 then
                out[#out + 1] = ","
            end
            K.json.emit(t[i], fmt, out)
        end
        out[#out + 1] = "]"
        return
    end
    out[#out + 1] = "{"
    local first = true
    for k, x in pairs(t) do
        first = K.json.member(k, x, fmt, out, first)
    end
    out[#out + 1] = "}"
end

-- One object member: a number key written "#<fmt(k)>", a string key as is, any other key skipped. Returns the
-- next member's first flag. (A pairs loop whose body ends in an if leaves that end unexecuted under the line
-- hook, so the branching lives here.)
function K.json.member(k, x, fmt, out, first)
    local key = k
    if type(k) == "number" then
        key = "#" .. fmt(k)
    elseif type(k) == "string" and string.sub(k, 1, 1) == "#" then
        key = "#" .. k
    end
    if type(key) ~= "string" then
        return first
    end
    if not first then
        out[#out + 1] = ","
    end
    out[#out + 1] = K.json.str(key)
    out[#out + 1] = ":"
    K.json.emit(x, fmt, out)
    return false
end

function K.json.encode(v, fmt)
    local out = {}
    K.json.emit(v, fmt, out)
    return table.concat(out)
end

-- Decoding: a cursor over the text; every reader returns value, next position, or nil, position, message.
function K.json.skip(s, i)
    local j = string.find(s, "[^ \t\r\n]", i)
    if j == nil then
        return string.len(s) + 1
    end
    return j
end

function K.json.readValue(s, i)
    i = K.json.skip(s, i)
    local c = string.sub(s, i, i)
    if c == "{" then
        return K.json.readObject(s, i + 1)
    end
    if c == "[" then
        return K.json.readArray(s, i + 1)
    end
    if c == '"' then
        return K.json.readString(s, i + 1)
    end
    if string.sub(s, i, i + 3) == "true" then
        return true, i + 4
    end
    if string.sub(s, i, i + 4) == "false" then
        return false, i + 5
    end
    if string.sub(s, i, i + 3) == "null" then
        return nil, i + 4
    end
    local a, b = string.find(s, "^-?[0-9][0-9.eE+-]*", i)
    if a == nil then
        return nil, i, "json: unexpected character at " .. tostring(i)
    end
    local n = tonumber(string.sub(s, a, b))
    if n == nil then
        return nil, i, "json: bad number at " .. tostring(i)
    end
    return n, b + 1
end

K.json.UNESC = { ['"'] = '"', ['\\'] = '\\', ['/'] = '/', ['n'] = '\n', ['r'] = '\r', ['t'] = '\t', ['b'] = '\b', ['f'] = '\f' }

function K.json.readString(s, i)
    local out = {}
    local len = string.len(s)
    while i <= len do
        local c = string.sub(s, i, i)
        if c == '"' then
            return table.concat(out), i + 1
        end
        if c == "\\" then
            local e = string.sub(s, i + 1, i + 1)
            if e == "u" then
                local code = tonumber(string.sub(s, i + 2, i + 5), 16)
                if code == nil then
                    return nil, i, "json: bad escape at " .. tostring(i)
                end
                out[#out + 1] = string.char(code % 256)
                i = i + 6
            else
                local r = K.json.UNESC[e]
                if r == nil then
                    return nil, i, "json: bad escape at " .. tostring(i)
                end
                out[#out + 1] = r
                i = i + 2
            end
        else
            out[#out + 1] = c
            i = i + 1
        end
    end
    return nil, i, "json: unterminated string"
end

function K.json.keyOf(k)
    if string.sub(k, 1, 2) == "##" then
        return string.sub(k, 2)
    end
    if string.sub(k, 1, 1) == "#" then
        local n = tonumber(string.sub(k, 2))
        if n ~= nil then
            return n
        end
    end
    return k
end

function K.json.readObject(s, i)
    local t = {}
    i = K.json.skip(s, i)
    if string.sub(s, i, i) == "}" then
        return t, i + 1
    end
    while true do
        i = K.json.skip(s, i)
        if string.sub(s, i, i) ~= '"' then
            return nil, i, "json: expected a key at " .. tostring(i)
        end
        local k, j, err = K.json.readString(s, i + 1)
        if k == nil then
            return nil, j, err
        end
        j = K.json.skip(s, j)
        if string.sub(s, j, j) ~= ":" then
            return nil, j, "json: expected : at " .. tostring(j)
        end
        local v, after, errV = K.json.readValue(s, j + 1)
        if errV ~= nil then
            return nil, after, errV
        end
        t[K.json.keyOf(k)] = v
        after = K.json.skip(s, after)
        local c = string.sub(s, after, after)
        if c == "}" then
            return t, after + 1
        end
        if c ~= "," then
            return nil, after, "json: expected , or } at " .. tostring(after)
        end
        i = after + 1
    end
end

function K.json.readArray(s, i)
    local t = {}
    i = K.json.skip(s, i)
    if string.sub(s, i, i) == "]" then
        return t, i + 1
    end
    local n = 0
    while true do
        local v, after, errV = K.json.readValue(s, i)
        if errV ~= nil then
            return nil, after, errV
        end
        n = n + 1
        t[n] = v
        after = K.json.skip(s, after)
        local c = string.sub(s, after, after)
        if c == "]" then
            return t, after + 1
        end
        if c ~= "," then
            return nil, after, "json: expected , or ] at " .. tostring(after)
        end
        i = after + 1
    end
end

function K.json.decode(text)
    if type(text) ~= "string" or text == "" then
        return nil, "json: empty text"
    end
    local v, i, err = K.json.readValue(text, 1)
    if err ~= nil then
        return nil, err
    end
    i = K.json.skip(text, i)
    if i <= string.len(text) then
        return nil, "json: trailing text at " .. tostring(i)
    end
    if type(v) ~= "table" then
        return nil, "json: not a record"
    end
    return v, nil
end
