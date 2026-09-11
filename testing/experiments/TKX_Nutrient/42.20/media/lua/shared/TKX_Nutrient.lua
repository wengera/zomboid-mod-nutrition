-- TKX_Nutrient -- shared state for the new-nutrient-field experiment (slice 12).
--  * TKX_Nutrient is a GLOBAL on purpose: it is what the harness's `lua.global` witness reads
--    on each side, and what the profile gates on. Each Lua state (server VM, client VM) keeps
--    its OWN copy of this table -- that is the point of `side` and of the per-side counters.
--  * Plain assignment, not `TKX_Nutrient or {}`: a `reloadlua` SHOULD reset these counters, so
--    a witness reading after a reload reports the new state rather than a stale sum.
--  * Only plain values go in the table: the witness serialises it, and a function field would
--    be noise at best.
-- Every file in this mod opens with its OWN six-line `tkxCall` (index the member, then pcall
-- it) and never touches the harness's `TK`: these mods must load on a server with no PZTestKit
-- at all. Nothing in THIS file reaches a Java member, so the guard here is unused by design --
-- it is part of the per-file shape the slice is documenting.
local function tkxCall(obj, name, ...)
    if obj == nil then return false, nil end
    local m = obj[name]
    if m == nil then return false, nil end
    return pcall(m, obj, ...)
end

TKX_Nutrient = { version = 1, ticks = 0, itemWrites = 0, side = "?" }
