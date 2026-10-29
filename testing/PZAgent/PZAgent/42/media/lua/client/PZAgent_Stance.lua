-- PZAgent_Stance.lua — the stance and the climb (PZA/1.5, ruling P24-G; Plan 24 spec section 6): the skills aim and
-- climb, registered into PZA.skills.types like PZAgent_SkillsWorld.lua's, whose runner (K.start, K.tick) owns every act
-- line, the S-12 and S-15 guards and MO.off at every end. Loads after PZAgent_SkillsWorld.lua (client files load by
-- name, "Sk" before "St") and reaches its helpers through K (K.squareAt, K.queueAction, K.zombieById, K.zombieDead,
-- K.zombieDist, K.floorOf; K.queueWalk, K.clearQueue, K.inputVector from PZAgent_Skills.lua). Every Java member
-- through PZA.call (index-first), every vanilla class and member index-checked before a call under pcall.
-- The jar reads are docs/superpowers/specs/2026-10-29-plan-24-jar-reads-2.md (Task 6b, rows T6b.1-T6b.4).
local K = PZA.skills
local MO = PZA.motor
local W = PZA.world
local isDead, dist, clearQueue, posOf = K.isDead, K.dist, K.clearQueue, W.posOf

-- ---- the stance --------------------------------------------------------------------------------------------------
-- The stance is the force-aim (jar-reads-2 section 1, T6b.1): p:setForceAim(true), a default method of the interface
-- CharacterInputComponentEntity IsoPlayer implements, makes the update that reads it set the input's aiming (a run or a
-- sprint clears it; and the next frameStep, below); while aiming the character walks only, strafes (isStrafing is isAiming) and keeps the facing
-- the mod gave it, so the auto-walk vector moves it while it faces its target: the backpedal. A hit reaction clears the
-- aiming for its length, never the force-aim. Released by vanilla's own nullifyAiming() (IsoPlayer.nullifyAiming @0-@22
-- L1153-L1157: the force-aim toggled off and aiming cleared; ISFitnessAction.lua:15). The stance costs no endurance
-- beyond the walk (T6b.2). Every vanilla timed action but the climb stops on aiming (ISBaseTimedAction's stopOnAim
-- true), and the path follower will not climb while aiming (#4289), so the stance lives only under an aim and the
-- attack it hands over to:
--   an aim holds it from its first tick and releases it at its end (done, failed, superseded), except when an attack
--   supersedes it (K.start below names the starting type in K.starting): the attack then swings from the held stance
--   (PZAgent_SkillsWorld.lua's swing drops the run latches, faces and presses DoAttack(0), unchanged), and an attack
--   whose target is out of reach releases it before its approach, which runs;
--   any other skill started (walkTo, steer, climb, a care skill, stop) releases it (K.start's wrapper);
--   with no skill running it is released AIM_HOLD_MS after the last one ended (K.tick's wrapper), so a kept stance
--   never outlives the planner's next aim.
-- K.stance.held is the mod's own record of a stance it set; a release is one nullifyAiming under pcall (S-15: a raise
-- counted in K.errors, never propagated out of the runner).
-- Held every frame (PZA/1.5.4, Plan 24 Task 9 fix 6, ruling P24-T; jar-reads-2 section 9): the force-aim set once lives
-- one frame on 42.21 (the input component's frameStep clears it while the option toggleToAim is false, before the next
-- update reads it), so E6's aims never read isAiming true. While the stance is held, PZA.motor.wantAim is set and the
-- Motor's OnPlayerUpdate handler re-asserts setForceAim(true) every frame, inside the update and before
-- UpdateInputState reads it (PZAgent_Motor.lua); the release clears it.
K.AIM_HOLD_MS = 2000      -- a stance kept past an attack with no skill running is released this long after
K.AIM_R = 12              -- tiles: a target farther than the sense radius is no target
K.stance = K.stance or { held = false, idleAt = nil }
local ST = K.stance

function K.releaseStance(p)
    ST.held, ST.idleAt = false, nil
    MO.wantAim = false
    local ok, err = pcall(PZA.call, p, "nullifyAiming")
    if not ok then
        K.errors = K.errors + 1
        K.lastError = tostring(err)
    end
end
local release = K.releaseStance

-- whether the stance still holds: isForceAim (the flag the frame step clears) when the player exposes it, else isAiming
local function stanceHeld(p)
    local ok, v = PZA.call(p, "isForceAim")
    if ok then return v == true end
    local _, a = PZA.call(p, "isAiming")
    return a == true
end

-- ---- aim {vx, vy, seconds, targetId, bearing} ------------------------------------------------------------------------
-- Holds the stance for seconds of wall time. check: vx, vy and seconds numbers (seconds above 0), targetId and bearing
-- numbers when given (each -1 when absent); a targetId of 0 or more names a live zombie within AIM_R (K.zombieById),
-- else no target; a bearing of 0 or more (degrees, 0 east, 90 south: world x and y) is faced when there is no target,
-- -1 keeps the facing. The first tick: setForceAim and nullifyAiming index-checked (not loaded), and with a non-zero
-- vector Vector2 and the auto-walk members too (not loaded); the vanilla queue cleared, the run latches wanted off
-- (MO.want walk) and written false (the latches only keep the gait a walk), setForceAim(true), the facing, and with a non-zero
-- vector the steer skill's own auto-walk along it in input space (K.inputVector), at the stance's walk. Every tick:
-- the facing again (faceThisObject(z), or setForwardDirection(cos b, sin b)); a target that reads dead ends it done at
-- once. Done at seconds with {d (tiles from its start), held (stanceHeld at the end), targetDead, heldFrames, ticks};
-- the stance released. heldFrames counts the ticks after the first whose isAiming() read true, ticks those ticks (a
-- target read dead ends the leg before its tick is counted): a live leg proves its own stance (PZA/1.5.4, P24-T).
-- The cost a tick: the dead check (getBodyDamage, getOverallBodyHealth), the target's isDead, one facing call and the
-- isAiming read: five Java calls with a target, four with a bearing, three keeping the facing; no allocation (the
-- Vector2 is made once). The per-frame setForceAim is the Motor's, one call a frame while the stance is held.
local function faceOf(p, st)
    if st.z ~= nil then
        PZA.call(p, "faceThisObject", st.z)
    elseif st.fx ~= nil then
        PZA.call(p, "setForwardDirection", st.fx, st.fy)
    end
end

local function aimResult(p, st, targetDead)
    local d = st.x0 ~= nil and st.y0 ~= nil and dist(p, st.x0, st.y0) or nil
    return { d = d, held = stanceHeld(p), targetDead = targetDead, heldFrames = st.heldFrames, ticks = st.ticks }
end

-- one tick of the leg counted, and whether isAiming() read true on it
local function countHeld(p, st)
    st.ticks = st.ticks + 1
    local _, a = PZA.call(p, "isAiming")
    if a == true then st.heldFrames = st.heldFrames + 1 end
end

-- the first tick's members: nil when present, else not loaded
local function aimLoaded(p, st)
    if not PZA.field(p, "setForceAim") or not PZA.field(p, "nullifyAiming") then return false end
    if st.vx == 0 and st.vy == 0 then return true end
    if Vector2 == nil or Vector2.new == nil then return false end
    return PZA.field(p, "setAutoWalk") and PZA.field(p, "setAutoWalkDirection")
end

local function aimStart(p, st)
    clearQueue(p)
    st.x0, st.y0 = posOf(p)
    st.startMs = PZA.now()
    MO.want("walk")
    PZA.call(p, "setForceRun", false)
    PZA.call(p, "setForceSprint", false)
    PZA.call(p, "setForceAim", true)
    ST.held, ST.idleAt = true, nil
    MO.wantAim = true
    faceOf(p, st)
    if st.vx ~= 0 or st.vy ~= 0 then
        local ix, iy = K.inputVector(st.vx, st.vy)
        PZA.call(p, "setAutoWalk", true)
        PZA.call(p, "setAutoWalkDirection", Vector2.new(ix, iy))
    end
end

K.types.aim = {
    check = function(args, p)
        local vx, vy, s = args.vx, args.vy, args.seconds
        local id, b = args.targetId, args.bearing
        if id == nil then id = -1 end
        if b == nil then b = -1 end
        if type(vx) ~= "number" or type(vy) ~= "number" or type(s) ~= "number" or s <= 0 or type(id) ~= "number"
            or type(b) ~= "number" then
            return false, "bad args"
        end
        local st = { vx = vx, vy = vy, seconds = s, z = nil, fx = nil, fy = nil, startMs = nil, x0 = nil, y0 = nil,
                     heldFrames = 0, ticks = 0 }
        if id >= 0 then
            local z = K.zombieById(p, id)
            if z == nil or K.zombieDead(z) then return false, "no target" end
            local d = K.zombieDist(p, z)
            if d == nil or d > K.AIM_R then return false, "no target" end
            st.z = z
        elseif b >= 0 then
            local r = math.rad(b)
            st.fx, st.fy = math.cos(r), math.sin(r)
        end
        return true, "", st
    end,
    tick = function(p, st)
        if isDead(p) then return "failed", "dead" end
        if st.z ~= nil and K.zombieDead(st.z) then
            local out = aimResult(p, st, true)
            if st.startMs ~= nil then release(p) end
            return "done", out
        end
        if st.startMs == nil then
            if not aimLoaded(p, st) then return "failed", "not loaded" end
            aimStart(p, st)
            return nil
        end
        faceOf(p, st)
        countHeld(p, st)
        if PZA.now() - st.startMs >= st.seconds * 1000 then
            local out = aimResult(p, st, false)
            release(p)
            return "done", out
        end
        return nil
    end,
    -- every end but done: the stance released, unless an attack supersedes the aim (it swings from the stance)
    stop = function(p, st, reason)
        if st.startMs == nil then return end
        if reason == "superseded" and K.starting == "attack" then
            ST.idleAt = nil
            return
        end
        release(p)
    end,
}

-- the runner's start, wrapped: K.starting names the type being started while the base start runs (the aim's stop hook
-- reads it), and a held stance is released when the start began a skill (K.cur changed) that is not an aim or an
-- attack. A rejected command changes nothing, so it leaves the running skill, and a stance kept with none running (the
-- AIM_HOLD_MS after an attack), as they were (PZA/1.5.1, Task 9 review minor 4: an attack rejected busy during a hit
-- reaction dropped the kept stance). Main and the tests call K.start through the table.
local startBase = K.start
function K.start(cmd, p)
    K.starting = type(cmd) == "table" and cmd.type or nil
    local before = K.cur
    startBase(cmd, p)
    K.starting = nil
    local cur = K.cur
    if ST.held and cur ~= before and cur ~= nil and cur.type ~= "aim" and cur.type ~= "attack" then release(p) end
end

-- the runner's tick, wrapped: a stance kept with no skill running is released AIM_HOLD_MS after the runner went idle
local tickBase = K.tick
function K.tick(p)
    tickBase(p)
    if not ST.held or K.cur ~= nil then return end
    local now = PZA.now()
    if ST.idleAt == nil then
        ST.idleAt = now
    elseif now - ST.idleAt >= K.AIM_HOLD_MS then
        release(p)
    end
end

-- the attack's tick, wrapped: under a held stance, a target beyond the reach before the swing releases the stance (the
-- approach walk is a timed action, stopped by aiming, and runs)
local attackTick = K.types.attack.tick
K.types.attack.tick = function(p, st)
    if ST.held and st.swungAt == nil and st.sub == nil then
        local _, w = PZA.call(p, "getPrimaryHandItem")
        local d = K.zombieDist(p, st.z)
        if w ~= nil and d ~= nil and d > K.reachOf(p, w) then release(p) end
    end
    return attackTick(p, st)
end

-- ---- climb {x, y} ----------------------------------------------------------------------------------------------------
-- The hoppable fence on square (x, y)'s north or west edge (the square whose map record reads hopN or hopW), climbed at
-- a walk as vanilla's context menu climbs it (ISWorldObjectContextMenu.onClimbOverFence: a walk next to the fence, then
-- ISTimedActionQueue.add(ISClimbOverFence:new(playerObj, fence, direction)), lua:client/ISUI/ISWorldObjectContextMenu.lua
-- L2347-L2352). The jar (jar-reads-2 section 2, T6b.3, T6b.4): a short fence climbed at a walk costs no endurance and
-- rolls no fall; only a climb begun at a run or a sprint (the vault) rolls the trip; a tall fence (isTallHoppable:
-- perform calls climbOverWall) costs runningEnduranceReduce x 1200 and fails 1 time in s (getClimbingFailChanceInt).
-- check: x, y numbers (floored to the square); the square on the player's floor (no square), and on it the first object
-- whose isHoppable() or isTallHoppable() reads true, else not hoppable. The edge is north when the square has
-- IsoFlagType HoppableN or TallHoppableN (vanilla's ISClimbOverFence:getFacingDirection reads the square's HoppableN)
-- and no west flag (HoppableW, TallHoppableW), west when it has only a west flag or none; a corner square carrying both
-- takes the edge whose near square (on the player's side) the player stands nearer (PZA/1.5.1, Task 9 review minor 4;
-- north when the position cannot be read). The first tick: the vanilla queue cleared, the run latches wanted off and written false (a climb begun at a
-- run would vault), the player's side of the edge recorded (north of a north edge: floor(y) < y; west of a west edge:
-- floor(x) < x), a vanilla walk to the near square when the player stands elsewhere (no square, no path), then
-- ISClimbOverFence:new(p, fence, dir) with dir the IsoDirections constant facing across (S or N, E or W, nil when
-- IsoDirections is absent) queued behind it (not loaded, not valid). Later ticks: getVariableString("ClimbFenceOutcome")
-- reading fall or falling, or the floor changing, marks a fall; the player on the far side of the edge and within one
-- square (Chebyshev) of the fence's far square ends it (a walk crossing the edge's line elsewhere is not a climb:
-- PZA/1.5.1, Task 9 review minor 4), failed fell after a fall, else done {tall, wounds (the rise in getNumPartsScratched + getNumPartsBleeding since the queue)}; the climb
-- action gone from the vanilla queue CLIMB_SETTLE_MS with the player still on the near side is failed (a tall fence's
-- failed climb, or the walk before it failed); CLIMB_MS after the queue, interrupted.
K.CLIMB_MS = 20000        -- a climb not over within this wall time of its queue is interrupted
K.CLIMB_SETTLE_MS = 4000  -- the climb's state plays on after its action leaves the queue; past this, a near side fails

-- whether square sq carries IsoFlagType[name]: false when the constant or the member is absent
local function hasFlag(sq, name)
    local f = IsoFlagType ~= nil and IsoFlagType[name] or nil
    if f == nil then return false end
    local _, v = PZA.call(sq, "has", f)
    return v == true
end

-- the square's fence: its first object reading isHoppable() or isTallHoppable() true, and whether it is tall
local function fenceOn(sq)
    local objs = W.objectsOn(sq)
    for _, o in ipairs(objs) do
        local _, tall = PZA.call(o, "isTallHoppable")
        local _, hop = PZA.call(o, "isHoppable")
        if tall == true or hop == true then return o, tall == true end
    end
    return nil, false
end

-- the player's side of the fence: true on the north (or west) side of the edge
local function sideOf(st, px, py)
    if st.north then return math.floor(py) < st.y end
    return math.floor(px) < st.x
end

-- the near square (on the player's side of the edge) and the direction that faces across from it
local function nearOf(st, side)
    if st.north then
        if side then return st.x, st.y - 1, "S" end
        return st.x, st.y, "N"
    end
    if side then return st.x - 1, st.y, "E" end
    return st.x, st.y, "W"
end

-- the climb is over: the player on the other side of the edge from side0, within one square of the far square (the
-- near square of the other side)
local function across(st, px, py)
    local side = sideOf(st, px, py)
    if side == st.side0 then return false end
    local fx, fy = nearOf(st, side)
    return math.max(math.abs(math.floor(px) - fx), math.abs(math.floor(py) - fy)) <= 1
end

-- the squared distance from (px, py) to the centre of the near square of square (x, y)'s north or west edge
local function nearGap(north, x, y, px, py)
    local e = { north = north, x = x, y = y }
    local nx, ny = nearOf(e, sideOf(e, px, py))
    local dx, dy = px - (nx + 0.5), py - (ny + 0.5)
    return dx * dx + dy * dy
end

-- the edge of square (x, y) to climb: north for a north flag alone, west for a west flag alone or none; on a corner
-- with both, the edge whose near square the player at (px, py) stands nearer (north when unread or level)
local function northEdge(sq, x, y, px, py)
    local n = hasFlag(sq, "HoppableN") or hasFlag(sq, "TallHoppableN")
    local w = hasFlag(sq, "HoppableW") or hasFlag(sq, "TallHoppableW")
    if not (n and w) then return n end
    if px == nil or py == nil then return true end
    return nearGap(true, x, y, px, py) <= nearGap(false, x, y, px, py)
end

local function woundCount(p)
    local _, bd = PZA.call(p, "getBodyDamage")
    local _, s = PZA.call(bd, "getNumPartsScratched")
    local _, b = PZA.call(bd, "getNumPartsBleeding")
    return (type(s) == "number" and s or 0) + (type(b) == "number" and b or 0)
end

-- whether action still sits in the player's vanilla queue: vanilla's own ISTimedActionQueue.hasAction(action)
-- (lua:client/TimedActions/ISTimedActionQueue.lua:245), index-checked and under pcall; absent or raising, not queued
local function inQueue(action)
    local Q = ISTimedActionQueue
    if Q == nil or Q.hasAction == nil then return false end
    local ok, has = pcall(Q.hasAction, action)
    return ok and has == true
end

-- the first tick: the walk to the near square (when needed) and the climb queued behind it; nil, or the failure reason
local function climbQueue(p, st)
    local px, py, pz = posOf(p, true)
    if px == nil or py == nil then return "not loaded" end
    clearQueue(p)
    MO.want("walk")
    PZA.call(p, "setForceRun", false)
    PZA.call(p, "setForceSprint", false)
    st.side0, st.z0 = sideOf(st, px, py), pz
    local nx, ny, dirName = nearOf(st, st.side0)
    if math.floor(px) ~= nx or math.floor(py) ~= ny then
        local nsq = K.squareAt(nx, ny, st.z)
        if nsq == nil then return "no square" end
        if not K.queueWalk(p, nsq) then return "no path" end
    end
    local dir = IsoDirections ~= nil and IsoDirections[dirName] or nil
    local ok, why, action = K.queueAction(ISClimbOverFence, "not valid", nil, p, st.fence, dir)
    if not ok then return why end
    st.action, st.wounds0, st.queuedAt = action, woundCount(p), PZA.now()
    return nil
end

K.types.climb = {
    check = function(args, p)
        local x, y = args.x, args.y
        if type(x) ~= "number" or type(y) ~= "number" then return false, "bad args" end
        x, y = math.floor(x), math.floor(y)
        local z = K.floorOf(p)
        local sq = K.squareAt(x, y, z)
        if sq == nil then return false, "no square" end
        local fence, tall = fenceOn(sq)
        if fence == nil then return false, "not hoppable" end
        local px, py = posOf(p)
        local north = northEdge(sq, x, y, px, py)
        return true, "", { x = x, y = y, z = z, fence = fence, tall = tall, north = north, queuedAt = nil,
                           fell = false, leftAt = nil }
    end,
    tick = function(p, st)
        if isDead(p) then return "failed", "dead" end
        if st.queuedAt == nil then
            local why = climbQueue(p, st)
            if why ~= nil then return "failed", why end
            return nil
        end
        local _, oc = PZA.call(p, "getVariableString", "ClimbFenceOutcome")
        if oc == "fall" or oc == "falling" then st.fell = true end
        local px, py, pz = posOf(p, true)
        if pz ~= nil and st.z0 ~= nil and pz ~= st.z0 then st.fell = true end
        if px ~= nil and py ~= nil and across(st, px, py) then
            if st.fell then return "failed", "fell" end
            return "done", { tall = st.tall, wounds = math.max(0, woundCount(p) - st.wounds0) }
        end
        local now = PZA.now()
        if st.leftAt == nil and not inQueue(st.action) then st.leftAt = now end
        if st.leftAt ~= nil and now - st.leftAt >= K.CLIMB_SETTLE_MS then
            if st.fell then return "failed", "fell" end
            return "failed", "failed"
        end
        if now - st.queuedAt >= K.CLIMB_MS then return "failed", "interrupted" end
        return nil
    end,
}

-- ---- window {x, y, smash} (PZA/1.6, Task 9 fix 9; jar-reads-2 section 10) ---------------------------------------------
-- The window on square (x, y), climbed through as vanilla's context menu does it (ISWorldObjectContextMenu.
-- onClimbThroughWindow: a walk next to the window, then ISTimedActionQueue.add(ISClimbThroughWindow:new(playerObj,
-- window, 0)), lua:client/ISUI/ISWorldObjectContextMenu.lua:2355-2365), opened first (onOpenCloseWindow, :2279-2287,
-- ISOpenCloseWindow:new(playerObj, window)) or smashed first (onSmashWindow, :2367-2372, ISSmashWindow:new(playerObj,
-- window)) when it is shut. The jar: IsoWindow.canClimbThrough @0-@94 L1379-L1399 is false while it is invincible or
-- barricaded or the far square cannot be stood on (canClimbThroughHelper: solid, water, no floor), else true when it is
-- open or destroyed (health 0 or the destroyed flag; isSmashed and isDestroyed both read that flag, @0-@4 L1211, L404);
-- a locked window opens from inside, and from an exterior square each try may break its lock (1 in 10, 1 in 20 for a
-- Burglar: perma-locked, never to open) or force it by Strength (OpenWindowState.onAttemptFinished @46-@292
-- L185-L222); climbing through a destroyed window whose glass was not removed cuts a hand or forearm 1 time in 2
-- (ClimbThroughWindowState.getClimbThroughWindowPositioningParams @36-@65 L624-L625, then setScratchedWindow in execute
-- @775-@815 L217-L221, which does nothing on a client: BodyDamage.setScratchedWindow @0-@7 L1944-L1945); a smash with
-- no weapon in either hand scratches the smasher (ISSmashWindow:complete, lua:shared/TimedActions/ISSmashWindow.lua:46-
-- 58, server side).
-- check: x, y numbers (floored), smash absent or a boolean (else bad args); the square on the player's floor (no
-- square); on it an IsoWindow, else a thumpable window (IsoThumpable reading isWindow) or an IsoWindowFrame (not a
-- window); a barricaded one, a perma-locked shut one without smash, or a non-IsoWindow that canClimbThrough(p) refuses,
-- is rejected locked, and an IsoWindow open or smashed that it refuses (the far side) not valid. The edge is the window's: north when getNorth() reads true (the window sits on its square's north
-- edge, else its west edge), the climb's sideOf, nearOf and across. The first tick: the vanilla queue cleared, the run
-- latches off, the player's side recorded, a vanilla walk to the near square when it stands elsewhere (no square, no
-- path), then the first step queued behind it: the climb when canClimbThrough(p) reads true, else (an IsoWindow) the
-- open unless it reads perma-locked, else the smash when smash is true, else failed locked. Each step is timed from
-- the tick its action leaves the vanilla queue (a walk before it runs first), and an open or a smash whose action left
-- the queue with the player more than one square from the near square fails not adjacent. The open: canClimbThrough(p)
-- reading true queues the climb (opened); an open that reads true while the far side refuses fails not valid;
-- perma-locked, or WINDOW_OPEN_MS without opening (a locked window's struggle), queues the smash when smash is true (the
-- queue cleared first), else fails locked. The smash: isSmashed() reading true queues the climb (smashed),
-- WINDOW_SMASH_MS without it fails interrupted. The climb: getVariableString("ClimbWindowOutcome") reading fall,
-- fallback or fallfront, or the floor changing, marks a fall; the player across the edge within one square of the far
-- square ends it, failed fell after a fall, else done {smashed, opened, cut (the climb's wounds above 0), wounds (the
-- rise in getNumPartsScratched + getNumPartsBleeding since the climb was queued)}; its action gone from the queue
-- WINDOW_SETTLE_MS with the player on the near side, failed. WINDOW_MS after the first tick, interrupted.
-- Appended here (the file's climb helpers are its locals); the stance is released by K.start's wrapper above.
K.WINDOW_OPEN_MS = 15000    -- an open still shut this long after its action left the queue ends the open
K.WINDOW_SMASH_MS = 6000    -- a smash whose window still reads whole this long after its action left the queue fails
K.WINDOW_SETTLE_MS = 4000   -- the climb's state plays on after its action leaves the queue; past this, a near side fails
K.WINDOW_MS = 60000         -- a window not climbed within this wall time of the first tick is interrupted
local FALLS = { fall = true, fallback = true, fallfront = true }

-- the square's window: its IsoWindow, else a thumpable window or an IsoWindowFrame, and which ("window" or "other")
local function windowOn(sq)
    local other = nil
    local objs = W.objectsOn(sq)
    for _, o in ipairs(objs) do
        if W.isA(o, "IsoWindow") then return o, "window" end
        if other == nil and (W.isA(o, "IsoWindowFrame") or W.kindOf(o) == "window") then other = o end
    end
    if other ~= nil then return other, "other" end
    return nil, nil
end

local function reads(o, member, ...)
    local _, v = PZA.call(o, member, ...)
    return v == true
end

local function climbable(st, p) return reads(st.win, "canClimbThrough", p) end

-- the edge the window sits on: north when getNorth() (else isNorth()) reads true
local function windowNorth(win)
    local ok, n = PZA.call(win, "getNorth")
    if not ok then
        local _, m = PZA.call(win, "isNorth")
        n = m
    end
    return n == true
end

-- the next step after the window read shut: the open, the smash, or nil when none is left
local function shutStep(st)
    if st.kind == "window" and not st.triedOpen and not reads(st.win, "isPermaLocked") then return "open" end
    if st.kind == "window" and st.smash and not st.triedSmash then return "smash" end
    return nil
end

-- queues one step's action behind whatever the queue holds: nil, or the failure reason
local function queueStep(p, st, step)
    local ok, why, action
    if step == "climb" then
        ok, why, action = K.queueAction(ISClimbThroughWindow, "not valid", nil, p, st.win, 0)
        if ok then st.wounds0 = woundCount(p) end
    elseif step == "open" then
        ok, why, action = K.queueAction(ISOpenCloseWindow, "not valid", nil, p, st.win)
        st.triedOpen = true
    else
        ok, why, action = K.queueAction(ISSmashWindow, "not valid", nil, p, st.win)
        st.triedSmash = true
    end
    if not ok then return why end
    st.step, st.action, st.leftAt = step, action, nil
    return nil
end

-- the first tick: the walk to the near square (when needed) and the first step queued behind it; nil, or the reason
local function windowFirst(p, st)
    local px, py, pz = posOf(p, true)
    if px == nil or py == nil then return "not loaded" end
    clearQueue(p)
    MO.want("walk")
    PZA.call(p, "setForceRun", false)
    PZA.call(p, "setForceSprint", false)
    st.side0, st.z0, st.startAt = sideOf(st, px, py), pz, PZA.now()
    local nx, ny = nearOf(st, st.side0)
    st.nx, st.ny = nx, ny
    if math.floor(px) ~= nx or math.floor(py) ~= ny then
        local nsq = K.squareAt(nx, ny, st.z)
        if nsq == nil then return "no square" end
        if not K.queueWalk(p, nsq) then return "no path" end
    end
    if climbable(st, p) then return queueStep(p, st, "climb") end
    local step = shutStep(st)
    if step == nil then return "locked" end
    return queueStep(p, st, step)
end

-- the player stands within one square of the near square
local function atNear(st, px, py)
    if px == nil or py == nil then return false end
    return math.max(math.abs(math.floor(px) - st.nx), math.abs(math.floor(py) - st.ny)) <= 1
end

-- the next step queued after an open or a smash: nil, or the skill's end
local function thenStep(p, st, step)
    local why = queueStep(p, st, step)
    if why ~= nil then return "failed", why end
    return nil
end

-- an open or a smash step after its action left the queue: nil while it waits, else the skill's end
local function shutTick(p, st, now)
    if st.step == "smash" then
        if reads(st.win, "isSmashed") then
            st.smashed = true
            return thenStep(p, st, "climb")
        end
        if now - st.leftAt >= K.WINDOW_SMASH_MS then return "failed", "interrupted" end
        return nil
    end
    if climbable(st, p) then
        st.opened = true
        return thenStep(p, st, "climb")
    end
    if reads(st.win, "IsOpen") then return "failed", "not valid" end
    if reads(st.win, "isPermaLocked") or now - st.leftAt >= K.WINDOW_OPEN_MS then
        local step = shutStep(st)
        if step == nil then return "failed", "locked" end
        clearQueue(p)
        return thenStep(p, st, step)
    end
    return nil
end

-- the climb step: nil while it runs, else the skill's end
local function climbTick(p, st, now)
    local _, oc = PZA.call(p, "getVariableString", "ClimbWindowOutcome")
    if oc ~= nil and FALLS[oc] then st.fell = true end
    local px, py, pz = posOf(p, true)
    if pz ~= nil and st.z0 ~= nil and pz ~= st.z0 then st.fell = true end
    if px ~= nil and py ~= nil and across(st, px, py) then
        if st.fell then return "failed", "fell" end
        local wounds = math.max(0, woundCount(p) - (st.wounds0 or 0))
        return "done", { smashed = st.smashed, opened = st.opened, cut = wounds > 0, wounds = wounds }
    end
    if st.leftAt ~= nil and now - st.leftAt >= K.WINDOW_SETTLE_MS then
        if st.fell then return "failed", "fell" end
        return "failed", "failed"
    end
    return nil
end

K.types.window = {
    check = function(args, p)
        local x, y, smash = args.x, args.y, args.smash
        if type(x) ~= "number" or type(y) ~= "number" then return false, "bad args" end
        if smash == nil then smash = false end
        if type(smash) ~= "boolean" then return false, "bad args" end
        x, y = math.floor(x), math.floor(y)
        local z = K.floorOf(p)
        local sq = K.squareAt(x, y, z)
        if sq == nil then return false, "no square" end
        local win, kind = windowOn(sq)
        if win == nil then return false, "not a window" end
        if reads(win, "isBarricaded") then return false, "locked" end
        local st = { x = x, y = y, z = z, win = win, kind = kind, north = windowNorth(win), smash = smash,
                     startAt = nil, smashed = false, opened = false, fell = false }
        if not climbable(st, p) then
            if kind ~= "window" then return false, "locked" end
            if reads(win, "IsOpen") or reads(win, "isSmashed") then return false, "not valid" end
            if not smash and reads(win, "isPermaLocked") then return false, "locked" end
        end
        return true, "", st
    end,
    tick = function(p, st)
        if isDead(p) then return "failed", "dead" end
        if st.startAt == nil then
            local why = windowFirst(p, st)
            if why ~= nil then return "failed", why end
            return nil
        end
        local now = PZA.now()
        if now - st.startAt >= K.WINDOW_MS then return "failed", "interrupted" end
        if st.leftAt == nil and not inQueue(st.action) then
            st.leftAt = now
            local px, py = posOf(p)
            if st.step ~= "climb" and not atNear(st, px, py) then return "failed", "not adjacent" end
        end
        if st.step == "climb" then return climbTick(p, st, now) end
        if st.leftAt == nil then return nil end
        return shutTick(p, st, now)
    end,
}
