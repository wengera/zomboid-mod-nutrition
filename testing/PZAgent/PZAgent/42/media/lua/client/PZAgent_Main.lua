-- PZAgent_Main.lua — the one OnTick hook (spec § 8, Plan 22 Task 6). The tick order: player → init → poll → skills →
-- sense → map → flush. No player means nothing is polled, emitted or flushed. The first tick with a player is the init
-- tick: the Link initialised (M.init), hello, the inventory's first sight as item_added events (under its own pcall:
-- M.ready is set after hello, so a raise there is one lua_error, never a re-init) and one flush, and nothing else.
-- Every later tick: the poll (scan{r} and rate{hz} answered here by one act line, ruling P22-5; every
-- other command to the runner, K.start), the running skill's tick (K.tick), every max(1, floor(60 / S.RATE)) ticks
-- the events and the frame read (S.events, or S.frame on the first), the map (the scan job's next part while a job
-- runs, else, on the watch's ticks (MP.watchDue: every 6th whatever the rate), its next squares), an overflow event when the Link cut its backlog, the frame emitted with its
-- cost group, and one L.flush, called once every tick (it writes nothing when both queues are empty).
-- The first frame comes from S.frame, later ones carry S.events, so the first window's door states are recorded without
-- an event (S.events' door rule: one first seen is recorded silently).
-- The frame is read in the sense phase and emitted after the map so its cost carries this tick's map ms; its cost on
-- the 1 ms clock (PZA.now, getTimestampMs: ruling P22-4): tickMs the previous tick's whole body, actMs this tick's
-- K.tick, senseMs this tick's events and frame read, mapMs this tick's scan or watch step, linkMs the previous tick's
-- flush (a frame is encoded at its emit, before its own flush), tickMaxMs the worst body since the last frame and
-- over5 the bodies of 5 ms or more since it (the ticks before this one), dropped the Link's dropped lines; pollMs this
-- tick's L.poll (its ack write included), startMs this tick's command start (Main's scan or rate answer, else K.start),
-- and the per-phase maxima since the last frame (X4 fix pass, review I8: a burst on a tick that writes no frame is
-- attributed): maxPollMs, maxStartMs, maxActMs, maxSenseMs and maxMapMs over every tick since the last frame's emit,
-- this one included, and maxLinkMs over the flushes since it (the last frame's own flush included, this tick's not).
-- Main loads before Map, Motor, Sense, Skills and SkillsWorld (client files load by name), so it reaches them only at
-- tick time.
-- Everything sits inside one pcall; a raise counts in PZA.errors and, once the link is initialised, reports as a
-- lua_error event once a second (its flush under its own pcall, so the handler never raises). The map phase runs under
-- its own pcall besides (ruling S-15 extended to the map): a raise there counts in PZA.errors and PZA.map.errors, is
-- named raise:map in PZA.map.missing and reports as a lua_error under the same once-a-second limit, a running scan job is
-- dropped (its walk would retry the raising square every tick), and the tick goes on to emit its frame and flush.
PZA.main = PZA.main or {}
local M = PZA.main
PZA.tick = 0
PZA.errors = 0
M.ready = false
M.prev = nil
M.lastErrMs = -1e9
M.OVER_MS = 5
M.lastBodyMs = 0
M.lastLinkMs = 0
M.maxMs = 0
M.over5 = 0
M.PHASES = { "poll", "start", "act", "sense", "map", "link" }
M.phaseMax = {}
for _, ph in ipairs(M.PHASES) do M.phaseMax[ph] = 0 end
M.hooked = M.hooked or false

-- a phase's span into its maximum since the last frame
local function noteMax(ph, ms)
    if ms > M.phaseMax[ph] then M.phaseMax[ph] = ms end
end

-- the game clock's minute, or 0 while Sense cannot read it (a lua_error may come from Sense itself)
local function gameMin()
    local S = PZA.sense
    if S == nil or S.clock == nil then return 0 end
    local ok, m = pcall(S.clock)
    return (ok and type(m) == "number") and m or 0
end

-- hello's caps: every type this build accepts, the runner's skills and Main's scan and rate, sorted
local function caps()
    local out = { "rate", "scan" }
    for k in pairs(PZA.skills.types) do out[#out + 1] = k end
    table.sort(out)
    return out
end

-- a raise caught by Main: counted in PZA.errors and, once the link is initialised, emitted as a lua_error event at
-- most once a second (the caller flushes); answers true when it emitted
local function reportError(err)
    PZA.errors = PZA.errors + 1
    local now = PZA.now()
    if not M.ready or now - M.lastErrMs < 1000 then return false end
    M.lastErrMs = now
    PZA.emit("event", { event = "lua_error", gameMin = gameMin(), msg = tostring(err) })
    return true
end

-- the inventory's first sight as item_added events (under M.init's pcall: a raise here is reported, never re-inits)
local function firstSight(p)
    local ev = PZA.sense.firstSight(p)
    for i = 1, #ev do PZA.emit("event", ev[i]) end
end

-- the init tick's work (p, the player, read again when absent). M.ready is set once the Link is initialised and hello
-- emitted, so a raise after that point never runs L.init again; the first sight runs under its own pcall, its raise
-- reported as a lua_error on this tick, and the one flush follows either way
function M.init(user, p)
    local L, S = PZA.link, PZA.sense
    L.init(user)
    local core = getCore and getCore() or nil
    local _, ver = PZA.call(core, "getVersionNumber")
    PZA.emit("hello", { proto = PZA.schema.PROTO, mod = PZA.VERSION, build = ver or "", user = user, rate = S.RATE,
                        caps = caps(), mode = L.mode })
    M.ready = true
    local ok, err = pcall(firstSight, p or getPlayer())
    if not ok then reportError(err) end
    M.lastLinkMs = L.flush()
    noteMax("link", M.lastLinkMs)
end

-- a whole number in lo..hi
local function whole(v, lo, hi)
    return type(v) == "number" and v == math.floor(v) and v >= lo and v <= hi
end

-- scan{r} (r in 1..30) and rate{hz} (hz in 1..60), answered by one act line: done with { queued = the job's parts } /
-- { hz }, or rejected bad args (an empty aid, a bad argument) or not loaded (the player's position unreadable). Neither
-- touches the runner's skill. Answers true when cmd was one of the two.
local function mainCommand(cmd, p)
    local typ = cmd.type
    if typ ~= "scan" and typ ~= "rate" then return false end
    local K = PZA.skills
    local a = cmd.args
    local body = { aid = cmd.aid, type = typ, state = "rejected", reason = "bad args", result = {} }
    if type(cmd.aid) == "string" and cmd.aid ~= "" then
        if typ == "rate" and whole(a.hz, 1, 60) then
            PZA.sense.RATE = a.hz
            PZA.link.forceFull = true
            body.state, body.reason, body.result = "done", "", { hz = a.hz }
        elseif typ == "scan" and whole(a.r, 1, 30) then
            local parts = PZA.map.scanStart(p, a.r)
            if parts ~= nil then
                body.state, body.reason, body.result = "done", "", { queued = parts }
            else
                body.reason = "not loaded"
            end
        end
    end
    body.snapshot = K.snapshot(p)
    PZA.emit("act", body)
    return true
end

-- the map phase: the scan job's next part while a job runs, else the watch's next squares on the watch's ticks
local function mapStep(p)
    local MP = PZA.map
    if MP.job ~= nil then
        MP.scanStep(p)
    elseif MP.watchDue(PZA.tick) then
        MP.watchStep(p)
    end
end

-- a raise in the map phase (S-15): counted and named on the map, the job dropped, reported as Main reports any raise
local function mapRaised(err)
    local MP = PZA.map
    MP.errors = (MP.errors or 0) + 1
    MP.lastError = tostring(err)
    MP.job = nil
    PZA.missing(MP.missing, "raise:map")
    reportError(err)
end

local function body()
    PZA.tick = PZA.tick + 1
    local p = getPlayer()
    if p == nil then return end
    if not M.ready then
        local _, u = PZA.call(p, "getUsername")
        M.init(u or "admin", p)
        return
    end
    local L, K, S = PZA.link, PZA.skills, PZA.sense
    local tp = PZA.now()
    local cmd = L.poll()
    local t0 = PZA.now()
    if cmd ~= nil and not mainCommand(cmd, p) then K.start(cmd, p) end
    local ts = PZA.now()
    K.tick(p)
    local t1 = PZA.now()
    local cur = nil
    if PZA.tick % math.max(1, math.floor(60 / S.RATE)) == 0 then
        local ev = nil
        if M.prev ~= nil then ev, cur = S.events(p, M.prev) else cur = S.frame(p) end
        if ev ~= nil then for i = 1, #ev do PZA.emit("event", ev[i]) end end
    end
    local t2 = PZA.now()
    local okMap, errMap = pcall(mapStep, p)
    if not okMap then mapRaised(errMap) end
    local t3 = PZA.now()
    local pollMs, startMs, actMs, senseMs, mapMs = t0 - tp, ts - t0, t1 - ts, t2 - t1, t3 - t2
    noteMax("poll", pollMs); noteMax("start", startMs); noteMax("act", actMs)
    noteMax("sense", senseMs); noteMax("map", mapMs)
    if L.overflow ~= nil then
        PZA.emit("event", { event = "overflow", gameMin = gameMin(), queued = L.overflow.queued, cut = L.overflow.cut })
        L.overflow = nil
    end
    if cur ~= nil then
        local mx = M.phaseMax
        cur.cost = { tickMs = M.lastBodyMs, actMs = actMs, senseMs = senseMs, mapMs = mapMs, linkMs = M.lastLinkMs,
                     tickMaxMs = M.maxMs, over5 = M.over5, dropped = L.dropped or 0, pollMs = pollMs, startMs = startMs,
                     maxActMs = mx.act, maxSenseMs = mx.sense, maxMapMs = mx.map, maxLinkMs = mx.link,
                     maxPollMs = mx.poll, maxStartMs = mx.start }
        M.maxMs, M.over5 = 0, 0
        for _, ph in ipairs(M.PHASES) do mx[ph] = 0 end
        PZA.emitFrame(cur)
        M.prev = cur
    end
    M.lastLinkMs = L.flush()
    noteMax("link", M.lastLinkMs)
end

local function onTick()
    local t0 = PZA.now()
    local ok, err = pcall(body)
    local ms = PZA.now() - t0
    M.lastBodyMs = ms
    if ms > M.maxMs then M.maxMs = ms end
    if ms >= M.OVER_MS then M.over5 = M.over5 + 1 end
    if not ok and reportError(err) then
        -- the raised tick's flush (its body ms above already fed tickMaxMs and over5); its ms is the next frame's linkMs
        local okF, fms = pcall(PZA.link.flush)
        if okF and type(fms) == "number" then
            M.lastLinkMs = fms
            noteMax("link", fms)
        end
    end
end

if not M.hooked and Events ~= nil and Events.OnTick ~= nil then
    Events.OnTick.Add(onTick)
    M.hooked = true
end
