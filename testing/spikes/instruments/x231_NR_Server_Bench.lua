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
-- Plan 10b Task P1+P3 (the STAGED copy release/perf-dc619d0 only; never mod/): the slow minute by step, and the cost
-- of no per-tick work. Every entry below is server-gated and test-only. Readings are cost, not behaviour.
-- ===================================================================================================================
NR.server.bench = NR.server.bench or {}
local B = NR.server.bench

local function now()
    if getTimestampMs == nil then return 0 end
    local ok, v = pcall(getTimestampMs)
    if ok and type(v) == "number" then return v end
    return 0
end

-- The clock counters: ticks on OnTick, minutes on EveryOneMinute (the driver paces its phases on them).
B.ticks = 0
B.minutes = 0

-- The bench.global targets of Plan 10 S2, re-added: the first online player (cached), one takeover-handler call
-- or one whole P.work minute per call, at an unchanged world age.
local function firstOnline()
    if B.p ~= nil then return B.p, B.u end
    local P = NR.server.players
    local names = {}
    for u, _ in pairs(P and P.online or {}) do names[#names + 1] = u end
    table.sort(names)
    if names[1] == nil then return nil, nil end
    B.u = names[1]
    B.p = P.online[B.u]
    return B.p, B.u
end
function B.handler()
    local p = firstOnline()
    if p ~= nil and NR.server.fast ~= nil then NR.server.fast.handler(p) end
end
function B.minute()
    local p, u = firstOnline()
    if p ~= nil then NR.server.players.work(u, p) end
end

-- P1 Step 1: per-step timing of the slow minute. The plan placed the wrap at OnServerStarted; this file loads
-- before every adapter (NR_Server_Bench sorts first among server/NR_Server_*), so its OnServerStarted handler would
-- run before the adapters register their steps. The wrap therefore runs at the first profStart (the driver calls it
-- long after OnServerStarted), and records which steps it wrapped. Also wrapped: NR.server.minute.run (key __run:
-- the whole pipeline) and NR.server.players.work (key __work: the pipeline plus store.get, the dead read and
-- P.onMinute). A step's time is accumulated in ms over every run while prof.on is true; getTimestampMs is 1 ms
-- resolution, so a per-run cost is ms / runs over many runs.
-- The Java-call counter wraps NR.call. NR.num, NR.obj and NR.flag call it as pcall(NR.call, ...), a table lookup at
-- call time, and every adapter's local num/obj/flag alias captures those three (not NR.call), so the counter sees
-- every NR.call, NR.num, NR.obj and NR.flag call. Direct colon calls on Java objects are not counted here.
B.prof = { on = false, ms = {}, runs = {}, calls = {}, wrapped = false, wrappedNames = "" }
local calls = 0
local realCall = NR.call
function NR.call(o, name, ...)
    calls = calls + 1
    return realCall(o, name, ...)
end
B.callCount = function() return calls end

local function timed(key, fn)
    B.prof.ms[key], B.prof.runs[key], B.prof.calls[key] = 0, 0, 0
    return function(a1, a2, a3, a4)
        if not B.prof.on then return fn(a1, a2, a3, a4) end
        local c0, t0 = calls, now()
        local r1, r2 = fn(a1, a2, a3, a4)
        B.prof.ms[key] = B.prof.ms[key] + (now() - t0)
        B.prof.calls[key] = B.prof.calls[key] + (calls - c0)
        B.prof.runs[key] = B.prof.runs[key] + 1
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
            MIN.steps[name] = timed(name, fn)
            names[#names + 1] = name
        end
    end
    MIN.run = timed("__run", MIN.run)
    NR.server.players.work = timed("__work", NR.server.players.work)
    B.prof.wrappedNames = table.concat(names, ",")
    B.prof.wrapped = true
end

function B.profReset()
    for k, _ in pairs(B.prof.ms) do
        B.prof.ms[k], B.prof.runs[k], B.prof.calls[k] = 0, 0, 0
    end
    return B.prof.wrappedNames
end
function B.profStart()
    wrap()
    B.prof.on = true
    return B.prof.wrappedNames, B.ticks, B.minutes
end
function B.profStop()
    B.prof.on = false
    return B.prof.wrappedNames, B.ticks, B.minutes
end
-- One string: name=ms/runs/calls; per key, in ORDER then __run and __work. lua.call returns it as r1.
function B.profText()
    local MIN = NR.server.minute
    local parts = {}
    local keys = {}
    for i = 1, #MIN.ORDER do keys[#keys + 1] = MIN.ORDER[i] end
    keys[#keys + 1] = "__run"
    keys[#keys + 1] = "__work"
    for i = 1, #keys do
        local k = keys[i]
        if B.prof.ms[k] ~= nil then
            parts[#parts + 1] = k .. "=" .. tostring(B.prof.ms[k]) .. "/" .. tostring(B.prof.runs[k]) .. "/" .. tostring(B.prof.calls[k])
        end
    end
    return table.concat(parts, ";"), MIN.stats.runs, MIN.stats.failures
end

-- P3 Step 2: the no-per-tick entries. Stats handles as NR_Server_Fast's hoist reaches them: p:getStats(), then
-- stats:get(CharacterStat.X) and stats:set(CharacterStat.X, v).
B.holdOn = false
B.burstOn = false
B.panicTarget = 0.5
B.tempTarget = 37.5
B.holdUser = "admin"
B.rrM = 0

local function statsOf(p)
    if p == nil then return nil end
    local ok, s = pcall(function() return p:getStats() end)
    if ok then return s end
    return nil
end
local function sget(s, stat)
    if s == nil or stat == nil then return nil end
    local ok, v = pcall(function() return s:get(stat) end)
    if ok and type(v) == "number" then return v end
    return nil
end
local function sset(s, stat, v)
    if s == nil or stat == nil then return false end
    local ok = pcall(function() s:set(stat, v) end)
    return ok
end

-- The hold's rings (numeric arrays; the driver pages them with holdText). The tick ring samples the hold user's
-- PANIC and TEMPERATURE on every OnTick while holdOn; the write ring records each EveryOneMinute write for that
-- user: the pre-write values (what the minute's decay left), the read-back after the write, the tick and wall.
B.HOLD_MAX = 4000
B.hold = { tn = 0, tTick = {}, tMin = {}, tPanic = {}, tTemp = {},
           wn = 0, wTick = {}, wMin = {}, wPre = {}, wPreT = {}, wPost = {}, wPostT = {}, wMs = {}, wPlayers = {} }

function B.holdReset()
    B.hold = { tn = 0, tTick = {}, tMin = {}, tPanic = {}, tTemp = {},
               wn = 0, wTick = {}, wMin = {}, wPre = {}, wPreT = {}, wPost = {}, wPostT = {}, wMs = {}, wPlayers = {} }
    return B.ticks, B.minutes
end

local function holdPlayer()
    local P = NR.server.players
    if P == nil or P.online == nil then return nil end
    return P.online[B.holdUser]
end

function B.minuteHold()
    if not B.holdOn then return end
    local P = NR.server.players
    if P == nil or P.online == nil or CharacterStat == nil then return end
    local H = B.hold
    local n = 0
    for u, p in pairs(P.online) do
        local s = statsOf(p)
        local pre = sget(s, CharacterStat.PANIC)
        local preT = sget(s, CharacterStat.TEMPERATURE)
        sset(s, CharacterStat.PANIC, B.panicTarget)
        sset(s, CharacterStat.TEMPERATURE, B.tempTarget)
        n = n + 1
        if u == B.holdUser and H.wn < B.HOLD_MAX then
            H.wn = H.wn + 1
            local i = H.wn
            H.wTick[i] = B.ticks
            H.wMin[i] = B.minutes
            H.wPre[i] = pre or -1
            H.wPreT[i] = preT or -1
            H.wPost[i] = sget(s, CharacterStat.PANIC) or -1
            H.wPostT[i] = sget(s, CharacterStat.TEMPERATURE) or -1
            H.wMs[i] = now()
        end
    end
    if H.wn > 0 then H.wPlayers[H.wn] = n end
end

local function holdTick()
    if not B.holdOn or CharacterStat == nil then return end
    local H = B.hold
    if H.tn >= B.HOLD_MAX then return end
    local s = statsOf(holdPlayer())
    if s == nil then return end
    H.tn = H.tn + 1
    local i = H.tn
    H.tTick[i] = B.ticks
    H.tMin[i] = B.minutes
    H.tPanic[i] = sget(s, CharacterStat.PANIC) or -1
    H.tTemp[i] = sget(s, CharacterStat.TEMPERATURE) or -1
end

-- holdText("t" | "w", from, to): the tick ring as tick,minute,panic,temp; or the write ring as
-- tick,minute,prePanic,preTemp,postPanic,postTemp,wallMs; entries joined by ";". r2 is the ring's count.
function B.holdText(kind, from, to)
    local H = B.hold
    local count = (kind == "w") and H.wn or H.tn
    local a = tonumber(from) or 1
    local b = tonumber(to) or count
    if b > count then b = count end
    local parts = {}
    local i = a
    while i <= b do
        if kind == "w" then
            parts[#parts + 1] = tostring(H.wTick[i]) .. "," .. tostring(H.wMin[i]) .. "," .. tostring(H.wPre[i]) .. ","
                .. tostring(H.wPreT[i]) .. "," .. tostring(H.wPost[i]) .. "," .. tostring(H.wPostT[i]) .. "," .. tostring(H.wMs[i])
        else
            parts[#parts + 1] = tostring(H.tTick[i]) .. "," .. tostring(H.tMin[i]) .. "," .. tostring(H.tPanic[i]) .. "," .. tostring(H.tTemp[i])
        end
        i = i + 1
    end
    return table.concat(parts, ";"), count, B.ticks
end

-- The burst: one EveryOneMinute event runs P.work for every online player (B.burst) or for ceil(N / m) players in a
-- persistent rotation (B.burstRR(m)). The live OnTick drain stays on, so each player's minute also runs from the
-- queue at a later tick of the same minute at a near-zero interval: the burst's runs carry the minute's elapsed
-- time (it runs first), the state change is cost-not-behaviour. Accumulates event count, players run, total ms, the
-- max per-event ms and a per-event ms histogram (e0..e4, e5 = five or more).
B.bst = { events = 0, players = 0, ms = 0, maxMs = 0, e0 = 0, e1 = 0, e2 = 0, e3 = 0, e4 = 0, e5 = 0, rot = 0 }
function B.burstReset()
    B.bst = { events = 0, players = 0, ms = 0, maxMs = 0, e0 = 0, e1 = 0, e2 = 0, e3 = 0, e4 = 0, e5 = 0, rot = 0 }
    return B.ticks, B.minutes
end

local function onlineNames()
    local P = NR.server.players
    local names = {}
    for u, _ in pairs(P and P.online or {}) do names[#names + 1] = u end
    table.sort(names)
    return names
end

local function account(t0, k)
    local d = now() - t0
    local S = B.bst
    S.events = S.events + 1
    S.players = S.players + k
    S.ms = S.ms + d
    if d > S.maxMs then S.maxMs = d end
    if d >= 5 then S.e5 = S.e5 + 1
    elseif d == 4 then S.e4 = S.e4 + 1
    elseif d == 3 then S.e3 = S.e3 + 1
    elseif d == 2 then S.e2 = S.e2 + 1
    elseif d == 1 then S.e1 = S.e1 + 1
    else S.e0 = S.e0 + 1 end
end

function B.burst()
    local P = NR.server.players
    local names = onlineNames()
    local t0 = now()
    local k = 0
    for i = 1, #names do
        local p = P.online[names[i]]
        if p ~= nil then
            P.work(names[i], p)
            k = k + 1
        end
    end
    account(t0, k)
end

function B.burstRR(m)
    local P = NR.server.players
    local names = onlineNames()
    local n = #names
    if n == 0 then return end
    local mm = tonumber(m) or 1
    if mm < 1 then mm = 1 end
    local share = math.ceil(n / mm)
    local t0 = now()
    local k = 0
    local j = 0
    while j < share do
        local idx = (B.bst.rot % n) + 1
        B.bst.rot = B.bst.rot + 1
        local u = names[idx]
        local p = P.online[u]
        if p ~= nil then
            P.work(u, p)
            k = k + 1
        end
        j = j + 1
    end
    account(t0, k)
end

function B.burstText()
    local S = B.bst
    return "events=" .. tostring(S.events) .. " players=" .. tostring(S.players) .. " ms=" .. tostring(S.ms)
        .. " maxMs=" .. tostring(S.maxMs) .. " e0=" .. tostring(S.e0) .. " e1=" .. tostring(S.e1) .. " e2=" .. tostring(S.e2)
        .. " e3=" .. tostring(S.e3) .. " e4=" .. tostring(S.e4) .. " e5=" .. tostring(S.e5) .. " rot=" .. tostring(S.rot),
        B.ticks, B.minutes
end

if Events ~= nil then
    if Events.OnTick ~= nil then
        Events.OnTick.Add(function()
            if not NR.isServer() then return end
            B.ticks = B.ticks + 1
            holdTick()
        end)
    end
    if Events.EveryOneMinute ~= nil then
        Events.EveryOneMinute.Add(function()
            if not NR.isServer() then return end
            B.minutes = B.minutes + 1
            B.minuteHold()
            if B.burstOn then
                if (tonumber(B.rrM) or 0) > 0 then B.burstRR(B.rrM) else B.burst() end
            end
        end)
    end
end
