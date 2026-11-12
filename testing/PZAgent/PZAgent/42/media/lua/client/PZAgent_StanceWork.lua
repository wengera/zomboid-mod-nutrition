-- PZAgent_StanceWork.lua — the footwork reflex (PZA/1.13, Plan 35 Task 1; the spec
-- `2026-11-10-plan-35-the-footwork-design.md` section 3.1, the cerebellum's second cut; PZA/1.16, Plan 37 Task 2: the
-- dispositions, the string and the safe release, the spec `2026-11-12-plan-37-the-disposition-design.md` sections 3.1
-- to 3.3, the block at the end of this file). The melee reflex
-- (PZAgent_StanceMelee.lua) owns one zombie to the kill at the client's tick rate; this file gives it footwork between
-- presses behind the melee's optional work arguments, so in contact one reflex owns the press, the facing and the step
-- together and no 2 Hz leg supersedes it. Loads after PZAgent_StanceMelee.lua (client files load by name,
-- case-insensitively, #0850: "pzagent_stancemelee" before "pzagent_stancework"), and registers into it as Plan 34 Task
-- 4b's K.meleeHitHandback did: the melee's hooks (the block at the end of PZAgent_StanceMelee.lua) call K.footwork,
-- K.workTick, K.workResult and K.workFloor only when st.work is set, which only this file's check sets. With no work
-- argument the melee runs as before, byte for byte (test_lua_footwork.py). Every Java member through PZA.call, every
-- vanilla constant index-checked; no goto, no integer format of a float, no # on a Java list.
--
-- melee {..., workR, crawlerR, bandLo, withdrawX, withdrawY, floorHealth, pile[, backswing][, disposition][, release]}
--   (PZA/1.13; backswing PZA/1.15, Plan 36 Task 2a; disposition and release PZA/1.16, Plan 37 Task 2): disposition
--   the table of primitives the tick runs (K.DISPOSITIONS: hunt, hold or string; absent reads hunt, the Plan 36
--   footwork byte for byte), release true to ask the hand-back released (K.workRelease); workR the standing zombies
--   read for the heading (3.5 tiles), crawlerR a crawler this near repels the heading hard, vetoes a probe point and is
--   the target with no standing zombie in reach (1.2), bandLo the gap under which the step back goes is the reach less
--   this (0.4), withdrawX and withdrawY the planner's bias (a vector, absent together), floorHealth the hand-back floor
--   (0 for none), pile true to meet three standing within K.MELEE_CROWD_R in the reflex, backswing true to press on
--   the back step: a press launched while this file's step walks (the auto-walk of kind work: setAutoWalk and
--   setAutoWalkDirection in input space, M.walkAlong, never a position write) leaves the walk held through the press
--   instead of stopping it on the press's tick (the melee's K.meleePressWalk; the leaf's moving_back). check
--   (wrapped): any work field given makes workR, crawlerR, bandLo and floorHealth numbers at or above 0, the withdraw
--   pair numbers or absent together, pile, backswing and release booleans or absent, disposition a K.DISPOSITIONS key
--   or absent (bad args otherwise); none given leaves st.work nil. Under a disposition with its own release radius
--   (string: K.STRING_RELEASE_R) the melee's check reads it in place of the sent releaseR (too far, and rule 3's out
--   of range after it). Plan 37 Task 2 (the spec's section 3.1, widening Plan 35's same-target rule): a melee re-sent
--   carrying work while one with work runs keeps the footwork's state whatever the target (keepState: the heading and
--   its choice, the nearest's id, the clear count, the pile's step and its heading, the cadence marks re-based on the
--   new act's press counts, the armed ticks of the band step, the ride, the buffer and the stagger in, the flight time,
--   the ring, the gait, and the release's count while both ask it) and takes the new work fields; the per-target reads
--   (the crawler pin, the closing history, the faceR latch) are kept only at the same target (its sent id). The melee
--   keeps the stance across it (keptOnResend). So the planner changes the disposition and the target by re-send.
-- Each tick with work, after a press in flight and a hit reaction (the melee's rules 1 and 2) and the release radius,
-- the tick (K.workTick, before the crowd), in order (Plan 36 Task 2b: the contact cadence and the crawler buffer, the
-- spec 2026-11-11-plan-36-the-engagement-design.md sections 3.2 and 3.5; the probe's ruling task-2-ruling.md: the
-- engine starts and lands an attack while the stance walks backward, so the press rides the moving back step):
--   the floor hand-back (done handback, why floor: the body's health, the last frame's body.health else
--   getBodyDamage():getOverallBodyHealth(), at or under floorHealth when floorHealth is above 0; read under a hit
--   reaction too); the release (Plan 37 Task 2: release true, K.workRelease; read under a hit reaction too); the stall
--   (fix 7); the gap (the nearest standing zombie: the target while it stands, else the
--   nearest of K.meleeCrowd's read within the larger of the reach, K.MELEE_CROWD_R and K.WORK_CONTACT_R), a change of
--   its id re-choosing the heading at once; contact (the tick's nearest standing inside K.WORK_CONTACT_R, counted when
--   no press is in flight at the tick's end); clear (done handback, why clear: K.WORK_CLEAR_TICKS ticks in a row with
--   the target a crawler beyond crawlerR, no standing zombie within releaseR and no other crawler within crawlerR);
--   1. the pile (pile true, pileTick below; Plan 36 Task 2b items 5 and 7b, replacing Plan 35 fix 3's trigger and
--      its shove-first loop): (a) a shove's result (any shove of the melee, the press's count moved) is always
--      followed by the step out, never by a re-pin and another shove; (b) two or more standing inside
--      K.WORK_POINT_BLANK_R (the target counted while it stands) take the step out before any shove (the point-blank
--      hold yields to it); the step out goes along the room ring's most open heading within 90 degrees of the way
--      away from their centroid (outHeading), K.WORK_STEP_TICKS ticks, step_for pile_out, the body held on the
--      nearest; then the meet's next press, waited K.WORK_STEP_TICKS at most; no heading reading K.WORK_ROOM_NEED:
--      the meet presses (cornered). (c) The chosen knock-down: one standing inside point blank and two or more within
--      the reach (the target counted): the nearest re-pinned to, then shoved (shove_for knockdown on the line),
--      then (a). The crowd hand-back is kept for pile false.
--   Plan 37 Task 2 fix 3 (the horde8 trial x_trial-ladder-20261112-065221, a trial reading: a zombie the shove knocked
--   down bit the leg from the floor at 0.85 tiles, CrawlerBiteLEFT, and the drag-down followed): to the reflex a
--   fallen zombie (the frame's onFloor record read live: not dead, isOnFloor; never the finish's target) inside
--   K.CRAWLER_BITE_R is a crawler (K.crawlersNear: the buffer step, the probe veto, no clear), the stomp first only
--   for a real crawler; one within K.CRAWLER_BUFFER_R repels the heading at K.WORK_CRAWLER_W; and the step out after
--   a shove that knocked its target down is repelled by it at that weight (outHeading's weighted centroid).
--   2. the crawler buffer (crawlerTick below; Plan 36 Task 2b item 7, replacing Plan 35 fix 5's stomp-first): a
--      crawler within K.CRAWLER_BUFFER_R with the target standing ends the standing position: one step perpendicular
--      to the crawler's bearing toward the ring's more open side (bufferHeading) for K.WORK_STEP_TICKS ticks before
--      the next press (step_for crawler_buffer), one such step a press; the crawler is the target (the re-pin, the
--      finish's stomp) only inside K.CRAWLER_BITE_R with nothing standing within K.MELEE_CROWD_R.
--   3. the nearest attacker's facing (attackerTick; item 6): the gap inside K.WORK_POINT_BLANK_R, the reflex re-pins
--      to the zombie inside it whose getRealState reads attack (read only with the engine's attackers count above 0;
--      the target first), else to the nearest standing one when it is nearer than the target by
--      K.MELEE_REPIN_SLACK; repin_for attacker.
--   pinned (Plan 37 Task 2: two or more standing inside K.WORK_POINT_BLANK_R, the target counted, the leaf's);
--   4. the stagger in (staggerIn; item 4; off under string): the standing target the nearest, beyond the reach by under
--      K.WORK_STAGGER_R and reading staggerback or hitreaction: one step toward it (the walk kind in, never held
--      through a press) for K.WORK_STEP_TICKS ticks at most, step_for stagger_in, one a press; the press, then the
--      step back.
--   4b. the string (Plan 37 Task 2, K.workString at the end of this file; under string only): the walk away, or the
--      turn and the meet's press at the leader; the retreat and the band step do not run under it.
--   5. the retreat (fix 6, retreatTick below; item 4): on by the disposition's retreat flag (hunt: a withdraw vector
--      given, the Plan 36 rule; hold: always, along the repulsion sum with no vector; string: never), the back step
--      along the biased
--      heading (step_for retreat, the leaf's retreat true) goes only while the predicted distance at the next swing's
--      landing (K.workLanding: the gap less the target's closing speed and plus the player's own speed away, times the
--      swing's flight time) stays within the reach less K.WORK_EDGE_SLACK; past it the step is withheld (held reach) and the meet closes or
--      waits; the press goes at whoever stands nearest inside the reach beyond MinRange on every press window, the
--      window opening K.WORK_RIDE_TICKS ticks of the step after each press's result (the swing rides the back step:
--      with backswing the walk is held through the press; inside MinRange the meet's protective shove, then (1a) the
--      step); the band step does not run under it.
--   6. the band step (pressStep; fix 1): armed at a press's result, while the nearest standing is inside the reach
--      less bandLo and its landing distance within the reach, unless held point_blank or attack (fixes 2 and 4).
--   the idle (K.footwork, where the meet would stand or face): the gap under the reach less bandLo the step `work`
--   along the heading (the stance's
--   force-aim held, the auto-walk in input space, the facing the meet's own snap this tick), `cornered` with no clear
--   heading (the walk stopped: the press is the defence); else the meet's own stand or face.
--   the heading (re-chosen every K.WORK_TICKS ticks, at once on a new nearest): the repulsion sum of the standing
--   zombies within workR (the frame's records not onFloor and not crawler, each position read live; the target's this
--   tick's) weighted 1 / d^2, of the crawlers within crawlerR x 2 (K.crawlersNear) weighted K.WORK_CRAWLER_W / d^2, and
--   K.WORK_WITHDRAW_W x the withdraw vector; turned by K.WORK_TURNS in order, the first clear one taken. A heading is
--   clear (Plan 36 Task 1) when the room ring's heading nearest it (K.workRoomIndex, 45 degrees apart) reads at least
--   K.WORK_ROOM_NEED tiles clear (the ring, the end of this file: the squares readable, neither isSolid nor
--   isSolidTrans, not isBlockedTo from the square before, no hoppable crossed edge: the stance cannot climb, #4289),
--   and at each K.WORK_PROBE distance along the heading itself no crawler lies within crawlerR of the point no farther
--   from it than the player now (fix 5) and no fallen zombie (the frame's onFloor records, the target fallen) within
--   K.WORK_FALLEN_R. The ring is the work state's, read again at a choose on a new square or after K.WORK_TICKS (fix
--   1's budget ruling: at most one ring a re-choose). A heading the ring cannot index (a non-finite sum) reads closed,
--   and a non-finite sum is no heading at all (cornered, the leaf's nan_heading).
-- The lines: every result line (progress, done, failed) carries contact and the work leaf {disposition, pinned (Plan 37
--   Task 2), turn_for {leader, gap2} (on a line whose tick the string turned), heading (degrees, atan2's
--   convention), turn (degrees), clear, gap, n (the standing zombies in the sum), crawler (the nearest crawler's
--   distance within crawlerR x 2), held (fixes 2 and 4: point_blank or attack; Plan 36 Task 2b: reach; why the step was
--   last withheld or ended; absent once one goes), pile (Plan 36 Task 2b: pile_out or shove, what started the last
--   step out), step_for (gap, retreat, and since Plan 36 Task 2b pile_out, crawler_buffer or stagger_in, since Plan 37
--   Task 2 string; turn and n only for a step along a chosen heading), repin_for (stall, and since Plan 36 Task 2b
--   attacker, since Plan 37 Task 2 string), shove_for
--   (Plan 36 Task 2b: knockdown, on its press's line)}, a value not read absent; heading, turn, clear, n and step_for
--   only on a tick that stepped, crawler read every tick; the steps work and cornered in the done line's steps.
-- The cost (counted in test_lua_footwork.py): K.meleeCrowd's one read replaces the crowd's (3 a candidate: isDead,
--   isOnFloor, the distance); the floor reads the frame (2 calls without one); the step keeps its walk (walkAlong sets
--   it again only past K.MELEE_TURN_DOT) and holds the force-aim (setForceAim once a release); a re-choose adds getZ,
--   2 a standing zombie and 3 a crawler, and the ring's read when it is due (the ring's own cost, at its block).
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
K.WORK_PILE_R = 1.3          -- fix 3: tiles: the near read's radius with pile (K.meleeCrowd; since Plan 36 Task 2b
                             -- no trigger of its own: the pile is two inside K.WORK_POINT_BLANK_R)
K.CRAWLER_BUFFER_R = 2.0     -- Plan 36 Task 2b (the spec's section 3.5): tiles: a crawler this near ends the standing
                             -- position (the buffer step)
K.CRAWLER_BITE_R = 0.9       -- tiles: a crawler inside this is stomped first when nothing stands within
                             -- K.MELEE_CROWD_R (a judgment: the CrawlerBite read at 0.85 in x_trial-ladder-20261109-
                             -- 105452, under the crowd radius)
K.WORK_STAGGER_R = 1.0       -- tiles beyond the reach a staggered target is stepped in to (a judgment: one step's gain)
K.WORK_EDGE_SLACK = 0.1      -- tiles: the retreat's back step stops this short of the reach (a tolerance: a dead band
                             -- between the back step and the meet's close walk beyond the reach, no flapping)
K.WORK_RIDE_TICKS = 6        -- the retreat's back step after a press's result before the next press window (K.WORK_TICKS'
                             -- 0.1 s, a judgment: the press rides a step already walking)
-- Plan 37 Task 2 (PZA/1.16, the spec 2026-11-12-plan-37-the-disposition-design.md sections 3.2 and 3.3). The speeds
-- below are a design read off F21's and F22's committed frames by the controller's scratch (Plan 36 Task 4's method),
-- not evidence: the character walks at 2.09 tiles a second (median of 1179 consecutive-frame pairs moving and not
-- aiming), runs at 3.55 (959 pairs running) and backpedals in the stance at 0.98 (882 pairs moving and aiming);
-- zombies walk at 0.55 median and 1.45 at the 90th percentile, and lunge at 1.34 median and 1.58 at the 90th. So a
-- walk outpaces every shambler and a run every zombie, and a group strung out by speed meets the character one at a time
K.STRING_GAP = 2.5           -- tiles: the string turns to press the leader only with the second-nearest standing
                             -- beyond this (the spec's section 3.2: the second well behind)
K.STRING_TURN_R = 0.5        -- tiles beyond the reach within which the leader's distance at the next landing turns the
                             -- walk (the spec's section 3.3: the turn lands the press as the leader arrives)
K.STRING_RUN_V = 1.0         -- tiles a second: the leader closing faster takes the run (Plan 37 Task 2 fix 1, the
                             -- string probe x_trial-ladder-20261112-055128, a trial reading: its leaders walked at
                             -- about 1.4 and the gap never grew at a walk; the walk's 2.09 outpaces only the slow
                             -- shambler's 0.55, the design read above, so anything faster takes the run; was 1.6)
K.STRING_RELEASE_R = 8.0     -- tiles: the melee's release radius under string (the planner sends it at a leader five
                             -- tiles off; the spec's section 3.2)
K.RELEASE_SAFE_R = 1.3       -- tiles: the release hands back safe with the nearest standing beyond this (K.WORK_PILE_R's
                             -- radius: beyond the pile's read; the spec's section 3.1)
K.RELEASE_MAX_TICKS = 90     -- ticks after the first that read release before it hands back whatever the frame (1.5 s
                             -- at the client's 60 Hz, a judgment: the spec's bound, about a swing's clip and a half at
                             -- CombatSpeed 1.0, #4668)
-- the dispositions (the spec's section 3.2): each the flags the tick reads, never a copy of the tick. retreat: given
-- (the fighting retreat with a withdraw vector given, the Plan 36 rule), always (with none, along the repulsion sum)
-- or never; staggerIn the step in on a staggered target; knockdown the pile's chosen knock-down (rule (c): off under
-- string, fix 1: the probe's shoves cost the walk its gain; the step out, (a) and (b), runs under every disposition and
-- the string's walk resumes after it); string the string's walk and turn (K.workString); releaseR
-- the release radius the check sends in place of the planner's. The crawler buffer and the nearest attacker's facing
-- read no flag: on under every disposition (test_lua_footwork.py)
K.DISPOSITIONS = {
    hunt = { retreat = "given", staggerIn = true, knockdown = true, string = false },
    hold = { retreat = "always", staggerIn = true, knockdown = true, string = false },
    string = { retreat = "never", staggerIn = false, knockdown = false, string = true, releaseR = K.STRING_RELEASE_R },
}

local WORK_NUMS = { "workR", "crawlerR", "bandLo", "floorHealth" }
local WORK_KEYS = { "workR", "crawlerR", "bandLo", "floorHealth", "withdrawX", "withdrawY", "pile", "backswing",
                    "disposition", "release" }   -- Plan 37 Task 2: disposition and release
local KEEP = { "hx", "hy", "heading", "turn", "clear", "n", "gap", "crawlerD", "sinceChoose", "nearId", "clearTicks",
               "stepTicks", "rideTicks", "crawlTicks", "inTicks", "bufHx", "bufHy", "tc", "walkV", "room", "roomTicks",
               "stringTicks", "run", "gaitRun" }   -- Plan 37 Task 2: the armed ticks, the ring and the gait too
local MARKS = { "pressMark", "rideMark", "crawlMark", "inMark", "pileMark", "tcMark" }   -- the press counts they read
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
    if args.backswing ~= nil and type(args.backswing) ~= "boolean" then return nil, true end   -- Plan 36 Task 2a
    local disp = args.disposition   -- Plan 37 Task 2
    if disp ~= nil and (type(disp) ~= "string" or K.DISPOSITIONS[disp] == nil) then return nil, true end
    if args.release ~= nil and type(args.release) ~= "boolean" then return nil, true end
    return { workR = args.workR, crawlerR = args.crawlerR, bandLo = args.bandLo, floorHealth = args.floorHealth,
             disposition = disp or "hunt", release = args.release == true, releaseTicks = nil,   -- Plan 37 Task 2
             pinned = false, turnFor = nil, stringing = false, stringWalked = false, stringTicks = K.WORK_TICKS,
             run = false, gaitRun = false,
             withdrawX = wx or 0, withdrawY = wy or 0, pile = args.pile == true,
             backswing = args.backswing == true,   -- Plan 36 Task 2a: the press held on the back step
             retreat = wx ~= nil and (wx ~= 0 or wy ~= 0), retreating = false,   -- fix 6: a withdraw vector given
             contact = 0, inContact = false, near = nil, gap = nil, nearId = nil, n = nil, clear = nil,
             stepTicks = 0, pressMark = 0, nearO = nil, held = nil,
             pileWhy = nil, pileWait = 0, shoveMark = 0, shoveFor = nil, outHx = nil, outHy = nil,
             bufHx = nil, bufHy = nil, inTicks = 0, inMark = nil, rideMark = 0, rideTicks = 0, reachHold = false,
             tc = nil, tcMark = nil, lh = nil, lt = nil, lc = nil, ln = nil,
             crawlers = nil, crawlTicks = 0, crawlMark = nil, steppedNow = false, stepFor = nil,
             hx = nil, hy = nil, heading = nil, turn = nil, crawlerD = nil, sinceChoose = K.WORK_TICKS,
             clearTicks = 0, pinId = nil, pileState = nil, pileTicks = 0, pileMark = 0, piles = 0,
             room = nil, roomTicks = 0 }
end

-- a work re-send while a work melee runs (Plan 37 Task 2: whatever the target; the header's): the footwork's state
-- kept, each press-count mark re-based on the new act's counts (the old mark less the old count: a press result not yet
-- read stays unread), the release's count while both ask it; at the same target (its sent id) the crawler pin, the
-- closing history and the faceR latch too; the new fields taken
local function keepState(work, st, args)
    local cur = K.cur
    if cur == nil or cur.type ~= "melee" or type(cur.st) ~= "table" or cur.st.work == nil then return end
    local o = cur.st
    local ow = o.work
    for i = 1, #KEEP do work[KEEP[i]] = ow[KEEP[i]] end
    local pc = o.swings + o.shoves + o.stomps + o.floors   -- the old act's presses (presses(o), defined below)
    for i = 1, #MARKS do
        local m = ow[MARKS[i]]
        if m ~= nil then work[MARKS[i]] = m - pc end
    end
    work.shoveMark = ow.shoveMark - o.shoves
    if ow.pileState == "step" then   -- fix 1 (x_trial-ladder-20261111-202744): the step out's heading kept too
        work.pileState, work.pileTicks = "step", ow.pileTicks
        work.outHx, work.outHy = ow.outHx, ow.outHy
    end
    if work.release and ow.release then work.releaseTicks = ow.releaseTicks end
    if args.targetId == o.id then
        work.pinId = ow.pinId
        st.hist, st.near = o.hist, o.near
    end
end

-- the args the melee's check reads: under a disposition with its own release radius a copy carrying it as releaseR
-- (a releaseR that is no positive number left for the check's bad args)
local function sentArgs(args, work)
    local r = work ~= nil and K.DISPOSITIONS[work.disposition].releaseR or nil
    if r == nil or type(args.releaseR) ~= "number" or args.releaseR <= 0 then return args end
    local a = {}
    for k, v in pairs(args) do a[k] = v end
    a.releaseR = r
    return a
end

local def = K.types.melee
local baseCheck = def.check
def.check = function(args, p)
    local work, bad = workArgs(args)
    if bad then return false, "bad args" end
    local ok, why, st = baseCheck(sentArgs(args, work), p)
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
    w.inContact, w.steppedNow, w.repinFor, w.shoveFor, w.stepNan = false, false, nil, nil, nil
    w.turnFor, w.stringing, w.stringWalked = nil, false, false   -- Plan 37 Task 2: the string's, this tick's
    if w.release then w.releaseTicks = (w.releaseTicks or -1) + 1 end   -- 0 on the first tick that reads it
    local a, b, c = baseTick(p, st)
    if w.inContact and st.strike == nil then w.contact = w.contact + 1 end
    if w.gaitRun and not w.stringWalked then K.workStringGait(p, w, false) end   -- no string walk: the run dropped
    return a, b, c
end

-- the crawlers within r of the player other than the target ({id, d, o, x, y[, fallen]} each, nearest first), or nil:
-- the last frame's records reading crawler within r + K.MELEE_CROWD_SLACK, each read live (dead, its position) through
-- S.zobj; Plan 37 Task 2 fix 3: and the fallen (a record reading onFloor, not crawler, isOnFloor read live) within
-- the lesser of r and K.CRAWLER_BITE_R, marked fallen
function K.crawlersNear(p, st, r)
    local S = PZA.sense
    local f = S ~= nil and S.last or nil
    local objs = S ~= nil and S.zobj or nil
    local recs = f ~= nil and f.zombies or nil
    if recs == nil or objs == nil or st.px == nil then return nil end
    local out = nil
    for i = 1, #recs do
        local rec = recs[i]
        local crawl = rec.crawler == true
        local lim = r
        if not crawl and lim > K.CRAWLER_BITE_R then lim = K.CRAWLER_BITE_R end   -- fix 3: a fallen one at the feet
        if (crawl or rec.onFloor == true) and rec.id ~= st.id and type(rec.dist) == "number"
           and rec.dist < lim + K.MELEE_CROWD_SLACK then
            local o = objs[rec.id]
            if o ~= nil and not K.zombieDead(o) and (crawl or K.onFloor(o)) then
                local x, y = posOf(o)
                if x ~= nil and y ~= nil then
                    local ex, ey = x - st.px, y - st.py
                    local d = math.sqrt(ex * ex + ey * ey)
                    if d < lim then
                        out = out or {}
                        out[#out + 1] = { id = rec.id, d = d, o = o, x = x, y = y, fallen = not crawl }
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

-- whether the unit heading (hx, hy) is clear (the header's rule): the room ring's nearest heading reads at least
-- K.WORK_ROOM_NEED tiles clear (Plan 36 Task 1: the ring's one probe read, no square read here), then no crawler and
-- no fallen zombie at a K.WORK_PROBE point along the heading itself
local function headingClear(ctx, w, hx, hy)
    if K.workRoomOpen(ctx.ring, hx, hy) < K.WORK_ROOM_NEED then return false end
    for i = 1, #K.WORK_PROBE do
        local r = K.WORK_PROBE[i]
        local x, y = ctx.px + hx * r, ctx.py + hy * r
        local cs = ctx.crawlers
        if cs ~= nil then   -- fix 5: a crawler vetoes a point within crawlerR of it only when no farther than now
            for j = 1, #cs do
                local ex, ey = cs[j].x - x, cs[j].y - y
                local e2 = ex * ex + ey * ey
                if e2 < w.crawlerR * w.crawlerR and e2 <= cs[j].d * cs[j].d then return false end
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

-- the unit (bx, by) turned by K.WORK_TURNS in order to the first clear heading (headingClear, the crawlers cs and the
-- fallen fl), into w: hx, hy, heading, turn and clear true; w untouched with none clear
local function turnClear(p, st, bx, by, cs, fl)
    local w = st.work
    local _, pz = PZA.call(p, "getZ")
    local ctx = { px = st.px, py = st.py, ring = K.workRoomFor(p, st, st.px, st.py, pz), crawlers = cs, fallen = fl }
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

-- Plan 37 Task 2 fix 3: the fallen zombie of record rec (its object o) repels the sum s at K.WORK_CRAWLER_W within
-- K.CRAWLER_BUFFER_R, read live (not dead, isOnFloor, its position); not when the crawlers cs already hold it
local function repelFallen(s, st, rec, o, cs)
    if o == nil or rec.dist >= K.CRAWLER_BUFFER_R + K.MELEE_CROWD_SLACK then return end
    if cs ~= nil then
        for i = 1, #cs do
            if cs[i].id == rec.id then return end
        end
    end
    if K.zombieDead(o) or not K.onFloor(o) then return end
    local x, y = posOf(o)
    if x == nil or y == nil then return end
    local ex, ey = x - st.px, y - st.py
    if ex * ex + ey * ey >= K.CRAWLER_BUFFER_R * K.CRAWLER_BUFFER_R then return end
    repel(s, st.px, st.py, x, y, K.WORK_CRAWLER_W)
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
    local cs = w.crawlers   -- fix 5: this tick's read (K.workTick), crawlerR x 2, the leaf's crawler refreshed there
    if recs ~= nil and objs ~= nil then
        for i = 1, #recs do
            local rec = recs[i]
            if rec.id ~= st.id and type(rec.dist) == "number" and rec.crawler ~= true then
                if rec.onFloor == true then
                    if type(rec.x) == "number" and type(rec.y) == "number" and rec.dist < w.workR + K.MELEE_CROWD_SLACK then
                        fl[#fl + 1] = { x = rec.x, y = rec.y }
                    end
                    repelFallen(s, st, rec, objs[rec.id], cs)   -- Plan 37 Task 2 fix 3
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
    if cs ~= nil then
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
    w.hx, w.hy, w.heading, w.turn, w.clear, w.nanHeading = nil, nil, nil, nil, false, nil
    if len ~= len or len == math.huge then   -- fix 1: a non-finite sum (NaN or infinite) is no heading: cornered
        w.nanHeading = true
        return
    end
    if len <= 0 then return end
    turnClear(p, st, s.x / len, s.y / len, cs, fl)
end

-- the step along the heading (chosen when due): kind, or cornered with none clear (the walk stopped)
local function stepAlong(p, st, kind, fallen, why)
    local w = st.work
    if w.sinceChoose >= K.WORK_TICKS then choose(p, st, fallen) end
    w.steppedNow, w.stepFor, w.held = true, why, nil   -- fix 5: the leaf's step_for, its heading this tick's
    w.lh, w.lt, w.lc, w.ln = w.heading, w.turn, w.clear, w.n
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

-- whether v is a finite number (not nil, not NaN, not infinite)
local function finite(v)
    return type(v) == "number" and v == v and v ~= math.huge and v ~= -math.huge
end

-- Plan 36 Task 2b: a step along the unit heading (hx, hy) chosen by its rule (the pile's step out, the crawler buffer),
-- the body held on (fx, fy) when given: the stance's force-aim held, the auto-walk of kind work (held through a press
-- with backswing); the leaf's heading this tick's, no turn and no n. Fix 1: a heading not finite (nil, NaN or
-- infinite) is no step: nil, the leaf's nan_heading on this tick's line (w.stepNan), the caller's next rule
local function stepTo(p, st, hx, hy, why, fx, fy)
    local w = st.work
    if not finite(hx) or not finite(hy) or (hx == 0 and hy == 0) then
        w.stepNan = true
        return nil
    end
    w.steppedNow, w.stepFor, w.held = true, why, nil
    w.lh, w.lt, w.lc, w.ln = math.atan2(hy, hx) * DEG, nil, true, nil
    if fx ~= nil and fy ~= nil then K.FACING.hold(p, st, K.FACING.bearing(st.px, st.py, fx, fy)) end
    aimHeld(p)
    M.walkAlong(p, st, "work", hx, hy)
    return "work"
end

-- the room ring's most open heading within 90 degrees of the unit (ax, ay), ties to the nearest it, reading at least
-- K.WORK_ROOM_NEED: hx, hy, else nil
local function openToward(p, st, ax, ay)
    local _, pz = PZA.call(p, "getZ")
    local ring = K.workRoomFor(p, st, st.px, st.py, pz)
    local bx, by, bh, bc = nil, nil, nil, nil
    for i = 1, #K.WORK_ROOM_HEADINGS do
        local a = K.WORK_ROOM_HEADINGS[i] * RAD
        local hx, hy = math.cos(a), math.sin(a)
        local c = hx * ax + hy * ay
        local h = K.workRoomOpen(ring, hx, hy)
        if c >= 0 and h >= K.WORK_ROOM_NEED and (bh == nil or h > bh or (h == bh and c > bc)) then
            bx, by, bh, bc = hx, hy, h, c
        end
    end
    return bx, by
end

-- the predicted distance at the next swing's landing of a zombie at gap g (Plan 36 Task 2b item 4): g less the
-- target's closing speed (the melee's closingOf; 0 for another zombie, whose history is not kept), times the swing's
-- flight time (one update plus K.MELEE_HIT_FRAC / CombatSpeed, read once a press: w.tc); under backswing (the walk
-- held through the press, so the player keeps moving through the flight) plus the player's own speed away times the
-- flight time: while the step walks st.backV (K.meleeTrack), kept as w.walkV, which a standing tick reads, so the
-- step starts only where it may go on (no step-and-stop at the edge). Without backswing the press stops the walk on
-- its tick and the player's own speed is no term
function K.workLanding(p, st, g, gid)
    local w = st.work
    if w.tc == nil then w.tc = st.dtS + K.MELEE_HIT_FRAC / M.combatSpeed(p) end
    local v = 0
    if gid == st.id then v = M.closingOf(st, st.px, st.py, st.zx, st.zy, g) or 0 end
    local back = 0
    if w.backswing then
        if st.walk == "work" and (st.backV or 0) > 0 then w.walkV = st.backV end
        back = w.walkV or 0
    end
    return g - v * w.tc + back * w.tc
end

-- fix 3 (x_trial-ladder-20261110-091352, the drag-down death at frame 1420): the engine's attackers count, the last
-- frame's me.attackers, else getSurroundingAttackingZombies live; 0 unread (since Plan 36 Task 2b the attacker's
-- facing's gate, attackerTick)
local function attackersOf(p)
    local S = PZA.sense
    local f = S ~= nil and S.last or nil
    local a = f ~= nil and type(f.me) == "table" and f.me.attackers or nil
    if type(a) == "number" then return a end
    local ok, v = PZA.call(p, "getSurroundingAttackingZombies")
    if ok and type(v) == "number" then return v end
    return 0
end

-- the standing zombies within r ({id, d, o[, x, y]} each, nearest first), the target first counted while it stands
-- (its position this tick's), the rest from K.meleeCrowd's read (w.near)
local function standingWithin(st, d, standing, r)
    local out = {}
    if standing and d < r then out[1] = { id = st.id, d = d, o = st.z, x = st.zx, y = st.zy } end
    local near = st.work.near
    if near ~= nil then
        for i = 1, #near do
            if near[i].d < r then out[#out + 1] = near[i] end
        end
    end
    if #out > 1 then table.sort(out, function(a, b) return a.d < b.d end) end
    return out
end

-- the step out's heading (7b): the ring's most open within 90 degrees of the way away from the centroid of zs (each
-- {x, y} or {o}, and since Plan 37 Task 2 fix 3 its weight wt, 1 when absent); nil with none, or with nothing to step
-- from
local function outHeading(p, st, zs)
    local cx, cy, n = 0, 0, 0
    for i = 1, #zs do
        local x, y = zs[i].x, zs[i].y
        if x == nil and zs[i].o ~= nil then x, y = posOf(zs[i].o) end
        local wt = zs[i].wt or 1
        if x ~= nil and y ~= nil then cx, cy, n = cx + x * wt, cy + y * wt, n + wt end
    end
    if n == 0 then return nil end
    local ax, ay = st.px - cx / n, st.py - cy / n
    local len = math.sqrt(ax * ax + ay * ay)
    if len ~= len or len <= 0 then return nil end
    return openToward(p, st, ax / len, ay / len)
end

-- the pile (the header's tick, 1): the step out, then the meet's press; a step or a press, else nil to go on
local function pileTick(p, st, d, fallen, standing)
    local w = st.work
    if w.pileState == "step" then
        if w.pileTicks < K.WORK_STEP_TICKS then
            w.pileTicks = w.pileTicks + 1
            local fx, fy = st.zx, st.zy
            if w.nearO ~= nil and w.nearId ~= st.id then fx, fy = posOf(w.nearO) end
            local step = stepTo(p, st, w.outHx, w.outHy, "pile_out", fx, fy)
            if step ~= nil then return step end
            w.pileTicks = K.WORK_STEP_TICKS   -- fix 1: no finite heading: the step ends into the press window
        end
        w.pileState, w.pileMark, w.pileWait = "press", presses(st), 0
        return nil
    end
    if w.pileState == "press" then
        w.pileWait = w.pileWait + 1
        if presses(st) == w.pileMark and w.pileWait < K.WORK_STEP_TICKS then return nil end
        w.pileState = nil
    end
    local pb = standingWithin(st, d, standing, K.WORK_POINT_BLANK_R)
    local why = nil
    if st.shoves ~= w.shoveMark then w.shoveMark, why = st.shoves, "shove" end   -- (a): a shove's result
    if why == nil and #pb >= 2 then why = "pile_out" end                       -- (b): two at point blank
    if why ~= nil then
        local zs = {}
        for i = 1, #pb do zs[i] = pb[i] end
        if why == "shove" and not standing then   -- fix 3: the one the shove knocked down repels too
            zs[#zs + 1] = { x = st.zx, y = st.zy, wt = K.WORK_CRAWLER_W }
        end
        if #zs == 0 then zs = { { x = st.zx, y = st.zy } } end
        w.outHx, w.outHy = outHeading(p, st, zs)
        if w.outHx == nil then return nil end   -- no way out: the meet presses (cornered)
        w.pileState, w.pileTicks, w.piles, w.pileWhy = "step", 0, w.piles + 1, why
        return pileTick(p, st, d, fallen, standing)
    end
    if fallen or not standing or #pb ~= 1 or pb[1].d > st.shoveR then return nil end
    if not K.DISPOSITIONS[w.disposition].knockdown then return nil end   -- Plan 37 Task 2 fix 1: off under string
    local inReach = standingWithin(st, d, standing, M.reachOf(p, st))   -- a Lua table
    if #inReach < 2 then return nil end   -- (c): against several only
    if pb[1].id ~= st.id then
        if pb[1].id == w.stallId then return nil end
        return M.repin(p, st, pb[1])
    end
    local off = M.lookOff(p, st.px, st.py, st.zx, st.zy)
    local step, pwhy = M.press(p, st, "shove", d, d, off, "face", d)
    if step == "shove" then w.shoveFor = "knockdown" end
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
-- K.WORK_POINT_BLANK_R) or attack (its getRealState so reading; one call). The reason is kept in w.held for the leaf,
-- cleared when a step goes. Fix 4 (the controller's ruling on fix 3's concern 1): no lunge hold; live, `lunge` is every
-- chaser's state at any distance (x_trial-ladder-20261110-091352: 0.6 to 2.5 tiles), so it held the whole band
local function stepHeld(w, g)
    if g ~= nil and g < K.WORK_POINT_BLANK_R then return "point_blank" end
    local o = w.nearO
    if o == nil then return nil end
    local ok, state = PZA.call(o, "getRealState")
    if not ok or type(state) ~= "string" then return nil end
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
    if not standing or g == nil or g >= M.reachOf(p, st) - w.bandLo
       or K.workLanding(p, st, g, w.nearId) > M.reachOf(p, st) then   -- Plan 36 Task 2b item 4: the next landing
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
    local step = stepAlong(p, st, "work", false, "gap")
    if step == "cornered" then
        w.stepTicks = 0
        return nil
    end
    return step
end

-- fix 5 (x_trial-ladder-20261110-103609, a56 and a57: the crawler 29707 lay at 0.16 to 0.18 tiles, never the target,
-- and bit first at 1.02): the crawlers within crawlerR x 2 read every tick (w.crawlers, the leaf's crawler). Plan 36
-- Task 2b (item 7, the spec's section 3.5; fix 5's stomp-first inside the shove range re-read: the buffer first unless
-- the crawler is already inside its bite reach): the header's tick, 2

-- the buffer step's heading: perpendicular to the crawler c's bearing, the side the ring reads more open (ties to the
-- side away from the target), reading at least K.WORK_ROOM_NEED; nil otherwise
local function bufferHeading(p, st, c)
    local ux, uy = c.x - st.px, c.y - st.py
    local len = math.sqrt(ux * ux + uy * uy)
    if len ~= len or len <= 0 then return nil end
    ux, uy = ux / len, uy / len
    local _, pz = PZA.call(p, "getZ")
    local ring = K.workRoomFor(p, st, st.px, st.py, pz)
    local ax, ay, bx, by = -uy, ux, uy, -ux
    local ha, hb = K.workRoomOpen(ring, ax, ay), K.workRoomOpen(ring, bx, by)
    local pickB = hb > ha
    if ha == hb then
        local tx, ty = st.px - st.zx, st.py - st.zy
        pickB = bx * tx + by * ty > ax * tx + ay * ty
    end
    if pickB then ax, ay, ha = bx, by, hb end
    if ha < K.WORK_ROOM_NEED then return nil end
    return ax, ay
end

-- fix 1: the buffer with no open side: the crawler inside its bite reach is stomped (the re-pin, whatever stands
-- near: no step can take the character off it; w.noSideStomp holds the pin against the attacker's re-pin and the
-- finish's standing re-pin until the next press or another target), else nil (the next rule)
local function crawlerNoSide(p, st, c)
    if c.d >= K.CRAWLER_BITE_R then return nil end
    local w = st.work
    local step = M.repin(p, st, c)
    w.pinId, w.nearId, w.sinceChoose, w.crawlTicks = c.id, nil, K.WORK_TICKS, 0
    w.noSideStomp, w.noSideMark = c.id, presses(st)
    return step
end

local function crawlerTick(p, st, standing, g)
    local w = st.work
    local cs = K.crawlersNear(p, st, w.crawlerR * 2)
    w.crawlers = cs
    w.crawlerD = nil
    if cs ~= nil then w.crawlerD = cs[1].d end
    if cs == nil or cs[1].d >= K.CRAWLER_BUFFER_R or not standing then
        w.crawlTicks = 0
        return cs, nil
    end
    local c = cs[1]
    if c.d < K.CRAWLER_BITE_R and not c.fallen and (g == nil or g >= K.MELEE_CROWD_R) then   -- inside its bite, nothing
        -- standing near (fix 3: a fallen zombie takes the buffer step, never the stomp first: it stands again)
        local step = M.repin(p, st, c)
        w.pinId, w.nearId, w.sinceChoose, w.crawlTicks = c.id, nil, K.WORK_TICKS, 0
        return cs, step
    end
    if w.crawlTicks <= 0 then
        if w.crawlMark == presses(st) then return cs, nil end   -- one buffer step a press
        local hx, hy = bufferHeading(p, st, c)
        if hx == nil then return cs, crawlerNoSide(p, st, c) end   -- fix 1: no open side
        w.crawlTicks, w.crawlMark, w.bufHx, w.bufHy = K.WORK_STEP_TICKS, presses(st), hx, hy
    end
    w.crawlTicks = w.crawlTicks - 1
    local step = stepTo(p, st, w.bufHx, w.bufHy, "crawler_buffer", st.zx, st.zy)
    if step == nil then   -- fix 1: no finite heading: the buffer ends, as with no open side
        w.crawlTicks = 0
        return cs, crawlerNoSide(p, st, c)
    end
    return cs, step
end

-- the nearest attacker's facing (the header's tick, 3; item 6): a re-pin, else nil
local function attackerTick(p, st, d, standing, g)
    local w = st.work
    if g == nil or g >= K.WORK_POINT_BLANK_R or w.noSideStomp == st.id then return nil end   -- fix 1: the held stomp
    local pb = standingWithin(st, d, standing, K.WORK_POINT_BLANK_R)
    if #pb == 0 then return nil end
    local pick, attacking = nil, false
    if attackersOf(p) > 0 then
        for i = 1, #pb do
            local ok, state = PZA.call(pb[i].o, "getRealState")
            if ok and type(state) == "string" and string.find(state, "attack") ~= nil then
                pick, attacking = pb[i], true
                if pb[i].id == st.id then return nil end   -- the target attacking: kept
                break
            end
        end
    end
    if pick == nil then pick = pb[1] end
    if pick.id == st.id or pick.id == w.stallId then return nil end
    if not attacking and standing and pick.d >= d - K.MELEE_REPIN_SLACK then return nil end
    w.repinFor = "attacker"
    return M.repin(p, st, pick)
end

-- the stagger in (the header's tick, 4; item 4): a step, else nil
local function staggerIn(p, st, standing, g, gid)
    local w = st.work
    local reach = M.reachOf(p, st)
    if not standing or gid ~= st.id or g == nil or g <= reach or g > reach + K.WORK_STAGGER_R then
        w.inTicks = 0
        return nil
    end
    if w.inTicks <= 0 then
        if w.inMark == presses(st) then return nil end   -- one step in a press
        local ok, state = PZA.call(st.z, "getRealState")
        if not ok or type(state) ~= "string" then return nil end
        if string.find(state, "stagger") == nil and string.find(state, "hitreact") == nil then return nil end
        w.inTicks, w.inMark = K.WORK_STEP_TICKS, presses(st)
    end
    local ex, ey = st.zx - st.px, st.zy - st.py
    if not finite(ex) or not finite(ey) or (ex == 0 and ey == 0) then   -- fix 1: no finite heading, no step in
        w.inTicks, w.stepNan = 0, true
        return nil
    end
    w.inTicks = w.inTicks - 1
    w.steppedNow, w.stepFor, w.held = true, "stagger_in", nil
    w.lh, w.lt, w.lc, w.ln = math.atan2(ey, ex) * DEG, nil, true, nil
    K.FACING.hold(p, st, K.FACING.bearing(st.px, st.py, st.zx, st.zy))
    aimHeld(p)
    M.walkAlong(p, st, "in", ex, ey)
    return "work"
end

-- fix 6 (the controller's ruling, Angus's fighting retreat; x_trial-ladder-20261110-104702: four standing at 1.0 to
-- 1.4 tiles for 60 frames while the character stood shoving at pace 0, the planner's withdraw vector sent on 12 lines
-- and used only in the band step's window, then the drag-down): with a withdraw vector given and a standing zombie
-- read (the target or the near read's), the retreat runs: the step along the heading (the repulsion sum plus the
-- withdraw bias) is the default, ungated by the point-blank and attack holds, the body snapped on the nearest standing
-- zombie, step_for retreat; the press is the exception, when the nearest standing zombie is within the reach and
-- closing (the meet's closing read) or inside MinRange (the protective shove): nil, and the meet presses (re-pinned
-- to the nearest first when it is not the target); the step resumes at the press's result. With no clear heading the
-- meet presses, its idle reading cornered. The crawler (fix 5) goes first; the pile and the band step do not run
local function retreatSnap(p, st, gid)
    local w = st.work
    local x, y = st.zx, st.zy
    if gid ~= st.id and w.nearO ~= nil then x, y = posOf(w.nearO) end
    K.FACING.hold(p, st, K.FACING.bearing(st.px, st.py, x, y))
end

-- whether the disposition runs the retreat (K.DISPOSITIONS' retreat: given, always or never)
local function retreatOn(w)
    local mode = K.DISPOSITIONS[w.disposition].retreat
    return mode == "always" or (mode == "given" and w.retreat)
end

local function retreatTick(p, st, d, standing, g, gid)
    local w = st.work
    w.retreating, w.reachHold = false, false
    if not retreatOn(w) or g == nil then return nil end
    w.retreating = true
    local pc = presses(st)
    if pc ~= w.rideMark then w.rideMark, w.rideTicks = pc, K.WORK_RIDE_TICKS end   -- a press's result: the step rides
    local reach = M.reachOf(p, st)
    local hold = K.workLanding(p, st, g, gid) > reach - K.WORK_EDGE_SLACK   -- item 4: no back step past the next landing
    w.reachHold = hold   -- the idle's (K.footwork) hold too, on a press window the meet leaves unpressed
    if hold then w.held = "reach" end
    if g <= reach and w.rideTicks <= 0 then   -- the press window: at whoever stands nearest inside the reach
        local near = w.near
        if gid ~= st.id and near ~= nil and near[1].id == gid and gid ~= w.stallId then return M.repin(p, st, near[1]) end
        if standing then return nil end   -- the meet's swing on the back step (inside MinRange its protective shove)
    end
    if hold then
        M.stopWalk(p, st)
        return nil
    end
    w.rideTicks = w.rideTicks - 1
    retreatSnap(p, st, gid)
    local step = stepAlong(p, st, "work", false, "retreat")
    if step == "cornered" then return nil end   -- the meet presses; its idle reads cornered
    return step
end

-- the footwork's tick (the header's): the floor, the gap and contact, clear, the pile; a step or an end, else nil
function K.workTick(p, st, d, crowd, fallen, now)
    local w = st.work
    w.sinceChoose, w.roomTicks = w.sinceChoose + 1, w.roomTicks + 1
    local fh, fhow, fres = K.workFloor(p, st)
    if fh ~= nil then return fh, fhow, fres end
    local standing = not fallen and not st.knocked   -- fix 1: a target the press knocked down is no standing zombie
    if w.release then   -- Plan 37 Task 2: the release, before anything else but the floor
        local rs, rhow, rres = K.workRelease(p, st, d, standing, w.near)
        if rs ~= nil then return rs, rhow, rres end
    end
    if st.nothing >= st.stall then   -- fix 7: the stall re-read every tick (deferred in shove range, K.meleeStall)
        local ss, sh, sr = K.meleeStall(p, st, d)
        if ss ~= nil then return ss, sh, sr end
    else
        st.stallHeld = false
    end
    local g, gid = nil, nil
    if standing then g, gid, w.nearO = d, st.id, st.z end
    local near = w.near
    if near ~= nil and (g == nil or near[1].d < g) then g, gid, w.nearO = near[1].d, near[1].id, near[1].o end
    if g == nil then w.nearO = nil end
    w.gap = g
    if gid ~= w.nearId then w.nearId, w.sinceChoose = gid, K.WORK_TICKS end
    w.inContact = g ~= nil and g < K.WORK_CONTACT_R
    local pb = standingWithin(st, d, standing, K.WORK_POINT_BLANK_R)   -- a Lua table
    w.pinned = #pb >= 2   -- Plan 37 Task 2: the leaf's pinned
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
    local pc = presses(st)
    if pc ~= w.tcMark then w.tcMark, w.tc = pc, nil end   -- the flight time read again once a press
    if w.noSideStomp ~= nil and (w.noSideStomp ~= st.id or pc ~= w.noSideMark) then w.noSideStomp = nil end   -- fix 1
    if w.pile then   -- 1: the pile
        local ps, phow, pres = pileTick(p, st, d, fallen, standing)
        if ps ~= nil then return ps, phow, pres end
    end
    local cs, cstep = crawlerTick(p, st, standing, g)   -- 2: the crawler buffer
    if cstep ~= nil then return cstep end
    local as = attackerTick(p, st, d, standing, g)   -- 3: the nearest attacker
    if as ~= nil then return as end
    local disp = K.DISPOSITIONS[w.disposition]
    if disp.staggerIn then
        local ss = staggerIn(p, st, standing, g, gid)   -- 4: the stagger in
        if ss ~= nil then return ss end
    end
    if disp.string then   -- 4b: the string (Plan 37 Task 2)
        local ws, whow, wres = K.workString(p, st, d, standing, fallen)
        if ws ~= nil then return ws, whow, wres end
        if w.stringing then return nil end   -- the turn (or no clear heading): the meet presses
    end
    local rs, rhow, rres = retreatTick(p, st, d, standing, g, gid)   -- 5: the fighting retreat
    if rs ~= nil then return rs, rhow, rres end
    if w.retreating then return nil end   -- the press due, or the step withheld: the meet's
    return pressStep(p, st, standing, g)   -- 6: the band step
end

-- the idle (the meet would stand or face): the step inside the band, else the meet's own (the crawler target is
-- K.workTick's since fix 5)
function K.footwork(p, st, d, px, py, zx, zy, now)
    local w = st.work
    if w.stringing then   -- Plan 37 Task 2: the string's turn: no step, the meet's stand or face until its press
        M.stopWalk(p, st)
        if st.near then return "face" end
        return "stand"
    end
    if w.retreating then   -- fix 6: the meet pressed nothing: the retreat's step (cornered with no clear heading)
        if w.reachHold then   -- Plan 36 Task 2b: the step withheld past the next landing: the hold
            M.stopWalk(p, st)
            if st.near then return "face" end
            return "stand"
        end
        retreatSnap(p, st, w.nearId)
        return stepAlong(p, st, "work", false, "retreat")
    end
    local reach = M.reachOf(p, st)
    if w.gap ~= nil and w.gap < reach - w.bandLo and K.workLanding(p, st, w.gap, w.nearId) <= reach then
        local held = stepHeld(w, w.gap)   -- fixes 2 and 4: no step at point blank or into an attack
        if held == nil then
            w.held = nil
            return stepAlong(p, st, "work", false, "gap")
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
    local leaf = { gap = w.gap, crawler = w.crawlerD, held = w.held, pile = w.pileWhy,
                   disposition = w.disposition, pinned = w.pinned, turn_for = w.turnFor }   -- Plan 37 Task 2
    if w.retreating then leaf.retreat = true end   -- fix 6: the retreat's mode running
    if st.stallHeld then leaf.stall_held = true end   -- fix 7: the stall deferred in shove range
    leaf.repin_for = w.repinFor   -- fix 7b: the stall's re-pin, on its own tick's line
    leaf.shove_for = w.shoveFor   -- Plan 36 Task 2b: the chosen knock-down, on its press's line
    if w.steppedNow then   -- fix 5: the heading, its turn, clear and n of the step this tick, absent on any other
        leaf.heading, leaf.turn, leaf.clear, leaf.n, leaf.step_for = w.lh, w.lt, w.lc, w.ln, w.stepFor
        if w.nanHeading then leaf.nan_heading = true end   -- fix 1: the sum read non-finite
    end
    if w.stepNan then   -- Plan 36 Task 2 fix 1: a step rule's heading read non-finite (stepTo's guard), this tick's
        leaf.nan_heading = true
    end
    out.work = leaf
end

-- ---- the room ring (PZA/1.14, Plan 36 Task 1; the spec `2026-11-11-plan-36-the-engagement-design.md` section 3.1) ----
-- The frames could not see a solid square behind the body (F21's three engagement bites, a solid square 123 to 177
-- degrees off the body within 2 tiles). The ring is the one probe read the footwork's turns and the frame's me.room
-- share: for each of K.WORK_ROOM_HEADINGS, degrees from the world's +x in atan2(y, x)'s convention (me.fwdAngle's and
-- Vector2.getDirection's, in degrees: 90 is the world's +y), the clear tiles along it, 0.0 to K.WORK_ROOM_MAX in
-- K.WORK_ROOM_STEP steps, and the stop's kind. Walking out from the player's position a step at a time, a point on the
-- square already reached is clear; a point on a new square crosses the edge from the last square reached, and that
-- edge stops the heading:
--   wall: the new square unreadable (absent, not loaded), isSolid or isSolidTrans not false, or isBlockedTo from the
--     last square not false with no door on the edge (a read that fails reads as wall);
--   hop: a crossed x edge whose eastern square has IsoFlagType.HoppableW, or a crossed y edge whose southern square has
--     HoppableN (the flags the Map's hopN and hopW read; the stance cannot climb, #4289; a failed has read reads wall);
--   door: isBlockedTo not false with a door on the edge, the last square's getDoorTo(new square) (the 42.22.2 jar:
--     IsoGridSquare.getDoorTo(IsoGridSquare) @0 L3640, the edge element between the two squares that is a door: a
--     closed door blocks, an open one does not and reads clear); where getDoorTo is absent (PZA.call's index check), a
--     door object (W.kindOf) on either square;
--   open: K.WORK_ROOM_MAX reached clear.
-- The clear tiles are the farthest step reached before the stop (a wall whose square the 1.5 step first enters reads
-- 1.0). Each square's solid reads and each edge's verdict are read once a ring (its context's caches). The ring is kept
-- twice: in the melee's work state (K.workRoomFor, at a choose: read again when the player's square changed or after
-- K.WORK_TICKS of the melee's ticks, fix 1's budget ruling) and in K.room (the last ring read by any caller), which the frame reuses on
-- the same square within K.WORK_ROOM_TICKS client ticks (K.workRoomNow). The cost (test_lua_footwork.py counts it):
-- getZ and the two positions when the caller passes none; getGridSquare once a square (the player's own included),
-- isSolid and isSolidTrans once a square entered (isSolidTrans only when isSolid reads false); per edge crossed into an
-- open square one has per crossed axis and isBlockedTo; getDoorTo at a blocked edge.
K.WORK_ROOM_HEADINGS = { 0, 45, 90, 135, 180, 225, 270, 315 }   -- degrees from the world's +x, atan2(y, x)'s
K.WORK_ROOM_STEP = 0.5       -- tiles between the points read along a heading (the spec's 0.5 steps)
K.WORK_ROOM_MAX = 3.0        -- tiles: the farthest point read (the spec's 0.0 to 3.0)
K.WORK_ROOM_TICKS = 3        -- client ticks the frame reuses a ring on one square (the spec's refresh); the melee's
                             -- ring is reused K.WORK_TICKS (fix 1: the controller's budget ruling, one ring a re-choose)
K.WORK_ROOM_NEED = 1.0       -- tiles: a turn's heading is clear when its ring heading reads this far (K.WORK_PROBE's
                             -- farthest point, the distance Plan 35's probe read)
K.roomReads = 0              -- the rings read so far (the cache's falsifier in test_lua_footwork.py)

local ROOM_SCRATCH = {}

-- the crossed edge's flag kind: hop when the square has flag name, wall when the read fails, nil otherwise (an absent
-- flag constant reads nil, as Plan 35's probe read it)
local function hopKind(sq, name)
    local flag = IsoFlagType ~= nil and IsoFlagType[name] or nil
    if flag == nil then return nil end
    local ok, v = PZA.call(sq, "has", flag)
    if not ok then return "wall" end
    if v == true then return "hop" end
    return nil
end

-- a blocked edge's kind: door when a door sits between squares a and b, else wall
local function doorKind(a, b)
    local ok, d = PZA.call(a, "getDoorTo", b)
    if ok then
        if d ~= nil then return "door" end
        return "wall"
    end
    local sqs = { a, b }
    for i = 1, 2 do
        local objs, n = W.objectsOn(sqs[i], ROOM_SCRATCH)
        for j = 1, n do
            if W.kindOf(objs[j]) == "door" then return "door" end
        end
    end
    return "wall"
end

-- the square (sx, sy) on the ring's floor, read once a ring: {sq} (nil sq: unreadable)
local function roomSquare(ctx, sx, sy)
    local key = sx * 100000 + sy
    local e = ctx.sqs[key]
    if e ~= nil then return e end
    e = { sq = K.squareAt(sx, sy, ctx.pz) }
    ctx.sqs[key] = e
    return e
end

-- whether the square read e is open (readable, neither isSolid nor isSolidTrans), read once a ring, only for a square
-- entered (the player's own and a square left are never read for it)
local function roomOpen(e)
    if e.open == nil then
        e.open = false
        if e.sq ~= nil then
            local okS, solid = PZA.call(e.sq, "isSolid")
            if okS and solid == false then
                local okT, trans = PZA.call(e.sq, "isSolidTrans")
                e.open = okT and trans == false
            end
        end
    end
    return e.open
end

-- the edge from square (fx, fy) to its neighbour (tx, ty): its stop's kind, or false when it is crossed clear
local function roomEdge(ctx, fx, fy, tx, ty)
    local key = (fx * 100000 + fy) * 9 + (tx - fx + 1) * 3 + (ty - fy + 1)
    local v = ctx.edges[key]
    if v ~= nil then return v end
    local f, t = roomSquare(ctx, fx, fy), roomSquare(ctx, tx, ty)
    local stop = false
    if f.sq == nil or t.sq == nil or not roomOpen(t) then
        stop = "wall"
    else
        if tx ~= fx then
            local east = f.sq
            if tx > fx then east = t.sq end
            stop = hopKind(east, "HoppableW") or false
        end
        if not stop and ty ~= fy then
            local south = f.sq
            if ty > fy then south = t.sq end
            stop = hopKind(south, "HoppableN") or false
        end
        if not stop then
            local okB, blocked = PZA.call(f.sq, "isBlockedTo", t.sq)
            if not okB or blocked ~= false then stop = doorKind(f.sq, t.sq) end
        end
    end
    ctx.edges[key] = stop
    return stop
end

-- a ring's read context at the player's position (px, py) on floor pz: the caches its headings share
local function roomCtx(px, py, pz)
    return { px = px, py = py, pz = pz, psx = math.floor(px), psy = math.floor(py), sqs = {}, edges = {} }
end

-- the player's position and floor, each nil when unread
local function playerAt(p)
    local px, py = posOf(p)
    local _, pz = PZA.call(p, "getZ")
    return px, py, pz
end

-- the clear tiles along heading (degrees, the ring's convention) up to maxTiles in K.WORK_ROOM_STEP steps, and the
-- stop's kind (wall, hop, door or open); ctx a ring's shared read context, else one made here off the player
function K.workClearAlong(p, heading, maxTiles, ctx)
    if ctx == nil then
        local px, py, pz = playerAt(p)
        if px == nil or py == nil then return 0, "wall" end
        ctx = roomCtx(px, py, pz)
    end
    local a = heading * RAD
    local hx, hy = math.cos(a), math.sin(a)
    if math.abs(hx) < 1e-9 then hx = 0 end   -- a cardinal heading exactly on its axis
    if math.abs(hy) < 1e-9 then hy = 0 end
    local fx, fy = ctx.psx, ctx.psy
    local clear = 0
    local n = math.floor(maxTiles / K.WORK_ROOM_STEP + 1e-9)
    for i = 1, n do
        local r = i * K.WORK_ROOM_STEP
        local sx, sy = math.floor(ctx.px + hx * r), math.floor(ctx.py + hy * r)
        if sx ~= fx or sy ~= fy then
            local stop = roomEdge(ctx, fx, fy, sx, sy)
            if stop then return clear, stop end
            fx, fy = sx, sy
        end
        clear = r
    end
    return clear, "open"
end

-- the ring read now at the player's position (px, py and pz when the caller holds them, else read): {h, stop, tick,
-- sx, sy, z}, h[i] and stop[i] K.workClearAlong's for K.WORK_ROOM_HEADINGS[i], tick the client tick (PZA.tick) it was
-- read on, (sx, sy, z) the player's square; nil when the position is unread. Kept in K.room
function K.workRoom(p, px, py, pz)
    if px == nil or py == nil then px, py, pz = playerAt(p) end
    if px == nil or py == nil then return nil end
    local ctx = roomCtx(px, py, pz)
    local h, stop = {}, {}
    for i = 1, #K.WORK_ROOM_HEADINGS do
        h[i], stop[i] = K.workClearAlong(p, K.WORK_ROOM_HEADINGS[i], K.WORK_ROOM_MAX, ctx)
    end
    K.roomReads = K.roomReads + 1
    local ring = { h = h, stop = stop, tick = PZA.tick or 0, sx = ctx.psx, sy = ctx.psy, z = pz }
    K.room = ring
    return ring
end

-- the ring's index (1 to 8) of the heading nearest the vector (hx, hy), a tie taken by the larger angle; nil for a
-- non-finite vector. Fix 1 (x_trial-ladder-20261111-175926, the client parked at `__lt not defined for operand` in
-- headingClear: the away heading from a zombie south-east of the player read atan2 -164.7 degrees): no % on a negative
-- dividend, since Kahlua's % truncates (the 42.22.2 jar: KahluaThread.primitiveMath @111-@127 L1355-L1356, a - (int)(a /
-- b) * b) where Lua 5.1's floors, so -164.7 % 360 read -164.7 and the index -3 read nil off the ring
function K.workRoomIndex(hx, hy)
    local deg = math.atan2(hy, hx) * DEG     -- (-180, 180]
    if deg ~= deg or deg == math.huge or deg == -math.huge then return nil end
    if deg < 0 then deg = deg + 360 end
    local i = math.floor((deg + 22.5) / 45) + 1
    if i > #K.WORK_ROOM_HEADINGS then i = i - #K.WORK_ROOM_HEADINGS end   -- (337.5, 360) is the 0 heading
    return i
end

-- the clear tiles the ring reads along the heading nearest (hx, hy); 0.0 for no ring, a vector it cannot index or an
-- entry it lacks (fix 1: no ring read is ever compared as nil)
function K.workRoomOpen(ring, hx, hy)
    local h = type(ring) == "table" and ring.h or nil
    if type(h) ~= "table" then return 0.0 end
    local i = K.workRoomIndex(hx, hy)
    local v = i ~= nil and h[i] or nil
    if type(v) ~= "number" or v ~= v then return 0.0 end
    return v
end

-- an all-closed ring at the square (sx, sy, z): every heading 0.0, wall (fix 1: what the melee holds with no read)
local function closedRing(sx, sy, z)
    local h, stop = {}, {}
    for i = 1, #K.WORK_ROOM_HEADINGS do h[i], stop[i] = 0.0, "wall" end
    return { h = h, stop = stop, tick = PZA.tick or 0, sx = sx, sy = sy, z = z }
end

-- the melee's ring (the footwork's choose): its work state's, read again when the player's square changed or after
-- K.WORK_TICKS of its ticks (w.roomTicks, counted in K.workTick; fix 1's budget ruling: the re-choose cadence, so a
-- re-choose reads at most one ring); never nil: a read that answers none keeps the last ring, else an all-closed one
function K.workRoomFor(p, st, px, py, pz)
    local w = st.work
    local r = w.room
    if r == nil or w.roomTicks >= K.WORK_TICKS or r.sx ~= math.floor(px) or r.sy ~= math.floor(py) or r.z ~= pz then
        local fresh = nil
        if px == px and py == py then fresh = K.workRoom(p, px, py, pz) end
        if fresh ~= nil then
            r = fresh
        elseif r == nil then
            r = closedRing(math.floor(px), math.floor(py), pz)
        end
        w.room, w.roomTicks = r, 0
    end
    return r
end

-- the frame's ring (PZAgent_Sense.lua's me.room): K.room when it was read on the player's square within
-- K.WORK_ROOM_TICKS client ticks, else one read now; nil when the position is unread
function K.workRoomNow(p)
    local px, py, pz = playerAt(p)
    if px == nil or py == nil then return nil end
    local r = K.room
    local now = PZA.tick or 0
    if r ~= nil and now >= r.tick and now - r.tick < K.WORK_ROOM_TICKS and r.sx == math.floor(px)
       and r.sy == math.floor(py) and r.z == pz then
        return r
    end
    return K.workRoom(p, px, py, pz)
end

-- ---- the dispositions' string and release (PZA/1.16, Plan 37 Task 2; the spec
-- `2026-11-12-plan-37-the-disposition-design.md` sections 3.1 to 3.3) ----------------------------------------------
-- The planner picks the disposition; the reflex executes its table (K.DISPOSITIONS, the flags K.workTick reads) and
-- never decides. Under string (the tick's 4b, after the pile, the crawler buffer and the nearest attacker's facing,
-- which run under every disposition, and in place of the stagger in, the retreat and the band step):
--   the leader: the nearest standing zombie within workR (the target counted while it stands, the rest the melee's
--     near read, which reads workR under string, K.workNearR), else the standing target; none standing: nil, the
--     finish or the meet goes on. A leader other than the target is re-pinned to (M.repin, repin_for string) every
--     K.WORK_TICKS ticks, and at once at a turn, never back to a stalled zombie (fix 7b's stallId).
--   the gait: the run (MO.want run) while the leader's closing speed (the melee's closingOf over K.MELEE_SAMPLES, the
--     target's history) exceeds K.STRING_RUN_V, the walk once a read is at or under it, the last read kept while the
--     history is short (a re-pin restarts it); the run's latch written false on a change to the walk and on any tick
--     with no string walk (the def.tick wrapper above).
--   the turn: the leader's distance at the next landing (K.workLanding) within the reach plus K.STRING_TURN_R and
--     the second-nearest standing within workR beyond K.STRING_GAP, or none: the walk stopped, the walk gait, the
--     stance taken beyond faceR (M.holdStance; inside faceR the meet's own release and face), turn_for {leader, gap2}
--     on the tick's line, and nil: the meet presses the leader (K.footwork answers its stand or face, no step) and
--     after the press's result the tick reads again.
--   else the walk: along the heading re-chosen every K.WORK_TICKS ticks (at once on a new nearest): the withdraw
--     vector when given, else the way away from the centroid of the standing within workR (the leader's position with
--     none), turned by K.WORK_TURNS to the first clear heading as the footwork's choose turns (turnClear: the ring,
--     the crawlers, the fallen); the stance released (M.loosen), the walk of kind string (M.walkAlong: a forward walk
--     in input space, the force-aim off), step work, step_for string. With no clear heading the walk stops and the
--     meet presses (nil, the leaf's clear false).
-- The release (the tick's first read after the floor, and under a hit reaction through K.meleeWorkFloor): release
-- true ends done handback {why released, safe true} when no press is in flight and the nearest standing zombie (the
-- target while it stands, the near read's) stands beyond K.RELEASE_SAFE_R or the target is knocked down, else the
-- disposition's own tick runs and K.RELEASE_MAX_TICKS ticks after the first that read it (w.releaseTicks, counted in
-- the def.tick wrapper on every tick, a press's included) it ends {why released, safe false}. The floor stays first.
-- The cost: no Java call beyond the reads named (the near read's distTo per candidate within its radius; a re-choose's
-- getZ, the ring when due and two position reads a standing zombie without a frame position; the release's
-- isOnFloor and its near read only under a hit reaction).

-- the string's gait: the run wanted, or the walk (the run's latch written false when it was the run)
function K.workStringGait(p, w, run)
    if run then
        MO.want("run")
    else
        MO.want("walk")
        if w.gaitRun then PZA.call(p, "setForceRun", false) end
    end
    w.gaitRun = run
end

-- the fallen zombies the string's heading avoids ({x, y} each): the target when fallen, and the frame's records
-- reading onFloor (not crawler) within workR, as the footwork's choose reads them
local function fallenNear(st, fallen)
    local w = st.work
    local fl = {}
    if fallen then fl[1] = { x = st.zx, y = st.zy } end
    local S = PZA.sense
    local f = S ~= nil and S.last or nil
    local recs = f ~= nil and f.zombies or nil
    if recs == nil then return fl end
    for i = 1, #recs do
        local rec = recs[i]
        if rec.id ~= st.id and rec.onFloor == true and rec.crawler ~= true and type(rec.dist) == "number"
           and rec.dist < w.workR + K.MELEE_CROWD_SLACK and type(rec.x) == "number" and type(rec.y) == "number" then
            fl[#fl + 1] = { x = rec.x, y = rec.y }
        end
    end
    return fl
end

-- the string's heading chosen into w (hx, hy, heading, turn, clear, n): the withdraw vector, else away from the
-- centroid of zs (each {x, y} or {o}), the leader's with none; turned to the first clear (turnClear)
local function stringChoose(p, st, zs, leader, fallen)
    local w = st.work
    w.sinceChoose = 0
    local ax, ay = 0, 0
    if w.retreat then
        ax, ay = w.withdrawX, w.withdrawY
    else
        local from = zs
        if #from == 0 then from = { leader } end
        local cx, cy, n = 0, 0, 0
        for i = 1, #from do
            local x, y = from[i].x, from[i].y
            if x == nil and from[i].o ~= nil then x, y = posOf(from[i].o) end
            if x ~= nil and y ~= nil then cx, cy, n = cx + x, cy + y, n + 1 end
        end
        if n > 0 then ax, ay = st.px - cx / n, st.py - cy / n end
    end
    w.n = #zs
    w.hx, w.hy, w.heading, w.turn, w.clear, w.nanHeading = nil, nil, nil, nil, false, nil
    local len = math.sqrt(ax * ax + ay * ay)
    if len ~= len or len == math.huge then   -- a non-finite way away is no heading (the leaf's nan_heading)
        w.nanHeading = true
        return
    end
    if len <= 0 then return end
    turnClear(p, st, ax / len, ay / len, w.crawlers, fallenNear(st, fallen))
end

-- the string (the block's rule): a step (the walk's work, a re-pin), else nil (the turn, no clear heading, or nothing
-- standing: w.stringing tells the first two)
function K.workString(p, st, d, standing, fallen)
    local w = st.work
    local zs = standingWithin(st, d, standing, w.workR)
    local leader = zs[1]
    if leader == nil and standing then leader = { id = st.id, d = d, o = st.z, x = st.zx, y = st.zy } end
    if leader == nil then return nil end
    w.stringing = true
    w.stringTicks = w.stringTicks + 1
    local second = zs[2]
    local turn = K.workLanding(p, st, leader.d, leader.id) <= M.reachOf(p, st) + K.STRING_TURN_R
                 and (second == nil or second.d > K.STRING_GAP)
    if leader.id ~= st.id and leader.id ~= w.stallId and (turn or w.stringTicks >= K.WORK_TICKS) then
        w.stringTicks, w.repinFor = 0, "string"
        return M.repin(p, st, leader)
    end
    if leader.id == st.id then
        local v = M.closingOf(st, st.px, st.py, st.zx, st.zy, d)
        if v ~= nil then w.run = v > K.STRING_RUN_V end
    end
    if turn then
        M.stopWalk(p, st)
        K.workStringGait(p, w, false)
        if d > st.faceR then M.holdStance(p, st) end
        local gap2 = nil
        if second ~= nil then gap2 = second.d end
        w.turnFor = { leader = leader.id, gap2 = gap2 }
        return nil
    end
    if w.sinceChoose >= K.WORK_TICKS then stringChoose(p, st, zs, leader, fallen) end
    w.steppedNow, w.stepFor, w.held = true, "string", nil
    w.lh, w.lt, w.lc, w.ln = w.heading, w.turn, w.clear, w.n
    if not w.clear then   -- no clear heading: the walk stopped, the meet presses
        M.stopWalk(p, st)
        K.workStringGait(p, w, false)
        return nil
    end
    M.loosen(p, st)
    K.workStringGait(p, w, w.run)
    w.stringWalked = true
    M.walkAlong(p, st, "string", w.hx, w.hy)
    return "work"
end

-- the release (the block's rule): done handback released {safe}, else nil. standing and near the tick's reads (the
-- target standing, the melee's near read); standing nil (under a hit reaction): both read here
function K.workRelease(p, st, d, standing, near)
    local w = st.work
    if w == nil or not w.release then return nil end
    if standing == nil then
        standing = not K.onFloor(st.z) and not st.knocked
        near = M.standingNear(p, st, K.RELEASE_SAFE_R)
    end
    local nd = nil
    if standing then nd = d end
    if near ~= nil and near[1] ~= nil and (nd == nil or near[1].d < nd) then nd = near[1].d end
    local flying = st.strike ~= nil and not st.strike.ended
    if not flying and (st.knocked or nd == nil or nd > K.RELEASE_SAFE_R) then
        return "done", "handback", { why = "released", safe = true }
    end
    if (w.releaseTicks or 0) >= K.RELEASE_MAX_TICKS then return "done", "handback", { why = "released", safe = false } end
    return nil
end

-- the radius the melee's near read (K.meleeCrowd) widens to: K.RELEASE_SAFE_R while the release is asked, workR under
-- string; 0 otherwise (the Plan 36 read)
function K.workNearR(w)
    local r = 0
    if w.release then r = K.RELEASE_SAFE_R end
    if K.DISPOSITIONS[w.disposition].string and w.workR > r then r = w.workR end
    return r
end
