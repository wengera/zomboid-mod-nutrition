-- PZAgent_StanceWork.lua — the footwork reflex (PZA/1.13, Plan 35 Task 1; the spec
-- `2026-11-10-plan-35-the-footwork-design.md` section 3.1, the cerebellum's second cut). The melee reflex
-- (PZAgent_StanceMelee.lua) owns one zombie to the kill at the client's tick rate; this file gives it footwork between
-- presses behind the melee's optional work arguments, so in contact one reflex owns the press, the facing and the step
-- together and no 2 Hz leg supersedes it. Loads after PZAgent_StanceMelee.lua (client files load by name,
-- case-insensitively, #0850: "pzagent_stancemelee" before "pzagent_stancework"), and registers into it as Plan 34 Task
-- 4b's K.meleeHitHandback did: the melee's hooks (the block at the end of PZAgent_StanceMelee.lua) call K.footwork,
-- K.workTick, K.workResult and K.workFloor only when st.work is set, which only this file's check sets. With no work
-- argument the melee runs as before, byte for byte (test_lua_footwork.py). Every Java member through PZA.call, every
-- vanilla constant index-checked; no goto, no integer format of a float, no # on a Java list.
--
-- melee {..., workR, crawlerR, bandLo, withdrawX, withdrawY, floorHealth, pile} (PZA/1.13): workR the standing zombies
--   read for the heading (3.5 tiles), crawlerR a crawler this near repels the heading hard, vetoes a probe point and is
--   the target with no standing zombie in reach (1.2), bandLo the gap under which the step back goes is the reach less
--   this (0.4), withdrawX and withdrawY the planner's bias (a vector, absent together), floorHealth the hand-back floor
--   (0 for none), pile true to meet three standing within K.MELEE_CROWD_R in the reflex. check (wrapped): any work field
--   given makes workR, crawlerR, bandLo and floorHealth numbers at or above 0, the withdraw pair numbers or absent
--   together, pile a boolean or absent (bad args otherwise); none given leaves st.work nil. A melee re-sent at the same
--   target (its sent or re-pinned id) while one with work runs keeps the footwork's state (the heading, its cadence, the
--   nearest's id, the clear count, the pile's step) and the closing history and takes the new work fields.
-- Each tick with work, after a press in flight and a hit reaction (the melee's rules 1 and 2) and the release read:
--   the tick (K.workTick, before the crowd): the floor hand-back (done handback, why floor: the body's health, the last
--   frame's body.health else getBodyDamage():getOverallBodyHealth(), at or under floorHealth when floorHealth is above
--   0; read under a hit reaction too); the gap (the nearest standing zombie: the target while it stands, else the
--   nearest of K.meleeCrowd's read within the larger of the reach, K.MELEE_CROWD_R and K.WORK_CONTACT_R), a change of
--   its id re-choosing the heading at once; contact (the tick's nearest standing inside K.WORK_CONTACT_R, counted when
--   no press is in flight at the tick's end); clear (done handback, why clear: K.WORK_CLEAR_TICKS ticks in a row with
--   the target a crawler beyond crawlerR, no standing zombie within releaseR and no other crawler within crawlerR); the
--   pile (pile true; fix 3: triggered by the engine's attackers count at 2 or more, or K.MELEE_CROWD_N standing
--   within K.WORK_PILE_R, the target counted while it stands; re-pinned to the nearest: the shove at it within shoveR,
--   its leaf's knock_p, skipped after two in a row at it that knocked nothing down; at its result the step `pile`
--   along the heading for K.WORK_STEP_TICKS ticks, ungated, the body snapped on the target; then the meet's next
--   press; again while the trigger holds; pileTick below). The crowd hand-back is kept for pile false.
--   the idle (K.footwork, where the meet would stand or face): a crawler within crawlerR with no standing zombie within
--   the reach is the target (the re-pin; finished as fallen, the finish's stomp; after it a standing zombie breaks the
--   stomp only within the reach); the gap under the reach less bandLo the step `work` along the heading (the stance's
--   force-aim held, the auto-walk in input space, the facing the meet's own snap this tick), `cornered` with no clear
--   heading (the walk stopped: the press is the defence); else the meet's own stand or face.
--   the heading (re-chosen every K.WORK_TICKS ticks, at once on a new nearest): the repulsion sum of the standing
--   zombies within workR (the frame's records not onFloor and not crawler, each position read live; the target's this
--   tick's) weighted 1 / d^2, of the crawlers within crawlerR x 2 (K.crawlersNear) weighted K.WORK_CRAWLER_W / d^2, and
--   K.WORK_WITHDRAW_W x the withdraw vector; turned by K.WORK_TURNS in order, the first clear one taken. A heading is
--   clear when at each K.WORK_PROBE distance along it the square is the player's own or readable, neither isSolid nor
--   isSolidTrans, not isBlockedTo from the player's square, with no IsoFlagType.HoppableW on the crossed x edge (the
--   eastern square's) nor HoppableN on the crossed y edge (the southern square's): the stance cannot climb (#4289); no
--   crawler lies within crawlerR of the point and no fallen zombie (the frame's onFloor records, the target fallen)
--   within K.WORK_FALLEN_R. Each square's verdict is read once a choose.
-- The lines: every result line (progress, done, failed) carries contact and the work leaf {heading (degrees, atan2's
--   convention), turn (degrees), clear, gap, n (the standing zombies in the sum), crawler (the nearest crawler's
--   distance within crawlerR x 2), held (fix 2: point_blank, lunge or attack, why the step was last withheld or ended;
--   absent once one goes)}, a value not yet read absent (clear and n until the first heading choice, fix 1:
--   "never chose" told from "chose, nothing clear"); the steps work, cornered and pile in the done line's
--   steps.
-- The cost (counted in test_lua_footwork.py): K.meleeCrowd's one read replaces the crowd's (3 a candidate: isDead,
--   isOnFloor, the distance); the floor reads the frame (2 calls without one); the step keeps its walk (walkAlong sets
--   it again only past K.MELEE_TURN_DOT) and holds the force-aim (setForceAim once a release); a re-choose adds getZ,
--   the player's square, 2 a standing zombie and 3 a crawler, and per square read once isSolid, isSolidTrans,
--   isBlockedTo and its crossed hop flag.
local K = PZA.skills
local M = K.meleeWork
if M == nil or K.types.melee == nil then return end   -- a melee without the footwork's sites: nothing registered
local MO = PZA.motor
local W = PZA.world
local posOf = W.posOf
local ST = K.stance

K.WORK_TICKS = 6             -- ticks between heading choices (about 0.1 s at the client's 60 Hz), the spec's
K.WORK_CLEAR_TICKS = 30      -- ticks in a row of nothing to fight before the clear hand-back (half a second)
K.WORK_TURNS = { 0, 30, -30, 60, -60, 90, -90, 120, -120, 150, -150, 180 }   -- degrees off the sum, nearest first
K.WORK_PROBE = { 0.6, 1.0 }  -- tiles along a heading its squares are read at
K.WORK_FALLEN_R = 0.5        -- tiles: a fallen zombie this near a probe point vetoes the heading
K.WORK_WITHDRAW_W = 1.0      -- the withdraw vector's weight in the sum
K.WORK_CRAWLER_W = 2.0       -- a crawler's weight in the sum (the standing ones' 1)
K.WORK_CONTACT_R = 1.0       -- tiles: the nearest standing zombie inside this is contact (the spec's reading)
K.WORK_STEP_TICKS = 30       -- fix 1: the most ticks of the step after a press's result inside the band (half a
                             -- second, a judgment: the struck zombie's stagger, #4686, is the step's window)
K.WORK_POINT_BLANK_R = 0.9   -- fix 2: tiles: no step with the nearest standing zombie inside this (K.MELEE_CROWD_R's
                             -- radius, the pile's: #4290); there the press is the defence (#4372, #4688)
K.WORK_PILE_R = 1.3          -- fix 3: tiles: three standing within this (the target counted) trigger the pile, as the
                             -- engine's attackers 2 do (the drag-down's approach, x_trial-ladder-20261110-091352)

local WORK_NUMS = { "workR", "crawlerR", "bandLo", "floorHealth" }
local WORK_KEYS = { "workR", "crawlerR", "bandLo", "floorHealth", "withdrawX", "withdrawY", "pile" }
local KEEP = { "hx", "hy", "heading", "turn", "clear", "n", "gap", "crawlerD", "sinceChoose", "nearId", "clearTicks" }
local RAD = math.pi / 180
local DEG = 180 / math.pi

-- the work table typed off the args: nil when no work field is given; nil, true when one is bad
local function workArgs(args)
    local any = false
    for i = 1, #WORK_KEYS do
        if args[WORK_KEYS[i]] ~= nil then any = true end
    end
    if not any then return nil end
    for i = 1, #WORK_NUMS do
        local v = args[WORK_NUMS[i]]
        if type(v) ~= "number" or v < 0 then return nil, true end
    end
    local wx, wy = args.withdrawX, args.withdrawY
    if (wx == nil) ~= (wy == nil) then return nil, true end
    if wx ~= nil and (type(wx) ~= "number" or type(wy) ~= "number") then return nil, true end
    if args.pile ~= nil and type(args.pile) ~= "boolean" then return nil, true end
    return { workR = args.workR, crawlerR = args.crawlerR, bandLo = args.bandLo, floorHealth = args.floorHealth,
             withdrawX = wx or 0, withdrawY = wy or 0, pile = args.pile == true,
             contact = 0, inContact = false, near = nil, gap = nil, nearId = nil, n = nil, clear = nil,
             stepTicks = 0, pressMark = 0, nearO = nil, held = nil,
             pileWhy = nil, pileShove = false, pileWait = 0, shoveId = nil, shoveFails = 0,
             hx = nil, hy = nil, heading = nil, turn = nil, crawlerD = nil, sinceChoose = K.WORK_TICKS,
             clearTicks = 0, pinId = nil, pileState = nil, pileTicks = 0, pileMark = 0, piles = 0 }
end

-- a re-send at the running melee's target: its footwork state and closing history kept, the new fields taken
local function keepState(work, st, args)
    local cur = K.cur
    if cur == nil or cur.type ~= "melee" or type(cur.st) ~= "table" or cur.st.work == nil then return end
    local o = cur.st
    if args.targetId ~= o.id and args.targetId ~= o.argId then return end
    for i = 1, #KEEP do work[KEEP[i]] = o.work[KEEP[i]] end
    if o.work.pileState == "step" then work.pileState, work.pileTicks = "step", o.work.pileTicks end
    if args.targetId == o.id then
        work.pinId = o.work.pinId
        st.hist, st.near = o.hist, o.near
    end
end

local def = K.types.melee
local baseCheck = def.check
def.check = function(args, p)
    local work, bad = workArgs(args)
    if bad then return false, "bad args" end
    local ok, why, st = baseCheck(args, p)
    if not ok or work == nil then return ok, why, st end
    keepState(work, st, args)
    st.work = work
    return ok, why, st
end

-- the first tick with work checks getZ (the heading's square reads; not loaded); contact counted at the tick's end
local baseTick = def.tick
def.tick = function(p, st)
    local w = st.work
    if w == nil then return baseTick(p, st) end
    if st.startMs == nil and not PZA.field(p, "getZ") then return "failed", "not loaded" end
    w.inContact = false
    local a, b, c = baseTick(p, st)
    if w.inContact and st.strike == nil then w.contact = w.contact + 1 end
    return a, b, c
end

-- the crawlers within r of the player other than the target ({id, d, o, x, y} each, nearest first), or nil: the last
-- frame's records reading crawler within r + K.MELEE_CROWD_SLACK, each read live (dead, its position) through S.zobj
function K.crawlersNear(p, st, r)
    local S = PZA.sense
    local f = S ~= nil and S.last or nil
    local objs = S ~= nil and S.zobj or nil
    local recs = f ~= nil and f.zombies or nil
    if recs == nil or objs == nil or st.px == nil then return nil end
    local out = nil
    for i = 1, #recs do
        local rec = recs[i]
        if rec.crawler == true and rec.id ~= st.id and type(rec.dist) == "number" and rec.dist < r + K.MELEE_CROWD_SLACK then
            local o = objs[rec.id]
            if o ~= nil and not K.zombieDead(o) then
                local x, y = posOf(o)
                if x ~= nil and y ~= nil then
                    local ex, ey = x - st.px, y - st.py
                    local d = math.sqrt(ex * ex + ey * ey)
                    if d < r then
                        out = out or {}
                        out[#out + 1] = { id = rec.id, d = d, o = o, x = x, y = y }
                    end
                end
            end
        end
    end
    if out ~= nil and #out > 1 then table.sort(out, function(a, b) return a.d < b.d end) end
    return out
end

-- the body's health: the last frame's body.health, else the live read; nil unread
local function playerHealth(p)
    local S = PZA.sense
    local f = S ~= nil and S.last or nil
    local h = f ~= nil and type(f.body) == "table" and f.body.health or nil
    if type(h) == "number" then return h end
    local _, bd = PZA.call(p, "getBodyDamage")
    local _, v = PZA.call(bd, "getOverallBodyHealth")
    if type(v) == "number" then return v end
    return nil
end

-- the floor hand-back: done handback floor at or under floorHealth (above 0); else nil
function K.workFloor(p, st)
    local w = st.work
    if w == nil or w.floorHealth <= 0 then return nil end
    local h = playerHealth(p)
    if h ~= nil and h <= w.floorHealth then return "done", "handback", { why = "floor" } end
    return nil
end

-- the frame's record of zombie id, or nil
local function recordOf(id)
    local S = PZA.sense
    local f = S ~= nil and S.last or nil
    local recs = f ~= nil and f.zombies or nil
    if recs == nil then return nil end
    for i = 1, #recs do
        if recs[i].id == id then return recs[i] end
    end
    return nil
end

-- the stance's force-aim held for the step (the meet released it inside faceR this tick; the Motor re-asserts it
-- every frame from here, PZAgent_Motor.lua)
local function aimHeld(p)
    if ST.held then return end
    PZA.call(p, "setForceAim", true)
    ST.held = true
    MO.wantAim = true
end

-- whether square (sx, sy) is clear from the player's square (ctx), read once a choose: the player's own square is;
-- else readable, neither solid nor solidTrans, not blocked from the player's square, no hoppable crossed edge
local function hopOn(sq, name)
    local flag = IsoFlagType ~= nil and IsoFlagType[name] or nil
    if flag == nil then return false end
    local ok, v = PZA.call(sq, "has", flag)
    return not ok or v == true
end

local function readSquare(ctx, sx, sy)
    local psq = ctx.psq
    if psq == nil then return false end
    local sq = K.squareAt(sx, sy, ctx.pz)
    if sq == nil then return false end
    local okS, solid = PZA.call(sq, "isSolid")
    if not okS or solid ~= false then return false end
    local okT, trans = PZA.call(sq, "isSolidTrans")
    if not okT or trans ~= false then return false end
    local okB, blocked = PZA.call(psq, "isBlockedTo", sq)
    if not okB or blocked ~= false then return false end
    if sx ~= ctx.psx then
        local east = psq
        if sx > ctx.psx then east = sq end
        if hopOn(east, "HoppableW") then return false end
    end
    if sy ~= ctx.psy then
        local south = psq
        if sy > ctx.psy then south = sq end
        if hopOn(south, "HoppableN") then return false end
    end
    return true
end

local function squareClear(ctx, sx, sy)
    if sx == ctx.psx and sy == ctx.psy then return true end
    local key = tostring(sx) .. ":" .. tostring(sy)
    local v = ctx.cache[key]
    if v == nil then
        v = readSquare(ctx, sx, sy)
        ctx.cache[key] = v
    end
    return v
end

-- whether the unit heading (hx, hy) is clear (the header's rule)
local function headingClear(ctx, w, hx, hy)
    for i = 1, #K.WORK_PROBE do
        local r = K.WORK_PROBE[i]
        local x, y = ctx.px + hx * r, ctx.py + hy * r
        if not squareClear(ctx, math.floor(x), math.floor(y)) then return false end
        local cs = ctx.crawlers
        if cs ~= nil then
            for j = 1, #cs do
                local ex, ey = cs[j].x - x, cs[j].y - y
                if ex * ex + ey * ey < w.crawlerR * w.crawlerR then return false end
            end
        end
        local fs = ctx.fallen
        for j = 1, #fs do
            local ex, ey = fs[j].x - x, fs[j].y - y
            if ex * ex + ey * ey < K.WORK_FALLEN_R * K.WORK_FALLEN_R then return false end
        end
    end
    return true
end

-- adds the repulsion of a zombie at (x, y), weight wt / d^2, to the sum s
local function repel(s, px, py, x, y, wt)
    local ex, ey = px - x, py - y
    local d2 = ex * ex + ey * ey
    if d2 <= 0 then return false end
    local d = math.sqrt(d2)
    s.x = s.x + ex / d * wt / d2
    s.y = s.y + ey / d * wt / d2
    return true
end

-- the heading chosen (the header's rule) into w: hx, hy, heading, turn, clear, n, crawlerD
local function choose(p, st, fallen)
    local w = st.work
    w.sinceChoose = 0
    local px, py = st.px, st.py
    local s = { x = 0, y = 0 }
    local n = 0
    local fl = {}
    if not fallen then
        if repel(s, px, py, st.zx, st.zy, 1) then n = n + 1 end
    else
        fl[#fl + 1] = { x = st.zx, y = st.zy }
    end
    local S = PZA.sense
    local f = S ~= nil and S.last or nil
    local objs = S ~= nil and S.zobj or nil
    local recs = f ~= nil and f.zombies or nil
    if recs ~= nil and objs ~= nil then
        for i = 1, #recs do
            local rec = recs[i]
            if rec.id ~= st.id and type(rec.dist) == "number" and rec.crawler ~= true then
                if rec.onFloor == true then
                    if type(rec.x) == "number" and type(rec.y) == "number" and rec.dist < w.workR + K.MELEE_CROWD_SLACK then
                        fl[#fl + 1] = { x = rec.x, y = rec.y }
                    end
                elseif rec.dist < w.workR + K.MELEE_CROWD_SLACK then
                    local o = objs[rec.id]
                    local x, y = nil, nil
                    if o ~= nil then x, y = posOf(o) end
                    if x ~= nil and y ~= nil then
                        local ex, ey = x - px, y - py
                        if ex * ex + ey * ey < w.workR * w.workR and repel(s, px, py, x, y, 1) then n = n + 1 end
                    end
                end
            end
        end
    end
    local cs = K.crawlersNear(p, st, w.crawlerR * 2)
    w.crawlerD = nil
    if cs ~= nil then
        w.crawlerD = cs[1].d
        for i = 1, #cs do repel(s, px, py, cs[i].x, cs[i].y, K.WORK_CRAWLER_W) end
    end
    s.x = s.x + K.WORK_WITHDRAW_W * w.withdrawX
    s.y = s.y + K.WORK_WITHDRAW_W * w.withdrawY
    w.n = n
    local len = math.sqrt(s.x * s.x + s.y * s.y)
    if len <= 0 then
        s.x, s.y = px - st.zx, py - st.zy
        len = math.sqrt(s.x * s.x + s.y * s.y)
    end
    w.hx, w.hy, w.heading, w.turn, w.clear = nil, nil, nil, nil, false
    if len <= 0 then return end
    local bx, by = s.x / len, s.y / len
    local _, pz = PZA.call(p, "getZ")
    local psx, psy = math.floor(px), math.floor(py)
    local ctx = { px = px, py = py, pz = pz, psx = psx, psy = psy, psq = K.squareAt(psx, psy, pz), cache = {},
                  crawlers = cs, fallen = fl }
    for i = 1, #K.WORK_TURNS do
        local a = K.WORK_TURNS[i] * RAD
        local c, sn = math.cos(a), math.sin(a)
        local hx, hy = bx * c - by * sn, bx * sn + by * c
        if headingClear(ctx, w, hx, hy) then
            w.hx, w.hy, w.turn, w.clear = hx, hy, K.WORK_TURNS[i], true
            w.heading = math.atan2(hy, hx) * DEG
            return
        end
    end
end

-- the step along the heading (chosen when due): kind, or cornered with none clear (the walk stopped)
local function stepAlong(p, st, kind, fallen)
    local w = st.work
    if w.sinceChoose >= K.WORK_TICKS then choose(p, st, fallen) end
    if not w.clear then
        M.stopWalk(p, st)
        return "cornered"
    end
    aimHeld(p)
    M.walkAlong(p, st, "work", w.hx, w.hy)
    return kind
end

-- the presses pressed so far
local function presses(st)
    return st.swings + st.shoves + st.stomps + st.floors
end

-- fix 3 (x_trial-ladder-20261110-091352, the drag-down death at frame 1420: two to four standing at 0.47 to 1.3 tiles
-- for 70 frames with the engine's attackers 1 to 2, a30 and a31 shoving nine times with no knock-down, the pile met
-- only at frame 1395, three within K.MELEE_CROWD_R one frame before the drag): the engine's attackers count, the last
-- frame's me.attackers, else getSurroundingAttackingZombies live; 0 unread
local function attackersOf(p)
    local S = PZA.sense
    local f = S ~= nil and S.last or nil
    local a = f ~= nil and type(f.me) == "table" and f.me.attackers or nil
    if type(a) == "number" then return a end
    local ok, v = PZA.call(p, "getSurroundingAttackingZombies")
    if ok and type(v) == "number" then return v end
    return 0
end

-- the pile's trigger now, or nil: attackers (the engine counts 2 or more attacking), else near (K.MELEE_CROWD_N
-- standing within K.WORK_PILE_R, the target counted while it stands: the drag-down's approach, not its radius, #4290)
local function pileTrigger(p, st, standing)
    if attackersOf(p) >= 2 then return "attackers" end
    local n = 0
    if standing then n = 1 end
    local near = st.work.near
    if near ~= nil then
        for i = 1, #near do
            if near[i].d < K.WORK_PILE_R then n = n + 1 end
        end
    end
    if n >= K.MELEE_CROWD_N then return "near" end
    return nil
end

-- the pile (pile true; fix 3): on the trigger the shove at the nearest standing zombie (re-pinned to it first; within
-- shoveR, and not after two shoves in a row at it that knocked nothing down), at its result the step `pile` along the
-- clearest heading for K.WORK_STEP_TICKS ticks with the body snapped on the target, ungated (the move at point
-- blank: no point-blank, lunge or attack hold), `cornered` with no clear heading (the meet presses next); then the
-- meet's next press (the swing once the gap passes MinRange), waited K.WORK_STEP_TICKS at most; again while the
-- trigger holds. nil to go on
local function pileTick(p, st, d, fallen, standing)
    local w = st.work
    local why = pileTrigger(p, st, standing)
    if why ~= nil then w.pileWhy = why end
    if w.pileState == "step" then
        if w.pileShove then   -- the shove's result, read on the step's first tick
            w.pileShove = false
            if st.knocked then
                w.shoveFails = 0
            elseif w.shoveId == st.id then
                w.shoveFails = w.shoveFails + 1
            else
                w.shoveId, w.shoveFails = st.id, 1
            end
        end
        if w.pileTicks < K.WORK_STEP_TICKS then
            w.pileTicks = w.pileTicks + 1
            K.FACING.hold(p, st, K.FACING.bearing(st.px, st.py, st.zx, st.zy))
            local step = stepAlong(p, st, "pile", fallen)
            if step == "cornered" then w.pileTicks = K.WORK_STEP_TICKS end
            return step
        end
        w.pileState, w.pileMark, w.pileWait = "press", presses(st), 0
        return nil
    end
    if w.pileState == "press" then
        w.pileWait = w.pileWait + 1
        if presses(st) > w.pileMark or why == nil or w.pileWait >= K.WORK_STEP_TICKS then
            w.pileState = nil
        else
            return nil
        end
    end
    if why == nil or fallen or not standing then return nil end
    local near = w.near
    if near ~= nil and near[1].d < d - K.MELEE_REPIN_SLACK then return M.repin(p, st, near[1]) end
    if d > st.shoveR or (w.shoveId == st.id and w.shoveFails >= 2) then   -- the step first, then the meet's press
        w.pileState, w.pileTicks, w.piles = "step", 0, w.piles + 1
        return pileTick(p, st, d, fallen, standing)
    end
    local off = M.lookOff(p, st.px, st.py, st.zx, st.zy)
    local step, pwhy = M.press(p, st, "shove", d, d, off, "face", d)
    if step == "shove" then w.pileState, w.pileTicks, w.piles, w.pileShove = "step", 0, w.piles + 1, true end
    return step, pwhy
end

-- fix 1 (the smokes x_trial-ladder-20261110-081250 and -081935: inside the band the meet pressed swing after swing
-- and never reached its stand or face, so the step never went): at a press's result (the presses' count moved since
-- the last tick read, no refusal running) the step is armed for K.WORK_STEP_TICKS ticks; while armed and the nearest
-- standing zombie (the target not knocked down) is inside the reach less bandLo, the step `work` goes before the
-- meet's next press, the body snapped on the target; cornered, or the gap out of the band, ends it and the meet presses
-- fix 2 (x_trial-ladder-20261110-084643, a73's wound at frame 2618: the step went at the leaf's gap 0.59, the nearest
-- the second zombie 4378 reading `attack`, ahead of the meet's re-pin to it and its press; the bite landed at 0.73):
-- why the step is withheld or ended now, or nil: point_blank (the nearest standing zombie inside
-- K.WORK_POINT_BLANK_R), lunge or attack (its getRealState so reading; one call). The reason is kept in w.held for
-- the leaf, cleared when a step goes
local function stepHeld(w, g)
    if g ~= nil and g < K.WORK_POINT_BLANK_R then return "point_blank" end
    local o = w.nearO
    if o == nil then return nil end
    local ok, state = PZA.call(o, "getRealState")
    if not ok or type(state) ~= "string" then return nil end
    if string.find(state, "lunge") ~= nil then return "lunge" end
    if string.find(state, "attack") ~= nil then return "attack" end
    return nil
end

local function pressStep(p, st, standing, g)
    local w = st.work
    local pc = presses(st)
    if pc ~= w.pressMark then
        w.pressMark = pc
        if st.refusals == 0 then w.stepTicks = K.WORK_STEP_TICKS end
    end
    if w.stepTicks <= 0 then return nil end
    if not standing or g == nil or g >= M.reachOf(p, st) - w.bandLo then
        w.stepTicks = 0
        return nil
    end
    local held = stepHeld(w, g)
    if held ~= nil then   -- fix 2: the meet presses (the protective shove inside MinRange, else the swing)
        w.held, w.stepTicks = held, 0
        M.stopWalk(p, st)
        return nil
    end
    w.held = nil
    w.stepTicks = w.stepTicks - 1
    K.FACING.hold(p, st, K.FACING.bearing(st.px, st.py, st.zx, st.zy))
    local step = stepAlong(p, st, "work", false)
    if step == "cornered" then
        w.stepTicks = 0
        return nil
    end
    return step
end

-- the footwork's tick (the header's): the floor, the gap and contact, clear, the pile; a step or an end, else nil
function K.workTick(p, st, d, crowd, fallen, now)
    local w = st.work
    w.sinceChoose = w.sinceChoose + 1
    local fh, fhow, fres = K.workFloor(p, st)
    if fh ~= nil then return fh, fhow, fres end
    local g, gid = nil, nil
    local standing = not fallen and not st.knocked   -- fix 1: a target the press knocked down is no standing zombie
    if standing then g, gid, w.nearO = d, st.id, st.z end
    local near = w.near
    if near ~= nil and (g == nil or near[1].d < g) then g, gid, w.nearO = near[1].d, near[1].id, near[1].o end
    if g == nil then w.nearO = nil end
    w.gap = g
    if gid ~= w.nearId then w.nearId, w.sinceChoose = gid, K.WORK_TICKS end
    w.inContact = g ~= nil and g < K.WORK_CONTACT_R
    local clear = false
    if fallen and g == nil and d > w.crawlerR then
        local rec = recordOf(st.id)
        if (w.pinId == st.id or rec ~= nil and rec.crawler == true)
           and M.standingNear(p, st, st.releaseR) == nil and K.crawlersNear(p, st, w.crawlerR) == nil then
            clear = true
        end
    end
    if clear then
        w.clearTicks = w.clearTicks + 1
        if w.clearTicks >= K.WORK_CLEAR_TICKS then return "done", "handback", { why = "clear" } end
    else
        w.clearTicks = 0
    end
    if w.pile then
        local ps, phow, pres = pileTick(p, st, d, fallen, standing)
        if ps ~= nil then return ps, phow, pres end
    end
    return pressStep(p, st, standing, g)
end

-- the idle (the meet would stand or face): the crawler target, the step inside the band, else the meet's own
function K.footwork(p, st, d, px, py, zx, zy, now)
    local w = st.work
    local reach = M.reachOf(p, st)
    if w.gap == nil or w.gap > reach then
        local cs = K.crawlersNear(p, st, w.crawlerR)
        if cs ~= nil then
            local step = M.repin(p, st, cs[1])
            w.pinId, w.nearId, w.sinceChoose = cs[1].id, nil, K.WORK_TICKS
            return step
        end
    end
    if w.gap ~= nil and w.gap < reach - w.bandLo then
        local held = stepHeld(w, w.gap)   -- fix 2: no step at point blank or into a lunge
        if held == nil then
            w.held = nil
            return stepAlong(p, st, "work", false)
        end
        w.held = held
    end
    M.stopWalk(p, st)
    if st.near then return "face" end
    return "stand"
end

-- the result's contact and work leaf (every result line while work is set)
function K.workResult(st, out)
    local w = st.work
    out.contact = w.contact
    out.work = { heading = w.heading, turn = w.turn, clear = w.clear, gap = w.gap, n = w.n, crawler = w.crawlerD,
                 held = w.held, pile = w.pileWhy }
end
