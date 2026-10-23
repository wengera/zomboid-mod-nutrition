-- NR_Client_Mirror.lua -- the client's read-only copy of the server's mirror: a client write to a field no packet
-- carries would only drift (#0129). Requested at OnGameStart and on each panel open; dropped at the local player's
-- death, so a respawn shows nothing of the dead character until its first push.
-- The sentinel NR_ClientMirror_Installed holds the two handler closures, so a reload adds no second handler.
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

-- The arrival counter moves so the view rebuilds.
function NR.client.installMirror(m)
    NR.client.mirror = m
    NR.client.received = NR.client.received + 1
end

-- No arrival counted: the caller forces the view's rebuild (V.onPlayerDeath).
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
