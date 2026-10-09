-- NR_Server_Intake.lua -- the intake wrappers (spec § 4.2): ISEatFoodAction.complete and
-- ISEatFoodAction.serverStop, wrapped server-side so the capture reads the item before Eat touches it
-- (#1190, #1033) and again after. A multiplayer client never reaches complete (#0109), and a cancel
-- reaches Eat through serverStop, not complete (#0111), so both seats are wrapped.
--
-- Shape (eat-and-cook-hooks rules; Task 1's QualityCooking composition ruling):
--  * Each sentinel is a global of its own, NOT a field of NutritionRevamp, which NR_Core re-creates by
--    plain assignment on every load (#0943): a sentinel kept there would be wiped under a wrapper still
--    installed and the next install would wrap the wrapper.
--  * install() saves the current method and replaces it only when it is not already the mod's wrapper
--    (#1067), so it is idempotent within a boot and across a reloadlua. It also does not re-wrap when the
--    mod's wrapper is still in the chain below another mod's later save-and-replace of the same method
--    (QualityCooking's has no sentinel): the sentinel remembers the class table it wrapped, and a wrap is
--    redone only when that table was re-created (a reload of the vanilla file), which drops the wrapper.
--  * The wrapper ALWAYS calls the saved original and returns its result -- on the client, on a failed
--    capture, on every path -- and never inside the pcall: a mod bug can never block an eat, and any
--    corpus wrap below this one (QualityCooking's buff) always runs.
--  * The wrapper reads its logic from NutritionRevamp.server.intake at call time, so a reload of this
--    file swaps the capture code under a wrapper that stays installed.
--  * The side test is nil-checked and per call: this server/ file also runs in the client VM (#0855).
--  * Every Java global (ISEatFoodAction, ISDrinkFluidAction, ISTakeWaterAction, Events, getGameTime) is named only inside
--    a function, behind a nil check, so the file loads with no engine
--    (testing/tests/kernel/test_intake_shape.py).
--  * Java lists are walked with size()/get(i), never `#` (#0940).
--
-- Cadence: the eat capture runs once per eat (complete) or cancel (serverStop) on the server. The
-- drink capture runs once per updateEat call -- every server tick during a drink plus about every
-- 100 ms from the animation event (#0085), bounded to the drink's duration -- each call allocating one
-- fluid sample and one store lookup. The world-water capture runs once per transferFluid step. None
-- of it is on the per-tick stat path: no @fastpath region in this file.
--
-- The landing every route shares (Plan 4 Task 12, IN.land): the eat, the drink sip and the world-water
-- transfer each go through it, in this order --
--  1. the per-minute ingested sum IN.lastIngested[username] (every key of K.vector.KEYS, the amount as
--     INGESTED, before the B12 ceiling), which NR_Server_Nutrients reads and clears once a slow minute
--     (the excess ladder, the alcohol day total);
--  2. the acute dose test (ruling 18), IN.acuteAtEat: K.nutrients.acuteTest per record with an `acute`
--     field on the landed vector, against the body mass fm + lm and the pre-eat record.stomachFill,
--     stamping record.nutrients[key].ax = ACUTE_DECAY_H and .axr = the rung (a live flag's higher rung is
--     kept); NR_Server_Nutrients exposes no acuteAtEat, so it is here, under its own pcall;
--  3. the B12 per-eat ceiling (ruling 20, S0357/S0358): vector.vitB12 = K.interact.b12Ceiling(vitB12).
--     The ceiling is an ABSORPTION cap per meal, so it is applied where the per-eat amount is known, on
--     the vector that goes into the stomach; K.stomach.BIOAVAIL.vitB12 stays 1.0, so the stomach absorbs
--     what the ceiling let through;
--  4. the gut lane (ruling T17-2, x151r #2982/#2983): the vector's ethanol and caffeine are added to
--     IN.pendingAlc[username] / IN.pendingCaf[username] (numbers, no table allocated) and zeroed on the
--     vector, so neither enters the stomach; NR_Server_Nutrients drains them into record.acute.gutAlc /
--     gutCaf on its next minute (the pending tables are the simpler of the two shapes the fix brief
--     offered: the eat never has to create record.acute, whose slow-metaboliser draw is the adapter's);
--  5. K.stomach.ingest, or K.stomach.ingestLiquid for a drink (Plan 11c ruling 11c-12: its water in the liquid lane);
--  6. the satiety pool P fed with the delivered vector's weighted kcal (IN.feed; Plan 11c rulings 11c-27, 11c-30).
--
-- The vector's source (Plan 6 rulings 13-14, IN.assemble): a dish's ingredient list, else a craft map,
-- else the eaten item's own chain IN.chainOne -- declared (the item's NR_Nutrients default-modData
-- string, K.vector.declared, its four macros the item's own) -> the table (NR.data.nutrients.get) ->
-- inferred (the item's four macros and FoodType through NR.data.infer, K.vector.infer) -> missing. A
-- dish or craft input goes through the same chain per type (IN.chainedLookup), its declared string,
-- macros and FoodType read once per type per boot off a fresh instance (IN.typeInfo: a script's macros
-- have no getter, #2679, so the instanceItem global, #2680).
local NR = NutritionRevamp
local K = NR.kernel
NR.server.intake = { wrapped = false, wrappedComplete = false, wrappedServerStop = false,
                     wrappedDrink = false, wrappedWorld = false, wired = false,
                     stats = { eats = 0, cancels = 0, sips = 0, worldSips = 0, landed = 0, failures = 0,
                               passthrough = 0, unreadableAfter = 0, acuteFlags = 0, acuteFailures = 0,
                               declaredMalformed = 0, creditFailures = 0 },
                     lastIngested = {},
                     landed = {},
                     pendingAlc = {},
                     pendingCaf = {},
                     typeInfoCache = {},
                     limitations = {
                         "a food outside the table takes a vector inferred from its FoodType's per-kcal medians over the pass's own mapped records (NR_Data_Infer.lua; a judgement); a declared NR_Nutrients script key (unrecognised by the loader, landing in default modData — #1281) takes precedence and its macros are the item's own",
                         "a landed vector's ethanol and caffeine wait in a transient server table until the next slow minute moves them to record.acute: a server stop in that minute loses them (the ingested day totals keep them)",
                         "a world-water drink lands at most the action's planned litres (waterUnit, sized from THIRST at its start); while the view holds THIRST, vanilla's updateUse re-transfers its cumulative target, so the SOURCE can lose more than was landed until the slow clock lands the water",
                         "a world-water source lands as the Water seed whatever its fluid (a tainted source included)",
                         "a drink's acute dose is tested per sip, not per drink: a dose split across sips can read a lower rung",
                     },
                     lastError = nil }
local IN = NR.server.intake

-- The sentinels: `or {}` keeps the existing table when this file is re-run, and NR_Core's reset never
-- touches them. Each holds orig (the saved method), wrapper (the mod's closure), class (the class table
-- the wrap went into) and off (a pass-through switch for an uninstall that could not unwind).
NR_IntakeComplete_Installed = NR_IntakeComplete_Installed or {}
NR_IntakeServerStop_Installed = NR_IntakeServerStop_Installed or {}
NR_IntakeDrink_Installed = NR_IntakeDrink_Installed or {}
NR_IntakeWorld_Installed = NR_IntakeWorld_Installed or {}

-- ---------------------------------------------------------------------------------------------------
-- The pure helpers: no Java, tested on the lupa host.

-- The eat's pure arithmetic is the kernel's (NR_Kernel_Intake.lua, K.intake; Plan 10 Task R3): shareEaten,
-- fractionOf, macrosEaten, sourceOf, chainOne, newTrace, traceStep and the core of assemble moved there with their
-- comments. Each public name stays here as a thin wrapper, so every caller and shape test reaches the same code.
-- shareEaten: the share of the WHOLE item eaten, the drop in raw hunger over the instance base hunger, 0..1.
IN.shareEaten = K.intake.shareEaten
-- fractionOf: frac (Eat's own fraction of what was LEFT) and share (of the WHOLE instance); a thirst-only Food
-- takes them from its raw thirst and the type's script thirst.
IN.fractionOf = K.intake.fractionOf

-- A finite number: a number, not NaN (the one value unequal to itself) and not an infinity. Pure.
IN.isFinite = NR.finite

-- The raw reading after the original, normalised: a finished item reads NaN, not 0 (#2832) -- Eat
-- sets hungChange to 0, then Food.setCurrentUses calls consumeHunger(0), whose 0/0 writes NaN into
-- the scaled fields. A non-finite or unreadable after-reading against a numeric before-reading means
-- the item was finished, so it reads 0 (a finishing quarter then lands its whole remainder: frac 1).
-- A non-numeric before-reading passes the after-reading through untouched.
function IN.afterReading(before, after)
    if type(before) == "number" and not IN.isFinite(after) then return 0 end
    return after
end

-- An after-reading that is UNREADABLE (nil or not a number) against a numeric before-reading, as
-- opposed to the known NaN/inf of a finished item (#2832, silent): afterReading still maps it to 0
-- (finished, so the whole remainder lands), but it is not the vanilla 0/0, so it is made visible.
function IN.isUnreadableAfter(before, after)
    return type(before) == "number" and type(after) ~= "number"
end

-- The first key of a vector that is not finite, or nil when every key is (numeric-for over KEYS, a
-- Lua table the kernel built, so `#` on it is a Lua length). A NaN landed in the stomach would poison
-- the buffer, pool and the HUNGER stat for the session (#2833).
function IN.firstNonFinite(vec)
    local keys = K.vector.KEYS
    for i = 1, #keys do
        local k = keys[i]
        if not IN.isFinite(vec[k]) then return k end
    end
    return nil
end

-- Add one landed vector into the per-minute ingested sum for username (every declared key, numeric for
-- over KEYS, a Lua table). The sum is allocated the first time a username lands in a minute; the slow
-- clock (NR_Server_Nutrients) reads it and sets the slot to nil. Returns the sum.
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

-- The acute dose test at the eat (ruling 18): every record with an `acute` field and a vector key is
-- tested on the landed vector against the body mass (fm + lm) and the record's stomachFill (the slow
-- clock's stamp, the fill before this eat; nil or non-finite reads the stomach's own fill, else empty: ruling C-2).
-- A rung > 0 stamps the key's state ax = ACUTE_DECAY_H and axr = the rung, keeping a still-live flag's higher rung. records defaults
-- to NR.data.records; no records or no body tests nothing. A missing record.nutrients is made the way
-- NR_Server_Nutrients makes it. Returns the number of keys flagged.
function IN.acuteAtEat(record, vec, records)
    records = records or (NR.data and NR.data.records)
    if records == nil or record == nil then return 0 end
    local body = record.body
    if body == nil then return 0 end
    local w = (body.fm or 0) + (body.lm or 0)
    if not IN.isFinite(w) or w <= 0 then return 0 end
    local fill = K.stomach.recordFill(record)
    -- ruling C-2: a missing fill is the stomach's own, else empty (since 11c-15 a new stomach is empty)
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

-- The landing every route shares (the header's six steps): the ingested sum and the acute test read
-- the vector as ingested; the B12 ceiling then caps vitB12 in place; the ethanol and caffeine leave the
-- vector for the gut lane's pending sums; the stomach takes the result -- lane "liquid" (a drink, world water)
-- lands the water in the liquid lane, anything else lands as food -- and the satiety pool is fed with it.
-- The record's stomach must exist. The acute test runs under its own pcall: a raise there is counted
-- and named, and the landing goes on.
function IN.land(record, username, vec, lane)
    IN.landed[username] = true                     -- the writer's sip fold skips this minute (Plan 11 ruling 7)
    if NR.server.store ~= nil and NR.server.store.mark ~= nil then NR.server.store.mark(username) end -- saved at the next store step (ruling T20-1)
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
        K.stomach.ingest(record.stomach, vec)
    end
    IN.feed(record, vec)
    return vec
end

-- Plan 11c (rulings 11c-27, 11c-30; Task 6 amendment 1): the meal pool P is fed at the eat with the delivered
-- vector's weighted kcal (K.satiety.feed), on every route that lands -- the eat, the drink, world water and the
-- reconcile path -- and a partial eat's vector is already its fraction. A record whose satiety or P is absent or
-- non-finite is left for the writer's seed at its next minute: an eat in a fresh record's first minute
-- shows only through the HUNGER the seed reads (a named limitation, the writer's limitation 4). A feed that comes
-- out non-finite is not kept.
function IN.feed(record, vec)
    local s = record.satiety
    if type(s) ~= "table" or not IN.isFinite(s.P) then return end
    local P = K.satiety.feed(s.P, vec)
    if IN.isFinite(P) then s.P = P end
end

-- The vector's source: dish > craft > the eaten item's own chain step (K.intake.sourceOf).
IN.sourceOf = K.intake.sourceOf

-- The NR_Nutrients default-modData string of an item (the declared-nutrients contract, ruling 14: an
-- unrecognised script key lands in default modData as a String unless it parses as a Double, #0212,
-- #1281), or nil. modData is a Lua-shaped table.
function IN.declaredOf(md)
    if type(md) ~= "table" then return nil end
    local v = md.NR_Nutrients
    if type(v) == "string" then return v end
    return nil
end

-- One type through the chain declared -> table -> inferred -> missing (K.intake.chainOne, over K.vector.resolve).
IN.chainOne = K.intake.chainOne

-- A fresh per-eat trace of the chain (K.intake.newTrace), and one chain step recorded in it (K.intake.traceStep).
IN.newTrace = K.intake.newTrace
IN.traceStep = K.intake.traceStep

-- The chained lookup a dish ingredient or a craft input goes through: lookup(fullType) -> vec or nil
-- over IN.chainOne, info(fullType) giving the type's declared string, macros and FoodType (nil info:
-- the table alone, as before Plan 6). Built once per eat, here in the server file -- a closure, which
-- the kernel's lookup-taking functions call without knowing (no closure inside the kernel).
function IN.chainedLookup(lookup, templates, info, trace)
    return function(fullType)
        local i = nil
        if info ~= nil then i = info(fullType) end
        local vec, step, note = IN.chainOne(fullType, lookup, templates, i)
        IN.traceStep(trace, fullType, step, note)
        return vec
    end
end

-- The consumed fullType -> count map the hand-craft action writes onto a single output (#2667), or nil.
-- Keeps string keys holding a `.` (a full type) with number values; drops the vanilla keys customName
-- and Tooltip (#1415) and the mod's own NR_ keys. modData is a Lua-shaped table, so pairs is allowed.
function IN.craftMap(md)
    if type(md) ~= "table" then return nil end
    local out, n = {}, 0
    for k, v in pairs(md) do
        if type(k) == "string" and type(v) == "number" and k ~= "customName" and k ~= "Tooltip"
                and string.sub(k, 1, 3) ~= "NR_" and string.find(k, ".", 1, true) ~= nil then
            out[k] = v
            n = n + 1
        end
    end
    if n == 0 then return nil end
    return out
end

-- What Eat delivered to the four vanilla macros, /5 when burnt (K.intake.macrosEaten).
IN.macrosEaten = K.intake.macrosEaten

-- Assemble the eaten vector (K.intake.assemble, whose comment carries the share and frac semantics). Returns vec,
-- source, missing, share, frac, trace. lookup(fullType) -> seed vector or nil (the server passes
-- NR.data.nutrients.get); templates is NR.data.infer (nil: no inference); info(fullType) -> a dish or craft
-- input's { declared, macros, foodType } (nil: inputs through the table alone). The adapter's part is the
-- per-eat trace and the chained-lookup closure over it (the kernel holds no closure), built only for a dish or a
-- craft, the two sources that read inputs (Plan 11 Task 3).
function IN.assemble(b, rawAfter, lookup, thirstAfter, templates, info)
    local trace = IN.newTrace()
    local inputs = nil
    if (b.extraTypes ~= nil and #b.extraTypes > 0) or b.craftMap ~= nil then
        inputs = IN.chainedLookup(lookup, templates, info, trace)   -- a dish or a craft: the one closure per eat
    end
    return K.intake.assemble(b, rawAfter, lookup, thirstAfter, templates, inputs, trace)
end

-- ---------------------------------------------------------------------------------------------------
-- The engine edge: every Java member through the index-first guard (NR.call), nothing assumed.

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

-- A Food's FoodType string (Food.getFoodType, the script's FoodType), or nil when absent or empty.
function IN.foodTypeOf(item)
    local ft = read(item, "getFoodType")
    if type(ft) == "string" and ft ~= "" then return ft end
    return nil
end

-- The chain's reads off one Food instance: { declared, foodType, macros }, or nil when the item has
-- no calories getter (not a Food).
function IN.foodInfo(item)
    local cal = read(item, "getCalories")
    if type(cal) ~= "number" then return nil end
    local macros = { calories = cal, carbs = num(read(item, "getCarbohydrates")),
                     lipids = num(read(item, "getLipids")), proteins = num(read(item, "getProteins")) }
    return { declared = IN.declaredOf(read(item, "getModData")), foodType = IN.foodTypeOf(item),
             macros = macros }
end

-- A dish or craft input's chain reads, by type: a fresh instance through the instanceItem global (a
-- script's macros have no getter and InventoryItemFactory is not exposed, #2679, #2680), read by
-- IN.foodInfo. Script data is fixed for a boot, so each type is instanced once and cached
-- (IN.typeInfoCache; false for a type that does not instance or is not a Food). nil without the global.
function IN.typeInfo(fullType)
    local cached = IN.typeInfoCache[fullType]
    if cached == false then return nil end
    if cached ~= nil then return cached end
    if instanceItem == nil then return nil end
    local info = false
    local ok, item = pcall(instanceItem, fullType)
    if ok and item ~= nil then
        local okI, fi = pcall(IN.foodInfo, item)   -- a raising getter on the fresh instance caches false (the Task 10 review)
        if okI then info = fi or false end
    end
    IN.typeInfoCache[fullType] = info
    if info == false then return nil end
    return info
end

-- The before-snapshot of the action's item, or nil when there is nothing to capture (no item, no
-- character, no username, not a Food: no raw hunger getter).
function IN.readBefore(action)
    local item, char = action.item, action.character
    if item == nil or char == nil then return nil end
    local username = read(char, "getUsername")
    if username == nil then return nil end
    local rawBefore = read(item, "getHungChange")          -- the RAW stored hunger (#0002)
    if type(rawBefore) ~= "number" then return nil end
    local b = { item = item, username = username, rawBefore = rawBefore }
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
    -- the script hunger, a public bare read in script points (#2678): /100 to the instance's units
    local script = read(item, "getScriptItem")
    local scriptHunger = read(script, "getHungerChange")
    b.scriptHunger = 0
    if type(scriptHunger) == "number" then b.scriptHunger = scriptHunger / 100 end
    -- the script thirst, the same shape: Item.getThirstChange() is a bare getfield of the script
    -- object's thirstChange (jar 42.20.4, Item.getThirstChange L563), script points /100 like hunger
    -- (#0011, #0323) -- a thirst-only Food's whole-instance denominator (fractionOf)
    local scriptThirst = read(script, "getThirstChange")
    b.scriptThirst = 0
    if type(scriptThirst) == "number" then b.scriptThirst = scriptThirst / 100 end
    -- the dish's ingredient list: a Java ArrayList, walked with size()/get(i)
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
    -- the chain's own reads (rulings 13-14): the declared NR_Nutrients string, the FoodType, the macros
    b.declared = IN.declaredOf(md)
    b.foodType = IN.foodTypeOf(item)
    b.macros = { calories = b.cal, carbs = b.carb, lipids = b.lip, proteins = b.pro }
    return b
end

-- After the original: the raw hunger again, the assembly, the landing in the player's stomach.
function IN.readAfterAndLand(b)
    -- a finished item reads NaN here, not 0 (#2832, vanilla's 0/0 in consumeHunger): normalised to 0
    local rawRead = read(b.item, "getHungChange")
    local rawAfter = IN.afterReading(b.rawBefore, rawRead)
    -- the raw thirst again (#0005), the same normalisation
    local thirstRead = read(b.item, "getThirstChangeUnmodified")
    local thirstAfter = IN.afterReading(b.thirstBefore, thirstRead)
    -- an unreadable (nil/non-number) after-read is treated as finished like the NaN, but counted and
    -- named, once per landing: it is not the known vanilla 0/0, so it must not pass silently
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
    local record = NR.server.store.get(b.username, worldAge())
    if record == nil then error("intake: no store record for " .. tostring(b.username)) end
    record.stomach = record.stomach or K.stomach.new()  -- an empty stomach, as kinetics lays it (ruling 11c-15)
    record.pool = record.pool or K.vector.new()
    IN.land(record, b.username, vec)
    record.lastIntake = { fullType = b.fullType, source = source, share = share, frac = frac,
                          missing = missing, declared = trace.declared, inferred = trace.inferred }
    IN.stats.landed = IN.stats.landed + 1
    NR.log.say(3, "intake: " .. b.fullType .. " for " .. tostring(b.username) .. " source " .. source
        .. " share " .. tostring(share))
    return vec
end

-- A rejected landing: nothing lands, the failure is counted and named. Returns nil.
function IN.reject(key)
    IN.stats.failures = IN.stats.failures + 1
    IN.lastError = "non-finite intake rejected: " .. tostring(key)
    NR.log.say(2, "intake: " .. IN.lastError)
    return nil
end

-- The two halves the wrapper calls, each under its own pcall; the original runs between them, outside.
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
        return b
    end
    IN.stats.failures = IN.stats.failures + 1
    IN.lastError = b
    NR.log.say(2, "intake: capture failed before the " .. kind .. ": " .. tostring(b))
    return nil
end

function IN.guardAfter(b, kind)
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

-- The reconciliation credit (Plan 8 ruling 6, NR_Server_Reconcile): the four vanilla macro stores are read
-- before the original (b.nrStores, b.nrChar) and again after a landing that landed a vector, and the movement
-- between the two -- the engine's own Eat or DrinkFluid write inside the wrap -- is credited to the record's
-- reconciliation baseline, so the next slow minute does not land the same intake again as macros, while a
-- store rise by another writer outside the wrap stays visible to it. A landing that lands nothing (a cancel
-- with nothing eaten, a rejected vector) credits nothing: a store rise it leaves is reconciled as macros only.
-- Each half under its own pcall: a raise is counted and never reaches the eat.
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
    local record = NR.server.store.get(b.username, worldAge())
    return RC.credit(record, b.nrStores, after)
end

-- The wrapper closure, made once per sentinel and kept in it. It names nothing from this file's load:
-- the sentinel S is a persistent global and the logic is looked up on NutritionRevamp per call. The
-- method's own arguments reach the before-read (transferFluid's _amount; the other seats ignore them).
local function makeWrapper(S, kind)
    return function(self, ...)
        local nr = NutritionRevamp
        local intake = nil
        if nr ~= nil and nr.server ~= nil then intake = nr.server.intake end
        local b = nil
        if intake ~= nil and not S.off and nr.isServer ~= nil and nr.isServer() then
            b = intake.guardBefore(self, kind, ...)
        elseif intake ~= nil then
            intake.stats.passthrough = intake.stats.passthrough + 1 -- the client, or switched off
        end
        local result = S.orig(self, ...)                   -- every path; never inside a pcall
        if b ~= nil then intake.guardAfter(b, kind) end
        return result
    end
end

local function installOne(S, cls, clsName, method, kind)
    if cls == nil then return false end
    local cur = cls[method]
    if cur == nil then return false end
    S.off = false
    if cur == S.wrapper then return true end               -- already the outermost: idempotent
    if S.wrapper ~= nil and S.class == cls then return true end -- still in the chain below a later wrap
    S.orig = cur
    S.wrapper = S.wrapper or makeWrapper(S, kind)
    S.class = cls
    cls[method] = S.wrapper
    NR.log.say(2, "intake: " .. clsName .. "." .. method .. " wrapped")
    return true
end

local function uninstallOne(S, cls, method)
    if cls == nil or S.wrapper == nil or S.class ~= cls then return end
    if cls[method] == S.wrapper then
        cls[method] = S.orig
        S.class = nil
    else
        S.off = true                                       -- wrapped over by another mod: pass through
    end
end

local function mirror()
    local cls = ISEatFoodAction
    local C, T = NR_IntakeComplete_Installed, NR_IntakeServerStop_Installed
    IN.wrappedComplete = cls ~= nil and C.wrapper ~= nil and C.class == cls and not C.off
    IN.wrappedServerStop = cls ~= nil and T.wrapper ~= nil and T.class == cls and not T.off
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

function IN.uninstall()
    uninstallOne(NR_IntakeComplete_Installed, ISEatFoodAction, "complete")
    uninstallOne(NR_IntakeServerStop_Installed, ISEatFoodAction, "serverStop")
    return mirror()
end

-- ---------------------------------------------------------------------------------------------------
-- The drink wrapper (Task 9): ISDrinkFluidAction.updateEat, the drink action's ONE DrinkFluid call
-- (#2689). The update reaches it when not a client, the drinkFluid animation event when a server, and
-- complete unguarded (complete is just updateEat(1)), so updateEat is the single seat: wrapping complete
-- as well would count the last sip twice. A drink has no eat hook and no eat packet (#0084).
--  * Each sip is seen once: updateEat consumes only the gap between the target ratio and what has
--    already gone (#0085), so the litres before minus the litres after EACH call, summed over the
--    calls, is the container's whole consumed amount with no double count. Several calls per drink are
--    normal (the animation event about every 100 ms, complete the last); each lands its own vector.
--  * The mix is sampled BEFORE the call: the removal returns a FluidConsume with the aggregate's
--    nutrition and no per-fluid breakdown (#2688). The sample is walked with size()/get(i), never `#`
--    (#2685), and is pooled, so it is released inside the before-read, before the original runs.
--  * No retention on a drink: a fluid has no cooked/burnt/rotten/frozen state (tainted water and
--    poison are a separate vanilla path the mod does not touch here). No macro override either: the
--    per-litre seed macros are the fluid's own Properties, which is exactly what DrinkFluid writes
--    times the litres (#0064, #0630), so the fluid vector's macros track vanilla by construction.
--  * Same sentinel shape as the eat wrappers: a global of its own, idempotent save-and-replace with
--    the class-table reload guard, the saved original ALWAYS called, outside the pcall.
--
-- limitations:
--  * A drink straight from a world water source goes through ISTakeWaterAction, which moves the litres
--    into a temporary container and calls DrinkFluid on it itself (#2690): this wrapper never sees it;
--    the world-water wrapper below (transferFluid, Plan 4 Task 12) does.
--  * ISDrinkFromBottle is dead code on this build (no caller chain; it calls no DrinkFluid) (#0670).
--
-- limitations (intake-wide: the eat, cancel and craft paths, Task 10):
--  * A crafted output from a MULTI-output recipe carries no vanilla consumed-type map (the hand-craft
--    action writes it only for exactly one output), so it falls back to dish (an extra-items list) or
--    baseline (the output type's seed x instance scale, the right 1/amount for an InheritFood split)
--    (#2667, #2660).
--  * A crafted output made through the ENTITY craft path (CraftLogicSystem: furnaces, drying racks)
--    carries no map either and takes the same fallback: that path calls OnCreate (#2665) but only the
--    hand-craft action writes the consumed-type map (#2667).
--  * An evolved DISH is not a craft: its ingredient list is extraItems and sourceOf ranks dish over
--    craft, so a dish never reaches the craft arm (#2650, #2653).
--  * A LATER mod that replaces ISEatFoodAction.complete (or serverStop, ISDrinkFluidAction.updateEat or
--    ISTakeWaterAction.transferFluid)
--    WITHOUT calling the saved original removes the capture silently; no sentinel can detect it, and
--    only NR.server.intake.stats.eats standing still across eats reveals it (#2842, the function-wrap
--    wall). #1067 is the rule it breaks (keep and call the original so two wraps compose).
--  * A crafted output's consumed-type map counts INSTANCES, not uses: a partly-used input (10 of 30
--    ice-cream uses, #0709) lands its whole seed, so the craft arm over-counts partial inputs by the
--    unspent fraction -- the map carries no uses, and the fix is Plan 6's (a per-recipe use fraction
--    from data/recipes.json). The map is +1 per entry of getAllConsumedItems (ISHandcraftAction.lua
--    :236-247), and that list holds one entry per consumed InventoryItem whatever its uses spent
--    (jar 42.20.4: CraftRecipeData.getAllConsumedItems @range L2220-L2235 walks the inputs into
--    CacheData.addAppliedItemsToList @L1868, a copy of appliedItems; CacheData.addAppliedItem
--    @range L1825-L1828 adds the item once (its duplicate check is a Java assert, off in production);
--    what makes it one entry per item is that CraftRecipeManager.consumeInputItemInternal @range
--    L948-L949 calls it once per InventoryItem and the uses arm, consumeInputItemUsesInternal, never does).
--  * No craft hook ships (Plan 2 ruling 5): the vanilla consumed-type map is the source, and X31's
--    craft probe runs only if a live reading shows that map unreachable.

-- The litres one updateEat call removed: before - after, floored at 0; a nil on either side -> 0.
function IN.litresDrunk(before, after)
    if type(before) ~= "number" or type(after) ~= "number" then return 0 end
    return K.max(before - after, 0)
end

-- The drink's vector: each sampled fluid's per-litre seed x its proportion of the mix x the litres
-- drunk, summed (K.vector.fluid is the single-fluid form of the same product). mix is a Lua array of
-- { fluidTypeString, proportion 0..1 } the before-read built, so `#` on it is a Lua length. A type the
-- lookup does not know goes to `missing` and contributes nothing. Returns vec, missing.
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

-- The before-snapshot of a drink, or nil when there is nothing to capture (no item, no character, no
-- username, no container, an empty container).
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
    local d = { item = item, fc = fc, username = username, litresBefore = litresBefore, mix = {} }
    d.fullType = tostring(read(item, "getFullType"))
    -- the mix: getPercentage(i) is the fluid's proportion 0..1 of the container's amount (the
    -- instance amount over the container total); getFluidTypeString is never null on a Fluid (#2684),
    -- the key the per-fluid table uses
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

-- After the original: the litres again, the fluid vector for the litres drunk, the landing.
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
    local record = NR.server.store.get(d.username, worldAge())
    if record == nil then error("intake: no store record for " .. tostring(d.username)) end
    record.stomach = record.stomach or K.stomach.new()  -- an empty stomach, as kinetics lays it (ruling 11c-15)
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
    IN.wrappedDrink = cls ~= nil and D.wrapper ~= nil and D.class == cls and not D.off
    return IN.wrappedDrink
end

function IN.installDrink()
    if ISDrinkFluidAction == nil then return mirrorDrink() end
    installOne(NR_IntakeDrink_Installed, ISDrinkFluidAction, "ISDrinkFluidAction", "updateEat", "drink")
    return mirrorDrink()
end

function IN.uninstallDrink()
    uninstallOne(NR_IntakeDrink_Installed, ISDrinkFluidAction, "updateEat")
    return mirrorDrink()
end

-- ---------------------------------------------------------------------------------------------------
-- The world-water wrapper (Plan 4 Task 12; ruling 9 with Task 1 verdict 4 and Task 4 arm D, x151w #2942):
-- ISTakeWaterAction.transferFluid(_amount) is the seat. The action drinks a world source in steps, each
-- reaching transferFluid from update, animEvent or complete, and the server builds and runs the action
-- (NetTimedAction.parse, #2932); with no item the step moves min(_amount, the source's amount) litres into a
-- temporary container and DrinkFluid drinks it whole (#2931) -- a Java call no Lua wrap sees, and not the
-- drink wrapper's updateEat. With an item the step FILLS that item and nothing is drunk: not captured.
-- The litres are read before the original and land as the Water seed through the fluid path
-- (IN.fluidVector, then IN.land) after it. Same sentinel shape as the other three wraps.
-- limitations: IN.limitations (the planned-litres cap and the fluid read as Water). a world-water drink lands at most the action's planned litres (waterUnit, sized from THIRST at its start); while the view holds THIRST, vanilla's updateUse re-transfers its cumulative target, so the SOURCE can lose more than was landed until the slow clock lands the water (ruling T1-1).
-- The cap: readWorldBefore lands min(step, source, waterUnit - action.nrLanded); nrLanded is a field on the
-- vanilla action object for its lifetime, never on the record.
-- Residual notes: after a respawn one minute's autoDrop can go to the dead character's record (stated
-- here; the takeover's respawn limitation named only stomachFill); if the slow clock never clears autoDrop for a
-- player (a repeated raise), auto-drink stays skipped for that player -- the heal is Plan 8's.

-- The before-snapshot of one world-water step, or nil when nothing is drunk (an item to fill, no
-- character or username, a non-positive amount, an empty or unreadable source).
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
    return { username = username, litres = litres, fullType = "world water", action = action }
end

-- After the original: the step's litres as the Water seed, the landing.
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
    local record = NR.server.store.get(d.username, worldAge())
    if record == nil then error("intake: no store record for " .. tostring(d.username)) end
    record.stomach = record.stomach or K.stomach.new()  -- an empty stomach, as kinetics lays it (ruling 11c-15)
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
    IN.wrappedWorld = cls ~= nil and W.wrapper ~= nil and W.class == cls and not W.off
    return IN.wrappedWorld
end

function IN.installWorld()
    if ISTakeWaterAction == nil then return mirrorWorld() end
    installOne(NR_IntakeWorld_Installed, ISTakeWaterAction, "ISTakeWaterAction", "transferFluid", "world")
    return mirrorWorld()
end

function IN.uninstallWorld()
    uninstallOne(NR_IntakeWorld_Installed, ISTakeWaterAction, "transferFluid")
    return mirrorWorld()
end

-- At load, so the wrap is in place before the first eat (the wrapper itself gates on the side per
-- call), and again at OnServerStarted behind the side test. Both modes install: the mod owns intake in
-- managed and overlay alike; only the stat tick differs by mode.
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
