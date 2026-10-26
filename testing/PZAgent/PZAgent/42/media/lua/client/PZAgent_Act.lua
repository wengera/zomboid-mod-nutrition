-- PZAgent_Act.lua — the goals (spec § 2.3). One goal at a time; each is a per-tick state machine that
-- sets state done|failed with a detail from its closed set: a failed detail from the `-- reasons:` line below, a done
-- detail from the `-- done:` line (agent/reasons.py's REASONS and DONE; a test parses both). The walk is the game's own timed action,
-- queued the way the harness's player.walk does [#2082: setRunning(true) does not make a walk run].
-- A top-level goto x y run asks to run once, at its walk's start; a flee's run-flagged walk asks every tick (setRun).
-- args: goto x y [run]; open x y; loot x y [food|water|weapon|bandage|all]; eat <fullType>; drink; fight; flee x y;
-- sleep. Every x y is a world square coordinate, as a scan reports it (an offset goes stale while the player moves).
-- A player whose overall body health reads 0 is dead: every goal's start refuses with dead, and a running goto
-- fails dead at once (an absent reading is not dead). goto is stuck when the player has not moved (|dx| + |dy| under
-- STILL_EPS) for STUCK_TICKS consecutive ticks: a walk round a house grows the straight-line distance while it walks
-- correctly (Stage A pass 2), so progress toward the target is never read. Every failed goto clears its walk.
-- details: goto no square|no path|stuck|dead; open no square|no door|locked|not adjacent; loot not loaded|no container|
-- not adjacent|empty|no match|interrupted; eat, drink none held|not valid|interrupted; fight done clear, failed
-- no weapon|weapon broke|low health; flee done at, failed cornered; sleep done awake, failed not allowed|
-- interrupted; any running goal superseded. Done details: goto d=<distance>; stop an empty detail; open open; loot
-- moved=<n>; eat, drink consumed; fight clear; flee at; sleep awake (d= and moved= are prefixes, the empty one unlisted).
-- open's locked is read after the toggle: a door or window still shut OPEN_MS after its queued open reads
-- locked (locked from outside, a stuck door, a smashed or invincible window); only a barricade fails it up front.
-- reasons: bad args|no square|no path|stuck|superseded|no door|locked|not adjacent|no container|not loaded|empty|no match|none held|interrupted|not valid|no weapon|weapon broke|low health|cornered|not allowed|dead
-- done: d=|moved=|open|consumed|clear|at|awake
PZA.act = PZA.act or {}
local A = PZA.act
A.goals = A.goals or {}
A.goal = nil
A.REPLAN_MAX = 3
A.STUCK_TICKS = 90
A.STILL_EPS = 0.01        -- tiles, |dx| + |dy| between two ticks: under this the player has not moved

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

-- the overall body health, or nil when it cannot be read
local function healthOf(p)
    local _, bd = PZA.call(p, "getBodyDamage")
    local ok, h = PZA.call(bd, "getOverallBodyHealth")
    if ok then return h end
    return nil
end

-- dead only on a reading of 0 or less; an absent reading is not dead
local function isDead(p)
    local h = healthOf(p)
    return h ~= nil and h <= 0
end

-- true when the vanilla timed-action queue and its add are loaded (index-checked, never called to find out)
local function queueLoaded()
    return ISTimedActionQueue ~= nil and ISTimedActionQueue.add ~= nil
end

-- clears the player's vanilla timed-action queue: the class and its clear index-checked first (an unloaded queue has
-- nothing to clear), the call under pcall for a raise inside vanilla Lua
local function clearQueue(p)
    if ISTimedActionQueue ~= nil and ISTimedActionQueue.clear ~= nil then pcall(ISTimedActionQueue.clear, p) end
end

-- sets the player's run and sprint flags together (Stage C pass 2: run 1's flee frames read running false on all 92,
-- the one setRunning(true) at the walk's start being #2082's finding again; the harness's TK.sprintWatch sets both
-- every tick). Whether asking every tick makes the walk run is a reading for the C pass-2 frames' running and
-- sprinting fields, not a fix known to work.
local function setRun(p, on)
    PZA.call(p, "setRunning", on)
    PZA.call(p, "setSprinting", on)
end

-- A new goal replaces a running one: the old walk and the run and sprint flags are cleared and the old goal's
-- status comes back as failed "superseded" (third return) so the caller reports it. A dead player refuses every goal but
-- stop (a dead body's running goal can still be stopped), and the running one carries on to its own end.
function A.start(cmd, p)
    local def = A.goals[cmd.goal]
    if def == nil then return false, "unknown goal" end
    if p ~= nil and cmd.goal ~= "stop" and isDead(p) then return false, "dead" end
    local argv = split(cmd.args)
    local ok, reason, st = def.start(argv)
    if not ok then return false, reason end
    local old = nil
    if A.goal ~= nil and A.goal.state == "running" then
        if p ~= nil then
            clearQueue(p)
            setRun(p, false) -- a superseded flee's run outlives it otherwise
        end
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

-- queues the vanilla walk to sq; false, "no walk action" when the queue or the walk class or its new is not loaded
-- (index-checked before the call: a missing one is the goal's own failure, never a raise under pcall; goto maps it to
-- no path, the reason a refused walk already takes), the call itself under pcall for a raise inside vanilla Lua
local function queueWalk(p, sq)
    if not queueLoaded() or ISWalkToTimedAction == nil or ISWalkToTimedAction.new == nil then
        return false, "no walk action"
    end
    local ran, err = pcall(function() ISTimedActionQueue.add(ISWalkToTimedAction:new(p, sq)) end)
    return ran, err
end

local function dist(p, x, y)
    local ex, ey = p:getX() - x, p:getY() - y
    return math.sqrt(ex * ex + ey * ey)
end

-- a goto's failed exit: its walk is cleared as done's is (Stage A pass 2's first leg failed stuck with its walk left
-- queued, and the next leg's walk waited 3661 ms behind it), then the goal fails with detail
local function failWalk(p, g, detail)
    clearQueue(p)
    g.state, g.detail = "failed", detail
end

A.goals["goto"] = {
    start = function(argv)
        local x, y = tonumber(argv[1]), tonumber(argv[2])
        if x == nil or y == nil then return false, "bad args" end
        return true, "", { x = x, y = y, run = argv[3] == "run", replans = 0, lastX = nil, lastY = nil, still = 0 }
    end,
    -- still counts the consecutive ticks the player has not moved (the first tick reads the position); at
    -- STUCK_TICKS the walk is cleared and re-queued, REPLAN_MAX times, then the goal fails stuck
    tick = function(p, g)
        if isDead(p) then failWalk(p, g, "dead"); return end
        if g.tx == nil then
            g.tx, g.ty = g.x, g.y
            local cell = getCell and getCell() or nil
            local _, sq = PZA.call(cell, "getGridSquare", g.tx, g.ty, p:getZ())
            if sq == nil then failWalk(p, g, "no square"); return end
            g.sq = sq
            if g.run then PZA.call(p, "setRunning", true) end
            local ran, err = queueWalk(p, sq)
            if not ran then failWalk(p, g, "no path"); return end
        end
        local d = dist(p, g.tx, g.ty)
        if d <= (g.doneR or 1.0) then
            clearQueue(p) -- the walk would carry on past the target and queue ahead of the next goal
            g.state, g.detail = "done", "d=" .. tostring(d)
            return
        end
        local x, y = p:getX(), p:getY()
        if g.lastX ~= nil and math.abs(x - g.lastX) + math.abs(y - g.lastY) < A.STILL_EPS then
            g.still = g.still + 1
        else
            g.still = 0
        end
        g.lastX, g.lastY = x, y
        if g.still >= A.STUCK_TICKS then
            if g.replans >= A.REPLAN_MAX then failWalk(p, g, "stuck"); return end
            g.replans, g.still = g.replans + 1, 0
            clearQueue(p)
            queueWalk(p, g.sq)
        end
    end,
}

A.goals["stop"] = {
    start = function(argv) return true, "", {} end,
    tick = function(p, g)
        clearQueue(p)
        setRun(p, false)
        g.state, g.detail = "done", ""
    end,
}

-- ---- open, loot, eat, drink --------------------------------------------------------------------
-- open and loot take the target square's world x y, walk through a goto sub-state to the non-solid
-- square at Chebyshev distance 1 nearest the player, then queue the vanilla action. The constructors,
-- read off the 42.21 install: ISOpenCloseDoor:new(character, item); ISOpenCloseWindow:new(character,
-- object); ISInventoryTransferAction:new(character, item, srcContainer,
-- destContainer, time); ISEatFoodAction:new(character, item, percentage);
-- ISDrinkFluidAction:new(character, item, percentage). Each vanilla class and member is index-checked before the
-- call (a missing one is the goal's own failure), and the call is under pcall for a raise inside vanilla Lua.
A.OPEN_MS = 5000          -- a queued open that leaves the door shut this long reads as locked
A.CONSUME_MS = 20000      -- an eat or drink not seen landing within this wall time is interrupted
A.LOOT_MS = 10000         -- a loot's wall budget: this, plus LOOT_ITEM_MS per queued transfer
A.LOOT_ITEM_MS = 3000

local function isA(o, cls)
    return instanceof ~= nil and instanceof(o, cls) == true
end

local function squareAt(x, y, z)
    local cell = getCell and getCell() or nil
    local _, sq = PZA.call(cell, "getGridSquare", x, y, z)
    return sq
end

local function objectsOn(sq)
    local out = {}
    local _, list = PZA.call(sq, "getObjects")
    local okN, n = PZA.call(list, "size")
    if not okN then return out end
    for i = 0, n - 1 do
        local _, o = PZA.call(list, "get", i)
        if o ~= nil then out[#out + 1] = o end
    end
    return out
end

-- the square's door or window and its kind, door first. A door is an IsoDoor or an IsoThumpable whose
-- isDoor is true; a window is an IsoWindow only, since ISOpenCloseWindow:perform calls
-- character:openWindow(object), which the jar takes as IsoWindow alone (a thumpable window would raise).
local function openableOn(sq)
    local objs = objectsOn(sq)
    local win = nil
    for _, o in ipairs(objs) do
        if isA(o, "IsoDoor") then return o, "door" end
        if isA(o, "IsoWindow") and win == nil then win = o end
        if isA(o, "IsoThumpable") then
            local _, d = PZA.call(o, "isDoor")
            if d == true then return o, "door" end
        end
    end
    if win ~= nil then return win, "window" end
    return nil, nil
end

local function containersOn(sq)
    local out = {}
    local objs = objectsOn(sq)
    for _, o in ipairs(objs) do
        local okN, cn = PZA.call(o, "getContainerCount")
        if okN then
            for i = 0, cn - 1 do
                local _, c = PZA.call(o, "getContainerByIndex", i)
                if c ~= nil then out[#out + 1] = c end
            end
        else
            local _, c = PZA.call(o, "getContainer")
            if c ~= nil then out[#out + 1] = c end
        end
    end
    return out
end

local function xyArgs(argv)
    local x, y = tonumber(argv[1]), tonumber(argv[2])
    if x == nil or y == nil then return nil, nil end
    return math.floor(x), math.floor(y)
end

local function cheb(p, x, y)
    return math.max(math.abs(math.floor(p:getX()) - x), math.abs(math.floor(p:getY()) - y))
end

-- the square at Chebyshev distance 1 from (x, y) nearest the player that is neither solid nor solidTrans
-- (furniture: a stove or counter reads isSolid false and isSolidTrans true, and blocks the walk), or nil;
-- an absent isSolidTrans member counts as not solidTrans
local function adjacentTo(p, x, y, z)
    local bx, by, bd = nil, nil, nil
    for dy = -1, 1 do
        for dx = -1, 1 do
            if dx ~= 0 or dy ~= 0 then
                local sq = squareAt(x + dx, y + dy, z)
                local _, solid = PZA.call(sq, "isSolid")
                local _, solidTrans = PZA.call(sq, "isSolidTrans")
                if sq ~= nil and solid ~= true and solidTrans ~= true then
                    local d = dist(p, x + dx + 0.5, y + dy + 0.5)
                    if bd == nil or d < bd then bx, by, bd = x + dx, y + dy, d end
                end
            end
        end
    end
    return bx, by
end

-- a goto state aimed at square (x, y)'s centre, set up the way A.start sets a goal; run makes it a run
local function subGoto(x, y, run)
    local argv = { x + 0.5, y + 0.5 }
    if run then argv[3] = "run" end
    local _, _, st = A.goals["goto"].start(argv)
    st.seq, st.name, st.state, st.detail, st.argv, st.ticks = 0, "goto", "running", "", {}, 0
    return st
end

-- one tick of g.sub while it runs; its state after. A run-flagged sub-walk still running after its tick asks to run
-- again (setRun), every tick; its owner clears the flags when the walk ends
local function tickSub(p, g)
    if g.sub.state == "running" then
        g.sub.ticks = g.sub.ticks + 1
        A.goals["goto"].tick(p, g.sub)
        if g.sub.run and g.sub.state == "running" then setRun(p, true) end
    end
    return g.sub.state
end

-- walks next to (g.x, g.y): "here" once within one square, "walk" while the sub-goto runs, "fail" when
-- no square is free next to it or the walk failed
local function approach(p, g)
    if g.sub == nil then
        if cheb(p, g.x, g.y) <= 1 then return "here" end
        local ax, ay = adjacentTo(p, g.x, g.y, p:getZ())
        if ax == nil then return "fail" end
        g.sub = subGoto(ax, ay)
    end
    local st = tickSub(p, g)
    if st == "running" then return "walk" end
    if st == "done" then return "here" end
    return "fail"
end

A.goals["open"] = {
    start = function(argv)
        local x, y = xyArgs(argv)
        if x == nil then return false, "bad args" end
        return true, "", { x = x, y = y }
    end,
    tick = function(p, g)
        if g.door == nil then
            local sq = squareAt(g.x, g.y, p:getZ())
            if sq == nil then g.state, g.detail = "failed", "no square"; return end
            g.door, g.kind = openableOn(sq)
            if g.door == nil then g.state, g.detail = "failed", "no door"; return end
        end
        local _, isOpen = PZA.call(g.door, "IsOpen")
        if isOpen == true then g.state, g.detail = "done", "open"; return end
        if g.queuedAt == nil then
            -- no isLocked pre-check: IsoDoor.ToggleDoorActual unlocks a door that canBeOpenFromInside
            local _, barricaded = PZA.call(g.door, "isBarricaded")
            if barricaded == true then g.state, g.detail = "failed", "locked"; return end
            local at = approach(p, g)
            if at == "fail" then g.state, g.detail = "failed", "not adjacent"; return end
            if at == "walk" then return end
            local ctor = ISOpenCloseDoor
            if g.kind == "window" then ctor = ISOpenCloseWindow end
            -- the vanilla class, its new and the queue's add index-checked before the call (no raise to catch)
            if ctor == nil or ctor.new == nil or not queueLoaded() then g.state, g.detail = "failed", "no door"; return end
            local ran = pcall(function() ISTimedActionQueue.add(ctor:new(p, g.door)) end)
            if not ran then g.state, g.detail = "failed", "no door"; return end
            g.queuedAt = PZA.now()
            return
        end
        if PZA.now() - g.queuedAt > A.OPEN_MS then g.state, g.detail = "failed", "locked" end
    end,
}

local function fullTypeHas(it, a, b)
    local _, ft = PZA.call(it, "getFullType")
    ft = tostring(ft or "")
    return string.find(ft, a, 1, true) ~= nil or string.find(ft, b, 1, true) ~= nil
end

local FILTERS = {
    all = function(it) return true end,
    food = function(it) return isA(it, "Food") end,
    weapon = function(it) return isA(it, "HandWeapon") end,
    water = function(it) local _, fc = PZA.call(it, "getFluidContainer"); return fc ~= nil end,
    bandage = function(it) return fullTypeHas(it, "Bandage", "Rag") end,
}

local function invCount(p)
    local _, inv = PZA.call(p, "getInventory")
    local _, items = PZA.call(inv, "getItems")
    local ok, n = PZA.call(items, "size")
    return ok and n or 0, inv
end

-- every item of g.boxes passing g.filter, as {item, container}; and how many items and unloaded boxes were seen
local function lootPicks(g)
    local picks, seen, unloaded = {}, 0, 0
    local keep = FILTERS[g.filter]
    for _, c in ipairs(g.boxes) do
        local okG, items = PZA.call(c, "getItems")
        local okS, n = PZA.call(items, "size")
        if okG and okS then
            for i = 0, n - 1 do
                local _, it = PZA.call(items, "get", i)
                if it ~= nil then
                    seen = seen + 1
                    if keep(it) then picks[#picks + 1] = { it, c } end
                end
            end
        else
            unloaded = unloaded + 1
        end
    end
    return picks, seen, unloaded
end

A.goals["loot"] = {
    start = function(argv)
        local x, y = xyArgs(argv)
        local filter = argv[3] or "all"
        if x == nil or FILTERS[filter] == nil then return false, "bad args" end
        return true, "", { x = x, y = y, filter = filter }
    end,
    tick = function(p, g)
        if g.boxes == nil then
            local sq = squareAt(g.x, g.y, p:getZ())
            if sq == nil then g.state, g.detail = "failed", "not loaded"; return end
            g.boxes = containersOn(sq)
            if #g.boxes == 0 then g.state, g.detail = "failed", "no container"; return end
        end
        if g.queuedAt == nil then
            local at = approach(p, g)
            if at == "fail" then g.state, g.detail = "failed", "not adjacent"; return end
            if at == "walk" then return end
            local picks, seen, unloaded = lootPicks(g)
            if unloaded == #g.boxes then g.state, g.detail = "failed", "not loaded"; return end
            if seen == 0 then g.state, g.detail = "failed", "empty"; return end
            if #picks == 0 then g.state, g.detail = "failed", "no match"; return end
            -- the vanilla transfer class, its new and the queue's add index-checked once before the loop: a missing
            -- one is the vanilla class not loaded, not "no match", so the goal fails not loaded
            if ISInventoryTransferAction == nil or ISInventoryTransferAction.new == nil or not queueLoaded() then
                g.state, g.detail = "failed", "not loaded"; return
            end
            local before, inv = invCount(p)
            local queued = 0
            for _, pick in ipairs(picks) do
                local ran = pcall(function() ISTimedActionQueue.add(ISInventoryTransferAction:new(p, pick[1], pick[2], inv)) end)
                if ran then queued = queued + 1 end
            end
            if queued == 0 then g.state, g.detail = "failed", "no match"; return end
            g.before, g.want, g.queuedAt = before, queued, PZA.now()
            return
        end
        local moved = math.max(0, (invCount(p)) - g.before)
        local late = PZA.now() - g.queuedAt > A.LOOT_MS + A.LOOT_ITEM_MS * g.want
        if moved >= g.want or (late and moved > 0) then g.state, g.detail = "done", "moved=" .. tostring(moved); return end
        if late then g.state, g.detail = "failed", "interrupted" end
    end,
}

-- builds ctor:new(p, it, 1), checks its isValidStart and queues it; false when any step refuses. The class, its new,
-- the action's isValidStart and the queue's add are index-checked before each call (a missing one is false, never a
-- raise under pcall); the calls stay under pcall for a raise inside vanilla Lua
local function queueConsume(p, g, ctor, it)
    if ctor == nil or ctor.new == nil or not queueLoaded() then return false end
    local ran, act = pcall(function() return ctor:new(p, it, 1) end)
    if not ran or act == nil then return false end
    if act.isValidStart == nil then return false end
    local okV, valid = pcall(function() return act:isValidStart() end)
    if not okV or valid ~= true then return false end
    local okA = pcall(function() ISTimedActionQueue.add(act) end)
    if not okA then return false end
    g.queuedAt = PZA.now()
    return true
end

A.goals["eat"] = {
    start = function(argv)
        if argv[1] == nil then return false, "bad args" end
        return true, "", { want = argv[1] }
    end,
    -- top level only: ISEatFoodAction:isValid on an MP client checks the main inventory's containsID, and
    -- vanilla transfers a bag's item out first; a non-Food item is refused before ISEatFoodAction:new,
    -- whose getDuration calls the Food-only getBaseHunger (a caught raise still parks a -debug client)
    tick = function(p, g)
        local _, inv = PZA.call(p, "getInventory")
        local _, count = PZA.call(inv, "getCountType", g.want)
        count = count or 0
        if g.queuedAt == nil then
            local _, it = PZA.call(inv, "getFirstType", g.want)
            if it == nil then g.state, g.detail = "failed", "none held"; return end
            if not isA(it, "Food") then g.state, g.detail = "failed", "not valid"; return end
            if not queueConsume(p, g, ISEatFoodAction, it) then g.state, g.detail = "failed", "not valid"; return end
            g.before = count
            return
        end
        if count < g.before then g.state, g.detail = "done", "consumed"; return end
        if PZA.now() - g.queuedAt > A.CONSUME_MS then g.state, g.detail = "failed", "interrupted" end
    end,
}

-- a top-level inventory item holding a non-empty, non-poisonous fluid container, and that container:
-- the first filled with clean water, else the first other one (bleach or petrol is never drunk)
local function firstDrink(p)
    local _, inv = PZA.call(p, "getInventory")
    local _, items = PZA.call(inv, "getItems")
    local okN, n = PZA.call(items, "size")
    local anyIt, anyFc = nil, nil
    for i = 0, (okN and n or 0) - 1 do
        local _, it = PZA.call(items, "get", i)
        local _, fc = PZA.call(it, "getFluidContainer")
        local _, empty = PZA.call(fc, "isEmpty")
        local okP, poison = PZA.call(fc, "isPoisonous")
        -- fails closed: a container whose isPoisonous is absent is never drunk
        if fc ~= nil and empty ~= true and okP and poison == false then
            local _, clean = PZA.call(fc, "isFilledWithCleanWater")
            if clean == true then return it, fc end
            if anyIt == nil then anyIt, anyFc = it, fc end
        end
    end
    return anyIt, anyFc
end

A.goals["drink"] = {
    start = function(argv) return true, "", {} end,
    tick = function(p, g)
        if g.queuedAt == nil then
            local it, fc = firstDrink(p)
            if it == nil then g.state, g.detail = "failed", "none held"; return end
            local _, amount = PZA.call(fc, "getAmount")
            if not queueConsume(p, g, ISDrinkFluidAction, it) then g.state, g.detail = "failed", "not valid"; return end
            g.fc, g.before = fc, amount or 0
            return
        end
        local _, amount = PZA.call(g.fc, "getAmount")
        if amount ~= nil and amount < g.before then g.state, g.detail = "done", "consumed"; return end
        if PZA.now() - g.queuedAt > A.CONSUME_MS then g.state, g.detail = "failed", "interrupted" end
    end,
}

-- ---- fight, flee, sleep -------------------------------------------------------------------------
-- fight swings the way the harness's attack.melee does (PZTestKit_Client.lua: faceThisObject(z), then
-- DoAttack(0) on a 1200 ms cadence) only within the held weapon's reach (A.reachOf), and walks toward a zombie
-- between that reach and FIGHT_R; DoAttack is reached through PZA.call, which indexes before it calls, under pcall.
-- sleep is vanilla's own ground sleep with its dialog answered: ISWorldObjectContextMenu.onConfirmSleep
-- (this, button, player, bed) with button.internal "YES" and bed nil, which runs the vanilla checks (zombies in
-- sight, pain, panic) and sets the character asleep; a refusal there is a halo text, so a sleep that never
-- comes within SLEEP_WAIT_MS reads as not allowed.
A.FIGHT_R = 3             -- a zombie this close is fought
-- The reach (tiles) is the held weapon's, as the engine reads it for a swing's targets: weapon:getMaxRange(chr) *
-- weapon:getRangeMod(chr) (the jar's CombatManager.calcValidTargets L1445 and calculateHitListWeapon L2056). For a melee
-- weapon getMaxRange(chr) is the script's MaxRange (HandWeapon L879; the aiming term at L877 is for ranged weapons
-- only), and getRangeMod is 1.0, or 1.2 with the weapon's Blunt/Axe/Spear... perk at 7 or more (L491-L511). The
-- fallback is the 42.21 install's Base.BaseballBat MaxRange = 1.25 (scripts/generated/items/weapon.txt L6700), and
-- the margin keeps the swing inside the reach while both bodies move (run 1's fight 27 swung 210 s at a zombie 2.74
-- tiles off, out of reach).
A.REACH_FALLBACK = 1.25
A.REACH_MARGIN = 0.9
A.CLOSE_DONE_R = 0.5      -- a closing step's done radius (a goto's default is 1.0), so the reach check fires first
A.SWING_MS = 1200       -- the swing cadence, the harness's attack.melee nextAt
A.GRAB_R = 1.0            -- inside this, with no swing due, the player steps back
A.STEP_BACK = 2           -- tiles stepped back, along the zombie-to-player line
A.FLEE_HEALTH = 40        -- overall body health under this fails a fight (Python decides what next)
A.CLEAR_TICKS = 60        -- ticks with no live zombie within PZA.sense.ZOMBIE_RADIUS before a fight is done
A.FLEE_REPLAN_TICKS = 30  -- a flee re-aims this often, away from the zombies' centroid
A.FLEE_DIST = 8           -- tiles a re-aimed flee runs from the player's position
A.SLEEP_WAIT_MS = 10000   -- a sleep not begun within this wall time is not allowed

-- the live zombies within r of the player, as {z, x, y, d}, and the nearest of them
local function liveZombies(p, r)
    local out, best = {}, nil
    local cell = getCell and getCell() or nil
    local _, list = PZA.call(cell, "getZombieList")
    local okN, n = PZA.call(list, "size")
    if not okN then return out, nil end
    local px, py = p:getX(), p:getY()
    for i = 0, n - 1 do
        local _, z = PZA.call(list, "get", i)
        local _, dead = PZA.call(z, "isDead")
        if z ~= nil and dead ~= true then
            local zx, zy = z:getX(), z:getY()
            local ex, ey = zx - px, zy - py
            local d = math.sqrt(ex * ex + ey * ey)
            if d <= r then
                local e = { z = z, x = zx, y = zy, d = d }
                out[#out + 1] = e
                if best == nil or d < best.d then best = e end
            end
        end
    end
    return out, best
end

-- the square `dist` tiles from the player along the unit vector away from (ax, ay), or nil when the
-- player stands on that point
local function awayFrom(p, ax, ay, dist)
    local px, py = p:getX(), p:getY()
    local vx, vy = px - ax, py - ay
    local n = math.sqrt(vx * vx + vy * vy)
    if n == 0 then return nil, nil end
    return math.floor(px + vx / n * dist), math.floor(py + vy / n * dist)
end

-- the held weapon's reach in tiles: getMaxRange(p) * getRangeMod(p), or REACH_FALLBACK when either member is
-- absent or answers no number, times REACH_MARGIN
function A.reachOf(p, w)
    local okM, mx = PZA.call(w, "getMaxRange", p)
    local okR, rm = PZA.call(w, "getRangeMod", p)
    local r = A.REACH_FALLBACK
    if okM and okR and type(mx) == "number" and type(rm) == "number" then r = mx * rm end
    return r * A.REACH_MARGIN
end

-- drops a fight's step walk (back, or toward the zombie); one dropped while it runs (the zombies left) is cleared
-- from the queue, since it would carry on and queue ahead of the next goal (a failed one cleared its own walk, a
-- done one too)
local function dropStep(p, g)
    if g.sub ~= nil and g.sub.state == "running" then clearQueue(p) end
    g.sub = nil
end

A.goals["fight"] = {
    start = function(argv) return true, "", { quiet = 0 } end,
    tick = function(p, g)
        local _, w = PZA.call(p, "getPrimaryHandItem")
        if w == nil then g.state, g.detail = "failed", "no weapon"; return end
        local okC, cond = PZA.call(w, "getCondition")
        if okC and cond ~= nil and cond <= 0 then g.state, g.detail = "failed", "weapon broke"; return end
        local h = healthOf(p)
        if h ~= nil and h < A.FLEE_HEALTH then g.state, g.detail = "failed", "low health"; return end
        local zs, near = liveZombies(p, PZA.sense.ZOMBIE_RADIUS)
        if near == nil then
            dropStep(p, g)
            g.quiet = g.quiet + 1
            if g.quiet >= A.CLEAR_TICKS then
                clearQueue(p)
                g.state, g.detail = "done", "clear"
            end
            return
        end
        g.quiet = 0
        local reach = A.reachOf(p, w)
        local zx, zy = math.floor(near.x), math.floor(near.y)
        -- a step toward the zombie is dropped once it is within reach or beyond FIGHT_R, and re-aimed (dropped here,
        -- queued again below) when the zombie's square changes
        if g.sub ~= nil and g.closing then
            if near.d <= reach or near.d > A.FIGHT_R or zx ~= g.zx or zy ~= g.zy then dropStep(p, g) end
        end
        if g.sub ~= nil then
            local st = tickSub(p, g)
            if st == "running" then return end
            -- a closing walk that ended done is as near as a walk to that square gets: the fight swings from there
            -- while the zombie stays on it, never re-queueing the same walk every tick
            if st == "done" and g.closing then g.closedX, g.closedY = g.zx, g.zy end
            dropStep(p, g)
        end
        if near.d > A.FIGHT_R then return end
        local closed = g.closedX == zx and g.closedY == zy
        if not closed then g.closedX, g.closedY = nil, nil end
        if near.d > reach and not closed then
            -- a walk (not a run) to the zombie's own square with a tight done radius, so the reach check above
            -- drops it before the walk can end short of the zombie
            g.sub = subGoto(zx, zy, false)
            g.sub.doneR = A.CLOSE_DONE_R
            g.closing, g.zx, g.zy = true, zx, zy
            tickSub(p, g)
            return
        end
        PZA.call(p, "faceThisObject", near.z)
        local now = PZA.now()
        if g.lastSwing == nil or now - g.lastSwing >= A.SWING_MS then
            pcall(PZA.call, p, "DoAttack", 0)
            g.lastSwing = now
            return
        end
        if near.d < A.GRAB_R then
            local bx, by = awayFrom(p, near.x, near.y, A.STEP_BACK)
            if bx == nil then return end
            g.sub = subGoto(bx, by, false)
            g.closing = false
            g.closedX, g.closedY = nil, nil  -- a step-back forgets the closed square, so the fight closes again after it
            tickSub(p, g)
        end
    end,
}

-- re-aims a flee FLEE_DIST tiles from the player, away from the centroid of the live zombies in sense
-- radius; a target square that is unknown or solid keeps the current walk. The new walk inherits the
-- old one's stuck count, replans and last position, so re-aiming never hides a player who is not moving.
local function fleeReplan(p, g)
    local zs = liveZombies(p, PZA.sense.ZOMBIE_RADIUS)
    if #zs == 0 then return end
    local cx, cy = 0, 0
    for _, e in ipairs(zs) do cx, cy = cx + e.x, cy + e.y end
    local tx, ty = awayFrom(p, cx / #zs, cy / #zs, A.FLEE_DIST)
    if tx == nil then return end
    local sq = squareAt(tx, ty, p:getZ())
    local _, solid = PZA.call(sq, "isSolid")
    if sq == nil or solid == true then return end
    local old = g.sub
    clearQueue(p)
    g.sub = subGoto(tx, ty, true)
    g.sub.still, g.sub.replans, g.sub.lastX, g.sub.lastY = old.still, old.replans, old.lastX, old.lastY
end

A.goals["flee"] = {
    start = function(argv)
        local x, y = xyArgs(argv)
        if x == nil then return false, "bad args" end
        return true, "", { x = x, y = y }
    end,
    tick = function(p, g)
        if g.sub == nil then g.sub = subGoto(g.x, g.y, true) end
        if g.ticks % A.FLEE_REPLAN_TICKS == 0 then fleeReplan(p, g) end
        local st = tickSub(p, g)
        if st == "running" then return end
        setRun(p, false) -- the run and the sprint outlive the walk otherwise
        if st == "done" then g.state, g.detail = "done", "at"; return end
        g.state, g.detail = "failed", "cornered"
    end,
}

-- vanilla's menu gates, which onConfirmSleep does not check (ISVehicleMenu.lua L190-L206): on a client, sleep
-- only when the server's SleepAllowed is true; when sleep is needed (not a client, or SleepNeeded), not within an
-- hour of the last sleep (getHoursSurvived() - getLastHourSleeped() <= 1). Fails closed on an unreadable option.
local function sleepAllowed(p)
    local client = false
    if isClient ~= nil then client = isClient() == true end
    local needed = not client
    if client then
        local opts = getServerOptions ~= nil and getServerOptions() or nil
        local okA, allowed = PZA.call(opts, "getBoolean", "SleepAllowed")
        if not okA or allowed ~= true then return false end
        local okN, need = PZA.call(opts, "getBoolean", "SleepNeeded")
        if not okN then return false end
        needed = need == true
    end
    if needed then
        local okH, hours = PZA.call(p, "getHoursSurvived")
        local okL, last = PZA.call(p, "getLastHourSleeped")
        if okH and okL and hours ~= nil and last ~= nil and hours - last <= 1 then return false end
    end
    return true
end

-- done awake when isAsleep goes true then false; woken with less health than it lay down with, or with a
-- live zombie in sense radius, it is interrupted
A.goals["sleep"] = {
    start = function(argv) return true, "", {} end,
    tick = function(p, g)
        if g.calledAt == nil then
            local menu = ISWorldObjectContextMenu
            local fn = menu ~= nil and menu.onConfirmSleep or nil
            if fn == nil or not sleepAllowed(p) then g.state, g.detail = "failed", "not allowed"; return end
            local _, num = PZA.call(p, "getPlayerNum")
            -- the one site whose raise would park a -debug client: fn is index-checked above, but
            -- ISWorldObjectContextMenu.onConfirmSleep(this, button, player, bed) is vanilla Lua that can raise inside
            -- itself, which no index check prevents, so the pcall stays
            local ran = pcall(fn, nil, { internal = "YES" }, num or 0, nil)
            if not ran then g.state, g.detail = "failed", "not allowed"; return end
            g.calledAt, g.hp = PZA.now(), healthOf(p)
            return
        end
        local okA, asleep = PZA.call(p, "isAsleep")
        if not okA then g.state, g.detail = "failed", "not allowed"; return end
        if asleep == true then g.slept = true; return end
        if g.slept then
            local h = healthOf(p)
            local _, near = liveZombies(p, PZA.sense.ZOMBIE_RADIUS)
            if (h ~= nil and g.hp ~= nil and h < g.hp) or near ~= nil then
                g.state, g.detail = "failed", "interrupted"
            else
                g.state, g.detail = "done", "awake"
            end
            return
        end
        if PZA.now() - g.calledAt > A.SLEEP_WAIT_MS then g.state, g.detail = "failed", "not allowed" end
    end,
}
