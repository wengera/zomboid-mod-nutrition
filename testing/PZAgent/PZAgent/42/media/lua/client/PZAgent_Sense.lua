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

-- the inventory by item id: { [id] = { fullType, weight, use } }, walked by getItems' size/get; an id already in known
-- reuses its entry (its full type, weight and use are read once, at its first sight). nil when the inventory or its list
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
                k.use = W.useOf(it)
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
    return { event = "item_added", gameMin = gameMin, itemId = id, fullType = k.fullType, weight = k.weight, use = k.use }
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
        ev[#ev + 1] = { event = "door", gameMin = gameMin, x = d.x, y = d.y, z = d.z, open = d.open }
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
--   item_added{itemId, fullType, weight, use} / item_removed{itemId, fullType}: the inventory's ids against S.lastInv
--   (a first call without firstSight seeds it silently);
--   door{x, y, z, open}: a door or window whose open state changed between two map records of its square (the map's
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
-- isDeathDragDown(). Each is one PZA.call read (an absent member nil and named in missing). This block sits at the end
-- of the file (CLAUDE.md section 5: the repo: pointers into Sense keep their lines), so S.frame is wrapped here: the
-- base reader runs, then the three reads land in its me under their own guard, so a raise among them costs these
-- three fields (raise:me:combat), never the rest of me or the frame. S.events and Main call S.frame through the table,
-- so both read the wrapped one; a reload redefines S.frame above and wraps it again once.
-- Cost: the frame runs every max(1, floor(60 / S.RATE)) ticks (Main), every tick at rate 60, so these reads run at
-- that rate. getHitReaction and isDeathDragDown are field reads. getSurroundingAttackingZombies copies the moving
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
end

local frameBase = S.frame
function S.frame(p)
    local f = frameBase(p)
    guarded("me:combat", meCombat, p, f)
    return f
end
