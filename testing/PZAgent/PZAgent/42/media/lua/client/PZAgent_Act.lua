-- PZAgent_Act.lua — the goals (spec § 2.3). One goal at a time; each is a per-tick state machine that
-- sets state done|failed with a detail from its closed set, the `-- reasons:` line below (agent/reasons.py parses it). The walk is the game's own timed action,
-- queued the way the harness's player.walk does [#2082: setRunning(true) does not make a walk run].
-- args: goto x y [run]; open x y; loot x y [food|water|weapon|bandage|all]; eat <fullType>; drink. Every x y is a
-- world square coordinate, as a scan reports it (an offset goes stale while the player moves).
-- details: goto no square|no path|stuck; open no square|no door|locked|not adjacent; loot not loaded|no container|
-- not adjacent|empty|no match|interrupted; eat, drink none held|not valid|interrupted; any running goal superseded.
-- open's locked is read after the toggle: a door or window still shut OPEN_MS after its queued open reads
-- locked (locked from outside, a stuck door, a smashed or invincible window); only a barricade fails it up front.
-- reasons: bad args|no square|no path|stuck|superseded|no door|locked|not adjacent|no container|not loaded|empty|no match|none held|interrupted|not valid
PZA.act = PZA.act or {}
local A = PZA.act
A.goals = A.goals or {}
A.goal = nil
A.REPLAN_MAX = 3
A.STUCK_TICKS = 90

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

-- A new goal replaces a running one: the old walk is cleared and the old goal's status comes back
-- as failed "superseded" (third return) so the caller reports it.
function A.start(cmd, p)
    local def = A.goals[cmd.goal]
    if def == nil then return false, "unknown goal" end
    local argv = split(cmd.args)
    local ok, reason, st = def.start(argv)
    if not ok then return false, reason end
    local old = nil
    if A.goal ~= nil and A.goal.state == "running" then
        if p ~= nil then pcall(ISTimedActionQueue.clear, p) end
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

local function queueWalk(p, sq)
    local ran, err = pcall(function() ISTimedActionQueue.add(ISWalkToTimedAction:new(p, sq)) end)
    return ran, err
end

local function dist(p, x, y)
    local ex, ey = p:getX() - x, p:getY() - y
    return math.sqrt(ex * ex + ey * ey)
end

A.goals["goto"] = {
    start = function(argv)
        local x, y = tonumber(argv[1]), tonumber(argv[2])
        if x == nil or y == nil then return false, "bad args" end
        return true, "", { x = x, y = y, run = argv[3] == "run", replans = 0, lastX = nil, lastY = nil, still = 0 }
    end,
    tick = function(p, g)
        if g.tx == nil then
            g.tx, g.ty = g.x, g.y
            local cell = getCell and getCell() or nil
            local _, sq = PZA.call(cell, "getGridSquare", g.tx, g.ty, p:getZ())
            if sq == nil then g.state, g.detail = "failed", "no square"; return end
            g.sq = sq
            if g.run then PZA.call(p, "setRunning", true) end
            local ran, err = queueWalk(p, sq)
            if not ran then g.state, g.detail = "failed", "no path"; return end
        end
        local d = dist(p, g.tx, g.ty)
        if d <= 1.0 then
            pcall(ISTimedActionQueue.clear, p) -- the walk would carry on past the target and queue ahead of the next goal
            g.state, g.detail = "done", "d=" .. tostring(d)
            return
        end
        local x, y = p:getX(), p:getY()
        if g.lastX == x and g.lastY == y then g.still = g.still + 1 else g.still = 0 end
        g.lastX, g.lastY = x, y
        if g.still >= A.STUCK_TICKS then
            if g.replans >= A.REPLAN_MAX then g.state, g.detail = "failed", "stuck"; return end
            g.replans, g.still = g.replans + 1, 0
            pcall(ISTimedActionQueue.clear, p)
            queueWalk(p, g.sq)
        end
    end,
}

A.goals["stop"] = {
    start = function(argv) return true, "", {} end,
    tick = function(p, g)
        pcall(ISTimedActionQueue.clear, p)
        PZA.call(p, "setRunning", false)
        g.state, g.detail = "done", ""
    end,
}

-- ---- open, loot, eat, drink --------------------------------------------------------------------
-- open and loot take the target square's world x y, walk through a goto sub-state to the non-solid
-- square at Chebyshev distance 1 nearest the player, then queue the vanilla action. The constructors,
-- read off the 42.21 install: ISOpenCloseDoor:new(character, item); ISOpenCloseWindow:new(character,
-- object); ISInventoryTransferAction:new(character, item, srcContainer,
-- destContainer, time); ISEatFoodAction:new(character, item, percentage);
-- ISDrinkFluidAction:new(character, item, percentage). Vanilla Lua is reached under pcall.
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

-- the non-solid square at Chebyshev distance 1 from (x, y) nearest the player, or nil
local function adjacentTo(p, x, y, z)
    local bx, by, bd = nil, nil, nil
    for dy = -1, 1 do
        for dx = -1, 1 do
            if dx ~= 0 or dy ~= 0 then
                local sq = squareAt(x + dx, y + dy, z)
                local _, solid = PZA.call(sq, "isSolid")
                if sq ~= nil and solid ~= true then
                    local d = dist(p, x + dx + 0.5, y + dy + 0.5)
                    if bd == nil or d < bd then bx, by, bd = x + dx, y + dy, d end
                end
            end
        end
    end
    return bx, by
end

-- a goto state aimed at square (x, y)'s centre, set up the way A.start sets a goal
local function subGoto(x, y)
    local _, _, st = A.goals["goto"].start({ x + 0.5, y + 0.5 })
    st.seq, st.name, st.state, st.detail, st.argv, st.ticks = 0, "goto", "running", "", {}, 0
    return st
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
    if g.sub.state == "running" then
        g.sub.ticks = g.sub.ticks + 1
        A.goals["goto"].tick(p, g.sub)
    end
    if g.sub.state == "running" then return "walk" end
    if g.sub.state == "done" then return "here" end
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
            if ctor == nil then g.state, g.detail = "failed", "no door"; return end
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

-- builds ctor:new(p, it, 1), checks its isValidStart and queues it; false when any step refuses
local function queueConsume(p, g, ctor, it)
    local ran, act = pcall(function() return ctor:new(p, it, 1) end)
    if not ran or act == nil then return false end
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
        local _, poison = PZA.call(fc, "isPoisonous")
        if fc ~= nil and empty ~= true and poison ~= true then
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
