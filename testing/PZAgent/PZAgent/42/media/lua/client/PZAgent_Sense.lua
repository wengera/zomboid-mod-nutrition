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
    local _, items = PZA.call(inv, "getItems")
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
        local _, items = PZA.call(c, "getItems")
        local okS, n = PZA.call(items, "size")
        if not okS then PZA.missing(missing, "getItems") end
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

function S.scan(p, r)
    local cell = getCell and getCell() or nil
    local out = { r = r, squares = {}, missing = {} }
    out.hour = math.floor((S.clock()) / 60)
    local px, py, pz = math.floor(p:getX()), math.floor(p:getY()), p:getZ()
    for dy = -r, r do
        for dx = -r, r do
            local _, sq = PZA.call(cell, "getGridSquare", px + dx, py + dy, pz)
            if sq ~= nil then out.squares[#out.squares + 1] = square(sq, out.missing) end
        end
    end
    return out
end
