-- PZAgent_Motor.lua — the run latch's per-frame assert (Plan 22 probe X1). Lua OnPlayerUpdate fires inside the local
-- player's update before UpdateInputState reads isForceRun, and the latch is wiped every frame a path walk leaves the
-- input vector at zero, so a forced run on a path is re-asserted here every frame while PZA.motor.wantRun is set
-- (the jar reading: jar-research-movement.md Q1, IsoPlayer.updateInternal @1141 L2446 then @1841 L2609).
-- The skills own the wants (PZAgent_Skills.lua: walkTo and steer call MO.want(gait) at their start, and the runner
-- calls MO.off at every end, supersede and stop); the handler only asserts them and reads back, after its own asserts,
-- what the frame ended with: updRunning (IsRunning), updForceRun (isForceRun), updSprinting (isSprinting) and
-- updForceSprint (isForceSprint), each nil when the member is absent; Sense's frame reads these, never the player's own
-- flags (observe, never echo). upd counts the handler's calls, updErrors its caught raises. The handler acts on the
-- player it is given, never getPlayer(); its body runs under pcall so a raise never propagates into the player update,
-- and every Java member is reached through PZA.call (index-first: a missing member is skipped, never called).
PZA.motor = PZA.motor or { wantRun = false, wantSprint = false, upd = 0, updErrors = 0,
                           updRunning = nil, updForceRun = nil, updSprinting = nil, hooked = false }
local MO = PZA.motor

-- the gait a skill moves at: walk wants neither latch, run the force-run latch, sprint both
function MO.want(gait)
    MO.wantRun = gait == "run" or gait == "sprint"
    MO.wantSprint = gait == "sprint"
end

-- every skill's end: both latches and the auto-walk cleared on the player, and the wants dropped so the handler
-- asserts nothing more
function MO.off(p)
    MO.wantRun, MO.wantSprint = false, false
    PZA.call(p, "setForceRun", false)
    PZA.call(p, "setForceSprint", false)
    PZA.call(p, "setAutoWalk", false)
end

-- the member's answer, or nil when it is absent
local function read(pl, name)
    local ok, v = PZA.call(pl, name)
    if ok then return v end
    return nil
end

local function update(pl)
    MO.upd = MO.upd + 1
    if MO.wantRun then PZA.call(pl, "setForceRun", true) end
    if MO.wantSprint then PZA.call(pl, "setForceSprint", true) end
    MO.updRunning = read(pl, "IsRunning")
    MO.updForceRun = read(pl, "isForceRun")
    MO.updSprinting = read(pl, "isSprinting")
    MO.updForceSprint = read(pl, "isForceSprint")
end

function MO.onPlayerUpdate(pl)
    local ok = pcall(update, pl)
    if not ok then MO.updErrors = MO.updErrors + 1 end
end

if not MO.hooked and Events ~= nil and Events.OnPlayerUpdate ~= nil then
    Events.OnPlayerUpdate.Add(MO.onPlayerUpdate)
    MO.hooked = true
end
