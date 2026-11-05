-- PZAgent_StanceMelee.lua — the melee reflex (PZA/1.8, Plan 28 Task 7a; survival iteration 22, cut 1 of the maneuver
-- layer: docs/superpowers/plans/2026-11-04-plan-28-the-strike.md, Task 7). The skill melee owns one zombie from the
-- combat stance to the kill at the client's tick rate: the sub-second sequence (face, press a tick later, read the
-- strike's end, back off, shove again, stomp the fallen) that the planner's 0.5 s tick cannot time (F12's eight of nine
-- hits came 0.645 to 1.043 s after a strike that left the zombie standing). Registered into PZA.skills.types like
-- PZAgent_Stance.lua's skills; the runner (K.start, K.tick) owns every act line, the S-12 and S-15 guards and MO.off at
-- every end. Loads after PZAgent_Stance.lua and before PZAgent_Tend.lua: client files load by name, sorted
-- case-insensitively (#0850), and "pzagent_stance.lua" sorts before "pzagent_stancemelee.lua" ("." before "m"); a name
-- starting "PZAgent_M" would load before PZAgent_Skills.lua. Every Java member through PZA.call (index-first), every
-- vanilla class index-checked; no goto, no integer format of a float, no # on a Java list.
--
-- melee {targetId, mode, reach, keepR, shoveR, releaseR, backVx, backVy, seconds, floorSwing}
--   targetId  the zombie (K.zombieById); mode strike (the weapon swing within reach, the shove per the reflexes), shove
--   (no weapon swing at a standing target) or finish (the target fallen: the stomp or the floor swing only); reach the
--   swing's distance (0: the held weapon's K.reachOf, read once); keepR the back leg's bound after a miss; shoveR the
--   shove's distance (shove mode's, the early shove's at a chasing target, the point blank after a miss); releaseR
--   beyond which it fails out of range; (backVx, backVy) the back leg's world heading, the planner's clear-turned one
--   ((0, 0): stand); seconds the span; floorSwing the floor swing allowed at a fallen target. Every tunable is the
--   planner's argument; the Lua's own constants are the engine's (K.STOMP_R, K.STAND_R, K.SWING_MS, K.FACE_TICKS,
--   K.STOMP_APPROACH_MS) and two of its own below, a steering tolerance and a prefilter, neither a behaviour.
-- check: the args typed (bad args: targetId a number, mode one of the three, the seven numbers numbers, seconds above
--   0, reach 0 or more, floorSwing absent or a boolean); the target live and readable (no target), within releaseR (too
--   far); in strike mode a weapon held (no weapon).
-- tick: the player dead fails dead; the target dead ends done (end dead). The first tick checks the members every step
--   may call (setForceAim, nullifyAiming, faceThisObject, DoAttack, setDoShove, setAutoWalk, setAutoWalkDirection,
--   Vector2.new: not loaded) and reads the target's health. Then d, the distance read live from the target object
--   (DistToProper, the planar distance in one call, T91.3; else the two positions; unreadable: not loaded), and the
--   first reflex that matches (the architecture review's section 3.3 order):
--    2. a hit reaction (hasHitReaction): step hit, no press (no swing starts in one, #4292), the walk stopped, a running
--       strike's end still tracked; a new run of it counts one hit.
--    3. a strike running: its step held until its end (isAttackStarted read true then false, or K.SWING_MS) and one
--       tick more, then its result: the target's isKnockedDown (a knockdown counted for a swing or a shove; the knock
--       wait armed) and its health against the press's; a swing or a shove that left it standing and unhurt is a miss.
--    4. d beyond releaseR fails out of range; another standing zombie within K.STAND_R of the player (the engine's press
--       would take it) fails crowd with result {id, d} (the last frame's records within K.STAND_R + CROWD_SLACK read
--       live); seconds passed ends done (end time). A running strike or a hit holds the time end until it ends.
--    5. the target fallen (isOnFloor): with floorSwing, a weapon and d within the reach, the floor swing (a weapon's
--       floor attack multiplies its damage by at least 5, #4374); else within K.STOMP_R the stomp (the shove pair at the
--       floor, #4372); else the auto-walk to it, unaimed at a walk (stomp_walk; out of reach after K.STOMP_APPROACH_MS).
--    6. knocked down by its own strike (or, in finish mode, reading isKnockedDown) and not yet on the floor: knock_wait in
--       the stance, no press; the stomp follows on the first tick reading isOnFloor. A finish whose target stands fails
--       stood.
--    7. the shove: in shove mode within shoveR; after a miss within shoveR (P28-B2); or a target chasing the player
--       (getTarget is the player, T91.1) whose d fell since the last tick, within shoveR (P28-B1); a shove's face, once
--       begun, presses as a shove while the target stays within shoveR.
--    8. the swing: in strike mode within the reach, not after a miss (the back leg owns the miss).
--    9. after a miss within keepR: the back leg in the stance along (backVx, backVy), facing the target each tick (a zero
--       heading stands); the miss cleared once d reaches keepR (or by the shove of 7).
--   10. an idle target (getTarget nil) beyond the reach (shoveR in shove mode): close on it at a walk in the stance.
--   11. otherwise stand in the stance, facing it.
--   Every press (swing, shove, stomp, floor) faces the target with the stance released (the aimed player faces the
--   cursor every update, #4589, and a shove under aim can lose its shove, T91.2) and presses on a later tick (P28-F,
--   K.FACE_TICKS: the hit test reads the animation's angle at the press, #4591, turned only on the update after the
--   face, #4590); the stance is re-taken by the next step that holds it. The swing's face is its own step (face).
-- The act lines: progress on every step change and once a second while a step holds, result {step, d, hp, swings,
--   shoves, stomps, floors, knockdowns, hits} (the runner's PZA/1.8 progress with a result); done {end, kill, the five
--   counts, hits, hp0, hp1, dMin, steps {step: ticks}}; failed dead, out of range, crowd {id, d}, no weapon, not
--   loaded, stood, out of reach, superseded, interrupted. The frame's act.step is K.cur.st.step (K.status).
-- The stance across re-sends: a melee superseded by a melee of the same target keeps it (the stop hook reads
--   K.startingCmd, PZAgent_Stance.lua's K.start wrapper), so the planner's re-send for a fresh heading takes no new one;
--   every other end releases it (done, a failure, a supersede by any other command).
-- The cost a tick with no press (counted in test_lua_melee.py): the dead check (2), the target's isDead (1), d (1), the
--   hit read (1), isOnFloor (1), getTarget where 7, 10 or 11 asks (1) and the facing (1): 8 standing, 7 on the back
--   leg, 6 while a strike runs; the close adds the two positions (4) and sets its walk only when the heading turned.
local K = PZA.skills
local MO = PZA.motor
local W = PZA.world
local isDead, posOf = K.isDead, W.posOf
local ST = K.stance
local release = K.releaseStance

K.MELEE_TURN_DOT = 0.985     -- the close's and the stomp walk's heading set again only past this cosine (about 10 deg)
K.MELEE_CROWD_SLACK = 1.0    -- tiles: a record of the last frame farther than K.STAND_R + this is not read live for crowd

local MODES = { strike = true, shove = true, finish = true }
local NUMS = { "reach", "keepR", "shoveR", "releaseR", "backVx", "backVy", "seconds" }
local MEMBERS = { "setForceAim", "nullifyAiming", "faceThisObject", "DoAttack", "setDoShove", "setAutoWalk",
                  "setAutoWalkDirection" }
local COUNT = { swing = "swings", shove = "shoves", stomp = "stomps", floor = "floors" }
local STRIKE_STEPS = { face = true, swing = true, shove = true, stomp = true, floor = true }

-- the planar distance from the player to z: DistToProper (one call, T91.3), else the four position reads; nil unreadable
local function distTo(p, z)
    local ok, d = PZA.call(p, "DistToProper", z)
    if ok and type(d) == "number" then return d end
    return (K.zombieDist(p, z))
end

local function healthOf(z)
    local _, h = PZA.call(z, "getHealth")
    if type(h) == "number" then return h end
    return nil
end

local function weaponOf(p)
    local _, w = PZA.call(p, "getPrimaryHandItem")
    return w
end

local function hitReaction(p)
    local _, hit = PZA.call(p, "hasHitReaction")
    return hit == true
end

local function targetOf(st)
    local _, t = PZA.call(st.z, "getTarget")
    return t
end

-- the swing's distance: the argument, else the held weapon's K.reachOf read once (0 with nothing held)
local function reachOf(p, st)
    if st.reach > 0 then return st.reach end
    if st.weaponReach == nil then
        local w = weaponOf(p)
        if w == nil then return 0 end
        st.weaponReach = K.reachOf(p, w)
    end
    return st.weaponReach
end

-- every member a step may call, and Vector2's constructor, present (index-checked: not loaded otherwise)
local function meleeLoaded(p)
    if Vector2 == nil or Vector2.new == nil then return false end
    for i = 1, #MEMBERS do
        if not PZA.field(p, MEMBERS[i]) then return false end
    end
    return true
end

local function face(p, st)
    PZA.call(p, "faceThisObject", st.z)
end

-- the stance taken when not held (the run latches off: the stance walks), and the target faced
local function holdStance(p, st)
    if not ST.held then
        MO.want("walk")
        PZA.call(p, "setForceRun", false)
        PZA.call(p, "setForceSprint", false)
        PZA.call(p, "setForceAim", true)
        ST.held = true
        MO.wantAim = true
    end
    face(p, st)
end

local function stopWalk(p, st)
    if st.walk == nil then return end
    PZA.call(p, "setAutoWalk", false)
    st.walk, st.wx, st.wy = nil, nil, nil
end

-- the auto-walk along world (vx, vy) at a walk, in input space (K.inputVector); set again only for another kind of walk
-- or a heading turned past MELEE_TURN_DOT, so a straight leg makes no Vector2 after its first tick
local function walkAlong(p, st, kind, vx, vy)
    local n = math.sqrt(vx * vx + vy * vy)
    if n <= 0 then
        stopWalk(p, st)
        return
    end
    local ux, uy = vx / n, vy / n
    if st.walk == kind and ux * st.wx + uy * st.wy >= K.MELEE_TURN_DOT then return end
    local ix, iy = K.inputVector(ux, uy)
    PZA.call(p, "setAutoWalk", true)
    PZA.call(p, "setAutoWalkDirection", Vector2.new(ix, iy))
    st.walk, st.wx, st.wy = kind, ux, uy
end

-- the walk straight at the target; false when a position cannot be read
local function towardTarget(p, st, kind)
    local zx, zy = posOf(st.z)
    local px, py = posOf(p)
    if zx == nil or zy == nil or px == nil or py == nil then return false end
    walkAlong(p, st, kind, zx - px, zy - py)
    return true
end

-- a press: the face with the stance released on its first tick (the kind it began for kept in st.faceKind), the press
-- K.FACE_TICKS later (the shove flag first for a shove or a stomp, the weapon read for a swing or a floor swing: no
-- weapon), held facing while an attack still runs (isAttackStarted: the engine drops a press then, #4292, as when a melee
-- supersedes an attack mid-swing); the step, or "failed", reason
local function strike(p, st, kind)
    stopWalk(p, st)
    local faceStep = kind
    if kind == "swing" then faceStep = "face" end
    if st.face == nil then
        if ST.held then release(p) end
        MO.want("walk")
        PZA.call(p, "setForceRun", false)
        PZA.call(p, "setForceSprint", false)
        face(p, st)
        st.face, st.faceKind = 0, kind
        return faceStep
    end
    st.face = st.face + 1
    if st.face < K.FACE_TICKS then
        face(p, st)
        return faceStep
    end
    if (kind == "swing" or kind == "floor") and weaponOf(p) == nil then return "failed", "no weapon" end
    face(p, st)
    local _, busy = PZA.call(p, "isAttackStarted")
    if busy == true then return faceStep end
    local h = healthOf(st.z)
    if kind == "shove" or kind == "stomp" then pcall(PZA.call, p, "setDoShove", true) end
    pcall(PZA.call, p, "DoAttack", 0)
    st.face, st.faceKind, st.missed = nil, nil, false
    st.strike = { kind = kind, at = PZA.now(), started = false, ended = false, health0 = h }
    st[COUNT[kind]] = st[COUNT[kind]] + 1
    return kind
end

-- the running strike: false until a tick after its end (isAttackStarted read true and then false, or K.SWING_MS)
local function strikeOver(p, st)
    local s = st.strike
    if s.ended then return true end
    local _, started = PZA.call(p, "isAttackStarted")
    if started == true then
        s.started = true
    elseif s.started then
        s.ended = true
        return false
    end
    if PZA.now() - s.at >= K.SWING_MS then s.ended = true end
    return false
end

-- the ended strike's result: a knockdown (counted for a swing or a shove, the knock wait armed), a miss (a swing or a
-- shove that left the target standing and unhurt), the shove flag cleared after a shove or a stomp
local function strikeResult(p, st)
    local s = st.strike
    st.strike = nil
    if s.kind == "shove" or s.kind == "stomp" then K.releaseShove(p) end
    local knocked = K.knockedDown(st.z)
    local h = healthOf(st.z)
    local hurt = h ~= nil and s.health0 ~= nil and h < s.health0
    if s.kind == "swing" or s.kind == "shove" then
        if knocked then st.knockdowns = st.knockdowns + 1 end
        st.missed = not knocked and not hurt
    end
    if knocked then st.knocked = true end
end

-- another standing zombie within K.STAND_R of the player: its id and distance, or nil. The candidates are the last
-- frame's records (a Lua table, Sense's S.last) within K.STAND_R + MELEE_CROWD_SLACK, each read live (dead, on the floor,
-- its distance) through the frame's own object map (S.zobj); no frame, no candidate
local function crowd(p, st)
    local S = PZA.sense
    local f = S ~= nil and S.last or nil
    local objs = S ~= nil and S.zobj or nil
    local recs = f ~= nil and f.zombies or nil
    if recs == nil or objs == nil then return nil end
    for i = 1, #recs do
        local rec = recs[i]
        if rec.id ~= st.id and type(rec.dist) == "number" and rec.dist < K.STAND_R + K.MELEE_CROWD_SLACK then
            local o = objs[rec.id]
            if o ~= nil and not K.zombieDead(o) and not K.onFloor(o) then
                local d = distTo(p, o)
                if d ~= nil and d < K.STAND_R then return rec.id, d end
            end
        end
    end
    return nil
end

-- the walk to a fallen target beyond K.STOMP_R, unaimed at a walk (the stomp's own walk): stomp_walk, or failed
local function stompWalk(p, st)
    if ST.held then release(p) end
    local now = PZA.now()
    if st.stompAt == nil then
        st.stompAt = now
        MO.want("walk")
    end
    if now - st.stompAt >= K.STOMP_APPROACH_MS then return "failed", "out of reach" end
    if not towardTarget(p, st, "stomp") then return "failed", "out of reach" end
    return "stomp_walk"
end

-- the reflexes in order, first match wins: the step, or "failed", reason[, result], or "done", end
local function reflex(p, st, d)
    local z = st.z
    if hitReaction(p) then
        if not st.inHit then st.hits = st.hits + 1 end
        st.inHit = true
        if st.strike ~= nil then strikeOver(p, st) end
        stopWalk(p, st)
        return "hit"
    end
    st.inHit = false
    if st.strike ~= nil then
        if not strikeOver(p, st) then return st.strike.kind end
        strikeResult(p, st)
    end
    if d > st.releaseR then return "failed", "out of range" end
    local cid, cd = crowd(p, st)
    if cid ~= nil then return "failed", "crowd", { id = cid, d = cd } end
    if PZA.now() - st.startMs >= st.seconds * 1000 then return "done", "time" end
    if K.onFloor(z) then
        st.knocked = false
        if st.floorSwing and d <= reachOf(p, st) and weaponOf(p) ~= nil then return strike(p, st, "floor") end
        if d < K.STOMP_R then return strike(p, st, "stomp") end
        return stompWalk(p, st)
    end
    st.stompAt = nil
    if st.knocked or st.mode == "finish" then
        if K.knockedDown(z) then
            stopWalk(p, st)
            holdStance(p, st)
            return "knock_wait"
        end
        st.knocked = false
    end
    if st.mode == "finish" then return "failed", "stood" end
    local t, read = nil, false
    if d <= st.shoveR then
        if st.mode == "shove" or st.missed or st.faceKind == "shove" then return strike(p, st, "shove") end
        if st.lastD ~= nil and d < st.lastD then
            t, read = targetOf(st), true
            if t ~= nil and t == p then return strike(p, st, "shove") end
        end
    end
    if st.mode == "strike" and not st.missed and d <= reachOf(p, st) then return strike(p, st, "swing") end
    if st.missed then
        if d < st.keepR then
            holdStance(p, st)
            walkAlong(p, st, "back", st.bvx, st.bvy)
            return "back"
        end
        st.missed = false
    end
    if not read then t = targetOf(st) end
    local closeR = st.shoveR
    if st.mode == "strike" then closeR = reachOf(p, st) end
    if t == nil and d > closeR then
        holdStance(p, st)
        if towardTarget(p, st, "close") then return "close" end
    end
    stopWalk(p, st)
    holdStance(p, st)
    return "stand"
end

local function progressResult(st, d)
    return { step = st.step, d = d, hp = healthOf(st.z), swings = st.swings, shoves = st.shoves, stomps = st.stomps,
             floors = st.floors, knockdowns = st.knockdowns, hits = st.hits }
end

-- the done result; the stance released first, then the shove flag
local function doneResult(p, st, how)
    if ST.held then release(p) end
    K.releaseShove(p)
    return { ["end"] = how, kill = how == "dead", swings = st.swings, shoves = st.shoves, stomps = st.stomps,
             floors = st.floors, knockdowns = st.knockdowns, hits = st.hits, hp0 = st.hp0, hp1 = healthOf(st.z),
             dMin = st.dMin, steps = st.steps }
end

-- a supersede by a melee of the same target keeps the stance (the planner's re-send for a fresh heading)
local function keptOnResend(st, reason)
    local c = K.startingCmd
    return reason == "superseded" and K.starting == "melee" and type(c) == "table" and type(c.args) == "table"
        and c.args.targetId == st.id
end

K.types.melee = {
    check = function(args, p)
        local id, mode, fs = args.targetId, args.mode, args.floorSwing
        if type(id) ~= "number" or type(mode) ~= "string" or MODES[mode] ~= true then return false, "bad args" end
        for i = 1, #NUMS do
            if type(args[NUMS[i]]) ~= "number" then return false, "bad args" end
        end
        if args.seconds <= 0 or args.reach < 0 then return false, "bad args" end
        if fs == nil then fs = false end
        if type(fs) ~= "boolean" then return false, "bad args" end
        local z = K.zombieById(p, id)
        if z == nil or K.zombieDead(z) then return false, "no target" end
        local d = distTo(p, z)
        if d == nil then return false, "no target" end
        if d > args.releaseR then return false, "too far" end
        if mode == "strike" and weaponOf(p) == nil then return false, "no weapon" end
        return true, "", { id = id, z = z, mode = mode, reach = args.reach, keepR = args.keepR, shoveR = args.shoveR,
                           releaseR = args.releaseR, bvx = args.backVx, bvy = args.backVy, seconds = args.seconds,
                           floorSwing = fs, startMs = nil, step = nil, lastP = 0, lastD = nil, dMin = nil, hp0 = nil,
                           swings = 0, shoves = 0, stomps = 0, floors = 0, knockdowns = 0, hits = 0, steps = {},
                           face = nil, faceKind = nil, strike = nil, missed = false, knocked = false, inHit = false, walk = nil,
                           wx = nil, wy = nil, stompAt = nil, weaponReach = nil }
    end,
    tick = function(p, st)
        if isDead(p) then return "failed", "dead" end
        if K.zombieDead(st.z) then return "done", doneResult(p, st, "dead") end
        if st.startMs == nil then
            if not meleeLoaded(p) then return "failed", "not loaded" end
            st.startMs = PZA.now()
            st.hp0 = healthOf(st.z)
            MO.want("walk")
        end
        local d = distTo(p, st.z)
        if d == nil then return "failed", "not loaded" end
        if st.dMin == nil or d < st.dMin then st.dMin = d end
        local step, why, res = reflex(p, st, d)
        st.lastD = d
        if step == "failed" then return "failed", why, res end
        if step == "done" then return "done", doneResult(p, st, why) end
        if not STRIKE_STEPS[step] then st.face, st.faceKind = nil, nil end
        st.steps[step] = (st.steps[step] or 0) + 1
        local now = PZA.now()
        if step ~= st.step or now - st.lastP >= K.PROGRESS_MS then
            st.step, st.lastP = step, now
            return "progress", progressResult(st, d)
        end
        return nil
    end,
    -- every end but done: the stance released unless a melee of the same target supersedes it, then the shove flag
    stop = function(p, st, reason)
        if ST.held and not keptOnResend(st, reason) then release(p) end
        K.releaseShove(p)
    end,
}
