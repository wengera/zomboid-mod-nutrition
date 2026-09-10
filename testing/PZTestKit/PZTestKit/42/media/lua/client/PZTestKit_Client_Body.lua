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
