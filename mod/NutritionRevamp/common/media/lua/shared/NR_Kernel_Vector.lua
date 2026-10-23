-- NR_Kernel_Vector.lua -- the nutrient vector, one flat table of named scalars. The kernel hard-codes only the four
-- macros, so a nutrient is added by adding a key here, never a code path. `#` on this file's own tables is a Lua
-- length, never a Java list (#0940).
local K = NutritionRevamp.kernel
K.vector = {}

-- In the engine's order.
K.vector.MACROS = {"calories", "carbs", "lipids", "proteins"}

-- The unit of each is NR.data.UNITS.
K.vector.KEYS = {"calories", "carbs", "lipids", "proteins", "fibre", "water", "vitC", "iron", "phytate",
                 "retinol", "carotene", "vitD", "vitE", "vitK", "thiamine", "riboflavin", "niacin", "vitB6",
                 "folate", "vitB12", "choline", "sodium", "potassium", "calcium", "magnesium", "zinc",
                 "iodine", "selenium", "efa", "caffeine", "ethanol"}

function K.vector.keys()
    return K.vector.KEYS
end

-- Slow-clock capture-path code, so the `for` over this file's own KEYS is allowed.
function K.vector.new()
    local v = {}
    for i = 1, #K.vector.KEYS do
        v[K.vector.KEYS[i]] = 0
    end
    return v
end

-- Read only; never written.
K.vector.EMPTY = K.vector.new()

-- No allocation: dst is returned. A missing src key counts as 0.
function K.vector.add(dst, src, scale)
    for i = 1, #K.vector.KEYS do
        local k = K.vector.KEYS[i]
        dst[k] = dst[k] + (src[k] or 0) * scale
    end
    return dst
end

-- Vector assembly: an injected lookup in, a fresh vector out, no NR.data reference, so the kernel is testable with no
-- data file. The aggregating functions list the types they could not resolve in `missing`.

-- A nil lookup leaves the vector all-zero and names the type in `missing`.
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

-- The sum is scaled so its macro total matches the dish's own, recovering the cooking share the ingredient list does
-- not keep (#2650). A zero scratch total or a non-positive dishMacroTotal leaves it unscaled (scaled=false).
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

-- The instance scale (#3326): b.cal x frac over the vector's own calories, right for a plain, partial, caught, split or
-- replaced item alike; with no calories on either side the hunger ratio, and 1 when the script hunger is 0.
function K.vector.instanceScale(vecKcal, cal, frac, instBase, scriptHunger, share)
    if vecKcal ~= nil and vecKcal > 0 and cal ~= nil and cal > 0 then
        return cal * frac / vecKcal, 1
    end
    local scale = 1
    if scriptHunger ~= nil and scriptHunger ~= 0 and instBase ~= nil then
        scale = instBase / scriptHunger
    end
    return scale, share
end

function K.vector.scaled(vec, scale)
    local out = K.vector.new()
    K.vector.add(out, vec, scale)
    return out
end

-- The count is consumed INSTANCES, not uses (#2667): MakeMeatPatty spends 40 uses of ONE MincedMeat tub, so its map is
-- { Base.MincedMeat = 1 }. A partly-used input lands its whole seed (a known limitation).
function K.vector.craft(lookup, consumedCounts, share)
    local vec = K.vector.new()
    local missing = {}
    for fullType, count in pairs(consumedCounts) do
        local seed = lookup(fullType)
        if seed == nil then
            missing[#missing + 1] = fullType
        end
        local src = seed or K.vector.EMPTY
        K.vector.add(vec, src, count * share)
    end
    return vec, missing
end

-- fluidVector is per litre (#0634).
function K.vector.fluid(fluidVector, litres)
    local vec = K.vector.new()
    K.vector.add(vec, fluidVector, litres)
    return vec
end

-- The fallback inference: the item's own macros, and every other key at the FoodType template's per-kcal density (the
-- generated NR_Data_Infer.lua, a judgement, not a measurement). Calories <= 0 or no templates: the macros only.
function K.vector.infer(macros, foodType, templates)
    local vec = K.vector.new()
    for i = 1, #K.vector.MACROS do
        local m = K.vector.MACROS[i]
        vec[m] = macros[m] or 0
    end
    local calories = vec.calories
    if calories <= 0 then
        return vec
    end
    if templates == nil then
        return vec
    end
    local template = nil
    if foodType ~= nil then
        template = templates[foodType]
    end
    if template == nil then
        template = templates["_default"]
    end
    if template == nil then
        return vec
    end
    local density = template.density
    for i = #K.vector.MACROS + 1, #K.vector.KEYS do
        local k = K.vector.KEYS[i]
        local d = density[k]
        if d ~= nil then
            vec[k] = d * calories
        end
    end
    return vec
end

function K.vector.trim(s)
    return string.match(s, "^%s*(.-)%s*$")
end

-- The declared-nutrients contract: a mod writes NR_Nutrients = key:value;... in its item script, which lands as a
-- string in default modData (#0212). A key outside KEYS is skipped and named in `unknown`; a bad pair, an empty key or
-- a value not a finite number >= 0 makes the WHOLE string malformed (nil and a reason). Macros absent read 0.
function K.vector.declared(str)
    if type(str) ~= "string" then
        return nil, "not a string"
    end
    local known = {}
    for i = 1, #K.vector.KEYS do
        known[K.vector.KEYS[i]] = true
    end
    local vec = K.vector.new()
    local unknown = {}
    local knownRead = 0
    local pairsRead = 0
    local pos = 1
    local len = string.len(str)
    while pos <= len do
        local stop = string.find(str, ";", pos, true)
        if stop == nil then
            stop = len + 1
        end
        local pair = K.vector.trim(string.sub(str, pos, stop - 1))
        pos = stop + 1
        if pair ~= "" then
            local colon = string.find(pair, ":", 1, true)
            if colon == nil then
                return nil, "a pair without a colon: " .. pair
            end
            local key = K.vector.trim(string.sub(pair, 1, colon - 1))
            local value = tonumber(K.vector.trim(string.sub(pair, colon + 1)))
            if key == "" then
                return nil, "a pair without a key: " .. pair
            end
            if not K.finite(value) or value < 0 then
                return nil, "not a finite number >= 0: " .. pair
            end
            pairsRead = pairsRead + 1
            if known[key] then
                vec[key] = value
                knownRead = knownRead + 1
            else
                unknown[#unknown + 1] = key
            end
        end
    end
    if pairsRead == 0 then
        return nil, "no key:value pair"
    end
    if knownRead == 0 then
        return nil, "no known key (the declaration falls through to the table)"
    end
    return vec, unknown
end

-- Shared by the intake (IN.chainOne) and the food tooltip, so the tooltip shows what the eat would land. Returns vec,
-- source ("declared", "table", "inferred" or "missing") and note. A declared vector's macros are the item's own.
function K.vector.resolve(declared, macros, foodType, fullType, data)
    local note = nil
    if declared ~= nil then
        local vec, extra = K.vector.declared(declared)
        note = extra
        if vec ~= nil then
            local m = macros
            if m == nil then
                m = {}
            end
            vec.calories = m.calories or 0
            vec.carbs = m.carbs or 0
            vec.lipids = m.lipids or 0
            vec.proteins = m.proteins or 0
            return vec, "declared", note
        end
    end
    if data == nil then
        return nil, "missing", note
    end
    local seed = nil
    if data.nutrients ~= nil then
        seed = data.nutrients.get(fullType)
    end
    if seed ~= nil then
        return seed, "table", note
    end
    if data.infer ~= nil and macros ~= nil and K.finite(macros.calories) and macros.calories > 0 then
        return K.vector.infer(macros, foodType, data.infer), "inferred", note
    end
    return nil, "missing", note
end
