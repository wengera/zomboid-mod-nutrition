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
--  * Every Java global (ISEatFoodAction, Events, getGameTime) is named only inside a function, behind a
--    nil check, so the file loads with no engine (testing/tests/kernel/test_intake_shape.py).
--  * Java lists are walked with size()/get(i), never `#` (#0940).
--
-- The capture runs once per eat on the server, never per tick: no @fastpath region in this file.
local NR = NutritionRevamp
local K = NR.kernel
NR.server.intake = { wrapped = false, wrappedComplete = false, wrappedServerStop = false, wired = false,
                     stats = { eats = 0, cancels = 0, landed = 0, failures = 0, passthrough = 0 },
                     lastError = nil }
local IN = NR.server.intake

-- The sentinels: `or {}` keeps the existing table when this file is re-run, and NR_Core's reset never
-- touches them. Each holds orig (the saved method), wrapper (the mod's closure), class (the class table
-- the wrap went into) and off (a pass-through switch for an uninstall that could not unwind).
NR_IntakeComplete_Installed = NR_IntakeComplete_Installed or {}
NR_IntakeServerStop_Installed = NR_IntakeServerStop_Installed or {}

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
-- thirst before IS that fraction, and of the whole and of what was left alike (no rescale to undo).
-- Raw thirst is negative like hunger; the sign cancels. Nothing readable -> 0, 0 (nothing landed).
function IN.fractionOf(rawBefore, rawAfter, instBase, thirstBefore, thirstAfter)
    if instBase == nil or instBase == 0 then
        if type(thirstBefore) == "number" and type(thirstAfter) == "number" and thirstBefore ~= 0 then
            local f = K.clamp((thirstBefore - thirstAfter) / thirstBefore, 0, 1)
            return f, f
        end
        return 0, 0
    end
    return IN.shareEaten(rawBefore, rawAfter, rawBefore), IN.shareEaten(rawBefore, rawAfter, instBase)
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
-- both from its raw thirst (fractionOf); thirstAfter is the raw thirst after the original ran.
-- lookup(fullType) -> seed vector or nil (the server passes NR.data.nutrients.get).
function IN.assemble(b, rawAfter, lookup, thirstAfter)
    local frac, share = IN.fractionOf(b.rawBefore, rawAfter, b.instBase, b.thirstBefore, thirstAfter)
    if share <= 0 or frac <= 0 then return nil, nil, {}, share, frac end
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
    local scriptHunger = read(read(item, "getScriptItem"), "getHungerChange")
    b.scriptHunger = 0
    if type(scriptHunger) == "number" then b.scriptHunger = scriptHunger / 100 end
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
    local rawAfter = read(b.item, "getHungChange")         -- 0 when consumed at fraction 1 (#0058)
    if type(rawAfter) ~= "number" then
        error("intake: getHungChange unreadable after the original for " .. b.fullType)
    end
    local thirstAfter = read(b.item, "getThirstChangeUnmodified") -- the raw thirst again (#0005)
    if NR.data == nil or NR.data.nutrients == nil then error("intake: NR.data.nutrients absent") end
    local vec, source, missing, share, frac = IN.assemble(b, rawAfter, NR.data.nutrients.get, thirstAfter)
    if vec == nil then return nil end                      -- a cancel under vanilla's guards, or a no-op
    local record = NR.server.store.get(b.username, worldAge())
    if record == nil then error("intake: no store record for " .. tostring(b.username)) end
    record.stomach = record.stomach or K.stomach.new()
    record.pool = record.pool or K.vector.new()
    K.stomach.ingest(record.stomach, vec)
    record.lastIntake = { fullType = b.fullType, source = source, share = share, frac = frac,
                          missing = missing }
    IN.stats.landed = IN.stats.landed + 1
    NR.log.say(3, "intake: " .. b.fullType .. " for " .. tostring(b.username) .. " source " .. source
        .. " share " .. tostring(share))
    return vec
end

-- The two halves the wrapper calls, each under its own pcall; the original runs between them, outside.
function IN.guardBefore(action, kind)
    if kind == "cancel" then
        IN.stats.cancels = IN.stats.cancels + 1
    else
        IN.stats.eats = IN.stats.eats + 1
    end
    local ok, b = pcall(IN.readBefore, action)
    if ok then return b end
    IN.stats.failures = IN.stats.failures + 1
    IN.lastError = b
    NR.log.say(2, "intake: capture failed before the " .. kind .. ": " .. tostring(b))
    return nil
end

function IN.guardAfter(b, kind)
    local ok, err = pcall(IN.readAfterAndLand, b)
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

local function installOne(S, method, kind)
    local cls = ISEatFoodAction
    local cur = cls[method]
    if cur == nil then return false end
    S.off = false
    if cur == S.wrapper then return true end               -- already the outermost: idempotent
    if S.wrapper ~= nil and S.class == cls then return true end -- still in the chain below a later wrap
    S.orig = cur
    S.wrapper = S.wrapper or makeWrapper(S, kind)
    S.class = cls
    cls[method] = S.wrapper
    NR.log.say(2, "intake: ISEatFoodAction." .. method .. " wrapped")
    return true
end

local function uninstallOne(S, method)
    local cls = ISEatFoodAction
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
    installOne(NR_IntakeComplete_Installed, "complete", "eat")
    installOne(NR_IntakeServerStop_Installed, "serverStop", "cancel")
    return mirror()
end

function IN.uninstall()
    uninstallOne(NR_IntakeComplete_Installed, "complete")
    uninstallOne(NR_IntakeServerStop_Installed, "serverStop")
    return mirror()
end

-- At load, so the wrap is in place before the first eat (the wrapper itself gates on the side per
-- call), and again at OnServerStarted behind the side test. Both modes install: the mod owns intake in
-- takeover and overlay alike; only the stat tick differs by mode.
IN.install()

if Events ~= nil and Events.OnServerStarted ~= nil then
    Events.OnServerStarted.Add(function()
        if not NR.isServer() then return end
        IN.install()
        if not IN.wired then
            IN.wired = true
            NR.log.say(1, "intake: wrappers " .. tostring(IN.wrapped))
        end
    end)
end
