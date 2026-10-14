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
