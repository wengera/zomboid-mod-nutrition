"""The probe mod TKX_Symptoms (Plan 18 Task 1), offline: its server and client Lua loaded in a Lua 5.1 host (lupa) over
stubs of the engine members it reaches (getOnlinePlayers, CharacterStat, BodyPartType, MoodleType, getGameTime, Events,
isServer and isClient, the harness's TK.result). It pins what the live sessions read through lua.call and lua.read:
the holds' write rules (pain re-set every minute, a ceiling only above, a floor only below), the minute log's rows
and their multiplier sums, the per-tick snapshot and its level trackers, the ring's cap, the dump's document, and the
listeners added only on their own side."""
import os

import lupa.lua51 as lua51
import pytest

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LUA = os.path.join(REPO, "testing", "experiments", "TKX_Symptoms", "42.21", "media", "lua")
SERVER = os.path.join(LUA, "server", "TKX_Symptoms_Server.lua")
CLIENT = os.path.join(LUA, "client", "TKX_Symptoms_Client.lua")

STUBS = r"""
W = { now = 1000, age = 10.0, mult = 4.8, server = true, client = false, results = {}, events = {} }
getTimestampMs = function() return W.now end
isServer = function() return W.server end
isClient = function() return W.client end
getGameTime = function()
    return { getWorldAgeHours = function(s) return W.age end, getMultiplier = function(s) return W.mult end }
end
CharacterStat = { PAIN = "PAIN", ENDURANCE = "ENDURANCE", STRESS = "STRESS", NICOTINE_WITHDRAWAL = "NICOTINE",
                  UNHAPPINESS = "UNHAPPINESS", BOREDOM = "BOREDOM", FATIGUE = "FATIGUE" }
MoodleType = { PAIN = "M_PAIN", ENDURANCE = "M_END", STRESS = "M_STRESS", UNHAPPY = "M_UNHAPPY" }
BodyPartType = { FromIndex = function(i) return "BPT" .. tostring(i) end }
function makePart()
    local bp = { pain = 0 }
    bp.getAdditionalPain = function(s) return s.pain end
    bp.setAdditionalPain = function(s, v) s.pain = v end
    return bp
end
function makePlayer(name)
    local p = { name = name, stats = { PAIN = 0, ENDURANCE = 1, STRESS = 0, NICOTINE = 0, UNHAPPINESS = 0,
                                       BOREDOM = 0, FATIGUE = 0 },
                parts = {}, levels = { M_PAIN = 0, M_END = 0, M_STRESS = 0, M_UNHAPPY = 0 }, sets = 0 }
    for i = 0, 16 do p.parts["BPT" .. tostring(i)] = makePart() end
    p.getUsername = function(s) return s.name end
    p.getStats = function(s)
        return { get = function(st, e) return s.stats[e] end,
                 set = function(st, e, v) s.stats[e] = v; s.sets = s.sets + 1 end }
    end
    p.getBodyDamage = function(s) return { getBodyPart = function(bd, t) return s.parts[t] end } end
    p.getMoodles = function(s) return { getMoodleLevel = function(m, mt) return s.levels[mt] end } end
    return p
end
ONLINE = {}
getOnlinePlayers = function()
    return { size = function(s) return #ONLINE end, get = function(s, i) return ONLINE[i + 1] end }
end
getPlayer = function() return ONLINE[1] end
Events = {}
for _, nm in ipairs({ "EveryOneMinute", "OnTick" }) do
    Events[nm] = { fns = {}, Add = function(self, fn) end }
    local ev = Events[nm]
    ev.Add = function(fn) ev.fns[#ev.fns + 1] = fn end
end
function fire(nm) for _, fn in ipairs(Events[nm].fns) do fn() end end
TK = { result = function(name, tbl) W.results[name] = tbl; return true end }
"""


def host(server=True, client=False, files=(SERVER,)):
    rt = lua51.LuaRuntime(unpack_returned_tuples=True)
    rt.execute(STUBS)
    rt.globals().W.server = server
    rt.globals().W.client = client
    rt.execute('ONLINE[1] = makePlayer("admin")')
    for f in files:
        with open(f, encoding="utf-8") as fh:
            rt.execute(fh.read())
    return rt


def lua_list(t):
    return [t[i] for i in range(1, len(t) + 1)] if t is not None else []


def test_listeners_only_on_the_server():
    rt = host(server=True)
    assert len(rt.eval("Events.EveryOneMinute.fns")) == 1 and len(rt.eval("Events.OnTick.fns")) == 1
    rt2 = host(server=False)
    assert len(rt2.eval("Events.EveryOneMinute.fns")) == 0 and len(rt2.eval("Events.OnTick.fns")) == 0


def test_reload_adds_no_second_listener():
    rt = host(server=True)
    with open(SERVER, encoding="utf-8") as fh:
        rt.execute(fh.read())
    assert len(rt.eval("Events.OnTick.fns")) == 1


def test_pain_hold_sets_at_arm_and_re_sets_every_minute_logging_before():
    rt = host()
    ok, before, after = rt.eval('TKX_Symptoms.hold("admin", "pain", 7, 20)')
    assert ok is True and before == 0 and after == 20
    rt.execute('ONLINE[1].parts["BPT7"].pain = 19.1')
    for _ in range(3):
        rt.execute("fire('OnTick')")
    rt.execute("fire('EveryOneMinute')")
    rows = lua_list(rt.eval("TKX_Symptoms.mlog.rows"))
    assert [r.ev for r in rows] == ["arm", "minute"]
    m = rows[1]
    assert m.key == "pain:7" and m.before == pytest.approx(19.1) and m.after == 20 and m.wrote is True
    assert m.ticks == 3 and m.mult == pytest.approx(3 * 4.8)
    assert rt.eval('ONLINE[1].parts["BPT7"].pain') == 20
    assert rt.eval("TKX_Symptoms.acc.ticks") == 0           # the sums restart at every minute event


def test_ceiling_writes_only_above_and_floor_only_below():
    rt = host()
    rt.execute('ONLINE[1].stats.ENDURANCE = 0.70')
    ok, before, after = rt.eval('TKX_Symptoms.hold("admin", "endcap", 0.74)')
    assert ok and before == pytest.approx(0.70) and after == pytest.approx(0.70)
    assert rt.eval("ONLINE[1].sets") == 0
    rt.execute('ONLINE[1].stats.ENDURANCE = 0.7456')
    rt.execute("fire('EveryOneMinute')")
    assert rt.eval("ONLINE[1].stats.ENDURANCE") == pytest.approx(0.74)
    rt.execute('ONLINE[1].stats.STRESS = 0.4')
    rt.eval('TKX_Symptoms.hold("admin", "stress", 0.30)')
    assert rt.eval("ONLINE[1].stats.STRESS") == pytest.approx(0.4)        # above the floor: untouched
    rt.execute('ONLINE[1].stats.STRESS = 0.29')
    rt.execute("fire('EveryOneMinute')")
    assert rt.eval("ONLINE[1].stats.STRESS") == pytest.approx(0.30)
    rt.execute('ONLINE[1].stats.BOREDOM = 3')
    rt.eval('TKX_Symptoms.hold("admin", "boredcap", 0)')
    assert rt.eval("ONLINE[1].stats.BOREDOM") == 0
    rt.eval('TKX_Symptoms.hold("admin", "unhappy", 25)')
    assert rt.eval("ONLINE[1].stats.UNHAPPINESS") == 25


def test_hold_refuses_unknown_kinds_offline_players_and_bad_args():
    rt = host()
    assert rt.eval('TKX_Symptoms.hold("bob", "pain", 7, 20)')[0] is False
    assert rt.eval('TKX_Symptoms.hold("admin", "warp", 1)')[0] is False
    assert rt.eval('TKX_Symptoms.hold("admin", "pain", 7)')[0] is False
    assert rt.eval('TKX_Symptoms.hold("admin", "endcap", "x")')[0] is False


def test_release_one_and_all():
    rt = host()
    rt.eval('TKX_Symptoms.hold("admin", "pain", 7, 20)')
    rt.eval('TKX_Symptoms.hold("admin", "endcap", 0.5)')
    assert rt.eval('TKX_Symptoms.release("pain", 7)') is True
    assert rt.eval('TKX_Symptoms.release("pain", 7)') is False
    assert rt.eval('TKX_Symptoms.release("all")') == (True, 1)
    rt.execute('ONLINE[1].parts["BPT7"].pain = 5')
    rt.execute("fire('EveryOneMinute')")
    assert rt.eval('ONLINE[1].parts["BPT7"].pain') == 5        # no hold: no re-set


def test_set_pain_is_one_shot():
    rt = host()
    ok, before, after = rt.eval('TKX_Symptoms.setPain("admin", 7, 60)')
    assert ok is True and before == 0 and after == 60
    rt.execute('ONLINE[1].parts["BPT7"].pain = 59')
    rt.execute("fire('EveryOneMinute')")
    assert rt.eval('ONLINE[1].parts["BPT7"].pain') == 59
    assert rt.eval("TKX_Symptoms.trackPart") == 7


def test_tick_snapshot_trackers_and_reset():
    rt = host()
    rt.eval('TKX_Symptoms.watch("admin")')
    rt.execute('ONLINE[1].levels.M_END = 1')
    rt.execute("fire('OnTick')")
    rt.execute('ONLINE[1].levels.M_END = 0; ONLINE[1].stats.PAIN = 15.5; ONLINE[1].parts["BPT7"].pain = 20')
    rt.execute("fire('OnTick')")
    s = rt.eval("TKX_Symptoms.s")
    assert s.online is True and s.pain == 15.5 and s.part == 20 and s.lvEnd == 0 and s.n == 2
    trk = rt.eval("TKX_Symptoms.trk")
    assert trk.lvEndMin == 0 and trk.lvEndMax == 1 and trk.n == 2
    rt.eval("TKX_Symptoms.trkReset()")
    assert rt.eval("TKX_Symptoms.trk.lvEndMin") is None and rt.eval("TKX_Symptoms.trk.n") == 0


def test_snapshot_marks_an_offline_watched_player():
    rt = host()
    rt.eval('TKX_Symptoms.watch("admin")')
    rt.execute("ONLINE[1] = nil")
    rt.execute("fire('OnTick')")
    assert rt.eval("TKX_Symptoms.s.online") is False


def test_ring_records_while_on_and_counts_past_its_cap():
    rt = host()
    rt.eval('TKX_Symptoms.watch("admin")')
    rt.execute("TKX_Symptoms.RING_CAP = 3")
    rt.execute("fire('OnTick')")
    assert rt.eval("TKX_Symptoms.ring.n") == 0                 # off by default
    rt.eval("TKX_Symptoms.ringOn(true)")
    for _ in range(5):
        rt.execute("fire('OnTick')")
    assert rt.eval("TKX_Symptoms.ring.n") == 3 and rt.eval("TKX_Symptoms.ring.dropped") == 2


def test_minute_log_cap_counts_drops():
    rt = host()
    rt.execute("TKX_Symptoms.MINUTE_CAP = 2")
    rt.eval('TKX_Symptoms.hold("admin", "pain", 7, 20)')
    rt.execute("fire('EveryOneMinute'); fire('EveryOneMinute')")
    assert rt.eval("TKX_Symptoms.mlog.n") == 2 and rt.eval("TKX_Symptoms.mlog.dropped") == 1


def test_dump_writes_the_document_through_tk_result():
    rt = host()
    rt.eval('TKX_Symptoms.watch("admin")')
    rt.eval("TKX_Symptoms.ringOn(true)")
    rt.eval('TKX_Symptoms.hold("admin", "pain", 7, 20)')
    rt.execute("fire('OnTick'); fire('EveryOneMinute')")
    ok, mn, tn = rt.eval('TKX_Symptoms.dump("end")')
    assert ok is True and mn == 2 and tn == 1
    doc = rt.eval('W.results["tkxs-end"]')
    assert doc.mN == 2 and doc.tN == 1 and doc.user == "admin" and doc.holds["pain:7"].value == 20
    rt.execute("TK = nil")
    assert rt.eval('TKX_Symptoms.dump("x")')[0] is False


def test_a_raising_member_is_a_recorded_error_not_a_raise():
    rt = host()
    rt.eval('TKX_Symptoms.watch("admin")')
    rt.execute("getGameTime = function() error('boom') end")
    rt.execute("fire('OnTick')")                               # the multiplier read is under pcall
    assert rt.eval("TKX_Symptoms.s.online") is True
    rt.execute("TKX_Symptoms.findPlayer = function() error('kaboom') end")
    rt.execute("fire('OnTick')")
    assert "kaboom" in rt.eval("TKX_Symptoms.lastError")


def test_client_snapshot_trackers_and_part_choice():
    rt = host(server=False, client=True, files=(SERVER, CLIENT))
    assert len(rt.eval("Events.OnTick.fns")) == 1                # the client file's only
    rt.execute('ONLINE[1].levels.M_PAIN = 1; ONLINE[1].stats.PAIN = 12; ONLINE[1].parts["BPT7"].pain = 0')
    rt.execute("fire('OnTick')")
    c = rt.eval("TKX_Symptoms.c")
    assert c.pain == 12 and c.lvPain == 1 and c.part == 0 and c.cpart == 7 and c.n == 1
    assert rt.eval("TKX_Symptoms.cpartSet(8)") is True and rt.eval('TKX_Symptoms.cpartSet("x")') is False
    rt.execute('ONLINE[1].levels.M_PAIN = 2')
    rt.execute("fire('OnTick')")
    t = rt.eval("TKX_Symptoms.ctrk")
    assert t.lvPainMin == 1 and t.lvPainMax == 2 and t.n == 2
    rt.eval("TKX_Symptoms.creset()")
    assert rt.eval("TKX_Symptoms.ctrk.n") == 0
    assert rt.eval("TKX_Symptoms.version") == "1"


def test_client_file_adds_nothing_on_the_server():
    rt = host(server=True, client=False, files=(CLIENT,))
    assert len(rt.eval("Events.OnTick.fns")) == 0
