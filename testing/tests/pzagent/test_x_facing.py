"""drivers/x_facing.py and driverlib/facing.py (Plan 32 Task 2, the facing trial driver, ruling P31-T), offline: the
driver is never invoked, the game never boots, the `claude` CLI is never called.

The static tests read the driver's refusal (its order before `main`, `parse_argv` over bad and good argvs), its
constants and the mode table against the schema's `probeMode` enum. The geometry (`cursor_bearing`, `target_point`)
runs on fixtures. The sequencer runs on the real `Actions` over a recording transport on a fake clock: the `Aim`
first, the twelve `Probe`s in order with the back vector, the 2 s rest on the fake clock between them, the zombie
spawn and its confirmation, the one closing `Stop`. The pre-boot checks run against the real profile and the
throwaway fixture records (conftest's `agent_fixture`), every machine reading injected."""
import json
import math
import os

import pytest

from agent.base import pza1
from agent.base.actions import Actions
from agent.driverlib import facing as F
from agent.driverlib import session as S
from agent.driverlib import trial as TR
from agent.drivers import x_facing as XF

ME = XF.__file__


# ================================================================ static: the refusal, the constants, the table
def test_the_driver_refuses_arguments_before_main_with_exit_2():
    src = open(ME, encoding="utf-8").read()
    i_ref = src.index("refusal = parse_argv(sys.argv[1:], __file__)")
    i_main = src.rindex("    main(flags(sys.argv[1:]), sys.argv[1:])")
    assert src.index('if __name__ == "__main__":') < i_ref < i_main
    assert "sys.exit(2)" in src[i_ref:i_main]
    assert XF.ALLOWED == ("--fixture", "--ticks", "--zombie", "--modes", "--minutes", "--detached")
    assert XF.parse_argv is F.parse_argv and XF.flags is F.flags
    for bad in (["--bogus"], ["--fix", "arena-east"], ["--variant", "ladder"], ["--waves", "lone"],
                ["--goals", "hold"], ["--no-llm"], ["--teleport", "1,2"], ["--make-fixture", "x"], ["x"], ["--help"],
                ["--fixture", "a", "--fixture", "b"], ["--fixture"], ["--ticks"], ["--ticks", "0"], ["--ticks", "x"],
                ["--ticks", "2.5"], ["--ticks", "-3"], ["--zombie", "--zombie"], ["--zombie", "x"],
                ["--modes"], ["--modes", "read,nope"], ["--modes", "read,read"], ["--modes", ""],
                ["--minutes", "0"], ["--minutes", "nan"], ["--minutes", "61"], ["--detached", "--detached"],
                ["--fixture", "../x"], ["--minutes", "7"]):
        r = XF.parse_argv(bad, ME)
        assert r and "x_facing.py" in r and "\n" not in r, bad
    for good in ([], ["--fixture", "arena-east"], ["--ticks", "60", "--zombie"], ["--modes", "read,snap_aimed"],
                 ["--minutes", "5"], ["--minutes", "9", "--detached"], ["--zombie", "--ticks", "120"],
                 ["--modes", "turn_k"]):
        assert XF.parse_argv(good, ME) is None, good


def test_the_flags_default_and_read():
    a = XF.flags([])
    assert a["fixture"] == "arena-east" and a["ticks"] == 60 and a["zombie"] is False and a["modes"] is None
    assert a["minutes"] == TR.DEFAULT_MINUTES and a["detached"] is False
    b = XF.flags(["--fixture", "agent", "--ticks", "30", "--zombie", "--modes", "read,turn_k", "--minutes", "2"])
    assert (b["fixture"], b["ticks"], b["zombie"], b["modes"], b["minutes"]) == (
        "agent", 30, True, ["read", "turn_k"], 2)


def test_the_constants_name_this_file_and_the_trial_profile():
    assert XF.KEY == "x_facing" and XF.DRIVER == "x_facing.py" and XF.ARTIFACT == "x_facing.json"
    assert XF.PROFILE == TR_PROFILE
    assert XF._ME == "x_facing.py"
    assert 'run_prefix=KEY' in open(ME, encoding="utf-8").read()
    # the bound is the trial's: the default stays under the foreground cap, a long one needs --detached
    assert TR.wall_bound(XF.flags([]))["launch"] == "foreground"
    assert TR.wall_bound(XF.flags(["--minutes", "9"]))["launch"] == "detached"


TR_PROFILE = "testing/profiles/agent.toml"


def test_the_mode_table_has_twelve_runs_over_the_schemas_mode_enum():
    assert len(F.MODES) == 12
    assert [m[0] for m in F.MODES] == ["read", "snap_aimed", "unaimed_face", "unaimed_snap", "block_aim",
                                       "ignore_aim", "turn_k", "turn_k", "read", "snap_aimed", "unaimed_face",
                                       "unaimed_snap"]
    assert {m[0] for m in F.MODES} <= set(pza1.PROBE_MODES) == set(pza1._ENUMS["probeMode"])
    assert [m[3] for m in F.MODES if m[0] == "turn_k"] == [3.0, 5.0]
    assert [i for i, m in enumerate(F.MODES) if m[1] is F.BACK] == [8, 9, 10, 11]
    assert all(m[1] is m[2] for m in F.MODES) and all(m[1] == 0 for m in F.MODES[:8])
    press = [i for i, m in enumerate(F.MODES) if m[0] in F.PRESS_MODES]
    assert F.PRESS_MODES == ("snap_aimed", "unaimed_snap") and press == [1, 3, 9, 11]


def test_the_modes_filter_keeps_order_and_both_movements():
    got = F.filter_modes(F.MODES, ["unaimed_snap", "read"])
    assert [(m[0], m[1] is F.BACK) for m in got] == [("read", False), ("unaimed_snap", False), ("read", True),
                                                      ("unaimed_snap", True)]
    assert F.filter_modes(F.MODES, None) == F.MODES


# ================================================================ the geometry
def frame(a):
    return {"me": {"aimAngle": a}}


def test_cursor_bearing_is_the_median_of_the_read_frames():
    assert F.cursor_bearing([frame(0.1), frame(None), frame(0.3), frame(0.2)]) == pytest.approx(0.2)
    assert F.cursor_bearing([frame(None), frame(None)]) is None
    assert F.cursor_bearing([]) is None
    # only the first 20 frames count
    assert F.cursor_bearing([frame(1.0)] * 20 + [frame(5.0)] * 30) == pytest.approx(1.0)
    # a bearing straddling +-pi reads as one bearing, not the median of two far values
    c = F.cursor_bearing([frame(math.pi - 0.01), frame(-math.pi + 0.01), frame(math.pi - 0.02)])
    assert abs(abs(c) - math.pi) < 0.03


def test_target_point_is_six_tiles_at_the_bearing_plus_a_quarter_turn():
    x, y = F.target_point({"x": 10.0, "y": 20.0}, 0.0)
    assert (x, y) == (pytest.approx(10.0, abs=1e-9), pytest.approx(26.0, abs=1e-9))
    x, y = F.target_point({"x": 10.0, "y": 20.0}, math.pi / 2)
    assert (x, y) == (pytest.approx(4.0, abs=1e-9), pytest.approx(20.0, abs=1e-9))
    x, y = F.target_point({"x": 0.0, "y": 0.0}, 0.0, dist=2.0)
    assert (x, y) == (pytest.approx(0.0, abs=1e-9), pytest.approx(2.0, abs=1e-9))


# ================================================================ the sequencer
class Wire:
    """A transport that records the commands it is sent."""

    def __init__(self):
        self.cmd_seq = 0
        self.sent = []

    def send(self, cmd):
        self.cmd_seq = cmd["seq"]
        self.sent.append(cmd)


class Clock:
    def __init__(self):
        self.t = 1000.0

    def __call__(self):
        return self.t


class FakeWorld:
    def __init__(self, x=10.0, y=20.0, aim=0.0):
        self.me = {"x": x, "y": y, "aimAngle": aim}
        self.zombies = {}


def done_line(aid, t="probe"):
    return {"kind": "act", "aid": aid, "type": t, "state": "done", "reason": "", "result": {}}


def make(tmp_path, spawn=None, zombie=False, ticks=60, modes=None, aim=0.0):
    clock, wire = Clock(), Wire()
    actions = Actions(wire, clock=clock)
    world = FakeWorld(aim=aim)
    spawned = []
    seq = F.ProbeSequencer(str(tmp_path / "decision.log"), clock, ticks=ticks, zombie=zombie, modes=modes,
                           spawn=spawn or (lambda x, y: spawned.append((x, y))))
    return seq, world, actions, clock, wire, spawned


def run_to_end(seq, world, actions, clock, wire, spawn_zombie=None, limit=400):
    """Tick at 10 Hz; every sent action ends done one tick after it is sent. Returns the list of what each tick sent."""
    sent, pending = [], []
    for _ in range(limit):
        clock.t += 0.1
        if pending:
            actions.pump([done_line(a.aid, a.type) for a in pending])
            pending = []
        a = seq.tick(world, actions)
        if spawn_zombie and not world.zombies and spawn_zombie.get("at"):
            x, y = spawn_zombie["at"]
            world.zombies[77] = {"x": x + 0.3, "y": y - 0.2, "dist": 6.0}
        if a is not None:
            sent.append(a)
            pending.append(a)
        if seq.finished:
            break
    return sent


def test_the_sequencer_sends_aim_first_then_the_twelve_probes_in_order_then_one_stop(tmp_path):
    seq, world, actions, clock, wire, spawned = make(tmp_path)
    sent = run_to_end(seq, world, actions, clock, wire)
    types = [a.type for a in sent]
    assert types == ["aim"] + ["probe"] * 12 + ["stop"]
    aim = wire.sent[0]["args"]
    assert (aim["vx"], aim["vy"], aim["seconds"], aim["targetId"]) == (0.0, 0.0, 2.0, -1)
    probes = [c["args"] for c in wire.sent if c["type"] == "probe"]
    assert [p["mode"] for p in probes] == [m[0] for m in F.MODES]
    assert all(p["ticks"] == 60 for p in probes)
    for p in probes[:8]:
        assert not p.get("vx") and not p.get("vy")
    assert [p.get("k") for p in probes if p["mode"] == "turn_k"] == [3.0, 5.0]
    for p in probes[8:]:
        assert p["vx"] == -1.0 and not p.get("vy")
    # c = 0: the target is six tiles along +y of the character at (10, 20)
    assert probes[0]["x"] == pytest.approx(10.0) and probes[0]["y"] == pytest.approx(26.0)
    assert seq.finished is True and spawned == []
    assert seq.cursor == pytest.approx(0.0) and seq.error is None
    assert [c["type"] for c in wire.sent].count("stop") == 1


def test_the_sequencer_rests_two_seconds_after_each_terminal_state(tmp_path):
    seq, world, actions, clock, wire, spawned = make(tmp_path, modes=["read"])
    sends, ends, pending = [], [], []
    for _ in range(300):
        clock.t += 0.1
        if pending:
            actions.pump([done_line(a.aid, a.type) for a in pending])
            ends.append(clock.t)                       # the act ended at this tick's clock (Actions stamps ended_wall)
            pending = []
        a = seq.tick(world, actions)
        if a is not None:
            sends.append((a.type, clock.t))
            pending.append(a)
        if seq.finished:
            break
    assert [t for t, _ in sends] == ["aim", "probe", "probe", "stop"]
    assert len(ends) == 3
    for end, (_, nxt) in zip(ends, sends[1:]):
        assert nxt - end >= 2.0 - 1e-6, (end, nxt)
        assert nxt - end < 2.0 + 0.25


def test_the_sequencer_does_not_send_a_probe_while_the_aim_runs(tmp_path):
    seq, world, actions, clock, wire, spawned = make(tmp_path)
    clock.t += 0.1
    a = seq.tick(world, actions)
    assert a.type == "aim"
    for _ in range(50):
        clock.t += 0.1
        assert seq.tick(world, actions) is None
    assert [c["type"] for c in wire.sent] == ["aim"]


def test_with_zombie_the_spawn_is_sent_confirmed_and_the_press_runs_carry_its_id(tmp_path):
    seq, world, actions, clock, wire, spawned = make(tmp_path, zombie=True)
    sent, pending = [], []
    for _ in range(600):
        clock.t += 0.1
        if pending:
            actions.pump([done_line(a.aid, a.type) for a in pending])
            pending = []
        if spawned and not world.zombies:
            world.zombies[77] = {"x": spawned[0][0] + 0.5, "y": spawned[0][1] + 0.5, "dist": 6.0}
        a = seq.tick(world, actions)
        if a is not None:
            sent.append(a)
            pending.append(a)
        if seq.finished:
            break
    assert len(spawned) == 1
    assert spawned[0] == (10, 26)                     # the target point floored
    probes = [c["args"] for c in wire.sent if c["type"] == "probe"]
    assert len(probes) == 12 and seq.finished
    for i, p in enumerate(probes):
        if F.MODES[i][0] in F.PRESS_MODES:
            assert p["targetId"] == 77, i
        else:
            assert p.get("targetId", -1) == -1, i


def test_with_zombie_an_unconfirmed_spawn_is_resent_once_then_the_run_ends_with_an_error(tmp_path):
    seq, world, actions, clock, wire, spawned = make(tmp_path, zombie=True)
    pending = []
    for _ in range(800):
        clock.t += 0.1
        if pending:
            actions.pump([done_line(a.aid, a.type) for a in pending])
            pending = []
        a = seq.tick(world, actions)
        if a is not None:
            pending.append(a)
        if seq.finished:
            break
    assert len(spawned) == 2 and seq.finished and "zombie" in (seq.error or "")
    assert [c["type"] for c in wire.sent if c["type"] == "probe"] == []


def test_no_cursor_bearing_ends_the_run_with_an_error(tmp_path):
    seq, world, actions, clock, wire, spawned = make(tmp_path, aim=None)
    run_to_end(seq, world, actions, clock, wire)
    assert seq.finished and "bearing" in (seq.error or "")
    assert not [c for c in wire.sent if c["type"] == "probe"]


def test_ticks_and_modes_set_the_plan(tmp_path):
    seq, world, actions, clock, wire, spawned = make(tmp_path, ticks=12, modes=["turn_k", "read"])
    run_to_end(seq, world, actions, clock, wire)
    probes = [c["args"] for c in wire.sent if c["type"] == "probe"]
    assert [(p["mode"], p["ticks"]) for p in probes] == [("read", 12), ("turn_k", 12), ("turn_k", 12), ("read", 12)] \
        or [p["mode"] for p in probes] == ["read", "turn_k", "turn_k", "read"]
    assert all(p["ticks"] == 12 for p in probes)


def test_the_decision_line_names_the_plan(tmp_path):
    seq, world, actions, clock, wire, spawned = make(tmp_path, modes=["read"])
    run_to_end(seq, world, actions, clock, wire)
    lines = [json.loads(ln) for ln in open(tmp_path / "decision.log", encoding="utf-8") if ln.strip()]
    assert lines and all(ln["branch"] == "probe" for ln in lines)
    sent = [ln for ln in lines if ln.get("aid") and ln.get("action", {}).get("type") == "probe"]
    assert [(s["plan_index"], s["mode"], s["move"]) for s in sent] == [(0, "read", "still"), (1, "read", "back")]
    assert sent[0]["cursor_bearing"] == pytest.approx(0.0) and sent[0]["target"] == [pytest.approx(10.0),
                                                                                     pytest.approx(26.0)]
    assert seq.last_branch == "probe"


# ================================================================ the pre-boot (the trial's, on the real profile)
def _preboot(monkeypatch, args, **kw):
    monkeypatch.setattr(S.DL.C, "doctor", lambda: (True, "ok  PZ java processes: none"))
    monkeypatch.setattr(S.DL.harness, "lint_paths", lambda srcs: [])
    kw.setdefault("free", lambda: 15.0)
    kw.setdefault("java_pids", lambda: [])
    return F.preboot(args, XF.PROFILE, **kw)


def test_preboot_on_the_real_profile_never_probes_the_model(agent_fixture, monkeypatch):
    def no_cli(*a, **k):
        raise AssertionError("the claude CLI is never called")
    args = XF.flags(["--fixture", "agent"])
    pre, ok = _preboot(monkeypatch, args, which=no_cli, run=no_cli)
    assert ok, pre
    assert pre["checks"]["fixture_ok"] and pre["checks"]["lint_clean"] and pre["checks"]["variant_ok"]
    assert "claude_ok" not in pre["checks"]
    pre, ok = _preboot(monkeypatch, XF.flags(["--fixture", "nope"]))
    assert not ok and pre["checks"]["fixture_ok"] is False
    pre, ok = _preboot(monkeypatch, args, java_pids=lambda: ["4242"])
    assert not ok and pre["checks"]["no_game_java"] is False


def test_the_trial_args_carry_the_keys_the_trial_boot_reads():
    a = XF.flags([])
    for k in ("variant", "fixture", "minutes", "no_llm", "goals", "waves", "teleport", "make_fixture", "detached"):
        assert k in a
    assert a["waves"] in TR.WAVE_PLANS and not TR.WAVE_PLANS[a["waves"]]["spawns"]
    assert a["make_fixture"] is None and a["teleport"] is None
    rec = TR.trial_record(a, {"commit": "c", "stamp": None, "dirty": False, "diff_sha256": None,
                              "provenance": "git"}, [], "t")
    assert rec["fixture"] == "arena-east"
