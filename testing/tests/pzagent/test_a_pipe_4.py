"""drivers/a_pipe_4.py, grades.gate_a4 and drivers/a_grade_4.py (Plan 21b Stage A pass 4), offline: the driver is never
invoked.

The phases run against FakeMod3 (test_a_pipe_3: pass 3's scan in parts) and FakeMod4, a FakeMod3 whose goto walk first
steps 0.3 tiles west and 0.3 south (a detour, as every +x leg of pass 3 left the agent0 house westward) before it
walks toward its target: on a +x leg the first frame that moved at all comes well before the first frame 0.2 tiles
east of the start."""
import json
import math
import os

import pytest

from agent import grades as G
from agent.drivers import a_grade_4 as AG4
from agent.drivers import a_pipe_4 as D
from agent.link import Link
from . import test_a_pipe as T1
from . import test_a_pipe_3 as T3

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
    assert os.path.basename(D.__file__) == D.DRIVER == D.KEY + ".py" == "a_pipe_4.py"
    assert D.KEY == "a_pipe_4" and D.ARTIFACT == "a_pipe_4.json" and D.BUDGET_S == 800.0
    assert D.PROFILE == "testing/profiles/agent-nozombies.toml" and os.path.isfile(os.path.join(REPO, D.PROFILE))
    assert D.PASS3_RUN == "a_pipe_3-20261026-130558" and D.PASS3_RUN in D.__doc__
    assert D.MOVE_EPS_TILES == G.MOVE_EPS_TILES == 0.01 and D.CONSTANTS["MOVE_EPS_TILES"] == 0.01
    assert D.CONSTANTS["BUDGET_S"] == 800.0 and D.CONSTANTS["PASS3_RUN"] == D.PASS3_RUN
    assert D.CONSTANTS["inherited_from_a_pipe_3"]["RATE60_WINDOW_S"] == D.AP3.RATE60_WINDOW_S
    assert D.CONSTANTS["inherited_from_a_pipe_2"]["WINDOW_S"] == D.AP2.WINDOW_S
    assert "first_move" in D.__doc__ and "P21b-1" in D.__doc__


def test_the_frozen_drivers_are_imported_never_copied_over():
    src = open(D.__file__, encoding="utf-8").read()
    for name in ("a_pipe as AP", "a_pipe_2 as AP2", "a_pipe_3 as AP3"):
        assert "from agent.drivers import %s" % name in src
    assert issubclass(D.Pipe4, D.AP3.Pipe3) and D.AP3.KEY == "a_pipe_3"
    assert "make_client=AP.clearing_make_client(session.make_client)" in src
    assert "G.gate_a4(out)" in src and '"cmd_move_p90_ms"' in src


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
    tracked["v"] = "testing/artifacts/a_pipe_4-20261027-120000/a_pipe_4.json"
    assert D.preboot(D.__file__)[1] is False
    tracked["v"] = ""
    assert D.preboot(os.path.join(os.path.dirname(D.__file__), "a_pipe_3.py"))[1] is False


def test_driver_checks_refuse_a_dirty_lua_or_driver():
    say = lambda *a: ""
    c, ok = D.driver_checks(D.__file__, git_say=say, git_dirty=lambda rel: (False, ""))
    assert ok and c["no_committed_artifact"] is True
    for dirty in ("testing/PZAgent", "testing/agent/drivers/a_pipe_4.py"):
        c, ok = D.driver_checks(D.__file__, git_say=say, git_dirty=lambda rel, d=dirty: (rel == d, ""))
        assert ok is False, dirty


# ================================================================ first_move
def fr(seq, x, y, wall=None):
    return ({"seq": seq, "wallMs": wall if wall is not None else 1000 + seq, "x": x, "y": y}, 5000.0 + seq)


def test_first_move_is_the_first_frame_after_the_ack_off_the_start_in_any_direction():
    frames = [fr(1, 101.0, 200.0), fr(3, 100.0, 200.0), fr(4, 100.005, 200.005), fr(5, 99.99, 200.02), fr(6, 105, 200)]
    ack = {"ok": True, "seq": 2, "wallMs": 1002}
    assert D.first_move(frames, ack, 100.0, 200.0) == {"seq": 5, "wallMs": 1005, "x": 99.99, "y": 200.02,
                                                      "readPyMs": 5005.0}
    assert D.first_move(frames, ack, 100.0, 200.0, eps=0.1)["seq"] == 6      # the epsilon is the hypot, not one axis


@pytest.mark.parametrize("ack, x0", [(None, 100.0), ({"ok": False, "seq": 2, "reason": "dead"}, 100.0),
                                     ({"ok": True}, 100.0), ({"ok": True, "seq": 2}, None)])
def test_a_refused_unacked_or_unplaced_row_has_no_first_move(ack, x0):
    assert D.first_move([fr(3, 120.0, 200.0)], ack, x0, 200.0) is None


def test_a_leg_that_never_moves_has_no_first_move():
    assert D.first_move([fr(3, 100.0, 200.0), fr(4, 100.0, 200.0)], {"ok": True, "seq": 2}, 100.0, 200.0) is None


# ================================================================ the motion phase against FakeMod4
class FakeMod4(T3.FakeMod3):
    """FakeMod3 whose goto walk first steps (-0.05, +0.05) a tick for DETOUR ticks (0.3 tiles west and 0.3 south),
    then walks toward its target as FakeMod does."""
    DETOUR = 6

    def __init__(self, d, clock, **kw):
        super().__init__(d, clock, move_delay=3 + self.DETOUR, **kw)

    def step(self):
        g = self.goal
        detour = (g is not None and g["state"] == "running" and self.drift == 0
                  and self.move_delay - self.DETOUR <= g["ticks"] < self.move_delay)
        if detour:                     # this tick's base step increments ticks into the detour window
            self.x -= 0.05
            self.y += 0.05
        super().step()


def make_pipe(tmp_path, mod_cls=T3.FakeMod3, **flags):
    clock = T1.Clock()
    sd = str(tmp_path / "clients" / "admin" / "Lua" / "pzagent" / "admin")
    mod = mod_cls(sd, clock, **flags)
    out = D.new_out()

    def ask(node, cmd, args, timeout=30):
        mod.sleep(0.05)
        return {"ok": True, "user": args, "stats": {"HUNGER": 0.1}}

    xs = X.Xs(out, node=lambda side: side, ask=ask, clock=clock.now, sleep=mod.sleep, budget_s=1e9, user="admin")
    xs.path = str(tmp_path / D.ARTIFACT)
    return D.Pipe4(xs, Link(sd, clock=clock.now), clock=clock.now, sleep=mod.sleep), out, mod


@pytest.fixture
def short_windows(monkeypatch):
    monkeypatch.setattr(D.AP2, "WINDOW_S", 5.0)
    monkeypatch.setattr(D.AP3, "RATE60_WINDOW_S", 2.0)


def test_a_detour_leg_moves_first_and_reaches_the_commanded_direction_later(tmp_path):
    pipe, out, mod = make_pipe(tmp_path, mod_cls=FakeMod4)
    pipe.wait_until(lambda: pipe.hello is not None, 5)
    pipe.link.send("rate", "10")
    pipe.wait_until(lambda: mod.rate == 10, 5)
    row = pipe.one_goto(0, 10)
    assert row["goal"]["state"] == "done", row
    mv, mo = row["first_move"], row["first_motion"]
    assert mv is not None and mo is not None and mv["seq"] > row["ack"]["seq"]
    assert mv["seq"] < mo["seq"] and mv["wallMs"] < mo["wallMs"]
    assert mv["x"] < row["x0"] and mv["y"] > row["y0"]                    # the first moved frame is the detour
    assert math.hypot(mv["x"] - row["x0"], mv["y"] - row["y0"]) > D.MOVE_EPS_TILES
    assert mo["x"] - row["x0"] > D.AP2.MOTION_EPS                          # the directional reading is the later one
    assert set(mv) == {"seq", "wallMs", "x", "y", "readPyMs"}
    move_ms, motion_ms = G.cmd_move_ms([row])[0], G.cmd_motion_ms([row])[0]
    assert move_ms <= 100 and motion_ms >= move_ms + 200                  # ack to the detour's first frame; then east


def test_a_clean_run_carries_first_move_on_every_leg_and_grades_go(tmp_path, short_windows):
    pipe, out, mod = make_pipe(tmp_path)
    pipe.run()
    assert out["phase_errors"] == {}, out["phase_errors"]
    assert out["pass3_run"] == D.PASS3_RUN and out["pass2_run"] == D.AP3.PASS2_RUN
    legs = out["readings"]["motion"]
    assert len(legs) == 20 and all(r["first_move"] is not None and r["first_motion"] is not None for r in legs)
    assert all(r["first_move"]["seq"] <= r["first_motion"]["seq"] for r in legs)
    out["client_lua_errors"] = 0
    g = G.gate_a4(out)
    assert g["verdict"] == "GO" and all(g["pass"].values()), g
    assert g["cmd_move_n"] == g["cmd_move_paired"] == 20 and g["tick_mean_ms_at60"] == pytest.approx(0.6)
    assert g["tick60_frames"] == out["readings"]["rate60"]["frames"]


# ================================================================ gate_a4 arithmetic
def move_rows(n, ms=120, missing=0):
    rows = [{"ack": {"wallMs": 1000}, "first_move": {"wallMs": 1000 + ms}, "first_motion": {"wallMs": 9130}}
            for _ in range(n)]
    rows += [{"ack": {"wallMs": 1000}, "first_move": None, "first_motion": None} for _ in range(missing)]
    return rows


def passing_out4():
    o = T1.passing_out()
    o["readings"]["rate60"] = {"tick_mean_ms_at60": 0.48, "frames": 1803, "expected": 1800.0}
    o["readings"]["motion"] = move_rows(20)
    return o


def test_gate_a4_passes_a_passing_set_with_the_ungraded_readings_beside_it():
    o = passing_out4()
    o["readings"]["rates"]["5"]["tickMs"] = [2.0] * 300                # a p99 of 2: gate_a's fail, ungraded here
    g = G.gate_a4(o)
    assert g["verdict"] == "GO" and all(g["pass"].values()), g
    assert set(g["pass"]) == {"tick_mean_at60", "scan15", "cmd_move_p90", "gaps", "lua_errors", "hello"}
    assert g["tick_p99_ms_at5"] == 2.0 and g["cmd_motion_p90_ms"] == 8130
    assert "tick_p99_at5" not in g["pass"] and "cmd_motion_p90" not in g["pass"]
    assert G.gate_a(o)["verdict"] == "NO-GO"                            # the same artifact fails gate_a
    assert g["cmd_move_p90_ms"] == 120 and g["cmd_move_n"] == g["cmd_move_paired"] == 20
    assert g["tick_mean_ms_at60"] == 0.48 and g["tick60_frames"] == 1803
    assert set(G.gate_a(o)) <= set(g)


@pytest.mark.parametrize("rate60, ok", [
    ({"tick_mean_ms_at60": 0.48, "frames": 1803, "expected": 1800.0}, True),
    ({"tick_mean_ms_at60": 0.999, "frames": 1620, "expected": 1800.0}, True),
    ({"tick_mean_ms_at60": 1.2, "frames": 1803, "expected": 1800.0}, False),
    ({"tick_mean_ms_at60": 1.0, "frames": 1803, "expected": 1800.0}, False),
    ({"tick_mean_ms_at60": 0.48, "frames": 1619, "expected": 1800.0}, False),   # a short window
    ({"tick_mean_ms_at60": 0.48, "frames": 1803}, False),
    ({"tick_mean_ms_at60": None, "frames": 1803, "expected": 1800.0}, False),
    ({}, False),
])
def test_the_tick_gate_is_the_60_hz_mean_on_a_full_window(rate60, ok):
    o = passing_out4()
    o["readings"]["rate60"] = rate60
    g = G.gate_a4(o)
    assert g["pass"]["tick_mean_at60"] is ok and (g["verdict"] == "GO") is ok
    assert [k for k, v in g["pass"].items() if not v] == ([] if ok else ["tick_mean_at60"])


def test_the_move_gate_needs_twenty_legs_and_counts_a_missing_first_move_as_inf():
    o = passing_out4()
    assert G.gate_a4(o)["pass"]["cmd_move_p90"] is True
    o["readings"]["motion"] = move_rows(19)
    g = G.gate_a4(o)
    assert g["cmd_move_n"] == 19 and [k for k, v in g["pass"].items() if not v] == ["cmd_move_p90"]
    o["readings"]["motion"] = move_rows(19, missing=1)
    g = G.gate_a4(o)
    assert g["cmd_move_n"] == 20 and g["cmd_move_paired"] == 19 and g["cmd_move_p90_ms"] == 120
    assert G.cmd_move_ms(move_rows(0, missing=1)) == [math.inf]
    o["readings"]["motion"] = move_rows(17, missing=3)                  # rank 18 of 20 is an unpaired leg
    g = G.gate_a4(o)
    assert g["cmd_move_p90_ms"] == math.inf and g["pass"]["cmd_move_p90"] is False
    o["readings"]["motion"] = move_rows(20, ms=500)
    assert G.gate_a4(o)["pass"]["cmd_move_p90"] is False
    o["readings"]["motion"] = move_rows(20, ms=499)
    assert G.gate_a4(o)["pass"]["cmd_move_p90"] is True
    o["readings"]["motion"] = []
    assert G.gate_a4(o)["cmd_move_p90_ms"] is None and G.gate_a4(o)["pass"]["cmd_move_p90"] is False


def test_a_voided_leg_leaves_the_move_gate():
    o = passing_out4()
    o["readings"]["motion"] = move_rows(20) + [{"ack": {"wallMs": 1000}, "first_move": None, "voided": "dead"}]
    g = G.gate_a4(o)
    assert g["cmd_move_n"] == 20 and g["cmd_motion_voided"] == 1 and g["pass"]["cmd_move_p90"] is True


@pytest.mark.parametrize("name", ["scan15", "gaps", "lua_errors", "hello"])
def test_the_gates_kept_from_gate_a_still_fail_alone(name):
    o = passing_out4()
    if name == "scan15":
        o["readings"]["scans"]["15"] = []
    elif name == "gaps":
        o["gaps"] = [3]
    elif name == "lua_errors":
        o["client_lua_errors"] = 1
    else:
        o["mode"] = None
    g = G.gate_a4(o)
    assert [k for k, v in g["pass"].items() if not v] == [name] and g["verdict"] == "NO-GO"


# ================================================================ a_grade_4
def test_a_grade_4_exits_on_the_verdict(tmp_path, capsys):
    p = tmp_path / "a.json"
    p.write_text(json.dumps(passing_out4()))
    assert AG4.main([str(p)]) == 0
    assert json.loads(capsys.readouterr().out)["verdict"] == "GO"
    bad = passing_out4()
    bad["readings"]["rate60"]["tick_mean_ms_at60"] = 1.2
    p.write_text(json.dumps(bad))
    assert AG4.main([str(p)]) == 1
    assert json.loads(capsys.readouterr().out)["verdict"] == "NO-GO"
    assert AG4.main([]) == 2 and AG4.main([str(tmp_path / "none.json")]) == 2
    p.write_text("{not json")
    assert AG4.main([str(p)]) == 2
