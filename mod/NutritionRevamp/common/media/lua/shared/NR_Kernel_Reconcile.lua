-- NR_Kernel_Reconcile.lua -- the missed-intake delta (Plan 8, ruling 6; spec § 4.8, § 7 item 38). With the
-- vanilla update off (Nutrition = false, ruling T18-1) the four vanilla macro stores move only through an
-- eat or a drink, the mod's own legacy-mirror write, or another mod's action. Once a slow minute, before
-- the legacy mirror writes, the server adapter compares the stores against a baseline -- the values the
-- mod last wrote (LegacyMirror on) or last observed (LegacyMirror off) -- and a calorie rise above
-- RECONCILE_EPS is an intake the wrapped eat never saw: it lands as the four macros only, with every other
-- vector key 0 and a note that the nutrient vector is unknown. A fall is never an intake. The baseline is
-- reset to the stores after every landing and after every wrapped eat or drink (the adapter's side).
-- Pure: Lua tables in, Lua tables out, no Java. This file sorts before NR_Kernel_Vector.lua, so every
-- K.vector reference is at call time.
local K = NutritionRevamp.kernel
K.reconcile = {}

-- The calorie rise below which a store movement is not an intake.
-- gc: half a kilocalorie clears every item-pass food, the smallest RedRadish at 0.99 kcal (NR_ItemPass_Food.txt), and sits far above the float32 round trip of a store value (#3143); rests on #3143
K.reconcile.RECONCILE_EPS = 0.5

-- The note a reconciled intake carries (lastIntake.note).
K.reconcile.NOTE = "reconciled: macros only, nutrient vector unknown"

-- A number read off t[k]: 0 when t is not a table or the value is not a number.
function K.reconcile.num(t, k)
    if type(t) ~= "table" then
        return 0
    end
    local v = t[k]
    if type(v) ~= "number" then
        return 0
    end
    return v
end

-- The store minus the baseline on the four macros (calories, carbs, lipids, proteins); a nil table or value
-- reads 0. Both tables are keyed by the vector's macro names.
function K.reconcile.delta(store, baseline)
    local out = {}
    local keys = K.vector.MACROS
    for i = 1, #keys do
        local k = keys[i]
        out[k] = K.reconcile.num(store, k) - K.reconcile.num(baseline, k)
    end
    return out
end

-- The intake a delta implies: nil when the calorie rise is not above eps (a fall, no change, a NaN, or a
-- rise inside the tolerance; eps nil reads RECONCILE_EPS); else a fresh vector (K.vector.new, every key 0)
-- with the four macros set to their rises, and the note. A macro whose delta is not positive lands 0: the
-- stores move together on an eat, so a lone macro fall beside a calorie rise is another writer (with Nutrition = false there is no
-- vanilla drain), never part of the intake.
function K.reconcile.intake(delta, eps)
    local e = eps
    if e == nil then
        e = K.reconcile.RECONCILE_EPS
    end
    local c = K.reconcile.num(delta, "calories")
    if not (c > e) then
        return nil
    end
    local vec = K.vector.new()
    local keys = K.vector.MACROS
    for i = 1, #keys do
        local k = keys[i]
        local d = K.reconcile.num(delta, k)
        if d > 0 then
            vec[k] = d
        end
    end
    return vec, K.reconcile.NOTE
end

-- The baseline after a landing or a write: a copy of the store's four macros (a nil value reads 0).
function K.reconcile.baselineAfter(store)
    local out = {}
    local keys = K.vector.MACROS
    for i = 1, #keys do
        local k = keys[i]
        out[k] = K.reconcile.num(store, k)
    end
    return out
end
