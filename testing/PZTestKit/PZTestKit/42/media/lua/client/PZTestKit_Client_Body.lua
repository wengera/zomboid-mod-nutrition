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

-- ---- Plan 5 Task 2: the effects harness wave (client commands) --------------------------------

-- Plan 5 helpers for the client state, one local (P5). hop is the index-first, pcall'd call:
-- an absent member or a raise answers nil, never an error on the -debug client.
local P5 = {}

function P5.hop(obj, name, ...)
    if obj == nil then return nil end
    local f = obj[name]
    if f == nil then return nil end
    local ran, v = pcall(f, obj, ...)
    if not ran then return nil end
    return v
end

function P5.part(p, i)
    local bd = P5.hop(p, "getBodyDamage")
    if bd == nil or BodyPartType == nil then return nil, nil end
    local fromIndex = BodyPartType["FromIndex"]
    if fromIndex == nil then return nil, nil end
    local ran, t = pcall(fromIndex, i)
    if not ran or t == nil then return nil, nil end
    return P5.hop(bd, "getBodyPart", t), t
end

P5.PART_GETTERS = {
    { "health", "getHealth" }, { "bleedingTime", "getBleedingTime" }, { "bleeding", "bleeding" },
    { "deepWoundTime", "getDeepWoundTime" }, { "scratchTime", "getScratchTime" },
    { "cutTime", "getCutTime" }, { "biteTime", "getBiteTime" }, { "burnTime", "getBurnTime" },
    { "fractureTime", "getFractureTime" }, { "woundInfectionLevel", "getWoundInfectionLevel" },
    { "infectedWound", "isInfectedWound" }, { "additionalPain", "getAdditionalPain" },
    { "bandaged", "bandaged" }, { "alcoholLevel", "getAlcoholLevel" },
}

function P5.partRow(part, t, i)
    local row = { index = i }
    if BodyPartType ~= nil and BodyPartType["ToString"] ~= nil and t ~= nil then
        local ran, nm = pcall(BodyPartType["ToString"], t)
        if ran then row.name = nm end
    end
    for _, g in ipairs(P5.PART_GETTERS) do
        local v = P5.hop(part, g[2])
        if v == nil then row["absent_" .. g[1]] = true else row[g[1]] = v end
    end
    return row
end

-- <user> <partIndex|all>. The client twin of the server bodypart.get: the same getters on the
-- local player's own BodyDamage, so a server write that syncBodyPart carried shows here as the
-- same value and one that it did not shows as the stale one.
-- @args <user> <partIndex|all>
-- @reply {ok, side, parts [, reason]} | string
-- @purpose Client twin of bodypart.get: reads the per-part wound fields of one or all body parts of the local player, to compare against the server's after a syncBodyPart.
TK.register("bodypart.get", function(argv)
    local p, why = kineticsPlayer(argv[1])
    if p == nil then return { ok = false, reason = why } end
    local which = argv[2] or "all"
    local out = { ok = false, side = TK.side, parts = {} }
    local bd = P5.hop(p, "getBodyDamage")
    if bd == nil then
        out.reason = "no getBodyDamage()"
        return out
    end
    local first, last = 0, 0
    if which == "all" then
        local n = P5.hop(P5.hop(bd, "getBodyParts"), "size")
        if n == nil then
            out.reason = "no getBodyParts():size()"
            return out
        end
        first, last = 0, n - 1
    else
        first = tonumber(which)
        if first == nil then return "usage: bodypart.get <user> <partIndex|all>" end
        last = first
    end
    for i = first, last do
        local part, t = P5.part(p, i)
        if part == nil then
            out.reason = "no body part at index " .. i
            if which ~= "all" then return out end
        else
            out.parts[#out.parts + 1] = P5.partRow(part, t, i)
        end
    end
    out.ok = (#out.parts > 0)
    return out
end)

-- The client reading of overall and per-part health: getOverallBodyHealth(), getHealth() and
-- BodyPart:getHealth() walked by size()/get(i) over getBodyParts() (a Java list, never #).
function P5.healthRead(p)
    local bd = P5.hop(p, "getBodyDamage")
    local r = { overall = P5.hop(bd, "getOverallBodyHealth"), health = P5.hop(bd, "getHealth"), parts = {} }
    local list = P5.hop(bd, "getBodyParts")
    local n = P5.hop(list, "size")
    local i = 0
    while n ~= nil and i < n do
        r.parts[#r.parts + 1] = P5.hop(P5.hop(list, "get", i), "getHealth")
        i = i + 1
    end
    return r
end

-- <user>. The client twin of the server health.get: the local player's overall and per-part
-- health as this side holds them, to be read beside the server's after a ReduceGeneralHealth.
-- @args <user>
-- @reply {ok, side, overall, health, parts [, reason]} | string
-- @purpose Client twin of health.get: reads the local player's overall body health, BodyDamage health and per-part health list.
TK.register("health.get", function(argv)
    local p, why = kineticsPlayer(argv[1])
    if p == nil then return { ok = false, reason = why } end
    local r = P5.healthRead(p)
    return { ok = (r.overall ~= nil), side = TK.side, overall = r.overall, health = r.health, parts = r.parts }
end)

-- The client landing listener: the twin of the server's, installed once by the first
-- fall.probe on this side, never raising (every body under pcall), keeping up to 20 FALLDOWN
-- records (side, amount, wall) and a count of every tag in P5.fall.
P5.fall = { list = {}, counts = {}, hooked = false }

function P5.fallHook()
    if P5.fall.hooked or TK.p5FallHooked then
        P5.fall.hooked = true
        return true
    end
    if Events == nil or Events.OnPlayerGetDamage == nil then return false end
    Events.OnPlayerGetDamage.Add(function(character, tag, amount)
        pcall(function()
            local t = tostring(tag)
            P5.fall.counts[t] = (P5.fall.counts[t] or 0) + 1
            if t == "FALLDOWN" and #P5.fall.list < 20 then
                P5.fall.list[#P5.fall.list + 1] = { side = TK.side, amount = amount, wall = TK.now() }
            end
        end)
    end)
    TK.p5FallHooked = true
    P5.fall.hooked = true
    return true
end

function P5.legFractures(p)
    local out = { legs = {}, maxFracture = 0 }
    local bd = P5.hop(p, "getBodyDamage")
    local list = P5.hop(bd, "getBodyParts")
    local n = P5.hop(list, "size")
    local i = 0
    while n ~= nil and i < n do
        local part = P5.hop(list, "get", i)
        local ft = P5.hop(part, "getFractureTime")
        local nm = nil
        local t = P5.hop(part, "getType")
        if t ~= nil and BodyPartType ~= nil and BodyPartType["ToString"] ~= nil then
            local ran, s = pcall(BodyPartType["ToString"], t)
            if ran then nm = s end
        end
        if ft ~= nil and ft > out.maxFracture then out.maxFracture = ft end
        local low = string.lower(tostring(nm))
        if ft ~= nil and (string.find(low, "leg", 1, true) or string.find(low, "foot", 1, true)) then
            out.legs[#out.legs + 1] = tostring(nm) .. "=" .. tostring(ft)
        end
        i = i + 1
    end
    return out
end

-- The fall watcher: after a push, an OnTick sampler records z, isbFalling and the fall time
-- every 250 ms of wall time for up to 8 s, then writes fall-probe.json with the series, the
-- FALLDOWN records this side heard and the leg fracture times. One window at a time.
TK.p5FallWatch = TK.p5FallWatch or { armed = false }

local function p5FallOnTick()
    local w = TK.p5FallWatch
    if not w.armed then return end
    local now = TK.now()
    if now < w.nextAt then return end
    local p = getPlayer()
    if p == nil then return end
    w.nextAt = now + 250
    local z = P5.hop(p, "getZ")
    local f = P5.hop(p, "isbFalling")
    w.series[#w.series + 1] = "dt=" .. tostring(now - w.start) .. " z=" .. tostring(z) .. " falling=" .. tostring(f)
    if now >= w.deadline then
        w.armed = false
        local fr = P5.legFractures(p)
        TK.result("fall-probe", { series = w.series, fall = P5.fall.list, counts = P5.fall.counts,
                                  legs = fr.legs, maxFracture = fr.maxFracture, pushedZ = w.pushedZ })
    end
end

if not TK.p5FallTickHooked and Events ~= nil and Events.OnTick ~= nil then
    Events.OnTick.Add(function() p5FallOnTick() end)
    TK.p5FallTickHooked = true
end

-- <user> <z> [land <f>]. The CLIENT half of the landing probe: installs this side's
-- OnPlayerGetDamage listener, then raises the local player by z tiles with
-- IsoMovingObject:setZ(z0 + z) and sets isbFalling true (setbFalling) with the fall time reset to
-- 0 (setFallTime), so the engine's own falling state can land it; the client owns the position of
-- its player, the server reads it from the position packets. With `land <f>` it ALSO calls
-- IsoGameCharacter:DoLand(f) at once (the landing impact entry, which fires FALLDOWN when the
-- damage is nonzero) -- a direct arm for the case the height push does not fall. An OnTick
-- watcher samples z, isbFalling every 250 ms for 8 s and writes fall-probe.json with the series,
-- this side's FALLDOWN records and the leg fracture times. Where no height write is accepted the
-- reply is {ok=false, reason}; the listener half still stands.
-- @args <user> <z> [land <f>]
-- @reply {ok, side, hooked, zBefore, zAfter, falling, result, file [, landCalled] [, reason]} | string
-- @purpose Installs the client OnPlayerGetDamage listener for FALLDOWN, raises the local player by z tiles and sets it falling (optionally calling DoLand directly), and writes the z series, the FALLDOWN records and the leg fracture times to fall-probe.json.
TK.register("fall.probe", function(argv)
    local p, why = kineticsPlayer(argv[1])
    if p == nil then return { ok = false, reason = why } end
    local dz = tonumber(argv[2])
    if dz == nil then return "usage: fall.probe <user> <z> [land <f>]" end
    local out = { ok = false, side = TK.side }
    out.hooked = P5.fallHook()
    if TK.p5FallWatch.armed then
        out.reason = "a fall.probe window is already armed"
        return out
    end
    out.zBefore = P5.hop(p, "getZ")
    local setter = p["setZ"]
    if setter == nil or out.zBefore == nil then
        out.reason = "no height write: no setZ/getZ on the player"
        return out
    end
    local ran, err = pcall(setter, p, out.zBefore + dz)
    if not ran then
        out.reason = "no height write: setZ raised: " .. tostring(err)
        return out
    end
    P5.hop(p, "setFallTime", 0)
    P5.hop(p, "setbFalling", true)
    out.zAfter = P5.hop(p, "getZ")
    out.falling = P5.hop(p, "isbFalling")
    if argv[3] == "land" then
        local f = tonumber(argv[4])
        if f == nil then return "usage: fall.probe <user> <z> [land <f>]" end
        local landed = pcall(function() p["DoLand"](p, f) end)
        out.landCalled = landed
    end
    local start = TK.now()
    TK.p5FallWatch = { armed = true, start = start, nextAt = start, deadline = start + 8000,
                       series = {}, pushedZ = dz }
    out.result = "fall-probe"
    out.file = "pzt-results/fall-probe.json"
    out.ok = (out.zAfter ~= nil)
    return out
end)

-- The anim.probe sampler (X47). One OnTick handler, installed once, whose first statement is the
-- nil-cheap `armed` test. Sample 0 is taken at the arm tick BEFORE the write (the control, which
-- must differ from the written value or no revert is readable), then the variable is written
-- once through IsoGameCharacter:setVariable(name, float) and every later sample is taken when
-- the wall clock passes the next `ms` boundary. The series is written to anim-probe.json when
-- `n` samples are in: a bus round trip takes about 1 s and cannot sample at 250 ms, so the
-- command answers at once and the artifact carries the series.
TK.p5AnimWatch = TK.p5AnimWatch or { armed = false }

local function p5AnimOnTick()
    local w = TK.p5AnimWatch
    if not w.armed then return end
    local p = getPlayer()
    if p == nil then return end
    local now = TK.now()
    if now < w.nextAt then return end
    local v = P5.hop(p, "getVariableFloat", w.var, -1)
    w.values[#w.values + 1] = v
    w.dts[#w.dts + 1] = now - w.start
    if #w.values == 1 then
        w.control = v
        w.writeRan = pcall(function() p["setVariable"](p, w.var, w.value) end)
        w.wroteAt = now - w.start
    end
    w.nextAt = now + w.ms
    if #w.values >= w.n then
        w.armed = false
        TK.result("anim-probe", { var = w.var, value = w.value, ms = w.ms, n = w.n, control = w.control,
                                  writeRan = w.writeRan, wroteAt = w.wroteAt, values = w.values, dts = w.dts })
    end
end

if not TK.p5AnimHooked and Events ~= nil and Events.OnTick ~= nil then
    Events.OnTick.Add(function() p5AnimOnTick() end)
    TK.p5AnimHooked = true
end

-- <var> <value> <ms> <n>. X47 (#2096): does a client write to an animation variable hold? Reads
-- getVariableFloat(var, -1) as the pre-write control at the arm tick, writes `value` through
-- setVariable(var, value) (the float overload), and keeps sampling on its own Lua timer every
-- `ms` of wall time until `n` samples are in (1 <= n <= 200, 50 <= ms <= 5000); it answers at
-- once and writes anim-probe.json with the values and their wall offsets. Use it as
-- `anim.probe WalkSpeed 0.3 250 16` with player.walk 20 0 for the walking arm and standing still
-- for the second; player.stop after.
-- @args <var> <value> <ms> <n>
-- @reply {ok, armed, var, value, ms, n, result, file [, reason]} | string
-- @purpose Samples an animation variable on the local player every ms for n samples around one setVariable write (X47: does the write hold across the injuries-packet window), writing anim-probe.json.
TK.register("anim.probe", function(argv)
    local p = getPlayer and getPlayer() or nil
    if p == nil then return { ok = false, reason = "no local player" } end
    local var, value, ms, n = argv[1], tonumber(argv[2]), tonumber(argv[3]), tonumber(argv[4])
    if var == nil or value == nil or ms == nil or n == nil or ms < 50 or ms > 5000 or n < 1 or n > 200 then
        return "usage: anim.probe <var> <value> <ms> <n>  (50 <= ms <= 5000, 1 <= n <= 200)"
    end
    if not TK.p5AnimHooked then return { ok = false, reason = "no Events.OnTick on this side" } end
    if TK.p5AnimWatch.armed then return { ok = false, reason = "an anim.probe window is already armed" } end
    local start = TK.now()
    TK.p5AnimWatch = { armed = true, var = var, value = value, ms = ms, n = n, start = start, nextAt = start,
                       values = {}, dts = {} }
    return { ok = true, armed = true, var = var, value = value, ms = ms, n = n, result = "anim-probe",
             file = "pzt-results/anim-probe.json" }
end)

-- The aiming-delay sampler (Plan 5, platform briefing 5.1). One OnTick handler, installed once,
-- whose first statement is the nil-cheap `armed` test. Per tick of an armed window it reads
-- isAiming() (BEFORE any re-assert, so an engine that clears the flag shows) and
-- getAimingDelay(), keeps the first 120 raw samples and a histogram of the delay at two
-- decimals (at most 60 keys, the rest in d_other), then re-asserts setIsAiming(true). A queued
-- shot (aim.fire) faces the nearest zombie within 20 tiles when there is one, reads the delay,
-- calls IsoPlayer:DoAttack(0) (the route attack.melee uses) under pcall, reads the delay again
-- and, when a bump is standing (aim.bump), writes setAimingDelay(delay + bump) at once and
-- reads it a third time. Shots are spaced 1200 ms apart. At the deadline the window writes
-- aim-probe.json and clears the aiming flag.
TK.p5Aim = TK.p5Aim or { armed = false }

local function p5Fmt(v, dec)
    if type(v) ~= "number" then return tostring(v) end
    return string.format("%." .. dec .. "f", v)
end

local function p5AimShot(p, w, now)
    local nearest, bestD = nil, 400
    local cell = getCell and getCell() or nil
    local list = P5.hop(cell, "getZombieList")
    local count = P5.hop(list, "size") or 0
    local px, py = P5.hop(p, "getX"), P5.hop(p, "getY")
    for i = 0, count - 1 do
        local z = P5.hop(list, "get", i)
        local zx, zy = P5.hop(z, "getX"), P5.hop(z, "getY")
        if zx ~= nil and zy ~= nil and px ~= nil and py ~= nil then
            local d = (zx - px) * (zx - px) + (zy - py) * (zy - py)
            if d <= bestD then nearest, bestD = z, d end
        end
    end
    if nearest ~= nil then P5.hop(p, "faceThisObject", nearest) end
    local before = P5.hop(p, "getAimingDelay")
    local ran, ret = pcall(function()
        local f = p["DoAttack"]
        if f == nil then return "no DoAttack" end
        return f(p, 0)
    end)
    local after = P5.hop(p, "getAimingDelay")
    w.shots = w.shots + 1
    local line = "shot " .. w.shots .. " dt=" .. tostring(now - w.start) .. " target=" .. tostring(nearest ~= nil) ..
        " ret=" .. (ran and tostring(ret) or ("error: " .. tostring(ret))) ..
        " before=" .. p5Fmt(before, 3) .. " after=" .. p5Fmt(after, 3)
    if w.bumpX ~= nil and after ~= nil then
        P5.hop(p, "setAimingDelay", after + w.bumpX)
        line = line .. " bump=" .. tostring(w.bumpX) .. " afterBump=" .. p5Fmt(P5.hop(p, "getAimingDelay"), 3)
    end
    w.events[#w.events + 1] = line
end

local function p5AimOnTick()
    local w = TK.p5Aim
    if not w.armed then return end
    local p = getPlayer()
    if p == nil then return end
    local now = TK.now()
    local aiming = P5.hop(p, "isAiming")
    local d = P5.hop(p, "getAimingDelay")
    w.count = w.count + 1
    local ds = p5Fmt(d, 2)
    if w.count <= 120 then
        w.raw[w.count] = "dt=" .. tostring(now - w.start) .. " d=" .. p5Fmt(d, 4) .. " aim=" .. tostring(aiming)
    end
    if aiming ~= true then w.notAiming = w.notAiming + 1 end
    local key = "d_" .. string.gsub(ds, "[%.%-]", "_")
    if w.hist[key] == nil and w.keys >= 60 then key = "d_other" elseif w.hist[key] == nil then w.keys = w.keys + 1 end
    w.hist[key] = (w.hist[key] or 0) + 1
    P5.hop(p, "setIsAiming", true)
    if w.fire > 0 and now >= w.nextFireAt then
        w.fire = w.fire - 1
        w.nextFireAt = now + 1200
        p5AimShot(p, w, now)
    end
    if now >= w.deadline then
        w.armed = false
        P5.hop(p, "setIsAiming", false)
        TK.result("aim-probe", { weapon = w.weapon, samples = w.count, notAiming = w.notAiming, shots = w.shots,
                                 windowMs = w.deadline - w.start, hist = w.hist, events = w.events, raw = w.raw })
    end
end

if not TK.p5AimHooked and Events ~= nil and Events.OnTick ~= nil then
    Events.OnTick.Add(function() p5AimOnTick() end)
    TK.p5AimHooked = true
end

-- <user> <seconds>. Equips a loaded pistol on the local player and samples its aiming delay on
-- every tick for `seconds` (1..300). The weapon is the first Base.Pistol in the local inventory
-- (an RCON additem copy, which both sides hold) or, when there is none, one added CLIENT-side as
-- item.spawn does -- the aiming delay and the hit roll are client state, so the server needs no
-- copy. Loading is by the item's own flags, not the vanilla reload timed-action chain
-- (ISReloadWeaponAction, which needs a magazine item in the inventory): setContainsClip(true),
-- setCurrentAmmoCount(getClipSize()), setRoundChambered(true); `loaded` replies what was read
-- back. The item is equipped with setPrimaryHandItem on the same tick it is found, the aiming
-- flag set with setIsAiming(true) and re-asserted each tick; aim.fire queues shots at the
-- nearest zombie within 20 tiles (zombie.near first), aim.bump adds a standing delay bump after
-- each shot. The artifact is aim-probe.json: samples, the raw first 120 as "dt=.. d=.. aim=..",
-- the delay histogram, the shot events with delay before, after and after bump.
-- @args <user> <seconds>
-- @reply {ok, armed, weapon, spawned, loaded, equipped, aiming, seconds, result, file [, reason]} | string
-- @purpose Equips a loaded pistol, sets the aiming flag and samples getAimingDelay on every client tick for n seconds into aim-probe.json, the window aim.fire and aim.bump act inside.
TK.register("aim.probe", function(argv)
    local p, why = kineticsPlayer(argv[1])
    if p == nil then return { ok = false, reason = why } end
    local secs = tonumber(argv[2])
    if secs == nil or secs < 1 or secs > 300 then return "usage: aim.probe <user> <seconds>  (1 <= seconds <= 300)" end
    local out = { ok = false, armed = false, seconds = secs }
    if not TK.p5AimHooked then
        out.reason = "no Events.OnTick on this side"
        return out
    end
    if TK.p5Aim.armed then
        out.reason = "an aim.probe window is already armed"
        return out
    end
    local inv = P5.hop(p, "getInventory")
    local w = P5.hop(inv, "getFirstTypeRecurse", "Base.Pistol")
    out.spawned = false
    if w == nil then
        w = P5.hop(inv, "AddItem", "Base.Pistol")
        out.spawned = (w ~= nil)
    end
    if w == nil then
        out.reason = "no Base.Pistol in the inventory and AddItem gave nothing"
        return out
    end
    out.weapon = P5.hop(w, "getFullType")
    P5.hop(w, "setContainsClip", true)
    P5.hop(w, "setCurrentAmmoCount", P5.hop(w, "getClipSize") or 15)
    P5.hop(w, "setRoundChambered", true)
    out.loaded = { clip = P5.hop(w, "isContainsClip"), ammo = P5.hop(w, "getCurrentAmmoCount"),
                   chambered = P5.hop(w, "isRoundChambered"), ranged = P5.hop(w, "isRanged") }
    P5.hop(p, "setPrimaryHandItem", w)
    out.equipped = (P5.hop(p, "getPrimaryHandItem") == w)
    P5.hop(p, "setIsAiming", true)
    out.aiming = P5.hop(p, "isAiming")
    local start = TK.now()
    TK.p5Aim = { armed = true, start = start, deadline = start + secs * 1000, weapon = out.weapon, count = 0,
                 notAiming = 0, shots = 0, fire = 0, nextFireAt = start, hist = {}, keys = 0, raw = {}, events = {},
                 bumpX = nil }
    out.armed = true
    out.ok = true
    out.result = "aim-probe"
    out.file = "pzt-results/aim-probe.json"
    return out
end)
