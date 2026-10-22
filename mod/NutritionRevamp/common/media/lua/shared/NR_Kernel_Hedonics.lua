-- NR_Kernel_Hedonics.lua -- food hedonics (Plan 19 Task 5; spec docs/superpowers/specs/2026-10-21-dials-and-hedonics-design.md
-- section B.2): four rules on top of vanilla's per-item UnhappyChange and BoredomChange, which stay the base (B.1).
-- Every magnitude is a dial of the hedonics domain (NR_Data_Dials.lua); every rule is pure, runs at an eat, an
-- ingredient add or the existing writer minute, never per tick (Rule 6), and its adapters are NR_Server_Intake's and
-- NR_Server_Writer's (Task 6).
--  R1 plain energy (the stick of butter): a plain energy food is energy-dense (PLAIN_KCAL a 100 g or more), takes at
--     least PLAIN_SHARE of its macro energy from one macro, is no vanilla treat (UnhappyChange under 0), and falls in
--     none of S2291's sodium pairings (fat and sodium, carbohydrate and sodium), unless one macro gives PAIR_SHARE of
--     its energy or more: a food almost all one macro is eaten as plain energy whatever its salt (ruling T5-1: salted
--     butter, margarine, mayonnaise); a pairing is palatable (S2291, S2289).
--     The classification is a generated table (tools/food_hedonics.py, NR_Data_Hedonics.lua) from the nutrient data,
--     read through K.hedonics.isPlain so the generator and the budget oracle classify by the same rule. Each eat books
--     its kcal, and its plain kcal, into a ring of RING_N online hours (K.hedonics.book); the ring's plain share over
--     at least SHARE_MIN_KCAL drives an UNHAPPINESS floor on the FLOOR_KNOTS curve (K.hedonics.target), composed with
--     monotony's in the writer's self-releasing floor, so it releases as the share falls. An ingredient added to an
--     evolved dish is not an eat and never books.
--  R2 preparation quality: a cooked or evolved dish's relief (the negative side of its UnhappyChange) is scaled by the
--     cook's Cooking level on the PREP_KNOTS curve (K.hedonics.prep); a dish's sad side is never made worse by skill.
--  R3 alliesthesia: a food's sad UnhappyChange (the positive side) is scaled by ALLIES_F while the mod's HUNGER is at
--     the ALLIES_LEVEL moodle level or above (K.hedonics.allies); the happy side is never scaled.
--  R4 taste class: monotony also books a taste class (sweet, savoury, fatty, staple) beside the item type, weighted
--     CLASS_W (K.monotony.record's class argument; S2294 the key); a stew's class is its main ingredient's
--     (K.hedonics.dishClass).
-- The state record.hedonics = { s = the world age the current hour began, i = its slot, p = { plain kcal a slot },
-- a = { all kcal a slot } }: the slots are rotated by the online clock (s is a K.resume stamp, so the resume moves it
-- past an absence and no offline hour rolls one off), at the eat and in the writer minute; nothing is allocated after
-- the ring is made. Pure: Lua tables and numbers in and out, no Java; one statement a line for the coverage gate.
local K = NutritionRevamp.kernel
K.hedonics = {}

-- R1: the classifier's thresholds (tools/food_hedonics.py writes the table from them).
K.hedonics.PLAIN_SHARE = K.dials.get("hedonics.PLAIN_SHARE")
K.hedonics.PLAIN_KCAL = K.dials.get("hedonics.PLAIN_KCAL")
K.hedonics.PAIR_SHARE = K.dials.get("hedonics.PAIR_SHARE")
K.hedonics.FSOD_FAT = K.dials.get("hedonics.FSOD_FAT")
K.hedonics.FSOD_NA = K.dials.get("hedonics.FSOD_NA")
K.hedonics.CSOD_CARB = K.dials.get("hedonics.CSOD_CARB")
K.hedonics.CSOD_NA = K.dials.get("hedonics.CSOD_NA")
K.hedonics.FATTY_SHARE = K.dials.get("hedonics.FATTY_SHARE")

-- R1: the ring and the floor.
K.hedonics.RING_N = 24 -- the hourly slots of the 24 online hours the share reads: structural, no row needed
K.hedonics.SHARE_MIN_KCAL = K.dials.get("hedonics.SHARE_MIN_KCAL")
K.hedonics.FLOOR_KNOTS = {
    { K.dials.get("hedonics.FLOOR_KNOTS.1.1"), 0 }, -- the share under which no floor holds: the floor's foot, no row needed
    { K.dials.get("hedonics.FLOOR_KNOTS.2.1"), K.dials.get("hedonics.FLOOR_KNOTS.2.2") },
    { K.dials.get("hedonics.FLOOR_KNOTS.3.1"), K.dials.get("hedonics.FLOOR_KNOTS.3.2") },
}

-- R2: the Cooking level to the dish's relief scale.
K.hedonics.PREP_KNOTS = {
    { 0, K.dials.get("hedonics.PREP_KNOTS.1.2") }, -- Cooking level 0, the perk's foot: no row needed
    { K.dials.get("hedonics.PREP_KNOTS.2.1"), 1 }, -- the level at which vanilla's relief stands: the neutral scale, no row needed
    { 10, K.dials.get("hedonics.PREP_KNOTS.3.2") }, -- Cooking level 10, the perk's top: no row needed
}

-- R3: the hunger scale on a sad food and its moodle level.
K.hedonics.ALLIES_F = K.dials.get("hedonics.ALLIES_F")
K.hedonics.ALLIES_LEVEL = K.dials.get("hedonics.ALLIES_LEVEL")

-- R4: the taste class's portion weight.
K.hedonics.CLASS_W = K.dials.get("hedonics.CLASS_W")

-- The budget oracle's bands (tools/hedonics_budget.py reads them here): mean mood points over its 14 days.
K.hedonics.BUDGET_FAIR = K.dials.get("hedonics.BUDGET_FAIR")
K.hedonics.BUDGET_DEGEN = K.dials.get("hedonics.BUDGET_DEGEN")

-- The taste classes and their monotony keys: a key starts with "@", which no full type does ("Module.Item").
K.hedonics.CLASSES = { sweet = "@sweet", savoury = "@savoury", fatty = "@fatty", staple = "@staple" }

-- Whether a food's macro split falls in one of S2291's sodium pairings: fat over FSOD_FAT of its energy with sodium at
-- FSOD_NA % by weight or more, or carbohydrate over CSOD_CARB with sodium at CSOD_NA % or more. S2291's third pairing,
-- fat and simple sugars (each over 20 % of the energy), is never tested: the data carries no sugars, and a food at
-- PLAIN_SHARE 0.8 or more from one macro cannot meet it. isPlain asks it only under PAIR_SHARE.
function K.hedonics.paired(fatShare, carbShare, naPct)
    if fatShare > K.hedonics.FSOD_FAT and naPct >= K.hedonics.FSOD_NA then
        return true
    end
    return carbShare > K.hedonics.CSOD_CARB and naPct >= K.hedonics.CSOD_NA
end

-- Whether a food is plain energy (R1): p, c and l its protein, carbohydrate and fat grams (any basis), naPct its
-- sodium in % by weight, kcal100 its kcal a 100 g and unhappy vanilla's UnhappyChange. A food with no macro energy is
-- not plain.
function K.hedonics.isPlain(p, c, l, naPct, kcal100, unhappy)
    local ep = K.satiety.ATWATER_P * p
    local ec = K.satiety.ATWATER_C * c
    local el = K.satiety.ATWATER_F * l
    local e = ep + ec + el
    if not (e > 0) or kcal100 < K.hedonics.PLAIN_KCAL or unhappy < 0 then
        return false
    end
    local top = K.max(ep, K.max(ec, el))
    if top < K.hedonics.PLAIN_SHARE * e then
        return false
    end
    if top >= K.hedonics.PAIR_SHARE * e then
        return true
    end
    return not K.hedonics.paired(el / e, ec / e, naPct)
end

-- A food's taste class (R4), by precedence: staple (the monotony staple rule, staple true), fatty (fat at FATTY_SHARE
-- of the macro energy or more), sweet (sweet true: the generator's reading of the food type and description), else
-- savoury. p, c and l as K.hedonics.isPlain's.
function K.hedonics.tasteClass(p, c, l, staple, sweet)
    if staple == true then
        return "staple"
    end
    local el = K.satiety.ATWATER_F * l
    local e = K.satiety.ATWATER_P * p + K.satiety.ATWATER_C * c + el
    if e > 0 and el >= K.hedonics.FATTY_SHARE * e then
        return "fatty"
    end
    if sweet == true then
        return "sweet"
    end
    return "savoury"
end

-- A fresh ring at world age ageH: every slot 0, the current hour beginning at ageH in slot 1.
function K.hedonics.new(ageH)
    local h = { s = ageH, i = 1, p = {}, a = {} }
    for k = 1, K.hedonics.RING_N do
        h.p[k] = 0
        h.a[k] = 0
    end
    return h
end

-- Rotate ring h to world age ageH: each whole hour since the current one began opens the next slot, zeroed (the
-- whole ring at most), and s moves on by those hours. An age not a whole hour past s (behind it, equal or not a
-- number) leaves it. Returns h.
function K.hedonics.rotate(h, ageH)
    local d = math.floor(ageH - h.s)
    if not (d >= 1) then
        return h
    end
    local n = K.min(d, K.hedonics.RING_N)
    for k = 1, n do
        h.i = h.i % K.hedonics.RING_N + 1
        h.p[h.i] = 0
        h.a[h.i] = 0
    end
    h.s = h.s + d
    return h
end

-- One eat into ring h at world age ageH (R1): its kcal into the current hour, and into the plain sum when plain is
-- true. kcal that is not a positive finite number books nothing. Returns h.
function K.hedonics.book(h, ageH, kcal, plain)
    K.hedonics.rotate(h, ageH)
    if not K.finite(kcal) or kcal <= 0 then
        return h
    end
    h.a[h.i] = h.a[h.i] + kcal
    if plain == true then
        h.p[h.i] = h.p[h.i] + kcal
    end
    return h
end

-- The plain share of ring h: its plain kcal over its kcal, the kcal read at SHARE_MIN_KCAL at least, so a little
-- plain food in an otherwise empty day is no diet of it.
function K.hedonics.share(h)
    local p = 0
    local a = 0
    for k = 1, K.hedonics.RING_N do
        p = p + h.p[k]
        a = a + h.a[k]
    end
    return p / K.max(a, K.hedonics.SHARE_MIN_KCAL)
end

-- The plain-energy floor of a share: the FLOOR_KNOTS curve, 0 under its foot and held at its last knot.
function K.hedonics.floorOf(share)
    return K.interp(K.hedonics.FLOOR_KNOTS, share)
end

-- The writer minute's plain-energy floor (R1) at world age ageH: ring h rotated to ageH, then its share's floor. h
-- is a healed ring (K.hedonics.heal); nil reads 0.
function K.hedonics.target(h, ageH)
    if h == nil then
        return 0
    end
    K.hedonics.rotate(h, ageH)
    return K.hedonics.floorOf(K.hedonics.share(h))
end

-- The heal (the #2833 pattern): a stored ring that is not a table, whose s is not a finite number at or before ageH,
-- whose i is not a slot, or whose p or a is not a table of RING_N finite numbers at 0 or more, is reset to a fresh
-- ring at ageH. Returns the ring to keep and whether it was reset (nil reads fresh, not reset).
function K.hedonics.heal(h, ageH)
    if h == nil then
        return K.hedonics.new(ageH), false
    end
    if K.hedonics.bad(h, ageH) then
        return K.hedonics.new(ageH), true
    end
    return h, false
end

-- Whether a stored ring is corrupt (K.hedonics.heal's reading).
function K.hedonics.bad(h, ageH)
    if type(h) ~= "table" or not K.finite(h.s) or h.s > ageH then
        return true
    end
    if type(h.i) ~= "number" or h.i ~= math.floor(h.i) or h.i < 1 or h.i > K.hedonics.RING_N then
        return true
    end
    return K.hedonics.badSlots(h.p) or K.hedonics.badSlots(h.a)
end

-- Whether a slot table is not RING_N finite numbers at 0 or more.
function K.hedonics.badSlots(t)
    if type(t) ~= "table" then
        return true
    end
    for k = 1, K.hedonics.RING_N do
        if not K.finite(t[k]) or t[k] < 0 then
            return true
        end
    end
    return false
end

-- R2: a dish's UnhappyChange as the cook of Cooking level `level` makes it: its relief (a negative value) times the
-- PREP_KNOTS scale at the level (held at the curve's ends); a sad or neutral value is returned as it is.
function K.hedonics.prep(unhappy, level)
    if not (unhappy < 0) then
        return unhappy
    end
    return unhappy * K.interp(K.hedonics.PREP_KNOTS, level)
end

-- R3: a food's UnhappyChange as the eater at HUNGER `hunger` (the stat the mod writes) feels it: a sad value (over 0)
-- times ALLIES_F while hunger is over the ALLIES_LEVEL moodle threshold (K.hungerCurve.THRESHOLDS, a strict
-- greater-than, #0507); a happy or neutral value, or any value under the threshold, is returned as it is.
function K.hedonics.allies(unhappy, hunger)
    if unhappy > 0 and hunger > K.hungerCurve.THRESHOLDS[K.hedonics.ALLIES_LEVEL] then
        return unhappy * K.hedonics.ALLIES_F
    end
    return unhappy
end

-- R4: the monotony key of a taste class, or nil for a class that is not one of CLASSES (nil included).
function K.hedonics.classKey(class)
    if class == nil then
        return nil
    end
    return K.hedonics.CLASSES[class]
end

-- R4: a dish's taste class, its main ingredient's: the class of the ingredient of most kcal (the first on a tie); nil
-- for none. classes and kcals are parallel lists, one entry an ingredient.
function K.hedonics.dishClass(classes, kcals)
    local best = nil
    local top = 0
    for k = 1, #classes do
        best, top = K.hedonics.heavier(best, top, classes[k], kcals[k])
    end
    return best
end

-- One ingredient against the heaviest so far (the dishClass loop body, kept out of the loop so the line-granular
-- coverage gate sees both outcomes): the ingredient's class and kcal when its kcal is a finite number over top, else
-- best and top as they were.
function K.hedonics.heavier(best, top, class, kcal)
    if K.finite(kcal) and kcal > top then
        return class, kcal
    end
    return best, top
end
