-- NR_Server_Creation.lua: the creation handler. When the server's OnNewGame resets a record, the character's picks are
-- validated and the starting body is built from what survives. OnNewGame fires after IsoPlayer.applyTraits has set
-- every trait the client sent (CreatePlayerPacket.processServer L291); the server enforces neither the point total
-- nor an exclusion.
-- 1. Validation, on the server's own definitions. The strip order never reads the list's order: getKnownTraits() is
--    not the client's order, and vanilla's band listener rewrites the muscle and Fitness traits during applyTraits. A
--    free trait is never stripped; of two exclusive non-free picks the higher absolute cost goes (a tie by name); then,
--    while the screen's PointToSpend (CharacterCreationProfession.lua:860-867) reads below 0, the costliest kept pick
--    goes. An unreadable profession skips the point check (nothing is stripped on a guess). A strip reverts the
--    trait's XP boosts.
--    The muscle pick is inferred first (CRE.inferMuscle): applyTraits climbs Strength with LevelPerk and vanilla's
--    listener swaps the band at every step, so the held trait is the native level's band, not the pick.
-- 2. The body: K.body.create over the inferred muscle pick and the held weight band under the profession's Strength
--    boost, through CRE.newBody, which first sight shares, so the two build one way.
-- 3. The writes, in order: the weight; the Strength level (STR.writeLevel), then the band re-asserted (STR.remap: a
--    strip's setPerkLevelDebug swaps no band); then the weight-band traits, last, so they are final. body.levelDue
--    stays true, so the first server minute re-pins the XP fraction OnNewGame's write loses.
-- Java statics are called with a dot under pcall, as vanilla calls them. Event-driven, once per new character (Rule 6).
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
        "an exclusion chain from a modified client (A excludes B, B excludes C) strips the costlier pick of each pair, A and B, where stripping B alone would make the list legal",
    },
}
local CRE = NR.server.creation

local num, obj, flag = NR.num, NR.obj, NR.flag

-- The perk level a revert is clamped to.
CRE.LEVEL_MAX = 10

-- nil when the class or member is absent or raises.
local function static(cls, name, ...)
    if cls == nil then return nil end
    local f = cls[name]
    if f == nil then return nil end
    local ok, v = pcall(f, ...)
    if ok then return v end
    return nil
end

function CRE.traitDef(t)
    if CharacterTraitDefinition == nil then return nil end
    return static(CharacterTraitDefinition, "getCharacterTraitDefinition", t)
end

-- Walked with size()/get(i) (#0940); an unreadable list reads empty.
function CRE.walk(list)
    local out = {}
    local n = num(list, "size", 0)
    for i = 0, n - 1 do
        local ok, v = NR.try(list, "get", i)
        if ok and v ~= nil then out[#out + 1] = v end
    end
    return out
end

-- Vanilla never lets a character hold two weight-band (or muscle-band) traits, so the list order is moot.
function CRE.heldTrait(traits, names)
    if CharacterTrait == nil or traits == nil then return nil end
    for i = 1, #names do
        local t = CharacterTrait[names[i]]
        if t ~= nil and flag(traits, "get", t) then return names[i] end
    end
    return nil
end

-- A Lua number, or a java Integer read with intValue; nil when neither.
function CRE.boostOf(v)
    if type(v) == "number" then return v end
    return num(v, "intValue", nil)
end

-- 0 when it has none or the map is unreadable.
function CRE.strengthBoost(def)
    local map = obj(def, "getXpBoosts")
    if map == nil or transformIntoKahluaTable == nil or Perks == nil then return 0 end
    local okT, tbl = pcall(transformIntoKahluaTable, map)
    if not okT or type(tbl) ~= "table" then return 0 end
    for perk, v in pairs(tbl) do
        if perk == Perks.Strength then return CRE.boostOf(v) or 0 end
    end
    return 0
end

-- nil when unreadable.
function CRE.professionDef(player)
    local prof = obj(obj(player, "getDescriptor"), "getCharacterProfession")
    if prof == nil or CharacterProfessionDefinition == nil then return nil end
    return static(CharacterProfessionDefinition, "getCharacterProfessionDefinition", prof)
end

-- The restated blocks keep vanilla's XPBoosts; false is no pick.
CRE.MUSCLE_BY_BOOST = { [-5] = "WEAK", [-2] = "FEEBLE", [0] = false, [2] = "STOUT", [4] = "STRONG" }

local function muscleName(t)
    if CharacterTrait == nil then return nil end
    local names = K.strength.MUSCLE_TRAITS
    for i = 1, #names do
        if CharacterTrait[names[i]] == t then return names[i] end
    end
    return nil
end

-- native - 5 - the profession's boost - every held non-band trait's boost, mapped by CRE.MUSCLE_BY_BOOST; nil when the
-- level cannot tell (unreadable, clamped at 0 or 10, no profession, an unmapped offset).
function CRE.inferMuscle(player, pdef, known)
    if Perks == nil or Perks.Strength == nil or CharacterTrait == nil or pdef == nil then return nil end
    local native = num(player, "getPerkLevel", nil, Perks.Strength)
    if native == nil or native <= 0 or native >= K.strength.L_MAX then return nil end
    local off = native - 5 - CRE.strengthBoost(pdef)
    for i = 1, #known do
        if muscleName(known[i]) == nil then off = off - CRE.strengthBoost(CRE.traitDef(known[i])) end
    end
    return CRE.MUSCLE_BY_BOOST[off]
end

function CRE.musclePick(player, traits, pdef)
    local muscle = CRE.inferMuscle(player, pdef, CRE.walk(obj(traits, "getKnownTraits")))
    if muscle == nil then return CRE.heldTrait(traits, K.strength.MUSCLE_TRAITS) end
    if muscle == false then return nil end
    return muscle
end

-- The one builder of first sight and the creation handler, so the two build one way.
function CRE.newBody(player, muscle, weight, ageH, profBoost)
    local sex = 1
    if flag(player, "isFemale") then sex = 2 end
    local spec = K.body.create(muscle, weight, NR.strengthP(), K.body.effSex(sex, NR.sexSpecific()), profBoost)
    return K.body.new(spec, sex, ageH)
end

local function nameOf(t)
    local ok, v = NR.try(t, "getName")
    if ok and type(v) == "string" then return v end
    return tostring(t)
end

local function lists(def, t)
    return flag(obj(def, "getMutuallyExclusiveTraits"), "contains", t)
end

-- In both directions: isMutuallyExclusive sits on one side only for some pairs (Weight Gain's).
function CRE.excludes(a, b)
    if a.def == nil or b.def == nil then return false end
    return lists(a.def, b.t) or lists(b.def, a.t)
        or flag(a.def, "isMutuallyExclusive", b.def) or flag(b.def, "isMutuallyExclusive", a.def)
end

-- Among the kept positive picks the first is also the costliest, so both strips read one order.
function CRE.before(a, b)
    local ca, cb = math.abs(a.cost), math.abs(b.cost)
    if ca ~= cb then return ca > cb end
    return a.name < b.name
end

-- CharacterCreationProfession.lua:918-936.
function CRE.offset(penalty, n)
    if n <= 0 then return 0 end
    if penalty == 2 then return math.floor(n / 3) end
    if penalty == 3 then return math.floor(n / 2) end
    if penalty == 4 then return n - 1 end
    return 0
end

-- 1 and 0 when unread.
local function sandboxPoints()
    local penalty = num(obj(NR.sandbox(), "getOptionByName", "NegativeTraitsPenalty"), "getValue", 1)
    local free = 0
    local sv = SandboxVars
    if type(sv) == "table" and NR.finite(sv.CharacterFreePoints) then free = sv.CharacterFreePoints end
    return penalty, free
end

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

local function addGrants(set, list)
    local ts = CRE.walk(list)
    for i = 1, #ts do set[ts[i]] = true end
end

-- setPerkLevelDebug fires no LevelPerk event (#2870), then setXPToLevel.
local function revertBoosts(player, def)
    local map = obj(def, "getXpBoosts")
    if map == nil or transformIntoKahluaTable == nil then return end
    local okT, tbl = pcall(transformIntoKahluaTable, map)
    if not okT or type(tbl) ~= "table" then return end
    local xp = obj(player, "getXp")
    for perk, v in pairs(tbl) do
        local boost = CRE.boostOf(v)
        local level = num(player, "getPerkLevel", nil, perk)
        if boost ~= nil and boost ~= 0 and level ~= nil then
            local to = K.clamp(level - boost, 0, CRE.LEVEL_MAX)
            NR.call(player, "setPerkLevelDebug", perk, to)
            NR.call(xp, "setXPToLevel", perk, to)
        end
    end
end

local function strip(player, coll, e, why, stripped)
    if e.held ~= nil then NR.call(coll, "remove", e.held) end
    if e.def ~= nil then revertBoosts(player, e.def) end
    stripped[#stripped + 1] = e.name
    CRE.stats.stripped = CRE.stats.stripped + 1
    NR.log.say(1, "creation: " .. tostring(NR.obj(player, "getUsername")) .. " loses " .. e.name .. " (" .. why .. ")")
end

-- Empty when nothing was illegal or unreadable. One trait push when anything was stripped.
function CRE.validate(player)
    local stripped = {}
    if CharacterTraitDefinition == nil then return stripped end
    local coll = obj(player, "getCharacterTraits")
    local known = CRE.walk(obj(coll, "getKnownTraits"))
    local pdef = CRE.professionDef(player)
    local grants = {}
    addGrants(grants, obj(pdef, "getGrantedTraits"))
    local muscle = CRE.inferMuscle(player, pdef, known)
    local entries = {}
    local placed = false
    local function enter(t, held)
        local def = CRE.traitDef(t)
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

-- Each nil for none; profBoost 0 when unreadable.
function CRE.picks(player)
    local traits = obj(player, "getCharacterTraits")
    local pdef = CRE.professionDef(player)
    local muscle = CRE.musclePick(player, traits, pdef)
    return muscle, CRE.heldTrait(traits, K.traits.WEIGHT_TRAITS), CRE.strengthBoost(pdef)
end

local function create(username, player, record)
    local ageH = record.firstSeen
    if not NR.finite(ageH) then ageH = NR.worldAge() end
    if ageH == nil then return end
    CRE.validate(player)
    local muscle, weight, profBoost = CRE.picks(player)
    local body = CRE.newBody(player, muscle, weight, ageH, profBoost)
    body.levelDue = true                                -- kept when the write raises
    record.body = body
    NR.call(obj(player, "getNutrition"), "setWeight", body.lm + body.lx + body.fm)
    NR.server.strength.writeLevel(player, body)
    body.levelDue = true                                -- the first minute re-pins the fraction
    local native = Perks ~= nil and num(player, "getPerkLevel", nil, Perks.Strength) or nil
    if native ~= nil then NR.server.strength.remap(player, native) end  -- a strip's setPerkLevelDebug swaps no band
    NR.server.weight.writeTraits(player, body)
    CRE.stats.created = CRE.stats.created + 1
    NR.log.say(2, "creation: " .. tostring(username) .. " muscle=" .. tostring(muscle) .. " weight=" .. tostring(weight)
        .. " prof=" .. tostring(profBoost))
end

-- One pcall; on a failure first sight builds the body from the traits held.
function CRE.onNewGame(username, player, record)
    if record == nil or not NR.isServer() then return end
    local ok, err = pcall(create, username, player, record)
    if not ok then
        CRE.stats.failures = CRE.stats.failures + 1
        CRE.lastError = err
        NR.log.say(2, "creation: " .. tostring(username) .. " failed: " .. tostring(err))
    end
end

-- Once, on the server only (NR_Server_Players loads after this file).
if Events ~= nil and Events.OnServerStarted ~= nil then
    Events.OnServerStarted.Add(function()
        if not NR.isServer() then return end
        if CRE.wired then return end
        CRE.wired = true
        local P = NR.server.players
        if P ~= nil and P.onNewGame ~= nil then P.onNewGame[#P.onNewGame + 1] = CRE.onNewGame end
    end)
end
