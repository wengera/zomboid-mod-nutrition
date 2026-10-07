-- NR_Server_Bench.lua -- the cost-budget entry point (spec § 6, Plan 2 entry gate).
-- bench.global calls a resolved global N times with no arguments; the fast kernel step needs a
-- fully filled input and output, so this file owns one filled input, one output and the constants,
-- builds them once at file scope, and runs NutritionRevamp.kernel.fast.step once per call. The
-- tables are reused, never re-allocated, so bench.global measures the step and not a constructor.
-- This file exists only for the § 6 cost reading and ships with the mod. It is not a kernel file:
-- it defines no NutritionRevamp.kernel function (it only calls the kernel's K.fast.* helpers). It
-- names no Java global -- at file scope or in its functions -- so it loads with no engine (it only
-- reads NutritionRevamp.kernel, loaded before it).
local NR = NutritionRevamp
local K = NR.kernel

-- Built once: the constants, one output and one input filled to a steady-state awake tick.
local BENCH_C = K.fast.defaults()
local BENCH_OUT = K.fast.output()
local BENCH_INP = K.fast.input()

-- A steady-state awake update: one game-minute (M = 1, D = 24 -> sixty game-seconds), not asleep,
-- not a ghost, mid-range stats, the optional multipliers neutral except dmod and rmod (below), a real day length and a mid
-- fitness level. Every trait and flag K.fast.input() seeds false stays false, except the two Plan 5
-- ownership flags (fOwned, endFold) set below.
BENCH_INP.M = 1
BENCH_INP.D = 24
BENCH_INP.sd = 1
BENCH_INP.asleep = false
BENCH_INP.ghost = false
BENCH_INP.hunger = 0.3
BENCH_INP.thirst = 0.3
BENCH_INP.fatigue = 0.2
BENCH_INP.endurance = 1
BENCH_INP.stress = 0
BENCH_INP.anger = 0
BENCH_INP.idleness = 0
BENCH_INP.morale = 1
BENCH_INP.nicotine = 0
BENCH_INP.thermoFatigue = 1
BENCH_INP.thermoFluids = 1
BENCH_INP.endRegen = 1
BENCH_INP.recoveryMod = 1
BENCH_INP.bedFactor = 1
BENCH_INP.minutesPerDay = 60
BENCH_INP.fitnessLevel = 5
BENCH_INP.energyState = 1
BENCH_INP.rmod = 0.9
BENCH_INP.thirstTarget = 0.3
-- Plan 5 (Tasks 7, 11): the shipped steady state. The record owns FATIGUE (the writer runs with a slow sleep
-- pressure, a circadian term and an offset), the endurance fold is on and takes its regeneration arm (a one-tick regeneration
-- of 0.0005 at rmod 0.9), dmod and rmod sit off neutral, and a stress floor of 0.1 holds.
BENCH_INP.fOwned = true
BENCH_INP.fFrozen = false
BENCH_INP.fS = 0.3
BENCH_INP.fCirc = 0.05
BENCH_INP.fOff = 0.02
BENCH_INP.solAddH = 0
BENCH_INP.solMul = 1
BENCH_INP.endFold = true
BENCH_INP.endLast = 0.9995
BENCH_INP.dmod = 1.1
BENCH_INP.stressTarget = 0.1

-- One fast step over the reused tables; returns the output table. The target of bench.global.
function NR.bench_fast()
    K.fast.step(BENCH_INP, BENCH_OUT, BENCH_C)
    return BENCH_OUT
end

-- The filled input, for a test to read the steady-state tick it benchmarks.
function NR.bench_fast_input()
    return BENCH_INP
end

-- ===================================================================================================================
-- Plan 10c Task H2 (run x242; the STAGED copy release/hitch-x242 only; never mod/): sub-step and burst-source costs,
-- the store's save and request arm (H6's arm E) and the client tooltip bench. Every entry is test-only; every reading
-- is cost, not behaviour. getTimestampMs is a 1 ms clock: every figure is a total over many runs with its count.
-- The sub-block sites (SBT/SBA) sit in the staged NR_Server_Nutrients, _Metabolism, _Effects and _Strength copies,
-- one line each (line count unchanged); this file loads first among server/NR_Server_* so their file-scope
-- `NR.server.bench.sbT` reads resolve. Server work is gated on NR.isServer(); the client helpers (NR_H2C, the
-- NR_H6 receive probe) on isClient().
-- ===================================================================================================================
NR.server.bench = NR.server.bench or {}
local B = NR.server.bench

local function now()
    if getTimestampMs == nil then return 0 end
    return getTimestampMs()
end
B.now = now

local function isCl()
    if isClient == nil then return false end
    local ok, v = pcall(isClient)
    return ok and v == true
end

local function copyOf(v, depth)
    if type(v) ~= "table" then return v end
    if depth > 24 then return nil end
    local c = {}
    for k, x in pairs(v) do c[k] = copyOf(x, depth + 1) end
    return c
end
B.copyOf = copyOf

-- The clock counters (the driver paces on .minutes).
B.ticks = 0
B.minutes = 0

-- ---- accumulators: key -> ms, runs (a key is "<set>|<name>"; set is u:<username>, ghost or bench:<kind>) ------
B.acc = { ms = {}, runs = {} }
B.prof = { on = false, wrapped = false, wrappedNames = "" }
B.sbOn = false
B.curSet = "none"
B.benchSet = nil

local function add(key, d)
    local A = B.acc
    local m = A.ms[key]
    if m == nil then
        A.ms[key] = d
        A.runs[key] = 1
    else
        A.ms[key] = m + d
        A.runs[key] = A.runs[key] + 1
    end
end

-- The sub-block probe pair: sbT is nil unless both the profile and the sub-blocks are on, so an off site costs one
-- call and one compare.
function B.sbT()
    if B.sbOn and B.prof.on then return now() end
    return nil
end
function B.sbA(key, t0)
    if t0 == nil then return end
    add(B.curSet .. "|" .. key, now() - t0)
end

local function setOf(username)
    if B.benchSet ~= nil then return B.benchSet end
    local P = NR.server.players
    if P ~= nil and P.online ~= nil and username ~= nil and P.online[username] ~= nil then return "u:" .. tostring(username) end
    return "ghost"
end

-- The per-run record: a histogram per set (0..30 ms, 30 = 30 or more) and, for the real players only, a ring of
-- runs: username, ms, minute counter, Metabolism closes, Nutrients closes and Effects closes in the run.
B.RING_MAX = 4000
B.hist = {}
B.ring = { n = 0, u = {}, ms = {}, mn = {}, mc = {}, nc = {}, ec = {} }

local function statN(t, k)
    if t == nil or t.stats == nil then return 0 end
    local v = t.stats[k]
    if type(v) == "number" then return v end
    return 0
end

local function timedRun(fn)
    return function(u, p, r)
        if not B.prof.on then return fn(u, p, r) end
        local set = setOf(u)
        local prevSet = B.curSet
        B.curSet = set
        local MET, NUT, EFF = NR.server.metabolism, NR.server.nutrients, NR.server.effects
        local m0, n0, e0 = statN(MET, "days"), statN(NUT, "days"), statN(EFF, "closes")
        local t0 = now()
        fn(u, p, r)
        local d = now() - t0
        add(set .. "|__run", d)
        local h = B.hist[set]
        if h == nil then
            h = {}
            for i = 0, 30 do h[i] = 0 end
            B.hist[set] = h
        end
        local bucket = d
        if bucket > 30 then bucket = 30 end
        if bucket < 0 then bucket = 0 end
        h[bucket] = h[bucket] + 1
        if string.sub(set, 1, 2) == "u:" and B.ring.n < B.RING_MAX then
            local R = B.ring
            R.n = R.n + 1
            local i = R.n
            R.u[i] = u
            R.ms[i] = d
            R.mn[i] = B.minutes
            R.mc[i] = statN(MET, "days") - m0
            R.nc[i] = statN(NUT, "days") - n0
            R.ec[i] = statN(EFF, "closes") - e0
        end
        B.curSet = prevSet
    end
end

local function timedStep(name, fn)
    return function(a1, a2, a3, a4)
        if not B.prof.on then return fn(a1, a2, a3, a4) end
        local t0 = now()
        local r1, r2 = fn(a1, a2, a3, a4)
        add(B.curSet .. "|" .. name, now() - t0)
        return r1, r2
    end
end

local function timedWork(fn)
    return function(u, p)
        if not B.prof.on then return fn(u, p) end
        local set = setOf(u)
        local t0 = now()
        local r1, r2 = fn(u, p)
        add(set .. "|__work", now() - t0)
        return r1, r2
    end
end

local function wrap()
    if B.prof.wrapped then return end
    local MIN = NR.server.minute
    local names = {}
    for i = 1, #MIN.ORDER do
        local name = MIN.ORDER[i]
        local fn = MIN.steps[name]
        if fn ~= nil then
            MIN.steps[name] = timedStep(name, fn)
            names[#names + 1] = name
        end
    end
    MIN.run = timedRun(MIN.run)
    NR.server.players.work = timedWork(NR.server.players.work)
    B.prof.wrappedNames = table.concat(names, ",")
    B.prof.wrapped = true
end

function B.profReset()
    B.acc = { ms = {}, runs = {} }
    B.hist = {}
    B.ring = { n = 0, u = {}, ms = {}, mn = {}, mc = {}, nc = {}, ec = {} }
    return B.prof.wrappedNames, B.ticks, B.minutes
end
function B.profStart(sb)
    wrap()
    B.sbOn = (sb == true or sb == 1 or sb == "true")
    B.prof.on = true
    return B.prof.wrappedNames, B.ticks, B.minutes
end
function B.profStop()
    B.prof.on = false
    B.sbOn = false
    return B.prof.wrappedNames, B.ticks, B.minutes
end
function B.sbSet(on)
    B.sbOn = (on == true or on == 1 or on == "true")
    return B.sbOn, B.ticks, B.minutes
end

-- The accumulators as one string, sorted by key: key=ms/runs;... (r2 the key count, r3 MIN.stats.failures).
function B.accText(prefix)
    local keys = {}
    for k, _ in pairs(B.acc.ms) do
        if prefix == nil or prefix == "" or string.sub(k, 1, string.len(prefix)) == prefix then keys[#keys + 1] = k end
    end
    table.sort(keys)
    local parts = {}
    for i = 1, #keys do
        local k = keys[i]
        parts[#parts + 1] = k .. "=" .. tostring(B.acc.ms[k]) .. "/" .. tostring(B.acc.runs[k])
    end
    local MIN = NR.server.minute
    return table.concat(parts, ";"), #keys, MIN.stats.failures
end

-- The histograms: set:c0,c1,...,c30 joined by ";".
function B.histText()
    local sets = {}
    for s, _ in pairs(B.hist) do sets[#sets + 1] = s end
    table.sort(sets)
    local parts = {}
    for i = 1, #sets do
        local h = B.hist[sets[i]]
        local cs = {}
        for j = 0, 30 do cs[#cs + 1] = tostring(h[j]) end
        parts[#parts + 1] = sets[i] .. ":" .. table.concat(cs, ",")
    end
    return table.concat(parts, ";"), #sets, B.minutes
end

-- The ring, entries from..to as user,ms,minute,metCloses,nutCloses,effCloses joined by ";" (r2 the count).
function B.ringText(from, to)
    local R = B.ring
    local a = tonumber(from) or 1
    local b = tonumber(to) or R.n
    if b > R.n then b = R.n end
    local parts = {}
    local i = a
    while i <= b do
        parts[#parts + 1] = tostring(R.u[i]) .. "," .. tostring(R.ms[i]) .. "," .. tostring(R.mn[i]) .. ","
            .. tostring(R.mc[i]) .. "," .. tostring(R.nc[i]) .. "," .. tostring(R.ec[i])
        i = i + 1
    end
    return table.concat(parts, ";"), R.n, B.minutes
end

-- ---- bench C: one interleaved set of the burst sources a tick (OnTick), n sets ---------------------------------
-- Kinds: typ (a whole minute on a fresh copy of admin's record, dtM 1), close (the same with one day to close:
-- Metabolism, Nutrients and Effects each close once), catch (seven days to close: Metabolism's MAX_CLOSES, the
-- seven-close catch-up), fsLoad (NR_Server_Store's load of a fresh copy), fsBody (MET.ensureBody on an empty
-- record: a new player's body), fsHooks (every P.onFirstSight hook, as the players' walk fires them, for admin on a
-- fresh copy; the mirror send stubbed and counted), send (B.sendMirror of admin's own record to admin, the real
-- send) and build (K.mirror.build alone). typ/close/catch run MIN.run under the copies' own usernames with
-- sendServerCommand stubbed and counted; their fast input is admin's (feed). The copies are made outside the timed
-- bracket, fresh each set, so no copy drifts over the bench.
B.C = nil
B.C_KINDS = { "typ", "close", "catch", "fsLoad", "fsBody", "fsHooks", "send", "build" }

local function sscStub()
    local C = B.C
    if C ~= nil then C.stubbed = C.stubbed + 1 end
end

local function prep(r, closes, age)
    local today = math.floor(age / 24)
    if type(r.body) == "table" then
        r.body.lastAgeH = age - 1 / 60
        if closes > 0 then r.body.dayIndex = today - closes end
    end
    if type(r.nutrients) == "table" then
        r.nutrients.lastAgeH = age - 1 / 60
        if closes > 0 then r.nutrients.lastDayIndex = today - closes end
    end
    if closes > 0 and type(r.effects) == "table" then r.effects.lastDay = today - closes end
end

local function runCopy(C, name, r, p)
    local F = NR.server.fast
    if F ~= nil and type(F.lastInp) == "table" then F.lastInp[name] = F.lastInp[C.u] end
    local real = sendServerCommand
    sendServerCommand = sscStub
    local t0 = now()
    local ok, err = pcall(NR.server.minute.run, name, p, r)
    local d = now() - t0
    sendServerCommand = real
    if not ok then
        C.fail = C.fail + 1
        C.err = tostring(err)
    end
    return d
end

local function hooks(C, r, p)
    local P = NR.server.players
    local real = sendServerCommand
    sendServerCommand = sscStub
    local t0 = now()
    for i = 1, #P.onFirstSight do
        local ok, err = pcall(P.onFirstSight[i], C.u, p, r)
        if not ok then
            C.fail = C.fail + 1
            C.err = tostring(err)
        end
    end
    local d = now() - t0
    sendServerCommand = real
    return d
end

local function one(C, kind, base, p, age)
    local d = 0
    local mark = nil
    if kind == "typ" or kind == "close" or kind == "catch" then
        local r = copyOf(base, 0)
        local k = 0
        if kind == "close" then k = 1 elseif kind == "catch" then k = 7 end
        prep(r, k, age)
        B.benchSet = "bench:" .. kind
        local MET = NR.server.metabolism
        local m0 = statN(MET, "days")
        d = runCopy(C, "h2b_" .. kind, r, p)
        mark = statN(MET, "days") - m0
        B.benchSet = nil
    elseif kind == "fsLoad" then
        local r = copyOf(base, 0)
        local t0 = now()
        local ok, err = pcall(NR.server.store.load, "h2b_fs", r)
        d = now() - t0
        if not ok then
            C.fail = C.fail + 1
            C.err = tostring(err)
        end
    elseif kind == "fsBody" then
        local r = {}
        local t0 = now()
        local ok, err = pcall(NR.server.metabolism.ensureBody, "h2b_fs", p, r, age)
        d = now() - t0
        if not ok then
            C.fail = C.fail + 1
            C.err = tostring(err)
        end
    elseif kind == "fsHooks" then
        local r = copyOf(base, 0)
        d = hooks(C, r, p)
    elseif kind == "send" then
        local t0 = now()
        local ok, err = pcall(NR.server.bus.sendMirror, p, base)
        d = now() - t0
        if not ok or err ~= true then
            C.fail = C.fail + 1
            C.err = "send: " .. tostring(err)
        end
    elseif kind == "build" then
        local BUS = NR.server.bus
        local t0 = now()
        local ok, err = pcall(K.mirror.build, base, BUS.meta(), NR.data and NR.data.records and NR.data.records.ORDER)
        d = now() - t0
        if not ok then
            C.fail = C.fail + 1
            C.err = "build: " .. tostring(err)
        elseif C.payloadKeys == nil and type(err) == "table" then
            local n = 0
            for _ in pairs(err) do n = n + 1 end
            C.payloadKeys = n
        end
    end
    C.ms[kind] = C.ms[kind] + d
    C.n[kind] = C.n[kind] + 1
    if d > C.max[kind] then C.max[kind] = d end
    if mark ~= nil then C.closes[kind] = C.closes[kind] + mark end
end

function B.cTick()
    local C = B.C
    if C == nil or C.done then return end
    local P = NR.server.players
    local p = P.online[C.u]
    local recs = NR.server.store.attach()
    local base = recs ~= nil and recs[C.u] or nil
    if p == nil or base == nil then
        C.done = true
        C.reason = "the bench user is offline or has no record"
        return
    end
    local age = NR.worldAge()
    if type(age) ~= "number" then
        C.waits = C.waits + 1
        return
    end
    local i = C.sets + 1
    local nk = #B.C_KINDS
    local t0 = now()
    for j = 1, nk do
        local kind = B.C_KINDS[((i + j - 2) % nk) + 1]
        one(C, kind, base, p, age)
    end
    local d = now() - t0
    C.setMs = C.setMs + d
    if d > C.setMax then C.setMax = d end
    C.sets = i
    if C.sets >= C.target then
        C.done = true
        C.doneAt = now()
    end
end

function B.cArm(n, user)
    local target = tonumber(n) or 0
    if target < 1 then return false, "n" end
    local C = { target = target, u = user or "admin", sets = 0, done = false, waits = 0, fail = 0, err = nil,
                stubbed = 0, setMs = 0, setMax = 0, armedAt = now(), doneAt = nil, reason = nil, payloadKeys = nil,
                ms = {}, n = {}, max = {}, closes = {} }
    for i = 1, #B.C_KINDS do
        local k = B.C_KINDS[i]
        C.ms[k], C.n[k], C.max[k], C.closes[k] = 0, 0, 0, 0
    end
    B.C = C
    return true, target, C.u
end

-- The bench's state: done, sets, fail, stubbed, then kind=ms/n/max/closes per kind (r1); r2 done; r3 sets.
function B.cText()
    local C = B.C
    if C == nil then return "none", false, 0 end
    local parts = { "done=" .. tostring(C.done), "sets=" .. tostring(C.sets), "target=" .. tostring(C.target),
                    "fail=" .. tostring(C.fail), "stubbed=" .. tostring(C.stubbed), "waits=" .. tostring(C.waits),
                    "setMs=" .. tostring(C.setMs), "setMax=" .. tostring(C.setMax),
                    "payloadKeys=" .. tostring(C.payloadKeys), "wall=" .. tostring((C.doneAt or now()) - C.armedAt),
                    "reason=" .. tostring(C.reason), "err=" .. tostring(C.err) }
    for i = 1, #B.C_KINDS do
        local k = B.C_KINDS[i]
        parts[#parts + 1] = k .. "=" .. tostring(C.ms[k]) .. "/" .. tostring(C.n[k]) .. "/" .. tostring(C.max[k]) .. "/"
            .. tostring(C.closes[k])
    end
    return table.concat(parts, ";"), C.done, C.sets
end

-- ---- H6's arm E: the seeded store (server) and the request probe (client) ---------------------------------------
NR_H6 = NR_H6 or {}
NR_H6.NAME = "NutritionRevamp.players"
NR_H6.max = NR_H6.max or 0
NR_H6.rx = NR_H6.rx or { n = 0, name = "", isTable = false, keys = -1, at = 0, sent = 0, sentAt = 0 }

local function pad6(i)
    local s = string.format("%.0f", i)
    while string.len(s) < 6 do s = "0" .. s end
    return s
end

-- seed(n): exactly n synthetic records h6p000001..h6p<n> in the store's table, each a deep copy of admin's record
-- (else the first by name) with its username field set to its key. Returns the table's key count and the ms taken.
function NR_H6.seed(n)
    if not NR.isServer() then return -1, 0 end
    local t = NR.server.store.attach()
    if t == nil then return -2, 0 end
    local want = tonumber(n) or 0
    local base = t.admin
    if base == nil then
        local names = {}
        for k, v in pairs(t) do
            if type(v) == "table" and string.sub(tostring(k), 1, 3) ~= "h6p" then names[#names + 1] = k end
        end
        table.sort(names)
        if names[1] ~= nil then base = t[names[1]] end
    end
    if base == nil then return -3, 0 end
    local t0 = now()
    local i = 1
    while i <= want do
        local key = "h6p" .. pad6(i)
        if t[key] == nil then
            local c = copyOf(base, 0)
            c.username = key
            t[key] = c
        end
        i = i + 1
    end
    local j = want + 1
    while j <= NR_H6.max do
        t["h6p" .. pad6(j)] = nil
        j = j + 1
    end
    if want > NR_H6.max then NR_H6.max = want end
    if want < NR_H6.max then NR_H6.max = want end
    local count = 0
    for _ in pairs(t) do count = count + 1 end
    return count, now() - t0
end

function NR_H6.clear()
    return NR_H6.seed(0)
end

function NR_H6.count()
    if not NR.isServer() then return -1, 0 end
    local t = NR.server.store.attach()
    if t == nil then return -2, 0 end
    local count, synth = 0, 0
    for k, _ in pairs(t) do
        count = count + 1
        if string.sub(tostring(k), 1, 3) == "h6p" then synth = synth + 1 end
    end
    return count, synth
end

-- request(): the client asks the server for the store's table by name (ModData.request); the receive probe below
-- records what arrives.
function NR_H6.request()
    if not isCl() then return false, "not a client" end
    if ModData == nil or ModData.request == nil then return false, "ModData.request absent" end
    local R = NR_H6.rx
    local ok, err = pcall(ModData.request, NR_H6.NAME)
    R.sent = R.sent + 1
    R.sentAt = now()
    return ok, tostring(err)
end

if Events ~= nil and Events.OnReceiveGlobalModData ~= nil then
    Events.OnReceiveGlobalModData.Add(function(name, data)
        if not isCl() then return end
        local R = NR_H6.rx
        R.n = R.n + 1
        R.name = tostring(name)
        R.isTable = type(data) == "table"
        local k = 0
        if type(data) == "table" then
            for _ in pairs(data) do k = k + 1 end
        end
        R.keys = k
        R.at = now()
        R.lag = R.at - (R.sentAt or 0)
    end)
end

-- ---- bench D: the client tooltip's entry (bench.global targets, no arguments) -----------------------------------
NR_H2C = NR_H2C or { item = nil }

-- arm(fullType): the local player's first inventory item of the type (r1 true when found, r2 its full type).
function NR_H2C.arm(fullType)
    if not isCl() or getPlayer == nil then return false, "not a client" end
    local okP, p = pcall(getPlayer)
    if not okP or p == nil then return false, "no player" end
    local okI, inv = pcall(function() return p:getInventory() end)
    if not okI or inv == nil then return false, "no inventory" end
    local okF, item = pcall(function() return inv:getFirstTypeRecurse(fullType) end)
    if not okF or item == nil then return false, "no item" end
    NR_H2C.item = item
    local T = NutritionRevamp.client and NutritionRevamp.client.tooltip or nil
    if T == nil then return false, "no tooltip" end
    local e = T.entryFor(item)
    local lines = 0
    if type(e) == "table" and type(e.lines) == "table" then lines = #e.lines end
    return true, tostring(fullType), lines
end

-- hit(): the per-frame path for the same hovered item (the cache's same-item check after its reads).
function NR_H2C.hit()
    return NutritionRevamp.client.tooltip.entryFor(NR_H2C.item)
end

-- miss(): the cache cleared first, so every call builds the entry.
function NR_H2C.miss()
    local T = NutritionRevamp.client.tooltip
    T.cache = {}
    T.last = nil
    return T.entryFor(NR_H2C.item)
end

if Events ~= nil then
    if Events.OnTick ~= nil then
        Events.OnTick.Add(function()
            if not NR.isServer() then return end
            B.ticks = B.ticks + 1
            if B.C ~= nil and not B.C.done then B.cTick() end
        end)
    end
    if Events.EveryOneMinute ~= nil then
        Events.EveryOneMinute.Add(function()
            if not NR.isServer() then return end
            B.minutes = B.minutes + 1
        end)
    end
end
