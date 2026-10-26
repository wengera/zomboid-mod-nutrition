-- PZAgent_Act.lua — the goals (spec § 2.3). One goal at a time; each is a per-tick state machine that
-- sets state done|failed with a detail from its closed set (no square, no path, stuck, bad args, superseded, ...). The walk is the game's own timed action,
-- queued the way the harness's player.walk does [#2082: setRunning(true) does not make a walk run].
PZA.act = PZA.act or {}
local A = PZA.act
A.goals = A.goals or {}
A.goal = nil
A.REPLAN_MAX = 3
A.STUCK_TICKS = 90

local function split(args)
    local out = {}
    for w in string.gmatch(args or "", "%S+") do out[#out + 1] = w end
    return out
end

function A.status()
    local g = A.goal
    if g == nil then return { seq = 0, name = "idle", state = "idle", detail = "" } end
    if g.state ~= "running" then g.reported = true end -- reading a finished goal is its report; the next tick clears it
    return { seq = g.seq, name = g.name, state = g.state, detail = g.detail or "" }
end

-- A new goal replaces a running one: the old walk is cleared and the old goal's status comes back
-- as failed "superseded" (third return) so the caller reports it.
function A.start(cmd, p)
    local def = A.goals[cmd.goal]
    if def == nil then return false, "unknown goal" end
    local argv = split(cmd.args)
    local ok, reason, st = def.start(argv)
    if not ok then return false, reason end
    local old = nil
    if A.goal ~= nil and A.goal.state == "running" then
        if p ~= nil then pcall(ISTimedActionQueue.clear, p) end
        A.goal.state, A.goal.detail = "failed", "superseded"
        old = A.status()
    end
    st.seq, st.name, st.state, st.detail, st.argv, st.ticks = cmd.seq, cmd.goal, "running", "", argv, 0
    A.goal = st
    return true, "", old
end

function A.tick(p)
    local g = A.goal
    if g == nil then return end
    if g.state ~= "running" then
        if g.reported then A.goal = nil end
        return
    end
    g.ticks = g.ticks + 1
    A.goals[g.name].tick(p, g)
end

local function queueWalk(p, sq)
    local ran, err = pcall(function() ISTimedActionQueue.add(ISWalkToTimedAction:new(p, sq)) end)
    return ran, err
end

local function dist(p, x, y)
    local ex, ey = p:getX() - x, p:getY() - y
    return math.sqrt(ex * ex + ey * ey)
end

A.goals["goto"] = {
    start = function(argv)
        local dx, dy = tonumber(argv[1]), tonumber(argv[2])
        if dx == nil or dy == nil then return false, "bad args" end
        return true, "", { dx = dx, dy = dy, run = argv[3] == "run", replans = 0, lastX = nil, lastY = nil, still = 0 }
    end,
    tick = function(p, g)
        if g.tx == nil then
            g.tx, g.ty = p:getX() + g.dx, p:getY() + g.dy
            local cell = getCell and getCell() or nil
            local _, sq = PZA.call(cell, "getGridSquare", g.tx, g.ty, p:getZ())
            if sq == nil then g.state, g.detail = "failed", "no square"; return end
            g.sq = sq
            if g.run then PZA.call(p, "setRunning", true) end
            local ran, err = queueWalk(p, sq)
            if not ran then g.state, g.detail = "failed", "no path"; return end
        end
        local d = dist(p, g.tx, g.ty)
        if d <= 1.0 then g.state, g.detail = "done", "d=" .. tostring(d); return end
        local x, y = p:getX(), p:getY()
        if g.lastX == x and g.lastY == y then g.still = g.still + 1 else g.still = 0 end
        g.lastX, g.lastY = x, y
        if g.still >= A.STUCK_TICKS then
            if g.replans >= A.REPLAN_MAX then g.state, g.detail = "failed", "stuck"; return end
            g.replans, g.still = g.replans + 1, 0
            pcall(ISTimedActionQueue.clear, p)
            queueWalk(p, g.sq)
        end
    end,
}

A.goals["stop"] = {
    start = function(argv) return true, "", {} end,
    tick = function(p, g)
        pcall(ISTimedActionQueue.clear, p)
        PZA.call(p, "setRunning", false)
        g.state, g.detail = "done", ""
    end,
}
