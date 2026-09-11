-- TKX_Nutrient client side -- the CONTROL for the server file. Same event, same player
-- modData table, a DIFFERENT key and no transmit of any kind, so a census of the player's
-- modData says which side wrote which key:
--   TKX_fibre         written by the server VM only  (server/TKX_Nutrient_Server.lua, arm 1)
--   TKX_fibre_client  written by the client VM only  (this file)
-- The two VMs hold separate copies of the shared TKX_Nutrient table, so `ticks` here counts
-- this side's EveryOneMinute firings and nothing else.
--
-- Own six-line guard; the harness's TK is never referenced.
local function tkxCall(obj, name, ...)
    if obj == nil then return false, nil end
    local m = obj[name]
    if m == nil then return false, nil end
    return pcall(m, obj, ...)
end

local function tick()
    if TKX_Nutrient == nil then return end          -- shared/ not loaded: nothing to witness
    TKX_Nutrient.side = "client"
    TKX_Nutrient.ticks = TKX_Nutrient.ticks + 1
    if getPlayer == nil then return end
    local okP, player = pcall(getPlayer)
    if not okP or player == nil then return end
    local okMd, md = tkxCall(player, "getModData")
    if not okMd or md == nil then return end
    md.TKX_fibre_client = TKX_Nutrient.ticks        -- no transmit: this key must stay local
end

Events.EveryOneMinute.Add(tick)
