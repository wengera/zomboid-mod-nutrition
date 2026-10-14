-- TKX_TraitLevers shared side (Plan 13 Task 0, checks 1-3): the Lua list edits of two vanilla trait definitions,
-- made at shared file scope on both sides. Scripts load before any Lua on both sides (trait-levers.md section 2.2),
-- so the definitions exist here, and vanilla's own OnGameBoot DoTraits runs after every file has loaded.
--   1. Underweight: getXpBoosts():remove(Perks.Fitness)                    (the live HashMap<Perk,Integer>)
--   2. Overweight:  getMutuallyExclusiveTraits():remove(CharacterTrait.ATHLETIC)   (the live ArrayList)
--   3. Overweight:  getMutuallyExclusiveTraits():add(CharacterTrait.OBESE)
-- Each edit's pcall result lands in TKX_TraitLevers.edits.<key> = {ok, ret [, err]}; edits.errors counts the
-- failed ones. TKX_TraitLevers is a GLOBAL on purpose: the harness lua.read reads it on each side. The server file
-- adds the OnNewGame writer and the AddXP recorder to the same table.
TKX_TraitLevers = TKX_TraitLevers or {}
TKX_TraitLevers.version = 1
TKX_TraitLevers.edits = { errors = 0 }

local function definition(enum)
    if enum == nil then error("no CharacterTrait enum") end
    if CharacterTraitDefinition == nil or CharacterTraitDefinition.getCharacterTraitDefinition == nil then
        error("no CharacterTraitDefinition.getCharacterTraitDefinition")
    end
    local def = CharacterTraitDefinition.getCharacterTraitDefinition(enum)
    if def == nil then error("no definition") end
    return def
end

local function edit(key, fn)
    local ok, ret = pcall(fn)
    local row = { ok = ok, ret = tostring(ret) }
    if not ok then
        row.err = tostring(ret)
        TKX_TraitLevers.edits.errors = TKX_TraitLevers.edits.errors + 1
    end
    TKX_TraitLevers.edits[key] = row
end

edit("underweightFitness", function()
    local def = definition(CharacterTrait.UNDERWEIGHT)
    return def:getXpBoosts():remove(Perks.Fitness)
end)

edit("overweightAthletic", function()
    local def = definition(CharacterTrait.OVERWEIGHT)
    return def:getMutuallyExclusiveTraits():remove(CharacterTrait.ATHLETIC)
end)

edit("overweightObese", function()
    local def = definition(CharacterTrait.OVERWEIGHT)
    return def:getMutuallyExclusiveTraits():add(CharacterTrait.OBESE)
end)
