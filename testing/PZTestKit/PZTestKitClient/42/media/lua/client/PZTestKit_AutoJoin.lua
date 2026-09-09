-- PZTestKit client harness.
--  * Auto-join, driven by <cachedir>/Lua/pzt-join.txt (key=value lines):
--      stage 1: ServerConnectPopup visible -> fill credentials, call the same connect(...)
--               the CONNECT button calls (ServerConnectPopup.lua:203).
--      stage 2: MP character creation, which in B42 is (verified 2026-09-09):
--               MapSpawnSelect -> CharacterCreationProfession -> CharacterCreationMain -> world.
--               Each screen's NEXT is driven by invoking its onOptionMouseDown({internal="NEXT"}).
--  * Command bus: the orchestrator writes <cachedir>/Lua/pzt-cmd.txt {seq, cmd}; each seq is
--    executed once (the last seq is recovered from pzt-ack.txt after a Lua reset) and answered
--    in pzt-ack.txt {seq, cmd, result}.
-- Every step prints a "PZTK:" line so the orchestrator can read the timeline.

local TK = { manifest = nil, joined = false, ticks = 0, step = {}, lastSeq = 0, ready = false }

local function log(msg) print("PZTK: " .. tostring(msg)) end

local function readKV(name)
    local reader = getFileReader(name, false)
    if not reader then return nil end
    local t = {}
    while true do
        local line = reader:readLine()
        if line == nil then break end
        local k, v = string.match(line, "^%s*([%w_]+)%s*=%s*(.-)%s*$")
        if k then t[k] = v end
    end
    reader:close()
    return t
end

local function writeKV(name, t)
    local w = getFileWriter(name, true, false)
    if not w then log("cannot write " .. name); return end
    for k, v in pairs(t) do w:write(k .. "=" .. tostring(v) .. "\n") end
    w:close()
end

local function readManifest()
    local m = readKV("pzt-join.txt")
    if not m then log("no manifest (Lua/pzt-join.txt)"); return nil end
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

-- "ready" = in-world with a player object; the orchestrator keys on this line.
local function checkReady()
    if TK.ready then return end
    if isIngameState and not isIngameState() then return end
    local p = getPlayer()
    if not p then return end
    TK.ready = true
    log(string.format("player %s at %.0f,%.0f,%.0f", tostring(p:getUsername()), p:getX(), p:getY(), p:getZ()))
end

local COMMANDS = {}
function COMMANDS.ping() return "pong" end
function COMMANDS.quit()
    -- the in-game quit used by ISServerDisconnectUI/ISPostDeathUI: proper disconnect first
    getCore():quitToDesktop()
    return "quitting"
end

local function pollCommands()
    local c = readKV("pzt-cmd.txt")
    if not c or not c.seq then return end
    local seq = tonumber(c.seq) or 0
    if seq <= TK.lastSeq then return end
    TK.lastSeq = seq
    local name = c.cmd or ""
    writeKV("pzt-ack.txt", { seq = seq, cmd = name, result = "running" })
    local fn = COMMANDS[name]
    local ok, res
    if fn then ok, res = pcall(fn, c) else ok, res = false, "unknown command" end
    log("cmd #" .. seq .. " " .. name .. " -> " .. tostring(res))
    writeKV("pzt-ack.txt", { seq = seq, cmd = name, result = (ok and "ok:" or "err:") .. tostring(res) })
end

local function onTick()
    TK.ticks = TK.ticks + 1
    if TK.ticks % 30 ~= 0 then return end          -- ~twice a second
    if not TK.manifest then
        TK.manifest = readManifest()
        if not TK.manifest then
            Events.OnFETick.Remove(onTick)
            if Events.OnPostUIDraw then Events.OnPostUIDraw.Remove(onTick) end
            return
        end
    end
    -- After a successful connect the client reloads Lua with the server's mod list,
    -- so this file may start fresh mid-flow: always try every stage.
    if not TK.joined then tryJoin() end
    tryCharacterCreation()
    checkReady()
    pollCommands()
end

-- A Lua reset (join) reloads this file: don't replay the last executed command.
local ack = readKV("pzt-ack.txt")
if ack and ack.seq then TK.lastSeq = tonumber(ack.seq) or 0 end

-- OnFETick stops once the client leaves MainScreenState; OnPostUIDraw fires every UI frame
-- in every state.
Events.OnFETick.Add(onTick)
if Events.OnPostUIDraw then Events.OnPostUIDraw.Add(onTick) end
Events.OnMainMenuEnter.Add(function() log("main menu entered") end)
Events.OnGameStart.Add(function() log("OnGameStart - in world") end)
log("harness loaded")
