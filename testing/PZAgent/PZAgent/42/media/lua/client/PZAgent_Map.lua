-- PZAgent_Map.lua — the map (spec § 2.1, Plan 22 Task 6): the squares round the player from first sight, sent as PZA/1
-- map lines through the Link's backlog (L.queueMap: unstamped bodies the flush stamps and drains BUDGET_BYTES a tick).
-- Two writers, one at a time (Main steps the scan job while one runs, else the watch):
--   the scan job (moved from Sense): scan{r} walks the (2r+1)^2 grid SCAN_SQUARES_PER_TICK squares a tick, each part
--   queued as a map line in mode "full" { scanId, part, parts, squares, missing };
--   the watch, a dirty set: each tick the next WATCH_PER_TICK squares of the (2 WATCH_R + 1)^2 ring round the player
--   (by index, cycling) are read, and a square whose dirty key differs from the last one emitted (MP.seen; a key
--   never seen counts as changed) is queued as a one-square map line in mode "delta"
--   { scanId = 0, part = 1, parts = 1 }, at most once every DELTA_MIN_TICKS ticks a square (MP.lastDelta).
-- The dirty key is the square's encoding without light (ruling S-14, MP.watchKey): the dirty set means a world change
-- (walls, doors, windows, containers, floor), and an unrounded light level would dirty most of the ring at every
-- lighting drift and fill the budget with deltas; an emitted line still carries the real light.
-- MP.seen holds the dirty key of every square ever emitted (full or delta) and MP.lastDelta the tick of every delta, both
-- unbounded: a session sees a few thousand squares, about 100 bytes of string each. Every Java member is reached
-- through PZA.call (index-first); a member a square lacks is named in the part's missing list, never nil-called.
PZA.map = PZA.map or {}
local MP = PZA.map
MP.WATCH_R = 6              -- tiles: the watch's ring is (2 * 6 + 1)^2 = 169 squares, a cycle of 22 ticks
MP.WATCH_PER_TICK = 8
MP.DELTA_MIN_TICKS = 30
MP.seen = {}
MP.lastDelta = {}
MP.watchIdx = 0
MP.missing = {}             -- the members the watch's squares lacked (a delta line carries an empty list)

local function getm(miss, out, key, obj, member, ...)
    local ok, v = PZA.call(obj, member, ...)
    if ok then out[key] = v else PZA.missing(miss, member) end
    return ok, v
end

function MP.key(x, y, z)
    return x .. "," .. y .. "," .. z
end

local function objectsOf(sq)
    local out = {}
    local _, list = PZA.call(sq, "getObjects")
    local okN, n = PZA.call(list, "size")
    if not okN or type(n) ~= "number" then return out end
    for i = 0, n - 1 do local _, o = PZA.call(list, "get", i); if o ~= nil then out[#out + 1] = o end end
    return out
end

local function isA(o, cls)
    return instanceof ~= nil and instanceof(o, cls) == true
end

-- door, window or neither, by type first: IsoWindow and IsoThumpable also answer IsOpen/isLocked/isBarricaded
local function kindOf(o)
    if isA(o, "IsoDoor") then return "door" end
    if isA(o, "IsoWindow") then return "window" end
    if isA(o, "IsoThumpable") then
        local _, d = PZA.call(o, "isDoor")
        if d == true then return "door" end
        local _, w = PZA.call(o, "isWindow")
        if w == true then return "window" end
    end
    return nil
end

local function containersOf(o, missing)
    local out, list = {}, {}
    local okN, cn = PZA.call(o, "getContainerCount")
    if okN and type(cn) == "number" then
        for i = 0, cn - 1 do local _, c = PZA.call(o, "getContainerByIndex", i); if c ~= nil then list[#list + 1] = c end end
    else
        local okC, c = PZA.call(o, "getContainer")
        if okC and c ~= nil then list[1] = c end
    end
    for _, c in ipairs(list) do
        local ct = { items = {} }
        getm(missing, ct, "type", c, "getType")
        local okG, items = PZA.call(c, "getItems")
        local okS, n = PZA.call(items, "size")
        if not okG then PZA.missing(missing, "getItems") elseif not okS then PZA.missing(missing, "size") end
        ct.n = (okS and type(n) == "number") and n or 0
        for i = 0, ct.n - 1 do local _, it = PZA.call(items, "get", i); local _, ft = PZA.call(it, "getFullType"); ct.items[#ct.items + 1] = ft or "?" end
        out[#out + 1] = ct
    end
    return out
end

-- one square as the schema's square record: x, y, z, solid, solidTrans, light, room, building, door and window (a
-- portal { open, locked, barricaded } or nil), containers ({ type, n, items } each, items full types) and floor (the
-- full types of its world items); a member the square lacks leaves its field nil and its name in missing
function MP.square(sq, missing)
    local q = { containers = {}, floor = {} }
    getm(missing, q, "x", sq, "getX"); getm(missing, q, "y", sq, "getY"); getm(missing, q, "z", sq, "getZ")
    getm(missing, q, "solid", sq, "isSolid"); getm(missing, q, "solidTrans", sq, "isSolidTrans"); getm(missing, q, "light", sq, "getLightLevel", 0)
    local okR, room = PZA.call(sq, "getRoom"); if okR and room ~= nil then local _, nm = PZA.call(room, "getName"); q.room = nm end
    local okB, b = PZA.call(sq, "getBuilding"); if okB and b ~= nil then local _, id = PZA.call(b, "getID"); q.building = id end
    local objs = objectsOf(sq)
    for _, o in ipairs(objs) do
        local cts = containersOf(o, missing)
        for _, ct in ipairs(cts) do q.containers[#q.containers + 1] = ct end
        local kind = kindOf(o)
        if kind ~= nil then
            local _, open = PZA.call(o, "IsOpen")
            local _, locked = PZA.call(o, "isLocked")
            local _, barr = PZA.call(o, "isBarricaded")
            q[kind] = { open = open == true, locked = locked == true, barricaded = barr == true }
        end
    end
    local _, wl = PZA.call(sq, "getWorldObjects")
    local okW, wn = PZA.call(wl, "size")
    for i = 0, ((okW and type(wn) == "number") and wn or 0) - 1 do
        local _, wo = PZA.call(wl, "get", i); local _, it = PZA.call(wo, "getItem"); local _, ft = PZA.call(it, "getFullType")
        if ft ~= nil then q.floor[#q.floor + 1] = ft end
    end
    return q
end

-- the dirty key of a square record: its PZA.enc.square encoding with light left out (ruling S-14); q is left as it was
function MP.watchKey(q)
    local light = q.light
    q.light = nil
    local e = PZA.enc.square(q)
    q.light = light
    return e
end

-- the dirty key a square was last emitted with, by its key (a square without a readable position is never keyed)
local function remember(q)
    if q.x == nil or q.y == nil or q.z == nil then return nil end
    local key = MP.key(q.x, q.y, q.z)
    MP.seen[key] = MP.watchKey(q)
    return key
end

-- the player's position, or nil when any of x, y, z cannot be read as a number
local function posOf(p)
    local okX, x = PZA.call(p, "getX")
    local okY, y = PZA.call(p, "getY")
    local okZ, z = PZA.call(p, "getZ")
    if not (okX and okY and okZ) or type(x) ~= "number" or type(y) ~= "number" or type(z) ~= "number" then return nil end
    return x, y, z
end

-- The scan is a job walked SCAN_SQUARES_PER_TICK squares a tick (Stage A pass 1 read r=15, 961 squares, at
-- 14-21 ms in one tick) and sent in parts, one per tick (Stage A pass 2 read the completing tick's emit of the
-- whole r=15 line, 99.3 KB, at 45 ms: about 0.45 ms per KB of PZA.json and append, so the line is cut where the walk
-- is). scanStart fixes the (2r+1)^2 grid at the player's square at start and gives the job the next scanId; scanStep
-- walks the next chunk row by row, queues it as a map line (mode "full") and returns it as a part: { scanId, r, hour,
-- part (1-based), parts (the job's ceil(n / SCAN_SQUARES_PER_TICK), fixed at start), squares (the found squares of this
-- chunk), stepMs (this tick's walk ms), missing (the members this chunk's squares lacked) }; the last part also carries
-- done = true, scanMs (the summed stepMs), scanTicks, scanMsPerTick (each part's stepMs) and scanStepMaxMs (its
-- largest). One job at a time: a start replaces it, and the replaced job's parts stop.
-- 20 squares a part (Stage A pass 3, testing/artifacts/a_pipe_3-20261026-130558/GUIDE.md § 1): 60-square parts read
-- 3-7 ms a tick, the walk about 1 ms beside an emit of about 0.5 ms per KB plus about 0.5 ms a line; a 20-square part
-- projects to about 4.1-4.5 ms peak.
MP.SCAN_SQUARES_PER_TICK = 20
MP.job = nil
MP.scanId = 0

-- a job over the (2r+1)^2 grid at the player's square, or nil when the player's position cannot be read
local function newJob(p, r, id)
    local x, y, z = posOf(p)
    if x == nil then return nil end
    local side = 2 * r + 1
    local n = side * side
    local gameMin = PZA.sense ~= nil and PZA.sense.clock ~= nil and PZA.sense.clock() or 0
    return { id = id, r = r, side = side, i = 0, n = n, parts = math.ceil(n / MP.SCAN_SQUARES_PER_TICK),
             hour = math.floor(gameMin / 60), ms = 0, ticks = 0, steps = {},
             px = math.floor(x), py = math.floor(y), pz = z }
end

-- walks job's next chunk and returns it as a part; the last part carries done and the job's totals
local function stepJob(job)
    local t0 = PZA.now()
    local cell = getCell and getCell() or nil
    local stop = math.min(job.n, job.i + MP.SCAN_SQUARES_PER_TICK)
    local part = { scanId = job.id, r = job.r, hour = job.hour, part = job.ticks + 1, parts = job.parts,
                   squares = {}, missing = {} }
    while job.i < stop do
        local i = job.i
        local dy = math.floor(i / job.side) - job.r
        local dx = i % job.side - job.r
        local _, sq = PZA.call(cell, "getGridSquare", job.px + dx, job.py + dy, job.pz)
        if sq ~= nil then part.squares[#part.squares + 1] = MP.square(sq, part.missing) end
        job.i = i + 1
    end
    local dt = PZA.now() - t0
    job.ms, job.ticks = job.ms + dt, job.ticks + 1
    job.steps[job.ticks] = dt
    part.stepMs = dt
    if job.i < job.n then return part end
    local top = 0
    for k = 1, job.ticks do top = math.max(top, job.steps[k]) end
    part.done = true
    part.scanMs, part.scanTicks, part.scanMsPerTick, part.scanStepMaxMs = job.ms, job.ticks, job.steps, top
    return part
end

-- starts a job under the next scanId (a running one is replaced); answers its parts, or nil when the player's
-- position cannot be read (no job, no id taken)
function MP.scanStart(p, r)
    local job = newJob(p, r, MP.scanId + 1)
    if job == nil then return nil end
    MP.scanId = job.id
    MP.job = job
    return job.parts
end

-- one chunk of the running job, queued as its full map line and remembered in MP.seen, returned as its part (the last
-- one carrying done), else nil when no job runs
function MP.scanStep(p)
    local job = MP.job
    if job == nil then return nil end
    local part = stepJob(job)
    if part.done then MP.job = nil end
    for _, q in ipairs(part.squares) do remember(q) end
    PZA.link.queueMap({ mode = "full", scanId = part.scanId, part = part.part, parts = part.parts,
                        squares = part.squares, missing = part.missing })
    return part
end

-- the synchronous form, for tests: its own job (no scanId taken, nothing queued, MP.seen untouched), stepped to the end
-- and reassembled into pass 2's whole scan { r, hour, squares, missing (the parts' union), scanMs, scanTicks,
-- scanMsPerTick, scanStepMaxMs }; a running MP.job is left alone
function MP.scan(p, r)
    local job = newJob(p, r, 0)
    if job == nil then return nil end
    local out = { r = r, hour = job.hour, squares = {}, missing = {} }
    local part = nil
    while part == nil or not part.done do
        part = stepJob(job)
        for _, q in ipairs(part.squares) do out.squares[#out.squares + 1] = q end
        for _, m in ipairs(part.missing) do PZA.missing(out.missing, m) end
    end
    out.scanMs, out.scanTicks, out.scanMsPerTick, out.scanStepMaxMs = part.scanMs, part.scanTicks, part.scanMsPerTick,
        part.scanStepMaxMs
    return out
end

-- the watch: the next WATCH_PER_TICK squares of the ring round the player's square (MP.watchIdx cycling over its
-- (2 WATCH_R + 1)^2 indexes, row by row, the ring re-centred each tick), each read and queued as a delta when its
-- dirty key (MP.watchKey: the encoding without light) is not MP.seen's and its last delta is DELTA_MIN_TICKS ticks
-- old or more (a held change is read again on a later cycle). An absent square still takes its index. Answers the
-- deltas queued.
function MP.watchStep(p)
    local x, y, z = posOf(p)
    if x == nil then return 0 end
    local cell = getCell and getCell() or nil
    local r = MP.WATCH_R
    local side = 2 * r + 1
    local n = side * side
    local px, py = math.floor(x), math.floor(y)
    local tick = PZA.tick or 0
    local seen, last, watchKey = MP.seen, MP.lastDelta, MP.watchKey
    local queued = 0
    for _ = 1, MP.WATCH_PER_TICK do
        local i = MP.watchIdx % n
        MP.watchIdx = (i + 1) % n
        local _, sq = PZA.call(cell, "getGridSquare", px + i % side - r, py + math.floor(i / side) - r, z)
        if sq ~= nil then
            local q = MP.square(sq, MP.missing)
            if q.x ~= nil and q.y ~= nil and q.z ~= nil then
                local key = MP.key(q.x, q.y, q.z)
                local e = watchKey(q)
                local at = last[key]
                if e ~= seen[key] and (at == nil or tick - at >= MP.DELTA_MIN_TICKS) then
                    seen[key] = e
                    last[key] = tick
                    PZA.link.queueMap({ mode = "delta", scanId = 0, part = 1, parts = 1, squares = { q }, missing = {} })
                    queued = queued + 1
                end
            end
        end
    end
    return queued
end
