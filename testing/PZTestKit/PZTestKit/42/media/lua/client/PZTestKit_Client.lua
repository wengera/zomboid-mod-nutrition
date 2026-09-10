-- PZTestKit client side.
--  * Auto-join, driven by <cachedir>/Lua/pzt-join.txt (key=value lines):
--      stage 1: ServerConnectPopup visible -> fill credentials, call the same connect(...)
--               the CONNECT button calls (ServerConnectPopup.lua:203).
--      stage 2: MP character creation (B42, verified 2026-09-09):
--               MapSpawnSelect -> CharacterCreationProfession -> CharacterCreationMain -> world.
--               Each screen's NEXT is driven by invoking its onOptionMouseDown({internal="NEXT"}).
--  * Client commands for the bus (see PZTestKit_Core.lua) and the client half of the
--    sync witness (S6): ask the server for its view, compare with ours, write a result.
local C = { manifest = nil, joined = false, step = {}, ready = false, witnessItem = nil }

local function visible(panel)
    return panel ~= nil and panel.isVisible ~= nil and panel:isVisible()
end

local function readManifest()
    local m = TK.readKV("pzt-join.txt")
    if not m then TK.log("no manifest (Lua/pzt-join.txt)"); return nil end
    TK.log("manifest loaded: user=" .. tostring(m.username) .. " server=" .. tostring(m.ip) .. ":" .. tostring(m.port))
    return m
end

local function tryJoin()
    local popup = ServerConnectPopup and ServerConnectPopup.instance
    if not visible(popup) then return end
    local m = C.manifest
    popup.usernameEntry:setText(m.username or "")
    popup.passwordEntry:setText(m.password or "")
    popup.serverPasswordEntry:setText(m.serverPassword or "")
    local ip, port = popup.ip or m.ip, popup.port or m.port
    TK.log("popup visible; connecting as " .. tostring(m.username) .. " to " .. tostring(ip) .. ":" .. tostring(port))
    C.joined = true
    ConnectToServer.instance:connect(popup, "", m.username or "", m.password or "",
        ip, "", tostring(port), m.serverPassword or "", false, true, 1)
end

-- Press NEXT on one screen at most once; returns true if it acted.
local function pressNext(name, panel)
    if C.step[name] or not visible(panel) then return false end
    C.step[name] = true
    TK.log("screen '" .. name .. "' visible -> NEXT")
    local ok, err = pcall(function() panel:onOptionMouseDown({ internal = "NEXT" }, 0, 0) end)
    if not ok then TK.log("NEXT on " .. name .. " failed: " .. tostring(err)) end
    return true
end

local function tryCharacterCreation()
    local spawn = MapSpawnSelect and MapSpawnSelect.instance
    if visible(spawn) and not C.step.spawn then
        if spawn.listbox and spawn.listbox.selected and spawn.listbox.selected < 1 then
            spawn.listbox.selected = 1
        end
        local n = spawn.listbox and spawn.listbox.items and #spawn.listbox.items or -1
        TK.log("spawn regions listed: " .. tostring(n) .. ", selected #" .. tostring(spawn.listbox and spawn.listbox.selected))
        pressNext("spawn", spawn)
        return
    end
    local prof = CharacterCreationProfession and CharacterCreationProfession.instance
    if pressNext("profession", prof) then return end
    local main = MainScreen and MainScreen.instance and MainScreen.instance.charCreationMain
    if pressNext("appearance", main) then return end
end

-- "ready" = in-world with a player object; the orchestrator keys on this line.
local function checkReady()
    if C.ready then return end
    if isIngameState and not isIngameState() then return end
    local p = getPlayer()
    if not p then return end
    C.ready = true
    TK.log(string.format("player %s at %.0f,%.0f,%.0f", tostring(p:getUsername()), p:getX(), p:getY(), p:getZ()))
end

-- ---- client commands ---------------------------------------------------------
TK.register("quit", function()
    getCore():quitToDesktop()   -- the in-game quit: proper disconnect first
    return "quitting"
end)
TK.register("player.stats", function()
    local p = getPlayer()
    local n = p:getNutrition()
    return { calories = n:getCalories(), weight = n:getWeight(), carbs = n:getCarbohydrates(),
             lipids = n:getLipids(), proteins = n:getProteins(), x = p:getX(), y = p:getY(), z = p:getZ(),
             items = p:getInventory():getItems():size() }
end)
TK.register("moddata.set", function(argv)
    getPlayer():getModData()[argv[1]] = argv[2]
    return "set " .. tostring(argv[1])
end)
TK.register("moddata.transmit", function()
    getPlayer():transmitModData()
    return "transmitted"
end)
TK.register("witness.moddata", function(argv)
    sendClientCommand(getPlayer(), "PZTestKit", "witness", { kind = "moddata", key = argv[1] })
    return "sent"
end)
TK.register("witness.nutrition", function()
    sendClientCommand(getPlayer(), "PZTestKit", "witness", { kind = "nutrition" })
    return "sent"
end)
TK.register("witness.item", function(argv)
    local item = getPlayer():getInventory():getFirstTypeRecurse(argv[1])
    if not item then return "no item " .. tostring(argv[1]) end
    C.witnessItem = item
    sendClientCommand(getPlayer(), "PZTestKit", "witness", { kind = "item", id = item:getID(), type = item:getFullType() })
    return "sent id=" .. tostring(item:getID())
end)
TK.register("item.spawn", function(argv)
    local it = getPlayer():getInventory():AddItem(argv[1])
    return it and ("id=" .. tostring(it:getID())) or "failed"
end)
-- <type> <conditionMax> <condition> [modDataTag]: change fields locally, then push with the
-- game's own item sync (sendItemStats). What the server ends up with is the S6 question.
TK.register("item.tamper", function(argv)
    local item = getPlayer():getInventory():getFirstTypeRecurse(argv[1])
    if not item then return "no item " .. tostring(argv[1]) end
    item:setConditionMax(tonumber(argv[2]) or item:getConditionMax())
    item:setCondition(tonumber(argv[3]) or item:getCondition())
    if argv[4] then item:getModData().pzt_tag = argv[4] end
    sendItemStats(item)
    return string.format("cond=%d/%d tag=%s", item:getCondition(), item:getConditionMax(), tostring(item:getModData().pzt_tag))
end)

-- ---- intake-pipeline commands (slice 01) -------------------------------------
local function nutritionSnapshot(p) return TK.nutritionSnapshot(p) end

TK.register("nutrition.get", function() return nutritionSnapshot(getPlayer()) end)
TK.register("nutrition.set", function(argv)
    local n, v = getPlayer():getNutrition(), tonumber(argv[2])
    local m = TK.NUTRITION_SETTERS[argv[1]]
    if not m or v == nil then return "usage: nutrition.set <calories|carbs|lipids|proteins|weight> <value>" end
    if not TK.call(n, m, v) then return "no Nutrition:" .. m end
    return nutritionSnapshot(getPlayer())
end)

local SCRIPT_GETTERS = { "HungerChange", "ThirstChange", "Calories", "Carbohydrates", "Lipids", "Proteins",
                         "DaysFresh", "DaysTotallyRotten", "IsCookable", "MinutesToCook", "MinutesToBurn" }
local function scriptItem(fullType)
    local sm = getScriptManager()
    local ok, s = TK.call(sm, "getItem", fullType)
    if ok and s then return s, "getItem" end
    ok, s = TK.call(sm, "FindItem", fullType)      -- the form the game's own Lua uses
    if ok and s then return s, "FindItem" end
    return nil, nil
end
-- get<X>() / is<X>() / the public field <x>: the script Item keeps calories, carbohydrates,
-- lipids and proteins as public fields with no getter at all (Item.InstanceItem reads them
-- directly), so the field route is not optional. `access` records which one answered.
local function scriptValues(fullType)
    local s, via = scriptItem(fullType)
    if not s then return nil end
    local field = { Calories = "calories", Carbohydrates = "carbohydrates", Lipids = "lipids",
                    Proteins = "proteins" }
    local out = { fullType = fullType, via = via, access = {} }
    for _, g in ipairs(SCRIPT_GETTERS) do
        local route, ok, v = "get", TK.call(s, "get" .. g)
        if not ok then
            route, ok, v = "is", TK.call(s, "is" .. g)
        end
        if not ok then
            route = "field"
            ok, v = TK.field(s, field[g] or (string.lower(string.sub(g, 1, 1)) .. string.sub(g, 2)))
        end
        if ok and v ~= nil then out[g], out.access[g] = v, route end
    end
    return out
end
TK.register("item.script", function(argv) return scriptValues(argv[1]) or ("no script item " .. tostring(argv[1])) end)

local ITEM_STATE = { cooked = "isCooked", burnt = "isBurnt", rotten = "isRotten", frozen = "isFrozen",
                     age = "getAge", hungChange = "getHungChange", baseHunger = "getBaseHunger",
                     calories = "getCalories", carbs = "getCarbohydrates", lipids = "getLipids",
                     proteins = "getProteins", id = "getID", uses = "getCurrentUsesFloat" }
local function itemState(it)
    local out = { fullType = it:getFullType() }
    for k, m in pairs(ITEM_STATE) do
        local ok, v = TK.call(it, m)
        if ok then out[k] = v end
    end
    return out
end
local function findOrSpawn(fullType)
    local inv = getPlayer():getInventory()
    return inv:getFirstTypeRecurse(fullType) or inv:AddItem(fullType)
end
TK.register("item.state", function(argv)
    local it = findOrSpawn(argv[1])
    if not it then return "no item " .. tostring(argv[1]) end
    local s = argv[2]
    if s == "cooked" then TK.call(it, "setCooked", true)
    elseif s == "burnt" then TK.call(it, "setBurnt", true)
    elseif s == "rotten" then
        TK.call(it, "setRotten", true)
        local ok, rotten = TK.call(it, "isRotten")
        if not ok or not rotten then                      -- setRotten alone may not stick
            local hasMax, max = TK.call(it, "getOffAgeMax")
            TK.call(it, "setAge", (hasMax and max or 0) + 1)
        end
    elseif s == "frozen" then TK.call(it, "setFrozen", true)
    elseif s == "fresh" then TK.call(it, "setAge", 0) end
    return itemState(it)
end)

-- Direct application: measures the intake arithmetic of IsoGameCharacter.Eat. In MP this is
-- NOT the path a real eat takes (the server runs it) - see `eat.action` for that.
TK.register("eat", function(argv)
    local p = getPlayer()
    local it = findOrSpawn(argv[1])
    if not it then return "no item " .. tostring(argv[1]) end
    local fraction = tonumber(argv[2]) or 1.0
    local before, script, stateBefore = nutritionSnapshot(p), scriptValues(argv[1]), itemState(it)
    -- IsoGameCharacter.Eat(InventoryItem,float,boolean) - the 3-arg overload the game's own
    -- ISEatFoodAction:complete() calls; Eat(item,float) and Eat(item) exist as trampolines.
    local ok = TK.call(p, "Eat", it, fraction, false)
    if not ok then return "no Eat method on the player object" end
    local after = nutritionSnapshot(p)
    local delta = {}
    for k, v in pairs(after) do
        if type(v) == "number" and type(before[k]) == "number" then delta[k] = v - before[k] end
    end
    local remaining = p:getInventory():getFirstTypeRecurse(argv[1])
    return { fraction = fraction, signature = "Eat(item,fraction,useUtensil)", before = before,
             after = after, delta = delta, script = script, itemBefore = stateBefore,
             itemAfter = remaining and itemState(remaining) or "consumed" }
end)

-- The real MP path: queue ISEatFoodAction, which the client mirrors to the server
-- (NetTimedAction) and the SERVER completes. Result is asynchronous: poll nutrition.get.
TK.register("eat.action", function(argv)
    local p = getPlayer()
    local it = findOrSpawn(argv[1])
    if not it then return "no item " .. tostring(argv[1]) end
    local fraction = tonumber(argv[2]) or 1.0
    local before, stateBefore = nutritionSnapshot(p), itemState(it)
    if not ISEatFoodAction or not ISTimedActionQueue then return "no ISEatFoodAction/ISTimedActionQueue" end
    local act = ISEatFoodAction:new(p, it, fraction)
    local _, validStart = TK.call(act, "isValidStart")   -- false when FOOD_EATEN moodle >= 3
    local _, moodles = TK.call(p, "getMoodles")
    local _, level = TK.call(moodles, "getMoodleLevel", MoodleType and MoodleType.FOOD_EATEN)
    ISTimedActionQueue.add(act)
    return { queued = true, fraction = fraction, itemId = stateBefore.id, itemBefore = stateBefore,
             validStart = validStart, maxTime = act.maxTime, moodleFoodEaten = level, before = before }
end)

-- Server's authoritative view arrives here; compare with ours and record.
Events.OnServerCommand.Add(function(module, command, args)
    if module ~= "PZTestKit" or command ~= "witness" then return end
    local rep = { kind = args.kind, key = args.key, server = {}, client = {}, serverWorldAge = args.serverWorldAge }
    local p = getPlayer()
    if args.kind == "moddata" then
        local v = p:getModData()[args.key]
        rep.server.value = args.value
        rep.client.value = (v ~= nil) and tostring(v) or "nil"
        rep.match = rep.server.value == rep.client.value
    elseif args.kind == "nutrition" then
        local n = p:getNutrition()
        rep.server = { calories = args.calories, weight = args.weight, carbs = args.carbs, lipids = args.lipids, proteins = args.proteins }
        rep.client = { calories = n:getCalories(), weight = n:getWeight(), carbs = n:getCarbohydrates(), lipids = n:getLipids(), proteins = n:getProteins() }
        rep.match = math.abs((args.calories or -1e9) - rep.client.calories) < 1
            and math.abs((args.weight or -1e9) - rep.client.weight) < 0.01
    elseif args.kind == "item" then
        rep.server = { found = args.found, condition = args.condition, conditionMax = args.conditionMax,
                       modTag = args.modTag, inventoryCount = args.inventoryCount }
        local it = C.witnessItem
        if it then
            local tag = it:getModData().pzt_tag
            rep.client = { condition = it:getCondition(), conditionMax = it:getConditionMax(),
                           modTag = (tag ~= nil) and tostring(tag) or "nil" }
        end
        rep.match = args.found == true and it ~= nil and args.condition == rep.client.condition
            and args.conditionMax == rep.client.conditionMax and tostring(args.modTag) == tostring(rep.client.modTag)
    end
    TK.log("witness " .. tostring(args.kind) .. " match=" .. tostring(rep.match)
        .. " server=" .. TK.json(rep.server) .. " client=" .. TK.json(rep.client))
    TK.result("witness_" .. tostring(args.kind) .. (args.key and ("_" .. args.key) or ""), rep)
end)

local function onTick()
    TK.ticks = TK.ticks + 1
    if TK.ticks % 30 ~= 0 then return end          -- ~twice a second
    if not C.manifest then
        C.manifest = readManifest()
        if not C.manifest then
            Events.OnFETick.Remove(onTick)
            if Events.OnPostUIDraw then Events.OnPostUIDraw.Remove(onTick) end
            return
        end
    end
    -- After a successful connect the client reloads Lua with the server's mod list,
    -- so this file may start fresh mid-flow: always try every stage.
    if not C.joined then tryJoin() end
    tryCharacterCreation()
    checkReady()
    TK.pollCommands()
end

-- OnFETick stops once the client leaves MainScreenState; OnPostUIDraw fires every UI frame
-- in every state.
Events.OnFETick.Add(onTick)
if Events.OnPostUIDraw then Events.OnPostUIDraw.Add(onTick) end
Events.OnMainMenuEnter.Add(function() TK.log("main menu entered") end)
Events.OnGameStart.Add(function() TK.log("OnGameStart - in world") end)
TK.log("client harness loaded")
