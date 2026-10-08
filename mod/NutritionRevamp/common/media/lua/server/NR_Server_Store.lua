-- NR_Server_Store.lua -- the durable per-player store: one global modData table keyed by
-- username (server-lifecycle rules #2410, #3287; spec § 4.8), cached server-side, inputs only,
-- never transmitted (#2416) and never player modData (#1042). Runs in both Lua states; every
-- write below is behind NutritionRevamp.isServer().
--
-- The load (Plan 8 ruling 5, ruling T4-1): the first S.get of a username in a sight -- the players' walk
-- calls it at first sight, before the first-sight hooks; a mirror request or an eat that comes first takes
-- it -- runs K.store.fillInPlace on the stored record: the inputs are kept, every derived field dropped for
-- the slow minute to rebuild, and the version set to K.store.VERSION, all in the record's OWN table, so every
-- handle held on it (NR_Server_Fast's h.record) reads the loaded record with no re-point. The load is
-- idempotent and runs at every first sight (derived on read); a record whose version moved logs
-- "store: migrated <username> v<old> -> v<new>" once (a record with no version is v1). A departure (the
-- players' onDeparture hook) forgets the sight, so a return loads again; a swapped records table (a new
-- OnInitGlobalModData attach) forgets every sight. A load that raises leaves the record as it was, logged.
local NR = NutritionRevamp
NR.server.store = { name = "NutritionRevamp.players", records = nil, loaded = {}, loadedFor = nil, wired = false,
                    stats = { loads = 0, migrations = 0, created = 0, failures = 0 } }
local S = NR.server.store

-- ModData.getOrCreate creates the table when the file did not hold it; OnInitGlobalModData's
-- boolean is the world dictionary's new-game flag, which read true on reload boots too (#3287, #3284), so the table is fetched whenever it is
-- found missing, not only on a new world.
function S.attach()
    if S.records ~= nil then return S.records end
    if ModData == nil then return nil end
    -- ModData.getOrCreate is a static bound with a DOT call: passing the table as a first argument
    -- raises "expected argument of type String" (acceptance run x131-20261004-175014).
    local fn = ModData.getOrCreate
    if fn == nil then return nil end
    local ok, t = pcall(fn, S.name)
    if ok and t ~= nil then S.records = t end
    return S.records
end

-- A fresh record at the current version (K.store.new: the identity fields only).
function S.new(username, worldAgeHours)
    return NR.kernel.store.new(username, worldAgeHours)
end

-- The sight set of the records table t: a different table than the one the set was kept for starts empty.
local function sights(t)
    if S.loadedFor ~= t then
        S.loaded = {}
        S.loadedFor = t
    end
    return S.loaded
end

-- The load of a stored record r, in place (the header). Returns r.
function S.load(username, r)
    local old = r.v
    if old == nil then old = 1 end
    local records = NR.data and NR.data.records
    local ok, err = pcall(NR.kernel.store.fillInPlace, r, r, records and records.ORDER, records)
    if not ok then
        S.stats.failures = S.stats.failures + 1
        NR.log.say(2, "store: load failed for " .. tostring(username) .. ": " .. tostring(err))
        return r
    end
    S.stats.loads = S.stats.loads + 1
    if r.v ~= old then
        S.stats.migrations = S.stats.migrations + 1
        NR.log.say(2, "store: migrated " .. tostring(username) .. " v" .. tostring(old) .. " -> v" .. tostring(r.v))
    end
    return r
end

function S.get(username, worldAgeHours)
    local t = S.attach()
    if t == nil then return nil end
    local seen = sights(t)
    local r = t[username]
    if r == nil then
        -- Plan 11 Task 3: a failed clock read never creates a record stamped 0
        if worldAgeHours == nil then return nil end
        r = S.new(username, worldAgeHours)
        t[username] = r
        seen[username] = true
        S.stats.created = S.stats.created + 1
        NR.log.say(3, "store: new record for " .. tostring(username))
        return r
    end
    if seen[username] ~= true then
        seen[username] = true
        S.load(username, r)
    end
    return r
end

-- A departure: the sight forgotten, so the next first sight loads the record again.
function S.forget(username)
    if username ~= nil and S.loaded ~= nil then S.loaded[username] = nil end
end

-- A respawn: the character is new, the record starts fresh, the reset count carries over so
-- (S.reset REPLACES the table — the one place a cached handle such as NR_Server_Fast's h.record goes
-- stale for up to a minute, the respawn exception to the in-place load above; Fast's limitation names it)
-- a later reading can tell a returning player from a new one.
function S.reset(username, worldAgeHours)
    local t = S.attach()
    if t == nil then return nil end
    local old = t[username]
    local r = S.new(username, worldAgeHours)
    r.resets = (old and old.resets or 0) + 1
    t[username] = r
    sights(t)[username] = true
    NR.log.say(2, "store: reset record for " .. tostring(username) .. " (reset " .. tostring(r.resets) .. ")")
    return r
end

if Events ~= nil and Events.OnInitGlobalModData ~= nil then
    Events.OnInitGlobalModData.Add(function(isNewGame)
        if not NR.isServer() then return end
        S.records = nil
        S.attach()
        NR.log.say(2, "store attached (new world: " .. tostring(isNewGame) .. ")")
    end)
end

-- Wiring: the departure hook, at OnServerStarted (this file sorts after NR_Server_Players).
if Events ~= nil and Events.OnServerStarted ~= nil then
    Events.OnServerStarted.Add(function()
        if not NR.isServer() then return end
        if S.wired then return end
        local P = NR.server.players
        if P == nil then return end
        S.wired = true
        P.onDeparture[#P.onDeparture + 1] = S.forget
    end)
end
