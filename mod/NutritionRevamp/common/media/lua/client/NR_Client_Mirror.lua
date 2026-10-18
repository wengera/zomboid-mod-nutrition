-- NR_Client_Mirror.lua -- the client's read-only copy of the server's mirror (spec § 4.8). It
-- installs what the server sends and never writes back; a client write to a field no packet
-- carries would only drift (#0129). The one other command, "backup", lays the server's copy of the record's backup in
-- the local player's own modData (NR_Server_Backup), so a transmitModData any mod makes on this client carries the
-- copy back instead of wiping it (#1042); this file never transmits. The request is sent once at OnGameStart and again each time the
-- panel opens (NR_Client_Panel.lua). clearMirror drops the copy at the local player's death
-- (NR_Client_View.lua), so a respawn shows nothing of the dead character until its first push.
--
-- Shape (the client-file discipline): the sentinel NR_ClientMirror_Installed is a global of its own holding the
-- two handler closures, so a reload of this file adds no second handler; each looks NutritionRevamp up per call.
local NR = NutritionRevamp
if NR.client.received == nil then NR.client.received = 0 end

NR_ClientMirror_Installed = NR_ClientMirror_Installed or {}

function NR.client.requestMirror()
    if not NR.isClient() then return false end
    if sendClientCommand == nil or getPlayer == nil then return false end
    local okP, p = pcall(getPlayer)
    if not okP or p == nil then return false end
    local okC, present, dead = pcall(NR.call, p, "isDead")
    if okC and present and dead == true then return false end
    local ok = pcall(sendClientCommand, p, "NutritionRevamp", "mirror.request", {})
    return ok
end

-- The installed copy, and the arrival counter moved so the view rebuilds.
function NR.client.installMirror(m)
    NR.client.mirror = m
    NR.client.received = NR.client.received + 1
end

-- No copy, and no arrival counted: the caller forces the view's rebuild (V.onPlayerDeath) from the empty mirror.
function NR.client.clearMirror()
    NR.client.mirror = nil
end

-- The server's backup copy laid in the local player's modData under the server's key (NR_Server_Backup: the field
-- backup of modData.NutritionRevamp). False when there is no player or no modData.
function NR.client.keepBackup(doc)
    if type(doc) ~= "table" or getPlayer == nil then return false end
    local okP, p = pcall(getPlayer)
    if not okP or p == nil then return false end
    local ok, present, md = pcall(NR.call, p, "getModData")
    if not ok or not present or type(md) ~= "table" then return false end
    if type(md.NutritionRevamp) ~= "table" then md.NutritionRevamp = {} end
    md.NutritionRevamp.backup = doc
    return true
end

local S = NR_ClientMirror_Installed
if Events ~= nil then
    if S.command == nil and Events.OnServerCommand ~= nil then
        S.command = function(module, command, args)
            if module ~= "NutritionRevamp" then return end
            local nr = NutritionRevamp
            if not nr.isClient() then return end
            if command == "backup" then
                nr.client.keepBackup(args)
                return
            end
            if command ~= "mirror" then return end
            nr.client.installMirror(args)
            if nr.client.view ~= nil and nr.client.view.onMirror ~= nil then pcall(nr.client.view.onMirror) end
        end
        Events.OnServerCommand.Add(S.command)
    end
    if S.start == nil and Events.OnGameStart ~= nil then
        S.start = function() NutritionRevamp.client.requestMirror() end
        Events.OnGameStart.Add(S.start)
    end
end
