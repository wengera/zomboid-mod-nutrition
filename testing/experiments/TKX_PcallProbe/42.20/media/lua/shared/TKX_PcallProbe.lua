-- TKX_PcallProbe -- does a Kahlua nil call escape `pcall`, and does a raise in one event
-- handler kill the handlers registered BEHIND it?
--
-- The library's standing rule ("Kahlua's 'tried to call nil' escapes `pcall` and kills the
-- whole handler" -- the reason for `TK.call` and every `tkxCall` guard) rests on
-- `exp01-20260909-235420`, which has no committed artifact, and the Task 9 jar review reads
-- the other way: `BaseLib.pcall` -> `KahluaThread.pcall(I)I` wraps `call(I)I` in a try whose
-- dynamic extent covers the nested `luaMainloop`, and `zombie/Lua/Event.trigger` calls each
-- callback through `LuaCaller.protectedCallVoid` inside a per-iteration `catch (Throwable)`
-- that CONTINUES the loop. One probe measures both claims at once.
--
-- This file is shared/ ON PURPOSE: both Lua states (server VM, client VM) load it, so the
-- run gets two independent readings of the same question rather than one.
--
-- TKX_P is a GLOBAL because `lua.global` is what reads it, and EVERY field is a STRING:
-- a `false` coming back through the bus would be indistinguishable from a walk that stopped,
-- and `unset` vs `"false"` is exactly the distinction H1 turns on.
--
-- Kahlua rules: no `goto`, no `%d`, no `#`, no Java members anywhere in this file -- so there
-- is no `tkxCall` guard here, because there is nothing to guard. `isServer`/`isClient` are
-- Lua globals, and each is `== nil`-checked BEFORE the pcall precisely because the standing
-- rule this file is testing says a pcall alone would not save us.
TKX_P = { side = "?", before = "0", ok = "unset", err = "unset", tail = "0", behind = "0", ctrl_ok = "unset", ctrl_err = "unset", version = 1 }
if isServer ~= nil then local okS, s = pcall(isServer); if okS and s then TKX_P.side = "server" end end
if isClient ~= nil then local okC, c = pcall(isClient); if okC and c then TKX_P.side = "client" end end
-- H0: proves the event fires and the chain reaches this file
Events.EveryOneMinute.Add(function() TKX_P.before = tostring(tonumber(TKX_P.before) + 1) end)
-- H1: the nil call under pcall. If pcall catches, ok/err are assigned and tail advances; if the raise escapes, none of the three lines after it run.
Events.EveryOneMinute.Add(function()
  local ok, err = pcall(TKX_DefinitelyNil)   -- a global that is never defined
  TKX_P.ok = tostring(ok); TKX_P.err = tostring(err)
  TKX_P.tail = tostring(tonumber(TKX_P.tail) + 1)
end)
-- H2: registered AFTER H1 on the same event -- advances only if the engine runs later handlers after a raise in H1
Events.EveryOneMinute.Add(function() TKX_P.behind = tostring(tonumber(TKX_P.behind) + 1) end)
-- H3 control: an ordinary error under pcall (must be caught: ctrl_ok "false", ctrl_err containing "boom")
Events.EveryOneMinute.Add(function() local ok, err = pcall(error, "boom"); TKX_P.ctrl_ok = tostring(ok); TKX_P.ctrl_err = tostring(err) end)
