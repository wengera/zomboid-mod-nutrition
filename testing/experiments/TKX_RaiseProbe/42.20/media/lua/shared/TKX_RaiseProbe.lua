-- TKX_RaiseProbe -- what does an UNGUARDED Kahlua nil call do to the rest of its own event
-- handler and to the handlers registered BEHIND it, and does the NESTED pcall shape catch?
--
-- Session 6 (`x126-20260911-045205`) measured `pcall(<nil>)` -- the undefined global passed as
-- pcall's function ARGUMENT, which is the shape `TK.call`/`tkxCall` use -- and found it CAUGHT
-- on both sides, returning `false, "tried to call nil java.lang.RuntimeException"`. Because it
-- caught, nothing raised, and two questions stayed open:
--
--   (1) does an unguarded nil call abort the REST of its handler's body, and do the handlers
--       registered AFTER it still run? The Task 9 jar review says `zombie/Lua/Event.trigger`
--       calls each callback through `LuaCaller.protectedCallVoid` with a per-iteration
--       `catch (Throwable)` (`@194-@198 L41-L42`) and CONTINUES the loop (`@216-@219 L31`).
--   (2) does `pcall(function() SomeNil() end)` catch too? There the raise comes from inside the
--       NESTED `luaMainloop`, one frame deeper than session 6 measured.
--
-- This file is shared/ ON PURPOSE: both Lua states (server VM, client VM) load it, so the run
-- gets two independent readings of the same pair of questions rather than one.
--
-- TKX_R is a GLOBAL because `lua.global` is what reads it, and EVERY field is a STRING: a
-- `false` coming back through the bus would be indistinguishable from a walk that stopped, and
-- `unset` vs `"false"` is exactly the distinction H1 turns on. `raw_tail` staying at `"0"` while
-- `behind` advances is the whole of H2/H3.
--
-- Kahlua rules: no `goto`, no `%d`, no `#`, no Java members anywhere in this file -- so there is
-- no `tkxCall` guard here, because there is nothing to guard. `isServer`/`isClient` are Lua
-- globals, and each is `== nil`-checked BEFORE the pcall.
TKX_R = { side = "?", before = "0", nested_ok = "unset", nested_err = "unset", nested_tail = "0", raw_tail = "0", behind = "0", version = 1 }
if isServer ~= nil then local okS, s = pcall(isServer); if okS and s then TKX_R.side = "server" end end
if isClient ~= nil then local okC, c = pcall(isClient); if okC and c then TKX_R.side = "client" end end
Events.EveryOneMinute.Add(function() TKX_R.before = tostring(tonumber(TKX_R.before) + 1) end)          -- H0
Events.EveryOneMinute.Add(function()                                                                    -- H1: the NESTED pcall shape
  local ok, err = pcall(function() TKX_DefinitelyNilToo() end)
  TKX_R.nested_ok = tostring(ok); TKX_R.nested_err = tostring(err)
  TKX_R.nested_tail = tostring(tonumber(TKX_R.nested_tail) + 1)
end)
Events.EveryOneMinute.Add(function()                                                                    -- H2: the UNGUARDED raise
  TKX_DefinitelyNilThree()          -- no guard: if the raise aborts the body, raw_tail never advances
  TKX_R.raw_tail = tostring(tonumber(TKX_R.raw_tail) + 1)
end)
Events.EveryOneMinute.Add(function() TKX_R.behind = tostring(tonumber(TKX_R.behind) + 1) end)          -- H3: registered AFTER the raising handler
