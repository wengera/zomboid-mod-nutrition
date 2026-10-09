-- NR_Kernel_Store.lua -- the persisted record's contract (Plan 8, ruling 5; spec § 4.8): the closed list of
-- INPUT paths a save holds, and the load that keeps a stored record's inputs and rebuilds everything else.
-- An input is a field a slow-clock step READS from the previous
-- minute and writes back (an accumulator, a clock stamp, a hysteresis or latch state, a once-per-character
-- draw, a creation constant, a day-close stamp held until the next close): no step can recompute it. A
-- derived field is one a step recomputes from the inputs before any step reads it, or recomputes every
-- minute and reads only as a one-minute-lag neutral; load drops it, so a formula change touches no save.
-- The classification below was read off each owning step (named per group); a reviewer diffs it there.
-- Paths are dotted; a `*` segment stands for every key of the table at that level (every nutrient key of
-- the order, every vector key, every ring slot). A path whose value is a table (a ring slot of bandWeek) is
-- copied deep.
-- load(raw, order) builds a fresh record from the kernel constructors (K.store.new for the identity; for each
-- sub-table raw carries, its own kernel constructor) and copies every INPUT path present in raw over it, so a
-- missing input keeps the constructor's default and an unknown or derived field never survives. The copy is
-- idempotent. After a load and until the first slow minute rebuilds them, the derived fields read their
-- constructor's neutral values (the mirror's dmod, rmod, energyState, band, dehydPct, iu, ... and the
-- effects set), except stomachFill, which load recomputes from the stomach's inputs (the physical fill and the writer's
-- fallback; the writer's F is W.satietyF), and fluids.thirstTarget and effects.intoxTarget, which load leaves nil: nil is the writer's no-write
-- for both, where the constructors' 0 would drive THIRST or INTOXICATION to 0.
-- Pure: Lua tables in, Lua tables out, no Java. Slow-clock and join-time code with no fast region. This file
-- sorts before NR_Kernel_Strength.lua, NR_Kernel_Vector.lua and NR_Kernel_View.lua and after the body,
-- acute, effects, fluids, nutrients and stomach kernels; every K.* reference outside K.store is at call time.
local K = NutritionRevamp.kernel
K.store = {}


-- The closed list of persisted paths, grouped by the step that owns each field.
K.store.INPUTS = {
    -- identity (NR_Server_Store, NR_Server_Players): the key, the first and last world age seen, the respawn
    -- count, the death flag
    "username", "firstSeen", "lastSeen", "resets", "dead",
    -- satiety (Plan 11c; NR_Server_Writer, NR_Server_Metabolism): the meal pool P (weighted kcal), which the writer
    -- seeds from HUNGER when absent or non-finite, the acute suppression state S and the exercise lag L (kcal/day)
    "satiety.P", "satiety.S", "satiety.L", "satiety.t", -- t: the writer's last step age in game hours, read across a restart (Plan 11c close, ruling C-1)
    -- kinetics (NR_Server_Kinetics, K.stomach): the clock stamp the next minute's dtH reads, the liquid lane and the
    -- solid buffer (ingest and ingestLiquid add, drain empties), the absorbed pool (toPool accumulates; a diagnostic
    -- no step reads back, kept because it cannot be rebuilt)
    "kineticsAge", "stomach.liquid", "stomach.buffer.*", "pool.*",
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
    -- day's stamps held until the next close (inDayClosed, pPrevKg, and exKcalPrev, the closed day's exercise kcal)
    "body.inDay", "body.eeDay", "body.ebDay", "body.actKcalDay", "body.exKcalDay", "body.pDay", "body.carbDay",
    "body.lipDay", "body.alcDay", "body.inDayClosed", "body.pPrevKg", "body.exKcalPrev",
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
    -- fluids (K.fluids.intake, losses and clearance; the writer's sip fold): the water, sodium
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

-- A fresh record: the identity fields only (NR_Server_Store's S.new shape, which calls this). The sub-tables
-- are laid by their adapters at first sight.
function K.store.new(username, worldAgeHours)
    local r = {}
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
-- factor, responder and clock (a saved body always holds them: K.body.new lays them all). A sex other than 2
-- builds as 1; the copy then restores the stored value.
function K.store.bodyBase(rb)
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
        rec.stomach = K.stomach.new() -- an empty stomach (ruling 11c-15); the stored buffer and liquid lane overwrite it
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

-- The four fields Metabolism reads before the Nutrients minute refreshes them, recomputed from the loaded
-- inputs, each through the kernel's own function: nutrients.ironGrade (K.nutrients.gradeOf), nutrients.allReplete
-- (K.nutrients.allRepleteOf, read off the records argument), acute.g (K.acute.glycG) and fluids.dehydPct
-- (K.fluids.dehydPct at the body mass, no pending water). A part the record lacks keeps its constructor's value.
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
        rec.fluids.dehydPct = K.fluids.dehydPct(rec.fluids, rec.body.fm + rec.body.lm, 0)
    end
end

-- allReplete of a loaded nutrient state when the records argument is present (nil leaves it, no global read).
function K.store.recomputeReplete(n, records)
    if records ~= nil then
        n.allReplete = K.nutrients.allRepleteOf(n, records)
    end
end

-- A loaded body with no stored closed-day stamp reads the resting expenditure as that day's absorbed kcal,
-- the value Nutrients' close already uses for a body with no closed day (K.energy.ree), so the first close is
-- not read as a 0 kcal day. (A stored stamp, copied from the record, is kept.)
function K.store.closeDefault(rec)
    if rec.body ~= nil and type(rec.body.inDayClosed) ~= "number" then
        rec.body.inDayClosed = K.energy.ree(rec.body.lm)
    end
end

-- Load a stored record into a fresh record: the constructors' defaults, every INPUTS path present in raw
-- copied over them, the stomach fill and the four read-before-refresh fields recomputed. order is the nutrient key list (NR.data.records.ORDER); nil reads the stored state's own
-- keys. A non-table raw reads nil. records is the nutrient data (NR.data.records),
-- passed by the caller and never read from a global.
function K.store.load(raw, order, records)
    if type(raw) ~= "table" then
        return nil
    end
    local rec = K.store.new(raw.username, raw.firstSeen)
    K.store.defaults(rec, raw, order)
    if type(raw.satiety) == "table" then
        rec.satiety = {} -- the stored P, S, L and t overwrite it
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

-- Load raw and lay the result into target in place (ruling T4-1): every key target holds is cleared and the
-- loaded record's keys are set on it, so a handle held on target reads the loaded record with no re-point. raw may be target itself: load copies every input deep before the
-- clear. Returns target, or nil with target untouched when raw is not a table.
function K.store.fillInPlace(target, raw, order, records)
    local rec = K.store.load(raw, order, records)
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
-- complement is what load drops). The live record is pruned only by the first-sight load (fillInPlace); this is the contract's oracle.
function K.store.inputsOnly(record)
    local out = {}
    local segs = K.store.SEGS
    for i = 1, #segs do
        K.store.pick(out, record, segs[i], 1)
    end
    return out
end

-- A file-safe name: letters, digits, _ and - kept, any other character _, an empty name "default". The server name
-- passes through it (getServerName is not sanitised, T1102.6: a name holding .. would make every write nil).
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

K.store.HEX = "0123456789abcdef" -- the digit lookup: %x on a float raises on Kahlua (K.json.ctl's rule)

-- One code unit (0-65535) as four lower-case hex digits, built from the lookup string.
function K.store.hex4(b)
    local out = {}
    local d = 4096 -- 16^3, the first digit's place value
    for i = 1, 4 do
        local q = math.floor(b / d) % 16 + 1
        out[i] = string.sub(K.store.HEX, q, q)
        d = d / 16
    end
    return table.concat(out)
end

-- A username as lower-case hex, four digits a code unit: string.byte answers UTF-16 code units on Kahlua
-- (T1102.8), so a fixed width keeps every name a distinct file name (two digits a unit let U+0123 "A" and
-- U+0012 U+0341 both write 12341).
function K.store.hexName(username)
    local out = {}
    for i = 1, string.len(username) do
        out[i] = K.store.hex4(string.byte(username, i))
    end
    return table.concat(out)
end

-- One index entry into out when it is offline and unseen for more than keepS seconds (K.store.expired's body:
-- a pairs loop whose body ends in an if leaves that end unexecuted under the line hook, so the test lives here).
function K.store.addExpired(out, u, seen, isOnline, nowS, keepS)
    if isOnline == nil and type(seen) == "number" and nowS - seen > keepS then
        out[#out + 1] = u
    end
end

-- The usernames of an index { username = lastSeen seconds } not online and unseen for more than keepS seconds,
-- sorted; keepS 0 or less keeps everything.
function K.store.expired(index, nowS, keepS, online)
    local out = {}
    if keepS <= 0 then
        return out
    end
    for u, seen in pairs(index) do
        K.store.addExpired(out, u, seen, online[u], nowS, keepS)
    end
    table.sort(out)
    return out
end

-- Which of a pair of decoded files { gen = n, ... } is the newer: "a", "b", or nil when both are absent; a tie reads
-- "a"; a file whose gen is not a number reads as absent, so no comparison can raise. The store's writer opens the
-- OTHER file of the pair, never this one (getFileWriter truncates at the call, T1102.4).
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

-- Whether a gap of gapMs has passed since last (nil: never, so due).
function K.store.due(last, now, gapMs)
    return last == nil or now - last >= gapMs
end

-- A millisecond stamp as whole seconds (the index's unit).
function K.store.seconds(ms)
    return math.floor(ms / 1000) -- milliseconds a second; no row needed
end

-- A keep in real days as seconds.
function K.store.keepSeconds(days)
    return days * 86400 -- seconds a day; no row needed
end

-- A decoded file when its gen is a number, else nil (K.store.newest's guard).
function K.store.withGen(d)
    if d == nil or type(d.gen) ~= "number" then
        return nil
    end
    return d
end

-- A player's save phase in [0, gapMs): a hash of the username (string.byte's code units), half a gap away from
-- K.view.pushOffset's push phase, so the saves of players first seen together after a boot spread over the gap
-- instead of falling into one drain.
function K.store.savePhase(username, gapMs)
    local h = 0
    for i = 1, string.len(username) do
        h = (h * 31 + string.byte(username, i)) % 1000003 -- the push offset's hash: a prime modulus, no row needed
    end
    return (h + math.floor(gapMs / 2)) % gapMs
end

-- The lastWrite a player's first save is timed from: one gap before now plus its phase, so the first save falls
-- savePhase ms after now (K.store.due).
function K.store.firstLast(username, now, gapMs)
    return now - gapMs + K.store.savePhase(username, gapMs)
end
