-- PZAgent_Motor.lua — the run latch's per-frame assert (Plan 22 probe X1). Lua OnPlayerUpdate fires inside the local
-- player's update before UpdateInputState reads isForceRun, and the latch is wiped every frame a path walk leaves the
-- input vector at zero, so a forced run on a path is re-asserted here every frame while PZA.motor.forceRun is set
-- (the jar reading: jar-research-movement.md Q1, IsoPlayer.updateInternal @1141 L2446 then @1841 L2609).
-- The goals own the flags (PZAgent_Act.lua: the goto arms forcerun, forcesprint and toggle, autowalk's forcerun, and
-- A.motorOff on every exit); the handler only asserts them and reads back, after its own asserts, what the frame
-- ended with: updRunning (IsRunning), updForceRun (isForceRun), updSprinting (isSprinting), each nil when the member
-- is absent. upd counts the handler's calls, updErrors its caught raises. The handler acts on the player it is
-- given, never getPlayer(); its body runs under pcall so a raise never propagates into the player update, and every
-- Java member is reached through PZA.call (index-first: a missing member is skipped, never called).
PZA.motor = PZA.motor or { forceRun = false, forceSprint = false, toggleWas = nil, upd = 0, updErrors = 0,
                           updRunning = nil, updForceRun = nil, updSprinting = nil, hooked = false }
local MO = PZA.motor

-- the member's answer, or nil when it is absent
local function read(pl, name)
    local ok, v = PZA.call(pl, name)
    if ok then return v end
    return nil
end

local function update(pl)
    MO.upd = MO.upd + 1
    if MO.forceRun then PZA.call(pl, "setForceRun", true) end
    if MO.forceSprint then PZA.call(pl, "setForceSprint", true) end
    MO.updRunning = read(pl, "IsRunning")
    MO.updForceRun = read(pl, "isForceRun")
    MO.updSprinting = read(pl, "isSprinting")
end

function MO.onPlayerUpdate(pl)
    local ok = pcall(update, pl)
    if not ok then MO.updErrors = MO.updErrors + 1 end
end

if not MO.hooked and Events ~= nil and Events.OnPlayerUpdate ~= nil then
    Events.OnPlayerUpdate.Add(MO.onPlayerUpdate)
    MO.hooked = true
end
