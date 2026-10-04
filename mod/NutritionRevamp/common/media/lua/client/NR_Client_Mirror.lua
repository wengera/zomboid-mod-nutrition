-- NR_Client_Mirror.lua -- the client's read-only copy of the server's mirror (spec § 4.8). It
-- installs what the server sends and never writes back; a client write to a field no packet
-- carries would only drift (#0129). The request is sent once at OnGameStart and again by
-- whatever opens the panel in a later plan.
local NR = NutritionRevamp
NR.client.mirror = nil
NR.client.received = 0

function NR.client.requestMirror()
    if not NR.isClient() then return false end
    if sendClientCommand == nil or getPlayer == nil then return false end
    local okP, p = pcall(getPlayer)
    if not okP or p == nil then return false end
    local ok = pcall(sendClientCommand, p, "NutritionRevamp", "mirror.request", {})
    return ok
end

if Events ~= nil then
    if Events.OnServerCommand ~= nil then
        Events.OnServerCommand.Add(function(module, command, args)
            if module ~= "NutritionRevamp" or command ~= "mirror" then return end
            if not NR.isClient() then return end
            NR.client.mirror = args
            NR.client.received = NR.client.received + 1
        end)
    end
    if Events.OnGameStart ~= nil then
        Events.OnGameStart.Add(function() NR.client.requestMirror() end)
    end
end
