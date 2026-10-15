-- NR_Kernel_Traits.lua -- the body-trait axes (Plan 13 Task 10; spec section 8): which of the five weight-band traits
-- (Overweight, Obese, Underweight, Very Underweight, Emaciated) a body holds, read at day close from the record.
-- The fat axis reads the lean-scaled fat index (K.traits.fatIndex) against Kelly 2009's FMI cuts through the effective
-- sex (K.body.effSex, NR.SexSpecific; ruling 13-17): each cut and its margin scale with the body's lean over the
-- untrained average's (Task 10b, Angus 2026-10-15), so a muscular body carries more fat before a fat trait applies and
-- the male cuts sit at 25 % and 33.3 % body fat for every lean. The thinness axis reads the BMI (lm + fm) / H2 against
-- WHO's thinness grades, the labile lean lx left out (ruling 13-15). Each axis holds a rung and moves only past its cut
-- by more than its margin, several rungs in one read when the reading is past several; a thinness rung excludes the fat
-- rungs (precedence).
-- Pure: numbers and Lua tables in, numbers, strings and Lua tables out, no Java. Slow-clock code with no fast region.
-- This file sorts after NR_Kernel.lua, and every K.HEIGHT_M reference is at call time.
local K = NutritionRevamp.kernel
K.traits = {}

-- The fat cuts by effective sex (1 male, 2 female): fat-mass index, kg/m2, above which Overweight then Obese.
K.traits.FAT_CUTS = { { 6, 9 }, { 9, 13 } } -- S2056 (men: excess fat > 6, obese > 9); S2057 (women: > 9, > 13), Kelly 2009 Table 4
K.traits.FAT_WORDS = { "overweight", "obese" }
K.traits.FAT_MARGIN = 0.3 -- game choice (spec section 8: the damping margin, FMI kg/m2)

-- The untrained average lean Favg, fOfBio(5) of the strength defaults (52.02 kg at 1.70 m), read at call time.
function K.traits.leanAvg()
    return K.strength.fOfBio(5, K.strength.DEFAULTS)
end

-- The lean-scaled fat index of fat fm on lean lm: fm / (H2 * lm / Favg), the fat-mass index an average-lean body at the
-- same body-fat share would read. Comparing it with a cut c and margin m is comparing fm with c * H2 * lm / Favg and
-- m * H2 * lm / Favg (Task 10b).
function K.traits.fatIndex(fm, lm)
    return fm * K.traits.leanAvg() / (K.HEIGHT_M * K.HEIGHT_M * lm)
end

-- The thinness cuts: BMI below which Underweight, Very Underweight, Emaciated.
K.traits.THIN_CUTS = { 18.5, 17, 16 } -- S2059 (WHO: underweight < 18.5, moderate thinness < 17, severe < 16)
K.traits.THIN_WORDS = { "underweight", "veryUnderweight", "emaciated" }
K.traits.THIN_MARGIN = 0.5 -- game choice (spec section 8: the damping margin, BMI kg/m2)

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

-- Writes body.fatT (0..2) and body.thinT (0..3) from the body's lean-scaled fat index and BMI at K.HEIGHT_M, sex the
-- effective sex (2 reads the female fat cuts, any other value the male), clears fatT while thinT > 0, and returns the
-- band word: the thin word, else the fat word, else "normal".
function K.traits.axes(body, sex)
    local H2 = K.HEIGHT_M * K.HEIGHT_M
    local fatCuts = K.traits.FAT_CUTS[1]
    if sex == 2 then
        fatCuts = K.traits.FAT_CUTS[2]
    end
    body.thinT = K.traits.held(body.thinT, (body.lm + body.fm) / H2, K.traits.THIN_CUTS, K.traits.THIN_MARGIN, false)
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
