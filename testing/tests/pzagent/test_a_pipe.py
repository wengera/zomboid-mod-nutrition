"""drivers/a_pipe.py, drivers/a_grade.py and agent/grades.py (Plan 21 Task 8), offline: the driver is never invoked.

The phases run against a FakeMod that plays PZAgent's Lua into a tmp state dir with the real line shapes
(PZAgent_Main.lua: hello {modVersion, build, user, rate, mode}; ack {cmdSeq, ok, reason}; frame {x, y, z, goal {seq,
name, state, detail}, cost {actMs, senseMs, linkMs, pollMs, dropped}}; scan {r, squares, missing, scanMs}; a config
command acked and flushed on its tick, a scan line emitted before its ack) on an injected clock, so a 60 s window costs
no wall time."""
import json
import math
import os
import shutil
import types

import pytest

from agent import grades as G
from agent.drivers import a_pipe as D
from agent.drivers import a_grade as AG
from agent.link import Link
from pzt import fixture as fx

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
X = D.X


# ================================================================ static: refusal and constants
def test_the_driver_refuses_arguments_before_main():
    with open(D.__file__, encoding="utf-8") as fh:
        src = fh.read()
    i_ref, i_main = src.index("refusal = parse_argv(sys.argv[1:], __file__)"), src.rindex("    main()")
    assert src.index('if __name__ == "__main__":') < i_ref < i_main
    assert "sys.exit(refusal)" in src[i_ref:i_main]
    assert D.parse_argv(["x"], D.__file__) and D.parse_argv(["--help"], D.__file__)
    assert D.parse_argv([], D.__file__) is None


def test_the_constants_name_the_drivers_own_file_and_profile():
    assert os.path.basename(D.__file__) == D.DRIVER == D.KEY + ".py"
    assert D.ARTIFACT == D.KEY + ".json"
    assert D.PROFILE == "testing/profiles/agent-nozombies.toml" and os.path.isfile(os.path.join(REPO, D.PROFILE))
    assert (D.BUDGET_S, D.USER, D.MIN_FREE_GB) == (540.0, "admin", 12.0)
    assert D.RATES == (2, 5, 10) and D.SCAN_RADII == (5, 10, 15) and D.MOTION_TRIPS == 10


# ================================================================ grades
def test_pct_nearest_rank():
    v = list(range(1, 101))
    assert G.pct(v, 99) == 99 and G.pct(v, 90) == 90 and G.pct(v, 50) == 50 and G.pct(v, 100) == 100
    assert G.pct([5.0], 99) == 5.0 and G.pct([3, 1, 2], 50) == 2
    assert G.pct([1, 2, 3, 4], 0) == 1
    assert G.pct([], 99) is None and G.pct([None, None], 50) is None


def passing_out():
    return {"mode": "append", "gaps": [], "lua_errors": 0, "client_lua_errors": 0,
            "readings": {"rates": {"5": {"tickMs": [0.5] * 299 + [1.9]}},
                         "scans": {"15": [{"scanMs": 4}] * 5},
                         "motion": [{"ack": {"wallMs": 1000}, "first_motion": {"wallMs": 1000 + d}}
                                    for d in [100] * 18 + [450, 900]]}}


def test_gate_a_passes_a_passing_set():
    g = G.gate_a(passing_out())
    assert g["verdict"] == "GO" and all(g["pass"].values()), g
    assert g["tick_p99_ms_at5"] == 0.5 and g["scan15_ms_max"] == 4 and g["cmd_motion_p90_ms"] == 100
    assert g["gaps"] == 0 and g["lua_errors"] == 0 and g["mode"] == "append"


def _cross(name):
    o = passing_out()
    r = o["readings"]
    if name == "tick_p99_at5":
        r["rates"]["5"]["tickMs"] = [0.5] * 290 + [2.0] * 10
    elif name == "scan15":
        r["scans"]["15"] = [{"scanMs": 4}] * 4 + [{"scanMs": 5.0}]
    elif name == "cmd_motion_p90":
        r["motion"] = [{"ack": {"wallMs": 0}, "first_motion": {"wallMs": d}} for d in [100] * 17 + [500] * 3]
    elif name == "gaps":
        o["gaps"] = [[5, 7]]
    elif name == "lua_errors":
        o["client_lua_errors"] = 1
    elif name == "hello":
        o["mode"] = None
    return o


@pytest.mark.parametrize("name", ["tick_p99_at5", "scan15", "cmd_motion_p90", "gaps", "lua_errors", "hello"])
def test_each_threshold_crossed_alone_flips_its_gate_and_the_verdict(name):
    g = G.gate_a(_cross(name))
    assert g["verdict"] == "NO-GO"
    assert [k for k, v in g["pass"].items() if not v] == [name]


def test_a_lua_error_event_alone_fails():
    o = passing_out()
    o["lua_errors"] = 1
    assert G.gate_a(o)["pass"]["lua_errors"] is False


@pytest.mark.parametrize("drop", ["rates", "scans", "motion", "gaps", "lua_errors", "client_lua_errors",
                                  "scan_none", "motion_unpaired", "tick_none"])
def test_a_missing_reading_fails_its_gate(drop):
    o = passing_out()
    r = o["readings"]
    if drop in ("rates", "scans", "motion"):
        del r[drop]
    elif drop == "scan_none":
        r["scans"]["15"][2] = {"error": "no scan line"}
    elif drop == "motion_unpaired":
        r["motion"] = [{"ack": {"wallMs": 0}, "first_motion": None}] * 20
    elif drop == "tick_none":
        r["rates"]["5"]["tickMs"] = [None, None]
    else:
        del o[drop]
    g = G.gate_a(o)
    assert g["verdict"] == "NO-GO"
    want = {"rates": "tick_p99_at5", "tick_none": "tick_p99_at5", "scans": "scan15", "scan_none": "scan15",
            "motion": "cmd_motion_p90", "motion_unpaired": "cmd_motion_p90", "gaps": "gaps",
            "lua_errors": "lua_errors", "client_lua_errors": "lua_errors"}[drop]
    assert g["pass"][want] is False


def test_cmd_motion_is_the_client_clock_difference():
    rows = [{"ack": {"wallMs": 5000}, "first_motion": {"wallMs": 5120, "readPyMs": 1.7e12}, "sentPyMs": 1.7e12 - 9e9}]
    assert G.cmd_motion_ms(rows) == [120]


def test_a_grade_exits_on_the_verdict(tmp_path, capsys):
    p = tmp_path / "a.json"
    p.write_text(json.dumps(passing_out()))
    assert AG.main([str(p)]) == 0
    assert json.loads(capsys.readouterr().out)["verdict"] == "GO"
    p.write_text(json.dumps(_cross("gaps")))
    assert AG.main([str(p)]) == 1
    assert AG.main([]) == 2 and AG.main([str(tmp_path / "none.json")]) == 2


# ================================================================ pre-boot, on the real profile and a real run layout
@pytest.fixture
def agent_fixture(tmp_path, monkeypatch):
    """A throwaway `agent` fixture (the real one is machine-local and gitignored), test_dlib's."""
    root = tmp_path / "fixtures"
    sv = root / "agent" / "cache" / "server" / "Server"
    sv.mkdir(parents=True)
    (sv / "pzt_SandboxVars.lua").write_text("SandboxVars = {\n    Zombies = 5,\n    DayLength = 4,\n}\n")
    (root / "agent" / "fixture.json").write_text(json.dumps(
        {"name": "agent", "build": "42.21.0", "server": {"name": "pzt", "mods": ["PZTestKit"]},
         "clients": {"admin": {}}}))
    monkeypatch.setattr(fx, "FIXTURES", str(root))
    return root


def stub_checks(monkeypatch, dirty=False, lint=(), tracked=""):
    monkeypatch.setattr(D.DL.C, "doctor", lambda: (True, "ok"))
    monkeypatch.setattr(D.DL.harness, "lint_paths", lambda srcs: list(lint))
    monkeypatch.setattr(D.DL.C, "git_dirty", lambda rel: (dirty, ""))
    real = D.DL.C.git_say
    monkeypatch.setattr(D.DL.C, "git_say", lambda *a: tracked if a[0] == "ls-files" else real(*a))


def test_preboot_on_the_real_profile(agent_fixture, monkeypatch):
    stub_checks(monkeypatch)
    pre, ok = D.preboot(D.__file__)
    assert ok, pre
    assert pre["profile"] == "agent-nozombies" and pre["lint_errors"] == [] and pre["doctor_clean"]
    assert pre["driver_checks"] == {"driver_file": True, "driver_prefix": True, "profile_exists": True,
                                    "no_committed_artifact": True, "agent_lua_dirty": False, "driver_dirty": False}


def test_preboot_refuses(agent_fixture, monkeypatch):
    stub_checks(monkeypatch, tracked="testing/artifacts/a_pipe-20261026-120000/a_pipe.json")
    pre, ok = D.preboot(D.__file__)
    assert not ok and pre["driver_checks"]["no_committed_artifact"] is False
    stub_checks(monkeypatch, dirty=True)
    pre, ok = D.preboot(D.__file__)
    assert not ok and pre["driver_checks"]["agent_lua_dirty"] is True
    stub_checks(monkeypatch, lint=["ERROR x"])
    assert D.preboot(D.__file__)[1] is False
    stub_checks(monkeypatch)
    pre, ok = D.preboot(os.path.join(os.path.dirname(D.__file__), "b_act.py"))
    assert not ok and pre["driver_checks"]["driver_file"] is False


def test_preboot_refuses_a_missing_profile(monkeypatch, tmp_path):
    stub_checks(monkeypatch)
    c, ok = D.driver_checks(D.__file__, repo=str(tmp_path))
    assert not ok and c["profile_exists"] is False


def test_the_run_layout_state_dir_is_cleared_before_the_client_starts(tmp_path):
    run_dir = tmp_path / "runs" / "a_pipe-20261026-120000"
    cache = run_dir / "clients" / "admin"
    stale = cache / "Lua" / "pzagent" / "admin"
    stale.mkdir(parents=True)
    (stale / "ack.txt").write_text("seq=40\n")
    (stale / "state.log").write_text('{"seq":1,"kind":"hello"}\n')
    (cache / "Lua" / "keep.ini").write_text("x")
    calls = []

    def make(rd, user, server, rec, **kw):
        calls.append((rd, user))
        return types.SimpleNamespace(cache=str(cache), username=user), True

    c, restored = D.clearing_make_client(make)(str(run_dir), "admin", None, {})
    assert restored and calls == [(str(run_dir), "admin")]
    assert not (cache / "Lua" / "pzagent").exists() and (cache / "Lua" / "keep.ini").exists()
    assert D.DL.state_dir(c) == str(stale)


def test_main_patches_make_client_where_attach_clients_reads_it():
    from pzt import session
    src = open(D.__file__, encoding="utf-8").read()
    assert "session.make_client = clearing_make_client(real_make)" in src
    assert 'globals()["make_client"]' in open(session.__file__, encoding="utf-8").read()


# ================================================================ the phases against a FakeMod
class Clock:
    def __init__(self):
        self.t = 1_790_000_000.0

    def now(self):
        return self.t


class FakeMod:
    """PZAgent's Lua, one tick at a time on `clock`: polls cmd.txt by seq, acks, emits the real line shapes and
    appends them to state.log. Flags: silent (no line at all), still (never moves; the goal fails stuck), scan_ms,
    tick cost (pollMs, actMs, senseMs, linkMs), move_delay ticks before the walk moves the player. `goto x y` takes
    world coordinates (the coordinator's ruling, Task 9's Lua)."""
    TPS = 60

    def __init__(self, d, clock, silent=False, still=False, scan_ms=3, cost=(0.1, 0.2, 0.3, 0.0), move_delay=3,
                 walk=0.08, lua_error_at=None):
        os.makedirs(d, exist_ok=True)
        self.d, self.clock = d, clock
        self.silent, self.still, self.scan_ms, self.cost = silent, still, scan_ms, cost
        self.move_delay, self.walk, self.lua_error_at = move_delay, walk, lua_error_at
        self.seq = self.tick = self.last_cmd = 0
        self.rate = 5
        self.buf = []
        self.x, self.y = 100.5, 200.5
        self.goal = None
        self.ready = False
        self.cmds = []

    def now_ms(self):
        return int(self.clock.t * 1000)

    def emit(self, kind, body):
        self.seq += 1
        body.update(kind=kind, seq=self.seq, tick=self.tick, wallMs=self.now_ms())
        self.buf.append(json.dumps(body))

    def flush(self):
        if self.buf:
            with open(os.path.join(self.d, "state.log"), "a", encoding="utf-8", newline="\n") as f:
                f.write("\n".join(self.buf) + "\n")
            self.buf = []

    def poll(self):
        p = os.path.join(self.d, "cmd.txt")
        if not os.path.isfile(p):
            return None
        kv = dict(ln.split("=", 1) for ln in open(p, encoding="utf-8").read().splitlines() if "=" in ln)
        seq = int(kv["seq"])
        if seq <= self.last_cmd:
            return None
        self.last_cmd = seq
        return {"seq": seq, "goal": kv.get("goal", ""), "args": kv.get("args", "")}

    def status(self):
        g = self.goal
        if g is None:
            return {"seq": 0, "name": "idle", "state": "idle", "detail": ""}
        if g["state"] != "running":
            g["reported"] = True
        return {"seq": g["seq"], "name": g["name"], "state": g["state"], "detail": g["detail"]}

    def step(self):
        self.clock.t += 1.0 / self.TPS
        self.tick += 1
        if self.silent:
            return
        cmd = self.poll()
        if cmd:
            self.cmds.append(cmd)
            a = cmd["args"].split()
            if cmd["goal"] == "rate":
                self.rate = float(a[0])
            elif cmd["goal"] == "scan":
                r = int(a[0])
                sq = [{"x": int(self.x) + dx, "y": int(self.y) + dy, "z": 0, "solid": False}
                      for dy in range(-r, r + 1) for dx in range(-r, r + 1)]
                self.emit("scan", {"r": r, "squares": sq, "missing": ["getLightLevel"] if r == 15 else [],
                                   "scanMs": self.scan_ms, "hour": 7})
            if cmd["goal"] == "goto":
                self.goal = {"seq": cmd["seq"], "name": "goto", "state": "running", "detail": "",
                             "tx": float(a[0]), "ticks": 0}
                self.emit("ack", {"cmdSeq": cmd["seq"], "ok": True, "reason": ""})
            elif cmd["goal"] in ("rate", "scan"):
                self.emit("ack", {"cmdSeq": cmd["seq"], "ok": True, "reason": ""})
            else:
                self.emit("ack", {"cmdSeq": cmd["seq"], "ok": False, "reason": "unknown goal"})
            self.flush()
        if not self.ready:
            self.emit("hello", {"modVersion": "0.1", "build": "42.21.0", "user": "admin", "rate": self.rate,
                                "mode": "append"})
            self.flush()
            self.ready = True
        if self.lua_error_at == self.tick:
            self.emit("event", {"event": "lua_error", "msg": "boom"})
            self.flush()
        g = self.goal
        if g is not None:
            if g["state"] != "running":
                if g.get("reported"):
                    self.goal = None
            else:
                g["ticks"] += 1
                if self.still:
                    if g["ticks"] >= 120:
                        g["state"], g["detail"] = "failed", "stuck"
                elif g["ticks"] > self.move_delay:
                    d = g["tx"] - self.x
                    self.x += math.copysign(min(self.walk, abs(d)), d)
                    if abs(g["tx"] - self.x) <= 1.0:
                        g["state"], g["detail"] = "done", "d=%s" % abs(g["tx"] - self.x)
        every = max(1, math.floor(60 / self.rate))
        if self.tick % every == 0:
            p, a, s, l = self.cost
            self.emit("frame", {"x": self.x, "y": self.y, "z": 0, "goal": self.status(),
                                "cost": {"pollMs": p, "actMs": a, "senseMs": s, "linkMs": l, "dropped": 0}})
            self.flush()

    def sleep(self, dt):
        for _ in range(max(1, round(dt * self.TPS))):
            self.step()


def run_pipe(tmp_path, budget_s=1e9, **flags):
    clock = Clock()
    sd = str(tmp_path / "clients" / "admin" / "Lua" / "pzagent" / "admin")
    mod = FakeMod(sd, clock, **flags)
    out = D.new_out()
    calls = []

    def ask(node, cmd, args, timeout=30):
        calls.append((node, cmd, args))
        mod.sleep(0.05)
        return {"ok": True, "user": args, "stats": {"HUNGER": 0.1}}

    xs = X.Xs(out, node=lambda side: side, ask=ask, clock=clock.now, sleep=mod.sleep, budget_s=budget_s,
              user="admin")
    xs.path = str(tmp_path / D.ARTIFACT)
    pipe = D.Pipe(xs, Link(sd, clock=clock.now), clock=clock.now, sleep=mod.sleep)
    pipe.run()
    return out, mod, calls, clock


def test_the_phases_record_every_reading_on_a_correct_mod(tmp_path):
    out, mod, calls, _ = run_pipe(tmp_path)
    assert out["phase_errors"] == {} and "budget_stop" not in out, out["phase_errors"]
    assert out["mode"] == "append" and out["hello"]["kind"] == "hello"
    rd = out["readings"]
    assert sorted(rd) == ["motion", "rates", "scans", "server"]
    for r in ("2", "5", "10"):
        row = rd["rates"][r]
        assert row["expected"] == 60 * int(r) and abs(row["frames"] - row["expected"]) <= 2, row["frames"]
        assert row["ack"]["ok"] is True and row["ack"]["cmdSeq"] == row["cmdSeq"]
        for k in D.COST_KEYS + ("tickMs",):
            assert len(row[k]) == row["frames"]
        assert row["tickMs"][0] == pytest.approx(0.6) and row["dropped_max"] == 0
        assert row["state_bytes_end"] > row["state_bytes_start"]
        assert row["frame_wallMs_last"] - row["frame_wallMs_first"] <= 60_000
    assert sorted(rd["scans"]) == ["10", "15", "5"]
    for r in (5, 10, 15):
        rows = rd["scans"][str(r)]
        assert len(rows) == 5 and all(s["scanMs"] == 3 and s["squares"] == (2 * r + 1) ** 2 for s in rows)
        assert all(s["bytes"] > 0 and s["next_frame_senseMs"] == 0.3 and s["ack"]["ok"] for s in rows)
    m = rd["motion"]
    assert len(m) == 20 and [r["dx"] for r in m[:2]] == [10, -10]
    for r in m:
        assert r["args"] == "%s %s" % (str(r["x0"] + r["dx"]), str(r["y0"]))      # world coordinates, unrounded
        assert r["goal"]["state"] == "done" and r["first_motion"] is not None, r
        assert r["first_motion"]["wallMs"] >= r["ack"]["wallMs"] and abs(r["first_motion"]["x"] - r["x0"]) > 0.2
        assert r["sentPyMs"] <= r["first_motion"]["readPyMs"]
    assert len(rd["server"]) == 3 and all(s["rttMs"] > 0 and s["ack"]["ok"] for s in rd["server"])
    assert [c[1] for c in calls] == ["stats.all"] * 3 and calls[0][2] == "admin"
    assert out["missing"] == ["getLightLevel"] and out["gaps"] == [] and out["bad"] == 0 and out["lua_errors"] == 0
    assert [c["goal"] for c in mod.cmds[:3]] == ["rate"] * 3
    out["client_lua_errors"] = 0
    g = G.gate_a(out)
    assert g["verdict"] == "GO", g
    persisted = json.loads((tmp_path / D.ARTIFACT).read_text(encoding="utf-8"))
    assert persisted["readings"]["rates"]["5"]["frames"] == out["readings"]["rates"]["5"]["frames"]


@pytest.fixture
def short_window(monkeypatch):
    """The defect cases need no 60 s window: 5 s keeps the suite quick (the correct-mod case runs the real one)."""
    monkeypatch.setattr(D, "WINDOW_S", 5.0)


def test_a_mod_that_never_moves_fails_cmd_motion(tmp_path, short_window):
    out, _, _, _ = run_pipe(tmp_path, still=True)
    m = out["readings"]["motion"]
    assert len(m) == 20 and all(r["first_motion"] is None and r["goal"]["state"] == "failed" for r in m)
    out["client_lua_errors"] = 0
    g = G.gate_a(out)
    assert g["pass"]["cmd_motion_p90"] is False and g["cmd_motion_p90_ms"] is None and g["verdict"] == "NO-GO"


def test_a_slow_scan_and_a_lua_error_fail_their_gates(tmp_path, short_window):
    out, _, _, _ = run_pipe(tmp_path, scan_ms=7, lua_error_at=100)
    out["client_lua_errors"] = 0
    g = G.gate_a(out)
    assert out["lua_errors"] == 1 and g["pass"]["scan15"] is False and g["pass"]["lua_errors"] is False
    assert g["pass"]["tick_p99_at5"] and g["pass"]["cmd_motion_p90"]


def test_a_silent_mod_fails_fast_with_no_hello(tmp_path):
    out, _, calls, clock = run_pipe(tmp_path, silent=True)
    pe = out["phase_errors"]
    assert sorted(pe) == ["motion", "rates", "scans"] and all("no hello" in v["error"] for v in pe.values())
    assert out["readings"]["rates"] == {} and out.get("mode") is None and len(out["readings"]["server"]) == 3
    assert clock.t - 1_790_000_000.0 < D.HELLO_TIMEOUT_S + 5
    assert G.gate_a(out)["verdict"] == "NO-GO"


def test_the_budget_stops_a_phase_and_is_recorded(tmp_path):
    out, _, _, _ = run_pipe(tmp_path, budget_s=30.0)
    assert "budget_stop" in out["phase_walls"]["rates"] and out["budget_stop"]["why"].startswith("wall ")
    assert out["readings"]["rates"] == {}          # the first window never closed
    assert len(out["readings"]["server"]) == 3     # the server phase has no poll, so it still runs


def test_a_goto_with_no_frame_yet_is_recorded_and_never_sent(tmp_path):
    clock = Clock()
    sd = str(tmp_path / "sd")
    mod = FakeMod(sd, clock, silent=True)
    xs = X.Xs(D.new_out(), node=lambda side: side, clock=clock.now, sleep=mod.sleep, user="admin")
    link = Link(sd, clock=clock.now)
    row = D.Pipe(xs, link, clock=clock.now, sleep=mod.sleep).one_goto(0, 10)
    assert row["error"].startswith("no frame before the command") and "cmdSeq" not in row and link.cmd_seq == 0
