-- PZAgent_Hutch.lua — the hutch guard (Plan 28 Task 1c, ruling P28-G). The reading (Plan 28's jar read on 42.21, jar
-- 4a0e9546ec [T90.1, T90.2]): E20 and E21, the chain's sessions on the fixture agent, each ended on the client's
-- NullPointerException at IsoHutch.removeFromWorld (IsoHutch.java:1095): it calls removeFromUpdateLists on every value
-- of the hutch's animalInside map with no null test, and the client runs it from every chunk its window drops
-- (IsoChunkMap.Down both times: the character crossed y = 10648 going south, unloading chunk row 1324). On a client the
-- map holds only what the animal packets put there, and NetworkPlayerAI.parse(AnimalPacket) writes null at an animal's
-- recorded slot and refills only the packet's slot, so an animal the server moves (a hen into a nest box) leaves a null.
-- The ruling: every tick on a ready tick (Main calls H.guard after the init tick, under its own pcall), for each hutch
-- in H.HUTCHES whose master square is known, getHutch(x, y, 0) is read; with a hutch loaded its map
-- (hutch:getAnimalInside(), read again only when getHutch answers a different object: a reloaded chunk builds a new
-- hutch, and the identity check alone catches a new object that appears with no nil tick between) is asked
-- containsValue(nil), and on true the map is cleared, counted in H.clears and logged through PZA.log with the tick, the
-- hutch's square, the entries cleared and the clears left unlogged since the hutch's last line. Nothing else touches the
-- hutch. A hutch whose square is not yet known is swept one row of its chunk a tick, 8 squares, so its 64 squares take
-- at most 8 ticks (getHutch answers each tile's IsoHutch, a slave tile's included: a slave, isSlave true, is passed
-- over, and the first master found is kept for the session, since a map hutch never moves). Cost a tick: 8 getHutch a
-- hutch while sweeping (isSlave on a tile that holds a hutch), one getHutch a found hutch while unloaded, getHutch and
-- containsValue a loaded hutch (getAnimalInside once more on its first read of an object), size and clear on a clear.
-- Per packet: NetworkPlayerAI.parse's nest-box branch (L421-L425) never resets the client's hutchPosition, so every later
-- packet for a hen still sitting in a nest box writes the null again (L410); the guard clears once a packet for as long
-- as she sits, every clear counted in H.clears, and its console line is rate-limited to one a hutch per HUTCH_LOG_S.
-- Nil crosses to Java as null: Kahlua passes a Lua nil for an object parameter as null (vanilla's own
-- player:setPrimaryHandItem(nil), media/lua/client/Farming/CFarming_Interact.lua:123), so containsValue(nil) is
-- HashMap.containsValue(null); the call is made directly with its literal nil (PZA.field index-first), never through
-- PZA.call's varargs. Every Java member is reached through PZA.call index-first: an absent getHutch,
-- getAnimalInside, containsValue or clear is named in H.missing once and the guard stands down (H.off), never nil-called,
-- with one console line naming the member; a raise (Main's pcall sets H.off and names raise:hutch) takes the same line on
-- the next tick, so a silent switch-off never reads as a guard that found no null.
-- Cost if wrong: the client's copy of the hutch's animals emptied (the server's is the truth; the next animal packet
-- refills its slot, NetworkPlayerAI.parse); a one-tick race (a packet's null written after this tick's OnTick and before
-- the next tick's IsoChunkMap.ProcessChunkPos still reaches the unload), which recurs with every packet that rewrites the
-- null, not once a laying; a hutch this table does not know (another fixture) unguarded: a new fixture adds its rows.
-- The table's provenance (the read's section 4): the fixture agent's provisioned server save
-- (testing/fixtures/agent/cache/server/Saves/Multiplayer/pzt/map/, per machine) holds the hen hutch's base sprite
-- location_farm_accesories_01_50 in chunk file map/1340/1324.bin (tiles x 10720-10727, y 10592-10599) and the turkey
-- hutch's location_farm_accesories_01_66 in map/1347/1329.bin (x 10776-10783, y 10632-10639); no other chunk file holds
-- a hutch base sprite. Each row is the chunk's tile origin (x0, y0), its tiles x0..x0+7 by y0..y0+7.
-- Kahlua rules: no goto, no %d on floats (every number reaches a log line through tostring), no # on a Java list, no %g.
-- This file loads before Link and Main (client files load by name), and Main reaches it only at tick time.
PZA.hutch = PZA.hutch or {}
local H = PZA.hutch
H.CHUNK = 8
H.HUTCHES = {
    { name = "hen", x0 = 10720, y0 = 10592 },      -- map/1340/1324.bin, location_farm_accesories_01_50
    { name = "turkey", x0 = 10776, y0 = 10632 },   -- map/1347/1329.bin, location_farm_accesories_01_66
}
-- the console's clear line, at most one a hutch per this many seconds of the 1 ms clock (PZA.now): a hen sitting in a
-- nest box has every packet rewrite the null, so an unlimited line would print once a packet; H.clears counts them all
H.HUTCH_LOG_S = 10
H.missing = {}
H.clears = 0
H.errors = 0
H.off = false
H.offLogged = false

-- the one stand-down line, naming the absent member or the raise (raise:hutch, Main's)
local function logStandDown(what)
    H.offLogged = true
    PZA.log("hutch guard: stood down, " .. tostring(what))
end

-- an absent member: named once and logged once, and the guard stands down
local function standDown(name)
    PZA.missing(H.missing, name)
    H.off = true
    logStandDown(name .. " absent")
end

-- true when the square (x, y) holds a hutch that is not a slave tile
local function isMaster(x, y)
    local h = getHutch(x, y, 0)
    if h == nil then return false end
    local okS, slave = PZA.call(h, "isSlave")
    if not okS then PZA.missing(H.missing, "isSlave") end
    return slave ~= true
end

-- one row of the hutch's chunk a tick (8 squares), the row cursor wrapping; the first master tile found is kept
local function sweep(rec)
    local r = rec.row or 0
    rec.row = (r + 1) % H.CHUNK
    local y = rec.y0 + r
    for c = 0, H.CHUNK - 1 do
        local x = rec.x0 + c
        if isMaster(x, y) then
            rec.x, rec.y = x, y
            PZA.log("hutch guard: found the " .. rec.name .. " hutch at " .. tostring(x) .. "," .. tostring(y))
            return
        end
    end
end

-- the clear's console line: a hutch's first clear, then at most one per HUTCH_LOG_S, each naming the clears left
-- unlogged since the hutch's previous line
local function logClear(rec, tick, size)
    local now = PZA.now()
    if rec.logMs ~= nil and now - rec.logMs < H.HUTCH_LOG_S * 1000 then
        rec.unlogged = (rec.unlogged or 0) + 1
        return
    end
    PZA.log("hutch guard: cleared the " .. rec.name .. " hutch at " .. tostring(rec.x) .. "," .. tostring(rec.y)
            .. " (tick " .. tostring(tick) .. ", " .. tostring(size) .. " entries, clear " .. tostring(H.clears)
            .. ", " .. tostring(rec.unlogged or 0) .. " unlogged since the last line)")
    rec.logMs = now
    rec.unlogged = 0
end

-- the known hutch's map cleared when it holds a null; an unloaded hutch is let go (never held across an unload)
local function guardOne(rec, tick)
    if rec.x == nil then
        sweep(rec)
        return
    end
    local h = getHutch(rec.x, rec.y, 0)
    if h == nil then
        rec.obj, rec.map = nil, nil
        return
    end
    if not rawequal(h, rec.obj) then
        local okA, m = PZA.call(h, "getAnimalInside")
        if not okA then return standDown("getAnimalInside") end
        rec.obj, rec.map = h, m
    end
    local m = rec.map
    if m == nil then return end
    local okC, cv = PZA.field(m, "containsValue")
    if not okC then return standDown("containsValue") end
    if cv(m, nil) ~= true then return end
    local _, size = PZA.call(m, "size")
    local okX = PZA.call(m, "clear")
    if not okX then return standDown("clear") end
    H.clears = H.clears + 1
    logClear(rec, tick, size)
end

-- the tick's guard over every row of H.HUTCHES; the global getHutch index-checked first. Stood down, it logs once
-- the stand-down not yet logged (a raise: Main's pcall set H.off and named raise:hutch last in H.missing)
function H.guard(tick)
    if H.off then
        if not H.offLogged then logStandDown(H.missing[#H.missing] or "raise") end
        return
    end
    if getHutch == nil then return standDown("getHutch") end
    for i = 1, #H.HUTCHES do
        guardOne(H.HUTCHES[i], tick)
        if H.off then return end
    end
end
