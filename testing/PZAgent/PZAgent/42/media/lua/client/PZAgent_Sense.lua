-- PZAgent_Sense.lua — the sensors (spec § 2.1). A member this build does not expose is reported in
-- PZA.sense.missing and the key is absent, never nil-called [#1725]: a zero and an absent accessor are
-- different findings. Every reading is written as Lua renders it.
PZA.sense = PZA.sense or {}
local S = PZA.sense
S.RATE = 5
S.ZOMBIE_RADIUS = 12
S.SCAN_S = 0
S.missing = {}

local function getm(miss, out, key, obj, member, ...)
    local ok, v = PZA.call(obj, member, ...)
    if ok then out[key] = v else PZA.missing(miss, member) end
    return ok, v
end

local function get(out, key, obj, member, ...)
    return getm(S.missing, out, key, obj, member, ...)
end

-- Stats.get(CharacterStat.X) is the 42.21 accessor (Stats has no getHunger etc.); a nil constant is reported.
local STATS = { { "hunger", "HUNGER" }, { "thirst", "THIRST" }, { "fatigue", "FATIGUE" }, { "endurance", "ENDURANCE" },
                { "panic", "PANIC" }, { "pain", "PAIN" }, { "sickness", "FOOD_SICKNESS" }, { "wetness", "WETNESS" },
                { "temperature", "TEMPERATURE" } }
local MOODLES = { "HUNGRY", "THIRST", "TIRED", "ENDURANCE", "PANIC", "PAIN", "INJURED", "BLEEDING", "SICK", "WET", "STRESS", "UNHAPPY" }

function S.clock()
    local gt = getGameTime ~= nil and getGameTime() or nil
    local okH, h = PZA.call(gt, "getHour")
    local okM, m = PZA.call(gt, "getMinutes")
    local okW, w = PZA.call(gt, "getWorldAgeHours")
    local gameMin = (okH and okM) and (h * 60 + m) or 0
    return gameMin, okW and w or 0
end

local function zombies(p, px, py)
    local cell = getCell and getCell() or nil
    local _, list = PZA.call(cell, "getZombieList")
    local okN, n = PZA.call(list, "size")
    local out, count = {}, 0
    if not okN then PZA.missing(S.missing, "getZombieList"); return out, 0 end
    for i = 0, n - 1 do
        local _, z = PZA.call(list, "get", i)
        local _, dead = PZA.call(z, "isDead")
        if z ~= nil and dead ~= true then
            local ex, ey = z:getX() - px, z:getY() - py
            local d = math.sqrt(ex * ex + ey * ey)
            if d <= S.ZOMBIE_RADIUS then
                count = count + 1
                local okId, id = PZA.call(z, "getOnlineID")
                local _, target = PZA.call(z, "getTarget")
                local _, crawl = PZA.call(z, "isCrawling")
                out[count] = { id = okId and id or ("i" .. i), x = z:getX(), y = z:getY(), dist = d,
                               hasTarget = target ~= nil, crawler = crawl == true }
            end
        end
    end
    return out, count
end

function S.frame(p)
    local f = { x = p:getX(), y = p:getY(), z = p:getZ() }
    get(f, "dir", p, "getDir"); f.dir = f.dir ~= nil and tostring(f.dir) or nil
    get(f, "moving", p, "isPlayerMoving"); get(f, "running", p, "IsRunning"); get(f, "sprinting", p, "isSprinting")
    local okS, st = PZA.call(p, "getStats")
    if okS then
        for _, e in ipairs(STATS) do
            local c = CharacterStat ~= nil and CharacterStat[e[2]] or nil
            if c ~= nil then get(f, e[1], st, "get", c) else PZA.missing(S.missing, "CharacterStat." .. e[2]) end
        end
    else PZA.missing(S.missing, "getStats") end
    local okB, bd = PZA.call(p, "getBodyDamage")
    if okB then get(f, "health", bd, "getOverallBodyHealth") else PZA.missing(S.missing, "getBodyDamage") end
    local okW, w = PZA.call(p, "getPrimaryHandItem")
    if not okW then PZA.missing(S.missing, "getPrimaryHandItem") end
    if okW and w ~= nil then
        f.weapon = {}
        get(f.weapon, "type", w, "getFullType"); get(f.weapon, "condition", w, "getCondition"); get(f.weapon, "ammo", w, "getCurrentAmmoCount")
    end
    local okI, inv = PZA.call(p, "getInventory")
    local okG, items = PZA.call(inv, "getItems")
    local okC, n = PZA.call(items, "size")
    f.items = okC and n or 0
    if not okI then PZA.missing(S.missing, "getInventory") elseif not okG then PZA.missing(S.missing, "getItems") elseif not okC then PZA.missing(S.missing, "size") end
    local okM, mo = PZA.call(p, "getMoodles")
    if okM then
        f.moodles = {}
        for _, name in ipairs(MOODLES) do
            local mt = MoodleType ~= nil and MoodleType[name] or nil
            if mt ~= nil then
                local ok, lv = PZA.call(mo, "getMoodleLevel", mt)
                if ok then f.moodles[name] = lv else PZA.missing(S.missing, "getMoodleLevel") end
            else PZA.missing(S.missing, "MoodleType." .. name) end
        end
    else PZA.missing(S.missing, "getMoodles") end
    -- the player's timed-action queue is vanilla Lua: guarded, its first action's Type and the length
    local okQ, q = pcall(function() return ISTimedActionQueue.getTimedActionQueue(p).queue end)
    if okQ and q ~= nil then
        local okN, qn = pcall(function() return #q end)
        if okN then f.action = { class = q[1] ~= nil and q[1].Type or nil, n = qn } end
    end
    f.zombies, f.nZombies = zombies(p, f.x, f.y)
    return f
end

local function byId(list)
    local m = {}
    for i = 1, #list do m[list[i].id] = list[i] end
    return m
end

function S.events(p, prev)
    local cur = S.frame(p)
    local ev = {}
    local was, now = byId(prev.zombies or {}), byId(cur.zombies or {})
    for id, z in pairs(now) do if was[id] == nil then ev[#ev + 1] = { event = "zombie_enter", id = id, dist = z.dist } end end
    for id, _ in pairs(was) do if now[id] == nil then ev[#ev + 1] = { event = "zombie_leave", id = id } end end
    if cur.health ~= nil and prev.health ~= nil and prev.health - cur.health > 0.5 then
        ev[#ev + 1] = { event = "hit", health = cur.health }
    end
    if (cur.items or 0) > (prev.items or 0) then
        local _, inv = PZA.call(p, "getInventory")
        local _, items = PZA.call(inv, "getItems")
        local _, last = PZA.call(items, "get", cur.items - 1)
        local _, ft = PZA.call(last, "getFullType")
        ev[#ev + 1] = { event = "item_added", fullType = ft or "" }
    end
    return ev, cur
end

local function objectsOf(sq)
    local out = {}
    local _, list = PZA.call(sq, "getObjects")
    local okN, n = PZA.call(list, "size")
    if not okN then return out end
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
    if okN then
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
        ct.n = okS and n or 0
        for i = 0, ct.n - 1 do local _, it = PZA.call(items, "get", i); local _, ft = PZA.call(it, "getFullType"); ct.items[#ct.items + 1] = ft or "?" end
        out[#out + 1] = ct
    end
    return out
end

local function square(sq, missing)
    local q = { x = sq:getX(), y = sq:getY(), z = sq:getZ(), containers = {}, floor = {} }
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
    for i = 0, (okW and wn or 0) - 1 do
        local _, wo = PZA.call(wl, "get", i); local _, it = PZA.call(wo, "getItem"); local _, ft = PZA.call(it, "getFullType")
        if ft ~= nil then q.floor[#q.floor + 1] = ft end
    end
    return q
end

-- The scan is a job walked SCAN_SQUARES_PER_TICK squares a tick (Stage A pass 1 read r=15, 961 squares, at
-- 14-21 ms in one tick) and emitted in parts, one per tick (Stage A pass 2 read the completing tick's emit of the
-- whole r=15 line, 99.3 KB, at 45 ms: about 0.45 ms per KB of PZA.json and append, so the line is cut where the walk
-- is). scanStart fixes the (2r+1)^2 grid at the player's square at start and gives the job the next scanId; scanStep
-- walks the next chunk row by row and returns it as a part: { scanId, r, hour, part (1-based), parts (the job's
-- ceil(n / SCAN_SQUARES_PER_TICK), fixed at start), squares (the found squares of this chunk), stepMs (this tick's
-- walk ms), missing (the members this chunk's squares lacked) }; the last part also carries done = true, scanMs (the
-- summed stepMs), scanTicks, scanMsPerTick (each part's stepMs) and scanStepMaxMs (its largest). Main stamps each
-- part's emitMs. One job at a time: a start replaces it, and the replaced job's parts stop.
S.SCAN_SQUARES_PER_TICK = 60
S.job = nil
S.scanId = 0

local function newJob(p, r, id)
    local side = 2 * r + 1
    local n = side * side
    return { id = id, r = r, side = side, i = 0, n = n, parts = math.ceil(n / S.SCAN_SQUARES_PER_TICK),
             hour = math.floor((S.clock()) / 60), ms = 0, ticks = 0, steps = {},
             px = math.floor(p:getX()), py = math.floor(p:getY()), pz = p:getZ() }
end

-- walks job's next chunk and returns it as a part; the last part carries done and the job's totals
local function stepJob(job)
    local t0 = PZA.now()
    local cell = getCell and getCell() or nil
    local stop = math.min(job.n, job.i + S.SCAN_SQUARES_PER_TICK)
    local part = { scanId = job.id, r = job.r, hour = job.hour, part = job.ticks + 1, parts = job.parts,
                   squares = {}, missing = {} }
    while job.i < stop do
        local i = job.i
        local dy = math.floor(i / job.side) - job.r
        local dx = i % job.side - job.r
        local _, sq = PZA.call(cell, "getGridSquare", job.px + dx, job.py + dy, job.pz)
        if sq ~= nil then part.squares[#part.squares + 1] = square(sq, part.missing) end
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

function S.scanStart(p, r)
    S.scanId = S.scanId + 1
    S.job = newJob(p, r, S.scanId)
end

-- one chunk of the running job as its part (the last one carrying done), else nil when no job runs
function S.scanStep(p)
    local job = S.job
    if job == nil then return nil end
    local part = stepJob(job)
    if part.done then S.job = nil end
    return part
end

-- the synchronous form, for tests: its own job (no scanId taken), stepped to the end and reassembled into pass 2's
-- whole scan line { r, hour, squares, missing (the parts' union), scanMs, scanTicks, scanMsPerTick, scanStepMaxMs };
-- a running S.job is left alone
function S.scan(p, r)
    local job = newJob(p, r, 0)
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
