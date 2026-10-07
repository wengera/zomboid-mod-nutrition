-- TKX_ClientRaise -- X23 (Plan 9 Task 5): what does a RELEASE client (launched without -debug) do when
-- a client Lua handler raises UNGUARDED? x127 (TKX_RaiseProbe) measured the server half -- the raise
-- aborts the rest of its own handler body and the handlers registered behind it still run -- but its
-- -debug client parked at the first raise (KahluaUtil.fail(String) @0-@50 L95-L97 reads Core.debug
-- and, on the Lua thread, calls UIManager.debugBreakpoint; debugBreakpoint @0-@6 L1173-L1174 returns
-- at once unless UIManager.showLuaDebuggerOnError, which GameWindow.enter sets true right after
-- OnGameBoot @271-@278 L772-L773). A release client has Core.debug false, so the jar reads it
-- straight to the RuntimeException at L100 -- that is a reading of what the engine COULD do, and this
-- probe is the reading of what it DOES.
--
-- This file is client/ ON PURPOSE: a dedicated server does not load it, and the raise must happen on
-- the client the harness names (`event.trigger TKX_ClientRaise` on `client:bob`, then on `client:admin`
-- as the -debug control). The event is a custom one registered here, so nothing but the harness fires
-- it: no raise happens at boot, and the client reaches ready before any reading is taken.
--
--   H0  TKX_CR.before ++                          -- the event fired and the chain reached here
--   H1  TKX_DefinitelyNilClient() UNGUARDED, then TKX_CR.raw_tail ++
--                                                  -- if the raise aborts the body, raw_tail stays "0"
--   H2  TKX_CR.behind ++                           -- registered AFTER the raising handler
--
-- TKX_CR is a GLOBAL because `lua.global` is what reads it, and every reading is a STRING (the x127
-- discipline: "unset" vs "false" is a distinction a boolean through the bus cannot carry). `version`
-- is assigned in the table constructor, so it answers 1 the moment the file ran -- the liveness control.
--
-- The two flags are READ, never set, once at OnGameStart: debugFlag = tostring(getCore():getDebug())
-- (zombie.core.Core.getDebug()Z, @0 L737 returns the static Core.debug -- read with pz.sh methods and
-- dump); showFlag = tostring(UIManager.isShowLuaDebuggerOnError()) (zombie.ui.UIManager, the static
-- getter vanilla's DebugToolstrip.lua:64 calls). Each stays "unset" when its getter is absent.
--
-- Kahlua rules: no `goto`, no `%d`, no `#`. Every Java member is nil-tested first and called in the
-- pcall ARGUMENT shape (pcall(fn, ...)), the shape x126 measured caught on both sides; nothing in this
-- file may raise on a -debug client before the harness fires the event, because a debug client parks
-- on any Lua error, a pcall'd one included (x127's acceptance boot).
TKX_CR = { before = "0", raw_tail = "0", behind = "0", version = 1, debugFlag = "unset", showFlag = "unset", registered = "no" }
if LuaEventManager ~= nil and LuaEventManager.AddEvent ~= nil then
  local okA = pcall(LuaEventManager.AddEvent, "TKX_ClientRaise")
  TKX_CR.registered = tostring(okA)
end
if Events.TKX_ClientRaise ~= nil then
  Events.TKX_ClientRaise.Add(function() TKX_CR.before = tostring(tonumber(TKX_CR.before) + 1) end)    -- H0
  Events.TKX_ClientRaise.Add(function()                                                                -- H1: the UNGUARDED raise
    TKX_DefinitelyNilClient()          -- no guard: if the raise aborts the body, raw_tail never advances
    TKX_CR.raw_tail = tostring(tonumber(TKX_CR.raw_tail) + 1)
  end)
  Events.TKX_ClientRaise.Add(function() TKX_CR.behind = tostring(tonumber(TKX_CR.behind) + 1) end)    -- H2: registered AFTER the raising handler
else
  TKX_CR.registered = TKX_CR.registered .. ",noEventsEntry"
end
Events.OnGameStart.Add(function()
  if getCore ~= nil then
    local okC, core = pcall(getCore)
    if okC and core ~= nil and core.getDebug ~= nil then
      local okD, d = pcall(core.getDebug, core)
      if okD then TKX_CR.debugFlag = tostring(d) end
    end
  end
  if UIManager ~= nil and UIManager.isShowLuaDebuggerOnError ~= nil then
    local okS, s = pcall(UIManager.isShowLuaDebuggerOnError)
    if okS then TKX_CR.showFlag = tostring(s) end
  end
end)
