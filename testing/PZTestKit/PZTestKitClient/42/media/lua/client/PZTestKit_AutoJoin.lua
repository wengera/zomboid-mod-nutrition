-- PZTestKit auto-join: driven by <cachedir>/Lua/pzt-join.txt (key=value lines).
-- Stage 1: when the ServerConnectPopup is visible, fill credentials and call the
--          same connect(...) the CONNECT button calls (ServerConnectPopup.lua:203).
-- Stage 2: when MP character creation appears, pick the first spawn region and accept.
-- Every step prints a "PZTK:" line so the orchestrator can read the timeline.

local TK = {}
TK.manifest = nil
TK.joined = false
TK.charDone = false
TK.ticks = 0

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

local function tryJoin()
    local popup = ServerConnectPopup and ServerConnectPopup.instance
    if not popup or not popup:isVisible() then return end
    local m = TK.manifest
    popup.usernameEntry:setText(m.username or "")
    popup.passwordEntry:setText(m.password or "")
    popup.serverPasswordEntry:setText(m.serverPassword or "")
    local ip = popup.ip or m.ip
    local port = popup.port or m.port
    log("popup visible; connecting as " .. tostring(m.username) .. " to " .. tostring(ip) .. ":" .. tostring(port))
    TK.joined = true
    -- mirrors ServerConnectPopup:onOptionMouseDown CONNECT branch
    ConnectToServer.instance:connect(popup, "", m.username or "", m.password or "",
        ip, "", tostring(port), m.serverPassword or "", false, true, 1)
end

local function tryCharacterCreation()
    local sel = CoopMapSpawnSelect and CoopMapSpawnSelect.instance
    local cc = CoopCharacterCreation and CoopCharacterCreation.instance
    if type(cc) == "table" and cc.accept == nil then
        -- may be an array indexed by player index
        cc = cc[0] or cc[1]
    end
    if not sel or not sel:isVisible() then return end
    if sel.listbox and sel.listbox.items and #sel.listbox.items > 0 then
        sel.listbox.selected = 1
        log("spawn regions: " .. tostring(#sel.listbox.items) .. "; choosing #1")
        sel:clickNext()
    else
        log("spawn select visible but no regions listed")
        return
    end
    if cc and cc.accept then
        log("accepting character creation")
        TK.charDone = true
        cc:accept()
    else
        log("CoopCharacterCreation.instance not found; cc=" .. tostring(cc))
        TK.charDone = true -- avoid spamming; orchestrator sees the log
    end
end

local function onTick()
    TK.ticks = TK.ticks + 1
    if TK.ticks % 30 ~= 0 then return end          -- ~twice a second at 60fps
    if not TK.manifest then
        TK.manifest = readManifest()
        if not TK.manifest then Events.OnFETick.Remove(onTick); return end
    end
    if not TK.joined then tryJoin() return end
    if not TK.charDone then tryCharacterCreation() end
end

Events.OnFETick.Add(onTick)
Events.OnMainMenuEnter.Add(function() log("main menu entered") end)
Events.OnGameStart.Add(function() log("OnGameStart — in world") end)
log("harness loaded")
