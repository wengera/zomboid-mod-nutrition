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

-- <user> <PerkName>. The XP READ perk.set has never had: `getPerkLevel` is the only perk
-- number on the shipped bus and a 10-XP grant does not move a level, so every XP-sized effect
-- in the game has so far been unmeasurable. Slice 09 needs it as a client/server
-- discriminator -- Food.update grants the cook 10 Cooking XP and only ever on the server
-- (@789 GameServer.server; an MP client that runs the same transition skips the block
-- entirely) -- so an XP delta across the action says WHICH side ran it, independently of any
-- field reading.
--
-- Two calls, never one: jar-confirmed on 42.20.4, IsoGameCharacter.getXp() is zero-argument
-- and answers the inner IsoGameCharacter$XP object, and the number comes from
-- XP.getXP(PerkFactory$Perk)F on THAT object. There is no single getter for it, which is
-- exactly why `witness.fields` (zero-argument getters only) cannot read it.
TK.register("perk.xp", function(argv)
    local p = findPlayer(argv[1])
    if not p then return "no online player " .. tostring(argv[1]) end
    local name = argv[2]
    if not name then return "usage: perk.xp <user> <PerkName>" end
    local perk = Perks and Perks[name]
    if not perk then return { error = "no Perks." .. tostring(name), perk = name } end
    local out = { perk = name, user = tostring(argv[1]), side = TK.side }
    local okXp, xp = TK.call(p, "getXp")
    if not okXp or xp == nil then
        out.error = "no IsoGameCharacter:getXp()"
        return out
    end
    local okV, v = TK.call(xp, "getXP", perk)
    if not okV then
        out.error = "no XP:getXP(Perk)"
    else
        out.xp = v
    end
    local _, lvl = TK.call(p, "getPerkLevel", perk)
    out.level = lvl
    out.serverWorldAge = getGameTime():getWorldAgeHours()
    return out
end)

-- ---- body-side commands (slice 03) -------------------------------------------
-- Everything below is SERVER-side on purpose. Hunger, thirst, endurance and the whole
-- Nutrition block tick only here in MP: `updateStats_WakeState @8-@26 L10227` and the twin
-- guard in `updateThirst @38-@73 L10377` are `GameServer.server || (!GameClient.client &&
-- IsoPlayer.getInstance() == this)`, `IsoPlayer.updateEndurance @0-@13 L3427` returns early
-- on a client, and `Nutrition.update @42 L75` is `!GameClient.client` (03-notes Q7). A client
-- read is a mirror of the last 1 Hz PlayerStatsPacket and nothing more.

-- <user>. The atomic sample the rate fits are built from -- see TK.bodySnapshot for why it is
-- one command rather than three.
TK.register("stats.get", function(argv)
    local p = findPlayer(argv[1])
    if not p then return "no online player " .. tostring(argv[1]) end
    return TK.bodySnapshot(p)
end)

-- <option> <value>. The SERVER half of the client's `sandbox.set`, and a different thing:
-- the client's admin panel never calls getSandboxOptions():set() (ISServerSandboxOptionsUI
-- .lua:738 guards it with `if not isClient()`) and pushes a copy instead, so a client flip is
-- local. Here the write IS the live server config -- SandboxOptions.getStatsDecreaseMultiplier
-- reads it on the next tick, no push needed.
-- `value` is a number for enum/integer options (StatsDecrease is newEnumOption(...,5,3)) and
-- true|false for booleans; both routes are tried, and the resulting multiplier is read back
-- when the getter is exposed -- that read alone settles the inferred key->value mapping
-- (1 -> 2.0 ... 5 -> 0.65, 03-notes "Open / uncertain" #1) without needing a rate measurement.
TK.register("sandbox.set", function(argv)
    local name = argv[1]
    if not name then return "usage: sandbox.set <option> [<value>]" end
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
    local _, multBefore = TK.call(opts, "getStatsDecreaseMultiplier")
    out.statsDecreaseMultiplierBefore = multBefore
    if argv[2] ~= nil then
        local value
        if argv[2] == "true" or argv[2] == "false" then value = (argv[2] == "true")
        else value = tonumber(argv[2]) end
        if value == nil then return "expected a number or true|false, got " .. tostring(argv[2]) end
        out.requested = value
        -- pcall wraps the CALL, not the lookup: TK.call has already ruled out "call nil" (the
        -- one failure pcall cannot catch), so what is left is an argument/type mismatch inside
        -- SandboxOptions:set, which pcall does catch and which must fall through to the
        -- per-option setter rather than kill the ack.
        local ran, present = pcall(TK.call, opts, "set", name, value)
        if ran and present then
            out.route = "SandboxOptions:set(name,value)"
        else
            if not ran then out.setError = tostring(present) end
            local ran2, present2 = false, false
            if opt then ran2, present2 = pcall(TK.call, opt, "setValue", value) end
            if ran2 and present2 then out.route = "getOptionByName():setValue()"
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
    local _, multAfter = TK.call(opts, "getStatsDecreaseMultiplier")
    out.statsDecreaseMultiplierAfter = multAfter
    return out
end)

-- <user> <TraitName> <add|remove>. The game's own route is
-- `char:getCharacterTraits():add(CharacterTrait.X)` (ISPlayerStatsUI.lua:594, XpUpdate.lua:216),
-- i.e. the ENUM, not the string -- so the field is resolved first and the call skipped when it
-- is nil (a nil argument into a live Java method is the mismatch pcall cannot catch).
-- Accepts either spelling: "HeartyAppetite" (the registered string) or "HEARTY_APPETITE" (the
-- static field). The read-back is TK.traitNames, not hasTrait: `hasTrait` is called with a
-- CharacterTrait throughout the game's own Lua, so the string it would need here is exactly
-- the argument mismatch that cannot be caught. Note the arg parser splits on whitespace, so
-- "Very Underweight" is not addressable through this command -- it is not needed either, the
-- band traits are driven by weight and read back through the same trait list.
local TRAIT_FIELDS = { HeartyAppetite = "HEARTY_APPETITE", LightEater = "LIGHT_EATER",
                       HighThirst = "HIGH_THIRST", LowThirst = "LOW_THIRST",
                       Obese = "OBESE", Overweight = "OVERWEIGHT", Underweight = "UNDERWEIGHT",
                       Emaciated = "EMACIATED" }

TK.register("trait.set", function(argv)
    local p = findPlayer(argv[1])
    if not p then return "no online player " .. tostring(argv[1]) end
    local name, op = argv[2], argv[3]
    if not name or (op ~= "add" and op ~= "remove") then
        return "usage: trait.set <user> <TraitName> <add|remove>"
    end
    local field = TRAIT_FIELDS[name] or name
    local out = { trait = name, field = field, op = op }
    local before = TK.traitNames(p)
    out.before = TK.hasTraitName(before, name)
    local enum = CharacterTrait and CharacterTrait[field]
    out.enumFound = enum ~= nil
    local _, coll = TK.call(p, "getCharacterTraits")
    out.collection = coll ~= nil and "getCharacterTraits()" or "none"
    if coll ~= nil and enum ~= nil then
        local ran, present = pcall(TK.call, coll, op, enum)
        if ran and present then out.route = "getCharacterTraits():" .. op .. "(CharacterTrait." .. field .. ")"
        else
            out.route = "none"
            if not ran then out.callError = tostring(present) end
        end
    else
        out.route = "none"
        out.error = (coll == nil and "no IsoGameCharacter:getCharacterTraits" or
                     "no CharacterTrait." .. tostring(field))
    end
    local after, list = TK.traitNames(p)
    out.after = TK.hasTraitName(after, name)
    out.traitList = list
    out.held = (op == "add") == (out.after == true)
    return out
end)

-- <user> <true|false>. IsoGameCharacter.setAsleep -- the same call the game's own sleep dialog
-- makes (ISSleepDialog.lua:75) and the one the server applies for a remote player
-- (ClientCommands.lua:608). The asleep flag is what picks updateStats_Sleeping /
-- updateCalories' 0.003 branch (03-notes Q1/Q2); whether it HOLDS on a dedicated server with
-- a live client attached is a measurement, hence the read-back.
TK.register("player.sleep", function(argv)
    local p = findPlayer(argv[1])
    if not p then return "no online player " .. tostring(argv[1]) end
    if argv[2] ~= "true" and argv[2] ~= "false" then
        return "usage: player.sleep <user> <true|false>"
    end
    local value = argv[2] == "true"
    local out = { requested = value }
    local _, before = TK.call(p, "isAsleep")
    out.before = before
    out.setAsleep = TK.call(p, "setAsleep", value)
    if not out.setAsleep then out.error = "no IsoGameCharacter:setAsleep" end
    local _, after = TK.call(p, "isAsleep")
    out.after = after
    out.held = (after == value)
    return out
end)

-- <user>. Nutrition.applyTraitFromWeight() on demand. Vanilla runs it only every 2000
-- updateWeight calls (`updateWeight @329-@357 L200-L203`), so a fresh setWeight does not show
-- up in hasTrait for a while; the band sweep measures that latency once and then forces the
-- refresh here for the remaining rows.
TK.register("nutrition.applytraits", function(argv)
    local p = findPlayer(argv[1])
    if not p then return "no online player " .. tostring(argv[1]) end
    -- Guarded like every other accessor here: a raw `p:getNutrition():getWeight()` on a build
    -- that moved either method is an argument/index error Kahlua does not let pcall catch, and
    -- it would take the whole command bus down rather than answering with a usable error.
    local _, n = TK.call(p, "getNutrition")
    if n == nil then return "no IsoGameCharacter:getNutrition" end
    local out = {}
    local okW, w = TK.call(n, "getWeight")
    if okW then out.weight = w else out.error = "no Nutrition:getWeight" end
    out.applied = TK.call(n, "applyTraitFromWeight")
    -- Keep the FIRST error: a build missing getWeight is the more informative failure, and
    -- overwriting it here would hide it behind the second one.
    if not out.applied and out.error == nil then
        out.error = "no Nutrition:applyTraitFromWeight"
    end
    local set, list = TK.traitNames(p)
    local traits = {}
    for key, tname in pairs(TK.WEIGHT_TRAITS) do traits[key] = TK.hasTraitName(set, tname) end
    out.traits, out.traitList = traits, list
    return out
end)

-- <user> <value>. BodyDamage.healthFromFoodTimer, the FOOD_EATEN driver (03-notes Q5). Needed
-- in both directions: primed to 0 before every hunger-rate window (the moodle silently zeroes
-- the hunger rate) and read back during the FOOD_EATEN row.
TK.register("foodtimer.set", function(argv)
    local p = findPlayer(argv[1])
    if not p then return "no online player " .. tostring(argv[1]) end
    local v = tonumber(argv[2])
    if v == nil then return "usage: foodtimer.set <user> <value>" end
    local _, bd = TK.call(p, "getBodyDamage")
    if bd == nil then return "no IsoGameCharacter:getBodyDamage" end
    local out = { requested = v }
    local _, before = TK.call(bd, "getHealthFromFoodTimer")
    out.before = before
    out.set = TK.call(bd, "setHealthFromFoodTimer", v)
    if not out.set then out.error = "no BodyDamage:setHealthFromFoodTimer" end
    local _, after = TK.call(bd, "getHealthFromFoodTimer")
    out.after = after
    return out
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
    -- slice 09: `chef` is the only STRING setter, and it is here for one reason -- the
    -- Cooking-XP grant inside Food.update (@755-@779 on 42.20.4) is gated on chef != null and
    -- non-empty, and then @789 GameServer.server -> getPlayerByUserNameForCommand(chef) ->
    -- addXp(player, Perks.Cooking, 10). An RCON `additem` spawn leaves chef null, so without
    -- this setter that whole branch is unreachable from the bus and the "only the server
    -- grants XP" asymmetry can never be measured. Jar-confirmed: Food.setChef(Ljava/lang/
    -- String;)V. The value is a username, so it cannot contain a space (splitArgs splits on
    -- %S+) -- that is a limitation of the bus, not of the setter.
    chef = { "setChef", "string" },
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
    elseif spec[2] == "string" then
        -- An empty string is refused rather than passed through: Food.update's XP gate reads
        -- chef.isEmpty() as "no chef", so `item.set ... chef ""` would look like a write and
        -- behave like a clear. Nothing on the bus needs to clear it.
        if argv[4] == nil or argv[4] == "" then return "expected a string, got " .. tostring(argv[4]) end
        value = tostring(argv[4])
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

-- ---- script-item census (slice 05) -------------------------------------------
-- ScriptManager.getAllItems() is the game's own loaded-item list: the live cross-check for
-- tools/food_scan.py, which reads the same definitions off media/scripts/ instead. The game's
-- own Lua reads an entry's type as `itemScript:getItemType():toString()` -- a ResourceLocation
-- string, "base:food" (ISFluidItemsViewPanel.lua:141) -- so match on the "food" SUBSTRING
-- rather than the whole string: a registry rename cannot then silently zero the bucket, and
-- the raw string is counted in `byType` either way, so a rename is visible rather than
-- guessed at. `Item` (the script object) exposes no component accessor, so fluid CONTAINERS
-- have no live route here -- only fluid DEFINITIONS do, through the list below.
local FLUID_GETTERS = { "HungerChange", "ThirstChange", "Calories", "Carbohydrates", "Lipids",
                        "Proteins", "FatigueChange", "StressChange", "UnhappyChange", "Alcohol",
                        "FluReduction", "PainReduction", "EnduranceChange", "FoodSicknessChange" }

-- `getScriptManager` is checked for nil BEFORE it is called. A nil global raises Kahlua's
-- "tried to call nil", which pcall does not catch here (see TK.call in the core) -- it would
-- take the whole poll handler with it instead of answering the bus with an error.
local function scriptManager()
    if getScriptManager == nil then return nil end
    return getScriptManager()
end

-- (list, size) for a ScriptManager accessor; (nil, 0) when this build does not expose it.
-- `size` is type-checked because `n - 1` on a nil would be an arithmetic error in the loop.
local function listOf(sm, method)
    local ok, all = TK.call(sm, method)
    if not ok or all == nil then return nil, 0 end
    local _, n = TK.call(all, "size")
    return all, (type(n) == "number") and n or 0
end

TK.register("items.count", function()
    local sm = scriptManager()
    local all, n = listOf(sm, "getAllItems")
    if all == nil then return "no ScriptManager:getAllItems()" end
    local out = { total = 0, food = 0, byType = {}, foodByModule = {} }
    for i = 0, n - 1 do
        local _, sc = TK.call(all, "get", i)
        if sc ~= nil then
            local _, itemType = TK.call(sc, "getItemType")
            -- tostring() is the fallback route: TK.json already relies on Kahlua handing back
            -- a Java object's own toString(), so a build that does not expose the method by
            -- name still yields the ResourceLocation rather than a "?" bucket.
            local okS, s = TK.call(itemType, "toString")
            local t = "?"
            if okS and s ~= nil then t = tostring(s)
            elseif itemType ~= nil then t = tostring(itemType) end
            out.byType[t] = (out.byType[t] or 0) + 1
            out.total = out.total + 1
            if string.find(string.lower(t), "food") then
                out.food = out.food + 1
                local _, m = TK.call(sc, "getModuleName")
                local mod = tostring(m or "?")
                out.foodByModule[mod] = (out.foodByModule[mod] or 0) + 1
            end
        end
    end
    local fl, fn = listOf(sm, "getAllFluidDefinitionScripts")
    out.fluidDefs = fn
    -- 0 fluids and "no such accessor" both read as fluidDefs=0, and they are different
    -- findings (the second one is what makes the 61-fluid count scanner-only): say which.
    if fl == nil then out.fluidDefsError = "no ScriptManager:getAllFluidDefinitionScripts()" end
    return out
end)

-- <fullType>. The SERVER half of the client's `item.script`, added by slice 09: script data
-- is loaded per side and never synced, so one side answering is not evidence about the other
-- and a mod teardown wants both. Same implementation (TK.scriptValues in the core), so the
-- two replies differ only where the two sides genuinely differ; `side` in the reply says
-- which is talking. The 09-11 plan's cold-start command inventory already listed
-- `item.script <type>` under *server* -- until now that line was simply wrong.
TK.register("item.script", function(argv)
    if getScriptManager == nil then return "no getScriptManager()" end
    local want = tostring(argv[1] or "")
    if want == "" then return "usage: item.script <fullType>" end
    return TK.scriptValues(want) or ("no script item " .. want)
end)

-- The id a fluid definition answers to, and the accessor that produced it.
-- `getFluidTypeString()` is the game's own route (ISFluidOverviewPanel.lua:113), but on
-- 42.20.4 it answers for only 34 of the 61 definitions -- MEASURED, t4probe-20260910-080930:
-- it returns nothing for every fluid that also has a built-in FluidType enum constant (Water,
-- TaintedWater, Petrol, Beer, Wine, Whiskey, Coffee, Tea, Honey, SodaPop, Blood, the milks...)
-- and carries the string only for the script-only ones (Cola, the juices, the sodas, the
-- spirits). Reading it alone therefore made `fluid.script Water` miss a fluid that
-- media/scripts/generated/fluids.txt plainly defines. So fall back to the enum and stringify
-- it, and report which route answered so the reply is never ambiguous about where its id
-- came from.
local function fluidId(f)
    local ok, s = TK.call(f, "getFluidTypeString")
    if ok and s ~= nil and tostring(s) ~= "" then return tostring(s), "getFluidTypeString" end
    local okT, ft = TK.call(f, "getFluidType")
    if okT and ft ~= nil and tostring(ft) ~= "" then return tostring(ft), "getFluidType" end
    return "", "none"
end

-- One fluid definition's LIVE property getters, for the same cross-check on the drink side.
-- A getter this build does not expose is reported in `missingGetters` rather than left
-- silently absent from the reply -- an absent key would otherwise be indistinguishable from a
-- fluid that genuinely carries no such property.
TK.register("fluid.script", function(argv)
    local want = tostring(argv[1] or "")
    if want == "" then return "usage: fluid.script <fluidId>" end
    local all, n = listOf(scriptManager(), "getAllFluidDefinitionScripts")
    if all == nil then return "no ScriptManager:getAllFluidDefinitionScripts()" end
    local seen = {}
    for i = 0, n - 1 do
        local _, f = TK.call(all, "get", i)
        local id, route = fluidId(f)
        -- Every id the list yielded, so a miss reports which ids DO exist instead of only
        -- that this one does not; a definition neither route could name keeps its position
        -- as "?", which separates "the definition is absent" from "it is there but unnamed".
        seen[#seen + 1] = (id ~= "") and id or "?"
        if id ~= "" and (id == want or id == "Base." .. want or "Base." .. id == want) then
            local out = { fluidType = id, fluidTypeRoute = route }
            -- These two go through the same rule as the 14 property getters below: the TK.call
            -- ok flag is kept, so a member this build does not expose lands in `missingGetters`
            -- instead of silently dropping the key. It matters most for `hasPropertiesSet`,
            -- which legitimately answers `false` on 10 of the 61 fluids (the ones with no
            -- `Properties` block at all) -- discarding the flag would make "not exposed"
            -- indistinguishable from "exposed and false".
            local missing = {}
            local okDn, dn = TK.call(f, "getDisplayName")
            if okDn then out.displayName = dn else missing[#missing + 1] = "getDisplayName" end
            local okHp, hp = TK.call(f, "hasPropertiesSet")
            if okHp then out.hasPropertiesSet = hp
            else missing[#missing + 1] = "hasPropertiesSet" end
            for gi = 1, #FLUID_GETTERS do
                local g = FLUID_GETTERS[gi]
                local okg, v = TK.call(f, "get" .. g)
                if okg then out[g] = v else missing[#missing + 1] = "get" .. g end
            end
            if #missing > 0 then out.missingGetters = missing end
            return out
        end
    end
    return "no fluid '" .. want .. "' among " .. string.format("%.0f", n) .. " definitions: "
           .. table.concat(seen, ",")
end)

-- ---- live drink probe (slice 05, task 5b) ------------------------------------
-- `drink <user> <fullType> [fraction]` -- the drink action's payload with the timed action
-- taken off, so the per-litre fluid arithmetic can be MEASURED rather than read off the jar
-- (slice 01 open question #11; 05-notes q3 "Open" #1).
--
-- SERVER-side because the server owns the write. An MP client never calls `DrinkFluid` at
-- all: `LuaTimedActionNew.complete @31 L162` skips the Lua `complete` when
-- `GameClient.client`, and the action's own hooks are `if not isClient()` (`:26-:30`) and
-- `if isServer()` (`:42-:48`). A client-side probe would measure the 1 Hz mirror, not the
-- store.
--
-- The call is the SAME entry point the shipped action uses. `ISDrinkFluidAction:updateEat`
-- (`:109-:120`) ends in `self.character:DrinkFluid(self.item, deltaToConsume,
-- self.useUtensil)` -- the `(InventoryItem, F, Z)` overload, with `useUtensil` always false
-- (`:new`) and never read (the third argument is dead in the jar, q3 notes Step 6). What the
-- action varies across its ~160 ticks is only `deltaToConsume`, and `complete()` lands on
-- exactly `f = 1`; so one call at `f = <fraction>` IS the finished action minus the
-- animation. The `syncItemFields()` that follows it in `updateEat` is made here too, and
-- reported, so the route is the shipped one end to end.
--
-- `f` is a share of the container's CURRENT contents, not of its capacity --
-- `removeFluid(getAmount() * f, true)`. On a full can `amount == capacity`, so `f = 1`
-- empties it and `f = 0.5` halves it; a SECOND `0.5` would take half of what is left, not
-- the rest. `before.container.amount` / `after.container.amount` are in the reply so that
-- reading never rests on the reasoning.
--
-- Both snapshots are taken INSIDE this call, on either side of the one Java line, so they
-- are the same game tick: `Nutrition.update` and `updateStats_*` run on their own ticks and
-- cannot interleave with a command handler, and the passive drain between them is therefore
-- zero rather than small. `worldAgeBefore` / `worldAgeAfter` are in the reply so that is
-- checkable rather than asserted -- the experiment's `stats.get` / `nutrition.get` bracket
-- around the command is the independent outer reading, and that one DOES carry drift.
--
-- Which instance: `item.get`'s finder is `getFirstTypeRecurse`, which answers the FIRST
-- match -- and after one full drink the first match is an EMPTY can, so a second probe on
-- the same type would drink nothing and report it as a zero delta. This command picks the
-- FULLEST instance instead, ties broken by the highest id (the newest), and puts every
-- candidate's id and amount in the reply, so the choice is auditable rather than implicit.
local FLUID_PROPS = { calories = "getCalories", carbs = "getCarbohydrates",
                      lipids = "getLipids", proteins = "getProteins",
                      hungerChange = "getHungerChange", thirstChange = "getThirstChange",
                      unhappyChange = "getUnhappyChange", fatigueChange = "getFatigueChange",
                      stressChange = "getStressChange", alcohol = "getAlcohol",
                      poison = "getPoison", enduranceChange = "getEnduranceChange",
                      fluReduction = "getFluReduction", painReduction = "getPainReduction",
                      foodSicknessChange = "getFoodSicknessChange" }

-- `FluidContainer.getProperties()` is ALREADY litres-weighted -- `recalculateCaches @234-@250
-- L632` sums `perLitre x litres` -- so this block is what a FULL container delivers, and
-- `DrinkFluid` multiplies it by `f`. Read BEFORE the call: an emptied container recalculates
-- to all zeroes. A getter this build does not expose lands in `missingGetters` rather than
-- being silently absent (the `fluid.script` rule).
local function fluidProps(fc)
    local ok, props = TK.call(fc, "getProperties")
    if not ok or props == nil then return nil, "no FluidContainer:getProperties()" end
    local out, missing = {}, {}
    for k, m in pairs(FLUID_PROPS) do
        local okg, v = TK.call(props, m)
        if okg then out[k] = v else missing[#missing + 1] = m end
    end
    if #missing > 0 then out.missingGetters = missing end
    return out, nil
end

local function containerState(fc)
    local out = {}
    local ok, v = TK.call(fc, "getAmount");    if ok then out.amount = v end
    ok, v = TK.call(fc, "getCapacity");        if ok then out.capacity = v end
    ok, v = TK.call(fc, "getFilledRatio");     if ok then out.filledRatio = v end
    ok, v = TK.call(fc, "isEmpty");            if ok then out.empty = v end
    return out
end

-- BodyDamage.healthFromFoodTimer, which `DrinkFluid @254-@286 L5896-L5897` raises by
-- `(int)(timer + |consume.hungerChange| * 13000)`. A third, independent reading of the same
-- per-litre arithmetic -- and the one that shows the truncation.
local function foodTimerOf(p)
    local _, bd = TK.call(p, "getBodyDamage")
    if bd == nil then return nil end
    local ok, v = TK.call(bd, "getHealthFromFoodTimer")
    if ok then return v end
    return nil
end

-- Every instance of <fullType> in the inventory, with the fluid each holds. The one-argument
-- `getAllTypeRecurse` is the game's own route (`ISBuildUtil.lua:201`, on a full type).
local function fluidCandidates(p, fullType)
    local _, inv = TK.call(p, "getInventory")
    if inv == nil then return nil, "no IsoGameCharacter:getInventory()" end
    local ok, list = TK.call(inv, "getAllTypeRecurse", fullType)
    if not ok then return nil, "no ItemContainer:getAllTypeRecurse(String)" end
    if list == nil then return {}, nil end
    local okS, n = TK.call(list, "size")
    if not okS or type(n) ~= "number" then return nil, "no size() on the getAllTypeRecurse list" end
    local out = {}
    for i = 0, n - 1 do
        local okG, it = TK.call(list, "get", i)
        if okG and it ~= nil then
            local row = { index = i }
            local okI, id = TK.call(it, "getID");  if okI then row.id = id end
            -- getFluidContainer() is GameEntity's, inherited by InventoryItem (checked on the
            -- jar: it is NOT declared on InventoryItem itself), and is the accessor
            -- `ISDrinkFluidAction:new` uses.
            local _, fc = TK.call(it, "getFluidContainer")
            row.hasFluidContainer = fc ~= nil
            if fc ~= nil then
                local st = containerState(fc)
                row.amount, row.capacity, row.empty = st.amount, st.capacity, st.empty
            end
            out[#out + 1] = { item = it, fc = fc, row = row }
        end
    end
    return out, nil
end

-- Fullest, then highest id. A scan rather than table.sort, so the comparison is explicit and
-- an instance whose amount could not be read is never handed to `<`.
local function pickFullest(cands)
    local best = nil
    for i = 1, #cands do
        local c = cands[i]
        if c.fc ~= nil then
            if best == nil then
                best = c
            else
                local a, id = c.row.amount or -1, c.row.id or -1
                local ba, bid = best.row.amount or -1, best.row.id or -1
                if a > ba or (a == ba and id > bid) then best = c end
            end
        end
    end
    return best
end

TK.register("drink", function(argv)
    local user, fullType = argv[1], argv[2]
    if not user or not fullType then return "usage: drink <user> <fullType> [fraction]" end
    local f = 1.0
    if argv[3] ~= nil then
        f = tonumber(argv[3])
        if f == nil then return "expected a number for <fraction>, got " .. tostring(argv[3]) end
    end
    local p = findPlayer(user)
    if not p then return "no online player " .. tostring(user) end

    local cands, cerr = fluidCandidates(p, fullType)
    if cands == nil then return cerr end
    local finder = "getAllTypeRecurse"
    -- Belt and braces. `getAllTypeRecurse` is the game's own list route, but only
    -- `getFirstTypeRecurse` has been exercised against a full type by this harness
    -- (`item.get`, slice 02/05). If the list route answers nothing, fall back to the proven
    -- one rather than reporting an absent item -- and say which finder answered, because the
    -- fallback cannot see a second instance and its "fullest" guarantee is therefore void.
    if #cands == 0 then
        local _, inv = TK.call(p, "getInventory")
        local okF, it = TK.call(inv, "getFirstTypeRecurse", fullType)
        if okF and it ~= nil then
            local _, fc = TK.call(it, "getFluidContainer")
            local rowF = { index = 0, hasFluidContainer = fc ~= nil }
            local okI, id = TK.call(it, "getID");  if okI then rowF.id = id end
            if fc ~= nil then
                local st = containerState(fc)
                rowF.amount, rowF.capacity, rowF.empty = st.amount, st.capacity, st.empty
            end
            cands = { { item = it, fc = fc, row = rowF } }
            finder = "getFirstTypeRecurse (getAllTypeRecurse answered nothing)"
        end
    end
    local rows = {}
    for i = 1, #cands do rows[#rows + 1] = cands[i].row end
    if #cands == 0 then
        return "no " .. tostring(fullType) .. " in " .. tostring(user) .. "'s inventory"
    end
    local pick = pickFullest(cands)
    if pick == nil then
        return { error = "no FluidContainer on any of the " .. string.format("%.0f", #cands)
                         .. " " .. tostring(fullType) .. " instances", candidates = rows }
    end

    local out = { user = user, fullType = fullType, fraction = f, finder = finder,
                  selectionRule = "fullest, then highest id",
                  candidates = rows, selected = pick.row }
    local _, sft = TK.call(pick.item, "getFullType");  out.selectedFullType = sft
    local _, fluid = TK.call(pick.fc, "getPrimaryFluid")
    -- `fluidId` is the `fluid.script` route pair: getFluidTypeString() answers for only 34 of
    -- the 61 definitions, so it falls back to stringifying the FluidType enum and says which
    -- one named the fluid.
    local fid, froute = fluidId(fluid)
    out.primaryFluid, out.primaryFluidRoute = fid, froute
    local _, dn = TK.call(fluid, "getDisplayName");    out.fluidDisplayName = dn

    local props, perr = fluidProps(pick.fc)
    out.containerProperties = props
    if perr then out.containerPropertiesError = perr end
    if props then
        -- Nutrition: `n.setX(n.getX() + fc.getProperties().getX() * f)` (@23-@100
        -- L5878-L5881), i.e. the litres-weighted aggregate x f.
        out.predictedNutrition = { calories = (props.calories or 0) * f,
                                   carbs = (props.carbs or 0) * f,
                                   lipids = (props.lipids or 0) * f,
                                   proteins = (props.proteins or 0) * f }
        -- Stats: from the FluidConsume, which `removeFluid` weights by `getAmount() * f` and
        -- which DrinkFluid does NOT re-multiply by f (@129-@253 L5885-L5894). Since the
        -- aggregate above is weighted by that same `getAmount()`, the consume equals
        -- aggregate x f -- so the prediction is the same shape, and the whole claim is that
        -- these two numbers come out of one `f`.
        out.predictedStats = { hunger = (props.hungerChange or 0) * f,
                               thirst = (props.thirstChange or 0) * f }
    end

    local gt = getGameTime()
    out.worldAgeBefore = gt:getWorldAgeHours()
    out.before = { container = containerState(pick.fc), nutrition = TK.nutritionSnapshot(p),
                   foodTimer = foodTimerOf(p) }
    if props and out.before.foodTimer ~= nil then
        -- (int)(timer + |hungerChange * f| * 13000): the cast truncates the WHOLE sum, so the
        -- prediction has to as well.
        out.predictedFoodTimer =
            math.floor(out.before.foodTimer + math.abs((props.hungerChange or 0) * f) * 13000.0)
    end

    -- The call. Route 1 is the shipped action's own overload; route 2 is the FluidContainer
    -- one. `pcall` wraps the CALL, not the lookup -- TK.call has already ruled out "tried to
    -- call nil", which pcall cannot catch -- so what is left is an argument/type mismatch
    -- inside Kahlua's overload dispatch. pcall catches that in the shape it takes here: a
    -- WRONG-TYPE but non-nil argument raises a catchable error. A NIL argument is the case it
    -- cannot catch, the same failure mode as the nil member above; `subject` is `pick.item` /
    -- `pick.fc`, both checked non-nil before either attempt, and `f` is a number by here, so
    -- the wrap covers what it can be asked to. The fallback is
    -- taken ONLY when route 1 cannot have applied anything: the member was absent, or it
    -- raised and left the container's amount untouched. Never after a partial application --
    -- a second call there would drink twice and the artifact would be a fiction.
    local amountBefore = out.before.container.amount
    local function attempt(subject, label)
        local ran, present, value = pcall(TK.call, p, "DrinkFluid", subject, f, false)
        if ran and present then return true, label, value, nil end
        local st = containerState(pick.fc)
        local applied = (amountBefore ~= nil) and (st.amount ~= nil) and (st.amount ~= amountBefore)
        return false, label, nil, { raised = (not ran) and tostring(present) or nil,
                                    memberAbsent = (ran and not present) or nil,
                                    appliedAnyway = applied }
    end

    local ok1, label1, ret1, err1 = attempt(pick.item, "IsoGameCharacter:DrinkFluid(InventoryItem, f, false)")
    if ok1 then
        out.route, out.drinkFluidReturned = label1, ret1
    else
        out.routeAttempts = { { route = label1, failure = err1 } }
        if err1.appliedAnyway then
            out.route = "none (route 1 raised AFTER changing the container -- not retried)"
            out.error = "DrinkFluid raised but the container moved: " .. tostring(err1.raised)
        else
            local ok2, label2, ret2, err2 =
                attempt(pick.fc, "IsoGameCharacter:DrinkFluid(FluidContainer, f, false)")
            if ok2 then
                out.route, out.drinkFluidReturned = label2, ret2
            else
                out.routeAttempts[2] = { route = label2, failure = err2 }
                out.route = "none"
                out.error = "no DrinkFluid overload accepted the arguments"
            end
        end
    end

    out.after = { container = containerState(pick.fc), nutrition = TK.nutritionSnapshot(p),
                  foodTimer = foodTimerOf(p) }
    out.worldAgeAfter = gt:getWorldAgeHours()

    -- The shipped action's own second half (`updateEat` :117). Not needed for the server-side
    -- reading -- it pushes the item's new fill to the client -- but it is part of the route,
    -- so it is made and reported rather than quietly skipped.
    -- Two keys: `TK.call` answers `(ok, value)`, and a single assignment kept only the ok flag,
    -- so the return value was reported as if it were the presence flag. `syncItemFields` stays
    -- the presence/ran flag it always was and `syncItemFieldsReturned` is the value (nil in
    -- 42.20.4 -- the member is void). Wrapped, because every measurement above is already
    -- complete: a raise here must cost this one key, not the reply that carries them.
    local okSync, ranSync, retSync = pcall(TK.call, pick.item, "syncItemFields")
    if okSync then
        out.syncItemFields, out.syncItemFieldsReturned = ranSync, retSync
    else
        out.syncItemFields = false
        out.syncItemFieldsError = tostring(ranSync)
    end

    local function d(a, b) if a == nil or b == nil then return nil end return b - a end
    local nb, na = out.before.nutrition, out.after.nutrition
    out.delta = { amount = d(out.before.container.amount, out.after.container.amount),
                  calories = d(nb.calories, na.calories), carbs = d(nb.carbs, na.carbs),
                  lipids = d(nb.lipids, na.lipids), proteins = d(nb.proteins, na.proteins),
                  hunger = d(nb.hunger, na.hunger), thirst = d(nb.thirst, na.thirst),
                  weight = d(nb.weight, na.weight),
                  foodTimer = d(out.before.foodTimer, out.after.foodTimer),
                  worldAgeHours = d(out.worldAgeBefore, out.worldAgeAfter) }
    return out
end)

-- `item.use <user> <fullType> <uses>` -- what a `craftRecipe` input line WITHOUT
-- `flags[ItemCount]` does to the food it consumes, with the crafting action taken off
-- (slice 06 task 4b; `.superpowers/sdd/06-recipes/q-itemcount-notes.md`, grade C throughout
-- until this command ran). The dataset's whole nutrition ledger rests on the chain below and
-- nothing had ever measured it.
--
--   CraftRecipeData.processDestroyAndUsedItems @453 L576
--       ItemUser.UseItem(item, true, false, ceil(remaining), keep, destroy)
--   ItemUser.UseItem @18 L34            used = Math.min(item.getCurrentUses(), count)
--                    @28-@41 L37-38     if (!keep) item.setCurrentUses(getCurrentUses() - used)
--                    @146 L53           replaceOnDeplete is behind `instanceof
--                                       DrainableComboItem` -- a Food never enters that arm
--                    @293 L73-74        sendItemStats(item) when uses REMAIN
--                    @272 L68-70        uses <= 0 && !isKeepOnDeplete() -> RemoveItem(item)
--   Food.setCurrentUses  @6      L2230  a `baseHunger == 0` branch sits ahead of the line
--                                       below, so an item with no hunger scale never reaches
--                                       consumeHunger (the same zero getMaxUses answers 1 for)
--                        @23-@35 L2228-L2233  n = max(0, n);
--                                             consumeHunger((getCurrentUses() - n) / 100f)
--   Food.consumeHunger   @0-@17  L2714-L2715  r = |a / hungChange|; multiplyFoodValues(1 - r)
--   Food.getCurrentUses  @14-@26 L2219-L2223  (int)|hungChange  * 100|
--   Food.getMaxUses      @11-@23 L2210-L2214  (int)|baseHunger * 100|
--
-- so `r = ((cur - n)/100) / |hungChange|`, and every field `multiplyFoodValues` touches
-- (hungChange, calories, carbohydrates, proteins, lipids, and the thirst/mood block) is scaled
-- by `1 - r`. `|hungChange| = cur/100` -- and with it `r = used/cur` -- holds EXACTLY only
-- while `|hungChange| * 100` is a whole number, i.e. on an item whose uses have never been
-- part-spent: `getCurrentUses()` truncates, so on a nibbled item `cur/100` is a hair under
-- `|hungChange|` and the real factor is a hair under `1 - used/cur`. `predictedFactor` below
-- is the readable `1 - used/cur`; the experiment recomputes `1 - amount/hungChange` at float32
-- width for its compare, which is the arithmetic the game runs. The denominator is
-- `currentUses`, NOT `maxUses` -- they are equal only while the item is whole, because
-- `multiplyFoodValues` moves `hungChange` (and with it `getCurrentUses()`) but never
-- `baseHunger` (and with it `getMaxUses()`). Both ints are in `before`, so a caller checks
-- that rather than assuming it.
--
-- SERVER-side for the same reason `drink` is: the server owns the item, and slice 02
-- measured that a client's copy is a stale mirror. No `sendItemStats` push is made here --
-- every reading in the reply is taken on this side, on the object this side holds.

-- `TK.itemState` plus the two INT accessors the reduction actually works in. itemState's own
-- `uses` is `getCurrentUsesFloat()` (= |hungChange| on a `Food`); `currentUses` is the int
-- `UseItem` subtracts from and `maxUses` the whole-item denominator, and once
-- `multiplyFoodValues` has moved `hungChange` neither is recoverable from the float alone.
-- Deliberately NOT added to `TK.ITEM_STATE`: slices 01/02/05 compare `item.get` replies field
-- by field and this command is the only caller that needs the ints.
local function useState(it)
    local st = TK.itemState(it)
    if st == nil then return nil end
    local ok, v = TK.call(it, "getCurrentUses");   if ok then st.currentUses = v end
    ok, v = TK.call(it, "getMaxUses");             if ok then st.maxUses = v end
    -- Absent member -> absent key, never `false`: after route 1 a depleted item is
    -- `RemoveItem`d, so "is it still in a container" is a measurement, not a formality.
    local okC, cont = TK.call(it, "getContainer"); if okC then st.inContainer = cont ~= nil end
    return st
end

-- The four uses columns one candidate row carries. The fluid column those rows also carry
-- (`hasFluidContainer`, false on every Food, set by `fluidCandidates`) is left in: it is the
-- reading that says these uses are the `Food` override's and not a drainable's.
local function useRow(it, row)
    local ok, v = TK.call(it, "getCurrentUses");   if ok then row.currentUses = v end
    ok, v = TK.call(it, "getMaxUses");             if ok then row.maxUses = v end
    ok, v = TK.call(it, "getCurrentUsesFloat");    if ok then row.usesFloat = v end
    ok, v = TK.call(it, "getHungChange");          if ok then row.hungChange = v end
    return row
end

-- The finder `drink` uses. `fluidCandidates` is the enumeration itself (`getAllTypeRecurse`,
-- the game's own list route) and the `getFirstTypeRecurse` fallback below is `drink`'s own
-- belt and braces, for the same reason: only the first-match route has been exercised against
-- a full type by this harness (`item.get`), so an empty list falls back to it rather than
-- reporting an absent item -- and the reply says which finder answered, because the fallback
-- cannot see a second instance and its "most uses" guarantee is therefore void.
--
-- Returns `(cands, finder, err)`, and `cands == nil` is the FAILED enumeration -- distinct
-- from an empty list, which is a successfully-read empty inventory. Callers must not let the
-- two look alike: `candidatesAfter` being empty is how the reply says a depleted item was
-- removed.
local function useCandidates(p, fullType)
    local cands, cerr = fluidCandidates(p, fullType)
    if cands == nil then return nil, nil, cerr end
    local finder = "getAllTypeRecurse"
    if #cands == 0 then
        local _, inv = TK.call(p, "getInventory")
        local okF, it = TK.call(inv, "getFirstTypeRecurse", fullType)
        if okF and it ~= nil then
            local row = { index = 0 }
            local okI, id = TK.call(it, "getID");  if okI then row.id = id end
            local _, fc = TK.call(it, "getFluidContainer")
            row.hasFluidContainer = fc ~= nil
            cands = { { item = it, fc = fc, row = row } }
            finder = "getFirstTypeRecurse (getAllTypeRecurse answered nothing)"
        end
    end
    for i = 1, #cands do useRow(cands[i].item, cands[i].row) end
    return cands, finder, nil
end

-- `pickFullest`'s rule with `getCurrentUses()` in place of the container's amount: most uses,
-- then highest id (the newest). A scan rather than table.sort, so an instance whose uses could
-- not be read is never handed to `<`.
local function pickMostUses(cands)
    local best = nil
    for i = 1, #cands do
        local c = cands[i]
        if c.row.currentUses ~= nil then
            if best == nil then
                best = c
            else
                local u, id = c.row.currentUses, c.row.id or -1
                local bu, bid = best.row.currentUses, best.row.id or -1
                if u > bu or (u == bu and id > bid) then best = c end
            end
        end
    end
    return best
end

TK.register("item.use", function(argv)
    local user, fullType = argv[1], argv[2]
    if not user or not fullType or argv[3] == nil then
        return "usage: item.use <user> <fullType> <uses>"
    end
    local uses = tonumber(argv[3])
    if uses == nil then return "expected a number for <uses>, got " .. tostring(argv[3]) end
    uses = math.floor(uses)                      -- UseItem's `count` is an int
    if uses < 0 then return "expected <uses> >= 0, got " .. string.format("%.0f", uses) end
    local p = findPlayer(user)
    if not p then return "no online player " .. tostring(user) end

    local cands, finder, cerr = useCandidates(p, fullType)
    if cands == nil then return cerr end
    local rows = {}
    for i = 1, #cands do rows[#rows + 1] = cands[i].row end
    if #cands == 0 then
        return "no " .. tostring(fullType) .. " in " .. tostring(user) .. "'s inventory"
    end
    local pick = pickMostUses(cands)
    if pick == nil then
        return { error = "no getCurrentUses() on any of the " .. string.format("%.0f", #cands)
                         .. " " .. tostring(fullType) .. " instances",
                 finder = finder, candidates = rows }
    end
    local it = pick.item

    local out = { user = user, fullType = fullType, requestedUses = uses, finder = finder,
                  selectionRule = "most currentUses, then highest id",
                  candidates = rows, selected = pick.row }
    local okT, sft = TK.call(it, "getFullType");        if okT then out.selectedFullType = sft end
    local okD, dis = TK.call(it, "isDisappearOnUse");   if okD then out.disappearOnUse = dis end
    local okK, kod = TK.call(it, "isKeepOnDeplete");    if okK then out.keepOnDeplete = kod end

    local gt = getGameTime()
    out.worldAgeBefore = gt:getWorldAgeHours()
    out.before = useState(it)
    if out.before == nil then
        out.error = "no item state for " .. tostring(fullType)
        return out
    end
    local cur = out.before.currentUses
    if cur == nil then
        out.error = "no InventoryItem:getCurrentUses() on the selected instance"
        return out
    end
    -- REFUSED, not applied: on an already-depleted `Food` the chain divides by zero. `cur == 0`
    -- means `|hungChange|` has already been scaled to 0 (`getCurrentUses` is
    -- `(int)|hungChange * 100|`), so `setCurrentUses(0)` reaches
    -- `consumeHunger((0 - 0) / 100f)` and `Food.consumeHunger @0-@17 L2714-L2715` computes
    -- `r = |0 / 0|` = NaN, then `multiplyFoodValues(1 - NaN)` writes NaN into hungChange,
    -- calories, carbohydrates, proteins, lipids and the mood block. The item would be
    -- unreadable afterwards and the run would have destroyed its own evidence, so the command
    -- answers with the `before` snapshot it already took and changes nothing.
    if cur == 0 then
        out.error = "the selected " .. tostring(fullType) .. " has 0 uses left; refusing: "
                    .. "Food.consumeHunger would divide by a zero hungChange and write NaN "
                    .. "into every macro (@0-@17 L2714-L2715). Nothing was applied."
        out.route = "none (refused: currentUses == 0)"
        return out
    end
    -- `used = Math.min(item.getCurrentUses(), count)` -- UseItem @18 L34.
    local used = uses
    if cur < used then used = cur end
    out.usedUses, out.targetUses = used, cur - used

    -- The rule's own prediction, next to the reading (`drink`'s `predictedNutrition` shape).
    -- Computed in Lua doubles while the game computes it in float32, so it is the READABLE
    -- version -- the experiment recomputes the same chain at float32 width for its compare.
    local factor = 1.0 - (used / cur)            -- cur > 0 is guaranteed by the guard above
    out.predictedFactor = factor
    out.predictedFactorBasis =
        "multiplyFoodValues(1 - used/currentUses), via Food.setCurrentUses -> consumeHunger; "
        .. "equal to 1 - used/maxUses only while the item is whole, and equal to the game's "
        .. "own 1 - amount/hungChange only while |hungChange| * 100 is a whole number"
    -- `thirstChange` is NOT predicted here. `multiplyFoodValues @42 L2292` scales
    -- `getThirstChangeUnmodified()`, while `TK.ITEM_STATE.thirstChange` reads the MODIFIED
    -- getter -- the two are different numbers, so a prediction built from the modified one
    -- would be wrong wherever the modifiers bite, and right only by accident where they do
    -- not. `before.thirstChange` / `after.thirstChange` are still in the reply, recorded and
    -- uncompared.
    local pred, PRED = {}, { "hungChange", "calories", "carbs", "lipids", "proteins" }
    for i = 1, #PRED do
        local b = out.before[PRED[i]]
        if b ~= nil then pred[PRED[i]] = b * factor end
    end
    out.predicted = pred

    -- Route 1 -- the crafting path's own entry: the static
    -- `zombie/inventory/ItemUser.UseItem(InventoryItem,ZZIZZ)I` = (item, p1, p2, count, keep,
    -- destroy), confirmed on the 42.20.4 jar. `p1 = true` is what
    -- `processDestroyAndUsedItems @453 L576` passes and is what gets past the
    -- `!isDisappearOnUse() && !p1 && !destroy -> return 0` guard at `@0 L30-31`; `keep = false`
    -- is the consuming case (`mode:keep` skips the reduction entirely) and `destroy = false`
    -- so the item goes only when its uses reach 0.
    --
    -- A STATIC, so it is called `ItemUser.UseItem(item, ...)` with no self and NOT through
    -- TK.call, which would hand the class table in as a seventh argument. Presence is still
    -- established by INDEXING first (`_G["ItemUser"]`, then `.UseItem`), because "tried to
    -- call nil" escapes pcall -- see TK.call; the pcall then covers what is left, an
    -- argument/type mismatch inside Kahlua's overload dispatch.
    --
    -- READ OFF THE JAR before this command was written: `LuaManager$Exposer.shouldExpose
    -- @6-@14 L2833` is a strict `HashSet.contains` over the ~1000 classes `exposeAll()`
    -- registers, and `zombie/inventory/ItemUser` is not one of them (`InventoryItem`,
    -- `ItemContainer`, `ItemPickerJava` and `ItemSpawner` are). So this route is expected to
    -- be ABSENT on 42.20.4 and route 2 is the real one. It is attempted anyway, and reported,
    -- so a build that does expose it is taken automatically and the claim stays checkable.
    local attempts, applied = {}, false
    -- `_G and _G[...]` is `TK.setPerk`'s `Perks and Perks[name]` shape: an undefined global
    -- reads as nil, and the guard means a build without `_G` costs this route rather than the
    -- whole reply.
    local cls = _G and _G["ItemUser"] or nil
    local fn = nil
    if cls ~= nil then fn = cls.UseItem end
    if fn ~= nil then
        local ran, ret = pcall(fn, it, true, false, used, false, false)
        if ran then
            out.route = "ItemUser.UseItem(item, true, false, " .. string.format("%.0f", used)
                        .. ", false, false)"
            out.useItemReturned = ret        -- UseItem returns `used` (@303 L77)
            applied = true
        else
            -- Same rule as `drink`: never retry after a raise that already moved the item.
            local okNow, curNow = TK.call(it, "getCurrentUses")
            local moved = okNow and curNow ~= nil and curNow ~= cur
            attempts[#attempts + 1] = { route = "ItemUser.UseItem", raised = tostring(ret),
                                        appliedAnyway = moved }
            if moved then
                applied = true
                out.route = "none (route 1 raised AFTER changing the item -- not retried)"
                out.error = "ItemUser.UseItem raised but the uses moved: " .. tostring(ret)
            end
        end
    else
        attempts[#attempts + 1] = { route = "ItemUser.UseItem", memberAbsent = true,
            detail = (cls == nil)
                     and "no global ItemUser (not in LuaManager$Exposer.exposeAll)"
                     or "the global ItemUser has no UseItem" }
    end

    -- Route 2 -- `item:setCurrentUses(currentUses - used)`: literally the line UseItem runs
    -- (`@28-@41 L37-38`), and the notes' whole point is that crafting reaches hunger ONLY
    -- through this polymorphic setter -- a jar-wide grep puts no `setHungChange` /
    -- `consumeHunger` / `multiplyFoodValues` call anywhere in the crafting packages. What it
    -- does not do is UseItem's bookkeeping AFTER the reduction, which for a `Food` is exactly
    -- three things: the `replaceOnUse` spawn, `sendItemStats(item)` when uses REMAIN
    -- (`@293 L73-74`), and `getCurrentUses() <= 0 && !isKeepOnDeplete() -> RemoveItem(item)`
    -- (`@272 L68-70`). It is NOT `replaceOnDeplete`: that arm is behind
    -- `instanceof DrainableComboItem` (`@146 L53`) and a `Food` never reaches it. None of the
    -- three moves a nutrition field, so the measurement is unaffected -- and the skipped
    -- `sendItemStats` is a client PUSH, which this command deliberately does not make either
    -- way (every reading here is server-side, on the object the server holds). But a fully
    -- consumed item stays in the inventory on this route where the crafting code would have
    -- removed it, and `after.inContainer` / `candidatesAfter` are what say which happened
    -- rather than leaving it to be inferred.
    if not applied then
        local ran, present = pcall(TK.call, it, "setCurrentUses", out.targetUses)
        if ran and present then
            out.route = "item:setCurrentUses(" .. string.format("%.0f", out.targetUses)
                        .. ")  [= ItemUser.UseItem @28 L37-38, without its RemoveItem]"
            applied = true
        else
            attempts[#attempts + 1] = { route = "InventoryItem:setCurrentUses(int)",
                raised = (not ran) and tostring(present) or nil,
                memberAbsent = (ran and not present) or nil }
        end
    end
    if #attempts > 0 then out.routeAttempts = attempts end
    if not applied then
        out.route = "none"
        out.error = "no route reduced the item's uses"
    end

    out.after = useState(it)
    out.worldAgeAfter = gt:getWorldAgeHours()
    -- The inventory re-enumerated after the call. A depleted item is `RemoveItem`d on route 1
    -- and is not on route 2, so this is the direct reading of that, not an inference.
    --
    -- The enumeration's own error is captured: an empty `candidatesAfter` is how a caller
    -- reads "the item was removed", and a FAILED enumeration also leaves it empty. Left
    -- uncaptured the two would be indistinguishable and a wedged inventory read would be
    -- reported as a successful depletion (the slice-05 `fluidDefsError` rule).
    local cAfter, _finderAfter, cAfterErr = useCandidates(p, fullType)
    local rowsAfter = {}
    if cAfter == nil then
        out.candidatesAfterError = cAfterErr or "useCandidates answered no list and no error"
    else
        for i = 1, #cAfter do rowsAfter[#rowsAfter + 1] = cAfter[i].row end
    end
    out.candidatesAfter = rowsAfter

    local function d(a, b) if a == nil or b == nil then return nil end return b - a end
    local bs, as = out.before, out.after or {}
    out.delta = { currentUses = d(bs.currentUses, as.currentUses),
                  maxUses = d(bs.maxUses, as.maxUses), uses = d(bs.uses, as.uses),
                  hungChange = d(bs.hungChange, as.hungChange),
                  hungerChange = d(bs.hungerChange, as.hungerChange),
                  baseHunger = d(bs.baseHunger, as.baseHunger),
                  calories = d(bs.calories, as.calories), carbs = d(bs.carbs, as.carbs),
                  lipids = d(bs.lipids, as.lipids), proteins = d(bs.proteins, as.proteins),
                  thirstChange = d(bs.thirstChange, as.thirstChange),
                  worldAgeHours = d(out.worldAgeBefore, out.worldAgeAfter) }
    return out
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
