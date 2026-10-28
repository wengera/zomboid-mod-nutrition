"""drivers/x4_link_3.py (Plan 23 X4 session: x4_link_2.py copied, the same gate), base/gates.gate_x4 and
drivers/x4_grade.py, offline: test_x4_link_2.py copied with the module swapped; the driver is never invoked.

The phases run against ScriptedMod, a FakeMod (the schema's line shapes, every line through pza1.encode) ticking on a
fake clock at its frame rate: it answers cmd.txt (Rate, Scan, WalkTo), emits a scan in 20-square parts one a tick,
walks a WalkTo leg after a short delay and writes each frame's cost group. The readings' builders are fed the lines
the session read, so the gate's GO and each falsifier come off the same shapes the live run will write."""
import copy
import json
import math
import os

import pytest

from agent.base import gates as GT
from agent.base import pza1
from agent.base.transport.files import FileTransport
from agent.drivers import x4_grade as XG
from agent.drivers import x4_link_3 as D
from .fakemod import DEFAULT_FRAME, FakeMod

REPO = D.REPO
X = D.X


# ================================================================ static: refusal, constants, imports, trigger
def test_the_driver_refuses_arguments_before_main():
    with open(D.__file__, encoding="utf-8") as fh:
        src = fh.read()
    i_ref, i_main = src.index("refusal = parse_argv(sys.argv[1:], __file__)"), src.rindex("    main()")
    assert src.index('if __name__ == "__main__":') < i_ref < i_main
    assert "sys.exit(refusal)" in src[i_ref:i_main]
    assert D.parse_argv(["x"], D.__file__) and D.parse_argv(["--help"], D.__file__)
    assert D.parse_argv([], D.__file__) is None


def test_the_constants_name_the_drivers_own_file_key_artifact_and_profile():
    assert os.path.basename(D.__file__) == D.DRIVER == D.KEY + ".py" == "x4_link_3.py"
    assert D.KEY == "x4_link_3" and D.ARTIFACT == "x4_link_3.json"
    assert D.PROFILE == "testing/profiles/agent-nozombies.toml" and os.path.isfile(os.path.join(REPO, D.PROFILE))
    want = {"BUDGET_S": 840.0, "USER": "admin", "MIN_FREE_GB": 12.0, "RATE60_S": 30.0, "WORST_WINDOW_S": 600.0,
            "WALK_LEGS": 20, "LEG_DX": 6, "LEG_TIMEOUT_S": 30.0, "SCAN_R": 15, "SCAN_TIMEOUT_S": 60.0,
            "MOVE_EPS_TILES": 0.01, "SIDECAR_MEAN_MS": 1.0, "SIDECAR_WORST_MS": 3.0, "HELLO_TIMEOUT_S": 60.0}
    for k, v in want.items():
        assert getattr(D, k) == v, k
        assert k == "USER" or D.CONSTANTS[k] == v, k
    assert D.SIDECAR_MEAN_MS == GT.SIDECAR_MEAN_MS and D.SIDECAR_WORST_MS == GT.SIDECAR_WORST_MS
    assert D.WORST_WINDOW_S == GT.WORST_SPAN_S and D.WALK_LEGS == GT.MIN_LEGS
    assert GT.RATE60_MIN_FRAMES == int(0.9 * 60 * D.RATE60_S)


def test_nothing_is_imported_from_a_frozen_driver():
    src = open(D.__file__, encoding="utf-8").read()
    imports = [l.split("#")[0].strip() for l in src.splitlines() if l.strip().startswith(("import ", "from "))]
    drivers = [l for l in imports if "drivers" in l or l.split()[1].split(".")[0] in (
        "a_pipe", "a_pipe_2", "a_pipe_3", "a_pipe_4", "b_actions", "b_actions_2", "c_survive", "c_survive_2",
        "c_survive_dense", "p22_probe")]
    assert drivers == [], drivers
    assert "import _dlib as DL" in imports and "import xlib as X" in imports
    for frozen in ("agent.link", "agent.grades", "agent.world", "agent.policy", "link_for"):
        assert frozen not in src, frozen
    assert "X4(xs, FileTransport(DL.state_dir(clients[USER]))).run()" in src
    assert "make_client=clearing_make_client(session.make_client)" in src
    assert "def memory_gate(xs" in src and "DL.wait_memory" in src and "DL.clear_state_dir(c)" in src
    assert D.PARK_RX == r"LuaError|STACK TRACE|attempted index|tried to call nil"


def test_the_sidecar_trigger_is_stated_before_the_run():
    doc = GT.__doc__
    i = doc.index("THE SIDECAR TRIGGER")
    stated = doc[i:doc.index("\n\n", i)]
    assert "1 ms mean" in stated and "3 ms worst" in stated and "linkMs" in stated
    assert "SIDECAR_MEAN_MS = 1.0" in stated and "SIDECAR_WORST_MS =" in stated and "3.0" in stated
    assert "gate_x4_2" in doc and "FROZEN" in doc


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
    tracked["v"] = "testing/artifacts/x4_link_3-20261027-120000/x4_link_3.json"
    assert D.preboot(D.__file__)[1] is False
    tracked["v"] = ""
    assert D.preboot(os.path.join(os.path.dirname(D.__file__), "x4_grade.py"))[1] is False


def test_driver_checks_refuse_a_dirty_lua_base_or_driver():
    say = lambda *a: ""
    c, ok = D.driver_checks(D.__file__, git_say=say, git_dirty=lambda rel: (False, ""))
    assert ok and c["no_committed_artifact"] is True and c["profile_exists"] is True
    for dirty in ("testing/PZAgent", "testing/agent/base", "testing/agent/drivers/x4_link_3.py"):
        c, ok = D.driver_checks(D.__file__, git_say=say, git_dirty=lambda rel, d=dirty: (rel == d, ""))
        assert ok is False, dirty
    c, ok = D.driver_checks(D.__file__, git_say=say, git_dirty=lambda rel: (None, "no git"))
    assert ok is False                                  # unknown is not clean
    c, ok = D.driver_checks(D.__file__, git_say=lambda *a: "testing/artifacts/x4_link_3-1/x4_link_3.json",
                            git_dirty=lambda rel: (False, ""))
    assert ok is False and c["no_committed_artifact"] is False


# ================================================================ ScriptedMod: the fake Lua on a fake clock
class Clock:
    def __init__(self):
        self.t = 1_790_000_000.0

    def now(self):
        return self.t


def square(x, y, extra_door=None):
    solid = (x * 7 + y * 3) % 11 == 0
    has_door = (not solid and x % 9 == 0 and y % 4 == 0) or (x, y) == extra_door
    door = {"open": False, "locked": False, "barricaded": False} if has_door else None
    window = ({"open": False, "locked": True, "barricaded": False}
              if not solid and door is None and (x + 2 * y) % 13 == 0 else None)
    conts = [{"type": "crate", "n": 1, "items": ["Base.Hammer"]}] if not solid and (x * y) % 17 == 0 else []
    if not solid and (x + y) % 23 == 0:
        conts.append({"type": "fridge", "n": 0, "items": []})
    return {"x": x, "y": y, "z": 0, "solid": solid, "solidTrans": False, "light": 1, "room": None, "building": None,
            "door": door, "window": window, "containers": conts, "floor": []}


COST = {"tickMs": 0.6, "actMs": 0.05, "senseMs": 0.1, "mapMs": 0.0, "linkMs": 0.4, "tickMaxMs": 1.0, "over5": 0,
        "dropped": 0}


class ScriptedMod(FakeMod):
    """The fake Lua: sleep(dt) runs its ticks (one frame a tick at `hz`) on the shared clock. Flags: `still` (a walk
    never moves; it times out), `new_door` (a door appears on a square after the first scan, with no map delta),
    `lua_error_at` (a lua_error event on that tick), `short` (a walk stops that many tiles short of its target),
    `cost` laid over COST."""
    SPEED = 3.0           # tiles a second
    DELAY = 2             # ticks between the accepted act and the first step

    def __init__(self, d, clock, still=False, new_door=None, lua_error_at=None, short=0.0, **cost):
        super().__init__(d, clock=clock.now)
        self.clk = clock
        self.hz, self.x, self.y = 10, 100.5, 200.5
        self.still, self.new_door, self.lua_error_at, self.short = still, new_door, lua_error_at, short
        self.cost = dict(COST, **cost)
        self.cmd_seen, self.goal, self.parts, self.scans, self.ticks = 0, None, [], 0, 0
        self.next_t = clock.t
        self.hello()
        self._tick()

    def sleep(self, dt):
        end = self.clk.t + dt
        while self.next_t <= end:
            self.clk.t = self.next_t
            self._tick()
            self.next_t += 1.0 / self.hz
        self.clk.t = end

    def _poll(self):
        p = os.path.join(self.dir, "cmd.txt")
        if not os.path.isfile(p):
            return
        with open(p, encoding="utf-8") as f:
            cmd = json.loads(f.read())
        if cmd["seq"] <= self.cmd_seen:
            return
        self.cmd_seen = cmd["seq"]
        t, aid, args = cmd["type"], cmd["aid"], cmd["args"]
        if self.goal is not None:
            self.act(self.goal["aid"], "failed", "walkTo", reason="superseded")
            self.goal = None
        self.act(aid, "accepted", t)
        if t == "rate":
            self.hz = args["hz"]
            self.act(aid, "done", t, result={})
        elif t == "scan":
            self.scans += 1
            door = self.new_door if self.scans > 1 else None
            cx, cy, r = math.floor(self.x), math.floor(self.y), args["r"]
            grid = [square(x, y, door) for y in range(cy - r, cy + r + 1) for x in range(cx - r, cx + r + 1)]
            n = math.ceil(len(grid) / 20)
            self.parts = [(i + 1, n, grid[i * 20:(i + 1) * 20]) for i in range(n)]
            self.act(aid, "done", t, result={})
        elif t == "walkTo":
            back = math.copysign(self.short, self.x - args["x"]) if self.short else 0.0
            self.goal = {"aid": aid, "x": args["x"] + back, "y": args["y"], "wait": self.DELAY}

    def _tick(self):
        self.ticks += 1
        self._poll()
        scanning = bool(self.parts)
        if self.parts:
            part, parts, sq = self.parts.pop(0)
            self.map_full(sq, scan_id=self.scans, part=part, parts=parts)
        g = self.goal
        if g is not None and not self.still:
            if g["wait"] > 0:
                g["wait"] -= 1
            else:
                dx, dy = g["x"] - self.x, g["y"] - self.y
                d, step = math.hypot(dx, dy), self.SPEED / self.hz
                if d <= step:
                    self.x, self.y = g["x"], g["y"]
                    self.act(g["aid"], "done", "walkTo", result={})
                    self.goal = None
                else:
                    self.x, self.y = self.x + dx / d * step, self.y + dy / d * step
        if self.ticks == self.lua_error_at:
            self.event("lua_error", msg="attempted index: x of non-table")
        me = dict(DEFAULT_FRAME["me"], x=self.x, y=self.y, moving=self.goal is not None)
        self.frame(me=me, cost=dict(self.cost, mapMs=0.8 if scanning else 0.0))


# the probe's real stats.all reply (testing/artifacts/p22_probe-20261027-032502/p22_probe.json readings.server[0].ack)
PROBE_STATS = {"Anger": 0, "Boredom": 0, "Discomfort": 0, "Endurance": 0.8892875909805298,
               "Fatigue": 0.03465772420167923, "Fitness": 0, "FoodSickness": 0, "Hunger": 0.030409572646021843,
               "Idleness": 0, "Intoxication": 0, "Morale": 1, "NicotineWithdrawal": 0, "Pain": 3.1785154342651367,
               "Panic": 0, "Poison": 0, "Sanity": 1, "Sickness": 0, "Stress": 0, "Temperature": 37.22496032714844,
               "Thirst": 0.026972748339176178, "Unhappiness": 0, "Wetness": 0, "ZombieFever": 0, "ZombieInfection": 0}


def run_x4(tmp_path, budget_s=1e9, **flags):
    clock = Clock()
    sd = str(tmp_path / "clients" / "admin" / "Lua" / "pzagent" / "admin")
    mod = ScriptedMod(sd, clock, **flags)
    out = D.new_out()
    asked = []

    def ask(node, cmd, args, timeout=30):
        asked.append((node, cmd, args, timeout))
        mod.sleep(0.05)
        if cmd == "players":
            return ["admin"]
        return {"side": "server", "stats": dict(PROBE_STATS), "missing": {}, "wall": int(clock.t * 1000),
                "user": args, "worldAge": 3.216904640197754, "mult": 4.795048236846924}

    xs = X.Xs(out, node=lambda side: side, ask=ask, clock=clock.now, sleep=mod.sleep, budget_s=budget_s,
              user="admin")
    xs.path = str(tmp_path / D.ARTIFACT)
    x4 = D.X4(xs, FileTransport(sd, clock=clock.now), clock=clock.now, sleep=mod.sleep)
    x4.run()
    out["frames"]["parks"] = 0              # main's read_logs: the console read, no client here
    out["finished"] = True
    return out, mod, asked


@pytest.fixture(scope="module")
def clean_run(tmp_path_factory):
    """Every driver constant as the live run's but the pump's period: on this host each read of a state.log just
    appended to costs a few ms (a scan of the growing file), so the fake run polls every 0.25 s instead of 0.05 s;
    every reading is by seq and the client's wallMs, none by the poll."""
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(D, "POLL_S", 0.25)
        out, mod, asked = run_x4(tmp_path_factory.mktemp("x4"))
    return out, mod, asked


# ================================================================ the fake run: every phase's reading and the GO
def test_a_clean_fake_run_reads_every_phase_and_grades_go(clean_run):
    out, mod, asked = clean_run
    assert out["phase_errors"] == {} and out.get("budget_stop") is None
    rd = out["readings"]
    assert list(rd) == list(D.PHASES)
    assert rd["hello"]["ok"] and rd["hello"]["proto"] == "PZA/1" and rd["hello"]["first_frame"]["seq"] == 2
    r60 = rd["rate60"]
    assert r60["rate_on"]["state"] == "done" and r60["rate_off"]["state"] == "done" and mod.hz == 10
    # from the done act to RATE60_S after the poll that read it, plus the last pump: 30 s and up to two polls
    assert 1800 <= r60["frames"] <= 60 * (30 + 2 * 0.25) and len(r60["tickMs"]) == r60["frames"]
    assert r60["tick_mean_ms"] == pytest.approx(0.6) and 29.9 < r60["span_s"] <= 30.5
    sc = rd["scan"]
    assert sc["parts"] == 49 and sc["got"] == 49 and sc["complete"] and sc["squares"] == 961
    assert sc["act"]["state"] == "done" and 0.8 in sc["mapMs"]
    walk = rd["walk"]
    assert len(walk["legs"]) == 20
    for i, leg in enumerate(walk["legs"]):
        assert leg["end"]["state"] == "done" and leg["settled"] is True, leg
        assert leg["target"]["x"] == pytest.approx(leg["x0"] + (6 if i % 2 == 0 else -6))
        fm = leg["first_move"]
        assert fm is not None and fm["seq"] > leg["accepted_seq"]
        assert set(fm) == {"seq", "wallMs", "x", "y"}
        # the accept's own tick spends one DELAY tick, the next the other, the third steps: 200 ms at 10 Hz
        assert fm["wallMs"] - leg["accepted_wallMs"] == pytest.approx(200, abs=1)
    fs = rd["final_scan"]
    assert fs["scan"]["complete"] and fs["final_squares"] == 961 and fs["kept_squares"] >= 961
    for kind in GT.MAP_KINDS:
        assert fs["kept"][kind]["ratio"] == 1.0 and fs["kept"][kind]["total"] > 0, kind
        assert fs["kept"][kind]["absent"] == 0 and fs["kept"][kind]["seen"] == fs["kept"][kind]["total"], kind
    assert fs["settled"] is True
    ww = rd["worst_window"]
    assert ww["stopped"] == "span" and ww["span_s"] >= 600.0
    assert ww["span_s"] == D.frames_span_s(out["frames"]["cost"][:ww["frames"]])
    assert [a[1] for a in asked] == ["stats.all", "players"] and rd["server"]["players"]["ack"] == ["admin"]
    assert rd["server"]["stats"]["ack"]["missing"] == {} and "Hunger" in rd["server"]["stats"]["ack"]["stats"]
    assert all(a[3] == 10.0 for a in asked)
    fr = out["frames"]
    assert fr["n"] == len(fr["cost"]) and fr["gaps"] == 0 and fr["bad"] == 0 and fr["lua_errors"] == 0
    assert set(fr["cost"][0]) == {"seq", "tick", "wallMs", "cost"}
    assert list(fr["cost"][0]["cost"]) == list(pza1.GROUPS["cost"])
    g = GT.gate_x4(out)
    assert g["verdict"] == "GO", g
    assert g["sidecar_trigger"] == "not fired" and g["emit_mean_ms"] == pytest.approx(0.4)
    json.dumps(out, allow_nan=False)                    # the artifact persists as plain JSON


def test_a_walk_that_never_moves_reads_no_first_move_and_fails_the_move_gate(tmp_path, monkeypatch):
    monkeypatch.setattr(D, "WALK_LEGS", 2)
    monkeypatch.setattr(D, "LEG_TIMEOUT_S", 3.0)
    monkeypatch.setattr(D, "WORST_WINDOW_S", 5.0)
    monkeypatch.setattr(D, "RATE60_S", 2.0)
    out, mod, _ = run_x4(tmp_path, still=True)
    legs = out["readings"]["walk"]["legs"]
    assert [l["end"]["state"] for l in legs] == ["timeout", "timeout"]
    assert all(l["first_move"] is None and l["accepted_seq"] is not None for l in legs)
    assert GT.leg_move_ms(legs) == [math.inf, math.inf]
    assert GT.gate_x4(out)["pass"]["cmd_move_p90"] is False


def test_a_door_the_kept_map_never_heard_of_fails_map_kept(tmp_path, monkeypatch):
    monkeypatch.setattr(D, "WALK_LEGS", 2)
    monkeypatch.setattr(D, "WORST_WINDOW_S", 5.0)
    monkeypatch.setattr(D, "RATE60_S", 2.0)
    out, _, _ = run_x4(tmp_path, new_door=(101, 201))
    kept = out["readings"]["final_scan"]["kept"]
    assert kept["doors"]["kept"] == kept["doors"]["total"] - 1 and kept["doors"]["ratio"] < 0.99
    assert kept["walls"]["ratio"] == 1.0
    assert GT.gate_x4(out)["pass"]["map_kept"] is False


def test_a_short_last_leg_across_a_square_edge_leaves_the_ratio_and_counts_the_new_columns_absent(tmp_path,
                                                                                                    monkeypatch):
    """One leg +6 from 100.5 that stops 0.6 short: 105.9, across the edge into square 105. The final scan, centred
    there (x 90..120), holds columns 116..120 the first scan (x 85..115) never sent: absent, not lost."""
    monkeypatch.setattr(D, "WALK_LEGS", 1)
    monkeypatch.setattr(D, "WORST_WINDOW_S", 5.0)
    monkeypatch.setattr(D, "RATE60_S", 2.0)
    out, mod, _ = run_x4(tmp_path, short=0.6)
    assert mod.x == pytest.approx(105.9) and math.floor(mod.x) == 105
    fs = out["readings"]["final_scan"]
    assert fs["settled"] is True and fs["x"] == pytest.approx(105.9)
    new = [square(x, y) for x in range(116, 121) for y in range(185, 216)]
    want = {"walls": sum(s["solid"] for s in new), "doors": sum(s["door"] is not None for s in new),
            "windows": sum(s["window"] is not None for s in new), "containers": sum(len(s["containers"]) for s in new)}
    for kind in GT.MAP_KINDS:
        k = fs["kept"][kind]
        assert k["absent"] == want[kind] and k["ratio"] == 1.0 and k["kept"] == k["total"] - k["absent"], (kind, k)
    assert sum(want.values()) > 0 and GT.gate_x4(out)["pass"]["map_kept"] is True


def test_a_reserve_stop_keeps_the_server_reading_and_the_artifact_graded(tmp_path, monkeypatch):
    monkeypatch.setattr(D, "WALK_LEGS", 1)
    monkeypatch.setattr(D, "RATE60_S", 2.0)
    out, _, asked = run_x4(tmp_path, budget_s=70.0)
    ww = out["readings"]["worst_window"]
    assert ww["stopped"] == "reserve" and ww["span_s"] < 600.0 and out.get("budget_stop") is None
    assert [a[1] for a in asked] == ["stats.all", "players"] and all(a[3] <= 10.0 for a in asked)
    assert out["readings"]["server"]["players"]["ack"] == ["admin"] and "server" not in out["phase_errors"]
    g = GT.gate_x4(out)
    assert g["pass"]["worst_tick"] is False and g["gates"]["worst_tick"]["value"]["span_s"] < 600.0
    persisted = tmp_path / D.ARTIFACT
    assert persisted.is_file() and XG.main([str(persisted)]) == 1


def test_the_server_steps_take_the_budgets_remaining_seconds(tmp_path):
    clock = Clock()
    out = D.new_out()
    seen = []
    xs = X.Xs(out, node=lambda side: side, ask=lambda n, c, a, timeout=30: seen.append(timeout) or ["admin"],
              clock=clock.now, budget_s=100.0, user="admin")
    x4 = D.X4(xs, FileTransport(str(tmp_path)), clock=clock.now)
    clock.t += 96.0
    x4.server()
    assert seen == [4.0, 4.0]
    clock.t += 10.0
    x4.server()
    assert seen[2:] == [1.0, 1.0]


def test_a_lua_error_event_is_counted_and_fails_its_gate(tmp_path, monkeypatch):
    monkeypatch.setattr(D, "WALK_LEGS", 1)
    monkeypatch.setattr(D, "WORST_WINDOW_S", 5.0)
    monkeypatch.setattr(D, "RATE60_S", 2.0)
    out, _, _ = run_x4(tmp_path, lua_error_at=5)
    assert out["frames"]["lua_errors"] == 1 and out["frames"]["lua_error_msgs"] == ["attempted index: x of non-table"]
    assert GT.gate_x4(out)["pass"]["lua_errors"] is False


def test_a_link_cost_over_the_trigger_fires_the_sidecar_ungraded(tmp_path, monkeypatch):
    monkeypatch.setattr(D, "WALK_LEGS", 1)
    monkeypatch.setattr(D, "WORST_WINDOW_S", 5.0)
    monkeypatch.setattr(D, "RATE60_S", 2.0)
    out, _, _ = run_x4(tmp_path, linkMs=1.1)
    g = GT.gate_x4(out)
    assert g["sidecar_trigger"] == "fired" and g["emit_mean_ms"] == pytest.approx(1.1)
    assert "sidecar_trigger" not in g["pass"]


def test_no_hello_skips_every_phase_but_server(tmp_path, monkeypatch):
    clock = Clock()
    sd = str(tmp_path / "sd")
    os.makedirs(sd)
    out = D.new_out()
    xs = X.Xs(out, node=lambda side: side, ask=lambda *a, **k: ["admin"], clock=clock.now,
              sleep=lambda dt: setattr(clock, "t", clock.t + dt), budget_s=1e9, user="admin")
    D.X4(xs, FileTransport(sd, clock=clock.now), clock=clock.now,
         sleep=lambda dt: setattr(clock, "t", clock.t + dt)).run()
    assert "hello" in out["phase_errors"] and list(out["readings"]) == ["hello", "server"]
    assert out["readings"]["hello"]["ok"] is False
    assert GT.gate_x4(out)["verdict"] == "NO-GO"


# ================================================================ the builders, alone
def _lines(tmp_path, write):
    clock = Clock()
    mod = FakeMod(str(tmp_path / "b"), clock=clock.now)
    write(mod, clock)
    return FileTransport(str(tmp_path / "b")).lines()


def test_first_move_is_the_first_frame_after_the_accept_off_the_accept_position(tmp_path):
    def write(mod, clock):
        for x in (100.0, 101.0):                                   # the position at accept is the last before it
            clock.t += 0.1
            mod.frame(me=dict(DEFAULT_FRAME["me"], x=x))
        mod.act("a1", "accepted", "walkTo")
        for x in (101.0, 101.005, 100.99, 105.0):
            clock.t += 0.1
            mod.frame(me=dict(DEFAULT_FRAME["me"], x=x))
    lines = _lines(tmp_path, write)
    row = D.leg_reading(lines, "a1", 100.0, 200.0)
    assert row["at_accept"] == {"x": 101, "y": 200} and row["accepted_seq"] == 3
    assert row["first_move"]["seq"] == 6 and row["first_move"]["x"] == 100.99
    assert D.leg_reading(lines, "a1", 100.0, 200.0, eps=0.5)["first_move"]["x"] == 105
    assert D.leg_reading(lines, "a2", 100.0, 200.0)["first_move"] is None          # never accepted


def test_rate60_keeps_only_the_frames_after_the_rates_done_act(tmp_path):
    def write(mod, clock):
        clock.t += 0.1
        mod.frame(cost=dict(COST, tickMs=3.0))                     # a 10 Hz frame read in the window's slice
        mod.act("a1", "done", "rate", result={})
        for _ in range(3):
            clock.t += 0.016
            mod.frame(cost=COST)
    lines = _lines(tmp_path, write)
    r = D.rate60_reading(lines, 2, 0.05)
    assert r["frames"] == 3 and r["tickMs"] == [0.6] * 3 and r["first_seq"] == 3 and r["last_seq"] == 5
    assert r["span_s"] == pytest.approx(0.032, abs=0.002) and r["seconds"] == 0.05
    assert D.rate60_reading(lines, None, 0.05)["frames"] == 0                 # no done act: no window


def test_map_kept_counts_by_kind_and_reads_an_empty_kind_as_one(tmp_path):
    final = [square(x, 0) for x in range(0, 60)]
    kept = copy.deepcopy(final)
    conts = [(s["x"], s["y"], 0, c["type"]) for s in kept for c in s["containers"]]
    m = D.map_kept(kept, conts, final)
    assert all(m[k]["ratio"] == 1.0 for k in GT.MAP_KINDS) and m["walls"]["total"] > 0
    lost = [s for s in kept if not s["solid"]][:1]
    walls = [s for s in kept if s["solid"]]
    m = D.map_kept(lost + walls[1:], conts[1:], final)
    assert m["walls"]["kept"] == m["walls"]["total"] - 1 and m["containers"]["kept"] == m["containers"]["total"] - 1
    m = D.map_kept([], [], [square(1, 1)])
    assert m["doors"] == {"kept": 0, "total": 0, "absent": 0, "seen": 0, "ratio": 1.0,
                          "note": "no square of this kind both maps saw: ratio 1.0"}


def test_map_kept_reads_fidelity_over_the_squares_both_saw_and_reports_absent():
    first = [square(x, y) for x in range(0, 40) for y in range(0, 6)]
    final = [square(x, y) for x in range(1, 41) for y in range(0, 6)]       # one column the kept map never saw
    conts = [(s["x"], s["y"], 0, c["type"]) for s in first for c in s["containers"]]
    m = D.map_kept(first, conts, final)
    col = [s for s in final if s["x"] == 40]
    want = {"walls": sum(s["solid"] for s in col), "doors": sum(s["door"] is not None for s in col),
            "windows": sum(s["window"] is not None for s in col),
            "containers": sum(len(s["containers"]) for s in col)}
    assert sum(want.values()) > 0
    for kind in GT.MAP_KINDS:
        assert m[kind]["absent"] == want[kind] and m[kind]["ratio"] == 1.0, (kind, m[kind])
        assert m[kind]["seen"] == m[kind]["total"] - m[kind]["absent"] == m[kind]["kept"]


def test_scan_reading_waits_for_every_part_of_the_newest_scan(tmp_path):
    def write(mod, clock):
        mod.map_full([square(1, 1)], scan_id=1, part=1, parts=1)
        mod.frame(cost=dict(COST, mapMs=2.0))
        mod.map_full([square(1, 1), square(2, 1)], scan_id=2, part=1, parts=3)
        mod.map_full([square(3, 1)], scan_id=2, part=3, parts=3)
        mod.frame(cost=dict(COST, mapMs=3.0))
    lines = _lines(tmp_path, write)
    r = D.scan_reading(lines)
    assert (r["scanId"], r["parts"], r["got"], r["complete"], r["squares"]) == (2, 3, 2, False, 3)
    assert r["mapMs"] == [2.0, 3.0]
    assert [s["x"] for s in D.scan_squares(lines)] == [1, 2, 3]


# ================================================================ gate_x4: each gate's falsifier
def passing_out():
    """A passing artifact built by the phases' builders over FakeMod lines: 1800 frames 16 ms apart at tickMs 0.6 and
    linkMs 0.4, 600 s more at 1 s, twenty legs moving 200 ms after their accept, a whole kept map."""
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        clock = Clock()
        mod = FakeMod(d, clock=clock.now)
        mod.hello()
        mod.act("a1", "done", "rate", result={})
        for _ in range(1800):
            clock.t += 0.016
            mod.frame(cost=COST)
        for _ in range(600):
            clock.t += 1.0
            mod.frame(cost=COST)
        lines = FileTransport(d).lines()
    out = D.new_out()
    out["readings"]["hello"] = D.hello_reading(lines)
    out["readings"]["rate60"] = D.rate60_reading(lines[:1802], 2, 30.0)
    out["frames"]["cost"] = [D.cost_row(l) for l in lines if l["kind"] == "frame"]
    out["frames"].update(n=len(out["frames"]["cost"]), gaps=0, lua_errors=0, parks=0)
    out["readings"]["walk"] = {"legs": [{"accepted_wallMs": 1000 * i, "first_move": {"seq": i, "wallMs": 1000 * i + 200,
                                                                                    "x": 1, "y": 1}}
                                        for i in range(20)]}
    final = [square(x, y) for x in range(80) for y in range(3)]
    conts = [(s["x"], s["y"], 0, c["type"]) for s in final for c in s["containers"]]
    out["readings"]["final_scan"] = {"kept": D.map_kept(final, conts, final)}
    out["finished"] = True
    return out


@pytest.fixture(scope="module")
def good():
    return passing_out()


def test_gate_x4_passes_a_passing_set_with_the_trigger_beside_it(good):
    g = GT.gate_x4(copy.deepcopy(good))
    assert g["verdict"] == "GO" and set(g["pass"]) == set(GT.GRADED) and all(g["pass"].values()), g
    assert g["gates"]["tick_mean_at60"]["n"] == 1800 and g["gates"]["tick_mean_at60"]["value"] == pytest.approx(0.6)
    assert g["gates"]["worst_tick"]["value"]["span_s"] >= 600.0
    assert g["gates"]["cmd_move_p90"]["value"] == 200
    assert set(g["gates"]["map_kept"]["value"]) == set(GT.MAP_KINDS)
    assert g["sidecar_trigger"] == "not fired" and g["emit_mean_ms"] == pytest.approx(0.4)
    for gate in g["gates"].values():
        assert set(gate) == {"ok", "value", "threshold", "n"}


def _fails_alone(out, name):
    g = GT.gate_x4(out)
    assert [k for k, v in g["pass"].items() if not v] == [name], g["pass"]
    assert g["verdict"] == "NO-GO"
    return g


def test_a_tick_mean_of_1_2_fails(good):
    o = copy.deepcopy(good)
    o["readings"]["rate60"]["tickMs"] = [1.2] * 1800
    assert _fails_alone(o, "tick_mean_at60")["gates"]["tick_mean_at60"]["value"] == pytest.approx(1.2)


def test_too_few_60_hz_frames_fail(good):
    o = copy.deepcopy(good)
    o["readings"]["rate60"]["tickMs"] = o["readings"]["rate60"]["tickMs"][:1619]
    _fails_alone(o, "tick_mean_at60")
    o["readings"]["rate60"]["tickMs"] = [0.6] * 1620
    assert GT.gate_x4(o)["verdict"] == "GO"


def test_one_over5_fails(good):
    o = copy.deepcopy(good)
    o["frames"]["cost"][700]["cost"]["over5"] = 1
    _fails_alone(o, "worst_tick")


@pytest.mark.parametrize("top, ok", [(3.0, True), (3.01, False)])
def test_the_worst_tick_is_at_most_3_ms(good, top, ok):
    o = copy.deepcopy(good)
    o["frames"]["cost"][900]["cost"]["tickMaxMs"] = top
    assert GT.gate_x4(o)["pass"]["worst_tick"] is ok


def test_a_worst_window_short_of_600_s_fails(good):
    o = copy.deepcopy(good)
    o["frames"]["cost"] = o["frames"]["cost"][:1800 + 570]
    _fails_alone(o, "worst_tick")


def test_19_legs_fail(good):
    o = copy.deepcopy(good)
    o["readings"]["walk"]["legs"] = o["readings"]["walk"]["legs"][:19]
    _fails_alone(o, "cmd_move_p90")


def test_a_leg_without_first_move_counts_inf(good):
    o = copy.deepcopy(good)
    legs = o["readings"]["walk"]["legs"]
    legs[0]["first_move"] = None
    legs[1]["accepted_wallMs"] = None
    assert GT.leg_move_ms(legs)[:2] == [math.inf, math.inf]
    assert GT.gate_x4(o)["pass"]["cmd_move_p90"] is True       # p90 of 20 is the 18th: two infs sit above it
    legs[2]["first_move"] = None
    g = _fails_alone(o, "cmd_move_p90")
    assert g["gates"]["cmd_move_p90"]["value"] == math.inf


def test_a_slow_p90_fails(good):
    o = copy.deepcopy(good)
    for leg in o["readings"]["walk"]["legs"][:3]:
        leg["first_move"]["wallMs"] = leg["accepted_wallMs"] + 500
    _fails_alone(o, "cmd_move_p90")


@pytest.mark.parametrize("kind", GT.MAP_KINDS)
def test_map_kept_at_0_98_fails(good, kind):
    o = copy.deepcopy(good)
    o["readings"]["final_scan"]["kept"][kind]["ratio"] = 0.98
    _fails_alone(o, "map_kept")
    o["readings"]["final_scan"]["kept"][kind]["ratio"] = 0.99
    assert GT.gate_x4(o)["verdict"] == "GO"


@pytest.mark.parametrize("name", ["gaps", "lua_errors", "parks"])
def test_one_gap_lua_error_or_park_fails(good, name):
    o = copy.deepcopy(good)
    o["frames"][name] = 1
    _fails_alone(o, name)


@pytest.mark.parametrize("name, cut", [
    ("tick_mean_at60", lambda o: o["readings"].pop("rate60")),
    ("worst_tick", lambda o: o["frames"].pop("cost")),
    ("gaps", lambda o: o["frames"].pop("gaps")),
    ("lua_errors", lambda o: o["frames"].pop("lua_errors")),
    ("parks", lambda o: o["frames"].update(parks=None)),
    ("cmd_move_p90", lambda o: o["readings"].pop("walk")),
    ("map_kept", lambda o: o["readings"].pop("final_scan")),
])
def test_a_missing_reading_fails_its_gate_with_value_none(good, name, cut):
    o = copy.deepcopy(good)
    cut(o)
    g = GT.gate_x4(o)
    assert g["pass"][name] is False and g["gates"][name]["value"] is None and g["verdict"] == "NO-GO"


@pytest.mark.parametrize("link, top, trigger", [(1.1, 1.1, "fired"), (0.3, 0.3, "not fired"),
                                                (0.3, 3.1, "fired"), (0.3, 3.0, "not fired")])
def test_the_sidecar_trigger(good, link, top, trigger):
    o = copy.deepcopy(good)
    for r in o["frames"]["cost"]:
        r["cost"]["linkMs"] = link
    o["frames"]["cost"][5]["cost"]["linkMs"] = top
    g = GT.gate_x4(o)
    assert g["sidecar_trigger"] == trigger and g["verdict"] == "GO"
    assert g["emit_worst_ms"] == pytest.approx(max(link, top))


def test_the_sidecar_reads_flushing_ticks_only(good):
    o = copy.deepcopy(good)
    for i, r in enumerate(o["frames"]["cost"]):
        r["cost"]["linkMs"] = 1.5 if i % 2 else 0.0          # a mean of 0.75 over all, 1.5 over the flushing ones
    assert GT.gate_x4(o)["sidecar_trigger"] == "fired"
    for r in o["frames"]["cost"]:
        r["cost"]["linkMs"] = 0.0
    g = GT.gate_x4(o)
    assert g["sidecar_trigger"] == "unmeasured" and g["emit_mean_ms"] is None


# ================================================================ x4_grade
def test_x4_grade_exits_on_the_verdict(tmp_path, capsys, good):
    p = tmp_path / "a.json"
    p.write_text(json.dumps(good))
    assert XG.main([str(p)]) == 0
    assert json.loads(capsys.readouterr().out)["verdict"] == "GO"
    bad = copy.deepcopy(good)
    bad["readings"]["rate60"]["tickMs"] = [1.2] * 1800
    p.write_text(json.dumps(bad))
    assert XG.main([str(p)]) == 1
    assert json.loads(capsys.readouterr().out)["verdict"] == "NO-GO"
    assert XG.main([]) == 2 and XG.main([str(p), str(p)]) == 2 and XG.main([str(tmp_path / "none.json")]) == 2
    p.write_text("{not json")
    assert XG.main([str(p)]) == 2
    p.write_text("[1, 2]")
    assert XG.main([str(p)]) == 2


def test_count_parks_reads_the_console_and_the_park_flag(tmp_path):
    con = tmp_path / "console.txt"
    con.write_text("LOG  : General > fine\nERROR: LuaError: attempted index: x of non-table\nPZTK: LuaError echo\n")
    found, n = D.count_parks([("admin", str(con))])
    assert n == 1 and len(found["admin"]) == 1
    clean = tmp_path / "clean.txt"
    clean.write_text("LOG  : General > fine\n")
    assert D.count_parks([("admin", str(clean))])[1] == 0
    assert D.count_parks([("admin", str(clean))], admin_parked=True)[1] == 1


# ================================================================ the copy: x4_link_2.py's phases and constants, its own key
def test_the_copy_differs_from_x4_link_2_only_in_its_docstring_head_and_its_three_names():
    """Plan 23 Task 16a (P23-C): the same phases, constants and gate; only the first docstring paragraph, KEY, DRIVER and
    ARTIFACT differ."""
    here = os.path.dirname(D.__file__)
    a = open(os.path.join(here, "x4_link_2.py"), encoding="utf-8").read()
    b = open(D.__file__, encoding="utf-8").read()
    body = lambda s: s[s.index("PHASES (each through xs.run_phase"):]
    norm = body(b)
    for mine, theirs in (('KEY = "x4_link_3"', 'KEY = "x4_link_2"'), ('DRIVER = "x4_link_3.py"', 'DRIVER = "x4_link_2.py"'),
                         ('ARTIFACT = "x4_link_3.json"', 'ARTIFACT = "x4_link_2.json"')):
        assert norm.count(mine) == 1, mine
        norm = norm.replace(mine, theirs)
    assert norm == body(a)
    head = b[:b.index("PHASES (each through xs.run_phase")]
    for c in ("ed519ef5", "3240565b"):
        assert c in head, c
    from agent.drivers import x4_link_2 as D1
    assert D.CONSTANTS == D1.CONSTANTS and D.PHASES == D1.PHASES and D.PROFILE == D1.PROFILE
