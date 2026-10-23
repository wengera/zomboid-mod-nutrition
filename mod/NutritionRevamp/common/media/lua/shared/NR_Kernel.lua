-- NR_Kernel.lua -- the pure kernel's namespace and shared helpers: no Java object crosses into a kernel function, and
-- every function is a field of NutritionRevamp.kernel so the coverage gate can enumerate it.
local K = NutritionRevamp.kernel
K.version = NutritionRevamp.version

-- The engine clamps every Stats write too (#2208). A NaN passes through: a caller that must not write one tests K.finite.
function K.clamp(x, lo, hi)
    if x < lo then
        return lo
    end
    if x > hi then
        return hi
    end
    return x
end

-- Without math.*, which the fast-path lint forbids per tick.
function K.max(a, b)
    if a > b then
        return a
    end
    return b
end

function K.min(a, b)
    if a < b then
        return a
    end
    return b
end

-- False for NaN, an infinity and a non-number; NR.finite is the adapters' name for it.
K.finite = NutritionRevamp.finite

-- kn is { {x, y}, ... }, x ascending; extend reads the end segments past the end knots, else the ends read flat.
function K.interp(kn, x, extend)
    local n = #kn -- a Lua table the kernel built, so # is defined on it
    if extend ~= true then
        x = K.clamp(x, kn[1][1], kn[n][1])
    end
    local seg = n
    for i = n, 2, -1 do
        if x <= kn[i][1] then
            seg = i
        end
    end
    local x0 = kn[seg - 1][1]
    local y0 = kn[seg - 1][2]
    return y0 + (kn[seg][2] - y0) * (x - x0) / (kn[seg][1] - x0)
end

-- One sandbox leaf: a wrong type, a NaN or an out-of-range number reads the default, or with clampIt (a double
-- option is continuous, so its nearest bound is the intent) is clamped. The one clamp rule of every option read.
function K.readLeaf(tbl, key, default, lo, hi, clampIt)
    if tbl == nil then
        return default
    end
    local v = tbl[key]
    if type(default) == "boolean" then
        if type(v) == "boolean" then
            return v
        end
        return default
    end
    if type(v) ~= "number" or v ~= v then
        return default
    end
    if clampIt then
        return K.max(lo, K.min(hi, v))
    end
    if v < lo or v > hi then
        return default
    end
    return v
end

-- The one username hash the push phase and the save phase both read, so the two stay half a gap apart.
function K.nameHash(username)
    local h = 0
    for i = 1, string.len(username) do
        h = (h * 31 + string.byte(username, i)) % 1000003
    end
    return h
end

K.HEX = "0123456789abcdef" -- the digit lookup: %x on a float raises on Kahlua

function K.hexDigits(n, width)
    local d = 1
    for i = 2, width do
        d = d * 16
    end
    local out = ""
    for i = 1, width do
        local q = math.floor(n / d) % 16 + 1
        out = out .. string.sub(K.HEX, q, q)
        d = d / 16
    end
    return out
end

-- The dials resolver lives here because this file loads before every other kernel file: a kernel resolves its dials
-- into its own fields once at load, so no lookup runs per tick (Rule 6) and the fields stay patchable (the fit tools).
K.dials = {}
K.dials.DEPTH = 8 -- no row needed: the most `same` links a dial may follow before it reads as a cycle

-- An unknown id, or a host that never loaded the registry, raises, so a typo fails at load.
function K.dials.row(id)
    local data = NutritionRevamp.data
    local row = nil
    if data ~= nil and data.dials ~= nil then
        row = data.dials[id]
    end
    if row == nil then
        error("NutritionRevamp: no dial " .. tostring(id))
    end
    return row
end

-- A `same` row resolves to its target, a chain past DEPTH raises; a table value is the registry's own, never written.
function K.dials.get(id)
    local row = K.dials.row(id)
    local hops = 0
    while row.same ~= nil do
        hops = hops + 1
        if hops > K.dials.DEPTH then
            error("NutritionRevamp: dial cycle at " .. tostring(id))
        end
        row = K.dials.row(row.same)
    end
    return row.value
end

-- The one shared height, fixed and sex-neutral, read by every BMI and FFMI; resolved once K.dials.get is defined.
K.HEIGHT_M = K.dials.get("core.HEIGHT_M")
