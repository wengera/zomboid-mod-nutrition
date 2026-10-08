-- NR_Server_Players.lua -- the slow clock (spec § 4.1): the minute event snapshots the online list, marks each new
-- sight (a first join, a reconnect, a respawn's new object; the server fires no join event, #2412), drops the
-- departed (no disconnect event either, #2403) and merges the queue (K.sched.merge: unserved names carried forward,
-- never doubled); OnTick drains it under a per-tick budget sized to the minute's work (K.sched; Decision 6 (b), rule
-- #3497); first sight, one-shot tasks (the store's flushes) and the harness's extra names ride the same queue; death
-- is read off the dead flag. OnNewGame fires server-side for every character a client creates, respawns included
-- (#2411): it resets the record and evicts the username (#3358); a reset that met no readable clock stays pending
-- and is made in the player's next queue slot. Java lists are walked with size()/get(i) (#0940).
local NR = NutritionRevamp
local K = NR.kernel
NR.server.players = { online = {}, queue = {}, queueHead = 1, onFirstSight = {}, onDeparture = {},
                      minutes = 0, drained = 0, served = 0, sight = {}, resetPending = {}, extraSet = {},
                      tasks = {}, extra = nil, ticks = 0, ticksLast = nil, ticksPrev = nil, meanMs = nil,
                      budgetMs = 15, runCap = 1, wired = false }
local P = NR.server.players

local function fire(list, username, player, record)
    for i = 1, #list do
        local ok, err = pcall(list[i], username, player, record)
        if not ok then NR.log.say(2, "players: hook failed: " .. tostring(err)) end
    end
end

local function nowMs()
    if getTimestampMs == nil then return nil end
    local ok, v = pcall(getTimestampMs)
    if ok and type(v) == "number" then return v end
    return nil
end

-- One player's minute work: refresh lastSeen and the dead flag (OnNewGame's eviction keeps a respawn's reset from
-- the dead body's queued entry, and P.minute never adopts a dead body as a new sight, #3358), then the slow minute's pipeline (NR_Server_Minute.lua), then P.onMinute, kept for a third party's append.
P.onMinute = {}
function P.work(username, player)
    local age = NR.worldAge()
    if age == nil then return end                 -- no clock read: the minute is skipped, never stamped 0
    local r = NR.server.store.get(username, age)
    if r == nil then return end
    r.lastSeen = age
    local okD, dead = NR.call(player, "isDead")
    if okD and dead == true and r.dead ~= true then
        r.dead = true
        NR.log.say(2, "players: " .. tostring(username) .. " is dead; record kept until respawn")
    end
    NR.server.minute.run(username, player, r)
    fire(P.onMinute, username, player, r)
end

-- First sight, run in the player's own queue slot: the store's load, then the first-sight hooks (Metabolism's sends
-- the one first-sight mirror). False when the clock cannot be read (the sight is retried at the next minute).
function P.firstSight(username, player)
    local age = NR.worldAge()
    if age == nil then return false end
    local r = NR.server.store.get(username, age)
    NR.log.say(2, "players: first sight of " .. tostring(username))
    fire(P.onFirstSight, username, player, r)
    return true
end

-- A respawn's reset that OnNewGame could not make (no clock read there), made in the player's queue slot. False
-- while the clock or the store cannot be read: the reset stays pending for the next slot, never dropped.
function P.makeReset(username)
    local age = NR.worldAge()
    if age == nil then return false end
    if NR.server.store.reset(username, age) == nil then return false end
    P.resetPending[username] = nil
    NR.log.say(2, "players: the pending reset of " .. tostring(username) .. " is made")
    return true
end

-- A one-shot task carried in the queue until it runs (the store's departure flush).
function P.task(name, fn)
    P.tasks[name] = fn
end

function P.minute()
    if getOnlinePlayers == nil then return end
    local ok, list = pcall(getOnlinePlayers)
    if not ok or list == nil then return end
    local okS, n = NR.call(list, "size")
    if not okS or type(n) ~= "number" then return end
    P.minutes = P.minutes + 1
    local age = NR.worldAge()
    local roster = {}
    local seen = {}
    local i = 0
    while i < n do
        local okG, player = NR.call(list, "get", i)
        if okG and player ~= nil then
            local okU, username = NR.call(player, "getUsername")
            -- a first sight without a clock read waits for the next minute: the player stays out of seen and
            -- the queue, so no record is made at a nil age and the sight is retried
            -- a new object that reads dead is the respawn's dead body, still listed up to two ticks after OnNewGame
            -- (#3358): never adopted, or its work marks the reset record dead; a raising or absent member reads alive
            if okU and username ~= nil and (P.online[username] ~= nil or age ~= nil) then
                local new = P.online[username] ~= player
                if not (new and NR.flag(player, "isDead")) then
                    seen[username] = player
                    if new then
                        P.sight[username] = player      -- first sight, a reconnect or a respawn's new object
                    end
                    roster[#roster + 1] = username
                end
            end
        end
        i = i + 1
    end
    for username, _ in pairs(P.online) do
        if seen[username] == nil then
            NR.log.say(2, "players: " .. tostring(username) .. " left")
            P.sight[username] = nil
            fire(P.onDeparture, username, nil, nil)
        end
    end
    P.online = seen
    P.extraSet = {}
    if P.extra ~= nil then
        local okX, extra = pcall(P.extra.names)
        if okX and type(extra) == "table" then
            for j = 1, #extra do
                roster[#roster + 1] = extra[j]
                P.extraSet[extra[j]] = true
            end
        end
    end
    for name, _ in pairs(P.tasks) do
        roster[#roster + 1] = name
    end
    P.queue = K.sched.merge(P.queue, P.queueHead, roster)
    P.queueHead = 1
    P.ticksPrev = P.ticksLast
    P.ticksLast = P.ticks
    P.ticks = 0
    if P.meanMs == nil then P.meanMs = K.sched.SEED_MS end
    P.budgetMs = K.sched.budgetMs(P.meanMs, #P.queue, K.sched.ticksPerMinute(P.ticksLast, P.ticksPrev))
    P.runCap = K.sched.runCap(P.budgetMs, P.meanMs)
end

-- One queued name: an online player (its pending reset, then its first sight, when marked), else a one-shot task,
-- else a name of this minute's extra set (an evicted player's stale entry is none of these and runs nothing).
function P.runOne(name)
    local player = P.online[name]
    if player ~= nil then
        if P.resetPending[name] == true and not P.makeReset(name) then
            P.online[name] = nil                        -- no clock: seen again, and sighted, at the next minute
            return
        end
        local sp = P.sight[name]
        if sp ~= nil then
            P.sight[name] = nil
            if not P.firstSight(name, sp) then
                P.online[name] = nil                    -- no clock: seen again, and sighted, at the next minute
                return
            end
        end
        P.drained = P.drained + 1
        P.work(name, player)
        return
    end
    local task = P.tasks[name]
    if task ~= nil then
        P.tasks[name] = nil
        local okT, errT = pcall(task)
        if not okT then NR.log.say(2, "players: task " .. tostring(name) .. " failed: " .. tostring(errT)) end
        return
    end
    if P.extra ~= nil and P.extraSet[name] == true then
        local okX, errX = pcall(P.extra.run, name)
        if not okX then NR.log.say(2, "players: extra " .. tostring(name) .. " failed: " .. tostring(errX)) end
    end
end

-- The drain: queued names until the run cap or the budget's wall time is spent; the tick's cost a run feeds the mean.
function P.drain()
    local t0 = nowMs()
    local ran = 0
    local spent = 0
    while ran < P.runCap do
        local name = P.queue[P.queueHead]
        if name == nil then break end
        P.queueHead = P.queueHead + 1
        P.runOne(name)
        ran = ran + 1
        if t0 ~= nil then
            local t1 = nowMs()
            if t1 ~= nil then spent = t1 - t0 end
            if spent >= P.budgetMs then break end
        end
    end
    P.served = P.served + ran
    if t0 ~= nil and ran > 0 then P.meanMs = K.sched.ema(P.meanMs, spent / ran) end
end

-- The OnTick listener, registered server-side only at OnServerStarted: one add and one compare when the queue is
-- empty (the empty-queue clause of ruling 2: at most 0.1 ms a frame).
function P.tick()
    P.ticks = P.ticks + 1
    if P.queueHead > #P.queue then return end
    P.drain()
end

if Events ~= nil then
    if Events.EveryOneMinute ~= nil then
        Events.EveryOneMinute.Add(function() if NR.isServer() then P.minute() end end)
    end
    if Events.OnServerStarted ~= nil then
        Events.OnServerStarted.Add(function()
            if not NR.isServer() then return end
            if P.wired then return end
            P.wired = true
            if Events.OnTick ~= nil then Events.OnTick.Add(P.tick) end
        end)
    end
    if Events.OnNewGame ~= nil then
        Events.OnNewGame.Add(function(player, square)
            if not NR.isServer() then return end
            local okU, username = NR.call(player, "getUsername")
            if not okU or username == nil then return end
            P.online[username] = nil                    -- #3358: evict; the next minute adopts the new object
            P.sight[username] = nil
            local age = NR.worldAge()
            if age == nil then
                P.resetPending[username] = true         -- made in the player's next queue slot with a clock read
                NR.log.say(2, "players: no world age at OnNewGame for " .. tostring(username)
                    .. "; the reset waits in the queue for a readable clock")
                return
            end
            P.resetPending[username] = nil
            NR.server.store.reset(username, age)
        end)
    end
end
