"""drivers/c_survive.py, drivers/c_survive_dense.py, drivers/c_grade.py and agent/grade_c.py (Plan 21 Task 12), offline:
the driver is never invoked.

The loop runs against a SurviveMod that plays PZAgent's Lua into a tmp state dir with the real line shapes (hello
{modVersion, build, user, rate, mode}; ack {cmdSeq, ok, reason}; frame {x, y, z, health, hunger, thirst, fatigue,
gameMin, worldAge, weapon?, zombies, goal {seq, name, state, detail}, cost {pollMs, actMs, scanStepMs, senseMs, linkMs,
dropped, scanEmitMs}}; scan {r, squares, missing, scanMs, scanTicks}; event goal_done {goalSeq} / goal_failed {goalSeq,
reason}, lua_error {msg}, zombie_leave {id}) on an injected clock, and the server's replies in the harness's own shapes
(stats.all {side, user, worldAge, mult, wall, stats {<registry id>: value}, missing}; players [<username>, ...], {} when
nobody is online; a failed read a string)."""
import json
import math
import os
import types

import pytest

from agent import grade_c as GC
from agent.drivers import c_grade as CG
from agent.drivers import c_survive as D
from agent.drivers import c_survive_dense as DD
from agent.link import Link

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
X = D.X


# ================================================================ static: refusal, constants, the dense variant
@pytest.mark.parametrize("mod,name,call", [(D, "c_survive.py", "    main()"), (DD, "c_survive_dense.py",
                                                                             "    CS.main(SPEC, _ME)")])
def test_each_driver_refuses_arguments_before_main(mod, name, call):
    with open(mod.__file__, encoding="utf-8") as fh:
        src = fh.read()
    i_ref, i_main = src.index("refusal = parse_argv(sys.argv[1:], __file__)"), src.rindex(call)
    assert src.index('if __name__ == "__main__":') < i_ref < i_main
    assert "sys.exit(refusal)" in src[i_ref:i_main]
    assert "%s takes no arguments" % name in mod.parse_argv(["x"], mod.__file__)
    assert mod.parse_argv(["--help"], mod.__file__) and mod.parse_argv([], mod.__file__) is None


def test_the_constants_name_the_drivers_own_file_and_profile():
    assert os.path.basename(D.__file__) == D.DRIVER == D.KEY + ".py" and D.ARTIFACT == D.KEY + ".json"
    assert (D.KEY, D.PROFILE, D.ARTIFACT) == ("c_survive", "testing/profiles/agent.toml", "c_survive.json")
    assert (D.BUDGET_S, D.USER, D.MIN_FREE_GB) == (5700.0, "admin", 12.0)
    assert (D.PLANNER_HZ, D.SERVER_POLL_S, D.PERSIST_S, D.MEM_POLL_S, D.DAY_CAP_S) == (2, 60, 30, 300, 5400)
    assert (D.BUS_DEAD_S, D.STORM_N, D.STORM_WINDOW_S, D.KIT) == (60, 10, 60, "Base.BaseballBat")
    assert D.SPEC == (D.KEY, D.DRIVER, D.PROFILE, D.ARTIFACT)
    assert os.path.isfile(os.path.join(REPO, D.PROFILE))


def test_the_dense_driver_differs_only_by_its_names_and_imports_the_rest():
    assert os.path.basename(DD.__file__) == DD.DRIVER == DD.KEY + ".py" and DD.ARTIFACT == DD.KEY + ".json"
    assert (DD.KEY, DD.PROFILE, DD.ARTIFACT) == ("c_survive_dense", "testing/profiles/agent-dense.toml",
                                                 "c_survive_dense.json")
    assert DD.SPEC == (DD.KEY, DD.DRIVER, DD.PROFILE, DD.ARTIFACT) and os.path.isfile(os.path.join(REPO, DD.PROFILE))
    assert DD.Survive is D.Survive and DD.parse_argv is D.parse_argv and DD.BUDGET_S == D.BUDGET_S
    src = open(DD.__file__, encoding="utf-8").read()
    assert "class " not in src and "def main" not in src


def test_main_clears_the_state_dir_through_the_boot_seam_and_gates_memory_before_the_boot():
    src = open(D.__file__, encoding="utf-8").read()
    assert "make_client=clearing_make_client(session.make_client)" in src
    i_x, i_g, i_b = src.index("xs = X.Xs("), src.index("memory_gate(xs)"), src.index("DL.boot(")
    assert i_x < i_g < i_b
    assert "sv = Survive(xs, DL.link_for(clients, USER))" in src and 'out["finished"] = True' in src
    assert "xs.copy_artifacts(REPO, run_id, run_dir, spec.artifact)" in src


# ================================================================ pre-boot, on the real profiles
def stub_checks(monkeypatch, dirty=None, lint=(), tracked=""):
    dirty = dirty or {}
    monkeypatch.setattr(D.DL.C, "doctor", lambda: (True, "ok"))
    monkeypatch.setattr(D.DL.harness, "lint_paths", lambda srcs: list(lint))
    monkeypatch.setattr(D.DL.C, "git_dirty", lambda rel: (dirty.get(rel, False), ""))
    real = D.DL.C.git_say
    monkeypatch.setattr(D.DL.C, "git_say", lambda *a: tracked if a[0] == "ls-files" else real(*a))


CLEAN = {"driver_file": True, "driver_prefix": True, "profile_exists": True, "no_committed_artifact": True,
         "agent_lua_dirty": False, "agent_py_dirty": False, "driver_dirty": False}


def test_preboot_on_the_real_profiles(agent_fixture, monkeypatch):
    stub_checks(monkeypatch)
    pre, ok = D.preboot(D.__file__)
    assert ok, pre
    assert pre["profile"] == "agent" and pre["lint_errors"] == [] and pre["driver_checks"] == CLEAN
    pre, ok = DD.preboot(DD.__file__)
    assert ok, pre
    assert pre["profile"] == "agent-dense" and pre["driver_checks"] == CLEAN


def test_preboot_refuses(agent_fixture, monkeypatch):
    stub_checks(monkeypatch, tracked="testing/artifacts/c_survive-20261026-120000/c_survive.json")
    pre, ok = D.preboot(D.__file__)
    assert not ok and pre["driver_checks"]["no_committed_artifact"] is False
    for rel in ("testing/PZAgent", "testing/agent", "testing/agent/drivers/c_survive.py"):
        stub_checks(monkeypatch, dirty={rel: True})
        assert D.preboot(D.__file__)[1] is False, rel
    stub_checks(monkeypatch, dirty={"testing/agent/drivers/c_survive_dense.py": True})
    assert DD.preboot(DD.__file__)[1] is False and D.preboot(D.__file__)[1] is True
    stub_checks(monkeypatch, lint=["ERROR x"])
    assert D.preboot(D.__file__)[1] is False
    stub_checks(monkeypatch)
    assert D.preboot(DD.__file__)[1] is False and DD.preboot(D.__file__)[1] is False   # each file under its own spec


# ================================================================ pure helpers
def test_tick_cost_sums_the_cost_keys_present():
    assert D.tick_cost({"pollMs": 0.1, "actMs": 0.2, "scanStepMs": 0.0, "senseMs": 0.3, "linkMs": 0.4,
                        "dropped": 7, "scanEmitMs": 9}) == pytest.approx(1.0)
    assert D.tick_cost({"pollMs": 0.5}) == 0.5 and D.tick_cost({"dropped": 1}) is None and D.tick_cost(None) is None


def test_players_and_stats_replies_are_read_by_their_shapes():
    assert D.players_list(["admin", "bob"]) == ["admin", "bob"] and D.players_list({}) == []
    assert D.players_list("timeout") is None and D.players_list({"error": "x"}) == ["x"]
    assert D.server_stats({"stats": {"Hunger": 0.2}}) == {"Hunger": 0.2}
    assert D.server_stats("no online player admin") is None and D.server_stats({"error": "TimeoutError"}) is None


def test_decision_tail_keeps_the_last_ten_lines_read_incrementally(tmp_path):
    p = tmp_path / "decision.log"
    t = D.DecisionTail(str(p))
    t.read()
    assert t.last() == []
    with open(p, "a", encoding="utf-8") as f:
        for i in range(7):
            f.write(json.dumps({"i": i}) + "\n")
        f.write('{"i": 7')                                                     # a partial line waits
    t.read()
    assert [d["i"] for d in t.last()] == list(range(7))
    with open(p, "a", encoding="utf-8") as f:
        f.write("}\n" + "".join(json.dumps({"i": i}) + "\n" for i in range(8, 14)))
    t.read()
    assert [d["i"] for d in t.last()] == list(range(4, 14))


# ================================================================ the loop against a SurviveMod
class Clock:
    def __init__(self):
        self.t = 1_790_000_000.0

    def now(self):
        return self.t


BAT = {"type": "Base.BaseballBat", "condition": 10, "ammo": 0}


class SurviveMod:
    """PZAgent's Lua for Stage C, one tick at a time on `clock` (TPS ticks a second, a frame every FRAME_EVERY). A goal
    ends after GOAL_TICKS: goto/flee move the player and end done; fight ends done "clear" and the zombies leave; a
    scan emits its line at once; a goal's goal_done/goal_failed event lands as the Lua's does (goal_event). Knobs, each in seconds of the mod's own clock since its first tick: die_at (health 0
    from then), zombie_at (one zombie two tiles east from then until a fight clears it), lua_err_from (a lua_error
    event every second from then), silent_from (no line written from then). `mode` is the hello's."""
    TPS = 10
    FRAME_EVERY = 2
    GOAL_TICKS = 5

    def __init__(self, d, clock, die_at=None, zombie_at=None, lua_err_from=None, silent_from=None, mode="append"):
        os.makedirs(d, exist_ok=True)
        self.d, self.clock = d, clock
        self.die_at, self.zombie_at, self.lua_err_from, self.silent_from, self.mode = (
            die_at, zombie_at, lua_err_from, silent_from, mode)
        self.seq = self.tick = self.last_cmd = 0
        self.buf = []
        self.x, self.y = 100.5, 200.5
        self.health, self.hunger, self.thirst, self.fatigue = 100.0, 0.1, 0.1, 0.1
        self.weapon = None
        self.goal = None
        self.ready = False
        self.cleared = False
        self.leave = False
        self.cmds = []
        self.last_err_s = None

    def s(self):
        return self.tick / float(self.TPS)

    def silent(self):
        return self.silent_from is not None and self.s() >= self.silent_from

    def emit(self, kind, body):
        self.seq += 1
        body.update(kind=kind, seq=self.seq, tick=self.tick, wallMs=int(self.clock.t * 1000))
        self.buf.append(json.dumps(body))

    def flush(self):
        if self.buf and not self.silent():
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

    def zombies(self):
        if self.zombie_at is None or self.s() < self.zombie_at or self.cleared:
            return {}
        return [{"id": 7, "x": self.x + 2.0, "y": self.y, "dist": 2.0, "hasTarget": True, "crawler": False}]

    def scan(self, r):
        px, py = math.floor(self.x), math.floor(self.y)
        sqs = [{"x": px + dx, "y": py + dy, "z": 0, "solid": False, "containers": {}, "floor": {}}
               for dy in range(-r, r + 1) for dx in range(-r, r + 1)]
        self.emit("scan", {"r": r, "squares": sqs, "missing": {}, "scanMs": 3, "scanTicks": 1})

    def end(self, g):
        name, a = g["name"], g["argv"]
        g["state"] = "done"
        if name in ("goto", "flee"):
            self.x, self.y = float(a[0]) + 0.5, float(a[1]) + 0.5
            g["detail"] = "d=0.1" if name == "goto" else "at"
        elif name == "fight":
            g["detail"] = "clear"
            self.cleared = True
            self.leave = True                   # zombie_leave is a sense event: it lands on the next frame tick
        elif name in ("eat", "drink"):
            g["detail"] = "consumed"
        elif name == "loot":
            g["state"], g["detail"] = "failed", "empty"
        else:
            g["detail"] = "awake"

    def goal_event(self, g):
        """PZAgent_Main.lua's goalEvent: once per goal seq, on the frame tick that first sees it end (before that
        frame), or at once for a goal a new command superseded."""
        if g is None or g["state"] not in ("done", "failed") or g.get("reported"):
            return
        g["reported"] = True
        ev = {"event": "goal_done", "goalSeq": g["seq"]}
        if g["state"] == "failed":
            ev.update(event="goal_failed", reason=g["detail"])
        self.emit("event", ev)

    def step(self):
        self.clock.t += 1.0 / self.TPS
        self.tick += 1
        if self.die_at is not None and self.s() >= self.die_at:
            self.health = 0.0
        cmd = self.poll()
        if cmd:
            self.cmds.append(cmd)
            a = cmd["args"].split()
            if cmd["goal"] == "scan":
                self.scan(int(a[0]))
            else:
                old = self.goal
                if old is not None and old["state"] == "running":
                    old["state"], old["detail"] = "failed", "superseded"
                self.goal_event(old)
                self.goal = {"seq": cmd["seq"], "name": cmd["goal"], "argv": a, "state": "running", "detail": "",
                             "ticks": 0}
            self.emit("ack", {"cmdSeq": cmd["seq"], "ok": True, "reason": "queued" if cmd["goal"] == "scan" else ""})
        if not self.ready:
            self.emit("hello", {"modVersion": "0.1", "build": "42.21.0", "user": "admin", "rate": 5, "mode": self.mode})
            self.ready = True
        g = self.goal
        if g is not None and g["state"] == "running":
            g["ticks"] += 1
            if g["ticks"] >= self.GOAL_TICKS:
                self.end(g)
        if self.lua_err_from is not None and self.s() >= self.lua_err_from and (
                self.last_err_s is None or self.s() - self.last_err_s >= 1.0):
            self.last_err_s = self.s()
            self.emit("event", {"event": "lua_error", "msg": "boom"})
        if self.tick % self.FRAME_EVERY == 0:
            if self.leave:
                self.leave = False
                self.emit("event", {"event": "zombie_leave", "id": 7})
            self.goal_event(g)
            st = ({"seq": 0, "name": "idle", "state": "idle", "detail": ""} if g is None else
                  {"seq": g["seq"], "name": g["name"], "state": g["state"], "detail": g["detail"]})
            f = {"x": self.x, "y": self.y, "z": 0, "health": self.health, "hunger": self.hunger,
                 "thirst": self.thirst, "fatigue": self.fatigue, "gameMin": 420 + self.tick // 4, "worldAge": 31.5,
                 "zombies": self.zombies(), "nZombies": len(self.zombies()), "goal": st,
                 "cost": {"pollMs": 0.1, "actMs": 0.1, "scanStepMs": 0.0, "senseMs": 0.2, "linkMs": 0.1 * (
                     1 + self.tick % 3), "dropped": 0, "scanEmitMs": 0}}
            if self.weapon:
                f["weapon"] = dict(self.weapon)
            self.emit("frame", f)
        self.flush()

    def sleep(self, dt):
        for _ in range(max(1, round(dt * self.TPS))):
            self.step()


class Server:
    """The server's bus replies in their real shapes. `stats_bad_from` / `players_bad_from` (mod seconds): the read
    answers a failure from then; `gone_from`: the players list lacks admin from then (an empty {})."""

    def __init__(self, mod, stats_bad_from=None, players_bad_from=None, gone_from=None, bus_dead_from=None):
        self.mod = mod
        self.stats_bad_from, self.players_bad_from, self.gone_from, self.bus_dead_from = (
            stats_bad_from, players_bad_from, gone_from, bus_dead_from)
        self.stats_calls, self.players_calls = [], []

    def after(self, t):
        return t is not None and self.mod.s() >= t

    def stats(self, xs, user):
        self.stats_calls.append(self.mod.s())
        if self.after(self.bus_dead_from):
            raise X.BusDead("server bus dead after stats")
        if self.after(self.stats_bad_from):
            return {"ack": "no online player admin", "wallMs": self.mod.clock.t * 1000}
        m = self.mod
        return {"ack": {"side": "server", "user": user, "worldAge": 31.5, "mult": 1.0, "wall": 1,
                        "stats": {"Hunger": m.hunger + 0.01, "Thirst": m.thirst, "Fatigue": m.fatigue},
                        "missing": {}}, "wallMs": m.clock.t * 1000}

    def players(self, xs):
        self.players_calls.append(self.mod.s())
        if self.after(self.players_bad_from):
            return "timeout"
        if self.after(self.gone_from):
            return {}
        return ["admin"]


def run_survive(tmp_path, limits=None, budget_s=1e9, free=lambda: 30.0, parked_at=None, server=None, **flags):
    clock = Clock()
    sd = str(tmp_path / "clients" / "admin" / "Lua" / "pzagent" / "admin")
    mod = SurviveMod(sd, clock, **flags)
    srv = Server(mod, **(server or {}))
    out = D.new_out()
    spawns, equips = [], []

    def spawn(ft, n, tag):
        spawns.append((ft, n, tag))
        return {"type": ft, "n": n, "confirmed": True}

    def equip(xs, ft):
        equips.append(ft)
        mod.weapon = dict(BAT)
        return {"ok": True, "fullType": ft, "queued": True}

    seen = {}
    client = types.SimpleNamespace(seen=seen)
    xs = X.Xs(out, node=lambda side: side, clock=clock.now, sleep=mod.sleep, budget_s=budget_s, user="admin",
              clients={"admin": client})
    xs.path = str(tmp_path / D.ARTIFACT)
    persists = []
    real_persist = xs.persist

    def persist():
        persists.append((mod.s(), (out.get("loop") or {}).get("wallS")))
        if parked_at is not None and mod.s() >= parked_at:
            seen["lua_error"] = 1
        real_persist()
    xs.persist = persist
    sv = D.Survive(xs, Link(sd, clock=clock.now), clock=clock.now, sleep=mod.sleep, bus_stats=srv.stats,
                   players=srv.players, free=free, spawn=spawn, equip=equip, limits=limits)
    sv.run()
    out["client_lua_errors"] = 0
    return types.SimpleNamespace(out=out, mod=mod, srv=srv, sv=sv, spawns=spawns, equips=equips, persists=persists,
                                 xs=xs)


def decisions(tmp_path):
    with open(tmp_path / D.DECISION_LOG, encoding="utf-8") as f:
        return [json.loads(ln) for ln in f]


def test_the_planner_loop_sends_the_policys_goals_and_stops_at_the_day_cap(tmp_path):
    r = run_survive(tmp_path, limits={"DAY_CAP_S": 40})
    out = r.out
    assert out["phase_errors"] == {}, out["phase_errors"]
    assert out["stop"]["reason"] == "day_cap" and out["stop"]["wallS"] == pytest.approx(40, abs=0.2)
    assert out["mode"] == "append" and r.spawns == [("Base.BaseballBat", 1, "spawn_BaseballBat")]
    assert r.equips == ["Base.BaseballBat"]
    kit = out["readings"]["start_kit"]
    assert kit["armed"] is True and kit["spawn"]["confirmed"] is True and kit["equip"]["queued"] is True
    loop = out["loop"]
    log = decisions(tmp_path)
    assert loop["ticks"] == len(log) and loop["ticks"] == pytest.approx(40 * D.PLANNER_HZ, abs=2)
    sent = [(d["goal"], d["args"]) for d in log if d["sent"]]
    assert loop["decisions"] == len(sent) > 0
    assert [(c["goal"], c["args"]) for c in r.mod.cmds] == sent                     # every goal came from the policy
    assert sent[0] == ("scan", "10")                                               # explore scans first
    assert loop["last_decisions"] == log[-10:]
    assert loop["cost"]["n"] > 0 and 0.4 < loop["cost"]["p50"] <= loop["cost"]["p99"] <= loop["cost"]["max"]
    assert "goto" in loop["goal_outcomes"] and "scan" not in loop["goal_outcomes"]
    assert loop["goal_outcomes"]["goto"]["done"]
    assert D.DECISION_LOG in r.xs.copied
    assert out["lua_errors"] == 0 and out["gaps"] == [] and out["bad"] == 0
    persisted = json.loads((tmp_path / D.ARTIFACT).read_text(encoding="utf-8"))
    assert persisted["stop"]["reason"] == "day_cap" and persisted["loop"]["ticks"] == loop["ticks"]


def test_the_server_is_polled_and_merged_on_schedule_with_one_needs_row_each(tmp_path):
    r = run_survive(tmp_path, limits={"DAY_CAP_S": 130})
    calls = r.srv.stats_calls
    loop0 = calls[0]
    assert [round(c - loop0) for c in calls] == [0, 60, 120] and len(r.srv.players_calls) == 3
    assert r.sv.world.server["stats"]["Hunger"] == pytest.approx(0.11)
    needs = r.out["loop"]["needs"]
    assert len(needs) == 3 and all(len(n) == 6 for n in needs)
    assert needs[1][1:5] == [0.1, 0.1, 0.1, 100.0] and needs[1][5] == pytest.approx(0.11)
    assert r.out["loop"]["server_polls"] == 3 and r.out["loop"]["server_fails"] == 0


def test_persist_runs_every_persist_s_of_the_loop(tmp_path):
    r = run_survive(tmp_path, limits={"DAY_CAP_S": 100})
    walls = [w for _, w in r.persists if w is not None]
    periodic = walls[:3]
    assert [round(w) for w in periodic] == [30, 60, 90]
    assert walls[-1] == pytest.approx(100, abs=0.2)                                  # the stop's own save


def test_a_death_frame_stops_the_loop_with_the_last_ten_decisions(tmp_path):
    r = run_survive(tmp_path, die_at=12.0)
    st, death = r.out["stop"], r.out["loop"]["death"]
    assert st["reason"] == "death" and "health 0.0" in st["detail"]
    assert death["via"] == "frame" and death["frame"]["health"] == 0.0
    assert death["last_decisions"] == decisions(tmp_path)[-10:] and len(death["last_decisions"]) == 10
    assert st["wallS"] < 12.0


def test_a_players_reply_without_the_user_is_a_death(tmp_path):
    r = run_survive(tmp_path, limits={"SERVER_POLL_S": 5}, server={"gone_from": 7.0})
    st = r.out["stop"]
    assert st["reason"] == "death" and "players reply without admin" in st["detail"]
    assert r.out["loop"]["death"]["via"] == "players" and len(r.srv.players_calls) == 3


def test_no_good_server_reply_for_bus_dead_s_stops_the_loop(tmp_path):
    r = run_survive(tmp_path, server={"stats_bad_from": 0.0, "players_bad_from": 0.0})
    st = r.out["stop"]
    assert st["reason"] == "bus_dead" and "no good server reply" in st["detail"]
    assert st["wallS"] == pytest.approx(60, abs=0.2) and r.out["loop"]["server_fails"] == 2
    # one good reader keeps the bus alive
    r = run_survive(tmp_path / "b", limits={"DAY_CAP_S": 130}, server={"stats_bad_from": 0.0})
    assert r.out["stop"]["reason"] == "day_cap" and r.out["loop"]["needs"][-1][5] is None


def test_xlib_busdead_stops_the_loop_as_bus_dead(tmp_path):
    r = run_survive(tmp_path, limits={"SERVER_POLL_S": 5}, server={"bus_dead_from": 8.0})
    assert r.out["stop"]["reason"] == "bus_dead" and "BusDead" in r.out["stop"]["detail"]


def test_a_silent_link_stops_the_loop_as_bus_dead(tmp_path):
    r = run_survive(tmp_path, silent_from=5.0)
    st = r.out["stop"]
    assert st["reason"] == "bus_dead" and "no link line" in st["detail"]
    assert 60 <= st["wallS"] < 66


def test_a_parked_client_stops_the_loop_as_bus_dead(tmp_path):
    r = run_survive(tmp_path, limits={"PERSIST_S": 5}, parked_at=8.0)
    st = r.out["stop"]
    assert st["reason"] == "bus_dead" and "parked" in st["detail"]


def test_a_lua_error_storm_stops_the_loop(tmp_path):
    r = run_survive(tmp_path, lua_err_from=3.0)
    st = r.out["stop"]
    assert st["reason"] == "lua_error_storm" and "11 lua_error events" in st["detail"]
    assert r.out["lua_errors"] == 11 and sum(r.out["loop"]["lua_errors_per_min"].values()) == 11
    assert len(r.out["lua_error_lines"]) == 11


def test_ten_lua_errors_in_a_minute_are_not_a_storm(tmp_path):
    # one a second, read on a 0.1 s poll: at most ten fall inside any 8.5 s window
    r = run_survive(tmp_path, limits={"DAY_CAP_S": 30, "STORM_WINDOW_S": 8.5}, lua_err_from=2.0)
    assert r.out["stop"]["reason"] == "day_cap" and r.out["lua_errors"] >= 20


def test_low_memory_on_the_periodic_read_stops_the_loop(tmp_path):
    reads = iter([30.0, 20.0, 8.5])
    r = run_survive(tmp_path, limits={"MEM_POLL_S": 10}, free=lambda: next(reads))
    st = r.out["stop"]
    assert st["reason"] == "memory" and "8.5" in st["detail"] and st["wallS"] == pytest.approx(20, abs=0.2)
    assert [m["free_gb"] for m in r.out["loop"]["memory"]] == [30.0, 20.0, 8.5]
    r = run_survive(tmp_path / "b", limits={"MEM_POLL_S": 10}, free=lambda: None)          # no reading counts as low
    assert r.out["stop"]["reason"] == "memory"


def test_the_wall_budget_stops_the_loop(tmp_path):
    r = run_survive(tmp_path, budget_s=25.0)
    st = r.out["stop"]
    assert st["reason"] == "budget" and "past the budget" in st["detail"]


def test_a_fight_is_sent_and_its_end_recorded(tmp_path):
    r = run_survive(tmp_path, limits={"DAY_CAP_S": 20}, zombie_at=6.0)
    fights = r.out["loop"]["fights"]
    assert len(fights) == 1
    f = fights[0]
    assert f["threats"] == 1 and f["health"] == 100.0 and f["startS"] > 5.0
    assert f["end"]["state"] == "done" and f["end"]["detail"] == "clear" and f["end"]["wallMs"] > f["startWallMs"]
    assert f["end"]["from"] == "frame"                     # the goal_done event came first and carried no detail
    # a goal that ends between frames and is superseded before the next frame tick is reported by the Lua's
    # goalEvent(old) alone: done with no detail, kept as such
    sv = r.sv
    sv.goal_end[99] = {"state": "done", "detail": "", "seq": 1, "wallMs": 1, "from": "event"}
    sv.fights.append({"seq": 99, "end": None})
    sv.close_fights()
    assert sv.fights[-1]["end"] == {"state": "done", "detail": "", "wallMs": 1, "from": "event"}
    assert r.out["loop"]["goal_outcomes"]["fight"] == {"done": {"clear": 1}}


def test_a_hello_in_another_mode_fails_the_phase_and_the_loop_never_runs(tmp_path):
    r = run_survive(tmp_path, mode="chunk")
    assert "not append" in r.out["phase_errors"]["hello"]["error"]
    assert r.out["stop"]["reason"] == "error" and r.out["loop"].get("ticks") is None


def test_the_decision_log_is_copied_with_the_artifact(tmp_path):
    r = run_survive(tmp_path, limits={"DAY_CAP_S": 5})
    assert r.xs.copied == [D.DECISION_LOG]
    dest = r.xs.copy_artifacts(str(tmp_path / "repo"), "c_survive-x", str(tmp_path), D.ARTIFACT)
    assert sorted(os.listdir(dest)) == sorted([D.ARTIFACT, D.DECISION_LOG])
    assert open(os.path.join(dest, D.DECISION_LOG), encoding="utf-8").read() == (
        tmp_path / D.DECISION_LOG).read_text(encoding="utf-8")


# ================================================================ grade_c and c_grade
def synthetic():
    dec = [{"wall": i, "gameMin": 600 + i, "branch": "threat", "goal": "flee", "args": "92 100", "sent": i == 9,
            "inputs": {"health": 10.0 - i}} for i in range(10)]
    return {"session_key": "c_survive", "run_id": "c_survive-x", "finished": True, "lua_errors": 2,
            "client_lua_errors": 0, "readings": {"start_kit": {"armed": True}},
            "stop": {"reason": "death", "detail": "frame seq 9 health 0.0", "wallS": 1800.0, "gameMin": 610},
            "loop": {"wallS": 1800.0, "ticks": 3600, "decisions": 450, "last_decisions": dec,
                     "needs": [[420, 0.1, 0.1, 0.1, 100.0, 0.12], [480, 0.3, 0.4, 0.2, 80.0, 0.25],
                               [540, 0.2, 0.6, 0.3, 40.0, None]],
                     "fights": [{"seq": 4, "end": {"state": "done", "detail": "clear"}},
                                {"seq": 9, "end": {"state": "failed", "detail": "low health"}},
                                {"seq": 12, "end": None}],
                     "lua_errors_per_min": {"3": 1, "17": 1},
                     "cost": {"n": 9000, "p50": 0.42, "p99": 1.7, "max": 4.0},
                     "goal_outcomes": {"goto": {"done": {"d=0.1": 3, "d=0.4": 2}, "failed": {"no path": 1}},
                                       "fight": {"done": {"clear": 1}, "failed": {"low health": 1}, "open": {"": 1}}},
                     "server_polls": 30, "server_fails": 1,
                     "death": {"via": "frame", "detail": "frame seq 9 health 0.0", "wallS": 1800.0, "gameMin": 610,
                               "last_decisions": dec}}}


def test_grade_c_reads_a_synthetic_artifact():
    g = GC.grade_c(synthetic())
    assert g["stop"]["reason"] == "death" and g["survived"] is False and g["survival_s"] == 1800.0
    assert g["decisions_per_min"] == pytest.approx(15.0) and g["ticks_per_min"] == pytest.approx(120.0)
    assert g["fights"] == {"count": 3, "outcomes": {"done:clear": 1, "failed:low health": 1, "open": 1}}
    assert len(g["deaths"]) == 1 and g["deaths"][0]["via"] == "frame" and len(g["deaths"][0]["last_decisions"]) == 10
    assert (g["cost_p50"], g["cost_p99"], g["cost_n"]) == (0.42, 1.7, 9000)
    assert g["lua_errors"] == 2 and g["lua_errors_max_per_min"] == 1
    assert g["goal_outcomes"]["goto"] == {"done": {"d=": 5}, "failed": {"no path": 1}}
    ns = g["needs_summary"]
    assert ns["rows"] == 3 and ns["paired_rows"] == 2 and ns["hunger_client_server_max_diff"] == pytest.approx(0.05)
    assert ns["peak"] == {"hunger": 0.3, "thirst": 0.6, "fatigue": 0.3} and ns["min_health"] == 40.0
    lines = g["report_lines"]
    assert lines[0].startswith("died after 1800 s") and any(l.startswith("death via frame") for l in lines)
    assert any("goal goto: done 5 (d= x5); failed 1 (no path x1)" == l for l in lines)
    assert all("\n" not in l for l in lines)


def test_grade_c_on_a_survived_and_an_empty_artifact():
    o = synthetic()
    o["stop"] = {"reason": "day_cap", "detail": "x", "wallS": 5400.0}
    del o["loop"]["death"]
    g = GC.grade_c(o)
    assert g["survived"] is True and g["deaths"] == [] and g["survival_s"] == 5400.0
    e = GC.grade_c({})
    assert e["stop"] is None and e["survived"] is None and e["survival_s"] is None and e["deaths"] == []
    assert e["decisions_per_min"] is None and e["fights"]["count"] == 0 and e["report_lines"][0].startswith("no loop")
    assert GC.grade_c("not a dict")["survival_s"] is None


def test_grade_c_on_a_real_offline_session(tmp_path):
    r = run_survive(tmp_path, limits={"DAY_CAP_S": 20}, zombie_at=6.0)
    g = GC.grade_c(json.loads((tmp_path / D.ARTIFACT).read_text(encoding="utf-8")))
    assert g["survived"] is True and g["stop"]["reason"] == "day_cap" and g["fights"]["count"] == 1
    assert g["start_kit_armed"] is True and g["cost_p99"] is not None and g["decisions"] == r.out["loop"]["decisions"]


def test_c_grade_prints_strict_json_and_exits_zero(tmp_path, capsys):
    p = tmp_path / "c.json"
    o = synthetic()
    o["loop"]["cost"]["max"] = math.inf
    p.write_text(json.dumps(o))
    assert CG.main([str(p)]) == 0
    g = json.loads(capsys.readouterr().out)
    assert g["stop"]["reason"] == "death" and g["cost_max"] is None
    p.write_text(json.dumps({}))
    assert CG.main([str(p)]) == 0                                                  # no gate: an empty session is 0
    assert CG.main([]) == 2 and CG.main([str(tmp_path / "none.json")]) == 2
