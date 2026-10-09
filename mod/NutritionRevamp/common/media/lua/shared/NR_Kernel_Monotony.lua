-- NR_Kernel_Monotony.lua -- monotony at the eat (Plan 11e Task 3, ruling 11e-1; spec memo C11). Repeated eats of one
-- food type within the last 7 game days raise BOREDOM and UNHAPPINESS at the eat; nothing here reads into hunger
-- (ruling 11d-9): S1596's field rations cut intake as the sole food but not in a cafeteria setting, so the setting,
-- not the food, drives the intake fall, and the mod puts monotony into mood alone. The direction rests on S1592 (daily
-- presentation habituated faster than once-weekly: the decayed count), S1593 (acceptance and intake fell over a
-- monotony week and not over a variety week; a potato product resisted, green beans did not: the staple reduction),
-- S1594 (boredom rose and acceptance fell with repetition, most under imposed monotony and least under free choice),
-- S1595 (daily chocolate lost pleasantness over 22 days, bread and butter did not: a second staple anchor) and S1597
-- (ration bars cut intake and mood, menu fatigue implicated). S1594's free choice is the mechanic: the player who
-- chooses variety never pays it. The sizes are game choices anchored on vanilla's own per-item scale (#0042: stale
-- +10, rotten +20 on both getBoredomChange and getUnhappyChange).
-- The record, record.monotony = { t = { [fullType] = { n = count, last = ageH } } }: n is the count of recent eats of
-- the type (item-equivalents: a partial eat counts its share of the whole item) decayed to the world age `last` of
-- the type's latest eat, with a HALF_LIFE_H half-life; a type whose latest eat is more than WINDOW_H ago counts 0
-- and is pruned. The key is the item's full type, so an evolved dish (a pot of rice with anything added) is one type
-- whatever its ingredients. An eat's delta, the same on BOREDOM and UNHAPPINESS, is
-- share x min(CAP, slope x max(0, n - 1)), n the decayed count including this eat and slope SLOPE (STAPLE x SLOPE
-- for a staple): a first eat, and every part of an item eaten in parts while it is the first, adds nothing.
-- Pure: Lua tables in, no Java. Run once per eat by NR_Server_Intake (IN.atEat), never per tick.
local K = NutritionRevamp.kernel
K.monotony = {}

K.monotony.WINDOW_H = 168 -- game choice, Plan 11e (ruling 11e-1): the 7 game days a type is remembered; S1592's daily-against-weekly contrast and S1593's monotony week set the scale, not the size
K.monotony.HALF_LIFE_H = 72 -- game choice, Plan 11e (ruling 11e-1): the count's 3-day half-life inside the window, so a type left uneaten for days stops counting (S1592: spacing the presentations slows habituation)
K.monotony.SLOPE = 4.3 -- game choice, Plan 11e (ruling 11e-1): the rise per recent eat, sized so the fifth eat of one type at one a day reads 4.3 x (2^-1/3 + 2^-2/3 + 2^-1 + 2^-4/3) = 9.98 on each stat, vanilla's stale +10 (#0042); direction S1592-S1595, S1597
K.monotony.CAP = 20 -- game choice, Plan 11e (ruling 11e-1): one eat's delta never exceeds vanilla's rotten +20 (#0042) on either stat
K.monotony.STAPLE = 0.25 -- game choice, Plan 11e (ruling 11e-1): a staple's slope multiplier; S1593's potato product resisted monotony and S1595's bread and butter showed no fall in pleasantness, neither giving a size

-- The staple rule (ruling 11e-1; bread, rice, potato, pasta and oats): the script's FoodType, the food data's own
-- category (data/food-items.json food_type; the item's getFoodType at the eat), is Bread, Rice or Pasta; or the full
-- type is one of the plain potato, oat and bread types whose FoodType is absent or Vegetables, named here from the
-- 42.21 food scan's FDC descriptions (data/food-nutrients.json: Potatoes, Cereals oats, Bread, Bagels, Tortillas).
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

-- An entry's count decayed to ageH: 0 for no entry or one whose last eat is beyond the window.
function K.monotony.count(e, ageH)
    if e == nil then
        return 0
    end
    local dt = ageH - e.last
    if dt > K.monotony.WINDOW_H then
        return 0
    end
    return e.n * math.exp(-0.6931471805599453 * dt / K.monotony.HALF_LIFE_H)
end

-- A share of the whole item eaten, 0..1; nil reads a whole eat.
function K.monotony.shareOf(share)
    if share == nil then
        return 1
    end
    return K.clamp(share, 0, 1)
end

-- The BOREDOM and UNHAPPINESS an eat of typeKey at ageH adds (read before K.monotony.record books it): both the same.
function K.monotony.delta(m, typeKey, ageH, staple, share)
    local s = K.monotony.shareOf(share)
    local n = K.monotony.count(m.t[typeKey], ageH) + s
    local slope = K.monotony.SLOPE
    if staple then
        slope = slope * K.monotony.STAPLE
    end
    local d = K.min(K.monotony.CAP, slope * K.max(0, n - 1)) * s
    return d, d
end

-- Book an eat of typeKey at ageH: the count decayed to the eat plus the share, stamped ageH. Returns the entry.
function K.monotony.record(m, typeKey, ageH, share)
    local n = K.monotony.count(m.t[typeKey], ageH) + K.monotony.shareOf(share)
    local e = m.t[typeKey]
    if e == nil then
        e = {}
        m.t[typeKey] = e
    end
    e.n = n
    e.last = ageH
    return e
end

-- Drop every type whose last eat is beyond the window at ageH. Returns the number dropped.
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

-- One type into the prune's list when its last eat is beyond the window (the pairs body, kept out of the loop so
-- the line-granular coverage gate sees both outcomes).
function K.monotony.addGone(gone, k, e, ageH)
    if ageH - e.last > K.monotony.WINDOW_H then
        gone[#gone + 1] = k
    end
end

-- The heal (the #2833 pattern): a stored monotony that is not a table, whose t is not a table, or with any entry not
-- a { n, last } of finite numbers under a string key, with n negative or last ahead of ageH, is reset to a fresh
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
    return e.n < 0 or e.last > ageH
end
