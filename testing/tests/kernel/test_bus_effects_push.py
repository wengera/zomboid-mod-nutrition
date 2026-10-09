"""The effects push on the bus (Plan 5 Task 10): the NR_Server_Bus.lua flush, the per-user gap and the dedupe.

Split out of test_client_effects_shape.py in Plan 11a Task 8, which deleted the client effects listener
(NR_Client_Effects.lua: the aim and speed effects were never applied, X86 and X47 open) and kept these tests.

The files are loaded into a FRESH Lua 5.1 runtime per test (NR_Core.lua first, then the file under test), with
Lua stand-ins for the engine: an Events table whose Add records each listener, isClient/isServer, getTimestampMs
on a settable clock, sendServerCommand counting sends, and a stub K.mirror.build. It also stubs K.view with a constant signature and a zero phase; the push offset is pinned in test_bus_shape.py and test_kernel_view.py. Nothing here
loads a kernel file, so the session host's coverage gate is untouched.
"""
import os

import lupa.lua51 as lua51

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
LUA = os.path.join(REPO, "mod", "NutritionRevamp", "common", "media", "lua")
CORE = os.path.join(LUA, "shared", "NR_Core.lua")
BUS = os.path.join(LUA, "server", "NR_Server_Bus.lua")
MINUTE = os.path.join(LUA, "server", "NR_Server_Minute.lua")

ENV = r"""
NR_T = { adds = {}, sends = 0, sent = {}, now = 1000000 }
local function event(name)
    NR_T.adds[name] = {}
    return { Add = function(fn) local l = NR_T.adds[name]; l[#l + 1] = fn end }
end
Events = {
    OnGameStart = event("OnGameStart"),
    OnClientCommand = event("OnClientCommand"),
    OnServerStarted = event("OnServerStarted"),
}
NR_T.local_ = { getUsername = function(s) return "admin" end }
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
NutritionRevamp.kernel.mirror = { build = function(record, meta, order) return { username = record.username } end, stomachMass = function() return 0 end }
-- K.view stubbed (Plan 11a Task 4): a constant class signature and a zero push phase, so these tests pin the gap
-- and the dedupe alone; the signature and the phase are test_bus_shape.py's and test_kernel_view.py's.
NutritionRevamp.kernel.view = { pushSignature = function() return 0 end, pushOffset = function(u, gap) return 0 end }
NutritionRevamp.server.players = { onFirstSight = {}, onDeparture = {} }
NutritionRevamp.server.store = { get = function(u, age) return NR_T.records[u] end }
NR_T.records = {}
"""


def _src(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def _load(rt, path):
    rt.eval("function(src, name) return assert(loadstring(src, name)) end")(_src(path), "@" + os.path.basename(path))()


def G(rt):
    return rt.globals()


def bus_rt():
    rt = lua51.LuaRuntime(unpack_returned_tuples=True)
    rt.execute(ENV)
    _load(rt, CORE)
    rt.execute(STUBS)
    _load(rt, MINUTE)
    _load(rt, BUS)
    rt.execute("for _, f in ipairs(NR_T.adds.OnServerStarted) do f() end")
    return rt


# ------------------------------------------------------------------------------------------- the bus push

def BUS_(rt):
    return G(rt).NutritionRevamp.server.bus


def rec(rt, username="admin", dirty=None):
    lua = "{ username = '%s'%s }" % (username, "" if dirty is None else ", effects = { dirty = %s }" % ("true" if dirty else "false"))
    r = rt.eval(lua)
    G(rt).NR_T.records[username] = r
    return r


def minute(rt, r, username="admin"):
    G(rt).NutritionRevamp.server.minute.run(username, G(rt).NR_T.local_, r)   # the pipeline's run (Plan 10 R2)


def test_the_flush_is_wired_once():
    rt = bus_rt()
    P = G(rt).NutritionRevamp.server.players
    MIN = G(rt).NutritionRevamp.server.minute
    same = rt.eval("rawequal")
    assert same(MIN.steps["bus"], BUS_(rt).flushEffects)
    rt.execute("for _, f in ipairs(NR_T.adds.OnServerStarted) do f() end")
    assert same(MIN.steps["bus"], BUS_(rt).flushEffects)
    assert len(P.onFirstSight) == 1 and len(P.onDeparture) == 1


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
