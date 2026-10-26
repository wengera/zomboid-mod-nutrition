import json, os
from agent.link import Link


class FakeMod:
    def __init__(self, d, chunk=False):
        self.d, self.chunk, self.seq, self.n = d, chunk, 0, 0
        os.makedirs(d, exist_ok=True)

    def line(self, kind, **body):
        self.seq += 1
        body.update(kind=kind, seq=self.seq, tick=self.seq * 12, wallMs=1000 + self.seq)
        s = json.dumps(body) + "\n"
        if self.chunk:
            self.n += 1
            open(os.path.join(self.d, "state-%06d.log" % self.n), "w").write(s)
        else:
            open(os.path.join(self.d, "state.log"), "a").write(s)

    def answer(self):
        kv = dict(l.split("=", 1) for l in open(os.path.join(self.d, "cmd.txt")).read().splitlines())
        self.line("ack", cmdSeq=int(kv["seq"]), ok=True, reason="")
        return kv


def test_tail_in_order_with_gaps_and_partial(tmp_path):
    m = FakeMod(str(tmp_path)); lk = Link(str(tmp_path))
    m.line("frame", x=1); m.line("frame", x=2)
    assert [l["seq"] for l in lk.lines()] == [1, 2]
    with open(tmp_path / "state.log", "a") as f: f.write('{"kind":"frame","seq":3')
    assert lk.lines() == []
    with open(tmp_path / "state.log", "a") as f: f.write(',"x":3}\n')
    m.seq = 4; m.line("frame", x=5)                      # seq 5, a gap at 4
    assert [l["seq"] for l in lk.lines()] == [3, 5]
    assert lk.gaps == [(4, 5)]


def test_chunk_files_read_in_number_order(tmp_path):
    m = FakeMod(str(tmp_path), chunk=True); lk = Link(str(tmp_path))
    for i in range(12): m.line("frame", x=i)
    assert [l["x"] for l in lk.lines()] == list(range(12))


def test_send_is_atomic_kv_and_ack_matches(tmp_path):
    m = FakeMod(str(tmp_path)); lk = Link(str(tmp_path))
    s = lk.send("goto", "3 4 run")
    assert s == 1 and not os.path.exists(tmp_path / "cmd.txt.tmp")
    assert m.answer() == {"seq": "1", "goal": "goto", "args": "3 4 run"}
    lk.lines()
    assert lk.ack_of(1)["ok"] is True and lk.ack_of(2) is None


def test_await_goal_done_and_timeout(tmp_path):
    m = FakeMod(str(tmp_path)); t = {"now": 0.0}
    lk = Link(str(tmp_path), clock=lambda: t["now"])
    s = lk.send("goto", "1 1")
    m.line("frame", goal={"seq": s, "name": "goto", "state": "running", "detail": ""})
    m.line("frame", goal={"seq": s, "name": "goto", "state": "done", "detail": "d=0.4"})
    g = lk.await_goal(s, timeout_s=5)
    assert g["state"] == "done"
    s2 = lk.send("goto", "9 9")
    def tick(): t["now"] += 1.0
    try:
        lk.await_goal(s2, timeout_s=3, poll_s=0, on_line=None, _sleep=lambda _: tick())
        assert False
    except TimeoutError as e:
        assert "goal 2" in str(e)


def test_await_goal_returns_a_done_frame_already_pumped(tmp_path):
    m = FakeMod(str(tmp_path)); lk = Link(str(tmp_path), clock=lambda: 0.0)
    s = lk.send("goto", "1 1")
    m.line("frame", goal={"seq": s, "name": "goto", "state": "done", "detail": ""})
    assert len(lk.lines()) == 1
    assert lk.await_goal(s, timeout_s=0, _sleep=lambda _: None)["state"] == "done"


def test_malformed_line_is_skipped_and_counted(tmp_path):
    m = FakeMod(str(tmp_path)); lk = Link(str(tmp_path))
    m.line("frame", x=1)
    with open(tmp_path / "state.log", "a") as f: f.write("not json\n")
    m.line("frame", x=2)
    assert [l["x"] for l in lk.lines()] == [1, 2]
    assert lk.bad == 1


def test_stray_state_file_names_are_ignored(tmp_path):
    m = FakeMod(str(tmp_path)); lk = Link(str(tmp_path))
    (tmp_path / "state.bak.log").write_text("garbage\n")
    (tmp_path / "state-x.log").write_text("garbage\n")
    m.line("frame", x=1)
    assert [l["x"] for l in lk.lines()] == [1]


def test_superseded_segments_are_not_reopened(tmp_path, monkeypatch):
    lk = Link(str(tmp_path))
    for i, name in enumerate(["state.log", "state.1.log", "state.2.log"], 1):
        (tmp_path / name).write_text(json.dumps({"kind": "frame", "seq": i}) + "\n")
    assert [l["seq"] for l in lk.lines()] == [1, 2, 3]
    assert len(lk._done_chunks) == 2
    import builtins
    opened = []
    real = builtins.open
    monkeypatch.setattr(builtins, "open", lambda p, *a, **k: (opened.append(os.path.basename(str(p))), real(p, *a, **k))[1])
    assert lk.lines() == []
    assert opened == ["state.2.log"]
