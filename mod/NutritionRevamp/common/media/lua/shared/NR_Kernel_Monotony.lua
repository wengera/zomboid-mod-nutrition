-- NR_Kernel_Monotony.lua -- monotony as a self-releasing floor (Plan 11e Task 3, ruling 11e-1; Plan 11f Task 9b,
-- rulings T9-1 and T9-3; spec memo C11). Repeated eats of one food type within the last 7 game days hold a floor
-- under BOREDOM and UNHAPPINESS; nothing here reads into hunger (ruling 11d-9): S1596's field rations cut intake as
-- the sole food but not in a cafeteria setting, so the setting, not the food, drives the intake fall, and the mod puts
-- monotony into mood alone. The direction rests on S1592 (daily presentation habituated faster than once-weekly: the
-- decayed count), S1593 (acceptance and intake fell over a monotony week and not over a variety week; a potato product
-- resisted, green beans did not: the staple reduction), S1594 (boredom rose and acceptance fell with repetition, most
-- under imposed monotony and least under free choice), S1595 (daily chocolate lost pleasantness over 22 days, bread and
-- butter did not: a second staple anchor) and S1597 (ration bars cut intake and mood, menu fatigue implicated). S1594's
-- free choice is the mechanic: the player who chooses variety never pays it. The sizes are game choices anchored on
-- vanilla's own per-item scale (#0042: stale +10, rotten +20 on both getBoredomChange and getUnhappyChange).
-- The unit is a meal-sized portion (ruling T3-3; the studies count presentations of a served portion, S1592-S1595): an
-- eat weighs w = min(1, kcal / MEAL_KCAL); an eat with no energy weighs 0 and is not booked. The record,
-- record.monotony = { t = { [fullType] = { n = count, last = ageH, s = staple } } }: n is the type's recent portions
-- decayed to its latest eat's world age `last` with a HALF_LIFE_H half-life, s true for a staple; a type whose latest
-- eat is more than WINDOW_H ago counts 0 and is pruned once its count is one portion or less (its level already 0, so no step). The key is the item's full type, so an evolved dish is one type.
-- A type's level is f x min(CAP, SLOPE x max(0, n - 1)), n its count decayed to the minute and f STAPLE for a staple
-- (1 otherwise), and the target is the most repeated type's level (K.monotony.target): UNHAPPINESS's, and BOREDOM's
-- held under BORED_MAX. Nothing is added at the eat (ruling T9-1): the writer raises the stats toward the target once a
-- minute and lowers them by the target's fall (K.hybrid.write, #3119), so variety lets the counts decay and releases it.
-- Pure: Lua tables in, no Java. K.monotony.record runs once per eat (NR_Server_Intake IN.atEat), K.monotony.target once
-- per writer minute (NR_Server_Writer W.monotony), never per tick.
local K = NutritionRevamp.kernel
K.monotony = {}

K.monotony.WINDOW_H = 168 -- game choice, Plan 11e (ruling 11e-1): the 7 game days a type is remembered, measured from the type's latest eat; a type eaten daily keeps its decayed older eats (ruling T3-4); S1592's daily-against-weekly contrast and S1593's monotony week set the scale, not the size; since Plan 11f Task 9b fix 1 a type past it is forgotten only once its decayed count is one portion or less, where its level is already 0, so the window bounds the record without a step in the floor
K.monotony.HALF_LIFE_H = 72 -- game choice, Plan 11e (ruling 11e-1): the count's 3-day half-life inside the window, so a type left uneaten for days stops counting (S1592: spacing the presentations slows habituation)
K.monotony.SLOPE = 4.3 -- game choice, Plan 11e (ruling 11e-1): the level per recent portion past the first, sized so right after the fifth meal-sized eat of one type at one a day the level reads 4.3 x (2^-1/3 + 2^-2/3 + 2^-1 + 2^-4/3) = 9.98 on each stat, vanilla's stale +10 (#0042); direction S1592-S1595, S1597
K.monotony.CAP = 30 -- game choice, Plan 11e (ruling 11e-1), a level since Plan 11f (ruling T9-1), 30 since Plan 11f Task 9b fix 1 (Angus 2026-10-11, level-1 moodles; S1592-S1597 give direction, not size; thresholds #2369): a type's level, and so the target, never exceeds 30, so a one-food diet at three portions a day holds 30 from day 5, above UNHAPPY level 1 (20) by 10 and BORED level 1 (25) by 5 and under BORED level 2 (50); Moodle.Update sets a level only when the stat is strictly above its threshold (fcmpl/ifle: BORED @856-@873 L219-L220, UNHAPPY @967-@984 L237-L238 on 42.21); vanilla's stale +10 (#0042) still sizes SLOPE but no longer binds the cap, which was vanilla's rotten +20 (#0042) before the fix
K.monotony.STAPLE = 0.25 -- game choice, Plan 11e (ruling 11e-1): a staple's level multiplier, outside the cap (Plan 11f Task 9b); S1593's potato product resisted monotony and S1595's bread and butter showed no fall in pleasantness, neither giving a size
K.monotony.MEAL_KCAL = 400 -- game choice, Plan 11e (ruling T3-3); the studies' unit is a served portion (S1592-S1595): the landed energy of one meal-sized portion, the weight-1 eat

-- The staple rule (ruling 11e-1; bread, rice, potato, pasta and oats): the script's FoodType, the food data's own
-- category (data/food-items.json food_type; the item's getFoodType at the eat), is Bread, Rice or Pasta; or the full
-- type is one of the plain potato, oat, bread and pasta types whose FoodType is absent, Vegetables or NoExplicit,
-- named here from the 42.21 food scan's FDC descriptions (data/food-nutrients.json: Potatoes, Cereals oats, Bread,
-- Bagels, Tortillas, Cornbread) and its plain-pasta pots (ruling T3-5).
K.monotony.STAPLE_FOOD_TYPES = { Bread = true, Rice = true, Pasta = true }
K.monotony.STAPLE_TYPES = {
    ["Base.Potato"] = true,
    ["Base.CannedPotato"] = true,
    ["Base.CannedPotato2"] = true,
    ["Base.CannedPotatoOpen"] = true,
    ["Base.CannedPotato_Open"] = true,
    ["Base.OatsRaw"] = true,
    ["Base.Oatmeal"] = true,
    ["Base.Toast"] = true,
    ["Base.BagelPlain"] = true,
    ["Base.BagelPoppy"] = true,
    ["Base.BagelSesame"] = true,
    ["Base.BunsHamburger"] = true,
    ["Base.BunsHotdog"] = true,
    ["Base.Tortilla"] = true,
    ["Base.Cornbread"] = true,
    ["Base.WaterPotPasta"] = true,
    ["Base.WaterPotForgedPasta"] = true,
    ["Base.WaterSaucepanPasta"] = true,
    ["Base.WaterSaucepanPastaCopper"] = true,
}

function K.monotony.new()
    return { t = {} }
end

-- Whether a type is a staple (the rule above): its FoodType, else its full type.
function K.monotony.isStaple(fullType, foodType)
    if foodType ~= nil and K.monotony.STAPLE_FOOD_TYPES[foodType] == true then
        return true
    end
    return K.monotony.STAPLE_TYPES[fullType] == true
end

-- An entry's count decayed to ageH: 0 for no entry, or past the window once it is one portion or less (K.monotony.faded).
function K.monotony.count(e, ageH)
    if e == nil then
        return 0
    end
    local dt = ageH - e.last
    if dt > K.monotony.WINDOW_H then
        return K.monotony.faded(e, dt)
    end
    return e.n * math.exp(-0.6931471805599453 * dt / K.monotony.HALF_LIFE_H)
end

-- An eat's portion weight (ruling T3-3): its landed kcal over MEAL_KCAL, at most 1; no energy, or energy that is not
-- a finite number, weighs 0.
function K.monotony.weightOf(kcal)
    if not K.vector.finite(kcal) or kcal <= 0 then
        return 0
    end
    return K.min(1, kcal / K.monotony.MEAL_KCAL)
end

-- A portion weight held to 0..1; nil reads one full portion.
function K.monotony.portion(w)
    if w == nil then
        return 1
    end
    return K.clamp(w, 0, 1)
end

-- Book an eat of typeKey at ageH weighing w: the count decayed to the eat plus w, stamped ageH, and marked a staple
-- when staple is true (the latest eat's reading stands; s is left nil otherwise). Returns the entry.
function K.monotony.record(m, typeKey, ageH, w, staple)
    local n = K.monotony.count(m.t[typeKey], ageH) + K.monotony.portion(w)
    local e = m.t[typeKey]
    if e == nil then
        e = {}
        m.t[typeKey] = e
    end
    e.n = n
    e.last = ageH
    e.s = nil
    if staple == true then
        e.s = true
    end
    return e
end

-- Drop every type past the window whose count is one portion or less at ageH. Returns the number dropped.
function K.monotony.prune(m, ageH)
    local gone = {}
    for k, e in pairs(m.t) do
        K.monotony.addGone(gone, k, e, ageH)
    end
    for i = 1, #gone do
        m.t[gone[i]] = nil
    end
    return #gone
end

-- One type into the prune's list when it is past the window and counts 0 (the pairs body, kept out of the loop so
-- the line-granular coverage gate sees both outcomes); a heavier type is kept until its level has faded to 0.
function K.monotony.addGone(gone, k, e, ageH)
    if ageH - e.last > K.monotony.WINDOW_H and K.monotony.count(e, ageH) <= 0 then
        gone[#gone + 1] = k
    end
end

-- The heal (the #2833 pattern): a stored monotony that is not a table, whose t is not a table, or with any entry not
-- a { n, last } of finite numbers with an absent or boolean s under a string key, with n negative or last ahead of
-- ageH, is reset to a fresh
-- table. Returns the table to keep and whether it was reset (nil reads fresh, not reset).
function K.monotony.heal(m, ageH)
    if m == nil then
        return K.monotony.new(), false
    end
    if type(m) ~= "table" or type(m.t) ~= "table" then
        return K.monotony.new(), true
    end
    local bad = false
    for k, e in pairs(m.t) do
        bad = K.monotony.badEntry(bad, k, e, ageH)
    end
    if bad then
        return K.monotony.new(), true
    end
    return m, false
end

-- Whether a heal has found a bad entry so far, this one included.
function K.monotony.badEntry(bad, k, e, ageH)
    if bad then
        return true
    end
    if type(k) ~= "string" or type(e) ~= "table" then
        return true
    end
    if not K.vector.finite(e.n) or not K.vector.finite(e.last) then
        return true
    end
    if e.s ~= nil and type(e.s) ~= "boolean" then
        return true
    end
    return e.n < 0 or e.last > ageH
end

-- Plan 11f Task 9b (rulings T9-1, T9-3): the floor. Appended so no line above moves.
K.monotony.BORED_MAX = 49 -- game choice, Plan 11f (ruling T9-3): the BOREDOM target is held one under the BORED level-2 step 50 (#2369; MoodleStat.<clinit> @118-@133 L16 on 42.21), because vanilla adds UNHAPPINESS while the BORED moodle is above level 1 (BodyDamage.UpdateBoredom @510-@575 L2042-L2043 on 42.21), so monotony alone never drives that term; vanilla also resets BOREDOM while PANIC > 5 (UpdateBoredom @482-@509, #3015), the mod's own dehydration PANIC floor included (ruling T9-3), so the BOREDOM floor is wiped while the character panics

-- A type's level at ageH: f x min(CAP, SLOPE x max(0, n - 1)), n the count decayed to ageH (0 past the window) and f
-- STAPLE for an entry marked a staple, else 1.
function K.monotony.level(e, ageH)
    if type(e) ~= "table" then
        return 0
    end
    local n = K.monotony.count(e, ageH)
    local f = 1
    if e.s == true then
        f = K.monotony.STAPLE
    end
    return f * K.min(K.monotony.CAP, K.monotony.SLOPE * K.max(0, n - 1))
end

-- The floor's targets at ageH, UNHAPPINESS's and BOREDOM's: the most repeated type's level (the maximum over the
-- types, so a rotation of k foods reads one food's level at a k-th of the eats, and a varied diet's counts decay
-- under one portion and release it), BOREDOM's held at BORED_MAX. m is a healed record (K.monotony.heal).
function K.monotony.target(m, ageH)
    local u = 0
    for k, e in pairs(m.t) do
        u = K.max(u, K.monotony.level(e, ageH))
    end
    return u, K.min(K.monotony.BORED_MAX, u)
end

-- Plan 11f Task 9b fix 1: the count of an entry past the window, dt hours after its last eat: its decayed count while
-- above one portion, else 0. Its level, SLOPE x max(0, n - 1), falls to 0 continuously as n reaches one portion, so the
-- window no longer drops the floor in one minute; the entry is pruned only after (K.monotony.addGone).
function K.monotony.faded(e, dt)
    local n = e.n * math.exp(-0.6931471805599453 * dt / K.monotony.HALF_LIFE_H)
    if n <= 1 then
        return 0
    end
    return n
end

-- Skip gapH game hours the adapter does not integrate (K.acute.skipRecord, an offline gap after fromH): every entry
-- stamped by fromH moves forward by the gap, so its count decays over no offline time; one stamped after fromH (an eat
-- at the return) stays. A monotony that is not a table, and an entry that is not one or whose stamp is not a finite
-- number, are left for the heal. Returns m.
function K.monotony.skip(m, gapH, fromH)
    if type(m) ~= "table" or type(m.t) ~= "table" then
        return m
    end
    for _, e in pairs(m.t) do
        K.monotony.skipOne(e, gapH, fromH)
    end
    return m
end

-- One entry of the skip (the pairs body, kept out of the loop so the line-granular coverage gate sees both outcomes).
function K.monotony.skipOne(e, gapH, fromH)
    if type(e) == "table" and K.vector.finite(e.last) and e.last <= fromH then
        e.last = e.last + gapH
    end
end
