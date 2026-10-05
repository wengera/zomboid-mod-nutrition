-- PZTestKit client side, body half (slice 03).
--
-- Separate file from PZTestKit_Client.lua purely so the two slices' edits do not collide;
-- it is loaded by the same client Lua state and registers into the same TK command table.
--
-- What lives here is the CLIENT MIRROR of the body-side state, and it is a mirror in the
-- strict sense: hunger, thirst, endurance and the whole Nutrition block tick only on the
-- server in MP (03-notes Q7 -- `updateStats_WakeState @8-@26 L10227`,
-- `updateThirst @38-@73 L10377`, `updateEndurance @0-@13 L3427`, `Nutrition.update @42 L75`),
-- and reach this side as an unconditional full snapshot in `PlayerStatsPacket` at 1 Hz.
-- So a reading taken here is never a measurement of a rate; it is a measurement of what the
-- packet carries and how far behind it runs. Two rows use exactly that:
--   * client `stats.set hunger 0.9` reverting  -> the server owns the stat (row 13)
--   * client `nutrition.set weight 105` reverting, and `hasTrait("Obese")` staying false
--     -> `updateWeight`'s `setWeight` and `applyTraitFromWeight` are both behind the
--        `GameClient.client` early-out at `@317-@320 L198` (row 14)
-- Moodles are the one thing recomputed locally on both sides (`Moodles.Update` has no side
-- guard), which is why the snapshot carries them here too: a client moodle level is a pure
-- function of this side's possibly-stale stats.

-- The client twin of the server's `stats.get <user>`: same shape, same TK.bodySnapshot, no
-- username argument (a client only ever has its own player).
-- @args (none)
-- @reply {calories, carbs, lipids, proteins, weight, hunger, thirst, statsApi, incWeight, incWeightLot, decWeight, endurance, fatigue, moodles, traits, traitList, traitRoute, maxWeight, foodTimer, standardFoodTime, asleep, running, sprinting, moving, worldAge, mult, wall} | string
-- @purpose One atomic client-side body snapshot of the local player -- a mirror of the last 1 Hz PlayerStatsPacket, never a rate.
TK.register("stats.get", function()
    local p = getPlayer()
    if not p then return "no local player" end
    return TK.bodySnapshot(p)
end)

-- <dx> <dy> [run]: ONE attempt at the moving-burn rows (03-notes matrix rows 3 and 4).
--
-- The three moving branches of `Nutrition.updateCalories` are picked by
-- `parent.IsRunning() && parent.isPlayerMoving()` etc. on the SERVER's copy of the character,
-- and the server's copy of a remote player's movement comes from this client's position
-- updates -- so the walk has to be started here, not there. This is the game's own route
-- (`ISTimedActionQueue.add(ISWalkToTimedAction:new(chr, square))`, ISBBQMenu.lua:91), minus
-- the context menu that normally picks the square.
--
-- It is one attempt by ruling: if the server-side snapshot does not report `moving` true
-- while this runs, rows 3-6 are recorded n/a rather than chased. Nothing here is retried and
-- nothing here is required by another row.
-- @args <dx> <dy> [run]
-- @reply {dx, dy, run, from [, error], target [, setRunning], queued [, queueError], clientRunning, clientMoving} | string
-- @purpose Queues the game's own walk action to the square dx,dy away from the client, so the server's copy of the player actually moves.
TK.register("player.walk", function(argv)
    local p = getPlayer()
    if not p then return "no local player" end
    local dx, dy = tonumber(argv[1]), tonumber(argv[2])
    if dx == nil or dy == nil then return "usage: player.walk <dx> <dy> [run]" end
    local out = { dx = dx, dy = dy, run = (argv[3] == "run"),
                  from = { x = p:getX(), y = p:getY(), z = p:getZ() } }
    local cell = getCell()
    if not cell then return "no getCell()" end
    local ok, sq = TK.call(cell, "getGridSquare", p:getX() + dx, p:getY() + dy, p:getZ())
    if not ok or sq == nil then
        out.error = "no grid square at +" .. tostring(dx) .. "," .. tostring(dy)
        return out
    end
    out.target = { x = sq:getX(), y = sq:getY(), z = sq:getZ() }
    if not ISWalkToTimedAction or not ISTimedActionQueue then
        out.error = "no ISWalkToTimedAction/ISTimedActionQueue"
        return out
    end
    -- setRunning before the action is queued: ISWalkToTimedAction does not set it, and the
    -- run flag is half of `IsRunning() && isPlayerMoving()`.
    if argv[3] == "run" then out.setRunning = TK.call(p, "setRunning", true) end
    local ran, err = pcall(function()
        ISTimedActionQueue.add(ISWalkToTimedAction:new(p, sq))
    end)
    out.queued = ran
    if not ran then out.queueError = tostring(err) end
    local _, running = TK.call(p, "IsRunning")
    local _, moving = TK.call(p, "isPlayerMoving")
    out.clientRunning, out.clientMoving = running, moving
    return out
end)

-- Stop whatever `player.walk` started, so a half-finished path cannot bleed into the next
-- condition's idle window.
-- @args (none)
-- @reply {cleared [, clearError], setRunning, clientMoving} | string
-- @purpose Clears the client's timed-action queue and unsets running, so a half-finished path cannot bleed into the next window.
TK.register("player.stop", function()
    local p = getPlayer()
    if not p then return "no local player" end
    local out = {}
    -- There is no ISTimedActionQueue.clear; the queue object is fetched and cleared
    -- (ISTimedActionQueue.lua:148 / :46).
    if ISTimedActionQueue and ISTimedActionQueue.getTimedActionQueue then
        local ran, err = pcall(function()
            ISTimedActionQueue.getTimedActionQueue(p):clearQueue()
        end)
        out.cleared = ran
        if not ran then out.clearError = tostring(err) end
    end
    out.setRunning = TK.call(p, "setRunning", false)
    local _, moving = TK.call(p, "isPlayerMoving")
    out.clientMoving = moving
    return out
end)

TK.log("client body harness loaded")

-- <dx> <dy>: the run arm of player.walk, ONE bounded attempt (Plan 2 Task 12). Plan 1 read that
-- `player.walk <dx> <dy> run` only walked: setRunning(true) before ISWalkToTimedAction did not
-- make the character run (#2082). Reading the vanilla action (client/TimedActions/
-- WalkToTimedAction.lua) shows it never touches a run flag -- start() only calls
-- getPathFindBehavior2():pathToLocation and update() only steps that behaviour -- so there is no
-- run flag on the action to drive. The one run-related member the jar exposes on the path side is
-- IsoPlayer.setPathfindRunning(Z) / isPathfindRunning() (a bare boolean field, `pathfindRun`);
-- IsoCharacter has no setForceRun. So the route tried is: setRunning(true) + setForceRun(true)
-- if that member exists (it is expected not to; the reply records it) + setPathfindRunning(true),
-- then the same queued walk. Whether the server's copy reports running+moving is the measurement;
-- the driver reads `stats.get <user>` running/moving. Nothing here is retried; if it does not run
-- the residual arm stays unmeasured.
-- @args <dx> <dy>
-- @reply {dx, dy, target, setRunning, setForceRun, setPathfindRunning [, queued] [, queueError], clientRunning, clientMoving, clientSprinting} | string
-- @purpose Sets running and the pathfind run flag on the local player then queues the game's own walk action dx,dy away; one bounded attempt at making the walk actually run.
TK.register("player.run", function(argv)
    local p = getPlayer()
    if not p then return "no local player" end
    local dx, dy = tonumber(argv[1]), tonumber(argv[2])
    if dx == nil or dy == nil then return "usage: player.run <dx> <dy>" end
    local out = { dx = dx, dy = dy }
    local cell = getCell()
    if not cell then return "no getCell()" end
    local ok, sq = TK.call(cell, "getGridSquare", p:getX() + dx, p:getY() + dy, p:getZ())
    if not ok or sq == nil then
        out.error = "no grid square at +" .. tostring(dx) .. "," .. tostring(dy)
        return out
    end
    out.target = { x = sq:getX(), y = sq:getY(), z = sq:getZ() }
    if not ISWalkToTimedAction or not ISTimedActionQueue then
        out.error = "no ISWalkToTimedAction/ISTimedActionQueue"
        return out
    end
    out.setRunning = TK.call(p, "setRunning", true)
    out.setForceRun = TK.call(p, "setForceRun", true)
    out.setPathfindRunning = TK.call(p, "setPathfindRunning", true)
    local ran, err = pcall(function()
        ISTimedActionQueue.add(ISWalkToTimedAction:new(p, sq))
    end)
    out.queued = ran
    if not ran then out.queueError = tostring(err) end
    local _, running = TK.call(p, "IsRunning")
    local _, moving = TK.call(p, "isPlayerMoving")
    local _, sprinting = TK.call(p, "isSprinting")
    out.clientRunning, out.clientMoving, out.clientSprinting = running, moving, sprinting
    return out
end)

-- <trait> <seconds>. Arms an OnTick watcher on the CLIENT (tick.rate's arm-and-result-doc
-- pattern): each tick it reads the local player's trait list (TK.traitNames, the list stats.get
-- builds traitList from, lowercased) and on the FIRST tick the trait is present writes the result
-- doc trait-watch.json {trait, armedWall, firstSeenWall, ticks, found = true} through TK.result and
-- unarms; at the deadline with no sighting it writes found = false. It answers at once. The driver
-- arms it, calls the server's trait.add.push, then wait_result("trait-watch"): firstSeenWall minus
-- the server's wallAfter is the push arm's latency with a client-side first-change stamp.
TK.traitWatch = TK.traitWatch or { armed = false }
local TRAIT_WATCH_MAX_SECONDS = 600

local function traitWatchOnTick()
    local w = TK.traitWatch
    if not w.armed then return end
    local p = getPlayer()
    w.ticks = w.ticks + 1
    local now = TK.now()
    if p ~= nil then
        local set = TK.traitNames(p)
        if TK.hasTraitName(set, w.trait) then
            w.armed = false
            TK.result("trait-watch", { trait = w.trait, armedWall = w.armedWall,
                                       firstSeenWall = now, ticks = w.ticks, found = true })
            return
        end
    end
    if now >= w.deadline then
        w.armed = false
        TK.result("trait-watch", { trait = w.trait, armedWall = w.armedWall,
                                   deadlineWall = w.deadline, ticks = w.ticks, found = false })
    end
end

if not TK.traitWatchHooked and Events ~= nil and Events.OnTick ~= nil then
    Events.OnTick.Add(function() traitWatchOnTick() end)
    TK.traitWatchHooked = true
end

-- @args <trait> <seconds>
-- The result document trait-watch.json: {trait, armedWall, firstSeenWall, ticks, found} or, with no
--   sighting by the deadline, {trait, armedWall, deadlineWall, ticks, found = false}, plus
--   TK.result's own {name, side, t, complete}.
-- @reply {armed, trait, seconds, result, file} | {error} | string
-- @purpose Arms a client OnTick watcher for one trait and answers at once; trait-watch.json (wait_result) then carries the wall stamp of the first tick the local player has it.
TK.register("trait.watch", function(argv)
    local trait = argv[1]
    local seconds = tonumber(argv[2])
    if trait == nil or seconds == nil or seconds <= 0 or seconds > TRAIT_WATCH_MAX_SECONDS then
        return "usage: trait.watch <trait> <seconds>  (0 < seconds <= 600)"
    end
    if not TK.traitWatchHooked then return { error = "no Events.OnTick on this side" } end
    if TK.traitWatch.armed then return { error = "a trait.watch window is already armed" } end
    local start = TK.now()
    if start == 0 then return { error = "no getTimestampMs()" } end
    TK.traitWatch = { armed = true, trait = trait, seconds = seconds, ticks = 0,
                      armedWall = start, deadline = start + seconds * 1000 }
    return { armed = true, trait = trait, seconds = seconds, result = "trait-watch",
             file = "pzt-results/trait-watch.json" }
end)

-- ---- Plan 4 Task 3: the kinetics harness wave (client commands) -------------------------------

-- The local player a client command acts on. `user` is the bus argument: a client only ever has
-- its own player, so "-" or the local username is accepted and any other name is refused rather
-- than silently acting on the wrong character.
local function kineticsPlayer(user)
    if getPlayer == nil then return nil, "no getPlayer() on this side" end
    local p = getPlayer()
    if p == nil then return nil, "no local player" end
    if user ~= nil and user ~= "-" then
        local _, me = TK.call(p, "getUsername")
        if me ~= nil and me ~= user then return nil, "local player is " .. tostring(me) .. ", not " .. tostring(user) end
    end
    return p
end

-- <user> <StatName> <value>. The client twin of the server stats.setany; a client write is
-- expected to be overwritten by the 1 Hz PlayerStatsPacket for any stat the server owns, which is
-- the discriminator. Resolution and read-back are the server command's.
-- @args <user> <StatName> <value>
-- @reply {ok, stat, side, requested, before, after [, reason]} | string
-- @purpose Client-side write of any CharacterStat by enum name on the local player, replying the value read before and after the write.
TK.register("stats.setany", function(argv)
    local p, why = kineticsPlayer(argv[1])
    if p == nil then return { ok = false, reason = why } end
    local name, v = argv[2], tonumber(argv[3])
    if name == nil or v == nil then return "usage: stats.setany <user> <StatName> <value>" end
    local out = { ok = false, stat = name, side = TK.side, requested = v }
    local enum = nil
    if CharacterStat ~= nil then
        enum = CharacterStat[name]
        if enum == nil and CharacterStat["valueOf"] ~= nil then
            local ran, e = pcall(CharacterStat["valueOf"], name)
            if ran then enum = e end
        end
    end
    if enum == nil then
        out.reason = "no CharacterStat." .. tostring(name)
        return out
    end
    local _, s = TK.call(p, "getStats")
    if s == nil then
        out.reason = "no getStats()"
        return out
    end
    local _, before = TK.call(s, "get", enum)
    out.before = before
    local ran, err = pcall(s["set"], s, enum, v)
    if not ran then
        out.reason = "Stats:set raised: " .. tostring(err)
        return out
    end
    local _, after = TK.call(s, "get", enum)
    out.after = after
    out.ok = (after ~= nil)
    if not out.ok then out.reason = "no read-back" end
    return out
end)

-- <user> <fullType> <fluidType> <litres>. Spawns the container item on the CLIENT (item.spawn path:
-- getInventory():AddItem, which the server never hears of), empties its FluidContainer and adds
-- `litres` of the named fluid. The fluid is resolved as FluidType.FromNameLower(name lowercased),
-- the call ISFluidContainerMenu makes, then FluidType[name]; the add is
-- FluidContainer:addFluid(FluidType, litres), all under pcall so a bad name or a full container
-- replies ok=false. The container is read back (getAmount, getPrimaryFluid:getFluidTypeString).
-- @args <user> <fullType> <fluidType> <litres>
-- @reply {ok, side, fullType, id, requested, litres, fluid, capacity [, reason]} | string
-- @purpose Spawns a fluid-container item on the client, empties it and adds the named litres of a fluid, replying the amount and primary fluid read back.
TK.register("fluid.fill", function(argv)
    local p, why = kineticsPlayer(argv[1])
    if p == nil then return { ok = false, reason = why } end
    local fullType, fluidName, litres = argv[2], argv[3], tonumber(argv[4])
    if fullType == nil or fluidName == nil or litres == nil then
        return "usage: fluid.fill <user> <fullType> <fluidType> <litres>"
    end
    local out = { ok = false, side = TK.side, fullType = fullType, requested = litres }
    local _, inv = TK.call(p, "getInventory")
    local _, item = TK.call(inv, "AddItem", fullType)
    if item == nil then
        out.reason = "AddItem gave nothing for " .. fullType
        return out
    end
    local _, id = TK.call(item, "getID")
    out.id = id
    local _, fc = TK.call(item, "getFluidContainer")
    if fc == nil then
        out.reason = "no FluidContainer on " .. fullType
        return out
    end
    local enum = nil
    if FluidType ~= nil then
        if FluidType["FromNameLower"] ~= nil then
            local ran, e = pcall(FluidType["FromNameLower"], string.lower(fluidName))
            if ran then enum = e end
        end
        if enum == nil then enum = FluidType[fluidName] end
    end
    if enum == nil then
        out.reason = "no FluidType for " .. fluidName
        return out
    end
    local ranE, errE = pcall(fc["Empty"], fc)
    if not ranE then
        out.reason = "Empty raised: " .. tostring(errE)
        return out
    end
    local ran, err = pcall(fc["addFluid"], fc, enum, litres)
    if not ran then
        out.reason = "addFluid raised: " .. tostring(err)
        return out
    end
    local _, amount = TK.call(fc, "getAmount")
    local _, cap = TK.call(fc, "getCapacity")
    local _, prim = TK.call(fc, "getPrimaryFluid")
    local _, fname = TK.call(prim, "getFluidTypeString")
    out.litres = amount
    out.capacity = cap
    out.fluid = fname
    out.ok = (amount ~= nil and math.abs(amount - litres) < 0.001)
    if not out.ok then out.reason = "amount read back is not the amount added (capacity?)" end
    return out
end)

-- <user> <fullType>. Spawns the pill on the CLIENT (item.spawn path) and queues
-- ISTakePillAction:new(player, item) through ISTimedActionQueue.add, the pair the inventory
-- context menu uses (ISInventoryPaneContextMenu.onPillsItems). The action runs on the client and
-- reaches the server through the game timed-action sync; whether the server has a copy of the
-- item to consume is the gate measurement, not this reply.
-- @args <user> <fullType>
-- @reply {queued, side, fullType, id [, reason]} | string
-- @purpose Spawns a pill item on the client and queues an ISTakePillAction on it for the local player, replying whether it was queued.
TK.register("pill.take", function(argv)
    local p, why = kineticsPlayer(argv[1])
    if p == nil then return { queued = false, reason = why } end
    local fullType = argv[2]
    if fullType == nil then return "usage: pill.take <user> <fullType>" end
    local out = { queued = false, side = TK.side, fullType = fullType }
    if ISTakePillAction == nil or ISTimedActionQueue == nil then
        out.reason = "no ISTakePillAction/ISTimedActionQueue on this side"
        return out
    end
    local _, inv = TK.call(p, "getInventory")
    local _, item = TK.call(inv, "AddItem", fullType)
    if item == nil then
        out.reason = "not in inventory: AddItem gave nothing for " .. fullType
        return out
    end
    local _, id = TK.call(item, "getID")
    out.id = id
    local ran, err = pcall(function()
        ISTimedActionQueue.add(ISTakePillAction:new(p, item))
    end)
    out.queued = ran
    if not ran then out.reason = "queue raised: " .. tostring(err) end
    return out
end)

-- <user>. Finds the nearest square within 10 tiles on the player floor holding an object whose
-- hasWater() is true (getCell():getGridSquare(x, y, z) -> getObjects() -> IsoObject:hasWater()),
-- walks to it the way ISWorldObjectContextMenu.onDrink does (luautils.walkAdjObject) and queues
-- ISTakeWaterAction:new(player, nil, source, source:isTaintedWater()); the nil container item is
-- the drink-from-the-source branch. No source in range replies ok=false, reason "no source".
-- @args <user>
-- @reply {ok, queued, side, source, fluidAmount, tainted [, reason]} | string
-- @purpose Queues the vanilla drink-from-source ISTakeWaterAction on the nearest water-bearing object within 10 tiles, replying the source found or no source.
TK.register("water.take", function(argv)
    local p, why = kineticsPlayer(argv[1])
    if p == nil then return { ok = false, queued = false, reason = why } end
    local out = { ok = false, queued = false, side = TK.side }
    if ISTakeWaterAction == nil or ISTimedActionQueue == nil then
        out.reason = "no ISTakeWaterAction/ISTimedActionQueue on this side"
        return out
    end
    local _, cell = TK.call(p, "getCell")
    local _, px = TK.call(p, "getX")
    local _, py = TK.call(p, "getY")
    local _, pz = TK.call(p, "getZ")
    if cell == nil or px == nil or py == nil or pz == nil then
        out.reason = "no cell or player position"
        return out
    end
    local bx, by, bz = math.floor(px), math.floor(py), math.floor(pz)
    local best, bestD, bestAt = nil, nil, nil
    for dx = -10, 10 do
        for dy = -10, 10 do
            local _, sq = TK.call(cell, "getGridSquare", bx + dx, by + dy, bz)
            local _, objs = TK.call(sq, "getObjects")
            local _, n = TK.call(objs, "size")
            local i = 0
            while n ~= nil and i < n do
                local _, o = TK.call(objs, "get", i)
                local ranW, w = pcall(function() return o["hasWater"](o) end)
                if ranW and w == true then
                    local d = dx * dx + dy * dy
                    if bestD == nil or d < bestD then
                        best, bestD, bestAt = o, d, { x = bx + dx, y = by + dy, z = bz }
                    end
                end
                i = i + 1
            end
        end
    end
    if best == nil then
        out.reason = "no source"
        return out
    end
    local _, nm = TK.call(best, "getObjectName")
    local _, amt = TK.call(best, "getFluidAmount")
    local _, tainted = TK.call(best, "isTaintedWater")
    out.source = { at = bestAt, name = nm, dist = math.floor(math.sqrt(bestD) * 10 + 0.5) / 10 }
    out.fluidAmount = amt
    out.tainted = tainted
    local ran, err = pcall(function()
        if luautils ~= nil and luautils.walkAdjObject ~= nil then
            if not luautils.walkAdjObject(p, best, true, true) then error("walkAdjObject refused the source") end
        end
        ISTimedActionQueue.add(ISTakeWaterAction:new(p, nil, best, tainted == true))
    end)
    out.queued = ran
    out.ok = ran
    if not ran then out.reason = "queue raised: " .. tostring(err) end
    return out
end)

-- <user> <fullType>. pill.take's held twin (Plan 4 Task 5): pill.take spawns its pill on the
-- client, so the server's copy of the action has no item to consume. This command spawns nothing:
-- it takes the FIRST item of the type already in the local inventory (getFirstTypeRecurse -- an
-- RCON `additem` copy, which both sides hold) and queues ISTakePillAction:new(player, item)
-- through ISTimedActionQueue.add, the pair the inventory context menu uses. No such item replies
-- queued=false with reason "not in inventory".
-- @args <user> <fullType>
-- @reply {queued, side, fullType, id [, reason]} | string
-- @purpose Queues ISTakePillAction on the first pill of the type already in the local player's inventory (no spawn), so a server-visible pill is the one taken.
TK.register("pill.take.held", function(argv)
    local p, why = kineticsPlayer(argv[1])
    if p == nil then return { queued = false, reason = why } end
    local fullType = argv[2]
    if fullType == nil then return "usage: pill.take.held <user> <fullType>" end
    local out = { queued = false, side = TK.side, fullType = fullType }
    if ISTakePillAction == nil or ISTimedActionQueue == nil then
        out.reason = "no ISTakePillAction/ISTimedActionQueue on this side"
        return out
    end
    local _, inv = TK.call(p, "getInventory")
    local _, item = TK.call(inv, "getFirstTypeRecurse", fullType)
    if item == nil then
        out.reason = "not in inventory"
        return out
    end
    local _, id = TK.call(item, "getID")
    out.id = id
    local ran, err = pcall(function()
        ISTimedActionQueue.add(ISTakePillAction:new(p, item))
    end)
    out.queued = ran
    if not ran then out.reason = "queue raised: " .. tostring(err) end
    return out
end)
