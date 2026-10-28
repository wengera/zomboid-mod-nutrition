-- PZAgent_Skills.lua — the skill runner and its skills (Plan 22 spec § 7): skills, not machines. A command
-- {seq, aid, type, args} from the Link's poll starts one skill, a bounded engine action with a typed result; the
-- planner owns every decision between skills. Each skill is K.types[type] = { check, tick }:
--   check(args, p) -> ok, reason, st   validates and converts the decoded args; st is the skill's private state
--   tick(p, st) -> nil | "done", result | "failed", reason   one tick of the running skill; a skill never emits
--   stop(p, st, reason)   optional: the runner calls it at a skill's end in any state but done (failed with its reason,
--                         superseded included), after MO.off and before the act line, under pcall (a raise counted in
--                         K.errors, never propagated); sleep's wakes the character (ruling P23-AB)
-- The runner owns every act line (PZA.emit("act", {aid, type, state, reason, result, snapshot}), the schema's act
-- shape): accepted and progress carry result {} and no snapshot; rejected, failed and done carry K.snapshot(p);
-- reason is "" unless rejected or failed; result is {} unless done. At every end (done, failed, superseded) the runner
-- calls MO.off(p), and on every failure it clears the vanilla timed-action queue. A dead player is rejected for every
-- type but stop (a dead body's running skill can still be stopped). Every Java member is reached through PZA.call, and
-- every vanilla class and its member are index-checked before the call. A raise inside a skill's check or tick (ruling
-- S-12) is caught by the runner: a check's raise is rejected bad args, a tick's raise ends the skill failed interrupted,
-- each counted in K.errors with its message in K.lastError; a caught raise still parks the -debug client (#0957), so the
-- index-first rule stands and this guard only keeps the runner's state consistent on a release client. Ruling S-15
-- extends it to the runner's own reads: the dead check in K.start (a raise is rejected interrupted), every read of
-- K.snapshot (a raise leaves its field absent) and MO.off at a skill's end, each counted in K.errors; the runner goes
-- idle before its end line, so a raise never leaves K.cur set.
-- The skills: walkTo, steer, stop (movement) here; attack, interact, equip, consume, drop (one engine action each, ported
-- from Plan 21's PZAgent_Act.lua goals, whose state machines with several steps are the planner's now) in
-- PZAgent_SkillsWorld.lua, which loads after this file (client files load by name, "." before "W") and registers them
-- into K.types. Positions are read through the shared world readers (PZA.world, shared/PZAgent_World.lua).
PZA.skills = PZA.skills or {}
local K = PZA.skills
local MO = PZA.motor
local W = PZA.world
K.types = K.types or {}
K.cur = nil
K.PROGRESS_MS = 1000
K.errors = 0              -- raises caught inside a skill's check or tick (S-12)
K.lastError = nil         -- the last caught raise's message

-- ---- the runner's helpers (PZAgent_SkillsWorld.lua's skills reach these through K) ----------------------------------

-- the overall body health, or nil when it cannot be read
local function healthOf(p)
    local _, bd = PZA.call(p, "getBodyDamage")
    local ok, h = PZA.call(bd, "getOverallBodyHealth")
    if ok then return h end
    return nil
end

-- dead only on a reading of 0 or less; an absent reading is not dead
local function isDead(p)
    local h = healthOf(p)
    return h ~= nil and h <= 0
end

-- posOf(p): the player's world x and y, each nil when absent or not a number
local posOf = W.posOf

-- the straight-line distance from the player to (x, y), or nil when the position cannot be read
local function dist(p, x, y)
    local px, py = posOf(p)
    if px == nil or py == nil then return nil end
    local ex, ey = px - x, py - y
    return math.sqrt(ex * ex + ey * ey)
end

-- true when the vanilla timed-action queue and its add are loaded (index-checked, never called to find out)
local function queueLoaded()
    return ISTimedActionQueue ~= nil and ISTimedActionQueue.add ~= nil
end

-- clears the player's vanilla timed-action queue: the class and its clear index-checked first (an unloaded queue has
-- nothing to clear), the call under pcall for a raise inside vanilla Lua
local function clearQueue(p)
    if ISTimedActionQueue ~= nil and ISTimedActionQueue.clear ~= nil then pcall(ISTimedActionQueue.clear, p) end
end

-- queues the vanilla walk to sq; false when the queue or the walk class or its new is not loaded (index-checked before
-- the call: a missing one is the skill's own failure, never a raise under pcall; walkTo maps it to no path, the reason
-- a refused walk already takes), each call under pcall for a raise inside vanilla Lua
local function queueWalk(p, sq)
    if not queueLoaded() or ISWalkToTimedAction == nil or ISWalkToTimedAction.new == nil then return false end
    local made, action = pcall(ISWalkToTimedAction.new, ISWalkToTimedAction, p, sq)
    if not made or action == nil then return false end
    local ran = pcall(ISTimedActionQueue.add, action)
    return ran
end

-- the gait from the args: walk when absent, nil when not one of the schema's gaits
local function gaitOf(args)
    local g = args.gait
    if g == nil then return "walk" end
    if type(g) ~= "string" or PZA.schema.gaits[g] ~= true then return nil end
    return g
end

K.healthOf, K.isDead, K.posOf, K.dist = healthOf, isDead, posOf, dist
K.queueLoaded, K.clearQueue, K.queueWalk, K.gaitOf = queueLoaded, clearQueue, queueWalk, gaitOf

-- ---- the runner -----------------------------------------------------------------------------------------------------

-- a raise the runner caught (S-12 inside a skill's check or tick; S-15 in its own reads and at a skill's end): counted,
-- its message kept
local function caught(err)
    K.errors = K.errors + 1
    K.lastError = tostring(err)
end

-- fn(...)'s answer, or nil with the raise caught (S-15: a raising Java member inside a present one is a supported fault)
local function safely(fn, ...)
    local ok, v, w = pcall(fn, ...)
    if ok then return v, w end
    caught(v)
    return nil, nil
end

local function zOf(p)
    local _, z = PZA.call(p, "getZ")
    return z
end

local function nearestOf(p)
    if PZA.sense == nil or PZA.sense.nearestZombie == nil then return nil end
    return PZA.sense.nearestZombie(p)
end

-- the last frame's overall health (Sense's S.last), else, before the first frame or without Sense, the player's own
local function lastHealthOf(p)
    local f = PZA.sense ~= nil and PZA.sense.last or nil
    if f ~= nil and f.body ~= nil then return f.body.health end
    return healthOf(p)
end

-- the player's state for an act line: me {x, y, z, health} (each absent when unreadable) and the nearest zombie
-- {id, dist} through Sense when it is loaded and provides one, else nil (the line omits it, which the reader takes as
-- null). The position is read now; the health and the nearest are the last frame's (X4 fix pass 2.5, review I8: a
-- command's accept tick reads no body, inventory or cell for its line; as old as the frame, at most one frame window).
-- Each read runs under pcall (S-15): a raise leaves its field absent and is counted in K.errors, so the snapshot
-- never raises (Main's scan and rate take it too).
function K.snapshot(p)
    local x, y = safely(posOf, p)
    local me = { x = x, y = y, z = safely(zOf, p), health = safely(lastHealthOf, p) }
    return { me = me, nearest = safely(nearestOf, p) }
end

-- one act line; snapshot only on rejected, failed and done
local function emitAct(p, aid, typ, state, reason, result)
    local body = { aid = aid, type = typ, state = state, reason = reason or "", result = result or {} }
    if state == "rejected" or state == "failed" or state == "done" then body.snapshot = K.snapshot(p) end
    PZA.emit("act", body)
end

-- the running skill's end: the runner idle, the latches off, its act line; a failure also clears the vanilla queue, and
-- a failure with no reason is interrupted (a failed line never carries an empty reason). The runner goes idle first and
-- the latches go off before the line (X4 fix pass 2.7, fix-wave review Minor 4: a raise in PZA.emit can no longer
-- leave the Motor re-asserting a run with no skill); every read and setter is guarded (S-15: K.snapshot's reads here,
-- each setter in MO.off), so a raise at a skill's end never leaves K.cur set or a latch untried; MO.off's caught
-- raises are counted in K.errors. A skill's stop hook runs at every end but done, after MO.off and before the line,
-- under the same guard (ruling P23-AB: the sleep's wake).
local function finish(p, cur, state, reason, result)
    K.cur = nil
    if state == "failed" then
        clearQueue(p)
        if reason == nil or reason == "" then reason = "interrupted" end
    end
    local n, err = MO.off(p)
    if n > 0 then
        K.errors = K.errors + n
        K.lastError = err
    end
    local stop = cur.def.stop
    if state ~= "done" and stop ~= nil then
        local ran, why = pcall(stop, p, cur.st, reason)
        if not ran then caught(why) end
    end
    emitAct(p, cur.aid, cur.type, state, reason, result)
end

-- a command from the Link's poll; it emits, and returns nothing the caller needs. A command with an empty aid is
-- rejected bad args, an unknown type unknown type, a dead player dead (but for stop; a dead check that raises is
-- rejected interrupted, S-15), a failed check its reason;
-- otherwise a running skill ends failed superseded (its line first) and the new one starts with accepted.
function K.start(cmd, p)
    local aid, typ = cmd.aid, cmd.type
    if type(aid) ~= "string" or aid == "" then
        emitAct(p, type(aid) == "string" and aid or "", typ, "rejected", "bad args")
        return
    end
    local def = K.types[typ]
    if def == nil then
        emitAct(p, aid, typ, "rejected", "unknown type")
        return
    end
    if typ ~= "stop" then
        local readable, dead = pcall(isDead, p)
        if not readable then
            caught(dead)
            emitAct(p, aid, typ, "rejected", "interrupted")
            return
        end
        if dead then
            emitAct(p, aid, typ, "rejected", "dead")
            return
        end
    end
    local args = type(cmd.args) == "table" and cmd.args or {}
    local ran, ok, reason, st = pcall(def.check, args, p)
    if not ran then
        caught(ok)
        emitAct(p, aid, typ, "rejected", "bad args")
        return
    end
    if not ok then
        emitAct(p, aid, typ, "rejected", reason or "bad args")
        return
    end
    if K.cur ~= nil then finish(p, K.cur, "failed", "superseded") end
    local now = PZA.now()
    K.cur = { aid = aid, type = typ, def = def, st = st or {}, state = "accepted", lastProgress = now }
    emitAct(p, aid, typ, "accepted")
end

-- one tick of the running skill; a progress line at most every PROGRESS_MS while it runs
function K.tick(p)
    local cur = K.cur
    if cur == nil then return end
    local ran, state, out = pcall(cur.def.tick, p, cur.st)
    if not ran then
        caught(state)
        finish(p, cur, "failed", "interrupted")
        return
    end
    if state == "done" then
        finish(p, cur, "done", "", out or {})
        return
    end
    if state == "failed" then
        finish(p, cur, "failed", out)
        return
    end
    local now = PZA.now()
    if now - cur.lastProgress >= K.PROGRESS_MS then
        cur.lastProgress = now
        cur.state = "progress"
        emitAct(p, cur.aid, cur.type, "progress")
    end
end

-- the frame's act group: the running skill's aid and its last emitted state, nil when idle
function K.status()
    local cur = K.cur
    if cur == nil then return nil end
    return { aid = cur.aid, state = cur.state }
end

-- world → input space: the inverse of IsoPlayer.updateMovementFromInput @136-157 L3025-L3026 (42.21: playerMoveDir.x = iy + ix, playerMoveDir.y = iy - ix), the length kept as an input length; ix = L(ux - uy)/sqrt 2, iy = L(ux + uy)/sqrt 2 (probe X1, GUIDE.md L85; #4199)
function K.inputVector(vx, vy)
    local s = 1 / math.sqrt(2)
    return (vx - vy) * s, (vx + vy) * s
end

-- ---- walkTo {x, y, gait} --------------------------------------------------------------------------------------------
-- The walk is the game's own timed action, ISWalkToTimedAction queued on the target square (getGridSquare(x, y,
-- p:getZ())), the gait through MO.want; done within DONE_R tiles with result {d = tiles to the target}, the queue
-- cleared at done (the walk would carry on past the target and queue ahead of the next skill) and, by the runner, at
-- every failure (Stage A pass 2's first leg failed stuck with its walk left queued, and the next leg's walk waited
-- 3661 ms behind it). Stuck is the player not having moved (|dx| + |dy| under STILL_EPS) for STUCK_TICKS consecutive
-- ticks: a walk round a house grows the straight-line distance while it walks correctly (Stage A pass 2), so progress
-- toward the target is never read. At STUCK_TICKS the walk is cleared and re-queued, REPLAN_MAX times, then the skill
-- fails stuck. A running walk fails dead at once (an absent reading is not dead).
K.STUCK_TICKS = 90
K.REPLAN_MAX = 3
K.STILL_EPS = 0.01        -- tiles, |dx| + |dy| between two ticks: under this the player has not moved
K.DONE_R = 1.0

K.types.walkTo = {
    check = function(args, p)
        local x, y, gait = args.x, args.y, gaitOf(args)
        if type(x) ~= "number" or type(y) ~= "number" or gait == nil then return false, "bad args" end
        return true, "", { x = x, y = y, gait = gait, replans = 0, still = 0, lastX = nil, lastY = nil, sq = nil }
    end,
    tick = function(p, st)
        if isDead(p) then return "failed", "dead" end
        if st.sq == nil then
            MO.want(st.gait)
            local cell = getCell ~= nil and getCell() or nil
            local _, z = PZA.call(p, "getZ")
            local _, sq = PZA.call(cell, "getGridSquare", st.x, st.y, z or 0)
            if sq == nil then return "failed", "no square" end
            st.sq = sq
            if not queueWalk(p, sq) then return "failed", "no path" end
        end
        local d = dist(p, st.x, st.y)
        if d ~= nil and d <= K.DONE_R then
            clearQueue(p)
            return "done", { d = d }
        end
        local x, y = posOf(p)
        if x == nil or y == nil then
            st.still = st.still + 1   -- an unreadable position is no movement
        elseif st.lastX ~= nil and math.abs(x - st.lastX) + math.abs(y - st.lastY) < K.STILL_EPS then
            st.still = st.still + 1
        else
            st.still = 0
        end
        st.lastX, st.lastY = x, y
        if st.still >= K.STUCK_TICKS then
            if st.replans >= K.REPLAN_MAX then return "failed", "stuck" end
            st.replans, st.still = st.replans + 1, 0
            clearQueue(p)
            queueWalk(p, st.sq)
        end
        return nil
    end,
}

-- ---- steer {vx, vy, seconds, gait} ----------------------------------------------------------------------------------
-- The game's auto-walk (setAutoWalk, setAutoWalkDirection) along a world vector, rotated into input space by
-- K.inputVector so the planner sends world vectors; the gait through MO.want, so a run is re-asserted by the Motor's
-- OnPlayerUpdate handler every frame. Done once seconds of wall time have passed, result {d = tiles from its start};
-- no stuck rule. The runner's MO.off at every end sends setAutoWalk(false). Vector2 and its new, and the player's
-- setAutoWalk and setAutoWalkDirection, are index-checked before the first call (not loaded: a player without the
-- auto-walk never steered, so it never reads as done).
K.types.steer = {
    check = function(args, p)
        local vx, vy, s, gait = args.vx, args.vy, args.seconds, gaitOf(args)
        if type(vx) ~= "number" or type(vy) ~= "number" or type(s) ~= "number" or s <= 0 or gait == nil then
            return false, "bad args"
        end
        return true, "", { vx = vx, vy = vy, seconds = s, gait = gait, startMs = nil, x0 = nil, y0 = nil }
    end,
    tick = function(p, st)
        if isDead(p) then return "failed", "dead" end
        if st.startMs == nil then
            if Vector2 == nil or Vector2.new == nil then return "failed", "not loaded" end
            if not PZA.field(p, "setAutoWalk") or not PZA.field(p, "setAutoWalkDirection") then
                return "failed", "not loaded"
            end
            clearQueue(p)
            st.x0, st.y0 = posOf(p)
            st.startMs = PZA.now()
            MO.want(st.gait)
            local ix, iy = K.inputVector(st.vx, st.vy)
            PZA.call(p, "setAutoWalk", true)
            PZA.call(p, "setAutoWalkDirection", Vector2.new(ix, iy))
            return nil
        end
        if PZA.now() - st.startMs >= st.seconds * 1000 then
            local d = st.x0 ~= nil and st.y0 ~= nil and dist(p, st.x0, st.y0) or nil
            return "done", { d = d }
        end
        return nil
    end,
}

-- ---- stop {} --------------------------------------------------------------------------------------------------------
-- clears the vanilla queue on its first tick and is done {}; the runner's end clears the latches and the auto-walk
K.types.stop = {
    check = function(args, p) return true, "", {} end,
    tick = function(p, st)
        clearQueue(p)
        return "done", {}
    end,
}
