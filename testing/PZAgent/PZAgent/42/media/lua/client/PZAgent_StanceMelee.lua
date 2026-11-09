-- PZAgent_StanceMelee.lua — the melee reflex (PZA/1.10, Plan 31 Task 2: the meet, the finish aimed at the head and the
-- spent meet, the spec `2026-11-05-plan-31-the-rebuild-design.md` section 4 items 1, 2 and 2b; first cut PZA/1.8, Plan
-- 28 Task 7a, the maneuver layer's cut 1). The skill melee owns one zombie to the kill at the client's tick rate: the
-- facing written from faceR on, the press when the look is on the target and the target's distance at the swing's
-- collision event is predicted inside the reach, the press again at once after a swing that left it standing (no back
-- step, no pause: a player mid-attack facing an attacking zombie is never bitten, #4688, and a landed hit staggers it,
-- #4686), the finish of a fallen target at its head (#4679), the shove and the stomp when the arms or the moodles are
-- spent (#4370, #4371); it ends on the kill, a hand-back to the decider or a lost target, never on time. Registered into
-- PZA.skills.types like PZAgent_Stance.lua's skills; the runner (K.start, K.tick) owns every act line, the S-12 and S-15
-- guards and MO.off at every end. Loads after PZAgent_Stance.lua and before PZAgent_Tend.lua: client files load by name,
-- sorted case-insensitively (#0850), and "pzagent_stance.lua" sorts before "pzagent_stancemelee.lua" ("." before "m").
-- Every Java member through PZA.call (index-first), every vanilla class index-checked; no goto, no integer format of a
-- float, no # on a Java list.
--
-- melee {targetId, mode, reach, shoveR, releaseR, faceR, pressAngle, pressLo, floorR, handbackR, stall, floorSwing,
--        headAim}
--   targetId the zombie (K.zombieById); mode strike (the meet with the weapon swing), shove (the spent meet: no weapon
--   swing, the shove at a standing target and the stomp at a fallen one) or finish (sent at a fallen target: its
--   finish, then the meet should it stand; needs no weapon); reach the swing's distance at the collision (0: the held
--   weapon's K.reachOf, read once); shoveR the spent meet's shove distance; releaseR beyond which the target is lost;
--   faceR the distance inside which the stance is released and the target faced every tick; pressAngle the most the
--   look may lie off the target's bearing at a press, in degrees; pressLo the least predicted distance at the collision
--   a swing is pressed at; floorR the floor swing's distance to a fallen target's head; handbackR inside which another
--   standing zombie ends a finish handback; stall the presses in a row that lowered nothing and knocked nothing down
--   (a swing, a floor swing or a stomp; a shove does no damage, #4373, and counts none) after which the target is lost;
--   floorSwing the weapon's floor swing allowed at a fallen target; headAim (fix 1, review-t2 F4, the controller's
--   ruling) the finish aimed at the head estimate (PZA.sense.headOf) rather than the zombie's position, off until the
--   estimate's lying direction is calibrated. Every tunable is the planner's argument; the Lua's
--   own constants below are the engine's, each with its row, and three tolerances of its reads, none a behaviour.
-- check: the args typed (bad args: targetId a number, mode in the schema's meleeMode enum, PZA.schema.meleeModes, the
--   nine numbers numbers, reach, shoveR, faceR, pressLo, floorR and handbackR 0 or more, releaseR above 0, pressAngle
--   above 0 and at most 180, stall 1 or more, floorSwing and headAim absent or booleans); the target live and readable (no
--   target), within releaseR (too far); in strike mode a weapon held (no weapon).
-- tick: the player dead fails dead; the target dead ends done kill (a press in flight read first, its leaf on the done
--   line). The first tick checks the members every step may call (setForceAim, nullifyAiming,
--   setTargetAndCurrentDirection, DoAttack, setDoShove, setAutoWalk, setAutoWalkDirection, the press mode's,
--   Vector2.new: not loaded). Then the two positions (unreadable: not
--   loaded), d the planar distance, the target's position kept for its closing speed, and the first reflex that matches:
--    1. a hit reaction (hasHitReaction): step hit, no press (no swing starts in one, #4292), the walk stopped, the
--       facing still written (fix 1, F2); a press in flight is marked cut_by hit (the reaction leaves the swing's
--       state, #4664, and before its collision event the swing does no damage, #4665) and its end still tracked; a new
--       run of it counts one hit.
--    2. a press in flight: its step held, the facing written every tick (fix 1, F2: the collision's dot, #4681, and
--       the bite's facing skip, #4688, read the look, which turns toward the last facing written, #4689), until its
--       end (isAttackStarted read true then false, or K.SWING_MS) and one tick more, then its result: the press leaf
--       (below), a swing or shove's knock-down (isKnockedDown) counted and the knock wait armed, the no-progress run
--       (stall reached: done lost, why no progress). A press isAttackStarted reads false on the tick after it was
--       refused (fix 1, F3: pressedAttack sets attackStarted at the press, review-t2): its leaf cut_by refused, no
--       stall counted, and the meet presses again on that tick. The retry is bounded (the residual): after
--       K.REFUSE_MAX refusals in a row the press waits K.REFUSE_WAIT_MS (step refused, the facing still written), then
--       retries; K.REFUSE_END in a row end it done lost, why refused. A run of refusals writes its leaf only on its
--       first and an act line again at its end (the next accepted press, or the melee's end), each carrying
--       `refusals`, the run's count so far.
--    3. d beyond releaseR: done lost, why out of range. The crowd (Plan 31 Task 15a, the crowd handback's ruling: the
--       swing, hit and handback re-pin loop that killed three street trials of round two, two standing within 0.6
--       tiles handing back before every press): the other standing zombies within K.MELEE_CROWD_R, the crowd radius
--       (#4290's 0.9 tiles; fix 1, review-t15a M4: the read was K.STAND_R's 0.6, under the row; the last frame's
--       records within K.MELEE_CROWD_R + MELEE_CROWD_SLACK read live). K.MELEE_CROWD_N standing (the target
--       counted while it stands: three attackers within 0.9 tiles zero the defence and drag the character down, #4290):
--       done handback, why crowd, with the nearest other's id and d, the count n and the standing zombies' distances
--       ds, nearest first. Fewer: no hand-back (a player mid-attack facing the zombie is never bitten, #4688: the
--       press is the defence); a standing target farther than the nearest other by more than K.MELEE_REPIN_SLACK is
--       re-pinned in the reflex to that one (step repin, its stall, history, health and walk bound restarted, counted
--       in `repins`; every line after it carries `target`, the zombie now pressed), and the meet presses it.
--    4. the target fallen (isOnFloor): the finish. Another standing zombie within handbackR: done handback, why
--       standing, with its id and d; one beyond it never breaks the finish. The facing is pointed at the aim point
--       every tick, unaimed: with headAim the head estimate (PZA.sense.headOf; faceLocationF, else faceThisObject),
--       the floor attack testing the weapon's line along the facing against the head bone first, x3 (#4679); without
--       it (the default until calibrated) the zombie's position (faceThisObject), since a reversed estimate would aim
--       the line at the calves and feet (x0.05, #4679); a floor attack does not turn the body (#4689). With floorSwing, a weapon, the arms and moodles not spent, the head within floorR
--       and the target within the reach: the floor swing (a weapon's floor attack, #4374); else with the aim point within
--       K.MELEE_STOMP_R: the stomp (the shove pair at the floor, #4372, its line 0.3, #4679); each pressed once the look
--       is within pressAngle of the aim point (step head while it turns); else the walk to it, unaimed (stomp_walk).
--       Plan 33 Task 1 (the head step's floor and cap, the block at the end of this file): no look gate under
--       K.HEAD_LOOK_FLOOR, and K.HEAD_MAX_TICKS head ticks with no press end done handback, why head_stall.
--    5. knocked down and not yet on the floor (isKnockedDown, read after the skill's own knock-down and on every tick
--       the target is within the reach or shoveR): knock_wait, facing it, no press.
--    6. the meet, the target standing. Beyond faceR (the latch released only past faceR + MELEE_FACE_SLACK): the stance
--       (stand), or the close at a walk in the stance on a target not closing. Inside it: the stance released, the
--       target faced every tick (faceThisObject; the aimed player faces the cursor, #4589, #4590), and the press waits
--       for the look (getLookAngleRadians: the angle the hit list's dot, #4591, and the bite's facing skip, #4688,
--       read; the body turns toward the facing over time, #4689) within pressAngle of the bearing. The swing: v the
--       target's closing speed over the last K.MELEE_SAMPLES ticks (its displacement toward the player), t_c one update
--       (the last tick's length) plus K.MELEE_HIT_FRAC / CombatSpeed (getCombatSpeed clamped to [0.8, 1.6]: the clip of
--       1.0 s / CombatSpeed whose collision event comes at 25 %, #4665, #4668), the predicted distance at the collision
--       d - v * t_c within [pressLo, reach] (the collision rebuilds the hit list with MaxRange and no lower distance,
--       #4681, #4682), the raw distance at the press within the engine's own reach, the unmargined getMaxRange x
--       getRangeMod (+0.2 against a zombie lunging from under 2 tiles), since the press builds its own hit list and an
--       empty one makes the two-hander's attack a MISS that returns before the critical roll (#4591; fix 1, F1, the
--       review's dump of pressedAttack), and the distance at the swing state's entry, d_min - v * update, beyond the
--       weapon's MinRange (where the shove verdict is taken again, the review's caveat 1; getMinRange, else
--       K.STAND_R). d_min is the distance the shove test reads, the nearest of the target's readable points as the
--       engine takes the nearest of head, pelvis and position (#4682; fix 1, F5): for a standing target its position
--       (no bone is readable from Lua; the head and pelvis stand over it), for a fallen one the nearer of its position
--       and, with headAim, the head estimate. The shove only with d_min inside MinRange at the test (#4372): these
--       point-blank presses are protective presses inside MinRange (the engine shoves), kept though most do nothing
--       (round two's street trials: 7 of 8 at under 0.6 tiles), since the player mid-attack facing the zombie is never
--       bitten (#4688). Spent (mode shove, no weapon, the arms' pain over K.MELEE_SPENT_PAIN or the
--       ENDURANCE or TIRED moodle at K.MELEE_SPENT_MOODLE or more): the shove within shoveR. The spent meet never
--       loops on shoves (Plan 31 Task 15a, the spent meet's ruling: round one's trial 11 read the arms' pain 44 to 363
--       and 7 of 8 shoves doing nothing): after a shove that knocked nothing down (a shove does no damage, #4373) the
--       next press is the swing, as the meet's (its damage divided by the arms' pain, #4370, it still lands and
--       staggers an attacking zombie, #4686), when a weapon is held; inside MinRange that press is the protective
--       shove; once the swing has gone the shove again. A fallen target is stomped (the finish never floor-swings
--       spent; the stomp is undivided, #4374). Not pressed: a target not closing beyond the press's distance is
--       closed on at a walk, unaimed (close); else face.
--   After a press there is no back step and no pause: knocked down, the knock wait and the finish; else the meet's
--   press again as soon as the swing has ended and the look holds.
-- The press leaf, on the act line after each press's result (a progress line, or the done or failed line it ends on):
--   press {d_press, d_collide_pred, d_min, look_off, hp0, hp1, knock, cut_by}: the distance at the press (to the aim
--   point for a floor swing or a stomp), the predicted distance at the collision (the raw distance for a shove, a
--   floor swing or a stomp), the distance the shove test read (d_min, fix 1, F5), the look's angle off the bearing in
--   degrees, the target's health at the press and at the result, whether the result read it knocked down, and what
--   cut the clip early ("hit", "refused" for a press the engine refused, a supersede's reason on the failed line,
--   else ""); a value that could not be read is absent. A shove's leaf adds knock_p (Plan 31 Task 15a), the chance in
--   [0, 1] the engine's critical roll knocks the target down (#4373: 35 - 5 per endurance and heavy-load moodle
--   level - 1.3 per panic level + 2 x Strength, truncated, rolled against Rand.Next(100)), read at the press off the
--   moodles and getPerkLevel(Perks.Strength); a reading, never a decision, and absent when any input is unread (the
--   combat config's from-behind and default additions are not read).
-- The act lines: progress on every step change, on each press leaf and once a second while a step holds, result {step,
--   d, hp, swings, shoves, stomps, floors, knockdowns, hits, spent[, press][, target, repins]}; done {end, kill, why,
--   id, d, the five counts, hits, hp0, hp1, dMin, steps {step: ticks}[, n, ds][, press][, target, repins]}: end kill
--   (the target dead: the re-pinned one once `target` is on the line), handback (why crowd, with the nearest other's
--   id and d, the count n and the distances ds, or standing, with the other zombie's id and d) or lost (why out of
--   range, out of reach: K.STOMP_APPROACH_MS of
--   walking, summed over the melee's walking steps, with no MELEE_WALK_GAIN on its best distance since its last gain
--   or press, fix 1, F6; or no progress); failed dead, no weapon, not loaded,
--   superseded or interrupted (the stop hook's result {the counts[, press]} on the line). The frame's act.step is
--   K.cur.st.step (K.status).
-- The stance across re-sends: a melee superseded by a melee of the same target or by an aim keeps it (the stop hook
--   reads K.starting and K.startingCmd, PZAgent_Stance.lua's K.start wrapper); every other end releases it.
-- The facing (Plan 32 Task 4, the facing trials' ruling, testing/trials/facing.md; the jar read's claims 7, 13, 14, 17,
--   19): every facing write above is the snap, K.FACING at the end of this file. The aimed player's forward direction
--   is the mouse's after OnPlayerUpdate (#4589), so faceThisObject lost to the cursor under the stance (75 to 88
--   degrees off in every probe boot) and converged unaimed at the turn rate only; setTargetAndCurrentDirection(cos b,
--   sin b) sets the body angle itself and held it within 3 degrees under the stance, 0 unaimed. The stance's write
--   (stand, the close) is FACING.hold (the snap, the aim posture kept); the unaimed writes inside faceR and on the
--   floor (face, the head) are the snap too; each press runs inside FACING.press_enter and FACING.press_exit (the
--   press mode K.PRESS_FACING: unaimed_snap releases the force-aim for the press's ticks and snaps body and look, the
--   aim re-asserted at the press's result when it was wanted before; block_aim the switchable alternative), the exit
--   made on every path (the press's result, which a kill's done reads first, and the stop hook on a failure, a
--   supersede or a raise; every other done follows a result). b is the bearing from
--   the player to the target (its head on the floor), held at the last one while the target sits within
--   K.FACING_MIN_D (a zero vector is never written). The press leaf adds body_off, the body angle
--   (getAnimAngleRadians) off b at the press in degrees, and facing, the press mode.
-- The cost a tick with no press (counted in test_lua_melee.py): the dead check (2), the target's isDead (1), the two
--   positions (4), the hit read (1), isOnFloor (1), isKnockedDown within the reach or shoveR (1), the facing (1, a press
--   in flight and the hit step included); inside faceR the look (1) and, with the look on, getCombatSpeed (1); the
--   engine's reach read once a melee, getRealState only with the predicted band met; the spent read once a frame
--   (getMoodles and two levels); getTarget only before two positions are kept. The finish with headAim adds the head
--   (getAnimAngleRadians, isCrawling, isFallOnFront and the two positions, 5).
local K = PZA.skills
local MO = PZA.motor
local W = PZA.world
local isDead, posOf = K.isDead, W.posOf
local ST = K.stance
local release = K.releaseStance

K.MELEE_TURN_DOT = 0.985     -- the walks' heading set again only past this cosine (about 10 deg): a steering tolerance
K.MELEE_CROWD_SLACK = 1.0    -- tiles: a record of the last frame farther than the radius + this is not read live
K.MELEE_STOMP_R = 0.3        -- tiles: a stomp's line reaches 0.3 along the facing (#4679), so the head within it
K.MELEE_HIT_FRAC = 0.25      -- the swing's collision event at 25 % of its clip (#4665), the clip 1.0 s / CombatSpeed (#4668)
K.MELEE_CS_MIN = 0.8         -- CombatSpeed's clamp (#4668)
K.MELEE_CS_MAX = 1.6
K.MELEE_SPENT_PAIN = 10      -- the arms' pain past which every swing but a stomp is divided by a tenth of it (#4370)
K.MELEE_SPENT_MOODLE = 2     -- the endurance or tired moodle level from which a swing's damage is x0.2 or less (#4371)
K.MELEE_SAMPLES = 3          -- ticks the target's closing speed is read over (the spec's section 4 item 1)
K.MELEE_UPDATE_S = 0.017     -- seconds: one update before two ticks have been timed (a client tick at about 60 Hz)
K.MELEE_CLOSING_V = 0.1      -- tiles a second: a target closing slower is not closing (a tolerance of the read)
K.MELEE_FACE_SLACK = 0.5     -- tiles: the faceR latch released only past faceR + this (a tolerance, no flapping stance)
K.MELEE_WALK_GAIN = 0.1      -- tiles a walk must gain on its best distance to restart its bound (a tolerance)
K.MELEE_LUNGE_BONUS = 0.2    -- tiles the collision's reach adds against a zombie lunging at the attacker (#4681)
K.MELEE_LUNGE_R = 2.0        -- tiles: ... from under this (#4681)
K.REFUSE_MAX = 5             -- refused presses in a row after which the press waits (the residual of review-t2 F3: a
                             -- persistent refusal pressed every tick wrote about 60 act lines a second), a judgment
K.REFUSE_WAIT_MS = K.SWING_MS / 2   -- the wait, half the swing's own bound (750 ms), the facing still written
K.REFUSE_END = 15            -- refused presses in a row that end the melee lost, why refused (three runs), a judgment
K.MELEE_CROWD_N = 3          -- standing zombies within K.MELEE_CROWD_R (the target counted) that end the meet handback
                             -- crowd: three attackers within 0.9 tiles zero the defence and drag the character down
                             -- (#4290, at the fixtures' sandbox Strength); with two the nearest is pressed (#4688), Task 15a
K.MELEE_CROWD_R = 0.9        -- tiles: the crowd radius, #4290's (fix 1, review-t15a M4: K.STAND_R's 0.6 under-read it)
K.MELEE_REPIN_SLACK = 0.1    -- tiles a crowd's other zombie must be nearer than the target to be re-pinned (a tolerance
                             -- of the read, so two at one distance do not flap)
K.KNOCK_BASE = 35            -- the shove's critical chance, calculateCritChance (#4373): the base,
K.KNOCK_LEVEL = 5            -- ... less this per endurance and per heavy-load moodle level,
K.KNOCK_PANIC = 1.3          -- ... less this per panic moodle level,
K.KNOCK_STRENGTH = 2         -- ... plus this per Strength level, out of Rand.Next(100)

local NUMS = { "reach", "shoveR", "releaseR", "faceR", "pressAngle", "pressLo", "floorR", "handbackR", "stall" }
local NONNEG = { "reach", "shoveR", "faceR", "pressLo", "floorR", "handbackR" }
local BOOLS = { "floorSwing", "headAim" }
local MEMBERS = { "setForceAim", "nullifyAiming", "setTargetAndCurrentDirection", "DoAttack", "setDoShove",
                  "setAutoWalk", "setAutoWalkDirection" }
local COUNT = { swing = "swings", shove = "shoves", stomp = "stomps", floor = "floors" }
local DEG = 180 / math.pi

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

-- the planar distance from the player to z: DistToProper (one call, T91.3), else the four position reads; nil unreadable
local function distTo(p, z)
    local ok, d = PZA.call(p, "DistToProper", z)
    if ok and type(d) == "number" then return d end
    return (K.zombieDist(p, z))
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

-- the engine's press-time reach (#4591, #4681): the unmargined getMaxRange x getRangeMod of the held weapon, read once
-- (K.REACH_FALLBACK when unread, 0 with nothing held), + K.MELEE_LUNGE_BONUS against a target lunging (its
-- getRealState a lunge) from under K.MELEE_LUNGE_R
local function engineReach(p, st, d)
    if st.rawReach == nil then
        local w = weaponOf(p)
        if w == nil then return 0 end
        local okM, mx = PZA.call(w, "getMaxRange", p)
        local okR, rm = PZA.call(w, "getRangeMod", p)
        st.rawReach = K.REACH_FALLBACK
        if okM and okR and type(mx) == "number" and type(rm) == "number" then st.rawReach = mx * rm end
    end
    if d < K.MELEE_LUNGE_R then
        local ok, state = PZA.call(st.z, "getRealState")
        if ok and type(state) == "string" and string.find(state, "lunge") ~= nil then
            return st.rawReach + K.MELEE_LUNGE_BONUS
        end
    end
    return st.rawReach
end

-- the held weapon's MinRange, read once (#4372: a standing target nearer makes the press a shove), else K.STAND_R
local function minRangeOf(p, st)
    if st.minR == nil then
        local ok, r = PZA.call(weaponOf(p), "getMinRange")
        if ok and type(r) == "number" then st.minR = r else st.minR = K.STAND_R end
    end
    return st.minR
end

local function combatSpeed(p)
    local ok, cs = PZA.call(p, "getCombatSpeed")
    if not ok or type(cs) ~= "number" then return 1 end
    return math.max(K.MELEE_CS_MIN, math.min(K.MELEE_CS_MAX, cs))
end

-- every member a step may call, and Vector2's constructor, present (index-checked: not loaded otherwise)
local function meleeLoaded(p)
    if Vector2 == nil or Vector2.new == nil then return false end
    for i = 1, #MEMBERS do
        if not PZA.field(p, MEMBERS[i]) then return false end
    end
    local pm = K.FACING.MODES[K.PRESS_FACING] or {}   -- Plan 32 Task 4: the press mode's members
    for i = 1, #pm do
        if not PZA.field(p, pm[i]) then return false end
    end
    return true
end

-- the look's angle off the bearing from (px, py) to (tx, ty) in degrees (getLookAngleRadians, #4591, #4688: radians in
-- Vector2.getDirection's atan2(y, x) convention, Sense's header), or nil when unread
local function lookOff(p, px, py, tx, ty)
    local ok, a = PZA.call(p, "getLookAngleRadians")
    if not ok or type(a) ~= "number" then return nil end
    local off = a - math.atan2(ty - py, tx - px)
    while off > math.pi do off = off - 2 * math.pi end
    while off < -math.pi do off = off + 2 * math.pi end
    return math.abs(off) * DEG
end

-- the look on the bearing: within pressAngle; an unreadable look reads on once the target has been faced unaimed
-- K.FACE_TICKS ticks before this one (the turn on the update after the face, #4590, as before PZA/1.10)
local function lookOn(st, off)
    if off ~= nil then return off <= st.pressAngle end
    return st.faced > K.FACE_TICKS
end

-- the facing snapped onto the target (Plan 32 Task 4: K.FACING.snap toward the tick's positions, st.px .. st.zy)
local function face(p, st)
    K.FACING.snap(p, st, K.FACING.bearing(st.px, st.py, st.zx, st.zy))
    st.faced = st.faced + 1
end

-- the facing snapped onto (x, y), the fallen target's head
local function faceAt(p, st, x, y)
    K.FACING.snap(p, st, K.FACING.bearing(st.px, st.py, x, y))
    st.faced = st.faced + 1
end

-- the facing written while no step of the meet or the finish writes it (a press in flight, the hit step; fix 1, F2):
-- at the press's aim point for a floor press with headAim, else at the target
local function faceOn(p, st)
    local s = st.strike
    if s ~= nil and s.ax ~= nil then
        faceAt(p, st, s.ax, s.ay)
    else
        face(p, st)
    end
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
    st.loose = false
    K.FACING.hold(p, st, K.FACING.bearing(st.px, st.py, st.zx, st.zy))
end

-- the stance released and the run latches off once, inside faceR and on the floor (the facing is the Lua's)
local function loosen(p, st)
    if ST.held then release(p) end
    if st.loose then return end
    MO.want("walk")
    PZA.call(p, "setForceRun", false)
    PZA.call(p, "setForceSprint", false)
    st.loose, st.faced = true, 0
end

local function stopWalk(p, st)
    if st.walk == nil then return end
    PZA.call(p, "setAutoWalk", false)
    st.walk, st.wx, st.wy = nil, nil, nil
end

-- the auto-walk along world (vx, vy) at a walk, in input space (K.inputVector); set again only for another kind of walk
-- or a heading turned past MELEE_TURN_DOT, so a straight walk makes no Vector2 after its first tick
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

-- a walk of kind toward (tx, ty), dd away, bounded once a melee (fix 1, F6: the walking ticks of every walking step
-- summed, so a closing read flickering between the walk and the stand cannot run the melee forever): lost (out of
-- reach) once K.STOMP_APPROACH_MS of walking has gained no MELEE_WALK_GAIN on the best distance since the last gain or
-- press; else kind
local function walkToward(p, st, kind, px, py, tx, ty, dd, now)
    walkAlong(p, st, kind, tx - px, ty - py)
    if st.walkBest == nil or dd < st.walkBest - K.MELEE_WALK_GAIN then
        st.walkBest, st.walkMs = dd, 0
    else
        st.walkMs = st.walkMs + st.dtS * 1000
    end
    if st.walkMs >= K.STOMP_APPROACH_MS then return "done", "lost", { why = "out of reach" } end
    return kind
end

-- a moodle's level, else `unread` when the moodle type or its level cannot be read: 0 when omitted (the spent read's);
-- knock_p passes false, its strict read (fix 1, review-t15a M5: one function, not two)
local function moodleLevel(mo, name, unread)
    if unread == nil then unread = 0 end
    local t = MoodleType ~= nil and MoodleType[name] or nil
    if t == nil then return unread end
    local ok, l = PZA.call(mo, "getMoodleLevel", t)
    if ok and type(l) == "number" then return l end
    return unread
end

-- the shove's knock-down chance in [0, 1] (#4373, calculateCritChance's shove at a zombie): KNOCK_BASE - KNOCK_LEVEL
-- per endurance and heavy-load level - KNOCK_PANIC per panic level + KNOCK_STRENGTH x Strength, truncated toward zero
-- as its f2i, over the roll's 100; nil when any input is unread. Read at the press (Task 15a: a reading for the leaf)
local function knockP(p)
    local ok, mo = PZA.call(p, "getMoodles")
    local perk = Perks ~= nil and Perks.Strength or nil
    if not ok or mo == nil or perk == nil then return nil end
    local okS, s = PZA.call(p, "getPerkLevel", perk)
    local e, h, pa = moodleLevel(mo, "ENDURANCE", false), moodleLevel(mo, "HEAVY_LOAD", false),
                     moodleLevel(mo, "PANIC", false)
    if not okS or type(s) ~= "number" or not e or not h or not pa then return nil end
    local c = K.KNOCK_BASE - K.KNOCK_LEVEL * (e + h) - K.KNOCK_PANIC * pa + K.KNOCK_STRENGTH * s
    if c >= 0 then c = math.floor(c) else c = math.ceil(c) end
    return math.max(0, math.min(100, c)) / 100
end

-- spent: mode shove, nothing held, the arms' pain (the last frame's body.armPain, Sense's) over MELEE_SPENT_PAIN or the
-- ENDURANCE or TIRED moodle at MELEE_SPENT_MOODLE or more; read once a frame (once a K.PROGRESS_MS with no frame)
local function spentOf(p, st, now)
    if st.mode == "shove" or st.unarmed then
        st.spent = true
        return true
    end
    local S = PZA.sense
    local f = S ~= nil and S.last or nil
    if st.spentAt ~= nil and (f ~= nil and f == st.spentFrame or f == nil and now - st.spentAt < K.PROGRESS_MS) then
        return st.spent
    end
    st.spentFrame, st.spentAt = f, now
    local pain = f ~= nil and type(f.body) == "table" and f.body.armPain or nil
    local spent = type(pain) == "number" and pain > K.MELEE_SPENT_PAIN
    if not spent then
        local ok, mo = PZA.call(p, "getMoodles")
        if ok and mo ~= nil then
            spent = moodleLevel(mo, "ENDURANCE") >= K.MELEE_SPENT_MOODLE or moodleLevel(mo, "TIRED") >= K.MELEE_SPENT_MOODLE
        end
    end
    st.spent = spent == true
    return st.spent
end

-- the target's position kept for its closing speed (the last MELEE_SAMPLES + 1 ticks)
local function sample(st, now, zx, zy)
    local h = st.hist
    h[#h + 1] = { t = now, x = zx, y = zy }
    if #h > K.MELEE_SAMPLES + 1 then table.remove(h, 1) end
end

-- the target's closing speed toward the player in tiles a second over the kept ticks (its displacement along the unit
-- vector from it to the player), nil with fewer than two
local function closingOf(st, px, py, zx, zy, d)
    local h = st.hist
    if #h < 2 or d <= 0 then return nil end
    local a = h[1]
    local dt = (h[#h].t - a.t) / 1000
    if dt <= 0 then return nil end
    return ((zx - a.x) * (px - zx) + (zy - a.y) * (py - zy)) / d / dt
end

-- the other standing zombies within r of the player, nearest first ({id, d, o} each), or nil when there is none (no
-- table made on the common tick). The candidates are the last frame's records (a Lua table, Sense's S.last) within
-- r + MELEE_CROWD_SLACK, each read live (dead, on the floor, its distance) through the frame's own object map
-- (S.zobj); no frame, no candidate
local function standingNear(p, st, r)
    local S = PZA.sense
    local f = S ~= nil and S.last or nil
    local objs = S ~= nil and S.zobj or nil
    local recs = f ~= nil and f.zombies or nil
    if recs == nil or objs == nil then return nil end
    local out = nil
    for i = 1, #recs do
        local rec = recs[i]
        if rec.id ~= st.id and type(rec.dist) == "number" and rec.dist < r + K.MELEE_CROWD_SLACK then
            local o = objs[rec.id]
            if o ~= nil and not K.zombieDead(o) and not K.onFloor(o) then
                local d = distTo(p, o)
                if d ~= nil and d < r then
                    out = out or {}
                    out[#out + 1] = { id = rec.id, d = d, o = o }
                end
            end
        end
    end
    if out ~= nil and #out > 1 then table.sort(out, function(a, b) return a.d < b.d end) end
    return out
end

-- a press of kind at the target (the shove flag first for a shove or a stomp; a swing or a floor swing needs a weapon),
-- held while an attack still runs (isAttackStarted: the engine drops a press then, #4292); the step, or failed, reason
local function press(p, st, kind, d, pred, off, waitStep, dmin, ax, ay)
    stopWalk(p, st)
    if st.refuseUntil ~= nil and PZA.now() < st.refuseUntil then return "refused" end   -- the residual: the wait
    if (kind == "swing" or kind == "floor") and weaponOf(p) == nil then return "failed", "no weapon" end
    local _, busy = PZA.call(p, "isAttackStarted")
    if busy == true then return waitStep end
    local hp = healthOf(st.z)
    local kp = nil
    if kind == "shove" then kp = knockP(p) end   -- Task 15a: the roll's chance, read before the press rolls it
    if kind == "shove" or kind == "stomp" then pcall(PZA.call, p, "setDoShove", true) end
    local F = K.FACING
    local b = F.bearing(st.px, st.py, ax or st.zx, ay or st.zy)
    local bodyOff = F.body_off(p, b or st.faceB)   -- Plan 32 Task 4: the body at the press, before the press's snap
    st.strike = { kind = kind, at = PZA.now(), started = false, ended = false, refused = false, ticks = 0, hp0 = hp,
                  dPress = d, dPred = pred, dMin = dmin or d, off = off, cut = "", ax = ax, ay = ay, knockP = kp,
                  bodyOff = bodyOff, facing = K.PRESS_FACING, headTicks = st.headTicks }
    st.headTicks = 0   -- Plan 33 Task 1: a press restarts the head step's count
    F.press_enter(p, st, b)
    pcall(PZA.call, p, "DoAttack", 0)
    st[COUNT[kind]] = st[COUNT[kind]] + 1
    st.walkBest, st.walkMs = nil, 0   -- a press restarts the walk's bound (fix 1, F6)
    return kind
end

-- the press in flight: false until a tick after its end (isAttackStarted read true and then false, or K.SWING_MS)
local function strikeOver(p, st)
    local s = st.strike
    if s.ended then return true end
    s.ticks = s.ticks + 1
    local _, started = PZA.call(p, "isAttackStarted")
    if started == true then
        if not s.started and st.refusals > 0 then   -- the residual: an accepted press ends a refusal run, its count kept
            st.refuseRun, st.refusals, st.refuseUntil = st.refusals, 0, nil
        end
        s.started = true
    elseif s.started then
        s.ended = true
        return false
    elseif s.ticks == 1 then
        s.ended, s.refused = true, true   -- fix 1, F3: pressedAttack sets attackStarted at the press; false now, refused
        if s.cut == "" then s.cut = "refused" end
        return true
    end
    if PZA.now() - s.at >= K.SWING_MS then s.ended = true end
    return false
end

-- the press's leaf with its result read now (cut its cut_by)
local function leafOf(st, s, cut)
    local knocked = K.knockedDown(st.z)
    return { d_press = s.dPress, d_collide_pred = s.dPred, d_min = s.dMin, look_off = s.off, hp0 = s.hp0,
             hp1 = healthOf(st.z), knock = knocked, cut_by = cut, knock_p = s.knockP, body_off = s.bodyOff,
             facing = s.facing, head_ticks = s.headTicks }, knocked
end

-- the ended press's result: its leaf, a swing's or a shove's knock-down (counted, the knock wait armed), the shove flag
-- cleared after a shove or a stomp, and the no-progress run (a swing, a floor swing or a stomp that neither lowered the
-- health nor knocked down extends it; any other restarts it; a shove leaves it)
local function strikeResult(p, st)
    local s = st.strike
    st.strike = nil
    K.FACING.press_exit(p, st)
    if s.kind == "shove" or s.kind == "stomp" then K.releaseShove(p) end
    local leaf, knocked = leafOf(st, s, s.cut)
    if s.refused then   -- the residual: one leaf a run (its first), the wait after each K.REFUSE_MAX
        st.refusals = st.refusals + 1
        if st.refusals == 1 then st.leaf = leaf end
        if st.refusals % K.REFUSE_MAX == 0 then st.refuseUntil = PZA.now() + K.REFUSE_WAIT_MS end
    else
        st.leaf = leaf
    end
    if knocked and (s.kind == "swing" or s.kind == "shove") then
        st.knockdowns = st.knockdowns + 1
        st.knocked = true
    end
    if not s.refused then   -- Task 15a: a shove that knocked nothing down asks the spent meet's swing next
        if s.kind == "shove" then st.shoveFailed = not knocked elseif s.kind == "swing" then st.shoveFailed = false end
    end
    if s.kind ~= "shove" and not s.refused then
        if not knocked and s.hp0 ~= nil and leaf.hp1 ~= nil and leaf.hp1 >= s.hp0 then
            st.nothing = st.nothing + 1
        else
            st.nothing = 0
        end
    end
end

-- the head step held with no press (Plan 33 Task 1, F18's a71: 14.553 s of `head` on a target under the feet): counted
-- in st.headTicks (reset by every press); at K.HEAD_MAX_TICKS done handback, why head_stall, with head_ticks and the
-- standing zombies within K.MELEE_CROWD_R (the crowd handback's form: n, and with one or more the nearest's id and d
-- and the distances ds), so the decider decides
local function headWait(p, st)
    if st.headTicks >= K.HEAD_MAX_TICKS then
        local near = standingNear(p, st, K.MELEE_CROWD_R)
        local out = { why = "head_stall", head_ticks = st.headTicks, n = 0 }
        if near ~= nil then
            local ds = {}
            for i = 1, #near do ds[i] = near[i].d end
            out.id, out.d, out.n, out.ds = near[1].id, near[1].d, #near, ds
        end
        return "done", "handback", out
    end
    st.headTicks = st.headTicks + 1
    return "head"
end

-- 4: the finish at a fallen target's head
local function finish(p, st, d, px, py, now)
    local near = standingNear(p, st, st.handbackR)
    if near ~= nil then return "done", "handback", { why = "standing", id = near[1].id, d = near[1].d } end
    local S = PZA.sense
    local hx, hy = nil, nil
    if st.headAim and S ~= nil and S.headOf ~= nil then hx, hy = S.headOf(st.z) end
    local aimed = hx ~= nil and hy ~= nil
    if not aimed then hx, hy = posOf(st.z) end
    local ex, ey = hx - px, hy - py
    local dh = math.sqrt(ex * ex + ey * ey)
    loosen(p, st)
    if aimed then faceAt(p, st, hx, hy) else face(p, st) end
    local ax, ay = nil, nil
    if aimed then ax, ay = hx, hy end
    local dmin = math.min(d, dh)
    local floor = st.floorSwing and not spentOf(p, st, now) and dh <= st.floorR and d <= reachOf(p, st)
                  and weaponOf(p) ~= nil
    if floor or dh <= K.MELEE_STOMP_R then
        stopWalk(p, st)
        local off = lookOff(p, px, py, hx, hy)
        if dh >= K.HEAD_LOOK_FLOOR and not lookOn(st, off) then return headWait(p, st) end   -- Plan 33: the floor
        local step, why = press(p, st, floor and "floor" or "stomp", dh, dh, off, "head", dmin, ax, ay)
        if step == "head" then return headWait(p, st) end   -- an attack still running: a head tick with no press
        return step, why
    end
    return walkToward(p, st, "stomp_walk", px, py, hx, hy, dh, now)
end

-- the meet's press at a standing target, the step (or failed, reason) it takes, else nil: inside the weapon's MinRange
-- the shove (the protective press: the engine shoves there, #4372), else the swing once the look is on, the predicted
-- distance at the collision within [pressLo, at], the swing state's entry beyond MinRange and the raw distance within
-- the engine's own reach
local function swingPress(p, st, d, v, off, on, at)
    local minR = minRangeOf(p, st)
    local dmin = d   -- the shove test's distance: a standing target's readable point is its position (F5)
    if dmin <= minR then
        if on then return press(p, st, "shove", d, d, off, "face", dmin) end
        stopWalk(p, st)
        return "face"
    end
    if on then
        local vv = v or 0
        local pred = d - vv * (st.dtS + K.MELEE_HIT_FRAC / combatSpeed(p))
        if pred >= st.pressLo and pred <= at and dmin - vv * st.dtS > minR and d <= engineReach(p, st, d) then
            return press(p, st, "swing", d, pred, off, "face", dmin)
        end
    end
    return nil
end

-- 6: the meet at a standing target
local function meet(p, st, d, px, py, zx, zy, now)
    if d <= st.faceR then
        st.near = true
    elseif d > st.faceR + K.MELEE_FACE_SLACK then
        st.near = false
    end
    local v = closingOf(st, px, py, zx, zy, d)
    local closing
    if v ~= nil then closing = v > K.MELEE_CLOSING_V else closing = targetOf(st) == p end
    local spent = spentOf(p, st, now)
    local at = spent and st.shoveR or reachOf(p, st)
    if not st.near then
        holdStance(p, st)
        if not closing then return walkToward(p, st, "close", px, py, zx, zy, d, now) end
        stopWalk(p, st)
        return "stand"
    end
    loosen(p, st)
    face(p, st)
    local off = lookOff(p, px, py, zx, zy)
    local on = lookOn(st, off)
    local swingNext = spent and st.shoveFailed and weaponOf(p) ~= nil   -- Task 15a: never a loop of shoves
    if spent and not swingNext then
        if d <= st.shoveR then
            if on then return press(p, st, "shove", d, d, off, "face") end
            stopWalk(p, st)
            return "face"
        end
    else
        if swingNext then at = reachOf(p, st) end
        local step, why = swingPress(p, st, d, v, off, on, at)
        if step ~= nil then return step, why end
    end
    if not closing and d > at then return walkToward(p, st, "close", px, py, zx, zy, d, now) end
    stopWalk(p, st)
    return "face"
end

-- the target re-pinned to crowd entry c (Task 15a: the nearer of two standing is pressed): the reflex's per-target
-- reads restarted (the closing history, the stall, the knock wait, the walk bound, the health the span reads, the
-- least distance), the facing turned to it on this tick
local function repin(p, st, c)
    stopWalk(p, st)
    st.z, st.id, st.repins = c.o, c.id, st.repins + 1
    st.hist, st.nothing, st.knocked, st.shoveFailed = {}, 0, false, false
    st.walkBest, st.walkMs, st.dMin, st.hp0 = nil, 0, c.d, healthOf(c.o)
    st.zx, st.zy = posOf(c.o)
    face(p, st)
    return "repin"
end

-- 3, the crowd (the header's step 3): crowd the other standing zombies within K.MELEE_CROWD_R, nearest first; d the target's
-- distance, fallen whether it lies. K.MELEE_CROWD_N standing (the target counted while it stands): done handback
-- crowd {id, d of the nearest other, n, ds}; else a standing target farther than the nearest other by more than
-- K.MELEE_REPIN_SLACK re-pinned to it; else nil (the meet or the finish goes on)
local function crowdOf(p, st, crowd, d, fallen)
    local n = #crowd
    if not fallen then n = n + 1 end
    if n >= K.MELEE_CROWD_N then
        local ds = {}
        if not fallen then ds[1] = d end
        for i = 1, #crowd do ds[#ds + 1] = crowd[i].d end
        table.sort(ds)
        return "done", "handback", { why = "crowd", id = crowd[1].id, d = crowd[1].d, n = n, ds = ds }
    end
    if not fallen and crowd[1].d < d - K.MELEE_REPIN_SLACK then return repin(p, st, crowd[1]) end
    return nil
end

-- the reflexes in order, first match wins: the step, or "failed", reason[, result], or "done", end, extra
local function reflex(p, st, d, px, py, zx, zy, now)
    local z = st.z
    if hitReaction(p) then
        if not st.inHit then st.hits = st.hits + 1 end
        st.inHit = true
        if st.strike ~= nil then
            if not st.strike.ended and st.strike.cut == "" then st.strike.cut = "hit" end
            strikeOver(p, st)
        end
        stopWalk(p, st)
        faceOn(p, st)
        return "hit"
    end
    st.inHit = false
    if st.strike ~= nil then
        if not strikeOver(p, st) then
            faceOn(p, st)
            return st.strike.kind
        end
        strikeResult(p, st)
        if st.nothing >= st.stall then return "done", "lost", { why = "no progress" } end
        if st.refusals >= K.REFUSE_END then return "done", "lost", { why = "refused" } end
    end
    if d > st.releaseR then return "done", "lost", { why = "out of range" } end
    local crowd = standingNear(p, st, K.MELEE_CROWD_R)
    local fallen = K.onFloor(z)
    if crowd ~= nil then
        local step, how, res = crowdOf(p, st, crowd, d, fallen)
        if step ~= nil then return step, how, res end
    end
    if fallen then
        st.knocked = false
        return finish(p, st, d, px, py, now)
    end
    if st.knocked or d <= st.shoveR or d <= reachOf(p, st) then
        if K.knockedDown(z) then
            stopWalk(p, st)
            if st.near then
                loosen(p, st)
                face(p, st)
            else
                holdStance(p, st)
            end
            return "knock_wait"
        end
        st.knocked = false
    end
    return meet(p, st, d, px, py, zx, zy, now)
end

local function counts(st, out)
    out.swings, out.shoves, out.stomps, out.floors = st.swings, st.shoves, st.stomps, st.floors
    out.knockdowns, out.hits = st.knockdowns, st.hits
    if st.repins > 0 then out.target, out.repins = st.id, st.repins end   -- Task 15a: the zombie now pressed
    return out
end

-- the refusal run's count a line carries (the residual): a run just ended (its count, once), else the running run's
-- count on its first refusal's leaf line or on an end line; nil otherwise
local function refusalsOf(st, ending)
    local n = st.refuseRun
    st.refuseRun = nil
    if n == nil and st.refusals > 0 and (ending or st.leaf ~= nil) then n = st.refusals end
    return n
end

-- the progress result, the pending press leaf carried once
local function progressResult(st, d)
    local out = counts(st, { step = st.step, d = d, hp = healthOf(st.z), spent = st.spent == true,
                             refusals = refusalsOf(st, false), press = st.leaf })
    st.leaf = nil
    return out
end

-- the done result; the stance released first, then the shove flag
local function doneResult(p, st, how, extra)
    if ST.held then release(p) end
    K.releaseShove(p)
    extra = extra or {}
    local out = counts(st, { ["end"] = how, kill = how == "kill", why = extra.why, id = extra.id, d = extra.d,
                             n = extra.n, ds = extra.ds, head_ticks = extra.head_ticks, hp0 = st.hp0, hp1 = healthOf(st.z), dMin = st.dMin,
                             steps = st.steps, refusals = refusalsOf(st, true), press = st.leaf })
    st.leaf = nil
    return out
end

-- a supersede by a melee of the same target (a decider's re-send) or by an aim keeps the stance
local function keptOnResend(st, reason)
    if reason ~= "superseded" then return false end
    if K.starting == "aim" then return true end
    local c = K.startingCmd
    return K.starting == "melee" and type(c) == "table" and type(c.args) == "table"
           and (c.args.targetId == st.id or c.args.targetId == st.argId)   -- Task 15a: the sent or re-pinned target
end

K.types.melee = {
    check = function(args, p)
        local id, mode, fs = args.targetId, args.mode, args.floorSwing
        if type(id) ~= "number" or type(mode) ~= "string" or PZA.schema.meleeModes[mode] ~= true then
            return false, "bad args"                 -- the schema's meleeMode enum (PZA.schema.meleeModes)
        end
        for i = 1, #NUMS do
            if type(args[NUMS[i]]) ~= "number" then return false, "bad args" end
        end
        for i = 1, #NONNEG do
            if args[NONNEG[i]] < 0 then return false, "bad args" end
        end
        if args.releaseR <= 0 or args.pressAngle <= 0 or args.pressAngle > 180 or args.stall < 1 then
            return false, "bad args"
        end
        for i = 1, #BOOLS do
            local b = args[BOOLS[i]]
            if b ~= nil and type(b) ~= "boolean" then return false, "bad args" end
        end
        if fs == nil then fs = false end
        local z = K.zombieById(p, id)
        if z == nil or K.zombieDead(z) then return false, "no target" end
        local d = distTo(p, z)
        if d == nil then return false, "no target" end
        if d > args.releaseR then return false, "too far" end
        local unarmed = weaponOf(p) == nil
        if mode == "strike" and unarmed then return false, "no weapon" end
        return true, "", { id = id, argId = id, repins = 0, shoveFailed = false, z = z, mode = mode, reach = args.reach,
                           shoveR = args.shoveR,
                           releaseR = args.releaseR, faceR = args.faceR, pressAngle = args.pressAngle,
                           pressLo = args.pressLo, floorR = args.floorR, handbackR = args.handbackR, stall = args.stall,
                           floorSwing = fs, headAim = args.headAim == true, unarmed = unarmed, startMs = nil, step = nil, lastP = 0, lastNow = nil,
                           dtS = K.MELEE_UPDATE_S, dMin = nil, hp0 = nil, hist = {}, near = false, loose = false,
                           faced = 0, swings = 0, shoves = 0, stomps = 0, floors = 0, knockdowns = 0, hits = 0,
                           nothing = 0, steps = {}, strike = nil, leaf = nil, knocked = false, inHit = false,
                           walk = nil, wx = nil, wy = nil, walkBest = nil, walkMs = 0, weaponReach = nil, minR = nil,
                           rawReach = nil, refusals = 0, refuseRun = nil, refuseUntil = nil,
                           spent = false, spentFrame = nil, spentAt = nil, px = nil, py = nil, zx = nil, zy = nil,
                           faceB = nil, pf = nil, headTicks = 0 }
    end,
    tick = function(p, st)
        if isDead(p) then return "failed", "dead" end
        if K.zombieDead(st.z) then
            if st.strike ~= nil then strikeResult(p, st) end
            return "done", doneResult(p, st, "kill")
        end
        local now = PZA.now()
        if st.startMs == nil then
            if not meleeLoaded(p) then return "failed", "not loaded" end
            st.startMs = now
            st.hp0 = healthOf(st.z)
            MO.want("walk")
        end
        local px, py = posOf(p)
        local zx, zy = posOf(st.z)
        if px == nil or py == nil or zx == nil or zy == nil then return "failed", "not loaded" end
        local ex, ey = zx - px, zy - py
        local d = math.sqrt(ex * ex + ey * ey)
        if st.lastNow ~= nil and now > st.lastNow then st.dtS = (now - st.lastNow) / 1000 end
        st.lastNow = now
        sample(st, now, zx, zy)
        st.px, st.py, st.zx, st.zy = px, py, zx, zy   -- the facing's bearing (K.FACING) reads this tick's positions
        if st.dMin == nil or d < st.dMin then st.dMin = d end
        local step, why, res = reflex(p, st, d, px, py, zx, zy, now)
        if step == "failed" then return "failed", why, res end
        if step == "done" then return "done", doneResult(p, st, why, res) end
        st.steps[step] = (st.steps[step] or 0) + 1
        if step ~= st.step or st.leaf ~= nil or st.refuseRun ~= nil or now - st.lastP >= K.PROGRESS_MS then
            st.step, st.lastP = step, now
            return "progress", progressResult(st, d)
        end
        return nil
    end,
    -- every end but done: the stance released unless a melee of the same target or an aim supersedes it, then the shove
    -- flag; the failed line's result the counts, with a press in flight read as its leaf cut by the end's reason
    stop = function(p, st, reason)
        K.FACING.press_exit(p, st)
        if ST.held and not keptOnResend(st, reason) then release(p) end
        K.releaseShove(p)
        local leaf = st.leaf
        if st.strike ~= nil then leaf = leafOf(st, st.strike, reason or "") end
        st.leaf, st.strike = nil, nil
        return counts(st, { refusals = refusalsOf(st, true), press = leaf })
    end,
}

-- ---- the facing (Plan 32 Task 4) ---------------------------------------------------------------------------------
-- The ruled mechanism (the facing trials' Task 3 ruling over three probe boots, PZAgent_FacingProbe.lua's modes; the
-- jar read facing-jar-research.md claims 7, 13, 14, 17, 19): the aimed player's forward direction is written toward
-- the mouse on every update after OnPlayerUpdate, so no Lua facing call survives the stance but the one that sets the
-- body angle itself, setTargetAndCurrentDirection (claim 14: snap_aimed held the body within 3 degrees standing and
-- back-pedalling, the look 18 to 47 degrees toward the mouse; unaimed_snap held body and look at 0.0 standing and 6.8
-- back-pedalling; block_aim, setForceAim(false) with setBlockMovement(true) and setIsAiming(true), body and look 0.0
-- with isAiming true, movement blocked). So the held stance snaps the body every tick and keeps the aim (hold); a press
-- releases the force-aim for its ticks, snaps body and look and re-asserts the aim at its result (press_enter,
-- press_exit, the mode K.PRESS_FACING); block_aim is the switch's other mode. Called from the melee's facing sites
-- above and from PZAgent_Stance.lua's faceOf (the aim leg), each at the tick it writes, through K.FACING (resolved at
-- the call: this table is made when the file loads, before any tick). Every flag a press mode sets is restored by
-- press_exit, and every setter either makes (the snap aside, the facing's every-tick write) is under its own pcall (a
-- raise counted in K.errors, the next call still made: MO.off's form), once; press_exit does nothing without a
-- press_enter before it.
K.PRESS_FACING = "unaimed_snap"   -- the press mode: unaimed_snap (the ruling), or block_aim (its switchable alternative)
K.FACING_MIN_D = 0.01             -- tiles: a target nearer holds the last bearing (a zero vector raises, claim 16)

local FACING = {}
K.FACING = FACING
FACING.MODES = { unaimed_snap = { "setForceAim", "setTargetAndCurrentDirection" },
                 block_aim = { "setForceAim", "setBlockMovement", "setIsAiming", "nullifyAiming",
                               "setTargetAndCurrentDirection" } }

-- one setter call under its own pcall, a raise counted (S-15), as the press's own DoAttack and setDoShove
local function guarded(fn, ...)
    local ok, err = pcall(fn, ...)
    if not ok then
        K.errors = (K.errors or 0) + 1
        K.lastError = tostring(err)
    end
end

-- the bearing in radians from (px, py) to (tx, ty) (atan2(y, x), Vector2.getDirection's convention), nil when a
-- position is unread or the target sits within K.FACING_MIN_D
function FACING.bearing(px, py, tx, ty)
    if px == nil or py == nil or tx == nil or ty == nil then return nil end
    local ex, ey = tx - px, ty - py
    if ex * ex + ey * ey < K.FACING_MIN_D * K.FACING_MIN_D then return nil end
    return math.atan2(ey, ex)
end

-- the snap: body and facing set onto b at once (b nil: the last bearing st.faceB, none written without one); whether
-- it wrote
function FACING.snap(p, st, b)
    if b == nil then b = st.faceB end
    if b == nil then return false end
    st.faceB = b
    PZA.call(p, "setTargetAndCurrentDirection", math.cos(b), math.sin(b))
    return true
end

-- the held stance's write: the snap, the aim posture kept (no flag touched)
function FACING.hold(p, st, b)
    return FACING.snap(p, st, b)
end

-- the press's facing on: the stance's wants recorded (st.pf), the force-aim released for the press's ticks (unaimed:
-- K.stance.held and PZA.motor.wantAim false, setForceAim(false) once), block_aim's posture set, and the snap onto b;
-- the mode
function FACING.press_enter(p, st, b)
    FACING.press_exit(p, st)
    local mode = K.PRESS_FACING
    st.pf = { mode = mode, held = K.stance.held, wantAim = PZA.motor.wantAim }
    K.stance.held = false
    PZA.motor.wantAim = false
    guarded(PZA.call, p, "setForceAim", false)
    if mode == "block_aim" then
        guarded(PZA.call, p, "setBlockMovement", true)
        guarded(PZA.call, p, "setIsAiming", true)
    end
    FACING.snap(p, st, b)
    return mode
end

-- the press's facing off, once: block_aim's posture released (setBlockMovement(false), nullifyAiming), and the stance
-- re-asserted when it was wanted at the press (K.stance.held as it was, PZA.motor.wantAim true, setForceAim(true): the
-- Motor re-asserts it every frame from here)
function FACING.press_exit(p, st)
    local s = st.pf
    if s == nil then return end
    st.pf = nil
    if s.mode == "block_aim" then
        guarded(PZA.call, p, "setBlockMovement", false)
        guarded(PZA.call, p, "nullifyAiming")
    end
    if s.wantAim then
        K.stance.held = s.held
        PZA.motor.wantAim = true
        guarded(PZA.call, p, "setForceAim", true)
    end
end

-- the body angle (getAnimAngleRadians) off the bearing b, in degrees in [0, 180]; nil when either is unread
function FACING.body_off(p, b)
    if b == nil then return nil end
    local ok, a = PZA.call(p, "getAnimAngleRadians")
    if not ok or type(a) ~= "number" then return nil end
    local off = a - b
    while off > math.pi do off = off - 2 * math.pi end
    while off < -math.pi do off = off + 2 * math.pi end
    return math.abs(off) * DEG
end

-- ---- the finish's head step (Plan 33 Task 1) ----------------------------------------------------------------------
-- F18 (f_goals_18-20261108-235005, #4704): the finish a71 stomped its fallen target once and then held its head step
-- 14.553 s with no press, the character standing on it (d 0.0053): the bearing from the player to a target under the
-- feet is numerically unstable and the look gate (lookOn) never read on, while a group of three walked in. Two rules in
-- finish (the header's reflex 4): the head nearer than K.HEAD_LOOK_FLOOR is pressed with no look gate (the stomp lands
-- on the square under the character, the earlier stomp at 0.27 landed; the engine's attack never reads the aim, the
-- facing jar read's claim 19); and a head step held K.HEAD_MAX_TICKS ticks with no press (headWait, st.headTicks,
-- restarted by every press) ends done handback, why head_stall, {head_ticks, n[, id, d, ds]}: the standing zombies within
-- K.MELEE_CROWD_R, the crowd handback's form, so the decider decides. Every press leaf adds head_ticks, the head ticks
-- waited before it (0 for a press with no wait).
K.HEAD_LOOK_FLOOR = 0.15   -- tiles: a head nearer is pressed with no look gate (the target under the feet)
K.HEAD_MAX_TICKS = 20      -- head ticks with no press before the head_stall handback (the spec's 20, a judgment)

-- ---- the idle snap (Plan 33 Task 1) ------------------------------------------------------------------------------
-- F18's visual pass (shots 31, 33, 35, 36) saw the body turned away from the nearest zombie between presses while
-- every press read it squared: the snap ran only inside a melee's steps and the aim leg. FACING.idle(p), called once a
-- frame from the Motor's per-frame hold (PZAgent_Motor.lua) under K.IDLE_SNAP: while no skill runs (K.cur nil: a
-- melee, the aim leg, a steer, a walk or any other leg owns the body) and no run latch is wanted, the body is snapped
-- (setTargetAndCurrentDirection(cos b, sin b), FACING.snap) onto the nearest standing zombie within K.IDLE_SNAP_R, the
-- aim posture as it is (no setForceAim here: the Motor asserts the stance's). The candidates are the last frame's
-- records (Sense's S.last, its S.zobj) within K.IDLE_SNAP_R + K.MELEE_CROWD_SLACK by the frame's distance, each read
-- live: its position, and isDead and isOnFloor only for one nearer than the best so far. No frame, no candidate, a
-- zombie on the player's square (FACING.bearing nil): nothing; the snap member absent (index-checked on the first idle
-- frame): nothing and no read, ever.
-- Cost a frame idle near a standing zombie: the player's position (2), each candidate's (2) with isDead and isOnFloor
-- (2), and the snap (1); none with no candidate in the frame's records.
K.IDLE_SNAP = true         -- the switch
K.IDLE_SNAP_R = 2.5        -- tiles: the planner's KEEP_R (policies.py), a Lua constant of its own
local IDLE = { faceB = nil, ok = nil }   -- the snap's scratch state and the snap member's index check, made once

function FACING.idle(p)
    if K.cur ~= nil or MO.wantRun or MO.wantSprint then return false end
    if IDLE.ok == nil then IDLE.ok = PZA.field(p, "setTargetAndCurrentDirection") == true end
    if not IDLE.ok then return false end
    local S = PZA.sense
    local f = S ~= nil and S.last or nil
    local objs = S ~= nil and S.zobj or nil
    local recs = f ~= nil and f.zombies or nil
    if recs == nil or objs == nil then return false end
    local r = K.IDLE_SNAP_R
    local px, py, best, bx, by = nil, nil, nil, nil, nil
    local r2 = r * r
    for i = 1, #recs do
        local rec = recs[i]
        local o = type(rec.dist) == "number" and rec.dist < r + K.MELEE_CROWD_SLACK and objs[rec.id] or nil
        if o ~= nil then
            if px == nil then
                px, py = posOf(p)
                if px == nil or py == nil then return false end
            end
            local zx, zy = posOf(o)
            if zx ~= nil and zy ~= nil then
                local ex, ey = zx - px, zy - py
                local d2 = ex * ex + ey * ey
                if d2 < r2 and (best == nil or d2 < best) then
                    if not K.zombieDead(o) and not K.onFloor(o) then best, bx, by = d2, zx, zy end
                end
            end
        end
    end
    if best == nil then return false end
    local b = FACING.bearing(px, py, bx, by)
    if b == nil then return false end
    return FACING.snap(p, IDLE, b)
end
