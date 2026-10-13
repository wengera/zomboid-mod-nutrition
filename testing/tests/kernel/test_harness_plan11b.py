"""The Plan 11b Task 1 harness commands, offline: PZTestKit_Client.lua's and PZTestKit_Server.lua's Plan 11b blocks, each
from its marker line to the end of its file. The client block runs in a bare Lua 5.1 runtime with a stub C, TK, player
and clock; the server block on the shared server host beside the real mod, with a stub TK and a global findPlayer (the
file's own is a local at :25). They pin each command's reply shape, its refusals and what it leaves behind, which the
first live session that uses each command cannot cheaply show; that session is still its smoke test. The harness is
never a kernel file, so the coverage gate is untouched."""
import os

import lupa.lua51 as lua51

from .server_host import Host, REPO

LUA = os.path.join(REPO, "testing", "PZTestKit", "PZTestKit", "42", "media", "lua")
CLIENT = os.path.join(LUA, "client", "PZTestKit_Client.lua")
SERVER = os.path.join(LUA, "server", "PZTestKit_Server.lua")
CORE = os.path.join(LUA, "shared", "PZTestKit_Core.lua")

CLIENT_MARK = "-- ==== Plan 11b Task 1 additions (client"
SERVER_MARK = "-- ==== Plan 11b Task 1 additions (server"


def section(path, marker):
    with open(path, encoding="utf-8", newline="") as fh:
        src = fh.read().replace("\r\n", "\n")
    return src[src.index(marker):]


def load(rt, src, name):
    rt.eval("function(src, name) return assert(loadstring(src, name)) end")(src, name)()


def lst(t):
    return [t[i] for i in range(1, len(t) + 1)]


# ---- the client block ------------------------------------------------------------------------------------------------

CLIENT_ENV = r"""
T = { now = 1000, ticks = {}, level = 0, raise = false }
getTimestampMs = function() return T.now end
Events = { OnTick = { Add = function(fn) T.ticks[#T.ticks + 1] = fn end } }
MoodleType = { PANIC = "E_PANIC", HUNGRY = "E_HUNGRY" }
T.moodles = { getMoodleLevel = function(s, mt)
    if T.raise then error("a Java raise") end
    if mt == "E_PANIC" then return T.level end
    return 0
end }
T.player = { getMoodles = function(s) return T.moodles end }
getPlayer = function() return T.player end
C = {}
TK = { side = "client", commands = {} }
TK.register = function(name, fn) TK.commands[name] = fn end
TK.call = function(obj, name, ...)
    if obj == nil then return false, nil end
    local m = obj[name]
    if m == nil then return false, nil end
    return true, m(obj, ...)
end
function T.tick(n, dt)
    for i = 1, n do
        T.now = T.now + dt
        for j = 1, #T.ticks do T.ticks[j]() end
    end
end
"""


def client():
    rt = lua51.LuaRuntime(unpack_returned_tuples=True)
    rt.execute(CLIENT_ENV)
    load(rt, section(CLIENT, CLIENT_MARK), "@PZTestKit_Client.lua")
    g = rt.globals()
    return rt, g


def ccmd(rt, g, name, *args):
    return g.TK.commands[name](rt.table(*args))


def test_moodle_watch_records_every_level_change_inside_the_window_and_ends_it():
    rt, g = client()
    T = g.T
    assert ccmd(rt, g, "moodle.watch", "read").reason == "not armed"
    r = ccmd(rt, g, "moodle.watch", "PANIC", "1")
    assert r.ok is True and r.armed is True and r.moodle == "PANIC" and r.seconds == 1
    T.tick(4, 100)                                   # level 0 four ticks (1100-1400 ms)
    T.level = 2
    T.tick(2, 100)                                   # 0 -> 2 at 1500
    T.level = 1
    T.tick(4, 100)                                   # 2 -> 1 at 1700; the window (1000 ms) ends at 2000, sampled
    T.level = 3
    T.tick(5, 100)                                   # past the window: never sampled
    w = ccmd(rt, g, "moodle.watch", "read")
    assert w.ok is True and w.done is True and w.moodle == "PANIC"
    assert w.samples == 10 and w.min == 0 and w.max == 2 and w.level == 1
    assert w.transitions == 2
    ch = lst(w.changes)
    assert [(c["from"], c.to) for c in ch] == [(0, 2), (2, 1)]
    assert ch[0].at == 1500 and ch[1].at == 1700     # the wall ms of the tick that saw each change
    assert w.err is None


def test_moodle_watch_refuses_an_unknown_moodle_and_a_bad_window():
    rt, g = client()
    r = ccmd(rt, g, "moodle.watch", "NOSUCH", "5")
    assert r.ok is False and r.reason == "no MoodleType.NOSUCH"
    assert ccmd(rt, g, "moodle.watch", "PANIC", "0") == "usage: moodle.watch <MoodleType> <seconds> | read"
    assert ccmd(rt, g, "moodle.watch", "PANIC") == "usage: moodle.watch <MoodleType> <seconds> | read"


def test_a_raising_sample_ends_the_window_and_reads_back_as_err():
    rt, g = client()
    T = g.T
    ccmd(rt, g, "moodle.watch", "PANIC", "10")
    T.tick(2, 100)
    T["raise"] = True
    T.tick(1, 100)                                   # the listener's pcall catches it; nothing escapes the tick
    w = ccmd(rt, g, "moodle.watch", "read")
    assert w.done is True and "a Java raise" in w.err and w.samples == 2


# ---- the server block ------------------------------------------------------------------------------------------------

SERVER_ENV = r"""
NR_T.now = 5000000
getTimestampMs = function() NR_T.now = NR_T.now + 1; return NR_T.now end
MoodleType = { PANIC = "E_PANIC" }
"""

STUB_TK = r"""
TK = { side = "server", commands = {}, results = {} }
TK.register = function(name, fn) TK.commands[name] = fn end
TK.now = function() return getTimestampMs() end
TK.log = function(msg) NR_T.printed[#NR_T.printed + 1] = "PZTK: " .. tostring(msg) end
TK.call = function(obj, name, ...)
    if obj == nil then return false, nil end
    local m = obj[name]
    if m == nil then return false, nil end
    return true, m(obj, ...)
end
findPlayer = function(username)
    local list = getOnlinePlayers()
    for i = 0, list:size() - 1 do
        local p = list:get(i)
        if p:getUsername() == username then return p end
    end
    return nil
end
"""

MOODLES = r"""
function(p, level)
    p.moodleLevel = level
    p.getMoodles = function(s)
        return { getMoodleLevel = function(m, mt) if mt == "E_PANIC" then return p.moodleLevel end return 0 end }
    end
end
"""


def server(extra_env=""):
    h = Host(extra_env=SERVER_ENV + extra_env)
    p = h.player("admin")
    h.rt.eval(MOODLES)(p, 2)
    h.p = p
    h.online(p)
    h.minute()
    h.tick(10)                                       # the record exists
    assert h.record("admin") is not None
    h.rt.execute(STUB_TK)
    load(h.rt, section(CORE, "-- ==== Plan 11f Task 1 additions (H1)"), "@PZTestKit_Core.lua")
    load(h.rt, section(SERVER, SERVER_MARK), "@PZTestKit_Server.lua")
    h.TK = h.G.TK
    return h


def scmd(h, name, *args):
    return h.TK.commands[name](h.rt.table(*args))


def test_moodle_level_reads_a_named_players_level_and_refuses_the_rest():
    h = server()
    r = scmd(h, "moodle.level", "admin", "PANIC")
    assert r.ok is True and r.side == "server" and r.user == "admin" and r.moodle == "PANIC" and r.level == 2
    h.p.moodleLevel = 0
    assert scmd(h, "moodle.level", "admin", "PANIC").level == 0
    r = scmd(h, "moodle.level", "nobody", "PANIC")
    assert r.ok is False and r.reason == "no online player"
    r = scmd(h, "moodle.level", "admin", "NOSUCH")
    assert r.ok is False and r.reason == "no MoodleType.NOSUCH"
    assert scmd(h, "moodle.level", "admin") == "usage: moodle.level <user> <MoodleType>"
