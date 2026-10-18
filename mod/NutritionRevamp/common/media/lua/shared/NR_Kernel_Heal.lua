-- NR_Kernel_Heal.lua -- the body record's self-heal (the #2833 pattern; Plan 10 Task R3, moved out of
-- NR_Server_Metabolism.lua's local heal). The adapter runs it once, before the minute's arithmetic (Plan 11
-- ruling 10): a non-finite scalar or ring slot is stamped its neutral and named. The masses and the creation scalars
-- (lm, fm, F0, Fc, Pk) heal to the no-trait body's values (K.body.create(nil, nil, P) at the effective sex, Plan 13
-- Task 12), N0 to the no-trait 1 and T to 1; fmRef to the current fat; rmod's protein input to the neutral P_LOW;
-- dayIndex to the record-day lower bound the adapter passes (the Nutrients step's last seen day, else the Effects
-- day), else to the birth day floor(bornAge / 24), else to the world day (a NaN would stop every day close; the
-- birth day forgets the closes since birth but counts no offline day, Plan 16 Task 2); dayStartH to the world day's
-- start; lastAgeH to the world age; the labile
-- lean, the grace counters, the signal, the closed week's sets and the day accumulators to 0; a fat rung that is not
-- a whole number in 0..2, or a thin rung not in 0..3, to 0; lm0dis to the current lean; a ring slot to 0 (mass7's to
-- the current body mass fm + lm + lx); the trailing-24 h window's age (its online clock, K.body.trailClock) to the world age with every ring emptied, and a
-- window slot to 0, its ring named once a slot (K.heal.trail). Every field and ring is laid by K.body.new, so the heal
-- creates none. Pure: a Lua table and numbers in; the adapter counts and logs. Slow-clock code: no fast region. Every
-- K.body / K.aerobic / K.strength reference is at call time.
local K = NutritionRevamp.kernel
K.heal = {}

-- The scalars that heal to a fixed neutral, as { key, neutral } pairs in the order the names are reported in.
K.heal.NEUTRAL = { { "energyState", 1 }, { "rmod", 1 }, { "tac", 1 }, { "at", 0 }, { "inDay", 0 }, { "eeDay", 0 },
                   { "ebDay", 0 }, { "actKcalDay", 0 }, { "exKcalDay", 0 }, { "pDay", 0 }, { "carbDay", 0 },
                   { "lipDay", 0 }, { "alcDay", 0 }, { "metMinDay", 0 }, { "band1Day", 0 }, { "band2Day", 0 },
                   { "tDisuse", 0 }, { "lx", 0 }, { "grace", 0 }, { "Tgrace", 0 }, { "sigDay", 0 }, { "S", 0 },
                   { "N0", 1 }, { "T", 1 } }
-- The creation fields that heal to the no-trait body's value (K.body.create's keys), in report order.
K.heal.CREATION = { "lm", "fm", "F0", "Fc", "Pk" }
-- The rungs and their highest value: a held rung is a whole number from 0 (K.traits.axes).
K.heal.RUNGS = { { "fatT", 2 }, { "thinT", 3 } }
-- The rings whose slots heal to 0 (slot 7 is yesterday); mass7 heals to the current mass.
K.heal.ZERO_RINGS = { "eb7", "p7", "sig7" }

-- The names so far, comma-joined, with one more appended (a repeat is appended again, as the adapter's log
-- always read).
function K.heal.mark(bad, name)
    if bad == nil then
        return name
    end
    return bad .. "," .. name
end

-- Whether v is a held rung: a whole number from 0 to top.
function K.heal.rung(v, top)
    return K.finite(v) and v >= 0 and v <= top and v == math.floor(v)
end

-- Heal body in place at world age ageH. specific is NR.SexSpecific, P the strength table the no-trait body is built
-- with (nil reads K.strength.DEFAULTS) and dayFloor the record-day lower bound a non-finite dayIndex heals to (nil or
-- non-finite reads the world day). Returns the comma-joined names of the healed fields, or nil when none was.
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

-- The post-step guard: copy the guarded keys of t before the step, and after it
-- re-stamp from the copy every key the step left non-finite, so no later step of the same minute reads a NaN the
-- step's own arithmetic made. A key whose copy is not finite either is left for the next pre-step heal.
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

-- The trailing-24 h window's heal (the Task 9c review), from K.heal.body, before the
-- minute moves the window; ageH is the window's clock at the minute (K.body.trailClock, the world age when that is not
-- finite). A non-finite age leaves no slot's hour known: every ring takes K.body.newTrail(ageH)'s
-- values (every slot and closed sum 0, unbuilt) at ageH, and only the age is named. Otherwise the heal
-- walks the rings (K.body.trailRingSum, which zeroes every non-finite slot and counts them) when the closed sums are
-- unbuilt or stand for another hour, when the hour turns at ageH (so a closed hour's slot gone non-finite is zeroed
-- here, named, and not by a reader's rebuild), or that ring alone when its read is non-finite (K.body.trail24: the
-- current hour, the oldest and the closed sums); it names a ring once for every slot it zeroed, or once when its read
-- was non-finite and it zeroed none (the derived closed sum alone; Task 9d fix), and leaves the sums built for the
-- window's hour. The check is six O(1) reads a minute; the 150 slots are walked once a game hour. Returns bad with the
-- names appended.
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
