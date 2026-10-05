-- NR_Data_Nutrients.lua -- not a kernel file: the seed per-type nutrient table and its loader (spec § 4.2, § 4.6; Plan 6 regenerates it at full coverage).
-- The seed covers only the foods and fluids the live sessions eat and drink. The macros are
-- verbatim from data/food-items.json (42.20.4, jar b0bbce05d5) or, for a fluid, its fluid block; the
-- mod nutrients are per-item (per-litre for a fluid) and are either resolved from the data-pipeline
-- report's SR Legacy mapping or a clearly labelled judgement -- precision is Plan 6's deliverable,
-- coverage of the session foods is the seed's. phytate is 0 on non-grain/legume foods. Each entry
-- writes every key: the Plan 2 keys on its first line, the kinetics keys (USDA-shaped per-100 g
-- values scaled to the item, labelled judgements) on its second, each line with its own SEED label.
-- A reader goes through the loaders, never the tables, so Plan 6 can swap the provenance untouched.
-- Units: NR.data.UNITS below (ug = micrograms).
local NR = NutritionRevamp
local K = NR.kernel
NR.data = NR.data or {}
NR.data.nutrients = {}
NR.data.fluids = {}

-- The units contract: the unit of every vector key, per item (per litre for a fluid). Plan 6's
-- pipeline emits these units and the kernel's coefficients assume them -- K.stomach.ironFactor's
-- per-MILLIGRAM phytate and vitamin C slopes (the rows cited there) and K.stomach.BIOAVAIL per the
-- same key -- so a seed or generated value in any other unit misreads by the conversion factor
-- (phytate in grams read about 1000x too weak an inhibition). Every K.vector.KEYS key is listed, and
-- nothing else.
-- The Plan 4 keys: micrograms for retinol, carotene (beta-carotene), vitD, vitK, folate (DFE), vitB12,
-- iodine and selenium; grams for efa (linoleic plus alpha-linolenic acid) and ethanol; milligrams for
-- the rest. ASCII "ug" rather than the micro sign, so the string is one byte per character.
NR.data.UNITS = { calories = "kcal", carbs = "g", lipids = "g", proteins = "g", fibre = "g", water = "g",
                  vitC = "mg", iron = "mg", phytate = "mg",
                  retinol = "ug", carotene = "ug", vitD = "ug", vitE = "mg", vitK = "ug", thiamine = "mg",
                  riboflavin = "mg", niacin = "mg", vitB6 = "mg", folate = "ug", vitB12 = "ug", choline = "mg",
                  sodium = "mg", potassium = "mg", calcium = "mg", magnesium = "mg", zinc = "mg", iodine = "ug",
                  selenium = "ug", efa = "g", caffeine = "mg", ethanol = "g" }

-- Per-item vectors (macros exact from food-items.json; mod nutrients per the report's mapping or a
-- judgement). Every entry line: -- SEED <pz_id> <sr-legacy-id or "judgement">.
local NUTRIENTS = {
    ["Base.Apple"] = { calories = 95.0, carbs = 25.13, lipids = 0.31, proteins = 0.47, fibre = 4.4, water = 155.8, vitC = 8.4, iron = 0.22, phytate = 0.0,  -- SEED Base.Apple 171688 (Apples raw w/skin, 182 g)
        retinol = 0.0, carotene = 49.0, vitD = 0.0, vitE = 0.33, vitK = 4.0, thiamine = 0.031, riboflavin = 0.047, niacin = 0.17, vitB6 = 0.075, folate = 5.5, vitB12 = 0.0, choline = 6.2, sodium = 1.8, potassium = 195.0, calcium = 11.0, magnesium = 9.1, zinc = 0.07, iodine = 0.0, selenium = 0.0, efa = 0.09, caffeine = 0.0, ethanol = 0.0 },  -- SEED Base.Apple USDA-shaped judgement (per 182 g apple, SR 171688 per-100 g scaled)
    ["Base.Steak"] = { calories = 220.0, carbs = 0.0, lipids = 9.35, proteins = 31.62, fibre = 0.0, water = 74.0, vitC = 0.0, iron = 2.4, phytate = 0.0,  -- SEED Base.Steak judgement (beef cut ~120 g; vitC 0, phytate 0 on meat)
        retinol = 0.0, carotene = 0.0, vitD = 0.12, vitE = 0.48, vitK = 1.8, thiamine = 0.084, riboflavin = 0.2, niacin = 8.6, vitB6 = 0.72, folate = 9.6, vitB12 = 1.8, choline = 120.0, sodium = 72.0, potassium = 408.0, calcium = 24.0, magnesium = 30.0, zinc = 6.0, iodine = 2.4, selenium = 36.0, efa = 0.42, caffeine = 0.0, ethanol = 0.0 },  -- SEED Base.Steak USDA-shaped judgement (per ~120 g cooked lean beef)
    ["Base.Bread"] = { calories = 532.0, carbs = 99.0, lipids = 6.66, proteins = 17.7, fibre = 4.4, water = 65.0, vitC = 0.0, iron = 6.5, phytate = 400.0,  -- SEED Base.Bread judgement: ~400 mg phytic acid per ~190 g loaf-portion of wholemeal-ish bread (macros 172675 french bread)
        retinol = 0.0, carotene = 0.0, vitD = 0.0, vitE = 0.38, vitK = 0.76, thiamine = 0.99, riboflavin = 0.63, niacin = 9.1, vitB6 = 0.17, folate = 475.0, vitB12 = 0.0, choline = 28.5, sodium = 1140.0, potassium = 222.0, calcium = 95.0, magnesium = 51.0, zinc = 1.8, iodine = 19.0, selenium = 53.0, efa = 1.1, caffeine = 0.0, ethanol = 0.0 },  -- SEED Base.Bread USDA-shaped judgement (per ~190 g enriched french bread; folate as DFE)
    ["Base.Carrots"] = { calories = 25.0, carbs = 6.0, lipids = 0.15, proteins = 0.6, fibre = 1.7, water = 54.6, vitC = 3.7, iron = 0.19, phytate = 0.0,  -- SEED Base.Carrots judgement (carrot ~62 g)
        retinol = 0.0, carotene = 5140.0, vitD = 0.0, vitE = 0.41, vitK = 8.2, thiamine = 0.041, riboflavin = 0.036, niacin = 0.61, vitB6 = 0.086, folate = 11.8, vitB12 = 0.0, choline = 5.5, sodium = 43.0, potassium = 198.0, calcium = 20.5, magnesium = 7.4, zinc = 0.15, iodine = 1.0, selenium = 0.06, efa = 0.07, caffeine = 0.0, ethanol = 0.0 },  -- SEED Base.Carrots USDA-shaped judgement (per ~62 g raw carrot; carotene as beta-carotene)
    ["Base.Lettuce"] = { calories = 54.0, carbs = 10.33, lipids = 0.54, proteins = 4.9, fibre = 6.3, water = 285.0, vitC = 12.0, iron = 3.0, phytate = 0.0,  -- SEED Base.Lettuce judgement (romaine head ~300 g; water high on produce)
        retinol = 0.0, carotene = 15680.0, vitD = 0.0, vitE = 0.39, vitK = 308.0, thiamine = 0.22, riboflavin = 0.2, niacin = 0.94, vitB6 = 0.22, folate = 408.0, vitB12 = 0.0, choline = 30.0, sodium = 24.0, potassium = 741.0, calcium = 99.0, magnesium = 42.0, zinc = 0.69, iodine = 1.0, selenium = 1.2, efa = 0.35, caffeine = 0.0, ethanol = 0.0 },  -- SEED Base.Lettuce USDA-shaped judgement (per ~300 g romaine head)
    ["Base.Tomato"] = { calories = 14.0, carbs = 3.5, lipids = 0.2, proteins = 1.3, fibre = 0.94, water = 73.7, vitC = 10.7, iron = 0.21, phytate = 0.0,  -- SEED Base.Tomato judgement (tomato ~78 g)
        retinol = 0.0, carotene = 350.0, vitD = 0.0, vitE = 0.42, vitK = 6.2, thiamine = 0.029, riboflavin = 0.015, niacin = 0.46, vitB6 = 0.062, folate = 11.7, vitB12 = 0.0, choline = 5.2, sodium = 3.9, potassium = 185.0, calcium = 7.8, magnesium = 8.6, zinc = 0.13, iodine = 0.5, selenium = 0.0, efa = 0.06, caffeine = 0.0, ethanol = 0.0 },  -- SEED Base.Tomato USDA-shaped judgement (per ~78 g raw tomato)
    ["Base.MincedMeat"] = { calories = 300.0, carbs = 0.0, lipids = 30.0, proteins = 46.0, fibre = 0.0, water = 160.0, vitC = 0.0, iron = 4.0, phytate = 0.0,  -- SEED Base.MincedMeat judgement (ground beef; the craft input)
        retinol = 0.0, carotene = 0.0, vitD = 0.25, vitE = 1.05, vitK = 3.75, thiamine = 0.11, riboflavin = 0.4, niacin = 11.5, vitB6 = 0.83, folate = 17.5, vitB12 = 6.0, choline = 145.0, sodium = 165.0, potassium = 725.0, calcium = 37.5, magnesium = 45.0, zinc = 11.5, iodine = 5.0, selenium = 37.5, efa = 1.1, caffeine = 0.0, ethanol = 0.0 },  -- SEED Base.MincedMeat USDA-shaped judgement (per ~250 g raw ground beef)
    ["Base.MeatPatty"] = { calories = 612.0, carbs = 0.0, lipids = 30.0, proteins = 46.0, fibre = 0.0, water = 140.0, vitC = 0.0, iron = 4.0, phytate = 0.0,  -- SEED Base.MeatPatty judgement (cooked patty; the craft output)
        retinol = 0.0, carotene = 0.0, vitD = 0.25, vitE = 1.05, vitK = 3.75, thiamine = 0.11, riboflavin = 0.4, niacin = 11.5, vitB6 = 0.83, folate = 17.5, vitB12 = 6.0, choline = 145.0, sodium = 165.0, potassium = 725.0, calcium = 37.5, magnesium = 45.0, zinc = 11.5, iodine = 5.0, selenium = 37.5, efa = 1.1, caffeine = 0.0, ethanol = 0.0 },  -- SEED Base.MeatPatty USDA-shaped judgement (the MincedMeat tub it is made from; cooking losses ride the retention classes)
    ["Base.PillsVitamins"] = { calories = 0.0, carbs = 0.0, lipids = 0.0, proteins = 0.0, fibre = 0.0, water = 0.0, vitC = 0.0, iron = 0.0, phytate = 0.0,  -- SEED Base.PillsVitamins judgement (no macros, no Plan 2 nutrient)
        retinol = 0.0, carotene = 0.0, vitD = 0.0, vitE = 0.0, vitK = 0.0, thiamine = 0.0, riboflavin = 0.0, niacin = 0.0, vitB6 = 0.0, folate = 0.0, vitB12 = 0.0, choline = 0.0, sodium = 0.0, potassium = 0.0, calcium = 0.0, magnesium = 0.0, zinc = 0.0, iodine = 0.0, selenium = 0.0, efa = 0.0, caffeine = 50.0, ethanol = 0.0 },  -- SEED Base.PillsVitamins judgement (per USE of the 5-use drainable, UseDelta 0.2; the vanilla item lowers fatigue (fatigueChange -4) and wears the caffeine-pill icon and model; 50 mg caffeine a game choice; read only once the pill path is wired)
}

-- Per-litre fluid vectors (macros per litre from the fluid blocks; mod nutrients per litre).
local FLUIDS = {
    ["Cola"] = { calories = 400.0, carbs = 104.0, lipids = 0.0, proteins = 0.0, fibre = 0.0, water = 890.0, vitC = 0.0, iron = 0.0, phytate = 0.0,  -- SEED Cola judgement (per litre; water-rest of a sugar solution)
        retinol = 0.0, carotene = 0.0, vitD = 0.0, vitE = 0.0, vitK = 0.0, thiamine = 0.0, riboflavin = 0.0, niacin = 0.0, vitB6 = 0.0, folate = 0.0, vitB12 = 0.0, choline = 0.0, sodium = 40.0, potassium = 20.0, calcium = 20.0, magnesium = 0.0, zinc = 0.0, iodine = 0.0, selenium = 0.0, efa = 0.0, caffeine = 96.0, ethanol = 0.0 },  -- SEED Cola USDA-shaped judgement (per litre; sodium 40 mg/L and caffeine 96 mg/L)
    ["JuiceGrape"] = { calories = 400.0, carbs = 120.0, lipids = 0.0, proteins = 0.0, fibre = 0.5, water = 840.0, vitC = 1.0, iron = 2.4, phytate = 0.0,  -- SEED JuiceGrape judgement (per litre; grape juice)
        retinol = 0.0, carotene = 0.0, vitD = 0.0, vitE = 0.0, vitK = 0.0, thiamine = 0.17, riboflavin = 0.15, niacin = 1.3, vitB6 = 0.32, folate = 0.0, vitB12 = 0.0, choline = 0.0, sodium = 50.0, potassium = 1320.0, calcium = 110.0, magnesium = 100.0, zinc = 0.7, iodine = 0.0, selenium = 0.0, efa = 0.0, caffeine = 0.0, ethanol = 0.0 },  -- SEED JuiceGrape USDA-shaped judgement (per litre; potassium 1320 mg/L)
    ["Water"] = { calories = 0.0, carbs = 0.0, lipids = 0.0, proteins = 0.0, fibre = 0.0, water = 1000.0, vitC = 0.0, iron = 0.0, phytate = 0.0,  -- SEED Water judgement (per litre; hydration only)
        retinol = 0.0, carotene = 0.0, vitD = 0.0, vitE = 0.0, vitK = 0.0, thiamine = 0.0, riboflavin = 0.0, niacin = 0.0, vitB6 = 0.0, folate = 0.0, vitB12 = 0.0, choline = 0.0, sodium = 0.0, potassium = 0.0, calcium = 0.0, magnesium = 0.0, zinc = 0.0, iodine = 0.0, selenium = 0.0, efa = 0.0, caffeine = 0.0, ethanol = 0.0 },  -- SEED Water judgement (per litre; every kinetics key 0)
    ["Beer"] = { calories = 500.0, carbs = 36.0, lipids = 0.0, proteins = 4.0, fibre = 0.0, water = 920.0, vitC = 0.0, iron = 0.2, phytate = 0.0,  -- SEED Beer judgement (per litre; macros verbatim from the Beer fluid block, water the rest of a 5 % ABV beer)
        retinol = 0.0, carotene = 0.0, vitD = 0.0, vitE = 0.0, vitK = 0.0, thiamine = 0.05, riboflavin = 0.25, niacin = 5.1, vitB6 = 0.46, folate = 60.0, vitB12 = 0.2, choline = 100.0, sodium = 40.0, potassium = 270.0, calcium = 40.0, magnesium = 60.0, zinc = 0.1, iodine = 0.0, selenium = 6.0, efa = 0.0, caffeine = 0.0, ethanol = 39.5 },  -- SEED Beer USDA-shaped judgement (per litre; ethanol 39.5 g = 1000 mL x 0.05 ABV x 0.789 g/mL; potassium 270 mg/L)
    ["Coffee"] = { calories = 10.0, carbs = 0.0, lipids = 0.0, proteins = 1.0, fibre = 0.0, water = 990.0, vitC = 0.0, iron = 0.1, phytate = 0.0,  -- SEED Coffee judgement (per litre; macros verbatim from the Coffee fluid block, brewed coffee)
        retinol = 0.0, carotene = 0.0, vitD = 0.0, vitE = 0.0, vitK = 0.0, thiamine = 0.0, riboflavin = 0.8, niacin = 1.9, vitB6 = 0.0, folate = 0.0, vitB12 = 0.0, choline = 26.0, sodium = 20.0, potassium = 490.0, calcium = 20.0, magnesium = 30.0, zinc = 0.2, iodine = 0.0, selenium = 0.0, efa = 0.0, caffeine = 428.0, ethanol = 0.0 },  -- SEED Coffee S0797 (caffeine 428 mg/L = 107 mg per 250 mL); the rest USDA-shaped judgement (per litre brewed)
    ["Whiskey"] = { calories = 2500.0, carbs = 0.0, lipids = 0.0, proteins = 0.0, fibre = 0.0, water = 634.0, vitC = 0.0, iron = 0.0, phytate = 0.0,  -- SEED Whiskey judgement (per litre; macros verbatim from the Whiskey fluid block; water the rest of a 40 % ABV spirit)
        retinol = 0.0, carotene = 0.0, vitD = 0.0, vitE = 0.0, vitK = 0.0, thiamine = 0.0, riboflavin = 0.0, niacin = 0.0, vitB6 = 0.0, folate = 0.0, vitB12 = 0.0, choline = 0.0, sodium = 0.0, potassium = 0.0, calcium = 0.0, magnesium = 0.0, zinc = 0.0, iodine = 0.0, selenium = 0.0, efa = 0.0, caffeine = 0.0, ethanol = 315.6 },  -- SEED Whiskey judgement (per litre; ethanol 315.6 g = 1000 mL x 0.40 ABV x 0.789 g/mL)
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
