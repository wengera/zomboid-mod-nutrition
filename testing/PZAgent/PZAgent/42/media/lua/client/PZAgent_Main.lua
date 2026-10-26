-- PZAgent_Main.lua — the one OnTick hook (loads last by name). Each tick: poll cmd.txt, run the goal,
-- emit a frame every 60/RATE ticks with the goal status and the tick's own cost, flush. Everything sits
-- inside one pcall; a raise counts in PZA.errors and reports as a lua_error event once a second.
PZA.main = PZA.main or {}
local M = PZA.main
PZA.tick = 0
PZA.errors = 0
M.prev = nil
M.lastErrMs = -1e9
M.lastGoalSeq = nil
M.lastGoalState = nil
M.hooked = M.hooked or false

local function config(cmd)
    local v = tonumber(cmd.args)
    if cmd.goal == "rate" and v and v > 0 then PZA.sense.RATE = v; return true end
    if cmd.goal == "radius" and v and v > 0 then PZA.sense.ZOMBIE_RADIUS = v; return true end
    if cmd.goal == "scan" and v and v >= 0 then
        local okP, p = pcall(getPlayer)
        if okP and p ~= nil then local s = PZA.sense.scan(p, v); s.gameMin, s.worldAge = PZA.sense.clock(); PZA.emit("scan", s) end
        return true
    end
    return nil
end

function M.init(user)
    PZA.link.init(user)
    local build = getCore and getCore() or nil
    local _, ver = PZA.call(build, "getVersionNumber")
    PZA.emit("hello", { modVersion = PZA.VERSION, build = ver or "", user = user, rate = PZA.sense.RATE, mode = PZA.link.mode })
    PZA.link.flush()
end

-- the first frame tick that sees a goal's done or failed state reports it once per goal seq
local function goalEvent(st, gameMin, worldAge)
    if st.state ~= "done" and st.state ~= "failed" then return end
    if M.lastGoalSeq == st.seq and M.lastGoalState == st.state then return end
    M.lastGoalSeq, M.lastGoalState = st.seq, st.state
    local e = { event = "goal_done", gameMin = gameMin, worldAge = worldAge }
    if st.state == "failed" then e.event, e.reason = "goal_failed", st.detail end
    PZA.emit("event", e)
end

local function body()
    PZA.tick = PZA.tick + 1
    local t0 = PZA.now()
    local cmd = PZA.link.poll()
    if cmd ~= nil then
        local handled = config(cmd)
        if handled == nil then
            local ok, reason = PZA.act.start(cmd)
            PZA.link.ack(cmd.seq, ok, reason)
        else PZA.link.ack(cmd.seq, true, "") end
    end
    local p = getPlayer()
    if p == nil then return end
    if not M.ready then local _, u = PZA.call(p, "getUsername"); M.init(u or "admin"); M.ready = true end
    local tAct = PZA.now()
    PZA.act.tick(p)
    local tSense = PZA.now()
    local every = math.max(1, math.floor(60 / PZA.sense.RATE))
    if PZA.tick % every == 0 then
        local ev, cur = {}, nil
        if M.prev ~= nil then ev, cur = PZA.sense.events(p, M.prev) else cur = PZA.sense.frame(p) end
        local gameMin, worldAge = PZA.sense.clock()
        for i = 1, #ev do ev[i].gameMin, ev[i].worldAge = gameMin, worldAge; PZA.emit("event", ev[i]) end
        local st = PZA.act.status()
        goalEvent(st, gameMin, worldAge)
        cur.goal = st
        cur.gameMin, cur.worldAge = gameMin, worldAge
        local tLink = PZA.now()
        cur.cost = { actMs = tSense - tAct, senseMs = tLink - tSense, linkMs = 0, pollMs = tAct - t0, dropped = PZA.link.dropped or 0 }
        PZA.emit("frame", cur)
        cur.cost.linkMs = PZA.link.flush()
        M.prev = cur
    end
end

local function onTick()
    local ok, err = pcall(body)
    if not ok then
        PZA.errors = PZA.errors + 1
        local now = PZA.now()
        if now - M.lastErrMs >= 1000 then
            M.lastErrMs = now
            PZA.emit("event", { event = "lua_error", msg = tostring(err) })
            PZA.link.flush()
        end
    end
end

if not M.hooked and Events ~= nil and Events.OnTick ~= nil then
    Events.OnTick.Add(onTick)
    M.hooked = true
end
