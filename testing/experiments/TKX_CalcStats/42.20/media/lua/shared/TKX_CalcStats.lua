-- TKX_CalcStats -- shared state for the Hook.CalculateStats registrant experiments (X32, X46).
-- TKX_CalcStats is a GLOBAL on purpose: the harness lua.global witness reads it on each side,
-- and each Lua state keeps its OWN copy. Plain assignment, so a reloadlua resets the counters.
--   calls   the no-op handler (both X32 sides)
--   callsA  handler A, returns true     callsB  handler B, returns false (X46)
-- Own six-line guard per file; the harness TK is never referenced.
local function tkxCall(obj, name, ...)
    if obj == nil then return false, nil end
    local m = obj[name]
    if m == nil then return false, nil end
    return pcall(m, obj, ...)
end

TKX_CalcStats = { version = 1, calls = 0, callsA = 0, callsB = 0, side = "?" }
