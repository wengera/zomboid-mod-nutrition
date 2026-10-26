"""drivers/a_pipe_3.py and the gate_a amendment (Plan 21 Stage A pass 3), offline: the driver is never invoked.

The phases run against FakeMod3, test_a_pipe_2's FakeMod2 with pass 3's Lua shapes (PZAgent_Main.lua after Stage A pass
3): a `scan r` acked at once ("queued") and its squares emitted as scanPart lines, one per tick from the ack's own tick,
each with scanId, part, parts, stepMs and emitMs (the previous part's emit, part 1's 0), the last carrying done and the
scan's totals; the first frame after the last part carrying cost.scanEmitMs (the last part's own emit)."""
import math
import os

import pytest

from agent import grades as G
from agent.drivers import a_pipe_3 as D
from agent.link import Link
from agent.world import World
from . import test_a_pipe as T1
from . import test_a_pipe_2 as T2

REPO = T1.REPO
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


def test_the_constants_name_the_drivers_own_file_key_artifact_and_profile():
    assert os.path.basename(D.__file__) == D.DRIVER == D.KEY + ".py" == "a_pipe_3.py"
    assert D.KEY == "a_pipe_3" and D.ARTIFACT == "a_pipe_3.json" and D.BUDGET_S == 560.0
    assert D.PROFILE == "testing/profiles/agent-nozombies.toml" and os.path.isfile(os.path.join(REPO, D.PROFILE))
    assert D.PASS2_RUN == "a_pipe_2-20261026-115846" and D.PASS2_RUN in D.__doc__
    assert (D.RATE60, D.RATE60_WINDOW_S, D.RATE_BACK) == (60, 30.0, 10) and D.RATE_BACK == D.AP2.RATES[-1] and D.COST_KEYS == D.AP2.COST_KEYS
    assert D.CONSTANTS["inherited_from_a_pipe_2"]["WINDOW_S"] == D.AP2.WINDOW_S
    assert "mean of quantised readings" in D.__doc__ and "does NOT resolve" in D.__doc__


def test_the_frozen_drivers_are_imported_never_copied_over():
    src = open(D.__file__, encoding="utf-8").read()
    assert "from agent.drivers import a_pipe as AP" in src and "from agent.drivers import a_pipe_2 as AP2" in src
    assert issubclass(D.Pipe3, D.AP2.Pipe2) and D.AP2.KEY == "a_pipe_2"
    assert "make_client=AP.clearing_make_client(session.make_client)" in src


def test_preboot_on_the_real_profile(agent_fixture, monkeypatch):
    monkeypatch.setattr(D.DL.C, "doctor", lambda: (True, "ok"))
    monkeypatch.setattr(D.DL.harness, "lint_paths", lambda srcs: [])
    monkeypatch.setattr(D.DL.C, "git_dirty", lambda rel: (False, ""))
    real = D.DL.C.git_say
    tracked = {"v": ""}
    monkeypatch.setattr(D.DL.C, "git_say", lambda *a: tracked["v"] if a[0] == "ls-files" else real(*a))
    pre, ok = D.preboot(D.__file__)
    assert ok, pre
    assert pre["profile"] == "agent-nozombies" and pre["driver_checks"]["driver_file"] is True
    tracked["v"] = "testing/artifacts/a_pipe_3-20261027-120000/a_pipe_3.json"
    assert D.preboot(D.__file__)[1] is False
    tracked["v"] = ""
    assert D.preboot(os.path.join(os.path.dirname(D.__file__), "a_pipe_2.py"))[1] is False


# ================================================================ gate_a: the per-tick term over parts
def parts_row(steps, emits, last_emit, **over):
    """A pass-3 row: partEmitMs as the lines carry them (part i's is part i-1's emit; part 1's 0)."""
    row = {"scanMs": sum(steps), "scanTicks": len(steps), "partStepMs": list(steps), "partEmitMs": list(emits),
           "scanEmitMs": last_emit}
    row.update(over)
    return row


def test_the_part_emits_performed_are_the_next_parts_emit_ms_and_the_frames_last():
    row = parts_row([1, 2, 3], [0, 5, 6], 7)
    assert G.part_emits(row) == [5, 6, 7]                       # tick 1 paid part 2's reported 5, tick 3 the frame's 7
    assert G.scan_part_tick_ms(row) == max(1 + 5, 2 + 6, 3 + 7) == 10
    assert G.scan_latency_ms(row) == 6 + 18


def test_a_three_ms_step_with_a_three_ms_emit_fails_and_two_plus_two_goes():
    o = T1.passing_out()
    steps = [1] * 17
    o["readings"]["scans"]["15"] = [parts_row(steps, [0] + [1] * 16, 1)] * 5
    bad = parts_row([1] * 8 + [3] + [1] * 8, [0] + [1] * 8 + [3] + [1] * 7, 1)   # tick 9: 3 ms walk + 3 ms emit
    o["readings"]["scans"]["15"][2] = bad
    g = G.gate_a(o)
    assert g["scan15_ms_max"] == 6 and [k for k, v in g["pass"].items() if not v] == ["scan15"]
    o["readings"]["scans"]["15"][2] = parts_row([1] * 8 + [2] + [1] * 8, [0] + [1] * 8 + [2] + [1] * 7, 1)
    g = G.gate_a(o)
    assert g["scan15_ms_max"] == 4 and g["verdict"] == "GO", g
    o["readings"]["scans"]["15"][2] = parts_row([1] * 16 + [3], [0] + [1] * 16, 3)   # the last tick: the frame's emit
    assert G.gate_a(o)["scan15_ms_max"] == 6


def test_the_emit_is_charged_to_the_tick_that_performed_it_not_the_part_that_reports_it():
    o = T1.passing_out()
    # part 2 reports a 4 ms emit (part 1's) beside its own 3 ms step: 3 + 4 is not a tick; tick 1 is 1 + 4 = 5
    o["readings"]["scans"]["15"] = [parts_row([1, 3, 1], [0, 4, 0], 0)] * 5
    g = G.gate_a(o)
    assert g["scan15_ms_max"] == 5 and g["pass"]["scan15"] is False
    o["readings"]["scans"]["15"] = [parts_row([1, 3, 1], [0, 3.9, 0], 0)] * 5
    assert G.gate_a(o)["scan15_ms_max"] == 4.9 and G.gate_a(o)["pass"]["scan15"] is True


@pytest.mark.parametrize("bad", ["no_frame_emit", "none_step", "none_emit", "short_emits", "empty"])
def test_a_missing_part_value_fails_the_scan_gate(bad):
    o = T1.passing_out()
    row = parts_row([1, 1, 1], [0, 1, 1], 1)
    if bad == "no_frame_emit":
        row["scanEmitMs"] = None
    elif bad == "none_step":
        row["partStepMs"][1] = None
    elif bad == "none_emit":
        row["partEmitMs"][2] = None
    elif bad == "short_emits":
        row["partEmitMs"] = [0, 1]
    else:
        row["partStepMs"], row["partEmitMs"] = [], []
    o["readings"]["scans"]["15"][1] = row
    g = G.gate_a(o)
    assert g["scan15_ms_max"] is None and g["pass"]["scan15"] is False and g["verdict"] == "NO-GO"


def test_tick_mean_at60_is_reported_ungraded():
    o = T1.passing_out()
    assert G.gate_a(o)["tick_mean_ms_at60"] is None and G.gate_a(o)["verdict"] == "GO"
    o["readings"]["rate60"] = {"tick_mean_ms_at60": 9.5}
    g = G.gate_a(o)
    assert g["tick_mean_ms_at60"] == 9.5 and "tick_mean_ms_at60" not in g["pass"] and g["verdict"] == "GO"


# ================================================================ the phases against FakeMod3
class FakeMod3(T2.FakeMod2):
    """FakeMod2 with pass 3's scan in parts: each part's walk costs step_ms and its emit emit_ms; `alt` maps a tick
    parity to an actMs, so a rate-60 window's frames carry a known non-constant cost."""

    def __init__(self, d, clock, step_ms=1, emit_ms=2, alt=None, **kw):
        super().__init__(d, clock, chunk_ms=step_ms, **kw)
        self.step_ms, self.emit_ms, self.alt = step_ms, emit_ms, alt
        self.job, self.scan_id, self.last_part_emit = None, 0, 0

    def poll(self):
        cmd = super().poll()
        if self.pending:                                       # FakeMod2 queued a whole-line scan: run it as parts
            _, r, _ = self.pending
            self.pending = None
            self.scan_id += 1
            sq = [{"x": int(self.x) + dx, "y": int(self.y) + dy, "z": 0, "solid": False}
                  for dy in range(-r, r + 1) for dx in range(-r, r + 1)]
            self.job = {"id": self.scan_id, "r": r, "squares": sq, "parts": math.ceil(len(sq) / 60), "next": 1}
        return cmd

    def emit(self, kind, body):
        if kind == "frame":
            body.update(health=self.health, nZombies=self.nz)
            body["cost"]["scanStepMs"] = self.step_ms + self.emit_ms if self.job else 0
            body["cost"]["scanEmitMs"], self.emit_due = self.emit_due, 0
            if self.alt is not None:
                body["cost"]["actMs"] = self.alt[self.tick % 2]
        T1.FakeMod.emit(self, kind, body)

    def step(self):
        super().step()
        j = self.job
        if j is None:
            return
        k, n = j["next"], j["parts"]
        body = {"scanId": j["id"], "r": j["r"], "hour": 7, "part": k, "parts": n,
                "squares": j["squares"][(k - 1) * 60:k * 60], "missing": [], "stepMs": self.step_ms,
                "emitMs": self.last_part_emit if k > 1 else 0}
        if k == n:
            body.update(done=True, scanMs=self.step_ms * n, scanTicks=n, scanMsPerTick=[self.step_ms] * n,
                        scanStepMaxMs=self.step_ms)
        self.emit("scanPart", body)
        self.flush()
        self.last_part_emit = self.emit_ms
        if k == n:
            self.emit_due, self.job = self.emit_ms, None
        else:
            j["next"] = k + 1


@pytest.fixture
def short_windows(monkeypatch):
    monkeypatch.setattr(D.AP2, "WINDOW_S", 5.0)
    monkeypatch.setattr(D, "RATE60_WINDOW_S", 2.0)


def make_pipe(tmp_path, **flags):
    clock = T1.Clock()
    sd = str(tmp_path / "clients" / "admin" / "Lua" / "pzagent" / "admin")
    mod = FakeMod3(sd, clock, **flags)
    out = D.new_out()

    def ask(node, cmd, args, timeout=30):
        mod.sleep(0.05)
        return {"ok": True, "user": args, "stats": {"HUNGER": 0.1}}

    xs = X.Xs(out, node=lambda side: side, ask=ask, clock=clock.now, sleep=mod.sleep, budget_s=1e9, user="admin")
    xs.path = str(tmp_path / D.ARTIFACT)
    return D.Pipe3(xs, Link(sd, clock=clock.now), clock=clock.now, sleep=mod.sleep), out, mod


def test_a_clean_run_records_every_part_and_the_rate60_window(tmp_path, short_windows):
    pipe, out, mod = make_pipe(tmp_path)
    pipe.run()
    assert out["phase_errors"] == {}, out["phase_errors"]
    assert out["pass2_run"] == D.PASS2_RUN and out["mode"] == "append"
    for r in (5, 10, 15):
        rows = out["readings"]["scans"][str(r)]
        n = math.ceil((2 * r + 1) ** 2 / 60)
        assert len(rows) == 5 and all("error" not in s for s in rows), rows[0]
        for s in rows:
            assert s["parts"] == n and s["partNumbers"] == list(range(1, n + 1)) and s["done"] is True
            assert s["partStepMs"] == [1] * n and s["partEmitMs"] == [0] + [2] * (n - 1) and s["scanEmitMs"] == 2
            assert s["squares"] == (2 * r + 1) ** 2 and sum(s["partSquares"]) == s["squares"]
            assert len(s["partBytes"]) == n and sum(s["partBytes"]) == s["bytes"] and s["ack"]["reason"] == "queued"
            assert s["scanMs"] == n and s["scanTicks"] == n and s["scanStepMaxMs"] == 1
    assert [s["scanId"] for s in out["readings"]["scans"]["15"]] == list(range(11, 16))
    w = out["readings"]["rate60"]
    assert w["ack"]["ok"] and w["back_ack"]["ok"] and 0 <= w["frames"] - 120 <= 60 * D.AP2.POLL_S + 2 and w["tick_none"] == 0
    assert w["tick_mean_ms_at60"] == pytest.approx(0.6) and w["tick_sum"] == pytest.approx(0.6 * w["frames"])
    assert mod.rate == 10                                        # the window put back the rates phase's last rate
    out["client_lua_errors"] = 0
    g = G.gate_a(out)
    assert g["scan15_ms_max"] == 3 and g["scan15_latency_ms_max"] == 17 + 17 * 2 and g["pass"]["scan15"], g
    assert g["tick_mean_ms_at60"] == pytest.approx(0.6) and g["cmd_motion_n"] == 20
    assert {(100 + dx, 200 + dy, 0) for dx in range(-15, 16) for dy in range(-15, 16)} <= set(pipe.world.map)
    assert pipe.world.dropped_scans == 0


def test_the_rate60_window_is_the_mean_of_its_frames_quantised_costs(tmp_path, short_windows):
    pipe, out, mod = make_pipe(tmp_path, alt=(0, 1))             # actMs reads 0 on even ticks, 1 on odd
    pipe.wait_until(lambda: pipe.hello is not None, 5)
    pipe.phase_rate60()
    w = out["readings"]["rate60"]
    assert w["frames"] == len(w["tickMs"]) and 0 <= w["frames"] - 60 * D.RATE60_WINDOW_S <= 60 * D.AP2.POLL_S + 2   # from the ack's line, not its read
    assert w["tick_sum"] == pytest.approx(sum(w["tickMs"]))
    assert w["tick_mean_ms_at60"] == pytest.approx(w["tick_sum"] / w["frames"])
    assert w["tick_mean_ms_at60"] == pytest.approx(0.4 + 0.5, abs=0.02)   # 0.1 + 0.3 + mean(0, 1)
    assert sorted(set(w["tickMs"])) == [pytest.approx(0.4), pytest.approx(1.4)]
    assert w["wall_ms"] == w["frame_wallMs_last"] - w["frame_wallMs_first"]
    assert abs(w["wall_ms"] - (w["frames"] - 1) * 1000 / 60) <= 2 and mod.rate == D.RATE_BACK == 10


def test_a_frame_missing_a_cost_key_leaves_the_mean_unread(tmp_path, short_windows):
    class NoPoll(FakeMod3):
        def emit(self, kind, body):
            if kind == "frame" and self.rate == 60 and self.tick % 7 == 0:
                body["cost"].pop("pollMs")
            super().emit(kind, body)
    clock = T1.Clock()
    sd = str(tmp_path / "sd")
    mod = NoPoll(sd, clock)
    xs = X.Xs(D.new_out(), node=lambda side: side, clock=clock.now, sleep=mod.sleep, user="admin")
    pipe = D.Pipe3(xs, Link(sd, clock=clock.now), clock=clock.now, sleep=mod.sleep)
    pipe.wait_until(lambda: pipe.hello is not None, 5)
    pipe.phase_rate60()
    w = xs.out["readings"]["rate60"]
    assert w["tick_none"] > 0 and w["tick_mean_ms_at60"] is None and G.gate_a(xs.out)["tick_mean_ms_at60"] is None


def test_a_rate_back_without_its_ack_fails_the_phase_after_keeping_the_row(tmp_path, short_windows):
    class Deaf(FakeMod3):
        def poll(self):
            cmd = super().poll()
            if cmd and cmd["goal"] == "rate" and cmd["args"] == "10":
                self.rate = 10.0
                return None                                  # applied, never acked
            return cmd
    clock = T1.Clock()
    sd = str(tmp_path / "sd")
    mod = Deaf(sd, clock)
    xs = X.Xs(D.new_out(), node=lambda side: side, clock=clock.now, sleep=mod.sleep, user="admin")
    pipe = D.Pipe3(xs, Link(sd, clock=clock.now), clock=clock.now, sleep=mod.sleep)
    pipe.wait_until(lambda: pipe.hello is not None, 5)
    xs.run_phase("rate60", pipe.phase_rate60)
    assert "no ack for rate 10 back" in xs.out["phase_errors"]["rate60"]["error"]
    assert xs.out["readings"]["rate60"]["frames"] > 0 and xs.out["readings"]["rate60"]["back_ack"] is None


def test_a_replaced_scans_parts_are_not_counted_and_a_gap_is_an_error_row(tmp_path, short_windows):
    pipe, out, mod = make_pipe(tmp_path)
    pipe.wait_until(lambda: pipe.hello is not None, 5)
    row = pipe.one_scan(15)
    assert "error" not in row and row["scanId"] == 1

    class Gappy(FakeMod3):
        def emit(self, kind, body):
            if kind == "scanPart" and body["part"] == 3:
                self.seq += 1                                # part 3's line is lost: its seq is skipped
                return
            super().emit(kind, body)
    clock = T1.Clock()
    sd = str(tmp_path / "gap")
    mod2 = Gappy(sd, clock)
    xs = X.Xs(D.new_out(), node=lambda side: side, clock=clock.now, sleep=mod2.sleep, user="admin")
    pipe2 = D.Pipe3(xs, Link(sd, clock=clock.now), clock=clock.now, sleep=mod2.sleep)
    pipe2.wait_until(lambda: pipe2.hello is not None, 5)
    row = pipe2.one_scan(15)
    assert row["error"] == "parts not contiguous" and 3 not in row["partNumbers"] and row["parts"] == 17
    assert G.scan_part_tick_ms(row) is None                     # 16 parts against a 17-tick scan: the gate fails it


def test_world_replay_of_a_parts_log_matches_the_scans(tmp_path, short_windows):
    pipe, out, mod = make_pipe(tmp_path)
    pipe.wait_until(lambda: pipe.hello is not None, 5)
    pipe.one_scan(5)
    w = World()
    for l, _ in pipe.parts:
        w.apply(l)
    assert len(w.map) == 121 and w.dropped_scans == 0 and pipe.world.map == w.map
