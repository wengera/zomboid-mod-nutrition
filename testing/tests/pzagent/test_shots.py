"""agent/driverlib/shots.py (ruling P23-AL): the timestamped screenshots of the client window, offline.

The grabber and the window finder are injected: a fake `grab(bbox)` returning a 1920x1080 PIL image (or raising), a
fake `find(pid)` returning a rect or None. `run_due()` is the worker's one pass, called on the test's thread so the
fake clock stays single-threaded; one test runs the real worker thread and joins it. The session-level tests reuse
test_driverlib's run_session (DayMod on a fake clock) with an inline ShotTaker attached through its `setup` hook."""
import hashlib
import json
import os
import threading
import time
import types

import pytest
from PIL import Image

from agent.driverlib import day as DY
from agent.driverlib import record as R
from agent.driverlib import session as S
from agent.driverlib import shots as SH
from .test_driverlib import run_session

RECT = (100, 50, 2020, 1130)
KEYS = {"n", "file", "bytes", "sha256", "wallMs", "pyMs", "seq", "gameMin", "health", "branch", "flee", "fight",
        "goal", "decision_line", "trigger", "window", "grab_ms"}


class Clock:
    def __init__(self, t=1000.0):
        self.t = t

    def now(self):
        return self.t


def fake_grab(calls=None, size=(1920, 1080)):
    def grab(bbox):
        if calls is not None:
            calls.append(bbox)
        return Image.new("RGB", size, (40, 90, 30))
    return grab


def taker(tmp_path, clock, find=lambda pid: RECT, grab=None, **kw):
    return SH.ShotTaker(str(tmp_path), pid=4242, grab=grab or fake_grab(), find=find, clock=clock.now, **kw)


def moment(seq=1, health=100.0, branch="goal", flee=None, fight=None, goal="LootBuilding", line=1, gameMin=560):
    return {"seq": seq, "wallMs": 1.79e12 + seq * 100.0, "gameMin": gameMin, "health": health, "branch": branch,
            "flee": flee, "fight": fight, "goal": goal, "decision_line": line}


def index(tmp_path):
    p = tmp_path / SH.SHOTS_DIR / SH.INDEX
    if not p.exists():
        return []
    return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]


def step(t, clock, at, m=None, final=None):
    """Mark at clock time `at` (a moment, else moment(seq=at)), then one worker pass."""
    clock.t = 1000.0 + at
    t.mark(m if m is not None else moment(seq=int(at * 10)), final=final)
    return t.run_due()


# ================================================================ constants
def test_the_constants_are_the_rulings():
    assert (SH.SHOT_EVERY_S, SH.SHOT_MIN_GAP_S, SH.SHOT_MAX) == (10.0, 1.0, 800)
    assert (SH.SHOT_WIDTH, SH.SHOT_QUALITY, SH.HEALTH_DROP) == (1280, 80, 5.0)
    assert SH.TRIGGERS == ("cadence", "threat", "goal", "health", "death", "stop") and SH.FINAL == ("death", "stop")
    assert (SH.SHOTS_DIR, SH.INDEX) == ("shots", "shots.jsonl")


# ================================================================ the cadence and the triggers
def test_the_cadence_marks_at_0_5_10_20_shoot_at_0_10_20(tmp_path):
    c = Clock()
    t = taker(tmp_path, c)
    took = [step(t, c, at) for at in (0, 5, 10, 20)]
    assert took == [1, 0, 1, 1]
    rows = index(tmp_path)
    assert [r["pyMs"] for r in rows] == [1000.0 * 1000, 1010.0 * 1000, 1020.0 * 1000]
    assert [r["trigger"] for r in rows] == ["cadence"] * 3 and [r["n"] for r in rows] == [1, 2, 3]
    assert [r["seq"] for r in rows] == [0, 100, 200]


@pytest.mark.parametrize("kind,m2", [
    ("threat", moment(seq=2, branch="threat", fight=0)),                     # a fight starts
    ("threat", moment(seq=2, branch="threat", flee="held_inside")),          # a hold begins
    ("goal", moment(seq=2, goal="Drink")),
    ("health", moment(seq=2, health=94.5)),
])
def test_each_event_trigger_shoots_at_once(tmp_path, kind, m2):
    c = Clock()
    t = taker(tmp_path, c)
    assert step(t, c, 0, moment(seq=1)) == 1
    assert step(t, c, 2, m2) == 1
    rows = index(tmp_path)
    assert [r["trigger"] for r in rows] == ["cadence", kind] and rows[1]["seq"] == 2


def test_a_flee_reason_change_and_a_hold_breaking_shoot(tmp_path):
    c = Clock()
    t = taker(tmp_path, c)
    step(t, c, 0, moment(seq=1, branch="threat", fight=0, flee="held_inside"))
    assert step(t, c, 2, moment(seq=2, branch="threat", fight=0, flee="held_inside")) == 0   # unchanged: none
    assert step(t, c, 3, moment(seq=3, branch="threat", fight=0, flee="pair")) == 1          # the reason changes
    assert step(t, c, 5, moment(seq=4, branch="threat", fight=0, flee=None)) == 1            # the hold breaks
    assert step(t, c, 7, moment(seq=5, branch="threat", fight=1, flee=None)) == 1            # a new fight
    assert [r["trigger"] for r in index(tmp_path)] == ["cadence", "threat", "threat", "threat"]


def test_health_counts_from_the_last_shot_not_the_last_mark(tmp_path):
    c = Clock()
    t = taker(tmp_path, c)
    step(t, c, 0, moment(seq=1, health=100.0))
    assert step(t, c, 2, moment(seq=2, health=97.0)) == 0
    assert step(t, c, 3, moment(seq=3, health=95.0)) == 1                    # 5 below the last shot's 100
    assert index(tmp_path)[-1]["trigger"] == "health" and index(tmp_path)[-1]["health"] == 95.0


def test_death_and_stop_fire_with_their_own_moment(tmp_path):
    c = Clock()
    t = taker(tmp_path, c)
    step(t, c, 0, moment(seq=1))
    c.t = 1000.2
    t.mark(moment(seq=7, health=0.0), final="death")
    t.mark(moment(seq=9, health=0.0), final="stop")                         # both before the worker's pass
    assert t.run_due() == 1 and t.run_due() == 1                             # the gap does not hold a final shot
    rows = index(tmp_path)
    assert [(r["trigger"], r["seq"]) for r in rows] == [("cadence", 1), ("death", 7), ("stop", 9)]


def test_the_1_s_gap_defers_an_event_until_it_passes(tmp_path):
    c = Clock()
    t = taker(tmp_path, c)
    step(t, c, 0, moment(seq=1))
    assert step(t, c, 0.5, moment(seq=2, goal="Drink")) == 0                 # inside the gap: held
    assert step(t, c, 0.8, moment(seq=3, goal="Drink")) == 0
    assert step(t, c, 1.0, moment(seq=4, goal="Drink")) == 1                 # the gap passed: the latest moment
    rows = index(tmp_path)
    assert [(r["trigger"], r["seq"]) for r in rows] == [("cadence", 1), ("goal", 4)]
    assert step(t, c, 1.5, moment(seq=5, goal="Eat")) == 0 and step(t, c, 2.0, moment(seq=6, goal="Eat")) == 1


def test_the_cap_leaves_only_death_and_stop(tmp_path):
    c = Clock()
    t = taker(tmp_path, c, cap=3)
    for at in (0, 10, 20, 30, 40):
        step(t, c, at)
    assert step(t, c, 42, moment(seq=1, goal="Other")) == 0
    s = t.summary()
    assert s["n"] == 3 and s["cap_hit"] is True
    assert step(t, c, 43, moment(seq=8, health=0.0), final="death") == 1
    assert step(t, c, 43.1, moment(seq=9, health=0.0), final="stop") == 1
    assert [r["trigger"] for r in index(tmp_path)] == ["cadence"] * 3 + ["death", "stop"]
    assert t.summary()["n"] == 5


# ================================================================ the image and the index
def test_the_index_line_and_the_file_it_names(tmp_path):
    c = Clock()
    calls = []
    t = taker(tmp_path, c, grab=fake_grab(calls))
    step(t, c, 0, moment(seq=31, branch="threat", flee="pair", fight=2, goal=None, line=17, health=88.0))
    (row,) = index(tmp_path)
    assert set(row) == KEYS
    assert row["file"] == "shot-0001-31.jpg" and row["n"] == 1
    assert (row["seq"], row["wallMs"], row["gameMin"], row["health"]) == (31, 1.79e12 + 3100.0, 560, 88.0)
    assert (row["branch"], row["flee"], row["fight"], row["goal"], row["decision_line"]) == ("threat", "pair", 2, None,
                                                                                            17)
    assert row["window"] == {"found": True, "rect": list(RECT), "rect_source": None} and calls == [RECT]
    assert row["pyMs"] == 1000.0 * 1000 and row["grab_ms"] >= 0
    data = (tmp_path / "shots" / row["file"]).read_bytes()
    assert row["bytes"] == len(data) and row["sha256"] == hashlib.sha256(data).hexdigest()
    img = Image.open(tmp_path / "shots" / row["file"])
    assert img.format == "JPEG" and img.size == (1280, 720)                  # 1920x1080 kept its aspect


def test_no_window_grabs_the_primary_screen_and_says_so(tmp_path):
    c = Clock()
    calls = []
    t = taker(tmp_path, c, find=lambda pid: None, grab=fake_grab(calls, size=(2560, 1440)))
    step(t, c, 0)
    (row,) = index(tmp_path)
    assert calls == [None] and row["window"] == {"found": False, "rect": None, "rect_source": None}
    assert Image.open(tmp_path / "shots" / row["file"]).size == (1280, 720)


def test_a_narrow_image_is_not_upscaled(tmp_path):
    c = Clock()
    t = taker(tmp_path, c, grab=fake_grab(size=(800, 600)))
    step(t, c, 0)
    assert Image.open(tmp_path / "shots" / index(tmp_path)[0]["file"]).size == (800, 600)


def test_a_grab_that_raises_is_counted_and_the_marks_keep_flowing(tmp_path):
    c = Clock()
    n = {"calls": 0}

    def grab(bbox):
        n["calls"] += 1
        if n["calls"] == 1:
            raise OSError("screen grab failed")
        return Image.new("RGB", (1920, 1080))
    t = taker(tmp_path, c, grab=grab)
    assert step(t, c, 0) == 0
    s = t.summary()
    assert s["failures"] == 1 and s["last_error"] == "OSError: screen grab failed" and s["n"] == 0
    assert step(t, c, 5) == 0                                                # the failed try counts as the last shot
    assert step(t, c, 10) == 1 and t.summary()["n"] == 1 and index(tmp_path)[0]["file"] == "shot-0001-100.jpg"


def test_a_finder_that_raises_is_counted_too(tmp_path):
    c = Clock()

    def find(pid):
        raise RuntimeError("no user32")
    t = taker(tmp_path, c, find=find)
    assert step(t, c, 0) == 0 and t.summary()["failures"] == 1


def test_a_bad_moment_never_raises_into_the_loop(tmp_path):
    c = Clock()
    t = taker(tmp_path, c)
    t.mark(None)
    t.mark({"health": "x", "seq": None})
    t.mark(moment(seq=1))
    assert t.run_due() == 1


def test_the_summary_is_the_records_shape(tmp_path):
    c = Clock()
    t = taker(tmp_path, c)
    assert t.summary() == {"n": 0, "failures": 0, "last_error": None, "dir": "shots", "every_s": 10.0,
                           "cap_hit": False}


# ================================================================ the worker thread
def test_the_worker_thread_shoots_and_joins_at_the_end(tmp_path):
    c = Clock()
    t = SH.ShotTaker(str(tmp_path), pid=None, grab=fake_grab(), find=lambda pid: RECT, clock=c.now, idle_s=0.005)
    t.start()
    t.mark(moment(seq=1))
    t0 = time.time()
    while t.summary()["n"] < 1 and time.time() - t0 < 5:
        time.sleep(0.005)
    t.mark(moment(seq=2, health=0.0), final="stop")
    assert t.end(timeout_s=5.0) is True
    assert [r["trigger"] for r in index(tmp_path)] == ["cadence", "stop"]
    assert not any(th.name == "ShotTaker" and th.is_alive() for th in threading.enumerate())


def test_the_join_is_bounded(tmp_path):
    c = Clock()
    gate = threading.Event()

    def slow(bbox):
        gate.wait(5)
        return Image.new("RGB", (64, 32))
    t = SH.ShotTaker(str(tmp_path), grab=slow, find=lambda pid: None, clock=c.now, idle_s=0.005)
    t.start()
    t.mark(moment(seq=1))
    time.sleep(0.05)
    t0 = time.time()
    assert t.end(timeout_s=0.1) is False and time.time() - t0 < 1.0
    gate.set()
    assert t.end(timeout_s=5.0) is True


def test_an_unstarted_taker_ends_joined(tmp_path):
    assert taker(tmp_path, Clock()).end() is True


# ================================================================ the session: marks, the death, the stop, the record
class InlineShots(SH.ShotTaker):
    """The worker's pass run on the loop's thread at each mark (the fake clock stays single-threaded)."""

    def start(self):
        self.started = True

    def mark(self, m, final=None):
        super().mark(m, final=final)
        self.run_due()


def attach(tmp_path, holder):
    def setup(sess):
        holder["t"] = InlineShots(str(tmp_path), pid=1, grab=fake_grab(size=(320, 180)), find=lambda pid: RECT,
                                  clock=sess.clock)
        sess.shots = holder["t"]
    return setup


def test_a_session_marks_each_tick_and_the_stop_and_records_its_shots(tmp_path, monkeypatch):
    h = {}
    r = run_session(tmp_path, monkeypatch, "sync", limits={"DAY_CAP_S": 40}, setup=attach(tmp_path, h))
    rows = index(tmp_path)
    loop = r.out["loop"]
    assert loop["shots"] == h["t"].summary() and loop["shots"]["n"] == len(rows) and loop["shots"]["failures"] == 0
    assert loop["shots_joined"] is True
    trig = [x["trigger"] for x in rows]
    assert trig[-1] == "stop" and trig.count("cadence") >= 4 and set(trig) <= set(SH.TRIGGERS)
    seqs = {f["seq"] for f in loop["last_frames"]}
    assert all(x["seq"] in seqs for x in rows)                               # every shot names a kept frame
    with open(tmp_path / S.DECISION_LOG, encoding="utf-8") as fh:
        n_lines = sum(1 for l in fh if l.strip())
    assert rows[-1]["decision_line"] == n_lines and rows[0]["decision_line"] >= 1
    persisted = json.loads((tmp_path / "session.json").read_text(encoding="utf-8"))
    assert persisted["loop"]["shots"] == loop["shots"]


def test_a_death_session_shoots_the_death_frame(tmp_path, monkeypatch):
    h = {}
    r = run_session(tmp_path, monkeypatch, "sync", die_from=40.0, drain=5.0, setup=attach(tmp_path, h))
    rows = index(tmp_path)
    death = r.out["loop"]["death"]
    d = [x for x in rows if x["trigger"] == "death"]
    assert len(d) == 1 and d[0]["seq"] == death["frame"]["seq"] and d[0]["health"] == 0.0
    assert rows[-1]["trigger"] == "stop" and any(x["trigger"] == "health" for x in rows)


def test_a_session_without_shots_records_none(tmp_path, monkeypatch):
    r = run_session(tmp_path, monkeypatch, "sync", limits={"DAY_CAP_S": 5})
    assert r.out["loop"]["shots"] is None and "shots_joined" not in r.out["loop"]
    assert not (tmp_path / "shots").exists()


def test_the_record_names_shots():
    assert "shots" in R.__doc__ and "shots" in S.__doc__ and "shots.jsonl" in DY.__doc__


# ================================================================ the day's wiring
def test_the_day_builds_a_taker_only_for_a_live_client(tmp_path):
    xs = types.SimpleNamespace(copied=[], out=S.new_out(), user="admin", path=str(tmp_path / "a.json"),
                               clients={"admin": types.SimpleNamespace(seen={})})
    assert DY.day_shots(xs) is None                                          # a fake client: no process
    xs.clients["admin"].proc = types.SimpleNamespace(pid=9876)
    t = DY.day_shots(xs, clock=lambda: 3.0)
    assert isinstance(t, SH.ShotTaker) and t.pid == 9876 and t.run_dir == str(tmp_path) and t.clock() == 3.0
    assert DY.day_shots(types.SimpleNamespace(user="admin", path=None, clients={})) is None
    c = DY.make_day_session(xs, None, lambda w, a, p, k: types.SimpleNamespace(), clock=lambda: 5.0,
                            shots=InlineShots(str(tmp_path), find=lambda pid: None, grab=fake_grab()))
    assert isinstance(c.shots, InlineShots)


def test_the_artifact_copy_takes_the_index(tmp_path):
    run_dir, repo = tmp_path / "run", tmp_path / "repo"
    (run_dir / "shots").mkdir(parents=True)
    (run_dir / "shots" / "shots.jsonl").write_bytes(b'{"n": 1}\n')
    (run_dir / "shots" / "shot-0001-5.jpg").write_bytes(b"jpeg")
    dest = DY.copy_shots_index(str(repo), "r-1", str(run_dir))
    assert dest == os.path.join(str(repo), "testing", "artifacts", "r-1", "shots", "shots.jsonl")
    assert open(dest, "rb").read() == b'{"n": 1}\n'
    assert sorted(os.listdir(os.path.dirname(dest))) == ["shots.jsonl"]      # the images stay in the run dir
    assert DY.copy_shots_index(str(repo), "r-2", str(tmp_path / "none")) is None
    src = open(DY.__file__, encoding="utf-8").read()
    assert "copy_shots_index(repo, run_id, run_dir)" in src


def test_the_drivers_are_not_edited():
    drivers = os.path.join(os.path.dirname(os.path.dirname(SH.__file__)), "drivers")
    for drv in ("e_day_2.py", "f_goals.py"):
        src = open(os.path.join(drivers, drv), encoding="utf-8").read()
        assert "ShotTaker" not in src and "shots=" not in src and "driverlib.shots" not in src, drv


# ================================================================ fix 1 (the shots review's residuals)
def test_a_due_that_raises_once_keeps_the_worker_and_its_final_shots(tmp_path):
    c = Clock()
    t = SH.ShotTaker(str(tmp_path), grab=fake_grab(), find=lambda pid: RECT, clock=c.now, idle_s=0.005)
    real, calls = t.due, {"n": 0}

    def due():
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("due broke")
        return real()
    t.due = due
    t.mark(moment(seq=1))
    t.start()
    t0 = time.time()
    while t.summary()["n"] < 1 and time.time() - t0 < 5:
        time.sleep(0.005)
    t.mark(moment(seq=2, health=0.0), final="stop")
    assert t.end(timeout_s=5.0) is True
    assert [r["trigger"] for r in index(tmp_path)] == ["cadence", "stop"]
    s = t.summary()
    assert s["failures"] == 1 and s["last_error"] == "worker: RuntimeError: due broke"


def test_an_artifact_copy_that_raises_still_leaves_the_index(tmp_path):
    run_dir, repo = tmp_path / "run", tmp_path / "repo"
    (run_dir / "shots").mkdir(parents=True)
    (run_dir / "shots" / "shots.jsonl").write_bytes(b'{"n": 1}\n')

    def boom(*a):
        raise OSError("disk full")
    xs = types.SimpleNamespace(copy_artifacts=boom)
    assert DY.copy_run(xs, str(repo), "r-1", str(run_dir), "a.json") is None
    dest = repo / "testing" / "artifacts" / "r-1" / "shots" / "shots.jsonl"
    assert dest.read_bytes() == b'{"n": 1}\n'
    src = open(DY.__file__, encoding="utf-8").read()
    body = src[src.index("def boot_and_run("):]
    assert "copy_run(xs, repo, run_id, run_dir, artifact)" in body and "xs.copy_artifacts(" not in body


# ================================================================ fix 2: the DWM frame bounds (the first live shots)
GWR = (630, 430, 1952, 1226)          # GetWindowRect: the visible frame plus the invisible resize borders and shadow
DWM = (640, 440, 1922, 1193)          # the extended frame bounds: the visible frame only
SCREEN = (0, 0, 2560, 1600)


def test_the_dwm_bounds_are_used_over_get_window_rect():
    assert SH.DWMWA_EXTENDED_FRAME_BOUNDS == 9
    assert SH.window_rect(7, dwm=lambda h: DWM, gwr=lambda h: GWR, screen=lambda: SCREEN) == (DWM, "dwm")


@pytest.mark.parametrize("dwm", [lambda h: None, lambda h: (5, 5, 5, 5), "raise"])
def test_a_failing_dwm_falls_back_to_get_window_rect(dwm):
    if dwm == "raise":
        def dwm(h):
            raise OSError("no dwmapi")
    assert SH.window_rect(7, dwm=dwm, gwr=lambda h: GWR, screen=lambda: SCREEN) == (GWR, "gwr")


def test_the_rect_is_clipped_to_the_virtual_screen_and_a_minimised_window_is_none():
    got = SH.window_rect(7, dwm=lambda h: (-8, -8, 2568, 1560), gwr=lambda h: GWR, screen=lambda: SCREEN)
    assert got == ((0, 0, 2560, 1560), "dwm")
    assert SH.window_rect(7, dwm=lambda h: None, gwr=lambda h: (-32000, -32000, -31840, -31972),
                          screen=lambda: SCREEN) is None
    assert SH.window_rect(7, dwm=lambda h: None, gwr=lambda h: None, screen=lambda: SCREEN) is None
    assert SH.window_rect(7, dwm=lambda h: DWM, gwr=lambda h: GWR, screen=lambda: None) == (DWM, "dwm")
    assert SH.clip((3000, 10, 3100, 20), SCREEN) is None


@pytest.mark.parametrize("src", ["dwm", "gwr"])
def test_the_index_line_names_the_rect_source(tmp_path, src):
    c = Clock()
    calls = []
    t = taker(tmp_path, c, find=lambda pid: {"rect": DWM, "source": src}, grab=fake_grab(calls))
    step(t, c, 0)
    (row,) = index(tmp_path)
    assert row["window"] == {"found": True, "rect": list(DWM), "rect_source": src} and calls == [DWM]
