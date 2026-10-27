"""drivers/d_survive.py, drivers/d_grade.py and base/gates.grade_d (Plan 22 Task 17, the survival acceptance),
offline: the driver is never invoked.

The loop runs against DayMod, a FakeMod (every line through pza1.encode) ticking at 10 Hz on a fake clock shared with
the driver: it answers cmd.txt (equip wields the bat; attack kills its zombie with a zombie_dead event; every other
type is accepted and done), emits the kit's item_added after the RCON additem, and on its knobs drains body.health
(the server recording each drop as a HEAVYLOAD damage record), lists a zombie, writes lua_error events or falls
silent. FakeBus answers the server's bus with the @reply shapes of PZTestKit_Server.lua: stats.all {side, user,
worldAge, mult, wall, stats {<registry id>: value}, missing {}} (a failed read a string), players [<username>, ...]
({} when nobody is online, L16), damage.watch {ok, side, hooked, user, counts {tag: n}, n, last [{i, tag, amount,
wall}], dropped} (Task 7's block; `{}` for an empty Lua table), item.get and ping. The stop-condition falsifiers are
test_c_survive.py's, ported to the new shapes."""
import json
import math
import os
import re
import types

import pytest

from agent.base import gates as GT
from agent.base.transport.files import FileTransport
from agent.drivers import d_grade as DG
from agent.drivers import d_survive as D
from .fakemod import DEFAULT_FRAME, FakeMod

REPO = D.REPO
X = D.X
C_SURVIVE = os.path.join(os.path.dirname(D.__file__), "c_survive.py")
X5_COMBAT = os.path.join(os.path.dirname(D.__file__), "x5_combat.py")


def _source_constant(path, name):
    """A module-level constant's value read off a frozen driver's source text (never imported) with its line."""
    with open(path, encoding="utf-8") as fh:
        for n, line in enumerate(fh, 1):
            m = re.match(r"^%s = (.+?)\s*(#.*)?$" % name, line)
            if m:
                return eval(m.group(1)), n                       # noqa: S307 - a literal off a tracked file
    raise KeyError(name)


# ================================================================ static: refusal, constants, imports, preboot
def test_the_driver_refuses_arguments_before_main():
    with open(D.__file__, encoding="utf-8") as fh:
        src = fh.read()
    i_ref, i_main = src.index("refusal = parse_argv(sys.argv[1:], __file__)"), src.rindex("    main()")
    assert src.index('if __name__ == "__main__":') < i_ref < i_main
    assert "sys.exit(refusal)" in src[i_ref:i_main]
    assert "d_survive.py takes no arguments" in D.parse_argv(["x"], D.__file__)
    assert D.parse_argv(["--help"], D.__file__) and D.parse_argv([], D.__file__) is None


def test_the_constants_name_the_drivers_own_file_key_artifact_and_profile():
    assert os.path.basename(D.__file__) == D.DRIVER == D.KEY + ".py" == "d_survive.py"
    assert (D.KEY, D.PROFILE, D.ARTIFACT) == ("d_survive", "testing/profiles/agent.toml", "d_survive.json")
    assert os.path.isfile(os.path.join(REPO, D.PROFILE))
    brief = {"BUDGET_S": 5700.0, "DAY_CAP_S": 5400, "PLANNER_HZ": 2, "SERVER_POLL_S": 60, "DAMAGE_POLL_S": 30,
             "PERSIST_S": 30, "MEM_POLL_S": 300, "LIVE_MIN_FREE_GB": 0.5, "STOP_HEALTH": 0.0}
    for k, v in brief.items():
        assert getattr(D, k) == v and D.CONSTANTS[k] == v, k
    assert D.STOPS == ("death", "bus_dead", "lua_error_storm", "memory", "day_cap", "budget", "error")
    assert D.PHASES == ("hello", "kit", "damage_hook", "survive") and D.USER == "admin"
    assert (D.LAST_FRAMES, D.DEATH_WINDOW_S, D.LAST_DECISIONS) == (300, 300, 10) and GT.DEATH_TOL == 0.10
    assert GT.DANGER_R == 6.0


@pytest.mark.parametrize("name,path", [
    ("BUDGET_S", C_SURVIVE), ("MIN_FREE_GB", C_SURVIVE), ("PLANNER_HZ", C_SURVIVE), ("SERVER_POLL_S", C_SURVIVE),
    ("PERSIST_S", C_SURVIVE), ("MEM_POLL_S", C_SURVIVE), ("LIVE_MIN_FREE_GB", C_SURVIVE), ("MEM_LOW_READS", C_SURVIVE),
    ("DAY_CAP_S", C_SURVIVE), ("BUS_DEAD_S", C_SURVIVE), ("BUS_DEAD_POLLS", C_SURVIVE), ("STORM_N", C_SURVIVE),
    ("STORM_WINDOW_S", C_SURVIVE), ("HELLO_TIMEOUT_S", C_SURVIVE), ("FRAME_TIMEOUT_S", C_SURVIVE),
    ("KIT", C_SURVIVE), ("POLL_S", C_SURVIVE), ("DECISION_LOG", C_SURVIVE), ("LAST_DECISIONS", C_SURVIVE),
    ("KIT_TIMEOUT_S", X5_COMBAT), ("EQUIP_TIMEOUT_S", X5_COMBAT), ("ACT_TIMEOUT_S", X5_COMBAT),
    ("SERVER_TIMEOUT_S", X5_COMBAT), ("PARK_RX", X5_COMBAT)])
def test_each_copied_constant_equals_its_frozen_source_and_names_its_line(name, path):
    value, line = _source_constant(path, name)
    assert getattr(D, name) == value, name
    src = open(D.__file__, encoding="utf-8").read()
    if name != "PARK_RX":
        decl = next(l for l in src.splitlines() if l.startswith(name + " = "))
        assert "%s L%d" % (os.path.basename(path), line) in decl, (name, decl)


def test_nothing_is_imported_from_a_frozen_driver():
    src = open(D.__file__, encoding="utf-8").read()
    imports = [l.split("#")[0].strip() for l in src.splitlines() if l.strip().startswith(("import ", "from "))]
    drivers = [l for l in imports if "drivers" in l or l.split()[1].split(".")[0] in (
        "a_pipe", "a_pipe_2", "a_pipe_3", "a_pipe_4", "b_actions", "b_actions_2", "c_survive", "c_survive_2",
        "c_survive_dense", "c_grade", "p22_probe", "x4_link", "x5_combat")]
    assert drivers == [], drivers
    assert "import _dlib as DL" in imports and "import xlib as X" in imports
    assert "from agent.base.planner.survive import Survive" in imports
    for frozen in ("agent.link", "agent.grades", "agent.grade_c", "agent.world", "agent.policy", "link_for"):
        assert frozen not in src, frozen
    assert "Day(xs, FileTransport(DL.state_dir(clients[USER]))).run()" in src
    assert "make_client=clearing_make_client(session.make_client)" in src
    i_x, i_g, i_b = src.index("xs = X.Xs("), src.index("    memory_gate(xs)"), src.index("DL.boot(")
    assert i_x < i_g < i_b
    assert 'out["grade_d"] = GT.grade_d(out)' in src and "xs.copy_artifacts(REPO, run_id, run_dir, ARTIFACT)" in src
    gsrc = open(DG.__file__, encoding="utf-8").read()
    assert "c_grade" not in [l.split()[1] for l in gsrc.splitlines() if l.startswith(("import ", "from "))]


def test_preboot_on_the_real_profile(agent_fixture, monkeypatch):
    monkeypatch.setattr(D.DL.C, "doctor", lambda: (True, "ok"))
    monkeypatch.setattr(D.DL.harness, "lint_paths", lambda srcs: [])
    monkeypatch.setattr(D.DL.C, "git_dirty", lambda rel: (False, ""))
    real = D.DL.C.git_say
    tracked = {"v": ""}
    monkeypatch.setattr(D.DL.C, "git_say", lambda *a: tracked["v"] if a[0] == "ls-files" else real(*a))
    pre, ok = D.preboot(D.__file__)
    assert ok, pre
    assert pre["profile"] == "agent" and pre["driver_checks"]["driver_file"] is True
    tracked["v"] = "testing/artifacts/d_survive-20261027-120000/d_survive.json"
    assert D.preboot(D.__file__)[1] is False
    tracked["v"] = ""
    assert D.preboot(os.path.join(os.path.dirname(D.__file__), "x5_combat.py"))[1] is False


def test_driver_checks_refuse_a_dirty_lua_base_or_driver():
    say = lambda *a: ""                                                     # noqa: E731
    c, ok = D.driver_checks(D.__file__, git_say=say, git_dirty=lambda rel: (False, ""))
    assert ok and c["no_committed_artifact"] is True and c["profile_exists"] is True
    for dirty in ("testing/PZAgent", "testing/agent/base", "testing/agent/drivers/d_survive.py"):
        c, ok = D.driver_checks(D.__file__, git_say=say, git_dirty=lambda rel, d=dirty: (rel == d, ""))
        assert ok is False, dirty
    c, ok = D.driver_checks(D.__file__, git_say=say, git_dirty=lambda rel: (None, "no git"))
    assert ok is False                                                      # unknown is not clean
    c, ok = D.driver_checks(D.__file__, git_say=lambda *a: "testing/artifacts/d_survive-1/d_survive.json",
                            git_dirty=lambda rel: (False, ""))
    assert ok is False and c["no_committed_artifact"] is False


# ================================================================ DayMod and FakeBus: the fake session
class Clock:
    def __init__(self):
        self.t = 1_790_000_000.0

    def now(self):
        return self.t


KIT_ID = 5001
ZID = 77


class DayMod(FakeMod):
    """The fake Lua on the shared clock: sleep(dt) runs its ticks (one frame a tick at 10 Hz). Knobs, in seconds of
    its own clock since it was made: `die_from` (body.health falls by `drain` a tick from then, to `floor` (0); each
    drop is a server HEAVYLOAD record of `amount` (default `drain`) when `server_damage`), `client_damage` (one client
    damage event at the drain's start), `zombie_at` (zombie ZID at 1.5 tiles from then until an attack kills it),
    `lua_err_from` / `lua_err_every`, `silent_from` (no line written from then), `hello_mode`, `no_hello` (no hello
    line), `zombie_far_s` (the zombie stands at 8 tiles for that long before it closes to `zombie_dist`) and
    `bite_at` (body.bitten 0 -> 1 and a hurt part from then: a wound the server never hears)."""

    def __init__(self, d, clock, die_from=None, drain=5.0, amount=None, floor=0.0, server_damage=True,
                 client_damage=False, zombie_at=None, lua_err_from=None, lua_err_every=1.0, silent_from=None,
                 hello_mode="append", no_hello=False, zombie_far_s=0.0, zombie_dist=1.5, bite_at=None):
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
        self.server_records = []
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
        self.pending.append({"itemId": KIT_ID, "fullType": D.KIT, "weight": 1.5})

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
        self.act(aid, "accepted", t)
        if t == "equip":
            self.weapon = {"type": D.KIT, "cond": 1.0, "reach": 1.125, "ammo": None}
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
        wall = int(round(self.clk.t * 1000))
        if self.die_from is not None and self.s() >= self.die_from - 1e-9 and self.health > self.floor:
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
        dist = 8.0 if self._zombie_live() and self.s() < self.zombie_at + self.zombie_far_s else self.zombie_dist
        zs = [{"id": ZID, "x": 100.0 + dist, "y": 200.0, "dist": dist, "hasTarget": True, "crawler": False,
               "health": 1.0}] if self._zombie_live() else []
        body = dict(DEFAULT_FRAME["body"], health=self.health)
        if self.bite_at is not None and self.s() >= self.bite_at - 1e-9:
            body.update(bitten=1, parts=[{"i": 5, "h": 80.0}])
        self.frame(gameMin=480.0 + self.s() * 16.0 / 60.0, body=body, weapon=self.weapon, zombies=zs)


class FakeServer:
    def __init__(self, mod):
        self.mod, self.errors = mod, []

    def rcon(self, cmd):
        self.mod.additem()
        return True, "Item %s Added in admin's inventory." % D.KIT


class FakeBus:
    """The server's bus in its real reply shapes. Knobs (the mod's seconds): `stats_bad_from` / `players_bad_from`
    (a failure reply from then, until `bad_until`), `gone_from` (players {} from then), `players_error_from` (players
    {"error": "TimeoutError: no reply"} from then: a stall the ping answers), `bus_dead_from` (stats.all and
    item.get stall and the ping never answers: xlib's BusDead), `stall_at` / `stall_s` (one stats.all call blocks
    stall_s while the client keeps writing)."""

    def __init__(self, mod, stats_bad_from=None, players_bad_from=None, bad_until=None, gone_from=None,
                 players_error_from=None, bus_dead_from=None, stall_at=None, stall_s=0.0, bus_s=0.05):
        self.mod = mod
        self.stats_bad_from, self.players_bad_from, self.bad_until = stats_bad_from, players_bad_from, bad_until
        self.gone_from, self.players_error_from, self.bus_dead_from = gone_from, players_error_from, bus_dead_from
        self.stall_at, self.stall_s, self.bus_s = stall_at, stall_s, bus_s
        self.asked, self.stats_calls, self.players_calls, self.damage_calls = [], [], [], []
        self.hooked_ms = None        # the listener records from its install on (TK.DW.hook), never before

    def after(self, t):
        return t is not None and self.mod.s() >= t

    def bad(self, t):
        return self.after(t) and not self.after(self.bad_until)

    def ask(self, node, cmd, args, timeout=30):
        self.asked.append((node, cmd, args, timeout))
        self.mod.sleep(self.bus_s)
        m = self.mod
        dead = self.after(self.bus_dead_from)
        if cmd == "ping":
            return {"error": "TimeoutError: no reply"} if dead else "pong"
        if dead and cmd in ("stats.all", "item.get", "players", "damage.watch"):
            return {"error": "TimeoutError: no reply"}
        if cmd == "item.get":
            if not m.has_kit:
                return "no item %s in admin's inventory" % D.KIT
            return {"fullType": D.KIT, "id": KIT_ID, "uses": 1, "age": 0, "weight": 1.5}
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


def run_day(tmp_path, monkeypatch, limits=None, budget_s=1e9, free=lambda: 30.0, parked_at=None, bus=None,
            setup=None, **flags):
    clock = Clock()
    sd = str(tmp_path / "clients" / "admin" / "Lua" / "pzagent" / "admin")
    mod = DayMod(sd, clock, **flags)
    fb = FakeBus(mod, **(bus or {}))
    monkeypatch.setattr(D.DL, "time", types.SimpleNamespace(time=clock.now))   # _dlib.bus_stats's wallMs clock
    out = D.new_out()
    seen = {}
    xs = X.Xs(out, node=lambda side: side, server=FakeServer(mod), ask=fb.ask, clock=clock.now, sleep=mod.sleep,
              budget_s=budget_s, user="admin", clients={"admin": types.SimpleNamespace(seen=seen)})
    xs.path = str(tmp_path / D.ARTIFACT)
    persists = []
    real_persist = xs.persist

    def persist():
        persists.append((mod.s(), (out.get("loop") or {}).get("wallS")))
        if parked_at is not None and mod.s() >= parked_at:
            seen["lua_error"] = 1
        real_persist()
    xs.persist = persist
    day = D.Day(xs, FileTransport(sd, clock=clock.now), clock=clock.now, sleep=mod.sleep, free=free, limits=limits)
    if setup is not None:
        setup(day)
    day.run()
    out["frames"]["parks"] = 0                                             # main's read_logs: no console here
    out["finished"] = True
    return types.SimpleNamespace(out=out, mod=mod, bus=fb, day=day, persists=persists, xs=xs, clock=clock)


def decisions(tmp_path):
    with open(tmp_path / D.DECISION_LOG, encoding="utf-8") as f:
        return [json.loads(ln) for ln in f]


# ================================================================ the loop: phases, polls, rows
def test_a_clean_day_runs_every_phase_and_stops_at_the_day_cap(tmp_path, monkeypatch):
    r = run_day(tmp_path, monkeypatch, limits={"DAY_CAP_S": 40})
    out = r.out
    assert out["phase_errors"] == {}, out["phase_errors"]
    assert out["stop"]["reason"] == "day_cap" and out["stop"]["wallS"] == pytest.approx(40, abs=0.2)
    h = out["readings"]["hello"]
    assert h["ok"] and h["proto"] == "PZA/1" and h["mode"] == "append" and h["first_frame"]["seq"] >= 1
    kit = out["readings"]["kit"]
    assert kit["spawn"]["confirmed"] is True and kit["item"] == {"itemId": KIT_ID, "source": "item_added",
                                                                 "seq": kit["item"]["seq"],
                                                                 "wallMs": kit["item"]["wallMs"]}
    assert kit["equip"]["state"] == "done" and kit["weapon_frame"]["type"] == D.KIT
    assert kit["armed"] is True and kit["ok"] is True
    dh = out["readings"]["damage_hook"]
    assert dh["ok"] is True and dh["hooked"] is True and dh["n"] == 0 and dh["last_i"] == 0
    assert list(out["readings"]) == ["hello", "kit", "damage_hook"] and out["loop"]["started"] is True
    loop = out["loop"]
    log = decisions(tmp_path)
    assert loop["ticks"] == len(log) and loop["ticks"] == pytest.approx(40 * D.PLANNER_HZ, abs=2)
    assert loop["last_decisions"] == log[-10:]
    sent = [d["action"] for d in log if d["sent"]]
    assert loop["decisions"] == len(sent) == len(loop["actions"]) > 0
    assert sent[0] == {"type": "scan", "args": {"r": 10}}                  # explore scans first
    planner_cmds = [c for c in r.mod.cmds if c["type"] != "equip"]
    assert [{"type": c["type"], "args": c["args"]} for c in planner_cmds] == sent
    assert all(set(a) == {"aid", "type", "args", "state", "reason", "sentS", "endedS"} for a in loop["actions"])
    assert loop["actions"][0]["state"] == "done" and loop["actions"][0]["endedS"] >= loop["actions"][0]["sentS"]
    assert loop["cost"]["n"] > 0 and loop["cost"]["p50"] == pytest.approx(0.2) and loop["cost"]["over5"] == 0
    assert loop["first_game_min"] is not None and loop["game_min"] > loop["first_game_min"]
    assert D.DECISION_LOG in r.xs.copied
    fr = out["frames"]
    assert fr["lua_errors"] == 0 and fr["gaps"] == 0 and fr["bad"] == 0 and fr["n"] > 300
    persisted = json.loads((tmp_path / D.ARTIFACT).read_text(encoding="utf-8"))
    assert persisted["stop"]["reason"] == "day_cap" and persisted["loop"]["ticks"] == loop["ticks"]
    json.dumps(out, allow_nan=False)
    g = GT.grade_d(persisted)
    assert g["survived"] is True and g["death_explained"] is None and g["start_kit_armed"] is True
    assert g["actions"]["by_type"]["scan"] == {"done": 1} and g["game_minutes"] > 0


def test_the_server_is_polled_on_schedule_with_one_paired_needs_row_each(tmp_path, monkeypatch):
    r = run_day(tmp_path, monkeypatch, limits={"DAY_CAP_S": 130})
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


def test_damage_watch_is_polled_since_the_last_index_and_merged_tagged_server(tmp_path, monkeypatch):
    r = run_day(tmp_path, monkeypatch, limits={"DAY_CAP_S": 100}, die_from=45.0, drain=0.05)
    hook, calls = r.bus.damage_calls[0], [c[:2] for c in r.bus.damage_calls[1:]]
    assert hook[2] == "admin"                                              # the listener installed at the kit's end
    t0 = calls[0][0]
    assert [round(t - t0) for t, _ in calls] == [0, 30, 60, 90] and r.out["stop"]["reason"] == "day_cap"

    def n_at(s):                                                           # the records the server held at mod s
        return sum(1 for d in r.mod.server_records if d["wall"] <= round((r.mod.t0 + s) * 1000))
    assert [s for _, s in calls] == [0, 0, n_at(calls[1][0]), n_at(calls[2][0])]
    assert calls[2][1] == 0 and calls[3][1] > 100                          # the drain began between the 2nd and 3rd
    assert all(a[3] == D.SERVER_TIMEOUT_S for a in r.bus.asked if a[1] == "damage.watch")
    w, last = r.day.world, n_at(calls[3][0])                              # the records as of the last poll
    assert w.damage_counts_server == {"HEAVYLOAD": last} and len(r.mod.server_records) > last
    assert [d["side"] for d in w.damage] == ["server"] * min(last, 500)   # World.damage keeps the last 500
    dm = r.out["loop"]["damage"]
    assert dm["polls"] == 5 and dm["fails"] == 0 and dm["lost"] == 0 and dm["since"] == last == dm["merged"]
    assert dm["totals"] == {"HEAVYLOAD": {"n": dm["since"], "amount": pytest.approx(0.05 * dm["since"])}}
    g = GT.grade_d(r.out)
    assert g["health_lost_by_source"]["HEAVYLOAD"]["n"] == dm["since"]
    assert any(l.startswith("health lost by source (the server's damage.watch): HEAVYLOAD") for l in g["report_lines"])


def test_persist_runs_every_persist_s_of_the_loop(tmp_path, monkeypatch):
    r = run_day(tmp_path, monkeypatch, limits={"DAY_CAP_S": 100})
    walls = [w for _, w in r.persists if w is not None]
    assert [round(w) for w in walls[:3]] == [30, 60, 90]
    assert walls[-1] == pytest.approx(100, abs=0.2)                        # the stop's own save


def test_a_fight_is_read_off_the_decision_logs_threat_branch(tmp_path, monkeypatch):
    r = run_day(tmp_path, monkeypatch, limits={"DAY_CAP_S": 20}, zombie_at=8.0)
    fights = r.out["loop"]["fights"]
    assert len(fights) == 1
    f = fights[0]
    loop0 = r.day.t_loop0 - r.mod.t0                                       # the mod's seconds at the loop's start
    assert f["threats"] == 1 and f["health"] == 100.0 and f["fight_ticks"] >= 1
    assert 0 <= f["startS"] - (8.0 - loop0) <= 1.0                          # within a planner tick or two of the sight
    assert f["sent"] >= 1 and f["flee"] == {} and f["end"]["branch"] != "threat" and f["end"]["endS"] > f["startS"]
    assert any(a["type"] == "attack" and a["args"] == {"targetId": ZID} and a["state"] == "done"
               for a in r.out["loop"]["actions"])
    fs = GT.grade_d(r.out)["fights"]
    assert fs["count"] == 1 and fs["fought"] == 1 and fs["fled"] == 0 and fs["open"] == 0
    assert fs["health_lost"] == [0.0]


# ================================================================ the death record and death_explained
def test_a_heavyload_death_keeps_its_record_and_the_frames_explain_it(tmp_path, monkeypatch):
    r = run_day(tmp_path, monkeypatch, die_from=40.0, drain=5.0, client_damage=True)
    st, death = r.out["stop"], r.out["loop"]["death"]
    assert st["reason"] == "death" and st["detail"].endswith("body.health 0") and st["wallS"] < 40.0
    assert set(death) == {"via", "detail", "wallS", "gameMin", "frame", "last_decisions", "last_frames",
                          "server_damage", "client_damage", "window_ms"}
    assert death["via"] == "frame" and death["frame"]["health"] == 0.0
    assert death["last_decisions"] == decisions(tmp_path)[-10:] and len(death["last_decisions"]) == 10
    lf = death["last_frames"]
    assert len(lf) == D.LAST_FRAMES and lf[-1]["body"]["health"] == 0.0 and lf[0]["body"]["health"] == 100.0
    assert all(set(f) >= {"seq", "wallMs", "me", "body", "load", "zombies"} for f in lf)
    assert [f["seq"] for f in lf] == sorted(f["seq"] for f in lf)
    assert len(death["server_damage"]) == 20 == len(r.mod.server_records)  # the final read brought the last ones
    assert {d["tag"] for d in death["server_damage"]} == {"HEAVYLOAD"} and death["server_damage"][0]["i"] == 1
    assert [d["side"] for d in death["client_damage"]] == ["client"]
    assert death["window_ms"]["to"] - death["window_ms"]["from"] == D.DEATH_WINDOW_S * 1000
    g = GT.grade_d(r.out)
    assert g["survived"] is False and g["outcome"] == "died" and g["death_explained"] is True
    assert g["death_explained_by"] == "tagged"
    c = g["death_check"]
    assert c["health_fall"] == pytest.approx(100.0) and c["server_amount"] == pytest.approx(100.0)
    assert c["server_n"] == 20 and c["frames_n"] == 300 and c["why"] is None and c["tagged"]["explained"] is True
    assert c["wound"]["explained"] is False and c["wound"]["why"] == "no wound in the window's frames"
    assert c["frames_window_ms"] == {"from": lf[0]["wallMs"], "to": lf[-1]["wallMs"]}
    assert c["server_window_ms"]["from"] == lf[0]["wallMs"] and c["server_tags"] == {"HEAVYLOAD": 100.0}
    assert g["health_lost_by_source"] == {"HEAVYLOAD": {"n": 20, "amount": 100.0}}
    assert any(l.startswith("death explained by the frames") for l in g["report_lines"])


def test_health_held_just_above_stop_health_is_no_death(tmp_path, monkeypatch):
    r = run_day(tmp_path, monkeypatch, limits={"DAY_CAP_S": 30}, die_from=8.0, drain=5.0, floor=0.5)
    assert r.out["stop"]["reason"] == "day_cap" and "death" not in r.out["loop"]
    assert r.day.frames[-1]["body"]["health"] == 0.5


def _wound_day(tmp_path, monkeypatch, **flags):
    # the zombie stands at 8 tiles from 30 s, closes to 2 at 32 s; health falls 0.5 a tick from 33 s to 0 at 53 s
    kw = dict(die_from=33.0, drain=0.5, server_damage=False, zombie_at=30.0, zombie_far_s=2.0, zombie_dist=2.0,
              bite_at=33.0)
    kw.update(flags)
    return run_day(tmp_path, monkeypatch, **kw)


def test_a_wound_death_is_explained_by_the_wound_arm(tmp_path, monkeypatch):
    r = _wound_day(tmp_path, monkeypatch)
    assert r.out["stop"]["reason"] == "death" and r.out["loop"]["death"]["server_damage"] == []
    g = GT.grade_d(r.out)
    assert g["death_explained"] is True and g["death_explained_by"] == "wound"
    c = g["death_check"]
    assert c["tagged"]["explained"] is False and c["health_fall"] == pytest.approx(100.0) and c["frames_n"] == 300
    w = c["wound"]
    assert w["explained"] is True and w["what"] == "bitten 0 -> 1" and w["wound_health"] == pytest.approx(100.0)
    assert w["frame_seq"] == w["fall_seq"] and w["gameMin"] is not None
    assert w["zombie"]["id"] == ZID and w["zombie"]["dist"] == 2.0 and w["zombie"]["seq"] <= w["frame_seq"]
    assert any(l.startswith("death explained by the frames (wound)") for l in g["report_lines"])


def test_a_wound_death_with_no_zombie_near_is_not_explained(tmp_path, monkeypatch):
    r = _wound_day(tmp_path, monkeypatch, zombie_at=None)
    g = GT.grade_d(r.out)
    assert g["death_explained"] is False and g["death_explained_by"] is None
    assert g["death_check"]["wound"]["why"].startswith("no zombie within 6.0 tiles")
    r = _wound_day(tmp_path / "far", monkeypatch, zombie_far_s=1000.0)       # at 8 tiles: beyond DANGER_R
    assert GT.grade_d(r.out)["death_explained"] is False


def test_a_wound_after_the_fall_began_does_not_explain_it(tmp_path, monkeypatch):
    r = _wound_day(tmp_path, monkeypatch, bite_at=40.0)
    c = GT.grade_d(r.out)["death_check"]
    assert c["explained"] is False and c["explained_by"] is None and "after the fall began" in c["wound"]["why"]


def test_the_wound_arm_reads_parts_and_names_the_nearest_zombie():
    def fr(seq, health, parts=(), zombies=(), **wounds):
        return {"seq": seq, "wallMs": 1000 + 100 * seq, "gameMin": 600 + seq,
                "body": dict({"health": health, "bleeding": 0, "scratched": 0, "bitten": 0, "parts": list(parts)},
                             **wounds), "zombies": list(zombies)}
    near = [{"id": 3, "dist": 5.5}, {"id": 4, "dist": 2.5}, {"id": 9, "dist": 7.0}]
    frames = [fr(1, 100.0, zombies=near), fr(2, 100.0, parts=[{"i": 2, "h": 90.0}]), fr(3, 70.0), fr(4, 0.0)]
    w = GT.death_check({"last_frames": frames})["wound"]
    assert w["explained"] is True and w["what"] == "part 2 appears at 90.0" and w["frame_seq"] == 2
    assert w["zombie"] == {"id": 4, "dist": 2.5, "seq": 1} and w["wound_health"] == 100.0
    frames = [fr(1, 100.0, parts=[{"i": 2, "h": 90.0}], zombies=near), fr(2, 60.0, parts=[{"i": 2, "h": 50.0}]),
              fr(3, 0.0, parts=[{"i": 2, "h": 50.0}])]
    c = GT.death_check({"last_frames": frames, "server_damage": [{"i": 1, "tag": "BLEEDING", "amount": 10.0,
                                                                   "wall": 1300}]})
    assert c["explained_by"] == "wound" and c["wound"]["what"] == "part 2 falls 90.0 -> 50.0"
    assert c["wound"]["wound_health"] == 90.0                                  # the fall 100 less the tagged 10
    frames = [fr(1, 100.0, zombies=[{"id": 9, "dist": 6.01}]), fr(2, 0.0, scratched=1)]
    assert GT.death_check({"last_frames": frames})["explained"] is False      # 6.01 is beyond DANGER_R
    frames = [fr(1, 100.0, zombies=[{"id": 9, "dist": 6.0}]), fr(2, 0.0, bleeding=1)]
    assert GT.death_check({"last_frames": frames})["explained_by"] == "wound"  # within, at exactly 6.0


def test_a_park_in_the_hello_is_bus_dead_and_never_survived(tmp_path, monkeypatch):
    def setup(day):
        day.xs.clients["admin"].seen["lua_error"] = 1
    r = run_day(tmp_path, monkeypatch, no_hello=True, setup=setup)
    st = r.out["stop"]
    assert st["reason"] == "bus_dead" and "parked" in st["detail"] and "started" not in r.out["loop"]
    g = GT.grade_d(r.out)
    assert g["survived"] is None and g["loop_started"] is False


def test_a_stop_before_the_loop_ran_is_never_survived(tmp_path, monkeypatch):
    r = run_day(tmp_path, monkeypatch, no_hello=True, budget_s=5.0)
    assert r.out["stop"]["reason"] == "budget" and "started" not in r.out["loop"]
    g = GT.grade_d(r.out)
    assert g["survived"] is None and g["outcome"] == "undecided: the session stopped on budget before the loop ran"
    o = {"stop": {"reason": "day_cap", "wallS": 9.0}, "loop": {}}
    assert GT.grade_d(o)["survived"] is None and GT.grade_d(dict(o, loop={"started": True}))["survived"] is True


def test_the_damage_listener_is_installed_once_at_the_kits_end(tmp_path, monkeypatch):
    r = run_day(tmp_path, monkeypatch, limits={"DAY_CAP_S": 40})
    dw = [i for i, a in enumerate(r.bus.asked) if a[1] == "damage.watch"]
    installs = [i for i in dw if r.bus.asked[i][2] == "admin"]
    assert len(installs) == 1 and installs[0] == dw[0]
    assert r.bus.asked[installs[0]][3] == D.SERVER_TIMEOUT_S
    item_gets = [i for i, a in enumerate(r.bus.asked) if a[1] == "item.get"]
    stats = [i for i, a in enumerate(r.bus.asked) if a[1] == "stats.all"]
    assert max(item_gets) < installs[0] < min(stats)                        # after the kit, before the loop
    assert all(r.bus.asked[i][2].startswith("admin since ") for i in dw[1:])
    assert r.out["phase_walls"]["damage_hook"]["start"] >= r.out["phase_walls"]["kit"]["end"]


def test_a_death_without_server_records_is_not_explained(tmp_path, monkeypatch):
    r = run_day(tmp_path, monkeypatch, die_from=12.0, drain=5.0, server_damage=False)
    assert r.out["stop"]["reason"] == "death" and r.out["loop"]["death"]["server_damage"] == []
    g = GT.grade_d(r.out)
    assert g["death_explained"] is False and g["death_check"]["server_n"] == 0
    assert "no server damage record" in g["death_check"]["why"]
    assert any(l.startswith("death NOT explained") for l in g["report_lines"])


def test_a_death_whose_server_amounts_miss_the_fall_by_more_than_ten_percent_is_not_explained(tmp_path, monkeypatch):
    r = run_day(tmp_path, monkeypatch, die_from=12.0, drain=5.0, amount=4.0)
    c = GT.grade_d(r.out)["death_check"]
    assert c["explained"] is False and c["server_amount"] == pytest.approx(80.0) and c["diff"] == pytest.approx(20.0)


def test_a_players_reply_without_the_user_is_a_death_with_its_record(tmp_path, monkeypatch):
    r = run_day(tmp_path, monkeypatch, limits={"SERVER_POLL_S": 5}, bus={"gone_from": 35.0})
    st = r.out["stop"]
    assert st["reason"] == "death" and "players reply without admin" in st["detail"]
    death = r.out["loop"]["death"]
    assert death["via"] == "players" and death["frame"] is None and len(death["last_frames"]) == D.LAST_FRAMES
    g = GT.grade_d(r.out)
    assert g["death_explained"] is False and g["death_explained_by"] is None and g["deaths"][0]["via"] == "players"


def _frames(healths, t0=1000, dt=100):
    return [{"seq": i + 1, "wallMs": t0 + i * dt, "body": {"health": h}} for i, h in enumerate(healths)]


def test_death_check_reads_the_window_and_the_ten_percent_line():
    frames = _frames([100.0, 100.0, 60.0, 20.0, 0.0])                     # wallMs 1000..1400; fall 100
    recs = lambda amounts, walls: [{"i": i, "tag": "HEAVYLOAD", "amount": a, "wall": w}  # noqa: E731
                                   for i, (a, w) in enumerate(zip(amounts, walls), 1)]
    ok = GT.death_check({"last_frames": frames, "server_damage": recs([40.0, 40.0, 11.0], [1200, 1300, 1400])})
    assert ok["explained"] is True and ok["server_amount"] == 91.0 and ok["health_fall"] == 100.0  # 9 <= 9.1
    no = GT.death_check({"last_frames": frames, "server_damage": recs([40.0, 40.0, 10.9], [1200, 1300, 1400])})
    assert no["explained"] is False                                         # 9.1 > 9.09
    edge = GT.death_check({"last_frames": frames, "server_damage": recs([50.0, 50.0], [1000, 1400])})
    assert edge["server_n"] == 1 and edge["explained"] is False             # a record at the first frame's time is out
    late = GT.death_check({"last_frames": frames, "server_damage": recs([100.0], [1401])})
    assert late["server_n"] == 0 and late["explained"] is False
    rises = GT.death_check({"last_frames": _frames([50.0, 60.0, 0.0]), "server_damage": recs([60.0], [1200])})
    assert rises["health_fall"] == 60.0 and rises["explained"] is True    # a rise is no fall
    assert GT.death_check({"last_frames": _frames([10.0])})["why"].startswith("fewer than two")
    assert GT.death_check({})["explained"] is False


def test_pair_frame_pairs_within_the_wall_second_only():
    frames = _frames([100.0, 100.0], t0=10_000, dt=500)                    # 10000, 10500
    f, p = D.pair_frame(frames, 11_400)
    assert f["seq"] == 2 and p == {"frameSeq": 2, "frameWallMs": 10_500, "serverWallMs": 11_400, "dtMs": 900,
                                   "paired": True}
    f, p = D.pair_frame(frames, 11_600)
    assert f["seq"] == 2 and p["dtMs"] == 1100 and p["paired"] is False
    f, p = D.pair_frame(frames, 10_250)
    assert f["seq"] == 1 and p["paired"] is True                            # ties go to the earlier seq
    assert D.pair_frame([], 1)[0] is None and D.pair_frame(frames, None)[1]["paired"] is False
    rows = [[480, 0.1, 0.1, 0.1, 100.0, 0.5], [481, 0.1, 0.1, 0.1, 100.0, 0.12]]
    ns = GT.d_needs_summary(rows, [{"paired": False}, {"paired": True}])
    assert ns["paired_rows"] == 1 and ns["unpaired_rows"] == 1
    assert ns["hunger_client_server_max_diff"] == pytest.approx(0.02)       # the unpaired 0.4 is left out


# ================================================================ the stop conditions (test_c_survive.py's, ported)
def test_no_good_server_reply_for_two_polls_stops_the_loop_as_bus_dead(tmp_path, monkeypatch):
    r = run_day(tmp_path, monkeypatch, bus={"stats_bad_from": 0.0, "players_bad_from": 0.0})
    st = r.out["stop"]
    assert st["reason"] == "bus_dead" and "2 consecutive failed server polls" in st["detail"]
    assert st["wallS"] == pytest.approx(60, abs=0.3) and r.out["loop"]["server_fails"] == 2


def test_one_failed_server_poll_between_good_ones_is_not_bus_dead(tmp_path, monkeypatch):
    # the polls land at the mod's ~2.5, 62.5 and 122.5 s; only the second fails, stats and players both
    r = run_day(tmp_path, monkeypatch, limits={"DAY_CAP_S": 130},
                bus={"stats_bad_from": 40.0, "players_bad_from": 40.0, "bad_until": 100.0})
    assert r.out["stop"]["reason"] == "day_cap" and r.out["loop"]["server_fails"] == 1
    assert r.out["loop"]["needs"][1][5] is None and r.out["loop"]["needs"][2][5] == pytest.approx(0.11)
    r = run_day(tmp_path / "b", monkeypatch, limits={"DAY_CAP_S": 130, "SERVER_POLL_S": 20},
                bus={"stats_bad_from": 20.0, "players_bad_from": 20.0, "bad_until": 30.0})
    assert r.out["stop"]["reason"] == "day_cap" and r.out["loop"]["server_fails"] == 1


def test_a_players_error_reply_is_no_death(tmp_path, monkeypatch):
    r = run_day(tmp_path, monkeypatch, limits={"DAY_CAP_S": 30, "SERVER_POLL_S": 5},
                bus={"players_error_from": 12.0})
    assert r.out["stop"]["reason"] == "day_cap" and "death" not in r.out["loop"]
    pe = r.out["loop"]["players_error"]
    assert pe is not None and "TimeoutError" in pe["reply"] and r.out["loop"]["server_fails"] == 0
    r = run_day(tmp_path / "b", monkeypatch, limits={"DAY_CAP_S": 130}, bus={"stats_bad_from": 0.0})
    assert r.out["stop"]["reason"] == "day_cap" and r.out["loop"]["needs"][-1][5] is None


def test_xlib_busdead_stops_the_loop_as_bus_dead(tmp_path, monkeypatch):
    r = run_day(tmp_path, monkeypatch, limits={"SERVER_POLL_S": 5}, bus={"bus_dead_from": 15.0})
    assert r.out["stop"]["reason"] == "bus_dead" and "BusDead" in r.out["stop"]["detail"]


def test_a_bus_dead_before_the_loop_names_the_stop_bus_dead(tmp_path, monkeypatch):
    r = run_day(tmp_path, monkeypatch, bus={"bus_dead_from": 0.0})
    st = r.out["stop"]
    assert st["reason"] == "bus_dead" and st["detail"].startswith("server bus dead after kit")
    assert r.out["phase_walls"]["kit"].get("bus_dead") and r.out["loop"]["server_polls"] == 0


def test_a_silent_link_stops_the_loop_as_bus_dead(tmp_path, monkeypatch):
    r = run_day(tmp_path, monkeypatch, silent_from=10.0)
    st = r.out["stop"]
    silent = 10.0 - (r.day.t_loop0 - r.mod.t0)                               # the loop's seconds at the silence
    assert st["reason"] == "bus_dead" and "no link line" in st["detail"]
    assert 60 <= st["wallS"] - silent < 61


def test_a_parked_client_stops_the_loop_as_bus_dead(tmp_path, monkeypatch):
    r = run_day(tmp_path, monkeypatch, limits={"PERSIST_S": 5}, parked_at=12.0)
    st = r.out["stop"]
    assert st["reason"] == "bus_dead" and "parked" in st["detail"]


def test_a_lua_error_storm_stops_the_loop(tmp_path, monkeypatch):
    r = run_day(tmp_path, monkeypatch, lua_err_from=8.0)
    st = r.out["stop"]
    assert st["reason"] == "lua_error_storm" and "11 lua_error events" in st["detail"]
    assert r.out["frames"]["lua_errors"] == 11 and sum(r.out["loop"]["lua_errors_per_min"].values()) == 11
    assert len(r.out["frames"]["lua_error_msgs"]) == 11


def test_ten_lua_errors_in_a_window_are_not_a_storm(tmp_path, monkeypatch):
    # one a second, read on a 0.1 s poll: at most ten fall inside any 8.5 s window
    r = run_day(tmp_path, monkeypatch, limits={"DAY_CAP_S": 30, "STORM_WINDOW_S": 8.5}, lua_err_from=7.0)
    assert r.out["stop"]["reason"] == "day_cap" and r.out["frames"]["lua_errors"] >= 20


def test_a_backlog_of_lua_errors_read_at_once_is_no_storm(tmp_path, monkeypatch):
    # one error every 7 s of the client clock: never more than 9 in a 60 s window; a stalled stats call holds the
    # driver 85 s, so 12 of them are read in one pump. Stamped at the read, they would be a storm
    r = run_day(tmp_path, monkeypatch, limits={"DAY_CAP_S": 160}, lua_err_from=6.0, lua_err_every=7.0,
                bus={"stall_at": 40.0, "stall_s": 85.0})
    assert r.out["stop"]["reason"] == "day_cap" and r.out["frames"]["lua_errors"] >= 20
    r = run_day(tmp_path / "b", monkeypatch, limits={"DAY_CAP_S": 160}, lua_err_from=6.0,
                bus={"stall_at": 40.0, "stall_s": 85.0})
    assert r.out["stop"]["reason"] == "lua_error_storm"


def test_a_live_host_at_the_ready_readings_never_stops_on_memory(tmp_path, monkeypatch):
    r = run_day(tmp_path, monkeypatch, limits={"DAY_CAP_S": 40, "MEM_POLL_S": 10}, free=lambda: 2.5)
    assert r.out["stop"]["reason"] == "day_cap"
    walls = [m["wallS"] for m in r.out["memory_reads"]]
    assert walls[0] == pytest.approx(10, abs=0.2) and len(walls) >= 3
    assert r.out["memory_reads"] == r.out["loop"]["memory"]
    assert (D.LIVE_MIN_FREE_GB, D.MEM_LOW_READS, D.MIN_FREE_GB) == (0.5, 2, 12.0)


def test_two_consecutive_low_reads_stop_on_memory_and_one_does_not(tmp_path, monkeypatch):
    reads = iter([0.4, 0.4])
    r = run_day(tmp_path, monkeypatch, limits={"MEM_POLL_S": 10}, free=lambda: next(reads))
    st = r.out["stop"]
    assert st["reason"] == "memory" and "2 consecutive reads below 0.5 GB" in st["detail"]
    assert st["wallS"] == pytest.approx(20, abs=0.2) and [m["free_gb"] for m in r.out["memory_reads"]] == [0.4, 0.4]
    alt = iter([0.4, 3.0] * 10)
    r = run_day(tmp_path / "b", monkeypatch, limits={"DAY_CAP_S": 60, "MEM_POLL_S": 10}, free=lambda: next(alt))
    assert r.out["stop"]["reason"] == "day_cap" and len(r.out["memory_reads"]) >= 5
    r = run_day(tmp_path / "c", monkeypatch, limits={"MEM_POLL_S": 10}, free=lambda: None)   # None counts as low
    assert r.out["stop"]["reason"] == "memory" and len(r.out["memory_reads"]) == 2


def test_the_wall_budget_stops_the_loop(tmp_path, monkeypatch):
    r = run_day(tmp_path, monkeypatch, budget_s=25.0)
    st = r.out["stop"]
    assert st["reason"] == "budget" and "past the budget" in st["detail"]
    assert GT.grade_d(r.out)["survived"] is True


def test_a_fault_in_the_loop_stops_it_as_error(tmp_path, monkeypatch):
    def setup(day):
        real = day.planner.tick

        def tick(world, actions):
            if day.ticks >= 5:
                raise ValueError("planner fault")
            return real(world, actions)
        day.planner.tick = tick
    r = run_day(tmp_path, monkeypatch, setup=setup)
    st = r.out["stop"]
    assert st["reason"] == "error" and st["detail"] == "ValueError: planner fault"
    assert "planner fault" in r.out["phase_errors"]["survive"]["error"] and r.out["loop"]["ticks"] == 5
    assert GT.grade_d(r.out)["survived"] is None


def test_a_hello_in_another_mode_fails_the_phase_and_the_loop_never_runs(tmp_path, monkeypatch):
    r = run_day(tmp_path, monkeypatch, hello_mode="chunk")
    assert "not append" in r.out["phase_errors"]["hello"]["error"]
    assert r.out["stop"]["reason"] == "error" and r.out["loop"].get("ticks") is None
    assert "kit" not in r.out["readings"] and r.bus.stats_calls == []


def test_no_hello_names_the_stop_and_grades(tmp_path):
    clock = Clock()
    sd = str(tmp_path / "sd")
    os.makedirs(sd)
    out = D.new_out()
    step = lambda dt: setattr(clock, "t", clock.t + dt)                     # noqa: E731
    xs = X.Xs(out, node=lambda side: side, ask=lambda *a, **k: ["admin"], clock=clock.now, sleep=step,
              budget_s=1e9, user="admin")
    xs.path = str(tmp_path / D.ARTIFACT)
    D.Day(xs, FileTransport(sd, clock=clock.now), clock=clock.now, sleep=step).run()
    assert "no hello line" in out["phase_errors"]["hello"]["error"] and out["stop"]["reason"] == "error"
    g = GT.grade_d(out)
    assert g["survival_s"] is None and g["report_lines"][0].startswith("no loop ran")


def test_the_decision_log_is_copied_with_the_artifact(tmp_path, monkeypatch):
    r = run_day(tmp_path, monkeypatch, limits={"DAY_CAP_S": 5})
    assert r.xs.copied == [D.DECISION_LOG]
    dest = r.xs.copy_artifacts(str(tmp_path / "repo"), "d_survive-x", str(tmp_path), D.ARTIFACT)
    assert sorted(os.listdir(dest)) == sorted([D.ARTIFACT, D.DECISION_LOG])


# ================================================================ grade_d and d_grade
@pytest.mark.parametrize("reason,survived", [("day_cap", True), ("budget", True), ("death", False),
                                             ("bus_dead", None), ("lua_error_storm", None), ("memory", None),
                                             ("error", None)])
def test_survived_is_true_only_for_day_cap_or_budget(reason, survived):
    g = GT.grade_d({"stop": {"reason": reason, "detail": "x", "wallS": 900.0},
                    "loop": {"wallS": 900.0, "started": True}})
    assert g["survived"] is survived
    assert g["outcome"] == {True: "survived (%s)" % reason, False: "died"}.get(
        survived, "undecided: the session stopped on %s" % reason)
    assert g["report_lines"][0].startswith(g["outcome"])


def test_grade_d_on_an_empty_artifact():
    g = GT.grade_d({})
    assert g["stop"] is None and g["survived"] is None and g["survival_s"] is None and g["deaths"] == []
    assert g["death_explained"] is None and g["death_check"] is None and g["actions"]["n"] == 0
    assert g["fights"]["count"] == 0 and g["report_lines"][0].startswith("no loop ran")
    assert GT.grade_d("not a dict")["survival_s"] is None
    json.dumps(g, allow_nan=False)


def test_d_grade_prints_the_report_lines_and_strict_json_and_exits_zero(tmp_path, monkeypatch, capsys):
    r = run_day(tmp_path / "run", monkeypatch, die_from=12.0, drain=5.0)
    p = tmp_path / "d.json"
    o = json.loads((tmp_path / "run" / D.ARTIFACT).read_text(encoding="utf-8"))
    o["loop"]["cost"]["max"] = math.inf
    p.write_text(json.dumps(o))
    assert DG.main([str(p)]) == 0
    text = capsys.readouterr().out
    lines = text.splitlines()
    want = GT.report_lines_d(GT.grade_d(o))
    assert lines[:len(want)] == want and lines[0].startswith("died after")
    g = json.loads("\n".join(lines[len(want):]))
    assert g["death_explained"] is True and g["cost"]["max"] is None and g["stop"]["reason"] == "death"
    assert r.out["stop"]["reason"] == "death"
    p.write_text(json.dumps({}))
    assert DG.main([str(p)]) == 0                                            # no gate: an empty session is 0
    assert DG.main([]) == 2 and DG.main([str(tmp_path / "none.json")]) == 2
