-- NR_Server_Hedonics.lua: the food hedonics seats (docs/superpowers/specs/2026-10-21-dials-and-hedonics-design.md@
-- program-record-v19 section B.2; the kernel is K.hedonics). Each rule runs at an eat, an ingredient add or the writer
-- minute, never per tick (Rule 6).
--  R1: the eat books its kcal into record.hedonics (H.atEat); the writer composes the ring's floor with monotony's.
--  R2: the seat is a server wrapper of ISAddItemInRecipe.complete, which holds the chef and, after the original, the
--     dish (#2658). EvolvedRecipe.addItem rewrites a dish's UnhappyChange at every add and fires no Lua event (#2657);
--     OnCooked was not chosen: it has no chef argument. A relief is scaled by the chef's Cooking level and the scale stamped in the
--     dish's modData (NR_PrepS); before the next add the vanilla value is restored, so a dish of many adds is scaled
--     once, never compounded. A client's syncItemFields wipes the server item's modData (#1241), so whenever the stamp
--     changes the dish's fields are synced to its owner, whose copy then carries the stamp back.
--  R3: before vanilla's eat a sad food's stored field is lowered so vanilla applies the scaled value with its own share
--     and utensil factor; after it the remainder's field is restored. Vanilla's part-eat sends the item-stats packet
--     while the field is lowered, so a part-eaten item still in a container is synced again (#4147).
--  R4: a dish's class is its main ingredient TYPE's (kcal summed per type); any other food's is the generated table's.
-- Shape (NR_Server_Intake.lua's): a sentinel global of its own (#0943); the wrapper ALWAYS calls the saved original
-- outside any pcall; the logic is read per call; the side test is per call (#0855). Never wrap a timed action's
-- `new`: complete is called off the class table.
-- Cost (Rule 6): per eat one Java read, more only for a sad food eaten Hungry; per ingredient add one read before and
-- the dish's value after, more only for a relief.
local NR = NutritionRevamp
local K = NR.kernel
NR.server.hedonics = {
    stats = { cooks = 0, prepped = 0, unprepped = 0, cookFailures = 0, passthrough = 0, allies = 0, restores = 0,
              alliesFailures = 0, booked = 0, plain = 0, healed = 0, bookFailures = 0 },
    wrappedCook = false,
    wired = false,
    lastError = nil,
    limitations = {
        "preparation quality (R2) scales an evolved dish's relief by the Cooking level of the chef of its last add, the whole dish at that chef's level; a dish whose stored UnhappyChange is 0 or more is vanilla's; a crafted (non-evolved) food, a cooked plain item and a spawned dish keep vanilla's mood; an add whose vanilla original raises after addItem (vanilla's Beer branch) keeps vanilla's mood; a client sync racing an add can still lose a stamp",
        "alliesthesia (R3) reads the HUNGER stat at the eat, which is the mod's written hunger in Mode 1 and vanilla's own in Overlay; it scales the whole read-time sad value, the state terms (stale, rotten, burnt, frozen, cold) included; a drink's mood is vanilla's; an eat whose vanilla original raises keeps the lowered field",
        "a dish's taste class is the class of its ingredient type of most kcal, each type's kcal the mod's table's whole-item value times its appearances in the ingredient list (no amounts are kept, #2650); a type the hedonics table does not carry counts for no class",
    },
}
local H = NR.server.hedonics

-- A global of its own, kept across a reload of this file and of NR_Core.
NR_HedonicsCook_Installed = NR_HedonicsCook_Installed or {}

-- Counted in stats[key], kept as lastError and logged. Returns nil.
function H.fail(key, err)
    H.stats[key] = H.stats[key] + 1
    H.lastError = tostring(err)
    NR.log.say(2, "hedonics: " .. H.lastError)
    return nil
end

-- ---------------------------------------------------------------------------------------------------
-- R1 and R4 at the eat.

-- 0 for a type the table does not carry.
function H.kcalOf(fullType)
    local D = NR.data and NR.data.nutrients
    if D == nil then return 0 end
    local seed = D.get(fullType)
    if seed == nil or not NR.finite(seed.calories) then return 0 end
    return seed.calories
end

-- A type with no class counts for none; extraTypes is IN.readBefore's Lua list of full types.
function H.dishClass(extraTypes)
    local at, types, classes, counts, kcals = {}, {}, {}, {}, {}
    for i = 1, #extraTypes do
        local t = extraTypes[i]
        local _, class = NR.data.hedonics.get(t)
        if class ~= nil then
            local k = at[t]
            if k == nil then
                k = #classes + 1
                at[t] = k
                types[k] = t
                classes[k] = class
                counts[k] = 0
            end
            counts[k] = counts[k] + 1
        end
    end
    for k = 1, #classes do kcals[k] = H.kcalOf(types[k]) * counts[k] end
    return K.hedonics.dishClass(classes, kcals)
end

-- A dish is never plain and takes its main ingredient type's class. No table: not plain, no class.
function H.tasteOf(b)
    if NR.data == nil or NR.data.hedonics == nil then return false, nil end
    if type(b.extraTypes) == "table" and #b.extraTypes > 0 then
        return false, H.dishClass(b.extraTypes)
    end
    return NR.data.hedonics.get(b.fullType)
end

-- Returns the class for monotony, nil on a failure (counted, never raised).
function H.atEat(record, b, kcal, ageH)
    local ok, class = pcall(H.book, record, b, kcal, ageH)
    if ok then return class end
    return H.fail("bookFailures", "booking failed: " .. tostring(class))
end

function H.book(record, b, kcal, ageH)
    local plain, class = H.tasteOf(b)
    local ring, healed = K.hedonics.heal(record.hedonics, ageH)
    if healed then
        H.stats.healed = H.stats.healed + 1
        NR.log.say(2, "hedonics: ring reset for " .. tostring(b.username))
    end
    record.hedonics = ring
    K.hedonics.book(ring, ageH, kcal, plain)
    b.plain = plain == true
    b.class = class
    H.stats.booked = H.stats.booked + 1
    if plain == true then H.stats.plain = H.stats.plain + 1 end
    return class
end

-- ---------------------------------------------------------------------------------------------------
-- R3 around vanilla's eat.

-- b.allies = { field, written, scale } is kept for the restore. Under its own pcall.
function H.alliesBefore(b)
    if type(b) ~= "table" then return end
    local ok, err = pcall(H.allies, b)
    if not ok then H.fail("alliesFailures", "alliesthesia failed before the eat: " .. tostring(err)) end
end

function H.allies(b)
    local item = b.item
    local u = NR.num(item, "getUnhappyChange", nil)        -- the read-time value vanilla applies (state terms included)
    if u == nil or not (u > 0) or CharacterStat == nil then return end
    local hunger = NR.num(NR.obj(b.player, "getStats"), "get", nil, CharacterStat.HUNGER)
    if hunger == nil then return end
    local scaled = K.hedonics.allies(u, hunger)
    if not (scaled < u) then return end
    local field = NR.num(item, "getUnhappyChangeUnmodified", nil)
    if field == nil then return end
    local written = K.hedonics.alliesField(field, u, hunger)
    NR.call(item, "setUnhappyChange", written)
    b.allies = { field = field, written = written, scale = scaled / u }
    H.stats.allies = H.stats.allies + 1
end

-- Under its own pcall.
function H.alliesAfter(b)
    if type(b) ~= "table" or b.allies == nil then return end
    local ok, err = pcall(H.restore, b)
    if not ok then H.fail("alliesFailures", "alliesthesia failed after the eat: " .. tostring(err)) end
end

function H.restore(b)
    local a = b.allies
    local after = NR.num(b.item, "getUnhappyChangeUnmodified", nil)
    local q = nil
    if a.written == 0 and type(b.rawBefore) == "number" and b.rawBefore ~= 0 then
        local raw = NR.num(b.item, "getHungChange", nil)
        if raw ~= nil then q = raw / b.rawBefore end
    end
    local restored = K.hedonics.alliesRestore(a.field, a.written, after, q)
    if restored == nil then return end
    NR.call(b.item, "setUnhappyChange", restored)
    H.stats.restores = H.stats.restores + 1
    if NR.obj(b.item, "getContainer") ~= nil then H.sync(b.item) end
end

-- sendItemStats, a server global (#3567): the mood fields ride it when non-zero.
function H.sync(item)
    if sendItemStats ~= nil then sendItemStats(item) end
end

-- ---------------------------------------------------------------------------------------------------
-- R2 at the add-ingredient seat.

-- Under its own pcall; the after half runs whatever this one did.
function H.cookBefore(action)
    H.stats.cooks = H.stats.cooks + 1
    local ok, err = pcall(H.unprepBase, action)
    if not ok then H.fail("cookFailures", "the add's restore failed: " .. tostring(err)) end
    return true
end

function H.unprepBase(action)
    local base = action.baseItem
    local md = NR.obj(base, "getModData")
    if type(md) ~= "table" or md.NR_PrepS == nil then return end
    local stored = NR.num(base, "getUnhappyChangeUnmodified", nil)
    if stored ~= nil then
        local v = K.hedonics.unprep(stored, md.NR_PrepS)
        if v ~= stored then
            NR.call(base, "setUnhappyChange", v)
            H.stats.unprepped = H.stats.unprepped + 1
        end
    end
    md.NR_PrepS = nil
    action.nrStamp = true                                  -- the stamp changed: cookAfter syncs the dish's fields
end

-- The original reassigns baseItem, so the dish is read after it. Under its own pcall.
function H.cookAfter(action)
    local ok, err = pcall(H.prepDish, action)
    if not ok then H.fail("cookFailures", "the add's scale failed: " .. tostring(err)) end
    if action.nrStamp then
        action.nrStamp = nil
        local ok2, err2 = pcall(NR.call, action.baseItem, "syncItemFields")
        if not ok2 then H.fail("cookFailures", "the add's field sync failed: " .. tostring(err2)) end
    end
end

function H.prepDish(action)
    local dish = action.baseItem
    local v = NR.num(dish, "getUnhappyChangeUnmodified", nil)
    if v == nil or not (v < 0) or Perks == nil then return end
    local level = NR.num(action.character, "getPerkLevel", nil, Perks.Cooking)
    if level == nil then return end
    local md = NR.obj(dish, "getModData")
    if type(md) ~= "table" then return end
    NR.call(dish, "setUnhappyChange", K.hedonics.prep(v, level))
    md.NR_PrepS = K.hedonics.prepScale(level)
    action.nrStamp = true
    H.stats.prepped = H.stats.prepped + 1
    H.sync(dish)
end

-- Made once per sentinel; it names nothing from this file's load.
local function makeWrapper(S, kind)
    return function(self, ...)
        local nr = NutritionRevamp
        local h = nil
        if nr ~= nil and nr.server ~= nil then h = nr.server.hedonics end
        local seen = false
        if h ~= nil and nr.isServer ~= nil and nr.isServer() then
            seen = h.cookBefore(self)
        elseif h ~= nil then
            h.stats.passthrough = h.stats.passthrough + 1     -- the client
        end
        local result = S.orig(self, ...)                       -- every path; never inside a pcall
        if seen then h.cookAfter(self) end
        return result
    end
end

-- ISAddItemInRecipe is vanilla's shared/TimedActions file, loaded before every server/ file. Never touches ISAddItemInRecipe.new.
function H.install()
    local cls = ISAddItemInRecipe
    if cls ~= nil then
        NR.installWrap(NR_HedonicsCook_Installed, cls, "complete", makeWrapper, "cook",
            "hedonics: ISAddItemInRecipe.complete")
    end
    local S = NR_HedonicsCook_Installed
    H.wrappedCook = cls ~= nil and S.wrapper ~= nil and S.class == cls
    return H.wrappedCook
end

-- At load, and again at OnServerStarted behind the side test.
H.install()

if Events ~= nil and Events.OnServerStarted ~= nil then
    Events.OnServerStarted.Add(function()
        if not NR.isServer() then return end
        H.install()
        if not H.wired then
            H.wired = true
            NR.log.say(1, "hedonics: add-ingredient wrapper " .. tostring(H.wrappedCook))
        end
    end)
end
