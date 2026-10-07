-- TKX_GlobalsProbe -- Plan 10 Task S1: the zeroed-drains alternative to the Hook.CalculateStats takeover.
--
-- The desk read (task-S1-desk.md): every HUNGER, THIRST and FATIGUE rise rate of the seven updaters is a
-- ZomboidGlobals static that ZomboidGlobals.Load() copies ONCE from this Lua table (Load @0-@626 L67-L120,
-- rawget, checkcast Double, putstatic). On a dedicated server Load runs at GameServer.doMinimumInit @531
-- L1517, after every mod file's file scope (LoadDirBase @341-@354 L1488-L1490) and one instruction after
-- the OnGameBoot trigger (@525-@528 L1516); nothing re-runs it, and ZomboidGlobals is not exposed.
--
-- So this file zeroes the six non-zero rise keys by the two reachable routes, one route per key group,
-- so each group's drift witnesses its own route:
--   file scope (earliest; every Lua state):      ThirstIncrease, ThirstSleepingIncrease
--   Events.OnGameBoot (the server's last chance): HungerIncrease, HungerIncreaseWhileAsleep,
--                                                  HungerIncreaseWhenExercise, FatigueIncrease
-- (HungerIncreaseWhenWellFed ships at 0 and is left alone.) A key is set to 0, never nil: Load's
-- doubleValue on a nil would throw at boot.
--
-- Then, on the server only, once a game minute, every online player gets HUNGER = 0.3, THIRST = 0.2 and
-- FATIGUE = 0.1 through stats:set(CharacterStat.X, v) -- the takeover's own setter (NR_Server_Fast.lua's
-- hoist: h.set = stats.set, called set(stats, h.HUNGER, v)). The value read just BEFORE each write and
-- just AFTER it are kept per player: pre minus the player's previous post is what vanilla's own update
-- (and any event) did to the stat over one game minute with the rates zeroed.
--
-- TKX_G is the string-valued record the driver reads with lua.global: what was set, when, and the
-- values read back from the Lua table (the Java statics cannot be read from Lua; the drift is the
-- Java-side witness). TKX_GP holds the functions the driver calls (lua.call, bench.global) and the one
-- switch it flips (lua.setpath TKX_GP.on false|true).
--
-- Kahlua rules: no goto, no %d, no # on a Java list (the online list is walked with size()/get()).
-- Every Java member is reached inside a pcall'd function; the minute handler is one pcall per player.
TKX_G = { version = "1", side = "?", fileScope = "unset", fileScopeAt = "unset", fileScopeDayLength = "unset",
          bootFired = "0", bootAt = "unset", bootSide = "unset", bootSet = "unset", bootDayLength = "unset",
          bootTableBefore = "unset", startedTable = "unset", startedAt = "unset", minutes = "0", writes = "0",
          writeErrors = "0", lastErr = "", on = "true", targets = "HUNGER=0.3,THIRST=0.2,FATIGUE=0.1" }
TKX_GP = { on = true, minutes = 0, writes = 0, errors = 0, seq = 0, RING = 256, ring = {}, last = {}, agg = {},
           bp = nil, bs = nil, bu = "" }
local G, GP = TKX_G, TKX_GP
local W_H, W_T, W_F = 0.3, 0.2, 0.1
local KEYS = { "ThirstIncrease", "ThirstSleepingIncrease", "HungerIncrease", "HungerIncreaseWhenWellFed",
               "HungerIncreaseWhileAsleep", "HungerIncreaseWhenExercise", "FatigueIncrease" }
local BOOT_KEYS = { "HungerIncrease", "HungerIncreaseWhileAsleep", "HungerIncreaseWhenExercise", "FatigueIncrease" }

local function now()
    if getTimestampMs == nil then return 0 end
    local ok, t = pcall(getTimestampMs)
    if ok and t ~= nil then return t end
    return 0
end

local function sideName()
    local s = "?"
    if isServer ~= nil then
        local ok, v = pcall(isServer)
        if ok and v then s = "server" end
    end
    if s == "?" and isClient ~= nil then
        local ok, v = pcall(isClient)
        if ok and v then s = "client" end
    end
    return s
end
G.side = sideName()

local function dayLength()
    if SandboxVars == nil then return "noSandboxVars" end
    return tostring(SandboxVars.DayLength)
end

local function tableText(keys)
    local zg = ZomboidGlobals
    if type(zg) ~= "table" then return "noTable" end
    local parts = {}
    local n = 0
    for _, k in ipairs(keys) do
        n = n + 1
        parts[n] = k .. "=" .. tostring(zg[k])
    end
    return table.concat(parts, ";")
end

-- Route 1: file scope (runs inside LoadDirBase, before Load on every side).
if type(ZomboidGlobals) == "table" then
    ZomboidGlobals.ThirstIncrease = 0
    ZomboidGlobals.ThirstSleepingIncrease = 0
    G.fileScope = tableText({ "ThirstIncrease", "ThirstSleepingIncrease" })
else
    G.fileScope = "noTable"
end
G.fileScopeAt = tostring(now())
G.fileScopeDayLength = dayLength()

-- Route 2: OnGameBoot (on the dedicated server, one instruction before Load).
local function onBoot()
    G.bootFired = tostring(tonumber(G.bootFired) + 1)
    G.bootAt = tostring(now())
    G.bootSide = sideName()
    G.bootDayLength = dayLength()
    G.bootTableBefore = tableText(KEYS)
    if type(ZomboidGlobals) ~= "table" then
        G.bootSet = "noTable"
        return
    end
    for _, k in ipairs(BOOT_KEYS) do
        ZomboidGlobals[k] = 0
    end
    G.bootSet = tableText(BOOT_KEYS)
end
if Events ~= nil and Events.OnGameBoot ~= nil then Events.OnGameBoot.Add(onBoot) end

-- After Load: the Lua table as it stands (a mirror; the drift says what the statics hold).
local function onStarted()
    G.startedTable = tableText(KEYS)
    G.startedAt = tostring(now())
end
if Events ~= nil and Events.OnServerStarted ~= nil then Events.OnServerStarted.Add(onStarted) end
if Events ~= nil and Events.OnGameStart ~= nil then Events.OnGameStart.Add(onStarted) end

local function fmt(v)
    if v == nil then return "nil" end
    return tostring(v)
end

local function aggFor(u)
    local a = GP.agg[u]
    if a == nil then
        a = { n = 0, nAwake = 0, nAsleep = 0, awH = 0, awT = 0, awF = 0, slH = 0, slT = 0, slF = 0, slSumF = 0,
              slMinF = 0, slMaxF = 0 }
        GP.agg[u] = a
    end
    return a
end

local function absv(x)
    if x < 0 then return -x end
    return x
end

-- One player's minute: read, write the three stats, read back, keep the ring row and the aggregates.
local function writeOne(p)
    local HUNGER, THIRST, FATIGUE = CharacterStat.HUNGER, CharacterStat.THIRST, CharacterStat.FATIGUE
    local u = p:getUsername()
    local s = p:getStats()
    local asleep = p:isAsleep()
    local h0, t0, f0 = s:get(HUNGER), s:get(THIRST), s:get(FATIGUE)
    s:set(HUNGER, W_H)
    s:set(THIRST, W_T)
    s:set(FATIGUE, W_F)
    local h1, t1, f1 = s:get(HUNGER), s:get(THIRST), s:get(FATIGUE)
    GP.writes = GP.writes + 1
    local last = GP.last[u]
    local dText = "na"
    if last ~= nil then
        local dH, dT, dF = h0 - last.h, t0 - last.t, f0 - last.f
        dText = fmt(dH) .. "," .. fmt(dT) .. "," .. fmt(dF)
        local a = aggFor(u)
        a.n = a.n + 1
        if asleep then
            a.nAsleep = a.nAsleep + 1
            if absv(dH) > a.slH then a.slH = absv(dH) end
            if absv(dT) > a.slT then a.slT = absv(dT) end
            if absv(dF) > a.slF then a.slF = absv(dF) end
            a.slSumF = a.slSumF + dF
            if dF < a.slMinF then a.slMinF = dF end
            if dF > a.slMaxF then a.slMaxF = dF end
        else
            a.nAwake = a.nAwake + 1
            if absv(dH) > a.awH then a.awH = absv(dH) end
            if absv(dT) > a.awT then a.awT = absv(dT) end
            if absv(dF) > a.awF then a.awF = absv(dF) end
        end
    end
    GP.last[u] = { h = h1, t = t1, f = f1 }
    GP.seq = GP.seq + 1
    local age = "?"
    if getGameTime ~= nil then
        local okA, gt = pcall(getGameTime)
        if okA and gt ~= nil then age = fmt(gt:getWorldAgeHours()) end
    end
    GP.ring[GP.seq % GP.RING] = tostring(GP.seq) .. "|" .. tostring(GP.minutes) .. "|" .. tostring(u) .. "|"
        .. tostring(asleep) .. "|" .. fmt(h0) .. "," .. fmt(t0) .. "," .. fmt(f0) .. "|" .. fmt(h1) .. ","
        .. fmt(t1) .. "," .. fmt(f1) .. "|" .. dText .. "|" .. age .. "|" .. tostring(now())
end

local function onMinute()
    if G.side ~= "server" then return end
    GP.minutes = GP.minutes + 1
    G.minutes = tostring(GP.minutes)
    G.on = tostring(GP.on)
    if not GP.on then return end
    local okL, list = pcall(getOnlinePlayers)
    if not okL or list == nil then return end
    local okN, n = pcall(function() return list:size() end)
    if not okN or n == nil then return end
    for i = 0, n - 1 do
        local okP, p = pcall(function() return list:get(i) end)
        if okP and p ~= nil then
            local ok, err = pcall(writeOne, p)
            if not ok then
                GP.errors = GP.errors + 1
                G.writeErrors = tostring(GP.errors)
                G.lastErr = tostring(err)
            end
        end
    end
    G.writes = tostring(GP.writes)
end
if Events ~= nil and Events.EveryOneMinute ~= nil then Events.EveryOneMinute.Add(onMinute) end

-- The driver's reads (lua.call): ring rows a..b (by sequence number) and the aggregates.
function TKX_GP.ringText(a, b)
    local lo = tonumber(a) or 1
    local hi = tonumber(b) or GP.seq
    if hi > GP.seq then hi = GP.seq end
    if lo < GP.seq - GP.RING + 1 then lo = GP.seq - GP.RING + 1 end
    if lo < 1 then lo = 1 end
    local parts = {}
    local n = 0
    for i = lo, hi do
        n = n + 1
        parts[n] = GP.ring[i % GP.RING] or ""
    end
    return table.concat(parts, "\n"), GP.seq, GP.minutes
end

function TKX_GP.aggText()
    local parts = {}
    local n = 0
    for u, a in pairs(GP.agg) do
        n = n + 1
        parts[n] = tostring(u) .. ":n=" .. a.n .. ",awake=" .. a.nAwake .. ",awH=" .. fmt(a.awH) .. ",awT=" .. fmt(a.awT)
            .. ",awF=" .. fmt(a.awF) .. ",asleep=" .. a.nAsleep .. ",slH=" .. fmt(a.slH) .. ",slT=" .. fmt(a.slT)
            .. ",slF=" .. fmt(a.slF) .. ",slSumF=" .. fmt(a.slSumF) .. ",slMinF=" .. fmt(a.slMinF) .. ",slMaxF="
            .. fmt(a.slMaxF)
    end
    return table.concat(parts, ";"), GP.seq, GP.minutes
end

function TKX_GP.resetAgg()
    GP.agg = {}
    return "reset", GP.seq, GP.minutes
end

-- The cost arm (bench.global): one player picked by name and its stats object hoisted, then three
-- shapes called n times -- an empty call (the bench's own floor), three sets, three gets plus three sets.
function TKX_GP.benchPick(name)
    GP.bp, GP.bs, GP.bu = nil, nil, ""
    local list = getOnlinePlayers()
    local n = list:size()
    for i = 0, n - 1 do
        local p = list:get(i)
        if p ~= nil and p:getUsername() == tostring(name) then
            GP.bp = p
            GP.bs = p:getStats()
            GP.bu = p:getUsername()
        end
    end
    return GP.bu, n, tostring(GP.bs ~= nil)
end

function TKX_GP.benchNoop()
end

function TKX_GP.benchSet()
    local s = GP.bs
    s:set(CharacterStat.HUNGER, W_H)
    s:set(CharacterStat.THIRST, W_T)
    s:set(CharacterStat.FATIGUE, W_F)
end

function TKX_GP.benchGetSet()
    local s = GP.bs
    local h = s:get(CharacterStat.HUNGER)
    local t = s:get(CharacterStat.THIRST)
    local f = s:get(CharacterStat.FATIGUE)
    GP.benchSink = h + t + f
    s:set(CharacterStat.HUNGER, W_H)
    s:set(CharacterStat.THIRST, W_T)
    s:set(CharacterStat.FATIGUE, W_F)
end

-- The instrumented minute itself (the reads, the writes, the ring row): an upper bound on a writer's
-- per-player minute. It advances the ring and the aggregates, so the driver calls it last.
function TKX_GP.benchMinute()
    writeOne(GP.bp)
end
