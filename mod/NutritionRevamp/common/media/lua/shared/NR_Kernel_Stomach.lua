-- NR_Kernel_Stomach.lua -- the stomach's two lanes and absorption into the pool (spec § 4.2, § 4.4; Plan 11c spec
-- § 5a). A food lands in the solid buffer, its water with it (ingest); a drink's water lands in the liquid lane and
-- its other keys, its energy among them, in the buffer (ingestLiquid, ruling 11c-12). The slow clock empties both
-- lanes per step (drain): the solid lane's energy at a zero-order rate rising with the energy it holds, every other
-- key in the same proportion, never faster than water; the liquid lane first-order at a half-time that grows with the
-- solid lane's energy. Absorption applies per-nutrient bioavailability and the phytate/vitamin-C iron interaction
-- (absorb); the absorbed vector accumulates into the pool (toPool). The unabsorbed remainder is discarded.
-- Ruling T17-1 (x151r #2981): the factor reads the meal in the stomach, not the share emptied this
-- minute. The slow clock takes K.stomach.context(stomach) -- the buffer's phytate, vitC and calcium
-- BEFORE the minute's emptying -- and hands it to absorb(emptied, ctx), so a 400 mg phytate loaf reads
-- 400 mg. absorb(emptied) with no ctx keeps the Plan 2 reading off the emptied vector itself. Ruling T19-1 extends the
-- context to the fat factor: ctx carries the buffer's lipids. Caffeine and ethanol never enter the buffer (ruling
-- T17-2: the intake landing diverts them to the acute kernel's gut lane), so their BIOAVAIL entries stay 1.0 and unused.
-- The emptying constants rest on settled rows as labelled inferences (Plan 11c's block below); the absorption factors
-- cite settled rows. Pure: tables in, tables out, no Java. Slow-clock code with no @fastpath region, so math.exp and
-- the bounded `for` over K.vector.KEYS (a Lua table the kernel built, so `#` is a Lua length) are allowed. This file
-- sorts before NR_Kernel_Vector.lua, so every K.vector and K.retention reference is at call time, never at load.
local K = NutritionRevamp.kernel
K.stomach = {}

-- Per-nutrient bioavailability of the emptied vector. water and fibre pass through as intake
-- (judgement); vitC 0.85 is a judgement (food vitamin C is absorbed at about 70-90 %); phytate is an
-- anti-nutrient context, not a pooled nutrient, so it absorbs at 0. A macro has no entry and passes at
-- 1.0; every non-macro key is listed (an unlisted one would pass at 1.0). The fat-soluble keys
-- (retinol, carotene, vitD, vitE, vitK) take the fat factor in absorb on top of this entry.
K.stomach.BIOAVAIL = {}
K.stomach.BIOAVAIL.water = 1.0
K.stomach.BIOAVAIL.fibre = 1.0
K.stomach.BIOAVAIL.vitC = 0.85 -- design-phase-v1 game choice: food vitamin C absorption 70-90 %, no settled row
K.stomach.BIOAVAIL.iron = 0.18 -- S0434 (the RDA's assumed 18 %), S0535 (14-18 % for mixed diets)
K.stomach.BIOAVAIL.phytate = 0.0
K.stomach.BIOAVAIL.retinol = 1.0 -- design-phase-v1 game choice: absorb default 1.0 for a new key with no row
K.stomach.BIOAVAIL.carotene = 0.14 -- S0156 (beta-carotene from whole mixed vegetables, ~14 % of purified)
K.stomach.BIOAVAIL.vitD = 1.0 -- design-phase-v1 game choice: absorb default 1.0 for a new key with no row
K.stomach.BIOAVAIL.vitE = 1.0 -- design-phase-v1 game choice: absorb default 1.0 for a new key with no row
K.stomach.BIOAVAIL.vitK = 1.0 -- design-phase-v1 game choice: absorb default 1.0 for a new key with no row
K.stomach.BIOAVAIL.thiamine = 1.0 -- design-phase-v1 game choice: absorb default 1.0 for a new key with no row
K.stomach.BIOAVAIL.riboflavin = 1.0 -- design-phase-v1 game choice: absorb default 1.0 for a new key with no row
K.stomach.BIOAVAIL.niacin = 1.0 -- design-phase-v1 game choice: absorb default 1.0 for a new key with no row
K.stomach.BIOAVAIL.vitB6 = 1.0 -- design-phase-v1 game choice: absorb default 1.0 for a new key with no row
K.stomach.BIOAVAIL.folate = 1.0 -- design-phase-v1 game choice: absorb default 1.0 (folate in DFE already folds in its availability)
K.stomach.BIOAVAIL.vitB12 = 1.0 -- design-phase-v1 game choice: absorb default 1.0 for a new key with no row
K.stomach.BIOAVAIL.choline = 1.0 -- design-phase-v1 game choice: absorb default 1.0 for a new key with no row
K.stomach.BIOAVAIL.sodium = 1.0 -- design-phase-v1 game choice: absorb default 1.0 for a new key with no row
K.stomach.BIOAVAIL.potassium = 1.0 -- design-phase-v1 game choice: absorb default 1.0 for a new key with no row
K.stomach.BIOAVAIL.calcium = 0.25 -- S0413 (fractional absorption of dietary calcium, about 25 % of intake)
K.stomach.BIOAVAIL.magnesium = 0.325 -- S0536 (fractional magnesium absorption 32.5 % with no added phytate)
K.stomach.BIOAVAIL.zinc = 1.0 -- design-phase-v1 game choice: absorb default 1.0 for a new key with no row
K.stomach.BIOAVAIL.iodine = 1.0 -- design-phase-v1 game choice: absorb default 1.0 for a new key with no row
K.stomach.BIOAVAIL.selenium = 1.0 -- design-phase-v1 game choice: absorb default 1.0 for a new key with no row
K.stomach.BIOAVAIL.efa = 1.0 -- design-phase-v1 game choice: absorb default 1.0 for a new key with no row
K.stomach.BIOAVAIL.caffeine = 1.0 -- design-phase-v1 game choice: absorb default 1.0 for a new key with no row
K.stomach.BIOAVAIL.ethanol = 1.0 -- design-phase-v1 game choice: absorb default 1.0 for a new key with no row

-- The fat-soluble keys that take the fat factor in absorb (vitamin D takes its own floored form).
K.stomach.FAT_SOLUBLE = {}
K.stomach.FAT_SOLUBLE.retinol = true
K.stomach.FAT_SOLUBLE.carotene = true
K.stomach.FAT_SOLUBLE.vitE = true
K.stomach.FAT_SOLUBLE.vitK = true

-- Vitamin D's fat-free share of its fat-meal absorption: 1 / 1.32 (a fat meal raises the plasma peak
-- 32 %), so D absorbs at VITD_FAT_FREE + (1 - VITD_FAT_FREE) x fatFactor, 0.772 with no fat at all.
K.stomach.VITD_FAT_FREE = 0.76 -- S0198 (+32 % with a fat-containing meal; 1/1.32 = 0.76, derived)

-- A fresh stomach: an all-zero solid buffer and an empty liquid lane (spec § 4, ruling 11c-15: a record with no
-- stomach starts empty).
function K.stomach.new()
    local stomach = {}
    stomach.buffer = K.vector.new()
    stomach.liquid = 0
    return stomach
end

-- A food into the solid buffer, its water with it (a food's water stays with the food, spec § 3.1); returns the
-- stomach.
function K.stomach.ingest(stomach, vector)
    K.vector.add(stomach.buffer, vector, 1)
    return stomach
end

-- The meal-context multiplier on non-haem iron absorption, log-linear in the meal's phytic acid and
-- ascorbic acid (mg): exp(-0.0034 * phytate + 0.0065 * vitC), vitamin C counteracting phytate. The
-- [0.2, 4.0] band is a judgement bounding the log-linear model: its floor caps the loss at -80 %,
-- just above S0532's measured -82 % at 250 mg phytate PHOSPHORUS (about 886 mg phytic acid, which
-- the unclamped model would put near 0.05), so the band deliberately under-reads the heaviest
-- phytate meals rather than extrapolate the log-linear fit past the measured range.
-- design-phase-v1 game choice: the [0.2, 4.0] band is a judgement; S0532 supports the -82 % at 250 mg phytate P, which the floor caps at -80 %. Of the S tags below, S0195 and S0194 state the slopes (-0.0034 per mg phytate, +0.0065 per mg vitamin C); S0533 is a direction row and S0532 the 250 mg dose-response point, neither a slope.
function K.stomach.ironFactor(phytateMg, vitCMg)
    return K.clamp(math.exp(-0.0034 * phytateMg + 0.0065 * vitCMg), 0.2, 4.0) -- S0195, S0194, S0533, S0532
end

-- The fat co-ingestion multiplier for a fat-soluble nutrient: 1 - exp(-lipids / FAT_EFOLD_G), floored at 0.05
-- (fat-free: negligible carotenoid absorption) and saturating within about 10 g.
-- design-phase-v1 game choice: the e-fold and the 0.05 floor are judgements; S0197/S0199 support only the direction and the 28 g reference.
-- absorb reads it once per call, off ctx.lipids (the meal's lipids in the stomach, ruling T19-1) or the
-- emptied vector's own when no context is given, for the fat-soluble keys.
K.stomach.FAT_EFOLD_G = 3 -- design-phase-v1 game choice: a few grams of fat per meal give near-full fat-soluble absorption (S0197 carotene negligible without fat, S0198 vitamin D +32 % with fat - direction only; no row for the saturation; Plan 2 shipped 10 g, which left a 30 g-fat meal at 68 % once the factor read the meal in the stomach (Plan 4 close))
function K.stomach.fatFactor(lipidsG)
    return K.clamp(1 - math.exp(-lipidsG / K.stomach.FAT_EFOLD_G), 0.05, 1.0) -- S0197, S0199
end

-- The meal context the interaction factors read (rulings T17-1, T19-1): the buffer's phytate, vitC,
-- calcium and lipids totals, taken BEFORE the minute's emptying. Written into out (a table the caller
-- keeps and overwrites, so the slow clock allocates nothing per minute); a nil out gets a fresh table.
-- Returns out.
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

-- Absorb an emptied vector: a fresh vector. A macro passes unchanged; iron takes its bioavailability
-- times the meal-context factor of phytate and vitC; magnesium and zinc take their bioavailability times
-- the phytate factor; phytate absorbs to 0. The phytate and vitC the factors read are ctx's (the meal in
-- the stomach, ruling T17-1) when ctx is given, else the emptied vector's own. Vitamin D takes its
-- bioavailability times VITD_FAT_FREE + (1 - VITD_FAT_FREE) x the fat factor; retinol, carotene, vitE
-- and vitK take their bioavailability times the fat factor, both read off the meal's lipids in the
-- stomach (ctx, ruling T17-1, extended by T19-1) or the emptied vector's when no context is given; any
-- other key takes its bioavailability (1.0 when unlisted).
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
            -- the phytate factor reads the meal's phytate (S0536 direction and slope, S1084 the zinc reuse)
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

-- Accumulate the absorbed vector into the pool; returns the pool.
function K.stomach.toPool(pool, absorbed)
    K.vector.add(pool, absorbed, 1)
    return pool
end

-- The physical fill (record.stomachFill) the acute dose test and the mirror read, and the writer's fallback (the
-- writer's F is W.satietyF, the fullness mass with the protein term): the stomach's satiety mass (structure D: the solid
-- lane plus a fifth of drunk liquid, K.stomach.satietyMass) over its maximal capacity, clamped to [0, 1] (K.satiety.fill;
-- ruling 11c-19, Plan 11c Task 6 amendment 2). The soft cap reads K.stomach.mass whole, never this fill.
function K.stomach.fill(stomach)
    return K.satiety.fill(K.stomach.satietyMass(stomach), K.stomach.CAPACITY_MAX_G)
end

-- Plan 11c (spec § 5a rulings 11c-4, 11c-5 and 11c-8): fill by mass and the stomach's two lanes. Appended below the
-- Plan 2 code; the first-order pieces it replaced retired in Task 6. The solid lane (stomach.buffer)
-- empties energy at a zero-order rate that rises with the energy it holds, every other key leaving in the same
-- proportion, never faster than water; the liquid lane (stomach.liquid, grams of drunk water) half-empties in
-- WATER_HALF_MIN plus LIQUID_PER_KCAL per kcal in the solid lane. K.stomach.new lays both lanes.
K.stomach.RATE_BASE = 1.25 -- S0131 (labelled inference, ruling 11c-4): kcal/min at no load, fitted so the rate reads Hunt 1985's overall 2.5 kcal/min at its mean load; liquid carbohydrate meals applied to solids
K.stomach.RATE_PER_KCAL = 0.0025 -- S0131 (labelled inference, ruling 11c-4): per min, the rise with load (+0.72 kcal/min for +300 kcal of volume, +0.62 for +240 kcal of density: 0.0024 and 0.0026 per kcal)
K.stomach.WATER_HALF_MIN = 13 -- S1245 (Mudie 2014: 240 mL of water half-empties in 13 +/- 1 min, fasted); the fastest either lane empties
K.stomach.LIQUID_PER_KCAL = 0.12 -- S1234 over S1245 (labelled inference, ruling 11c-5): min of liquid half-time per kcal in the solid lane, fitted to Camps 2016's thin 100 and 500 kcal shakes (26.5 and 69.5 min) over water's 13 min
K.stomach.CAPACITY_G = 430 -- S1250 (labelled inference, ruling 11c-8): the comfortable capacity, van Dyck 2016's 428 mL of water to satiation taken as stomach mass at density 1
K.stomach.CAPACITY_MAX_G = 730 -- S1250 (labelled inference, ruling 11c-8): the soft cap, 734 mL of water to maximum fullness; S1251's slow nutrient drinks (937-1048 mL) bound it above
K.stomach.CAPACITY_HARD_G = 1100 -- S1253 (labelled inference): the soft cap's full scale, a balloon at maximal discomfort in lean subjects (1100 mL, n = 4)

-- A vector's mass in grams: its water, macronutrients and fibre (the gram keys of the buffer's mass, efa inside lipids, ethanol left out by ruling T17-2; calories are energy, not mass).
function K.stomach.massOf(vector)
    return vector.water + vector.proteins + vector.carbs + vector.lipids + vector.fibre
end

-- The stomach's mass: the solid buffer's mass plus the liquid lane.
function K.stomach.mass(stomach)
    return K.stomach.massOf(stomach.buffer) + stomach.liquid
end

-- The stomach's still-unabsorbed water in both lanes (the thirst view's pending water, ruling T1-1).
function K.stomach.water(stomach)
    return stomach.buffer.water + stomach.liquid
end

-- A drink: its water into the liquid lane, every other key (its energy among them, ruling 11c-5) into the solid
-- buffer, whose own water is kept bit for bit. The vector is not changed. Returns the stomach.
function K.stomach.ingestLiquid(stomach, vector)
    local own = stomach.buffer.water
    K.vector.add(stomach.buffer, vector, 1)
    stomach.buffer.water = own
    stomach.liquid = stomach.liquid + (vector.water or 0)
    return stomach
end

-- The solid lane's energy delivery at energy E: RATE_BASE + RATE_PER_KCAL x E kcal a minute.
function K.stomach.solidRate(energy)
    return K.stomach.RATE_BASE + K.stomach.RATE_PER_KCAL * energy
end

-- A first-order lane's emptied fraction over dtM minutes at a half-time of halfMin minutes; nothing for no time.
function K.stomach.waterFraction(dtM, halfMin)
    if dtM <= 0 then
        return 0
    end
    return 1 - math.exp(-0.6931471805599453 * dtM / halfMin)
end

-- The liquid lane's half-time with E kcal in the solid lane (ruling 11c-5).
function K.stomach.liquidHalfMin(energy)
    return K.stomach.WATER_HALF_MIN + K.stomach.LIQUID_PER_KCAL * K.max(energy, 0)
end

-- The solid lane's emptied fraction over dtM minutes holding E kcal: the closed form of dE/dt = -(a + k E) over the
-- step (a whole buffer when the step outlasts its energy), never more than water's fraction; a lane with no energy
-- (salt, a pill, fibre alone) empties like water.
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

-- Empty both lanes over dtH game hours: the solid fraction of every buffered key and the liquid lane's share of its
-- water move out as a fresh vector (the liquid's share added to its water); the buffer and the lane keep the rest.
-- The solid lane's energy before the step sets both fractions.
function K.stomach.drain(stomach, dtH)
    local dtM = dtH * 60
    local energy = stomach.buffer.calories
    local f = K.stomach.solidFraction(energy, dtM)
    local fl = K.stomach.waterFraction(dtM, K.stomach.liquidHalfMin(energy))
    local emptied = K.vector.add(K.vector.new(), stomach.buffer, f)
    local keys = K.vector.KEYS
    for i = 1, #keys do
        local k = keys[i]
        stomach.buffer[k] = stomach.buffer[k] * (1 - f)
    end
    local liquid = stomach.liquid
    local lw = liquid * fl
    stomach.liquid = liquid - lw
    emptied.water = emptied.water + lw
    return emptied
end

-- The hunger-relevant mass (structure D, ruling 11c-30): the solid lane's mass plus K.satiety.LIQUID_WEIGHT x the
-- liquid lane, drunk liquid counting at a fifth (S1231's null for water drunk alongside; S1233's drink volumes). The
-- fill (K.stomach.fill) passes it to K.satiety.fill and stays physical, while the writer's F reads K.stomach.fullnessMass, it plus the protein term (W.satietyF, ruling T5-2); the soft cap still reads K.stomach.mass, both lanes whole (S1250).
function K.stomach.satietyMass(stomach)
    return K.stomach.massOf(stomach.buffer) + K.satiety.LIQUID_WEIGHT * stomach.liquid
end

-- Plan 11c close (ruling C-2): the fill a reader takes from a record (the intake's acute dose test, the mirror):
-- record.stomachFill, the kinetics' stamp, when finite; else the stomach's own fill when the record holds a stomach with
-- a solid buffer and a liquid lane; else 0, since ruling 11c-15 a new stomach is empty. A non-finite stomach, or one
-- whose liquid lane is not a number (malformed, ruling C9-9), reads 0.
function K.stomach.recordFill(record)
    local f = record.stomachFill
    if type(f) == "number" and f - f == 0 then
        return f
    end
    local s = record.stomach
    if s == nil or s.buffer == nil or type(s.liquid) ~= "number" then
        return 0
    end
    f = K.stomach.fill(s)
    if f - f ~= 0 then
        return 0
    end
    return f
end

-- Plan 11d Task 5 (rulings 11d-5, T5-2): the mass the writer's satiety F reads (W.satietyF; never K.stomach.fill, whose
-- physical stomachFill gates emptiness): the satiety mass plus K.satiety.PROTEIN_FILL x the solid lane's protein, where a
-- drink's protein lands too (ruling 11c-12). The protein leaves in proportion to the lane's energy (drain), so the term
-- fades as the meal empties. Appended so no line above moves; one statement a line for the coverage gate.
function K.stomach.fullnessMass(stomach)
    return K.stomach.satietyMass(stomach) + K.satiety.PROTEIN_FILL * stomach.buffer.proteins
end
