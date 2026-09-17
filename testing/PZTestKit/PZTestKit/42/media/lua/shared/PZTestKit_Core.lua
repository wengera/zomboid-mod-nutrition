-- PZTestKit core. Loads on the dedicated server and on every client (shared/).
--  * TK is a global on purpose: `reloadlua` re-runs this file and state must survive (S7).
--  * Command bus: the orchestrator writes <cachedir>/Lua/pzt-cmd.txt {seq, cmd, args};
--    each seq is executed once (last seq recovered from pzt-ack.txt after a Lua reset)
--    and answered in pzt-ack.txt {seq, cmd, result}. Same protocol on both sides.
--  * Results: TK.result(name, table) writes <cachedir>/Lua/pzt-results/<name>.json as one
--    complete JSON object; a parseable file IS the ready marker (S4).
--  * Reflective witness (slice 08): `witness.fields` and `witness.moddata` read any getter or
--    any modData key BY NAME on either side, so a new mod needs no new command. Registered
--    here, at the end of this file, and documented there.
TK = TK or {}
TK.version = 1
TK.commands = TK.commands or {}
TK.lastSeq = TK.lastSeq or 0
TK.ticks = TK.ticks or 0
TK.side = isServer() and "server" or (isClient() and "client" or "sp")

function TK.log(msg) print("PZTK: " .. tostring(msg)) end

function TK.now() return getTimestampMs and getTimestampMs() or 0 end

function TK.readKV(name)
    local reader = getFileReader(name, false)
    if not reader then return nil end
    local t = {}
    while true do
        local line = reader:readLine()
        if line == nil then break end
        local k, v = string.match(line, "^%s*([%w_%.]+)%s*=%s*(.-)%s*$")
        if k then t[k] = v end
    end
    reader:close()
    return t
end

function TK.writeKV(name, t)
    local w = getFileWriter(name, true, false)
    if not w then TK.log("cannot write " .. name); return false end
    for k, v in pairs(t) do w:write(k .. "=" .. tostring(v) .. "\n") end
    w:close()
    return true
end

-- ---- JSON (encode only) ----------------------------------------------------
local function jsonString(s)
    s = string.gsub(s, '[%c"\\]', function(c)
        if c == '"' then return '\\"' end
        if c == "\\" then return "\\\\" end
        if c == "\n" then return "\\n" end
        if c == "\t" then return "\\t" end
        if c == "\r" then return "\\r" end
        return string.format("\\u%04x", string.byte(c))
    end)
    return '"' .. s .. '"'
end

function TK.json(v, depth)
    depth = depth or 0
    if depth > 8 then return '"<too deep>"' end
    local t = type(v)
    if t == "nil" then return "null" end
    if t == "boolean" then return v and "true" or "false" end
    -- Slice 10 widened the non-integral branch from `string.format("%.6f", v)` to `tostring(v)`.
    -- WHY NOT `%.9g` / `%.17g` (the three candidates the ruling named): Kahlua implements its own
    -- string.format, and its `%g` is `StringLib.appendSignificantNumber` + `roundToSignificantNumbers`
    -- (`Math.round(x*10^k)/10^k` on the FRACTIONAL part) -- a reimplementation whose exactness
    -- cannot be established from the bytecode, and there is no way to run Kahlua offline here
    -- (the jar has one `main` -- se/krka/kahlua/threading/BlockingKahluaThread, a hardcoded
    -- 100-thread demo of `x = (x or 0) + 1`, not a script runner; 105 classes under se/krka/kahlua;
    -- the machine has a JRE with no javac and no jshell to drive LuaCompiler.loadstring).
    -- `tostring` is decidable and is exactly what is wanted: `KahluaUtil.tostring` -> `rawTostring`
    -- -> `numberToString` (jar-read, 42.20.4) is
    --     NaN -> "nan";  +/-Inf -> "inf"/"-inf";
    --     floor(d)==d and |d|<1e14 -> String.valueOf((long) d);   -- integers stay integers
    --     otherwise -> Double.toString(d)                         -- round-trips EXACTLY (JLS)
    -- so a float32 widened to a double (every packet-carried number) survives the bus intact
    -- instead of being quantised to six decimals. Integers are unaffected either way: the `%.0f`
    -- branch below still takes them first, and it keeps its own 1e15 cut-off.
    -- The two non-finite cases are the reason this branch still guards: JSON has no literal for
    -- either, and `tostring` would emit a bare `nan`/`inf` that no parser accepts, which would
    -- lose the WHOLE ack rather than one number. NaN answered `null` before this change and still
    -- does; +/-Inf produced an unparseable ack before it and answers `null` now.
    if t == "number" then
        if v ~= v then return "null" end
        if v == math.floor(v) and math.abs(v) < 1e15 then return string.format("%.0f", v) end
        if v * 0 ~= 0 then return "null" end     -- +/-Inf (finite*0 == 0; Inf*0 is NaN)
        return tostring(v)
    end
    if t == "string" then return jsonString(v) end
    if t == "table" then
        local n = #v
        local isArray = n > 0
        if isArray then
            for k in pairs(v) do if type(k) ~= "number" then isArray = false; break end end
        end
        local parts = {}
        if isArray then
            for i = 1, n do parts[#parts + 1] = TK.json(v[i], depth + 1) end
            return "[" .. table.concat(parts, ",") .. "]"
        end
        for k, val in pairs(v) do
            parts[#parts + 1] = jsonString(tostring(k)) .. ":" .. TK.json(val, depth + 1)
        end
        return "{" .. table.concat(parts, ",") .. "}"
    end
    return jsonString(tostring(v))   -- Java objects: their toString()
end

function TK.result(name, tbl)
    tbl = tbl or {}
    tbl.name, tbl.side, tbl.t, tbl.complete = name, TK.side, TK.now(), true
    local w = getFileWriter("pzt-results/" .. name .. ".json", true, false)
    if not w then TK.log("cannot write result " .. name); return false end
    w:write(TK.json(tbl))
    w:close()
    TK.log("result " .. name .. " written")
    return true
end

-- ---- probing Java objects safely --------------------------------------------
-- Calling a method a Java object does not have raises Kahlua's "tried to call nil".
-- `pcall` DOES catch that raise: it returns false plus the string
-- "tried to call nil java.lang.RuntimeException" on both sides (measured 2026-09-11, run
-- x126-20260911-045205). The older reading here - "it escapes pcall and kills the calling
-- event handler", from exp01-20260909-235420, which left no committed artifact - is
-- FALSIFIED in its first half and stays only as history.
-- The index-first guard is kept anyway, for the two reasons the same sessions measured:
--   * a CAUGHT nil call names nothing - no global, no file, no line, and the engine logs
--     nothing - so "this build does not expose the member" and "the member threw" would be
--     the same reply; the guard is what makes an absence visible (x126).
--   * an UNGUARDED nil call aborts the rest of the handler body it fires in, which here is
--     the bus poll, and on the -debug client it parks the process in the Lua debugger's
--     modal break (x127-20260911-052049: server VM for the abort, two boots for the
--     freeze). Handlers registered behind the raising one still run.
-- The rule, both halves and their bounds: docs/modding/lua-api.md section 5.
-- So probe by indexing first, exactly like the game's own ISItemEditPanel.lua:442.
-- Returns (present, value).
function TK.call(obj, name, ...)
    if obj == nil then return false, nil end
    local m = obj[name]
    if m == nil then return false, nil end
    return true, m(obj, ...)
end

function TK.field(obj, name)
    if obj == nil then return false, nil end
    local v = obj[name]
    if v == nil or type(v) == "function" then return false, nil end
    return true, v
end

-- ---- item state (both sides) ------------------------------------------------
-- Slice 02 moved this out of the client file: the SERVER owns item aging (Food.update gates
-- updateAge on GameServer.server, 02-notes Q8), so every real age/cooking reading has to be
-- taken on the server and compared against the client's copy. One table, read through
-- TK.call, so a key a build does not expose is simply absent rather than fatal.
-- Slice-01 keys are unchanged; the slice-02 additions are the aging/cooking block below.
TK.ITEM_STATE = {
    -- slice 01
    cooked = "isCooked", burnt = "isBurnt", rotten = "isRotten", frozen = "isFrozen",
    age = "getAge", hungChange = "getHungChange", baseHunger = "getBaseHunger",
    calories = "getCalories", carbs = "getCarbohydrates", lipids = "getLipids",
    proteins = "getProteins", id = "getID", uses = "getCurrentUsesFloat",
    -- slice 02: the aging/cooking/freezing fields, none of which travel in ItemStatsPacket
    -- except cooked/burnt/cookingTime/heat (02-notes Q8) -- which is exactly what the
    -- MP-ownership phase measures.
    fresh = "isFresh", offAge = "getOffAge", offAgeMax = "getOffAgeMax",
    freezingTime = "getFreezingTime", cookingTime = "getCookingTime", heat = "getHeat",
    minutesToCook = "getMinutesToCook", minutesToBurn = "getMinutesToBurn",
    thirstChange = "getThirstChange",
    -- getHungerChange() is NOT getHungChange(): the first is the read-time getter that applies
    -- the cooked/burnt/stale/rotten ladder, the second is the raw stored field that aging never
    -- touches (02-notes Q3). Recording only one of the pair makes "nothing moved" unreadable --
    -- it looks like rot has no effect on hunger, when in fact the effect is entirely at read
    -- time. `thirstChange` above is already the modified getter, so this makes the pair honest.
    hungerChange = "getHungerChange",
    -- slice 09: the cookable flag and the three weight readings, all READ-ONLY here (item.set
    -- deliberately offers no setter for any of them -- `customWeight` is a side effect of
    -- setActualWeight's caller, not a field a probe should force). They live here rather than
    -- only in `witness.fields` so item.get / item.set's before+after / item.update's `before`
    -- carry them too, which is what makes "who ran the cook transition" readable off one ack.
    -- Confirmed on the 42.20.4 jar, zombie/inventory/InventoryItem: isCookable()Z,
    -- getActualWeight()F, getWeight()F, isCustomWeight()Z (and Food overrides the first two).
    isCookable = "isCookable", actualWeight = "getActualWeight",
    weight = "getWeight", customWeight = "isCustomWeight",
    -- slice 09 fix round 1: the cook block's OWN gate. Food.update runs it at most once per
    -- game minute (`@86 L377`: GameTime.getMinutes() ~= lastCookMinute, stamped at
    -- `@104-@106 L381`), and slice 09's first session could not tell "the flip we sent opened
    -- the gate" from "the gate had already reopened on its own" because the stamped minute was
    -- never readable -- only the item.set that WROTE it. Read-only here: the setter already
    -- exists in ITEM_SETTERS, and this is its read-back. Jar-confirmed on 42.20.4,
    -- zombie/inventory/types/Food: getLastCookMinute()I (and setLastCookMinute(I)V).
    lastCookMinute = "getLastCookMinute",
}

function TK.itemState(it)
    if it == nil then return nil end
    local out = { fullType = it:getFullType() }
    for k, m in pairs(TK.ITEM_STATE) do
        local ok, v = TK.call(it, m)
        if ok then out[k] = v end
    end
    return out
end

-- ---- script-item values (both sides) ----------------------------------------
-- Moved here from the client file by slice 09 so the SERVER can answer `item.script` too.
-- Script data is loaded per side and never synced, so "the definition the client has" and
-- "the definition the server has" are two different readings and a teardown wants both --
-- the 09-11 plan's cold-start inventory already listed `item.script` under *server*, and
-- until this move that line was simply wrong (slice 09 Task 1, I3). One implementation, so
-- the two sides cannot drift and a cross-side diff means something.
--
-- MEASURED on 42.20.4 (slice 01): for Calories / Carbohydrates / Lipids / Proteins NONE of
-- the three routes below answers -- all four keys come back absent -- even though the jar
-- keeps them as public fields on the script Item (Item.InstanceItem reads them directly).
-- Kahlua does not expose them, so those per-item numbers have to come from an instantiated
-- item (`eat`'s itemBefore, or the server's `item.get`) or from parsing media/scripts.
TK.SCRIPT_GETTERS = { "HungerChange", "ThirstChange", "Calories", "Carbohydrates", "Lipids",
                      "Proteins", "DaysFresh", "DaysTotallyRotten", "IsCookable",
                      "MinutesToCook", "MinutesToBurn" }
local SCRIPT_FIELD = { Calories = "calories", Carbohydrates = "carbohydrates",
                       Lipids = "lipids", Proteins = "proteins" }

-- `getScriptManager` is checked for nil BEFORE it is called: an unguarded nil-global call
-- raises Kahlua's "tried to call nil" (see the note above TK.call) and aborts the rest of
-- the poll handler's body rather than answer the bus. Both server files carry the same guard.
local function scriptItem(fullType)
    if getScriptManager == nil then return nil, nil end
    local sm = getScriptManager()
    local ok, s = TK.call(sm, "getItem", fullType)
    if ok and s then return s, "getItem" end
    ok, s = TK.call(sm, "FindItem", fullType)      -- the form the game's own Lua uses
    if ok and s then return s, "FindItem" end
    return nil, nil
end

-- Tries get<X>(), then is<X>(), then the public field <x>; `access` records which answered,
-- `via` which accessor found the script, and `side` which side is talking.
function TK.scriptValues(fullType)
    local s, via = scriptItem(fullType)
    if not s then return nil end
    local out = { fullType = fullType, via = via, side = TK.side, access = {} }
    for _, g in ipairs(TK.SCRIPT_GETTERS) do
        local route, ok, v = "get", TK.call(s, "get" .. g)
        if not ok then
            route, ok, v = "is", TK.call(s, "is" .. g)
        end
        if not ok then
            route = "field"
            ok, v = TK.field(s, SCRIPT_FIELD[g] or
                                (string.lower(string.sub(g, 1, 1)) .. string.sub(g, 2)))
        end
        if ok and v ~= nil then out[g], out.access[g] = v, route end
    end
    return out
end

-- ---- perk levels (both sides) -----------------------------------------------
-- EvolvedRecipe.addItem reads chef:getPerkLevel(Perks.Cooking) and scales the dish's macros by
-- (1 + lvl/15) and its hunger by (1 - 0.03*lvl), so the level has to be pinned before any
-- recipe measurement (02-notes Q5, precondition 7).
--
-- Two calls, in the order the game's own debug UI uses (ISStatsAndBody.lua:229-230), because
-- they write different things and only the pair is consistent:
--   setPerkLevelDebug(perk, lvl) -> PerkInfo.level = lvl        (and, on a CLIENT only,
--                                   GameClient.sendPerks(player))
--   getXp():setXPToLevel(perk, lvl) -> xpMap[perk] = perk:getTotalXpForLevel(lvl)
-- setXPToLevel alone does NOT move getPerkLevel (measured: exp02-20260910-025434 read back 0
-- after it), and setPerkLevelDebug alone leaves the XP behind the level.
--
-- MEASURED: a client-only write does not survive in MP. The client pushes with sendPerks, but
-- the SERVER's copy of the character is still at the old level and wins within a second -- the
-- same ownership shape as Nutrition and hunger/thirst in slice 01. Pin the SERVER: measured in
-- exp02-20260910-030433, that write is on the client by the next bus command (its `before`
-- already reads the new level), so a client call after it is a no-op fallback, not a required
-- second half. Read `before` back on a further call to confirm the level held.
function TK.setPerk(p, name, level)
    local perk = Perks and Perks[name]
    if not perk then return { error = "no Perks." .. tostring(name) } end
    local out = { perk = name, requested = level, side = TK.side }
    local _, before = TK.call(p, "getPerkLevel", perk)
    out.before = before
    out.setPerkLevelDebug = TK.call(p, "setPerkLevelDebug", perk, level)
    local _, mid = TK.call(p, "getPerkLevel", perk)
    out.afterSetPerkLevelDebug = mid
    local _, xp = TK.call(p, "getXp")
    out.setXPToLevel = xp ~= nil and TK.call(xp, "setXPToLevel", perk, level) or false
    local _, after = TK.call(p, "getPerkLevel", perk)
    out.after = after
    if after ~= level then out.route = "none"
    elseif before == level then out.route = "already at level"
    elseif mid == level then out.route = "setPerkLevelDebug"
    else out.route = "getXp():setXPToLevel" end
    return out
end

-- ---- nutrition snapshot (both sides: client commands and the server's per-user ones) ----
-- Stats accessors moved with B42: the pre-B42 getHunger()/`.hunger` pair is gone and the
-- game's own Lua reads Stats:get(CharacterStat.HUNGER). Try that first, then the two older
-- forms; `statsApi` in the snapshot records which one answered (decision ledger evidence).
local function statValue(s, enumName, getter, field)
    local enum = CharacterStat and CharacterStat[enumName]
    if enum then
        local ok, v = TK.call(s, "get", enum)
        if ok and v ~= nil then return v, "Stats:get(CharacterStat." .. enumName .. ")" end
    end
    local ok, v = TK.call(s, getter)
    if ok and v ~= nil then return v, "Stats:" .. getter .. "()" end
    ok, v = TK.field(s, field)
    if ok then return v, "Stats." .. field end
    return nil, "none"
end

-- The three weight-DIRECTION flags (slice 10) are OPTIONAL reads and go through TK.call, unlike
-- the five macros above them, which are called directly on purpose (see the note above
-- TK.bodySnapshot: a build that lost getCalories must fail loudly rather than answer with no
-- calories). Jar-confirmed on 42.20.4, `zombie/characters/BodyDamage/Nutrition`:
--   isIncWeight()Z   isIncWeightLot()Z   isDecWeight()Z
-- They are what `Nutrition.updateWeight` sets and are NOT carried by PlayerStatsPacket
-- (`Nutrition.save` writes calories/carbs/lipids/proteins/weight only), so reading them on both
-- sides is the only way to see whether a client recomputes them from its mirrored macros.
-- `false` is a real reading here, so each key is written only when the member EXISTS
-- (TK.call's first return), never when it merely answered false.
local WEIGHT_FLAGS = { incWeight = "isIncWeight", incWeightLot = "isIncWeightLot",
                       decWeight = "isDecWeight" }

function TK.nutritionSnapshot(p)
    local n, s = p:getNutrition(), p:getStats()
    local hunger, api = statValue(s, "HUNGER", "getHunger", "hunger")
    local thirst = statValue(s, "THIRST", "getThirst", "thirst")
    local out = { calories = n:getCalories(), carbs = n:getCarbohydrates(), lipids = n:getLipids(),
                  proteins = n:getProteins(), weight = n:getWeight(), hunger = hunger,
                  thirst = thirst, statsApi = api }
    for key, getter in pairs(WEIGHT_FLAGS) do
        local ok, v = TK.call(n, getter)
        if ok then out[key] = v end
    end
    return out
end

TK.NUTRITION_SETTERS = { calories = "setCalories", carbs = "setCarbohydrates", lipids = "setLipids",
                         proteins = "setProteins", weight = "setWeight" }

-- ---- body snapshot (both sides) ---------------------------------------------
-- Slice 03. One ATOMIC read of everything the body-side rates are fitted against: the
-- nutrition block, the four stats, the five moodle levels, the five weight-band traits,
-- carry capacity, the food timer and the world clock -- all in the same Lua call, i.e. the
-- same game tick.
--
-- Why one command instead of the three the brief named (`time.snapshot` + `nutrition.get` +
-- `stats.get`): every rate in slice 03 is fitted as d<value>/d<worldAge>, and three separate
-- bus round-trips put up to ~1 s of wall time between the clock read and the calorie read.
-- At `settimespeed 30` on this fixture that is ~500 game-seconds of skew on a window that
-- only spans ~10 000 -- a 2-5 % rate error injected by the harness itself. Sampling all of
-- it in one tick removes that term entirely. `time.snapshot` is still called at session start
-- and after the teardown clock restore, as an independent read of getGameTime(); the CLIENT's
-- own `stats.get` is the convergence witness at each window boundary. `nutrition.get` is not
-- used by the body experiment at all -- this snapshot is a superset of it.
--
-- The OPTIONAL reads below go through TK.call, and each MoodleType / CharacterStat member is
-- nil-checked BEFORE it is passed in: handing a nil enum to a present Java method is an arity
-- or overload mismatch -- it raises and pcall catches it (lua-api.md section 5 row 2); the
-- guard keeps the reply informative (see TK.call). The reads
-- that are NOT wrapped are so on purpose -- `TK.nutritionSnapshot`'s `p:getNutrition()` block,
-- `TK.bodySnapshot`'s own `p:getStats()` (the handle every needs/endurance read below hangs
-- off) and `getGameTime():getWorldAgeHours()` are called directly, because every rate in the
-- slice is fitted against them and a build that lost one should fail loudly here rather than
-- return a snapshot that quietly has no calories, no stats or no clock.
TK.MOODLES = { hungry = "HUNGRY", thirst = "THIRST", foodEaten = "FOOD_EATEN",
               heavyLoad = "HEAVY_LOAD", endurance = "ENDURANCE" }
-- The trait STRINGS as CharacterTrait.<clinit> registers them ("Very Underweight" carries a
-- space, 03-notes Q4). They are used as SET KEYS against the character's own trait list, never
-- passed into a Java method: B42's `hasTrait` is called with a CharacterTrait everywhere in
-- the game's own Lua (ISBuildAction.lua:269 and 70 more), so handing it a String would risk
-- exactly that trap -- an arity or overload mismatch raises and pcall catches it (lua-api.md
-- section 5 row 2); the guard keeps the reply informative. `TK.traitNames` reads the
-- list instead -- `getCharacterTraits():getKnownTraits()` plus `trait:getName()`, the same
-- pair LastStandSetup.lua:126-128 uses to write a trait back out by name.
TK.WEIGHT_TRAITS = { obese = "Obese", overweight = "Overweight", underweight = "Underweight",
                     veryUnderweight = "Very Underweight", emaciated = "Emaciated" }
-- The four appetite/thirst traits row 9 flips: registered string -> CharacterTrait field.
TK.APPETITE_TRAITS = { HeartyAppetite = "HEARTY_APPETITE", LightEater = "LIGHT_EATER",
                       HighThirst = "HIGH_THIRST", LowThirst = "LOW_THIRST" }

-- The character's own traits, as a { [lowercased name] = true } set plus the raw ordered list.
-- Read-only and argument-safe: nothing here passes a value into a Java method.
-- MEASURED (smoke03-20260910-045044): `CharacterTrait:getName()` comes back LOWERCASED --
-- adding CharacterTrait.HEARTY_APPETITE puts "heartyappetite" in the list, and a weight of 105
-- puts "obese" there -- so the set is keyed lowercase and every lookup goes through
-- TK.hasTraitName. Matching the registry's own spelling ("HeartyAppetite", "Very Underweight")
-- would have read false on a trait that was demonstrably applied.
function TK.traitNames(p)
    local set, list = {}, {}
    local _, coll = TK.call(p, "getCharacterTraits")
    if coll == nil then return set, list, "no getCharacterTraits" end
    local ok, known = TK.call(coll, "getKnownTraits")
    if not ok or known == nil then return set, list, "no getKnownTraits" end
    local okS, n = TK.call(known, "size")
    if not okS or type(n) ~= "number" then return set, list, "no getKnownTraits():size()" end
    for i = 0, n - 1 do
        local okG, t = TK.call(known, "get", i)
        if okG and t ~= nil then
            local okN, name = TK.call(t, "getName")
            if okN and name ~= nil then
                set[string.lower(tostring(name))] = true
                list[#list + 1] = tostring(name)
            end
        end
    end
    return set, list, "getKnownTraits"
end

-- `set` from TK.traitNames, `name` in the registry's own spelling.
function TK.hasTraitName(set, name)
    return set[string.lower(tostring(name))] == true
end

function TK.bodySnapshot(p)
    if p == nil then return { error = "no player" } end
    local out = TK.nutritionSnapshot(p)          -- calories/carbs/lipids/proteins/weight/hunger/thirst
    local s = p:getStats()
    out.endurance = statValue(s, "ENDURANCE", "getEndurance", "endurance")
    out.fatigue = statValue(s, "FATIGUE", "getFatigue", "fatigue")
    local _, moodles = TK.call(p, "getMoodles")
    out.moodles = {}
    for key, name in pairs(TK.MOODLES) do
        local mt = MoodleType and MoodleType[name]
        if moodles ~= nil and mt ~= nil then
            local ok, lvl = TK.call(moodles, "getMoodleLevel", mt)
            if ok then out.moodles[key] = lvl end
        end
    end
    local set, list, route = TK.traitNames(p)
    out.traits = {}
    for key, name in pairs(TK.WEIGHT_TRAITS) do out.traits[key] = TK.hasTraitName(set, name) end
    for name in pairs(TK.APPETITE_TRAITS) do out.traits[name] = TK.hasTraitName(set, name) end
    out.traitList, out.traitRoute = list, route
    local okMW, mw = TK.call(p, "getMaxWeight")
    if okMW then out.maxWeight = mw end
    -- healthFromFoodTimer is what drives the FOOD_EATEN moodle (03-notes Q5); it has to be 0
    -- before any hunger-rate window or the rate is silently zeroed.
    local _, bd = TK.call(p, "getBodyDamage")
    if bd ~= nil then
        local okT, ft = TK.call(bd, "getHealthFromFoodTimer")
        if okT then out.foodTimer = ft end
        local okS, st = TK.call(bd, "getStandardHealthFromFoodTime")
        if okS then out.standardFoodTime = st end
    end
    local _, asleep = TK.call(p, "isAsleep");        out.asleep = asleep
    local _, running = TK.call(p, "IsRunning");      out.running = running
    local _, sprint = TK.call(p, "isSprinting");     out.sprinting = sprint
    local _, moving = TK.call(p, "isPlayerMoving");  out.moving = moving
    local gt = getGameTime()
    out.worldAge = gt:getWorldAgeHours()
    out.mult = gt:getMultiplier()
    out.wall = TK.now()
    return out
end

-- ---- writing stats (hunger/thirst) ------------------------------------------
-- Needed because CharacterStat.HUNGER/THIRST clamp to [0,1]: on a satiated character every
-- eat's hunger/thirst relief is silently discarded and dHunger/dThirst measure nothing.
-- B42 writes stats through the enum -- the game's own Lua is Stats:set(CharacterStat.HUNGER, v)
-- (ISAnimalContextMenu.lua:739, Tutorial/Steps.lua:548, server/ClientCommands.lua:897), which
-- also pins the arity at two -- so that is the primary route and set<Name>() the fallback.
-- The enum is read BEFORE the call and the route skipped when it is nil: handing a nil enum to
-- a present Java method is an arity or overload mismatch -- it raises and pcall catches it
-- (lua-api.md section 5 row 2); the guard keeps the reply informative.
-- Returns (ok, how): `how` names the route that answered, or why none did.
-- getStats() itself goes through TK.call: it was the one unguarded Java member on this path,
-- and on a subject without it (an entity the caller resolved wrongly, a build that moved the
-- accessor) it is a "tried to call nil" -- index-first guard: a caught nil call is silent and
-- names nothing; an unguarded raise aborts the rest of this handler (x126/x127), which here is
-- EveryOneMinute -- see docs/modding/lua-api.md section 5. Guarded, it returns a failed route
-- the caller can log instead.
TK.STAT_FIELDS = { hunger = { "HUNGER", "setHunger" }, thirst = { "THIRST", "setThirst" },
                   fatigue = { "FATIGUE", "setFatigue" }, endurance = { "ENDURANCE", "setEndurance" } }

function TK.setStat(p, field, value)
    local spec = TK.STAT_FIELDS[field]
    if not spec then return false, "unknown stat '" .. tostring(field) .. "'" end
    local _, s = TK.call(p, "getStats")
    if s == nil then return false, "no getStats()" end
    local enum = CharacterStat and CharacterStat[spec[1]]
    if enum and TK.call(s, "set", enum, value) then
        return true, "Stats:set(CharacterStat." .. spec[1] .. ")"
    end
    if TK.call(s, spec[2], value) then return true, "Stats:" .. spec[2] .. "()" end
    return false, "no Stats:set(CharacterStat." .. spec[1] .. ") and no Stats:" .. spec[2] .. "()"
end

-- "<field> <value> [<field> <value> ...]" starting at argv[first]. Reports per field so a
-- half-applied prime is visible in the results rather than silently wrong.
function TK.applyStats(p, argv, first)
    local applied, any = {}, false
    for i = first, #argv - 1, 2 do
        local v = tonumber(argv[i + 1])
        if v == nil then
            applied[tostring(argv[i])] = "not a number: " .. tostring(argv[i + 1])
        else
            local ok, how = TK.setStat(p, argv[i], v)
            applied[tostring(argv[i])] = (ok and how or ("failed: " .. tostring(how)))
            any = any or ok
        end
    end
    return applied, any
end

-- ---- command bus -----------------------------------------------------------
function TK.register(name, fn) TK.commands[name] = fn end

local function splitArgs(s)
    local out = {}
    for w in string.gmatch(s or "", "%S+") do out[#out + 1] = w end
    return out
end

function TK.pollCommands()
    local c = TK.readKV("pzt-cmd.txt")
    if not c or not c.seq then return end
    local seq = tonumber(c.seq) or 0
    if seq <= TK.lastSeq then return end
    TK.lastSeq = seq
    local name = c.cmd or ""
    TK.writeKV("pzt-ack.txt", { seq = seq, cmd = name, result = "running" })
    local fn = TK.commands[name]
    local ok, res
    if fn then ok, res = pcall(fn, splitArgs(c.args), c) else ok, res = false, "unknown command" end
    if type(res) == "table" then res = TK.json(res) end
    TK.log("cmd #" .. seq .. " " .. name .. " -> " .. tostring(res))
    TK.writeKV("pzt-ack.txt", { seq = seq, cmd = name, result = (ok and "ok:" or "err:") .. tostring(res) })
end

-- A Lua reset (client join) reloads this file: don't replay the last executed command.
do
    local ack = TK.readKV("pzt-ack.txt")
    if ack and ack.seq then TK.lastSeq = math.max(TK.lastSeq, tonumber(ack.seq) or 0) end
end

-- ---- commands available on both sides ---------------------------------------
TK.register("ping", function() return "pong" end)
TK.register("version", function() return "v" .. tostring(TK.version) .. " " .. TK.side end)
TK.register("result", function(argv)
    TK.result(argv[1] or "manual", { note = argv[2] })
    return "written"
end)
TK.register("state", function()
    return { ticks = TK.ticks, lastSeq = TK.lastSeq, version = TK.version, side = TK.side }
end)
TK.register("lua.reload", function(argv)
    local r = reloadLuaFile(argv[1])
    return "reloadLuaFile(" .. tostring(argv[1]) .. ") -> " .. tostring(r)
end)
TK.register("time.snapshot", function()
    local gt = getGameTime()
    return { worldAge = gt:getWorldAgeHours(), hour = gt:getHour(), minutes = gt:getMinutes(),
             mult = gt:getMultiplier(), wall = TK.now() }
end)
-- S3 probe: KeenPerception (workshop mod) removes the Keen Hearing <-> Deaf exclusivity.
TK.register("trait.check", function()
    local kh = CharacterTraitDefinition.getCharacterTraitDefinition(CharacterTrait.KEEN_HEARING)
    if not kh then return "no KEEN_HEARING definition" end
    local ex = kh:getMutuallyExclusiveTraits()
    return { keenHearingExcludesDeaf = ex:contains(CharacterTrait.DEAF),
             keenHearingExcludesHardOfHearing = ex:contains(CharacterTrait.HARD_OF_HEARING),
             keenPerceptionLoaded = not ex:contains(CharacterTrait.DEAF) }
end)

-- ---- generic reflective witness (both sides, slice 08) -----------------------
-- One command instead of a getter-specific one per mod: slices 09-11 probe fields nobody has
-- named yet. Every read goes through TK.call, so a member this build does not expose lands in
-- `missing` instead of raising Kahlua's "tried to call nil" - a raise that pcall does catch
-- but that names nothing, and that aborts the handler body when it is unguarded (see the
-- note above TK.call).
--
-- witness.fields <player|item> <id> <getter,getter,...>
--   <id> = username | "-" (the first online player) | fullType | "#<itemId>" | "<user>/<fullType>"
--   ZERO-ARGUMENT getters only: an arity mismatch is as fatal as a nil call (see TK.call), so
--   nothing here passes arguments to the member it reads.
--   -> { side, subject, id, resolved, fields = {<getter> = value}, missing = {...},
--        nils = {...}, count, worldAge [, truncatedAt] }
--   `count` is how many names were READ (the cap applies first); each read is sorted into one
--   of the three by outcome:
--     missing = this build's object does not expose the member at all (TK.call said absent);
--     nils    = it DOES expose it and the call returned nil -- a reading, not an absence;
--     fields  = anything else, encoded by TK.json (a Java object as its toString()).
--   `fields` is a MAP keyed by getter name, so a name asked for twice is read twice and
--   counted twice but appears ONCE; `missing`/`nils` are lists and keep the repeat. The three
--   therefore add up to `count` only when the requested names are distinct -- they are not a
--   partition, and nothing here de-duplicates the request.
--   Splitting `nils` out of "simply not in fields" is what makes "the mod did not set it"
--   distinguishable from "this build never had it", which is the whole question in 09-11.
--   A subject that does not RESOLVE still answers a table: { side, subject, id, resolved =
--   false, worldAge, error }. Only a missing/unknown <player|item> word answers the usage
--   string, so a caller never meets a bare string except on that gate.
--
-- witness.moddata [player[:<user>] | item:<id> | global:<name>] <key ...>
--   No scope prefix => player: the LOCAL player on a client, the first online one on the
--   server. Every reply carries the CENSUS -- `keys` is every top-level key as a sorted
--   "<name>:<type>" list -- so "*" or no key at all is a valid call, and is how a mod's
--   modData shape gets discovered before anyone knows a key to ask for. A key may be a
--   dotted path (`a.b.c`), which walks nested tables; a path that does not resolve is
--   `missing`, exactly as an unset key is.
--   -> { side, scope, arg, resolved, keys, keyCount, values = {<key> = value},
--        missing = {...}, count, worldAge [, error] [, truncatedAt] }
--   `count` is keys READ (the census is sized by `keyCount`); `values` is a map and repeats
--   collapse in it exactly as in witness.fields. A subject that does not resolve answers
--   `resolved = false` plus `error`, the same table shape as witness.fields.
--   The scope words are RESERVED in the FIRST argument: a bare `item` or `global` answers the
--   usage string, and a bare `player` is consumed as the scope. So a modData key literally
--   named `item`, `global` or `player` cannot be read at the default scope -- ask for it
--   behind an explicit prefix (`witness.moddata player:- player`), where it is just a key.
--   `global:<name>` reads through ModData.getOrCreate, which CREATES the table when it is
--   absent. A global census can therefore never report "no such table": an empty `keys` says
--   only that nothing stores anything under that name -- and the probe has just made it.
--
-- Both replies travel as one bus ack line, hence the TK.WITNESS_MAX cap on names per call.
-- getGameTime():getWorldAgeHours() and getOnlinePlayers() are reached DIRECTLY, on purpose and
-- for the same reason TK.bodySnapshot's block is (see the note at :240-247): a build that lost
-- either must fail loudly here rather than answer with no clock or no subject.
TK.WITNESS_MAX = 32                -- keeps one ack line inside the bus's key=value shape

-- ModData's Lua binding is a DOT call (`ModData.getOrCreate("t")`), so TK.call's colon
-- semantics would pass ModData itself as the first argument. Index first, then call, no self.
function TK.callStatic(tbl, name, ...)
    if tbl == nil then return false, nil end
    local f = tbl[name]
    if f == nil then return false, nil end
    return true, f(...)
end

-- kind = "player"|"item"; id = username | "-" | fullType | "#<itemId>" | "<user>/<fullType>".
-- Returns (subject, label) or (nil, nil, why).
local function subjectOf(kind, id)
    local user, what = string.match(tostring(id or ""), "^([^/]+)/(.+)$")
    if kind == "player" then
        if TK.side ~= "server" then                        -- a client only ever has its own
            if getPlayer == nil then return nil, nil, "no getPlayer() on side " .. tostring(TK.side) end
            local p = getPlayer()
            if p == nil then return nil, nil, "no local player" end
            return p, tostring(p:getUsername())
        end
        local list, want = getOnlinePlayers(), (user or id)
        if list == nil then return nil, nil, "getOnlinePlayers() returned nil" end
        for i = 0, list:size() - 1 do
            local p = list:get(i)
            if want == nil or want == "-" or p:getUsername() == want then return p, tostring(p:getUsername()) end
        end
        return nil, nil, "no online player " .. tostring(want)
    end
    local owner, label, err = subjectOf("player", user or "-")   -- `local function` recurses
    if owner == nil then return nil, nil, err end
    local _, inv = TK.call(owner, "getInventory")
    if inv == nil then return nil, nil, "no getInventory() on " .. tostring(label) end
    local target = what or id
    -- No id at all: `target` would go into getFirstTypeRecurse as a nil, and that member is
    -- OVERLOADED on this jar ((String) and (ItemKey)), so a nil is an ambiguous same-arity
    -- dispatch -- an arity or overload mismatch raises and pcall catches it (lua-api.md
    -- section 5 row 2); the guard keeps the reply informative. Refuse before the lookup
    -- instead, so nothing has to pay for the dispatch at all.
    if target == nil then return nil, nil, "usage: <id> required for an item subject" end
    local wantId = string.match(tostring(target), "^#(%d+)$")
    if wantId == nil then
        -- the harness's own idiom everywhere else, and the only route that looks inside bags
        local okR, it = TK.call(inv, "getFirstTypeRecurse", target)
        if okR and it ~= nil then
            local _, full = TK.call(it, "getFullType")
            local _, iid = TK.call(it, "getID")
            return it, tostring(label) .. "/" .. tostring(full) .. " #" .. tostring(iid)
        end
    end
    local _, items = TK.call(inv, "getItems")   -- flat, but the only route that matches by id
    if items == nil then return nil, nil, "no inventory list on " .. tostring(label) end
    for i = 0, items:size() - 1 do
        local it = items:get(i)
        local _, full = TK.call(it, "getFullType")
        local _, iid = TK.call(it, "getID")
        if (wantId ~= nil and tostring(iid) == wantId) or (wantId == nil and full == target) then
            return it, tostring(label) .. "/" .. tostring(full) .. " #" .. tostring(iid)
        end
    end
    return nil, nil, "no item " .. tostring(target) .. " on " .. tostring(label)
end

TK.register("witness.fields", function(argv)
    if argv[1] ~= "player" and argv[1] ~= "item" then
        return "usage: witness.fields <player|item> <id> <getter,...>"
    end
    local subject, label, err = subjectOf(argv[1], argv[2])
    -- A subject that does not resolve is a RESULT, not a usage error, so it answers the same
    -- table shape witness.moddata does: the driver reads reply.fields/reply.error without ever
    -- meeting a string. Only the argv[1] gate above (a missing/unknown subject word) is usage.
    if subject == nil then
        return { side = TK.side, subject = argv[1], id = argv[2] or "-", resolved = false,
                 worldAge = getGameTime():getWorldAgeHours(), error = err or "no subject" }
    end
    local out = { side = TK.side, subject = argv[1], id = argv[2] or "-", resolved = label,
                  fields = {}, missing = {}, nils = {},
                  worldAge = getGameTime():getWorldAgeHours() }
    local n = 0
    for name in string.gmatch(tostring(argv[3] or ""), "[^,]+") do
        -- counted BEFORE the read, so `count` is the number actually read and `truncatedAt`
        -- is the only signal that more were asked for.
        if n >= TK.WITNESS_MAX then out.truncatedAt = TK.WITNESS_MAX; break end
        n = n + 1
        local ok, v = TK.call(subject, name)
        if not ok then out.missing[#out.missing + 1] = name
        elseif v == nil then out.nils[#out.nils + 1] = name
        else out.fields[name] = v end
    end
    out.count = n
    return out
end)

-- The scope words that are NOT a subject: a bare `item`/`global`, and all three with a
-- trailing colon and nothing after it. See the gate inside the command below.
local BARE_SCOPE = { item = true, global = true,
                     ["player:"] = true, ["item:"] = true, ["global:"] = true }

TK.register("witness.moddata", function(argv)
    local first = tostring(argv[1] or "")
    local scope, arg = string.match(first, "^(player):(.+)$")
    if not scope then scope, arg = string.match(first, "^(item):(.+)$") end
    if not scope then scope, arg = string.match(first, "^(global):(.+)$") end
    -- A bare "item"/"global" -- or ANY of the three scope words with a trailing colon and no
    -- name, since all three patterns above require at least one character after the colon --
    -- would otherwise be read as a KEY on the default player scope and answer a
    -- plausible-looking census for the wrong subject. The trailing-colon half was slice 08's
    -- parked defect (docs/testing/README.md, witness block); slice 09 closes it while the
    -- harness is live. A bare "player" stays legal: it is consumed as the scope word.
    -- Lua patterns have no alternation, so the `^(player|item|global):?$` gate is a table.
    if not scope and BARE_SCOPE[first] then
        return "usage: witness.moddata [player[:<user>]|item:<id>|global:<name>] <key...>"
    end
    local from = (scope or first == "player") and 2 or 1
    scope = scope or "player"
    local out = { side = TK.side, scope = scope, arg = arg, values = {}, missing = {},
                  worldAge = getGameTime():getWorldAgeHours() }
    local tbl
    if scope == "global" then
        -- getOrCreate CREATES the table when it is absent, so a global census can never report
        -- "no such table": an empty `keys` is the answer for "nothing stores anything here".
        local ok, t = TK.callStatic(ModData, "getOrCreate", arg)
        if not ok then out.error = "no ModData.getOrCreate on this build"; return out end
        tbl = t
    else
        local subject, label, err = subjectOf(scope, arg or "-")
        -- `resolved = false` matches witness.fields' failure reply: both twins say resolved
        -- plus error, and `out` already carries side/worldAge from its constructor.
        if subject == nil then out.resolved = false; out.error = err or "no subject"; return out end
        out.resolved = label
        local ok, t = TK.call(subject, "getModData")
        if not ok then out.error = "no getModData() on " .. tostring(label); return out end
        tbl = t
    end
    -- pairs() on a Java object is an error rather than an empty census, and a nil table walks
    -- every key into `missing` as if the mod had simply not set them: say which it was.
    if type(tbl) ~= "table" then
        out.error = "modData is a " .. type(tbl) .. ", not a table"
        return out
    end
    local keys = {}                                -- the census: what a mod actually stores
    for k, v in pairs(tbl) do keys[#keys + 1] = tostring(k) .. ":" .. type(v) end
    table.sort(keys)
    out.keys, out.keyCount = keys, #keys
    local wanted = 0
    for i = from, #argv do
        if argv[i] ~= "*" then
            if wanted >= TK.WITNESS_MAX then out.truncatedAt = TK.WITNESS_MAX; break end
            wanted = wanted + 1
            local node = tbl
            for part in string.gmatch(argv[i], "[^%.]+") do    -- dotted paths walk nested tables
                node = (type(node) == "table") and node[part] or nil
            end
            if node == nil then out.missing[#out.missing + 1] = argv[i]
            else out.values[argv[i]] = (type(node) == "table") and node or tostring(node) end
        end
    end
    out.count = wanted        -- keys READ, as witness.fields' `count`; `keyCount` is the census
    return out
end)

-- ---- Lua globals (both sides, slice 11) --------------------------------------
-- lua.global <name>[.<field>...]
--   -> { side, name, resolved = true, type, value }               scalars and functions
--   -> { side, name, resolved = true, type = "table", keyCount }  tables
--   -> { side, name, resolved = false, failedAt [, stoppedOn] }   a path that does not resolve
--   -> { side, name, resolved = false, error = "no _G on this build" }   no failedAt: the walk
--                                                                 never started (guard 1)
--   -> "usage: ..."                                               no name, or a name with no
--                                                                 segments (guard 4)
--
-- Why it exists: nothing on the bus could read `_G`. A mod whose whole surface is Lua -- no
-- scripts, no server half, no modData it transmits -- has nothing else left to read once its
-- load-time state has been censused, and slice 11's question is WHICH PHYSICAL COPY of a file a
-- mod split across two media trees actually ran (`42.13/AutoCook.lua` defines
-- `AutoCook:acceptIngredient`; the `common/` copy of the same file does not). A global present
-- in only one of the two copies is the one reading that separates them. Slice 10 parked the
-- same gap for `SimpleStatus.VERSION` (testing/profiles/teardown-simplestatus.toml).
--
-- It READS, and it never calls. A function is reported as the string "function" -- that it
-- exists, and its type, never its result -- because calling an unknown global at unknown arity
-- is exactly the Kahlua raise TK.call exists to avoid (the note above TK.call).
-- No Java surface at all: `_G` is Kahlua's own global table and the dotted walk is the game's
-- own idiom -- `client/ISUI/ISXuiBuilder.lua:10-35` (`findFunction`) walks `_G` segment by
-- segment, guarding each hop with `type(container[v]) == "table"`.
--
-- Four guards, all deliberate:
--   * `_G` itself is nil-checked, the way text.get checks `getText` -- reading an absent global
--     is nil in Lua, never a raise, and it must be REPORTED rather than walked. That reply is
--     its own shape: `resolved = false` with an `error` and NO `failedAt`, because no segment
--     was ever tried -- a reader keying on `failedAt` must treat its absence as this case;
--   * a hop is taken only when the node is a `table`. pairs() and indexing on a Java-backed
--     object raise rather than answer (the note above the census loop at :737-738), so a
--     non-table node ENDS the walk: `failedAt` names the segment that could not be entered and
--     `stoppedOn` the type that stopped it. That is also why `keyCount` is gated on
--     `type(v) == "table"` and not on "it looks like it has keys";
--   * presence is `node == nil`, NEVER `if not node`. The first subject has
--     `AutoCook.Verbose = false` and `AutoCook.MaxSpices = -1`, and a truthiness test would
--     report the boolean false as missing -- reading a global's absence IS the command;
--   * a name that yields NO segments (`""`, or `"."`) answers the usage string rather than
--     censusing `_G` itself. `string.gmatch` on such a name iterates zero times, so the walk
--     would fall through with `node` still `_G` and report the whole global table as a hit --
--     the `parts == 0` gate after the loop is what stops that, and it is why a bare name and a
--     nil name give the same reply.
--
-- `TK.version` is the control a session should send first: TK is a global on purpose (see :2),
-- so it must resolve to the number 1 on BOTH sides, and a `resolved = false` there means the
-- walk itself is broken rather than the asked-for global being absent.
TK.register("lua.global", function(argv)
    local name = argv[1]
    if name == nil then return "usage: lua.global <name>[.<field>...]" end
    if _G == nil then
        return { side = TK.side, name = name, resolved = false, error = "no _G on this build" }
    end
    local out = { side = TK.side, name = name }
    local node, parts = _G, 0
    for part in string.gmatch(tostring(name), "[^%.]+") do
        parts = parts + 1
        if type(node) ~= "table" then
            out.resolved, out.failedAt, out.stoppedOn = false, part, type(node)
            return out
        end
        node = node[part]
        if node == nil then
            out.resolved, out.failedAt = false, part
            return out
        end
    end
    if parts == 0 then return "usage: lua.global <name>[.<field>...]" end
    local t = type(node)
    out.resolved, out.type = true, t
    if t == "table" then
        local n = 0
        for _k in pairs(node) do n = n + 1 end
        out.keyCount = n
    elseif t == "function" then
        out.value = "function"                 -- never called: the type IS the reading
    elseif t == "boolean" or t == "number" or t == "string" then
        out.value = node
    else
        out.value = tostring(node)             -- a Java object: its toString(), as TK.json does
    end
    return out
end)

-- ---- translation lookup (both sides; slice 10, moved here by slice 12) -------
-- text.get <translation key>
--   -> { key, text, miss, side }                            the lookup ran
--   -> { key, side, miss = true, null = true }              getText() returned Java NULL
--   -> { key, side, error = "no getText() on this build" }  no getText global on this side
--   -> "usage: ..."                                         no key given
--
-- Moved here from the client file by slice 12 so the SERVER answers it too -- the same move
-- slice 09 made for `item.script` (TK.scriptValues above), and for the same reason:
-- translation tables are loaded PER SIDE and never synced, so "the string the client has" and
-- "the string the server has" are two readings, not one. Registered ONCE, here: shared/ loads
-- before client/, so a client registration of the same name would silently shadow this one.
-- The SERVER half is UNPROVEN as of this commit -- no run has sent `text.get` to a dedicated
-- server yet. Slice 12's x121 M4 is the first read, and `no getText() on this build` is a
-- legitimate ANSWER there (the finding for question 4), not a bug to fix.
--
-- Why it exists (slice 10): a mod that ships no scripts, registers nothing server-side and
-- writes its one modData key only from UI input handlers has no state a bus command can read --
-- except its TRANSLATIONS, which are shared/ files the engine loads at start. This command is
-- what turns such a mod's `[[verify]]` probe from tier (b) (grep the mod's own console print out
-- of the client log) into tier (a) (read the mod's own effect through the bus).
-- `getText` is a Lua GLOBAL the engine exposes, not a member on an object, so TK.call / TK.field
-- (both of which index an object) do not apply. The nil-check-then-call is this harness's own
-- idiom for globals (`getScriptManager` at :217 in this file; `getSandboxOptions` at
-- client/PZTestKit_Client.lua:169, `getEvolvedRecipes` at client/PZTestKit_Client.lua:305) and
-- is safe: reading an undefined global is nil in Lua, never a raise.
-- Jar-confirmed on 42.20.4: `zombie/Lua/LuaManager$GlobalObject.getText(Ljava/lang/String;
-- [Ljava/lang/Object;)Ljava/lang/String;` -- varargs, and the game's own Lua calls it with one
-- argument everywhere. A MISS returns the KEY ITSELF (`Translator.getTextInternal`, the IGUI_
-- branch at @116-@138 L434-L435, null at @684-@685, `aload_0` return at @749-@750 L491), so
-- `text == key` is "no such key" and is reported as `miss` rather than left for the caller to
-- infer. That is also why a translated value is real evidence: it cannot be echoed from the
-- argument.
-- The NULL guard (slice 12, Task 3 review finding 2, landed ahead of the x121 session): the
-- return is a Java `String`, so a route that answers `null` arrives in Kahlua as `nil`, and the
-- old `tostring(getText(key))` turned that into the STRING `"nil"` -- which is neither the key
-- nor a translation, so `miss` came back FALSE and a null read as a hit. That is a false hit
-- exactly where x121's M4 grades on `miss`, so a nil return is now its own answer:
-- `miss = true` (it is certainly not a translation) beside `null = true` (and NO `text` key, so
-- a reader cannot mistake the string "nil" for one). `Translator.getTextInternal` is read as
-- returning the key on a miss, but the server half is unproven and this build's server route
-- is exactly what M4 measures -- so the shape it might answer with is recorded rather than
-- assumed away.
TK.register("text.get", function(argv)
    local key = argv[1]
    if key == nil then return "usage: text.get <translation key>" end
    if getText == nil then
        return { key = key, side = TK.side, error = "no getText() on this build" }
    end
    local t = getText(key)
    if t == nil then
        return { key = key, side = TK.side, miss = true, null = true }
    end
    local text = tostring(t)
    return { key = key, text = text, miss = (text == key), side = TK.side }
end)
TK.log("core loaded (" .. TK.side .. ")")
