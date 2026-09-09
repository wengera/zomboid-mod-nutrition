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
