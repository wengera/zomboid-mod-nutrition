-- NR_Server_Bus.lua -- the server half of the command bus (mp-model #0932, lessons #1065):
-- module "NutritionRevamp"; the client asks "mirror.request" with no payload and the server
-- answers "mirror" with the flat table K.mirror.build makes. The server never trusts a payload
-- it did not send; in this plan the one client command carries none.
local NR = NutritionRevamp
local K = NR.kernel
NR.server.bus = { module = "NutritionRevamp" }
local B = NR.server.bus

function B.meta()
    local o = NR.server.options
    return { mode = o and o.mode or 1, version = NR.version, build = NR.build }
end

function B.sendMirror(player, record)
    if player == nil or record == nil then return false end
    if sendServerCommand == nil then return false end
    local ok = pcall(sendServerCommand, player, B.module, "mirror", K.mirror.build(record, B.meta(), NR.data and NR.data.records and NR.data.records.ORDER))
    if not ok then NR.log.say(2, "bus: sendServerCommand failed for " .. tostring(record.username)) end
    return ok
end

if Events ~= nil and Events.OnClientCommand ~= nil then
    Events.OnClientCommand.Add(function(module, command, player, args)
        if module ~= B.module then return end
        if not NR.isServer() then return end
        if command == "mirror.request" then
            local okU, username = NR.call(player, "getUsername")
            if not okU or username == nil then return end
            local okT, gt = pcall(getGameTime)
            local okA, age = NR.call(okT and gt or nil, "getWorldAgeHours")
            local r = NR.server.store.get(username, okA and age or 0)
            if r ~= nil then B.sendMirror(player, r) end
        end
    end)
end
