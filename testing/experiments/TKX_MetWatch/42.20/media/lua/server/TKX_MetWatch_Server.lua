-- TKX_MetWatch server (X37, X38, X36): what the server sees of a connected player's activity.
-- The driver arms a window through `globalmoddata.set TKX_MetWatch arm <seconds>` (the global-
-- modData table "TKX_MetWatch", key `arm`, 0 < seconds <= 300). The first online player is
-- sampled EVERY server tick until the wall-clock window ends (per-tick samples are the
-- measurement, so this is an OnTick handler; #1071 prices OnTick as the expensive tier, so the
-- handler's FIRST statement is the nil-cheap `state.armed` test and, while unarmed, it looks at
-- the modData key only every 30th tick). Per sample, each hop index-first (#0935):
--   target    getBodyDamage():getThermoregulator():getMetabolicTarget()
--   rate      ...:getMetabolicRate()
--   moving / running / sprinting   isPlayerMoving() / isRunning() / isSprinting()
--   calmod    getCharacterActions() (a java.util.Stack): get(0):getTable().caloriesModifier,
--             or the string "unreadable:<failing hop>" ("noaction" when the stack is empty)
--   squats    getFitness():getRegularity("squats")
--   invw      getInventoryWeight()
-- At the window end the global modData table gets FLAT scalar keys only (#2848):
--   status ("armed" | "done"), samples (count), windowMs,
--   hist_<field>_<value>   a count per value (numbers rounded to 0.1, booleans, calmod strings),
--   raw_1 .. raw_50        the first 50 samples as "t=<ms> target=.. rate=.. mv=.. run=.. spr=.. ...".
-- Install-once (#2845): the sentinel TKX_MetWatch_Installed is a global of its own; the handler
-- registers at file scope behind the nil-checked isServer() test, once, never at a boot event.
local function tkxServer()
    if isServer == nil then return false end
    local ok, s = pcall(isServer)
    return ok and s == true
end

local state = { armed = false, idle = 0 }

local function num(v)
    if type(v) ~= "number" then return tostring(v) end
    return tostring(math.floor(v * 10 + 0.5) / 10)
end

local function hop(obj, name, ...)
    if obj == nil then return nil end
    local f = obj[name]
    if f == nil then return nil end
    local ok, v = pcall(f, obj, ...)
    if not ok then return nil end
    return v
end

local function readCalMod(p)
    local acts = hop(p, "getCharacterActions")
    if acts == nil then return "unreadable:getCharacterActions" end
    local n = hop(acts, "size")
    if n == nil then return "unreadable:size" end
    if n == 0 then return "noaction" end
    local a = hop(acts, "get", 0)
    if a == nil then return "unreadable:get(0)" end
    local tbl = hop(a, "getTable")
    if tbl == nil then return "unreadable:getTable" end
    local cm = tbl["caloriesModifier"]
    if cm == nil then return "unreadable:caloriesModifier" end
    return num(cm)
end

local function bumpHist(h, field, value)
    local key = "hist_" .. field .. "_" .. tostring(value)
    h[key] = (h[key] or 0) + 1
end

local function sample(p)
    local bd = hop(p, "getBodyDamage")
    local th = hop(bd, "getThermoregulator")
    local target = hop(th, "getMetabolicTarget")
    local rate = hop(th, "getMetabolicRate")
    local fit = hop(p, "getFitness")
    local reg = hop(fit, "getRegularity", "squats")
    return {
        target = target == nil and "unreadable" or num(target),
        rate = rate == nil and "unreadable" or num(rate),
        mv = tostring(hop(p, "isPlayerMoving")),
        run = tostring(hop(p, "isRunning")),
        spr = tostring(hop(p, "isSprinting")),
        calmod = readCalMod(p),
        squats = reg == nil and "unreadable" or num(reg),
        invw = num(hop(p, "getInventoryWeight")),
    }
end

local function finish(t)
    for k, v in pairs(state.hist) do t[k] = v end
    for i = 1, #state.raw do t["raw_" .. i] = state.raw[i] end
    t["samples"] = state.count
    t["windowMs"] = state.windowMs
    t["status"] = "done"
    t["arm"] = 0
    state.armed = false
end

local function onTick()
    if not state.armed then
        state.idle = state.idle + 1
        if state.idle < 30 then return end
        state.idle = 0
        if ModData == nil then return end
        local t = ModData.getOrCreate("TKX_MetWatch")
        local secs = tonumber(t["arm"])
        if secs == nil or secs <= 0 then return end
        if secs > 300 then secs = 300 end
        state.armed = true
        state.start = getTimestampMs()
        state.deadline = state.start + secs * 1000
        state.windowMs = secs * 1000
        state.hist = {}
        state.raw = {}
        state.count = 0
        t["arm"] = 0
        t["status"] = "armed"
        return
    end
    local players = nil
    if getOnlinePlayers ~= nil then players = getOnlinePlayers() end
    local now = getTimestampMs()
    local nPlayers = hop(players, "size")
    local first = nil
    if nPlayers ~= nil and nPlayers > 0 then first = hop(players, "get", 0) end
    if first ~= nil then
        local s = sample(first)
        state.count = state.count + 1
        bumpHist(state.hist, "target", s.target)
        bumpHist(state.hist, "rate", s.rate)
        bumpHist(state.hist, "mv", s.mv)
        bumpHist(state.hist, "run", s.run)
        bumpHist(state.hist, "spr", s.spr)
        bumpHist(state.hist, "calmod", s.calmod)
        bumpHist(state.hist, "squats", s.squats)
        bumpHist(state.hist, "invw", s.invw)
        if state.count <= 50 then
            state.raw[state.count] = "t=" .. tostring(now - state.start) .. " target=" .. s.target
                .. " rate=" .. s.rate .. " mv=" .. s.mv .. " run=" .. s.run .. " spr=" .. s.spr
                .. " calmod=" .. s.calmod .. " squats=" .. s.squats .. " invw=" .. s.invw
        end
    end
    if now >= state.deadline then
        finish(ModData.getOrCreate("TKX_MetWatch"))
    end
end

if tkxServer() and TKX_MetWatch_Installed == nil then
    TKX_MetWatch_Installed = true
    if Events ~= nil and Events.OnTick ~= nil then
        Events.OnTick.Add(onTick)
    end
end
