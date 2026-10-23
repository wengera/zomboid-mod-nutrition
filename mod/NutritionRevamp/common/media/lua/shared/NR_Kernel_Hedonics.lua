-- NR_Kernel_Hedonics.lua: food hedonics, four rules on top of vanilla's UnhappyChange and BoredomChange (spec
-- docs/superpowers/specs/2026-10-21-dials-and-hedonics-design.md@program-record-v19 section B.2). Pure, no Java; runs
-- at an eat, an ingredient add or the writer minute, never per tick (Rule 6); the adapters are NR_Server_Hedonics's.
--  R1 plain energy: an energy-dense food mostly from one macro, no vanilla treat and in none of S2291's sodium pairings
--     (unless one macro gives PAIR_SHARE or more: salted butter is plain) books into a RING_N-hour ring, whose plain
--     share drives an UNHAPPINESS floor composed with monotony's self-releasing one. An ingredient add never books.
--     The table is generated (tools/food_hedonics.py) through isPlain, so generator and budget oracle agree.
--  R2 preparation: a dish's relief is scaled by the cook's Cooking level; its sad side never is.
--  R3 alliesthesia: a sad food is scaled by ALLIES_F at the ALLIES_LEVEL hunger moodle or above.
--  R4 taste class: monotony also books a class (sweet, savoury, fatty, staple); a stew's is its main ingredient's.
-- record.hedonics = { s, i, p, a }: s is a K.resume stamp, so no offline hour rolls a slot off;
-- nothing is allocated after the ring is made. One statement a line for the coverage gate.
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

K.hedonics.RING_N = 24 -- the hourly slots of the 24 online hours the share reads: structural, no row needed
K.hedonics.SHARE_MIN_KCAL = K.dials.get("hedonics.SHARE_MIN_KCAL")
K.hedonics.FLOOR_KNOTS = {
    { K.dials.get("hedonics.FLOOR_KNOTS.1.1"), 0 }, -- the share under which no floor holds: the floor's foot, no row needed
    { K.dials.get("hedonics.FLOOR_KNOTS.2.1"), K.dials.get("hedonics.FLOOR_KNOTS.2.2") },
    { K.dials.get("hedonics.FLOOR_KNOTS.3.1"), K.dials.get("hedonics.FLOOR_KNOTS.3.2") },
}

K.hedonics.PREP_KNOTS = {
    { 0, K.dials.get("hedonics.PREP_KNOTS.1.2") }, -- Cooking level 0, the perk's foot: no row needed
    { K.dials.get("hedonics.PREP_KNOTS.2.1"), 1 }, -- the level at which vanilla's relief stands: the neutral scale, no row needed
    { 10, K.dials.get("hedonics.PREP_KNOTS.3.2") }, -- Cooking level 10, the perk's top: no row needed
}

K.hedonics.ALLIES_F = K.dials.get("hedonics.ALLIES_F")
K.hedonics.ALLIES_LEVEL = K.dials.get("hedonics.ALLIES_LEVEL")

K.hedonics.CLASS_W = K.dials.get("hedonics.CLASS_W")

-- The budget oracle's bands (tools/hedonics_budget.py reads them here): mean mood points over its 14 days.
K.hedonics.BUDGET_FAIR = K.dials.get("hedonics.BUDGET_FAIR")
K.hedonics.BUDGET_DEGEN = K.dials.get("hedonics.BUDGET_DEGEN")

-- The taste classes and their monotony keys: a key starts with "@", which no full type does ("Module.Item").
K.hedonics.CLASSES = { sweet = "@sweet", savoury = "@savoury", fatty = "@fatty", staple = "@staple" }

-- S2291's sodium pairings (fat with sodium, carbohydrate with sodium). Its third, fat with sugars, is never tested:
-- the data carries no sugars, and isPlain asks only under PAIR_SHARE, where it cannot be met.
function K.hedonics.paired(fatShare, carbShare, naPct)
    if fatShare > K.hedonics.FSOD_FAT and naPct >= K.hedonics.FSOD_NA then
        return true
    end
    return carbShare > K.hedonics.CSOD_CARB and naPct >= K.hedonics.CSOD_NA
end

-- p, c, l in grams (any basis), naPct sodium % by weight; a food with no macro energy is not plain.
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

-- Precedence: staple, fatty (FATTY_SHARE of the energy), sweet (the generator's reading of type and description),
-- else savoury.
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

function K.hedonics.new(ageH)
    local h = { s = ageH, i = 1, p = {}, a = {} }
    for k = 1, K.hedonics.RING_N do
        h.p[k] = 0
        h.a[k] = 0
    end
    return h
end

-- Each whole hour since s opens the next slot, zeroed; an age not a whole hour past s leaves the ring.
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

-- kcal that is not a positive finite number books nothing.
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

-- The kcal read at SHARE_MIN_KCAL at least, so a little plain food in an empty day is no diet of it.
function K.hedonics.share(h)
    local p = 0
    local a = 0
    for k = 1, K.hedonics.RING_N do
        p = p + h.p[k]
        a = a + h.a[k]
    end
    return p / K.max(a, K.hedonics.SHARE_MIN_KCAL)
end

function K.hedonics.floorOf(share)
    return K.interp(K.hedonics.FLOOR_KNOTS, share)
end

-- h is a healed ring (K.hedonics.heal); nil reads 0.
function K.hedonics.target(h, ageH)
    if h == nil then
        return 0
    end
    K.hedonics.rotate(h, ageH)
    return K.hedonics.floorOf(K.hedonics.share(h))
end

-- The #2833 heal: a corrupt ring resets to a fresh one; returns the ring and whether it was reset.
function K.hedonics.heal(h, ageH)
    if h == nil then
        return K.hedonics.new(ageH), false
    end
    if K.hedonics.bad(h, ageH) then
        return K.hedonics.new(ageH), true
    end
    return h, false
end

function K.hedonics.bad(h, ageH)
    if type(h) ~= "table" or not K.finite(h.s) or h.s > ageH then
        return true
    end
    if type(h.i) ~= "number" or h.i ~= math.floor(h.i) or h.i < 1 or h.i > K.hedonics.RING_N then
        return true
    end
    return K.hedonics.badSlots(h.p) or K.hedonics.badSlots(h.a)
end

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

-- R2: relief (a negative value) times the PREP_KNOTS scale; a sad or neutral value is returned as it is.
function K.hedonics.prep(unhappy, level)
    if not (unhappy < 0) then
        return unhappy
    end
    return unhappy * K.hedonics.prepScale(level)
end

-- R3: the threshold is a strict greater-than (#0507); a happy or neutral value is returned as it is.
function K.hedonics.allies(unhappy, hunger)
    if unhappy > 0 and hunger > K.hungerCurve.THRESHOLDS[K.hedonics.ALLIES_LEVEL] then
        return unhappy * K.hedonics.ALLIES_F
    end
    return unhappy
end

function K.hedonics.classKey(class)
    if class == nil then
        return nil
    end
    return K.hedonics.CLASSES[class]
end

-- R4: classes and kcals are parallel lists; the ingredient of most kcal wins, the first on a tie.
function K.hedonics.dishClass(classes, kcals)
    local best = nil
    local top = 0
    for k = 1, #classes do
        best, top = K.hedonics.heavier(best, top, classes[k], kcals[k])
    end
    return best
end

-- The loop body, out of the loop so the line-granular coverage gate sees both outcomes.
function K.hedonics.heavier(best, top, class, kcal)
    if K.finite(kcal) and kcal > top then
        return class, kcal
    end
    return best, top
end

-- R2: also the stamp the add-ingredient seat keeps on a dish beside the relief it wrote.
function K.hedonics.prepScale(level)
    return K.interp(K.hedonics.PREP_KNOTS, level)
end

-- R2: the vanilla value under a seat-written relief. Vanilla's next add starts from it, so a dish of many adds is
-- scaled once, never compounded.
function K.hedonics.unprep(stored, scale)
    if not (stored < 0) or not K.finite(scale) or not (scale > 0) then
        return stored
    end
    return stored / scale
end

-- R3: the field the eat seat writes before vanilla's eat, so the read-time value vanilla applies (field plus state
-- terms) reads K.hedonics.allies(unhappy, hunger).
function K.hedonics.alliesField(field, unhappy, hunger)
    return field - (unhappy - K.hedonics.allies(unhappy, hunger))
end

-- R3: the remainder's field as if R3 never ran: vanilla scaled the written field (multiplyFoodValues), so the same
-- ratio on the original, or q when the written field was 0. nil for a finished item, which reads NaN (#2832).
function K.hedonics.alliesRestore(field, written, after, q)
    if not K.finite(after) then
        return nil
    end
    if written ~= 0 then
        return field * (after / written)
    end
    if not K.finite(q) then
        return nil
    end
    return field * q
end
