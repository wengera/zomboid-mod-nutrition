-- NR_Kernel_Traits.lua -- the body-trait axes (Plan 13 Task 10; spec section 8): which of the five weight-band traits
-- (Overweight, Obese, Underweight, Very Underweight, Emaciated) a body holds, read at day close from the record.
-- The fat axis reads the lean-scaled fat index (K.traits.fatIndex) against Kelly 2009's FMI cuts through the effective
-- sex (K.body.effSex, NR.SexSpecific; ruling 13-17): each cut and its margin scale with the body's lean over the
-- untrained average's (Task 10b, Angus 2026-10-15), so a muscular body carries more fat before a fat trait applies and
-- the male cuts sit at 25 % and 33.3 % body fat for every lean. The thinness axis reads the body-fat share
-- fm / (lm + fm), the labile lean lx left out (ruling 13-15), against its edges (Plan 13 Task 10c, Angus 2026-10-15:
-- thinness is leanness, not weight), height-free; under the female values each edge is raised by the essential-fat
-- offset. Each axis holds a rung and moves only past its cut by more than its margin, several rungs in one read when
-- the reading is past several; a thinness rung excludes the fat rungs (precedence).
-- Pure: numbers and Lua tables in, numbers, strings and Lua tables out, no Java. Slow-clock code with no fast region.
-- This file sorts after NR_Kernel.lua, and every K.HEIGHT_M reference is at call time.
local K = NutritionRevamp.kernel
K.traits = {}

-- The fat cuts by effective sex (1 male, 2 female): fat-mass index, kg/m2, above which Overweight then Obese.
K.traits.FAT_CUTS = { { K.dials.get("traits.FAT_CUTS.1.1"), K.dials.get("traits.FAT_CUTS.1.2") }, { K.dials.get("traits.FAT_CUTS.2.1"), K.dials.get("traits.FAT_CUTS.2.2") } }
K.traits.FAT_WORDS = { "overweight", "obese" }
K.traits.FAT_MARGIN = K.dials.get("traits.FAT_MARGIN")

-- The lean-scaled fat index of fat fm on lean lm: fm / (H2 * lm / Favg), the fat-mass index an average-lean body at the
-- same body-fat share would read. Comparing it with a cut c and margin m is comparing fm with c * H2 * lm / Favg and
-- m * H2 * lm / Favg (Task 10b).
function K.traits.fatIndex(fm, lm)
    return fm * K.strength.averageLean() / (K.HEIGHT_M * K.HEIGHT_M * lm)
end

-- The thinness cuts (male): the body-fat share below which Underweight (shown as Overly Lean), Very Underweight
-- (Gaunt), Emaciated. Emaciated sits just above the male floor, 4-6 % (S1910).
K.traits.THIN_CUTS = { K.dials.get("traits.THIN_CUTS.1"), K.dials.get("traits.THIN_CUTS.2"), K.dials.get("traits.THIN_CUTS.3") }
K.traits.THIN_WORDS = { "underweight", "veryUnderweight", "emaciated" }
K.traits.THIN_MARGIN = K.dials.get("traits.THIN_MARGIN")
-- The female values' essential-fat offset, added to every thin edge for effective sex 2 (female 20 / 16 / 13 %): the
-- gap between the sexes' floors, men 4-6 % (S1910) and women a suggested minimum of 12-14 % (S1911); the 8 points are
-- a game choice.
K.traits.THIN_F_OFFSET = K.dials.get("traits.THIN_F_OFFSET")

-- The thin axis's reading of a body: its body-fat share fm / (lm + fm), less the essential-fat offset for effective
-- sex 2, so one table of edges serves both sexes. A body with no mass reads 0 (the deepest rung).
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

-- The rung held from rung at the reading x over the ascending-severity cuts: step deeper while the next cut is passed
-- by more than margin, step back while the current cut is undone by more than margin. up is true when a higher reading
-- is worse (the fat axis), false when a lower one is (thinness).
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

-- Writes body.fatT (0..2) and body.thinT (0..3) from the body's lean-scaled fat index and body-fat share, sex the
-- effective sex (2 reads the female fat cuts and the offset thin edges, any other value the male), clears fatT while
-- thinT > 0, and returns the band word: the thin word, else the fat word, else "normal".
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

-- The five weight-band trait names, in K.traits.WANT's names (CharacterTrait registry fields, #0550): the one list every
-- server reader walks; vanilla never lets a character hold two, so the order is moot.
K.traits.WEIGHT_TRAITS = { "OBESE", "OVERWEIGHT", "UNDERWEIGHT", "VERY_UNDERWEIGHT", "EMACIATED" }

-- The five weight-band trait names each true or false from the rungs: one fat trait at most, one thin trait at most.
function K.traits.WANT(fatT, thinT)
    local want = {}
    want.OVERWEIGHT = fatT == 1
    want.OBESE = fatT == 2
    want.UNDERWEIGHT = thinT == 1
    want.VERY_UNDERWEIGHT = thinT == 2
    want.EMACIATED = thinT == 3
    return want
end
