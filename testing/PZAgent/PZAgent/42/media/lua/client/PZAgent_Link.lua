-- PZAgent_Link.lua — the file channel. Out: JSON lines appended to Lua/pzagent/<user>/state.log
-- (or chunk files when append does not hold: ruling P21-1). In: cmd.txt as key=value lines, read by
-- seq (ruling P21-0); ack.txt holds the last accepted seq so a Lua reset never replays a command.
-- The Lua writer is rooted at the cachedir's Lua folder and allows ini/cfg/txt/log/json only [#1866].
PZA.link = PZA.link or {}
local L = PZA.link
L.ROTATE_BYTES = 8 * 1024 * 1024
L.buf = {}
L.bytes = 0
L.rot = 0
L.chunk = 0
L.seq = 0
L.lastCmd = 0
L.live = "state.log"
L.dropped = 0

local function writeAll(name, s, append)
    local w = getFileWriter(name, true, append)
    if not w then PZA.log("cannot write " .. name); return false end
    w:write(s)
    w:close()
    return true
end

local function countLines(name)
    local r = getFileReader(name, false)
    if not r then return 0 end
    local n = 0
    while true do
        local line = r:readLine()
        if line == nil then break end
        if line ~= "" then n = n + 1 end
    end
    r:close()
    return n
end

function L.init(user)
    L.user = user
    L.dir = "pzagent/" .. user .. "/"
    local probe = L.dir .. "probe.log"
    writeAll(probe, "1\n", false)
    writeAll(probe, "2\n", true)
    L.mode = (countLines(probe) == 2) and "append" or "chunk"
    L.live = "state.log"
    L.rot = 0
    L.bytes = 0
    local prev = getFileReader(L.dir .. "state.log", false)
    if prev then
        prev:close()
        local n = 1
        while true do
            local r = getFileReader(L.dir .. "state." .. n .. ".log", false)
            if not r then break end
            r:close()
            n = n + 1
        end
        L.rot = n
        L.live = "state." .. n .. ".log"
    end
    local ack = PZA.readKV(L.dir .. "ack.txt")
    L.lastCmd = (ack and tonumber(ack.seq)) or 0
    PZA.log("link " .. L.mode .. " lastCmd=" .. tostring(L.lastCmd))
end

function PZA.emit(kind, body)
    L.seq = L.seq + 1
    body.kind = kind
    body.seq = L.seq
    body.tick = PZA.tick or 0
    body.wallMs = PZA.now()
    L.buf[#L.buf + 1] = PZA.json(body)
end

function L.flush()
    if #L.buf == 0 then return 0 end
    local t0 = PZA.now()
    local s = table.concat(L.buf, "\n") .. "\n"
    L.buf = {}
    local ok
    if L.mode == "chunk" then
        L.chunk = L.chunk + 1
        ok = writeAll(L.dir .. string.format("state-%06.0f.log", L.chunk), s, false)
        if not ok then L.chunk = L.chunk - 1 end
    else
        -- rotate by switching the live file name: no read-back, no rewrite
        if L.bytes + #s > L.ROTATE_BYTES and L.bytes > 0 then
            L.rot = L.rot + 1
            L.live = "state." .. L.rot .. ".log"
            L.bytes = 0
        end
        ok = writeAll(L.dir .. L.live, s, true)
        if ok then L.bytes = L.bytes + #s end
    end
    if not ok then
        table.insert(L.buf, 1, string.sub(s, 1, -2))
        while #L.buf > 2000 do
            table.remove(L.buf, 1)
            L.dropped = L.dropped + 1
        end
    end
    return PZA.now() - t0
end

function L.poll()
    local c = PZA.readKV(L.dir .. "cmd.txt")
    if not c then return nil end
    local seq = tonumber(c.seq)
    if not seq or seq <= L.lastCmd then return nil end
    L.lastCmd = seq
    writeAll(L.dir .. "ack.txt", "seq=" .. string.format("%.0f", seq) .. "\n", false)
    return { seq = seq, goal = c.goal or "", args = c.args or "" }
end

function L.ack(seq, ok, reason)
    PZA.emit("ack", { cmdSeq = seq, ok = ok, reason = reason or "" })
end
