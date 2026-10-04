-- TKX_CalcStats client side (X32 both-sides half). The no-op handler is added at file scope
-- when isClient() is true, so the client count answers whether the hook fires on the client.
-- isClient is nil-checked before the protected call.
local function tkxIsClient()
    if isClient == nil then return false end
    local ok, c = pcall(isClient)
    return ok and c == true
end

local function noop()
    if TKX_CalcStats == nil then return end
    TKX_CalcStats.calls = TKX_CalcStats.calls + 1
end

if TKX_CalcStats ~= nil and tkxIsClient() then
    TKX_CalcStats.side = "client"
    if Hook ~= nil and Hook.CalculateStats ~= nil and Hook.CalculateStats.Add ~= nil then
        Hook.CalculateStats.Add(noop)
    end
end
