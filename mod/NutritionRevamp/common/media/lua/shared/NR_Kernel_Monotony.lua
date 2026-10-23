-- NR_Kernel_Monotony.lua -- monotony as a self-releasing floor under BOREDOM and UNHAPPINESS, never hunger: the setting,
-- not the food, drives the intake fall (S1596), so monotony goes into mood alone; the direction rests on S1592, S1593,
-- S1595 and S1597. The player's free choice is the mechanic: one who chooses variety never pays it (S1594). BOREDOM's
-- floor is wiped while PANIC > 5 (ruling T9-3: vanilla resets it). The unit is a meal-sized portion; an eat with no energy is not
-- booked. The key is the item's full type, so an evolved dish is one type. Nothing is added at the eat: the writer
-- moves the stats toward the target once a minute (K.hybrid.write, #3119), so variety decays the counts and releases it.
-- K.monotony.record runs once per eat, K.monotony.target once per writer minute, never per tick.
local K = NutritionRevamp.kernel
K.monotony = {}

K.monotony.WINDOW_H = K.dials.get("monotony.WINDOW_H")
K.monotony.HALF_LIFE_H = K.dials.get("monotony.HALF_LIFE_H")
K.monotony.SLOPE = K.dials.get("monotony.SLOPE")
K.monotony.CAP = K.dials.get("monotony.CAP")
K.monotony.STAPLE = K.dials.get("monotony.STAPLE")
K.monotony.MEAL_KCAL = K.dials.get("monotony.MEAL_KCAL")

-- Staples resist monotony (S1593): FoodType Bread, Rice or Pasta, or the plain types whose FoodType is absent,
-- named from the 42.21 food scan.
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

function K.monotony.isStaple(fullType, foodType)
    if foodType ~= nil and K.monotony.STAPLE_FOOD_TYPES[foodType] == true then
        return true
    end
    return K.monotony.STAPLE_TYPES[fullType] == true
end

-- Past the window, an entry counts only while above one portion (K.monotony.faded).
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

-- No energy, or energy that is not finite, weighs 0.
function K.monotony.weightOf(kcal)
    if not K.finite(kcal) or kcal <= 0 then
        return 0
    end
    return K.min(1, kcal / K.monotony.MEAL_KCAL)
end

function K.monotony.portion(w)
    if w == nil then
        return 1
    end
    return K.clamp(w, 0, 1)
end

-- A rotation of foods of one class holds the class's level where each food's own has faded (S2294), so the eat is also
-- booked under its taste class at CLASS_W; the class key is one more type to the target, decay, prune and heal.
function K.monotony.record(m, typeKey, ageH, w, staple, class)
    local p = K.monotony.portion(w)
    local e = K.monotony.book(m, typeKey, ageH, p, staple)
    local key = K.hedonics.classKey(class)
    if key ~= nil then
        K.monotony.book(m, key, ageH, p * K.hedonics.CLASS_W, class == "staple")
    end
    return e
end

-- The latest eat's staple reading stands; s is left nil otherwise.
function K.monotony.book(m, typeKey, ageH, p, staple)
    local n = K.monotony.count(m.t[typeKey], ageH) + p
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

-- (the pairs body, kept out of the loop for the coverage gate); a heavier type is kept until its level has faded to 0.
function K.monotony.addGone(gone, k, e, ageH)
    if ageH - e.last > K.monotony.WINDOW_H and K.monotony.count(e, ageH) <= 0 then
        gone[#gone + 1] = k
    end
end

-- The #2833 heal: any malformed entry resets the whole table to fresh. nil reads fresh, not reset.
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

function K.monotony.badEntry(bad, k, e, ageH)
    if bad then
        return true
    end
    if type(k) ~= "string" or type(e) ~= "table" then
        return true
    end
    if not K.finite(e.n) or not K.finite(e.last) then
        return true
    end
    if e.s ~= nil and type(e.s) ~= "boolean" then
        return true
    end
    return e.n < 0 or e.last > ageH
end

K.monotony.BORED_MAX = K.dials.get("monotony.BORED_MAX")

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

-- The maximum over the types, so a rotation of k foods reads one food's level at a k-th of the eats.
function K.monotony.target(m, ageH)
    local u = 0
    for k, e in pairs(m.t) do
        u = K.max(u, K.monotony.level(e, ageH))
    end
    return u, K.min(K.monotony.BORED_MAX, u)
end

-- The dead zone, as the hunger curve's: a held target stops the moodle blinking; a rise is never held. The BOREDOM
-- target stops at BORED_MAX 49, under BORED level 2 (#2369).
K.monotony.DEAD_ZONE = K.dials.get("monotony.DEAD_ZONE")
K.monotony.HOLD_EPS = K.dials.get("monotony.HOLD_EPS")
K.monotony.UNHAPPY_AT = { 20, 45 } -- VANILLA #2369 (UNHAPPY levels 1 and 2)
K.monotony.BORED_AT = { 25 } -- VANILLA #2369 (BORED level 1)

-- A prev or v that is not a finite number returns v.
function K.monotony.hold(v, prev, at)
    if not K.finite(v) or not K.finite(prev) then
        return v
    end
    -- at is one of this file's Lua arrays, so # is its length
    for i = 1, #at do
        local t = at[i]
        if prev > t and v <= t and v > t - K.monotony.DEAD_ZONE * t then
            return K.min(prev, t + K.monotony.HOLD_EPS)
        end
    end
    return v
end

-- The level falls to 0 continuously as n reaches one portion, so the window never drops the floor in one minute.
function K.monotony.faded(e, dt)
    local n = e.n * math.exp(-0.6931471805599453 * dt / K.monotony.HALF_LIFE_H)
    if n <= 1 then
        return 0
    end
    return n
end
