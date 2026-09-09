-- PZTestKit auto-join: driven by <cachedir>/Lua/pzt-join.txt (key=value lines).
-- Stage 1: ServerConnectPopup visible -> fill credentials, call the same connect(...)
--          the CONNECT button calls (ServerConnectPopup.lua:203).
-- Stage 2: MP character creation, which in B42 is (verified 2026-09-09):
--            MapSpawnSelect -> CharacterCreationProfession -> CharacterCreationMain -> world
--          Each screen's NEXT is driven by invoking its onOptionMouseDown({internal="NEXT"}).
-- Every step prints a "PZTK:" line so the orchestrator can read the timeline.

local TK = { manifest = nil, joined = false, ticks = 0, step = {} }

local function log(msg) print("PZTK: " .. tostring(msg)) end

local function readManifest()
    local reader = getFileReader("pzt-join.txt", false)
    if not reader then log("no manifest (Lua/pzt-join.txt)"); return nil end
    local m = {}
    while true do
        local line = reader:readLine()
        if line == nil then break end
        local k, v = string.match(line, "^%s*([%w_]+)%s*=%s*(.-)%s*$")
        if k then m[k] = v end
    end
    reader:close()
    log("manifest loaded: user=" .. tostring(m.username) .. " server=" .. tostring(m.ip) .. ":" .. tostring(m.port))
    return m
end

local function visible(panel)
    return panel ~= nil and panel.isVisible ~= nil and panel:isVisible()
end

local function tryJoin()
    local popup = ServerConnectPopup and ServerConnectPopup.instance
    if not visible(popup) then return end
    local m = TK.manifest
    popup.usernameEntry:setText(m.username or "")
    popup.passwordEntry:setText(m.password or "")
    popup.serverPasswordEntry:setText(m.serverPassword or "")
    local ip, port = popup.ip or m.ip, popup.port or m.port
    log("popup visible; connecting as " .. tostring(m.username) .. " to " .. tostring(ip) .. ":" .. tostring(port))
    TK.joined = true
    ConnectToServer.instance:connect(popup, "", m.username or "", m.password or "",
        ip, "", tostring(port), m.serverPassword or "", false, true, 1)
end

-- Press NEXT on one screen at most once; returns true if it acted.
local function pressNext(name, panel)
    if TK.step[name] or not visible(panel) then return false end
    TK.step[name] = true
    log("screen '" .. name .. "' visible -> NEXT")
    local ok, err = pcall(function() panel:onOptionMouseDown({ internal = "NEXT" }, 0, 0) end)
    if not ok then log("NEXT on " .. name .. " failed: " .. tostring(err)) end
    return true
end

local function tryCharacterCreation()
    local spawn = MapSpawnSelect and MapSpawnSelect.instance
    if visible(spawn) and not TK.step.spawn then
        if spawn.listbox and spawn.listbox.selected and spawn.listbox.selected < 1 then
            spawn.listbox.selected = 1
        end
        local n = spawn.listbox and spawn.listbox.items and #spawn.listbox.items or -1
        log("spawn regions listed: " .. tostring(n) .. ", selected #" .. tostring(spawn.listbox and spawn.listbox.selected))
        pressNext("spawn", spawn)
        return
    end
    local prof = CharacterCreationProfession and CharacterCreationProfession.instance
    if pressNext("profession", prof) then return end
    local main = MainScreen and MainScreen.instance and MainScreen.instance.charCreationMain
    if pressNext("appearance", main) then return end
end

local function onTick()
    TK.ticks = TK.ticks + 1
    if TK.ticks % 30 ~= 0 then return end          -- ~twice a second
    if not TK.manifest then
        TK.manifest = readManifest()
        if not TK.manifest then Events.OnFETick.Remove(onTick); return end
    end
    -- After a successful connect the client reloads Lua with the server's mod list,
    -- so this file may start fresh mid-flow: always try both stages.
    if not TK.joined then tryJoin() end
    tryCharacterCreation()
end

-- OnFETick appears to stop once the client leaves MainScreenState (nothing logged
-- after connect in attempts 5/6); OnPostUIDraw fires every UI frame in every state.
Events.OnFETick.Add(onTick)
if Events.OnPostUIDraw then Events.OnPostUIDraw.Add(onTick) end
Events.OnMainMenuEnter.Add(function() log("main menu entered") end)
Events.OnGameStart.Add(function()
    log("OnGameStart - in world")
    local p = getPlayer()
    if p then log(string.format("player %s at %.0f,%.0f,%d", tostring(p:getUsername()), p:getX(), p:getY(), p:getZ())) end
end)
log("harness loaded")
