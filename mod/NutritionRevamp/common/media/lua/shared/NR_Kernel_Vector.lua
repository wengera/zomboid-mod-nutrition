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

-- The fallback inference (Plan 6 ruling 13): a food with no table entry and no declared vector takes
-- the four macros as read off the item and every other key as the template's per-kcal density times
-- the item's calories. templates is NR.data.infer (NR_Data_Infer.lua, generated: per FoodType the
-- median of key / calories over the item pass's own mapped food records, `_default` over all of them;
-- a judgement, not a measurement); the FoodType's entry, else `_default`; a nil foodType takes
-- `_default`. Calories <= 0, no templates or no `_default` -> the four macros only (the rest 0). A
-- missing macro reads 0. Returns a fresh vector. KEYS opens with the four MACROS (the order the
-- vector test pins), so the density loop starts after them; `#` on this file's own tables is a Lua
-- length.
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

-- The trimmed text of s (leading and trailing whitespace dropped).
function K.vector.trim(s)
    return string.match(s, "^%s*(.-)%s*$")
end

-- The declared-nutrients contract (Plan 6 ruling 14): a food-content mod writes NR_Nutrients =
-- key:value;key:value in its item script, in the units contract (NR.data.UNITS, per item); the loader
-- does not know the key, so it lands as a string in the item's default modData (#0212, #1281). Parses
-- that string: each `;`-separated pair is key:value, whitespace around either ignored, an empty pair
-- (a trailing `;`) skipped. A key in KEYS takes its value (a later duplicate wins); a key outside KEYS
-- is skipped and named in the returned `unknown` list. A pair without a `:`, an empty key, or a value
-- that is not a finite number >= 0 makes the WHOLE string malformed: nil and a reason string. A string
-- with no pair at all is malformed too. Returns vec, unknown: the four macros as the string gives
-- them, else 0 (the caller fills them from the item, whose script block owns them).
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
            if value == nil or value ~= value or value < 0 or value == math.huge then
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

-- A finite number: a number, not NaN (the one value unequal to itself) and not an infinity.
function K.vector.finite(x)
    return type(x) == "number" and x == x and x ~= math.huge and x ~= -math.huge
end

-- One food type through the source chain declared -> table -> inferred -> missing (Plan 6 rulings 13-14), shared
-- by the intake (NR_Server_Intake.lua, IN.chainOne) and the food tooltip (Plan 7 ruling 8), so the band shows what
-- the eat would land. declared is the item's NR_Nutrients default-modData string or nil; macros the item's own
-- { calories, carbs, lipids, proteins } or nil; foodType its FoodType or nil; data is NR.data's shape:
-- { nutrients = { get = fn(fullType) -> seed or nil }, infer = templates } (either part, or data, may be nil).
-- Returns vec, source, note: source is "declared", "table", "inferred" or "missing" (vec nil); note is the declared
-- string's unknown-key list, or its malformed reason (a string) when the chain fell through it, else nil. A declared
-- vector's four macros are the item's own (the script block owns them; a nil macros reads 0). The table's seed is
-- returned as the lookup gives it. Inference needs templates and finite calories above 0.
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
    if data.infer ~= nil and macros ~= nil and K.vector.finite(macros.calories) and macros.calories > 0 then
        return K.vector.infer(macros, foodType, data.infer), "inferred", note
    end
    return nil, "missing", note
end
