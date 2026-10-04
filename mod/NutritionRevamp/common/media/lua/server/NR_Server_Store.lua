-- NR_Server_Store.lua -- the durable per-player store: one global modData table keyed by
-- username (server-lifecycle rules #2410, #2417; spec § 4.8), cached server-side, inputs only,
-- never transmitted (#2416) and never player modData (#1042). Runs in both Lua states; every
-- write below is behind NutritionRevamp.isServer().
local NR = NutritionRevamp
NR.server.store = { name = "NutritionRevamp.players", records = nil }
local S = NR.server.store

-- ModData.getOrCreate creates the table when the file did not hold it; OnInitGlobalModData's
-- boolean says the WORLD is new, not the table (#2417), so the table is fetched whenever it is
-- found missing, not only on a new world.
function S.attach()
    if S.records ~= nil then return S.records end
    if ModData == nil then return nil end
    local ok, t = NR.call(ModData, "getOrCreate", S.name)
    if ok and t ~= nil then S.records = t end
    return S.records
end

function S.new(username, worldAgeHours)
    return { v = 1, username = username, firstSeen = worldAgeHours, lastSeen = worldAgeHours,
             resets = 0, dead = false }
end

function S.get(username, worldAgeHours)
    local t = S.attach()
    if t == nil then return nil end
    local r = t[username]
    if r == nil then
        r = S.new(username, worldAgeHours)
        t[username] = r
        NR.log.say(3, "store: new record for " .. tostring(username))
    end
    return r
end

-- A respawn: the character is new, the record starts fresh, the reset count carries over so
-- a later reading can tell a returning player from a new one.
function S.reset(username, worldAgeHours)
    local t = S.attach()
    if t == nil then return nil end
    local old = t[username]
    local r = S.new(username, worldAgeHours)
    r.resets = (old and old.resets or 0) + 1
    t[username] = r
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
