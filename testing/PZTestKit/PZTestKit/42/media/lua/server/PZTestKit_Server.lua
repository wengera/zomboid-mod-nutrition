-- PZTestKit server side: command bus polling + authoritative "witness" replies (S6).
if not isServer() then return end

TK.register("time.multiplier", function(argv)
    -- server-only fallback; the admin command (settimespeed) also broadcasts to clients
    getGameTime():setMultiplier(tonumber(argv[1]) or 1)
    return "mult=" .. tostring(getGameTime():getMultiplier())
end)

TK.register("players", function()
    local list, names = getOnlinePlayers(), {}
    for i = 0, list:size() - 1 do names[#names + 1] = list:get(i):getUsername() end
    return names
end)

-- ---- intake-pipeline commands (slice 01) -------------------------------------
-- Same snapshot/setters as the client's, addressed by username: the pair is what tells us
-- which side owns Nutrition in MP.
local function findPlayer(username)
    local list = getOnlinePlayers()
    for i = 0, list:size() - 1 do
        local p = list:get(i)
        if p:getUsername() == username then return p end
    end
    return nil
end

TK.register("nutrition.get", function(argv)
    local p = findPlayer(argv[1])
    if not p then return "no online player " .. tostring(argv[1]) end
    return TK.nutritionSnapshot(p)
end)

TK.register("nutrition.set", function(argv)
    local p = findPlayer(argv[1])
    if not p then return "no online player " .. tostring(argv[1]) end
    local m, v = TK.NUTRITION_SETTERS[argv[2]], tonumber(argv[3])
    if not m or v == nil then
        return "usage: nutrition.set <username> <calories|carbs|lipids|proteins|weight> <value>"
    end
    if not TK.call(p:getNutrition(), m, v) then return "no Nutrition:" .. m end
    return TK.nutritionSnapshot(p)
end)

-- <user> <field> <value> [<field> <value> ...]. The twin of the client's stats.set: which of
-- the two survives says who owns hunger/thirst, the same way the nutrition.set pair settled
-- who owns Nutrition.
TK.register("stats.set", function(argv)
    local p = findPlayer(argv[1])
    if not p then return "no online player " .. tostring(argv[1]) end
    if #argv < 3 then
        return "usage: stats.set <username> <hunger|thirst|fatigue|endurance> <value> [...]"
    end
    local applied = TK.applyStats(p, argv, 2)
    local snap = TK.nutritionSnapshot(p)
    snap.applied = applied
    return snap
end)

-- <user> <PerkName> <level>. The authoritative one: the client's own perk.set is overwritten
-- by the server's copy within a second (TK.setPerk), so the evolved-recipe phases pin the
-- level HERE.
-- MEASURED (exp02-20260910-030433): this write also reaches the client by itself, inside one
-- bus round-trip and with no wait in between -- the client read its own copy back already at
-- the new level (route "already at level") both when phase (f) set Cooking 10 and when
-- teardown put it back to 0. setPerkLevelDebug's own sendPerks branch is client-side, so the
-- carrier is some other server->client character sync, not this call; which one was not
-- established. The client-side perk.set is therefore a fallback, not a required second half.
TK.register("perk.set", function(argv)
    local p = findPlayer(argv[1])
    if not p then return "no online player " .. tostring(argv[1]) end
    local level = tonumber(argv[3])
    if not argv[2] or level == nil then return "usage: perk.set <user> <PerkName> <level>" end
    return TK.setPerk(p, argv[2], level)
end)

-- ---- item lifecycle commands (slice 02) --------------------------------------
-- The SERVER owns item aging: Food.update gates updateAge on GameServer.server (02-notes
-- Q2/Q8, code). MEASURED (exp02-20260910-030433): `age` does not travel to the client -- not
-- on sendItemStats, not on updateAge(true), and not over a whole accelerated game day. That
-- offAge/offAgeMax/freezingTime are likewise absent from ItemStatsPacket is a reading of the
-- packet code, not a measurement: no run has yet made them differ between the two sides.
-- Either way a client-side age probe measures the client's stale copy, and every real
-- aging/cooking reading has to be taken here.
local function findItem(username, fullType)
    local p = findPlayer(username)
    if not p then return nil, "no online player " .. tostring(username) end
    local it = p:getInventory():getFirstTypeRecurse(fullType)
    if not it then return nil, "no item " .. tostring(fullType) .. " in " .. username .. "'s inventory" end
    return it, nil, p
end

TK.register("item.get", function(argv)
    local it, err = findItem(argv[1], argv[2])
    if not it then return err or "usage: item.get <user> <fullType>" end
    local out = TK.itemState(it)
    out.serverWorldAge = getGameTime():getWorldAgeHours()
    return out
end)

-- <user> <fullType> <field> <value>. Every field is a documented Food/InventoryItem setter
-- (02-notes "Exact setters / getters"); `rotten` and `frozen` are deliberately NOT offered --
-- setRotten(true)/setFrozen(true) write fields nothing reads back (isRotten() reads age,
-- and the next updateFreezing undoes setFrozen). Force rot with `age <offAgeMax+1>` and
-- freezing with the `item.freeze` command below.
-- offAge/offAgeMax are here because the aging phases need to move the thresholds as well as
-- the age; lastCookMinute because Food.update runs its cooking block at most once per game
-- minute, so a second forced transition inside the same minute is otherwise a silent no-op.
local ITEM_SETTERS = {
    age = { "setAge", "number" }, offAge = { "setOffAge", "number" },
    offAgeMax = { "setOffAgeMax", "number" }, freezingTime = { "setFreezingTime", "number" },
    cookingTime = { "setCookingTime", "number" }, heat = { "setHeat", "number" },
    calories = { "setCalories", "number" }, hungChange = { "setHungChange", "number" },
    lastCookMinute = { "setLastCookMinute", "number" },
    cooked = { "setCooked", "boolean" }, burnt = { "setBurnt", "boolean" },
}

TK.register("item.set", function(argv)
    local it, err = findItem(argv[1], argv[2])
    if not it then return err or "usage: item.set <user> <fullType> <field> <value>" end
    local spec = ITEM_SETTERS[argv[3] or ""]
    if not spec then
        local names = {}
        for k in pairs(ITEM_SETTERS) do names[#names + 1] = k end
        table.sort(names)
        return "usage: item.set <user> <fullType> <" .. table.concat(names, "|") .. "> <value>"
    end
    local value
    if spec[2] == "boolean" then
        if argv[4] ~= "true" and argv[4] ~= "false" then return "expected true|false, got " .. tostring(argv[4]) end
        value = argv[4] == "true"
    else
        value = tonumber(argv[4])
        if value == nil then return "expected a number, got " .. tostring(argv[4]) end
    end
    local before = TK.itemState(it)
    if not TK.call(it, spec[1], value) then return "no InventoryItem:" .. spec[1] end
    -- The game's own item sync. It will NOT carry age back to the client (Q8) -- that is the
    -- measurement, not a bug -- so this command also reports the server-side reading directly.
    local pushed = false
    if sendItemStats then
        local ran, e = pcall(sendItemStats, it)
        pushed = ran and "sendItemStats(item)" or ("sendItemStats raised: " .. tostring(e))
    else
        pushed = "no sendItemStats()"
    end
    local out = TK.itemState(it)
    out.field, out.requested, out.before, out.sync = argv[3], value, before, pushed
    out.serverWorldAge = getGameTime():getWorldAgeHours()
    return out
end)

-- One aging step on demand: Food.updateAge(true). The `true` is the SYNC gate, not the age
-- gate -- it is what makes the server call sendItemStats afterwards (Q2). Whether that packet
-- carries the new age to the client is the point of the MP phase.
TK.register("item.age.tick", function(argv)
    local it, err = findItem(argv[1], argv[2])
    if not it then return err or "usage: item.age.tick <user> <fullType>" end
    local before = TK.itemState(it)
    if not TK.call(it, "updateAge", true) then return "no Food:updateAge(boolean)" end
    local out = TK.itemState(it)
    out.before, out.dAge = before, (out.age and before.age) and (out.age - before.age) or nil
    out.serverWorldAge = getGameTime():getWorldAgeHours()
    return out
end)

-- Food.freeze() = setFreezingTime(100), which is what actually flips `frozen`. setFrozen(true)
-- alone is undone by the next updateFreezing tick (Q2), so it is not offered.
TK.register("item.freeze", function(argv)
    local it, err = findItem(argv[1], argv[2])
    if not it then return err or "usage: item.freeze <user> <fullType>" end
    local before = TK.itemState(it)
    if not TK.call(it, "freeze") then return "no Food:freeze()" end
    if sendItemStats then pcall(sendItemStats, it) end
    local out = TK.itemState(it)
    out.before = before
    return out
end)

-- Food.update(): the cooking driver. With cookingTime already past minutesToCook and heat
-- above 1.6 this is the transition without an appliance (Q4 precondition 4).
TK.register("item.update", function(argv)
    local it, err = findItem(argv[1], argv[2])
    if not it then return err or "usage: item.update <user> <fullType>" end
    local before = TK.itemState(it)
    if not TK.call(it, "update") then return "no InventoryItem:update()" end
    local out = TK.itemState(it)
    out.before = before
    out.gameMinute = getGameTime():getMinutes()
    out.serverWorldAge = getGameTime():getWorldAgeHours()
    return out
end)

-- The server's view of what a client asked about; sent back on the same channel.
local function witness(player, args)
    local reply = { kind = args.kind, key = args.key }
    if args.kind == "moddata" then
        local v = player:getModData()[args.key]
        reply.value = (v ~= nil) and tostring(v) or "nil"
    elseif args.kind == "nutrition" then
        local n = player:getNutrition()
        reply.calories, reply.weight = n:getCalories(), n:getWeight()
        reply.carbs, reply.lipids, reply.proteins = n:getCarbohydrates(), n:getLipids(), n:getProteins()
    elseif args.kind == "item" then
        local items = player:getInventory():getItems()
        reply.found, reply.inventoryCount = false, items:size()
        for i = 0, items:size() - 1 do
            local it = items:get(i)
            if it:getID() == args.id then
                reply.found, reply.type = true, it:getFullType()
                reply.condition, reply.conditionMax = it:getCondition(), it:getConditionMax()
                local tag = it:getModData().pzt_tag
                reply.modTag = (tag ~= nil) and tostring(tag) or "nil"
                -- Slice 02: the server's own item state travels back with the reply, so the
                -- client can diff it field by field against its own copy of the SAME item id.
                -- That diff is the direct reading of what ItemStatsPacket carries (Q8).
                reply.state = TK.itemState(it)
                break
            end
        end
    end
    reply.serverWorldAge = getGameTime():getWorldAgeHours()
    sendServerCommand(player, "PZTestKit", "witness", reply)
end

Events.OnClientCommand.Add(function(module, command, player, args)
    if module ~= "PZTestKit" then return end
    if command == "witness" then
        local ok, err = pcall(witness, player, args)
        if not ok then TK.log("witness failed: " .. tostring(err)) end
    end
end)

local function tick()
    TK.ticks = TK.ticks + 1
    if TK.ticks % 20 == 0 then TK.pollCommands() end
end
if Events.OnTick then Events.OnTick.Add(tick) end
-- belt and braces: game-time driven poll in case OnTick is quiet on the dedicated server
if Events.EveryOneMinute then Events.EveryOneMinute.Add(function() TK.pollCommands() end) end
if Events.OnServerStarted then Events.OnServerStarted.Add(function() TK.log("server started event") end) end
TK.log("server harness loaded")
