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
--  * Every Java global (ISEatFoodAction, ISDrinkFluidAction, Events, getGameTime) is named only inside
--    a function, behind a nil check, so the file loads with no engine
--    (testing/tests/kernel/test_intake_shape.py).
--  * Java lists are walked with size()/get(i), never `#` (#0940).
--
-- Cadence: the eat capture runs once per eat (complete) or cancel (serverStop) on the server. The
-- drink capture runs once per updateEat call -- every server tick during a drink plus about every
-- 100 ms from the animation event (#0085), bounded to the drink's duration -- each call allocating one
-- fluid sample and one store lookup. None of it is on the per-tick stat path: no @fastpath region in
-- this file.
local NR = NutritionRevamp
local K = NR.kernel
NR.server.intake = { wrapped = false, wrappedComplete = false, wrappedServerStop = false,
                     wrappedDrink = false, wired = false,
                     stats = { eats = 0, cancels = 0, sips = 0, landed = 0, failures = 0, passthrough = 0,
                               unreadableAfter = 0 },
                     lastError = nil }
local IN = NR.server.intake

-- The sentinels: `or {}` keeps the existing table when this file is re-run, and NR_Core's reset never
-- touches them. Each holds orig (the saved method), wrapper (the mod's closure), class (the class table
-- the wrap went into) and off (a pass-through switch for an uninstall that could not unwind).
NR_IntakeComplete_Installed = NR_IntakeComplete_Installed or {}
NR_IntakeServerStop_Installed = NR_IntakeServerStop_Installed or {}
NR_IntakeDrink_Installed = NR_IntakeDrink_Installed or {}

-- ---------------------------------------------------------------------------------------------------
-- The pure helpers: no Java, tested on the lupa host.

-- The share of the WHOLE item eaten: the drop in raw hunger over the instance base hunger, clamped to
-- 0..1 (#0002, #0001). Raw hunger is negative (an apple is -0.16); the sign cancels in the ratio. A base
-- hunger of 0 answers 0. With instBase replaced by rawBefore it is the share of what was LEFT, which is
-- Eat's own rescaled fraction (Eat rescales the requested fraction by baseHunger/hungChange, #0006).
function IN.shareEaten(rawBefore, rawAfter, instBase)
    if instBase == 0 then return 0 end
    return K.clamp((rawBefore - rawAfter) / instBase, 0, 1)
end

-- The two fractions (see assemble): frac = Eat's own fraction of what was LEFT, share = the share of
-- the WHOLE instance. From the raw hunger when the instance base hunger is non-zero. A thirst-only
-- Food (base hunger 0) still goes through Eat (#0083), which then skips the baseHunger rescale and
-- applies the menu fraction directly (#0014); the leftover multiplyFoodValues(1 - f) scales its stored
-- thirstChange too (#0057), so the drop in RAW thirst (getThirstChangeUnmodified, #0005) over the raw
-- thirst before IS that fraction -- of what was LEFT (frac). It is the share of the whole only for a
-- never-eaten item: after a partial eat the stored thirst has shrunk, so the whole-instance share
-- takes the drop over the TYPE's unscaled thirst instead (scriptThirst, readBefore), the same shape as
-- hunger's instBase. A thirst-only Food has no base-thirst field; scriptThirst is the denominator.
-- Raw thirst is negative like hunger; the sign cancels. Nothing readable -> 0, 0 (nothing landed).
-- limitations:
--  * A split or butchered thirst-only item (its instance thirst scaled off the script value) mis-shares
--    by that scale -- vanishingly rare for a thirst-only Food.
--  * scriptThirst 0 or unreadable: the whole is unknown and share falls back to frac, which over-counts
--    the whole-instance vector on any eat after the first partial one.
function IN.fractionOf(rawBefore, rawAfter, instBase, thirstBefore, thirstAfter, scriptThirst)
    if instBase == nil or instBase == 0 then
        if type(thirstBefore) == "number" and type(thirstAfter) == "number" and thirstBefore ~= 0 then
            local drop = thirstBefore - thirstAfter
            local f = K.clamp(drop / thirstBefore, 0, 1)
            if type(scriptThirst) == "number" and scriptThirst ~= 0 then
                return f, K.clamp(drop / scriptThirst, 0, 1)
            end
            return f, f                                    -- the base is unknown (limitation above)
        end
        return 0, 0
    end
    return IN.shareEaten(rawBefore, rawAfter, rawBefore), IN.shareEaten(rawBefore, rawAfter, instBase)
end

-- A finite number: a number, not NaN (the one value unequal to itself) and not an infinity. Pure.
function IN.isFinite(x)
    return type(x) == "number" and x == x and x ~= math.huge and x ~= -math.huge
end

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
-- the buffer, bulk, pool and the HUNGER stat for the session (#2833).
function IN.firstNonFinite(vec)
    local keys = K.vector.KEYS
    for i = 1, #keys do
        local k = keys[i]
        if not IN.isFinite(vec[k]) then return k end
    end
    return nil
end

-- The vector's source: a dish's ingredient list is authoritative, so it wins over a craft map.
function IN.sourceOf(hasExtra, hasCraftMap)
    if hasExtra then return "dish" end
    if hasCraftMap then return "craft" end
    return "baseline"
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

-- What Eat delivered to the four vanilla macros: each live macro times the fraction Eat applied,
-- divided by 5 when the item is burnt (#0019, #0036 -- the one vanilla nutrition modifier).
function IN.macrosEaten(cal, carb, lip, pro, share, burnt)
    local d = 1
    if burnt then d = 5 end
    return { calories = cal * share / d, carbs = carb * share / d, lipids = lip * share / d,
             proteins = pro * share / d }
end

-- Assemble the eaten vector from the before-snapshot b and the raw hunger after the original ran.
-- Returns vec, source, missing, share, frac (nil vec when nothing was eaten). Two fractions:
--  share = the drop over instBase, the share of the WHOLE instance -- the factor on a whole-instance
--          vector (the baseline at the instance scale, the craft map);
--  frac  = the drop over rawBefore, the share of what was LEFT, which is Eat's own fraction -- the
--          factor on anything read off the live item, whose values a prior partial eat already shrank
--          (multiplyFoodValues): the four macros and the dish scaled to the live macro total.
-- For an item never eaten before rawBefore == instBase and the two agree. A thirst-only Food takes
-- frac from its raw thirst and share from that drop over the type's script thirst (fractionOf);
-- thirstAfter is the raw thirst after the original ran.
-- lookup(fullType) -> seed vector or nil (the server passes NR.data.nutrients.get).
function IN.assemble(b, rawAfter, lookup, thirstAfter)
    local frac, share = IN.fractionOf(b.rawBefore, rawAfter, b.instBase, b.thirstBefore, thirstAfter,
        b.scriptThirst)
    if not IN.isFinite(share) or share <= 0 or not IN.isFinite(frac) or frac <= 0 then
        return nil, nil, {}, share, frac
    end
    local extra = b.extraTypes or {}
    local source = IN.sourceOf(#extra > 0, b.craftMap ~= nil)
    local vec, missing, factor
    if source == "dish" then
        local note
        vec, note = K.vector.dish(lookup, extra, b.cal + b.carb + b.lip + b.pro)
        missing = note.missing
        factor = frac
    elseif source == "craft" then
        vec, missing = K.vector.craft(lookup, b.craftMap, 1)
        factor = share
    else
        -- the instance scale instBase/scriptHunger: 1 for an unscaled item, the butcher ratio x jitter
        -- for a butchered meat (#2669-#2672), 1/amount for a split output (#2660); meat guards 0
        vec, missing = K.vector.baseline(lookup, b.fullType, 1)
        vec = K.vector.meat(vec, b.instBase, b.scriptHunger)
        factor = share
    end
    vec = K.vector.add(K.vector.new(), vec, factor)
    -- the macros track vanilla exactly: what Eat delivered, not what the seed says
    local m = IN.macrosEaten(b.cal, b.carb, b.lip, b.pro, frac, b.burnt)
    vec.calories, vec.carbs, vec.lipids, vec.proteins = m.calories, m.carbs, m.lipids, m.proteins
    -- retention skips the macros by design
    vec = K.retention.apply(vec, { cooked = b.cooked, burnt = b.burnt, rotten = b.rotten, frozen = b.frozen })
    return vec, source, missing or {}, share, frac
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

local function worldAge()
    if getGameTime == nil then return 0 end
    local ok, gt = pcall(getGameTime)
    local okA, age = NR.call(ok and gt or nil, "getWorldAgeHours")
    if okA and type(age) == "number" then return age end
    return 0
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
    b.craftMap = IN.craftMap(read(item, "getModData"))
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
    local vec, source, missing, share, frac = IN.assemble(b, rawAfter, NR.data.nutrients.get, thirstAfter)
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
    record.stomach = record.stomach or K.stomach.seedFull(K.stomach.new())  -- seeded full like kinetics' first sight (Task 11 game choice): an eat before the first kinetics minute must not leave an unseeded stomach
    record.pool = record.pool or K.vector.new()
    K.stomach.ingest(record.stomach, vec)
    record.lastIntake = { fullType = b.fullType, source = source, share = share, frac = frac,
                          missing = missing }
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
function IN.guardBefore(action, kind)
    local readFn = IN.readBefore
    if kind == "cancel" then
        IN.stats.cancels = IN.stats.cancels + 1
    elseif kind == "drink" then
        IN.stats.sips = IN.stats.sips + 1             -- one per updateEat call
        readFn = IN.readDrinkBefore
    else
        IN.stats.eats = IN.stats.eats + 1
    end
    local ok, b = pcall(readFn, action)
    if ok then return b end
    IN.stats.failures = IN.stats.failures + 1
    IN.lastError = b
    NR.log.say(2, "intake: capture failed before the " .. kind .. ": " .. tostring(b))
    return nil
end

function IN.guardAfter(b, kind)
    local landFn = IN.readAfterAndLand
    if kind == "drink" then landFn = IN.readDrinkAfterAndLand end
    local ok, err = pcall(landFn, b)
    if ok then return end
    IN.stats.failures = IN.stats.failures + 1
    IN.lastError = err
    NR.log.say(2, "intake: capture failed after the " .. kind .. ": " .. tostring(err))
end

-- The wrapper closure, made once per sentinel and kept in it. It names nothing from this file's load:
-- the sentinel S is a persistent global and the logic is looked up on NutritionRevamp per call.
local function makeWrapper(S, kind)
    return function(self, ...)
        local nr = NutritionRevamp
        local intake = nil
        if nr ~= nil and nr.server ~= nil then intake = nr.server.intake end
        local b = nil
        if intake ~= nil and not S.off and nr.isServer ~= nil and nr.isServer() then
            b = intake.guardBefore(self, kind)
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
--    into a temporary container and calls DrinkFluid on it itself (#2690): this wrapper never sees it,
--    and that route is out of this plan's scope.
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
--  * A LATER mod that replaces ISEatFoodAction.complete (or serverStop, or ISDrinkFluidAction.updateEat)
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
--    @range L1825-L1828 adds the item once, asserting no duplicate; its one consume-side caller,
--    CraftRecipeManager.consumeInputItemInternal @range L948-L949, passes one InventoryItem).
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
    record.stomach = record.stomach or K.stomach.seedFull(K.stomach.new())  -- seeded full like kinetics' first sight (Task 11 game choice): an eat before the first kinetics minute must not leave an unseeded stomach
    record.pool = record.pool or K.vector.new()
    K.stomach.ingest(record.stomach, vec)
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

-- At load, so the wrap is in place before the first eat (the wrapper itself gates on the side per
-- call), and again at OnServerStarted behind the side test. Both modes install: the mod owns intake in
-- takeover and overlay alike; only the stat tick differs by mode.
IN.install()
IN.installDrink()

if Events ~= nil and Events.OnServerStarted ~= nil then
    Events.OnServerStarted.Add(function()
        if not NR.isServer() then return end
        IN.install()
        IN.installDrink()
        if not IN.wired then
            IN.wired = true
            NR.log.say(1, "intake: wrappers " .. tostring(IN.wrapped) .. " drink " .. tostring(IN.wrappedDrink))
        end
    end)
end
