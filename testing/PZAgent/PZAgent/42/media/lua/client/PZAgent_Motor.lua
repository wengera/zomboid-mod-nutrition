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
-- The stance (PZA/1.5.4, Plan 24 Task 9 fix 6, ruling P24-T; jar-reads-2 section 9): while PZA.motor.wantAim is set the
-- handler asserts setForceAim(true) every frame and no run latch. On 42.21 the force-aim lives one frame: the update
-- bucket runs the player's frameStep before its update (MovingObjectUpdateSchedulerUpdateBucket.update L56-L58), and the
-- input component's updateToggleToAim clears it while the toggle-aim handler is muted, which it is whenever the option
-- toggleToAim is false, the default (CharacterInputComponent.updateToggleToAim @7-@22 L149-L151, the handler's mute
-- callback lambda$new$0 L51, Core.<init> L446); OnPlayerUpdate fires before UpdateInputState reads it (updateInternal2
-- L2446, L2559; UpdateInputState L4397-L4398 sets the input's aiming, L2580 copies it into setIsAiming), so a set made
-- here reaches isAiming, while one made in OnTick (after the world update) is cleared before any update reads it. The
-- stance's owner (PZAgent_Stance.lua) sets wantAim when it holds the stance and clears it at the release; MO.off leaves
-- it, so a stance kept past an attack's end is still held. No run latch is asserted under it: a run would only be
-- dropped by the aiming (updateInternal2 L2596-L2599), and the stance walks.
-- The sneak (PZA/1.9, Plan 30 Task 1; the jar read sneak-jar-read.md, #4654): the opposite case. The sneaking flag is
-- one stored field on the character that only the crouch key's toggle (IsoPlayer.updateSneakKey, after OnPlayerUpdate),
-- the save load and the player packet's reader write, and nothing clears on an attack, a shove, a run, an aim or a hit,
-- so it is never re-asserted per frame: MO.sneak(on[, p]) records PZA.motor.wantSneak (and, given the player, writes
-- it at once, as the sneak command does), and the handler, after its latches and reads, calls setSneaking(wantSneak)
-- only when isSneaking() reads a boolean that differs: one write per transition, and one more only when something
-- outside the motor flipped the field (a crouch press, a load). An unreadable flag is never written on a guess. MO.off
-- leaves wantSneak and the flag: a stop or a supersede ends a walk, never the sneak, which is the planner's posture.
-- Under the flag the walk plays the crouched sneak walk and the run latch the sneak run (#4656). The frame's
-- me.sneaking is Sense's own isSneaking() read (the stored field reads the same in either tick: observed, never the
-- want echoed).
-- The idle snap (Plan 33 Task 1): after the latches, each frame calls PZA.skills.FACING.idle (PZAgent_StanceMelee.lua's
-- end) under PZA.skills.IDLE_SNAP, resolved at the call and under its own pcall (a raise counted in updErrors, the
-- reads still made), so between legs the body is snapped onto the nearest standing zombie, the aim posture as it is.
PZA.motor =PZA.motor or { wantRun = false, wantSprint = false, wantAim = false, wantSneak = false, upd = 0,
                           updErrors = 0, updRunning = nil, updForceRun = nil, updSprinting = nil, hooked = false }
local MO = PZA.motor
if MO.wantAim == nil then MO.wantAim = false end
if MO.wantSneak == nil then MO.wantSneak = false end

-- the gait a skill moves at: walk wants neither latch, run the force-run latch, sprint both
function MO.want(gait)
    MO.wantRun = gait == "run" or gait == "sprint"
    MO.wantSprint = gait == "sprint"
end

MO.offErrors = MO.offErrors or 0

-- one setter written false under pcall: nil when it ran (or is absent), else the raise's message
local function clear(p, name)
    local ok, err = pcall(PZA.call, p, name, false)
    if ok then return nil end
    return tostring(err)
end

-- every skill's end: the wants dropped so the handler asserts nothing more, then both latches and the auto-walk cleared
-- on the player, each setter under its own pcall (ruling S-15: a raising Java member inside a present one is a supported
-- fault), so a raise never leaves the next setter untried. Answers the raises caught, counted in MO.offErrors, and the
-- last one's message (the runner counts them in K.errors).
function MO.off(p)
    MO.wantRun, MO.wantSprint = false, false
    local n, last = 0, nil
    local e1 = clear(p, "setForceRun")
    local e2 = clear(p, "setForceSprint")
    local e3 = clear(p, "setAutoWalk")
    if e1 ~= nil then n, last = n + 1, e1 end
    if e2 ~= nil then n, last = n + 1, e2 end
    if e3 ~= nil then n, last = n + 1, e3 end
    MO.offErrors = MO.offErrors + n
    return n, last
end

-- the member's answer, or nil when it is absent
local function read(pl, name)
    local ok, v = PZA.call(pl, name)
    if ok then return v end
    return nil
end

-- the sneak want onto the player: setSneaking only when isSneaking() reads a boolean that differs (the header's sneak).
-- A raising setter is re-raised (the handler counts it in updErrors, the sneak command answers failed interrupted) and
-- counted in MO.sneakRaises; after SNEAK_RAISES raises in a row the want drops to the flag as read, so the Motor stops
-- trying and the next frame's me.sneaking shows the truth (review-t1 minor 3). A write that runs, or a new want,
-- resets the count.
MO.SNEAK_RAISES = 3
MO.sneakRaises = MO.sneakRaises or 0
local function applySneak(pl)
    local ok, on = PZA.call(pl, "isSneaking")
    if not ok or type(on) ~= "boolean" or on == MO.wantSneak then return end
    local ran, err = pcall(PZA.call, pl, "setSneaking", MO.wantSneak)
    if ran then
        MO.sneakRaises = 0
        return
    end
    MO.sneakRaises = MO.sneakRaises + 1
    if MO.sneakRaises >= MO.SNEAK_RAISES then
        MO.wantSneak = on
        MO.sneakRaises = 0
    end
    error(err, 0)
end

-- the planner's sneak posture (PZA/1.9): the want recorded, and written at once when the player is given
function MO.sneak(on, p)
    MO.wantSneak = on == true
    MO.sneakRaises = 0
    if p ~= nil then applySneak(p) end
end

local function update(pl)
    MO.upd = MO.upd + 1
    if MO.wantAim then
        PZA.call(pl, "setForceAim", true)
    else
        if MO.wantRun then PZA.call(pl, "setForceRun", true) end
        if MO.wantSprint then PZA.call(pl, "setForceSprint", true) end
    end
    local K = PZA.skills   -- Plan 33 Task 1: the idle snap (FACING.idle, PZAgent_StanceMelee.lua's end), its own pcall
    if K ~= nil and K.IDLE_SNAP and K.FACING ~= nil and K.FACING.idle ~= nil then
        if not pcall(K.FACING.idle, pl) then MO.updErrors = MO.updErrors + 1 end
    end
    MO.updRunning = read(pl, "IsRunning")
    MO.updForceRun = read(pl, "isForceRun")
    MO.updSprinting = read(pl, "isSprinting")
    MO.updForceSprint = read(pl, "isForceSprint")
    applySneak(pl)
end

function MO.onPlayerUpdate(pl)
    local ok = pcall(update, pl)
    if not ok then MO.updErrors = MO.updErrors + 1 end
end

if not MO.hooked and Events ~= nil and Events.OnPlayerUpdate ~= nil then
    Events.OnPlayerUpdate.Add(MO.onPlayerUpdate)
    MO.hooked = true
end
