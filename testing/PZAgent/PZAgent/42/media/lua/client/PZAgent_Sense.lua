-- PZAgent_Sense.lua — the sensors (spec § 2.1, Plan 22 Task 5). S.frame(p) returns the PZA/1 frame's groups, keyed
-- exactly by the schema's x-order (PZA.schema.groups): gameMin, worldAge, me, stats, body, load, weapon, action, act,
-- zombies (cost is Main's). A field that could not be read is nil, so the positional encoder writes null; a member this
-- build does not expose is reported in PZA.sense.missing, never nil-called [#1725]: a zero and an absent accessor are
-- different findings. Every Java member is reached through PZA.call (index-first). Observe, never echo: the run latch
-- is the Motor's post-assert read (PZA.motor.upd*), never the player's flags read in Sense's own tick.
PZA.sense = PZA.sense or {}
local S = PZA.sense
S.RATE = 10
S.ZOMBIE_RADIUS = 12
S.DOOR_R = 4              -- tiles (Chebyshev, the player's floor): the door and window watch's reach
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

function S.clock()
    local gt = getGameTime ~= nil and getGameTime() or nil
    local okH, h = PZA.call(gt, "getHour")
    local okM, m = PZA.call(gt, "getMinutes")
    local okW, w = PZA.call(gt, "getWorldAgeHours")
    local gameMin = (okH and okM) and (h * 60 + m) or 0
    return gameMin, okW and w or 0
end

-- the cell's zombie list as a Lua array of its non-nil entries (by size/get, never # on the Java list), or nil when
-- the cell or its list cannot be read
local function zombieList()
    local cell = getCell ~= nil and getCell() or nil
    local _, list = PZA.call(cell, "getZombieList")
    local okN, n = PZA.call(list, "size")
    if not okN or type(n) ~= "number" then return nil end
    local out = {}
    for i = 0, n - 1 do
        local _, z = PZA.call(list, "get", i)
        if z ~= nil then out[#out + 1] = z end
    end
    return out
end

local function isDead(z)
    local _, dead = PZA.call(z, "isDead")
    return dead == true
end

-- a zombie's distance from (px, py), with its position, or nil when its position cannot be read
local function distOf(z, px, py)
    local okX, zx = PZA.call(z, "getX")
    local okY, zy = PZA.call(z, "getY")
    if not okX or not okY or type(zx) ~= "number" or type(zy) ~= "number" then return nil end
    local ex, ey = zx - px, zy - py
    return math.sqrt(ex * ex + ey * ey), zx, zy
end

local function byDist(a, b) return a.dist < b.dist end

-- the live zombies within ZOMBIE_RADIUS, nearest first, as the schema's zombie records; S.zobj maps each record's id
-- to its object, so the next events call can ask a zombie seen in this frame whether it died
local function zombies(px, py)
    local out, objs = {}, {}
    local list = zombieList()
    if list == nil then PZA.missing(S.missing, "getZombieList"); return out, objs end
    if px == nil or py == nil then return out, objs end
    for _, z in ipairs(list) do
        if not isDead(z) then
            local d, zx, zy = distOf(z, px, py)
            if d ~= nil and d <= S.ZOMBIE_RADIUS then
                local rec = { x = zx, y = zy, dist = d }
                get(rec, "id", z, "getOnlineID")
                local _, target = PZA.call(z, "getTarget")
                local _, crawl = PZA.call(z, "isCrawling")
                rec.hasTarget, rec.crawler = target ~= nil, crawl == true
                get(rec, "health", z, "getHealth")
                out[#out + 1] = rec
                if rec.id ~= nil then objs[rec.id] = z end
            end
        end
    end
    table.sort(out, byDist)
    return out, objs
end

-- me: the position, facing and moving reads, the pace measured from the previous frame (S.prev: x, y, wallMs; nil on
-- the first frame or a zero dt), and the run latch as the Motor's OnPlayerUpdate handler read it after its asserts
-- (PZA.motor absent before PZAgent_Motor.lua loads: the four are nil). autoWalk has no Motor read, so it is the
-- player's isAutoWalk.
local function me(p)
    local m = {}
    get(m, "x", p, "getX"); get(m, "y", p, "getY"); get(m, "z", p, "getZ")
    get(m, "dir", p, "getDir"); if m.dir ~= nil then m.dir = tostring(m.dir) end
    get(m, "moving", p, "isPlayerMoving"); get(m, "autoWalk", p, "isAutoWalk")
    local mo = PZA.motor
    if mo ~= nil then
        m.running, m.sprinting = mo.updRunning, mo.updSprinting
        m.forceRun, m.forceSprint = mo.updForceRun, mo.updForceSprint
    end
    local now = PZA.now()
    local prev = S.prev
    if prev ~= nil and type(m.x) == "number" and type(m.y) == "number" and now > prev.wallMs then
        local dx, dy = m.x - prev.x, m.y - prev.y
        m.pace = math.sqrt(dx * dx + dy * dy) / ((now - prev.wallMs) / 1000)
    end
    if type(m.x) == "number" and type(m.y) == "number" then S.prev = { x = m.x, y = m.y, wallMs = now } end
    return m
end

local function stats(p)
    local s = {}
    local okS, st = PZA.call(p, "getStats")
    if not okS then PZA.missing(S.missing, "getStats"); return s end
    for _, e in ipairs(STATS) do
        local c = CharacterStat ~= nil and CharacterStat[e[2]] or nil
        if c ~= nil then get(s, e[1], st, "get", c) else PZA.missing(S.missing, "CharacterStat." .. e[2]) end
    end
    return s
end

-- body: the overall health, the wound counts and every part whose health reads under 100 as the schema's part record
-- { i, h } (i 0-based, the getBodyParts order); parts is always an array, empty when none is hurt
local function body(p)
    local b = { parts = {} }
    local okB, bd = PZA.call(p, "getBodyDamage")
    if not okB then PZA.missing(S.missing, "getBodyDamage"); return b end
    get(b, "health", bd, "getOverallBodyHealth")
    get(b, "bleeding", bd, "getNumPartsBleeding"); get(b, "scratched", bd, "getNumPartsScratched")
    get(b, "bitten", bd, "getNumPartsBitten")
    local okP, list = PZA.call(bd, "getBodyParts")
    local okN, n = PZA.call(list, "size")
    if not okP then PZA.missing(S.missing, "getBodyParts") elseif not okN then PZA.missing(S.missing, "size") end
    for i = 0, (okN and n or 0) - 1 do
        local _, part = PZA.call(list, "get", i)
        local okH, h = PZA.call(part, "getHealth")
        if okH and type(h) == "number" and h < 100 then b.parts[#b.parts + 1] = { i = i, h = h } end
    end
    return b
end

-- load (spec § 9, the planner's input): the carried weight, the maximum, the HEAVY_LOAD moodle level and the
-- inventory's item count
local function carry(p)
    local l = {}
    local okInv, inv = PZA.call(p, "getInventory")
    if okInv then
        get(l, "weight", inv, "getCapacityWeight")
        local okG, items = PZA.call(inv, "getItems")
        if okG then get(l, "n", items, "size") else PZA.missing(S.missing, "getItems") end
    else PZA.missing(S.missing, "getInventory") end
    get(l, "max", p, "getMaxWeight")
    local okM, mo = PZA.call(p, "getMoodles")
    local mt = MoodleType ~= nil and MoodleType.HEAVY_LOAD or nil
    if not okM then PZA.missing(S.missing, "getMoodles")
    elseif mt == nil then PZA.missing(S.missing, "MoodleType.HEAVY_LOAD")
    else get(l, "level", mo, "getMoodleLevel", mt) end
    return l
end

-- weapon: the primary hand item, nil when the hand is empty; reach is the runner's K.reachOf (getMaxRange x
-- getRangeMod x the margin), nil while PZAgent_Skills.lua is not loaded
local function weapon(p)
    local okW, w = PZA.call(p, "getPrimaryHandItem")
    if not okW then PZA.missing(S.missing, "getPrimaryHandItem"); return nil end
    if w == nil then return nil end
    local wp = {}
    get(wp, "type", w, "getFullType"); get(wp, "cond", w, "getCondition")
    local K = PZA.skills
    if K ~= nil and K.reachOf ~= nil then wp.reach = K.reachOf(p, w) end
    get(wp, "ammo", w, "getCurrentAmmoCount")
    return wp
end

-- the player's timed-action queue is vanilla Lua: the class and its member are index-checked before the call (a
-- missing one leaves the frame without action, never a raise), the returned object and its queue read only as
-- Lua tables, so #q is a Lua length, never a Java list's; the call itself stays under pcall
local function action(p)
    if ISTimedActionQueue == nil or ISTimedActionQueue.getTimedActionQueue == nil then return nil end
    local okQ, tq = pcall(ISTimedActionQueue.getTimedActionQueue, p)
    local q = nil
    if okQ and type(tq) == "table" then q = tq.queue end
    if type(q) ~= "table" then return nil end
    local first = q[1]
    local cls = nil
    if type(first) == "table" then cls = first.Type end
    return { class = cls, n = #q }
end

-- act: the runner's K.status() ({aid, state}, nil when idle), nil while PZAgent_Skills.lua is not loaded
local function act()
    local K = PZA.skills
    if K == nil or K.status == nil then return nil end
    return K.status()
end

function S.frame(p)
    local f = {}
    f.gameMin, f.worldAge = S.clock()
    f.me = me(p)
    f.stats = stats(p)
    f.body = body(p)
    f.load = carry(p)
    f.weapon = weapon(p)
    f.action = action(p)
    f.act = act()
    f.zombies, S.zobj = zombies(f.me.x, f.me.y)
    return f
end

-- the client's OnPlayerGetDamage (Plan 22 probe X3, interface § 4): each call appends { tag, amount, isLocal } to
-- S.damage, and the next S.events drains them as damage events. Hooked once; the body under pcall, a raise counted in
-- S.damageErrors, never propagated into the game's damage path. S.damage holds at most DAMAGE_MAX entries between
-- drains (before the first frame nothing drains it); past the cap an entry is dropped and counted in S.damageDropped.
S.DAMAGE_MAX = 200
S.damage = S.damage or {}
S.damageErrors = S.damageErrors or 0
S.damageDropped = S.damageDropped or 0
S.damageHooked = S.damageHooked or false

local function recordDamage(ch, tag, amount)
    if #S.damage >= S.DAMAGE_MAX then
        S.damageDropped = S.damageDropped + 1
        return
    end
    local me = getPlayer ~= nil and getPlayer() or nil
    S.damage[#S.damage + 1] = { tag = tostring(tag), amount = amount, isLocal = ch == me }
end

function S.onDamage(ch, tag, amount)
    local ok = pcall(recordDamage, ch, tag, amount)
    if not ok then S.damageErrors = S.damageErrors + 1 end
end

if not S.damageHooked and Events ~= nil and Events.OnPlayerGetDamage ~= nil then
    Events.OnPlayerGetDamage.Add(S.onDamage)
    S.damageHooked = true
end

-- the inventory by item id: { [id] = { fullType, weight } }, walked by getItems' size/get; an id already in known
-- reuses its entry (its full type and weight are read once, at its first sight). nil when the inventory or its list
-- cannot be read, so a failed read never reads as every item removed.
function S.invIds(p, known)
    local _, inv = PZA.call(p, "getInventory")
    local _, items = PZA.call(inv, "getItems")
    local okN, n = PZA.call(items, "size")
    if not okN or type(n) ~= "number" then return nil end
    local out = {}
    for i = 0, n - 1 do
        local _, it = PZA.call(items, "get", i)
        local okI, id = PZA.call(it, "getID")
        if okI and id ~= nil then
            local k = known ~= nil and known[id] or nil
            if k == nil then
                k = {}
                getm(S.missing, k, "fullType", it, "getFullType")
                getm(S.missing, k, "weight", it, "getWeight")
            end
            out[id] = k
        end
    end
    return out
end

local function sortedIds(m)
    local ids = {}
    for id, _ in pairs(m) do ids[#ids + 1] = id end
    table.sort(ids)
    return ids
end

local function itemAdded(id, k, gameMin)
    return { event = "item_added", gameMin = gameMin, itemId = id, fullType = k.fullType, weight = k.weight }
end

-- the inventory's first sight (ruling P22-2): one item_added per held item, ids ascending; seeds the diff S.events
-- runs. Main calls it after hello.
function S.firstSight(p)
    local gameMin = S.clock()
    local now = S.invIds(p, nil)
    local ev = {}
    if now == nil then return ev end
    S.lastInv = now
    local ids = sortedIds(now)
    for _, id in ipairs(ids) do ev[#ev + 1] = itemAdded(id, now[id], gameMin) end
    return ev
end

-- door or window, by type first (the scan's kindOf rule: IsoThumpable answers by isDoor/isWindow)
local function portalOf(o)
    if instanceof == nil then return false end
    if instanceof(o, "IsoDoor") == true or instanceof(o, "IsoWindow") == true then return true end
    if instanceof(o, "IsoThumpable") == true then
        local _, d = PZA.call(o, "isDoor")
        local _, w = PZA.call(o, "isWindow")
        return d == true or w == true
    end
    return false
end

-- every door and window within DOOR_R of (px, py) on floor pz, by "x,y,z,k" (k the object's index on its square),
-- each its IsOpen read
local function doorsAround(px, py, pz)
    local out = {}
    local cell = getCell ~= nil and getCell() or nil
    if cell == nil then return out end
    local r = S.DOOR_R
    for y = py - r, py + r do
        for x = px - r, px + r do
            local _, sq = PZA.call(cell, "getGridSquare", x, y, pz)
            local _, list = PZA.call(sq, "getObjects")
            local okN, n = PZA.call(list, "size")
            for i = 0, (okN and type(n) == "number" and n or 0) - 1 do
                local _, o = PZA.call(list, "get", i)
                if o ~= nil and portalOf(o) then
                    local okO, open = PZA.call(o, "IsOpen")
                    if okO then out[x .. "," .. y .. "," .. pz .. "," .. i] = { x = x, y = y, z = pz, open = open == true } end
                end
            end
        end
    end
    return out
end

-- the typed events since prev (spec § 2.1), each { event = <kind>, gameMin, <the kind's fields flat> } without kind or
-- the envelope (Main emits each through PZA.emit("event", ev)):
--   damage{tag, amount, side = "client"}: the damage hook's records, drained;
--   swing{attackStarted, meleeDelay}: isAttackStarted reads true where the last events call read it not true;
--   zombie_dead{id}: a zombie in prev's frame whose object now answers isDead;
--   item_added{itemId, fullType, weight} / item_removed{itemId, fullType}: the inventory's ids against S.lastInv
--   (a first call without firstSight seeds it silently);
--   door{x, y, z, open}: a door or window within DOOR_R whose IsOpen changed since the last call (one first seen is
--   recorded without an event).
-- Returns ev and the new frame (cur).
function S.events(p, prev)
    local seen = S.zobj or {}
    local cur = S.frame(p)
    local gameMin = cur.gameMin
    local ev = {}
    for _, d in ipairs(S.damage) do
        ev[#ev + 1] = { event = "damage", gameMin = gameMin, tag = d.tag, amount = d.amount, side = "client" }
    end
    S.damage = {}
    local okA, started = PZA.call(p, "isAttackStarted")
    if okA then
        if started == true and S.lastAttack ~= true then
            local _, delay = PZA.call(p, "getMeleeDelay")
            ev[#ev + 1] = { event = "swing", gameMin = gameMin, attackStarted = true, meleeDelay = delay }
        end
        S.lastAttack = started == true
    end
    for _, z in ipairs(prev ~= nil and prev.zombies or {}) do
        local obj = z.id ~= nil and seen[z.id] or nil
        if obj ~= nil and isDead(obj) then ev[#ev + 1] = { event = "zombie_dead", gameMin = gameMin, id = z.id } end
    end
    local last = S.lastInv
    local now = S.invIds(p, last)
    if now ~= nil then
        if last ~= nil then
            local added, removed = sortedIds(now), sortedIds(last)
            for _, id in ipairs(added) do
                if last[id] == nil then ev[#ev + 1] = itemAdded(id, now[id], gameMin) end
            end
            for _, id in ipairs(removed) do
                if now[id] == nil then
                    ev[#ev + 1] = { event = "item_removed", gameMin = gameMin, itemId = id, fullType = last[id].fullType }
                end
            end
        end
        S.lastInv = now
    end
    local m = cur.me
    if type(m.x) == "number" and type(m.y) == "number" and type(m.z) == "number" then
        local doors = doorsAround(math.floor(m.x), math.floor(m.y), m.z)
        local was = S.lastDoors
        if was ~= nil then
            local keys = sortedIds(doors)
            for _, key in ipairs(keys) do
                local dnow, dwas = doors[key], was[key]
                if dwas ~= nil and dwas.open ~= dnow.open then
                    ev[#ev + 1] = { event = "door", gameMin = gameMin, x = dnow.x, y = dnow.y, z = dnow.z, open = dnow.open }
                end
            end
        end
        S.lastDoors = doors
    end
    return ev, cur
end

-- the live zombie whose online id is id, as its object (the IsoZombie the attack skill faces), or nil for an unknown
-- or dead id; the whole cell list, not the frame's radius
function S.zombieById(p, id)
    if id == nil then return nil end
    local list = zombieList()
    if list == nil then return nil end
    for _, z in ipairs(list) do
        local okI, zid = PZA.call(z, "getOnlineID")
        if okI and zid == id then
            if isDead(z) then return nil end
            return z
        end
    end
    return nil
end

-- the nearest live zombie in the cell list as { id, dist }, or nil when none (the runner's snapshot)
function S.nearestZombie(p)
    local okX, px = PZA.call(p, "getX")
    local okY, py = PZA.call(p, "getY")
    local list = zombieList()
    if not okX or not okY or list == nil then return nil end
    local best = nil
    for _, z in ipairs(list) do
        if not isDead(z) then
            local d = distOf(z, px, py)
            if d ~= nil and (best == nil or d < best.dist) then
                local _, zid = PZA.call(z, "getOnlineID")
                best = { id = zid, dist = d }
            end
        end
    end
    return best
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
-- 20 squares a part (Stage A pass 3, testing/artifacts/a_pipe_3-20261026-130558/GUIDE.md § 1): 60-square parts read
-- 3-7 ms a tick, the walk about 1 ms beside an emit of about 0.5 ms per KB plus about 0.5 ms a line; a 20-square part
-- projects to about 4.1-4.5 ms peak.
S.SCAN_SQUARES_PER_TICK = 20
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
