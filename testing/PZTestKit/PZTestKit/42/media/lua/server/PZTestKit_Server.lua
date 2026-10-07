-- PZTestKit server side: command bus polling + authoritative "witness" replies (S6).
if not isServer() then return end

-- @args [<multiplier>]
-- @reply string
-- @purpose Sets the server's game-time multiplier and reports the value read back; the server-only fallback for settimespeed.
TK.register("time.multiplier", function(argv)
    -- server-only fallback; the admin command (settimespeed) also broadcasts to clients
    getGameTime():setMultiplier(tonumber(argv[1]) or 1)
    return "mult=" .. tostring(getGameTime():getMultiplier())
end)

-- @args (none)
-- @reply [<username>, ...] every online player's username ({} when none are online)
-- @purpose Lists the usernames the server currently has online.
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

-- @args <user>
-- @reply {calories, carbs, lipids, proteins, weight, hunger, thirst, statsApi, incWeight, incWeightLot, decWeight} | string
-- @purpose Server-side read of one named online player's Nutrition block -- the authoritative half of the client twin.
TK.register("nutrition.get", function(argv)
    local p = findPlayer(argv[1])
    if not p then return "no online player " .. tostring(argv[1]) end
    return TK.nutritionSnapshot(p)
end)

-- @args <user> <calories|carbs|lipids|proteins|weight> <value>
-- @reply {calories, carbs, lipids, proteins, weight, hunger, thirst, statsApi, incWeight, incWeightLot, decWeight} | string
-- @purpose Server-side write of one Nutrition field on a named player; the reply is the post-write snapshot.
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
-- @args <user> <hunger|thirst|fatigue|endurance> <value> [<field> <value> ...]
-- @reply {calories, carbs, lipids, proteins, weight, hunger, thirst, statsApi, incWeight, incWeightLot, decWeight, applied} | string
-- @purpose Server-side write of one or more hunger/thirst/fatigue/endurance stats on a named player; applied names the route each field took.
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
-- @args <user> <PerkName> <level>
-- @reply {perk, requested, side, before, setPerkLevelDebug, afterSetPerkLevelDebug, setXPToLevel, after, route} | {error} | string
-- @purpose Authoritative server-side write of a perk level (setPerkLevelDebug plus getXp():setXPToLevel), with the read-back that says which route held.
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
-- @args <user> <PerkName>
-- @reply {perk, user, side, xp, level, serverWorldAge [, error]} | {error, perk} | string
-- @purpose Server-side read of a named player's raw perk XP beside the level -- the XP number perk.set never had.
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

-- ---- player modData (slice 10) -----------------------------------------------
-- <user> <key> <value>. The SERVER twin of the client's `moddata.set`
-- (`client/PZTestKit_Client.lua:86-89`), and the only way to plant a player-modData key the
-- CLIENT's copy does not have. That asymmetry is the whole point: pass 1 measured the player
-- census as server 4 keys / client 5 (the four vanilla fitness keys, plus `hotbar` on the
-- client), so the client is a strict superset and the difference set that would expose
-- `KahluaTableImpl.load`'s wipe-before-rawset on the receiving side is empty without this
-- command. Plant a key here, have the client `moddata.transmit`, and a server census that has
-- LOST the planted key is the wipe, measured rather than read off the jar.
--
-- Jar-confirmed on 42.20.4: `zombie/iso/IsoObject.getModData()Lse/krka/kahlua/vm/KahluaTable;`
-- (inherited by IsoPlayer) -- no new Java surface; `transmitModData()V` is on the same class.
-- The write is a plain assignment, exactly like the client's shipped command: a KahluaTableImpl
-- carries no metatable, so `md[k] = v` IS a raw set, and `rawset` is a global this build's Lua
-- never uses anywhere (0 hits in the game's own media/lua), which would make an absent one a
-- "tried to call nil" on the server -- index-first guard: a caught nil call is silent and
-- names nothing; an unguarded raise aborts the rest of this handler (x126/x127) -- see
-- docs/modding/lua-api.md section 5.
-- The VALUE is always a string (`argv[3]`, the bus splits on %S+), like the client's -- see
-- docs/testing/README.md. There is no delete: writing nil through this path cannot be told from
-- a missing argument, and nothing needs it.
-- @args <user> <key> <value>
-- @reply {user, key, value, side, keyCount, keys, serverWorldAge} | string
-- @purpose Server-side write of one string key into a named player's modData, answering with the resulting key census.
TK.register("moddata.set", function(argv)
    local p = findPlayer(argv[1])
    if not p then return "no online player " .. tostring(argv[1]) end
    if argv[2] == nil or argv[3] == nil then return "usage: moddata.set <user> <key> <value>" end
    local ok, md = TK.call(p, "getModData")
    if not ok then return "no getModData() on " .. tostring(argv[1]) end
    if type(md) ~= "table" then return "modData is a " .. type(md) .. ", not a table" end
    md[argv[2]] = argv[3]
    local keys = {}
    for k in pairs(md) do keys[#keys + 1] = tostring(k) end
    table.sort(keys)
    return { user = tostring(argv[1]), key = argv[2], value = argv[3], side = TK.side,
             keyCount = #keys, keys = keys, serverWorldAge = getGameTime():getWorldAgeHours() }
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
-- @args <user>
-- @reply {calories, carbs, lipids, proteins, weight, hunger, thirst, statsApi, incWeight, incWeightLot, decWeight, endurance, fatigue, moodles, traits, traitList, traitRoute, maxWeight, foodTimer, standardFoodTime, asleep, running, sprinting, moving, worldAge, mult, wall} | string
-- @purpose One atomic server-side body snapshot of a named player -- stats, moodles, nutrition, traits and the world clock in a single tick.
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
-- @args <option> [<number>|true|false]
-- @reply {option, side, before, type, sandboxVarsBefore, statsDecreaseMultiplierBefore [, requested] [, route] [, setError] [, setValueError] [, error], after, sandboxVarsAfter, statsDecreaseMultiplierAfter} | string
-- @purpose Reads or flips one sandbox option in the live server config -- unlike the client twin this write is the running config -- and brackets it with the statsDecrease multiplier.
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
        -- pcall wraps the CALL, not the lookup: TK.call has already ruled out "call nil" --
        -- index-first guard: a caught nil call is silent and names nothing; an unguarded raise
        -- aborts the rest of this handler (x126/x127) -- see docs/modding/lua-api.md section 5.
        -- What is left is an argument/type mismatch inside SandboxOptions:set, which pcall does
        -- catch and which must fall through to the per-option setter rather than kill the ack.
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
-- is nil: an arity or overload mismatch raises and pcall catches it (lua-api.md section 5
-- row 2); the guard keeps the reply informative.
-- Accepts either spelling: "HeartyAppetite" (the registered string) or "HEARTY_APPETITE" (the
-- static field). The read-back is TK.traitNames, not hasTrait: `hasTrait` is called with a
-- CharacterTrait throughout the game's own Lua, so the string it would need here is exactly
-- that trap -- an arity or overload mismatch raises and pcall catches it (lua-api.md section 5
-- row 2); the guard keeps the reply informative. Note the arg parser splits on whitespace, so
-- "Very Underweight" is not addressable through this command -- it is not needed either, the
-- band traits are driven by weight and read back through the same trait list.
local TRAIT_FIELDS = { HeartyAppetite = "HEARTY_APPETITE", LightEater = "LIGHT_EATER",
                       HighThirst = "HIGH_THIRST", LowThirst = "LOW_THIRST",
                       Obese = "OBESE", Overweight = "OVERWEIGHT", Underweight = "UNDERWEIGHT",
                       Emaciated = "EMACIATED" }

-- @args <user> <TraitName> <add|remove>
-- @reply {trait, field, op, before, enumFound, collection, route [, callError] [, error], after, traitList, held} | string
-- @purpose Adds or removes one CharacterTrait on a named player from the server, with a trait-list read-back in held.
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
-- @args <user> <true|false>
-- @reply {requested, before, setAsleep [, error], after, held} | string
-- @purpose Sets a named player's asleep flag on the server and reads it back -- the flag that picks the sleeping stat and calorie branches.
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
-- @args <user>
-- @reply {weight [, error], applied, traits, traitList} | string
-- @purpose Runs Nutrition.applyTraitFromWeight() on demand for a named player on the server and reports the weight-band traits that resulted.
TK.register("nutrition.applytraits", function(argv)
    local p = findPlayer(argv[1])
    if not p then return "no online player " .. tostring(argv[1]) end
    -- Guarded like every other accessor here: a raw `p:getNutrition():getWeight()` on a build
    -- that moved either method is a "tried to call nil" -- index-first guard: a caught nil call
    -- is silent and names nothing; an unguarded raise aborts the rest of this handler
    -- (x126/x127) -- see docs/modding/lua-api.md section 5. The guard is what lets this command
    -- answer the bus with a usable error instead.
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
-- @args <user> <value>
-- @reply {requested, before, set [, error], after} | string
-- @purpose Writes BodyDamage.healthFromFoodTimer on a named player from the server, with a before/after read-back.
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

-- @args <user> <fullType>
-- @reply {fullType, cooked, burnt, rotten, frozen, age, hungChange, baseHunger, calories, carbs, lipids, proteins, id, uses, fresh, offAge, offAgeMax, freezingTime, cookingTime, heat, minutesToCook, minutesToBurn, thirstChange, hungerChange, isCookable, actualWeight, weight, customWeight, lastCookMinute, serverWorldAge} | string
-- @purpose Server-side read of one inventory item's whole state -- the side that owns aging and cooking, so the only real reading of either.
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

-- @args <user> <fullType> <age|burnt|calories|chef|cooked|cookingTime|freezingTime|heat|hungChange|lastCookMinute|offAge|offAgeMax> <value>
-- @reply {fullType, cooked, burnt, rotten, frozen, age, hungChange, baseHunger, calories, carbs, lipids, proteins, id, uses, fresh, offAge, offAgeMax, freezingTime, cookingTime, heat, minutesToCook, minutesToBurn, thirstChange, hungerChange, isCookable, actualWeight, weight, customWeight, lastCookMinute, field, requested, before, sync, gameMinute, serverWorldAge} | string
-- @purpose Server-side write of one Food/InventoryItem field followed by sendItemStats; the reply pairs the before and after states.
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
    -- The cook block's gate value, beside the world age that was already here. `serverWorldAge`
    -- is hours-since-world-start; `getMinutes()` is the 0-59 clock minute Food.update @86
    -- actually compares against lastCookMinute, and slice 09's first session had to infer one
    -- from the other. `item.update` has carried it since slice 02 (see below); a sequence of
    -- item.set calls around a cook transition needs it on every step, not only on the witness.
    out.gameMinute = getGameTime():getMinutes()
    out.serverWorldAge = getGameTime():getWorldAgeHours()
    return out
end)

-- One aging step on demand: Food.updateAge(true). The `true` is the SYNC gate, not the age
-- gate -- it is what makes the server call sendItemStats afterwards (Q2). Whether that packet
-- carries the new age to the client is the point of the MP phase.
-- @args <user> <fullType>
-- @reply {fullType, cooked, burnt, rotten, frozen, age, hungChange, baseHunger, calories, carbs, lipids, proteins, id, uses, fresh, offAge, offAgeMax, freezingTime, cookingTime, heat, minutesToCook, minutesToBurn, thirstChange, hungerChange, isCookable, actualWeight, weight, customWeight, lastCookMinute, before, dAge, serverWorldAge} | string
-- @purpose Runs one Food.updateAge(true) aging step on the server and reports the age delta it produced.
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
-- @args <user> <fullType>
-- @reply {fullType, cooked, burnt, rotten, frozen, age, hungChange, baseHunger, calories, carbs, lipids, proteins, id, uses, fresh, offAge, offAgeMax, freezingTime, cookingTime, heat, minutesToCook, minutesToBurn, thirstChange, hungerChange, isCookable, actualWeight, weight, customWeight, lastCookMinute, before} | string
-- @purpose Calls Food.freeze() on a server-side item -- the only write that makes frozen stick -- and pushes it with sendItemStats.
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
-- @args <user> <fullType>
-- @reply {fullType, cooked, burnt, rotten, frozen, age, hungChange, baseHunger, calories, carbs, lipids, proteins, id, uses, fresh, offAge, offAgeMax, freezingTime, cookingTime, heat, minutesToCook, minutesToBurn, thirstChange, hungerChange, isCookable, actualWeight, weight, customWeight, lastCookMinute, before, gameMinute, serverWorldAge} | string
-- @purpose Runs InventoryItem.update() -- the cooking driver -- on the server and reports the item state either side of it.
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

-- `getScriptManager` is checked for nil BEFORE it is called, so the poll handler answers the
-- bus with an error instead of raising -- index-first guard: a caught nil call is silent and
-- names nothing; an unguarded raise aborts the rest of this handler (x126/x127) -- see
-- docs/modding/lua-api.md section 5 (and TK.call in the core).
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

-- @args (none)
-- @reply {total, food, byType, foodByModule, fluidDefs [, fluidDefsError]} | string
-- @purpose Server-side census of every loaded script item bucketed by item type: the live cross-check for tools/food_scan.py.
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
-- @args <fullType>
-- @reply {fullType, via, side, access, HungerChange, ThirstChange, Calories, Carbohydrates, Lipids, Proteins, DaysFresh, DaysTotallyRotten, IsCookable, MinutesToCook, MinutesToBurn} | string
-- @purpose Server-side read of one script item's live property getters; script data loads per side and never syncs, so this is not the client's reading.
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
-- @args <fluidId>
-- @reply {fluidType, fluidTypeRoute, displayName, hasPropertiesSet, HungerChange, ThirstChange, Calories, Carbohydrates, Lipids, Proteins, FatigueChange, StressChange, UnhappyChange, Alcohol, FluReduction, PainReduction, EnduranceChange, FoodSicknessChange [, missingGetters]} | string
-- @purpose Server-side read of one fluid definition's live property getters: the drink-side cross-check for the scanned fluid data.
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

-- @args <user> <fullType> [<fraction>]
-- @reply {user, fullType, fraction, finder, selectionRule, candidates, selected, selectedFullType, primaryFluid, primaryFluidRoute, fluidDisplayName, containerProperties [, containerPropertiesError], predictedNutrition, predictedStats, worldAgeBefore, before [, predictedFoodTimer], route [, drinkFluidReturned] [, routeAttempts] [, error], after, worldAgeAfter, syncItemFields [, syncItemFieldsReturned] [, syncItemFieldsError], delta} | {error, candidates} | string
-- @purpose Makes one server-side DrinkFluid call -- the shipped drink action minus the timed action -- and reports the container, nutrition and food timer either side of it.
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
    -- call nil" -- index-first guard: a caught nil call is silent and names nothing; an
    -- unguarded raise aborts the rest of this handler (x126/x127) -- see
    -- docs/modding/lua-api.md section 5. What is left is an argument/type mismatch inside
    -- Kahlua's overload dispatch: an arity or overload mismatch raises and pcall catches it
    -- (lua-api.md section 5 row 2); the guard keeps the reply informative. A WRONG-TYPE but
    -- non-nil argument and a NIL into an overloaded member are both that same shape (the nil
    -- one is unmeasured, section 5 row 2); `subject` is `pick.item` / `pick.fc`, both checked
    -- non-nil before either attempt, and `f` is a number by here, so the wrap covers what it
    -- can be asked to. The fallback is
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

-- @args <user> <fullType> <uses>
-- @reply {user, fullType, requestedUses, finder, selectionRule, candidates, selected, selectedFullType, disappearOnUse, keepOnDeplete, worldAgeBefore, before, usedUses, targetUses, predictedFactor, predictedFactorBasis, predicted, route [, useItemReturned] [, routeAttempts] [, error], after, worldAgeAfter [, candidatesAfterError], candidatesAfter, delta} | {error, finder, candidates} | string
-- @purpose Consumes N uses of a food on the server the way a craftRecipe input line without flags[ItemCount] does, and reports the macro scaling either side of the reduction.
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
    -- established by INDEXING first (`_G["ItemUser"]`, then `.UseItem`) -- index-first guard:
    -- a caught nil call is silent and names nothing; an unguarded raise aborts the rest of this
    -- handler (x126/x127) -- see docs/modding/lua-api.md section 5. The pcall then covers what
    -- is left, an argument/type mismatch inside Kahlua's overload dispatch.
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

-- ---- Plan 1 Task 7 additions --------------------------------------------------
-- Appended after the file's trailing event registrations on purpose: the claims register holds
-- `repo:` pointers into this harness by line number, so new sites go at the end and no existing
-- line moves. Registration order does not matter -- TK.commands is read at poll time.

-- <user>. Every stat of the registry (docs/facts/character-stats.md#registry) for one named
-- player, read on the server, which owns the stats in MP; the shared body is TK.statsAll in the
-- core file. The client twin reads its own mirror.
-- @args <user>
-- @reply {side, user, worldAge, mult, wall, stats, missing [, error]} | string
-- @purpose Server-side read of all 24 registered CharacterStat values of a named player in one tick; a static this build lacks lands in missing.
TK.register("stats.all", function(argv)
    local p = findPlayer(argv[1])
    if not p then return "no online player " .. tostring(argv[1]) end
    return TK.statsAll(p)
end)

-- <user> [mask]. Sends the player-fields packet from the server: mask bit 2 is the trait block
-- (docs/platform/mp-model.md, #2595), the default here. `sendSyncPlayerFields` is a Lua GLOBAL,
-- so it takes the harness's nil-check-then-call idiom for globals rather than TK.call; the call
-- runs under pcall so an argument mismatch answers `callError` instead of killing the ack. The
-- global is server-gated and the server send returns SILENTLY for a null player or an online id
-- of -1 (#2602), so `sent` records only that the call ran -- never delivery; delivery is a
-- client-side read. `traitList` is the server's own list after the push and `held` says it is
-- the same list as before it (the push writes nothing on the sending side).
-- @args <user> [<mask>]
-- @reply {user, mask, wall, sent, traitList, held [, callError] [, error]} | string
-- @purpose Calls sendSyncPlayerFields(player, mask or 2) on the server for a named player -- the trait-block push -- and reads the server trait list back; sent is not delivery.
TK.register("trait.push", function(argv)
    local p = findPlayer(argv[1])
    if not p then return "no online player " .. tostring(argv[1]) end
    local mask = 2
    if argv[2] ~= nil then
        mask = tonumber(argv[2])
        if mask == nil or mask < 0 or mask ~= math.floor(mask) then
            return "usage: trait.push <user> [<mask>]"
        end
    end
    local _, beforeList = TK.traitNames(p)
    local out = { user = tostring(argv[1]), mask = mask, sent = false, wall = TK.now() }
    if sendSyncPlayerFields == nil then
        out.error = "no sendSyncPlayerFields global on this side"
    else
        local ran, err = pcall(sendSyncPlayerFields, p, mask)
        out.sent = ran
        if not ran then out.callError = tostring(err) end
    end
    local _, list = TK.traitNames(p)
    out.traitList = list
    local same = #list == #beforeList
    if same then
        for i = 1, #list do
            if list[i] ~= beforeList[i] then same = false; break end
        end
    end
    out.held = same
    return out
end)

-- <name> <key> <value>. One write into a GLOBAL modData table on the server, the store the mod's
-- persistence uses (ModData.getOrCreate). ModData's binding is a DOT call, so it goes through
-- TK.callStatic (index first, then call, no self). The table is created when absent -- that is
-- what getOrCreate does. The bus splits arguments on whitespace, so the value arrives as a
-- string; it is coerced true|false -> boolean, a number -> number, anything else stays a string,
-- the coercion the brief names for this command. Note: the player-scope `moddata.set` above
-- stores its value as the raw string; this command coerces because a mod's global table holds
-- numbers. There is no delete. The census is every top-level key, sorted.
-- @args <name> <key> <value>
-- @reply {name, key, value, keyCount, keys} | {name, error} | string
-- @purpose Server-side write of one coerced key (boolean, number or string) into a global ModData table, answering with the table's key census.
TK.register("globalmoddata.set", function(argv)
    local name, key, raw = argv[1], argv[2], argv[3]
    if name == nil or key == nil or raw == nil then
        return "usage: globalmoddata.set <name> <key> <value>"
    end
    local ok, t = TK.callStatic(ModData, "getOrCreate", name)
    if not ok then return { name = name, error = "no ModData.getOrCreate" } end
    if type(t) ~= "table" then return { name = name, error = "getOrCreate answered a " .. type(t) } end
    local value
    if raw == "true" or raw == "false" then value = (raw == "true")
    elseif tonumber(raw) ~= nil then value = tonumber(raw)
    else value = raw end
    t[key] = value
    local keys = {}
    for k in pairs(t) do keys[#keys + 1] = tostring(k) end
    table.sort(keys)
    return { name = name, key = key, value = value, keyCount = #keys, keys = keys }
end)

-- <name>. ModData.transmit(name) from the server -- the push of one global table to the
-- clients. Through TK.callStatic like the write above; `transmitted` records only that the
-- member existed and the call returned, never delivery.
-- @args <name>
-- @reply {name, transmitted [, error]} | string
-- @purpose Calls ModData.transmit(name) on the server for one global modData table; transmitted is that the call ran, not delivery.
TK.register("globalmoddata.transmit", function(argv)
    local name = argv[1]
    if name == nil then return "usage: globalmoddata.transmit <name>" end
    local ok = TK.callStatic(ModData, "transmit", name)
    local out = { name = name, transmitted = ok }
    if not ok then out.error = "no ModData.transmit" end
    return out
end)
TK.log("server harness Task 7 commands loaded")

TK.sleepHold = TK.sleepHold or {}

-- <user> <seconds>. Sets the asleep flag and RE-ASSERTS it on every server tick for a wall
-- window. Plan 1 read that one plain setAsleep(true) does not hold: the attached client resets
-- the flag (#2081, #2752). Whether a per-tick re-assert wins against that reset is THE
-- MEASUREMENT: the driver reads `stats.get <user>` asleep across the window. The closure is kept
-- in TK.sleepHold keyed by username so a second call replaces the first; `<seconds> 0` cancels
-- and removes it. The handler removes itself from Events.OnTick once TK.now() passes the deadline.
-- @args <user> <seconds>
-- @reply {user, seconds, before, after, armed, deadlineWall [, error]} | string
-- @purpose Sets a named player's asleep flag and re-asserts it every server tick for a wall window (0 cancels); whether the re-assert holds against the client's reset is the measurement.
TK.register("player.sleep.hold", function(argv)
    local user = argv[1]
    local p = findPlayer(user)
    if not p then return "no online player " .. tostring(user) end
    local seconds = tonumber(argv[2])
    if seconds == nil or seconds < 0 or seconds > 600 then
        return "usage: player.sleep.hold <user> <seconds>  (0 cancels; <= 600)"
    end
    local out = { user = tostring(user), seconds = seconds, armed = false }
    local prior = TK.sleepHold[user]
    if prior ~= nil then
        if Events ~= nil and Events.OnTick ~= nil then Events.OnTick.Remove(prior) end
        TK.sleepHold[user] = nil
    end
    local _, before = TK.call(p, "isAsleep")
    out.before = before
    if seconds == 0 then
        out.after = before
        return out
    end
    if Events == nil or Events.OnTick == nil then
        out.error = "no Events.OnTick on this side"
        return out
    end
    if not TK.call(p, "setAsleep", true) then out.error = "no IsoGameCharacter:setAsleep" end
    local _, after = TK.call(p, "isAsleep")
    out.after = after
    local deadline = TK.now() + seconds * 1000
    out.deadlineWall = deadline
    local closure
    closure = function()
        local who = findPlayer(user)
        if who ~= nil then TK.call(who, "setAsleep", true) end
        if TK.now() >= deadline then
            Events.OnTick.Remove(closure)
            if TK.sleepHold[user] == closure then TK.sleepHold[user] = nil end
        end
    end
    TK.sleepHold[user] = closure
    Events.OnTick.Add(closure)
    out.armed = true
    return out
end)

-- <user> <TraitName>. The same-tick add-and-push (X4's push arm, #2099): inside ONE handler, so
-- one server tick, it stamps wallBefore, adds the trait by the route trait.set's add uses
-- (getCharacterTraits():add(CharacterTrait.<field>)), calls sendSyncPlayerFields(player, 2) by the
-- call trait.push makes, and stamps wallAfter. The client's `trait.watch` first-sight stamp minus
-- wallAfter is then the push's latency, separable from any experience-driven route. `sent` is that
-- the call ran, never delivery.
-- @args <user> <TraitName>
-- @reply {user, trait, added, sent, wallBefore, wallAfter, traitList [, callError] [, error]} | string
-- @purpose Adds one CharacterTrait and calls sendSyncPlayerFields(player, 2) in the same server tick, stamping the wall clock either side; the client-side trait.watch stamp then gives the push latency. `added` says only that the add call did not raise; grade presence on `traitList`.
TK.register("trait.add.push", function(argv)
    local p = findPlayer(argv[1])
    if not p then return "no online player " .. tostring(argv[1]) end
    local name = argv[2]
    if name == nil then return "usage: trait.add.push <user> <TraitName>" end
    local field = TRAIT_FIELDS[name] or name
    local out = { user = tostring(argv[1]), trait = name, added = false, sent = false }
    out.wallBefore = TK.now()
    local enum = CharacterTrait and CharacterTrait[field]
    local _, coll = TK.call(p, "getCharacterTraits")
    if coll ~= nil and enum ~= nil then
        local ran, present = pcall(TK.call, coll, "add", enum)
        out.added = ran and present == true
        if not ran then out.callError = tostring(present) end
    else
        out.error = (coll == nil and "no IsoGameCharacter:getCharacterTraits" or
                     "no CharacterTrait." .. tostring(field))
    end
    if sendSyncPlayerFields == nil then
        out.error = out.error or "no sendSyncPlayerFields global on this side"
    else
        local ran, err = pcall(sendSyncPlayerFields, p, 2)
        out.sent = ran
        if not ran then out.callError = tostring(err) end
    end
    out.wallAfter = TK.now()
    local _, list = TK.traitNames(p)
    out.traitList = list
    return out
end)

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

-- <user> <getter1[(arg)]>.<getter2[(arg)]>... Walks a chain of zero- or one-literal-argument
-- getters from the player, every hop index-first (#0935): `local f = obj[name]; if f == nil
-- then fail; obj = f(obj, arg)`, a colon call written as a dot call with the receiver first,
-- under a pcall so a hop that throws names its index instead of aborting the handler. The
-- chain is split on dots OUTSIDE parentheses, so `getXp.getXP(Perks.Strength)` is two hops. A
-- literal argument is `Perks.<Name>` (the perk object), a number (a number) or else a string.
-- The end value: a number, boolean or string is tostring'd; a Lua table is walked ONE level
-- into string values; anything else (a Java object) is tostring'd, which names its class.
-- @args <user> <getter1[(arg)]>.<getter2>...
-- @reply {ok, value, hops, failedAt [, error] [, reason]} | string
-- @purpose Reads the value at the end of a dot-chain of zero- or one-literal-argument getters on a named player (index-first at every hop); the one command for reads the typed witnesses do not name, such as the thermoregulator's metabolic target.
TK.register("witness.chain", function(argv)
    local p = findPlayer(argv[1])
    if not p then return "no online player " .. tostring(argv[1]) end
    if argv[2] == nil then return "usage: witness.chain <user> <getter1[(arg)]>.<getter2>..." end
    return chainRead(p, argv[2])
end)

-- <user> <Perk> <level>. The level-only perk write the strength gate needs: `perk.set` writes the
-- level AND getXp():setXPToLevel, so it cannot say what the level setter alone does to the XP
-- (#2119: setPerkLevelDebug writes the level and nothing else; #2103: setXPToLevel is the XP
-- side). This calls setPerkLevelDebug and nothing else, then reads the level and the XP back in
-- the same tick, so a level that moved while the XP stayed is visible in one reply.
-- @args <user> <Perk> <level>
-- @reply {perk, requested, side, before, after, xp [, error]} | string
-- @purpose Writes a perk level through setPerkLevelDebug ONLY (no setXPToLevel) and reads the level and the raw XP back in the same tick.
TK.register("perk.level", function(argv)
    local p = findPlayer(argv[1])
    if not p then return "no online player " .. tostring(argv[1]) end
    local level = tonumber(argv[3])
    if not argv[2] or level == nil then return "usage: perk.level <user> <Perk> <level>" end
    local perk = Perks and Perks[argv[2]]
    if not perk then return { error = "no Perks." .. tostring(argv[2]), perk = argv[2] } end
    local out = { perk = argv[2], requested = level, side = TK.side }
    local _, before = TK.call(p, "getPerkLevel", perk)
    out.before = before
    local present = TK.call(p, "setPerkLevelDebug", perk, level)
    if not present then out.error = "no IsoGameCharacter:setPerkLevelDebug" end
    local _, after = TK.call(p, "getPerkLevel", perk)
    out.after = after
    local _, xpObj = TK.call(p, "getXp")
    local _, xp = TK.call(xpObj, "getXP", perk)
    out.xp = xp
    return out
end)

-- <user> <Perk> <amount>. A real server-side XP grant through the game's own Lua global
-- `addXp(player, perk, amount)`, which routes to GameServer.addXp when GameServer.server is set
-- (#2130) and there calls the six-argument XP.AddXP and then refreshes the anti-cheat's
-- experience snapshot (#2132). It is capability-gated inside the engine, so a grant the engine
-- refused is read off xpBefore against xpAfter, never off `ok` (which says only that the call
-- ran without raising).
-- @args <user> <Perk> <amount>
-- @reply {ok, perk, amount, side, xpBefore, xpAfter, levelBefore, levelAfter [, error]} | string
-- @purpose Grants XP through the server Lua global addXp (the checker-refreshing route) and reads XP and level either side of it in the same tick.
TK.register("xp.grant", function(argv)
    local p = findPlayer(argv[1])
    if not p then return "no online player " .. tostring(argv[1]) end
    local amount = tonumber(argv[3])
    if not argv[2] or amount == nil then return "usage: xp.grant <user> <Perk> <amount>" end
    local perk = Perks and Perks[argv[2]]
    if not perk then return { ok = false, error = "no Perks." .. tostring(argv[2]), perk = argv[2] } end
    local out = { ok = false, perk = argv[2], amount = amount, side = TK.side }
    local _, xpObj = TK.call(p, "getXp")
    local _, x0 = TK.call(xpObj, "getXP", perk)
    local _, l0 = TK.call(p, "getPerkLevel", perk)
    out.xpBefore = x0
    out.levelBefore = l0
    if addXp == nil then
        out.error = "no addXp global on this side"
    else
        local ran, err = pcall(addXp, p, perk, amount)
        out.ok = ran
        if not ran then out.error = tostring(err) end
    end
    local _, x1 = TK.call(xpObj, "getXP", perk)
    local _, l1 = TK.call(p, "getPerkLevel", perk)
    out.xpAfter = x1
    out.levelAfter = l1
    return out
end)

-- <user> <delta>. Writes the carry-capacity delta through IsoPlayer.setMaxWeightDelta (#2143:
-- public, no caller in the jar, re-read on every carry recompute). The recompute that turns the
-- new delta into getMaxWeight() lands on the next body-damage update, not in this call, so the
-- same-tick `maxWeight` is the OLD capacity and the driver re-reads it later.
-- @args <user> <delta>
-- @reply {side, before, after, maxWeight [, error]} | string
-- @purpose Writes the player's carry delta through setMaxWeightDelta and reads the delta and getMaxWeight() back; maxWeight moves only after the next recompute, so re-read it later.
TK.register("carry.set", function(argv)
    local p = findPlayer(argv[1])
    if not p then return "no online player " .. tostring(argv[1]) end
    local delta = tonumber(argv[2])
    if delta == nil then return "usage: carry.set <user> <delta>" end
    local out = { side = TK.side }
    local _, before = TK.call(p, "getMaxWeightDelta")
    out.before = before
    local present = TK.call(p, "setMaxWeightDelta", delta)
    if not present then out.error = "no IsoPlayer:setMaxWeightDelta" end
    local _, after = TK.call(p, "getMaxWeightDelta")
    out.after = after
    local _, mw = TK.call(p, "getMaxWeight")
    out.maxWeight = mw
    return out
end)

-- <user> <fullType> <count>. Server-side AddItems on the named player's inventory, then the
-- server's own inventory weight and carry capacity read in the same tick. Whether the CLIENT
-- ever sees the added items or the weight is the gate's measurement (the add is not sent to the
-- client by this call), so the reply records only the server side.
-- @args <user> <fullType> <count>
-- @reply {ok, fullType, count, side, invWeight, maxWeight [, error]} | string
-- @purpose Adds count items of a type to a named player's inventory on the server and reads getInventoryWeight() and getMaxWeight() the same tick; client visibility is read separately.
TK.register("inventory.add", function(argv)
    local p = findPlayer(argv[1])
    if not p then return "no online player " .. tostring(argv[1]) end
    local count = tonumber(argv[3])
    if not argv[2] or count == nil then return "usage: inventory.add <user> <fullType> <count>" end
    local out = { ok = false, fullType = argv[2], count = count, side = TK.side }
    local _, inv = TK.call(p, "getInventory")
    if inv == nil or inv["AddItems"] == nil then
        out.error = "no getInventory():AddItems"
        return out
    end
    local ran, err = pcall(inv["AddItems"], inv, argv[2], count)
    out.ok = ran
    if not ran then out.error = tostring(err) end
    local _, w = TK.call(p, "getInventoryWeight")
    local _, mw = TK.call(p, "getMaxWeight")
    out.invWeight = w
    out.maxWeight = mw
    return out
end)

-- ---- nested-table writes (close fix wave, Plan 3) --------------------------------------------
-- A literal arrives as a whitespace-split string: true|false -> boolean, a number -> number,
-- anything else stays a string (the coercion globalmoddata.set uses).
local function parseLiteral(raw)
    if raw == "true" then return true end
    if raw == "false" then return false end
    local n = tonumber(raw)
    if n ~= nil then return n end
    return raw
end

-- Walks a dot path from a Lua table WITHOUT creating anything: returns (parent, leafKey) with
-- parent the table holding the leaf, or (nil, nil, failedAt, reason) when a hop before the leaf
-- is absent or not a table. Pure Lua tables only, so there is no Java member to index first.
local function walkToLeaf(root, path)
    local segs = {}
    for seg in string.gmatch(path, "[^%.]+") do segs[#segs + 1] = seg end
    if #segs == 0 then return nil, nil, 0, "empty path" end
    local cur = root
    for i = 1, #segs - 1 do
        if type(cur) ~= "table" then return nil, nil, i, "not a table before hop " .. i end
        cur = cur[segs[i]]
        if cur == nil then return nil, nil, i, "no table at " .. segs[i] end
    end
    if type(cur) ~= "table" then return nil, nil, #segs, "not a table before the leaf" end
    return cur, segs[#segs]
end

-- <Section.Key> <value>. A live sandbox flip that REACHES SandboxVars: sandbox.set goes through
-- SandboxOptions:set and its sandboxVars read covers one level only, and a mod option such as
-- NR.LegacyMirror lives at SandboxVars.NR.LegacyMirror, a plain Lua table the mod re-reads every
-- game minute (#2460). This assigns that nested leaf directly on the server (the intermediate
-- tables must exist, none is created; the leaf may be new, `before` nil says so) and reads it back.
-- The value is parsed true|false -> boolean, a number -> number, else a string. When the
-- read-back does not equal the request the reply is `ok = false` with the reason -- never a
-- claim that a flip stuck. The write is server-local config: it is not sent to the clients.
-- @args <Section.Key> <value>
-- @reply {ok, path, requested, before, after [, failedAt] [, reason]} | string
-- @purpose Assigns a nested SandboxVars leaf (e.g. NR.LegacyMirror) on the server from a parsed literal and replies the read-back before and after; ok is false when a hop is missing or the read-back differs.
TK.register("sandbox.var", function(argv)
    local path, raw = argv[1], argv[2]
    if path == nil or raw == nil then return "usage: sandbox.var <Section.Key> <value>" end
    local out = { ok = false, path = path }
    if type(SandboxVars) ~= "table" then
        out.reason = "no SandboxVars table"
        return out
    end
    local parent, key, failedAt, why = walkToLeaf(SandboxVars, path)
    if parent == nil then
        out.failedAt = failedAt
        out.reason = why
        return out
    end
    local value = parseLiteral(raw)
    out.requested = value
    out.before = parent[key]
    local ran, err = pcall(function() parent[key] = value end)
    out.after = parent[key]
    if not ran then
        out.reason = "assignment raised: " .. tostring(err)
    elseif out.after ~= value then
        out.reason = "assignment did not stick"
    else
        out.ok = true
    end
    return out
end)

-- <table> <a.b.c> <value>. The record-edit instrument: edits one nested leaf of a global
-- ModData table (globalmoddata.set writes top-level keys only). The table is fetched with
-- ModData.getOrCreate only when ModData.exists says it is there (a typo never creates one), then
-- the dot path is walked creating NO table -- a missing or non-table intermediate replies
-- `ok = false` with failedAt, the 1-based segment. The leaf is assigned from a literal parsed
-- true|false -> boolean, a number -> number, else a string, and the reply carries the leaf
-- before and after. The write is server-side only; globalmoddata.transmit pushes it to clients.
-- @args <table> <a.b.c> <value>
-- @reply {ok, name, path, requested, before, after [, failedAt] [, reason]} | string
-- @purpose Assigns one nested leaf of an existing global ModData table at a dot path (no table is created; a missing hop replies ok=false with failedAt) and replies the leaf before and after.
TK.register("globalmoddata.setpath", function(argv)
    local name, path, raw = argv[1], argv[2], argv[3]
    if name == nil or path == nil or raw == nil then
        return "usage: globalmoddata.setpath <table> <a.b.c> <value>"
    end
    local out = { ok = false, name = name, path = path }
    local hasExists, exists = TK.callStatic(ModData, "exists", name)
    if not hasExists then
        out.reason = "no ModData.exists"
        return out
    end
    if exists ~= true then
        out.failedAt = 0
        out.reason = "no global modData table " .. name
        return out
    end
    local _, t = TK.callStatic(ModData, "getOrCreate", name)
    if type(t) ~= "table" then
        out.reason = "getOrCreate answered a " .. type(t)
        return out
    end
    local parent, key, failedAt, why = walkToLeaf(t, path)
    if parent == nil then
        out.failedAt = failedAt
        out.reason = why
        return out
    end
    local value = parseLiteral(raw)
    out.requested = value
    out.before = parent[key]
    parent[key] = value
    out.after = parent[key]
    out.ok = (out.after == value)
    if not out.ok then out.reason = "read-back differs" end
    return out
end)

-- <n>. Spawns n zombies within one tile of the first online player (the admin subject) through
-- the server's own spawner: the Lua global `addZombiesInOutfit(x, y, z, count, outfit,
-- femaleChance)` (LuaManager$GlobalObject, the entry the admin horde UI calls; its body runs
-- VirtualZombieManager.createRealZombieAlways on the IsoCell's square at x,y,z, so on the server
-- the zombie is server-owned -- the RCON `createhorde` lands too far). Each is placed on the
-- player's square offset by one tile (+1,0 then -1,0 alternating, so none lands further than a
-- tile). `spawned` is the returned list's size and `dists` each zombie's distance from the player
-- read back index-first. n is 1..10. An absent global or a raise replies ok=false with the reason.
-- @args <n>
-- @reply {ok, requested, spawned, at, dists [, reason]} | string
-- @purpose Spawns n (1..10) zombies on the squares one tile either side of the first online player through the server's addZombiesInOutfit global, replying how many appeared and their distances.
TK.register("zombie.near", function(argv)
    local n = tonumber(argv[1])
    if n == nil or n < 1 or n > 10 or n ~= math.floor(n) then return "usage: zombie.near <n>  (1 <= n <= 10)" end
    local out = { ok = false, requested = n, spawned = 0, dists = {} }
    if addZombiesInOutfit == nil then
        out.reason = "no addZombiesInOutfit global on this side"
        return out
    end
    local players = getOnlinePlayers and getOnlinePlayers() or nil
    local _, count = TK.call(players, "size")
    if count == nil or count < 1 then
        out.reason = "no online player"
        return out
    end
    local _, p = TK.call(players, "get", 0)
    local _, px = TK.call(p, "getX")
    local _, py = TK.call(p, "getY")
    local _, pz = TK.call(p, "getZ")
    if px == nil or py == nil or pz == nil then
        out.reason = "no player position"
        return out
    end
    local bx, by, bz = math.floor(px), math.floor(py), math.floor(pz)
    out.at = { x = bx, y = by, z = bz }
    local spawned = 0
    for i = 1, n do
        local dx = 1
        if i % 2 == 0 then dx = -1 end
        local ran, list = pcall(addZombiesInOutfit, bx + dx, by, bz, 1, nil, 50)
        if not ran then
            out.reason = "addZombiesInOutfit raised: " .. tostring(list)
            break
        end
        local _, made = TK.call(list, "size")
        local k = 0
        while made ~= nil and k < made do
            local _, z = TK.call(list, "get", k)
            local _, zx = TK.call(z, "getX")
            local _, zy = TK.call(z, "getY")
            if zx ~= nil and zy ~= nil then
                local ex, ey = zx - px, zy - py
                out.dists[#out.dists + 1] = math.floor(math.sqrt(ex * ex + ey * ey) * 100 + 0.5) / 100
            end
            spawned = spawned + 1
            k = k + 1
        end
    end
    out.spawned = spawned
    out.ok = (spawned == n)
    if not out.ok and out.reason == nil then out.reason = "spawned " .. spawned .. " of " .. n end
    return out
end)

-- ---- Plan 4 Task 3: the kinetics harness wave (server commands) -------------------------------

-- <user> <StatName> <value>. stats.set reaches only the four fields TK.STAT_FIELDS names; the
-- kinetics gates need INTOXICATION, POISON, FOOD_SICKNESS, SICKNESS, TEMPERATURE, WETNESS and
-- the rest of the CharacterStat enum. The name is resolved to the enum (CharacterStat[name], then
-- a pcall'd CharacterStat.valueOf(name)) so a bad name replies ok=false rather than raising, and
-- the value goes through Stats:set(enum, value) index-first; before and after are read through
-- Stats:get(enum), so a stat the server re-derives the same tick shows as after ~= requested.
-- @args <user> <StatName> <value>
-- @reply {ok, stat, side, requested, before, after [, reason]} | string
-- @purpose Server-side write of any CharacterStat by enum name on a named player, replying the value read before and after the write.
TK.register("stats.setany", function(argv)
    local p = findPlayer(argv[1])
    if not p then return "no online player " .. tostring(argv[1]) end
    local name, v = argv[2], tonumber(argv[3])
    if name == nil or v == nil then return "usage: stats.setany <user> <StatName> <value>" end
    local out = { ok = false, stat = name, side = TK.side, requested = v }
    local enum = nil
    if CharacterStat ~= nil then
        enum = CharacterStat[name]
        if enum == nil and CharacterStat["valueOf"] ~= nil then
            local ran, e = pcall(CharacterStat["valueOf"], name)
            if ran then enum = e end
        end
    end
    if enum == nil then
        out.reason = "no CharacterStat." .. tostring(name)
        return out
    end
    local _, s = TK.call(p, "getStats")
    if s == nil then
        out.reason = "no getStats()"
        return out
    end
    local _, before = TK.call(s, "get", enum)
    out.before = before
    local ran, err = pcall(s["set"], s, enum, v)
    if not ran then
        out.reason = "Stats:set raised: " .. tostring(err)
        return out
    end
    local _, after = TK.call(s, "get", enum)
    out.after = after
    out.ok = (after ~= nil)
    if not out.ok then out.reason = "no read-back" end
    return out
end)

-- <user> <true|false>. IsoPlayer:setAutoDrink(flag) is the server-side player flag IsoGameCharacter
-- .autoDrink tests first on a server (jar: `autoDrink @7-@34 L11730` returns when the server's
-- IsoPlayer.getAutoDrink() is false); the client option (Core.getOptionAutoDrink) and the
-- asleep/aiming/climbing states gate it further, and THIRST must be at or under 0.1. The reply
-- reads the flag back through getAutoDrink() before and after, both index-first.
-- @args <user> <true|false>
-- @reply {ok, side, requested, before, after [, reason]} | string
-- @purpose Sets the server-side player autoDrink flag (IsoPlayer:setAutoDrink) on a named player, replying the flag read before and after.
TK.register("autodrink.set", function(argv)
    local p = findPlayer(argv[1])
    if not p then return "no online player " .. tostring(argv[1]) end
    local flag
    if argv[2] == "true" then flag = true elseif argv[2] == "false" then flag = false end
    if flag == nil then return "usage: autodrink.set <user> <true|false>" end
    local out = { ok = false, side = TK.side, requested = flag }
    if p["setAutoDrink"] == nil or p["getAutoDrink"] == nil then
        out.reason = "no IsoPlayer:setAutoDrink/getAutoDrink on this build"
        return out
    end
    local _, before = TK.call(p, "getAutoDrink")
    out.before = before
    local ran, err = pcall(p["setAutoDrink"], p, flag)
    if not ran then
        out.reason = "setAutoDrink raised: " .. tostring(err)
        return out
    end
    local _, after = TK.call(p, "getAutoDrink")
    out.after = after
    out.ok = (after == flag)
    if not out.ok then out.reason = "read-back differs" end
    return out
end)

-- <user>. One-tick bracket for the autoDrink gate: THIRST (Stats:get(CharacterStat.THIRST),
-- index-first) and the litres in the FIRST fluid container in the player's main inventory that
-- holds anything, read in the same command so no tick falls between them; plus the autoDrink flag
-- and the item's primary fluid. A container-less inventory replies litres = nil, item = nil.
-- @args <user>
-- @reply {ok, side, thirst, autoDrink, item, litres, fluid, containers [, reason]} | string
-- @purpose Reads a named player's THIRST and the first non-empty fluid container's litres on one tick, with the autoDrink flag, to bracket an autoDrink sip.
TK.register("autodrink.probe", function(argv)
    local p = findPlayer(argv[1])
    if not p then return "no online player " .. tostring(argv[1]) end
    local out = { ok = false, side = TK.side, containers = 0 }
    local _, s = TK.call(p, "getStats")
    local _, thirst = TK.call(s, "get", CharacterStat and CharacterStat["THIRST"])
    out.thirst = thirst
    local _, flag = TK.call(p, "getAutoDrink")
    out.autoDrink = flag
    local _, inv = TK.call(p, "getInventory")
    local _, items = TK.call(inv, "getItems")
    local _, n = TK.call(items, "size")
    if n == nil then
        out.reason = "no inventory item list"
        return out
    end
    for i = 0, n - 1 do
        local _, it = TK.call(items, "get", i)
        local _, fc = TK.call(it, "getFluidContainer")
        if fc ~= nil then
            out.containers = out.containers + 1
            local _, amount = TK.call(fc, "getAmount")
            if out.item == nil and amount ~= nil and amount > 0 then
                local _, ft = TK.call(it, "getFullType")
                out.item = ft
                out.litres = amount
                local _, prim = TK.call(fc, "getPrimaryFluid")
                local _, fname = TK.call(prim, "getFluidTypeString")
                out.fluid = fname
            end
        end
    end
    out.ok = (thirst ~= nil)
    if not out.ok then out.reason = "no THIRST read" end
    return out
end)

-- <celsius>|off. The climate admin override the install's debug climate panel uses
-- (ClimateOptionsDebug: getClimateManager():getClimateFloat(i) for i in 0..getFloatMax()-1, then
-- the ClimateFloat's setEnableAdmin / setAdminValue). The float whose getName() is "temperature"
-- (case-insensitive) is found by that walk, so no index constant is assumed. `off` clears the
-- admin flag. The final value is recomputed on the climate's own update, so the reply carries the
-- admin value read back at once (ok follows it), the float's final value and the manager's
-- getTemperature() as read in this same command -- the settled air temperature is the probe's
-- later read, not this reply's. On a dedicated server the override is the server's.
-- @args <celsius|off>
-- @reply {ok, side, requested, floatName, enableAdmin, adminValue, finalValue, temperature [, reason]} | string
-- @purpose Sets or clears the ClimateManager's admin override on the temperature float, replying the admin value read back and the manager's temperature that tick.
TK.register("climate.set", function(argv)
    local raw = argv[1]
    local off = (raw == "off")
    local c = tonumber(raw)
    if raw == nil or (not off and c == nil) then return "usage: climate.set <celsius|off>" end
    local out = { ok = false, side = TK.side, requested = raw }
    if getClimateManager == nil then
        out.reason = "no getClimateManager global on this side"
        return out
    end
    local okM, cm = pcall(getClimateManager)
    if not okM or cm == nil then
        out.reason = "getClimateManager raised or answered nil"
        return out
    end
    local _, max = TK.call(cm, "getFloatMax")
    if max == nil then
        out.reason = "no ClimateManager:getFloatMax()"
        return out
    end
    local cf = nil
    for i = 0, max - 1 do
        local _, f = TK.call(cm, "getClimateFloat", i)
        local _, nm = TK.call(f, "getName")
        if nm ~= nil and string.lower(tostring(nm)) == "temperature" then
            cf = f
            out.floatName = nm
            break
        end
    end
    if cf == nil then
        out.reason = "no ClimateFloat named temperature among " .. tostring(max)
        return out
    end
    if off then
        local ran, err = pcall(cf["setEnableAdmin"], cf, false)
        if not ran then
            out.reason = "setEnableAdmin raised: " .. tostring(err)
            return out
        end
    else
        local ran, err = pcall(function()
            cf["setEnableAdmin"](cf, true)
            cf["setAdminValue"](cf, c)
        end)
        if not ran then
            out.reason = "admin override raised: " .. tostring(err)
            return out
        end
    end
    local _, en = TK.call(cf, "isEnableAdmin")
    local _, av = TK.call(cf, "getAdminValue")
    local _, fv = TK.call(cf, "getFinalValue")
    local _, t = TK.call(cm, "getTemperature")
    out.enableAdmin = en
    out.adminValue = av
    out.finalValue = fv
    out.temperature = t
    if off then
        out.ok = (en == false)
    else
        out.ok = (en == true and av ~= nil and math.abs(av - c) < 0.01)
    end
    if not out.ok then out.reason = "read-back differs" end
    return out
end)

-- ---- Plan 4 Task 5: the server twin of fluid.fill ---------------------------------------------

-- <user> <fullType> <fluidType> <litres>. The server twin of the client fluid.fill: the client
-- command spawns a container the server never hears of, so a drink of it raises in the server's
-- ISDrinkFluidAction.new (x151w-20261005-161652 B2). This twin fills the FIRST item of the type
-- already in the named player's server inventory (getFirstTypeRecurse -- an RCON `additem` copy,
-- which both sides hold), or, when there is none, spawns one server-side with AddItem (server-only,
-- as inventory.add); it empties the FluidContainer and adds `litres` of the named fluid
-- (FluidType.FromNameLower of the lowered name, then FluidType[name], as the client twin), all
-- under pcall. The client's copy is NOT refilled: drink the result on the server (the `drink`
-- command), never with the client's drink.action.
-- @args <user> <fullType> <fluidType> <litres>
-- @reply {ok, side, fullType, id, spawned, requested, litres, fluid, capacity [, reason]} | string
-- @purpose Server twin of fluid.fill: fills the first server-inventory item of the type (spawning one server-side when absent) with the named litres of a fluid, replying the amount and primary fluid read back.
TK.register("fluid.fill", function(argv)
    local p = findPlayer(argv[1])
    if not p then return "no online player " .. tostring(argv[1]) end
    local fullType, fluidName, litres = argv[2], argv[3], tonumber(argv[4])
    if fullType == nil or fluidName == nil or litres == nil then
        return "usage: fluid.fill <user> <fullType> <fluidType> <litres>"
    end
    local out = { ok = false, side = TK.side, fullType = fullType, requested = litres, spawned = false }
    local _, inv = TK.call(p, "getInventory")
    local _, item = TK.call(inv, "getFirstTypeRecurse", fullType)
    if item == nil then
        local _, added = TK.call(inv, "AddItem", fullType)
        item = added
        out.spawned = (added ~= nil)
    end
    if item == nil then
        out.reason = "not in inventory and AddItem gave nothing for " .. fullType
        return out
    end
    local _, id = TK.call(item, "getID")
    out.id = id
    local _, fc = TK.call(item, "getFluidContainer")
    if fc == nil then
        out.reason = "no FluidContainer on " .. fullType
        return out
    end
    local enum = nil
    if FluidType ~= nil then
        if FluidType["FromNameLower"] ~= nil then
            local ran, e = pcall(FluidType["FromNameLower"], string.lower(fluidName))
            if ran then enum = e end
        end
        if enum == nil then enum = FluidType[fluidName] end
    end
    if enum == nil then
        out.reason = "no FluidType for " .. fluidName
        return out
    end
    local ranE, errE = pcall(fc["Empty"], fc)
    if not ranE then
        out.reason = "Empty raised: " .. tostring(errE)
        return out
    end
    local ran, err = pcall(fc["addFluid"], fc, enum, litres)
    if not ran then
        out.reason = "addFluid raised: " .. tostring(err)
        return out
    end
    local _, amount = TK.call(fc, "getAmount")
    local _, cap = TK.call(fc, "getCapacity")
    local _, prim = TK.call(fc, "getPrimaryFluid")
    local _, fname = TK.call(prim, "getFluidTypeString")
    out.litres = amount
    out.capacity = cap
    out.fluid = fname
    out.ok = (amount ~= nil and math.abs(amount - litres) < 0.001)
    if not out.ok then out.reason = "amount read back is not the amount added (capacity?)" end
    return out
end)

-- ---- Plan 5 Task 2: the effects harness wave (server commands) --------------------------------

-- Plan 5 shared helpers. One local (P5) holds them so the chunk's local count stays low. hop is
-- the index-first, pcall'd call: an absent member or a raise answers nil, never an error.
local P5 = {}

function P5.hop(obj, name, ...)
    if obj == nil then return nil end
    local f = obj[name]
    if f == nil then return nil end
    local ran, v = pcall(f, obj, ...)
    if not ran then return nil end
    return v
end

-- One body part by index: getBodyDamage():getBodyPart(BodyPartType.FromIndex(i)). BodyPartType
-- is a Java enum whose FromIndex is a static, so it goes through the index-first dot call.
function P5.part(p, i)
    local bd = P5.hop(p, "getBodyDamage")
    if bd == nil or BodyPartType == nil then return nil, nil end
    local fromIndex = BodyPartType["FromIndex"]
    if fromIndex == nil then return nil, nil end
    local ran, t = pcall(fromIndex, i)
    if not ran or t == nil then return nil, nil end
    return P5.hop(bd, "getBodyPart", t), t
end

-- The reader table of bodypart.get: reply key, getter. Every getter takes no argument.
P5.PART_GETTERS = {
    { "health", "getHealth" }, { "bleedingTime", "getBleedingTime" }, { "bleeding", "bleeding" },
    { "deepWoundTime", "getDeepWoundTime" }, { "scratchTime", "getScratchTime" },
    { "cutTime", "getCutTime" }, { "biteTime", "getBiteTime" }, { "burnTime", "getBurnTime" },
    { "fractureTime", "getFractureTime" }, { "woundInfectionLevel", "getWoundInfectionLevel" },
    { "infectedWound", "isInfectedWound" }, { "additionalPain", "getAdditionalPain" },
    { "bandaged", "bandaged" }, { "alcoholLevel", "getAlcoholLevel" },
}

function P5.partRow(part, t, i)
    local row = { index = i }
    if BodyPartType ~= nil and BodyPartType["ToString"] ~= nil and t ~= nil then
        local ran, nm = pcall(BodyPartType["ToString"], t)
        if ran then row.name = nm end
    end
    for _, g in ipairs(P5.PART_GETTERS) do
        local v = P5.hop(part, g[2])
        if v == nil then row["absent_" .. g[1]] = true else row[g[1]] = v end
    end
    return row
end

-- <user> <partIndex|all>. Per body part the wound fields #2366 / #2626 name, read index-first
-- under pcall through BodyDamage:getBodyPart(BodyPartType.FromIndex(i)); a getter the build does
-- not answer is written once as absent_<field> on that row, never raised. `all` walks the
-- indices 0 .. getBodyParts():size() - 1; the client twin reads the local player the same way.
-- @args <user> <partIndex|all>
-- @reply {ok, side, parts [, reason]} | string
-- @purpose Reads the per-part wound fields (health, bleeding, deep wound, scratch, cut, bite, burn, fracture, infection, pain, bandage and alcohol) of one or all body parts of a named player.
TK.register("bodypart.get", function(argv)
    local p = findPlayer(argv[1])
    if not p then return "no online player " .. tostring(argv[1]) end
    local which = argv[2] or "all"
    local out = { ok = false, side = TK.side, parts = {} }
    local bd = P5.hop(p, "getBodyDamage")
    if bd == nil then
        out.reason = "no getBodyDamage()"
        return out
    end
    local first, last = 0, 0
    if which == "all" then
        local n = P5.hop(P5.hop(bd, "getBodyParts"), "size")
        if n == nil then
            out.reason = "no getBodyParts():size()"
            return out
        end
        first, last = 0, n - 1
    else
        first = tonumber(which)
        if first == nil then return "usage: bodypart.get <user> <partIndex|all>" end
        last = first
    end
    for i = first, last do
        local part, t = P5.part(p, i)
        if part == nil then
            out.reason = "no body part at index " .. i
            if which ~= "all" then return out end
        else
            out.parts[#out.parts + 1] = P5.partRow(part, t, i)
        end
    end
    out.ok = (#out.parts > 0)
    return out
end)

-- The writer table of bodypart.set: field name -> { setter, getter, kind, mask bit }. The mask bit
-- is the body-part packet key minus one (#2626: bleedingTime 17, deepWoundTime 18, scratchTime 12,
-- biteTime 13, fractureTime 27, cutTime 39, additionalPain 22, woundInfectionLevel 15,
-- infectedWound 16, health 0); a field with no bit (bleeding, burnTime) replies synced=false with
-- the reason when `sync` is asked. kind: "num" -> tonumber, "bool" -> true|false.
P5.PART_SETTERS = {
    health = { "SetHealth", "getHealth", "num", 0 },
    bleedingTime = { "setBleedingTime", "getBleedingTime", "num", 17 },
    bleeding = { "setBleeding", "bleeding", "bool", nil },
    deepWoundTime = { "setDeepWoundTime", "getDeepWoundTime", "num", 18 },
    scratchTime = { "setScratchTime", "getScratchTime", "num", 12 },
    cutTime = { "setCutTime", "getCutTime", "num", 39 },
    biteTime = { "setBiteTime", "getBiteTime", "num", 13 },
    burnTime = { "setBurnTime", "getBurnTime", "num", nil },
    fractureTime = { "setFractureTime", "getFractureTime", "num", 27 },
    woundInfectionLevel = { "setWoundInfectionLevel", "getWoundInfectionLevel", "num", 15 },
    infectedWound = { "setInfectedWound", "isInfectedWound", "bool", 16 },
    additionalPain = { "setAdditionalPain", "getAdditionalPain", "num", 22 },
}

-- <user> <partIndex> <field> <value> [sync]. The matching BodyPart setter (index-first, under
-- pcall) for one field of one part, read back through the getter before and after. `sync` then
-- calls the Lua global syncBodyPart(part, mask) with the field's own packet bit (#2626; the long
-- mask goes in as a double, 2^bit, which is exact to 2^53); the global is server-gated and the
-- call returning says nothing about delivery, so `synced` records only that it ran -- delivery is
-- the client twin's bodypart.get. The setter table is P5.PART_SETTERS above.
-- @args <user> <partIndex> <field> <value> [sync]
-- @reply {ok, side, part, field, requested, before, after, synced [, mask] [, reason]} | string
-- @purpose Writes one wound field of one body part of a named player through its BodyPart setter, replying the value before and after and whether syncBodyPart ran with that field's packet bit.
TK.register("bodypart.set", function(argv)
    local p = findPlayer(argv[1])
    if not p then return "no online player " .. tostring(argv[1]) end
    local idx, field, raw = tonumber(argv[2]), argv[3], argv[4]
    if idx == nil or field == nil or raw == nil then
        return "usage: bodypart.set <user> <partIndex> <field> <value> [sync]"
    end
    local spec = P5.PART_SETTERS[field]
    local out = { ok = false, side = TK.side, part = idx, field = field, synced = false }
    if spec == nil then
        out.reason = "no setter for " .. tostring(field)
        return out
    end
    local v
    if spec[3] == "bool" then
        if raw == "true" or raw == "1" then v = true elseif raw == "false" or raw == "0" then v = false end
    else
        v = tonumber(raw)
    end
    if v == nil then
        out.reason = "bad value " .. tostring(raw)
        return out
    end
    out.requested = v
    local part = P5.part(p, idx)
    if part == nil then
        out.reason = "no body part at index " .. idx
        return out
    end
    out.before = P5.hop(part, spec[2])
    local setter = part[spec[1]]
    if setter == nil then
        out.reason = "no " .. spec[1] .. " on BodyPart"
        return out
    end
    local ran, err = pcall(setter, part, v)
    if not ran then
        out.reason = spec[1] .. " raised: " .. tostring(err)
        return out
    end
    out.after = P5.hop(part, spec[2])
    out.ok = (out.after ~= nil)
    if argv[5] == "sync" then
        if spec[4] == nil then
            out.reason = "no packet bit for " .. field .. ": synced=false"
        elseif syncBodyPart == nil then
            out.reason = "no syncBodyPart global on this side"
        else
            out.mask = 2 ^ spec[4]
            local ranS, errS = pcall(syncBodyPart, part, out.mask)
            out.synced = ranS
            if not ranS then out.reason = "syncBodyPart raised: " .. tostring(errS) end
        end
    end
    return out
end)

-- The health reading the three health commands reply with: BodyDamage:getOverallBodyHealth()
-- and BodyDamage:getHealth(), plus the per-part health list through getBodyParts() (a Java
-- list: walked by size()/get(i), never by #), each element read through BodyPart:getHealth().
function P5.healthRead(p)
    local bd = P5.hop(p, "getBodyDamage")
    local r = { overall = P5.hop(bd, "getOverallBodyHealth"), health = P5.hop(bd, "getHealth"), parts = {} }
    local list = P5.hop(bd, "getBodyParts")
    local n = P5.hop(list, "size")
    local i = 0
    while n ~= nil and i < n do
        r.parts[#r.parts + 1] = P5.hop(P5.hop(list, "get", i), "getHealth")
        i = i + 1
    end
    return r
end

-- <user> <f>. BodyDamage:ReduceGeneralHealth(f), the engine call every health drain makes (it
-- spreads f over the parts); the overall health is read before and after on the same tick, and
-- the reply carries the per-part health after. The value is a float in the engine's own units
-- (the drains pass fractions of the 0..100 scale). Server-side: the server owns BodyDamage.
-- @args <user> <f>
-- @reply {ok, side, requested, before, after, health, parts [, reason]} | string
-- @purpose Calls BodyDamage:ReduceGeneralHealth(f) on a named player, replying the overall body health before and after and the per-part health.
TK.register("health.reduce", function(argv)
    local p = findPlayer(argv[1])
    if not p then return "no online player " .. tostring(argv[1]) end
    local f = tonumber(argv[2])
    if f == nil then return "usage: health.reduce <user> <f>" end
    local out = { ok = false, side = TK.side, requested = f }
    local bd = P5.hop(p, "getBodyDamage")
    if bd == nil or bd["ReduceGeneralHealth"] == nil then
        out.reason = "no BodyDamage:ReduceGeneralHealth"
        return out
    end
    out.before = P5.hop(bd, "getOverallBodyHealth")
    local ran, err = pcall(bd["ReduceGeneralHealth"], bd, f)
    if not ran then
        out.reason = "ReduceGeneralHealth raised: " .. tostring(err)
        return out
    end
    local r = P5.healthRead(p)
    out.after, out.health, out.parts = r.overall, r.health, r.parts
    out.ok = (out.after ~= nil)
    return out
end)

-- <user> <f>. BodyDamage:AddGeneralHealth(f), the engine call the regeneration terms make; read
-- and replied exactly as health.reduce, so a reduce and an add can be compared on the same
-- scale.
-- @args <user> <f>
-- @reply {ok, side, requested, before, after, health, parts [, reason]} | string
-- @purpose Calls BodyDamage:AddGeneralHealth(f) on a named player, replying the overall body health before and after and the per-part health.
TK.register("health.add", function(argv)
    local p = findPlayer(argv[1])
    if not p then return "no online player " .. tostring(argv[1]) end
    local f = tonumber(argv[2])
    if f == nil then return "usage: health.add <user> <f>" end
    local out = { ok = false, side = TK.side, requested = f }
    local bd = P5.hop(p, "getBodyDamage")
    if bd == nil or bd["AddGeneralHealth"] == nil then
        out.reason = "no BodyDamage:AddGeneralHealth"
        return out
    end
    out.before = P5.hop(bd, "getOverallBodyHealth")
    local ran, err = pcall(bd["AddGeneralHealth"], bd, f)
    if not ran then
        out.reason = "AddGeneralHealth raised: " .. tostring(err)
        return out
    end
    local r = P5.healthRead(p)
    out.after, out.health, out.parts = r.overall, r.health, r.parts
    out.ok = (out.after ~= nil)
    return out
end)

-- <user>. The server reading of overall and per-part health, no write; the client twin reads the
-- local player, so the two replies side by side say what the health surfaces carry to the owner
-- (#2609, #2713 leave the carrier unread).
-- @args <user>
-- @reply {ok, side, overall, health, parts [, reason]} | string
-- @purpose Reads a named player's overall body health (getOverallBodyHealth), BodyDamage health and the per-part health list on the server.
TK.register("health.get", function(argv)
    local p = findPlayer(argv[1])
    if not p then return "no online player " .. tostring(argv[1]) end
    local r = P5.healthRead(p)
    return { ok = (r.overall ~= nil), side = TK.side, overall = r.overall, health = r.health, parts = r.parts }
end)

-- The four whole-body regeneration constants (#2354): reply key, getter, setter. The severe tier
-- keeps the engine's own misspelling, setSeverlyReducedHealthAddition.
P5.REGEN = {
    { "standard", "getStandardHealthAddition", "setStandardHealthAddition" },
    { "reduced", "getReducedHealthAddition", "setReducedHealthAddition" },
    { "severe", "getSeverlyReducedHealthAddition", "setSeverlyReducedHealthAddition" },
    { "sleeping", "getSleepingHealthAddition", "setSleepingHealthAddition" },
}

function P5.regenRead(bd)
    local r = {}
    for _, g in ipairs(P5.REGEN) do
        local v = P5.hop(bd, g[2])
        if v == nil then r["absent_" .. g[1]] = true else r[g[1]] = v end
    end
    return r
end

-- <user> <standard> <reduced> <severe> <sleeping>. The four BodyDamage regeneration setters
-- (#2354: 0.002 / 0.0013 / 0.0008 / 0.02 by default), index-first under pcall; a "-" in place of
-- a value leaves that constant alone. The reply carries the four values read before and after, so
-- a setter the engine re-asserts shows as after ~= requested on a later regen.get.
-- @args <user> <standard> <reduced> <severe> <sleeping>
-- @reply {ok, side, before, after [, reason]} | string
-- @purpose Writes the four BodyDamage regeneration constants (standard, reduced, severe, sleeping) of a named player through their setters, replying the four values before and after.
TK.register("regen.set", function(argv)
    local p = findPlayer(argv[1])
    if not p then return "no online player " .. tostring(argv[1]) end
    local out = { ok = false, side = TK.side }
    local bd = P5.hop(p, "getBodyDamage")
    if bd == nil then
        out.reason = "no getBodyDamage()"
        return out
    end
    local want = {}
    for k = 1, 4 do
        local a = argv[k + 1]
        if a == nil then return "usage: regen.set <user> <standard> <reduced> <severe> <sleeping>  (- leaves one alone)" end
        if a ~= "-" then
            want[k] = tonumber(a)
            if want[k] == nil then return "bad value " .. tostring(a) end
        end
    end
    out.before = P5.regenRead(bd)
    local err = nil
    for k, g in ipairs(P5.REGEN) do
        if want[k] ~= nil then
            local setter = bd[g[3]]
            if setter == nil then
                err = "no " .. g[3]
            else
                local ran, e = pcall(setter, bd, want[k])
                if not ran then err = g[3] .. " raised: " .. tostring(e) end
            end
        end
    end
    out.after = P5.regenRead(bd)
    out.ok = (err == nil)
    out.reason = err
    return out
end)

-- <user>. The server reading of the four regeneration constants through their getters; no write.
-- Re-read it after a regen.set, a load or a day to see whether the engine kept the value.
-- @args <user>
-- @reply {ok, side, standard, reduced, severe, sleeping [, absent_<name>]} | string
-- @purpose Reads the four BodyDamage regeneration constants (standard, reduced, severe, sleeping) of a named player through their getters.
TK.register("regen.get", function(argv)
    local p = findPlayer(argv[1])
    if not p then return "no online player " .. tostring(argv[1]) end
    local bd = P5.hop(p, "getBodyDamage")
    if bd == nil then return { ok = false, side = TK.side, reason = "no getBodyDamage()" } end
    local r = P5.regenRead(bd)
    r.ok = (r.standard ~= nil)
    r.side = TK.side
    return r
end)

-- <user>. One-tick reading of the thermoregulator's core temperature and the TEMPERATURE stat.
-- getThermoregulator() answers nil off the server and can answer nil on it (#3010), so it is
-- guarded: a nil regulator replies ok=false with the reason and still carries the stat. Each
-- getter (getCoreTemperature, getSetPoint, getCoreHeatDelta, getCoreRateOfChange) is index-first
-- under pcall and a missing one is written once as absent_<field>; the stat is
-- Stats:get(CharacterStat.TEMPERATURE).
-- @args <user>
-- @reply {ok, side, core, setPoint, heatDelta, rateOfChange, temperature [, absent_<field>] [, reason]} | string
-- @purpose Reads a named player's thermoregulator core temperature, set point, heat delta and rate of change beside the TEMPERATURE stat on one server tick.
TK.register("temp.core", function(argv)
    local p = findPlayer(argv[1])
    if not p then return "no online player " .. tostring(argv[1]) end
    local out = { ok = false, side = TK.side }
    local stats = P5.hop(p, "getStats")
    if CharacterStat ~= nil and CharacterStat["TEMPERATURE"] ~= nil then
        out.temperature = P5.hop(stats, "get", CharacterStat["TEMPERATURE"])
    else
        out.absent_temperature = true
    end
    local bd = P5.hop(p, "getBodyDamage")
    local th = P5.hop(bd, "getThermoregulator")
    if th == nil then
        out.reason = "no thermoregulator (nil off the server, or not yet created)"
        return out
    end
    local fields = {
        { "core", "getCoreTemperature" }, { "setPoint", "getSetPoint" },
        { "heatDelta", "getCoreHeatDelta" }, { "rateOfChange", "getCoreRateOfChange" },
    }
    for _, g in ipairs(fields) do
        local v = P5.hop(th, g[2])
        if v == nil then out["absent_" .. g[1]] = true else out[g[1]] = v end
    end
    out.ok = (out.core ~= nil)
    return out
end)

-- <user> [value]. BodyDamage:getDrunkReductionValue() / setDrunkReductionValue(v), the per-player
-- reduction the intoxication decay reads (platform briefing 6). With no value it only reads; with
-- one it writes through the setter (index-first, pcall) and replies the value read before and
-- after.
-- @args <user> [<value>]
-- @reply {ok, side, before, after [, requested] [, reason]} | string
-- @purpose Reads, or with a value writes, BodyDamage's drunk-reduction value on a named player, replying it before and after.
TK.register("intox.reduction", function(argv)
    local p = findPlayer(argv[1])
    if not p then return "no online player " .. tostring(argv[1]) end
    local out = { ok = false, side = TK.side }
    local bd = P5.hop(p, "getBodyDamage")
    if bd == nil then
        out.reason = "no getBodyDamage()"
        return out
    end
    out.before = P5.hop(bd, "getDrunkReductionValue")
    if argv[2] ~= nil then
        local v = tonumber(argv[2])
        if v == nil then return "usage: intox.reduction <user> [<value>]" end
        out.requested = v
        local setter = bd["setDrunkReductionValue"]
        if setter == nil then
            out.reason = "no setDrunkReductionValue"
            return out
        end
        local ran, err = pcall(setter, bd, v)
        if not ran then
            out.reason = "setDrunkReductionValue raised: " .. tostring(err)
            return out
        end
    end
    out.after = P5.hop(bd, "getDrunkReductionValue")
    out.ok = (out.after ~= nil)
    return out
end)

-- The landing listener (#2357 lists six tags; the jar adds FALLDOWN, fired by
-- handleLandingImpact after ReduceGeneralHealth). Events.OnPlayerGetDamage hands the listener the
-- character, a tag and the amount. The listener is installed once, lazily, by the first
-- fall.probe on a side, and never raises: every body runs under pcall. It counts every tag and
-- keeps up to 20 FALLDOWN records (side, amount, wall time) in P5.fall.
P5.fall = { list = {}, counts = {}, hooked = false }

function P5.fallHook()
    if P5.fall.hooked or TK.p5FallHooked then
        P5.fall.hooked = true
        return true
    end
    if Events == nil or Events.OnPlayerGetDamage == nil then return false end
    Events.OnPlayerGetDamage.Add(function(character, tag, amount)
        pcall(function()
            local t = tostring(tag)
            P5.fall.counts[t] = (P5.fall.counts[t] or 0) + 1
            if t == "FALLDOWN" and #P5.fall.list < 20 then
                P5.fall.list[#P5.fall.list + 1] = { side = TK.side, amount = amount, wall = TK.now() }
            end
        end)
    end)
    TK.p5FallHooked = true
    P5.fall.hooked = true
    return true
end

-- Fracture times of every leg and foot part, and the largest fracture time on any part, read
-- through getBodyParts() (walked by size()/get(i)) and BodyPartType.ToString for the name.
function P5.legFractures(p)
    local out = { legs = {}, maxFracture = 0 }
    local bd = P5.hop(p, "getBodyDamage")
    local list = P5.hop(bd, "getBodyParts")
    local n = P5.hop(list, "size")
    local i = 0
    while n ~= nil and i < n do
        local part = P5.hop(list, "get", i)
        local ft = P5.hop(part, "getFractureTime")
        local nm = nil
        local t = P5.hop(part, "getType")
        if t ~= nil and BodyPartType ~= nil and BodyPartType["ToString"] ~= nil then
            local ran, s = pcall(BodyPartType["ToString"], t)
            if ran then nm = s end
        end
        if ft ~= nil and ft > out.maxFracture then out.maxFracture = ft end
        local low = string.lower(tostring(nm))
        if ft ~= nil and (string.find(low, "leg", 1, true) or string.find(low, "foot", 1, true)) then
            out.legs[#out.legs + 1] = tostring(nm) .. "=" .. tostring(ft)
        end
        i = i + 1
    end
    return out
end

-- <user> [<z>]. The SERVER half of the landing probe. The first call installs the
-- OnPlayerGetDamage listener on this side (so call it BEFORE the client's fall.probe, which
-- installs the client's). With <z> it also tries a server-side height write,
-- IsoMovingObject:setZ(z0 + z) on the named player: a connected player's position is the
-- client's to report, so the read-back right after says only what the call did, never that the
-- player fell. The reply is the listener's record so far -- FALLDOWN records (side, amount,
-- wall), a count of every tag seen, and the leg and foot fracture times -- so call it again after
-- the client's fall to read what the server heard.
-- @args <user> [<z>]
-- @reply {ok, side, hooked, zBefore, zAfter, fall, counts, legs, maxFracture [, reason]} | string
-- @purpose Installs the server OnPlayerGetDamage listener for tag FALLDOWN, optionally tries a server setZ on the player, and replies the FALLDOWN records heard so far with the leg fracture times.
TK.register("fall.probe", function(argv)
    local p = findPlayer(argv[1])
    if not p then return "no online player " .. tostring(argv[1]) end
    local out = { ok = false, side = TK.side }
    out.hooked = P5.fallHook()
    if not out.hooked then out.reason = "no Events.OnPlayerGetDamage on this side" end
    if argv[2] ~= nil then
        local dz = tonumber(argv[2])
        if dz == nil then return "usage: fall.probe <user> [<z>]" end
        out.zBefore = P5.hop(p, "getZ")
        local setter = p["setZ"]
        if setter == nil or out.zBefore == nil then
            out.reason = "no setZ/getZ on the player"
        else
            local ran, err = pcall(setter, p, out.zBefore + dz)
            if not ran then out.reason = "setZ raised: " .. tostring(err) end
        end
        out.zAfter = P5.hop(p, "getZ")
    end
    local fr = P5.legFractures(p)
    out.fall, out.counts, out.legs, out.maxFracture = P5.fall.list, P5.fall.counts, fr.legs, fr.maxFracture
    out.ok = out.hooked
    return out
end)

-- <a.b.c> <value>. TEST-ONLY INSTRUMENT: the harness mod is installed only by test profiles and is never
-- shipped. Assigns a scalar to a field of any server-side Lua table reached by a dotted path from the
-- globals, e.g. `NR.server.fast.endFoldOn false`, so an acceptance driver can reach a plain Lua field
-- that `globalmoddata.setpath` cannot (it assigns modData leaves only). It stands in for a chunk runner
-- because `loadstring` is removed on 42.20.x (docs/platform/lessons.md). The value is `true`, `false`,
-- `nil`, a number or else the string as given; every path segment but the last must already be a table
-- (a numeric-looking segment is tried as a string key first, then as a number), and the field is never
-- created on a missing parent. The bus is the harness's own file channel, so only the driver writes it.
-- @args <a.b.c> <value>
-- @reply {ok, side, path, before, after [, err]} | string
-- @purpose Test-only: assigns a true, false, nil, number or string scalar to a field of a server Lua table reached by a dotted path from the globals, replying the value before and after.
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

-- ---- Plan 10c Task H0: the frame-time instrument and the synthetic ghost load -------------------------
-- TEST-ONLY INSTRUMENTS (the harness mod is installed only by test profiles and is never shipped). Appended at
-- the end of the file so no `repo:` pointer into it moves (CLAUDE.md s5). Five commands:
--
-- tick.ring <n> | read <tag> | off. A ring of the last n server frames. Each frame is stamped twice with
--   getTimestampMs (1 ms resolution, so a frame's figures are whole milliseconds and a sub-millisecond frame
--   reads 0): at OnTickEvenPaused (the frame's start, the first thing IngameState.updateInternal fires) and at
--   OnTick (the frame's last Lua event). busy = start -> OnTick within one frame (it misses the work after OnTick
--   and the packet passes between frames); period = start -> next start; endPeriod = OnTick -> next OnTick (the
--   gap closest to the engine's own update period, which is stamped after the frame). Each frame also carries
--   whether EveryOneMinute fired in it (minute), the ghost runs made in it (runs) and the ms spent in them
--   (ghostMs). The hooks are installed ONCE, lazily, at the first tick.ring / perf.local / ghost.load, so they are
--   appended after every mod's own OnTick and EveryOneMinute handlers (Event.trigger walks its callback list by
--   index and re-reads its size, so an Add from inside a handler is safe and runs in the same pass): the OnTick
--   stamp therefore follows the mod's drain and the ghost work, and the minute flag follows the mod's minute.
--   `read` replies the p50, p99 and max (nearest rank) of busy, period and endPeriod with the count of periods
--   over 110 ms, and writes every frame to pzt-results/tick-ring-<tag>.json; the ring keeps recording.
--
-- perf.local <n> | read <tag> | now. The engine's own frame-period counters through getPerformanceLocal() (jar:
--   LuaManager$GlobalObject.getPerformanceLocal L3101 -> PerformanceStatistic.getLocalTable). The engine feeds
--   PerformanceStatistic.addUpdate(ms) once a frame from GameServer.main (L1113-L1126) and copies the counters into
--   that flat Lua table once a MultiplayerStatisticsPeriod (default 1 s; StatisticManager.update L179-L181), then
--   clears them (Statistic.update: every 6-argument Counter is perishable), so `max-update-period` and
--   `min-update-period` are per-window figures and `avg-update-period` is a 5 % running mean restarted from 0 each
--   window (addUpdate L44: avg += (ms - avg) * 0.05), not a window mean. The table is read on every OnTick and a
--   sample is kept only when the window's figures changed, so each window is sampled once; a sample carries the
--   wall ms and the ring's frame number at which it was seen, so a driver can line it up with the frames the
--   window covered (the frames from the previous sample's frame to this sample's frame minus one).
--   `read` writes pzt-results/perf-local-<tag>.json; `now` replies the table as it stands.
--
-- ghost.load <N> <burst|rr<m>|drainTicks|budget<ms>>, ghost.stop, ghost.stats. N - (online players) ghost
--   records, so the two real players plus the ghosts make N. THE CHOICE (Plan 10c H0 Step 1): a ghost reaches the
--   pipeline through NutritionRevamp.server.minute.run(ghostName, carrier, ghostRecord) -- the call P.work makes
--   -- with P.work's own two lines kept here on the ghost's record (record.lastSeen = the world age, and the dead
--   flag read off the carrier) and P.onMinute fired after it as P.work fires it. P.work itself is not called,
--   because it fetches the record from the mod's store by username and would create a store record for a ghost.
--   The ghost record is a deep copy of its carrier's store record (the carrier is the real online player chosen
--   round-robin), renamed to the ghost's name, held in this table only (TK.H0.g.ghosts), never in the store; it
--   keeps its own stamps, so each run integrates the game time since that ghost last ran. ghost.stats counts the
--   store keys that start with "ghost" as a guard (storeGhostKeys, expected 0).
--   COST, NOT BEHAVIOUR: the pipeline runs against a real IsoPlayer, so a ghost's Java writes land on its
--   carrier: the weight step's setCalories/setProteins/setCarbohydrates/setLipids/setWeight/setIncWeight/
--   setIncWeightLot/setDecWeight on the carrier's Nutrition; the effects step's regeneration constants, per-part
--   bleeding/infection/wound-time writes, setCatchACold, ReduceGeneralHealth and trait add/remove; the strength
--   step's trait add/remove, setMaxWeightDelta and setPerkLevelDebug; and sendSyncPlayerFields(carrier, 2) on a
--   trait change, which goes to the carrier's own connection and is counted (syncs) but not suppressed. No
--   behaviour reading may rest on a session with ghosts loaded.
--   THE BUS PUSH IS SUPPRESSED: around every ghost batch the global sendServerCommand is swapped for a counting
--   stub and restored after (every ghost run is under pcall, so the restore always runs); the mod's B.sendMirror
--   reads that global at call time, so the mirror is still BUILT (K.mirror.build, its cost kept) and never sent
--   (suppressed counts the would-be sends). The transient per-username tables a ghost leaves in the mod
--   (bus.effects.dirty/last, effects.last, intake.lastIngested/pendingAlc/pendingCaf) are cleared by ghost.stop.
--   SCHEDULERS (harness code, driving ghosts only; the real players stay on the mod's own drain):
--     burst       on EveryOneMinute run every ghost.
--     rr<m>       on EveryOneMinute run ceil(G/m) ghosts in a persistent rotation (G = the ghost count).
--     drainTicks  on EveryOneMinute enqueue every ghost not already queued (the queue carries over); on OnTick run
--                 ceil(G / T) a tick, T the OnTick count between the last two minute events (1 a tick until one
--                 whole minute has been counted).
--     budget<ms>  on EveryOneMinute enqueue every ghost not already queued (carried, never rebuilt, so nothing
--                 starves); on OnTick run at least one queued ghost, then more until getTimestampMs has moved
--                 <ms> or the run count reaches floor(<ms> / mean), the mean a running mean (0.8/0.2) of the
--                 per-run ms of each tick's batch (1 ms resolution: the ms cap is coarse, the run cap does the
--                 metering).
--   ghost.stats: runs, failures, ms in ghost runs (1 ms resolution, summed per batch), the minute events seen,
--   starved = ghosts not run within their period (1 minute event; m for rr<m>) counted at each minute event
--   (starvedEvents, starvedMinutes, maxStaleMinutes), neverRun, per-ghost staleness in minute events and in game
--   minutes, and runs per frame (max, mean over frames with a run, mean over all frames since the load).
TK.H0 = TK.H0 or {}
local H0 = TK.H0
H0.RING_MAX = 20000
H0.PERF_MAX = 20000
H0.frameNo = H0.frameNo or 0
H0.frameRuns = H0.frameRuns or 0
H0.frameGhostMs = H0.frameGhostMs or 0

function H0.now()
    if getTimestampMs == nil then return 0 end
    return getTimestampMs()
end

function H0.ensureHooks()
    if H0.hooked then return H0.hookInfo end
    H0.hooked = true
    H0.hookInfo = { evenPaused = false, tick = false, minute = false }
    if Events.OnTickEvenPaused ~= nil then
        Events.OnTickEvenPaused.Add(function() TK.H0.onFrameStart() end)
        H0.hookInfo.evenPaused = true
    end
    if Events.OnTick ~= nil then
        Events.OnTick.Add(function() TK.H0.onTickLate() end)
        H0.hookInfo.tick = true
    end
    if Events.EveryOneMinute ~= nil then
        Events.EveryOneMinute.Add(function() TK.H0.onMinuteLate() end)
        H0.hookInfo.minute = true
    end
    return H0.hookInfo
end

function H0.onFrameStart()
    H0.frameStart = H0.now()
    H0.minuteFlag = false
    H0.frameRuns = 0
    H0.frameGhostMs = 0
end

-- nearest-rank percentile of an ascending array
function H0.pct(sorted, p)
    local n = #sorted
    if n == 0 then return nil end
    local k = math.ceil(p * n)
    if k < 1 then k = 1 end
    if k > n then k = n end
    return sorted[k]
end

function H0.summary(list)
    local s = {}
    for i = 1, #list do s[#s + 1] = list[i] end
    table.sort(s)
    return { n = #s, p50 = H0.pct(s, 0.5), p99 = H0.pct(s, 0.99), max = s[#s], min = s[1] }
end

-- ---- the ring ---------------------------------------------------------------------------------------------
function H0.ringRecord(e)
    local R = H0.ring
    if R == nil then return end
    local i = R.next
    R.frame[i] = H0.frameNo
    R.start[i] = H0.frameStart or -1
    R.stop[i] = e
    if H0.frameStart ~= nil and H0.frameStart <= e then R.busy[i] = e - H0.frameStart else R.busy[i] = -1 end
    if R.lastStart ~= nil and H0.frameStart ~= nil then R.period[i] = H0.frameStart - R.lastStart else R.period[i] = -1 end
    if R.lastEnd ~= nil then R.endPeriod[i] = e - R.lastEnd else R.endPeriod[i] = -1 end
    R.minute[i] = H0.minuteFlag and 1 or 0
    R.runs[i] = H0.frameRuns
    R.ghostMs[i] = H0.frameGhostMs
    R.lastStart = H0.frameStart
    R.lastEnd = e
    R.count = R.count + 1
    R.next = i + 1
    if R.next > R.cap then R.next = 1 end
end

-- the ring oldest first, as parallel arrays
function H0.ringLinear()
    local R = H0.ring
    local n = R.count
    if n > R.cap then n = R.cap end
    local first = 1
    if R.count > R.cap then first = R.next end
    local out = { frame = {}, start = {}, stop = {}, busy = {}, period = {}, endPeriod = {}, minute = {}, runs = {},
                  ghostMs = {} }
    local j = first
    for _k = 1, n do
        for key, arr in pairs(out) do arr[#arr + 1] = R[key][j] end
        j = j + 1
        if j > R.cap then j = 1 end
    end
    return out, n
end

-- @args <n> | read <tag> | off
-- @reply {ok, side, armed, cap, hooks} | {ok, side, tag, frames, recorded, cap, busy, period, endPeriod, over110, minuteFrames, minuteBusyMax, runsMax, ghostMsMax, result, file} | {ok, side, off} | string
-- @purpose Test-only: arms a ring of the last n server frames stamped at OnTickEvenPaused and OnTick (1 ms clock), or replies its busy, period and end-to-end period p50/p99/max and writes every frame to tick-ring-<tag>.json.
TK.register("tick.ring", function(argv)
    local usage = "usage: tick.ring <n> | read <tag> | off  (1 <= n <= 20000)"
    local a = argv[1]
    if a == "off" then
        H0.ring = nil
        return { ok = true, side = TK.side, off = true }
    end
    if a == "read" then
        local tag = argv[2]
        if tag == nil then return usage end
        if H0.ring == nil then return { ok = false, side = TK.side, reason = "no ring armed" } end
        local L, n = H0.ringLinear()
        local busy, period, endp = {}, {}, {}
        local over, minutes, minuteBusyMax, runsMax, gmsMax = 0, 0, nil, 0, 0
        for i = 1, n do
            if L.busy[i] >= 0 then busy[#busy + 1] = L.busy[i] end
            if L.period[i] >= 0 then
                period[#period + 1] = L.period[i]
                if L.period[i] > 110 then over = over + 1 end
            end
            if L.endPeriod[i] >= 0 then endp[#endp + 1] = L.endPeriod[i] end
            if L.minute[i] == 1 then
                minutes = minutes + 1
                if L.busy[i] >= 0 and (minuteBusyMax == nil or L.busy[i] > minuteBusyMax) then minuteBusyMax = L.busy[i] end
            end
            if L.runs[i] > runsMax then runsMax = L.runs[i] end
            if L.ghostMs[i] > gmsMax then gmsMax = L.ghostMs[i] end
        end
        local out = { ok = true, side = TK.side, tag = tag, frames = n, recorded = H0.ring.count, cap = H0.ring.cap,
                      busy = H0.summary(busy), period = H0.summary(period), endPeriod = H0.summary(endp),
                      over110 = over, minuteFrames = minutes, minuteBusyMax = minuteBusyMax, runsMax = runsMax,
                      ghostMsMax = gmsMax, armedAt = H0.ring.armedAt, hooks = H0.hookInfo }
        local doc = {}
        for k, v in pairs(out) do doc[k] = v end
        doc.frames_list = L
        out.result = "tick-ring-" .. tag
        out.file = "pzt-results/tick-ring-" .. tag .. ".json"
        TK.result(out.result, doc)
        return out
    end
    local n = tonumber(a)
    if n == nil or n < 1 or n > H0.RING_MAX or n ~= math.floor(n) then return usage end
    local hooks = H0.ensureHooks()
    H0.ring = { cap = n, next = 1, count = 0, armedAt = H0.now(), frame = {}, start = {}, stop = {}, busy = {},
                period = {}, endPeriod = {}, minute = {}, runs = {}, ghostMs = {} }
    return { ok = true, side = TK.side, armed = true, cap = n, hooks = hooks }
end)

-- ---- perf.local -------------------------------------------------------------------------------------------
H0.PERF_KEYS = { "min-update-period", "max-update-period", "avg-update-period", "fps", "memory-used" }

function H0.perfTable()
    if getPerformanceLocal == nil then return nil end
    local ok, t = pcall(getPerformanceLocal)
    if not ok then return nil end
    return t
end

function H0.perfPoll(now)
    local P = H0.perf
    if P == nil then return end
    local t = H0.perfTable()
    if t == nil then return end
    local mn, mx, av, cur = t["min-update-period"], t["max-update-period"], t["avg-update-period"], t["fps"]
    if mn == P.lmn and mx == P.lmx and av == P.lav and cur == P.lcur then return end
    P.lmn, P.lmx, P.lav, P.lcur = mn, mx, av, cur
    local i = P.next
    P.wall[i] = now
    P.frame[i] = H0.frameNo
    P.min[i] = mn
    P.max[i] = mx
    P.avg[i] = av
    P.cur[i] = cur
    P.mem[i] = t["memory-used"]
    P.count = P.count + 1
    P.next = i + 1
    if P.next > P.cap then P.next = 1 end
end

-- @args <n> | read <tag> | now
-- @reply {ok, side, armed, cap, present, hooks} | {ok, side, tag, samples, recorded, max, min, avg, cur, result, file} | {ok, side, present, values} | string
-- @purpose Test-only: samples getPerformanceLocal()'s per-window min/max/avg update period (ms) into a ring once per engine window, or replies the series' p50/p99/max and writes it to perf-local-<tag>.json, or reads the table now.
TK.register("perf.local", function(argv)
    local usage = "usage: perf.local <n> | read <tag> | now  (1 <= n <= 20000)"
    local a = argv[1]
    if a == "now" then
        local t = H0.perfTable()
        local out = { ok = t ~= nil, side = TK.side, present = getPerformanceLocal ~= nil, values = {} }
        if t ~= nil then
            for i = 1, #H0.PERF_KEYS do out.values[H0.PERF_KEYS[i]] = t[H0.PERF_KEYS[i]] end
        end
        return out
    end
    if a == "read" then
        local tag = argv[2]
        if tag == nil then return usage end
        local P = H0.perf
        if P == nil then return { ok = false, side = TK.side, reason = "perf.local not armed" } end
        local n = P.count
        if n > P.cap then n = P.cap end
        local j = 1
        if P.count > P.cap then j = P.next end
        local L = { wall = {}, frame = {}, min = {}, max = {}, avg = {}, cur = {}, mem = {} }
        for _k = 1, n do
            for key, arr in pairs(L) do arr[#arr + 1] = P[key][j] end
            j = j + 1
            if j > P.cap then j = 1 end
        end
        local out = { ok = true, side = TK.side, tag = tag, samples = n, recorded = P.count,
                      max = H0.summary(L.max), min = H0.summary(L.min), avg = H0.summary(L.avg), cur = H0.summary(L.cur) }
        local doc = {}
        for k, v in pairs(out) do doc[k] = v end
        doc.samples_list = L
        out.result = "perf-local-" .. tag
        out.file = "pzt-results/perf-local-" .. tag .. ".json"
        TK.result(out.result, doc)
        return out
    end
    local n = tonumber(a)
    if n == nil or n < 1 or n > H0.PERF_MAX or n ~= math.floor(n) then return usage end
    local hooks = H0.ensureHooks()
    H0.perf = { cap = n, next = 1, count = 0, wall = {}, frame = {}, min = {}, max = {}, avg = {}, cur = {}, mem = {} }
    return { ok = true, side = TK.side, armed = true, cap = n, present = getPerformanceLocal ~= nil, hooks = hooks }
end)

-- ---- ghosts -----------------------------------------------------------------------------------------------
function H0.copy(v, depth)
    if type(v) ~= "table" then return v end
    if depth > 24 then return nil end
    local c = {}
    for k, x in pairs(v) do c[k] = H0.copy(x, depth + 1) end
    return c
end

function H0.parseSched(s)
    if s == "burst" then return { kind = "burst", period = 1 } end
    if s == "drainTicks" then return { kind = "drainTicks", period = 1 } end
    local m = s and string.match(s, "^rr(%d+)$")
    if m ~= nil and tonumber(m) >= 1 then return { kind = "rr", m = tonumber(m), period = tonumber(m) } end
    local b = s and string.match(s, "^budget(%d+)$")
    if b ~= nil and tonumber(b) >= 1 then return { kind = "budget", cap = tonumber(b), period = 1 } end
    return nil
end

function H0.worldAge()
    local NR = NutritionRevamp
    if NR ~= nil and NR.worldAge ~= nil then
        local ok, v = pcall(NR.worldAge)
        if ok and type(v) == "number" then return v end
    end
    return 0
end

function H0.sscStub()
    local G = H0.g
    if G ~= nil then G.suppressed = G.suppressed + 1 end
end

function H0.syncWrap(p, n)
    local G = H0.g
    if G ~= nil then G.syncs = G.syncs + 1 end
    if H0.realSync ~= nil then return H0.realSync(p, n) end
end

function H0.beginBatch()
    H0.realSSC = sendServerCommand
    H0.realSync = sendSyncPlayerFields
    sendServerCommand = H0.sscStub
    if H0.realSync ~= nil then sendSyncPlayerFields = H0.syncWrap end
    H0.batchT0 = H0.now()
    H0.batchRuns = 0
end

function H0.endBatch()
    sendServerCommand = H0.realSSC
    if H0.realSync ~= nil then sendSyncPlayerFields = H0.realSync end
    local el = H0.now() - H0.batchT0
    local G = H0.g
    G.ms = G.ms + el
    H0.frameGhostMs = H0.frameGhostMs + el
    return el
end

-- one ghost's minute: P.work's own lines on the ghost's record, then the pipeline, then P.onMinute
function H0.work(g)
    local NR = NutritionRevamp
    local age = H0.worldAge()
    local r = g.rec
    r.lastSeen = age
    local okD, dead = TK.call(g.carrier, "isDead")
    if okD and dead == true and r.dead ~= true then r.dead = true end
    NR.server.minute.run(g.name, g.carrier, r)
    local P = NR.server.players
    if P ~= nil and P.onMinute ~= nil then
        for i = 1, #P.onMinute do pcall(P.onMinute[i], g.name, g.carrier, r) end
    end
end

function H0.runOne(g)
    local G = H0.g
    local ok, err = pcall(H0.work, g)
    if not ok then
        G.failures = G.failures + 1
        G.lastError = tostring(err)
    end
    g.runs = g.runs + 1
    g.lastRunMinute = G.minuteNo
    g.lastRunAge = H0.worldAge()
    G.runs = G.runs + 1
    H0.frameRuns = H0.frameRuns + 1
    H0.batchRuns = H0.batchRuns + 1
end

function H0.enqueueAll()
    local G = H0.g
    for i = 1, #G.ghosts do
        local g = G.ghosts[i]
        if not g.queued then
            g.queued = true
            G.qt = G.qt + 1
            G.q[G.qt] = g
        end
    end
end

function H0.pop()
    local G = H0.g
    if G.qh > G.qt then
        G.qh, G.qt = 1, 0
        return nil
    end
    local g = G.q[G.qh]
    G.q[G.qh] = nil
    G.qh = G.qh + 1
    g.queued = false
    return g
end

-- One batch: the sends swapped in, the body under pcall (so the restore always runs), the sends restored.
function H0.batch(body)
    H0.beginBatch()
    local ok, err = pcall(body)
    local el = H0.endBatch()
    if not ok then
        H0.g.failures = H0.g.failures + 1
        H0.g.lastError = "batch: " .. tostring(err)
    end
    return el
end

function H0.burstBody()
    local G = H0.g
    for i = 1, #G.ghosts do H0.runOne(G.ghosts[i]) end
end

function H0.rrBody()
    local G = H0.g
    local n = #G.ghosts
    local k = math.ceil(n / G.sched.m)
    for _i = 1, k do
        H0.runOne(G.ghosts[G.rot])
        G.rot = G.rot + 1
        if G.rot > n then G.rot = 1 end
    end
end

function H0.drainBody()
    local G = H0.g
    local k = 1
    if G.tpmLast ~= nil and G.tpmLast > 0 then k = math.ceil(#G.ghosts / G.tpmLast) end
    for _i = 1, k do
        local g = H0.pop()
        if g == nil then break end
        H0.runOne(g)
    end
end

function H0.budgetBody()
    local G = H0.g
    local cap = G.sched.cap
    local runCap = 1000000
    if G.meanMs ~= nil and G.meanMs > 0 then
        runCap = math.floor(cap / G.meanMs)
        if runCap < 1 then runCap = 1 end
    end
    local t0 = H0.batchT0
    local ran = 0
    while true do
        local g = H0.pop()
        if g == nil then break end
        H0.runOne(g)
        ran = ran + 1
        if ran >= runCap then break end
        if H0.now() - t0 >= cap then break end
    end
end

function H0.onMinuteLate()
    H0.minuteFlag = true
    local G = H0.g
    if G == nil or not G.active then return end
    if G.ticksSinceMinute ~= nil and G.minuteNo > 0 then G.tpmLast = G.ticksSinceMinute end
    G.ticksSinceMinute = 0
    -- starvation, counted before this minute's work: a ghost not run within its period
    local starved = 0
    for i = 1, #G.ghosts do
        local stale = G.minuteNo - G.ghosts[i].lastRunMinute
        if stale >= G.sched.period then starved = starved + 1 end
        if stale > G.maxStaleMinutes then G.maxStaleMinutes = stale end
    end
    G.starvedEvents = G.starvedEvents + starved
    if starved > 0 then G.starvedMinutes = G.starvedMinutes + 1 end
    G.minuteNo = G.minuteNo + 1
    local kind = G.sched.kind
    if kind == "burst" then
        H0.batch(H0.burstBody)
    elseif kind == "rr" then
        H0.batch(H0.rrBody)
    else
        H0.enqueueAll()
    end
end

function H0.drainTick()
    local G = H0.g
    if G.qh > G.qt then return end
    local kind = G.sched.kind
    if kind == "drainTicks" then
        H0.batch(H0.drainBody)
    elseif kind == "budget" then
        local el = H0.batch(H0.budgetBody)
        local ran = H0.batchRuns
        if ran > 0 then
            local per = el / ran
            if G.meanMs == nil then G.meanMs = per else G.meanMs = 0.8 * G.meanMs + 0.2 * per end
        end
    end
end

function H0.onTickLate()
    H0.frameNo = H0.frameNo + 1
    local G = H0.g
    if G ~= nil and G.active then
        if G.ticksSinceMinute ~= nil then G.ticksSinceMinute = G.ticksSinceMinute + 1 end
        if G.sched.kind == "drainTicks" or G.sched.kind == "budget" then H0.drainTick() end
        G.frames = G.frames + 1
        if H0.frameRuns > 0 then
            G.framesWithRuns = G.framesWithRuns + 1
            G.runsInFrames = G.runsInFrames + H0.frameRuns
            if H0.frameRuns > G.maxRunsFrame then G.maxRunsFrame = H0.frameRuns end
        end
    end
    local now = H0.now()
    if H0.ring ~= nil then H0.ringRecord(now) end
    if H0.perf ~= nil then H0.perfPoll(now) end
    H0.minuteFlag = false
    H0.frameRuns = 0
    H0.frameGhostMs = 0
end

function H0.online()
    local out = {}
    if getOnlinePlayers == nil then return out end
    local list = getOnlinePlayers()
    if list == nil then return out end
    for i = 0, list:size() - 1 do
        local p = list:get(i)
        out[#out + 1] = { name = p:getUsername(), p = p }
    end
    return out
end

-- @args <N> <burst|rr<m>|drainTicks|budget<ms>>
-- @reply {ok, side, N, ghosts, online, scheduler, period, carriers, names, hooks [, reason]} | string
-- @purpose Test-only: makes N minus the online count ghost records (deep copies of the online players' store records, held in the harness) and runs each ghost's minute pipeline against its real carrier under the named scheduler, its mirror send suppressed.
TK.register("ghost.load", function(argv)
    local usage = "usage: ghost.load <N> <burst|rr<m>|drainTicks|budget<ms>>"
    local N = tonumber(argv[1])
    local sched = H0.parseSched(argv[2])
    if N == nil or N ~= math.floor(N) or N < 1 or N > 500 or sched == nil then return usage end
    local out = { ok = false, side = TK.side, N = N, scheduler = argv[2] }
    if H0.g ~= nil and H0.g.active then
        out.reason = "ghosts already loaded; ghost.stop first"
        return out
    end
    local NR = NutritionRevamp
    if NR == nil or NR.server == nil or NR.server.minute == nil or NR.server.minute.run == nil
        or NR.server.store == nil or NR.server.store.attach == nil then
        out.reason = "NutritionRevamp.server.minute.run or .store is absent"
        return out
    end
    local records = NR.server.store.attach()
    if records == nil then
        out.reason = "the store is not attached"
        return out
    end
    local on = H0.online()
    out.online = #on
    local count = N - #on
    if #on == 0 or count < 1 then
        out.reason = "N must exceed the online count"
        return out
    end
    local carriers = {}
    for i = 1, #on do
        if records[on[i].name] == nil then
            out.reason = "no store record yet for " .. tostring(on[i].name)
            return out
        end
        carriers[#carriers + 1] = on[i].name
    end
    local G = { active = false, sched = sched, ghosts = {}, q = {}, qh = 1, qt = 0, rot = 1, minuteNo = 0,
                ticksSinceMinute = nil, tpmLast = nil, meanMs = nil, runs = 0, failures = 0, ms = 0, suppressed = 0,
                syncs = 0, starvedEvents = 0, starvedMinutes = 0, maxStaleMinutes = 0, frames = 0,
                framesWithRuns = 0, runsInFrames = 0, maxRunsFrame = 0, loadedAt = H0.now(),
                loadedAge = H0.worldAge() }
    local names = {}
    for i = 1, count do
        local c = on[((i - 1) % #on) + 1]
        local name = "ghost" .. tostring(i) .. "_" .. tostring(c.name)
        local rec = H0.copy(records[c.name], 0)
        rec.username = name
        G.ghosts[i] = { name = name, carrier = c.p, carrierName = c.name, rec = rec, runs = 0,
                        lastRunMinute = 0, lastRunAge = G.loadedAge, queued = false }
        names[#names + 1] = name
    end
    H0.g = G
    out.hooks = H0.ensureHooks()
    G.ticksSinceMinute = 0
    G.active = true
    out.ok = true
    out.ghosts = count
    out.period = sched.period
    out.carriers = carriers
    out.names = names
    return out
end)

function H0.stats()
    local G = H0.g
    local out = { ok = G ~= nil, side = TK.side }
    if G == nil then
        out.reason = "no ghosts loaded"
        return out
    end
    local age = H0.worldAge()
    local staleM, staleG, never = {}, {}, 0
    local maxG = 0
    for i = 1, #G.ghosts do
        local g = G.ghosts[i]
        staleM[i] = G.minuteNo - g.lastRunMinute
        staleG[i] = (age - g.lastRunAge) * 60
        if staleG[i] > maxG then maxG = staleG[i] end
        if g.runs == 0 then never = never + 1 end
    end
    local storeGhostKeys = 0
    local NR = NutritionRevamp
    local records = NR ~= nil and NR.server ~= nil and NR.server.store ~= nil and NR.server.store.records or nil
    if records ~= nil then
        for k in pairs(records) do
            if string.sub(tostring(k), 1, 5) == "ghost" then storeGhostKeys = storeGhostKeys + 1 end
        end
    end
    out.active = G.active
    out.scheduler = G.sched.kind
    out.m, out.cap, out.period = G.sched.m, G.sched.cap, G.sched.period
    out.ghosts = #G.ghosts
    out.runs, out.failures, out.lastError, out.ms = G.runs, G.failures, G.lastError, G.ms
    if G.runs > 0 then out.usPerRun = G.ms * 1000 / G.runs end
    out.minuteEvents = G.minuteNo
    out.tpmLast, out.meanMs = G.tpmLast, G.meanMs
    out.queued = G.qt - G.qh + 1
    out.starvedEvents, out.starvedMinutes, out.maxStaleMinutes = G.starvedEvents, G.starvedMinutes, G.maxStaleMinutes
    out.neverRun = never
    out.staleMinuteEvents = staleM
    out.staleGameMinutes = staleG
    out.maxStaleGameMinutes = maxG
    out.frames, out.framesWithRuns, out.maxRunsPerFrame = G.frames, G.framesWithRuns, G.maxRunsFrame
    if G.framesWithRuns > 0 then out.meanRunsPerRunFrame = G.runsInFrames / G.framesWithRuns end
    if G.frames > 0 then out.meanRunsPerFrame = G.runsInFrames / G.frames end
    out.suppressed, out.syncs = G.suppressed, G.syncs
    out.storeGhostKeys = storeGhostKeys
    out.wallSinceLoad = H0.now() - G.loadedAt
    out.gameMinutesSinceLoad = (age - G.loadedAge) * 60
    return out
end

-- @args (none)
-- @reply {ok, side, active, scheduler, m, cap, period, ghosts, runs, failures, lastError, ms, usPerRun, minuteEvents, tpmLast, meanMs, queued, starvedEvents, starvedMinutes, maxStaleMinutes, neverRun, staleMinuteEvents, staleGameMinutes, maxStaleGameMinutes, frames, framesWithRuns, maxRunsPerFrame, meanRunsPerRunFrame, meanRunsPerFrame, suppressed, syncs, storeGhostKeys, wallSinceLoad, gameMinutesSinceLoad} | {ok, side, reason}
-- @purpose Test-only: the ghost load's counters -- runs, failures, ms, starvation per minute event, per-ghost staleness, runs per frame, the suppressed sends and the store-leak guard.
TK.register("ghost.stats", function()
    return H0.stats()
end)

-- @args (none)
-- @reply {ok, side, stopped, cleared, stats} | {ok, side, reason}
-- @purpose Test-only: stops the ghost load (its scheduler goes idle), replies the final ghost.stats and clears the per-username transient tables the ghosts left in the mod.
TK.register("ghost.stop", function()
    local G = H0.g
    if G == nil then return { ok = false, side = TK.side, reason = "no ghosts loaded" } end
    G.active = false
    local stats = H0.stats()
    local NR = NutritionRevamp
    local cleared = 0
    local S = NR ~= nil and NR.server or nil
    local tabs = {}
    if S ~= nil then
        if S.bus ~= nil and S.bus.effects ~= nil then
            tabs[#tabs + 1] = S.bus.effects.dirty
            tabs[#tabs + 1] = S.bus.effects.last
        end
        if S.effects ~= nil then tabs[#tabs + 1] = S.effects.last end
        if S.intake ~= nil then
            tabs[#tabs + 1] = S.intake.lastIngested
            tabs[#tabs + 1] = S.intake.pendingAlc
            tabs[#tabs + 1] = S.intake.pendingCaf
        end
    end
    for i = 1, #G.ghosts do
        local name = G.ghosts[i].name
        for j = 1, #tabs do
            local t = tabs[j]
            if type(t) == "table" and t[name] ~= nil then
                t[name] = nil
                cleared = cleared + 1
            end
        end
    end
    G.q, G.qh, G.qt = {}, 1, 0
    return { ok = true, side = TK.side, stopped = true, cleared = cleared, stats = stats }
end)
