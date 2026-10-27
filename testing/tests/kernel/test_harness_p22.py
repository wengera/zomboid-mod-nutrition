"""The Plan 22 Task 7 harness commands, offline: PZTestKit_Server.lua's Plan 22 Task 7 block (damage.watch,
zombie.get) and the fix wave H block after it (damage.unwatch), from the Task 7 marker line to the end of the file, in
a bare Lua 5.1 runtime with a stub TK, a stub findPlayer (the file's own is a local defined above the block), an
Events.OnPlayerGetDamage recorder with Add and Remove and a stub getCell whose zombie list is Lua stand-ins. They pin
each command's reply shape (an empty count or record list is {} on the bus, a Lua empty table), the listener's username
keying, its one-install guard, its 5000-record ring and the count a since misses, the since check, the unwatch and its
listener removal, and its pcall guard. The
first live session that uses them is their smoke test. The harness is never a kernel file, so the coverage gate is
untouched."""
import os

import lupa.lua51 as lua51

from .server_host import REPO

SERVER = os.path.join(REPO, "testing", "PZTestKit", "PZTestKit", "42", "media", "lua", "server", "PZTestKit_Server.lua")
MARK = "-- ---- Plan 22 Task 7: damage.watch and zombie.get (server)"
MARK_H = "-- ---- Plan 22 fix wave H: damage.unwatch (server)"

ENV = r"""
T = { listeners = {}, clock = 0 }
local function jlist(t)
    return { size = function(s) return #t end, get = function(s, i) return t[i + 1] end }
end
local function character(name)
    return { name = name, getUsername = function(s) return s.name end }
end
T.admin = character("admin")
T.other = character("bob")
T.raiser = { getUsername = function(s) error("boom") end }
local function zombie(id, health, x, y, z, dead)
    return {
        getOnlineID = function(s) return id end,
        getHealth = function(s) return health end,
        getX = function(s) return x end,
        getY = function(s) return y end,
        getZ = function(s) return z end,
        isDead = function(s) return dead end,
    }
end
T.zombies = { zombie(3, 0.5, 10.5, 20.5, 0, false), zombie(7, 1.25, 100.5, 200.25, 1, false) }
getCell = function()
    return { getZombieList = function(s) return jlist(T.zombies) end }
end
findPlayer = function(name)
    if name == "admin" then return T.admin end
    return nil
end
Events = { OnPlayerGetDamage = {
    Add = function(fn) T.listeners[#T.listeners + 1] = fn end,
    Remove = function(fn)
        for i = #T.listeners, 1, -1 do
            if T.listeners[i] == fn then table.remove(T.listeners, i) end
        end
    end,
} }
TK = { side = "server", commands = {} }
TK.register = function(name, fn) TK.commands[name] = fn end
TK.now = function() T.clock = T.clock + 1; return T.clock end
TK.call = function(obj, name, ...)
    if obj == nil then return false, nil end
    local m = obj[name]
    if m == nil then return false, nil end
    return true, m(obj, ...)
end
function T.fire(ch, tag, amount)
    for i = 1, #T.listeners do T.listeners[i](ch, tag, amount) end
end
"""


def section():
    with open(SERVER, encoding="utf-8", newline="") as fh:
        src = fh.read().replace("\r\n", "\n")
    return src[src.index(MARK):]


class Server:
    def __init__(self):
        self.rt = lua51.LuaRuntime(unpack_returned_tuples=True)
        self.rt.execute(ENV)
        self.rt.eval("function(src, name) return assert(loadstring(src, name)) end")(section(), "p22_block")()
        g = self.rt.globals()
        self.T, self.TK = g.T, g.TK


def cmd(s, name, *args):
    return s.TK.commands[name](s.rt.table(*args))


def fire(s, who, tag, amount=1.0):
    s.T.fire(s.T[who], tag, amount)


def lst(t):
    return [t[i] for i in range(1, len(t) + 1)]


def counts(t):
    return dict(t.items())


def test_the_markers_open_their_blocks_and_they_register_three_commands():
    with open(SERVER, encoding="utf-8", newline="") as fh:
        lines = fh.read().split("\r\n")
    assert MARK in lines and MARK_H in lines and lines.index(MARK) < lines.index(MARK_H)
    s = Server()
    for name in ("damage.watch", "zombie.get", "damage.unwatch"):
        assert s.TK.commands[name] is not None


def test_damage_watch_hooks_once_and_replies_empty_tables():
    s = Server()
    r = cmd(s, "damage.watch", "admin")
    assert r.ok is True and r.side == "server" and r.hooked is True and r.user == "admin"
    assert counts(r.counts) == {} and r.n == 0 and r.dropped == 0 and len(r.last) == 0
    assert r.reason is None
    cmd(s, "damage.watch", "admin")
    cmd(s, "damage.watch", "bob")
    assert len(s.T.listeners) == 1


def test_damage_watch_counts_the_named_users_tags_and_keeps_indexed_records():
    s = Server()
    cmd(s, "damage.watch", "admin")
    fire(s, "admin", "HEAVYLOAD", 0.5)
    fire(s, "admin", "HEAVYLOAD", 0.75)
    fire(s, "other", "HEAVYLOAD", 9.0)
    fire(s, "admin", "FALLDOWN", 2.0)
    r = cmd(s, "damage.watch", "admin")
    assert counts(r.counts) == {"HEAVYLOAD": 2, "FALLDOWN": 1}
    assert r.n == 3 and r.dropped == 0
    recs = lst(r.last)
    assert [x.i for x in recs] == [1, 2, 3]
    assert [x.tag for x in recs] == ["HEAVYLOAD", "HEAVYLOAD", "FALLDOWN"]
    assert [x.amount for x in recs] == [0.5, 0.75, 2.0]
    assert all(isinstance(x.wall, (int, float)) for x in recs)


def test_damage_watch_keys_by_username_so_an_offline_user_can_be_watched():
    s = Server()
    r = cmd(s, "damage.watch", "bob")                               # findPlayer("bob") is nil: still watched
    assert r.ok is True and r.user == "bob" and r.n == 0
    fire(s, "other", "HEAVYLOAD")
    fire(s, "admin", "HEAVYLOAD")
    r = cmd(s, "damage.watch", "bob")
    assert r.n == 1 and counts(r.counts) == {"HEAVYLOAD": 1}


def test_damage_watch_since_returns_only_later_records():
    s = Server()
    cmd(s, "damage.watch", "admin")
    for tag in ("HEAVYLOAD", "HEAVYLOAD", "FALLDOWN"):
        fire(s, "admin", tag)
    r = cmd(s, "damage.watch", "admin", "since", "2")
    recs = lst(r.last)
    assert [x.i for x in recs] == [3] and recs[0].tag == "FALLDOWN"
    assert r.n == 3 and counts(r.counts) == {"HEAVYLOAD": 2, "FALLDOWN": 1}


def test_damage_watch_keeps_a_ring_of_the_last_5000_and_names_what_a_since_missed():
    s = Server()
    cmd(s, "damage.watch", "admin")
    assert s.TK.DW_MAX == 5000
    for _ in range(5100):
        fire(s, "admin", "HEAVYLOAD")
    assert len(s.TK.DW.users["admin"].ring) == 5000                 # the ring never grows past its cap
    r = cmd(s, "damage.watch", "admin")                             # no since: everything aged out is missed
    recs = lst(r.last)
    assert r.n == 5100 and r.dropped == 100 and len(recs) == 5000
    assert recs[0].i == 101 and recs[-1].i == 5100
    assert [x.i for x in recs] == list(range(101, 5101))
    assert counts(r.counts) == {"HEAVYLOAD": 5100}
    r = cmd(s, "damage.watch", "admin", "since", "50")              # records 51..100 aged out after the since
    recs = lst(r.last)
    assert r.dropped == 50 and len(recs) == 5000 and recs[0].i == 101 and recs[-1].i == 5100
    r = cmd(s, "damage.watch", "admin", "since", "100")             # the ring's oldest is 101: nothing missed
    assert r.dropped == 0 and len(r.last) == 5000
    r = cmd(s, "damage.watch", "admin", "since", "5000")
    recs = lst(r.last)
    assert r.dropped == 0 and [x.i for x in recs] == list(range(5001, 5101))
    r = cmd(s, "damage.watch", "admin", "since", "5100")
    assert r.dropped == 0 and len(r.last) == 0 and r.n == 5100


def test_damage_watch_ring_wraps_in_order_past_several_laps():
    s = Server()
    s.rt.execute("TK.DW_MAX = 3")
    cmd(s, "damage.watch", "admin")
    for k in range(1, 11):
        fire(s, "admin", "T%d" % k)
    r = cmd(s, "damage.watch", "admin")
    recs = lst(r.last)
    assert [x.i for x in recs] == [8, 9, 10] and [x.tag for x in recs] == ["T8", "T9", "T10"]
    assert r.n == 10 and r.dropped == 7
    r = cmd(s, "damage.watch", "admin", "since", "8")
    assert [x.i for x in lst(r.last)] == [9, 10] and r.dropped == 0


def test_damage_watch_listener_never_raises():
    s = Server()
    cmd(s, "damage.watch", "admin")
    s.T.fire(s.T.raiser, "HEAVYLOAD", 1.0)                          # getUsername raises inside the listener
    s.T.fire(None, "HEAVYLOAD", 1.0)
    fire(s, "admin", "FALLDOWN")
    r = cmd(s, "damage.watch", "admin")
    assert r.n == 1 and counts(r.counts) == {"FALLDOWN": 1}


def test_damage_watch_without_events_replies_not_hooked_with_a_reason():
    s = Server()
    s.rt.execute("Events = nil")
    r = cmd(s, "damage.watch", "admin")
    assert r.ok is False and r.hooked is False and r.reason == "no Events.OnPlayerGetDamage on this side"


def test_damage_watch_usage():
    s = Server()
    assert cmd(s, "damage.watch") == "usage: damage.watch <user> [since <i>]"
    assert cmd(s, "damage.watch", "admin", "since", "x") == "usage: damage.watch <user> [since <i>]"
    assert len(s.T.listeners) == 0


def test_damage_watch_since_must_be_a_non_negative_integer():
    s = Server()
    usage = "usage: damage.watch <user> [since <i>]"
    for bad in (("since",), ("since", "1.5"), ("since", "-1"), ("since", "abc"), ("from", "3")):
        assert cmd(s, "damage.watch", "admin", *bad) == usage, bad
    assert len(s.T.listeners) == 0                                  # a refused call installs nothing
    r = cmd(s, "damage.watch", "admin", "since", "0")
    assert r.ok is True and r.n == 0


def test_damage_unwatch_drops_the_users_records_and_the_last_unwatch_removes_the_listener():
    s = Server()
    cmd(s, "damage.watch", "admin")
    cmd(s, "damage.watch", "bob")
    fire(s, "admin", "HEAVYLOAD")
    fire(s, "admin", "FALLDOWN")
    r = cmd(s, "damage.unwatch", "admin")
    assert r.ok is True and r.side == "server" and r.user == "admin" and r.watched is True and r.n == 2
    assert r.hooked is True and len(s.T.listeners) == 1             # bob is still watched
    assert s.TK.DW.users["admin"] is None
    fire(s, "admin", "HEAVYLOAD")                                   # no longer recorded
    r = cmd(s, "damage.unwatch", "bob")
    assert r.watched is True and r.n == 0 and r.hooked is False and len(s.T.listeners) == 0
    r = cmd(s, "damage.watch", "admin")                             # a fresh watch re-hooks and starts at zero
    assert r.ok is True and r.n == 0 and len(r.last) == 0 and len(s.T.listeners) == 1
    fire(s, "admin", "FALLDOWN")
    assert cmd(s, "damage.watch", "admin").n == 1


def test_damage_unwatch_of_an_unwatched_user_and_usage():
    s = Server()
    r = cmd(s, "damage.unwatch", "carol")
    assert r.ok is True and r.user == "carol" and r.watched is False and r.n == 0 and r.hooked is False
    assert cmd(s, "damage.unwatch") == "usage: damage.unwatch <user>"
    assert cmd(s, "damage.unwatch", "") == "usage: damage.unwatch <user>"


def test_zombie_get_finds_health_and_position_by_online_id():
    s = Server()
    r = cmd(s, "zombie.get", "7")
    assert r.ok is True and r.side == "server" and r.id == 7 and r.found is True
    assert r.health == 1.25 and r.x == 100.5 and r.y == 200.25 and r.z == 1 and r.dead is False


def test_zombie_get_unknown_id_is_not_found():
    s = Server()
    r = cmd(s, "zombie.get", "99")
    assert r.ok is True and r.found is False and r.id == 99
    assert r.health is None and r.x is None


def test_zombie_get_without_a_cell_replies_a_reason():
    s = Server()
    s.rt.execute("getCell = nil")
    r = cmd(s, "zombie.get", "7")
    assert r.ok is False and r.found is False and isinstance(r.reason, str)


def test_zombie_get_usage():
    s = Server()
    assert cmd(s, "zombie.get") == "usage: zombie.get <onlineId>"
    assert cmd(s, "zombie.get", "abc") == "usage: zombie.get <onlineId>"
    assert cmd(s, "zombie.get", "1.5") == "usage: zombie.get <onlineId>"
