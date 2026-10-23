-- NR_Kernel.lua -- the pure kernel's namespace and its shared helpers. Tables in, tables out,
-- no Java object ever crosses into a kernel function (spec § 4.1); every function here is a
-- field of NutritionRevamp.kernel so the coverage gate can enumerate it.
local K = NutritionRevamp.kernel
K.version = NutritionRevamp.version

-- Clamp x into [lo, hi]. Every Stats write passes the stat's own clamp in Java (#2208); the
-- kernel clamps too so a delta it hands out never asks the engine to clamp. A NaN passes through unchanged (both
-- comparisons are false): the clamp does not sanitise, so a caller that must not write a NaN tests K.finite first.
function K.clamp(x, lo, hi)
    if x < lo then
        return lo
    end
    if x > hi then
        return hi
    end
    return x
end

-- max(a, b) and min(a, b) without math.*, which the fast-path lint forbids per tick.
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

-- Whether x is a finite number: false for NaN, for an infinity and for any non-number. The one finiteness test,
-- NR_Core's NR.finite (the adapters' name for the same function).
K.finite = NutritionRevamp.finite

-- The piecewise-linear reading at x of knots kn ({ {x, y}, ... }, x ascending, at least two): the segment whose upper
-- knot is the first at or above x. extend true extends the end segments past the end knots; otherwise x is clamped
-- to [first, last] and the ends read flat.
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

-- One sandbox leaf from the table tbl at key: a boolean when the default is a boolean, else a number in [lo, hi]. Any
-- other type reads the default; so does a NaN; so does an out-of-range number, or with clampIt (a double option's
-- value is continuous, so its nearest bound is the operator's intent) the number is clamped to [lo, hi]. The one
-- clamp rule of every option read (Plan 13 ruling 13-32; NR_Server_Options calls it).
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

-- A username's rolling hash over string.byte's code units (31 a step, a prime modulus; no row needed): the one hash
-- the push phase (K.view.pushOffset) and the save phase (K.store.savePhase) read, so the two stay half a gap apart.
function K.nameHash(username)
    local h = 0
    for i = 1, string.len(username) do
        h = (h * 31 + string.byte(username, i)) % 1000003
    end
    return h
end

K.HEX = "0123456789abcdef" -- the digit lookup: %x on a float raises on Kahlua

-- n (a whole number in [0, 16^width)) as width lower-case hex digits, built from the lookup string.
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

-- The tuning dials (Plan 19, spec Part A; ruling T1-1). NR.data.dials (NR_Data_Dials.lua, which sorts before every
-- kernel file) holds one row a dial; a kernel resolves its dials into its own table fields once, as it loads
-- (K.monotony.SLOPE = K.dials.get("monotony.SLOPE")), so a call site reads a plain field as before, no lookup runs per
-- tick or per minute (Rule 6), and the fields stay patchable (replay_live.set_constants, the fit tools). The
-- resolver lives here because this file loads before every other kernel file; the sandbox re-resolve is
-- NR_Kernel_Dials.lua's.
K.dials = {}
K.dials.DEPTH = 8 -- no row needed: the most `same` links a dial may follow before it reads as a cycle

-- The row of dial id. An unknown id, or a host that never loaded the registry, raises, so a typo fails at load.
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

-- The value of dial id: a row naming another dial (same) resolves to that dial's value, and a chain longer than
-- DEPTH raises as a cycle; a table value is the registry's own table, built by the constructor the kernel line had, so
-- its pairs order is unchanged; a kernel never writes into a table dial.
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

-- The one shared height (m): fixed and sex-neutral, read by every BMI and FFMI in the mod (K.acute's refeeding BMI
-- among them). It lives here, outside any sub-table, because this file loads before every other kernel file; it
-- resolves from its dial, core.HEIGHT_M, once K.dials.get above is defined.
K.HEIGHT_M = K.dials.get("core.HEIGHT_M")
