"""agent/driverlib (Plan 23 Task 2): the drivers' shared code as a library, offline; no driver is invoked.

parse_argv, PollThread, chain.lineage_diff and snapshot_cmd, and Session: d_survive's Day generalised, its loop tests
(test_d_survive.py's) ported onto Session with planner_factory=Survive and run twice, once with the synchronous server
reads and once through `polls` (InlinePolls: the PollThread's schedule run on the loop's own thread at each `latest`,
so the fake clock stays single-threaded and the numbers are the synchronous path's). One test runs a real PollThread
whose bus stub sleeps 2 s of real time while the loop's ticks keep rising on the fake clock.

The fixtures are test_d_survive.py's (DayMod, FakeServer, FakeBus, the run helper), copied: the fake mod answers
equip (wields the bat), attack (kills its zombie) and every other type (accepted and done), and FakeBus answers in the
@reply shapes of PZTestKit_Server.lua: stats.all {side, user, worldAge, mult, wall, stats, missing} (a failed read a
string), players [<username>, ...] ({} when nobody is online), damage.watch {ok, side, hooked, user, counts, n, last,
dropped} ({} for an empty Lua table), item.get and ping."""
import json
import os
import re
import threading
import time
import types

import pytest

from agent.base import gates as GT
from agent.base import pza1
from agent.base.planner.survive import Survive
from agent.base.transport.files import FileTransport
from agent.driverlib import chain as CH
from agent.driverlib import day as DY
from agent.driverlib import polls as P
from agent.driverlib import record as R
from agent.driverlib import session as S
from .fakemod import DEFAULT_FRAME, FakeMod

X = S.X
KIT = S.DEFAULTS["KIT"]
LIB = os.path.dirname(S.__file__)


# ================================================================ static: the package, its constants, its imports
def test_the_defaults_are_the_briefs():
    want = {"BUDGET_S": 1200.0, "MIN_FREE_GB": 12.0, "DAY_CAP_S": 840, "PLANNER_HZ": 2, "SERVER_POLL_S": 60,
            "DAMAGE_POLL_S": 5, "PERSIST_S": 30, "MEM_POLL_S": 300, "LIVE_MIN_FREE_GB": 0.5, "STOP_HEALTH": 0.0,
            "MEM_LOW_READS": 2, "BUS_DEAD_S": 60, "BUS_DEAD_POLLS": 2, "STORM_N": 10, "STORM_WINDOW_S": 60,
            "HELLO_TIMEOUT_S": 60.0, "FRAME_TIMEOUT_S": 10.0, "KIT": "Base.BaseballBat", "POLL_S": 0.1,
            "LAST_DECISIONS": 10, "KIT_TIMEOUT_S": 30.0, "EQUIP_TIMEOUT_S": 30.0, "ACT_TIMEOUT_S": 10.0,
            "SERVER_TIMEOUT_S": 10.0, "LAST_FRAMES": 3000, "DEATH_WINDOW_S": 300, "PAIR_S": 1.0,
            "SERVER_RECORDS_KEPT": 5000, "PARK_RX": r"LuaError|STACK TRACE|attempted index|tried to call nil"}
    assert S.DEFAULTS == want
    # I-5: the kept frames span the death window at the frames' 10 Hz, so a wound that opens it is never cut off
    assert S.DEFAULTS["LAST_FRAMES"] == S.DEFAULTS["DEATH_WINDOW_S"] * S.FRAME_HZ == 3000 and S.FRAME_HZ == 10
    assert S.STOP_SETTLE_S == 2.0


def test_the_library_imports_no_driver_but_dlib():
    for name in sorted(os.listdir(LIB)):
        if not name.endswith(".py"):
            continue
        src = open(os.path.join(LIB, name), encoding="utf-8").read()
        imports = [l.split("#")[0].strip() for l in src.splitlines() if l.strip().startswith(("import ", "from "))]
        for l in imports:
            mod = l.split()[1]
            assert "drivers" not in mod, (name, l)
            assert not re.match(r"^(a_|b_|c_|d_|p22|x4_|x5_)", mod), (name, l)
        assert "copied from" not in src.lower(), name
    init = open(os.path.join(LIB, "__init__.py"), encoding="utf-8").read()
    assert "not frozen" in init and "commit" in init


# ================================================================ parse_argv
def test_parse_argv_refuses_anything_not_allowed():
    me = "/x/e_day.py"
    assert S.parse_argv([], me) is None
    for bad in (["x"], ["--help"], ["--session", "2"], ["--session"]):
        r = S.parse_argv(bad, me)
        assert r and "e_day.py" in r and "\n" not in r, bad
    assert S.parse_argv(["--session", "2"], me, allowed=("--session",)) is None
    for bad in (["--session"], ["--help"], ["2"], ["--session", "2", "x"], ["--fixture", "a"],
                ["--session", "--session"], ["--session", "2", "--session", "3"]):
        r = S.parse_argv(bad, me, allowed=("--session",))
        assert r and "e_day.py" in r and "--session" in r and "\n" not in r, bad
    two = ("--session", "--fixture")
    assert S.parse_argv(["--fixture", "f1", "--session", "3"], me, allowed=two) is None
    assert S.parse_flags(["--fixture", "f1", "--session", "3"], two) == {"--fixture": "f1", "--session": "3"}


def test_driver_checks_name_the_drivers_key_and_refuse_a_dirty_library():
    me = os.path.join(os.path.dirname(LIB), "drivers", "e_day.py")
    args = (me, "e_day", "e_day.py", "testing/profiles/agent.toml")
    say = lambda *a: ""                                                     # noqa: E731
    c, ok = S.driver_checks(*args, git_say=say, git_dirty=lambda rel: (False, ""))
    assert ok and c["driver_file"] and c["driver_prefix"] and c["profile_exists"] and c["driverlib_dirty"] is False
    for dirty in ("testing/PZAgent", "testing/agent/base", "testing/agent/driverlib", "testing/agent/drivers/e_day.py"):
        assert S.driver_checks(*args, git_say=say, git_dirty=lambda rel, d=dirty: (rel == d, ""))[1] is False, dirty
    c, ok = S.driver_checks(*args, git_say=lambda *a: "testing/artifacts/e_day-1/e_day.json",
                            git_dirty=lambda rel: (False, ""))
    assert ok is False and c["no_committed_artifact"] is False
    assert S.driver_checks(me, "f_goals", "f_goals.py", args[3], git_say=say,
                           git_dirty=lambda rel: (False, ""))[1] is False


# ================================================================ PollThread
def _until(pred, timeout_s=5.0):
    t0 = time.time()
    while not pred():
        if time.time() - t0 > timeout_s:
            return False
        time.sleep(0.005)
    return True


def test_the_poll_thread_runs_each_read_on_its_own_thread_and_keeps_the_latest():
    ids, n = [], {"v": 0}

    def read():
        ids.append(threading.get_ident())
        n["v"] += 1
        return n["v"]
    p = P.PollThread()
    assert p.latest("a") == (None, None) and p.pending("a") is False
    p.schedule("a", 0.01, read)
    p.start()
    try:
        assert _until(lambda: n["v"] >= 3)
        result, wall = p.latest("a")
        assert result >= 3 and isinstance(wall, float) and wall <= time.time()
        assert set(ids) == {ids[0]} and ids[0] != threading.get_ident()
    finally:
        assert p.stop() is True
    assert not p._thread.is_alive()
    k = n["v"]
    time.sleep(0.05)
    assert n["v"] == k                                                        # stopped: no read after the join


def test_a_raising_read_lands_in_errors_and_its_schedule_is_kept():
    n = {"v": 0}

    def read():
        n["v"] += 1
        if n["v"] == 1:
            raise ValueError("first read fails")
        return "ok%d" % n["v"]
    p = P.PollThread()
    p.schedule("b", 0.01, read)
    p.start()
    try:
        assert _until(lambda: n["v"] >= 2)
        assert _until(lambda: p.latest("b")[0] is not None)
    finally:
        p.stop()
    assert p.errors[0]["name"] == "b" and "ValueError: first read fails" in p.errors[0]["error"]
    assert isinstance(p.errors[0]["wall"], float) and len(p.errors) == 1
    assert p.latest("b")[0].startswith("ok")


def test_each_read_runs_at_most_every_every_s_on_the_given_clock():
    clock = {"t": 100.0}
    calls = []
    p = P.PollThread(clock=lambda: clock["t"])
    p.schedule("s", 60, lambda: calls.append(clock["t"]) or clock["t"])
    p.schedule("d", 5, lambda: "d")
    assert p.run_due() == 2 and calls == [100.0]                              # both run at the first chance
    clock["t"] = 159.0
    assert p.run_due() == 1 and calls == [100.0]                              # only d is due (since 105)
    clock["t"] = 160.0
    assert p.run_due(only="s") == 1 and calls == [100.0, 160.0] and p.latest("s") == (160.0, 160.0)
    assert p.pending("s") is False


# ================================================================ chain
def _frame(x=100.0, y=200.0, health=100.0, hunger=0.1, n=12, gmin=480.0, wa=8.0):
    return {"seq": 5, "wallMs": 1, "gameMin": gmin, "worldAge": wa, "me": {"x": x, "y": y, "z": 0},
            "body": {"health": health}, "stats": {"hunger": hunger, "thirst": 0.1, "fatigue": 0.05},
            "load": {"weight": 4.5, "max": 8.0, "level": 0, "n": n}}


def test_lineage_diff_is_ok_only_within_the_tolerances():
    assert CH.LINEAGE_TOL == {"position": 0.5, "health": 0.01, "stat": 0.005, "inventory_n": 0, "world_min": 3.0}
    prev = {"loop": {"last_frames": [_frame(x=0.0), _frame()]}}
    d = CH.lineage_diff(prev, _frame())
    assert d["ok"] is True
    assert d["position"] == {"prev": [100.0, 200.0], "now": [100.0, 200.0], "d": 0.0, "tol": 0.5, "ok": True}
    assert d["health"] == {"prev": 100.0, "now": 100.0, "delta": 0.0, "tol": 0.01, "ok": True}
    assert d["inventory_n"] == {"prev": 12, "now": 12, "delta": 0, "tol": 0, "ok": True}
    assert d["stats"]["hunger"] == {"prev": 0.1, "now": 0.1, "delta": 0.0, "tol": 0.005, "ok": True}
    assert d["world_age"] == {"prev": 8.0, "now": 8.0, "delta_min": 0.0, "lo": 0.0, "hi": 3.0, "ok": True}
    assert d["game_min"] == {"prev": 480.0, "now": 480.0}                    # reported, never banded
    d = CH.lineage_diff(prev, _frame(x=101.0))
    assert d["ok"] is False and d["position"]["d"] == pytest.approx(1.0) and d["position"]["ok"] is False
    assert CH.lineage_diff(prev, _frame(x=100.4))["ok"] is True
    # P23-Y amended: the teardown save 2 game minutes on, the stats moved with it
    late = CH.lineage_diff(prev, _frame(gmin=482.0, wa=8.0 + 2.0 / 60.0, hunger=0.104))
    assert late["ok"] is True and late["world_age"]["delta_min"] == pytest.approx(2.0)
    assert late["stats"]["hunger"]["delta"] == pytest.approx(0.004)
    assert CH.lineage_diff(prev, _frame(wa=8.05))["ok"] is True                # 3.0 game minutes: the band's edge
    # a midnight crossing: gameMin wraps, worldAge does not
    night = {"loop": {"last_frames": [_frame(gmin=1439.0, wa=23.0 + 59.0 / 60.0)]}}
    mid = CH.lineage_diff(night, _frame(gmin=1.0, wa=24.0 + 1.0 / 60.0))
    assert mid["ok"] is True and mid["world_age"]["delta_min"] == pytest.approx(2.0)
    assert mid["game_min"] == {"prev": 1439.0, "now": 1.0}
    # a clock that ran backwards (a stale save) and one too far on are BROKEN
    for bad, key in ((_frame(health=99.98), "health"), (_frame(n=13), "inventory_n"),
                     (_frame(wa=8.0 - 1.0 / 60.0), "world_age"), (_frame(wa=8.0 + 3.5 / 60.0), "world_age")):
        r = CH.lineage_diff(prev, bad)
        assert r["ok"] is False and r[key]["ok"] is False, key
    back = CH.lineage_diff(prev, _frame(wa=8.0 - 1.0 / 60.0))
    assert back["world_age"]["delta_min"] == pytest.approx(-1.0)
    r = CH.lineage_diff(prev, _frame(hunger=0.106))
    assert r["ok"] is False and r["stats"]["hunger"]["ok"] is False
    assert r["stats"]["hunger"]["delta"] == pytest.approx(0.006)
    assert CH.lineage_diff({}, _frame())["ok"] is False and CH.lineage_diff(None, None)["ok"] is False
    assert CH.lineage_diff({}, _frame())["world_age"] == {"prev": None, "now": 8.0, "delta_min": None, "lo": 0.0,
                                                         "hi": 3.0, "ok": False}


# ================================================================ day (Task 16d: the day drivers' shared session)
def _fixture_rec(root, name, session=None, body=None):
    (root / name / "cache" / "server").mkdir(parents=True)
    rec = {"name": name, "build": "42.21.0", "server": {"name": "pzt", "mods": ["PZTestKit"]}, "clients": {}}
    if session is not None:
        rec["session"] = session
    (root / name / "fixture.json").write_text(body if body is not None else json.dumps(rec), encoding="utf-8")


def _artifact(path, frames=True, session=None):
    art = {"loop": {"last_frames": [_frame()] if frames else []}}
    if session is not None:
        art["chain"] = {"session": session}
    path.write_text(json.dumps(art), encoding="utf-8")
    return str(path)


def test_chain_checks_refuse_a_bad_fixture_or_prev_and_report_the_sessions_order(agent_fixture, tmp_path):
    cc, ok = DY.chain_checks(DY.flags([]))
    assert ok and cc == {"fixture": "agent", "fixture_ok": True, "fixture_error": None, "fixture_session": None,
                         "prev": None, "prev_ok": None, "prev_error": None, "prev_frames": None,
                         "prev_session": None, "session": 1, "session_consistent": None}
    cc, ok = DY.chain_checks(DY.flags(["--fixture", "nope"]))
    assert not ok and cc["fixture_ok"] is False and "nope" in cc["fixture_error"]
    _fixture_rec(agent_fixture, "corrupt", body="{not json")                   # a traceback before: now a refusal
    cc, ok = DY.chain_checks(DY.flags(["--fixture", "corrupt"]))
    assert not ok and cc["fixture_error"].startswith("JSONDecodeError")
    _fixture_rec(agent_fixture, "chain-1", session=1)
    good = _artifact(tmp_path / "a.json", session=1)
    cc, ok = DY.chain_checks(DY.flags(["--session", "2", "--fixture", "chain-1", "--prev", good]))
    assert ok and cc["prev_ok"] is True and cc["prev_frames"] is True and cc["prev_error"] is None
    assert (cc["fixture_session"], cc["prev_session"], cc["session_consistent"]) == (1, 1, True)
    bare = _artifact(tmp_path / "bare.json", frames=False)
    cc, ok = DY.chain_checks(DY.flags(["--session", "2", "--fixture", "chain-1", "--prev", bare]))
    assert not ok and cc["prev_ok"] is True and cc["prev_frames"] is False and "last_frames" in cc["prev_error"]
    (tmp_path / "other.json").write_text(json.dumps({"stop": None}), encoding="utf-8")
    cc, ok = DY.chain_checks(DY.flags(["--prev", str(tmp_path / "other.json")]))
    assert not ok and cc["prev_frames"] is False
    assert DY.session_line(cc) is None
    # P23-Z: a --session that does not follow the chain refuses the boot, its line naming the sessions
    cc, ok = DY.chain_checks(DY.flags(["--session", "3", "--fixture", "chain-1", "--prev", good]))
    assert not ok and cc["session_consistent"] is False
    assert DY.session_line(cc) == ("refused (P23-Z): --session 3 does not follow the chain: the fixture's session 1, "
                                   "the prev's 1 (each expected 2)")
    later = _artifact(tmp_path / "b.json", session=2)
    cc, ok = DY.chain_checks(DY.flags(["--session", "2", "--fixture", "chain-1", "--prev", later]))
    assert not ok and cc["session_consistent"] is False and "the prev's 2" in DY.session_line(cc)
    cc, ok = DY.chain_checks(DY.flags(["--session", "2", "--prev", _artifact(tmp_path / "c.json")]))
    assert ok and cc["session_consistent"] is None and DY.session_line(cc) is None    # nothing to compare
    cc, ok = DY.chain_checks(DY.flags(["--session", "1", "--fixture", "chain-1"]))
    assert not ok and cc["session_consistent"] is False                         # a fresh chain on a later fixture


def test_boot_and_run_keeps_the_boots_order():
    src = open(DY.__file__, encoding="utf-8").read()
    body = src[src.index("    pre, ok = preboot()", src.index("def boot_and_run(")):]          # past the docstring
    order = ["pre, ok = preboot()", "sys.exit(1)", "rec_fx = fx.load(args[\"fixture\"])", "new_run_dir(key)",
             "xs = X.Xs(", "DS.memory_gate(xs, min_free_gb)",
             "DL.boot(xs, prof, rec_fx, run_dir, [user], started, clients, holder,",
             "make_client=DS.clearing_make_client(session.make_client)",
             "if not all(v.get(\"ok\") for v in out[\"verify\"])",
             "ran = run_session(xs, FileTransport(DL.state_dir(clients[user])), prev, pre)", "finally:",
             "out[\"teardown_started_wall\"] = wall()",
             "xs.finish(B.bounded_teardown, hard_kill, every, read_logs=read_logs)",
             "run_after_teardown(after_teardown, out, ran)", "grade_fn(out)",
             "out[\"finished\"] = True", "copy_run(xs, repo, run_id, run_dir, artifact)",
             "next_steps(args, run_dir, xs.path)"]
    at = [body.index(s) for s in order]
    assert at == sorted(at), order


def test_the_day_chain_lays_the_drivers_extra_and_copied_over_its_record(tmp_path):
    xs = types.SimpleNamespace(copied=[], out=S.new_out(), user="admin", path=str(tmp_path / "a.json"))
    c = DY.Chain(xs, None, extra=lambda s: {"llm": {"n": 1}}, copied=("goals.log",),
                 planner_factory=Survive, clock=lambda: 5.0)
    assert xs.copied == ["goals.log", "decision.log"]
    rec = c.extra_record()
    assert rec["llm"] == {"n": 1} and rec["lineage"] is None and rec["goals"] == [] and rec["t_loop0_ms"] is None
    assert DY.CONTRACT_KEYS == ("goals", "night", "lineage", "t_loop0_ms", "results")
    assert rec["results"] == []
    clash = DY.Chain(types.SimpleNamespace(copied=[], out=S.new_out(), user="admin", path=None), None,
                     extra=lambda s: {"llm": 1, "lineage": "x"}, planner_factory=Survive, clock=lambda: 5.0)
    with pytest.raises(AssertionError, match="lineage"):
        clash.extra_record()
    assert rec["night"] == {"wants": 0, "steps": [], "sleeps": []}
    plain = DY.Chain(types.SimpleNamespace(copied=[], out=S.new_out(), user="admin", path=None), None,
                     planner_factory=Survive, clock=lambda: 5.0)
    assert set(plain.extra_record()) == {"goals", "night", "lineage", "t_loop0_ms", "results"}


def test_after_teardown_runs_with_the_sessions_return_and_never_raises():
    seen = []
    out = {}
    DY.run_after_teardown(None, out, "s")
    DY.run_after_teardown(lambda o, ran: seen.append(ran), out, "s")
    assert seen == ["s"] and out == {}
    DY.run_after_teardown(lambda o, ran: 1 / 0, out, None)
    assert out["after_teardown_error"].startswith("ZeroDivisionError")


def test_day_grade_records_a_failure_rather_than_raising():
    out = {}
    DY.grade(out, "grade_x", lambda o: {"ok": 1})
    assert out == {"grade_x": {"ok": 1}}
    DY.grade(out, "grade_y", lambda o: 1 / 0)
    assert out["grade_y_error"].startswith("ZeroDivisionError") and "grade_y" not in out


def test_the_summary_names_the_chains_next_fixture_and_the_next_sessions_argv():
    """I-7: the chain's fixtures are agent-s1, agent-s2, ... (spec section 4); M-10: the next session, E or F, is
    given --session n+1 and --prev of this artifact (P23-Z refuses it otherwise)."""
    assert DY.next_fixture(1) == "agent-s1" and DY.next_fixture(3) == "agent-s3"
    args = {"session": 2, "fixture": "agent-s1", "prev": "testing/runs/e_day-1/e_day.json"}
    nx = DY.next_steps(args, "testing/runs/e_day-2", "testing/runs/e_day-2/e_day.json")
    assert nx["snapshot_cmd"][-9:] == ["snapshot", "--from-run", "testing/runs/e_day-2", "--name", "agent-s2",
                                       "--parent", "agent-s1", "--session", "2"]
    assert nx["next_session"] == "--session 3 --fixture agent-s2 --prev testing/runs/e_day-2/e_day.json"
    assert nx["f_session"] == ("an F session on the chain's last fixture: f_goals.py --session 3 --fixture agent-s2 "
                               "--prev testing/runs/e_day-2/e_day.json (P23-Z: any other --session is refused)")
    first = DY.next_steps({"session": 1, "fixture": "agent", "prev": None}, "r1", "r1/e_day.json")
    assert first["snapshot_cmd"][-5:] == ["agent-s1", "--parent", "agent", "--session", "1"]
    src = open(DY.__file__, encoding="utf-8").read()
    assert "-after-" not in src and '"next": next_steps(args, run_dir, xs.path)' in src


def test_make_day_session_is_the_one_chain_builder(tmp_path):
    """M-8: the day's shared constants and its one session builder live in day.py; a driver's make_session only
    names its planner, its extra record and its copied files."""
    assert DY.LIMITS == {"DAY_CAP_S": 840, "PLANNER_HZ": 2, "DAMAGE_POLL_S": 5}
    assert DY.CONSTANTS == dict(S.DEFAULTS, **DY.LIMITS, BUDGET_S=1200.0)
    assert (DY.USER, DY.BUDGET_S, DY.MIN_FREE_GB) == ("admin", 1200.0, 12.0)
    xs = types.SimpleNamespace(copied=[], out=S.new_out(), user="admin", path=str(tmp_path / "a.json"))
    made = []

    def factory(world, actions, log_path, clock):
        made.append(log_path)
        return Survive(world, actions, log_path, clock)
    c = DY.make_day_session(xs, None, factory, extra=lambda s: {"x": 1}, copied=("goals.log",), prev={"loop": {}},
                            clock=lambda: 5.0, limits={"DAY_CAP_S": 9})
    assert isinstance(c, DY.Chain) and isinstance(c.polls, P.PollThread) and c.prev == {"loop": {}}
    assert c.lim["DAY_CAP_S"] == 9 and c.lim["PLANNER_HZ"] == 2 and c.lim["DAMAGE_POLL_S"] == 5
    assert xs.copied == ["goals.log", "decision.log"] and made and c.extra_record()["x"] == 1
    for drv in ("e_day.py", "f_goals.py"):
        src = open(os.path.join(os.path.dirname(LIB), "drivers", drv), encoding="utf-8").read()
        assert "DY.make_day_session(" in src, drv
        for own in ("LIMITS = ", "DAY_CAP_S = ", "PLANNER_HZ = ", "DAMAGE_POLL_S = ", "BUDGET_S = ", "USER = ",
                    "PollThread(clock)"):
            assert own not in src, (drv, own)


def test_snapshot_cmd_is_the_pzt_snapshot_argv():
    argv = CH.snapshot_cmd("testing/runs/e_day-1", "chain-2", "agent", 2)
    assert argv[-9:] == ["snapshot", "--from-run", "testing/runs/e_day-1", "--name", "chain-2", "--parent", "agent",
                         "--session", "2"]
    assert argv[1].replace("\\", "/").endswith("testing/pzt")


# ================================================================ DayMod and FakeBus (test_d_survive.py's, copied)
class Clock:
    def __init__(self):
        self.t = 1_790_000_000.0

    def now(self):
        return self.t


KIT_ID = 5001
OLD_ID = 4999
ZID = 77


class DayMod(FakeMod):
    """The fake Lua on the shared clock: sleep(dt) runs its ticks (one frame a tick at 10 Hz). Knobs, in seconds of
    its own clock since it was made: `die_from` (body.health falls by `drain` a tick from then, to `floor` (0); each
    drop is a server HEAVYLOAD record of `amount` (default `drain`) when `server_damage`), `client_damage` (one client
    damage event at the drain's start), `zombie_at` (zombie ZID at 1.5 tiles from then until an attack kills it),
    `lua_err_from` / `lua_err_every`, `silent_from` (no line written from then), `hello_mode`, `no_hello` (no hello
    line), `zombie_far_s` and `zombie_dist`, `bite_at` (body.bitten 0 -> 1 and a hurt part from then), `held` (the bat
    in the inventory at the first sight, a chain's later session) and `wielded` (the bat in the hand from the start),
    `first_sight_ticks` (the held bat's item_added arrives that many ticks after the first frame, whose load.n
    already counts it) and `late_old` (an older bat, id OLD_ID, item_added on the tick after the spawn's tick, before
    the new bat's). A `sleep` stays accepted until the next command, which ends it `failed superseded`.
    `death_at` (PZA/1.3, ruling P23-AO): one death event on the first tick from then, before that tick's frame, its
    health the frame's (frozen from then on: the drain stops, as the fourth chain's client copy froze above 0).
    Every other command, stop included, is accepted and done."""

    def __init__(self, d, clock, die_from=None, drain=5.0, amount=None, floor=0.0, server_damage=True,
                 client_damage=False, zombie_at=None, lua_err_from=None, lua_err_every=1.0, silent_from=None,
                 hello_mode="append", no_hello=False, zombie_far_s=0.0, zombie_dist=1.5, bite_at=None, held=False,
                 wielded=False, first_sight_ticks=0, late_old=False, death_at=None):
        super().__init__(d, clock=clock.now)
        self.clk, self.t0 = clock, clock.t
        self.hz = 10
        self.die_from, self.drain, self.amount, self.floor = die_from, drain, drain if amount is None else amount, floor
        self.server_damage_on, self.client_damage = server_damage, client_damage
        self.zombie_at, self.zombie_dead = zombie_at, False
        self.lua_err_from, self.lua_err_every, self.last_err = lua_err_from, lua_err_every, None
        self.silent_from = silent_from
        self.zombie_far_s, self.zombie_dist, self.bite_at = zombie_far_s, zombie_dist, bite_at
        self.health, self.weapon, self.has_kit = 100.0, None, False
        self.pending, self.cmd_seen, self.cmds = [], 0, []
        self.late, self.late_old, self.sleeping, self.load_n = [], late_old, None, 1 if held else 0
        self.server_records = []
        self.death_at, self.died = death_at, False
        if held:                                                              # a chain's later session: the bat kept
            self.has_kit = True
            ev = {"itemId": KIT_ID, "fullType": KIT, "weight": 1.5, "use": "weapon"}
            (self.late.append([first_sight_ticks, ev]) if first_sight_ticks else self.pending.append(ev))
        if wielded:
            self.weapon = {"type": KIT, "cond": 1.0, "reach": 1.125, "ammo": None}
        if not no_hello:
            self.hello(mode=hello_mode)
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

    def additem(self):
        self.has_kit = True
        self.load_n += 1
        if self.late_old:                                    # an older bat's event lands first, on the same tick
            self.pending.append({"itemId": OLD_ID, "fullType": KIT, "weight": 1.5})
        self.pending.append({"itemId": KIT_ID, "fullType": KIT, "weight": 1.5})

    def _zombie_live(self):
        return self.zombie_at is not None and self.s() >= self.zombie_at and not self.zombie_dead

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
        t, aid, args = cmd["type"], cmd["aid"], cmd["args"]
        if t == "attack" and not (args["targetId"] == ZID and self._zombie_live()):
            self.act(aid, "rejected", t, reason="no target")
            return
        if self.sleeping is not None:
            self.act(self.sleeping, "failed", "sleep", reason="superseded")
            self.sleeping = None
        self.act(aid, "accepted", t)
        if t == "sleep":
            self.sleeping = aid
            return
        if t == "equip":
            self.weapon = {"type": KIT, "cond": 1.0, "reach": 1.125, "ammo": None}
        if t == "attack":
            self.zombie_dead = True
            self.event("zombie_dead", id=ZID)
            self.act(aid, "done", t, result={"swings": 1, "attackStarted": True, "meleeDelay": 0,
                                             "targetDead": True})
        else:
            self.act(aid, "done", t, result={})

    def _tick(self):
        if self.silent_from is not None and self.s() >= self.silent_from:
            return
        self._poll()
        for ev in self.pending:
            self.event("item_added", **ev)
        self.pending = []
        for d in self.late:
            d[0] -= 1
            if d[0] <= 0:
                self.event("item_added", **d[1])
        self.late = [d for d in self.late if d[0] > 0]
        wall = int(round(self.clk.t * 1000))
        if self.die_from is not None and self.s() >= self.die_from - 1e-9 and self.health > self.floor and \
                not self.died:
            if self.client_damage and self.health == 100.0:
                self.event("damage", tag="HEAVYLOAD", amount=self.drain, side="client")
            self.health = max(self.floor, self.health - self.drain)
            if self.server_damage_on:
                self.server_records.append({"i": len(self.server_records) + 1, "tag": "HEAVYLOAD",
                                            "amount": self.amount, "wall": wall})
        if self.lua_err_from is not None and self.s() >= self.lua_err_from - 1e-9 and (
                self.last_err is None or self.s() - self.last_err >= self.lua_err_every - 1e-9):
            self.last_err = self.s()
            self.event("lua_error", msg="boom")
        if self.death_at is not None and not self.died and self.s() >= self.death_at - 1e-9:
            self.died = True
            self.death(gameMin=480.0 + self.s() * 16.0 / 60.0, x=100.0, y=200.0, health=self.health,
                       zombiesKilled=1 if self.zombie_dead else 0)
        dist = 8.0 if self._zombie_live() and self.s() < self.zombie_at + self.zombie_far_s else self.zombie_dist
        zs = [{"id": ZID, "x": 100.0 + dist, "y": 200.0, "dist": dist, "hasTarget": True, "crawler": False,
               "health": 1.0}] if self._zombie_live() else []
        body = dict(DEFAULT_FRAME["body"], health=self.health)
        if self.bite_at is not None and self.s() >= self.bite_at - 1e-9:
            body.update(bitten=1, parts=[{"i": 5, "h": 80.0}])
        self.frame(gameMin=480.0 + self.s() * 16.0 / 60.0, body=body, weapon=self.weapon, zombies=zs,
                   load=dict(DEFAULT_FRAME["load"], n=self.load_n))


class FakeServer:
    def __init__(self, mod):
        self.mod, self.errors, self.rcons = mod, [], []

    def rcon(self, cmd):
        self.rcons.append(cmd)
        self.mod.additem()
        return True, "Item %s Added in admin's inventory." % KIT


class FakeBus:
    """The server's bus in its real reply shapes. Knobs (the mod's seconds): `stats_bad_from` / `players_bad_from`
    (a failure reply from then, until `bad_until`), `gone_from` (players {} from then), `players_error_from` (players
    {"error": "TimeoutError: no reply"} from then), `bus_dead_from` (stats.all and item.get stall and the ping never
    answers: xlib's BusDead), `stall_at` / `stall_s` (one stats.all call blocks stall_s while the client keeps
    writing)."""

    def __init__(self, mod, stats_bad_from=None, players_bad_from=None, bad_until=None, gone_from=None,
                 players_error_from=None, bus_dead_from=None, stall_at=None, stall_s=0.0, bus_s=0.05):
        self.mod = mod
        self.stats_bad_from, self.players_bad_from, self.bad_until = stats_bad_from, players_bad_from, bad_until
        self.gone_from, self.players_error_from, self.bus_dead_from = gone_from, players_error_from, bus_dead_from
        self.stall_at, self.stall_s, self.bus_s = stall_at, stall_s, bus_s
        self.asked, self.stats_calls, self.players_calls, self.damage_calls = [], [], [], []
        self.hooked_ms = None

    def after(self, t):
        return t is not None and self.mod.s() >= t

    def bad(self, t):
        return self.after(t) and not self.after(self.bad_until)

    def ask(self, node, cmd, args, timeout=30):
        self.asked.append((node, cmd, args, timeout))
        if self.bus_s:
            self.mod.sleep(self.bus_s)
        m = self.mod
        dead = self.after(self.bus_dead_from)
        if cmd == "ping":
            return {"error": "TimeoutError: no reply"} if dead else "pong"
        if dead and cmd in ("stats.all", "item.get", "players", "damage.watch"):
            return {"error": "TimeoutError: no reply"}
        if cmd == "item.get":
            if not m.has_kit:
                return "no item %s in admin's inventory" % KIT
            return {"fullType": KIT, "id": KIT_ID, "uses": 1, "age": 0, "weight": 1.5}
        if cmd == "stats.all":
            self.stats_calls.append(m.s())
            if self.after(self.stall_at) and self.stall_s:
                m.sleep(self.stall_s)
                self.stall_s = 0.0
            if self.bad(self.stats_bad_from):
                return "no online player admin"
            return {"side": "server", "user": args, "worldAge": 8.0, "mult": 1.0, "wall": 1,
                    "stats": {"Hunger": 0.11, "Thirst": 0.1, "Fatigue": 0.05}, "missing": {}}
        if cmd == "players":
            self.players_calls.append(m.s())
            if self.bad(self.players_bad_from):
                return "timeout"
            if self.after(self.players_error_from):
                return {"error": "TimeoutError: no reply"}
            if self.after(self.gone_from):
                return {}
            return ["admin"]
        if cmd == "damage.watch":
            parts = args.split()
            since = int(parts[2]) if len(parts) == 3 else 0
            self.damage_calls.append((m.s(), since, args))
            if self.hooked_ms is None:
                self.hooked_ms = round(m.clk.t * 1000)
            heard = [r for r in m.server_records if r["wall"] >= self.hooked_ms]
            counts = {}
            for r in heard:
                counts[r["tag"]] = counts.get(r["tag"], 0) + 1
            last = [dict(r) for r in heard if r["i"] > since]
            return {"ok": True, "side": "server", "hooked": True, "user": parts[0], "counts": counts or {},
                    "n": len(heard), "last": last or {}, "dropped": 0}
        return {"error": "unknown command " + cmd}


class InlinePolls(P.PollThread):
    """The PollThread's schedule run on the caller's thread: `latest(name)` first runs that read when it is due, so
    the merge path runs on the fake clock exactly where the synchronous path would read."""

    def start(self):
        self.started = True

    def latest(self, name):
        self.run_due(only=name)
        return super().latest(name)


MODES = ("sync", "polls")
# d_survive's damage cadence (its DAMAGE_POLL_S 30), laid under every run so the ported tests keep their numbers: each
# bus call costs the fake mod bus_s, and the library's 5 s cadence shifts the loop's other reads by those calls
PORT_LIMITS = {"DAMAGE_POLL_S": 30}


def run_session(tmp_path, monkeypatch, mode="sync", limits=None, budget_s=1e9, free=lambda: 30.0, bus=None,
                setup=None, polls=None, sleep=None, port=True, polls_join_s=None, **flags):
    """One Session on DayMod and a bus (FakeBus from the `bus` knobs, or an object with bind(mod) and ask). `polls`
    is a PollThread or a callable of the fake clock making one; mode "polls" without one runs InlinePolls. `sleep`
    wraps the mod's sleep. PORT_LIMITS lie under `limits` unless port is False (the library's own defaults)."""
    clock = Clock()
    sd = str(tmp_path / "clients" / "admin" / "Lua" / "pzagent" / "admin")
    mod = DayMod(sd, clock, **flags)
    if hasattr(bus, "bind"):
        fb = bus
        fb.bind(mod)
    else:
        fb = FakeBus(mod, **(bus or {}))
    monkeypatch.setattr(S.DL, "time", types.SimpleNamespace(time=clock.now))   # _dlib.bus_stats's wallMs clock
    out = S.new_out()
    xs = X.Xs(out, node=lambda side: side, server=FakeServer(mod), ask=fb.ask, clock=clock.now, sleep=mod.sleep,
              budget_s=budget_s, user="admin", clients={"admin": types.SimpleNamespace(seen={})})
    xs.path = str(tmp_path / "session.json")
    if callable(polls):
        polls = polls(clock)
    elif polls is None and mode == "polls":
        polls = InlinePolls(clock=clock.now)
    lim = dict(PORT_LIMITS if port else {}, **(limits or {}))
    sess = S.Session(xs, FileTransport(sd, clock=clock.now), planner_factory=Survive, clock=clock.now,
                     sleep=sleep(mod.sleep) if sleep else mod.sleep, free=free, limits=lim, polls=polls,
                     polls_join_s=polls_join_s)
    if setup is not None:
        setup(sess)
    sess.run()
    out["frames"]["parks"] = 0
    out["finished"] = True
    return types.SimpleNamespace(out=out, mod=mod, bus=fb, day=sess, xs=xs, clock=clock)


def fr_n(out):
    """Every frame the session kept: a session under DEATH_WINDOW_S of frames keeps them all."""
    return out["frames"]["n"]


def decisions(tmp_path):
    with open(tmp_path / S.DECISION_LOG, encoding="utf-8") as f:
        return [json.loads(ln) for ln in f]


# ================================================================ the loop, ported
@pytest.mark.parametrize("mode", MODES)
def test_a_clean_day_runs_every_phase_and_stops_at_the_day_cap(tmp_path, monkeypatch, mode):
    r = run_session(tmp_path, monkeypatch, mode, limits={"DAY_CAP_S": 40})
    out = r.out
    assert out["phase_errors"] == {}, out["phase_errors"]
    assert out["stop"]["reason"] == "day_cap" and out["stop"]["wallS"] == pytest.approx(40, abs=0.2)
    h = out["readings"]["hello"]
    assert h["ok"] and h["proto"] == "PZA/1" and h["mode"] == "append" and h["first_frame"]["seq"] >= 1
    kit = out["readings"]["kit"]
    assert kit["spawn"]["confirmed"] is True and kit["item"] == {"itemId": KIT_ID, "source": "item_added",
                                                                 "fullType": KIT, "seq": kit["item"]["seq"],
                                                                 "wallMs": kit["item"]["wallMs"]}
    assert kit["equip"]["state"] == "done" and kit["weapon_frame"]["type"] == KIT
    assert kit["armed"] is True and kit["ok"] is True
    dh = out["readings"]["damage_hook"]
    assert dh["ok"] is True and dh["hooked"] is True and dh["n"] == 0 and dh["last_i"] == 0
    assert list(out["readings"]) == ["hello", "damage_hook", "kit"] and out["loop"]["started"] is True
    loop = out["loop"]
    log = decisions(tmp_path)
    assert loop["ticks"] == len(log) and loop["ticks"] == pytest.approx(40 * S.DEFAULTS["PLANNER_HZ"], abs=2)
    assert loop["last_decisions"] == log[-10:]
    sent = [d["action"] for d in log if d["sent"]]
    assert loop["decisions"] == len(sent) == len(loop["actions"]) > 0
    assert sent[0] == {"type": "scan", "args": {"r": 10}}
    planner_cmds = [c for c in r.mod.cmds if c["type"] != "equip"]
    assert planner_cmds[-1]["type"] == "stop"                                  # I-6: the loop's own, after the cap
    assert [{"type": c["type"], "args": c["args"]} for c in planner_cmds[:-1]] == sent
    assert all(set(a) == {"aid", "type", "args", "state", "reason", "sentS", "endedS", "branch"}
               | ({"use"} if a["type"] == "consume" else set()) for a in loop["actions"])
    assert [a["branch"] for a in loop["actions"]] == [d["branch"] for d in log if d["sent"]]
    assert loop["actions"][0]["state"] == "done" and loop["actions"][0]["endedS"] >= loop["actions"][0]["sentS"]
    assert loop["cost"]["n"] > 0 and loop["cost"]["p50"] == pytest.approx(0.2) and loop["cost"]["over5"] == 0
    assert loop["first_game_min"] is not None and loop["game_min"] > loop["first_game_min"]
    assert loop["first_world_age"] == loop["last_frames"][0]["worldAge"] is not None   # every frame kept: the first is [0]
    assert len(loop["last_frames"]) == fr_n(out) < S.DEFAULTS["LAST_FRAMES"]   # every frame: 40 s is under the cap
    assert S.DECISION_LOG in r.xs.copied
    fr = out["frames"]
    assert fr["lua_errors"] == 0 and fr["gaps"] == 0 and fr["bad"] == 0 and fr["n"] > 300
    persisted = json.loads((tmp_path / "session.json").read_text(encoding="utf-8"))
    assert persisted["stop"]["reason"] == "day_cap" and persisted["loop"]["ticks"] == loop["ticks"]
    json.dumps(out, allow_nan=False)
    g = GT.grade_d(persisted)
    assert g["survived"] is True and g["death_explained"] is None and g["start_kit_armed"] is True
    assert g["actions"]["by_type"]["scan"] == {"done": 1} and g["game_minutes"] > 0


@pytest.mark.parametrize("mode", MODES)
def test_the_server_is_polled_on_schedule_with_one_paired_needs_row_each(tmp_path, monkeypatch, mode):
    r = run_session(tmp_path, monkeypatch, mode, limits={"DAY_CAP_S": 130})
    calls = r.bus.stats_calls
    assert [round(c - calls[0]) for c in calls] == [0, 60, 120] and len(r.bus.players_calls) == 3
    assert r.day.world.server["stats"]["Hunger"] == pytest.approx(0.11)
    loop = r.out["loop"]
    assert len(loop["needs"]) == 3 and all(len(n) == 6 for n in loop["needs"])
    assert loop["needs"][1][1:5] == [0.1, 0.1, 0.05, 100.0] and loop["needs"][1][5] == pytest.approx(0.11)
    assert loop["needs_fields"] == ["gameMin", "hunger", "thirst", "fatigue", "health", "serverHunger"]
    for p in loop["needs_pairs"]:
        assert p["paired"] is True and p["dtMs"] <= 1000.0 and p["frameSeq"] is not None
    assert loop["server_polls"] == 3 and loop["server_fails"] == 0
    ns = GT.grade_d(r.out)["needs_summary"]
    assert ns["paired_rows"] == 3 and ns["unpaired_rows"] == 0
    assert ns["hunger_client_server_max_diff"] == pytest.approx(0.01)


@pytest.mark.parametrize("mode", MODES)
def test_damage_watch_is_polled_since_the_last_index_and_merged_tagged_server(tmp_path, monkeypatch, mode):
    r = run_session(tmp_path, monkeypatch, mode, limits={"DAY_CAP_S": 100, "DAMAGE_POLL_S": 30}, die_from=45.0,
                    drain=0.05)
    hook, calls = r.bus.damage_calls[0], [c[:2] for c in r.bus.damage_calls[1:]]
    assert hook[2] == "admin"
    t0 = calls[0][0]
    assert [round(t - t0) for t, _ in calls] == [0, 30, 60, 90] and r.out["stop"]["reason"] == "day_cap"

    def n_at(s):
        return sum(1 for d in r.mod.server_records if d["wall"] <= round((r.mod.t0 + s) * 1000))
    assert [s for _, s in calls] == [0, 0, n_at(calls[1][0]), n_at(calls[2][0])]
    assert calls[2][1] == 0 and calls[3][1] > 100
    assert all(a[3] == S.DEFAULTS["SERVER_TIMEOUT_S"] for a in r.bus.asked if a[1] == "damage.watch")
    w, last = r.day.world, n_at(calls[3][0])
    assert w.damage_counts_server == {"HEAVYLOAD": last} and len(r.mod.server_records) > last
    assert [d["side"] for d in w.damage] == ["server"] * min(last, 500)
    dm = r.out["loop"]["damage"]
    assert dm["polls"] == 5 and dm["fails"] == 0 and dm["lost"] == 0 and dm["since"] == last == dm["merged"]
    assert dm["totals"] == {"HEAVYLOAD": {"n": dm["since"], "amount": pytest.approx(0.05 * dm["since"])}}
    g = GT.grade_d(r.out)
    assert g["health_lost_by_source"]["HEAVYLOAD"]["n"] == dm["since"]
    assert any(l.startswith("health lost by source (the server's damage.watch): HEAVYLOAD") for l in g["report_lines"])


@pytest.mark.parametrize("mode", MODES)
def test_a_heavyload_death_keeps_its_record_and_the_frames_explain_it(tmp_path, monkeypatch, mode):
    r = run_session(tmp_path, monkeypatch, mode, die_from=40.0, drain=5.0, client_damage=True)
    st, death = r.out["stop"], r.out["loop"]["death"]
    assert st["reason"] == "death" and st["detail"].endswith("body.health 0") and st["wallS"] < 40.0
    assert set(death) == {"via", "detail", "wallS", "gameMin", "frame", "event", "last_decisions", "last_frames",
                          "server_damage", "client_damage", "window_ms"}
    assert death["via"] == "frame" and death["frame"]["health"] == 0.0 and death["frame"]["signal"] == "frame_health"
    assert death["event"] is None
    assert death["last_decisions"] == decisions(tmp_path)[-10:] and len(death["last_decisions"]) == 10
    lf = death["last_frames"]
    assert len(lf) == fr_n(r.out) and lf[-1]["body"]["health"] == 0.0 and lf[0]["body"]["health"] == 100.0
    assert all(set(f) >= {"seq", "wallMs", "me", "body", "load", "zombies"} for f in lf)
    assert [f["seq"] for f in lf] == sorted(f["seq"] for f in lf)
    assert len(death["server_damage"]) == 20 == len(r.mod.server_records)
    assert {d["tag"] for d in death["server_damage"]} == {"HEAVYLOAD"} and death["server_damage"][0]["i"] == 1
    assert [d["side"] for d in death["client_damage"]] == ["client"]
    assert death["window_ms"]["to"] - death["window_ms"]["from"] == S.DEFAULTS["DEATH_WINDOW_S"] * 1000
    g = GT.grade_d(r.out)
    assert g["survived"] is False and g["outcome"] == "died" and g["death_explained"] is True
    assert g["death_explained_by"] == "tagged"
    c = g["death_check"]
    assert c["health_fall"] == pytest.approx(100.0) and c["server_amount"] == pytest.approx(100.0)
    assert c["server_n"] == 20 and c["frames_n"] == len(lf) and c["why"] is None and c["tagged"]["explained"] is True
    assert c["wound"]["explained"] is False and c["wound"]["why"] == "no wound in the window's frames"
    assert c["frames_window_ms"] == {"from": lf[0]["wallMs"], "to": lf[-1]["wallMs"]}
    assert c["server_window_ms"]["from"] == lf[0]["wallMs"] and c["server_tags"] == {"HEAVYLOAD": 100.0}
    assert g["health_lost_by_source"] == {"HEAVYLOAD": {"n": 20, "amount": 100.0}}
    assert any(l.startswith("death explained by the frames") for l in g["report_lines"])
    assert "final_error" not in r.out["loop"]["damage"]                        # the final read ran
    if mode == "polls":
        assert r.out["loop"]["polls_joined"] is True


@pytest.mark.parametrize("mode", MODES)
def test_a_silent_link_stops_the_loop_as_bus_dead(tmp_path, monkeypatch, mode):
    r = run_session(tmp_path, monkeypatch, mode, silent_from=10.0)
    st = r.out["stop"]
    silent = 10.0 - (r.day.t_loop0 - r.mod.t0)
    assert st["reason"] == "bus_dead" and "no link line" in st["detail"]
    assert 60 <= st["wallS"] - silent < 61


@pytest.mark.parametrize("mode", MODES)
def test_a_lua_error_storm_stops_the_loop(tmp_path, monkeypatch, mode):
    r = run_session(tmp_path, monkeypatch, mode, lua_err_from=8.0)
    st = r.out["stop"]
    assert st["reason"] == "lua_error_storm" and "11 lua_error events" in st["detail"]
    assert r.out["frames"]["lua_errors"] == 11 and sum(r.out["loop"]["lua_errors_per_min"].values()) == 11
    assert len(r.out["frames"]["lua_error_msgs"]) == 11


@pytest.mark.parametrize("mode", MODES)
def test_two_consecutive_low_reads_stop_on_memory_and_one_does_not(tmp_path, monkeypatch, mode):
    reads = iter([0.4, 0.4])
    r = run_session(tmp_path, monkeypatch, mode, limits={"MEM_POLL_S": 10}, free=lambda: next(reads))
    st = r.out["stop"]
    assert st["reason"] == "memory" and "2 consecutive reads below 0.5 GB" in st["detail"]
    assert st["wallS"] == pytest.approx(20, abs=0.2) and [m["free_gb"] for m in r.out["memory_reads"]] == [0.4, 0.4]
    alt = iter([0.4, 3.0] * 10)
    r = run_session(tmp_path / "b", monkeypatch, mode, limits={"DAY_CAP_S": 60, "MEM_POLL_S": 10},
                    free=lambda: next(alt))
    assert r.out["stop"]["reason"] == "day_cap" and len(r.out["memory_reads"]) >= 5
    r = run_session(tmp_path / "c", monkeypatch, mode, limits={"MEM_POLL_S": 10}, free=lambda: None)
    assert r.out["stop"]["reason"] == "memory" and len(r.out["memory_reads"]) == 2


@pytest.mark.parametrize("mode", MODES)
def test_a_players_reply_without_the_user_is_a_death_with_its_record(tmp_path, monkeypatch, mode):
    r = run_session(tmp_path, monkeypatch, mode, limits={"SERVER_POLL_S": 5}, bus={"gone_from": 35.0})
    st = r.out["stop"]
    assert st["reason"] == "death" and "players reply without admin" in st["detail"]
    death = r.out["loop"]["death"]
    assert death["via"] == "players" and death["frame"] is None and len(death["last_frames"]) == fr_n(r.out)
    g = GT.grade_d(r.out)
    assert g["death_explained"] is False and g["death_explained_by"] is None and g["deaths"][0]["via"] == "players"


@pytest.mark.parametrize("mode", MODES)
def test_no_good_server_reply_for_two_polls_stops_the_loop_as_bus_dead(tmp_path, monkeypatch, mode):
    r = run_session(tmp_path, monkeypatch, mode, bus={"stats_bad_from": 0.0, "players_bad_from": 0.0})
    st = r.out["stop"]
    assert st["reason"] == "bus_dead" and "2 consecutive failed server polls" in st["detail"]
    assert st["wallS"] == pytest.approx(60, abs=0.3) and r.out["loop"]["server_fails"] == 2


@pytest.mark.parametrize("mode", MODES)
def test_a_players_error_reply_is_no_death(tmp_path, monkeypatch, mode):
    r = run_session(tmp_path, monkeypatch, mode, limits={"DAY_CAP_S": 30, "SERVER_POLL_S": 5},
                    bus={"players_error_from": 12.0})
    assert r.out["stop"]["reason"] == "day_cap" and "death" not in r.out["loop"]
    pe = r.out["loop"]["players_error"]
    assert pe is not None and "TimeoutError" in pe["reply"] and r.out["loop"]["server_fails"] == 0


# ================================================================ Session's own: limits, hooks, polls errors
def test_limits_lay_over_the_defaults_and_the_hooks_run(tmp_path, monkeypatch):
    seen = []

    class Mine(S.Session):
        def on_frame(self, line):
            seen.append(line.get("seq"))

        def extra_record(self):
            return {"mine": len(seen)}
    clock = Clock()
    sd = str(tmp_path / "sd")
    mod = DayMod(sd, clock)
    fb = FakeBus(mod)
    monkeypatch.setattr(S.DL, "time", types.SimpleNamespace(time=clock.now))
    out = S.new_out()
    xs = X.Xs(out, node=lambda side: side, server=FakeServer(mod), ask=fb.ask, clock=clock.now, sleep=mod.sleep,
              budget_s=1e9, user="admin", clients={})
    xs.path = str(tmp_path / "s.json")
    made = []

    def factory(world, actions, log_path, clk):
        made.append(log_path)
        return Survive(world, actions, log_path, clk)
    s = Mine(xs, FileTransport(sd, clock=clock.now), planner_factory=factory, clock=clock.now, sleep=mod.sleep,
             free=lambda: 30.0, limits={"DAY_CAP_S": 10, "LAST_FRAMES": 20})
    assert s.lim["DAY_CAP_S"] == 10 and s.lim["SERVER_POLL_S"] == 60 and S.DEFAULTS["DAY_CAP_S"] == 840
    assert made == [os.path.join(str(tmp_path), S.DECISION_LOG)]
    s.run()
    assert out["stop"]["reason"] == "day_cap" and out["loop"]["mine"] == len(seen) == out["frames"]["n"] > 0
    assert len(out["loop"]["last_frames"]) == 20


def test_a_poll_threads_raising_read_counts_as_a_failed_poll(tmp_path, monkeypatch):
    def setup(sess):
        def boom(*a, **k):
            raise RuntimeError("bus gone")
        monkeypatch.setattr(S.DL, "bus_stats", boom)
        sess.players = boom
    r = run_session(tmp_path, monkeypatch, "polls", setup=setup)
    st = r.out["stop"]
    assert st["reason"] == "bus_dead" and "2 consecutive failed server polls" in st["detail"]
    assert r.out["loop"]["server_fails"] == 2 and r.out["loop"]["poll_errors"][0]["name"] == "stats"


class SlowBus:
    """A bus whose stats.all sleeps 2 s of real time on the caller's thread (the PollThread's worker); it never moves
    the fake clock, and records the loop's tick count at the read's entry and exit and the thread it ran on."""

    def __init__(self):
        self.mod, self.sess, self.reads, self.inner = None, None, [], None

    def bind(self, mod):
        self.mod = mod
        self.inner = FakeBus(mod, bus_s=0.0)

    def ask(self, node, cmd, args, timeout=30):
        if cmd == "stats.all" and self.sess is not None and self.sess.t_loop0 is not None:
            row = {"thread": threading.get_ident(), "ticks_in": self.sess.ticks}
            time.sleep(2.0)
            row["ticks_out"] = self.sess.ticks
            self.reads.append(row)
        return self.inner.ask(node, cmd, args, timeout)


def test_a_poll_thread_session_never_blocks_the_loop_on_a_slow_server_read(tmp_path, monkeypatch):
    bus = SlowBus()

    def setup(sess):
        bus.sess = sess

    def slow(mod_sleep):
        def sleep(dt):
            time.sleep(0.005)                                                 # the loop spans real time
            mod_sleep(dt)
        return sleep
    main = threading.get_ident()
    r = run_session(tmp_path, monkeypatch, limits={"DAY_CAP_S": 60}, bus=bus, setup=setup,
                    polls=lambda clock: P.PollThread(clock=clock.now), sleep=slow)
    assert r.out["stop"]["reason"] == "day_cap" and r.out["stop"]["wallS"] == pytest.approx(60, abs=0.2)
    assert bus.reads, "no stats read ran"
    first = bus.reads[0]
    assert first["thread"] != main
    assert first["ticks_out"] > first["ticks_in"]                             # the loop ticked through the 2 s read
    loop = r.out["loop"]
    assert loop["server_polls"] >= 1 and r.day.world.server["stats"]["Hunger"] == pytest.approx(0.11)
    assert len(loop["needs"]) == loop["server_polls"] and loop["server_fails"] == 0
    assert loop["needs_pairs"] and all(p["paired"] is True and p["dtMs"] <= 1000.0 for p in loop["needs_pairs"])
    assert loop["polls_joined"] is True
    assert r.day.polls._thread is not None and not r.day.polls._thread.is_alive()


# ================================================================ fix 1: the join, the defaults' cadence
class BlockingBus:
    """A bus whose loop stats.all read blocks on an event (set by the test after the run) on the worker; it counts
    the calls in flight at once, so a second caller while the first is blocked shows as max_in_flight 2."""

    def __init__(self):
        self.mod, self.sess, self.inner = None, None, None
        self.release = threading.Event()
        self.lock = threading.Lock()
        self.in_flight = self.max_in_flight = 0
        self.blocked = threading.Event()

    def bind(self, mod):
        self.mod = mod
        self.inner = FakeBus(mod, bus_s=0.0)

    def ask(self, node, cmd, args, timeout=30):
        with self.lock:
            self.in_flight += 1
            self.max_in_flight = max(self.max_in_flight, self.in_flight)
        try:
            if cmd == "stats.all" and self.sess is not None and self.sess.t_loop0 is not None:
                self.blocked.set()
                self.release.wait(10.0)
            return self.inner.ask(node, cmd, args, timeout)
        finally:
            with self.lock:
                self.in_flight -= 1


def test_a_read_past_the_join_skips_the_final_damage_read_and_never_overlaps_it(tmp_path, monkeypatch):
    bus = BlockingBus()

    def setup(sess):
        bus.sess = sess

    def paced(mod_sleep):
        def sleep(dt):
            if bus.sess is not None and bus.sess.t_loop0 is not None:
                bus.blocked.wait(5.0)                                         # the worker is in its read first
            mod_sleep(dt)
        return sleep
    t0 = time.time()
    try:
        r = run_session(tmp_path, monkeypatch, bus=bus, setup=setup, sleep=paced, die_from=20.0, drain=5.0,
                        polls=lambda clock: P.PollThread(clock=clock.now), polls_join_s=0.2)
    finally:
        bus.release.set()
    took = time.time() - t0
    loop = r.out["loop"]
    assert r.out["stop"]["reason"] == "death" and loop["polls_joined"] is False
    assert loop["damage"]["final_error"] == "poll worker still in a read"
    assert bus.max_in_flight == 1                                             # no second caller during the read
    assert loop["death"]["via"] == "frame" and loop["death"]["last_frames"][-1]["body"]["health"] == 0.0
    assert any("did not end within 0.2s" in n["note"] for n in r.out["notes"])
    assert took < 10.0                                                        # one 0.2 s join, not a wait per path
    assert r.day.polls_join_s == 0.2
    assert _until(lambda: not r.day.polls.alive())                           # released: the worker ends


def test_the_join_timeout_covers_the_longest_read_by_default(tmp_path):
    out = S.new_out()
    xs = X.Xs(out, node=lambda side: side, ask=lambda *a, **k: None, budget_s=1e9, user="admin")
    xs.path = str(tmp_path / "s.json")
    s = S.Session(xs, FileTransport(str(tmp_path / "sd"), clock=time.time), polls=P.PollThread())
    assert s.polls_join_s == S.STEP_TIMEOUT_S + xs.ping_timeout_s == 35.0


@pytest.mark.parametrize("mode", ("sync", "thread"))
def test_a_clean_day_at_the_library_defaults(tmp_path, monkeypatch, mode):
    """DAMAGE_POLL_S 5 (the library's default, every new driver's), synchronous and through a real PollThread."""
    kw = {}
    if mode == "thread":
        def paced(mod_sleep):
            def sleep(dt):
                time.sleep(0.01)                                              # the worker keeps up in real time
                mod_sleep(dt)
            return sleep

        class Bus0:
            def bind(self, mod):
                self.inner = FakeBus(mod, bus_s=0.0)                         # the worker never moves the fake clock
                self.mod = mod

            def ask(self, *a, **k):
                return self.inner.ask(*a, **k)
        kw = dict(bus=Bus0(), sleep=paced, polls=lambda clock: P.PollThread(clock=clock.now, idle_s=0.001))
    r = run_session(tmp_path, monkeypatch, port=False, limits={"DAY_CAP_S": 40}, die_from=20.0, drain=0.05,
                    floor=80.0, **kw)
    fb = r.bus.inner if mode == "thread" else r.bus
    assert r.out["stop"]["reason"] == "day_cap" and r.out["stop"]["wallS"] == pytest.approx(40, abs=0.2)
    assert r.out["phase_errors"] == {}
    calls = fb.damage_calls[1:]                                               # the hook's install first
    gaps = [b[0] - a[0] for a, b in zip(calls, calls[1:])]
    assert len(calls) >= 7 and all(abs(g - 5.0) <= 0.6 for g in gaps), gaps          # a bus call costs bus_s
    sinces = [c[1] for c in calls]
    assert sinces == sorted(sinces) and sinces[-1] > 0                        # since advances with the records
    dm = r.out["loop"]["damage"]
    assert dm["fails"] == 0 and dm["lost"] == 0 and dm["since"] == dm["merged"] > 0
    loop = r.out["loop"]
    assert loop["needs_pairs"] and all(p["paired"] is True for p in loop["needs_pairs"])
    assert len(loop["needs"]) == loop["server_polls"] == 1 and loop["server_fails"] == 0
    if mode == "thread":
        assert loop["polls_joined"] is True


# ================================================================ record
def test_action_rows_and_the_loop_summary_read_the_session(tmp_path, monkeypatch):
    a = types.SimpleNamespace(aid="a1", type="scan", args={"r": 10}, state="done", reason="", sent_wall=12.0,
                              ended_wall=13.5)
    b = types.SimpleNamespace(aid="a2", type="walk", args={}, state="sent", reason="", sent_wall=14.0, ended_wall=None)
    assert R.action_rows([a, b], 10.0) == [
        {"aid": "a1", "type": "scan", "args": {"r": 10}, "state": "done", "reason": "", "sentS": 2.0, "endedS": 3.5},
        {"aid": "a2", "type": "walk", "args": {}, "state": "sent", "reason": "", "sentS": 4.0, "endedS": None}]
    r = run_session(tmp_path, monkeypatch, limits={"DAY_CAP_S": 5})
    summ = R.loop_summary(r.day)
    for k in ("wallS", "ticks", "decisions", "last_decisions", "needs", "needs_fields", "needs_pairs", "fights",
              "actions", "lua_errors_per_min", "cost", "server_polls", "server_fails", "players_error", "memory",
              "damage", "first_game_min", "first_world_age", "game_min", "last_frames"):
        assert k in summ, k
    assert summ["ticks"] == r.out["loop"]["ticks"]


def test_action_rows_carry_each_sends_branch_and_a_consumes_use(tmp_path):
    """Plan 23 Task 16c: Session.planner_tick keeps, per sent aid, the planner's `last_branch` (None for a planner
    without one) and, for a consume, the item's use off `world.by_use()` at the send (None when the id is not held);
    record.action_rows lays them on the rows (`branch` on every row, `use` on consume rows only)."""
    sends = []

    class Stub:
        def __init__(self, world, actions, log_path, clock):
            self.last_branch = None

        def tick(self, world, actions):
            if not sends:
                return None
            branch, a = sends.pop(0)
            self.last_branch = branch
            return a

    out = S.new_out()
    xs = X.Xs(out, node=lambda side: side, ask=lambda *a, **k: None, budget_s=1e9, user="admin")
    xs.path = str(tmp_path / "s.json")
    s = S.Session(xs, FileTransport(str(tmp_path / "sd"), clock=time.time), planner_factory=Stub)
    s.world.inventory[701] = {"fullType": "Base.WaterBottle", "weight": 1.0, "use": "water"}
    s.world.inventory[702] = {"fullType": "Base.Apple", "weight": 0.2}
    def mk(aid, typ, args):
        return types.SimpleNamespace(aid=aid, type=typ, args=args, state="sent", reason="", sent_wall=11.0,
                                     ended_wall=None)
    sends.extend([("need", mk("a1", "consume", {"itemId": 701})), ("need", mk("a2", "consume", {"itemId": 702})),
                  ("load", mk("a3", "drop", {"itemId": 702})), ("need", mk("a4", "consume", {"itemId": 999}))])
    for _ in range(5):
        s.planner_tick()
    assert s.sent_meta == {"a1": {"branch": "need", "use": "water"}, "a2": {"branch": "need", "use": "food"},
                           "a3": {"branch": "load"}, "a4": {"branch": "need", "use": None}}
    rows = R.action_rows(s.sent, 10.0, s.sent_meta)
    assert [(r["branch"], r.get("use", "-")) for r in rows] == [("need", "water"), ("need", "food"), ("load", "-"),
                                                                ("need", None)]
    assert all(r["sentS"] == 1.0 for r in rows)
    assert R.action_rows(s.sent, 10.0, {})[0]["branch"] is None and R.action_rows(s.sent, 10.0, {})[0]["use"] is None
    assert "branch" not in R.action_rows(s.sent, 10.0)[0]                    # no meta: the plain rows

    class Bare:                                                               # a planner with no last_branch
        def __init__(self, *a):
            pass

        def tick(self, world, actions):
            return sends.pop(0)[1] if sends else None
    s2 = S.Session(xs, FileTransport(str(tmp_path / "sd2"), clock=time.time), planner_factory=Bare)
    sends.append(("x", mk("b1", "scan", {"r": 10})))
    s2.planner_tick()
    assert s2.sent_meta == {"b1": {"branch": None}}


# ================================================================ fix wave D: the kit, the frames, the stop, the reads
def test_a_chain_session_holding_the_bat_spawns_nothing_and_equips_it(tmp_path, monkeypatch):
    """C-1: a later session of the chain holds the last session's bat; it spawns none (the chain never builds its own
    load) and equips the held one."""
    r = run_session(tmp_path, monkeypatch, limits={"DAY_CAP_S": 5}, held=True)
    kit = r.out["readings"]["kit"]
    assert r.xs.server.rcons == [] and kit["spawn"] is None
    assert kit["item"] == {"itemId": KIT_ID, "source": "held", "fullType": KIT, "seq": None, "wallMs": None}
    assert kit["equip"]["state"] == "done" and kit["weapon_frame"]["type"] == KIT
    assert kit["armed"] is True and kit["ok"] is True
    equips = [c for c in r.mod.cmds if c["type"] == "equip"]
    assert len(equips) == 1 and equips[0]["args"] == {"itemId": KIT_ID}
    # held and already in the hand: nothing sent at all
    w = run_session(tmp_path / "w", monkeypatch, limits={"DAY_CAP_S": 5}, held=True, wielded=True)
    kit = w.out["readings"]["kit"]
    assert w.xs.server.rcons == [] and kit["spawn"] is None and kit["equip"] is None
    assert kit["item"]["source"] == "held" and kit["armed"] is True and kit["ok"] is True
    assert kit["weapon_frame"]["type"] == KIT and [c for c in w.mod.cmds if c["type"] == "equip"] == []
    # a first session holds no weapon: the spawn as before
    f = run_session(tmp_path / "f", monkeypatch, limits={"DAY_CAP_S": 5})
    assert len(f.xs.server.rcons) == 1 and f.out["readings"]["kit"]["item"]["source"] == "item_added"


def test_a_wound_400_frames_before_the_death_is_kept(tmp_path, monkeypatch):
    """I-5 (session half): LAST_FRAMES covers DEATH_WINDOW_S, so the wound that opens the window is in the record."""
    r = run_session(tmp_path, monkeypatch, bite_at=5.0, die_from=48.0, drain=5.0)
    assert r.out["stop"]["reason"] == "death"
    for lf in (r.out["loop"]["last_frames"], r.out["loop"]["death"]["last_frames"]):
        bitten = [f for f in lf if f["body"].get("bitten")]
        wound = bitten[0]
        dead = next(f for f in lf if f["body"]["health"] == 0.0)
        assert dead["seq"] - wound["seq"] >= 400
        before = [f for f in lf if f["seq"] < wound["seq"]]
        assert before and not before[-1]["body"].get("bitten")                 # the rise itself is kept
        assert GT._wound(before[-1], wound) == "bitten 0 -> 1"


@pytest.mark.parametrize("mode", MODES)
def test_the_loop_ends_by_stopping_the_character(tmp_path, monkeypatch, mode):
    """I-6: at every stop the loop sends Stop and pumps until its act line and a later frame, before the poll join;
    the lineage's previous frame is then a frame after the stop."""
    r = run_session(tmp_path, monkeypatch, mode, limits={"DAY_CAP_S": 10})
    loop = r.out["loop"]
    st = loop["stopped"]
    assert r.out["stop"]["reason"] == "day_cap" and r.out["stop"]["wallS"] == pytest.approx(10, abs=0.2)
    assert st["sent"] is True and st["acked"] is True and st["state"] == "done"
    assert 0 < st["settleS"] <= S.STOP_SETTLE_S and st["wallS"] == pytest.approx(10, abs=0.2)
    assert r.mod.cmds[-1]["type"] == "stop" and r.mod.cmds[-1]["aid"] == st["aid"]
    assert loop["last_frame_after_stop"] is True and loop["last_frames"][-1]["seq"] > st["ack_seq"]
    persisted = json.loads((tmp_path / "session.json").read_text(encoding="utf-8"))
    assert persisted["loop"]["stopped"] == st and persisted["loop"]["last_frame_after_stop"] is True
    if mode == "polls":
        assert loop["polls_joined"] is True


def test_a_stop_never_acked_settles_at_its_cap(tmp_path, monkeypatch):
    r = run_session(tmp_path, monkeypatch, silent_from=10.0)
    st = r.out["loop"]["stopped"]
    assert r.out["stop"]["reason"] == "bus_dead"
    assert st["sent"] is True and st["acked"] is False and st["ack_seq"] is None
    assert st["settleS"] == pytest.approx(S.STOP_SETTLE_S, abs=0.15)
    assert r.out["loop"]["last_frame_after_stop"] is False


def test_server_reads_are_one_helper_behind_due_and_latest(tmp_path, monkeypatch):
    """M-9: the synchronous path and the PollThread path behind ServerReads (reads.py): due(now) runs the sync
    path's due reads, latest() returns each new result once; Session keeps no read of its own."""
    from agent.driverlib import reads as RD
    for gone in ("server_poll", "merge_polls", "merge_stats", "damage_merge", "damage_read", "start_polls",
                 "end_polls", "_half", "check_fails"):
        assert not hasattr(S.Session, gone), gone
    r = run_session(tmp_path, monkeypatch, limits={"DAY_CAP_S": 3})
    rd = r.day.reads
    assert isinstance(rd, RD.ServerReads) and rd.polls is None and r.day.polls is None
    assert rd.latest() == []                                                   # all merged
    now = r.clock.now() + 100.0
    rd.due(now)
    got = rd.latest()
    assert [g[0] for g in got] == ["stats", "players", "damage"] and all(g[2] is None for g in got)
    assert rd.latest() == []
    rd.due(now + 1.0)
    assert rd.latest() == []                                                   # none due a second later
    p = run_session(tmp_path / "p", monkeypatch, "polls", limits={"DAY_CAP_S": 3})
    assert p.day.reads.polls is p.day.polls
    assert p.out["loop"]["server_polls"] == r.out["loop"]["server_polls"] == 1


# ================================================================ residual D: the stop wakes a sleeper, the kit's first sight
def _quiet(sess):
    sess.planner_tick = lambda: None                  # the planner sends nothing: the test's own actions only


def test_the_closing_stop_wakes_a_sleeper_and_records_it(tmp_path, monkeypatch):
    """P23-AE: the loop's Stop ends a running sleep (`failed superseded`); loop.stopped.woke says so."""
    def setup(sess):
        _quiet(sess)
        loop = sess.phase_loop

        def sleep_first():
            sess.actions.send(pza1.Sleep())
            return loop()
        sess.phase_loop = sleep_first
    r = run_session(tmp_path, monkeypatch, limits={"DAY_CAP_S": 3}, setup=setup)
    sl = next(a for a in r.day.actions.history if a.type == "sleep")
    assert sl.state == "failed" and sl.reason == "superseded"
    assert r.out["loop"]["stopped"]["woke"] is True and r.out["loop"]["stopped"]["acked"] is True
    q = run_session(tmp_path / "q", monkeypatch, limits={"DAY_CAP_S": 3}, setup=_quiet)
    assert q.out["loop"]["stopped"]["woke"] is False


def test_the_kit_waits_for_a_late_first_sight_and_keeps_the_bat(tmp_path, monkeypatch):
    """N-2: the held bat's item_added arrives two ticks behind the first frame (load.n 1): no spawn, the bat equipped."""
    r = run_session(tmp_path, monkeypatch, limits={"DAY_CAP_S": 5}, held=True, first_sight_ticks=2)
    kit = r.out["readings"]["kit"]
    fs = kit["first_sight"]
    assert fs["loadN"] == 1 and fs["items"] == 1 and fs["complete"] is True and fs["waitMs"] > 0
    assert r.xs.server.rcons == [] and kit["spawn"] is None
    assert kit["item"]["source"] == "held" and kit["item"]["itemId"] == KIT_ID
    assert kit["armed"] is True and kit["ok"] is True
    assert [c["args"] for c in r.mod.cmds if c["type"] == "equip"] == [{"itemId": KIT_ID}]


def test_the_kit_matches_its_spawn_by_a_new_id_not_a_late_older_bat(tmp_path, monkeypatch):
    """N-2: no bat at the first sight (load.n 0, complete at once): a spawn; an older bat's event lands before the
    spawn's own on the same tick, and the spawn is matched by its id, so the older one is never equipped."""
    r = run_session(tmp_path, monkeypatch, limits={"DAY_CAP_S": 5}, late_old=True)
    kit = r.out["readings"]["kit"]
    assert kit["first_sight"]["loadN"] == 0 and kit["first_sight"]["complete"] is True
    assert len(r.xs.server.rcons) == 1 and kit["item"]["source"] == "item_added"
    assert kit["item"]["itemId"] == KIT_ID
    assert [c["args"] for c in r.mod.cmds if c["type"] == "equip"] == [{"itemId": KIT_ID}]


# ================================================================ PZA/1.3: the death event (ruling P23-AO)
@pytest.mark.parametrize("mode", MODES)
def test_the_death_event_stops_the_loop_when_the_health_never_reads_0(tmp_path, monkeypatch, mode):
    """The fourth chain's death: the client's health froze above 0 on the dead character and no frame read 0; the Lua's
    death event ends the loop, named by its seq, and its frame is the death frame."""
    r = run_session(tmp_path, monkeypatch, mode, die_from=20.0, drain=0.5, death_at=30.0)
    st, death = r.out["stop"], r.out["loop"]["death"]
    ev = death["event"]
    assert st["reason"] == "death" and st["detail"] == "event death seq %s via hook body.health %s" % (
        ev["seq"], ev["health"])
    assert death["via"] == "event" and 0.0 < ev["health"] < 100.0 and ev["zombiesKilled"] == 0
    assert set(ev) == {"seq", "wallMs", "gameMin"} | set(pza1.EVENT_FIELDS["death"])
    df = death["frame"]
    assert df["signal"] == "event" and df["seq"] == ev["seq"] and df["health"] == ev["health"]
    assert df["event"] == ev and df["frameSeq"] == ev["seq"] + 1          # the frame the Lua wrote after it
    lf = r.out["loop"]["last_frames"]
    assert all(f["body"]["health"] > 0.0 for f in lf)                     # no 0 frame: the event alone stopped it
    assert lf[-1]["seq"] > df["frameSeq"] and lf[-1]["body"]["health"] == ev["health"]   # the frames go on after it
    g = GT.grade_d(r.out)
    assert g["survived"] is False and g["deaths"][0]["via"] == "event"


@pytest.mark.parametrize("mode", MODES)
def test_a_0_frame_before_the_event_stays_the_death_frame_and_the_event_is_kept(tmp_path, monkeypatch, mode):
    r = run_session(tmp_path, monkeypatch, mode, die_from=40.0, drain=5.0, death_at=42.0)
    death = r.out["loop"]["death"]
    assert r.out["stop"]["detail"].startswith("frame seq ") and death["via"] == "frame"
    assert death["frame"]["signal"] == "frame_health" and death["frame"]["health"] == 0.0
    assert death["event"] is not None and death["event"]["seq"] > death["frame"]["seq"]   # read in the stop's settle


def test_only_the_first_death_event_is_kept_and_another_kind_is_no_death(tmp_path):
    xs = types.SimpleNamespace(user="admin", out=S.new_out(), path=None, copied=[])
    sess = S.Session.__new__(S.Session)
    sess.out, sess.death_frame, sess.death_event, sess.shots = xs.out, None, None, None
    sess.mark_shot = lambda final=None: None
    sess.read_death_event({"kind": "event", "event": "death", "seq": 7, "wallMs": 1, "gameMin": 5.0, "worldAge": 1.0,
                           "x": 1.0, "y": 2.0, "z": 0, "health": 19.5, "zombiesKilled": 1, "via": "isDead"})
    sess.read_death_event({"kind": "event", "event": "death", "seq": 9, "health": 3.0})
    assert sess.death_event["seq"] == 7 and sess.death_frame["seq"] == 7 and sess.death_via() == "event"
    with pytest.raises(S.Stop) as e:
        sess.check_lines.__func__(types.SimpleNamespace(death_frame=sess.death_frame), 0.0)
    assert e.value.reason == "death" and e.value.detail == "event death seq 7 via isDead body.health 19.5"


def test_a_new_day_sessions_grade_is_grade_e5_under_its_own_key(monkeypatch):
    """CLAUDE.md section 5 freezing (Plan 24 Task 20): a new session's record carries grade_e5 under the key grade_e5
    (grade_e4 was the key until the E7 session; e_grade_4.py grades that artifact)."""
    from agent.base import gates_e as GE
    assert DY.GRADE_KEY == "grade_e5"
    out = S.new_out()
    out.update(stop={"reason": "day_cap", "detail": "x", "wallS": 1.0})
    DY.grade_day(out)
    assert out["grade_e5"]["grade"] == "grade_e5" and "grade_e1" not in out and "grade_e2" not in out
    monkeypatch.setattr(GE, "grade_e5", lambda o, **kw: 1 / 0)
    bad = {}
    DY.grade_day(bad)
    assert bad["grade_e5_error"].startswith("ZeroDivisionError") and "grade_e5" not in bad


def test_the_record_carries_the_results_of_the_sent_actions_of_the_care_types():
    from agent.base.actions import Action
    xs = types.SimpleNamespace(copied=[], out=S.new_out(), user="admin", path=None)
    c = DY.Chain(xs, None, planner_factory=Survive, clock=lambda: 5.0)
    rows = [("a1", "bandage", {"part": 3}), ("a2", "consume", {"itemId": 1}), ("a3", "fill", None),
            ("a4", "fill", {"fluid": "Water"})]
    for aid, t, res in rows:
        a = Action(aid, t, {}, 5.0, 1.0)
        a.state, a.result = "done", res
        c.sent.append(a)
    assert c.extra_record()["results"] == [{"aid": "a1", "type": "bandage", "state": "done", "result": {"part": 3}},
                                           {"aid": "a4", "type": "fill", "state": "done",
                                            "result": {"fluid": "Water"}}]
    assert "consume" not in DY.RESULT_TYPES


def test_the_run_copy_carries_every_state_log_rotation(tmp_path):
    """Plan 24 Task 20: E7's state.1.log (the Lua rotates state.log on a long session) was not in the controller's copy;
    copy_run takes state.log and every state.<n>.log of the state dir byte-identical, and nothing else."""
    state = tmp_path / "run" / "clients" / "admin" / "Lua" / "pzagent" / "admin"
    state.mkdir(parents=True)
    for name, data in (("state.log", b"aa"), ("state.1.log", b"bb"), ("state.2.log", b"cc"),
                       ("cmd.txt", b"x"), ("ack.txt", b"y"), ("state.bak", b"z")):
        (state / name).write_bytes(data)
    repo = tmp_path / "repo"
    got = DY.copy_state_logs(str(repo), "r-1", str(state))
    dest = repo / "testing" / "artifacts" / "r-1"
    assert sorted(os.path.basename(p) for p in got) == ["state.1.log", "state.2.log", "state.log"]
    assert sorted(os.listdir(dest)) == ["state.1.log", "state.2.log", "state.log"]
    assert (dest / "state.1.log").read_bytes() == b"bb" and (dest / "state.log").read_bytes() == b"aa"
    assert DY.copy_state_logs(str(repo), "r-2", str(tmp_path / "none")) == []
    # through copy_run: the user's state dir under the run dir, found without out["state_dir"], and with it
    artifact = tmp_path / "run" / "a.json"
    artifact.write_text("{}", encoding="utf-8")
    for out in ({}, {"state_dir": str(state)}):
        copied = []
        xs = types.SimpleNamespace(user="admin", out=out, copy_artifacts=lambda *a: copied.append(a) or "d")
        r = "r-3" if not out else "r-4"
        assert DY.copy_run(xs, str(repo), r, str(tmp_path / "run"), "a.json") == "d" and len(copied) == 1
        assert sorted(os.listdir(repo / "testing" / "artifacts" / r)) == ["state.1.log", "state.2.log", "state.log"]
    src = open(DY.__file__, encoding="utf-8").read()
    assert src.index("copy_state_logs(repo, run_id") < src.index("xs.copy_artifacts(repo, run_id")
