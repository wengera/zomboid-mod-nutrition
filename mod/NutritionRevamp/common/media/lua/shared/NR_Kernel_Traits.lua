-- NR_Kernel_Traits.lua -- which of the five weight-band traits a body holds, read at day close. The fat axis reads a
-- lean-scaled fat index, so a muscular body carries more fat before a fat trait applies and
-- the male cuts sit at 25 % and 33.3 % body fat for every lean. The thinness axis reads the body-fat share, lx left
-- out, height-free: thinness is leanness, not weight. Each axis moves only past its cut by more than its margin; a
-- thinness rung excludes the fat rungs. K.HEIGHT_M is read at call time.
local K = NutritionRevamp.kernel
K.traits = {}

-- By effective sex (1 male, 2 female): fat-mass index, kg/m2, above which Overweight then Obese.
K.traits.FAT_CUTS = { { K.dials.get("traits.FAT_CUTS.1.1"), K.dials.get("traits.FAT_CUTS.1.2") }, { K.dials.get("traits.FAT_CUTS.2.1"), K.dials.get("traits.FAT_CUTS.2.2") } }
K.traits.FAT_WORDS = { "overweight", "obese" }
K.traits.FAT_MARGIN = K.dials.get("traits.FAT_MARGIN")

-- The fat-mass index an average-lean body at the same body-fat share would read.
function K.traits.fatIndex(fm, lm)
    return fm * K.strength.averageLean() / (K.HEIGHT_M * K.HEIGHT_M * lm)
end

-- Emaciated sits just above the male floor (S1910).
K.traits.THIN_CUTS = { K.dials.get("traits.THIN_CUTS.1"), K.dials.get("traits.THIN_CUTS.2"), K.dials.get("traits.THIN_CUTS.3") }
K.traits.THIN_WORDS = { "underweight", "veryUnderweight", "emaciated" }
K.traits.THIN_MARGIN = K.dials.get("traits.THIN_MARGIN")
-- The gap between the sexes' essential-fat floors (S1911); its size is a game choice.
K.traits.THIN_F_OFFSET = K.dials.get("traits.THIN_F_OFFSET")

-- The offset is taken off for effective sex 2, so one table of edges serves both sexes; no mass reads 0.
function K.traits.thinReading(fm, lm, sex)
    local w = lm + fm
    local bf = 0
    if w > 0 then
        bf = fm / w
    end
    if sex == 2 then
        bf = bf - K.traits.THIN_F_OFFSET
    end
    return bf
end

-- up is true when a higher reading is worse (the fat axis). Several rungs move in one read when passed.
function K.traits.held(rung, x, cuts, margin, up)
    local s = 1
    if not up then
        s = -1
    end
    while rung < #cuts and s * (x - cuts[rung + 1]) > margin do
        rung = rung + 1
    end
    while rung > 0 and s * (cuts[rung] - x) > margin do
        rung = rung - 1
    end
    return rung
end

-- Clears fatT while thinT > 0, and returns the band word.
function K.traits.axes(body, sex)
    local fatCuts = K.traits.FAT_CUTS[1]
    if sex == 2 then
        fatCuts = K.traits.FAT_CUTS[2]
    end
    body.thinT = K.traits.held(body.thinT, K.traits.thinReading(body.fm, body.lm, sex), K.traits.THIN_CUTS, K.traits.THIN_MARGIN, false)
    body.fatT = K.traits.held(body.fatT, K.traits.fatIndex(body.fm, body.lm), fatCuts, K.traits.FAT_MARGIN, true)
    if body.thinT > 0 then
        body.fatT = 0
        return K.traits.THIN_WORDS[body.thinT]
    end
    if body.fatT > 0 then
        return K.traits.FAT_WORDS[body.fatT]
    end
    return "normal"
end

-- The one list every server reader walks (#0550); vanilla never lets a character hold two, so the order is moot.
K.traits.WEIGHT_TRAITS = { "OBESE", "OVERWEIGHT", "UNDERWEIGHT", "VERY_UNDERWEIGHT", "EMACIATED" }

function K.traits.WANT(fatT, thinT)
    local want = {}
    want.OVERWEIGHT = fatT == 1
    want.OBESE = fatT == 2
    want.UNDERWEIGHT = thinT == 1
    want.VERY_UNDERWEIGHT = thinT == 2
    want.EMACIATED = thinT == 3
    return want
end
