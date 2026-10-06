"""The client effects channel (Plan 5 Task 10): NR_Client_Effects.lua and the effects push in NR_Server_Bus.lua.

Both files are loaded into a FRESH Lua 5.1 runtime per test (NR_Core.lua first, then the file under test), with
Lua stand-ins for the engine: an Events table whose Add records each listener, isClient/isServer, getPlayer with
a fake local player (getAimingDelay, and setAimingDelay/setVariable stubs that only count, so a write would show),
getTimestampMs on a settable clock, sendServerCommand counting sends, and a stub K.mirror.build. Nothing here
loads a kernel file, so the session host's coverage gate is untouched. A stub proves the wiring, the guards and
the dedupe, never the engine: whether OnWeaponSwing passes the local player, and what the delay reads while a
player really aims, are the live runs' (X86, #3061-#3063).

The aim re-apply and the speed write ship UNAPPLIED (ruling 20; X86 and X47 open): the client file reads and
logs, and a source-text test pins that neither setAimingDelay nor setVariable appears outside its comments.
"""
import os
import re

import lupa.lua51 as lua51

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
LUA = os.path.join(REPO, "mod", "NutritionRevamp", "common", "media", "lua")
CORE = os.path.join(LUA, "shared", "NR_Core.lua")
CLIENT_EFFECTS = os.path.join(LUA, "client", "NR_Client_Effects.lua")
CLIENT_MIRROR = os.path.join(LUA, "client", "NR_Client_Mirror.lua")
BUS = os.path.join(LUA, "server", "NR_Server_Bus.lua")

ENV = r"""
NR_T = { adds = {}, aimWrites = 0, varWrites = 0, sends = 0, sent = {}, delay = 25, now = 1000000 }
local function event(name)
    NR_T.adds[name] = {}
    return { Add = function(fn) local l = NR_T.adds[name]; l[#l + 1] = fn end }
end
Events = {
    OnWeaponSwing = event("OnWeaponSwing"),
    OnServerCommand = event("OnServerCommand"),
    OnGameStart = event("OnGameStart"),
    OnClientCommand = event("OnClientCommand"),
    OnServerStarted = event("OnServerStarted"),
}
NR_T.local_ = {
    getAimingDelay = function(s)
        if NR_T.delayRaises then error("boom") end
        return NR_T.delay
    end,
    setAimingDelay = function(s, v) NR_T.aimWrites = NR_T.aimWrites + 1 end,
    setVariable = function(s, k, v) NR_T.varWrites = NR_T.varWrites + 1 end,
    getUsername = function(s) return "admin" end,
}
NR_T.other = { getAimingDelay = function(s) return 99 end, getUsername = function(s) return "bob" end }
getPlayer = function() return NR_T.local_ end
isClient = function() return NR_T.client ~= false end
isServer = function() return NR_T.server ~= false end
getTimestampMs = function() return NR_T.now end
sendServerCommand = function(p, module, command, args)
    NR_T.sends = NR_T.sends + 1
    NR_T.sent[#NR_T.sent + 1] = { module = module, command = command, args = args }
end
"""

STUBS = r"""
NutritionRevamp.kernel.mirror = { build = function(record, meta, order) return { username = record.username } end }
NutritionRevamp.server.players = { onMinute = {}, onFirstSight = {}, onDeparture = {} }
NutritionRevamp.server.store = { get = function(u, age) return NR_T.records[u] end }
NR_T.records = {}
"""


def _src(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def _load(rt, path):
    rt.eval("function(src, name) return assert(loadstring(src, name)) end")(_src(path), "@" + os.path.basename(path))()


def client_rt():
    rt = lua51.LuaRuntime(unpack_returned_tuples=True)
    rt.execute(ENV)
    _load(rt, CORE)
    _load(rt, CLIENT_EFFECTS)
    _load(rt, CLIENT_MIRROR)
    return rt


def bus_rt():
    rt = lua51.LuaRuntime(unpack_returned_tuples=True)
    rt.execute(ENV)
    _load(rt, CORE)
    rt.execute(STUBS)
    _load(rt, BUS)
    rt.execute("for _, f in ipairs(NR_T.adds.OnServerStarted) do f() end")
    return rt


def G(rt):
    return rt.globals()


def CE(rt):
    return G(rt).NutritionRevamp.client.effects


def swing(rt, who="local_"):
    rt.execute("for _, f in ipairs(NR_T.adds.OnWeaponSwing) do f(NR_T.%s, {}) end" % who)


def receive(rt, mirror_lua):
    rt.execute("for _, f in ipairs(NR_T.adds.OnServerCommand) do f('NutritionRevamp', 'mirror', %s) end" % mirror_lua)


def code_only(src):
    """The source with every comment removed (long comments first, then line comments)."""
    src = re.sub(r"--\[(=*)\[.*?\]\1\]", "", src, flags=re.S)
    return "\n".join(line.split("--", 1)[0] for line in src.splitlines())


# ------------------------------------------------------------------------------------------- the client file

def test_the_listener_installs_once():
    rt = client_rt()
    assert len(G(rt).NR_T.adds.OnWeaponSwing) == 1
    assert CE(rt).install() is True
    assert len(G(rt).NR_T.adds.OnWeaponSwing) == 1


def test_a_reload_adds_no_second_listener_and_the_logic_is_read_at_call_time():
    rt = client_rt()
    _load(rt, CORE)            # NR_Core re-creates NutritionRevamp by plain assignment
    _load(rt, CLIENT_EFFECTS)
    _load(rt, CLIENT_MIRROR)
    assert len(G(rt).NR_T.adds.OnWeaponSwing) == 1
    assert lua51.lua_type(G(rt).NR_ClientEffects_Installed) == "table"
    swing(rt)
    assert CE(rt).stats.swings == 1   # the one listener reached the reloaded table


def test_a_swing_with_no_mirror_counts_and_writes_nothing():
    rt = client_rt()
    swing(rt)
    s = CE(rt).stats
    assert s.swings == 1 and s.noMirror == 1 and s.reads == 0
    assert CE(rt).lastAimMul is None
    assert G(rt).NR_T.aimWrites == 0 and G(rt).NR_T.varWrites == 0


def test_a_swing_reads_the_mirrors_aimMul_and_the_delay_and_writes_nothing():
    rt = client_rt()
    receive(rt, "{ effects_aimMul = 0.8, effects_speedMul = 0.9 }")
    swing(rt)
    e = CE(rt)
    assert e.stats.reads == 1 and e.stats.swings == 1
    assert e.lastAimMul == 0.8
    assert e.lastDelay == 25
    assert e.lastWouldBe == 20       # delay * aimMul; the stub weapon has no getAimingTime to cap it
    assert G(rt).NR_T.aimWrites == 0 and G(rt).NR_T.varWrites == 0


def test_the_mirror_read_is_nil_safe_on_an_absent_key_and_a_non_number():
    rt = client_rt()
    receive(rt, "{ v = 1 }")
    assert CE(rt).aimMul() is None and CE(rt).speedMul() is None
    receive(rt, "{ effects_aimMul = 'x', effects_speedMul = 0/0 }")
    assert CE(rt).aimMul() is None and CE(rt).speedMul() is None
    swing(rt)
    assert CE(rt).stats.reads == 0 and CE(rt).stats.noMirror == 1


def test_speedMul_returns_the_mirrors_value_and_writes_nothing():
    rt = client_rt()
    assert CE(rt).speedMul() is None
    receive(rt, "{ effects_speedMul = 0.85 }")
    assert CE(rt).speedMul() == 0.85
    assert G(rt).NR_T.varWrites == 0 and G(rt).NR_T.aimWrites == 0


def test_another_characters_swing_is_ignored():
    rt = client_rt()
    receive(rt, "{ effects_aimMul = 0.8 }")
    swing(rt, "other")
    assert CE(rt).stats.swings == 0 and CE(rt).stats.notLocal == 1


def test_the_server_side_never_counts():
    rt = client_rt()
    G(rt).NR_T.client = False
    swing(rt)
    assert CE(rt).stats.swings == 0


def test_a_raising_getter_is_caught_and_counted():
    rt = client_rt()
    receive(rt, "{ effects_aimMul = 0.8 }")
    G(rt).NR_T.delayRaises = True
    swing(rt)                         # must not raise into the event
    assert CE(rt).stats.errors == 1


def test_the_verbose_log_runs_only_at_level_3():
    rt = client_rt()
    receive(rt, "{ effects_aimMul = 0.8 }")
    rt.execute("NR_T.printed = 0; print = function() NR_T.printed = NR_T.printed + 1 end")
    swing(rt)
    assert G(rt).NR_T.printed == 0
    G(rt).NutritionRevamp.log.level = 3
    swing(rt)
    assert G(rt).NR_T.printed == 1


def test_neither_engine_write_appears_outside_the_comments():
    code = code_only(_src(CLIENT_EFFECTS))
    assert "setAimingDelay" not in code
    assert "setVariable" not in code
    assert "setAimingDelay" in _src(CLIENT_EFFECTS)    # the header names the one-line write
    assert "X86" in _src(CLIENT_EFFECTS) and "X47" in _src(CLIENT_EFFECTS)


def test_the_limitations_name_both_open_rows():
    rt = client_rt()
    lim = list(CE(rt).limitations.values())
    assert any("X86" in s for s in lim) and any("X47" in s for s in lim)


# ------------------------------------------------------------------------------------------- the bus push

def BUS_(rt):
    return G(rt).NutritionRevamp.server.bus


def rec(rt, username="admin", dirty=None):
    lua = "{ username = '%s'%s }" % (username, "" if dirty is None else ", effects = { dirty = %s }" % ("true" if dirty else "false"))
    r = rt.eval(lua)
    G(rt).NR_T.records[username] = r
    return r


def minute(rt, r, username="admin"):
    for i in range(1, len(G(rt).NutritionRevamp.server.players.onMinute) + 1):
        G(rt).NutritionRevamp.server.players.onMinute[i](username, G(rt).NR_T.local_, r)


def test_the_flush_is_wired_once():
    rt = bus_rt()
    P = G(rt).NutritionRevamp.server.players
    assert len(P.onMinute) == 1
    rt.execute("for _, f in ipairs(NR_T.adds.OnServerStarted) do f() end")
    assert len(P.onMinute) == 1 and len(P.onFirstSight) == 1 and len(P.onDeparture) == 1


def test_no_mark_no_send():
    rt = bus_rt()
    r = rec(rt)
    minute(rt, r)
    assert G(rt).NR_T.sends == 0


def test_one_mark_one_send_and_a_second_mark_within_the_minute_none():
    rt = bus_rt()
    B = BUS_(rt)
    r = rec(rt)
    B.markEffects("admin")
    minute(rt, r)
    assert G(rt).NR_T.sends == 1
    assert G(rt).NR_T.sent[1].command == "mirror"
    G(rt).NR_T.now = G(rt).NR_T.now + 30000
    B.markEffects("admin")
    minute(rt, r)
    assert G(rt).NR_T.sends == 1                      # deduped: 30 s since the last effects push
    assert B.effects.stats.deferred == 1
    G(rt).NR_T.now = G(rt).NR_T.now + 30000           # 60 s since the push: the held mark goes out
    minute(rt, r)
    assert G(rt).NR_T.sends == 2
    minute(rt, r)
    assert G(rt).NR_T.sends == 2                      # the flag was cleared


def test_marks_inside_one_minute_collapse_to_one_send():
    rt = bus_rt()
    B = BUS_(rt)
    r = rec(rt)
    B.markEffects("admin")
    B.markEffects("admin")
    minute(rt, r)
    minute(rt, r)
    assert G(rt).NR_T.sends == 1


def test_the_records_dirty_flag_alone_pushes_and_is_cleared():
    rt = bus_rt()
    r = rec(rt, dirty=True)
    minute(rt, r)
    assert G(rt).NR_T.sends == 1
    assert r.effects.dirty is False


def test_the_gap_is_per_user():
    rt = bus_rt()
    B = BUS_(rt)
    a, b = rec(rt, "admin"), rec(rt, "bob")
    B.markEffects("admin")
    B.markEffects("bob")
    minute(rt, a, "admin")
    minute(rt, b, "bob")
    assert G(rt).NR_T.sends == 2


def test_a_failed_send_keeps_the_flag():
    rt = bus_rt()
    B = BUS_(rt)
    r = rec(rt)
    saved = G(rt).sendServerCommand
    G(rt).sendServerCommand = None
    B.markEffects("admin")
    minute(rt, r)
    assert B.effects.stats.failed == 1 and B.effects.dirty["admin"] is True
    G(rt).sendServerCommand = saved
    minute(rt, r)
    assert G(rt).NR_T.sends == 1


def test_no_clock_falls_back_to_the_slow_minute():
    rt = bus_rt()
    B = BUS_(rt)
    r = rec(rt)
    G(rt).getTimestampMs = None
    B.markEffects("admin")
    minute(rt, r)
    B.markEffects("admin")
    minute(rt, r)
    assert G(rt).NR_T.sends == 2


def test_a_clock_that_runs_back_does_not_hold_the_push_forever():
    rt = bus_rt()
    B = BUS_(rt)
    r = rec(rt)
    B.markEffects("admin")
    minute(rt, r)
    G(rt).NR_T.now = G(rt).NR_T.now - 5000
    B.markEffects("admin")
    minute(rt, r)
    assert G(rt).NR_T.sends == 2


def test_departure_and_first_sight_forget_the_transient_state():
    rt = bus_rt()
    B = BUS_(rt)
    P = G(rt).NutritionRevamp.server.players
    r = rec(rt, dirty=True)
    B.markEffects("admin")
    P.onFirstSight[1]("admin", G(rt).NR_T.local_, r)  # the first-sight mirror (Metabolism's) covers it
    assert B.effects.dirty["admin"] is None and r.effects.dirty is False
    minute(rt, r)
    assert G(rt).NR_T.sends == 0
    B.markEffects("admin")
    minute(rt, r)
    assert G(rt).NR_T.sends == 1
    P.onDeparture[1]("admin", None, None)
    assert B.effects.last["admin"] is None and B.effects.dirty["admin"] is None


def test_the_flush_is_server_only():
    rt = bus_rt()
    B = BUS_(rt)
    r = rec(rt)
    G(rt).NR_T.server = False
    B.markEffects("admin")
    minute(rt, r)
    assert G(rt).NR_T.sends == 0


def test_the_request_path_is_unchanged():
    rt = bus_rt()
    rec(rt)
    rt.execute("NR_T.adds.OnClientCommand[1]('NutritionRevamp', 'mirror.request', NR_T.local_, {})")
    assert G(rt).NR_T.sends == 1
    assert BUS_(rt).effects.stats.pushes == 0
