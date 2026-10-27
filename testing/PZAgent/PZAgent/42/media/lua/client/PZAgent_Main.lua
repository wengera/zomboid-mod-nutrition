-- PZAgent_Main.lua — the one OnTick hook (loads last by name). The tick order: player → init → poll →
-- act → scan part → frame. No player means nothing is polled or emitted; the link is initialised (M.init) before the
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
M.lastScanEmitMs = 0
M.lastPartEmitMs = 0
M.hooked = M.hooked or false

-- a configuration command: true and the ack's reason when handled, nil when cmd is a goal. scan r queues
-- the chunked scan job under the next scanId (a running one is replaced) and acks "queued"; its parts land from body.
local function config(cmd, p)
    local v = tonumber(cmd.args)
    if cmd.goal == "rate" and v and v > 0 then PZA.sense.RATE = v; return true, "" end
    if cmd.goal == "radius" and v and v > 0 then PZA.sense.ZOMBIE_RADIUS = v; return true, "" end
    if cmd.goal == "scan" and v and v >= 0 then
        if p ~= nil then PZA.sense.scanStart(p, v) end
        return true, "queued"
    end
    return nil
end

function M.init(user)
    PZA.link.init(user)
    local build = getCore and getCore() or nil
    local _, ver = PZA.call(build, "getVersionNumber")
    PZA.emit("hello", { modVersion = PZA.VERSION, build = ver or "", user = user, rate = PZA.sense.RATE, mode = PZA.link.mode })
    if PZA.bench ~= nil and PZA.bench.sizes ~= nil then PZA.emit("bench", PZA.bench.sizes()) end -- probe X2's encoder sizes
    PZA.link.flush()
end

-- the first frame tick that sees a goal's done or failed state reports it once per goal seq; the goal's
-- seq rides as goalSeq, since PZA.emit stamps the line's own seq over a body's seq
local function goalEvent(st, gameMin, worldAge)
    if st.state ~= "done" and st.state ~= "failed" then return end
    if M.lastGoalSeq == st.seq and M.lastGoalState == st.state then return end
    M.lastGoalSeq, M.lastGoalState = st.seq, st.state
    local e = { event = "goal_done", goalSeq = st.seq, gameMin = gameMin, worldAge = worldAge }
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
        local handled, why = config(cmd, p)
        if handled == nil then
            local ok, reason, old = PZA.act.start(cmd, p)
            if old ~= nil then goalEvent(old, PZA.sense.clock()) end
            PZA.link.ack(cmd.seq, ok, reason)
        else PZA.link.ack(cmd.seq, true, why) end
        PZA.link.flush()
    end
    local tAct = PZA.now()
    PZA.act.tick(p)
    -- one chunk of a running scan, emitted (and flushed) as its scanPart line on the tick it is walked. A part is
    -- serialised before its own emit and flush is timed, so part i carries part i-1's as emitMs (part 1 reads 0) and
    -- the last part's lands as the next frame's cost.scanEmitMs; the last part also carries gameMin and worldAge
    local tScan = PZA.now()
    local part = PZA.sense.scanStep(p)
    if part ~= nil then
        if part.part == 1 then M.lastPartEmitMs = 0 end
        part.emitMs = M.lastPartEmitMs
        if part.done then part.gameMin, part.worldAge = PZA.sense.clock() end
        local te = PZA.now()
        PZA.emit("scanPart", part)
        PZA.link.flush()
        M.lastPartEmitMs = PZA.now() - te
        if part.done then M.lastScanEmitMs = M.lastPartEmitMs end
    end
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
        -- scanStepMs is this tick's scan chunk with its part's emit and flush (0 with no job); it is in neither
        -- actMs nor senseMs, and the job's own scanMs sums its chunks' walks. scanEmitMs is the last completed scan's
        -- last part's own emit and flush, carried once on the first frame after it (0 otherwise)
        cur.cost = { actMs = tScan - tAct, scanStepMs = tSense - tScan, senseMs = tLink - tSense, linkMs = M.lastLinkMs,
                     pollMs = tAct - t0, dropped = PZA.link.dropped or 0, scanEmitMs = M.lastScanEmitMs }
        M.lastScanEmitMs = 0
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
