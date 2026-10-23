-- NR_Kernel_Store.lua: the persisted record's contract: the closed list of INPUT paths a save holds, and the load that
-- keeps a stored record's inputs and rebuilds everything else. An input is a field a step reads from the previous
-- minute and no step can recompute (an accumulator, a stamp, a latch, a draw, a creation constant); every other field
-- is derived and dropped at load, so a formula change touches no save. A `*` segment stands for every key at its level.
-- After a load the derived fields read their constructors' neutral values until the first slow minute, except
-- stomachFill (recomputed) and fluids.thirstTarget and effects.intoxTarget, left nil: nil is the writer's no-write,
-- where the constructors' 0 would drive THIRST or INTOXICATION to 0.
-- Pure, no Java. Sorts after the body, acute, drain, effects, fluids, nutrients and stomach kernels and before
-- Strength, Vector and View; every K.* reference outside K.store resolves at call time.
local K = NutritionRevamp.kernel
K.store = {}

-- Grouped by the step that owns each field; a reviewer diffs each group against its owning step.
K.store.INPUTS = {
    -- identity (NR_Server_Store, NR_Server_Players)
    "username", "firstSeen", "lastSeen", "resets", "dead",
    -- satiety: the meal pool M, which the writer
    -- seeds from HUNGER when absent or non-finite, the acute suppression state S and the exercise lag L (kcal/day)
    "satiety.M", "satiety.S", "satiety.L", "satiety.t", "satiety.nicH", -- t: the writer's last step age, read across a restart; nicH: the nicotine fade's anchor
    -- kinetics: pool is a diagnostic no step reads back, kept because it cannot be rebuilt
    "kineticsAge", "stomach.liquid", "stomach.volX", "stomach.liqKcal", "stomach.buffer.*", "pool.*",
    -- nutrients, per key: g is gradeHyst's previous grade and ah its hours (the scurvy, beriberi and pellagra onsets read
    -- g == 4 with ah); S, H and bone are laid lazily by K.interact.two (a dropped S re-seeds iron replete). x is derived.
    "nutrients.*.p", "nutrients.*.p2", "nutrients.*.g", "nutrients.*.gl", "nutrients.*.ah", "nutrients.*.e24",
    "nutrients.*.dmg", "nutrients.*.ext", "nutrients.*.ax", "nutrients.*.axr", "nutrients.*.S", "nutrients.*.H",
    "nutrients.*.bone",
    -- nutrients, the state's own: allReplete, ironGrade, anaemia and vitDClinical are derived.
    "nutrients.epoch", "nutrients.lastAgeH", "nutrients.lastDayIndex",
    -- body, the creation constants
    "body.lm0dis", "body.fmRef", "body.sex", "body.bornAge", "body.F0", "body.Fc", "body.N0",
    -- body, the masses and clocks
    "body.fm", "body.lm", "body.lx", "body.Pk", "body.dayIndex", "body.dayStartH", "body.lastAgeH",
    -- body, the day accumulators and the closed day's stamps held until the next close
    "body.inDay", "body.eeDay", "body.ebDay", "body.actKcalDay", "body.exKcalDay", "body.pDay", "body.carbDay",
    "body.lipDay", "body.alcDay", "body.inDayClosed", "body.inDay2", "body.inDay3", "body.recentDays", "body.pPrevKg",
    "body.eb7.*", "body.mass7.*", "body.p7.*", "body.bandWeek.*",
    -- body, the trailing-24 h window: c and ch are derived (the constructor's ch -1 rebuilds them)
    "body.trail.at", "body.trail.kcal.*", "body.trail.ee.*", "body.trail.ex.*", "body.trail.p.*", "body.trail.carb.*",
    "body.trail.lip.*",
    -- body, adaptation: multi-day accumulators, never recomputed from the masses
    "body.tac", "body.at", "body.epoc", -- epoc: the after-burn pool, laid by the first exercise minute
    "body.metMinDay", "body.band1Day", "body.band2Day",
    -- body, strength: levelDue keeps a write deferred on a sleeper or a first-minute re-pin across a restart
    "body.sigDay", "body.sig7.*", "body.S", "body.grace", "body.T", "body.Tgrace", "body.tDisuse", "body.fatT",
    "body.thinT", "body.band", "body.wroteL", "body.levelDue",
    -- acute: bac, g, wd, circ, frozen, iu, iuSleep and av are derived.
    "acute.gutAlc", "acute.gutCaf", "acute.caf", "acute.cafMean", "acute.cafTol", "acute.cafLowH",
    "acute.slowMet", "acute.alc", "acute.alcPeak", "acute.hang", "acute.hangH", "acute.glyc", "acute.bg",
    "acute.awakeH", "acute.debtH", "acute.sleptH", "acute.boutH", "acute.gapH", "acute.winStartH",
    "acute.winSleptH", "acute.S", "acute.starvedDays", "acute.lowDay", "acute.mass90max", "acute.mass90ageH",
    "acute.bmi", "acute.refeedRisk", "acute.refeedDayN", "acute.refeedEvent", "acute.exEma",
    "acute.lastVigAgeH", "acute.boutVig", "acute.coldH", "acute.retEma", "acute.alc7", "acute.alcDayG",
    "acute.lastFedAgeH", "acute.lastB1", "acute.lastB2", "acute.bodyHour", "acute.bodyOn",
    -- fluids: dehydPct, c, naPlasma, thirstTarget, sweatActive, sweatLmin, viewPct and fv are derived.
    "fluids.water", "fluids.na", "fluids.k", "fluids.sweatK", "fluids.naSweat", "fluids.sweat6h",
    "fluids.loss6h", "fluids.autoDrop",
    -- effects: a lost own flag orphans the band trait; the coefficient set and its key are derived (the default key
    -- forces a compose).
    "effects.dirty", "effects.epoch", "effects.own.nv", "effects.own.ss", "effects.nvDays", "effects.pe",
    "effects.ea", "effects.lastDay", "effects.exSeen",
    -- drain: every hour clock counts back down while its cause is absent and the smoothed BMI clock keeps its anchor and
    -- largest progress, so a restart keeps a recovering ceiling and neither re-anchors nor lets it fall. mask,
    -- recovering, the fractions, the target, the rate, starvedH and recentKcal are derived.
    "drain.bmi0", "drain.naH", "drain.feH", "drain.fedAgeH", "drain.acuteH",
    "drain.stH", "drain.dhH", "drain.bClose", "drain.bRate", "drain.pAt", "drain.pS", "drain.dPrev",
    "drain.scH", "drain.bbH", "drain.plH",
    "drain.spell", -- the meal spell: a refeed's fed spell survives a restart
    -- reconciliation: the baseline is re-seeded at first sight, since player save and global table are written apart (#2098)
    "reconcile.count", "monotony", "moodLast", -- monotony (NR_Server_Intake IN.atEat, K.monotony): copied whole, healed at the eat; moodLast: the mood floors' last targets, so a reconnect reads them as the player left them
    "hedonics", -- the plain-energy ring (K.hedonics), copied whole, healed by K.hedonics.heal
}

function K.store.split(path)
    local out = {}
    local pos = 1
    local len = string.len(path)
    while pos <= len + 1 do
        local stop = string.find(path, ".", pos, true)
        if stop == nil then
            stop = len + 1
        end
        out[#out + 1] = string.sub(path, pos, stop - 1)
        pos = stop + 1
    end
    return out
end

-- Built once at load.
function K.store.compile(paths)
    local out = {}
    for i = 1, #paths do
        out[i] = K.store.split(paths[i])
    end
    return out
end

K.store.SEGS = K.store.compile(K.store.INPUTS)

function K.store.copy(v)
    if type(v) ~= "table" then
        return v
    end
    local out = {}
    for k, x in pairs(v) do
        out[k] = K.store.copy(x)
    end
    return out
end

-- The identity fields only; the adapters lay the sub-tables at first sight.
function K.store.new(username, worldAgeHours)
    local r = {}
    r.username = username
    r.firstSeen = worldAgeHours
    r.lastSeen = worldAgeHours
    r.resets = 0 -- a count: no respawn yet
    r.dead = false
    return r
end

-- The last sight, else the first, else 0; every clock it stamps is an input the copy then overwrites.
function K.store.ageOf(raw)
    if type(raw.lastSeen) == "number" then
        return raw.lastSeen
    end
    if type(raw.firstSeen) == "number" then
        return raw.firstSeen
    end
    return 0 -- the world's start, a stamp the copy overwrites; no row needed
end

-- The stored body rb is healed in place first, as K.heal.body heals in memory: a non-finite number saves as JSON null
-- and reads back absent, so without the heal one bad field cost the whole record. A sex other than 1 or 2 reads 1 (any
-- other index stops every minute). P nil reads K.strength.DEFAULTS, so a tuned server's cap holds.
function K.store.bodyBase(rb, ageH, specific, P)
    if rb.sex == nil or (type(rb.sex) == "number" and rb.sex ~= 1 and rb.sex ~= 2) then
        rb.sex = 1
    end
    local sex = 1 -- K.body's sex index: 1 male, 2 female
    if rb.sex == 2 then
        sex = 2 -- K.body's female index
    end
    local spec = K.body.create(nil, nil, P or K.strength.DEFAULTS, K.body.effSex(sex, specific))
    K.store.healLeaf(rb, "fm", spec.fm)
    K.store.healLeaf(rb, "lm", spec.lm)
    local lastAgeH = K.store.healLeaf(rb, "lastAgeH", ageH)
    return K.body.new(spec, sex, lastAgeH)
end

-- Returns t[k] when finite, else v; a value of another type is left for K.store.checkLeaf to reject.
function K.store.healLeaf(t, k, v)
    local x = t[k]
    if x == nil or (type(x) == "number" and not K.finite(x)) then
        t[k] = v
    end
    if K.finite(t[k]) then
        return t[k]
    end
    return v
end

function K.store.nutrientKeys(order, rn)
    if order ~= nil then
        return order
    end
    local out = {}
    for k, v in pairs(rn) do
        K.store.addKey(out, k, v)
    end
    return out
end

function K.store.addKey(out, k, v)
    if type(v) == "table" then
        out[#out + 1] = k
    end
end

function K.store.defaults(rec, raw, order, specific, P)
    if type(raw.stomach) == "table" then
        rec.stomach = K.stomach.new() -- an empty stomach (ruling 11c-15); the stored buffer and liquid lane overwrite it
    end
    if type(raw.pool) == "table" then
        rec.pool = K.vector.new()
    end
    if type(raw.nutrients) == "table" then
        rec.nutrients = K.nutrients.newState({ ORDER = K.store.nutrientKeys(order, raw.nutrients) })
    end
    if type(raw.body) == "table" then
        rec.body = K.store.bodyBase(raw.body, K.store.ageOf(raw), specific, P)
    end
    if type(raw.acute) == "table" then
        rec.acute = K.acute.new(K.store.ageOf(raw))
    end
    if type(raw.fluids) == "table" then
        rec.fluids = K.fluids.new(nil, nil, nil)
        rec.fluids.thirstTarget = nil
    end
    if type(raw.effects) == "table" then
        rec.effects = K.effects.new()
        rec.effects.intoxTarget = nil
    end
    if type(raw.reconcile) == "table" then
        rec.reconcile = {}
    end
    if type(raw.drain) == "table" then
        rec.drain = K.drain.new()
    end
    return rec
end

function K.store.overlay(dst, src, segs, i)
    local seg = segs[i]
    if seg ~= "*" then
        K.store.overlayKey(dst, src, seg, segs, i)
        return dst
    end
    for k, _ in pairs(dst) do
        K.store.overlayKey(dst, src, k, segs, i)
    end
    return dst
end

-- The walk descends only where both sides hold a table; a missing stored value keeps the default.
function K.store.overlayKey(dst, src, k, segs, i)
    local sv = src[k]
    if sv == nil then
        return
    end
    if i == #segs then
        K.store.checkLeaf(dst[k], sv, k)
        dst[k] = K.store.copy(sv)
        return
    end
    local dv = dst[k]
    if type(sv) ~= "table" or type(dv) ~= "table" then
        return
    end
    K.store.overlay(dv, sv, segs, i + 1)
end

-- A stored input must have its default's type, and a lazily laid one be a number, boolean or table; anything else
-- raises, and the server lays a fresh record (NR_Server_Store's S.load), never one every step fails on.
function K.store.checkLeaf(dv, sv, k)
    local t = type(sv)
    if dv ~= nil and t ~= type(dv) then
        error("store: input " .. tostring(k) .. " is a " .. t .. ", not a " .. type(dv))
    end
    if dv == nil and t ~= "number" and t ~= "boolean" and t ~= "table" then
        error("store: input " .. tostring(k) .. " is a " .. t)
    end
end

-- The four fields Metabolism reads before the Nutrients minute refreshes them, each through the kernel's own function.
function K.store.recompute(rec, records)
    local n = rec.nutrients
    if n ~= nil then
        n.ironGrade = K.nutrients.gradeOf(n, "iron")
        K.store.recomputeReplete(n, records)
    end
    if rec.acute ~= nil then
        rec.acute.g = K.acute.glycG(rec.acute)
    end
    if rec.fluids ~= nil and rec.body ~= nil then
        rec.fluids.dehydPct = K.fluids.dehydPct(rec.fluids, rec.body.fm + rec.body.lm + rec.body.lx, 0)
    end
end

-- nil records leaves it: no global read.
function K.store.recomputeReplete(n, records)
    if records ~= nil then
        n.allReplete = K.nutrients.allRepleteOf(n, records)
    end
end

-- With no stored stamp the resting expenditure stands for the closed day's kcal, so the first close is not a 0 kcal day.
function K.store.closeDefault(rec)
    if rec.body ~= nil and type(rec.body.inDayClosed) ~= "number" then
        rec.body.inDayClosed = K.energy.ree(rec.body.lm)
    end
end

-- order nil reads the stored state's own keys; records is passed by the caller, never read from a global; specific and
-- P are for the default body. A non-table raw reads nil.
function K.store.load(raw, order, records, specific, P)
    if type(raw) ~= "table" then
        return nil
    end
    local rec = K.store.new(raw.username, raw.firstSeen)
    K.store.defaults(rec, raw, order, specific, P)
    if type(raw.satiety) == "table" then
        rec.satiety = {} -- the stored M, S, L, t and nicH overwrite it
    end
    local segs = K.store.SEGS
    for i = 1, #segs do
        K.store.overlay(rec, raw, segs[i], 1)
    end
    if rec.stomach ~= nil then
        rec.stomachFill = K.stomach.fill(rec.stomach)
    end
    K.store.closeDefault(rec)
    K.store.recompute(rec, records)
    return rec
end

-- Every key of target is cleared and the loaded keys set on it, so a held handle reads the loaded record; raw may be
-- target itself (load copies every input deep before the clear).
function K.store.fillInPlace(target, raw, order, records, specific, P)
    local rec = K.store.load(raw, order, records, specific, P)
    if rec == nil then
        return nil
    end
    local keys = {}
    for k, _ in pairs(target) do
        keys[#keys + 1] = k
    end
    for i = 1, #keys do
        target[keys[i]] = nil
    end
    for k, v in pairs(rec) do
        target[k] = v
    end
    return target
end

function K.store.pick(dst, src, segs, i)
    local seg = segs[i]
    if seg ~= "*" then
        K.store.pickKey(dst, src, seg, segs, i)
        return dst
    end
    for k, _ in pairs(src) do
        K.store.pickKey(dst, src, k, segs, i)
    end
    return dst
end

-- A table is descended, its counterpart in dst laid on the way.
function K.store.pickKey(dst, src, k, segs, i)
    local sv = src[k]
    if sv == nil then
        return
    end
    if i == #segs then
        dst[k] = K.store.copy(sv)
        return
    end
    if type(sv) ~= "table" then
        return
    end
    if type(dst[k]) ~= "table" then
        dst[k] = {}
    end
    K.store.pick(dst[k], sv, segs, i + 1)
end

-- The contract's oracle: the live record is pruned only by the first-sight load.
function K.store.inputsOnly(record)
    local out = {}
    local segs = K.store.SEGS
    for i = 1, #segs do
        K.store.pick(out, record, segs[i], 1)
    end
    return out
end

-- getServerName is not sanitised (T1102.6): a name holding .. would make every write nil.
function K.store.safeName(s)
    local out = {}
    for i = 1, string.len(s) do
        local c = string.sub(s, i, i)
        if string.find(c, "^[%w_%-]$") ~= nil then
            out[#out + 1] = c
        else
            out[#out + 1] = "_"
        end
    end
    if #out == 0 then
        return "default"
    end
    return table.concat(out)
end

function K.store.hex4(b)
    return K.hexDigits(b, 4)
end

-- string.byte answers UTF-16 code units on Kahlua (T1102.8), so a fixed four-digit width keeps every name a distinct
-- file name.
function K.store.hexName(username)
    local out = {}
    for i = 1, string.len(username) do
        out[i] = K.store.hex4(string.byte(username, i))
    end
    return table.concat(out)
end

-- A tie reads "a"; a non-number gen reads absent. The writer opens the OTHER file of the pair, never this one
-- (getFileWriter truncates at the call, T1102.4).
function K.store.newest(a, b)
    a = K.store.withGen(a)
    b = K.store.withGen(b)
    if b == nil then
        if a == nil then
            return nil
        end
        return "a"
    end
    if a == nil or b.gen > a.gen then
        return "b"
    end
    return "a"
end

-- nil last: never, so due.
function K.store.due(last, now, gapMs)
    return last == nil or now - last >= gapMs
end

-- The index's unit.
function K.store.seconds(ms)
    return math.floor(ms / 1000) -- milliseconds a second; no row needed
end

-- K.store.newest's guard.
function K.store.withGen(d)
    if d == nil or type(d.gen) ~= "number" then
        return nil
    end
    return d
end

-- Half a gap from K.view.pushOffset's phase, so players first seen together after a boot spread their saves.
function K.store.savePhase(username, gapMs)
    return (K.nameHash(username) + math.floor(gapMs / 2)) % gapMs
end

-- The first save falls savePhase ms after now.
function K.store.firstLast(username, now, gapMs)
    return now - gapMs + K.store.savePhase(username, gapMs)
end
