-- NR_Server_Bus.lua -- the server half of the command bus (mp-model #0932, lessons #1065):
-- module "NutritionRevamp"; the client asks "mirror.request" with no payload and the server
-- answers "mirror" with the flat table K.mirror.build makes. The server never trusts a payload
-- it did not send; in this plan the one client command carries none.
--
-- The effects push (Plan 5 Task 10): the effects adapter calls B.markEffects(username) when the coefficient
-- set is rebuilt or a trait changes (it also sets record.effects.dirty, the flag that survives a save). The
-- flush rides the slow minute (the pipeline's bus step, NR_Server_Minute): when either flag is up and at
-- least PUSH_GAP_MS of server wall clock (getTimestampMs) has passed since this player's last effects push,
-- it sends the WHOLE mirror through B.sendMirror -- the request-time sender, unchanged (ruling T14-1 holds
-- for client reads) -- and clears both flags; a mark inside the gap stays up and goes out at the first slow
-- minute after it. A failed send keeps the flags. The bus step is first in the pipeline's ORDER, so the flush
-- runs first in a player's minute and a mark made in one minute goes out with the next one's flush, carrying
-- the whole of the marking minute's state. First sight and departure forget the transient state (the
-- first-sight mirror, NR_Server_Metabolism's, carries the set).
local NR = NutritionRevamp
local K = NR.kernel
NR.server.bus = {
    module = "NutritionRevamp",
    PUSH_GAP_MS = 60000,       -- game choice: at most one effects push per player per real minute
    REQUEST_GAP_MS = 5000,     -- game choice: at most one answered mirror request per player per 5 s of wall clock
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
        "a class change (energy, hydration, stimulant or sleep rung) or an Overfull level change marks a push at the next slow minute, inside the push gap",
        "each player's first push waits a per-player offset inside the 60 s gap, so pushes first made together spread over the gap",
    },
}
local B = NR.server.bus

function B.meta()
    local o = NR.server.options
    return { mode = o and o.mode or 1, version = NR.version, build = NR.build }
end

local function nowMs()
    if getTimestampMs == nil then return nil end
    local ok, v = pcall(getTimestampMs)
    if ok and type(v) == "number" then return v end
    return nil
end

function B.sendMirror(player, record)
    if player == nil or record == nil then return false end
    if sendServerCommand == nil then return false end
    local okB, m = pcall(K.mirror.build, record, B.meta(), NR.data and NR.data.records and NR.data.records.ORDER)
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
            local r = NR.server.store.get(username, NR.worldAge())
            if r ~= nil then B.sendMirror(player, r) end
        end
    end)
end

-- The effects push. markEffects is the hook NR_Server_Effects calls (it checks for it by name).
function B.markEffects(username)
    if username == nil then return end
    B.effects.dirty[username] = true
    B.effects.stats.marks = B.effects.stats.marks + 1
end

-- One player's flush, from the slow minute. Returns true when it pushed.
function B.flushEffects(username, player, record)
    if username == nil or record == nil then return false end
    if not NR.isServer() then return false end
    local body, fl, ac = record.body, record.fluids, record.acute
    local sig = K.view.pushSignature(body and body.energyState, fl and fl.dehydPct, ac and ac.caf, ac and ac.debtH, K.mirror.stomachMass(record))
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

-- First sight and departure: the transient state forgotten; at first sight the record's flag cleared too,
-- since the first-sight mirror carries the whole set.
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

-- The band mark (Plan 8 ruling 7): NR_Server_Weight calls B.markBand(username) when the body band changes
-- (the mirror's body_band). It IS the effects mark -- one dirty flag, one PUSH_GAP_MS gap, one flush -- and
-- is counted apart. The first-sight and OnNewGame mirrors (NR_Server_Metabolism's) stay unconditional.
function B.markBand(username)
    if username == nil then return end
    B.effects.stats.bandMarks = B.effects.stats.bandMarks + 1
    B.markEffects(username)
end
