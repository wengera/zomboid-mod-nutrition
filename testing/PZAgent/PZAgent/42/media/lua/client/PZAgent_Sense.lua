-- PZAgent_Sense.lua — the sensors (spec § 2.1). A member this build does not expose is reported in
-- PZA.sense.missing and the key is absent, never nil-called [#1725]: a zero and an absent accessor are
-- different findings. Every reading is written as Lua renders it.
PZA.sense = PZA.sense or {}
local S = PZA.sense
S.RATE = 5
S.ZOMBIE_RADIUS = 12
S.SCAN_S = 0
S.missing = {}

local function get(out, key, obj, member, ...)
    local ok, v = PZA.call(obj, member, ...)
    if ok then out[key] = v else PZA.missing(S.missing, member) end
    return ok, v
end

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
                out[count] = { id = okId and id or i, x = z:getX(), y = z:getY(), dist = d,
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
        get(f, "hunger", st, "getHunger"); get(f, "thirst", st, "getThirst"); get(f, "fatigue", st, "getFatigue")
        get(f, "endurance", st, "getEndurance"); get(f, "panic", st, "getPanic"); get(f, "pain", st, "getPain")
    else PZA.missing(S.missing, "getStats") end
    local okB, bd = PZA.call(p, "getBodyDamage")
    if okB then get(f, "health", bd, "getOverallBodyHealth") else PZA.missing(S.missing, "getBodyDamage") end
    local okW, w = PZA.call(p, "getPrimaryHandItem")
    if okW and w ~= nil then
        f.weapon = {}
        get(f.weapon, "type", w, "getFullType"); get(f.weapon, "condition", w, "getCondition"); get(f.weapon, "ammo", w, "getCurrentAmmoCount")
    end
    local okI, inv = PZA.call(p, "getInventory")
    local _, items = PZA.call(inv, "getItems")
    local okC, n = PZA.call(items, "size")
    f.items = okC and n or 0
    if not okI then PZA.missing(S.missing, "getInventory") end
    local okM, mo = PZA.call(p, "getMoodles")
    if okM and MoodleType ~= nil then
        f.moodles = {}
        for _, name in ipairs({ "Hungry", "Thirst", "Tired", "Endurance", "Panic", "Pain", "Injured", "Bleeding", "Sick", "Wet", "Stress", "Unhappy" }) do
            local mt = MoodleType[name]
            if mt ~= nil then local ok, lv = PZA.call(mo, "getMoodleLevel", mt); if ok then f.moodles[name] = lv end end
        end
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

local function square(sq)
    local q = { x = sq:getX(), y = sq:getY(), z = sq:getZ(), containers = {}, floor = {} }
    get(q, "solid", sq, "isSolid"); get(q, "solidTrans", sq, "isSolidTrans"); get(q, "light", sq, "getLightLevel", 0)
    local okR, room = PZA.call(sq, "getRoom"); if okR and room ~= nil then local _, nm = PZA.call(room, "getName"); q.room = nm end
    local okB, b = PZA.call(sq, "getBuilding"); if okB and b ~= nil then local _, id = PZA.call(b, "getID"); q.building = id end
    local objs = objectsOf(sq)
    for _, o in ipairs(objs) do
        local okC, c = PZA.call(o, "getContainer")
        if okC and c ~= nil then
            local ct = { items = {} }
            get(ct, "type", c, "getType")
            local _, items = PZA.call(c, "getItems")
            local okN, n = PZA.call(items, "size")
            ct.n = okN and n or 0
            for i = 0, ct.n - 1 do local _, it = PZA.call(items, "get", i); local _, ft = PZA.call(it, "getFullType"); ct.items[#ct.items + 1] = ft or "?" end
            q.containers[#q.containers + 1] = ct
        end
        local okO, open = PZA.call(o, "IsOpen")
        if okO then
            local _, locked = PZA.call(o, "isLocked")
            local okBar, barr = PZA.call(o, "isBarricaded")
            if okBar then q.door = { open = open == true, locked = locked == true, barricaded = barr == true }
            else q.window = { open = open == true, locked = locked == true } end
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
    local out = { r = r, squares = {}, missing = S.missing }
    local px, py, pz = math.floor(p:getX()), math.floor(p:getY()), p:getZ()
    for dy = -r, r do
        for dx = -r, r do
            local _, sq = PZA.call(cell, "getGridSquare", px + dx, py + dy, pz)
            if sq ~= nil then out.squares[#out.squares + 1] = square(sq) end
        end
    end
    return out
end
