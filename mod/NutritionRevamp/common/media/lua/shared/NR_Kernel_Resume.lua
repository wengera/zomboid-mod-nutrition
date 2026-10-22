-- NR_Kernel_Resume.lua -- nothing changes offline (Angus, 2026-10-18; Plan 16 spec section 1.1): the one resume
-- step and the online stall's sub-steps. A character resumes exactly as its player left it.
--
-- The resume: the store runs K.resume.resume at the first touch of every sight (NR_Server_Store's S.load, before any
-- step reads the record; a sight is a new player object or the first touch after a departure, never a stall). It
-- moves every world-age stamp of the record (K.resume.STAMPS) forward by the gap from the record's last step age
-- (K.resume.fromH) to the world age of the touch, so no step integrates the offline time and no world-age clock the
-- mod reads (a sleep window, a fed or vigorous latch, the 90-day mass window, a monotony entry, the nicotine anchor,
-- the unfed clock, the record day) counts it. The first step back then integrates only the online time since the
-- touch. A stamp laid after the last step (an eat after the last minute before a logout, or during a stall's carry)
-- lands at the touch, never past it (K.resume.moved; Plan 16 close review L1).
-- The fields that hold a world age but are not moved (K.resume.KEPT) say why.
--
-- The stall: a step longer than K.resume.STEP_M game minutes on the same player object (a slow server, the
-- fast-forwarded night) is online time, never an absence. The players' minute integrates it in K.resume.substeps
-- equal sub-steps of at most STEP_M, so nothing the minute books (sleep included) is lost; a queue slot runs at most
-- K.resume.SLOT_SUBSTEPS of them and the rest carry to the player's next minutes (Plan 16 Task 2 fix 1, ruling F2:
-- a stall is integrated in full, never frozen, and no frame runs more than the cap).
--
-- Pure: Lua tables and numbers in and out, no Java. Slow-clock and join-time code with no fast region. This file
-- sorts before NR_Kernel_Store.lua, so it keeps its own path splitter.
local K = NutritionRevamp.kernel
K.resume = {}

K.resume.STEP_M = K.dials.get("resume.STEP_M")
K.resume.SLOT_SUBSTEPS = K.dials.get("resume.SLOT_SUBSTEPS")

-- Every world-age stamp a record holds, by dotted path (a `*` segment is every key of the table at that level). The
-- step stamps (the age each adapter last stepped at) and the anchors the mod reads elapsed world time from. A record
-- field ending AgeH, At or Stamp is either here or in KEPT (test_kernel_resume.py walks a stepped record for them).
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
    "drain.pAt",           -- the smoothed BMI clock's anchor (starvation, Plan 17 spec section 1.2a): the open record day's start (body.dayStartH), moved at each close
    "monotony.t.*.last",   -- each eaten type's last eat (its count's decay)
}

-- The fields that hold a world age and are never moved, with the reason.
K.resume.KEPT = {
    firstSeen = "the age the record was made: identity, read only by the creation handler at the record's first sight",
    ["body.trail.ch"] = "derived: the hour the closed sums were built for, on the trail's online clock",
    ["body.bornAge"] = "the age the body was made: read only as its record day, floor(bornAge / 24), against the day count dayIndex, which counts online closes",
    ["body.trail.at"] = "the trailing-24 h window's clock, which runs on online hours (Metabolism moves it by each step's own length), so it needs no move",
    ["acute.bodyHour"] = "the body clock's phase, an hour of the day advanced only by integrated online hours (K.circadian.step), not a world age: an absence leaves it as the player left it",
}

-- The segments of a dotted path (a fresh array of strings).
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

-- The record's last step age: the latest finite step stamp of lastSeen, kineticsAge, satiety.t, nutrients.lastAgeH
-- and body.lastAgeH, or nil when none is finite (a record no step has run on).
function K.resume.fromH(record)
    local best = nil
    best = K.resume.later(best, record.lastSeen)
    best = K.resume.later(best, record.kineticsAge)
    best = K.resume.later(best, K.resume.field(record.satiety, "t"))
    best = K.resume.later(best, K.resume.field(record.nutrients, "lastAgeH"))
    best = K.resume.later(best, K.resume.field(record.body, "lastAgeH"))
    return best
end

-- t[k] when t is a table, else nil.
function K.resume.field(t, k)
    if type(t) ~= "table" then
        return nil
    end
    return t[k]
end

-- The later of best (nil or a number) and v; a v that is not finite is ignored.
function K.resume.later(best, v)
    if not K.finite(v) then
        return best
    end
    if best == nil or v > best then
        return v
    end
    return best
end

-- Move one stamp: v + gapH, or exactly toH when v is fromH (so the step stamps land on the touch's age with no
-- rounding, and the first step back integrates exactly 0). A forward move never lays a stamp past toH: a stamp laid
-- after the last step (an eat after the last minute before a logout, or during a stall's carry that a departure cut
-- short) reads as laid at the return, so no heal reads it as in the future and no restart reads it as a hard kill
-- (Plan 16 close review L1). A value that is not finite is left for its owner's heal.
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

-- Visit every leaf the path segs names under table t from index i, folding acc through fn: acc = fn(tbl, key, acc,
-- a, b, c) with the leaf's own table and key (a `*` segment visits every key of the table at that level). A path whose
-- table is absent visits nothing. Returns acc. The one dotted-path visitor of K.resume.shift and K.resume.latest.
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

-- K.resume.visit's leaf for the shift: move t[k] (K.resume.moved). Returns acc unchanged.
function K.resume.moveAt(t, k, acc, gapH, fromH, toH)
    t[k] = K.resume.moved(t[k], gapH, fromH, toH)
    return acc
end

-- K.resume.visit's leaf for the latest: the later of best and t[k] (K.resume.later).
function K.resume.peakAt(t, k, best)
    return K.resume.later(best, t[k])
end

-- Move every stamp of K.resume.STAMPS in record by gapH game hours (a stamp equal to fromH lands on toH exactly, and a
-- forward move stops at toH, when both are given). A path whose table is absent, and a stamp that is not finite, are
-- left. Returns the record.
function K.resume.shift(record, gapH, fromH, toH)
    local segs = K.resume.SEGS
    for i = 1, #segs do
        K.resume.visit(record, segs[i], 1, K.resume.moveAt, nil, gapH, fromH, toH)
    end
    return record
end

-- The resume at world age ageH: every stamp moved by the gap from the record's last step age to ageH. A record whose
-- latest stamp (K.resume.latest) is past ageH was written after the world's last save (a hard kill rolled the world
-- back under it, Plan 16 Task 3 fix 1): every stamp moves back by ageH - latest, so the latest lands on the world
-- clock and no heal reads a stamp in the future (the freeze rule run backwards; the rolled-back stretch is neither
-- integrated again nor read as elapsed). A record no step has run on, an unread age or an age equal to the last step
-- with no stamp past it moves nothing. Returns the gap moved, in game hours: positive forward, negative back, 0 none.
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

-- The sub-steps of an online step from fromH to ageH: 1 when it is at most STEP_M (or either age is not finite), else
-- the fewest equal sub-steps of at most STEP_M. The caller runs at most SLOT_SUBSTEPS of them a slot.
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

-- The record's latest world-age stamp over every path of K.resume.STAMPS, or nil when none is finite. The store reads
-- a record whose latest stamp is past the world clock as written after the world's last save (a hard-kill rollback,
-- NR_Server_Store's load rule, Plan 16 Task 3) and restores the backup, whose copy may itself be past it (fix 1).
-- K.resume.later's rule: a stamp that is not finite is ignored, and a path whose table is absent adds nothing.
function K.resume.latest(record)
    local best = nil
    local segs = K.resume.SEGS
    for i = 1, #segs do
        best = K.resume.visit(record, segs[i], 1, K.resume.peakAt, best)
    end
    return best
end
