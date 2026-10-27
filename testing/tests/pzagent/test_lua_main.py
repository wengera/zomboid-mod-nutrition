"""PZAgent_Main.lua (Plan 22 Task 6): the one OnTick hook in the order player -> init -> poll -> skills -> sense -> map ->
flush, one flush a tick; hello with caps, the inventory's first sight, scan and rate answered by one act line (ruling
P22-5), the frame's cost group on the 1 ms clock, the overflow and lua_error events. Ports test_lua_act.py's main_*
cases (deleted at Task 4) to the PZA/1 shapes."""
import json

from agent.base import pza1
from .conftest import lua_file, make_player, make_cell, J

DIR = "pzagent/admin/"
LIVE = DIR + "state.log"
CMD = DIR + "cmd.txt"


def load(lua):
    """The client files in the game's load order (by name: Link, Main, Map, Motor, Sense, Skills), so Main reaches every
    other module only at tick time."""
    for f in ("client/PZAgent_Link.lua", "client/PZAgent_Main.lua", "client/PZAgent_Map.lua",
              "client/PZAgent_Motor.lua", "client/PZAgent_Sense.lua", "client/PZAgent_Skills.lua"):
        lua.execute(open(lua_file(f), encoding="utf-8").read())


def sq(x, y):
    return J(getX=lambda s: x, getY=lambda s: y, getZ=lambda s: 0)


def lines(fs):
    """Every line of the live file, decoded through the Python side of PZA/1 (a schema-invalid line raises)."""
    return [pza1.decode(json.loads(l)) for l in fs.files.get(LIVE, "").split("\n") if l.strip()]


def kinds(fs):
    return [l["kind"] for l in lines(fs)]


def cmd(fs, seq, typ, aid="a%d", **args):
    fs.files[CMD] = json.dumps({"seq": seq, "aid": aid % seq if "%d" in aid else aid, "type": typ, "args": args}) + "\n"


def live_writes(lua, fs):
    """Counts every writer opened, by file name, into the returned dict."""
    names = {}

    def writer(name, create, append):
        names[name] = names.get(name, 0) + 1
        return fs.writer(name, create, append)
    lua.globals().getFileWriter = writer
    return names


def setup(lua, fs, p=None, ticks=1):
    """Loaded, a player, and `ticks` handler calls (the first is the init tick)."""
    load(lua)
    g = lua.globals()
    player = p if p is not None else make_player()
    g.getPlayer = lambda: player
    for _ in range(ticks):
        g._handlers[0]()
    return g, player


def run(g, n=1):
    for _ in range(n):
        g._handlers[0]()


# ---- init: hello, the first sight, one flush ---------------------------------------------------------------------

def test_the_first_tick_with_a_player_writes_hello_the_first_sight_and_one_flush(lua, fs):
    load(lua)
    g = lua.globals()
    assert len(g._handlers) == 1
    p = make_player(items=("Base.Bread", "Base.Apple"))
    g.getPlayer = lambda: p
    names = live_writes(lua, fs)
    run(g)
    out = lines(fs)
    assert [l["kind"] for l in out] == ["hello", "event", "event"]
    hello = out[0]
    caps = sorted(lua.eval("PZA.schema.actions").keys())
    assert hello["proto"] == "PZA/1" and hello["mod"] == "1.0" and hello["user"] == "admin"
    assert hello["caps"] == caps and hello["rate"] == 10 and hello["mode"] == "append" and hello["build"] == ""
    assert sorted(list(lua.eval("PZA.skills.types").keys()) + ["rate", "scan"]) == caps
    assert [(e["event"], e["itemId"], e["fullType"]) for e in out[1:]] == [("item_added", 1000, "Base.Bread"),
                                                                           ("item_added", 1001, "Base.Apple")]
    assert names.get(LIVE) == 1 and lua.eval("PZA.main.ready") is True
    run(g)
    assert [l["kind"] for l in lines(fs)].count("hello") == 1


def test_a_tick_without_a_player_polls_and_writes_nothing(lua, fs):
    load(lua)
    g = lua.globals(); g.getPlayer = lambda: None
    cmd(fs, 1, "stop")
    run(g, 30)
    assert lua.eval("PZA.errors") == 0 and fs.opens == 0
    assert list(fs.files) == [CMD] and not lua.eval("PZA.main.ready")


def test_a_raise_before_init_counts_and_never_re_raises(lua, fs):
    load(lua)
    g = lua.globals(); g.getPlayer = lambda: (_ for _ in ()).throw(RuntimeError("boom"))
    run(g, 30)                                                  # a raise out of the handler would fail the test here
    assert lua.eval("PZA.errors") == 30 and fs.files == {} and fs.opens == 0


# ---- the frame and its cost --------------------------------------------------------------------------------------

def test_at_rate_10_a_positional_frame_every_6th_tick_with_the_previous_ticks_ms_and_the_running_act(lua, fs):
    load(lua)
    g = lua.globals()
    clock = g._clock
    p = make_player()
    g._cell = make_cell(squares={(13, 20, 0): sq(13, 20)})
    t = {"n": 0}

    def get_player():                                          # tick n's body costs n ms
        t["n"] += 1
        clock["ms"] += t["n"]
        return p
    g.getPlayer = get_player
    run(g)                                                      # tick 1: init
    cmd(fs, 1, "walkTo", x=13, y=20)
    run(g, 35)                                                  # ticks 2-36
    raw = [l for l in fs.files[LIVE].split("\n") if l.startswith('["frame"')]
    frames = [pza1.decode(json.loads(l)) for l in raw]
    assert [f["tick"] for f in frames] == [6, 12, 18, 24, 30, 36]
    assert [f["cost"]["tickMs"] for f in frames] == [5, 11, 17, 23, 29, 35]      # the previous tick's whole body
    assert frames[0]["cost"]["tickMaxMs"] == 5 and frames[0]["cost"]["over5"] == 1  # ticks 1-5 (tick 1 is the init)
    assert [f["cost"]["tickMaxMs"] for f in frames[1:]] == [11, 17, 23, 29, 35]    # ticks 6-11, 12-17, ...
    assert [f["cost"]["over5"] for f in frames[1:]] == [6] * 5
    assert frames[0]["act"] == {"aid": "a1", "state": "accepted"}
    assert all(f["cost"]["dropped"] == 0 for f in frames)


def test_each_cost_field_is_measured_at_its_own_phase(lua, fs):
    g, p = setup(lua, fs, ticks=5)                              # ticks 1-5; the frame comes on tick 6
    clock = g._clock
    lua.globals()._ms = lambda n: clock.__setitem__("ms", clock["ms"] + n)
    lua.execute("""
        local K, S, MP = PZA.skills, PZA.sense, PZA.map
        local tick, frame, events, watch = K.tick, S.frame, S.events, MP.watchStep
        K.tick = function(p) _ms(2); return tick(p) end
        S.frame = function(p) _ms(3); return frame(p) end
        S.events = function(p, prev) _ms(1); return events(p, prev) end
        MP.watchStep = function(p) _ms(4); return watch(p) end
    """)
    fs.write_cost_ms = 7
    run(g)                                                      # tick 6: the first frame (S.frame only: no prev)
    run(g, 4)                                                   # ticks 7-10
    lua.execute("PZA.emit('event', {event = 'lua_error', msg = 'y', gameMin = 0})")
    run(g)                                                      # tick 11 flushes it: 7 ms
    run(g)                                                      # tick 12: S.events (+1) reads S.frame (+3)
    frames = [l for l in lines(fs) if l["kind"] == "frame"]
    c1, c2 = frames[0]["cost"], frames[1]["cost"]
    assert (c1["actMs"], c1["senseMs"], c1["mapMs"]) == (2, 3, 4)
    assert (c2["actMs"], c2["senseMs"], c2["mapMs"]) == (2, 4, 4)
    assert c1["linkMs"] == 0                                    # tick 5 flushed nothing
    assert c2["linkMs"] == 7                                    # tick 11's flush
    assert c2["tickMs"] == 2 + 4 + 7                            # tick 11's whole body: act, map, its flush
    # tick 6's body: act 2, sense 3, map 4 and the frame's own flush 7, the worst of ticks 6-11
    assert c2["tickMaxMs"] == 2 + 3 + 4 + 7 and c2["over5"] == 6


def test_frame_link_ms_is_the_previous_ticks_flush(lua, fs):
    g, p = setup(lua, fs)
    fs.write_cost_ms = 3
    run(g, 5)                                                   # ticks 2-6: tick 5 flushed nothing; tick 6's frame
    run(g, 4)                                                   # ticks 7-10
    lua.execute("PZA.emit('event', {event = 'lua_error', msg = 'x', gameMin = 0})")
    run(g)                                                      # tick 11 flushes it: 3 ms
    run(g)                                                      # tick 12: the frame
    frames = [l for l in lines(fs) if l["kind"] == "frame"]
    assert [f["tick"] for f in frames] == [6, 12]
    assert frames[0]["cost"]["linkMs"] == 0 and frames[1]["cost"]["linkMs"] == 3


# ---- commands ----------------------------------------------------------------------------------------------------

def test_a_walk_to_is_acked_by_an_accepted_line_in_the_same_ticks_single_flush(lua, fs):
    g, p = setup(lua, fs)
    g._cell = make_cell(squares={(13, 20, 0): sq(13, 20)})
    names = live_writes(lua, fs)
    n0 = len(lines(fs))
    cmd(fs, 1, "walkTo", x=13, y=20)
    run(g)
    new = lines(fs)[n0:]
    assert [(l["kind"], l["aid"], l["state"]) for l in new] == [("act", "a1", "accepted")]
    assert names == {LIVE: 1, DIR + "ack.txt": 1}             # one flush; the poll's ack write is the Link's own


def test_a_dead_players_walk_to_is_rejected_dead(lua, fs):
    g, p = setup(lua, fs, p=make_player(health=0.0))
    g._cell = make_cell(squares={(13, 20, 0): sq(13, 20)})
    cmd(fs, 1, "walkTo", x=13, y=20)
    run(g)
    acts = [l for l in lines(fs) if l["kind"] == "act"]
    assert [(a["state"], a["reason"]) for a in acts] == [("rejected", "dead")]


def test_rate_60_is_answered_done_and_the_next_frame_is_full(lua, fs):
    g, p = setup(lua, fs, ticks=12)                             # frames on ticks 6 (full) and 12 (a delta)
    raw = [json.loads(l) for l in fs.files[LIVE].split("\n") if l.startswith('["frame"')]
    assert any(v is True for v in raw[1][6:13])                 # sanity: the second frame elides a group
    cmd(fs, 1, "rate", hz=60)
    run(g)                                                      # tick 13: answered; a frame every tick now
    acts = [l for l in lines(fs) if l["kind"] == "act"]
    assert len(acts) == 1
    a = acts[0]
    assert (a["aid"], a["type"], a["state"], a["reason"], a["result"]) == ("a1", "rate", "done", "", {"hz": 60})
    assert a["snapshot"]["me"]["x"] == 10.0
    assert lua.eval("PZA.sense.RATE") == 60 and lua.eval("PZA.skills.cur") is None
    raw = [json.loads(l) for l in fs.files[LIVE].split("\n") if l.startswith('["frame"')]
    assert raw[-1][2] == 13 and not any(v is True for v in raw[-1])    # tick 13's frame, full
    run(g)
    raw2 = [json.loads(l) for l in fs.files[LIVE].split("\n") if l.startswith('["frame"')]
    assert len(raw2) == len(raw) + 1


def test_bad_rate_and_scan_args_are_rejected_bad_args(lua, fs):
    g, p = setup(lua, fs)
    for seq, (typ, args) in enumerate([("rate", {"hz": 0}), ("rate", {"hz": 61}), ("rate", {"hz": "x"}),
                                       ("rate", {}), ("scan", {"r": 0}), ("scan", {"r": 31}), ("scan", {"r": "5"}),
                                       ("rate", {"hz": 7.5}), ("scan", {"r": 2.5})], start=1):
        cmd(fs, seq, typ, **args)
        run(g)
    acts = [l for l in lines(fs) if l["kind"] == "act"]
    assert [(a["state"], a["reason"]) for a in acts] == [("rejected", "bad args")] * 9
    assert all(a["snapshot"] is not None for a in acts)
    assert lua.eval("PZA.sense.RATE") == 10 and lua.eval("PZA.map.job") is None


def scan_world(lua, cx, cy, r):
    """Every square of the (2r+1)^2 grid around (cx, cy) exists, with only its position."""
    squares = {(x, y, 0): sq(x, y) for x in range(cx - r, cx + r + 1) for y in range(cy - r, cy + r + 1)}
    lua.globals()._cell = J(getZombieList=lambda s: J(size=lambda s2: 0, get=lambda s2, i: None),
                            getGridSquare=lambda s, x, y, z: squares.get((int(x), int(y), int(z))))


def test_scan_15_is_answered_done_and_49_map_lines_follow_under_the_budget(lua, fs):
    g, p = setup(lua, fs)
    scan_world(lua, 10, 20, 15)
    budget = lua.eval("PZA.link.BUDGET_BYTES")
    cmd(fs, 1, "scan", r=15)
    per_tick = []
    for i in range(70):
        before = fs.files[LIVE]
        run(g)
        new = fs.files[LIVE][len(before):]
        maps = [l for l in new.split("\n") if l.startswith('["map"')]
        per_tick.append(maps)
        if i == 0:
            acts = [l for l in lines(fs) if l["kind"] == "act"]
            assert len(acts) == 1 and acts[0]["state"] == "done" and acts[0]["result"] == {"queued": 49}
            assert acts[0]["type"] == "scan"
    assert all(sum(len(m) for m in maps) <= budget or len(maps) == 1 for maps in per_tick)
    parts = [pza1.decode(json.loads(m)) for maps in per_tick for m in maps]
    full = [m for m in parts if m["mode"] == "full"]
    assert len(full) == 49 and [m["part"] for m in full] == list(range(1, 50)) and {m["scanId"] for m in full} == {1}
    assert sum(len(m["squares"]) for m in full) == 961
    assert lua.eval("PZA.map.job") is None


def test_a_second_scan_replaces_a_running_one_and_its_parts_stop(lua, fs):
    g, p = setup(lua, fs)
    scan_world(lua, 10, 20, 15)
    cmd(fs, 1, "scan", r=15)
    run(g, 3)
    cmd(fs, 2, "scan", r=1)
    run(g, 30)
    full = [l for l in lines(fs) if l["kind"] == "map" and l["mode"] == "full"]
    assert [(m["scanId"], m["part"], m["parts"]) for m in full] == [(1, 1, 49), (1, 2, 49), (1, 3, 49), (2, 1, 1)]
    assert len(full[-1]["squares"]) == 9


def test_one_flush_a_tick_over_100_ticks_with_a_scan_running(lua, fs):
    g, p = setup(lua, fs)
    scan_world(lua, 10, 20, 15)
    cmd(fs, 1, "scan", r=15)
    run(g)                                                      # the command's tick (its ack write is the Link's poll)
    for _ in range(100):
        o0 = fs.opens
        run(g)
        assert fs.opens - o0 <= 1


def test_the_watch_runs_when_no_scan_job_does(lua, fs):
    g, p = setup(lua, fs)
    scan_world(lua, 10, 20, 6)
    run(g)                                                      # tick 2: the watch's first 8 squares, never seen
    deltas = [l for l in lines(fs) if l["kind"] == "map"]
    assert [(m["mode"], m["scanId"], len(m["squares"])) for m in deltas] == [("delta", 0, 1)] * 8
    assert lua.eval("PZA.map.watchIdx") == 8


# ---- overflow and lua_error --------------------------------------------------------------------------------------

def test_an_overflow_is_one_event_and_is_cleared(lua, fs):
    g, p = setup(lua, fs)
    lua.execute("PZA.link.overflow = { queued = 400, cut = 3 }")
    run(g, 3)
    ev = [l for l in lines(fs) if l["kind"] == "event" and l["event"] == "overflow"]
    assert len(ev) == 1 and (ev[0]["queued"], ev[0]["cut"], ev[0]["gameMin"]) == (400, 3, 450)
    assert lua.eval("PZA.link.overflow") is None


def test_a_raise_in_the_body_counts_and_emits_lua_error_once_a_second(lua, fs):
    g, p = setup(lua, fs)
    clock = g._clock
    g.getPlayer = lambda: (_ for _ in ()).throw(RuntimeError("boom"))
    run(g, 30)                                                  # a raise out of the handler would fail the test here
    assert lua.eval("PZA.errors") == 30
    errs = [l for l in lines(fs) if l["kind"] == "event" and l["event"] == "lua_error"]
    assert len(errs) == 1 and "boom" in errs[0]["msg"] and errs[0]["gameMin"] == 450
    clock["ms"] += 999
    run(g)
    assert len([l for l in lines(fs) if l["kind"] == "event" and l["event"] == "lua_error"]) == 1
    clock["ms"] += 1
    run(g)
    assert len([l for l in lines(fs) if l["kind"] == "event" and l["event"] == "lua_error"]) == 2
    g.getPlayer = lambda: p
    run(g, 12)
    assert lua.eval("PZA.errors") == 32 and "frame" in kinds(fs)


def test_main_is_lf_and_names_no_removed_api():
    src = open(lua_file("client/PZAgent_Main.lua"), "rb").read()
    assert b"\r\n" not in src
    for gone in (b"PZA.act", b"link.ack", b"scanPart", b"goalEvent", b"local function config"):
        assert gone not in src
