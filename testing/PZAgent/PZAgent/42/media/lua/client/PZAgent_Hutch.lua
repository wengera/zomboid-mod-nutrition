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
-- hutch) is asked containsValue(nil), and on true the map is cleared, counted in H.clears and logged through PZA.log
-- with the tick, the hutch's square and the entries cleared. Nothing else touches the hutch. A hutch whose square is not
-- yet known is swept one square a tick over its chunk's 64 squares (getHutch answers each tile's IsoHutch, a slave
-- tile's included: a slave, isSlave true, is passed over, and the first master found is kept for the session, since a
-- map hutch never moves). Cost a tick: one getHutch a hutch while sweeping or unloaded, getHutch and containsValue a
-- loaded hutch (getAnimalInside once more on its first read), size and clear on a clear.
-- Nil crosses to Java as null: Kahlua passes a Lua nil for an object parameter as null (vanilla's own
-- player:setPrimaryHandItem(nil), media/lua/client/Farming/CFarming_Interact.lua:123), so containsValue(nil) is
-- HashMap.containsValue(null); the call is made directly with its literal nil (PZA.field index-first), never through
-- PZA.call's varargs. Every Java member is reached through PZA.call index-first: an absent getHutch,
-- getAnimalInside, containsValue or clear is named in H.missing once and the guard stands down (H.off), never nil-called.
-- Cost if wrong: the client's copy of the hutch's animals emptied (the server's is the truth; the next animal packet
-- refills its slot, NetworkPlayerAI.parse); a one-tick race (a packet's null written after this tick's OnTick and before
-- the next tick's IsoChunkMap.ProcessChunkPos still reaches the unload); a hutch this table does not know (another
-- fixture) unguarded: a new fixture adds its rows.
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
H.missing = {}
H.clears = 0
H.errors = 0
H.off = false

-- an absent member: named once, and the guard stands down
local function standDown(name)
    PZA.missing(H.missing, name)
    H.off = true
end

-- one square of the hutch's chunk a tick, the cursor wrapping; the first master tile found is kept
local function sweep(rec)
    local n = H.CHUNK * H.CHUNK
    local i = rec.i or 0
    rec.i = (i + 1) % n
    local x = rec.x0 + i % H.CHUNK
    local y = rec.y0 + math.floor(i / H.CHUNK)
    local h = getHutch(x, y, 0)
    if h == nil then return end
    local okS, slave = PZA.call(h, "isSlave")
    if not okS then PZA.missing(H.missing, "isSlave") end
    if slave == true then return end
    rec.x, rec.y = x, y
    PZA.log("hutch guard: found the " .. rec.name .. " hutch at " .. tostring(x) .. "," .. tostring(y))
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
    PZA.log("hutch guard: cleared the " .. rec.name .. " hutch at " .. tostring(rec.x) .. "," .. tostring(rec.y)
            .. " (tick " .. tostring(tick) .. ", " .. tostring(size) .. " entries, clear " .. tostring(H.clears) .. ")")
end

-- the tick's guard over every row of H.HUTCHES; the global getHutch index-checked first
function H.guard(tick)
    if H.off then return end
    if getHutch == nil then return standDown("getHutch") end
    for i = 1, #H.HUTCHES do
        guardOne(H.HUTCHES[i], tick)
        if H.off then return end
    end
end
