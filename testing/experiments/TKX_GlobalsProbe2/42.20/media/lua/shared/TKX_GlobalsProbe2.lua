-- TKX_GlobalsProbe2 -- Plan 10 Task S1b: the zeroed-rates route's unmeasured seats.
--
-- S1 (TKX_GlobalsProbe, run x221-20261007-083259, rows #3362-#3373) showed that a mod can zero vanilla's
-- hunger, thirst and fatigue rise rates by assigning the Lua ZomboidGlobals keys before ZomboidGlobals.Load
-- copies them (GameServer.doMinimumInit: file scope @341-@354, the server sandbox @423-@498, OnGameBoot
-- @525-@528, Load @531 L1517), and hold the three stats with a per-minute server write. This probe is a NEW
-- copy for the five seats S1 left (S1's committed probe is never edited):
--   1  the mod's own sandbox options (SandboxVars.NR.Mode, NR.Severity) read at file scope, in the server's
--      OnGameBoot (where the zeroing happens) and at OnServerStarted;
--   2  auto-drink under zeroed rates and a per-minute THIRST write (the driver raises the THIRST target);
--   3  an eat landing between two per-minute writes;
--   4  the exercise hunger arm (HungerIncreaseWhenExercise zeroed too) while the player runs, squats or swings;
--   5  the cost of one public character update with and without a CalculateStats hook registered.
--
-- The zeroing: all six non-zero rise keys are set 0 in Events.OnGameBoot (the route a sandbox option can
-- choose), unconditionally; what an NR.Mode gate would have decided is recorded beside it (bootGate), so the
-- run does not depend on the answer to seat 1.
--
-- The writer (server, EveryOneMinute): every online player gets HUNGER = GP.wH, THIRST = GP.wT, FATIGUE = GP.wF
-- through stats:set(CharacterStat.X, v). The targets default to 0.3, 0.05 (under the 0.1 auto-drink gate) and
-- 0.1, and the driver changes them with lua.setpath TKX_GP2.wT <v>. Each write keeps a ring row with the value
-- read just before (pre) and just after (post) and the server tick it ran on.
--
-- The sampler (server, OnTick): armed for one player and an optional fluid item, it keeps a ring row per tick:
-- the three stats, the item's litres, the running/moving/sprinting flags, whether the character is in
-- SwipeStatePlayer, asleep, the FOOD_EATEN moodle level, the minute counter and the tick number.
--
-- The cost arm: benchPick(name) hoists one player; benchUpdate calls its public update() (calculateStats is
-- protected and the seven updaters private or protected, so no narrower Lua route exists); hookOn / hookOff
-- register and remove an empty Hook.CalculateStats handler, which makes calculateStats return before the
-- updaters for every character (Event.trigger answers true whenever a callback is registered).
--
-- TKX_G2 is the string-valued record the driver reads with lua.global; TKX_GP2 holds the state, the functions
-- the driver calls (lua.call, bench.global) and the targets it sets (lua.setpath).
-- Kahlua rules: no goto, no %d, no # on a Java list (the online list is walked with size()/get()).
TKX_G2 = { version = "1", side = "?", fileScopeNR = "unset", fileScopeDayLength = "unset", fileScopeAt = "unset",
           bootFired = "0", bootSide = "unset", bootAt = "unset", bootDayLength = "unset", bootNR = "unset",
           bootNRMode = "unset", bootNRSeverity = "unset", bootGate = "unset", bootTableBefore = "unset",
           bootSet = "unset", startedNR = "unset", startedNRMode = "unset", startedNRSeverity = "unset",
           startedTable = "unset", startedAt = "unset", minutes = "0", writes = "0", writeErrors = "0",
           lastErr = "", sampleErrors = "0", sampleLastErr = "", hooked = "false", hookAdds = "0",
           hookRemoves = "0", hookErr = "" }
TKX_GP2 = { on = true, wH = 0.3, wT = 0.05, wF = 0.1, minutes = 0, writes = 0, errors = 0, tick = 0, seq = 0,
            RING = 512, ring = {}, last = {},
            sm = { on = false, p = nil, user = "", fc = nil, ticks = 0, max = 0, seq = 0, RING = 4096, ring = {},
                   swipe = nil, fe = nil, errors = 0 },
            bp = nil, bu = "", hooked = false }
local G, GP = TKX_G2, TKX_GP2
local KEYS = { "ThirstIncrease", "ThirstSleepingIncrease", "HungerIncrease", "HungerIncreaseWhenWellFed",
               "HungerIncreaseWhileAsleep", "HungerIncreaseWhenExercise", "FatigueIncrease" }
local ZERO_KEYS = { "ThirstIncrease", "ThirstSleepingIncrease", "HungerIncrease", "HungerIncreaseWhileAsleep",
                    "HungerIncreaseWhenExercise", "FatigueIncrease" }

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

local function fmt(v)
    if v == nil then return "nil" end
    return tostring(v)
end

local function dayLength()
    if SandboxVars == nil then return "noSandboxVars" end
    return tostring(SandboxVars.DayLength)
end

-- The mod's own options as SandboxVars carries them: the NR table's type, then Mode and Severity.
local function nrRead()
    if SandboxVars == nil then return "noSandboxVars", "noSandboxVars", "noSandboxVars" end
    local t = SandboxVars.NR
    if type(t) ~= "table" then return "NR:" .. type(t), "noNR", "noNR" end
    return "NR:table", fmt(t.Mode), fmt(t.Severity)
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

-- File scope (inside LoadDirBase, before the server's sandbox is loaded): what the NR options read here.
do
    local t, m, s = nrRead()
    G.fileScopeNR = t .. ";Mode=" .. m .. ";Severity=" .. s
    G.fileScopeDayLength = dayLength()
    G.fileScopeAt = tostring(now())
end

-- OnGameBoot (on the dedicated server one instruction before ZomboidGlobals.Load): read the NR options,
-- record the gate a mode-driven zeroing would take, then zero the six rise keys unconditionally.
local function onBoot()
    G.bootFired = tostring(tonumber(G.bootFired) + 1)
    G.bootAt = tostring(now())
    G.bootSide = sideName()
    G.bootDayLength = dayLength()
    local t, m, s = nrRead()
    G.bootNR = t
    G.bootNRMode = m
    G.bootNRSeverity = s
    if m == "2" or m == "2.0" then G.bootGate = "zero (Mode 2)" else G.bootGate = "keep (Mode " .. m .. ")" end
    G.bootTableBefore = tableText(KEYS)
    if type(ZomboidGlobals) ~= "table" then
        G.bootSet = "noTable"
        return
    end
    for _, k in ipairs(ZERO_KEYS) do
        ZomboidGlobals[k] = 0
    end
    G.bootSet = tableText(ZERO_KEYS)
end
if Events ~= nil and Events.OnGameBoot ~= nil then Events.OnGameBoot.Add(onBoot) end

local function onStarted()
    local t, m, s = nrRead()
    G.startedNR = t
    G.startedNRMode = m
    G.startedNRSeverity = s
    G.startedTable = tableText(KEYS)
    G.startedAt = tostring(now())
end
if Events ~= nil and Events.OnServerStarted ~= nil then Events.OnServerStarted.Add(onStarted) end
if Events ~= nil and Events.OnGameStart ~= nil then Events.OnGameStart.Add(onStarted) end

local function worldAge()
    if getGameTime == nil then return "?" end
    local ok, gt = pcall(getGameTime)
    if ok and gt ~= nil then return fmt(gt:getWorldAgeHours()) end
    return "?"
end

-- One player's minute: read, write the three stats, read back, keep the ring row.
local function writeOne(p)
    local HUNGER, THIRST, FATIGUE = CharacterStat.HUNGER, CharacterStat.THIRST, CharacterStat.FATIGUE
    local u = p:getUsername()
    local s = p:getStats()
    local asleep = p:isAsleep()
    local h0, t0, f0 = s:get(HUNGER), s:get(THIRST), s:get(FATIGUE)
    s:set(HUNGER, GP.wH)
    s:set(THIRST, GP.wT)
    s:set(FATIGUE, GP.wF)
    local h1, t1, f1 = s:get(HUNGER), s:get(THIRST), s:get(FATIGUE)
    GP.writes = GP.writes + 1
    local last = GP.last[u]
    local dText = "na"
    if last ~= nil then
        dText = fmt(h0 - last.h) .. "," .. fmt(t0 - last.t) .. "," .. fmt(f0 - last.f)
    end
    GP.last[u] = { h = h1, t = t1, f = f1 }
    GP.seq = GP.seq + 1
    GP.ring[GP.seq % GP.RING] = tostring(GP.seq) .. "|" .. tostring(GP.minutes) .. "|" .. tostring(u) .. "|"
        .. tostring(asleep) .. "|" .. fmt(h0) .. "," .. fmt(t0) .. "," .. fmt(f0) .. "|" .. fmt(h1) .. ","
        .. fmt(t1) .. "," .. fmt(f1) .. "|" .. dText .. "|" .. worldAge() .. "|" .. tostring(now()) .. "|"
        .. tostring(GP.tick)
end

local function onMinute()
    if G.side ~= "server" then return end
    GP.minutes = GP.minutes + 1
    G.minutes = tostring(GP.minutes)
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

-- ---- the per-tick sampler ------------------------------------------------------------------------------
local function call0(obj, m)
    local ok, v = pcall(function() return obj[m](obj) end)
    if ok then return v end
    return "err"
end

local function sampleRow()
    local sm = GP.sm
    local p = sm.p
    local s = p:getStats()
    local h, t, f = s:get(CharacterStat.HUNGER), s:get(CharacterStat.THIRST), s:get(CharacterStat.FATIGUE)
    local litres = "-"
    if sm.fc ~= nil then litres = fmt(call0(sm.fc, "getAmount")) end
    local swipe = "na"
    if sm.swipe ~= nil then
        local ok, v = pcall(function() return p:isCurrentState(sm.swipe) end)
        if ok then swipe = tostring(v) else swipe = "err" end
    end
    local fe = "na"
    if sm.fe ~= nil then
        local ok, v = pcall(function() return p:getMoodles():getMoodleLevel(sm.fe) end)
        if ok then fe = fmt(v) else fe = "err" end
    end
    sm.seq = sm.seq + 1
    sm.ring[sm.seq % sm.RING] = tostring(sm.seq) .. "|" .. tostring(GP.tick) .. "|" .. tostring(GP.minutes) .. "|"
        .. worldAge() .. "|" .. tostring(now()) .. "|" .. fmt(h) .. "," .. fmt(t) .. "," .. fmt(f) .. "|" .. litres
        .. "|" .. fmt(call0(p, "IsRunning")) .. "," .. fmt(call0(p, "isPlayerMoving")) .. ","
        .. fmt(call0(p, "isSprinting")) .. "," .. swipe .. "|" .. fmt(call0(p, "isAsleep")) .. "|" .. fe
end

local function onTick()
    GP.tick = GP.tick + 1
    local sm = GP.sm
    if not sm.on then return end
    sm.ticks = sm.ticks + 1
    if sm.ticks > sm.max then
        sm.on = false
        return
    end
    local ok, err = pcall(sampleRow)
    if not ok then
        sm.errors = sm.errors + 1
        G.sampleErrors = tostring(sm.errors)
        G.sampleLastErr = tostring(err)
    end
end
if Events ~= nil and Events.OnTick ~= nil then Events.OnTick.Add(onTick) end

local function findOnline(name)
    local list = getOnlinePlayers()
    local n = list:size()
    for i = 0, n - 1 do
        local p = list:get(i)
        if p ~= nil and p:getUsername() == tostring(name) then return p, n end
    end
    return nil, n
end

-- arm(user, fullType or "-", maxTicks): the sampler's player, its fluid item (getFirstTypeRecurse) and length.
function TKX_GP2.arm(user, fullType, maxTicks)
    local sm = GP.sm
    sm.on = false
    local p = findOnline(user)
    if p == nil then return "noPlayer", 0, "" end
    sm.p, sm.user, sm.fc = p, tostring(user), nil
    local itemText = "none"
    if fullType ~= nil and tostring(fullType) ~= "-" then
        local okI, it = pcall(function() return p:getInventory():getFirstTypeRecurse(tostring(fullType)) end)
        if okI and it ~= nil then
            local okF, fc = pcall(function() return it:getFluidContainer() end)
            if okF and fc ~= nil then
                sm.fc = fc
                itemText = "fc:" .. fmt(call0(fc, "getAmount"))
            else
                itemText = "noFluidContainer"
            end
        else
            itemText = "noItem"
        end
    end
    if sm.swipe == nil and SwipeStatePlayer ~= nil then
        local okS, st = pcall(function() return SwipeStatePlayer.instance() end)
        if okS then sm.swipe = st end
    end
    if sm.fe == nil and MoodleType ~= nil then
        local okM, mt = pcall(function() return MoodleType.FOOD_EATEN end)
        if okM then sm.fe = mt end
    end
    sm.ticks, sm.max = 0, tonumber(maxTicks) or 300
    sm.on = true
    return "armed", sm.seq, itemText .. ";swipe=" .. tostring(sm.swipe ~= nil) .. ";fe=" .. tostring(sm.fe ~= nil)
end

function TKX_GP2.disarm()
    GP.sm.on = false
    return "disarmed", GP.sm.seq, GP.sm.ticks
end

local function ringPage(ring, size, seq, a, b)
    local lo = tonumber(a) or 1
    local hi = tonumber(b) or seq
    if hi > seq then hi = seq end
    if lo < seq - size + 1 then lo = seq - size + 1 end
    if lo < 1 then lo = 1 end
    local parts = {}
    local n = 0
    for i = lo, hi do
        n = n + 1
        parts[n] = ring[i % size] or ""
    end
    return table.concat(parts, "\n")
end

function TKX_GP2.sampleText(a, b)
    return ringPage(GP.sm.ring, GP.sm.RING, GP.sm.seq, a, b), GP.sm.seq, GP.tick
end

function TKX_GP2.ringText(a, b)
    return ringPage(GP.ring, GP.RING, GP.seq, a, b), GP.seq, GP.minutes
end

function TKX_GP2.seqs()
    return GP.seq, GP.sm.seq, GP.tick
end

-- ---- the cost arm ----------------------------------------------------------------------------------------
function TKX_GP2.benchPick(name)
    GP.bp, GP.bu = nil, ""
    local p, n = findOnline(name)
    if p ~= nil then
        GP.bp = p
        GP.bu = p:getUsername()
    end
    return GP.bu, n, tostring(GP.bp ~= nil)
end

function TKX_GP2.benchNoop()
end

function TKX_GP2.benchUpdate()
    GP.bp:update()
end

function TKX_GP2.hookFn(character)
end

function TKX_GP2.benchHookFn()
    TKX_GP2.hookFn(GP.bp)
end

function TKX_GP2.hookOn()
    if Hook == nil or Hook.CalculateStats == nil or Hook.CalculateStats.Add == nil then
        G.hookErr = "noHook"
        return "noHook", tostring(GP.hooked), G.hookAdds
    end
    if GP.hooked then return "already", tostring(GP.hooked), G.hookAdds end
    local ok, err = pcall(function() Hook.CalculateStats.Add(TKX_GP2.hookFn) end)
    if ok then
        GP.hooked = true
        G.hookAdds = tostring(tonumber(G.hookAdds) + 1)
    else
        G.hookErr = tostring(err)
    end
    G.hooked = tostring(GP.hooked)
    return tostring(ok), tostring(GP.hooked), G.hookAdds
end

function TKX_GP2.hookOff()
    if not GP.hooked then return "notHooked", tostring(GP.hooked), G.hookRemoves end
    local ok, err = pcall(function() Hook.CalculateStats.Remove(TKX_GP2.hookFn) end)
    if ok then
        GP.hooked = false
        G.hookRemoves = tostring(tonumber(G.hookRemoves) + 1)
    else
        G.hookErr = tostring(err)
    end
    G.hooked = tostring(GP.hooked)
    return tostring(ok), tostring(GP.hooked), G.hookRemoves
end
