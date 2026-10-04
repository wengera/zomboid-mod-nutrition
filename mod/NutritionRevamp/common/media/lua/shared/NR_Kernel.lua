-- NR_Kernel.lua -- the pure kernel's namespace and its shared helpers. Tables in, tables out,
-- no Java object ever crosses into a kernel function (spec § 4.1); every function here is a
-- field of NutritionRevamp.kernel so the coverage gate can enumerate it (Plan 1 ruling 3).
local K = NutritionRevamp.kernel
K.version = NutritionRevamp.version

-- Clamp x into [lo, hi]. Every Stats write passes the stat's own clamp in Java (#2208); the
-- kernel clamps too so a delta it hands out never asks the engine to clamp.
function K.clamp(x, lo, hi)
    if x < lo then return lo end
    if x > hi then return hi end
    return x
end

-- max(a, b) and min(a, b) without math.*, which the fast-path lint forbids per tick.
function K.max(a, b)
    if a > b then return a end
    return b
end

function K.min(a, b)
    if a < b then return a end
    return b
end
