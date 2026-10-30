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
S.missing = {}

local W = PZA.world
local getm = W.getm

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
    local zx, zy = W.posOf(z)
    if zx == nil or zy == nil then return nil end
    local ex, ey = zx - px, zy - py
    return math.sqrt(ex * ex + ey * ey), zx, zy
end

local function byDist(a, b) return a.dist < b.dist end

-- the frame's one walk of the cell's zombie list (X4 fix pass 2.4: by size/get, no copy of the list): the live zombies
-- within ZOMBIE_RADIUS, nearest first, as the schema's zombie records; S.zobj maps each record's id to its object, so
-- the next events call can ask a zombie seen in this frame whether it died, and zombie_dead reads this walk's S.zobj
-- for the zombies it found alive; the third answer is the cell list's size (me.zombiesSeen, review M15), nil when the
-- list cannot be read
local function zombies(px, py)
    local out, objs = {}, {}
    local cell = getCell ~= nil and getCell() or nil
    local _, list = PZA.call(cell, "getZombieList")
    local okN, n = PZA.call(list, "size")
    if not okN or type(n) ~= "number" then PZA.missing(S.missing, "getZombieList"); return out, objs, nil end
    if px == nil or py == nil then return out, objs, n end
    for i = 0, n - 1 do
        local _, z = PZA.call(list, "get", i)
        if z ~= nil and not isDead(z) then
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
    return out, objs, n
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
    local gt = getGameTime ~= nil and getGameTime() or nil
    get(m, "hour", gt, "getTimeOfDay")
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

-- body: the overall health, the wound counts and every part S.notePart lists (hurt, bandaged or bleeding: PZA/1.5, at
-- the end of this file) as the schema's part record (i 0-based, the getBodyParts order); parts empty when none is listed
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
        if okH and type(h) == "number" then S.notePart(b, i, part, h) end
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

-- a raising Java member is a supported fault (ruling S-15): each group reader runs under pcall in S.frame and each event
-- kind's reader under pcall in S.events, so an engine exception inside a present member costs that group or kind, never
-- the frame. A raise is counted in S.frameErrors, its message kept in S.lastFrameError, and the group or event kind
-- recorded in S.missing as "raise:<name>" (the pcall cannot name the member; the group it sat in can). The index-first
-- reads stand inside every reader: a caught raise still parks the -debug client (#0957), so these pcalls contain only
-- what an index check cannot foresee.
S.frameErrors = S.frameErrors or 0
S.lastFrameError = nil

-- a raise caught under name: counted, its message kept, the name recorded
local function raised(name, err)
    S.frameErrors = S.frameErrors + 1
    S.lastFrameError = tostring(err)
    PZA.missing(S.missing, "raise:" .. name)
end

-- fn(...)'s answers (up to three), or nil (and the raise counted under name) when it raises
local function guarded(name, fn, ...)
    local ok, a, b, c = pcall(fn, ...)
    if ok then return a, b, c end
    raised(name, a)
    return nil, nil, nil
end

-- the frame: a required group (me, stats, body, load) whose reader raised is its table with every field nil (body keeps
-- its parts array, the zombies their empty array); a nullable group (weapon, action, act) is nil; gameMin and worldAge
-- read 0, as S.clock answers an unreadable clock. me also carries the zombie walk's counts: zombiesSeen the cell list's
-- size (nil when unread) and zombiesListed the frame's zombie records, so a reader tells a listing gap from a range gap
function S.frame(p)
    local f = {}
    f.gameMin, f.worldAge = guarded("clock", S.clock)
    if f.gameMin == nil then f.gameMin, f.worldAge = 0, 0 end
    f.me = guarded("me", me, p) or {}
    f.stats = guarded("stats", stats, p) or {}
    f.body = guarded("body", body, p) or { parts = {} }
    f.load = guarded("load", carry, p) or {}
    f.weapon = guarded("weapon", weapon, p)
    f.action = guarded("action", action, p)
    f.act = guarded("act", act)
    local seen
    f.zombies, S.zobj, seen = guarded("zombies", zombies, f.me.x, f.me.y)
    if f.zombies == nil then f.zombies, S.zobj = {}, {} end
    f.me.zombiesSeen, f.me.zombiesListed = seen, #f.zombies
    S.last = f
    return f
end

-- the client's OnPlayerGetDamage (Plan 22 probe X3, interface § 4): each call appends { tag, amount, isLocal } to
-- S.damage, and the next S.events drains them as damage events. Hooked once; the body under pcall, a raise counted in
-- S.damageErrors, never propagated into the game's damage path. S.damage holds at most DAMAGE_MAX entries between
-- drains (before the first frame nothing drains it); past the cap an entry is dropped and counted in S.damageDropped.
-- Only a record whose character is the local player becomes a damage event; another character's is counted in
-- S.damageRemote and carried nowhere else.
S.DAMAGE_MAX = 200
S.damageRemote = S.damageRemote or 0
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

-- the inventory by item id: { [id] = { fullType, weight, use, worn, rip, clothing } }, walked by getItems' size/get; an id
-- in known reuses its entry (its fields are read once, at its first sight; PZA/1.6 W.clothingOf). nil when the list
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
        if not okI or id == nil then PZA.missing(S.missing, "getID") end
        if okI and id ~= nil then
            local k = known ~= nil and known[id] or nil
            if k == nil then
                k = {}
                getm(S.missing, k, "fullType", it, "getFullType")
                getm(S.missing, k, "weight", it, "getWeight")
                k.use, k.worn, k.rip, k.clothing = W.useOf(it), W.wornOf(it), W.ripOf(it), W.clothingOf(it)   -- 1.5.2, 1.6
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
    return S.record({ event = "item_added", gameMin = gameMin, itemId = id, fullType = k.fullType, weight = k.weight }, k)
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

-- the readers of S.events, one per event kind, each appending its events to the list it is given
local function damageEvents(ev, gameMin)
    for _, d in ipairs(S.damage) do
        if d.isLocal == true then
            ev[#ev + 1] = { event = "damage", gameMin = gameMin, tag = d.tag, amount = d.amount, side = "client" }
        else
            S.damageRemote = S.damageRemote + 1
        end
    end
end

local function swingEvents(ev, gameMin, p)
    local okA, started = PZA.call(p, "isAttackStarted")
    if okA then
        if started == true and S.lastAttack ~= true then
            local _, delay = PZA.call(p, "getMeleeDelay")
            ev[#ev + 1] = { event = "swing", gameMin = gameMin, attackStarted = true, meleeDelay = delay }
        end
        S.lastAttack = started == true
    end
end

-- prev's zombies whose object now answers isDead; one this frame's walk listed alive (alive, this frame's S.zobj) is
-- not asked again, so a frame asks each zombie once (X4 fix pass 2.4)
local function deathEvents(ev, gameMin, prev, seen, alive)
    for _, z in ipairs(prev ~= nil and prev.zombies or {}) do
        local obj = z.id ~= nil and seen[z.id] or nil
        if obj ~= nil and alive[z.id] == nil and isDead(obj) then
            ev[#ev + 1] = { event = "zombie_dead", gameMin = gameMin, id = z.id }
        end
    end
end

local function itemEvents(ev, gameMin, p)
    local last = S.lastInv
    local now = S.invIds(p, last)
    if now == nil then return end
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

-- the map's door events since the last call (PZA.map.doorEvents, drained first so a raise never reads one twice):
-- Map sets each record it emits against the last one for its square (X4 fix pass 2.3), so no square is read here
local function doorEvents(ev, gameMin)
    local MP = PZA.map
    if MP == nil or MP.doorEvents == nil then return end
    local list = MP.doorEvents
    MP.doorEvents = {}
    for _, d in ipairs(list) do
        ev[#ev + 1] = { event = "door", gameMin = gameMin, x = d.x, y = d.y, z = d.z, open = d.open, locked = d.locked }
    end
end

-- one event kind's reader fn(part, ...) under pcall (S-15): its events join ev only when it ran through, so a raise
-- costs that kind's events this call (none half-read), never the other kinds or the frame
local function collect(ev, name, fn, ...)
    local part = {}
    local ok, err = pcall(fn, part, ...)
    if not ok then
        raised(name, err)
        return
    end
    for i = 1, #part do ev[#ev + 1] = part[i] end
end

-- the typed events since prev (spec § 2.1), each { event = <kind>, gameMin, <the kind's fields flat> } without kind or
-- the envelope (Main emits each through PZA.emit("event", ev)):
--   damage{tag, amount, side = "client"}: the damage hook's records of the local player, drained;
--   swing{attackStarted, meleeDelay}: isAttackStarted reads true where the last events call read it not true;
--   zombie_dead{id}: a zombie in prev's frame whose object now answers isDead;
--   item_added{itemId, fullType, weight, use, worn, rip, clothing} / item_removed{itemId, fullType}: against S.lastInv
--   (a first call without firstSight seeds it silently);
--   door{x, y, z, open, locked}: a door or window whose open state changed between two map records of its square (Map's
--   PZA.map.doorEvents: a scan part's or the watch's, the ring of WATCH_R tiles; a square first seen queues none).
--   death{worldAge, x, y, z, health, zombiesKilled, via}: the local player's death, once per player object
--   (S.playerDeathEvents, at the end of this file).
-- Returns ev and the new frame (cur).
-- Each kind through collect; the damage records are drained whatever the damage reader did, so a raising record is
-- never read twice.
function S.events(p, prev)
    local seen = S.zobj or {}
    local cur = S.frame(p)
    local gameMin = cur.gameMin
    local ev = {}
    collect(ev, "event:damage", damageEvents, gameMin)
    S.damage = {}
    collect(ev, "event:swing", swingEvents, gameMin, p)
    collect(ev, "event:zombie_dead", deathEvents, gameMin, prev, seen, S.zobj or {})
    collect(ev, "event:item", itemEvents, gameMin, p)
    collect(ev, "event:door", doorEvents, gameMin)
    collect(ev, "event:death", S.playerDeathEvents, gameMin, p, cur)
    return ev, cur
end

-- the live zombie whose online id is id, as its object (the IsoZombie the attack skill faces), or nil for an unknown
-- or dead id: the last frame's object for that id first (S.zobj, checked with isDead), else the whole cell list, not
-- the frame's radius
function S.zombieById(p, id)
    if id == nil then return nil end
    local known = S.zobj ~= nil and S.zobj[id] or nil
    if known ~= nil then
        if isDead(known) then return nil end
        return known
    end
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

-- the nearest live zombie as { id, dist } (the runner's snapshot): the last frame's first zombie record, the frame's
-- list being sorted nearest first within ZOMBIE_RADIUS, or nil before the first frame or when it listed none; no cell
-- walk, so a snapshot (every rejected, failed and done act, every scan and rate) costs no Java call
function S.nearestZombie(p)
    local f = S.last
    local z = f ~= nil and f.zombies ~= nil and f.zombies[1] or nil
    if z == nil then return nil end
    return { id = z.id, dist = z.dist }
end

-- the client's OnPlayerDeath (PZA/1.3, ruling P23-AO; the vanilla client hooks it the same way, its handler handed the
-- dead IsoPlayer: ISPostDeathUI.OnPlayerDeath(playerObj), media/lua/client/ISUI/ISPostDeathUI.lua): a call naming the
-- local player (getPlayer(), the identity recordDamage uses) sets S.deathHook to that player, read by the next
-- S.events; another character's death is counted in S.deathRemote and carried nowhere else. Hooked once; the body under
-- pcall, a raise counted in S.deathErrors, never propagated into the game's death path.
S.deathRemote = S.deathRemote or 0
S.deathErrors = S.deathErrors or 0
S.deathHooked = S.deathHooked or false

local function recordDeath(ch)
    local me = getPlayer ~= nil and getPlayer() or nil
    if me ~= nil and ch == me then
        S.deathHook = ch
    else
        S.deathRemote = S.deathRemote + 1
    end
end

function S.onDeath(ch)
    local ok = pcall(recordDeath, ch)
    if not ok then S.deathErrors = S.deathErrors + 1 end
end

if not S.deathHooked and Events ~= nil and Events.OnPlayerDeath ~= nil then
    Events.OnPlayerDeath.Add(S.onDeath)
    S.deathHooked = true
end

-- S.playerDeathEvents, the death{worldAge, x, y, z, health, zombiesKilled, via} reader S.events collects (a field, so
-- this block sits at the end of the file, CLAUDE.md section 5): once per player object (S.deathSent), when the hook named p
-- (via hook) or p's isDead reads true (via isDead), the hook taking precedence; the position and health are the
-- event's own frame's (cur: the client's copy, which can freeze above 0 on a dead character in multiplayer), the kill
-- count the game's getZombieKills (nil, so absent from the line, when that read fails: the schema keeps it optional).
-- The frames go on after it.
function S.playerDeathEvents(ev, gameMin, p, cur)
    if S.deathSent ~= nil and S.deathSent == p then return end
    local via = nil
    if S.deathHook ~= nil and S.deathHook == p then
        via = "hook"
    else
        local okD, dead = PZA.call(p, "isDead")
        if okD and dead == true then via = "isDead" end
    end
    if via == nil then return end
    local okK, kills = PZA.call(p, "getZombieKills")
    if not okK then PZA.missing(S.missing, "getZombieKills") end
    local m, b = cur.me or {}, cur.body or {}
    ev[#ev + 1] = { event = "death", gameMin = gameMin, worldAge = cur.worldAge, x = m.x, y = m.y, z = m.z,
                    health = b.health, zombiesKilled = okK and kills or nil, via = via }
    S.deathSent = p
end

-- me's combat reads (PZA/1.4, ruling P24-C; the jar reads docs/superpowers/specs/2026-10-29-plan-24-jar-reads.md
-- section 2, #4290-#4293): attackers is getSurroundingAttackingZombies(), the drag-down's own count in its no-argument
-- form (crawlers left out: the moving objects on the player's square and its eight neighbours that are zombies
-- targeting the player within 0.9 tiles in an attack or lunge state; the drag-down kills at three, two at sandbox
-- Strength 1); hitReaction is getHitReaction() ("" when it answers no string: every zombie attack that reaches the
-- damage roll sets it, a defended one included, and no swing starts while the player is in that state); dragDown is
-- isDeathDragDown(); aiming (PZA/1.5, ruling P24-G) is isAiming(), the stance an aim holds (PZAgent_Stance.lua), or a
-- swing's own (IsoGameCharacter.isAiming L14779-L14780: true while a hostile animation plays); forceAim (PZA/1.5.4,
-- ruling P24-T) is isForceAim(), the input component's flag the Motor re-asserts every frame while the stance is held,
-- read here after the frame's update: true when the flag survived the frame (not cleared by a run key or a release); aiming shows whether the update used it.
-- Each is one PZA.call read (an absent member nil and named in missing). This block sits at the end
-- of the file (CLAUDE.md section 5: the repo: pointers into Sense keep their lines), so S.frame is wrapped here: the
-- base reader runs, then the five reads land in its me under their own guard, so a raise among them costs these
-- five fields (raise:me:combat), never the rest of me or the frame. S.events and Main call S.frame through the table,
-- so both read the wrapped one; a reload redefines S.frame above and wraps it again once.
-- Cost: the frame runs every max(1, floor(60 / S.RATE)) ticks (Main), every tick at rate 60, so these reads run at
-- that rate. getHitReaction, isDeathDragDown and isAiming are field reads, isForceAim the input component's lookup and
-- its field. getSurroundingAttackingZombies copies the moving
-- objects of nine squares into a static list and walks it (a type test, a target compare and a distance each), and
-- counts only zombies within 0.9 tiles (squared distance under 0.81, the jar's @257), so it is called only when the
-- frame's nearest listed zombie (the list is sorted nearest first, within ZOMBIE_RADIUS) is under NEAR_R tiles, or
-- when the zombie walk could not be read (me.zombiesSeen nil); otherwise attackers is 0 without the call (Task 1b fix
-- 1, review M1).
S.NEAR_R = 2

-- whether the attackers count must be asked: the walk unread, or its nearest listed zombie under NEAR_R tiles
local function attackersNear(f)
    if f.me.zombiesSeen == nil then return true end
    local z = f.zombies ~= nil and f.zombies[1] or nil
    return z ~= nil and type(z.dist) == "number" and z.dist < S.NEAR_R
end

local function meCombat(p, f)
    local m = f.me
    if attackersNear(f) then
        get(m, "attackers", p, "getSurroundingAttackingZombies")
    else
        m.attackers = 0
    end
    local okH, hr = get(m, "hitReaction", p, "getHitReaction")
    if okH then
        if type(hr) == "string" then m.hitReaction = hr else m.hitReaction = "" end
    end
    get(m, "dragDown", p, "isDeathDragDown")
    get(m, "aiming", p, "isAiming")
    get(m, "forceAim", p, "isForceAim")
end

local frameBase = S.frame
function S.frame(p)
    local f = frameBase(p)
    guarded("me:combat", meCombat, p, f)
    return f
end

-- body.parts' records (PZA/1.5, ruling P24-G; docs/superpowers/specs/2026-10-29-plan-24-jar-reads-2.md section 3, rows
-- T6b.5 and T6b.6): body's walk of getBodyParts calls S.notePart(b, i, part, h) for every part whose health reads (that
-- one line edited in place, so no repo: pointer into Sense moves). It lists a part whose health is under 100, which
-- reads bandaged(), or which reads bleeding() (asked only while body's getNumPartsBleeding is above 0 or unread), as
-- the record { i, h, bleeding, bleedingTime, bandaged, bandageLife, bandageDirty, deep, infected }: bleeding() (false
-- without the call when no part bleeds), getBleedingTime() (kept under a bandage, which clears the flag but not the
-- time), bandaged(), getBandageLife() and isBandageDirty() (its life at 0 or less; both nil on an unbandaged part,
-- whose life reads 0 and so dirty), deepWounded() and isInfectedWound(). An absent member leaves its field nil and is
-- named in missing. Cost a frame: bandaged() on each of the 17 parts beside getHealth (bleeding() too while a part
-- bleeds), then five or six reads per listed part; the body group is elided from a delta frame while it is unchanged.
function S.notePart(b, i, part, h)
    local okB, band = PZA.call(part, "bandaged")
    if not okB then PZA.missing(S.missing, "bandaged") end
    local bleed = false
    if b.bleeding == nil or (type(b.bleeding) == "number" and b.bleeding > 0) then
        local okL, bl = PZA.call(part, "bleeding")
        if okL then bleed = bl == true else bleed = nil; PZA.missing(S.missing, "bleeding") end
    end
    if h >= 100 and band ~= true and bleed ~= true then return end
    local r = { i = i, h = h, bleeding = bleed }
    if okB then r.bandaged = band == true end
    get(r, "bleedingTime", part, "getBleedingTime")
    if band == true then
        get(r, "bandageLife", part, "getBandageLife")
        get(r, "bandageDirty", part, "isBandageDirty")
    end
    get(r, "deep", part, "deepWounded")
    get(r, "infected", part, "isInfectedWound")
    b.parts[#b.parts + 1] = r
end

-- item_changed{itemId, use, fluid, amount, worn, rip} (PZA/1.5.1, Task 9 fix 1, review major 1): S.invIds reads an item's use once,
-- at its first sight, so a bottle a fill filled read container and one drunk empty read water for good. A skill that
-- changes a held item's contents (fill, consume, wash, rip: PZAgent_Tend.lua's end hooks) calls S.recheck(id, amount0)
-- when it ends, amount0 its fluid amount when it began (nil when it read none). For RECHECK_MS after that, each S.events
-- call reads the item again while it is held: its fluid amount (getFluidContainer():getAmount(), three Java calls), and
-- once the amount has held still SETTLE_MS (a drink runs on after consume's done, which lands on the first fall) and
-- differs from the last one reported (amount0 first), or at the first read, the use through W.useOf again. An
-- item_changed event is emitted when the use or the settled amount changed, carrying the new use, the primary fluid's
-- getFluidTypeString() (nil when empty) and the amount; the inventory's entry (S.lastInv[id]) takes the new use, so the
-- diff and a later first-sight read agree. The mark ends with the window, the item gone (its item_removed says so), an
-- item without a fluid container after its one use read, or an amount settled at the one last reported. Appended here (CLAUDE.md section 5: the repo: pointers into
-- Sense keep their lines); S.events is wrapped, and Main calls it through the table.
S.RECHECK_MS = 30000       -- a mark lives this long after its skill's end (consume's CONSUME_MS and some)
S.SETTLE_MS = 1000         -- an amount held still this long is settled
S.AMOUNT_EPS = 0.0001      -- litres: a change under this is no change
S.recheckIds = S.recheckIds or {}

function S.recheck(id, amount0)
    if id == nil then return end
    S.recheckIds[id] = { untilMs = PZA.now() + S.RECHECK_MS, reported = amount0, last = nil, stillAt = nil,
                         first = true }
end

local function amountOf(it)
    local _, fc = PZA.call(it, "getFluidContainer")
    if fc == nil then return nil, nil end
    local ok, a = PZA.call(fc, "getAmount")
    if ok and type(a) == "number" then return a, fc end
    return nil, fc
end

local function fluidName(fc)
    local _, f = PZA.call(fc, "getPrimaryFluid")
    local _, ft = PZA.call(f, "getFluidTypeString")
    if type(ft) == "string" then return ft end
    return nil
end

local function differs(a, b)
    if a == nil or b == nil then return a ~= b end
    return math.abs(a - b) > S.AMOUNT_EPS
end

-- one mark's read: true when the mark is done with
local function recheckOne(ev, gameMin, p, id, m, now)
    local k = S.lastInv ~= nil and S.lastInv[id] or nil
    local it = k ~= nil and PZA.skills ~= nil and PZA.skills.itemById(p, id) or nil
    if it == nil then return true end
    if W.isA(it, "Clothing") then return S.recheckClothing(ev, gameMin, id, k, it, m, now) end
    local a, fc = amountOf(it)
    if differs(a, m.last) then m.last, m.stillAt = a, now end
    local settled = m.stillAt ~= nil and (now - m.stillAt >= S.SETTLE_MS or now >= m.untilMs)
    local moved = settled and m.reported ~= nil and differs(a, m.reported)
    if m.first or moved then
        local use = W.useOf(it)
        if use ~= k.use or moved then
            local rec = { fullType = k.fullType, weight = k.weight, use = use, worn = W.wornOf(it), rip = W.ripOf(it),
                          clothing = W.clothingOf(it) }
            ev[#ev + 1] = S.record({ event = "item_changed", gameMin = gameMin, itemId = id,
                                     fluid = fc ~= nil and fluidName(fc) or nil, amount = a }, rec)
            S.lastInv[id] = rec
            m.reported = a
        end
        if m.reported == nil then m.reported = a end
        m.first = false
        return fc == nil or now >= m.untilMs
    end
    return now >= m.untilMs or (settled and not differs(a, m.reported))
end

local function changedEvents(ev, gameMin, p)
    if S.lastInv == nil then return end
    local now = PZA.now()
    for id, m in pairs(S.recheckIds) do
        if recheckOne(ev, gameMin, p, id, m, now) then S.recheckIds[id] = nil end
    end
end

local eventsBase = S.events
function S.events(p, prev)
    local ev, cur = eventsBase(p, prev)
    collect(ev, "event:item_changed", changedEvents, cur.gameMin, p)
    return ev, cur
end

-- the inventory record's item fields (PZA/1.5.2, Task 9 fix 4, review-t10 minor 7): ev (an item_added or item_changed
-- event) takes the entry k's use, and its worn and rip (PZAgent_World.lua's W.wornOf and W.ripOf, read with the use:
-- at the item's first sight, and again at an item_changed), each elided when false or absent (a nil key is no key on
-- the wire), and (PZA/1.6) its clothing record (W.clothingOf, nil and so elided for an item that is not Clothing). Appended here (CLAUDE.md section 5: the repo: pointers into Sense keep their lines); itemAdded and
-- recheckOne call it through the table.
function S.record(ev, k)
    ev.use, ev.worn, ev.rip, ev.clothing = k.use, k.worn, k.rip, k.clothing   -- PZA/1.6: the clothing record
    return ev
end

-- ---- the clothing (PZA/1.6, Task 9 fix 9, review-t18 ruling 5; jar-reads-2 section 10) -----------------------------
-- S.recheckClothing: recheckOne's branch for a marked item whose class is Clothing (the wear skill marks the garment it
-- put on and the one it replaced at its end, PZAgent_Tend.lua). The item's record is read again (its use, worn, rip and
-- W.clothingOf) and an item_changed event (no fluid, no amount) is emitted when the use, worn or the clothing record
-- (compared by its PZA.json encoding, keys sorted) differs from the inventory's entry, which takes the new record; the
-- mark ends then, or at its window's end (RECHECK_MS), so a worn flag that reaches the client late is still reported.
-- Appended here (CLAUDE.md section 5: the repo: pointers into Sense keep their lines); recheckOne calls it through S.
local function clothingKey(c)
    if c == nil then return "" end
    return PZA.json(c)
end

function S.recheckClothing(ev, gameMin, id, k, it, m, now)
    local rec = { fullType = k.fullType, weight = k.weight, use = W.useOf(it), worn = W.wornOf(it), rip = W.ripOf(it),
                  clothing = W.clothingOf(it) }
    if rec.use ~= k.use or rec.worn ~= k.worn or clothingKey(rec.clothing) ~= clothingKey(k.clothing) then
        ev[#ev + 1] = S.record({ event = "item_changed", gameMin = gameMin, itemId = id }, rec)
        S.lastInv[id] = rec
        return true
    end
    return now >= m.untilMs
end

-- me.worn: the body locations the player's worn clothing covers, each { loc, bite, scratch } with the defences of the
-- Clothing items worn there summed (one item a location but for a multi-item group), in the order getWornItems() lists
-- them (WornItems.size/get, each WornItem's getLocation() as its registry name and getItem(); an item whose class is
-- not Clothing, a bag on the back, is left out, and a location whose name cannot be read too). The defences are the
-- items' own getBiteDefense and getScratchDefense (0 at condition 0), the values the engine sums per body part for a
-- zombie's bite or scratch roll (jar-reads-2 section 10): the planner compares a candidate garment's bite and scratch
-- with the worn ones at its loc. Elided (nil, null on the wire) on every frame but one whose list differs from the last
-- one carried, so a reader keeps the last list it saw; the first frame carries it ([] when nothing is worn). The list is
-- read on a frame after an item, item_changed or damage event (S.wornDirty, a hit can hole a garment or lower its
-- condition) and on every WORN_EVERY-th frame otherwise. An unreadable getWornItems leaves me.worn nil and is named in
-- missing; a raise among these reads costs me.worn alone (raise:me:worn). Cost: two calls a list, seven a worn item.
-- PZA/1.6.1 (Task 9 fix 10): each entry also carries holes (the sum of the items' getHolesNumber) and cond (the lowest
-- getCondition among them): the engine drops a garment from a body part wherever it has a hole there
-- (IsoGameCharacter.getBodyPartClothingDefense @0-@230 L13615-L13655, Clothing.getDefForPart @0-@139 L957-L989), and
-- getBiteDefense and getScratchDefense ignore holes, so an entry with holes above 0 defends less than its bite and
-- scratch say. A zombie's attack turned by the clothing makes a hole and returns with no wound (AddRandomDamageFromZombie
-- L1542-L1544), so no damage event follows it: the list is also read on the frame after the hit reaction rises (a landed
-- or a turned attack sets it, S.hitSeen; read again when it changes or ends) or the attackers count rises from 0.
S.WORN_EVERY = 10         -- frames between two reads of the worn list with no event to prompt one
S.wornFrames = 0
S.wornDirty = true
S.wornKey = nil
S.hitSeen = ""            -- the last frame's hitReaction, and S.attSeen its attackers: a rise reads the worn list again
S.attSeen = 0

function S.wornOf(p)
    local okW, wi = PZA.call(p, "getWornItems")
    local okN, n = PZA.call(wi, "size")
    if not okW or not okN or type(n) ~= "number" then
        PZA.missing(S.missing, "getWornItems")
        return nil
    end
    local out, byLoc = {}, {}
    for i = 0, n - 1 do
        local _, w = PZA.call(wi, "get", i)
        local _, it = PZA.call(w, "getItem")
        local _, loc = PZA.call(w, "getLocation")
        if it ~= nil and loc ~= nil and W.isA(it, "Clothing") then
            local name = tostring(loc)
            local r = byLoc[name]
            if r == nil then
                r = { loc = name, bite = 0, scratch = 0, holes = 0 }
                byLoc[name] = r
                out[#out + 1] = r
            end
            local _, b = PZA.call(it, "getBiteDefense")
            local _, sc = PZA.call(it, "getScratchDefense")
            if type(b) == "number" then r.bite = r.bite + b end
            if type(sc) == "number" then r.scratch = r.scratch + sc end
            local _, h = PZA.call(it, "getHolesNumber")
            local _, c = PZA.call(it, "getCondition")
            if type(h) == "number" then r.holes = r.holes + h end
            if type(c) == "number" and (r.cond == nil or c < r.cond) then r.cond = c end
        end
    end
    return out
end

local function meWorn(p, f)
    S.wornFrames = S.wornFrames + 1
    local hr, att = f.me.hitReaction, f.me.attackers
    if type(hr) == "string" and hr ~= S.hitSeen then S.wornDirty = true end   -- rises, changes or ends
    if type(att) == "number" and att > 0 and S.attSeen == 0 then S.wornDirty = true end
    if type(hr) == "string" then S.hitSeen = hr end
    if type(att) == "number" then S.attSeen = att end
    if not S.wornDirty and S.wornFrames % S.WORN_EVERY ~= 1 then return end
    S.wornDirty = false
    local list = S.wornOf(p)
    if list == nil then return end
    local key = PZA.json(list)
    if key ~= S.wornKey then
        f.me.worn = list
        S.wornKey = key
    end
end

local frameWornBase = S.frame
function S.frame(p)
    local f = frameWornBase(p)
    if f.me ~= nil then guarded("me:worn", meWorn, p, f) end
    return f
end

local WORN_KINDS = { item_added = true, item_removed = true, item_changed = true, damage = true }
local eventsWornBase = S.events
function S.events(p, prev)
    local ev, cur = eventsWornBase(p, prev)
    for i = 1, #ev do
        if WORN_KINDS[ev[i].event] then S.wornDirty = true end
    end
    return ev, cur
end

-- ---- the arms' strain and pain, the loaded grid's width (PZA/1.7, Task 9 fix 11; jar-reads-2 sections 11 and 13) -------
-- body.armPain: the summed getPain() of the six arm parts Hand_L, Hand_R, ForeArm_L, ForeArm_R, UpperArm_L, UpperArm_R
-- (BodyDamage.getBodyPart(BodyPartType)), the sum the engine divides a melee swing's damage by once it passes 10 (#4370);
-- body.strain = {l, r}: each side's largest getStiffness() over its three arm parts (#4368, #4369). Both rounded to 0.01
-- (the stiffness decays by a small step each server update), so the body group elides while they hold; the six part objects
-- are fetched once per BodyDamage (S.arms). An absent BodyPartType constant, getBodyPart, getPain or getStiffness leaves its
-- field nil and is named in missing; a raise costs the two fields alone (raise:body:arms). Cost a frame: twelve Java calls.
-- me.loadedWidth: getCell():getChunkMap(0):getWidthInTiles(), the side of the client's loaded square grid in tiles (104 at
-- 1280 x 720, 152 at 1920 x 1080; #4375): carried on the first frame and on a frame where it changed, nil otherwise (a reader
-- keeps the last value, as for me.worn), re-read every WIDTH_EVERY-th frame. Appended here (CLAUDE.md section 5: the repo:
-- pointers into Sense keep their lines); S.frame is wrapped and Main calls it through the table.
S.WIDTH_EVERY = 100       -- frames between two reads of the loaded grid's width
S.widthFrames = 0
S.widthSeen = nil
S.armBd = nil
S.arms = nil
local ARM_SIDES = { { "l", { "Hand_L", "ForeArm_L", "UpperArm_L" } }, { "r", { "Hand_R", "ForeArm_R", "UpperArm_R" } } }

local function round2(v) return math.floor(v * 100 + 0.5) / 100 end

-- the six arm part objects of body damage bd as { side, part } entries, nil when one cannot be had
local function armParts(bd)
    if S.armBd == bd and S.arms ~= nil then return S.arms end
    local out = {}
    for _, side in ipairs(ARM_SIDES) do
        for _, name in ipairs(side[2]) do
            local t = BodyPartType ~= nil and BodyPartType[name] or nil
            if t == nil then PZA.missing(S.missing, "BodyPartType." .. name); return nil end
            local ok, part = PZA.call(bd, "getBodyPart", t)
            if not ok then PZA.missing(S.missing, "getBodyPart"); return nil end
            if part == nil then return nil end
            out[#out + 1] = { side = side[1], part = part }
        end
    end
    S.armBd, S.arms = bd, out
    return out
end

local function armReads(p, b)
    local okB, bd = PZA.call(p, "getBodyDamage")
    if not okB then return end
    local arms = armParts(bd)
    if arms == nil then return end
    local pain, painOk, stiffOk = 0, true, true
    local big = { l = 0, r = 0 }
    for i = 1, #arms do
        local a = arms[i]
        local okP, v = PZA.call(a.part, "getPain")
        if okP and type(v) == "number" then pain = pain + v else painOk = false; PZA.missing(S.missing, "getPain") end
        local okS, s = PZA.call(a.part, "getStiffness")
        if okS and type(s) == "number" then
            if s > big[a.side] then big[a.side] = s end
        else
            stiffOk = false
            PZA.missing(S.missing, "getStiffness")
        end
    end
    if painOk then b.armPain = round2(pain) end
    if stiffOk then b.strain = { l = round2(big.l), r = round2(big.r) } end
end

local function meWidth(p, f)
    S.widthFrames = S.widthFrames + 1
    if S.widthSeen ~= nil and S.widthFrames % S.WIDTH_EVERY ~= 1 then return end
    local cell = getCell ~= nil and getCell() or nil
    local okM, cm = PZA.call(cell, "getChunkMap", 0)
    if not okM then PZA.missing(S.missing, "getChunkMap"); return end
    local okW, w = PZA.call(cm, "getWidthInTiles")
    if not okW or type(w) ~= "number" then PZA.missing(S.missing, "getWidthInTiles"); return end
    if w ~= S.widthSeen then
        f.me.loadedWidth = w
        S.widthSeen = w
    end
end

local frameArmsBase = S.frame
function S.frame(p)
    local f = frameArmsBase(p)
    if f.body ~= nil then guarded("body:arms", armReads, p, f.body) end
    if f.me ~= nil then guarded("me:width", meWidth, p, f) end
    return f
end

-- zombie.onFloor (PZA/1.7, Task 9 fix 11): true when a listed zombie lies on the floor, isOnFloor() read through the frame's
-- own object map (S.zobj, the walk's id to object); nil when it stands (null on the wire), so a frame of standing zombies
-- carries none. One Java call a listed zombie; an absent member leaves every record's field nil and is named in missing. It
-- is the planner's read for the stomp (a fallen target), and for a weapon finish on a fallen zombie. Appended here
-- (CLAUDE.md section 5: the repo: pointers into Sense keep their lines); S.frame is wrapped, Main calls it through the table.
local function zombiesFloor(f)
    local objs = S.zobj
    if objs == nil or f.zombies == nil then return end
    for i = 1, #f.zombies do
        local rec = f.zombies[i]
        local z = rec.id ~= nil and objs[rec.id] or nil
        if z ~= nil then
            local ok, v = PZA.call(z, "isOnFloor")
            if not ok then PZA.missing(S.missing, "isOnFloor") end
            if v == true then rec.onFloor = true end
        end
    end
end

local frameFloorBase = S.frame
function S.frame(p)
    local f = frameFloorBase(p)
    guarded("zombies:floor", zombiesFloor, f)
    return f
end
