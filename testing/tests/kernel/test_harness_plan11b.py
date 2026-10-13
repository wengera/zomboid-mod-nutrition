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


# ---- H3 action.cancel (client) ---------------------------------------------------------------------------------------

# vanilla's clear (ISTimedActionQueue.lua:236-243) and clearQueue (:46-58), with a character whose StopAllActionQueue
# stops the started Java action, whose stop() resets the Lua queue (ISBaseTimedAction:stop, :63-66)
QUEUE = r"""
T.java = {}
T.stops = 0
T.player.getCharacterActions = function(s) return { size = function(l) return #T.java end } end
T.player.StopAllActionQueue = function(s)
    T.stops = T.stops + 1
    T.java = {}
    local q = ISTimedActionQueue.getTimedActionQueue(s)
    for i = #q.queue, 1, -1 do q.queue[i] = nil end
end
local Q = { queue = {} }
function Q:isCurrentActionAddingOtherActions()
    local current = self.queue[1]
    return (current ~= nil) and current._isAddingActions and (tonumber(current._numAddedActions) ~= nil)
end
function Q:clearQueue()
    if self:isCurrentActionAddingOtherActions() then
        local current = self.queue[1]
        for i = 1, current._numAddedActions do table.remove(self.queue, 2) end
        current._numAddedActions = 0
        return
    end
    for i = #self.queue, 1, -1 do self.queue[i] = nil end
end
ISTimedActionQueue = { q = Q }
ISTimedActionQueue.getTimedActionQueue = function(character) return Q end
ISTimedActionQueue.clear = function(character)
    local queue = ISTimedActionQueue.getTimedActionQueue(character)
    if not queue:isCurrentActionAddingOtherActions() then
        character:StopAllActionQueue()
    end
    queue:clearQueue()
    return queue
end
function T.action(type, started)
    local a = { Type = type, started = started }
    function a:isStarted() return self.started end
    return a
end
"""


def client_with_queue():
    rt, g = client()
    rt.execute(QUEUE)
    return rt, g


def test_action_cancel_stops_a_started_action_and_empties_the_queue():
    rt, g = client_with_queue()
    T = g.T
    q = g.ISTimedActionQueue.q.queue
    q[1] = T.action("ISEatFoodAction", True)
    q[2] = T.action("ISWalkToTimedAction", False)
    T.java[1] = "the started Java action"
    r = ccmd(rt, g, "action.cancel")
    assert r.ok is True and r.cleared is True and r.clearError is None
    assert r.before == 2 and r.after == 0
    assert r.current == "ISEatFoodAction" and r.started is True
    assert r.adding is False and r.stopped is True and T.stops == 1
    assert r.javaBefore == 1 and r.javaAfter == 0


def test_action_cancel_on_an_empty_queue_still_calls_the_stop():
    rt, g = client_with_queue()
    r = ccmd(rt, g, "action.cancel")
    assert r.ok is True and r.before == 0 and r.after == 0 and r.current is None and r.started is False
    assert r.stopped is True and g.T.stops == 1


def test_action_cancel_says_when_the_current_action_is_adding_others():
    rt, g = client_with_queue()
    T = g.T
    q = g.ISTimedActionQueue.q.queue
    cur = T.action("ISInventoryTransferAction", True)
    cur._isAddingActions = True
    cur._numAddedActions = 1
    q[1] = cur
    q[2] = T.action("ISEatFoodAction", False)
    r = ccmd(rt, g, "action.cancel")
    assert r.adding is True and r.stopped is False and T.stops == 0   # clear skipped StopAllActionQueue
    assert r.before == 2 and r.after == 1                                  # only the added action went


def test_action_cancel_refuses_without_the_vanilla_queue():
    rt, g = client()
    r = ccmd(rt, g, "action.cancel")
    assert r.ok is False and r.reason == "no ISTimedActionQueue.clear"


# ---- H4 sched.arm (server) -------------------------------------------------------------------------------------------

def many(h, n):
    """n online players (admin first), each with moodles, every record laid."""
    ps = [h.p] + [h.player("p%d" % i) for i in range(1, n)]
    for p in ps[1:]:
        h.rt.eval(MOODLES)(p, 0)
    h.online(*ps)
    h.minute()
    h.tick(40)
    return ps


def test_sched_arm_spread_lowers_each_minutes_cap_to_the_spread_and_off_restores_the_mods_step():
    h = server()
    P = h.NR.server.players
    many(h, 12)
    base = P.minute
    r = scmd(h, "sched.arm", "spread", "1")
    assert r.ok is True and r.armed is True and r.k == 1 and r.minutes == 0
    assert not h.rt.eval("rawequal")(P.minute, base)
    h.minute()                                       # the mod's listener reaches the wrapper through the table
    queued = len(P.queue) - P.queueHead + 1
    tpm = h.K.sched.ticksPerMinute(P.ticksLast, P.ticksPrev)
    shipped = h.K.sched.runCap(P.budgetMs, P.meanMs)
    spread = max(1, -(-queued * 1 // tpm))
    assert queued == 12 and spread < shipped
    assert P.runCap == spread
    r = scmd(h, "sched.arm", "read")
    assert r.minutes == 1 and r.capped == 1 and r.lastLowered is True
    assert r.lastSpread == spread and r.lastShipped == shipped and r.lastQueued == 12 and r.lastTpm == tpm
    assert r.budgetMs == P.budgetMs                  # the budget is the mod's, untouched
    h.tick(1)
    assert len(P.queue) - P.queueHead + 1 == 12 - spread   # the drain ran at the spread cap
    off = scmd(h, "sched.arm", "off")
    assert off.ok is True and off.armed is False and off.restoredCap == shipped and P.runCap == shipped
    assert h.rt.eval("rawequal")(P.minute, base)
    h.minute()
    assert scmd(h, "sched.arm", "read").minutes == 1  # the mod's own step again: the wrapper never ran


def test_sched_arm_leaves_a_cap_already_under_the_spread_and_rearms_with_a_new_k():
    h = server()
    P = h.NR.server.players
    many(h, 3)
    scmd(h, "sched.arm", "spread", "100")
    h.minute()
    r = scmd(h, "sched.arm", "read")
    assert r.capped == 0 and r.lastLowered is False and P.runCap == r.lastShipped
    w = P.minute
    scmd(h, "sched.arm", "spread", "0.5")            # a second arm changes k only
    assert h.rt.eval("rawequal")(P.minute, w) and scmd(h, "sched.arm", "read").k == 0.5
    h.minute()
    r = scmd(h, "sched.arm", "read")
    assert r.minutes == 2 and P.runCap == min(r.lastShipped, r.lastSpread)


def test_sched_arm_counts_nothing_when_the_minute_did_not_run_and_refuses_bad_arguments():
    h = server()
    P = h.NR.server.players
    scmd(h, "sched.arm", "spread", "1")
    h.G.getOnlinePlayers = None                      # P.minute returns before it counts a minute
    h.minute()
    assert scmd(h, "sched.arm", "read").minutes == 0
    usage = "usage: sched.arm spread <k> | off | read"
    assert scmd(h, "sched.arm", "spread", "0") == usage
    assert scmd(h, "sched.arm", "spread") == usage
    assert scmd(h, "sched.arm", "sideways") == usage
    scmd(h, "sched.arm", "off")
    assert scmd(h, "sched.arm", "off").reason == "not armed"


def test_sched_arm_off_leaves_a_later_wrap_in_place():
    h = server()
    P = h.NR.server.players
    scmd(h, "sched.arm", "spread", "1")
    later = h.rt.eval("function(P) local w = P.minute; P.minute = function() return w() end; return P.minute end")(P)
    r = scmd(h, "sched.arm", "off")
    assert r.ok is False and "replaced" in r.reason and h.rt.eval("rawequal")(P.minute, later)


# ---- H5 stats.bench (server) -----------------------------------------------------------------------------------------

STATS = r"""
function(p)
    local st = { vals = { E_BOREDOM = 12.5 }, gets = 0, sets = 0, setVals = {} }
    st.get = function(s, e) s.gets = s.gets + 1; return s.vals[e] end
    st.set = function(s, e, v) s.sets = s.sets + 1; s.setVals[v] = true; s.vals[e] = v end
    p.st = st
    p.getStats = function(s) return st end
end
"""

BENCH_ENV = r"""
CharacterStat = { BOREDOM = "E_BOREDOM", PANIC = "E_PANIC" }
"""


def bench_server():
    h = server(BENCH_ENV)
    h.rt.eval(STATS)(h.p)
    return h


def test_stats_bench_times_n_unchanged_get_and_set_pairs_bare_and_wrapped():
    h = bench_server()
    st = h.p.st
    g0, s0 = st.gets, st.sets
    r = scmd(h, "stats.bench", "admin", "BOREDOM", "1000")
    assert r.ok is True and r.side == "server" and r.wrapped is False and r.n == 1000
    assert st.gets - g0 == 1000 + 2 and st.sets - s0 == 1000      # the pairs, plus the before and after reads
    assert r.before == 12.5 and r.after == 12.5 and list(st.setVals.keys()) == [12.5]   # set back unchanged
    assert r.ms >= 0 and r.usPerPair == r.ms * 1000 / 1000 and r.loopMs >= 0 and r.err is None
    g1, s1 = st.gets, st.sets
    w = scmd(h, "stats.bench", "admin", "BOREDOM", "500", "wrapped")
    assert w.ok is True and w.wrapped is True and st.gets - g1 == 500 + 2 and st.sets - s1 == 500
    assert w.after == 12.5


def test_stats_bench_refuses_what_it_cannot_price():
    h = bench_server()
    usage = "usage: stats.bench <user> <STAT> <n 1-100000> [wrapped]"
    assert scmd(h, "stats.bench", "admin", "BOREDOM") == usage
    assert scmd(h, "stats.bench", "admin", "BOREDOM", "0") == usage
    assert scmd(h, "stats.bench", "admin", "BOREDOM", "100001") == usage
    assert scmd(h, "stats.bench", "nobody", "BOREDOM", "10").reason == "no online player"
    assert scmd(h, "stats.bench", "admin", "NOSUCH", "10").reason == "no CharacterStat.NOSUCH"
    r = scmd(h, "stats.bench", "admin", "PANIC", "10")              # a stat the stub reads as nil
    assert r.ok is False and "read no number" in r.reason and h.p.st.sets == 0


# ---- H6 record.set (server) ------------------------------------------------------------------------------------------

def test_record_set_reaches_a_bracketed_full_type_key_and_replies_before_and_after():
    h = server()
    rec = h.record("admin")
    rec.monotony = h.rt.table_from({"t": h.rt.table_from({"TKX.Mono450": h.rt.table_from({"n": 5, "last": 100.25})})})
    r = scmd(h, "record.set", "admin", "monotony.t.[TKX.Mono450].last", "-68")
    assert r.ok is True and r.side == "server" and r.key == "last" and r.keyType == "string"
    assert r.before == 100.25 and r.beforeType == "number" and r.after == -68 and r.afterType == "number"
    assert rec.monotony.t["TKX.Mono450"].last == -68
    r = scmd(h, "record.set", "admin", "dead", "true")
    assert r.ok is True and r.before is False and r.after is True and rec.dead is True
    r = scmd(h, "record.set", "admin", "monotony.t.[TKX.Mono450].note", "hello")   # an absent leaf, on its parent
    assert r.ok is True and r.before is None and r.beforeType == "nil" and rec.monotony.t["TKX.Mono450"].note == "hello"
    r = scmd(h, "record.set", "admin", "monotony.t.[TKX.Mono450].note", "nil")
    assert r.ok is True and r.after is None and r.afterType == "nil"


def test_record_set_takes_the_number_key_of_a_ring_slot():
    h = server()
    rec = h.record("admin")
    rec.ring = h.rt.table(10, 20, 30)
    r = scmd(h, "record.set", "admin", "ring.2", "25")
    assert r.ok is True and r.keyType == "number" and r.before == 20 and rec.ring[2] == 25 and rec.ring["2"] is None
    r = scmd(h, "record.set", "admin", "ring.4", "40")                # an absent numeric leaf: the number key
    assert r.ok is True and r.keyType == "number" and rec.ring[4] == 40


def test_record_set_never_creates_a_parent_a_record_or_a_global():
    h = server()
    rec = h.record("admin")
    r = scmd(h, "record.set", "admin", "monotony.t.[TKX.Mono450].last", "1")
    assert r.ok is False and r.error.startswith("parent nil") and rec.monotony is None
    r = scmd(h, "record.set", "nobody", "dead", "true")
    assert r.ok is False and r.error == "no record" and h.record("nobody") is None
    r = scmd(h, "record.set", "admin", "_G.TKX_flag", "1")
    assert r.ok is False and "_G" in r.error and h.G.TKX_flag is None
    rec.satiety = h.rt.table_from({"M": 300})
    r = scmd(h, "record.set", "admin", "satiety", "5")
    assert r.ok is False and "scalars only" in r.error and rec.satiety.M == 300
    r = scmd(h, "record.set", "admin", "monotony.[TKX.Mono450", "5")
    assert r.ok is False and r.error.startswith("bad path")
    assert scmd(h, "record.set", "admin", "dead") == "usage: record.set <user> <path> <value>"
