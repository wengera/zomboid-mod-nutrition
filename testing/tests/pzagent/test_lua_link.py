import json
from .conftest import lua_file


def load(lua):
    lua.execute(open(lua_file("client/PZAgent_Link.lua"), encoding="utf-8").read())
    lua.globals().PZA.tick = 0


def lines(fs, name):
    return [json.loads(l) for l in fs.files[name].split("\n") if l.strip()]


def test_append_mode_emits_lines_with_seq(lua, fs):
    load(lua)
    lua.execute("PZA.link.init('admin')")
    assert lua.eval("PZA.link.mode") == "append"
    lua.execute("PZA.emit('frame', {x=1.5}); PZA.emit('frame', {x=2}); PZA.link.flush()")
    lua.execute("PZA.emit('frame', {x=3}); PZA.link.flush()")
    got = lines(fs, "pzagent/admin/state.log")
    assert [g["seq"] for g in got] == [1, 2, 3]
    assert got[0]["kind"] == "frame" and got[0]["x"] == 1.5 and got[0]["wallMs"] == 1000


def test_chunk_mode_when_append_fails(lua, fs):
    fs.append_works = False
    load(lua)
    lua.execute("PZA.link.init('admin')")
    assert lua.eval("PZA.link.mode") == "chunk"
    lua.execute("PZA.emit('frame', {x=1}); PZA.link.flush(); PZA.emit('frame', {x=2}); PZA.link.flush()")
    assert lines(fs, "pzagent/admin/state-000001.log")[0]["x"] == 1
    assert lines(fs, "pzagent/admin/state-000002.log")[0]["x"] == 2


def test_rotate_past_limit(lua, fs):
    load(lua)
    lua.execute("PZA.link.init('admin'); PZA.link.ROTATE_BYTES = 40")
    opens = fs.opens
    lua.execute("for i = 1, 5 do PZA.emit('frame', {x=i}); PZA.link.flush() end")
    assert fs.opens - opens == 5
    assert "pzagent/admin/state.log" in fs.files and "pzagent/admin/state.1.log" in fs.files
    first = json.loads(fs.files["pzagent/admin/state.log"].split("\n")[0])
    assert first["seq"] == 1
    total = sum(len(lines(fs, n)) for n in fs.files if n.startswith("pzagent/admin/state"))
    assert total == 5


def test_init_starts_a_new_segment_when_state_log_exists(lua, fs):
    load(lua)
    fs.files["pzagent/admin/state.log"] = '{"seq":1}\n'
    fs.files["pzagent/admin/state.1.log"] = '{"seq":2}\n'
    lua.execute("PZA.link.init('admin')")
    assert lua.eval("PZA.link.live") == "state.2.log"
    lua.execute("PZA.emit('frame', {x=1}); PZA.link.flush()")
    assert len(lines(fs, "pzagent/admin/state.2.log")) == 1
    assert fs.files["pzagent/admin/state.log"] == '{"seq":1}\n'


def test_failed_write_keeps_the_batch(lua, fs):
    load(lua)
    lua.execute("PZA.link.init('admin')")
    lua.execute("PZA.emit('frame', {x=1})")
    fs.fail_next = True
    lua.execute("PZA.link.flush()")
    assert lua.eval("#PZA.link.buf") == 1
    lua.execute("PZA.link.flush()")
    got = lines(fs, "pzagent/admin/state.log")
    assert len(got) == 1 and got[0]["x"] == 1


def test_poll_accepts_each_seq_once_and_acks(lua, fs):
    load(lua)
    lua.execute("PZA.link.init('admin')")
    fs.files["pzagent/admin/cmd.txt"] = "seq=1\ngoal=goto\nargs=3 4\n"
    c = lua.eval("PZA.link.poll()")
    assert c["seq"] == 1 and c["goal"] == "goto" and c["args"] == "3 4"
    assert lua.eval("PZA.link.poll()") is None
    assert fs.files["pzagent/admin/ack.txt"] == "seq=1\n"
    lua.execute("PZA.link.ack(1, true, '')")
    lua.execute("PZA.link.flush()")
    assert lines(fs, "pzagent/admin/state.log")[-1] == {"kind": "ack", "seq": 1, "tick": 0, "wallMs": 1000,
                                                        "cmdSeq": 1, "ok": True, "reason": ""}


def test_last_cmd_recovered_from_ack_after_reset(lua, fs):
    load(lua)
    fs.files["pzagent/admin/ack.txt"] = "seq=7\n"
    fs.files["pzagent/admin/cmd.txt"] = "seq=7\ngoal=stop\nargs=\n"
    lua.execute("PZA.link.init('admin')")
    assert lua.eval("PZA.link.poll()") is None
