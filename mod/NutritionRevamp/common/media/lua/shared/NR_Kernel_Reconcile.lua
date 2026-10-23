-- NR_Kernel_Reconcile.lua -- the missed-intake delta. With Nutrition = false the vanilla macro stores move only through
-- an eat, the mod's mirror write or another mod, so a calorie rise over the baseline is an intake the wrapped eat never
-- saw: it lands as the four macros only. A fall is never an intake. K.vector is read at call time.
local K = NutritionRevamp.kernel
K.reconcile = {}

-- gc: half a kcal clears the smallest item-pass food (0.99 kcal) and sits far above the float32 round trip (#3143)
K.reconcile.RECONCILE_EPS = 0.5

K.reconcile.NOTE = "reconciled: macros only, nutrient vector unknown"

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

-- A nil table or value reads 0.
function K.reconcile.delta(store, baseline)
    local out = {}
    local keys = K.vector.MACROS
    for i = 1, #keys do
        local k = keys[i]
        out[k] = K.reconcile.num(store, k) - K.reconcile.num(baseline, k)
    end
    return out
end

-- nil when the calorie rise is not above eps. A macro whose delta is not positive lands 0: the stores move together on
-- an eat, so a lone fall beside a rise is another writer, never part of the intake.
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

-- A nil value reads 0.
function K.reconcile.baselineAfter(store)
    local out = {}
    local keys = K.vector.MACROS
    for i = 1, #keys do
        local k = keys[i]
        out[k] = K.reconcile.num(store, k)
    end
    return out
end
