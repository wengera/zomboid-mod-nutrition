"""PZAgent_Bench.lua (Plan 22 probe X2): the emit arms the harness's bench.global times on the client, and the bench line
Main's init emits."""
import json
from .conftest import lua_file, make_player

NAMES = ("json", "jsonNoSort", "compact", "openWrite", "openWrite20", "openOnly", "heldOpen", "heldWrite", "heldClose",
         "poll", "concat")


def load(lua, files=("client/PZAgent_Link.lua", "client/PZAgent_Bench.lua")):
    for f in files:
        lua.execute(open(lua_file(f), encoding="utf-8").read())


def call(lua, name):
    return lua.eval("PZA.bench.%s()" % name)


def test_every_bench_arm_is_a_function_of_no_arguments(lua):
    load(lua)
    for name in NAMES:
        assert lua.eval("type(PZA.bench.%s)" % name) == "function", name


def test_json_is_the_part_of_20_squares_at_2_to_3_5_kb(lua):
    load(lua)
    s = call(lua, "json")
    assert 2000 <= len(s) <= 3500
    part = json.loads(s)
    sq = part["squares"]
    assert len(sq) == 20
    assert sum(1 for q in sq if isinstance(q["containers"], list) and len(q["containers"]) == 1
               and len(q["containers"][0]["items"]) == 3) == 2
    assert sum(1 for q in sq if "door" in q) == 1
    assert all({"x", "y", "z", "solid", "solidTrans", "light", "containers", "floor"} <= set(q) for q in sq)
    assert call(lua, "concat") == s


def test_no_sort_and_compact_parse_and_compact_is_20_positional_lists(lua):
    load(lua)
    assert json.loads(call(lua, "jsonNoSort")) == json.loads(call(lua, "json"))
    rows = json.loads(call(lua, "compact"))
    assert len(rows) == 20 and all(isinstance(r, list) and len(r) == 10 for r in rows)
    full = json.loads(call(lua, "json"))["squares"]
    for r, q in zip(rows, full):
        assert r[:6] == [q["x"], q["y"], q["z"], q["solid"], q["solidTrans"], q["light"]]
        assert r[6] == q.get("room") and r[7] == q.get("building")
    boxes = [r[8] for r in rows if r[8]]
    assert len(boxes) == 2 and all(len(b) == 1 and b[0][1] == 3 and len(b[0][2]) == 3 for b in boxes)


def test_open_write_opens_one_writer_per_call_and_appends_the_part(lua, fs):
    load(lua)
    lua.execute("PZA.link.init('admin')")
    s21 = call(lua, "json")
    opens = fs.opens
    call(lua, "openWrite")
    call(lua, "openWrite")
    assert fs.opens - opens == 2 and fs.files["pzagent/admin/bench.log"] == s21 * 2
    call(lua, "openWrite20")
    assert fs.files["pzagent/admin/bench.log"] == s21 * 2 + "0123456789abcdefghi\n"
    assert len("0123456789abcdefghi\n") == 20
    call(lua, "openOnly")
    assert fs.opens - opens == 4 and len(fs.files["pzagent/admin/bench.log"]) == 2 * len(s21) + 20


def test_the_bench_file_before_the_link_is_initialised(lua, fs):
    load(lua)
    call(lua, "openWrite")
    assert fs.files["pzagent/bench.log"] == call(lua, "json")


def test_a_held_writer_opens_once_and_appends_each_write(lua, fs):
    load(lua)
    lua.execute("PZA.link.init('admin')")
    s21 = call(lua, "json")
    opens = fs.opens
    call(lua, "heldOpen")
    for _ in range(3):
        call(lua, "heldWrite")
    call(lua, "heldClose")
    assert fs.opens - opens == 1 and fs.files["pzagent/admin/bench.log"] == s21 * 3
    assert lua.eval("PZA.bench.w") is None


def test_every_arm_tolerates_a_nil_writer(lua, fs):
    load(lua)
    lua.execute("PZA.link.init('admin')")
    call(lua, "heldWrite")                          # no held writer: a raise would fail the test here
    call(lua, "heldClose")
    fs.fail_next = True
    call(lua, "openWrite")
    fs.fail_next = True
    call(lua, "heldOpen")
    call(lua, "heldWrite")
    assert "pzagent/admin/bench.log" not in fs.files


def test_poll_reads_cmd_txt_through_the_file_reader(lua, fs):
    load(lua)
    lua.execute("PZA.link.init('admin')")
    reads = []
    real = fs.reader

    def reader(name, create):
        reads.append(name)
        return real(name, create)
    lua.globals().getFileReader = reader
    fs.files["pzagent/admin/cmd.txt"] = "seq=4\ngoal=stop\nargs=\n"
    t = call(lua, "poll")
    assert reads == ["pzagent/admin/cmd.txt"] and t["seq"] == "4"


def test_main_init_emits_the_bench_line_after_hello(lua, fs):
    load(lua, ("client/PZAgent_Act.lua", "client/PZAgent_Bench.lua", "client/PZAgent_Link.lua",
               "client/PZAgent_Main.lua", "client/PZAgent_Motor.lua", "client/PZAgent_Sense.lua"))
    lua.globals().getPlayer = lambda: make_player()
    lua.execute("PZA.main.init('admin')")
    lines = [json.loads(l) for l in fs.files["pzagent/admin/state.log"].splitlines()]
    assert [l["kind"] for l in lines] == ["hello", "bench"]
    b = lines[1]
    assert b["json21Bytes"] == len(call(lua, "json")) and b["compactBytes"] == len(call(lua, "compact"))
    assert b["noSortBytes"] == len(call(lua, "jsonNoSort")) and b["squares"] == 20
    assert lines[0]["modVersion"] == "0.2"


def test_a_second_held_open_closes_the_first_writer(lua, fs):
    load(lua)
    lua.execute("PZA.link.init('admin')")
    n = len(fs.writers)
    call(lua, "heldOpen")
    call(lua, "heldOpen")
    first, second = fs.writers[n:]
    assert first.closed is True and second.closed is False
    call(lua, "heldClose")
    assert second.closed is True
