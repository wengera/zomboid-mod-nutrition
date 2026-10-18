-- NR_Kernel_Resume.lua -- nothing changes offline (Angus, 2026-10-18; Plan 16 spec section 1.1): the one resume
-- step and the online stall's sub-steps. A character resumes exactly as its player left it.
--
-- The resume: the store runs K.resume.resume at the first touch of every sight (NR_Server_Store's S.load, before any
-- step reads the record; a sight is a new player object or the first touch after a departure, never a stall). It
-- moves every world-age stamp of the record (K.resume.STAMPS) forward by the gap from the record's last step age
-- (K.resume.fromH) to the world age of the touch, so no step integrates the offline time and no world-age clock the
-- mod reads (a sleep window, a fed or vigorous latch, the 90-day mass window, a monotony entry, the nicotine anchor,
-- the unfed clock, the record day) counts it. The first step back then integrates only the online time since the
-- touch. A stamp laid after the last step (an eat after the last minute before a logout) moves with the rest.
-- The fields that hold a world age but are not moved (K.resume.KEPT) say why.
--
-- The stall: a step longer than K.resume.STEP_M game minutes on the same player object (a slow server, the
-- fast-forwarded night) is online time, never an absence. The players' minute integrates it in K.resume.substeps
-- equal sub-steps of at most STEP_M, so nothing the minute books (sleep included) is lost.
--
-- Pure: Lua tables and numbers in and out, no Java. Slow-clock and join-time code with no fast region. This file
-- sorts before NR_Kernel_Store.lua, so it keeps its own path splitter.
local K = NutritionRevamp.kernel
K.resume = {}

K.resume.STEP_M = 60 -- game minutes, not science (no row): the longest step an adapter integrates at once, the bound the adapters clamped a step at until Plan 16
K.resume.MAX_SUBSTEPS = 24 -- not science (no row), Rule 6: a stall longer than a day of STEP_M sub-steps is a stopped server, not play; its excess is frozen as an absence, so one queue slot runs at most 24 pipelines

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
    "monotony.t.*.last",   -- each eaten type's last eat (its count's decay)
}

-- The fields that hold a world age and are never moved, with the reason.
K.resume.KEPT = {
    firstSeen = "the age the record was made: identity, read only by the creation handler at the record's first sight",
    ["body.bornAge"] = "the age the body was made: read only as its record day, floor(bornAge / 24), against the day count dayIndex, which counts online closes",
    ["body.trail.at"] = "the trailing-24 h window's clock, which runs on online hours (Metabolism moves it by each step's own length), so it needs no move",
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
-- rounding, and the first step back integrates exactly 0). A value that is not finite is left for its owner's heal.
function K.resume.moved(v, gapH, fromH, toH)
    if not K.finite(v) then
        return v
    end
    if fromH ~= nil and v == fromH then
        return toH
    end
    return v + gapH
end

-- Walk segs from index i under table t and move every stamp the path names.
function K.resume.walk(t, segs, i, gapH, fromH, toH)
    if type(t) ~= "table" then
        return
    end
    local seg = segs[i]
    if i == #segs then
        t[seg] = K.resume.moved(t[seg], gapH, fromH, toH)
        return
    end
    if seg == "*" then
        for _, v in pairs(t) do
            K.resume.walk(v, segs, i + 1, gapH, fromH, toH)
        end
        return
    end
    K.resume.walk(t[seg], segs, i + 1, gapH, fromH, toH)
end

-- Move every stamp of K.resume.STAMPS in record by gapH game hours (a stamp equal to fromH lands on toH exactly,
-- when both are given). A path whose table is absent, and a stamp that is not finite, are left. Returns the record.
function K.resume.shift(record, gapH, fromH, toH)
    local segs = K.resume.SEGS
    for i = 1, #segs do
        K.resume.walk(record, segs[i], 1, gapH, fromH, toH)
    end
    return record
end

-- The resume at world age ageH: every stamp moved by the gap from the record's last step age to ageH. A record no
-- step has run on, an unread age or an age not past the last step moves nothing (a world behind the record, a
-- hard-kill rollback, is the store's backup's case). Returns the gap moved, in game hours (0 when none).
function K.resume.resume(record, ageH)
    if not K.finite(ageH) then
        return 0
    end
    local fromH = K.resume.fromH(record)
    if fromH == nil or not (ageH > fromH) then
        return 0
    end
    local gapH = ageH - fromH
    K.resume.shift(record, gapH, fromH, ageH)
    return gapH
end

-- The sub-steps of an online step from fromH to ageH: 1 when it is at most STEP_M (or either age is not finite), else
-- the fewest equal sub-steps of at most STEP_M, capped at MAX_SUBSTEPS. Second: the game hours past the cap, which the
-- caller freezes (K.resume.shift) before it integrates the rest (0 under the cap).
function K.resume.substeps(fromH, ageH)
    if not K.finite(fromH) or not K.finite(ageH) then
        return 1, 0
    end
    local stepH = K.resume.STEP_M / 60
    local spanH = ageH - fromH
    if spanH <= stepH then
        return 1, 0
    end
    local n = math.ceil(spanH / stepH - 1e-9)
    if n <= K.resume.MAX_SUBSTEPS then
        return n, 0
    end
    return K.resume.MAX_SUBSTEPS, spanH - K.resume.MAX_SUBSTEPS * stepH
end
