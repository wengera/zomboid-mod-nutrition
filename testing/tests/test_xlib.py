"""Offline tests of testing/experiments/xlib.py (Plan 12 Task 4).

The fake bus answers the harness's real reply shapes, taken from the `@reply` comment lines of
testing/PZTestKit/PZTestKit/42/media/lua/: `ping` -> "pong" (shared/PZTestKit_Core.lua), `item.get` ->
{id, fullType, ...} or a string (server/PZTestKit_Server.lua), `eat.action` -> {queued, spawned, itemId,
...} (client/PZTestKit_Client.lua), `time.snapshot` -> {worldAge, hour, minutes, mult, trueMult, wall}
(shared/PZTestKit_Core.lua). A stalled read is what _common.ask returns for a wedged side:
{"error": "TimeoutError: ..."}.
"""
import json
import os
import re
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))                                  # testing/
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "experiments"))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(HERE)), "tools"))

import xlib as X                      # noqa: E402
from pzt.session import Timeline      # noqa: E402

TIMEOUT = {"error": "TimeoutError: no ack in 5 s"}


def fresh_out():
    return {"steps": [], "notes": [], "phase_walls": {}, "phase_errors": {}, "verdicts": {},
            "world_changes": {"left_in_place": []}}


class FakeAsk:
    """ask(node, cmd, args, timeout): scripted replies by (node, cmd); a list is consumed in order."""

    def __init__(self, script):
        self.script = {k: (list(v) if isinstance(v, list) else v) for k, v in script.items()}
        self.calls = []

    def __call__(self, node, cmd, args="", timeout=20):
        self.calls.append((node, cmd, args, timeout))
        r = self.script.get((node, cmd), {"error": "RuntimeError: no script"})
        if isinstance(r, list):
            r = r.pop(0) if len(r) > 1 else r[0]
        return r


class FakeServer:
    def __init__(self, rcon_ok=True):
        self.rcon_ok = rcon_ok
        self.cmds = []
        self.errors = []

    def rcon(self, cmd):
        self.cmds.append(cmd)
        return self.rcon_ok, "ok"


class Clock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now


def make(script, **kw):
    clock = Clock()
    ask = FakeAsk(script)
    xs = X.Xs(fresh_out(), node=lambda side: side, ask=ask, clock=clock, sleep=lambda s: None,
              server=kw.pop("server", FakeServer()), **kw)
    return xs, ask, clock


# ---------------------------------------------------------------- step, ping, dead bus
def test_step_success_records_the_row():
    xs, _, _ = make({("server", "time.snapshot"): {"worldAge": 5.0, "hour": 7, "minutes": 3, "mult": 1,
                                                    "trueMult": 1, "wall": 12}})
    s = xs.snap("t0")
    assert s["worldAge"] == 5.0 and xs.out["steps"][0]["cmd"] == "time.snapshot"
    assert xs.bus_dead is None


def test_ping_pong_keeps_the_bus_alive():
    xs, _, _ = make({("server", "ping"): "pong"})
    assert xs.ping("p") is True and xs.bus_dead is None


def test_timeout_then_pong_does_not_kill_the_bus():
    xs, _, _ = make({("server", "item.get"): TIMEOUT, ("server", "ping"): "pong"})
    r = xs.step("g", "server", "item.get", "admin Base.Apple")
    assert r["liveness_pong"] is True and xs.bus_dead is None


def test_timeout_without_pong_marks_the_bus_dead_and_raises():
    tl = Timeline()
    xs, _, _ = make({("server", "item.get"): TIMEOUT, ("server", "ping"): TIMEOUT}, tl=tl)
    with pytest.raises(X.BusDead):
        xs.step("g", "server", "item.get", "admin Base.Apple")
    assert xs.bus_dead == "g_liveness" and "server bus dead" in xs.out["abort"]
    assert tl.items[-1]["phase"] == "error"


def test_dead_bus_skips_later_server_steps_but_not_client_steps():
    xs, ask, _ = make({("client:admin", "eat.action"): {"spawned": "found"}})
    xs.mark_dead("x")
    r = xs.step("s", "server", "time.snapshot")
    assert r["skipped"] is True and ask.calls == []
    xs.step("c", "client:admin", "eat.action", "Base.Apple 1")
    assert len(ask.calls) == 1


def test_non_stalling_error_does_not_ping():
    xs, ask, _ = make({("server", "item.get"): "no item Base.Apple in admin's inventory"})
    r = xs.step("g", "server", "item.get", "admin Base.Apple")
    assert r["ack_shape"] == "str" and all(c[1] != "ping" for c in ask.calls)


# ---------------------------------------------------------------- budget
def test_check_passes_inside_the_budget():
    xs, _, clock = make({}, budget_s=100)
    clock.now += 10
    xs.check()


def test_check_stops_past_the_budget():
    xs, _, clock = make({}, budget_s=100)
    clock.now += 101
    with pytest.raises(X.Budget):
        xs.check()


def test_check_stops_when_admin_is_parked():
    xs, _, _ = make({})
    xs.clients = {"admin": type("C", (), {"seen": {"lua_error": 1}})()}
    with pytest.raises(X.Budget, match="parked"):
        xs.check()


# ---------------------------------------------------------------- run_phase
def test_run_phase_records_failed_phase_never_phase_kw():
    tl = Timeline()
    xs, _, _ = make({}, tl=tl)

    def boom():
        raise ValueError("bad")

    xs.run_phase("A", boom)          # would raise TypeError if mark got phase= twice
    err = [i for i in tl.items if i["phase"] == "error"][0]
    assert err["failed_phase"] == "A" and "in_phase" not in err
    assert xs.out["phase_errors"]["A"]["error"] == "ValueError: bad"


def test_run_phase_budget_and_dead_bus_and_stop_eats():
    xs, _, _ = make({})
    xs.run_phase("B", lambda: (_ for _ in ()).throw(X.Budget("late")))
    xs.run_phase("D", lambda: (_ for _ in ()).throw(X.BusDead("gone")))
    xs.run_phase("E", lambda: (_ for _ in ()).throw(X.StopEats("stop")))
    pw = xs.out["phase_walls"]
    assert pw["B"]["budget_stop"] == "late" and xs.out["budget_stop"]["phase"] == "B"
    assert xs.phase_dead("D") and pw["E"]["stop_eats"] == "stop"


def test_run_phase_success_records_start_and_end():
    xs, _, _ = make({})
    xs.run_phase("OK", lambda: None)
    assert set(xs.out["phase_walls"]["OK"]) == {"start", "end"}


# ---------------------------------------------------------------- spawn
ITEM = {"id": 4411, "fullType": "Base.Apple", "calories": 95.0, "age": 0.0}


def test_spawn_confirmed_by_item_get():
    xs, _, _ = make({("server", "item.get"): ["no item Base.Apple in admin's inventory", ITEM]})
    row = xs.spawn("Base.Apple", 1, "sp")
    assert row["confirmed"] is True and row["after"]["id"] == 4411
    assert xs.server.cmds == ['additem "admin" "Base.Apple" 1']
    assert xs.out["world_changes"]["left_in_place"] == ["RCON additem Base.Apple x1"]


def test_spawn_unconfirmed_when_item_get_finds_nothing():
    xs, _, _ = make({("server", "item.get"): "no item Base.Apple in admin's inventory"})
    row = xs.spawn("Base.Apple", 1, "sp")
    assert row["confirmed"] is False and "no id after" in xs.out["notes"][0]["note"]
    assert xs.out["world_changes"]["left_in_place"] == []


def test_spawn_unconfirmed_when_a_leftover_was_there_before():
    xs, _, _ = make({("server", "item.get"): ITEM})
    row = xs.spawn("Base.Apple", 1, "sp")
    assert row["leftover_before"] is True and row["confirmed"] is False


def _eat_script(reply):
    return {("server", "foodtimer.set"): {"ok": True}, ("client:admin", "eat.action"): reply}


def test_eat_queue_found_continues():
    reply = {"queued": True, "fraction": 1.0, "spawned": "found", "itemId": 4411, "validStart": True,
             "maxTime": 120}
    xs, _, _ = make(_eat_script(reply))
    row = xs.eat_queue("Base.Apple", "e1")
    assert row["spawned"] == "found" and xs.out["eats"][0]["tag"] == "e1"


@pytest.mark.parametrize("spawned", ["client", None, "", True])
def test_eat_queue_stops_at_any_spawned_that_is_not_the_string_found(spawned):
    xs, _, _ = make(_eat_script({"queued": True, "spawned": spawned, "itemId": 1}))
    with pytest.raises(X.StopEats):
        xs.eat_queue("Base.Apple", "e1")
    assert "not 'found'" in xs.out["stop_reason"]


# ---------------------------------------------------------------- grep_noecho
ECHO = re.compile(r"PZTK: ")
PROBE = re.compile(r"\b(?:item\.get|eat\.action)")


def test_grep_noecho_skips_echo_and_probe_names(tmp_path):
    log = tmp_path / "server-stdout.log"
    log.write_text("LuaError real\nPZTK: LuaError echoed\nrun item.get LuaError probe\nLuaError again\n",
                   encoding="utf-8")
    hits, skipped = X.grep_noecho(str(log), re.compile("LuaError"), 10, ECHO, PROBE)
    assert hits == ["LuaError real", "LuaError again"] and skipped == 2


def test_grep_noecho_limit_and_missing_log(tmp_path):
    log = tmp_path / "l.log"
    log.write_text("x\n" * 5, encoding="utf-8")
    assert len(X.grep_noecho(str(log), re.compile("x"), 2, ECHO, PROBE)[0]) == 2
    assert X.grep_noecho(str(tmp_path / "none.log"), re.compile("x"), 2, ECHO, PROBE) == ([], 0)


# ---------------------------------------------------------------- deployed markers
def _deploy(run_dir, name, text, sub="client/mods/PZTestKit/42/media/lua/server"):
    d = run_dir / sub
    d.mkdir(parents=True, exist_ok=True)
    (d / name).write_text(text, encoding="utf-8")


def test_deployed_marker_check_ok(tmp_path):
    _deploy(tmp_path, "PZTestKit_Server.lua", "-- marker A\n")
    dm, ok = X.deployed_marker_check(str(tmp_path), ["PZTestKit_Server.lua"], {"PZTestKit_Server.lua": ["marker A"]})
    assert ok is True and list(dm.values()) == [True]


def test_deployed_marker_check_missing_marker(tmp_path):
    _deploy(tmp_path, "PZTestKit_Server.lua", "-- other\n")
    dm, ok = X.deployed_marker_check(str(tmp_path), ["PZTestKit_Server.lua"], {"PZTestKit_Server.lua": ["marker A"]})
    assert ok is False and list(dm.values()) == [False]


def test_deployed_marker_check_needs_every_marker(tmp_path):
    _deploy(tmp_path, "PZTestKit_Server.lua", "-- marker A\n")
    dm, ok = X.deployed_marker_check(str(tmp_path), ["PZTestKit_Server.lua"],
                                     {"PZTestKit_Server.lua": ["marker A", "marker B"]})
    assert ok is False and list(dm.values()) == [False]


def test_deployed_marker_check_missing_copy(tmp_path):
    dm, ok = X.deployed_marker_check(str(tmp_path), ["PZTestKit_Server.lua"], {"PZTestKit_Server.lua": ["m"]})
    assert dm == {} and ok is False


def test_abort_on_missing_marker():
    tl = Timeline()
    xs, _, _ = make({}, tl=tl)
    assert xs.abort_on_missing_marker({"a": False}, False) is True
    assert "lacks a marker" in xs.out["abort"] and tl.items[-1]["phase"] == "error"
    xs2, _, _ = make({})
    assert xs2.abort_on_missing_marker({"a": True}, True) is False and "abort" not in xs2.out


# ---------------------------------------------------------------- manifest gate
class FakeRP:
    def __init__(self, head, booted):
        self.m = {"mod": head, "stage": booted}

    def manifest(self, p):
        return self.m["stage" if "stage" in p else "mod"]

    @staticmethod
    def diff(old, new):
        return {"added": sorted(set(new) - set(old)), "removed": sorted(set(old) - set(new)),
                "changed": [], "script_changed": []}


def _gate(tmp_path, staged, head, booted, dirty=False):
    root = tmp_path / "release"
    root.mkdir(exist_ok=True)
    (root / "MANIFEST.json").write_text(json.dumps(staged), encoding="utf-8")
    return X.manifest_gate(FakeRP(head, booted), str(tmp_path), "mod", "release", "release/stage",
                           "MANIFEST.json", lambda *a: "abc123", lambda p: (dirty, ""))


def test_manifest_gate_ok(tmp_path):
    m = {"a.lua": {"sha256": "1", "bytes": 3}}
    g = _gate(tmp_path, m, m, m)
    assert g["ok"] is True and g["files"] == 1


def test_manifest_gate_mismatch_names_the_diff(tmp_path):
    head = {"a.lua": {"sha256": "1"}, "b.lua": {"sha256": "2"}}
    g = _gate(tmp_path, {"a.lua": {"sha256": "1"}}, head, head)
    assert g["ok"] is False and g["diff_staged_vs_head"]["added"] == ["b.lua"]


def test_manifest_gate_staged_tree_differs_or_mod_dirty(tmp_path):
    m = {"a.lua": {"sha256": "1"}}
    assert _gate(tmp_path, m, m, {}, dirty=False)["ok"] is False
    assert _gate(tmp_path, m, m, m, dirty=True)["ok"] is False


def test_manifest_gate_missing_manifest_is_an_error_not_a_raise(tmp_path):
    g = X.manifest_gate(FakeRP({}, {}), str(tmp_path), "mod", "release", "release/stage", "MANIFEST.json",
                        lambda *a: "x", lambda p: (False, ""))
    assert g["ok"] is False and "error" in g


# ---------------------------------------------------------------- memory
def test_memory_ok():
    assert X.memory_ok(14.0, 12.0) is True
    assert X.memory_ok(0.55, 12.0) is False
    assert X.memory_ok(None, 12.0) is False


# ---------------------------------------------------------------- grades
def test_grade_with_zero_samples_is_unmeasured_not_as_predicted():
    xs, _, _ = make({})
    row = xs.grade("HOLD", "as_predicted", {"n": 0}, "a read off", samples=[])
    assert row["verdict"] == "unmeasured" and xs.out["verdicts"]["HOLD"]["verdict"] == "unmeasured"


def test_grade_with_samples_keeps_the_verdict_and_falsified_stays():
    xs, _, _ = make({})
    assert xs.grade("A", "as_predicted", {}, "f", samples=[1])["verdict"] == "as_predicted"
    assert xs.grade("B", "falsified", {}, "f", samples=[])["verdict"] == "falsified"
    assert xs.grade("C", "void", {}, "f")["verdict"] == "void"


def test_grade_marks_the_timeline_with_name_and_verdict():
    tl = Timeline()
    xs, _, _ = make({}, tl=tl, predictions={"A": "p"})
    row = xs.grade("A", "falsified", {}, "f", extra={"why": "x"})
    assert tl.items[-1]["verdict"] == "falsified" and row["predicted"] == "p" and row["why"] == "x"


# ---------------------------------------------------------------- skeleton
def test_persist_and_copy_artifacts_are_byte_identical(tmp_path):
    xs, _, _ = make({})
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    xs.path = str(run_dir / "a.json")
    (run_dir / "MANIFEST.json").write_text("{}", encoding="utf-8")
    xs.copied.append("MANIFEST.json")
    xs.persist()
    dest = xs.copy_artifacts(str(tmp_path), "x999-1", str(run_dir), "a.json")
    assert open(os.path.join(dest, "a.json"), "rb").read() == open(xs.path, "rb").read()
    assert os.path.isfile(os.path.join(dest, "MANIFEST.json"))


def test_copy_artifacts_never_raises_on_a_missing_artifact(tmp_path):
    xs, _, _ = make({})
    xs.path = str(tmp_path / "missing.json")
    assert xs.copy_artifacts(str(tmp_path), "x999-2", str(tmp_path), "missing.json") is None


def test_refuse_exits_one_and_persists(tmp_path):
    xs, _, _ = make({})
    xs.path = str(tmp_path / "o.json")
    with pytest.raises(SystemExit) as e:
        xs.refuse("doctor not clean")
    assert e.value.code == 1 and json.load(open(xs.path))["error"] == "doctor not clean"


def test_finish_fences_each_stage_and_records_failures(tmp_path):
    xs, _, _ = make({}, tl=Timeline())
    xs.path = str(tmp_path / "o.json")
    killed = []

    def bad_teardown(tl, server, cs):
        raise RuntimeError("td")

    def bad_logs():
        raise ValueError("logs")

    graded = []
    xs.finish(bad_teardown, lambda s, ev: killed.append(1), [], read_logs=bad_logs, grade_all=lambda: graded.append(1))
    assert xs.out["teardown_error"] == "RuntimeError: td" and killed == [1] and graded == [1]
    assert xs.out["logs_error"] == "ValueError: logs" and "wall_seconds" in xs.out
