"""The Transport seam and FileTransport (Plan 22 Task 8, spec § 8), and the fake mod's own round trips: every line the
fake mod writes decodes through the schema back to what it wrote; delta frames are merged into the running frame;
Plan 21's tailing cases (gaps, partial lines, chunks, malformed lines, stray names, superseded segments)."""
import builtins
import json
import os

from agent.base import pza1
from agent.base.transport import Transport
from agent.base.transport.files import FileTransport

from .fakemod import DEFAULT_FRAME, FakeMod

SQUARE = {"x": 100, "y": 200, "z": 0, "solid": False, "solidTrans": False, "light": 0.8, "room": "kitchen",
          "building": 7, "door": {"open": False, "locked": True, "barricaded": False}, "window": None,
          "containers": [{"type": "fridge", "n": 2, "items": ["Base.Milk", "Base.Cheese"]}], "floor": ["Base.Axe"],
          "blockN": False, "blockW": True, "edgeN": False, "edgeW": True, "hopN": False, "hopW": True,
          "water": None}


def pair(tmp_path, **kw):
    t = {"now": 1000.0}
    clock = lambda: t["now"]
    return FakeMod(str(tmp_path), clock=clock, **kw), FileTransport(str(tmp_path), clock=clock), t


# -- the fake mod's round trips --------------------------------------------------------------------------------------

def test_every_kind_round_trips_through_the_transport(tmp_path):
    m, tr, _ = pair(tmp_path)
    wrote = [
        m.hello(),
        m.frame(),
        m.frame(zombies=[{"id": 4, "x": 101.5, "y": 199.25, "dist": 1.6, "hasTarget": True, "crawler": False,
                          "health": 1.75}]),
        m.event("damage", tag="ZOMBIE", amount=0.25, side="client"),
        m.map_full([SQUARE], scan_id=3, missing=["getModData"]),
        m.map_delta(dict(SQUARE, solid=True)),
        m.act("a1", "done", "walkTo", result={"d": 0.5}),
        m.reply(4, {"ok": True}),
    ]
    got = tr.lines()
    assert [l["kind"] for l in got] == ["hello", "frame", "frame", "event", "map", "map", "act", "reply"]
    assert got == wrote
    assert tr.bad == 0 and tr.gaps == []
    assert all(pza1.SAME not in l.values() for l in got)


def test_the_fake_mod_writes_deltas_on_the_full_every_cadence(tmp_path):
    m, _, _ = pair(tmp_path, full_every=3)
    for i in range(7):
        m.frame(me=dict(DEFAULT_FRAME["me"], x=100.0 + (i % 2)))
    raws = [json.loads(s) for s in (tmp_path / "state.log").read_text().splitlines()]
    me_at = pza1.ORDER["frame"].index("me")
    stats_at = pza1.ORDER["frame"].index("stats")
    assert [r[stats_at] is True for r in raws] == [False, True, True, False, True, True, False]
    assert all(r[me_at] is not True for r in raws)          # me changes every frame
    m.force_full()
    m.frame()
    assert json.loads((tmp_path / "state.log").read_text().splitlines()[-1])[stats_at] is not True


def test_the_fake_mod_chunk_mode_writes_one_file_a_line(tmp_path):
    m, tr, _ = pair(tmp_path, chunk=True)
    m.hello(); m.frame()
    assert sorted(os.listdir(tmp_path)) == ["state-000001.log", "state-000002.log"]
    assert [l["kind"] for l in tr.lines()] == ["hello", "frame"]


def test_the_fake_mod_rejects_a_bad_command(tmp_path):
    m, tr, _ = pair(tmp_path)
    tr.send({"seq": 1, "aid": "a1", "type": "walkTo", "args": {"x": "far", "y": 2, "gait": "run"}})
    m.answer()
    tr.send({"seq": 2, "aid": "a2", "type": "fly", "args": {}})
    m.answer()
    tr.send({"seq": 3, "aid": "a3", "type": "scan", "args": {"r": 5}})
    m.answer({"scan": ["accepted", {"state": "failed", "reason": "not loaded"}]})
    got = [(l["aid"], l["state"], l["reason"]) for l in tr.lines()]
    assert got == [("a1", "rejected", "bad args"), ("a2", "rejected", "unknown type"),
                   ("a3", "accepted", ""), ("a3", "failed", "not loaded")]
    assert m.last_cmd["aid"] == "a3"


# -- positional and delta frames --------------------------------------------------------------------------------------

def test_a_positional_frame_decodes_to_the_keyed_dict(tmp_path):
    m, tr, _ = pair(tmp_path)
    m.frame(me=dict(DEFAULT_FRAME["me"], x=12.5))
    raw = json.loads((tmp_path / "state.log").read_text())
    assert isinstance(raw, list) and raw[0] == "frame"
    (f,) = tr.lines()
    assert f["me"]["x"] == 12.5 and f["stats"]["temperature"] == 37 and f["weapon"]["ammo"] is None
    assert set(f) == set(pza1.ORDER["frame"])


def test_a_delta_frame_is_filled_from_the_running_frame(tmp_path):
    m, tr, _ = pair(tmp_path)
    m.frame(stats=dict(DEFAULT_FRAME["stats"], hunger=0.3))
    m.frame(stats=dict(DEFAULT_FRAME["stats"], hunger=0.3), me=dict(DEFAULT_FRAME["me"], x=5.5))
    m.frame(stats=dict(DEFAULT_FRAME["stats"], hunger=0.3), me=dict(DEFAULT_FRAME["me"], x=5.5),
            load=dict(DEFAULT_FRAME["load"], n=13))
    stats_at = pza1.ORDER["frame"].index("stats")
    raws = [json.loads(s) for s in (tmp_path / "state.log").read_text().splitlines()]
    assert [r[stats_at] is True for r in raws] == [False, True, True]
    f1, f2, f3 = tr.lines()
    assert f2["stats"]["hunger"] == 0.3 and f2["me"]["x"] == 5.5
    assert f3["me"]["x"] == 5.5 and f3["load"]["n"] == 13 and f3["stats"] == f1["stats"]
    assert tr.bad == 0


def test_the_running_frame_carries_across_reads(tmp_path):
    m, tr, _ = pair(tmp_path)
    m.frame(stats=dict(DEFAULT_FRAME["stats"], thirst=0.6))
    tr.lines()
    m.frame(stats=dict(DEFAULT_FRAME["stats"], thirst=0.6))
    (f,) = tr.lines()
    assert f["stats"]["thirst"] == 0.6


def test_a_delta_before_any_full_frame_counts_bad_and_is_dropped(tmp_path):
    m, _, _ = pair(tmp_path)
    m.frame(); m.frame(); m.hello()
    tr = FileTransport(str(tmp_path))
    log = tmp_path / "state.log"
    lines = log.read_text().splitlines()
    log.write_text("\n".join(lines[1:]) + "\n")           # the full frame is gone
    got = tr.lines()
    assert [l["kind"] for l in got] == ["hello"]
    assert tr.bad == 1 and tr.gaps == [(1, 2)]


def test_a_full_frame_replaces_the_running_frame(tmp_path):
    m, tr, _ = pair(tmp_path, full_every=2)
    m.frame(stats=dict(DEFAULT_FRAME["stats"], pain=0.5))
    m.frame(stats=dict(DEFAULT_FRAME["stats"], pain=0.5))
    m.frame()                                               # full, pain back to 0
    m.frame()                                               # delta, stats elided
    got = tr.lines()
    assert [l["stats"]["pain"] for l in got] == [0.5, 0.5, 0, 0]


def test_a_returned_frame_is_a_copy_of_the_running_frame(tmp_path):
    m, tr, _ = pair(tmp_path)
    m.frame()
    (f1,) = tr.lines()
    f1["me"]["x"] = -1.0
    f1["body"]["parts"].append({"i": 0, "h": 1.0})
    m.frame()                                               # a delta, me and body elided
    (f2,) = tr.lines()
    assert f2["me"]["x"] == 100 and f2["body"]["parts"] == []


# -- tailing (Plan 21's cases) ----------------------------------------------------------------------------------------

def test_tail_in_order_with_gaps_and_partial(tmp_path):
    m, tr, _ = pair(tmp_path)
    m.hello(); m.frame()
    assert [l["seq"] for l in tr.lines()] == [1, 2]
    line = json.dumps({"aid": "a1", "kind": "act", "reason": "", "result": None, "seq": 3, "snapshot": None,
                       "state": "accepted", "tick": 1, "type": "walkTo", "wallMs": 5})
    m.raw(line[:20])
    assert tr.lines() == []
    m.raw(line[20:] + "\n")
    m.seq = 4
    m.frame()                                               # seq 5, a gap at 4
    assert [l["seq"] for l in tr.lines()] == [3, 5]
    assert tr.gaps == [(4, 5)]


def test_lines_come_back_in_seq_order_across_files(tmp_path):
    m, tr, _ = pair(tmp_path)
    m.hello(); m.frame(); m.frame(load=dict(DEFAULT_FRAME["load"], n=1))
    lines = (tmp_path / "state.log").read_text().splitlines()
    (tmp_path / "state.1.log").write_text(lines[2] + "\n")
    (tmp_path / "state.log").write_text("\n".join(lines[:2]) + "\n")
    got = tr.lines()
    assert [l["seq"] for l in got] == [1, 2, 3] and got[2]["load"]["n"] == 1


def test_chunk_files_read_in_number_order(tmp_path):
    m, tr, _ = pair(tmp_path, chunk=True)
    for i in range(12):
        m.frame(load=dict(DEFAULT_FRAME["load"], n=i))
    assert [l["load"]["n"] for l in tr.lines()] == list(range(12))
    assert tr.lines() == []


def test_malformed_line_is_skipped_and_counted(tmp_path):
    m, tr, _ = pair(tmp_path)
    m.hello()
    m.raw("not json\n")
    m.frame()
    assert [l["seq"] for l in tr.lines()] == [1, 2]
    assert tr.bad == 1


def test_an_unknown_kind_or_a_bad_shape_counts_bad_without_raising(tmp_path):
    m, tr, _ = pair(tmp_path)
    m.raw(json.dumps({"kind": "ack", "seq": 1, "tick": 0, "wallMs": 0}) + "\n")
    m.raw(json.dumps(["frame", 2, 0, 0]) + "\n")                      # wrong arity
    m.raw(json.dumps({"kind": "act", "seq": 3, "aid": "a1"}) + "\n")  # no envelope
    m.raw(json.dumps(["ack", 4]) + "\n")
    m.raw("[]\n")
    m.raw("7\n")
    m.raw('{"kind":"event","event":[1],"seq":1,"tick":0,"wallMs":0,"gameMin":0}\n')   # a TypeError in decode
    m.seq = 4
    m.hello()                                                         # a good line later in the same read
    assert [(l["kind"], l["seq"]) for l in tr.lines()] == [("hello", 5)]
    assert tr.bad == 7


def test_stray_state_file_names_are_ignored(tmp_path):
    m, tr, _ = pair(tmp_path)
    (tmp_path / "state.bak.log").write_text("garbage\n")
    (tmp_path / "state-x.log").write_text("garbage\n")
    m.hello()
    assert [l["seq"] for l in tr.lines()] == [1]
    assert tr.bad == 0


def test_superseded_segments_are_not_reopened(tmp_path, monkeypatch):
    m, tr, _ = pair(tmp_path)
    m.hello(); m.hello(); m.hello()
    lines = (tmp_path / "state.log").read_text().splitlines()
    for name, line in zip(["state.log", "state.1.log", "state.2.log"], lines):
        (tmp_path / name).write_text(line + "\n")
    assert [l["seq"] for l in tr.lines()] == [1, 2, 3]
    assert len(tr._done_chunks) == 2
    opened = []
    real = builtins.open
    monkeypatch.setattr(builtins, "open",
                        lambda p, *a, **k: (opened.append(os.path.basename(str(p))), real(p, *a, **k))[1])
    assert tr.lines() == []
    assert opened == ["state.2.log"]


# -- send --------------------------------------------------------------------------------------------------------

def test_send_writes_one_sorted_json_line_atomically(tmp_path):
    _, tr, _ = pair(tmp_path)
    tr.send({"type": "scan", "seq": 1, "args": {"r": 5}, "aid": "a1"})
    text = (tmp_path / "cmd.txt").read_text(encoding="utf-8")
    assert text == '{"aid": "a1", "args": {"r": 5}, "seq": 1, "type": "scan"}\n'
    assert not os.path.exists(tmp_path / "cmd.txt.tmp")
    assert tr.cmd_seq == 1
    tr.send({"seq": 2, "aid": "a2", "type": "stop", "args": {}})
    assert tr.cmd_seq == 2
    assert json.loads((tmp_path / "cmd.txt").read_text())["aid"] == "a2"


def test_send_refuses_a_bad_envelope_before_any_write(tmp_path):
    _, tr, _ = pair(tmp_path)
    for cmd in ({"seq": 1, "aid": "a1", "type": "stop"},
                {"seq": 1, "aid": "a1", "type": "stop", "args": {}, "extra": 1},
                {"seq": 0, "aid": "a1", "type": "stop", "args": {}}):
        try:
            tr.send(cmd)
            assert False, cmd
        except ValueError:
            pass
    assert not os.path.exists(tmp_path / "cmd.txt") and tr.cmd_seq == 0


def test_send_refuses_a_non_finite_number_before_any_write(tmp_path):
    _, tr, _ = pair(tmp_path)
    for x in (float("nan"), float("inf")):
        try:
            tr.send({"seq": 1, "aid": "a1", "type": "walkTo", "args": {"x": x, "y": 2, "gait": "walk"}})
            assert False, x
        except ValueError:
            pass
    assert not os.path.exists(tmp_path / "cmd.txt") and not os.path.exists(tmp_path / "cmd.txt.tmp")
    assert tr.cmd_seq == 0


CMD1 = {"type": "scan", "seq": 1, "args": {"r": 5}, "aid": "a1"}


def test_send_retries_the_replace_on_a_sharing_violation(tmp_path, monkeypatch):
    from agent.base.transport import files
    _, tr, _ = pair(tmp_path)
    real, calls, slept = os.replace, [], []

    def flaky(src, dst):
        calls.append(1)
        if len(calls) <= 2:
            raise PermissionError(5, "Access is denied")
        return real(src, dst)

    monkeypatch.setattr(files.os, "replace", flaky)
    monkeypatch.setattr(files.time, "sleep", slept.append)
    tr.send(CMD1)
    assert json.loads((tmp_path / "cmd.txt").read_text())["aid"] == "a1"
    assert tr.replace_retries == 2 and tr.cmd_seq == 1
    assert slept == [files.REPLACE_SLEEP_S] * 2


def test_send_raises_after_the_retries_run_out(tmp_path, monkeypatch):
    from agent.base.transport import files
    _, tr, _ = pair(tmp_path)
    calls = []

    def always(src, dst):
        calls.append(1)
        raise PermissionError(5, "Access is denied")

    monkeypatch.setattr(files.os, "replace", always)
    monkeypatch.setattr(files.time, "sleep", lambda s: None)
    try:
        tr.send(CMD1)
        assert False, "no raise"
    except PermissionError:
        pass
    assert len(calls) == files.REPLACE_TRIES
    assert tr.cmd_seq == 0 and tr.replace_retries == files.REPLACE_TRIES - 1


def test_send_without_a_collision_counts_no_retry(tmp_path, monkeypatch):
    from agent.base.transport import files
    _, tr, _ = pair(tmp_path)
    slept = []
    monkeypatch.setattr(files.time, "sleep", slept.append)
    tr.send(CMD1)
    assert tr.replace_retries == 0 and slept == []


def test_file_transport_satisfies_the_protocol(tmp_path):
    assert isinstance(FileTransport(str(tmp_path)), Transport)


# -- M8 (the whole-pass review): cmd_seq seeded from ack.txt -----------------------------------------------------------
# The Lua ignores every command whose seq is not above ack.txt's (PZAgent_Link.lua L255); a FileTransport on a state dir
# the driver did not clear starts above it, so its first command is not taken for an old one.

def test_cmd_seq_is_seeded_from_ack_txt(tmp_path):
    from agent.base.actions import Actions
    (tmp_path / "ack.txt").write_text('{"seq":40}\n', encoding="utf-8")
    tr = FileTransport(str(tmp_path))
    assert tr.cmd_seq == 40
    Actions(tr).send(pza1.Stop())
    assert json.loads((tmp_path / "cmd.txt").read_text(encoding="utf-8"))["seq"] >= 41


def test_a_bad_or_absent_ack_txt_seeds_zero(tmp_path):
    assert FileTransport(str(tmp_path)).cmd_seq == 0
    for i, text in enumerate(['{"seq":', '{"seq":"40"}', '[40]', '{"seq":true}', '{"seq":-3}', '\xff']):
        d = tmp_path / str(i)
        d.mkdir()
        (d / "ack.txt").write_text(text, encoding="latin-1")
        assert FileTransport(str(d)).cmd_seq == 0, text


def test_the_init_comments_share_one_column():
    """N2 (the whole-pass review): `self.bad`'s comment fell out of the column in the Task 18 fix."""
    import inspect
    src = inspect.getsource(FileTransport.__init__).splitlines()
    cols = {ln.index("  # ") for ln in src if ln.lstrip().startswith("self.") and "  # " in ln}
    assert len(cols) == 1, cols
