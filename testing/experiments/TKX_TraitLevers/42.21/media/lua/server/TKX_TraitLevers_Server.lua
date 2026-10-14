-- TKX_TraitLevers server side (Plan 13 Task 0, checks 4-8). Three parts, every one live on the dedicated server
-- only (this file also runs in a client's Lua state, so the side test is made once at file scope, behind a
-- sentinel global of its own, the TKX_XpEvents install-once shape, #2845):
--   1. OnNewGame(player, square): fired by CreatePlayerPacket.processServer after applyTraits (square is nil
--      there). It records the known traits, the weight and the Strength and Fitness levels and experience
--      (TKX_TraitLevers.newGame.before), then writes getNutrition():setWeight(77.7), removes STRONG when held,
--      adds OUT_OF_SHAPE, and steps Strength once with LevelPerk (LoseLevel at 10), the route of ruling 13-8 whose
--      LevelPerk event runs vanilla's band listener (XpUpdate.lua:389), and records the same reads again
--      (.after) with the writes' pcall results (.writes). newGame.count counts the handler's calls; the table
--      holds the latest call. The trait list is kept twice: as a Lua array (traits) and joined (traitsStr), so
--      lua.read reads it in one path.
--   2. The AddXP recorder (ruling 13-27): one record per Events.AddXP call in TKX_TraitLevers.xp.ev[i] =
--      {user, perk, amount, ms, protein, fitness, exe, level, xp}: the perk's id, the event's amount (the local
--      after every multiplier and clamp, XP.AddXP @1346-@1364), the wall ms (getTimestampMs), the server's
--      protein store (getNutrition():getProteins()), whether an ISFitnessAction is running (the server's
--      getFitness():getCurrentExe(), set at ISFitnessAction:serverStart and cleared at its stop) and the level
--      and experience read inside the listener. Capped at 200 records (xp.n); a call past the cap counts in
--      xp.dropped; xp.calls counts every call. TKX_TraitLevers.xpReset() (lua.call) empties the ring.
--   3. TKX_TraitLevers.zombieNear(user) (lua.call): one zombie one tile east of the named player through the
--      server's addZombiesInOutfit global (the harness zombie.near's spawner, which spawns beside the FIRST online
--      player only); returns the count spawned and the distance.
-- Every Java member is reached under pcall, so a missing member is a recorded error, never a raise in a handler.
TKX_TraitLevers = TKX_TraitLevers or {}

local XP_CAP = 200
local WEIGHT = 77.7

local function onServer()
    if isServer == nil then return false end
    local ok, s = pcall(isServer)
    return ok and s == true
end

local function try(fn)
    local ok, v = pcall(fn)
    if ok then return v end
    return nil
end

local function traitList(player)
    local names = {}
    local coll = try(function() return player:getCharacterTraits() end)
    local known = coll ~= nil and try(function() return coll:getKnownTraits() end) or nil
    local n = known ~= nil and try(function() return known:size() end) or nil
    if type(n) ~= "number" then return names end
    for i = 0, n - 1 do
        local t = try(function() return known:get(i) end)
        local nm = t ~= nil and try(function() return t:getName() end) or nil
        names[#names + 1] = tostring(nm or t)
    end
    return names
end

local function bodyRead(player)
    local r = {}
    r.traits = traitList(player)
    r.traitsStr = table.concat(r.traits, ",")
    r.weight = try(function() return player:getNutrition():getWeight() end)
    r.strength = try(function() return player:getPerkLevel(Perks.Strength) end)
    r.strengthXp = try(function() return player:getXp():getXP(Perks.Strength) end)
    r.fitness = try(function() return player:getPerkLevel(Perks.Fitness) end)
    r.fitnessXp = try(function() return player:getXp():getXP(Perks.Fitness) end)
    r.hasStrong = try(function() return player:hasTrait(CharacterTrait.STRONG) end)
    r.hasStout = try(function() return player:hasTrait(CharacterTrait.STOUT) end)
    r.hasOutOfShape = try(function() return player:hasTrait(CharacterTrait.OUT_OF_SHAPE) end)
    r.ms = getTimestampMs and getTimestampMs() or nil
    return r
end

local function write(w, key, fn)
    local ok, v = pcall(fn)
    w[key] = { ok = ok, ret = tostring(v) }
end

local function onNewGame(player, square)
    if player == nil then return end
    local prev = TKX_TraitLevers.newGame
    local ng = { count = ((prev and prev.count) or 0) + 1, squareNil = (square == nil) }
    ng.user = try(function() return player:getUsername() end)
    ng.before = bodyRead(player)
    local w = {}
    write(w, "weight", function() player:getNutrition():setWeight(WEIGHT) end)
    if ng.before.hasStrong == true then
        write(w, "removeStrong", function() return player:getCharacterTraits():remove(CharacterTrait.STRONG) end)
    end
    write(w, "addOutOfShape", function() return player:getCharacterTraits():add(CharacterTrait.OUT_OF_SHAPE) end)
    if ng.before.strength == 10 then
        w.step = "LoseLevel"
        write(w, "stepCall", function() player:LoseLevel(Perks.Strength) end)
    else
        w.step = "LevelPerk"
        write(w, "stepCall", function() player:LevelPerk(Perks.Strength) end)
    end
    ng.writes = w
    ng.after = bodyRead(player)
    TKX_TraitLevers.newGame = ng
end

local function xpReset()
    TKX_TraitLevers.xp = { n = 0, calls = 0, dropped = 0, cap = XP_CAP, ev = {},
                           resetMs = getTimestampMs and getTimestampMs() or nil }
    return true
end

local function onAddXp(owner, perk, amount)
    local x = TKX_TraitLevers.xp
    if x == nil then
        xpReset()
        x = TKX_TraitLevers.xp
    end
    x.calls = x.calls + 1
    if x.n >= XP_CAP then
        x.dropped = x.dropped + 1
        return
    end
    local exe = owner ~= nil and try(function() return owner:getFitness():getCurrentExe() end) or nil
    local ev = {
        user = owner ~= nil and try(function() return owner:getUsername() end) or nil,
        perk = perk ~= nil and (try(function() return perk:getId() end) or tostring(perk)) or "nil",
        amount = amount,
        ms = getTimestampMs and getTimestampMs() or nil,
        protein = owner ~= nil and try(function() return owner:getNutrition():getProteins() end) or nil,
        fitness = exe ~= nil,
        exe = exe ~= nil and tostring(exe) or nil,
        level = (owner ~= nil and perk ~= nil) and try(function() return owner:getPerkLevel(perk) end) or nil,
        xp = (owner ~= nil and perk ~= nil) and try(function() return owner:getXp():getXP(perk) end) or nil,
    }
    x.n = x.n + 1
    x.ev[x.n] = ev
end

local function findOnline(username)
    local players = try(function() return getOnlinePlayers() end)
    local n = players ~= nil and try(function() return players:size() end) or nil
    if type(n) ~= "number" then return nil end
    for i = 0, n - 1 do
        local p = try(function() return players:get(i) end)
        if p ~= nil and try(function() return p:getUsername() end) == username then return p end
    end
    return nil
end

local function zombieNear(username)
    local p = findOnline(username)
    if p == nil then return 0, "no online player " .. tostring(username) end
    if addZombiesInOutfit == nil then return 0, "no addZombiesInOutfit" end
    local px, py, pz = p:getX(), p:getY(), p:getZ()
    local ok, list = pcall(addZombiesInOutfit, math.floor(px) + 1, math.floor(py), math.floor(pz), 1, nil, 50)
    if not ok then return 0, "addZombiesInOutfit raised: " .. tostring(list) end
    local made = try(function() return list:size() end) or 0
    local dist = nil
    if made > 0 then
        local z = list:get(0)
        local dx, dy = z:getX() - px, z:getY() - py
        dist = math.floor(math.sqrt(dx * dx + dy * dy) * 100 + 0.5) / 100
    end
    return made, dist
end

if onServer() and TKX_TraitLevers_ServerInstalled == nil then
    TKX_TraitLevers_ServerInstalled = true
    TKX_TraitLevers.server = true
    TKX_TraitLevers.xpReset = xpReset
    TKX_TraitLevers.zombieNear = zombieNear
    xpReset()
    if Events ~= nil then
        if Events.OnNewGame ~= nil then Events.OnNewGame.Add(onNewGame) end
        if Events.AddXP ~= nil then Events.AddXP.Add(onAddXp) end
    end
end
