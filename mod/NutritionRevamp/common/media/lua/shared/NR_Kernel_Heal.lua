-- NR_Kernel_Heal.lua -- the body record's self-heal (the #2833 pattern; Plan 10 Task R3, moved out of
-- NR_Server_Metabolism.lua's local heal). The adapter runs it once, before the minute's arithmetic (Plan 11
-- ruling 10): a non-finite scalar or ring slot is stamped its neutral and named. Masses heal to their creation values
-- (a non-finite creation value to the current mass, else the 80 kg split); rmod's protein input to the neutral
-- P_LOW; dayIndex to the day of the world age (a NaN would stop every day close); lastAgeH and lastCloseAgeH to
-- the world age; a ring slot to 0 (mass7's to the current mass). Every field and ring is laid by K.body.new, so
-- the heal creates none. The creation scalars heal too: r and
-- traitCarry to 1, l0 to the Strength level the adapter read (its one engine read, made only when body.l0 is not
-- finite, and passed in), tDisuse to 0, lm0dis to the current lean mass, nPeak to 0 and tPeakD to dayIndex; every
-- nHist and bandWeek slot to 0. Pure: a Lua table and numbers in; the adapter counts and logs. Slow-clock code:
-- no fast region. Every K.body / K.aerobic / K.strength reference is at call time.
local K = NutritionRevamp.kernel
K.heal = {}

-- The scalars that heal to a fixed neutral, and their order (the order the names are reported in).
K.heal.NEUTRAL = { energyState = 1, dmod = 1, rmod = 1, tac = 1, at = 0, n = 0, vStr = 0, vHyp = 0,
                   vStrHigh = 0, inDay = 0, eeDay = 0, ebDay = 0, actKcalDay = 0, exKcalDay = 0, pDay = 0,
                   carbDay = 0, lipDay = 0, alcDay = 0, metMinDay = 0, band1Day = 0, band2Day = 0, cumDef = 0,
                   r = 1, traitCarry = 1, tDisuse = 0, nPeak = 0 }
K.heal.NEUTRAL_KEYS = { "energyState", "dmod", "rmod", "tac", "at", "n", "vStr", "vHyp", "vStrHigh", "inDay",
                        "eeDay", "ebDay", "actKcalDay", "exKcalDay", "pDay", "carbDay", "lipDay", "alcDay",
                        "metMinDay", "band1Day", "band2Day", "cumDef", "r", "traitCarry", "tDisuse", "nPeak" }
-- The rings whose slots heal to 0 (slot 7 is yesterday); mass7 heals to the current mass.
K.heal.ZERO_RINGS = { "eb7", "p7", "carb7", "lip7" }

-- The names so far, comma-joined, with one more appended (a repeat is appended again, as the adapter's log
-- always read).
function K.heal.mark(bad, name)
    if bad == nil then
        return name
    end
    return bad .. "," .. name
end

-- Heal body in place at world age ageH; l0 is the Strength level read now (nil or non-finite reads 0), used only
-- when body.l0 is not finite. Returns the comma-joined names of the healed fields, or nil when none was.
function K.heal.body(body, ageH, l0)
    local bad = nil
    if not K.vector.finite(body.fm0) or not K.vector.finite(body.lm0) then
        local sex = 1
        if body.sex == 2 then
            sex = 2
        end
        local fmS, lmS = K.body.split(80, sex, {})
        if not K.vector.finite(body.fm0) then
            if K.vector.finite(body.fm) then
                body.fm0 = body.fm
            else
                body.fm0 = fmS
            end
            bad = K.heal.mark(bad, "fm0")
        end
        if not K.vector.finite(body.lm0) then
            if K.vector.finite(body.lm) then
                body.lm0 = body.lm
            else
                body.lm0 = lmS
            end
            bad = K.heal.mark(bad, "lm0")
        end
    end
    if not K.vector.finite(body.fm) then
        body.fm = body.fm0
        bad = K.heal.mark(bad, "fm")
    end
    if not K.vector.finite(body.lm) then
        body.lm = body.lm0
        bad = K.heal.mark(bad, "lm")
    end
    if not K.vector.finite(body.fmRef) then
        body.fmRef = body.fm
        bad = K.heal.mark(bad, "fmRef")
    end
    if not K.vector.finite(body.pPrevKg) then
        body.pPrevKg = K.aerobic.P_LOW
        bad = K.heal.mark(bad, "pPrevKg")
    end
    if not K.vector.finite(body.dayIndex) then
        body.dayIndex = math.floor(ageH / 24)
        bad = K.heal.mark(bad, "dayIndex")
    end
    if not K.vector.finite(body.lastAgeH) then
        body.lastAgeH = ageH
        bad = K.heal.mark(bad, "lastAgeH")
    end
    if not K.vector.finite(body.lastCloseAgeH) then
        body.lastCloseAgeH = ageH
        bad = K.heal.mark(bad, "lastCloseAgeH")
    end
    local keys = K.heal.NEUTRAL_KEYS
    for i = 1, #keys do
        local k = keys[i]
        if not K.vector.finite(body[k]) then
            body[k] = K.heal.NEUTRAL[k]
            bad = K.heal.mark(bad, k)
        end
    end
    if not K.vector.finite(body.l0) then
        if K.vector.finite(l0) then
            body.l0 = l0
        else
            body.l0 = 0
        end
        bad = K.heal.mark(bad, "l0")
    end
    if not K.vector.finite(body.lm0dis) then
        body.lm0dis = body.lm
        bad = K.heal.mark(bad, "lm0dis")
    end
    if not K.vector.finite(body.tPeakD) then
        body.tPeakD = body.dayIndex
        bad = K.heal.mark(bad, "tPeakD")
    end
    for i = 1, K.strength.MEM_HOLD_DAYS do
        if not K.vector.finite(body.nHist[i]) then
            body.nHist[i] = 0
            bad = K.heal.mark(bad, "nHist")
        end
    end
    for i = 1, 7 do
        local slot = body.bandWeek[i]
        if not K.vector.finite(slot[1]) then
            slot[1] = 0
            bad = K.heal.mark(bad, "bandWeek")
        end
        if not K.vector.finite(slot[2]) then
            slot[2] = 0
            bad = K.heal.mark(bad, "bandWeek")
        end
    end
    for i = 1, 7 do
        if not K.vector.finite(body.mass7[i]) then
            body.mass7[i] = body.fm + body.lm
            bad = K.heal.mark(bad, "mass7")
        end
    end
    for r = 1, #K.heal.ZERO_RINGS do
        local key = K.heal.ZERO_RINGS[r]
        local ring = body[key]
        for i = 1, 7 do
            if not K.vector.finite(ring[i]) then
                ring[i] = 0
                bad = K.heal.mark(bad, key)
            end
        end
    end
    return bad
end

-- The post-step guard (Plan 11 Task 12; Appendix J): copy the guarded keys of t before the step, and after it
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
        if type(v) == "number" and (v ~= v or v == math.huge or v == -math.huge) then
            local s = snap[k]
            if type(s) == "number" and s == s and s ~= math.huge and s ~= -math.huge then
                t[k] = s
                n = n + 1
            end
        end
    end
    return n
end
