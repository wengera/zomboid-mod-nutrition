-- NR_Server_Players.lua -- the slow clock (spec § 4.1): EveryOneMinute snapshots the online
-- list, initialises a player on first sight (the server fires no join event, #2412), drops a
-- player who left (no disconnect event either, #2403), reads death off the dead flag, and queues
-- the per-player minute work so OnTick drains one player per frame (the stagger). OnNewGame
-- fires server-side for every character a client creates, respawns included (#2411): the record
-- is reset there. Java lists are walked with size()/get(i) (#0940).
local NR = NutritionRevamp
NR.server.players = { online = {}, queue = {}, queueHead = 1, onFirstSight = {}, onDeparture = {},
                      minutes = 0, drained = 0 }
local P = NR.server.players

local function worldAge() return NR.worldAge() or 0 end







local function fire(list, username, player, record)
    for i = 1, #list do
        local ok, err = pcall(list[i], username, player, record)
        if not ok then NR.log.say(2, "players: hook failed: " .. tostring(err)) end
    end
end

-- One player's minute work. Plan 1: refresh lastSeen and the dead flag; later plans append to
-- P.onMinute. Called from the OnTick drain, one player per tick.
P.onMinute = {}
function P.work(username, player)
    local r = NR.server.store.get(username, worldAge())
    if r == nil then return end
    r.lastSeen = worldAge()
    local okD, dead = NR.call(player, "isDead")
    if okD and dead == true and r.dead ~= true then
        r.dead = true
        NR.log.say(2, "players: " .. tostring(username) .. " is dead; record kept until respawn")
    end
    fire(P.onMinute, username, player, r)
end

function P.minute()
    if getOnlinePlayers == nil then return end
    local ok, list = pcall(getOnlinePlayers)
    if not ok or list == nil then return end
    local okS, n = NR.call(list, "size")
    if not okS or type(n) ~= "number" then return end
    P.minutes = P.minutes + 1
    P.queue = {}                      -- a fresh queue each minute: a slow drain never doubles a player (review-t4 I1)
    P.queueHead = 1
    local seen = {}
    local i = 0
    while i < n do
        local okG, player = NR.call(list, "get", i)
        if okG and player ~= nil then
            local okU, username = NR.call(player, "getUsername")
            if okU and username ~= nil then
                seen[username] = player
                if P.online[username] == nil then
                    local r = NR.server.store.get(username, worldAge())
                    NR.log.say(2, "players: first sight of " .. tostring(username))
                    fire(P.onFirstSight, username, player, r)
                    -- no mirror here: NR_Server_Metabolism's onFirstSight hook sends the one first-sight mirror
                end
                P.queue[#P.queue + 1] = username
            end
        end
        i = i + 1
    end
    for username, _ in pairs(P.online) do
        if seen[username] == nil then
            NR.log.say(2, "players: " .. tostring(username) .. " left")
            fire(P.onDeparture, username, nil, nil)
        end
    end
    P.online = seen
    P.queueHead = 1
end

-- The stagger: one queued player per tick; a cheap early-out when the queue is empty, which is
-- what keeps this off the expensive tier (lessons #1071, #1080).
function P.drain()
    local username = P.queue[P.queueHead]
    if username == nil then
        if #P.queue > 0 then P.queue = {}; P.queueHead = 1 end
        return
    end
    P.queueHead = P.queueHead + 1
    local player = P.online[username]
    if player ~= nil then
        P.drained = P.drained + 1
        P.work(username, player)
    end
end

if Events ~= nil then
    if Events.EveryOneMinute ~= nil then
        Events.EveryOneMinute.Add(function() if NR.isServer() then P.minute() end end)
    end
    if Events.OnTick ~= nil then
        Events.OnTick.Add(function() if NR.isServer() then P.drain() end end)
    end
    if Events.OnNewGame ~= nil then
        Events.OnNewGame.Add(function(player, square)
            if not NR.isServer() then return end
            local okU, username = NR.call(player, "getUsername")
            if okU and username ~= nil then
                local r = NR.server.store.reset(username, worldAge())
                if r ~= nil then fire(P.onFirstSight, username, player, r) end   -- Metabolism's hook: the body, then the one mirror
            end
        end)
    end
end
