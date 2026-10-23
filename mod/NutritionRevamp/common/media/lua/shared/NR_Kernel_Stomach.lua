-- NR_Kernel_Stomach.lua: the stomach's two lanes and absorption into the pool. A food lands in the solid buffer with its
-- water (ingest); a drink's water lands in the liquid lane, its other keys in the buffer (ingestLiquid). The solid lane
-- empties energy zero-order, never faster than water; the liquid lane first-order, slowed only by drink-borne energy.
-- The absorption factors read the meal in the stomach before the minute's emptying (K.stomach.context, #2981), not the
-- share emptied. Caffeine and ethanol never enter the buffer (the intake diverts them to the acute gut lane).
-- Pure, no Java; slow-clock code with no @fastpath region. Sorts before NR_Kernel_Vector.lua, so every K.vector and
-- K.retention reference resolves at call time, never at load.
local K = NutritionRevamp.kernel
K.stomach = {}

-- water and fibre pass through as intake; phytate is a context, never pooled. A macro, caffeine and ethanol are
-- unlisted and pass at 1.0. The fat-soluble keys take the fat factor in absorb on top of this entry.
K.stomach.BIOAVAIL = {}
K.stomach.BIOAVAIL.water = K.dials.get("stomach.BIOAVAIL.water")
K.stomach.BIOAVAIL.fibre = K.dials.get("stomach.BIOAVAIL.fibre")
K.stomach.BIOAVAIL.vitC = K.dials.get("stomach.BIOAVAIL.vitC")
K.stomach.BIOAVAIL.iron = K.dials.get("stomach.BIOAVAIL.iron")
K.stomach.BIOAVAIL.phytate = 0.0 -- no row needed: absorb zeroes phytate itself (an anti-nutrient context, never pooled); the entry keeps every non-macro key listed
K.stomach.BIOAVAIL.retinol = K.dials.get("stomach.BIOAVAIL.retinol")
K.stomach.BIOAVAIL.carotene = K.dials.get("stomach.BIOAVAIL.carotene")
K.stomach.BIOAVAIL.vitD = K.dials.get("stomach.BIOAVAIL.vitD")
K.stomach.BIOAVAIL.vitE = K.dials.get("stomach.BIOAVAIL.vitE")
K.stomach.BIOAVAIL.vitK = K.dials.get("stomach.BIOAVAIL.vitK")
K.stomach.BIOAVAIL.thiamine = K.dials.get("stomach.BIOAVAIL.thiamine")
K.stomach.BIOAVAIL.riboflavin = K.dials.get("stomach.BIOAVAIL.riboflavin")
K.stomach.BIOAVAIL.niacin = K.dials.get("stomach.BIOAVAIL.niacin")
K.stomach.BIOAVAIL.vitB6 = K.dials.get("stomach.BIOAVAIL.vitB6")
K.stomach.BIOAVAIL.folate = K.dials.get("stomach.BIOAVAIL.folate")
K.stomach.BIOAVAIL.vitB12 = K.dials.get("stomach.BIOAVAIL.vitB12")
K.stomach.BIOAVAIL.choline = K.dials.get("stomach.BIOAVAIL.choline")
K.stomach.BIOAVAIL.sodium = K.dials.get("stomach.BIOAVAIL.sodium")
K.stomach.BIOAVAIL.potassium = K.dials.get("stomach.BIOAVAIL.potassium")
K.stomach.BIOAVAIL.calcium = K.dials.get("stomach.BIOAVAIL.calcium")
K.stomach.BIOAVAIL.magnesium = K.dials.get("stomach.BIOAVAIL.magnesium")
K.stomach.BIOAVAIL.zinc = K.dials.get("stomach.BIOAVAIL.zinc")
K.stomach.BIOAVAIL.iodine = K.dials.get("stomach.BIOAVAIL.iodine")
K.stomach.BIOAVAIL.selenium = K.dials.get("stomach.BIOAVAIL.selenium")
K.stomach.BIOAVAIL.efa = K.dials.get("stomach.BIOAVAIL.efa")

K.stomach.FAT_SOLUBLE = {}
K.stomach.FAT_SOLUBLE.retinol = true
K.stomach.FAT_SOLUBLE.carotene = true
K.stomach.FAT_SOLUBLE.vitE = true
K.stomach.FAT_SOLUBLE.vitK = true

-- A fat meal raises the plasma peak 32 %, so D absorbs at VITD_FAT_FREE + (1 - VITD_FAT_FREE) x fatFactor.
K.stomach.VITD_FAT_FREE = K.dials.get("stomach.VITD_FAT_FREE")

-- A record with no stomach starts empty.
function K.stomach.new()
    local stomach = {}
    stomach.buffer = K.vector.new()
    stomach.liquid = 0
    stomach.volX = 0
    stomach.liqKcal = 0
    return stomach
end

-- A food's water stays with the food. mlPerG (nil adds nothing) puts the volume excess (mlPerG - 1) x mass into
-- stomach.volX, which the satiety mass weighs at K.satiety.BETA.
function K.stomach.ingest(stomach, vector, mlPerG)
    K.vector.add(stomach.buffer, vector, 1)
    if mlPerG ~= nil then
        stomach.volX = stomach.volX + (mlPerG - 1) * K.stomach.massOf(vector)
    end
    return stomach
end

-- Non-haem iron, log-linear in the meal's phytic and ascorbic acid (mg; slopes S0195, S0194). The [IRON_MIN, IRON_MAX]
-- band is a game choice that under-reads the heaviest phytate meals (S0532's -82 % floored at -80 %) rather than
-- extrapolate past the measured range.
K.stomach.IRON_PHYTATE_SLOPE = K.dials.get("stomach.IRON_PHYTATE_SLOPE")
K.stomach.IRON_VITC_SLOPE = K.dials.get("stomach.IRON_VITC_SLOPE")
K.stomach.IRON_MIN = K.dials.get("stomach.IRON_MIN")
K.stomach.IRON_MAX = K.dials.get("stomach.IRON_MAX")
function K.stomach.ironFactor(phytateMg, vitCMg)
    return K.clamp(math.exp(K.stomach.IRON_PHYTATE_SLOPE * phytateMg + K.stomach.IRON_VITC_SLOPE * vitCMg), K.stomach.IRON_MIN, K.stomach.IRON_MAX) -- S0195, S0194, S0533, S0532
end

-- Saturating within about 10 g; the e-fold and the floor are game choices (S0197 supports only the direction). absorb
-- reads it once a call, off the meal's lipids (ctx) or the emptied vector's own.
K.stomach.FAT_EFOLD_G = K.dials.get("stomach.FAT_EFOLD_G")
K.stomach.FAT_FLOOR = K.dials.get("stomach.FAT_FLOOR")
function K.stomach.fatFactor(lipidsG)
    return K.clamp(1 - math.exp(-lipidsG / K.stomach.FAT_EFOLD_G), K.stomach.FAT_FLOOR, 1.0) -- S0197, S0199
end

-- Written into out, which the caller keeps, so the slow clock allocates nothing a minute.
function K.stomach.context(stomach, out)
    if out == nil then
        out = {}
    end
    local b = stomach.buffer
    out.phytate = b.phytate
    out.vitC = b.vitC
    out.calcium = b.calcium
    out.lipids = b.lipids
    return out
end

-- A fresh vector; the factors read ctx (the meal in the stomach) when given, else the emptied vector's own.
function K.stomach.absorb(emptied, ctx)
    local out = K.vector.new()
    local macros = K.retention.macroSet()
    local lip = emptied.lipids
    local phy = emptied.phytate
    local vc = emptied.vitC
    if ctx ~= nil then
        lip = ctx.lipids
        phy = ctx.phytate
        vc = ctx.vitC
    end
    local fat = K.stomach.fatFactor(lip)
    local keys = K.vector.KEYS
    for i = 1, #keys do
        local k = keys[i]
        if macros[k] then
            out[k] = emptied[k]
        elseif k == "iron" then
            out[k] = emptied.iron * K.stomach.BIOAVAIL.iron * K.stomach.ironFactor(phy, vc)
        elseif k == "magnesium" then
            out[k] = emptied.magnesium * K.stomach.BIOAVAIL.magnesium * K.interact.phytateMg(phy)
        elseif k == "zinc" then
            out[k] = emptied.zinc * K.stomach.BIOAVAIL.zinc * K.interact.phytateZn(phy) -- S0536 slope reused for zinc (open S1084: game choice)
        elseif k == "phytate" then
            out[k] = 0
        elseif k == "vitD" then
            out[k] = emptied.vitD * K.stomach.BIOAVAIL.vitD * (K.stomach.VITD_FAT_FREE + (1 - K.stomach.VITD_FAT_FREE) * fat)
        elseif K.stomach.FAT_SOLUBLE[k] then
            out[k] = emptied[k] * K.stomach.BIOAVAIL[k] * fat
        else
            out[k] = emptied[k] * (K.stomach.BIOAVAIL[k] or 1)
        end
    end
    return out
end

function K.stomach.toPool(pool, absorbed)
    K.vector.add(pool, absorbed, 1)
    return pool
end

-- The physical fill the mirror reads: both lanes at density 1, the scale CAPACITY_MAX_G was measured on (S1250, 734 mL
-- of water). LIQUID_WEIGHT weighs satiety alone, never this fill.
function K.stomach.fill(stomach)
    return K.satiety.fill(K.stomach.mass(stomach), K.stomach.CAPACITY_MAX_G)
end

-- The two lanes. Water drunk with or after a solid meal separates from it and empties at about its fasting pace (S2265);
-- only energy carried in the drink itself slows it (S1234), so stomach.liqKcal counts only that.
K.stomach.RATE_BASE = K.dials.get("stomach.RATE_BASE")
K.stomach.RATE_PER_KCAL = K.dials.get("stomach.RATE_PER_KCAL")
K.stomach.WATER_HALF_MIN = K.dials.get("stomach.WATER_HALF_MIN")
K.stomach.LIQUID_PER_KCAL = K.dials.get("stomach.LIQUID_PER_KCAL")
K.stomach.CAPACITY_MAX_G = K.dials.get("stomach.CAPACITY_MAX_G")
K.stomach.CAPACITY_HARD_G = K.dials.get("stomach.CAPACITY_HARD_G")

-- Gram keys only: efa sits inside lipids, ethanol is left out (ruling T17-2) and calories are energy, not mass.
function K.stomach.massOf(vector)
    return vector.water + vector.proteins + vector.carbs + vector.lipids + vector.fibre
end

function K.stomach.mass(stomach)
    return K.stomach.massOf(stomach.buffer) + stomach.liquid
end

-- The thirst view's pending water.
function K.stomach.water(stomach)
    return stomach.buffer.water + stomach.liquid
end

-- The buffer's own water is kept bit for bit; the drink's energy also joins stomach.liqKcal.
function K.stomach.ingestLiquid(stomach, vector)
    local own = stomach.buffer.water
    K.vector.add(stomach.buffer, vector, 1)
    stomach.buffer.water = own
    stomach.liquid = stomach.liquid + (vector.water or 0)
    stomach.liqKcal = stomach.liqKcal + (vector.calories or 0)
    return stomach
end

function K.stomach.solidRate(energy)
    return K.stomach.RATE_BASE + K.stomach.RATE_PER_KCAL * energy
end

function K.stomach.waterFraction(dtM, halfMin)
    if dtM <= 0 then
        return 0
    end
    return 1 - math.exp(-0.6931471805599453 * dtM / halfMin)
end

function K.stomach.liquidHalfMin(energy)
    return K.stomach.WATER_HALF_MIN + K.stomach.LIQUID_PER_KCAL * K.max(energy, 0)
end

-- The closed form of dE/dt = -(a + k E) over the step, never more than water's fraction; a lane with no energy (salt,
-- a pill, fibre alone) empties like water.
function K.stomach.solidFraction(energy, dtM)
    local fw = K.stomach.waterFraction(dtM, K.stomach.WATER_HALF_MIN)
    if energy <= 0 then
        return fw
    end
    local a = K.stomach.RATE_BASE
    local k = K.stomach.RATE_PER_KCAL
    local left = energy - a * dtM
    if k > 0 then
        left = (energy + a / k) * math.exp(-k * dtM) - a / k
    end
    local fe = 1
    if left > 0 then
        fe = K.max(0, 1 - left / energy)
    end
    return K.min(fe, fw)
end

-- The drink-borne energy, stomach.liqKcal capped at the lane's energy, sets the liquid lane's rate and leaves at the
-- solid fraction with the energy it rode in on; a NaN counter reads as the lane's energy (K.min answers its second
-- argument) and heals on the step. volX leaves at the solid fraction too.
function K.stomach.drain(stomach, dtH)
    local dtM = dtH * 60
    local energy = stomach.buffer.calories
    local f = K.stomach.solidFraction(energy, dtM)
    local liqE = K.min(stomach.liqKcal, energy)
    local fl = K.stomach.waterFraction(dtM, K.stomach.liquidHalfMin(liqE))
    local emptied = K.vector.add(K.vector.new(), stomach.buffer, f)
    local keys = K.vector.KEYS
    for i = 1, #keys do
        local k = keys[i]
        stomach.buffer[k] = stomach.buffer[k] * (1 - f)
    end
    local liquid = stomach.liquid
    local lw = liquid * fl
    stomach.liquid = liquid - lw
    stomach.volX = stomach.volX * (1 - f)
    stomach.liqKcal = liqE * (1 - f)
    emptied.water = emptied.water + lw
    return emptied
end

-- The hunger-relevant mass: an airy food fills a little more than its weight (volX) and drunk liquid counts at
-- LIQUID_WEIGHT (S1231). The physical fill and the soft cap read K.stomach.mass, both lanes whole, never volX (ruling T6c-1).
function K.stomach.satietyMass(stomach)
    return K.stomach.massOf(stomach.buffer) + K.satiety.BETA * stomach.volX + K.satiety.LIQUID_WEIGHT * stomach.liquid
end

-- record.stomachFill when finite, else the stomach's own fill; a malformed or non-finite stomach reads 0.
function K.stomach.recordFill(record)
    local f = record.stomachFill
    if K.finite(f) then
        return f
    end
    local s = record.stomach
    if s == nil or s.buffer == nil or type(s.liquid) ~= "number" then
        return 0
    end
    f = K.stomach.fill(s)
    if not K.finite(f) then
        return 0
    end
    return f
end

-- The writer's satiety F mass (never the mirror's stomachFill), where a drink's protein lands too.
-- The protein leaves in proportion to the lane's energy (drain), so the term fades as the meal empties.
function K.stomach.fullnessMass(stomach)
    return K.stomach.satietyMass(stomach) + K.satiety.PROTEIN_FILL * stomach.buffer.proteins
end

-- The food fill the two fed gates read (NUT.FED_FILL, K.nutrients.ACUTE_EMPTY_FILL): drunk water, in the liquid lane,
-- is not food.
function K.stomach.foodFill(stomach)
    return K.satiety.fill(K.stomach.massOf(stomach.buffer), K.stomach.CAPACITY_MAX_G)
end

-- Live: before the eat lands at the intake's acute test, after the minute's drain in Nutrients (which runs after
-- Kinetics).
function K.stomach.recordFoodFill(record)
    local s = record.stomach
    if s == nil or s.buffer == nil then
        return 0
    end
    local f = K.stomach.foodFill(s)
    if not K.finite(f) then
        return 0
    end
    return f
end
