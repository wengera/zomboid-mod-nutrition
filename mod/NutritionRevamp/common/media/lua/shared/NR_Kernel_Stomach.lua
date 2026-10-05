-- NR_Kernel_Stomach.lua -- the stomach buffer, first-order gastric emptying and absorption into the
-- pool (spec § 4.2, § 4.4). A meal vector lands in the stomach buffer (ingest); the slow clock empties
-- a first-order fraction of every buffered nutrient per step (empty); absorption applies per-nutrient
-- bioavailability and the phytate/vitamin-C iron interaction read off the emptied vector itself
-- (absorb); the absorbed vector accumulates into the pool (toPool), the provisional accumulator Plan 4's
-- record engine replaces. The unabsorbed remainder is discarded, never returned to the stomach.
-- The gastric-emptying constants rest on OPEN science rows and ship as labelled game choices
-- (spec § 7 item 37); the absorption factors cite settled rows. Pure: tables in, tables out, no Java.
-- Slow-clock code with no @fastpath region, so math.exp and the bounded `for` over K.vector.KEYS (a Lua
-- table the kernel built, so `#` is a Lua length) are allowed. This file sorts before
-- NR_Kernel_Vector.lua, so every K.vector and K.retention reference is at call time, never at load.
local K = NutritionRevamp.kernel
K.stomach = {}

-- The half-time of a mixed solid meal, in game hours (a mixed solid meal half-empties in about 2 h).
K.stomach.HALF_TIME_H = 2.0 -- S0130 design-phase-v1: open row, a game choice until it settles (spec § 7 item 37)

-- The bulk at which the stomach reads full (judgement: a game choice in bulkOf's units).
K.stomach.FULL_BULK = 8.0

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

-- A fresh stomach: an all-zero buffer and no bulk.
function K.stomach.new()
    local stomach = {}
    stomach.buffer = K.vector.new()
    stomach.bulk = 0
    return stomach
end

-- A vector's stomach-fill contribution: energy / 100 + fibre * 0.5 + water / 100. Judgement, a game
-- choice: one fill unit mixing energy, fibre bulk and liquid volume; the fast hunger term reads the
-- fill (Task 11).
function K.stomach.bulkOf(vector)
    return vector.calories / 100 + vector.fibre * 0.5 + vector.water / 100
end

-- Seed a stomach full: bulk = FULL_BULK, the buffer untouched (so nothing absorbs from it); returns the
-- stomach. Plan 2 game choice (Task 11) -- judgement: the character ate before the apocalypse, so a
-- new or respawned record starts at vanilla's hunger 0 and empties on the gastric half-time.
function K.stomach.seedFull(stomach)
    stomach.bulk = K.stomach.FULL_BULK
    return stomach
end

-- Add a meal vector into the buffer and its bulk into the fill total; returns the stomach.
function K.stomach.ingest(stomach, vector)
    K.vector.add(stomach.buffer, vector, 1)
    stomach.bulk = stomach.bulk + K.stomach.bulkOf(vector)
    return stomach
end

-- The composition multiplier on the half-time: fat and fibre slow emptying, a pure liquid (no energy,
-- no fibre, some water) empties at a quarter of the half-time. The coefficients are game choices.
function K.stomach.compositionScale(vector)
    if vector.calories == 0 and vector.fibre == 0 and vector.water > 0 then
        return 0.25 -- S0131 design-phase-v1: open row, a game choice until it settles (spec § 7 item 37)
    end
    return K.clamp(1 + vector.lipids / 40 + vector.fibre / 15, 0.5, 3.0) -- S0131 design-phase-v1: open row, a game choice until it settles (spec § 7 item 37)
end

-- The first-order fraction emptied over dtH hours: 1 - exp(-ln2 * dtH / (halfTimeH * compScale)), ln 2
-- as a literal. A non-positive step empties nothing.
function K.stomach.emptyFraction(halfTimeH, compScale, dtH)
    if dtH <= 0 then
        return 0
    end
    return 1 - math.exp(-0.6931471805599453 * dtH / (halfTimeH * compScale)) -- S0130 design-phase-v1: open row, a game choice until it settles (spec § 7 item 37)
end

-- Empty the stomach over dtH hours: the emptied fraction of every buffered key moves out as a fresh
-- vector, the buffer and the bulk keep the rest. The composition scale is read off the buffer itself.
function K.stomach.empty(stomach, dtH)
    local f = K.stomach.emptyFraction(K.stomach.HALF_TIME_H, K.stomach.compositionScale(stomach.buffer), dtH)
    local emptied = K.vector.add(K.vector.new(), stomach.buffer, f)
    local keys = K.vector.KEYS
    for i = 1, #keys do
        local k = keys[i]
        stomach.buffer[k] = stomach.buffer[k] * (1 - f)
    end
    stomach.bulk = stomach.bulk * (1 - f)
    return emptied
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

-- The fat co-ingestion multiplier for a fat-soluble nutrient: 1 - exp(-lipids / 10), floored at 0.05
-- (fat-free: negligible carotenoid absorption) and saturating by 28 g.
-- design-phase-v1 game choice: the /10 saturation and the 0.05 floor are judgements; S0197/S0199 support only the direction and the 28 g reference.
-- absorb reads it once per emptied vector, off the vector's own lipids, for the fat-soluble keys.
function K.stomach.fatFactor(lipidsG)
    return K.clamp(1 - math.exp(-lipidsG / 10), 0.05, 1.0) -- S0197, S0199
end

-- Absorb an emptied vector: a fresh vector. A macro passes unchanged; iron takes its bioavailability
-- times the meal-context factor read off the emptied vector's own phytate and vitC; magnesium and zinc take
-- their bioavailability times the phytate factor; phytate absorbs to
-- 0; vitamin D takes its bioavailability times VITD_FAT_FREE + (1 - VITD_FAT_FREE) x the fat factor;
-- retinol, carotene, vitE and vitK take their bioavailability times the fat factor, both read off the
-- emptied vector's own lipids; any other key takes its bioavailability (1.0 when unlisted).
function K.stomach.absorb(emptied)
    local out = K.vector.new()
    local macros = K.retention.macroSet()
    local fat = K.stomach.fatFactor(emptied.lipids)
    local keys = K.vector.KEYS
    for i = 1, #keys do
        local k = keys[i]
        if macros[k] then
            out[k] = emptied[k]
        elseif k == "iron" then
            out[k] = emptied.iron * K.stomach.BIOAVAIL.iron * K.stomach.ironFactor(emptied.phytate, emptied.vitC)
        elseif k == "magnesium" then
            -- the phytate factor reads the emptied vector's own phytate (S0536 direction and slope, S1084 the zinc reuse)
            out[k] = emptied.magnesium * K.stomach.BIOAVAIL.magnesium * K.interact.phytateMg(emptied.phytate)
        elseif k == "zinc" then
            out[k] = emptied.zinc * K.stomach.BIOAVAIL.zinc * K.interact.phytateZn(emptied.phytate) -- S0536, S1084
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

-- The fill scalar the fast hunger term reads: bulk over FULL_BULK, clamped to [0, 1].
function K.stomach.fill(stomach)
    return K.clamp(stomach.bulk / K.stomach.FULL_BULK, 0, 1)
end
