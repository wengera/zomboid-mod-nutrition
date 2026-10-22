-- NR_Server_Hedonics.lua -- the food hedonics seats (Plan 19 Task 6; spec docs/superpowers/specs/
-- 2026-10-21-dials-and-hedonics-design.md section B.2; the kernel is NR_Kernel_Hedonics.lua, K.hedonics). Each rule
-- runs at an eat, an ingredient add or the existing writer minute, never per tick (Rule 6):
--  R1 plain energy: the eat books its landed kcal, and its plain kcal, into record.hedonics, the ring of online hours
--     (H.atEat, called by NR_Server_Intake's IN.monotony once per landed eat); the writer minute composes the ring's
--     floor with monotony's (NR_Server_Writer W.monotony), never as a raw add. A dish books as not plain; an
--     ingredient add books nothing (it is no eat).
--  R2 preparation quality: the seat is a server wrapper of ISAddItemInRecipe.complete, the add-ingredient action's
--     completion, which holds the chef and, after its call of the original, the dish (#2658). The dish's mood is set
--     there and nowhere else: EvolvedRecipe.addItem zeroes a new dish's UnhappyChange and rewrites it at every add
--     (an ingredient's -5 term, a spice's useSpice, #0381, #4127), and it fires no Lua event (#2657). OnCooked was not
--     chosen: it has no chef argument (in multiplayer the cook need not be the eater), and the cook transition sets no
--     dish mood. After the original, a relief (the stored UnhappyChange under 0) is scaled by the chef's Cooking level
--     (K.hedonics.prep) and the scale is stamped in the dish's modData (NR_PrepS); before the next add the stamp is read
--     back and the vanilla value restored (K.hedonics.unprep), so vanilla's arithmetic always runs on its own value and
--     a dish of many adds is scaled once, by the last add's chef, never compounded. A part-eaten dish keeps the stamp:
--     vanilla scales its stored value linearly, which the restore divides back exactly.
--  R3 alliesthesia: before vanilla's eat (NR_Server_Intake's guardBefore, an eat or a cancel), a sad food (its
--     read-time UnhappyChange over 0) eaten while the HUNGER stat (the hunger the mod's writer writes) is over the
--     ALLIES_LEVEL threshold has its stored field lowered so vanilla's own JustAteFood applies the scaled value with its
--     own share and utensil factor (K.hedonics.alliesField); after the eat the remainder's field is restored to what it
--     would have kept (K.hedonics.alliesRestore). No stat is written here.
--  R4 taste class: the eat's class goes into K.monotony.record beside the type. A dish's class is its main
--     ingredient TYPE's (ruling T6-1 as refined: the kcal of each ingredient type summed, the type of most kcal wins,
--     K.hedonics.dishClass over one entry a type); any other food's is the generated table's (NR_Data_Hedonics).
--
-- Shape (the intake wrappers', NR_Server_Intake.lua): the sentinel is a global of its own (#0943); install() is
-- idempotent through NR.installWrap; the wrapper ALWAYS calls the saved original outside any pcall and returns its
-- result, and every read and write around it runs under a pcall, counted and named on failure, so a mod bug never
-- blocks an add or an eat; the logic is read off NutritionRevamp.server.hedonics per call; the side test is per call
-- (this server/ file also runs in the client VM, #0855); every Java global (ISAddItemInRecipe, Perks, CharacterStat,
-- sendItemStats, Events) is named only inside a function behind a nil check, so the file loads with no engine. Never
-- wrap a timed action's `new` (CLAUDE.md s6): complete is called off the class table.
--
-- Cost (Rule 6): per eat, one Java read (getUnhappyChange); a sad food adds the HUNGER read (two calls), and a scaled
-- one a read and a write before and a read, a write and an item sync after. Per ingredient add, one read (the base's
-- modData) before, and after it the dish's stored value; a relief adds the Cooking level, the modData, a write and an
-- item sync. The dish class reads Lua tables only. No @fastpath region.
local NR = NutritionRevamp
local K = NR.kernel
NR.server.hedonics = {
    stats = { cooks = 0, prepped = 0, unprepped = 0, cookFailures = 0, passthrough = 0, allies = 0, restores = 0,
              alliesFailures = 0, booked = 0, plain = 0, healed = 0, bookFailures = 0 },
    wrappedCook = false,
    wired = false,
    lastError = nil,
    limitations = {
        "preparation quality (R2) scales an evolved dish's relief by the Cooking level of the chef of its last add, the whole dish at that chef's level; a dish whose stored UnhappyChange is 0 or more is vanilla's; a crafted (non-evolved) food, a cooked plain item and a spawned dish keep vanilla's mood",
        "alliesthesia (R3) reads the HUNGER stat at the eat, which is the mod's written hunger in Mode 1 and vanilla's own in Overlay; it scales the whole read-time sad value, the state terms (stale, rotten, burnt, frozen, cold) included; a drink's mood is vanilla's",
        "a dish's taste class is the class of its ingredient type of most kcal, each type's kcal the mod's table's whole-item value times its appearances in the ingredient list (no amounts are kept, #2650); a type the hedonics table does not carry counts for no class",
    },
}
local H = NR.server.hedonics

-- The sentinel: a global of its own, kept across a reload of this file and of NR_Core.
NR_HedonicsCook_Installed = NR_HedonicsCook_Installed or {}

-- A failure in one of the seats: counted in stats[key], kept as lastError and logged. Returns nil.
function H.fail(key, err)
    H.stats[key] = H.stats[key] + 1
    H.lastError = tostring(err)
    NR.log.say(2, "hedonics: " .. H.lastError)
    return nil
end

-- ---------------------------------------------------------------------------------------------------
-- R1 and R4 at the eat.

-- The whole-item kcal of one type in the mod's table, 0 for a type it does not carry.
function H.kcalOf(fullType)
    local D = NR.data and NR.data.nutrients
    if D == nil then return 0 end
    local seed = D.get(fullType)
    if seed == nil or not NR.finite(seed.calories) then return 0 end
    return seed.calories
end

-- A dish's taste class (ruling T6-1 as refined): one entry an ingredient TYPE, its kcal the type's whole-item kcal
-- times its appearances in the list, its class the table's; a type with no class counts for none. K.hedonics.dishClass
-- picks the type of most kcal (the first on a tie). extraTypes is a Lua list of full types (IN.readBefore's).
function H.dishClass(extraTypes)
    local at, classes, kcals = {}, {}, {}
    for i = 1, #extraTypes do
        local t = extraTypes[i]
        local _, class = NR.data.hedonics.get(t)
        if class ~= nil then
            local k = at[t]
            if k == nil then
                k = #classes + 1
                at[t] = k
                classes[k] = class
                kcals[k] = 0
            end
            kcals[k] = kcals[k] + H.kcalOf(t)
        end
    end
    return K.hedonics.dishClass(classes, kcals)
end

-- An eat's plain flag and taste class off its before-snapshot b: a dish (an ingredient list) is never plain and takes
-- its main ingredient type's class; anything else is the table's reading of its full type. No table: not plain, no
-- class.
function H.tasteOf(b)
    if NR.data == nil or NR.data.hedonics == nil then return false, nil end
    if type(b.extraTypes) == "table" and #b.extraTypes > 0 then
        return false, H.dishClass(b.extraTypes)
    end
    return NR.data.hedonics.get(b.fullType)
end

-- The booking (IN.monotony calls it once per landed eat with energy, before monotony's own): the record's ring healed
-- (a corrupt one reset and counted) and the eat's kcal booked, plain or not, at world age ageH; b.plain and b.class
-- set for the landing's lastIntake. Returns the class for monotony, nil on a failure (counted, never raised).
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

-- Before the original (IN.guardBefore, an eat or a cancel, b the before-snapshot or nil): the scaled field written and
-- b.allies = { field, written, scale } kept for the restore. Under its own pcall.
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

-- After the original (IN.guardAfter): the remainder's field restored and the item synced while it is still in a
-- container. Under its own pcall.
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

-- The item-stats packet to the item's owner (sendItemStats, a server global, #3567): the mood fields ride it when non-zero.
function H.sync(item)
    if sendItemStats ~= nil then sendItemStats(item) end
end

-- ---------------------------------------------------------------------------------------------------
-- R2 at the add-ingredient seat.

-- Before the original: a stamped base's vanilla value restored and its stamp cleared, so vanilla's add runs on its own
-- value. Under its own pcall; the after half runs whatever this one did.
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
end

-- After the original: the dish (the action's baseItem, which the original reassigns) scaled by the chef's Cooking
-- level when its stored value is a relief, the scale stamped and the dish synced. Under its own pcall.
function H.cookAfter(action)
    local ok, err = pcall(H.prepDish, action)
    if not ok then H.fail("cookFailures", "the add's scale failed: " .. tostring(err)) end
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
    H.stats.prepped = H.stats.prepped + 1
    H.sync(dish)
end

-- The wrapper closure, made once per sentinel and kept in it; it names nothing from this file's load.
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

-- Installs the wrap when ISAddItemInRecipe exists (vanilla's shared/TimedActions file, loaded before every server/
-- file); returns whether it is in place. Never touches ISAddItemInRecipe.new.
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

-- At load, so the wrap is in place before the first add (the wrapper gates on the side per call), and again at
-- OnServerStarted behind the side test.
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
