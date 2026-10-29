-- PZAgent_Map.lua — the map (spec § 2.1, Plan 22 Task 6): the squares round the player from first sight, sent as PZA/1
-- map lines through the Link's backlog (L.queueMap: unstamped bodies the flush stamps and drains BUDGET_BYTES a tick).
-- Two writers, one at a time (Main steps the scan job while one runs, else the watch):
--   the scan job (moved from Sense): scan{r} walks the (2r+1)^2 grid SCAN_SQUARES_PER_TICK squares a tick, each part
--   queued as a map line in mode "full" { scanId, part, parts, squares, missing };
--   the watch, a dirty set: on every WATCH_EVERY-th tick (MP.watchDue: the 10 Hz frame tick whatever S.RATE, so at
--   60 Hz its cost a tick falls by the rate ratio; X4 fix pass, review I7) the next WATCH_PER_FRAME squares of the
--   (2 WATCH_R + 1)^2 ring round the player (by index, cycling) are fingerprinted (MP.fingerprint: the solid flags,
--   each portal's kind and states, each container's item count, the object and floor counts, the four edges), and only a square whose
--   fingerprint differs from the one stored for it (MP.fp; none stored counts as changed) is read whole (MP.square);
--   one whose dirty key differs from the last one emitted (MP.seen; a key never seen counts as changed) is queued as a
--   one-square map line in mode "delta" { scanId = 0, part = 1, parts = 1 }, at most once every DELTA_MIN_TICKS ticks
--   a square (MP.lastDelta). The fingerprint is stored once the whole read agrees with MP.seen or its delta is
--   queued, so a held change is read again on a later cycle. A change the fingerprint cannot see (an item swapped for
--   another in a container or on the floor, the count unchanged; a room or building change) waits for the next scan.
-- The square record's four edges (PZA/1.2, Plan 23 Task 6, ruling P23-K) are blockN and blockW, the square's
-- isBlockedTo its north (x, y - 1) and west (x - 1, y) neighbour off the cell, and edgeN and edgeW, its isSomethingTo
-- the same neighbours; an unloaded neighbour leaves its side's two nil and names neighbourN or neighbourW in missing,
-- and the fingerprint carries all four, so a door closing on an edge dirties its square.
-- The jar read (docs/superpowers/specs/2026-10-28-plan-23-jar-reads.md § 1) found a square stores only its own north
-- and west edges, which both predicates read for those neighbours: a wall, a closed or barricaded door, an intact
-- closed window or a stair edge blocks, an open door does not.
-- The record's hopN and hopW (PZA/1.4, ruling P24-C; docs/superpowers/specs/2026-10-29-plan-24-jar-reads.md § 1) are
-- the square's own merged flags sq:has(IsoFlagType.HoppableN) and has(IsoFlagType.HoppableW), as vanilla's
-- ISClimbOverFence.lua:48 reads them: a low fence loads with its edge's collide flag, so blockN/blockW read it blocked,
-- while the path follower climbs any edge carrying the flag at a walk (a solid wall on the same edge unsets it). They
-- need no neighbour, so a square without one still reads them; an absent IsoFlagType constant is named in missing. They
-- ride the scan and the delta (the dirty key is the record's encoding) and are left out of the fingerprint, whose
-- edges already change when a fence lands (its collide flag blocks the edge), so the watch reads no more per square.
-- The record's water (PZA/1.5, ruling P24-G; docs/superpowers/specs/2026-10-29-plan-24-jar-reads-2.md section 7,
-- T6b.10) is the square's first object whose hasWater() holds as { amount (getFluidAmount: 10000 for an infinite
-- source), tainted (isTaintedWater), infinite (getFluidCapacity at 10000: waterOf) }, nil when none: a sink or a
-- toilet in a room, a bath, a well, a rain collector, a river, a puddle. It rides the scan and the delta like the door
-- record and is left out of the fingerprint (one more call per object a watch step), so a source drying or a puddle
-- forming waits for the next scan or a square's whole read for another change.
-- The dirty key is the square's encoding without light (ruling S-14, MP.watchKey): the dirty set means a world change
-- (walls, doors, windows, containers, floor), and an unrounded light level would dirty most of the ring at every
-- lighting drift and fill the budget with deltas; an emitted line still carries the real light.
-- MP.seen holds the dirty key of every square ever emitted (full or delta) and MP.lastDelta the tick of every delta, both
-- unbounded: a session sees a few thousand squares, about 100 bytes of string each.
-- The door events come from here (X4 fix pass 2.3, review I7: Sense's own 81-square door walk a frame is gone): every
-- record the map emits (a scan part's square or a watch delta) is set against the door and window open states of the
-- last record emitted for its square (MP.portals), and each portal whose open state changed is queued in
-- MP.doorEvents as { x, y, z, open } for Sense's next events call to drain; a square first seen records its portals
-- silently. So a door is read once per dirty square, and its event is as late as the watch's cycle (132 ticks at most). Every Java member is reached
-- through PZA.call (index-first); a member a square lacks is named in the part's missing list, never nil-called.
PZA.map = PZA.map or {}
local MP = PZA.map
MP.WATCH_R = 6              -- tiles: the watch's ring is (2 * 6 + 1)^2 = 169 squares, a cycle of 22 steps (132 ticks)
MP.WATCH_PER_FRAME = 8      -- squares a watch step
MP.WATCH_EVERY = 6          -- ticks between watch steps: the 10 Hz frame tick
MP.DELTA_MIN_TICKS = 30
MP.seen = {}
MP.lastDelta = {}
MP.fp = {}                  -- the fingerprint each watched square was last settled with, by its grid key
MP.portals = {}             -- the door and window open states of the last record emitted, by square key
MP.doorEvents = {}          -- the door events since Sense last drained them, at most DOOR_EVENTS_MAX
MP.DOOR_EVENTS_MAX = 100
MP.doorDropped = 0          -- door events past DOOR_EVENTS_MAX, dropped
MP.watchIdx = 0
MP.missing = {}             -- the members the watch's squares lacked (a delta line carries an empty list)
MP.errors = 0               -- raises in the map phase, caught by Main's own pcall round it (S-15; raise:map in missing)
MP.lastError = nil

local W = PZA.world
local getm = W.getm

function MP.key(x, y, z)
    return x .. "," .. y .. "," .. z
end

-- the object's containers (PZA.world.containersOf) as the schema's container records { type, n, items }
local function containersOf(o, missing)
    local out = {}
    local list = W.containersOf(o)
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

-- the square's north (x, y - 1) and west (x - 1, y) neighbours off the cell at its own read position, each nil when
-- the cell holds no square there (unloaded, or the map's edge); both nil when any of x, y, z is nil
local function neighboursOf(cell, x, y, z)
    if x == nil or y == nil or z == nil then return nil, nil end
    local _, nsq = PZA.call(cell, "getGridSquare", x, y - 1, z)
    local _, wsq = PZA.call(cell, "getGridSquare", x - 1, y, z)
    return nsq, wsq
end

-- the square's edges to one neighbour into q[blockKey] (isBlockedTo: a wall, a closed or barricaded door, an intact
-- closed window, a stair edge) and q[edgeKey] (isSomethingTo: anything standing on that edge); an absent neighbour
-- leaves both nil and names missName
local function edgesTo(missing, q, sq, other, blockKey, edgeKey, missName)
    if other == nil then
        PZA.missing(missing, missName)
        return
    end
    getm(missing, q, blockKey, sq, "isBlockedTo", other)
    getm(missing, q, edgeKey, sq, "isSomethingTo", other)
end

-- the square's own hoppable north and west edges into q.hopN and q.hopW (PZA/1.4): sq:has(IsoFlagType.HoppableN) and
-- has(IsoFlagType.HoppableW), each nil when the constant is absent (named IsoFlagType.<name> in missing) or the square
-- lacks has (named has)
local HOPS = { { "hopN", "HoppableN" }, { "hopW", "HoppableW" } }

local function hopsOf(missing, q, sq)
    for _, h in ipairs(HOPS) do
        local flag = IsoFlagType ~= nil and IsoFlagType[h[2]] or nil
        if flag == nil then
            PZA.missing(missing, "IsoFlagType." .. h[2])
        else
            getm(missing, q, h[1], sq, "has", flag)
        end
    end
end

-- the water record of a water object (PZA/1.5): { amount, tainted, infinite }, a member it lacks nil and named.
-- infinite (PZA/1.5.4, Plan 24 Task 9 fix 6; jar-reads-2 section 9): IsoObject.isWaterInfinite is private on 42.21
-- (access 0x2), so Kahlua never exposes it and E6 named it missing on every water square; the public getFluidCapacity()
-- answers 10000 when it holds (IsoObject.getFluidCapacity @16-@26 L2746-L2747, @44-@53 L2756-L2757), else an
-- external source's, the container's or the piped reserve's capacity (20 for a sink after the shut-off, L2765-L2766).
-- A capacity of WATER_INFINITE or more reads infinite; a non-number answer leaves it nil, an absent member names it.
MP.WATER_INFINITE = 10000

local function waterOf(o, missing)
    local w = {}
    getm(missing, w, "amount", o, "getFluidAmount")
    getm(missing, w, "tainted", o, "isTaintedWater")
    local ok, cap = PZA.call(o, "getFluidCapacity")
    if not ok then
        PZA.missing(missing, "getFluidCapacity")
    elseif type(cap) == "number" then
        w.infinite = cap >= MP.WATER_INFINITE
    end
    return w
end

-- a portal's lock (PZA/1.6, Task 9 fix 9; jar-reads-2 section 10): true when any of its kind's lock members reads true
-- (a door: isLocked, isLockedByKey, and a thumpable's isLockedByPadlock; a window: isLocked, isPermaLocked), false when
-- one at least reads and none reads true, and true (fail-closed: never sent to an open it would refuse) when none of
-- them can be read, isLocked then named in missing. The jar: IsoDoor.setLockedByKey @14-@21 L2006-L2007 sets locked too
-- and IsoDoor.checkKeyId @138-@162 L2297-L2298 marks a locked door of a building (a key id) locked by key, which
-- ToggleDoorActual @304-@393 L1514-L1527 refuses to a player outside holding no key; a player inside unlocks it
-- (canBeOpenFromInside, @279-@294 L1509-L1511). A locked window from outside struggles and may lock for good
-- (OpenWindowState.onAttemptFinished @61-@142 L190-L199); a perma-locked one never opens. So locked true means may
-- refuse, never will refuse: a door locked but not by key also refuses a player from one side with the 'Locked' sound
-- (ToggleDoorActual @582-@619 L1545-L1548), and a player holding the key opens a door locked by key (@394 L1529, the
-- 'Unlock' sound); a player inside unlocks it.
MP.LOCKS = { door = { "isLocked", "isLockedByKey", "isLockedByPadlock" }, window = { "isLocked", "isPermaLocked" } }

function MP.lockedOf(o, kind, missing)
    local read = false
    for _, m in ipairs(MP.LOCKS[kind] or MP.LOCKS.door) do
        local ok, v = PZA.call(o, m)
        if ok then
            read = true
            if v == true then return true end
        end
    end
    if not read then
        if missing ~= nil then PZA.missing(missing, "isLocked") end
        return true
    end
    return false
end

-- one square as the schema's square record: x, y, z, solid, solidTrans, light, room, building, door and window (a
-- portal { open, locked, barricaded } or nil), containers ({ type, n, items } each, items full types), floor (the
-- full types of its world items), its four edges blockN, blockW, edgeN, edgeW (edgesTo, read against the north and
-- west neighbours off cell), its own hop flags hopN, hopW (hopsOf) and water (its first object whose hasWater() holds,
-- waterOf; nil when none); a member the square lacks leaves its field nil and its name in missing
function MP.square(sq, missing, cell)
    local q = { containers = {}, floor = {} }
    getm(missing, q, "x", sq, "getX"); getm(missing, q, "y", sq, "getY"); getm(missing, q, "z", sq, "getZ")
    if q.x ~= nil and q.y ~= nil and q.z ~= nil then
        local nsq, wsq = neighboursOf(cell, q.x, q.y, q.z)
        edgesTo(missing, q, sq, nsq, "blockN", "edgeN", "neighbourN")
        edgesTo(missing, q, sq, wsq, "blockW", "edgeW", "neighbourW")
    end
    hopsOf(missing, q, sq)
    getm(missing, q, "solid", sq, "isSolid"); getm(missing, q, "solidTrans", sq, "isSolidTrans"); getm(missing, q, "light", sq, "getLightLevel", 0)
    local okR, room = PZA.call(sq, "getRoom"); if okR and room ~= nil then local _, nm = PZA.call(room, "getName"); q.room = nm end
    local okB, b = PZA.call(sq, "getBuilding"); if okB and b ~= nil then local _, id = PZA.call(b, "getID"); q.building = id end
    local objs = W.objectsOn(sq)
    for _, o in ipairs(objs) do
        local cts = containersOf(o, missing)
        for _, ct in ipairs(cts) do q.containers[#q.containers + 1] = ct end
        local kind = W.kindOf(o)
        if kind ~= nil then
            local _, open = PZA.call(o, "IsOpen")
            local _, barr = PZA.call(o, "isBarricaded")
            q[kind] = { open = open == true, locked = MP.lockedOf(o, kind, missing), barricaded = barr == true }
        end
        if q.water == nil then
            local _, hw = PZA.call(o, "hasWater")
            if hw == true then q.water = waterOf(o, missing) end
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

-- the square's fingerprint (X4 fix pass, review I7): its solid flags, the object count, each portal's kind and
-- open/locked/barricaded in object order, each container's item count, and the floor's world-object count, as one
-- string; light, types and names are left out, so a fingerprint is a few reads and no item walk. The objects are read
-- into one scratch table (W.objectsOn's out). Its last element is the four edges (Plan 23 Task 6), "e" then blockN,
-- blockW, edgeN, edgeW as "t", "f" or "n" (nil: the neighbour unloaded, the member absent), so a door closing on an
-- edge or a neighbour loading changes it. x, y, z are the square's grid coordinates as the caller holds them (the
-- watch's gx, gy and floor), so the fingerprint reads none of the square's own (fix wave L, M-1).
local fpScratch = {}

-- an edge read as one character: "t", "f", or "n" when the read answered nothing
local function edgeChar(ok, v)
    if not ok or v == nil then return "n" end
    if v == true then return "t" end
    return "f"
end

-- the four edges' characters against the square's neighbours off cell, at the coordinates the caller already holds
-- (Plan 23 fix wave L, M-1: the square's own getX/getY/getZ are never re-read; nil coordinates read every edge "n")
local function edgeMark(sq, cell, x, y, z)
    local nsq, wsq = neighboursOf(cell, x, y, z)
    local bn, en, bw, ew = "n", "n", "n", "n"
    if nsq ~= nil then
        bn = edgeChar(PZA.call(sq, "isBlockedTo", nsq))
        en = edgeChar(PZA.call(sq, "isSomethingTo", nsq))
    end
    if wsq ~= nil then
        bw = edgeChar(PZA.call(sq, "isBlockedTo", wsq))
        ew = edgeChar(PZA.call(sq, "isSomethingTo", wsq))
    end
    return "e" .. bn .. bw .. en .. ew
end

function MP.fingerprint(sq, cell, x, y, z)
    local out = {}
    local _, solid = PZA.call(sq, "isSolid")
    local _, solidTrans = PZA.call(sq, "isSolidTrans")
    local objs, n = W.objectsOn(sq, fpScratch)
    out[1] = tostring(solid == true) .. tostring(solidTrans == true) .. tostring(n)
    for i = 1, n do
        local o = objs[i]
        local kind = W.kindOf(o)
        if kind ~= nil then
            local _, open = PZA.call(o, "IsOpen")
            local _, barr = PZA.call(o, "isBarricaded")
            out[#out + 1] = kind .. tostring(open == true) .. tostring(MP.lockedOf(o, kind)) .. tostring(barr == true)
        end
        local cs = W.containersOf(o)
        for k = 1, #cs do
            local _, items = PZA.call(cs[k], "getItems")
            local _, cn = PZA.call(items, "size")
            out[#out + 1] = "c" .. tostring(cn)
        end
    end
    local _, wl = PZA.call(sq, "getWorldObjects")
    local _, wn = PZA.call(wl, "size")
    out[#out + 1] = "f" .. tostring(wn)
    out[#out + 1] = edgeMark(sq, cell, x, y, z)
    return table.concat(out, ",")
end

-- the dirty key of a square record: its PZA.enc.square encoding with light left out (ruling S-14); q is left as it was
function MP.watchKey(q)
    local light = q.light
    q.light = nil
    local e = PZA.enc.square(q)
    q.light = light
    return e
end

-- a portal record's open state, nil when the square has no such portal
local function openOf(pt)
    if pt == nil then return nil end
    return pt.open == true
end

local PORTAL_KINDS = { "door", "window" }

-- the record q about to be emitted for key, set against MP.portals[key]: each door or window whose open state changed
-- queues a door event carrying its record's locked (PZA/1.6; a square first seen queues none); MP.portals[key] becomes q's
local function notePortals(key, q)
    local was = MP.portals[key]
    local now = { door = openOf(q.door), window = openOf(q.window) }
    if was ~= nil then
        for _, k in ipairs(PORTAL_KINDS) do
            if was[k] ~= nil and now[k] ~= nil and was[k] ~= now[k] then
                if #MP.doorEvents >= MP.DOOR_EVENTS_MAX then
                    MP.doorDropped = MP.doorDropped + 1
                else
                    MP.doorEvents[#MP.doorEvents + 1] = { x = q.x, y = q.y, z = q.z, open = now[k], locked = q[k].locked }
                end
            end
        end
    end
    MP.portals[key] = now
end

-- the dirty key a square was last emitted with, by its key (a square without a readable position is never keyed), and
-- its portals against the last record's
local function remember(q)
    if q.x == nil or q.y == nil or q.z == nil then return nil end
    local key = MP.key(q.x, q.y, q.z)
    MP.seen[key] = MP.watchKey(q)
    notePortals(key, q)
    return key
end

-- the player's position, or nil when any of x, y, z cannot be read as a number
local function posOf(p)
    local x, y, z = W.posOf(p, true)
    if x == nil or y == nil or z == nil then return nil end
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
        if sq ~= nil then part.squares[#part.squares + 1] = MP.square(sq, part.missing, cell) end
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

-- true on the ticks the watch steps (every WATCH_EVERY-th: Main calls MP.watchStep only then, and never while a scan
-- job runs)
function MP.watchDue(tick)
    return tick % MP.WATCH_EVERY == 0
end

-- the watch: the next WATCH_PER_FRAME squares of the ring round the player's square (MP.watchIdx cycling over its
-- (2 WATCH_R + 1)^2 indexes, row by row, the ring re-centred each step), each fingerprinted; MP.fp is keyed on the
-- player's floor (math.floor(z): a fractional z on a stair keeps its keys; X4 fix pass fix 1, review M-2); a square whose
-- fingerprint is not MP.fp's is read whole and queued as a delta when its dirty key (MP.watchKey: the encoding without
-- light) is not MP.seen's and its last delta is DELTA_MIN_TICKS ticks old or more (a held change keeps its old
-- fingerprint, so it is read again on a later cycle). An absent square still takes its index. Answers the deltas
-- queued.
function MP.watchStep(p)
    local x, y, z = posOf(p)
    if x == nil then return 0 end
    local cell = getCell and getCell() or nil
    local r = MP.WATCH_R
    local side = 2 * r + 1
    local n = side * side
    local px, py, fz = math.floor(x), math.floor(y), math.floor(z)
    local tick = PZA.tick or 0
    local seen, last, fps, watchKey = MP.seen, MP.lastDelta, MP.fp, MP.watchKey
    local queued = 0
    for _ = 1, MP.WATCH_PER_FRAME do
        local i = MP.watchIdx % n
        MP.watchIdx = (i + 1) % n
        local gx, gy = px + i % side - r, py + math.floor(i / side) - r
        local _, sq = PZA.call(cell, "getGridSquare", gx, gy, z)
        if sq ~= nil then
            local gk = MP.key(gx, gy, fz)
            local f = MP.fingerprint(sq, cell, gx, gy, fz)
            if f ~= fps[gk] then
                local q = MP.square(sq, MP.missing, cell)
                if q.x ~= nil and q.y ~= nil and q.z ~= nil then
                    local key = MP.key(q.x, q.y, q.z)
                    local e = watchKey(q)
                    local at = last[key]
                    if e == seen[key] then
                        fps[gk] = f
                    elseif at == nil or tick - at >= MP.DELTA_MIN_TICKS then
                        fps[gk] = f
                        seen[key] = e
                        last[key] = tick
                        notePortals(key, q)
                        PZA.link.queueMap({ mode = "delta", scanId = 0, part = 1, parts = 1, squares = { q }, missing = {} })
                        queued = queued + 1
                    end
                end
            end
        end
    end
    return queued
end
