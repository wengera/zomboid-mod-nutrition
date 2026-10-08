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
    return string.format("cond=%.0f/%.0f tag=%s", item:getCondition(), item:getConditionMax(), tostring(item:getModData().pzt_tag))
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

-- ---- Plan 1 Task 7 additions --------------------------------------------------
-- Appended after the file's trailing event registrations on purpose: the claims register holds
-- `repo:` pointers into this file by line number, so new sites go at the end and no existing
-- line moves. Registration order does not matter -- TK.commands is read at poll time.

-- The client twin of the server's `stats.all`: the same TK.statsAll body over the local player.
-- In MP this is the MIRROR of the stats the server owns (the once-a-second stats packet), so it
-- is a second reading, never the authoritative one.
-- @args (none)
-- @reply {side, user, worldAge, mult, wall, stats, missing [, error]} | string
-- @purpose Client-side read of all 24 registered CharacterStat values of the local player -- the mirror of the server's stats.all.
TK.register("stats.all", function()
    if getPlayer == nil then return "no getPlayer()" end
    local p = getPlayer()
    if p == nil then return "getPlayer() returned nil" end
    return TK.statsAll(p)
end)

-- The drink twin of `eat.action`: queue the real ISDrinkFluidAction from the client, which the
-- client mirrors to the server (NetTimedAction) and the SERVER completes. The constructor is
-- `ISDrinkFluidAction:new(character, item, percentage)` (media/lua/shared/TimedActions/
-- ISDrinkFluidAction.lua:126 in the install), and it reads `item:getFluidContainer()` itself, so
-- an item with no fluid container is refused here before the constructor can index nil.
-- findOrSpawn has eat.action's trap: a "client" spawn is an item the server never heard of --
-- spawn server-side (RCON additem) for anything that has to stay error-free. The outcome is
-- asynchronous: poll nutrition.get (and the server's stats) for it.
-- @args <fullType> [<percentage>]
-- @reply {queued, percentage, spawned, itemId, filledRatioBefore, before} | string
-- @purpose Queues the real ISDrinkFluidAction from the client, which the server completes; the outcome is asynchronous, so poll nutrition.get for it.
TK.register("drink.action", function(argv)
    if argv[1] == nil then return "usage: drink.action <fullType> [<percentage>]" end
    local p = getPlayer()
    local it, spawned = findOrSpawn(argv[1])
    if not it then return "no item " .. tostring(argv[1]) end
    local percentage = tonumber(argv[2]) or 1.0
    local _, fc = TK.call(it, "getFluidContainer")
    if fc == nil then return "no fluid container on " .. tostring(argv[1]) end
    local _, ratio = TK.call(fc, "getFilledRatio")
    local _, itemId = TK.call(it, "getID")
    local before = nutritionSnapshot(p)
    if not ISDrinkFluidAction or not ISTimedActionQueue then
        return "no ISDrinkFluidAction/ISTimedActionQueue"
    end
    local act = ISDrinkFluidAction:new(p, it, percentage)
    ISTimedActionQueue.add(act)
    return { queued = true, percentage = percentage, spawned = spawned, itemId = itemId,
             filledRatioBefore = ratio, before = before }
end)
TK.log("client harness Task 7 commands loaded")

-- ---- chained getter read (Plan 3 Task 2) ----------------------------------------------------
-- ---- helpers for witness.chain (documented at its register site below)

local function chainSplit(chain)
    local hops, depth, cur = {}, 0, ""
    for i = 1, string.len(chain) do
        local c = string.sub(chain, i, i)
        if c == "(" then depth = depth + 1 elseif c == ")" then depth = depth - 1 end
        if c == "." and depth == 0 then
            hops[#hops + 1] = cur
            cur = ""
        else
            cur = cur .. c
        end
    end
    hops[#hops + 1] = cur
    return hops
end

local function chainLiteral(lit)
    local perkName = string.match(lit, "^Perks%.([%w_]+)$")
    if perkName ~= nil then return Perks and Perks[perkName] end
    local n = tonumber(lit)
    if n ~= nil then return n end
    return lit
end

local function chainRead(subject, chain)
    local hops = chainSplit(chain)
    local out = { ok = false, hops = #hops }
    local obj = subject
    for i = 1, #hops do
        local name, lit = string.match(hops[i], "^([%w_]+)%((.*)%)$")
        if name == nil then name = hops[i] end
        if obj == nil then
            out.failedAt = i
            out.error = "nil before hop " .. i
            return out
        end
        local f = obj[name]
        if f == nil then
            out.failedAt = i
            out.error = "no member " .. name
            return out
        end
        -- a `get(N)` on a Java list whose size() <= N is an empty read, not a raise: answer it
        -- without calling get, so the engine log carries no exception line (T5).
        local idx = lit ~= nil and tonumber(lit) or nil
        if name == "get" and idx ~= nil and obj["size"] ~= nil then
            local okS, n = pcall(obj["size"], obj)
            if okS and type(n) == "number" and n <= idx then
                out.failedAt = i
                out.reason = "empty"
                return out
            end
        end
        local ran, v
        if lit ~= nil then
            local arg = chainLiteral(lit)
            if arg == nil then
                out.failedAt = i
                out.error = "literal " .. lit .. " did not resolve"
                return out
            end
            ran, v = pcall(f, obj, arg)
        else
            ran, v = pcall(f, obj)
        end
        if not ran then
            out.failedAt = i
            out.error = tostring(v)
            return out
        end
        obj = v
    end
    out.ok = true
    local t = type(obj)
    if t == "table" then
        local walked = {}
        for k, v in pairs(obj) do walked[tostring(k)] = tostring(v) end
        out.value = walked
    elseif obj == nil then
        out.value = "nil"
    else
        out.value = tostring(obj)
    end
    return out
end

-- <getter1[(arg)]>.<getter2[(arg)]>... Walks a chain of zero- or one-literal-argument
-- getters from the local player, every hop index-first (#0935): `local f = obj[name]; if f == nil
-- then fail; obj = f(obj, arg)`, a colon call written as a dot call with the receiver first,
-- under a pcall so a hop that throws names its index instead of aborting the handler. The
-- chain is split on dots OUTSIDE parentheses, so `getXp.getXP(Perks.Strength)` is two hops. A
-- literal argument is `Perks.<Name>` (the perk object), a number (a number) or else a string.
-- The end value: a number, boolean or string is tostring'd; a Lua table is walked ONE level
-- into string values; anything else (a Java object) is tostring'd, which names its class.
-- @args <getter1[(arg)]>.<getter2>...
-- @reply {ok, value, hops, failedAt [, error] [, reason]} | string
-- @purpose Reads the value at the end of a dot-chain of zero- or one-literal-argument getters on the local player (index-first at every hop); the one command for reads the typed witnesses do not name, such as the thermoregulator's metabolic target.
TK.register("witness.chain", function(argv)
    if argv[1] == nil then return "usage: witness.chain <getter1[(arg)]>.<getter2>..." end
    return chainRead(getPlayer(), argv[1])
end)

-- (none). The admin panel's experience sync from the client: the install's ISPlayerStatsUI.lua
-- calls the Java-exposed global `SyncXp(player)` after an admin trait add (lines 596 and 671),
-- and the jar lists SyncXp(IsoPlayer)V on LuaManager$GlobalObject, so it is Lua-reachable.
-- The call is made for the LOCAL player; `called` says only that it ran without raising, and
-- whether the server accepted it is read off the server's XP and the player-stats packet.
-- @args (none)
-- @reply {ok, called [, error]} | string
-- @purpose Calls the Java global SyncXp(getPlayer()) the admin panel uses to push the local player's experience to the server; called says the call ran, not that the server accepted it.
TK.register("xp.sync", function()
    local out = { ok = false, called = false }
    if SyncXp == nil then
        out.error = "SyncXp not exposed to Lua"
        return out
    end
    local ran, err = pcall(SyncXp, getPlayer())
    out.called = ran
    out.ok = ran
    if not ran then out.error = tostring(err) end
    return out
end)

-- <type> <minutes>. Queues the game's own fitness action for the local player, the call
-- ISFitnessUI:onClick makes (ISFitnessUI.lua:280): `ISFitnessAction:new(player, exercise,
-- timeToExe, exeData, exeData.type)` through `ISTimedActionQueue.addGetUpAndThen` (the queue is
-- client-only, #2641). The exercise table is `FitnessExercises.exercisesType`, keyed `squats`,
-- `pushups`, `situp` (singular -- `situps` is accepted and mapped), `burpees`. The third
-- constructor argument is GAME MINUTES the set may run (`endMS = start + timeToExe * 60000`,
-- ISFitnessAction.lua:213), not a repetition count: reps come from the engine's own anim loop
-- (`exerciseRepeat` per ActiveAnimLooped), so a driver reads rep counts off the server. The UI's
-- equip/unequip step is skipped: these four need no item. A player who is not idle, is moving or
-- has an endurance moodle above the threshold has the action refused or stopped by the engine;
-- `queued` says only that the add returned without raising.
-- @args <squats|pushups|situp|burpees> <minutes>
-- @reply {ok, exercise, minutes, queued, queueLen [, error | queueError]} | string
-- @purpose Queues ISFitnessAction for the local player with the named exercise for the given game minutes (not reps); queued says the add ran, the server's Fitness regularity says the exercise did.
TK.register("exercise.do", function(argv)
    local p = getPlayer()
    if not p then return "no local player" end
    local name = argv[1]
    if name == "situps" then name = "situp" end
    local minutes = tonumber(argv[2])
    if name == nil or minutes == nil or minutes <= 0 then
        return "usage: exercise.do <squats|pushups|situp|burpees> <minutes>"
    end
    local out = { ok = false, exercise = name, minutes = minutes }
    if FitnessExercises == nil or FitnessExercises.exercisesType == nil then
        out.error = "no FitnessExercises.exercisesType"
        return out
    end
    local exeData = FitnessExercises.exercisesType[name]
    if exeData == nil then
        out.error = "no exercise " .. tostring(name)
        return out
    end
    if ISFitnessAction == nil or ISTimedActionQueue == nil or ISTimedActionQueue.addGetUpAndThen == nil then
        out.error = "no ISFitnessAction/ISTimedActionQueue.addGetUpAndThen"
        return out
    end
    local ran, err = pcall(function()
        local action = ISFitnessAction:new(p, name, minutes, exeData, exeData.type)
        ISTimedActionQueue.addGetUpAndThen(p, action)
    end)
    out.queued = ran
    out.ok = ran
    if not ran then out.queueError = tostring(err) end
    local qlen = nil
    local rq, q = pcall(ISTimedActionQueue.getTimedActionQueue, p)
    if rq and q ~= nil and q.queue ~= nil then qlen = #q.queue end
    out.queueLen = qlen
    return out
end)

-- index-first value read (#0935): the value of obj:name(...) or nil when the member is absent.
local function got(obj, name, ...)
    local _, v = TK.call(obj, name, ...)
    return v
end

-- [<bookType>]. Queues the game's own read action on a book in the local inventory:
-- `ISTimedActionQueue.add(ISReadABook:new(player, item))` (the install's ISReadABook.lua:483
-- takes (character, item) only -- the brief's third argument does not exist). The book is the
-- first inventory item of the named type (the part after the dot of a full type, default
-- `Base.Book`); when there is none, one is added client-side first, exactly as item.spawn does,
-- and `spawned` says so. The action sets `caloriesModifier = 0.5` on itself (:511), which is the
-- value the activity gate reads server-side from `getCharacterActions()`.
-- @args [<bookType>]
-- @reply {ok, bookType, spawned, itemId, queued [, error | queueError]} | string
-- @purpose Queues ISReadABook on an inventory book of the given type (spawned client-side when absent) for the local player; queued says the add ran.
TK.register("action.read", function(argv)
    local p = getPlayer()
    if not p then return "no local player" end
    local full = argv[1] or "Base.Book"
    local short = string.match(full, "([^%.]+)$") or full
    local out = { ok = false, bookType = full, spawned = false }
    if ISReadABook == nil or ISTimedActionQueue == nil then
        out.error = "no ISReadABook/ISTimedActionQueue"
        return out
    end
    local inv = got(p, "getInventory")
    local item = got(inv, "getFirstTypeRecurse", short)
    if item == nil then
        item = got(inv, "AddItem", full)
        out.spawned = true
    end
    if item == nil then
        out.error = "no item " .. tostring(full)
        return out
    end
    out.itemId = got(item, "getID")
    local ran, err = pcall(function()
        ISTimedActionQueue.add(ISReadABook:new(p, item))
    end)
    out.queued = ran
    out.ok = ran
    if not ran then out.queueError = tostring(err) end
    return out
end)

-- <dx> <dy> <seconds>. Holds sprint on the local player for a window: queues the same walk
-- action player.run does (ISWalkToTimedAction to the square dx,dy away -- the move intent), then
-- an OnTick watcher (trait.watch's arm-and-result pattern) sets setSprinting(true) and
-- setRunning(true) every tick until the deadline and, every 0.5 s of wall time, records what the
-- CLIENT's isSprinting/isRunning/isPlayerMoving read (at most 40 samples, so seconds <= 20).
-- It answers at once; at the deadline the trace goes to player-sprint.json through TK.result.
-- The run flag has never reached the server (#0591/#2810); this records the client side only
-- and does not try to make the flag arrive -- the driver pairs it with the server's stats.get.
TK.sprintWatch = TK.sprintWatch or { armed = false }
local SPRINT_MAX_SECONDS = 20

local function sprintOnTick()
    local w = TK.sprintWatch
    if not w.armed then return end
    local p = getPlayer()
    if p == nil then return end
    local now = TK.now()
    TK.call(p, "setSprinting", true)
    TK.call(p, "setRunning", true)
    if now >= w.nextSample and #w.samples < 40 then
        local _, sp = TK.call(p, "isSprinting")
        local _, ru = TK.call(p, "isRunning")
        local _, mv = TK.call(p, "isPlayerMoving")
        w.samples[#w.samples + 1] = { t = now - w.armedWall, sprinting = sp, running = ru, moving = mv }
        w.nextSample = now + 500
    end
    if now >= w.deadline then
        w.armed = false
        TK.call(p, "setSprinting", false)
        TK.call(p, "setRunning", false)
        TK.result("player-sprint", { dx = w.dx, dy = w.dy, seconds = w.seconds, samples = w.samples,
                                     sampleCount = #w.samples })
    end
end

if not TK.sprintHooked and Events ~= nil and Events.OnTick ~= nil then
    Events.OnTick.Add(function() sprintOnTick() end)
    TK.sprintHooked = true
end

-- @args <dx> <dy> <seconds>
-- @reply {armed, dx, dy, seconds, queued [, queueError], result, file} | {error} | string
-- @purpose Holds sprint and run on the local player for up to 20 s while a queued walk moves it, answers at once, and writes the client's sprint/run/moving reads every 0.5 s to player-sprint.json.
TK.register("player.sprint", function(argv)
    local p = getPlayer()
    if not p then return "no local player" end
    local dx, dy, seconds = tonumber(argv[1]), tonumber(argv[2]), tonumber(argv[3])
    if dx == nil or dy == nil or seconds == nil or seconds <= 0 or seconds > SPRINT_MAX_SECONDS then
        return "usage: player.sprint <dx> <dy> <seconds>  (0 < seconds <= 20)"
    end
    if not TK.sprintHooked then return { error = "no Events.OnTick on this side" } end
    if TK.sprintWatch.armed then return { error = "a player.sprint window is already armed" } end
    local cell = getCell()
    if not cell then return { error = "no getCell()" } end
    local px, py, pz = got(p, "getX"), got(p, "getY"), got(p, "getZ")
    if px == nil or py == nil or pz == nil then return { error = "no player position" } end
    local ok, sq = TK.call(cell, "getGridSquare", px + dx, py + dy, pz)
    if not ok or sq == nil then return { error = "no grid square at +" .. tostring(dx) .. "," .. tostring(dy) } end
    if not ISWalkToTimedAction or not ISTimedActionQueue then
        return { error = "no ISWalkToTimedAction/ISTimedActionQueue" }
    end
    local out = { armed = true, dx = dx, dy = dy, seconds = seconds, result = "player-sprint",
                  file = "pzt-results/player-sprint.json" }
    local ran, err = pcall(function()
        ISTimedActionQueue.add(ISWalkToTimedAction:new(p, sq))
    end)
    out.queued = ran
    if not ran then out.queueError = tostring(err) end
    local start = TK.now()
    if start == 0 then return { error = "no getTimestampMs()" } end
    TK.sprintWatch = { armed = true, dx = dx, dy = dy, seconds = seconds, samples = {},
                       armedWall = start, nextSample = start, deadline = start + seconds * 1000 }
    return out
end)

-- [<n>]. Swings the local player's weapon at the nearest zombie within 2 tiles, n times (default
-- 1, at most 20). The zombie is found by walking `getCell():getZombieList()` by size/get
-- (index-first). There is NO spawn path: the harness has no zombie spawner, and the only Lua
-- spawn globals (`addZombiesInOutfit`, `createZombie`) are what the admin debug UI uses -- a
-- client-side call in multiplayer would create a zombie the server never owns -- so with no
-- zombie in range the command replies `{ ok = false, reason }` and the driver places one by
-- another means. With no primary-hand item it spawns and equips `Base.BaseballBat` first. It
-- answers at once; an OnTick watcher then, every 1.2 s of wall time, faces the zombie
-- (`faceThisObject`) and calls `DoAttack(0)` (IsoPlayer.DoAttack(F)Z, the body AttemptAttack
-- calls with the charge time) until n swings are made or the zombie is gone, and writes
-- attack-melee.json with the per-swing DoAttack return values. `swings` in the reply is the
-- number scheduled; the artifact carries the number made.
TK.attackWatch = TK.attackWatch or { armed = false }
local ATTACK_MAX_SWINGS = 20

local function attackOnTick()
    local w = TK.attackWatch
    if not w.armed then return end
    local p = getPlayer()
    if p == nil then return end
    local now = TK.now()
    if now < w.nextAt then return end
    local z = w.zombie
    local dead = true
    if z ~= nil then
        local _, d = TK.call(z, "isDead")
        dead = (d == true)
    end
    if w.made >= w.n or dead then
        w.armed = false
        TK.result("attack-melee", { n = w.n, swings = w.made, targetDead = dead, returns = w.returns })
        return
    end
    TK.call(p, "faceThisObject", z)
    local ran, ret = pcall(function()
        local f = p["DoAttack"]
        if f == nil then return "no DoAttack" end
        return f(p, 0)
    end)
    w.made = w.made + 1
    w.returns[#w.returns + 1] = ran and tostring(ret) or ("error: " .. tostring(ret))
    w.nextAt = now + 1200
end

if not TK.attackHooked and Events ~= nil and Events.OnTick ~= nil then
    Events.OnTick.Add(function() attackOnTick() end)
    TK.attackHooked = true
end

-- @args [<n>]
-- @reply {ok, target, swings, weapon, result, file} | {ok, reason} | string
-- @purpose Swings the local player's weapon n times at the nearest zombie within 2 tiles (no spawn path; ok=false when none is in range) and writes the per-swing DoAttack results to attack-melee.json.
TK.register("attack.melee", function(argv)
    local p = getPlayer()
    if not p then return "no local player" end
    local n = tonumber(argv[1]) or 1
    if n < 1 or n > ATTACK_MAX_SWINGS then return "usage: attack.melee [<n>]  (1 <= n <= 20)" end
    if not TK.attackHooked then return { ok = false, reason = "no Events.OnTick on this side" } end
    if TK.attackWatch.armed then return { ok = false, reason = "an attack.melee window is already armed" } end
    local cell = getCell()
    if not cell then return { ok = false, reason = "no getCell()" } end
    local list = got(cell, "getZombieList")
    if list == nil then return { ok = false, reason = "no getCell():getZombieList()" } end
    local best, bestD = nil, 2.0
    local px, py = got(p, "getX"), got(p, "getY")
    local count = got(list, "size") or 0
    for i = 0, count - 1 do
        local z = got(list, "get", i)
        if z ~= nil then
            local dx, dy = got(z, "getX") - px, got(z, "getY") - py
            local d = math.sqrt(dx * dx + dy * dy)
            if d <= bestD then best, bestD = z, d end
        end
    end
    if best == nil then
        return { ok = false, reason = "no zombie within 2 tiles and no safe client-side spawn path (a client addZombiesInOutfit is not server-owned in MP)" }
    end
    local weapon = got(p, "getPrimaryHandItem")
    if weapon == nil then
        local bat = got(got(p, "getInventory"), "AddItem", "Base.BaseballBat")
        if bat ~= nil then
            TK.call(p, "setPrimaryHandItem", bat)
            weapon = bat
        end
    end
    local start = TK.now()
    TK.attackWatch = { armed = true, n = n, made = 0, zombie = best, returns = {}, nextAt = start }
    return { ok = true, target = { x = got(best, "getX"), y = got(best, "getY"), dist = bestD }, swings = n,
             weapon = weapon and got(weapon, "getFullType") or "none", result = "attack-melee",
             file = "pzt-results/attack-melee.json" }
end)
-- <a.b.c> <value>. TEST-ONLY INSTRUMENT, the client twin of the server command: the harness mod is installed only by test profiles and is never
-- shipped. Assigns a scalar to a field of any client-side Lua table reached by a dotted path from the
-- globals, e.g. `NR.client.someFlag false`, so an acceptance driver can reach a plain Lua field
-- that `globalmoddata.setpath` cannot (it assigns modData leaves only). It stands in for a chunk runner
-- because `loadstring` is removed on 42.20.x (docs/platform/lessons.md). The value is `true`, `false`,
-- `nil`, a number or else the string as given; every path segment but the last must already be a table
-- (a numeric-looking segment is tried as a string key first, then as a number), and the field is never
-- created on a missing parent. The bus is the harness's own file channel, so only the driver writes it.
-- @args <a.b.c> <value>
-- @reply {ok, side, path, before, after [, err]} | string
-- @purpose Test-only: assigns a true, false, nil, number or string scalar to a field of a client Lua table reached by a dotted path from the globals, replying the value before and after.
TK.register("lua.setpath", function(argv)
    if argv[1] == nil or argv[2] == nil then return "usage: lua.setpath <a.b.c> <value>" end
    local out = { ok = false, side = TK.side, path = argv[1] }
    local raw = argv[2]
    local value = raw
    if raw == "true" then value = true
    elseif raw == "false" then value = false
    elseif raw == "nil" then value = nil
    elseif tonumber(raw) ~= nil then value = tonumber(raw) end
    local segs = {}
    for seg in string.gmatch(argv[1], "[^%.]+") do segs[#segs + 1] = seg end
    local node = _G
    local i = 1
    while i < #segs do
        local nxt = node[segs[i]]
        if nxt == nil and tonumber(segs[i]) ~= nil then nxt = node[tonumber(segs[i])] end
        if type(nxt) ~= "table" then
            out.err = "segment " .. segs[i] .. " is " .. type(nxt) .. ", not a table"
            return out
        end
        node = nxt
        i = i + 1
    end
    local last = segs[#segs]
    out.before = tostring(node[last])
    node[last] = value
    out.after = tostring(node[last])
    out.ok = true
    return out
end)

-- ---- Plan 11 Task 19: a player's own-action latency (Decision 6 open item 3) ---------------------------------
-- action.latency <fullType> <n> queues n eats of a fresh <fullType>, one after another, and records for each the
-- client wall ms from the queue to the item leaving the container it was found in (the server's completion
-- reaching this client); a sample that has not completed in 30 s is recorded as timed out (done false).
-- action.latency read replies them. findOrSpawn's trap holds: a "client" spawn is an item the server never heard
-- of, so spawn the items server-side (RCON additem) first. ItemContainer.containsID(int) is on the 42.21 jar.
C.lat = nil

function C.latStart(L)
    local p = getPlayer()
    local it = findOrSpawn(L.fullType)
    if not it then
        L.done, L.reason = true, "no item " .. tostring(L.fullType)
        return
    end
    if not instanceof(it, "Food") then   -- no pcall: a caught raise still parks a debug client
        L.done, L.reason = true, "not a Food item"
        return
    end
    local _, cont = TK.call(it, "getContainer")
    L.cont = cont or p:getInventory()
    local act = ISEatFoodAction:new(p, it, 1.0)
    ISTimedActionQueue.add(act)
    L.id = it:getID()
    L.t0 = getTimestampMs()
    L.maxTime = act.maxTime
end

function C.latTick()
    local L = C.lat
    if L == nil or L.done then return end
    local p = getPlayer()
    if p == nil then return end
    local now = getTimestampMs()
    if L.id == nil then
        C.latStart(L)
        return
    end
    local gone = not L.cont:containsID(L.id)
    if gone or now - L.t0 > 30000 then
        L.samples[#L.samples + 1] = { ms = now - L.t0, done = gone, maxTime = L.maxTime }
        L.id = nil
        if #L.samples >= L.n then
            L.done = true
            L.doneAt = now
        end
    end
end

if Events ~= nil and Events.OnTick ~= nil then Events.OnTick.Add(function() C.latTick() end) end

-- @args <fullType> <n> | read
-- @reply {ok, armed, fullType, n} | {ok, done, n, samples, reason} | string
-- @purpose Test-only: queues n sequential eats of a fresh <fullType> and records each eat's client wall ms from the queue to the item leaving its container; read replies the samples.
TK.register("action.latency", function(argv)
    if argv[1] == "read" then
        local L = C.lat
        if L == nil then return { ok = false, reason = "not armed" } end
        return { ok = true, done = L.done, n = L.n, samples = L.samples, reason = L.reason }
    end
    local n = tonumber(argv[2])
    if argv[1] == nil or n == nil or n < 1 then return "usage: action.latency <fullType> <n> | read" end
    C.lat = { fullType = argv[1], n = n, samples = {}, done = false, id = nil }
    return { ok = true, armed = true, fullType = argv[1], n = n }
end)
