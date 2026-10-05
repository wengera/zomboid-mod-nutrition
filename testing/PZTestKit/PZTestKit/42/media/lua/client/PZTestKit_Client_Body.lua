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
