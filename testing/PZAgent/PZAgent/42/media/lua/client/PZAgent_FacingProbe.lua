-- PZAgent_FacingProbe.lua — the facing probe (PZA/1.11, Plan 32 Task 1; the spec `2026-11-08-plan-32-the-facing-design.md`
-- section 4.1; the facing jar read `.superpowers/sdd/2026-11-05-plan-31-the-rebuild/facing-jar-research.md`, its six
-- experiments made one act). The engine writes the aimed player's facing from the mouse on every update after
-- OnPlayerUpdate (the jar read's claims 7 and 11), so the harness's faceThisObject is lost under the stance; the probe
-- reads, per tick and at float resolution, which writer won under each candidate mechanism, before anything is adopted.
-- A harness experiment for the zombie-free trial driver, never a planner action. Registered into PZA.skills.types like
-- PZAgent_StanceMelee.lua's melee; the runner (K.start, K.tick) owns every act line, the S-12 and S-15 guards and MO.off
-- at every end. Client files load by name, sorted case-insensitively (#0850): "pzagent_facingprobe.lua" sorts first,
-- before PZAgent_Motor.lua and PZAgent_Skills.lua, so this file touches nothing but PZA.skills.types at load (the table
-- made here when absent, which PZAgent_Skills.lua keeps: PZA.skills = PZA.skills or {}, K.types = K.types or {}) and
-- reaches K's helpers (K.isDead, K.zombieById, K.zombieDead, K.inputVector, K.stance, K.releaseStance) and PZA.motor only
-- when a probe runs. Every Java member through PZA.call (index-first), Vector2.new index-checked; no goto, no integer
-- format of a float, no # on a Java list.
--
-- probe {mode, targetId, x, y, ticks, k, vx, vy}
--   mode (the schema's probeMode enum, PZA.schema.probeModes) the mechanism probed; targetId the zombie (K.zombieById;
--   -1, the default, takes the point); x, y the point (each 0 or more when no targetId); ticks the ring ticks (a whole
--   number, 1 or more; 60 by default); k turn_k's turn delta (above 0; ignored by the other modes); vx, vy a back-pedal
--   (non-zero: the steer skill's auto-walk along the world vector at a walk, in input space, K.inputVector, as
--   PZAgent_Stance.lua's aim walks it; cleared at the end).
-- check: bad args (mode not in the enum; a number field not a number; ticks not a whole number of 1 or more; turn_k's
--   k 0 or less); no target (targetId 0 or more and no live listed zombie by it; no targetId and x or y below 0).
-- tick: the player dead fails dead (the mode exited first). The first tick checks every member the mode will call
--   (failed not loaded, the result's missing naming the first absent one; nothing written). Each ring tick, in order:
--    1. the readings, before any write (the jar read's experiment 1): fwd getDirectionAngleRadians, body
--       getAnimAngleRadians, look getLookAngleRadians, twist getTwist (degrees), aim the direction of getAimVector(v)
--       (nil at zero length; the Vector2 made once), aiming isAiming, forceAim isForceAim, autoWalk isAutoWalk, the
--       bearing b = atan2(ty - py, tx - px) to the target (its position read live; the previous b held when the target
--       sits within K.PROBE_MIN_D, where no facing is written: a zero vector raises in setForwardDirection, the jar
--       read's claim 16), err_body and err_look body - b and look - b wrapped to (-180, 180] degrees;
--    2. on the first tick only, the mode's enter (and the back-pedal's walk);
--    3. the mode's write toward the target;
--    4. on the last tick of snap_aimed or unaimed_snap at a zombie, the press DoAttack(0) after the snap (guarded as the
--       melee's press), the target's health read before it;
--   and one progress line (result_probe_step). The tick after the last ends done with the summary (result_probe): the
--   median and the 90th percentile (nearest rank) of |err_body| and |err_look|, hold30 the share of ring ticks with
--   |err_body| under K.PROBE_HOLD_DEG, aiming_share the share reading isAiming true, pressed, and the press leaf (the
--   melee's keys d_press, look_off, hp0, hp1 read now, cut_by refused when isAttackStarted reads false now).
-- The modes, each a table {enter, write, exit} below: the aimed modes (read, snap_aimed, ignore_aim) take the stance as
--   PZAgent_Stance.lua's aim takes it (the run latches off, setForceAim(true), K.stance.held and PZA.motor.wantAim set,
--   so the Motor re-asserts the force-aim every frame) and release it at the end (K.releaseStance: nullifyAiming); the
--   unaimed modes (unaimed_face, unaimed_snap, block_aim, turn_k) drop it on enter (K.stance.held and wantAim false,
--   setForceAim(false) once). The writes: face (faceThisObject(z) at a zombie, faceLocationF(x, y) at a point) or snap
--   (setTargetAndCurrentDirection(cos b, sin b), the one call that sets the body angle itself, the jar read's claim 14).
--   block_aim adds setBlockMovement(true) and setIsAiming(true) on enter, setBlockMovement(false) and nullifyAiming() on
--   exit (claim 24); ignore_aim setIgnoreAimingInput(true) and false (claim 22); turn_k reads getTurnDelta() on enter,
--   writes setTurnDelta(k) and restores the read value on exit (claim 17).
-- Every flag a mode sets is restored on every exit path, each call under its own pcall (a raise counted in K.errors,
--   the next call still made: MO.off's form): on done (before the line), on a stop or a supersede (the stop hook), on a
--   raise inside a tick (the tick is run under pcall: the mode exited, the raise counted, failed interrupted with the
--   summary so far); exited once. The cost a ring tick: eleven reads (eight getters, two positions, the vector's length
--   and direction) and one or two writes; one progress line a tick, so a probe is a short experiment, never a loop.
PZA.skills = PZA.skills or {}
local K = PZA.skills
K.types = K.types or {}

K.PROBE_MIN_D = 0.01      -- tiles: a target nearer holds the previous bearing and is not faced (a zero vector raises)
K.PROBE_HOLD_DEG = 30     -- degrees: the hold30 share's bound (the spec's success criterion 1, the 90th percentile)

local DEG = 180 / math.pi
local RING = { "getDirectionAngleRadians", "getAnimAngleRadians", "getLookAngleRadians", "getTwist", "getAimVector",
               "isAiming", "isForceAim", "isAutoWalk", "getX", "getY" }
local NUMS = { "targetId", "x", "y", "ticks", "k", "vx", "vy" }
local DEFAULTS = { targetId = -1, x = -1, y = -1, ticks = 60, k = -1, vx = 0, vy = 0 }
local aimVec = nil        -- the Vector2 getAimVector fills, made once

-- the object's world x and y (the shared world reader, shared/ loading before client/)
local function posOf(o)
    return PZA.world.posOf(o)
end

-- a raise caught at an exit (S-15): counted, its message kept
local function caught(err)
    K.errors = (K.errors or 0) + 1
    K.lastError = tostring(err)
end

-- one exit call under its own pcall, so a raise never leaves the next one unmade
local function guarded(fn, ...)
    local ok, err = pcall(fn, ...)
    if not ok then caught(err) end
end

local function num(p, name)
    local ok, v = PZA.call(p, name)
    if ok and type(v) == "number" then return v end
    return nil
end

local function bool(p, name)
    local ok, v = PZA.call(p, name)
    if ok and type(v) == "boolean" then return v end
    return nil
end

-- r radians wrapped to (-180, 180] degrees
local function wrapDeg(r)
    local d = r * DEG
    while d > 180 do d = d - 360 end
    while d <= -180 do d = d + 360 end
    return d
end

-- the aim vector's direction in radians, nil at zero length or unread
local function aimOf(p)
    local ok, v = PZA.call(p, "getAimVector", aimVec)
    if not ok then return nil end
    local _, len = PZA.call(v, "getLength")
    if type(len) ~= "number" or len <= 0 then return nil end
    local _, a = PZA.call(v, "getDirection")
    if type(a) == "number" then return a end
    return nil
end

local function healthOf(z)
    local _, h = PZA.call(z, "getHealth")
    if type(h) == "number" then return h end
    return nil
end

-- ---- the stance and the writes ---------------------------------------------------------------------------------------

-- the stance taken as PZAgent_Stance.lua's aim takes it: the run latches off (the stance walks), the force-aim set
-- and wanted, so the Motor re-asserts it every frame (PZAgent_Motor.lua's header)
local function stanceOn(p)
    local MO = PZA.motor
    MO.want("walk")
    PZA.call(p, "setForceRun", false)
    PZA.call(p, "setForceSprint", false)
    PZA.call(p, "setForceAim", true)
    if K.stance ~= nil then K.stance.held = true end
    MO.wantAim = true
end

-- the stance released (K.releaseStance: held and wantAim false, nullifyAiming)
local function stanceOff(p)
    if K.releaseStance ~= nil then
        K.releaseStance(p)
        return
    end
    PZA.motor.wantAim = false
    PZA.call(p, "nullifyAiming")
end

-- no stance: the run latches off, held and wantAim dropped, the force-aim written false once
local function unaimed(p)
    local MO = PZA.motor
    MO.want("walk")
    PZA.call(p, "setForceRun", false)
    PZA.call(p, "setForceSprint", false)
    if K.stance ~= nil then K.stance.held = false end
    MO.wantAim = false
    PZA.call(p, "setForceAim", false)
end

-- the face write: faceThisObject at a zombie, faceLocationF at a point; none while the target sits on the player
local function face(p, st, fresh)
    if not fresh then return end
    if st.z ~= nil then
        PZA.call(p, "faceThisObject", st.z)
    else
        PZA.call(p, "faceLocationF", st.tx, st.ty)
    end
end

-- the snap: the body angle set onto b at once (a unit vector, never zero)
local function snap(p, st)
    if st.b == nil then return end
    PZA.call(p, "setTargetAndCurrentDirection", math.cos(st.b), math.sin(st.b))
end

local function noop() end

-- the modes: enter on the first ring tick, write every ring tick, exit once at the end; members the ones each calls
-- beyond the ring's (the face member is the target's: faceThisObject or faceLocationF)
local MODES = {
    read = { enter = stanceOn, write = face, exit = stanceOff, members = { "setForceAim", "nullifyAiming" } },
    snap_aimed = { enter = stanceOn, write = snap, exit = stanceOff,
                   members = { "setForceAim", "nullifyAiming", "setTargetAndCurrentDirection" } },
    unaimed_face = { enter = unaimed, write = face, exit = noop, members = { "setForceAim" } },
    unaimed_snap = { enter = unaimed, write = snap, exit = noop,
                     members = { "setForceAim", "setTargetAndCurrentDirection" } },
    block_aim = {
        enter = function(p)
            unaimed(p)
            PZA.call(p, "setBlockMovement", true)
            PZA.call(p, "setIsAiming", true)
        end,
        write = face,
        exit = function(p)
            guarded(PZA.call, p, "setBlockMovement", false)
            guarded(PZA.call, p, "nullifyAiming")
        end,
        members = { "setForceAim", "setBlockMovement", "setIsAiming", "nullifyAiming" } },
    ignore_aim = {
        enter = function(p)
            stanceOn(p)
            PZA.call(p, "setIgnoreAimingInput", true)
        end,
        write = face,
        exit = function(p)
            guarded(PZA.call, p, "setIgnoreAimingInput", false)
            guarded(stanceOff, p)
        end,
        members = { "setForceAim", "nullifyAiming", "setIgnoreAimingInput" } },
    turn_k = {
        enter = function(p, st)
            unaimed(p)
            st.turn0 = num(p, "getTurnDelta")
            PZA.call(p, "setTurnDelta", st.k)
        end,
        write = face,
        exit = function(p, st)
            if st.turn0 ~= nil then guarded(PZA.call, p, "setTurnDelta", st.turn0) end
        end,
        members = { "setForceAim", "getTurnDelta", "setTurnDelta" } },
}
local PRESSES = { snap_aimed = true, unaimed_snap = true }
local SNAPS = { snap_aimed = true, unaimed_snap = true }

-- the first absent member the probe would call, nil when every one is present
local function absent(p, st)
    if Vector2 == nil or Vector2.new == nil then return "Vector2.new" end
    for i = 1, #RING do
        if not PZA.field(p, RING[i]) then return RING[i] end
    end
    local m = st.mode.members
    for i = 1, #m do
        if not PZA.field(p, m[i]) then return m[i] end
    end
    if not SNAPS[st.name] then
        local f = st.z ~= nil and "faceThisObject" or "faceLocationF"
        if not PZA.field(p, f) then return f end
    end
    if st.walk then
        if not PZA.field(p, "setAutoWalk") then return "setAutoWalk" end
        if not PZA.field(p, "setAutoWalkDirection") then return "setAutoWalkDirection" end
    end
    if st.press and not PZA.field(p, "DoAttack") then return "DoAttack" end
    return nil
end

-- ---- the ring, the press and the summary ---------------------------------------------------------------------------

-- the target's position: the zombie's, read live, else the point
local function targetPos(st)
    if st.z ~= nil then return posOf(st.z) end
    return st.tx, st.ty
end

-- the ring tick's readings before any write; fresh whether the target was read beyond K.PROBE_MIN_D (b taken now)
local function ring(p, st)
    local r = { step = st.n, tick = PZA.tick, fwd = num(p, "getDirectionAngleRadians"),
                body = num(p, "getAnimAngleRadians"), look = num(p, "getLookAngleRadians"), twist = num(p, "getTwist"),
                aim = aimOf(p), aiming = bool(p, "isAiming"), forceAim = bool(p, "isForceAim"),
                autoWalk = bool(p, "isAutoWalk") }
    local px, py = posOf(p)
    local tx, ty = targetPos(st)
    local fresh = false
    if px ~= nil and py ~= nil and tx ~= nil and ty ~= nil then
        local ex, ey = tx - px, ty - py
        st.d = math.sqrt(ex * ex + ey * ey)
        if st.d >= K.PROBE_MIN_D then
            st.b = math.atan2(ey, ex)
            fresh = true
        end
    end
    r.b = st.b
    if st.b ~= nil then
        if r.body ~= nil then r.err_body = wrapDeg(r.body - st.b) end
        if r.look ~= nil then r.err_look = wrapDeg(r.look - st.b) end
    end
    if r.err_body ~= nil then
        st.eb[#st.eb + 1] = math.abs(r.err_body)
        if math.abs(r.err_body) < K.PROBE_HOLD_DEG then st.hold = st.hold + 1 end
    end
    if r.err_look ~= nil then st.el[#st.el + 1] = math.abs(r.err_look) end
    if r.aiming == true then st.aimingN = st.aimingN + 1 end
    return r, fresh
end

-- the press after the last tick's snap, guarded as the melee's press; the leaf's first half
local function press(p, st, r)
    local look = nil
    if r.err_look ~= nil then look = math.abs(r.err_look) end
    local hp = healthOf(st.z)
    pcall(PZA.call, p, "DoAttack", 0)
    st.pressed = true
    st.leaf = { d_press = st.d, look_off = look, hp0 = hp }
end

-- the press leaf's second half, a tick after the press
local function pressResult(p, st)
    st.leaf.hp1 = healthOf(st.z)
    local _, started = PZA.call(p, "isAttackStarted")
    st.leaf.cut_by = started == false and "refused" or ""
end

-- the nearest-rank q quantile of the values (a sorted copy), nil when none
local function rank(vals, q)
    local n = #vals
    if n == 0 then return nil end
    local s = {}
    for i = 1, n do s[i] = vals[i] end
    table.sort(s)
    local i = math.ceil(q * n)
    if i < 1 then i = 1 end
    return s[i]
end

local function summary(st)
    local out = { ticks = st.n, mode = st.name, err_body_med = rank(st.eb, 0.5), err_body_p90 = rank(st.eb, 0.9),
                  err_look_med = rank(st.el, 0.5), err_look_p90 = rank(st.el, 0.9), pressed = st.pressed,
                  press = st.leaf }
    if st.n > 0 then
        out.hold30 = st.hold / st.n
        out.aiming_share = st.aimingN / st.n
    end
    return out
end

-- the mode's exit and the walk's clear, once, each call guarded; nothing when the mode never entered
local function exitOnce(p, st)
    if not st.entered or st.exited then return end
    st.exited = true
    if st.walk then guarded(PZA.call, p, "setAutoWalk", false) end
    guarded(st.mode.exit, p, st)
end

-- the back-pedal: the steer skill's auto-walk along the world vector, in input space, at a walk
local function walkOn(p, st)
    local ix, iy = K.inputVector(st.vx, st.vy)
    PZA.call(p, "setAutoWalk", true)
    PZA.call(p, "setAutoWalkDirection", Vector2.new(ix, iy))
end

local function probeTick(p, st)
    if K.isDead(p) then
        exitOnce(p, st)
        return "failed", "dead", summary(st)
    end
    if st.n >= st.ticks then
        if st.pressed then pressResult(p, st) end
        exitOnce(p, st)
        return "done", summary(st)
    end
    if st.n == 0 then
        local miss = absent(p, st)
        if miss ~= nil then return "failed", "not loaded", { ticks = 0, mode = st.name, pressed = false, missing = miss } end
        if aimVec == nil then aimVec = Vector2.new(0, 0) end
    end
    st.n = st.n + 1
    local r, fresh = ring(p, st)
    if not st.entered then
        st.entered = true
        st.mode.enter(p, st)
        if st.walk then walkOn(p, st) end
    end
    st.mode.write(p, st, fresh)
    if st.press and st.n == st.ticks then press(p, st, r) end
    return "progress", r
end

K.types.probe = {
    check = function(args, p)
        local mode = args.mode
        if type(mode) ~= "string" or PZA.schema.probeModes[mode] ~= true then return false, "bad args" end
        local a = {}
        for i = 1, #NUMS do
            local name = NUMS[i]
            local v = args[name]
            if v == nil then v = DEFAULTS[name] end
            if type(v) ~= "number" then return false, "bad args" end
            a[name] = v
        end
        if a.ticks < 1 or a.ticks ~= math.floor(a.ticks) then return false, "bad args" end
        if mode == "turn_k" and a.k <= 0 then return false, "bad args" end
        local z = nil
        if a.targetId >= 0 then
            if K.zombieById ~= nil then z = K.zombieById(p, a.targetId) end
            if z == nil or K.zombieDead(z) then return false, "no target" end
        elseif a.x < 0 or a.y < 0 then
            return false, "no target"
        end
        return true, "", { name = mode, mode = MODES[mode], z = z, tx = a.x, ty = a.y, ticks = a.ticks, k = a.k,
                           vx = a.vx, vy = a.vy, walk = a.vx ~= 0 or a.vy ~= 0, press = z ~= nil and PRESSES[mode] == true,
                           n = 0, b = nil, d = nil, eb = {}, el = {}, hold = 0, aimingN = 0, entered = false,
                           exited = false, turn0 = nil, pressed = false, leaf = nil }
    end,
    -- the ring under pcall: a raise exits the mode before the runner's failed line (S-12's count kept here)
    tick = function(p, st)
        local ran, state, out, res = pcall(probeTick, p, st)
        if ran then return state, out, res end
        caught(state)
        exitOnce(p, st)
        return "failed", "interrupted", summary(st)
    end,
    -- every end but done (a stop, a supersede, a failure): the mode exited once; the summary so far is the line's
    stop = function(p, st)
        exitOnce(p, st)
        return summary(st)
    end,
}
