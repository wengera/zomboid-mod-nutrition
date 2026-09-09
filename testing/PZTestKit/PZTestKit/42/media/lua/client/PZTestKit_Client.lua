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
