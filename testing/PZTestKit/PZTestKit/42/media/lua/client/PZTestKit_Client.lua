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
-- @args (none)
-- @reply string
-- @purpose Quits the client to desktop through the in-game route, so the server sees a proper disconnect.
TK.register("quit", function()
    getCore():quitToDesktop()   -- the in-game quit: proper disconnect first
    return "quitting"
end)
-- @args (none)
-- @reply {calories, weight, carbs, lipids, proteins, x, y, z, items}
-- @purpose Client-side read of the local player's four macros, weight, position and inventory size.
TK.register("player.stats", function()
    local p = getPlayer()
    local n = p:getNutrition()
    return { calories = n:getCalories(), weight = n:getWeight(), carbs = n:getCarbohydrates(),
             lipids = n:getLipids(), proteins = n:getProteins(), x = p:getX(), y = p:getY(), z = p:getZ(),
             items = p:getInventory():getItems():size() }
end)
-- @args <key> <value>
-- @reply string
-- @purpose Writes one string key into the local player's modData on the client; the server twin takes <user> first.
TK.register("moddata.set", function(argv)
    getPlayer():getModData()[argv[1]] = argv[2]
    return "set " .. tostring(argv[1])
end)
-- @args (none)
-- @reply string
-- @purpose Calls transmitModData() on the local player, pushing the client's whole modData table to the server.
TK.register("moddata.transmit", function()
    getPlayer():transmitModData()
    return "transmitted"
end)
-- Renamed from `witness.moddata` in slice 08. That name now belongs to the SHARED reflective
-- command in PZTestKit_Core.lua, and shared/ loads before client/, so a client registration of
-- the same name would silently shadow it on this side only. Nothing else about this command
-- changed: `args.kind` is still "moddata", so the OnServerCommand handler below and the result
-- file (witness_moddata_<key>.json) are untouched.
-- @args <key>
-- @reply string
-- @purpose Asks the server from the client for its value of one player modData key; the comparison lands asynchronously in witness_moddata_<key>.json.
TK.register("witness.sync.moddata", function(argv)
    sendClientCommand(getPlayer(), "PZTestKit", "witness", { kind = "moddata", key = argv[1] })
    return "sent"
end)
-- @args (none)
-- @reply string
-- @purpose Asks the server from the client for its copy of the local player's Nutrition block; the comparison arrives asynchronously as a result file.
TK.register("witness.nutrition", function()
    sendClientCommand(getPlayer(), "PZTestKit", "witness", { kind = "nutrition" })
    return "sent"
end)
-- @args <fullType>
-- @reply string
-- @purpose Asks the server from the client for its copy of one inventory item by id; the field-by-field comparison arrives asynchronously as a result file.
TK.register("witness.item", function(argv)
    local item = getPlayer():getInventory():getFirstTypeRecurse(argv[1])
    if not item then return "no item " .. tostring(argv[1]) end
    C.witnessItem = item
    sendClientCommand(getPlayer(), "PZTestKit", "witness", { kind = "item", id = item:getID(), type = item:getFullType() })
    return "sent id=" .. tostring(item:getID())
end)
-- @args <fullType>
-- @reply string
-- @purpose Spawns one item into the local player's inventory on the client, where the server never hears of it (S6); the reply carries the new item id.
TK.register("item.spawn", function(argv)
    local it = getPlayer():getInventory():AddItem(argv[1])
    return it and ("id=" .. tostring(it:getID())) or "failed"
end)
-- <type> <conditionMax> <condition> [modDataTag]: change fields locally, then push with the
-- game's own item sync (sendItemStats). What the server ends up with is the S6 question.
-- @args <fullType> <conditionMax> <condition> [<modDataTag>]
-- @reply string
-- @purpose Changes an item's condition and modData tag on the client and pushes them with sendItemStats; what the server keeps is the S6 question.
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

-- @args (none)
-- @reply {calories, carbs, lipids, proteins, weight, hunger, thirst, statsApi, incWeight, incWeightLot, decWeight}
-- @purpose Client-side read of the local player's Nutrition block -- a mirror of the last 1 Hz PlayerStatsPacket, never a rate.
TK.register("nutrition.get", function() return nutritionSnapshot(getPlayer()) end)
-- @args <calories|carbs|lipids|proteins|weight> <value>
-- @reply {calories, carbs, lipids, proteins, weight, hunger, thirst, statsApi, incWeight, incWeightLot, decWeight} | string
-- @purpose Client-side write of one Nutrition field on the local player; the server owns Nutrition, so the write is expected to revert.
TK.register("nutrition.set", function(argv)
    local n, v = getPlayer():getNutrition(), tonumber(argv[2])
    local m = TK.NUTRITION_SETTERS[argv[1]]
    if not m or v == nil then return "usage: nutrition.set <calories|carbs|lipids|proteins|weight> <value>" end
    if not TK.call(n, m, v) then return "no Nutrition:" .. m end
    return nutritionSnapshot(getPlayer())
end)

-- <field> <value> [<field> <value> ...]; the snapshot comes back so the caller can see the
-- read-back in the same ack. Whether a client-side write SURVIVES is a separate question --
-- the server owns Nutrition (task 3) -- so the experiment probes both sides before relying
-- on either.
-- @args <hunger|thirst|fatigue|endurance> <value> [<field> <value> ...]
-- @reply {calories, carbs, lipids, proteins, weight, hunger, thirst, statsApi, incWeight, incWeightLot, decWeight, applied} | string
-- @purpose Client-side write of one or more hunger/thirst/fatigue/endurance stats on the local player, with the snapshot read back in the same ack.
TK.register("stats.set", function(argv)
    local p = getPlayer()
    if #argv < 2 then return "usage: stats.set <hunger|thirst|fatigue|endurance> <value> [...]" end
    local applied = TK.applyStats(p, argv, 1)
    local snap = nutritionSnapshot(p)
    snap.applied = applied
    return snap
end)

-- <option> [true|false] [push]: read a sandbox option, or flip it at runtime.
-- With no value it only reports (there is no other read command).
-- The game's own admin panel does NOT call getSandboxOptions():set() on a client --
-- ISServerSandboxOptionsUI.lua:738 guards it with `if not isClient()` and clients instead
-- fill a SandboxOptions copy and call :sendToServer() -- so a plain flip here is expected to
-- be client-local. `push` additionally tries sendToServer(): nil-checked and pcall-wrapped,
-- but NOT admin-gated -- nothing here checks isAdmin(), so whether a non-admin's push is
-- refused is the server's decision and is not established by this harness.
-- @args <option> [true|false] [push]
-- @reply {option, side, before, type, sandboxVarsBefore [, requested] [, route] [, setError] [, setValueError] [, error], after, sandboxVarsAfter [, push] [, pushError]} | string
-- @purpose Reads or flips one sandbox option on the client, optionally pushing it with sendToServer; a plain flip is client-local.
TK.register("sandbox.set", function(argv)
    local name = argv[1]
    if not name then return "usage: sandbox.set <option> [true|false] [push]" end
    if argv[2] and argv[2] ~= "true" and argv[2] ~= "false" and argv[2] ~= "push" then
        return "usage: sandbox.set <option> [true|false] [push]"
    end
    if not getSandboxOptions then return "no getSandboxOptions()" end
    local opts = getSandboxOptions()
    if not opts then return "getSandboxOptions() returned nil" end
    local out = { option = name, side = TK.side }
    local hasByName, opt = TK.call(opts, "getOptionByName", name)
    if hasByName and opt then
        local ok, v = TK.call(opt, "getValue")
        if ok then out.before = v end
        ok, v = TK.call(opt, "getType")
        if ok then out.type = v end
    else
        out.before = "no SandboxOptions:getOptionByName"
    end
    out.sandboxVarsBefore = SandboxVars and SandboxVars[name]
    if argv[2] == "true" or argv[2] == "false" then
        local value = argv[2] == "true"
        out.requested = value
        -- pcall wraps the CALL, not the lookup: TK.call has already ruled out "call nil" --
        -- index-first guard: a caught nil call is silent and names nothing; an unguarded raise
        -- aborts the rest of this handler (x126/x127) -- see docs/modding/lua-api.md section 5.
        -- What is left is an argument/type mismatch inside SandboxOptions:set -- which pcall
        -- does catch, and which must fall through to the per-option setter rather than kill
        -- the ack.
        local ran, present = pcall(TK.call, opts, "set", name, value)
        if ran and present then
            out.route = "SandboxOptions:set(name,value)"
        else
            if not ran then out.setError = tostring(present) end
            local ran2, present2 = false, false
            if opt then ran2, present2 = pcall(TK.call, opt, "setValue", value) end
            if ran2 and present2 then
                out.route = "getOptionByName():setValue()"
            else
                out.route = "none"
                out.error = "not settable at runtime: no SandboxOptions:set and no option:setValue"
                if not ran2 and opt then out.setValueError = tostring(present2) end
            end
        end
    end
    if hasByName and opt then
        local ok, v = TK.call(opt, "getValue")
        if ok then out.after = v end
    end
    out.sandboxVarsAfter = SandboxVars and SandboxVars[name]
    if argv[2] == "push" or argv[3] == "push" then
        -- Same reasoning as the `set` route above: TK.call rules out "call nil" -- index-first
        -- guard: a caught nil call is silent and names nothing; an unguarded raise aborts the
        -- rest of this handler (x126/x127) -- see docs/modding/lua-api.md section 5. What pcall
        -- catches here is a failure INSIDE sendToServer -- and that must be reported, not
        -- allowed to kill the ack after the flip already happened.
        local ran, present = pcall(TK.call, opts, "sendToServer")
        if not ran then
            out.push, out.pushError = "sendToServer() raised", tostring(present)
        else
            out.push = present and "sendToServer() called" or "no SandboxOptions:sendToServer"
        end
    end
    return out
end)

-- Slice 09 moved the implementation into the core (TK.scriptValues) so the SERVER can answer
-- `item.script` with the same code: script data is loaded per side and never synced, so the
-- two sides are two readings and a teardown wants both. This side is unchanged apart from the
-- reply gaining `side` -- see the block above TK.scriptValues for the getter list and for why
-- Calories / Carbohydrates / Lipids / Proteins come back absent on 42.20.4.
local function scriptValues(fullType) return TK.scriptValues(fullType) end
-- @args <fullType>
-- @reply {fullType, via, side, access, HungerChange, ThirstChange, Calories, Carbohydrates, Lipids, Proteins, DaysFresh, DaysTotallyRotten, IsCookable, MinutesToCook, MinutesToBurn} | string
-- @purpose Client-side read of one script item's live property getters; the server twin is a separate reading, since script data never syncs.
TK.register("item.script", function(argv) return scriptValues(argv[1]) or ("no script item " .. tostring(argv[1])) end)

-- Slice 02 moved the table into Core so the server half can return the same shape; the
-- slice-01 keys are unchanged (see TK.ITEM_STATE).
local function itemState(it) return TK.itemState(it) end
-- Returns (item, "found"|"client"). The AddItem fallback is EXPERIMENT-ONLY: a client-spawned
-- item is invisible to the server (S6), so eating one makes the server log a SyncItemFields
-- NPE (IsoGameCharacter.Eat -> syncItemFields on an item the server never heard of) and
-- `pzt run` counts any server error line as FAIL. Spawn server-side --
-- RCON `additem "user" "Type" 1` -- for anything that has to stay error-free.
local function findOrSpawn(fullType)
    local inv = getPlayer():getInventory()
    local it = inv:getFirstTypeRecurse(fullType)
    if it then return it, "found" end
    return inv:AddItem(fullType), "client"
end
-- `spawned` is reported here for the same reason `eat` reports it, and it is the reading that
-- actually counts: when a caller runs item.state BEFORE eat (the matrix does), it is THIS call
-- that finds-or-spawns the item, so a missed server-side spawn is answered here and eat's own
-- `spawned` would read "found" either way. Dropping it made the provenance unfalsifiable.
-- @args <fullType> [cooked|burnt|rotten|frozen|fresh]
-- @reply {fullType, cooked, burnt, rotten, frozen, age, hungChange, baseHunger, calories, carbs, lipids, proteins, id, uses, fresh, offAge, offAgeMax, freezingTime, cookingTime, heat, minutesToCook, minutesToBurn, thirstChange, hungerChange, isCookable, actualWeight, weight, customWeight, lastCookMinute, spawned} | string
-- @purpose Finds or spawns an item on the client, optionally forces one state onto it, and answers with the resulting item state.
TK.register("item.state", function(argv)
    local it, spawned = findOrSpawn(argv[1])
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
    local out = itemState(it)
    out.spawned = spawned
    return out
end)

-- ---- lifecycle commands (slice 02) -------------------------------------------
-- <fullType> <days>: setAge on the CLIENT's copy. This measures nothing about aging -- the
-- server owns that (02-notes Q8) -- it measures the five local Food getters as a pure
-- function of age: isFresh/isRotten/getHungChange and the four macros.
-- @args <fullType> <days>
-- @reply {fullType, cooked, burnt, rotten, frozen, age, hungChange, baseHunger, calories, carbs, lipids, proteins, id, uses, fresh, offAge, offAgeMax, freezingTime, cookingTime, heat, minutesToCook, minutesToBurn, thirstChange, hungerChange, isCookable, actualWeight, weight, customWeight, lastCookMinute, spawned, requestedAge, before} | string
-- @purpose Sets an item's age on the client's own copy, to read the local Food getters as a function of age; the server owns real aging.
TK.register("item.age", function(argv)
    local it, spawned = findOrSpawn(argv[1])
    if not it then return "no item " .. tostring(argv[1]) end
    local days = tonumber(argv[2])
    if days == nil then return "usage: item.age <fullType> <days>" end
    local before = itemState(it)
    if not TK.call(it, "setAge", days) then return "no InventoryItem:setAge" end
    local out = itemState(it)
    out.spawned, out.requestedAge, out.before = spawned, days, before
    return out
end)

-- <PerkName> <level> on the local player. The server's twin (`perk.set <user> …`) is the
-- authoritative one and, measured, reaches this side by itself; this command is the fallback
-- and the read-back. See TK.setPerk for why a client-only write does not survive in MP.
-- @args <PerkName> <level>
-- @reply {perk, requested, side, before, setPerkLevelDebug, afterSetPerkLevelDebug, setXPToLevel, after, route} | {error} | string
-- @purpose Client-side write of a perk level on the local player: the fallback and read-back for the authoritative server twin.
TK.register("perk.set", function(argv)
    local level = tonumber(argv[2])
    if not argv[1] or level == nil then return "usage: perk.set <PerkName> <level>" end
    return TK.setPerk(getPlayer(), argv[1], level)
end)

-- <recipeName> <BaseType> <ingredientType>...  The game's own path, minus the UI: the
-- context menu queues ISAddItemInRecipe, whose :complete() is
-- `recipe:addItem(baseItem, usedItem, character)` (ISAddItemInRecipe.lua:70) followed by
-- checkName/checkTemperature. addItem is a plain Java call, so it runs headlessly; the menu
-- is only what *chooses* the pair. getItemsCanBeUse/isItemUsableInRecipe are recorded per
-- ingredient so a refusal the menu would have made silently (water, MaxItems, frozen, burnt,
-- rotten under Cooking 7) is visible instead of showing up as a flat result.
-- checkName is deliberately skipped: it only generates a display name.
local function findEvolvedRecipe(name)
    if not getEvolvedRecipes then return nil, "no getEvolvedRecipes()" end
    local list = getEvolvedRecipes()
    if not list then return nil, "getEvolvedRecipes() returned nil" end
    local seen = {}
    for i = 0, list:size() - 1 do
        local r = list:get(i)
        local _, untranslated = TK.call(r, "getUntranslatedName")   -- the script block name
        local _, original = TK.call(r, "getOriginalname")
        local _, display = TK.call(r, "getName")
        if untranslated == name or original == name or display == name then return r, nil end
        if #seen < 12 then seen[#seen + 1] = tostring(untranslated) end
    end
    return nil, "no evolved recipe '" .. tostring(name) .. "' among " .. tostring(list:size())
        .. " (first: " .. table.concat(seen, ",") .. ")"
end

-- @args <recipeName> <BaseType> <ingredientType> [<ingredientType> ...]
-- @reply {recipe, baseType, cookingLevel, baseBefore, ingredients, recipeInfo, result} | string
-- @purpose Runs the evolved-recipe addItem path on the client without the context menu, recording each ingredient's usability and the base item after it.
TK.register("recipe.evolved", function(argv)
    local recipeName, baseType = argv[1], argv[2]
    if not recipeName or not baseType or not argv[3] then
        return "usage: recipe.evolved <recipeName> <BaseType> <ingredientType>..."
    end
    local recipe, err = findEvolvedRecipe(recipeName)
    if not recipe then return err end
    local p = getPlayer()
    local inv = p:getInventory()
    local base = inv:getFirstTypeRecurse(baseType)
    if not base then return "no base item " .. tostring(baseType) .. " in inventory" end
    -- Perks.Cooking is read BEFORE the call and the read skipped when it is nil: handing a
    -- nil enum to a present Java method is an arity or overload mismatch -- it raises and pcall
    -- catches it (lua-api.md section 5 row 2); the guard keeps the reply informative.
    local cooking = Perks and Perks.Cooking
    local cookLvl = nil
    if cooking then local _, lvl = TK.call(p, "getPerkLevel", cooking); cookLvl = lvl end
    local out = { recipe = recipeName, baseType = baseType, cookingLevel = cookLvl,
                  baseBefore = itemState(base), ingredients = {} }
    local _, rItem = TK.call(recipe, "getResultItem")
    local _, maxItems = TK.call(recipe, "getMaxItems")
    local _, minWater = TK.call(recipe, "getMinimumWater")
    local _, cookable = TK.call(recipe, "isCookable")
    out.recipeInfo = { resultItem = rItem, maxItems = maxItems, minimumWater = minWater, cookable = cookable }
    for i = 3, #argv do
        local ingType = argv[i]
        local row = { type = ingType }
        local ing = inv:getFirstTypeRecurse(ingType)
        if not ing then
            row.error = "not in inventory"
        else
            row.before = itemState(ing)
            -- Diagnostics first: what the menu would have offered for THIS base. Called with
            -- method syntax and a literal nil (exactly ISAddItemInRecipe.lua:17) rather than
            -- through TK.call, because a trailing nil in a Kahlua vararg forward is not worth
            -- trusting; the nil-check on the member is what TK.call would have done anyway.
            if recipe.getItemsCanBeUse then
                local ran, list = pcall(function() return recipe:getItemsCanBeUse(p, base, nil) end)
                if ran and list then
                    row.canBeUseCount, row.canBeUseContains = list:size(), list:contains(ing)
                else
                    row.canBeUseCount = "getItemsCanBeUse raised: " .. tostring(list)
                end
            else
                row.canBeUseCount = "no EvolvedRecipe:getItemsCanBeUse"
            end
            local okUsable, usable = TK.call(recipe, "isItemUsableInRecipe", p, base, ing:getID())
            -- not `okUsable and usable or "..."`: a legitimate `false` would report the
            -- missing-method string, which is the one answer that must stay distinguishable.
            if okUsable then
                row.usable = usable
            else
                row.usable = "no EvolvedRecipe:isItemUsableInRecipe"
            end
            local okAdd, newBase = TK.call(recipe, "addItem", base, ing, p)
            if not okAdd then
                row.error = "no EvolvedRecipe:addItem"
            else
                row.baseReplaced = (newBase ~= base)
                if newBase then base = newBase end
                -- the game's own post-step (ISAddItemInRecipe.lua:78); averages the heats
                if ISAddItemInRecipe and type(ISAddItemInRecipe.checkTemperature) == "function" then
                    local ran, e = pcall(ISAddItemInRecipe.checkTemperature, base, ing, recipe)
                    row.checkTemperature = ran and "ran" or ("raised: " .. tostring(e))
                end
                local still = inv:getFirstTypeRecurse(ingType)
                row.consumed = (still == nil) or (still:getID() ~= row.before.id)
                row.after = (still ~= nil and still:getID() == row.before.id) and itemState(still) or "consumed"
                row.baseAfter = itemState(base)
            end
        end
        out.ingredients[#out.ingredients + 1] = row
    end
    out.result = itemState(base)
    return out
end)

-- Direct application: measures the intake arithmetic of IsoGameCharacter.Eat. In MP this is
-- NOT the path a real eat takes (the server runs it) - see `eat.action` for that.
-- @args <fullType> [<fraction>]
-- @reply {fraction, spawned, signature, before, after, delta, script, itemBefore, itemAfter} | string
-- @purpose Calls IsoGameCharacter.Eat directly on the client to measure the intake arithmetic; in MP this is not the path a real eat takes.
TK.register("eat", function(argv)
    local p = getPlayer()
    local it, spawned = findOrSpawn(argv[1])   -- "client" = spawned here; see findOrSpawn
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
    return { fraction = fraction, spawned = spawned, signature = "Eat(item,fraction,useUtensil)",
             before = before, after = after, delta = delta, script = script, itemBefore = stateBefore,
             itemAfter = remaining and itemState(remaining) or "consumed" }
end)

-- The real MP path: queue ISEatFoodAction, which the client mirrors to the server
-- (NetTimedAction) and the SERVER completes. Result is asynchronous: poll nutrition.get.
-- @args <fullType> [<fraction>]
-- @reply {queued, fraction, spawned, itemId, itemBefore, validStart, maxTime, moodleFoodEaten, before} | string
-- @purpose Queues the real ISEatFoodAction from the client, which the server completes; the outcome is asynchronous, so poll nutrition.get for it.
TK.register("eat.action", function(argv)
    local p = getPlayer()
    local it, spawned = findOrSpawn(argv[1])   -- "client" spawns trip the server NPE; see findOrSpawn
    if not it then return "no item " .. tostring(argv[1]) end
    local fraction = tonumber(argv[2]) or 1.0
    local before, stateBefore = nutritionSnapshot(p), itemState(it)
    if not ISEatFoodAction or not ISTimedActionQueue then return "no ISEatFoodAction/ISTimedActionQueue" end
    local act = ISEatFoodAction:new(p, it, fraction)
    local _, validStart = TK.call(act, "isValidStart")   -- false when FOOD_EATEN moodle >= 3
    -- TK.call only guards against a missing method; passing a nil enum INTO a present Java
    -- method is an argument mismatch, and that is just as unrecoverable in Kahlua. So skip
    -- the read entirely rather than call getMoodleLevel(nil) when MoodleType is not exposed.
    local level
    local eatenType = MoodleType and MoodleType.FOOD_EATEN
    if eatenType then
        local _, moodles = TK.call(p, "getMoodles")
        local _, lvl = TK.call(moodles, "getMoodleLevel", eatenType)
        level = lvl
    end
    ISTimedActionQueue.add(act)
    return { queued = true, fraction = fraction, spawned = spawned, itemId = stateBefore.id,
             itemBefore = stateBefore, validStart = validStart, maxTime = act.maxTime,
             moodleFoodEaten = level, before = before }
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
        -- Slice 02: the same item's full state on both sides. `match` above stays the slice-01
        -- condition/modTag comparison (S6) so nothing that reads it changes meaning; the state
        -- pair below is what answers "which fields does ItemStatsPacket actually carry" --
        -- age/offAge/offAgeMax/freezingTime are not in it, cooked/burnt/cookingTime/heat and
        -- the nutrition block are (02-notes Q8).
        rep.serverState, rep.clientState = args.state, TK.itemState(it)
        if type(rep.serverState) == "table" and type(rep.clientState) == "table" then
            local diff = {}
            for k, sv in pairs(rep.serverState) do
                local cv = rep.clientState[k]
                if type(sv) == "number" and type(cv) == "number" then
                    if math.abs(sv - cv) > 0.0001 then diff[k] = { server = sv, client = cv } end
                elseif sv ~= cv then
                    diff[k] = { server = sv, client = cv }
                end
            end
            rep.stateDiff = diff
        end
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
