-- NR_Kernel_Vector.lua -- the nutrient vector: one flat table of named scalars, the four vanilla
-- macros plus the mod-nutrient keys (spec § 4.2, § 4.4). The kernel iterates the vector's own key
-- list and hard-codes only the four macros, so a nutrient is added by adding a key here, never a
-- code path. Pure: tables in, tables out, no Java. KEYS is a Lua table this file built, so `#` on it
-- is a Lua length, never a Java list (#0940).
local K = NutritionRevamp.kernel
K.vector = {}

-- The four vanilla macros, in the engine's order. The only nutrient names the kernel hard-codes.
K.vector.MACROS = {"calories", "carbs", "lipids", "proteins"}

-- The declared key list: the macros, the Plan 2 seed set, then the twenty-two kinetics keys Plan 4 adds
-- (the fat-soluble vitamins, the B vitamins and choline, the minerals and electrolytes, the essential
-- fats, caffeine and ethanol); the unit of each is NR.data.UNITS.
K.vector.KEYS = {"calories", "carbs", "lipids", "proteins", "fibre", "water", "vitC", "iron", "phytate",
                 "retinol", "carotene", "vitD", "vitE", "vitK", "thiamine", "riboflavin", "niacin", "vitB6",
                 "folate", "vitB12", "choline", "sodium", "potassium", "calcium", "magnesium", "zinc",
                 "iodine", "selenium", "efa", "caffeine", "ethanol"}

-- The declared key list a reader iterates.
function K.vector.keys()
    return K.vector.KEYS
end

-- A fresh vector with every declared key set to 0. Slow-clock capture-path code (not a per-tick
-- fast region), so the `for` over this file's own KEYS table is allowed.
function K.vector.new()
    local v = {}
    for i = 1, #K.vector.KEYS do
        v[K.vector.KEYS[i]] = 0
    end
    return v
end

-- Accumulate src into dst over every declared key, scaled, and return dst (the same object, no
-- allocation): dst[k] = dst[k] + (src[k] or 0) * scale. A missing src key counts as 0.
function K.vector.add(dst, src, scale)
    for i = 1, #K.vector.KEYS do
        local k = K.vector.KEYS[i]
        dst[k] = dst[k] + (src[k] or 0) * scale
    end
    return dst
end

-- Four-source nutrient-vector assembly (spec § 4.2). Each function is pure: an injected lookup or an
-- already-resolved vector in, a fresh vector out, no NR.data reference, so the kernel stays testable
-- with no data file. The aggregating functions (baseline, dish, craft) take lookup(fullType) ->
-- seed vector or nil, and track the types it could not resolve in a `missing` list; the server
-- wrapper passes NR.data.nutrients.get as the lookup, the test a stub. The vector, the scratch and
-- the missing list are Lua tables this file built, so `#` on them is a Lua length, never a Java list.

-- One type's seed times the share eaten: a fresh vector plus a `missing` list naming the type when
-- lookup returned nil (the vector is then all-zero).
function K.vector.baseline(lookup, fullType, share)
    local vec = K.vector.new()
    local missing = {}
    local seed = lookup(fullType)
    if seed == nil then
        missing[#missing + 1] = fullType
        return vec, missing
    end
    K.vector.add(vec, seed, share)
    return vec, missing
end

-- A dish: sum each ingredient type (one entry per appearance in extraTypes) into a scratch vector,
-- then scale every key so the summed macro total matches the dish's own macro total -- recovering the
-- cooking share the ingredient list does not keep (jar read § A, #2650/#2651; the Salad 25.0 kcal at
-- Cooking 0, #0301). Returns the vector and a note {missing=<list>, scaled=<bool>}; a zero scratch
-- macro total or a non-positive dishMacroTotal leaves the sum unscaled with scaled=false.
function K.vector.dish(lookup, extraTypes, dishMacroTotal)
    local scratch = K.vector.new()
    local missing = {}
    for i = 1, #extraTypes do
        local fullType = extraTypes[i]
        local seed = lookup(fullType)
        if seed == nil then
            missing[#missing + 1] = fullType
        else
            K.vector.add(scratch, seed, 1)
        end
    end
    local scratchMacroTotal = 0
    for i = 1, #K.vector.MACROS do
        scratchMacroTotal = scratchMacroTotal + scratch[K.vector.MACROS[i]]
    end
    local note = {}
    note.missing = missing
    if scratchMacroTotal > 0 and dishMacroTotal > 0 then
        local scale = dishMacroTotal / scratchMacroTotal
        for i = 1, #K.vector.KEYS do
            local k = K.vector.KEYS[i]
            scratch[k] = scratch[k] * scale
        end
        note.scaled = true
        return scratch, note
    end
    note.scaled = false
    return scratch, note
end

-- Animal meat: the type baseline scaled by raw hunger over base hunger (the butcher factor, accepting
-- the per-field noise of about +/-11 %, jar read § D #2669-#2672); a baseHunger of 0 falls back to
-- scale 1. typeBaseline is an already-resolved vector.
function K.vector.meat(typeBaseline, rawHunger, baseHunger)
    local scale = 1
    if baseHunger ~= 0 then
        scale = rawHunger / baseHunger
    end
    local vec = K.vector.new()
    K.vector.add(vec, typeBaseline, scale)
    return vec
end

-- A crafted output: sum each consumed type's seed times its count times the share, over the
-- consumed-type-to-count map the hand-craft action writes (#2667). The count is consumed item
-- INSTANCES, not uses: the map is +1 per entry of getAllConsumedItems, one entry per consumed
-- InventoryItem (jar 42.20.4, CraftRecipeData.getAllConsumedItems @range L2220-L2235 into
-- CacheData.addAppliedItem @range L1825-L1828). MakeMeatPatty spends 40 USES of ONE MincedMeat tub
-- (#0745), so its map is { Base.MincedMeat = 1 }: the whole-tub seed once. A partly-used input lands
-- its whole seed (an Intake limitation; Plan 6's use fraction). Returns the vector and a `missing` list.
function K.vector.craft(lookup, consumedCounts, share)
    local vec = K.vector.new()
    local missing = {}
    local empty = K.vector.new()
    for fullType, count in pairs(consumedCounts) do
        local seed = lookup(fullType)
        if seed == nil then
            missing[#missing + 1] = fullType
        end
        local src = seed or empty
        K.vector.add(vec, src, count * share)
    end
    return vec, missing
end

-- A drink: the per-litre fluid vector times the litres drunk (Cola per-litre 400 x 0.3 = the per-can
-- figure, #0634). fluidVector is an already-resolved per-litre vector.
function K.vector.fluid(fluidVector, litres)
    local vec = K.vector.new()
    K.vector.add(vec, fluidVector, litres)
    return vec
end
