-- PZAgent_Main.lua — the one OnTick hook (loads last by name). The tick order: player → init → poll →
-- act → frame. No player means nothing is polled or emitted; the link is initialised (M.init) before the
-- first poll, then cmd.txt is polled, the goal runs, and every 60/RATE ticks a frame carries the goal
-- status and the tick's own cost, then flushes. Everything sits inside one pcall; a raise counts in
-- PZA.errors and, once the link is initialised, reports as a lua_error event once a second (its flush
-- under its own pcall, so the handler never raises).
-- A frame's cost.linkMs lags one frame: it is the previous frame tick's flush, since a frame is
-- serialised at its emit, before its own flush has run (the first frame reads 0).
PZA.main = PZA.main or {}
local M = PZA.main
PZA.tick = 0
PZA.errors = 0
M.prev = nil
M.lastErrMs = -1e9
M.lastGoalSeq = nil
M.lastGoalState = nil
M.lastLinkMs = 0
M.hooked = M.hooked or false

local function config(cmd, p)
    local v = tonumber(cmd.args)
    if cmd.goal == "rate" and v and v > 0 then PZA.sense.RATE = v; return true end
    if cmd.goal == "radius" and v and v > 0 then PZA.sense.ZOMBIE_RADIUS = v; return true end
    if cmd.goal == "scan" and v and v >= 0 then
        if p ~= nil then
            local ts = PZA.now()
            local s = PZA.sense.scan(p, v)
            s.scanMs = PZA.now() - ts
            s.gameMin, s.worldAge = PZA.sense.clock()
            PZA.emit("scan", s)
        end
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
    local e = { event = "goal_done", seq = st.seq, gameMin = gameMin, worldAge = worldAge }
    if st.state == "failed" then e.event, e.reason = "goal_failed", st.detail end
    PZA.emit("event", e)
end

local function body()
    PZA.tick = PZA.tick + 1
    local t0 = PZA.now()
    local p = getPlayer()
    if p == nil then return end
    if not M.ready then local _, u = PZA.call(p, "getUsername"); M.init(u or "admin"); M.ready = true end
    local cmd = PZA.link.poll()
    if cmd ~= nil then
        local handled = config(cmd, p)
        if handled == nil then
            local ok, reason, old = PZA.act.start(cmd, p)
            if old ~= nil then goalEvent(old, PZA.sense.clock()) end
            PZA.link.ack(cmd.seq, ok, reason)
        else PZA.link.ack(cmd.seq, true, "") end
        PZA.link.flush()
    end
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
        -- linkMs is the previous frame tick's flush ms (one-frame lag: this frame's flush runs after its emit)
        cur.cost = { actMs = tSense - tAct, senseMs = tLink - tSense, linkMs = M.lastLinkMs, pollMs = tAct - t0, dropped = PZA.link.dropped or 0 }
        PZA.emit("frame", cur)
        M.lastLinkMs = PZA.link.flush()
        M.prev = cur
    end
end

local function onTick()
    local ok, err = pcall(body)
    if not ok then
        PZA.errors = PZA.errors + 1
        local now = PZA.now()
        if M.ready and now - M.lastErrMs >= 1000 then
            M.lastErrMs = now
            PZA.emit("event", { event = "lua_error", msg = tostring(err) })
            pcall(PZA.link.flush)
        end
    end
end

if not M.hooked and Events ~= nil and Events.OnTick ~= nil then
    Events.OnTick.Add(onTick)
    M.hooked = true
end
