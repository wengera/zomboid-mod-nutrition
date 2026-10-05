-- NR_Kernel_Vector.lua -- the nutrient vector: one flat table of named scalars, the four vanilla
-- macros plus the seed's mod-nutrient keys (spec § 4.2). The kernel iterates the vector's own key
-- list and hard-codes only the four macros, so Plan 4 adds a nutrient by adding a key here, never a
-- code path. Pure: tables in, tables out, no Java. KEYS is a Lua table this file built, so `#` on it
-- is a Lua length, never a Java list (#0940).
local K = NutritionRevamp.kernel
K.vector = {}

-- The four vanilla macros, in the engine's order. The only nutrient names the kernel hard-codes.
K.vector.MACROS = {"calories", "carbs", "lipids", "proteins"}

-- The declared key list: the macros plus the seed's worked mod-nutrient set (Plan 4 extends it).
K.vector.KEYS = {"calories", "carbs", "lipids", "proteins", "fibre", "water", "vitC", "iron", "phytate"}

-- The declared key list a reader iterates.
function K.vector.keys()
    return K.vector.KEYS
end

-- A fresh vector with every declared key set to 0. Slow-clock capture-path code (not a per-tick
-- fast region), so the `for` over this file's own KEYS table is allowed.
function K.vector.new()
    local v = {}
    for i = 1, #K.vector.KEYS do
        v[K.vector.KEYS[i]] = 0
    end
    return v
end

-- Accumulate src into dst over every declared key, scaled, and return dst (the same object, no
-- allocation): dst[k] = dst[k] + (src[k] or 0) * scale. A missing src key counts as 0.
function K.vector.add(dst, src, scale)
    for i = 1, #K.vector.KEYS do
        local k = K.vector.KEYS[i]
        dst[k] = dst[k] + (src[k] or 0) * scale
    end
    return dst
end
