-- PZAgent_Link.lua — the file channel of PZA/1. Out: lines appended to Lua/pzagent/<user>/state.log (or chunk files
-- when append does not hold: ruling P21-1), one file write a flush and one flush a tick. Three writers share one seq:
-- PZA.emit (a keyed JSON line, into the immediate buffer), PZA.emitFrame (a positional frame, into the immediate
-- buffer; a full frame every FULL_EVERY frames, else each group whose encoding equals the last one sent is elided as
-- true) and L.queueMap / L.queueLine (a positional map part, or a keyed line that may wait such as the inventory's
-- first sight, into the backlog, which drains BUDGET_BYTES a flush and is capped at BACKLOG_MAX lines, the oldest cut
-- and L.overflow set for Main to emit once). In: cmd.txt as one JSON line read by
-- seq through PZA.decode; ack.txt holds {"seq":N}, the last accepted seq, so a Lua reset never replays a command.
-- The Lua writer is rooted at the cachedir's Lua folder and allows ini/cfg/txt/log/json only [#1866]. No writer is
-- held across ticks: every write opens, writes and closes.
PZA.link = PZA.link or {}
local L = PZA.link
L.ROTATE_BYTES = 8 * 1024 * 1024
L.BUDGET_BYTES = 1536
L.BACKLOG_MAX = 400
L.FULL_EVERY = 10
L.BUF_MAX = 2000
L.buf = {}
L.backlog = {}
L.bytes = 0
L.rot = 0
L.chunk = 0
L.seq = 0
L.lastCmd = 0
L.live = "state.log"
L.dropped = 0
L.badCmd = 0
L.lastBad = nil
L.frames = 0
L.lastFull = {}
L.forceFull = false
L.overflow = nil

local concat = table.concat

-- the frame's elidable groups in schema order (zombies is a record list, never a group, so never elided)
local GROUPS = {}
for _, f in ipairs(PZA.schema.order.frame) do
    if PZA.schema.groups[f] ~= nil then GROUPS[#GROUPS + 1] = f end
end

local function writeAll(name, s, append)
    local w = getFileWriter(name, true, append)
    if w == nil then PZA.log("cannot write " .. name); return false end
    local ok = PZA.call(w, "write", s)
    PZA.call(w, "close")
    return ok
end

-- the non-empty lines of a file, through one reader closed before returning
local function countLines(name)
    local r = getFileReader(name, false)
    if r == nil then return 0 end
    local n = 0
    while true do
        local ok, line = PZA.call(r, "readLine")
        if not ok or line == nil then break end
        if line ~= "" then n = n + 1 end
    end
    PZA.call(r, "close")
    return n
end

-- the first line holding a non-blank character, or nil (no file, or none); polled every tick, so no closure
local function firstLine(name)
    local r = getFileReader(name, false)
    if r == nil then return nil end
    local first
    while true do
        local ok, line = PZA.call(r, "readLine")
        if not ok or line == nil then break end
        if string.find(line, "%S") ~= nil then
            first = line
            break
        end
    end
    PZA.call(r, "close")
    return first
end

local function exists(name)
    local r = getFileReader(name, false)
    if r == nil then return false end
    PZA.call(r, "close")
    return true
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
    if exists(L.dir .. "state.log") then
        local n = 1
        while exists(L.dir .. "state." .. n .. ".log") do n = n + 1 end
        L.rot = n
        L.live = "state." .. n .. ".log"
    end
    L.frames = 0
    L.lastFull = {}
    L.forceFull = false
    local line = firstLine(L.dir .. "ack.txt")
    local ack = line and PZA.decode(line)
    L.lastCmd = (type(ack) == "table" and type(ack.seq) == "number") and ack.seq or 0
    PZA.log("link " .. L.mode .. " lastCmd=" .. tostring(L.lastCmd))
end

-- the envelope every PZA/1 line carries, one seq across every writer
local function stamp(kind, body)
    L.seq = L.seq + 1
    body.kind = kind
    body.seq = L.seq
    body.tick = PZA.tick or 0
    body.wallMs = PZA.now()
end

-- a keyed line (hello, event, act, reply), written at the next flush
function PZA.emit(kind, body)
    stamp(kind, body)
    L.buf[#L.buf + 1] = PZA.json(body)
end

-- a positional frame, written at the next flush. The elision base is the last sent encoding of each group: a group
-- written (every group in a full frame, a changed one in a delta) replaces it, so a reader merges each delta into
-- its running frame. A full frame when L.frames % FULL_EVERY == 1 (frames 1, 11, 21, ...) or L.forceFull is set.
function PZA.emitFrame(body)
    stamp("frame", body)
    L.frames = L.frames + 1
    local full = L.forceFull or L.FULL_EVERY <= 1 or (L.frames % L.FULL_EVERY == 1)
    L.forceFull = false
    local last, enc, same = L.lastFull, PZA.enc, {}
    for i = 1, #GROUPS do
        local g = GROUPS[i]
        local e = enc[g](body[g])
        if not full and e == last[g] then
            same[g] = true
        else
            last[g] = e
        end
    end
    L.buf[#L.buf + 1] = enc.frame(body, same)
end

-- a map part's body, into the backlog unstamped: L.flush stamps and encodes it as it is taken, so every line's seq
-- rises in file order (ruling S-11). At BACKLOG_MAX the oldest bodies are cut to make room and L.overflow records
-- the size before the cut and the parts cut (accumulating until Main emits it and clears it)
function L.queueMap(body)
    local bl = L.backlog
    local n = #bl
    if n >= L.BACKLOG_MAX then
        local cut = n - L.BACKLOG_MAX + 1
        local kept = {}
        for i = cut + 1, n do kept[#kept + 1] = bl[i] end
        bl = kept
        L.backlog = kept
        if L.overflow ~= nil then
            L.overflow.queued = n
            L.overflow.cut = L.overflow.cut + cut
        else
            L.overflow = { queued = n, cut = cut }
        end
    end
    bl[#bl + 1] = body
end

-- a keyed line's body (an event) into the backlog behind the map parts already there, unstamped like them: it drains
-- under the same budget, so a burst of keyed lines (the inventory's first sight, X4 fix pass 2.2) spreads over ticks
function L.queueLine(kind, body)
    body.kind = kind
    L.queueMap(body)
end

-- the one write of a flush: chunk mode a new chunk file, append mode the live file, rotated by name past ROTATE_BYTES
local function write(s)
    if L.mode == "chunk" then
        L.chunk = L.chunk + 1
        local ok = writeAll(L.dir .. string.format("state-%06.0f.log", L.chunk), s, false)
        if not ok then L.chunk = L.chunk - 1 end
        return ok
    end
    -- rotate by switching the live file name: no read-back, no rewrite
    if L.bytes + #s > L.ROTATE_BYTES and L.bytes > 0 then
        L.rot = L.rot + 1
        L.live = "state." .. L.rot .. ".log"
        L.bytes = 0
    end
    local ok = writeAll(L.dir .. L.live, s, true)
    if ok then L.bytes = L.bytes + #s end
    return ok
end

-- once a tick: the whole immediate buffer, then the backlog's lines from its front (map parts, positional; a queued
-- keyed line, as JSON), each stamped and encoded as it is taken (so its seq follows every line before it), while the encoded bytes fit BUDGET_BYTES (a single line over
-- the budget goes alone, so the backlog never stalls); one write. A part that does not fit gives its seq back. A
-- failed write gives the parts' seqs back and leaves both queues as they were, the immediate buffer capped at BUF_MAX
-- lines (L.dropped counts the cut, and the next frame is full, so a reader's base is never a frame it lost).
-- Answers the ms taken.
function L.flush()
    local buf, bl = L.buf, L.backlog
    local nb, nl = #buf, #bl
    if nb == 0 and nl == 0 then return 0 end
    local t0 = PZA.now()
    local out = {}
    for i = 1, nb do out[i] = buf[i] end
    local seq0 = L.seq
    local used, take = 0, 0
    while take < nl do
        local body = bl[take + 1]
        local kind = body.kind or "map"
        stamp(kind, body)
        local line = (kind == "map") and PZA.enc.map(body) or PZA.json(body)
        local size = #line
        if take > 0 and used + size > L.BUDGET_BYTES then
            L.seq = L.seq - 1
            break
        end
        take = take + 1
        used = used + size
        out[nb + take] = line
    end
    if write(concat(out, "\n") .. "\n") then
        L.buf = {}
        if take > 0 then
            local kept = {}
            for i = take + 1, nl do kept[#kept + 1] = bl[i] end
            L.backlog = kept
        end
    else
        L.seq = seq0
        while #L.buf > L.BUF_MAX do
            table.remove(L.buf, 1)
            L.dropped = L.dropped + 1
            L.forceFull = true
        end
    end
    return PZA.now() - t0
end

-- a command's seq: a finite integral number
local function goodSeq(seq)
    return type(seq) == "number" and seq == seq and seq ~= math.huge and seq ~= -math.huge and seq == math.floor(seq)
end

-- the command file: its first non-empty line as one JSON object with a good seq; a seq at or below lastCmd is old.
-- A malformed line is skipped and counted once in L.badCmd (polled again, not recounted until a good line between).
function L.poll()
    local line = firstLine(L.dir .. "cmd.txt")
    if line == nil then return nil end
    local c = PZA.decode(line)
    if type(c) ~= "table" or not goodSeq(c.seq) then
        if line ~= L.lastBad then
            L.lastBad = line
            L.badCmd = L.badCmd + 1
        end
        return nil
    end
    L.lastBad = nil
    local seq = c.seq
    if seq <= L.lastCmd then return nil end
    L.lastCmd = seq
    writeAll(L.dir .. "ack.txt", PZA.json({ seq = seq }) .. "\n", false)
    local args = c.args
    if type(args) ~= "table" then args = {} end
    return { seq = seq, aid = tostring(c.aid or ""), type = tostring(c.type or ""), args = args }
end
