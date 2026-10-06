-- NR_Kernel_Store.lua -- the persisted record's contract (Plan 8, ruling 5; spec § 4.8): the version field,
-- the closed list of INPUT paths a save holds, and the load that migrates an older record by keeping its
-- inputs and rebuilding everything else. An input is a field a slow-clock step READS from the previous
-- minute and writes back (an accumulator, a clock stamp, a hysteresis or latch state, a once-per-character
-- draw, a creation constant, a day-close stamp held until the next close): no step can recompute it. A
-- derived field is one a step recomputes from the inputs before any step reads it, or recomputes every
-- minute and reads only as a one-minute-lag neutral; load drops it, so a formula change needs no migration.
-- The classification below was read off each owning step (named per group); a reviewer diffs it there.
-- Paths are dotted; a `*` segment stands for every key of the table at that level (every nutrient key of
-- the order, every vector key, every ring slot). A path whose value is a table (a ring slot of bandWeek) is
-- copied deep.
-- load(raw, order) builds a fresh record from the kernel constructors (K.store.new for the identity; for each
-- sub-table raw carries, its own kernel constructor) and copies every INPUT path present in raw over it, so a
-- missing input keeps the constructor's default and an unknown or derived field never survives. A v1 record
-- (no `v`, or v = 1) and a v2 record pass through the same copy: the copy IS the migration, and it is
-- idempotent. After a load and until the first slow minute rebuilds them, the derived fields read their
-- constructor's neutral values (the mirror's dmod, rmod, energyState, band, dehydPct, iu, ... and the
-- effects set), except stomachFill, which load recomputes from the stomach's inputs (the fast clock's hunger
-- reads it every tick), and fluids.thirstTarget and effects.intoxTarget, which load leaves nil: nil is the
-- fast clock's pass-through for both, where the constructors' 0 would drive THIRST or INTOXICATION to 0.
-- Pure: Lua tables in, Lua tables out, no Java. Slow-clock and join-time code with no fast region. This file
-- sorts before NR_Kernel_Strength.lua, NR_Kernel_Vector.lua and NR_Kernel_View.lua and after the body,
-- acute, effects, fluids, nutrients and stomach kernels; every K.* reference outside K.store is at call time.
local K = NutritionRevamp.kernel
K.store = {}

-- The record version: 1 is Plan 1's identity-only S.new with the sub-tables laid lazily beside it; 2 is
-- the inputs-only contract below.
K.store.VERSION = 2 -- schema version, no row needed

-- The closed list of persisted paths, grouped by the step that owns each field.
K.store.INPUTS = {
    -- identity (NR_Server_Store, NR_Server_Players): the version field the save holds (load rewrites it to
    -- VERSION after the copy), the key, the first and last world age seen, the respawn count, the death flag
    "v", "username", "firstSeen", "lastSeen", "resets", "dead",
    -- kinetics (NR_Server_Kinetics, K.stomach): the clock stamp the next minute's dtH reads, the buffer and
    -- its bulk (ingest adds, empty drains), the absorbed pool (toPool accumulates; a diagnostic no step reads
    -- back, kept because it cannot be rebuilt)
    "kineticsAge", "stomach.bulk", "stomach.buffer.*", "pool.*",
    -- nutrients, per key (K.nutrients.minute, K.interact.two): the pools p and p2; the grade g, which the
    -- next minute reads as gradeHyst's previous grade, and gl, the grade it left; ah, the hours at the grade
    -- (the scurvy, beriberi and pellagra onsets read g == 4 with ah, so a dropped g would re-zero them); the
    -- excess accumulators e24 and ext, the acute flag's hours ax and its rung axr; B12's damage hours dmg;
    -- the iron store and haem compartments S and H and calcium's bone, laid lazily by K.interact.two (a
    -- dropped S re-seeds iron replete). x, the excess rung, is recomputed every minute: derived.
    "nutrients.*.p", "nutrients.*.p2", "nutrients.*.g", "nutrients.*.gl", "nutrients.*.ah", "nutrients.*.e24",
    "nutrients.*.dmg", "nutrients.*.ext", "nutrients.*.ax", "nutrients.*.axr", "nutrients.*.S", "nutrients.*.H",
    "nutrients.*.bone",
    -- nutrients, the state's own (K.nutrients.minute, NR_Server_Nutrients): the epoch counter the step bumps;
    -- the adapter's clock stamp and the day index its close reads. allReplete, ironGrade, anaemia and
    -- vitDClinical are recomputed at the end of every minute: derived.
    "nutrients.epoch", "nutrients.lastAgeH", "nutrients.lastDayIndex",
    -- body, the creation constants (K.body.new, NR_Server_Metabolism.ensureBody): the masses at birth, the
    -- disuse and fat references, the Strength level at birth, sex, the responder constant, the creation
    -- carry factor and the birth world age
    "body.fm0", "body.lm0", "body.lm0dis", "body.fmRef", "body.l0", "body.sex", "body.r", "body.traitCarry",
    "body.bornAge",
    -- body, the masses and clocks (K.partition, K.energy, NR_Server_Metabolism, NR_Server_Strength): fat and
    -- lean mass, the day index and the last close, the metabolism and strength clock stamps
    "body.fm", "body.lm", "body.dayIndex", "body.lastAgeH", "body.lastCloseAgeH", "body.strAgeH",
    -- body, the day accumulators (K.energy.minute and intake, zeroed by K.partition.closeDay) and the closed
    -- day's stamps held until the next close (inDayClosed, pPrevKg)
    "body.inDay", "body.eeDay", "body.ebDay", "body.actKcalDay", "body.exKcalDay", "body.pDay", "body.carbDay",
    "body.lipDay", "body.alcDay", "body.inDayClosed", "body.pPrevKg",
    -- body, the 7-day rings (K.partition.closeDay pushes; K.training.closeDay shifts bandWeek)
    "body.eb7.*", "body.mass7.*", "body.p7.*", "body.carb7.*", "body.lip7.*", "body.bandWeek.*",
    -- body, adaptation (K.aerobic.tacDay steps tac from its last value at each close; K.energy.atStep steps
    -- at): both are multi-day accumulators, never recomputed from the masses
    "body.tac", "body.at",
    -- body, training (K.training.sample, event, decay and closeDay): the decaying volumes and the day's
    -- MET-minutes and band minutes
    "body.vStr", "body.vHyp", "body.vStrHigh", "body.metMinDay", "body.band1Day", "body.band2Day",
    -- body, strength (K.strength.neuralStep, closeDay and policy): the neural factor, the held peak and its
    -- day, the 14-day history, the cumulative deficit, the disuse day count; the shown level and its rise
    -- hold and last fall, which the policy reads back as its previous state
    "body.n", "body.nPeak", "body.tPeakD", "body.nHist.*", "body.cumDef", "body.tDisuse", "body.shownL",
    "body.riseHeldH", "body.lastFallAge",
    -- acute (K.acute.*, NR_Server_Nutrients.ensure and closeDay): the gut lane; caffeine's load, rate mean,
    -- tolerance and low-hours, the slow-metaboliser draw; alcohol's load, peak and hangover; glycogen and
    -- blood glucose (each relaxes from its last value); the sleep state, its bout, gap and window; the
    -- refeeding close's counts, mass window, BMI, risk, day count and event; the exercise and cold EMAs and
    -- the vigorous latch; the retinol EMA; the adapter's 7-day alcohol mean, day alcohol, last fed age and the
    -- band baselines. bac, g, wd, wdH, circ, frozen, iu, iuSleep and av are recomputed each minute: derived.
    "acute.gutAlc", "acute.gutCaf", "acute.caf", "acute.cafMean", "acute.cafTol", "acute.cafLowH",
    "acute.slowMet", "acute.alc", "acute.alcPeak", "acute.hang", "acute.hangH", "acute.glyc", "acute.bg",
    "acute.awakeH", "acute.debtH", "acute.sleptH", "acute.boutH", "acute.gapH", "acute.winStartH",
    "acute.winSleptH", "acute.S", "acute.starvedDays", "acute.lowDay", "acute.mass90max", "acute.mass90ageH",
    "acute.bmi", "acute.refeedRisk", "acute.refeedDayN", "acute.refeedEvent", "acute.exEma",
    "acute.lastVigAgeH", "acute.boutVig", "acute.coldH", "acute.retEma", "acute.alc7", "acute.alcDayG",
    "acute.lastFedAgeH", "acute.lastB1", "acute.lastB2",
    -- fluids (K.fluids.intake, losses and clearance; NR_Server_Fast's autoDrink bracket): the water, sodium
    -- and potassium balances, the once-per-character sweat draws, the 6 h EMAs and the pending sip. dehydPct,
    -- c, naPlasma, thirstTarget, sweatActive, sweatLmin, viewPct and fv are recomputed each minute: derived.
    "fluids.water", "fluids.na", "fluids.k", "fluids.sweatK", "fluids.naSweat", "fluids.sweat6h",
    "fluids.loss6h", "fluids.autoDrop",
    -- effects (NR_Server_Effects, K.effects): the bus flag that survives a save (Plan 5 T10) and the set's
    -- epoch counter; which band traits the mod itself added (a lost own flag orphans the trait); the
    -- night-vision accumulator; the day close's protein-energy grade, energy availability and day, and the
    -- exercise kcal the next close reads. The coefficient set, its key and the per-minute scalars are rebuilt
    -- by the first minute (the default key forces a compose): derived.
    "effects.dirty", "effects.epoch", "effects.own.nv", "effects.own.ss", "effects.nvDays", "effects.pe",
    "effects.ea", "effects.lastDay", "effects.exSeen",
    -- reconciliation (NR_Server_Reconcile, Plan 8 Task 4): the landing count. The baseline is re-seeded from
    -- the vanilla stores at first sight, since the player save and the global table are written apart (#2098):
    -- dropped.
    "reconcile.count",
}

-- Split a dotted path into its segments (a fresh array of strings).
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

-- Every INPUTS path as its segment array, built once at load.
function K.store.compile(paths)
    local out = {}
    for i = 1, #paths do
        out[i] = K.store.split(paths[i])
    end
    return out
end

K.store.SEGS = K.store.compile(K.store.INPUTS)

-- A deep copy of v: a table is copied key by key, anything else is returned as is.
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

-- A fresh record: the identity fields only, at version VERSION (NR_Server_Store's S.new shape, which calls
-- this). The sub-tables are laid by their adapters at first sight.
function K.store.new(username, worldAgeHours)
    local r = {}
    r.v = K.store.VERSION
    r.username = username
    r.firstSeen = worldAgeHours
    r.lastSeen = worldAgeHours
    r.resets = 0 -- a count: no respawn yet
    r.dead = false
    return r
end

-- The world age a constructor stamps its clocks with: the record's last sight, else its first, else 0 (the
-- world's start; every clock the constructor stamps is an input the copy then overwrites).
function K.store.ageOf(raw)
    if type(raw.lastSeen) == "number" then
        return raw.lastSeen
    end
    if type(raw.firstSeen) == "number" then
        return raw.firstSeen
    end
    return 0 -- the world's start, a stamp the copy overwrites; no row needed
end

-- The default body the inputs are copied over: K.body.new at the stored masses, sex, Strength level, carry
-- factor, responder and clock, or nil when the stored body lacks a mass, the sex or the clock (the
-- Metabolism adapter then makes a fresh body at first sight). A sex other than 2 builds as 1; the copy then
-- restores the stored value.
function K.store.bodyBase(rb)
    if type(rb.fm) ~= "number" or type(rb.lm) ~= "number" then
        return nil
    end
    if type(rb.sex) ~= "number" or type(rb.lastAgeH) ~= "number" then
        return nil
    end
    local sex = 1 -- K.body's sex index: 1 male, 2 female
    if rb.sex == 2 then
        sex = 2 -- K.body's female index
    end
    return K.body.new(rb.fm + rb.lm, sex, {}, rb.l0, rb.traitCarry, rb.r, rb.lastAgeH)
end

-- The nutrient keys a load lays: the order when given, else every table-valued key of the stored state.
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

-- Append k to the key list out when its value v is a table (a nutrient key's state).
function K.store.addKey(out, k, v)
    if type(v) == "table" then
        out[#out + 1] = k
    end
end

-- The default sub-tables for every sub-table raw carries, each from its own kernel constructor.
function K.store.defaults(rec, raw, order)
    if type(raw.stomach) == "table" then
        rec.stomach = K.stomach.new()
    end
    if type(raw.pool) == "table" then
        rec.pool = K.vector.new()
    end
    if type(raw.nutrients) == "table" then
        rec.nutrients = K.nutrients.newState({ ORDER = K.store.nutrientKeys(order, raw.nutrients) })
    end
    if type(raw.body) == "table" then
        rec.body = K.store.bodyBase(raw.body)
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
    return rec
end

-- One segment of a load's copy: dst and src at the same level; a `*` walks every key dst holds there.
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

-- One key of a load's copy: at the last segment the stored value is copied (deep) over the default; above
-- it the walk descends only where both sides hold a table. A missing stored value keeps the default.
function K.store.overlayKey(dst, src, k, segs, i)
    local sv = src[k]
    if sv == nil then
        return
    end
    if i == #segs then
        dst[k] = K.store.copy(sv)
        return
    end
    local dv = dst[k]
    if type(sv) ~= "table" or type(dv) ~= "table" then
        return
    end
    K.store.overlay(dv, sv, segs, i + 1)
end

-- Load a stored record (any version) into a fresh version-VERSION record: the constructors' defaults, every
-- INPUTS path present in raw copied over them, v set, the stomach fill recomputed. order is the nutrient
-- key list (NR.data.records.ORDER); nil reads the stored state's own keys. A non-table raw reads nil.
function K.store.load(raw, order)
    if type(raw) ~= "table" then
        return nil
    end
    local rec = K.store.new(raw.username, raw.firstSeen)
    K.store.defaults(rec, raw, order)
    local segs = K.store.SEGS
    for i = 1, #segs do
        K.store.overlay(rec, raw, segs[i], 1)
    end
    rec.v = K.store.VERSION
    if rec.stomach ~= nil then
        rec.stomachFill = K.stomach.fill(rec.stomach)
    end
    return rec
end

-- One segment of the inputs-only walk: dst built as it goes; a `*` walks every key src holds there.
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

-- One key of the inputs-only walk: the last segment copies the value (deep); above it a table is descended,
-- its counterpart in dst laid on the way.
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

-- The table a save would hold: a fresh table of the INPUTS paths present in record, nothing else (the
-- complement is what load drops). The live record is not pruned (Task 4); this is the contract's oracle.
function K.store.inputsOnly(record)
    local out = {}
    local segs = K.store.SEGS
    for i = 1, #segs do
        K.store.pick(out, record, segs[i], 1)
    end
    return out
end

-- Whether the dotted path names an input or lies under one: some INPUTS path matches its leading segments,
-- a `*` matching any one segment.
function K.store.isInput(path)
    local p = K.store.split(path)
    local segs = K.store.SEGS
    for i = 1, #segs do
        if K.store.matches(segs[i], p) then
            return true
        end
    end
    return false
end

-- Whether pattern segments pat match the leading segments of p.
function K.store.matches(pat, p)
    if #p < #pat then
        return false
    end
    for j = 1, #pat do
        if pat[j] ~= "*" and pat[j] ~= p[j] then
            return false
        end
    end
    return true
end
