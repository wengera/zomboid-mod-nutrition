-- NR_Client_Mirror.lua -- the client's read-only copy of the server's mirror (spec § 4.8). It
-- installs what the server sends and never writes back; a client write to a field no packet
-- carries would only drift (#0129). The request is sent once at OnGameStart and again each time the
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

local S = NR_ClientMirror_Installed
if Events ~= nil then
    if S.command == nil and Events.OnServerCommand ~= nil then
        S.command = function(module, command, args)
            if module ~= "NutritionRevamp" or command ~= "mirror" then return end
            local nr = NutritionRevamp
            if not nr.isClient() then return end
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
