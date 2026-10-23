-- NR_Server_Bus.lua: the server half of the command bus (#0932): the client asks "mirror.request" with no payload and
-- the server answers "mirror" with K.mirror.build's flat table. The server never trusts a payload it did not send.
-- The effects push: a mark (B.markEffects, and record.effects.dirty, which survives a save) is flushed by the bus step,
-- first in ORDER, at least PUSH_GAP_MS of wall clock after this player's last push: the WHOLE mirror through
-- B.sendMirror. A mark inside the gap stays up; a failed send keeps the flags.
local NR = NutritionRevamp
local K = NR.kernel
NR.server.bus = {
    module = "NutritionRevamp",
    PUSH_GAP_MS = K.dials.get("bus.PUSH_GAP_MS"),
    REQUEST_GAP_MS = K.dials.get("bus.REQUEST_GAP_MS"),
    wired = false,
    effects = { dirty = {}, last = {}, stats = { marks = 0, pushes = 0, deferred = 0, failed = 0, bandMarks = 0 } },
    requests = { last = {}, stats = { answered = 0, denied = 0 } },
    lastSig = {},              -- username -> K.view.pushSignature at the player's last flush
    build = { failed = 0 },    -- mirror builds that raised (outside effects.stats, which the golden trace walks)
    limitations = {
        "an effects change (B.markEffects) or a body band change (B.markBand, the same mark) is pushed at most once per player per 60 s of server wall clock; a change inside the gap waits for the first slow minute after it",
        "the push rides the player's next slow minute: a change made in one game minute reaches the client with the next one's flush",
        "with no getTimestampMs the gap is the slow minute itself",
        "a mirror request is answered at most once per player per 5 s of server wall clock; a denied request is counted and dropped",
        "a change of the stimulant or sleep rung, the Overfull level, the whole dehydration per cent, the weight-trend word or the set of active drain states marks a push at the next slow minute, inside the push gap",
        "each player's first push waits a per-player offset inside the 60 s gap, so pushes first made together spread over the gap",
    },
}
local B = NR.server.bus

function B.meta()
    return { mode = NR.runningMode(), version = NR.version, build = NR.build }
end

local nowMs = NR.nowMs

function B.sendMirror(player, record)
    if player == nil or record == nil then return false end
    if sendServerCommand == nil then return false end
    local okB, m = pcall(K.mirror.build, record, B.meta(), NR.data and NR.data.records and NR.data.records.ORDER, NR.strengthP())
    if not okB then
        B.build.failed = B.build.failed + 1
        NR.log.say(2, "bus: mirror build failed for " .. tostring(record.username) .. ": " .. tostring(m))
        return false
    end
    local ok = pcall(sendServerCommand, player, B.module, "mirror", m)
    if not ok then NR.log.say(2, "bus: sendServerCommand failed for " .. tostring(record.username)) end
    return ok
end

if Events ~= nil and Events.OnClientCommand ~= nil then
    Events.OnClientCommand.Add(function(module, command, player, args)
        if module ~= B.module then return end
        if not NR.isServer() then return end
        if command == "mirror.request" then
            local okU, username = NR.call(player, "getUsername")
            if not okU or username == nil then return end
            local now = nowMs()
            local last = B.requests.last[username]
            if now ~= nil and last ~= nil and now >= last and now - last < B.REQUEST_GAP_MS then
                B.requests.stats.denied = B.requests.stats.denied + 1
                return
            end
            B.requests.last[username] = now
            B.requests.stats.answered = B.requests.stats.answered + 1
            local r = NR.server.store.get(username, NR.worldAge(), player)
            if r ~= nil and r.dead ~= true then B.sendMirror(player, r) end
        end
    end)
end

-- NR_Server_Effects checks for markEffects by name.
function B.markEffects(username)
    if username == nil then return end
    B.effects.dirty[username] = true
    B.effects.stats.marks = B.effects.stats.marks + 1
end

function B.flushEffects(username, player, record)
    if username == nil or record == nil then return false end
    if not NR.isServer() then return false end
    local body, fl, ac, D = record.body, record.fluids, record.acute, record.drain
    local trend = nil
    if body ~= nil then trend = K.view.trendIndex(K.mirror.trend(body, body.fm + body.lm + body.lx)) end
    local sig = K.view.pushSignature(fl and fl.dehydPct, ac and ac.caf, ac and ac.debtH, K.mirror.stomachMass(record), K.view.drainSignal(D), trend)
    if B.lastSig[username] ~= nil and B.lastSig[username] ~= sig then B.effects.dirty[username] = true end
    B.lastSig[username] = sig
    local E = record.effects
    local recDirty = type(E) == "table" and E.dirty == true
    if B.effects.dirty[username] ~= true and not recDirty then return false end
    local now = nowMs()
    local last = B.effects.last[username]
    if now ~= nil and last == nil then
        last = now - B.PUSH_GAP_MS + K.view.pushOffset(username, B.PUSH_GAP_MS)  -- the first gap is this player's phase
        B.effects.last[username] = last
    end
    if now ~= nil and last ~= nil and now >= last and now - last < B.PUSH_GAP_MS then
        B.effects.stats.deferred = B.effects.stats.deferred + 1
        return false
    end
    if not B.sendMirror(player, record) then
        B.effects.stats.failed = B.effects.stats.failed + 1
        return false
    end
    B.effects.last[username] = now
    B.effects.dirty[username] = nil
    if type(E) == "table" then E.dirty = false end
    B.effects.stats.pushes = B.effects.stats.pushes + 1
    return true
end

-- At first sight the record's flag is cleared too, since the first-sight mirror carries the whole set.
function B.forgetEffects(username, player, record)
    if username == nil then return end
    B.effects.dirty[username] = nil
    B.effects.last[username] = nil
    B.lastSig[username] = nil
    B.requests.last[username] = nil
    if record ~= nil and type(record.effects) == "table" then record.effects.dirty = false end
end

if Events ~= nil and Events.OnServerStarted ~= nil then
    Events.OnServerStarted.Add(function()
        if not NR.isServer() then return end
        if B.wired then return end
        local P = NR.server.players
        if P == nil then return end
        B.wired = true
        NR.server.minute.register("bus", B.flushEffects)
        P.onFirstSight[#P.onFirstSight + 1] = B.forgetEffects
        P.onDeparture[#P.onDeparture + 1] = B.forgetEffects
    end)
end

-- It IS the effects mark (one flag, one gap, one flush), counted apart.
function B.markBand(username)
    if username == nil then return end
    B.effects.stats.bandMarks = B.effects.stats.bandMarks + 1
    B.markEffects(username)
end

