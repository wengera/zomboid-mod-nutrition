-- TKX_CalcStats server side (X32, X46). Three handlers are added to and removed from
-- Hook.CalculateStats by an OnTick watcher that reads player-modData keys, so the no-handler
-- arm has an EMPTY callback list (a flag read inside a registered handler cannot make it):
--   TKX_calc  -> noop (bumps calls)      TKX_hookA -> A (callsA, returns true)
--   TKX_hookB -> B (callsB, returns false)
-- A key reads as wanted when it is the number 1 or the string "1". The watcher keeps an
-- installed flag per handler and calls Add or Remove only when wanted differs from it; Add and
-- Remove are DOT calls and Remove receives the same closure object that Add received.
-- This file also runs in the client Lua state, so every side test is made at event time.
local function tkxCall(obj, name, ...)
    if obj == nil then return false, nil end
    local m = obj[name]
    if m == nil then return false, nil end
    return pcall(m, obj, ...)
end

local function tkxIsServer()
    if isServer == nil then return false end
    local ok, s = pcall(isServer)
    return ok and s == true
end

local function noop()
    if TKX_CalcStats == nil then return end
    TKX_CalcStats.calls = TKX_CalcStats.calls + 1
end

local function handlerA()
    if TKX_CalcStats == nil then return true end
    TKX_CalcStats.callsA = TKX_CalcStats.callsA + 1
    return true
end

local function handlerB()
    if TKX_CalcStats == nil then return false end
    TKX_CalcStats.callsB = TKX_CalcStats.callsB + 1
    return false
end

local installed = { calc = false, a = false, b = false }

local function isWanted(v)
    return v == 1 or v == "1"
end

local function setInstalled(key, fn, want)
    if installed[key] == want then return end
    if Hook == nil or Hook.CalculateStats == nil then return end
    local hook = Hook.CalculateStats
    local act = hook.Remove
    if want then act = hook.Add end
    if act == nil then return end
    local ok = pcall(act, fn)
    if ok then installed[key] = want end
end

local function tick()
    if TKX_CalcStats == nil then return end
    if not tkxIsServer() then return end
    TKX_CalcStats.side = "server"
    if getOnlinePlayers == nil then return end
    local okList, players = pcall(getOnlinePlayers)
    if not okList or players == nil then return end
    local okSize, size = tkxCall(players, "size")
    if not okSize or size == nil then return end
    local wantCalc = false
    local wantA = false
    local wantB = false
    local i = 0
    while i < size do
        local okGet, player = tkxCall(players, "get", i)
        if okGet and player ~= nil then
            local okMd, md = tkxCall(player, "getModData")
            if okMd and md ~= nil then
                if isWanted(md.TKX_calc) then wantCalc = true end
                if isWanted(md.TKX_hookA) then wantA = true end
                if isWanted(md.TKX_hookB) then wantB = true end
            end
        end
        i = i + 1
    end
    setInstalled("calc", noop, wantCalc)
    setInstalled("a", handlerA, wantA)
    setInstalled("b", handlerB, wantB)
end

if Events ~= nil and Events.OnTick ~= nil then
    Events.OnTick.Add(tick)
end
