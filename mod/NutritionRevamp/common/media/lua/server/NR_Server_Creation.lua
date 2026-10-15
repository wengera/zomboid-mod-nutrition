-- NR_Server_Creation.lua -- the creation handler (spec section 3.2, Plan 13 Task 17): when the server's OnNewGame resets a
-- record (NR_Server_Players fires P.onNewGame after store.reset, or from its pending reset), the character's picks are
-- validated and the starting body is built from what survives. OnNewGame fires on the server from
-- CreatePlayerPacket.processServer @1074-@1082 L291, after IsoPlayer.applyTraits (L282) has set every trait the client
-- sent and before the save (trait-levers sections 3-4); the server enforces neither the point total nor an exclusion.
--
-- 1. Validation (ruling 13-16), on the server's own definitions (CharacterTraitDefinition.getCharacterTraitDefinition).
--    The strip order never reads the list's order (fix 3): the server's getKnownTraits() is not the client's sent order
--    (x422, Task 0's check 5: sent strong, stout, obese, overweight; held obese, overweight, out of shape, strong), and
--    vanilla's band listener rewrites the muscle and Fitness traits during applyTraits. A free trait (the profession's
--    grants, or a held trait's grants) is never stripped; a profession trait (isFree) that no grant names is stripped
--    (fix 2, ruling 13-16). A non-free pick that excludes a free trait is stripped. Of two non-free picks that exclude
--    each other, the one with the higher absolute cost is stripped, a tie stripping the name first in alphabetical
--    order (CRE.before): the picks are walked in that order, and each is stripped when it excludes a pick still held
--    that comes later in it. A pair excludes when either definition's getMutuallyExclusiveTraits holds the other, when
--    isMutuallyExclusive answers true either way (Task 16's ruling I2: Weight Gain's Athletic, Fit and Emaciated pairs
--    sit on Weight Gain alone); the mod adds no pair of its own (Plan 13 Task 10c lifted ruling 13-46's muscle and thin
--    pairs: a thin pick is fat-only). Then, while the creation screen's
--    remaining points read below 0, the kept non-free pick with the highest positive cost is stripped, a tie stripping
--    the name first in alphabetical order: a trait with a cost of 0 or below never raises the total (removing a bad
--    trait lowers the negative-trait offset by at most one, CharacterCreationProfession.lua:918-936).
--    The remaining points are the screen's PointToSpend (lua:client/OptionScreens/CharacterCreationProfession.lua:860-867):
--      profession cost (:479) + SandboxVars.CharacterFreePoints (:865-866) - the sum of the non-free picks' costs
--      (addTrait :645, free traits :459-466 and :654-659 never touch it) - the offset (:862, :918-936: n the selected
--      traits with a negative cost, free ones included; NegativeTraitsPenalty 2 floor(n/3), 3 floor(n/2), 4 n - 1)
--    and the list is legal at 0 or more (NEXT is disabled below 0, :827-829). An unreadable profession definition skips
--    the point check (nothing is stripped on a guess). A stripped trait is removed from the collection, its XP boosts
--    reverted (setPerkLevelDebug(perk, level - boost) clamped to [0, 10], then setXPToLevel; applyTraits applied them,
--    trait-levers section 3.1), and logged at level 1.
--    The muscle pick is inferred first (CRE.inferMuscle, fix 1; NR_Server_Metabolism's MET.inferMuscle, which first
--    sight shares since Task 17b fix 1): applyTraits climbs Strength with LevelPerk and vanilla's
--    listener (XpUpdate.lua:196-218) swaps the muscle band at every step, so the trait held is the native level's band,
--    not the pick. The four muscle blocks keep vanilla's Strength boosts (NR_Traits_Body.txt), so native - 5 - the
--    profession's Strength boost - every other held trait's Strength boost is the pick's boost, mapped through
--    MET.MUSCLE_BY_BOOST; a native level at 0 or 10 (clamped), an unreadable one or an unmapped offset falls back to the
--    held band trait. Validation reads the inferred pick in place of the held band trait (its cost and exclusions; a
--    strip removes the held one), and a held band trait with no pick behind it (a profession's boost) is vanilla's,
--    never validated.
-- 2. The body: K.body.create over the inferred muscle pick and the weight-band trait held after validation (CRE.picks;
--    Emaciated is read as Very Underweight by the kernel), under the profession's Strength boost (Task 17b: Angus,
--    "treat it like a small trait"; the start level is the pick's plus the boost, clamped to [0, 10]), at the
--    effective sex (NR.SexSpecific) and the reset's age, through NR_Server_Metabolism's builder, so OnNewGame and
--    first sight build one way; first sight then finds the body present.
-- 3. The writes, in this order: the weight (lm + lx + fm, overwriting applyWeightFromTraits' 50/60/70/95/105 kg,
--    trait-levers section 3.2); the Strength level (STR.writeLevel: LevelPerk steps, whose vanilla listener swaps the
--    muscle band, XpUpdate.lua:200-217), then the muscle band re-asserted for the native level (STR.remap: a strip's
--    setPerkLevelDebug swaps no band, and a write that takes no step fires no listener); then the five weight-band traits (WGT.writeTraits), last, so they are final.
--    Fitness band traits are vanilla's and stay (spec section 14). body.levelDue stays true after the level write, so
--    the first server minute writes the level again and re-pins the XP fraction OnNewGame's write loses (x433 read
--    XP 10500 at a shown 3.83; Plan 13 Task 10c ruling: cost if wrong, one extra write).
--
-- Java statics (CharacterTraitDefinition, CharacterProfessionDefinition, transformIntoKahluaTable) are called with a dot
-- under pcall, as vanilla calls them; every other Java read goes through NR.call. Each global is named only inside a
-- function behind a nil check, so the file loads with no engine (testing/tests/kernel/test_creation_shape.py).
-- Event-driven, once per new character: no clock work (Rule 6).
local NR = NutritionRevamp
local K = NR.kernel
NR.server.creation = {
    stats = { created = 0, stripped = 0, failures = 0, budgetUnread = 0, budgetUnfixed = 0, pushes = 0,
              pushMissing = 0 },
    lastError = nil,
    wired = false,
    limitations = {
        "the server keeps no pick order (x422 measured its getKnownTraits order unlike the client's sent order), so an illegal list loses its costliest pick, a tie its alphabetically first, never its last-picked one (ruling 13-16, fix 3)",
        "a stripped trait's XP boosts are reverted from the level applyTraits clamped to [0, 10], so a boost that was clamped reverts too far",
        "two muscle picks from a modified client collapse into the one pick their summed boost maps to",
        "a stripped trait's learning-rate entry in the descriptor's XP boost map stays (the engine's map takes integers; it is not edited from Lua)",
        "the muscle pick is inferred from the native Strength level less the profession's and the other held traits' Strength boosts; at a clamped level (0 or 10) it is the held band trait, which a profession's Strength boost can have moved",
    },
}
local CRE = NR.server.creation

local num, obj, flag = NR.num, NR.obj, NR.flag

-- The perk level a revert is clamped to.
CRE.LEVEL_MAX = 10

-- A Java static called with a dot (cls.name(...)) under pcall; nil when the class or member is absent or raises.
local function static(cls, name, ...)
    if cls == nil then return nil end
    local f = cls[name]
    if f == nil then return nil end
    local ok, v = pcall(f, ...)
    if ok then return v end
    return nil
end

-- The server's definition of a trait, or nil.
local function defOf(t)
    if CharacterTraitDefinition == nil then return nil end
    return static(CharacterTraitDefinition, "getCharacterTraitDefinition", t)
end

-- The elements of a Java list (NR_Server_Metabolism's walker, MET.walk).
local function walk(list)
    return NR.server.metabolism.walk(list)
end

-- A trait's name for the log and the stripped list.
local function nameOf(t)
    local ok, v = NR.try(t, "getName")
    if ok and type(v) == "string" then return v end
    return tostring(t)
end

-- Whether a definition's own exclusion list holds trait t.
local function lists(def, t)
    return flag(obj(def, "getMutuallyExclusiveTraits"), "contains", t)
end

-- Whether entries a and b exclude each other, in both directions (Task 16's ruling I2).
function CRE.excludes(a, b)
    if a.def == nil or b.def == nil then return false end
    return lists(a.def, b.t) or lists(b.def, a.t)
        or flag(a.def, "isMutuallyExclusive", b.def) or flag(b.def, "isMutuallyExclusive", a.def)
end

-- The strip order (fix 3): the higher absolute cost first, a tie by name in alphabetical order. Among the kept
-- positive picks the first in it is also the costliest, so the budget strip and the exclusion strip read one order.
function CRE.before(a, b)
    local ca, cb = math.abs(a.cost), math.abs(b.cost)
    if ca ~= cb then return ca > cb end
    return a.name < b.name
end

-- The profession's definition off the player's descriptor, or nil (NR_Server_Metabolism's reader, shared with first
-- sight).
local function professionDef(player)
    return NR.server.metabolism.professionDef(player)
end

-- The negative-trait offset (CharacterCreationProfession.lua:918-936) for n traits with a negative cost.
function CRE.offset(penalty, n)
    if n <= 0 then return 0 end
    if penalty == 2 then return math.floor(n / 3) end
    if penalty == 3 then return math.floor(n / 2) end
    if penalty == 4 then return n - 1 end
    return 0
end

-- The sandbox's NegativeTraitsPenalty (1 when unread) and CharacterFreePoints (0 when unread).
local function sandboxPoints()
    local penalty = num(obj(NR.sandbox(), "getOptionByName", "NegativeTraitsPenalty"), "getValue", 1)
    local free = 0
    local sv = SandboxVars
    if type(sv) == "table" and NR.finite(sv.CharacterFreePoints) then free = sv.CharacterFreePoints end
    return penalty, free
end

-- The remaining points over the free and kept entries (the formula in the header).
function CRE.remaining(profCost, freePoints, penalty, free, kept)
    local spent, negatives = 0, 0
    for i = 1, #kept do
        spent = spent + kept[i].cost
        if kept[i].cost < 0 then negatives = negatives + 1 end
    end
    for i = 1, #free do
        if free[i].cost < 0 then negatives = negatives + 1 end
    end
    return profCost + freePoints - spent - CRE.offset(penalty, negatives)
end

-- A set keyed by the traits of a Java list of traits.
local function addGrants(set, list)
    local ts = walk(list)
    for i = 1, #ts do set[ts[i]] = true end
end

-- A boost value off transformIntoKahluaTable, and a definition's Strength boost: NR_Server_Metabolism's readers,
-- shared with first sight (Task 17b).
local function boostOf(v)
    return NR.server.metabolism.boostOf(v)
end

local function strengthBoost(def)
    return NR.server.metabolism.strengthBoost(def)
end

-- The muscle band name of trait t, or nil.
local function muscleName(t)
    if CharacterTrait == nil then return nil end
    local names = K.strength.MUSCLE_TRAITS
    for i = 1, #names do
        if CharacterTrait[names[i]] == t then return names[i] end
    end
    return nil
end

-- CRE.inferMuscle(player, pdef, known) -> the muscle pick's name, false for no pick, or nil when the native level
-- cannot tell (unreadable, clamped at 0 or 10, no profession definition, or an offset no muscle boost makes).
-- known is the held traits; their muscle band traits are not subtracted (their boost is the unknown).
function CRE.inferMuscle(player, pdef, known)
    return NR.server.metabolism.inferMuscle(player, pdef, known)
end

-- Reverts a stripped trait's XP boosts: each boosted perk's level less the boost, clamped to [0, 10], written with
-- setPerkLevelDebug (no LevelPerk event, #2870) and setXPToLevel.
local function revertBoosts(player, def)
    local map = obj(def, "getXpBoosts")
    if map == nil or transformIntoKahluaTable == nil then return end
    local okT, tbl = pcall(transformIntoKahluaTable, map)
    if not okT or type(tbl) ~= "table" then return end
    local xp = obj(player, "getXp")
    for perk, v in pairs(tbl) do
        local boost = boostOf(v)
        local level = num(player, "getPerkLevel", nil, perk)
        if boost ~= nil and boost ~= 0 and level ~= nil then
            local to = K.clamp(level - boost, 0, CRE.LEVEL_MAX)
            NR.call(player, "setPerkLevelDebug", perk, to)
            NR.call(xp, "setXPToLevel", perk, to)
        end
    end
end

-- One strip: the trait removed, its boosts reverted, the strip logged at level 1 and counted.
local function strip(player, coll, e, why, stripped)
    if e.held ~= nil then NR.call(coll, "remove", e.held) end
    if e.def ~= nil then revertBoosts(player, e.def) end
    stripped[#stripped + 1] = e.name
    CRE.stats.stripped = CRE.stats.stripped + 1
    NR.log.say(1, "creation: " .. tostring(NR.obj(player, "getUsername")) .. " loses " .. e.name .. " (" .. why .. ")")
end

-- CRE.validate(player) -> the names of the stripped traits, in strip order (empty when nothing was illegal or the
-- traits or the definitions are unreadable). One trait push when anything was stripped.
function CRE.validate(player)
    local stripped = {}
    if CharacterTraitDefinition == nil then return stripped end
    local coll = obj(player, "getCharacterTraits")
    local known = walk(obj(coll, "getKnownTraits"))
    local pdef = professionDef(player)
    local grants = {}
    addGrants(grants, obj(pdef, "getGrantedTraits"))
    local muscle = CRE.inferMuscle(player, pdef, known)
    local entries = {}
    local placed = false
    local function enter(t, held)
        local def = defOf(t)
        addGrants(grants, obj(def, "getGrantedTraits"))
        entries[#entries + 1] = { t = t, def = def, name = nameOf(t), cost = num(def, "getCost", 0), held = held }
    end
    for i = 1, #known do
        local t = known[i]
        if muscle == nil or muscleName(t) == nil then
            enter(t, t)
        elseif muscle and not placed then
            enter(CharacterTrait[muscle], t)            -- the inferred pick in place of the held band trait
            placed = true
        end                                             -- else vanilla's band, no pick behind it: not validated
    end
    if muscle and not placed then enter(CharacterTrait[muscle], nil) end
    local free, kept = {}, {}
    for i = 1, #entries do
        local e = entries[i]
        if grants[e.t] == true then free[#free + 1] = e end
    end
    local picks = {}
    for i = 1, #entries do
        local e = entries[i]
        if grants[e.t] ~= true then
            if flag(e.def, "isFree") then
                strip(player, coll, e, "a profession trait no grant names", stripped)
            else
                local hit = nil
                for j = 1, #free do
                    if hit == nil and CRE.excludes(e, free[j]) then hit = free[j] end
                end
                if hit ~= nil then
                    strip(player, coll, e, "excluded by " .. hit.name, stripped)
                else
                    picks[#picks + 1] = e
                end
            end
        end
    end
    table.sort(picks, CRE.before)
    local gone = {}
    for i = 1, #picks do
        local e = picks[i]
        local hit = nil
        for j = i + 1, #picks do
            if hit == nil and not gone[j] and CRE.excludes(e, picks[j]) then hit = picks[j] end
        end
        if hit ~= nil then
            gone[i] = true
            strip(player, coll, e, "excluded by " .. hit.name, stripped)
        else
            kept[#kept + 1] = e
        end
    end
    if pdef == nil then
        CRE.stats.budgetUnread = CRE.stats.budgetUnread + 1
    else
        local penalty, freePoints = sandboxPoints()
        local profCost = num(pdef, "getCost", 0)
        local rem = CRE.remaining(profCost, freePoints, penalty, free, kept)
        while rem < 0 do
            local at = nil
            for j = 1, #kept do
                if at == nil and kept[j].cost > 0 then at = j end      -- kept is in CRE.before's order
            end
            if at == nil then
                CRE.stats.budgetUnfixed = CRE.stats.budgetUnfixed + 1
                NR.log.say(1, "creation: the point total stays below 0 with no positive pick left to strip")
                break
            end
            local e = table.remove(kept, at)
            strip(player, coll, e, "over the point total", stripped)
            rem = CRE.remaining(profCost, freePoints, penalty, free, kept)
        end
    end
    if #stripped > 0 then NR.pushTraits(player, CRE.stats) end
    return stripped
end

-- CRE.picks(player) -> muscle, weight, profBoost: the inferred muscle pick (CRE.inferMuscle; the held band trait when
-- the level cannot tell), the weight-band trait held (NR_Server_Metabolism's lists), each nil for none, and the
-- profession's Strength boost the inference read (0 when unreadable; Task 17b: it raises the start like a small trait).
function CRE.picks(player)
    local MET = NR.server.metabolism
    local traits = obj(player, "getCharacterTraits")
    local pdef = professionDef(player)
    local muscle = MET.musclePick(player, traits, pdef)
    return muscle, MET.heldTrait(traits, K.traits.WEIGHT_TRAITS), strengthBoost(pdef)
end

local function create(username, player, record)
    local ageH = record.firstSeen
    if not NR.finite(ageH) then ageH = NR.worldAge() end
    if ageH == nil then return end
    CRE.validate(player)
    local muscle, weight, profBoost = CRE.picks(player)
    local body = NR.server.metabolism.newBody(player, muscle, weight, ageH, profBoost)
    body.levelDue = true                                -- kept when the write raises
    record.body = body
    NR.call(obj(player, "getNutrition"), "setWeight", body.lm + body.lx + body.fm)
    NR.server.strength.writeLevel(player, body)
    body.levelDue = true                                -- the first minute re-pins the fraction (Plan 13 Task 10c)
    local native = Perks ~= nil and num(player, "getPerkLevel", nil, Perks.Strength) or nil
    if native ~= nil then NR.server.strength.remap(player, native) end  -- a strip's setPerkLevelDebug swaps no band
    NR.server.weight.writeTraits(player, body)
    CRE.stats.created = CRE.stats.created + 1
    NR.log.say(2, "creation: " .. tostring(username) .. " muscle=" .. tostring(muscle) .. " weight=" .. tostring(weight)
        .. " prof=" .. tostring(profBoost))
end

-- CRE.onNewGame(username, player, record): the P.onNewGame hook. One pcall; a failure is counted, kept and logged,
-- and first sight then builds the body from the traits held (NR_Server_Metabolism.ensureBody).
function CRE.onNewGame(username, player, record)
    if record == nil or not NR.isServer() then return end
    local ok, err = pcall(create, username, player, record)
    if not ok then
        CRE.stats.failures = CRE.stats.failures + 1
        CRE.lastError = err
        NR.log.say(2, "creation: " .. tostring(username) .. " failed: " .. tostring(err))
    end
end

-- Wiring: the P.onNewGame hook, once, on the server only, at OnServerStarted (NR_Server_Players loads after this file).
if Events ~= nil and Events.OnServerStarted ~= nil then
    Events.OnServerStarted.Add(function()
        if not NR.isServer() then return end
        if CRE.wired then return end
        CRE.wired = true
        local P = NR.server.players
        if P ~= nil and P.onNewGame ~= nil then P.onNewGame[#P.onNewGame + 1] = CRE.onNewGame end
    end)
end
