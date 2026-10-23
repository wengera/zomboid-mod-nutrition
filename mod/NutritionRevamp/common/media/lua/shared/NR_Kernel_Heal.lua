-- NR_Kernel_Heal.lua -- the body record's self-heal (the #2833 pattern), run once before the minute's arithmetic: a
-- non-finite scalar or ring slot is stamped its neutral and named. Creation fields heal to the no-trait body's values;
-- a NaN dayIndex would stop every day close, so it heals to the record-day floor, which counts no offline day. Every
-- field is laid by K.body.new, so the heal creates none. K.body / K.aerobic / K.strength are read at call time.
local K = NutritionRevamp.kernel
K.heal = {}

K.heal.NEUTRAL = { { "energyState", 1 }, { "rmod", 1 }, { "tac", 1 }, { "at", 0 }, { "inDay", 0 }, { "eeDay", 0 },
                   { "ebDay", 0 }, { "actKcalDay", 0 }, { "exKcalDay", 0 }, { "pDay", 0 }, { "carbDay", 0 },
                   { "lipDay", 0 }, { "alcDay", 0 }, { "metMinDay", 0 }, { "band1Day", 0 }, { "band2Day", 0 },
                   { "tDisuse", 0 }, { "lx", 0 }, { "grace", 0 }, { "Tgrace", 0 }, { "sigDay", 0 }, { "S", 0 },
                   { "N0", 1 }, { "T", 1 } }
K.heal.CREATION = { "lm", "fm", "F0", "Fc", "Pk" }
K.heal.RUNGS = { { "fatT", 2 }, { "thinT", 3 } }
K.heal.ZERO_RINGS = { "eb7", "p7", "sig7" }

-- A repeat is appended again, as the adapter's log always read.
function K.heal.mark(bad, name)
    if bad == nil then
        return name
    end
    return bad .. "," .. name
end

function K.heal.rung(v, top)
    return K.finite(v) and v >= 0 and v <= top and v == math.floor(v)
end

-- P nil reads K.strength.DEFAULTS; a nil or non-finite dayFloor reads the world day. Returns the names, or nil.
function K.heal.body(body, ageH, specific, P, dayFloor)
    local bad = nil
    local base = nil
    local creation = K.heal.CREATION
    for i = 1, #creation do
        local k = creation[i]
        if not K.finite(body[k]) then
            base = base or K.body.create(nil, nil, P or K.strength.DEFAULTS, K.body.effSex(body.sex, specific))
            body[k] = base[k]
            bad = K.heal.mark(bad, k)
        end
    end
    if not K.finite(body.fmRef) then
        body.fmRef = body.fm
        bad = K.heal.mark(bad, "fmRef")
    end
    if not K.finite(body.pPrevKg) then
        body.pPrevKg = K.aerobic.P_LOW
        bad = K.heal.mark(bad, "pPrevKg")
    end
    if not K.finite(body.dayIndex) then
        if K.finite(dayFloor) then
            body.dayIndex = dayFloor
        elseif K.finite(body.bornAge) then
            body.dayIndex = math.floor(body.bornAge / 24)
        else
            body.dayIndex = math.floor(ageH / 24)
        end
        bad = K.heal.mark(bad, "dayIndex")
    end
    if not K.finite(body.dayStartH) then
        body.dayStartH = math.floor(ageH / 24) * 24
        bad = K.heal.mark(bad, "dayStartH")
    end
    if not K.finite(body.lastAgeH) then
        body.lastAgeH = ageH
        bad = K.heal.mark(bad, "lastAgeH")
    end
    local neutral = K.heal.NEUTRAL
    for i = 1, #neutral do
        local k = neutral[i][1]
        if not K.finite(body[k]) then
            body[k] = neutral[i][2]
            bad = K.heal.mark(bad, k)
        end
    end
    local rungs = K.heal.RUNGS
    for i = 1, #rungs do
        local k = rungs[i][1]
        if not K.heal.rung(body[k], rungs[i][2]) then
            body[k] = 0
            bad = K.heal.mark(bad, k)
        end
    end
    if not K.finite(body.lm0dis) then
        body.lm0dis = body.lm
        bad = K.heal.mark(bad, "lm0dis")
    end
    for i = 1, K.body.WEEK_N do
        local slot = body.bandWeek[i]
        if not K.finite(slot[1]) then
            slot[1] = 0
            bad = K.heal.mark(bad, "bandWeek")
        end
        if not K.finite(slot[2]) then
            slot[2] = 0
            bad = K.heal.mark(bad, "bandWeek")
        end
    end
    for i = 1, K.body.WEEK_N do
        if not K.finite(body.mass7[i]) then
            body.mass7[i] = body.fm + body.lm + body.lx
            bad = K.heal.mark(bad, "mass7")
        end
    end
    for r = 1, #K.heal.ZERO_RINGS do
        local key = K.heal.ZERO_RINGS[r]
        local ring = body[key]
        for i = 1, K.body.WEEK_N do
            if not K.finite(ring[i]) then
                ring[i] = 0
                bad = K.heal.mark(bad, key)
            end
        end
    end
    local clock = K.body.trailClock(body, ageH)
    if not K.finite(clock) then
        clock = ageH
    end
    return K.heal.trail(body.trail, clock, bad)
end

-- The post-step guard: re-stamp from the pre-step copy every key the step left non-finite, so no later step of the
-- same minute reads a NaN; a key whose copy is not finite either is left for the next pre-step heal.
function K.heal.snap(t, keys, out)
    for i = 1, #keys do
        out[keys[i]] = t[keys[i]]
    end
    return out
end

function K.heal.guard(t, keys, snap)
    local n = 0
    for i = 1, #keys do
        local k = keys[i]
        local v = t[k]
        if type(v) == "number" and not K.finite(v) then
            local s = snap[k]
            if K.finite(s) then
                t[k] = s
                n = n + 1
            end
        end
    end
    return n
end

-- The trailing-24 h window's heal, before the minute moves it. A non-finite age empties every ring (only the age is
-- named). Otherwise the rings are walked when the closed sums are unbuilt or stale or the hour turns, so a closed slot
-- gone non-finite is zeroed and named here, not by a reader's rebuild; six O(1) reads a minute, the walk once an hour.
function K.heal.trail(t, ageH, bad)
    local keys = K.body.TRAIL_KEYS
    if not K.finite(t.at) then
        for k = 1, #keys do
            local ring = t[keys[k]]
            for i = 1, K.body.TRAIL_N do
                ring[i] = 0
            end
            t.c[keys[k]] = 0
        end
        t.ch = -1
        t.at = ageH
        return K.heal.mark(bad, "trail.at")
    end
    local h = math.floor(t.at)
    local due = t.ch ~= h or h ~= math.floor(ageH)
    local cur = K.body.trailSlot(h)
    for k = 1, #keys do
        local key = keys[k]
        local badRead = false
        if not due then
            badRead = not K.finite(K.body.trail24(t, key))
        end
        if due or badRead then
            local s, z = K.body.trailRingSum(t[key], cur)
            t.c[key] = s
            for i = 1, z do
                bad = K.heal.mark(bad, "trail." .. key)
            end
            if badRead and z == 0 then
                bad = K.heal.mark(bad, "trail." .. key)
            end
        end
    end
    if due then
        t.ch = h
    end
    return bad
end
