-- NR_Data_Nutrients.lua -- not a kernel file: the seed per-type nutrient table and its loader (spec § 4.2, § 4.6; Plan 6 regenerates it at full coverage).
-- The seed covers only the foods and fluids this plan's live sessions eat and drink. The macros are
-- verbatim from data/food-items.json (42.20.4, jar b0bbce05d5); the mod nutrients (fibre, water,
-- vitC, iron, phytate) are per-item (per-litre for a fluid) and are either resolved from the
-- data-pipeline report's SR Legacy mapping or a clearly labelled judgement -- precision is Plan 6's
-- deliverable, coverage of the session foods is this task's. phytate is 0 on non-grain/legume foods.
-- A reader goes through the loaders, never the tables, so Plan 6 can swap the provenance untouched.
-- Units: calories kcal; carbs/lipids/proteins/fibre/water/phytate g; vitC/iron mg.
local NR = NutritionRevamp
local K = NR.kernel
NR.data = NR.data or {}
NR.data.nutrients = {}
NR.data.fluids = {}

-- Per-item vectors (macros exact from food-items.json; mod nutrients per the report's mapping or a
-- judgement). Every entry: -- SEED <pz_id> <sr-legacy-id or "judgement">.
local NUTRIENTS = {
    ["Base.Apple"] = { calories = 95.0, carbs = 25.13, lipids = 0.31, proteins = 0.47, fibre = 4.4, water = 155.8, vitC = 8.4, iron = 0.22, phytate = 0.0 },       -- SEED Base.Apple 171688 (Apples raw w/skin, 182 g)
    ["Base.Steak"] = { calories = 220.0, carbs = 0.0, lipids = 9.35, proteins = 31.62, fibre = 0.0, water = 74.0, vitC = 0.0, iron = 2.4, phytate = 0.0 },         -- SEED Base.Steak judgement (beef cut ~120 g; vitC 0, phytate 0 on meat)
    ["Base.Bread"] = { calories = 532.0, carbs = 99.0, lipids = 6.66, proteins = 17.7, fibre = 4.4, water = 65.0, vitC = 0.0, iron = 6.5, phytate = 0.4 },         -- SEED Base.Bread judgement (172675 french bread ~190 g; grain -> small phytate)
    ["Base.Carrots"] = { calories = 25.0, carbs = 6.0, lipids = 0.15, proteins = 0.6, fibre = 1.7, water = 54.6, vitC = 3.7, iron = 0.19, phytate = 0.0 },         -- SEED Base.Carrots judgement (carrot ~62 g)
    ["Base.Lettuce"] = { calories = 54.0, carbs = 10.33, lipids = 0.54, proteins = 4.9, fibre = 6.3, water = 285.0, vitC = 12.0, iron = 3.0, phytate = 0.0 },      -- SEED Base.Lettuce judgement (romaine head ~300 g; water high on produce)
    ["Base.Tomato"] = { calories = 14.0, carbs = 3.5, lipids = 0.2, proteins = 1.3, fibre = 0.94, water = 73.7, vitC = 10.7, iron = 0.21, phytate = 0.0 },         -- SEED Base.Tomato judgement (tomato ~78 g)
    ["Base.MincedMeat"] = { calories = 300.0, carbs = 0.0, lipids = 30.0, proteins = 46.0, fibre = 0.0, water = 160.0, vitC = 0.0, iron = 4.0, phytate = 0.0 },    -- SEED Base.MincedMeat judgement (ground beef; the craft input)
    ["Base.MeatPatty"] = { calories = 612.0, carbs = 0.0, lipids = 30.0, proteins = 46.0, fibre = 0.0, water = 140.0, vitC = 0.0, iron = 4.0, phytate = 0.0 },     -- SEED Base.MeatPatty judgement (cooked patty; the craft output)
}

-- Per-litre fluid vectors (macros per litre from the fluid blocks; mod nutrients per litre).
local FLUIDS = {
    ["Cola"] = { calories = 400.0, carbs = 104.0, lipids = 0.0, proteins = 0.0, fibre = 0.0, water = 890.0, vitC = 0.0, iron = 0.0, phytate = 0.0 },               -- SEED Cola judgement (per litre; water-rest of a sugar solution)
    ["JuiceGrape"] = { calories = 400.0, carbs = 120.0, lipids = 0.0, proteins = 0.0, fibre = 0.5, water = 840.0, vitC = 1.0, iron = 2.4, phytate = 0.0 },         -- SEED JuiceGrape judgement (per litre; grape juice)
    ["Water"] = { calories = 0.0, carbs = 0.0, lipids = 0.0, proteins = 0.0, fibre = 0.0, water = 1000.0, vitC = 0.0, iron = 0.0, phytate = 0.0 },                 -- SEED Water judgement (per litre; hydration only)
}

-- A fresh zeroed vector of the declared keys filled from the seed entry, so a reader cannot mutate
-- the seed; nil if the entry is absent.
local function copyOf(seed)
    if seed == nil then
        return nil
    end
    local v = K.vector.new()
    for key, value in pairs(seed) do
        v[key] = value
    end
    return v
end

-- The per-item loader every reader goes through.
function NR.data.nutrients.get(fullType)
    return copyOf(NUTRIENTS[fullType])
end

-- The per-litre fluid loader every reader goes through.
function NR.data.fluids.get(fluidTypeString)
    return copyOf(FLUIDS[fluidTypeString])
end
