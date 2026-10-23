-- NR_Kernel_Resume.lua -- nothing changes offline: a character resumes exactly as its player left it.
-- The resume runs at the first touch of every sight (S.load, before any step reads the record) and moves every
-- world-age stamp forward by the offline gap, so no step or clock integrates it. A stamp laid after the last step
-- lands at the touch, never past it. The stall (a step longer than STEP_M on the same player object) is online time:
-- it is integrated in full in sub-steps, at most SLOT_SUBSTEPS a queue slot, the rest carried to the next minutes.
-- This file sorts before NR_Kernel_Store.lua, so it keeps its own path splitter.
local K = NutritionRevamp.kernel
K.resume = {}

K.resume.STEP_M = K.dials.get("resume.STEP_M")
K.resume.SLOT_SUBSTEPS = K.dials.get("resume.SLOT_SUBSTEPS")

-- Every world-age stamp a record holds, by dotted path (`*` is every key). A field ending AgeH, At or Stamp is here or
-- in KEPT (test_kernel_resume.py walks a stepped record for them).
K.resume.STAMPS = {
    "lastSeen",            -- the players' minute: the age of the last step (K.resume.fromH reads it first)
    "kineticsAge",         -- Kinetics' step stamp
    "satiety.t",           -- the writer's step stamp
    "satiety.nicH",        -- the writer's nicotine anchor: the last minute the withdrawal read 0 or fell
    "nutrients.lastAgeH",  -- Nutrients' step stamp
    "body.lastAgeH",       -- Metabolism's step stamp
    "body.dayStartH",      -- the open record day's start: the day closes 24 online hours after it
    "acute.winStartH",     -- the sleep window's start
    "acute.mass90ageH",    -- the 90-day mass window's stamp
    "acute.lastFedAgeH",   -- the last fed minute (blood glucose's fasting clock)
    "acute.lastVigAgeH",   -- the last band-2 minute (the sleep bout's vigorous latch)
    "drain.fedAgeH",       -- the unfed clock's stamp (starvation)
    "drain.pAt",           -- the smoothed BMI clock's anchor (starvation): the open record day's start, moved at each close
    "monotony.t.*.last",   -- each eaten type's last eat (its count's decay)
    "hedonics.s",          -- the plain-energy ring's current hour start (K.hedonics.rotate: the ring runs on online hours)
}

-- The fields that hold a world age and are never moved, with the reason.
K.resume.KEPT = {
    firstSeen = "the age the record was made: identity, read only by the creation handler at the record's first sight",
    ["body.trail.ch"] = "derived: the hour the closed sums were built for, on the trail's online clock",
    ["body.bornAge"] = "the age the body was made: read only as its record day, floor(bornAge / 24), against the day count dayIndex, which counts online closes",
    ["body.trail.at"] = "the trailing-24 h window's clock, which runs on online hours (Metabolism moves it by each step's own length), so it needs no move",
    ["acute.bodyHour"] = "the body clock's phase, an hour of the day advanced only by integrated online hours (K.circadian.step), not a world age: an absence leaves it as the player left it",
}

function K.resume.split(path)
    local out = {}
    for seg in string.gmatch(path, "[^%.]+") do
        out[#out + 1] = seg
    end
    return out
end

K.resume.SEGS = {}
for i = 1, #K.resume.STAMPS do
    K.resume.SEGS[i] = K.resume.split(K.resume.STAMPS[i])
end

-- nil when none is finite (a record no step has run on).
function K.resume.fromH(record)
    local best = nil
    best = K.resume.later(best, record.lastSeen)
    best = K.resume.later(best, record.kineticsAge)
    best = K.resume.later(best, K.resume.field(record.satiety, "t"))
    best = K.resume.later(best, K.resume.field(record.nutrients, "lastAgeH"))
    best = K.resume.later(best, K.resume.field(record.body, "lastAgeH"))
    return best
end

function K.resume.field(t, k)
    if type(t) ~= "table" then
        return nil
    end
    return t[k]
end

function K.resume.later(best, v)
    if not K.finite(v) then
        return best
    end
    if best == nil or v > best then
        return v
    end
    return best
end

-- A stamp equal to fromH lands on toH exactly, so the first step back integrates exactly 0. A forward move never passes
-- toH, so no heal reads a late stamp as in the future and no restart reads it as a hard kill. A non-finite v is left.
function K.resume.moved(v, gapH, fromH, toH)
    if not K.finite(v) then
        return v
    end
    if fromH ~= nil and v == fromH then
        return toH
    end
    if toH ~= nil and gapH > 0 and v + gapH > toH then
        return toH
    end
    return v + gapH
end

-- A path whose table is absent visits nothing. The one dotted-path visitor of shift and latest.
function K.resume.visit(t, segs, i, fn, acc, a, b, c)
    if type(t) ~= "table" then
        return acc
    end
    local seg = segs[i]
    if i == #segs then
        return fn(t, seg, acc, a, b, c)
    end
    if seg == "*" then
        for _, v in pairs(t) do
            acc = K.resume.visit(v, segs, i + 1, fn, acc, a, b, c)
        end
        return acc
    end
    return K.resume.visit(t[seg], segs, i + 1, fn, acc, a, b, c)
end

function K.resume.moveAt(t, k, acc, gapH, fromH, toH)
    t[k] = K.resume.moved(t[k], gapH, fromH, toH)
    return acc
end

function K.resume.peakAt(t, k, best)
    return K.resume.later(best, t[k])
end

-- A path whose table is absent, and a stamp that is not finite, are left.
function K.resume.shift(record, gapH, fromH, toH)
    local segs = K.resume.SEGS
    for i = 1, #segs do
        K.resume.visit(record, segs[i], 1, K.resume.moveAt, nil, gapH, fromH, toH)
    end
    return record
end

-- A record whose latest stamp is past ageH was written after the world's last save (a hard kill rolled the world back
-- under it): every stamp moves back, so the latest lands on the world clock and no heal reads a stamp in the future.
-- Returns the gap moved, in game hours: positive forward, negative back, 0 none.
function K.resume.resume(record, ageH)
    if not K.finite(ageH) then
        return 0
    end
    local fromH = K.resume.fromH(record)
    if fromH == nil then
        return 0
    end
    local latest = K.resume.latest(record)
    local gapH = ageH - fromH
    if latest ~= nil and latest > ageH then
        gapH = ageH - latest
        fromH = latest
    elseif not (ageH > fromH) then
        return 0
    end
    K.resume.shift(record, gapH, fromH, ageH)
    return gapH
end

-- The caller runs at most SLOT_SUBSTEPS of them a slot.
function K.resume.substeps(fromH, ageH)
    if not K.finite(fromH) or not K.finite(ageH) then
        return 1
    end
    local stepH = K.resume.STEP_M / 60
    local spanH = ageH - fromH
    if spanH <= stepH then
        return 1
    end
    return math.ceil(spanH / stepH - 1e-9)
end

-- The store reads a record whose latest stamp is past the world clock as a hard-kill rollback and restores the backup.
function K.resume.latest(record)
    local best = nil
    local segs = K.resume.SEGS
    for i = 1, #segs do
        best = K.resume.visit(record, segs[i], 1, K.resume.peakAt, best)
    end
    return best
end
