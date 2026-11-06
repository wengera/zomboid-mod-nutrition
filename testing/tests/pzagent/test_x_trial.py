"""drivers/x_trial.py and driverlib/trial.py (Plan 31 Task 6, the generic trial driver, ruling P31-T), offline: the
driver is never invoked, the game never boots, the `claude` CLI is never called.

The static tests read the driver's refusal (its order before `main` and `parse_argv` over bad and good argvs), its
constants and its imports. The pre-boot checks run against the real profile and throwaway fixture records (conftest's
`agent_fixture`), every machine reading injected. The boot (`trial.boot_and_run`) runs whole on a real run layout
(`pzt.paths.RUNS` pointed into tmp, the run dir made by `new_run_dir`) with `_dlib.boot`, the teardown and the kill
injected: the fake boot starts DayMod (test_e_day_24.py's, trimmed, its position moved by the teleport) under a
FakeServer whose `rcon` is the fake RCON (every command recorded in order) and FakeBus's replies; the session is the
library's `run_session` on the fake clock with InlinePolls (test_e_day_24.py's), so the loop stays single-threaded
but for the wave thread under test. `Survive` is wrapped so the `control=` keyword is recorded and passed on only
when Plan 31 Task 1's fork is on the tree."""
import inspect
import json
import os
import re
import types

import pytest

from agent.base.planner import survive as SV
from agent.base.planner.goals import ScriptedSource
from agent.base.planner.llm import LLMSource
from agent.base.planner.survive import Survive
from agent.driverlib import chain as CH
from agent.driverlib import day as DY
from agent.driverlib import polls as P
from agent.driverlib import session as S
from agent.driverlib import trial as TR
from agent.drivers import x_trial as XT
from .fakemod import DEFAULT_FRAME, FakeMod

REPO = S.REPO
X = S.X
KIT = S.DEFAULTS["KIT"]
KIT_ID = 5001
BAT = {"itemId": KIT_ID, "fullType": KIT, "weight": 1.5, "use": "weapon"}
FORK = "control" in inspect.signature(Survive.__init__).parameters     # Plan 31 Task 1's fork on this tree
ME = XT.__file__


# ================================================================ static: the refusal, the constants, the imports
def test_the_driver_refuses_arguments_before_main():
    src = open(ME, encoding="utf-8").read()
    i_ref = src.index("refusal = parse_argv(sys.argv[1:], __file__)")
    i_main = src.rindex("    main(flags(sys.argv[1:]), sys.argv[1:])")
    assert src.index('if __name__ == "__main__":') < i_ref < i_main
    assert "sys.exit(refusal)" in src[i_ref:i_main]
    assert XT.parse_argv is TR.parse_argv and XT.flags is TR.flags
    base = ["--variant", "ladder", "--fixture", "agent"]
    for bad in ([], ["x"], ["--help"], ["--variant", "ladder"], ["--fixture", "agent"], ["--variant"],
                base + ["--variant", "doctrine"], base + ["--no-llm", "--no-llm"], base + ["--no-llm", "x"],
                base + ["--session", "1"], base + ["--prev", "a.json"], base + ["--minutes"],
                base + ["--minutes", "0"], base + ["--minutes", "-1"], base + ["--minutes", "five"],
                base + ["--minutes", "nan"], base + ["--minutes", "inf"], base + ["--waves", "horde"],
                base + ["--teleport", "10750"], base + ["--teleport", "10750,10620,0"], base + ["--teleport", "a,b"],
                base + ["--make-fixture", "agent"], base + ["--make-fixture", "arena-east", "--waves", "lone"],
                base + ["--make-fixture", "arena-east", "--waves", "pair"], base + ["--make-fixture", "../x"],
                ["--variant", "Ladder", "--fixture", "agent"], ["--variant", "a-b", "--fixture", "agent"],
                ["--variant", "ladder", "--fixture", "../agent"], base + ["--waves", "lone", "x"]):
        r = XT.parse_argv(bad, ME)
        assert r and "x_trial.py" in r and "\n" not in r, bad
    for good in (base, base + ["--minutes", "5"], base + ["--minutes", "0.5"], base + ["--no-llm"],
                 ["--no-llm"] + base, base + ["--waves", "lone"], base + ["--waves", "pair"],
                 base + ["--waves", "street"], base + ["--teleport", "10750,10620"],
                 base + ["--teleport", "10750.5,-3"], base + ["--make-fixture", "arena-east"],
                 base + ["--teleport", "10750,10620", "--make-fixture", "arena-east", "--waves", "street",
                         "--minutes", "1", "--no-llm"]):
        assert XT.parse_argv(good, ME) is None, good
    assert XT.flags(base) == {"variant": "ladder", "fixture": "agent", "minutes": 5, "no_llm": False,
                              "waves": "street", "teleport": None, "make_fixture": None}
    assert XT.flags(base + ["--minutes", "0.5", "--no-llm", "--waves", "pair", "--teleport", "10750,10620.5",
                            "--make-fixture", "arena-east"]) == {
        "variant": "ladder", "fixture": "agent", "minutes": 0.5, "no_llm": True, "waves": "pair",
        "teleport": [10750, 10620.5], "make_fixture": "arena-east"}


def test_the_refusal_names_why():
    r = XT.parse_argv(["--variant", "ladder", "--fixture", "agent", "--make-fixture", "a", "--waves", "lone"], ME)
    assert r.startswith("x_trial.py takes only --variant <name> --fixture <name> [--minutes N] [--no-llm] "
                        "[--waves lone|pair|street] [--teleport X,Y] [--make-fixture <name>]; refused: ")
    assert "spawned zombies into the fixture" in r
    assert "(missing --fixture)" in XT.parse_argv(["--variant", "ladder"], ME)


def test_the_constants_name_the_drivers_own_file_key_artifact_and_profile():
    assert os.path.basename(ME) == XT.DRIVER == XT.KEY + ".py" == "x_trial.py"
    assert (XT.KEY, XT.PROFILE, XT.ARTIFACT) == ("x_trial", "testing/profiles/agent.toml", "x_trial.json")
    assert os.path.isfile(os.path.join(REPO, XT.PROFILE))
    assert TR.MIN_FREE_GB == S.DEFAULTS["MIN_FREE_GB"] == 10.0
    assert TR.DEFAULT_MINUTES == 5 and TR.DEFAULT_WAVES == "street" and TR.USER == "admin"
    src = open(ME, encoding="utf-8").read()
    assert ("TR.boot_and_run(args, lambda: TR.preboot(args, PROFILE), key=KEY, driver=DRIVER, artifact=ARTIFACT,"
            in src)
    imports = [l.split("#")[0].strip() for l in src.splitlines() if l.strip().startswith(("import ", "from "))]
    assert "import xlib as X" in imports and "from agent.driverlib import trial as TR" in imports
    assert not [l for l in imports if "drivers" in l or re.search(r"\b(e_day|f_goals)_\d+", l)], imports


def test_the_trial_library_never_copies_into_the_artifacts_nor_prints_next_steps():
    """No auto-copy (the code, past the docstring, calls none of copy_run, copy_artifacts, copy_state_logs,
    copy_shots_index or next_steps) and no grade."""
    import ast
    tree = ast.parse(open(TR.__file__, encoding="utf-8").read())
    docs = {id(n.body[0].value) for n in ast.walk(tree)
            if isinstance(n, (ast.Module, ast.FunctionDef, ast.ClassDef)) and n.body
            and isinstance(n.body[0], ast.Expr) and isinstance(n.body[0].value, ast.Constant)}
    names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)} | {
        n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)}
    strings = [n.value for n in ast.walk(tree) if isinstance(n, ast.Constant) and isinstance(n.value, str)
               and id(n) not in docs]
    for name in ("copy_run", "copy_artifacts", "copy_state_logs", "copy_shots_index", "next_steps", "grade",
                 "grade_fn", "driver_checks"):
        assert name not in names, name
    assert not [s for s in strings if "artifacts" in s], strings


def test_the_rcon_forms_live_in_one_constant_each():
    assert TR.TELEPORT_CMD.format(user="admin", x=10750, y=10620, z=0) == 'teleportto "admin" 10750,10620,0'
    assert TR.TELEPORT_TAG == "setup_tp"
    assert TR.CREATEHORDE2_CMD.format(x=108, y=200, z=0, count=1, radius=1) == (
        "createhorde2 -x 108 -y 200 -z 0 -count 1 -radius 1")
    src = open(TR.__file__, encoding="utf-8").read()
    assert src.count("teleportto ") == 1 and src.count("createhorde2 -x") == 1


# ================================================================ the waves
def test_the_wave_square_is_the_position_plus_the_distance_at_the_bearing():
    assert TR.wave_square((100.0, 200.0), 8.0, 0.0) == (108, 200)
    assert TR.wave_square((100.0, 200.0), 8.0, 90.0) == (100, 208)
    assert TR.wave_square((100.0, 200.0), 8.0, 180.0) == (92, 200)
    assert TR.wave_square((100.0, 200.0), 8.0, -90.0) == (100, 192)
    # 35 degrees: 8 cos 35 = 6.553, 8 sin 35 = 4.589; the square is the floor of the point
    assert TR.wave_square((100.5, 200.5), 8.0, 35.0) == (107, 205)
    assert TR.wave_square((100.5, 200.5), 8.0, -35.0) == (107, 195)
    assert TR.wave_square((10764.2, 10617.9), 15.0, 45.0) == (10774, 10628)


def test_the_plans_spawn_as_named():
    assert TR.WAVE_PLANS["lone"] == {"period_s": 60.0, "spawns": ((1, 8.0, 0.0),)}
    pair = TR.WAVE_PLANS["pair"]
    assert pair["period_s"] == 90.0 and [s[:2] for s in pair["spawns"]] == [(1, 8.0), (1, 8.0)]
    assert abs(pair["spawns"][1][2] - pair["spawns"][0][2]) == 70.0
    assert TR.WAVE_PLANS["street"] == {"period_s": None, "spawns": ()}


def _waves(plan, pos=(100.0, 200.0)):
    sent = []
    w = TR.Waves(plan, lambda cmd, tag: sent.append((cmd, tag)) or {"ok": True, "reply": "ok"}, lambda: pos)
    return w, sent


def test_lone_fires_one_zombie_at_8_tiles_at_the_start_then_every_60_s():
    w, sent = _waves("lone")
    w.begin(1000.0)
    assert len(w.step(1000.0)) == 1
    assert sent == [("createhorde2 -x 108 -y 200 -z 0 -count 1 -radius 1", "wave_0_0")]
    assert w.step(1000.0) == [] and w.step(1059.9) == []
    assert len(w.step(1060.0)) == 1 and w.step(1061.0) == [] and len(w.step(1120.5)) == 1
    assert [t for _, t in sent] == ["wave_0_0", "wave_1_0", "wave_2_0"]
    r = w.rows
    assert [x["t"] for x in r] == [0.0, 60.0, 120.5] and r[2]["lateS"] == 0.5 and r[2]["missed"] == 0
    assert r[0]["from"] == [100.0, 200.0] and r[0]["at"] == [108, 200] and r[0]["ack"] == {"ok": True, "reply": "ok"}
    # a late pass fires the latest boundary's wave, never the missed ones in a burst, and the next is the next boundary
    assert len(w.step(1310.0)) == 1 and w.rows[-1]["wave"] == 5 and w.rows[-1]["lateS"] == 10.0
    assert w.rows[-1]["missed"] == 2                                       # waves 3 and 4 skipped
    assert w.step(1359.0) == [] and len(w.step(1360.0)) == 1 and w.rows[-1]["wave"] == 6


def test_pair_fires_two_at_8_tiles_70_degrees_apart_every_90_s():
    w, sent = _waves("pair")
    w.begin(0.0)
    assert len(w.step(0.0)) == 2
    assert sent == [("createhorde2 -x 106 -y 195 -z 0 -count 1 -radius 1", "wave_0_0"),
                    ("createhorde2 -x 106 -y 204 -z 0 -count 1 -radius 1", "wave_0_1")]
    assert w.step(89.0) == [] and len(w.step(90.0)) == 2 and w.step(170.0) == [] and len(w.step(180.0)) == 2
    assert [r["bearing"] for r in w.rows[:2]] == [-35.0, 35.0]


def test_street_spawns_nothing_and_starts_no_thread():
    w, sent = _waves("street")
    w.start()
    assert w.started is True and w._thread is None and w.step(1e9) == [] and sent == []
    w.stop()
    assert w.record() == {"plan": "street", "period_s": None, "spawns": [], "started": True, "rows": [],
                          "error": None, "joined": None}


def test_a_wave_without_a_frame_position_is_recorded_skipped():
    w, sent = _waves("lone", pos=None)
    w.begin(0.0)
    rows = w.step(0.0)
    assert sent == [] and rows[0]["skipped"] == "no frame position" and rows[0]["cmd"] is None


def test_the_wave_thread_fires_the_first_wave_at_once_and_stops_on_its_join():
    sent = []
    w = TR.Waves("lone", lambda cmd, tag: sent.append(tag) or {"ok": True}, lambda: (1.0, 2.0), poll_s=0.01)
    w.start()
    for _ in range(500):
        if sent:
            break
        import time
        time.sleep(0.01)
    w.stop()
    assert sent == ["wave_0_0"] and w.joined is True and w.error is None and not w._thread.is_alive()


def test_a_wave_fault_ends_the_waves_never_the_loop():
    def boom(cmd, tag):
        raise RuntimeError("socket")
    w = TR.Waves("lone", boom, lambda: (1.0, 2.0), poll_s=0.01)
    w.start()
    w._thread.join(5)
    w.stop()
    assert w.error == "RuntimeError: socket" and w.joined is True


# ================================================================ provenance, trial.json, the switches
def test_provenance_reads_the_snapshot_stamp_when_present(tmp_path):
    stamp = {"commit": "a" * 40, "dirty": True, "diff_sha256": "b" * 64, "made_at": "2026-11-05T18:00:00"}
    (tmp_path / TR.STAMP).write_text(json.dumps(stamp), encoding="utf-8")

    def no_git(*a):
        raise AssertionError("git is never asked beside a stamp")
    p = TR.provenance(str(tmp_path), git=no_git)
    assert p == {"commit": "a" * 40, "stamp": stamp, "dirty": True, "diff_sha256": "b" * 64, "provenance": "stamp",
                 "diff": None}
    (tmp_path / TR.STAMP).write_text("{nope", encoding="utf-8")
    p = TR.provenance(str(tmp_path), git=no_git)
    assert p["provenance"] == "stamp" and p["commit"] is None and "error" in p["stamp"]


def test_provenance_reads_git_over_the_sessions_paths_without_a_stamp(tmp_path):
    asked = []

    def git(repo, *args):
        asked.append(args)
        if args[0] == "rev-parse":
            return 0, b"c" * 40 + b"\n"
        if args[0] == "status":
            return 0, b" M testing/agent/base/planner/survive.py\n"
        return 0, b"diff --git a/x b/x\n+1\n"
    p = TR.provenance(str(tmp_path), git=git)
    import hashlib
    assert p["commit"] == "c" * 40 and p["dirty"] is True and p["provenance"] == "git" and p["stamp"] is None
    assert p["diff"] == "diff --git a/x b/x\n+1\n"
    assert p["diff_sha256"] == hashlib.sha256(b"diff --git a/x b/x\n+1\n").hexdigest()
    assert asked[1] == ("status", "--porcelain", "--") + TR.SESSION_PATHS
    assert asked[2] == ("diff", "HEAD", "--") + TR.SESSION_PATHS
    clean = TR.provenance(str(tmp_path), git=lambda repo, *a: (0, b"d" * 40) if a[0] == "rev-parse" else (0, b""))
    assert clean["dirty"] is False and clean["diff"] is None and clean["diff_sha256"] is None
    broken = TR.provenance(str(tmp_path), git=lambda repo, *a: (128, b""))
    assert broken["commit"] is None and broken["dirty"] is None


def test_provenance_on_this_tree_names_its_head():
    p = TR.provenance(REPO)
    if p["provenance"] == "git":
        assert p["commit"] and re.match(r"^[0-9a-f]{40}$", p["commit"]) and p["dirty"] in (True, False)


def test_the_switches_are_every_t_tuple_read_off_the_planner():
    sv = types.SimpleNamespace(CORNER_BREAK=False, SWING_CLOSE=True)
    sw = TR.switches(sv)
    names = [n for k in sorted((int(m.group(1)), k) for k in dir(SV) for m in [TR.SWITCH_RX.match(k)] if m)
             for n in getattr(SV, k[1])]
    assert list(sw) == names and names[0] == "CORNER_BREAK" and "SWING_CLOSE" in names
    assert sw["CORNER_BREAK"] is False and sw["SWING_CLOSE"] is True and sw["DOOR_HELD"] is None


# ================================================================ pre-boot
class Proc:
    def __init__(self, stdout="", returncode=0, stderr=""):
        self.stdout, self.returncode, self.stderr = stdout, returncode, stderr


CONTROL = types.SimpleNamespace(CONTROLS=("ladder",), load=lambda name: (_ for _ in ()).throw(
    ValueError("unknown control %r" % name)))      # planner/control.py's shape (Plan 31 Task 1): CONTROLS, load


class Forked:
    """A Survive stand-in whose constructor takes the fork's keyword (variant_check reads only the signature)."""

    def __init__(self, world, actions, log_path, clock=None, source=None, control="ladder"):
        pass


def _preboot(monkeypatch, args, **kw):
    monkeypatch.setattr(S.DL.C, "doctor", lambda: (True, "ok  PZ java processes: none"))
    monkeypatch.setattr(S.DL.harness, "lint_paths", lambda srcs: [])
    kw.setdefault("free", lambda: 15.0)
    kw.setdefault("java_pids", lambda: [])
    kw.setdefault("survive", Forked)
    kw.setdefault("control", CONTROL)
    return TR.preboot(args, XT.PROFILE, **kw)


def _no_cli(*a, **k):
    raise AssertionError("the claude CLI is never called under --no-llm")


def test_preboot_on_the_real_profile_without_the_model_never_probes(agent_fixture, monkeypatch):
    args = XT.flags(["--variant", "ladder", "--fixture", "agent", "--no-llm"])
    pre, ok = _preboot(monkeypatch, args, which=_no_cli, run=_no_cli)
    assert ok, pre
    assert pre["checks"] == {"profile_exists": True, "doctor_clean": True, "lint_clean": True, "memory": True,
                             "no_game_java": True, "fixture_ok": True, "variant_ok": True}
    assert pre["profile"] == "agent" and pre["free_gb"] == 15.0 and pre["java_pids"] == []
    assert pre["claude_available"]["error"] == "not probed: --no-llm" and pre["claude_version"] is None
    assert pre["claude_answers"]["ok"] is None and pre["claude_answers"]["error"] == "not probed: --no-llm"
    assert pre["variant"] == {"variant": "ladder", "fork": True, "ok": True, "error": None}


def test_preboot_with_the_model_probes_once_and_refuses_on_a_failed_probe(agent_fixture, monkeypatch):
    args = XT.flags(["--variant", "ladder", "--fixture", "agent"])
    calls = []

    def run(argv, **kw):
        calls.append(argv)
        if argv[-1] == "--version":
            return Proc("2.1.310 (Claude Code)\n")
        return Proc(json.dumps({"type": "result", "is_error": False, "result": "ok"}))
    pre, ok = _preboot(monkeypatch, args, which=lambda n: "C:/bin/claude.exe", run=run)
    assert ok, pre
    assert len(calls) == 2 and calls[0] == ["C:/bin/claude.exe", "--version"] and "-p" in calls[1]
    assert pre["checks"]["claude_ok"] is True and pre["claude_answers"]["ok"] is True
    assert pre["claude_version"] == "2.1.310 (Claude Code)"

    def limited(argv, **kw):
        if argv[-1] == "--version":
            return Proc("2.1.310 (Claude Code)\n")
        return Proc("", 1, "rate limited")
    pre, ok = _preboot(monkeypatch, args, which=lambda n: "C:/bin/claude.exe", run=limited)
    assert ok is False and pre["checks"]["claude_ok"] is False and "rate limited" in pre["claude_answers"]["error"]
    pre, ok = _preboot(monkeypatch, args, which=lambda n: None, run=_no_cli)
    assert ok is False and pre["claude_answers"]["error"] == "not probed: no CLI"


def test_preboot_refuses_each_failed_check(agent_fixture, monkeypatch):
    args = XT.flags(["--variant", "ladder", "--fixture", "agent", "--no-llm"])
    kw = {"which": _no_cli, "run": _no_cli}
    assert _preboot(monkeypatch, args, free=lambda: 9.9, **kw)[1] is False
    assert _preboot(monkeypatch, args, free=lambda: None, **kw)[1] is False
    assert _preboot(monkeypatch, args, java_pids=lambda: ["4242"], **kw)[1] is False

    def unread():
        raise OSError("no powershell")
    pre, ok = _preboot(monkeypatch, args, java_pids=unread, **kw)
    assert ok is False and pre["java_pids"] is None and "no powershell" in pre["java_error"]
    pre, ok = _preboot(monkeypatch, XT.flags(["--variant", "ladder", "--fixture", "nope", "--no-llm"]), **kw)
    assert ok is False and pre["checks"]["fixture_ok"] is False and "nope" in pre["fixture_error"]
    pre, ok = _preboot(monkeypatch, args, survive=Survive if not FORK else type("Old", (), {
        "__init__": lambda self, world, actions, log_path, clock=None, source=None: None}), **kw)
    assert ok is False and pre["variant"]["fork"] is False and "Task 1" in pre["variant"]["error"]
    taken = XT.flags(["--variant", "ladder", "--fixture", "agent", "--no-llm", "--make-fixture", "agent0"])
    pre, ok = _preboot(monkeypatch, taken, **kw)
    assert ok is False and pre["checks"]["make_fixture_free"] is False
    free = XT.flags(["--variant", "ladder", "--fixture", "agent", "--no-llm", "--make-fixture", "arena-east"])
    pre, ok = _preboot(monkeypatch, free, **kw)
    assert ok and pre["checks"]["make_fixture_free"] is True
    monkeypatch.setattr(S.DL.C, "doctor", lambda: (False, "FAIL ports in use"))
    monkeypatch.setattr(S.DL.harness, "lint_paths", lambda srcs: [])
    assert TR.preboot(args, XT.PROFILE, free=lambda: 15.0, java_pids=lambda: [], survive=Forked, control=CONTROL,
                      **kw)[1] is False


def test_an_unknown_variant_refuses_the_boot_once_the_fork_is_on_the_tree():
    r = TR.variant_check("no_such_variant_xyz", survive=Forked, control=CONTROL)
    assert r == {"variant": "no_such_variant_xyz", "fork": True, "ok": False,
                 "error": "ValueError: unknown control 'no_such_variant_xyz'"}
    assert TR.variant_check("ladder", survive=Forked, control=CONTROL)["ok"] is True
    loaded = []
    stub = types.SimpleNamespace(CONTROLS=("ladder",), load=loaded.append)
    assert TR.variant_check("doctrine", survive=Forked, control=stub)["ok"] is True and loaded == ["doctrine"]


# ================================================================ the fake session: DayMod, FakeServer, FakeBus
class Clock:
    def __init__(self):
        self.t = 1_790_000_000.0

    def now(self):
        return self.t


class DayMod(FakeMod):
    """test_e_day_24.py's DayMod trimmed: one frame a tick at 10 Hz on the shared clock, the character at `pos` (moved
    by `teleport`), equip wields the bat, attack rejected, every other type accepted and done."""

    def __init__(self, d, clock, items=(), pos=(100.0, 200.0)):
        super().__init__(d, clock=clock.now)
        self.clk, self.t0 = clock, clock.t
        self.hz = 10
        self.pos = list(pos)
        self.weapon = None
        self.pending, self.cmd_seen, self.cmds = [dict(i) for i in items], 0, []
        self.hello(mode="append")
        self.next_t = clock.t
        self._tick()
        self.next_t += 1.0 / self.hz

    def s(self):
        return self.clk.t - self.t0

    def sleep(self, dt):
        end = self.clk.t + dt
        while self.next_t <= end + 1e-9:
            self.clk.t = self.next_t
            self._tick()
            self.next_t += 1.0 / self.hz
        self.clk.t = max(self.clk.t, end)

    def _poll(self):
        p = os.path.join(self.dir, "cmd.txt")
        if not os.path.isfile(p):
            return
        with open(p, encoding="utf-8") as f:
            cmd = json.loads(f.read())
        if cmd["seq"] <= self.cmd_seen:
            return
        self.cmd_seen = cmd["seq"]
        self.cmds.append(cmd)
        t, aid = cmd["type"], cmd["aid"]
        if t == "attack":
            self.act(aid, "rejected", t, reason="no target")
            return
        self.act(aid, "accepted", t)
        if t == "equip":
            self.weapon = {"type": KIT, "cond": 1.0, "reach": 1.125, "ammo": None}
        self.act(aid, "done", t, result={})

    def _tick(self):
        self._poll()
        for ev in self.pending:
            self.event("item_added", **ev)
        self.pending = []
        gmin = 480.0 + self.s() * 16.0 / 60.0
        self.frame(gameMin=gmin, worldAge=8.0 + (gmin - 480.0) / 60.0, weapon=self.weapon, zombies=[],
                   me=dict(DEFAULT_FRAME["me"], x=self.pos[0], y=self.pos[1]))


class FakeServer:
    """The fake RCON: every command recorded in `calls` in order; teleportto moves the fake mod's character."""

    def __init__(self, mod, calls):
        self.mod, self.calls, self.errors = mod, calls, []

    def rcon(self, cmd):
        self.calls.append(("rcon", cmd))
        m = re.match(r'^teleportto "admin" (-?[\d.]+),(-?[\d.]+),(-?[\d.]+)$', cmd)
        if m:
            self.mod.pos = [float(m.group(1)), float(m.group(2))]
            return True, "admin teleported to %s" % cmd.split(" ", 2)[2]
        if cmd.startswith("createhorde2 "):
            return True, "Horde spawned."
        return False, "unknown command"


class FakeBus:
    """test_e_day_24.py's FakeBus, its happy path (stats.all, players, damage.watch, item.get, ping)."""

    def __init__(self, mod):
        self.mod = mod

    def ask(self, node, cmd, args, timeout=30):
        self.mod.sleep(0.05)
        if cmd == "ping":
            return "pong"
        if cmd == "item.get":
            return {"fullType": KIT, "id": KIT_ID, "uses": 1, "age": 0, "weight": 1.5}
        if cmd == "stats.all":
            return {"side": "server", "user": args, "worldAge": 8.0, "mult": 1.0, "wall": 1,
                    "stats": {"Hunger": 0.11, "Thirst": 0.1, "Fatigue": 0.05}, "missing": {}}
        if cmd == "players":
            return ["admin"]
        if cmd == "damage.watch":
            return {"ok": True, "side": "server", "hooked": True, "user": args.split()[0], "counts": {}, "n": 0,
                    "last": {}, "dropped": 0}
        return {"error": "unknown command " + cmd}


class InlinePolls(P.PollThread):
    """test_e_day_24.py's InlinePolls: `latest(name)` first runs that read when it is due, on the caller's thread."""

    def start(self):
        self.started = True

    def latest(self, name):
        self.run_due(only=name)
        return super().latest(name)


def _survive_recording(monkeypatch):
    """TR.Survive wrapped: each construction's `control` recorded, passed on only when the fork is on the tree."""
    seen = []

    def make(*a, **kw):
        seen.append(kw.get("control", "<absent>"))
        if not FORK:
            kw.pop("control", None)
        return Survive(*a, **kw)
    monkeypatch.setattr(TR, "Survive", make)
    return seen


def boot_trial(tmp_path, monkeypatch, argv, prov=None):
    """trial.boot_and_run on the real profile and a real run layout with the boot, the teardown and the kill injected
    (the module docstring); the fake RCON's calls and the snapshot's argv land in one ordered list."""
    clock = Clock()
    calls = []
    runs = tmp_path / "runs"
    from pzt import paths as PZ
    monkeypatch.setattr(PZ, "RUNS", str(runs))
    monkeypatch.setattr(S.DL, "wait_memory", lambda g: (True, [{"wall": 0, "free_gb": 15.0}]))
    monkeypatch.setattr(X, "free_gb", lambda: 15.0)
    monkeypatch.setattr(X, "java_gb", lambda: {"pids": [], "gb": 0.0, "each": []})
    monkeypatch.setattr(S.DL, "time", types.SimpleNamespace(time=clock.now))
    monkeypatch.setattr(DY, "copy_run", lambda *a, **k: pytest.fail("copy_run is never called by a trial"))
    monkeypatch.setattr(X.Xs, "copy_artifacts", lambda *a, **k: pytest.fail("no artifact copy in a trial"))
    seen = _survive_recording(monkeypatch)
    got = {}

    def boot(xs, prof, rec_fx, run_dir, users, started, clients, holder, make_client=None):
        cache = tmp_path / "client-cache"
        client = types.SimpleNamespace(cache=str(cache), username="admin", seen={}, alive=True, proc=None,
                                       console=str(tmp_path / "console.txt"))
        mod = DayMod(os.path.join(str(cache), "Lua", "pzagent", "admin"), clock, items=[BAT])
        srv = FakeServer(mod, calls)
        holder["server"], xs.server = srv, srv
        xs.ask, xs.node, xs.sleep = FakeBus(mod).ask, (lambda side: side), mod.sleep
        clients["admin"] = client
        started.append(client)
        got.update(mod=mod, xs=xs, run_dir=run_dir)
        return {"verify": [{"ok": True}], "build": "42.21.0"}

    def run_session_fn(xs, transport, pre, note):
        sess = TR.run_session(args, xs, transport, pre, note, clock=clock.now, sleep=got["mod"].sleep,
                              free=lambda: 30.0, polls=InlinePolls(clock=clock.now))
        got["sess"] = sess
        return sess

    def snap(cmd, **kw):
        calls.append(("run", cmd))
        return Proc("FIXTURE snapshotted", 0)

    args = XT.flags(argv)
    out = TR.boot_and_run(args, lambda: ({"checks": {"ok": True}}, True), key=XT.KEY, driver=XT.DRIVER,
                          artifact=XT.ARTIFACT, profile=XT.PROFILE, argv=argv,
                          run_session_fn=run_session_fn, boot=boot, teardown=lambda tl, srv, cl: calls.append(
                              ("teardown",)), kill=lambda srv, every: None, run=snap,
                          provenance_fn=prov or (lambda repo: {"commit": "e" * 40, "stamp": None, "dirty": False,
                                                               "diff_sha256": None, "provenance": "git",
                                                               "diff": None}))
    return types.SimpleNamespace(out=out, calls=calls, seen=seen, clock=clock, run_dir=got["run_dir"],
                                 sess=got.get("sess"), mod=got["mod"], runs=runs, args=args)


# ================================================================ the boot on a real run layout
def test_a_trial_writes_trial_json_at_the_run_root_and_copies_nothing(tmp_path, monkeypatch, agent_fixture):
    argv = ["--variant", "ladder", "--fixture", "agent", "--minutes", "0.5", "--no-llm"]
    r = boot_trial(tmp_path, monkeypatch, argv)
    out = r.out
    assert out["phase_errors"] == {} and out.get("error") is None and out["stop"]["reason"] == "day_cap"
    assert out["stop"]["wallS"] == pytest.approx(30, abs=0.3) and out["finished"] is True
    run_id = os.path.basename(r.run_dir)
    assert re.match(r"^x_trial-ladder-\d{8}-\d{6}$", run_id) and os.path.dirname(r.run_dir) == str(r.runs)
    trial = json.loads(open(os.path.join(r.run_dir, "trial.json"), encoding="utf-8").read())
    assert tuple(trial) == TR.TRIAL_KEYS
    assert trial["variant"] == "ladder" and trial["fixture"] == "agent" and trial["minutes"] == 0.5
    assert trial["commit"] == "e" * 40 and trial["dirty"] is False and trial["stamp"] is None
    assert trial["provenance"] == "git" and trial["diff_sha256"] is None
    assert trial["waves"] == "street" and trial["wave_plan"] == {"period_s": None, "spawns": []}
    assert trial["no_llm"] is True and trial["teleport"] is None and trial["make_fixture"] is None
    assert trial["argv"] == argv and re.match(r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d$", trial["started_at"])
    assert trial["switches"] == TR.switches(r.sess.planner) and trial["switches"]["SWING_CLOSE"] is True
    assert json.loads(json.dumps(out["trial"])) == trial
    assert r.seen == ["ladder"]                                       # Survive(control="ladder")
    assert isinstance(r.sess, TR.TrialChain) and isinstance(r.sess.planner.goals.source, ScriptedSource)
    assert r.sess.lim["DAY_CAP_S"] == 30.0 and out["constants"]["BUDGET_S"] == 330.0
    assert out["driver_commit"] == "e" * 40 and out["session_key"] == "x_trial" and out["driver"] == "x_trial.py"
    # no auto-copy (copy_run and copy_artifacts fail the test if called): nothing under this tree's artifacts
    assert not os.path.exists(os.path.join(REPO, "testing", "artifacts", run_id))
    assert "make_fixture" not in out and "llm" not in out["loop"]
    assert out["loop"]["trial"] == {"teleport": None, "waves": {"plan": "street", "period_s": None, "spawns": [],
                                                                "started": True, "rows": [], "error": None,
                                                                "joined": None}}
    assert r.calls == [("teardown",)]                                  # no RCON on the street, no snapshot
    persisted = json.loads(open(os.path.join(r.run_dir, "x_trial.json"), encoding="utf-8").read())
    assert persisted["finished"] is True and persisted["trial"]["variant"] == "ladder"
    json.dumps(out, allow_nan=False, default=str)


def test_a_dirty_tree_saves_its_diff_beside_trial_json(tmp_path, monkeypatch, agent_fixture):
    prov = {"commit": "f" * 40, "stamp": None, "dirty": True, "diff_sha256": "0" * 64, "provenance": "git",
            "diff": "diff --git a/x b/x\r\n+1\n"}
    r = boot_trial(tmp_path, monkeypatch, ["--variant", "ladder", "--fixture", "agent", "--minutes", "0.1",
                                           "--no-llm"], prov=lambda repo: prov)
    trial = json.loads(open(os.path.join(r.run_dir, "trial.json"), encoding="utf-8").read())
    assert trial["dirty"] is True and trial["diff_sha256"] == "0" * 64 and "diff" not in trial
    with open(os.path.join(r.run_dir, "trial.diff"), encoding="utf-8", newline="") as fh:
        assert fh.read() == prov["diff"]


def test_the_lone_wave_spawns_at_the_square_off_the_last_frame(tmp_path, monkeypatch, agent_fixture):
    r = boot_trial(tmp_path, monkeypatch, ["--variant", "ladder", "--fixture", "agent", "--minutes", "0.2",
                                           "--no-llm", "--waves", "lone"])
    rcon = [c for c in r.calls if c[0] == "rcon"]
    assert rcon == [("rcon", "createhorde2 -x 108 -y 200 -z 0 -count 1 -radius 1")]   # wave 0 at once; 12 s < 60
    w = r.out["loop"]["trial"]["waves"]
    assert w["plan"] == "lone" and w["started"] is True and w["joined"] is True and w["error"] is None
    assert len(w["rows"]) == 1 and w["rows"][0]["at"] == [108, 200] and w["rows"][0]["ack"]["ok"] is True
    steps = [s for s in r.out["steps"] if s.get("cmd") == "rcon"]
    assert [s["step"] for s in steps] == ["wave_0_0"]
    # the wave thread started on the loop's first frame, never before the loop
    assert r.sess.waves.t0 >= r.sess.t_loop0


def test_the_fixture_making_path_teleports_then_snapshots_in_order(tmp_path, monkeypatch, agent_fixture):
    argv = ["--variant", "ladder", "--fixture", "agent", "--minutes", "0.2", "--no-llm", "--teleport", "10750,10620",
            "--make-fixture", "arena-east"]
    r = boot_trial(tmp_path, monkeypatch, argv)
    snap = CH.snapshot_cmd(r.run_dir, "arena-east", "agent", 1)
    assert r.calls == [("rcon", 'teleportto "admin" 10750,10620,0'), ("teardown",), ("run", snap)]
    assert snap[-8:] == ["--from-run", r.run_dir, "--name", "arena-east", "--parent", "agent", "--session", "1"]
    tp = r.out["loop"]["trial"]["teleport"]
    assert tp["cmd"] == 'teleportto "admin" 10750,10620,0' and tp["ack"]["ok"] is True and tp["arrived"] is True
    assert tp["pos"] == [10750.0, 10620.0]
    steps = [s for s in r.out["steps"] if s.get("cmd") == "rcon"]
    assert [s["step"] for s in steps] == ["setup_tp"] and steps[0]["phase"] == "loop"
    # the teleport was read before the loop began: the loop's first kept frame is at the new square
    assert r.sess.first_frame["me"]["x"] == 100.0                          # the hello-phase first frame: before it
    mf = r.out["make_fixture"]
    assert mf == {"name": "arena-east", "cmd": snap, "ran": True, "exit": 0, "output": "FIXTURE snapshotted",
                  "skipped": None, "error": None}
    trial = json.loads(open(os.path.join(r.run_dir, "trial.json"), encoding="utf-8").read())
    assert trial["teleport"] == [10750, 10620] and trial["make_fixture"] == "arena-east"


def test_make_fixture_skips_a_session_that_did_not_end_at_its_cap():
    args = XT.flags(["--variant", "ladder", "--fixture", "agent", "--teleport", "1,2", "--make-fixture", "a1"])

    def never(*a, **k):
        raise AssertionError("no snapshot")
    ok_tp = {"loop": {"trial": {"teleport": {"arrived": True}}}}
    assert "stopped death" in TR.make_fixture(dict(ok_tp, stop={"reason": "death"}), args, "r", never)["skipped"]
    assert "failed" in TR.make_fixture(dict(ok_tp, stop={"reason": "day_cap"}, error="X: y"), args, "r",
                                       never)["skipped"]
    assert "teleport" in TR.make_fixture({"stop": {"reason": "day_cap"}, "loop": {"trial": {"teleport": {
        "arrived": False}}}}, args, "r", never)["skipped"]
    r = TR.make_fixture(dict(ok_tp, stop={"reason": "day_cap"}), args, "r",
                        lambda cmd, **k: Proc("", 1, "refused: fixture 'a1' already exists"))
    assert r["ran"] is True and r["exit"] == 1 and "already exists" in r["output"]


def test_the_model_trial_builds_the_llm_source_and_its_record(tmp_path):
    args = XT.flags(["--variant", "ladder", "--fixture", "agent"])
    xs = types.SimpleNamespace(copied=[], out=S.new_out(), user="admin", path=str(tmp_path / "a.json"),
                               rcon=lambda cmd, tag: {"ok": True})
    seen = []

    def make(*a, **kw):
        seen.append(kw.get("control", "<absent>"))
        if not FORK:
            kw.pop("control", None)
        return Survive(*a, **kw)
    orig = TR.Survive
    TR.Survive = make
    try:
        c = TR.make_session(xs, None, args, cli_version="2.1", clock=lambda: 5.0)
    finally:
        TR.Survive = orig
    assert seen == ["ladder"] and isinstance(c, TR.TrialChain) and isinstance(c.planner.goals.source, LLMSource)
    assert c.planner.goals.source.log_path == str(tmp_path / "goals.log")
    assert c.lim["DAY_CAP_S"] == 300.0 and c.lim["PLANNER_HZ"] == 2
    rec = c.extra_record()
    assert rec["llm"]["model"] == TR.MODEL and rec["llm"]["cli_version"] == "2.1" and rec["llm"]["calls"] == []
    assert rec["trial"]["waves"]["plan"] == "street"


def test_the_planner_factory_passes_the_variant_as_control():
    """The fork's keyword: `Survive(..., control=<variant>)` in the factory's source, whatever the tree's Survive."""
    src = inspect.getsource(TR.planner_factory)
    assert "return Survive(world, actions, log_path, clock, source=source, control=variant)" in src
