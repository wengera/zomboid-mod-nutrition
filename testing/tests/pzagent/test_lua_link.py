"""The Link (PZAgent_Link.lua, Plan 22 Task 2): keyed lines through PZA.emit, positional frames through PZA.emitFrame
(a full frame every L.FULL_EVERY, else unchanged groups elided as true), map parts through L.queueMap into a bounded
backlog drained under L.BUDGET_BYTES, one file write a flush, and cmd.txt and ack.txt as one JSON line each."""
import copy
import json

from agent.base import pza1
from .conftest import lua_file
from .test_pza1 import lua_lit

DIR = "pzagent/admin/"
LIVE = DIR + "state.log"


def load(lua, user="admin"):
    lua.execute(open(lua_file("client/PZAgent_Link.lua"), encoding="utf-8").read())
    lua.globals().PZA.tick = 0
    if user is not None:
        lua.execute("PZA.link.init('%s')" % user)


def raw(fs, name=LIVE):
    return [l for l in fs.files.get(name, "").split("\n") if l.strip()]


def lines(fs, name=LIVE):
    return [json.loads(l) for l in raw(fs, name)]


def frame_body(x=10.5, stats_hunger=0.25, **over):
    """A full frame body (every field of the schema's order but the envelope)."""
    b = {"gameMin": 4321.25, "worldAge": 31.5,
         "me": {"x": x, "y": -20.125, "z": 0, "dir": "N", "pace": 3.5, "moving": True, "running": False,
                "sprinting": False, "forceRun": False, "forceSprint": False, "autoWalk": False, "zombiesSeen": 0,
                "zombiesListed": 0, "hour": 13.5, "attackers": 1, "hitReaction": "", "dragDown": False,
                "aiming": True, "forceAim": True, "worn": [{"loc": "base:tshirt", "bite": 0, "scratch": 10.5}]},
         "stats": {"hunger": stats_hunger, "thirst": 0.5, "fatigue": 0.125, "endurance": 0.75, "panic": 0, "pain": 0,
                   "sickness": 0, "wetness": 5, "temperature": 37},
         "body": {"health": 100, "bleeding": 0, "scratched": 0, "bitten": 0, "parts": []},
         "load": {"weight": 4.5, "max": 8, "level": 0, "n": 3},
         "weapon": None,
         "action": None,
         "act": None,
         "zombies": [],
         "cost": {"tickMs": 0.5, "actMs": 0, "senseMs": 0.25, "mapMs": 0, "linkMs": 0, "tickMaxMs": 1, "over5": 0,
                  "dropped": 0, "pollMs": 0, "startMs": 0, "maxActMs": 0, "maxSenseMs": 0.25, "maxMapMs": 0,
                  "maxLinkMs": 0, "maxPollMs": 0, "maxStartMs": 0}}
    b.update(over)
    return b


def emit_frame(lua, body):
    lua.execute("_body = " + lua_lit(body))
    lua.execute("PZA.emitFrame(_body)")


def queue_map(lua, body):
    lua.execute("_mbody = " + lua_lit(body))
    lua.execute("PZA.link.queueMap(_mbody)")


def map_body(squares=(), missing=(), scan=1, part=1, parts=1):
    return {"mode": "full", "scanId": scan, "part": part, "parts": parts, "squares": list(squares),
            "missing": list(missing)}


def group_at(arr, g):
    return arr[pza1.ORDER["frame"].index(g)]


# ---- what holds from the old Link: append, chunk, rotation, the new segment ---------------------------------------

def test_append_mode_emits_keyed_lines_with_the_envelope(lua, fs):
    load(lua)
    assert lua.eval("PZA.link.mode") == "append"
    lua.execute("PZA.emit('event', {event='door', gameMin=1.5}); PZA.emit('event', {event='door', gameMin=2})")
    lua.execute("PZA.link.flush()")
    lua.execute("PZA.emit('event', {event='door', gameMin=3}); PZA.link.flush()")
    got = lines(fs)
    assert [g["seq"] for g in got] == [1, 2, 3]
    assert got[0] == {"kind": "event", "seq": 1, "tick": 0, "wallMs": 1000, "event": "door", "gameMin": 1.5}
    assert lua.eval("PZA.link.ack") is None                 # ruling S-5: no ack kind in PZA/1


def test_chunk_mode_when_append_fails(lua, fs):
    fs.append_works = False
    load(lua)
    assert lua.eval("PZA.link.mode") == "chunk"
    emit_frame(lua, frame_body(x=1))
    lua.execute("PZA.link.flush()")
    emit_frame(lua, frame_body(x=2))
    lua.execute("PZA.link.flush()")
    assert group_at(lines(fs, DIR + "state-000001.log")[0], "me")[0] == 1
    assert group_at(lines(fs, DIR + "state-000002.log")[0], "me")[0] == 2


def test_rotate_past_limit(lua, fs):
    load(lua)
    lua.execute("PZA.link.ROTATE_BYTES = 40")
    opens = fs.opens
    lua.execute("for i = 1, 5 do PZA.emit('event', {event='door', x=i}); PZA.link.flush() end")
    assert fs.opens - opens == 5
    assert LIVE in fs.files and DIR + "state.1.log" in fs.files
    assert json.loads(raw(fs)[0])["seq"] == 1
    total = sum(len(lines(fs, n)) for n in fs.files if n.startswith(DIR + "state"))
    assert total == 5


def test_init_starts_a_new_segment_when_state_log_exists(lua, fs):
    fs.files[LIVE] = '{"seq":1}\n'
    fs.files[DIR + "state.1.log"] = '{"seq":2}\n'
    load(lua)
    assert lua.eval("PZA.link.live") == "state.2.log"
    lua.execute("PZA.emit('event', {event='door'}); PZA.link.flush()")
    assert len(lines(fs, DIR + "state.2.log")) == 1
    assert fs.files[LIVE] == '{"seq":1}\n'


def test_an_empty_flush_opens_nothing(lua, fs):
    load(lua)
    opens = fs.opens
    assert lua.eval("PZA.link.flush()") == 0
    assert fs.opens == opens


# ---- one flush a tick: the immediate buffer, then the map backlog under the budget --------------------------------

def test_a_tick_writes_one_file_open_frame_then_act_then_map(lua, fs):
    load(lua)
    assert lua.eval("PZA.link.BUDGET_BYTES") == 1536
    assert lua.eval("PZA.link.BACKLOG_MAX") == 400
    assert lua.eval("PZA.link.FULL_EVERY") == 10
    for i in range(3):
        queue_map(lua, map_body(part=i + 1, parts=3))
    emit_frame(lua, frame_body())
    lua.execute("PZA.emit('act', {aid='a1', type='walkTo', state='accepted'})")
    opens = fs.opens
    lua.execute("PZA.link.flush()")
    assert fs.opens - opens == 1
    out = raw(fs)
    assert len(out) == 5
    assert out[0].startswith('["frame"')
    assert json.loads(out[1])["kind"] == "act"
    assert all(l.startswith('["map"') for l in out[2:])
    # the map parts in queue order, queued before the frame yet stamped at the flush: seq rises in file order (S-11)
    assert [json.loads(l)[pza1.ORDER["map"].index("part")] for l in out[2:]] == [1, 2, 3]
    assert [file_seq(l) for l in out] == [1, 2, 3, 4, 5]
    assert lua.eval("#PZA.link.buf") == 0 and lua.eval("#PZA.link.backlog") == 0


def file_seq(line):
    v = json.loads(line)
    return v["seq"] if isinstance(v, dict) else v[1]


def test_seq_rises_by_one_line_by_line_over_ticks_with_a_deferred_backlog(lua, fs):
    load(lua)
    for i in range(10):
        queue_map(lua, padded_map(1, 600))                      # 600 bytes: two parts a tick under the budget
    for tick in range(4):
        lua.globals().PZA.tick = tick
        emit_frame(lua, frame_body(x=float(tick)))
        lua.execute("PZA.emit('event', {event='door', gameMin=%d})" % tick)
        lua.execute("PZA.link.flush()")
    out = raw(fs)
    assert sum(1 for l in out if l.startswith('["map"')) == 8 and lua.eval("#PZA.link.backlog") == 2
    seqs = [file_seq(l) for l in out]
    assert seqs == list(range(1, len(out) + 1))
    assert lua.eval("PZA.link.seq") == len(out)                 # a part left over gave its seq back


def test_flush_returns_the_ms_its_write_took(lua, fs):
    load(lua)
    fs.write_cost_ms = 3
    lua.execute("PZA.emit('event', {event='door'})")
    assert lua.eval("PZA.link.flush()") == 3


def padded_map(seq, size):
    """A map body whose line is exactly `size` bytes once stamped with seq, tick 0 and wallMs 1000."""
    body = map_body(missing=[""])
    base = dict(body, kind="map", seq=seq, tick=0, wallMs=1000)
    n = len(pza1.encode("map", base))
    body["missing"] = ["p" * (size - n)]
    assert len(pza1.encode("map", dict(base, missing=body["missing"]))) == size
    return body


def test_a_backlog_of_ten_400_byte_lines_drains_three_a_tick(lua, fs):
    load(lua)
    lua.execute("PZA.link.seq = 100")                         # seqs 101..110: every line the same width
    for i in range(10):
        queue_map(lua, padded_map(101 + i, 400))
    drained = []
    for tick in range(5):
        before = len(raw(fs))
        opens = fs.opens
        lua.execute("PZA.link.flush()")
        assert fs.opens - opens == (1 if tick < 4 else 0)
        drained.append(len(raw(fs)) - before)
    assert drained == [3, 3, 3, 1, 0]                         # 1200 <= 1536 < 1600
    assert all(len(l) == 400 for l in raw(fs))
    assert [json.loads(l)[1] for l in raw(fs)] == list(range(101, 111))


def test_an_oversize_map_line_goes_alone(lua, fs):
    load(lua)
    queue_map(lua, map_body(missing=["q" * 2000]))
    queue_map(lua, map_body())
    lua.execute("PZA.link.flush()")
    assert len(raw(fs)) == 1 and len(raw(fs)[0]) > 1536
    lua.execute("PZA.link.flush()")
    assert len(raw(fs)) == 2


def test_the_immediate_buffer_is_never_held_back_by_the_budget(lua, fs):
    load(lua)
    for i in range(6):
        lua.execute("PZA.emit('event', {event='lua_error', msg=string.rep('e', 400)})")
    queue_map(lua, map_body())
    lua.execute("PZA.link.flush()")
    out = raw(fs)
    assert len(out) == 7 and out[-1].startswith('["map"')


def test_401_queued_lines_cut_the_oldest_and_set_overflow(lua, fs):
    load(lua)
    for i in range(401):
        queue_map(lua, map_body(part=i + 1, parts=401))
    assert lua.eval("#PZA.link.backlog") == 400
    o = lua.eval("PZA.link.overflow")
    assert (o["queued"], o["cut"]) == (400, 1)
    assert lua.eval("PZA.link.backlog[1].part") == 2           # the oldest went
    assert lua.eval("PZA.link.backlog[1].seq") is None         # stored unstamped (S-11)
    queue_map(lua, map_body(part=402, parts=402))
    o = lua.eval("PZA.link.overflow")
    assert (o["queued"], o["cut"]) == (400, 2)                # cut accumulates until Main clears it
    lua.execute("PZA.link.overflow = nil")
    queue_map(lua, map_body(part=403, parts=403))
    o = lua.eval("PZA.link.overflow")
    assert (o["queued"], o["cut"]) == (400, 1)


# ---- frames: full every FULL_EVERY, else unchanged groups elided ---------------------------------------------------

def test_frames_elide_unchanged_groups_and_go_full_every_ten(lua, fs):
    load(lua)
    for i in range(1, 12):
        emit_frame(lua, frame_body(x=float(i), zombies=[]))
        lua.execute("PZA.link.flush()")
    out = [json.loads(l) for l in raw(fs)]
    assert len(out) == 11 and lua.eval("PZA.link.frames") == 11
    for n, arr in enumerate(out, start=1):
        assert group_at(arr, "me")[0] == n                   # the changed group is always written
        assert group_at(arr, "zombies") == []                # zombies never elided
        full = n in (1, 11)
        for g in ("stats", "body", "load", "weapon", "action", "act", "cost"):
            if full:
                assert group_at(arr, g) is not True, (n, g)
            else:
                assert group_at(arr, g) is True, (n, g)
    assert group_at(out[0], "weapon") is None and group_at(out[10], "weapon") is None


def test_a_changed_group_is_written_and_becomes_the_base(lua, fs):
    load(lua)
    emit_frame(lua, frame_body(stats_hunger=0.25))
    emit_frame(lua, frame_body(stats_hunger=0.5))
    emit_frame(lua, frame_body(stats_hunger=0.5))
    emit_frame(lua, frame_body(stats_hunger=0.25))
    lua.execute("PZA.link.flush()")
    out = [json.loads(l) for l in raw(fs)]
    assert group_at(out[1], "stats")[0] == 0.5
    assert group_at(out[2], "stats") is True                  # the base is the last sent encoding
    assert group_at(out[3], "stats")[0] == 0.25


def test_force_full_makes_the_next_frame_full(lua, fs):
    load(lua)
    emit_frame(lua, frame_body())
    emit_frame(lua, frame_body())
    lua.execute("PZA.link.forceFull = true")
    emit_frame(lua, frame_body())
    emit_frame(lua, frame_body())
    lua.execute("PZA.link.flush()")
    out = [json.loads(l) for l in raw(fs)]
    assert [group_at(a, "stats") is True for a in out] == [False, True, False, True]
    assert lua.eval("PZA.link.forceFull") is False


def test_init_resets_the_frame_count_so_the_next_frame_is_full(lua, fs):
    load(lua)
    emit_frame(lua, frame_body())
    emit_frame(lua, frame_body())
    lua.execute("PZA.link.flush(); PZA.link.init('admin')")
    emit_frame(lua, frame_body())
    lua.execute("PZA.link.flush()")
    out = [json.loads(l) for l in raw(fs, DIR + "state.1.log")]
    assert group_at(out[0], "stats") is not True and lua.eval("PZA.link.frames") == 1


# ---- the failed write ---------------------------------------------------------------------------------------------

def test_a_failed_write_requeues_and_the_next_flush_writes_everything_once(lua, fs):
    load(lua)
    emit_frame(lua, frame_body())
    lua.execute("PZA.emit('act', {aid='a1', type='stop', state='done'})")
    queue_map(lua, map_body())
    fs.fail_next = True
    lua.execute("PZA.link.flush()")
    assert raw(fs) == []
    assert lua.eval("#PZA.link.buf") == 2 and lua.eval("#PZA.link.backlog") == 1
    lua.execute("PZA.link.flush()")
    out = raw(fs)
    assert len(out) == 3 and out[0].startswith('["frame"') and out[2].startswith('["map"')
    assert [file_seq(l) for l in out] == [1, 2, 3]            # the failed flush gave the part's seq back
    lua.execute("PZA.link.flush()")
    assert len(raw(fs)) == 3


def test_a_failed_write_caps_the_buffer_and_counts_the_cut(lua, fs):
    load(lua)
    lua.execute("for i = 1, 2001 do PZA.emit('event', {event='door', i=i}) end")
    fs.fail_next = True
    lua.execute("PZA.link.flush()")
    assert lua.eval("#PZA.link.buf") == 2000 and lua.eval("PZA.link.dropped") == 1
    lua.execute("PZA.link.flush()")
    assert lines(fs)[0]["i"] == 2


def test_a_cut_line_forces_the_next_frame_full(lua, fs):
    load(lua)
    emit_frame(lua, frame_body())
    lua.execute("PZA.link.flush()")
    emit_frame(lua, frame_body())                              # a delta, its base the frame above
    lua.execute("PZA.link.BUF_MAX = 1")
    fs.fail_next = True
    lua.execute("PZA.emit('event', {event='door'}); PZA.link.flush()")
    assert lua.eval("PZA.link.dropped") == 1 and lua.eval("PZA.link.forceFull") is True
    emit_frame(lua, frame_body())
    lua.execute("PZA.link.flush()")
    out = raw(fs)
    assert len(out) == 3 and group_at(json.loads(out[2]), "stats") is not True     # full again


# ---- cmd.txt and ack.txt, one JSON line each ----------------------------------------------------------------------

def test_poll_reads_json_acks_and_accepts_each_seq_once(lua, fs):
    load(lua)
    assert lua.eval("PZA.link.poll()") is None                # no cmd.txt
    fs.files[DIR + "cmd.txt"] = '{"seq":1,"aid":"a1","type":"walkTo","args":{"x":3,"y":4.5,"gait":"run"}}\n'
    c = lua.eval("PZA.link.poll()")
    assert (c["seq"], c["aid"], c["type"]) == (1, "a1", "walkTo")
    assert (c["args"]["x"], c["args"]["y"], c["args"]["gait"]) == (3, 4.5, "run")
    assert json.loads(fs.files[DIR + "ack.txt"]) == {"seq": 1}
    assert lua.eval("PZA.link.poll()") is None                # the same seq
    fs.files[DIR + "cmd.txt"] = '{"seq":0,"aid":"a0","type":"stop","args":{}}\n'
    assert lua.eval("PZA.link.poll()") is None                # below lastCmd
    fs.files[DIR + "cmd.txt"] = '\n{"seq":2,"aid":"a2","type":"stop"}\n'
    c = lua.eval("PZA.link.poll()")
    assert c["seq"] == 2 and c["type"] == "stop" and len(list(c["args"].keys())) == 0
    assert json.loads(fs.files[DIR + "ack.txt"]) == {"seq": 2}
    assert lua.eval("PZA.link.badCmd") == 0


def test_a_malformed_cmd_txt_is_skipped_and_counted_once(lua, fs):
    load(lua)
    for bad in ('{"seq":1,"aid":', "seq=1", '{"aid":"a1"}', '["seq",1]', '{"seq":"1"}'):
        fs.files[DIR + "cmd.txt"] = bad + "\n"
        n = lua.eval("PZA.link.badCmd")
        assert lua.eval("PZA.link.poll()") is None, bad
        assert lua.eval("PZA.link.poll()") is None, bad          # polled again: the same bad line counts once
        assert lua.eval("PZA.link.badCmd") == n + 1, bad
    assert DIR + "ack.txt" not in fs.files
    fs.files[DIR + "cmd.txt"] = '{"seq":1,"aid":"a1","type":"stop","args":{}}'
    assert lua.eval("PZA.link.poll()")["seq"] == 1


def test_a_bad_line_counts_again_after_a_good_one(lua, fs):
    load(lua)
    bad, good = '{"seq":', '{"seq":1,"aid":"a1","type":"stop","args":{}}'
    for line in (bad, good, bad):
        fs.files[DIR + "cmd.txt"] = line + "\n"
        lua.eval("PZA.link.poll()")
    assert lua.eval("PZA.link.badCmd") == 2


def test_a_non_finite_or_fractional_seq_is_a_bad_command(lua, fs):
    load(lua)
    for line in ('{"seq":1e999,"aid":"a1","type":"stop","args":{}}', '{"seq":-1e999,"aid":"a1","type":"stop"}',
                 '{"seq":2.5,"aid":"a1","type":"stop","args":{}}'):
        fs.files[DIR + "cmd.txt"] = line + "\n"
        assert lua.eval("PZA.link.poll()") is None, line
    assert lua.eval("PZA.link.badCmd") == 3 and lua.eval("PZA.link.lastCmd") == 0
    assert DIR + "ack.txt" not in fs.files


def test_last_cmd_recovered_from_ack_after_reset(lua, fs):
    fs.files[DIR + "ack.txt"] = '{"seq":7}\n'
    fs.files[DIR + "cmd.txt"] = '{"seq":7,"aid":"a7","type":"stop","args":{}}\n'
    load(lua)
    assert lua.eval("PZA.link.lastCmd") == 7
    assert lua.eval("PZA.link.poll()") is None
    fs.files[DIR + "cmd.txt"] = '{"seq":8,"aid":"a8","type":"stop","args":{}}\n'
    assert lua.eval("PZA.link.poll()")["seq"] == 8


def test_a_malformed_ack_txt_starts_from_zero(lua, fs):
    fs.files[DIR + "ack.txt"] = "seq=7\n"
    load(lua)
    assert lua.eval("PZA.link.lastCmd") == 0


# ---- one schema, two hosts (ruling S-3) ---------------------------------------------------------------------------

def test_a_frame_and_its_delta_decode_through_pza1(lua, fs):
    load(lua)
    lua.globals().PZA.tick = 42
    f1 = frame_body(x=10.5)
    f1["load"] = {"weight": 19.555, "max": 12, "level": 3, "n": 37}
    f1["weapon"] = None
    f1["action"] = {"class": 'IS"Walk\\Toé', "n": 2}
    f1["act"] = {"aid": "a3", "state": "progress"}
    f1["zombies"] = [{"id": 11, "x": 12.5, "y": 13.0, "dist": 2.5, "hasTarget": True, "crawler": False, "health": 0.75},
                     {"id": 12, "x": 14.25, "y": 9, "dist": 4.0, "hasTarget": False, "crawler": True, "health": 1}]
    f2 = copy.deepcopy(f1)
    f2["me"]["x"] = 11.25
    f2["zombies"] = []
    emit_frame(lua, f1)
    lua.execute("PZA.link.flush()")
    emit_frame(lua, f2)
    lua.execute("PZA.link.flush()")
    out = raw(fs)
    d1 = pza1.decode(json.loads(out[0]))
    d2 = pza1.decode(json.loads(out[1]))
    assert d1 == dict(f1, kind="frame", seq=1, tick=42, wallMs=1000)
    assert d2["stats"] is pza1.SAME and d2["weapon"] is pza1.SAME and d2["me"]["x"] == 11.25
    assert pza1.merge_delta(d2, d1) == dict(f2, kind="frame", seq=2, tick=42, wallMs=1000)


def test_a_map_line_decodes_through_pza1(lua, fs):
    load(lua)
    m = map_body(scan=4, part=1, parts=2, missing=["getWindow"], squares=[
        {"x": 100, "y": 200, "z": 0, "solid": False, "solidTrans": False, "light": 0.75, "room": "kitchen",
         "building": 12, "door": {"open": False, "locked": True, "barricaded": False}, "window": None,
         "containers": [], "floor": [], "blockN": True, "blockW": False, "edgeN": True, "edgeW": False, "hopN": True,
         "hopW": False, "water": None},
        {"x": 101, "y": 200, "z": 0, "solid": False, "solidTrans": False, "light": 0.5, "room": "kitchen",
         "building": 12, "door": None, "window": None,
         "containers": [{"type": "fridge", "n": 2, "items": ["Base.Apple", "Base.WaterBottle"]}], "floor": ["Base.Plank"],
         "blockN": False, "blockW": True, "edgeN": False, "edgeW": True, "hopN": False, "hopW": True,
         "water": {"amount": 20.0, "tainted": False, "infinite": False}}])
    queue_map(lua, m)
    lua.execute("PZA.link.flush()")
    out = raw(fs)
    assert len(out) == 1 and out[0].startswith('["map"')
    assert pza1.decode(json.loads(out[0])) == dict(m, kind="map", seq=1, tick=0, wallMs=1000)


# ---- the poll every third tick (Plan 23 Task 5, P23-4) -----------------------------------------------------------

def count_reads(lua, fs):
    """Counts every getFileReader call (the fake FS's `opens` counts writers only); the returned list holds the names."""
    names = []

    def reader(name, create):
        names.append(name)
        return fs.reader(name, create)
    lua.globals().getFileReader = reader
    return names


def test_the_poll_opens_cmd_txt_on_every_third_tick_only(lua, fs):
    load(lua)
    assert lua.eval("PZA.link.POLL_EVERY") == 3
    fs.files[DIR + "cmd.txt"] = '{"seq":1,"aid":"a1","type":"stop","args":{}}\n'
    reads = count_reads(lua, fs)
    accepted = [t for t in range(1, 31) if lua.eval("PZA.link.poll(%d)" % t) is not None]
    assert len(reads) == 10 and set(reads) == {DIR + "cmd.txt"}
    assert accepted == [3]


def test_a_command_written_between_polls_is_read_at_the_next_poll_tick(lua, fs):
    load(lua)
    for t in (1, 2, 3):
        assert lua.eval("PZA.link.poll(%d)" % t) is None
    fs.files[DIR + "cmd.txt"] = '{"seq":1,"aid":"a1","type":"stop","args":{}}\n'      # written at tick 4
    got = [t for t in range(4, 8) if lua.eval("PZA.link.poll(%d)" % t) is not None]
    assert got == [6]
