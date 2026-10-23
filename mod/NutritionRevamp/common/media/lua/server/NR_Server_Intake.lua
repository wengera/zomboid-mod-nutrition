-- NR_Server_Intake.lua: the intake wrappers. ISEatFoodAction.complete and serverStop are wrapped server-side, so the
-- capture reads the item before Eat touches it (#1190) and again after: a multiplayer client never reaches complete
-- (#0109), and a cancel reaches Eat through serverStop (#0111). The drink and world-water seats are below.
-- Pitfalls:
--  * Each sentinel is a global of its own, never a field of NutritionRevamp, which NR_Core re-creates on every load
--    (#0943): a sentinel there would be wiped and the next install would wrap the wrapper.
--  * install() is idempotent (#1067) and re-wraps only when the class table it wrapped was re-created, so it never
--    re-wraps under another mod's later save-and-replace (QualityCooking's has no sentinel).
--  * The wrapper ALWAYS calls the saved original, outside the pcall: a mod bug never blocks an eat.
--  * The logic is read from NutritionRevamp.server.intake per call, so a reload swaps it under the installed wrapper.
--  * This server/ file also runs in the client VM (#0855): the side test is per call; Java globals are named only
--    inside functions; Java lists are walked with size()/get(i), never `#` (#0940).
-- Cadence: once per eat or cancel; a drink once per updateEat call (every tick plus the animation event, #0085). None
-- of it is on the per-tick stat path.
-- The landing every route shares (IN.land), in order: the per-minute ingested sum (as INGESTED, before the B12 ceiling);
-- the acute dose test; the B12 per-eat absorption ceiling (S0357); ethanol and caffeine moved to the gut lane's pending
-- sums (#2982), so neither enters the stomach; the stomach; the meal pool M.
-- The vector's source (IN.assemble): a dish's ingredients, else a craft map, else the item's own chain declared ->
-- table -> inferred -> missing; a script's macros have no getter, so inputs are read off a fresh instance (#2680).
local NR = NutritionRevamp
local K = NR.kernel
NR.server.intake = { wrapped = false, wrappedComplete = false, wrappedServerStop = false,
                     wrappedDrink = false, wrappedWorld = false, wired = false,
                     stats = { eats = 0, cancels = 0, sips = 0, worldSips = 0, landed = 0, failures = 0,
                               passthrough = 0, unreadableAfter = 0, acuteFlags = 0, acuteFailures = 0,
                               declaredMalformed = 0, creditFailures = 0, monotony = 0, monotonyHealed = 0, monotonyFailures = 0 },
                     lastIngested = {},
                     landed = {},
                     pendingAlc = {},
                     pendingCaf = {},
                     typeInfoCache = {},
                     itemTypeCache = {},
                     limitations = {
                         "a food outside the table takes a vector inferred from its FoodType's per-kcal medians over the pass's own mapped records (NR_Data_Infer.lua; a judgement); a declared NR_Nutrients script key (unrecognised by the loader, landing in default modData — #1281) takes precedence and its macros are the item's own",
                         "a landed vector's ethanol and caffeine wait in a transient server table until the next slow minute moves them to record.acute: a server stop in that minute loses them (the ingested day totals keep them)",
                         "a world-water drink lands at most the action's planned litres (waterUnit, sized from THIRST at its start); while the view holds THIRST, vanilla's updateUse re-transfers its cumulative target, so the SOURCE can lose more than was landed until the slow clock lands the water",
                         "a world-water source lands as the Water seed whatever its fluid (a tainted source included)",
                         "a drink's acute dose is tested per sip, not per drink: a dose split across sips can read a lower rung",
                     },
                     lastError = nil }
local IN = NR.server.intake

-- `or {}` keeps the table across a re-run; NR_Core's reset never touches it. Holds orig, wrapper and class.
NR_IntakeComplete_Installed = NR_IntakeComplete_Installed or {}
NR_IntakeServerStop_Installed = NR_IntakeServerStop_Installed or {}
NR_IntakeDrink_Installed = NR_IntakeDrink_Installed or {}
NR_IntakeWorld_Installed = NR_IntakeWorld_Installed or {}

-- ---------------------------------------------------------------------------------------------------
-- The pure helpers: no Java, tested on the lupa host.

-- The eat's pure arithmetic is the kernel's (K.intake); each public name here is a thin wrapper, so every caller and
-- shape test reaches the same code.
IN.shareEaten = K.intake.shareEaten
-- A thirst-only Food takes them from its raw thirst and the type's script thirst.
IN.fractionOf = K.intake.fractionOf

IN.isFinite = NR.finite

-- A finished item reads NaN, not 0 (#2832: Eat zeroes hungChange, then consumeHunger(0) writes 0/0), so a non-finite
-- after-reading against a numeric before-reading reads 0 and the whole remainder lands.
function IN.afterReading(before, after)
    if type(before) == "number" and not IN.isFinite(after) then return 0 end
    return after
end

-- An UNREADABLE after-reading also maps to 0, but it is not the vanilla 0/0, so it is made visible.
function IN.isUnreadableAfter(before, after)
    return type(before) == "number" and type(after) ~= "number"
end

-- A NaN landed in the stomach would poison the buffer, pool and HUNGER for the session (#2833).
function IN.firstNonFinite(vec)
    local keys = K.vector.KEYS
    for i = 1, #keys do
        local k = keys[i]
        if not IN.isFinite(vec[k]) then return k end
    end
    return nil
end

-- Allocated the first time a username lands in a minute; NR_Server_Nutrients reads it and sets the slot to nil.
function IN.addIngested(username, vec)
    local sum = IN.lastIngested[username]
    if sum == nil then
        sum = K.vector.new()
        IN.lastIngested[username] = sum
    end
    local keys = K.vector.KEYS
    for i = 1, #keys do
        local k = keys[i]
        sum[k] = (sum[k] or 0) + (vec[k] or 0)
    end
    return sum
end

-- So the new character's first Nutrients minute never inherits a drink landed in the death minute.
function IN.forget(username)
    local tables = { IN.pendingAlc, IN.pendingCaf, IN.lastIngested }
    for i = 1, 3 do
        if tables[i] ~= nil then tables[i][username] = nil end
    end
end

-- Against the body mass and the pre-eat food fill; a rung keeps a still-live flag's higher rung. No records or no
-- body tests nothing. Returns the number of keys flagged.
function IN.acuteAtEat(record, vec, records)
    records = records or (NR.data and NR.data.records)
    if records == nil or record == nil then return 0 end
    local body = record.body
    if body == nil then return 0 end
    local w = (body.fm or 0) + (body.lm or 0) + (body.lx or 0)
    if not IN.isFinite(w) or w <= 0 then return 0 end
    local fill = K.stomach.recordFoodFill(record)
    if record.nutrients == nil then record.nutrients = K.nutrients.newState(records) end
    local n = record.nutrients
    local order = records.ORDER
    local flagged = 0
    for i = 1, #order do
        local key = order[i]
        local rec = records.REC[key]
        if rec ~= nil and rec.acute ~= nil and rec.key ~= nil then
            local rung = K.nutrients.acuteTest(rec, vec[rec.key] or 0, w, fill)
            if rung > 0 then
                local st = n[key]
                if st == nil then
                    st = K.nutrients.newKey()
                    n[key] = st
                end
                if st.ax > 0 and st.axr > rung then rung = st.axr end
                st.ax = K.nutrients.ACUTE_DECAY_H
                st.axr = rung
                flagged = flagged + 1
            end
        end
    end
    return flagged
end

-- The header's steps. The record's stomach must exist; the acute test's raise is counted and the landing goes on.
function IN.land(record, username, vec, lane, mlPerG)
    IN.landed[username] = true                     -- the writer's sip fold skips this minute
    if NR.server.store ~= nil and NR.server.store.mark ~= nil then NR.server.store.mark(username) end -- saved at the next store step
    IN.addIngested(username, vec)
    local ok, flagged = pcall(IN.acuteAtEat, record, vec)
    if ok then
        IN.stats.acuteFlags = IN.stats.acuteFlags + flagged
    else
        IN.stats.acuteFailures = IN.stats.acuteFailures + 1
        IN.lastError = "acute test failed: " .. tostring(flagged)
        NR.log.say(2, "intake: " .. IN.lastError)
    end
    vec.vitB12 = K.interact.b12Ceiling(vec.vitB12 or 0)
    IN.pendingAlc[username] = (IN.pendingAlc[username] or 0) + (vec.ethanol or 0)
    IN.pendingCaf[username] = (IN.pendingCaf[username] or 0) + (vec.caffeine or 0)
    vec.ethanol = 0
    vec.caffeine = 0
    if lane == "liquid" then
        K.stomach.ingestLiquid(record.stomach, vec)
    else
        K.stomach.ingest(record.stomach, vec, mlPerG)
    end
    IN.feed(record, vec)
    return vec
end

-- M is fed at the eat
-- on every route that lands -- the eat, the drink, world water and the reconcile path. An absent or non-finite M is
-- left for the writer's seed; a feed that comes out non-finite is not kept.
function IN.feed(record, vec)
    local s = record.satiety
    if type(s) ~= "table" or not IN.isFinite(s.M) then return end
    local M = K.satiety.mealFeed(s.M, vec)
    if IN.isFinite(M) then s.M = M end
end

IN.sourceOf = K.intake.sourceOf

-- An unrecognised script key lands in default modData as a String unless it parses as a Double (#1281).
function IN.declaredOf(md)
    if type(md) ~= "table" then return nil end
    local v = md.NR_Nutrients
    if type(v) == "string" then return v end
    return nil
end

IN.chainOne = K.intake.chainOne

IN.newTrace = K.intake.newTrace
IN.traceStep = K.intake.traceStep

-- The closure lives here: the kernel's lookup-taking functions call it without knowing (no closure in the kernel).
function IN.chainedLookup(lookup, templates, info, trace)
    return function(fullType)
        local i = nil
        if info ~= nil then i = info(fullType) end
        local vec, step, note = IN.chainOne(fullType, lookup, templates, i)
        IN.traceStep(trace, fullType, step, note)
        return vec
    end
end

-- The hand-craft consumed map (#2667). Keys must name an item type (IN.isItemType), so another mod's dotted modData key
-- never turns a food into a craft.
function IN.craftMap(md)
    if type(md) ~= "table" then return nil end
    local out, n = {}, 0
    for k, v in pairs(md) do
        if type(k) == "string" and type(v) == "number" and string.sub(k, 1, 3) ~= "NR_"
                and string.find(k, "^[^%.%s]+%.[^%.%s]+$") ~= nil and IN.isItemType(k) then
            out[k] = v
            n = n + 1
        end
    end
    if n == 0 then return nil end
    return out
end

-- /5 when burnt.
IN.macrosEaten = K.intake.macrosEaten

-- See K.intake.assemble for the share and frac semantics. The adapter builds the per-eat trace and the chained-lookup
-- closure only for a dish or a craft, the two sources that read inputs.
function IN.assemble(b, rawAfter, lookup, thirstAfter, templates, info)
    local trace = IN.newTrace()
    local inputs = nil
    if (b.extraTypes ~= nil and #b.extraTypes > 0) or b.craftMap ~= nil then
        inputs = IN.chainedLookup(lookup, templates, info, trace)   -- a dish or a craft: the one closure per eat
    end
    return K.intake.assemble(b, rawAfter, lookup, thirstAfter, templates, inputs, trace)
end

-- ---------------------------------------------------------------------------------------------------
-- The engine edge: every Java member through the index-first guard (NR.call).

local function read(obj, name, ...)
    local ok, v = NR.call(obj, name, ...)
    if ok then return v end
    return nil
end

local function num(v)
    if type(v) == "number" then return v end
    return 0
end

local worldAge = NR.worldAge          -- nil on a failed clock read: store.get answers nil and the eat is counted

function IN.foodTypeOf(item)
    local ft = read(item, "getFoodType")
    if type(ft) == "string" and ft ~= "" then return ft end
    return nil
end

-- nil when the item has no calories getter (not a Food).
function IN.foodInfo(item)
    local cal = read(item, "getCalories")
    if type(cal) ~= "number" then return nil end
    local macros = { calories = cal, carbs = num(read(item, "getCarbohydrates")),
                     lipids = num(read(item, "getLipids")), proteins = num(read(item, "getProteins")) }
    return { declared = IN.declaredOf(read(item, "getModData")), foodType = IN.foodTypeOf(item),
             macros = macros }
end

-- A fresh instance through the instanceItem global (InventoryItemFactory is not exposed, #2680), cached per type per
-- boot (false for a non-Food).
function IN.typeInfo(fullType)
    local cached = IN.typeInfoCache[fullType]
    if cached == false then return nil end
    if cached ~= nil then return cached end
    if instanceItem == nil then return nil end
    local info = false
    local ok, item = pcall(instanceItem, fullType)
    if ok and item ~= nil then
        local okI, fi = pcall(IN.foodInfo, item)   -- a raising getter on the fresh instance caches false
        if okI then info = fi or false end
    end
    IN.typeInfoCache[fullType] = info
    if info == false then return nil end
    return info
end

-- Cached per type per boot (#2680); without the global nothing can be checked: true, uncached.
function IN.isItemType(fullType)
    local cached = IN.itemTypeCache[fullType]
    if cached ~= nil then return cached end
    if instanceItem == nil then return true end
    local ok, item = pcall(instanceItem, fullType)
    local known = ok and item ~= nil
    IN.itemTypeCache[fullType] = known
    return known
end

-- nil with no item, character or username, or not a Food.
function IN.readBefore(action)
    local item, char = action.item, action.character
    if item == nil or char == nil then return nil end
    local username = read(char, "getUsername")
    if username == nil then return nil end
    local rawBefore = read(item, "getHungChange")          -- the RAW stored hunger (#0002)
    if type(rawBefore) ~= "number" then return nil end
    local b = { item = item, username = username, rawBefore = rawBefore, player = char }   -- player: the store's sight key
    b.fullType = tostring(read(item, "getFullType"))
    b.instBase = num(read(item, "getBaseHunger"))
    b.thirstBefore = read(item, "getThirstChangeUnmodified") -- the RAW thirst (#0005), never the ladder
    b.cal = num(read(item, "getCalories"))
    b.carb = num(read(item, "getCarbohydrates"))
    b.lip = num(read(item, "getLipids"))
    b.pro = num(read(item, "getProteins"))
    b.cooked = read(item, "isCooked") == true
    b.burnt = read(item, "isBurnt") == true
    b.rotten = read(item, "isRotten") == true
    b.frozen = read(item, "isFrozen") == true
    -- the script hunger, a bare read in script points (#2678): /100 to the instance's units
    local script = read(item, "getScriptItem")
    local scriptHunger = read(script, "getHungerChange")
    b.scriptHunger = 0
    if type(scriptHunger) == "number" then b.scriptHunger = scriptHunger / 100 end
    -- the script thirst, the same shape (#0011): a thirst-only Food's whole-instance denominator
    local scriptThirst = read(script, "getThirstChange")
    b.scriptThirst = 0
    if type(scriptThirst) == "number" then b.scriptThirst = scriptThirst / 100 end
    b.extraTypes = {}
    if read(item, "haveExtraItems") == true then
        local list = read(item, "getExtraItems")
        local n = num(read(list, "size"))
        local i = 0
        while i < n do
            local t = read(list, "get", i)
            if t ~= nil then b.extraTypes[#b.extraTypes + 1] = tostring(t) end
            i = i + 1
        end
    end
    local md = read(item, "getModData")
    b.craftMap = IN.craftMap(md)
    b.declared = IN.declaredOf(md)
    b.foodType = IN.foodTypeOf(item)
    b.macros = { calories = b.cal, carbs = b.carb, lipids = b.lip, proteins = b.pro }
    return b
end

function IN.readAfterAndLand(b)
    -- a finished item reads NaN here, not 0 (#2832, vanilla's 0/0 in consumeHunger): normalised to 0
    local rawRead = read(b.item, "getHungChange")
    local rawAfter = IN.afterReading(b.rawBefore, rawRead)
    -- the raw thirst again (#0005), the same normalisation
    local thirstRead = read(b.item, "getThirstChangeUnmodified")
    local thirstAfter = IN.afterReading(b.thirstBefore, thirstRead)
    -- an unreadable after-read is treated as finished but counted and named: it is not the known vanilla 0/0
    if IN.isUnreadableAfter(b.rawBefore, rawRead) or IN.isUnreadableAfter(b.thirstBefore, thirstRead) then
        IN.stats.unreadableAfter = IN.stats.unreadableAfter + 1
        IN.lastError = "after-read unreadable; treated as finished: " .. tostring(b.fullType)
        NR.log.say(2, "intake: " .. IN.lastError)
    end
    if NR.data == nil or NR.data.nutrients == nil then error("intake: NR.data.nutrients absent") end
    local vec, source, missing, share, frac, trace = IN.assemble(b, rawAfter, NR.data.nutrients.get,
        thirstAfter, NR.data.infer, IN.typeInfo)
    -- a malformed declared string fell through to the table: counted and named, never silent
    if #trace.malformed > 0 then
        IN.stats.declaredMalformed = IN.stats.declaredMalformed + #trace.malformed
        IN.lastError = "NR_Nutrients malformed, ignored: " .. table.concat(trace.malformed, "; ")
        NR.log.say(2, "intake: " .. IN.lastError)
    end
    if #trace.unknown > 0 then
        NR.log.say(2, "intake: NR_Nutrients unknown keys skipped: " .. table.concat(trace.unknown, "; "))
    end
    -- the landing guard: nothing non-finite reaches the stomach (#2833)
    local bad = nil
    if not IN.isFinite(share) then
        bad = "share"
    elseif not IN.isFinite(frac) then
        bad = "frac"
    elseif vec ~= nil then
        bad = IN.firstNonFinite(vec)
    end
    if bad ~= nil then return IN.reject(bad) end
    if vec == nil then return nil end                      -- a cancel under vanilla's guards, or a no-op
    local record = NR.server.store.get(b.username, worldAge(), b.player)
    if record == nil then error("intake: no store record for " .. tostring(b.username)) end
    record.stomach = record.stomach or K.stomach.new()  -- an empty stomach, as kinetics lays it
    record.pool = record.pool or K.vector.new()
    IN.land(record, b.username, vec, nil, IN.volumeOf(b.fullType))
    IN.atEat(record, b, vec.calories)                      -- monotony: mood, never hunger
    record.lastIntake = { fullType = b.fullType, source = source, share = share, frac = frac,
                          missing = missing, declared = trace.declared, inferred = trace.inferred,
                          plain = b.plain, class = b.class, allies = b.allies and b.allies.scale or 1 }
    IN.stats.landed = IN.stats.landed + 1
    NR.log.say(3, "intake: " .. b.fullType .. " for " .. tostring(b.username) .. " source " .. source
        .. " share " .. tostring(share))
    return vec
end
function IN.reject(key)
    IN.stats.failures = IN.stats.failures + 1
    IN.lastError = "non-finite intake rejected: " .. tostring(key)
    NR.log.say(2, "intake: " .. IN.lastError)
    return nil
end

-- Each half under its own pcall; the original runs between them, outside.
function IN.guardBefore(action, kind, ...)
    local readFn = IN.readBefore
    if kind == "cancel" then
        IN.stats.cancels = IN.stats.cancels + 1
    elseif kind == "drink" then
        IN.stats.sips = IN.stats.sips + 1             -- one per updateEat call
        readFn = IN.readDrinkBefore
    elseif kind == "world" then
        IN.stats.worldSips = IN.stats.worldSips + 1   -- one per transferFluid call
        readFn = IN.readWorldBefore
    else
        IN.stats.eats = IN.stats.eats + 1
    end
    local ok, b = pcall(readFn, action, ...)
    if ok then
        IN.storesBefore(b, action)
        IN.hedonicsBefore(b, kind)
        return b
    end
    IN.stats.failures = IN.stats.failures + 1
    IN.lastError = b
    NR.log.say(2, "intake: capture failed before the " .. kind .. ": " .. tostring(b))
    return nil
end

function IN.guardAfter(b, kind)
    IN.hedonicsAfter(b, kind)
    local landFn = IN.readAfterAndLand
    if kind == "drink" then landFn = IN.readDrinkAfterAndLand end
    if kind == "world" then landFn = IN.readWorldAfterAndLand end
    local ok, err = pcall(landFn, b)
    if ok then
        if err ~= nil then IN.creditStores(b) end
        return
    end
    IN.stats.failures = IN.stats.failures + 1
    IN.lastError = err
    NR.log.say(2, "intake: capture failed after the " .. kind .. ": " .. tostring(err))
end

-- The reconciliation credit: the macro stores' movement across the wrap (the engine's own Eat or DrinkFluid write) is
-- credited to the reconcile baseline, so the next slow minute does not land the intake twice; a rise by another writer
-- stays visible. A landing that lands nothing credits nothing.
function IN.storesBefore(b, action)
    if type(b) ~= "table" or type(action) ~= "table" then return end
    local RC = NR.server.reconcile
    if RC == nil or RC.read == nil then return end
    local ok, st = pcall(RC.read, action.character)
    if ok then
        b.nrStores = st
        b.nrChar = action.character
    else
        IN.stats.creditFailures = IN.stats.creditFailures + 1
    end
end

function IN.creditStores(b)
    if type(b) ~= "table" or b.nrStores == nil then return false end
    local ok, done = pcall(IN.credit, b)
    if not ok then
        IN.stats.creditFailures = IN.stats.creditFailures + 1
        IN.lastError = "reconcile credit failed: " .. tostring(done)
        NR.log.say(2, "intake: " .. IN.lastError)
        return false
    end
    return done
end

function IN.credit(b)
    local RC = NR.server.reconcile
    local after = RC.read(b.nrChar)
    if after == nil then return false end
    local record = NR.server.store.get(b.username, worldAge(), b.player)
    return RC.credit(record, b.nrStores, after)
end

-- Names nothing from this file's load: the sentinel is a persistent global and the logic is looked up per call.
local function makeWrapper(S, kind)
    return function(self, ...)
        local nr = NutritionRevamp
        local intake = nil
        if nr ~= nil and nr.server ~= nil then intake = nr.server.intake end
        local b = nil
        if intake ~= nil and nr.isServer ~= nil and nr.isServer() then
            b = intake.guardBefore(self, kind, ...)
        elseif intake ~= nil then
            intake.stats.passthrough = intake.stats.passthrough + 1 -- the client
        end
        local result = S.orig(self, ...)                   -- every path; never inside a pcall
        if b ~= nil then intake.guardAfter(b, kind) end
        return result
    end
end

local function installOne(S, cls, clsName, method, kind)
    return NR.installWrap(S, cls, method, makeWrapper, kind, "intake: " .. clsName .. "." .. method)
end

local function mirror()
    local cls = ISEatFoodAction
    local C, T = NR_IntakeComplete_Installed, NR_IntakeServerStop_Installed
    IN.wrappedComplete = cls ~= nil and C.wrapper ~= nil and C.class == cls
    IN.wrappedServerStop = cls ~= nil and T.wrapper ~= nil and T.class == cls
    IN.wrapped = IN.wrappedComplete and IN.wrappedServerStop
    return IN.wrapped
end

function IN.install()
    if ISEatFoodAction == nil then
        mirror()
        return false
    end
    installOne(NR_IntakeComplete_Installed, ISEatFoodAction, "ISEatFoodAction", "complete", "eat")
    installOne(NR_IntakeServerStop_Installed, ISEatFoodAction, "ISEatFoodAction", "serverStop", "cancel")
    return mirror()
end

-- ---------------------------------------------------------------------------------------------------
-- The drink wrapper: ISDrinkFluidAction.updateEat, the action's ONE DrinkFluid call (#2689); wrapping complete too
-- would count the last sip twice (complete is updateEat(1)).
--  * Each call consumes only the gap to the target ratio (#0085), so litres before minus after, summed, is the whole drink.
--  * The mix is sampled BEFORE the call (the removal returns the aggregate only, #2688); the sample is pooled and
--    released before the original runs.
--  * No retention or macro override: DrinkFluid writes the fluid's own per-litre Properties (#0064).
-- limitations:
--  * A drink straight from a world source goes through ISTakeWaterAction (#2690), captured by the world-water wrapper.
--  * A MULTI-output craft or an entity craft (furnaces, racks) carries no consumed map and falls back to dish or
--    baseline (#2667).
--  * A LATER mod that replaces a wrapped method WITHOUT calling the saved original removes the capture silently; only
--    NR.server.intake.stats.eats standing still reveals it (#2842).
--  * The consumed map counts INSTANCES, not uses, so a partly-used input lands its whole seed (#0709).

-- The litres one updateEat call removed: before - after, floored at 0; a nil on either side -> 0.
function IN.litresDrunk(before, after)
    if type(before) ~= "number" or type(after) ~= "number" then return 0 end
    return K.max(before - after, 0)
end

-- mix is the before-read's Lua array of { fluidTypeString, proportion }; an unknown type goes to missing.
function IN.fluidVector(lookup, mix, litres)
    local vec = K.vector.new()
    local missing = {}
    for i = 1, #mix do
        local typeStr, proportion = mix[i][1], mix[i][2]
        local seed = lookup(typeStr)
        if seed == nil then
            missing[#missing + 1] = typeStr
        else
            K.vector.add(vec, seed, proportion * litres)
        end
    end
    return vec, missing
end

-- nil with no item, character, username or container, or an empty one.
function IN.readDrinkBefore(action)
    local item, char = action.item, action.character
    if item == nil or char == nil then return nil end
    local username = read(char, "getUsername")
    if username == nil then return nil end
    local fc = action.fluidContainer                       -- the action's own Lua field
    if fc == nil then fc = read(item, "getFluidContainer") end
    if fc == nil then return nil end
    local litresBefore = read(fc, "getAmount")             -- litres (#2685)
    if type(litresBefore) ~= "number" or litresBefore <= 0 then return nil end
    local d = { item = item, fc = fc, username = username, litresBefore = litresBefore, mix = {}, player = char }
    d.fullType = tostring(read(item, "getFullType"))
    -- getPercentage(i) is the fluid's proportion 0..1; getFluidTypeString is never null on a Fluid (#2684)
    local sample = read(fc, "createFluidSample")
    if sample ~= nil then
        local n = num(read(sample, "size"))
        local i = 0
        while i < n do
            local fluid = read(sample, "getFluid", i)
            local typeStr = read(fluid, "getFluidTypeString")
            local proportion = read(sample, "getPercentage", i)
            if type(proportion) == "number" then
                d.mix[#d.mix + 1] = { tostring(typeStr), proportion }
            end
            i = i + 1
        end
        NR.call(sample, "release")                         -- pooled: back before the original runs
    end
    return d
end

function IN.readDrinkAfterAndLand(d)
    local litresAfter = read(d.fc, "getAmount")
    if type(litresAfter) ~= "number" then
        error("intake: getAmount unreadable after the original for " .. d.fullType)
    end
    local litres = IN.litresDrunk(d.litresBefore, litresAfter)
    if litres <= 0 then return nil end                     -- an empty container or a no-op call
    if NR.data == nil or NR.data.fluids == nil then error("intake: NR.data.fluids absent") end
    local vec, missing = IN.fluidVector(NR.data.fluids.get, d.mix, litres)
    -- the landing guard, as for an eat (#2833)
    local bad = IN.firstNonFinite(vec)
    if not IN.isFinite(litres) then bad = "litres" end
    if bad ~= nil then return IN.reject(bad) end
    local record = NR.server.store.get(d.username, worldAge(), d.player)
    if record == nil then error("intake: no store record for " .. tostring(d.username)) end
    record.stomach = record.stomach or K.stomach.new()  -- an empty stomach, as kinetics lays it
    record.pool = record.pool or K.vector.new()
    IN.land(record, d.username, vec, "liquid")
    record.lastIntake = { fullType = d.fullType, source = "fluid", litres = litres, missing = missing }
    IN.stats.landed = IN.stats.landed + 1
    NR.log.say(3, "intake: " .. d.fullType .. " for " .. tostring(d.username) .. " source fluid litres "
        .. tostring(litres))
    return vec
end

local function mirrorDrink()
    local cls = ISDrinkFluidAction
    local D = NR_IntakeDrink_Installed
    IN.wrappedDrink = cls ~= nil and D.wrapper ~= nil and D.class == cls
    return IN.wrappedDrink
end

function IN.installDrink()
    if ISDrinkFluidAction == nil then return mirrorDrink() end
    installOne(NR_IntakeDrink_Installed, ISDrinkFluidAction, "ISDrinkFluidAction", "updateEat", "drink")
    return mirrorDrink()
end

-- ---------------------------------------------------------------------------------------------------
-- The world-water wrapper (#2942): ISTakeWaterAction.transferFluid. With no item the step moves litres into a temporary
-- container and DrinkFluid drinks it whole (#2931), which no Lua wrap sees; with an item it fills and nothing is drunk.
-- The cap is read off nrLanded, a field on the vanilla action object for its lifetime, never on the record.

-- nil when nothing is drunk (an item to fill, a non-positive amount, an empty or unreadable source).
function IN.readWorldBefore(action, amount)
    if action.item ~= nil then return nil end              -- filling a container, not a drink
    local char = action.character
    if char == nil then return nil end
    if type(amount) ~= "number" or amount <= 0 then return nil end
    local avail = read(action.waterObject, "getFluidAmount")
    if type(avail) ~= "number" or avail <= 0 then return nil end
    local username = read(char, "getUsername")
    if username == nil then return nil end
    local litres = K.min(amount, avail)
    local planned = action.waterUnit
    if type(planned) == "number" then
        litres = K.min(litres, K.max(planned - (action.nrLanded or 0), 0))
    end
    if litres <= 0 then
        return nil
    end
    return { username = username, litres = litres, fullType = "world water", action = action, player = char }
end

function IN.readWorldAfterAndLand(d)
    local litres = d.litres
    if not IN.isFinite(litres) then return IN.reject("litres") end
    local vec, missing
    if NR.data ~= nil and NR.data.fluids ~= nil then
        vec, missing = IN.fluidVector(NR.data.fluids.get, { { "Water", 1 } }, litres)
    end
    if vec == nil or missing[1] ~= nil then
        vec = K.vector.new()                               -- no Water seed: the water alone
        vec.water = litres * 1000
    end
    local bad = IN.firstNonFinite(vec)
    if bad ~= nil then return IN.reject(bad) end
    local record = NR.server.store.get(d.username, worldAge(), d.player)
    if record == nil then error("intake: no store record for " .. tostring(d.username)) end
    record.stomach = record.stomach or K.stomach.new()  -- an empty stomach, as kinetics lays it
    record.pool = record.pool or K.vector.new()
    IN.land(record, d.username, vec, "liquid")
    if d.action ~= nil then d.action.nrLanded = (d.action.nrLanded or 0) + litres end
    record.lastIntake = { fullType = d.fullType, source = "world", litres = litres, missing = {} }
    IN.stats.landed = IN.stats.landed + 1
    NR.log.say(3, "intake: world water for " .. tostring(d.username) .. " litres " .. tostring(litres))
    return vec
end

local function mirrorWorld()
    local cls = ISTakeWaterAction
    local W = NR_IntakeWorld_Installed
    IN.wrappedWorld = cls ~= nil and W.wrapper ~= nil and W.class == cls
    return IN.wrappedWorld
end

function IN.installWorld()
    if ISTakeWaterAction == nil then return mirrorWorld() end
    installOne(NR_IntakeWorld_Installed, ISTakeWaterAction, "ISTakeWaterAction", "transferFluid", "world")
    return mirrorWorld()
end

-- At load, so the wrap is in place before the first eat, and again at OnServerStarted; both modes install.
IN.install()
IN.installDrink()
IN.installWorld()

if Events ~= nil and Events.OnServerStarted ~= nil then
    Events.OnServerStarted.Add(function()
        if not NR.isServer() then return end
        IN.install()
        IN.installDrink()
        IN.installWorld()
        if not IN.wired then
            IN.wired = true
            NR.log.say(1, "intake: wrappers " .. tostring(IN.wrapped) .. " drink " .. tostring(IN.wrappedDrink)
                .. " world " .. tostring(IN.wrappedWorld))
        end
    end)
end

-- ---------------------------------------------------------------------------------------------------
-- Monotony booked at the eat, in meal-sized portions. Nothing is added to a stat here: UNHAPPINESS never falls on its
-- own (#3033), so adds would pile up; the writer holds a self-releasing floor instead (#3119). Under its own pcall.
function IN.atEat(record, b, kcal)
    local ok, err = pcall(IN.monotony, record, b, kcal)
    if ok then return err end
    IN.stats.monotonyFailures = IN.stats.monotonyFailures + 1
    IN.lastError = "monotony failed: " .. tostring(err)
    NR.log.say(2, "intake: " .. IN.lastError)
    return 0
end

-- A corrupt monotony is reset by the kernel's heal and counted (monotonyHealed).
function IN.monotony(record, b, kcal)
    local ageH = worldAge()
    local w = K.monotony.weightOf(kcal)
    if not IN.isFinite(ageH) or w <= 0 then return 0 end
    local typeKey = b.fullType
    if type(typeKey) ~= "string" or typeKey == "" or typeKey == "nil" then return 0 end
    local m, healed = K.monotony.heal(record.monotony, ageH)
    if healed then
        IN.stats.monotonyHealed = IN.stats.monotonyHealed + 1
        NR.log.say(2, "intake: monotony record reset for " .. tostring(b.username))
    end
    record.monotony = m
    K.monotony.prune(m, ageH)
    local class = IN.hedonicsAtEat(record, b, kcal, ageH)
    K.monotony.record(m, typeKey, ageH, w, K.monotony.isStaple(typeKey, b.foodType), class)
    IN.stats.monotony = IN.stats.monotony + 1
    return w
end

IN.limitations[#IN.limitations + 1] = "monotony keys an eat by the item's full type, so an evolved dish is one type whatever went into it and two foods of one kind under different types count apart (beside a taste-class key at a tenth of the weight, NR_Server_Hedonics' limitations); an eat counts as its landed kcal over a 400 kcal meal-sized portion, at most one, so an eat with no energy books nothing and a small snack counts a sliver of a meal; drinks and world water book no monotony; monotony is a self-releasing floor, not an add at the eat: the writer holds UNHAPPINESS and BOREDOM up to the most repeated type's level once a minute, a game choice anchored on vanilla's stale item and capped at 30, so a one-food diet alone shows the level-1 Unhappy and Bored moodles and stays under Bored level 2, where a staple (FoodType Bread, Rice or Pasta, or a named potato, oat, bread or plain-pasta type) holds a quarter of it, so a repeat shows at the next minute and rises at the floor's rate; as the counts decay the floor fades to 0 with no step at the 7-day window, a fall under 0.05 held to the next write, and its release lowers the stat by the target's fall even when another source also raised it; vanilla resets BOREDOM while PANIC above 5, the mod's own dehydration panic floor included, so monotony's BOREDOM floor is wiped while the character panics"

-- The SR Legacy household measures (S2212); 1.0 for a type with no entry. One Lua table read per eat.
function IN.volumeOf(fullType)
    if type(fullType) ~= "string" or NR.data == nil or NR.data.volume == nil then return 1.0 end
    return NR.data.volume.get(fullType)
end

IN.limitations[#IN.limitations + 1] = "a food fills by its weight plus 0.05 of its plate volume beyond its weight (a game choice), the volume being the eaten item's own type's household measure (a family judgement's where the source has none: buns, baguette, croissant, crisps, crackers): an evolved dish reads the eaten item's own type's measure, whatever went into it (a sandwich has none and loses the bread's air; toast or a bowl of oatmeal applies its own to every topping), a food with no measure in the source (bagels, cookies, cakes, most meat) or one the item pass does not map fills by weight alone, and drinks, world water and the reconcile path add no volume"

-- The hedonics seats (NR.server.hedonics), looked up per call so a host without that file still eats; each under the
-- seat's own pcall.
function IN.hedonicsBefore(b, kind)
    local H = NR.server.hedonics
    if H ~= nil and (kind == "eat" or kind == "cancel") then H.alliesBefore(b) end
end

function IN.hedonicsAfter(b, kind)
    local H = NR.server.hedonics
    if H ~= nil and (kind == "eat" or kind == "cancel") then H.alliesAfter(b) end
end

function IN.hedonicsAtEat(record, b, kcal, ageH)
    local H = NR.server.hedonics
    if H == nil then return nil end
    return H.atEat(record, b, kcal, ageH)
end
