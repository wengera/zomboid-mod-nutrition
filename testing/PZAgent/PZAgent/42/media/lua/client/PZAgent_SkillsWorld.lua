-- PZAgent_SkillsWorld.lua — the skills that act on the world (Plan 22 spec § 7; split from PZAgent_Skills.lua in the
-- fix wave, M2): attack, interact, equip, consume, drop, one engine action each, ported from Plan 21's PZAgent_Act.lua
-- goals. Loads after PZAgent_Skills.lua (client files load by name, "." before "W") and registers each skill into
-- PZA.skills.types; the runner there (K.start, K.tick) owns every act line, the S-12 and S-15 guards and MO.off at every
-- end, as its header says. The runner's helpers come from K (K.isDead, K.dist, K.clearQueue, K.queueLoaded) and the
-- world readers from PZA.world (shared/PZAgent_World.lua: positions, a square's objects, its door or window, its
-- containers).
-- The constructors, read off the 42.21 install: ISOpenCloseDoor:new(character, item); ISOpenCloseWindow:new(character,
-- object); ISInventoryTransferAction:new(character, item, srcContainer, destContainer, time); ISEatFoodAction:new(
-- character, item, percentage); ISDrinkFluidAction:new(character, item, percentage). Each vanilla class and member is
-- index-checked before the call (a missing one is the skill's own failure), and the call is under pcall for a raise
-- inside vanilla Lua.
local K = PZA.skills
local MO = PZA.motor
local W = PZA.world
local isA, posOf, openableOn, containersOn = W.isA, W.posOf, W.openableOn, W.containersOn
local isDead, dist, clearQueue, queueLoaded = K.isDead, K.dist, K.clearQueue, K.queueLoaded

-- ---- the helpers attack and interact share ---------------------------------------------------------------------------

local function squareAt(x, y, z)
    local cell = getCell ~= nil and getCell() or nil
    local _, sq = PZA.call(cell, "getGridSquare", x, y, z)
    return sq
end

-- the Chebyshev distance in squares from the player's square to square (x, y), nil when the position cannot be read
local function cheb(p, x, y)
    local px, py = posOf(p)
    if px == nil or py == nil then return nil end
    return math.max(math.abs(math.floor(px) - x), math.abs(math.floor(py) - y))
end

-- the square at Chebyshev distance 1 from (x, y) nearest the player that is neither solid nor solidTrans
-- (furniture: a stove or counter reads isSolid false and isSolidTrans true, and blocks the walk), or nil;
-- an absent isSolidTrans member counts as not solidTrans (an unreadable position takes the first free one)
local function adjacentTo(p, x, y, z)
    local bx, by, bd = nil, nil, nil
    for dy = -1, 1 do
        for dx = -1, 1 do
            if dx ~= 0 or dy ~= 0 then
                local sq = squareAt(x + dx, y + dy, z)
                local _, solid = PZA.call(sq, "isSolid")
                local _, solidTrans = PZA.call(sq, "isSolidTrans")
                if sq ~= nil and solid ~= true and solidTrans ~= true then
                    local d = dist(p, x + dx + 0.5, y + dy + 0.5) or 0
                    if bd == nil or d < bd then bx, by, bd = x + dx, y + dy, d end
                end
            end
        end
    end
    return bx, by
end

-- queues cls:new(...) on the vanilla timed-action queue: true when queued, else false and the reason. The class, its new
-- and the queue's add are index-checked before any call (not loaded: a missing one is the skill's own failure, never a
-- raise under pcall); new and add each run under pcall for a raise inside vanilla Lua, a raise or a nil action failing
-- with bad (the caller's reason). vet, when given, is asked of the built action before the add and answers nil to pass
-- or the reason it refuses with (queueConsume's isValidStart).
local function queueAction(cls, bad, vet, ...)
    if cls == nil or cls.new == nil or not queueLoaded() then return false, "not loaded" end
    local made, action = pcall(cls.new, cls, ...)
    if not made or action == nil then return false, bad end
    if vet ~= nil then
        local why = vet(action)
        if why ~= nil then return false, why end
    end
    if not pcall(ISTimedActionQueue.add, action) then return false, bad end
    return true, nil
end

-- A sub-walk: walkTo's own state, built by its check and aimed at (x, y) at gait, run by a skill's approach as a sub-state
-- (Act's subGoto/tickSub form), never a second command: a skill stays one action with one act line sequence.
local function subWalk(x, y, gait)
    local _, _, st = K.types.walkTo.check({ x = x, y = y, gait = gait }, nil)
    st.state = "running"
    return st
end

-- one tick of a sub-walk while it runs; its state after: running, done or failed (sub.reason the walk's reason). A failed
-- sub-walk clears its walk (Stage A pass 2's leg left queued); a done one has cleared it already (walkTo's done)
local function tickSub(p, sub)
    if sub.state ~= "running" then return sub.state end
    local s, out = K.types.walkTo.tick(p, sub)
    if s == "done" then
        sub.state = "done"
    elseif s == "failed" then
        sub.state, sub.reason = "failed", out
        clearQueue(p)
    end
    return sub.state
end

-- the player's floor level, 0 when unreadable
local function floorOf(p)
    local _, z = PZA.call(p, "getZ")
    return z or 0
end

-- the size of the player's main inventory (0 when unreadable) and the inventory
local function invCount(p)
    local _, inv = PZA.call(p, "getInventory")
    local _, items = PZA.call(inv, "getItems")
    local ok, n = PZA.call(items, "size")
    if ok and type(n) == "number" then return n, inv end
    return 0, inv
end

-- the held item whose getID is id: inv:getItemById(id) first (the member the harness's inv.ids block uses,
-- PZTestKit_Client.lua L1641), then a walk of getItems() comparing getID; nil when absent
function K.itemById(p, id)
    local _, inv = PZA.call(p, "getInventory")
    local _, byId = PZA.call(inv, "getItemById", id)
    if byId ~= nil then return byId end
    local _, items = PZA.call(inv, "getItems")
    local okN, n = PZA.call(items, "size")
    if not okN or type(n) ~= "number" then return nil end
    for i = 0, n - 1 do
        local _, it = PZA.call(items, "get", i)
        local _, iid = PZA.call(it, "getID")
        if it ~= nil and iid == id then return it end
    end
    return nil
end

-- the check of a skill on one held item by id: itemId a number, the item held (none held)
local function itemCheck(args, p)
    local id = args.itemId
    if type(id) ~= "number" then return false, "bad args" end
    local it = K.itemById(p, id)
    if it == nil then return false, "none held" end
    return true, "", { id = id, item = it, queuedAt = nil }
end

-- ---- attack {targetId} ----------------------------------------------------------------------------------------------
-- One swing at the zombie whose online id is targetId (PZA.sense.zombieById, index-checked), the way the harness's
-- attack.melee swings (PZTestKit_Client.lua: faceThisObject(z), then DoAttack(0)), only within the held weapon's reach
-- (K.reachOf). check: the zombie alive within ATTACK_R of the player, else rejected no target (a check-time rejection
-- only); a held weapon, else no weapon. Beyond the reach one approach walk at a run (a sub-walk to the zombie's position)
-- for up to APPROACH_MS, then failed out of reach (a walk that fails, as one that cannot queue, ends it at once failed
-- with the walk's reason: no square, no path, stuck); within the reach the walk is cleared, the run dropped, and
-- faceThisObject(z) and DoAttack(0) are called once, DoAttack through PZA.call (index-first) under pcall, its return
-- never read (the jar: DoAttack always returns false). From the swing on, each tick reads isAttackStarted and
-- getMeleeDelay through PZA.call; done when attackStarted has read true and then false, or SWING_MS after the swing.
-- A target that reads dead mid-skill ends it done at once with the swings made so far (0 during the approach). Result
-- {swings (1 once DoAttack was called), attackStarted (true ever read), meleeDelay (the largest read, 0 when none),
-- targetDead (isDead at the end)}.
-- The reach (tiles) is the held weapon's, as the engine reads it for a swing's targets: weapon:getMaxRange(chr) *
-- weapon:getRangeMod(chr) (the jar's CombatManager.calcValidTargets L1445 and calculateHitListWeapon L2056). For a melee
-- weapon getMaxRange(chr) is the script's MaxRange (HandWeapon L879; the aiming term at L877 is for ranged weapons
-- only), and getRangeMod is 1.0, or 1.2 with the weapon's Blunt/Axe/Spear... perk at 7 or more (L491-L511). The
-- fallback is the 42.21 install's Base.BaseballBat MaxRange = 1.25 (scripts/generated/items/weapon.txt L6700), and
-- the margin keeps the swing inside the reach while both bodies move (run 1's fight 27 swung 210 s at a zombie 2.74
-- tiles off, out of reach).
K.ATTACK_R = 6            -- tiles: a target farther than this is no target
K.REACH_FALLBACK = 1.25
K.REACH_MARGIN = 0.9
K.APPROACH_MS = 4000      -- the approach walk's wall budget before out of reach
K.SWING_MS = 1500         -- a swing whose attack never starts and ends is done this long after DoAttack

-- the held weapon's reach in tiles: getMaxRange(p) * getRangeMod(p), or REACH_FALLBACK when either member is
-- absent or answers no number, times REACH_MARGIN
function K.reachOf(p, w)
    local okM, mx = PZA.call(w, "getMaxRange", p)
    local okR, rm = PZA.call(w, "getRangeMod", p)
    local r = K.REACH_FALLBACK
    if okM and okR and type(mx) == "number" and type(rm) == "number" then r = mx * rm end
    return r * K.REACH_MARGIN
end

-- the zombie whose online id is id through Sense, index-checked (nil while Sense does not provide it)
local function zombieById(p, id)
    local S = PZA.sense
    if S == nil or S.zombieById == nil then return nil end
    return S.zombieById(p, id)
end

local function zombieDead(z)
    local _, dead = PZA.call(z, "isDead")
    return dead == true
end

-- the distance from the player to the zombie and its position, each nil when unreadable
local function zombieDist(p, z)
    local zx, zy = posOf(z)
    if zx == nil or zy == nil then return nil, nil, nil end
    return dist(p, zx, zy), zx, zy
end

local function attackResult(st)
    return { swings = st.swings, attackStarted = st.started, meleeDelay = st.delay, targetDead = zombieDead(st.z) }
end

-- the approach and the swing: nil while the approach runs, else the skill's end
local function attackApproach(p, st)
    local _, w = PZA.call(p, "getPrimaryHandItem")
    if w == nil then return "failed", "no weapon" end
    local d, zx, zy = zombieDist(p, st.z)
    local now = PZA.now()
    if d ~= nil and d <= K.reachOf(p, w) then
        if st.sub ~= nil and st.sub.state == "running" then clearQueue(p) end
        st.sub = nil
        -- the approach's run dropped before the swing by construction: the wants off and both latches written false
        -- here, never left to the engine's per-frame wipe
        MO.want("walk")
        PZA.call(p, "setForceRun", false)
        PZA.call(p, "setForceSprint", false)
        PZA.call(p, "faceThisObject", st.z)
        local _, called = pcall(PZA.call, p, "DoAttack", 0)
        if called == true then st.swings = 1 end
        st.swungAt = now
        return nil
    end
    if st.sub == nil then
        if zx == nil then return "failed", "out of reach" end
        st.sub, st.approachAt = subWalk(zx, zy, "run"), now
    end
    if now - st.approachAt >= K.APPROACH_MS then return "failed", "out of reach" end
    -- a sub-walk that fails (no square, no path: it cannot queue; stuck) ends the attack at once with its reason
    if tickSub(p, st.sub) == "failed" then return "failed", st.sub.reason or "out of reach" end
    return nil
end

K.types.attack = {
    check = function(args, p)
        local id = args.targetId
        if type(id) ~= "number" then return false, "bad args" end
        local z = zombieById(p, id)
        if z == nil or zombieDead(z) then return false, "no target" end
        local d = zombieDist(p, z)
        if d == nil or d > K.ATTACK_R then return false, "no target" end
        local _, w = PZA.call(p, "getPrimaryHandItem")
        if w == nil then return false, "no weapon" end
        return true, "", { id = id, z = z, swings = 0, started = false, delay = 0, sub = nil, approachAt = nil,
                           swungAt = nil }
    end,
    tick = function(p, st)
        if isDead(p) then return "failed", "dead" end
        if zombieDead(st.z) then return "done", attackResult(st) end
        if st.swungAt == nil then
            local state, out = attackApproach(p, st)
            if state ~= nil or st.swungAt == nil then return state, out end
        end
        local _, started = PZA.call(p, "isAttackStarted")
        local _, delay = PZA.call(p, "getMeleeDelay")
        if type(delay) == "number" and delay > st.delay then st.delay = delay end
        if started == true then
            st.started = true
        elseif st.started then
            return "done", attackResult(st)
        end
        if PZA.now() - st.swungAt >= K.SWING_MS then return "done", attackResult(st) end
        return nil
    end,
}

-- ---- interact {x, y, kind, filter} ----------------------------------------------------------------------------------
-- kind open or close (Plan 21's open) and loot (Plan 21's loot) on square (x, y), floored to a world square as a scan
-- reports it. Both walk (a sub-walk at a walk) to the non-solid, non-solidTrans square at Chebyshev distance 1 nearest the
-- player unless the player stands within one square already, then queue the vanilla action; not adjacent when no such
-- square is free or the walk fails.
-- open or close: the square's door or window (openableOn), no square or no door when absent; done at once, or when it
-- later reads so, with result {open = IsOpen} once IsOpen reads the state asked for. An open's locked is read after the
-- toggle: a door or window still shut OPEN_MS after its queued open reads locked (locked from outside, a stuck door, a
-- smashed or invincible window); only a barricade fails it up front. A close still open after OPEN_MS is interrupted.
-- loot: ISInventoryTransferAction per item of the square's containers passing the filter (FILTERS); not loaded, no
-- container, empty or no match before any queue; done {moved} once the inventory grew by the queued count, or by one or
-- more when LOOT_MS + LOOT_ITEM_MS per queued item has passed; interrupted when it passes with none moved.
K.OPEN_MS = 5000          -- a queued open that leaves the door shut this long reads as locked
K.LOOT_MS = 10000         -- a loot's wall budget: this, plus LOOT_ITEM_MS per queued transfer
K.LOOT_ITEM_MS = 3000

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

-- walks next to (st.x, st.y): "here" once within one square, "walk" while the sub-walk runs, "fail" when
-- no square is free next to it or the walk failed
local function approach(p, st)
    if st.sub == nil then
        local c = cheb(p, st.x, st.y)
        if c ~= nil and c <= 1 then return "here" end
        local ax, ay = adjacentTo(p, st.x, st.y, floorOf(p))
        if ax == nil then return "fail" end
        st.sub = subWalk(ax + 0.5, ay + 0.5, "walk")
    end
    local s = tickSub(p, st.sub)
    if s == "running" then return "walk" end
    if s == "done" then return "here" end
    return "fail"
end

local function openTick(p, st)
    local want = st.kind == "open"
    if st.door == nil then
        local sq = squareAt(st.x, st.y, floorOf(p))
        if sq == nil then return "failed", "no square" end
        st.door, st.dkind = openableOn(sq)
        if st.door == nil then return "failed", "no door" end
    end
    local _, isOpen = PZA.call(st.door, "IsOpen")
    if isOpen == want then return "done", { open = isOpen } end
    if st.queuedAt == nil then
        if want then
            -- no isLocked pre-check: IsoDoor.ToggleDoorActual unlocks a door that canBeOpenFromInside
            local _, barricaded = PZA.call(st.door, "isBarricaded")
            if barricaded == true then return "failed", "locked" end
        end
        local at = approach(p, st)
        if at == "fail" then return "failed", "not adjacent" end
        if at == "walk" then return nil end
        local ctor = ISOpenCloseDoor
        if st.dkind == "window" then ctor = ISOpenCloseWindow end
        -- the vanilla class, its new and the queue's add index-checked before the call (no raise to catch)
        local ok, why = queueAction(ctor, "no door", nil, p, st.door)
        if not ok then return "failed", why end
        st.queuedAt = PZA.now()
        return nil
    end
    if PZA.now() - st.queuedAt > K.OPEN_MS then
        if want then return "failed", "locked" end
        return "failed", "interrupted"
    end
    return nil
end

-- every item of st.boxes passing st.filter, as {item, container}; and how many items and unloaded boxes were seen.
-- With st.maxWeight > 0 a pick is taken only while the inventory's getCapacityWeight (read once, plus each taken pick's
-- getWeight) stays within it; a pick left for the cap counts in st.skippedWeight. An unreadable inventory weight
-- applies no cap; an unreadable item weight counts 0.
local function lootPicks(st, p)
    local picks, seen, unloaded = {}, 0, 0
    local cap, weight = st.maxWeight or 0, 0
    if cap > 0 then
        local _, inv = PZA.call(p, "getInventory")
        local okW, cw = PZA.call(inv, "getCapacityWeight")
        if okW and type(cw) == "number" then weight = cw else cap = 0 end
    end
    st.skippedWeight = 0
    local keep = FILTERS[st.filter]
    for _, c in ipairs(st.boxes) do
        local okG, items = PZA.call(c, "getItems")
        local okS, n = PZA.call(items, "size")
        if okG and okS and type(n) == "number" then
            for i = 0, n - 1 do
                local _, it = PZA.call(items, "get", i)
                if it ~= nil then
                    seen = seen + 1
                    if keep(it) then
                        local take = true
                        if cap > 0 then
                            local okI, iw = PZA.call(it, "getWeight")
                            iw = (okI and type(iw) == "number") and iw or 0
                            take = weight + iw <= cap
                            if take then weight = weight + iw else st.skippedWeight = st.skippedWeight + 1 end
                        end
                        if take then picks[#picks + 1] = { it, c } end
                    end
                end
            end
        else
            unloaded = unloaded + 1
        end
    end
    return picks, seen, unloaded
end

local function lootTick(p, st)
    if st.boxes == nil then
        local sq = squareAt(st.x, st.y, floorOf(p))
        if sq == nil then return "failed", "not loaded" end
        st.boxes = containersOn(sq)
        if #st.boxes == 0 then return "failed", "no container" end
    end
    if st.queuedAt == nil then
        local at = approach(p, st)
        if at == "fail" then return "failed", "not adjacent" end
        if at == "walk" then return nil end
        local picks, seen, unloaded = lootPicks(st, p)
        if unloaded == #st.boxes then return "failed", "not loaded" end
        if seen == 0 then return "failed", "empty" end
        if #picks == 0 then return "failed", "no match" end   -- also when the cap left every match
        -- the vanilla transfer class, its new and the queue's add index-checked once before the loop: a missing
        -- one is the vanilla class not loaded, not "no match", so the skill fails not loaded
        local T = ISInventoryTransferAction
        if T == nil or T.new == nil or not queueLoaded() then return "failed", "not loaded" end
        local before, inv = invCount(p)
        local queued = 0
        for _, pick in ipairs(picks) do
            if queueAction(T, "no match", nil, p, pick[1], pick[2], inv) then queued = queued + 1 end
        end
        if queued == 0 then return "failed", "no match" end
        st.before, st.want, st.queuedAt = before, queued, PZA.now()
        return nil
    end
    local moved = math.max(0, (invCount(p)) - st.before)
    local late = PZA.now() - st.queuedAt > K.LOOT_MS + K.LOOT_ITEM_MS * st.want
    if moved >= st.want or (late and moved > 0) then return "done", { moved = moved, skipped = st.skippedWeight or 0 } end
    if late then return "failed", "interrupted" end
    return nil
end

K.types.interact = {
    check = function(args, p)
        local x, y, kind, filter = args.x, args.y, args.kind, args.filter
        if type(x) ~= "number" or type(y) ~= "number" or type(kind) ~= "string" or PZA.schema.ikinds[kind] ~= true then
            return false, "bad args"
        end
        if kind == "loot" then
            if filter == nil then filter = "all" end
            if type(filter) ~= "string" or FILTERS[filter] == nil then return false, "bad args" end
        end
        local maxWeight = args.maxWeight
        if maxWeight == nil then maxWeight = 0 end
        if type(maxWeight) ~= "number" or maxWeight < 0 then return false, "bad args" end
        return true, "", { x = math.floor(x), y = math.floor(y), kind = kind, filter = filter, maxWeight = maxWeight, sub = nil }
    end,
    tick = function(p, st)
        if isDead(p) then return "failed", "dead" end
        if st.kind == "loot" then return lootTick(p, st) end
        return openTick(p, st)
    end,
}

-- ---- equip {itemId} -------------------------------------------------------------------------------------------------
-- The held item by id (none held) into the primary hand, queued as the harness's weapon.equip queues it
-- (PZTestKit_Client.lua L1366-L1378): ISEquipWeaponAction:new(player, item, 50, true, item:isTwoHandWeapon()) through
-- ISTimedActionQueue.add, the timed action whose complete() the server runs too; the class, its new and the queue's add
-- index-checked first (not loaded). Done {itemId} once getPrimaryHandItem():getID() reads itemId (at once when it
-- already does), else interrupted after EQUIP_MS.
K.EQUIP_MS = 5000

local function primaryId(p)
    local _, w = PZA.call(p, "getPrimaryHandItem")
    local _, id = PZA.call(w, "getID")
    return id
end

K.types.equip = {
    check = itemCheck,
    tick = function(p, st)
        if isDead(p) then return "failed", "dead" end
        if primaryId(p) == st.id then return "done", { itemId = st.id } end
        if st.queuedAt == nil then
            local _, two = PZA.call(st.item, "isTwoHandWeapon")
            local ok, why = queueAction(ISEquipWeaponAction, "not valid", nil, p, st.item, 50, true, two == true)
            if not ok then return "failed", why end
            st.queuedAt = PZA.now()
            return nil
        end
        if PZA.now() - st.queuedAt > K.EQUIP_MS then return "failed", "interrupted" end
        return nil
    end,
}

-- ---- consume {itemId} -----------------------------------------------------------------------------------------------
-- The held item by id (none held): ISEatFoodAction:new(p, item, 1) when it answers IsFood true, ISDrinkFluidAction:new(
-- p, item, 1) when it answers a fluid container (getFluidContainer non-nil) that is drinkable, else not valid. A non-food
-- item is refused before ISEatFoodAction:new, whose getDuration calls the Food-only getBaseHunger (a caught raise still
-- parks a -debug client); ISEatFoodAction:isValid on an MP client checks the main inventory's containsID, which
-- isValidStart reads before the queue. Done {itemId} once the eat or drink is seen landing (the item gone from the
-- inventory by id, its getHungerChange changed for a food, its fluid amount fallen for a drink), else interrupted after
-- CONSUME_MS.
K.CONSUME_MS = 20000      -- an eat or drink not seen landing within this wall time is interrupted

-- bleach or petrol is never drunk (Act's firstDrink rule): a full type naming Bleach or Petrol, an empty container, or one
-- whose isPoisonous is not read false (fails closed: a container whose isPoisonous is absent is never drunk)
local function undrinkable(it, fc)
    if fullTypeHas(it, "Bleach", "Petrol") then return true end
    local _, empty = PZA.call(fc, "isEmpty")
    local okP, poison = PZA.call(fc, "isPoisonous")
    return empty == true or not okP or poison ~= false
end

-- the built action's isValidStart, index-checked before the call and under pcall: nil when it answers true, else not valid
local function validStart(action)
    if action.isValidStart == nil then return "not valid" end
    local okV, valid = pcall(action.isValidStart, action)
    if not okV or valid ~= true then return "not valid" end
    return nil
end

-- builds ctor:new(p, it, 1), checks its isValidStart and queues it; nil when queued, else the failure's reason: not
-- loaded when the class, its new or the queue's add is absent, not valid when the action refuses or raises. The class,
-- its new, the action's isValidStart and the queue's add are index-checked before each call (a missing one is a reason,
-- never a raise under pcall); the calls stay under pcall for a raise inside vanilla Lua (queueAction, vetted by validStart)
local function queueConsume(p, ctor, it)
    local _, why = queueAction(ctor, "not valid", validStart, p, it, 1)
    return why
end

local function consumeLanded(p, st)
    if K.itemById(p, st.id) == nil then return true end
    if st.fc ~= nil then
        local _, amount = PZA.call(st.fc, "getAmount")
        return amount ~= nil and st.amount ~= nil and amount < st.amount
    end
    local _, h = PZA.call(st.item, "getHungerChange")
    return h ~= nil and st.hunger ~= nil and h ~= st.hunger
end

K.types.consume = {
    check = itemCheck,
    tick = function(p, st)
        if isDead(p) then return "failed", "dead" end
        if st.queuedAt == nil then
            local _, food = PZA.call(st.item, "IsFood")
            local ctor = ISEatFoodAction
            if food == true then
                local _, h = PZA.call(st.item, "getHungerChange")
                st.hunger = h
            else
                local _, fc = PZA.call(st.item, "getFluidContainer")
                if fc == nil or undrinkable(st.item, fc) then return "failed", "not valid" end
                local _, amount = PZA.call(fc, "getAmount")
                ctor, st.fc, st.amount = ISDrinkFluidAction, fc, amount
            end
            local why = queueConsume(p, ctor, st.item)
            if why ~= nil then return "failed", why end
            st.queuedAt = PZA.now()
            return nil
        end
        if consumeLanded(p, st) then return "done", { itemId = st.id } end
        if PZA.now() - st.queuedAt > K.CONSUME_MS then return "failed", "interrupted" end
        return nil
    end,
}

-- ---- drop {itemId} --------------------------------------------------------------------------------------------------
-- The held item by id (none held) onto the player's own square through vanilla's own floor drop,
-- ISDropWorldItemAction:new(character, item, sq, xoffset, yoffset, zoffset, rotation, isMultiple) (the 42.21 install's
-- media/lua/shared/TimedActions/ISDropWorldItemAction.lua:157; probe X3's heavy-load drain). The class, its new, the
-- queue's add and the player's getCurrentSquare are index-checked first (not loaded); the queue add stays under pcall
-- for a raise inside vanilla Lua (not valid). Done {moved = 1} once the item is gone by id or the inventory's size has
-- fallen; interrupted when LOOT_MS + LOOT_ITEM_MS passes first.
K.types.drop = {
    check = itemCheck,
    tick = function(p, st)
        if isDead(p) then return "failed", "dead" end
        if st.queuedAt == nil then
            local okS, sq = PZA.call(p, "getCurrentSquare")
            if not okS or sq == nil then return "failed", "not loaded" end
            st.before = (invCount(p))
            local ok, why = queueAction(ISDropWorldItemAction, "not valid", nil, p, st.item, sq, 0, 0, 0, 0, false)
            if not ok then return "failed", why end
            st.queuedAt = PZA.now()
            return nil
        end
        if K.itemById(p, st.id) == nil or (invCount(p)) < st.before then return "done", { moved = 1 } end
        if PZA.now() - st.queuedAt > K.LOOT_MS + K.LOOT_ITEM_MS then return "failed", "interrupted" end
        return nil
    end,
}
